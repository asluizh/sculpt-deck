import math

import bmesh
import bpy
from bpy.app.handlers import persistent
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty,
                       StringProperty)
from bpy.types import Operator
from mathutils import Matrix

from ..utils import settings
from ..utils.actions import object_history
from ..utils.undo import push_scene_undo
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


class TOUCHVIEW_OT_stroke_method(Operator):
    """Choose how the active brush applies its stroke (Space, Dots, Line, Curve...)"""

    bl_label = "Stroke Method"
    bl_idname = "touchview.stroke_method"

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


# custom property marking the mode an object returns to: saved in the undo step, cleared once back in that mode
RETURN_MODE = "touchview_return_mode"


def enter_mode(window, area, mode: str, tool: str = ""):
    """Switch the active object to `mode` right after the current operator or undo step"""

    def run():
        try:
            with bpy.context.temp_override(window=window, area=area):
                obj = bpy.context.view_layer.objects.active
                if obj is None:
                    return None
                if bpy.context.mode == "OBJECT":
                    bpy.ops.object.mode_set(mode=mode)
                if RETURN_MODE in obj:
                    del obj[RETURN_MODE]
                if tool:
                    bpy.ops.wm.tool_set_by_id(name=tool, space_type="VIEW_3D")
        except (RuntimeError, ReferenceError, TypeError):
            pass
        return None

    bpy.app.timers.register(run, first_interval=0.0)


def finish_in_mode(context, mode: str, tool: str = ""):
    """Return to `mode` once the calling operator has finished in Object Mode.

    Ending in Object Mode makes the operator's own undo step a whole scene step, so redoing it brings its objects
    back (see push_scene_undo). The mode switch afterwards adds no undo step of its own. That step is saved in
    Object Mode, so the object is marked with its mode, and returns to it whenever the step is undone or redone to.
    """
    if mode == "OBJECT":
        return
    obj = context.view_layer.objects.active
    if obj is not None:
        obj[RETURN_MODE] = mode
    enter_mode(context.window, context.area, mode, tool)


@persistent
def restore_mode(*_):
    """After undo or redo: put an object marked by finish_in_mode back in its mode"""
    context = bpy.context
    obj = context.view_layer.objects.active if context.view_layer else None
    if obj is None or RETURN_MODE not in obj:
        return
    # the mode may still change while the undo finishes, so the timer checks it
    window = context.window or next(iter(context.window_manager.windows), None)
    area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), None) if window else None
    enter_mode(window, area, obj[RETURN_MODE])


