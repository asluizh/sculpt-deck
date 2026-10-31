# Built-in modules
import math
import time

import bpy
from bpy.props import EnumProperty
from bpy.types import Operator
from bpy_extras.view3d_utils import (region_2d_to_origin_3d,
                                     region_2d_to_vector_3d)
from mathutils import Vector

# Local modules
from ..utils.blender import preferences, ui_scale
from ..utils.constants import (FINISHED, LMOUSE, MODAL, PASSTHROUGH, PEN,
                               PRESS, RMOUSE, brush_modes, input_mode_items,
                               object_modes)

# a touch that lifts within TAP_TIME without moving TAP_SLOP pixels is a tap;
# held for LONG_PRESS_TIME without moving it toggles the object's selection
TAP_TIME = 0.35
TAP_SLOP = 5
LONG_PRESS_TIME = 0.5
# a second tap this close to the first one makes a double tap; Blender's own
# double click needs both clicks on almost the same pixel
DOUBLE_TAP_DISTANCE = 40


def is_touch(event):
    return event.pressure in [0.0, 1.0]


class TOUCHVIEW_OT_right_click_action(Operator):
    """Viewport right-click shortcut"""

    bl_label = "Viewport right-click shortcut"
    bl_idname = "touchview.rc_action"

    @classmethod
    def poll(cls, context):
        return context.area.type in {"VIEW_2D", "VIEW_3D"} and context.region.type == "WINDOW"

    def invoke(self, context, event):
        prefs = preferences()
        if prefs.right_click_source == "NONE":
            return PASSTHROUGH
        if event.type not in [RMOUSE]:
            return PASSTHROUGH
        # pen buttons are handled by touchview.pen_button
        if event.is_tablet:
            return PASSTHROUGH
        if event.value == "DOUBLE_CLICK":
            return PASSTHROUGH
        self.execute(context)
        return FINISHED

    def execute(self, context):
        prefs = preferences()
        op = prefs.right_click_mode.split(".")
        if op[1] == "transfer_mode" and context.area.type != "VIEW_3D":
            return PASSTHROUGH
        if op[1] == "transfer_mode" and context.mode == "OBJECT":
            bpy.ops.view3d.select("INVOKE_DEFAULT")  # type: ignore
            return PASSTHROUGH
        opgrp = getattr(bpy.ops, op[0])
        getattr(opgrp, op[1])("INVOKE_DEFAULT")
        return FINISHED


class TOUCHVIEW_OT_double_click_action(Operator):
    """Viewport double-tap shortcut"""

    bl_label = "Viewport double-tap shortcut"
    bl_idname = "touchview.dt_action"

    @classmethod
    def poll(cls, context):
        return context.area.type in {"NODE_EDITOR", "VIEW_2D", "VIEW_3D", "IMAGE_EDITOR"} and context.region.type == "WINDOW"

    def invoke(self, context, event):
        if event.type not in [PEN, LMOUSE]:
            return PASSTHROUGH
        if not is_touch(event):
            return PASSTHROUGH
        if event.value != "DOUBLE_CLICK":
            return PASSTHROUGH
        return self.execute(context)

    def execute(self, context):
        prefs = preferences()
        if not prefs.enable_double_click:
            return PASSTHROUGH
        op = prefs.double_click_mode.split(".")
        opgrp = getattr(bpy.ops, op[0])
        if op[1] == "transfer_mode" and context.area.type != "VIEW_3D":
            return PASSTHROUGH
        if op[1] == "transfer_mode" and context.mode == "OBJECT":
            bpy.ops.view3d.select("INVOKE_DEFAULT")  # type: ignore
            return PASSTHROUGH
        getattr(opgrp, op[1])("INVOKE_DEFAULT")
        return FINISHED


class TOUCHVIEW_OT_touch_input_2d(Operator):
    """Active Viewport control zones"""

    bl_label = "2D Viewport Control Regions"
    bl_idname = "touchview.view_ops_2d"

    delta: tuple[float, float]

    mode: EnumProperty(  # type: ignore
        name="Mode",
        description="Sets the viewport control type",
        items=input_mode_items,
        default="PAN",
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context):
        return context.area.type in {"NODE_EDITOR", "VIEW_2D", "IMAGE_EDITOR"} and context.region.type == "WINDOW"

    def invoke(self, context, event):
        prefs = preferences()
        if not prefs.is_enabled:
            return PASSTHROUGH
        if prefs.input_mode == "FULL" and (event.type == PEN or not is_touch(event)):
            return PASSTHROUGH

        if event.value != PRESS:
            return PASSTHROUGH
        self.delta = (event.mouse_region_x, event.mouse_region_y)

        mid_point = Vector((context.region.width / 2, context.region.height / 2))

        dolly_scale = prefs.getWidth()
        dolly_wid = mid_point.x * dolly_scale

        if dolly_wid > self.delta[0] or self.delta[0] > context.region.width - dolly_wid:
            self.mode = "DOLLY"
        else:
            self.mode = "PAN"

        if prefs.swap_panrotate:
            if self.mode == "PAN":
                self.mode = "ORBIT"
            elif self.mode == "ORBIT":
                self.mode = "PAN"

        self.execute(context)
        return FINISHED

    def execute(self, context):
        if context.area.type == "IMAGE_EDITOR":
            return self.exec_image_editor(context)
        if self.mode == "DOLLY":
            bpy.ops.view2d.zoom("INVOKE_DEFAULT")  # type: ignore
        elif self.mode == "PAN":
            bpy.ops.view2d.pan("INVOKE_DEFAULT")  # type: ignore
        return FINISHED

    def exec_image_editor(self, context):
        if self.mode == "PAN":
            bpy.ops.image.view_pan("INVOKE_DEFAULT")  # type: ignore
        elif self.mode == "DOLLY":
            bpy.ops.image.view_zoom("INVOKE_DEFAULT")  # type: ignore
        return FINISHED


