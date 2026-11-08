#!/usr/bin/env bash
# UI scenarios: builds and installs Sculpt Deck into a throwaway Blender profile, starts a headless weston session
# with Xwayland (no screen needed, nothing shows on yours), and runs dev/tests/scenarios.py in Blender's full UI.
# Sculpt undo steps only exist in the UI, so this is where undo, redo and Adjust Last Operation get tested.
#
#   dev/tests/scenarios.sh                       run every scenario
#   dev/tests/scenarios.sh detour_join ...       run only the named ones
#
# Needs weston (with its xwayland module) and the Blender flatpak. Log: bin/test/scenarios.log
set -euo pipefail

source "$(dirname "$0")/common.sh"
results="$work/scenarios_results.txt"
log="$work/scenarios.log"
weston_log="$work/weston.log"

build_and_install >"$log"
rm -f "$results"

weston --backend=headless --renderer=gl --xwayland --socket="sculpt-deck-test-$$" --width=1600 --height=1000 \
  >"$weston_log" 2>&1 &
weston_pid=$!
trap 'kill "$weston_pid" 2>/dev/null || true' EXIT

display=""
for _ in $(seq 1 50); do
  display="$(grep -oE 'xserver listening on display :[0-9]+' "$weston_log" | grep -oE ':[0-9]+' || true)"
  [[ -n "$display" ]] && break
  sleep 0.2
done
if [[ -z "$display" ]]; then
  cat "$weston_log"
  echo "SCENARIOS FAILED: weston didn't start Xwayland"
  exit 1
fi

# --enable-event-simulate: Blender ignores real input and accepts window.event_simulate
timeout 600 bash -c "$(declare -f blender); work='$work'; blender --socket=x11 --nosocket=wayland --env=DISPLAY=$display \
  -- --enable-event-simulate --python '$root/dev/tests/scenarios.py' -- '$results' $*" >>"$log" || true

if [[ ! -s "$results" ]]; then
  tail -40 "$log"
  echo "SCENARIOS FAILED: no results (Blender crashed or timed out; log: $log)"
  exit 1
fi
cat "$results"
if grep -qE "^(FAIL|XPASS)" "$results"; then
  echo "SCENARIOS FAILED (log: $log)"
  exit 1
fi
echo "SCENARIOS OK: $(grep -c "^PASS" "$results") passed, $(grep -c "^XFAIL" "$results" || true) known failures"
