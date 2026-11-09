"""The Hop: a brief switch to another mode and back within one action (see GLOSSARY.md).

Unlike a Detour, a Hop adds or removes no objects, so it stores no Scene Checkpoint, and the mode switches push no
undo steps of their own: the action's own undo step is the only one the user sees, saved in the mode the action
started and ended in.

The exception is leaving Sculpt Mode with Dyntopo on. Blender then pushes its own "Dynamic topology disable" steps
(a Sculpt step, which undo skips, and a whole scene step), and turning Dyntopo back on pushes a "Dynamic topology
enable" one, even from Python; nothing from Python can skip or remove them. For a Hop that is the whole action
(`whole_action`), the Hop marks the whole scene steps it stores, and after an undo or redo that lands on one of its
steps, core/step_over.py undoes or redoes again until it's past them. One undo or redo then takes the whole action
back or forward, while the Undo History list still shows the extra steps. See PROJECT.md, undo notes.

The switches act on the active object of the current context (`bpy.ops`), so `context` should be that one.
"""

from contextlib import contextmanager

import bpy

# the marks of the whole scene steps a Hop under Dyntopo stores (core/step_over.py):
# - BEFORE: Dyntopo turned off before the Hop, which the Sculpt step after it turns on again: undo returns to that
#   Sculpt step, since undoing to a whole scene step turns Dyntopo off in Blender 5.2
# - START: the Hop leaving Sculpt Mode, with everything as before the action
# - INSIDE: back in Sculpt Mode, after the action's changes, before its own step
from .step_over import BEFORE, INSIDE, START, STEP_OVER


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
        obj[STEP_OVER] = BEFORE
        toggle_dyntopo()
        del obj[STEP_OVER]
        toggle_dyntopo()
        obj[STEP_OVER] = START
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
            obj[STEP_OVER] = INSIDE
            push_step("Back to Sculpt Mode")
        finally:
            obj.pop(STEP_OVER, None)
