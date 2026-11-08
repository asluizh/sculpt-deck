from bpy_extras import view3d_utils
from mathutils import Matrix, Vector

from ..utils.constants import CANCEL, FINISHED, MODAL

###
# Gizmo drags
#  Shared by the operators the tool gizmos start. A drag confirms on release,
#  while a tap (e.g. from a pie or a widget button) leaves it running until
#  the next click, so it works with a mouse, a pen and touch alike.
###

# mouse travel before a release confirms, so a tap doesn't end the drag
DRAG_THRESHOLD = 4


def axis_on_screen(region, rv3d, point: Vector, axis: Vector) -> Vector:
    """Pixels covered by one world unit along the axis, at the point"""
    center = view3d_utils.location_3d_to_region_2d(region, rv3d, point)
    if center is None:
        return Vector((0.0, 1.0))
    side = view3d_utils.region_2d_to_location_3d(region, rv3d, center + Vector((1.0, 0.0)), point)
    step = max((side - point).length, 1e-6) * 50
    tip = view3d_utils.location_3d_to_region_2d(region, rv3d, point + axis.normalized() * step)
    screen = (tip - center) / step if tip is not None else Vector((0.0, 0.0))
    if screen.length < 1e-3:
        # the axis points at the viewer, drag up and down instead
        screen = Vector((0.0, 50 / step))
    return screen


def set_world_matrix(obj, matrix: Matrix, keep_scale: bool):
    """Setting the matrix recomputes the scale with rounding errors, moves
    and rotations keep it exact"""
    scale = obj.scale.copy()
    obj.matrix_world = matrix
    if keep_scale:
        obj.scale = scale


def distance_along(screen_axis: Vector, start: Vector, mouse: Vector) -> float:
    """World distance along an axis for a mouse drag, see axis_on_screen()"""
    return (mouse - start).dot(screen_axis) / screen_axis.length_squared


def view_plane_offset(region, rv3d, point: Vector, start: Vector, mouse: Vector) -> Vector:
    """World offset for a mouse drag in the view plane, at the point's depth"""
    begin = view3d_utils.region_2d_to_location_3d(region, rv3d, start, point)
    return view3d_utils.region_2d_to_location_3d(region, rv3d, mouse, point) - begin


class ViewDrag:
    """Modal handling for a drag. Subclasses implement drag(), restore() and
    is_identity(), and optionally confirmed() and header_text()."""

    # the tool gizmos hide while a drag runs
    running = False
    status = "Drag to adjust  •  Release/Click: Confirm  •  Right Click/Esc: Cancel  •  Ctrl: Snap"

    def start_drag(self, context, event):
        self.start_mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self.moved = False
        type(self).running = True
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set(self.status)
        self.update(context, event)
        return MODAL

    def modal(self, context, event):
        if event.type in {"RIGHTMOUSE", "ESC"} and event.value == "PRESS":
            self.restore(context)
            return self.finish(context, CANCEL)
        if event.type in {"RET", "NUMPAD_ENTER", "SPACE"} and event.value == "PRESS":
            return self.confirm(context)
        if event.type == "LEFTMOUSE":
            self.update(context, event)
            # a tap leaves the drag running
            if event.value == "RELEASE" and self.moved:
                return self.confirm(context)
            return MODAL
        if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE", "LEFT_CTRL", "RIGHT_CTRL"}:
            self.update(context, event)
        return MODAL

    def update(self, context, event):
        mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        if (mouse - self.start_mouse).length > DRAG_THRESHOLD:
            self.moved = True
        self.drag(context, mouse, event.ctrl)
        context.area.header_text_set(self.header_text())

    def confirm(self, context):
        if self.is_identity():
            self.restore(context)
            return self.finish(context, CANCEL)
        self.confirmed(context)
        return self.finish(context, FINISHED)

    def finish(self, context, result):
        type(self).running = False
        context.workspace.status_text_set(None)
        context.area.header_text_set(None)
        context.area.tag_redraw()
        return result

    def drag(self, context, mouse: Vector, snap: bool):
        raise NotImplementedError

    def restore(self, context):
        raise NotImplementedError

    def is_identity(self) -> bool:
        raise NotImplementedError

    def confirmed(self, context):
        pass

    def header_text(self) -> str | None:
        return None


class ScreenAngle:
    """Counter-clockwise angle a drag turns around a point on screen,
    accumulated so it can go past 180°"""

    def __init__(self, center: Vector, mouse: Vector):
        self.center = center
        self.previous = mouse - center
        self.angle = 0.0

    def update(self, mouse: Vector) -> float:
        current = mouse - self.center
        if current.length > 2 and self.previous.length > 2:
            self.angle -= self.previous.angle_signed(current)
            self.previous = current
        elif self.previous.length <= 2:
            self.previous = current
        return self.angle


def facing_sign(rv3d, point: Vector, axis: Vector) -> float:
    """1 when the axis points at the viewer, so a counter-clockwise drag turns
    around it the right-handed way, else -1"""
    if rv3d.is_perspective:
        toward_viewer = rv3d.view_matrix.inverted().translation - point
    else:
        toward_viewer = rv3d.view_rotation @ Vector((0.0, 0.0, 1.0))
    return 1.0 if axis.dot(toward_viewer) >= 0 else -1.0
