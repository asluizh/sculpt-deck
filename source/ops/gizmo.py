import bpy
from bpy.types import Operator

from ..utils.constants import CANCEL, FINISHED


class SCULPT_DECK_OT_cycle_controlGizmo(Operator):
    """Cycle the object gizmo between move, rotate, scale and none"""

    bl_label = "switch object control gizmo"
    bl_idname = "sculpt_deck.cycle_control_gizmo"

    @classmethod
    def poll(cls, context):
        return context.area.type in ["VIEW_2D", "VIEW_3D"] and context.region.type == "WINDOW"

    def execute(self, context):
        space = context.space_data
        if not isinstance(space, bpy.types.SpaceView3D):
            return CANCEL
        mode = self.getMode(space)
        self.clearControls(space)
        if mode == "none":
            space.show_gizmo_object_translate = True
        if mode == "translate":
            space.show_gizmo_object_rotate = True
        if mode == "rotate":
            space.show_gizmo_object_scale = True
        return FINISHED

    def getMode(self, space: bpy.types.SpaceView3D):
        if space.show_gizmo_object_translate:
            return "translate"
        if space.show_gizmo_object_rotate:
            return "rotate"
        if space.show_gizmo_object_scale:
            return "scale"
        return "none"

    def clearControls(self, space: bpy.types.SpaceView3D):
        space.show_gizmo_object_translate = False
        space.show_gizmo_object_rotate = False
        space.show_gizmo_object_scale = False


classes = (SCULPT_DECK_OT_cycle_controlGizmo,)


register, unregister = bpy.utils.register_classes_factory(classes)
