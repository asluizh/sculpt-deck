"""UI scenarios, run inside Blender by dev/tests/scenarios.sh on a headless weston session. Not part of the add-on.

Each scenario is a generator: it drives Blender from a timer, checks results with `check`, and yields the number of
seconds to wait so Blender can process events, timers and redraws in between. A scenario passes when it ends
without an exception. Add a scenario by writing a generator and listing it in SCENARIOS.

Operators are called the way the UI would run them, with an undo step (`call`); undo, redo and Adjust Last
Operation go through Blender's own operators. Pen buttons need tablet events, which `window.event_simulate`
can't make, so `pen_events` makes the add-on treat simulated presses as pen presses.
"""

import os
import sys
import tempfile
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


def local_transform_two_objects():
    """Local Transform moves every selected object, and undo moves them all back"""
    yield from reset(extra_cubes=1)
    bpy.context.scene.objects["Cube.001"].select_set(True)
    call("sculpt_deck.local_transform", mode="MOVE", axis="X", distance=1.0)
    yield 0.5
    both = (location_x(), location_x("Cube.001"))
    check(both == (1.0, 4.0), f"move two objects: expected x = 1 and 4, got {both}")
    yield undo()
    both = (location_x(), location_x("Cube.001"))
    check(both == (0.0, 3.0), f"undo move of two objects: expected x = 0 and 3, got {both}")
    check(mode() == "SCULPT", f"undo move of two objects: expected Sculpt Mode, got {mode()}")
    yield redo()
    both = (location_x(), location_x("Cube.001"))
    check(both == (1.0, 4.0), f"redo move of two objects: expected x = 1 and 4, got {both}")


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


def count_hops(feature: str = "array") -> list[str]:
    """Record the target mode of every Hop the feature's operators make from now on, in the returned list"""
    hops: list[str] = []
    module = sys.modules[PACKAGE + f".source.features.{feature}.operators"]
    original = sys.modules[PACKAGE + ".source.core.hop"].hop

    def recording(context, target, *args, **kwargs):
        hops.append(target)
        return original(context, target, *args, **kwargs)

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


# the custom property a Hop under Dyntopo marks its undo steps with (core/hop.py), never left on the object
HOP_STEP = "sculpt_deck_hop_step"


def settle_hop():
    """Wait for the extra undos or redos stepping over a Hop's steps under Dyntopo, each run from a timer"""
    hop = sys.modules[PACKAGE + ".source.core.hop"]
    for _ in range(20):
        yield 0.25
        if hop.scheduled == 0 and HOP_STEP not in cube():
            break
    yield 0.25


def hop_undo():
    yield undo()
    yield from settle_hop()


def hop_redo():
    yield redo()
    yield from settle_hop()


def check_dyntopo_state(when: str, modifiers: list[str], width: float, dyntopo: bool | None = None):
    """The Cube's modifiers and width (its mesh's, with Dyntopo too), in Sculpt Mode with Dyntopo as given, and no
    Hop mark left. Dyntopo isn't checked when None: Blender 5.2 turns it off whenever undo or redo lands on a whole
    scene step in Sculpt Mode, so it's off after redoing an apply too, as after redoing any whole scene step."""
    state = (modifier_names(), round(cube().dimensions.x, 4), mode())
    check(state == (modifiers, width, "SCULPT"), f"{when}: expected (modifiers, width, mode) = "
          f"{(modifiers, width, 'SCULPT')}, got {state}")
    if dyntopo is not None:
        expected = "on" if dyntopo else "off"
        check(cube().use_dynamic_topology_sculpting == dyntopo, f"{when}: expected Dyntopo {expected}")
    check(HOP_STEP not in cube(), f"{when}: the Hop's undo mark was left on the Cube")


def hop_array_apply_dyntopo_undo():
    yield from add_and_apply_array(dyntopo=True)
    check_dyntopo_state("Apply Array", [], 6.4, dyntopo=True)
    yield from hop_undo()
    check_dyntopo_state("undo Apply Array", ["Linear Array"], 2.0, dyntopo=True)
    yield from hop_redo()
    check_dyntopo_state("redo Apply Array", [], 6.4)
    yield from check_applied_array_kept()


def hop_array_apply_dyntopo_twice():
    """Two arrays added and applied in a row: each undo and redo goes one action back or forward"""
    yield from add_and_apply_array(dyntopo=True)
    yield from start_tool("sculpt_deck.linear_array", "Linear Array")
    call("sculpt_deck.array_apply", kind="LINEAR")
    yield 0.5
    check_dyntopo_state("second Apply Array", [], 20.48, dyntopo=True)
    steps = [
        # the second apply, the second Add Linear Array, the first apply
        (["Linear Array"], 6.4, True),
        ([], 6.4, None),
        (["Linear Array"], 2.0, True),
    ]
    for index, (modifiers, width, dyntopo) in enumerate(steps):
        yield from hop_undo()
        check_dyntopo_state(f"undo {index + 1}", modifiers, width, dyntopo)
    for index, (modifiers, width) in enumerate([([], 6.4), (["Linear Array"], 6.4), ([], 20.48)]):
        yield from hop_redo()
        check_dyntopo_state(f"redo {index + 1}", modifiers, width)


