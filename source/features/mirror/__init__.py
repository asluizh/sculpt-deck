"""Mirror: its node group (whose inputs are the Mirror settings) and operators, and its toolbar tool, header and
plane outlines."""

from . import operators, tools


def register():
    operators.register()
    tools.register()


def unregister():
    tools.unregister()
    operators.unregister()
