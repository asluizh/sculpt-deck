"""Join Selected, Fuse (Union) and Fuse (Difference): Detours that combine the selected meshes into the active one.

What gets combined is what the user sees. Join keeps the active mesh's modifiers (see modifiers.py): a mesh whose
modifiers draw the same as the active's is joined as it is, any other has its modifiers applied first. When the
active mesh has modifiers that would act differently on the others, Join asks whether to keep them or to apply every
modifier. Fuse remeshes or cuts the meshes, so it always applies every modifier first.
"""

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator

from ...core.constants import object_modes
from ...core.detour import Detour
from .modifiers import apply_blocker, apply_shown, draws_like, shown

join_modifier_items = [
    (
        "APPLY_ALL",
        "Apply All",
        "Apply every modifier first, the active mesh's too, so the joined mesh looks as the meshes did",
    ),
    (
        "KEEP_ACTIVE",
        "Keep Active's Modifiers",
        "Keep the active mesh's modifiers, acting on the joined meshes too; the other meshes' own are applied first",
    ),
]


def selection(context):
    """The active mesh and the other selected meshes"""
    active = context.view_layer.objects.active
    return active, [obj for obj in context.selected_objects if obj.type == "MESH" and obj != active]


class SelectedMeshes(Detour):
    """Shared by Join and Fuse: the selected meshes, combined into the active one in Object Mode"""

    @classmethod
    def poll(cls, context):
        # only an active mesh, as Blender's own Join asks: Adjust Last Operation checks the poll before undoing,
        # when the other meshes are joined already, so asking for them here would cancel every adjustment
        active = context.view_layer.objects.active
        return context.mode in object_modes and active is not None and active.type == "MESH"

    def to_apply(self, active, others) -> list:
        """The meshes whose modifiers get applied before combining"""
        return [active, *others]

    def blocker(self, context) -> str:
        active, others = selection(context)
        if not active.select_get() or not others:
            return "Select the meshes to combine with the active one"
        return apply_blocker(self.to_apply(active, others))

    def object_mode_work(self, context):
        active, others = selection(context)
        for obj in self.to_apply(active, others):
            apply_shown(context, obj)
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


def differing(active, others) -> bool:
    """Whether the active mesh has modifiers that would act on other meshes differently from their own"""
    return bool(shown(active)) and not all(draws_like(active, obj) for obj in others)


class SCULPT_DECK_OT_join_selected(SelectedMeshes, Operator):
    """Join the selected meshes into the active one, staying in the current mode. What each mesh shows is kept:
    modifiers are applied first unless the active mesh's would draw the same"""

    bl_label = "Join Selected"
    bl_idname = "sculpt_deck.join_selected"
    bl_options = {"REGISTER", "UNDO"}

    modifiers: EnumProperty(  # type: ignore
        name="Modifiers",
        description="What to do when the active mesh's modifiers would act differently on the other meshes",
        items=join_modifier_items,
        default="APPLY_ALL",
        options={"SKIP_SAVE"},
    )
    # whether the active mesh's modifiers differed, recorded when run, for Adjust Last Operation (the other meshes
    # are gone by then)
    differed: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore

    def invoke(self, context, event):
        if differing(*selection(context)):
            return context.window_manager.invoke_props_dialog(self, title="Join Selected", confirm_text="Join")
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        if not (self.differed or differing(*selection(context))):
            return
        column = layout.column(align=True)
        column.label(text="The active mesh's modifiers would act", icon="ERROR")
        column.label(text="differently on the other meshes.")
        layout.prop(self, "modifiers", expand=True)

    def to_apply(self, active, others) -> list:
        self.differed = differing(active, others)
        if self.differed and self.modifiers == "APPLY_ALL":
            return [active, *others]
        # the active mesh's modifiers stay; a mesh they'd draw the same on is joined as it is
        return [obj for obj in others if not draws_like(active, obj)]


class SCULPT_DECK_OT_fuse_selected(Fuse, Operator):
    """Merge the selected meshes into the active one and voxel remesh them, staying in the current mode. Modifiers
    are applied first"""

    bl_label = "Fuse (Union)"
    bl_idname = "sculpt_deck.fuse_selected"
    bl_options = {"REGISTER", "UNDO"}

    def combine(self, context, active, others):
        super().combine(context, active, others)
        self.remesh(active)


class SCULPT_DECK_OT_fuse_difference(Fuse, Operator):
    """Cut the other selected meshes out of the active one and voxel remesh it, staying in the current mode.
    Modifiers are applied first"""

    bl_label = "Fuse (Difference)"
    bl_idname = "sculpt_deck.fuse_difference"
    bl_options = {"REGISTER", "UNDO"}

    def combine(self, context, active, others):
        for cutter in others:
            modifier = active.modifiers.new("Sculpt Deck Cut", "BOOLEAN")
            modifier.operation = "DIFFERENCE"
            modifier.solver = "EXACT"
            modifier.object = cutter
            # apply before the modifiers left, hidden ones
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
