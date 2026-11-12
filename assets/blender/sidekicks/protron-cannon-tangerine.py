"""Protron Cannon Tangerine (sidekick 25, tyrian.shp#9 2x2 frame 85): a 3D version of its sprite.

What the sprite shows (24x28 grid, 21x19 drawn, symmetric about column 12's centre, x = +0.5 here):
a front-mounted claw cannon, a weapon module (not a ship).
- Twin gun housings (columns 8-10 / 14-16, rows 4-12): round-crowned tubes; the bright column 9/15 is
  sheen on the crown, column 10/14 the dark valley against the chamber. Row 4 shows a blue-grey lens
  (106/102) on each housing's sloped front: a targeting lens on the glacis; the bore is on the front face.
- The protron chamber (columns 11-13, rows 5-13): a bronze capsule between the housings (21; the 28 at
  row 9 is sheen) with an emitter cap (row 5), two grey clamp bands (rows 6 and 8) and a domed tail.
- Armour cheeks (columns 5-7, rows 5-12): lower plates outside the housings, ribbed (dark column 6 is a
  groove, column 7 a raised rib); dark-red marker lamps on their front-outer corners (rows 6-7).
- Side lugs (columns 3-4, rows 8-10): rounded shoulder pads bolted to the cheeks.
- Two pincer prongs (rows 13-20): chamfered arms hung off the rear corners, running aft, bowing out and
  curling inward, dropping toward the tips; a red lamp band round each (row 17) and bronze claw teeth at
  the tips (rows 19-21) pointing at each other.

This leads with readability at the game's scale: clear height steps (housings 3.7 px > chamber 3.0 >
cheeks 2.3 > lugs 1.6 > prongs 2.3 falling to 1.0), one big shape per sprite region, then machined detail
(groove rings, rib, bolts, bores, lens). Undersides: a closed shape only.

Units: sprite px; x = column edge - 12, y = row edge (down the sprite = south / aft), z up; T.finish maps.

Texture: AO/roughness bake only (usp_talon.bake_maps), no concept projection; outline shell (D51).

Run: tools/build-models.sh -j 2 assets/blender/sidekicks/protron-cannon-tangerine.py
"""

import math
import sys
import tempfile
from pathlib import Path

import bpy  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
WT = common.repo_root(__file__)
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, hull, pchip  # noqa: E402

NAME = "sidekick-protron-cannon-tangerine"
MODEL = "sidekicks/protron-cannon-tangerine"
TEXTURED = (HOUSING_I := 0, 1, 2, 3, 4, 5, 6, 12)
ROOT = WT
AX = 0.5  # mirror axis (column 12's centre)

(HOUSING, CHEEK, LUG, PRONG, CORE, CLAMP, BRONZE, LENS, DARK, LAMPF, LAMPF_LENS, LAMPR, TRIM) = range(13)


def materials(sprite):
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    return [
        pal(7, metallic=0.2, roughness=0.5),    # HOUSING gun housings (median 7)
        pal(6, metallic=0.2, roughness=0.52),   # CHEEK armour cheeks (L7/R4)
        pal(4, metallic=0.2, roughness=0.52),    # LUG side lugs (L3/R5)
        pal(5, metallic=0.2, roughness=0.5),   # PRONG pincer prongs
        pal(21, metallic=0.2, roughness=0.5),   # CORE bronze protron chamber
        pal(10, metallic=0.2, roughness=0.48),  # CLAMP grey clamp bands (rows 6, 8)
        pal(20, metallic=0.2, roughness=0.48),   # BRONZE hinge pins, claw teeth
        pal(106, metallic=0.1, roughness=0.15),  # LENS blue-grey targeting lens
        pal(1, metallic=0.2, roughness=0.6),     # DARK bores
        pal(66, metallic=0.3, roughness=0.4),    # LAMPF dark-red lamp housing
        pal(113, metallic=0.0, roughness=0.15, emission_strength=0.6),  # LAMPF_LENS
        pal(118, metallic=0.0, roughness=0.2, emission_strength=0.8),   # LAMPR rear lamp band
        pal(3, metallic=0.2, roughness=0.52),    # TRIM bolt heads, bore bezels
    ]


