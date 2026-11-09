"""The Action catalog, and the Action List each Gesture offers in each mode, built from it by rule.

Every Action is listed once in CATALOG with its traits: the modes it applies to, whether it can be Momentary and
whether it is a Resolution Change. A Gesture's Action List in a mode is the surface's own extras (Blender Default,
Nothing, Previous/Specific Brush, Empty), then the mode's Actions minus what the Gesture can't do, then Custom.
Adding an Action here makes it appear on every Gesture where it fits. See GLOSSARY.md for the terms.

A part that can be removed (navigation) adds its own Actions with add_actions when it registers, at the place they
take in the catalog, and takes them out with remove_actions, so without the part they're in no Action List.

An idname is an operator, a menu (_MT_; opened as a pie when it ends in _pie), a brush asset shelf (_AST_) or a
tool (TOOL:). Choices are stored by identifier.
"""

import zlib
from dataclasses import dataclass, replace

from .constants import pen_brush_modes

TOOL_PREFIX = "TOOL:"

# modes with their own Actions (context.mode, as in pie_mode_items); ANY_MODE applies to every mode, also "OTHER"
ANY_MODE = "ANY"
OBJECT = "OBJECT"
EDIT = "EDIT_MESH"
SCULPT = "SCULPT"
VERTEX = "PAINT_VERTEX"
WEIGHT = "PAINT_WEIGHT"
TEXTURE = "PAINT_TEXTURE"
GREASE = "PAINT_GREASE_PENCIL"
MESH_PAINT = (SCULPT, VERTEX, WEIGHT, TEXTURE)
BRUSH_MODES = (*MESH_PAINT, GREASE)


@dataclass(frozen=True)
class Action:
    idname: str
    label: str
    icon: str
    modes: tuple[str, ...]
    # can be engaged only while a button is held and put back on release
    momentary: bool = False
    # changes how dense a mesh is; kept off pen buttons and clicks
    resolution_change: bool = False
    # False for what an Action Pie slot can't hold: the Action Pie itself
    pie_slot: bool = True

    def applies_to(self, mode: str) -> bool:
        return ANY_MODE in self.modes or mode in self.modes

    @property
    def every_mode(self) -> bool:
        return ANY_MODE in self.modes


def action(idname: str, label: str, icon: str, *modes: str, **traits) -> Action:
    return Action(idname, label, icon, modes, **traits)


def tool(name: str, label: str, icon: str, *modes: str) -> Action:
    """A toolbar tool, used while a pen button is held"""
    return Action(TOOL_PREFIX + name, label + " Tool", icon, modes, momentary=True)


def again(earlier: Action, *modes: str) -> Action:
    """The same Action placed again, in other modes, where those modes list it at another position"""
    return replace(earlier, modes=modes)


# Blender's own Join drops the other meshes' modifiers, so Object Mode gets ours too
_join = action("sculpt_deck.join_selected", "Join Selected", "OBJECT_DATA", OBJECT)
_cycle_gizmo = action("sculpt_deck.cycle_control_gizmo", "Cycle Object Gizmo", "ORIENTATION_LOCAL", OBJECT, EDIT)

