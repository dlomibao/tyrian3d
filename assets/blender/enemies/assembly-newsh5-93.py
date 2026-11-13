"""Heavy drill torpedo (newsh5.shp frames 55 over 93, assembly of 2 pieces, 24 x 56 px).

What it is (D120/D122: identify the object first). 4.11 ?TUNNEL? (harness main=8): ground layer,
ARMOUR 255, 28 rigid pairs in two columns (x 90 and 208), one every 100 ticks from t 340; it moves
(0,+2), then sways (+-2,-1), then accelerates down the screen (y 0..+8 px/tick on top of the scroll)
and leaves by the bottom after ~65 ticks. So it is an indestructible heavy torpedo / drill diving
DOWN the tunnel, the pointed bulb (sprite bottom) first. Not a column lying on the ground.

So it is built as a flying body of revolution along screen Y, its axis level at AXIS_Z above the
ground, closed all round (the underside is only a plausible closed shape):
  - rear (sprite top): a domed tail cap and a broad stabiliser flange ring (rows 0-8),
  - a neck into the motor hood (rows 12-17): a wide faired shell over the core, with two side pods
    running on to row 20 and a lower cross frame between them,
  - two glowing red power hoses coming out of the hood's front lip through couplings, curving in
    and down to the collar (rows 17-23), a dark spine with a polished top bar between them,
  - a collar (24-26), a neck, a thin ring (30), a ribbed sleeve (32-37), a piston cage (38-41: a
    dark core inside four struts, the top one polished), a bearing knob (42-45),
  - and the pointed ogive drill bulb (46-55) with a hardened tip.
Every radius follows the inner edge of the sprite's ink border row by row (D74), the colours are
the sprite's region medians (greys 5-9, hoses 116), highlights are sheen (rule 2).

Run: blender --background --python assembly-newsh5-93.py -- [--no-export] [--out whole.glb] [--review DIR]
Exports newsh5-55 and newsh5-93 (each at its own origin with its _outline shell) through
common.export_sprite_model; --review writes review renders and the IoU measure into DIR.
The repo is found from the script's own location.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent


def find_repo():
    """The repo this script lives in (assets/blender/enemies/ -> repo root)."""
    for p in HERE.parents:
        if (p / "package.json").exists() and (p / "assets" / "blender" / "common.py").exists():
            return p
    raise SystemExit(f"no repo above {HERE}")


ROOT = find_repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "assembly-newsh5-93"
PIECES = ["newsh5-55", "newsh5-93"]
LAYOUT = [("newsh5-55", 104, 11), ("newsh5-93", 104, 39)]
CX0, CY0 = 104, 25  # assembly centre (screen px) = Blender origin
U = 1 / 12  # one sprite px
AXIS_E = 11.25  # the shaft's axis, as a pixel edge coordinate: the inner mask's mean centre (its
# right edge is drawn in ink one px further in on the shaded side)
HOOD_E = 11.5  # the hood, pods and hoses: rows 13-22 are centred on column 11's centre
AXIS_Z = 5.6  # axis height above the ground, px


def BX(e):
    """Pixel edge column -> Blender X."""
    return (e - 12) * U


def BY(r):
    """Pixel edge row -> Blender Y (sprite up = +Y)."""
    return (28 - r) * U


# --- geometry ------------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def ring(self, pts):
        return [self.bm.verts.new(p) for p in pts]

    def skin(self, rings, mat, cap0=True, cap1=True):
        """Quads between consecutive rings (same count; a 1-vertex ring is a pole)."""
        bm = self.bm
        faces = []
        for a, b in zip(rings, rings[1:]):
            n = max(len(a), len(b))
            for i in range(n):
                j = (i + 1) % n
                if len(a) == 1:
                    vs = [a[0], b[j], b[i]]
                elif len(b) == 1:
                    vs = [a[i], a[j], b[0]]
                else:
                    vs = [a[i], a[j], b[j], b[i]]
                try:
                    faces.append(bm.faces.new(vs))
                except ValueError:
                    pass
        for r, flip in ((rings[0], False), (rings[-1], True)):
            if len(r) < 3 or (r is rings[0] and not cap0) or (r is rings[-1] and not cap1):
                continue
            c = sum((v.co for v in r), Vector()) / len(r)
            cv = bm.verts.new(c)
            n = len(r)
            for i in range(n):
                vs = [r[(i + 1) % n], r[i], cv] if not flip else [r[i], r[(i + 1) % n], cv]
                faces.append(bm.faces.new(vs))
        for f in faces:
            f.material_index = mat
        return faces


def sec_pts(xc, y, zc, rx, rzt, rzb=None, sides=24, power=2.0, phase=0.0):
    """A closed section in the XZ plane at Blender y: superellipse half-width rx, top rzt, bottom rzb
    (px). Returns Blender points. rx = 0 is a pole."""
    rzb = rzt if rzb is None else rzb
    if rx <= 1e-4:
        return [(xc, y, zc * U)]
    pts = []
    e = 2.0 / power
    for i in range(sides):
        a = phase + 2 * math.pi * i / sides
        c, s = math.cos(a), math.sin(a)
        x = math.copysign(abs(c) ** e, c) * rx
        z = math.copysign(abs(s) ** e, s) * (rzt if s > 0 else rzb)
        pts.append((xc + x * U, y, (zc + z) * U))
    return pts


# The shaft's centre per sprite row (pixel edge coordinate): the inner mask's centre, held within
# 10.75-11.75. The sprite draws its shaded right edge in ink one px further in on some rows, so a
# round section centred on column 11 would stand a px outside it there; a quarter / half px of
# lateral drift between sections is invisible in 3D.
CEN = {1: 11.0, 2: 11.0, 3: 11.0, 4: 11.5, 5: 11.5, 6: 11.5, 7: 11.75, 8: 11.75, 9: 11.5, 10: 11.0, 11: 11.25,
       12: 11.5, 20: 11.0, 21: 11.0, 22: 10.75, 23: 10.75, 24: 11.5, 25: 11.5, 26: 11.0, 27: 11.0, 28: 11.0,
       29: 10.75, 30: 11.5, 31: 10.75, 32: 11.5, 33: 11.5, 34: 11.5, 35: 11.5, 36: 11.5, 37: 11.0, 38: 10.75,
       39: 11.0, 40: 11.25, 41: 11.0, 42: 11.25, 43: 11.0, 44: 11.0, 45: 11.25, 46: 11.5, 47: 11.0, 48: 11.5,
       49: 11.5, 50: 11.5, 51: 11.5, 52: 11.5, 53: 11.5, 54: 11.5}


def cen(r):
    """The shaft's centre at row edge r: CEN for the row r lies in, blended over 0.3 px across row
    boundaries (rows missing from CEN take the nearest listed row)."""
    def row_c(i):
        keys = sorted(CEN)
        return CEN[min(keys, key=lambda k: (abs(k - i), k))]
    i = math.floor(r)
    f = r - i
    c = row_c(i)
    if f < 0.15:
        return c + (row_c(i - 1) - c) * (0.15 - f) / 0.3
    if f > 0.85:
        return c + (row_c(i + 1) - c) * (f - 0.85) / 0.3
    return c


def cen_s(r):
    """cen smoothed over +-0.8 rows: for thin straight parts (rods, rails) that must not zigzag."""
    return sum(cen(r + d) for d in [-0.8 + 0.2 * k for k in range(9)]) / 9


def bolts(M, row, rr, n, mat, depth=0.35, rad=0.32, phase=0.0, xc_e=None):
    """n bolt heads on a face facing the nose (-Y) at row edge `row`, on a circle of radius rr px."""
    c = cen(row) if xc_e is None else xc_e
    for k in range(n):
        a = phase + 2 * math.pi * k / n
        x, z = BX(c) + rr * math.cos(a) * U, (AXIS_Z + rr * math.sin(a)) * U
        tube(M, [(x, BY(row - depth), z), (x, BY(row + 0.12), z)], rad, mat, sides=6)


def revolve(M, stations, mat, sides=24, xc_e=None, zc=AXIS_Z, sz=1.0):
    """Round sections along the axis: stations are (row edge, radius px[, material]) top to bottom;
    a station's material holds from it to the next change (one continuous closed surface)."""
    rings, mats = [], []
    cur = mat
    for st in stations:
        r, rad = st[0], st[1]
        if len(st) > 2:
            cur = st[2]
        rings.append(M.ring(sec_pts(BX(cen(r) if xc_e is None else xc_e), BY(r), zc, rad, rad * sz, sides=sides)))
        mats.append(cur)
    faces = []
    for i in range(len(rings) - 1):
        faces += M.skin([rings[i], rings[i + 1]], mats[i], cap0=(i == 0), cap1=(i == len(rings) - 2))
    return faces