class TOUCHVIEW_OT_touch_input_3d(Operator):
    """Active Viewport control zones"""

    bl_label = "Viewport Control Regions"
    bl_idname = "touchview.view_ops_3d"

    delta: tuple[float, float]

    mode: EnumProperty(  # type: ignore
        name="Mode",
        description="Sets the viewport control type",
        items=input_mode_items,
        options={"HIDDEN"},
        default="ORBIT",
    )

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def invoke(self, context, event):
        prefs = preferences()
        passcheck = self.should_pass(context, event)
        if passcheck:
            return PASSTHROUGH

        self.delta = (event.mouse_region_x, event.mouse_region_y)

        mid_point = Vector((context.region.width / 2, context.region.height / 2))

        dolly_scale = prefs.getWidth()
        pan_scale = prefs.getRadius()

        dolly_wid = mid_point.x * dolly_scale
        pan_diameter = math.dist(
            (0, 0),
            mid_point,  # type: ignore
        ) * (pan_scale * 0.5)

        is_quadview_orthographic = context.region_data.is_orthographic_side_view and context.region.alignment == "QUAD_SPLIT"
        is_locked = context.region_data.lock_rotation or is_quadview_orthographic

        if dolly_wid > self.delta[0] or self.delta[0] > context.region.width - dolly_wid:
            self.mode = "DOLLY"
        elif (
            math.dist(
                self.delta,
                mid_point,  # type: ignore
            )
            < pan_diameter
            or is_locked
        ):
            self.mode = "PAN"
        else:
            self.mode = "ORBIT"

        if prefs.swap_panrotate and not is_locked:
            if self.mode == "PAN":
                self.mode = "ORBIT"
            elif self.mode == "ORBIT":
                self.mode = "PAN"

        # wait to see whether this is a tap (select/switch object) or a drag
        if prefs.tap_to_switch and context.mode in object_modes and not event.is_tablet:
            self.press_time = time.monotonic()
            self.state = "PRESSED"
            wm = context.window_manager
            self.timer = wm.event_timer_add(0.05, window=context.window)
            wm.modal_handler_add(self)
            return MODAL
        self.navigate(context)
        return FINISHED

    def modal(self, context, event):
        elapsed = time.monotonic() - self.press_time
        if self.state == "PRESSED":
            if event.type == LMOUSE and event.value == "RELEASE":
                if elapsed >= TAP_TIME:
                    return self.finish(context)
                # a second tap may follow; act only once it's clear it won't
                if preferences().enable_double_click:
                    self.state = "RELEASED"
                    self.release_time = time.monotonic()
                    return MODAL
                self.tap(context)
                return self.finish(context)
            if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"}:
                dx = event.mouse_region_x - self.delta[0]
                dy = event.mouse_region_y - self.delta[1]
                if math.hypot(dx, dy) > TAP_SLOP * ui_scale():
                    self.finish(context)
                    self.navigate(context)
                    return FINISHED
                return MODAL
            if event.type == "TIMER" and elapsed >= LONG_PRESS_TIME:
                self.toggle_selection(context)
                self.state = "LONG_PRESSED"
            return PASSTHROUGH

        if self.state == "RELEASED":
            if event.type == LMOUSE and event.value in {"PRESS", "DOUBLE_CLICK"}:
                dx = event.mouse_region_x - self.delta[0]
                dy = event.mouse_region_y - self.delta[1]
                if math.hypot(dx, dy) <= DOUBLE_TAP_DISTANCE * ui_scale():
                    try:
                        bpy.ops.touchview.dt_action("EXEC_DEFAULT")  # type: ignore
                    except RuntimeError as error:
                        self.report({"WARNING"}, str(error))
                    self.state = "DOUBLE_TAPPED"
                    return MODAL
                # a new touch somewhere else: the first one was a single tap
                self.tap(context)
                self.finish(context)
                return {"FINISHED", "PASS_THROUGH"}
            double_click_time = context.preferences.inputs.mouse_double_click_time / 1000
            if event.type == "TIMER" and time.monotonic() - self.release_time > double_click_time:
                self.tap(context)
                return self.finish(context)
            return PASSTHROUGH

        # long pressed or double tapped: ignore the rest of the touch
        if event.type == LMOUSE and event.value == "RELEASE":
            return self.finish(context)
        return MODAL if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"} else PASSTHROUGH

    def finish(self, context):
        context.window_manager.event_timer_remove(self.timer)
        return FINISHED

    # tap an object to select it, or to switch to it in edit/sculpt/paint modes
    def tap(self, context):
        if context.mode == "OBJECT":
            bpy.ops.view3d.select("INVOKE_DEFAULT", deselect_all=True)  # type: ignore
            return
        target = self.objectAt(context, *self.delta)
        if target is None or target == context.view_layer.objects.active:
            return
        try:
            bpy.ops.object.transfer_mode("INVOKE_DEFAULT")  # type: ignore
        except RuntimeError:
            pass  # the object can't enter this mode

    # long press an object to add it to or remove it from the selection
    def toggle_selection(self, context):
        target = self.objectAt(context, *self.delta)
        active = context.view_layer.objects.active
        if target is None or target == active:
            return
        target.select_set(not target.select_get())
        if active is not None:
            active.select_set(True)
        change = "added to" if target.select_get() else "removed from"
        self.report({"INFO"}, f"{target.name} {change} the selection")
        context.area.tag_redraw()

    def navigate(self, context):
        if context.mode == "SCULPT":
            bpy.ops.sculpt.set_pivot_position(mode=preferences().pivot_mode)
        self.execute(context)

    def execute(self, context):
        if self.mode == "DOLLY":
            bpy.ops.view3d.zoom("INVOKE_DEFAULT")  # type: ignore
        elif self.mode == "ORBIT":
            if context.mode == "SCULPT":
                bpy.ops.sculpt.set_pivot_position(mode="SURFACE", mouse_x=self.delta[0], mouse_y=self.delta[1])
            bpy.ops.view3d.rotate("INVOKE_DEFAULT")  # type: ignore
        elif self.mode == "PAN":
            bpy.ops.view3d.move("INVOKE_DEFAULT")  # type: ignore
        return FINISHED

    def should_pass(self, context, event):
        prefs = preferences()

        # experimental passthrough in drawing mode
        if (
            prefs.lazy_mode
            and not prefs.is_enabled
            and event.value == PRESS
            and brush_modes.__contains__(context.mode)
            and self.mouseTarget(context, event) != context.active_object
        ):
            return False

        if not prefs.is_enabled:
            return True

        if prefs.input_mode == "FULL" and (event.type == PEN or not is_touch(event)):
            return True

        if event.value != PRESS:
            return True
        return False

    def mouseTarget(self, context, event):
        return self.objectAt(context, event.mouse_region_x, event.mouse_region_y)

    # the mesh object under a point of the region, if any
    def objectAt(self, context, x: float, y: float):
        region = context.region
        rv3d = context.region_data
        coord = Vector((x, y))

        # get the ray from the viewport and mouse
        view_vector = region_2d_to_vector_3d(region, rv3d, coord)
        self.ray_origin = region_2d_to_origin_3d(region, rv3d, coord)

        self.ray_target = self.ray_origin + view_vector
        return self.isCurrentObject(context)

    def visible_objects_and_duplicates(self, context):
        depsgraph = context.evaluated_depsgraph_get()
        for dup in depsgraph.object_instances:
            if dup.is_instance:  # Real dupli instance
                obj = dup.instance_object
                yield (obj, dup.matrix_world.copy())  # type: ignore
            else:  # Usual object
                obj = dup.object
                yield (obj, obj.matrix_world.copy())  # type: ignore

    def obj_ray_cast(self, obj, matrix):
        # get the ray relative to the object
        matrix_inv = matrix.inverted()
        ray_origin_obj = matrix_inv @ self.ray_origin
        ray_target_obj = matrix_inv @ self.ray_target
        ray_direction_obj = ray_target_obj - ray_origin_obj

        # cast the ray
        success, location, normal, face_index = obj.ray_cast(ray_origin_obj, ray_direction_obj)

        if success:
            return location, normal, face_index
        else:
            return None, None, None

    def isCurrentObject(self, context):
        # cast rays and find the closest object
        best_length_squared = -1.0
        best_obj = None

        for obj, matrix in self.visible_objects_and_duplicates(context):
            if obj.type == "MESH":
                hit, _, _ = self.obj_ray_cast(obj, matrix)
                if hit is not None:
                    hit_world = matrix @ hit
                    length_squared = (hit_world - self.ray_origin).length_squared
                    if best_obj is None or length_squared < best_length_squared:
                        best_length_squared = length_squared
                        best_obj = obj

        return best_obj.original if best_obj is not None else None


classes = (
    TOUCHVIEW_OT_right_click_action,
    TOUCHVIEW_OT_double_click_action,
    TOUCHVIEW_OT_touch_input_2d,
    TOUCHVIEW_OT_touch_input_3d,
)


register, unregister = bpy.utils.register_classes_factory(classes)
