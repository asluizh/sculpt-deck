# flake8: noqa
from . import actions, array, gizmo, local_transform, pen, touch


def register():
    actions.register()
    local_transform.register()
    array.register()
    touch.register()
    gizmo.register()
    pen.register()


def unregister():
    actions.unregister()
    touch.unregister()
    gizmo.unregister()
    pen.unregister()
    array.unregister()
    local_transform.unregister()
