"""Silver Ship (player ship, tyrian.shp#8 frame 81 and its banking frames 77-85): a hard-surface
fighter built cross-sections first from a multi-view blueprint (the flagship pipeline: blueprint, two
competing designs, judge, strict review; CLAUDE.md art rule 8, PLAYBOOK lesson 22).

What the ship is: a slim armoured fuselage (the only tall part: 7 px wide at the waterline, a deep V
keel, and on its back a 5 px machined spine deck: the canopy's fairing run aft as a raised polished spine
between two channels and two longeron rails, the three members on the three pipes' lines), a small dark
windshield with a polished hoop behind it,
two swept canards, and behind the waist a thick faceted sponson each side (the sprite's "bulge": a
45 degree leading edge, a straight side, a 45 degree rear) that carries one engine tight against the
hull: a raked polished intake lip over a dark mouth, a cowl, two cooling louvre hoops with the red hot
liner showing in the gaps (the sprite's paired red vent stripes), and a red scarfed nozzle cut on the
rear diagonal. Three round exhaust pipes run aft of the stern over a black heat tray on a grey V keel
(the sprite's three prongs).

Rules kept: the sprite gives the plan outline (the blueprint's lines through frame 81's inner mask,
D74), the windshield's pixels and each part's palette index (the median of its region, lit and shaded
side together). No tone bands are painted: one index per part, the light and dark sides come from the
sections under the game's lights (PLAYBOOK lesson 21). No part is thinned to fit pixels: the sponson is
a 3.4 px deep faceted armour block with a 2 px blunt outboard wall (crown, forward glacis, outboard
shoulder, vertical wall, chamfered bilge), the nozzle a 3 x 4 px barrel, the hull 5 px tall.

How it is built: lofts through explicit sections (solid(): any section, concave too, oriented as a
closed solid), V grooves modelled in the lofts for panel lines, proud armour plates (usp_talon.plate),
convex faceted blocks (usp_talon.hull) with the cooling slot and the intake ramp cut out of the
sponsons by an exact boolean, the spine deck one loft whose section carries the channels, their gutters,
the louvre pockets and the intake slots (build_deck; its casing satin and its colour map trimmed to the ship's greys, only
the spine's top polished and bright: DECK_BAKE), AO/roughness bake only (no concept projection:
"bake": "model" in its maps.json; the deck unwrapped on its own at twice the texel density with every
chamfer an island, the margin extended from each island's own texels: unwrap, fill_unbaked), outline
shell from a filled copy (D51), tyrian_engines at the two scarfed exits.

Frame: sprite px. x from the ship's centre line (the middle of sprite column 11), y = sprite row as an
edge coordinate (row r spans y r..r+1, aft is +y), z up. Blender: X = (x - 0.5) / 12, Y = (14 - y) / 12,
Z = z / 12.

    Blender --background --factory-startup --python ship-silver-ship.py -- [--out path.glb] [--no-bake]
            [--measure top.json] [--preview png] [--no-ink] [--bake-dir dir]

--no-ink shrinks the outline shell to nothing: the reference for measuring the ink the shell draws over
the model's interior (viewer captures with and without it).
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
from usp_talon import Part, cbox, hull, join, offset_loop, plate  # noqa: E402
from usp_talon import pchip as _pchip  # noqa: E402

NAME = "ship-silver-ship"
MODEL = f"ships/{NAME}"
PX = 1 / 12
AXIS = -0.5

# --- materials: one palette index per part (blueprint.json "parts"/"spriteMedians") ----------------
SLOTS = [  # name, palette index, tag, metallic (x METAL), roughness, emission
    ("NOSE", 5, "nose", 0.55, 0.40, 0.0),     # nose cone, cockpit hull, canards
    ("HULL", 6, "hull", 0.55, 0.40, 0.0),     # aft hull flanks, manifold
    ("DECK", 11, "deck", 0.55, 0.44, 0.0),    # spine deck casing: rails, chamfers, flanks, fittings (satin)
    ("DECKP", 11, "deckpol", 0.90, 0.18, 0.0),  # the dorsal spine's polished top, bolt heads (same index)
    ("CHAN", 10, "channel", 0.55, 0.46, 0.0),   # the deck's channel floors (cols 10 and 12: median 10)
    ("TRIM", 12, "trim", 0.90, 0.20, 0.0),    # canopy hoop, intake lips: polished
    ("STRAKE", 8, "strake", 0.55, 0.38, 0.0),  # chine strakes
    ("LOUV1", 10, "louvre1", 0.65, 0.30, 0.0),  # louvre hoop between the red vents (row 19: 12 11 10)
    ("LOUV2", 6, "louvre2", 0.55, 0.40, 0.0),   # louvre hoop behind them (row 21: 6 6 6)
    ("SPON", 7, "sponson", 0.55, 0.40, 0.0),  # sponsons, tip rails
    ("COWL", 9, "cowl", 0.60, 0.34, 0.0),     # engine cowls, canopy coaming
    ("FLANGE", 10, "flange", 0.80, 0.26, 0.0),  # pipe root collars (row 22: 9 11 8)
    ("BELLY", 5, "belly", 0.40, 0.55, 0.0),   # tail tray's V keel
    ("DARK", 3, "dark", 0.40, 0.60, 0.0),     # tray walls, intake throats, cradle
    ("DEEP", 2, "recess", 0.30, 0.80, 0.0),   # cooling slots
    ("INK", 1, "black", 0.20, 0.90, 0.0),     # tray top, pipe bores
    ("GLASS", 1, "glass", 0.00, 0.04, 0.0),
    ("LINER", 115, "liner", 0.00, 0.50, 1.0),  # hot liner in the vents (D126: kept at 1)
    ("NOZ", 114, "nozzle", 0.50, 0.45, 0.45),  # heat-stained nozzle shell
    ("RIM", 113, "rim", 0.40, 0.50, 0.0),
    ("THROAT", 118, "throat", 0.00, 0.40, 1.3),
    ("RAMP", 5, "ramp", 0.40, 0.55, 0.0),     # intake ramps
    ("PIPE", 7, "pipe", 0.75, 0.30, 0.0),     # exhaust pipes
    ("RIDGE", 11, "ridge", 0.60, 0.32, 0.0),  # the nose's dorsal ridge (col 11, rows 1-4)
    ("FAIR", 10, "fairing", 0.55, 0.44, 0.0),  # the fairing's broad top ahead of the spine (rows 10-12: median 10)
]
for _i, _s in enumerate(SLOTS):
    globals()[_s[0]] = _i
METAL = 0.22
TINT = (1.0, 0.96, 0.82)  # the bake's tint, as D118's
# The spine deck's colour map (tag: gain, occlusion floor, tint), linear multipliers. The rest of the ship
# bakes as D118 did: 0.48 + 0.62 x occlusion, clamped at 1, so the first sixth of the occlusion is lost and
# an open face keeps its palette colour. The deck, index 11 and 10 and nearly all of it flat and facing up,
# came out near white under the game's lights that way: its rails (median tone, 0-255) 190 in a level, 197
# in the hangar and 221 in the viewer, where the sprite's rail columns are 175, its plates 142 and the hull
# about 80: one bright block on a grey ship, its map 251-255 from edge to edge. So the deck's map is
# trimmed, one gain per part (a part keeps one tone; light and dark still come from its form, lesson 21):
# the satin casing (rails, chamfers, fittings) down to the tone D118's deck had, the fairing's top with it
# (in its own index, FAIR), the channel floors left at their index, the polished spine trimmed least, so
# the spine is the deck's one bright strip. And the deck's occlusion is kept whole (floor + (1 - floor) x occlusion, no headroom): the
# channels, the rails' roots and the fairing's and spine's feet darken as they are shut in (the rail roots
# bake at 0.6 of the rail tops, the floors at 0.4-0.8 of an open one).
# Measured in the game's own renders part by part against the sprite's columns (fix-tone's tone table):
# rails 156 in a level, 157 in the hangar, 178 in the viewer; plates 123 / 134 / 158; spine 168 / 179 / 214.
# Index 11 is a green grey (162 166 162) where the hull's indices (5, 6, 7, 9) are neutral: over the whole
# deck that read as a cooler part on a warm grey ship. Its map takes the green out.
DECK_TINT = (1.0, 0.955, 0.99)
DECK_BAKE = {"deck": (0.62, 0.3, DECK_TINT), "deckpol": (0.92, 0.3, DECK_TINT), "channel": (1.0, 0.4, (1.0, 1.0, 1.0)),
             "fairing": (0.72, 0.3, (1.0, 1.0, 1.0))}
TEXTURED = tuple(i for i, s in enumerate(SLOTS) if s[0] not in ("GLASS", "LINER", "THROAT"))


def materials(sprite):
    return [common.palette_material(sprite, pal, f"silver_{tag}", metallic=m * METAL, roughness=r,
                                    emission_strength=e) for _, pal, tag, m, r, e in SLOTS]


# --- small maths -----------------------------------------------------------------------------------

def pchip(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    f = _pchip(xs, ys)
    return lambda t: f(min(max(t, xs[0]), xs[-1]))


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, a, b):
    return max(a, min(b, x))


def spow(t, e):
    return math.copysign(abs(t) ** (2 / e), t)


# --- mesh helpers ----------------------------------------------------------------------------------

def _face(part, verts, mat):
    if len({id(v) for v in verts}) < 3:
        return None
    try:
        f = part.bm.faces.new(verts)
    except ValueError:
        return None
    f.material_index = mat
    return f


def solid(part, rings, mat, cap0=True, cap1=True, capmat=None):
    """A closed solid lofted through `rings` (lists of 3D points, all the same length; any section,
    concave too). mat: a slot, or mat(band, segment). Faces are oriented as a closed solid."""
    vr = [[part.v(p) for p in r] for r in rings]
    faces = []
    n = len(rings[0])
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            m = mat(k, i) if callable(mat) else mat
            faces.append(_face(part, (vr[k][i], vr[k][j], vr[k + 1][j], vr[k + 1][i]), m))
    cm = capmat if capmat is not None else (mat(0, 0) if callable(mat) else mat)
    if cap0:
        faces.append(_face(part, vr[0], cm))
    if cap1:
        faces.append(_face(part, list(reversed(vr[-1])), cm))
    faces = [f for f in faces if f is not None]
    bmesh.ops.recalc_face_normals(part.bm, faces=faces)
    return faces


def inset(poly, d):
    """A convex polygon's edges moved in by d."""
    n = len(poly)
    area = sum(p[0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * p[1] for i, p in enumerate(poly))
    sg = 1 if area > 0 else -1
    lines = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln * sg, dx / ln * sg
        lines.append((p[0] + nx * d, p[1] + ny * d, dx, dy))
    out = []
    for i in range(n):
        a, b = lines[i - 1], lines[i]
        den = a[2] * b[3] - a[3] * b[2]
        if abs(den) < 1e-9:
            out.append((b[0], b[1]))
            continue
        t = ((b[0] - a[0]) * b[3] - (b[1] - a[1]) * b[2]) / den
        out.append((a[0] + a[2] * t, a[1] + a[3] * t))
    return out


def slab(part, poly, zb, zt, bev, mat, side=1):
    """A chamfered slab: plan polygon [(x, y)] between zb and zt (numbers or functions of (x, y))."""
    fb = zb if callable(zb) else (lambda x, y: zb)
    ft = zt if callable(zt) else (lambda x, y: zt)

    def ring(q, top, dz):
        return [(side * x, y, (ft(x, y) if top else fb(x, y)) + dz) for x, y in q]
    return solid(part, [ring(inset(poly, bev * 0.6), False, 0), ring(poly, False, bev * 0.5),
                        ring(poly, True, -bev), ring(inset(poly, bev), True, 0)], mat)


def ring_y(x, y, z, r, n=12, rot=0.0, rz=None):
    return [(x + r * math.cos(2 * math.pi * (k + rot) / n), y, z + (rz if rz is not None else r) * math.sin(2 * math.pi * (k + rot) / n))
            for k in range(n)]


def ring_z(x, y, z, r, n=6, rot=0.5):
    return [(x + r * math.cos(2 * math.pi * (k + rot) / n), y + r * math.sin(2 * math.pi * (k + rot) / n), z) for k in range(n)]


def stud(part, x, y, z, r, h, mat, n=6, c=0.02):
    """A bolt head or cap standing h proud of z: an n-sided prism with a chamfered top edge."""
    solid(part, [ring_z(x, y, z - 0.04, r, n), ring_z(x, y, z + h - c, r, n), ring_z(x, y, z + h, r - c, n)], mat)


def box(part, x0, x1, y0, y1, z0, z1, ch, mat, side=1, chz=None):
    hull(part, [(side * x, y, z) for x, y, z in cbox(x0, x1, y0, y1, z0, z1, ch, chz)], mat)


# --- dimensions (the blueprint's G, sprite px) -------------------------------------------------------

# Fuselage stations [y, value]
FW = pchip([(1.0, 0.5), (1.2, 1.0), (1.5, 1.3), (2.0, 1.55), (3.0, 2.0), (4.0, 2.5), (5.0, 3.0), (5.6, 3.3),
            (6.2, 3.5), (22.0, 3.5)])                       # plan half width at the waterline
DW = pchip([(1.0, 0.14), (1.5, 0.36), (4.6, 0.36), (5.0, 0.5), (6.2, 1.7), (9.0, 1.9), (10.0, 2.5),
            (22.0, 2.5)])                                   # flat top half width
ZT = pchip([(1.0, 0.75), (1.3, 1.0), (2.0, 1.3), (3.0, 1.6), (4.0, 1.85), (5.0, 2.0), (5.6, 2.05), (6.5, 2.1),
            (8.0, 2.2), (9.0, 2.3), (10.0, 2.36), (12.0, 2.5), (14.0, 2.66), (17.5, 2.86), (20.5, 2.62),
            (21.2, 2.48), (21.6, 2.36), (22.0, 2.16)])      # top line: cambered to a crest over row 18
ZF = pchip([(1.0, 0.45), (2.0, 0.5), (3.0, 0.55), (5.0, 0.65), (6.5, 0.75), (22.0, 0.75)])  # waterline
ZK = pchip([(1.0, 0.15), (1.3, -0.1), (2.0, -0.55), (3.0, -1.0), (4.0, -1.35), (5.0, -1.6), (6.5, -1.9),
            (9.0, -2.15), (12.0, -2.3), (17.5, -2.3), (20.5, -2.2), (22.0, -2.1)])           # keel


def fuse_half(y):
    """Half section, top centre to keel centre: deck land, shoulder knee, waterline chine, tumblehome,
    bilge, keel flat."""
    fw = FW(y)
    dw = min(DW(y), fw * 0.86)
    zt = ZT(y)
    zf = min(ZF(y), zt - 0.1)
    zk = ZK(y)
    h = zf - zk
    return [(0.0, zt), (dw, zt), (dw + 0.28 * (fw - dw), zt - 0.18 * (zt - zf)), (fw, zf),
            (fw * 0.97, zf - 0.45 * h), (fw * 0.62, zk + 0.12 * h), (fw * 0.3, zk), (0.0, zk)]


def fuse_loop(y):
    hs = fuse_half(y)
    return hs + [(-x, z) for x, z in reversed(hs[1:7])]


def hull_top(x, y):
    h = fuse_half(y)
    x = abs(x)
    for i in range(3):
        if x <= h[i + 1][0]:
            t = (x - h[i][0]) / max(1e-6, h[i + 1][0] - h[i][0])
            return lerp(h[i][1], h[i + 1][1], t)
    return h[3][1]


def fuse_ring(y, d=0.0):
    pts = fuse_loop(y)
    if d:
        vn, _ = offset_loop(pts, (0.0, (ZT(y) + ZK(y)) / 2))
        pts = [(x - nx * d, z - nz * d) for (x, z), (nx, nz) in zip(pts, vn)]
    return [(x, y, z) for x, z in pts]


GROOVE_W, GROOVE_D = 0.05, 0.07
FUSE_YS = [1.0, 1.15, 1.3, 1.6, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.3, 5.6, 6.0, 6.5, 7.25, 8.0, 9.0,
           10.0, 11.0, 12.0, 14.0, 16.0, 17.5, 19.0, 20.5, 21.2, 21.6, 22.0]
FUSE_GROOVES = [2.7, 4.2, 12.6, 16.2, 19.6]   # frame lines: V grooves round the hull


def grooved(stations, grooves):
    """Stations with a V groove (a modelled panel line) at each of `grooves`: [(y, inset)]."""
    out = [(y, 0.0) for y in stations if all(abs(y - g) > GROOVE_W * 2.2 for g in grooves)]
    for g in grooves:
        out += [(g - GROOVE_W, 0.0), (g, GROOVE_D), (g + GROOVE_W, 0.0)]
    return sorted(out)


# Sponson
SP = dict(le=6.95, side=8.5, diag=29.0)  # leading edge y = x + le, straight side, rear diagonal x + y = diag
NC = dict(cx=5.0, hw=1.5, z0=0.75, H=1.15, E=2.6, liner=0.82, band=0.85, vent0=18.0)
# Raked intake lip, y at x: a polished band through the sprite's bright diagonal, (row 14, col 7),
# (16, 6), (17, 5) on the lit side.
LIP = pchip([(3.5, 13.75), (4.0, 14.4), (5.0, 16.0), (6.0, 17.1), (6.5, 17.5)])
COWL_X = [NC["cx"] - NC["hw"] + 2 * NC["hw"] * t for t in (0, 0.03, 0.1, 0.22, 0.36, 0.5, 0.64, 0.78, 0.9, 0.97, 1)]


def cowl_z(x, H=None):
    H = NC["H"] if H is None else H
    u = abs((x - NC["cx"]) / NC["hw"])
    return NC["z0"] + H * max(0.0, 1 - u ** NC["E"]) ** (1 / NC["E"])


# --- the parts ---------------------------------------------------------------------------------------

def build_fuselage(P):
    # One tube, nose tip to stern: nose cone (5), cockpit hull (5), aft hull (6). Panel lines are V
    # grooves modelled in the loft.
    st = grooved(FUSE_YS, FUSE_GROOVES)
    rings = [fuse_ring(y, d) for y, d in st]
    # a rounded tip in front of row 1
    tip = fuse_ring(1.0)
    cz = (ZT(1.0) + ZK(1.0)) / 2 + 0.1
    rings.insert(0, [(x * 0.45, 0.93, cz + (z - cz) * 0.5) for x, _, z in tip])
    ys = [0.93] + [y for y, _ in st]
    solid(P, rings, lambda k, i: NOSE if ys[k + 1] <= 10.0 else HULL)
    # Polished dorsal ridge on the nose (col 11, rows 1-4), into the windshield's point.
    R = []
    for i, y in enumerate((1.12, 2.0, 3.0, 4.0, 4.95)):
        w = 0.42 * (0.5 if i in (0, 4) else 1.0)
        z = ZT(y)
        R.append([(-w, y, z - 0.06), (-w * 0.7, y, z + 0.07), (w * 0.7, y, z + 0.07), (w, y, z - 0.06)])
    solid(P, R, RIDGE)
    # Armour plates standing 0.07 px proud with chamfered edges (their gaps are the panel lines): the
    # upper flank ahead of each engine and beside it, the lower cheek under each canard.
    def L(y):
        return fuse_loop(y), (0.0, (ZT(y) + ZK(y)) / 2)
    for side in (1, -1):
        def S(a, b):
            return (a, b) if side > 0 else (14 - b, 14 - a)
        for y0, y1 in ((10.35, 13.55), (13.75, 17.6), (17.8, 21.4)):
            plate(P, L, y0, y1, HULL, *S(2.12, 2.86), d=0.07, c=0.06, depth=0.08, ystep=1.2)
        for y0, y1 in ((5.75, 9.2), (9.4, 12.2)):
            plate(P, L, y0, y1, NOSE if y1 < 10 else HULL, *S(3.12, 3.9), d=0.07, c=0.06, depth=0.08, ystep=1.2)
    # Keel strake under the aft hull (underside: one plain fin, nothing more).
    pts = []
    for y, dz in ((11.0, 0.05), (13.0, 0.5), (20.0, 0.5), (21.8, 0.1)):
        pts += [(sx * x, y, ZK(y) - z) for sx in (-1, 1) for x, z in ((0.5, -0.2), (0.22, dz))]
    hull(P, pts, HULL)


def build_canopy(G, P):
    # Dark glass over the sprite's cockpit px (col 11 at row 5, cols 10-12 at rows 6-8).
    ST = [(5.0, 0.05, 0.04), (5.5, 0.5, 0.26), (6.0, 1.0, 0.46), (6.4, 1.4, 0.56), (7.0, 1.5, 0.63), (7.7, 1.5, 0.66),
          (8.4, 1.47, 0.56), (9.05, 1.38, 0.3)]
    E, NA = 2.4, 11

    def arch(y, hw, ap, base):
        return [(hw * spow(math.cos(math.pi * k / (NA - 1)), E), y,
                 base + ap * math.sin(math.pi * k / (NA - 1)) ** (2 / E)) for k in range(NA)]
    solid(G, [arch(y, hw, ap, hull_top(hw, y) - 0.04) for y, hw, ap in ST], GLASS)
    # Its coaming: a low machined sill round the glass, in the hull's alloy.
    solid(P, [arch(y - (0.14 if i == 0 else 0), hw + 0.13, ap * 0.2 + 0.07, hull_top(hw + 0.13, y) - 0.05)
              for i, (y, hw, ap) in enumerate(ST)], COWL)


def build_hoop(P):
    # The canopy's rear hoop (row 9, the sprite's near-white collar): a machined arch, shoulder to shoulder.
    rings = []
    for y, d in ((9.0, 0.03), (9.2, 0.2), (9.8, 0.2), (10.0, 0.05)):
        h = fuse_half(y)
        up = [(h[2][0] + 0.12, h[2][1] - 0.25), h[2], h[1], h[0]]
        w = [(0.9, 0.2), (0.75, 0.7), (0.3, 0.95), (0.0, 1.0)]
        half = [(x + d * a, z + d * b) for (x, z), (a, b) in zip(up, w)]
        arch_ = [(-x, y, z) for x, z in half] + [(x, y, z) for x, z in reversed(half[:3])]
        base = [(x, z - 0.12) for x, z in up]
        under = [(-x, y, z) for x, z in base] + [(x, y, z) for x, z in reversed(base[:3])]
        rings.append(arch_ + list(reversed(under)))
    solid(P, rings, TRIM)


# Spine deck (rows 10-21, cols 9-13): a machined dorsal casing in the deck's index (11), its shading from
# form (no tone bands: a raised part is brighter only because the lights reach it).
# Across it, three raised members on the three exhaust pipes' lines (cols 9, 11, 13) with a channel either
# side of the middle one (the sprite's rows 10 and 20, cols 9-13: 11 10 12 10 10 and 12 10 13 10 11):
#   - the dorsal spine: the canopy's fairing, 2.6 px wide behind the hoop, necked to 1.25 px by row 13 and
#     run aft to the stern, its top crowned and polished (DECKP, the same index), 0.74 px proud;
#   - a longeron rail along either edge, 0.5 px proud, its top falling outboard to a wide edge chamfer
#     (the deck is crowned in facets: spine, rail, chamfer, then the hull's own shoulder knee);
#   - the channels between, 0.18 px proud (their floors the sprite's cols 10 and 12: index 10), a dark
#     drain gutter along the spine's foot and the rail's foot, that carry the fittings: an access hatch, a
#     louvre bank over a dark pocket (five raked slats, open aft), a filler cap and an inspection door.
# Panel lines follow the form: the rails' seams sit on the hull's frame lines (rows 12.6, 16.2, 19.6) and
# run on down the flanks as its grooves, the spine's own seams are staggered between them (13.3, 18.3)
# with a recessed waist band at row 15.6. A bleed-air intake slot is let into each edge chamfer beside the
# engine (rows 13-16), a sensor blister rides the fairing, bolt heads flank every seam. A low closing frame
# across the stern (STERN_BAR) ends the channels and their gutters square.
DK = dict(W=2.56, foot=2.5, lip=0.08, x_out=2.04, x_in=1.49, rail=0.5, rail_out=0.39, floor=0.18, gut=0.12,
          gx0=0.79, gx1=1.295, gx2=1.38, base=-0.14, pk0=0.84, pk1=1.25, pk_d=0.13, pocket=(15.0, 17.56),
          notch=(12.95, 16.0), notch_d=0.1, y0=10.02, y1=21.97, taper=21.4)
DECK_SEAMS = (12.6, 16.2, 19.6)
SPINE_SEAMS = (13.3, 18.3)
SPINE_BAND = (15.4, 15.8)
SEAM_D = 0.06
SPW = pchip([(9.98, 1.3), (10.7, 1.2), (11.6, 0.95), (12.5, 0.7), (13.1, 0.62), (21.97, 0.62)])
SPH = pchip([(9.98, 0.08), (10.3, 0.44), (10.8, 0.66), (11.6, 0.74), (19.4, 0.74), (21.0, 0.66), (21.6, 0.56),
             (21.97, 0.42)])
DECK_SLATS = tuple((15.06 + 0.5 * i, 15.42 + 0.5 * i) for i in range(5))
DECK_HATCHES = ((0.86, 1.23, 13.5, 14.62), (0.88, 1.21, 19.95, 21.2))
DECK_CAP = (1.045, 18.55)
RAIL_BOLTS = (10.62, 12.34, 12.86, 15.94, 16.46, 19.34, 19.86, 21.25)
STERN_BAR = (21.52, 21.985, 1.46, 0.09)   # the closing frame: y0, y1, half width, height over the channel floor
FILL_SINK = 0.04   # the outline copy's rails sit this far inside the real ones (see build_deck)


def ZD(y):
    """The hull's top line as the loft has it: straight between the fuselage's stations."""
    y = clamp(y, FUSE_YS[0], FUSE_YS[-1])
    for a, b in zip(FUSE_YS, FUSE_YS[1:]):
        if y <= b:
            return lerp(ZT(a), ZT(b), (y - a) / (b - a))


def tramp(y, a, b, e):
    """0 outside a..b, 1 from a + e to b - e."""
    return clamp(min(y - a, b - y) / e, 0.0, 1.0)


def deck_k(y):
    """The casing's height scale: its chamfered front behind the hoop, its boat-tail at the stern."""
    return min(lerp(0.3, 1.0, clamp((y - DK["y0"]) / 0.2, 0.0, 1.0)),
               lerp(1.0, 0.6, clamp((y - DK["taper"]) / (DK["y1"] - DK["taper"]), 0.0, 1.0)))


def rail_z(x, y):
    """The rail top's height above the hull at lateral x."""
    return lerp(DK["rail"], DK["rail_out"], clamp((abs(x) - DK["x_in"]) / (DK["x_out"] - DK["x_in"]), 0.0, 1.0)) * deck_k(y)


def deck_half(y, gd=0.0):
    """The casing's half section, centre to foot, as heights above the hull: channel floor (with the louvre
    pocket), riser, rail, edge chamfer (with the intake slot), foot land. gd: a seam's depth here."""
    k = deck_k(y)
    p = DK["pk_d"] * tramp(y, *DK["pocket"], 0.02)
    q = DK["notch_d"] * tramp(y, *DK["notch"], 0.12)
    fl, g = DK["floor"] * k, DK["gut"] * k
    a = (DK["x_out"], DK["rail_out"] * k - gd)
    b = (DK["foot"], DK["lip"] * k - gd * 0.5)
    ln = math.hypot(b[0] - a[0], b[1] - a[1])
    nx, nz = -(b[1] - a[1]) / ln, (b[0] - a[0]) / ln

    def C(t, push=0.0):
        return (lerp(a[0], b[0], t) - nx * push, lerp(a[1], b[1], t) - nz * push)
    return [(0.0, fl - g), (DK["gx0"], fl - g), (DK["gx0"] + 0.01, fl), (DK["pk0"], fl), (DK["pk0"] + 0.02, fl - p),
            (DK["pk1"] - 0.02, fl - p), (DK["pk1"], fl), (DK["gx1"] - 0.01, fl), (DK["gx1"], fl - g), (DK["gx2"], fl - g),
            (DK["x_in"], DK["rail"] * k - gd), a, C(0.3), C(0.34, q), C(0.76, q), C(0.8), b, (DK["W"], 0.0)]


# Each segment of the half section: its slot, or (slot inside the pocket / the intake slot, slot elsewhere).
DECK_SEGS = ("DARK", "DARK", "CHAN", ("DEEP", "CHAN", 0), ("DEEP", "CHAN", 0), ("DEEP", "CHAN", 0), "CHAN", "DARK", "DARK",
             "DECK", "DECK", "DECK", ("DARK", "DECK", 1), ("DARK", "DECK", 1), ("DARK", "DECK", 1), "DECK", "DECK")


def build_deck(P, fill=False):
    if fill:
        # For the outline shell: the casing's envelope (spine top to rail to foot), channels bridged. This
        # copy stands in the scene during the bake, so its rails and edge chamfers are sunk FILL_SINK inside
        # the real ones: coplanar with them, the bake's occlusion rays hit it at random (rounding) and the
        # rails came out in cloudy patches.
        e = FILL_SINK
        rings = []
        for y in sorted({9.98, 10.12, 10.3, 10.55, 10.8, 11.3, 12.0, 12.5, 13.05, DK["y1"]} | {y for y in FUSE_YS if 13.1 < y < DK["y1"]}):
            k, h, z = deck_k(y), SPH(y), ZD(y)
            c = min(0.2, max(0.02, h * 0.45))
            half = [(max(0.05, SPW(y) - c), max(h, DK["rail"] * k)), (DK["x_in"], DK["rail"] * k - e),
                    (DK["x_out"], DK["rail_out"] * k - e), (DK["foot"], DK["lip"] * k - e), (DK["W"], DK["base"])]
            rings.append([(-x, y, z + q) for x, q in reversed(half)] + [(x, y, z + q) for x, q in half])
        solid(P, rings, DECK)
        return
    # The casing: one loft, stern to hoop, its seams V grooves across the rails and chamfers.
    ys = {DK["y0"], DK["y0"] + 0.2, DK["taper"], DK["y1"]} | {y for y in FUSE_YS if DK["y0"] + 0.25 < y < DK["y1"]}
    for a, b, e in ((*DK["pocket"], 0.02), (*DK["notch"], 0.12)):
        ys |= {a, a + e, b - e, b}
    st = [(y, 0.0) for y in ys if all(abs(y - g) > GROOVE_W * 2.2 for g in DECK_SEAMS)]
    for g in DECK_SEAMS:
        st += [(g - GROOVE_W, 0.0), (g, SEAM_D), (g + GROOVE_W, 0.0)]
    st.sort()
    rings, pk, nq = [], [], []
    for y, gd in st:
        half = deck_half(y, gd)
        z = ZD(y)
        rings.append([(-x, y, z + h) for x, h in reversed(half[1:])] + [(x, y, z + h) for x, h in half]
                     + [(DK["W"], y, z + DK["base"]), (-DK["W"], y, z + DK["base"])])
        pk.append(tramp(y, *DK["pocket"], 0.02) > 0)
        nq.append(tramp(y, *DK["notch"], 0.12) > 0)
    n = len(deck_half(12.0)) - 1

    def mat(k, i):
        j = n - 1 - i if i < n else i - n          # the half section's segment, either side
        if i >= 2 * n:
            return DECK
        sg = DECK_SEGS[j]
        if isinstance(sg, tuple):
            on = (pk, nq)[sg[2]]
            sg = sg[0] if on[k] or on[k + 1] else sg[1]
        return globals()[sg]
    solid(P, rings, mat)

    # The dorsal spine: the canopy's fairing, necked behind it and run to the stern; a crowned polished top
    # between chamfers, battered sides down into the channels. Seams and a waist band are modelled in.
    sy = {9.98, 10.12, 10.3, 10.55, 10.8, 11.0, 11.3, 11.6, 12.0, 12.5, 12.8, 13.05, 20.0, 21.9, DK["y1"]}
    sy |= {y for y in FUSE_YS if 13.1 < y < DK["y1"]}
    st = [(y, 0.0) for y in sy if all(abs(y - g) > GROOVE_W * 2.2 for g in SPINE_SEAMS)
          and not SPINE_BAND[0] - 0.12 < y < SPINE_BAND[1] + 0.12]
    for g in SPINE_SEAMS:
        st += [(g - GROOVE_W, 0.0), (g, SEAM_D), (g + GROOVE_W, 0.0)]
    st += [(SPINE_BAND[0] - 0.06, 0.0), (SPINE_BAND[0], 0.05), (SPINE_BAND[1], 0.05), (SPINE_BAND[1] + 0.06, 0.0)]
    st.sort()
    rings = []
    for y, gd in st:
        end = 0.07 if y >= DK["y1"] else 0.0       # the stern end's chamfer
        w, h, z = SPW(y) - gd - end, SPH(y) - gd - end, ZD(y)
        c = min(0.2, max(0.02, h * 0.45))
        fl = min((DK["floor"] - DK["gut"]) * deck_k(y) - 0.06, h - c - 0.01)
        half = [(w - c, h), (w, h - c), (w + 0.035, fl)]
        rings.append([(-x, y, z + q) for x, q in reversed(half)] + [(0.0, y, z + h + 0.035 * min(1.0, h / 0.5))]
                     + [(x, y, z + q) for x, q in half])
    # Polished from its first seam (row 13.3) aft: ahead of it the fairing's broad top is satin, in the index
    # of the sprite's pixels there (FAIR: rows 10-12 are 9 to 12, median 10; the spine behind 10 to 13).
    sy_ = [y for y, _ in st]
    solid(P, rings, lambda k, i: DECK if i not in (2, 3) else DECKP if sy_[k] >= SPINE_SEAMS[0] - 1e-6 else FAIR, capmat=DECK)

    # Stern closing frame: a low chamfered cross-member, rail to rail under the spine, that ends the channels
    # and their gutters square (open, the gutters' mouths made the channel floors read as loose straps).
    ya, yb, hw, up = STERN_BAR
    pts = []
    for y, c in ((ya, 0.05), (ya + 0.05, 0.0), (yb - 0.05, 0.0), (yb, 0.05)):
        top = DK["floor"] * deck_k(min(y, DK["y1"])) + up - c
        pts += [(sx * hw, y, ZD(y) + q) for sx in (-1, 1) for q in (DK["base"], top)]
    hull(P, pts, DECK)

    # Sensor blister on the fairing: a polished teardrop.
    rings = []
    for y, r, hh in ((10.98, 0.05, 0.02), (11.15, 0.22, 0.12), (11.45, 0.33, 0.2), (11.85, 0.3, 0.19), (12.25, 0.18, 0.11),
                     (12.5, 0.05, 0.02)):
        zb = ZD(y) + SPH(y)
        rings.append([(r * math.cos(math.pi * k / 6), y, zb + hh * math.sin(math.pi * k / 6)) for k in range(7)]
                     + [(-r, y, zb - 0.08), (r, y, zb - 0.08)])
    solid(P, rings, DECKP)

    for s in (-1, 1):
        # Louvre slats over the pocket: raked plates, front edge on the floor, open aft.
        for y0, y1 in DECK_SLATS:
            za, zb = ZD(y0) + DK["floor"], ZD(y1) + DK["floor"]
            pts = []
            for x in (DK["pk0"] - 0.01, DK["pk1"] + 0.01):
                pts += [(s * x, y0, za + 0.012), (s * x, y0 + 0.04, za - 0.05), (s * x, y1, zb + 0.13), (s * x, y1 - 0.02, zb + 0.08)]
            hull(P, pts, DECK)
        # Access hatch and inspection door: low chamfered lands in the channel, a bolt at each corner.
        for x0, x1, y0, y1 in DECK_HATCHES:
            slab(P, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], lambda x, y: ZD(y) + DK["floor"] * deck_k(y) - 0.03,
                 lambda x, y: ZD(y) + DK["floor"] * deck_k(y) + 0.05, 0.03, DECK, s)
            for x in (x0 + 0.09, x1 - 0.09):
                for y in (y0 + 0.1, y1 - 0.1):
                    stud(P, s * x, y, ZD(y) + DK["floor"] * deck_k(y) + 0.05, 0.05, 0.03, DECKP)
        # Filler cap: a collar and a polished hex plug.
        x, y = DECK_CAP
        z = ZD(y) + DK["floor"]
        stud(P, s * x, y, z, 0.2, 0.06, DECK, n=10)
        stud(P, s * x, y, z + 0.05, 0.11, 0.05, DECKP)
        # Bolt heads on the rails, either side of each seam.
        for y in RAIL_BOLTS:
            stud(P, s * 1.77, y, ZD(y) + rail_z(1.77, y), 0.085, 0.04, DECKP)
    # and on the spine, either side of its seams
    for g in SPINE_SEAMS:
        for y in (g - 0.24, g + 0.24):
            for x in (-0.22, 0.22):
                stud(P, x, y, ZD(y) + SPH(y) + 0.02, 0.06, 0.035, DECKP)


