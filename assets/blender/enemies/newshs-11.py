"""newshs-11: the grey observation dome of the stone fortress (newshs.shp 11, 125, 277).

Reading of the sprite (24 x 28, opaque: it fills its tile; tools/calibration/rubric.md):
- A light grey dome stands at the back of the tile (columns 3.5-19.5, rows 0-14.5, round: its
  lower-left contour and its top touching the tile edge). Its bright left rim (column 4, 12-14)
  and the dark right edge (column 19, 4) are lighting, the dome's metal is 9.
- A straight seam across it at row 6 (7-8): the dome is two shells, a rear hood and a front body,
  so the seam is a real groove (D50-D53 panel line), not paint.
- A square window in the hood (columns 9-15, rows 2-5) inside a recess whose top and left walls
  are in shade (row 1 and column 8, 4-5); the right and bottom walls drop straight. The glass is
  grey (8) on frame 11, a bright green lens on 125 (pane 199, core 203: its 201-207 glow, the 207 hot spot read as highlight), half lit on 277 (upper
  rows grey, lower rows 195/198). One window part per frame (frame_part, D17), as before.
- Two conduits (columns 10 and 12, 10; the dark columns 9 and 11 between them are their shade)
  run from the seam down the front of the dome.
- Below the dome a dark ribbed apron (rows 14.5-22.5, columns 5-18, 3-5 with lit ribs at
  columns 7-8, 10, 12 and 16): a low armoured glacis the dome sits on, its ribs carrying on
  from the conduits. The black band to the right of the dome (columns 19-23) and under the
  apron (row 23) is the dome's cast shadow on the stone: lighting, lifted to the stone's tones.

Hard surface: lofted dome shells (chord sections, clustered at the seam lips and the rim), the
seam a chamfered groove, the window recess cut by a boolean (sloped top/left walls), a fitted
base flange with hex bolts, conduits with collars and a manifold block, a chamfered glacis with
ribs and bolted feet. Floor: the stone plate painted from the sprite (tyrian_ground). Outline
shell from a smooth proxy (D51). Underside: closed by the floor plate only.

Run: blender --background --python assets/blender/enemies/newshs-11.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newshs-11"
PX = 1 / 12

# --- plan and heights (sprite px: x right from the tile centre, y down from its top, z up) ------
CX, CY = -0.5, 7.5      # dome centre (column 11.5, row 7.5)
NSE = 3.5               # plan superellipse exponent: the sprite's dome is a rounded square in plan
RXF, RYF = 7.65, 7.5    # flange foot outer outline (columns 3.85-19.15, rows 0-15)
RXT, RYT = 7.4, 7.25   # flange top outer edge
RX, RY = 7.05, 6.9      # dome base outline (on the flange)
FLOOR = 0.36            # floor top (0.03 units, the fortress tiles' FLOOR)
Z0 = 0.95               # flange top = dome base
H = 5.4                 # dome height above the flange
P_EXP, Q_EXP = 3.0, 0.5
P_REAR, Q_REAR = 4.5, 0.38
YS, GAP, CHAMF, DEPTH = 6.5, 0.3, 0.28, 0.45   # the seam: row, half gap, lip chamfer, depth
WIN_OPEN = (-4.0, 4.0, 1.15, 6.5)   # window opening at the surface: x0, x1, y0, y1 (near sill chamfered)
WIN_GLASS = (-3.05, 4.0, 1.95, 6.0)  # recess floor (glass)
WIN_CREASE = 3.95  # the glass is two panes: a steep rear pane and a front pane facing the camera
PIPES = (-1.5, 0.5)     # conduit centres (columns 10, 12)
PIPE_R = 0.42
AP_Y0, AP_Y1 = 14.0, 22.6           # glacis rear and front edge
AP_X0, AP_X1 = -7.1, 6.5            # glacis sides (columns 4.9-18.5)
AP_Z0, AP_Z1 = 2.5, 1.05           # glacis top height at the rear / at the front edge
RIBS = ((-4.6, 1.0), (-1.5, 0.5), (0.5, 0.5), (4.5, 0.5))  # x centre, half width
SHELL_GROW = 0.2
METAL = dict(metallic=0.4, roughness=0.55)  # satin painted metal (the sprite's front face is a flat 9)


def prof(rho, y=None):
    """Dome profile; behind the seam the hood's shoulders fill out (P, Q blend towards the rear) so
    its top, where the window sits, faces up rather than back."""
    rho = min(1.0, max(0.0, rho))
    p, q = P_EXP, Q_EXP
    if y is not None and y < YS:
        t = min(1.0, (YS - y) / 3.5)
        t = t * t * (3 - 2 * t)
        p, q = p + (P_REAR - p) * t, q + (Q_REAR - q) * t
    return max(0.0, 1 - rho ** p) ** q


def srho(u, v):
    return (abs(u) ** NSE + abs(v) ** NSE) ** (1 / NSE)


def sep(t, ax, ay, z):
    """Point at parameter angle t on the superellipse ax, ay round the dome centre."""
    c, s = math.cos(t), math.sin(t)
    return (CX + ax * math.copysign(abs(c) ** (2 / NSE), c), CY + ay * math.copysign(abs(s) ** (2 / NSE), s), z)


def dome_z(x, y):
    return Z0 + H * prof(srho((x - CX) / RX, (y - CY) / RY), y)


def surf_z(x, y):
    """Dome top with the seam groove."""
    z = dome_z(x, y)
    d = abs(y - YS)
    if d <= GAP:
        return z - DEPTH
    if d < GAP + CHAMF:  # chamfered lip: drops CHAMF*0.6 over the chamfer, then the wall
        t = (GAP + CHAMF - d) / CHAMF
        return z - 0.16 * t
    return z


def ap_z(y):
    t = (y - AP_Y0) / (AP_Y1 - AP_Y0)
    return AP_Z0 + (AP_Z1 - AP_Z0) * t


# --- materials ----------------------------------------------------------------------------------
class Mats:
    def __init__(self, sprite):
        self.sprite, self.list, self.slots = sprite, [], {}

    def __call__(self, index, part, metallic=0.4, roughness=0.45, emission=0.0, frames=None):
        key = (index, part)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, f"{NAME}_{part}", metallic=metallic,
                                                     roughness=roughness, emission_strength=emission,
                                                     frames=frames))
        return self.slots[key]


# --- the dome: a loft of chord sections along y ------------------------------------------------
def dome_ys():
    n = 34
    ys = [CY + RY * (-math.cos(math.pi * k / n)) for k in range(n + 1)]
    ys += [YS - GAP - CHAMF, YS - GAP, YS + GAP, YS + GAP + CHAMF,
           YS - GAP - 0.002, YS + GAP + 0.002]
    ys = sorted(set(round(y, 4) for y in ys))
    return [y for y in ys if CY - RY < y < CY + RY] + []


def build_dome(P, mat_dome, mat_seam):
    """Closed dome solid: top surface rows (chord sections), its rim on the flange, a flat base."""
    nu = 36
    ys = dome_ys()
    rows = []
    for y in ys:
        v = (y - CY) / RY
        half = RX * max(0.0, 1 - abs(v) ** NSE) ** (1 / NSE)
        row = []
        for j in range(nu + 1):
            u = -math.cos(math.pi * j / nu)  # clustered at the rim
            x = CX + half * u
            z = surf_z(x, y) if abs(u) < 0.999 else Z0
            row.append(P.v((x, y, z)))
        rows.append(row)
    top_v, bot_v = P.v((CX, CY - RY, Z0)), P.v((CX, CY + RY, Z0))
    away = (CX, CY, Z0 - 4.0)
    for i in range(len(rows) - 1):
        ym = (ys[i] + ys[i + 1]) / 2
        m = mat_seam if abs(ym - YS) < GAP + CHAMF + 0.01 else mat_dome
        for j in range(nu):
            P.f([rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]], m, away=away)
    for j in range(nu):
        P.f([top_v, rows[0][j + 1], rows[0][j]], mat_dome, away=away)
        P.f([bot_v, rows[-1][j], rows[-1][j + 1]], mat_dome, away=away)
    # base: a flat cap at Z0 - 0.3 (inside the flange) joined by the rim wall
    nt = 72
    base = []
    for k in range(nt):
        t = 2 * math.pi * k / nt
        base.append(P.v(sep(t, RX - 0.05, RY - 0.05, Z0 - 0.3)))
    c = P.v((CX, CY, Z0 - 0.3))
    for k in range(nt):
        P.f([base[k], base[(k + 1) % nt], c], mat_dome, out=(0, 0, -1))


def flange(P, mat, mat_bolt):
    nt = 80
    profile = [(RXF, RYF, FLOOR - 0.05), (RXF - 0.05, RYF - 0.05, Z0 - 0.3), (RXT, RYT, Z0),
               (RX - 0.25, RY - 0.25, Z0), (RX - 0.25, RY - 0.25, FLOOR - 0.05)]
    rings = [[P.v(sep(2 * math.pi * k / nt, ax, ay, z)) for k in range(nt)] for ax, ay, z in profile]
    for i in range(len(rings) - 1):
        for k in range(nt):
            c = 2 * math.pi * (k + .5) / nt
            rad = (math.cos(c) / RXF, math.sin(c) / RYF, 0.0)
            out = [rad, (rad[0], rad[1], 0.2), (0, 0, 1), (-rad[0], -rad[1], 0.0)][i]
            P.f([rings[i][k], rings[i][(k + 1) % nt], rings[i + 1][(k + 1) % nt], rings[i + 1][k]], mat, out=out)
    bx, by = (RXT + RX) / 2, (RYT + RY) / 2
    for k in range(18):
        t = 2 * math.pi * (k + 0.5) / 18
        x, y, _ = sep(t, bx, by, 0)
        if y > AP_Y0 - 1.2:  # under the glacis
            continue
        hexbolt(P, x, y, Z0, 0.24, mat_bolt, t)


def hexbolt(P, x, y, z, r, mat, rot=0.0):
    pts = []
    for j in range(6):
        a = math.pi / 3 * j + rot
        for zz, rr in ((z - 0.1, r), (z + 0.13, r), (z + 0.2, r * 0.7)):
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a), zz))
    T.hull(P, pts, mat)


# --- conduits -----------------------------------------------------------------------------------
def tube_along(P, path, r, mat, nt=10, caps=True):
    """A round tube along a polyline of (x, y, z) points (no twist: frames from the path)."""
    rings = []
    for i, p in enumerate(path):
        p = Vector(p)
        a = Vector(path[max(0, i - 1)])
        b = Vector(path[min(len(path) - 1, i + 1)])
        t = (b - a).normalized()
        side = Vector((1, 0, 0))
        n = t.cross(side).normalized()
        if n.z < 0:
            n = -n
        s = n.cross(t).normalized()
        rings.append([P.v(tuple(p + r * (math.cos(2 * math.pi * k / nt) * s + math.sin(2 * math.pi * k / nt) * n)))
                      for k in range(nt)])
    for i in range(len(rings) - 1):
        c = (Vector(path[i]) + Vector(path[i + 1])) / 2
        for k in range(nt):
            P.f([rings[i][k], rings[i][(k + 1) % nt], rings[i + 1][(k + 1) % nt], rings[i + 1][k]], mat, away=tuple(c))
    if caps:
        for ring, i, j in ((rings[0], 0, 1), (rings[-1], -1, -2)):
            cv = P.v(tuple(path[i]))
            out = tuple(Vector(path[i]) - Vector(path[j]))
            for k in range(nt):
                P.f([ring[k], ring[(k + 1) % nt], cv], mat, out=out)


def conduits(P, mat_pipe, mat_collar, mat_block):
    y_start, y_end = YS + GAP + CHAMF + 0.35, 14.3
    for x in PIPES:
        path = []
        n = 22
        for k in range(n + 1):
            y = y_start + (y_end - y_start) * k / n
            z = max(dome_z(x, y), ap_z(y)) + PIPE_R * 0.55
            path.append((x, y, z))
        tube_along(P, path, PIPE_R, mat_pipe)
        # collars: where it leaves the seam, and a clamp halfway
        for yc, w in ((y_start + 0.1, 0.35), (10.6, 0.3)):
            zc = dome_z(x, yc) + PIPE_R * 0.55
            ring = [(x + (PIPE_R + 0.13) * math.cos(2 * math.pi * k / 12), yc + dy,
                     zc + (PIPE_R + 0.13) * math.sin(2 * math.pi * k / 12))
                    for k in range(12) for dy in (-w / 2, w / 2)]
            ring = [(px, py, max(pz, dome_z(px, py) - 0.2)) for px, py, pz in ring]
            T.hull(P, ring, mat_collar)
    # manifold block where both conduits meet the glacis
    x0, x1 = PIPES[0] - 0.95, PIPES[1] + 0.95
    T.hull(P, T.cbox(x0, x1, 13.3, 15.1, Z0, ap_z(14.0) + 0.85, 0.22), mat_block)
    for x in PIPES:
        hexbolt(P, x, 14.55, ap_z(14.0) + 0.85, 0.2, mat_collar)


# --- the glacis ---------------------------------------------------------------------------------
def glacis(P, mat_top, mat_side, mat_rib, mat_bolt):
    ch = 0.3
    yf = AP_Y1 - 0.55  # nose: the front edge chamfers down to the floor
    pts = []
    for x, sx in ((AP_X0, 1), (AP_X1, -1)):
        pts += [(x + sx * ch, AP_Y0, AP_Z0), (x, AP_Y0, AP_Z0 - ch), (x, AP_Y0, FLOOR - 0.02),
                (x + sx * ch, yf, ap_z(yf)), (x, yf, ap_z(yf) - ch),
                (x + sx * ch, AP_Y1, FLOOR + 0.12), (x, AP_Y1 - 0.1, FLOOR + 0.05), (x, AP_Y1, FLOOR - 0.02)]
    T.hull(P, pts, mat_top)
    # ribs down the slope
    for xc, hw in RIBS:
        rpts = []
        for y in (AP_Y0 + 0.4, yf - 0.25):
            zb = ap_z(y)
            for x, sx in ((xc - hw, 1), (xc + hw, -1)):
                rpts += [(x, y, zb - 0.1), (x, y, zb + 0.3), (x + sx * 0.18, y, zb + 0.46)]
        y = yf + 0.2  # sloped end
        for x in (xc - hw, xc + hw):
            rpts += [(x, y, ap_z(yf) - 0.3)]
        T.hull(P, rpts, mat_rib)
        hexbolt(P, xc, yf - 0.85, ap_z(yf - 0.85) + 0.46, min(0.24, hw * 0.55), mat_bolt)
    # a cross panel line half way down (a modelled groove across between the ribs is too fine at
    # this size; a raised strap reads instead)
    ys = 18.4
    T.hull(P, T.cbox(AP_X0 + 0.25, AP_X1 - 0.25, ys - 0.3, ys + 0.3, ap_z(ys) - 0.2, ap_z(ys) + 0.2, 0.12), mat_side)


# --- window -------------------------------------------------------------------------------------
def recess_plane():
    """Recess floor zp(x, y): two panes meeting at WIN_CREASE. The rear pane drops steeply under the
    shaded rear wall; the front pane (frame 277's lit band, 125's lower glow) sits just under the dome
    and leans ~17 degrees towards the tilted game camera, its near sill a shallow chamfer that runs
    into the seam groove, so nothing in front of it hides the glass. Both lean down to the right with
    the dome's shoulder (the right wall drops straight)."""
    gx0, gx1, y0, y1 = WIN_GLASS
    yc = WIN_CREASE
    xm = (gx0 + gx1) / 2
    sx = ((dome_z(gx1, 5.0) - dome_z(gx0, 5.0)) / (gx1 - gx0))
    xs = [gx0 + (gx1 - gx0) * i / 14 for i in range(15)]
    za = min(dome_z(xm, WIN_OPEN[2]) - 0.4, dome_z(xm, y0) - 0.75)
    zb = min(dome_z(x, yc) - sx * (x - xm) for x in xs) - 0.1
    zn = zb - 0.63
    def base(y):
        if y <= yc:
            return za + (zb - za) * (y - y0) / (yc - y0)
        return zb + (zn - zb) * (y - yc) / (y1 - yc)
    return lambda x, y: base(y) + sx * (x - xm)


