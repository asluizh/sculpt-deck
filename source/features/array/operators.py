import math

import bpy
from bpy.app.handlers import persistent
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, PropertyGroup
from bpy_extras import view3d_utils
from mathutils import Matrix, Vector

from ...core.checkpoint import store_scene_checkpoint
from ...core.constants import CANCEL, FINISHED, object_modes
from ...core.drag import (
    ScreenAngle,
    ViewDrag,
    axis_on_screen,
    distance_along,
    facing_sign,
    set_world_matrix,
    view_plane_offset,
)
from ...core.history import tool_history
from ...core.hop import active_object, cancel_step_over, hop

###
# Arrays
#  A Geometry Nodes modifier that keeps the real mesh where it is, visible
#  and sculptable, and places copies of it as instances: in a line (Offset
#  between copies) or around a circle (Center, Axis and Arc, with the
#  object's origin on the circle). Sculpting the mesh updates every copy, and
#  applying the modifier turns the copies into real mesh. Each kind has its
#  own tool, so a circular array can be stacked on a linear one. A tool adds
#  its array when it starts, and hands back to the previous tool once the
#  array is applied or removed, or the active mesh has none, also when undo
#  takes the array away; redo brings both back.
###

LINEAR_TOOL_ID = "sculpt_deck.linear_array"
CIRCULAR_TOOL_ID = "sculpt_deck.circular_array"

# marks our node groups, rebuilt when the version changes
GROUP_KEY = "sculpt_deck_array"
GROUP_VERSION = 2

array_kinds = [
    ("LINEAR", "Linear", "Copies in a line", "MOD_ARRAY", 0),
    ("CIRCULAR", "Circular", "Copies around a circle", "MESH_CIRCLE", 1),
]
kind_names = {"LINEAR": "Linear Array", "CIRCULAR": "Circular Array"}

orientation_items = [
    ("GLOBAL", "Global", "Handles and axes follow the world", "ORIENTATION_GLOBAL", 0),
    ("LOCAL", "Local", "Handles and axes follow the object", "ORIENTATION_LOCAL", 1),
]

AXES = ("X", "Y", "Z")
AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}

SNAP_DISTANCE = 0.1
MAX_COUNT = 1000

# dragging the arc inside the circle moves in coarse steps, outside in fine ones
ARC_COARSE = math.radians(15)
ARC_FINE = math.radians(1)
# turning the count handle this far adds or removes one copy
COUNT_TURN = math.radians(15)

# defaults for a new array, relative to the mesh's size
LINEAR_SPACING = 1.1
CIRCULAR_RADIUS = 0.6


# NODE GROUPS


