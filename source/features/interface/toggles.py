"""Toggles that replace keyboard shortcuts: the sidebar (N), the side of the tools region, the Sculpt pivot mode."""

import bpy
from bpy.types import Operator

from ...utils.blender import preferences
from ...utils.constants import CANCEL, FINISHED, pivot_items


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
        prefs = preferences()
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


classes = (
    SCULPT_DECK_OT_flip_tools,
    SCULPT_DECK_OT_next_pivot_mode,
    SCULPT_DECK_OT_toggle_npanel,
)


register, unregister = bpy.utils.register_classes_factory(classes)
