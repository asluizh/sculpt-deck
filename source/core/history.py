"""Histories polled from one timer, since Blender doesn't notify add-ons of these changes: the recently used tools
per mode, the recently active meshes, and any history a part adds with `watch` (the brush history)."""

from typing import Callable, Collection

import bpy

from .invoke import active_tool


class ToolHistory:
    """Recently used tools per mode, so a tool can hand back to the one used before it"""

    size = 8

    def __init__(self):
        self.recent: dict[str, list[str]] = {}

    def update(self, context):
        tool = active_tool(context)
        if not tool:
            return
        recent = self.recent.setdefault(context.mode, [])
        if recent and recent[-1] == tool:
            return
        if tool in recent:
            recent.remove(tool)
        recent.append(tool)
        del recent[: -self.size]

    def previous(self, mode: str, skip: Collection[str], default: str) -> str:
        for tool in reversed(self.recent.get(mode, [])):
            if tool not in skip:
                return tool
        return default


tool_history = ToolHistory()


class ObjectHistory:
    """Recently active meshes, so Delete can go back to the mesh used before the deleted one"""

    size = 16

    def __init__(self):
        self.recent: list[str] = []

    def update(self, context):
        obj = context.view_layer.objects.active
        if obj is None or obj.type != "MESH":
            return
        if self.recent and self.recent[-1] == obj.name:
            return
        if obj.name in self.recent:
            self.recent.remove(obj.name)
        self.recent.append(obj.name)
        del self.recent[: -self.size]

    def previous(self, context, skip):
        """The latest mesh still in the view layer and visible, other than `skip`"""
        layer = context.view_layer.objects
        for name in reversed(self.recent):
            obj = layer.get(name)
            if obj is not None and obj != skip and obj.type == "MESH" and obj.visible_get():
                return obj
        return None


object_history = ObjectHistory()


# updates polled besides the tool and object histories, each given the context
_watched: list[Callable] = []


def watch(update: Callable):
    """Poll update(context) with the other histories, until unwatch"""
    if update not in _watched:
        _watched.append(update)


def unwatch(update: Callable):
    if update in _watched:
        _watched.remove(update)


def poll_histories():
    for update in (tool_history.update, object_history.update, *_watched):
        try:
            update(bpy.context)
        except (AttributeError, ReferenceError, TypeError):
            pass  # no scene while loading files
    return 0.25


def register():
    bpy.app.timers.register(poll_histories, first_interval=0.25, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(poll_histories):
        bpy.app.timers.unregister(poll_histories)
