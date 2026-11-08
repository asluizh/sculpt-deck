"""Toggles that replace keyboard shortcuts: the sidebar (N), the side of the tools region, the Sculpt pivot mode, and
Cycle Control Gizmo for the object gizmos."""

import bpy
from bpy.types import Operator

from ...core.constants import CANCEL, FINISHED
from ...core.preferences import preferences
from .settings import pivot_items


class SCULPT_DECK_OT_flip_tools(Operator):
    """Relocate Tools panel between left and right"""

    bl_label = "Tools Region Swap"
    bl_idname = "sculpt_deck.tools_region_flip"

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def execute(self, context):
        override = context.copy()
        override["area"] = context.area
        override["region"] = context.region
        for r in context.area.regions:
            if r.type == "TOOLS":
                override["region"] = r
        with context.temp_override(region=override["region"]):  # type: ignore
            bpy.ops.screen.region_flip()
        return FINISHED


class SCULPT_DECK_OT_next_pivot_mode(Operator):
    """Step through Pivot modes"""

    bl_label = "Use next Pivot mode"
    bl_idname = "sculpt_deck.step_pivot_mode"

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def execute(self, context):
        prefs = preferences().interface
        count = 0
        for enum, _, _ in pivot_items:
            if enum == prefs.pivot_mode:
                count += 1
                if count == len(pivot_items):
                    count = 0
                pivot = pivot_items[count][0]
                bpy.ops.sculpt.set_pivot_position(mode=pivot)
                prefs.pivot_mode = pivot
                context.area.tag_redraw()
                return FINISHED
            count += 1
        return FINISHED


class SCULPT_DECK_OT_toggle_npanel(Operator):
    """Toggle the sidebar (N panel)"""

    bl_label = "Display prefs Panel"
    bl_idname = "sculpt_deck.toggle_n_panel"

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def execute(self, context):
        if not isinstance(context.space_data, bpy.types.SpaceView3D):
            return CANCEL
        context.space_data.show_region_ui ^= True
        return FINISHED


class SCULPT_DECK_OT_cycle_controlGizmo(Operator):
    """Cycle the object gizmo between move, rotate, scale and none"""

    bl_label = "switch object control gizmo"
    bl_idname = "sculpt_deck.cycle_control_gizmo"

    @classmethod
    def poll(cls, context):
        return context.area.type in ["VIEW_2D", "VIEW_3D"] and context.region.type == "WINDOW"

    def execute(self, context):
        space = context.space_data
        if not isinstance(space, bpy.types.SpaceView3D):
            return CANCEL
        mode = self.getMode(space)
        self.clearControls(space)
        if mode == "none":
            space.show_gizmo_object_translate = True
        if mode == "translate":
            space.show_gizmo_object_rotate = True
        if mode == "rotate":
            space.show_gizmo_object_scale = True
        return FINISHED

    def getMode(self, space: bpy.types.SpaceView3D):
        if space.show_gizmo_object_translate:
            return "translate"
        if space.show_gizmo_object_rotate:
            return "rotate"
        if space.show_gizmo_object_scale:
            return "scale"
        return "none"

    def clearControls(self, space: bpy.types.SpaceView3D):
        space.show_gizmo_object_translate = False
        space.show_gizmo_object_rotate = False
        space.show_gizmo_object_scale = False


classes = (
    SCULPT_DECK_OT_cycle_controlGizmo,
    SCULPT_DECK_OT_flip_tools,
    SCULPT_DECK_OT_next_pivot_mode,
    SCULPT_DECK_OT_toggle_npanel,
)


register, unregister = bpy.utils.register_classes_factory(classes)
