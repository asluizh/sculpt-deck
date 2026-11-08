# The add-on is moving from the layered packages (ops, ui, utils) to parts grouped by feature (core, features,
# surfaces, navigation); both are registered until the move is done.
from . import core, features, ops, surfaces, ui, utils

# touch navigation, removable as a unit (ADR 0001): delete navigation/, this import and its two calls below
from . import navigation  # isort: skip


def register():
    ops.register()
    ui.register()
    utils.register()
    core.register()
    features.register()
    surfaces.register()
    navigation.register()


def unregister():
    navigation.unregister()
    surfaces.unregister()
    features.unregister()
    core.unregister()
    ops.unregister()
    ui.unregister()
    utils.unregister()
