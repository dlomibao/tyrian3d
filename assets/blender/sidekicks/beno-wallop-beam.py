"""Beno Wallop Beam (sidekicks 27 Beno Wallop Beam and 28 Beno Protron System -B-, tyrian.shp#9
frame 43, 2x2 = 24x28, one frame), design A: the blueprint's geometry built cross-section first, to
the player-ship hard-surface standard (DECISIONS D50-D53, D65; outline fitted to the sprite's INNER
mask, D74).

What it is: a front-mounted beam turret (style 2, floats ahead of the ship the whole level). A BALL
POD of satin lilac metal split, the way a real turret ball is built, into an upper shell and a
slightly smaller lower shell (a crisp step at the equator), and fore/aft by a raised BELT flange at
row 17. A through CHANNEL (columns 8-16, the sprite's 1 px background gaps either side of the barrel)
splits the front of the pod into two CHEEKS whose inner walls funnel at 45 degrees (rows 12-13) into
a 5 px BREECH SLOT with a dark floor block. The BARREL (turned steel) lies in the channel on a recoil
CRADLE web, its axis above the cheeks: collars at rows 2-3 and 5, grooves at 4, 6 and 10, a long body,
a rounded shoulder at row 11 and a narrow BREECH running back down the slot into the belt. The muzzle
is a beam EMITTER: a glowing ring (row 1), a dark-red lip (row 0) and a hot yellow lens. Two HATCH
panels (rows 14-16) flank the slot; a REAR HOUSING (two plates with a real gap at row 22) runs down
the back to a dark exhaust NOZZLE; a dark mounting HUB under the flat belly.

Cross-sections (the engineering read; sprite px, x = column edge - 12, y = row edge, z up):
- pod plan: superellipse about (12.5, 15.5), A 9.5, B 9.4, p 2.2 (fitted to the inner mask, see
  fit_plan.py); upper shell z = H sqrt(1 - |dx/A|^p - |dr/B|^p), H 7.0, down to z -0.3; lower shell
  the same plan x0.94, depth 6.4, cut flat at z -4.6.
- every shell piece is a loft of those sections along the rows (cheeks: the section beyond the
  channel wall, with a 0.35 px chamfer on the inner top edge; the wall half width is 4.5 to row 11.8,
  45 degrees down to 2.5 at row 13.8, 2.5 to the belt).
- barrel: revolved profile about (12.5, z 5.4).

Authoring space as microsol-frontblaster/A: finish() maps x/12, (14 - y)/12, z/12 into Blender, the
same origin as assets/blender/sidekicks/beno-wallop-beam.py.

Finish (step 4): cheek louvres in the hatch recesses and a ribbed rear hatch strap; the slot is a
recess (dark floor, lilac front wall) rather than a flat black slab. Exports through
common.export_sprite_model (D49 "ungrouped" kept), AO/roughness bake only (D65), outline shell (D51).

Run: blender --background --factory-startup --python assets/blender/sidekicks/beno-wallop-beam.py [-- --nobake] [--renders DIR]
"""
import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part  # noqa: E402

NAME = "sidekick-beno-wallop-beam"   # object name, reference folder and sprite name
MODEL = "sidekicks/beno-wallop-beam"
ROOT = common.repo_root(__file__)
PX = 1 / 12
FRAMES = [43]

AXC = 12.5                     # mirror axis, column edge
CX = AXC - 12.0                # its x
A, B, RC, PE = 9.5, 9.4, 15.5, 2.2   # pod plan superellipse (inner mask fit)
H = 7.0                        # upper shell crown height
ZS = -0.3                      # upper shell bottom (the equator step)
KL, HL, ZLT, FLOOR = 0.94, 6.4, -0.25, -4.6   # lower shell: plan scale, depth, top, flat belly
CHF = 0.35                     # chamfer on the cheeks' inner top edges
BZ = 5.4                       # barrel axis height
R_BELT0, R_BELT1, BELT_H = 17.0, 18.0, 0.32
SLOT_FLOOR_R = 14.75

(POD, LOWER, BELT, HATCH, HOUSING, BARREL, GROOVE, BREECH, GLOW, LIP, LENS, SLOT, CRADLE, NOZZLE,
 HUB, RIB) = range(16)


