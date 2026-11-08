"""Smoke check, run inside Blender by dev/tests/smoke.sh: enables, disables and re-enables Sculpt Deck, and prints
what got registered (operators, classes, the sidebar panel order and every Action List) in a stable form. Then
checks the Action List rules, that an Action added to the catalog appears where it fits, and that settings survive a
save and load. Not part of the add-on."""

import json
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


def subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from subclasses(sub)


def sidebar_panels() -> list[str]:
    """The Sculpt Deck sidebar's sub-panels in the order users see them. Blender sorts sub-panels by bl_order,
    then by registration; every one sets its own bl_order, so no two may share one"""
    panels = {
        cls.__name__: cls
        for cls in subclasses(bpy.types.Panel)
        if cls.is_registered and getattr(cls, "bl_parent_id", "") == "SCULPT_DECK_PT_view_3d_panel"
    }
    orders = [getattr(cls, "bl_order", 0) for cls in panels.values()]
    assert len(set(orders)) == len(orders), f"sidebar sub-panels share a bl_order: {sorted(orders)}"
    ordered = sorted(panels.values(), key=lambda cls: getattr(cls, "bl_order", 0))
    return [f"{getattr(cls, 'bl_order', 0)} {cls.__name__} ({cls.bl_label})" for cls in ordered]


def report(lines: list[str]):
    prefs = bpy.context.preferences.addons[MODULE].preferences
    lines.append("# operators")
    lines += [f"sculpt_deck.{name}" for name in sorted(dir(bpy.ops.sculpt_deck))]
    lines.append("# classes")
    lines += sorted(name for name in dir(bpy.types) if name.startswith("SCULPT_DECK_"))
    lines.append("# sidebar panels")
    lines += sidebar_panels()
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


PEN_GESTURES = ("upper_click", "upper_hold", "lower_click", "lower_hold", "right_click", "double_click")


def gesture_lists(prefs, mode: str) -> dict[str, list[str]]:
    """Every Action List of one mode, by Gesture, read from the enum properties themselves"""
    lists = {
        "pie": enum_choices(prefs.getMenuSettings(mode), "menu_choice_1"),
        "widget": enum_choices(prefs.getWidgetSettings(mode), "menu_choice_1"),
    }
    pen_set = prefs.getPenSet(mode)
    for gesture in PEN_GESTURES:
        lists[gesture] = enum_choices(getattr(pen_set, gesture), "action")
    return lists


def check_catalog_rules(prefs):
    """The rules hold in every list, and an Action added to the catalog with its traits shows up on every Gesture
    where it fits, with no other edit"""
    catalog = sys.modules[MODULE + ".source.core.actions"]
    modes = sorted(pen_set.mode for pen_set in prefs.pen_sets)
    for mode in modes:
        for gesture, choices in gesture_lists(prefs, mode).items():
            for idname in choices:
                found = catalog.find(idname)
                if found is None:
                    continue
                assert not (gesture.endswith("_hold") and not found.momentary), f"{idname} on {mode} {gesture}"
                assert not (gesture not in ("pie", "widget") and found.resolution_change), (
                    f"Resolution Change {idname} on {mode} {gesture}"
                )

    added = [
        catalog.action("smoke.plain", "Plain", "DOT", "SCULPT"),
        catalog.action("smoke.momentary", "Momentary", "DOT", "SCULPT", "OBJECT", momentary=True),
        catalog.action("smoke.resolution", "Resolution", "DOT", "SCULPT", resolution_change=True),
        catalog.action("smoke.every_mode", "Every Mode", "DOT", catalog.ANY_MODE),
    ]
    expected = {
        "smoke.plain": {("SCULPT", g) for g in ("pie", "widget", "upper_click", "lower_click", "right_click",
                                                 "double_click")},
        "smoke.momentary": {(m, g) for m in ("SCULPT", "OBJECT") for g in ("pie", "widget", *PEN_GESTURES)},
        "smoke.resolution": {("SCULPT", "pie"), ("SCULPT", "widget")},
        "smoke.every_mode": {(m, g) for m in modes for g in ("pie", "widget", "upper_click", "lower_click",
                                                            "right_click", "double_click")},
    }
    saved = list(catalog.CATALOG)
    try:
        # before the Actions for every mode, like the other Actions of a mode
        first_common = next(i for i, entry in enumerate(saved) if entry.every_mode and entry.pie_slot)
        catalog.CATALOG[first_common:first_common] = added[:3]
        catalog.CATALOG.append(added[3])
        catalog.clear_cache()
        found = {idname: set() for idname in expected}
        for mode in modes:
            for gesture, choices in gesture_lists(prefs, mode).items():
                for idname in expected:
                    if idname in choices:
                        found[idname].add((mode, gesture))
        for idname, where in expected.items():
            assert found[idname] == where, (
                f"{idname}: missing on {sorted(where - found[idname])}, extra on {sorted(found[idname] - where)}"
            )
        # the mode's own Actions come before those of every mode
        sculpt_pie = enum_choices(prefs.getMenuSettings("SCULPT"), "menu_choice_1")
        assert sculpt_pie.index("smoke.plain") < sculpt_pie.index("SCULPT_DECK_MT_all_actions") < sculpt_pie.index(
            "smoke.every_mode"
        ), "smoke actions out of order"
    finally:
        catalog.CATALOG[:] = saved
        catalog.clear_cache()
    print("catalog rules checked")


def check_round_trip(prefs):
    """Saving the settings and loading them back gives the same settings, choices stored by identifier"""
    sculpt = prefs.getPenSet("SCULPT")
    sculpt.upper_click.action = "SCULPT_DECK_MT_floating"
    sculpt.lower_hold.action = "TOOL:builtin.box_mask"
    sculpt.double_click.action = "CUSTOM"
    sculpt.double_click.operator = "object.shade_smooth"
    prefs.getWidgetSettings("OBJECT").setSlot(3, "object.join")
    prefs.getMenuSettings("SCULPT").setSlot(8, "my.custom_operator")
    saved = json.loads(json.dumps(prefs.to_dict()))
    pen = next(pen_set for pen_set in saved["pen_sets"] if pen_set["mode"] == "SCULPT")
    assert pen["upper_click"]["action"] == "SCULPT_DECK_MT_floating", pen["upper_click"]
    assert pen["lower_hold"]["action"] == "TOOL:builtin.box_mask", pen["lower_hold"]
    assert pen["double_click"] == {"action": "CUSTOM", "operator": "object.shade_smooth", "brush": []}
    settings = sys.modules[MODULE + ".source.core.settings"]
    # changed after saving, so loading has to bring each one back
    sculpt.upper_click.action = "DEFAULT"
    sculpt.lower_hold.action = "NONE"
    sculpt.double_click.action = "ed.undo"
    prefs.getWidgetSettings("OBJECT").setSlot(3, "")
    prefs.getMenuSettings("SCULPT").setSlot(8, "")
    settings.apply(saved)
    assert json.loads(json.dumps(prefs.to_dict())) == saved, "settings changed on a save and load"
    assert prefs.getMenuSettings("SCULPT").slot(8) == "my.custom_operator"
    assert prefs.getWidgetSettings("OBJECT").slot(3) == "object.join"
    print("settings round trip checked")


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
    prefs = addons[MODULE].preferences
    check_catalog_rules(prefs)
    check_round_trip(prefs)
    print(f"SMOKE OK: {len(lines)} lines written to {output}")


main()
