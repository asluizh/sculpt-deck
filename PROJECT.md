# Touchview: project notes

Working notes for this fork of [Touchview](https://github.com/nendotools/touchview): what it's for, what it covers, how the code is laid out and where the work stands. The user-facing documentation is the [README](README.md).

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
bundle.sh                builds bin/touchview.zip
icons/                   toolbar icons (triangle .dat files, see dev/)
dev/                     development tools, not shipped
  pen_event_probe.py       logs pen/mouse/touch events, run from the Text Editor
  make_tool_icon.py        builds the Local Transform icon from Blender's Transform icon
  make_array_icons.py      builds the Linear/Circular Array icons
source/
  ops/                   operators
    actions.py             general actions: add mesh, join/fuse, remesh, Multires, masks, brush size/strength
    touch.py               touch navigation, tap/double tap/long press on objects, double click and right click actions
    gizmo.py               widget and action pie operators
    pen.py                 pen button bindings (click and hold, temporary brushes and tools), BindingRunner shared with clicks
    drag.py                shared modal drag for tool gizmos (confirm on release, tap keeps running)
    local_transform.py     Local Transform tool operator, settings, Apply Scale
    array.py               array node groups, settings, and the add/apply/remove/axis/edit operators
  ui/                    drawing
    gizmo_group_2d.py      on-screen widget
    gizmo_2d.py, gizmo_config.py  widget button types and layout
    panel.py               sidebar panels and menus (action pie, All Actions, Add Mesh)
    local_transform.py     Local Transform toolbar tool, header and 3D gizmos
    array.py               Linear/Circular Array toolbar tools, headers and 3D gizmos
  utils/                 shared helpers
    constants.py           action lists per mode, enums, defaults
    actions.py             runs an action by idname (operator, menu, pie, asset shelf, tool), tool history
    brush.py               brush history, polled every 0.25 s along with the tool history
    settings.py            default settings (add-on user folder) and per-file settings (scene property), unsaved check
    keymaps.py             keymap registration
    overlay.py             touch region overlay
    blender.py             preferences access, safe area and other UI helpers
```

How the tools fit together:

- **Local Transform** moves, rotates and scales the whole object instead of its vertices, so the origin stays with the mesh. Scale is applied to the mesh when each scale ends, so stretches never skew. The **Instances** pivot, which is the default, turns or scales each array copy in place by turning the array settings back by the same amount.
- **Arrays** are Geometry Nodes modifiers built by the add-on, one node group per kind, versioned by a custom property. The real mesh stays in place and sculptable, and the copies are instances that follow it. The node trees lay out the copies as if the object's scale were already applied, so copies don't warp while a scale is being dragged.
- **Tool gizmos** start operators that share the drag handling in `ops/drag.py`. Each operator's `description()` provides the hovered gizmo's tooltip.

Development notes (Blender 5.2):

- Geometry Nodes modifier inputs are read and written through `modifier.properties.inputs.<socket id>.value`, not `modifier["Socket_N"]`.
- Gizmo offsets (`matrix_offset`) are in scene units unless `use_draw_offset_scale` is set, which makes them follow the gizmo's screen size.
- Writing `matrix_world` recomputes the scale with rounding errors. Moves and rotations restore the exact scale afterwards.
- Data can't be changed while gizmos draw, so tools change data from a `bpy.app.timers` callback.
- Python edits to mesh data in Sculpt Mode, and Python operators with `UNDO`, both undo correctly. `object.transform_apply` doesn't run in Sculpt Mode, but `object.modifier_apply` does.
- Sculpt and Edit Mode undo steps can't add or remove objects. Operators that do (Add Mesh, Join, Fuse) store a whole scene step first (`push_scene_undo`, which hides the active object so Blender picks that step type), finish in Object Mode so their own step is a whole scene step too, and return to the mode from a timer (`finish_in_mode`). Those steps are saved in Object Mode, so the object carries a `touchview_return_mode` property and undo/redo handlers switch it back. Each such operator leaves one extra "Before ..." undo step.
- Undo can be tested in the UI with operators called from a timer as `bpy.ops.<op>("EXEC_DEFAULT", True, ...)` (the `True` pushes an undo step) and `bpy.context.window_manager.print_undo_steps()`.
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
- [x] Default and per-file settings: Save Default Settings in the sidebar, settings stored in the .blend file when they differ, Auto-Save Defaults option.
- [x] Add Mesh: shape options (segments, subdivisions, base vertices, capsule and torus sizes), Smooth and Round Edges; Icosphere, Quad Sphere and Capsule. Undo and redo in Sculpt and Edit Mode fixed for Add Mesh, Join and Fuse.

Next:

- [ ] Curve array.
- [ ] README feature sections for Local Transform and the array tools (so far they're only in the changelog).
- [ ] Decide what an array tool does when a file is opened with it active (it currently adds an array right away).

Known limitations:

- Arrays after a Multires modifier probably don't apply as displayed. Arrays are aimed at voxel and dynamic topology meshes.
- Blender hides generative modifiers while dynamic topology is on, so array copies may not show then.
- Brushes only act on the real mesh, not on array copies, until the array is applied.
- Arrays created before node group version 2 lack the scale handling; remove and re-add them.
- After Add Mesh, Join or Fuse in Edit Mode, undoing the first edit made afterwards lands in Object Mode (Blender only leaves Edit Mode when the scene step it undoes to is already loaded, so the return mode mark isn't seen). Sculpt Mode isn't affected.
