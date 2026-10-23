"""Nort ship (player ship, tyrian.shp#8 frames 220 and 222 drawn side by side as one 48x28
object): a 3D version of its sprite.

A wide grey delta. A pointed nose fuselage with a dark canopy runs down the middle into a pale
raised spine; broad swept wings with a blue leading-edge band and two chevron ridges each end in
a short prong at the tip; under each wing root an engine pod pokes out behind the trailing edge
(dark vents on top) and tapers to a nozzle. Two short red-tipped guns sit on the shoulders
beside the nose. Symmetric about the edge between sprite columns 23 and 24 minus half a pixel
(the middle of column 23); the origin is the middle of the 48x28 block.

Run: blender --background --python assets/blender/ships/ship-nort-ship.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b141 import dome, loft, span_wing, tube  # noqa: E402

NAME = "ship-nort-ship"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 23.5  # the middle of sprite column 23 (pixel edges)


def mir(c):
    return 2 * AXIS - c


# Left wing planform, tip to centre: (col, front row, back row, thickness, z mid), pixel edges.
WING = [
    (5.6, 17.4, 21.6, 1.0, 0.0),
    (6.5, 16.5, 22.4, 1.2, 0.0),
    (7.5, 15.5, 23.4, 1.4, 0.0),
    (8.5, 14.5, 24.6, 1.6, 0.0),
    (9.5, 13.5, 25.0, 1.8, 0.0),
    (10.8, 12.3, 25.0, 2.0, 0.0),
    (11.0, 12.1, 22.0, 2.0, 0.0),
    (12.0, 11.2, 21.4, 2.2, 0.0),
    (13.5, 10.0, 21.2, 2.5, 0.0),
    (15.0, 9.3, 21.2, 2.8, 0.0),
    (16.5, 8.0, 21.2, 3.0, 0.0),
    (18.5, 6.8, 21.2, 3.2, 0.0),
    (AXIS, 6.5, 21.0, 3.4, 0.0),
]


def wing_section(c):
    """The wing's planform values interpolated at column c (left half; mirrored for the right)."""
    if c > AXIS:
        c = mir(c)
    for a, b in zip(WING, WING[1:]):
        if a[0] <= c <= b[0]:
            k = (c - a[0]) / (b[0] - a[0])
            return [x + (y - x) * k for x, y in zip(a, b)]
    return list(WING[0] if c < WING[0][0] else WING[-1])


