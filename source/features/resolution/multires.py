"""Multires Level Up and Down: step the active object's Multires level, subdividing past the highest level (up to
the Subdivision Limit setting) and unsubdividing below the lowest."""

import bpy
from bpy.types import Operator

from ...core.constants import CANCEL, FINISHED
from .settings import resolution_settings


class SCULPT_DECK_OT_increase_multires(Operator):
    """Increase the Multires level, subdividing when at the highest level"""

    bl_label = "Increment Multires modifier by 1 or add subdivision level"
    bl_idname = "sculpt_deck.increment_multires"

    def execute(self, context):
        prefs = resolution_settings()
        if not context.active_object or not len(context.active_object.modifiers):
            return CANCEL
        for mod in context.active_object.modifiers:
            if isinstance(mod, bpy.types.MultiresModifier):
                if context.mode == "SCULPT":
                    if mod.sculpt_levels == mod.total_levels:
                        if mod.sculpt_levels < prefs.subdivision_limit:
                            bpy.ops.object.multires_subdivide(modifier=mod.name)
                    else:
                        mod.sculpt_levels += 1
                else:
                    if mod.levels == mod.total_levels:
                        if mod.levels < prefs.subdivision_limit:
                            bpy.ops.object.multires_subdivide(modifier=mod.name)
                    else:
                        mod.levels += 1
                return FINISHED
        return CANCEL


class SCULPT_DECK_OT_decrease_multires(Operator):
    """Decrease the Multires level, unsubdividing when at the lowest level"""

    bl_label = "decrement Multires modifier by 1"
    bl_idname = "sculpt_deck.decrement_multires"

    def execute(self, context):
        if not context.active_object or not len(context.active_object.modifiers):
            return CANCEL
        for mod in context.active_object.modifiers:
            if not isinstance(mod, bpy.types.MultiresModifier):
                continue
            if context.mode == "SCULPT":
                if mod.sculpt_levels == 0:
                    bpy.ops.object.multires_unsubdivide(modifier=mod.name)
                else:
                    mod.sculpt_levels -= 1
            else:
                if mod.levels == 0:
                    bpy.ops.object.multires_unsubdivide(modifier=mod.name)
                else:
                    mod.levels -= 1
            return FINISHED
        return CANCEL


classes = (
    SCULPT_DECK_OT_decrease_multires,
    SCULPT_DECK_OT_increase_multires,
)


register, unregister = bpy.utils.register_classes_factory(classes)
