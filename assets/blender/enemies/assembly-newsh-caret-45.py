"""Red and grey crab in the wall (newsh^.shp frames 157, 159, 161, an assembly of three pieces):
a 3D version of its sprites.

Seen in episode 4 (level 4.14). Three 2x2 enemies side by side make one 72x28 px crab set into a
dark brick wall (sprite.json `assemblyLayout`, which also lists the separate gun emplacements of
newsh-caret-45.py; this script builds the crab, newsh-caret-157, -159 and -161). A grey domed head
with a red trident emblem and a darker thorax below it, red shoulder balls either side with a
ribbed grey joint under each, grey ball joints further out and big red hooked claws curling down
at the ends, and two small red mandibles curling in under the head. Every piece has one frame and
fills its tile, so the wall's floor and bricks are part of the model.

The whole crab is built once in assembly coordinates (left half, mirrored about the centre of
pixel column 36, the sprite's axis), then cut into the three pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh-caret-45.py [-- --preview out.png]
(the preview is the whole crab; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from lib_b072 import (Grid, sweep, loft_y, plate, ellipsoid, dome, floor_bricks, mirror_all,  # noqa: E402
                      to_object, merged_sprite, composite_png)

NAME = "assembly-newsh-caret-45"
ROOT = common.repo_root(__file__)
PIECES = ["newsh-caret-157", "newsh-caret-159", "newsh-caret-161"]
# One crab of the layout (screen cy 10, cx 32 / 56 / 80); its centre (screen 56, 10) is the
# Blender origin and assembly pixel (0, 0) is the top-left corner of newsh-caret-157.
LAYOUT = [("newsh-caret-157", -24, 0), ("newsh-caret-159", 0, 0), ("newsh-caret-161", 24, 0)]
G = Grid(72, 28)
AXIS_COL = 36

# Head dome: centre (column, row), radii in px, base z and height.
HEAD = (36.0, 7.6, 8.4, 6.0, 0.03, 0.4)


def head_z(c, r, lift=0.0):
    """Height of the head dome's surface over pixel (c, r), plus `lift`."""
    hc, hr, rx, ry, z0, rz = HEAD
    d = 1 - ((c - hc) / rx) ** 2 - ((r - hr) / ry) ** 2
    return z0 + rz * math.sqrt(max(d, 0.0)) + lift


