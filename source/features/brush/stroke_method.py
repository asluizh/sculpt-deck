"""Stroke Method: the menu Blender opens with Alt E in paint and sculpt modes."""

import bpy
from bpy.types import Operator

from ...utils.constants import FINISHED, paint_settings_name


class SCULPT_DECK_OT_stroke_method(Operator):
    """Choose how the active brush applies its stroke (Space, Dots, Line, Curve...)"""

    bl_label = "Stroke Method"
    bl_idname = "sculpt_deck.stroke_method"

    @classmethod
    def poll(cls, context):
        paint = paint_settings_name(context.mode)
        if paint is None:
            return False
        brush = getattr(getattr(context.tool_settings, paint, None), "brush", None)
        return brush is not None and hasattr(brush, "stroke_method")

    def execute(self, context):
        paint = paint_settings_name(context.mode)
        bpy.ops.wm.context_menu_enum(data_path=f"tool_settings.{paint}.brush.stroke_method")
        return FINISHED


classes = (SCULPT_DECK_OT_stroke_method,)


register, unregister = bpy.utils.register_classes_factory(classes)
