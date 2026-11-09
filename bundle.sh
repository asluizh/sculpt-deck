# Builds bin/sculpt_deck.zip from the working tree.
#
#   ./bundle.sh                       the whole add-on
#   ./bundle.sh --without navigation  without source/navigation, which can be removed as a unit (ADR 0001); the
#                                     tree itself isn't touched (dev/tests/smoke.sh checks this build too)
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
  while [[ $# -gt 0 ]]; do
    if [[ "$1" == "--without" && -n "${2:-}" && -d "$dir/source/$2" ]]; then
      rm -rf "${dir:?}/source/$2"
      shift 2
    else
      echo "bundle.sh: expected --without <a part in source/>, got: $*" >&2
      rm -rf "$dir"
      return 1
    fi
  done
  cd "$dest"
  zip -r "sculpt_deck.zip" "sculpt_deck" -x "*__pycache__*" "*.pyc"
  cd ".."
  rm -rf "$dir"
}

bundle "$@"
