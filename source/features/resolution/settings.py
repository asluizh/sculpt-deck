# type: ignore
"""The Resolution Changes' settings: the Subdivision Limit Multires Level Up stops at, and the Topology Mode. Held by
the add-on preferences as `preferences().resolution`."""

import bpy
from bpy.props import EnumProperty, IntProperty
from bpy.types import PropertyGroup, UILayout

from ...core.preferences import add_section, preferences, remove_section


class SCULPT_DECK_PG_ResolutionSettings(PropertyGroup):
    subdivision_limit: IntProperty(
        name="Subdivision Limit",
        default=4,
        min=1,
        max=7,
    )

    # not read by any Action yet
    topology_mode: EnumProperty(
        name="Topology Mode",
        items=[
            ("MANUAL", "manual", "user-defined vertex density"),
            ("RELATIVE", "relative", "relative mesh vertex density steps"),
            (
                "RELATIVE-EXP",
                "exponential",
                "relative mesh vertex density steps with scaling",
            ),
        ],
        default="MANUAL",
    )

    def to_dict(self):
        return {
            "subdivision_limit": self.subdivision_limit,
            "topology_mode": self.topology_mode,
        }

    def from_dict(self, data: dict):
        self.subdivision_limit = data.get("subdivision_limit", 4)
        self.topology_mode = data.get("topology_mode", "MANUAL")


def resolution_settings() -> SCULPT_DECK_PG_ResolutionSettings:
    return preferences().resolution


def draw_preferences(layout: UILayout, settings):
    col = layout.column()
    col.label(text="Tool Settings")
    col.prop(settings, "subdivision_limit", slider=True)


def register():
    bpy.utils.register_class(SCULPT_DECK_PG_ResolutionSettings)
    # in the Gizmo tab, after the Widget's settings
    add_section("resolution", SCULPT_DECK_PG_ResolutionSettings, draw_preferences, tab="GIZMO", order=45)


def unregister():
    remove_section("resolution")
    bpy.utils.unregister_class(SCULPT_DECK_PG_ResolutionSettings)
