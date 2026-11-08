"""Build the Local Transform toolbar icon from Blender's Transform tool icon.

Usage: python3 make_tool_icon.py <blender>/datafiles/icons/ops.transform.transform.dat
       ../icons/ops.sculpt_deck.local_transform.dat

Tool icons are triangle lists: b"VCO\\0", width, height, x and y start bytes,
then 6 coordinate bytes per triangle and 12 color bytes (RGBA per corner).
The icon is tilted to read as "local axes", with the X arrowheads red and the
Y arrowheads green, like Blender's axis colors.
"""
import math
import sys

TILT = math.radians(-25)
SHRINK = 0.97
RED, GREEN = (255, 74, 94, 255), (130, 210, 40, 255)


def read(path):
    data = open(path, "rb").read()
    count = (len(data) - 8) // 18
    coords, colors = data[8:8 + count * 6], data[8 + count * 6:]
    return [
        (
            [(coords[i * 6 + 2 * k], coords[i * 6 + 2 * k + 1]) for k in range(3)],
            [tuple(colors[i * 12 + 4 * k:i * 12 + 4 * k + 4]) for k in range(3)],
        )
        for i in range(count)
    ]


def main(source, target):
    triangles = []
    for points, colors in read(source):
        cx = sum(p[0] for p in points) / 3 - 127.5
        cy = sum(p[1] for p in points) / 3 - 127.5
        angle = math.degrees(math.atan2(cy, cx)) % 90
        # the arrowheads are single triangles sitting on the axes
        if 55 < math.hypot(cx, cy) < 72 and (angle < 12 or angle > 78):
            colors = [RED if abs(cx) > abs(cy) else GREEN] * 3
        tilted = []
        for x, y in points:
            x, y = x - 127.5, y - 127.5
            nx = (x * math.cos(TILT) - y * math.sin(TILT)) * SHRINK + 127.5
            ny = (x * math.sin(TILT) + y * math.cos(TILT)) * SHRINK + 127.5
            tilted.append((max(0, min(255, round(nx))), max(0, min(255, round(ny)))))
        triangles.append((tilted, colors))
    data = b"VCO\x00" + bytes([255, 255, 0, 0])
    data += b"".join(bytes(c for p in points for c in p) for points, _ in triangles)
    data += b"".join(bytes(v for c in colors for v in c) for _, colors in triangles)
    open(target, "wb").write(data)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
