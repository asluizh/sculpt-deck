# flake8: noqa
from . import actions, array, gizmo, local_transform, mirror, pen, touch


def register():
    actions.register()
    local_transform.register()
    array.register()
    mirror.register()
    touch.register()
    gizmo.register()
    pen.register()


def unregister():
    actions.unregister()
    touch.unregister()
    gizmo.unregister()
    pen.unregister()
    mirror.unregister()
    array.unregister()
    local_transform.unregister()
