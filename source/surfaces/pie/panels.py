# type: ignore
"""The Action Pie's sidebar panel: the pie's slots for the current mode."""

import bpy
from bpy.types import Panel, UILayout

from ...core.constants import pie_mode, pie_mode_items
from ...core.preferences import preferences
from ..action_slots import draw_action_slots

# pie positions, in the order Blender fills a pie
pie_slot_names = ("Left", "Right", "Bottom", "Top", "Top Left", "Top Right", "Bottom Left", "Bottom Right")

# slots listed clockwise from the top, for the settings UI
pie_slot_display_order = (4, 6, 2, 8, 3, 7, 1, 5)


# shared by the sidebar panel and the add-on preferences
def draw_action_pie(layout: UILayout, prefs, mode: str):
    menu = prefs.getMenuSettings(mode)
    if menu is not None:
        labels = [pie_slot_names[slot - 1] for slot in pie_slot_display_order]
        draw_action_slots(layout, menu, pie_slot_display_order, labels)


class SCULPT_DECK_PT_action_pie(Panel):
    bl_label = "Action Pie"
    bl_order = 60  # see SculptDeckPanel in core/ui.py
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sculpt Deck"
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        prefs = preferences()
        layout = self.layout
        layout.use_property_decorate = False
        mode = pie_mode(context.mode)
        names = {item[0]: item[1] for item in pie_mode_items}
        layout.label(text=f"Pie for {names[mode]}", icon="SETTINGS")
        layout.label(text="Open it from a widget or pen button", icon="INFO")
        draw_action_pie(layout, prefs, mode)


classes = (SCULPT_DECK_PT_action_pie,)


register, unregister = bpy.utils.register_classes_factory(classes)
