"""The add-on preferences, where every part keeps its settings."""

import bpy

from ... import __package__ as package  # the add-on's root package


def preferences():
    """The add-on preferences"""
    return bpy.context.preferences.addons[package].preferences  # type: ignore