def materials(sprite):
    def metal(i, tag, rough=0.42, met=0.5):
        return common.palette_material(sprite, i, f"bwb_{tag}", metallic=met, roughness=rough)

    def glow(i, tag, e, rough=0.25):
        return common.palette_material(sprite, i, f"bwb_{tag}", metallic=0.0, roughness=rough, emission_strength=e)
    # Palette index per part = the trimmed median of the sprite pixels it covers (blueprint regions).
    return [
        metal(87, "pod", rough=0.42, met=0.35),  # pod shells (median 87): satin paint
        metal(87, "lower", rough=0.5, met=0.35),          # lower shell (unseen from the top; same paint)
        metal(89, "belt", rough=0.38, met=0.4),          # belt flange (row 17 median 89)
        metal(84, "hatch", rough=0.48),         # hatch panels (median 84)
        metal(90, "housing", rough=0.4, met=0.35),        # rear housing top (median 90; its sides are light)
        metal(7, "barrel", rough=0.34, met=0.3),   # turned steel barrel (trimmed median 7): satin
        metal(5, "groove", rough=0.45, met=0.4),   # machined grooves
        metal(8, "breech", rough=0.38, met=0.3),    # breech (trimmed median 8)
        glow(122, "glow", 1.0),                 # emitter ring (row 1 trimmed median 122)
        metal(113, "lip", rough=0.45, met=0.4),     # dark-red muzzle lip (row 0, 113)
        glow(125, "lens", 1.0, rough=0.1),      # hot yellow lens core (125)
        common.palette_material(sprite, 1, "bwb_slot", metallic=0.1, roughness=0.8),   # slot floor (1)
        metal(4, "cradle", rough=0.5, met=0.45),
        metal(3, "nozzle", rough=0.5, met=0.45),
        metal(4, "hub", rough=0.55, met=0.4),
        metal(89, "rib", rough=0.4, met=0.4),      # rear hatch strap and ribs (belt colour)
    ]


# --- the pod's sections ----------------------------------------------------------------------

def s_of(r, b=B):
    return max(0.0, 1.0 - abs((r - RC) / b) ** PE)


def w_of(r, a=A, b=B):
    return a * s_of(r, b) ** (1 / PE)


def zt(dx, r):
    """Upper shell height at (dx from the axis, row)."""
    return H * math.sqrt(max(0.0, s_of(r) - abs(dx / A) ** PE))


def zl(dx, r):
    """Lower shell surface (negative), cut flat at FLOOR."""
    al, bl = A * KL, B * KL
    return max(FLOOR, -HL * math.sqrt(max(0.0, s_of(r, bl) - abs(dx / al) ** PE)))


def ch_of(r):
    """Half width of the channel / funnel / slot cut at row r."""
    if r <= 11.8:
        return 4.5
    if r >= 13.8:
        return 2.5
    return 4.5 - 2.0 * (r - 11.8) / 2.0


def offset_pts(pts, o, closed=True):
    """Move each 2D point (dx, z) of a convex CCW-or-CW loop outward by o along its vertex normal."""
    if o == 0:
        return list(pts)
    n = len(pts)
    cx = sum(p[0] for p in pts) / n
    cz = sum(p[1] for p in pts) / n
    out = []
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        tx, tz = c[0] - a[0], c[1] - a[1]
        ln = math.hypot(tx, tz) or 1e-9
        nx, nz = tz / ln, -tx / ln
        if nx * (b[0] - cx) + nz * (b[1] - cz) < 0:
            nx, nz = -nx, -nz
        out.append((b[0] + nx * o, b[1] + nz * o))
    return out


NARC = 22


def sec_full_upper(r, o=0.0):
    w = max(w_of(r), 0.02)
    sq = math.sqrt(s_of(r))
    pts = [(w, ZS)]
    for i in range(NARC + 1):
        ph = math.pi * i / NARC
        c = math.cos(ph)
        pts.append((w * c, H * sq * math.sqrt(max(0.0, 1 - abs(c) ** PE))))
    pts.append((-w, ZS))
    return offset_pts(pts, o)


NLOW = 12


def sec_full_lower(r):
    al = A * KL
    w = max(w_of(r, al, B * KL), 0.02)
    pts = [(-w, ZLT)]
    for i in range(NLOW + 1):
        ph = math.pi + math.pi * i / NLOW
        c = math.cos(ph)
        pts.append((w * c, zl(w * c, r)))
    pts.append((w, ZLT))
    return pts


NCH = 12


