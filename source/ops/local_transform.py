import json
import math

import bpy
import numpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, PointerProperty, StringProperty)
from bpy.types import Operator, PropertyGroup
from bpy_extras import view3d_utils
from mathutils import Matrix, Vector

from ..utils.constants import CANCEL, FINISHED, object_modes
from .array import array_snapshot, keep_arrays, restore_arrays, scale_arrays
from .drag import (ViewDrag, axis_on_screen, distance_along,
                   set_world_matrix, view_plane_offset)

###
# Local Transform
#  Moves, rotates and scales the whole object (its location, rotation and
#  scale) instead of its vertices like Blender's Sculpt Mode transform tools,
#  so the origin stays with the mesh and later rotations still turn around it.
#  Scaling happens along the object's own axes and is applied to the mesh
#  right away, so rotating between two stretches can't skew it and brushes
#  never work on a stretched object.
###

TOOL_ID = "touchview.local_transform"

local_pivot_items = [
    ("ORIGIN", "Origin", "Transform around the active object's origin", "OBJECT_ORIGIN", 0),
    ("BOUNDS", "Bounding Box Center", "Transform around the center of the selected objects' bounds", "PIVOT_BOUNDBOX", 1),
    ("CURSOR", "3D Cursor", "Transform around the 3D cursor", "PIVOT_CURSOR", 2),
    (
        "INSTANCES",
        "Instances",
        "Rotate and scale every selected object and array copy around its own origin, the array's layout stays in place",
        "PIVOT_INDIVIDUAL",
        3,
    ),
]

orientation_items = [
    ("GLOBAL", "Global", "Move and rotate along the world axes", "ORIENTATION_GLOBAL", 0),
    ("LOCAL", "Local", "Move and rotate along the object's own axes", "ORIENTATION_LOCAL", 1),
]

transform_modes = [
    ("MOVE", "Move", "", "CON_LOCLIKE", 0),
    ("ROTATE", "Rotate", "", "CON_ROTLIKE", 1),
    ("SCALE", "Scale", "", "CON_SIZELIKE", 2),
]

transform_axes = [
    ("X", "X", "The X axis", 0),
    ("Y", "Y", "The Y axis", 1),
    ("Z", "Z", "The Z axis", 2),
    ("VIEW", "View", "Move in the view plane, rotate around the view axis, or scale on every axis", 3),
]

AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}

SNAP_ANGLE = math.radians(5)
SNAP_FACTOR = 0.1
SNAP_DISTANCE = 0.1


class TOUCHVIEW_PG_local_transform(PropertyGroup):
    pivot: EnumProperty(  # type: ignore
        name="Pivot",
        description="Point the object rotates and scales around",
        items=local_pivot_items,
        default="INSTANCES",
    )
    orientation: EnumProperty(  # type: ignore
        name="Axis",
        description="Axes the handles move and rotate along. Scaling always follows the object's own axes",
        items=orientation_items,
        default="LOCAL",
    )
    show_move: BoolProperty(name="Move", description="Show the move handles", default=True)  # type: ignore
    show_rotate: BoolProperty(name="Rotate", description="Show the rotation rings", default=True)  # type: ignore
    show_scale: BoolProperty(name="Scale", description="Show the scale handles", default=True)  # type: ignore


def settings(context) -> TOUCHVIEW_PG_local_transform:
    return context.scene.touchview_local_transform  # type: ignore


def transform_objects(context) -> list:
    """The objects Local Transform works on: the active one first, then the other selected ones. Children of
    those are left out, they follow their parents."""
    active = context.active_object
    objects = [active] if active is not None else []
    objects += [obj for obj in context.selected_objects if obj != active]
    chosen = set(objects)

    def has_chosen_parent(obj):
        parent = obj.parent
        while parent is not None:
            if parent in chosen:
                return True
            parent = parent.parent
        return False

    return [obj for obj in objects if not has_chosen_parent(obj)]


