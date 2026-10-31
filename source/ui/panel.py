# type: ignore
import bpy
from bpy.types import Menu, Panel, UILayout

from ..utils.blender import preferences
from ..utils.brush import brush_name
from ..utils.constants import (WIDGET_SLOTS, pie_actions, pie_mode,
                               pie_mode_items, pie_slot_display_order,
                               pie_slot_names, primitive_items)


# shared by the sidebar panel and the add-on preferences
def draw_pen_buttons(layout: UILayout, prefs):
    layout.row().prop(prefs, "pen_mode_tab", expand=True)
    pen_set = prefs.getPenSet(prefs.pen_mode_tab)
    if pen_set is None:
        return
    layout.label(text="Mouse and touch are not affected", icon="INFO")
    for button, label in (("upper", "Upper Button"), ("lower", "Lower Button")):
        box = layout.box()
        box.label(text=label, icon="STYLUS_PRESSURE")
        col = box.column()
        col.use_property_split = True
        for gesture, gesture_label in (("click", "Click"), ("hold", "Hold / Drag")):
            slot = button + "_" + gesture
            binding = getattr(pen_set, slot)
            col.prop(binding, "action", text=gesture_label)
            if binding.action == "OPERATOR":
                col.prop(binding, "operator", text="Operator")
            elif binding.action == "BRUSH":
                split = col.split(factor=0.4)
                split.label(text="")
                row = split.row(align=True)
                row.label(text=brush_name(binding.brushRef()) or "No brush set", icon="BRUSH_DATA")
                op = row.operator("touchview.pen_use_active_brush", text="", icon="EYEDROPPER")
                op.mode = pen_set.mode
                op.slot = slot


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


def operator_exists(idname: str) -> bool:
    try:
        category, name = idname.split(".")
        getattr(getattr(bpy.ops, category), name).get_rna_type()
    except (ValueError, AttributeError, KeyError):
        return False
    return True


def draw_pie_slot(pie: UILayout, idname: str):
    # empty slots keep the others in place; the pie can't contain itself
    if not idname or idname == "TOUCHVIEW_MT_floating":
        pie.separator()
        return
    label, icon = pie_actions.get(idname, (None, "NONE"))
    text = {"text": label} if label else {}
    if "_AST_" in idname:
        pie.operator("wm.call_asset_shelf_popover", icon=icon, **text).name = idname
    elif "_MT_" in idname and idname.endswith("_pie"):
        pie.operator("wm.call_menu_pie", icon=icon, text=label or idname).name = idname
    elif "_MT_" in idname:
        pie.menu(idname, icon=icon, **text)
    elif operator_exists(idname):
        pie.operator(idname, icon=icon, **text)
    else:
        pie.label(text=f"Unknown: {idname}", icon="ERROR")


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


class TOUCHVIEW_PT_right_click(TouchView, Panel):
    bl_label = "Right Click Actions"
    bl_parent_id = "TOUCHVIEW_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        prefs = preferences()

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column()
        col.prop(prefs, "right_click_source", text="Mouse/Touch", expand=True)
        col.prop(prefs, "right_click_mode", text="Mode", expand=True)


class TOUCHVIEW_PT_double_click(TouchView, Panel):
    bl_label = "Double Click Actions"
    bl_parent_id = "TOUCHVIEW_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        prefs = preferences()

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column()
        col.prop(prefs, "enable_double_click")
        col.prop(prefs, "double_click_mode", text="Mode", expand=True)


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
        draw_pen_buttons(layout, preferences())


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
    TOUCHVIEW_PT_image_editor_panel,
    TOUCHVIEW_PT_node_editor_panel,
    TOUCHVIEW_PT_gizmo_display,
    TOUCHVIEW_MT_floating,
    TOUCHVIEW_MT_add_mesh,
)


register, unregister = bpy.utils.register_classes_factory(classes)
