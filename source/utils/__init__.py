from . import brush, keymaps
from .overlay import Overlay

ov = Overlay()


def register():
    keymaps.register()
    brush.register()
    ov.drawUI()


def unregister():
    ov.clear_overlays()
    brush.unregister()
    keymaps.unregister()
