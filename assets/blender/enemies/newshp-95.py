"""newshp-95 (green small missile): the green palette swap of newshp-19 (D65, D120, D122, D123).

newshp.shp size 1, frames 95/114/133/152: pixel for pixel the drawing of newshp-19 (19/38/57/76)
with the brown motor casing (19/21 shade, 24/26 sheen, 23/25 body) swapped for green (35/37,
40/42, 39/41). Every other index (grey nose/aft body, 103/101 fins and vane housings, the red-orange
exhaust flicker) is the same on every frame. So ONE geometry: newshp-19.py's build_missile, loaded
read-only, called with the green body pair read from the sprite:
  band = trimmed median of rows 5 / 9 (cols 5-7: 35 40 39) -> 39
  mid  = trimmed median of rows 6-8 (cols 5-7: 37 42 41)  -> 41
(newshp-19 passes (23, 25) from the same rows.) The frames only change colours (D17): the bell,
vane housings and flame cores carry palette_material frames= maps keyed by THIS model's frames.

WHAT IT IS: a launched missile (type 460, mv(0,5), launched by newshs-93): flies down the screen,
the grey ogive nose (row 13) leads, nozzle/fins/flame at the top. Free flying, round, closed belly.

The sprite comes from reference/models/newshp-95/sprite.json (made from the game data: the catalogue
bot never saw it on screen).
"""

import importlib.util
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "assets" / "blender")]
import common  # noqa: E402

NAME = "newshp-95"
FRAMES = [95, 114, 133, 152]


def load_missile_module():
    """newshp-19.py, read-only (its name has a hyphen, so importlib)."""
    spec = importlib.util.spec_from_file_location("newshp_19", ROOT / "assets" / "blender" / "enemies" / "newshp-19.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def trimmed_median(vals, colors):
    """Median palette index of a region, dropping the darkest and brightest (lighting)."""
    luma = lambda i: sum(w * c for w, c in zip((0.299, 0.587, 0.114), colors[str(i)]))
    s = sorted(vals, key=luma)
    if len(s) > 2:
        s = s[1:-1]
    return s[len(s) // 2]


def body_pair(sprite):
    px = sprite["frames"][0]["pixels"]
    band = trimmed_median([px[r][c] for r in (5, 9) for c in (5, 6, 7)], sprite["colors"])
    mid = trimmed_median([px[r][c] for r in (6, 7, 8) for c in (5, 6, 7)], sprite["colors"])
    return band, mid


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(ROOT, NAME)
    pair = body_pair(sprite)
    assert pair == (39, 41), pair
    mis = load_missile_module()
    coll = common.reset_collection(NAME)
    objs = mis.build_missile(sprite, NAME, coll, FRAMES, pair)
    common.export_sprite_model(ROOT, objs, "enemies/newshp-95", sprite["sprites"])


if __name__ == "__main__":
    main()
