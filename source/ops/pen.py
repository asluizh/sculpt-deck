import time

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..utils.actions import TOOL_PREFIX, active_tool, invoke_action, set_tool
from ..utils.blender import preferences, ui_scale
from ..utils.brush import (activate_brush, brush_name, brush_ref, history,
                           paint_settings)
from ..utils.constants import (CANCEL, FINISHED, MODAL, PASSTHROUGH,
                               brush_direction_pairs, pen_brush_actions,
                               pen_brush_modes, pen_buttons,
                               pen_default_context_menus, pen_hold_action)

# a press becomes a hold after this long, or once it moves past Blender's
# tablet drag threshold, or when the pen tip touches down while it's held
HOLD_TIME = 0.3


def is_pen(event) -> bool:
    return event.is_tablet


class TOUCHVIEW_OT_pen_button(Operator):
    """Run the action bound to this pen button"""

    bl_label = "Pen Button Action"
    bl_idname = "touchview.pen_button"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    def invoke(self, context, event):
        if not is_pen(event) or event.value != "PRESS" or event.type not in pen_buttons:
            return PASSTHROUGH
        pen_set = preferences().getPenSet(context.mode)
        if pen_set is None:
            return PASSTHROUGH
        self.button_type = event.type
        button = pen_buttons[event.type]
        self.click = getattr(pen_set, button + "_click")
        self.hold = getattr(pen_set, button + "_hold")
        if self.click.action == "DEFAULT" and self.hold.action == "DEFAULT":
            return PASSTHROUGH

        self.mode = context.mode
        self.start = (event.mouse_x, event.mouse_y)
        self.start_time = time.monotonic()
        self.is_hold = False
        self.revert = None  # brush or tool to restore when a hold ends
        history.update(context)
        self.snapshot = history.snapshot(self.mode)

        # when click and hold switch to the same brush or tool, switch right
        # away so drawing isn't delayed; release then decides whether it sticks
        click_target = self.switch_target(self.click)
        if click_target is not None and click_target == self.switch_target(self.hold):
            self.switch_temporarily(context, click_target)

        wm = context.window_manager
        self.timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        return MODAL

    def modal(self, context, event):
        if event.type == self.button_type and event.value == "RELEASE":
            return self.release(context)
        if event.type in {"ESC", "WINDOW_DEACTIVATE"}:
            self.end_hold(context)
            self.finish(context)
            return {"FINISHED", "PASS_THROUGH"}

        # hold to invert: strokes drawn while the button is held are inverted,
        # like holding Ctrl
        if (
            self.hold.action == "touchview.brush_invert"
            and event.type == "LEFTMOUSE"
            and event.value == "PRESS"
            and self.mode == "SCULPT"
            and active_tool(context) == "builtin.brush"
        ):
            self.is_hold = True
            bpy.ops.sculpt.brush_stroke("INVOKE_DEFAULT", mode="INVERT")  # type: ignore
            return MODAL

        if not self.is_hold and self.becomes_hold(context, event):
            self.is_hold = True
            result = self.start_hold(context)
            if result is not None:
                return result
        # let everything else through, e.g. a stroke with a temporary brush
        return PASSTHROUGH

    def becomes_hold(self, context, event) -> bool:
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            return True
        if time.monotonic() - self.start_time > HOLD_TIME:
            return True
        threshold = context.preferences.inputs.drag_threshold_tablet * ui_scale()
        dx, dy = event.mouse_x - self.start[0], event.mouse_y - self.start[1]
        return (dx * dx + dy * dy) ** 0.5 > threshold

    # returns an operator result when the hold hands over to something else
    def start_hold(self, context):
        action = self.hold.action
        if pen_hold_action(action):
            target = self.switch_target(self.hold)
            if self.revert is None and target is not None:
                self.switch_temporarily(context, target)
            return None

        # the hold does something else, so drop what was switched on press
        self.end_hold(context)
        self.finish(context)
        if action == "DEFAULT":
            self.run_default(context, hold=True)
        else:
            self.run_action(context, self.hold)
        return FINISHED

    def release(self, context):
        self.finish(context)
        if self.is_hold:
            self.end_hold(context)
        elif self.revert is None:
            if self.click.action == "DEFAULT":
                self.run_default(context, hold=False)
            else:
                self.run_action(context, self.click)
        # a click keeps a brush or tool switched on press
        return FINISHED

    def finish(self, context):
        if self.timer is not None:
            context.window_manager.event_timer_remove(self.timer)
            self.timer = None

    # what a brush or tool action switches to, as (kind, target)
    def switch_target(self, binding):
        action = binding.action
        if action == "BRUSH_PREVIOUS":
            ref = history.previous.get(self.mode)
            return ("BRUSH", ref) if ref else None
        if action == "BRUSH":
            ref = binding.brushRef()
            return ("BRUSH", ref) if ref else None
        if action.startswith(TOOL_PREFIX):
            return ("TOOL", action[len(TOOL_PREFIX):])
        return None

    def current(self, context, kind: str):
        if kind == "TOOL":
            return ("TOOL", active_tool(context))
        return ("BRUSH", brush_ref(paint_settings(context, self.mode)))

    def switch_temporarily(self, context, target):
        current = self.current(context, target[0])
        if target == current or not current[1]:
            return
        if self.switch(context, target):
            self.revert = current
            history.update(context)

    def end_hold(self, context):
        if self.revert is None:
            return
        self.switch(context, self.revert)
        self.revert = None
        # a temporary brush shouldn't become the "previous" brush
        history.restore(self.mode, self.snapshot)

    def switch(self, context, target) -> bool:
        kind, value = target
        if kind == "TOOL":
            try:
                set_tool(value)
                return True
            except RuntimeError as error:
                self.report({"WARNING"}, f"Can't use tool {value}: {error}")
                return False
        if activate_brush(value):
            return True
        self.report({"WARNING"}, f"Brush not found: {brush_name(value)}")
        return False

    def run_default(self, context, hold: bool):
        if self.button_type == "MIDDLEMOUSE":
            if hold:
                bpy.ops.view3d.rotate("INVOKE_DEFAULT")  # type: ignore
            return
        op, name = pen_default_context_menus.get(self.mode, (None, None))
        if op is not None:
            category, op_name = op.split(".")
            getattr(getattr(bpy.ops, category), op_name)("INVOKE_DEFAULT", name=name)

    def run_action(self, context, binding):
        action = binding.action
        if action == "NONE":
            return
        if action in pen_brush_actions or action.startswith(TOOL_PREFIX):
            target = self.switch_target(binding)
            if target is not None:
                self.switch(context, target)
            elif action == "BRUSH_PREVIOUS":
                self.report({"INFO"}, "No previous brush yet")
            else:
                self.report({"WARNING"}, "No brush set for this pen button")
        else:
            self.run_shared(binding.operator.strip() if action == "CUSTOM" else action)

    # an action shared with the pie and the widget, or a custom one
    def run_shared(self, idname: str):
        try:
            invoke_action(idname)
        except (ValueError, AttributeError, RuntimeError) as error:
            self.report({"WARNING"}, f"Can't run '{idname}': {error}")


