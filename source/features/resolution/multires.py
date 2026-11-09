"""Multires Level Up and Down: step the active object's Multires level, subdividing past the highest level (up to
the Subdivision Limit setting) and unsubdividing below the lowest.

The levels are modifier settings, which a Sculpt undo step doesn't hold. In Sculpt Mode each press stores a Scene
Checkpoint first, and its own step is then a whole scene step too (no Blender operator it runs stores a Sculpt
step), so undo and redo bring back both the levels and the subdivided mesh.
"""

import bpy
from bpy.types import Operator

from ...core.checkpoint import store_scene_checkpoint
from ...core.constants import CANCEL, FINISHED
from .settings import resolution_settings


def multires_modifier(context):
    obj = context.active_object
    if not obj:
        return None
    return next((mod for mod in obj.modifiers if isinstance(mod, bpy.types.MultiresModifier)), None)


def level_name(context) -> str:
    """The level the current mode shows and sculpts at"""
    return "sculpt_levels" if context.mode == "SCULPT" else "levels"


def run_blender(operator: Operator, blender_operator, modifier: str) -> set[str]:
    """Run Blender's (un)subdivide on the modifier, cancelling with its message when it fails. The checkpoint
    already stored then stays, as the one extra step."""
    try:
        blender_operator(modifier=modifier)
    except RuntimeError as error:
        operator.report({"WARNING"}, str(error).strip())
        return CANCEL
    return FINISHED


class SCULPT_DECK_OT_increase_multires(Operator):
    """Increase the Multires level, subdividing when at the highest level"""

    bl_label = "Increment Multires modifier by 1 or add subdivision level"
    bl_idname = "sculpt_deck.increment_multires"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        mod = multires_modifier(context)
        if mod is None:
            return CANCEL
        level = getattr(mod, level_name(context))
        if level == mod.total_levels and level >= resolution_settings().subdivision_limit:
            return CANCEL
        store_scene_checkpoint(context, f"Before {self.bl_label}")
        if level < mod.total_levels:
            setattr(mod, level_name(context), level + 1)
            return FINISHED
        return run_blender(self, bpy.ops.object.multires_subdivide, mod.name)


class SCULPT_DECK_OT_decrease_multires(Operator):
    """Decrease the Multires level, unsubdividing when at the lowest level"""

    bl_label = "decrement Multires modifier by 1"
    bl_idname = "sculpt_deck.decrement_multires"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        mod = multires_modifier(context)
        if mod is None:
            return CANCEL
        store_scene_checkpoint(context, f"Before {self.bl_label}")
        level = getattr(mod, level_name(context))
        if level > 0:
            setattr(mod, level_name(context), level - 1)
            return FINISHED
        # fails when Blender finds no lower level to rebuild
        return run_blender(self, bpy.ops.object.multires_unsubdivide, mod.name)


classes = (
    SCULPT_DECK_OT_decrease_multires,
    SCULPT_DECK_OT_increase_multires,
)


register, unregister = bpy.utils.register_classes_factory(classes)