def cutters(coll, zp):
    """The recess as two convex cutters (rear pane, front pane) meeting at the crease."""
    out = []
    gx0, gx1, gy0, gy1 = WIN_GLASS
    ox0, ox1, oy0, oy1 = WIN_OPEN
    yc = WIN_CREASE
    for (ga, gb), (oa, ob) in (((gy0, yc + 0.02), (oy0, yc + 0.02)), ((yc - 0.02, gy1), (yc - 0.02, oy1))):
        P = T.Part(f"{NAME}_cutter{len(out)}", smooth_angle=1)
        pts = []
        for x in (gx0, gx1):
            for y in (ga, gb):
                pts.append((x, y, zp(x, y)))
        for x in (ox0, ox1):
            for y in (oa, ob):
                zs = max(dome_z(xx, y) for xx in (ox0, ox1, 0.0)) + 0.1
                pts.append((x, y, zs))
                pts.append((x, y, 14.0))
        T.hull(P, pts, 0)
        out.append(T.finish(P, [], coll))
    return out


def window_parts(coll, M, zp):
    gx0, gx1, gy0, gy1 = WIN_GLASS
    off = M(8, "glass_off", metallic=0.1, roughness=0.18)
    lit = M(199, "glass_lit", metallic=0.0, roughness=0.2, emission=2.0)
    core = M(203, "glass_core", metallic=0.0, roughness=0.6, emission=1.0)  # the 201-207 glow, 207 hot spot trimmed as highlight; the game glows at the palette colour whatever the strength
    half = M(195, "glass_half", metallic=0.0, roughness=0.2, emission=2.0)
    half_core = M(198, "glass_halfcore", metallic=0.0, roughness=0.2, emission=2.0)

    def pane(P, x0, x1, y0, y1, lift, mat, round_=0.0):
        """A pane slab on the recess floor, following its crease; round_ > 0 rounds its corners
        (a lens). Built in rows across y so it bends with the floor."""
        r = max(0.0, round_)
        ys = {y0, y1}
        if y0 < WIN_CREASE < y1:
            ys.add(WIN_CREASE)
        nseg = 4
        for k in range(nseg + 1):
            a = (math.pi / 2) * k / nseg
            ys.add(y0 + r - r * math.cos(a))
            ys.add(y1 - r + r * math.cos(a))
        ys = sorted(y for y in ys if y0 <= y <= y1)

        def xr(y):
            d = 0.0
            if r > 0:
                dy = max(0.0, (y0 + r) - y, y - (y1 - r))
                d = r - math.sqrt(max(0.0, r * r - dy * dy))
            return x0 + d, x1 - d

        top, bot = [], []
        for y in ys:
            xa, xb = xr(y)
            top.append([P.v((x, y, zp(x, y) + lift)) for x in (xa, xb)])
            bot.append([P.v((x, y, zp(x, y) + lift - 0.06)) for x in (xa, xb)])
        xm = (x0 + x1) / 2

        def mid(y, dz):
            return (xm, y, zp(xm, y) + lift - 0.03 + dz)
        for i in range(len(ys) - 1):
            ym = (ys[i] + ys[i + 1]) / 2
            P.f([top[i][0], top[i][1], top[i + 1][1], top[i + 1][0]], mat, away=mid(ym, -1.0))
            P.f([bot[i][0], bot[i][1], bot[i + 1][1], bot[i + 1][0]], mat, away=mid(ym, 1.0))
            for j in (0, 1):
                P.f([top[i][j], top[i + 1][j], bot[i + 1][j], bot[i][j]], mat, away=mid(ym, 0.0))
        for i, dy in ((0, 1.0), (-1, -1.0)):
            P.f([top[i][0], top[i][1], bot[i][1], bot[i][0]], mat, away=mid(ys[i] + dy, 0.0))

    parts = []
    P = T.Part(f"{NAME}-window-11", smooth_angle=20)
    pane(P, gx0, gx1, gy0, gy1, 0.08, off)
    parts.append(common.frame_part(T.finish(P, M.list, coll), [11]))
    P = T.Part(f"{NAME}-window-125", smooth_angle=20)
    pane(P, gx0, gx1, gy0, gy1, 0.08, lit)
    pane(P, -2.1, 2.1, 2.85, 5.05, 0.14, core, round_=0.6)
    parts.append(common.frame_part(T.finish(P, M.list, coll), [125]))
    P = T.Part(f"{NAME}-window-277", smooth_angle=20)
    ym = WIN_CREASE
    pane(P, gx0, gx1, gy0, ym, 0.08, off)
    pane(P, gx0, gx1, ym, gy1, 0.08, half)
    pane(P, -1.6, 1.6, ym + 0.2, 5.15, 0.14, half_core, round_=0.35)
    parts.append(common.frame_part(T.finish(P, M.list, coll), [277]))
    return parts


