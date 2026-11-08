# type: ignore
"""The add-on preferences: they assemble the settings of every registered part (see core/preferences.py) and draw
their sections. Saving and loading the defaults file, and the settings kept in .blend files, are in core/settings.py.
"""

import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty
from bpy.types import AddonPreferences

from .source.core import settings
from .source.core.preferences import TABS, sections
from .source.core.ui import draw_default_settings


class SCULPT_DECK_AP_OverlaySettings(AddonPreferences):
    bl_idname = __package__

    # one PointerProperty per section, named after it, is added on register

    auto_save_defaults: BoolProperty(
        name="Auto-Save Defaults",
        description=(
            "Save every change as the default settings for new and other files. "
            "Off: changes stay in the current file until saved as defaults from the sidebar"
        ),
        default=False,
        update=lambda self, _: settings.auto_save_changed(),
    )

    gizmo_tabs: EnumProperty(
        name="Gizmo Tabs",
        items=[(identifier, label, "", number) for number, (identifier, label) in enumerate(TABS)],
        default="GIZMO",
    )

    def to_dict(self):
        data = {
            "auto_save_defaults": self.auto_save_defaults,
            "gizmo_tabs": self.gizmo_tabs,
        }
        for section in sections():
            data.update(getattr(self, section.name).to_dict())
        return data

    def from_dict(self, data: dict):
        self.auto_save_defaults = data.get("auto_save_defaults", False)
        self.gizmo_tabs = data.get("gizmo_tabs", "GIZMO")
        for section in sections():
            getattr(self, section.name).from_dict(data)
        self.ensure()

    def ensure(self):
        """What the loaded data didn't hold, e.g. the Action slots of a mode, gets its defaults"""
        for section in sections():
            ensure = getattr(getattr(self, section.name), "ensure", None)
            if ensure is not None:
                ensure()

    def load(self):
        settings.load_defaults()

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False

        box = layout.box()
        box.prop(self, "auto_save_defaults")
        draw_default_settings(box)

        for section in sections(tab=""):
            if section.draw is not None:
                section.draw(layout, getattr(self, section.name))

        main_box = layout.box()
        row = main_box.row(align=True)
        row.prop(self, "gizmo_tabs", expand=True)
        main_box.use_property_split = True
        for section in sections(tab=self.gizmo_tabs):
            if section.draw is not None:
                section.draw(main_box, getattr(self, section.name))


# the sections added on register, taken out again on unregister
_pointers: list[str] = []


def register():
    # the parts registered first, with their settings
    annotations = SCULPT_DECK_AP_OverlaySettings.__annotations__
    for section in sections():
        annotations[section.name] = PointerProperty(type=section.settings)
        _pointers.append(section.name)
    bpy.utils.register_class(SCULPT_DECK_AP_OverlaySettings)


def unregister():
    bpy.utils.unregister_class(SCULPT_DECK_AP_OverlaySettings)
    annotations = SCULPT_DECK_AP_OverlaySettings.__annotations__
    for name in _pointers:
        annotations.pop(name, None)
    _pointers.clear()