def new_group(kind: str):
    group = bpy.data.node_groups.new(kind_names[kind], "GeometryNodeTree")
    group.is_modifier = True
    group[GROUP_KEY] = kind
    group[GROUP_KEY + "_version"] = GROUP_VERSION
    interface = group.interface
    interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    count = interface.new_socket("Count", in_out="INPUT", socket_type="NodeSocketInt")
    count.description = "Number of copies, counting the mesh itself"
    count.default_value = 3
    count.min_value = 1
    count.max_value = MAX_COUNT
    if kind == "LINEAR":
        offset = interface.new_socket("Offset", in_out="INPUT", socket_type="NodeSocketVector")
        offset.description = "Distance from one copy to the next, in the object's space"
        offset.subtype = "TRANSLATION"
    else:
        center = interface.new_socket("Center", in_out="INPUT", socket_type="NodeSocketVector")
        center.description = "Center of the circle, in the object's space"
        center.subtype = "TRANSLATION"
        axis = interface.new_socket("Axis", in_out="INPUT", socket_type="NodeSocketVector")
        axis.description = "Axis the copies turn around, in the object's space"
        axis.default_value = (0.0, 0.0, 1.0)
        arc = interface.new_socket("Arc", in_out="INPUT", socket_type="NodeSocketFloat")
        arc.description = "Angle the copies spread over, a full circle spaces them evenly"
        arc.subtype = "ANGLE"
        arc.default_value = math.tau
        arc.min_value = 0.0
        arc.max_value = math.tau
    realize = interface.new_socket("Realize", in_out="INPUT", socket_type="NodeSocketBool")
    realize.description = "Make the copies real mesh, set when the array is applied"
    realize.hide_in_modifier = True

    nodes, links = group.nodes, group.links
    inputs = nodes.new("NodeGroupInput")
    output = nodes.new("NodeGroupOutput")

    def math_node(operation, a, b):
        node = nodes.new("ShaderNodeMath")
        node.operation = operation
        for socket, value in zip(node.inputs, (a, b)):
            if isinstance(value, bpy.types.NodeSocket):
                links.new(value, socket)
            else:
                socket.default_value = value
        return node.outputs[0]

    def vector_node(operation, a, b=None, b_name=None):
        node = nodes.new("ShaderNodeVectorMath")
        node.operation = operation
        if a is not None:
            links.new(a, node.inputs[0])
        if b is not None:
            links.new(b, node.inputs[b_name] if b_name else node.inputs[1])
        return node.outputs[0]

    # The layout is built as if the object's scale were applied to the mesh
    # (as it is at the end of every scale), then that scale is taken back off
    # the copies, so they look the same while a non-uniform scale is dragged.
    # The scale only changes instance transforms, never the mesh itself.
    self_info = nodes.new("GeometryNodeObjectInfo")
    self_info.transform_space = "ORIGINAL"
    links.new(nodes.new("GeometryNodeSelfObject").outputs[0], self_info.inputs["Object"])
    scale = self_info.outputs["Scale"]
    unscale = vector_node("DIVIDE", None, scale)
    unscale.node.inputs[0].default_value = (1.0, 1.0, 1.0)
    as_instance = nodes.new("GeometryNodeGeometryToInstance")
    links.new(inputs.outputs["Geometry"], as_instance.inputs[0])
    scaled_mesh = nodes.new("GeometryNodeTransform")
    links.new(as_instance.outputs[0], scaled_mesh.inputs["Geometry"])
    links.new(scale, scaled_mesh.inputs["Scale"])

    # copy k (from 1) is the mesh moved k steps; the mesh itself is copy 0
    index = nodes.new("GeometryNodeInputIndex").outputs[0]
    step = math_node("ADD", index, 1.0)
    points = nodes.new("GeometryNodePoints")
    links.new(math_node("SUBTRACT", inputs.outputs["Count"], 1.0), points.inputs["Count"])
    instances = nodes.new("GeometryNodeInstanceOnPoints")
    links.new(points.outputs[0], instances.inputs["Points"])
    links.new(scaled_mesh.outputs[0], instances.inputs["Instance"])

    if kind == "LINEAR":
        offset = vector_node("MULTIPLY", inputs.outputs["Offset"], scale)
        position = vector_node("SCALE", offset, step, "Scale")
        links.new(position, points.inputs["Position"])
    else:
        # a full circle leaves a gap after the last copy, a partial arc ends on it
        full = math_node("GREATER_THAN", inputs.outputs["Arc"], math.tau - 0.001)
        divisions = math_node("ADD", math_node("SUBTRACT", inputs.outputs["Count"], 1.0), full)
        angle = math_node("MULTIPLY", step, math_node("DIVIDE", inputs.outputs["Arc"], divisions))
        rotation = nodes.new("FunctionNodeAxisAngleToRotation")
        axis = vector_node("NORMALIZE", vector_node("MULTIPLY", inputs.outputs["Axis"], scale))
        links.new(axis, rotation.inputs["Axis"])
        links.new(angle, rotation.inputs["Angle"])
        # turning around the center: rotate, then move by center - rotated center
        rotated = nodes.new("FunctionNodeRotateVector")
        center = vector_node("MULTIPLY", inputs.outputs["Center"], scale)
        links.new(center, rotated.inputs["Vector"])
        links.new(rotation.outputs[0], rotated.inputs["Rotation"])
        position = vector_node("SUBTRACT", center, rotated.outputs[0])
        links.new(position, points.inputs["Position"])
        links.new(rotation.outputs[0], instances.inputs["Rotation"])

    unscaled = nodes.new("GeometryNodeTransform")
    links.new(instances.outputs[0], unscaled.inputs["Geometry"])
    links.new(unscale, unscaled.inputs["Scale"])
    join = nodes.new("GeometryNodeJoinGeometry")
    links.new(unscaled.outputs[0], join.inputs[0])
    links.new(inputs.outputs["Geometry"], join.inputs[0])
    realize_node = nodes.new("GeometryNodeRealizeInstances")
    links.new(join.outputs[0], realize_node.inputs[0])
    switch = nodes.new("GeometryNodeSwitch")
    switch.input_type = "GEOMETRY"
    links.new(inputs.outputs["Realize"], switch.inputs["Switch"])
    links.new(join.outputs[0], switch.inputs["False"])
    links.new(realize_node.outputs[0], switch.inputs["True"])
    links.new(switch.outputs[0], output.inputs[0])

    for column, node in enumerate(nodes):
        node.location = (column * 200, 0)
    return group


def node_group(kind: str):
    for group in bpy.data.node_groups:
        if group.get(GROUP_KEY) == kind and group.get(GROUP_KEY + "_version") == GROUP_VERSION:
            return group
    return new_group(kind)


# MODIFIERS


def array_kind(modifier) -> str | None:
    if modifier is None or modifier.type != "NODES" or modifier.node_group is None:
        return None
    return modifier.node_group.get(GROUP_KEY)