def colour_recess(obj, M, zp):
    """After the boolean: the recess floor 5, its top and left walls 5 (in shade), right wall 9,
    front wall 7 (Blender coords: y up = towards the tile top)."""
    me = obj.data
    gx0, gx1, gy0, gy1 = WIN_GLASS
    ox0, ox1, oy0, oy1 = WIN_OPEN
    wall_dark = M(5, "recess", metallic=0.35, roughness=0.55)
    wall_r = M(9, "dome", **METAL)
    wall_f = M(7, "seam", metallic=0.4, roughness=0.5)
    for poly in me.polygons:
        c = poly.center
        x, y, z = c.x / PX, 14 - c.y / PX, c.z / PX
        if not (ox0 - 0.05 <= x <= ox1 + 0.05 and oy0 - 0.05 <= y <= oy1 + 0.05):
            continue
        if z > dome_z(x, y) - 0.06:
            continue  # the dome's own surface
        n = poly.normal
        if y > gy1 + 0.02:
            poly.material_index = wall_f  # the sill chamfer running into the seam groove
            continue
        if n.z > 0.85 and z < zp(x, y) + 0.1:
            poly.material_index = wall_dark
        elif n.y < -0.4:  # faces the tile top: rear wall... (normal points to -Y in Blender = down the tile)
            poly.material_index = wall_dark
        elif n.x > 0.4:
            poly.material_index = wall_dark  # left wall faces right
        elif n.x < -0.4:
            poly.material_index = wall_r
        elif n.y > 0.4:
            poly.material_index = wall_f
        else:
            poly.material_index = wall_dark


