# type: ignore
import zlib

import bpy
from bpy.props import *
from bpy.types import AddonPreferences, PropertyGroup, UILayout

from .source.ui.panel import (draw_action_pie, draw_click_binding,
                              draw_default_settings, draw_pen_buttons,
                              draw_widget_buttons)
from .source.utils import settings
from .source.utils.constants import (WIDGET_SLOTS, click_defaults, click_slots,
                                     gizmo_sets, menu_defaults,
                                     menu_orientation_items, menu_style_items,
                                     pen_action_aliases, pen_action_numbers,
                                     pen_brush_items, pen_brush_modes,
                                     pen_button_items, pen_buttons,
                                     pen_defaults, pen_gestures,
                                     pen_hold_action, pen_resolution_actions,
                                     pie_common_actions, pie_mode,
                                     pie_mode_actions, pie_mode_aliases,
                                     pie_mode_items, pivot_items,
                                     position_items, widget_defaults,
                                     widget_only_actions)


def NODE_HT_sculpt_deck_header(s, c):
    prefs = c.preferences.addons[__package__].preferences
    layout = s.layout
    layout.separator()
    layout.prop(prefs, "is_enabled", toggle=True)


def update_header_toggle_position(c):
    prefs = c.preferences.addons[__package__].preferences
    bpy.types.NODE_HT_header.remove(NODE_HT_sculpt_deck_header)
    bpy.types.IMAGE_HT_header.remove(NODE_HT_sculpt_deck_header)
    if prefs.header_toggle_position == "LEFT":
        bpy.types.NODE_HT_header.prepend(NODE_HT_sculpt_deck_header)
        bpy.types.IMAGE_HT_header.prepend(NODE_HT_sculpt_deck_header)
    else:
        bpy.types.NODE_HT_header.append(NODE_HT_sculpt_deck_header)
        bpy.types.IMAGE_HT_header.append(NODE_HT_sculpt_deck_header)


# preference changes made outside the viewport (e.g. in the Preferences window)
# don't redraw the viewport gizmos on their own
def redraw_viewports(_, c):
    for window in c.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


##
# Action Menu Settings
##
# the pie uses the first 8 slots, the widget all of them
PIE_SLOTS = range(1, 9)
ALL_SLOTS = range(1, WIDGET_SLOTS + 1)

# dynamic enum items must stay referenced while Blender uses them
_pie_choice_cache: dict[tuple, list] = {}


# stable numbers keep stored choices valid when the catalog changes
def pie_choice_number(idname: str) -> int:
    return 2 + zlib.crc32(idname.encode()) % 1_000_000


def pie_choices(group, _):
    key = (group.mode, group.kind)
    if key not in _pie_choice_cache:
        items = [("NONE", "Empty", "Leave this slot empty", "BLANK1", 0)]
        widget_actions = widget_only_actions if group.kind == "WIDGET" else []
        for actions in (widget_actions, pie_mode_actions.get(group.mode, []), pie_common_actions):
            if actions:
                items.append(None)
            items += [(idname, label, idname, icon, pie_choice_number(idname)) for idname, label, icon in actions]
        items += [None, ("CUSTOM", "Custom...", "Type the name of an operator or menu", "SCRIPT", 1)]
        _pie_choice_cache[key] = items
    return _pie_choice_cache[key]


def pie_choice(slot: int):
    return EnumProperty(
        name="Pie Slot",
        description="Action for this position of the pie",
        items=pie_choices,
        update=lambda group, _: group.choiceChanged(slot),
    )


def pie_custom():
    return StringProperty(
        name="Custom Action",
        description="Operator (e.g. object.shade_smooth) or menu (e.g. VIEW3D_MT_add) to show in this slot",
        default="",
    )


