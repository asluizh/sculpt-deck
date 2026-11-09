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


def adjust_last(undo: bool = True, cancelled: bool = False, **props):
    """Adjust Last Operation: change the last operator's settings and run it again from the step before it.

    With `undo` it runs with an undo step, like `call` and like the Adjust Last Operation panel. Without one, Blender
    treats it as called from a script: the repeated operator stores no undo step (the history stays one step
    behind) and runs before the mode of the step undone to is back, in Object Mode, which is how a Detour that
    took its mode from the current one ended in the wrong mode (#13).

    Fails unless the operator ran again, or with `cancelled`, unless it cancelled: Blender cancels without a word
    when the operator's poll fails on the state after it, before undoing (#29).
    """
    with override():
        last = bpy.context.active_operator
        check(last is not None, "no last operation to adjust")
        for name, value in props.items():
            setattr(last.properties, name, value)
        result = bpy.ops.ed.undo_redo("EXEC_DEFAULT", undo)
    expected = {"CANCELLED"} if cancelled else {"FINISHED"}
    check(result == expected, f"Adjust Last Operation on {last.bl_idname}: expected {expected}, got {result}")
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


def array_on(name: str):
    """A Linear Array on the named mesh, as its tool adds it: three copies stepping along X"""
    obj = bpy.context.scene.objects[name]
    sys.modules[PACKAGE + ".source.features.array.operators"].add_array(obj, "LINEAR", "LOCAL", None)
    obj.update_tag()


def modifiers_of(name: str = "Cube") -> list[str]:
    return [modifier.name for modifier in bpy.context.scene.objects[name].modifiers]


def real_vertices() -> int:
    """Vertices of the Cube's own mesh: array copies count only once applied"""
    return len(bpy.context.scene.objects["Cube"].data.vertices)


def max_x() -> float:
    obj = bpy.context.scene.objects["Cube"]
    return max((obj.matrix_world @ vertex.co).x for vertex in obj.data.vertices)


def combine_join_applies_others_modifiers():
    """Join keeps what each mesh shows: the other mesh's array is applied before joining (#29)"""
    yield from reset(extra_cubes=1)
    array_on("Cube.001")
    bpy.context.scene.objects["Cube.001"].select_set(True)
    call("sculpt_deck.join_selected")
    yield 1.0
    check(meshes() == ["Cube"], f"Join: expected only the Cube, got {meshes()}")
    check(modifiers_of() == [], f"Join: expected no modifiers, got {modifiers_of()}")
    check(real_vertices() == 32, f"Join: expected the copies joined as mesh (32 vertices), got {real_vertices()}")
    check(mode() == "SCULPT", f"Join: expected to end in Sculpt Mode, got {mode()}")
    yield undo()
    check(meshes() == ["Cube", "Cube.001"], f"undo Join: expected both cubes, got {meshes()}")
    check(modifiers_of("Cube.001") == ["Linear Array"], f"undo Join: expected the array back, got "
          f"{modifiers_of('Cube.001')}")
    check(mode() == "SCULPT", f"undo Join: expected Sculpt Mode, got {mode()}")
    yield redo()
    check(meshes() == ["Cube"] and real_vertices() == 32, f"redo Join: expected the Cube with 32 vertices, got "
          f"{meshes()}, {real_vertices()}")


def combine_join_keeps_matching_modifiers():
    """Arrays that step the same way in the world stay as the active mesh's array, without asking (#29)"""
    yield from reset(extra_cubes=1)
    array_on("Cube")
    array_on("Cube.001")
    bpy.context.scene.objects["Cube.001"].select_set(True)
    with override():
        result = bpy.ops.sculpt_deck.join_selected("INVOKE_DEFAULT", True)
    check(result == {"FINISHED"}, f"Join: expected it to run without asking, got {result}")
    yield 1.0
    check(meshes() == ["Cube"], f"Join: expected only the Cube, got {meshes()}")
    check(modifiers_of() == ["Linear Array"], f"Join: expected the array kept, got {modifiers_of()}")
    check(real_vertices() == 16, f"Join: expected both cubes as mesh, the copies as instances (16 vertices), got "
          f"{real_vertices()}")
    check(mode() == "SCULPT", f"Join: expected to end in Sculpt Mode, got {mode()}")


