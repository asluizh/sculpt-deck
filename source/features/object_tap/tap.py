"""Tap an object to select it or switch to it, double tap for the double click action, long press to add it to or
remove it from the selection.

A touch can also start viewport navigation, which lives apart (navigation/) so it can be removed. The two share the
press, each with its own keymap entry: navigation passes on the presses `takes_press` accepts, this operator waits
to see whether the touch is a tap, and hands a touch that moves over to the navigation through `drag_handoff`,
which navigation sets while it's registered. Without navigation, a touch is only taken when it lands on an object
a tap would select or switch to, and a drag from there does nothing."""

import math
import time
from typing import Protocol

import bpy
from bpy.types import Operator
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
from mathutils import Vector

from ...core.blender import ui_scale
from ...core.constants import FINISHED, LMOUSE, MODAL, PASSTHROUGH, PRESS, object_modes
from ...core.preferences import preferences
from ...surfaces.clicks.action import click_binding, is_touch

# a touch that lifts within TAP_TIME without moving TAP_SLOP pixels is a tap;
# held for LONG_PRESS_TIME without moving it toggles the object's selection
TAP_TIME = 0.35
TAP_SLOP = 5
LONG_PRESS_TIME = 0.5
# a second tap this close to the first one makes a double tap; Blender's own
# double click needs both clicks on almost the same pixel
DOUBLE_TAP_DISTANCE = 40


class DragHandoff(Protocol):
    """What a touch that moves becomes: set by navigation while it's registered"""

    def claims(self, context, event) -> bool:
        """Whether this press is a touch the navigation would take"""
        ...

    def start(self, context, x: float, y: float):
        """Start navigating, for a touch pressed at x, y of the region"""
        ...


drag_handoff: DragHandoff | None = None


def set_drag_handoff(handoff: DragHandoff | None):
    global drag_handoff
    drag_handoff = handoff


def object_at(context, x: float, y: float):
    """The mesh object under a point of the region, if any (the original, not the evaluated one)"""
    region = context.region
    rv3d = context.region_data
    coord = Vector((x, y))
    ray_origin = region_2d_to_origin_3d(region, rv3d, coord)
    ray_target = ray_origin + region_2d_to_vector_3d(region, rv3d, coord)

    best_length_squared = -1.0
    best_obj = None
    depsgraph = context.evaluated_depsgraph_get()
    for dup in depsgraph.object_instances:
        obj = dup.instance_object if dup.is_instance else dup.object
        if obj.type != "MESH":
            continue
        matrix = dup.matrix_world.copy() if dup.is_instance else obj.matrix_world.copy()
        # the ray relative to the object
        matrix_inv = matrix.inverted()
        origin = matrix_inv @ ray_origin
        success, location, _normal, _face = obj.ray_cast(origin, matrix_inv @ ray_target - origin)
        if not success:
            continue
        length_squared = (matrix @ location - ray_origin).length_squared
        if best_obj is None or length_squared < best_length_squared:
            best_length_squared = length_squared
            best_obj = obj
    return best_obj.original if best_obj is not None else None


def takes_press(context, event) -> bool:
    """Whether the object tap takes this press of the 3D viewport, to wait and see if it's a tap. Navigation passes
    these on, so the two don't depend on the order of their keymap entries"""
    if event.value != PRESS or event.is_tablet:
        return False
    if not preferences().object_tap.tap_to_switch or context.mode not in object_modes:
        return False
    if drag_handoff is not None:
        return drag_handoff.claims(context, event)
    # without navigation, only a touch a tap would turn into a selection or switch
    target = object_at(context, event.mouse_region_x, event.mouse_region_y)
    return is_touch(event) and target is not None and target != context.view_layer.objects.active


