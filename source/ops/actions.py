import math

import bpy
from bpy.types import Operator

from ..utils import settings
from ..utils.blender import preferences
from ..utils.constants import CANCEL, FINISHED, paint_settings_name, pivot_items


class SCULPT_DECK_OT_flip_tools(Operator):
    """Relocate Tools panel between left and right"""

    bl_label = "Tools Region Swap"
    bl_idname = "sculpt_deck.tools_region_flip"

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def execute(self, context):
        override = context.copy()
        override["area"] = context.area
        override["region"] = context.region
        for r in context.area.regions:
            if r.type == "TOOLS":
                override["region"] = r
        with context.temp_override(region=override["region"]):  # type: ignore
            bpy.ops.screen.region_flip()
        return FINISHED


class SCULPT_DECK_OT_next_pivot_mode(Operator):
    """Step through Pivot modes"""

    bl_label = "Use next Pivot mode"
    bl_idname = "sculpt_deck.step_pivot_mode"

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def execute(self, context):
        prefs = preferences()
        count = 0
        for enum, _, _ in pivot_items:
            if enum == prefs.pivot_mode:
                count += 1
                if count == len(pivot_items):
                    count = 0
                pivot = pivot_items[count][0]
                bpy.ops.sculpt.set_pivot_position(mode=pivot)
                prefs.pivot_mode = pivot
                context.area.tag_redraw()
                return FINISHED
            count += 1
        return FINISHED


class SCULPT_DECK_OT_toggle_touch_controls(Operator):
    """Toggle Touch Controls"""

    bl_label = "Toggle Touch Controls"
    bl_idname = "sculpt_deck.toggle_touch"

    def execute(self, context):
        prefs = preferences()
        prefs.is_enabled = not prefs.is_enabled
        context.area.tag_redraw()
        return FINISHED


class SCULPT_DECK_OT_toggle_npanel(Operator):
    """Toggle the sidebar (N panel)"""

    bl_label = "Display prefs Panel"
    bl_idname = "sculpt_deck.toggle_n_panel"

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def execute(self, context):
        if not isinstance(context.space_data, bpy.types.SpaceView3D):
            return CANCEL
        context.space_data.show_region_ui ^= True
        return FINISHED


class SCULPT_DECK_OT_viewport_recenter(Operator):
    """Recenter Viewport and Cursor on Selected Object"""

    bl_label = "Recenter Viewport and Cursor on Selected"
    bl_idname = "sculpt_deck.viewport_recenter"

    def execute(self, context):
        current = context.scene.tool_settings.transform_pivot_point
        context.scene.tool_settings.transform_pivot_point = "ACTIVE_ELEMENT"
        bpy.ops.view3d.snap_cursor_to_selected()
        bpy.ops.view3d.view_center_cursor()
        bpy.ops.view3d.view_selected()
        context.scene.tool_settings.transform_pivot_point = current
        return FINISHED


class SCULPT_DECK_OT_viewport_lock(Operator):
    """Toggle viewport rotation lock"""

    bl_label = "Viewport rotation lock toggle"
    bl_idname = "sculpt_deck.viewport_lock"

    region_ids = []

    def execute(self, context):
        if not isinstance(context.area.spaces.active, bpy.types.SpaceView3D):
            return CANCEL
        if len(context.area.spaces.active.region_quadviews) == 0:
            context.region_data.lock_rotation ^= True
            return FINISHED

        for region in context.area.spaces.active.region_quadviews:
            self.region_ids.append((region.as_pointer(), region.lock_rotation))

        start_change = False
        regions = dict(self.region_ids)
        for i in range(3, -1, -1):
            region_data = context.area.spaces.active.region_quadviews[i]
            if context.region_data.as_pointer() == region_data.as_pointer():
                start_change = True
                context.region_data.lock_rotation ^= True
                continue

            if start_change:
                region_data.lock_rotation = regions[region_data.as_pointer()]
        self.region_ids = []
        return FINISHED


class BrushRadialControl:
    """Shared radial control for brush properties, mirroring Blender's own keymap"""

    prop = ""

    def invoke(self, context, event):
        prefs = preferences()
        # move the cursor away from the bar so the radial control has room
        if prefs.menu_style in {"fixed.bar"}:
            if prefs.gizmo_position in ["LEFT", "RIGHT"]:
                context.window.cursor_warp(
                    context.region.x + math.floor(context.region.width / 2),
                    context.region.y + event.mouse_region_y,
                )
            else:
                context.window.cursor_warp(
                    context.region.x + event.mouse_region_x,
                    context.region.y + math.floor(context.region.height / 2),
                )
        return self.execute(context)

    def execute(self, context):
        paint = paint_settings_name(context.mode)
        if paint is None:
            return CANCEL
        brush_path = f"tool_settings.{paint}.brush"
        # grease pencil draw mode ignores unified settings, same as Blender's keymap
        if paint == "gpencil_paint":
            bpy.ops.wm.radial_control(
                "INVOKE_DEFAULT",  # type: ignore
                data_path_primary=f"{brush_path}.{self.prop}",
            )
            return FINISHED

        unified_path = f"tool_settings.{paint}.unified_paint_settings"
        bpy.ops.wm.radial_control(
            "INVOKE_DEFAULT",  # type: ignore
            data_path_primary=f"{brush_path}.{self.prop}",
            data_path_secondary=f"{unified_path}.{self.prop}",
            use_secondary=f"{unified_path}.use_unified_{self.prop}",
            rotation_path=f"{brush_path}.texture_slot.angle",
            color_path=f"{brush_path}.cursor_color_add",
            image_id=brush_path,
        )
        return FINISHED


class SCULPT_DECK_OT_brush_resize(BrushRadialControl, Operator):
    """Adjust the brush size"""

    bl_label = "Brush Size Adjust"
    bl_idname = "sculpt_deck.brush_resize"

    prop = "size"


