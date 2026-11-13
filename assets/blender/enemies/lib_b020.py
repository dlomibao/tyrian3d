"""Shared builder for the panel satellites newshl 7/9/45/47 (assembly-newshl-45) and 11/13/49/51 (assembly-newshl-49, the exact
left-right mirror) and their twin-disc spindles newshl-24 and newshl-34 (the mirror). Imported by assembly-newshl-45.py,
assembly-newshl-49.py, newshl-24.py and newshl-34.py, each of which exports only its own models (see run_station / run_spindle).

Design notes (written for the station and spindle of newshl-45/24; mirror=True flips X):

What it is (TIME WAR, 4.17): space stations sliding down the screen at the screen edges. Types
659-668 drift (0, +1) on the top layer; newshl-24 rides rigid with newshl-45 at (dx -24, dy +14).
In play (TIME WAR capture, skip 350) the spindle's axle lines up with the station's core: it sits
straight left of the end wheel, its flange against the wheel's hub, and the beam the two stations
fire at each other leaves its nose. So it is the station's end spindle, built as a separate model
(its own sprite) that meets the wheel. Nothing here is ground: everything floats, closed hard surface.

Station (48 x 56 px, four 24 x 28 pieces). A turned core lies along X on the axis row 27.5, its axis
at z = 0, and every arm and panel lies in that mid-plane:
  core, left to right   end wheel (r 7.5, chamfered face, hub boss, bolt ring) | groove ring |
                        drum (r 5.6) | glowing blue coil (r 3.4, two retaining rings) | sleeve
                        (r 4.6, two panel grooves) | collar (r 7.5, squared section, mid groove) |
                        neck (r 4.6) | red emitter cone | red rod through a dark clamp block into
                        the right panel's hub
  fork tines            above and below the emitter, from the neck to the clamp block
  shoulders             saddle plates across the collar's north and south, carrying
  bars                  a rail along the core each side (r 1.6), its left end bending in as a pipe
                        to the wheel's rim, and
  struts                a diagonal strut from each shoulder to a corner panel
  panels (5)            chamfered modules with a raised rim, recessed grooves and raised cells:
                        north and south (2 x 1 cells) on arms from the rails, up-right and
                        down-right (2 x 3) on the struts, and the right one (2 x 1 + cross rib)
                        on the rod
The lower half is the upper half mirrored; its regions keep the sprite's darker indices, one or two
steps up from the sprite's darkest (drawn shadow is lighting; art rule 2), see PAL.

Spindle (newshl 24, 24 x 28 px), its own object, axle along X at z = 0: nose, body with a groove,
two full-height discs with a dark web between them and red lamps on the web's north and south rim,
a narrower shaft, an end flange, and dark clamp blocks north and south of that shaft with red strips.

Units: authored in sprite px. Station: c (0..48), r (0..56) pixel edges of the assembly block,
Blender X = (c - 24) / 12, Y = (28 - r) / 12, Z = z / 12; the origin is screen (286, -3), the same
CENTRE as the current script, so the pieces keep their layout offsets. Spindle: its own 24 x 28 grid,
X = (c - 12) / 12, Y = (14 - r) / 12, placed at its screen offset (-36, 0) in the scratch glb.

Run a wrapper script: blender --background --python assets/blender/enemies/assembly-newshl-45.py -- [--measure DIR] [--views DIR] [--no-bake]
A normal build exports public/models + src/render/spriteModels; --measure/--views write review output only where asked.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector


def _find_repo():
    """The repo holding assets/blender/common.py, found from this file's own location."""
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("assets/blender/common.py not found above " + str(here))


WT = _find_repo()
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask  # noqa: E402

ROOT = WT
NAME = "assembly-newshl-45"
TAG = "nshl45"
PIECES = ["newshl-7", "newshl-9", "newshl-45", "newshl-47"]
SPINDLE = "newshl-24"
CENTRE = (286, -3)
MIRROR = False


def configure(name, pieces, centre, spindle, mirror):
    global NAME, TAG, PIECES, CENTRE, SPINDLE, MIRROR
    NAME, PIECES, CENTRE, SPINDLE, MIRROR = name, pieces, centre, spindle, mirror
    TAG = "nshl" + name.split("-")[-1]

U = 1 / 12
AXIS = 27.5

# Region palette indices (sprite medians over each part with the darkest shading and brightest
# sheen left out). Lower half: the sprite draws it in shadow; it keeps darker indices.
PAL = dict(
    wheel=9, groove=4, drum=8, coil=55, coil_ring=9, sleeve=9, collar=8, collar_groove=4, neck=5,
    emitter=116, rod=115, clamp=3, clamp_tab_n=6, clamp_tab_s=4, tine_n=5, tine_s=4, hub=5,
    shoulder_n=5, shoulder_s=3, bar_n=7, bar_s=5, pipe_n=6, pipe_s=4, arm_n=5, arm_s=4, strut_n=6, strut_s=4,
    panel_n=(9, 8, 5), panel_s=(6, 4, 2),          # (rim, cells, grooves)
    diag_n=(6, 5, 2), diag_s=(4, 3, 1),
    panel_e=(6, 4, 2), rib_e=8,
    bolt=6,
)
SPAL = dict(nose=8, body=8, body_groove=5, shaft=7, disc=8, web=2, lamp_n=116, lamp_s=114, tail=7, flange=8,
            clamp=2, red_n=114, red_s=113)

