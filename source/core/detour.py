"""Detour: a trip through Object Mode that an action makes when Blender only allows it there, ending back in the
mode the user started in, with undo returning there too. See GLOSSARY.md."""

import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, StringProperty

from ..utils.constants import FINISHED, object_modes
from .checkpoint import store_scene_checkpoint

# custom property marking the mode an object returns to: saved in the undo step, cleared once back in that mode
RETURN_MODE = "sculpt_deck_return_mode"


def enter_mode(window, area, mode: str, tool: str = ""):
    """Switch the active object to `mode` right after the current operator or undo step"""

    def run():
        try:
            with bpy.context.temp_override(window=window, area=area):
                obj = bpy.context.view_layer.objects.active
                if obj is None:
                    return None
                if bpy.context.mode == "OBJECT":
                    bpy.ops.object.mode_set(mode=mode)
                if RETURN_MODE in obj:
                    del obj[RETURN_MODE]
                if tool:
                    bpy.ops.wm.tool_set_by_id(name=tool, space_type="VIEW_3D")
        except (RuntimeError, ReferenceError, TypeError):
            pass
        return None

    bpy.app.timers.register(run, first_interval=0.0)


def finish_in_mode(context, mode: str, tool: str = ""):
    """Return to `mode` once the calling operator has finished in Object Mode.

    Ending in Object Mode makes the operator's own undo step a whole scene step, so redoing it brings its objects
    back. The mode switch afterwards adds no undo step of its own. That step is saved in Object Mode, so the object
    is marked with its mode, and returns to it whenever the step is undone or redone to.
    """
    if mode == "OBJECT":
        return
    obj = context.view_layer.objects.active
    if obj is not None:
        obj[RETURN_MODE] = mode
    enter_mode(context.window, context.area, mode, tool)


@persistent
def restore_mode(*_):
    """After undo or redo: put an object marked by finish_in_mode back in its mode"""
    context = bpy.context
    obj = context.view_layer.objects.active if context.view_layer else None
    if obj is None or RETURN_MODE not in obj:
        return
    # the mode may still change while the undo finishes, so the timer checks it
    window = context.window or next(iter(context.window_manager.windows), None)
    area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), None) if window else None
    enter_mode(window, area, obj[RETURN_MODE])


class Detour:
    """Base for operators that must go through Object Mode because they add or remove objects.

    `execute` runs every step, in order: it records the mode it starts from, stores the Scene Checkpoint
    ("Before <label>"), switches to Object Mode, runs `object_mode_work`, and ends back in the starting mode, marking
    the object so undo and redo return there too. A subclass supplies only `object_mode_work` (and, if it hands the
    user a tool afterwards, `return_tool`); it can't override `execute`.

    The starting mode is recorded once, on the first run, and kept when Blender runs the operator again (Adjust
    Last Operation undoes to the step before it, in Object Mode, and repeats it with the same properties). Each
    Detour leaves exactly one "Before …" step: the checkpoint is stored once too.
    """

    # the mode the Detour started from and ends in, recorded on the first run; a caller may preset it
    start_mode: StringProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore
    # store the Scene Checkpoint first; turned off once stored, so repeats don't stack more, and by a caller that
    # already stored one (such as another Detour running this one)
    checkpoint: BoolProperty(default=True, options={"HIDDEN", "SKIP_SAVE"})  # type: ignore

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # also catches a mixin listed before Detour
        for base in cls.__mro__:
            if base is Detour:
                break
            if "execute" in base.__dict__:
                raise TypeError(f"{cls.__name__} is a Detour: supply object_mode_work, not execute")

    def execute(self, context):
        if not self.start_mode:
            self.start_mode = object_modes[context.mode]
        if self.checkpoint:
            store_scene_checkpoint(context, f"Before {self.bl_label}")
            self.checkpoint = False
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        try:
            self.object_mode_work(context)
        finally:
            # even when the work fails: the user is put back in their mode, and the checkpoint stays to undo to
            finish_in_mode(context, self.start_mode, self.return_tool())
        return FINISHED

    def object_mode_work(self, context):
        """What the action does, run in Object Mode"""
        raise NotImplementedError

    def return_tool(self) -> str:
        """The tool to switch to once back in the starting mode, or "" to keep the current one"""
        return ""


mode_handlers = (bpy.app.handlers.undo_post, bpy.app.handlers.redo_post)


def register():
    for handlers in mode_handlers:
        handlers.append(restore_mode)


def unregister():
    for handlers in mode_handlers:
        if restore_mode in handlers:
            handlers.remove(restore_mode)
