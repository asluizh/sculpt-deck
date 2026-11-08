# type: ignore
"""The double click and right click settings: whether each runs its action. The actions themselves are kept with the
pen buttons of each mode (pen/settings.py). Held by the add-on preferences as `preferences().clicks`."""

import bpy
from bpy.props import BoolProperty
from bpy.types import PropertyGroup, UILayout

from ...core.preferences import add_section, preferences, remove_section


class SCULPT_DECK_PG_ClickSettings(PropertyGroup):
    enable_double_click: BoolProperty(
        name="Double Click",
        description="Run an action on a double tap or double click, set for each mode",
        default=True,
    )

    enable_right_click: BoolProperty(
        name="Right Click",
        description="Run an action on a mouse or touch right click, set for each mode. Off: Blender's own right click",
        default=False,
    )

    def to_dict(self):
        return {
            "enable_double_click": self.enable_double_click,
            "enable_right_click": self.enable_right_click,
        }

    def from_dict(self, data: dict):
        self.enable_double_click = data.get("enable_double_click", True)
        self.enable_right_click = data.get("enable_right_click", False)


def click_settings() -> SCULPT_DECK_PG_ClickSettings:
    return preferences().clicks


def draw_preferences(layout: UILayout, settings):
    from .panel import draw_click_binding

    mode = preferences().pen.pen_mode_tab
    col = layout.column()
    for slot, label in (
        ("right_click", "Right Click (mouse/touch)"),
        ("double_click", "Double Click / Double Tap"),
    ):
        box = col.box()
        box.prop(settings, "enable_" + slot, text=label)
        draw_click_binding(box, mode, slot)


def register():
    bpy.utils.register_class(SCULPT_DECK_PG_ClickSettings)
    # after the pen buttons, in the same tab: the clicks show the bindings of the pen's mode tab
    add_section("clicks", SCULPT_DECK_PG_ClickSettings, draw_preferences, tab="PEN", order=70)


def unregister():
    remove_section("clicks")
    bpy.utils.unregister_class(SCULPT_DECK_PG_ClickSettings)