FINISH = {  # metallic, roughness, emission
    "polish": (0.45, 0.3, 0.0),   # turned core parts: satin polished metal (sheen from the game's lights)
    "metal": (0.5, 0.42, 0.0),    # rails, struts, brackets
    "paint": (0.3, 0.55, 0.0),    # panel modules
    "dark": (0.3, 0.6, 0.0),
    "glow": (1.0, 0.9, 1.0),      # D126/D173: glow on metallic 1, rough
    "lamp": (1.0, 0.9, 1.2),
    "redstrip": (0.3, 0.6, 0.6),
}


# ---------------------------------------------------------------------------------------------
# Mesh builder (px coordinates in, Blender units out)
# ---------------------------------------------------------------------------------------------

class Builder:
    def __init__(self, to_world):
        self.V, self.F, self.FM = [], [], []
        self.W = to_world
        self.mat_keys = []

    def slot(self, pal, finish):
        k = (pal, finish)
        if k not in self.mat_keys:
            self.mat_keys.append(k)
        return self.mat_keys.index(k)

    def v(self, c, r, z):
        self.V.append(self.W(c, r, z))
        return len(self.V) - 1

    def vw(self, p):
        self.V.append(tuple(p))
        return len(self.V) - 1

    def f(self, idx, s):
        self.F.append(tuple(idx))
        self.FM.append(s)


def W_station(c, r, z):
    return ((24 - c if MIRROR else c - 24) * U, (28 - r) * U, z * U)


def W_spindle(c, r, z):
    return ((12 - c if MIRROR else c - 12) * U, (14 - r) * U, z * U)


def _rings_faces(b, rings, s, cap0=True, cap1=True):
    n = len(rings[0])
    for a, c in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            b.f((a[i], a[j], c[j], c[i]), s)
    if cap0:
        b.f(list(reversed(rings[0])), s)
    if cap1:
        b.f(rings[-1], s)


def revolve_x(b, secs, axis_r, s, z0=0.0, sides=24, power=2.0, cap0=True, cap1=True):
    """A turned part along X: secs are (c, radius px) or (c, radius across, radius up); section a
    superellipse of `power` (2 = round)."""
    rings = []
    for sec in secs:
        c, ry = sec[0], sec[1]
        rz = sec[2] if len(sec) > 2 else ry
        ring = []
        for k in range(sides):
            t = 2 * math.pi * (k + 0.5) / sides
            ct, st = math.cos(t), math.sin(t)
            q = (abs(ct) ** power + abs(st) ** power) ** (-1 / power)
            ring.append(b.v(c, axis_r - ry * ct * q, z0 + rz * st * q))
        rings.append(ring)
    _rings_faces(b, rings, s, cap0, cap1)


def _inset_xy(poly, d):
    """Inset a convex CCW polygon (Blender XY) by d."""
    n = len(poly)
    lines = []
    for i in range(n):
        p, q = Vector(poly[i]), Vector(poly[(i + 1) % n])
        e = (q - p).normalized()
        nrm = Vector((-e.y, e.x))
        lines.append((p + nrm * d, e))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        den = d1.x * d2.y - d1.y * d2.x
        if abs(den) < 1e-9:
            out.append(tuple(p2))
            continue
        t = ((p2.x - p1.x) * d2.y - (p2.y - p1.y) * d2.x) / den
        out.append(tuple(p1 + d1 * t))
    return out


def _ccw(poly):
    a = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
            for i in range(len(poly)))
    return poly if a > 0 else list(reversed(poly))


def prism(b, poly_px, z0, z1, s, ch=0.35, ch_bottom=None, top_s=None):
    """A chamfered prism: poly in px (c, r), convex; z in px. Chamfer ch px on the top edges and
    ch_bottom (default ch) on the bottom ones."""
    chb = ch if ch_bottom is None else ch_bottom
    poly = _ccw([b.W(c, r, 0)[:2] for c, r in poly_px])
    rings = []
    spec = []
    if chb > 0:
        spec += [(_inset_xy(poly, chb * U), z0), (poly, z0 + chb)]
    else:
        spec += [(poly, z0)]
    if ch > 0:
        spec += [(poly, z1 - ch), (_inset_xy(poly, ch * U), z1)]
    else:
        spec += [(poly, z1)]
    for pts, z in spec:
        rings.append([b.vw((x, y, z * U)) for x, y in pts])
    n = len(poly)
    for a, c in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            b.f((a[i], a[j], c[j], c[i]), s)
    b.f(list(reversed(rings[0])), s)
    b.f(rings[-1], top_s if top_s is not None else s)


def rect(c0, r0, c1, r1, cut=0.0):
    if cut <= 0:
        return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]
    k = cut
    return [(c0 + k, r0), (c1 - k, r0), (c1, r0 + k), (c1, r1 - k), (c1 - k, r1), (c0 + k, r1), (c0, r1 - k), (c0, r0 + k)]


def tube(b, path_px, rad, s, sides=10, caps=True):
    """A tube along a path of (c, r, z) px points, radius rad px (or a list of radii)."""
    pts = [Vector(b.W(*p)) for p in path_px]
    rads = rad if isinstance(rad, (list, tuple)) else [rad] * len(pts)
    rings = []
    for i, p in enumerate(pts):
        a = pts[max(0, i - 1)]
        c = pts[min(len(pts) - 1, i + 1)]
        d = (c - a).normalized()
        ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(ref).normalized()
        w = d.cross(u).normalized()
        R = rads[i] * U
        rings.append([b.vw(p + R * (math.cos(2 * math.pi * (k + 0.5) / sides) * u +
                                    math.sin(2 * math.pi * (k + 0.5) / sides) * w)) for k in range(sides)])
    _rings_faces(b, rings, s, caps, caps)