# In catalog order. A mode's Actions come in this order, so an Action shared by several modes sits where all of
# them list it; again() places one a second time when two modes can't agree. Actions for every mode come last.
CATALOG: list[Action] = [
    # offered in every mode, set apart at the top
    action("SCULPT_DECK_MT_floating", "Action Pie", "SETTINGS", ANY_MODE, pie_slot=False),
    # the mode's own
    action("VIEW3D_MT_add", "Add", "ADD", OBJECT),
    action("object.delete", "Delete", "X", OBJECT),
    action("object.duplicate_move", "Duplicate", "DUPLICATE", OBJECT),
    action("object.duplicate_move_linked", "Duplicate Linked", "LINKED", OBJECT),
    _join,
    action("VIEW3D_MT_edit_mesh_select_mode", "Select Mode", "VERTEXSEL", EDIT),
    action("VIEW3D_AST_brush_sculpt", "Brushes", "BRUSHES_ALL", SCULPT),
    action("VIEW3D_AST_brush_vertex_paint", "Brushes", "BRUSHES_ALL", VERTEX),
    action("VIEW3D_AST_brush_weight_paint", "Brushes", "BRUSHES_ALL", WEIGHT),
    action("VIEW3D_AST_brush_texture_paint", "Brushes", "BRUSHES_ALL", TEXTURE),
    action("VIEW3D_AST_brush_gpencil_paint", "Brushes", "BRUSHES_ALL", GREASE),
    action("sculpt_deck.brush_previous", "Previous Brush", "LOOP_BACK", *BRUSH_MODES),
    action("sculpt_deck.brush_invert", "Invert Brush", "ARROW_LEFTRIGHT", SCULPT, momentary=True),
    action("SCULPT_DECK_MT_add_mesh", "Add Mesh", "ADD", EDIT, *MESH_PAINT),
    action("sculpt_deck.duplicate_object", "Duplicate", "DUPLICATE", *MESH_PAINT),
    action("sculpt_deck.delete_object", "Delete", "X", *MESH_PAINT),
    action("sculpt_deck.brush_resize", "Brush Size", "ANTIALIASED", *BRUSH_MODES),
    action("sculpt_deck.brush_strength", "Brush Strength", "SMOOTHCURVE", *BRUSH_MODES),
    action("sculpt_deck.stroke_method", "Stroke Method", "STROKE", *MESH_PAINT),
    again(_join, SCULPT),
    action("sculpt_deck.fuse_selected", "Fuse (Union)", "SELECT_EXTEND", OBJECT, SCULPT, resolution_change=True),
    action("sculpt_deck.fuse_difference", "Fuse (Difference)", "SELECT_DIFFERENCE", OBJECT, SCULPT,
           resolution_change=True),
    _cycle_gizmo,
    action("VIEW3D_MT_mask", "Mask Popup", "MOD_MASK", SCULPT),
    action("VIEW3D_MT_sculpt_mask_edit_pie", "Mask Edit Pie", "MOD_MASK", SCULPT),
    action("paint.mask_flood_fill", "Clear Mask", "CLIPUV_DEHLT", SCULPT),
    action("sculpt_deck.mask_invert", "Invert Mask", "CLIPUV_HLT", SCULPT),
    action("sculpt_deck.reveal_all", "Reveal Hidden", "HIDE_OFF", SCULPT),
    action("VIEW3D_MT_face_sets", "Face Sets Popup", "FACE_MAPS", SCULPT),
    action("VIEW3D_MT_sculpt_face_sets_edit_pie", "Face Sets Edit Pie", "FACE_MAPS", SCULPT),
    action("VIEW3D_MT_sculpt_automasking_pie", "Auto-Masking Pie", "MOD_MASK", SCULPT),
    action("paint.visibility_invert", "Invert Visibility", "HIDE_ON", SCULPT),
    action("object.voxel_remesh", "Voxel Remesh", "MOD_REMESH", SCULPT, resolution_change=True),
    # editing the voxel size alone changes nothing yet
    action("object.voxel_size_edit", "Edit Voxel Size", "MESH_GRID", SCULPT),
    action("sculpt_deck.density_up", "Voxel Density Up", "TRIA_UP", SCULPT, resolution_change=True),
    action("sculpt_deck.density_down", "Voxel Density Down", "TRIA_DOWN", SCULPT, resolution_change=True),
    action("sculpt_deck.increment_multires", "Multires Level Up", "TRIA_UP", OBJECT, SCULPT, resolution_change=True),
    action("sculpt_deck.decrement_multires", "Multires Level Down", "TRIA_DOWN", OBJECT, SCULPT,
           resolution_change=True),
    again(_cycle_gizmo, SCULPT),
    action("sculpt_deck.apply_object_scale", "Apply Scale", "CON_SIZELIKE", SCULPT),
    action("sculpt_deck.array_apply", "Apply Array", "MOD_ARRAY", SCULPT),
    action("sculpt_deck.array_remove", "Remove Array", "X", SCULPT),
    action("sculpt_deck.mirror_apply", "Apply Mirror", "MOD_MIRROR", SCULPT),
    action("sculpt_deck.mirror_remove", "Remove Mirror", "X", SCULPT),
    action("object.quadriflow_remesh", "QuadriFlow Remesh", "MOD_REMESH", SCULPT, resolution_change=True),
    action("sculpt.dynamic_topology_toggle", "Toggle Dyntopo", "MESH_DATA", SCULPT, resolution_change=True),
    action("VIEW3D_MT_sculpt", "Sculpt Menu", "SCULPTMODE_HLT", SCULPT),
    action("object.select_all", "Select All (Toggle)", "RESTRICT_SELECT_OFF", OBJECT),
    action("object.hide_view_set", "Hide Selected", "HIDE_ON", OBJECT),
    action("object.hide_view_clear", "Reveal Hidden", "HIDE_OFF", OBJECT),
    action("object.shade_smooth", "Shade Smooth", "SMOOTHCURVE", OBJECT),
    action("object.shade_auto_smooth", "Shade Auto Smooth", "MOD_SMOOTH", OBJECT),
    action("object.shade_flat", "Shade Flat", "MESH_PLANE", OBJECT),
    action("VIEW3D_MT_object_apply", "Apply", "CHECKMARK", OBJECT),
    action("VIEW3D_MT_object_parent", "Parent", "ORIENTATION_PARENT", OBJECT),
    action("VIEW3D_MT_snap", "Snap", "SNAP_ON", OBJECT),
    action("object.origin_set", "Set Origin", "OBJECT_ORIGIN", OBJECT),
    action("VIEW3D_MT_object_context_menu", "Context Menu", "COLLAPSEMENU", OBJECT),
    action("mesh.select_all", "Select All (Toggle)", "RESTRICT_SELECT_OFF", EDIT),
    action("mesh.select_linked", "Select Linked", "LINKED", EDIT),
    action("mesh.select_more", "Select More", "ADD", EDIT),
    action("mesh.select_less", "Select Less", "REMOVE", EDIT),
    action("view3d.edit_mesh_extrude_move_normal", "Extrude", "EXPORT", EDIT),
    action("mesh.inset", "Inset Faces", "FULLSCREEN_EXIT", EDIT),
    action("mesh.bevel", "Bevel", "MOD_BEVEL", EDIT),
    action("mesh.loopcut_slide", "Loop Cut", "MOD_EDGESPLIT", EDIT),
    action("mesh.knife_tool", "Knife", "MOD_TRIANGULATE", EDIT),
    action("mesh.subdivide", "Subdivide", "MOD_SUBSURF", EDIT, resolution_change=True),
    action("mesh.edge_face_add", "Make Edge/Face", "FACESEL", EDIT),
    action("VIEW3D_MT_edit_mesh_merge", "Merge", "AUTOMERGE_ON", EDIT),
    action("VIEW3D_MT_edit_mesh_delete", "Delete", "X", EDIT),
    action("mesh.hide", "Hide Selected", "HIDE_ON", EDIT),
    action("mesh.reveal", "Reveal Hidden", "HIDE_OFF", EDIT),
    action("VIEW3D_MT_edit_mesh_context_menu", "Context Menu", "COLLAPSEMENU", EDIT),
    action("paint.sample_color", "Sample Color", "EYEDROPPER", VERTEX, TEXTURE),
    action("paint.brush_colors_flip", "Swap Colors", "ARROW_LEFTRIGHT", VERTEX, TEXTURE),
    action("paint.vertex_color_set", "Fill with Color", "COLOR", VERTEX),
    action("paint.vertex_color_invert", "Invert Colors", "GROUP_VCOL", VERTEX),
    action("paint.vertex_color_smooth", "Smooth Colors", "MOD_SMOOTH", VERTEX),
    action("VIEW3D_MT_paint_vertex", "Paint Menu", "VPAINT_HLT", VERTEX),
    action("paint.weight_sample", "Sample Weight", "EYEDROPPER", WEIGHT),
    action("paint.weight_sample_group", "Sample Group", "EYEDROPPER", WEIGHT),
    action("paint.weight_gradient", "Weight Gradient", "IPO_EASE_IN_OUT", WEIGHT),
    action("paint.weight_set", "Set Weight", "WPAINT_HLT", WEIGHT),
    action("VIEW3D_MT_paint_weight_lock", "Locks", "LOCKED", WEIGHT),
    action("VIEW3D_MT_paint_weight", "Weights Menu", "WPAINT_HLT", WEIGHT),
    action("paint.add_texture_paint_slot", "Add Paint Slot", "IMAGE_DATA", TEXTURE),
    action("image.save_all_modified", "Save All Images", "FILE_TICK", TEXTURE),
    action("GREASE_PENCIL_MT_layer_active", "Active Layer", "OUTLINER_DATA_GP_LAYER", GREASE),
    action("grease_pencil.layer_add", "Add Layer", "ADD", GREASE),
    action("grease_pencil.insert_blank_frame", "Insert Blank Frame", "KEYFRAME", GREASE),
    action("grease_pencil.frame_duplicate", "Duplicate Frame", "DUPLICATE", GREASE),
    action("grease_pencil.interpolate", "Interpolate", "IPO_EASE_IN_OUT", GREASE),
    action("grease_pencil.interpolate_sequence", "Interpolate Sequence", "IPO_EASE_IN_OUT", GREASE),
    # toolbar tools, after the mode's other Actions
    tool("builtin.select_box", "Select Box", "RESTRICT_SELECT_OFF", OBJECT, EDIT),
    tool("builtin.cursor", "3D Cursor", "PIVOT_CURSOR", OBJECT, EDIT),
    tool("builtin.brush", "Brush", "BRUSH_DATA", SCULPT),
    tool("builtin.box_mask", "Box Mask", "MOD_MASK", SCULPT),
    tool("builtin.lasso_mask", "Lasso Mask", "MOD_MASK", SCULPT),
    tool("builtin.line_mask", "Line Mask", "MOD_MASK", SCULPT),
    tool("builtin.polyline_mask", "Polyline Mask", "MOD_MASK", SCULPT),
    tool("builtin.box_hide", "Box Hide", "HIDE_ON", SCULPT),
    tool("builtin.lasso_hide", "Lasso Hide", "HIDE_ON", SCULPT),
    tool("builtin.line_hide", "Line Hide", "HIDE_ON", SCULPT),
    tool("builtin.polyline_hide", "Polyline Hide", "HIDE_ON", SCULPT),
    tool("builtin.box_face_set", "Box Face Set", "FACE_MAPS", SCULPT),
    tool("builtin.lasso_face_set", "Lasso Face Set", "FACE_MAPS", SCULPT),
    tool("builtin.face_set_edit", "Edit Face Set", "FACE_MAPS", SCULPT),
    tool("builtin.box_trim", "Box Trim", "MOD_BOOLEAN", SCULPT),
    tool("builtin.lasso_trim", "Lasso Trim", "MOD_BOOLEAN", SCULPT),
    tool("builtin.line_trim", "Line Trim", "MOD_BOOLEAN", SCULPT),
    tool("builtin.polyline_trim", "Polyline Trim", "MOD_BOOLEAN", SCULPT),
    tool("builtin.line_project", "Line Project", "MOD_UVPROJECT", SCULPT),
    tool("builtin.mesh_filter", "Mesh Filter", "MOD_SIMPLEDEFORM", SCULPT),
    tool("builtin.cloth_filter", "Cloth Filter", "MOD_CLOTH", SCULPT),
    tool("builtin.color_filter", "Color Filter", "COLOR", SCULPT),
    tool("builtin.mask_by_color", "Mask by Color", "EYEDROPPER", SCULPT),
    tool("builtin.move", "Move", "CON_LOCLIKE", OBJECT, EDIT, SCULPT),
    tool("builtin.rotate", "Rotate", "CON_ROTLIKE", OBJECT, EDIT, SCULPT),
    tool("builtin.scale", "Scale", "CON_SIZELIKE", OBJECT, EDIT, SCULPT),
    tool("builtin.transform", "Transform", "OBJECT_ORIGIN", OBJECT, SCULPT),
    tool("builtin.measure", "Measure", "DRIVER_DISTANCE", OBJECT),
    tool("builtin.annotate", "Annotate", "GREASEPENCIL", OBJECT),
    tool("builtin.extrude_region", "Extrude Region", "EXPORT", EDIT),
    tool("builtin.inset_faces", "Inset Faces", "FULLSCREEN_EXIT", EDIT),
    tool("builtin.bevel", "Bevel", "MOD_BEVEL", EDIT),
    tool("builtin.loop_cut", "Loop Cut", "MOD_EDGESPLIT", EDIT),
    tool("builtin.knife", "Knife", "MOD_TRIANGULATE", EDIT),
    tool("builtin.poly_build", "Poly Build", "MESH_DATA", EDIT),
    tool("builtin.smooth", "Smooth", "MOD_SMOOTH", EDIT),
    tool("builtin.shrink_fatten", "Shrink/Fatten", "FULLSCREEN_ENTER", EDIT),
    tool("builtin.edge_slide", "Edge Slide", "ARROW_LEFTRIGHT", EDIT),
    tool("sculpt_deck.local_transform", "Local Transform", "ORIENTATION_LOCAL", SCULPT),
    tool("sculpt_deck.mirror", "Mirror", "MOD_MIRROR", SCULPT),
    tool("sculpt_deck.linear_array", "Linear Array", "MOD_ARRAY", SCULPT),
    tool("sculpt_deck.circular_array", "Circular Array", "MESH_CIRCLE", SCULPT),
    # every mode: what usually needs a keyboard shortcut
    action("SCULPT_DECK_MT_all_actions", "All Actions", "THREE_DOTS", ANY_MODE),
    action("ed.undo", "Undo", "LOOP_BACK", ANY_MODE),
    action("ed.redo", "Redo", "LOOP_FORWARDS", ANY_MODE),
    action("sculpt_deck.toggle_n_panel", "Toggle Sidebar", "EVENT_N", ANY_MODE),
    action("screen.region_quadview", "Toggle Quad View", "IMGDISPLAY", ANY_MODE),
    action("ed.undo_history", "Undo History", "RECOVER_LAST", ANY_MODE),
    action("screen.repeat_last", "Repeat Last", "FILE_REFRESH", ANY_MODE),
    action("screen.redo_last", "Adjust Last Operation", "OPTIONS", ANY_MODE),
    action("VIEW3D_MT_object_mode_pie", "Mode Pie", "OBJECT_DATAMODE", ANY_MODE),
    action("object.editmode_toggle", "Toggle Edit Mode", "EDITMODE_HLT", ANY_MODE),
    action("VIEW3D_MT_view_pie", "View Pie", "VIEW3D", ANY_MODE),
    action("VIEW3D_MT_shading_pie", "Shading Pie", "SHADING_RENDERED", ANY_MODE),
    action("VIEW3D_MT_pivot_pie", "Pivot Pie", "PIVOT_BOUNDBOX", ANY_MODE),
    action("VIEW3D_MT_snap_pie", "Snap Pie", "SNAP_ON", ANY_MODE),
    action("VIEW3D_MT_orientations_pie", "Orientation Pie", "ORIENTATION_GLOBAL", ANY_MODE),
    action("view3d.view_selected", "Frame Selected", "ZOOM_SELECTED", ANY_MODE),
    action("view3d.view_all", "Frame All", "ZOOM_ALL", ANY_MODE),
    action("view3d.localview", "Local View", "HIDE_OFF", ANY_MODE),
    action("view3d.toggle_xray", "Toggle X-Ray", "XRAY", ANY_MODE),
    action("screen.screen_full_area", "Maximize Area", "FULLSCREEN_ENTER", ANY_MODE),
    action("wm.toolbar", "Tools Popup", "TOOL_SETTINGS", ANY_MODE),
    action("SCREEN_MT_user_menu", "Quick Favorites", "SOLO_ON", ANY_MODE),
    action("wm.search_menu", "Search", "VIEWZOOM", ANY_MODE),
    action("wm.save_mainfile", "Save", "FILE_TICK", ANY_MODE),
]


