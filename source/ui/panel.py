# type: ignore
import bpy
from bpy.types import Panel, UILayout

from ..utils import settings
from ..utils.blender import preferences
from ..utils.constants import pie_mode, pie_mode_items


# Every sidebar sub-panel of SCULPT_DECK_PT_view_3d_panel sets its place with bl_order, spaced in tens, wherever
# it's defined (here, navigation, the surfaces, the features), so the order users see doesn't depend on which
# package registers first: Control Zones 10, Gizmo 20, Right Click 30, Double Click 40, Widget Buttons 50,
# Action Pie 60, Pen Buttons 70, Tool Options 80, Viewport Options 90, Default Settings 100.
class SculptDeckPanel:
    bl_label = "Sculpt Deck Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Sculpt Deck"


class SCULPT_DECK_PT_view_3d_panel(SculptDeckPanel, Panel):
    # bl_label = "Sculpt Deck Settings"

    def draw(self, context):
        prefs = preferences()

        layout = self.layout
        layout.use_property_decorate = False

        box = layout.box()
        box.label(
            text=UILayout.enum_item_description(prefs, "input_mode", prefs.input_mode),
            icon_value=UILayout.enum_item_icon(prefs, "input_mode", prefs.input_mode),
        )

        row = box.row()
        row.prop(prefs, "input_mode", expand=True)

        col = box.column(align=True)
        col.use_property_split = True
        col.prop(prefs, "lazy_mode")
        if prefs.input_mode == "FULL":
            col.prop(prefs, "enable_floating_toggle")


class SCULPT_DECK_PT_tool_settings(SculptDeckPanel, Panel):
    bl_label = "Tool Options"
    bl_order = 80
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        prefs = preferences()

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        layout.prop(prefs, "subdivision_limit", slider=True)


class SCULPT_DECK_PT_viewport_options(SculptDeckPanel, Panel):
    bl_label = "Viewport Options"
    bl_order = 90
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        prefs = preferences()

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        view = context.space_data
        space = context.area.spaces.active

        col = layout.column()
        col.operator("sculpt_deck.tools_region_flip", text="Flip Tools")
        if len(space.region_quadviews) > 0:
            col.operator("screen.region_quadview", text="Disable Quadview")
        else:
            col.operator("screen.region_quadview", text="Enable Quadview")

        col = layout.column(align=True)
        if not len(space.region_quadviews) > 0:
            col.prop(space, "lock_cursor", text="Lock to Cursor")
            col.prop(view.region_3d, "lock_rotation", text="Lock Rotation")


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


classes = (
    SCULPT_DECK_PT_view_3d_panel,
    SCULPT_DECK_PT_tool_settings,
    SCULPT_DECK_PT_viewport_options,
    # last, so it sits at the bottom
    SCULPT_DECK_PT_default_settings,
)


register, unregister = bpy.utils.register_classes_factory(classes)
