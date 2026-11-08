# type: ignore
"""The Widget's sidebar panels (layout and buttons per mode) and its entry in the viewport's Gizmos popover."""

import bpy
from bpy.types import Panel

from ...core.constants import pie_mode, pie_mode_items
from .settings import draw_layout, draw_widget_buttons, widget_settings


class WidgetPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sculpt Deck"
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}


class SCULPT_DECK_PT_gizmo_bar(WidgetPanel, Panel):
    bl_label = "Gizmo"
    bl_order = 20  # see SculptDeckPanel in core/ui.py

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        draw_layout(layout, widget_settings())


class SCULPT_DECK_PT_widget_buttons(WidgetPanel, Panel):
    bl_label = "Widget Buttons"
    bl_order = 50  # see SculptDeckPanel in core/ui.py

    def draw_header(self, context):
        self.layout.prop(widget_settings(), "show_menu", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        mode = pie_mode(context.mode)
        names = {item[0]: item[1] for item in pie_mode_items}
        layout.label(text=f"Buttons for {names[mode]}", icon="TOOL_SETTINGS")
        layout.label(text="Unusable buttons hide, e.g. voxel ones with Multires", icon="INFO")
        draw_widget_buttons(layout, mode)


# UI panel to append Gizmo menu
class SCULPT_DECK_PT_gizmo_display(Panel):
    bl_label = "Sculpt Deck Gizmos"
    bl_parent_id = "VIEW3D_PT_gizmo_display"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"

    def draw(self, context):
        col = self.layout.column()
        col.active = context.space_data.show_gizmo
        col.prop(widget_settings(), "show_menu")
        col.label(text="Choose buttons in the sidebar: Sculpt Deck > Widget Buttons")


classes = (
    SCULPT_DECK_PT_gizmo_bar,
    SCULPT_DECK_PT_widget_buttons,
    SCULPT_DECK_PT_gizmo_display,
)


register, unregister = bpy.utils.register_classes_factory(classes)
