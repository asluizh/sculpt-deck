"""Smoke check, run inside Blender by dev/tests/smoke.sh: enables, disables and re-enables Sculpt Deck, and prints
what got registered (operators, classes, the sidebar panel order, the saved settings keys and every Action List) in
a stable form. Then checks that every Action of the catalog is registered, the Action List rules, that an Action
added to the catalog appears where it fits, and that settings survive a save and load. Run on a build without
navigation, it checks that the add-on is the same minus what navigation registers. Not part of the add-on."""

import difflib
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
    # the keys settings are saved under in preferences.json and .blend files, so a moved setting keeps its key
    lines.append("# settings keys")
    lines += sorted(prefs.to_dict())
    lines.append("# action lists")
    for surface, sets, gestures in (
        ("pie", prefs.pie.menu_sets, ("menu_choice_1",)),
        ("widget", prefs.widget.widget_sets, ("menu_choice_1",)),
    ):
        for group in sorted(sets, key=lambda group: group.mode):
            for gesture in gestures:
                lines.append(f"{surface} {group.mode}: {' '.join(enum_choices(group, gesture))}")
    for pen_set in sorted(prefs.pen.pen_sets, key=lambda pen_set: pen_set.mode):
        for gesture in ("upper_click", "upper_hold", "lower_click", "lower_hold", "right_click", "double_click"):
            lines.append(f"pen {pen_set.mode} {gesture}: {' '.join(enum_choices(getattr(pen_set, gesture), 'action'))}")


PEN_GESTURES = ("upper_click", "upper_hold", "lower_click", "lower_hold", "right_click", "double_click")


def gesture_lists(prefs, mode: str) -> dict[str, list[str]]:
    """Every Action List of one mode, by Gesture, read from the enum properties themselves"""
    lists = {
        "pie": enum_choices(prefs.pie.getMenuSettings(mode), "menu_choice_1"),
        "widget": enum_choices(prefs.widget.getWidgetSettings(mode), "menu_choice_1"),
    }
    pen_set = prefs.pen.getPenSet(mode)
    for gesture in PEN_GESTURES:
        lists[gesture] = enum_choices(getattr(pen_set, gesture), "action")
    return lists


def check_catalog_rules(prefs):
    """The rules hold in every list, and an Action added to the catalog with its traits shows up on every Gesture
    where it fits, with no other edit"""
    catalog = sys.modules[MODULE + ".source.core.actions"]
    modes = sorted(pen_set.mode for pen_set in prefs.pen.pen_sets)
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
        sculpt_pie = enum_choices(prefs.pie.getMenuSettings("SCULPT"), "menu_choice_1")
        assert sculpt_pie.index("smoke.plain") < sculpt_pie.index("SCULPT_DECK_MT_all_actions") < sculpt_pie.index(
            "smoke.every_mode"
        ), "smoke actions out of order"
    finally:
        catalog.CATALOG[:] = saved
        catalog.clear_cache()
    print("catalog rules checked")


def check_round_trip(prefs):
    """Saving the settings and loading them back gives the same settings, choices stored by identifier"""
    sculpt = prefs.pen.getPenSet("SCULPT")
    sculpt.upper_click.action = "SCULPT_DECK_MT_floating"
    sculpt.lower_hold.action = "TOOL:builtin.box_mask"
    sculpt.double_click.action = "CUSTOM"
    sculpt.double_click.operator = "object.shade_smooth"
    prefs.widget.getWidgetSettings("OBJECT").setSlot(3, "object.join")
    prefs.pie.getMenuSettings("SCULPT").setSlot(8, "my.custom_operator")
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
    prefs.widget.getWidgetSettings("OBJECT").setSlot(3, "")
    prefs.pie.getMenuSettings("SCULPT").setSlot(8, "")
    settings.apply(saved)
    assert json.loads(json.dumps(prefs.to_dict())) == saved, "settings changed on a save and load"
    assert prefs.pie.getMenuSettings("SCULPT").slot(8) == "my.custom_operator"
    assert prefs.widget.getWidgetSettings("OBJECT").slot(3) == "object.join"
    print("settings round trip checked")


def registered_tools(mode: str) -> set[str]:
    """The idnames of the toolbar tools of a mode, Blender's and the add-on's"""
    from bl_ui.space_toolsystem_common import ToolSelectPanelHelper

    found: set[str] = set()

    def walk(items):
        for item in items:
            if item is None:
                continue
            if hasattr(item, "idname"):
                found.add(item.idname)
            elif isinstance(item, (tuple, list)):
                walk(item)
            elif callable(item):
                walk(item(bpy.context) or ())

    walk(ToolSelectPanelHelper._tool_class_from_space_type("VIEW_3D")._tools.get(mode, ()))
    return found


# menus Blender defines in C, which bpy.types doesn't list
C_MENUS = {"SCREEN_MT_user_menu"}


