"""Linear Array and Circular Array: their node groups, settings (`Scene.sculpt_deck_array`) and operators, and
their toolbar tools, headers and gizmos."""

from . import operators, tools


def register():
    operators.register()
    tools.register()


def unregister():
    tools.unregister()
    operators.unregister()
