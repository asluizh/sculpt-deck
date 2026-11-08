"""Linear Array and Circular Array: their node groups, settings (`Scene.sculpt_deck_array`) and operators, and
their toolbar tools, headers and gizmos."""

# isort: off
# tools first: they import ops.local_transform, which imports the array helpers from operators. Importing
# operators first would load the ops package (for ops.drag) halfway through operators, and ops.local_transform
# would then find it only partly defined. Goes away once Local Transform and the drag helpers leave ops (#6).
from . import tools
from . import operators

# isort: on


def register():
    operators.register()
    tools.register()


def unregister():
    tools.unregister()
    operators.unregister()
