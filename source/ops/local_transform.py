import math

import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, PointerProperty)
from bpy.types import Operator, PropertyGroup
from bpy_extras import view3d_utils
from mathutils import Matrix, Vector

from ..utils.constants import CANCEL, FINISHED, MODAL, object_modes

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
    ("ORIGIN", "Origin", "Transform around the object's origin", "OBJECT_ORIGIN", 0),
    ("BOUNDS", "Bounding Box Center", "Transform around the center of the object's bounds", "PIVOT_BOUNDBOX", 1),
    ("CURSOR", "3D Cursor", "Transform around the 3D cursor", "PIVOT_CURSOR", 2),
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

# mouse travel before a release confirms, so a tap doesn't end the transform
DRAG_THRESHOLD = 4
SNAP_ANGLE = math.radians(5)
SNAP_FACTOR = 0.1
SNAP_DISTANCE = 0.1


class TOUCHVIEW_PG_local_transform(PropertyGroup):
    pivot: EnumProperty(  # type: ignore
        name="Pivot",
        description="Point the object rotates and scales around",
        items=local_pivot_items,
        default="ORIGIN",
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


def pivot_point(context, obj) -> Vector:
    pivot = settings(context).pivot
    if pivot == "CURSOR":
        return context.scene.cursor.location.copy()
    if pivot == "BOUNDS":
        center = sum((Vector(corner) for corner in obj.bound_box), Vector()) / 8
        return obj.matrix_world @ center
    return obj.matrix_world.translation.copy()


def apply_scale(context, obj) -> bool:
    """Bake the object's scale into its mesh, staying in the current mode"""
    if obj.type != "MESH" or tuple(obj.scale) == (1.0, 1.0, 1.0):
        return True
    if obj.data.users > 1:
        return False
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


class TOUCHVIEW_OT_local_transform(Operator):
    """Move, rotate or scale the whole object, staying in the current mode"""

    bl_label = "Local Transform"
    bl_idname = "touchview.local_transform"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    # the gizmos hide while a transform runs
    running = False

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
        pivot = Vector(self.pivot)
        if self.mode == "MOVE":
            if self.axis == "VIEW":
                return moved(matrix, Vector(self.offset))
            return moved(matrix, self.world_axis(matrix) * self.distance)
        if self.mode == "ROTATE":
            return rotated(matrix, pivot, self.world_axis(matrix), self.angle)
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
        obj = context.active_object
        self.use_settings(context)
        if not self.use_pivot:
            self.pivot = pivot_point(context, obj)
            self.use_pivot = True
        obj.matrix_world = self.transformed(obj.matrix_world.copy())
        if self.mode == "SCALE":
            self.apply_scale(context)
        return FINISHED

    def apply_scale(self, context):
        context.view_layer.update()
        if not apply_scale(context, context.active_object):
            self.report({"WARNING"}, "Scale not applied, the mesh is shared with other objects")

    def invoke(self, context, event):
        region, rv3d = context.region, context.region_data
        if context.area is None or context.area.type != "VIEW_3D" or rv3d is None:
            return self.execute(context)
        obj = context.active_object
        self.use_settings(context)
        self.start = obj.matrix_world.copy()
        self.pivot = pivot_point(context, obj)
        self.use_pivot = True
        self.view_axis = rv3d.view_rotation @ Vector((0.0, 0.0, 1.0))

        pivot = Vector(self.pivot)
        center = view3d_utils.location_3d_to_region_2d(region, rv3d, pivot)
        self.center = center if center is not None else Vector((region.width / 2, region.height / 2))
        self.start_mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self.previous = self.start_mouse - self.center
        self.screen_angle = 0.0
        self.moved = False
        self.screen_axis = self.axis_on_screen(context, pivot)

        TOUCHVIEW_OT_local_transform.running = True
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set(
            "Drag to transform  •  Release/Click: Confirm  •  Right Click/Esc: Cancel  •  Ctrl: Snap"
        )
        self.update(context, event)
        return MODAL

    def axis_on_screen(self, context, pivot: Vector) -> Vector:
        """Pixels covered by one unit along the axis, at the pivot"""
        region, rv3d = context.region, context.region_data
        side = view3d_utils.region_2d_to_location_3d(region, rv3d, self.center + Vector((1.0, 0.0)), pivot)
        step = max((side - pivot).length, 1e-6) * 50
        tip = view3d_utils.location_3d_to_region_2d(region, rv3d, pivot + self.world_axis(self.start) * step)
        axis = (tip - self.center) / step if tip is not None else Vector((0.0, 0.0))
        if axis.length < 1e-3:
            # the axis points at the viewer, drag up and down instead
            axis = Vector((0.0, 1.0 / step * 50))
        return axis

    def modal(self, context, event):
        if event.type in {"RIGHTMOUSE", "ESC"} and event.value == "PRESS":
            context.active_object.matrix_world = self.start
            return self.finish(context, CANCEL)
        if event.type in {"RET", "NUMPAD_ENTER", "SPACE"} and event.value == "PRESS":
            return self.confirm(context)
        if event.type == "LEFTMOUSE":
            self.update(context, event)
            # a tap (e.g. from a pie or button) leaves the transform running
            if event.value == "RELEASE" and self.moved:
                return self.confirm(context)
            return MODAL
        if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE", "LEFT_CTRL", "RIGHT_CTRL"}:
            self.update(context, event)
        return MODAL

    def confirm(self, context):
        if self.is_identity():
            return self.finish(context, CANCEL)
        if self.mode == "SCALE":
            self.apply_scale(context)
        return self.finish(context, FINISHED)

    def finish(self, context, result):
        TOUCHVIEW_OT_local_transform.running = False
        context.workspace.status_text_set(None)
        context.area.header_text_set(None)
        context.area.tag_redraw()
        return result

    def update(self, context, event):
        mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        if (mouse - self.start_mouse).length > DRAG_THRESHOLD:
            self.moved = True
        snap = event.ctrl
        if self.mode == "MOVE":
            self.update_move(context, mouse, snap)
        elif self.mode == "ROTATE":
            self.update_rotate(context, mouse, snap)
        else:
            self.update_scale(mouse, snap)
        context.active_object.matrix_world = self.transformed(self.start)
        context.area.header_text_set(self.header_text())

    def update_move(self, context, mouse: Vector, snap: bool):
        if self.axis == "VIEW":
            region, rv3d, pivot = context.region, context.region_data, Vector(self.pivot)
            start = view3d_utils.region_2d_to_location_3d(region, rv3d, self.start_mouse, pivot)
            self.offset = view3d_utils.region_2d_to_location_3d(region, rv3d, mouse, pivot) - start
            return
        distance = (mouse - self.start_mouse).dot(self.screen_axis) / self.screen_axis.length_squared
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
    """Apply the object's scale to its mesh, so brushes aren't stretched, staying in the current mode"""

    bl_label = "Apply Scale"
    bl_idname = "touchview.apply_object_scale"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and context.mode in object_modes

    def execute(self, context):
        if not apply_scale(context, context.active_object):
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
