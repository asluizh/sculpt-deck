# type: ignore
"""The Widget's settings: its layout, its buttons for each mode and the initial ones, and which of the old fixed
buttons show. Held by the add-on preferences as `preferences().widget`."""

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, FloatVectorProperty
from bpy.types import PropertyGroup, UILayout

from ...core.blender import redraw_viewports
from ...core.constants import pie_mode, pie_mode_items
from ...core.preferences import add_section, preferences, remove_section
from ..action_slots import (
    WIDGET_SLOTS,
    SCULPT_DECK_PG_MenuModeGroup,
    draw_action_slots,
    ensure_mode_sets,
    find_mode_set,
)

# initial widget buttons per mode
widget_defaults = {
    "OBJECT": ("ed.undo", "ed.redo", "VIEW3D_MT_add", "sculpt_deck.cycle_control_gizmo",
               "sculpt_deck.viewport_recenter", "screen.screen_full_area", "sculpt_deck.toggle_n_panel",
               "sculpt_deck.increment_multires", "sculpt_deck.decrement_multires", "SCULPT_DECK_MT_floating"),
    "EDIT_MESH": ("ed.undo", "ed.redo", "SCULPT_DECK_MT_add_mesh", "sculpt_deck.cycle_control_gizmo",
                  "sculpt_deck.viewport_recenter", "screen.screen_full_area", "sculpt_deck.toggle_n_panel",
                  "SCULPT_DECK_MT_floating"),
    "SCULPT": ("ed.undo", "ed.redo", "SCULPT_DECK_MT_add_mesh", "sculpt_deck.viewport_recenter",
               "sculpt_deck.toggle_n_panel", "object.voxel_size_edit", "object.voxel_remesh",
               "sculpt_deck.increment_multires", "sculpt_deck.decrement_multires", "sculpt_deck.brush_resize",
               "sculpt_deck.brush_strength", "SCULPT_DECK_MT_floating"),
    "PAINT_VERTEX": ("ed.undo", "ed.redo", "SCULPT_DECK_MT_add_mesh", "sculpt_deck.viewport_recenter",
                     "screen.screen_full_area", "sculpt_deck.toggle_n_panel", "sculpt_deck.brush_resize",
                     "sculpt_deck.brush_strength", "SCULPT_DECK_MT_floating"),
    "PAINT_WEIGHT": ("ed.undo", "ed.redo", "SCULPT_DECK_MT_add_mesh", "sculpt_deck.viewport_recenter",
                     "screen.screen_full_area", "sculpt_deck.toggle_n_panel", "sculpt_deck.brush_resize",
                     "sculpt_deck.brush_strength", "SCULPT_DECK_MT_floating"),
    "PAINT_TEXTURE": ("ed.undo", "ed.redo", "SCULPT_DECK_MT_add_mesh", "sculpt_deck.viewport_recenter",
                      "screen.screen_full_area", "sculpt_deck.toggle_n_panel", "sculpt_deck.brush_resize",
                      "sculpt_deck.brush_strength", "SCULPT_DECK_MT_floating"),
    "PAINT_GREASE_PENCIL": ("ed.undo", "ed.redo", "sculpt_deck.viewport_recenter", "screen.screen_full_area",
                            "sculpt_deck.toggle_n_panel", "sculpt_deck.brush_resize", "sculpt_deck.brush_strength",
                            "SCULPT_DECK_MT_floating"),
    "OTHER": ("ed.undo", "ed.redo", "sculpt_deck.viewport_recenter", "screen.screen_full_area",
              "sculpt_deck.toggle_n_panel", "SCULPT_DECK_MT_floating"),
}

position_items = [
    ("TOP", "Top", "Set Gizmo position to top of viewport"),
    ("RIGHT", "Right", "Set Gizmo position to right of viewport"),
    ("BOTTOM", "Bottom", "Set Gizmo position to bottom of viewport"),
    ("LEFT", "Left", "Set Gizmo position to left of viewport"),
]

menu_style_items = [
    ("float.radial", "Floating Radial", ""),
    ("fixed.bar", "Fixed Bar", ""),
]

menu_orientation_items = [
    ("HORIZONTAL", "Horizontal", ""),
    ("VERTICAL", "Vertical", ""),
]