def pivot_point(context, objects: list) -> Vector:
    """Where the handles sit, and what Origin, Bounding Box Center and 3D Cursor turn and scale around. Origin is
    the active object's; with Instances, each object turns around its own origin instead."""
    pivot = settings(context).pivot
    if pivot == "CURSOR":
        return context.scene.cursor.location.copy()
    if pivot == "BOUNDS":
        corners = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
        low = Vector([min(corner[i] for corner in corners) for i in range(3)])
        high = Vector([max(corner[i] for corner in corners) for i in range(3)])
        return (low + high) / 2
    return objects[0].matrix_world.translation.copy()


def unit_scale(obj) -> bool:
    return all(abs(factor - 1.0) < 1e-5 for factor in obj.scale)


def apply_scale(context, obj) -> bool:
    """Bake the object's scale into its mesh, staying in the current mode"""
    if obj.type != "MESH":
        return True
    if unit_scale(obj):
        # no more than rounding left over from matrix math
        obj.scale = (1.0, 1.0, 1.0)
        return True
    if obj.data.users > 1:
        return False
    # arrays are in the object's space, they scale with the mesh
    scale_arrays(obj, Vector(obj.scale))
    multires = any(modifier.type == "MULTIRES" for modifier in obj.modifiers)
    dyntopo = context.mode == "SCULPT" and obj.use_dynamic_topology_sculpting
    if multires or dyntopo or obj.children:
        # Blender's own apply handles multires displacement, dyntopo's
        # separate mesh and keeping children in place, but only in Object Mode
        mode = object_modes[context.mode]
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        selected = [other for other in context.selected_objects if other != obj]
        for other in selected:
            other.select_set(False)
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        for other in selected:
            other.select_set(True)
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode=mode)
        return True
    obj.data.transform(Matrix.Diagonal(Vector(obj.scale).to_4d()), shape_keys=True)
    obj.scale = (1.0, 1.0, 1.0)
    obj.data.update()
    return True


def local_size(obj) -> Vector:
    """Size of the mesh itself in the object's space, without modifiers"""
    if obj.type != "MESH" or not obj.data.vertices:
        return Vector()
    positions = numpy.empty(len(obj.data.vertices) * 3, dtype=numpy.float32)
    obj.data.vertices.foreach_get("co", positions)
    positions = positions.reshape(-1, 3)
    return Vector((positions.max(axis=0) - positions.min(axis=0)).tolist())


def moved(matrix: Matrix, offset: Vector) -> Matrix:
    result = matrix.copy()
    result.translation += offset
    return result


def rotated(matrix: Matrix, pivot: Vector, axis: Vector, angle: float) -> Matrix:
    return Matrix.Translation(pivot) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-pivot) @ matrix


def scaled(matrix: Matrix, pivot: Vector, factors: Vector) -> Matrix:
    """Scale along the object's own axes, keeping the pivot in place"""
    local_pivot = matrix.inverted_safe() @ pivot
    result = matrix @ Matrix.Diagonal(factors.to_4d())
    result.translation += pivot - result @ local_pivot
    return result


