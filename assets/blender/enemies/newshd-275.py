"""newshd-275 : the brown caged turret of the stone fortress (newshd.shp frames 275, 277,
279; 24 x 28 px), rebuilt hard-surface to the D65 standard.

Reading of the sprite (tools/calibration/rubric.md, "Reading a sprite"):
- The whole tile is the fortress's stone-brick floor (greys 1-11); the machine stands on it,
  centred on column edge 11.5.
- Rows 0-1, cols 6-16: a mount running off the top edge into the next tile: a brown strut (cols
  10-12) between two dark steel pipes (cols 6-9, 13-16).
- Rows 2-4, cols 4-18: a brown cowl (hood) across the back, rounded at its rear corners; its lit
  top edge (173 at row 2) is lighting.
- Rows 5-16, cols 3-19: a square cage of brown bars: rear rail (row 5), side rails (cols 3, 19),
  two uprights (cols 7-8, 14-15), a front rail (row 16) and bay bars (row 15). Solid corner plates
  at the back (cols 4-6 / 16-18, rows 6-8). In the middle a brown housing (cols 9-13, rows 9-11).
  Windows show the dark interior (97-101): the top centre (rows 7-8), the side bays (rows 9-14,
  cols 4-6 / 16-18) and the front centre (rows 12-15).
- A steel axle crosses the cage at row 10 (106-110 in the side bays) and ends in the red lamps on
  both flanks (cols 1-2, 21-22, rows 7-13): the lamps are the axle's hubs, domed lenses. The dark
  column 20 between the cage and the right lamp is the axle's collar (it catches the glow on
  277/279: 5-7).
- A steel breech cylinder (cols 10-12) runs from the housing forward through the window (rows
  12-15) and the neck (rows 18-19) to the barrel.
- Rows 17-20: a brown yoke: a bridge across (row 17) and two cheeks (cols 6-8, 14-16) either side
  of the breech; dark steel feet at the cage's front corners (row 17, cols 2-5 / 17-19).
- Rows 20-26, cols 8-14: the barrel, round, its collar at row 20; the red bore at rows 24-25 sits in
  the lower part of the round end with a brown lip below it: the barrel is pitched up toward the
  viewer (38 deg), so its muzzle face shows as an ellipse from above and faces the tilted camera.
- Frames: only the lamps and the muzzle brighten (275 -> 277 -> 279); on 277 the lower lip glows,
  on 279 the whole muzzle face. One model; palette_material frames= animates those parts (D17).

Colours (trimmed median per region, regions.py): hood 168, rails 165, side rails 168 (169),
uprights 167, corner plates 163, housing 164, mount strut 170, mount pipes 100, axle 106 (the
sprite's 107 is not in its palette; 106 is the nearest it uses), interior 99, breech 104, yoke 164,
collar 168, barrel 167, bore 114 -> 118 -> 122, lamps 115 -> 116 -> 119, feet 99 (the region's
median is 97, an ink-dark step; 99 is the darkest non-ink steel), floor tones as lib_b073.

Hard surface (D50-D53, D65): chamfered bar frame (convex-hull blocks), inset corner plates with a
modelled panel line, a bolted housing with a hatch, pchip-profiled lofts for the hood (rounded-rect
sections with a panel groove round its crown), revolved breech with machined bands, barrel with
collar, panel groove, chamfered lip and recessed glowing bore; lamps as domed lenses in bezel rings.
Floor: stone plate painted per pixel, a separate object marked tyrian_ground, built for the review renders only; not exported (D129: the game draws the tile's ground in HD, and the
plate painted per pixel from the sprite showed as grey pixel cells on it).
Outline shell (D51) from a closed proxy. Underside: closed, plain.

Units while building: sprite px (x = column edge - 12, y = row edge, down the screen, z up), moved
to Blender by usp_talon.finish (1/12, y flipped).

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshd-275.py
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]  # this checkout (was a hardcoded worktree path)
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshd-275"
HERE = Path(__file__).resolve().parent

FL = 0.36      # floor top (0.03 units, lib_b073's FLOOR, so the fortress tiles meet)
CX = -0.5      # machine centre line (column edge 11.5)
ZT = 6.6       # cage top
BAR = 1.05     # bar depth
HOODZ = 7.85   # hood crown
AXZ = 4.0      # axle height
BZ = 3.5       # breech axis height
BR = 1.9       # breech radius
PITCH = math.radians(38)


# --- materials ----------------------------------------------------------------------------------
class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list = []
        self.slots = {}

    def __call__(self, index, part, frames=None, metallic=0.45, roughness=0.45, emission=0.0):
        key = (index, part)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, f"{NAME}_{part}", metallic=metallic,
                                                     roughness=roughness, emission_strength=emission,
                                                     frames=frames))
        return self.slots[key]


# --- helpers ------------------------------------------------------------------------------------
def box(P, x0, x1, y0, y1, z0, z1, mat, ch=0.2, chz=None):
    T.hull(P, T.cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


def basis(u):
    u = Vector(u).normalized()
    ref = Vector((0, 0, 1)) if abs(u.z) < 0.9 else Vector((1, 0, 0))
    e1 = ref.cross(u).normalized()  # horizontal-ish
    e2 = u.cross(e1).normalized()   # up-ish
    return u, e1, e2


def revolve(P, a, u, stations, mat_of, n=16, k1=1.0, k2=1.0, cap0=True, cap1=True, phase=0.5):
    """Rings round the axis from point a along u: stations [(t, r)], t px along the axis, r radius
    (scaled k1 along e1, k2 along e2). mat_of(i, s) gives the material of the faces between
    stations i and i+1 at angle sine s (s < 0: the e2-negative half). Caps close the ends."""
    a = Vector(a)
    u, e1, e2 = basis(u)
    angs = [2 * math.pi * (k + phase) / n for k in range(n)]
    rings = []
    for t, r in stations:
        c = a + u * t
        rings.append([P.v(tuple(c + (e1 * (k1 * r * math.cos(q)) + e2 * (k2 * r * math.sin(q))))) for q in angs])
    for i in range(len(stations) - 1):
        (t0, r0), (t1, r1) = stations[i], stations[i + 1]
        dt, dr = t1 - t0, r1 - r0
        L = math.hypot(dt, dr) or 1.0
        nt, nr = -dr / L, dt / L
        for k in range(n):
            j = (k + 1) % n
            qm = (angs[k] + angs[j] + (2 * math.pi if j == 0 else 0)) / 2
            radial = e1 * (k1 * math.cos(qm)) + e2 * (k2 * math.sin(qm))
            out = u * nt + radial.normalized() * nr
            P.f([rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]], mat_of(i, math.sin(qm)), out=tuple(out))
    if cap0 and stations[0][1] > 1e-6:
        P.f(rings[0], mat_of(0, 1.0), out=tuple(-u))
    if cap1 and stations[-1][1] > 1e-6:
        P.f(rings[-1], mat_of(len(stations) - 2, 1.0), out=tuple(u))
    return rings


def const(m):
    return lambda i, s: m


def rrect(x0, x1, y0, y1, rb, rf, nc=5):
    """Rounded rectangle (plan), back corners (y0 side) radius rb, front (y1) rf: a ring of
    4 * nc points, the same count for any radii (so rings loft point for point)."""
    pts = []
    corners = [(x1 - rf, y1 - rf, rf, 0.0), (x0 + rf, y1 - rf, rf, 0.5 * math.pi),
               (x0 + rb, y0 + rb, rb, math.pi), (x1 - rb, y0 + rb, rb, 1.5 * math.pi)]
    for cx, cy, r, a0 in corners:
        for k in range(nc):
            a = a0 + 0.5 * math.pi * k / (nc - 1)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# --- parts --------------------------------------------------------------------------------------
def hood(P, M):
    """The cowl across the back (cols 4-18, rows 2-5): rounded-rect sections, a pchip shoulder
    falling to the back and sides, a panel groove round its crown; front face upright."""
    x0, x1, y0, y1 = -8.0, 7.0, 2.0, 5.2
    # (z, inset of back and sides): pchip shoulder, then a groove (step down, across, up) and crown.
    zs = [FL, 3.6, 5.4, 6.5, 7.2, 7.62, 7.85]
    ds = [0.0, 0.0, 0.18, 0.55, 1.0, 1.45, 1.9]
    prof = T.pchip(zs, ds)
    levels = [FL, 2.0, 3.6, 4.6, 5.4, 6.0, 6.5, 6.9, 7.2, 7.45, 7.62, 7.75, 7.85]
    secs = [(z, prof(z)) for z in levels]
    secs += [(7.72, 2.05), (7.72, 2.35), (7.85, 2.5)]
    rings = []
    for z, d in secs:
        yb = y0 + 0.6 * d  # the back falls less far than the sides: the crown keeps its depth
        rb = min(max(2.2 - 0.4 * d, 0.6), 0.95 * (y1 - yb - 0.25))
        pts = rrect(x0 + d, x1 - d, yb, y1, rb, 0.25)
        rings.append((z, [P.v((x, y, z)) for x, y in pts]))
    cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2
    for (za, a), (zb, b) in zip(rings, rings[1:]):
        n = len(a)
        for k in range(n):
            j = (k + 1) % n
            q = [a[k], a[j], b[j], b[k]]
            c = sum((Vector(v.co) for v in q), Vector()) / 4
            if abs(za - zb) < 1e-6:
                out = (0, 0, 1) if zb >= 7.8 else (0, 0, 1)
            else:
                out = (c.x - cxm, c.y - cym, 0.6 * (c.z - za))
                if c.y > y1 - 0.01:
                    out = (0, 1, 0)
            P.f(q, M["hood"], out=out)
    top = rings[-1][1]
    P.f(top, M["hood"], out=(0, 0, 1))
    P.f(rings[0][1], M["hood"], out=(0, 0, -1))
    # three louvre slots and a lip on the front face (the face the tilted camera sees above the rail)
    for xa in (-5.6, -1.9, 1.8):
        box(P, xa, xa + 2.8, y1 - 0.2, y1 + 0.06, 6.95, 7.5, M["dark"], ch=0.08)
    box(P, x0 + 0.6, x1 - 0.6, y1 - 0.35, y1 + 0.08, 7.6, 7.95, M["hood"], ch=0.1)
    # a plinth band round the foot of the back and sides, and a bolted cover plate on each rear corner
    box(P, x0 - 0.1, x1 + 0.1, y0 - 0.15, y1 - 0.3, FL, 1.25, M["hood"], ch=0.2)
    for xa in (-7.2, 4.6):
        box(P, xa, xa + 1.6, y0 - 0.12, y0 + 0.4, 1.5, 3.3, M["hood"], ch=0.12)
        for zr in (1.85, 2.95):
            box(P, xa + 0.55, xa + 1.05, y0 - 0.22, y0, zr - 0.2, zr + 0.2, M["rail"], ch=0.06)
    # rivets along the crown's front
    for xr in (-6.5, -3.5, 2.5, 5.5):
        box(P, xr - 0.25, xr + 0.25, 4.2, 4.7, 7.8, 8.0, M["hood"], ch=0.08)


def mount(P, M):
    """Rows 0-2: the strut and two pipes running off the top edge into the next tile."""
    box(P, -2.0, 1.0, 0.0, 2.6, FL, 5.2, M["strut"], ch=0.3)
    box(P, -1.4, 0.4, 0.0, 2.4, 5.1, 5.45, M["strut"], ch=0.1)  # a capping strip
    for xc in (-4.0, 3.0):
        a = (xc, 0.0, 2.9)
        revolve(P, a, (0, 1, 0), [(0.0, 1.75), (0.4, 1.75), (0.4, 1.4), (2.0, 1.4), (2.0, 1.75), (2.7, 1.75)],
                const(M["pipe"]), n=14)
        # pipe bracket down to the floor
        box(P, xc - 1.0, xc + 1.0, 0.9, 1.6, FL, 2.2, M["dark"], ch=0.15)


def cage(P, M):
    """The bar frame, corner plates, interior bed and housing."""
    x0, x1, y0, y1 = -9.0, 8.0, 5.0, 17.0
    zb = ZT - BAR
    # top perimeter
    box(P, x0, x1, y0, y0 + 1.1, zb, ZT, M["rail"])                     # rear rail (row 5)
    box(P, x0, x1, y1 - 1.05, y1, zb, ZT, M["rail"])                     # front rail (row 16)
    box(P, x0, x0 + 1.05, y0, y1, zb, ZT, M["side"])                     # side rails (cols 3, 19)
    box(P, x1 - 1.05, x1, y0, y1, zb, ZT, M["side"])
    for xa, xb in ((x0, -3.0), (2.0, x1)):                               # bay bars (row 15)
        box(P, xa, xb, 15.0, 16.1, zb + 0.1, ZT - 0.05, M["rail"])
    for xa, xb in ((-5.0, -3.0), (2.0, 4.0)):                            # uprights (cols 7-8, 14-15)
        box(P, xa, xb, y0 + 0.2, y1 - 0.2, zb - 0.2, ZT + 0.25, M["upright"], ch=0.3)
    # posts down to the floor: corners and either side of the breech opening
    for xa, xb in ((x0, x0 + 1.05), (x1 - 1.05, x1)):
        for ya, yb in ((y0, y0 + 1.05), (y1 - 1.05, y1)):
            box(P, xa, xb, ya, yb, FL, ZT - 0.1, M["side"], ch=0.18)
    for xa, xb in ((-5.0, -3.0), (2.0, 4.0)):
        box(P, xa + 0.3, xb - 0.3, y1 - 1.0, y1 - 0.05, FL, zb, M["upright"], ch=0.18)
    # sills round the foot
    box(P, x0, x1, y1 - 1.0, y1, FL, 1.5, M["rail"], ch=0.2)
    box(P, x0, x0 + 1.0, y0, y1, FL, 1.5, M["side"], ch=0.2)
    box(P, x1 - 1.0, x1, y0, y1, FL, 1.5, M["side"], ch=0.2)
    # side frames: a mid rail under the lamps and a diagonal brace behind them
    for xa, xb in ((x0 - 0.05, x0 + 0.9), (x1 - 0.9, x1 + 0.05)):
        box(P, xa, xb, y0, y1, 1.5, 2.1, M["side"], ch=0.15)
    # corner plates (cols 4-6 / 16-18, rows 6-8): a base plate and an inset panel, the gap between
    # them a panel line; two bolts each
    for xa, xb in ((-8.0, -5.0), (4.0, 7.0)):
        box(P, xa - 0.05, xb + 0.05, 6.0, 9.1, zb - 0.3, ZT - 0.45, M["plate"], ch=0.1)
        box(P, xa + 0.35, xb - 0.35, 6.35, 8.75, ZT - 0.5, ZT - 0.3, M["plate"], ch=0.12)
        for xr in (xa + 0.75, xb - 0.75):
            box(P, xr - 0.22, xr + 0.22, 8.25, 8.65, ZT - 0.35, ZT - 0.17, M["rail"], ch=0.07)
    # interior bed (the dark floor of the windows), stopping short of row 14 in the side bays
    box(P, x0 + 0.6, x1 - 0.6, y0 + 0.5, 13.8, FL, 1.7, M["dark"], ch=0.15)
    box(P, -3.2, 2.2, 13.0, 16.5, FL, 1.5, M["dark"], ch=0.15)
    # bearing blocks on the bed holding the axle, and a bulkhead behind window A
    for xc in (-6.5, 5.5):
        box(P, xc - 0.8, xc + 0.8, 9.3, 11.7, 1.6, AXZ, M["dark"], ch=0.2)
    box(P, -3.0, 2.0, 6.0, 6.7, 1.6, ZT - 0.6, M["dark"], ch=0.15)
    # housing round the axle and the breech's root (cols 9-13, rows 9-11), a bolted hatch on top
    box(P, -3.0, 2.0, 9.0, 12.2, 1.6, ZT - 0.25, M["block"], ch=0.3)
    box(P, -2.4, 1.4, 9.5, 11.7, ZT - 0.3, ZT - 0.12, M["block"], ch=0.12)
    for xr in (-2.0, 1.0):
        for yr in (9.9, 11.3):
            box(P, xr - 0.2, xr + 0.2, yr - 0.2, yr + 0.2, ZT - 0.15, ZT + 0.02, M["rail"], ch=0.06)


def axle_and_lamps(P, M):
    yc = 10.5
    # axle across the cage, with bearing collars
    revolve(P, (-9.0, yc, AXZ), (1, 0, 0), [(0.0, 0.7), (17.0, 0.7)], const(M["axle"]), n=12)
    for xc in (-6.5, 5.5):
        revolve(P, (xc - 0.9, yc, AXZ), (1, 0, 0), [(0.0, 1.0), (0.15, 1.15), (1.65, 1.15), (1.8, 1.0)],
                const(M["axle"]), n=12)
    # lamps: domed lenses (y 3.5, z 2.3 semi-axes) in bezel rings on the axle ends
    dome = [(math.sin(math.radians(a)), math.cos(math.radians(a))) for a in (0, 20, 38, 55, 70, 82, 90)]
    for base, sgn, stub in ((-9.0, -1, 0.0), (8.0, 1, 1.0)):
        u = (sgn, 0, 0)
        if stub:
            # right side: the axle's collar across the 1 px gap (column 20)
            revolve(P, (base - 0.2 * sgn, yc, AXZ), u, [(0.0, 1.3), (stub + 0.2, 1.3)], const(M["collar_r"]), n=12)
        b0 = base + sgn * stub
        st = [(0.0, 1.07), (0.32, 1.07), (0.32, 0.97)] + [(0.32 + 1.68 * s, 0.97 * c) for s, c in dome[1:]]
        mats = [M["bezel"], M["bezel"]] + [M["lens"]] * (len(st) - 3)
        revolve(P, (b0, yc, AXZ), u, st, lambda i, s: mats[i], n=20, k1=3.35, k2=2.15)


def breech_and_yoke(P, M):
    a = (CX, 11.5, BZ)
    st = [(0.0, BR), (1.4, BR), (1.5, BR + 0.22), (2.0, BR + 0.22), (2.1, BR), (3.6, BR), (3.7, BR + 0.22),
          (4.2, BR + 0.22), (4.3, BR), (9.2, BR)]
    revolve(P, a, (0, 1, 0), st, const(M["breech"]), n=16)
    # yoke: a collar round the breech (row 17), a bridge and two cheeks (cols 6-8, 14-16)
    revolve(P, (CX, 16.85, BZ), (0, 1, 0), [(0.0, 2.35), (0.12, 2.6), (1.08, 2.6), (1.2, 2.35)],
            const(M["collar"]), n=16)
    box(P, -6.0, 5.0, 17.0, 18.05, 1.0, 4.6, M["yoke"], ch=0.25)
    for xa, xb in ((-6.0, -3.0), (2.0, 5.0)):
        box(P, xa, xb, 17.0, 20.1, FL, 4.4, M["yoke"], ch=0.35, chz=0.5)
        xm = (xa + xb) / 2
        box(P, xm - 0.25, xm + 0.25, 18.5, 19.4, 4.3, 4.55, M["rail"], ch=0.08)   # cheek pin
    # feet at the cage's front corners (row 17, cols 2-5 / 17-19)
    box(P, -10.0, -6.0, 16.6, 18.0, FL, 1.9, M["feet"], ch=0.25)
    box(P, 5.0, 8.0, 16.6, 18.0, FL, 1.9, M["feet"], ch=0.25)


def barrel(P, M):
    u = (0, math.cos(PITCH), math.sin(PITCH))
    a = (CX, 20.4, 3.85)
    st = [(0.0, 2.55), (0.2, 2.75), (0.85, 2.75), (0.85, 3.0), (1.3, 3.38), (4.6, 3.38), (4.67, 3.22), (4.9, 3.22),
          (4.97, 3.38), (5.45, 3.38), (5.9, 2.65), (5.9, 1.75), (5.4, 1.75), (5.4, 0.0)]
    # segments: 0-2 collar, 3-8 body (a panel groove at 5-7), 9 lip chamfer, 10 face annulus, 11 bore wall,
    # 12 bore floor
    def mat_of(i, s):
        if i <= 2:
            return M["collar"]
        if i <= 9:
            return M["barrel"]
        if i == 10:
            return M["lip_lo"] if s < -0.45 else M["lip_hi"]
        return M["bore"]
    revolve(P, a, u, st, mat_of, n=22, cap1=False)
    # the bore floor (the last ring closes it)
    return u, a, st


def floor(sprite, Mt):
    """Stone floor plate, 0..FL, its top painted per pixel in four grey tones (as lib_b073)."""
    pix = sprite["frames"][0]["pixels"]
    colors = sprite["colors"]
    tones = ((1, 3), (4, 6), (7, 9), (10, 15))
    slots = []
    for lo, hi in tones:
        have = [i for i in range(lo, hi + 1) if str(i) in colors]
        mid = (lo + hi) / 2
        slots.append(Mt(min(have, key=lambda i: abs(i - mid)), f"stone{lo}", metallic=0.05, roughness=0.85)
                     if have else None)

    def slot_of(i):
        for (lo, hi), s in zip(tones, slots):
            if lo <= i <= hi:
                return s
        return slots[1]

    P = T.Part(f"{NAME}_floor", smooth_angle=5)
    T.hull(P, [(x, y, z) for x in (-12.0, 12.0) for y in (0.0, 28.0) for z in (0.0, FL - 0.01)], slot_of(4))
    for r in range(28):
        c = 0
        while c < 24:
            s = slot_of(pix[r][c])
            e = c + 1
            while e < 24 and slot_of(pix[r][e]) == s:
                e += 1
            vs = [P.v((xx, yy, FL)) for xx, yy in ((c - 12, r), (e - 12, r), (e - 12, r + 1), (c - 12, r + 1))]
            P.f(vs, s, out=(0, 0, 1))
            c = e
    return P


def shell_proxy(coll):
    """A closed, simple stand-in for the machine, for the outline shell."""
    e = 0.15
    P = T.Part(f"{NAME}_proxy", smooth_angle=180)
    T.hull(P, T.cbox(-9.0 - e, 8.0 + e, 4.9, 17.0 + e, FL + 0.3, ZT + 0.2, 0.3), 0)
    hz = [(x, y, z) for x, y in rrect(-8.0 - e, 7.0 + e, 2.0 - e, 5.2, 2.2, 0.25) for z in (FL + 0.3, 3.6)]
    hz += [(x, y, HOODZ + 0.1) for x, y in rrect(-6.1, 5.1, 3.2, 5.2, 1.0, 0.25)]
    T.hull(P, hz, 0)
    T.hull(P, T.cbox(-6.0, 5.0, 0.0, 2.7, FL + 0.3, 5.4, 0.3), 0)
    for base, sgn in ((-9.0, -1), (8.0, 1)):
        pts = []
        reach = 2.0 + (1.0 if sgn > 0 else 0.0)
        for k in range(16):
            q = 2 * math.pi * k / 16
            for s in (0.0, 0.5, 0.8, 1.0):
                r = math.sqrt(max(0.0, 1 - s * s)) * 1.05
                pts.append((base + sgn * (0.3 + s * (reach - 0.3) + e), 10.5 + 3.4 * r * math.cos(q),
                            AXZ + 2.2 * r * math.sin(q)))
        T.hull(P, pts, 0)
    T.hull(P, T.cbox(-6.0 - e, 5.0 + e, 16.8, 20.2, FL + 0.3, 4.7, 0.3), 0)
    T.hull(P, T.cbox(-10.0 - e, 8.0 + e, 16.5, 18.1, FL + 0.3, 2.0, 0.3), 0)
    u, e1, e2 = basis((0, math.cos(PITCH), math.sin(PITCH)))
    a = Vector((CX, 20.4, 3.85))
    pts = []
    for t, r in ((0.0, 2.75), (0.85, 2.75), (1.3, 3.38), (5.45, 3.38), (5.9, 2.65)):  # the barrel's stations
        for k in range(16):
            q = 2 * math.pi * k / 16
            pts.append(tuple(a + u * t + (e1 * math.cos(q) + e2 * math.sin(q)) * (r + e)))
    T.hull(P, pts, 0)
    return T.finish(P, [], coll)


def build():
    sprite = common.load_sprite(WT, NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    Mt = Mats(sprite)
    paint = dict(metallic=0.45, roughness=0.42)
    steel = dict(metallic=0.75, roughness=0.32)
    M = {
        "hood": Mt(168, "hood", **paint),
        "rail": Mt(165, "rail", **paint),
        "side": Mt(168, "side", **paint),
        "upright": Mt(167, "upright", **paint),
        "plate": Mt(163, "plate", **paint),
        "block": Mt(164, "block", **paint),
        "strut": Mt(170, "strut", **paint),
        "yoke": Mt(164, "yoke", **paint),
        "collar": Mt(168, "collar", **paint),
        "barrel": Mt(167, "barrel", metallic=0.35, roughness=0.5),
        "pipe": Mt(100, "pipe", **steel),
        "axle": Mt(106, "axle", **steel),
        "breech": Mt(104, "breech", **steel),
        "dark": Mt(99, "dark", metallic=0.6, roughness=0.5),
        "feet": Mt(99, "feet", metallic=0.6, roughness=0.5),
        "bezel": Mt(100, "bezel", **steel),
        "collar_r": Mt(2, "collar_r", frames={277: 5, 279: 6}, metallic=0.6, roughness=0.45),
        "lens": Mt(115, "lens", frames={277: 116, 279: 119}, metallic=0.0, roughness=0.15, emission=1.5),
        "bore": Mt(114, "bore", frames={277: 118, 279: 122}, metallic=0.0, roughness=0.95, emission=2.5),
        "lip_hi": Mt(167, "lip_hi", frames={279: 117}, metallic=0.3, roughness=0.6),
        "lip_lo": Mt(167, "lip_lo", frames={277: 116, 279: 117}, metallic=0.3, roughness=0.6),
    }
    P = T.Part(NAME, smooth_angle=32)
    hood(P, M)
    mount(P, M)
    cage(P, M)
    axle_and_lamps(P, M)
    breech_and_yoke(P, M)
    barrel(P, M)
    FP = floor(sprite, Mt)
    obj = T.finish(P, Mt.list, coll)
    fl = T.finish(FP, Mt.list, coll)
    fl.data.shade_flat()
    fl["tyrian_ground"] = True
    proxy = shell_proxy(coll)
    shell = common.outline_shell(proxy, coll, faces=2500)
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(proxy, do_unlink=True)
    return sprite, [obj, fl, shell]


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite, objs = build()
    objs = [o for o in objs if not o.get("tyrian_ground")]  # the floor plate stays out (D129)
    if "--out" in argv:  # a scratch export for measuring, not the game's files
        common.export_glb(objs, Path(argv[argv.index("--out") + 1]))
    else:
        common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"])
    tris = []
    for o in objs:
        o.data.calc_loop_triangles()
        tris.append(len(o.data.loop_triangles))
    print(f"built {NAME}: {tris[0]} triangles machine, shell {tris[1]}")
