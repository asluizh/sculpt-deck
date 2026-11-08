"""The add-on preferences, and the settings each part adds to them.

A part keeps its settings in a PropertyGroup of its own and adds it with `add_section` when it registers (after
registering the group), and takes it out again with `remove_section`. The root preferences.py registers after every
part and points one PointerProperty at each section's group, named after the section (`preferences().navigation`),
so a part that isn't there has no settings and nothing else to remove.

A section's group gives its settings as a flat dict with `to_dict()` and takes them back with `from_dict(data)`, with
keys unique across sections: preferences.json and the settings kept in .blend files store every section's keys side
by side, so a setting keeps its key wherever it lives. It may also have `ensure()`, run after loading, to fill in
what the data didn't hold. `draw(layout, settings)` draws the section in the Preferences window, in a tab of its
own (`tab`, one of TABS) or above the tabs; sections are drawn in `order`.
"""

from dataclasses import dataclass
from typing import Callable

import bpy

from ... import __package__ as package  # the add-on's root package

# the tabs of the Preferences window: identifier, label
TABS = (
    ("GIZMO", "Gizmo"),
    ("ACTIONS", "Action"),
    ("PEN", "Pen & Clicks"),
)


def preferences():
    """The add-on preferences"""
    return bpy.context.preferences.addons[package].preferences  # type: ignore


@dataclass(frozen=True)
class Section:
    # the attribute of the preferences holding the settings
    name: str
    settings: type
    draw: Callable | None = None
    # one of TABS, or "" to draw above the tabs
    tab: str = ""
    order: int = 0


_sections: dict[str, Section] = {}


def add_section(name: str, settings: type, draw: Callable | None = None, tab: str = "", order: int = 0):
    """Add a part's settings (a registered PropertyGroup) to the preferences, which register after every part"""
    assert name not in _sections, f"two parts add the settings section {name}"
    assert not tab or tab in dict(TABS), f"no Preferences tab {tab}"
    _sections[name] = Section(name, settings, draw, tab, order)


def remove_section(name: str):
    _sections.pop(name, None)


def sections(tab: str | None = None) -> list[Section]:
    """Every section in drawing order, or only those of one tab ("" for those above the tabs)"""
    found = sorted(_sections.values(), key=lambda section: section.order)
    return found if tab is None else [section for section in found if section.tab == tab]
