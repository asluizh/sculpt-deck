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


def adjust_last(undo: bool = True, **props):
    """Adjust Last Operation: change the last operator's settings and run it again from the step before it.

    With `undo` it runs with an undo step, like `call` and like the Adjust Last Operation panel. Without one, Blender
    treats it as called from a script: the repeated operator stores no undo step (the history stays one step
    behind) and runs before the mode of the step undone to is back, in Object Mode, which is how a Detour that
    took its mode from the current one ended in the wrong mode (#13).
    """
    with override():
        last = bpy.context.active_operator
        check(last is not None, "no last operation to adjust")
        for name, value in props.items():
            setattr(last.properties, name, value)
        bpy.ops.ed.undo_redo("EXEC_DEFAULT", undo)
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
    yield undo()
    check(meshes() == ["Cube"], f"undo adjusted Add Mesh: expected only the Cube, got {meshes()}")
    check(mode() == "SCULPT", f"undo adjusted Add Mesh: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(len(meshes()) == 2, f"redo adjusted Add Mesh: expected 2 meshes, got {meshes()}")
    check(mode() == "SCULPT", f"redo adjusted Add Mesh: expected Sculpt Mode, got {mode()}")


def detour_repeat_from_object_mode():
    """A Detour repeated while still in Object Mode keeps the mode it first started from (#13).

    The only scenario that repeats before the mode is back: `adjust_last` with an undo step runs the repeat after
    it. The undo history it leaves is one step behind, so it checks only the mode and the meshes."""
    yield from reset()
    call("sculpt_deck.add_primitive", primitive="CUBE")
    yield 1.0
    yield adjust_last(undo=False, primitive="SPHERE")
    yield 0.5
    yield adjust_last(undo=False, primitive="CYLINDER")
    yield 0.5
    check(len(meshes()) == 2, f"repeated Add Mesh: expected 2 meshes, got {meshes()}")
    check(mode() == "SCULPT", f"repeated Add Mesh: expected Sculpt Mode, got {mode()}")


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


def original_mesh() -> bool:
    """Whether the only mesh left is the startup Cube (8 vertices), not the remeshed cube Delete adds"""
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    return len(objects) == 1 and len(objects[0].data.vertices) == 8


def detour_delete_last_mesh():
    yield from reset()
    call("sculpt_deck.delete_object")
    yield 1.0
    check(len(meshes()) == 1 and not original_mesh(), f"Delete last: expected a new cube instead, got {meshes()}")
    check(mode() == "SCULPT", f"Delete last: expected to end in Sculpt Mode, got {mode()}")
    yield undo()
    check(original_mesh(), f"undo Delete last: expected the startup Cube back, got {meshes()}")
    check(mode() == "SCULPT", f"undo Delete last: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(len(meshes()) == 1 and not original_mesh(), f"redo Delete last: expected the new cube, got {meshes()}")
    check(mode() == "SCULPT", f"redo Delete last: expected Sculpt Mode, got {mode()}")


def detour_duplicate():
    yield from reset()
    call("sculpt_deck.duplicate_object")
    yield 1.0
    check(len(meshes()) == 2, f"Duplicate: expected 2 meshes, got {meshes()}")
    check(mode() == "SCULPT", f"Duplicate: expected to end in Sculpt Mode, got {mode()}")
    yield undo()
    check(meshes() == ["Cube"], f"undo Duplicate: expected only the Cube, got {meshes()}")
    check(mode() == "SCULPT", f"undo Duplicate: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(len(meshes()) == 2, f"redo Duplicate: expected 2 meshes, got {meshes()}")
    check(mode() == "SCULPT", f"redo Duplicate: expected Sculpt Mode, got {mode()}")


def detour_fuse():
    yield from reset(extra_cubes=1)
    bpy.context.scene.objects["Cube.001"].select_set(True)
    call("sculpt_deck.fuse_selected")
    yield 1.0
    check(meshes() == ["Cube"], f"Fuse: expected only the Cube, got {meshes()}")
    check(mode() == "SCULPT", f"Fuse: expected to end in Sculpt Mode, got {mode()}")
    yield adjust_last(voxel_size=0.2)
    yield 0.5
    check(meshes() == ["Cube"], f"Adjust Last Operation on Fuse: expected only the Cube, got {meshes()}")
    check(mode() == "SCULPT", f"Adjust Last Operation on Fuse: expected Sculpt Mode, got {mode()}")
    yield undo()
    check(meshes() == ["Cube", "Cube.001"], f"undo Fuse: expected both cubes, got {meshes()}")
    check(mode() == "SCULPT", f"undo Fuse: expected Sculpt Mode, got {mode()}")


def detour_fuse_difference():
    yield from reset(extra_cubes=1)
    cutter = bpy.context.scene.objects["Cube.001"]
    cutter.location.x = 1.0
    cutter.select_set(True)
    call("sculpt_deck.fuse_difference")
    yield 1.0
    check(meshes() == ["Cube"], f"Fuse (Difference): expected only the Cube, got {meshes()}")
    check(mode() == "SCULPT", f"Fuse (Difference): expected to end in Sculpt Mode, got {mode()}")
    yield undo()
    check(meshes() == ["Cube", "Cube.001"], f"undo Fuse (Difference): expected both cubes, got {meshes()}")
    check(mode() == "SCULPT", f"undo Fuse (Difference): expected Sculpt Mode, got {mode()}")
    yield redo()
    check(meshes() == ["Cube"], f"redo Fuse (Difference): expected only the Cube, got {meshes()}")
    check(mode() == "SCULPT", f"redo Fuse (Difference): expected Sculpt Mode, got {mode()}")


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


def cube():
    return bpy.context.scene.objects["Cube"]


def modifier_names() -> list[str]:
    return [modifier.name for modifier in cube().modifiers]


def vertex_count() -> int:
    """Vertices of the Cube's evaluated mesh, so it reads right with Dyntopo on too. Instances (array copies and the
    mirror image before they are applied) aren't counted."""
    with override():
        obj = cube().evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = obj.to_mesh()
        count = len(mesh.vertices)
        obj.to_mesh_clear()
    return count


def start_tool(idname: str, modifier: str):
    """Switch to a tool that adds its modifier when it starts, as the toolbar does, and wait for the modifier"""
    call("wm.tool_set_by_id", name=idname, space_type="VIEW_3D")
    for _ in range(10):
        yield 0.3
        if modifier in modifier_names():
            break
    check(modifier_names() == [modifier], f"{idname}: expected a {modifier} modifier, got {modifier_names()}")
    check(mode() == "SCULPT", f"{idname}: expected Sculpt Mode, got {mode()}")


def count_hops() -> list[str]:
    """Record the target mode of every Hop Array's apply makes from now on, in the returned list"""
    hops: list[str] = []
    module = sys.modules[PACKAGE + ".source.features.array.operators"]
    original = sys.modules[PACKAGE + ".source.core.hop"].hop

    def recording(context, target):
        hops.append(target)
        return original(context, target)

    module.hop = recording
    return hops


def add_and_apply_array(dyntopo: bool):
    """Add a Linear Array from its tool and apply it, staying in Sculpt Mode. With Dyntopo, Blender only applies
    properly in Object Mode, so Apply Array makes a Hop there."""
    yield from reset()
    if dyntopo:
        call("sculpt.dynamic_topology_toggle")
        yield 0.3
        check(cube().use_dynamic_topology_sculpting, "setup: Dyntopo didn't turn on")
    yield from start_tool("sculpt_deck.linear_array", "Linear Array")
    # the copies are instances until applied, so the evaluated mesh is the Cube's alone
    check(vertex_count() == 8, f"Linear Array: expected 8 real vertices, got {vertex_count()}")
    hops = count_hops()
    call("sculpt_deck.array_apply", kind="LINEAR")
    yield 0.5
    check(modifier_names() == [], f"Apply Array: expected no modifiers left, got {modifier_names()}")
    check(vertex_count() == 24, f"Apply Array: expected the copies in the mesh (24 vertices), got {vertex_count()}")
    check(mode() == "SCULPT", f"Apply Array: expected Sculpt Mode, got {mode()}")
    check(cube().use_dynamic_topology_sculpting == dyntopo, "Apply Array: Dyntopo changed")
    expected = ["OBJECT"] if dyntopo else []
    check(hops == expected, f"Apply Array: expected Hops to {expected}, got {hops}")


def check_applied_array_kept():
    """With Dyntopo, Sculpt Mode sculpts its own copy of the mesh and writes it back when it ends: the copies must
    be in that one too"""
    call("object.mode_set", undo=False, mode="OBJECT")
    yield 0.3
    count = len(cube().data.vertices)
    check(count == 24, f"leaving Sculpt Mode after Apply Array: expected the copies kept (24 vertices), got {count}")


def array_apply():
    yield from add_and_apply_array(dyntopo=False)
    yield undo()
    check(modifier_names() == ["Linear Array"], f"undo Apply Array: expected the array back, got {modifier_names()}")
    check(vertex_count() == 8, f"undo Apply Array: expected the copies as instances again (8 vertices), got "
          f"{vertex_count()}")
    check(mode() == "SCULPT", f"undo Apply Array: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(modifier_names() == [], f"redo Apply Array: expected no modifiers left, got {modifier_names()}")
    check(vertex_count() == 24, f"redo Apply Array: expected 24 vertices, got {vertex_count()}")
    check(mode() == "SCULPT", f"redo Apply Array: expected Sculpt Mode, got {mode()}")
    yield from check_applied_array_kept()


def hop_array_apply_dyntopo():
    yield from add_and_apply_array(dyntopo=True)
    yield from check_applied_array_kept()


def hop_array_apply_dyntopo_undo():
    yield from add_and_apply_array(dyntopo=True)
    yield undo()
    check(modifier_names() == ["Linear Array"], f"undo Apply Array: expected the array back, got {modifier_names()}")
    check(mode() == "SCULPT", f"undo Apply Array: expected Sculpt Mode, got {mode()}")
    check(cube().use_dynamic_topology_sculpting, "undo Apply Array: expected Dyntopo still on")
    yield redo()
    check(modifier_names() == [], f"redo Apply Array: expected no modifiers left, got {modifier_names()}")
    check(mode() == "SCULPT", f"redo Apply Array: expected Sculpt Mode, got {mode()}")


def hop_modes():
    """The Hop on its own: to Edit and Object Mode and back, also when the body raises, with no undo step"""
    hop = sys.modules[PACKAGE + ".source.core.hop"].hop
    yield from reset()
    call("sculpt_deck.local_transform", mode="MOVE", axis="X", distance=1.0)
    yield 0.5
    for target, inside in (("EDIT", "EDIT_MESH"), ("OBJECT", "OBJECT")):
        with override():
            with hop(bpy.context, target):
                check(bpy.context.mode == inside, f"Hop to {target}: expected {inside} inside, got {bpy.context.mode}")
        yield 0.2
        check(mode() == "SCULPT", f"Hop to {target}: expected Sculpt Mode back, got {mode()}")
        try:
            with override():
                with hop(bpy.context, target):
                    raise ValueError("body failed")
        except ValueError:
            pass
        yield 0.2
        check(mode() == "SCULPT", f"Hop to {target} that raised: expected Sculpt Mode back, got {mode()}")
    # nothing in the undo history: one undo takes back the move from before the Hops
    yield undo()
    check(location_x() == 0.0, f"undo after the Hops: expected the move undone (x = 0), got {location_x()}")
    check(mode() == "SCULPT", f"undo after the Hops: expected Sculpt Mode, got {mode()}")


def mirror_apply():
    yield from reset()
    # off the mirror plane, so the two halves stay apart: 16 vertices, none merged
    cube().location.x = 2.0
    yield from start_tool("sculpt_deck.mirror", "Mirror")
    call("sculpt_deck.mirror_apply")
    yield 0.5
    check(modifier_names() == [], f"Apply Mirror: expected no modifiers left, got {modifier_names()}")
    check(vertex_count() == 16, f"Apply Mirror: expected both halves in the mesh (16 vertices), got {vertex_count()}")
    check(mode() == "SCULPT", f"Apply Mirror: expected Sculpt Mode, got {mode()}")
    yield undo()
    check(modifier_names() == ["Mirror"], f"undo Apply Mirror: expected the mirror back, got {modifier_names()}")
    check(vertex_count() == 8, f"undo Apply Mirror: expected 8 vertices, got {vertex_count()}")
    check(mode() == "SCULPT", f"undo Apply Mirror: expected Sculpt Mode, got {mode()}")


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


def widget_group():
    """The Widget's gizmo group in the viewport, caught on its next redraw"""
    module = sys.modules[PACKAGE + ".source.surfaces.widget.gizmo_group_2d"]
    group_class = module.GIZMO_GT_viewport_gizmo_group
    found = []
    original = group_class.draw_prepare

    def draw_prepare(self, context):
        found.append(self)
        return original(self, context)

    group_class.draw_prepare = draw_prepare
    try:
        for _ in range(20):
            _window, area, _region = view3d()
            area.tag_redraw()
            yield 0.1
            if found:
                break
    finally:
        group_class.draw_prepare = original
    check(bool(found), "the Widget's gizmo group didn't draw")
    return found[-1]


def click_widget_button(group, idname: str):
    """Tap the Widget button set to `idname`, at the place the Widget drew it"""
    button = next((action for action in group.actions if action.idname == idname), None)
    check(button is not None, f"no Widget button for {idname}: {[action.idname for action in group.actions]}")
    check(button.visible, f"the Widget button for {idname} is hidden")
    window, _area, region = view3d()
    position = button.primary.matrix_basis.translation
    x, y = region.x + round(position.x), region.y + round(position.y)
    window.event_simulate("MOUSEMOVE", "NOTHING", x=x, y=y)
    yield 0.3
    window.event_simulate("LEFTMOUSE", "PRESS", x=x, y=y)
    yield 0.05
    window.event_simulate("LEFTMOUSE", "RELEASE", x=x, y=y)
    yield 0.5


def widget_button_runs_action():
    yield from reset()
    _window, area, _region = view3d()
    space = area.spaces.active
    before = space.show_region_ui
    group = yield from widget_group()
    # a Sculpt Mode default: an operator Action, run by the button itself
    yield from click_widget_button(group, "sculpt_deck.toggle_n_panel")
    check(space.show_region_ui != before, f"Widget N Panel button: sidebar still {'shown' if before else 'hidden'}")
    check(mode() == "SCULPT", f"Widget N Panel button: expected Sculpt Mode, got {mode()}")


def widget_button_opens_action_pie():
    yield from reset()
    menus = sys.modules[PACKAGE + ".source.surfaces.pie.menus"]
    pie_class = menus.SCULPT_DECK_MT_floating
    drawn = []
    original = pie_class.draw

    def draw(self, context):
        drawn.append(context.mode)
        return original(self, context)

    pie_class.draw = draw
    try:
        group = yield from widget_group()
        # a menu Action: the button runs sculpt_deck.widget_menu, which opens the pie after the release
        yield from click_widget_button(group, "SCULPT_DECK_MT_floating")
        yield 0.5
    finally:
        pie_class.draw = original
    check(bool(drawn), "Widget Action Pie button: the pie didn't open")
    check(set(drawn) == {"SCULPT"}, f"Widget Action Pie button: the pie drew in modes {sorted(set(drawn))}")
    window, area, _region = view3d()
    window.event_simulate("ESC", "PRESS", x=area.x + 5, y=area.y + 5)
    window.event_simulate("ESC", "RELEASE", x=area.x + 5, y=area.y + 5)
    yield 0.3


SCENARIOS = [
    detour_add_mesh,
    detour_add_mesh_adjust_last,
    detour_repeat_from_object_mode,
    detour_join,
    detour_delete,
    detour_delete_last_mesh,
    detour_duplicate,
    detour_fuse,
    detour_fuse_difference,
    local_transform_undo,
    local_transform_adjust_last,
    hop_modes,
    array_apply,
    hop_array_apply_dyntopo,
    hop_array_apply_dyntopo_undo,
    mirror_apply,
    pen_hold_momentary_brush,
    widget_button_runs_action,
    widget_button_opens_action_pie,
]

# Scenarios that fail on purpose because of a known bug, with the reason. They report XFAIL and don't fail the
# run; once the bug is fixed they report XPASS, which does, so the entry gets removed.
KNOWN_FAILURES = {
    "hop_array_apply_dyntopo_undo": "#17: leaving and entering Sculpt Mode with Dyntopo on pushes Blender's own "
    "Dynamic topology disable and enable steps, so the Hop shows in the undo history: one undo leaves the array "
    "applied, the next brings it back with Dyntopo off",
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