def smooth_stations(keys, step=0.25):
    """pchip through (row, r) keys, sampled every `step` rows (keys kept exactly)."""
    xs = [k[0] for k in keys]
    ys = [k[1] for k in keys]
    f = T.pchip(xs, ys)
    out = []
    for i in range(len(xs) - 1):
        n = max(1, int(round((xs[i + 1] - xs[i]) / step)))
        for k in range(n):
            x = xs[i] + (xs[i + 1] - xs[i]) * k / n
            out.append((x, max(0.0, f(x))))
    out.append((xs[-1], ys[-1]))
    return out


def tube(M, path, rad, mat, sides=12, cap=True):
    """A round tube along a path of Blender points with radius in px."""
    pts = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        a = t.cross(up).normalized()
        b = a.cross(t).normalized()
        rr = rad[i] if isinstance(rad, (list, tuple)) else rad
        rings.append(M.ring([p + (a * math.cos(2 * math.pi * k / sides) + b * math.sin(2 * math.pi * k / sides)) * rr * U
                             for k in range(sides)]))
    return M.skin(rings, mat, cap, cap)


def loft_y(M, secs, mat, xc_e, sides=24, power=2.0):
    """Sections (row, half width, top, bottom, zc) along Y about column edge xc_e."""
    rings = [M.ring(sec_pts(BX(xc_e), BY(r), zc, w, t, b, sides=sides, power=power)) for r, w, t, b, zc in secs]
    return M.skin(rings, mat)


