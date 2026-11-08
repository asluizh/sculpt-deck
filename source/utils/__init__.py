from . import keymaps, settings
from .overlay import Overlay

ov = Overlay()


def register():
    keymaps.register()
    settings.register()
    ov.drawUI()


def unregister():
    ov.clear_overlays()
    settings.unregister()
    keymaps.unregister()