# --- floor --------------------------------------------------------------------------------------
def covered(x0, x1, y0, y1):
    def in_ell(x, y):
        return srho((x - CX) / (RXF - 0.15), (y - CY) / (RYF - 0.15)) < 1

    def in_ap(x, y):
        return AP_X0 + 0.1 < x < AP_X1 - 0.1 and AP_Y0 + 0.1 < y < AP_Y1 - 0.1
    return all(in_ell(x, y) or in_ap(x, y) for x in (x0, x1) for y in (y0, y1))


def floor(sprite, M, coll):
    """Stone plate painted per pixel in the grey tones (as lib_b073.grey_tones). The dome's cast
    shadow (right of it and under the glacis' front) is lighting: those pixels lifted by 3 steps."""
    pix = sprite["frames"][0]["pixels"]
    colors = sprite["colors"]
    tones = ((1, 3), (4, 6), (7, 9), (10, 15))
    slots = []
    for lo, hi in tones:
        have = [i for i in range(lo, hi + 1) if str(i) in colors]
        mid = (lo + hi) / 2
        slots.append(M(min(have, key=lambda i: abs(i - mid)), f"stone{lo}", metallic=0.05, roughness=0.85))

    def tone(c, r):
        i = pix[r][c]
        shadow = (c >= 19 and 1 <= r <= 23) or (r == 23 and 4 <= c <= 19) or (r in (13, 14) and c >= 17)
        if shadow and i <= 5:
            i += 3
        for (lo, hi), s in zip(tones, slots):
            if lo <= i <= hi:
                return s
        return slots[1]

    P = T.Part(f"{NAME}_floor", smooth_angle=5)
    T.hull(P, [(x, y, z) for x in (-12.0, 12.0) for y in (0.0, 28.0) for z in (0.0, FLOOR - 0.01)], slots[1])
    for r in range(28):
        c = 0
        while c < 24:
            if covered(c - 12, c - 11, r, r + 1):
                c += 1
                continue
            s = tone(c, r)
            e = c + 1
            while e < 24 and not covered(e - 12, e - 11, r, r + 1) and tone(e, r) == s:
                e += 1
            vs = [P.v((xx, yy, FLOOR)) for xx, yy in ((c - 12, r), (e - 12, r), (e - 12, r + 1), (c - 12, r + 1))]
            P.f(vs, s, out=(0, 0, 1))
            c = e
    obj = T.finish(P, M.list, coll)
    obj.data.shade_flat()
    obj["tyrian_ground"] = True
    return obj


