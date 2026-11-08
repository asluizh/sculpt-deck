# type: ignore
"""The Control Zones sidebar panel: the touch navigation settings."""

import bpy
from bpy.types import Panel

from ..core.preferences import preferences
from ..core.ui import SculptDeckPanel


class SCULPT_DECK_PT_control_zones(SculptDeckPanel, Panel):
    bl_label = "Control Zones"
    bl_order = 10
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        prefs = preferences()

        layout = self.layout
        layout.use_property_decorate = False

        layout.prop(prefs, "is_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False

        prefs = preferences()

        layout.active = prefs.is_enabled
        layout.use_property_split = True

        col = layout.column(align=True)
        col.prop(prefs, "isVisible", text="Show Overlay")
        col.prop(prefs, "swap_panrotate")
        col.prop(prefs, "tap_to_switch")
        col.prop(prefs, "use_multiple_colors")

        col = layout.column()
        col.prop(prefs, "overlay_main_color", text="Main Color")
        if prefs.use_multiple_colors:
            col.prop(prefs, "overlay_secondary_color", text="Secondary Color")
        col.prop(prefs, "width", slider=True)
        col.prop(prefs, "radius", slider=True)


register, unregister = bpy.utils.register_classes_factory((SCULPT_DECK_PT_control_zones,))
