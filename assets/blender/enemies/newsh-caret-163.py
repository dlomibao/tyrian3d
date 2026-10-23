"""Blue energy orb (newsh^.shp frames 163 and 165, newshm.shp frames 129 and 131): a 3D version
of its sprite.

Seen in episode 1 (level 1.33) and episode 4 (level 4.4). A round ball of energy: a white-hot
core (index 143) fading through pale cyan (141, 139) and light blue (157) to a deep blue rim
(154), with a thin dark-blue halo. The frames only pulse it a pixel bigger and back, so one model
covers all four.

It is one round glowing ball whose top faces are banded from the centre out like the sprite.

Run: blender --background --python assets/blender/enemies/newsh-caret-163.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b046 as lib  # noqa: E402

NAME = "newsh-caret-163"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(211, metallic=0.2, roughness=0.5, emission_strength=1.0),  # 0 dark-blue halo
        pal(154, roughness=0.3, emission_strength=2.5),  # 1 deep blue rim
        pal(157, roughness=0.3, emission_strength=3.0),  # 2 light blue
        pal(139, roughness=0.25, emission_strength=4.0),  # 3 pale cyan
        pal(143, roughness=0.2, emission_strength=6.0),  # 4 white-hot core
    ]
    HALO, RIM, BLUE, CYAN, CORE = range(5)
    bm = bmesh.new()
    # The orb is centred on the middle of the block (column 11.5, row 13.5): X = Y = 0. One
    # round glowing ball, its faces banded by how far they are from the centre seen from above, as
    # the sprite's bands are (first frame; the second is a pixel bigger).
    x, y = G.X(11.5), G.Y(13.5)
    faces = lib.ellipsoid(bm, (x, y, 0.0), (8.6 * lib.PX, 8.6 * lib.PX, 0.29), segments=20, rings=16, mat=RIM)
    bands = ((4.9, CORE), (6.2, CYAN), (7.2, BLUE), (8.2, RIM))
    for f in faces:
        c = f.calc_center_median()
        if c.z < 0:
            continue
        rad = ((c.x - x) ** 2 + (c.y - y) ** 2) ** 0.5 * 12
        f.material_index = next((m for r, m in bands if rad < r), HALO)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = lib.preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