def bolt(b, c, r, z, s, rad=0.45, h=0.35, axis="z"):
    """A hex bolt head: on a face pointing +Z (axis z) or -X (axis x)."""
    if axis == "z":
        poly = [(c + rad * math.cos(math.pi / 3 * k), r + rad * math.sin(math.pi / 3 * k)) for k in range(6)]
        prism(b, poly, z - 0.1, z + h, s, ch=0.08, ch_bottom=0)
    else:
        ring0, ring1 = [], []
        for k in range(6):
            t = math.pi / 3 * k
            ring0.append(b.v(c + 0.1, r + rad * math.cos(t), z + rad * math.sin(t)))
        for k in range(6):
            t = math.pi / 3 * k
            ring1.append(b.v(c - h, r + rad * 0.8 * math.cos(t), z + rad * 0.8 * math.sin(t)))
        _rings_faces(b, [ring0, ring1], s)


def panel(b, centre, along, L, Wd, cols, grid, z0=-1.2, z1=1.2, rim=1.3, div=0.8, finish="paint",
          rib=None, hub=None):
    """A panel module: a chamfered box L (along) x Wd (across) px centred on `centre` (c, r) with
    `along` a (dc, dr) direction, top at z1; a raised rim `rim` px wide standing 0.45 px proud, a
    groove floor 0.35 px below the rim top's base, and raised cells (grid = (across, along)) between
    grooves `div` px wide. cols = (rim, cells, grooves) palette indices."""
    cc, rr = centre
    dl = Vector(along).normalized()
    da = Vector((-dl.y, dl.x))

    def P(a, w):
        q = Vector((cc, rr)) + dl * a + da * w
        return (q.x, q.y)

    def R(a0, a1, w0, w1):
        return [P(a0, w0), P(a1, w0), P(a1, w1), P(a0, w1)]

    rim_i, cell_i, groove_i = cols
    s_rim = b.slot(rim_i, finish)
    s_cell = b.slot(cell_i, finish)
    s_gr = b.slot(groove_i, "dark")
    hl, hw = L / 2, Wd / 2
    ztop = z1
    zfloor = z1 - 0.75
    # Body up to the groove floor, the rim's sides and chamfer.
    prism(b, R(-hl, hl, -hw, hw), z0, zfloor, s_rim, ch=0.0, ch_bottom=0.4, top_s=s_gr)
    # Rim bars (chamfered) on the body's edge.
    for a0, a1, w0, w1 in ((-hl, hl, -hw, -hw + rim), (-hl, hl, hw - rim, hw),
                           (-hl, -hl + rim, -hw + rim, hw - rim), (hl - rim, hl, -hw + rim, hw - rim)):
        prism(b, R(a0, a1, w0, w1), zfloor - 0.05, ztop, s_rim, ch=0.3, ch_bottom=0)
    # Cells.
    nu, nv = grid
    iu0, iu1 = -hw + rim + div * 0.6, hw - rim - div * 0.6
    iv0, iv1 = -hl + rim + div * 0.6, hl - rim - div * 0.6
    cu = (iu1 - iu0 - div * (nu - 1)) / nu
    cv = (iv1 - iv0 - div * (nv - 1)) / nv
    for i in range(nu):
        for j in range(nv):
            w0 = iu0 + i * (cu + div)
            a0 = iv0 + j * (cv + div)
            prism(b, R(a0, a0 + cv, w0, w0 + cu), zfloor - 0.05, ztop - 0.12, s_cell, ch=0.18, ch_bottom=0)
    if rib is not None:  # a raised cross rib at along-offset rib[0], palette rib[1]
        a = rib[0]
        prism(b, R(a - 0.5, a + 0.5, -hw + rim * 0.5, hw - rim * 0.5), zfloor - 0.05, ztop + 0.1,
              b.slot(rib[1], "metal"), ch=0.2, ch_bottom=0)
    # Corner bolts on the rim.
    for a in (-hl + rim / 2, hl - rim / 2):
        for w in (-hw + rim / 2, hw - rim / 2):
            c, r = P(a, w)
            bolt(b, c, r, ztop, b.slot(PAL["bolt"], "metal"), rad=0.35, h=0.2)


# ---------------------------------------------------------------------------------------------
# Station
# ---------------------------------------------------------------------------------------------