def wing_top(c, r):
    """Height (px) of the wing's upper surface at column c, row r (the span_wing profile)."""
    _, f, b, t, zm = wing_section(c)
    chord = b - f
    le = min(2.0, 0.22 * chord)
    prof = [(f, 0.0), (f + le, 0.42 * t), (f + 0.38 * chord, 0.5 * t), (f + 0.78 * chord, 0.4 * t), (b, 0.1 * t)]
    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        if r0 <= r <= r1:
            return zm + z0 + (z1 - z0) * (r - r0) / (r1 - r0)
    return zm


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.55, roughness=0.4),  # 0 wing grey
        pal(10, metallic=0.55, roughness=0.35),  # 1 nose fuselage
        pal(12, metallic=0.55, roughness=0.3),  # 2 pale spine
        pal(13, metallic=0.5, roughness=0.3),  # 3 bright ridges
        pal(5, metallic=0.4, roughness=0.55),  # 4 dark grooves and nozzles
        pal(57, metallic=0.5, roughness=0.3),  # 5 blue leading edge
        pal(8, metallic=0.55, roughness=0.4),  # 6 engine pods
        pal(2, metallic=0.2, roughness=0.6),  # 7 vents and seams
        pal(52, metallic=0.3, roughness=0.1),  # 8 canopy glass
        pal(70, metallic=0.2, roughness=0.4, emission_strength=2.5),  # 9 red gun lights
        pal(7, metallic=0.55, roughness=0.45),  # 10 gun barrels and wing edges
        pal(54, metallic=0.4, roughness=0.3),  # 11 blue canards
        pal(6, metallic=0.5, roughness=0.45),  # 12 nozzles
    ]
    WINGM, NOSE, SPINE, RIDGE, GROOVE, BLUE, POD, VENT, GLASS, RED, BARREL, CANARD, NOZZLE = range(13)
    bm = bmesh.new()

    # Wings, one loft from the left tip through the middle to the right tip.
    left = WING
    right = [(mir(c), f, b, t, z) for c, f, b, t, z in reversed(WING[:-1])]
    blue_le = lambda c: BLUE if (c if c < AXIS else mir(c)) < 11.6 else WINGM  # noqa: E731
    span_wing(bm, left + right, le_mat=blue_le, mat=WINGM)

    # Nose fuselage, tip (row 0.6) to the seam behind the shoulders (row 13).
    nose = [(0.6, 0, 0, 0.6), (1.2, 1.2, 0.8, 0.6), (2.0, 2.2, 1.3, 0.7), (3.0, 3.2, 1.8, 0.8),
            (4.0, 4.0, 2.2, 0.9), (5.5, 4.6, 2.5, 0.9), (7.0, 4.6, 2.7, 0.8), (9.0, 4.2, 2.8, 0.7),
            (11.0, 3.6, 2.8, 0.6), (13.0, 3.0, 2.6, 0.5)]
    loft(bm, [(r, AXIS, w, h, z) for r, w, h, z in nose], sides=16, mat=NOSE, power=0.8)
    # Dark seam (row 13) and the pale spine behind it, down to the notch at row 21.
    loft(bm, [(12.8, AXIS, 2.6, 2.3, 0.5), (13.9, AXIS, 2.6, 2.3, 0.5)], sides=12, mat=VENT, power=0.8)
    spine = [(13.8, 2.2, 2.4, 0.4), (16.0, 2.2, 2.5, 0.4), (19.0, 2.1, 2.3, 0.3), (20.6, 1.9, 1.9, 0.2),
             (21.0, 1.4, 1.3, 0.2)]
    loft(bm, [(r, AXIS, w, h, z) for r, w, h, z in spine], sides=12, mat=SPINE, power=0.7)
    # Bright ridge along the top of the nose (column 23, rows 7-10).
    loft(bm, [(6.8, AXIS, 0, 0, 3.4), (7.6, AXIS, 0.5, 0.3, 3.55), (11.0, AXIS, 0.5, 0.3, 3.3),
              (12.2, AXIS, 0, 0, 3.0)], sides=6, mat=RIDGE)
    # Canopy: a dark glass dome over columns 22-24, rows 4-6.
    dome(bm, AXIS, 5.4, 2.2, 2.6, 1.2, z=2.4, rings=4, sides=14, mat=GLASS)

    for side in (1, -1):
        cc = (lambda c: c) if side == 1 else mir  # column on this side

        # Blue canards beside the nose tip (column 19, rows 2-3).
        tube(bm, [(cc(20.6), 4.4, 0.6, 0.45, 0.9), (cc(19.6), 2.6, 0.55, 0.35, 0.8),
                  (cc(19.4), 1.9, 0, 0, 0.8)], sides=6, mat=CANARD)
        # Shoulder ridge: the bright diagonal from column 19 row 7 out to column 16 row 10.
        tube(bm, [(cc(20.0), 6.6, 0.55, 0.4, 2.4), (cc(18.0), 8.6, 0.6, 0.45, 2.1),
                  (cc(16.2), 10.6, 0.55, 0.4, 1.6)], sides=6, mat=RIDGE, power=0.7)
        # Shoulder gun: red-lit barrel at column 15, rows 6-9, on a grey base.
        tube(bm, [(cc(15.5), 5.6, 0, 0, 0.9), (cc(15.5), 5.9, 0.6, 0.6, 0.9), (cc(15.5), 8.9, 0.7, 0.7, 0.9)],
             sides=8, mat=RED, cap_end=False)
        tube(bm, [(cc(15.5), 8.9, 0.75, 0.75, 0.9), (cc(15.5), 10.8, 0.9, 0.9, 0.7)], sides=8, mat=BARREL)

        # Wing ridges: the inner chevron from row 12 down to the trailing edge, and the outer one
        # behind the blue band bending down into the tip prong; a dark groove between them.
        def on_wing(path, hw, hh, lift):
            return [(cc(c), r, hw, hh, wing_top(c, r) + lift) for c, r in path]
        tube(bm, on_wing([(18.9, 12.2), (15.5, 15.6), (12.4, 18.8), (12.1, 20.0), (12.2, 21.0)], 0.6, 0.25, 0.05),
             sides=6, mat=RIDGE, power=0.7)
        tube(bm, on_wing([(12.6, 14.0), (10.5, 16.2), (8.7, 18.1), (8.5, 21.0), (9.4, 23.2)], 0.6, 0.25, 0.05),
             sides=6, mat=RIDGE, power=0.7)
        tube(bm, on_wing([(14.4, 14.9), (10.8, 18.4), (10.6, 21.4)], 0.45, 0.15, 0.05), sides=4, mat=GROOVE)
        # Dark channel beside the spine (columns 19-20, rows 13-20).
        tube(bm, on_wing([(20.2, 12.6), (20.2, 16.5), (20.2, 20.9)], 0.9, 0.15, 0.05), sides=4, mat=GROOVE)
        # Grey wing-tip edge (column 6, rows 17-21).
        tube(bm, on_wing([(6.1, 17.2), (6.1, 21.4)], 0.5, 0.3, -0.1), sides=6, mat=BARREL)

        # Engine pod under the wing root: emerges behind the wing (rows 21-23, columns 12-20) and
        # tapers to a dark nozzle leaning in toward column 18 (row 27).
        pod = [(16.5, 14.5, 0, 0, -1.0), (16.5, 16.0, 2.8, 1.2, -1.0), (16.5, 18.5, 4.4, 1.8, -0.9),
               (16.5, 21.0, 4.9, 2.0, -0.8), (16.6, 22.8, 4.5, 1.9, -0.8), (16.9, 23.9, 3.4, 1.6, -0.8)]
        tube(bm, [(cc(c), r, w, h, z) for c, r, w, h, z in pod], sides=14, mat=POD, power=0.85, cap_end=False)
        nozzle = [(16.9, 23.9, 3.4, 1.6, -0.8), (17.3, 25.0, 2.6, 1.3, -0.8), (17.9, 26.4, 1.9, 1.0, -0.8),
                  (18.4, 27.6, 0.9, 0.6, -0.8), (18.5, 28.0, 0, 0, -0.8)]
        tube(bm, [(cc(c), r, w, h, z) for c, r, w, h, z in nozzle], sides=14, mat=NOZZLE, power=0.85, cap_start=False)
        # Dark vents on the pod's top (rows 21-22, columns 13-14 and 17-18).
        for c, w in ((14.0, 0.8), (17.9, 1.0)):
            tube(bm, [(cc(c), 21.0, w, 0.3, 1.05), (cc(c), 22.6, w, 0.3, 0.95)], sides=4, mat=VENT, power=0.5)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = ROOT / "reference" / "models" / NAME / frame["image"]
        common.render_preview([obj], out, ref, size=(frame["width"], frame["height"]))


if __name__ == "__main__":
    main()
