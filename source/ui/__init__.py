###
# Gizmo structure update
#
# Refactor the gizmo structure to be more modular and easier to maintain.
# Gizmo context (UI, space, etc), state (2-mode, 3-mode, etc),
# layout (vertical, horizontal, etc)
# to be managed through inheritance.
###
from . import local_transform, panel


def register():
    panel.register()
    # the Mirror and array tools (features/) join the end of Local Transform's toolbar section
    local_transform.register()


def unregister():
    local_transform.unregister()
    panel.unregister()