class SCULPT_DECK_PG_MenuModeGroup(PropertyGroup):
    mode: StringProperty(name="mode", default="OBJECT")
    kind: StringProperty(name="kind", default="PIE")  # PIE or WIDGET
    menu_choice_1: pie_choice(1)
    menu_choice_2: pie_choice(2)
    menu_choice_3: pie_choice(3)
    menu_choice_4: pie_choice(4)
    menu_choice_5: pie_choice(5)
    menu_choice_6: pie_choice(6)
    menu_choice_7: pie_choice(7)
    menu_choice_8: pie_choice(8)
    menu_choice_9: pie_choice(9)
    menu_choice_10: pie_choice(10)
    menu_choice_11: pie_choice(11)
    menu_choice_12: pie_choice(12)
    # custom action of each slot (and the only setting in older versions)
    menu_slot_1: pie_custom()
    menu_slot_2: pie_custom()
    menu_slot_3: pie_custom()
    menu_slot_4: pie_custom()
    menu_slot_5: pie_custom()
    menu_slot_6: pie_custom()
    menu_slot_7: pie_custom()
    menu_slot_8: pie_custom()
    menu_slot_9: pie_custom()
    menu_slot_10: pie_custom()
    menu_slot_11: pie_custom()
    menu_slot_12: pie_custom()

    def choiceChanged(self, slot: int):
        if getattr(self, f"menu_choice_{slot}") != "CUSTOM":
            setattr(self, f"menu_slot_{slot}", "")

    # the operator or menu shown in a slot, "" when empty
    def slot(self, slot: int) -> str:
        choice = getattr(self, f"menu_choice_{slot}")
        if choice == "CUSTOM":
            return getattr(self, f"menu_slot_{slot}").strip()
        return "" if choice == "NONE" else choice

    def setSlot(self, slot: int, idname: str):
        known = {item[0] for item in pie_choices(self, None) if item}
        if not idname:
            setattr(self, f"menu_choice_{slot}", "NONE")
        elif idname in known:
            setattr(self, f"menu_choice_{slot}", idname)
        else:
            setattr(self, f"menu_choice_{slot}", "CUSTOM")
            setattr(self, f"menu_slot_{slot}", idname)

    # settings from older versions only have the text of each slot
    def migrate(self):
        for slot in ALL_SLOTS:
            text = getattr(self, f"menu_slot_{slot}")
            if getattr(self, f"menu_choice_{slot}") == "NONE" and text:
                self.setSlot(slot, text)

    def slots(self, count: int) -> list[str]:
        return [self.slot(slot) for slot in range(1, count + 1)]

    def to_dict(self):
        return {"mode": self.mode, **{f"menu_slot_{slot}": self.slot(slot) for slot in ALL_SLOTS}}

    def from_dict(self, data: dict):
        self.mode = pie_mode(data.get("mode", "OBJECT"))
        for slot in ALL_SLOTS:
            self.setSlot(slot, data.get(f"menu_slot_{slot}", ""))


##
# Pen Button Settings
##
_pen_action_cache: dict[tuple, list] = {}


# Button-only actions (Blender default, nothing, brush switching, the action
# pie), then the actions shared with the pie and the widget. A click can use
# most of them (not resolution changes); a hold only brushes and tools, used
# until the button is released
def pen_actions(binding, _):
    key = (binding.mode, binding.gesture)
    if key not in _pen_action_cache:
        is_brush_mode = binding.mode in pen_brush_modes
        items = list(pen_button_items) + (pen_brush_items if is_brush_mode else [])
        for actions in (widget_only_actions, pie_mode_actions.get(binding.mode, []), pie_common_actions):
            # Previous Brush is already above, with hold support
            actions = [
                action
                for action in actions
                if action[0] != "sculpt_deck.brush_previous"
                and action[0] not in pen_resolution_actions
                and (binding.gesture == "click" or pen_hold_action(action[0]))
            ]
            if actions:
                items.append(None)
            items += [
                (idname, label, idname, icon, pen_action_numbers.get(idname, 100 + pie_choice_number(idname)))
                for idname, label, icon in actions
            ]
        items += [None, ("CUSTOM", "Custom...", "Type the name of an operator or menu", "SCRIPT", 4)]
        _pen_action_cache[key] = items
    return _pen_action_cache[key]