def current_array(obj, kind: str):
    """The active modifier when it's an array of this kind, else the last one"""
    if obj is None:
        return None
    if array_kind(obj.modifiers.active) == kind:
        return obj.modifiers.active
    for modifier in reversed(obj.modifiers):
        if array_kind(modifier) == kind:
            return modifier
    return None


def input_id(modifier, name: str) -> str:
    for item in modifier.node_group.interface.items_tree:
        if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.name == name:
            return item.identifier
    raise KeyError(name)


def input_socket(modifier, name: str):
    """The modifier's value for a node group input, see its .value"""
    return getattr(modifier.properties.inputs, input_id(modifier, name))


def get_input(modifier, name: str):
    value = input_socket(modifier, name).value
    return Vector(value) if hasattr(value, "__len__") else value


def set_input(obj, modifier, name: str, value):
    input_socket(modifier, name).value = value
    obj.update_tag()
    redraw()


def realize(obj, modifier):
    """Have an array (or a mirror, which shares this input) make its copies real mesh when applied next"""
    set_input(obj, modifier, "Realize", True)


def redraw():
    # header buttons only redraw the header, show the new copies right away
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def circle_step(modifier) -> float:
    """Angle between two copies of a circular array"""
    count, arc = get_input(modifier, "Count"), get_input(modifier, "Arc")
    divisions = count - 1 + (1 if arc > math.tau - 0.001 else 0)
    return arc / divisions if divisions > 0 else 0.0


def copy_matrix(modifier, angle: float) -> Matrix:
    """Where a circular copy turned by the angle sits, in the object's space"""
    center, axis = get_input(modifier, "Center"), get_input(modifier, "Axis")
    if axis.length < 1e-9:
        axis = Vector((0.0, 0.0, 1.0))
    return Matrix.Translation(center) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-center)


# array vectors, in the object's space
ARRAY_VECTORS = {"LINEAR": ("Offset",), "CIRCULAR": ("Center", "Axis")}


def array_snapshot(obj) -> list[tuple[str, dict]]:
    return [
        (modifier.name, {name: get_input(modifier, name) for name in ARRAY_VECTORS[kind]})
        for modifier in obj.modifiers
        if (kind := array_kind(modifier)) in ARRAY_VECTORS
    ]


def keep_arrays(obj, snapshot, local: Matrix):
    """After the object's matrix changed by the local 3x3 matrix, turn the
    arrays back so their layout stays where it was in the world, and each
    copy turns or scales around its own origin"""
    inverse = local.inverted_safe()
    for name, values in snapshot:
        modifier = obj.modifiers.get(name)
        for input_name, value in values.items():
            value = inverse @ value
            if input_name == "Axis":
                value.normalize()
            set_input(obj, modifier, input_name, value)


def scale_arrays(obj, factors: Vector):
    """Follow a scale applied to the mesh, so the copies keep their places"""
    for modifier in obj.modifiers:
        kind = array_kind(modifier)
        if kind == "LINEAR":
            set_input(obj, modifier, "Offset", get_input(modifier, "Offset") * factors)
        elif kind == "CIRCULAR":
            set_input(obj, modifier, "Center", get_input(modifier, "Center") * factors)
            set_input(obj, modifier, "Axis", (get_input(modifier, "Axis") * factors).normalized())


def restore_arrays(obj, snapshot):
    for name, values in snapshot:
        modifier = obj.modifiers.get(name)
        for input_name, value in values.items():
            set_input(obj, modifier, input_name, value)


# SETTINGS


def tool_object(context):
    obj = context.active_object
    return obj if obj is not None and obj.type == "MESH" else None


def proxy(kind: str, name: str, default):
    """Get and set for a header field showing an input of the current array,
    so the field can have its own increments"""

    def get(self):
        modifier = current_array(tool_object(bpy.context), kind)
        return get_input(modifier, name) if modifier else default

    def set(self, value):
        obj = tool_object(bpy.context)
        modifier = current_array(obj, kind)
        if modifier:
            set_input(obj, modifier, name, value)

    return get, set


class SCULPT_DECK_PG_array(PropertyGroup):
    orientation: EnumProperty(  # type: ignore
        name="Axis",
        description="Axes the array handles and buttons follow, the array itself doesn't change",
        items=orientation_items,
        default="LOCAL",
    )
    linear_count: IntProperty(  # type: ignore
        name="Count",
        description="Number of copies, counting the mesh itself",
        min=1,
        max=MAX_COUNT,
        get=proxy("LINEAR", "Count", 1)[0],
        set=proxy("LINEAR", "Count", 1)[1],
    )
    circular_count: IntProperty(  # type: ignore
        name="Count",
        description="Number of copies, counting the mesh itself",
        min=1,
        max=MAX_COUNT,
        get=proxy("CIRCULAR", "Count", 1)[0],
        set=proxy("CIRCULAR", "Count", 1)[1],
    )
    # 1° steps, 0.1° with Shift
    arc: FloatProperty(  # type: ignore
        name="Arc",
        description="Angle the copies spread over, a full circle spaces them evenly",
        subtype="ANGLE",
        min=0.0,
        max=math.tau,
        step=100,
        precision=1,
        get=proxy("CIRCULAR", "Arc", math.tau)[0],
        set=proxy("CIRCULAR", "Arc", math.tau)[1],
    )