def hop_array_apply_dyntopo_history():
    """Jumping in the Undo History list onto one of the Hop's steps steps over them too"""
    yield from add_and_apply_array(dyntopo=True)
    # the indexes follow the Hop's steps (the runner prints the history on failure): 3 Add Linear Array, 4-6 the
    # Dyntopo toggle before the Hop, 7-8 leaving Sculpt Mode, 9-10 back in it, 11 Apply Array
    for item, modifiers, width, dyntopo in ((8, ["Linear Array"], 2.0, True), (10, [], 6.4, None),
                                            (9, ["Linear Array"], 2.0, True)):
        with override():
            bpy.ops.ed.undo_history(item=item)
        yield from settle_hop()
        check_dyntopo_state(f"jump to undo step {item}", modifiers, width, dyntopo)


def hop_array_apply_dyntopo_adjust_last():
    """Adjust Last Operation undoes onto the Hop's last step and runs Apply Array again, which finds nothing left to
    apply: it stays applied, and isn't undone afterwards"""
    yield from add_and_apply_array(dyntopo=True)
    yield adjust_last()
    yield from settle_hop()
    check_dyntopo_state("Adjust Last Operation on Apply Array", [], 6.4)
    yield from hop_undo()
    check_dyntopo_state("undo after Adjust Last Operation", ["Linear Array"], 2.0, dyntopo=True)


def hop_mark_cleared_on_load():
    """A file saved while on one of the Hop's steps would keep its mark: opening it drops the mark"""
    yield from reset()
    cube()[HOP_STEP] = "INSIDE"
    path = os.path.join(tempfile.gettempdir(), "sculpt_deck_hop_mark.blend")
    with override():
        bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
        bpy.ops.wm.open_mainfile(filepath=path)
    yield 0.5
    check(HOP_STEP not in cube(), "opening a file: the Hop's undo mark was kept")
    os.remove(path)


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


def stretched_cube(dyntopo: bool = False, multires: bool = False):
    """The Cube stretched to twice its width in Object Mode, then in Sculpt Mode with Dyntopo or a subdivided
    Multires modifier. Stretched in Object Mode with an undo step, as a user would, since Sculpt undo steps don't
    hold object transforms."""
    with override():
        bpy.ops.wm.read_homefile("EXEC_DEFAULT")
    yield 0.5
    call("transform.resize", value=(2.0, 1.0, 1.0))
    if multires:
        call("object.modifier_add", type="MULTIRES")
        call("object.multires_subdivide", modifier="Multires", mode="CATMULL_CLARK")
        check(modifier_names() == ["Multires"], f"setup: expected a Multires modifier, got {modifier_names()}")
    call("object.mode_set", mode="SCULPT")
    yield 0.3
    check(mode() == "SCULPT", f"setup: expected Sculpt Mode, got {mode()}")
    if dyntopo:
        call("sculpt.dynamic_topology_toggle")
        yield 0.3
        check(cube().use_dynamic_topology_sculpting, "setup: Dyntopo didn't turn on")
    check(round(cube().scale.x, 4) == 2.0, f"setup: expected scale x = 2, got {cube().scale.x}")


def mesh_width() -> float:
    """Width of the Cube's own mesh along its X axis, without the object's scale"""
    xs = [vertex.co.x for vertex in cube().data.vertices]
    return round(max(xs) - min(xs), 4)


def apply_scale(feature_hops: list[str], expected_hops: list[str]):
    call("sculpt_deck.apply_object_scale")
    yield 0.5
    check(tuple(cube().scale) == (1.0, 1.0, 1.0), f"Apply Scale: expected scale 1, got {tuple(cube().scale)}")
    check(round(cube().dimensions.x, 4) == 4.0, f"Apply Scale: expected width 4, got {cube().dimensions.x}")
    check(mode() == "SCULPT", f"Apply Scale: expected Sculpt Mode, got {mode()}")
    check(feature_hops == expected_hops, f"Apply Scale: expected Hops to {expected_hops}, got {feature_hops}")


def apply_scale_undo():
    """Apply Scale on a plain mesh needs no Hop. Its undo goes back past a Sculpt step, which doesn't hold the
    scale, so it relies on the "Before Apply Scale" Scene Checkpoint"""
    yield from stretched_cube()
    hops = count_hops("local_transform")
    yield from apply_scale(hops, [])
    check(mesh_width() == 4.0, f"Apply Scale: expected the mesh 4 wide, got {mesh_width()}")
    yield undo()
    check(round(cube().scale.x, 4) == 2.0, f"undo Apply Scale: expected scale x = 2, got {cube().scale.x}")
    check(mesh_width() == 2.0, f"undo Apply Scale: expected the mesh 2 wide again, got {mesh_width()}")
    check(mode() == "SCULPT", f"undo Apply Scale: expected Sculpt Mode, got {mode()}")


def hop_apply_scale_multires():
    """Apply Scale with Multires uses Blender's own apply, which only runs in Object Mode, so it makes a Hop there
    and stays in Sculpt Mode, keeping the Multires modifier"""
    yield from stretched_cube(multires=True)
    hops = count_hops("local_transform")
    yield from apply_scale(hops, ["OBJECT"])
    check(modifier_names() == ["Multires"], f"Apply Scale: expected the Multires modifier kept, got {modifier_names()}")
    yield undo()
    check(round(cube().scale.x, 4) == 2.0, f"undo Apply Scale: expected scale x = 2, got {cube().scale.x}")
    check(round(cube().dimensions.x, 4) == 4.0, f"undo Apply Scale: expected width 4, got {cube().dimensions.x}")
    check(mode() == "SCULPT", f"undo Apply Scale: expected Sculpt Mode, got {mode()}")


