# INPUT EVENTS
TWEAK = "TWEAK"
MOUSE = "MOUSE"
PEN = "PEN"
MMOUSE = "MIDDLEMOUSE"
LMOUSE = "LEFTMOUSE"
RMOUSE = "RIGHTMOUSE"
PRESS = "PRESS"
DCLICK = "DOUBLE_CLICK"

# OPERATOR RESPONSES
FINISHED = {"FINISHED"}
MODAL = {"RUNNING_MODAL"}
CANCEL = {"CANCELLED"}
PASSTHROUGH = {"PASS_THROUGH"}

# DICTIONARIES
# the 3D View keymaps the double click and right click actions join ("Image Paint" is Texture Paint Mode's)
viewport_keymaps = (
    "3D View",
    "Image Paint",
    "Grease Pencil",
)

input_mode_items = [
    ("ORBIT", "Rotate", "Rotate the viewport"),
    ("PAN", "Pan", "Move the viewport"),
    ("DOLLY", "Zoom", "Zoom in/out the viewport"),
]

position_items = [
    ("TOP", "Top", "Set Gizmo position to top of viewport"),
    ("RIGHT", "Right", "Set Gizmo position to right of viewport"),
    ("BOTTOM", "Bottom", "Set Gizmo position to bottom of viewport"),
    ("LEFT", "Left", "Set Gizmo position to left of viewport"),
]

pivot_items = [
    ("SURFACE", "Surface", "Sets the pivot position to the surface under the cursor."),
    (
        "ACTIVE",
        "Active Vertex",
        "Sets the pivot position to the active vertex position.",
    ),
    (
        "UNMASKED",
        "Unmasked",
        """
        Sets the pivot position to the average position of the unmasked
        vertices.
     """,
    ),
    ("ORIGIN", "Origin", "Sets the pivot to the origin of the sculpt."),
    (
        "BORDER",
        "Mask Border",
        "Sets the pivot position to the center of the border of the mask.",
    ),
]

pivot_icon_items = [
    ("BORDER", "PIVOT_BOUNDBOX"),
    ("ORIGIN", "PIVOT_CURSOR"),
    ("UNMASKED", "CLIPUV_HLT"),
    ("ACTIVE", "PIVOT_ACTIVE"),
    ("SURFACE", "PIVOT_MEDIAN"),
]

# context.mode -> tool_settings attribute holding the paint settings
paint_settings = {
    "SCULPT": "sculpt",
    "PAINT_VERTEX": "vertex_paint",
    "PAINT_WEIGHT": "weight_paint",
    "PAINT_TEXTURE": "image_paint",
    "SCULPT_CURVES": "curves_sculpt",
    "PAINT_GREASE_PENCIL": "gpencil_paint",
    "SCULPT_GREASE_PENCIL": "gpencil_sculpt_paint",
    "WEIGHT_GREASE_PENCIL": "gpencil_weight_paint",
    "VERTEX_GREASE_PENCIL": "gpencil_vertex_paint",
    # legacy grease pencil mode names
    "PAINT_GPENCIL": "gpencil_paint",
    "SCULPT_GPENCIL": "gpencil_sculpt_paint",
    "WEIGHT_GPENCIL": "gpencil_weight_paint",
    "VERTEX_GPENCIL": "gpencil_vertex_paint",
}


def paint_settings_name(mode: str) -> str | None:
    return paint_settings.get(mode)


brush_modes = list(paint_settings)

# context.mode -> object.mode_set mode, for modes new objects can enter
object_modes = {
    "OBJECT": "OBJECT",
    "EDIT_MESH": "EDIT",
    "SCULPT": "SCULPT",
    "PAINT_VERTEX": "VERTEX_PAINT",
    "PAINT_WEIGHT": "WEIGHT_PAINT",
    "PAINT_TEXTURE": "TEXTURE_PAINT",
}

