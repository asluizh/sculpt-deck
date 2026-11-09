"""Modifiers of meshes about to be combined: whether two meshes' modifiers draw the same, and applying them.

Joining keeps only the active mesh's modifiers, which then act on everything joined into it. A mesh whose modifiers
draw what the active's would draw on it can be joined as it is; any other mesh's modifiers are applied first, so it
keeps the look it had. Only modifiers shown in the viewport count: hidden ones draw nothing.
"""

import bpy
from mathutils import Matrix, Vector

from ..array.operators import array_kind, get_input, set_input
from ..mirror.operators import AXES, is_mirror

# how far apart two values may be and still count as the same
TOLERANCE = 1e-4

# modifier settings that don't change what it draws
UI_SETTINGS = {
    "rna_type",
    "name",
    "show_viewport",
    "show_render",
    "show_in_editmode",
    "show_on_cage",
    "show_expanded",
    "is_active",
    "is_override_data_local",
    "use_pin_to_last",
    "persistent_uid",
    "execution_time",
    "use_apply_on_spline",
}


def shown(obj) -> list:
    return [modifier for modifier in obj.modifiers if modifier.show_viewport]


def drawing(obj, modifier) -> tuple:
    """What the modifier draws, in terms that compare across objects.

    The arrays' vectors are in the object's space, so they're compared in the world: two arrays whose copies step
    the same way in the world draw the same on a mesh joined from one object into the other. The mirror's planes are
    in the world already. Any other modifier is compared by its settings, and on an object placed exactly the same,
    since its settings are in the object's space too.
    """
    kind = array_kind(modifier)
    rotation_scale = obj.matrix_world.to_3x3()
    if kind == "LINEAR":
        return (kind, get_input(modifier, "Count"), rotation_scale @ get_input(modifier, "Offset"))
    if kind == "CIRCULAR":
        return (
            kind,
            get_input(modifier, "Count"),
            get_input(modifier, "Arc"),
            obj.matrix_world @ get_input(modifier, "Center"),
            (rotation_scale @ get_input(modifier, "Axis")).normalized(),
        )
    if is_mirror(modifier):
        return (
            "MIRROR",
            *(get_input(modifier, axis) for axis in AXES),
            get_input(modifier, "Mirror Object"),
            get_input(modifier, "Merge Distance"),
        )
    return (modifier.type, settings(modifier), obj.matrix_world)


def settings(modifier) -> tuple:
    if modifier.type == "NODES":
        return (modifier.node_group, node_inputs(modifier))
    values = []
    for prop in modifier.bl_rna.properties:
        if prop.identifier in UI_SETTINGS:
            continue
        value = getattr(modifier, prop.identifier)
        if prop.type == "POINTER" and value is not None and not isinstance(value, bpy.types.ID):
            # settings of their own (a falloff curve, say): only the same ones count as the same
            value = value.as_pointer()
        elif prop.type == "COLLECTION":
            value = tuple(item.as_pointer() for item in value)
        elif getattr(prop, "is_array", False):
            value = tuple(value)
        values.append(value)
    return tuple(values)


def node_inputs(modifier) -> tuple:
    values = []
    for item in modifier.node_group.interface.items_tree if modifier.node_group else ():
        if item.item_type != "SOCKET" or item.in_out != "INPUT" or item.socket_type == "NodeSocketGeometry":
            continue
        try:
            value = getattr(modifier.properties.inputs, item.identifier).value
        except AttributeError:
            # an input this code can't read: only the very same modifier counts as the same
            value = modifier.as_pointer()
        values.append(tuple(value) if hasattr(value, "__len__") and not isinstance(value, str) else value)
    return tuple(values)


def close(a, b) -> bool:
    if isinstance(a, Matrix) and isinstance(b, Matrix):
        return all(close(tuple(row_a), tuple(row_b)) for row_a, row_b in zip(a, b))
    if isinstance(a, (tuple, list, Vector)) and isinstance(b, (tuple, list, Vector)):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= TOLERANCE
    return a == b


def draws_like(active, other) -> bool:
    """Whether the active mesh's modifiers, acting on `other` once joined, draw what `other`'s own draw"""
    mine, theirs = shown(active), shown(other)
    return len(mine) == len(theirs) and all(
        close(drawing(active, a), drawing(other, b)) for a, b in zip(mine, theirs)
    )


def apply_blocker(objects) -> str:
    """Why the shown modifiers of these objects can't be applied, or "" when they can"""
    for obj in objects:
        if shown(obj) and obj.data.shape_keys is not None:
            return f"{obj.name} has shape keys, so its modifiers can't be applied"
    return ""


def apply_shown(context, obj):
    """Apply the object's shown modifiers, in stack order, in Object Mode. Arrays and mirrors make their copies and
    mirror image real mesh first, as Apply Array and Apply Mirror do."""
    if not shown(obj):
        return
    if obj.data.users > 1:
        # Blender won't apply to a mesh other objects use too; those keep theirs
        obj.data = obj.data.copy()
    with context.temp_override(object=obj, active_object=obj):
        for modifier in shown(obj):
            if array_kind(modifier) or is_mirror(modifier):
                set_input(obj, modifier, "Realize", True)
            bpy.ops.object.modifier_apply(modifier=modifier.name)