def settings(context) -> SCULPT_DECK_PG_array:
    return context.scene.sculpt_deck_array  # type: ignore


def axes_basis(obj, orientation: str) -> Matrix:
    """World directions of the X, Y and Z handles"""
    if orientation == "GLOBAL":
        return Matrix.Identity(3)
    return obj.matrix_world.to_3x3().normalized()


# ADDING


def add_array(obj, kind: str, orientation: str, view_rotation):
    """Add an array with copies showing right away"""
    modifier = obj.modifiers.new(kind_names[kind], "NODES")
    modifier.node_group = node_group(kind)
    obj.modifiers.active = modifier
    set_input(obj, modifier, "Count", 3)
    matrix = obj.matrix_world.copy()
    to_local = matrix.to_3x3().inverted_safe()
    size = max(max(obj.dimensions), 1e-3)
    if kind == "LINEAR":
        # copies side by side along X, with a small gap
        direction = axes_basis(obj, orientation).col[0]
        set_input(obj, modifier, "Offset", to_local @ (direction * size * LINEAR_SPACING))
        return modifier

    # a circle facing the view, around where the mesh was; the mesh steps aside
    axis = view_rotation @ Vector((0.0, 0.0, 1.0))
    center = matrix.translation.copy()
    matrix.translation += view_rotation @ Vector((1.0, 0.0, 0.0)) * size * CIRCULAR_RADIUS
    set_world_matrix(obj, matrix, keep_scale=True)
    set_input(obj, modifier, "Axis", (to_local @ axis).normalized())
    set_input(obj, modifier, "Center", matrix.inverted_safe() @ center)
    return modifier


def ensure_array(object_name: str, kind: str, view_rotation):
    """Add an array when a tool starts on a mesh without one, see the tools"""
    obj = bpy.data.objects.get(object_name)
    windows = bpy.context.window_manager.windows
    if obj is None or not windows or obj.type != "MESH" or obj.mode != "SCULPT":
        return
    if current_array(obj, kind) is not None:
        return
    window = windows[0]
    orientation = window.scene.sculpt_deck_array.orientation  # type: ignore
    tool = next(tool for tool, tool_kind in ARRAY_TOOLS.items() if tool_kind == kind)
    add_modifier_step(obj, tool, f"Add {kind_names[kind]}", lambda: add_array(obj, kind, orientation, view_rotation))


def add_modifier_step(obj, tool: str, message: str, add):
    """Run `add`, which adds the tool's modifier to the mesh in Sculpt Mode, as an undo step named `message` that
    undo takes back. Sculpt undo steps don't hold modifiers, so a Scene Checkpoint comes first; with Dyntopo, whose
    "Dynamic topology" steps a checkpoint would be undone to with Dyntopo off, a Hop to Object Mode that is the
    whole action instead (core/hop.py).

    Only while the tool is still active: its gizmos also start again after an undo or redo loads a whole scene step,
    when the tool may be on its way out, its modifier gone (leave_tool_without_modifier)."""
    with bpy.context.temp_override(window=bpy.context.window_manager.windows[0]):
        if active_tool(bpy.context) != tool:
            return
        undone_tools.clear()
        cancel_step_over()
        if obj.use_dynamic_topology_sculpting:
            with hop(bpy.context, "OBJECT", whole_action=True):
                add()
        else:
            store_scene_checkpoint(bpy.context, f"Before {message}")
            add()
        bpy.ops.ed.undo_push(message=message)


ARRAY_TOOLS = {LINEAR_TOOL_ID: "LINEAR", CIRCULAR_TOOL_ID: "CIRCULAR"}
# tools that add a modifier when they start, never handed back to, each with
# how to find its modifier on a mesh; the mirror tool adds itself
modifier_tools = {tool: (lambda obj, kind=kind: current_array(obj, kind)) for tool, kind in ARRAY_TOOLS.items()}
# (tool, mesh) for each modifier undo took away, latest last, for redo to take the tool again with the modifier
undone_tools: list[tuple[str, str]] = []
# (mesh, tools whose modifier it has) before the undo or redo running now
before_step: tuple[str, set[str]] = ("", set())


def active_tool(context) -> str:
    tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
    return tool.idname if tool else ""


def leave_tool(context):
    """Back to the tool used before the array and mirror tools, else the brush"""
    tool = tool_history.previous(context.mode, modifier_tools, "builtin.brush")
    bpy.ops.wm.tool_set_by_id(name=tool, space_type="VIEW_3D")


