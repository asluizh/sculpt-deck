import math
import os

import bpy
from bpy.types import Gizmo, GizmoGroup, WorkSpaceTool
from mathutils import Matrix, Vector

from ..ops.array import (AXES, CIRCULAR_TOOL_ID, LINEAR_TOOL_ID,
                         TOUCHVIEW_OT_array_edit, axes_basis, circle_step,
                         copy_matrix, current_array, ensure_array, get_input,
                         leave_tool_later, settings)
from ..ops.local_transform import TOOL_ID as LOCAL_TRANSFORM_ID
from .local_transform import AXIS_ALIGN

###
# Array tools
#  Linear Array and Circular Array, each editing its own kind of array, so
#  they can be stacked. Starting a tool on a mesh without that kind of array
#  adds one right away; selecting a mesh without one hands back to the
#  previous tool. The gizmos only show while the tool is active:
#   - linear: the dot on the first copy sets the spacing, freely or along an
#     arrow per axis; the arrow past the last copy adds or removes copies
#   - circular: a circle through the copies, a ring on its center, a ball on
#     the mesh, an arrowhead moving the mesh to or from the center, a dot on
#     the last copy for the count and an arrowhead at the end of the arc;
#     while the arc is dragged, a filled sector and marks show its steps
###

ICON_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "icons"))

ARROW_START = 0.25
ARROW_LENGTH = 0.35
DOT = 0.14
WHITE = (0.9, 0.9, 0.9)
ACCENT = (1.0, 0.63, 0.16)
CENTER_RING = 0.22
CIRCLE_SEGMENTS = 96
# step marks while dragging the arc, in parts of the radius: coarse ones
# inside the circle, fine ones as a short fringe outside it
COARSE_MARK = (0.6, 1.0)
FINE_MARK = (1.0, 1.07)
# the arc handle's tip sits on the circle this far before the arc's end, so
# it stays clear of the mesh's handles on a full circle
ARC_HANDLE_BACK = math.radians(30)
ARC_HANDLE_LENGTH = 0.25
# with no copies, the count dot waits on the circle this far ahead of the mesh
COUNT_ALONE_AHEAD = math.radians(30)
# the radius arrowhead sits past the mesh's ball
RADIUS_START = 0.3


def brighter(color) -> tuple:
    return tuple(min(channel * 1.3 + 0.15, 1.0) for channel in color)


def aligned(direction: Vector) -> Matrix:
    """Rotation turning a gizmo's Z axis onto the direction"""
    return direction.to_track_quat("Z", "Y").to_matrix().to_4x4()


def unit_circle(angle: float) -> Vector:
    return Vector((math.cos(angle), math.sin(angle), 0.0))


class TOUCHVIEW_GT_array_circle(Gizmo):
    """The circle of a circular array, drawn in its plane at its size: the
    matrix maps X to the mesh's side, Z to the axis, scaled by the radius.
    The "LINE" part draws the circle and the step marks, the "SECTOR" part
    fills the arc. Neither can be clicked, the handles do the editing."""

    bl_idname = "TOUCHVIEW_GT_array_circle"
    __slots__ = ("part", "shape", "shape_key", "marks", "marks_key")

    def setup(self):
        self.part = "LINE"
        self.shape = self.marks = None
        self.shape_key = self.marks_key = None
        self.use_draw_scale = False

    def build(self, arc: float, mark_step: float | None):
        if self.part == "SECTOR":
            arc = max(arc, 0.01)
            if self.shape_key != round(arc, 5):
                self.shape_key = round(arc, 5)
                segments = max(2, round(CIRCLE_SEGMENTS * arc / math.tau))
                points = [unit_circle(arc * i / segments) for i in range(segments + 1)]
                triangles = []
                for a, b in zip(points, points[1:]):
                    triangles += [Vector(), a, b]
                self.shape = self.new_custom_shape("TRIS", triangles)
            return
        if self.shape is None:
            points = [unit_circle(math.tau * i / CIRCLE_SEGMENTS) for i in range(CIRCLE_SEGMENTS + 1)]
            lines = []
            for a, b in zip(points, points[1:]):
                lines += [a, b]
            self.shape = self.new_custom_shape("LINES", lines)
        if mark_step is None:
            self.marks_key = None
        elif self.marks_key != mark_step:
            self.marks_key = mark_step
            low, high = COARSE_MARK if mark_step > math.radians(1.5) else FINE_MARK
            lines = []
            for i in range(round(math.tau / mark_step)):
                direction = unit_circle(mark_step * i)
                lines += [direction * low, direction * high]
            self.marks = self.new_custom_shape("LINES", lines)

    def draw(self, context):
        if self.shape is not None:
            self.draw_custom_shape(self.shape)
        if self.marks_key is not None and self.marks is not None:
            self.draw_custom_shape(self.marks)

    def draw_select(self, context, select_id):
        pass


