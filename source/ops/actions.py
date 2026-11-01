import math

import bpy
from bpy.props import EnumProperty, FloatProperty, IntProperty
from bpy.types import Operator

from ..utils.blender import preferences
from .local_transform import TOOL_ID
from ..utils.constants import (CANCEL, FINISHED, object_modes,
                               paint_settings_name, pivot_items,
                               primitive_items)


class TOUCHVIEW_OT_flip_tools(Operator):
    """Relocate Tools panel between left and right"""

    bl_label = "Tools Region Swap"
    bl_idname = "touchview.tools_region_flip"

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


class TOUCHVIEW_OT_next_pivot_mode(Operator):
    """Step through Pivot modes"""

    bl_label = "Use next Pivot mode"
    bl_idname = "touchview.step_pivot_mode"

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


class TOUCHVIEW_OT_toggle_touch_controls(Operator):
    """Toggle Touch Controls"""

    bl_label = "Toggle Touch Controls"
    bl_idname = "touchview.toggle_touch"

    def execute(self, context):
        prefs = preferences()
        prefs.is_enabled = not prefs.is_enabled
        context.area.tag_redraw()
        return FINISHED


class TOUCHVIEW_OT_toggle_npanel(Operator):
    """Toggle the sidebar (N panel)"""

    bl_label = "Display prefs Panel"
    bl_idname = "touchview.toggle_n_panel"

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D" and context.region.type == "WINDOW"

    def execute(self, context):
        if not isinstance(context.space_data, bpy.types.SpaceView3D):
            return CANCEL
        context.space_data.show_region_ui ^= True
        return FINISHED


class TOUCHVIEW_OT_viewport_recenter(Operator):
    """Recenter Viewport and Cursor on Selected Object"""

    bl_label = "Recenter Viewport and Cursor on Selected"
    bl_idname = "touchview.viewport_recenter"

    def execute(self, context):
        current = context.scene.tool_settings.transform_pivot_point
        context.scene.tool_settings.transform_pivot_point = "ACTIVE_ELEMENT"
        bpy.ops.view3d.snap_cursor_to_selected()
        bpy.ops.view3d.view_center_cursor()
        bpy.ops.view3d.view_selected()
        context.scene.tool_settings.transform_pivot_point = current
        return FINISHED


class TOUCHVIEW_OT_viewport_lock(Operator):
    """Toggle viewport rotation lock"""

    bl_label = "Viewport rotation lock toggle"
    bl_idname = "touchview.viewport_lock"

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


class TOUCHVIEW_OT_brush_resize(BrushRadialControl, Operator):
    """Adjust the brush size"""

    bl_label = "Brush Size Adjust"
    bl_idname = "touchview.brush_resize"

    prop = "size"


class TOUCHVIEW_OT_brush_strength(BrushRadialControl, Operator):
    """Adjust the brush strength"""

    bl_label = "Brush Strength Adjust"
    bl_idname = "touchview.brush_strength"

    prop = "strength"


class TOUCHVIEW_OT_increase_multires(Operator):
    """Increase the Multires level, subdividing when at the highest level"""

    bl_label = "Increment Multires modifier by 1 or add subdivision level"
    bl_idname = "touchview.increment_multires"

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


class TOUCHVIEW_OT_decrease_multires(Operator):
    """Decrease the Multires level, unsubdividing when at the lowest level"""

    bl_label = "decrement Multires modifier by 1"
    bl_idname = "touchview.decrement_multires"

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


class TOUCHVIEW_OT_density_up(Operator):
    """Increase voxel density and remesh"""

    bl_label = "Increase voxel density and remesh"
    bl_idname = "touchview.density_up"
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


class TOUCHVIEW_OT_density_down(Operator):
    """Decrease voxel density and remesh"""

    bl_label = "Decrease voxel density and remesh"
    bl_idname = "touchview.density_down"
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


class TOUCHVIEW_OT_mask_invert(Operator):
    """Invert the sculpt mask"""

    bl_label = "Invert Mask"
    bl_idname = "touchview.mask_invert"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "SCULPT"

    def execute(self, context):
        bpy.ops.paint.mask_flood_fill(mode="INVERT")
        return FINISHED


class TOUCHVIEW_OT_reveal_all(Operator):
    """Show all hidden parts of the sculpt"""

    bl_label = "Reveal Hidden"
    bl_idname = "touchview.reveal_all"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "SCULPT"

    def execute(self, context):
        bpy.ops.paint.hide_show_all(action="SHOW")
        return FINISHED


