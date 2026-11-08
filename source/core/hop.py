"""The Hop: a brief switch to another mode and back within one action (see GLOSSARY.md).

Unlike a Detour, a Hop adds or removes no objects, so it stores no Scene Checkpoint, and the mode switches push no
undo steps of their own: the action's own undo step is the only one the user sees, saved in the mode the action
started and ended in.
"""

from contextlib import contextmanager

import bpy


def set_mode(mode: str):
    # called from Python without an undo step, so nothing shows in the undo history
    bpy.ops.object.mode_set("EXEC_DEFAULT", False, mode=mode)


@contextmanager
def hop(context, mode: str):
    """Run the body in the given object mode (`Object.mode`: "OBJECT", "EDIT", "SCULPT", ...) on the active object,
    then switch back to the mode it was in, even when the body raises. Does nothing when already in that mode."""
    obj = context.active_object
    start = obj.mode if obj is not None else "OBJECT"
    if start == mode:
        yield
        return
    set_mode(mode)
    try:
        yield
    finally:
        set_mode(start)