class ArrayGizmos:
    """Shared by the two tools' gizmo groups"""

    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D"}

    kind = ""
    tool_id = ""

    @classmethod
    def poll(cls, context):
        if context.active_object is None:
            return False
        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        return tool is not None and tool.idname == cls.tool_id

    def start(self, context):
        """Add an array when the tool starts"""
        obj = context.active_object
        self.object = obj.name if obj else ""
        if obj is None or current_array(obj, self.kind) is not None:
            return
        rv3d = context.region_data or context.space_data.region_3d
        rotation = rv3d.view_rotation.copy()
        name, kind = obj.name, self.kind
        # data can't change while drawing, so add it right after
        bpy.app.timers.register(lambda: ensure_array(name, kind, rotation), first_interval=0.0)

    def handle(self, gizmo_type: str, handle: str, axis: str, color: tuple):
        gizmo = self.gizmos.new(gizmo_type)  # type: ignore
        props = gizmo.target_set_operator(TOUCHVIEW_OT_array_edit.bl_idname)
        props.handle = handle
        props.axis = axis
        gizmo.color = color
        gizmo.alpha = 0.7
        gizmo.color_highlight = brighter(color)
        gizmo.alpha_highlight = 1.0
        gizmo.line_width = 2
        return gizmo

    def dot(self, handle: str, color: tuple, fill: bool = True, size: float = DOT):
        gizmo = self.handle("GIZMO_GT_move_3d", handle, "VIEW", color)
        gizmo.draw_style = "RING_2D"
        gizmo.draw_options = {"FILL", "ALIGN_VIEW"} if fill else {"ALIGN_VIEW"}
        gizmo.scale_basis = size
        gizmo.line_width = 2
        return gizmo

    def arrow(self, handle: str, axis: str, color: tuple):
        gizmo = self.handle("GIZMO_GT_arrow_3d", handle, axis, color)
        gizmo.draw_style = "NORMAL"
        gizmo.draw_options = set()
        gizmo.length = ARROW_LENGTH
        gizmo.matrix_offset = Matrix.Translation((0.0, 0.0, ARROW_START))
        # offsets in gizmo units like the gizmo itself, not scene units
        gizmo.use_draw_offset_scale = True
        return gizmo

    def prepare(self, context):
        """The current array, or None to hide the gizmos"""
        obj = context.active_object
        modifier = current_array(obj, self.kind)
        if obj.name != getattr(self, "object", None):
            self.object = obj.name
            if modifier is None:
                # another mesh, without this kind of array
                leave_tool_later(self.tool_id)
        return modifier


class TOUCHVIEW_GGT_linear_array(ArrayGizmos, GizmoGroup):
    bl_idname = "TOUCHVIEW_GGT_linear_array"
    bl_label = "Linear Array"
    kind = "LINEAR"
    tool_id = LINEAR_TOOL_ID

    def setup(self, context):
        theme = context.preferences.themes[0].user_interface
        colors = (tuple(theme.axis_x), tuple(theme.axis_y), tuple(theme.axis_z))
        self.offset = self.dot("OFFSET", WHITE)
        self.offset_axes = [self.arrow("OFFSET", axis, color) for axis, color in zip(AXES, colors)]
        self.count = self.arrow("LINEAR_COUNT", "VIEW", ACCENT)
        self.start(context)

    def draw_prepare(self, context):
        modifier = self.prepare(context)
        for gizmo in self.gizmos:
            gizmo.hide = modifier is None or TOUCHVIEW_OT_array_edit.running
        if modifier is None:
            return
        obj = context.active_object
        matrix = obj.matrix_world
        view = context.region_data.view_rotation.to_matrix().to_4x4()
        offset = get_input(modifier, "Offset")
        first = Matrix.Translation(matrix @ offset)
        self.offset.matrix_basis = first @ view
        axes = axes_basis(obj, settings(context).orientation).to_4x4()
        for i, arrow in enumerate(self.offset_axes):
            arrow.matrix_basis = first @ axes @ AXIS_ALIGN[i]
        direction = matrix.to_3x3() @ offset
        if direction.length < 1e-9:
            direction = matrix.to_3x3().col[0]
        last = matrix @ (offset * (get_input(modifier, "Count") - 1))
        self.count.matrix_basis = Matrix.Translation(last) @ aligned(direction.normalized())


