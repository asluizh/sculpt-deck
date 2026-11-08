from ..utils.constants import pivot_icon_items

###
#  Config Standard
#  ( TYPE  BINDING  COMMAND  ICON )
#  @TYPE    - button type to instance (enum, bool, simple/default)
#  @BINDING - used to determine context and visibility
#  @COMMAND - operator to call when activated
#  @ICON    - icon to show on Gizmo
###

# Simple 2D Gizmo
controllerConfig = {
    "type": "default",
    "binding": {"location": "", "name": "menu_controller"},
    "command": "sculpt_deck.move_float_menu",
    "icon": "BLANK1",
    "use_grab_cursor": True,
}

floatingToggleConfig = {
    "type": "boolean",
    "binding": {"location": "", "name": "float_toggle"},
    "command": "sculpt_deck.move_toggle_button",
    "onIcon": "OUTLINER_DATA_CAMERA",
    "offIcon": "GREASEPENCIL",
    "use_grab_cursor": True,
}

gizmo_colors = {
    "disabled": {
        "color": [0.0, 0.0, 0.0],
        "color_highlight": [0.0, 0.0, 0.0],
        "alpha": 0.3,
        "alpha_highlight": 0.3,
    },
    "active": {
        "color": [0.0, 0.0, 0.0],
        "alpha": 0.5,
        "color_highlight": [0.5, 0.5, 0.5],
        "alpha_highlight": 0.5,
    },
    "error": {
        "color": [0.3, 0.0, 0.0],
        "alpha": 0.15,
        "color_highlight": [1.0, 0.2, 0.2],
        "alpha_highlight": 0.5,
    },
    "warn": {
        "color": [0.35, 0.3, 0.14],
        "alpha": 0.15,
        "color_highlight": [0.8, 0.7, 0.3],
        "alpha_highlight": 0.3,
    },
}

toggle_colors = {
    "active": {
        "color": [0.1, 0.1, 0.2],
        "alpha": 0.5,
        "color_highlight": [0.15, 0.15, 0.3],
        "alpha_highlight": 0.7,
    },
    "inactive": {
        "color": [0.0, 0.0, 0.0],
        "alpha": 0.5,
        "color_highlight": [0.05, 0.05, 0.05],
        "alpha_highlight": 0.7,
    },
}

# Enum 2D Gizmo
#
# not implemented yet
pivotModeConfig = {
    "type": "enum",
    "binding": {"location": "prefs", "name": "pivot_mode"},
    "command": "",
    "icons": pivot_icon_items,
}
