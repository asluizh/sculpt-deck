"""Touch navigation in the 3D View: a touch on a side rail zooms, one inside the circle pans and one elsewhere rotates
(pan and rotate swapped by Swap Pan/Rotate; pan only while the rotation is locked).

A touch the object tap (features/object_tap) takes is passed on to it: it waits to see whether the touch is a tap
and, when it moves, starts the navigation through `TouchHandoff`. A touch it doesn't take (tap turned off, a mode
without objects to tap, a tablet) is navigated here right away."""

import math

import bpy
from bpy.props import EnumProperty
from bpy.types import Operator
from mathutils import Vector

from ..core.constants import FINISHED, PASSTHROUGH, PEN, PRESS, brush_modes
from ..core.preferences import preferences
from ..features.object_tap import tap
from ..surfaces.clicks.action import is_touch
from .settings import navigation_settings

input_mode_items = [
    ("ORBIT", "Rotate", "Rotate the viewport"),
    ("PAN", "Pan", "Move the viewport"),
    ("DOLLY", "Zoom", "Zoom in/out the viewport"),
]


def zone_mode(context, x: float, y: float) -> str:
    """ORBIT, PAN or DOLLY for a touch at x, y of the region"""
    prefs = navigation_settings()
    region = context.region
    mid_point = Vector((region.width / 2, region.height / 2))
    dolly_wid = mid_point.x * prefs.getWidth()
    pan_diameter = math.dist((0, 0), mid_point) * (prefs.getRadius() * 0.5)  # type: ignore

    is_quadview_orthographic = context.region_data.is_orthographic_side_view and region.alignment == "QUAD_SPLIT"
    is_locked = context.region_data.lock_rotation or is_quadview_orthographic

    if dolly_wid > x or x > region.width - dolly_wid:
        mode = "DOLLY"
    elif math.dist((x, y), mid_point) < pan_diameter or is_locked:  # type: ignore
        mode = "PAN"
    else:
        mode = "ORBIT"

    if prefs.swap_panrotate and not is_locked:
        mode = {"PAN": "ORBIT", "ORBIT": "PAN"}.get(mode, mode)
    return mode


def navigate(context, mode: str, x: float, y: float):
    if context.mode == "SCULPT":
        bpy.ops.sculpt.set_pivot_position(mode=preferences().interface.pivot_mode)
    if mode == "DOLLY":
        bpy.ops.view3d.zoom("INVOKE_DEFAULT")  # type: ignore
    elif mode == "ORBIT":
        if context.mode == "SCULPT":
            bpy.ops.sculpt.set_pivot_position(mode="SURFACE", mouse_x=x, mouse_y=y)
        bpy.ops.view3d.rotate("INVOKE_DEFAULT")  # type: ignore
    elif mode == "PAN":
        bpy.ops.view3d.move("INVOKE_DEFAULT")  # type: ignore


def takes(context, event) -> bool:
    """Whether touch navigation takes this press"""
    prefs = navigation_settings()

    # experimental passthrough in drawing mode
    if (
        prefs.lazy_mode
        and not prefs.is_enabled
        and event.value == PRESS
        and context.mode in brush_modes
        and tap.object_at(context, event.mouse_region_x, event.mouse_region_y) != context.active_object
    ):
        return True

    if not prefs.is_enabled:
        return False
    if prefs.input_mode == "FULL" and (event.type == PEN or not is_touch(event)):
        return False
    return event.value == PRESS


class TouchHandoff:
    """The object tap's way into navigation: which touches navigation takes, and starting it once one moves"""

    def claims(self, context, event) -> bool:
        return takes(context, event)

    def start(self, context, x: float, y: float):
        navigate(context, zone_mode(context, x, y), x, y)


class SCULPT_DECK_OT_touch_input_3d(Operator):
    """Active Viewport control zones"""

    bl_label = "Viewport Control Regions"
    bl_idname = "sculpt_deck.view_ops_3d"

    mode: EnumProperty(  # type: ignore
        name="Mode",
        description="Sets the viewport control type",
        items=input_mode_items,
        options={"HIDDEN"},
        default="ORBIT",
    )

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def invoke(self, context, event):
        # the object tap's, which starts the navigation itself if the touch moves
        if tap.takes_press(context, event) or not takes(context, event):
            return PASSTHROUGH
        self.delta = (event.mouse_region_x, event.mouse_region_y)
        self.mode = zone_mode(context, *self.delta)
        navigate(context, self.mode, *self.delta)
        return FINISHED

    def execute(self, context):
        navigate(context, self.mode, context.region.width / 2, context.region.height / 2)
        return FINISHED


def register():
    bpy.utils.register_class(SCULPT_DECK_OT_touch_input_3d)
    tap.set_drag_handoff(TouchHandoff())


def unregister():
    tap.set_drag_handoff(None)
    bpy.utils.unregister_class(SCULPT_DECK_OT_touch_input_3d)
