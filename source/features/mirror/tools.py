import os

import bpy
from bpy.types import Gizmo, GizmoGroup, WorkSpaceTool
from mathutils import Matrix, Vector

from ...ops.local_transform import TOOL_ID as LOCAL_TRANSFORM_ID
from ...ui.local_transform import AXIS_ALIGN
from ..array.operators import input_socket, leave_tool_later
from .operators import (AXES, MIRROR_TOOL_ID, current_mirror, enabled_axes,
                        ensure_mirror, mirror_frame)

###
# Mirror tool
#  Starting the tool on a mesh without a mirror adds one right away;
#  selecting a mesh without one hands back to the previous tool. While the
#  tool is active, each enabled mirror plane shows as an outline in its
#  axis color, around the mesh's reflection point.
###

ICON = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "icons", "ops.sculpt_deck.mirror")
)

# the outline's half size, in parts of the mesh's largest dimension
PLANE_SIZE = 0.75


class SCULPT_DECK_GT_mirror_plane(Gizmo):
    """A square outline in the matrix's XY plane, from -1 to 1. It can't be
    clicked, the header sets the planes."""

    bl_idname = "SCULPT_DECK_GT_mirror_plane"
    __slots__ = ("shape",)

    def setup(self):
        corners = [Vector(c) for c in ((-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0))]
        lines = []
        for a, b in zip(corners, corners[1:] + corners[:1]):
            lines += [a, b]
        self.shape = self.new_custom_shape("LINES", lines)
        self.use_draw_scale = False

    def draw(self, context):
        self.draw_custom_shape(self.shape)

    def draw_select(self, context, select_id):
        pass


class SCULPT_DECK_GGT_mirror(GizmoGroup):
    bl_idname = "SCULPT_DECK_GGT_mirror"
    bl_label = "Mirror"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D"}

    @classmethod
    def poll(cls, context):
        if context.active_object is None:
            return False
        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        return tool is not None and tool.idname == MIRROR_TOOL_ID

    def setup(self, context):
        theme = context.preferences.themes[0].user_interface
        self.planes = []
        for color in (theme.axis_x, theme.axis_y, theme.axis_z):
            gizmo = self.gizmos.new(SCULPT_DECK_GT_mirror_plane.bl_idname)
            gizmo.color = tuple(color)
            gizmo.alpha = 0.6
            gizmo.line_width = 2
            self.planes.append(gizmo)
        # add a mirror when the tool starts; data can't change while drawing
        obj = context.active_object
        self.object = obj.name if obj else ""
        if obj is not None and current_mirror(obj) is None:
            name = obj.name
            bpy.app.timers.register(lambda: ensure_mirror(name), first_interval=0.0)

    def draw_prepare(self, context):
        obj = context.active_object
        modifier = current_mirror(obj)
        if obj.name != self.object:
            self.object = obj.name
            if modifier is None:
                # another mesh, without a mirror
                leave_tool_later(MIRROR_TOOL_ID)
        axes = enabled_axes(modifier) if modifier else []
        for i, plane in enumerate(self.planes):
            plane.hide = i not in axes
        if not axes:
            return
        frame = mirror_frame(modifier)
        rotation = frame.to_3x3().normalized().to_4x4()
        origin = frame.translation
        location = obj.matrix_world.translation
        size = max(max(obj.dimensions), 1e-3) * PLANE_SIZE
        for i in axes:
            normal = rotation.col[i].xyz
            center = location - normal * (location - origin).dot(normal)
            self.planes[i].matrix_basis = Matrix.Translation(center) @ rotation @ AXIS_ALIGN[i] @ Matrix.Scale(size, 4)


class SCULPT_DECK_TOOL_mirror(WorkSpaceTool):
    bl_space_type = "VIEW_3D"
    bl_context_mode = "SCULPT"
    bl_idname = MIRROR_TOOL_ID
    bl_label = "Mirror"
    bl_description = (
        "Mirror the mesh across the world origin's planes, or a Mirror Object's.\n"
        "The mesh stays in place and can still be sculpted, and its mirror image\n"
        "follows it until the mirror is applied"
    )
    bl_icon = ICON
    bl_widget = SCULPT_DECK_GGT_mirror.bl_idname

    def draw_settings(context, layout, tool):  # type: ignore
        modifier = current_mirror(context.active_object)
        if modifier is None:
            return
        row = layout.row(align=True)
        row.label(text="Mirror")
        for axis in AXES:
            row.prop(input_socket(modifier, axis), "value", text=axis, toggle=True)
        layout.prop(input_socket(modifier, "Mirror Object"), "value", text="", icon="OBJECT_DATA")
        row = layout.row(align=True)
        row.operator("sculpt_deck.mirror_apply", text="Apply", icon="CHECKMARK")
        row.operator("sculpt_deck.mirror_remove", text="", icon="X")


def register():
    bpy.utils.register_class(SCULPT_DECK_GT_mirror_plane)
    bpy.utils.register_class(SCULPT_DECK_GGT_mirror)
    # right after Local Transform, before the array tools (see features/__init__.py)
    bpy.utils.register_tool(SCULPT_DECK_TOOL_mirror, after={LOCAL_TRANSFORM_ID}, group=True)


def unregister():
    bpy.utils.unregister_tool(SCULPT_DECK_TOOL_mirror)
    bpy.utils.unregister_class(SCULPT_DECK_GGT_mirror)
    bpy.utils.unregister_class(SCULPT_DECK_GT_mirror_plane)
