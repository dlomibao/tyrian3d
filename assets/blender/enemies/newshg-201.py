"""newshg-201: the small domed gunboat (newshg.shp size 2, frame 201), hard-surface (D65).

WHAT IT IS: a small hovering gunboat of 2.6 GRYPHON. Placed by custom events 49-52 in rows on the
top layer, moving only with its layer's scroll; the 2.6 capture (tick 900-4200, sprites=original)
shows them drawn with a drop shadow over pipes AND over open space, so it flies: a closed round
underside, nose (dome) up-screen.

Reading the sprite (edge coords: x = column edge, y = row edge, z up, all in sprite px):
- a glossy glass ball (61) on the nose, cols 7-15 rows 1-8, sitting in a collar ring (57) on a
  cup-shaped nose fairing; twin chin guns under its flanks (hidden from the top view).
- the forward block (rows 8-13, cols 6-17, centred on col edge 12 like the sprite) with a square
  shaft straight through it (transparent cols 11-12 rows 11-12): a lined vertical bay.
- two light armour rails (57) down the deck at cols 8 and 14 (rows 9-18), turning in at row 19.
- between them, aft of the shaft, a louvred grille: slats at rows 14/16/18 (54) over a dark floor.
- square stub wings (55) rows 14-18, chamfered leading edge (the bright row-14 band is that bevel's
  sheen), a lower trailing flap (51) rows 17-18.
- a tapering tail (52) with a raised keel plate (54) between V grooves and a centre spine; a dark
  exhaust at the tail end (rows 25).
- two brown engine pods (164) at the back corners (rows 19-24), intake ring (168), nozzle (161/160).
The sprite's outline ring and shading are lighting; bright spots are sheen (gloss), not geometry.

Exports public/models/enemies/newshg-201.glb and src/render/spriteModels/newshg-201.json.

    tools/build-models.sh -j 2 assets/blender/enemies/newshg-201.py
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "newshg-201"
AX = 11.5          # symmetry axis (column edge) of the dome, wings and tail
BX = 12.0          # the forward block and its shaft sit half a pixel right, as in the sprite


class Part(T.Part):
    """T.Part in sprite edge coordinates: x shifted so T.finish centres it (X = (x - 12) / 12)."""

    def v(self, p):
        return self.bm.verts.new((p[0] - 12.0, p[1], p[2]))

    def f(self, verts, mat, out=None, away=None):
        if away is not None:
            away = (away[0] - 12.0, away[1], away[2])
        return super().f(verts, mat, out=out, away=away)


# --- helpers ---------------------------------------------------------------------------------------

def sel(t, p):
    c, s = math.cos(t), math.sin(t)
    return math.copysign(abs(c) ** (2 / p), c), math.copysign(abs(s) ** (2 / p), s)


def rrect(cx, cy, a, b, p, n):
    """Superellipse loop in XY, n points, starting at +x, counter-clockwise in (x, y)."""
    out = []
    for i in range(n):
        u, w = sel(2 * math.pi * i / n, p)
        out.append((cx + a * u, cy + b * w))
    return out


def grow(loop, cx, cy, d):
    """Push each point of a superellipse loop out from (cx, cy) by d along its radial direction,
    scaled so straight sides move by about d."""
    out = []
    n = len(loop)
    for i, (x, y) in enumerate(loop):
        x0, y0 = loop[i - 1]
        x1, y1 = loop[(i + 1) % n]
        tx, ty = x1 - x0, y1 - y0
        L = math.hypot(tx, ty) or 1
        nx, ny = ty / L, -tx / L
        if nx * (x - cx) + ny * (y - cy) < 0:
            nx, ny = -nx, -ny
        out.append((x + nx * d, y + ny * d))
    return out


def ring_faces(P, r0, r1, mat, out_fn):
    n = len(r0)
    for i in range(n):
        j = (i + 1) % n
        q = (r0[i], r0[j], r1[j], r1[i])
        c = sum((Vector(v.co) for v in q), Vector()) / 4
        P.f(q, mat, out=out_fn(c))


def prism(P, loop, cx, cy, z0, z1, ct, cb, mat, top_mat=None):
    """A chamfered prism over a convex loop (top chamfer ct, bottom chamfer cb)."""
    rings = []
    rings.append([P.v((x, y, z0)) for x, y in grow(loop, cx, cy, -cb)])
    rings.append([P.v((x, y, z0 + cb)) for x, y in loop])
    rings.append([P.v((x, y, z1 - ct)) for x, y in loop])
    rings.append([P.v((x, y, z1)) for x, y in grow(loop, cx, cy, -ct)])
    side = lambda c: (c.x - (cx - 12), c.y - cy, 0.0)  # noqa: E731
    for a, b in zip(rings, rings[1:]):
        ring_faces(P, a, b, mat, side)
    P.f(rings[0], mat, out=(0, 0, -1))
    P.f(rings[-1], top_mat if top_mat is not None else mat, out=(0, 0, 1))


def frame_prism(P, outer, ocx, ocy, inner, icx, icy, z0, z1, ct, cb, ci, mat, wall_mat):
    """A chamfered prism with a vertical hole straight through it (outer and inner loops the same
    length). The hole's lips are chamfered by ci."""
    o = [[P.v((x, y, z0)) for x, y in grow(outer, ocx, ocy, -cb)],
         [P.v((x, y, z0 + cb)) for x, y in outer],
         [P.v((x, y, z1 - ct)) for x, y in outer],
         [P.v((x, y, z1)) for x, y in grow(outer, ocx, ocy, -ct)]]
    h = [[P.v((x, y, z1)) for x, y in grow(inner, icx, icy, ci)],
         [P.v((x, y, z1 - ci)) for x, y in inner],
         [P.v((x, y, z0 + ci)) for x, y in inner],
         [P.v((x, y, z0)) for x, y in grow(inner, icx, icy, ci)]]
    side = lambda c: (c.x - (ocx - 12), c.y - ocy, 0.0)  # noqa: E731
    for a, b in zip(o, o[1:]):
        ring_faces(P, a, b, mat, side)
    hole = lambda c: ((icx - 12) - c.x, icy - c.y, 0.0)  # noqa: E731
    for a, b in zip(h, h[1:]):
        ring_faces(P, a, b, wall_mat, hole)
    ring_faces(P, o[-1], h[0], mat, lambda c: (0, 0, 1))
    ring_faces(P, h[-1], o[0], mat, lambda c: (0, 0, -1))


