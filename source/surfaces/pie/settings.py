"""The Action Pie's settings: the initial slots of each mode."""

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
