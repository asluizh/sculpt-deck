"""Join Selected, Fuse (Union) and Fuse (Difference): Detours that combine the selected meshes into the active one."""

import bpy
from bpy.props import FloatProperty
from bpy.types import Operator

from ...core.constants import object_modes
from ...core.detour import Detour


class SelectedMeshes(Detour):
    """Shared by Join and Fuse: the selected meshes, combined into the active one in Object Mode"""

    @classmethod
    def poll(cls, context):
        meshes = [obj for obj in context.selected_objects if obj.type == "MESH"]
        active = context.view_layer.objects.active
        return context.mode in object_modes and len(meshes) > 1 and active in meshes

    def object_mode_work(self, context):
        active = context.view_layer.objects.active
        others = [obj for obj in context.selected_objects if obj.type == "MESH" and obj != active]
        self.combine(context, active, others)

    def combine(self, context, active, others):
        for obj in context.selected_objects:
            if obj.type != "MESH":
                obj.select_set(False)
        bpy.ops.object.join()


class Fuse(SelectedMeshes):
    voxel_size: FloatProperty(  # type: ignore
        name="Voxel Size",
        description="Size of the remesh voxels, 0 keeps the active object's voxel size",
        default=0.0,
        min=0.0,
        subtype="DISTANCE",
    )

    def remesh(self, obj):
        if self.voxel_size > 0:
            obj.data.remesh_voxel_size = self.voxel_size
        bpy.ops.object.voxel_remesh()


class SCULPT_DECK_OT_join_selected(SelectedMeshes, Operator):
    """Join the selected meshes into the active one, staying in the current mode"""

    bl_label = "Join Selected"
    bl_idname = "sculpt_deck.join_selected"
    bl_options = {"REGISTER", "UNDO"}


class SCULPT_DECK_OT_fuse_selected(Fuse, Operator):
    """Merge the selected meshes into the active one and voxel remesh them, staying in the current mode"""

    bl_label = "Fuse (Union)"
    bl_idname = "sculpt_deck.fuse_selected"
    bl_options = {"REGISTER", "UNDO"}

    def combine(self, context, active, others):
        super().combine(context, active, others)
        self.remesh(active)


class SCULPT_DECK_OT_fuse_difference(Fuse, Operator):
    """Cut the other selected meshes out of the active one and voxel remesh it, staying in the current mode"""

    bl_label = "Fuse (Difference)"
    bl_idname = "sculpt_deck.fuse_difference"
    bl_options = {"REGISTER", "UNDO"}

    def combine(self, context, active, others):
        for cutter in others:
            modifier = active.modifiers.new("Sculpt Deck Cut", "BOOLEAN")
            modifier.operation = "DIFFERENCE"
            modifier.solver = "EXACT"
            modifier.object = cutter
            # apply before any existing modifiers, e.g. Multires
            bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=0)
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            bpy.data.objects.remove(cutter)
        self.remesh(active)


classes = (
    SCULPT_DECK_OT_fuse_difference,
    SCULPT_DECK_OT_fuse_selected,
    SCULPT_DECK_OT_join_selected,
)

register, unregister = bpy.utils.register_classes_factory(classes)