class TOUCHVIEW_GGT_circular_array(ArrayGizmos, GizmoGroup):
    bl_idname = "TOUCHVIEW_GGT_circular_array"
    bl_label = "Circular Array"
    kind = "CIRCULAR"
    tool_id = CIRCULAR_TOOL_ID

    def setup(self, context):
        self.circle = self.outline("LINE", 0.7)
        self.sector = self.outline("SECTOR", 0.2)
        self.center = self.dot("CENTER", ACCENT, fill=False, size=CENTER_RING)
        self.move = self.dot("MOVE", WHITE)
        self.radius = self.arrow("RADIUS", "VIEW", ACCENT)
        self.radius.matrix_offset = Matrix.Translation((0.0, 0.0, RADIUS_START))
        self.count = self.dot("CIRCULAR_COUNT", ACCENT, size=DOT * 0.8)
        self.arc = self.handle("GIZMO_GT_arrow_3d", "ARC", "VIEW", ACCENT)
        self.arc.draw_options = set()
        self.arc.length = ARC_HANDLE_LENGTH
        # the arrow ends with its tip on its position
        self.arc.matrix_offset = Matrix.Translation((0.0, 0.0, -ARC_HANDLE_LENGTH))
        self.arc.use_draw_offset_scale = True
        self.start(context)

    def outline(self, part: str, alpha: float):
        gizmo = self.gizmos.new(TOUCHVIEW_GT_array_circle.bl_idname)
        gizmo.part = part
        gizmo.color = ACCENT
        gizmo.alpha = alpha
        gizmo.line_width = 2
        return gizmo

    def draw_prepare(self, context):
        modifier = self.prepare(context)
        running = TOUCHVIEW_OT_array_edit.running
        handle = TOUCHVIEW_OT_array_edit.active_handle if running else ""
        for gizmo in self.gizmos:
            gizmo.hide = modifier is None or running
        if modifier is None:
            return
        # the circle stays while dragging around it, the sector only shows then
        self.circle.hide = running and handle not in {"ARC", "CIRCULAR_COUNT"}
        self.sector.hide = handle != "ARC"

        obj = context.active_object
        matrix = obj.matrix_world
        view = context.region_data.view_rotation.to_matrix().to_4x4()
        center = matrix @ get_input(modifier, "Center")
        origin = matrix.translation
        axis = (matrix.to_3x3() @ get_input(modifier, "Axis")).normalized()
        self.center.matrix_basis = Matrix.Translation(center) @ view
        self.move.matrix_basis = Matrix.Translation(origin) @ view

        outward = origin - center
        outward -= outward.project(axis)
        radius = outward.length
        if radius < 1e-6:
            outward, radius = axis.orthogonal(), 1e-3
        outward.normalize()
        self.radius.matrix_basis = Matrix.Translation(origin) @ aligned(outward)

        arc = get_input(modifier, "Arc")
        frame = Matrix((outward, axis.cross(outward), axis)).transposed().to_4x4()
        circle = Matrix.Translation(center) @ frame @ Matrix.Scale(radius, 4)
        self.circle.matrix_basis = self.sector.matrix_basis = circle
        self.circle.build(arc, TOUCHVIEW_OT_array_edit.arc_step if handle == "ARC" else None)
        self.sector.build(arc, None)

        # the dot sits on the last copy, or ahead of the mesh when there's none
        count = get_input(modifier, "Count")
        if count < 2:
            last = center + frame.to_3x3() @ unit_circle(COUNT_ALONE_AHEAD) * radius
        else:
            last = matrix @ copy_matrix(modifier, circle_step(modifier) * (count - 1)) @ Vector()
        self.count.matrix_basis = Matrix.Translation(last) @ view

        # the arrowhead sits on the circle just before the arc's end, pointing
        # the way it grows
        end = frame.to_3x3() @ unit_circle(arc - min(ARC_HANDLE_BACK, arc / 2))
        along = axis.cross(end)
        self.arc.matrix_basis = Matrix.Translation(center + end * radius) @ Matrix(
            (end, -axis, along)
        ).transposed().to_4x4()


