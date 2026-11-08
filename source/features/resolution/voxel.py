"""Voxel Density Up and Down: a finer or coarser voxel size, then a voxel remesh."""

import bpy
from bpy.types import Operator

from ...utils.constants import CANCEL, FINISHED


def remeshable(context) -> bool:
    """A mesh without a Multires modifier, whose levels a voxel remesh would drop"""
    obj = context.active_object
    if not obj or obj.type != "MESH":
        return False
    return not any(isinstance(mod, bpy.types.MultiresModifier) for mod in obj.modifiers)


class SCULPT_DECK_OT_density_up(Operator):
    """Increase voxel density and remesh"""

    bl_label = "Increase voxel density and remesh"
    bl_idname = "sculpt_deck.density_up"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not remeshable(context):
            return CANCEL
        mesh = context.active_object.data
        mesh.remesh_voxel_size *= 0.8
        bpy.ops.object.voxel_remesh()
        return FINISHED


class SCULPT_DECK_OT_density_down(Operator):
    """Decrease voxel density and remesh"""

    bl_label = "Decrease voxel density and remesh"
    bl_idname = "sculpt_deck.density_down"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not remeshable(context):
            return CANCEL
        mesh = context.active_object.data
        mesh.remesh_voxel_size /= 0.8
        bpy.ops.object.voxel_remesh()
        return FINISHED


classes = (
    SCULPT_DECK_OT_density_down,
    SCULPT_DECK_OT_density_up,
)


register, unregister = bpy.utils.register_classes_factory(classes)