def combine_join_differing_modifiers():
    """The active mesh's array would act differently on the other mesh: Apply All applies it, Keep Active's
    Modifiers keeps it, and Adjust Last Operation switches between them (#29)"""
    yield from reset(extra_cubes=1)
    array_on("Cube")
    bpy.context.scene.objects["Cube.001"].select_set(True)
    call("sculpt_deck.join_selected")
    yield 1.0
    check(modifiers_of() == [], f"Join (Apply All): expected no modifiers, got {modifiers_of()}")
    check(real_vertices() == 32, f"Join (Apply All): expected 32 vertices, got {real_vertices()}")
    yield adjust_last(modifiers="KEEP_ACTIVE")
    yield 0.5
    check(meshes() == ["Cube"], f"Keep Active's Modifiers: expected only the Cube, got {meshes()}")
    check(modifiers_of() == ["Linear Array"], f"Keep Active's Modifiers: expected the array kept, got {modifiers_of()}")
    check(real_vertices() == 16, f"Keep Active's Modifiers: expected 16 vertices, got {real_vertices()}")
    check(mode() == "SCULPT", f"Keep Active's Modifiers: expected Sculpt Mode, got {mode()}")
    yield undo()
    check(meshes() == ["Cube", "Cube.001"], f"undo Join: expected both cubes, got {meshes()}")
    check(mode() == "SCULPT", f"undo Join: expected Sculpt Mode, got {mode()}")


def combine_join_asks():
    """From the UI, Join asks first when the active mesh's modifiers would act differently; cancelling changes
    nothing (#29)"""
    yield from reset(extra_cubes=1)
    array_on("Cube")
    bpy.context.scene.objects["Cube.001"].select_set(True)
    with override():
        result = bpy.ops.sculpt_deck.join_selected("INVOKE_DEFAULT", True)
    check(result == {"RUNNING_MODAL"}, f"Join: expected the question, got {result}")
    yield 0.5
    check(meshes() == ["Cube", "Cube.001"], f"Join asking: expected both cubes still, got {meshes()}")
    simulate("ESC", "PRESS")
    simulate("ESC", "RELEASE")
    yield 0.5
    check(meshes() == ["Cube", "Cube.001"], f"Join cancelled: expected both cubes, got {meshes()}")
    check(modifiers_of() == ["Linear Array"], f"Join cancelled: expected the array, got {modifiers_of()}")
    check(mode() == "SCULPT", f"Join cancelled: expected Sculpt Mode, got {mode()}")


def circular_on(name: str):
    """A Circular Array of 4 on the named mesh around the world point (6, 0, 0), turning about the world Z axis"""
    from mathutils import Vector

    operators = sys.modules[PACKAGE + ".source.features.array.operators"]
    obj = bpy.context.scene.objects[name]
    bpy.context.view_layer.update()
    modifier = obj.modifiers.new("Circular Array", "NODES")
    modifier.node_group = operators.node_group("CIRCULAR")
    operators.set_input(obj, modifier, "Count", 4)
    operators.set_input(obj, modifier, "Center", obj.matrix_world.inverted() @ Vector((6.0, 0.0, 0.0)))
    axis = obj.matrix_world.to_3x3().inverted() @ Vector((0.0, 0.0, 1.0))
    operators.set_input(obj, modifier, "Axis", axis.normalized())


def drawn_points() -> list[tuple]:
    """Every vertex drawn, real or instanced, in the world"""
    points = set()
    for instance in bpy.context.evaluated_depsgraph_get().object_instances:
        if instance.object.type == "MESH":
            for vertex in instance.object.data.vertices:
                points.add(tuple(round(value, 3) for value in instance.matrix_world @ vertex.co))
    return sorted(points)


def invoke_join():
    with override():
        return bpy.ops.sculpt_deck.join_selected("INVOKE_DEFAULT", True)