class TOUCHVIEW_OT_brush_previous(Operator):
    """Switch back to the previously used brush"""

    bl_label = "Previous Brush"
    bl_idname = "touchview.brush_previous"

    @classmethod
    def poll(cls, context):
        return context.mode in pen_brush_modes

    def execute(self, context):
        history.update(context)
        target = history.previous.get(context.mode)
        if target is None:
            self.report({"INFO"}, "No previous brush yet")
            return CANCEL
        if not activate_brush(target):
            self.report({"WARNING"}, f"Brush not found: {brush_name(target)}")
            return CANCEL
        return FINISHED


class TOUCHVIEW_OT_brush_invert(Operator):
    """Switch the brush direction, e.g. add/subtract or smooth/enhance details"""

    bl_label = "Invert Brush"
    bl_idname = "touchview.brush_invert"

    @classmethod
    def poll(cls, context):
        brush = context.tool_settings.sculpt.brush if context.mode == "SCULPT" else None
        return brush is not None and brush.direction in brush_direction_pairs

    def execute(self, context):
        brush = context.tool_settings.sculpt.brush
        brush.direction = brush_direction_pairs[brush.direction]
        return FINISHED


class TOUCHVIEW_OT_pen_use_active_brush(Operator):
    """Bind the brush that is currently active in this mode"""

    bl_label = "Use Active Brush"
    bl_idname = "touchview.pen_use_active_brush"
    bl_options = {"INTERNAL"}

    mode: StringProperty()  # type: ignore
    slot: StringProperty()  # type: ignore

    def execute(self, context):
        pen_set = preferences().getPenSet(self.mode)
        ref = brush_ref(paint_settings(context, self.mode))
        if pen_set is None or ref is None:
            self.report({"WARNING"}, "No active brush to use")
            return CANCEL
        getattr(pen_set, self.slot).setBrushRef(ref)
        context.preferences.is_dirty = True
        return FINISHED


classes = (
    TOUCHVIEW_OT_brush_invert,
    TOUCHVIEW_OT_brush_previous,
    TOUCHVIEW_OT_pen_button,
    TOUCHVIEW_OT_pen_use_active_brush,
)


register, unregister = bpy.utils.register_classes_factory(classes)
