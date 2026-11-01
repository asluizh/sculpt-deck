# flake8: noqa
from . import actions, gizmo, local_transform, pen, touch


def register():
    actions.register()
    local_transform.register()
    touch.register()
    gizmo.register()
    pen.register()


def unregister():
    actions.unregister()
    touch.unregister()
    gizmo.unregister()
    pen.unregister()
    local_transform.unregister()
