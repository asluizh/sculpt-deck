import bpy
from mathutils import Matrix, Vector

from ...core.actions import find
from ...utils.actions import TOOL_PREFIX, operator_exists
from ...utils.blender import *
from ...utils.constants import (action_toggles, multires_actions,
                               popup_actions, voxel_actions)
from .gizmo_config import gizmo_colors, toggle_colors

##
# GizmoSet
#   - single-state
#     - one icon
#     - one action
#     - possible toggle by variable state
#
#   - 2-state (boolean)
#     - 2 icons
#     - 2 actions (or 1 action for both icons)
#
##


class GizmoSet:
    group: bpy.types.GizmoGroup

    def setup(self, group: bpy.types.GizmoGroup, config: dict):
        self.visible = True
        self.config = config
        self.has_dependent = "has_dependent" in config or False
        self.group = group
        self.scale = config["scale"] if ("scale" in config) else 14
        self.binding = config["binding"]
        self.has_attribute_bind = self.binding["attribute"] if "attribute" in self.binding else False
        self.primary = self.__buildGizmo(config["command"], config["icon"])

    def draw_prepare(self):
        prefs = preferences()
        self.hidden = not prefs.show_gizmos
        self.skip_draw = False
        self.__updatevisible()

        if self.binding["name"] in {"menu_controller"}:
            self.primary.hide = "float" not in prefs.menu_style or not prefs.show_menu
            self.primary.use_grab_cursor = False
            self.primary.show_drag = True
        if self.binding["name"] in {"menu_controller"}:
            self.primary.scale_basis = (36 * prefs.menu_spacing) * prefs.gizmo_scale
            self.primary.use_grab_cursor = False
            self.primary.show_drag = True
        else:
            self.primary.scale_basis = 18 * prefs.gizmo_scale

    def move(self, position: Vector):
        self.primary.matrix_basis = Matrix.Translation(position)

    def __updatevisible(self):
        if not preferences().show_menu and self.binding["name"] not in ["float_menu"]:
            self.visible = False
            self.primary.hide = True
            return
        if self.binding["location"] == "prefs":
            self.visible = getattr(preferences(), "show_" + self.binding["name"]) and self.binding["name"] in preferences().getGizmoSet(
                bpy.context.mode
            )

        if self.visible:
            self.visible = self.__visibilityLock() and not self.__checkAttributeBind()
        self.primary.hide = not self.visible

    def __visibilityLock(self) -> bool:
        if preferences().menu_style == "fixed.bar":
            return True
        return not self.hidden

    # if an attribute being assigned to active_object should hide/show bpy.types.Gizmo
    def __checkAttributeBind(self):
        if not self.has_attribute_bind:
            return False
        bind = self.binding["attribute"]
        state = self.__findAttribute(bind["path"], bind["value"]) == bind["state"]
        return not state

    # search for attribute, value through context.
    # will traverse bpy.types.bpy_prop_collection entries
    # by next attr to value comparison
    def __findAttribute(self, path: str, value: str):
        names = path.split(".")
        current = bpy.context
        for i, prop in enumerate(names):
            current = getattr(current, prop)
            if current is None:
                return False

            if isinstance(current, bpy.types.bpy_prop_collection):
                item = ""
                for item in current:
                    if getattr(item, names[i + 1]) == value:
                        return True
                return False
        return getattr(current, value)

    # initialize each gizmo, add them to named list with icon name(s)
    def __buildGizmo(self, command: str, icon: str) -> bpy.types.Gizmo:
        gizmo = self.group.gizmos.new("GIZMO_GT_button_2d")
        gizmo.target_set_operator(command)
        gizmo.icon = icon  # type: ignore
        gizmo.use_tooltip = True  # show operator description on hover
        gizmo.use_event_handle_all = True  # don't pass events e.g. shift+a to add
        gizmo.use_grab_cursor = "use_grab_cursor" in self.config
        gizmo.show_drag = False  # show default cursor
        gizmo.line_width = 5.0
        gizmo.use_draw_modal = True  # show gizmo while dragging
        gizmo.draw_options = {"BACKDROP", "OUTLINE"}  # type: ignore
        self.__setColors(gizmo)
        gizmo.scale_basis = 0.1
        return gizmo

    def __setColors(self, gizmo: bpy.types.Gizmo):
        gizmo.color = gizmo_colors["active"]["color"]
        gizmo.color_highlight = gizmo_colors["active"]["color_highlight"]
        gizmo.alpha = gizmo_colors["active"]["alpha"]
        gizmo.alpha_highlight = gizmo_colors["active"]["alpha_highlight"]


