"""Keymap entries of touch navigation: the touch press in the 3D View and Grease Pencil keymaps (beside the object
tap's, see features/object_tap), and Alt T for Toggle Touch Controls."""

import bpy

from ..utils.constants import LMOUSE, PRESS

KEYMAPS = ("3D View", "Grease Pencil")
keymap_items = []


def register():
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name="3D View", space_type="VIEW_3D")
    keymap_items.append((km, km.keymap_items.new("sculpt_deck.toggle_touch", type="T", value=PRESS, alt=True)))

    for kmap in wm.keyconfigs["Blender"].keymaps:
        if kmap.name not in KEYMAPS:
            continue
        km = wm.keyconfigs.addon.keymaps.new(name=kmap.name, space_type=kmap.space_type, region_type=kmap.region_type)
        keymap_items.append((km, km.keymap_items.new("sculpt_deck.view_ops_3d", LMOUSE, PRESS)))


def unregister():
    for km, kmi in keymap_items:
        km.keymap_items.remove(kmi)
    keymap_items.clear()
