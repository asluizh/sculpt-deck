"""A left-click drag scrolls UI lists and menus, as a middle-click drag does, so a pen or a finger can scroll them."""

import bpy

from ...utils.constants import LMOUSE, PRESS

# the keymap items this part added, removed again on unregister
added_keymaps = []


def register():
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig is None:
        return  # no add-on keyconfig in background mode
    km = keyconfig.keymaps.new(name="View2D Buttons List", space_type="EMPTY")
    kmi = km.keymap_items.new("view2d.pan", LMOUSE, PRESS)
    added_keymaps.append((km, kmi))


def unregister():
    for km, kmi in added_keymaps:
        km.keymap_items.remove(kmi)
    added_keymaps.clear()
