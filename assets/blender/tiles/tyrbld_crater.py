"""The small craters in TYRIAN's islands (map 1-9, layer 2; tile 153, one tile), after the concept
assets/blender/features/concepts/tyr-crater.jpg: three bore holes sunk into the island's grey rock,
each ringed by a brass collar clamped with pink fittings - a big one (upper right) and a smaller one
(left) glowing deep red at the bottom, a little empty socket (lower right) - and brass pipes laid
over the rock between them: an arc over the top, a bundle round the left edge, and cables from the
big ring down past the socket and out at the bottom left.

No enemies sit on it and it is drawn in the ordinary layer-2 pass (not `over`), so heights stay
modest anyway: the collars and clamps reach about 0.13, the boulders about 0.15; the holes go down
to -0.26 (above the slab's bottom, -0.30). The crater replaces its tile, so the model also carries
the tile's rock (Structure.rock, with holes cut for the bores), and its export removes the per-tile
model shapesz-t153. Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_crater.py
    python tools/concept_maps.py tile:shapesz-tyrbld-crater --concept tyr-crater --span 0,0,0,0 --px 32
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-crater
"""

import math
import sys
from pathlib import Path

import bmesh
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_tyrbld as tb  # noqa: E402

PX = 1 / 12

# The bores in the tile's pixels (1x), read off the concept (registered edge to edge on the tile)
# and checked against the art (tile 153: the big dark hole with its red core at px 11-18, rows 7-12,
# pink fittings at (12, 5), (10, 10), (21, 10), (18, 13); the small red core at (5.5, 16.5); the
# little ring's pink at (18, 21) and (22, 22)).
# name: centre (cx, cy), the collar's outer radii, its inner radii, the hole's radii, depth, glow,
# and the fittings' angles (degrees, screen: 0 = right, 90 = down).
BORES = {
    "big": dict(c=(15.4, 9.3), outer=(6.3, 4.8), inner=(5.3, 3.9), hole=(4.3, 3.2), depth=-0.26, glow=True,
                clamps=(-122, 176, 6)),
    "small": dict(c=(5.6, 16.9), outer=(3.4, 3.3), inner=(2.6, 2.5), hole=(2.0, 1.9), depth=-0.22, glow=True,
                  clamps=(-70, 165)),
    "socket": dict(c=(19.8, 22.8), outer=(2.6, 2.4), inner=(1.9, 1.75), hole=(1.6, 1.45), depth=-0.07, glow=False,
                   clamps=(-140, -5)),
}
BAND_Z = (0.0, 0.085)  # the brass collar's foot and top
CLAMP_Z = 0.105  # the pink clamp plates' top: just proud of the brass
CLAMP_LEN = 1.9  # px of the ring a clamp plate covers (its arc length)
COLLAR_Z = 0.03  # the cut-stone lip between the brass and the hole
PIPE_Z = 0.05  # the pipes' lowest axis height: lying on the slab
BOULDER_MAX = 0.2  # the boulders' top

# The pipes over the rock (pixel polylines from the concept), radius in px.
PIPES = [
    # the arc over the top, from a loop on the rock (left) to the big ring's top right
    ([(5.5, 7.4), (5.8, 5.6), (6.5, 3.5), (7.9, 1.8), (10.0, 0.75), (12.5, 0.35), (15.0, 0.45), (17.0, 1.1),
      (18.2, 2.4), (18.5, 3.8), (18.2, 4.9)], 0.42),
    # the bundle round the left edge, in from the map's side
    ([(-0.3, 6.8), (1.8, 7.2), (3.3, 8.4), (4.2, 10.3), (3.9, 12.0), (2.7, 13.1)], 0.3),
    ([(-0.3, 7.6), (1.3, 8.0), (2.6, 9.0), (3.3, 10.5), (3.0, 11.9), (2.0, 12.8)], 0.26),
    # small ring to big ring
    ([(8.4, 14.4), (9.6, 13.5), (10.6, 12.4)], 0.3),
    ([(8.9, 15.2), (10.2, 14.4), (11.6, 13.7), (12.6, 13.8)], 0.3),
    # the big ring's bottom down to the socket
    ([(17.9, 14.0), (18.6, 15.3), (18.9, 16.8), (18.6, 18.3), (18.1, 19.6), (18.1, 20.6)], 0.34),
    # the big ring's bottom, swinging left and down to the small ring
    ([(17.0, 14.1), (17.5, 15.6), (17.4, 17.0), (16.3, 17.8), (15.2, 18.5), (14.6, 20.0), (13.6, 21.6),
      (12.0, 22.4), (10.4, 22.6), (9.0, 22.0), (8.2, 20.8), (7.6, 19.9)], 0.3),
    # out of the small ring's bottom, across, and off the bottom left
    ([(6.4, 20.1), (7.4, 21.6), (9.2, 23.0), (11.0, 23.3), (12.5, 22.7), (13.8, 21.9)], 0.28),
    ([(12.3, 22.6), (11.2, 23.9), (9.5, 25.0), (7.0, 25.6), (4.6, 26.2), (2.6, 26.9), (0.8, 27.8), (0.2, 28.3)], 0.32),
    ([(13.0, 23.3), (11.9, 24.6), (10.0, 25.7), (7.3, 26.3), (5.0, 26.9), (3.0, 27.6), (1.8, 28.3)], 0.28),
]
N = 36  # vertices round a collar