def in_viewport_later(callback):
    """callback(context) in the 3D viewport, right after the drawing callback or undo step running now"""

    def run():
        windows = bpy.context.window_manager.windows
        if not windows:
            return None
        window = windows[0]
        area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), None)
        with bpy.context.temp_override(window=window, area=area):
            callback(bpy.context)
        return None

    bpy.app.timers.register(run, first_interval=0.0)


def leave_tool_later(tool_id: str):
    """leave_tool() from a drawing callback, when the tool is still active"""

    def leave(context):
        if active_tool(context) == tool_id:
            leave_tool(context)

    in_viewport_later(leave)


def tools_with_modifier(obj) -> set[str]:
    return {tool for tool, find in modifier_tools.items() if find(obj) is not None}


def leave_tool_without_modifier(context):
    """After undo or redo: the tool whose modifier it took away has nothing to edit"""
    obj = context.active_object
    tool = active_tool(context)
    if obj is not None and context.mode == "SCULPT" and tool in modifier_tools and modifier_tools[tool](obj) is None:
        leave_tool(context)


def retake_undone_tool(tool: str):
    """After redo: the tool undo took the modifier of, which redo brought back. Only while the modifier is still
    there: the tool adds one when it starts on a mesh without it."""

    def retake(context):
        if context.mode == "SCULPT" and modifier_tools[tool](context.active_object) is not None:
            bpy.ops.wm.tool_set_by_id(name=tool, space_type="VIEW_3D")

    in_viewport_later(retake)


# after each undo or redo, including the extra ones a Hop makes; the modifiers are read right away, since the
# extra undo or redo can run before a timer, the tool is switched from one
@persistent
def modifiers_before_step(*_):
    global before_step
    obj = active_object()
    before_step = (obj.name, tools_with_modifier(obj)) if obj is not None else ("", set())


def changed_modifiers(obj) -> tuple[set[str], set[str]]:
    """The tools whose modifier the undo or redo just made took away from the active mesh, and brought to it"""
    if obj is None or obj.name != before_step[0]:
        return set(), set()
    now = tools_with_modifier(obj)
    return before_step[1] - now, now - before_step[1]


@persistent
def tool_after_undo(*_):
    obj = active_object()
    undone_tools.extend((tool, obj.name) for tool in changed_modifiers(obj)[0])
    in_viewport_later(leave_tool_without_modifier)


@persistent
def tool_after_redo(*_):
    obj = active_object()
    if undone_tools and undone_tools[-1] in {(tool, obj.name) for tool in changed_modifiers(obj)[1]}:
        retake_undone_tool(undone_tools.pop()[0])
    in_viewport_later(leave_tool_without_modifier)


@persistent
def forget_undone_tools(*_):
    undone_tools.clear()


handlers = (
    (bpy.app.handlers.undo_pre, modifiers_before_step),
    (bpy.app.handlers.redo_pre, modifiers_before_step),
    (bpy.app.handlers.undo_post, tool_after_undo),
    (bpy.app.handlers.redo_post, tool_after_redo),
    (bpy.app.handlers.load_post, forget_undone_tools),
)


def array_poll(context) -> bool:
    obj = context.active_object
    return obj is not None and obj.type == "MESH" and context.mode in object_modes


def apply_modifier(context, modifier):
    """Apply, staying in the current mode where Blender allows it"""
    cancel_step_over()
    obj = context.active_object
    if obj.mode == "SCULPT" and obj.use_dynamic_topology_sculpting:
        # with dynamic topology on, Blender applies with only a warning ("Not supported in dyntopo"): the mesh
        # gets the copies, but the dynamic topology mesh being sculpted doesn't, and overwrites them when Sculpt
        # Mode ends, so the copies are lost. In Object Mode it applies properly, and the Hop turns dynamic
        # topology back on. The apply is the whole action, so undo returns to before it with dynamic topology on.
        with hop(context, "OBJECT", whole_action=True):
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        return
    try:
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    except RuntimeError:
        # wherever else Blender refuses to apply, Object Mode allows it
        with hop(context, "OBJECT"):
            bpy.ops.object.modifier_apply(modifier=modifier.name)


def view_rotation(context):
    space = context.space_data
    if space is not None and space.type == "VIEW_3D":
        return space.region_3d.view_rotation.copy()
    return Matrix.Identity(3).to_quaternion()


# OPERATORS


class ArrayOperator:
    kind: EnumProperty(name="Kind", items=array_kinds)  # type: ignore

    @classmethod
    def poll(cls, context):
        return array_poll(context)

    def leave(self, context, obj):
        # the array tool has nothing left to edit
        kind = ARRAY_TOOLS.get(active_tool(context))
        if kind and current_array(obj, kind) is None:
            leave_tool(context)

    def target(self, context):
        obj = context.active_object
        if self.properties.is_property_set("kind"):
            return obj, current_array(obj, self.kind)
        # from a pie or button: the active array tool's kind, else the active
        # or last array of any kind
        tool = active_tool(context)
        if tool in ARRAY_TOOLS:
            return obj, current_array(obj, ARRAY_TOOLS[tool])
        if array_kind(obj.modifiers.active):
            return obj, obj.modifiers.active
        return obj, next((m for m in reversed(obj.modifiers) if array_kind(m)), None)