def hop_apply_scale_dyntopo():
    yield from stretched_cube(dyntopo=True)
    hops = count_hops("local_transform")
    yield from apply_scale(hops, ["OBJECT"])
    check(cube().use_dynamic_topology_sculpting, "Apply Scale: Dyntopo changed")
    call("object.mode_set", undo=False, mode="OBJECT")
    yield 0.3
    check(mesh_width() == 4.0, f"leaving Sculpt Mode after Apply Scale: expected the mesh 4 wide, got {mesh_width()}")


def hop_apply_scale_dyntopo_undo():
    yield from stretched_cube(dyntopo=True)
    hops = count_hops("local_transform")
    yield from apply_scale(hops, ["OBJECT"])
    yield from hop_undo()
    state = (round(cube().scale.x, 4), round(cube().dimensions.x, 4), mode(), cube().use_dynamic_topology_sculpting)
    check(state == (2.0, 4.0, "SCULPT", True), "undo Apply Scale: expected (scale x, width, mode, Dyntopo) = "
          f"(2, 4, SCULPT, on), got {state}")
    yield from hop_redo()
    state = (round(cube().scale.x, 4), round(cube().dimensions.x, 4), mode())
    check(state == (1.0, 4.0, "SCULPT"), "redo Apply Scale: expected (scale x, width, mode) = (1, 4, SCULPT), got "
          f"{state}")
    check(HOP_STEP not in cube(), "redo Apply Scale: the Hop's undo mark was left on the Cube")
    call("object.mode_set", undo=False, mode="OBJECT")
    yield 0.3
    check(mesh_width() == 4.0, f"leaving Sculpt Mode after redo Apply Scale: expected the mesh 4 wide, got "
          f"{mesh_width()}")


def hop_apply_scale_dyntopo_adjust_last():
    """Adjust Last Operation undoes onto the Hop's last step and runs Apply Scale again, which finds nothing left to
    scale and finishes: the extra undos waiting mustn't undo that run, nor its step keep the Hop's mark"""
    yield from stretched_cube(dyntopo=True)
    hops = count_hops("local_transform")
    yield from apply_scale(hops, ["OBJECT"])
    yield adjust_last()
    yield from settle_hop()
    state = (round(cube().scale.x, 4), round(cube().dimensions.x, 4), mode())
    check(state == (1.0, 4.0, "SCULPT"), "Adjust Last Operation on Apply Scale: expected (scale x, width, mode) = "
          f"(1, 4, SCULPT), got {state}")
    check(HOP_STEP not in cube(), "Adjust Last Operation on Apply Scale: the Hop's undo mark was left on the Cube")
    yield from hop_undo()
    state = (round(cube().scale.x, 4), round(cube().dimensions.x, 4), mode(), cube().use_dynamic_topology_sculpting)
    check(state == (2.0, 4.0, "SCULPT", True), "undo after Adjust Last Operation: expected (scale x, width, mode, "
          f"Dyntopo) = (2, 4, SCULPT, on), got {state}")


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


def hop_mirror_apply_dyntopo_undo():
    yield from reset()
    cube().location.x = 2.0
    call("sculpt.dynamic_topology_toggle")
    yield 0.3
    yield from start_tool("sculpt_deck.mirror", "Mirror")
    call("sculpt_deck.mirror_apply")
    yield 0.5
    # both halves, 2 apart: from -3 to 3 in the Cube's own space
    check_dyntopo_state("Apply Mirror", [], 6.0, dyntopo=True)
    yield from hop_undo()
    check_dyntopo_state("undo Apply Mirror", ["Mirror"], 2.0, dyntopo=True)
    yield from hop_redo()
    check_dyntopo_state("redo Apply Mirror", [], 6.0)
    call("object.mode_set", undo=False, mode="OBJECT")
    yield 0.3
    count = len(cube().data.vertices)
    check(count == 16, f"leaving Sculpt Mode after Apply Mirror: expected both halves kept (16 vertices), got {count}")


def pen_events(pen: bool = True):
    """Make the add-on take simulated button presses for pen presses, or, with pen=False, for mouse presses again"""
    for name, module in list(sys.modules.items()):
        if name.startswith(PACKAGE) and hasattr(module, "is_pen"):
            module.is_pen = (lambda event: True) if pen else (lambda event: event.is_tablet)


