"""Resolution: Voxel Density Up/Down and Multires Level Up/Down, each a Resolution Change (see GLOSSARY.md).

Its settings are the Subdivision Limit and the Topology Mode; the Tool Options sidebar panel shows the limit."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import multires, panel, settings, voxel

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    settings,
    voxel,
    multires,
    panel,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