class SCULPT_DECK_PG_PenBinding(PropertyGroup):
    mode: StringProperty(name="mode", default="OBJECT")
    gesture: StringProperty(name="gesture", default="click")  # click or hold
    action: EnumProperty(name="Action", items=pen_actions)
    operator: StringProperty(
        name="Custom Action",
        description="Operator (e.g. object.shade_smooth) or menu (e.g. VIEW3D_MT_add) to run",
    )
    brush_library_type: StringProperty()
    brush_library: StringProperty()
    brush_asset: StringProperty()

    def brushRef(self) -> tuple | None:
        if not self.brush_asset:
            return None
        return (self.brush_library_type, self.brush_library, self.brush_asset)

    def setBrushRef(self, ref: tuple):
        self.brush_library_type, self.brush_library, self.brush_asset = ref

    def to_dict(self):
        return {
            "action": self.action,
            "operator": self.operator,
            "brush": list(self.brushRef() or ()),
        }

    def from_dict(self, data: dict):
        action = data.get("action", "DEFAULT")
        try:
            self.action = pen_action_aliases.get(action, action)
        except TypeError:
            self.action = "DEFAULT"
        self.operator = data.get("operator", "")
        brush = data.get("brush", [])
        if len(brush) == 3:
            self.setBrushRef(tuple(brush))


class SCULPT_DECK_PG_PenModeSet(PropertyGroup):
    mode: StringProperty(name="mode", default="OBJECT")
    upper_click: PointerProperty(type=SCULPT_DECK_PG_PenBinding)
    upper_hold: PointerProperty(type=SCULPT_DECK_PG_PenBinding)
    lower_click: PointerProperty(type=SCULPT_DECK_PG_PenBinding)
    lower_hold: PointerProperty(type=SCULPT_DECK_PG_PenBinding)
    # mouse/touch right click and double tap, with the actions of a pen button click
    right_click: PointerProperty(type=SCULPT_DECK_PG_PenBinding)
    double_click: PointerProperty(type=SCULPT_DECK_PG_PenBinding)

    def bindings(self):
        for button in pen_buttons.values():
            for gesture in pen_gestures:
                yield button + "_" + gesture, getattr(self, button + "_" + gesture)

    def all_bindings(self):
        yield from self.bindings()
        for slot in click_slots:
            yield slot, getattr(self, slot)

    def to_dict(self):
        return {"mode": self.mode, **{slot: binding.to_dict() for slot, binding in self.all_bindings()}}

    def from_dict(self, data: dict):
        for slot, binding in self.all_bindings():
            binding.from_dict(data.get(slot, {"action": click_defaults.get(slot, "DEFAULT")}))


