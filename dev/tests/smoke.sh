#!/usr/bin/env bash
# Smoke check: builds the extension, installs it into a throwaway Blender profile (bin/test/profile, never your
# own), enables, disables and re-enables it, and compares what got registered with dev/tests/smoke_expected.txt.
# Fails on any error, traceback or warning Blender prints, or on a difference from the expected output.
#
#   dev/tests/smoke.sh            run the check
#   dev/tests/smoke.sh --update   run it and accept the new output as expected
#
# Uses the Blender flatpak (org.blender.Blender), which can't see /tmp, so everything stays inside the repo.
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
work="$root/bin/test"
expected="$root/dev/tests/smoke_expected.txt"
actual="$work/smoke_actual.txt"
log="$work/smoke.log"

cd "$root"
rm -rf "$work/profile" "$root/bin/sculpt_deck.zip"
mkdir -p "$work/profile"
./bundle.sh >/dev/null

blender() {
  flatpak run --env=BLENDER_USER_RESOURCES="$work/profile" --command=blender org.blender.Blender \
    --background --factory-startup "$@" 2>&1 | grep -v '^F: ' # flatpak's own sandbox notices
}

{
  blender --command extension install-file -r user_default -e "$root/bin/sculpt_deck.zip"
  # no --factory-startup here: it would skip the extension just installed into the profile
  flatpak run --env=BLENDER_USER_RESOURCES="$work/profile" --command=blender org.blender.Blender \
    --background --python-exit-code 1 --python "$root/dev/tests/smoke_check.py" -- "$actual" 2>&1 | grep -v '^F: '
} >"$log" || true

if ! grep -q "^SMOKE OK" "$log" || grep -qiE "error|traceback|warning" "$log"; then
  cat "$log"
  echo "SMOKE FAILED (log: $log)"
  exit 1
fi

if [[ "${1:-}" == "--update" ]]; then
  cp "$actual" "$expected"
  echo "SMOKE OK, expected output updated: $expected"
  exit 0
fi

if ! diff -u "$expected" "$actual"; then
  echo "SMOKE FAILED: registered operators, classes or Action Lists changed (accept with --update)"
  exit 1
fi
echo "SMOKE OK"