class SCULPT_DECK_OT_brush_strength(BrushRadialControl, Operator):
    """Adjust the brush strength"""

    bl_label = "Brush Strength Adjust"
    bl_idname = "sculpt_deck.brush_strength"

    prop = "strength"


class SCULPT_DECK_OT_increase_multires(Operator):
    """Increase the Multires level, subdividing when at the highest level"""

    bl_label = "Increment Multires modifier by 1 or add subdivision level"
    bl_idname = "sculpt_deck.increment_multires"

    def execute(self, context):
        prefs = preferences()
        if not context.active_object or not len(context.active_object.modifiers):
            return CANCEL
        for mod in context.active_object.modifiers:
            # if mod is type of bpy.types.MultiresModifier
            if isinstance(mod, bpy.types.MultiresModifier):
                if context.mode == "SCULPT":
                    if mod.sculpt_levels == mod.total_levels:
                        if mod.sculpt_levels < prefs.subdivision_limit:
                            bpy.ops.object.multires_subdivide(modifier=mod.name)
                    else:
                        mod.sculpt_levels += 1
                else:
                    if mod.levels == mod.total_levels:
                        if mod.levels < prefs.subdivision_limit:
                            bpy.ops.object.multires_subdivide(modifier=mod.name)
                    else:
                        mod.levels += 1
                return FINISHED
        return CANCEL


class SCULPT_DECK_OT_decrease_multires(Operator):
    """Decrease the Multires level, unsubdividing when at the lowest level"""

    bl_label = "decrement Multires modifier by 1"
    bl_idname = "sculpt_deck.decrement_multires"

    def execute(self, context):
        if not context.active_object or not len(context.active_object.modifiers):
            return CANCEL
        for mod in context.active_object.modifiers:
            if not isinstance(mod, bpy.types.MultiresModifier):
                continue
            if context.mode == "SCULPT":
                if mod.sculpt_levels == 0:
                    bpy.ops.object.multires_unsubdivide(modifier=mod.name)
                else:
                    mod.sculpt_levels -= 1
            else:
                if mod.levels == 0:
                    bpy.ops.object.multires_unsubdivide(modifier=mod.name)
                else:
                    mod.levels -= 1
            return FINISHED
        return CANCEL


class SCULPT_DECK_OT_density_up(Operator):
    """Increase voxel density and remesh"""

    bl_label = "Increase voxel density and remesh"
    bl_idname = "sculpt_deck.density_up"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not context.active_object or context.active_object.type != "MESH":
            return CANCEL
        for mod in context.active_object.modifiers:
            if isinstance(mod, bpy.types.MultiresModifier):
                return CANCEL
        mesh = context.active_object.data
        mesh.remesh_voxel_size *= 0.8
        bpy.ops.object.voxel_remesh()
        return FINISHED


class SCULPT_DECK_OT_density_down(Operator):
    """Decrease voxel density and remesh"""

    bl_label = "Decrease voxel density and remesh"
    bl_idname = "sculpt_deck.density_down"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not context.active_object or context.active_object.type != "MESH":
            return CANCEL
        for mod in context.active_object.modifiers:
            if isinstance(mod, bpy.types.MultiresModifier):
                return CANCEL
        mesh = context.active_object.data
        mesh.remesh_voxel_size /= 0.8
        bpy.ops.object.voxel_remesh()
        return FINISHED


class SCULPT_DECK_OT_mask_invert(Operator):
    """Invert the sculpt mask"""

    bl_label = "Invert Mask"
    bl_idname = "sculpt_deck.mask_invert"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "SCULPT"

    def execute(self, context):
        bpy.ops.paint.mask_flood_fill(mode="INVERT")
        return FINISHED


class SCULPT_DECK_OT_stroke_method(Operator):
    """Choose how the active brush applies its stroke (Space, Dots, Line, Curve...)"""

    bl_label = "Stroke Method"
    bl_idname = "sculpt_deck.stroke_method"

    @classmethod
    def poll(cls, context):
        paint = paint_settings_name(context.mode)
        if paint is None:
            return False
        brush = getattr(getattr(context.tool_settings, paint, None), "brush", None)
        return brush is not None and hasattr(brush, "stroke_method")

    def execute(self, context):
        # the menu Blender opens with Alt E in paint and sculpt modes
        paint = paint_settings_name(context.mode)
        bpy.ops.wm.context_menu_enum(data_path=f"tool_settings.{paint}.brush.stroke_method")
        return FINISHED


class SCULPT_DECK_OT_reveal_all(Operator):
    """Show all hidden parts of the sculpt"""

    bl_label = "Reveal Hidden"
    bl_idname = "sculpt_deck.reveal_all"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "SCULPT"

    def execute(self, context):
        bpy.ops.paint.hide_show_all(action="SHOW")
        return FINISHED


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
    SCULPT_DECK_OT_mask_invert,
    SCULPT_DECK_OT_reveal_all,
    SCULPT_DECK_OT_stroke_method,
    SCULPT_DECK_OT_brush_resize,
    SCULPT_DECK_OT_brush_strength,
    SCULPT_DECK_OT_decrease_multires,
    SCULPT_DECK_OT_density_down,
    SCULPT_DECK_OT_density_up,
    SCULPT_DECK_OT_flip_tools,
    SCULPT_DECK_OT_increase_multires,
    SCULPT_DECK_OT_next_pivot_mode,
    SCULPT_DECK_OT_toggle_npanel,
    SCULPT_DECK_OT_toggle_touch_controls,
    SCULPT_DECK_OT_viewport_lock,
    SCULPT_DECK_OT_viewport_recenter,
)


register, unregister = bpy.utils.register_classes_factory(classes)
