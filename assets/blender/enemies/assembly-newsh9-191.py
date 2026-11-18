"""Armoured eye sphere, top 72x56 px (newsh9 153/155/157 over 191/193/195).

The model is built by the shared builder lib_eyesphere.py (see its docstring); this script exports
only the six top pieces. The swirl (the yin-yang armour boss, only in these top pieces: it spans
sphere rows 9-37, the lower assembly-newsh9-210 starts at row 56) is built here, by a local copy of
the builder's build_sphere with a local swirl; the shared lib stays untouched, and the ball, bar,
rods, lens and every other part are the lib's, unchanged.

The swirl (round-3 QA, e4a L2): the sprite draws it grey on grey, lobe A (the head, west) at
pal 10 (median of its pixels), lobe B (east) at pal 9, over the pal 7-8 ball, parted by a soft
shaded S valley (its pixels are 5-9, no black ink) and with sheen spots (13-15: lighting, art
rule 2). So: both lobes at the sprite's own indices with the ball's low-gloss metal (not the
near-white pal 11 dielectric that read flat white in game), the S parting line a smooth modelled
valley that the light shades (no exact-boolean pal-2 groove that drew as a heavy black line), a
shallow pal 6 strip only at its very bottom, the plate's rim rolled into the ball with no step,
and the tail rib a low rounded rib at pal 11 (the sprite's arc runs 10-14).
Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh9-191.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_eyesphere as lib  # noqa: E402
from lib_eyesphere import *  # noqa: E402,F401,F403  (the builder's helpers, for the local build_sphere)
from lib_eyesphere import (bmesh, bpy, common, math, Vector, X, Y, PX, SW, SH, NAME, zb, sw_uv, sw_pq,  # noqa: E402
                           lobe_of, seam_dist, catmull, smoothstep, sweep, bridge, cut_grooves,
                           to_object, _bm_to_mesh, fit_lens_plane, zl, e_of, lens_uv, crescent_in, plane,
                           E_LIMB, LCU, LCV, LA, LB, HT, HB, OU, OV, rim, normal_of, H_A, H_B)

# round-3 re-review: the sprite's ball is dark grey (7-8 lit, 3-5 at the east and rim); the swirl
# grey on grey (9-10, its bright S edge and pellet are sheen)
BALL_PAL, NE_PAL, EAST_PAL = 6, 4, 4
BALL_MET, BALL_ROUGH = 0.22, 0.5
LOBEA_PAL, LOBEB_PAL = 8, 8
SEAM_W, SEAM_H = 0.4, 0.035
# the rim: the lib fits it to the inner mask (+0.12 px); north of the ball's centre row (pieces
# 153/155/157) it is widened onto the sprite's outer edge, so each top piece covers its own
# outline ring (per-piece IoU >= 0.95); the rows the lower assembly-newsh9-210 shares stay as fitted
RIM_OUT = 0.35      # px inside the outer mask's edge

ONLY = ["newsh9-153", "newsh9-155", "newsh9-157", "newsh9-191", "newsh9-193", "newsh9-195"]

# the S valley: half width (unit disc of the swirl plan) and depth under the lobes' crown
VALLEY_W = 0.1
VALLEY_D = 0.85     # share of the local lobe height (the valley floor stays proud of the ball)
STRIP_W = 0.025     # the pal 6 strip at the valley's bottom
FILLET = 0.3        # the plate's edge roll, as a share of the plan radius


def pad_profile(r):
    """Crown, then a roll that meets the ball tangentially (zero slope at the rim): no concave
    crease where the plate meets the ball, so the outline pass draws no ink ring round it."""
    if r <= 1 - FILLET:
        return 1.0 - 0.05 * (r / (1 - FILLET)) ** 2
    t = min(1.0, (r - (1 - FILLET)) / FILLET)
    return 0.95 * (0.5 + 0.5 * math.cos(math.pi * t))


def zpad(u, v):
    """The swirl plate's surface: two crowned lobes on the ball, a smooth rounded S valley between
    them (the parting line is shaded by the light, not painted)."""
    p, q = sw_pq(u, v)
    r = math.hypot(p, q)
    if r >= 1.0:
        return zb(u, v)
    s = seam_dist(p, q)
    a = lobe_of(p, q)
    h_here, h_other = (H_A, H_B) if a else (H_B, H_A)
    # heights blend across the valley, so neither lobe stands as a cliff over the other
    k = smoothstep(0.5 + 0.5 * s / VALLEY_W) if s < VALLEY_W else 1.0
    h = h_other + (h_here - h_other) * k
    dip = 1.0 - VALLEY_D * (1.0 - smoothstep(s / VALLEY_W)) if s < VALLEY_W else 1.0
    return zb(u, v) + h * dip * pad_profile(r)


def build_sphere(sprite, coll):
    tag = "nsh9a"
    mats, slots = [], {}

    def M(key, i, **kw):
        if key not in slots:
            slots[key] = len(mats)
            mats.append(common.palette_material(sprite, i, f"{tag}{key}", **kw))
        return slots[key]

    BALL = M("ball", BALL_PAL, metallic=BALL_MET, roughness=BALL_ROUGH)
    # the armour panels at the sprite's own darker indices (art rule 1: palette index per region),
    # each bounded by a modelled seam: the NE cap (north of the east seam, east of the diagonal one)
    # and the east flank (east of the vertical seam, down to the lens)
    NECAP = M("necap", NE_PAL, metallic=BALL_MET, roughness=BALL_ROUGH)
    EAST = M("east", EAST_PAL, metallic=BALL_MET, roughness=BALL_ROUGH)
    # seams: thin shallow V grooves one shading step darker (pal 4), not black ink
    SEAM = M("seam", 4, metallic=0.3, roughness=0.65)
    # the swirl, grey on grey as the sprite draws it: lobe A (the head) at pal 10, lobe B at pal 9,
    # both the ball's low-gloss metal one step lighter than it; the S valley's bottom strip pal 6
    LOBEA = M("lobea", LOBEA_PAL, metallic=BALL_MET, roughness=BALL_ROUGH)
    LOBEB = M("lobeb", LOBEB_PAL, metallic=BALL_MET, roughness=BALL_ROUGH)
    SGROOVE = M("sgroove", 6, metallic=0.25, roughness=0.6)
    TAIL = M("tail", 10, metallic=0.28, roughness=0.44)   # the sprite's light arc runs 10-14
    BEZEL = M("bezel", 5, metallic=0.45, roughness=0.55)
    STRIP = M("strip", 132, metallic=1.0, roughness=0.55, emission_strength=0.8)
    ROD = M("rod", 12, metallic=0.85, roughness=0.28)
    SLOT = M("slot", 2, metallic=0.3, roughness=0.7)
    RING = M("ring", 6, metallic=0.6, roughness=0.36)
    LID = M("lid", 5, metallic=0.55, roughness=0.4)
    # glow surfaces: metallic 1 / rough (D126/D173), so they read as their colour, not a reflection
    IRIS = M("iris", 157, metallic=1.0, roughness=0.5, emission_strength=0.22)
    TEAL = M("teal", 130, metallic=1.0, roughness=0.5, emission_strength=0.35)
    LIMB = M("limb", 54, metallic=1.0, roughness=0.55, emission_strength=0.2)
    CYAN = M("cyan", 139, metallic=1.0, roughness=0.5, emission_strength=0.3)
    BRIGHT = M("bright", 159, metallic=1.0, roughness=0.5, emission_strength=0.25)
    # the cross: near-black (pal 97), a dielectric with a low F0 so it stays dark, not a grey rail
    CROSS = M("cross", 97, metallic=0.0, roughness=0.55)
    MID = M("mid", 158, metallic=1.0, roughness=0.5, emission_strength=0.25)
    DEEP = M("deep", 53, metallic=1.0, roughness=0.55, emission_strength=0.15)
    # black glass: a dielectric with a low F0 (Specular IOR Level, D176), so the domed cap catches
    # the game light as a soft sheen and stays black (glossier read grey or as a cartoon glint)
    PUPIL = M("pupil", 1, metallic=0.0, roughness=0.45)
    pb = next(n for n in mats[PUPIL].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in pb.inputs:
        pb.inputs["Specular IOR Level"].default_value = 0.2
    cb = next(n for n in mats[CROSS].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in cb.inputs:
        cb.inputs["Specular IOR Level"].default_value = 0.15
    FILL = M("fill", 2, metallic=0.3, roughness=0.7)

    # ---- the ball (unchanged armour) ----
    segs, nr = 96, 18
    bb = bmesh.new()

    def ring(p, zf):
        if p == 0:
            return [bb.verts.new((X(OU), Y(OV), zf(0.0)))]
        out = []
        for k in range(segs):
            a = 2 * math.pi * k / segs
            r = rim(a) * p
            out.append(bb.verts.new((X(OU + r * math.cos(a)), Y(OV + r * math.sin(a)), zf(p))))
        return out

    ps = [math.sin(0.5 * math.pi * i / nr) ** 0.9 for i in range(nr + 1)]
    top = [ring(p, lambda p: HT * math.sqrt(max(0.0, 1 - p * p))) for p in ps]
    under = [top[-1]] + [ring(p, lambda p: -HB * math.sqrt(max(0.0, 1 - p * p)))
                         for p in (0.97, 0.88, 0.72, 0.5, 0.0)]
    for r0, r1 in zip(top, top[1:]):
        for f in bridge(bb, r0, r1):
            f.material_index, f.smooth = BALL, True
    for r0, r1 in zip(under, under[1:]):
        for f in bridge(bb, r0, r1):
            f.material_index, f.smooth = BALL, True

    def groove(points, surface=zb, w=SEAM_W, h=SEAM_H, mat=SEAM, step=0.8):
        # a closed cutter (pointed ends): an open tube is not a solid and the exact boolean then
        # left the groove walls inverted / invisible (lib_b019's seams only showed as ink)
        t = bmesh.new()
        (ua, va), (ub, vb) = points[0], points[1]
        (uy, vy), (uz, vz) = points[-2], points[-1]
        la = math.hypot(ub - ua, vb - va) or 1.0
        lz = math.hypot(uz - uy, vz - vy) or 1.0
        start = (ua - (ub - ua) / la * 1.2, va - (vb - va) / la * 1.2, 0.0, 0.0, 0.0)
        end = (uz + (uz - uy) / lz * 1.2, vz + (vz - vy) / lz * 1.2, 0.0, 0.0, 0.0)
        sweep(t, [start] + [(u, v, 0.0, w, h) for u, v in points] + [end], sides=6, mat=mat, surface=surface,
              step=step, smooth=False)
        return t

    seams = [
        [(23.6, 2.6), (25.4, 6.0), (27.0, 8.6)],
        [(37.2, 1.4), (35.8, 5.0), (34.6, 8.8)],
        [(39.8, 1.4), (41.0, 2.8), (44.0, 6.4), (48.0, 9.6), (50.0, 13.0)],
        [(49.6, 13.4), (54.0, 13.6), (59.0, 13.4), (65.5, 13.6)],
        [(49.6, 13.4), (49.4, 20.0), (49.4, 27.0), (49.8, 35.0), (50.0, 39.6)],
        [(50.4, 26.0), (54.0, 25.8), (58.0, 26.4), (63.6, 27.4)],
        [(50.0, 35.2), (54.0, 35.6), (57.4, 36.6)],
        [(1.6, 20.6), (5.0, 22.2), (9.0, 23.6), (15.6, 24.6)],
        [(1.2, 36.0), (4.0, 37.0)],
        [(15.0, 30.2), (20.0, 31.2), (24.0, 31.6)],
        [(12.0, 43.6), (14.0, 40.0), (16.2, 36.8), (21.0, 35.4)],
        [(51.0, 37.4), (54.4, 40.0), (56.2, 43.0)],
    ]
    def seam_u(pts, v):
        # the seam's u at row v (a polyline running down the rows)
        for (ua, va), (ub, vb) in zip(pts, pts[1:]):
            if va <= v <= vb:
                return ua + (ub - ua) * (v - va) / max(1e-6, vb - va)
        return pts[0][0] if v < pts[0][1] else pts[-1][0]

    bm = bmesh.new()
    bm.from_mesh(cut_grooves(NAME + "_ball", bb, [groove(p) for p in seams], mats, coll))
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        if f.material_index != BALL:
            continue
        c = f.calc_center_median()
        u, v = c.x / PX + SW / 2, SH / 2 - c.y / PX
        if u > 49.6 and v > 13.5:
            f.material_index = EAST
        elif v < 13.5 and u > seam_u(seams[2], v):
            f.material_index = NECAP

    # ---- the swirl boss: one crowned elliptical plate, its two lobes parted by a shaded S valley ----
    bp = bmesh.new()
    # dense enough (about 0.3 px) for the S valley to be modelled, not a polar staircase
    NA = 240
    rr = [0.0] + [0.02 * i for i in range(1, 46)] + [0.92, 0.94, 0.96, 0.975, 0.987, 0.995, 1.0]
    prings = []
    for r in rr:
        if r == 0:
            u, v = sw_uv(0, 0)
            prings.append([bp.verts.new((X(u), Y(v), zpad(u, v)))])
            continue
        ring_ = []
        for k in range(NA):
            g = 2 * math.pi * k / NA
            u, v = sw_uv(r * math.cos(g), r * math.sin(g))
            z = zpad(u, v) if r < 1 else zb(u, v) - 0.004
            ring_.append(bp.verts.new((X(u), Y(v), z)))
        prings.append(ring_)
    u0, v0 = sw_uv(0, 0)
    pfloor = [bp.verts.new((X(u0), Y(v0), zb(u0, v0) - 0.1))]
    for r0, r1 in zip(prings, prings[1:]):
        for f in bridge(bp, r0, r1):
            f.smooth = True
    for f in bridge(bp, prings[-1], pfloor):
        f.smooth = False
        f.material_index = FILL
    bp.faces.ensure_lookup_table()
    for f in bp.faces:
        if f.material_index == FILL:
            continue
        c = f.calc_center_median()
        u = c.x / PX + SW / 2
        v = SH / 2 - c.y / PX
        p, q = sw_pq(u, v)
        if seam_dist(p, q) < STRIP_W and math.hypot(p, q) < 0.97:
            f.material_index = SGROOVE
        else:
            f.material_index = LOBEA if lobe_of(p, q) else LOBEB
    bm.from_mesh(_bm_to_mesh(bp))

    # the tail rib: the sprite's light arc, from the lens rim (upper left) under the boss and up
    # into the light bar's foot; thin at the rim, full under the boss
    tail_c = [(22.6, 36.2), (24.4, 35.3), (26.8, 34.3), (29.8, 33.2), (33.2, 32.1), (36.8, 30.8),
              (40.0, 29.0), (42.4, 26.8), (43.8, 25.0)]
    tl = catmull(tail_c, 4)
    n = len(tl)
    tail = [(tl[0][0] - 0.75, tl[0][1] + 0.38, 0.0, 0.0, 0.0)]
    for i, (u, v) in enumerate(tl):
        t = i / (n - 1)
        full = smoothstep(t / 0.4) - 0.3 * smoothstep((t - 0.65) / 0.35)
        tail.append((u, v, 0.0, 0.85 + 0.7 * full, 0.04 + 0.03 * full))
    tail.append((tl[-1][0] + 0.3, tl[-1][1] - 0.9, 0.0, 0.0, 0.0))
    # a low rounded rib (not a boxy tube standing on the ball: its foot crease drew as ink)
    sweep(bm, tail, sides=12, mat=TAIL, power=1.0, step=1.0)

    # ---- the light bar, in a dark recessed bezel ----
    bar = [(38.2, 10.8), (41.0, 12.2), (43.6, 14.6), (45.4, 17.6), (46.2, 21.0), (46.2, 24.0), (46.0, 25.6)]
    widths = [2.4, 3.0, 3.0, 2.9, 2.7, 2.6, 2.2]
    sweep(bm, [(bar[0][0] - 0.8, bar[0][1] - 0.4, 0.0, 0.0, 0.0)]
          + [(u, v, 0.0, w + 0.9, 0.05) for (u, v), w in zip(bar, widths)]
          + [(bar[-1][0], bar[-1][1] + 1.2, 0.0, 0.0, 0.0)], sides=10, mat=BEZEL, power=0.6, step=1.0)
    sweep(bm, [(bar[0][0] - 0.4, bar[0][1] - 0.2, 0.04, 0.0, 0.0)]
          + [(u, v, 0.06, w, 0.16) for (u, v), w in zip(bar, widths)]
          + [(bar[-1][0], bar[-1][1] + 0.9, 0.05, 0.0, 0.0)], sides=12, mat=STRIP, power=0.7, step=1.0)

    # ---- latch rods in slots on each flank ----
    for path in ([(9.4, 30.6), (11.2, 34.4), (13.4, 39.2)], [(61.6, 31.2), (59.8, 34.6), (57.8, 38.4)]):
        (u0, v0), _, (u1, v1) = path
        dx = 1.2 if u0 < 36 else -1.2
        sweep(bm, [(u0 - dx, v0 + 0.2, -0.03, 0.0, 0.0)] + [(u - dx * 0.7, v + 0.3, -0.03, 1.7, 0.05) for u, v in path]
              + [(u1 - dx * 0.4, v1 + 1.0, -0.03, 0.0, 0.0)], sides=8, mat=SLOT, power=0.6)
        sweep(bm, [(u0, v0, 0.05, 0.0, 0.0)] + [(u, v, 0.07, 1.0, 0.075) for u, v in path]
              + [(u1 + (u1 - u0) * 0.08, v1 + 0.6, 0.05, 0.0, 0.0)], sides=8, mat=ROD)
        for u, v in (path[0], path[2]):
            sweep(bm, [(u - 0.9, v, 0.02, 1.3, 0.11), (u + 0.9, v, 0.02, 1.3, 0.11)], sides=8, mat=RING,
                  power=0.5, step=2.0)

    # ---- the eye: a convex lens in a socket ----
    fit_lens_plane()
    be = bmesh.new()
    NE = 72

    def vert(u, v, z):
        return be.verts.new((X(u), Y(v), z))

    # ring parameters t -> e(t, g): iris rings up to the crescent's inner edge, crescent rings up to
    # the limbus, limbal rings up to the rim (so every colour change runs along a ring)
    iris_t = [0.1, 0.2, 0.32, 0.45, 0.58, 0.7, 0.8, 0.9, 1.0]
    cres_t = [0.5, 1.0]
    limb_e = [0.95, 0.985, 1.0]
    centre = [vert(LCU, LCV, zl(LCU, LCV))]
    rings_e = [centre]
    kinds = []
    for t in iris_t:
        rg = []
        for k in range(NE):
            g = 2 * math.pi * k / NE
            e = crescent_in(g) * t
            u, v = lens_uv(e, g)
            rg.append(vert(u, v, zl(u, v)))
        rings_e.append(rg)
        kinds.append(IRIS)
    for t in cres_t:
        rg = []
        for k in range(NE):
            g = 2 * math.pi * k / NE
            ci = crescent_in(g)
            e = ci + (E_LIMB - ci) * t
            u, v = lens_uv(e, g)
            rg.append(vert(u, v, zl(u, v)))
        rings_e.append(rg)
        kinds.append("cres")
    for e in limb_e:
        rg = []
        for k in range(NE):
            g = 2 * math.pi * k / NE
            u, v = lens_uv(e, g)
            rg.append(vert(u, v, zl(u, v)))
        rings_e.append(rg)
        kinds.append(LIMB)
    for (r0, r1), kind in zip(zip(rings_e, rings_e[1:]), kinds):
        for k, f in enumerate(bridge(be, r0, r1)):
            f.smooth = True
            if kind == "cres":
                g = 2 * math.pi * (k + 0.5) / NE
                f.material_index = TEAL if crescent_in(g) < E_LIMB - 0.02 else IRIS
            else:
                f.material_index = kind
    # the rim wall down into the socket, and a floor (closed solid)
    wall = [vert(*lens_uv(1.0, 2 * math.pi * k / NE), 0) for k in range(NE)]
    for k, w in enumerate(wall):
        u, v = lens_uv(1.0, 2 * math.pi * k / NE)
        w.co.z = min(zb(u, v), plane(u, v)) - 0.1
    for f in bridge(be, rings_e[-1], wall):
        f.material_index, f.smooth = BEZEL, False
    flo = [vert(LCU, LCV, plane(LCU, LCV) - 0.12)]
    for f in bridge(be, wall, flo):
        f.material_index, f.smooth = FILL, False
    bm.from_mesh(_bm_to_mesh(be))

    # the iris fibres: short radial streaks laid flush on the lens (colour, not geometry, art rule
    # 2), each a spindle with pointed ends along the lens's own spokes, so the iris reads fibrous as
    # the sprite's broken 137-143 / 158-159 streaks do, not as cartoon spots. Grouped in the sectors
    # where the sprite has its tones, with seeded jitter (the same every build). They lie
    # PATCH_LIFT on the lens, a skin under the cross (which stands 0.16 px proud).
    PATCH_LIFT = 0.09 * PX
    # (sector centre deg: 0 east, 90 south; half span deg; e from, e to; count; colours)
    sectors = [
        (232, 34, 0.4, 0.88, 17, (CYAN, MID, BRIGHT, MID)),      # upper left: light cyan / azure
        (182, 16, 0.4, 0.82, 7, (BRIGHT, MID, CYAN)),            # west, by the 62 glint
        (300, 26, 0.36, 0.8, 10, (DEEP, LIMB, TEAL)),            # upper right panes: dark blue
        (40, 26, 0.36, 0.74, 10, (LIMB, DEEP, TEAL)),            # lower right panes
        (95, 22, 0.42, 0.74, 6, (LIMB, DEEP)),                   # south, under the pupil
        (60, 14, 0.66, 0.95, 5, (MID, IRIS)),                    # lighter azure on the crescent
        (180, 180, 0.3, 0.66, 22, (MID, TEAL, MID, LIMB)),       # fine fibres all round the pupil
    ]
    import random
    rnd = random.Random(191)
    bpt = bmesh.new()
    NS, NT = 9, 3
    for gc, span, e0, e1, count, cols in sectors:
        for i in range(count):
            g0 = gc - span + 2 * span * (i + 0.5 + 0.6 * (rnd.random() - 0.5)) / count
            hl = (e1 - e0) * (0.22 + 0.16 * rnd.random())       # radial half length (e)
            ec = e0 + hl + (e1 - e0 - 2 * hl) * rnd.random()
            hw = (0.9 + 0.9 * rnd.random()) / max(0.4, ec)     # angular half width (deg)
            curl = (rnd.random() - 0.5) * 6.0                   # a slight bend (deg at the ends)
            mat = cols[i % len(cols)]
            grid_ = []
            for a_ in range(NS + 1):
                sv = -1 + 2 * a_ / NS
                w = hw * (1 - sv * sv) ** 0.7
                row_ = []
                for b_ in range(NT + 1):
                    tv = -1 + 2 * b_ / NT
                    g = math.radians(g0 + curl * sv * sv + w * tv)
                    u, v = lens_uv(ec + hl * sv, g)
                    row_.append(bpt.verts.new(Vector((X(u), Y(v), zl(u, v))) + normal_of(zl, u, v) * PATCH_LIFT))
                grid_.append(row_)
            for a_ in range(NS):
                for b_ in range(NT):
                    f = bpt.faces.new((grid_[a_][b_], grid_[a_ + 1][b_], grid_[a_ + 1][b_ + 1], grid_[a_][b_ + 1]))
                    f.material_index, f.smooth = mat, True
    # face them all up (outward); they join the whole after its normals are recalculated (an open
    # skin has no inside for the recalc to find)
    bpt.normal_update()
    for f in bpt.faces:
        if f.normal.z < 0:
            f.normal_flip()
    patch_mesh = _bm_to_mesh(bpt)

    # the pupil: a solid black cap, lens-shaped, its edge tucked into the lens
    # off centre as the sprite's pal-1 pupil sits (cols 29-35, rows 48-57: west of the vertical bar and
    # south of the horizontal one, so upper left on EYESPY's flipped screen), tapering a little
    # out along the four cross arms as the sprite's black runs into them
    PU, PV, PRU, PRV = 32.7, 52.9, 4.6, 5.4
    arms = [math.atan2(v - PV, u - PU) for u, v in ((36.5, 43.5), (36.5, 60.5), (43.5, 50.6), (26.5, 51.5))]

    def prad(g):
        k = 0.0
        for a in arms:
            d = math.atan2(math.sin(g - a), math.cos(g - a))
            k = max(k, math.exp(-(d / 0.3) ** 2))
        return 1 + 0.17 * k
    bpup = bmesh.new()
    prs = []
    for s, lift in ((0.0, 0.42 * PX), (0.35, 0.38 * PX), (0.65, 0.29 * PX), (0.85, 0.18 * PX),
                    (0.96, 0.07 * PX), (1.0, -0.15 * PX)):
        if s == 0:
            prs.append([bpup.verts.new((X(PU), Y(PV), zl(PU, PV) + lift))])
            continue
        rg = []
        for k in range(72):
            g = 2 * math.pi * k / 72
            rk = prad(g)
            u, v = PU + PRU * rk * s * math.cos(g), PV + PRV * rk * s * math.sin(g)
            rg.append(bpup.verts.new((X(u), Y(v), zl(u, v) + lift)))
        prs.append(rg)
    pbot = [bpup.verts.new((X(PU), Y(PV), zl(PU, PV) - 0.3 * PX))]
    for r0, r1 in zip(prs, prs[1:]):
        for f in bridge(bpup, r0, r1):
            f.material_index, f.smooth = PUPIL, True
    for f in bridge(bpup, prs[-1], pbot):
        f.material_index, f.smooth = PUPIL, False
    bm.from_mesh(_bm_to_mesh(bpup))

    # the cross: two full-length raised mullions following the dome (vertical col 36; horizontal
    # row 51 west of the pupil, row 50 east of it)
    def mullion(ctrl):
        line = catmull(ctrl, 6)
        line = [p for p in line if e_of(*p) <= 0.975]
        pts = [(line[0][0], line[0][1], 0.0, 0.0, 0.0)]
        for i, (u, v) in enumerate(line):
            pts.append((u, v, 0.0, 0.58, 0.16 * PX))
        pts.append((line[-1][0], line[-1][1], 0.0, 0.0, 0.0))
        # the ends: shorten the taper so the bar meets the limbus square
        pts[0] = (line[0][0], line[0][1], 0.0, 0.45, 0.1 * PX)
        pts[-1] = (line[-1][0], line[-1][1], 0.0, 0.45, 0.1 * PX)
        # flush inlaid strips, flat-topped (power < 1), not a wire cage over the lens
        sweep(bm, pts, sides=8, mat=CROSS, surface=zl, step=1.0, power=0.3)

    mullion([(36.5, LCV - LB), (36.5, 43.0), (36.5, 50.5), (36.5, 58.0), (36.5, LCV + LB)])
    mullion([(LCU - LA, 51.6), (22.0, 51.5), (30.0, 51.3), (36.5, 50.9), (44.0, 50.5), (LCU + LA, 50.4)])

    # the bezel: a machined ring round the lens
    NB = 120
    ring_pts = []
    for k in range(NB + 1):
        g = 2 * math.pi * k / NB
        u, v = LCU + (LA + 1.0) * math.cos(g), LCV + (LB + 1.0) * math.sin(g)
        ring_pts.append((u, v, 0.02, 1.15, 0.07))
    sweep(bm, ring_pts[:NB // 2 + 1], sides=8, mat=BEZEL, step=1.8, power=0.7)
    sweep(bm, ring_pts[NB // 2:], sides=8, mat=BEZEL, step=1.8, power=0.7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.from_mesh(patch_mesh)
    bpy.data.meshes.remove(patch_mesh)
    obj = to_object(NAME, bm, mats, coll, recalc=False)
    return obj, slots



def fit_rim(grid):
    m = _fit_rim(grid)
    outer = m["outer"]
    raw = []
    for k in range(lib.RIM_N):
        a = 2 * math.pi * k / lib.RIM_N
        ca, sa = math.cos(a), math.sin(a)
        r = 10.0
        while r < 60:
            uu, vv = OU + r * ca, OV + r * sa
            iu, iv = int(math.floor(uu)), int(math.floor(vv))
            if not (0 <= iv < SH and 0 <= iu < SW and outer[iv][iu]):
                break
            r += 0.05
        raw.append(r - RIM_OUT)
    # smooth the outer radius a little (a 7-sample window) so the pixel stairs do not ripple the rim
    n = lib.RIM_N
    sm = [sum(raw[(k + j) % n] for j in range(-3, 4)) / 7 for k in range(n)]
    for k in range(n):
        a = 2 * math.pi * k / n
        w = smoothstep((-math.sin(a) - 0.05) / 0.2)      # 1 north of row ~26, 0 south of row ~33
        lib.RIM[k] = max(lib.RIM[k], lib.RIM[k] + w * (sm[k] - lib.RIM[k]))
    return m


_fit_rim = lib.fit_rim
lib.fit_rim = fit_rim
lib.build_sphere = build_sphere

if __name__ == "__main__":
    lib.main(only=ONLY)
