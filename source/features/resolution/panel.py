# type: ignore
"""The Tool Options sidebar panel: the Subdivision Limit that Multires Level Up stops at."""

import bpy
from bpy.types import Panel

from ...core.ui import SculptDeckPanel
from .settings import resolution_settings


class SCULPT_DECK_PT_tool_settings(SculptDeckPanel, Panel):
    bl_label = "Tool Options"
    bl_order = 80  # see SculptDeckPanel in core/ui.py
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        layout.prop(resolution_settings(), "subdivision_limit", slider=True)


register, unregister = bpy.utils.register_classes_factory((SCULPT_DECK_PT_tool_settings,))
