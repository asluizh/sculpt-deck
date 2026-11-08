"""The add-on's parts, registered in order: core first, then the features, the Action Surfaces and navigation."""

from importlib import import_module
from importlib.util import find_spec

from . import core, features, surfaces

# Touch navigation can be removed as a unit (ADR 0001): deleting navigation/ is all it takes, it's registered only
# when it's there.
OPTIONAL = ("navigation",)

PARTS = [core, features, surfaces] + [
    import_module(f"{__name__}.{name}") for name in OPTIONAL if find_spec(f"{__name__}.{name}") is not None
]


def register():
    for part in PARTS:
        part.register()


def unregister():
    for part in reversed(PARTS):
        part.unregister()