def revolve(name: str, profile: list[tuple[float, float]], segments: int):
    """A closed mesh made by turning a profile of (radius, height) points, pole to pole, around Z"""
    bm = bmesh.new()
    rings = []
    for radius, z in profile:
        if radius < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
            continue
        rings.append([bm.verts.new((radius * math.cos(a), radius * math.sin(a), z))
                      for a in (2 * math.pi * i / segments for i in range(segments))])
    for low, high in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            if len(low) == 1:
                bm.faces.new((low[0], high[i], high[j]))
            elif len(high) == 1:
                bm.faces.new((low[i], high[0], low[j]))
            else:
                bm.faces.new((low[i], high[i], high[j], low[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


# shapes whose sharp edges Round Edges bevels
rounded_primitives = {"CUBE", "CYLINDER", "CONE"}
# shapes that are already evenly spaced, so Sculpt Mode keeps them instead of remeshing them
even_primitives = {"ICOSPHERE", "QUADSPHERE", "PLANE"}


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
    smooth: BoolProperty(name="Smooth", description="Shade the mesh smooth", default=True)  # type: ignore
    roundness: FloatProperty(  # type: ignore
        name="Round Edges",
        description="Round off the sharp edges, as a fraction of the shape's half size",
        default=0.0,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
    vertices: IntProperty(  # type: ignore
        name="Vertices",
        description="Vertices around the base: few for a prism or pyramid, many for a round shape",
        default=64,
        min=3,
        max=512,
    )
    segments: IntProperty(  # type: ignore
        name="Segments", description="Vertices around the equator", default=64, min=3, max=512)
    rings: IntProperty(  # type: ignore
        name="Rings", description="Vertices from pole to pole", default=32, min=3, max=256)
    ico_subdivisions: IntProperty(  # type: ignore
        name="Subdivisions", description="Subdivisions of the icosahedron, 1 being the icosahedron itself",
        default=6, min=1, max=8)
    quad_subdivisions: IntProperty(  # type: ignore
        name="Subdivisions", description="Subdivisions of the cube", default=6, min=1, max=8)
    radius: FloatProperty(  # type: ignore
        name="Radius", default=0.5, min=0.001, soft_max=10, subtype="DISTANCE")
    length: FloatProperty(  # type: ignore
        name="Length", description="Full length, ends included", default=2.0, min=0.001, soft_max=20,
        subtype="DISTANCE")
    outer_radius: FloatProperty(  # type: ignore
        name="Outer Radius", default=1.25, min=0.002, soft_max=10, subtype="DISTANCE")
    inner_radius: FloatProperty(  # type: ignore
        name="Inner Radius", default=0.75, min=0.001, soft_max=10, subtype="DISTANCE")
    major_segments: IntProperty(  # type: ignore
        name="Segments", description="Vertices around the ring", default=64, min=3, max=512)
    minor_segments: IntProperty(  # type: ignore
        name="Tube Segments", description="Vertices around the tube", default=24, min=3, max=256)
    # set once the undo step before the mesh is stored, so redos from Adjust Last Operation don't stack more
    undo_pushed: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore
    # for Delete: the mode to end in when called from Object Mode, and whether to keep the current tool
    target_mode: StringProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore
    keep_tool: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore

    # options drawn for each shape, besides Resolution, Smooth and Round Edges
    shape_options = {
        "SPHERE": ("segments", "rings"),
        "ICOSPHERE": ("ico_subdivisions",),
        "QUADSPHERE": ("quad_subdivisions",),
        "CYLINDER": ("vertices",),
        "CONE": ("vertices",),
        "CAPSULE": ("radius", "length", "segments", "rings"),
        "TORUS": ("outer_radius", "inner_radius", "major_segments", "minor_segments"),
    }

    @classmethod
    def poll(cls, context):
        return context.mode in object_modes

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "primitive")
        for name in self.shape_options.get(self.primitive, ()):
            layout.prop(self, name)
        if context.mode == "SCULPT" and self.primitive not in even_primitives:
            layout.prop(self, "resolution")
        layout.prop(self, "smooth")
        if self.primitive in rounded_primitives:
            layout.prop(self, "roundness", slider=True)

    def execute(self, context):
        mode = self.target_mode or object_modes[context.mode]
        if not self.undo_pushed:
            push_scene_undo(context, "Before Add Mesh")
            self.undo_pushed = True
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        sculpt = mode == "SCULPT"
        self.add_mesh(context, sculpt)

        obj = context.view_layer.objects.active
        if self.primitive in rounded_primitives and self.roundness > 0:
            self.round_edges(context, obj, sculpt)
        # voxel remesh needs a closed shape; evenly spaced shapes are sculptable as they are
        if sculpt and self.primitive not in even_primitives:
            context.view_layer.update()
            obj.data.remesh_voxel_size = max(obj.dimensions) / self.resolution
            bpy.ops.object.voxel_remesh()
        if not self.smooth:
            bpy.ops.object.shade_flat()
        elif sculpt or self.primitive not in rounded_primitives:
            bpy.ops.object.shade_smooth()
        else:
            # keep the corners of cubes and prisms crisp
            bpy.ops.object.shade_smooth_by_angle()
        # place the new mesh right away
        finish_in_mode(context, mode, TOOL_ID if sculpt and not self.keep_tool else "")
        return FINISHED

    def add_mesh(self, context, sculpt: bool):
        mesh = bpy.ops.mesh
        if self.primitive == "SPHERE":
            mesh.primitive_uv_sphere_add(segments=self.segments, ring_count=self.rings)
        elif self.primitive == "ICOSPHERE":
            mesh.primitive_ico_sphere_add(subdivisions=self.ico_subdivisions)
        elif self.primitive == "QUADSPHERE":
            mesh.primitive_cube_add()
            self.apply_modifier("SUBSURF", levels=self.quad_subdivisions)
            # project onto the unit sphere, matching the UV sphere's size
            data = context.view_layer.objects.active.data
            for vertex in data.vertices:
                vertex.co.normalize()
            data.update()
        elif self.primitive == "CUBE":
            mesh.primitive_cube_add()
        elif self.primitive == "CYLINDER":
            mesh.primitive_cylinder_add(vertices=self.vertices)
            self.face_front(context)
        elif self.primitive == "CONE":
            mesh.primitive_cone_add(vertices=self.vertices)
            self.face_front(context)
        elif self.primitive == "CAPSULE":
            self.add_capsule(context)
        elif self.primitive == "TORUS":
            outer = max(self.outer_radius, self.inner_radius + 0.001)
            mesh.primitive_torus_add(mode="EXT_INT", abso_major_rad=outer, abso_minor_rad=self.inner_radius,
                                     major_segments=self.major_segments, minor_segments=self.minor_segments)
        elif self.primitive == "PLANE":
            if sculpt:
                mesh.primitive_grid_add(x_subdivisions=self.resolution, y_subdivisions=self.resolution, size=2)
            else:
                mesh.primitive_plane_add()
        elif self.primitive == "MONKEY":
            mesh.primitive_monkey_add()
            if sculpt:
                # a rounder start for the remesh
                self.apply_modifier("SUBSURF", levels=2)

    def face_front(self, context):
        """Turn the base so a side faces front, so a square pyramid lines up with a cube; the object stays unrotated"""
        context.view_layer.objects.active.data.transform(Matrix.Rotation(math.pi / self.vertices, 4, "Z"))

    def add_capsule(self, context):
        """A cylinder with half spheres for ends, its rings evenly spaced along the whole length"""
        radius = self.radius
        straight = max(self.length - 2 * radius, 0)
        quarter = max(1, self.rings // 2)  # rings on each end
        step = math.pi / 2 / quarter
        cap = [(radius * math.sin(step * i), radius * math.cos(step * i)) for i in range(quarter)]
        cap.append((radius, 0.0))
        bands = max(1, round(straight / (radius * step)))
        half = straight / 2
        profile = [(r, -z - half) for r, z in cap]
        profile += [(radius, -half + straight * i / bands) for i in range(1, bands)]
        profile += [(r, z + half) for r, z in reversed(cap)]
        if straight == 0:
            # a sphere: the two equators are the same ring
            del profile[quarter + 1]
        mesh = revolve("Capsule", profile, self.segments)
        obj = bpy.data.objects.new("Capsule", mesh)
        context.collection.objects.link(obj)
        obj.location = context.scene.cursor.location
        context.view_layer.objects.active = obj
        obj.select_set(True)

    def round_edges(self, context, obj, sculpt: bool):
        context.view_layer.update()
        half = min(obj.dimensions) / 2
        width = self.roundness * half
        # enough segments for the remesh to see a curve, or a light bevel for Object Mode
        voxels_across = width / (max(obj.dimensions) / self.resolution)
        segments = min(64, max(4, round(voxels_across))) if sculpt else 4
        self.apply_modifier("BEVEL", width=width, segments=segments, limit_method="ANGLE",
                            use_clamp_overlap=True, harden_normals=False)

    def apply_modifier(self, kind: str, **settings):
        obj = bpy.context.view_layer.objects.active
        modifier = obj.modifiers.new("Touchview", kind)
        for name, value in settings.items():
            setattr(modifier, name, value)
        bpy.ops.object.modifier_apply(modifier=modifier.name)


class SelectedMeshes:
    """Shared by Join and Fuse: run in Object Mode, then return to the user's mode"""

    # see TOUCHVIEW_OT_add_primitive
    undo_pushed: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore

    @classmethod
    def poll(cls, context):
        meshes = [obj for obj in context.selected_objects if obj.type == "MESH"]
        active = context.view_layer.objects.active
        return context.mode in object_modes and len(meshes) > 1 and active in meshes

    def execute(self, context):
        mode = object_modes[context.mode]
        if not self.undo_pushed:
            push_scene_undo(context, f"Before {self.bl_label}")
            self.undo_pushed = True
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        active = context.view_layer.objects.active
        others = [obj for obj in context.selected_objects if obj.type == "MESH" and obj != active]
        self.combine(context, active, others)
        finish_in_mode(context, mode)
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


class ActiveMesh:
    """Shared by Duplicate and Delete: run in Object Mode on the active mesh, then return to the user's mode"""

    # see TOUCHVIEW_OT_add_primitive
    undo_pushed: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})  # type: ignore

    @classmethod
    def poll(cls, context):
        obj = context.view_layer.objects.active
        return context.mode in object_modes and obj is not None and obj.type == "MESH"

    def execute(self, context):
        mode = object_modes[context.mode]
        if not self.undo_pushed:
            push_scene_undo(context, f"Before {self.bl_label}")
            self.undo_pushed = True
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        obj = context.view_layer.objects.active
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        self.run(context, obj, mode)
        return FINISHED


class TOUCHVIEW_OT_duplicate_object(ActiveMesh, Operator):
    """Copy the active mesh and move the copy with Local Transform, staying in the current mode"""

    bl_label = "Duplicate"
    bl_idname = "touchview.duplicate_object"
    bl_options = {"REGISTER", "UNDO"}

    def run(self, context, obj, mode):
        bpy.ops.object.duplicate()
        # the copy is active; place it right away
        finish_in_mode(context, mode, TOOL_ID if mode == "SCULPT" else "")


# Round Edges of the cube Delete adds when no mesh is left
DELETE_CUBE_ROUNDNESS = 0.25


class TOUCHVIEW_OT_delete_object(ActiveMesh, Operator):
    """Delete the active mesh and go back to the mesh used before it, in the current mode.
    When no mesh is left, a rounded cube takes its place"""

    bl_label = "Delete"
    bl_idname = "touchview.delete_object"
    bl_options = {"REGISTER", "UNDO"}

    def run(self, context, obj, mode):
        layer = context.view_layer
        previous = object_history.previous(context, obj) or next(
            (o for o in layer.objects if o != obj and o.type == "MESH" and o.visible_get()), None
        )
        bpy.ops.object.delete()
        if previous is not None:
            previous.select_set(True)
            layer.objects.active = previous
            finish_in_mode(context, mode)
        elif mode != "OBJECT":
            # Sculpt and the other modes need a mesh to work on
            bpy.ops.touchview.add_primitive(
                primitive="CUBE", roundness=DELETE_CUBE_ROUNDNESS, target_mode=mode, keep_tool=True, undo_pushed=True
            )


class TOUCHVIEW_OT_save_default_settings(Operator):
    """Use the current settings for new files and files without their own settings"""

    bl_label = "Save Default Settings"
    bl_idname = "touchview.save_default_settings"

    def execute(self, context):
        try:
            settings.save_defaults()
        except OSError as error:
            self.report({"ERROR"}, f"Couldn't save the default settings: {error}")
            return CANCEL
        self.report({"INFO"}, "Default settings saved")
        return FINISHED


class TOUCHVIEW_OT_revert_settings(Operator):
    """Go back to the default settings"""

    bl_label = "Revert to Default Settings"
    bl_idname = "touchview.revert_settings"

    def execute(self, context):
        settings.revert_to_defaults()
        return FINISHED


classes = (
    TOUCHVIEW_OT_save_default_settings,
    TOUCHVIEW_OT_revert_settings,
    TOUCHVIEW_OT_add_primitive,
    TOUCHVIEW_OT_duplicate_object,
    TOUCHVIEW_OT_delete_object,
    TOUCHVIEW_OT_mask_invert,
    TOUCHVIEW_OT_reveal_all,
    TOUCHVIEW_OT_stroke_method,
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


register_classes, unregister_classes = bpy.utils.register_classes_factory(classes)
mode_handlers = (bpy.app.handlers.undo_post, bpy.app.handlers.redo_post)


def register():
    register_classes()
    for handlers in mode_handlers:
        handlers.append(restore_mode)


def unregister():
    for handlers in mode_handlers:
        if restore_mode in handlers:
            handlers.remove(restore_mode)
    unregister_classes()
