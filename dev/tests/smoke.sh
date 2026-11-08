#!/usr/bin/env bash
# Smoke check: builds the extension, installs it into a throwaway Blender profile (bin/test/profile, never your
# own), enables, disables and re-enables it, and compares what got registered with dev/tests/smoke_expected.txt.
# Fails on any error, traceback or warning Blender prints, or on a difference from the expected output.
#
#   dev/tests/smoke.sh            run the check
#   dev/tests/smoke.sh --update   run it and accept the new output as expected
set -euo pipefail

source "$(dirname "$0")/common.sh"
expected="$root/dev/tests/smoke_expected.txt"
actual="$work/smoke_actual.txt"
log="$work/smoke.log"

{
  build_and_install
  # no --factory-startup here: it would skip the extension just installed into the profile
  blender -- --background --python-exit-code 1 --python "$root/dev/tests/smoke_check.py" -- "$actual"
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