def sec_cheek_upper(r, sg):
    """Right cheek (sg +1) or left (-1): wall at ch_of(r), chamfered top edge, arc out to the rim."""
    d0 = ch_of(r)
    w = w_of(r)
    d1 = min(d0 + CHF, w - 0.01)
    ph0 = math.acos(max(-1.0, min(1.0, d1 / w)))
    zc = max(ZS + 0.02, zt(d1, r) - CHF)
    pts = [(d0, zc)]
    sq = math.sqrt(s_of(r))
    for i in range(NCH + 1):
        ph = ph0 * (1 - i / NCH)
        c = math.cos(ph)
        pts.append((w * c, H * sq * math.sqrt(max(0.0, 1 - abs(c) ** PE))))
    pts += [(w, ZS), (d0, ZS)]
    return [(sg * x, z) for x, z in pts]


NCHL = 7


def sec_cheek_lower(r, sg):
    d0 = ch_of(r)
    al = A * KL
    w = max(w_of(r, al, B * KL), d0 + 0.02)
    pts = [(d0, ZLT), (w, ZLT)]
    for i in range(NCHL + 1):
        x = w - (w - d0) * (i / NCHL) ** 0.7
        pts.append((x, zl(x, r)))
    return [(sg * x, z) for x, z in pts]


def loft_sections(part, secs, mat, cap0=True, cap1=True):
    """secs: [(r, [(dx, z), ...])] all with the same count. Faces hint away from each section's centre."""
    rings = []
    cents = []
    for r, pts in secs:
        rings.append([part.v((CX + x, r, z)) for x, z in pts])
        n = len(pts)
        cents.append((CX + sum(p[0] for p in pts) / n, r, sum(p[1] for p in pts) / n))
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        n = len(a)
        cc = Vector(cents[k]).lerp(Vector(cents[k + 1]), 0.5)
        for i in range(n):
            j = (i + 1) % n
            part.f((a[i], a[j], b[j], b[i]), mat, away=tuple(cc))
    if cap0:
        part.f(list(reversed(rings[0])), mat, out=(0, -1, 0))
    if cap1:
        part.f(rings[-1], mat, out=(0, 1, 0))


def r_front_where(wtarget, a=A, b=B):
    """Row in front of the centre where the plan half width is wtarget."""
    s = (wtarget / a) ** PE
    return RC - b * (1 - s) ** (1 / PE)


def front_rows(r0, r1, n):
    """n+1 rows from r0 to r1, denser at r0 (the tip)."""
    return [r0 + (r1 - r0) * (i / n) ** 1.8 for i in range(n + 1)]


def build_shells(P):
    # cheeks, upper: from the tip (plan width = wall + chamfer) to the belt
    for sg in (-1, 1):
        r_tip = r_front_where(4.5 + CHF + 0.12)
        rows = front_rows(r_tip, 11.8, 9) + [12.3, 12.8, 13.3, 13.8, 14.6, 15.4, 16.2, R_BELT0 + 0.02]
        loft_sections(P, [(r, sec_cheek_upper(r, sg)) for r in rows], POD)
        rl_tip = r_front_where(4.5 + 0.1, A * KL, B * KL)
        rows = front_rows(rl_tip, 11.8, 5) + [12.8, 13.8, 15.4, R_BELT0 + 0.02]
        loft_sections(P, [(r, sec_cheek_lower(r, sg)) for r in rows], LOWER)
    # belt: the full section offset outward (chamfered 45 degrees each side)
    loft_sections(P, [(R_BELT0 - 0.05, sec_full_upper(R_BELT0 - 0.05, 0.0)),
                      (R_BELT0 + 0.12, sec_full_upper(R_BELT0 + 0.12, BELT_H)),
                      (R_BELT1 - 0.12, sec_full_upper(R_BELT1 - 0.12, BELT_H)),
                      (R_BELT1 + 0.05, sec_full_upper(R_BELT1 + 0.05, 0.0))], BELT)
    # rear shell, upper: belt to the rear tip, rows spaced evenly in the plan angle
    rows = []
    psi0 = math.asin(min(1.0, ((R_BELT1 - RC) / B) ** (PE / 2)))
    for i in range(13):
        psi = psi0 + (math.pi / 2 - 0.06 - psi0) * i / 12
        rows.append(RC + B * math.sin(psi) ** (2 / PE))
    rows[0] = R_BELT1 - 0.02
    secs = [(r, sec_full_upper(r)) for r in rows]
    loft_sections(P, secs, POD, cap1=False)
    tip = P.v((CX, RC + B - 0.01, 0.0))
    last = secs[-1]
    # fan the last ring to the tip point
    n = len(last[1])
    vr = [P.v((CX + x, last[0], z)) for x, z in last[1]]
    for i in range(n):
        P.f((vr[i], vr[(i + 1) % n], tip), POD, out=(0, 1, 0.2))
    # rear shell, lower
    rows = []
    bl = B * KL
    psi0 = math.asin(min(1.0, ((R_BELT0 - RC) / bl) ** (PE / 2)))
    for i in range(9):
        psi = psi0 + (math.pi / 2 - 0.08 - psi0) * i / 8
        rows.append(RC + bl * math.sin(psi) ** (2 / PE))
    rows[0] = R_BELT0 - 0.02
    loft_sections(P, [(r, sec_full_lower(r)) for r in rows], LOWER)