def ell(c, r, t):
    return c[0] + r[0] * math.cos(t), c[1] + r[1] * math.sin(t)


def sweep(s, pts, profile, mat, closed=False, mats=None, cap=True, smooth=True):
    """A body swept along `pts` [(px, py, z)]: `profile` [(side_px, dz)] in the plane across the
    path (side: to the path's left on screen, px; dz: up, units). Frames stay level (the paths lie
    on the rock). `mats` per profile edge overrides `mat`."""
    bm = bmesh.new()
    n = len(pts)
    loops = []
    for i, (px, py, z) in enumerate(pts):
        a = pts[(i - 1) % n] if (closed or i > 0) else pts[i]
        b = pts[(i + 1) % n] if (closed or i < n - 1) else pts[i]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / ln, tx / ln  # left of the path (pixel axes)
        loops.append([bm.verts.new((s.x(px + nx * sp), s.y(py + ny * sp), z + dz)) for sp, dz in profile])
    m = len(profile)
    segs = n if closed else n - 1
    for i in range(segs):
        a_, b_ = loops[i], loops[(i + 1) % n]
        for k in range(m):
            j = (k + 1) % m
            bm.faces.new((a_[k], a_[j], b_[j], b_[k])).material_index = mats[k] if mats else mat
    if cap and not closed:
        for lp in (loops[0], loops[-1]):
            bm.faces.new(lp).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm, smooth=smooth)


def tube_profile(r_px, sides=8):
    return [(r_px * math.cos(2 * math.pi * k / sides), r_px * PX * math.sin(2 * math.pi * k / sides)) for k in range(sides)]


def resample(poly, step=0.7):
    """A polyline smoothed (Chaikin, twice) and resampled every `step` px."""
    p = [tuple(v) for v in poly]
    for _ in range(2):
        q = [p[0]]
        for a, b in zip(p, p[1:]):
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        q.append(p[-1])
        p = q
    out = [p[0]]
    acc = 0.0
    for a, b in zip(p, p[1:]):
        acc += math.hypot(b[0] - a[0], b[1] - a[1])
        if acc >= step:
            out.append(b)
            acc = 0.0
    if out[-1] != p[-1]:
        out.append(p[-1])
    return out


def snap_ends(poly):
    """Run a pipe's ends that stop near a collar on into the band (its mid ellipse), so every
    pipe plugs into a ring instead of ending in the air."""
    poly = [tuple(v) for v in poly]
    for end in (0, -1):
        px, py = poly[end]
        best = None
        for b in BORES.values():
            c, ro, ri = b["c"], b["outer"], b["inner"]
            mr = ((ro[0] + ri[0]) / 2, (ro[1] + ri[1]) / 2)
            dx, dy = (px - c[0]) / ro[0], (py - c[1]) / ro[1]
            d = math.hypot(dx, dy)
            if d < 1.7 and (best is None or d < best[0]):
                t = math.atan2(dy, dx)
                best = (d, ell(c, mr, t))
        if best:
            if end == 0:
                poly.insert(0, best[1])
            else:
                poly.append(best[1])
    return poly


def pipe_heights(s, rock_co, path, r):
    """The pipe's axis height at each point of `path`: PIPE_Z, or riding over the rock's top
    (`rock_co`, the rock's vertices) within reach, smoothed along the pipe."""
    zs = []
    reach = (r + 0.6) * PX
    for px, py in path:
        x, y = s.x(px), s.y(py)
        near = rock_co[(rock_co[:, 0] - x) ** 2 + (rock_co[:, 1] - y) ** 2 <= reach ** 2]
        top = near[:, 2].max() if len(near) else 0.0
        zs.append(max(PIPE_Z, top + r * PX * 0.4))
    for _ in range(4):  # dilate, then average: no dips between neighbouring stones
        zs = [max(zs[max(0, i - 2):i + 3]) for i in range(len(zs))]
    for _ in range(4):  # a long, gentle average: the pipe rises and falls smoothly, no lumps
        zs = [sum(zs[max(0, i - 4):i + 5]) / len(zs[max(0, i - 4):i + 5]) for i in range(len(zs))]
    return [max(PIPE_Z, z) for z in zs]


