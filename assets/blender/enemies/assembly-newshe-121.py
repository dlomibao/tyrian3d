"""Lava larva (newshe.shp assembly of 8 pieces, episode 3 level 3.7 STARGATE).

A giant segmented lava grub lying along the screen, head on the left, crawling left over the
ground. Eight 2x2 ground enemies (newshe-77/-79/-81/-83 over -115/-117/-119/-121, one frame each)
make one 96 x 56 px creature; it is built once in assembly coordinates and cut into the pieces.

Build, from the sprite (the inner mask, D74, sets every part's outline column by column):
- body: a head, a collar and seven armoured plates (six body segments and the tail cap), each a
  pchip loft of rounded-tube sections (crown lifted toward the dorsal knob line, sides rolled under
  to a flat belly). Each plate's front is tucked under the plate before it (shingled, front over
  back) and that tucked lip glows molten along the crown: the sprite's bright seams at columns 37,
  47, 54, 63, 71, 77 and 83. The plate's rear is a rounded rim.
- head: two glowing eyes in hot sockets, a dark mouth under them behind a glowing lower lip.
- pink tubercles: a collar of three behind the eyes, one on each plate's rear rim, one on the tail
  end, and a hooked pink stinger curling down the tail's right end.
- a long feeler from under the belly curling forward to a free tip under the chin, with two pink
  pads, and a thin hind leg along the bottom edge from a knee joint.
Highlights are sheen, never bumps; the underside is a plain rolled belly.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshe-121.py
Exports each piece (with its outline shell) to public/models/enemies/<piece>.glb and its
src/render/spriteModels entry. Add -- --measure [DIR] to write report.json, pal.json and review
views to DIR (default: a new temp folder).
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[3] / "tools")]
import common  # noqa: E402
WT = common.repo_root(__file__)
import sprite_mask as SM  # noqa: E402
from usp_talon import pchip  # noqa: E402

NAME = "assembly-newshe-121"
PIECES = ["newshe-121", "newshe-119", "newshe-117", "newshe-115",
          "newshe-83", "newshe-81", "newshe-79", "newshe-77"]
CX0, CY0 = 249, 15  # screen centre of the 96 x 56 block (its top-left is screen 201, -13)


def X(e):
    """Assembly column edge coordinate (pixel c spans e = c .. c+1) to Blender X."""
    return (e - 48) / 12


def Y(s):
    """Assembly row edge coordinate to Blender Y (sprite up is +Y)."""
    return (28 - s) / 12


# --- the sprite's inner mask -------------------------------------------------------------------

_idx, _colors = SM.load(NAME)
MASKS = SM.masks(_idx, _colors, [])
INNER = MASKS["inner"]


def first_run(c):
    """(top edge, bottom edge) of the first inner run from the top in column c."""
    rows = [r for r in range(len(INNER)) if INNER[r][c]]
    if not rows:
        return None
    r0 = rows[0]
    r1 = r0
    while r1 + 1 < len(INNER) and INNER[r1 + 1][c]:
        r1 += 1
    return float(r0), float(r1 + 1)


# Body bottom overrides (edge rows): under the left lobe the feeler and its pads take the bottom.
BELLY_CAP = {34: 47.6, 35: 47.6, 36: 47.6, 37: 47.6, 38: 47.6, 39: 47.4, 40: 47.2, 41: 47.0}


def column_edges(c):
    t, b = first_run(c)
    if c in BELLY_CAP:
        b = min(b, BELLY_CAP[c])
    return t, b


def smooth(vals, k=(0.25, 0.5, 0.25)):
    out = []
    for i in range(len(vals)):
        a = vals[max(i - 1, 0)]
        b = vals[i]
        c = vals[min(i + 1, len(vals) - 1)]
        out.append(k[0] * a + k[1] * b + k[2] * c)
    return out


class Profile:
    """A plate's outline: top and bottom edge rows as smooth functions of the column edge e,
    from the mask columns whose centres lie in [e0, e1] (lightly smoothed, pchip between)."""

    def __init__(self, e0, e1, smooth_top=True, smooth_bot=True, extra=()):
        cols = [c for c in range(96) if e0 - 0.5 <= c + 0.5 <= e1 + 0.5 and first_run(c)]
        xs = [c + 0.5 for c in cols]
        ts = [column_edges(c)[0] for c in cols]
        bs = [column_edges(c)[1] for c in cols]
        if smooth_top:
            ts = smooth(ts)
        if smooth_bot:
            bs = smooth(bs)
        for x, t, b in extra:
            i = next((j for j, xx in enumerate(xs) if xx > x), len(xs))
            xs.insert(i, x)
            ts.insert(i, t)
            bs.insert(i, b)
        self.top = pchip(xs, ts)
        self.bot = pchip(xs, bs)


# --- geometry ----------------------------------------------------------------------------------

N_RING = 22
CROWN = 0.16  # crown shift toward the sprite's top edge, as a share of the half width
ZC = 0.30  # side bulge (widest point) height as a share of the section's height


def height_for(hw):
    """Section height (units) for a half width (units): a round, low-slung grub."""
    return 0.62 * hw + 0.10


def ring_point(yc, w, H, a, crown=CROWN, zc=ZC):
    """Point of a section at angle a (0 = sprite-top edge, pi/2 = crown, pi = bottom edge, then
    under the belly)."""
    s = math.sin(a)
    y = yc + w * (math.cos(a) + (crown * s * s if s > 0 else 0.0))
    if s >= 0:
        z = zc * H + (1 - zc) * H * s ** 0.85
    else:
        z = zc * H * (1 + s)
    return y, z


def section(e, top, bot, hscale=1.0, wscale=1.0, hmin=0.0):
    yt, yb = Y(top), Y(bot)
    yc, w = (yt + yb) / 2, (yt - yb) / 2 * wscale
    H = max(height_for((yt - yb) / 2) * hscale, hmin)
    return yc, w, H


def loft(bm, rings_spec, mat_of=lambda i, k, a: 0, smooth_shade=True):
    """rings_spec: list of (x, yc, w, H). Closed loft with fan caps. mat_of(i, k, a) picks a
    face's material from its ring index, ring position and angle."""
    rings = []
    angs = [2 * math.pi * k / N_RING for k in range(N_RING)]
    for x, yc, w, H in rings_spec:
        ring = []
        for a in angs:
            y, z = ring_point(yc, w, H, a)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for k in range(N_RING):
            j = (k + 1) % N_RING
            f = bm.faces.new((r0[k], r1[k], r1[j], r0[j]))
            f.material_index = mat_of(i, k, (angs[k] + angs[j] + (2 * math.pi if j == 0 else 0)) / 2)
            f.smooth = smooth_shade
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        x = ring[0].co.x
        cy = sum(v.co.y for v in ring) / len(ring)
        cz = sum(v.co.z for v in ring) / len(ring)
        c = bm.verts.new((x, cy, cz))
        for k in range(N_RING):
            j = (k + 1) % N_RING
            vs = (c, ring[j], ring[k]) if rev else (c, ring[k], ring[j])
            f = bm.faces.new(vs)
            f.material_index = mat_of(0 if rev else len(rings) - 2, k, angs[k])
            f.smooth = smooth_shade
    return rings


def smoothstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# Plates: (name, front edge, rear edge, material, front lip glows, snout/tail rounding)
PLATES = [
    ("head", 8.7, 27.8, "HEAD", False),
    ("collar", 27.2, 36.8, "BODY", False),
    ("seg1", 36.5, 47.8, "BODY", True),
    ("seg2", 47.5, 54.8, "BODY", True),
    ("seg3", 54.5, 63.8, "BODY", True),
    ("seg4", 63.5, 71.8, "BODY", True),
    ("seg5", 71.5, 77.8, "BODY", True),
    ("seg6", 77.5, 83.4, "BODY", True),
    ("tail", 83.1, 93.2, "TAIL", True),
]
LIP_PX = 1.5
RIM_PX = 0.9  # each plate's polished rear rim  # width of each plate's tucked, glowing front lip


class Plate:
    def __init__(self, name, e0, e1, mat, glow):
        self.name, self.e0, self.e1, self.mat, self.glow = name, e0, e1, mat, glow
        extra = ()
        self.prof = Profile(e0, e1, extra=extra)
        n = 12
        self.mean_hw = sum((Y(self.prof.top(e)) - Y(self.prof.bot(e))) / 2
                           for e in (e0 + (e1 - e0) * (i + 0.5) / n for i in range(n))) / n

    def mods(self, e):
        """(height scale, width scale) along the plate."""
        f = (e - self.e0) / (self.e1 - self.e0)
        L = self.e1 - self.e0
        d0, d1 = (e - self.e0), (self.e1 - e)  # px from the front / rear edge
        if self.name == "head":
            # rounded snout at the front, full to the rear (the collar tucks under it)
            # a bulbous dome: rounded snout, taller than the plates' rule for its width
            r = 3.4
            k = math.sqrt(max(0.0, 1 - ((r - min(d0, r)) / r) ** 2))
            hs = 1.28 * (0.34 + 0.66 * k ** 0.7)
            ws = 0.10 + 0.90 * k
            hs *= 1.0 - 0.06 * smoothstep(1 - d1 / 1.0)
            return hs, ws
        if self.name == "tail":
            r = 2.2
            k = math.sqrt(max(0.0, 1 - ((r - min(d1, r)) / r) ** 2))
            front = 0.86 + 0.14 * smoothstep(d0 / 2.0)
            return front * (0.35 + 0.65 * k), (0.97 + 0.03 * smoothstep(d0 / 1.2)) * (0.15 + 0.85 * k)
        # a barrel: each plate crests a little behind its middle, its front tucked low under the
        # rim of the plate before it, its rear rolling down to a rim (dark valleys between plates)
        front = 0.78 + 0.22 * smoothstep(d0 / (0.38 * L))
        rear = 1.0 - 0.16 * smoothstep(1 - d1 / (0.3 * L))
        ws = (0.975 + 0.025 * smoothstep(d0 / 1.2)) * (1.0 - 0.012 * smoothstep(1 - d1 / 0.8))
        return front * rear, ws

    def section_at(self, e):
        hs, ws = self.mods(e)
        t, b = self.prof.top(e), self.prof.bot(e)
        yc, w, H = section(e, t, b, hscale=hs, wscale=ws)
        if self.name != "head":
            # the crest follows the plate's mean width, not the sprite's bumps column by column
            H = 0.35 * H + 0.65 * height_for(self.mean_hw) * hs
        return yc, w, H

    def build(self, bm, M):
        n = max(8, int(round((self.e1 - self.e0) * 1.6)))
        es = [self.e0 + (self.e1 - self.e0) * i / n for i in range(n + 1)]
        if self.name in ("head", "tail"):  # denser at the rounded end
            extra = [self.e0 + d for d in (0.15, 0.4, 0.75, 1.1)] if self.name == "head" else \
                [self.e1 - d for d in (0.15, 0.4, 0.75, 1.1)]
            es = sorted(set(round(v, 3) for v in es + extra))
        else:
            es = sorted(set(round(v, 3) for v in es + [self.e0 + LIP_PX, self.e0 + 0.4]))
        spec = []
        for e in es:
            yc, w, H = self.section_at(e)
            spec.append((X(e), yc, w, H))
        base = M[self.mat]

        def mat_of(i, k, a):
            e_mid = (es[i] + es[min(i + 1, len(es) - 1)]) / 2
            if self.glow and e_mid < self.e0 + LIP_PX:
                s = math.sin(a)
                if s > 0.72:
                    return M["GLOW"]
                return M["DARK"]
            if self.name not in ("head", "tail") and e_mid > self.e1 - RIM_PX and math.sin(a) > -0.2:
                return M["RIM"]
            return base

        loft(bm, spec, mat_of)

    def surface(self, e, s):
        """Top surface height over (e, s), or None outside the plate's outline."""
        yc, w, H = self.section_at(e)
        y = Y(s)
        if w <= 0:
            return None
        lo, hi = 0.0, math.pi  # y decreases with a on [0, pi]
        if y > ring_point(yc, w, H, 0.0)[0] or y < ring_point(yc, w, H, math.pi)[0]:
            return None
        for _ in range(40):
            mid = (lo + hi) / 2
            if ring_point(yc, w, H, mid)[0] > y:
                lo = mid
            else:
                hi = mid
        return ring_point(yc, w, H, (lo + hi) / 2)[1]