class SCULPT_DECK_OT_array_apply(ArrayOperator, Operator):
    """Turn the array's copies into real mesh, so each one can be sculpted on its own"""

    bl_label = "Apply Array"
    bl_idname = "sculpt_deck.array_apply"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj, modifier = self.target(context)
        if modifier is None:
            return CANCEL
        realize(obj, modifier)
        apply_modifier(context, modifier)
        self.leave(context, obj)
        return FINISHED


class SCULPT_DECK_OT_array_remove(ArrayOperator, Operator):
    """Remove the array, keeping only the mesh itself"""

    bl_label = "Remove Array"
    bl_idname = "sculpt_deck.array_remove"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj, modifier = self.target(context)
        if modifier is None:
            return CANCEL
        obj.modifiers.remove(modifier)
        self.leave(context, obj)
        return FINISHED


class SCULPT_DECK_OT_array_axis(Operator):
    """Turn the copies around an axis"""

    bl_label = "Circle Axis"
    bl_idname = "sculpt_deck.array_axis"
    bl_options = {"REGISTER", "UNDO"}

    axis: EnumProperty(  # type: ignore
        name="Axis",
        items=[*[(axis, axis, "", i) for i, axis in enumerate(AXES)], ("VIEW", "View", "", 3)],
        default="Z",
    )
    orientation: EnumProperty(name="Orientation", items=orientation_items, options={"SKIP_SAVE"})  # type: ignore
    view: FloatVectorProperty(default=(0, 0, 1), options={"HIDDEN", "SKIP_SAVE"})  # type: ignore

    @classmethod
    def poll(cls, context):
        return array_poll(context) and current_array(context.active_object, "CIRCULAR") is not None

    @classmethod
    def description(cls, context, properties):
        if properties.axis == "VIEW":
            return "Face the circle to the current view. It stays put when the view changes, click again to update it"
        where = "the world's" if settings(context).orientation == "GLOBAL" else "the object's"
        return f"Turn the copies around {where} {properties.axis} axis"

    def invoke(self, context, event):
        self.orientation = settings(context).orientation
        self.view = view_rotation(context) @ Vector((0.0, 0.0, 1.0))
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object
        modifier = current_array(obj, "CIRCULAR")
        if self.axis == "VIEW":
            world = Vector(self.view)
        else:
            world = axes_basis(obj, self.orientation).col[AXIS_INDEX[self.axis]]
        axis = (obj.matrix_world.to_3x3().inverted_safe() @ world).normalized()
        # keep the radius, with the center moved across the new axis
        center = get_input(modifier, "Center")
        across = center - center.project(axis)
        if across.length < 1e-6:
            across = axis.orthogonal()
        set_input(obj, modifier, "Center", across.normalized() * center.length)
        set_input(obj, modifier, "Axis", axis)
        return FINISHED


array_handles = [
    ("OFFSET", "Offset", "Distance between copies of a linear array", 0),
    ("LINEAR_COUNT", "Count", "Copies of a linear array", 1),
    ("CENTER", "Center", "Center of a circular array", 2),
    ("MOVE", "Move", "Move the mesh around the center of a circular array", 3),
    ("RADIUS", "Radius", "Radius of a circular array", 4),
    ("CIRCULAR_COUNT", "Count", "Copies of a circular array", 5),
    ("ARC", "Arc", "Arc of a circular array", 6),
]

drag_axes = [
    ("X", "X", "", 0),
    ("Y", "Y", "", 1),
    ("Z", "Z", "", 2),
    ("VIEW", "View", "In the view plane", 3),
]


