# Pen Event Probe
#
# Development tool for checking how Blender reports pen/stylus buttons, in
# particular whether `event.is_tablet` can tell a pen button apart from a mouse.
# Not part of the Sculpt Deck add-on.
#
# Usage: open this file in Blender's Text Editor and press Run Script, then in
# the 3D Viewport sidebar (N) open the "Pen Probe" tab and press Start.
# Every button/key event is shown in the viewport and appended to the text
# block "pen_probe.log" and to ~/pen_probe.log on disk (written immediately, so
# it survives quitting Blender). Events are passed through so Blender keeps
# working, unless "Block Blender Actions" is on: then Blender never sees events
# in the viewport (so e.g. a middle-click doesn't start rotating and hide the
# release). Pen events are always blocked; mouse/touch still work in the 3D
# Viewport sidebar, so Stop (or Esc) ends it. Each line notes the area/region under the cursor and, when blocking,
# whether the event was blocked or passed on to Blender.

bl_info = {
    "name": "Pen Event Probe",
    "description": "Logs pen, mouse and touch events to check event.is_tablet",
    "author": "Sculpt Deck contributors",
    "blender": (5, 2, 0),
    "version": (0, 1, 0),
    "category": "Development",
    "location": "View3D > Sidebar > Pen Probe",
}

import os
import time
from collections import deque

import blf
import bpy
from bpy.props import BoolProperty
from bpy.types import Operator, Panel