# --- helpers (copied here, not shared) ------------------------------------------------------------

def mx(x):
    return 2 * AX - x


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _centre(ring):
    n = len(ring)
    return tuple(sum(p[i] for p in ring) / n for i in range(3))


def loft(part, rings, mats, cap0=True, cap1=True, cap_mats=None):
    """Quads between consecutive rings (lists of 3D points, equal length, closed loops; sections may be
    concave). `mats`: one material per band (or one for all). Caps are n-gons. Each side face's
    outward hint is its edge x the loft direction, signed by the ring's winding, so grooves and ribs
    orient right."""
    vr = [[part.v(p) for p in ring] for ring in rings]
    n = len(rings[0])
    if isinstance(mats, int):
        mats = [mats] * (len(rings) - 1)
    for k in range(len(rings) - 1):
        a, b = vr[k], vr[k + 1]
        ca, cb = _centre(rings[k]), _centre(rings[k + 1])
        d = _sub(cb, ca)
        wind = sum(_dot(_cross(_sub(rings[k][i], ca), _sub(rings[k][(i + 1) % n], ca)), d) for i in range(n))
        sgn = 1.0 if wind > 0 else -1.0
        for i in range(n):
            j = (i + 1) % n
            e = _sub(rings[k][j], rings[k][i])
            if _dot(e, e) < 1e-12:
                e = _sub(rings[k + 1][j], rings[k + 1][i])
            o = _cross(e, d)
            part.f([a[i], a[j], b[j], b[i]], mats[k], out=(o[0] * sgn, o[1] * sgn, o[2] * sgn))
    cm = cap_mats or (mats[0], mats[-1])
    if cap0:
        d = _sub(_centre(rings[0]), _centre(rings[1]))
        part.f(list(vr[0]), cm[0], out=d)
    if cap1:
        d = _sub(_centre(rings[-1]), _centre(rings[-2]))
        part.f(list(vr[-1]), cm[1], out=d)


def crown_sec(hw, zb, zw, zc, ch=0.3, n=8, p=2.6):
    """A flat-walled, round-crowned section in (u, z): chamfered bottom corners, walls to zw, a
    superellipse crown (exponent p; 2 = a plain arc) peaking at zc: flatter top, tighter shoulders."""
    pts = [(-hw + ch, zb), (hw - ch, zb), (hw, zb + ch), (hw, zw)]
    e = 2 / p
    for k in range(1, n):
        a = math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        pts.append((hw * math.copysign(abs(c) ** e, c), zw + (zc - zw) * s ** e))
    pts += [(-hw, zw), (-hw, zb + ch)]
    return pts


