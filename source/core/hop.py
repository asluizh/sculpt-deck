"""The Hop: a brief switch to another mode and back within one action (see GLOSSARY.md).

Unlike a Detour, a Hop adds or removes no objects, so it stores no Scene Checkpoint, and the mode switches push no
undo steps of their own: the action's own undo step is the only one the user sees, saved in the mode the action
started and ended in.

The exception is leaving Sculpt Mode with Dyntopo on. Blender then pushes its own "Dynamic topology disable" steps
(a Sculpt step, which undo skips, and a whole scene step), and turning Dyntopo back on pushes a "Dynamic topology
enable" one, even from Python; nothing from Python can skip or remove them. For a Hop that is the whole action
(`whole_action`), the Hop marks the whole scene steps it stores, and after an undo or redo that lands on one of its
steps, `step_over_hop_undo` and `step_over_hop_redo` undo or redo again until it's past them. One undo or redo then
takes the whole action back or forward, while the Undo History list still shows the extra steps. See PROJECT.md,
undo notes.

The switches act on the active object of the current context (`bpy.ops`), so `context` should be that one.
"""

from contextlib import contextmanager

import bpy
from bpy.app.handlers import persistent

# custom property marking the whole scene steps a Hop under Dyntopo stores, saved in them, and never left on the
# object afterwards:
# - BEFORE: Dyntopo turned off before the Hop, which the Sculpt step after it turns on again: undo returns to that
#   Sculpt step, since undoing to a whole scene step turns Dyntopo off in Blender 5.2
# - START: the Hop leaving Sculpt Mode, with everything as before the action
# - INSIDE: back in Sculpt Mode, after the action's changes, before its own step
HOP_STEP = "sculpt_deck_hop_step"
BEFORE, START, INSIDE = "BEFORE", "START", "INSIDE"


def set_mode(mode: str):
    # called from Python without an undo step, so nothing shows in the undo history
    bpy.ops.object.mode_set("EXEC_DEFAULT", False, mode=mode)


@contextmanager
def hop(context, mode: str, whole_action: bool = False):
    """Run the body in the given object mode (`Object.mode`: "OBJECT", "EDIT", "SCULPT", ...) on the active object,
    then switch back to the mode it was in, even when the body raises. Does nothing when already in that mode.

    `whole_action`: the body makes all of the action's changes. From Sculpt Mode with Dyntopo on, Dyntopo is then on
    again afterwards, and one undo returns to before the action with Dyntopo still on (see the module docstring).
    Without it, Blender's Dyntopo steps show in the undo history as they are."""
    obj = context.active_object
    start = obj.mode if obj is not None else "OBJECT"
    if start == mode:
        yield
        return
    if whole_action and start == "SCULPT" and obj.use_dynamic_topology_sculpting:
        with dyntopo_hop(obj, mode):
            yield
        return
    set_mode(mode)
    try:
        yield
    finally:
        set_mode(start)


def toggle_dyntopo():
    # pushes Blender's "Dynamic topology disable/enable" steps, even from Python
    bpy.ops.sculpt.dynamic_topology_toggle("EXEC_DEFAULT", False)


def push_step(message: str):
    bpy.ops.ed.undo_push("EXEC_DEFAULT", False, message=message)


@contextmanager
def dyntopo_hop(obj, mode: str):
    """The Hop from Sculpt Mode with Dyntopo on, storing and marking these steps before the action's own one:

    - "Dynamic topology disable" (Sculpt, skipped by undo) and "Dynamic topology disable" (whole scene, BEFORE)
    - "Dynamic topology enable" (Sculpt): the state before the action, with Dyntopo on, where undo returns
    - "Dynamic topology disable" (Sculpt, skipped) and "Dynamic topology disable" (whole scene, START) as it
      leaves Sculpt Mode
    - "Dynamic topology enable" (Sculpt) as Dyntopo goes back on, and "Back to Sculpt Mode" (whole scene, INSIDE),
      which only the step after it in the undo history needs: undoing to that Sculpt step keeps the mark of the
      whole scene step loaded last
    """
    try:
        obj[HOP_STEP] = BEFORE
        toggle_dyntopo()
        del obj[HOP_STEP]
        toggle_dyntopo()
        obj[HOP_STEP] = START
        set_mode(mode)
        yield
    finally:
        try:
            if obj.mode != "SCULPT":
                set_mode("SCULPT")
                if obj.use_dynamic_topology_sculpting:
                    # entering Sculpt Mode turned it back on, and left its "Dynamic topology enable" step to be
                    # pushed
                    push_step("Dynamic topology enable")
            if not obj.use_dynamic_topology_sculpting:
                # a mesh the body replaced (by applying a modifier) doesn't keep Dyntopo on
                toggle_dyntopo()
            obj[HOP_STEP] = INSIDE
            push_step("Back to Sculpt Mode")
        finally:
            obj.pop(HOP_STEP, None)


