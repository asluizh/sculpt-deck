# type: ignore
"""The per-mode Action slots shared by the Widget and the Action Pie: one group of slots for each mode, whose choices
are the Gesture's Action List (WIDGET or PIE), and how they're drawn in the sidebar and the add-on preferences."""

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import PropertyGroup, UILayout

from ..core.actions import enum_items
from ..core.constants import pie_mode

WIDGET_SLOTS = 12

# the pie uses the first 8 slots, the widget all of them
PIE_SLOTS = range(1, 9)
ALL_SLOTS = range(1, WIDGET_SLOTS + 1)


# the Action List of a Widget button or an Action Pie slot (kind WIDGET or PIE)
def pie_choices(group, _):
    return enum_items(group.kind, group.mode)


def pie_choice(slot: int):
    return EnumProperty(
        name="Pie Slot",
        description="Action for this position of the pie",
        items=pie_choices,
        update=lambda group, _: group.choiceChanged(slot),
    )


def pie_custom():
    return StringProperty(
        name="Custom Action",
        description="Operator (e.g. object.shade_smooth) or menu (e.g. VIEW3D_MT_add) to show in this slot",
        default="",
    )


class SCULPT_DECK_PG_MenuModeGroup(PropertyGroup):
    mode: StringProperty(name="mode", default="OBJECT")
    kind: StringProperty(name="kind", default="PIE")  # PIE or WIDGET
    menu_choice_1: pie_choice(1)
    menu_choice_2: pie_choice(2)
    menu_choice_3: pie_choice(3)
    menu_choice_4: pie_choice(4)
    menu_choice_5: pie_choice(5)
    menu_choice_6: pie_choice(6)
    menu_choice_7: pie_choice(7)
    menu_choice_8: pie_choice(8)
    menu_choice_9: pie_choice(9)
    menu_choice_10: pie_choice(10)
    menu_choice_11: pie_choice(11)
    menu_choice_12: pie_choice(12)
    # custom action of each slot (and the only setting in older versions)
    menu_slot_1: pie_custom()
    menu_slot_2: pie_custom()
    menu_slot_3: pie_custom()
    menu_slot_4: pie_custom()
    menu_slot_5: pie_custom()
    menu_slot_6: pie_custom()
    menu_slot_7: pie_custom()
    menu_slot_8: pie_custom()
    menu_slot_9: pie_custom()
    menu_slot_10: pie_custom()
    menu_slot_11: pie_custom()
    menu_slot_12: pie_custom()

    def choiceChanged(self, slot: int):
        if getattr(self, f"menu_choice_{slot}") != "CUSTOM":
            setattr(self, f"menu_slot_{slot}", "")

    # the operator or menu shown in a slot, "" when empty
    def slot(self, slot: int) -> str:
        choice = getattr(self, f"menu_choice_{slot}")
        if choice == "CUSTOM":
            return getattr(self, f"menu_slot_{slot}").strip()
        return "" if choice == "NONE" else choice

    def setSlot(self, slot: int, idname: str):
        known = {item[0] for item in pie_choices(self, None) if item}
        if not idname:
            setattr(self, f"menu_choice_{slot}", "NONE")
        elif idname in known:
            setattr(self, f"menu_choice_{slot}", idname)
        else:
            setattr(self, f"menu_choice_{slot}", "CUSTOM")
            setattr(self, f"menu_slot_{slot}", idname)

    # settings from older versions only have the text of each slot
    def migrate(self):
        for slot in ALL_SLOTS:
            text = getattr(self, f"menu_slot_{slot}")
            if getattr(self, f"menu_choice_{slot}") == "NONE" and text:
                self.setSlot(slot, text)

    def slots(self, count: int) -> list[str]:
        return [self.slot(slot) for slot in range(1, count + 1)]

    def to_dict(self):
        return {"mode": self.mode, **{f"menu_slot_{slot}": self.slot(slot) for slot in ALL_SLOTS}}

    def from_dict(self, data: dict):
        self.mode = pie_mode(data.get("mode", "OBJECT"))
        for slot in ALL_SLOTS:
            self.setSlot(slot, data.get(f"menu_slot_{slot}", ""))


# shared by the sidebar panels and the add-on preferences
def draw_action_slots(layout: UILayout, mode_set, slots, labels):
    col = layout.column()
    col.use_property_split = True
    for slot, label in zip(slots, labels):
        col.prop(mode_set, f"menu_choice_{slot}", text=label)
        if getattr(mode_set, f"menu_choice_{slot}") == "CUSTOM":
            col.prop(mode_set, f"menu_slot_{slot}", text=" ", placeholder="e.g. object.shade_smooth or VIEW3D_MT_add")


# registered before the add-on preferences, whose menu_sets and widget_sets hold it
classes = (SCULPT_DECK_PG_MenuModeGroup,)


register, unregister = bpy.utils.register_classes_factory(classes)
