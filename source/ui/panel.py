# type: ignore
import bpy
from bpy.types import Menu, Panel, UILayout

from ..utils import settings
from ..utils.actions import TOOL_PREFIX, is_pie, operator_exists
from ..utils.blender import preferences
from ..utils.brush import brush_name
from ..utils.constants import (WIDGET_SLOTS, pie_actions, pie_common_actions,
                               pie_mode, pie_mode_actions, pie_mode_items,
                               pie_slot_display_order, pie_slot_names,
                               primitive_items)


# shared by the sidebar panel and the add-on preferences
def draw_pen_buttons(layout: UILayout, prefs, mode: str):
    pen_set = prefs.getPenSet(mode)
    if pen_set is None:
        return
    layout.label(text="Mouse and touch are not affected", icon="INFO")
    for button, label in (("lower", "Button 1 (lower)"), ("upper", "Button 2 (upper)")):
        box = layout.box()
        box.label(text=label, icon="STYLUS_PRESSURE")
        col = box.column()
        col.use_property_split = True
        for gesture, gesture_label in (("click", "Click"), ("hold", "Hold / Drag")):
            draw_binding(col, pen_set, button + "_" + gesture, gesture_label)


def draw_binding(col: UILayout, pen_set, slot: str, label: str):
    binding = getattr(pen_set, slot)
    col.prop(binding, "action", text=label)
    if binding.action == "CUSTOM":
        col.prop(binding, "operator", text=" ", placeholder="e.g. object.shade_smooth or VIEW3D_MT_add")
    elif binding.action == "BRUSH":
        split = col.split(factor=0.4)
        split.label(text="")
        row = split.row(align=True)
        row.label(text=brush_name(binding.brushRef()) or "No brush set", icon="BRUSH_DATA")
        op = row.operator("touchview.pen_use_active_brush", text="", icon="EYEDROPPER")
        op.mode = pen_set.mode
        op.slot = slot


# right click and double click: the same actions as a pen button click, for each mode
def draw_click_binding(layout: UILayout, prefs, mode: str, slot: str, enable: str):
    pen_set = prefs.getPenSet(mode)
    if pen_set is None:
        return
    col = layout.column()
    col.use_property_split = True
    col.active = getattr(prefs, enable)
    draw_binding(col, pen_set, slot, "Action")


# shared by the sidebar panels and the add-on preferences
def draw_action_slots(layout: UILayout, mode_set, slots, labels):
    col = layout.column()
    col.use_property_split = True
    for slot, label in zip(slots, labels):
        col.prop(mode_set, f"menu_choice_{slot}", text=label)
        if getattr(mode_set, f"menu_choice_{slot}") == "CUSTOM":
            col.prop(mode_set, f"menu_slot_{slot}", text=" ", placeholder="e.g. object.shade_smooth or VIEW3D_MT_add")


def draw_action_pie(layout: UILayout, prefs, mode: str):
    menu = prefs.getMenuSettings(mode)
    if menu is not None:
        labels = [pie_slot_names[slot - 1] for slot in pie_slot_display_order]
        draw_action_slots(layout, menu, pie_slot_display_order, labels)


def draw_widget_buttons(layout: UILayout, prefs, mode: str):
    widget = prefs.getWidgetSettings(mode)
    if widget is not None:
        slots = range(1, WIDGET_SLOTS + 1)
        draw_action_slots(layout, widget, slots, [f"Button {slot}" for slot in slots])


def draw_pie_slot(pie: UILayout, idname: str):
    # empty slots keep the others in place; the pie can't contain itself
    if not idname or idname == "TOUCHVIEW_MT_floating":
        pie.separator()
    else:
        draw_action(pie, idname)