def loft(P, rings, mats, cap0=True, cap1=True):
    """rings: [(points [(x, y, z)], centre (x, y, z))]; mats[i] between ring i and i + 1."""
    vs = [([P.v(p) for p in pts], c) for pts, c in rings]
    for i, ((r0, c0), (r1, _c1)) in enumerate(zip(vs, vs[1:])):
        n = len(r0)
        for a in range(n):
            b = (a + 1) % n
            P.f((r0[a], r0[b], r1[b], r1[a]), mats[i], away=c0)
    if cap0:
        P.f(vs[0][0], mats[0], out=(0, -1, 0))
    if cap1:
        P.f(vs[-1][0], mats[-1], out=(0, 1, 0))


def tube_y(P, xc, zc, prof, mats, seg=16, cap0=True, cap1=True):
    """A round tube along +y: prof [(y, r)], mats per band (or one)."""
    rings = []
    for y, r in prof:
        rings.append(([(xc + r * math.cos(2 * math.pi * k / seg), y, zc + r * math.sin(2 * math.pi * k / seg))
                       for k in range(seg)], (xc, y, zc)))
    m = mats if isinstance(mats, list) else [mats] * (len(prof) - 1)
    loft(P, rings, m, cap0, cap1)


def ellipsoid(P, c, r, mat, seg=32, rings=12, lo=0.0, hi=1.0, cap=True):
    """Part of an ellipsoid between latitude fractions lo..hi (0 = bottom pole, 1 = top pole)."""
    cx, cy, cz = c
    rx, ry, rz = r
    lats = [lo + (hi - lo) * i / rings for i in range(rings + 1)]
    rows = []
    for t in lats:
        phi = math.pi * (t - 0.5)
        s, zz = math.cos(phi), math.sin(phi)
        if s < 1e-4:
            rows.append([P.v((cx, cy, cz + rz * zz))])
        else:
            rows.append([P.v((cx + rx * s * math.cos(2 * math.pi * k / seg), cy + ry * s * math.sin(2 * math.pi * k / seg),
                              cz + rz * zz)) for k in range(seg)])
    for a, b in zip(rows, rows[1:]):
        for k in range(seg):
            j = (k + 1) % seg
            q = [a[k % len(a)], a[j % len(a)], b[j % len(b)], b[k % len(b)]]
            uniq = []
            for v in q:
                if v not in uniq:
                    uniq.append(v)
            P.f(uniq, mat, away=c)
    if cap and len(rows[0]) > 1:
        P.f(rows[0], mat, out=(0, 0, -1))
    if cap and len(rows[-1]) > 1:
        P.f(rows[-1], mat, out=(0, 0, 1))


