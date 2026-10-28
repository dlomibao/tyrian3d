"""Small grey-blue asteroid (newshd.shp frame 152): a 3D version of its sprite.

Seen in episodes 1-3. A rounded, lumpy boulder traced to the sprite's whole silhouette (its dark
rim included), about 9 px tall for its 12 x 14 px body as the sprite's lit facets and dark rim
say: an ellipsoid resting on z = 0, widest about 2.5 px up, its sides curving on round from the
ground to the crown. The sprite's three bright facet patches (upper left, upper right, lower left)
are flat planes of the rock itself: the crown's vertices over those pixels are set on one plane,
tilted a little toward the upper-left light, flush with the rock on its lit side and a little
above it on its shadowed lower right (no separate plates). The darker middle column sinks a little
as a crease, and the two dark pits (between the upper facets, and lower right) are cut in.
Each face takes the sprite's own palette index under it, so the facets' near-white cores and grey
surrounds come through; under the girth, and on the low steep side, the rock is the sprite's dark
slate rather than the outline's black. Flat shaded and matte all over.
One frame, one model.

Built here rather than by lib_b014.rock (which makes a thin lens of this size) from its helpers.

Run: blender --background --python assets/blender/enemies/newshd-152.py [-- --preview out.png]
"""

import math
import random
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshd-152"
TOP = 0.54        # height of the top above the girth at the widest (units; 6.5 px)
BOTTOM = 0.2      # depth of the underside (2.4 px); the whole rock is then lifted to rest on z = 0
# The sprite's dark pits: (x, y) in sprite px from the centre, radius (px), depth (units).
PITS = ((0.5, 1.0, 1.1, 0.12), (1.5, -2.0, 1.5, 0.22))
FACETS = (  # the sprite's lit facets, as (column, row) pixels
    {(5, 2), (4, 3), (5, 3), (4, 4)},                                  # upper left
    {(7, 3), (7, 4), (8, 4), (7, 5), (8, 5), (7, 6), (8, 6)},          # upper right
    {(5, 7), (3, 8), (4, 8), (5, 8), (3, 9), (4, 9), (5, 9)},          # lower left
)
PROUD = 0.03      # how far a facet's plane stands above the rock at its centre (units; 0.6 px)
FLUSH = 0.03      # how far below a facet's plane the rock round its lit side comes up to (units)
STEP = 0.05       # the least drop off a facet's shadowed side (units; 0.6 px)
FLATTEN = 0.6     # how much of the rock's own slope under a facet its plane keeps
TILT = 0.1        # extra tilt of each facet toward the upper-left light (units per unit)
RELIEF = 0.22     # how far the dark crease sinks, per 100 luminance below LEVEL
LUMPS = 0.05      # random lumpiness
SEED = 152
CUTS, TOP_FROM = 3, 0.1  # the crown is cut finer (under 1 px between vertices) for the facets
LEVEL = 100.0     # luminance that doesn't sink (about palette 106, mid ramp)
DIP = 0.06        # most the darker ramp sinks on the crown (units; 0.7 px)
SOFT = 1.3        # crease smoothing radius (sprite px)
FULL = 0.8        # < 1 fills out the ellipsoid's shoulders
NEUTRAL = (3, 4, 5, 6)  # the sprite's neutral greys (its rim and a few dark specks)
RIM, EDGE, SLATE = 3, 1, 102  # rim grey, near-black outline, the dark slate of the lower rows
MERGE = {32: 1, 4: 3, 6: 5, 108: 107}  # near-identical indices share a material
UNDER = -0.05     # faces facing further down than this are under the girth (painted slate)
GIRTH = 0.24      # faces below this height (units; 3 px) are under the girth, unseen from above
LOW_SIDE = 0.36  # steep outline faces below this height (units; 4.3 px) are painted slate
DARK_SLATE = 101  # the darkest slate, about the rim grey's brightness
UNDER_SLATE = 103  # under the girth, facing away from the light, a shade up reads as the slate