class SCULPT_DECK_AP_OverlaySettings(AddonPreferences):
    bl_idname = __package__

    ##
    # Viewport Control Options
    ##

    is_enabled: BoolProperty(
        name="Enable Controls",
        default=True,
    )

    header_toggle_position: EnumProperty(
        items=[
            ("LEFT", "Left", "Toggle position on the left"),
            ("RIGHT", "Right", "Toggle position on the right"),
        ],
        name="Header Toggle Position",
        default="RIGHT",
        update=lambda _, c: update_header_toggle_position(c),
    )

    lazy_mode: BoolProperty(
        name="Lazy Mode",
        default=False,
        description="always control camera when not touching selected object",
    )

    toggle_position: FloatVectorProperty(
        name="Toggle Position",
        soft_min=0,
        soft_max=100,
        size=2,
        default=(0, 0),
    )

    toggle_color: FloatVectorProperty(
        name="Toggle Button Color",
        default=(0.1, 0.1, 0.2, 0.5),
        subtype="COLOR",
        min=0.0,
        max=1.0,
        size=4,
    )

    isVisible: BoolProperty(
        name="Show Overlay",
        default=False,
    )

    auto_save_defaults: BoolProperty(
        name="Auto-Save Defaults",
        description=(
            "Save every change as the default settings for new and other files. "
            "Off: changes stay in the current file until saved as defaults from the sidebar"
        ),
        default=False,
        update=lambda self, _: settings.auto_save_changed(),
    )

    input_mode: EnumProperty(
        name="Input Mode",
        items=[
            ("FULL", "Full", "Mouse/Touch and Pen input", "CON_CAMERASOLVER", 0),
            ("PEN", "Pen", "Pen input only", "STYLUS_PRESSURE", 1),
            ("TOUCH", "Touch", "Mouse/Touch input only", "VIEW_PAN", 2),
        ],
        default="FULL",
        update=redraw_viewports,
    )

    enable_floating_toggle: BoolProperty(
        name="Floating Toggle",
        description=(
            "Show a floating button in the viewport (bottom-left by default, drag to move) "
            "that turns touch controls on/off. Always shown in Pen and Touch input modes"
        ),
        default=False,
        update=redraw_viewports,
    )

    enable_double_click: BoolProperty(
        name="Double Click",
        description="Run an action on a double tap or double click, set for each mode",
        default=True,
    )

    enable_right_click: BoolProperty(
        name="Right Click",
        description="Run an action on a mouse or touch right click, set for each mode. Off: Blender's own right click",
        default=False,
    )

    swap_panrotate: BoolProperty(
        name="Swap Pan/Rotate",
        default=False,
    )

    tap_to_switch: BoolProperty(
        name="Tap to Select/Switch",
        description=(
            "Tap an object with a finger to select it (Object Mode) or to switch to it in the current mode "
            "(Edit, Sculpt and Paint modes). Dragging still moves the view"
        ),
        default=True,
    )

    width: FloatProperty(
        name="Width",
        default=40.0,
        min=10.0,
        max=100,
    )

    radius: FloatProperty(
        name="Radius",
        default=35.0,
        min=10.0,
        max=100.0,
    )

    use_multiple_colors: BoolProperty(
        name="Multicolor Overlay",
        default=False,
    )

    overlay_main_color: FloatVectorProperty(
        name="Overlay Main Color",
        default=(1.0, 1.0, 1.0, 0.01),
        subtype="COLOR",
        min=0.0,
        max=1.0,
        size=4,
    )

    overlay_secondary_color: FloatVectorProperty(
        name="Overlay Secondary Color",
        default=(1.0, 1.0, 1.0, 0.01),
        subtype="COLOR",
        min=0.0,
        max=1.0,
        size=4,
    )

    ##
    # Gizmo Options
    ##

    show_menu: BoolProperty(
        name="Show Widget",
        description="Show the floating widget buttons in the viewport",
        default=True,
        update=redraw_viewports,
    )

    show_gizmos: BoolProperty(
        name="Toggle Gizmos on Menu",
        default=True,
    )

    menu_style: EnumProperty(
        name="Menu Style",
        items=menu_style_items,
        default="float.radial",
        update=redraw_viewports,
    )

    gizmo_position: EnumProperty(
        name="Gizmo Position",
        items=position_items,
        default="RIGHT",
        update=redraw_viewports,
    )

    menu_orientation: EnumProperty(
        name="Menu Orientation",
        items=menu_orientation_items,
        default="HORIZONTAL",
    )

    menu_spacing: FloatProperty(
        name="Menu Scale",
        min=1,
        max=2,
        default=1,
    )

    gizmo_scale: FloatProperty(
        name="Gizmo Scale",
        min=1,
        max=2,
        default=1,
    )

    gizmo_padding: FloatProperty(
        name="Gizmo Padding",
        subtype="PIXEL",
        min=0,
        soft_max=24,
        default=4,
    )

    menu_position: FloatVectorProperty(
        name="Menu Position",
        soft_min=0,
        soft_max=100,
        size=2,
        default=(100, 0),
    )

    show_undoredo: BoolProperty(
        name="Undo/Redo",
        default=True,
    )

    show_is_enabled: BoolProperty(
        name="Toggle Touch",
        default=True,
    )

    show_control_gizmo: BoolProperty(
        name="Toggle Control Gizmo",
        default=True,
    )

    show_show_fullscreen: BoolProperty(
        name="Fullscreen",
        default=True,
    )

    show_region_quadviews: BoolProperty(
        name="Quadview",
        default=True,
    )

    show_pivot_mode: BoolProperty(
        name="Pivot Mode",
        default=True,
    )

    show_snap_view: BoolProperty(
        name="Snap View",
        default=True,
    )

    show_n_panel: BoolProperty(
        name="N Panel",
        default=True,
    )

    show_lock_rotation: BoolProperty(
        name="Rotation Lock",
        default=True,
    )

    show_multires: BoolProperty(
        name="Multires",
        default=True,
    )

    show_voxel_remesh: BoolProperty(
        name="Voxel Remesh",
        default=True,
    )
    show_brush_dynamics: BoolProperty(
        name="Brush Dynamics",
        default=True,
    )

    subdivision_limit: IntProperty(
        name="Subdivision Limit",
        default=4,
        min=1,
        max=7,
    )

    pivot_mode: EnumProperty(
        name="Sculpt Pivot Mode",
        items=pivot_items,
        default="SURFACE",
    )

    ##
    # Topology Control
    ##

    topology_mode: EnumProperty(
        name="Topology Mode",
        items=[
            ("MANUAL", "manual", "user-defined vertex density"),
            ("RELATIVE", "relative", "relative mesh vertex density steps"),
            (
                "RELATIVE-EXP",
                "exponential",
                "relative mesh vertex density steps with scaling",
            ),
        ],
        default="MANUAL",
    )

    ##
    # Action Menu Options
    ##

    # the pie's old floating button, only read to give it a widget button instead
    show_float_menu: BoolProperty(default=False)

    menu_sets: CollectionProperty(
        type=SCULPT_DECK_PG_MenuModeGroup,
        options={"LIBRARY_EDITABLE"},
    )

    # widget buttons per mode, same actions as the pie
    widget_sets: CollectionProperty(type=SCULPT_DECK_PG_MenuModeGroup)

    active_widget: EnumProperty(
        name="Buttons for Mode",
        items=pie_mode_items,
        default="SCULPT",
    )

    ##
    # Pen Button Options
    ##

    pen_sets: CollectionProperty(type=SCULPT_DECK_PG_PenModeSet)

    pen_mode_tab: EnumProperty(
        name="Buttons for Mode",
        items=pie_mode_items,
        default="SCULPT",
    )

    ##
    # UI Panel Controls
    ##

    active_menu: EnumProperty(
        name="Pie for Mode",
        items=pie_mode_items,
    )

    gizmo_tabs: EnumProperty(
        name="Gizmo Tabs",
        items=[
            ("GIZMO", "Gizmo", "", 0),
            ("ACTIONS", "Action", "", 1),
            ("PEN", "Pen & Clicks", "", 2),
        ],
        default="GIZMO",
    )

    def to_dict(self):
        return {
            "is_enabled": self.is_enabled,
            "header_toggle_position": self.header_toggle_position,
            "lazy_mode": self.lazy_mode,
            "enable_floating_toggle": self.enable_floating_toggle,
            "toggle_position": list(self.toggle_position),
            "toggle_color": list(self.toggle_color),
            "is_visible": self.isVisible,
            "auto_save_defaults": self.auto_save_defaults,
            "input_mode": self.input_mode,
            "enable_double_click": self.enable_double_click,
            "enable_right_click": self.enable_right_click,
            "swap_panrotate": self.swap_panrotate,
            "tap_to_switch": self.tap_to_switch,
            "width": self.width,
            "radius": self.radius,
            "use_multiple_colors": self.use_multiple_colors,
            "overlay_main_color": list(self.overlay_main_color),
            "overlay_secondary_color": list(self.overlay_secondary_color),
            "show_menu": self.show_menu,
            "show_gizmos": self.show_gizmos,
            "menu_style": self.menu_style,
            "menu_orientation": self.menu_orientation,
            "menu_spacing": self.menu_spacing,
            "gizmo_padding": self.gizmo_padding,
            "gizmo_scale": self.gizmo_scale,
            "menu_position": list(self.menu_position),
            "show_undoredo": self.show_undoredo,
            "show_is_enabled": self.show_is_enabled,
            "show_control_gizmo": self.show_control_gizmo,
            "show_show_fullscreen": self.show_show_fullscreen,
            "show_region_quadviews": self.show_region_quadviews,
            "show_pivot_mode": self.show_pivot_mode,
            "show_snap_view": self.show_snap_view,
            "show_n_panel": self.show_n_panel,
            "show_lock_rotation": self.show_lock_rotation,
            "show_multires": self.show_multires,
            "show_voxel_remesh": self.show_voxel_remesh,
            "show_brush_dynamics": self.show_brush_dynamics,
            "gizmo_position": self.gizmo_position,
            "subdivision_limit": self.subdivision_limit,
            "pivot_mode": self.pivot_mode,
            "topology_mode": self.topology_mode,
            "show_float_menu": self.show_float_menu,
            "active_menu": self.active_menu,
            "gizmo_tabs": self.gizmo_tabs,
            "menu_sets": [m.to_dict() for m in self.menu_sets],
            "widget_sets": [w.to_dict() for w in self.widget_sets],
            "active_widget": self.active_widget,
            "pen_sets": [p.to_dict() for p in self.pen_sets],
        }

    def from_dict(self, data: dict):
        self.is_enabled = data.get("is_enabled", True)
        self.header_toggle_position = data.get("header_toggle_position", "RIGHT")
        self.lazy_mode = data.get("lazy_mode", False)
        self.enable_floating_toggle = data.get("enable_floating_toggle", False)
        self.toggle_position = data.get("toggle_position", (0, 0))
        self.toggle_color = data.get("toggle_color", (0.1, 0.1, 0.2, 0.5))
        self.isVisible = data.get("is_visible", False)
        self.auto_save_defaults = data.get("auto_save_defaults", False)
        self.input_mode = data.get("input_mode", "FULL")
        self.enable_double_click = data.get("enable_double_click", True)
        # before 4.5 right click was on by default, with its own short list of actions
        self.enable_right_click = data.get("enable_right_click", False) and "right_click_source" not in data
        self.swap_panrotate = data.get("swap_panrotate", False)
        self.tap_to_switch = data.get("tap_to_switch", True)
        self.width = data.get("width", 40.0)
        self.radius = data.get("radius", 35.0)
        self.use_multiple_colors = data.get("use_multiple_colors", False)
        self.overlay_main_color = data.get("overlay_main_color", (1.0, 1.0, 1.0, 0.01))
        self.overlay_secondary_color = data.get("overlay_secondary_color", (1.0, 1.0, 1.0, 0.01))
        self.show_menu = data.get("show_menu", True)
        self.show_gizmos = data.get("show_gizmos", True)
        self.menu_style = data.get("menu_style", "float.radial")
        self.menu_orientation = data.get("menu_orientation", "HORIZONTAL")
        self.menu_spacing = data.get("menu_spacing", 1.0)
        self.gizmo_scale = data.get("gizmo_scale", 1.0)
        self.gizmo_padding = data.get("gizmo_padding", 4.0)
        self.menu_position = data.get("menu_position", (100, 0))
        self.show_undoredo = data.get("show_undoredo", True)
        self.show_is_enabled = data.get("show_is_enabled", True)
        self.show_control_gizmo = data.get("show_control_gizmo", True)
        self.show_show_fullscreen = data.get("show_show_fullscreen", True)
        self.show_region_quadviews = data.get("show_region_quadviews", True)
        self.show_pivot_mode = data.get("show_pivot_mode", True)
        self.show_snap_view = data.get("show_snap_view", True)
        self.show_n_panel = data.get("show_n_panel", True)
        self.show_lock_rotation = data.get("show_lock_rotation", True)
        self.show_multires = data.get("show_multires", True)
        self.show_voxel_remesh = data.get("show_voxel_remesh", True)
        self.show_brush_dynamics = data.get("show_brush_dynamics", True)
        self.gizmo_position = data.get("gizmo_position", "RIGHT")
        self.subdivision_limit = data.get("subdivision_limit", 4)
        self.pivot_mode = data.get("pivot_mode", "SURFACE")
        self.topology_mode = data.get("topology_mode", "MANUAL")
        self.show_float_menu = data.get("show_float_menu", False)
        self.active_menu = pie_mode(data.get("active_menu", "OBJECT"))
        self.gizmo_tabs = data.get("gizmo_tabs", "GIZMO")
        self.menu_sets.clear()
        for menu in data.get("menu_sets", []):
            self.menu_sets.add().from_dict(menu)
        self.widget_sets.clear()
        for widget in data.get("widget_sets", []):
            widget_set = self.widget_sets.add()
            widget_set.kind = "WIDGET"
            widget_set.from_dict(widget)
        self.active_widget = pie_mode(data.get("active_widget", "SCULPT"))
        self.ensureMenuSets()

        self.ensurePenSets()
        for saved in data.get("pen_sets", []):
            pen_set = self.getPenSet(saved.get("mode"))
            if pen_set is not None:
                pen_set.from_dict(saved)
        # the old "pen" right click source becomes an upper pen button binding
        if data.get("right_click_source") == "PEN" and "pen_sets" not in data:
            for pen_set in self.pen_sets:
                pen_set.upper_click.action = "CUSTOM"
                pen_set.upper_click.operator = data.get("right_click_mode", "wm.window_fullscreen_toggle")

    def load(self):
        settings.load_defaults()

    def draw_v4(self, context):
        pass

    # set up addon preferences UI
    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False

        box = layout.box()
        box.prop(self, "auto_save_defaults")
        draw_default_settings(box)

        # Input Mode
        box = layout.box()
        box.label(text="Input Mode")
        box.use_property_split = True

        col = box.column()
        col.prop(self, "input_mode", text=UILayout.enum_item_description(self, "input_mode", self.input_mode), expand=True)
        col = box.column(align=True)
        col.prop(self, "lazy_mode")
        if self.input_mode == "FULL":
            col.prop(self, "enable_floating_toggle")

        # Control Zones
        box = layout.box()
        box.prop(self, "is_enabled", text="Control Zones")

        col = box.column()
        col.use_property_split = True
        col.active = self.is_enabled

        col = col.column()
        col.prop(self, "header_toggle_position", expand=True)
        col = col.column(align=True)
        col.prop(self, "isVisible", text="Show Overlay")
        col.prop(self, "swap_panrotate")
        col.prop(self, "tap_to_switch")
        col.prop(self, "use_multiple_colors")
        col = col.column()
        col.prop(self, "overlay_main_color", text="Main Color")
        if self.use_multiple_colors:
            col.prop(self, "overlay_secondary_color", text="Secondary Color")
        col.prop(self, "width", slider=True)
        col.prop(self, "radius", slider=True)

        # Gixmo Options
        main_box = layout.box()

        col = main_box.row(align=True)
        col.prop(self, "gizmo_tabs", expand=True)

        main_box.use_property_split = True
        col = main_box.column()

        if self.gizmo_tabs == "GIZMO":
            row = col.row()
            row.prop(self, "menu_style", expand=True)

            if self.menu_style == "fixed.bar":
                col.prop(self, "gizmo_position")
            elif self.menu_style == "float.radial":
                col.prop(self, "menu_spacing", slider=True)

            col.prop(self, "gizmo_scale", slider=True)
            col.prop(self, "gizmo_padding", slider=True)

            box = main_box.box()
            box.label(text="Widget Buttons")
            box.prop(self, "active_widget")
            draw_widget_buttons(box, self, self.active_widget)

            col = main_box.column()
            col.label(text="Tool Settings")
            col.prop(self, "subdivision_limit", slider=True)

        if self.gizmo_tabs == "PEN":
            col.prop(self, "pen_mode_tab")
            draw_pen_buttons(col, self, self.pen_mode_tab)
            for slot, enable, label in (
                ("right_click", "enable_right_click", "Right Click (mouse/touch)"),
                ("double_click", "enable_double_click", "Double Click / Double Tap"),
            ):
                box = col.box()
                box.prop(self, enable, text=label)
                draw_click_binding(box, self, self.pen_mode_tab, slot, enable)

        if self.gizmo_tabs == "ACTIONS":
            col.label(text="Open the pie from a widget or pen button", icon="INFO")
            col.prop(self, "active_menu")
            draw_action_pie(col, self, self.active_menu)

    ##
    # Data Accessors
    ##
    # the pie or widget buttons for a mode, e.g. context.mode; modes without
    # their own share one
    def getMenuSettings(self, mode: str):
        return self.findModeSet(self.menu_sets, mode)

    def getWidgetSettings(self, mode: str):
        return self.findModeSet(self.widget_sets, mode)

    def findModeSet(self, collection, mode: str):
        mode = pie_mode(mode)
        for mode_set in collection:
            if mode_set.mode == mode:
                return mode_set
        return None

    def ensureMenuSets(self):
        kinds = ((self.menu_sets, menu_defaults, "PIE"), (self.widget_sets, widget_defaults, "WIDGET"))
        for collection, defaults, kind in kinds:
            for mode_set in collection:
                mode_set.kind = kind
                alias = pie_mode_aliases.get(mode_set.mode)
                if alias is not None and self.findModeSet(collection, alias) is None:
                    mode_set.mode = alias
            for mode, _, _ in pie_mode_items:
                if self.findModeSet(collection, mode) is None:
                    mode_set = collection.add()
                    mode_set.mode = mode
                    mode_set.kind = kind
                    for slot, idname in enumerate(defaults.get(mode, ()), 1):
                        mode_set.setSlot(slot, idname)
            for mode_set in collection:
                mode_set.migrate()

        # the pie used to have a floating button of its own, now it's a widget button
        if self.show_float_menu:
            self.show_float_menu = False
            for widget in self.widget_sets:
                slots = widget.slots(WIDGET_SLOTS)
                if "SCULPT_DECK_MT_floating" not in slots and "" in slots:
                    widget.setSlot(slots.index("") + 1, "SCULPT_DECK_MT_floating")

    def getPenSet(self, mode: str):
        return self.findModeSet(self.pen_sets, mode)

    def ensurePenSets(self):
        # modes, not the sets: adding to a collection can move its items
        new_modes = []
        for mode, _, _ in pie_mode_items:
            if self.getPenSet(mode) is None:
                self.pen_sets.add().mode = mode
                new_modes.append(mode)
        for pen_set in self.pen_sets:
            for slot, binding in pen_set.all_bindings():
                binding.mode = pen_set.mode
                binding.gesture = "click" if slot in click_slots else slot.rsplit("_", 1)[1]
                # actions no longer offered for this button/gesture
                if binding.action == "":
                    binding.action = "DEFAULT"
        for mode in new_modes:
            pen_set = self.getPenSet(mode)
            for slot in click_slots:
                getattr(pen_set, slot).action = click_defaults[slot]
            for slot, action in pen_defaults.get(mode, {}).items():
                binding = getattr(pen_set, slot)
                if isinstance(action, tuple):
                    binding.action, ref = action
                    binding.setBrushRef(ref)
                else:
                    binding.action = action


    def getGizmoSet(self, mode: str | int):
        available = list(gizmo_sets["ALL"])

        if mode not in list(gizmo_sets):
            return available
        return available + list(gizmo_sets[mode])

    def getShowLock(self):
        return self.show_lock

    def getWidth(self):
        return self.width / 100

    def getRadius(self):
        return self.radius / 100


classes = (
    SCULPT_DECK_PG_MenuModeGroup,
    SCULPT_DECK_PG_PenBinding,
    SCULPT_DECK_PG_PenModeSet,
    SCULPT_DECK_AP_OverlaySettings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    bpy.types.NODE_HT_header.remove(NODE_HT_sculpt_deck_header)
    bpy.types.IMAGE_HT_header.remove(NODE_HT_sculpt_deck_header)