def box(P, x0, x1, y0, y1, z0, z1, mat, ch=0.15, chz=None):
    T.hull(P, [(x - 12.0, y, z) for x, y, z in T.cbox(x0, x1, y0, y1, z0, z1, ch, chz)], mat)


# --- hull profiles ---------------------------------------------------------------------------------

YS = [13.8, 15.0, 17.0, 19.0, 20.5, 22.0, 23.5, 24.6, 25.3, 25.75, 26.0]
HW = T.pchip([13.8, 17.0, 19.0, 20.5, 23.5, 24.6, 25.3, 25.75, 26.0], [5.5, 5.45, 5.3, 5.15, 5.05, 4.6, 3.6, 2.9, 2.5])
ZT = T.pchip([13.8, 17.0, 19.5, 22.0, 24.5, 26.0], [2.95, 2.85, 2.55, 2.1, 1.6, 1.2])
ZB = T.pchip([13.8, 19.0, 23.0, 25.0, 26.0], [-1.7, -1.7, -1.45, -1.0, -0.5])
NSEC = 28


def hull_section(y):
    """Flat deck with rounded shoulders (p 4) over a round belly (p 2.2)."""
    w, zt, zb = HW(y), ZT(y), ZB(y)
    zm = zb + 0.55 * (zt - zb)
    pts = []
    for k in range(NSEC):
        t = 2 * math.pi * k / NSEC
        c, s = math.cos(t), math.sin(t)
        p = 4.0 if s >= 0 else 2.2
        u = math.copysign(abs(c) ** (2 / p), c)
        v = abs(s) ** (2 / p)
        z = zm + v * ((zt - zm) if s >= 0 else (zb - zm))
        pts.append((AX + w * u, y, z))
    return pts, (AX, y, zm)


def deck_z(x, y):
    """Top of the hull section at (x, y)."""
    w, zt, zb = HW(y), ZT(y), ZB(y)
    zm = zb + 0.55 * (zt - zb)
    u = min(1.0, abs(x - AX) / w)
    return zm + (zt - zm) * (1 - u ** 4) ** 0.25


def strip(P, path, hw, lift, mat, depth=0.5, ch=0.22, top=None):
    """A chamfered strip laid on the deck along path [(x, y)] (rails, keel plate, spine).
    hw is a number or a function of y; top(x, y) gives the surface (default the hull deck)."""
    top = top or deck_z
    rings = []
    for (x, y) in path:
        w = hw(y) if callable(hw) else hw
        z = top(x, y)
        zl, zr = top(x - w, y), top(x + w, y)
        c = min(ch, w * 0.45)
        pts = [(x - w, y, zl - depth), (x - w, y, zl + lift - c), (x - w + c, y, max(zl, z) + lift),
               (x + w - c, y, max(zr, z) + lift), (x + w, y, zr + lift - c), (x + w, y, zr - depth)]
        rings.append((pts, (x, y, z)))
    loft(P, rings, [mat] * (len(rings) - 1))


# --- the model ---------------------------------------------------------------------------------------