def build_fins(P):
    CAN = [(3.3, 5.45), (6.5, 8.55), (6.5, 8.95), (4.5, 10.0), (3.3, 10.0)]
    STR = [(3.2, 9.4), (4.45, 9.8), (4.45, 12.3), (3.2, 12.3)]
    for s in (-1, 1):
        # Swept delta canard: a solid wedge plate, 0.82 px at the root to 0.24 at the tip.
        slab(P, CAN, lambda x, y: 0.42 + 0.08 * (x - 3.3), lambda x, y: 1.24 - 0.1 * (x - 3.3), 0.13, NOSE, s)
        # Chine strake: carries the canard's root back into the sponson's leading edge.
        slab(P, STR, -0.3, 0.98, 0.2, STRAKE, s)


# The sponson's facets (right side; x, y, z): a flat crown that carries the engine, a glacis falling
# forward to the blunt leading edge, a shoulder falling outboard to the top of the armoured wall, a
# raked underside that reaches full depth 2.6 px behind the leading edge.
SB = dict(xi=3.2, wall=8.44, crown=0.85, edge=0.5, le_bot=-0.95, belly=-2.55, belly_aft=-2.15, belly_in=-1.9,
          wall_bot=-1.55, glacis=1.5, rake=2.6, xs=6.55, xb=7.3, xk=4.1, end=22.3)


