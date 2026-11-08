#!/usr/bin/env bash
# Smoke check: builds the extension, installs it into a throwaway Blender profile (bin/test/profile, never your
# own), enables, disables and re-enables it, and compares what got registered with dev/tests/smoke_expected.txt.
# Then does the same with a build without source/navigation (bundle.sh --without navigation), which has to register
# exactly what the full build does minus what navigation registers (ADR 0001: navigation can be removed as a unit).
# Fails on any error, traceback or warning Blender prints, or on a difference from the expected output.
#
#   dev/tests/smoke.sh            run the check
#   dev/tests/smoke.sh --update   run it and accept the new output as expected
set -euo pipefail

source "$(dirname "$0")/common.sh"
expected="$root/dev/tests/smoke_expected.txt"
actual="$work/smoke_actual.txt"
navigation="$work/smoke_navigation.json"

# runs smoke_check.py on a fresh install of the given build (bundle.sh arguments), failing on errors in the log
run_check() {
  local name="$1"
  shift
  # one log per build, so a passing full-build log survives the run without navigation
  local log="$work/smoke-${name// /-}.log"
  local bundle_args=() check_args=()
  while [[ $# -gt 0 && "$1" != "--" ]]; do bundle_args+=("$1"); shift; done
  [[ "${1:-}" == "--" ]] && shift
  check_args=("$@")
  {
    build_and_install "${bundle_args[@]}"
    # no --factory-startup here: it would skip the extension just installed into the profile
    blender -- --background --python-exit-code 1 --python "$root/dev/tests/smoke_check.py" -- "${check_args[@]}"
  } >"$log" || true
  if ! grep -q "^SMOKE OK" "$log" || grep -qiE "error|traceback|warning" "$log"; then
    cat "$log"
    echo "SMOKE FAILED: $name (log: $log)"
    exit 1
  fi
}

run_check "full build" -- "$actual" "$navigation"

if [[ "${1:-}" == "--update" ]]; then
  cp "$actual" "$expected"
  echo "expected output updated: $expected"
elif ! diff -u "$expected" "$actual"; then
  echo "SMOKE FAILED: registered operators, classes or Action Lists changed (accept with --update)"
  exit 1
fi

run_check "without navigation" --without navigation -- "$work/smoke_actual_without_navigation.txt" \
  --without-navigation "$expected" "$navigation"
echo "SMOKE OK (also without navigation)"