def combine_join_circular_scaled():
    """Circular arrays turning about the same world centre and axis draw the same under any rotation and scale: Join
    keeps the active's without asking, and every copy stays where it was (#29)"""
    yield from reset(extra_cubes=1)
    bpy.context.scene.objects["Cube"].scale = (1.0, 2.0, 1.0)
    bpy.context.scene.objects["Cube.001"].scale = (0.5, 1.0, 1.5)
    bpy.context.scene.objects["Cube.001"].rotation_euler.z = 0.7
    circular_on("Cube")
    circular_on("Cube.001")
    bpy.context.scene.objects["Cube.001"].select_set(True)
    yield 0.3
    before = drawn_points()
    result = invoke_join()
    check(result == {"FINISHED"}, f"Join: expected it to run without asking, got {result}")
    yield 1.0
    check(modifiers_of() == ["Circular Array"], f"Join: expected the array kept, got {modifiers_of()}")
    after = drawn_points()
    check(after == before, f"Join: expected every copy where it was, {len(set(before) ^ set(after))} points moved")


def combine_join_circular_sheared():
    """Under a shear the same circular array turns the copies differently, so Join asks (#29)"""
    yield from reset(extra_cubes=1)
    with override():
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.empty_add()
        stretched = bpy.context.active_object
        stretched.scale = (1.0, 3.0, 1.0)
        bpy.ops.object.empty_add()
        turned = bpy.context.active_object
        turned.parent = stretched
        turned.rotation_euler.z = 0.6
    bpy.context.scene.objects["Cube"].parent = turned
    yield from reset_selection_to_sculpt()
    circular_on("Cube")
    circular_on("Cube.001")
    bpy.context.scene.objects["Cube.001"].select_set(True)
    result = invoke_join()
    check(result == {"RUNNING_MODAL"}, f"Join: expected the question, got {result}")
    yield 0.5
    simulate("ESC", "PRESS")
    simulate("ESC", "RELEASE")
    yield 0.5
    check(meshes() == ["Cube", "Cube.001"], f"Join cancelled: expected both cubes, got {meshes()}")


def reset_selection_to_sculpt():
    """Back to the Cube alone selected and active, in Sculpt Mode"""
    with override():
        bpy.ops.object.select_all(action="DESELECT")
    cube().select_set(True)
    bpy.context.view_layer.objects.active = cube()
    call("object.mode_set", mode="SCULPT")
    yield 0.3


def combine_join_asks_preselects_possible():
    """Shape keys on the active mesh stop Apply All, so the question starts on Keep Active's Modifiers, and
    confirming it joins (#29)"""
    yield from reset(extra_cubes=1)
    cube().shape_key_add(name="Basis")
    array_on("Cube")
    bpy.context.scene.objects["Cube.001"].select_set(True)
    result = invoke_join()
    check(result == {"RUNNING_MODAL"}, f"Join: expected the question, got {result}")
    yield 0.5
    simulate("RET", "PRESS")
    simulate("RET", "RELEASE")
    yield 1.0
    check(meshes() == ["Cube"], f"Join confirmed: expected only the Cube, got {meshes()}")
    check(modifiers_of() == ["Linear Array"], f"Join confirmed: expected the array kept, got {modifiers_of()}")


def combine_fuse_applies_modifiers():
    """Fuse applies every modifier first: the other mesh's copies are fused in, not lost (#29)"""
    yield from reset(extra_cubes=1)
    array_on("Cube.001")
    bpy.context.scene.objects["Cube.001"].select_set(True)
    call("sculpt_deck.fuse_selected", voxel_size=0.2)
    yield 1.0
    check(meshes() == ["Cube"], f"Fuse: expected only the Cube, got {meshes()}")
    check(modifiers_of() == [], f"Fuse: expected no modifiers, got {modifiers_of()}")
    # Cube.001 spans x 2..4, its copies step 2.2 along X, so the last one ends at 8.4
    check(max_x() > 8.0, f"Fuse: expected the copies fused in (reaching x = 8.4), got {max_x():.2f}")
    check(mode() == "SCULPT", f"Fuse: expected to end in Sculpt Mode, got {mode()}")
    yield undo()
    check(modifiers_of("Cube.001") == ["Linear Array"], f"undo Fuse: expected the array back, got "
          f"{modifiers_of('Cube.001') if 'Cube.001' in meshes() else meshes()}")


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


# the custom property marking the undo steps undo and redo step over (core/step_over.py): Scene Checkpoints and a
# Hop's steps under Dyntopo, never left on the object
STEP_OVER = "sculpt_deck_step_over"