def shoulder_z(x):
    """The sponson top's height at lateral x behind the glacis."""
    return SB["crown"] - (SB["crown"] - SB["edge"]) * clamp((x - SB["xs"]) / (SB["wall"] - SB["xs"]), 0.0, 1.0)


def hull_faces(part, pts, mat):
    before = set(part.bm.faces)
    hull(part, pts, mat)
    return [f for f in part.bm.faces if f not in before]


def build_sponson_bodies(B):
    le, d = SP["le"], SP["diag"]
    xi, w, xs, xb, xk, end = SB["xi"], SB["wall"], SB["xs"], SB["xb"], SB["xk"], SB["end"]
    for s in (-1, 1):
        pts = [
            (xi, xi + le, SB["edge"]), (w, w + le, SB["edge"]), (xi, xi + le, SB["le_bot"]), (w, w + le, SB["le_bot"]),
            (xi, xi + le + SB["glacis"], SB["crown"]), (xs, xs + le + SB["glacis"], SB["crown"]), (xs, end, SB["crown"]),
            (xi, end, SB["crown"]),
            (w, d - w, SB["edge"]), (d - end, end, shoulder_z(d - end)),
            (w, w + le + 2.2, SB["wall_bot"]), (w, d - w, SB["wall_bot"]),
            # underside: a flat belly from the keel-side chamfer (xk) out to the bilge chamfer (xb),
            # raked up to the leading edge and boat-tailed up to the nozzle's root
            (xi, xi + le + SB["rake"], SB["belly_in"]), (xk, xk + le + SB["rake"], SB["belly"]),
            (xb, xb + le + SB["rake"], SB["belly"]), (xb, 20.4, SB["belly"]), (xk, 20.4, SB["belly"]),
            (xi, 20.4, SB["belly_in"]), (xb, d - xb, SB["belly_aft"] - 0.15),
            (d - end, end, SB["belly_aft"]), (xk, end, SB["belly_aft"]), (xi, end, SB["belly_in"]),
        ]
        hull(B, [(s * x, y, z) for x, y, z in pts], SPON)


