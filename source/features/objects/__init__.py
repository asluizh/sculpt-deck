"""Object actions: Add Mesh, Duplicate, Delete, Join and Fuse. Each adds or removes objects, so each is a Detour."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import add_mesh, combine, duplicate_delete

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    add_mesh,
    duplicate_delete,
    combine,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
