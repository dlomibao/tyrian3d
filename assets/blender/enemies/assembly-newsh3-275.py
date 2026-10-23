"""Rock spire in a lava mound (newsh3.shp frames 237 + 275, an assembly of 2 pieces): a 3D
version of its sprites.

Seen in episode 4 (level 4.6). Two 2x2 ground enemies one above the other make one 24 x 48 px
object (sprite.json `assemblyLayout`): a grey stone spire, its flat lit top at the upper end and
its face sloping down the screen, rising out of a lumpy mound of dark red rock that is lit red
on its left side, with a few glowing lava spots.

The whole object is built once in assembly coordinates (pixel edges, cols 0..24, rows 0..56 from
the top of newsh3-237) and cut into the two pieces with common.split_assembly. Each face takes
the colour class of the sprite pixel under it (dark rock, red rock, grey stone, light stone), so
the mottling follows the sprite.

Run: blender --background --python assets/blender/enemies/assembly-newsh3-275.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import math
import random
import sys
from pathlib import Path

import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b115 as lib  # noqa: E402

NAME = "assembly-newsh3-275"
ROOT = common.repo_root(__file__)
PIECES = ["newsh3-237", "newsh3-275"]  # top, bottom
CX0, CY0 = 152, -4  # screen position of the assembly centre
W, H = 24, 56


def X(c):
    return (c - W / 2) / 12


def Y(r):
    return (H / 2 - r) / 12


# Material slots.
DARK, RED_DARK, RED, HOT, STONE_DARK, STONE, STONE_LIGHT, STONE_HI = range(8)


def silhouette_rows():
    """{row: (first col edge, last col edge)} of the assembly's opaque pixels."""
    rows = {}
    for name, top in (("newsh3-237", 0), ("newsh3-275", 28)):
        frame = common.load_sprite(ROOT, name)["frames"][0]
        for r, row in enumerate(frame["pixels"]):
            cols = [c for c, v in enumerate(row) if v >= 0]
            if cols:
                rows[top + r] = (cols[0], cols[-1] + 1)
    return rows


def mound(bm, rng):
    """The dark rock mound: the silhouette of rows 18-54 as its base, rings shrinking up to a low
    rounded top, jittered a little so it reads as rock. Returns the index of its first face."""
    rows = silhouette_rows()
    left, right = [], []
    for r in range(18, 54, 2):
        lo = min(rows[r][0], rows.get(r + 1, rows[r])[0])
        hi = max(rows[r][1], rows.get(r + 1, rows[r])[1])
        left.append((lo + 0.3, r + 1))
        right.append((hi - 0.3, r + 1))
    left.append(((rows[53][0] + rows[53][1]) / 2, 54))
    outline = left + list(reversed(right))
    centre = (13.5, 40.0)
    rings = []
    for k, (s, z) in enumerate([(1.0, 0.0), (0.93, 0.1), (0.8, 0.2), (0.6, 0.27), (0.38, 0.31)]):
        ring = []
        for c, r in outline:
            cc, rr = centre[0] + (c - centre[0]) * s, centre[1] + (r - centre[1]) * s
            jz = rng.uniform(-0.015, 0.015) if 0 < k < 4 else 0.0
            ring.append(bm.verts.new((X(cc), Y(rr), max(0.0, z + jz))))
        rings.append(ring)
    first = len(bm.faces)
    n = len(outline)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(rings[-1])
    faces = list(lib.faces_since(bm, first))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.smooth = True
        f.normal_update()
        # Lit red by the lava on its left flank and along its right edge; dark on top.
        f.material_index = RED if f.normal.x < -0.22 else RED_DARK if f.normal.x > 0.3 else DARK
    return first


# Rock bumps half sunk into the mound: (col, row, half width px, half length px, height above
# the mound, turn degrees, material), on the sprite's red and grey patches (rows 28+ are
# newsh3-275).
LUMPS = [
    (8.8, 22.0, 2.6, 4.6, 0.1, 10, "RED"),  # red rock on the spire's left foot
    (8.0, 36.5, 2.6, 4.4, 0.06, -30, "RED"),  # the red ridge running in from the left
    (11.0, 51.5, 3.0, 2.2, 0.05, 0, "RED"),
    (7.6, 30.4, 2.8, 2.6, 0.1, 0, "STONE_LIGHT"),  # grey boulder beside the spire's foot
]


