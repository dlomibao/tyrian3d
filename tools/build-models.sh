#!/usr/bin/env bash
# Rebuild Blender models headless, several at a time: every script in assets/blender/ (except
# common.py), or just the ones given. Each writes its .glb to public/models/ and, for models that
# replace sprites, its entry to src/render/spriteModels/.
#
#   tools/build-models.sh [-j jobs] [-p preview_dir] [script.py ...]
#
# -p also renders each model beside its sprite to <preview_dir>/<name>.png (needs the reference
# images from `npm run catalogue`). Blender comes from $BLENDER, `blender` on the PATH, or the
# default macOS install.
#
# A model with concept maps (assets/blender/textures/<name>/maps.json, DECISIONS.md D44) is textured
# (unless its maps.json says "bake": "model": its script bakes its own maps, D50) right after it's built (assets/blender/texture_bake.py, which must run on a fresh build), with all
# its animation frames: a build alone exports it plain, and a plain model, or a plain frame among
# textured ones, is the wrong look (a frame left plain flashes lighter, D46). -n builds without the
# bake (the models come out plain). An assembly's bake needs .shape/<name>/regions.json
# (tools/sprite_shape.py <name>).
set -euo pipefail
cd "$(dirname "$0")/.."

jobs=$(( $(getconf _NPROCESSORS_ONLN) / 2 ))
preview=""
texture=1
while getopts "j:p:n" opt; do
  case $opt in
    j) jobs=$OPTARG ;;
    p) preview=$OPTARG ;;
    n) texture=0 ;;
    *) exit 2 ;;
  esac
done
shift $((OPTIND - 1))

blender=${BLENDER:-$(command -v blender || echo /Applications/Blender.app/Contents/MacOS/Blender)}
if [ $# -eq 0 ]; then
  set -- $(find assets/blender -name '*.py' ! -name common.py ! -name 'lib_*' | sort)
fi

# The texture_bake.py name for a script's model, if it has concept maps: the script's own name, a tile
# model's entry (tile:<entry>, found by the model path it writes), or the Talon's. Maps whose maps.json
# says "bake": "model" are not baked here: the model's own script textures it (the Talon, D50).
bake_name() {
  local n=$1 entry
  if [ -f "assets/blender/textures/$n/maps.json" ]; then
    own_bake "assets/blender/textures/$n/maps.json" || echo "$n"
    return
  fi
  if [ "$n" = usp_talon ] && [ -f assets/blender/textures/ship-usp-talon-light-fighter/maps.json ]; then
    own_bake assets/blender/textures/ship-usp-talon-light-fighter/maps.json || echo ship-usp-talon-light-fighter
    return
  fi
  # Several entries can share a model (a variant pattern, e.g. a copy cut by the map's edge): use the
  # one with concept maps.
  for entry in $(grep -l "\"model\": \"tiles/[^\"]*/${n//_/-}\"" src/render/tileModels/*.json 2>/dev/null); do
    entry=$(basename "$entry" .json)
    if [ -f "assets/blender/textures/$entry/maps.json" ]; then
      own_bake "assets/blender/textures/$entry/maps.json" || echo "tile:$entry"
      return 0
    fi
  done
  return 0
}

# Whether a maps.json says the model's own script textures it ("bake": "model").
own_bake() {
  grep -q '"bake": *"model"' "$1"
}

build() {
  local script=$1 name log bake
  name=$(basename "$script" .py)
  log=$(mktemp)
  local args=(--background --factory-startup --python "$script")
  [ -n "$preview" ] && args+=(-- --preview "$preview/$name.png")
  if "$blender" "${args[@]}" >"$log" 2>&1 && ! grep -q "^Traceback\|^Error" "$log"; then
    grep "^exported" "$log" || echo "built $script"
  else
    echo "FAILED $script:" >&2
    cat "$log" >&2
    rm -f "$log"
    return 1
  fi
  bake=$(bake_name "$name")
  if [ "$texture" = 1 ] && [ -n "$bake" ]; then
    if [[ "$bake" == assembly-* ]] && [ ! -f ".shape/$bake/regions.json" ]; then
      echo "FAILED $script: built but not textured; run tools/sprite_shape.py $bake first (or -n)" >&2
      rm -f "$log"
      return 1
    fi
    if "$blender" --background --factory-startup --python assets/blender/texture_bake.py -- "$bake" >"$log" 2>&1 \
      && ! grep -q "^Traceback\|^Error" "$log"; then
      grep "^textured" "$log" || true
    else
      echo "FAILED $script: built, but texturing it ($bake) failed:" >&2
      cat "$log" >&2
      rm -f "$log"
      return 1
    fi
  fi
  rm -f "$log"
}
export -f build bake_name own_bake
export blender preview texture
[ -n "$preview" ] && mkdir -p "$preview"
printf '%s\n' "$@" | xargs -P "$jobs" -I{} bash -c 'build "$@"' _ {}