class GizmoSetBoolean(GizmoSet):
    def setup(self, group: bpy.types.GizmoGroup, config: dict):
        self.visible = True
        self.config = config
        self.has_dependent = "has_dependent" in config or False
        self.group = group
        self.scale = config["scale"] if ("scale" in config) else 14
        self.binding = config["binding"]
        self.has_attribute_bind = self.binding["attribute"] if "attribute" in self.binding else False
        self.onGizmo = self._GizmoSet__buildGizmo(config["command"], config["onIcon"])  # type: ignore
        self.offGizmo = self._GizmoSet__buildGizmo(config["command"], config["offIcon"])  # type: ignore
        self.__setActiveGizmo(True)

    def __setActiveGizmo(self, state: bool):
        self.onGizmo.hide = True
        self.offGizmo.hide = True
        self.primary = self.onGizmo if state else self.offGizmo

    def draw_prepare(self):
        prefs = preferences()
        self.hidden = not prefs.show_gizmos
        self.skip_draw = False
        self.__updatevisible()
        self.primary.scale_basis = 18 * prefs.gizmo_scale
        self.primary.use_grab_cursor = False
        if self.binding["name"] == "float_toggle":
            self.__setToggleColors(self.primary)

    def __updatevisible(self):
        prefs = preferences()
        bind = self.binding
        # the floating toggle is a standalone button, independent of the gizmo menu
        if bind["name"] == "float_toggle":
            self.visible = prefs.input_mode != "FULL" or prefs.enable_floating_toggle
            self.__setActiveGizmo(prefs.is_enabled)
            self.primary.hide = not self.visible
            return
        if not preferences().show_menu and (bind["name"] not in ["float_menu"]):
            self.visible = False
            self.primary.hide = True
            return
        self.visible = getattr(preferences(), "show_" + self.binding["name"])

        if self.visible:
            self.visible = (
                self._GizmoSet__visibilityLock()  # type: ignore
                and not self._GizmoSet__checkAttributeBind()  # type: ignore
            )  # type: ignore

        self.__setActiveGizmo(self._GizmoSet__findAttribute(bind["location"], bind["name"]))  # type: ignore
        self.primary.hide = not self.visible

    def __setToggleColors(self, gizmo: bpy.types.Gizmo):
        mode = "active" if preferences().is_enabled else "inactive"
        gizmo.color = toggle_colors[mode]["color"]
        gizmo.color_highlight = toggle_colors[mode]["color_highlight"]
        gizmo.alpha = toggle_colors[mode]["alpha"]
        gizmo.alpha_highlight = toggle_colors[mode]["alpha_highlight"]


class GizmoSetEnum(GizmoSet):
    gizmos: list[bpy.types.Gizmo]

    def setup(self, group: bpy.types.GizmoGroup, config):
        pass


def resolve_context_path(context, path: str):
    value = context
    for name in path.split("."):
        value = getattr(value, name, None)
        if value is None:
            return None
    return value


def action_icon(context, idname: str) -> str:
    toggle = action_toggles.get(idname)
    if toggle is not None:
        path, on_icon, off_icon = toggle
        state = resolve_context_path(context, path)
        is_on = len(state) > 0 if isinstance(state, bpy.types.bpy_prop_collection) else bool(state)
        return on_icon if is_on else off_icon
    known = find(idname)
    if known is not None:
        return known.icon
    return "COLLAPSEMENU" if "_MT_" in idname else "SCRIPT"


def action_available(context, idname: str) -> bool:
    if idname not in voxel_actions and idname not in multires_actions:
        return True
    obj = context.active_object
    if obj is None or obj.type != "MESH":
        return False
    has_multires = any(mod.type == "MULTIRES" for mod in obj.modifiers)
    return has_multires if idname in multires_actions else not has_multires


class ActionGizmo:
    """A widget button running one of the shared pie/widget actions"""

    # undo/redo and multires up/down stay next to each other in the radial menu
    pairs = {"ed.undo": "ed.redo", "sculpt_deck.increment_multires": "sculpt_deck.decrement_multires"}

    def __init__(self, group: bpy.types.GizmoGroup, context, idname: str):
        self.idname = idname
        self.visible = True
        self.skip_draw = False
        self.has_dependent = False
        self.primary = group.gizmos.new("GIZMO_GT_button_2d")
        self.set_target(idname)
        gizmo = self.primary
        gizmo.icon = action_icon(context, idname)  # type: ignore
        gizmo.use_tooltip = True  # show the action's description on hover
        gizmo.use_event_handle_all = True  # don't pass events e.g. shift+a to add
        gizmo.use_grab_cursor = False
        gizmo.show_drag = False  # show default cursor
        gizmo.line_width = 5.0
        gizmo.use_draw_modal = True  # show gizmo while dragging
        gizmo.draw_options = {"BACKDROP", "OUTLINE"}  # type: ignore
        gizmo.color = gizmo_colors["active"]["color"]
        gizmo.color_highlight = gizmo_colors["active"]["color_highlight"]
        gizmo.alpha = gizmo_colors["active"]["alpha"]
        gizmo.alpha_highlight = gizmo_colors["active"]["alpha_highlight"]

    def set_target(self, idname: str):
        if "_AST_" in idname or "_MT_" in idname or idname in popup_actions:
            self.primary.target_set_operator("sculpt_deck.widget_menu").name = idname
        elif idname.startswith(TOOL_PREFIX):
            self.primary.target_set_operator("wm.tool_set_by_id").name = idname[len(TOOL_PREFIX):]
        elif operator_exists(idname):
            self.primary.target_set_operator(idname)

    def draw_prepare(self, context):
        prefs = preferences()
        self.skip_draw = False
        self.visible = (
            prefs.show_menu
            and (prefs.menu_style == "fixed.bar" or prefs.show_gizmos)
            and action_available(context, self.idname)
        )
        self.primary.hide = not self.visible
        self.primary.scale_basis = 18 * prefs.gizmo_scale

    def move(self, position: Vector):
        self.primary.matrix_basis = Matrix.Translation(position)