def settle():
    """Wait for the extra undos or redos stepping over marked steps, each run from a timer"""
    step_over = sys.modules[PACKAGE + ".source.core.step_over"]
    for _ in range(20):
        yield 0.25
        active = bpy.context.view_layer.objects.active
        if step_over.scheduled == 0 and (active is None or STEP_OVER not in active):
            break
    yield 0.25


def settled_undo():
    yield undo()
    yield from settle()


def settled_redo():
    yield redo()
    yield from settle()


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
    check(STEP_OVER not in cube(), f"{when}: the Hop's undo mark was left on the Cube")


def hop_array_apply_dyntopo_undo():
    yield from add_and_apply_array(dyntopo=True)
    check_dyntopo_state("Apply Array", [], 6.4, dyntopo=True)
    yield from settled_undo()
    check_dyntopo_state("undo Apply Array", ["Linear Array"], 2.0, dyntopo=True)
    yield from settled_redo()
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
        ([], 6.4, True),
        (["Linear Array"], 2.0, True),
    ]
    for index, (modifiers, width, dyntopo) in enumerate(steps):
        yield from settled_undo()
        check_dyntopo_state(f"undo {index + 1}", modifiers, width, dyntopo)
    for index, (modifiers, width) in enumerate([([], 6.4), (["Linear Array"], 6.4), ([], 20.48)]):
        yield from settled_redo()
        check_dyntopo_state(f"redo {index + 1}", modifiers, width)


def hop_array_apply_dyntopo_history():
    """Jumping in the Undo History list onto one of the Hop's steps steps over them too"""
    yield from add_and_apply_array(dyntopo=True)
    # the indexes follow the Hop's steps (the runner prints the history on failure): 3-9 the Hop of Add Linear
    # Array, 10 Add Linear Array, 11-13 the Dyntopo toggle before the apply's Hop, 14-15 leaving Sculpt Mode, 16-17
    # back in it, 18 Apply Array
    for item, modifiers, width, dyntopo in ((15, ["Linear Array"], 2.0, True), (17, [], 6.4, None),
                                            (16, ["Linear Array"], 2.0, True)):
        with override():
            bpy.ops.ed.undo_history(item=item)
        yield from settle()
        check_dyntopo_state(f"jump to undo step {item}", modifiers, width, dyntopo)


def hop_array_apply_dyntopo_adjust_last():
    """Adjust Last Operation undoes onto the Hop's last step and runs Apply Array again, which finds nothing left to
    apply: it stays applied, and isn't undone afterwards"""
    yield from add_and_apply_array(dyntopo=True)
    yield adjust_last(cancelled=True)
    yield from settle()
    check_dyntopo_state("Adjust Last Operation on Apply Array", [], 6.4)
    yield from settled_undo()
    check_dyntopo_state("undo after Adjust Last Operation", ["Linear Array"], 2.0, dyntopo=True)


def hop_mark_cleared_on_load():
    """A file saved while on one of the Hop's steps would keep its mark: opening it drops the mark"""
    yield from reset()
    cube()[STEP_OVER] = "INSIDE"
    path = os.path.join(tempfile.gettempdir(), "sculpt_deck_hop_mark.blend")
    with override():
        bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
        bpy.ops.wm.open_mainfile(filepath=path)
    yield 0.5
    check(STEP_OVER not in cube(), "opening a file: the Hop's undo mark was kept")
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
    yield from settled_undo()
    state = (round(cube().scale.x, 4), round(cube().dimensions.x, 4), mode(), cube().use_dynamic_topology_sculpting)
    check(state == (2.0, 4.0, "SCULPT", True), "undo Apply Scale: expected (scale x, width, mode, Dyntopo) = "
          f"(2, 4, SCULPT, on), got {state}")
    yield from settled_redo()
    state = (round(cube().scale.x, 4), round(cube().dimensions.x, 4), mode())
    check(state == (1.0, 4.0, "SCULPT"), "redo Apply Scale: expected (scale x, width, mode) = (1, 4, SCULPT), got "
          f"{state}")
    check(STEP_OVER not in cube(), "redo Apply Scale: the Hop's undo mark was left on the Cube")
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
    yield from settle()
    state = (round(cube().scale.x, 4), round(cube().dimensions.x, 4), mode())
    check(state == (1.0, 4.0, "SCULPT"), "Adjust Last Operation on Apply Scale: expected (scale x, width, mode) = "
          f"(1, 4, SCULPT), got {state}")
    check(STEP_OVER not in cube(), "Adjust Last Operation on Apply Scale: the Hop's undo mark was left on the Cube")
    yield from settled_undo()
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
    yield from settled_undo()
    check_dyntopo_state("undo Apply Mirror", ["Mirror"], 2.0, dyntopo=True)
    yield from settled_redo()
    check_dyntopo_state("redo Apply Mirror", [], 6.0)
    call("object.mode_set", undo=False, mode="OBJECT")
    yield 0.3
    count = len(cube().data.vertices)
    check(count == 16, f"leaving Sculpt Mode after Apply Mirror: expected both halves kept (16 vertices), got {count}")