# menu order; the numbers stay fixed so saved values keep their meaning
primitive_items = [
    ("SPHERE", "Sphere", "", "MESH_UVSPHERE", 0),
    ("ICOSPHERE", "Icosphere", "", "MESH_ICOSPHERE", 10),
    ("QUADSPHERE", "Quad Sphere", "", "SPHERE", 11),
    ("CUBE", "Cube", "", "MESH_CUBE", 1),
    ("CYLINDER", "Cylinder", "", "MESH_CYLINDER", 2),
    ("CONE", "Cone", "", "MESH_CONE", 3),
    ("CAPSULE", "Capsule", "", "MESH_CAPSULE", 7),
    ("TORUS", "Torus", "", "MESH_TORUS", 4),
    ("PLANE", "Plane", "", "MESH_GRID", 5),
    ("MONKEY", "Monkey", "", "MESH_MONKEY", 6),
]

# ACTION PIE
# modes with their own action pie; any other mode uses "OTHER"
pie_mode_items = [
    ("OBJECT", "Object Mode", ""),
    ("EDIT_MESH", "Edit Mode", ""),
    ("SCULPT", "Sculpt Mode", ""),
    ("PAINT_VERTEX", "Vertex Paint Mode", ""),
    ("PAINT_WEIGHT", "Weight Paint Mode", ""),
    ("PAINT_TEXTURE", "Texture Paint Mode", ""),
    ("PAINT_GREASE_PENCIL", "Grease Pencil Draw Mode", ""),
    ("OTHER", "Other Modes", "Every mode without its own pie"),
]

# mode names from before Blender 5.x, as stored in older settings
pie_mode_aliases = {"PAINT_GPENCIL": "PAINT_GREASE_PENCIL"}

# pie positions, in the order Blender fills a pie
pie_slot_names = ("Left", "Right", "Bottom", "Top", "Top Left", "Top Right", "Bottom Left", "Bottom Right")

# slots listed clockwise from the top, for the settings UI
pie_slot_display_order = (4, 6, 2, 8, 3, 7, 1, 5)


def pie_mode(mode: str) -> str:
    mode = pie_mode_aliases.get(mode, mode)
    return mode if any(mode == item[0] for item in pie_mode_items) else "OTHER"


# The Actions themselves and the Action Lists are in core/actions.py.

# toggles whose widget icon follows their state: context path, on icon, off icon
action_toggles = {
    "screen.screen_full_area": ("screen.show_fullscreen", "FULLSCREEN_EXIT", "FULLSCREEN_ENTER"),
    "screen.region_quadview": ("space_data.region_quadviews", "IMGDISPLAY", "MESH_PLANE"),
    "sculpt_deck.viewport_lock": ("region_data.lock_rotation", "LOCKED", "UNLOCKED"),
}

# operators that open a popup, run like menus from widget buttons
popup_actions = {"wm.toolbar", "wm.search_menu", "ed.undo_history", "screen.redo_last"}

# widget buttons only shown when the active object can use them
voxel_actions = {"object.voxel_size_edit", "object.voxel_remesh", "sculpt_deck.density_up", "sculpt_deck.density_down"}
multires_actions = {"sculpt_deck.increment_multires", "sculpt_deck.decrement_multires"}

WIDGET_SLOTS = 12

