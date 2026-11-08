from . import core, features, surfaces

# touch navigation, removable as a unit (ADR 0001): delete navigation/, this import and its two calls below
from . import navigation  # isort: skip


def register():
    core.register()
    features.register()
    surfaces.register()
    navigation.register()


def unregister():
    navigation.unregister()
    surfaces.unregister()
    features.unregister()
    core.unregister()
