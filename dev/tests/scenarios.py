"""UI scenarios, run inside Blender by dev/tests/scenarios.sh on a headless weston session. Not part of the add-on.

Each scenario is a generator: it drives Blender from a timer, checks results with `check`, and yields the number of
seconds to wait so Blender can process events, timers and redraws in between. A scenario passes when it ends
without an exception. Add a scenario by writing a generator and listing it in SCENARIOS.

Operators are called the way the UI would run them, with an undo step (`call`); undo, redo and Adjust Last
Operation go through Blender's own operators. Pen buttons need tablet events, which `window.event_simulate`
can't make, so `pen_events` makes the add-on treat simulated presses as pen presses.
"""

import sys
import traceback

import bpy

PACKAGE = "bl_ext.user_default.sculpt_deck"


class ScenarioFailed(Exception):
    pass


def check(condition: bool, message: str):
    if not condition:
        raise ScenarioFailed(message)


def view3d():
    window = bpy.context.window_manager.windows[0]
    area = next(area for area in window.screen.areas if area.type == "VIEW_3D")
    region = next(region for region in area.regions if region.type == "WINDOW")
    return window, area, region


def override():
    window, area, region = view3d()
    return bpy.context.temp_override(window=window, area=area, region=region)


def call(idname: str, undo: bool = True, **props):
    """Run an operator in the 3D viewport like the UI does: executed, with its undo step"""
    module, name = idname.split(".")
    with override():
        result = getattr(getattr(bpy.ops, module), name)("EXEC_DEFAULT", undo, **props)
    check(result == {"FINISHED"}, f"{idname} returned {result}")


def mode() -> str:
    with override():
        return bpy.context.mode


def meshes() -> list[str]:
    return sorted(obj.name for obj in bpy.context.scene.objects if obj.type == "MESH")


def print_undo_steps():
    """Print the undo history to the log, for debugging a failure"""
    with override():
        bpy.context.window_manager.print_undo_steps()


def undo():
    with override():
        bpy.ops.ed.undo()
    return 0.5


def redo():
    with override():
        bpy.ops.ed.redo()
    return 0.5


def adjust_last(**props):
    """Adjust Last Operation: change the last operator's settings and run it again from the step before it"""
    with override():
        last = bpy.context.active_operator
        check(last is not None, "no last operation to adjust")
        for name, value in props.items():
            setattr(last.properties, name, value)
        bpy.ops.ed.undo_redo()
    return 0.5


def reset(extra_cubes: int = 0):
    """Fresh startup file (only the default Cube) plus extra cubes, the Cube active and selected, in Sculpt Mode"""
    with override():
        bpy.ops.wm.read_homefile("EXEC_DEFAULT")
    yield 0.5
    with override():
        for index in range(extra_cubes):
            bpy.ops.mesh.primitive_cube_add(location=(3.0 * (index + 1), 0.0, 0.0))
        bpy.ops.object.select_all(action="DESELECT")
    cube = bpy.context.scene.objects["Cube"]
    cube.select_set(True)
    bpy.context.view_layer.objects.active = cube
    call("object.mode_set", mode="SCULPT")
    yield 0.3
    check(mode() == "SCULPT", f"setup: expected Sculpt Mode, got {mode()}")


def location_x(name: str = "Cube") -> float:
    return round(bpy.context.scene.objects[name].location.x, 4)


# --- scenarios ---------------------------------------------------------------------------------------------------


