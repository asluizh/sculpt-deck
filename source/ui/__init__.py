###
# Gizmo structure update
#
# Refactor the gizmo structure to be more modular and easier to maintain.
# Gizmo context (UI, space, etc), state (2-mode, 3-mode, etc),
# layout (vertical, horizontal, etc)
# to be managed through inheritance.
###
from . import gizmo_group_2d, local_transform, panel


def register():
    gizmo_group_2d.register()
    panel.register()
    local_transform.register()


def unregister():
    local_transform.unregister()
    gizmo_group_2d.unregister()
    panel.unregister()
