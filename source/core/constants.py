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

# mode names from before Blender 5.x, as stored in older settings
pie_mode_aliases = {"PAINT_GPENCIL": "PAINT_GREASE_PENCIL"}


def pie_mode(mode: str) -> str:
    mode = pie_mode_aliases.get(mode, mode)
    return mode if any(mode == item[0] for item in pie_mode_items) else "OTHER"


# modes with brushes, where pen buttons can switch brushes
pen_brush_modes = {"SCULPT", "PAINT_VERTEX", "PAINT_WEIGHT", "PAINT_TEXTURE", "PAINT_GREASE_PENCIL"}
