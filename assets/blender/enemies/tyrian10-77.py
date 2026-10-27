"""Green crystal (tyrian.shp #10 frames 77-87): a 3D version of its sprite.

Seen in episode 3 (level 25) and episode 4. A long cut emerald pointing up and down the screen:
pointed ends, straight sides, a bright ridge down its middle that opens into a small diamond-shaped
table facet below the centre, a broad facet each side of the ridge and a narrow facet along each
edge. The six frames only sweep a white glint across it, so one model covers them all: frame 77
is the plain crystal, and on frames 79-87 a glint runs diagonally from the upper left to the lower
right. Each of those frames gets its own glint (common.frame_part): a pale green sheen where the
sprite's pixels light up to 43 or more, with a white core where they reach 46, laid over the
facets.

Run: blender --background --python assets/blender/enemies/tyrian10-77.py [-- --preview out.png]
     [--frames frames.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b039 as lib  # noqa: E402

NAME = "tyrian10-77"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = 1 / 12

# Centre of the crystal: column 11, row 13.
CX, CY = lib.px(11), lib.row(13)
H = 3.4 * U  # height of the ridge above the girdle
RIDGE = 0.6 * U  # half width of the ridge bevels

# Down the crystal, (px above the centre, half width in px, half width of the table facet in px).
SECTIONS = [(11.0, 0.0, 0.0), (5.5, 5.5, 0.0), (2.5, 5.5, 0.0), (1.0, 5.5, 1.1), (-1.0, 5.5, 2.1),
            (-3.0, 5.5, 1.3), (-4.5, 5.5, 0.0), (-5.5, 5.5, 0.0), (-11.0, 0.0, 0.0)]


def ring(dy, w, tw):
    """12 points round the crystal at dy px above the centre (see the segment list in build)."""
    if w == 0:
        return [(CX, CY + dy * U, 0.25 * H)]
    W, T = w * U, max(tw, 0.05) * U
    r = RIDGE * min(1.0, w / 5.5)
    xz = [(T, H), (T + r, H - 0.18 * U), (0.62 * W, 0.6 * H), (W, 0.0), (0.62 * W, -0.6 * H),
          (0.3 * W, -0.8 * H), (-0.3 * W, -0.8 * H), (-0.62 * W, -0.6 * H), (-W, 0.0),
          (-0.62 * W, 0.6 * H), (-T - r, H - 0.18 * U), (-T, H)]
    return [(CX + x, CY + dy * U, z) for x, z in xz]


# The glint: (lowest lit pixel value, palette index, lift above the facets) for each layer.
GLINT = [(43, 44, 0.006), (46, 47, 0.011)]
GLINT_FRAMES = [79, 81, 83, 85, 87]
STEP = 0.5  # px, the grid the glint is cut from
SIGMA = 0.7  # px, how much the dithered pixel mask is smoothed into a glint


def lit(frame, base, lo):
    """1 where this frame's pixel is at least `lo` and brighter than on the plain frame."""
    return [[1.0 if v >= lo and v > b else 0.0 for v, b in zip(fr, br)] for fr, br in zip(frame, base)]


def coverage(mask, c, r):
    """The mask, softened a little, at continuous sprite (column, row)."""
    total = weight = 0.0
    for rr in range(max(0, int(r) - 2), min(len(mask), int(r) + 3)):
        for cc in range(max(0, int(c) - 2), min(len(mask[0]), int(c) + 3)):
            w = math.exp(-((rr - r) ** 2 + (cc - c) ** 2) / (2 * SIGMA * SIGMA))
            total += mask[rr][cc] * w
            weight += w
    return total / weight


def glint(bm, bvh, mask, lift, mat_index):
    """A thin skin lying on the crystal over the lit pixels of `mask`."""
    cols = [5 + i * STEP for i in range(int(13 / STEP) + 1)]  # pixel edges, columns 5-17
    rows = [2 + j * STEP for j in range(int(23 / STEP) + 1)]  # rows 2-24
    verts = {}

    def vert(i, j):
        if (i, j) not in verts:
            x, y = (cols[i] - 12) / 12, (14 - rows[j]) / 12
            hit, normal, _, _ = bvh.ray_cast(Vector((x, y, 1.0)), Vector((0.0, 0.0, -1.0)))
            if hit is not None and normal.z < 0:  # the crystal's faces may not be oriented yet
                normal = -normal
            verts[i, j] = bm.verts.new(hit + normal * lift) if hit is not None and normal.z > 0.05 else None
        return verts[i, j]

    for j in range(len(rows) - 1):
        for i in range(len(cols) - 1):
            if coverage(mask, cols[i] + STEP / 2 - 0.5, rows[j] + STEP / 2 - 0.5) < 0.42:
                continue
            quad = [vert(i, j + 1), vert(i + 1, j + 1), vert(i + 1, j), vert(i, j)]  # anticlockwise from above
            if None not in quad:
                bm.faces.new(quad).material_index = mat_index
    # Merge the grid's cells on each facet into a few larger faces.
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=bm.verts[:], edges=bm.edges[:])


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(40, metallic=0.1, roughness=0.2),  # 0 left broad facet
        pal(37, metallic=0.1, roughness=0.2),  # 1 right broad facet
        pal(43, metallic=0.1, roughness=0.15),  # 2 bright ridge
        pal(41, metallic=0.1, roughness=0.15),  # 3 table facet
        pal(42, metallic=0.1, roughness=0.2),  # 4 right narrow facet
        pal(39, metallic=0.1, roughness=0.2),  # 5 left narrow facet
        pal(35, metallic=0.1, roughness=0.3),  # 6 underside
    ]
    LEFT, RIGHT, RIDGE_M, TABLE, RNARROW, LNARROW, UNDER = range(7)
    # Segments of a ring: right ridge bevel, right broad facet, right narrow facet, five underside,
    # left narrow facet, left broad facet, left ridge bevel, table.
    seg = [RIDGE_M, RIGHT, RNARROW, UNDER, UNDER, UNDER, UNDER, UNDER, LNARROW, LEFT, RIDGE_M, TABLE]
    bm = bmesh.new()
    lib.ring_loft(bm, [ring(*s) for s in SECTIONS], [seg] * (len(SECTIONS) - 1))
    bm.normal_update()
    bvh = BVHTree.FromBMesh(bm)
    parts = [common.mesh_object(NAME, bm, mats, coll, smooth=False)]

    # The glint of each frame: a pale sheen and a white core on top of it.
    glint_mats = [common.palette_material(sprite, i, f"{NAME}-glint", metallic=0.1, roughness=0.1,
                                          emission_strength=0.6 * k)
                  for k, (_, i, _) in enumerate(GLINT)]
    frames = {f["index"]: f["pixels"] for f in sprite["frames"]}
    for f in GLINT_FRAMES:
        gbm = bmesh.new()
        for k, (lo, _, lift) in enumerate(GLINT):
            glint(gbm, bvh, lit(frames[f], frames[77], lo), lift, k)
        obj = common.mesh_object(f"{NAME}-glint-{f}", gbm, glint_mats, coll, smooth=False)
        if sum(p.normal.z for p in obj.data.polygons) < 0:  # keep the skin facing up
            obj.data.flip_normals()
        parts.append(common.frame_part(obj, [f]))
    return parts


def main():
    sprite = common.load_sprite(ROOT, NAME)
    parts = build(sprite)
    common.export_sprite_model(ROOT, parts, MODEL, sprite["sprites"])
    lib.preview(parts, ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
