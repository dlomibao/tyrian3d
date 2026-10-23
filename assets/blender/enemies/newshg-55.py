"""Purple dome bunker (newshg.shp frame 55): a 3D version of its sprite.

Seen in episode 2 (levels 2.4 and 2.19). A ground emplacement in the top 20 rows of its block: a
ribbed carapace dome in the middle with three small red lights on its brow, a curved shoulder
plate on each side, and two heavy feet at the front with a glowing blue mouth between them. One
frame, one model; it sits on the ground (base at z = 0).

Run: blender --background --python assets/blender/enemies/newshg-55.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b124 as lib  # noqa: E402

NAME = "newshg-55"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
FR = lib.Frame(24, 28)
PX = lib.PX
AXIS = 11.5  # pixel column 11's centre, the sprite's mirror axis (pixel edges)

# The carapace dome: centre (col, row) in pixel edges, radii in px, base height and height.
DOME_C, DOME_R, DOME_RX, DOME_RY, DOME_Z0, DOME_H = AXIS, 7.2, 5.9, 7.0, 0.04, 0.42


def dome_z(c, r, lift=0.0):
    """Height of the dome's surface above sprite point (c, r) (pixel edges)."""
    u = ((c - DOME_C) / DOME_RX) ** 2 + ((r - DOME_R) / DOME_RY) ** 2
    return DOME_Z0 + DOME_H * math.sqrt(max(0.0, 1 - u)) + lift


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(89, metallic=0.2, roughness=0.4),  # 0 carapace
        pal(92, metallic=0.25, roughness=0.35),  # 1 light ribs
        pal(82, metallic=0.3, roughness=0.55),  # 2 dark lower body
        pal(81, metallic=0.2, roughness=0.7),  # 3 deep shadow, the mouth's recess
        pal(148, emission_strength=4.0),  # 4 blue mouth glow
        pal(67, emission_strength=3.0),  # 5 red brow lights
        pal(88, metallic=0.2, roughness=0.4),  # 6 shoulder plates
        pal(84, metallic=0.3, roughness=0.5),  # 7 feet
    ]
    SHELL, RIB, DARK, DEEP, GLOW, RED, SHOULDER, FOOT = range(8)
    bm = bmesh.new()

    # Lower body under everything (rows 7-17): a low dark mound joining the parts.
    lib.ellipsoid(bm, (*FR.xy(AXIS, 11.5), 0.0), (10.6 * PX, 6.5 * PX, 0.2), mat=DARK, segments=20, rings=8,
                  half=True)

    # Feet at the front (rows 11-19), one each side of the mouth, slightly turned out.
    for side in (-1, 1):
        c = AXIS + side * 6.3
        lib.ellipsoid(bm, (*FR.xy(c, 15.2), 0.0), (4.3 * PX, 4.6 * PX, 0.2), mat=FOOT, segments=16, rings=8,
                      half=True, rot_z=side * 0.25)
        # A ridge down the outer edge of each foot (the lighter column at 2-3).
        lib.tube(bm, [(*FR.xy(AXIS + side * 8.6, 11.0), 0.13), (*FR.xy(AXIS + side * 8.4, 14.0), 0.16),
                      (*FR.xy(AXIS + side * 7.6, 17.5), 0.08)], [0.02, 0.025, 0.015], sides=6, mat=SHOULDER)

    # Shoulder plates (columns 1-5, rows 3-13): long curved shells either side of the dome.
    for side in (-1, 1):
        c = AXIS + side * 8.0
        lib.ellipsoid(bm, (*FR.xy(c, 8.5), 0.02), (3.0 * PX, 5.6 * PX, 0.3), mat=SHOULDER, segments=14, rings=8,
                      half=True, rot_z=-side * 0.12)
        # Its bright crest (column 3 / 19, rows 4-11).
        crest = [(AXIS + side * 8.1, r) for r in (3.6, 5.5, 8.0, 10.5, 12.2)]
        zs = []
        for cc, r in crest:
            u = ((r - 8.5) / 5.6) ** 2
            zs.append(0.02 + 0.3 * math.sqrt(max(0.0, 1 - u)) + 0.004)
        lib.tube(bm, [(*FR.xy(cc, r), z) for (cc, r), z in zip(crest, zs)], [0.0, 0.035, 0.04, 0.035, 0.0],
                 sides=6, mat=RIB, flat=0.6)

    # The carapace dome (columns 6-16, rows 0-12).
    lib.ellipsoid(bm, (*FR.xy(DOME_C, DOME_R), DOME_Z0), (DOME_RX * PX, DOME_RY * PX, DOME_H), mat=SHELL,
                  segments=20, rings=10, half=True)
    # Two light ribs over it (columns 9 and 13, rows 1-8) and a darker groove between them.
    for c in (AXIS - 2.4, AXIS + 2.4):
        rows = [0.9, 2.0, 4.0, 6.0, 8.0, 9.0]
        lib.tube(bm, [(*FR.xy(c, r), dome_z(c, r, 0.0)) for r in rows],
                 [0.0, 0.07, 0.08, 0.075, 0.06, 0.0], sides=6, mat=RIB, flat=0.45)

    # Three small red lights on the brow (row 9-10, columns 10-12).
    for c, r in ((AXIS, 9.5), (AXIS - 1.0, 10.5), (AXIS + 1.0, 10.5)):
        lib.ellipsoid(bm, (*FR.xy(c, r), dome_z(c, r, -0.01)), (0.6 * PX, 0.6 * PX, 0.04), mat=RED,
                      segments=8, rings=4)

    # The blue mouth between the feet (columns 9-13, rows 13-15) in a dark recess.
    lib.ellipsoid(bm, (*FR.xy(AXIS, 14.6), 0.0), (3.4 * PX, 2.8 * PX, 0.16), mat=DEEP, segments=14, rings=6,
                  half=True)
    lib.ellipsoid(bm, (*FR.xy(AXIS, 14.3), 0.1), (2.6 * PX, 1.7 * PX, 0.1), mat=GLOW, segments=14, rings=6)

    return lib.to_object(NAME, bm, mats, coll)


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
