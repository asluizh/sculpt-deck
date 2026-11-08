"""Brush: Previous Brush and Invert Brush, Brush Size and Brush Strength (Blender's radial control), Stroke Method,
and the brush history that Previous Brush and the pen buttons read."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import history, operators, radial_control, stroke_method

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    history,
    operators,
    radial_control,
    stroke_method,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