def build_sponson_cutters(C):
    """What is cut out of the sponsons: the cooling slot between engine and rail (a trench 0.5 px deep,
    dark floor) and the intake ramp scooped into the crown ahead of each engine mouth."""
    for s in (-1, 1):
        x0, x1, y0, y1 = 6.64, 7.5, 17.9, 21.0
        pts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (shoulder_z(x) - 0.5, 1.6)]
        for f in hull_faces(C, [(s * x, y, z) for x, y, z in pts], SPON):
            if all(v.co.z < shoulder_z(x0) - 0.3 for v in f.verts):
                f.material_index = DEEP
        xa, xb_ = 3.75, 6.25
        pts = [(4.5, 13.45), (5.5, 13.45), (xb_, LIP(xb_) + 0.62), (xa, LIP(xa) + 0.62)]
        zs = [SB["crown"] + 0.012, SB["crown"] + 0.012, SB["crown"] - 0.32, SB["crown"] - 0.32]
        hull(C, [(s * x, y, z) for (x, y), z in zip(pts, zs)] + [(s * x, y, 1.6) for x, y in pts], RAMP)


def build_sponson_fittings(P):
    for s in (-1, 1):
        # Side armour: two plates on the wall with a seam between them and chamfered frames.
        for y0, y1 in ((15.62, 17.95), (18.1, 20.4)):
            box(P, 8.3, SP["side"], y0, y1, SB["wall_bot"] + 0.22, SB["edge"] - 0.12, 0.06, SPON, s)
        # Shoulder access panel between the engine and the rail, ahead of the slot.
        pts = []
        for x, y, c in ((6.74, 15.95, 1), (7.5, 15.95, 1), (7.5, 17.6, 1), (6.74, 17.6, 1)):
            pts.append((s * x, y, shoulder_z(x) - 0.1))
            cx, cy = 7.12, 16.775
            pts.append((s * (x + 0.05 * (1 if x < cx else -1)), y + 0.05 * (1 if y < cy else -1), shoulder_z(x) + 0.05))
        hull(P, pts, SPON)
        # Tip rail (cols 3 / 19, rows 15-20): an octagonal armour rail along the outer top edge.
        RV, RK = (15.55, 15.8, 16.2, 20.2, 20.6, 20.85), (0.35, 0.8, 1.0, 1.0, 0.8, 0.4)
        solid(P, [ring_y(s * 8.06, y, SB["edge"] + 0.3 - (1 - k) * 0.2, 0.4 * k, 8, 0.5) for y, k in zip(RV, RK)], SPON)
        # two rail stanchion feet
        for y in (16.6, 19.8):
            box(P, 7.72, 8.4, y - 0.22, y + 0.22, SB["edge"] - 0.1, SB["edge"] + 0.42, 0.08, SPON, s)