class TOUCHVIEW_OT_local_transform(ViewDrag, Operator):
    """Move, rotate or scale the whole object, staying in the current mode"""

    bl_label = "Local Transform"
    bl_idname = "touchview.local_transform"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    status = "Drag to transform  •  Release/Click: Confirm  •  Right Click/Esc: Cancel  •  Ctrl: Snap"

    mode: EnumProperty(name="Mode", items=transform_modes, default="MOVE")  # type: ignore
    axis: EnumProperty(name="Axis", items=transform_axes, default="X")  # type: ignore
    orientation: EnumProperty(  # type: ignore
        name="Orientation",
        items=orientation_items,
        default="LOCAL",
        options={"SKIP_SAVE"},
    )
    distance: FloatProperty(name="Distance", subtype="DISTANCE", options={"SKIP_SAVE"})  # type: ignore
    offset: FloatVectorProperty(name="Offset", subtype="TRANSLATION", options={"SKIP_SAVE"})  # type: ignore
    angle: FloatProperty(name="Angle", subtype="ANGLE", options={"SKIP_SAVE"})  # type: ignore
    factor: FloatProperty(name="Factor", default=1.0, min=0.001, options={"SKIP_SAVE"})  # type: ignore
    # filled on invoke, so Adjust Last Operation keeps the same pivot and view
    pivot: FloatVectorProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore
    view_axis: FloatVectorProperty(default=(0, 0, 1), options={"HIDDEN", "SKIP_SAVE"})  # type: ignore
    use_pivot: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore
    instances: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore
    # the objects and where they started, filled on the first run, so Adjust Last Operation starts from there too.
    # Undo steps made in Sculpt Mode don't hold object transforms, so the step Adjust Last Operation goes back to
    # can leave the objects where they were long before (as far back as entering Sculpt Mode)
    use_start: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore
    start_state: StringProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    @classmethod
    def description(cls, context, properties):
        # each gizmo starts this operator, so this is the gizmo's tooltip
        mode, axis = properties.mode, properties.axis
        if properties.is_property_set("orientation"):
            orientation = properties.orientation
        else:
            orientation = settings(context).orientation
        if mode == "SCALE":
            if axis == "VIEW":
                return "Scale evenly on every axis"
            return f"Stretch along the object's {axis} axis"
        if axis == "VIEW":
            return "Move freely in the view plane" if mode == "MOVE" else "Rotate around the view axis"
        where = "the world" if orientation == "GLOBAL" else "the object's"
        if mode == "MOVE":
            return f"Move along {where} {axis} axis"
        return f"Rotate around {where} {axis} axis"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "mode")
        layout.prop(self, "axis")
        if self.mode != "SCALE" and self.axis != "VIEW":
            layout.prop(self, "orientation")
        if self.mode == "MOVE":
            layout.prop(self, "offset" if self.axis == "VIEW" else "distance")
        elif self.mode == "ROTATE":
            layout.prop(self, "angle")
        else:
            layout.prop(self, "factor")

    def world_axis(self, matrix: Matrix) -> Vector:
        if self.axis == "VIEW":
            return Vector(self.view_axis).normalized()
        index = AXIS_INDEX[self.axis]
        # scaling only works along the object's axes, it can't shear the object
        if self.orientation == "GLOBAL" and self.mode != "SCALE":
            return Matrix.Identity(3).col[index]
        return matrix.col[index].xyz.normalized()

    def transformed(self, matrix: Matrix) -> Matrix:
        """Where an object starting at the matrix ends up. Moves and rotations follow the active object's axes,
        scaling follows each object's own"""
        pivot = matrix.translation if self.instances else Vector(self.pivot)
        if self.mode == "MOVE":
            if self.axis == "VIEW":
                return moved(matrix, Vector(self.offset))
            return moved(matrix, self.world_axis(self.start) * self.distance)
        if self.mode == "ROTATE":
            return rotated(matrix, pivot, self.world_axis(self.start), self.angle)
        factors = Vector((1.0, 1.0, 1.0))
        if self.axis == "VIEW":
            factors *= self.factor
        else:
            factors[AXIS_INDEX[self.axis]] = self.factor
        return scaled(matrix, pivot, factors)

    def is_identity(self) -> bool:
        if self.mode == "MOVE":
            return Vector(self.offset).length == 0 if self.axis == "VIEW" else self.distance == 0
        if self.mode == "ROTATE":
            return self.angle == 0
        return self.factor == 1

    def use_settings(self, context):
        if not self.properties.is_property_set("orientation"):
            self.orientation = settings(context).orientation

    def execute(self, context):
        self.use_settings(context)
        if not self.use_pivot:
            self.pivot = pivot_point(context, transform_objects(context))
            self.use_pivot = True
            self.instances = settings(context).pivot == "INSTANCES"
        self.begin(context)
        if not self.targets:
            return CANCEL
        self.set_matrices()
        if self.mode == "SCALE":
            self.apply_scale(context)
        return FINISHED

    def begin(self, context):
        """Fill self.targets with (object, start matrix, array snapshot), the active object first"""
        if self.use_start:
            # run again by Adjust Last Operation: put the objects back where this operation started
            self.targets = []
            states = json.loads(self.start_state or "{}")
            for state in states.get("objects", []):
                obj = bpy.data.objects.get(state["name"])
                if obj is None:
                    continue
                start = Matrix([state["matrix"][row * 4:row * 4 + 4] for row in range(4)])
                obj.matrix_world = start
                arrays = [(name, {key: Vector(value) for key, value in values.items()})
                          for name, values in state["arrays"] if name in obj.modifiers]
                restore_arrays(obj, arrays)
                self.restore_mesh_size(obj, Vector(state["size"]))
                self.targets.append((obj, start, arrays))
            # applying a parent's scale changes its children's own transforms
            for name, matrix in states.get("children", []):
                child = bpy.data.objects.get(name)
                if child is not None:
                    child.matrix_world = Matrix([matrix[row * 4:row * 4 + 4] for row in range(4)])
        else:
            self.targets = [(obj, obj.matrix_world.copy(), array_snapshot(obj)) for obj in transform_objects(context)]
            flat = lambda matrix: [value for row in matrix for value in row]  # noqa: E731
            self.start_state = json.dumps({
                "objects": [
                    {
                        "name": obj.name,
                        "matrix": flat(start),
                        "arrays": [(name, {key: list(value) for key, value in values.items()})
                                   for name, values in arrays],
                        "size": list(local_size(obj)),
                    }
                    for obj, start, arrays in self.targets
                ],
                "children": [
                    (child.name, flat(child.matrix_world))
                    for obj, _, _ in self.targets for child in obj.children_recursive
                ],
            })
            self.use_start = True
        # the active object's start sets the handles' axes
        self.start = self.targets[0][1] if self.targets else Matrix.Identity(4)

    def restore_mesh_size(self, obj, start_size: Vector):
        """Take back a scale this operation applied to the mesh, when going back a step didn't"""
        if self.mode != "SCALE" or obj.type != "MESH" or obj.data.users > 1:
            return
        if obj.use_dynamic_topology_sculpting or any(m.type == "MULTIRES" for m in obj.modifiers):
            # Blender's own apply was used, see apply_scale
            return
        size = local_size(obj)
        ratios = Vector([s / c if s > 1e-9 and c > 1e-9 else 1.0 for s, c in zip(start_size, size)])
        if all(abs(ratio - 1.0) < 1e-5 for ratio in ratios):
            return
        obj.data.transform(Matrix.Diagonal(ratios.to_4d()), shape_keys=True)
        obj.data.update()

    def set_matrices(self):
        for obj, start, arrays in self.targets:
            matrix = self.transformed(start)
            set_world_matrix(obj, matrix, keep_scale=self.mode != "SCALE")
            if self.instances and arrays and self.mode != "MOVE":
                keep_arrays(obj, arrays, start.to_3x3().inverted_safe() @ matrix.to_3x3())

    def apply_scale(self, context):
        context.view_layer.update()
        if not all([apply_scale(context, obj) for obj, _, _ in self.targets]):
            self.report({"WARNING"}, "Scale not applied to meshes shared with other objects")


    def invoke(self, context, event):
        region, rv3d = context.region, context.region_data
        if context.area is None or context.area.type != "VIEW_3D" or rv3d is None:
            return self.execute(context)
        self.use_settings(context)
        self.pivot = pivot_point(context, transform_objects(context))
        self.use_pivot = True
        self.instances = settings(context).pivot == "INSTANCES"
        self.use_start = False
        self.begin(context)
        self.view_axis = rv3d.view_rotation @ Vector((0.0, 0.0, 1.0))

        pivot = Vector(self.pivot)
        center = view3d_utils.location_3d_to_region_2d(region, rv3d, pivot)
        self.center = center if center is not None else Vector((region.width / 2, region.height / 2))
        self.previous = Vector((event.mouse_region_x, event.mouse_region_y)) - self.center
        self.screen_angle = 0.0
        self.screen_axis = axis_on_screen(region, rv3d, pivot, self.world_axis(self.start))
        return self.start_drag(context, event)

    def restore(self, context):
        for obj, start, arrays in self.targets:
            obj.matrix_world = start
            restore_arrays(obj, arrays)

    def confirmed(self, context):
        if self.mode == "SCALE":
            self.apply_scale(context)

    def drag(self, context, mouse: Vector, snap: bool):
        if self.mode == "MOVE":
            self.update_move(context, mouse, snap)
        elif self.mode == "ROTATE":
            self.update_rotate(context, mouse, snap)
        else:
            self.update_scale(mouse, snap)
        self.set_matrices()

    def update_move(self, context, mouse: Vector, snap: bool):
        if self.axis == "VIEW":
            region, rv3d = context.region, context.region_data
            self.offset = view_plane_offset(region, rv3d, Vector(self.pivot), self.start_mouse, mouse)
            return
        distance = distance_along(self.screen_axis, self.start_mouse, mouse)
        if snap:
            distance = round(distance / SNAP_DISTANCE) * SNAP_DISTANCE
        self.distance = distance

    def update_rotate(self, context, mouse: Vector, snap: bool):
        current = mouse - self.center
        if current.length > 2 and self.previous.length > 2:
            # counter-clockwise on screen, accumulated so it can turn past 180°
            self.screen_angle -= self.previous.angle_signed(current)
            self.previous = current
        elif self.previous.length <= 2:
            self.previous = current
        rv3d = context.region_data
        if rv3d.is_perspective:
            toward_viewer = rv3d.view_matrix.inverted().translation - Vector(self.pivot)
        else:
            toward_viewer = Vector(self.view_axis)
        sign = 1.0 if self.world_axis(self.start).dot(toward_viewer) >= 0 else -1.0
        angle = self.screen_angle * sign
        if snap:
            angle = round(angle / SNAP_ANGLE) * SNAP_ANGLE
        self.angle = angle

    def update_scale(self, mouse: Vector, snap: bool):
        start, current = self.start_mouse - self.center, mouse - self.center
        if self.axis == "VIEW":
            factor = current.length / max(start.length, 20.0)
        else:
            direction = self.screen_axis.normalized()
            start_along, along = start.dot(direction), current.dot(direction)
            if abs(start_along) >= 20:
                factor = along / start_along
            else:
                factor = 1.0 + (along - start_along) / 100
        if snap:
            factor = round(factor / SNAP_FACTOR) * SNAP_FACTOR
        self.factor = max(factor, 0.001)

    def header_text(self) -> str:
        if self.axis == "VIEW":
            axis = "View"
        elif self.orientation == "GLOBAL" and self.mode != "SCALE":
            axis = f"Global {self.axis}"
        else:
            axis = f"Local {self.axis}"
        if self.mode == "MOVE":
            if self.axis == "VIEW":
                x, y, z = self.offset
                return f"Move  {x:.4f}  {y:.4f}  {z:.4f}"
            return f"Move along {axis}: {self.distance:.4f}"
        if self.mode == "ROTATE":
            return f"Rotate around {axis}: {math.degrees(self.angle):.2f}°"
        if self.axis == "VIEW":
            return f"Scale: {self.factor:.4f}"
        return f"Scale along {axis}: {self.factor:.4f}"


class TOUCHVIEW_OT_apply_object_scale(Operator):
    """Apply the scale of the active and selected objects to their meshes, so brushes aren't stretched, staying in
    the current mode"""

    bl_label = "Apply Scale"
    bl_idname = "touchview.apply_object_scale"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and context.mode in object_modes

    def execute(self, context):
        meshes = [obj for obj in transform_objects(context) if obj.type == "MESH"]
        if not all([apply_scale(context, obj) for obj in meshes]):
            self.report({"WARNING"}, "Can't apply the scale of a mesh shared with other objects")
            return CANCEL
        return FINISHED


classes = (
    TOUCHVIEW_PG_local_transform,
    TOUCHVIEW_OT_local_transform,
    TOUCHVIEW_OT_apply_object_scale,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.touchview_local_transform = PointerProperty(type=TOUCHVIEW_PG_local_transform)  # type: ignore


def unregister():
    del bpy.types.Scene.touchview_local_transform  # type: ignore
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
