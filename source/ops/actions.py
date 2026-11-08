import bpy
from bpy.types import Operator

from ..utils import settings
from ..utils.constants import CANCEL, FINISHED


class SCULPT_DECK_OT_save_default_settings(Operator):
    """Use the current settings for new files and files without their own settings"""

    bl_label = "Save Default Settings"
    bl_idname = "sculpt_deck.save_default_settings"

    def execute(self, context):
        try:
            settings.save_defaults()
        except OSError as error:
            self.report({"ERROR"}, f"Couldn't save the default settings: {error}")
            return CANCEL
        self.report({"INFO"}, "Default settings saved")
        return FINISHED


class SCULPT_DECK_OT_revert_settings(Operator):
    """Go back to the default settings"""

    bl_label = "Revert to Default Settings"
    bl_idname = "sculpt_deck.revert_settings"

    def execute(self, context):
        settings.revert_to_defaults()
        return FINISHED


classes = (
    SCULPT_DECK_OT_save_default_settings,
    SCULPT_DECK_OT_revert_settings,
)


register, unregister = bpy.utils.register_classes_factory(classes)
