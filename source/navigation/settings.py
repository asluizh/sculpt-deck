# type: ignore
"""Touch navigation's settings: the input mode, the control zones and their overlay, and the floating toggle that
turns touch controls on and off. Held by the add-on preferences as `preferences().navigation`."""

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty
from bpy.types import PropertyGroup, UILayout

from ..core.blender import redraw_viewports
from ..core.preferences import add_section, preferences, remove_section


class SCULPT_DECK_PG_NavigationSettings(PropertyGroup):
    is_enabled: BoolProperty(
        name="Enable Controls",
        default=True,
    )

    lazy_mode: BoolProperty(
        name="Lazy Mode",
        default=False,
        description="always control camera when not touching selected object",
    )

    toggle_position: FloatVectorProperty(
        name="Toggle Position",
        soft_min=0,
        soft_max=100,
        size=2,
        default=(0, 0),
    )

    toggle_color: FloatVectorProperty(
        name="Toggle Button Color",
        default=(0.1, 0.1, 0.2, 0.5),
        subtype="COLOR",
        min=0.0,
        max=1.0,
        size=4,
    )

    isVisible: BoolProperty(
        name="Show Overlay",
        default=False,
    )

    input_mode: EnumProperty(
        name="Input Mode",
        items=[
            ("FULL", "Full", "Mouse/Touch and Pen input", "CON_CAMERASOLVER", 0),
            ("PEN", "Pen", "Pen input only", "STYLUS_PRESSURE", 1),
            ("TOUCH", "Touch", "Mouse/Touch input only", "VIEW_PAN", 2),
        ],
        default="FULL",
        update=redraw_viewports,
    )

    enable_floating_toggle: BoolProperty(
        name="Floating Toggle",
        description=(
            "Show a floating button in the viewport (bottom-left by default, drag to move) "
            "that turns touch controls on/off. Always shown in Pen and Touch input modes"
        ),
        default=False,
        update=redraw_viewports,
    )

    swap_panrotate: BoolProperty(
        name="Swap Pan/Rotate",
        default=False,
    )

    width: FloatProperty(
        name="Width",
        default=40.0,
        min=10.0,
        max=100,
    )

    radius: FloatProperty(
        name="Radius",
        default=35.0,
        min=10.0,
        max=100.0,
    )

    use_multiple_colors: BoolProperty(
        name="Multicolor Overlay",
        default=False,
    )

    overlay_main_color: FloatVectorProperty(
        name="Overlay Main Color",
        default=(1.0, 1.0, 1.0, 0.01),
        subtype="COLOR",
        min=0.0,
        max=1.0,
        size=4,
    )

    overlay_secondary_color: FloatVectorProperty(
        name="Overlay Secondary Color",
        default=(1.0, 1.0, 1.0, 0.01),
        subtype="COLOR",
        min=0.0,
        max=1.0,
        size=4,
    )

    def getWidth(self):
        return self.width / 100

    def getRadius(self):
        return self.radius / 100

    def to_dict(self):
        return {
            "is_enabled": self.is_enabled,
            "lazy_mode": self.lazy_mode,
            "enable_floating_toggle": self.enable_floating_toggle,
            "toggle_position": list(self.toggle_position),
            "toggle_color": list(self.toggle_color),
            "is_visible": self.isVisible,
            "input_mode": self.input_mode,
            "swap_panrotate": self.swap_panrotate,
            "width": self.width,
            "radius": self.radius,
            "use_multiple_colors": self.use_multiple_colors,
            "overlay_main_color": list(self.overlay_main_color),
            "overlay_secondary_color": list(self.overlay_secondary_color),
        }

    def from_dict(self, data: dict):
        self.is_enabled = data.get("is_enabled", True)
        self.lazy_mode = data.get("lazy_mode", False)
        self.enable_floating_toggle = data.get("enable_floating_toggle", False)
        self.toggle_position = data.get("toggle_position", (0, 0))
        self.toggle_color = data.get("toggle_color", (0.1, 0.1, 0.2, 0.5))
        self.isVisible = data.get("is_visible", False)
        self.input_mode = data.get("input_mode", "FULL")
        self.swap_panrotate = data.get("swap_panrotate", False)
        self.width = data.get("width", 40.0)
        self.radius = data.get("radius", 35.0)
        self.use_multiple_colors = data.get("use_multiple_colors", False)
        self.overlay_main_color = data.get("overlay_main_color", (1.0, 1.0, 1.0, 0.01))
        self.overlay_secondary_color = data.get("overlay_secondary_color", (1.0, 1.0, 1.0, 0.01))


def navigation_settings() -> SCULPT_DECK_PG_NavigationSettings:
    return preferences().navigation


def draw_input_mode(layout: UILayout, settings, description_as_label: bool):
    """The input mode, Lazy Mode and the floating toggle; in the sidebar the mode's description heads the box"""
    box = layout.box()
    if description_as_label:
        box.label(
            text=UILayout.enum_item_description(settings, "input_mode", settings.input_mode),
            icon_value=UILayout.enum_item_icon(settings, "input_mode", settings.input_mode),
        )
        row = box.row()
        row.prop(settings, "input_mode", expand=True)
    else:
        box.label(text="Input Mode")
        box.use_property_split = True
        col = box.column()
        description = UILayout.enum_item_description(settings, "input_mode", settings.input_mode)
        col.prop(settings, "input_mode", text=description, expand=True)

    col = box.column(align=True)
    col.use_property_split = True
    col.prop(settings, "lazy_mode")
    if settings.input_mode == "FULL":
        col.prop(settings, "enable_floating_toggle")


def draw_control_zones(layout: UILayout, settings, object_tap=None):
    """The control zones and their overlay; the sidebar also shows the object tap's Tap to Select/Switch here"""
    col = layout.column(align=True)
    col.prop(settings, "isVisible", text="Show Overlay")
    col.prop(settings, "swap_panrotate")
    if object_tap is not None:
        col.prop(object_tap, "tap_to_switch")
    col.prop(settings, "use_multiple_colors")
    col = layout.column()
    col.prop(settings, "overlay_main_color", text="Main Color")
    if settings.use_multiple_colors:
        col.prop(settings, "overlay_secondary_color", text="Secondary Color")
    col.prop(settings, "width", slider=True)
    col.prop(settings, "radius", slider=True)


def draw_preferences(layout: UILayout, settings):
    draw_input_mode(layout, settings, description_as_label=False)

    box = layout.box()
    box.prop(settings, "is_enabled", text="Control Zones")
    col = box.column()
    col.use_property_split = True
    col.active = settings.is_enabled
    draw_control_zones(col, settings)


def register():
    bpy.utils.register_class(SCULPT_DECK_PG_NavigationSettings)
    add_section("navigation", SCULPT_DECK_PG_NavigationSettings, draw_preferences, order=10)


def unregister():
    remove_section("navigation")
    bpy.utils.unregister_class(SCULPT_DECK_PG_NavigationSettings)
