import bpy
from bpy.types import Operator
from mathutils import Matrix

from ...core.constants import CANCEL, FINISHED
from ..array.operators import (active_tool, apply_modifier, array_poll, get_input, leave_tool, modifier_tools,
                               realize)

###
# Mirror
#  A Geometry Nodes modifier that keeps the real mesh where it is, visible
#  and sculptable, and shows its mirror image as an instance, across the
#  planes of the world origin, or of a Mirror Object when one is set. The
#  planes are in world space, so moving the mesh (with Local Transform, say)
#  moves its mirror image the other way. Applying turns the mirror image into
#  real mesh and merges the vertices on the planes. Like the array tools, the
#  tool adds a mirror when it starts and hands back to the previous tool once
#  the mirror is applied or removed, or the active mesh has none.
###

MIRROR_TOOL_ID = "sculpt_deck.mirror"
modifier_tools.add(MIRROR_TOOL_ID)

GROUP_KEY = "sculpt_deck_mirror"
GROUP_VERSION = 1
NAME = "Mirror"

AXES = ("X", "Y", "Z")
MERGE_DISTANCE = 0.001


# NODE GROUP


def new_group():
    group = bpy.data.node_groups.new(NAME, "GeometryNodeTree")
    group.is_modifier = True
    group[GROUP_KEY] = GROUP_VERSION
    interface = group.interface
    interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    for axis in AXES:
        socket = interface.new_socket(axis, in_out="INPUT", socket_type="NodeSocketBool")
        socket.description = f"Mirror across the plane facing {axis}"
        socket.default_value = axis == "X"
    mirror_object = interface.new_socket("Mirror Object", in_out="INPUT", socket_type="NodeSocketObject")
    mirror_object.description = "Mirror across this object's planes instead of the world origin's"
    merge = interface.new_socket("Merge Distance", in_out="INPUT", socket_type="NodeSocketFloat")
    merge.description = "Vertices this close to a mirror plane are merged when the mirror is applied"
    merge.subtype = "DISTANCE"
    merge.default_value = MERGE_DISTANCE
    merge.min_value = 0.0
    realize = interface.new_socket("Realize", in_out="INPUT", socket_type="NodeSocketBool")
    realize.description = "Make the mirror image real mesh, set when the mirror is applied"
    realize.hide_in_modifier = True

    nodes, links = group.nodes, group.links
    inputs = nodes.new("NodeGroupInput")
    output = nodes.new("NodeGroupOutput")

    def node(idname, **connections):
        new = nodes.new(idname)
        for name, value in connections.items():
            name = name.rstrip("_")
            socket = new.inputs[int(name[1:])] if name[0] == "i" and name[1:].isdigit() else new.inputs[name]
            if isinstance(value, bpy.types.NodeSocket):
                links.new(value, socket)
            else:
                socket.default_value = value
        return new

    def switch(input_type, condition, false, true):
        new = node("GeometryNodeSwitch")
        new.input_type = input_type
        links.new(condition, new.inputs["Switch"])
        links.new(false, new.inputs["False"])
        links.new(true, new.inputs["True"])
        return new.outputs[0]

    # the mirror frame in the object's space: the mirror object's (or the
    # world's, an empty Object Info gives the identity) world matrix seen
    # from the object, so the planes stay put in the world when it moves
    self_info = node("GeometryNodeObjectInfo", Object=node("GeometryNodeSelfObject").outputs[0])
    self_info.transform_space = "ORIGINAL"
    mirror_info = node("GeometryNodeObjectInfo", Object=inputs.outputs["Mirror Object"])
    mirror_info.transform_space = "ORIGINAL"
    to_local = node("FunctionNodeInvertMatrix", Matrix=self_info.outputs["Transform"]).outputs["Matrix"]
    frame = node("FunctionNodeMatrixMultiply", i0=to_local, i1=mirror_info.outputs["Transform"]).outputs[0]
    from_frame = node("FunctionNodeInvertMatrix", Matrix=frame).outputs["Matrix"]

    shown = realized = inputs.outputs["Geometry"]
    for i, axis in enumerate(AXES):
        flip = [1.0, 1.0, 1.0]
        flip[i] = -1.0
        scale = node("FunctionNodeCombineTransform", Scale=flip).outputs[0]
        reflect = node(
            "FunctionNodeMatrixMultiply",
            i0=node("FunctionNodeMatrixMultiply", i0=frame, i1=scale).outputs[0],
            i1=from_frame,
        ).outputs[0]
        enabled = inputs.outputs[axis]

        # shown: the mirror image as an instance, so only the real mesh is
        # sculpted and Blender draws the reflection the right way out
        image = node("GeometryNodeGeometryToInstance", i0=shown).outputs[0]
        moved = node("GeometryNodeTransform", Geometry=image)
        moved.inputs["Mode"].default_value = "Matrix"
        links.new(reflect, moved.inputs["Transform"])
        join = node("GeometryNodeJoinGeometry")
        links.new(moved.outputs[0], join.inputs[0])
        links.new(shown, join.inputs[0])
        shown = switch("GEOMETRY", enabled, shown, join.outputs[0])

        # applied: real mesh, with faces flipped so it isn't inside out
        moved = node("GeometryNodeTransform", Geometry=realized)
        moved.inputs["Mode"].default_value = "Matrix"
        links.new(reflect, moved.inputs["Transform"])
        flipped = node("GeometryNodeFlipFaces", Mesh=moved.outputs[0]).outputs[0]
        join = node("GeometryNodeJoinGeometry")
        links.new(flipped, join.inputs[0])
        links.new(realized, join.inputs[0])
        realized = switch("GEOMETRY", enabled, realized, join.outputs[0])

    # merge only the vertices on an enabled plane, where the halves meet
    position = node("GeometryNodeInputPosition").outputs[0]
    in_frame = node("FunctionNodeTransformPoint", Vector=position, Transform=from_frame).outputs[0]
    parts = node("ShaderNodeSeparateXYZ", Vector=in_frame)
    near = None
    for i, axis in enumerate(AXES):
        distance = node("ShaderNodeMath", i0=parts.outputs[i])
        distance.operation = "ABSOLUTE"
        close = node("FunctionNodeCompare", A=distance.outputs[0], B=inputs.outputs["Merge Distance"])
        close.data_type = "FLOAT"
        close.operation = "LESS_EQUAL"
        on_plane = node("FunctionNodeBooleanMath", i0=close.outputs[0], i1=inputs.outputs[axis])
        on_plane.operation = "AND"
        if near is None:
            near = on_plane.outputs[0]
        else:
            either = node("FunctionNodeBooleanMath", i0=near, i1=on_plane.outputs[0])
            either.operation = "OR"
            near = either.outputs[0]
    merged = node(
        "GeometryNodeMergeByDistance", Geometry=realized, Selection=near, Distance=inputs.outputs["Merge Distance"]
    ).outputs[0]
    # the faces where the halves met are inside the mesh now; a face is on
    # a plane when all its vertices are
    cleaned = node("GeometryNodeDeleteGeometry", Geometry=merged, Selection=near)
    cleaned.domain = "FACE"
    cleaned.mode = "ONLY_FACE"
    merged = cleaned.outputs[0]

    links.new(switch("GEOMETRY", inputs.outputs["Realize"], shown, merged), output.inputs[0])
    for column, each in enumerate(nodes):
        each.location = (column * 200, 0)
    return group