def convex_hull(points):
    """The convex hull of 2D points (sorted), counter-clockwise."""
    def half(pts):
        out = []
        for p in pts:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])
                                     - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out
    lower, upper = half(points), half(list(reversed(points)))
    return lower[:-1] + upper[:-1]


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    pixels, size = frame["pixels"], frame["size"]

    shade = lib.Shade(sprite, pixels, size)
    slot, mats = {}, []

    def mat(index):
        if index not in slot:
            slot[index] = len(mats)
            mats.append(common.palette_material(sprite, index, NAME, metallic=0.0, roughness=0.9))
        return slot[index]


    # The outline: every non-transparent pixel, the dark rim included, smoothed into an oval.
    whole = [[3 if v != -1 else -1 for v in r] for r in pixels]
    cx, cy, radii = lib.silhouette(whole, size, grow=0.15, smooth=4)
    rmax = max(radii)

    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    bm.normal_update()
    top = {e for f in bm.faces if f.normal.z > TOP_FROM for e in f.edges}
    bmesh.ops.subdivide_edges(bm, edges=list(top), cuts=CUTS, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])

    rng = random.Random(SEED)
    blobs = [(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized(),
              rng.uniform(0.4, 1.0)) for _ in range(10)]

    def lump(n):
        return sum(a * max(0.0, n.dot(d) - 0.55) for d, a in blobs)

    # An ellipsoid on the sprite's outline: round in section, widest at the midplane.
    lat = {}  # each vertex's latitude on the sphere (1 = top), before shaping
    for v in bm.verts:
        n = v.co.normalized()
        lat[v] = n.z
        r = lib.radius_at(radii, math.atan2(n.y, n.x))
        b = lump(n)
        h = (TOP if n.z > 0 else BOTTOM) * (0.8 + 0.2 * r / rmax)
        v.co = Vector((cx + n.x * r * (1 + LUMPS * 0.2 * b),
                       cy + n.y * r * (1 + LUMPS * 0.2 * b),
                       math.copysign(abs(n.z) ** FULL, n.z) * h * (1 + LUMPS * b * 1.5)))

    # The darker middle column sinks a little on the crown, as the crease between the facets (only
    # well inside the outline, so the shoulders stay round). Only the blue-grey ramp counts (the
    # grey rim would sink the shoulders), smoothed over about a pixel.
    ramp = lib.Shade(sprite, pixels, size, skip=NEUTRAL)
    ring = [(0.0, 0.0, 2.0)] + [(math.cos(a) * SOFT / 12, math.sin(a) * SOFT / 12, 1.0)
                                for a in (2 * math.pi * k / 8 for k in range(8))]
    for v in bm.verts:
        if v.co.z <= 0:
            continue
        acc = wsum = 0.0
        for dx, dy, w in ring:
            lum = ramp.at(v.co.x + dx, v.co.y + dy, blur=0.4)
            if lum is not None:
                acc += w * lum
                wsum += w
        if wsum < 3.0:
            continue
        d = (acc / wsum - LEVEL) / 100.0 * RELIEF
        if d < 0:
            v.co.z += max(d, -DIP) * min(1.0, max(0.0, (lat[v] - 0.55) / 0.3))

    # Rest the rock on the ground plane: its underside at z = 0, its widest girth about 4 px up.
    low = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= low

    # The lit facets are flat planes of the crown: the rock's vertices over each facet's pixels are
    # set on one plane fitted to the rock there (keeping FLATTEN of its slope), PROUD above it and
    # tilted further toward the upper-left light; round it the rock is about flush on the lit
    # upper-left side and steps down STEP on the shadowed lower right.
    def pixel_of(co):
        u, w = lib.to_edge(co.x, co.y, size)
        return int(math.floor(u)), int(math.floor(w))

    for cells in FACETS:
        near = {(c + dc, r + dr) for c, r in cells for dc in (-1, 0, 1) for dr in (-1, 0, 1)}
        vs = [v for v in bm.verts if lat.get(v, 0) > 0.2 and pixel_of(v.co) in near]
        mx = sum(v.co.x for v in vs) / len(vs)
        my = sum(v.co.y for v in vs) / len(vs)
        mz = sum(v.co.z for v in vs) / len(vs)
        sxx = sum((v.co.x - mx) ** 2 for v in vs)
        syy = sum((v.co.y - my) ** 2 for v in vs)
        sxy = sum((v.co.x - mx) * (v.co.y - my) for v in vs)
        sxz = sum((v.co.x - mx) * (v.co.z - mz) for v in vs)
        syz = sum((v.co.y - my) * (v.co.z - mz) for v in vs)
        det = sxx * syy - sxy * sxy
        gx, gy = (sxz * syy - syz * sxy) / det, (syz * sxx - sxz * sxy) / det
        gx, gy = gx * FLATTEN + TILT, gy * FLATTEN - TILT  # rises toward the lower right

        # The facet's centre: that of the convex hull of its pixels' corners.
        corners = {(lib.ex(c + i, size), lib.ey(r + j, size)) for c, r in cells for i in (0, 1) for j in (0, 1)}
        hull = convex_hull(sorted(corners))
        fx = sum(x for x, _ in hull) / len(hull)
        fy = sum(y for _, y in hull) / len(hull)
        z_at = lambda x, y: mz + PROUD + gx * (x - mx) + gy * (y - my)  # noqa: E731
        for v in vs:
            z = z_at(v.co.x, v.co.y)
            if pixel_of(v.co) in cells:
                v.co.z = z
            elif (v.co.y - fy) - (v.co.x - fx) > 0:
                v.co.z = z - FLUSH
            else:
                v.co.z = min(v.co.z, z - STEP)

    # The two dark pits (between the upper facets, and lower right) are cut into the crown,
    # after the facets so the rock pulled up round them doesn't fill the pits in.
    lit = set().union(*FACETS)
    for v in bm.verts:
        if lat.get(v, 0) < 0.4 or pixel_of(v.co) in lit:
            continue
        for px, py, pr, depth in PITS:
            d2 = ((v.co.x - px / 12) ** 2 + (v.co.y - py / 12) ** 2) * 144 / (pr * pr)
            v.co.z -= depth * math.exp(-d2 * d2) * min(1.0, (lat[v] - 0.4) / 0.3)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    # Paint: the sprite's own palette index under each face seen from above (the most common one
    # among a few samples), so the facets' near-white cores and grey surrounds both come through.
    # Faces under the girth can't be seen from above; the game camera sees them on the near side,
    # so they take the sprite's dark slate (its rows 10-12) rather than the outline's black, which
    # stays on the outermost ring only.
    bm.normal_update()
    for f in bm.faces:
        cen = f.calc_center_median()
        if f.normal.z < UNDER or cen.z < GIRTH:
            f.material_index = mat(UNDER_SLATE)
            continue
        pts = [cen] + [cen.lerp(v.co, 0.6) for v in f.verts]
        idx = [MERGE.get(i, i) for i in (shade.index(p.x, p.y) for p in pts)]
        idx = [i for i in idx if i != -1] or [EDGE]
        best = max(sorted(set(idx)), key=idx.count)
        if best == RIM and f.normal.z < 0.35:
            best = DARK_SLATE  # the rim's steep sides: as dark, but the rock's slate rather than grey
        elif best == EDGE and f.normal.z < 0.35 and cen.z < LOW_SIDE:
            best = SLATE  # the low side reads dark slate, not black
        f.material_index = mat(best)

    # Flat shaded all over, matte, so the whole rock reads as one faceted stone.
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
