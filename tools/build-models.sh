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
set -euo pipefail
cd "$(dirname "$0")/.."

jobs=$(( $(getconf _NPROCESSORS_ONLN) / 2 ))
preview=""
while getopts "j:p:" opt; do
  case $opt in
    j) jobs=$OPTARG ;;
    p) preview=$OPTARG ;;
    *) exit 2 ;;
  esac
done
shift $((OPTIND - 1))

blender=${BLENDER:-$(command -v blender || echo /Applications/Blender.app/Contents/MacOS/Blender)}
if [ $# -eq 0 ]; then
  set -- $(find assets/blender -name '*.py' ! -name common.py | sort)
fi

build() {
  local script=$1 name log
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
  rm -f "$log"
}
export -f build
export blender preview
[ -n "$preview" ] && mkdir -p "$preview"
printf '%s\n' "$@" | xargs -P "$jobs" -I{} bash -c 'build "$@"' _ {}
