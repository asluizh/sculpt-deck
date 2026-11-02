from . import brush, keymaps, settings
from .overlay import Overlay

ov = Overlay()


def register():
    keymaps.register()
    brush.register()
    settings.register()
    ov.drawUI()


def unregister():
    ov.clear_overlays()
    settings.unregister()
    brush.unregister()
    keymaps.unregister()
