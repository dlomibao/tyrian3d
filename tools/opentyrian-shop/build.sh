#!/bin/bash
# Builds driver.c against an OpenTyrian checkout and regenerates the shop-trace fixture that
# tests/sim/shop.test.ts compares the TypeScript item screen (src/sim/game_menu.ts) with.
#
#   tools/opentyrian-shop/build.sh <opentyrian/src> <tyrian data dir>
#
# Needs clang and SDL2 (sdl2-config; Homebrew's sdl2 works). Builds in a temp dir.
set -euo pipefail
OT_SRC=$(cd "$1" && pwd)
DATA=$(cd "$2" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
FIXTURES="$HERE/../../tests/sim/fixtures"
# SHOP_WORK=<dir> keeps the build (and a failed run's partial trace) there.
if [ -n "${SHOP_WORK:-}" ]; then
  WORK=$SHOP_WORK
  mkdir -p "$WORK"
else
  WORK=$(mktemp -d)
  trap 'rm -rf "$WORK"' EXIT
fi

CF="$(sdl2-config --cflags) -std=gnu11 -O0 -w -DOPENTYRIAN_VERSION=\"trace\" -I$OT_SRC"
for f in "$OT_SRC"/*.c; do
  b=$(basename "$f" .c)
  [ "$b" = game_menu ] && continue # driver.c includes it
  extra=""
  [ "$b" = opentyr ] && extra="-Dmain=opentyr_main"
  clang $CF $extra -c "$f" -o "$WORK/$b.o"
done
clang $CF -c "$HERE/driver.c" -o "$WORK/driver.o"
clang "$WORK"/*.o $(sdl2-config --libs) -lm -o "$WORK/driver"

SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$WORK/driver" "$DATA" "$FIXTURES/shop-trace.script" > "$WORK/shop-trace.txt"
cp "$WORK/shop-trace.txt" "$FIXTURES/shop-trace.c.txt"
echo "wrote $FIXTURES/shop-trace.c.txt"