def simulate(event_type: str, value: str):
    window, area, _region = view3d()
    window.event_simulate(event_type, value, x=area.x + area.width // 2, y=area.y + area.height // 2)


def brush() -> str:
    return bpy.context.tool_settings.sculpt.brush.name


def tool() -> str:
    with override():
        active = bpy.context.workspace.tools.from_space_view3d_mode("SCULPT", create=False)
    return active.idname if active else ""


def prefs():
    return bpy.context.preferences.addons[PACKAGE].preferences


SMOOTH = ("ESSENTIALS", "", "brushes/essentials_brushes-mesh_sculpt.blend/Brush/Smooth")


def bind(settings: dict):
    """Change the add-on settings, given as {(owner, property): value}; returns the old values for unbind"""
    saved = {}
    try:
        for (owner, prop), value in settings.items():
            saved[(owner, prop)] = getattr(owner, prop)
            setattr(owner, prop, value)
    except Exception:
        unbind(saved)
        raise
    return saved


def unbind(saved: dict):
    for (owner, prop), value in saved.items():
        setattr(owner, prop, value)


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


def voxel_size() -> float:
    return round(bpy.context.scene.objects["Cube"].data.remesh_voxel_size, 6)


def mesh_vertex_count() -> int:
    """Vertices of the Cube's own mesh data (not evaluated), for the voxel remesh and mask checks"""
    return len(bpy.context.scene.objects["Cube"].data.vertices)


def resolution_density_up():
    yield from reset()
    bpy.context.scene.objects["Cube"].data.remesh_voxel_size = 0.2
    before_size, before_count = voxel_size(), mesh_vertex_count()
    call("sculpt_deck.density_up")
    yield 0.5
    check(voxel_size() == round(before_size * 0.8, 6), f"Voxel Density Up: expected voxel size {before_size * 0.8}, "
          f"got {voxel_size()}")
    check(mesh_vertex_count() > before_count, f"Voxel Density Up: expected more than {before_count} vertices, "
          f"got {mesh_vertex_count()}")
    check(mode() == "SCULPT", f"Voxel Density Up: expected Sculpt Mode, got {mode()}")
    after_count = mesh_vertex_count()
    yield undo()
    check(mesh_vertex_count() == before_count, f"undo Voxel Density Up: expected {before_count} vertices, "
          f"got {mesh_vertex_count()}")
    check(mode() == "SCULPT", f"undo Voxel Density Up: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(mesh_vertex_count() == after_count, f"redo Voxel Density Up: expected {after_count} vertices, "
          f"got {mesh_vertex_count()}")
    check(voxel_size() == round(before_size * 0.8, 6), f"redo Voxel Density Up: expected voxel size "
          f"{before_size * 0.8}, got {voxel_size()}")
    check(mode() == "SCULPT", f"redo Voxel Density Up: expected Sculpt Mode, got {mode()}")


def resolution_density_up_undo_voxel_size():
    """Undo brings the voxel size back with the geometry (#21), so the next press starts from it"""
    yield from reset()
    bpy.context.scene.objects["Cube"].data.remesh_voxel_size = 0.2
    call("sculpt_deck.density_up")
    yield 0.5
    yield undo()
    check(voxel_size() == 0.2, f"undo Voxel Density Up: expected voxel size 0.2, got {voxel_size()}")
    call("sculpt_deck.density_up")
    yield 0.5
    check(voxel_size() == 0.16, f"Voxel Density Up after undo: expected voxel size 0.16, got {voxel_size()}")


def mask_full() -> bool:
    return set(mask_values()) == {1.0}


def resolution_density_down_undo():
    """Undo and redo bring back both the geometry and the voxel size, and the press leaves one extra step: after
    a mask, the first undo undoes the press, the second its Scene Checkpoint, and the third the mask"""
    yield from reset()
    bpy.context.scene.objects["Cube"].data.remesh_voxel_size = 0.2
    call("sculpt_deck.mask_invert")
    yield 0.5
    before_count = mesh_vertex_count()
    call("sculpt_deck.density_down")
    yield 0.5
    check(voxel_size() == 0.25, f"Voxel Density Down: expected voxel size 0.25, got {voxel_size()}")
    check(mesh_vertex_count() != before_count, f"Voxel Density Down: expected a remesh, still {before_count} vertices")
    check(mode() == "SCULPT", f"Voxel Density Down: expected Sculpt Mode, got {mode()}")
    after_count = mesh_vertex_count()
    yield undo()
    check(voxel_size() == 0.2, f"undo Voxel Density Down: expected voxel size 0.2, got {voxel_size()}")
    check(mesh_vertex_count() == before_count, f"undo Voxel Density Down: expected {before_count} vertices, "
          f"got {mesh_vertex_count()}")
    check(mode() == "SCULPT", f"undo Voxel Density Down: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(voxel_size() == 0.25, f"redo Voxel Density Down: expected voxel size 0.25, got {voxel_size()}")
    check(mesh_vertex_count() == after_count, f"redo Voxel Density Down: expected {after_count} vertices, "
          f"got {mesh_vertex_count()}")
    check(mode() == "SCULPT", f"redo Voxel Density Down: expected Sculpt Mode, got {mode()}")
    yield undo()
    yield undo()
    check(mask_full() and voxel_size() == 0.2, f"second undo after Voxel Density Down: expected the mask and "
          f"voxel size 0.2 kept, got mask {mask_values()[:4]}..., size {voxel_size()}")
    yield undo()
    check(not mask_full(), "third undo after Voxel Density Down: expected the mask undone")


def multires_cube():
    """The Cube with a Multires modifier subdivided twice in Object Mode, with undo steps as a user would, then in
    Sculpt Mode"""
    with override():
        bpy.ops.wm.read_homefile("EXEC_DEFAULT")
    yield 0.5
    call("object.modifier_add", type="MULTIRES")
    call("object.multires_subdivide", modifier="Multires", mode="CATMULL_CLARK")
    call("object.multires_subdivide", modifier="Multires", mode="CATMULL_CLARK")
    call("object.mode_set", mode="SCULPT")
    yield 0.3
    check(mode() == "SCULPT", f"setup: expected Sculpt Mode, got {mode()}")


def multires_levels() -> tuple[int, int]:
    mod = cube().modifiers["Multires"]
    return mod.sculpt_levels, mod.total_levels


def resolution_multires_undo():
    """Multires Level Down and Up (a level change and a subdivision) in Sculpt Mode, each undone and redone"""
    yield from multires_cube()
    check(multires_levels() == (2, 2), f"setup: expected levels (2, 2), got {multires_levels()}")
    for idname, label, expected in [
        ("sculpt_deck.decrement_multires", "Multires Level Down", (1, 2)),
        ("sculpt_deck.increment_multires", "Multires Level Up", (2, 2)),
        ("sculpt_deck.increment_multires", "Multires Level Up (subdivide)", (3, 3)),
    ]:
        before = multires_levels()
        call(idname)
        yield 0.5
        check(multires_levels() == expected, f"{label}: expected (sculpt, total) levels {expected}, "
              f"got {multires_levels()}")
        yield undo()
        check(multires_levels() == before, f"undo {label}: expected levels {before}, got {multires_levels()}")
        check(mode() == "SCULPT", f"undo {label}: expected Sculpt Mode, got {mode()}")
        yield redo()
        check(multires_levels() == expected, f"redo {label}: expected levels {expected}, got {multires_levels()}")
        check(mode() == "SCULPT", f"redo {label}: expected Sculpt Mode, got {mode()}")


def resolution_multires_down_fails():
    """Multires Level Down at level 0 of a mesh Blender can't unsubdivide cancels with a warning, raising nothing"""
    with override():
        bpy.ops.wm.read_homefile("EXEC_DEFAULT")
    yield 0.5
    call("object.modifier_add", type="MULTIRES")
    call("object.mode_set", mode="SCULPT")
    yield 0.3
    with override():
        result = bpy.ops.sculpt_deck.decrement_multires("EXEC_DEFAULT", True)
    yield 0.5
    check(result == {"CANCELLED"}, f"Multires Level Down at level 0: expected CANCELLED, got {result}")
    check(multires_levels() == (0, 0), f"Multires Level Down at level 0: expected levels (0, 0), "
          f"got {multires_levels()}")
    check(mode() == "SCULPT", f"Multires Level Down at level 0: expected Sculpt Mode, got {mode()}")


DRAW = ("ESSENTIALS", "", "brushes/essentials_brushes-mesh_sculpt.blend/Brush/Draw")


def shape() -> tuple:
    """The Cube's evaluated vertex positions (Multires at its viewport level), read in Object Mode.

    Sculpt Mode doesn't update the evaluated mesh after a stroke, and keeps Multires strokes in its own grids until
    the mode is left, so this leaves it for the reading (with no undo step) and comes back. Leaving also writes the
    strokes into the mesh, so a scenario that checks a stroke reaches an undo step reads the shape only afterwards.
    """
    start = mode()
    with override():
        bpy.ops.object.mode_set("EXEC_DEFAULT", False, mode="OBJECT")
        obj = cube().evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = obj.to_mesh()
        positions = tuple(tuple(vertex.co) for vertex in mesh.vertices)
        obj.to_mesh_clear()
        if start == "SCULPT":
            bpy.ops.object.mode_set("EXEC_DEFAULT", False, mode="SCULPT")
    return positions


def same_shape(a: tuple, b: tuple) -> bool:
    """The same vertex count, and every position within 0.001 (an undone stroke comes back within about 0.0001)"""
    return len(a) == len(b) and all(abs(x - y) <= 1e-3 for u, v in zip(a, b) for x, y in zip(u, v))


def stroke():
    """A real Draw brush stroke across the middle of the Cube, as seen in the 3D viewport, with its undo step"""
    from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d

    library_type, library, identifier = DRAW
    with override():
        bpy.ops.brush.asset_activate(asset_library_type=library_type, asset_library_identifier=library,
                                     relative_asset_identifier=identifier)
    _window, _area, region = view3d()
    x, y = region_point("Cube")
    points = []
    for index, dx in enumerate(range(-60, 61, 20)):
        mouse = (x + dx, y + dx // 3)
        # an executed stroke takes each point's 3D location as given, so it's found on the surface here
        origin = region_2d_to_origin_3d(region, region.data, mouse)
        direction = region_2d_to_vector_3d(region, region.data, mouse)
        hit, location, *_ = bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(), origin, direction)
        check(hit, f"stroke: the point {mouse} misses the Cube")
        points.append({"name": "", "location": location, "mouse": mouse, "mouse_event": mouse, "is_start": index == 0,
                       "pressure": 1.0, "size": 60.0, "time": float(index), "x_tilt": 0.0, "y_tilt": 0.0})
    call("sculpt.brush_stroke", stroke=points)
    yield 0.5


def stroke_survives(label: str, setup, run, undone, done):
    """A stroke made right before an action is kept when the action is undone.

    Reading the shape flushes the stroke (see `shape`), so the stroked shape comes from a first pass (setup, stroke),
    and a second one (setup, stroke, the action, undo) is compared with it. `undone()` and `done()` check the
    action's own change, after undo and after redo."""
    yield from setup()
    before = shape()
    yield from stroke()
    stroked = shape()
    check(not same_shape(stroked, before), "stroke: expected the Draw brush to change the Cube's shape")
    yield from setup()
    yield from stroke()
    yield from run()
    check(done(), f"{label}: didn't change anything")
    yield undo()
    check(undone(), f"undo {label}: expected it undone")
    check(mode() == "SCULPT", f"undo {label}: expected Sculpt Mode, got {mode()}")
    check(same_shape(shape(), stroked), f"undo {label}: expected the stroke made before it kept, the shape differs")
    yield redo()
    check(done(), f"redo {label}: expected it applied again")
    check(mode() == "SCULPT", f"redo {label}: expected Sculpt Mode, got {mode()}")


def resolution_multires_undo_keeps_stroke():
    """Undoing a Multires level change keeps a stroke made just before it"""

    def run():
        call("sculpt_deck.increment_multires")
        yield 0.5

    yield from stroke_survives("Multires Level Up", multires_cube, run, lambda: multires_levels() == (2, 2),
                               lambda: multires_levels() == (3, 3))


def remeshed_cube():
    """The Cube voxel remeshed at 0.1, in Sculpt Mode"""
    yield from reset()
    cube().data.remesh_voxel_size = 0.1
    call("object.voxel_remesh")
    yield 0.5


def resolution_density_undo_keeps_stroke():
    """Undoing Voxel Density Up keeps a stroke made just before it"""

    def run():
        call("sculpt_deck.density_up")
        yield 0.5

    yield from stroke_survives("Voxel Density Up", remeshed_cube, run, lambda: voxel_size() == 0.1,
                               lambda: voxel_size() == 0.08)


def mask_values() -> list[float]:
    attribute = bpy.context.scene.objects["Cube"].data.attributes.get(".sculpt_mask")
    if attribute is None:
        return [0.0] * mesh_vertex_count()
    return [round(item.value, 4) for item in attribute.data]


def masks_invert():
    yield from reset()
    check(set(mask_values()) == {0.0}, f"setup: expected no mask, got {mask_values()}")
    call("sculpt_deck.mask_invert")
    yield 0.5
    check(set(mask_values()) == {1.0}, f"Invert Mask: expected a full mask, got {mask_values()}")
    check(mode() == "SCULPT", f"Invert Mask: expected Sculpt Mode, got {mode()}")
    yield undo()
    check(set(mask_values()) == {0.0}, f"undo Invert Mask: expected no mask, got {mask_values()}")
    check(mode() == "SCULPT", f"undo Invert Mask: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(set(mask_values()) == {1.0}, f"redo Invert Mask: expected a full mask, got {mask_values()}")


def sidebar_shown() -> bool:
    _window, area, _region = view3d()
    return area.spaces.active.show_region_ui


def interface_toggle_sidebar():
    yield from reset()
    before = sidebar_shown()
    call("sculpt_deck.toggle_n_panel")
    yield 0.3
    check(sidebar_shown() != before, f"Toggle Sidebar: expected the sidebar shown = {not before}")
    call("sculpt_deck.toggle_n_panel")
    yield 0.3
    check(sidebar_shown() == before, f"Toggle Sidebar again: expected the sidebar shown = {before}")
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
def pen_click_brush():
    """A click of a pen button bound to a brush switches to it for good"""
    yield from reset()
    pen_events()
    upper = prefs().pen.getPenSet("SCULPT").upper_click
    hold = prefs().pen.getPenSet("SCULPT").upper_hold
    saved = bind({(upper, "action"): "BRUSH", (hold, "action"): "NONE"})
    old_ref = upper.brushRef()
    upper.setBrushRef(SMOOTH)
    try:
        check(brush() != "Smooth", "setup: the starting brush is already Smooth")
        simulate("MOUSEMOVE", "NOTHING")
        yield 0.2
        simulate("RIGHTMOUSE", "PRESS")
        yield 0.05
        simulate("RIGHTMOUSE", "RELEASE")
        yield 0.5
        check(brush() == "Smooth", f"pen click: expected the Smooth brush, got {brush()}")
        yield 0.5
        check(brush() == "Smooth", f"after the pen click: expected the Smooth brush to stay, got {brush()}")
    finally:
        unbind(saved)
        upper.setBrushRef(old_ref or ("", "", ""))


def pen_hold_momentary_tool():
    """A hold of a pen button bound to a Momentary tool uses it while held, and puts the brush tool back"""
    yield from reset()
    pen_events()
    pen_set = prefs().pen.getPenSet("SCULPT")
    saved = bind({(pen_set.upper_click, "action"): "NONE", (pen_set.upper_hold, "action"): "TOOL:builtin.box_mask"})
    try:
        before = tool()
        check(before == "builtin.brush", f"setup: expected the brush tool, got {before}")
        simulate("MOUSEMOVE", "NOTHING")
        yield 0.2
        simulate("RIGHTMOUSE", "PRESS")
        yield 0.8
        check(tool() == "builtin.box_mask", f"pen hold: expected the Box Mask tool while held, got {tool()}")
        simulate("RIGHTMOUSE", "RELEASE")
        yield 0.5
        check(tool() == before, f"pen release: expected {before} back, got {tool()}")
    finally:
        unbind(saved)


def right_click_action():
    """A mouse right click runs the right click action set for the mode, here a tool"""
    yield from reset()
    pen_events(pen=False)
    pen_set = prefs().pen.getPenSet("SCULPT")
    saved = bind({(prefs().clicks, "enable_right_click"): True, (pen_set.right_click, "action"): "TOOL:builtin.box_mask"})
    try:
        check(tool() == "builtin.brush", f"setup: expected the brush tool, got {tool()}")
        simulate("MOUSEMOVE", "NOTHING")
        yield 0.2
        simulate("RIGHTMOUSE", "PRESS")
        yield 0.1
        simulate("RIGHTMOUSE", "RELEASE")
        yield 0.5
        check(tool() == "builtin.box_mask", f"right click: expected the Box Mask tool, got {tool()}")
    finally:
        unbind(saved)


def double_click_action():
    """A double tap runs the double click action set for the mode, here a tool. event_simulate can't make a
    DOUBLE_CLICK event, so this goes through the touch tap handling, which runs the double click action itself"""
    yield from reset()
    pen_events(pen=False)
    pen_set = prefs().pen.getPenSet("SCULPT")
    saved = bind({(prefs().clicks, "enable_double_click"): True, (pen_set.double_click, "action"): "TOOL:builtin.box_mask"})
    try:
        check(tool() == "builtin.brush", f"setup: expected the brush tool, got {tool()}")
        simulate("MOUSEMOVE", "NOTHING")
        yield 0.2
        for _ in range(2):
            simulate("LEFTMOUSE", "PRESS")
            yield 0.05
            simulate("LEFTMOUSE", "RELEASE")
            yield 0.05
        yield 0.5
        check(tool() == "builtin.box_mask", f"double click: expected the Box Mask tool, got {tool()}")
    finally:
        unbind(saved)


def region_point(name: str) -> tuple[int, int]:
    """Where an object's origin shows in the 3D viewport, in region coordinates"""
    from bpy_extras.view3d_utils import location_3d_to_region_2d

    _window, _area, region = view3d()
    point = location_3d_to_region_2d(region, region.data, bpy.context.scene.objects[name].matrix_world.translation)
    check(point is not None, f"{name} isn't in view")
    check(0 < point.x < region.width and 0 < point.y < region.height, f"{name} is outside the viewport at {point}")
    return round(point.x), round(point.y)


def touch(value: str, x: int, y: int, event_type: str = "LEFTMOUSE"):
    """A simulated touch (a press without a tablet) at x, y of the 3D viewport region"""
    window, _area, region = view3d()
    window.event_simulate(event_type, value, x=region.x + x, y=region.y + y)


def object_tap_switches_object():
    """Tapping another object in Sculpt Mode switches to it and stays in Sculpt Mode"""
    yield from reset(extra_cubes=1)
    pen_events(pen=False)
    x, y = region_point("Cube.001")
    touch("NOTHING", x, y, "MOUSEMOVE")
    yield 0.2
    touch("PRESS", x, y)
    yield 0.05
    touch("RELEASE", x, y)
    # the tap waits out the double tap time first (a double click action is set by default)
    yield 1.0
    active = bpy.context.view_layer.objects.active
    check(active.name == "Cube.001", f"tap: expected Cube.001 active, got {active.name}")
    check(mode() == "SCULPT", f"tap: expected Sculpt Mode, got {mode()}")
    check(bpy.context.scene.objects["Cube.001"].mode == "SCULPT", "tap: Cube.001 isn't in Sculpt Mode")


def object_tap_long_press_toggles_selection():
    """A long press on another object adds it to the selection, a second one removes it, the active one stays"""
    yield from reset(extra_cubes=1)
    pen_events(pen=False)
    other = bpy.context.scene.objects["Cube.001"]
    check(not other.select_get(), "setup: Cube.001 is already selected")
    x, y = region_point("Cube.001")
    touch("NOTHING", x, y, "MOUSEMOVE")
    yield 0.2
    for expected in (True, False):
        touch("PRESS", x, y)
        yield 0.9
        touch("RELEASE", x, y)
        yield 0.5
        check(other.select_get() == expected, f"long press: expected Cube.001 selected = {expected}")
        active = bpy.context.view_layer.objects.active
        check(active.name == "Cube", f"long press: expected Cube to stay active, got {active.name}")
        check(mode() == "SCULPT", f"long press: expected Sculpt Mode, got {mode()}")


def touch_drag(x: int, y: int, dx: int, dy: int):
    """Press at x, y of the viewport region, move by dx, dy in steps, release"""
    touch("NOTHING", x, y, "MOUSEMOVE")
    yield 0.2
    touch("PRESS", x, y)
    yield 0.05
    steps = 10
    for step in range(1, steps + 1):
        touch("NOTHING", x + dx * step // steps, y + dy * step // steps, "MOUSEMOVE")
        yield 0.05
    touch("RELEASE", x + dx, y + dy)
    yield 0.3


def navigation_touch_drag():
    """A touch drag in the middle of the viewport pans the view, one between the middle and the side rails rotates
    it, in Sculpt Mode, and neither sculpts"""
    yield from reset()
    pen_events(pen=False)
    _window, _area, region = view3d()
    view = region.data
    before_location, before_rotation = view.view_location.copy(), view.view_rotation.copy()
    before_vertices = [vertex.co.copy() for vertex in bpy.context.scene.objects["Cube"].data.vertices]
    yield from touch_drag(region.width // 2, region.height // 2, 120, 60)
    check((view.view_location - before_location).length > 0.01, "drag in the middle: the view didn't pan")
    check(view.view_rotation.rotation_difference(before_rotation).angle < 0.001, "drag in the middle: the view rotated")
    before_location, before_rotation = view.view_location.copy(), view.view_rotation.copy()
    yield from touch_drag(region.width * 3 // 10, region.height // 2, 0, 120)
    check(view.view_rotation.rotation_difference(before_rotation).angle > 0.01, "drag off the middle: no rotation")
    check(mode() == "SCULPT", f"after the drags: expected Sculpt Mode, got {mode()}")
    after_vertices = [vertex.co.copy() for vertex in bpy.context.scene.objects["Cube"].data.vertices]
    check(after_vertices == before_vertices, "the drags sculpted the Cube")


def navigation_floating_toggle():
    """A tap on the floating toggle turns touch controls off, a second one back on, and the button stays put"""
    yield from reset()
    toggle = sys.modules[PACKAGE + ".source.navigation.toggle"]
    group_class = toggle.SCULPT_DECK_GGT_touch_toggle
    settings = prefs().navigation
    saved = bind({(settings, "enable_floating_toggle"): True, (settings, "input_mode"): "FULL"})
    found = []
    original = group_class.draw_prepare

    def draw_prepare(self, context):
        original(self, context)
        found.append(self)

    group_class.draw_prepare = draw_prepare
    try:
        position = tuple(settings.toggle_position)
        before = settings.is_enabled
        for expected in (not before, before):
            found.clear()
            for _ in range(20):
                _window, area, _region = view3d()
                area.tag_redraw()
                yield 0.1
                if found:
                    break
            check(bool(found), "the floating toggle's gizmo group didn't draw")
            group = found[-1]
            button = group.on if settings.is_enabled else group.off
            check(not button.hide, "the floating toggle is hidden")
            window, _area, region = view3d()
            point = button.matrix_basis.translation
            x, y = region.x + round(point.x), region.y + round(point.y)
            window.event_simulate("MOUSEMOVE", "NOTHING", x=x, y=y)
            yield 0.3
            window.event_simulate("LEFTMOUSE", "PRESS", x=x, y=y)
            yield 0.05
            window.event_simulate("LEFTMOUSE", "RELEASE", x=x, y=y)
            yield 0.5
            check(settings.is_enabled == expected, f"floating toggle tap: expected touch controls on = {expected}")
            check(tuple(settings.toggle_position) == position, "floating toggle tap: the button moved")
    finally:
        group_class.draw_prepare = original
        unbind(saved)


def preferences_draw():
    """The add-on's preferences draw every section, in each tab, without an error. Drawn the way the Preferences
    window draws them, into the 3D View's header, which always draws"""
    from bl_ui.space_userpref import USERPREF_PT_addons

    prefs_class = type(prefs())
    drawn, errors = [], []
    original = prefs_class.draw

    def draw(self, context):
        try:
            original(self, context)
            drawn.append(self.gizmo_tabs)
        except Exception as error:
            errors.append(f"{self.gizmo_tabs}: {error!r}")
            raise

    def draw_in_header(header, context):
        USERPREF_PT_addons.draw_addon_preferences(header.layout.column(), context, prefs())

    prefs_class.draw = draw
    bpy.types.VIEW3D_HT_header.append(draw_in_header)
    saved = bind({(prefs(), "gizmo_tabs"): "GIZMO"})
    try:
        for tab in ("GIZMO", "ACTIONS", "PEN"):
            prefs().gizmo_tabs = tab
            _window, area, _region = view3d()
            area.tag_redraw()
            yield 0.3
        check(not errors, f"the preferences failed to draw: {errors}")
        check(set(drawn) == {"GIZMO", "ACTIONS", "PEN"}, f"the preferences drew only the tabs {sorted(set(drawn))}")
    finally:
        bpy.types.VIEW3D_HT_header.remove(draw_in_header)
        prefs_class.draw = original
        unbind(saved)
        _window, area, _region = view3d()
        area.tag_redraw()
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
    local_transform_two_objects,
    hop_modes,
    array_apply,
    hop_array_apply_dyntopo,
    hop_array_apply_dyntopo_undo,
    hop_array_apply_dyntopo_twice,
    hop_array_apply_dyntopo_history,
    hop_array_apply_dyntopo_adjust_last,
    hop_mark_cleared_on_load,
    apply_scale_undo,
    hop_apply_scale_multires,
    hop_apply_scale_dyntopo,
    hop_apply_scale_dyntopo_undo,
    hop_apply_scale_dyntopo_adjust_last,
    mirror_apply,
    hop_mirror_apply_dyntopo_undo,
    pen_hold_momentary_brush,
    resolution_density_up,
    resolution_density_up_undo_voxel_size,
    resolution_density_down_undo,
    resolution_multires_undo,
    resolution_multires_down_fails,
    resolution_multires_undo_keeps_stroke,
    resolution_density_undo_keeps_stroke,
    masks_invert,
    interface_toggle_sidebar,
    widget_button_runs_action,
    widget_button_opens_action_pie,
    pen_click_brush,
    pen_hold_momentary_tool,
    right_click_action,
    double_click_action,
    object_tap_switches_object,
    object_tap_long_press_toggles_selection,
    navigation_touch_drag,
    navigation_floating_toggle,
    preferences_draw,
]

# Scenarios that fail on purpose because of a known bug, with the reason. They report XFAIL and don't fail the
# run; once the bug is fixed they report XPASS, which does, so the entry gets removed.
KNOWN_FAILURES = {
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