def build_station(b):
    S = b.slot
    A = AXIS
    pol = lambda k: S(PAL[k], "polish")  # noqa: E731
    met = lambda k: S(PAL[k], "metal")  # noqa: E731

    # --- Core (turned, axis r 27.5, z 0)
    # End wheel: a heavy chamfered face (the sprite's c0 is only 5 px tall), rim r 7.5.
    revolve_x(b, [(-0.05, 2.4), (0.45, 3.4), (0.95, 6.6), (1.35, 7.5), (3.9, 7.5), (4.35, 7.1), (4.85, 6.4)],
              A, pol("wheel"), sides=32)
    # Hub boss on the wheel's face and a bolt ring.
    revolve_x(b, [(-0.3, 1.1), (-0.1, 1.5), (0.4, 1.5)], A, S(6, "polish"), sides=16)
    for k in range(8):
        t = 2 * math.pi * (k + 0.5) / 8
        bolt(b, 0.75, A - 4.6 * math.cos(t), 4.6 * math.sin(t), S(PAL["bolt"], "metal"), rad=0.4, h=0.3, axis="x")
    revolve_x(b, [(4.7, 4.7), (5.15, 4.7)], A, S(PAL["groove"], "metal"), sides=24)
    # Drum.
    revolve_x(b, [(5.0, 5.0), (5.4, 5.6), (8.5, 5.6), (8.95, 5.0)], A, pol("drum"), sides=28)
    # Glowing coil with retaining rings.
    revolve_x(b, [(8.8, 2.9), (13.0, 2.9)], A, S(PAL["coil"], "glow"), sides=20)
    for c0 in (8.85, 12.55):
        revolve_x(b, [(c0, 3.0), (c0 + 0.1, 3.35), (c0 + 0.5, 3.35), (c0 + 0.6, 3.0)], A, pol("coil_ring"), sides=20)
    # Sleeve with two panel grooves.
    revolve_x(b, [(12.9, 4.0), (13.3, 4.6), (15.0, 4.6), (15.1, 4.25), (15.35, 4.25), (15.45, 4.6),
                  (17.0, 4.6), (17.1, 4.25), (17.35, 4.25), (17.45, 4.6), (18.7, 4.6), (19.1, 4.3)],
              A, pol("sleeve"), sides=24)
    # Lead-in cone from the sleeve up to the collar.
    revolve_x(b, [(15.8, 4.5), (16.0, 5.3), (17.1, 6.25), (19.1, 6.45)], A, pol("collar"), sides=32)
    # Collar: squared section, a circumferential groove at its middle.
    revolve_x(b, [(18.9, 6.4), (19.35, 7.5), (22.2, 7.5), (22.3, 7.1), (22.75, 7.1), (22.85, 7.5),
                  (25.6, 7.5), (26.05, 6.4)], A, pol("collar"), sides=32, power=2.6)
    # Neck.
    revolve_x(b, [(25.9, 4.6), (28.3, 4.6)], A, S(PAL["neck"], "polish"), sides=20)
    # Red emitter cone and rod.
    revolve_x(b, [(28.1, 3.2), (28.7, 3.2), (30.4, 2.6), (31.0, 1.6), (31.3, 0.8)], A,
              S(PAL["emitter"], "glow"), sides=20)
    revolve_x(b, [(30.8, 0.65), (36.4, 0.65)], A, S(PAL["rod"], "glow"), sides=10)
    # Dark clamp block the rod runs through, with lighter tabs on its north and south shoulders.
    # (split north and south of the rod, which shows between the halves as in the sprite)
    prism(b, rect(30.6, 24.9, 34.1, 26.95), -2.3, 2.3, S(PAL["clamp"], "dark"), ch=0.45)
    prism(b, rect(30.6, 28.05, 34.1, 30.1), -2.3, 2.3, S(PAL["clamp"], "dark"), ch=0.45)
    prism(b, rect(30.9, 26.7, 33.9, 28.3), -1.4, 0.0, S(PAL["clamp"], "dark"), ch=0.0)  # web under the rod
    prism(b, rect(30.9, 24.9, 33.0, 26.0), 2.0, 2.7, S(PAL["clamp_tab_n"], "metal"), ch=0.2, ch_bottom=0)
    prism(b, rect(30.9, 29.0, 33.0, 30.1), 2.0, 2.7, S(PAL["clamp_tab_s"], "metal"), ch=0.2, ch_bottom=0)
    # Fork tines from the neck to the clamp block, above and below the emitter.
    prism(b, rect(26.2, 21.7, 32.4, 24.95), -1.6, 1.6, S(PAL["tine_n"], "metal"), ch=0.4)
    prism(b, rect(26.2, 30.05, 32.4, 33.3), -1.6, 1.6, S(PAL["tine_s"], "metal"), ch=0.4)
    # Hub on the right panel where the rod lands.
    prism(b, rect(34.6, 25.2, 36.6, 29.8, 0.5), -1.6, 1.6, S(PAL["hub"], "metal"), ch=0.3)

    # --- The two halves (north = sign -1 in rows, south = mirrored)
    for half in ("n", "s"):
        row = (lambda r: r) if half == "n" else (lambda r: 2 * A - r)
        sh = S(PAL[f"shoulder_{half}"], "metal")
        # Shoulder saddle across the collar.
        r0, r1 = sorted((row(17.85), row(22.4)))
        prism(b, rect(16.8, r0, 29.0, r1, 0.5), -1.9, 1.9, sh, ch=0.45)
        r0, r1 = sorted((row(17.85), row(19.9)))
        prism(b, rect(15.2, r0, 17.2, r1), -1.5, 1.5, sh, ch=0.35)
        # Rail along the core, its end caps chamfered.
        rr = row(16.5)
        revolve_x(b, [(6.9, 1.1), (7.3, 1.6), (22.8, 1.6), (23.25, 1.1)], rr, S(PAL[f"bar_{half}"], "polish"), sides=14)
        # Rail clamps where it meets the shoulder.
        for cc in (16.2, 20.4):
            revolve_x(b, [(cc, 1.75), (cc + 0.15, 2.0), (cc + 1.0, 2.0), (cc + 1.15, 1.75)], rr, sh, sides=12)
        # Pipe bending from the rail's end to the wheel's rim.
        tube(b, [(7.6, row(16.5), 0.0), (5.6, row(16.55), 0.0), (4.4, row(17.2), 0.0), (3.6, row(18.4), 0.0),
                 (3.2, row(20.0), 0.0), (3.1, row(21.4), 0.0)], 0.85, S(PAL[f"pipe_{half}"], "metal"), sides=10)
        # Panel arm and its saddle on the rail.
        tube(b, [(15.5, row(10.6), 0.0), (15.5, row(15.2), 0.0)], 0.95, S(PAL[f"arm_{half}"], "metal"), sides=10)
        r0, r1 = sorted((row(13.2), row(14.0)))
        prism(b, rect(13.55, r0, 17.45, r1), -1.1, 1.1, S(PAL[f"arm_{half}"], "metal"), ch=0.25)
        r0, r1 = sorted((row(13.9), row(15.1)))
        prism(b, rect(12.85, r0, 18.15, r1, 0.3), -1.4, 1.4, S(PAL[f"arm_{half}"], "metal"), ch=0.3)
        # North/south panel (2 x 1 cells, the divider along the arm).
        if half == "n":
            panel(b, (15.5, 6.05), (0, 1), 10.3, 9.0, PAL["panel_n"], (2, 1))
        else:
            r0, r1 = sorted((row(12.1), row(13.6)))
            prism(b, rect(12.8, r0, 18.2, r1, 0.25), -1.2, 1.2, S(PAL["arm_s"], "metal"), ch=0.3)
            panel(b, (15.5, 48.55), (0, -1), 11.1, 9.0, PAL["panel_s"], (2, 1))
        # Diagonal strut from the shoulder to the corner panel.
        tube(b, [(25.0, row(19.6), 0.0), (27.6, row(17.0), 0.0), (31.0, row(13.9), 0.0)], 1.55,
             S(PAL[f"strut_{half}"], "metal"), sides=10)
        # Corner panel, long side along the strut (2 across x 3 along).
        d = (1, -1) if half == "n" else (1, 1)
        panel(b, (34.63, row(10.57)), d, 11.6, 8.8, PAL[f"diag_{half}"], (2, 3), rim=1.1, div=0.7)
        # Mount block where the strut meets the panel's inner corner.
        poly = [(30.4, row(14.4)), (33.2, row(13.4)), (34.9, row(15.6)), (34.3, row(16.9)), (30.9, row(16.9))]
        prism(b, poly, -1.5, 1.5, S(PAL[f"strut_{half}"], "metal"), ch=0.35)

    # Right panel on the rod: 2 cells split across the axis, a raised cross rib near its hub.
    panel(b, (41.35, A), (1, 0), 11.3, 9.0, PAL["panel_e"], (2, 1), rib=(-2.6, PAL["rib_e"]))