def tool_add_undo_redo(idname: str, modifier: str, previous: str | None = "builtin.box_mask", dyntopo: bool = False):
    """Start a tool that adds its modifier, then undo and redo (#28). Sculpt undo steps don't hold modifiers: undo
    must take the modifier away, staying in Sculpt Mode (with Dyntopo on too) and handing back to the tool used
    before, or with none, to the brush tool (with the brush active before, Draw in the startup file); redo brings
    the modifier and the tool back.
    The Circular Array also moves the mesh aside, which undo and redo follow."""
    yield from reset()
    if dyntopo:
        call("sculpt.dynamic_topology_toggle")
        yield 0.3
        check(cube().use_dynamic_topology_sculpting, "setup: Dyntopo didn't turn on")
    if previous:
        call("wm.tool_set_by_id", name=previous, space_type="VIEW_3D")
        yield 0.5
    else:
        sys.modules[PACKAGE + ".source.core.history"].tool_history.recent.pop("SCULPT", None)
    start = location_x()
    yield from start_tool(idname, modifier)
    added = location_x()
    yield from settled_undo()
    expected = ([], start, "SCULPT", previous or "builtin.brush")
    state = (modifier_names(), location_x(), mode(), tool())
    check(state == expected, f"undo {idname}: expected (modifiers, x, mode, tool) = {expected}, got {state}")
    if dyntopo:
        check(cube().use_dynamic_topology_sculpting, f"undo {idname}: expected Dyntopo on")
        check(STEP_OVER not in cube(), f"undo {idname}: the Hop's undo mark was left on the Cube")
    if not previous:
        check(brush() == "Draw", f"undo {idname}: expected the Draw brush, got {brush()}")
    yield from settled_redo()
    expected = ([modifier], added, "SCULPT", idname)
    state = (modifier_names(), location_x(), mode(), tool())
    check(state == expected, f"redo {idname}: expected (modifiers, x, mode, tool) = {expected}, got {state}")


def tool_linear_array_add_undo():
    yield from tool_add_undo_redo("sculpt_deck.linear_array", "Linear Array")


def tool_circular_array_add_undo():
    yield from tool_add_undo_redo("sculpt_deck.circular_array", "Circular Array")


def tool_mirror_add_undo():
    yield from tool_add_undo_redo("sculpt_deck.mirror", "Mirror")


def tool_add_undo_falls_back_to_brush():
    yield from tool_add_undo_redo("sculpt_deck.linear_array", "Linear Array", previous=None)


def hop_tool_add_undo_dyntopo():
    yield from tool_add_undo_redo("sculpt_deck.linear_array", "Linear Array", dyntopo=True)


