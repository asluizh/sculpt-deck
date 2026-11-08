"""Invert Mask and Reveal Hidden, which Blender only offers from its keymap or the Mask and Face Sets menus."""

import bpy
from bpy.types import Operator

from ...core.constants import FINISHED


class SCULPT_DECK_OT_mask_invert(Operator):
    """Invert the sculpt mask"""

    bl_label = "Invert Mask"
    bl_idname = "sculpt_deck.mask_invert"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "SCULPT"

    def execute(self, context):
        bpy.ops.paint.mask_flood_fill(mode="INVERT")
        return FINISHED


class SCULPT_DECK_OT_reveal_all(Operator):
    """Show all hidden parts of the sculpt"""

    bl_label = "Reveal Hidden"
    bl_idname = "sculpt_deck.reveal_all"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "SCULPT"

    def execute(self, context):
        bpy.ops.paint.hide_show_all(action="SHOW")
        return FINISHED


classes = (
    SCULPT_DECK_OT_mask_invert,
    SCULPT_DECK_OT_reveal_all,
)


register, unregister = bpy.utils.register_classes_factory(classes)
