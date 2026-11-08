# type: ignore
"""The Sculpt Deck sidebar: the main panel every part's sub-panels sit in, and the Default Settings panel at the
bottom."""

import bpy
from bpy.types import Panel

from . import settings


# Every sidebar sub-panel of SCULPT_DECK_PT_view_3d_panel sets its place with bl_order, spaced in tens, wherever
# it's defined (navigation, the surfaces, the features, here), so the order users see doesn't depend on which
# package registers first: Control Zones 10, Gizmo 20, Right Click 30, Double Click 40, Widget Buttons 50,
# Action Pie 60, Pen Buttons 70, Tool Options 80, Viewport Options 90, Default Settings 100.
class SculptDeckPanel:
    bl_label = "Sculpt Deck Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sculpt Deck"


# the parts draw into it with append (navigation's input mode) or as sub-panels
class SCULPT_DECK_PT_view_3d_panel(SculptDeckPanel, Panel):

    def draw(self, context):
        self.layout.use_property_decorate = False


def draw_default_settings(layout):
    """Save Default Settings and Revert, when the settings differ from the defaults"""
    if not settings.is_unsaved():
        return
    col = layout.column(align=True)
    col.label(text="Settings differ from the defaults", icon="INFO")
    col.label(text="They're kept in this file when it's saved")
    row = layout.row(align=True)
    row.operator("sculpt_deck.save_default_settings", icon="FILE_TICK")
    row.operator("sculpt_deck.revert_settings", text="", icon="LOOP_BACK")


class SCULPT_DECK_PT_default_settings(SculptDeckPanel, Panel):
    bl_label = "Default Settings"
    bl_order = 100
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return settings.is_unsaved()

    def draw(self, context):
        draw_default_settings(self.layout)


# the main panel first: the sub-panels of every part need it registered
classes = (
    SCULPT_DECK_PT_view_3d_panel,
    SCULPT_DECK_PT_default_settings,
)


register, unregister = bpy.utils.register_classes_factory(classes)
