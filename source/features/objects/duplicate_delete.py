"""Duplicate and Delete: Detours on the active mesh."""

import bpy
from bpy.types import Operator

from ...core.constants import object_modes
from ...core.detour import Detour
from ...core.history import object_history
from ..local_transform.operators import TOOL_ID


class ActiveMesh(Detour):
    """Shared by Duplicate and Delete: the active mesh, alone in the selection, in Object Mode"""

    @classmethod
    def poll(cls, context):
        obj = context.view_layer.objects.active
        return context.mode in object_modes and obj is not None and obj.type == "MESH"

    def object_mode_work(self, context):
        obj = context.view_layer.objects.active
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        self.run(context, obj)

    def run(self, context, obj):
        raise NotImplementedError


class SCULPT_DECK_OT_duplicate_object(ActiveMesh, Operator):
    """Copy the active mesh and move the copy with Local Transform, staying in the current mode"""

    bl_label = "Duplicate"
    bl_idname = "sculpt_deck.duplicate_object"
    bl_options = {"REGISTER", "UNDO"}

    def run(self, context, obj):
        # the copy is active
        bpy.ops.object.duplicate()

    def return_tool(self) -> str:
        # place the copy right away
        return TOOL_ID if self.start_mode == "SCULPT" else ""


# Round Edges of the cube Delete adds when no mesh is left
DELETE_CUBE_ROUNDNESS = 0.25


class SCULPT_DECK_OT_delete_object(ActiveMesh, Operator):
    """Delete the active mesh and go back to the mesh used before it, in the current mode.
    When no mesh is left, a rounded cube takes its place"""

    bl_label = "Delete"
    bl_idname = "sculpt_deck.delete_object"
    bl_options = {"REGISTER", "UNDO"}

    def run(self, context, obj):
        layer = context.view_layer
        previous = object_history.previous(context, obj) or next(
            (o for o in layer.objects if o != obj and o.type == "MESH" and o.visible_get()), None
        )
        bpy.ops.object.delete()
        if previous is not None:
            previous.select_set(True)
            layer.objects.active = previous
        elif self.start_mode != "OBJECT":
            # Sculpt and the other modes need a mesh to work on. Add Mesh runs as part of this Detour: this one
            # already stored the Scene Checkpoint, and both return to the mode this one started from.
            bpy.ops.sculpt_deck.add_primitive(
                primitive="CUBE", roundness=DELETE_CUBE_ROUNDNESS, keep_tool=True,
                start_mode=self.start_mode, checkpoint=False,
            )


classes = (
    SCULPT_DECK_OT_duplicate_object,
    SCULPT_DECK_OT_delete_object,
)

register, unregister = bpy.utils.register_classes_factory(classes)