def draw_orientation(layout, options):
    row = layout.row(align=True)
    row.label(text="Axis")
    row.prop(options, "orientation", expand=True)


def draw_finish(layout, kind: str):
    row = layout.row(align=True)
    row.operator("touchview.array_apply", text="Apply", icon="CHECKMARK").kind = kind
    row.operator("touchview.array_remove", text="", icon="X").kind = kind


class TOUCHVIEW_TOOL_linear_array(WorkSpaceTool):
    bl_space_type = "VIEW_3D"
    bl_context_mode = "SCULPT"
    bl_idname = LINEAR_TOOL_ID
    bl_label = "Linear Array"
    bl_description = (
        "Copy the mesh in a line. The mesh stays in place and can still be sculpted,\n"
        "and every copy follows it until the array is applied"
    )
    bl_icon = os.path.join(ICON_DIR, "ops.touchview.linear_array")
    bl_widget = TOUCHVIEW_GGT_linear_array.bl_idname

    def draw_settings(context, layout, tool):  # type: ignore
        options = settings(context)
        modifier = current_array(context.active_object, "LINEAR")
        if modifier is None:
            draw_orientation(layout, options)
            return
        layout.prop(options, "linear_count")
        draw_orientation(layout, options)
        draw_finish(layout, "LINEAR")


class TOUCHVIEW_TOOL_circular_array(WorkSpaceTool):
    bl_space_type = "VIEW_3D"
    bl_context_mode = "SCULPT"
    bl_idname = CIRCULAR_TOOL_ID
    bl_label = "Circular Array"
    bl_description = (
        "Copy the mesh around a circle. The mesh stays in place and can still be sculpted,\n"
        "and every copy follows it until the array is applied"
    )
    bl_icon = os.path.join(ICON_DIR, "ops.touchview.circular_array")
    bl_widget = TOUCHVIEW_GGT_circular_array.bl_idname

    def draw_settings(context, layout, tool):  # type: ignore
        options = settings(context)
        obj = context.active_object
        modifier = current_array(obj, "CIRCULAR")
        if modifier is None:
            draw_orientation(layout, options)
            return
        layout.prop(options, "circular_count")
        layout.prop(options, "arc")
        # light up the axis the circle turns around, in the current orientation
        axis = (obj.matrix_world.to_3x3() @ get_input(modifier, "Axis")).normalized()
        basis = axes_basis(obj, options.orientation)
        current = next((name for i, name in enumerate(AXES) if abs(axis.dot(basis.col[i])) > 0.9999), "VIEW")
        row = layout.row(align=True)
        row.label(text="Around")
        for name in (*AXES, "VIEW"):
            text = "View" if name == "VIEW" else name
            row.operator("touchview.array_axis", text=text, depress=name == current).axis = name
        draw_orientation(layout, options)
        draw_finish(layout, "CIRCULAR")


def register():
    bpy.utils.register_class(TOUCHVIEW_GT_array_circle)
    bpy.utils.register_class(TOUCHVIEW_GGT_linear_array)
    bpy.utils.register_class(TOUCHVIEW_GGT_circular_array)
    # next to Local Transform
    bpy.utils.register_tool(TOUCHVIEW_TOOL_linear_array, after={LOCAL_TRANSFORM_ID}, group=True)
    bpy.utils.register_tool(TOUCHVIEW_TOOL_circular_array, after={LINEAR_TOOL_ID}, group=True)


def unregister():
    bpy.utils.unregister_tool(TOUCHVIEW_TOOL_circular_array)
    bpy.utils.unregister_tool(TOUCHVIEW_TOOL_linear_array)
    bpy.utils.unregister_class(TOUCHVIEW_GGT_circular_array)
    bpy.utils.unregister_class(TOUCHVIEW_GGT_linear_array)
    bpy.utils.unregister_class(TOUCHVIEW_GT_array_circle)