def build(sprite, coll):
    mats = []

    def M(i, metallic=0.45, roughness=0.4, tag="m"):
        mat = common.palette_material(sprite, i, f"{NAME}_{tag}", metallic=metallic, roughness=roughness)
        if mat not in mats:
            mats.append(mat)
        return mats.index(mat)

    BODY = M(55, tag="body")
    BLOCK = M(56, tag="block")
    RAIL = M(57, 0.5, 0.3, tag="rail")
    COLLAR = M(59, 0.5, 0.35, tag="collar")
    RING = M(57, 0.5, 0.35, tag="ring")
    GLASS = M(61, 0.15, 0.08, tag="glass")
    GRILLE = M(54, tag="slat")
    FLOOR = M(50, 0.4, 0.6, tag="floor")
    SHAFT = M(50, 0.4, 0.6, tag="shaft")
    FLAP = M(51, tag="flap")
    TAIL = M(52, tag="tail")
    KEEL = M(54, tag="keel")
    SPINE = M(54, 0.5, 0.35, tag="spine")
    BELLY = M(53, 0.4, 0.5, tag="belly")
    POD = M(164, 0.45, 0.4, tag="pod")
    INTAKE = M(168, 0.5, 0.35, tag="intake")
    NOZ = M(165, 0.45, 0.4, tag="nozzle")
    GROOVE = M(160, 0.3, 0.7, tag="groove")
    BORE = M(160, 0.3, 0.7, tag="bore")
    GUN = M(52, 0.55, 0.35, tag="gun")
    EXH = M(49, 0.4, 0.6, tag="exhaust")

    P = Part(NAME, smooth_angle=32.0)

    # Forward block with the shaft through it (cols 6-17, rows 8-14), centred on BX like the sprite.
    outer = rrect(BX, 11.2, 6.0, 3.05, 6.0, 48)
    inner = rrect(BX, 12.0, 1.85, 1.85, 3.0, 48)
    frame_prism(P, outer, BX, 11.2, inner, BX, 12.0, -1.6, 3.0, 0.55, 0.9, 0.18, BLOCK, SHAFT)

    # Aft hull: deck 55 forward, 52 on the tail; belly faces get 53 below.
    rings = [hull_section(y) for y in YS]
    loft(P, rings, [BODY if y < 19.0 else TAIL for y in YS[:-1]])

    # Nose: the dome's cup (lower half-ellipsoid) and the collar ring at the dome's equator.
    DC = (AX, 4.75, 1.35)
    ellipsoid(P, (AX, 4.85, 1.25), (4.25, 3.65, 2.7), BODY, seg=32, rings=6, lo=0.0, hi=0.5)
    # collar: a flat ring, outer = the sprite's ring, inner under the glass
    seg = 40
    ring_pts = lambda rx, ry, z: [(AX + rx * math.cos(2 * math.pi * k / seg), DC[1] + ry * math.sin(2 * math.pi * k / seg), z)  # noqa: E731
                                  for k in range(seg)]
    rr = [ring_pts(4.0, 3.35, 0.6), ring_pts(4.5, 3.85, 1.0), ring_pts(4.5, 3.85, 1.55), ring_pts(4.25, 3.6, 1.85),
          ring_pts(3.9, 3.25, 1.85)]
    rv = [[P.v(p) for p in r] for r in rr]
    for a, b in zip(rv, rv[1:]):
        ring_faces(P, a, b, RING, lambda c: (c.x - (AX - 12), c.y - DC[1], 0.35))
    P.f(rv[-1], RING, out=(0, 0, 1))
    P.f(rv[0], RING, out=(0, 0, -1))
    # the glass ball
    ellipsoid(P, (AX, DC[1], 1.55), (4.12, 3.5, 3.25), GLASS, seg=40, rings=10, lo=0.42, hi=1.0)
    # a support neck from the cup back into the block (hidden from the top by glass and block)
    box(P, AX - 3.0, AX + 3.6, 6.5, 9.4, -1.3, 1.6, BODY, ch=0.5)

    # Cooling vents on the block's flanks: a dark recess with three slats.
    for side in (-1, 1):
        xw = BX + side * 6.0
        box(P, min(xw - side * 0.3, xw + side * 0.05), max(xw - side * 0.3, xw + side * 0.05), 9.9, 13.3, 0.1, 2.0, FLOOR, ch=0.03)
        for z0 in (0.3, 0.9, 1.5):
            box(P, min(xw - side * 0.35, xw + side * 0.12), max(xw - side * 0.35, xw + side * 0.16), 10.05, 13.15,
                z0, z0 + 0.32, BLOCK, ch=0.08)

    # Saddle plate where the glass's ring meets the block (the lit row 8 behind the dome).
    box(P, AX - 3.2, AX + 3.7, 7.9, 9.3, 2.2, 3.3, COLLAR, ch=0.35, chz=0.25)

    # Twin chin guns under the glass's flanks: barrel, jacket, muzzle ring.
    for side in (-1, 1):
        gx = AX + side * 2.95
        tube_y(P, gx, -0.85, [(3.4, 0.38), (3.6, 0.5), (4.3, 0.5), (4.5, 0.36), (8.8, 0.36)], [GUN, GUN, GUN, GUN], seg=12)
        tube_y(P, gx, -0.85, [(3.38, 0.2), (3.42, 0.2)], BORE, seg=8)
        box(P, gx - 0.75, gx + 0.75, 6.4, 9.0, -1.6, -0.2, BLOCK, ch=0.3)

    # Armour rails (cols 8 / 14), running over the block and down the deck, turning in at row 19.
    def block_top(x, y):
        return 3.0 if y < 14.15 else deck_z(x, y)
    for side in (-1, 1):
        rx = AX + side * 3.0
        path = [(rx, 8.75), (rx, 9.3)] + [(rx, y) for y in (11.0, 13.0, 14.1, 14.4, 16.0, 18.0, 18.7)] + \
               [(rx - side * 0.5, 19.35), (rx - side * 1.1, 19.95)]
        strip(P, path, lambda y: 0.5 if y < 19 else 0.42, 0.42, RAIL, depth=0.55, ch=0.22, top=block_top)

    # The louvred grille between the rails, aft of the shaft (rows 14-18).
    box(P, AX - 2.48, AX + 2.48, 13.85, 19.15, 2.35, 3.0, FLOOR, ch=0.08)
    for y0, y1 in ((14.0, 14.95), (16.0, 16.95), (18.0, 18.95)):
        box(P, AX - 2.5, AX + 2.5, y0, y1, 2.6, 3.25, GRILLE, ch=0.22, chz=0.18)

    # Keel plate between the tail's V grooves, and the centre spine.
    kp = [(AX, y) for y in (19.65, 20.4, 21.5, 22.6, 23.7, 24.6, 25.25)]
    strip(P, kp, T.pchip([19.65, 20.4, 22.6, 24.6, 25.25], [3.0, 3.3, 2.6, 1.5, 0.9]), 0.22, KEEL, depth=0.4, ch=0.25)
    strip(P, [(AX, y) for y in (19.2, 20.0, 22.0, 24.0, 25.4)], 0.48, 0.5, SPINE, depth=0.5, ch=0.2)
    # Tail exhaust: a dark round port in the tail's end.
    tube_y(P, AX, 0.3, [(25.5, 0.95), (26.15, 0.95), (26.25, 0.8)], [TAIL, TAIL], seg=16)
    tube_y(P, AX, 0.3, [(26.2, 0.6), (26.27, 0.6)], EXH, seg=12)

    # Stub wings: a main panel with a chamfered leading edge and a lower trailing flap.
    for side in (-1, 1):
        def X(x):
            return AX + side * (AX - x)
        main = [(1.0, 14.25), (1.3, 13.95), (4.7, 13.95), (5.5, 13.25), (7.0, 13.25), (7.0, 17.25), (1.0, 17.25)]
        flap = [(1.0, 17.05), (6.6, 17.05), (6.6, 19.75), (2.05, 19.75), (1.0, 18.95)]
        for loop, z0, z1, ct, cb, mat in ((main, -0.55, 1.15, 0.55, 0.35, BODY), (flap, -0.4, 0.75, 0.3, 0.25, FLAP)):
            pts = [(X(x), y) for x, y in loop]
            if side > 0:
                pts.reverse()
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            prism(P, pts, cx, cy, z0, z1, ct, cb, mat)
        # wing root fairing (the dark col-5 seam) and a wingtip edge strip
        box(P, X(5.1) - 0.45, X(5.1) + 0.45, 13.6, 19.4, -0.9, 1.35, FLAP, ch=0.25)

    # Engine pods at the back corners: intake ring, body, nozzle shroud, dark bore; a pylon in.
    for side in (-1, 1):
        px_ = AX + side * (AX - 5.05)
        tube_y(P, px_, 0.35, [(19.0, 1.0), (19.3, 1.55), (19.7, 1.85), (20.5, 1.9), (20.6, 1.8),
                              (22.75, 1.8), (22.85, 1.45), (23.25, 1.45), (23.35, 1.62), (24.8, 1.45), (25.05, 1.3)],
               [INTAKE, INTAKE, INTAKE, INTAKE, POD, GROOVE, GROOVE, GROOVE, NOZ, NOZ], seg=20, cap1=False)
        tube_y(P, px_, 0.35, [(25.05, 1.3), (24.75, 0.95), (24.5, 0.0)], [NOZ, BORE], seg=20, cap0=False, cap1=False)
        box(P, min(px_, AX + side * (AX - 7.2)) - 0.2 * (side < 0), max(px_, AX + side * (AX - 7.2)), 19.8, 23.4,
            -0.7, 1.05, TAIL, ch=0.3)

    obj = T.finish(P, [mats[i] for i in range(len(mats))], coll)
    # Belly: faces looking down below the wing plane get the darker underside colour.
    me = obj.data
    for poly in me.polygons:
        if poly.normal.z < -0.5 and poly.material_index in (BODY, TAIL, BLOCK):
            poly.material_index = BELLY
    return obj


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    copy = obj.copy()
    copy.data = obj.data.copy()
    coll.objects.link(copy)
    shell = common.outline_shell(copy, coll, voxel=0.03, faces=2600, smooth=6, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(copy, do_unlink=True)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    obj.data.calc_loop_triangles()
    print(f"{NAME}: {len(obj.data.loop_triangles)} triangles")
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])


if __name__ == "__main__":
    main()
