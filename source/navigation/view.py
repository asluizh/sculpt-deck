"""Navigation Actions: Recenter View, Lock Rotation and Toggle Touch Controls (also on Alt T, see keymaps.py), added to
the Action catalog while navigation is registered."""

import bpy
from bpy.types import Operator

from ..core.actions import ANY_MODE, action, add_actions, remove_actions
from ..core.constants import CANCEL, FINISHED
from .settings import navigation_settings


class SCULPT_DECK_OT_toggle_touch_controls(Operator):
    """Toggle Touch Controls"""

    bl_label = "Toggle Touch Controls"
    bl_idname = "sculpt_deck.toggle_touch"

    def execute(self, context):
        prefs = navigation_settings()
        prefs.is_enabled = not prefs.is_enabled
        context.area.tag_redraw()
        return FINISHED


class SCULPT_DECK_OT_viewport_recenter(Operator):
    """Recenter Viewport and Cursor on Selected Object"""

    bl_label = "Recenter Viewport and Cursor on Selected"
    bl_idname = "sculpt_deck.viewport_recenter"

    def execute(self, context):
        current = context.scene.tool_settings.transform_pivot_point
        context.scene.tool_settings.transform_pivot_point = "ACTIVE_ELEMENT"
        bpy.ops.view3d.snap_cursor_to_selected()
        bpy.ops.view3d.view_center_cursor()
        bpy.ops.view3d.view_selected()
        context.scene.tool_settings.transform_pivot_point = current
        return FINISHED


class SCULPT_DECK_OT_viewport_lock(Operator):
    """Toggle viewport rotation lock"""

    bl_label = "Viewport rotation lock toggle"
    bl_idname = "sculpt_deck.viewport_lock"

    region_ids = []

    def execute(self, context):
        if not isinstance(context.area.spaces.active, bpy.types.SpaceView3D):
            return CANCEL
        if len(context.area.spaces.active.region_quadviews) == 0:
            context.region_data.lock_rotation ^= True
            return FINISHED

        for region in context.area.spaces.active.region_quadviews:
            self.region_ids.append((region.as_pointer(), region.lock_rotation))

        start_change = False
        regions = dict(self.region_ids)
        for i in range(3, -1, -1):
            region_data = context.area.spaces.active.region_quadviews[i]
            if context.region_data.as_pointer() == region_data.as_pointer():
                start_change = True
                context.region_data.lock_rotation ^= True
                continue

            if start_change:
                region_data.lock_rotation = regions[region_data.as_pointer()]
        self.region_ids = []
        return FINISHED


classes = (
    SCULPT_DECK_OT_toggle_touch_controls,
    SCULPT_DECK_OT_viewport_lock,
    SCULPT_DECK_OT_viewport_recenter,
)

# the Actions of every mode these operators are, each placed after an Action of the catalog
ACTIONS = (
    ("ed.redo", action("sculpt_deck.viewport_recenter", "Recenter on Selected", "CURSOR", ANY_MODE)),
    ("sculpt_deck.toggle_n_panel", action("sculpt_deck.viewport_lock", "Toggle Rotation Lock", "LOCKED", ANY_MODE)),
    ("screen.region_quadview", action("sculpt_deck.toggle_touch", "Toggle Touch Controls", "VIEW_PAN", ANY_MODE)),
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    for after, entry in ACTIONS:
        add_actions(after, entry)


def unregister():
    remove_actions(*(entry for _, entry in ACTIONS))
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
