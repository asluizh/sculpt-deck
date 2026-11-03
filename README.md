<div align="center" style="display: flex; flex-direction: column; align-items: center; justify-content: center;">
  <h1>TouchView</h1>
  <div>BLENDER 3D add-on</div>
  <div><sup>customizable rotate/pan/zoom</sup></div>
  <div style="display: flex; flex-direction: row;">
    <img alt="GitHub release (latest by date)" src="https://img.shields.io/github/v/release/nendotools/touchview?style=flat-square">
    <img alt="GitHub Workflow Status (with branch)" src="https://img.shields.io/github/actions/workflow/status/nendotools/touchview/linting.yml?style=flat-square">
    <img alt="GitHub issues" src="https://img.shields.io/github/issues-raw/nendotools/touchview?style=flat-square">
    <img alt="GitHub" src="https://img.shields.io/github/license/nendotools/touchview?style=flat-square">
    <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/fake-bpy-module-latest?style=flat-square">
  </div>
</div>

### Table of Contents

- [Features](https://github.com/nendotools/touchview#features)
- [Building from Github](https://github.com/nendotools/touchview#building-from-github)
- [Installation](https://github.com/nendotools/touchview#installation)
- [Changelog](https://github.com/nendotools/touchview#changelog)

# Features

This add-on is designed to improve the user experience of Blender for users without immediate access to a keyboard or mouse. It provides many customizable UI improvements to cater to your workflow needs.

<div style="display:flex; flex-direction:row;">
<img align="right" src="/docs/simple_demo.gif" width="40%">
<div width="60%">
<h2>Viewport Touch Control</h2>

Pan, Rotate, and Zoom the viewport with your finger.

The viewport has be updated to use 3 interactive "hot regions" to control the camera position.

If you are a pen tablet user; the pen will still draw, while your finger can be used to control the camera.

If your tablet doesn't support touch; you can set the middle mouse button to activate the control regions in the add-on prefs.

- Pan by dragging for the middle of the viewport
- Zoom by dragging along the left or right edge of the viewport
- Rotate by dragging the remaining space in the viewport

<h3>Additional Details</h3>

Touch Controls come with a toggleable overlay which can be assigned colors.

It is recommended to disable the overlay once you are comfortable with the size of each touch region, or set the transparency very low. (note: the overlay will not be shown in the render output)

You may chose to switch the Pan and Rotate regions. If you lock the viewport rotation, Panning can be done anywhere between the Zoom control regions.

</div>
</div>

## Tap to Select or Switch Objects

Tap an object with your finger to select it in Object Mode, or to switch to it without leaving the current mode in Edit, Sculpt and Paint modes. Dragging still moves the view, and a second tap nearby makes a double tap. This can be turned off in the Control Zones settings.

Long press an object to add it to or remove it from the selection, then use _Join Selected_, _Fuse (Union)_ (merge and voxel remesh into one surface) or _Fuse (Difference)_ (cut the other objects out of the active one and voxel remesh it) from the action pie or the widget, without leaving the current mode.

## Add Meshes Without Leaving Your Mode

The _Add Mesh_ action (available in the action pie) adds a UV sphere, icosphere, quad sphere, cube, cylinder, cone, capsule, torus, plane or monkey at the 3D cursor and keeps you in the mode you were in. In Sculpt Mode the new mesh is voxel remeshed to an even, sculptable density. The icosphere, quad sphere and plane are already evenly spaced, so they're kept as they are.

The _Adjust Last Operation_ panel has:

- **Shape options**: segments and rings (sphere), subdivisions (icosphere, quad sphere), base vertices (cylinder and cone: 6 for a hexagonal prism, 4 for a pyramid), radius and length (capsule), outer and inner radius and segments (torus).
- **Resolution** (Sculpt Mode): how dense the remesh is.
- **Smooth** (on by default): shades the mesh smooth.
- **Round Edges** (cube, cylinder, cone): rounds off the sharp edges, from crisp to fully rounded.

## Double Click and Right Click Actions

A double tap (or mouse double click) and a mouse or touch right click can each run an action, chosen for each mode from the same list as a pen button click: Blender's default, nothing, brushes, tools, the widget and pie actions, or any operator or menu. Turn them on with the checkbox in their sidebar panel header (_Touchview > Double Click_ and _Right Click_) or in the add-on preferences under _Pen & Clicks_.

By default the double tap maximizes the area, and right click is off, leaving it to Blender.

###### _note:_ this feature only works by tapping your finger or clicking to prevent the pen from accidentally triggering it while drawing

## Custom On-screen Buttons

![gizmo bar](/docs/gizmo_bar.png)

Important features have been made available directly in the viewport. Each mode has up to 12 buttons, chosen in the sidebar under _Touchview > Widget Buttons_ (or in the add-on preferences) from the same list of actions as the action pie, or any custom operator or menu.

By default they include undo/redo, add mesh, recenter view, maximize area, the sidebar toggle and, depending on the mode, the object gizmo, voxel remesh, Multires levels and brush size/strength. Buttons that can't be used hide themselves, e.g. the voxel buttons on objects with a Multires modifier. Buttons that open a menu keep it open when tapped, or close it on release when held (releasing over an item picks it). Quad view, rotation lock, voxel density and many more are available from the list.

### Additional Details

#### Toggle Quad-view

Quad-view may sometimes replace the perspective viewport with an orthographic viewport when toggled off and on. This may cause the main viewport rotation to be automatically locked. Simply unlock it with the on-screen button.

#### Recent Viewport

This attempts to bring the active object back into view. If the origin is misaligned, it may not work perfectly.

#### Viewport Rotation Lock

Locking the viewport rotation replaces viewport rotation with panning control.

###### _NOTE:_ Quad-view will default to rotation locking for isometric viewports (top, front, and side views)

#### Topology Control

This feature provides quick access to Retopology control in Sculpt mode and is not shown in any other mode.

If the selected object has a Multi-resolution modifier; the retopology controls change to subdivision level controls.

![subdivision level control](/docs/sub-div_level.png)

Quickly jump through subdivision levels, subdivide and unsubdivide right from the viewport.

![subdivision available](/docs/subdiv_available.png)

A yellow icon means the next subdivision step needs to be calculated. It will automatically try to subdivide/unsubdivide when clicked.

![subdivision limit](/docs/subdiv_limit.png)

A red icon means you have reached your subdivision limit and it will not try to subdivide further. You may change the maximum subdivision levels available for the on-screen buttons to limit accidental subdivision.

###### _note:_ the subdivision limit only applies to increasing subdivision levels. You may unsubdivide as much as Blender is able.

#### Sculpt Brush Dynamics

This feature allows you to quickly access the UI for brush resizing and strength control in sculpt mode.

## Fully Customizable Action Pie

<img src="/docs/sample_menu.png" width="50%">

An action pie with up to 8 commands, unique to each mode (object, edit, sculpt, the paint modes and Grease Pencil draw; every other mode shares one pie). Open it from a widget button (_Action Pie_) or a pen button.

Set it up in the sidebar under _Touchview > Action Pie_, which edits the pie of the mode you're in, or in the add-on preferences. Each pie position has a dropdown of popular actions for that mode (e.g. the brush picker, mask and face set popups, and tools like box trim or mesh filter in sculpt mode) plus common ones that usually need a keyboard: undo history, adjust last operation, the mode, view, shading, pivot and snap pies, frame selected, local view, X-ray, search and save. _All Actions_ opens a popup with every action for the current mode, so nothing is out of reach between reassignments. Pick _Custom..._ to type any operator (`object.shade_smooth`) or menu (`VIEW3D_MT_add`) name; turn on _Preferences > Interface > Python Tooltips_ to see them when hovering Blender's buttons.

## Pen Buttons

Give your pen's side buttons their own actions in every mode, separately for a click and for a hold/drag. Only the pen is affected; mouse and touch keep their usual behavior.

A **click** can use most actions from the action pie and widget list, the action pie itself, or:

- **Blender Default** / **Nothing**
- **Previous Brush** / **Specific Brush** (brush modes): switch brushes; for a specific brush, pick it the usual way and press the eyedropper next to the binding
- **Invert Brush** (Sculpt Mode): a click swaps the brush direction (e.g. add/subtract, smooth/enhance details); a hold inverts the strokes you draw while holding it, like holding Ctrl
- **Tools** such as mask, hide, face set, trim, filters and the transform tools in Sculpt Mode, or transform, cursor and modeling tools in Object and Edit Mode

By default, in Sculpt Mode, button 1 (the lower one) inverts the brush on click and hold, and button 2 switches to the previous brush on click and uses the Smooth brush while held.

A **hold** uses a brush or a tool only until the button is released, e.g. hold for the Smooth brush, or hold and draw with the tip for a Box Hide. Actions that change the mesh resolution (remesh, Multires levels) aren't offered for pen buttons, which are easy to press by accident; _Edit Voxel Size_ is.

A press becomes a hold after a moment, once the pen moves, or when the tip touches down while the button is held. Set them up in the sidebar under _Touchview > Pen Buttons_, which edits the mode you're in, or in the add-on preferences.

## Default and Per-file Settings

Settings changed in the sidebar or the add-on preferences apply right away. When they differ from your defaults, the bottom of the _Touchview_ sidebar tab offers **Save Default Settings** (use them for new files and files without their own settings) and a revert button (go back to the defaults). Until they're saved as defaults, the changed settings are stored in the .blend file when you save it, so each file can keep its own setup. Opening a file without its own settings brings back the defaults.

To have every change saved as the default instead, turn on **Auto-Save Defaults** in the add-on preferences.

Defaults are kept in the add-on's user folder, so they survive add-on updates. You don't need to save Blender's preferences for them.

# Feature Roadmap

If you have a suggestion for more features, please check if it's on this list before submitting a request on Github.

I'm continuing to look at features which could improve the experience of Blender without adding too much clutter to the UI.

Currently, I'm planning to add the following features:

> - better 3D gizmos for edit mode
> - control gizmo enum (flip through object gizmos in sculpt mode)

This list will change as I explore options and get more user feedback.

# Building from Github

Building the addon zip can be done by using the included `bundle.sh` script. Simply run:

```
./bundle.sh
```

It will output the files to include and generate a new ZIP file:

```
$ ./bundle.sh
  adding: touchview/ (stored 0%)
  adding: touchview/source/ (stored 0%)
  adding: touchview/source/gizmos.py (deflated 77%)
  adding: touchview/source/items.py (deflated 68%)
  adding: touchview/source/operators.py (deflated 80%)
  adding: touchview/source/overlay.py (deflated 73%)
  adding: touchview/source/panel.py (deflated 69%)
  adding: touchview/source/touch_input.py (deflated 69%)
  adding: touchview/source/__init__.py (deflated 70%)
  adding: touchview/prefs.py (deflated 76%)
  adding: touchview/__init__.py (deflated 51%)
```

The final ZIP can be found in:

```
./bin/touchview.zip
```

# Installation

In Blender, open `Edit` > `Preferences...`.

Navigate to the `Add-ons` tab.

Click `Install...` and navigate to the `touchview.zip` file.

Select it and click `Install Add-on`.

###### _note:_ You do not need to extract it, first. Simply install the ZIP, directly

# Changelog

<details open><summary><b>Unreleased</b></summary><br>

- `ADDED`: Add Mesh shapes: Icosphere and Quad Sphere (with subdivisions), and Capsule (with radius and length).
- `ADDED`: Add Mesh shape options: sphere segments and rings, cylinder and cone base vertices (for prisms and pyramids), torus outer and inner radius and segments.
- `ADDED`: Add Mesh _Smooth_ (shade smooth, on by default) and _Round Edges_ (cube, cylinder, cone) options.
- `CHANGED`: Add Mesh in Sculpt Mode keeps the icosphere, quad sphere and plane as they are instead of remeshing them.
- `CHANGED`: Double Click and Right Click use the pen button click actions, set for each mode, with an on/off checkbox in their panel header. Defaults: double tap maximizes the area, right click is off (Blender's own). The Mouse/Touch/Off choice for right click is gone.
- `ADDED`: Default and per-file settings: _Save Default Settings_ and revert at the bottom of the sidebar when the settings differ from the defaults; changed settings are kept in the .blend file; _Auto-Save Defaults_ option.
- `FIXED`: Settings were only saved when Blender quit normally or the add-on was disabled, and into the add-on's folder, so a crash or an add-on update lost them. Defaults now live in the add-on's user folder; the old file is read once to carry the settings over.
- `FIXED`: In Sculpt or Edit Mode, undoing Add Mesh, Join or Fuse left the objects behind, and changing Add Mesh settings in _Adjust Last Operation_ added a new copy each time.

</details>

<details><summary><b>v4.4.0</b></summary><br>

- `ADDED`: Local Transform tool (Sculpt Mode): move, rotate and scale the whole object along its own or the world's axes, with per-handle tooltips and a uniform scale ring. Scale is applied to the mesh after every scale, so stretching after a rotation never skews it.
- `ADDED`: Local Transform pivots: Origin, Bounding Box Center, 3D Cursor and Instances (default), which rotates and scales each array copy in place.
- `ADDED`: Linear Array and Circular Array tools (Sculpt Mode): copies follow the mesh as you sculpt, can be stacked, and are edited with gizmos for count, spacing, radius, center and arc (15° steps inside the circle, 1° outside). They have X/Y/Z/View axes and Global/Local handles, and can be applied or removed from the header.
- `ADDED`: Apply Scale without leaving Sculpt Mode.
- `ADDED`: Pen button bindings per mode, with separate click and hold actions, temporary brushes and tools while held, and Invert Brush.
- `ADDED`: Configurable widget (up to 12 buttons per mode) and action pie (8 slots per mode), sharing one action list with the pen buttons; All Actions popup.
- `ADDED`: Tap an object to select it or switch to it, and long press to toggle its selection.
- `ADDED`: Add Mesh, Join Selected, Fuse (Union) and Fuse (Difference) without leaving the current mode.
- `CHANGED`: Add Mesh in Sculpt Mode switches to the Local Transform tool to place the new mesh.
- `CHANGED`: The action pie is a widget button instead of a separate floating button.
- `FIXED`: Action menu slots weren't restored from saved preferences.

</details>

<details><summary><b>v4.3.0</b></summary><br>

- `CHANGED`: Requires Blender v5.2 or newer.
- `ADDED`: Tooltips on every on-screen button.
- `ADDED`: Brush Dynamics buttons in Grease Pencil 3 and Curves Sculpt modes.
- `FIXED`: Brush size button had no effect in Blender 5.x (unified paint settings moved per paint mode).
- `FIXED`: On-screen buttons disappeared in quad view; each quad view now shows its own menu.
- `FIXED`: Fixed bar overlapped Blender's navigation gizmo; side bars now stay in the lower half of the viewport and wrap into extra columns/rows when needed.
- `FIXED`: Fixed bar covered the floating toggle and action menu buttons in the bottom corners.
- `FIXED`: Floating toggle was hidden along with the gizmo menu.
- `FIXED`: Viewport didn't redraw when changing gizmo settings in the Preferences window.
- `FIXED`: Decrease Multires stopped at the first non-Multires modifier.
- `FIXED`: Voxel density buttons failed when the mesh name differed from the object name.
- `IMPROVED`: Gizmo safe area now avoids the toolbar, sidebar, headers and asset shelf per region.
- `IMPROVED`: Clearer description for the Floating Toggle option.
- `REMOVED`: Unused duplicate gizmo modules.

</details>

<details><summary><b>v4.2.0</b></summary><br>

- `ADDED`: Support for Blender v4.2 (Extensions).
- `FIXED`: Gizmo size and overlapping.
- `FIXED`: Mouse position after moving the gizmo.
- `FIXED`: Broken reference to full control mode in enabled check.
- `CHANGED`: Class names, `register()`, and `unregister()` according to Blender conventions.
- `CHANGED`: EnumProperty items according to Blender conventions.
- `CHANGED`: Cursor type on hover over the gizmo.
- `CHANGED`: Folder structure.
- `IMPROVED`: Gizmo safe area.
- `IMPROVED`: UI and tooltips.

</details>

<details><summary><b>v4.0.5</b></summary><br>

- `ADDED`: switch 2D header toggle UI position

</details>

<details><summary><b>v4.0.4</b></summary><br>

- `ADDED`: optional enable floating toggle for touch controls in mixed mode
- `ADDED`: toggle touch controls button in node editor and image editor headers

</details>

<details><summary><b>v4.0.3</b></summary><br>

- `UPDATED`: fixed bug where hotkeys aren't assigned when opening Blender directly by file

</details>

<details><summary><b>v4.0.2</b></summary><br>

- `ADDED`: Nendo Tools Menu (limited options) for Image Editor and Node Editor
- `REMOVED`: Right-Click Action for Image Editor and Node Editor

</details>

<details><summary><b>v4.0.0</b></summary><br>
Compatibility update for Blender 4.0

- `ADDED`: support for Blender 4.0
- `ADDED`: auto-save/load preferences
- `UPDATED`: replace bgl module refs with gpu module implementation
- `UPDATED`: Swap Control Regions fixed context override implementation
- `UPDATED`: early exit when dragging gizmo near edge of viewport to prevent negative overflow
- `REMOVED`: argument renaming to disregard unused args (currently breaking CI/CD)

</details>

<details><summary><b>v2.12.0</b></summary><br>

- `UPDATED`: fixed bug with unindexed modes breaking gizmo menus
- `UPDATED`: updated resize and change strength for 2D views
- `UPDATED`: improved support for multi-mode devices

</details>

<details><summary><b>v2.11.0</b></summary><br>

- `UPDATED`: added various GPENCIL modes to edit mode list
- `UPDATED`: updated viewport gizmo panel to support v3.6 changes

</details>

<details><summary><b>v2.10.0</b></summary><br>

- `ADDED`: lazy camera control toggle in sculpt mode
- `UPDATED`: add support for Weylus (\*nix) sending 0.0 for pressure on touch events
- `UPDATED`: changed all new operator namespaces to `nendo` for easier identification
- `ADDED`: control mode icon when using signle-input mode
- `UPDATED`: control mode toggle and floating action button now use same sizing as gizmos
- `ADDED`: additional fine-tuning controls for gizmo spacing

</details>

<details><summary><b>v2.9.0</b></summary><br>

- `UPDATED`: additional changes to gizmo spacing
- `UPDATED`: fixed bug preventing custom actions being assigned for radial menu

</details>

<details><summary><b>v2.8.0</b></summary><br>

- `UPDATED`: fixed issues with menu bar spacing
- `REMOVED`: floating menu bar

</details>

<details><summary><b>v2.7.1</b></summary><br>

- `UPDATED`: replaced region_full_area with window_fullscreen

</details>

<details><summary><b>v2.7.0</b></summary><br>

- `ADDED`: relative remesh
- `UPDATED`: fixed error when disabling add-on

</details>

<details><summary><b>v2.6.0</b></summary><br>

- `UPDATED`: code spec now based on flake8
- `UPDATED`: added alternative action for TransferMode when used in OBJECT mode
- `UPDATED`: fixed desktop scaling issue with radial gizmo menu
- `UPDATED`: fixed toggle touch gizmo and RC/DC action
- `UPDATED`: fixed error message when rotation locked and pan/rotate swapped

</details>

<details><summary><b>v2.5.0</b></summary><br>

- `ADDED`: Gizmo size control
- `UPDATED`: moved operators into folder

</details>

<details><summary><b>v2.4.0</b></summary><br>

- `UPDATED`: preferences access simplified with utility function
- `ADDED`: single-input mode now activates large floating toggle button

</details>

<details><summary><b>v2.3.0</b></summary><br>

- `ADDED`: Input Mode selection (for devices with only touch or pen support)

</details>

<details><summary><b>v2.2.0</b></summary><br>

- `ADDED`: Toggle control gizmo (translate, rotate, scale, none)
- `UPDATED`: Added Brush dynamics (from sculpt mode) to paint modes
  - <span style="font-size: 0.6em">NOTE: some paint/sculpt modes when in 2D/Draw canvas mode aren't yet hooked up to brush dynamics </span>

</details>

<details><summary><b>v2.1.0</b></summary><br>

- `ADDED`: Right Click Actions
- `UPDATED`: Preferences and N-Panel restructure

</details>

<details><summary><b>v2.0.0</b></summary><br>

- `UPDATED`: Gizmos-related code simplified and reorganized for easier management
- `ADDED`: floating gizmo bar and floating gizmo radial menu modes
- `ADDED`: customizable gizmo menu spacing
- `UPDATED`: viewport safe area calculation
- `UPDATED`: floating action menu to use same move/access functionality as floating radial menu
- `ADDED`: 8th custom action for floating action menu

</details>

<details><summary><b>v1.2.4</b></summary><br>

- `ADDED`: Toggle Double-tap action on/off

</details>

<details><summary><b>v1.2.3</b></summary><br>

- `ADDED`: Sculpt Brush Dynamics
- `UPDATED`: Viewport rotation in sculpt mode automatically sets pivot to mesh under touch point

</details>

<details><summary><b>v1.2.2</b></summary><br>

- `UPDATED`: Gizmo panel layout split

</details>

<details><summary><b>v1.2.1</b></summary><br>

- `REMOVED`: Middle Mouse keybind
- `REMOVED`: viewport rotation lock when using the Grease Pencil

</details>

<details><summary><b>v1.2.0</b></summary><br>

- `BREAKING`: This version requires previous version to be disabled before install
- `UPDATED`: Improved Pen detection and simplified key configs
- `ADDED`: Support for various 2D and 2D-like views (Image Editor, UV Editor, 2D Animation, Compositing, etc)

</details>

<details><summary><b>v1.1.2</b></summary><br>

- `ADDED`: Support for Node Editor

</details>

<details><summary><b>v1.1.1</b></summary><br>

- `ADDED`: minor fix to pen detection

</details>

<details><summary><b>v1.1.0</b></summary><br>

- `ADDED`: Independent toggle for entire gizmo bar
- `ADDED`: Customizable double-tap actions
- `ADDED`: Multi-resolution level limiter and gizmo status color

</details>

<details><summary><b>v1.0.1</b></summary><br>

- `ADDED`: Optional include for MIDDLEMOUSE when disabling/enabling touch controls
- `FIXED`: Preferences bug preventing toggle of floating Gizmo

</details>

<details><summary><b>v1.0.0</b></summary><br>

- `ADDED`: Toggle swap pan/rotate regions
- `ADDED`: Toggle floating menu button to N Panel
- `UPDATED`: Disabling touch controls no longer removes overlay (hot regions still work with custom keybinds and MIDDLEMOUSE)
- `UPDATED`: Disabling touch controls restores default LEFTMOUSE functionality

</details>

<details><summary><b>v0.9.6</b></summary><br>

- `ADDED`: undo/redo gizmo
- `ADDED`: overlay color selection
- `ADDED`: touch control toggle in prefs
- `ADDED`: Alt+T to toggle touch controls
- `UPDATED`: N Panel now includes extra prefs from addon menu
- `UPDATED`: Lock Rotation now addresses quadview data replication bug
- `UPDATED`: Limited floating gizmo to viewport area
- `UPDATED`: code cleanup and additional structure tweaks
- `REMOVED`: Gizmo Tooltips

</details>

<details><summary><b>v0.9.5</b></summary><br>

- `ADDED`: multires modifier support to gizmo bar (shows retopology tools when no modifier is present)
- `FIXED`: Gizmos now properly follow mode visibility rules
- `FIXED`: Double-tap selection now only runs in appropriate viewport modes

</details>

<details><summary><b>v0.9.4</b></summary><br>

- `ADDED`: Support for menus in floating gizmo
- `ADDED`: Mode-specific options for floating gizmo
- `UPDATED`: Dependence on active_object for mode detection
- `UPDATED`: Classes to follow Blender naming conventions
- `UPDATED`: Keymaps for touchview in all context
- `UPDATED`: Keymaps for context action assigned to pen

</details>

<details><summary><b>v0.9.3</b></summary><br>

- `ADDED`: Sculpt pivot mode gizmo
- `ADDED`: Customizable floating menu

</details>

<details><summary><b>v0.9.2</b></summary><br>

- `FIXED`: Issue delaying overlay viewport binding
- `FIXED`: Gizmo tools/panel overlap issue when "Region Overlap" enabled
- `REMOVED`: Viewport manager class
- `REMOVED`: Default keymap causing Move Operator to trigger when dragging over non-modal gizmos

</details>

<details><summary><b>v0.9.1</b></summary><br>

- `ADDED`: Tap for menu scroll

</details>

<details><summary><b>v0.9</b></summary><br>

- `ADDED`: N-Panel gizmo
- `UPDATED`: Code restructure
- `FIXED`: Dragging over gizmo moves selected object

</details>

<details><summary><b>v0.8</b></summary><br>

- `ADDED`: Gizmo to toggle fullscreen mode
- `UPDATED`: Settings to addon preferences to save across projects and scenes
- `FIXED`: Bugs impacting user experience
- `FIXED`: Doubletap now selects/activates tapped object instead of triggering fullscreen

</details>

<details><summary><b>v0.7</b></summary><br>

- `ADDED`: Gizmos for key features
- `ADDED`: Hide/show Gizmo and layout options
- `ADDED`: Locked viewport rotation for isometric viewports in quadview to address lock/unlock inconsistencies
- `FIXED`: Fullscreen Toggle no longer maximizes the window, only expands the View3D region

</details>

<details><summary><b>v0.6</b></summary><br>

- `UPDATED`: Scale of viewport overlay prefs for more precision
- `FIXED`: Issues with determining locked state with quadviews

</details>

<details><summary><b>v0.5</b></summary><br>

- `ADDED`: Camera rotation lock in N-panel
- `FIXED`: Quad-view overlay compatibility
- `FIXED`: Rotation with panning when rotation is locked
- `FIXED`: Issue when locking view to Object or 3D Cursor

</details>

<details><summary><b>v0.4</b></summary><br>

- `ADDED`: Double-tap to toggle "focus" mode
- `ADDED`: Toggle Tools LEFT/RIGHT in UI

</details>

<details><summary><b>v0.3</b></summary><br>

- `FIXED`: Incorrect viewport calculation when N-panel is open
- `FIXED`: Refactored screen/area management code (additional major refactor needed)

</details>

<details><summary><b>v0.2</b></summary><br/>

- `FIXED`: Minor bug fixes and code cleanup

</details>

<details><summary><b>v0.1</b></summary><br>

- `ADDED`: Camera dolly on left and right of viewport
- `ADDED`: Camera pan from center of viewport
- `ADDED`: Camera rotate in any other area of viewport
- `ADDED`: Toggleable overlay to simplify resizing controls

</details>

# Issues

> Please [report any issues](https://github.com/nendotools/touchview/issues) you find and I'll do my best to address them.

> The add-on is free, but if it helps you, please consider [supporting me](https://nendo.gumroad.com/l/touchview).
