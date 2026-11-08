# type: ignore
"""The interface's setting: the Sculpt pivot mode that Use next Pivot mode steps through, and that navigation sets
before it rotates the view. Held by the add-on preferences as `preferences().interface`."""

import bpy
from bpy.props import EnumProperty
from bpy.types import PropertyGroup

from ...core.preferences import add_section, remove_section

pivot_items = [
    ("SURFACE", "Surface", "Sets the pivot position to the surface under the cursor."),
    (
        "ACTIVE",
        "Active Vertex",
        "Sets the pivot position to the active vertex position.",
    ),
    (
        "UNMASKED",
        "Unmasked",
        """
        Sets the pivot position to the average position of the unmasked
        vertices.
     """,
    ),
    ("ORIGIN", "Origin", "Sets the pivot to the origin of the sculpt."),
    (
        "BORDER",
        "Mask Border",
        "Sets the pivot position to the center of the border of the mask.",
    ),
]


class SCULPT_DECK_PG_InterfaceSettings(PropertyGroup):
    pivot_mode: EnumProperty(
        name="Sculpt Pivot Mode",
        items=pivot_items,
        default="SURFACE",
    )

    def to_dict(self):
        return {"pivot_mode": self.pivot_mode}

    def from_dict(self, data: dict):
        self.pivot_mode = data.get("pivot_mode", "SURFACE")


def register():
    bpy.utils.register_class(SCULPT_DECK_PG_InterfaceSettings)
    add_section("interface", SCULPT_DECK_PG_InterfaceSettings)


def unregister():
    remove_section("interface")
    bpy.utils.unregister_class(SCULPT_DECK_PG_InterfaceSettings)
