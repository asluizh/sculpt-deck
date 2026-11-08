"""Add Mesh: a Detour that adds a primitive at the 3D cursor, shaped for the mode it returns to, and the Add Mesh
menu listing the shapes."""

import math

import bmesh
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy.types import Menu, Operator
from mathutils import Matrix

from ...core.constants import object_modes
from ...core.detour import Detour
from ..local_transform.operators import TOOL_ID

# menu order; the numbers stay fixed so saved values keep their meaning
primitive_items = [
    ("SPHERE", "Sphere", "", "MESH_UVSPHERE", 0),
    ("ICOSPHERE", "Icosphere", "", "MESH_ICOSPHERE", 10),
    ("QUADSPHERE", "Quad Sphere", "", "SPHERE", 11),
    ("CUBE", "Cube", "", "MESH_CUBE", 1),
    ("CYLINDER", "Cylinder", "", "MESH_CYLINDER", 2),
    ("CONE", "Cone", "", "MESH_CONE", 3),
    ("CAPSULE", "Capsule", "", "MESH_CAPSULE", 7),
    ("TORUS", "Torus", "", "MESH_TORUS", 4),
    ("PLANE", "Plane", "", "MESH_GRID", 5),
    ("MONKEY", "Monkey", "", "MESH_MONKEY", 6),
]


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


class SCULPT_DECK_OT_add_primitive(Detour, Operator):
    """Add a mesh at the 3D cursor and keep working on it in the current mode"""

    bl_label = "Add Mesh"
    bl_idname = "sculpt_deck.add_primitive"
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
    # for Delete: keep the current tool instead of switching to Local Transform to place the mesh
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
        # after a run, the mode it started from: Adjust Last Operation draws this while back in that mode or not
        mode = self.start_mode or object_modes.get(context.mode, "")
        if mode == "SCULPT" and self.primitive not in even_primitives:
            layout.prop(self, "resolution")
        layout.prop(self, "smooth")
        if self.primitive in rounded_primitives:
            layout.prop(self, "roundness", slider=True)

    def return_tool(self) -> str:
        # place the new mesh right away
        return TOOL_ID if self.start_mode == "SCULPT" and not self.keep_tool else ""

    def object_mode_work(self, context):
        bpy.ops.object.select_all(action="DESELECT")
        # shaped for the mode the Detour returns to
        sculpt = self.start_mode == "SCULPT"
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
        modifier = obj.modifiers.new("Sculpt Deck", kind)
        for name, value in settings.items():
            setattr(modifier, name, value)
        bpy.ops.object.modifier_apply(modifier=modifier.name)


class SCULPT_DECK_MT_add_mesh(Menu):
    """Add a mesh and keep working on it in the current mode"""

    bl_label = "Add Mesh"

    def draw(self, context):
        for primitive, name, _, icon, _ in primitive_items:
            self.layout.operator("sculpt_deck.add_primitive", text=name, icon=icon).primitive = primitive


classes = (
    SCULPT_DECK_OT_add_primitive,
    SCULPT_DECK_MT_add_mesh,
)

register, unregister = bpy.utils.register_classes_factory(classes)
