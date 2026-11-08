# type: ignore
"""The Viewport Options sidebar panel: flip the tools region, quad view, lock to cursor and lock rotation."""

import bpy
from bpy.types import Panel

from ...core.ui import SculptDeckPanel


class SCULPT_DECK_PT_viewport_options(SculptDeckPanel, Panel):
    bl_label = "Viewport Options"
    bl_order = 90  # see SculptDeckPanel in core/ui.py
    bl_parent_id = "SCULPT_DECK_PT_view_3d_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        view = context.space_data
        space = context.area.spaces.active

        col = layout.column()
        col.operator("sculpt_deck.tools_region_flip", text="Flip Tools")
        if len(space.region_quadviews) > 0:
            col.operator("screen.region_quadview", text="Disable Quadview")
        else:
            col.operator("screen.region_quadview", text="Enable Quadview")

        col = layout.column(align=True)
        if not len(space.region_quadviews) > 0:
            col.prop(space, "lock_cursor", text="Lock to Cursor")
            col.prop(view.region_3d, "lock_rotation", text="Lock Rotation")


register, unregister = bpy.utils.register_classes_factory((SCULPT_DECK_PT_viewport_options,))