def active_object():
    view_layer = bpy.context.view_layer
    return view_layer.objects.active if view_layer else None


def steps_past_hop(direction: str) -> int:
    """After an undo or redo, how many more to make in the same direction to get past the steps a Hop under Dyntopo
    stored: none when it didn't land on one of them.

    BEFORE leads to the Sculpt step where undo of the action returns, a copy of the step before the Hop with
    Dyntopo on: undo from there goes on past the step before the Hop as from it, and redo past that Sculpt step on
    to the action. Undo from BEFORE or START, and redo from BEFORE, land on a Sculpt step, which keeps the object's
    properties as they are, so the mark is dropped first."""
    obj = active_object()
    if obj is None or HOP_STEP not in obj:
        return 0
    mark = obj[HOP_STEP]
    if mark == BEFORE or (direction == "undo" and mark == START):
        del obj[HOP_STEP]
    return 2 if mark == BEFORE else 1


# bumped by every undo, redo and Hop action, so extra undos or redos scheduled before one of them don't run
generation = 0
# extra undos or redos waiting for their timer
scheduled = 0


def cancel_step_over():
    """Called as a Hop's action starts: Adjust Last Operation runs it again right after its undo, which may have
    landed on a Hop's step. The extra undo or redo waiting then mustn't run, and the action's step mustn't keep the
    mark."""
    global generation
    generation += 1
    obj = active_object()
    if obj is not None:
        obj.pop(HOP_STEP, None)


def step_again(direction: str, times: int):
    """Undo or redo `times` more, right after the current undo or redo has finished"""
    global scheduled
    window = bpy.context.window or next(iter(bpy.context.window_manager.windows), None)
    expected = generation

    def run():
        global scheduled
        scheduled -= 1
        if expected != generation:
            return None
        try:
            area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), None)
            with bpy.context.temp_override(window=window, area=area):
                for _ in range(times):
                    getattr(bpy.ops.ed, direction)()
        except (AttributeError, RuntimeError, ReferenceError, TypeError):
            # stuck on a Hop's step: at least the next steps stored mustn't keep its mark
            obj = active_object()
            if obj is not None:
                obj.pop(HOP_STEP, None)
        return None

    if window is None:
        obj = active_object()
        if obj is not None:
            obj.pop(HOP_STEP, None)
        return
    scheduled += 1
    bpy.app.timers.register(run, first_interval=0.0)


@persistent
def new_step_taken(*_):
    """Before any undo or redo, the extra ones still waiting are outdated"""
    global generation
    generation += 1


@persistent
def step_over_hop_undo(*_):
    """After undo: past the steps a Hop under Dyntopo stored, on to the Sculpt step with Dyntopo on before them"""
    times = steps_past_hop("undo")
    if times:
        step_again("undo", times)


@persistent
def step_over_hop_redo(*_):
    """After redo: past the steps a Hop under Dyntopo stored, on to the action's own step"""
    times = steps_past_hop("redo")
    if times:
        step_again("redo", times)


@persistent
def clear_marks(*_):
    """A file saved while on a Hop's step keeps its mark: drop it, so steps stored later don't carry it"""
    for obj in bpy.data.objects:
        if HOP_STEP in obj:
            del obj[HOP_STEP]


handlers = (
    (bpy.app.handlers.undo_pre, new_step_taken),
    (bpy.app.handlers.redo_pre, new_step_taken),
    (bpy.app.handlers.undo_post, step_over_hop_undo),
    (bpy.app.handlers.redo_post, step_over_hop_redo),
    (bpy.app.handlers.load_post, clear_marks),
)


def register():
    for handler_list, handler in handlers:
        handler_list.append(handler)


def unregister():
    for handler_list, handler in handlers:
        if handler in handler_list:
            handler_list.remove(handler)
