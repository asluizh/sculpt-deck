# type: ignore
"""Pen button settings per mode: a click and a hold for each button, plus the mouse/touch right click and double
click, which offer the actions of a pen button click. Held by the add-on preferences as `preferences().pen`."""

import bpy
from bpy.props import CollectionProperty, EnumProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup, UILayout

from ...core.actions import GESTURES, enum_items
from ...core.constants import pie_mode_items
from ...core.preferences import add_section, preferences, remove_section
from ..action_slots import find_mode_set

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
# not set yet (SCULPT_DECK_PG_PenSettings.ensure sets it) reads as a click
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


class SCULPT_DECK_PG_PenSettings(PropertyGroup):
    pen_sets: CollectionProperty(type=SCULPT_DECK_PG_PenModeSet)

    pen_mode_tab: EnumProperty(
        name="Buttons for Mode",
        items=pie_mode_items,
        default="SCULPT",
    )

    # the pen set of a mode, e.g. context.mode; modes without their own share one
    def getPenSet(self, mode: str):
        return find_mode_set(self.pen_sets, mode)

    def ensure(self):
        # modes, not the sets: adding to a collection can move its items
        new_modes = []
        for mode, _, _ in pie_mode_items:
            if self.getPenSet(mode) is None:
                self.pen_sets.add().mode = mode
                new_modes.append(mode)
        for pen_set in self.pen_sets:
            for slot, binding in pen_set.all_bindings():
                binding.mode = pen_set.mode
                binding.gesture = slot.upper() if slot in click_slots else "PEN_" + slot.rsplit("_", 1)[1].upper()
                # actions no longer offered for this button/gesture
                if binding.action == "":
                    binding.action = "DEFAULT"
        for mode in new_modes:
            pen_set = self.getPenSet(mode)
            for slot in click_slots:
                getattr(pen_set, slot).action = click_defaults[slot]
            for slot, action in pen_defaults.get(mode, {}).items():
                binding = getattr(pen_set, slot)
                if isinstance(action, tuple):
                    binding.action, ref = action
                    binding.setBrushRef(ref)
                else:
                    binding.action = action

    # pen_mode_tab is only the open tab, not a setting
    def to_dict(self):
        return {"pen_sets": [p.to_dict() for p in self.pen_sets]}

    def from_dict(self, data: dict):
        self.ensure()
        for saved in data.get("pen_sets", []):
            pen_set = self.getPenSet(saved.get("mode"))
            if pen_set is not None:
                pen_set.from_dict(saved)


def pen_settings() -> SCULPT_DECK_PG_PenSettings:
    return preferences().pen


def draw_preferences(layout: UILayout, settings):
    from .panel import draw_pen_buttons

    col = layout.column()
    col.prop(settings, "pen_mode_tab")
    draw_pen_buttons(col, settings.pen_mode_tab)


# the bindings and pen sets before the settings that hold them
classes = (
    SCULPT_DECK_PG_PenBinding,
    SCULPT_DECK_PG_PenModeSet,
    SCULPT_DECK_PG_PenSettings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    add_section("pen", SCULPT_DECK_PG_PenSettings, draw_preferences, tab="PEN", order=60)


def unregister():
    remove_section("pen")
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
