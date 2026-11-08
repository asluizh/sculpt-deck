# Brush Actions offered on every surface: Previous Brush and Invert Brush. The pen buttons themselves are in
# surfaces/pen.
import bpy
from bpy.types import Operator

from ..utils.brush import activate_brush, brush_name, history
from ..utils.constants import (CANCEL, FINISHED, brush_direction_pairs,
                               pen_brush_modes)


class SCULPT_DECK_OT_brush_previous(Operator):
    """Switch back to the previously used brush"""

    bl_label = "Previous Brush"
    bl_idname = "sculpt_deck.brush_previous"

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


class SCULPT_DECK_OT_brush_invert(Operator):
    """Switch the brush direction, e.g. add/subtract or smooth/enhance details"""

    bl_label = "Invert Brush"
    bl_idname = "sculpt_deck.brush_invert"

    @classmethod
    def poll(cls, context):
        brush = context.tool_settings.sculpt.brush if context.mode == "SCULPT" else None
        return brush is not None and brush.direction in brush_direction_pairs

    def execute(self, context):
        brush = context.tool_settings.sculpt.brush
        brush.direction = brush_direction_pairs[brush.direction]
        return FINISHED


classes = (
    SCULPT_DECK_OT_brush_invert,
    SCULPT_DECK_OT_brush_previous,
)


register, unregister = bpy.utils.register_classes_factory(classes)
