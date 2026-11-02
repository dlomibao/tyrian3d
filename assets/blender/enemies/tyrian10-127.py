"""Armour crate +2 (tyrian.shp #10 frame 127, enemy type 561): a 3D version of its sprite.

One of the three crates the armour ship (tyrian10-279, enemy type 560) leaves when it's shot down
(JE_main's low-armour warning gives it enemydie 561-563 at random); picking it up adds 2 armour.
Its sprite is the strapped crate's (tyrian10-129, +4) silhouette and shading in plain grey metal,
with no straps, so it is that block (the same corners, profile and rounded ends, imported from
tyrian10-129.py), each top face coloured from the sprite pixel under it.

Run: blender --background --python assets/blender/enemies/tyrian10-127.py [-- --preview out.png]
"""

import importlib.util
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b039 as lib  # noqa: E402

NAME = "tyrian10-127"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# The sprite's ramp, darkest to lightest (palette indices), its shadowed lower-right side, and the
# metal's finish.
RAMP = ((2, 3, 4), (5, 6, 7), (8, 9, 10), (11, 12, 13, 14))
SIDE = 161
FINISH = dict(metallic=0.65, roughness=0.32)


def crate_geometry():
    """tyrian10-129.py as a module (its geometry: section, STATIONS)."""
    path = Path(__file__).with_name("tyrian10-129.py")
    spec = importlib.util.spec_from_file_location("crate_129", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(sprite, name=NAME, ramp=RAMP, side=SIDE, finish=FINISH):
    crate = crate_geometry()
    coll = common.reset_collection(name)
    mats = [common.palette_material(sprite, r[len(r) // 2], name, **finish) for r in ramp]
    mats.append(common.palette_material(sprite, side, name, metallic=0.0, roughness=0.9))
    under = len(mats) - 1
    slot_of = {i: k for k, r in enumerate(ramp) for i in r}
    slot_of.update({64: under, 161: under, 16: under})
    bm = bmesh.new()
    rings = [crate.section(s, k) for s, k in crate.STATIONS]
    lib.ring_loft(bm, rings, 1)
    pixels = sprite["frames"][0]["pixels"]
    lib.paint_from_sprite(bm, pixels, lambda i: slot_of.get(i), under_slot=under, min_nz=-0.2)
    return [common.mesh_object(name, bm, mats, coll, smooth=False)]


def main(name=NAME, **kw):
    sprite = common.load_sprite(ROOT, name)
    objs = build(sprite, name, **kw)
    common.export_sprite_model(ROOT, objs, f"enemies/{name}", sprite["sprites"])
    lib.preview(objs, ROOT, name, sprite)


if __name__ == "__main__":
    main()
