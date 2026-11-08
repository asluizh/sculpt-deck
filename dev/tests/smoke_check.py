"""Smoke check, run inside Blender by dev/tests/smoke.sh: enables, disables and re-enables Sculpt Deck, and prints
what got registered (operators and every Action List) in a stable form. Not part of the add-on."""

import re
import sys

import bpy

MODULE = "bl_ext.user_default.sculpt_deck"


def enum_choices(owner, prop: str) -> list[str]:
    """Every identifier a (possibly dynamic) enum offers: RNA doesn't list dynamic items, but assigning an
    invalid value raises an error naming all valid ones."""
    try:
        setattr(owner, prop, "@smoke-check@")
    except TypeError as error:
        found = re.search(r"not found in \((.*)\)", str(error))
        if found:
            return re.findall(r"'([^']*)'", found.group(1))
        raise
    raise AssertionError(f"{owner}.{prop} accepted an invalid value")


def report(lines: list[str]):
    prefs = bpy.context.preferences.addons[MODULE].preferences
    lines.append("# operators")
    lines += [f"sculpt_deck.{name}" for name in sorted(dir(bpy.ops.sculpt_deck))]
    lines.append("# classes")
    lines += sorted(name for name in dir(bpy.types) if name.startswith("SCULPT_DECK_"))
    lines.append("# action lists")
    for surface, sets, gestures in (
        ("pie", prefs.menu_sets, ("menu_choice_1",)),
        ("widget", prefs.widget_sets, ("menu_choice_1",)),
    ):
        for group in sorted(sets, key=lambda group: group.mode):
            for gesture in gestures:
                lines.append(f"{surface} {group.mode}: {' '.join(enum_choices(group, gesture))}")
    for pen_set in sorted(prefs.pen_sets, key=lambda pen_set: pen_set.mode):
        for gesture in ("upper_click", "upper_hold", "lower_click", "lower_hold", "right_click", "double_click"):
            lines.append(f"pen {pen_set.mode} {gesture}: {' '.join(enum_choices(getattr(pen_set, gesture), 'action'))}")


def main():
    output = sys.argv[sys.argv.index("--") + 1]
    addons = bpy.context.preferences.addons
    assert MODULE in addons, "Sculpt Deck isn't enabled after install"
    bpy.ops.preferences.addon_disable(module=MODULE)
    assert MODULE not in addons, "Sculpt Deck didn't disable"
    assert not dir(bpy.ops.sculpt_deck), "operators left registered after disabling"
    bpy.ops.preferences.addon_enable(module=MODULE)
    assert MODULE in addons, "Sculpt Deck didn't enable again"
    lines: list[str] = []
    report(lines)
    with open(output, "w") as file:
        file.write("\n".join(lines) + "\n")
    print(f"SMOKE OK: {len(lines)} lines written to {output}")


main()
