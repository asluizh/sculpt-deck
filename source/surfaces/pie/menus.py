# type: ignore
"""The Action Pie menu and the All Actions popup, and how either draws a button running an Action."""

import bpy
from bpy.types import Menu, UILayout

from ...core import actions as catalog
from ...utils.actions import TOOL_PREFIX, is_pie, operator_exists
from ...utils.blender import preferences
from ...utils.constants import pie_mode
from ..action_slots import PIE_SLOTS


def draw_pie_slot(pie: UILayout, idname: str):
    # empty slots keep the others in place; the pie can't contain itself
    if not idname or idname == "SCULPT_DECK_MT_floating":
        pie.separator()
    else:
        draw_action(pie, idname)


# a button running an action, in a pie or a menu
def draw_action(layout: UILayout, idname: str):
    known = catalog.find(idname)
    label, icon = (known.label, known.icon) if known else (None, "NONE")
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


class SCULPT_DECK_MT_floating(Menu):
    """Sculpt Deck action pie"""

    bl_label = "Action Pie"
    bl_description = "Sculpt Deck action pie, set up per mode in the sidebar"

    def draw(self, context):
        menu = preferences().getMenuSettings(context.mode)
        pie = self.layout.menu_pie()
        for slot in PIE_SLOTS:
            draw_pie_slot(pie, menu.slot(slot) if menu else "")


class SCULPT_DECK_MT_all_actions(Menu):
    """Every Sculpt Deck action for the current mode"""

    bl_label = "All Actions"

    def draw(self, context):
        actions = catalog.mode_actions(pie_mode(context.mode))
        groups = (
            ("Actions", [action for action in actions if not action.idname.startswith(TOOL_PREFIX)]),
            ("Tools", [action for action in actions if action.idname.startswith(TOOL_PREFIX)]),
            ("Common", [action for action in catalog.common_actions()
                        if action.idname != "SCULPT_DECK_MT_all_actions"]),
        )
        row = self.layout.row()
        for title, group in groups:
            if not group:
                continue
            col = row.column()
            col.label(text=title)
            col.separator()
            for action in group:
                draw_action(col, action.idname)


classes = (
    SCULPT_DECK_MT_floating,
    SCULPT_DECK_MT_all_actions,
)


register, unregister = bpy.utils.register_classes_factory(classes)
