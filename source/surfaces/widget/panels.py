# type: ignore
"""The Widget's sidebar panels (layout and buttons per mode) and its entry in the viewport's Gizmos popover."""

import bpy
from bpy.types import Panel, UILayout

from ...utils.blender import preferences
from ...utils.constants import WIDGET_SLOTS, pie_mode, pie_mode_items
from ..action_slots import draw_action_slots


# shared by the sidebar panel and the add-on preferences
def draw_widget_buttons(layout: UILayout, prefs, mode: str):
    widget = prefs.getWidgetSettings(mode)
    if widget is not None:
        slots = range(1, WIDGET_SLOTS + 1)
        draw_action_slots(layout, widget, slots, [f"Button {slot}" for slot in slots])


class WidgetPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sculpt Deck"
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}


class SCULPT_DECK_PT_gizmo_bar(WidgetPanel, Panel):
    bl_label = "Gizmo"

    def draw(self, context):
        prefs = preferences()

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column()
        col.prop(prefs, "menu_style", expand=True)

        if prefs.menu_style == "fixed.bar":
            col.prop(prefs, "gizmo_position")
        elif prefs.menu_style == "float.radial":
            col.prop(prefs, "menu_spacing", slider=True)

        col.prop(prefs, "gizmo_scale", slider=True)
        col.prop(prefs, "gizmo_padding", slider=True)


class SCULPT_DECK_PT_widget_buttons(WidgetPanel, Panel):
    bl_label = "Widget Buttons"

    def draw_header(self, context):
        self.layout.prop(preferences(), "show_menu", text="")

    def draw(self, context):
        prefs = preferences()
        layout = self.layout
        layout.use_property_decorate = False
        mode = pie_mode(context.mode)
        names = {item[0]: item[1] for item in pie_mode_items}
        layout.label(text=f"Buttons for {names[mode]}", icon="TOOL_SETTINGS")
        layout.label(text="Unusable buttons hide, e.g. voxel ones with Multires", icon="INFO")
        draw_widget_buttons(layout, prefs, mode)


# UI panel to append Gizmo menu
class SCULPT_DECK_PT_gizmo_display(Panel):
    bl_label = "Sculpt Deck Gizmos"
    bl_parent_id = "VIEW3D_PT_gizmo_display"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"

    def draw(self, context):
        prefs = preferences()

        col = self.layout.column()
        col.active = context.space_data.show_gizmo
        col.prop(prefs, "show_menu")
        col.label(text="Choose buttons in the sidebar: Sculpt Deck > Widget Buttons")


classes = (
    SCULPT_DECK_PT_gizmo_bar,
    SCULPT_DECK_PT_widget_buttons,
    SCULPT_DECK_PT_gizmo_display,
)


register, unregister = bpy.utils.register_classes_factory(classes)