def check_catalog_resolves():
    """Every Action of the catalog is there to run: a registered operator, menu or asset shelf, or a tool of each mode
    it's listed for. An Action whose part is gone would show as "Unknown" in the slots holding it"""
    catalog = sys.modules[MODULE + ".source.core.actions"]
    invoke = sys.modules[MODULE + ".source.core.invoke"]
    missing = []
    for entry in catalog.CATALOG:
        idname = entry.idname
        if idname.startswith(catalog.TOOL_PREFIX):
            tool = idname[len(catalog.TOOL_PREFIX):]
            modes = [mode for mode in entry.modes if tool not in registered_tools(mode)]
            if modes:
                missing.append(f"{idname} (no tool in {', '.join(modes)})")
        elif "_MT_" in idname or "_AST_" in idname:
            if not hasattr(bpy.types, idname) and idname not in C_MENUS:
                missing.append(idname)
        elif not invoke.operator_exists(idname):
            missing.append(idname)
    assert not missing, f"catalog Actions not registered: {missing}"
    print("catalog idnames checked")


def check_default_slots(prefs):
    """A new setup's Widget buttons and Action Pie slots hold Actions of the catalog, or nothing"""
    catalog = sys.modules[MODULE + ".source.core.actions"]
    unknown = []
    for surface, sets in (("pie", prefs.pie.menu_sets), ("widget", prefs.widget.widget_sets)):
        for group in sets:
            for idname in group.slots(12):
                if idname and catalog.find(idname) is None:
                    unknown.append(f"{surface} {group.mode}: {idname}")
    assert not unknown, f"default slots holding Actions that aren't in the catalog: {unknown}"
    print("default slots checked")


NAVIGATION = MODULE + ".source.navigation"


def navigation_parts(prefs) -> tuple[set[str], set[str]]:
    """What navigation registers: its operators, classes and settings keys, and its Actions"""
    names: set[str] = set(prefs.navigation.to_dict())
    for base in (bpy.types.Operator, bpy.types.Panel, bpy.types.Menu, bpy.types.GizmoGroup, bpy.types.PropertyGroup):
        for cls in subclasses(base):
            if cls.__module__.startswith(NAVIGATION + ".") and getattr(cls, "is_registered", False):
                # an operator's type is named after its idname, not its class
                names.add(cls.bl_rna.identifier)
                if base is bpy.types.Operator:
                    names.add(cls.bl_idname)
    actions = {entry.idname for _, entry in sys.modules[NAVIGATION + ".view"].ACTIONS}
    return names, actions


def without(expected: list[str], names: set[str], actions: set[str]) -> list[str]:
    """The expected report with what navigation registers taken out: its lines, and its Actions from every list"""
    kept = []
    in_lists = False
    for line in expected:
        in_lists = in_lists or line == "# action lists"
        if in_lists and ": " in line:
            head, choices = line.split(": ", 1)
            kept.append(f"{head}: {' '.join(choice for choice in choices.split() if choice not in actions)}")
        # a whole line (an operator, class or settings key), or a sidebar panel line ("10 CLASS (Label)")
        elif line not in names and not (line[:1].isdigit() and line.split()[1] in names):
            kept.append(line)
    return kept


def check_without_navigation(prefs, lines: list[str], expected_file: str, parts_file: str):
    """Built without navigation, the add-on registers what the full one does, minus what navigation registers: no
    operator, class, settings key or Action of navigation's is left, and nothing else is missing"""
    assert NAVIGATION not in sys.modules, "navigation got imported without its package"
    assert not hasattr(prefs, "navigation"), "the preferences hold navigation settings without navigation"
    with open(parts_file) as file:
        parts = json.load(file)
    with open(expected_file) as file:
        expected = without(file.read().splitlines(), set(parts["names"]), set(parts["actions"]))
    if lines != expected:
        diff = difflib.unified_diff(expected, lines, "expected without navigation", "registered", lineterm="")
        print("\n".join(diff))
        raise AssertionError("without navigation, the add-on differs from the full one by more than navigation")
    print("without navigation checked")


def main():
    """smoke_check.py -- OUTPUT PARTS: the check; what navigation registers is written to PARTS.
    smoke_check.py -- OUTPUT --without-navigation EXPECTED PARTS: the check of a build without navigation, whose
    report has to be EXPECTED minus the navigation PARTS a full check wrote."""
    args = sys.argv[sys.argv.index("--") + 1:]
    output = args[0]
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
    if "--without-navigation" in args:
        check_without_navigation(prefs, lines, args[2], args[3])
    else:
        names, actions = navigation_parts(prefs)
        with open(args[1], "w") as file:
            json.dump({"names": sorted(names), "actions": sorted(actions)}, file, indent=1)
    check_catalog_resolves()
    check_default_slots(prefs)
    check_catalog_rules(prefs)
    check_round_trip(prefs)
    print(f"SMOKE OK: {len(lines)} lines written to {output}")


main()