def add_actions(after: str, *entries: Action):
    """Add a part's own Actions to the catalog right after the Action `after`, the place they'd have if the catalog
    listed them, and build the Action Lists again"""
    index = next((i for i, entry in enumerate(CATALOG) if entry.idname == after), None)
    assert index is not None, f"{after} isn't in the catalog"
    for entry in entries:
        assert find(entry.idname) is None, f"{entry.idname} is in the catalog already"
    CATALOG[index + 1 : index + 1] = entries
    clear_cache()
    _check_catalog()


def remove_actions(*entries: Action):
    """Take out Actions added with add_actions, when their part unregisters"""
    CATALOG[:] = [entry for entry in CATALOG if not any(entry is removed for removed in entries)]
    clear_cache()


# idname -> Action, built when first needed and again after clear_cache()
_index: dict[str, Action] = {}


def find(idname: str) -> Action | None:
    """The catalog's Action with this idname"""
    if not _index:
        for entry in reversed(CATALOG):
            _index[entry.idname] = entry
    return _index.get(idname)


def mode_actions(mode: str) -> list[Action]:
    """The Actions of one mode only, in catalog order"""
    return [entry for entry in CATALOG if not entry.every_mode and entry.pie_slot and entry.applies_to(mode)]


def common_actions() -> list[Action]:
    """The Actions offered in every mode, in catalog order"""
    return [entry for entry in CATALOG if entry.every_mode and entry.pie_slot]


