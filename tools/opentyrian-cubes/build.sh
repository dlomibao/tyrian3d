#!/bin/bash
# Builds driver.c against an OpenTyrian checkout and regenerates the cube-digest fixture that
# tests/sim/cubes.test.ts compares the TypeScript data cube reader (src/sim/cubes.ts) with.
#
#   tools/opentyrian-cubes/build.sh <opentyrian/src> <tyrian data dir>
#
# Needs clang and SDL2 (sdl2-config; Homebrew's sdl2 works). Builds in a temp dir.
set -euo pipefail
OT_SRC=$(cd "$1" && pwd)
DATA=$(cd "$2" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
FIXTURES="$HERE/../../tests/sim/fixtures"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# NDEBUG as in a release build: some cube titles and headers are longer than their buffers, which
# readEncryptedString's assert(len < size) rejects but release builds truncate.
CF="$(sdl2-config --cflags) -std=gnu11 -O0 -w -DNDEBUG -DOPENTYRIAN_VERSION=\"trace\" -I$OT_SRC"
for f in "$OT_SRC"/*.c; do
  b=$(basename "$f" .c)
  [ "$b" = game_menu ] && continue # driver.c includes it
  extra=""
  [ "$b" = opentyr ] && extra="-Dmain=opentyr_main"
  clang $CF $extra -c "$f" -o "$WORK/$b.o" &
done
wait
clang $CF -c "$HERE/driver.c" -o "$WORK/driver.o"
clang "$WORK"/*.o $(sdl2-config --libs) -lm -o "$WORK/driver"

SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$WORK/driver" "$DATA" > "$WORK/cube-digest.txt"
cp "$WORK/cube-digest.txt" "$FIXTURES/cube-digest.c.txt"
echo "wrote $FIXTURES/cube-digest.c.txt"
