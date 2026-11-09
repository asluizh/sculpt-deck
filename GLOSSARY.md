# Sculpt Deck

A Blender add-on for sculpting with only a pen tablet and touch, with no keyboard: everything that normally needs a shortcut, a modifier key or the Properties editor can be reached from the viewport.

## Modes and undo

**Detour**:
A trip through Object Mode that an action makes when Blender only allows it there, ending back in the mode the user started in, with undo returning there too.
_Avoid_: mode switch, round trip, mode bridge

**Hop**:
A brief switch to another mode and back within one action, which the user never sees in the undo history. Unlike a Detour, it adds or removes no objects, so it needs no Scene Checkpoint.
_Avoid_: mode switch, temporary mode

**Scene Checkpoint**:
A whole scene undo step stored right before an action whose own undo step would not hold everything it changes (objects added or removed, object transforms in Sculpt Mode). Each one appears as an extra "Before …" step in the undo history, which undo and redo step over.
_Avoid_: scene undo, before step

## Actions

**Action**:
One thing the user can run from the viewport: an operator, a menu, a pie, an asset shelf or a tool.
_Avoid_: command, button, function

**Action Surface**:
A place in the viewport where the user assigns Actions and fires them: the Widget, the Action Pie, the pen buttons, and the double click and right click lists.
_Avoid_: binding, slot, button (each of these is one surface's detail)

**Gesture**:
One way of firing from an Action Surface: a Widget button, an Action Pie slot, a pen click, a pen hold, a double click or a right click.

**Action List**:
The choices one Gesture offers in one mode, built from that mode's Actions by what the Gesture can do, plus the surface's own extras (such as Blender Default or Nothing on a pen button). A mode has several.
_Avoid_: action catalog, menu

**Momentary**:
Engaged only while a button is held, and put back as it was on release: a brush, a tool or Invert Brush. A pen hold offers only Momentary choices.
_Avoid_: temporary, hold action

**Resolution Change**:
An Action that changes how dense a mesh is (remesh, Multires levels, subdivide, Dyntopo, Fuse). Kept off pen buttons, which are easy to press by accident.
_Avoid_: topology action, remesh action
