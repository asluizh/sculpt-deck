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
flat_modes = [
    "Node Editor",
    "Image",
    "Image Paint",
    "UV Editor",
    "View2D",
]

top_level_names = (
    "Node Editor",
    "UV Editor",
    "Image Editor",
    "Image Paint",
    "3D View",
    "Image",
    "View2D",
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

primitive_items = [
    ("SPHERE", "Sphere", "", "MESH_UVSPHERE", 0),
    ("CUBE", "Cube", "", "MESH_CUBE", 1),
    ("CYLINDER", "Cylinder", "", "MESH_CYLINDER", 2),
    ("CONE", "Cone", "", "MESH_CONE", 3),
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


# Popular actions for the pie and the widget buttons, as (idname, label, icon).
# An idname is an operator, a menu (_MT_; opened as a pie when it ends in _pie)
# or a brush asset shelf (_AST_). Common actions are offered in every mode and
# cover what usually needs a keyboard shortcut.
pie_common_actions = [
    ("ed.undo", "Undo", "LOOP_BACK"),
    ("ed.redo", "Redo", "LOOP_FORWARDS"),
    ("touchview.viewport_recenter", "Recenter on Selected", "CURSOR"),
    ("touchview.toggle_n_panel", "Toggle Sidebar", "EVENT_N"),
    ("touchview.viewport_lock", "Toggle Rotation Lock", "LOCKED"),
    ("screen.region_quadview", "Toggle Quad View", "IMGDISPLAY"),
    ("touchview.toggle_touch", "Toggle Touch Controls", "VIEW_PAN"),
    ("ed.undo_history", "Undo History", "RECOVER_LAST"),
    ("screen.repeat_last", "Repeat Last", "FILE_REFRESH"),
    ("screen.redo_last", "Adjust Last Operation", "OPTIONS"),
    ("VIEW3D_MT_object_mode_pie", "Mode Pie", "OBJECT_DATAMODE"),
    ("object.editmode_toggle", "Toggle Edit Mode", "EDITMODE_HLT"),
    ("VIEW3D_MT_view_pie", "View Pie", "VIEW3D"),
    ("VIEW3D_MT_shading_pie", "Shading Pie", "SHADING_RENDERED"),
    ("VIEW3D_MT_pivot_pie", "Pivot Pie", "PIVOT_BOUNDBOX"),
    ("VIEW3D_MT_snap_pie", "Snap Pie", "SNAP_ON"),
    ("VIEW3D_MT_orientations_pie", "Orientation Pie", "ORIENTATION_GLOBAL"),
    ("view3d.view_selected", "Frame Selected", "ZOOM_SELECTED"),
    ("view3d.view_all", "Frame All", "ZOOM_ALL"),
    ("view3d.localview", "Local View", "HIDE_OFF"),
    ("view3d.toggle_xray", "Toggle X-Ray", "XRAY"),
    ("screen.screen_full_area", "Maximize Area", "FULLSCREEN_ENTER"),
    ("wm.toolbar", "Tools Popup", "TOOL_SETTINGS"),
    ("SCREEN_MT_user_menu", "Quick Favorites", "SOLO_ON"),
    ("wm.search_menu", "Search", "VIEWZOOM"),
    ("wm.save_mainfile", "Save", "FILE_TICK"),
]

pie_mode_actions = {
    "OBJECT": [
        ("VIEW3D_MT_add", "Add", "ADD"),
        ("object.delete", "Delete", "X"),
        ("object.duplicate_move", "Duplicate", "DUPLICATE"),
        ("object.duplicate_move_linked", "Duplicate Linked", "LINKED"),
        ("object.join", "Join", "OBJECT_DATA"),
        ("touchview.fuse_selected", "Fuse Selected", "MOD_BOOLEAN"),
        ("touchview.cycle_control_gizmo", "Cycle Object Gizmo", "ORIENTATION_LOCAL"),
        ("touchview.increment_multires", "Multires Level Up", "TRIA_UP"),
        ("touchview.decrement_multires", "Multires Level Down", "TRIA_DOWN"),
        ("object.select_all", "Select All (Toggle)", "RESTRICT_SELECT_OFF"),
        ("object.hide_view_set", "Hide Selected", "HIDE_ON"),
        ("object.hide_view_clear", "Reveal Hidden", "HIDE_OFF"),
        ("object.shade_smooth", "Shade Smooth", "SMOOTHCURVE"),
        ("object.shade_auto_smooth", "Shade Auto Smooth", "MOD_SMOOTH"),
        ("object.shade_flat", "Shade Flat", "MESH_PLANE"),
        ("VIEW3D_MT_object_apply", "Apply", "CHECKMARK"),
        ("VIEW3D_MT_object_parent", "Parent", "ORIENTATION_PARENT"),
        ("VIEW3D_MT_snap", "Snap", "SNAP_ON"),
        ("object.origin_set", "Set Origin", "OBJECT_ORIGIN"),
        ("VIEW3D_MT_object_context_menu", "Context Menu", "COLLAPSEMENU"),
    ],
    "EDIT_MESH": [
        ("VIEW3D_MT_edit_mesh_select_mode", "Select Mode", "VERTEXSEL"),
        ("TOUCHVIEW_MT_add_mesh", "Add Mesh", "ADD"),
        ("touchview.cycle_control_gizmo", "Cycle Object Gizmo", "ORIENTATION_LOCAL"),
        ("mesh.select_all", "Select All (Toggle)", "RESTRICT_SELECT_OFF"),
        ("mesh.select_linked", "Select Linked", "LINKED"),
        ("mesh.select_more", "Select More", "ADD"),
        ("mesh.select_less", "Select Less", "REMOVE"),
        ("view3d.edit_mesh_extrude_move_normal", "Extrude", "EXPORT"),
        ("mesh.inset", "Inset Faces", "FULLSCREEN_EXIT"),
        ("mesh.bevel", "Bevel", "MOD_BEVEL"),
        ("mesh.loopcut_slide", "Loop Cut", "MOD_EDGESPLIT"),
        ("mesh.knife_tool", "Knife", "MOD_TRIANGULATE"),
        ("mesh.subdivide", "Subdivide", "MOD_SUBSURF"),
        ("mesh.edge_face_add", "Make Edge/Face", "FACESEL"),
        ("VIEW3D_MT_edit_mesh_merge", "Merge", "AUTOMERGE_ON"),
        ("VIEW3D_MT_edit_mesh_delete", "Delete", "X"),
        ("mesh.hide", "Hide Selected", "HIDE_ON"),
        ("mesh.reveal", "Reveal Hidden", "HIDE_OFF"),
        ("VIEW3D_MT_edit_mesh_context_menu", "Context Menu", "COLLAPSEMENU"),
    ],
    "SCULPT": [
        ("VIEW3D_AST_brush_sculpt", "Brushes", "BRUSHES_ALL"),
        ("TOUCHVIEW_MT_add_mesh", "Add Mesh", "ADD"),
        ("touchview.brush_resize", "Brush Size", "ANTIALIASED"),
        ("touchview.brush_strength", "Brush Strength", "SMOOTHCURVE"),
        ("touchview.join_selected", "Join Selected", "OBJECT_DATA"),
        ("touchview.fuse_selected", "Fuse Selected", "MOD_BOOLEAN"),
        ("VIEW3D_MT_mask", "Mask", "MOD_MASK"),
        ("VIEW3D_MT_sculpt_mask_edit_pie", "Mask Edit Pie", "MOD_MASK"),
        ("paint.mask_flood_fill", "Clear Mask", "CLIPUV_DEHLT"),
        ("VIEW3D_MT_face_sets", "Face Sets", "FACE_MAPS"),
        ("VIEW3D_MT_sculpt_face_sets_edit_pie", "Face Sets Edit Pie", "FACE_MAPS"),
        ("VIEW3D_MT_sculpt_automasking_pie", "Auto-Masking Pie", "MOD_MASK"),
        ("paint.visibility_invert", "Invert Visibility", "HIDE_ON"),
        ("object.voxel_remesh", "Voxel Remesh", "MOD_REMESH"),
        ("object.voxel_size_edit", "Edit Voxel Size", "MESH_GRID"),
        ("touchview.density_up", "Voxel Density Up", "TRIA_UP"),
        ("touchview.density_down", "Voxel Density Down", "TRIA_DOWN"),
        ("touchview.increment_multires", "Multires Level Up", "TRIA_UP"),
        ("touchview.decrement_multires", "Multires Level Down", "TRIA_DOWN"),
        ("touchview.cycle_control_gizmo", "Cycle Object Gizmo", "ORIENTATION_LOCAL"),
        ("object.quadriflow_remesh", "QuadriFlow Remesh", "MOD_REMESH"),
        ("sculpt.dynamic_topology_toggle", "Toggle Dyntopo", "MESH_DATA"),
        ("VIEW3D_MT_sculpt", "Sculpt Menu", "SCULPTMODE_HLT"),
    ],
    "PAINT_VERTEX": [
        ("VIEW3D_AST_brush_vertex_paint", "Brushes", "BRUSHES_ALL"),
        ("TOUCHVIEW_MT_add_mesh", "Add Mesh", "ADD"),
        ("touchview.brush_resize", "Brush Size", "ANTIALIASED"),
        ("touchview.brush_strength", "Brush Strength", "SMOOTHCURVE"),
        ("paint.sample_color", "Sample Color", "EYEDROPPER"),
        ("paint.brush_colors_flip", "Swap Colors", "ARROW_LEFTRIGHT"),
        ("paint.vertex_color_set", "Fill with Color", "COLOR"),
        ("paint.vertex_color_invert", "Invert Colors", "GROUP_VCOL"),
        ("paint.vertex_color_smooth", "Smooth Colors", "MOD_SMOOTH"),
        ("VIEW3D_MT_paint_vertex", "Paint Menu", "VPAINT_HLT"),
    ],
    "PAINT_WEIGHT": [
        ("VIEW3D_AST_brush_weight_paint", "Brushes", "BRUSHES_ALL"),
        ("TOUCHVIEW_MT_add_mesh", "Add Mesh", "ADD"),
        ("touchview.brush_resize", "Brush Size", "ANTIALIASED"),
        ("touchview.brush_strength", "Brush Strength", "SMOOTHCURVE"),
        ("paint.weight_sample", "Sample Weight", "EYEDROPPER"),
        ("paint.weight_sample_group", "Sample Group", "EYEDROPPER"),
        ("paint.weight_gradient", "Weight Gradient", "IPO_EASE_IN_OUT"),
        ("paint.weight_set", "Set Weight", "WPAINT_HLT"),
        ("VIEW3D_MT_paint_weight_lock", "Locks", "LOCKED"),
        ("VIEW3D_MT_paint_weight", "Weights Menu", "WPAINT_HLT"),
    ],
    "PAINT_TEXTURE": [
        ("VIEW3D_AST_brush_texture_paint", "Brushes", "BRUSHES_ALL"),
        ("TOUCHVIEW_MT_add_mesh", "Add Mesh", "ADD"),
        ("touchview.brush_resize", "Brush Size", "ANTIALIASED"),
        ("touchview.brush_strength", "Brush Strength", "SMOOTHCURVE"),
        ("paint.sample_color", "Sample Color", "EYEDROPPER"),
        ("paint.brush_colors_flip", "Swap Colors", "ARROW_LEFTRIGHT"),
        ("paint.add_texture_paint_slot", "Add Paint Slot", "IMAGE_DATA"),
        ("image.save_all_modified", "Save All Images", "FILE_TICK"),
    ],
    "PAINT_GREASE_PENCIL": [
        ("VIEW3D_AST_brush_gpencil_paint", "Brushes", "BRUSHES_ALL"),
        ("touchview.brush_resize", "Brush Size", "ANTIALIASED"),
        ("touchview.brush_strength", "Brush Strength", "SMOOTHCURVE"),
        ("GREASE_PENCIL_MT_layer_active", "Active Layer", "OUTLINER_DATA_GP_LAYER"),
        ("grease_pencil.layer_add", "Add Layer", "ADD"),
        ("grease_pencil.insert_blank_frame", "Insert Blank Frame", "KEYFRAME"),
        ("grease_pencil.frame_duplicate", "Duplicate Frame", "DUPLICATE"),
        ("grease_pencil.interpolate", "Interpolate", "IPO_EASE_IN_OUT"),
        ("grease_pencil.interpolate_sequence", "Interpolate Sequence", "IPO_EASE_IN_OUT"),
    ],
}

# only offered for widget buttons, a pie can't open itself
widget_only_actions = [
    ("TOUCHVIEW_MT_floating", "Action Pie", "SETTINGS"),
]

pie_actions = {idname: (label, icon) for idname, label, icon in pie_common_actions + widget_only_actions}
for _actions in pie_mode_actions.values():
    pie_actions.update({idname: (label, icon) for idname, label, icon in _actions})

# toggles whose widget icon follows their state: context path, on icon, off icon
action_toggles = {
    "screen.screen_full_area": ("screen.show_fullscreen", "FULLSCREEN_EXIT", "FULLSCREEN_ENTER"),
    "screen.region_quadview": ("space_data.region_quadviews", "IMGDISPLAY", "MESH_PLANE"),
    "touchview.viewport_lock": ("region_data.lock_rotation", "LOCKED", "UNLOCKED"),
}

# operators that open a popup, run like menus from widget buttons
popup_actions = {"wm.toolbar", "wm.search_menu", "ed.undo_history", "screen.redo_last"}

# widget buttons only shown when the active object can use them
voxel_actions = {"object.voxel_size_edit", "object.voxel_remesh", "touchview.density_up", "touchview.density_down"}
multires_actions = {"touchview.increment_multires", "touchview.decrement_multires"}

WIDGET_SLOTS = 12

# initial widget buttons per mode
widget_defaults = {
    "OBJECT": ("ed.undo", "ed.redo", "VIEW3D_MT_add", "touchview.cycle_control_gizmo",
               "touchview.viewport_recenter", "screen.screen_full_area", "touchview.toggle_n_panel",
               "touchview.increment_multires", "touchview.decrement_multires", "TOUCHVIEW_MT_floating"),
    "EDIT_MESH": ("ed.undo", "ed.redo", "TOUCHVIEW_MT_add_mesh", "touchview.cycle_control_gizmo",
                  "touchview.viewport_recenter", "screen.screen_full_area", "touchview.toggle_n_panel",
                  "TOUCHVIEW_MT_floating"),
    "SCULPT": ("ed.undo", "ed.redo", "TOUCHVIEW_MT_add_mesh", "touchview.viewport_recenter",
               "touchview.toggle_n_panel", "object.voxel_size_edit", "object.voxel_remesh",
               "touchview.increment_multires", "touchview.decrement_multires", "touchview.brush_resize",
               "touchview.brush_strength", "TOUCHVIEW_MT_floating"),
    "PAINT_VERTEX": ("ed.undo", "ed.redo", "TOUCHVIEW_MT_add_mesh", "touchview.viewport_recenter",
                     "screen.screen_full_area", "touchview.toggle_n_panel", "touchview.brush_resize",
                     "touchview.brush_strength", "TOUCHVIEW_MT_floating"),
    "PAINT_WEIGHT": ("ed.undo", "ed.redo", "TOUCHVIEW_MT_add_mesh", "touchview.viewport_recenter",
                     "screen.screen_full_area", "touchview.toggle_n_panel", "touchview.brush_resize",
                     "touchview.brush_strength", "TOUCHVIEW_MT_floating"),
    "PAINT_TEXTURE": ("ed.undo", "ed.redo", "TOUCHVIEW_MT_add_mesh", "touchview.viewport_recenter",
                      "screen.screen_full_area", "touchview.toggle_n_panel", "touchview.brush_resize",
                      "touchview.brush_strength", "TOUCHVIEW_MT_floating"),
    "PAINT_GREASE_PENCIL": ("ed.undo", "ed.redo", "touchview.viewport_recenter", "screen.screen_full_area",
                            "touchview.toggle_n_panel", "touchview.brush_resize", "touchview.brush_strength",
                            "TOUCHVIEW_MT_floating"),
    "OTHER": ("ed.undo", "ed.redo", "touchview.viewport_recenter", "screen.screen_full_area",
              "touchview.toggle_n_panel", "TOUCHVIEW_MT_floating"),
}

# initial slots of a new pie, in pie order (left, right, bottom, top, ...)
menu_defaults = {
    "OBJECT": ("VIEW3D_MT_add", "object.delete", "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie",
               "object.duplicate_move", "object.shade_auto_smooth", "ed.undo_history", "screen.redo_last"),
    "EDIT_MESH": ("VIEW3D_MT_edit_mesh_select_mode", "VIEW3D_MT_edit_mesh_delete", "VIEW3D_MT_object_mode_pie",
                  "VIEW3D_MT_view_pie", "view3d.edit_mesh_extrude_move_normal", "mesh.loopcut_slide",
                  "VIEW3D_MT_edit_mesh_merge", "screen.redo_last"),
    "SCULPT": ("VIEW3D_AST_brush_sculpt", "VIEW3D_MT_mask", "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie",
               "VIEW3D_MT_face_sets", "object.voxel_remesh", "ed.undo_history", "TOUCHVIEW_MT_add_mesh"),
    "PAINT_VERTEX": ("VIEW3D_AST_brush_vertex_paint", "paint.sample_color", "VIEW3D_MT_object_mode_pie",
                     "VIEW3D_MT_view_pie", "paint.brush_colors_flip", "", "", ""),
    "PAINT_WEIGHT": ("VIEW3D_AST_brush_weight_paint", "paint.weight_sample", "VIEW3D_MT_object_mode_pie",
                     "VIEW3D_MT_view_pie", "paint.weight_gradient", "", "", ""),
    "PAINT_TEXTURE": ("VIEW3D_AST_brush_texture_paint", "paint.sample_color", "VIEW3D_MT_object_mode_pie",
                      "VIEW3D_MT_view_pie", "paint.brush_colors_flip", "", "", ""),
    "PAINT_GREASE_PENCIL": ("VIEW3D_AST_brush_gpencil_paint", "GREASE_PENCIL_MT_layer_active",
                            "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie",
                            "grease_pencil.insert_blank_frame", "", "", ""),
    "OTHER": ("ed.undo", "ed.redo", "VIEW3D_MT_object_mode_pie", "VIEW3D_MT_view_pie", "", "", "", ""),
}

double_click_items = [
    ("object.transfer_mode", "Transfer Mode", ""),
    ("touchview.toggle_touch", "Toggle Touch View", ""),
    ("view3d.localview", "Toggle Local View", ""),
    ("wm.window_fullscreen_toggle", "Toggle Full Screen", ""),
]

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
    "NODE_EDITOR": {"control_gizmo"},
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

# modes that can have pen button bindings
pen_mode_items = [
    ("OBJECT", "Object", "Object Mode bindings"),
    ("SCULPT", "Sculpt", "Sculpt Mode bindings"),
]

# modes whose bindings may switch brushes
pen_brush_modes = {"SCULPT"}

pen_action_items = [
    ("DEFAULT", "Blender Default", "Do what Blender normally does for this button", "BLENDER", 0),
    ("NONE", "Nothing", "Ignore this button", "CANCEL", 1),
    ("PIE", "Touchview Action Pie", "Open the Touchview action pie menu", "SETTINGS", 2),
    ("QUICK_FAVORITES", "Quick Favorites", "Open Blender's Quick Favorites menu", "SOLO_ON", 3),
    ("OPERATOR", "Custom Operator", "Run an operator by its name, e.g. object.shade_smooth", "SCRIPT", 4),
]

pen_brush_action_items = [
    (
        "BRUSH_PREVIOUS",
        "Previous Brush",
        "Click switches to the previously used brush, hold uses it until released",
        "LOOP_BACK",
        5,
    ),
    ("BRUSH", "Specific Brush", "Click switches to the chosen brush, hold uses it until released", "BRUSH_DATA", 6),
]

pen_brush_actions = {"BRUSH_PREVIOUS", "BRUSH"}

# what Blender does for each button by default, used when only one gesture is
# bound and the other should keep Blender's behavior
pen_default_context_menus = {
    "OBJECT": ("wm.call_menu", "VIEW3D_MT_object_context_menu"),
    "SCULPT": ("wm.call_panel", "VIEW3D_PT_sculpt_context_menu"),
}