def node_group():
    for group in bpy.data.node_groups:
        if group.get(GROUP_KEY) == GROUP_VERSION:
            return group
    return new_group()


# MODIFIERS


def is_mirror(modifier) -> bool:
    return (
        modifier is not None
        and modifier.type == "NODES"
        and modifier.node_group is not None
        and modifier.node_group.get(GROUP_KEY) is not None
    )


def current_mirror(obj):
    """The active modifier when it's a mirror, else the last one"""
    if obj is None:
        return None
    if is_mirror(obj.modifiers.active):
        return obj.modifiers.active
    return next((m for m in reversed(obj.modifiers) if is_mirror(m)), None)


def mirror_frame(modifier) -> Matrix:
    """World matrix of the mirror planes"""
    mirror_object = get_input(modifier, "Mirror Object")
    return mirror_object.matrix_world.copy() if mirror_object is not None else Matrix.Identity(4)


def enabled_axes(modifier) -> list[int]:
    return [i for i, axis in enumerate(AXES) if get_input(modifier, axis)]


def add_mirror(obj):
    modifier = obj.modifiers.new(NAME, "NODES")
    modifier.node_group = node_group()
    obj.modifiers.active = modifier
    obj.update_tag()
    return modifier


def ensure_mirror(object_name: str):
    """Add a mirror when the tool starts on a mesh without one, see the tool"""
    obj = bpy.data.objects.get(object_name)
    windows = bpy.context.window_manager.windows
    if obj is None or not windows or obj.type != "MESH" or obj.mode != "SCULPT":
        return
    if current_mirror(obj) is not None:
        return
    add_mirror(obj)
    with bpy.context.temp_override(window=windows[0]):
        bpy.ops.ed.undo_push(message="Add Mirror")


# OPERATORS


class MirrorOperator:
    @classmethod
    def poll(cls, context):
        return array_poll(context) and current_mirror(context.active_object) is not None

    def leave(self, context, obj):
        # the mirror tool has nothing left to edit
        if active_tool(context) == MIRROR_TOOL_ID and current_mirror(obj) is None:
            leave_tool(context)


class SCULPT_DECK_OT_mirror_apply(MirrorOperator, Operator):
    """Turn the mirror image into real mesh, merged with the mesh on the mirror planes"""

    bl_label = "Apply Mirror"
    bl_idname = "sculpt_deck.mirror_apply"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        modifier = current_mirror(obj)
        if modifier is None:
            return CANCEL
        realize(obj, modifier)
        apply_modifier(context, modifier)
        self.leave(context, obj)
        return FINISHED


class SCULPT_DECK_OT_mirror_remove(MirrorOperator, Operator):
    """Remove the mirror, keeping only the mesh itself"""

    bl_label = "Remove Mirror"
    bl_idname = "sculpt_deck.mirror_remove"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        modifier = current_mirror(obj)
        if modifier is None:
            return CANCEL
        obj.modifiers.remove(modifier)
        self.leave(context, obj)
        return FINISHED


classes = (
    SCULPT_DECK_OT_mirror_apply,
    SCULPT_DECK_OT_mirror_remove,
)

register, unregister = bpy.utils.register_classes_factory(classes)
