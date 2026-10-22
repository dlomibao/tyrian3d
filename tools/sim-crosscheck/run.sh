#!/bin/bash
# Cross-checks the TypeScript world port (src/sim/tyrian2.ts, varz.ts, backgrnd.ts) against the
# real OpenTyrian C code: both run tests/sim/worldDriver.ts's loop (harness.c is its C twin) on
# every level the episode scripts reach directly, and the per-tick traces (enemies, enemy shots,
# scroll state, sound queue, final RNG value) must be identical.
#
# Usage: tools/sim-crosscheck/run.sh <opentyrian checkout> <tyrian data dir> [ticks]
# Needs SDL2 (sdl2-config). Builds in a temp dir; nothing is written to the repo.
#
# Known: the C build segfaults on a few levels when background 3 scrolls past the top of its map
# in one tick (draw_background_3 then reads before megaData3.mainmap); the TS port skips those
# out-of-range cells. For those levels the C trace is a prefix of the TS trace.
set -euo pipefail

OT=${1:?opentyrian checkout}
DATA=${2:?tyrian data dir}
TICKS=${3:-6000}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
WORK=$(mktemp -d)

CFLAGS="-std=gnu11 -O1 -g $(sdl2-config --cflags) -I$OT/src -w"
mkdir -p "$WORK/obj"
for f in "$OT"/src/*.c; do
  n=$(basename "$f" .c)
  extra=""
  if [ "$n" = opentyr ]; then extra="-Dmain=opentyr_main"; fi
  cc $CFLAGS $extra -c "$f" -o "$WORK/obj/$n.o"
done
cc $CFLAGS -c "$HERE/harness.c" -o "$WORK/obj/harness.o"
cc "$WORK"/obj/*.o $(sdl2-config --libs) -lm -o "$WORK/harness"

mkdir -p "$WORK/traces"
(cd "$REPO" && TYRIAN_DATA="$DATA" TICKS="$TICKS" CROSSCHECK_OUT="$WORK/traces" npx vitest run tests/sim/crosscheck.test.ts >/dev/null)

pass=0
fail=0
while read -r ep ml; do
  [ -z "$ep" ] && continue
  set +e
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$WORK/harness" "$DATA" "$ml" "$TICKS" "$ep" 1 > "$WORK/traces/c_${ep}_${ml}.txt" 2>/dev/null
  rc=$?
  set -e
  if cmp -s "$WORK/traces/c_${ep}_${ml}.txt" "$WORK/traces/ts_${ep}_${ml}.txt"; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    echo "DIFF episode $ep section $ml (C exit $rc):"
    diff "$WORK/traces/c_${ep}_${ml}.txt" "$WORK/traces/ts_${ep}_${ml}.txt" | head -6 || true
  fi
done < "$WORK/traces/cases.txt"
echo "identical: $pass, different: $fail (traces in $WORK/traces)"