def to_object(name, M, mats, coll):
    me = bpy.data.meshes.new(name)
    bmesh.ops.remove_doubles(M.bm, verts=M.bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(M.bm, faces=M.bm.faces)
    M.bm.normal_update()
    M.bm.to_mesh(me)
    M.bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


# --- the torpedo -----------------------------------------------------------------------------------

def merged_sprite():
    data = common.load_sprite(ROOT, PIECES[0])
    for name in PIECES[1:]:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def build(sprite, coll):
    tag = "nsh5a93"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.4, roughness=0.3),     # 0 body: turned satin metal (region medians 5)
        pal(4, metallic=0.6, roughness=0.38),    # 1 dark metal: grooves, spine core, cage core
        pal(6, metallic=0.4, roughness=0.28),    # 2 knob, bulb, collar band
        pal(7, metallic=0.8, roughness=0.32),    # 3 bright ring, couplings
        pal(9, metallic=0.85, roughness=0.25),   # 4 polished bars, top strut, tip
        pal(116, metallic=1.0, roughness=0.6, emission_strength=0.9),  # 5 glowing hoses (D126/D173)
        pal(3, metallic=0.6, roughness=0.55),    # 6 darkest recesses (pod nozzles, hose ports)
        pal(8, metallic=0.8, roughness=0.32),    # 7 spine top bar
        pal(124, metallic=1.0, roughness=0.55, emission_strength=2.2),  # 8 left hose's hot core (sprite 124)
        pal(119, metallic=1.0, roughness=0.55, emission_strength=1.0),  # 9 right hose's hot band
    ]
    BODY, DARK, MID, BRIGHT, POLISH, HOSE, RECESS, SPINE, HOT_L, HOT_R = range(10)
    M = Mesh()
    S = 32

    # Rear: tail dome, band, flange ring (rows 0.9-8.9).
    # a full (superelliptic) dome: rows 1-3 are already 2-3 px wide
    dome = [(0.95, 0.0)] + [(4.0 - 3.05 * math.cos(a) ** 0.8, 3.25 * math.sin(a) ** 0.8) for a in
                            [math.radians(d) for d in range(10, 91, 10)]]
    revolve(M, dome + [(4.35, 3.25), (4.45, 3.0), (4.6, 3.0), (4.7, 3.3),   # groove before the flange
                       (4.85, 4.9), (5.05, 5.45), (5.9, 5.5), (5.95, 5.25), (6.1, 5.25), (6.15, 5.5),
                       (7.0, 5.45), (7.7, 5.0), (8.35, 4.3), (8.85, 3.2), (9.0, 2.6),
                       # neck (9-12.6) with a machined groove
                       (9.2, 2.45), (10.2, 2.4), (10.3, 2.15), (10.6, 2.15), (10.7, 2.4), (11.9, 2.55),
                       (12.6, 3.4)], BODY, S)
    # Core inside the hood, tapering into the spine below it (rows 12.6-20.2).
    revolve(M, [(12.6, 3.0), (17.4, 3.0), (18.4, 2.7), (19.4, 2.0), (20.2, 1.5)], BODY, S)

    # Motor hood: a faired shell over the core (rows 12.4-17.7), wide superellipse sections.
    hood = [(12.35, 2.4, 2.4, 2.4), (12.8, 3.4, 3.2, 2.9), (13.4, 4.5, 3.9, 3.2), (14.2, 5.7, 4.5, 3.4),
            (14.55, 6.15, 4.62, 3.4), (14.62, 6.0, 4.45, 3.4), (14.75, 6.2, 4.62, 3.4),  # panel seam
            (15.5, 7.2, 4.9, 3.5), (16.5, 7.75, 5.0, 3.5), (17.1, 7.85, 4.85, 3.5), (17.5, 7.6, 4.3, 3.4),
            (17.75, 6.7, 3.4, 3.0)]
    loft_y(M, [(r, w, t, b, AXIS_Z) for r, w, t, b in hood], BODY, HOOD_E, sides=40, power=2.6)

    # Dorsal ridge along the hood's crown, and bolt rings on the flange's and collar's front faces.
    hf = T.pchip([h[0] for h in hood], [h[2] for h in hood])
    tube(M, [(BX(HOOD_E), BY(r), (AXIS_Z + hf(r) - 0.12) * U) for r in [12.9 + 0.3 * k for k in range(15)]],
         0.42, MID, sides=10)
    bolts(M, 8.0, 4.25, 12, BRIGHT, phase=math.pi / 12)
    bolts(M, 26.8, 4.55, 12, BRIGHT, phase=math.pi / 12)
    # Side pods (cols 3-5 and 17-19, rows 14-20), slung a little low on the hood's flanks.
    for side in (-1, 1):
        xc = HOOD_E + side * 7.0
        zc = AXIS_Z - 0.6
        revolve(M, [(14.7, 0.0), (14.9, 0.6), (15.5, 0.85), (16.5, 0.85), (17.0, 1.2), (17.3, 1.55), (18.8, 1.55), (18.95, 1.35),
                    (19.05, 1.35), (19.15, 1.5), (19.6, 1.45), (19.95, 1.15)], BODY, 16, xc_e=xc, zc=zc)
        # nozzle face at the pod's front end
        revolve(M, [(19.9, 0.95), (20.0, 0.88), (20.03, 0.6), (20.03, 0.0)], RECESS, 16, xc_e=xc, zc=zc)
    # Lower cross frame between the pods under the hoses (rows 17.5-19.9).
    xs = [HOOD_E - 7.0, HOOD_E + 7.0]
    # a faired bar: lofted along X, its section an ellipse in YZ
    bar_rings = []
    for x in [xs[0] + (xs[1] - xs[0]) * k / 10 for k in range(11)]:
        pts = []
        for i in range(16):
            a = 2 * math.pi * i / 16
            pts.append((BX(x), BY(18.3) + math.cos(a) * 1.0 * U, (AXIS_Z - 1.9 + math.sin(a) * 1.3) * U))
        bar_rings.append(M.ring(pts))
    M.skin(bar_rings, DARK)

    # Hoses: out of the hood's front lip through couplings, curving in and down into the collar.
    for side in (-1, 1):
        def P(r, e_off, z):
            # below the hood the pair centres on 11.4 (the sprite's right hose edge is ink)
            c = HOOD_E - min(1.0, max(0.0, (r - 18.5) / 1.5)) * 0.2
            return (BX(c + side * e_off), BY(r), (AXIS_Z + z) * U)
        path = [P(15.8, 4.5, 2.2), P(16.8, 4.5, 2.0), P(17.6, 4.35, 1.75), P(18.5, 3.9, 1.5), P(19.4, 3.25, 1.3),
                P(20.05, 2.05, 1.15), P(21.3, 2.05, 1.05), P(22.3, 2.05, 0.85), P(22.9, 1.2, -0.5), P(23.5, 0.6, -1.3), P(24.3, 0.4, -1.6)]
        # the pair dives under the spine into one manifold in the collar's rear face (row 23 shows no hose)
        # the shoulder run is as wide as the sprite's 3 px red blocks, narrowing below the bend
        # (the right hose's shoulder run sits a quarter px further out and a little slimmer: the sprite
        # leaves a gap between it and the spine on rows 17-18)
        if side > 0:
            path = [(x + (0.25 * U if i < 4 else 0.0), y, z) for i, (x, y, z) in enumerate(path)]
            radii = [1.2, 1.2, 1.15, 1.4, 1.3, 1.05, 0.95, 0.92, 0.85, 0.8, 0.8]
        else:
            radii = [1.35, 1.35, 1.4, 1.5, 1.3, 1.1, 1.0, 0.95, 0.85, 0.8, 0.8]
        tube(M, path, radii, HOSE, sides=16)
        # couplings: at the hood lip
        tube(M, [P(17.15, 4.5, 1.92), P(17.75, 4.33, 1.72)], 1.8, BRIGHT, sides=16)
        # the hot core showing through a heat window at the bend (the sprite's yellow on the left hose)
        win = [P(18.55, 3.86, 1.49), P(18.95, 3.6, 1.41), P(19.35, 3.29, 1.31)]
        if side > 0:
            win[0] = (win[0][0] + 0.03 * U, win[0][1], win[0][2])
        tube(M, win, [radii[3] + 0.06, (radii[3] + radii[4]) / 2 + 0.06, radii[4] + 0.06],
             HOT_L if side < 0 else HOT_R, sides=16)
    # Spine between the hoses: dark core and a polished top bar (cols 10-12, rows 17.5-23.9).
    revolve(M, [(20.0, 1.5), (23.9, 1.55)], DARK, 16)
    tube(M, [(BX(cen_s(r)), BY(r), (AXIS_Z + z) * U) for r, z in ((17.2, 2.0), (18.6, 1.55), (20.5, 1.25), (24.1, 1.25))],
         0.55, SPINE, sides=10)

    # Collar (rows 23.7-27).
    # Collar (23.7-27), neck, ring (row 30), short neck, ribbed sleeve (31.6-37.7): one surface.
    revolve(M, [(23.8, 1.6, MID), (23.9, 4.7), (24.1, 5.35), (24.75, 5.45), (24.82, 5.15), (24.98, 5.15),
                (25.05, 5.45), (25.85, 5.45), (25.92, 5.15), (26.08, 5.15), (26.15, 5.4), (26.6, 5.2),
                (26.95, 4.4), (27.1, 3.0, BODY), (28.6, 2.9), (28.95, 1.6), (29.2, 1.3), (29.8, 1.3, BRIGHT),
                (29.92, 4.0), (30.05, 4.5), (30.85, 4.5), (30.97, 3.8), (31.02, 1.38, DARK), (31.85, 1.38, BODY),
                (31.97, 3.2), (32.1, 3.5), (33.1, 3.5), (33.2, 3.15), (33.4, 3.15), (33.5, 3.5),
                (34.6, 3.5), (34.7, 3.15), (34.9, 3.15), (35.0, 3.45), (35.7, 3.35), (36.25, 2.75),
                (36.9, 2.35), (37.4, 2.05)], MID, S)
    # Drive coupling (rows 37.4-41.4): a waisted dark shaft (the sprite's hourglass, waist at row 38)
    # with a polished rod along its top in a dark slot and a rail down each side.
    prof = [(37.4, 2.05), (37.8, 1.75), (38.4, 1.5), (39.0, 1.6), (39.6, 2.0), (40.5, 2.45), (41.4, 2.75)]
    revolve(M, prof, DARK, S)
    f = T.pchip([a for a, _ in prof], [b for _, b in prof])
    rows = [37.3 + 0.35 * k for k in range(13)]
    tube(M, [(BX(10.9), BY(r), (AXIS_Z + f(r) - 0.05) * U) for r in rows], 0.5, POLISH, sides=10)
    for side in (-1, 1):
        tube(M, [(BX(10.95 + side * (f(r) - 0.6)), BY(r), (AXIS_Z + 0.2) * U) for r in rows], 0.5, BODY, sides=10)
    # Bearing knob (rows 41.6-46.3).
    knob = smooth_stations([(41.2, 2.6), (41.45, 2.95), (42.2, 3.4), (43.0, 3.9), (44.2, 3.92),
                            (45.0, 3.7), (45.7, 3.1), (46.15, 2.35)], 0.2)
    knob = [(r, rad - (0.25 if 43.45 <= r <= 43.75 else 0.0)) for r, rad in knob]  # equator seam
    revolve(M, knob, MID, S)
    # Drill bulb (rows 46.1-55.1): an ogive, a seam ring and a hardened tip.
    bulb = smooth_stations([(46.1, 2.35), (46.7, 2.8), (47.5, 3.05), (48.4, 3.5), (50.3, 3.55),
                            (51.3, 2.85), (52.3, 2.4), (53.2, 1.75)], 0.2)
    bulb = [(r, rad - (0.22 if 48.85 <= r <= 49.05 else 0.0)) for r, rad in bulb]
    revolve(M, bulb, MID, S)
    revolve(M, smooth_stations([(53.2, 1.75), (53.25, 1.62), (54.0, 1.0), (54.6, 0.45), (55.05, 0.0)], 0.15),
            MID, S)  # the tip: the sprite's greys 3-7, a separate cone behind a seam

    # Drill flights: three raised helical cutting edges on the bulb's front half (rows 49.4-54.5).
    bf = T.pchip([a for a, _ in bulb], [b for _, b in bulb])
    tf = T.pchip([53.2, 54.0, 54.6, 55.05], [1.75, 1.0, 0.45, 0.0])
    for k in range(3):
        pts = []
        for i in range(19):
            r = 49.4 + (54.4 - 49.4) * i / 18
            rad = (bf(r) if r <= 53.2 else tf(r)) - 0.12
            a = 2 * math.pi * k / 3 + math.radians(250) * i / 18
            pts.append((BX(cen_s(r)) + rad * math.cos(a) * U, BY(r), (AXIS_Z + rad * math.sin(a)) * U))
        tube(M, pts, [0.3] * 16 + [0.25, 0.2, 0.15], MID, sides=8)

    obj = to_object(NAME, M, mats, coll)
    return obj, mats


