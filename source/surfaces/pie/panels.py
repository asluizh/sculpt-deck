# type: ignore
"""The Action Pie's sidebar panel: the pie's slots for the current mode."""

import bpy
from bpy.types import Panel

from ...core.constants import pie_mode, pie_mode_items
from .settings import draw_action_pie


class SCULPT_DECK_PT_action_pie(Panel):
    bl_label = "Action Pie"
    bl_order = 60  # see SculptDeckPanel in core/ui.py
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sculpt Deck"
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        mode = pie_mode(context.mode)
        names = {item[0]: item[1] for item in pie_mode_items}
        layout.label(text=f"Pie for {names[mode]}", icon="SETTINGS")
        layout.label(text="Open it from a widget or pen button", icon="INFO")
        draw_action_pie(layout, mode)


classes = (SCULPT_DECK_PT_action_pie,)


register, unregister = bpy.utils.register_classes_factory(classes)
