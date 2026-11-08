from math import ceil, cos, radians, sin

import bpy
from bpy.types import GizmoGroup
from mathutils import Vector

from ...core.blender import navigation_gizmo_height, safe_area_3d, ui_scale
from ..action_slots import WIDGET_SLOTS
from .gizmo_2d import ActionGizmo, GizmoSet, action_icon, action_toggles
from .gizmo_config import controllerConfig
from .settings import widget_settings

__module__ = __name__.split(".")[0]

###
# GizmoGroup
#  - holds the menu controller and the action buttons (the floating
#    toggle is navigation's, see navigation/toggle.py)
#  - builds one ActionGizmo per widget button of the current mode, rebuilt
#    when the buttons, the mode or a toggle's state (its icon) change
#  - positions Gizmos during draw_prepare()
###


class GIZMO_GT_viewport_gizmo_group(GizmoGroup):
    bl_label = "Sculpt Deck widget"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"PERSISTENT", "SCALE"}

    # set up gizmo collection
    def setup(self, context):
        self.actions: list[ActionGizmo] = []
        self.signature = None
        self.__buildController(context)
        self.spacing = widget_settings().menu_spacing

    # rebuild the action buttons when what they show changes
    def __syncActions(self, context):
        widget = widget_settings().getWidgetSettings(context.mode)
        idnames = [idname for idname in (widget.slots(WIDGET_SLOTS) if widget else []) if idname]
        signature = tuple(
            (idname, action_icon(context, idname) if idname in action_toggles else "") for idname in idnames
        )
        if signature == self.signature:
            return
        self.signature = signature
        for action in self.actions:
            self.gizmos.remove(action.primary)
        self.actions = [ActionGizmo(self, context, idname) for idname in idnames]

    def __buildController(self, context):
        self.controller = GizmoSet()
        self.controller.setup(self, controllerConfig)

    def draw_prepare(self, context):
        self.context = context
        prefs = widget_settings()
        self.__updateOrigin()
        self.controller.draw_prepare()
        self.__move_gizmo(self.controller, self.origin)

        self.__syncActions(context)
        visible_gizmos = []
        for gizmo in self.actions:
            gizmo.draw_prepare(context)
            if gizmo.visible:
                visible_gizmos.append(gizmo)
        for gizmo, following in zip(visible_gizmos, visible_gizmos[1:]):
            gizmo.has_dependent = ActionGizmo.pairs.get(gizmo.idname) == following.idname

        if prefs.menu_style == "float.radial":
            self.__menuRadial(visible_gizmos)
        if prefs.menu_style == "fixed.bar":
            self.__menuBar(visible_gizmos)

    def __menuBar(self, visible_gizmos: list[GizmoSet]):
        prefs = widget_settings()
        safe_area = safe_area_3d()
        spacing = ((36 * prefs.gizmo_scale) + 2 * prefs.gizmo_padding) * ui_scale()
        center = (safe_area[0] + safe_area[1]) / 2
        # keep the bottom corners free, e.g. for the floating toggle
        bottom = safe_area[0].y + spacing

        # side bars are kept in the lower half of the viewport, and below the
        # navigation gizmo on the right, so they don't overlap Blender's own UI
        if prefs.gizmo_position in {"LEFT", "RIGHT"}:
            is_left = prefs.gizmo_position == "LEFT"
            top = center.y
            if not is_left:
                top = min(top, safe_area[1].y - navigation_gizmo_height() - spacing / 2)
            top = max(top, bottom)
            start = Vector(
                (
                    safe_area[0].x if is_left else safe_area[1].x,
                    (bottom + top) / 2,
                    0.0,
                )
            )
            axis = Vector((0.0, -1.0, 0.0))
            wrap = Vector((1.0 if is_left else -1.0, 0.0, 0.0))
            length = top - bottom
        else:
            is_top = prefs.gizmo_position == "TOP"
            start = Vector((center.x, safe_area[1].y if is_top else safe_area[0].y, 0.0))
            axis = Vector((1.0, 0.0, 0.0))
            wrap = Vector((0.0, -1.0 if is_top else 1.0, 0.0))
            length = safe_area[1].x - safe_area[0].x - 2 * spacing

        self.__layoutLines(visible_gizmos, start, axis, wrap, length, spacing)

    # center gizmos along `axis` around `start`, wrapping onto new lines
    # (offset towards `wrap`) whenever a line would exceed `length`
    def __layoutLines(
        self,
        gizmos: list[GizmoSet],
        start: Vector,
        axis: Vector,
        wrap: Vector,
        length: float,
        spacing: float,
    ):
        per_line = max(1, int(length // spacing) + 1)
        for line in range(ceil(len(gizmos) / per_line)):
            row = gizmos[line * per_line : (line + 1) * per_line]
            offset = -(len(row) - 1) * spacing / 2
            for i, gizmo in enumerate(row):
                self.__move_gizmo(gizmo, start + axis * (offset + i * spacing) + wrap * (line * spacing))

    def __menuRadial(self, visible_gizmos: list[GizmoSet]):
        prefs = widget_settings()
        # calculate minimum radius to prevent overlapping buttons
        menu_spacing = (36 * prefs.menu_spacing) * prefs.gizmo_scale + prefs.gizmo_padding
        gizmo_scale = 18 * prefs.gizmo_scale
        gizmo_padding = prefs.gizmo_padding
        spacing = (menu_spacing + gizmo_scale + gizmo_padding) * ui_scale()

        count = len(visible_gizmos)
        # reposition Gizmos to origin
        for i, gizmo in enumerate(visible_gizmos):
            if gizmo.skip_draw:
                continue

            if gizmo.has_dependent and i > count / 2:
                self.__calcMove(gizmo, i + 1, count, spacing)
                self.__calcMove(visible_gizmos[i + 1], i, count, spacing)
                visible_gizmos[i + 1].skip_draw = True
            else:
                self.__calcMove(gizmo, i, count, spacing)

    def __calcMove(self, gizmo: GizmoSet, step: int, size: int, spacing: float):
        distance = step / size
        offset = Vector(
            (
                sin(radians(distance * 360)),
                cos(radians(distance * 360)),
                0.0,
            )
        )
        self.__move_gizmo(gizmo, self.origin + offset * spacing)

    def __updateOrigin(self):
        prefs = widget_settings()
        safe_area = safe_area_3d(padding=90)

        # distance across viewport between menus
        span = Vector(
            (
                safe_area[1].x - safe_area[0].x,
                safe_area[1].y - safe_area[0].y,
            )
        )

        # apply position ratio to safe area
        self.origin = Vector(
            (
                safe_area[0].x + span.x * prefs.menu_position[0] * 0.01,
                safe_area[0].y + span.y * prefs.menu_position[1] * 0.01,
                0.0,
            )
        )

    def __move_gizmo(self, gizmo: GizmoSet, position: Vector):
        gizmo.move(position)


classes = (GIZMO_GT_viewport_gizmo_group,)


register, unregister = bpy.utils.register_classes_factory(classes)