# ---------------------------------------------------------------------------------------------
# Spindle (newshl-24)
# ---------------------------------------------------------------------------------------------

def build_spindle(b):
    S = b.slot
    A = 13.5
    pol = lambda k: S(SPAL[k], "polish")  # noqa: E731
    revolve_x(b, [(4.55, 1.4), (4.9, 2.3), (5.4, 2.6), (7.7, 2.6)], A, pol("nose"), sides=18)
    revolve_x(b, [(7.4, 3.8), (7.8, 4.5), (9.45, 4.5), (9.55, 4.15), (9.95, 4.15), (10.05, 4.5), (11.7, 4.5),
                  (12.1, 4.0)], A, pol("body"), sides=24)
    revolve_x(b, [(11.9, 3.6), (20.0, 3.6)], A, S(SPAL["shaft"], "polish"), sides=20)
    for c0, c1, ce in ((12.6, 14.6, 8.6), (16.0, 19.8, 7.6)):
        revolve_x(b, [(c0, 8.6), (c0 + 0.35, 9.5), (c1 - 0.45, 9.5), (c1, ce)], A, pol("disc"), sides=40)
        # Hub boss on each disc's outer face.
        revolve_x(b, [(c0 - 0.3, 4.8), (c0 + 0.1, 5.3)], A, S(SPAL["disc"] - 1, "polish"), sides=24, cap1=False)
    # Dark web between the discs and its rim lamps (north and south).
    revolve_x(b, [(14.5, 7.35), (16.1, 7.35)], A, S(SPAL["web"], "dark"), sides=32)
    for rr, key in ((5.0, "lamp_n"), (22.0, "lamp_s")):
        sgn = -1 if rr < A else 1
        tube(b, [(15.3, A + sgn * 6.9, 0.0), (15.3, A + sgn * 9.0, 0.0)], 0.7, S(SPAL[key], "lamp"), sides=10)
    revolve_x(b, [(19.2, 4.4), (22.6, 4.4)], A, S(SPAL["tail"], "polish"), sides=24)
    revolve_x(b, [(22.4, 4.4), (22.8, 4.9), (24.0, 4.9)], A, pol("flange"), sides=24)
    # Clamp blocks north and south of the tail shaft, red strips on their tops.
    prism(b, rect(19.2, 7.05, 23.0, 9.7), -2.4, 2.4, S(SPAL["clamp"], "dark"), ch=0.4)
    prism(b, rect(19.2, 17.3, 23.0, 19.95), -2.4, 2.4, S(SPAL["clamp"], "dark"), ch=0.4)
    prism(b, rect(19.8, 7.25, 22.8, 8.5), 2.2, 2.75, S(SPAL["red_n"], "redstrip"), ch=0.15, ch_bottom=0)
    prism(b, rect(19.8, 18.5, 22.8, 19.75), 2.2, 2.75, S(SPAL["red_s"], "redstrip"), ch=0.15, ch_bottom=0)


