# flake8: noqa
from . import actions, gizmo, pen, touch


def register():
    actions.register()
    touch.register()
    gizmo.register()
    pen.register()


def unregister():
    actions.unregister()
    touch.unregister()
    gizmo.unregister()
    pen.unregister()