def detour_add_mesh():
    yield from reset()
    call("sculpt_deck.add_primitive", primitive="CUBE")
    yield 1.0
    check(len(meshes()) == 2, f"Add Mesh: expected 2 meshes, got {meshes()}")
    check(mode() == "SCULPT", f"Add Mesh: expected to end in Sculpt Mode, got {mode()}")
    yield undo()
    check(len(meshes()) == 1, f"undo Add Mesh: expected 1 mesh, got {meshes()}")
    check(mode() == "SCULPT", f"undo Add Mesh: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(len(meshes()) == 2, f"redo Add Mesh: expected 2 meshes, got {meshes()}")
    check(mode() == "SCULPT", f"redo Add Mesh: expected Sculpt Mode, got {mode()}")


def detour_add_mesh_adjust_last():
    yield from reset()
    call("sculpt_deck.add_primitive", primitive="CUBE")
    yield 1.0
    yield adjust_last(primitive="SPHERE")
    yield 0.5
    yield adjust_last(primitive="CYLINDER")
    yield 0.5
    check(len(meshes()) == 2, f"Adjust Last Operation on Add Mesh: expected 2 meshes, got {meshes()}")
    check(mode() == "SCULPT", f"Adjust Last Operation on Add Mesh: expected Sculpt Mode, got {mode()}")


def detour_join():
    yield from reset(extra_cubes=1)
    bpy.context.scene.objects["Cube.001"].select_set(True)
    call("sculpt_deck.join_selected")
    yield 1.0
    check(len(meshes()) == 1, f"Join: expected 1 mesh, got {meshes()}")
    check(mode() == "SCULPT", f"Join: expected to end in Sculpt Mode, got {mode()}")
    yield undo()
    check(len(meshes()) == 2, f"undo Join: expected 2 meshes, got {meshes()}")
    check(mode() == "SCULPT", f"undo Join: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(len(meshes()) == 1, f"redo Join: expected 1 mesh, got {meshes()}")
    check(mode() == "SCULPT", f"redo Join: expected Sculpt Mode, got {mode()}")


def detour_delete():
    yield from reset(extra_cubes=1)
    call("sculpt_deck.delete_object")
    yield 1.0
    check(meshes() == ["Cube.001"], f"Delete: expected only Cube.001 left, got {meshes()}")
    check(mode() == "SCULPT", f"Delete: expected to end in Sculpt Mode, got {mode()}")
    yield undo()
    check(len(meshes()) == 2, f"undo Delete: expected 2 meshes, got {meshes()}")
    check(mode() == "SCULPT", f"undo Delete: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(meshes() == ["Cube.001"], f"redo Delete: expected only Cube.001 left, got {meshes()}")


def local_transform_undo():
    yield from reset()
    call("sculpt_deck.local_transform", mode="MOVE", axis="X", distance=1.0)
    yield 0.5
    check(location_x() == 1.0, f"move: expected x = 1, got {location_x()}")
    yield undo()
    check(location_x() == 0.0, f"undo move: expected x = 0, got {location_x()}")
    check(mode() == "SCULPT", f"undo move: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(location_x() == 1.0, f"redo move: expected x = 1, got {location_x()}")


def local_transform_adjust_last():
    yield from reset()
    call("sculpt_deck.local_transform", mode="MOVE", axis="X", distance=1.0)
    yield 0.5
    call("sculpt_deck.local_transform", mode="MOVE", axis="X", distance=1.0)
    yield 0.5
    check(location_x() == 2.0, f"two moves: expected x = 2, got {location_x()}")
    yield adjust_last(distance=0.5)
    check(location_x() == 1.5, f"Adjust Last Operation: expected x = 1.5 (only the last move changed), got {location_x()}")
    check(mode() == "SCULPT", f"Adjust Last Operation: expected Sculpt Mode, got {mode()}")


def pen_events():
    """Make the add-on take simulated button presses for pen presses"""
    for name, module in list(sys.modules.items()):
        if name.startswith(PACKAGE) and hasattr(module, "is_pen"):
            module.is_pen = lambda event: True


def simulate(event_type: str, value: str):
    window, area, _region = view3d()
    window.event_simulate(event_type, value, x=area.x + area.width // 2, y=area.y + area.height // 2)


def brush() -> str:
    return bpy.context.tool_settings.sculpt.brush.name


def pen_hold_momentary_brush():
    yield from reset()
    pen_events()
    before = brush()
    check(before != "Smooth", "setup: the starting brush is already Smooth")
    simulate("MOUSEMOVE", "NOTHING")
    yield 0.2
    # the upper pen button's default hold in Sculpt Mode: the Smooth brush while held
    simulate("RIGHTMOUSE", "PRESS")
    yield 0.8
    check(brush() == "Smooth", f"pen hold: expected the Smooth brush while held, got {brush()}")
    simulate("RIGHTMOUSE", "RELEASE")
    yield 0.5
    check(brush() == before, f"pen release: expected {before} back, got {brush()}")


SCENARIOS = [
    detour_add_mesh,
    detour_add_mesh_adjust_last,
    detour_join,
    detour_delete,
    local_transform_undo,
    local_transform_adjust_last,
    pen_hold_momentary_brush,
]

# Scenarios that fail on purpose because of a known bug, with the reason. They report XFAIL and don't fail the
# run; once the bug is fixed they report XPASS, which does, so the entry gets removed.
KNOWN_FAILURES = {
    "detour_add_mesh_adjust_last": "Add Mesh ends in Object Mode after Adjust Last Operation: the repeat runs before "
    "Sculpt Mode is restored, and Add Mesh takes the mode it finishes in from the current one",
}


# --- runner ------------------------------------------------------------------------------------------------------


def runner(output: str, only: set[str]):
    results = []
    for scenario in SCENARIOS:
        name = scenario.__name__
        if only and name not in only:
            continue
        print(f"SCENARIO {name}", flush=True)
        known = KNOWN_FAILURES.get(name)
        try:
            for wait in scenario():
                yield wait
            results.append(f"XPASS {name}: passes now, remove it from KNOWN_FAILURES" if known else f"PASS {name}")
        except Exception as error:
            if not isinstance(error, ScenarioFailed):
                traceback.print_exc()
            results.append(f"XFAIL {name}: {error} (known: {known})" if known else f"FAIL {name}: {error}")
            print_undo_steps()
        print(results[-1], flush=True)
    with open(output, "w") as file:
        file.write("\n".join(results) + "\n")
    with override():
        bpy.ops.wm.quit_blender()


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    steps = runner(args[0], set(args[1:]))

    def step():
        try:
            return next(steps)
        except StopIteration:
            return None

    bpy.app.timers.register(step, first_interval=2.0, persistent=True)


main()