def frange(a, b, step):
    n = max(1, int(round((b - a) / step)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def grooves(ys, centres, depth=0.18, half=0.12):
    """Station list with groove rings: three stations per groove (lip, floor, lip)."""
    out = set(ys)
    for g in centres:
        out |= {g - half - 0.02, g - half * 0.5, g + half * 0.5, g + half + 0.02}
    return sorted(out)


def groove_depth(y, centres, depth=0.18, half=0.12):
    for g in centres:
        if abs(y - g) < half * 0.5 + 1e-6:
            return depth
    return 0.0


# --- parts -----------------------------------------------------------------------------------------

def housing(part, side):
    """Gun housing: x -4..-1 (columns 8-10), y 4.0 front to 12.9 rear."""
    cx = -2.5
    yf, yr = 4.0, 12.9
    crest = pchip([4.0, 4.35, 4.95, 5.6, 11.6, 12.3, 12.9], [1.9, 2.75, 3.45, 3.7, 3.7, 3.05, 2.1])
    wall = pchip([4.0, 5.6, 11.6, 12.9], [1.0, 2.1, 2.1, 1.2])
    hw = pchip([4.0, 4.3, 12.4, 12.9], [1.42, 1.5, 1.5, 1.3])
    gs = [5.75, 8.45, 10.7, 12.05]
    ys = grooves(frange(4.0, 5.6, 0.4) + frange(5.6, 11.6, 1.5) + frange(11.6, 12.9, 0.33), gs)
    rings = []
    for y in ys:
        d = groove_depth(y, gs)
        sec = crown_sec(hw(y) - d * 0.5, -0.6, wall(y) - d * 0.3, crest(y) - d, ch=0.3)
        rings.append([(side_x(cx + u, side), y, z) for u, z in sec])
    loft(part, rings, HOUSING)
    # Muzzle: a raised bezel and the dark bore on the front face, low under the glacis.
    for (r, y0, y1, m) in ((0.72, 3.8, 4.1, TRIM), (0.46, 3.72, 3.85, DARK)):
        pts = []
        for i in range(12):
            a = 2 * math.pi * i / 12
            for y in (y0, y1):
                pts.append((side_x(cx + r * math.cos(a), side), y, 0.55 + r * math.sin(a)))
        hull(part, pts, m)
    # Targeting lens on the glacis (row 4, columns 9-10): a dark bezel and the blue-grey glass in it.
    def on_crown(x, y, dz):
        u = (x - cx) / hw(y)
        return wall(y) + (crest(y) - wall(y)) * math.sqrt(max(0.0, 1 - u * u)) + dz

    # A flat window on the glacis slope (not following the crown): a dark bezel, the glass proud of it.
    for (x0, x1, y0, y1, dz, m) in ((-3.35, -1.3, 4.02, 5.0, 0.16, TRIM), (-3.1, -1.55, 4.14, 4.86, 0.24, LENS)):
        za, zb = on_crown(cx, y0, -0.05) + dz, on_crown(cx, y1, -0.05) + dz
        zlow = min(on_crown(x0, y0, -0.5), on_crown(x1, y0, -0.5))
        pts = []
        for x in (x0, x1):
            for y, z in ((y0, za), (y1, zb)):
                pts += [(side_x(x, side), y, z), (side_x(x, side), y, zlow)]
        hull(part, pts, m)


def side_x(x, side):
    return x if side < 0 else mx(x)


def chamber(part):
    """The bronze protron chamber between the housings: x -1..2, y 4.9..14.1, with clamp bands."""
    cx = AX
    crest = pchip([4.9, 5.4, 6.2, 9.5, 12.6, 13.5, 14.1], [2.1, 2.6, 2.85, 3.05, 2.8, 2.2, 1.2])
    wall = pchip([4.9, 6.0, 12.6, 14.1], [0.9, 1.1, 1.1, 0.6])
    hw = pchip([4.9, 5.3, 12.8, 13.6, 14.1], [1.15, 1.5, 1.5, 1.4, 0.75])
    ys = frange(4.9, 6.2, 0.43) + frange(6.2, 12.6, 1.6) + frange(12.6, 14.1, 0.375)
    rings = []
    for y in sorted(set(round(v, 4) for v in ys)):
        sec = crown_sec(hw(y), -0.5, wall(y), crest(y), ch=0.3)
        rings.append([(cx + u, y, z) for u, z in sec])
    loft(part, rings, CORE)
    # Emitter cap (row 5): a short bronze drum on the nose.
    rings = []
    for y in (4.75, 5.05, 5.75):
        g = 0.12 if y < 5.0 else 0.0
        sec = crown_sec(1.25 - g, -0.3, 1.2, 2.55 - g, ch=0.25)
        rings.append([(cx + u, y, z) for u, z in sec])
    loft(part, rings, BRONZE)
    # Clamp bands (rows 6 and 8): grey rings standing proud of the chamber.
    for y0, y1 in ((6.05, 6.95), (8.05, 8.95)):
        rings = []
        for y, e in ((y0, 0.0), (y0 + 0.15, 0.18), (y1 - 0.15, 0.18), (y1, 0.0)):
            sec = crown_sec(1.5 + e * 0.5, -0.55, 1.1 + e, crest(y) + 0.08 + e, ch=0.3)
            rings.append([(cx + u, y, z) for u, z in sec])
        loft(part, rings, CLAMP)


def cheek(part, side):
    """Armour cheek: x -7..-3.6, y 5..13; a rib crest at column 7, a groove at column 6."""
    yf, yr = 5.0, 13.0
    xo = pchip([5.0, 5.6, 6.2, 12.4, 13.0], [-5.75, -6.3, -6.95, -6.95, -6.7])
    top = pchip([5.0, 5.7, 12.2, 13.0], [1.2, 2.3, 2.3, 1.8])
    gs = [7.55, 11.0]
    ys = grooves(frange(5.0, 6.1, 0.37) + frange(6.1, 12.2, 1.5) + frange(12.2, 13.0, 0.4), gs)
    rings = []
    for y in ys:
        d = groove_depth(y, gs, depth=0.16)
        o = xo(y)
        t = top(y) - d
        # outer wall, step (outer strake), groove, rib crest, inner slope into the housing.
        sec = [(o + 0.25, -0.45), (-3.6, -0.45), (-3.6, t - 0.4), (-4.4, t - 0.05), (-4.8, t),
               (-5.25, t - 0.1), (-5.55, t - 0.55), (-5.85, t - 0.6), (-6.05, t - 0.45),
               (o + 0.2, t - 0.6), (o, t - 0.9), (o, -0.2)]
        rings.append([(side_x(x, side), y, z) for x, z in sec])
    loft(part, rings, CHEEK)
    # Front marker lamp on the front-outer corner (rows 6-7, columns 4-5): housing + lens.
    pts = cbox(-7.3, -5.85, 6.05, 8.0, 0.1, 2.0, 0.25)
    hull(part, [(side_x(x, side), y, z) for x, y, z in pts], LAMPF)
    pts = cbox(-7.42, -6.55, 6.2, 7.75, 0.45, 2.1, 0.22)
    hull(part, [(side_x(x, side), y, z) for x, y, z in pts], LAMPF_LENS)


def lug(part, side):
    """Side lug (columns 3-4, rows 8-10, the outer rear corner cut at row 11)."""
    pts = []
    for y, xo in ((7.9, -8.6), (8.3, -9.05), (10.8, -9.05), (11.85, -8.05)):
        for x in (xo, -6.6):
            for z, g in ((-0.35, 0.25), (1.15, 0.0), (1.6, 0.35)):
                xx = x + (g if x < -7 else 0)
                yy = y + (g if y < 8 else -g if y > 11.5 else 0)
                pts.append((side_x(xx, side), yy, z))
    hull(part, pts, LUG)
    # Two bolt heads on the pad.
    for yb in (8.8, 10.2):
        pts = []
        for i in range(8):
            a = 2 * math.pi * i / 8
            for z, r in ((1.45, 0.3), (1.78, 0.24)):
                pts.append((side_x(-7.9 + r * math.cos(a), side), yb + r * math.sin(a), z))
        hull(part, pts, TRIM)


def prong(part, side):
    """Pincer prong: a path loft from the rear corner, aft, bowing out and curling in to a bronze tooth."""
    ctrl = [  # (x, y, half width, top z, bottom z)
        (-5.3, 12.2, 1.7, 2.3, -0.4),
        (-5.9, 14.0, 1.12, 2.2, -0.35),
        (-6.85, 15.6, 1.05, 2.0, -0.3),
        (-7.0, 17.0, 1.08, 1.85, -0.25),
        (-6.65, 18.45, 1.35, 1.7, -0.2),
        (-5.6, 19.65, 1.22, 1.5, -0.15),
        (-4.3, 20.35, 1.0, 1.3, -0.1),
        (-2.75, 20.85, 0.12, 0.85, 0.05),
    ]
    ts = list(range(len(ctrl)))
    fx = pchip(ts, [c[0] for c in ctrl])
    fy = pchip(ts, [c[1] for c in ctrl])
    fw = pchip(ts, [c[2] for c in ctrl])
    ft = pchip(ts, [c[3] for c in ctrl])
    fb = pchip(ts, [c[4] for c in ctrl])
    samples = frange(0, 5.6, 0.47) + [6.2, 6.6, 7.0]
    lamp = (2.95, 3.6)  # red band (row 17)
    tooth_t = 4.85
    joint = 1.45  # the dark joint at rows 14-15
    samples = sorted(set([round(s, 3) for s in samples if abs(s - joint) > 0.15 and abs(s - tooth_t) > 0.15]
                         + [lamp[0] - 0.02, lamp[0], lamp[1], lamp[1] + 0.02,
                            joint - 0.1, joint - 0.04, joint + 0.04, joint + 0.1,
                            tooth_t - 0.12, tooth_t - 0.05, tooth_t, tooth_t + 0.1]))
    dip = {joint - 0.04: -0.14, joint + 0.04: -0.14, tooth_t - 0.05: -0.14, tooth_t: 0.06, tooth_t + 0.1: 0.05}

    def frame(t):
        e = 0.02
        dx, dy = fx(t + e) - fx(t - e), fy(t + e) - fy(t - e)
        L = math.hypot(dx, dy)
        tx, ty = dx / L, dy / L
        out = (-ty, tx)  # outward: -x while heading south, south while heading east (the curl)
        return (fx(t), fy(t)), out

    def ring(t, grow=0.0):
        (px, py), o = frame(t)
        w = fw(t) + grow
        zt, zb = ft(t) + grow, fb(t) - grow * 0.5
        ch = min(0.35, w * 0.4)
        # (u outward, z): a chamfered arm with its ridge toward the outer edge.
        sec = [(-w + ch * 0.6, zb), (w - ch * 0.6, zb), (w, zb + ch * 0.6), (w, zt - ch - 0.3),
               (w * 0.55, zt), (w * 0.2, zt - 0.05), (-w + ch, zt - 0.35), (-w, zt - 0.35 - ch)]
        return [(side_x(px + u * o[0], side), py + u * o[1], z) for u, z in sec]

    rings = [ring(t, dip.get(t, 0.0)) for t in samples]
    mats = []
    for a, b in zip(samples, samples[1:]):
        m = (a + b) / 2
        mats.append(BRONZE if m > tooth_t - 0.03 else PRONG)
    loft(part, rings, mats, cap_mats=(PRONG, BRONZE))
    # Red lamp band round the arm (row 17).
    rings = [ring(t, g) for t, g in ((lamp[0], 0.0), (lamp[0] + 0.06, 0.13), (lamp[1] - 0.06, 0.13), (lamp[1], 0.0))]
    loft(part, rings, LAMPR)
    # Bronze hinge pin at the prong root (rows 12-13, columns 8-9), across under the housing's tail.
    pts = []
    for i in range(10):
        a = 2 * math.pi * i / 10
        for x in (-4.5, -3.1):
            pts.append((side_x(x, side), 13.05 + 0.62 * math.cos(a), 1.5 + 0.62 * math.sin(a)))
    hull(part, pts, BRONZE)


def bake(obj):
    tint, tex = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = (1.0, 1.0, 1.0), TEXTURED
    try:
        T.bake_maps(obj, tempfile.mkdtemp(prefix="pct_bake_"), size=512, samples=48)
    finally:
        T.TINT, T.TEXTURED = tint, tex
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", NAME)


def build(sprite, coll):
    mats = materials(sprite)
    P = Part(NAME, smooth_angle=35.0)
    chamber(P)
    for s in (-1, 1):
        housing(P, s)
        cheek(P, s)
        lug(P, s)
        prong(P, s)
    obj = T.finish(P, mats, coll)
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles")
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=1300, smooth=6, inside=0.004)
    if "--no-bake" not in sys.argv:
        bake(obj)
        fmt = "WEBP"
    else:
        fmt = "AUTO"
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
