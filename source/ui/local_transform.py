import math
import os

import bpy
from bpy.types import GizmoGroup, WorkSpaceTool
from mathutils import Matrix

from ..ops.local_transform import (TOOL_ID, SCULPT_DECK_OT_local_transform,
                                   pivot_point, settings, transform_objects,
                                   unit_scale)

###
# Local Transform tool
#  A Sculpt Mode tool with its own header settings and gizmos. The gizmos only
#  show while the tool is active, and each one starts a local transform drag:
#   - a ring per axis rotates, an arrow per axis moves, a box per axis scales
#   - the white ring rotates around the view, the outer ring scales evenly
#   - the dot in the middle moves in the view plane
#  Rings and arrows follow the Axis setting, the boxes always follow the
#  object's own axes, since the object can only be stretched along those.
###

# Blender joins this to its icon folder, an absolute path points at ours
ICON = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "icons", "ops.sculpt_deck.local_transform")
)

# turn a gizmo's Z axis onto the X, Y or Z axis
AXIS_ALIGN = (
    Matrix.Rotation(math.pi / 2, 4, "Y"),
    Matrix.Rotation(-math.pi / 2, 4, "X"),
    Matrix.Identity(4),
)
AXES = ("X", "Y", "Z")

# sizes in gizmo units, one unit is Blender's gizmo size preference
MOVE_START = 0.9
MOVE_LENGTH = 0.35
SCALE_LENGTH = 0.72
VIEW_RING = 1.22
UNIFORM_RING = 1.4
CENTER_DOT = 0.12
# the move arrows start this far past the outermost ring on screen, and hide
# when their axis points almost straight at the view
MOVE_MARGIN = - 0.06
MOVE_MAX_START = 4.0
MOVE_MIN_SIDEWAYS = 0.2


def brighter(color) -> tuple:
    return tuple(min(channel * 1.3 + 0.15, 1.0) for channel in color)


