"""The floating toggle: a viewport button that turns touch controls on and off, dragged to move it. Shown when the
Floating Toggle setting is on, and always in the Pen and Touch input modes. It takes the Widget's button size."""

import bpy
from bpy.types import GizmoGroup, Operator
from mathutils import Matrix, Vector

from ..core.blender import safe_area_3d
from ..core.constants import FINISHED, MODAL
from ..core.preferences import preferences
from .settings import navigation_settings

COMMAND = "sculpt_deck.move_toggle_button"
ON_ICON = "OUTLINER_DATA_CAMERA"
OFF_ICON = "GREASEPENCIL"

toggle_colors = {
    "active": {
        "color": [0.1, 0.1, 0.2],
        "alpha": 0.5,
        "color_highlight": [0.15, 0.15, 0.3],
        "alpha_highlight": 0.7,
    },
    "inactive": {
        "color": [0.0, 0.0, 0.0],
        "alpha": 0.5,
        "color_highlight": [0.05, 0.05, 0.05],
        "alpha_highlight": 0.7,
    },
}


def toggle_shown(settings) -> bool:
    return settings.input_mode != "FULL" or settings.enable_floating_toggle


class SCULPT_DECK_OT_float_controller(Operator):
    """Tap to toggle touch controls, drag to move this button"""

    bl_label = "Relocate Toggle Button"
    bl_idname = COMMAND

    def invoke(self, context, event):
        self.has_moved = False
        prefs = navigation_settings()
        fence = safe_area_3d()

        span = Vector((fence[1].x - fence[0].x, fence[1].y - fence[0].y))
        self.init_x = prefs.toggle_position[0]
        self.init_y = prefs.toggle_position[1]
        self.mouse_init_x = self.x = event.mouse_region_x
        self.mouse_init_y = self.y = event.mouse_region_y
        self.offset = Vector(
            (
                (span.x * self.init_x * 0.01 + fence[0].x) - self.x,
                (span.y * self.init_y * 0.01 + fence[0].y) - self.y,
            )
        )
        self.execute(context)

        context.window_manager.modal_handler_add(self)
        return MODAL

    def execute(self, context):
        prefs = navigation_settings()
        fence = safe_area_3d()
        span = Vector((fence[1].x - fence[0].x, fence[1].y - fence[0].y))

        prefs.toggle_position[0] = min(max((self.x - fence[0].x + self.offset.x) / (span.x) * 100.0, 0.0), 100.0)
        prefs.toggle_position[1] = min(max((self.y - fence[0].y + self.offset.y) / (span.y) * 100.0, 0.0), 100.0)
        return FINISHED

    def modal(self, context, event):
        prefs = navigation_settings()
        if (
            event.mouse_region_x < 0
            or event.mouse_region_y < 0
            or event.mouse_region_x > context.region.width
            or event.mouse_region_y > context.region.height
        ):
            # mouse out of region area broken in Blender 4.x, exit early
            return FINISHED
        if event.type == "MOUSEMOVE" and event.value != "RELEASE":  # Apply
            context.region.tag_redraw()
            self.x = event.mouse_region_x
            self.y = event.mouse_region_y
            self.execute(context)
        elif event.value == "RELEASE":  # Confirm
            if not self.__hasMoved():
                prefs.toggle_position[0] = self.init_x
                prefs.toggle_position[1] = self.init_y
                prefs.is_enabled = not prefs.is_enabled
            return FINISHED
        return MODAL

    def __hasMoved(self) -> bool:
        init = Vector((self.mouse_init_x, self.mouse_init_y))
        final = Vector((self.x, self.y))
        if (final - init).length > preferences().widget.menu_spacing / 2:
            return True
        return False


class SCULPT_DECK_GGT_touch_toggle(GizmoGroup):
    bl_label = "Sculpt Deck touch toggle"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"PERSISTENT", "SCALE"}

    def setup(self, context):
        # one button per state, the one not in use hidden
        self.on = self.button(ON_ICON)
        self.off = self.button(OFF_ICON)

    def button(self, icon: str) -> bpy.types.Gizmo:
        gizmo = self.gizmos.new("GIZMO_GT_button_2d")
        gizmo.target_set_operator(COMMAND)
        gizmo.icon = icon  # type: ignore
        gizmo.use_tooltip = True  # show operator description on hover
        gizmo.use_event_handle_all = True  # don't pass events e.g. shift+a to add
        gizmo.use_grab_cursor = False
        gizmo.show_drag = False  # show default cursor
        gizmo.line_width = 5.0
        gizmo.use_draw_modal = True  # show gizmo while dragging
        gizmo.draw_options = {"BACKDROP", "OUTLINE"}  # type: ignore
        gizmo.hide = True
        return gizmo

    def draw_prepare(self, context):
        settings = navigation_settings()
        primary = self.on if settings.is_enabled else self.off
        other = self.off if settings.is_enabled else self.on
        other.hide = True
        primary.hide = not toggle_shown(settings)

        colors = toggle_colors["active" if settings.is_enabled else "inactive"]
        primary.color = colors["color"]
        primary.color_highlight = colors["color_highlight"]
        primary.alpha = colors["alpha"]
        primary.alpha_highlight = colors["alpha_highlight"]
        primary.scale_basis = 18 * preferences().widget.gizmo_scale

        # the position is kept as a share of the viewport's safe area
        safe_area = safe_area_3d()
        span = safe_area[1] - safe_area[0]
        origin = Vector(
            (
                safe_area[0].x + span.x * settings.toggle_position[0] * 0.01,
                safe_area[0].y + span.y * settings.toggle_position[1] * 0.01,
                0.0,
            )
        )
        primary.matrix_basis = Matrix.Translation(origin)


classes = (
    SCULPT_DECK_OT_float_controller,
    SCULPT_DECK_GGT_touch_toggle,
)


register, unregister = bpy.utils.register_classes_factory(classes)