class TOUCHVIEW_OT_add_primitive(Operator):
    """Add a mesh at the 3D cursor and keep working on it in the current mode"""

    bl_label = "Add Mesh"
    bl_idname = "touchview.add_primitive"
    bl_options = {"REGISTER", "UNDO"}

    primitive: EnumProperty(name="Shape", items=primitive_items)  # type: ignore
    resolution: IntProperty(  # type: ignore
        name="Resolution",
        description="Sculpt mode: voxels across the longest side, for an even, sculptable mesh",
        default=80,
        min=8,
        soft_max=300,
    )

    @classmethod
    def poll(cls, context):
        return context.mode in object_modes

    def execute(self, context):
        mode = object_modes[context.mode]
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        sculpt = mode == "SCULPT"
        self.add_mesh(sculpt)

        obj = context.view_layer.objects.active
        # voxel remesh needs a closed shape; the sculpt plane is a dense grid instead
        if sculpt and self.primitive != "PLANE":
            context.view_layer.update()
            obj.data.remesh_voxel_size = max(obj.dimensions) / self.resolution
            bpy.ops.object.voxel_remesh()
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode=mode)
        if sculpt:
            # place the new mesh right away
            bpy.ops.wm.tool_set_by_id(name=TOOL_ID, space_type="VIEW_3D")
        return FINISHED

    def add_mesh(self, sculpt: bool):
        mesh = bpy.ops.mesh
        if self.primitive == "SPHERE":
            mesh.primitive_uv_sphere_add()
        elif self.primitive == "CUBE":
            mesh.primitive_cube_add()
        elif self.primitive == "CYLINDER":
            mesh.primitive_cylinder_add()
        elif self.primitive == "CONE":
            mesh.primitive_cone_add()
        elif self.primitive == "TORUS":
            mesh.primitive_torus_add()
        elif self.primitive == "PLANE":
            if sculpt:
                mesh.primitive_grid_add(x_subdivisions=self.resolution, y_subdivisions=self.resolution, size=2)
            else:
                mesh.primitive_plane_add()
        elif self.primitive == "MONKEY":
            mesh.primitive_monkey_add()


class SelectedMeshes:
    """Shared by Join and Fuse: run in Object Mode, then return to the user's mode"""

    @classmethod
    def poll(cls, context):
        meshes = [obj for obj in context.selected_objects if obj.type == "MESH"]
        active = context.view_layer.objects.active
        return context.mode in object_modes and len(meshes) > 1 and active in meshes

    def execute(self, context):
        mode = object_modes[context.mode]
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        active = context.view_layer.objects.active
        others = [obj for obj in context.selected_objects if obj.type == "MESH" and obj != active]
        self.combine(context, active, others)
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode=mode)
        return FINISHED

    def combine(self, context, active, others):
        for obj in context.selected_objects:
            if obj.type != "MESH":
                obj.select_set(False)
        bpy.ops.object.join()


class Fuse(SelectedMeshes):
    voxel_size: FloatProperty(  # type: ignore
        name="Voxel Size",
        description="Size of the remesh voxels, 0 keeps the active object's voxel size",
        default=0.0,
        min=0.0,
        subtype="DISTANCE",
    )

    def remesh(self, obj):
        if self.voxel_size > 0:
            obj.data.remesh_voxel_size = self.voxel_size
        bpy.ops.object.voxel_remesh()


class TOUCHVIEW_OT_join_selected(SelectedMeshes, Operator):
    """Join the selected meshes into the active one, staying in the current mode"""

    bl_label = "Join Selected"
    bl_idname = "touchview.join_selected"
    bl_options = {"REGISTER", "UNDO"}


class TOUCHVIEW_OT_fuse_selected(Fuse, Operator):
    """Merge the selected meshes into the active one and voxel remesh them, staying in the current mode"""

    bl_label = "Fuse (Union)"
    bl_idname = "touchview.fuse_selected"
    bl_options = {"REGISTER", "UNDO"}

    def combine(self, context, active, others):
        super().combine(context, active, others)
        self.remesh(active)


class TOUCHVIEW_OT_fuse_difference(Fuse, Operator):
    """Cut the other selected meshes out of the active one and voxel remesh it, staying in the current mode"""

    bl_label = "Fuse (Difference)"
    bl_idname = "touchview.fuse_difference"
    bl_options = {"REGISTER", "UNDO"}

    def combine(self, context, active, others):
        for cutter in others:
            modifier = active.modifiers.new("Touchview Cut", "BOOLEAN")
            modifier.operation = "DIFFERENCE"
            modifier.solver = "EXACT"
            modifier.object = cutter
            # apply before any existing modifiers, e.g. Multires
            bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=0)
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            bpy.data.objects.remove(cutter)
        self.remesh(active)


classes = (
    TOUCHVIEW_OT_add_primitive,
    TOUCHVIEW_OT_mask_invert,
    TOUCHVIEW_OT_reveal_all,
    TOUCHVIEW_OT_fuse_difference,
    TOUCHVIEW_OT_fuse_selected,
    TOUCHVIEW_OT_join_selected,
    TOUCHVIEW_OT_brush_resize,
    TOUCHVIEW_OT_brush_strength,
    TOUCHVIEW_OT_decrease_multires,
    TOUCHVIEW_OT_density_down,
    TOUCHVIEW_OT_density_up,
    TOUCHVIEW_OT_flip_tools,
    TOUCHVIEW_OT_increase_multires,
    TOUCHVIEW_OT_next_pivot_mode,
    TOUCHVIEW_OT_toggle_npanel,
    TOUCHVIEW_OT_toggle_touch_controls,
    TOUCHVIEW_OT_viewport_lock,
    TOUCHVIEW_OT_viewport_recenter,
)


register, unregister = bpy.utils.register_classes_factory(classes)