class SCULPT_DECK_GGT_local_transform(GizmoGroup):
    bl_idname = "SCULPT_DECK_GGT_local_transform"
    bl_label = "Local Transform"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D"}

    @classmethod
    def poll(cls, context):
        if context.active_object is None:
            return False
        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        return tool is not None and tool.idname == TOOL_ID

    def setup(self, context):
        theme = context.preferences.themes[0].user_interface
        colors = (tuple(theme.axis_x), tuple(theme.axis_y), tuple(theme.axis_z))
        self.rotate = []
        self.move = []
        self.scale = []
        for axis, color in zip(AXES, colors):
            ring = self.handle("GIZMO_GT_dial_3d", "ROTATE", axis, color)
            ring.draw_options = {"CLIP"}
            ring.line_width = 3
            self.rotate.append(ring)

            arrow = self.handle("GIZMO_GT_arrow_3d", "MOVE", axis, color)
            arrow.draw_style = "NORMAL"
            # only the arrowhead, like Blender's own move gizmo
            arrow.draw_options = set()
            arrow.length = MOVE_LENGTH
            arrow.matrix_offset = Matrix.Translation((0.0, 0.0, MOVE_START))
            # offsets in gizmo units like the gizmo itself, not scene units
            arrow.use_draw_offset_scale = True
            self.move.append(arrow)

            box = self.handle("GIZMO_GT_arrow_3d", "SCALE", axis, color)
            box.draw_style = "BOX"
            box.length = SCALE_LENGTH
            box.line_width = 2
            self.scale.append(box)

        self.view_ring = self.handle("GIZMO_GT_dial_3d", "ROTATE", "VIEW", (0.9, 0.9, 0.9))
        self.view_ring.scale_basis = VIEW_RING
        self.view_ring.line_width = 3

        self.uniform_ring = self.handle("GIZMO_GT_dial_3d", "SCALE", "VIEW", (0.75, 0.75, 0.55))
        self.uniform_ring.scale_basis = UNIFORM_RING
        self.uniform_ring.line_width = 3

        self.center = self.handle("GIZMO_GT_move_3d", "MOVE", "VIEW", (0.9, 0.9, 0.9))
        self.center.draw_style = "RING_2D"
        self.center.draw_options = {"FILL", "ALIGN_VIEW"}
        self.center.scale_basis = CENTER_DOT

    def handle(self, gizmo_type: str, mode: str, axis: str, color: tuple):
        gizmo = self.gizmos.new(gizmo_type)
        props = gizmo.target_set_operator(SCULPT_DECK_OT_local_transform.bl_idname)
        props.mode = mode
        props.axis = axis
        gizmo.color = color
        gizmo.alpha = 0.6
        gizmo.color_highlight = brighter(color)
        gizmo.alpha_highlight = 1.0
        return gizmo

    def draw_prepare(self, context):
        obj = context.active_object
        options = settings(context)
        running = SCULPT_DECK_OT_local_transform.running

        pivot = Matrix.Translation(pivot_point(context, transform_objects(context)))
        local = pivot @ obj.matrix_world.to_3x3().normalized().to_4x4()
        axes = pivot if options.orientation == "GLOBAL" else local
        view = pivot @ context.region_data.view_rotation.to_matrix().to_4x4()
        toward_viewer = view.col[2].xyz

        for i in range(3):
            self.rotate[i].matrix_basis = axes @ AXIS_ALIGN[i]
            self.move[i].matrix_basis = axes @ AXIS_ALIGN[i]
            self.scale[i].matrix_basis = local @ AXIS_ALIGN[i]
            # how much of the arrow shows sideways on screen
            facing = axes.col[i].xyz.normalized().dot(toward_viewer)
            sideways = math.sqrt(max(0.0, 1.0 - facing * facing))
            start = min(max(MOVE_START, (UNIFORM_RING + MOVE_MARGIN) / max(sideways, 1e-3)), MOVE_MAX_START)
            self.move[i].matrix_offset = Matrix.Translation((0.0, 0.0, start))
            self.rotate[i].hide = running or not options.show_rotate
            self.move[i].hide = running or not options.show_move or sideways < MOVE_MIN_SIDEWAYS
            self.scale[i].hide = running or not options.show_scale
        self.view_ring.matrix_basis = view
        self.uniform_ring.matrix_basis = view
        self.center.matrix_basis = view
        self.view_ring.hide = running or not options.show_rotate
        self.uniform_ring.hide = running or not options.show_scale
        self.center.hide = running or not options.show_move


class SCULPT_DECK_TOOL_local_transform(WorkSpaceTool):
    bl_space_type = "VIEW_3D"
    bl_context_mode = "SCULPT"
    bl_idname = TOOL_ID
    bl_label = "Local Transform"
    bl_description = (
        "Move, rotate and scale the whole object along its own axes, without leaving Sculpt Mode.\n"
        "Scaling always follows the object's axes, so rotating between stretches doesn't skew it"
    )
    bl_icon = ICON
    bl_widget = SCULPT_DECK_GGT_local_transform.bl_idname

    def draw_settings(context, layout, tool):  # type: ignore
        options = settings(context)
        row = layout.row(align=True)
        row.prop(options, "show_move", toggle=True)
        row.prop(options, "show_rotate", toggle=True)
        row.prop(options, "show_scale", toggle=True)
        row = layout.row(align=True)
        row.label(text="Axis")
        row.prop(options, "orientation", expand=True)
        layout.prop(options, "pivot")
        if any(not unit_scale(obj) for obj in transform_objects(context) if obj.type == "MESH"):
            # left over from before, brushes work stretched until it's applied
            row = layout.row()
            row.alert = True
            row.operator("sculpt_deck.apply_object_scale", icon="CON_SIZELIKE")


def register():
    bpy.utils.register_class(SCULPT_DECK_GGT_local_transform)
    # its own toolbar section, right after Blender's transform tools
    bpy.utils.register_tool(SCULPT_DECK_TOOL_local_transform, after={"builtin.transform"}, separator=True, group=True)


def unregister():
    bpy.utils.unregister_tool(SCULPT_DECK_TOOL_local_transform)
    bpy.utils.unregister_class(SCULPT_DECK_GGT_local_transform)