# a button running an action, in a pie or a menu
def draw_action(layout: UILayout, idname: str):
    label, icon = pie_actions.get(idname, (None, "NONE"))
    text = {"text": label} if label else {}
    # popup menus run their buttons with EXEC by default, which skips file
    # browsers and popups (Save, Search); invoke them like widget buttons do
    layout.operator_context = "INVOKE_REGION_WIN"
    if idname.startswith(TOOL_PREFIX):
        layout.operator("wm.tool_set_by_id", icon=icon, **text).name = idname[len(TOOL_PREFIX):]
    elif "_AST_" in idname:
        layout.operator("wm.call_asset_shelf_popover", icon=icon, **text).name = idname
    elif "_MT_" in idname and is_pie(idname):
        layout.operator("wm.call_menu_pie", icon=icon, text=label or idname).name = idname
    elif "_MT_" in idname:
        layout.menu(idname, icon=icon, **text)
    elif operator_exists(idname):
        layout.operator(idname, icon=icon, **text)
    else:
        layout.label(text=f"Unknown: {idname}", icon="ERROR")


class TouchView:
    bl_label = "Touchview Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Touchview"


class TOUCHVIEW_PT_view_3d_panel(TouchView, Panel):
    # bl_label = "Touchview Settings"

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


class TOUCHVIEW_PT_control_zones(TouchView, Panel):
    bl_label = "Control Zones"
    bl_parent_id = "TOUCHVIEW_PT_view_3d_panel"
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

        row = layout.row()
        row.prop(prefs, "header_toggle_position", expand=True)

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


class TOUCHVIEW_PT_gizmo_bar(TouchView, Panel):
    bl_label = "Gizmo"
    bl_parent_id = "TOUCHVIEW_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

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


class ClickPanel(TouchView):
    bl_parent_id = "TOUCHVIEW_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}
    slot = ""
    enable = ""
    note = ""

    def draw_header(self, context):
        self.layout.prop(preferences(), self.enable, text="")

    def draw(self, context):
        prefs = preferences()
        layout = self.layout
        layout.use_property_decorate = False
        mode = pie_mode(context.mode)
        names = {item[0]: item[1] for item in pie_mode_items}
        layout.label(text=f"Action for {names[mode]}", icon="TOOL_SETTINGS")
        layout.label(text=self.note, icon="INFO")
        draw_click_binding(layout, prefs, mode, self.slot, self.enable)


class TOUCHVIEW_PT_right_click(ClickPanel, Panel):
    bl_label = "Right Click"
    slot = "right_click"
    enable = "enable_right_click"
    note = "Mouse and touch, not the pen"


class TOUCHVIEW_PT_double_click(ClickPanel, Panel):
    bl_label = "Double Click"
    slot = "double_click"
    enable = "enable_double_click"
    note = "Double tap or mouse double click"


class TOUCHVIEW_PT_widget_buttons(TouchView, Panel):
    bl_label = "Widget Buttons"
    bl_parent_id = "TOUCHVIEW_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

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


class TOUCHVIEW_PT_action_pie(TouchView, Panel):
    bl_label = "Action Pie"
    bl_parent_id = "TOUCHVIEW_PT_view_3d_panel"
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


class TOUCHVIEW_PT_pen_buttons(TouchView, Panel):
    bl_label = "Pen Buttons"
    bl_parent_id = "TOUCHVIEW_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        mode = pie_mode(context.mode)
        names = {item[0]: item[1] for item in pie_mode_items}
        layout.label(text=f"Pen buttons for {names[mode]}", icon="STYLUS_PRESSURE")
        draw_pen_buttons(layout, preferences(), mode)


class TOUCHVIEW_PT_tool_settings(TouchView, Panel):
    bl_label = "Tool Options"
    bl_parent_id = "TOUCHVIEW_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        prefs = preferences()

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        layout.prop(prefs, "subdivision_limit", slider=True)


class TOUCHVIEW_PT_viewport_options(TouchView, Panel):
    bl_label = "Viewport Options"
    bl_parent_id = "TOUCHVIEW_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        prefs = preferences()

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        view = context.space_data
        space = context.area.spaces.active

        col = layout.column()
        col.operator("touchview.tools_region_flip", text="Flip Tools")
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
    row.operator("touchview.save_default_settings", icon="FILE_TICK")
    row.operator("touchview.revert_settings", text="", icon="LOOP_BACK")


