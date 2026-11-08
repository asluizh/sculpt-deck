"""Resolution: Voxel Density Up/Down and Multires Level Up/Down, each a Resolution Change (see GLOSSARY.md).

The Tool Options sidebar panel shows the Subdivision Limit. The Subdivision Limit and Topology Mode settings are still
add-on preferences (preferences.py); they move with the settings (#12)."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import multires, panel, voxel

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    voxel,
    multires,
    panel,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
