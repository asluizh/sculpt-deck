# type: ignore
"""Pen button settings per mode: a click and a hold for each button, plus the mouse/touch right click and double
click, which offer the actions of a pen button click. Saved with the add-on preferences (pen_sets)."""

import bpy
from bpy.props import EnumProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

from ...core.actions import GESTURES, enum_items

# pen side buttons arrive as mouse buttons with event.is_tablet set
pen_buttons = {
    "RIGHTMOUSE": "upper",
    "MIDDLEMOUSE": "lower",
}

pen_gestures = ("click", "hold")

# mouse and touch actions kept with the pen buttons of each mode, using the
# same actions as a pen button click
click_slots = ("right_click", "double_click")

click_defaults = {"right_click": "DEFAULT", "double_click": "screen.screen_full_area"}

# pen buttons of a new setup; button 1 is the lower one (BTN_STYLUS),
# button 2 the upper one (BTN_STYLUS2)
pen_defaults = {
    "SCULPT": {
        "lower_click": "sculpt_deck.brush_invert",
        "lower_hold": "sculpt_deck.brush_invert",
        "upper_click": "BRUSH_PREVIOUS",
        "upper_hold": ("BRUSH", ("ESSENTIALS", "", "brushes/essentials_brushes-mesh_sculpt.blend/Brush/Smooth")),
    },
}


# the Action List of a pen button click or hold, a double click or a right click; a gesture
# not set yet (ensurePenSets sets it) reads as a click
def pen_actions(binding, _):
    gesture = binding.gesture if binding.gesture in GESTURES else "PEN_CLICK"
    return enum_items(gesture, binding.mode)


class SCULPT_DECK_PG_PenBinding(PropertyGroup):
    mode: StringProperty(name="mode", default="OBJECT")
    # the Gesture, as named in core/actions.py: PEN_CLICK, PEN_HOLD, DOUBLE_CLICK or RIGHT_CLICK
    gesture: StringProperty(name="gesture", default="PEN_CLICK")
    action: EnumProperty(name="Action", items=pen_actions)
    operator: StringProperty(
        name="Custom Action",
        description="Operator (e.g. object.shade_smooth) or menu (e.g. VIEW3D_MT_add) to run",
    )
    brush_library_type: StringProperty()
    brush_library: StringProperty()
    brush_asset: StringProperty()

    def brushRef(self) -> tuple | None:
        if not self.brush_asset:
            return None
        return (self.brush_library_type, self.brush_library, self.brush_asset)

    def setBrushRef(self, ref: tuple):
        self.brush_library_type, self.brush_library, self.brush_asset = ref

    def to_dict(self):
        return {
            "action": self.action,
            "operator": self.operator,
            "brush": list(self.brushRef() or ()),
        }

    def from_dict(self, data: dict):
        try:
            self.action = data.get("action", "DEFAULT")
        except TypeError:
            self.action = "DEFAULT"
        self.operator = data.get("operator", "")
        brush = data.get("brush", [])
        if len(brush) == 3:
            self.setBrushRef(tuple(brush))


class SCULPT_DECK_PG_PenModeSet(PropertyGroup):
    mode: StringProperty(name="mode", default="OBJECT")
    upper_click: PointerProperty(type=SCULPT_DECK_PG_PenBinding)
    upper_hold: PointerProperty(type=SCULPT_DECK_PG_PenBinding)
    lower_click: PointerProperty(type=SCULPT_DECK_PG_PenBinding)
    lower_hold: PointerProperty(type=SCULPT_DECK_PG_PenBinding)
    # mouse/touch right click and double tap, with the actions of a pen button click
    right_click: PointerProperty(type=SCULPT_DECK_PG_PenBinding)
    double_click: PointerProperty(type=SCULPT_DECK_PG_PenBinding)

    def bindings(self):
        for button in pen_buttons.values():
            for gesture in pen_gestures:
                yield button + "_" + gesture, getattr(self, button + "_" + gesture)

    def all_bindings(self):
        yield from self.bindings()
        for slot in click_slots:
            yield slot, getattr(self, slot)

    def to_dict(self):
        return {"mode": self.mode, **{slot: binding.to_dict() for slot, binding in self.all_bindings()}}

    def from_dict(self, data: dict):
        for slot, binding in self.all_bindings():
            binding.from_dict(data.get(slot, {"action": click_defaults.get(slot, "DEFAULT")}))


# registered before the add-on preferences, which hold them in pen_sets
classes = (
    SCULPT_DECK_PG_PenBinding,
    SCULPT_DECK_PG_PenModeSet,
)


register, unregister = bpy.utils.register_classes_factory(classes)
