###
# Gizmo structure update
#
# Refactor the gizmo structure to be more modular and easier to maintain.
# Gizmo context (UI, space, etc), state (2-mode, 3-mode, etc),
# layout (vertical, horizontal, etc)
# to be managed through inheritance.
###
from . import panel


def register():
    panel.register()


def unregister():
    panel.unregister()