class SCULPT_DECK_OT_array_edit(ViewDrag, Operator):
    """Drag to change the array"""

    bl_label = "Edit Array"
    bl_idname = "sculpt_deck.array_edit"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    handle: EnumProperty(name="Handle", items=array_handles)  # type: ignore
    axis: EnumProperty(name="Axis", items=drag_axes, default="VIEW")  # type: ignore
    # the gizmos show the steps of an arc drag
    active_handle = ""
    arc_step = ARC_COARSE

    # results, kept for Adjust Last Operation
    vector: FloatVectorProperty(name="Value", subtype="TRANSLATION", options={"SKIP_SAVE"})  # type: ignore
    location: FloatVectorProperty(name="Location", subtype="TRANSLATION", options={"SKIP_SAVE"})  # type: ignore
    count: IntProperty(name="Count", min=1, max=MAX_COUNT, options={"SKIP_SAVE"})  # type: ignore
    arc: FloatProperty(name="Arc", subtype="ANGLE", min=0, max=math.tau, options={"SKIP_SAVE"})  # type: ignore
    moves_object: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore
    modifier: StringProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore

    @classmethod
    def poll(cls, context):
        return array_poll(context)

    @classmethod
    def description(cls, context, properties):
        # each gizmo starts this operator, so this is the gizmo's tooltip
        handle, axis = properties.handle, properties.axis
        if handle == "OFFSET":
            if axis == "VIEW":
                return "Drag to change the distance between copies"
            return f"Drag to change the distance between copies along the {axis} axis"
        return {
            "LINEAR_COUNT": "Drag along the line to add or remove copies",
            "CENTER": "Drag to move the center of the circle, the mesh stays in place",
            "MOVE": "Drag to move the mesh, the center of the circle stays in place",
            "RADIUS": "Drag to move the mesh closer to or away from the center",
            "CIRCULAR_COUNT": "Drag around the circle to add copies, back to remove them",
            "ARC": "Drag around the circle to change the arc the copies spread over.\n"
            "Inside the circle it moves in 15° steps, outside it in 1° steps",
        }[handle]

    def kind(self) -> str:
        return "LINEAR" if self.handle in {"OFFSET", "LINEAR_COUNT"} else "CIRCULAR"

    def target(self, context):
        obj = context.active_object
        if self.modifier:
            return obj, obj.modifiers.get(self.modifier)
        return obj, current_array(obj, self.kind())

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        if self.handle in {"LINEAR_COUNT", "CIRCULAR_COUNT"}:
            layout.prop(self, "count")
        elif self.handle == "ARC":
            layout.prop(self, "arc")
        else:
            layout.prop(self, "vector", text="Offset" if self.handle == "OFFSET" else "Center")
            if self.moves_object:
                layout.prop(self, "location")

    def execute(self, context):
        obj, modifier = self.target(context)
        if modifier is None:
            return CANCEL
        self.write(obj, modifier)
        return FINISHED

    def write(self, obj, modifier):
        if self.handle in {"LINEAR_COUNT", "CIRCULAR_COUNT"}:
            set_input(obj, modifier, "Count", self.count)
        elif self.handle == "ARC":
            set_input(obj, modifier, "Arc", self.arc)
        else:
            if self.moves_object:
                matrix = obj.matrix_world.copy()
                matrix.translation = self.location
                set_world_matrix(obj, matrix, keep_scale=True)
            set_input(obj, modifier, "Offset" if self.handle == "OFFSET" else "Center", Vector(self.vector))

    def invoke(self, context, event):
        obj, modifier = self.target(context)
        region, rv3d = context.region, context.region_data
        if modifier is None or context.area is None or context.area.type != "VIEW_3D" or rv3d is None:
            return CANCEL
        self.modifier = modifier.name
        self.start_matrix = obj.matrix_world.copy()
        self.start_count = self.count = get_input(modifier, "Count")
        self.moves_object = self.handle in {"MOVE", "RADIUS"}
        type(self).active_handle = self.handle
        self.location = self.start_matrix.translation
        matrix = self.start_matrix

        if self.kind() == "LINEAR":
            self.start_vector = get_input(modifier, "Offset")
            self.vector = self.start_vector
            if self.handle == "LINEAR_COUNT":
                self.point = matrix @ (self.start_vector * (self.start_count - 1))
                self.direction = matrix.to_3x3() @ self.start_vector
            else:
                self.point = matrix @ self.start_vector
                if self.axis != "VIEW":
                    self.direction = axes_basis(obj, settings(context).orientation).col[AXIS_INDEX[self.axis]]
            if self.handle == "LINEAR_COUNT" or self.axis != "VIEW":
                self.screen_axis = axis_on_screen(region, rv3d, self.point, self.direction)
            return self.start_drag(context, event)

        self.start_vector = get_input(modifier, "Center")
        self.vector = self.start_vector
        self.start_arc = self.arc = get_input(modifier, "Arc")
        self.center = matrix @ self.start_vector
        origin = matrix.translation
        axis = (matrix.to_3x3() @ get_input(modifier, "Axis")).normalized()
        if self.handle == "RADIUS":
            self.outward = origin - self.center
            if self.outward.length < 1e-6:
                self.outward = axis.orthogonal()
            self.radius = self.outward.length
            self.outward.normalize()
            self.screen_axis = axis_on_screen(region, rv3d, origin, self.outward)
        elif self.handle in {"CIRCULAR_COUNT", "ARC"}:
            center = view3d_utils.location_3d_to_region_2d(region, rv3d, self.center)
            if center is None:
                center = Vector((region.width / 2, region.height / 2))
            self.turn = ScreenAngle(center, Vector((event.mouse_region_x, event.mouse_region_y)))
            self.sign = facing_sign(rv3d, self.center, axis)
            # the circle's radius on screen
            outward = origin - self.center
            outward -= outward.project(axis)
            if outward.length < 1e-6:
                outward = axis.orthogonal()
            edge = view3d_utils.location_3d_to_region_2d(region, rv3d, self.center + outward)
            self.circle_pixels = (edge - center).length if edge is not None else 0.0
        return self.start_drag(context, event)

    def drag(self, context, mouse: Vector, snap: bool):
        obj, modifier = self.target(context)
        region, rv3d = context.region, context.region_data
        handle = self.handle
        if handle == "LINEAR_COUNT":
            length = self.direction.length
            distance = distance_along(self.screen_axis, self.start_mouse, mouse)
            steps = round(distance / length) if length > 1e-9 else 0
            self.count = max(1, min(MAX_COUNT, self.start_count + steps))
        elif handle in {"CIRCULAR_COUNT", "ARC"}:
            angle = self.turn.update(mouse) * self.sign
            if handle == "ARC":
                inside = (mouse - self.turn.center).length <= self.circle_pixels
                step = ARC_COARSE if inside else ARC_FINE
                type(self).arc_step = step
                self.arc = max(0.0, min(math.tau, round((self.start_arc + angle) / step) * step))
            else:
                # the same way round as the arc grows
                count = self.start_count + round(angle / COUNT_TURN)
                self.count = max(1, min(MAX_COUNT, count))
        elif handle in {"OFFSET", "CENTER"}:
            point = self.point if handle == "OFFSET" else self.center
            if self.axis == "VIEW":
                offset = view_plane_offset(region, rv3d, point, self.start_mouse, mouse)
            else:
                offset = self.direction * distance_along(self.screen_axis, self.start_mouse, mouse)
            vector = self.start_matrix.inverted_safe() @ (point + offset)
            if snap:
                vector = Vector(round(v / SNAP_DISTANCE) * SNAP_DISTANCE for v in vector)
            self.vector = vector
        else:
            origin = self.start_matrix.translation
            if handle == "MOVE":
                new_origin = origin + view_plane_offset(region, rv3d, origin, self.start_mouse, mouse)
                center = self.center
            else:
                radius = self.radius + distance_along(self.screen_axis, self.start_mouse, mouse)
                if snap:
                    radius = round(radius / SNAP_DISTANCE) * SNAP_DISTANCE
                radius = max(radius, 1e-3)
                if self.moves_object:
                    new_origin, center = self.center + self.outward * radius, self.center
                else:
                    new_origin, center = origin, origin - self.outward * radius
            matrix = self.start_matrix.copy()
            matrix.translation = new_origin
            self.location = new_origin
            # the center stays where it is in the world when the mesh moves
            self.vector = matrix.inverted_safe() @ center
        self.write(obj, modifier)

    def restore(self, context):
        obj, modifier = self.target(context)
        obj.matrix_world = self.start_matrix
        set_input(obj, modifier, "Count", self.start_count)
        if self.kind() == "LINEAR":
            set_input(obj, modifier, "Offset", self.start_vector)
        else:
            set_input(obj, modifier, "Center", self.start_vector)
            set_input(obj, modifier, "Arc", self.start_arc)

    def is_identity(self) -> bool:
        if self.handle in {"LINEAR_COUNT", "CIRCULAR_COUNT"}:
            return self.count == self.start_count
        if self.handle == "ARC":
            return self.arc == self.start_arc
        moved = (Vector(self.location) - self.start_matrix.translation).length > 1e-9
        return (Vector(self.vector) - self.start_vector).length < 1e-9 and not moved

    def header_text(self) -> str:
        if self.handle in {"LINEAR_COUNT", "CIRCULAR_COUNT"}:
            return f"Count: {self.count}"
        if self.handle == "ARC":
            return f"Arc: {math.degrees(self.arc):.1f}°"
        if self.handle == "RADIUS":
            # the origin is on the circle, so the center's distance is the radius
            return f"Radius: {Vector(self.vector).length:.4f}"
        x, y, z = self.vector
        return f"{'Offset' if self.handle == 'OFFSET' else 'Center'}  {x:.4f}  {y:.4f}  {z:.4f}"


classes = (
    SCULPT_DECK_PG_array,
    SCULPT_DECK_OT_array_apply,
    SCULPT_DECK_OT_array_remove,
    SCULPT_DECK_OT_array_axis,
    SCULPT_DECK_OT_array_edit,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.sculpt_deck_array = PointerProperty(type=SCULPT_DECK_PG_array)  # type: ignore
    for handler_list, handler in handlers:
        handler_list.append(handler)


def unregister():
    for handler_list, handler in handlers:
        if handler in handler_list:
            handler_list.remove(handler)
    del bpy.types.Scene.sculpt_deck_array  # type: ignore
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