gizmo_sets = {
    # ALL includes only the modes in this list
    "ALL": {
        "undoredo",
        "show_fullscreen",
        "region_quadviews",
        "snap_view",
        "n_panel",
        "lock_rotation",
    },
    "SCULPT": {
        "control_gizmo",
        "pivot_mode",
        "voxel_remesh",
        "multires",
        "brush_dynamics",
    },
    "OBJECT": {"control_gizmo", "multires"},
    "EDIT_MESH": {"control_gizmo"},
    "POSE": {},
    "PAINT_TEXTURE": {"brush_dynamics"},
    "PAINT_VERTEX": {"brush_dynamics"},
    "PAINT_WEIGHT": {"brush_dynamics"},
    "SCULPT_CURVES": {"brush_dynamics"},
    "PAINT_GREASE_PENCIL": {"brush_dynamics"},
    "SCULPT_GREASE_PENCIL": {"brush_dynamics"},
    "WEIGHT_GREASE_PENCIL": {"brush_dynamics"},
    "VERTEX_GREASE_PENCIL": {"brush_dynamics"},
    "WEIGHT_GPENCIL": {"brush_dynamics"},
    "VERTEX_GPENCIL": {"brush_dynamics"},
    "SCULPT_GPENCIL": {"brush_dynamics"},
    "PAINT_GPENCIL": {"brush_dynamics"},
}


class SCULPT_DECK_PG_WidgetSettings(PropertyGroup):
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

    # widget buttons per mode, same actions as the pie
    widget_sets: CollectionProperty(type=SCULPT_DECK_PG_MenuModeGroup)

    active_widget: EnumProperty(
        name="Buttons for Mode",
        items=pie_mode_items,
        default="SCULPT",
    )

    # the widget buttons of a mode, e.g. context.mode; modes without their own share one
    def getWidgetSettings(self, mode: str):
        return find_mode_set(self.widget_sets, mode)

    def getGizmoSet(self, mode: str | int):
        available = list(gizmo_sets["ALL"])

        if mode not in list(gizmo_sets):
            return available
        return available + list(gizmo_sets[mode])

    def ensure(self):
        ensure_mode_sets(self.widget_sets, widget_defaults, "WIDGET")

    def to_dict(self):
        return {
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
            "widget_sets": [w.to_dict() for w in self.widget_sets],
            "active_widget": self.active_widget,
        }

    def from_dict(self, data: dict):
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
        self.widget_sets.clear()
        for widget in data.get("widget_sets", []):
            widget_set = self.widget_sets.add()
            widget_set.kind = "WIDGET"
            widget_set.from_dict(widget)
        self.active_widget = pie_mode(data.get("active_widget", "SCULPT"))
        self.ensure()


def widget_settings() -> SCULPT_DECK_PG_WidgetSettings:
    return preferences().widget


def draw_layout(layout: UILayout, settings):
    """The widget's style, place and size; shared by the sidebar panel and the add-on preferences"""
    col = layout.column()
    col.prop(settings, "menu_style", expand=True)

    if settings.menu_style == "fixed.bar":
        col.prop(settings, "gizmo_position")
    elif settings.menu_style == "float.radial":
        col.prop(settings, "menu_spacing", slider=True)

    col.prop(settings, "gizmo_scale", slider=True)
    col.prop(settings, "gizmo_padding", slider=True)


def draw_widget_buttons(layout: UILayout, mode: str):
    """The buttons of one mode; shared by the sidebar panel and the add-on preferences"""
    widget = widget_settings().getWidgetSettings(mode)
    if widget is not None:
        slots = range(1, WIDGET_SLOTS + 1)
        draw_action_slots(layout, widget, slots, [f"Button {slot}" for slot in slots])


def draw_preferences(layout: UILayout, settings):
    draw_layout(layout, settings)
    box = layout.box()
    box.label(text="Widget Buttons")
    box.prop(settings, "active_widget")
    draw_widget_buttons(box, settings.active_widget)


def register():
    bpy.utils.register_class(SCULPT_DECK_PG_WidgetSettings)
    add_section("widget", SCULPT_DECK_PG_WidgetSettings, draw_preferences, tab="GIZMO", order=40)


def unregister():
    remove_section("widget")
    bpy.utils.unregister_class(SCULPT_DECK_PG_WidgetSettings)