def spire(bm):
    """The grey spire: a flat top at the upper end of the sprite, its sides widening and leaning
    down the screen to a broad foot inside the mound."""
    top = [(12.6, 6.4), (18.4, 6.4), (19.4, 8.2), (19.6, 12.0), (19.2, 15.6), (17.4, 17.4), (12.8, 17.8),
           (9.4, 16.6), (8.4, 13.2), (10.0, 9.0)]
    upper = [(12.0, 6.0), (19.0, 6.0), (20.8, 8.4), (21.0, 12.5), (20.8, 17.0), (18.8, 20.5), (12.0, 21.5),
             (8.2, 19.8), (7.0, 14.2), (9.2, 8.6)]
    foot = [(11.0, 16.0), (20.0, 16.0), (22.2, 20.0), (22.6, 25.0), (22.0, 31.0), (18.0, 34.0), (11.0, 34.0),
            (6.8, 31.0), (6.4, 24.0), (8.0, 19.0)]
    def split(poly):  # two points per side, so the faces are small enough to take the sprite's colours
        out = []
        for i, (c, r) in enumerate(poly):
            c2, r2 = poly[(i + 1) % len(poly)]
            out += [(c, r), ((c + c2) / 2, (r + r2) / 2)]
        return out

    def lerp(a, b, t):
        return [(ca + (cb - ca) * t, ra + (rb - ra) * t) for (ca, ra), (cb, rb) in zip(a, b)]

    top, upper, foot = split(top), split(upper), split(foot)
    levels = [(foot, 0.0), (lerp(foot, upper, 0.35), 0.22), (lerp(foot, upper, 0.7), 0.43), (upper, 0.62),
              (top, 0.8)]
    rings = [[bm.verts.new((X(c), Y(r), z)) for c, r in pts] for pts, z in levels]
    first = len(bm.faces)
    n = len(top)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(rings[-1])
    bm.faces.new(list(reversed(rings[0])))
    return first


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh3_275"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(112, metallic=0.1, roughness=0.85),  # 0 dark rock
        pal(115, metallic=0.1, roughness=0.8),  # 1 dark red rock
        pal(117, metallic=0.1, roughness=0.7, emission_strength=1.0),  # 2 red-lit rock
        pal(119, emission_strength=4.0),  # 3 glowing lava
        pal(4, metallic=0.2, roughness=0.8),  # 4 shaded stone
        pal(6, metallic=0.2, roughness=0.75),  # 5 stone
        pal(8, metallic=0.25, roughness=0.65),  # 6 lit stone
        pal(10, metallic=0.25, roughness=0.55),  # 7 stone highlight
    ]
    bm = bmesh.new()

    rng = random.Random(275)
    mound(bm, rng)
    first = spire(bm)
    faces = list(lib.faces_since(bm, first))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.smooth = False
        f.normal_update()
        n = f.normal
        if n.z > 0.95:
            f.material_index = STONE_LIGHT  # flat lit top
        elif n.x < -0.45:
            f.material_index = RED  # left side, lit red by the lava
        elif n.x > 0.45:
            f.material_index = DARK  # right side in shadow
        elif n.y < 0:
            f.material_index = STONE_LIGHT if n.x < 0.15 else STONE  # face sloping down the screen
        else:
            f.material_index = STONE_DARK
    # A lit crest on the spire's top (the brightest pixels, rows 13-17 cols 10-14).
    lib.ellipsoid(bm, X(13.0), Y(15.0), 0.8, 2.0 / 12, 2.2 / 12, 0.035, mat=STONE_HI, segments=10, rings=4, half=True)

    # Red bumps sunk into the mound, and glowing lava spots on top of whatever is under them.
    bvh = BVHTree.FromBMesh(bm)

    def ground(c, r):
        hit = bvh.ray_cast(Vector((X(c), Y(r), 2.0)), Vector((0, 0, -1)))
        return hit[0].z if hit[0] else 0.0

    for c, r, rx, ry, rz, turn, cls in LUMPS:
        g = ground(c, r)
        base = max(0.0, g - rz * 1.2)
        lib.ellipsoid(bm, X(c), Y(r), base, rx / 12, ry / 12, g + rz - base, mat=globals()[cls],
                      segments=10, rings=4, half=True, rot=math.radians(turn))
    for c, r, rad in [(7.5, 40.6, 1.1), (6.4, 41.6, 0.9), (5.6, 46.6, 0.9), (23.0, 38.6, 0.8), (6.5, 30.5, 0.8)]:
        lib.ellipsoid(bm, X(c), Y(r), ground(c, r) - 0.02, rad / 12, rad / 12, 0.05, mat=HOT, segments=8, rings=4,
                      half=True)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    lib.export_assembly(ROOT, obj, layout, argv, W, H)


if __name__ == "__main__":
    main()