##
# Gestures and their Action Lists
##
@dataclass(frozen=True)
class Extra:
    """A choice of a surface's own, beside the catalog's Actions"""

    idname: str
    label: str
    description: str
    icon: str
    momentary: bool = False
    # an Action this choice stands in for, left out of the list where the choice is offered
    replaces: str = ""


EMPTY = Extra("NONE", "Empty", "Leave this slot empty", "BLANK1")
BLENDER_DEFAULT = Extra("DEFAULT", "Blender Default", "Do what Blender normally does for this button", "BLENDER")
NOTHING = Extra("NONE", "Nothing", "Ignore this button", "CANCEL")
PREVIOUS_BRUSH = Extra(
    "BRUSH_PREVIOUS",
    "Previous Brush",
    "Click switches to the previously used brush, hold uses it until released",
    "LOOP_BACK",
    momentary=True,
    replaces="sculpt_deck.brush_previous",
)
SPECIFIC_BRUSH = Extra(
    "BRUSH", "Specific Brush", "Click switches to the chosen brush, hold uses it until released", "BRUSH_DATA",
    momentary=True,
)
CUSTOM = Extra("CUSTOM", "Custom...", "Type the name of an operator or menu", "SCRIPT")


@dataclass(frozen=True)
class Gesture:
    # extras listed first; the first one is the default of a new binding
    extras: tuple[Extra, ...]
    # extras offered in modes with brushes, after the others
    brush_extras: tuple[Extra, ...] = ()
    momentary_only: bool = False
    resolution_changes: bool = True
    pie_slot: bool = False

    def offers(self, entry: Action) -> bool:
        return (
            (entry.momentary or not self.momentary_only)
            and (self.resolution_changes or not entry.resolution_change)
            and (entry.pie_slot or not self.pie_slot)
        )


