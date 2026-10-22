#!/bin/bash
# Builds driver.c against an OpenTyrian checkout and regenerates the player-trace fixtures that
# tests/sim/playerTrace.test.ts compares the TypeScript port with.
#
#   tools/opentyrian-trace/build.sh <opentyrian/src> <tyrian data dir>
#
# Needs clang and SDL2 (sdl2-config; Homebrew's sdl2 works). Builds in a temp dir.
set -euo pipefail
OT_SRC=$(cd "$1" && pwd)
DATA=$(cd "$2" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
FIXTURES="$HERE/../../tests/sim/fixtures"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

CF="$(sdl2-config --cflags) -std=c11 -O0 -w -DOPENTYRIAN_VERSION=\"trace\" -I$OT_SRC"
for f in "$OT_SRC"/*.c; do
  b=$(basename "$f" .c)
  extra=""
  [ "$b" = opentyr ] && extra="-Dmain=opentyr_main"
  clang $CF $extra -c "$f" -o "$WORK/$b.o"
done
clang $CF -c "$HERE/driver.c" -o "$WORK/driver.o"
clang "$WORK"/*.o $(sdl2-config --libs) -lm -o "$WORK/driver"

# The C occasionally dies with SIGBUS mid-run: a blit reads a sprite offset through an invalid
# index (OpenTyrian's drawing, not the simulated state), and the garbage it reads varies by run.
# Retry until a run completes; completed runs are identical.
run() {
  for attempt in 1 2 3 4 5 6 7 8; do
    if "$WORK/driver" "$DATA" "$FIXTURES/$1.script" > "$WORK/$1.txt"; then
      cp "$WORK/$1.txt" "$FIXTURES/$1.c.txt"
      echo "wrote $FIXTURES/$1.c.txt"
      return 0
    fi
    echo "$1: driver crashed (attempt $attempt), retrying" >&2
  done
  return 1
}
run player-trace
run player-trace-2