def tool_add_two_undo_redo():
    """Two tools added in a row, both undone: each undo takes back one modifier, each redo brings back one with its
    tool. Each add's "Before Add …" step holds the same state as the step before it, which undo and redo step over
    (#26)."""
    yield from reset()
    yield from start_tool("sculpt_deck.linear_array", "Linear Array")
    call("wm.tool_set_by_id", name="sculpt_deck.circular_array", space_type="VIEW_3D")
    for _ in range(10):
        yield 0.3
        if "Circular Array" in modifier_names():
            break
    for when, step, modifiers, expected_tool in (
        ("undo 1", settled_undo, ["Linear Array"], "builtin.brush"),
        ("undo 2", settled_undo, [], "builtin.brush"),
        ("redo 1", settled_redo, ["Linear Array"], "sculpt_deck.linear_array"),
        ("redo 2", settled_redo, ["Linear Array", "Circular Array"], "sculpt_deck.circular_array"),
    ):
        yield from step()
        state = (modifier_names(), tool())
        check(state == (modifiers, expected_tool), f"{when}: expected (modifiers, tool) = "
              f"{(modifiers, expected_tool)}, got {state}")


def hop_array_apply_dyntopo_undo_add():
    """Two undos after Apply Array under Dyntopo take back the apply, then the add, with Dyntopo still on"""
    yield from add_and_apply_array(dyntopo=True)
    yield from settled_undo()
    check_dyntopo_state("undo Apply Array", ["Linear Array"], 2.0, dyntopo=True)
    yield from settled_undo()
    check_dyntopo_state("undo Add Linear Array", [], 2.0, dyntopo=True)


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
    """Undo and redo bring back both the geometry and the voxel size. The press leaves one extra step, its Scene
    Checkpoint, which undo steps over: after a mask, the first undo undoes the press, and the second the mask"""
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
    yield from settled_undo()
    check(mask_full() and voxel_size() == 0.2, f"undo Voxel Density Down: expected the mask and voxel size 0.2 "
          f"kept, got mask {mask_values()[:4]}..., size {voxel_size()}")
    yield from settled_undo()
    check(not mask_full(), "second undo after Voxel Density Down: expected the mask undone")


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


def each_step(label: str, state, states: list):
    """With `states` the state after each action, oldest first, and the last one now: each undo goes back one
    action and each redo forward one, none landing on a Scene Checkpoint, which looks the same as the step before
    it (#26)"""
    check(state() == states[-1], f"{label}: expected {states[-1]}, got {state()}")
    for index in range(len(states) - 2, -1, -1):
        yield from settled_undo()
        check(state() == states[index], f"{label}, undo {len(states) - 1 - index}: expected {states[index]}, "
              f"got {state()}")
    for index in range(1, len(states)):
        yield from settled_redo()
        check(state() == states[index], f"{label}, redo {index}: expected {states[index]}, got {state()}")


def checkpoint_local_transform_steps():
    yield from reset()
    for _ in range(2):
        call("sculpt_deck.local_transform", mode="MOVE", axis="X", distance=1.0)
        yield 0.5
    yield from each_step("two moves", lambda: (location_x(), mode()),
                         [(0.0, "SCULPT"), (1.0, "SCULPT"), (2.0, "SCULPT")])


def checkpoint_add_mesh_steps():
    yield from reset()
    for _ in range(2):
        call("sculpt_deck.add_primitive", primitive="CUBE")
        yield 1.0
    yield from each_step("two Add Mesh", lambda: (len(meshes()), mode()),
                         [(1, "SCULPT"), (2, "SCULPT"), (3, "SCULPT")])


def checkpoint_multires_steps():
    yield from multires_cube()
    for _ in range(2):
        call("sculpt_deck.decrement_multires")
        yield 0.5
    yield from each_step("two Multires Level Down", lambda: (multires_levels(), mode()),
                         [((2, 2), "SCULPT"), ((1, 2), "SCULPT"), ((0, 2), "SCULPT")])


def checkpoint_density_steps():
    yield from remeshed_cube()
    for _ in range(2):
        call("sculpt_deck.density_up")
        yield 0.5
    yield from each_step("two Voxel Density Up", lambda: (voxel_size(), mode()),
                         [(0.1, "SCULPT"), (0.08, "SCULPT"), (0.064, "SCULPT")])


def checkpoint_apply_scale_steps():
    yield from stretched_cube()
    call("sculpt_deck.local_transform", mode="MOVE", axis="X", distance=1.0)
    yield 0.5
    call("sculpt_deck.apply_object_scale")
    yield 0.5
    yield from each_step("move, Apply Scale", lambda: (location_x(), round(cube().scale.x, 4), mode()),
                         [(0.0, 2.0, "SCULPT"), (1.0, 2.0, "SCULPT"), (1.0, 1.0, "SCULPT")])