_pen_click = Gesture((BLENDER_DEFAULT, NOTHING), (PREVIOUS_BRUSH, SPECIFIC_BRUSH), resolution_changes=False)

GESTURES: dict[str, Gesture] = {
    "WIDGET": Gesture((EMPTY,)),
    "PIE": Gesture((EMPTY,), pie_slot=True),
    "PEN_CLICK": _pen_click,
    # used until the button is released, so only Momentary choices
    "PEN_HOLD": replace(_pen_click, momentary_only=True),
    # mouse and touch, with the choices of a pen button click
    "DOUBLE_CLICK": _pen_click,
    "RIGHT_CLICK": _pen_click,
}


def action_list(gesture: str, mode: str) -> list[Action | Extra | None]:
    """The choices one Gesture offers in one mode; None separates groups: the surface's own extras, Actions a pie
    slot can't hold, the mode's own Actions, the Actions of every mode, then Custom"""
    rules = GESTURES[gesture]
    extras = list(rules.extras) + (list(rules.brush_extras) if mode in pen_brush_modes else [])
    replaced = {extra.replaces for extra in extras if extra.replaces}
    offered = [entry for entry in CATALOG if entry.applies_to(mode) and rules.offers(entry)
               and entry.idname not in replaced]
    groups = (
        [entry for entry in offered if not entry.pie_slot],
        [entry for entry in offered if entry.pie_slot and not entry.every_mode],
        [entry for entry in offered if entry.pie_slot and entry.every_mode],
        [CUSTOM],
    )
    choices: list[Action | Extra | None] = list(extras)
    for group in groups:
        if group:
            choices.append(None)
            choices += group
    return choices


