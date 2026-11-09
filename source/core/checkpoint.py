"""Scene Checkpoint: a whole scene undo step stored right before an action whose own undo step would not hold
everything it changes. See GLOSSARY.md."""

import bpy

from .blender import active_object
from .step_over import CHECKPOINT, STEP_OVER


def store_scene_checkpoint(context, message: str):
    """Store a Scene Checkpoint named `message` ("Before …") in Sculpt Mode and the paint modes.

    Sculpt undo steps can't add or remove objects, and don't hold where objects are. An operator that adds or
    removes them, run in Sculpt Mode, would leave its objects behind on undo, and every redo from Adjust Last
    Operation would add more; one that moves them would leave them moved. Blender picks the step type from the
    active object, so hiding it gives a full scene step to undo back to.

    None is stored in Object Mode, where every step is a whole scene step already, nor in Edit Mode, where it would
    be an Edit step anyway: only Detours run there (actions that change objects aren't offered, see
    `object_data_modes`), their own step is a whole scene step saved in Object Mode, and undoing from it to the
    Edit step before restores the scene from the whole scene step before that. A checkpoint would only add a step
    that looks the same, which undo can't step over (an Edit step doesn't load the mark).

    The checkpoint looks the same as the step before it, so it's marked for undo and redo to step over
    (core/step_over.py): one undo takes the action back and lands on the step before it, one redo does it again.
    An action storing one calls `cancel_step_over` as it starts, since Adjust Last Operation runs it again right
    after undoing onto it.
    """
    if context.mode in {"OBJECT", "EDIT_MESH"}:
        return
    obj = active_object(context)
    if obj is not None:
        obj[STEP_OVER] = CHECKPOINT
    try:
        with context.temp_override(active_object=None, edit_object=None, object=None):
            bpy.ops.ed.undo_push(message=message)
    finally:
        if obj is not None:
            obj.pop(STEP_OVER, None)
