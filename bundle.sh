bundle() {
  local dest dir
  dest="bin"
  dir="bin/sculpt_deck"
  mkdir -p "$dir"
  cp "__init__.py" "$dir"
  cp "preferences.py" "$dir"
  cp "blender_manifest.toml" "$dir"
  cp -r "source" "$dir"
  cp -r "icons" "$dir"
  cd "$dest"
  zip -r "sculpt_deck.zip" "sculpt_deck"
  cd ".."
  rm -rf "$dir"
}

bundle