def split_open(obj, layout):
    """common.split_assembly without filling the cut, for the outline shell (no wall across the seam)."""
    result = {}
    coll = obj.users_collection[0]
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name + "_outline")
        bm.to_mesh(mesh)
        bm.free()
        for mat in obj.data.materials:
            mesh.materials.append(mat)
        piece = bpy.data.objects.new(name + "_outline", mesh)
        coll.objects.link(piece)
        result[name] = piece
    return result


def assemble():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    bpy.context.view_layer.update()
    sprite = merged_sprite()
    obj, mats = build(sprite, coll)
    # Outline shell from the sealed pre-cull copy; islands="outer" (D189).
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    shell = common.outline_shell(sealed, coll, voxel=0.012, faces=3000, smooth=4, inside=0.004, islands="outer")
    bpy.data.objects.remove(sealed, do_unlink=True)
    T.cull_hidden(obj, grid=4, ndirs=40)
    lay = [(n, cx - CX0, cy - CY0) for n, cx, cy in LAYOUT]
    bodies = common.split_assembly(obj, lay)
    shells = split_open(shell, lay)
    out = []
    for n, cx, cy in lay:
        b, sh = bodies[n], shells[n]
        b.data.shade_smooth()
        b.data.set_sharp_from_angle(angle=math.radians(35))
        sh.data.shade_smooth()
        sh["tyrian_outline"] = True
        assert len(sh.data.polygons) > 0, f"{n}_outline has no mesh"
        # place both pieces back at their layout places for the design glb
        b.location = (cx / 12, -cy / 12, 0)
        sh.parent = b
        out += [b, sh]
        tris = sum(len(p.vertices) - 2 for p in b.data.polygons)
        print(f"PIECE {n}: {tris} tris, outline {len(sh.data.polygons)} faces")
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.objects.remove(shell, do_unlink=True)
    bpy.context.view_layer.update()
    return sprite, out, None, None


