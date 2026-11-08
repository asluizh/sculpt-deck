# type: ignore
import bpy
from bpy.types import Panel, UILayout

from ...core.constants import pie_mode, pie_mode_items
from ...core.ui import SculptDeckPanel
from ..pen.panel import draw_binding
from ..pen.settings import pen_settings
from .settings import click_settings


# right click and double click: the same actions as a pen button click, for each mode;
# shared by the sidebar panels and the add-on preferences
def draw_click_binding(layout: UILayout, mode: str, slot: str):
    pen_set = pen_settings().getPenSet(mode)
    if pen_set is None:
        return
    col = layout.column()
    col.use_property_split = True
    col.active = getattr(click_settings(), "enable_" + slot)
    draw_binding(col, pen_set, slot, "Action")


class ClickPanel(SculptDeckPanel):
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}
    slot = ""
    enable = ""
    note = ""

    def draw_header(self, context):
        self.layout.prop(click_settings(), self.enable, text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        mode = pie_mode(context.mode)
        names = {item[0]: item[1] for item in pie_mode_items}
        layout.label(text=f"Action for {names[mode]}", icon="TOOL_SETTINGS")
        layout.label(text=self.note, icon="INFO")
        draw_click_binding(layout, mode, self.slot)


class SCULPT_DECK_PT_right_click(ClickPanel, Panel):
    bl_label = "Right Click"
    bl_order = 30
    slot = "right_click"
    enable = "enable_right_click"
    note = "Mouse and touch, not the pen"


class SCULPT_DECK_PT_double_click(ClickPanel, Panel):
    bl_label = "Double Click"
    bl_order = 40
    slot = "double_click"
    enable = "enable_double_click"
    note = "Double tap or mouse double click"


register, unregister = bpy.utils.register_classes_factory((SCULPT_DECK_PT_right_click, SCULPT_DECK_PT_double_click))
