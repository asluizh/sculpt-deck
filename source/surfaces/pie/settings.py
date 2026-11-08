# type: ignore
"""The Action Pie's settings: its slots for each mode and the initial ones. Held by the add-on preferences as
`preferences().pie`."""

import bpy
from bpy.props import CollectionProperty, EnumProperty
from bpy.types import PropertyGroup, UILayout

from ...core.constants import pie_mode, pie_mode_items
from ...core.preferences import add_section, preferences, remove_section
from ..action_slots import SCULPT_DECK_PG_MenuModeGroup, draw_action_slots, ensure_mode_sets, find_mode_set

# initial slots of a new pie, in pie order (left, right, bottom, top, ...)
menu_defaults = {
    "OBJECT": ("VIEW3D_MT_add", "object.delete", "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie",
               "object.duplicate_move", "SCULPT_DECK_MT_all_actions", "ed.undo_history", "screen.redo_last"),
    "EDIT_MESH": ("VIEW3D_MT_edit_mesh_select_mode", "VIEW3D_MT_edit_mesh_delete", "VIEW3D_MT_object_mode_pie",
                  "VIEW3D_MT_view_pie", "view3d.edit_mesh_extrude_move_normal", "SCULPT_DECK_MT_all_actions",
                  "VIEW3D_MT_edit_mesh_merge", "screen.redo_last"),
    "SCULPT": ("VIEW3D_AST_brush_sculpt", "VIEW3D_MT_mask", "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie",
               "VIEW3D_MT_face_sets", "SCULPT_DECK_MT_all_actions", "ed.undo_history", "SCULPT_DECK_MT_add_mesh"),
    "PAINT_VERTEX": ("VIEW3D_AST_brush_vertex_paint", "paint.sample_color", "VIEW3D_MT_object_mode_pie",
                     "VIEW3D_MT_view_pie", "paint.brush_colors_flip", "SCULPT_DECK_MT_all_actions", "", ""),
    "PAINT_WEIGHT": ("VIEW3D_AST_brush_weight_paint", "paint.weight_sample", "VIEW3D_MT_object_mode_pie",
                     "VIEW3D_MT_view_pie", "paint.weight_gradient", "SCULPT_DECK_MT_all_actions", "", ""),
    "PAINT_TEXTURE": ("VIEW3D_AST_brush_texture_paint", "paint.sample_color", "VIEW3D_MT_object_mode_pie",
                      "VIEW3D_MT_view_pie", "paint.brush_colors_flip", "SCULPT_DECK_MT_all_actions", "", ""),
    "PAINT_GREASE_PENCIL": ("VIEW3D_AST_brush_gpencil_paint", "GREASE_PENCIL_MT_layer_active",
                            "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie",
                            "grease_pencil.insert_blank_frame", "SCULPT_DECK_MT_all_actions", "", ""),
    "OTHER": ("ed.undo", "ed.redo", "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie", "",
              "SCULPT_DECK_MT_all_actions", "", ""),
}

# pie positions, in the order Blender fills a pie
pie_slot_names = ("Left", "Right", "Bottom", "Top", "Top Left", "Top Right", "Bottom Left", "Bottom Right")

# slots listed clockwise from the top, for the settings UI
pie_slot_display_order = (4, 6, 2, 8, 3, 7, 1, 5)


class SCULPT_DECK_PG_PieSettings(PropertyGroup):
    menu_sets: CollectionProperty(
        type=SCULPT_DECK_PG_MenuModeGroup,
        options={"LIBRARY_EDITABLE"},
    )

    active_menu: EnumProperty(
        name="Pie for Mode",
        items=pie_mode_items,
    )

    # the pie of a mode, e.g. context.mode; modes without their own share one
    def getMenuSettings(self, mode: str):
        return find_mode_set(self.menu_sets, mode)

    def ensure(self):
        ensure_mode_sets(self.menu_sets, menu_defaults, "PIE")

    def to_dict(self):
        return {
            "active_menu": self.active_menu,
            "menu_sets": [m.to_dict() for m in self.menu_sets],
        }

    def from_dict(self, data: dict):
        self.active_menu = pie_mode(data.get("active_menu", "OBJECT"))
        self.menu_sets.clear()
        for menu in data.get("menu_sets", []):
            self.menu_sets.add().from_dict(menu)
        self.ensure()


def pie_settings() -> SCULPT_DECK_PG_PieSettings:
    return preferences().pie


def draw_action_pie(layout: UILayout, mode: str):
    """The pie of one mode; shared by the sidebar panel and the add-on preferences"""
    menu = pie_settings().getMenuSettings(mode)
    if menu is not None:
        labels = [pie_slot_names[slot - 1] for slot in pie_slot_display_order]
        draw_action_slots(layout, menu, pie_slot_display_order, labels)


def draw_preferences(layout: UILayout, settings):
    col = layout.column()
    col.label(text="Open the pie from a widget or pen button", icon="INFO")
    col.prop(settings, "active_menu")
    draw_action_pie(col, settings.active_menu)


def register():
    bpy.utils.register_class(SCULPT_DECK_PG_PieSettings)
    add_section("pie", SCULPT_DECK_PG_PieSettings, draw_preferences, tab="ACTIONS", order=50)


def unregister():
    remove_section("pie")
    bpy.utils.unregister_class(SCULPT_DECK_PG_PieSettings)
