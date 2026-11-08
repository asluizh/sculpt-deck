"""Scene Checkpoint: a whole scene undo step stored right before an action whose own undo step would not hold
everything it changes. See GLOSSARY.md."""

import bpy


def store_scene_checkpoint(context, message: str):
    """Store a Scene Checkpoint named `message` ("Before …"), even in Sculpt or Edit Mode.

    Sculpt undo steps can't add or remove objects, and don't hold where objects are. An operator that adds or
    removes them, run in Sculpt Mode, would leave its objects behind on undo, and every redo from Adjust Last
    Operation would add more; one that moves them would leave them moved. Blender picks the step type from the
    active object, so hiding it gives a full scene step to undo back to. (Edit Mode still gets an edit step, which
    works: undoing to one also restores the scene from the last full scene step.) In Object Mode every step is a
    whole scene step already, so none is stored.
    """
    if context.mode == "OBJECT":
        return
    with context.temp_override(active_object=None, edit_object=None, object=None):
        bpy.ops.ed.undo_push(message=message)