class SCULPT_DECK_OT_object_tap(Operator):
    """Tap an object to select it or switch to it, long press to toggle its selection"""

    bl_label = "Object Tap"
    bl_idname = "sculpt_deck.object_tap"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def invoke(self, context, event):
        if not takes_press(context, event):
            return PASSTHROUGH
        self.delta = (event.mouse_region_x, event.mouse_region_y)

        # wait to see whether this is a tap, a long press or a drag
        self.press_time = time.monotonic()
        self.state = "PRESSED"
        wm = context.window_manager
        self.timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        return MODAL

    def modal(self, context, event):
        elapsed = time.monotonic() - self.press_time
        if self.state == "PRESSED":
            if event.type == LMOUSE and event.value == "RELEASE":
                if elapsed >= TAP_TIME:
                    return self.finish(context)
                # a second tap may follow; act only once it's clear it won't
                if click_binding(context, "double_click") is not None:
                    self.state = "RELEASED"
                    self.release_time = time.monotonic()
                    return MODAL
                self.tap(context)
                return self.finish(context)
            if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"}:
                dx = event.mouse_region_x - self.delta[0]
                dy = event.mouse_region_y - self.delta[1]
                if math.hypot(dx, dy) > TAP_SLOP * ui_scale():
                    self.finish(context)
                    if drag_handoff is not None:
                        drag_handoff.start(context, *self.delta)
                    return FINISHED
                return MODAL
            if event.type == "TIMER" and elapsed >= LONG_PRESS_TIME:
                self.toggle_selection(context)
                self.state = "LONG_PRESSED"
            return PASSTHROUGH

        if self.state == "RELEASED":
            if event.type == LMOUSE and event.value in {"PRESS", "DOUBLE_CLICK"}:
                dx = event.mouse_region_x - self.delta[0]
                dy = event.mouse_region_y - self.delta[1]
                if math.hypot(dx, dy) <= DOUBLE_TAP_DISTANCE * ui_scale():
                    try:
                        bpy.ops.sculpt_deck.dt_action("EXEC_DEFAULT")  # type: ignore
                    except RuntimeError as error:
                        self.report({"WARNING"}, str(error))
                    self.state = "DOUBLE_TAPPED"
                    return MODAL
                # a new touch somewhere else: the first one was a single tap
                self.tap(context)
                self.finish(context)
                return {"FINISHED", "PASS_THROUGH"}
            double_click_time = context.preferences.inputs.mouse_double_click_time / 1000
            if event.type == "TIMER" and time.monotonic() - self.release_time > double_click_time:
                self.tap(context)
                return self.finish(context)
            return PASSTHROUGH

        # long pressed or double tapped: ignore the rest of the touch
        if event.type == LMOUSE and event.value == "RELEASE":
            return self.finish(context)
        return MODAL if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"} else PASSTHROUGH

    def finish(self, context):
        context.window_manager.event_timer_remove(self.timer)
        return FINISHED

    # tap an object to select it, or to switch to it in edit/sculpt/paint modes
    def tap(self, context):
        if context.mode == "OBJECT":
            bpy.ops.view3d.select("INVOKE_DEFAULT", deselect_all=True)  # type: ignore
            return
        target = object_at(context, *self.delta)
        if target is None or target == context.view_layer.objects.active:
            return
        try:
            # with its undo steps, as from Blender's own keymap: called from Python it skips the step of entering
            # the mode, so undo would go back to "Change Active", saved before the object entered it
            bpy.ops.object.transfer_mode("INVOKE_DEFAULT", True)  # type: ignore
        except RuntimeError:
            pass  # the object can't enter this mode

    # long press an object to add it to or remove it from the selection
    def toggle_selection(self, context):
        target = object_at(context, *self.delta)
        active = context.view_layer.objects.active
        if target is None or target == active:
            return
        target.select_set(not target.select_get())
        if active is not None:
            active.select_set(True)
        change = "added to" if target.select_get() else "removed from"
        self.report({"INFO"}, f"{target.name} {change} the selection")
        context.area.tag_redraw()


# the keymaps touch navigation also uses
KEYMAPS = ("3D View", "Grease Pencil")
keymap_items = []


def register():
    bpy.utils.register_class(SCULPT_DECK_OT_object_tap)
    wm = bpy.context.window_manager
    for kmap in wm.keyconfigs["Blender"].keymaps:
        if kmap.name not in KEYMAPS:
            continue
        km = wm.keyconfigs.addon.keymaps.new(name=kmap.name, space_type=kmap.space_type, region_type=kmap.region_type)
        keymap_items.append((km, km.keymap_items.new(SCULPT_DECK_OT_object_tap.bl_idname, LMOUSE, PRESS)))


def unregister():
    for km, kmi in keymap_items:
        km.keymap_items.remove(kmi)
    keymap_items.clear()
    bpy.utils.unregister_class(SCULPT_DECK_OT_object_tap)