# ---------------------------------------------------------------------------------------------
# Objects, materials
# ---------------------------------------------------------------------------------------------

def merged_sprite(names):
    data = common.load_sprite(ROOT, names[0])
    for n in names[1:]:
        data["colors"].update(common.load_sprite(ROOT, n)["colors"])
    return data


def to_object(b, name, sprite, coll, tag):
    me = bpy.data.meshes.new(name)
    me.from_pydata(b.V, [], b.F)
    me.update()
    for p, s in zip(me.polygons, b.FM):
        p.material_index = s
    mats = []
    for pal, fin in b.mat_keys:
        m_, r_, e_ = FINISH[fin]
        mat = common.palette_material(sprite, pal, f"{tag}_{fin}", metallic=m_, roughness=r_, emission_strength=e_)
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if fin == "polish" and "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 1.0  # D176: F0 up for the polished greys
        mats.append(mat)
    for m in mats:
        me.materials.append(m)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    try:
        me.set_sharp_from_angle(angle=math.radians(35))
    except AttributeError:
        pass
    return obj


def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


# ---------------------------------------------------------------------------------------------
# Measure: top-view IoU against the inner masks, per-region colour
# ---------------------------------------------------------------------------------------------

def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = [w for w in str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split()
                 if w.isupper()]
        scene.render.engine = next(n for n in names if want.split("_")[1] in n)


def render_array(scene, cam, path):
    scene.camera = cam
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path))
    px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], img.channels)
    bpy.data.images.remove(img)
    return px[::-1]