def surface_z(plates, e, s):
    best = None
    for p in plates:
        if p.e0 <= e <= p.e1:
            z = p.surface(e, s)
            if z is not None and (best is None or z > best):
                best = z
    return best if best is not None else 0.0


def ellipsoid(bm, e, s, z, rx_px, ry_px, rz, mat, segs=14, rings=7, flat_bottom=None):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        co = v.co.copy()
        v.co = Vector((X(e) + co.x * rx_px / 12, Y(s) + co.y * ry_px / 12, z + co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


def tube(bm, path, mat, sides=10, tip_start=False, tip_end=False):
    """A tube along path [(e, s, z, half width px, half height units)], tapered to points where
    asked; caps closed."""
    pts = [Vector((X(e), Y(s), z)) for e, s, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (e, s, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.normalize()
        side = t.cross(up)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        nrm = side.cross(t).normalized()
        if (i == 0 and tip_start) or (i == len(path) - 1 and tip_end):
            rings.append([bm.verts.new(pts[i])])
            continue
        rings.append([bm.verts.new(pts[i] + side * (w / 12 * math.cos(2 * math.pi * k / sides))
                                   + nrm * (h * math.sin(2 * math.pi * k / sides)))
                      for k in range(sides)])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                faces.append(bm.faces.new((r0[0], r1[k], r1[j])))
            elif len(r1) == 1:
                faces.append(bm.faces.new((r0[k], r1[0], r0[j])))
            else:
                faces.append(bm.faces.new((r0[k], r1[k], r1[j], r0[j])))
    if len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = True


def resample(path, step=0.6):
    """Densify a centreline [(e, s, w)] with pchip in its arc parameter."""
    d = [0.0]
    for (e0, s0, *_), (e1, s1, *_) in zip(path, path[1:]):
        d.append(d[-1] + math.hypot(e1 - e0, s1 - s0))
    fs = [pchip(d, [p[i] for p in path]) for i in range(len(path[0]))]
    n = max(2, int(d[-1] / step))
    return [tuple(f(d[-1] * i / n) for f in fs) for i in range(n + 1)]


# --- the creature ------------------------------------------------------------------------------

def merged_sprite():
    data = common.load_sprite(WT, "newshe-121")
    for name in PIECES:
        data["colors"].update(common.load_sprite(WT, name)["colors"])
    return data


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshe121"

    def pal(i, **kw):
        return common.palette_material(sprite, i, tag, **kw)

    mats = {
        "BODY": pal(114, metallic=0.3, roughness=0.34),   # plates: the sprite's dark lava crust
        "RIM": common.palette_material(sprite, 114, tag + "rim", metallic=0.65, roughness=0.2),
        "HEAD": pal(115, metallic=0.3, roughness=0.34),   # head and tail cap: a step lighter
        "TAIL": pal(115, metallic=0.3, roughness=0.34),
        "DARK": pal(113, metallic=0.1, roughness=0.5),    # seams' flanks, mouth, eye sockets
        "GLOW": pal(121, metallic=1.0, roughness=0.85, emission_strength=1.0),  # molten seams
        "EYE": pal(126, metallic=1.0, roughness=0.85, emission_strength=1.0),
        "SOCKET": pal(123, metallic=1.0, roughness=0.85, emission_strength=1.0),
        "LIP": pal(120, metallic=0.6, roughness=0.6, emission_strength=0.4),
        "KNOB": pal(72, metallic=0.1, roughness=0.4),     # pink tubercles
        "COLLAR": pal(70, metallic=0.1, roughness=0.4),
        "KBASE": pal(66, metallic=0.1, roughness=0.6),     # their dark sockets
        "FEELER": pal(114, metallic=0.3, roughness=0.34),
        "PAD": pal(68, metallic=0.15, roughness=0.4),
    }
    order = list(mats)
    M = {k: order.index(k) for k in order}
    bm = bmesh.new()

    plates = [Plate(*p) for p in PLATES]
    for p in plates:
        p.build(bm, M)

    def sz(e, s):
        return surface_z(plates, e, s)

    # Eyes: glowing domes in hot sockets (sprite cores: cols 21-26 rows 12-16, cols 21-28 rows 19-22).
    for e, s, rx, ry in ((24.0, 14.6, 2.7, 2.2), (25.0, 21.0, 3.4, 1.9)):
        z = sz(e, s)
        ellipsoid(bm, e, s, z - 0.07, rx + 1.3, ry + 1.1, 0.11, M["DARK"], segs=16)
        ellipsoid(bm, e, s, z - 0.05, rx + 0.8, ry + 0.6, 0.12, M["SOCKET"], segs=16)
        ellipsoid(bm, e, s, z - 0.05, rx, ry, 0.15, M["EYE"], segs=16)

    # Mouth: a dark wide opening under the eyes, behind a glowing lower lip.
    # One wide opening (sprite rows 24-29, cols 14-28), set into the dome along its slope.
    mouth = [(13.4, 26.4, 1.4), (15.5, 26.6, 2.3), (19.0, 26.9, 2.7), (23.0, 27.1, 2.7),
             (26.5, 27.2, 2.3), (28.3, 27.4, 1.3)]
    mouth = resample(mouth, 0.7)
    tube(bm, [(e, s, sz(e, s) - 0.075, w, 0.09) for e, s, w in mouth], M["DARK"], sides=10)
    lip = [(11.0, 25.4, 0.8), (11.8, 28.4, 1.0), (13.6, 30.6, 1.15), (17.0, 31.8, 1.25),
           (21.5, 31.6, 1.2), (25.5, 30.8, 1.0), (28.6, 29.8, 0.7)]
    lip = resample(lip, 0.8)
    tube(bm, [(e, s, sz(e, s) - 0.03, w, 0.05) for e, s, w in lip], M["LIP"], sides=8)

    # Pink tubercles: (e, s, rx px, ry px, rz units, material)
    knobs = [
        (33.4, 12.9, 2.3, 1.9, 0.13, "COLLAR"), (33.6, 18.4, 2.3, 2.2, 0.14, "COLLAR"),
        (31.6, 24.6, 2.0, 1.4, 0.11, "COLLAR"), (30.4, 10.3, 1.2, 1.1, 0.08, "COLLAR"),
        (45.4, 13.8, 2.0, 1.6, 0.12, "KNOB"), (54.8, 14.9, 2.2, 1.4, 0.11, "KNOB"),
        (63.8, 16.8, 2.2, 1.5, 0.11, "KNOB"), (71.0, 18.9, 1.8, 1.5, 0.10, "KNOB"),
        (76.5, 20.6, 1.5, 1.9, 0.10, "KNOB"), (87.6, 22.0, 2.4, 2.6, 0.12, "KNOB"),
    ]
    for e, s, rx, ry, rz, m in knobs:
        z = sz(e, s)
        # a low tubercle in a dark collar ring, sunk to half its height
        ellipsoid(bm, e, s, z - 0.035, rx + 0.7, ry + 0.6, 0.06, M["KBASE"], segs=12, rings=6)
        ellipsoid(bm, e, s, z - 0.45 * rz, rx, ry, rz, M[m], segs=12, rings=6)

    # Stinger: a pink hook curling down the tail's right end to a point (sprite cols 82-91).
    sting = [(91.4, 21.8, 1.1), (91.6, 25.0, 1.1), (90.9, 28.6, 1.0), (89.4, 30.8, 0.95),
             (87.4, 32.4, 0.85), (85.0, 33.4, 0.65), (82.6, 33.6, 0.0)]
    sting = resample(sting, 0.7)
    path = []
    for e, s, w in sting:
        z = sz(min(e, 91.6), s)
        path.append((e, s, max(z, 0.08) + 0.01, max(w, 0.05), max(w, 0.05) * 0.075))
    tube(bm, path, M["KNOB"], sides=8, tip_end=True)

    # Feeler: from under the belly (col 45) forward along the bottom edge, curling up to a free
    # tip under the chin (sprite cols 9-45, rows 39-50).
    feeler = [(10.2, 39.6, 0.0), (11.3, 41.3, 0.75), (12.8, 43.2, 0.95), (14.6, 45.0, 1.0),
              (17.0, 46.9, 1.05), (20.0, 48.4, 1.1), (23.5, 49.4, 1.35), (27.5, 49.7, 1.45),
              (31.5, 49.6, 1.45), (35.5, 49.2, 1.5), (39.5, 48.3, 1.35), (43.5, 46.6, 1.3),
              (46.0, 44.5, 1.3)]
    feeler = resample(feeler, 0.7)
    zf = lambda e: 0.085 + 0.08 * smoothstep((e - 38.0) / 8.0)  # noqa: E731
    tube(bm, [(e, s, zf(e), max(w, 0.05), max(w, 0.05) * 0.08) for e, s, w in feeler],
         M["FEELER"], sides=10, tip_start=True)
    # Pads on the feeler (pink-brown, sprite cols 27-30 row 49 and cols 38-41 rows 46-48).
    for e, s, rx, ry in ((28.6, 49.5, 1.9, 1.3), (35.6, 49.2, 1.6, 1.3), (40.2, 47.9, 1.8, 1.3)):
        ellipsoid(bm, e, s, zf(e) + 0.03, rx, ry, 0.1, M["PAD"])

    # Hind leg: a knee joint at the bottom edge (sprite cols 56-62 rows 41-46) and a thin shin
    # running forward along the bottom edge to a foot (row 48, cols 46-57).
    leg = [(61.4, 41.0, 1.3), (60.6, 43.6, 1.25), (58.8, 46.0, 1.0), (56.5, 47.6, 0.85),
           (53.0, 48.5, 0.75), (49.5, 48.6, 0.72), (47.0, 48.4, 0.8), (45.6, 47.6, 0.9)]
    leg = resample(leg, 0.6)
    zl = lambda e: 0.07 + 0.12 * smoothstep((e - 55.0) / 6.0)  # noqa: E731
    tube(bm, [(e, s, zl(e), w, w * 0.075) for e, s, w in leg], M["FEELER"], sides=8)
    ellipsoid(bm, 60.4, 43.6, zl(60.4) + 0.02, 1.7, 1.8, 0.12, M["PAD"])  # knee
    ellipsoid(bm, 46.2, 48.0, 0.07, 1.3, 1.0, 0.07, M["PAD"])  # foot

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for k in order:
        mesh.materials.append(mats[k])
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj, coll


# --- outline shells: one per loose part (common.outline_shell keeps only the largest island) ---

def outline_shell_all(obj, collection, voxel=0.012, faces=1500, smooth=6, inside=0.008, min_faces=40):
    """common.outline_shell, but every outer island of the remesh keeps its shell: a piece cut from
    the creature can hold disjoint parts (the feeler's tip, the leg). An island whose bounding box
    lies inside another's (a cavity) is dropped."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    collection.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
    common._apply_modifiers(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.verts.ensure_lookup_table()
    seen, islands = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append(x)
            stack.extend(e.other_vert(x) for e in x.link_edges)
        islands.append(isl)

    # A cavity (an inner shell of the remesh) faces inward: negative signed volume. Keep the rest.
    vid = {}
    for i, isl in enumerate(islands):
        for v in isl:
            vid[v.index] = i
    vol = [0.0] * len(islands)
    for f in bm.faces:
        vs = [v.co for v in f.verts]
        for k in range(1, len(vs) - 1):
            vol[vid[f.verts[0].index]] += vs[0].dot(vs[k].cross(vs[k + 1])) / 6
    keep, kept = set(), 0
    for i, isl in enumerate(islands):
        if len(isl) < min_faces or vol[i] <= 0:
            continue
        kept += 1
        keep.update(v.index for v in isl)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    common._apply_modifiers(shell)
    if inside > 0:
        sw = shell.modifiers.new("inside", "SHRINKWRAP")
        sw.target = obj
        sw.wrap_method = "NEAREST_SURFACEPOINT"
        sw.wrap_mode = "INSIDE"
        sw.offset = -inside
        common._apply_modifiers(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell, len(islands), kept


def loose_parts(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    seen, n = set(), 0
    for v in bm.verts:
        if v.index in seen:
            continue
        n += 1
        stack = [v]
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            stack.extend(e.other_vert(x) for e in x.link_edges)
    bm.free()
    return n


# --- measuring ---------------------------------------------------------------------------------

def raycast_grid(obj, k):
    """Top view of obj (at the origin) on the 96 x 56 sprite grid, k x k rays per pixel: rows of
    bools, plus per pixel centre (palette index, height)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mats = [m.name for m in obj.data.materials]
    top = []
    for yy in range(56 * k):
        s = (yy + 0.5) / k
        row = []
        for xx in range(96 * k):
            e = (xx + 0.5) / k
            hit, *_ = ev.ray_cast(Vector((X(e), Y(s), 5.0)), Vector((0, 0, -1)))
            row.append(bool(hit))
        top.append(row)
    pal = [[None] * 96 for _ in range(56)]
    hgt = [[0.0] * 96 for _ in range(56)]
    for r in range(56):
        for c in range(96):
            hit, loc, nrm, fi = ev.ray_cast(Vector((X(c + 0.5), Y(r + 0.5), 5.0)), Vector((0, 0, -1)))
            if hit:
                mi = obj.data.polygons[fi].material_index
                pal[r][c] = int(mats[mi].split("_")[1])
                hgt[r][c] = loc.z
    return top, pal, hgt


def measure(obj):
    k = 6
    top, pal, hgt = raycast_grid(obj, k)
    whole = SM.measure(MASKS, top)
    out = {"whole": whole}
    # per piece windows
    first = common.load_sprite(WT, "newshe-121")
    for e in first["assemblyLayout"]:
        if e["model"] not in PIECES:
            continue
        x0, y0 = e["cx"] - 12 - 201, e["cy"] - 14 + 13
        pidx, pcol = SM.load(e["model"])
        pm = SM.masks(pidx, pcol, [])
        sub = [row[x0 * k:(x0 + 24) * k] for row in top[y0 * k:(y0 + 28) * k]]
        out[e["model"]] = SM.measure(pm, sub)
    # grid diff map
    g = [[sum(top[r * k + j][c * k + i] for j in range(k) for i in range(k)) / (k * k) >= 0.5
          for c in range(96)] for r in range(56)]
    diff = []
    for r in range(56):
        line = ""
        for c in range(96):
            s, m, fr = INNER[r][c], g[r][c], MASKS["free"][r][c]
            line += ("#" if s and m else "-" if s else "+" if m and not fr else "f" if fr and m else
                     "o" if MASKS["outer"][r][c] else ".")
        diff.append(line)
    out["diff"] = diff
    # colours per region: model's majority index vs sprite median
    import collections
    regions = {
        "plates": (38, 75, 10, 40), "head": (10, 20, 12, 22), "eye_up": (22, 25, 13, 15),
        "eye_lo": (22, 27, 20, 21), "mouth": (17, 26, 25, 28), "collar_knobs": (31, 35, 11, 20),
        "dorsal_knob1": (44, 46, 13, 14), "tail_knob": (86, 89, 20, 23), "feeler": (14, 32, 45, 49),
    }
    col = {}
    for n, (c0, c1, r0, r1) in regions.items():
        cnt = collections.Counter(pal[r][c] for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
                                  if pal[r][c] is not None)
        col[n] = cnt.most_common(3)
    out["colour"] = col
    out["max_height"] = max(max(r) for r in hgt)
    return out, pal, hgt


# --- review renders ----------------------------------------------------------------------------

def setup_render():
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.30, 0.33, 0.36, 1)
    bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    # The game's sun (src/render/sun.ts): from the left, the camera's side, mostly above.
    sun.rotation_euler = Vector((6, 8.4, -20)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.8
    fill.rotation_euler = Vector((-0.4, -0.6, -0.4)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def render_views(obj, out):
    out.mkdir(parents=True, exist_ok=True)
    scene, cam = setup_render()

    def look(loc, target):
        cam.location = Vector(loc)
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()

    def shoot(name, w, h, ortho=None, lens=50):
        scene.render.resolution_x, scene.render.resolution_y = w, h
        if ortho:
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = ortho
        else:
            cam.data.type = "PERSP"
            cam.data.lens = lens
        cam.data.clip_end = 100
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    c = Vector((0, 0, 0.35))
    cam.location = (0, 0, 10)
    cam.rotation_euler = (0, 0, 0)
    shoot("top", 960, 560, ortho=8.0)
    look((0, -12, 0.4), (0, 0, 0.4))
    shoot("side", 960, 300, ortho=8.4)          # long flank, from the screen bottom
    look((0, 12, 0.4), (0, 0, 0.4))
    shoot("side_far", 960, 300, ortho=8.4)      # far flank
    look((-12, 0, 0.5), (0, 0, 0.5))
    shoot("front", 620, 300, ortho=5.8)         # the head on
    look((12, 0, 0.5), (0, 0, 0.5))
    shoot("rear", 620, 300, ortho=5.8)
    look((-7.5, -7.0, 5.5), c)
    shoot("q_front", 760, 480, lens=55)
    look((7.5, -6.5, 5.0), c)
    shoot("q_rear", 760, 480, lens=55)
    a = math.radians(15)
    look((0, -26 * math.sin(a), 26 * math.cos(a)), c)
    shoot("game", 960, 600, lens=105)
    look((-6.0, -6.5, 1.6), c)
    shoot("low", 760, 420, lens=50)
    cam.location = (0, 0, -10)
    cam.rotation_euler = (math.pi, 0, 0)
    shoot("under", 760, 440, ortho=8.4)


# --- main --------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sprite = merged_sprite()
    obj, coll = build(sprite)
    report = {"whole_faces": len(obj.data.polygons),
              "whole_tris": sum(len(p.vertices) - 2 for p in obj.data.polygons)}
    HERE = None  # --measure output folder
    if "--measure" in argv:
        i = argv.index("--measure")
        HERE = Path(argv[i + 1]) if i + 1 < len(argv) and not argv[i + 1].startswith("--") \
            else Path(tempfile.mkdtemp(prefix="nshe121_measure_"))
        HERE.mkdir(parents=True, exist_ok=True)
        print("MEASURE_DIR", HERE)
        m, pal, hgt = measure(obj)
        report.update(m)
        (HERE / "pal.json").write_text(json.dumps({"pal": pal, "hgt": hgt}))
    first = common.load_sprite(WT, "newshe-121")
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in first["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout, coll)
    exported, info = [], {}
    for name, dx, dy in layout:
        p = pieces[name]
        shell, n_isl, kept = outline_shell_all(p, coll)
        info[name] = {"tris": sum(len(q.vertices) - 2 for q in p.data.polygons),
                      "parts": loose_parts(p), "shell_islands": f"{kept}/{n_isl}",
                      "shell_faces": len(shell.data.polygons)}
        exported.append((p, shell, dx, dy))
    report["pieces"] = info
    for p, shell, dx, dy in exported:
        data = common.load_sprite(WT, p.name)
        common.export_sprite_model(WT, [p, shell], f"enemies/{p.name}", data["sprites"])
    for p, shell, dx, dy in exported:
        p.location = (dx / 12, -dy / 12, 0)
        shell.location = (dx / 12, -dy / 12, 0)
    report["total_tris"] = sum(v["tris"] for v in info.values())
    if "--measure" in argv:
        for p, shell, *_ in exported:
            shell.hide_render = True
            p.hide_render = True
        obj.hide_render = False
        render_views(obj, HERE / "views")
        (HERE / "report.json").write_text(json.dumps(report, indent=1))
    print("REPORT", json.dumps({k: v for k, v in report.items() if k != "diff"})[:3000])


if __name__ == "__main__":
    main()
