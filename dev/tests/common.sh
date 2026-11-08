# Shared by the dev/tests scripts: paths, and building and installing Sculpt Deck into a throwaway Blender profile
# (bin/test/profile, never your own). The Blender flatpak can't see /tmp, so everything stays inside the repo.

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
work="$root/bin/test"
mkdir -p "$work"

# run the Blender flatpak with the throwaway profile; extra flatpak options go before "--"
blender() {
  local flatpak_args=()
  while [[ $# -gt 0 && "$1" != "--" ]]; do flatpak_args+=("$1"); shift; done
  [[ "${1:-}" == "--" ]] && shift
  flatpak run --env=BLENDER_USER_RESOURCES="$work/profile" "${flatpak_args[@]}" --command=blender \
    org.blender.Blender "$@" 2>&1 | grep -v '^F: ' # flatpak's own sandbox notices
}

# fresh profile with the current code installed as the user_default extension; arguments go to bundle.sh
# (e.g. --without navigation)
build_and_install() {
  rm -rf "$work/profile" "$root/bin/sculpt_deck.zip"
  mkdir -p "$work/profile"
  (cd "$root" && ./bundle.sh "$@" >/dev/null)
  blender -- --background --factory-startup --command extension install-file -r user_default -e \
    "$root/bin/sculpt_deck.zip"
}