def measure_one(obj, mask_name, w, h, centre_xy, out_dir, label, ss=8, regions=None):
    """Top view of obj on the w x h sprite grid centred on centre_xy (Blender XY of the grid's
    centre); IoU against sprite_mask's inner mask (free pixels count neither way)."""
    idx_l, cols = sprite_mask.load(mask_name, ref=str(ROOT / "reference" / "models"))
    masks = sprite_mask.masks(idx_l, cols)
    INNER = np.array(masks["inner"], dtype=bool)
    FREE = np.array(masks["free"], dtype=bool)
    IDX = np.array(idx_l)
    scene = bpy.context.scene
    others = [o for o in scene.objects if o.type == "MESH" and o is not obj and not o.hide_render]
    for o in others:
        o.hide_render = True
    set_engine(scene, "BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.color = (0, 0, 0)
    cd = bpy.data.cameras.new("measure")
    cd.type = "ORTHO"
    cd.ortho_scale = max(w, h) / 12
    cam = bpy.data.objects.new("measure", cd)
    scene.collection.objects.link(cam)
    cam.location = (centre_xy[0], centre_xy[1], 10)
    scene.render.resolution_x = w * ss
    scene.render.resolution_y = h * ss
    scene.render.resolution_percentage = 100
    sh.color_type = "SINGLE"
    sh.single_color = (1, 1, 1)
    sil = render_array(scene, cam, Path(out_dir) / f"{label}_sil.png")[..., 0]
    cov = sil.reshape(h, ss, w, ss).mean(axis=(1, 3))
    model = cov >= 0.5
    keep = ~FREE
    iou = float(((model & INNER) & keep).sum() / max(1, ((model | INNER) & keep).sum()))
    diff = np.full((h, w), ".")
    diff[INNER] = "-"
    diff[model & INNER] = "#"
    diff[model & ~INNER] = "+"
    diff[FREE & ~model] = "f"
    diff[FREE & model] = "F"
    (Path(out_dir) / f"{label}_diff.txt").write_text("\n".join("".join(r) for r in diff) + "\n")
    # Flat material colours from above -> nearest palette index.
    sh.color_type = "MATERIAL"
    for m in obj.data.materials:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        m.diffuse_color = tuple(bsdf.inputs["Base Color"].default_value)
    flat = render_array(scene, cam, Path(out_dir) / f"{label}_flat.png")[..., :3]
    centre = flat[ss // 2::ss, ss // 2::ss]
    keys = sorted({int(m.name.split("_")[1]) for m in obj.data.materials})
    # Linear base colours -> compare in linear space.
    arr = np.array([[v / 255 for v in cols[k]] for k in keys])
    d = ((centre[..., None, :] - arr[None, None]) ** 2).sum(-1)
    seen = np.array(keys)[d.argmin(-1)]
    seen[~model] = -1
    res = {"iou_rule_grid": round(iou, 4)}
    if regions:
        res["regions"] = {}
        for rname, boxes in regions.items():
            sel = np.zeros((h, w), dtype=bool)
            for (c0, r0, c1, r1) in boxes:
                sel[r0:r1, c0:c1] = True
            sv = IDX[sel & (IDX > 1)]
            mv = seen[sel & (seen >= 0)]
            if not len(sv) or not len(mv):
                continue
            s_sorted = np.sort(sv)
            lo, hi = int(len(s_sorted) * 0.15), int(len(s_sorted) * 0.85)
            trimmed = s_sorted[lo:max(hi, lo + 1)]
            m_sorted = np.sort(mv)
            lo, hi = int(len(m_sorted) * 0.15), int(len(m_sorted) * 0.85)
            res["regions"][rname] = {"sprite_median": int(np.median(trimmed)),
                                     "model_median": int(np.median(m_sorted[lo:max(hi, lo + 1)]))}
    np.save(Path(out_dir) / f"{label}_seen.npy", seen)
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in others:
        o.hide_render = False
    return res, model, INNER, FREE


ST_REGIONS = {
    "wheel": [(0, 20, 4, 35)], "drum": [(5, 22, 9, 33)], "coil": [(9, 24, 13, 31)], "sleeve": [(13, 23, 19, 31)],
    "collar": [(19, 20, 26, 35)], "emitter": [(28, 24, 31, 30)], "rod": [(31, 27, 36, 28)],
    "panel_n": [(11, 1, 20, 11)], "panel_s": [(11, 44, 20, 54)], "diag_n": [(30, 5, 39, 13)],
    "diag_s": [(30, 42, 39, 50)], "panel_e": [(37, 23, 46, 32)], "bar_n": [(8, 15, 22, 18)],
    "bar_s": [(8, 37, 22, 40)], "shoulder_n": [(17, 18, 28, 20)], "shoulder_s": [(17, 35, 28, 37)],
}
SP_REGIONS = {"nose": [(5, 11, 8, 16)], "body": [(8, 9, 12, 18)], "disc1": [(13, 4, 14, 23)],
              "disc2": [(17, 4, 19, 23)], "tail": [(19, 10, 24, 17)], "lamps": [(15, 5, 16, 6), (15, 21, 16, 22)],
              "red_n": [(20, 7, 24, 8)], "red_s": [(20, 18, 23, 20)]}


def measure(station, spindle, out_dir):
    """Either object may be None (a wrapper measures only its own model)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    res = {}
    if station is not None:
        r1, model, inner, free = measure_one(station, NAME, 48, 56, (0.0, 0.0), out, "station",
                                             regions=None if MIRROR else ST_REGIONS)
        res["station"] = r1
        keep = ~free
        res["station"]["pieces"] = {}
        for n, (c0, r0) in zip(PIECES, ((0, 0), (24, 0), (0, 28), (24, 28))):
            m, s, k = model[r0:r0 + 28, c0:c0 + 24], inner[r0:r0 + 28, c0:c0 + 24], keep[r0:r0 + 28, c0:c0 + 24]
            res["station"]["pieces"][n] = round(float(((m & s) & k).sum() / max(1, ((m | s) & k).sum())), 4)
    if spindle is not None:
        r2, *_ = measure_one(spindle, SPINDLE, 24, 28, (0.0, 0.0), out, "spindle",
                             regions=None if MIRROR else SP_REGIONS)
        res["spindle"] = r2
    (out / f"metrics_{TAG}.json").write_text(json.dumps(res, indent=1))
    print("MEASURE", json.dumps(res))
    return res


# ---------------------------------------------------------------------------------------------
# Views (EEVEE), for the sheet
# ---------------------------------------------------------------------------------------------

def render_views(objs, out_dir, size=720):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    others = [o for o in scene.objects if o.type == "MESH" and o not in objs and not o.hide_render]
    for o in others:
        o.hide_render = True
    set_engine(scene, "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in str(
        bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()) else "BLENDER_EEVEE")
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.16, 0.17, 0.2, 1)
    bg.inputs["Strength"].default_value = 1.0
    lights = []
    for name, rot, energy in (("key", (math.radians(35), math.radians(-25), math.radians(-20)), 3.6),
                              ("fill", (math.radians(60), math.radians(40), math.radians(160)), 0.9)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.angle = math.radians(3)
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = rot
        scene.collection.objects.link(lo)
        lights.append(lo)
    # Frame the station plus spindle.
    centre = Vector((-1.0, 0.0, 0.0))
    d = 16.0
    specs = [
        ("top", (0, 0, 10), 7.2), ("front_south", (0, -10, 0), 7.2), ("side_east", (10, 0, 0), 7.2),
        ("rear_north", (0, 10, 0), 7.2), ("side_west", (-10, 0, 0), 7.2),
        ("high34_sw", (-d * 0.5, -d * 0.55, d * 0.55), None), ("high34_ne", (d * 0.55, d * 0.5, d * 0.5), None),
        ("game", (0, -d * 0.53, d * 0.85), None), ("under", (d * 0.35, -d * 0.45, -d * 0.6), None),
    ]
    paths = {}
    for name, loc, ortho in specs:
        cd = bpy.data.cameras.new(name)
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = ortho
        else:
            cd.lens = 62
        co = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(co)
        co.location = centre + Vector(loc)
        co.rotation_euler = (centre - co.location).to_track_quat("-Z", "Y").to_euler()
        if name == "top":
            co.rotation_euler = (0, 0, 0)
        scene.camera = co
        p = out_dir / f"{name}.png"
        scene.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        paths[name] = str(p)
        bpy.data.objects.remove(co, do_unlink=True)
    for lo in lights:
        bpy.data.objects.remove(lo, do_unlink=True)
    for o in others:
        o.hide_render = False
    return paths


# ---------------------------------------------------------------------------------------------
# Bake: AO + edge into a colour multiplier and a roughness/metal map ("bake": "model"; no
# concept projection). After usp_talon.bake_maps / assembly-newshi-243.
# ---------------------------------------------------------------------------------------------

def bake_maps(obj, out_dir, tag, size=1024, samples=48):
    scene = bpy.context.scene
    set_engine(scene, "CYCLES")
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
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

        def mth(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.04
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.2
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = mth("MINIMUM", mth("MULTIPLY", mth("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = mth("MULTIPLY", mth("POWER", ao_s.outputs["AO"], 0.8),
                   mth("ADD", 0.65, mth("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        comb = node("ShaderNodeCombineColor")
        if mode == "colour":
            v = mth("MINIMUM", mth("ADD", mth("ADD", 0.5, mth("MULTIPLY", occl, 0.6)), mth("MULTIPLY", edge, 0.15)), 1.0)
            for k in range(3):
                nt.links.new(v, comb.inputs[k])
        else:
            r = mth("ADD", rough, mth("SUBTRACT", mth("MULTIPLY", mth("SUBTRACT", 1.0, occl), 0.3), mth("MULTIPLY", edge, 0.15)))
            r = mth("MAXIMUM", mth("MINIMUM", r, 1.0), 0.05)
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


def split_open(obj, layout, coll, suffix):
    """split_assembly without capping the cuts (for the outline shell)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


def make_shell(src, coll, name, faces):
    """Outline shell (D51) from a sealed copy of src, every outer island kept (D189)."""
    cp = src.copy()
    cp.data = src.data.copy()
    coll.objects.link(cp)
    shell = common.outline_shell(cp, coll, voxel=0.014, faces=faces, islands="outer")
    bpy.data.objects.remove(cp, do_unlink=True)
    shell.name = shell.data.name = name
    shell.hide_render = True
    return shell



# ---------------------------------------------------------------------------------------------
# Entry points for the wrapper scripts. Each builds and exports only its own models.
# ---------------------------------------------------------------------------------------------

def _argv():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _opt(argv, k):
    return argv[argv.index(k) + 1] if k in argv else None


def _bake(obj, tag, size, argv):
    if "--no-bake" in argv:
        return "AUTO"
    import atexit
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix=tag + "_bake_")  # the exporter reads the saved maps: removed at exit
    atexit.register(shutil.rmtree, tmp, True)
    bake_maps(obj, tmp, tag, size=size)
    return "WEBP"


def run_station(name, pieces, centre, spindle, mirror):
    """Build the station of `name` (mirror=True for the left-facing twin) and export its four pieces
    (each with its outline shell) to public/models/enemies + src/render/spriteModels."""
    configure(name, pieces, centre, spindle, mirror)
    argv = _argv()
    coll = common.reset_collection(NAME)
    sprite = merged_sprite(PIECES)
    b = Builder(W_station)
    build_station(b)
    station = to_object(b, NAME, sprite, coll, TAG)
    print(f"station {tris(station)} triangles")
    if _opt(argv, "--measure"):
        measure(station, None, _opt(argv, "--measure"))
    fmt = _bake(station, TAG, 1024, argv)
    if _opt(argv, "--views"):
        render_views([station], _opt(argv, "--views"))
    shell = make_shell(station, coll, f"{NAME}_outline", faces=2600)
    layout = [(e["model"], e["cx"] - CENTRE[0], e["cy"] - CENTRE[1]) for e in sprite["assemblyLayout"]]
    parts = common.split_assembly(station, layout, coll)
    shells = split_open(shell, layout, coll, "_outline")
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    for pn, _, _ in layout:
        shp = shells[pn]
        shp.data.materials.clear()
        shp.data.materials.append(outline_mat)
        shp.data.shade_smooth()
        shp["tyrian_outline"] = True
        shp.hide_render = True
        if len(shp.data.polygons) == 0:
            raise RuntimeError(f"{pn}_outline has no faces")
        print(f"piece {pn}: {tris(parts[pn])} triangles, outline {tris(shp)}")
    for pn, _, _ in layout:
        data = common.load_sprite(ROOT, pn)
        common.export_sprite_model(ROOT, [parts[pn], shells[pn]], f"enemies/{pn}", data["sprites"], image_format=fmt)


def run_spindle(name, mirror):
    """Build and export one twin-disc spindle (newshl-24, or newshl-34 mirrored)."""
    configure(NAME, PIECES, CENTRE, name, mirror)
    global TAG
    TAG = "nshl" + name.split("-")[-1]
    argv = _argv()
    coll = common.reset_collection(name)
    sprite = merged_sprite([name])
    b = Builder(W_spindle)
    build_spindle(b)
    sp = to_object(b, name, sprite, coll, TAG)
    print(f"spindle {tris(sp)} triangles")
    if _opt(argv, "--measure"):
        measure(None, sp, _opt(argv, "--measure"))
    fmt = _bake(sp, TAG, 512, argv)
    if _opt(argv, "--views"):
        render_views([sp], _opt(argv, "--views"))
    shell = make_shell(sp, coll, f"{name}_outline", faces=900)
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    shell.data.materials.clear()
    shell.data.materials.append(outline_mat)
    shell.data.shade_smooth()
    shell["tyrian_outline"] = True
    if len(shell.data.polygons) == 0:
        raise RuntimeError("spindle outline has no faces")
    common.export_sprite_model(ROOT, [sp, shell], f"enemies/{name}", sprite["sprites"], image_format=fmt)
