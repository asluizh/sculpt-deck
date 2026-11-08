# Sculpt Deck: project notes

Working notes for Sculpt Deck, which started as a fork of [Touchview](https://github.com/nendotools/touchview) (see [ADR 0001](docs/adr/0001-independent-from-touchview.md)): what it is for, what it covers, how the code is laid out and where the work stands. The user-facing documentation is the [README](README.md); domain terms are in the [glossary](GLOSSARY.md).

## Objective

Use Blender without a keyboard, with a pen tablet and touch, with the main focus on **sculpting**. Anything that normally needs a shortcut, a modifier key or a trip to a properties tab should be reachable from the viewport: by touch, from the on-screen widget, from the action pie or from a pen button.

Guiding principles:

- **Stay in the current mode.** Actions that Blender only offers in Object Mode (adding meshes, joining, applying scale, applying modifiers) switch modes behind the scenes, or avoid switching entirely, and return the user to where they were.
- **One workspace.** Settings live in tool headers, the sidebar and the action list, not in the Properties editor. Example: arrays are added, edited and applied without the modifier tab.
- **Blender's own UI where possible.** Toolbar tools with header settings, gizmos with tooltips, Adjust Last Operation and undo steps, instead of separate panels.
- **Pen, touch and mouse each keep their role.** Touch moves the view, the pen draws, and pen buttons are bound separately from mouse buttons.

## Scope

In scope:

- Viewport navigation by touch: pan, rotate and zoom regions, plus tap, double tap and long press on objects.
- An on-screen widget with up to 12 buttons per mode, an 8-slot action pie per mode, and pen side-button bindings (click and hold). All three draw from one shared action list.
- A sculpt workflow without leaving Sculpt Mode:
  - adding primitives;
  - duplicating and deleting meshes;
  - joining and fusing meshes (union and difference);
  - transforming whole objects along their own axes;
  - linear and circular arrays;
  - brush switching and inversion;
  - remesh and Multires controls.
- Blender 5.2 and newer.

Out of scope for now:

- Edit Mode modeling tools beyond what the action list exposes.
- Curve arrays, deferred until linear and circular arrays have settled.
- Keyboard shortcut customization: the add-on works alongside Blender's keymap and doesn't replace it.

## Structure

```
__init__.py              add-on entry point (bl_info, register)
preferences.py           add-on preferences, saved to and loaded from preferences.json
blender_manifest.toml    extension manifest (version, minimum Blender, build excludes)
bundle.sh                builds bin/sculpt_deck.zip
icons/                   toolbar icons (triangle .dat files, see dev/)
dev/                     development tools, not shipped
  pen_event_probe.py       logs pen/mouse/touch events, run from the Text Editor
  make_tool_icon.py        builds the Local Transform icon from Blender's Transform icon
  make_array_icons.py      builds the Linear/Circular Array icons
  make_mirror_icon.py      builds the Mirror icon
  tests/                   smoke.sh: headless register check (expected output in smoke_expected.txt)
                           scenarios.sh: UI scenarios (undo, Adjust Last Operation, pen buttons, clicks) on headless weston
source/
  core/                  shared mechanisms every part builds on (see the glossary)
    actions.py             the Action catalog (each Action's modes, Momentary, Resolution Change) and the rules
                           that build every Gesture's Action List from it
    checkpoint.py          Scene Checkpoint: a whole scene undo step in Sculpt and Edit Mode
    detour.py              Detour: base for operators that go through Object Mode, return mode on undo and redo
    hop.py                 Hop: a context manager that switches to a mode, runs the body and switches back
  features/              sculpt workflow features, one sub-package each (PARTS: Mirror before the arrays, for toolbar order)
    objects/               object actions, each a Detour
      add_mesh.py            Add Mesh operator and menu
      duplicate_delete.py    Duplicate and Delete
      combine.py             Join Selected, Fuse (Union) and Fuse (Difference)
    array/                 Linear and Circular Array
      operators.py           node groups, settings (Scene.sculpt_deck_array), add/apply/remove/axis/edit operators
      tools.py               toolbar tools, headers and 3D gizmos
    mirror/                Mirror
      operators.py           node group (its inputs are the Mirror settings), apply/remove operators
      tools.py               toolbar tool, header and plane outlines
  surfaces/              Action Surfaces, each with its settings, sidebar panel and keymap entries
    pen/                   pen buttons (click and hold per mode)
      settings.py            the pen set of each mode (PropertyGroups held in the preferences' pen_sets), with the
                             right click and double click bindings
      button.py              the pen button operator (hold engages a Momentary brush or tool, put back on release),
                             BindingRunner shared with the clicks, Use Active Brush, the pen keymap entries
      panel.py               Pen Buttons sidebar panel; draws a binding for the clicks too
    clicks/                double click and right click (mouse and touch)
      action.py              the double click and right click operators and their keymap entries
      panel.py               Right Click and Double Click sidebar panels
  ops/                   operators
    actions.py             general actions: remesh, Multires, masks, brush size/strength
    touch.py               touch navigation, tap/double tap/long press on objects
    gizmo.py               widget and action pie operators
    pen.py                 Previous Brush and Invert Brush
    drag.py                shared modal drag for tool gizmos (confirm on release, tap keeps running)
    local_transform.py     Local Transform tool operator, settings, Apply Scale
  ui/                    drawing
    gizmo_group_2d.py      on-screen widget
    gizmo_2d.py, gizmo_config.py  widget button types and layout
    panel.py               sidebar panels and menus (action pie, All Actions)
    local_transform.py     Local Transform toolbar tool, header and 3D gizmos
  utils/                 shared helpers
    constants.py           enums, defaults
    actions.py             runs an Action by idname (operator, menu, pie, asset shelf, tool), tool history
    brush.py               brush history, polled every 0.25 s along with the tool history
    undo.py                push_scene_undo: the Scene Checkpoint under its old name, for Local Transform
    settings.py            default settings (add-on user folder) and per-file settings (scene property), unsaved check
    keymaps.py             keymap registration of touch navigation (the surfaces register their own)
    overlay.py             touch region overlay
    blender.py             preferences access, safe area and other UI helpers
```

How the tools fit together:

- **Local Transform** moves, rotates and scales whole objects (the active one and the other selected ones, leaving out children of those) instead of their vertices, so the origin stays with the mesh. Scale is applied to the mesh when each scale ends, so stretches never skew. The **Instances** pivot, which is the default, turns or scales each selected object and each array copy in place, the copies by turning the array settings back by the same amount. Moves and rotations follow the active object's axes, scaling follows each object's own.
- **Arrays** are Geometry Nodes modifiers built by the add-on, one node group per kind, versioned by a custom property. The real mesh stays in place and sculptable, and the copies are instances that follow it. The node trees lay out the copies as if the object's scale were already applied, so copies don't warp while a scale is being dragged.
- **Mirror** is a Geometry Nodes modifier too. Its planes are the Mirror Object's, or the world origin's when none is set (an empty Object Info gives the identity matrix), turned into the object's space with Self Object, so they stay put in the world while the mesh moves. The reflection is an instance until applied; applying realizes it with flipped faces, merges the vertices on the planes and deletes the faces lying on them.
- **Tool gizmos** start operators that share the drag handling in `ops/drag.py`. Each operator's `description()` provides the hovered gizmo's tooltip.

Development notes (Blender 5.2):

- Run `dev/tests/smoke.sh` after every change: it builds the zip, installs it into a throwaway profile in `bin/test/` (the flatpak can't see `/tmp`), enables, disables and re-enables the add-on, and fails on any error or warning, or when the registered operators, classes or Action Lists differ from `dev/tests/smoke_expected.txt`. It also checks the Action List rules (a pen hold offers only Momentary choices, no pen button or click offers a Resolution Change), that Actions added to the catalog appear on every Gesture where they fit, and that the settings survive a save and load. When a difference is intended, accept it with `--update` and commit the new expected file with the change.

- Geometry Nodes modifier inputs are read and written through `modifier.properties.inputs.<socket id>.value`, not `modifier["Socket_N"]`.
- Gizmo offsets (`matrix_offset`) are in scene units unless `use_draw_offset_scale` is set, which makes them follow the gizmo's screen size.
- Writing `matrix_world` recomputes the scale with rounding errors. Moves and rotations restore the exact scale afterwards.
- Data can't be changed while gizmos draw, so tools change data from a `bpy.app.timers` callback.
- Python edits to mesh data in Sculpt Mode, and Python operators with `UNDO`, both undo correctly. `object.transform_apply` doesn't run in Sculpt Mode, but `object.modifier_apply` does.
- Sculpt and Edit Mode undo steps can't add or remove objects. Operators that do (Add Mesh, Duplicate, Delete, Join, Fuse) are Detours (`core/detour.py`): a subclass supplies only `object_mode_work`, and the `Detour` base stores a Scene Checkpoint first (`core/checkpoint.py`, which hides the active object so Blender picks a whole scene step), finishes in Object Mode so the operator's own step is a whole scene step too, and returns to the starting mode from a timer. Those steps are saved in Object Mode, so the object carries a `sculpt_deck_return_mode` property and undo/redo handlers switch it back. The Detour records its starting mode once, in a hidden property, so a repeat from Adjust Last Operation, which can run before that mode is back, still ends there; and it stores the checkpoint once, so each Detour leaves exactly one extra "Before ..." undo step. A Detour run by another one (Delete adding a cube when no mesh is left) gets `checkpoint=False` and the caller's `start_mode`.
- Sculpt Mode undo steps don't hold object transforms (or modifier settings), so undoing a move to a Sculpt step leaves the objects moved. Outside Object Mode, Local Transform stores a Scene Checkpoint (`push_scene_undo`, re-exported from `core/checkpoint.py` by `utils/undo.py`) of the objects at their start right before its own step, when the drag is confirmed, so undo moves them back and Adjust Last Operation goes back to that state. Each move leaves that extra "Before Local Transform" step. It also stores each object's starting matrix, array vectors and mesh size (and its children's matrices) in a hidden property, and starts from them when run again.
- Operators called from Python push no undo steps, but `object.transfer_mode` still saves its "Change Active" step (with the new object still in Object Mode) and then skips the step of entering the mode, so undo lands in Object Mode. The tap calls it with `undo=True`.
- Run `dev/tests/scenarios.sh` (or `dev/tests/scenarios.sh <name> ...`) after changes to undo, modes, Detours or pen buttons. Its `adjust_last` runs `ed.undo_redo` with an undo step: called from Python without one, the repeated operator stores no step of its own and runs while still in Object Mode (`detour_repeat_from_object_mode` uses that on purpose). Real Sculpt undo steps only exist in the full UI, so it starts `weston --backend=headless --renderer=gl --xwayland` and runs Blender's flatpak on its Xwayland display with `--enable-event-simulate`, driving it from a timer under a `temp_override` of the 3D viewport. A scenario is a generator in `dev/tests/scenarios.py` that calls operators with an undo step, checks the result and yields seconds to wait; add it to `SCENARIOS`. A scenario failing because of a known bug goes in `KNOWN_FAILURES` with the reason. `window.event_simulate` can't make tablet events, so the pen scenarios make the add-on take simulated presses for pen presses (`is_pen` in `surfaces/pen/button.py`), and the click scenarios turn that back off.
- Undo can be tested in the UI with operators called from a timer as `bpy.ops.<op>("EXEC_DEFAULT", True, ...)` (the `True` pushes an undo step) and `bpy.context.window_manager.print_undo_steps()`.
- `bpy.utils.register_tool(after=...)` puts a tool at the end of the separator section holding `after`, so the order inside a section is the registration order (`ui/__init__.py`, then `features/__init__.py`).
- Popup menus opened with `wm.call_menu` run their operator buttons with `EXEC_REGION_WIN`, so operators that need `invoke` (Save's file browser, Search) fail or vanish. `draw_action` sets `operator_context = "INVOKE_REGION_WIN"`.
- Add-on `unregister()` runs when Blender quits normally, but not after a crash. Changing add-on preferences from Python or the sidebar doesn't mark Blender's preferences as unsaved.
- Headless tests run with `flatpak run --filesystem=home org.blender.Blender -b --factory-startup --python <script>`, with the add-on linked into a scripts folder through `BLENDER_USER_SCRIPTS`. Gizmos, drags and headers need testing in the UI.

## Progress

Done:

- [x] Blender 5.2 support and fixes (v4.3.0, upstream pull request #54 from the `blender-5.2` branch).
- [x] Pen button bindings for click and hold, sharing the action list; tools and brushes used temporarily while held; Invert Brush.
- [x] Configurable widget (12 buttons per mode) and action pie (8 slots per mode); All Actions popup.
- [x] Touch object workflow: tap to select or switch objects, long press to toggle selection, Add Mesh, Join, Fuse (union and difference).
- [x] Local Transform tool:
  - Global/Local axes;
  - Origin, Bounds, 3D Cursor and Instances pivots;
  - scale applied automatically;
  - per-gizmo tooltips and a uniform scale ring.
- [x] Linear and Circular Array tools:
  - they start immediately and stack;
  - count, spacing, radius, center and arc gizmos, with an arc sector and step marks while dragging;
  - X/Y/Z/View axis and Global/Local;
  - Apply and Remove hand back to the previous tool.
- [x] Arrays stay correct while a non-uniform scale is dragged and after scale is applied.
- [x] Double Click and Right Click: per-mode actions from the pen button click list, with header checkboxes.
- [x] Mirror tool: world origin planes by default (planes in world space, so moving the mesh mirrors as expected), optional Mirror Object, the mirror image as an instance until applied, merged at the planes on Apply.
- [x] Duplicate and Delete actions without leaving the current mode: Duplicate places the copy with Local Transform; Delete returns to the previously active mesh (`object_history`), or adds a rounded cube when none is left.
- [x] Default and per-file settings: Save Default Settings in the sidebar, settings stored in the .blend file when they differ, Auto-Save Defaults option.
- [x] Add Mesh: shape options (segments, subdivisions, base vertices, capsule and torus sizes), Smooth and Round Edges; Icosphere, Quad Sphere and Capsule. Undo and redo in Sculpt and Edit Mode fixed for Add Mesh, Join and Fuse.

Next:

- [ ] Curve array.
- [ ] README feature sections for Local Transform and the array tools (so far they're only in the changelog).
- [ ] Decide what an array tool does when a file is opened with it active (it currently adds an array right away).

Known limitations:

- Applying an array or mirror with Dyntopo on makes a Hop to Object Mode (Blender applies in Sculpt Mode with only a warning, and Dyntopo's own mesh then overwrites the result). Leaving and entering Sculpt Mode with Dyntopo pushes Blender's own "Dynamic topology disable/enable" undo steps, so this Hop shows in the undo history: one undo leaves the array applied, the next brings it back with Dyntopo off (#17, scenario `hop_array_apply_dyntopo_undo`).
- Arrays after a Multires modifier probably don't apply as displayed. Arrays are aimed at voxel and dynamic topology meshes.
- Blender hides generative modifiers while dynamic topology is on, so array copies may not show then.
- Brushes only act on the real mesh, not on array copies or the mirror image, until the array or mirror is applied. Sculpt symmetry mirrors in the object's space, so it only matches the Mirror tool while the object sits on the world origin's planes.
- Arrays created before node group version 2 lack the scale handling; remove and re-add them.
- After Add Mesh, Join or Fuse in Edit Mode, undoing the first edit made afterwards lands in Object Mode (Blender only leaves Edit Mode when the scene step it undoes to is already loaded, so the return mode mark isn't seen). Sculpt Mode isn't affected.