def build():
    s = tb.Structure("crater")
    brass, brass_dark, brass_light = s.m("brass"), s.m("brass_dark"), s.m("brass_light")
    pink = s.m(78, roughness=0.45)
    pink_dark = s.m(77, roughness=0.5)
    stone = s.m(7)
    rock_dark = s.m("rock_dark")
    glow = s.m("red", emission_strength=1.3)
    pit = s.m("dark")  # the bores' walls and floor: near black, as the tile paints them
    glow_wall = s.m(112, roughness=0.8)  # the floor round the glow: a deep dark red
    socket_floor = s.m(19, roughness=0.8)

    # The island's rock first: the slab with the bores cut out, boulders kept off the collars and
    # mostly off the pipes (the pipes then ride over the ones left, see pipe_heights).
    cut = np.zeros((s.H, s.W), bool)
    keep_out = np.zeros((s.H, s.W), bool)
    paths = [(resample(snap_ends(poly), 0.5), r) for poly, r in PIPES]
    for b in BORES.values():
        c, ro, ri = b["c"], b["outer"], b["inner"]
        cut |= s.ellipse_mask(c[0], c[1], ri[0] + 0.3, ri[1] + 0.3)
        keep_out |= s.ellipse_mask(c[0], c[1], ro[0] + 1.5, ro[1] + 1.5)
    for path, r in paths:
        for px, py in path:
            keep_out |= s.ellipse_mask(px, py, r + 0.7, r + 0.7)
    s.rock(exclude=keep_out, cut=cut, max_height=BOULDER_MAX)
    rock_co = np.array([v.co[:] for v in s.parts.verts])

    for name, b in BORES.items():
        c, ro, ri, rh = b["c"], b["outer"], b["inner"], b["hole"]

        # The bore: a lip of cut stone from under the brass to the hole's edge, its walls down to
        # the floor (red-lit near a glowing one), the floor; a skirt below the lip down to the slab's
        # bottom closes it from under.
        steps = [(ri[0] + 0.5, ri[1] + 0.5, COLLAR_Z, None), (rh[0], rh[1], COLLAR_Z - 0.008, stone),
                 (rh[0] * 0.94, rh[1] * 0.94, COLLAR_Z - 0.03, stone)]
        d = b["depth"]
        if b["glow"]:
            steps += [(rh[0] * 0.86, rh[1] * 0.86, d * 0.45, rock_dark), (rh[0] * 0.74, rh[1] * 0.74, d * 0.8, pit),
                      (rh[0] * 0.62, rh[1] * 0.62, d, pit)]
        else:
            steps += [(rh[0] * 0.88, rh[1] * 0.88, d, brass_dark)]
        bm = bmesh.new()
        rings = []
        for rx, ry, z, _ in steps:
            rings.append([bm.verts.new((s.x(ell(c, (rx, ry), 2 * math.pi * i / N)[0]), s.y(ell(c, (rx, ry), 2 * math.pi * i / N)[1]), z))
                          for i in range(N)])
        for k in range(1, len(rings)):
            a_, b_ = rings[k - 1], rings[k]
            for i in range(N):
                j = (i + 1) % N
                bm.faces.new((a_[i], a_[j], b_[j], b_[i])).material_index = steps[k][3]
        # A flat floor in concentric rings (no fan shading): dark rock, then a deep red, then a
        # small glowing core at the centre of a glowing bore.
        if b["glow"]:
            fl = [(0.62 * 0.7, pit), (0.62 * 0.42, glow_wall), (0.62 * 0.22, glow), (0.0, glow)]
        else:
            fl = [(0.88 * 0.6, socket_floor), (0.88 * 0.3, socket_floor), (0.0, socket_floor)]
        prev = rings[-1]
        for f, mat in fl:
            if f == 0.0:
                mid = bm.verts.new((s.x(c[0]), s.y(c[1]), d))
                for i in range(N):
                    bm.faces.new((prev[i], prev[(i + 1) % N], mid)).material_index = mat
            else:
                ring = [bm.verts.new((s.x(ell(c, (rh[0] * f, rh[1] * f), 2 * math.pi * i / N)[0]),
                                      s.y(ell(c, (rh[0] * f, rh[1] * f), 2 * math.pi * i / N)[1]), d)) for i in range(N)]
                for i in range(N):
                    j = (i + 1) % N
                    bm.faces.new((prev[i], prev[j], ring[j], ring[i])).material_index = mat
                prev = ring
        skirt = [bm.verts.new((v.co.x, v.co.y, tb.L2_SLAB_BOTTOM)) for v in rings[0]]
        for i in range(N):
            j = (i + 1) % N
            bm.faces.new((skirt[i], skirt[j], rings[0][j], rings[0][i])).material_index = rock_dark
        bm.faces.new(list(reversed(skirt))).material_index = rock_dark
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        s._merge(bm)

        # The brass collar: a band with a rounded top and a darker inner step.
        mr = ((ro[0] + ri[0]) / 2, (ro[1] + ri[1]) / 2)
        hw = (ro[0] - ri[0]) / 2
        z0, z1 = BAND_Z
        band = [(-hw, z0 - 0.01), (-hw, z1 - 0.02), (-hw * 0.55, z1), (hw * 0.45, z1), (hw, z1 - 0.025), (hw, z0 - 0.01)]
        bmats = [brass_dark, brass_light, brass_light, brass, brass_dark, brass_dark]
        pts = [ell(c, mr, 2 * math.pi * i / N) + (0.0,) for i in range(N)]
        # profile side +: (-ty, tx) in pixel axes, which for this path (angle growing downward)
        # points inward, toward the hole.
        sweep(s, pts, band, brass, closed=True, mats=bmats, smooth=False)
        # A thin groove line round the band's top: a lighter rib on the outer half.
        rib = [(hw * 0.05, z1 - 0.004), (hw * 0.05, z1 + 0.008), (hw * 0.4, z1 + 0.008), (hw * 0.4, z1 - 0.004)]
        sweep(s, pts, rib, brass_light, closed=True, smooth=False)

        # The pink fittings: small clamp plates bent over the band, following its curve, with
        # rounded shoulders (no bolts: at this size the tile shows just a pink fleck).
        mean_r = (mr[0] + mr[1]) / 2
        for ang in b["clamps"]:
            half = math.degrees(CLAMP_LEN / 2 / mean_r)
            a0, a1 = math.radians(ang - half), math.radians(ang + half)
            seg = [ell(c, mr, a0 + (a1 - a0) * u / 5) + (0.0,) for u in range(6)]
            w = hw + 0.08
            prof = [(-w, z0 - 0.005), (-w, z1 - 0.005)]
            prof += [(-w * math.cos(math.pi / 2 * k / 4), z1 - 0.005 + (CLAMP_Z - z1 + 0.005) * math.sin(math.pi / 2 * k / 4)) for k in range(1, 5)]
            prof += [(w * math.sin(math.pi / 2 * k / 4), z1 - 0.005 + (CLAMP_Z - z1 + 0.005) * math.cos(math.pi / 2 * k / 4)) for k in range(1, 4)]
            prof += [(w, z1 - 0.005), (w, z0 - 0.005)]
            mats = [pink_dark] + [pink] * (len(prof) - 3) + [pink_dark, pink_dark]
            sweep(s, seg, prof, pink, mats=mats, smooth=True)

    # The pipes lying on the rock (over the boulders left under them), with collars here and there.
    for path, r in paths:
        zs = pipe_heights(s, rock_co, path, r)
        pts = [(px, py, z) for (px, py), z in zip(path, zs)]
        sweep(s, pts, tube_profile(r, 10), brass)
        for f in (0.33, 0.7):
            i = int(len(path) * f)
            if 0 < i < len(path) - 1:
                seg = [tuple(a * 0.3 + b * 0.7 for a, b in zip(pts[i - 1], pts[i])), pts[i],
                       tuple(a * 0.3 + b * 0.7 for a, b in zip(pts[i + 1], pts[i]))]
                sweep(s, seg, tube_profile(r * 1.3, 10), brass_light)
    # The top arc's end on the rock: a little loop (the concept's ring round its foot).
    sweep(s, [ell((5.6, 7.5), (0.9, 0.7), 2 * math.pi * i / 12) + (0.03,) for i in range(12)],
          tube_profile(0.25, 6), brass_dark, closed=True)

    objects = s.objects()
    s.check(objects)
    s.export(objects)


build()
