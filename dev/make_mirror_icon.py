"""Build the Mirror toolbar icon: the mesh as a solid square on the left, its
mirror image as an orange outline on the right, and a dashed mirror line
between them. Uses the shapes of make_array_icons.py, see make_tool_icon.py
for the icon format.

Usage: python3 make_mirror_icon.py ../icons
"""
import os
import sys

from make_array_icons import ACCENT, GAP, LINE, SIZE, WHITE, outline, rectangle, write

DASH = 22


def main(folder):
    offset = (SIZE + GAP) / 2 + 8
    left, right = round(128 - offset - SIZE / 2), round(128 + offset - SIZE / 2)
    bottom = round(128 - SIZE / 2)
    triangles = rectangle(left, bottom, left + SIZE, bottom + SIZE, WHITE)
    triangles += outline(right, bottom, right + SIZE, bottom + SIZE, ACCENT)
    half = LINE // 2
    for y in range(40, 216, DASH * 2):
        triangles += rectangle(128 - half, y, 128 + half + 1, min(y + DASH, 216), WHITE)
    write(os.path.join(folder, "ops.sculpt_deck.mirror.dat"), triangles)


if __name__ == "__main__":
    main(sys.argv[1])
