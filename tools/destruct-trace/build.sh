#!/bin/bash
# Builds driver.c against an OpenTyrian checkout and regenerates the Destruct trace fixture that
# tests/destruct/trace.test.ts compares the TypeScript port (src/destruct/sim.ts) with.
#
#   tools/destruct-trace/build.sh <opentyrian/src> <tyrian data dir>
#
# Needs clang and SDL2 (sdl2-config; Homebrew's sdl2 works). Builds in a temp dir.
# To see one case line by line: build, then run `driver <data> <seed> <mode> <ticks> full`
# (KEEP=1 keeps the build dir and prints it).
set -euo pipefail
OT_SRC=$(cd "$1" && pwd)
DATA=$(cd "$2" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
OUT="$HERE/../../tests/destruct/fixtures/destruct-trace.c.txt"
WORK=$(mktemp -d)
if [ -z "${KEEP:-}" ]; then trap 'rm -rf "$WORK"' EXIT; else echo "build dir: $WORK" >&2; fi

# -ffp-contract=off: no fused multiply-adds, so floats round as on x86-64 builds (and in JS). clang
# on arm64 otherwise fuses `unitY - 7 - sinf(angle) * 10` and the shots land an ulp apart.
CF="$(sdl2-config --cflags) -std=gnu11 -O0 -ffp-contract=off -w -DOPENTYRIAN_VERSION=\"trace\" -I$OT_SRC"
for f in "$OT_SRC"/*.c; do
  b=$(basename "$f" .c)
  [ "$b" = destruct ] && continue # driver.c includes it
  extra=""
  [ "$b" = opentyr ] && extra="-Dmain=opentyr_main"
  clang $CF $extra -c "$f" -o "$WORK/$b.o"
done
clang $CF -c "$HERE/driver.c" -o "$WORK/driver.o"
clang "$WORK"/*.o $(sdl2-config --libs) -lm -o "$WORK/driver"

mkdir -p "$(dirname "$OUT")"
: > "$OUT"
# The cases tests/destruct/trace.test.ts replays: seed, mode, ticks.
while read -r seed mode ticks; do
  echo "C $seed $mode $ticks" >> "$OUT"
  "$WORK/driver" "$DATA" "$seed" "$mode" "$ticks" >> "$OUT"
done <<CASES
1 0 6000
2 0 6000
3 1 6000
4 2 6000
5 3 6000
6 4 6000
7 0 6000
8 1 6000
9 2 6000
10 3 6000
11 4 6000
12 0 6000
CASES
echo "wrote $OUT"