def nacelle_profile(x, fill=False):
    """The engine's section in the y-z plane at lateral x: lip, cowl, vent, louvre hoop, vent, louvre
    hoop, then round underneath and up the intake throat. [(y, z)], with each segment's slot."""
    L = LIP(x)
    bd = min(NC["band"], max(0.05, (NC["vent0"] - L) * 0.6))
    cz = cowl_z(x)
    lz = cz if fill else cowl_z(x, NC["liner"])
    zb = 0.1
    back = 0.05 if fill else 0.55
    # a seam across the cowl at row 17.2 where the cowl is long enough to carry one
    g0 = max(L + bd + 0.05, 17.14)
    gd = 0.06 if (L + bd + 0.05 < 17.14 and not fill) else 0.0
    v0 = max(g0 + 0.14, NC["vent0"])
    pts = [
        (L, cz + 0.04, TRIM), (L + bd, cz + 0.04, TRIM), (L + bd + 0.03, cz, COWL),
        (g0, cz, COWL), (g0 + 0.05, cz - gd, COWL), (g0 + 0.1, cz, COWL),
        (v0, cz, COWL), (v0 + 0.1, lz, LINER), (18.98, lz, LOUV1),
        (19.1, cz, LOUV1), (19.9, cz, LOUV1), (20.02, lz, LINER), (20.98, lz, LOUV2),
        (21.1, cz, LOUV2), (22.05, cz, LOUV2), (22.05, zb, DARK), (L + back, zb, DARK),
        (L + back, max(zb + 0.02, cz - 0.24), DARK), (L + 0.07 if not fill else L + 0.04, cz - 0.2, TRIM),
    ]
    return pts