def composite_pixels():
    """The three pieces' pixels side by side (72 x 28)."""
    rows = [[] for _ in range(28)]
    for name in PIECES:
        pixels = common.load_sprite(ROOT, name)["frames"][0]["pixels"]
        for r in range(28):
            rows[r] += pixels[r]
    return rows


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshc45"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(2, metallic=0.1, roughness=0.9),  # 0 floor
        pal(3, metallic=0.2, roughness=0.8),  # 1 dark bricks
        pal(5, metallic=0.4, roughness=0.6),  # 2 light bricks
        pal(6, metallic=0.6, roughness=0.4),  # 3 ribbed joints, thorax
        pal(7, metallic=0.35, roughness=0.4),  # 4 head
        pal(9, metallic=0.75, roughness=0.25),  # 5 grey ball joints
        pal(11, metallic=0.8, roughness=0.2),  # 6 bright ribs
        pal(70, metallic=0.3, roughness=0.5),  # 7 dark red
        pal(72, metallic=0.35, roughness=0.4),  # 8 red shell
        pal(74, metallic=0.35, roughness=0.35),  # 9 light red emblem
        pal(76, metallic=0.3, roughness=0.3),  # 10 red highlight
        pal(4, metallic=0.4, roughness=0.6),  # 11 mouth plate
        pal(162, metallic=0.2, roughness=0.7),  # 12 dark brown claw underside
    ]
    FLOOR, DARK, LIGHT, JOINT, HEADM, BALL, RIB, DRED, RED, EMBLEM, SHINE, MOUTH, BROWN = range(13)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----

    # The claw (157, columns 5-14, rows 7-22): a round red shell at the top that curls down
    # into a hook, its tip at row 22 pointing in. The brown inner side is its shaded underside.
    ellipsoid(bm, G, 10.4, 9.6, 0.2, 4.3, 3.0, 0.17, mat=RED, segments=16, rings=8)
    ellipsoid(bm, G, 9.9, 9.0, 0.335, 1.5, 1.0, 0.035, mat=SHINE, segments=8, rings=4)
    sweep(bm, G, [(10.6, 9.6, 0.19, 0.0, 0.0), (10.2, 10.6, 0.19, 4.0, 0.14), (9.2, 12.6, 0.17, 4.0, 0.14),
                  (8.2, 14.6, 0.15, 3.3, 0.12), (7.4, 16.5, 0.13, 2.2, 0.1), (7.1, 18.4, 0.11, 1.7, 0.085),
                  (7.5, 20.2, 0.095, 1.4, 0.07), (8.5, 21.4, 0.08, 1.0, 0.055), (9.8, 22.3, 0.07, 0.0, 0.0)],
          sides=12, mat=RED)
    sweep(bm, G, [(12.0, 12.2, 0.12, 0.0, 0.0), (11.6, 13.0, 0.12, 1.4, 0.08), (10.8, 15.0, 0.11, 1.2, 0.07),
                  (9.8, 16.6, 0.1, 0.0, 0.0)], sides=8, mat=BROWN)

    # Grey ball joint between the claw and the shoulder (157, columns 14-22, rows 8-15).
    ellipsoid(bm, G, 18.5, 11.6, 0.16, 4.4, 3.9, 0.15, mat=BALL, segments=16, rings=8)
    sweep(bm, G, [(16.4, 8.4, 0.2, 0.0, 0.0), (16.4, 9.4, 0.25, 0.8, 0.04), (16.4, 12.6, 0.25, 0.8, 0.04),
                  (16.4, 13.8, 0.2, 0.0, 0.0)], sides=6, mat=RIB)

    # Ribbed grey joint under the shoulder (columns 22-30, rows 12-18).
    ellipsoid(bm, G, 26.2, 15.0, 0.1, 4.4, 2.8, 0.12, mat=JOINT, segments=12, rings=6)
    for c in (23.6, 25.6, 27.6):
        sweep(bm, G, [(c, 12.8, 0.14, 0.0, 0.0), (c, 13.6, 0.18, 0.6, 0.03), (c + 0.4, 16.4, 0.18, 0.6, 0.03),
                      (c + 0.4, 17.2, 0.14, 0.0, 0.0)], sides=4, mat=RIB)

    # Red shoulder ball beside the head (columns 23-31, rows 6-12).
    ellipsoid(bm, G, 27.2, 9.2, 0.2, 4.7, 3.6, 0.18, mat=RED, segments=12, rings=6)
    ellipsoid(bm, G, 26.2, 8.4, 0.33, 1.8, 1.3, 0.05, mat=SHINE, segments=8, rings=4)
    ellipsoid(bm, G, 27.2, 11.6, 0.1, 4.0, 1.4, 0.08, mat=DRED, segments=10, rings=4)

    # Mandible curling in under the head (columns 27-34, rows 18-22).
    sweep(bm, G, [(28.6, 17.4, 0.08, 0.0, 0.0), (28.6, 18.2, 0.09, 1.0, 0.06), (28.8, 19.6, 0.1, 1.3, 0.07),
                  (29.6, 21.0, 0.1, 1.4, 0.07), (31.4, 21.9, 0.09, 1.3, 0.065), (33.6, 22.1, 0.08, 1.0, 0.05),
                  (34.8, 22.1, 0.07, 0.0, 0.0)], sides=8, mat=RED)

    # Arm of the trident emblem on the head (columns 32-35, rows 4-7).
    path = [(32.4, 3.8), (33.6, 5.0), (34.8, 6.4), (35.6, 7.2)]
    sweep(bm, G, [(c, r, head_z(c, r, 0.005), 0.75, 0.025) for c, r in path], sides=6, mat=EMBLEM)

    mirror_all(bm, G.X(AXIS_COL))

    # ---- centre parts ----

    # The head dome (columns 28-44, rows 2-13) and the darker thorax below it (rows 12-18) with a
    # groove down its middle.
    hc, hr, rx, ry, z0, rz = HEAD
    dome(bm, G, hc, hr, z0, rx, ry, rz, mat=HEADM, segments=16, rings=8)
    dome(bm, G, 36.0, 14.4, 0.03, 5.6, 3.8, 0.24, mat=JOINT, segments=12, rings=6)
    loft_y(bm, G, AXIS_COL, [(12.5, 0.0, 0.0, 0.2), (13.0, 0.6, 0.03, 0.24), (16.5, 0.6, 0.03, 0.2),
                             (17.4, 0.0, 0.0, 0.12)], sides=6, mat=DARK)
    # Trident emblem: the centre line (rows 3-6) and the stem (rows 7-12) with a dark core.
    sweep(bm, G, [(AXIS_COL, r, head_z(AXIS_COL, r, 0.005), 0.75 if r < 7 else 1.6, 0.03)
                  for r in (2.8, 4.0, 5.5, 7.0, 8.5, 10.0, 11.4)], sides=8, mat=EMBLEM)
    sweep(bm, G, [(AXIS_COL, r, head_z(AXIS_COL, r, 0.03), 0.0 if r in (6.8, 11.0) else 0.5, 0.015 if r not in (6.8, 11.0) else 0.0)
                  for r in (6.8, 7.6, 10.2, 11.0)], sides=6, mat=DRED)

    # Dark plate between the mandibles (columns 30-42, rows 19-21).
    plate(bm, G, [(30, 19), (43, 19), (43, 21), (30, 21)], 0.03, 0.06, mat=MOUTH)

    floor_bricks(bm, G, composite_pixels(), FLOOR, DARK, LIGHT)
    return to_object(NAME, bm, mats, coll)


def main():
    sprite = merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    pieces = common.split_assembly(obj, LAYOUT)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(ROOT, LAYOUT, Path(tempfile.mkdtemp()) / "assembly.png", 72, 84)
        common.render_preview([obj], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
