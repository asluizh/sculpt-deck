"""Default settings, and settings kept in each .blend file.

The add-on's preferences are the live settings. Saving them as defaults writes them to a file in the add-on's user
folder, which survives add-on updates. Settings that differ from the defaults are stored in the .blend file when it's
saved, so each file can keep its own; opening a file without any brings back the defaults. Save Default Settings and
Revert to Default Settings are the operators for it.
"""

import json
from os import path

import bpy
from bpy.app.handlers import persistent
from bpy.types import Operator

from ... import __package__ as package
from .constants import CANCEL, FINISHED
from .preferences import preferences

FILE_NAME = "preferences.json"
# custom property of the scene that holds a file's own settings
FILE_KEY = "sculpt_deck_settings"
# not settings: open tabs, and the choice of how settings are saved
EXCLUDED_KEYS = {"active_menu", "active_widget", "gizmo_tabs", "auto_save_defaults"}

_defaults: dict = {}
_unsaved = False
_loading = False


def defaults_path(create: bool = False) -> str:
    try:
        folder = bpy.utils.extension_path_user(package, create=create)
    except ValueError:
        # installed as a legacy add-on, not an extension
        folder = bpy.utils.user_resource("CONFIG", path="sculpt_deck", create=create)
    return path.join(folder, FILE_NAME)


def comparable(data: dict) -> dict:
    """Settings only, with values as JSON gives them back, so stored and live settings compare equal"""
    return json.loads(json.dumps({key: value for key, value in data.items() if key not in EXCLUDED_KEYS}))


def current() -> dict:
    return comparable(preferences().to_dict())


def apply(data: dict):
    """Use these settings, keeping the open tabs and the auto save choice"""
    global _loading
    prefs = preferences()
    kept = {key: value for key, value in prefs.to_dict().items() if key in EXCLUDED_KEYS}
    _loading = True
    try:
        prefs.from_dict({**data, **kept})
    finally:
        _loading = False
    prefs.ensure()


def read(filename: str) -> dict | None:
    try:
        with open(filename) as file:
            return json.load(file)
    except (OSError, ValueError):
        return None


def load_defaults():
    """At startup: the saved defaults, or what Blender's preferences hold if there are none yet"""
    global _defaults, _loading
    data = read(defaults_path())
    prefs = preferences()
    if data is not None:
        _loading = True
        try:
            prefs.from_dict(data)
        finally:
            _loading = False
    prefs.ensure()
    _defaults = current()
    update_state()


def save_defaults():
    global _defaults
    # keys of parts not registered now (navigation removed) are kept, so adding the part back brings its settings
    data = {**(read(defaults_path()) or {}), **preferences().to_dict()}
    with open(defaults_path(create=True), "w") as file:
        json.dump(data, file)
    _defaults = current()
    update_state()


def auto_save_changed():
    """The choice is saved right away, whichever way it goes"""
    if not _loading:
        save_defaults()


def revert_to_defaults():
    apply(_defaults)
    update_state()


def is_unsaved() -> bool:
    """The settings differ from the defaults; checked a few times a second, see poll_settings"""
    return _unsaved


def update_state():
    global _unsaved
    try:
        unsaved = current() != _defaults
    except (AttributeError, KeyError, ReferenceError):
        return  # add-on not ready, or a file loading
    if unsaved != _unsaved:
        _unsaved = unsaved
        redraw_sidebars()


def redraw_sidebars():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "UI":
                        region.tag_redraw()


def poll_settings():
    update_state()
    try:
        if _unsaved and preferences().auto_save_defaults:
            save_defaults()
    except (AttributeError, KeyError, OSError):
        pass
    return 0.5


@persistent
def store_in_file(*_):
    """Before saving a .blend file: keep the settings in it when they differ from the defaults"""
    update_state()
    for scene in bpy.data.scenes:
        if FILE_KEY in scene:
            del scene[FILE_KEY]
    scene = bpy.context.scene
    if _unsaved and scene is not None:
        scene[FILE_KEY] = json.dumps(current())


@persistent
def load_from_file(*_):
    """After opening a .blend file (or a new one): its own settings, or the defaults"""
    scenes = [bpy.context.scene] + list(bpy.data.scenes)
    stored = next((scene[FILE_KEY] for scene in scenes if scene is not None and FILE_KEY in scene), None)
    data = None
    if isinstance(stored, str):
        try:
            data = json.loads(stored)
        except ValueError:
            pass
    if data is None and not _defaults:
        return  # defaults not loaded yet, e.g. the startup file before the add-on registers
    try:
        apply(data if data is not None else _defaults)
    except (AttributeError, KeyError):
        return
    update_state()


class SCULPT_DECK_OT_save_default_settings(Operator):
    """Use the current settings for new files and files without their own settings"""

    bl_label = "Save Default Settings"
    bl_idname = "sculpt_deck.save_default_settings"

    def execute(self, context):
        try:
            save_defaults()
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
        revert_to_defaults()
        return FINISHED


classes = (
    SCULPT_DECK_OT_save_default_settings,
    SCULPT_DECK_OT_revert_settings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.handlers.save_pre.append(store_in_file)
    bpy.app.handlers.load_post.append(load_from_file)
    bpy.app.timers.register(poll_settings, first_interval=0.5, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(poll_settings):
        bpy.app.timers.unregister(poll_settings)
    if load_from_file in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_from_file)
    if store_in_file in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(store_in_file)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