def build_engines(P, fill=False):
    for s in (-1, 1):
        # Nacelle: lofted across x through the profile (lip 12, cowl 9, liner 115, louvres 10 and 6, throat 3).
        profs = [nacelle_profile(x, fill) for x in COWL_X]
        rings = [[(s * x, y, z) for y, z, _ in pr] for x, pr in zip(COWL_X, profs)]
        solid(P, rings, lambda k, i: profs[0][i][2])
        # Scarfed nozzle: the full barrel (3 x 3.5 px) in heat-stained red, cut on the vertical plane
        # x + y = 29; a dark rim, an inner wall and the glowing throat.
        NN, K, E, HH, SQ, ZC = 20, 4, 2.8, 2.025, 0.1, -0.125

        def nz(t, scale=1.0, push=0.0):
            ring = []
            for j in range(NN):
                a = 2 * math.pi * (j + 0.5) / NN
                x = NC["cx"] + NC["hw"] * scale * spow(math.cos(a), E)
                y = lerp(22.0, SP["diag"] - x, t) - push
                z = ZC + HH * scale * (1 - SQ * t) * spow(math.sin(a), E)
                ring.append((s * (x - push), y, z))
            return ring
        rings = [nz(k / K) for k in range(K + 1)]
        mats = [NOZ] * K
        if fill:
            rings += [nz(1.0, 0.5, 0.0)]
            mats += [RIM]
        else:
            # a dark lip, an inner wall, the glowing throat annulus and a dark exhaust plug in its middle
            rings += [nz(1.0, 0.85, 0.05), nz(1.0, 0.77, 0.5), nz(1.0, 0.38, 0.5), nz(1.0, 0.06, 0.1)]
            mats += [RIM, RIM, THROAT, RIM]
        solid(P, rings, lambda k, i: mats[k], capmat=RIM)
        if not fill:
            # Six thin stator vanes set deep in the throat, from the plug out to the wall: blades on edge
            # across the glowing annulus, so the ring stays the brightest thing in the exit.
            hub, wall = nz(1.0, 0.37, 0.43), nz(1.0, 0.76, 0.43)
            hub1, wall1 = nz(1.0, 0.37, 0.56), nz(1.0, 0.76, 0.56)
            for j in (1, 4, 8, 11, 14, 18):
                t = (Vector(wall[(j + 1) % NN]) - Vector(wall[j - 1])).normalized() * 0.035
                pts = []
                for q in (hub[j], wall[j], wall1[j], hub1[j]):
                    pts += [tuple(Vector(q) + t), tuple(Vector(q) - t)]
                hull(P, pts, RIM)
        # a stiffening band round the nozzle's root (where it leaves the sponson)
        solid(P, [[(s * (NC["cx"] + (NC["hw"] + g) * spow(math.cos(2 * math.pi * (j + 0.5) / NN), E)), y,
                    ZC + (HH + g) * spow(math.sin(2 * math.pi * (j + 0.5) / NN), E)) for j in range(NN)]
                  for y, g in ((22.0, 0.0), (22.06, 0.07), (22.32, 0.07), (22.4, 0.0))], RIM)


