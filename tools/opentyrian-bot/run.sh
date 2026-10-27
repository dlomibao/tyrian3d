#!/bin/bash
# Runs OpenTyrian's real JE_loadMap/JE_main with the episode-test bot (driver.c) and regenerates the
# fixtures tests/sim/botTrace.test.ts compares the TypeScript port with:
#   bot-routes.c.txt  where JE_loadMap goes from each episode-script section with an item screen
#                     (]I[), letting constantPlay pick the next level;
#   bot-*.c.txt       the bot playing a level through the whole of JE_main, sampled.
#
#   tools/opentyrian-bot/run.sh <opentyrian checkout> <tyrian data dir>
#   tools/opentyrian-bot/run.sh <opentyrian checkout> <tyrian data dir> play|play2 <episode> <section> <ticks> [every]
#       (prints a trace instead, for investigating a level)
#
# Needs clang and SDL2 (sdl2-config; Homebrew's sdl2 works) and perl. Patches a copy of OpenTyrian's
# sources in a temp dir: hooks for the driver in JE_main and JE_nextEpisode, no frame delay
# (delayUntilElapsed), no save-game writes (JE_saveGame; the ]b[ script command saves one).
set -euo pipefail
OT=$(cd "$1" && pwd)
DATA=$(cd "$2" && pwd)
shift 2
HERE=$(cd "$(dirname "$0")" && pwd)
FIXTURES="$HERE/../../tests/sim/fixtures"
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
patch_src tyrian2.c 's/(start_level_first:.*?\n\tJE_loadMap\(\);\n)/$1\t{ extern void bot_level_loaded(void); bot_level_loaded(); }\n/s'
patch_src tyrian2.c 's/\nlevel_loop:\n/\nlevel_loop:\n\t{ extern void bot_level_tick(void); bot_level_tick(); }\n/'
patch_src tyrian2.c 's/(\tif \(reallyEndLevel\)\n\t\{\n)(\t\tgoto start_level;)/$1\t\t{ extern void bot_level_end(void); bot_level_end(); }\n$2/'
patch_src mainint.c 's/(void JE_nextEpisode\(void\)\n\{\n)/$1\t{ extern void bot_episode_end(void); bot_episode_end(); }\n/'
patch_src nortsong.c 's/(void delayUntilElapsed\(void\)\n\{\n)/$1\treturn;\n/'
patch_src keyboard.c 's/(void mouseGetRelativePosition\(Sint32 \*const out_x, Sint32 \*const out_y\)\n\{\n)/$1\t{ extern int bot_mouse_x, bot_mouse_y; *out_x = bot_mouse_x; *out_y = bot_mouse_y; return; }\n/'
patch_src config.c 's/(void JE_saveGame\(JE_byte slot, const char \*name\)\n\{\n)/$1\treturn;\n/'

CF="$(sdl2-config --cflags) -std=gnu11 -O1 -w -DOPENTYRIAN_VERSION=\"bot\" -I$S"
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
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$WORK/driver" "$1" "$DATA" "${@:2}" 2>/dev/null
}

if [ "${1:-}" = play ] || [ "${1:-}" = play2 ]; then
  driver "$@"
  exit 0
fi

# Every section that sets the map choices (]G[) and then opens the item screen (]I[), and episode 1
# section 1 (]J 002[ into section 2's item screen, how a new game starts).
routes=(
  "1 1" "1 4" "1 12" "1 15" "1 17" "1 18" "1 20" "1 22" "1 24" "1 27" "1 30" "1 32" "1 35" "1 37" "1 40"
  "2 1" "2 3" "2 5" "2 7" "2 9" "2 11" "2 14" "2 16" "2 18" "2 20" "2 23"
  "3 1" "3 3" "3 5" "3 7" "3 9" "3 11" "3 14" "3 16" "3 18" "3 20" "3 22" "3 24"
  "4 1" "4 3" "4 5" "4 7" "4 9" "4 11" "4 13" "4 15" "4 17" "4 19" "4 21" "4 24" "4 26" "4 28" "4 30" "4 33"
  "4 35" "4 39" "4 44" "4 46" "4 49" "4 51"
)
out="$FIXTURES/bot-routes.c.txt"
: > "$out"
for r in "${routes[@]}"; do
  driver route $r >> "$out"
done
echo "wrote $out"

# name episode section ticks every
play_case() { # name episode section ticks every [mode]
  local mode=${6:-play}
  out="$FIXTURES/bot-$1.c.txt"
  { echo "# $mode $2 $3 $4 $5"; driver "$mode" "$2" "$3" "$4" "$5"; } > "$out"
  echo "wrote $out"
}
play_case tyrian 1 3 60000 50       # episode 1's first level, played to its end
play_case squadron 4 45 20000 100   # the episode 4 galaga bonus game (it never ends)
play_case two-players 1 3 60000 25 play2 # a two-player game: player 2 links, unlinks, dies
play_case ale 1 41 30000 100        # the episode 1 galaga bonus game (past tick 22212 the
                                    # dragonwing, player 2, rams an enemy: two-player collisions)
