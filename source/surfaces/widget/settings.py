"""The Widget's settings: its layout, which buttons show, and the initial buttons of each mode."""

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

position_items = [
    ("TOP", "Top", "Set Gizmo position to top of viewport"),
    ("RIGHT", "Right", "Set Gizmo position to right of viewport"),
    ("BOTTOM", "Bottom", "Set Gizmo position to bottom of viewport"),
    ("LEFT", "Left", "Set Gizmo position to left of viewport"),
]

menu_style_items = [
    ("float.radial", "Floating Radial", ""),
    ("fixed.bar", "Fixed Bar", ""),
]

menu_orientation_items = [
    ("HORIZONTAL", "Horizontal", ""),
    ("VERTICAL", "Vertical", ""),
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
