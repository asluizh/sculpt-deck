"""Build the Linear Array and Circular Array toolbar icons: the mesh as a solid
square and its copies as outlines, the last one orange. See make_tool_icon.py
for the icon format.

Usage: python3 make_array_icons.py ../icons
"""
import math
import os
import sys

WHITE = (229, 229, 229, 255)
ACCENT = (255, 160, 40, 255)
SIZE, GAP, LINE = 60, 18, 11


def rectangle(x0, y0, x1, y1, color):
    return [([(x0, y0), (x1, y0), (x1, y1)], [color] * 3), ([(x0, y0), (x1, y1), (x0, y1)], [color] * 3)]


def outline(x0, y0, x1, y1, color):
    return (
        rectangle(x0, y0, x1, y0 + LINE, color)
        + rectangle(x0, y1 - LINE, x1, y1, color)
        + rectangle(x0, y0 + LINE, x0 + LINE, y1 - LINE, color)
        + rectangle(x1 - LINE, y0 + LINE, x1, y1 - LINE, color)
    )


def squares(centers):
    """A solid square on the first center, outlines on the others"""
    triangles = []
    for i, (x, y) in enumerate(centers):
        x0, y0 = round(x - SIZE / 2), round(y - SIZE / 2)
        x1, y1 = x0 + SIZE, y0 + SIZE
        if i == 0:
            triangles += rectangle(x0, y0, x1, y1, WHITE)
        else:
            triangles += outline(x0, y0, x1, y1, ACCENT if i == len(centers) - 1 else WHITE)
    return triangles


def write(path, triangles):
    data = b"VCO\x00" + bytes([255, 255, 0, 0])
    data += b"".join(bytes(c for p in points for c in p) for points, _ in triangles)
    data += b"".join(bytes(v for c in colors for v in c) for _, colors in triangles)
    open(path, "wb").write(data)


def main(folder):
    spacing = SIZE + GAP
    write(
        os.path.join(folder, "ops.sculpt_deck.linear_array.dat"),
        squares([(128 + (i - 1) * spacing, 128) for i in range(3)]),
    )
    radius = 70
    write(
        os.path.join(folder, "ops.sculpt_deck.circular_array.dat"),
        squares([
            (128 + radius * math.cos(angle), 128 + radius * math.sin(angle))
            for angle in (math.radians(90 + i * 120) for i in range(3))
        ]),
    )


if __name__ == "__main__":
    main(sys.argv[1])
