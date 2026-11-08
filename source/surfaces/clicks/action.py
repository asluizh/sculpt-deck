"""Double click and right click: per mode, the actions of a pen button click, for mouse and touch."""

import bpy
from bpy.types import Operator

from ...core.constants import FINISHED, LMOUSE, PASSTHROUGH, PEN, PRESS
from ...core.preferences import preferences
from ..pen.button import BindingRunner

RMOUSE = "RIGHTMOUSE"

DCLICK = "DOUBLE_CLICK"

# the 3D View keymaps the double click and right click actions join ("Image Paint" is Texture Paint Mode's)
viewport_keymaps = (
    "3D View",
    "Image Paint",
    "Grease Pencil",
)


def is_touch(event):
    return event.pressure in [0.0, 1.0]


def click_binding(context, slot: str):
    """The right click or double click action for the current mode, or None to leave the click to Blender"""
    prefs = preferences()
    if not getattr(prefs, "enable_" + slot):
        return None
    pen_set = prefs.getPenSet(context.mode)
    binding = getattr(pen_set, slot) if pen_set is not None else None
    if binding is None or binding.action == "DEFAULT":
        return None
    return binding


class ClickAction(BindingRunner):
    slot = ""

    def run(self, context):
        binding = click_binding(context, self.slot)
        if binding is None:
            return PASSTHROUGH
        self.mode = context.mode
        self.run_action(context, binding)
        return FINISHED

    def execute(self, context):
        return self.run(context)


class SCULPT_DECK_OT_right_click_action(ClickAction, Operator):
    """Run the right click action set for this mode"""

    bl_label = "Right Click Action"
    bl_idname = "sculpt_deck.rc_action"
    bl_options = {"INTERNAL"}
    slot = "right_click"

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def invoke(self, context, event):
        if event.type not in [RMOUSE]:
            return PASSTHROUGH
        # pen buttons are handled by sculpt_deck.pen_button
        if event.is_tablet:
            return PASSTHROUGH
        if event.value == "DOUBLE_CLICK":
            return PASSTHROUGH
        return self.run(context)


class SCULPT_DECK_OT_double_click_action(ClickAction, Operator):
    """Run the double click action set for this mode"""

    bl_label = "Double Click Action"
    bl_idname = "sculpt_deck.dt_action"
    bl_options = {"INTERNAL"}
    slot = "double_click"

    @classmethod
    def poll(cls, context):
        # its actions are the 3D View's, per object mode
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def invoke(self, context, event):
        if event.type not in [PEN, LMOUSE]:
            return PASSTHROUGH
        if not is_touch(event):
            return PASSTHROUGH
        if event.value != "DOUBLE_CLICK":
            return PASSTHROUGH
        return self.run(context)


classes = (
    SCULPT_DECK_OT_right_click_action,
    SCULPT_DECK_OT_double_click_action,
)

keymap_items = []


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # in the 3D View keymaps, beside the touch press of the object tap (features/) and navigation
    wm = bpy.context.window_manager
    for kmap in wm.keyconfigs["Blender"].keymaps:
        if kmap.name not in viewport_keymaps:
            continue
        km = wm.keyconfigs.addon.keymaps.new(name=kmap.name, space_type=kmap.space_type, region_type=kmap.region_type)
        keymap_items.append((km, km.keymap_items.new("sculpt_deck.dt_action", LMOUSE, DCLICK)))
        keymap_items.append((km, km.keymap_items.new("sculpt_deck.rc_action", RMOUSE, PRESS)))


def unregister():
    for km, kmi in keymap_items:
        km.keymap_items.remove(kmi)
    keymap_items.clear()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