class TOUCHVIEW_PT_default_settings(TouchView, Panel):
    bl_label = "Default Settings"
    bl_parent_id = "TOUCHVIEW_PT_view_3d_panel"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return settings.is_unsaved()

    def draw(self, context):
        draw_default_settings(self.layout)


class TOUCHVIEW_PT_image_editor_panel(TouchView, Panel):
    bl_space_type = "IMAGE_EDITOR"

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
        col.prop(prefs, "is_enabled")
        subcol = col.column(align=True)
        subcol.active = prefs.is_enabled
        subcol.prop(prefs, "header_toggle_position", expand=True)


class TOUCHVIEW_PT_node_editor_panel(TouchView, Panel):
    bl_space_type = "NODE_EDITOR"

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
        col.prop(prefs, "is_enabled")
        subcol = col.column(align=True)
        subcol.active = prefs.is_enabled
        subcol.prop(prefs, "header_toggle_position", expand=True)


# UI panel to append Gizmo menu
class TOUCHVIEW_PT_gizmo_display(Panel):
    bl_label = "Touchview Gizmos"
    bl_parent_id = "VIEW3D_PT_gizmo_display"
    bl_space_type = "VIEW_3D"
    bl_region_type = "HEADER"

    def draw(self, context):
        prefs = preferences()

        col = self.layout.column()
        col.active = context.space_data.show_gizmo
        col.prop(prefs, "show_menu")
        col.label(text="Choose buttons in the sidebar: Touchview > Widget Buttons")


class TOUCHVIEW_MT_floating(Menu):
    """Touchview action pie"""

    bl_label = "Action Pie"
    bl_description = "Touchview action pie, set up per mode in the sidebar"

    def draw(self, context):
        menu = preferences().getMenuSettings(context.mode)
        pie = self.layout.menu_pie()
        for slot in range(1, 9):
            draw_pie_slot(pie, menu.slot(slot) if menu else "")


class TOUCHVIEW_MT_all_actions(Menu):
    """Every Touchview action for the current mode"""

    bl_label = "All Actions"

    def draw(self, context):
        actions = pie_mode_actions.get(pie_mode(context.mode), [])
        groups = (
            ("Actions", [action for action in actions if not action[0].startswith(TOOL_PREFIX)]),
            ("Tools", [action for action in actions if action[0].startswith(TOOL_PREFIX)]),
            ("Common", [action for action in pie_common_actions if action[0] != "TOUCHVIEW_MT_all_actions"]),
        )
        row = self.layout.row()
        for title, group in groups:
            if not group:
                continue
            col = row.column()
            col.label(text=title)
            col.separator()
            for idname, _, _ in group:
                draw_action(col, idname)


class TOUCHVIEW_MT_add_mesh(Menu):
    """Add a mesh and keep working on it in the current mode"""

    bl_label = "Add Mesh"

    def draw(self, context):
        for primitive, name, _, icon, _ in primitive_items:
            self.layout.operator("touchview.add_primitive", text=name, icon=icon).primitive = primitive


classes = (
    TOUCHVIEW_PT_view_3d_panel,
    TOUCHVIEW_PT_control_zones,
    TOUCHVIEW_PT_gizmo_bar,
    TOUCHVIEW_PT_right_click,
    TOUCHVIEW_PT_double_click,
    TOUCHVIEW_PT_widget_buttons,
    TOUCHVIEW_PT_action_pie,
    TOUCHVIEW_PT_pen_buttons,
    TOUCHVIEW_PT_tool_settings,
    TOUCHVIEW_PT_viewport_options,
    # last, so it sits at the bottom
    TOUCHVIEW_PT_default_settings,
    TOUCHVIEW_PT_image_editor_panel,
    TOUCHVIEW_PT_node_editor_panel,
    TOUCHVIEW_PT_gizmo_display,
    TOUCHVIEW_MT_floating,
    TOUCHVIEW_MT_add_mesh,
    TOUCHVIEW_MT_all_actions,
)


register, unregister = bpy.utils.register_classes_factory(classes)