def conformal_patch(P, x0, x1, r0, r1, dz, mat, ch=0.12, nx=6, ny=5):
    """A panel lying on the upper shell: top dz above it with a chamfered rim, sides sunk into it."""
    def top(x, r, inset):
        return zt(x - CX, r) + dz - (ch if inset else 0.0)
    xs = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
    rs = [r0 + (r1 - r0) * j / ny for j in range(ny + 1)]
    # inner (top face) grid inset by ch
    xi = [x0 + ch + (x1 - x0 - 2 * ch) * i / nx for i in range(nx + 1)]
    ri = [r0 + ch + (r1 - r0 - 2 * ch) * j / ny for j in range(ny + 1)]
    g = [[P.v((xi[i], ri[j], zt(xi[i] - CX, ri[j]) + dz)) for j in range(ny + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(ny):
            P.f((g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]), mat, out=(0, 0, 1))
    # rim loop (outer edge at surface + dz - ch) and its sunk base
    loop_in = [g[i][0] for i in range(nx + 1)] + [g[nx][j] for j in range(1, ny + 1)] + \
        [g[i][ny] for i in range(nx - 1, -1, -1)] + [g[0][j] for j in range(ny - 1, 0, -1)]
    pts = [(xs[i], rs[0]) for i in range(nx + 1)] + [(xs[nx], rs[j]) for j in range(1, ny + 1)] + \
        [(xs[i], rs[ny]) for i in range(nx - 1, -1, -1)] + [(xs[0], rs[j]) for j in range(ny - 1, 0, -1)]
    rim = [P.v((x, r, zt(x - CX, r) + dz - ch)) for x, r in pts]
    base = [P.v((x, r, zt(x - CX, r) - 0.3)) for x, r in pts]
    cx, cr = (x0 + x1) / 2, (r0 + r1) / 2
    n = len(pts)
    for k in range(n):
        m = (k + 1) % n
        P.f((loop_in[k], loop_in[m], rim[m], rim[k]), mat, away=(cx, cr, zt(cx - CX, cr) - 3))
        P.f((rim[k], rim[m], base[m], base[k]), mat, away=(cx, cr, zt(cx - CX, cr) - 3))


def build_hatches(P):
    for sg in (-1, 1):
        a, b = 3.15, 6.55
        x0, x1 = (CX - b, CX - a) if sg < 0 else (CX + a, CX + b)
        conformal_patch(P, x0, x1, 14.15, 16.7, 0.1, HATCH)
        # louvres: two raised slats across each hatch recess (the sprite's striped cheeks)
        for r0 in (14.62, 15.62):
            conformal_patch(P, x0 + 0.3, x1 - 0.3, r0, r0 + 0.5, 0.3, HATCH, ch=0.08, nx=2, ny=1)


def build_slot(P):
    # the slot: a dark floor recess between the lower cheeks' walls, closed in front by a low lilac wall
    T_box(P, CX - 2.52, CX + 2.52, SLOT_FLOOR_R, R_BELT0 + 0.1, FLOOR + 0.05, FLOOR + 0.5, SLOT, ch=0.1)
    T_box(P, CX - 2.52, CX + 2.52, SLOT_FLOOR_R - 0.3, SLOT_FLOOR_R, FLOOR, 0.0, LOWER, ch=0.1)
    # recoil cradle web under the barrel (hidden from the top by the barrel)
    T_box(P, CX - 1.3, CX + 1.3, 7.6, SLOT_FLOOR_R + 0.05, -0.6, BZ - 3.1, CRADLE, ch=0.3)


def T_box(P, x0, x1, r0, r1, z0, z1, mat, ch=0.0):
    pts = [(x0, r0), (x1, r0), (x1, r1), (x0, r1)]
    prism(P, pts, z0, z1, mat, ch=ch)


def _ccw(pts):
    a = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return pts if a > 0 else list(reversed(pts))


def inset(pts, d):
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e0 = (p1[0] - p0[0], p1[1] - p0[1])
        e1 = (p2[0] - p1[0], p2[1] - p1[1])
        l0 = math.hypot(*e0) or 1
        l1 = math.hypot(*e1) or 1
        n0 = (-e0[1] / l0, e0[0] / l0)
        n1 = (-e1[1] / l1, e1[0] / l1)
        m = (n0[0] + n1[0], n0[1] + n1[1])
        ml = math.hypot(*m) or 1
        m = (m[0] / ml, m[1] / ml)
        cos = max(0.4, m[0] * n0[0] + m[1] * n0[1])
        out.append((p1[0] + m[0] * d / cos, p1[1] + m[1] * d / cos))
    return out


def prism(part, poly, z0, z1, mat, ch=0.0, ztop=None):
    """A plate: outline poly (x, r) from z0 up to z1 (or ztop(x, r)), top edge chamfered by ch."""
    pts = _ccw(list(poly))
    zt_ = (lambda x, y: z1) if ztop is None else ztop
    rings = [[(x, y, z0) for x, y in pts]]
    if ch:
        rings.append([(x, y, zt_(x, y) - ch) for x, y in pts])
        rings.append([(x, y, zt_(x, y)) for x, y in inset(pts, ch)])
    else:
        rings.append([(x, y, zt_(x, y)) for x, y in pts])
    vr = [[part.v(co) for co in ring] for ring in rings]
    n = len(pts)
    for k in range(len(vr) - 1):
        a, b = vr[k], vr[k + 1]
        zk = 1.0 if (ch and k == len(vr) - 2) else 0.0
        for i in range(n):
            j = (i + 1) % n
            ex, ey = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
            ln = math.hypot(ex, ey) or 1
            part.f((a[i], a[j], b[j], b[i]), mat, out=(ey / ln, -ex / ln, zk))
    part.f(list(reversed(vr[0])), mat, out=(0, 0, -1))
    part.f(vr[-1], mat, out=(0, 0, 1))


def revolve(part, prof, mats, n=20, zc=BZ, phase=0.0):
    """A solid of revolution about the barrel axis (x = CX, z = zc) along the rows. prof [(r, radius)]
    from axis to axis; mats[k] colours segment k (an int colours all)."""
    def ring(y, rad):
        if rad <= 1e-6:
            return [part.v((CX, y, zc))]
        return [part.v((CX + rad * math.cos(phase + 2 * math.pi * i / n), y,
                        zc + rad * math.sin(phase + 2 * math.pi * i / n))) for i in range(n)]
    rings = [ring(y, r) for y, r in prof]
    for k in range(len(prof) - 1):
        (y0, r0), (y1, r1) = prof[k], prof[k + 1]
        m = mats if isinstance(mats, int) else mats[k]
        ny, nr = -(r1 - r0), (y1 - y0)
        if abs(nr) < 1e-9 and abs(ny) < 1e-9:
            continue
        a, b = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            ang = phase + 2 * math.pi * (i + 0.5) / n
            out = (nr * math.cos(ang), ny, nr * math.sin(ang))
            if len(a) == 1:
                part.f((a[0], b[j], b[i]), m, out=out)
            elif len(b) == 1:
                part.f((a[i], a[j], b[0]), m, out=out)
            else:
                part.f((a[i], a[j], b[j], b[i]), m, out=out)


def build_barrel(P):
    B_, G_ = BARREL, GROOVE
    prof = [(1.95, 0.0), (1.95, 3.2), (2.15, 3.5), (3.85, 3.5), (4.05, 3.1), (4.95, 3.1), (5.15, 3.5),
            (5.85, 3.5), (6.05, 3.1), (6.95, 3.1), (7.1, 3.4), (9.9, 3.4), (10.05, 3.1), (10.85, 3.1),
            (11.0, 3.4), (11.6, 3.4), (12.0, 2.65), (12.35, 1.85), (12.5, 1.6), (17.4, 1.6), (17.4, 0.0)]
    mats = [B_, B_, B_, G_, G_, G_, B_, G_, G_, G_, B_, G_, G_, G_, B_, B_, B_, BREECH, BREECH, BREECH]
    revolve(P, prof, mats, n=20)
    # breech band (machined collar where the breech enters the slot)
    revolve(P, [(15.55, 0.0), (15.55, 1.62), (15.65, 1.78), (15.95, 1.78), (16.05, 1.62), (16.05, 0.0)], BREECH, n=16)
    # emitter: glowing ring, dark-red lip, hot lens
    revolve(P, [(1.0, 0.0), (1.0, 2.7), (1.12, 2.88), (1.85, 2.88), (2.0, 2.7), (2.0, 0.0)], GLOW, n=20)
    revolve(P, [(0.8, 0.0), (0.8, 1.55), (0.58, 1.75), (0.58, 2.42), (0.72, 2.62), (1.05, 2.62), (1.05, 0.0)],
            LIP, n=20)
    revolve(P, [(0.56, 0.0), (0.6, 1.0), (0.7, 1.45), (0.85, 1.6), (0.85, 0.0)], LENS, n=16)


def build_housing(P):
    def top(x, r):
        return zt(0.0, min(r, 24.3)) + 1.05
    hw = 2.5
    front = [(CX - hw, 19.85), (CX + hw, 19.85), (CX + hw, 22.25), (CX - hw, 22.25)]
    rear = [(CX - hw, 22.5), (CX + hw, 22.5), (CX + hw, 24.45), (CX + hw - 0.6, 25.0), (CX - hw + 0.6, 25.0),
            (CX - hw, 24.45)]
    prism(P, front, -0.2, None, HOUSING, ch=0.55, ztop=top)
    prism(P, rear, -0.2, None, HOUSING, ch=0.55, ztop=top)
    # rear hatch: a raised centre strap on the rear plate and two ribs across the front plate
    prism(P, [(CX - 0.55, 22.9), (CX + 0.55, 22.9), (CX + 0.55, 24.2), (CX - 0.55, 24.2)], -0.2, None, RIB,
          ch=0.1, ztop=lambda x, r: top(x, r) + 0.25)
    for r0 in (20.5, 21.5):
        prism(P, [(CX - 1.9, r0), (CX + 1.9, r0), (CX + 1.9, r0 + 0.35), (CX - 1.9, r0 + 0.35)], -0.2, None, RIB,
              ch=0.08, ztop=lambda x, r: top(x, r) + 0.2)
    # exhaust nozzle at its end, and its dark throat
    nz = 1.9
    revolve(P, [(24.6, 0.0), (24.6, 1.15), (25.35, 1.15), (25.42, 0.95), (25.42, 0.0)], NOZZLE, n=14, zc=nz)
    revolve(P, [(25.3, 0.0), (25.3, 0.72), (25.45, 0.72), (25.45, 0.0)], SLOT, n=12, zc=nz)


def build_hub(P):
    n = 14
    pts = [(CX + 3.6 * math.cos(2 * math.pi * i / n), 18.2 + 3.0 * math.sin(2 * math.pi * i / n)) for i in range(n)]
    prism(P, pts, FLOOR - 1.1, FLOOR + 0.05, HUB, ch=0.0)


def build(sprite, coll):
    mats = materials(sprite)
    P = Part(NAME, smooth_angle=34.0)
    build_shells(P)
    build_hatches(P)
    build_slot(P)
    build_barrel(P)
    build_housing(P)
    build_hub(P)
    return finish(P, mats, coll), mats


def finish(part, mats, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj




# --- bake (copied from sidekicks-2/microsol-frontblaster/A: AO/roughness only, glowing parts left flat) --

def bake_maps(obj, out_dir, tag, size=1024, samples=64):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(30), island_margin=0.006, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list({m.name: m for m in me.materials}.values())
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, bb=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, bb)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.02
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.09
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            nt.links.new(v, em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    for m in mats:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        if bsdf.inputs["Emission Strength"].default_value > 0:
            continue
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


# --- renders -----------------------------------------------------------------------------------

def camera(scene, name, location, look_at, ortho=None, lens=50, up="Y"):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = location
    direction = Vector(look_at) - Vector(location)
    cam.rotation_euler = direction.to_track_quat("-Z", up).to_euler()
    return cam


def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = [e for e in str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split()
                 if e.isupper()]
        key = "WORKBENCH" if "WORKBENCH" in want else "EEVEE"
        scene.render.engine = next(e for e in names if key in e)


def flat_colours(objs):
    """Workbench flat colours = each material's palette colour (for the top mask and colour check)."""
    for o in objs:
        for m in o.data.materials:
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            mix = next((n for n in m.node_tree.nodes if n.type == "MIX" and n.blend_type == "MULTIPLY"), None)
            base = tuple(mix.inputs[7].default_value)[:3] if mix else tuple(bsdf.inputs["Base Color"].default_value)[:3]
            m.diffuse_color = (*base, 1.0)


def render_tops(scene, objs, out):
    set_engine(scene, "BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 24 * 16, 28 * 16
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    cam = camera(scene, "bwb_top", (0, 0, 5), (0, 0, 0), ortho=28 / 12)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    flat_colours(objs)
    for f in FRAMES:
        scene.render.filepath = str(out / f"top_{f}.png")
        bpy.ops.render.render(write_still=True)


def render_views(scene, objs, out):
    set_engine(scene, "BLENDER_EEVEE")
    scene.render.film_transparent = False
    try:
        scene.view_settings.view_transform = "Khronos PBR Neutral"
    except TypeError:
        scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.09, 0.095, 0.11, 1)
    bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.new("bwb_sun", bpy.data.lights.new("bwb_sun", "SUN"))
    sun.data.energy = 4.5
    sun.rotation_euler = (Vector((0.45, -0.5, -1.0))).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("bwb_fill", bpy.data.lights.new("bwb_fill", "SUN"))
    fill.data.energy = 1.3
    fill.rotation_euler = (Vector((-0.6, 0.6, -0.3))).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill)
    scene.render.resolution_x = scene.render.resolution_y = 420
    D = 4.0
    ext = 2.0
    t15, t32 = math.radians(15), math.radians(32)
    views = {
        "top": camera(scene, "v_top", (0, 0, D), (0, 0, 0), ortho=ext),
        "side": camera(scene, "v_side", (D, 0, 0.1), (0, 0, 0.1), ortho=ext, up="Y"),
        "sidew": camera(scene, "v_sidew", (-D, 0, 0.1), (0, 0, 0.1), ortho=ext, up="Y"),
        "front": camera(scene, "v_front", (0, D, 0.1), (0, 0, 0.1), ortho=ext * 0.85, up="Y"),
        "rear": camera(scene, "v_rear", (0, -D, 0.1), (0, 0, 0.1), ortho=ext * 0.85, up="Y"),
        "q34": camera(scene, "v_q34", (2.4, 2.4, 2.4), (0, 0, 0), lens=60, up="Y"),
        "q34r": camera(scene, "v_q34r", (-2.4, -2.6, 2.1), (0, 0, 0), lens=60, up="Y"),
        "game15": camera(scene, "v_game15", (0, -6 * math.sin(t15), 6 * math.cos(t15)), (0, 0, 0), lens=55),
        "game32": camera(scene, "v_game32", (0, -6 * math.sin(t32), 6 * math.cos(t32)), (0, 0, 0), lens=55),
        "under": camera(scene, "v_under", (0, 0, -D), (0, 0, 0), ortho=ext),
    }
    views["top"].rotation_euler = (0, 0, 0)
    views["under"].rotation_euler = (math.pi, 0, 0)
    for k, cam in views.items():
        scene.camera = cam
        scene.render.filepath = str(out / f"view_{k}.png")
        bpy.ops.render.render(write_still=True)




def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bake = "--nobake" not in argv
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    coll = common.reset_collection(NAME)
    sprite = common.load_sprite(ROOT, NAME)
    body, mats = build(sprite, coll)
    shell = common.outline_shell(body, coll, voxel=0.01, faces=1200, smooth=6, inside=0.004)
    shell.name = f"{NAME}-outline"
    T.cull_hidden(body)
    if bake:
        shell.hide_render = True
        bake_maps(body, tempfile.mkdtemp(prefix="bwb_bake_"), "beno_wallop_beam")
        shell.hide_render = False
    objs = [body, shell]
    for o in objs:
        o.data.calc_loop_triangles()
        print("triangles", o.name, len(o.data.loop_triangles))
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"], image_format="WEBP" if bake else "AUTO")
    if "--renders" in argv:
        out = Path(argv[argv.index("--renders") + 1])
        out.mkdir(parents=True, exist_ok=True)
        shell.hide_render = True
        render_views(scene, [body], out)
        render_tops(scene, [body], out)


if __name__ == "__main__":
    main()
