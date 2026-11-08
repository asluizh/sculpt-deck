"""Local Transform and Apply Scale: the operators, the settings (`Scene.sculpt_deck_local_transform`), and the
toolbar tool, header and 3D gizmos."""

from . import operators, tools


def register():
    operators.register()
    tools.register()


def unregister():
    tools.unregister()
    operators.unregister()
