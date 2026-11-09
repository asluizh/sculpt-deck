"""Constants several parts share: event and operator result names, and the modes. A constant only one part uses
lives with that part."""

# INPUT EVENTS
PEN = "PEN"
LMOUSE = "LEFTMOUSE"
PRESS = "PRESS"

# OPERATOR RESPONSES
FINISHED = {"FINISHED"}
MODAL = {"RUNNING_MODAL"}
CANCEL = {"CANCELLED"}
PASSTHROUGH = {"PASS_THROUGH"}

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

# context.mode values where actions that change objects (transforms, modifiers and their settings) are offered: their undo steps hold
# them, or a Scene Checkpoint does. Not Edit Mode, whose undo steps hold only the mesh being edited, and push
# nothing else even from Python, so undo and redo couldn't take such a change back (#33)
object_data_modes = {mode for mode in object_modes if mode != "EDIT_MESH"}

# modes with their own Action slots and pen buttons; any other mode uses "OTHER"
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

def pie_mode(mode: str) -> str:
    return mode if any(mode == item[0] for item in pie_mode_items) else "OTHER"


# modes with brushes, where pen buttons can switch brushes
pen_brush_modes = {"SCULPT", "PAINT_VERTEX", "PAINT_WEIGHT", "PAINT_TEXTURE", "PAINT_GREASE_PENCIL"}