def is_momentary(idname: str) -> bool:
    """Can be used while a button is held, and put back on release"""
    choice = find(idname) or next((extra for extra in _all_extras() if extra.idname == idname), None)
    return choice is not None and choice.momentary


def _all_extras():
    for rules in GESTURES.values():
        yield from rules.extras
        yield from rules.brush_extras


def enum_number(idname: str) -> int:
    """A number that stays with the identifier, so Blender's own saved copy of the preferences keeps its meaning
    when the catalog changes"""
    return 2 + zlib.crc32(idname.encode()) % 1_000_000


# dynamic enum items must stay referenced while Blender uses them
_enum_cache: dict[tuple[str, str], list] = {}
# lists handed to Blender before clear_cache(): kept, since Blender may still read the last items it was given
_retired: list[list] = []


def enum_items(gesture: str, mode: str) -> list:
    """A Gesture's Action List as Blender enum items; the first choice gets 0, an enum property's default"""
    key = (gesture, mode)
    if key not in _enum_cache:
        items: list = []
        for choice in action_list(gesture, mode):
            if choice is None:
                items.append(None)
                continue
            number = enum_number(choice.idname) if items else 0
            description = choice.description if isinstance(choice, Extra) else choice.idname
            items.append((choice.idname, choice.label, description, choice.icon, number))
        numbers = [item[4] for item in items if item]
        assert len(set(numbers)) == len(numbers), f"enum numbers collide in the {gesture} list of {mode}"
        _enum_cache[key] = items
    return _enum_cache[key]


def clear_cache():
    """After changing the catalog, so the lists are built again"""
    _retired.extend(_enum_cache.values())
    _enum_cache.clear()
    _index.clear()


def _check_catalog():
    """An Action placed again keeps its traits, in other modes"""
    seen: dict[str, Action] = {}
    for entry in CATALOG:
        earlier = seen.setdefault(entry.idname, entry)
        if earlier is not entry:
            assert replace(earlier, modes=entry.modes) == entry, f"{entry.idname} placed again with other traits"
            assert not set(earlier.modes) & set(entry.modes), f"{entry.idname} placed twice in one mode"


_check_catalog()