# --- outline proxy ------------------------------------------------------------------------------
def shell_proxy(coll):
    e = SHELL_GROW
    P = T.Part(f"{NAME}_proxy", smooth_angle=180)
    nt = 96
    zl = FLOOR + 0.3
    prof_r = [(RXF + e, RYF + e, zl), (RXF - 0.05 + e, RYF - 0.05 + e, Z0 - 0.3), (RXT + e * 0.5, RYT + e * 0.5, Z0 + e)]
    for rho in (1.0, 0.995, 0.98, 0.95, 0.9, 0.83, 0.74, 0.62, 0.48, 0.32, 0.16):
        prof_r.append(((RX + e) * rho, (RY + e) * rho, None))
    rings = []
    for ax, ay, z in prof_r:
        ring = []
        for k in range(nt):
            x, y, _ = sep(2 * math.pi * k / nt, ax, ay, 0.0)
            zz = z if z is not None else Z0 + e + H * prof(ax / (RX + e), y)
            ring.append(P.v((x, y, zz)))
        rings.append(ring)
    away = (CX, CY, Z0 + 1.0)
    for i in range(len(rings) - 1):
        for k in range(nt):
            P.f([rings[i][k], rings[i][(k + 1) % nt], rings[i + 1][(k + 1) % nt], rings[i + 1][k]], 0, away=away)
    top, bot = P.v((CX, CY, Z0 + e + H * prof(0.0, CY))), P.v((CX, CY, zl))
    for k in range(nt):
        P.f([rings[-1][k], rings[-1][(k + 1) % nt], top], 0, out=(0, 0, 1))
        P.f([rings[0][k], rings[0][(k + 1) % nt], bot], 0, out=(0, 0, -1))
    yf = AP_Y1 - 0.55
    pts = []
    for x in (AP_X0 - e, AP_X1 + e):
        pts += [(x, AP_Y0 - e, zl), (x, AP_Y0 - e, AP_Z0 + 0.46 + e), (x, yf, ap_z(yf) + 0.46 + e),
                (x, AP_Y1 + e, zl + 0.1)]
    T.hull(P, pts, 0)
    T.hull(P, T.cbox(PIPES[0] - 0.95 - e, PIPES[1] + 0.95 + e, 13.3 - e, 15.1 + e, zl, ap_z(14.0) + 0.85 + e, 0.22), 0)
    return T.finish(P, [], coll)