def build_tail(P, fill=False):
    # Tail tray: the lower hull carried aft of the stern as a heat-shield trough: a black tray top
    # between two low dark walls, on a grey V keel (so the stern reads solid from behind and below).
    TZK = pchip([(21.8, -2.1), (23.5, -1.9), (25.0, -1.45), (26.05, -1.0)])
    HW, FLOOR, WALL = 3.4, 0.3, 0.72
    rings = []
    for y, k in ((21.8, 1.0), (23.5, 1.0), (25.3, 1.0), (25.8, 0.985), (26.05, 0.94)):
        zk, w = TZK(y), HW * k
        hs = [(0.0, FLOOR), (w - 0.5, FLOOR), (w - 0.38, WALL), (w, WALL), (w, 0.1), (w, -0.45), (1.8 * k, zk + 0.4),
              (0.0, zk)]
        rings.append([(x, y, z) for x, z in hs] + [(-x, y, z) for x, z in reversed(hs[1:7])])
    tm = {0: INK, 13: INK, 1: DARK, 2: DARK, 3: DARK, 10: DARK, 11: DARK, 12: DARK}
    solid(P, rings, lambda k, i: tm.get(i, BELLY), capmat=BELLY)
    # Manifold block at the foot of the stern face; the pipes come out of it. A saddle cradle near
    # their ends (under the pipes, never across them).
    box(P, -2.9, 2.9, 21.9, 23.0, 0.3, 1.05, 0.14, HULL)
    box(P, -2.9, 2.9, 24.55, 25.05, 0.3, 0.8, 0.08, DARK)
    # Three round exhaust pipes (cols 9, 11, 13, rows 22-25): 1 px in diameter on a 2 px pitch, each
    # one continuous tube from the manifold to its open end.
    for x in (-2.0, 0.0, 2.0):
        z, r = 1.1, 0.5
        rings = [ring_y(x, y, z, r) for y in (21.85, 23.0, 24.5, 25.9)] + [ring_y(x, 26.0, z, r - 0.07)]
        mats = [PIPE] * 4
        if fill:
            rings += [ring_y(x, 26.0, z, 0.1)]
            mats += [PIPE]
        else:
            rings += [ring_y(x, 26.0, z, 0.36), ring_y(x, 25.5, z, 0.32)]
            mats += [PIPE, INK]
        solid(P, rings, lambda k, i: mats[k], capmat=INK)
        # Root flange where the pipe leaves the manifold (row 22): a machined collar and its neck ring.
        solid(P, [ring_y(x, y, z, r + g) for y, g in ((22.03, 0.05), (22.1, 0.15), (22.5, 0.15), (22.56, 0.08),
                                                      (22.84, 0.08), (22.9, 0.02))], FLANGE)
        # a clamp band over the cradle
        solid(P, [ring_y(x, y, z, 0.56 * k) for y, k in ((24.55, 0.93), (24.62, 1.0), (24.98, 1.0), (25.05, 0.93))], PIPE)


def lip_x(y):
    """The lateral x where the raked intake lip crosses row y (LIP's inverse), None ahead of it."""
    if y < LIP(3.5):
        return None
    lo, hi = 3.5, 6.5
    for _ in range(30):
        mid = (lo + hi) / 2
        if LIP(mid) < y:
            lo = mid
        else:
            hi = mid
    return lo


def outline_fill():
    """Blocks for the outline shell only (never drawn): ramps that ease the tall steps seen from above
    (deck edge down to the nacelle, nacelle down to the rail), so the shell's back faces draw no ink
    lines across the hull. Each stays inside the model's own surfaces (behind the raked lip)."""
    Q = Part("silver_fill")
    for s in (-1, 1):
        pts = []
        for y in (14.5, 15.2, 16.0, 17.0, 18.0, 20.0, 21.6):
            xo = min(4.6, lip_x(y - 0.5))
            pts += [(s * 2.3, y, ZT(y) + 0.1), (s * 2.3, y, 0.0), (s * xo, y, cowl_z(xo) - 0.08), (s * xo, y, 0.0)]
        hull(Q, pts, 0)
        pts = []
        for y in (18.0, 21.0):
            pts += [(s * 6.0, y, cowl_z(6.0) - 0.06), (s * 6.0, y, 0.0), (s * 7.75, y, shoulder_z(7.75) + 0.27),
                    (s * 7.75, y, 0.0)]
        hull(Q, pts, 0)
    return Q


# The banking frames' pose (D93, fitted to sprites 77-85 with tools/bank_roll.py --fit): the game's
# roll (17.5 / 35 degrees), moved sideways only 0 / 0.5 px, not bankShift.ts's 1 / 2 (D118's entry).
BANK_ROLL = [17.5, 35.0]
BANK_SHIFT = [0.5, 0, 0, 0, -0.5]


