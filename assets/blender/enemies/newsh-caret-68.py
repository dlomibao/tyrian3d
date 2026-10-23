"""Purple drill turret (newsh^.shp frame 68): a 3D version of its sprite.

Seen in episode 4 (level 4.14). A small purple ground turret: a rounded body with a dark lobe on
either side, a raised block on top carrying an arch of green lights, and a cone (a drill or
nozzle) with a bright collar pointing down the screen. One frame.

Run: blender --background --python assets/blender/enemies/newsh-caret-68.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from lib_b072 import Grid, sweep, loft_y, ellipsoid, dome, to_object  # noqa: E402

NAME = "newsh-caret-68"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = Grid(12, 14)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(86, metallic=0.35, roughness=0.45),  # 0 body
        pal(84, metallic=0.3, roughness=0.5),  # 1 side lobes
        pal(90, metallic=0.4, roughness=0.35),  # 2 top block
        pal(82, metallic=0.2, roughness=0.6),  # 3 dark band under the body
        pal(92, metallic=0.45, roughness=0.3),  # 4 bright collar
        pal(88, metallic=0.4, roughness=0.4),  # 5 cone
        pal(195, emission_strength=3.0),  # 6 green lights
    ]
    BODY, LOBE, TOP, BAND, COLLAR, CONE, GREEN = range(7)
    bm = bmesh.new()

    # Body (columns 2-10, rows 1-7) with a darker lobe on each side (columns 2-3 and 9-10).
    dome(bm, G, 6.0, 4.2, 0.0, 4.6, 3.4, 0.24, mat=BODY, segments=16, rings=8)
    for c in (3.0, 9.0):
        ellipsoid(bm, G, c, 4.8, 0.06, 1.6, 2.2, 0.14, mat=LOBE, segments=10, rings=6)
    # Dark band round the bottom of the body where the cone comes out (rows 6-7).
    loft_y(bm, G, 6.0, [(5.8, 2.9, 0.12, 0.08), (7.3, 2.9, 0.12, 0.08), (7.8, 2.4, 0.09, 0.08)], sides=12, mat=BAND)

    # Raised block on top (columns 4-8, rows 0-5), rounded, with the arch of green lights.
    loft_y(bm, G, 6.0, [(0.5, 0.0, 0.0, 0.2), (0.7, 1.8, 0.1, 0.2), (1.4, 2.5, 0.14, 0.2),
                        (5.0, 2.5, 0.14, 0.2), (5.7, 1.6, 0.08, 0.2), (5.8, 0.0, 0.0, 0.2)], sides=12, mat=TOP)
    sweep(bm, G, [(5.0, 4.8, 0.33, 0.0, 0.0), (5.0, 4.3, 0.335, 0.75, 0.03), (5.0, 2.5, 0.34, 0.75, 0.03),
                  (6.0, 2.1, 0.34, 0.75, 0.03), (7.0, 2.5, 0.34, 0.75, 0.03), (7.0, 4.3, 0.335, 0.75, 0.03),
                  (7.0, 4.8, 0.33, 0.0, 0.0)], sides=6, mat=GREEN)

    # The cone pointing down the screen (rows 8-13) behind a bright collar (row 8).
    loft_y(bm, G, 6.0, [(7.5, 2.7, 0.15, 0.15), (8.6, 2.7, 0.15, 0.15), (8.9, 2.3, 0.13, 0.14)],
           sides=12, mat=COLLAR)
    loft_y(bm, G, 6.0, [(8.8, 2.3, 0.13, 0.14), (10.5, 1.9, 0.11, 0.13), (12.5, 1.1, 0.07, 0.11),
                        (13.6, 0.0, 0.0, 0.1)], sides=12, mat=CONE)
    return to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
