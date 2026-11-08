# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


bl_info = {
    "name": "Sculpt Deck",
    "description": "Sculpt in Blender with a pen and touch, without a keyboard.",
    "author": "Luiz Alves; based on Touchview by NENDO and Karan (b3dhub)",
    "blender": (5, 2, 0),
    "version": (0, 1, 0),
    "category": "3D View",
    "location": "View3D > Sidebar > Sculpt Deck",
    "warning": "",
    "doc_url": "https://github.com/asluizh/sculpt-deck",
    "tracker_url": "https://github.com/asluizh/sculpt-deck/issues",
}


import bpy

from . import preferences, source


def register():
    source.register()
    preferences.register()
    bpy.context.preferences.addons[__package__].preferences.load()  # type: ignore


# the reverse of register: the preferences hold property groups that parts of source register
def unregister():
    preferences.unregister()
    source.unregister()