def finish(part, mats, coll, dissolve=True):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges)
    if dissolve:
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.3), verts=bm.verts, edges=bm.edges,
                                 delimit={"MATERIAL"})
    m = Matrix(((PX, 0, 0, AXIS * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
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


def build(coll, mats, fill=False):
    P = Part("silver_hull", smooth_angle=30)
    build_fuselage(P)
    build_hoop(P)
    D = Part("silver_deck", smooth_angle=22)
    build_deck(D, fill)
    G = Part("silver_canopy", smooth_angle=50)
    C = Part("silver_coaming", smooth_angle=40)
    build_canopy(G, C)
    W = Part("silver_fins", smooth_angle=30)
    build_fins(W)
    S = Part("silver_sponson_fittings", smooth_angle=30)
    build_sponson_fittings(S)
    B = Part("silver_sponsons", smooth_angle=25)
    build_sponson_bodies(B)
    body = finish(B, mats, coll)
    if not fill:
        Cp = Part("silver_cutters", smooth_angle=25)
        build_sponson_cutters(Cp)
        cutter = finish(Cp, mats, coll)
        mod = body.modifiers.new("cut", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        mod.solver = "EXACT"
        common._apply_modifiers(body)
        bpy.data.objects.remove(cutter)
        body.data.set_sharp_from_angle(angle=math.radians(25))
    E = Part("silver_engines", smooth_angle=38)
    build_engines(E, fill)
    Tl = Part("silver_tail", smooth_angle=40)
    build_tail(Tl, fill)
    return [finish(p, mats, coll) for p in (P, D, G, C, W, S, E, Tl)] + [body]


def cull_hidden_sym(obj, grid=6, ndirs=48):
    """usp_talon.cull_hidden (same sample points, same directions) with one more rule: a face stays if its
    mirror image stays. The ship is symmetric and the test is not (a fixed spiral of directions; a warped
    quad's sample points lie off its two triangles, above them on one side of the ship and under them on
    the other), so it found the hull flank under the canopy hoop hidden on one side only and left a hole
    there: a pale shard beside the collar's corner."""
    from mathutils.bvhtree import BVHTree
    from mathutils.kdtree import KDTree
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    eps = 2e-4
    seen, mids = [], []
    for f in bm.faces:
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        mids.append(c)
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    u, v = (i + 0.5) / grid, (j + 0.5) / grid
                    pts.append(vs[0].lerp(vs[1], u).lerp(vs[3].lerp(vs[2], u), v))
        else:
            for vco in vs:
                for t in (0.35, 0.7, 0.92):
                    pts.append(c.lerp(vco, t))
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen.append(any(tree.ray_cast(q + n * eps, d, 50.0)[0] is None for q in pts for d in cand))
    kd = KDTree(len(mids))
    for i, c in enumerate(mids):
        kd.insert(c, i)
    kd.balance()
    dead, back = [], 0
    for f, c, ok in zip(bm.faces, mids, seen):
        if ok:
            continue
        twin = [i for _, i, _ in kd.find_range(Vector((2 * AXIS * PX - c.x, c.y, c.z)), 2e-5)
                if seen[i] and len(bm.faces[i].verts) == len(f.verts) and abs(bm.faces[i].calc_area() - f.calc_area()) < 1e-7]
        if twin:
            back += 1
        else:
            dead.append(f)
    print(f"silver: culled {len(dead)} hidden faces of {len(bm.faces)}, kept {back} for their mirror images")
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()


# --- texture: baked occlusion and edge wear (no concept projection), the baseline's bake ------------

DECK_TEXELS = 2.0     # the spine deck's texel density, times the rest of the ship's
DECK_UV_ANGLE = 30.0  # its unwrap's angle limit: every chamfer and wall an island of its own


def on_deck(co):
    """Whether a point of the built mesh (Blender units) is on the spine deck's casing or its fittings."""
    x, y, z = co.x / PX - AXIS, 14 - co.y / PX, co.z / PX
    return abs(x) < DK["W"] + 0.06 and DK["y0"] - 0.05 < y < STERN_BAR[1] + 0.02 and z > ZD(y) + DK["base"] - 0.02


def unwrap(me):
    """UVs for the bake (edit mode). The ship as the baseline has it (smart project, 55 degrees). The spine
    deck, the part every camera looks down on, is then unwrapped again on its own with a tighter angle limit
    and DECK_TEXELS the density: at 55 degrees a 45 degree chamfer joined its top's island as a strip two
    texels wide, and where that strip ran diagonally in the atlas (the fairing's neck, one flank) the step
    from the lit top to the shaded chamfer came out as a row of texel teeth. With the chamfer an island of
    its own the tone changes at the mesh's edge, not at a texel's."""
    def uv_area(f, uvl):
        pts = [l[uvl].uv for l in f.loops]
        return abs(sum(a.x * b.y - b.x * a.y for a, b in zip(pts, pts[1:] + pts[:1]))) / 2

    def density(faces, uvl):
        return math.sqrt(sum(uv_area(f, uvl) for f in faces) / sum(f.calc_area() for f in faces))

    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bm = bmesh.from_edit_mesh(me)
    uvl = bm.loops.layers.uv.active
    rest = [f for f in bm.faces if not on_deck(f.calc_center_median())]
    d0 = density(rest, uvl)
    for f in bm.faces:
        f.select_set(False)
    n = 0
    for f in bm.faces:
        if on_deck(f.calc_center_median()):
            f.select_set(True)
            n += 1
    bm.select_flush_mode()
    bmesh.update_edit_mesh(me)
    bpy.ops.uv.smart_project(angle_limit=math.radians(DECK_UV_ANGLE), island_margin=0.003, scale_to_bounds=False)
    bm = bmesh.from_edit_mesh(me)
    uvl = bm.loops.layers.uv.active
    deck = [f for f in bm.faces if f.select]
    k = DECK_TEXELS * d0 / density(deck, uvl)
    for f in deck:
        for l in f.loops:
            l[uvl].uv *= k
    bmesh.update_edit_mesh(me)
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.uv.pack_islands(margin=0.002, rotate_method="CARDINAL")   # quarter turns only: straight strips stay straight
    except TypeError:
        bpy.ops.uv.pack_islands(margin=0.002)
    bm = bmesh.from_edit_mesh(me)
    uvl = bm.loops.layers.uv.active
    rest = [f for f in bm.faces if not on_deck(f.calc_center_median())]
    deck = [f for f in bm.faces if on_deck(f.calc_center_median())]
    print(f"silver: unwrap {n} deck faces of {len(bm.faces)}; uv per unit: rest {density(rest, uvl):.3f} (alone {d0:.3f}), "
          f"deck {density(deck, uvl):.3f}")


def fill_unbaked(img):
    """Every texel the bake and its margin left untouched (cleared: red 0; a baked texel's red is never 0)
    takes its nearest baked neighbours' colour, so no black lies between the islands for the mip levels to
    bleed in as dark specks, and an island too small to own a texel (a bolt head) still gets its
    surroundings' tone, not a black dot."""
    import numpy as np
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)
    done = a[:, :, 0] > 0
    left = int((~done).sum())
    for _ in range(max(w, h)):
        if done.all():
            break
        acc = np.zeros((h, w, 3), np.float32)
        cnt = np.zeros((h, w), np.float32)
        pd = np.pad(done, 1)
        pa = np.pad(a[:, :, :3] * done[:, :, None], ((1, 1), (1, 1), (0, 0)))
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                if dy == 1 and dx == 1:
                    continue
                acc += pa[dy:dy + h, dx:dx + w]
                cnt += pd[dy:dy + h, dx:dx + w]
        new = ~done & (cnt > 0)
        a[new, :3] = acc[new] / cnt[new][:, None]
        done |= new
    a[:, :, 3] = 1.0
    img.pixels.foreach_set(a.ravel())
    img.update()
    print(f"silver: {img.name} filled {left} unbaked texels of {w * h}")


def bake_maps(obj, out_dir, size=1024, samples=96):
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
        print("silver: no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    unwrap(me)
    bpy.ops.object.mode_set(mode="OBJECT")

    col_img = bpy.data.images.new("silver_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("silver_rm", size // 2, size // 2, alpha=False)
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

        def math_(op, a, b=None):
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
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.16
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.005
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
            tag = m.name.split("silver_")[-1]
            trim = (1.0, 1.0, 1.0)
            if tag in DECK_BAKE:
                gain, floor, trim = DECK_BAKE[tag]
                v = math_("MULTIPLY", math_("MINIMUM", math_("ADD", math_("ADD", floor, math_("MULTIPLY", occl, 1.0 - floor)),
                                                             math_("MULTIPLY", edge, 0.2)), 1.0), gain)
            else:
                v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                           math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(math_("MULTIPLY", v, TINT[k] * trim[k]), tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
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
        # The margin extends each island's own texels (not the face next to it across the seam, the
        # default): a face keeps its tone right up to its edge.
        bpy.ops.object.bake(type="EMIT", margin=6, margin_type="EXTEND", use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        fill_unbaked(img)
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for i in TEXTURED:
        m = mats[i]
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


def measure_top(obj, path, ss=8, w=24, h=28):
    """Looks straight down at the model on the sprite's grid: per sub-sample the palette index of the
    top surface (0 = nothing). Written as JSON for measure.py (IoU, per-region colours, overlays)."""
    pal = []
    for m in obj.data.materials:
        pal.append(int(m.name.split("_")[1]))
    deps = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(deps)
    rows = []
    for j in range(h * ss):
        y = (14 - (j + 0.5) / ss) * PX
        row = []
        for i in range(w * ss):
            x = ((i + 0.5) / ss - 12) * PX
            hit, loc, nrm, idx = ev.ray_cast(Vector((x, y, 5.0)), Vector((0, 0, -1)))
            row.append(pal[ev.data.polygons[idx].material_index] if hit else 0)
        rows.append(row)
    Path(path).write_text(json.dumps({"ss": ss, "w": w, "h": h, "rows": rows}))
    print(f"silver: top view written to {path}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = common.repo_root(__file__)
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(root, NAME)
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    obj = join(build(coll, mats), NAME)
    # The outline shell's source: the model with its slots, vents, throats and bores filled, plus ramps.
    closed = join(build(coll, mats, fill=True) + [finish(outline_fill(), [], coll)], f"{NAME}_closed")
    cull_hidden_sym(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"silver: {len(obj.data.polygons)} faces, {tris} triangles")
    # Engine glows for the menu backdrop (src/ui/backdrop.ts): just outside each scarfed exit, glTF axes.
    gx, gy = 5.0 + 0.6, 24.0 + 0.6
    obj["tyrian_engines"] = {"color": "#ff3a1c", "at": [[round((sx * gx + AXIS) * PX, 4), 0.0,
                                                          round((gy - 14) * PX, 4)] for sx in (-1, 1)]}
    if "--measure" in argv:
        measure_top(obj, argv[argv.index("--measure") + 1])
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = argv[argv.index("--bake-dir") + 1] if "--bake-dir" in argv else tempfile.mkdtemp(prefix="silver_bake_")
        Path(bake_dir).mkdir(parents=True, exist_ok=True)
        bake_maps(obj, bake_dir)
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it: from 0.3 px voxels,
    # coarse enough to bridge the seams, vents and the deck's channels. No `inside` pull (D90): as
    # common.outline_shell sets that shrinkwrap (INSIDE mode, a negative offset), Blender 5.2 leaves the
    # pulled vertices 0.05 px OUTSIDE the hull, not inside it (measured: 546 of the shell's 3300 vertices,
    # all in creases), and there the shell's crumpled triangles drew as dark hairline spikes (the pipes'
    # flanges, the cooling slots' corners, the canard and strake roots). Voxel and smoothing were chosen by
    # the ink the shell draws over the model's interior in the viewer's judged cameras (Top, Game, front-high,
    # three-quarter-high; --no-ink builds the reference): none in Top and Game.
    shell = common.outline_shell(closed, coll, voxel=0.025, faces=3000, smooth=8)
    if "--no-ink" in argv:
        for v in shell.data.vertices:
            v.co *= 0.001
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    print(f"silver: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(root, [obj, shell], MODEL,
                                   common.with_bank_roll(sprite["sprites"], BANK_ROLL, BANK_SHIFT), image_format=fmt)
    if "--preview" in argv:
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = root / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=level["size"])


if __name__ == "__main__":
    main()
