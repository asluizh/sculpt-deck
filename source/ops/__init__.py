# flake8: noqa
from . import actions, gizmo, pen


def register():
    actions.register()
    gizmo.register()
    pen.register()


def unregister():
    actions.unregister()
    gizmo.unregister()
    pen.unregister()
