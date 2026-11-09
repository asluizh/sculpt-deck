"""Stepping over undo steps the user shouldn't land on: after an undo or redo that lands on a marked step, undo or
redo again until past it, so each undo or redo takes back or redoes something the user can see.

The steps are whole scene steps an action stores besides its own: a Scene Checkpoint ("Before …", which looks the
same as the step before it), and the steps a Hop under Dyntopo stores (core/hop.py). Each one is marked with a
custom property on the active object, saved in the step and dropped from the object right after, so undo or redo
loading the step brings the mark back. The Undo History list still shows the steps. See PROJECT.md, undo notes.
"""

import bpy
from bpy.app.handlers import persistent

# custom property marking a step to step over, saved in the step, and never left on the object afterwards:
# - CHECKPOINT: a Scene Checkpoint, with everything as in the step before it
# - BEFORE, START, INSIDE: the steps a Hop under Dyntopo stores (core/hop.py, dyntopo_hop)
STEP_OVER = "sculpt_deck_step_over"
CHECKPOINT = "CHECKPOINT"
BEFORE, START, INSIDE = "BEFORE", "START", "INSIDE"


def active_object():
    view_layer = bpy.context.view_layer
    return view_layer.objects.active if view_layer else None


def drop_mark():
    obj = active_object()
    if obj is not None:
        obj.pop(STEP_OVER, None)


def steps_past(direction: str) -> int:
    """After an undo or redo, how many more to make in the same direction to get past the marked steps: none when
    it didn't land on one of them.

    A Scene Checkpoint is followed by the action's own step, and comes right after the step before the action: one
    more either way. BEFORE leads to the Sculpt step where undo of a Hop's action returns, a copy of the step
    before the Hop with Dyntopo on: undo from there goes on past the step before the Hop as from it, and redo past
    that Sculpt step on to the action. The step undo or redo goes on to may be a Sculpt step, which keeps the
    object's properties as they are, so the mark is dropped first, except where the next step is a whole scene
    step without it (redo from START, undo or redo from INSIDE)."""
    obj = active_object()
    if obj is None or STEP_OVER not in obj:
        return 0
    mark = obj[STEP_OVER]
    if mark in {CHECKPOINT, BEFORE} or (direction == "undo" and mark == START):
        del obj[STEP_OVER]
    return 2 if mark == BEFORE else 1


# bumped by every undo, redo and action that stores marked steps, so extra undos or redos scheduled before one of
# them don't run
generation = 0
# extra undos or redos waiting for their timer
scheduled = 0


def cancel_step_over():
    """Called as an action storing marked steps starts: Adjust Last Operation runs it again right after its undo,
    which may have landed on a marked step. The extra undo or redo waiting then mustn't run, and the action's steps
    mustn't keep the mark."""
    global generation
    generation += 1
    drop_mark()


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
            # stuck on a marked step: at least the next steps stored mustn't keep its mark
            drop_mark()
        return None

    if window is None:
        drop_mark()
        return
    scheduled += 1
    bpy.app.timers.register(run, first_interval=0.0)


@persistent
def new_step_taken(*_):
    """Before any undo or redo, the extra ones still waiting are outdated"""
    global generation
    generation += 1


@persistent
def step_over_undo(*_):
    """After undo: past the marked steps, on to the step before the action"""
    times = steps_past("undo")
    if times:
        step_again("undo", times)


@persistent
def step_over_redo(*_):
    """After redo: past the marked steps, on to the action's own step"""
    times = steps_past("redo")
    if times:
        step_again("redo", times)


@persistent
def clear_marks(*_):
    """A file saved while on a marked step keeps its mark: drop it, so steps stored later don't carry it"""
    for obj in bpy.data.objects:
        if STEP_OVER in obj:
            del obj[STEP_OVER]


handlers = (
    (bpy.app.handlers.undo_pre, new_step_taken),
    (bpy.app.handlers.redo_pre, new_step_taken),
    (bpy.app.handlers.undo_post, step_over_undo),
    (bpy.app.handlers.redo_post, step_over_redo),
    (bpy.app.handlers.load_post, clear_marks),
)


def register():
    for handler_list, handler in handlers:
        handler_list.append(handler)


def unregister():
    for handler_list, handler in handlers:
        if handler in handler_list:
            handler_list.remove(handler)
