# The add-on is moving from the layered packages (ops, ui, utils) to parts grouped by feature (core, features,
# surfaces, navigation); both are registered until the move is done.
from . import core, features, navigation, ops, surfaces, ui, utils


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
