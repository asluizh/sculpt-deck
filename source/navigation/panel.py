# type: ignore
"""The touch navigation settings in the sidebar: the input mode at the top of the main panel, and the Control Zones
panel."""

import bpy
from bpy.types import Panel

from ..core.preferences import preferences
from ..core.ui import SCULPT_DECK_PT_view_3d_panel, SculptDeckPanel
from .settings import draw_control_zones, draw_input_mode, navigation_settings


def draw_main_panel(self, context):
    self.layout.use_property_decorate = False
    draw_input_mode(self.layout, navigation_settings(), description_as_label=True)


class SCULPT_DECK_PT_control_zones(SculptDeckPanel, Panel):
    bl_label = "Control Zones"
    bl_order = 10  # see SculptDeckPanel in core/ui.py
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        layout.use_property_decorate = False

        layout.prop(navigation_settings(), "is_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False

        settings = navigation_settings()

        layout.active = settings.is_enabled
        layout.use_property_split = True

        draw_control_zones(layout, settings, preferences().object_tap)


def register():
    bpy.utils.register_class(SCULPT_DECK_PT_control_zones)
    SCULPT_DECK_PT_view_3d_panel.append(draw_main_panel)


def unregister():
    SCULPT_DECK_PT_view_3d_panel.remove(draw_main_panel)
    bpy.utils.unregister_class(SCULPT_DECK_PT_control_zones)
