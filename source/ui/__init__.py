###
# Gizmo structure update
#
# Refactor the gizmo structure to be more modular and easier to maintain.
# Gizmo context (UI, space, etc), state (2-mode, 3-mode, etc),
# layout (vertical, horizontal, etc)
# to be managed through inheritance.
###
from . import array, gizmo_group_2d, local_transform, mirror, panel


def register():
    gizmo_group_2d.register()
    panel.register()
    local_transform.register()
    # tools join the end of Local Transform's toolbar section, in this order
    mirror.register()
    array.register()


def unregister():
    mirror.unregister()
    array.unregister()
    local_transform.unregister()
    gizmo_group_2d.unregister()
    panel.unregister()
