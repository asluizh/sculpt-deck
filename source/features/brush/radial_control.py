"""Brush Size and Brush Strength: Blender's radial control on the active brush, as its own keymap opens it."""

import math

import bpy
from bpy.types import Operator

from ...utils.blender import preferences
from ...utils.constants import CANCEL, FINISHED, paint_settings_name


class BrushRadialControl:
    """Shared radial control for brush properties, mirroring Blender's own keymap"""

    prop = ""

    def invoke(self, context, event):
        prefs = preferences()
        # move the cursor away from the bar so the radial control has room
        if prefs.menu_style in {"fixed.bar"}:
            if prefs.gizmo_position in ["LEFT", "RIGHT"]:
                context.window.cursor_warp(
                    context.region.x + math.floor(context.region.width / 2),
                    context.region.y + event.mouse_region_y,
                )
            else:
                context.window.cursor_warp(
                    context.region.x + event.mouse_region_x,
                    context.region.y + math.floor(context.region.height / 2),
                )
        return self.execute(context)

    def execute(self, context):
        paint = paint_settings_name(context.mode)
        if paint is None:
            return CANCEL
        brush_path = f"tool_settings.{paint}.brush"
        # grease pencil draw mode ignores unified settings, same as Blender's keymap
        if paint == "gpencil_paint":
            bpy.ops.wm.radial_control(
                "INVOKE_DEFAULT",  # type: ignore
                data_path_primary=f"{brush_path}.{self.prop}",
            )
            return FINISHED

        unified_path = f"tool_settings.{paint}.unified_paint_settings"
        bpy.ops.wm.radial_control(
            "INVOKE_DEFAULT",  # type: ignore
            data_path_primary=f"{brush_path}.{self.prop}",
            data_path_secondary=f"{unified_path}.{self.prop}",
            use_secondary=f"{unified_path}.use_unified_{self.prop}",
            rotation_path=f"{brush_path}.texture_slot.angle",
            color_path=f"{brush_path}.cursor_color_add",
            image_id=brush_path,
        )
        return FINISHED


class SCULPT_DECK_OT_brush_resize(BrushRadialControl, Operator):
    """Adjust the brush size"""

    bl_label = "Brush Size Adjust"
    bl_idname = "sculpt_deck.brush_resize"

    prop = "size"


class SCULPT_DECK_OT_brush_strength(BrushRadialControl, Operator):
    """Adjust the brush strength"""

    bl_label = "Brush Strength Adjust"
    bl_idname = "sculpt_deck.brush_strength"

    prop = "strength"


classes = (
    SCULPT_DECK_OT_brush_resize,
    SCULPT_DECK_OT_brush_strength,
)


register, unregister = bpy.utils.register_classes_factory(classes)
