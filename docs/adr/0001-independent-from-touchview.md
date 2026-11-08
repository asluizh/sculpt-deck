# Sculpt Deck is independent from Touchview

This project started as a fork of [nendotools/touchview](https://github.com/nendotools/touchview) (last upstream push December 2024, at 4.4.0) and is now its own add-on, **Sculpt Deck**. The goal moved from touch navigation to sculpting in Blender without a keyboard. Blender plans its own touch support across the whole interface, so general touch UI is left to Blender and this add-on covers only what sculpting needs. The fork is detached from the upstream network, gets a new extension ID, and its versions start again at 0.1, reaching 1.0 when the major features are shipped and the known bugs are fixed. Touchview's original authors stay credited and the license stays GPL.

## Consequences

- **No migration.** Saved settings, keymaps, `preferences.json` and add-on data stored in `.blend` files under the old `touchview_*` names are not carried over. Geometry and node groups already in files are unaffected; only the add-on's settings reset.
- **Navigation can be removed.** Viewport pan, rotate and zoom regions are kept for now, isolated so they can be deleted once Blender ships its own touch navigation. Navigation in 2D editors (Image, Node, View2D) is dropped. Tapping and long pressing objects are part of the sculpt workflow and stay.
- **No upstreaming.** Changes are no longer prepared for upstream.