# initial widget buttons per mode
widget_defaults = {
    "OBJECT": ("ed.undo", "ed.redo", "VIEW3D_MT_add", "sculpt_deck.cycle_control_gizmo",
               "sculpt_deck.viewport_recenter", "screen.screen_full_area", "sculpt_deck.toggle_n_panel",
               "sculpt_deck.increment_multires", "sculpt_deck.decrement_multires", "SCULPT_DECK_MT_floating"),
    "EDIT_MESH": ("ed.undo", "ed.redo", "SCULPT_DECK_MT_add_mesh", "sculpt_deck.cycle_control_gizmo",
                  "sculpt_deck.viewport_recenter", "screen.screen_full_area", "sculpt_deck.toggle_n_panel",
                  "SCULPT_DECK_MT_floating"),
    "SCULPT": ("ed.undo", "ed.redo", "SCULPT_DECK_MT_add_mesh", "sculpt_deck.viewport_recenter",
               "sculpt_deck.toggle_n_panel", "object.voxel_size_edit", "object.voxel_remesh",
               "sculpt_deck.increment_multires", "sculpt_deck.decrement_multires", "sculpt_deck.brush_resize",
               "sculpt_deck.brush_strength", "SCULPT_DECK_MT_floating"),
    "PAINT_VERTEX": ("ed.undo", "ed.redo", "SCULPT_DECK_MT_add_mesh", "sculpt_deck.viewport_recenter",
                     "screen.screen_full_area", "sculpt_deck.toggle_n_panel", "sculpt_deck.brush_resize",
                     "sculpt_deck.brush_strength", "SCULPT_DECK_MT_floating"),
    "PAINT_WEIGHT": ("ed.undo", "ed.redo", "SCULPT_DECK_MT_add_mesh", "sculpt_deck.viewport_recenter",
                     "screen.screen_full_area", "sculpt_deck.toggle_n_panel", "sculpt_deck.brush_resize",
                     "sculpt_deck.brush_strength", "SCULPT_DECK_MT_floating"),
    "PAINT_TEXTURE": ("ed.undo", "ed.redo", "SCULPT_DECK_MT_add_mesh", "sculpt_deck.viewport_recenter",
                      "screen.screen_full_area", "sculpt_deck.toggle_n_panel", "sculpt_deck.brush_resize",
                      "sculpt_deck.brush_strength", "SCULPT_DECK_MT_floating"),
    "PAINT_GREASE_PENCIL": ("ed.undo", "ed.redo", "sculpt_deck.viewport_recenter", "screen.screen_full_area",
                            "sculpt_deck.toggle_n_panel", "sculpt_deck.brush_resize", "sculpt_deck.brush_strength",
                            "SCULPT_DECK_MT_floating"),
    "OTHER": ("ed.undo", "ed.redo", "sculpt_deck.viewport_recenter", "screen.screen_full_area",
              "sculpt_deck.toggle_n_panel", "SCULPT_DECK_MT_floating"),
}

# initial slots of a new pie, in pie order (left, right, bottom, top, ...)
menu_defaults = {
    "OBJECT": ("VIEW3D_MT_add", "object.delete", "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie",
               "object.duplicate_move", "SCULPT_DECK_MT_all_actions", "ed.undo_history", "screen.redo_last"),
    "EDIT_MESH": ("VIEW3D_MT_edit_mesh_select_mode", "VIEW3D_MT_edit_mesh_delete", "VIEW3D_MT_object_mode_pie",
                  "VIEW3D_MT_view_pie", "view3d.edit_mesh_extrude_move_normal", "SCULPT_DECK_MT_all_actions",
                  "VIEW3D_MT_edit_mesh_merge", "screen.redo_last"),
    "SCULPT": ("VIEW3D_AST_brush_sculpt", "VIEW3D_MT_mask", "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie",
               "VIEW3D_MT_face_sets", "SCULPT_DECK_MT_all_actions", "ed.undo_history", "SCULPT_DECK_MT_add_mesh"),
    "PAINT_VERTEX": ("VIEW3D_AST_brush_vertex_paint", "paint.sample_color", "VIEW3D_MT_object_mode_pie",
                     "VIEW3D_MT_view_pie", "paint.brush_colors_flip", "SCULPT_DECK_MT_all_actions", "", ""),
    "PAINT_WEIGHT": ("VIEW3D_AST_brush_weight_paint", "paint.weight_sample", "VIEW3D_MT_object_mode_pie",
                     "VIEW3D_MT_view_pie", "paint.weight_gradient", "SCULPT_DECK_MT_all_actions", "", ""),
    "PAINT_TEXTURE": ("VIEW3D_AST_brush_texture_paint", "paint.sample_color", "VIEW3D_MT_object_mode_pie",
                      "VIEW3D_MT_view_pie", "paint.brush_colors_flip", "SCULPT_DECK_MT_all_actions", "", ""),
    "PAINT_GREASE_PENCIL": ("VIEW3D_AST_brush_gpencil_paint", "GREASE_PENCIL_MT_layer_active",
                            "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie",
                            "grease_pencil.insert_blank_frame", "SCULPT_DECK_MT_all_actions", "", ""),
    "OTHER": ("ed.undo", "ed.redo", "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie", "",
              "SCULPT_DECK_MT_all_actions", "", ""),
}

# mouse and touch actions kept with the pen buttons of each mode, using the
# same actions as a pen button click
click_slots = ("right_click", "double_click")
click_defaults = {"right_click": "DEFAULT", "double_click": "screen.screen_full_area"}

menu_style_items = [
    ("float.radial", "Floating Radial", ""),
    ("fixed.bar", "Fixed Bar", ""),
]

