#!/bin/bash
# Plays Tyrian's attract-mode demos (demo.1 .. demo.5) through OpenTyrian's real JE_main and writes
# the fixtures tests/sim/demo.test.ts compares the TypeScript port with (demo-N.c.txt).
#
#   tools/opentyrian-demo/run.sh <opentyrian checkout> <tyrian data dir>
#   tools/opentyrian-demo/run.sh <opentyrian checkout> <tyrian data dir> <demo> [every]
#       (prints one demo's trace instead)
#
# Needs clang and SDL2 (sdl2-config; Homebrew's sdl2 works) and perl. Patches a copy of OpenTyrian's
# sources in a temp dir: hooks for the driver in JE_main, demo.c's demoNum made visible, no frame
# delay (delayUntilElapsed), no save-game writes.
set -euo pipefail
OT=$(cd "$1" && pwd)
DATA=$(cd "$2" && pwd)
shift 2
HERE=$(cd "$(dirname "$0")" && pwd)
FIXTURES="${FIXTURES:-$HERE/../../tests/sim/fixtures}"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

cp -R "$OT/src" "$WORK/src"
S="$WORK/src"
patch_src() { # file, perl substitution; fails if it changes nothing
  local before
  before=$(cksum < "$S/$1")
  perl -0pi -e "$2" "$S/$1"
  if [ "$before" = "$(cksum < "$S/$1")" ]; then
    echo "patch failed: $1: $2" >&2
    exit 1
  fi
}
patch_src tyrian2.c 's/\nlevel_loop:\n/\nlevel_loop:\n\t{ extern void demo_level_tick(void); demo_level_tick(); }\n/'
patch_src tyrian2.c 's/(\tif \(reallyEndLevel\)\n\t\{\n)(\t\tgoto start_level;)/$1\t\t{ extern void demo_level_end(void); demo_level_end(); }\n$2/'
patch_src demo.c 's/static Uint8 demoNum = 0;/Uint8 demoNum = 0;/'
patch_src nortsong.c 's/(void delayUntilElapsed\(void\)\n\{\n)/$1\treturn;\n/'
patch_src config.c 's/(void JE_saveGame\(JE_byte slot, const char \*name\)\n\{\n)/$1\treturn;\n/'

CF="$(sdl2-config --cflags) -std=gnu11 -O1 -w -DOPENTYRIAN_VERSION=\"demo\" -I$S"
mkdir -p "$WORK/obj"
for f in "$S"/*.c; do
  b=$(basename "$f" .c)
  extra=""
  [ "$b" = opentyr ] && extra="-Dmain=opentyr_main"
  clang $CF $extra -c "$f" -o "$WORK/obj/$b.o"
done
clang $CF -c "$HERE/driver.c" -o "$WORK/driver.o"
clang "$WORK"/obj/*.o "$WORK/driver.o" $(sdl2-config --libs) -lm -o "$WORK/driver" 2>/dev/null

driver() {
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$WORK/driver" "$DATA" "$@" 2>/dev/null
}

if [ $# -gt 0 ]; then
  driver "$@"
  exit 0
fi

EVERY=${EVERY:-10}
for n in 1 2 3 4 5; do
  out="$FIXTURES/demo-$n.c.txt"
  { echo "# demo $n every $EVERY"; driver "$n" "$EVERY"; } > "$out"
  echo "wrote $out"
done
