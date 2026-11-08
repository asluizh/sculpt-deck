# type: ignore
"""The object tap's setting: whether a tap selects or switches objects. Held by the add-on preferences as
`preferences().object_tap`."""

import bpy
from bpy.props import BoolProperty
from bpy.types import PropertyGroup, UILayout

from ...core.preferences import add_section, remove_section


class SCULPT_DECK_PG_ObjectTapSettings(PropertyGroup):
    tap_to_switch: BoolProperty(
        name="Tap to Select/Switch",
        description=(
            "Tap an object with a finger to select it (Object Mode) or to switch to it in the current mode "
            "(Edit, Sculpt and Paint modes). Dragging still moves the view"
        ),
        default=True,
    )

    def to_dict(self):
        return {"tap_to_switch": self.tap_to_switch}

    def from_dict(self, data: dict):
        self.tap_to_switch = data.get("tap_to_switch", True)


def draw_preferences(layout: UILayout, settings):
    box = layout.box()
    box.label(text="Object Tap")
    col = box.column()
    col.use_property_split = True
    col.prop(settings, "tap_to_switch")


def register():
    bpy.utils.register_class(SCULPT_DECK_PG_ObjectTapSettings)
    add_section("object_tap", SCULPT_DECK_PG_ObjectTapSettings, draw_preferences, order=20)


def unregister():
    remove_section("object_tap")
    bpy.utils.unregister_class(SCULPT_DECK_PG_ObjectTapSettings)
