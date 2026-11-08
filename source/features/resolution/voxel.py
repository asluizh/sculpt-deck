"""Voxel Density Up and Down: a finer or coarser voxel size, then a voxel remesh.

The voxel size is mesh data, which a Sculpt undo step doesn't hold. In Sculpt Mode each press stores a Scene
Checkpoint first, so undo brings the size back with the geometry, and remeshes through a Hop to Object Mode, so
Blender's remesher stores no Sculpt step of its own and the press's own step is a whole scene step that redo
applies in full (size included).
"""

import bpy
from bpy.types import Operator

from ...core.checkpoint import store_scene_checkpoint
from ...core.constants import CANCEL, FINISHED
from ...core.hop import hop


def remeshable(context) -> bool:
    """A mesh in Object or Sculpt Mode without Dyntopo (the remesher refuses either), and without a Multires
    modifier, whose levels a voxel remesh would drop"""
    obj = context.active_object
    if not obj or obj.type != "MESH" or obj.mode not in {"OBJECT", "SCULPT"} or obj.use_dynamic_topology_sculpting:
        return False
    return not any(isinstance(mod, bpy.types.MultiresModifier) for mod in obj.modifiers)


def remesh(operator: Operator, context, factor: float):
    """Scale the active mesh's voxel size by `factor` and voxel remesh it"""
    store_scene_checkpoint(context, f"Before {operator.bl_label}")
    # in Sculpt Mode the remesher would store a Sculpt step (geometry only), which the press's step would become
    with hop(context, "OBJECT"):
        mesh = context.active_object.data
        mesh.remesh_voxel_size *= factor
        bpy.ops.object.voxel_remesh()


class SCULPT_DECK_OT_density_up(Operator):
    """Increase voxel density and remesh"""

    bl_label = "Increase voxel density and remesh"
    bl_idname = "sculpt_deck.density_up"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not remeshable(context):
            return CANCEL
        remesh(self, context, 0.8)
        return FINISHED


class SCULPT_DECK_OT_density_down(Operator):
    """Decrease voxel density and remesh"""

    bl_label = "Decrease voxel density and remesh"
    bl_idname = "sculpt_deck.density_down"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not remeshable(context):
            return CANCEL
        remesh(self, context, 1 / 0.8)
        return FINISHED


classes = (
    SCULPT_DECK_OT_density_down,
    SCULPT_DECK_OT_density_up,
)


register, unregister = bpy.utils.register_classes_factory(classes)