menu_orientation_items = [
    ("HORIZONTAL", "Horizontal", ""),
    ("VERTICAL", "Vertical", ""),
]

control_gizmo_items = [
    ("none", "", "disable_gizmo"),
    ("translate", "show_gizmo_object_translate", ""),
    ("rotate", "show_gizmo_object_rotate", ""),
    ("scale", "show_gizmo_object_scale", ""),
]

gizmo_sets = {
    # ALL includes only the modes in this list
    "ALL": {
        "undoredo",
        "show_fullscreen",
        "region_quadviews",
        "snap_view",
        "n_panel",
        "lock_rotation",
    },
    "SCULPT": {
        "control_gizmo",
        "pivot_mode",
        "voxel_remesh",
        "multires",
        "brush_dynamics",
    },
    "OBJECT": {"control_gizmo", "multires"},
    "EDIT_MESH": {"control_gizmo"},
    "POSE": {},
    "PAINT_TEXTURE": {"brush_dynamics"},
    "PAINT_VERTEX": {"brush_dynamics"},
    "PAINT_WEIGHT": {"brush_dynamics"},
    "SCULPT_CURVES": {"brush_dynamics"},
    "PAINT_GREASE_PENCIL": {"brush_dynamics"},
    "SCULPT_GREASE_PENCIL": {"brush_dynamics"},
    "WEIGHT_GREASE_PENCIL": {"brush_dynamics"},
    "VERTEX_GREASE_PENCIL": {"brush_dynamics"},
    "WEIGHT_GPENCIL": {"brush_dynamics"},
    "VERTEX_GPENCIL": {"brush_dynamics"},
    "SCULPT_GPENCIL": {"brush_dynamics"},
    "PAINT_GPENCIL": {"brush_dynamics"},
}

# PEN BUTTONS
# pen side buttons arrive as mouse buttons with event.is_tablet set
pen_buttons = {
    "RIGHTMOUSE": "upper",
    "MIDDLEMOUSE": "lower",
}

pen_gestures = ("click", "hold")

# modes with brushes, where pen buttons can switch brushes
pen_brush_modes = {"SCULPT", "PAINT_VERTEX", "PAINT_WEIGHT", "PAINT_TEXTURE", "PAINT_GREASE_PENCIL"}

# the brush choices of a pen button, which switch brushes (see core/actions.py)
pen_brush_actions = {"BRUSH_PREVIOUS", "BRUSH"}


# brush directions that Invert Brush swaps
brush_direction_pairs = {
    "ADD": "SUBTRACT",
    "SUBTRACT": "ADD",
    "SMOOTH": "ENHANCE_DETAILS",
    "ENHANCE_DETAILS": "SMOOTH",
    "PINCH": "MAGNIFY",
    "MAGNIFY": "PINCH",
    "INFLATE": "DEFLATE",
    "DEFLATE": "INFLATE",
}

# pen buttons of a new setup; button 1 is the lower one (BTN_STYLUS),
# button 2 the upper one (BTN_STYLUS2)
pen_defaults = {
    "SCULPT": {
        "lower_click": "sculpt_deck.brush_invert",
        "lower_hold": "sculpt_deck.brush_invert",
        "upper_click": "BRUSH_PREVIOUS",
        "upper_hold": ("BRUSH", ("ESSENTIALS", "", "brushes/essentials_brushes-mesh_sculpt.blend/Brush/Smooth")),
    },
}

# what Blender does for each button by default, used when only one gesture is
# bound and the other should keep Blender's behavior
pen_default_context_menus = {
    "OBJECT": ("wm.call_menu", "VIEW3D_MT_object_context_menu"),
    "EDIT_MESH": ("wm.call_menu", "VIEW3D_MT_edit_mesh_context_menu"),
    "SCULPT": ("wm.call_panel", "VIEW3D_PT_sculpt_context_menu"),
    "PAINT_VERTEX": ("wm.call_panel", "VIEW3D_PT_paint_vertex_context_menu"),
    "PAINT_WEIGHT": ("wm.call_panel", "VIEW3D_PT_paint_weight_context_menu"),
    "PAINT_TEXTURE": ("wm.call_panel", "VIEW3D_PT_paint_texture_context_menu"),
    "PAINT_GREASE_PENCIL": ("wm.call_panel", "VIEW3D_PT_greasepencil_draw_context_menu"),
}
