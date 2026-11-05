import bpy

from .actions import object_history, tool_history
from .constants import paint_settings_name, pen_brush_modes

# A brush is referenced the way Blender's asset system does it:
# (asset_library_type, asset_library_identifier, relative_asset_identifier),
# which is exactly what brush.asset_activate takes.


def paint_settings(context, mode: str):
    name = paint_settings_name(mode)
    scene = getattr(context, "scene", None)
    if name is None or scene is None:
        return None
    return getattr(scene.tool_settings, name, None)


def brush_ref(settings) -> tuple[str, str, str] | None:
    ref = getattr(settings, "brush_asset_reference", None)
    if ref is None or not ref.relative_asset_identifier:
        return None
    return (ref.asset_library_type, ref.asset_library_identifier, ref.relative_asset_identifier)


def brush_name(ref: tuple[str, str, str] | None) -> str:
    return ref[2].rsplit("/", 1)[-1] if ref else ""


def activate_brush(ref: tuple[str, str, str]) -> bool:
    try:
        result = bpy.ops.brush.asset_activate(
            asset_library_type=ref[0],
            asset_library_identifier=ref[1],
            relative_asset_identifier=ref[2],
        )
    except (RuntimeError, TypeError):
        return False
    return "FINISHED" in result


class BrushHistory:
    """Current and previous brush per paint mode.

    Blender doesn't notify add-ons of brush changes, so this is polled.
    """

    def __init__(self):
        self.current: dict[str, tuple] = {}
        self.previous: dict[str, tuple] = {}

    def update(self, context=None):
        context = context or bpy.context
        for mode in pen_brush_modes:
            ref = brush_ref(paint_settings(context, mode))
            if ref is None or ref == self.current.get(mode):
                continue
            if mode in self.current:
                self.previous[mode] = self.current[mode]
            self.current[mode] = ref

    def snapshot(self, mode: str) -> tuple:
        return (self.current.get(mode), self.previous.get(mode))

    def restore(self, mode: str, snapshot: tuple):
        for store, ref in zip((self.current, self.previous), snapshot):
            if ref is None:
                store.pop(mode, None)
            else:
                store[mode] = ref


history = BrushHistory()


def poll_history():
    try:
        history.update()
        tool_history.update(bpy.context)
        object_history.update(bpy.context)
    except (AttributeError, ReferenceError, TypeError):
        pass  # no scene while loading files
    return 0.25


def register():
    bpy.app.timers.register(poll_history, first_interval=0.25, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(poll_history):
        bpy.app.timers.unregister(poll_history)