def build():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    M = Mats(sprite)
    DOME = M(9, "dome", **METAL)
    SEAM = M(7, "seam", metallic=0.4, roughness=0.5)
    FL = M(8, "flange", metallic=0.45, roughness=0.5)
    BOLT = M(10, "bolt", metallic=0.55, roughness=0.35)
    PIPE = M(10, "pipe", metallic=0.5, roughness=0.35)
    COLLAR = M(8, "collar", metallic=0.5, roughness=0.4)
    BLOCK = M(8, "manifold", metallic=0.45, roughness=0.45)
    AP = M(3, "glacis", metallic=0.35, roughness=0.55)
    APS = M(4, "glacisstrap", metallic=0.35, roughness=0.55)
    RIB = M(4, "rib", metallic=0.4, roughness=0.5)
    M(5, "recess", metallic=0.35, roughness=0.55)

    zp = recess_plane()
    P = T.Part(NAME, smooth_angle=36)
    build_dome(P, DOME, SEAM)
    dome = T.finish(P, M.list, coll)
    for cut in cutters(coll, zp):
        mod = dome.modifiers.new("window", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = cut
        bpy.context.view_layer.objects.active = dome
        with bpy.context.temp_override(object=dome, active_object=dome):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(cut, do_unlink=True)
    colour_recess(dome, M, zp)

    P = T.Part(f"{NAME}_hw", smooth_angle=34)
    flange(P, FL, BOLT)
    conduits(P, PIPE, COLLAR, BLOCK)
    glacis(P, AP, APS, RIB, BOLT)
    hw = T.finish(P, M.list, coll)
    wins = window_parts(coll, M, zp)
    fl = floor(sprite, M, coll)

    # join dome + hardware into one body
    body = dome
    with bpy.context.temp_override(active_object=dome, object=dome,
                                   selected_objects=[dome, hw], selected_editable_objects=[dome, hw]):
        bpy.ops.object.join()
    body.name = NAME
    objs = [body] + wins + [fl]
    for o in objs:
        for m in M.list[len(o.data.materials):]:
            o.data.materials.append(m)
    proxy = shell_proxy(coll)
    shell = common.outline_shell(proxy, coll, faces=3000)
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(proxy, do_unlink=True)
    return objs + [shell]


if __name__ == "__main__":
    sprite = common.load_sprite(WT, NAME)
    objs = build()
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"])
    tris = 0
    for o in objs[:-1]:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    print(f"built {NAME}: {tris} triangles (body + windows + floor)")
