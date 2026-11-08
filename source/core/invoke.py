"""Running an Action by idname (the catalog is in actions.py). An idname is an operator, a menu (_MT_; a pie when it
ends in _pie, like the Action Pie), a brush asset shelf (_AST_) or a tool (TOOL:)."""

import bpy

from .actions import TOOL_PREFIX


def is_pie(idname: str) -> bool:
    return idname.endswith("_pie") or idname == "SCULPT_DECK_MT_floating"


def operator_exists(idname: str) -> bool:
    try:
        category, name = idname.split(".")
        getattr(getattr(bpy.ops, category), name).get_rna_type()
    except (ValueError, AttributeError, KeyError):
        return False
    return True


def active_tool(context) -> str:
    tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
    return tool.idname if tool else ""


def set_tool(tool: str):
    bpy.ops.wm.tool_set_by_id(name=tool)  # type: ignore


def invoke_action(idname: str):
    if idname.startswith(TOOL_PREFIX):
        set_tool(idname[len(TOOL_PREFIX):])
    elif "_AST_" in idname:
        bpy.ops.wm.call_asset_shelf_popover("INVOKE_DEFAULT", name=idname)  # type: ignore
    elif "_MT_" in idname:
        if is_pie(idname):
            bpy.ops.wm.call_menu_pie("INVOKE_DEFAULT", name=idname)  # type: ignore
        else:
            bpy.ops.wm.call_menu("INVOKE_DEFAULT", name=idname)  # type: ignore
    else:
        category, name = idname.split(".")
        getattr(getattr(bpy.ops, category), name)("INVOKE_DEFAULT")