def checkpoint_undo_reaches_stroke():
    """The issue's case: after a stroke and an action storing a Scene Checkpoint, the first undo takes back the
    action and keeps the stroke, the second takes back the stroke"""
    yield from remeshed_cube()
    before = shape()
    yield from stroke()
    stroked = shape()
    check(not same_shape(stroked, before), "stroke: expected the Draw brush to change the Cube's shape")
    yield from remeshed_cube()
    yield from stroke()
    call("sculpt_deck.local_transform", mode="MOVE", axis="X", distance=1.0)
    yield 0.5
    yield from settled_undo()
    check(location_x() == 0.0, f"undo move: expected x = 0, got {location_x()}")
    yield from settled_undo()
    check(same_shape(shape(), before), "second undo: expected the stroke undone, the shape differs")
    check(mode() == "SCULPT", f"second undo: expected Sculpt Mode, got {mode()}")


def checkpoint_edit_mode_steps():
    """Detours in Edit Mode store no Scene Checkpoint, which there would be an Edit step undo can't step over: each
    undo takes back one Add Mesh (#26, #33)"""
    yield from reset()
    call("object.mode_set", mode="EDIT")
    yield 0.3
    for _ in range(2):
        call("sculpt_deck.add_primitive", primitive="CUBE")
        yield 1.0
    yield from each_step("two Add Mesh in Edit Mode", lambda: (len(meshes()), mode()),
                         [(1, "EDIT_MESH"), (2, "EDIT_MESH"), (3, "EDIT_MESH")])


def edit_mode_detours():
    """Detours in Edit Mode, each undone, redone, then adjusted and undone (#33). Delete of the last mesh runs Add
    Mesh inside it, with no checkpoint of its own."""

    def state():
        objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        return len(objects), sum(len(obj.data.vertices) for obj in objects), mode()

    for label, idname, extra in (
        ("Duplicate", "sculpt_deck.duplicate_object", 0),
        ("Delete", "sculpt_deck.delete_object", 1),
        ("Delete the last mesh", "sculpt_deck.delete_object", 0),
        ("Join", "sculpt_deck.join_selected", 1),
        ("Fuse", "sculpt_deck.fuse_selected", 1),
    ):
        for adjust in (False, True):
            yield from reset(extra_cubes=extra)
            if extra:
                bpy.context.scene.objects["Cube.001"].select_set(True)
            call("object.mode_set", mode="EDIT")
            yield 0.3
            before = state()
            call(idname)
            yield 1.0
            if adjust:
                yield adjust_last()
                yield 1.0
            after = state()
            name = f"{label} in Edit Mode{' adjusted' if adjust else ''}"
            check(after != before and after[2] == "EDIT_MESH", f"{name}: expected a change, staying in Edit Mode, "
                  f"got {before} -> {after}")
            yield from each_step(name, state, [before, after])


def edit_mode_object_actions_unavailable():
    """Actions that change objects (transforms, modifiers) aren't offered in Edit Mode, whose undo steps hold only
    the mesh: undo and redo would leave the change in place (#33). They're still offered in Object Mode, Sculpt
    Mode and the paint modes, where undo takes them back."""
    yield from reset()
    yield from start_tool("sculpt_deck.circular_array", "Circular Array")
    call("wm.tool_set_by_id", name="builtin.brush", space_type="VIEW_3D")
    yield 0.5
    call("wm.tool_set_by_id", name="sculpt_deck.mirror", space_type="VIEW_3D")
    for _ in range(10):
        yield 0.3
        if "Mirror" in modifier_names():
            break
    check(modifier_names() == ["Circular Array", "Mirror"], f"setup: expected an array and a mirror, got "
          f"{modifier_names()}")
    call("wm.tool_set_by_id", name="builtin.brush", space_type="VIEW_3D")
    yield 0.5
    actions = ("local_transform", "apply_object_scale", "array_apply", "array_remove", "array_axis", "array_edit",
               "mirror_apply", "mirror_remove", "increment_multires", "decrement_multires")
    for target, offered in (("EDIT", False), ("VERTEX_PAINT", True), ("OBJECT", True), ("SCULPT", True)):
        call("object.mode_set", mode=target)
        yield 0.5
        with override():
            polls = {name: getattr(bpy.ops.sculpt_deck, name).poll() for name in actions}
        wrong = sorted(name for name, poll in polls.items() if poll != offered)
        check(not wrong, f"{target}: expected {'all' if offered else 'none'} of these offered, wrong for {wrong}")