# --- review (only with --review) ----------------------------------------------------------------

def review(sprite, objs, outdir):
    import re
    import sprite_mask as SM
    outdir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in bpy.data.objects:
        o.hide_render = o not in objs
    bodies = [o for o in objs if not o.get("tyrian_outline")]
    shells = [o for o in objs if o.get("tyrian_outline")]

    def cam(loc, look, ortho=None, fov=None, top=False, up="Y"):
        d = bpy.data.cameras.new("cam")
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.sensor_fit = "VERTICAL"
            d.angle_y = math.radians(fov)
        c = bpy.data.objects.new("cam", d)
        scene.collection.objects.link(c)
        c.location = loc
        c.rotation_euler = (0, 0, 0) if top else (Vector(look) - Vector(loc)).to_track_quat("-Z", up).to_euler()
        return c

    def shoot(c, path, rx, ry):
        scene.camera = c
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(c, do_unlink=True)

    def workbench(flat):
        try:
            scene.render.engine = "BLENDER_WORKBENCH"
        except TypeError:
            pass
        sh = scene.display.shading
        sh.light = "FLAT" if flat else "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_cavity = not flat
        sh.show_shadows = False
        scene.view_settings.view_transform = "Standard"
        scene.render.film_transparent = True
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"

    k = 8
    W, H = 24, 56
    ext = H * U
    for s in shells:
        s.hide_render = True
    workbench(True)
    shoot(cam((0, 0, 20), (0, 0, 0), ortho=ext, top=True), outdir / "top_flat.png", W * k, H * k)
    m = SM.masks(*SM.load(NAME))
    top = SM.read_png_mask(outdir / "top_flat.png")
    res = SM.measure(m, top)
    print("MEASURE", json.dumps(res))
    # per-region palette index under each sprite pixel (top-down ray cast) vs the sprite
    dg = bpy.context.evaluated_depsgraph_get()
    idx, _ = SM.load(NAME)
    hits = {}
    heights = []
    for r in range(H):
        for c in range(W):
            hit, loc, _n, face, o, _m = scene.ray_cast(dg, Vector((BX(c + 0.5), BY(r + 0.5), 5)), Vector((0, 0, -1)))
            if hit and o in bodies:
                ev = o.evaluated_get(dg)
                mi = ev.data.polygons[face].material_index
                g = re.match(r"pal_(\d+)", o.data.materials[mi].name)
                hits[(r, c)] = int(g.group(1)) if g else -1
                heights.append(loc.z / U)
    bands = {"cap": (0, 5), "flange": (5, 9), "neck": (9, 13), "hood": (13, 17), "hoses+spine": (17, 24),
             "collar": (24, 27), "neck2": (27, 30), "ring": (30, 31), "ribbed": (31, 38), "cage": (38, 42),
             "knob": (42, 46), "bulb": (46, 56)}
    import statistics as st
    lines = []
    for nm, (r0, r1) in bands.items():
        sv = sorted(idx[r][c] for r in range(r0, r1) for c in range(W) if idx[r][c] >= 0)
        mv = sorted(hits[(r, c)] for r in range(r0, r1) for c in range(W) if (r, c) in hits)
        sg = [v for v in sv if 2 < v < 12]
        sr = [v for v in sv if v >= 100]
        mg = [v for v in mv if v < 100]
        mr = [v for v in mv if v >= 100]
        lines.append(f"{nm:12s} sprite grey {st.median(sg) if sg else '-'} red {st.median(sr) if sr else '-'} | "
                     f"model grey {st.median(mg) if mg else '-'} red {st.median(mr) if mr else '-'}")
    print("REGIONS\n" + "\n".join(lines))
    (outdir / "measure.json").write_text(json.dumps({"measure": res, "regions": lines,
                                                     "zmax_px": max(heights) if heights else 0}, indent=1))
    for s in shells:
        s.hide_render = False
    # lit views (game-like EEVEE: env + sun from the camera's left side)
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "EEVEE" in e)
    world = scene.world or bpy.data.worlds.new("game")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.45, 0.55, 1.0)
    bg.inputs[1].default_value = 1.0
    sd = bpy.data.lights.new("sun", "SUN")
    sd.energy = 3.0
    sun = bpy.data.objects.new("sun", sd)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-6, -8.4, 20)).normalized().to_track_quat("Z", "Y").to_euler()
    scene.render.film_transparent = True
    for s in shells:  # the outline shell is only for the game's ink pass
        s.hide_render = True
    zc = AXIS_Z * U
    shoot(cam((0, 0, 20), (0, 0, 0), ortho=ext, top=True), outdir / "top_lit.png", W * k, H * k)
    span = ext * 1.15
    shoot(cam((20, 0, zc), (0, 0, zc), ortho=span, up="Y"), outdir / "side.png", 720, 360)
    shoot(cam((0, -20, zc), (0, 0, zc), ortho=span * 0.5, up="Y"), outdir / "front.png", 360, 360)
    shoot(cam((0, 20, zc), (0, 0, zc), ortho=span * 0.5, up="Y"), outdir / "rear.png", 360, 360)
    d = 7.5
    shoot(cam((d * 0.55, -d * 0.6, d * 0.7), (0, 0, zc), fov=35, up="Y"), outdir / "q_front.png", 480, 480)
    shoot(cam((-d * 0.6, d * 0.55, d * 0.7), (0, 0, zc), fov=35, up="Y"), outdir / "q_rear.png", 480, 480)
    tilt = math.radians(32)
    shoot(cam((0, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0), fov=35), outdir / "game.png", 480, 480)
    cu = cam((0, 0, -20), (0, 0, 0), ortho=ext * 1.05, top=True)
    cu.rotation_euler = (math.pi, 0, 0)
    shoot(cu, outdir / "under.png", 240, 480)
    tris = sum(len(p.vertices) - 2 for o in bodies for p in o.data.polygons)
    print(f"TRIS {tris}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite, objs, whole, shell = assemble()
    if "--out" in argv:
        common.export_glb(objs, argv[argv.index("--out") + 1])
    if "--review" in argv:
        outdir = Path(argv[argv.index("--review") + 1])
        review(sprite, objs, outdir)
    if "--no-export" in argv:
        return
    # each piece at its own origin with its outline shell: the game's sprite-model contract
    for n, b, sh in zip(PIECES, objs[0::2], objs[1::2]):
        sh.parent = None
        for o in (b, sh):
            o.location = (0, 0, 0)
        bpy.context.view_layer.update()
        data = common.load_sprite(ROOT, n)
        common.export_sprite_model(ROOT, [b, sh], f"enemies/{n}", data["sprites"])


if __name__ == "__main__":
    main()
