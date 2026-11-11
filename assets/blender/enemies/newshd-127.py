"""newshd-127: the grey lamp pod of the stone fortress (newshd.shp frames 127, 129, 131).

The sprite fills its 24 x 28 tile: a stone-brick floor and on it a wide oval grey pod, a pale
plate (the spine) running down its middle with two red lamps set in it. The lamps brighten from
dark red (127) through orange (129) to yellow (131); nothing else changes, so one model covers all
three frames, the lamps' colour following the frame (palette_material frames=, D17).

Reading of the sprite (tools/calibration/rubric.md): the bright upper-left rim and dark lower-right
edge of the pod and the black band under it are lighting; the four short bright streaks on the
lobes (rows 8-10 and 17-18) are sheen on the lips of two panel lines that cross each lobe at rows
11 and 16 (dark there), not ribs.

Hard surface (D50-D53, D65): a fitted base flange with bolts; the dome as separate armour panels
over a dark core, so the panel lines are real grooves with chamfered lips; the spine a lofted plate
with chamfered edges and end caps; each lamp a domed lens in a bezel ring, a railed conduit
between them. No floor plate (D130): the sprite's stone-brick floor round the pod is the tile's
ground, which the game draws in HD; the model is the pod alone (it was a plate painted per pixel
from the sprite, which showed as grey pixel cells on the HD ground).

Colours (median of each region's pixels, darkest/brightest sixth left out, all three frames):
dome 7, spine 10 (9.5-10; sides 9), lamp rim 112 -> 115 -> 118, lamp core 116 -> 121 -> 123,
lamp bezel 7, panel lines 4.

Seen in episodes 1-3 in a row of six along the top of the fortress set; flies as an air unit.

Run: blender --background --python assets/blender/enemies/newshd-127.py
Exports public/models/enemies/newshd-127.glb and src/render/spriteModels/newshd-127.json.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshd-127"
PX = 1 / 12

# --- plan and heights, sprite px (x right from the tile's centre, y down from its top, z up) ----
CY = 13.5             # pod centre row (edge coordinates): rows 4.5-22.5
RX, RY = 10.0, 8.0    # the dome's base ellipse, inside the flange
FX, FY = 11.0, 9.0    # flange top outer edge
BX, BY = 11.4, 9.4    # flange foot on the floor
FLOOR = 0.36          # foot height: the old floor plate's top (0.03 units, lib_b073's FLOOR), so the fortress tiles' heights still meet
Z0 = 1.0              # flange top = dome base
H = 6.4               # dome height above the flange
P_EXP, Q_EXP = 2.4, 0.5  # dome profile z = H (1 - rho^P)^Q: full shoulders, round top
SPINE_HW = 4.0        # spine half width (columns 8-15)
SPINE_TOP_HW = 3.1    # its flat top (columns 9-14 are the lit ones)
SPINE_RISE = 0.75     # spine top above the dome's crown line
SPINE_Y = (4.9, 22.1)  # its ends (rows 5-21)
GROOVES = (11.5, 16.5)  # panel lines across the lobes (rows 11 and 16)
GAP, CHAMF, DEPTH = 0.22, 0.3, 0.55  # panel line half gap, lip chamfer, groove depth
LAMPS = (11.0, 17.0)  # lamp centres (rows 9-12 and 15-18), x = 0
LENS_R, CORE_R, BEZEL_R = 1.8, 1.1, 2.2

SHELL_GROW = 0.2   # px: the outline proxy stands this far off the model
STRAP_FOOT = 0.3   # strap end height above the flange
METAL = dict(metallic=0.4, roughness=0.45)  # satin grey metal


def prof(rho):
    rho = min(1.0, max(0.0, rho))
    return max(0.0, 1 - rho ** P_EXP) ** Q_EXP


def dome_z(x, y):
    u, v = x / RX, (y - CY) / RY
    return Z0 + H * prof(math.hypot(u, v))


def crown_z(y):
    """Dome height along the centre line."""
    return Z0 + H * prof(abs((y - CY) / RY))


# --- materials ----------------------------------------------------------------------------------
class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list = []
        self.slots = {}

    def __call__(self, index, part=None, frames=None, metallic=0.5, roughness=0.42, emission=0.0):
        key = (index, part, metallic, roughness, emission)
        if key not in self.slots:
            tag = f"{NAME}_{part}" if part else f"{NAME}_{len(self.list)}"
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, tag, metallic=metallic,
                                                     roughness=roughness, emission_strength=emission,
                                                     frames=frames))
        return self.slots[key]


# --- geometry helpers (px space, through usp_talon.Part) ------------------------------------------
def quad_grid(P, grid, mat, away):
    """Faces between rows of a grid of verts (list of lists), outward away from `away`."""
    for i in range(len(grid) - 1):
        for j in range(len(grid[i]) - 1):
            P.f([grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]], mat, away=away)


class VPool:
    """Verts shared by position (so degenerate panel corners collapse to one vert)."""

    def __init__(self, P):
        self.P, self.d = P, {}

    def __call__(self, p):
        k = tuple(round(c, 5) for c in p)
        if k not in self.d:
            self.d[k] = self.P.v(p)
        return self.d[k]


def ring_strip(P, a, b, mat, away):
    n = len(a)
    for i in range(n - 1):
        P.f([a[i], a[i + 1], b[i + 1], b[i]], mat, away=away)


def panel(P, pool, v0, v1, side, mat_top, mat_lip, na=9, nb=7):
    """One armour panel of a lobe: normalised rows v0..v1 (v = (y - CY) / RY; -1/1 for the ends),
    from the spine's side (x = side * SPINE_HW) out to the flange. Its top follows the dome, its
    edges chamfer down by CHAMF and drop DEPTH into the groove; the outer edge meets the flange."""
    def pt(a, b, ins, dz):
        u_in = (SPINE_HW + ins) / RX
        vlo = v0 + ins / RY if v0 > -1 else -math.sqrt(max(0.0, 1 - u_in * u_in)) + 1e-4
        vhi = v1 - ins / RY if v1 < 1 else math.sqrt(max(0.0, 1 - u_in * u_in)) - 1e-4
        v = vlo + (vhi - vlo) * b
        u_out = math.sqrt(max(0.0, 1 - v * v))
        s = 1 - (1 - a) ** 1.7
        u = u_in + (u_out - u_in) * s
        if u > u_out:
            u = u_out
        x, y = side * u * RX, CY + v * RY
        z = Z0 + H * prof(math.hypot(u, v)) - dz
        if a >= 1.0:  # the outer edge sits on the flange
            z = Z0 - dz * 0.6
        return (x, y, z)

    # cluster rows towards the ends of the band (the lips)
    bs = [0.5 - 0.5 * math.cos(math.pi * k / nb) for k in range(nb + 1)]
    as_ = [k / na for k in range(na + 1)]
    away = (side * RX * 0.3, CY, Z0 - 3.0)
    top = [[pool(pt(a, b, GAP + CHAMF, 0.0)) for a in as_] for b in bs]
    quad_grid(P, top, mat_top, away)
    # boundary (around the grid): inner edge (a = 0) and the two band edges (b = 0, b = 1)
    def border(ins, dz):
        b0 = [pool(pt(a, 0.0, ins, dz)) for a in as_]               # one band edge, inner -> outer
        b1 = [pool(pt(a, 1.0, ins, dz)) for a in as_]               # the other
        inner = [pool(pt(0.0, b, ins, dz)) for b in bs]             # spine side, b0 -> b1
        return b0, b1, inner
    t_b0, t_b1, t_in = top[0], top[-1], [row[0] for row in top]
    c_b0, c_b1, c_in = border(GAP, CHAMF)
    w_b0, w_b1, w_in = border(GAP, DEPTH + CHAMF)
    for t, c, w in ((t_b0, c_b0, w_b0), (t_b1, c_b1, w_b1), (t_in, c_in, w_in)):
        ring_strip(P, t, c, mat_lip, away)
        ring_strip(P, c, w, mat_lip, away)


def dome_core(P, mat):
    """The dark core under the panels: the dome shrunk by the groove depth (seen in the grooves)."""
    pool = VPool(P)
    nt, rhos = 64, [0.0, 0.2, 0.4, 0.55, 0.7, 0.8, 0.88, 0.94, 0.98, 1.0]
    rings = []
    for r in rhos:
        ring = []
        for k in range(nt):
            t = 2 * math.pi * k / nt
            u, v = r * math.cos(t), r * math.sin(t)
            ring.append(pool((u * RX, CY + v * RY, Z0 + H * prof(r) - DEPTH - 0.05 - (0.3 if r >= 1 else 0))))
        rings.append(ring)
    away = (0, CY, -5.0)
    for i in range(len(rings) - 1):
        for k in range(nt):
            P.f([rings[i][k], rings[i][(k + 1) % nt], rings[i + 1][(k + 1) % nt], rings[i + 1][k]], mat, away=away)


def flange(P, mat, mat_bolt):
    """The base flange: a fitted ring round the dome, chamfered, bolted."""
    nt = 72
    profile = [(BX, BY, FLOOR - 0.05), (BX - 0.05, BY - 0.05, Z0 - 0.35), (FX, FY, Z0),
               (RX - 0.3, RY - 0.3, Z0), (RX - 0.3, RY - 0.3, FLOOR - 0.05)]
    rings = []
    for (ax, ay, z) in profile:
        rings.append([P.v((ax * math.cos(2 * math.pi * k / nt), CY + ay * math.sin(2 * math.pi * k / nt), z))
                      for k in range(nt)])
    for i in range(len(rings) - 1):
        for k in range(nt):
            q = [rings[i][k], rings[i][(k + 1) % nt], rings[i + 1][(k + 1) % nt], rings[i + 1][k]]
            c = 2 * math.pi * (k + .5) / nt
            rad = (math.cos(c) / FX, math.sin(c) / FY, 0.0)
            out = [rad, (rad[0], rad[1], 0.15), (0, 0, 1), (-rad[0], -rad[1], 0.0)][i]
            P.f(q, mat, out=out)
    # bolts on the flange top: hex heads, clear of the spine
    bx, by = (FX + RX - 0.3) / 2, (FY + RY - 0.3) / 2
    for k in range(20):
        t = 2 * math.pi * (k + 0.5) / 20
        x, y = bx * math.cos(t), CY + by * math.sin(t)
        if abs(x) < SPINE_HW + 0.8:
            continue
        pts = []
        for j in range(6):
            a = math.pi / 3 * j + t
            for z, r in ((Z0 - 0.1, 0.32), (Z0 + 0.16, 0.32), (Z0 + 0.24, 0.22)):
                pts.append((x + r * math.cos(a), y + r * math.sin(a), z))
        T.hull(P, pts, mat_bolt)


def strap_z(x, y, grow=0.0):
    """The strap's top: the dome inflated by its thickness (so it lies on the dome all the way
    down to the flange, crowned across as the dome is), Z0 outside."""
    r_ = SPINE_RISE + grow
    return Z0 + (H + r_) * prof(math.hypot(x / (RX + r_), (y - CY) / (RY + r_)))


def spine(P, mat_top, mat_side, grow=0.0):
    """The pale strap down the middle: a chamfered plate lying on the dome, running down its curve
    at both ends to a short foot on the flange (D50-D53). `grow` > 0 builds the outline proxy."""
    r_ = SPINE_RISE + grow
    hw, thw = SPINE_HW + grow, SPINE_TOP_HW + grow
    cols = [(-hw, 0.45), (-thw, 0.0), (-1.6, 0.0), (0.0, 0.0), (1.6, 0.0), (thw, 0.0), (hw, 0.45)]
    foot = STRAP_FOOT + grow
    zbase = Z0 - 0.3

    def yext(x, drop):
        """Half length of a column: where its top comes down to the foot height."""
        target = (foot + drop) / (H + r_)
        lo, hi = 0.0, 1.0  # bisect r with prof(r) = target
        for _ in range(40):
            mid = (lo + hi) / 2
            if prof(mid) > target:
                lo = mid
            else:
                hi = mid
        u = x / (RX + r_)
        return (RY + r_) * math.sqrt(max(0.0, lo * lo - u * u))

    n = 56
    ts = [-math.cos(math.pi * k / n) for k in range(n + 1)]  # clustered at the steep ends
    exts = [yext(x, d) for x, d in cols]
    rings = []
    for t in ts:
        top = []
        for (x, d), e in zip(cols, exts):
            y = CY + e * t
            top.append((x, y, max(strap_z(x, y, grow) - d, Z0 + 0.05)))
        yl, yr = top[0][1], top[-1][1]
        if grow > 0:
            zl, zr = Z0 - 0.3, Z0 - 0.3
        else:
            zl = max(dome_z(-SPINE_HW, yl) - DEPTH - 0.4, zbase)
            zr = max(dome_z(SPINE_HW, yr) - DEPTH - 0.4, zbase)
        rings.append([P.v((-hw, yl, zl))] + [P.v(p) for p in top] + [P.v((hw, yr, zr))])
    mats = [mat_side, mat_side, mat_top, mat_top, mat_top, mat_top, mat_top, mat_side, mat_side]
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        ym = (a[4].co.y + b[4].co.y) / 2
        for j in range(8):
            P.f([a[j], a[j + 1], b[j + 1], b[j]], mats[j], away=(0, ym, Z0 - 3))
        P.f([a[8], a[0], b[0], b[8]], mat_side, out=(0, 0, -1))
    for ring, sgn in ((rings[0], -1), (rings[-1], 1)):  # end faces on the flange: a fan
        c = sum((Vector(v.co) for v in ring), Vector()) / len(ring)
        cv = P.v(tuple(c))
        m = len(ring)
        for j in range(m):
            P.f([ring[j], ring[(j + 1) % m], cv], mat_side, out=(0, sgn, 0))
    return lambda y: strap_z(0.0, y, grow)


def lamp(P, y, z_top, mat_bezel, mat_ring, mat_core):
    """A domed lens in a bezel ring set into the spine top."""
    zt = z_top(y)
    nt = 24
    # bezel: a short tube with a chamfered lip, its inner wall down to the lens seat
    prof_b = [(BEZEL_R, zt - 0.5), (BEZEL_R, zt + 0.05), (BEZEL_R - 0.15, zt + 0.2),
              (LENS_R + 0.05, zt + 0.2), (LENS_R + 0.05, zt - 0.2)]
    rings = [[P.v((r * math.cos(2 * math.pi * k / nt), y + r * math.sin(2 * math.pi * k / nt), z))
              for k in range(nt)] for r, z in prof_b]
    for i in range(len(rings) - 1):
        for k in range(nt):
            q = [rings[i][k], rings[i][(k + 1) % nt], rings[i + 1][(k + 1) % nt], rings[i + 1][k]]
            c = 2 * math.pi * (k + 0.5) / nt
            out = (math.cos(c), math.sin(c), 0) if i == 0 else ((0, 0, 1) if i in (1, 2) else (-math.cos(c), -math.sin(c), 0))
            if i == 1:
                out = (math.cos(c), math.sin(c), 1)
            P.f(q, mat_bezel, out=out)
    # lens
    zb = zt - 0.2
    rs = [LENS_R, 1.65, 1.45, 1.25, CORE_R, 0.8, 0.45, 0.0]
    lh = 0.75
    lrings = []
    for r in rs:
        z = zb + lh * math.sqrt(max(0.0, 1 - (r / LENS_R) ** 2)) ** 0.8
        if r == 0:
            lrings.append([P.v((0, y, z))])
        else:
            lrings.append([P.v((r * math.cos(2 * math.pi * k / nt), y + r * math.sin(2 * math.pi * k / nt), z))
                           for k in range(nt)])
    for i in range(len(lrings) - 1):
        m = mat_core if rs[i] <= CORE_R + 1e-6 else mat_ring
        a, b = lrings[i], lrings[i + 1]
        for k in range(nt):
            if len(b) == 1:
                P.f([a[k], a[(k + 1) % nt], b[0]], m, out=(0, 0, 1))
            else:
                P.f([a[k], a[(k + 1) % nt], b[(k + 1) % nt], b[k]], m, out=(0, 0, 1))


def conduit(P, z_top, mat_rail, mat_floor):
    """Between the lamps (rows 13-14): two rails with a dark channel between them."""
    ya, yb = LAMPS[0] + BEZEL_R - 0.1, LAMPS[1] - BEZEL_R + 0.1
    zt = max(z_top(ya), z_top(yb))
    for x0, x1 in ((-1.95, -1.0), (1.0, 1.95)):
        T.hull(P, T.cbox(x0, x1, ya, yb, zt - 0.3, zt + 0.35, 0.12), mat_rail)
    T.hull(P, T.cbox(-1.0, 1.0, ya + 0.1, yb - 0.1, zt - 0.3, zt + 0.04, 0.02), mat_floor)


def end_caps(P, z_top, mat, mat_bolt):
    """Where the spine meets the flange: a clamp block at each end with two bolts."""
    for y, sgn in ((SPINE_Y[0], -1), (SPINE_Y[1], 1)):
        yi, yo = y - sgn * 0.9, y + sgn * 0.45
        zt = Z0 + SPINE_RISE + 0.5
        hw = SPINE_HW + 0.3
        T.hull(P, T.cbox(-hw, hw, min(yi, yo), max(yi, yo), FLOOR, zt, 0.3), mat)
        for x in (-2.3, 2.3):
            pts = []
            for j in range(6):
                a = math.pi / 3 * j
                for z, r in ((zt - 0.1, 0.32), (zt + 0.18, 0.32), (zt + 0.26, 0.22)):
                    pts.append((x + r * math.cos(a), (yi + yo) / 2 + r * math.sin(a), z))
            T.hull(P, pts, mat_bolt)


def shell_proxy(coll, z_top):
    """Closed, smooth stand-in for the pod (every part grown by SHELL_GROW) for the outline shell:
    no grooves, bolts or rails, its foot above the floor plate (ink at the base not buried in it)."""
    e = SHELL_GROW
    zl = FLOOR + 0.35
    P = T.Part(f"{NAME}_proxy", smooth_angle=180)
    nt = 96
    prof_r = [(BX + e, BY + e, zl), (BX - 0.05 + e, BY - 0.05 + e, Z0 - 0.35), (FX + 0.4 * e, FY + 0.4 * e, Z0 + e)]
    for rho in (1.0, 0.999, 0.995, 0.985, 0.97, 0.94, 0.9, 0.85, 0.78, 0.7, 0.6, 0.48, 0.35, 0.2):
        prof_r.append(((RX + e) * rho, (RY + e) * rho, Z0 + e + H * prof(rho)))
    rings = [[P.v((ax * math.cos(2 * math.pi * k / nt), CY + ay * math.sin(2 * math.pi * k / nt), z))
              for k in range(nt)] for ax, ay, z in prof_r]
    away = (0, CY, Z0 + 1.0)
    for i in range(len(rings) - 1):
        for k in range(nt):
            P.f([rings[i][k], rings[i][(k + 1) % nt], rings[i + 1][(k + 1) % nt], rings[i + 1][k]], 0, away=away)
    top, bot = P.v((0, CY, Z0 + e + H)), P.v((0, CY, zl))
    for k in range(nt):
        P.f([rings[-1][k], rings[-1][(k + 1) % nt], top], 0, out=(0, 0, 1))
        P.f([rings[0][k], rings[0][(k + 1) % nt], bot], 0, out=(0, 0, -1))
    spine(P, 0, 0, grow=e)
    for y, sgn in ((SPINE_Y[0], -1), (SPINE_Y[1], 1)):  # the clamps
        yi, yo = y - sgn * 0.9, y + sgn * 0.45
        hw = SPINE_HW + 0.3 + e
        T.hull(P, T.cbox(-hw, hw, min(yi, yo) - e, max(yi, yo) + e, zl, Z0 + SPINE_RISE + 0.5 + e, 0.3), 0)
    for y in LAMPS:  # bezel and lens as one solid
        zt = z_top(y)
        pts = []
        for r, z in ((BEZEL_R + e, zt - 0.6), (BEZEL_R + e, zt + 0.05 + e), (BEZEL_R - 0.15 + e, zt + 0.2 + e),
                     (1.25, zt - 0.2 + 0.75 * 0.8 + e), (0.6, zt - 0.2 + 0.75 + e)):
            pts += [(r * math.cos(2 * math.pi * k / 24), y + r * math.sin(2 * math.pi * k / 24), z) for k in range(24)]
        T.hull(P, pts, 0)
    return T.finish(P, [], coll)


def build():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    for o in list(bpy.data.objects):
        if o.name.startswith(NAME):
            bpy.data.objects.remove(o, do_unlink=True)
    M = Mats(sprite)
    DOME = M(7, part="dome", **METAL)
    LINE = M(4, part="line", metallic=0.3, roughness=0.6)
    FL = M(7, part="flange", metallic=0.5, roughness=0.5)
    BOLT = M(8, part="bolt", metallic=0.6, roughness=0.35)
    SP_TOP = M(10, part="spine", **METAL)
    SP_SIDE = M(9, part="spineside", **METAL)
    BEZEL = M(7, part="bezel", metallic=0.6, roughness=0.35)
    RING = M(112, part="lampring", frames={129: 115, 131: 118}, metallic=0.0, roughness=0.25, emission=1.0)
    CORE = M(116, part="lamp", frames={129: 121, 131: 123}, metallic=0.0, roughness=0.2, emission=2.5)
    CHAN = M(6, part="channel", metallic=0.4, roughness=0.55)

    P = T.Part(NAME, smooth_angle=34)
    pool = VPool(P)
    vg = [(g - CY) / RY for g in GROOVES]
    bands = [(-1.0, vg[0]), (vg[0], vg[1]), (vg[1], 1.0)]
    for side in (-1, 1):
        for v0, v1 in bands:
            panel(P, pool, v0, v1, side, DOME, DOME)
    dome_core(P, LINE)
    flange(P, FL, BOLT)
    z_top = spine(P, SP_TOP, SP_SIDE)
    for y in LAMPS:
        lamp(P, y, z_top, BEZEL, RING, CORE)
    conduit(P, z_top, SP_TOP, CHAN)
    end_caps(P, z_top, SP_SIDE, BOLT)
    pod = T.finish(P, M.list, coll)
    for m in M.list[len(pod.data.materials):]:  # finish() sets materials from the list at the time
        pod.data.materials.append(m)
    # The outline shell (D51) from a simple closed proxy a hair outside the model: the smooth dome
    # and flange, the strap, its clamps and the lamp bezels. A shell remeshed from the detailed pod
    # dipped into the grooves and the flange junction and drew ink scribbles there in game.
    proxy = shell_proxy(coll, z_top)
    shell = common.outline_shell(proxy, coll, faces=3000)
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(proxy, do_unlink=True)
    return [pod, shell]


if __name__ == "__main__":
    objs = build()
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", common.load_sprite(WT, NAME)["sprites"])
    tris = 0
    for o in objs[:1]:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    print(f"built {NAME}: {tris} triangles (pod), shell {len(objs[1].data.polygons)} faces")
