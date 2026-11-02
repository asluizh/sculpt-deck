import bpy

# Running the shared pie/widget/pen actions. An idname is an operator, a menu
# (_MT_; a pie when it ends in _pie, like the action pie), a brush asset shelf
# (_AST_) or a tool (TOOL:).
TOOL_PREFIX = "TOOL:"


def is_pie(idname: str) -> bool:
    return idname.endswith("_pie") or idname == "TOUCHVIEW_MT_floating"


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


class ToolHistory:
    """Recently used tools per mode, polled with the brush history, so a tool
    can hand back to the one used before it"""

    size = 8

    def __init__(self):
        self.recent: dict[str, list[str]] = {}

    def update(self, context):
        tool = active_tool(context)
        if not tool:
            return
        recent = self.recent.setdefault(context.mode, [])
        if recent and recent[-1] == tool:
            return
        if tool in recent:
            recent.remove(tool)
        recent.append(tool)
        del recent[: -self.size]

    def previous(self, mode: str, skip: set[str], default: str) -> str:
        for tool in reversed(self.recent.get(mode, [])):
            if tool not in skip:
                return tool
        return default


tool_history = ToolHistory()


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