def checkpoint_failed_action():
    """An action that fails after storing its Scene Checkpoint (Multires Level Down at level 0, with nothing to
    rebuild) leaves the checkpoint as its one step. The Sculpt steps after it mustn't bring its mark back (undoing
    to a Sculpt step keeps the mark of the last whole scene step loaded): undoing a move after a mask takes back
    only the move"""
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
    call("sculpt_deck.mask_invert")
    yield 0.5
    check(mask_full(), "Invert Mask: expected the mask full")
    call("sculpt_deck.local_transform", mode="MOVE", axis="X", distance=1.0)
    yield 0.5
    yield from settled_undo()
    check((location_x(), mask_full()) == (0.0, True), f"undo move: expected x = 0 and the mask kept, got x = "
          f"{location_x()}, mask {mask_values()[:4]}...")
    yield from settled_undo()
    check(not mask_full(), "second undo: expected the mask undone")


def checkpoint_adjust_last():
    """Adjust Last Operation undoes onto the move's checkpoint and moves again: the undo that would step over the
    checkpoint mustn't run, and each undo afterwards still takes back one move"""
    yield from reset()
    for _ in range(2):
        call("sculpt_deck.local_transform", mode="MOVE", axis="X", distance=1.0)
        yield 0.5
    yield adjust_last(distance=0.5)
    yield from settle()
    yield from each_step("two moves, the last adjusted", lambda: (location_x(), mode()),
                         [(0.0, "SCULPT"), (1.0, "SCULPT"), (1.5, "SCULPT")])


def checkpoint_history_jump():
    """Jumping in the Undo History list onto a Scene Checkpoint steps over it too: back onto it lands on the step
    before, forward onto it on the action"""
    yield from reset()
    for _ in range(2):
        call("sculpt_deck.local_transform", mode="MOVE", axis="X", distance=1.0)
        yield 0.5
    # the indexes (the runner prints the history on failure): 0 Original, 1 Sculpt Mode, 2 Before Local Transform,
    # 3 Local Transform, 4 Before Local Transform, 5 Local Transform
    for item, expected in ((4, 1.0), (2, 0.0), (4, 2.0)):
        with override():
            bpy.ops.ed.undo_history(item=item)
        yield from settle()
        check(location_x() == expected, f"jump to undo step {item}: expected x = {expected}, got {location_x()}")
        check(STEP_OVER not in cube(), f"jump to undo step {item}: the checkpoint's mark was left on the Cube")


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
    combine_join_applies_others_modifiers,
    combine_join_keeps_matching_modifiers,
    combine_join_differing_modifiers,
    combine_join_asks,
    combine_join_circular_scaled,
    combine_join_circular_sheared,
    combine_join_asks_preselects_possible,
    combine_fuse_applies_modifiers,
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
    tool_linear_array_add_undo,
    tool_circular_array_add_undo,
    tool_mirror_add_undo,
    tool_add_undo_falls_back_to_brush,
    tool_add_two_undo_redo,
    hop_tool_add_undo_dyntopo,
    hop_array_apply_dyntopo_undo_add,
    pen_hold_momentary_brush,
    resolution_density_up,
    resolution_density_up_undo_voxel_size,
    resolution_density_down_undo,
    resolution_multires_undo,
    resolution_multires_down_fails,
    resolution_multires_undo_keeps_stroke,
    resolution_density_undo_keeps_stroke,
    checkpoint_local_transform_steps,
    checkpoint_add_mesh_steps,
    checkpoint_multires_steps,
    checkpoint_density_steps,
    checkpoint_apply_scale_steps,
    checkpoint_undo_reaches_stroke,
    checkpoint_failed_action,
    checkpoint_adjust_last,
    checkpoint_edit_mode_steps,
    edit_mode_detours,
    edit_mode_object_actions_unavailable,
    checkpoint_history_jump,
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
