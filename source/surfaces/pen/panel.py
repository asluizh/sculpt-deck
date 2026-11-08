# type: ignore
import bpy
from bpy.types import Panel, UILayout

from ...core.constants import pie_mode, pie_mode_items
from ...core.preferences import preferences
from ...core.ui import SculptDeckPanel
from ...features.brush.history import brush_name


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


# one binding of a pen set: a pen button gesture, or the right click or double click
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
        op = row.operator("sculpt_deck.pen_use_active_brush", text="", icon="EYEDROPPER")
        op.mode = pen_set.mode
        op.slot = slot


class SCULPT_DECK_PT_pen_buttons(SculptDeckPanel, Panel):
    bl_label = "Pen Buttons"
    bl_order = 70
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        mode = pie_mode(context.mode)
        names = {item[0]: item[1] for item in pie_mode_items}
        layout.label(text=f"Pen buttons for {names[mode]}", icon="STYLUS_PRESSURE")
        draw_pen_buttons(layout, preferences(), mode)


register, unregister = bpy.utils.register_classes_factory((SCULPT_DECK_PT_pen_buttons,))