LOG_NAME = "pen_probe.log"
LOG_PATH = os.path.join(os.path.expanduser("~"), LOG_NAME)
MOVE_EVENTS = {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"}
IGNORED_EVENTS = {"TIMER", "TIMER_REPORT", "TIMERREGION", "NONE", "WINDOW_DEACTIVATE"}


class State:
    running = False
    stop = False
    lines: deque = deque(maxlen=18)
    last_move = ""
    draw_handle = None
    font = None
    # event type -> (time, x, y) of the last press, to measure taps vs drags
    presses: dict = {}


def describe(event) -> str:
    mods = "+".join(m for m in ("shift", "ctrl", "alt", "oskey") if getattr(event, m))
    return (
        f"{event.type:<12} {event.value:<8} tablet={str(event.is_tablet):<5} "
        f"pressure={event.pressure:.2f} tilt={event.tilt[0]:+.2f},{event.tilt[1]:+.2f} "
        f"at {event.mouse_x},{event.mouse_y}{' ' + mods if mods else ''}"
    )


def log(line: str):
    State.lines.append(line)
    text = bpy.data.texts.get(LOG_NAME) or bpy.data.texts.new(LOG_NAME)
    text.write(line + "\n")
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as file:
            file.write(line + "\n")
    except OSError as error:
        print("[pen probe] can't write", LOG_PATH, error)
    print("[pen probe]", line)


# area and region under the cursor; overlapping regions (sidebar, toolbar,
# headers) win over the main region they are drawn on top of
def regions_at(window, x: int, y: int):
    found = None
    for area in window.screen.areas:
        for region in area.regions:
            if region.width <= 1 or region.height <= 1:
                continue
            if region.x <= x < region.x + region.width and region.y <= y < region.y + region.height:
                if region.type != "WINDOW":
                    return area, region
                found = (area, region)
    return found or (None, None)


# blocking spares mouse/touch in the 3D Viewport sidebar, where Stop lives. With
# region overlap the sidebar spans the full height, so pen events are never
# spared, wherever they land
def is_probe_sidebar(area, region) -> bool:
    return area is not None and area.type == "VIEW_3D" and region.type == "UI"


def place(area, region) -> str:
    if area is None:
        return "outside"
    return f"{area.type}/{region.type}"


def redraw_viewports():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def monospace_font() -> int:
    if State.font is None:
        path = os.path.join(bpy.utils.system_resource("DATAFILES"), "fonts", "DejaVuSansMono.woff2")
        State.font = blf.load(path) if os.path.exists(path) else -1
    return State.font if State.font != -1 else 0


def draw_overlay():
    if not State.running:
        return
    ui = bpy.context.preferences.system.ui_scale
    font = monospace_font()
    blf.size(font, 11 * ui)
    blf.enable(font, blf.SHADOW)
    blf.shadow(font, 5, 0.0, 0.0, 0.0, 1.0)
    # right of the toolbar, below the viewport's own header text
    tools = [r.width for r in bpy.context.area.regions if r.type == "TOOLS"]
    x = (tools[0] if tools else 0) + 16 * ui
    y = bpy.context.region.height - 150 * ui
    step = 15 * ui
    blocking = bpy.context.window_manager.pen_probe_block
    title = "PEN PROBE (Blender actions blocked; Stop in sidebar or Esc)" if blocking else "PEN PROBE (Stop in sidebar)"
    rows = [title, "last move: " + State.last_move, ""]
    rows += list(State.lines)
    for i, row in enumerate(rows):
        blf.color(font, 1.0, 0.85 if i < 2 else 1.0, 0.3 if i < 2 else 1.0, 1.0)
        blf.position(font, x, y - i * step, 0)
        blf.draw(font, row)
    blf.disable(font, blf.SHADOW)


class PENPROBE_OT_run(Operator):
    """Log every pen, mouse and key event until stopped"""

    bl_idname = "pen_probe.run"
    bl_label = "Start Pen Probe"

    def invoke(self, context, event):
        if State.running:
            State.stop = True
            return {"FINISHED"}
        State.running = True
        State.stop = False
        State.draw_handle = bpy.types.SpaceView3D.draw_handler_add(draw_overlay, (), "WINDOW", "POST_PIXEL")
        log(f"--- probe started, Blender {bpy.app.version_string}, saving to {LOG_PATH} ---")
        context.window_manager.modal_handler_add(self)
        redraw_viewports()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if State.stop:
            self.finish()
            return {"FINISHED"}
        if event.type in IGNORED_EVENTS:
            return {"PASS_THROUGH"}

        area, region = regions_at(context.window, event.mouse_x, event.mouse_y)
        blocking = context.window_manager.pen_probe_block
        spared = is_probe_sidebar(area, region) and not event.is_tablet
        block = blocking and event.type not in MOVE_EVENTS and not spared
        line = f"{describe(event)}  [{place(area, region)}]"
        # Blender doesn't generate CLICK/CLICK_DRAG for blocked presses, so
        # measure hold time and travel between press and release here
        if event.value == "PRESS":
            State.presses[event.type] = (time.monotonic(), event.mouse_x, event.mouse_y)
        elif event.value == "RELEASE" and event.type in State.presses:
            start, x, y = State.presses.pop(event.type)
            moved = ((event.mouse_x - x) ** 2 + (event.mouse_y - y) ** 2) ** 0.5
            line += f"  held {(time.monotonic() - start) * 1000:.0f}ms moved {moved:.0f}px"
        if blocking:
            line += " blocked" if block else " passed"

        if event.type in MOVE_EVENTS:
            # moves are too frequent to log, only keep the latest
            State.last_move = line
        else:
            log(line)
        redraw_viewports()

        if blocking and event.type == "ESC" and event.value == "PRESS":
            self.finish()
            return {"FINISHED"}
        return {"RUNNING_MODAL"} if block else {"PASS_THROUGH"}

    def cancel(self, context):
        self.finish()

    def finish(self):
        log("--- probe stopped ---")
        State.running = False
        State.stop = False
        if State.draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(State.draw_handle, "WINDOW")
            State.draw_handle = None
        redraw_viewports()


class PENPROBE_OT_clear(Operator):
    """Clear the probe log"""

    bl_idname = "pen_probe.clear"
    bl_label = "Clear Log"

    def execute(self, context):
        State.lines.clear()
        State.last_move = ""
        text = bpy.data.texts.get(LOG_NAME)
        if text:
            text.clear()
        redraw_viewports()
        return {"FINISHED"}


class PENPROBE_PT_panel(Panel):
    bl_label = "Pen Probe"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Pen Probe"

    def draw(self, context):
        col = self.layout.column()
        if State.running:
            col.operator("pen_probe.run", text="Stop", icon="PAUSE", depress=True)
        else:
            col.operator("pen_probe.run", text="Start", icon="PLAY")
        col.prop(context.window_manager, "pen_probe_block")
        col.operator("pen_probe.clear", icon="TRASH")
        col.label(text=f"Log: Text Editor > {LOG_NAME}")
        col.label(text=f"Saved to: {LOG_PATH}")


classes = (PENPROBE_OT_run, PENPROBE_OT_clear, PENPROBE_PT_panel)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.pen_probe_block = BoolProperty(
        name="Block Blender Actions",
        description=(
            "Swallow logged events so Blender doesn't act on them. "
            "Mouse/touch still work in the 3D Viewport sidebar, so Stop (or Esc) ends the probe"
        ),
        default=False,
    )


def unregister():
    State.stop = True
    del bpy.types.WindowManager.pen_probe_block
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
