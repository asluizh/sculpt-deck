import time

import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from mathutils import Vector

from ..utils.blender import *
from ..utils.constants import CANCEL, FINISHED, MODAL, PASSTHROUGH, pie_actions

# a widget press held this long opens its menu before the release
MENU_HOLD_TIME = 0.3


class TOUCHVIEW_OT_move_float_menu(Operator):
    """Tap to show/hide the menu buttons, drag to move the menu"""

    bl_label = "Relocate Gizmo Menu"
    bl_idname = "touchview.move_float_menu"

    def invoke(self, context, event):
        self.has_moved = False
        prefs = preferences()
        fence = safe_area_3d(padding=90)
        span = Vector((fence[1].x - fence[0].x, fence[1].y - fence[0].y))

        self.init_x = prefs.menu_position[0]
        self.init_y = prefs.menu_position[1]
        self.mouse_init_x = self.x = event.mouse_region_x
        self.mouse_init_y = self.y = event.mouse_region_y
        self.offset = Vector(
            (
                (span.x * self.init_x * 0.01 + fence[0].x) - self.x,
                (span.y * self.init_y * 0.01 + fence[0].y) - self.y,
            )
        )
        self.execute(context)

        context.window_manager.modal_handler_add(self)
        return MODAL

    def execute(self, context):
        prefs = preferences()
        fence = safe_area_3d(padding=90)
        span = Vector((fence[1].x - fence[0].x, fence[1].y - fence[0].y))

        prefs.menu_position[0] = min(max((self.x - fence[0].x + self.offset.x) / (span.x) * 100.0, 0.0), 100.0)
        prefs.menu_position[1] = min(max((self.y - fence[0].y + self.offset.y) / (span.y) * 100.0, 0.0), 100.0)
        return FINISHED

    def modal(self, context, event):
        prefs = preferences()
        if event.type == "MOUSEMOVE" and event.value != "RELEASE":  # Apply
            context.region.tag_redraw()
            self.x = event.mouse_region_x
            self.y = event.mouse_region_y
            self.execute(context)
        elif event.value == "RELEASE":  # Confirm
            if not self.__hasMoved():
                prefs.menu_position[0] = self.init_x
                prefs.menu_position[1] = self.init_y
                prefs.show_gizmos = not prefs.show_gizmos
            return FINISHED
        return MODAL

    def __hasMoved(self) -> bool:
        prefs = preferences()
        init = Vector((self.mouse_init_x, self.mouse_init_y))
        final = Vector((self.x, self.y))
        if (final - init).length > prefs.menu_spacing / 2:
            return True
        return False


class TOUCHVIEW_OT_cycle_controlGizmo(Operator):
    """Cycle the object gizmo between move, rotate, scale and none"""

    bl_label = "switch object control gizmo"
    bl_idname = "touchview.cycle_control_gizmo"

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


class TOUCHVIEW_OT_float_controller(Operator):
    """Tap to toggle touch controls, drag to move this button"""

    bl_label = "Relocate Toggle Button"
    bl_idname = "touchview.move_toggle_button"

    def invoke(self, context, event):
        self.has_moved = False
        prefs = preferences()
        fence = safe_area_3d()

        span = Vector((fence[1].x - fence[0].x, fence[1].y - fence[0].y))
        self.init_x = prefs.toggle_position[0]
        self.init_y = prefs.toggle_position[1]
        self.mouse_init_x = self.x = event.mouse_region_x
        self.mouse_init_y = self.y = event.mouse_region_y
        self.offset = Vector(
            (
                (span.x * self.init_x * 0.01 + fence[0].x) - self.x,
                (span.y * self.init_y * 0.01 + fence[0].y) - self.y,
            )
        )
        self.execute(context)

        context.window_manager.modal_handler_add(self)
        return MODAL

    def execute(self, context):
        prefs = preferences()
        fence = safe_area_3d()
        span = Vector((fence[1].x - fence[0].x, fence[1].y - fence[0].y))

        prefs.toggle_position[0] = min(max((self.x - fence[0].x + self.offset.x) / (span.x) * 100.0, 0.0), 100.0)
        prefs.toggle_position[1] = min(max((self.y - fence[0].y + self.offset.y) / (span.y) * 100.0, 0.0), 100.0)
        return FINISHED

    def modal(self, context, event):
        prefs = preferences()
        if (
            event.mouse_region_x < 0
            or event.mouse_region_y < 0
            or event.mouse_region_x > context.region.width
            or event.mouse_region_y > context.region.height
        ):
            # mouse out of region area broken in Blender 4.x, exit early
            return FINISHED
        if event.type == "MOUSEMOVE" and event.value != "RELEASE":  # Apply
            context.region.tag_redraw()
            self.x = event.mouse_region_x
            self.y = event.mouse_region_y
            self.execute(context)
        elif event.value == "RELEASE":  # Confirm
            if not self.__hasMoved():
                prefs.toggle_position[0] = self.init_x
                prefs.toggle_position[1] = self.init_y
                prefs.is_enabled = not prefs.is_enabled
            return FINISHED
        return MODAL

    def __hasMoved(self) -> bool:
        prefs = preferences()
        init = Vector((self.mouse_init_x, self.mouse_init_y))
        final = Vector((self.x, self.y))
        if (final - init).length > prefs.menu_spacing / 2:
            return True
        return False


class TOUCHVIEW_OT_widget_menu(Operator):
    """Open a menu or popup from a widget button"""

    bl_label = "Widget Menu"
    bl_idname = "touchview.widget_menu"
    bl_options = {"INTERNAL"}

    name: StringProperty()  # type: ignore  # menu, asset shelf or popup operator

    @classmethod
    def description(cls, context, properties):
        label = pie_actions.get(properties.name, (properties.name,))[0]
        return f"Open {label}"

    # Opened right on press, a menu closes again on the release that follows.
    # A tap opens it after the release instead, so it stays until the next
    # tap; a hold opens it while still pressed
    def invoke(self, context, event):
        self.start = time.monotonic()
        wm = context.window_manager
        self.timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        return MODAL

    def modal(self, context, event):
        released = event.type == "LEFTMOUSE" and event.value == "RELEASE"
        held = event.type == "TIMER" and time.monotonic() - self.start > MENU_HOLD_TIME
        if not (released or held):
            return MODAL if event.type == "LEFTMOUSE" else PASSTHROUGH
        context.window_manager.event_timer_remove(self.timer)
        self.open_menu()
        return FINISHED

    def open_menu(self):
        if "." in self.name:
            category, name = self.name.split(".")
            getattr(getattr(bpy.ops, category), name)("INVOKE_DEFAULT")
        elif "_AST_" in self.name:
            bpy.ops.wm.call_asset_shelf_popover("INVOKE_DEFAULT", name=self.name)  # type: ignore
        elif self.name.endswith("_pie") or self.name == "TOUCHVIEW_MT_floating":
            bpy.ops.wm.call_menu_pie("INVOKE_DEFAULT", name=self.name)  # type: ignore
        else:
            bpy.ops.wm.call_menu("INVOKE_DEFAULT", name=self.name)  # type: ignore


classes = (
    TOUCHVIEW_OT_move_float_menu,
    TOUCHVIEW_OT_cycle_controlGizmo,
    TOUCHVIEW_OT_float_controller,
    TOUCHVIEW_OT_widget_menu,
)


register, unregister = bpy.utils.register_classes_factory(classes)
