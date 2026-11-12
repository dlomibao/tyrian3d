"""Side Ship (sidekick option 18, tyrian.shp#8 frames 245, 264, 283, 302), a 3D version of
its sprite to the player-ship hard-surface standard (DECISIONS D50-D53, D65, D74).

What it is: a mounted side pod (style 0) drawn as a tiny blue-steel escort fighter flying nose up the
screen beside the player's ship.

What the sprite shows (reference/models/sidekick-side-ship, 12x14, palette 5; x = column - 6,
y = row edge, z up, all in sprite px):
- rows 0-4: a pointed nose widening 2 -> 4 -> 6 px (columns 5-6, 4-7, 3-8): an ogive in plan;
- rows 2-4, columns 5-6: a pale canopy (137/142/139; the 142 spot is sheen);
- rows 5-8, columns 5-6: a lit dorsal spine (61/60, sheen on a raised fairing);
- row 6, columns 4 and 7: two lights, dark (55) on 245, red 115 / yellow 124 / orange 121 on
  264 / 283 / 302;
- rows 3-12, columns 3 and 8: the fuselage's lit flanks; rows 9-12 they are tail booms that run on
  to row 13 while the body between them ends at row 12 (columns 4/7 empty on row 12);
- rows 9-11, columns 4/7: a dark low aft deck between the booms and the engine;
- rows 10-12, columns 5-6: the engine's exposed core glowing (dim reds 67-76 on 245, orange and
  yellow 115-126 on the others), row 9 its dark collar, row 13 the exhaust flame;
- rows 9-12, columns 0-2 / 9-11: short low wings (dark, column 2/9) to round wingtip pods (columns
  0-1 / 10-11, a sheen streak on column 1/10), each pod carrying a slim forward gun barrel (column
  1/10, rows 6-8) and a small swept fin on its tail.

Design: a lofted fuselage of filleted, chamfered sections (pchip stations) with proud flank armour
plates and a recessed nose-cap seam; a glass bubble canopy on a frame sill; a chamfered spine; the
engine an emissive core cylinder (per-row glow bands, frame colours) between a steel collar and a
nozzle lip, with a separate emissive flame; booms, wings with a split flap, wingtip pods with
grooves, barrels with muzzle sleeves, swept fins. Underside: the same closed hull, nothing more.

Build: tools/build-models.sh -j 2 assets/blender/sidekicks/side-ship.py
Exports public/models/sidekicks/side-ship.glb and src/render/spriteModels/side-ship.json.
Scratch: -- [--nobake] [--views DIR] writes top/lit renders into DIR.
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
from usp_talon import Part, cbox, hull, pchip, frange, fillet  # noqa: E402

ROOT = common.repo_root(__file__)
WT = ROOT
MODEL = "sidekicks/side-ship"
NAME = "side-ship"
REF = f"sidekick-{NAME}"
HERE = Path(__file__).resolve().parent
PX = 1 / 12
ALL = [245, 264, 283, 302]

# Material slots.
(STEEL, STEEL_DK, NOSE, GLASS, FRAME, SPINE, WING, DEEP, LENS, DECK, POD,
 CORE10, CORE11, CORE12, FLAME, LAMP, BARREL) = range(17)


def materials(sprite):
    def pal(i, tag, metallic=0.45, roughness=0.4, **kw):
        return common.palette_material(sprite, i, f"sideship_{tag}", metallic=metallic, roughness=roughness, **kw)
    return [
        pal(59, "steel"),                       # hull: blue steel (cols 3/8, booms)
        pal(56, "steel_dk", 0.4, 0.5),          # core under the plates, seams, collar
        pal(58, "nose"),                        # nose cone (rows 0-1)
        pal(139, "glass", 0.0, 0.06),           # canopy
        pal(56, "frame", 0.5, 0.42),            # canopy sill
        pal(60, "spine", 0.5, 0.34),            # dorsal spine
        pal(54, "wing", 0.4, 0.46),             # wings (dark, low)
        pal(51, "deep", 0.2, 0.8),              # bores, exhausts, grooves
        pal(55, "lens", 0.1, 0.15),             # lamp lens (off on 245)
        pal(53, "deck", 0.4, 0.5),              # aft deck between booms and engine
        pal(58, "pod"),                         # wingtip pods
        # The engine's exposed core: the sprite's glow per row, per frame (palette_material frames=).
        pal(68, "core10", 0.0, 0.5, emission_strength=1.0, frames={264: 116, 283: 118, 302: 116}),
        pal(76, "core11", 0.0, 0.5, emission_strength=1.0, frames={264: 124, 283: 126, 302: 124}),
        pal(74, "core12", 0.0, 0.5, emission_strength=1.0, frames={264: 122, 283: 124, 302: 122}),
        pal(70, "flame", 0.0, 0.5, emission_strength=1.0, frames={264: 118, 283: 120, 302: 118}),
        # The lamps lit (frame part on 264/283/302).
        pal(115, "lamp", 0.0, 0.4, emission_strength=1.2, frames={283: 124, 302: 121}),
        pal(56, "barrel", 0.55, 0.36),          # gun barrels (col 1/10: 57/54/56)
    ]


# --- shapes (sprite px) --------------------------------------------------------------------------

# Fuselage plan half width (the sprite's 2-4-6 px steps as one smooth ogive), deck top and keel.
FW = pchip([0.0, 0.5, 1.0, 2.0, 3.0, 3.7, 4.5, 8.6, 9.3, 12.0],
           [0.45, 1.05, 1.55, 2.05, 2.62, 2.92, 3.0, 3.0, 2.86, 2.86])
FT = pchip([0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 8.3, 9.0, 9.6, 12.0],
           [0.1, 0.55, 0.9, 1.25, 1.47, 1.58, 1.62, 1.62, 1.05, 0.42, 0.4])
FB = pchip([0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 10.0, 12.0],
           [-0.25, -0.55, -0.85, -1.2, -1.42, -1.5, -1.5, -1.3])
FUSE_END = 12.0


def fus_loop(y, grow=0.0):
    """Fuselage section: flat deck, shoulder chamfer, flat flank, keel chamfer, flat keel; all corners
    filleted. Corner order c0 deck edge R, c1 shoulder R, c2 flank foot R, c3 keel edge R, then the
    left side c4..c7 (k = 2: three points per corner, so c_i sits at loop indices 3i..3i+2)."""
    w, t, b = FW(y) + grow, FT(y) + grow, FB(y) - grow
    h = t - b
    corners = [(0.5 * w, t), (w, t - 0.3 * h), (w, b + 0.3 * h), (0.55 * w, b),
               (-0.55 * w, b), (-w, b + 0.3 * h), (-w, t - 0.3 * h), (-0.5 * w, t)]
    s = min(1.0, w / 2.6)
    r = [0.45 * s, 0.5 * s, 0.5 * s, 0.4 * s, 0.4 * s, 0.5 * s, 0.5 * s, 0.45 * s]
    return fillet(corners, r, 2), (0.0, (t + b) / 2)


def deck_z(x, y):
    w, t, b = FW(y), FT(y), FB(y)
    ax = abs(x)
    if ax <= 0.5 * w:
        return t
    return t - 0.3 * (t - b) * min(1.0, (ax - 0.5 * w) / (0.5 * w))


def rrect(cx, cz, rx, rz, rad, k=2):
    """A filleted rectangle (a machined section) centred (cx, cz)."""
    corners = [(cx + rx, cz + rz), (cx + rx, cz - rz), (cx - rx, cz - rz), (cx - rx, cz + rz)]
    return fillet(corners, min(rad, 0.95 * min(rx, rz)), k), (cx, cz)


def circle(cx, cz, r, n=16, phase=0.5):
    return [(cx + r * math.cos(2 * math.pi * (i + phase) / n), cz + r * math.sin(2 * math.pi * (i + phase) / n))
            for i in range(n)], (cx, cz)


def loft_loops(part, rings, mats, cap0=True, cap1=True, tip0=None, tip1=None):
    """Loft through rings [(y, (pts, (cx, cz)))]; mats[i] between ring i and i+1 (mats[-1] caps).
    Two rings at the same y make a step (a groove wall). tip0/tip1 (y, z): fan the end to a point."""
    built = []
    for y, (pts, (cx, cz)) in rings:
        built.append(([part.v((x, y, z)) for x, z in pts], (cx, y, cz), y))
    for i in range(len(built) - 1):
        (r0, c0, y0), (r1, c1, y1) = built[i], built[i + 1]
        n = len(r0)
        for a in range(n):
            b = (a + 1) % n
            if abs(y1 - y0) < 1e-6:
                # groove wall: faces outward along y toward the side of the smaller ring
                ra = sum(abs(v.co.x - c0[0]) for v in r0)
                rb = sum(abs(v.co.x - c1[0]) for v in r1)
                part.f((r0[a], r0[b], r1[b], r1[a]), mats[i], out=(0, 1 if rb < ra else -1, 0))
            else:
                part.f((r0[a], r0[b], r1[b], r1[a]), mats[i], away=c0)
    for idx, cap, tip, sgn in ((0, cap0, tip0, -1), (-1, cap1, tip1, 1)):
        ring, c, y = built[idx]
        mat = mats[0] if idx == 0 else mats[-1]
        if tip is not None:
            tv = part.v((c[0], tip[0], tip[1]))
            n = len(ring)
            for a in range(n):
                part.f((ring[a], ring[(a + 1) % n], tv), mat, out=(0, sgn, 0))
        elif cap:
            part.f(ring, mat, out=(0, sgn, 0))
    return built


# --- parts -------------------------------------------------------------------------------------

def build_fuselage(p):
    # Nose cone (NOSE) to the recessed nose-cap seam at row 1.75, then the hull (STEEL) to the
    # aft bulkhead at row 12, chamfered in.
    g = 0.12
    ys = [0.02, 0.25, 0.55, 0.9, 1.3, 1.68]
    rings = [(y, fus_loop(y)) for y in ys]
    mats = [NOSE] * (len(ys) - 1)
    rings += [(1.68, fus_loop(1.68, -g)), (1.82, fus_loop(1.82, -g)), (1.82, fus_loop(1.82))]
    mats += [DEEP, DEEP, DEEP]
    for y in frange(2.1, 11.6, 1.2):
        rings.append((y, fus_loop(y)))
        mats.append(STEEL)
    rings += [(11.85, fus_loop(11.85)), (FUSE_END, fus_loop(FUSE_END, -0.18))]
    mats += [STEEL, STEEL]
    loft_loops(p, rings, mats, tip0=(-0.08, FT(0.0) * 0.4 + FB(0.0) * 0.6))
    # Flank armour plates (rows 3.3-8.5): from the shoulder chamfer down to the flank foot, 0.12 proud;
    # their chamfered edges and the gap to the deck are the panel lines.
    lf = lambda y: fus_loop(y)  # noqa: E731
    T.plate(p, lf, 3.3, 8.45, STEEL, s0=2.6, s1=6.9, d=0.12, c=0.1, depth=0.25, ystep=1.2)
    T.plate(p, lf, 3.3, 8.45, STEEL, s0=16.1, s1=20.4, d=0.12, c=0.1, depth=0.25, ystep=1.2)
    # Lower panel: a belly-side strip under each plate (machined, seen from the side).
    T.plate(p, lf, 4.2, 7.6, STEEL_DK, s0=7.4, s1=8.6, d=0.08, c=0.06, depth=0.2, ystep=0.8)
    T.plate(p, lf, 4.2, 7.6, STEEL_DK, s0=15.4, s1=16.6, d=0.08, c=0.06, depth=0.2, ystep=0.8)


def canopy_loop(y, grow=0.0):
    cw = pchip([1.85, 2.25, 3.0, 4.0, 4.6, 5.05], [0.2, 0.68, 0.93, 0.95, 0.84, 0.55])(y) + grow
    ch = pchip([1.85, 2.5, 3.3, 4.2, 4.7, 5.05], [0.12, 0.6, 0.86, 0.84, 0.68, 0.42])(y) + grow
    base = FT(y) - 0.25
    n = 10
    pts = []
    for i in range(n + 1):  # upper half-ellipse, a little squared off (superellipse)
        a = math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        x = cw * math.copysign(abs(c) ** 0.8, c)
        z = FT(y) + ch * abs(s) ** 0.8
        pts.append((x, z))
    pts += [(-cw, base), (cw, base)]
    return pts, (0.0, FT(y))


def build_canopy(p):
    ys = [1.85, 2.0, 2.3] + frange(2.6, 4.6, 0.4) + [4.85, 5.05]
    loft_loops(p, [(y, canopy_loop(y)) for y in ys], [GLASS] * (len(ys) - 1))
    # Sill: a thin frame round the canopy's foot.
    sill = []
    for y in [1.8, 2.1, 2.6, 3.4, 4.2, 4.8, 5.12]:
        cw = pchip([1.8, 2.25, 3.0, 4.0, 4.6, 5.12], [0.32, 0.8, 1.05, 1.07, 0.96, 0.66])(y)
        z = FT(y)
        sill.append((y, rrect(0.0, z + 0.04, cw, 0.12, 0.06, 1)))
    loft_loops(p, sill, [FRAME] * (len(sill) - 1))
    # Windshield bow: a slim frame across the canopy at row 2.45 (proud of the glass by 0.06).
    loft_loops(p, [(2.38, canopy_loop(2.38, 0.06)), (2.55, canopy_loop(2.55, 0.06))], [FRAME])


def build_spine(p):
    """A chamfered dorsal fairing from behind the canopy (row 4.9) to the engine collar (row 9.1)."""
    t = FT(6.0)
    hull(p, cbox(-0.95, 0.95, 4.85, 9.15, t - 0.4, t + 0.34, 0.2), SPINE)
    # A machined groove across it at row 7.2: two blocks with a gap.
    # (Implemented as a dark insert sunk across the spine.)
    hull(p, cbox(-0.98, 0.98, 7.12, 7.28, t - 0.3, t + 0.28, 0.03), DEEP)
    # Canopy rear fairing: a short wedge from the canopy's tail onto the spine.
    hull(p, [(-0.55, 4.6, t), (0.55, 4.6, t), (-0.9, 5.3, t), (0.9, 5.3, t),
             (-0.45, 4.75, t + 0.45), (0.45, 4.75, t + 0.45), (-0.8, 5.3, t + 0.34), (0.8, 5.3, t + 0.34)], SPINE)


def build_lamps(p, beads):
    """Two lamps on the deck's shoulders at row 6.5, columns 4 and 7 (x = +-1.5): a dark bezel and a
    lens; the lit bead is its own frame part (beads)."""
    for sx in (-1, 1):
        x, y = sx * 1.42, 6.5
        z = deck_z(x, y)
        n = 12
        bez = [(0.0, circle(0, 0, 0.5, n)), ]
        # bezel ring along z: build as a short vertical tube with a flat top
        for part, r_out, h, mat in ((p, 0.52, 0.12, DEEP), (p, 0.4, 0.2, LENS)):
            ring_lo = [part.v((x + r_out * math.cos(2 * math.pi * k / n), y + r_out * math.sin(2 * math.pi * k / n), z - 0.2))
                       for k in range(n)]
            ring_hi = [part.v((x + r_out * math.cos(2 * math.pi * k / n), y + r_out * math.sin(2 * math.pi * k / n), z + h))
                       for k in range(n)]
            for k in range(n):
                j = (k + 1) % n
                part.f((ring_lo[k], ring_lo[j], ring_hi[j], ring_hi[k]), mat, away=(x, y, z))
            top = part.v((x, y, z + h + (0.12 if mat == LENS else 0.0)))
            for k in range(n):
                part.f((ring_hi[k], ring_hi[(k + 1) % n], top), mat, out=(0, 0, 1))
        # lit bead
        rb = 0.36
        lo = [beads.v((x + rb * math.cos(2 * math.pi * k / n), y + rb * math.sin(2 * math.pi * k / n), z + 0.1)) for k in range(n)]
        mid = [beads.v((x + 0.7 * rb * math.cos(2 * math.pi * k / n), y + 0.7 * rb * math.sin(2 * math.pi * k / n), z + 0.36)) for k in range(n)]
        top = beads.v((x, y, z + 0.44))
        for k in range(n):
            j = (k + 1) % n
            beads.f((lo[k], lo[j], mid[j], mid[k]), LAMP, away=(x, y, z))
            beads.f((mid[k], mid[j], top), LAMP, out=(0, 0, 1))
        beads.f(lo, LAMP, out=(0, 0, -1))
        del bez


ENG_Z = 0.72  # engine axis height


def build_engine(p):
    """Collar (row 9.0-9.9, steel), exposed core (rows 9.9-12.75, glowing per row), nozzle lip."""
    rings = [
        (8.95, circle(0, ENG_Z, 0.9, 16)), (9.05, circle(0, ENG_Z, 1.08, 16)), (9.82, circle(0, ENG_Z, 1.08, 16)),
        (9.9, circle(0, ENG_Z, 0.94, 16)),
        (10.95, circle(0, ENG_Z, 0.96, 16)), (11.95, circle(0, ENG_Z, 0.98, 16)),
        (12.7, circle(0, ENG_Z, 0.98, 16)), (12.7, circle(0, ENG_Z, 1.04, 16)), (13.0, circle(0, ENG_Z, 1.02, 16)),
        (13.0, circle(0, ENG_Z, 0.7, 16)), (12.85, circle(0, ENG_Z, 0.55, 16)),
    ]
    mats = [STEEL_DK, STEEL_DK, STEEL_DK, CORE10, CORE11, CORE12, STEEL_DK, STEEL_DK, STEEL_DK, CORE12]
    loft_loops(p, rings, mats)
    # Three thin cooling-ring rails under the core's sides (not on top: the sprite shows the glow
    # across the whole top), as machined detail in side view.
    for y0 in (10.4, 11.4, 12.2):
        for sx in (-1, 1):
            hull(p, cbox(sx * 0.7 - 0.25, sx * 0.7 + 0.25, y0, y0 + 0.22, ENG_Z - 0.9, ENG_Z + 0.15, 0.06), STEEL_DK)


def build_flame(p):
    rings = [(12.98, circle(0, ENG_Z, 0.82, 12)), (13.4, circle(0, ENG_Z, 0.78, 12)),
             (13.75, circle(0, ENG_Z, 0.5, 12))]
    loft_loops(p, rings, [FLAME] * 2, tip1=(14.0, ENG_Z))


def boom_loop(sx, y):
    rz = pchip([8.2, 9.0, 12.4, 13.0], [0.55, 1.18, 1.18, 0.8])(y)
    cz = pchip([8.2, 9.0, 12.4, 13.0], [0.4, 0.05, 0.05, 0.05])(y)
    rx = pchip([8.2, 9.0, 12.5, 13.0], [0.38, 0.52, 0.52, 0.4])(y)
    cx = sx * pchip([8.2, 9.0, 13.0], [2.62, 2.5, 2.5])(y)
    return rrect(cx, cz, rx, rz, 0.32, 2)


def build_booms(p):
    for sx in (-1, 1):
        ys = [8.2, 8.6, 9.0, 10.7]
        rings = [(y, boom_loop(sx, y)) for y in ys]
        mats = [STEEL] * (len(ys) - 1)
        # panel groove at row 10.75
        (pts, c) = boom_loop(sx, 10.7)  # noqa
        sh = lambda d: ([(c[0] + (x - c[0]) * (1 - d), c[1] + (z - c[1]) * (1 - d)) for x, z in pts], c)  # noqa: E731
        rings += [(10.7, sh(0.07)), (10.78, sh(0.07)), (10.78, boom_loop(sx, 10.78))]
        mats += [DEEP, DEEP, DEEP]
        for y in [12.4, 12.8, 13.0]:
            rings.append((y, boom_loop(sx, y)))
            mats.append(STEEL)
        mats = mats[:len(rings) - 1]
        loft_loops(p, rings, mats)
        # exhaust port in the boom's tail
        cx = sx * 2.5
        hull(p, cbox(cx - 0.24, cx + 0.24, 12.85, 13.04, -0.2, 0.3, 0.06), DEEP)


WING_Z = -0.5


def build_wings(p):
    for sx in (-1, 1):
        def pts(x0, x1, y0, y1, t0, t1, le=True):
            out = []
            for x, t in ((x0, t0), (x1, t1)):
                ya = y0 + (x - x0) / (x1 - x0) * 0.12  # a slight sweep
                if le:
                    out += [(sx * x, ya, WING_Z), (sx * x, ya + 0.45, WING_Z + t / 2), (sx * x, ya + 0.45, WING_Z - t / 2)]
                else:
                    out += [(sx * x, ya, WING_Z + t / 2), (sx * x, ya, WING_Z - t / 2)]
                out += [(sx * x, y1 - 0.15, WING_Z + t / 2 * 0.8), (sx * x, y1 - 0.15, WING_Z - t / 2 * 0.8),
                        (sx * x, y1, WING_Z)]
            return out
        hull(p, pts(2.6, 4.4, 8.95, 11.08, 0.75, 0.55), WING)
        # The flap: a separate, thinner panel behind a gap (rows 11.2-12.0).
        hull(p, pts(2.75, 4.25, 11.2, 12.0, 0.5, 0.42, le=False), WING)


POD_CX, POD_CZ = 5.0, -0.42


def pod_loop(sx, y, d=0.0):
    k = pchip([8.85, 9.1, 9.55, 12.35, 12.75, 13.0], [0.45, 0.78, 1.0, 1.0, 0.86, 0.7])(y)
    return rrect(sx * POD_CX, POD_CZ, 0.98 * k - d, 0.8 * k - d, 0.7 * k, 2)


def build_pods(p):
    for sx in (-1, 1):
        ys = [8.85, 9.0, 9.2, 9.55, 10.6]
        rings = [(y, pod_loop(sx, y)) for y in ys]
        mats = [POD] * (len(ys) - 1)
        rings += [(10.6, pod_loop(sx, 10.6, 0.07)), (10.68, pod_loop(sx, 10.68, 0.07)), (10.68, pod_loop(sx, 10.68))]
        mats += [DEEP, DEEP, DEEP]
        for y in [12.35, 12.75, 13.0]:
            rings.append((y, pod_loop(sx, y)))
            mats.append(POD)
        loft_loops(p, rings, mats[:len(rings) - 1])
        # exhaust
        hull(p, cbox(sx * POD_CX - 0.4, sx * POD_CX + 0.4, 12.9, 13.03, POD_CZ - 0.3, POD_CZ + 0.3, 0.1), DEEP)
        # Gun barrel along the pod's inboard top (column 1/10), with a muzzle sleeve and a bore.
        bx, bz = sx * 4.5, 0.08
        rings = [(6.05, circle(bx, bz, 0.2, 10)), (6.05, circle(bx, bz, 0.4, 10)), (6.12, circle(bx, bz, 0.46, 10)),
                 (6.55, circle(bx, bz, 0.46, 10)), (6.62, circle(bx, bz, 0.36, 10)), (7.1, circle(bx, bz, 0.36, 10)),
                 (7.18, circle(bx, bz, 0.45, 10)), (8.95, circle(bx, bz, 0.45, 10)), (9.7, circle(bx, bz, 0.45, 10))]
        loft_loops(p, rings, [DEEP, BARREL, BARREL, BARREL, BARREL, BARREL, BARREL, BARREL], tip0=(6.25, bz))
        # cooling-jacket rings on the barrel's rear half
        for yr in (7.7, 8.3):
            loft_loops(p, [(yr, circle(bx, bz, 0.49, 10)), (yr + 0.16, circle(bx, bz, 0.49, 10))], [BARREL])
        # A mount block under the barrel's breech onto the pod.
        hull(p, cbox(bx - 0.3, bx + 0.3, 8.7, 9.8, POD_CZ, bz, 0.08), POD)
        # Swept fin on the pod's tail top: a root 2.3 px long, its leading edge raked back to a tip
        # 1.5 px up, the trailing edge near vertical.
        fx, zb = sx * 5.0, POD_CZ + 0.62
        hull(p, [(fx - 0.2, 10.6, zb), (fx + 0.2, 10.6, zb), (fx - 0.2, 12.9, zb), (fx + 0.2, 12.9, zb),
                 (fx - 0.1, 12.15, zb + 1.5), (fx + 0.1, 12.15, zb + 1.5), (fx - 0.1, 12.95, zb + 1.55),
                 (fx + 0.1, 12.95, zb + 1.55)], POD)


def finish(part, mats, coll):
    """T.finish for a 12x14 sprite: X = x / 12, Y = (7 - y) / 12, Z = z / 12."""
    part.orient()
    bm = part.bm
    # The aft deck between the booms and the engine (columns 4/7, rows 9-11): the sprite's dark 53.
    for f in bm.faces:
        c = f.calc_center_median()
        if f.material_index == STEEL and 9.25 < c.y < 12.05 and abs(c.x) < 2.15 and f.normal.z > 0.5:
            f.material_index = DECK
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 7 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
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


def build(sprite, coll):
    mats = materials(sprite)
    p = Part(NAME, smooth_angle=38)
    beads = Part(f"{NAME}-lamps", smooth_angle=60)
    build_fuselage(p)
    build_canopy(p)
    build_spine(p)
    build_lamps(p, beads)
    build_engine(p)
    build_booms(p)
    build_wings(p)
    build_pods(p)
    fl = Part(f"{NAME}-flame", smooth_angle=60)
    build_flame(fl)
    body = finish(p, mats, coll)
    flame = finish(fl, mats, coll)
    lamps = common.frame_part(finish(beads, mats, coll), [264, 283, 302])
    return body, [flame, lamps], mats


# --- bake (copied from charge-cannon_A / enemies/newshm-117.py: AO/roughness only) ------------

def bake_maps(obj, out_dir, tag, size=1024, samples=48):
    scene = bpy.context.scene
    set_engine(scene, "CYCLES")
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
    bpy.ops.uv.smart_project(angle_limit=math.radians(24), island_margin=0.006, scale_to_bounds=False)
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
            continue  # glowing parts stay flat palette colour
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

def set_frame(objs, frame):
    """Show the model as on sprite frame `frame` (for renders): frame parts and frame colours."""
    for o in objs:
        if "tyrian_frames" in o:
            o.hide_render = frame not in list(o["tyrian_frames"])
    mats = {m for o in objs if o.type == "MESH" for m in o.data.materials if m}
    for m in mats:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        mix = next((n for n in m.node_tree.nodes if n.type == "MIX" and n.blend_type == "MULTIPLY"), None)
        if "tyrian_base_rgb" not in m:
            base = tuple(mix.inputs[7].default_value)[:3] if mix else tuple(bsdf.inputs["Base Color"].default_value)[:3]
            m["tyrian_base_rgb"] = list(base)
        rgb = tuple(m.get("tyrian_frame_rgb", {}).get(str(frame), m["tyrian_base_rgb"]))
        if mix:
            mix.inputs[7].default_value = (*rgb, 1.0)
        else:
            bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        if bsdf.inputs["Emission Strength"].default_value > 0:
            bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
        m.diffuse_color = (*rgb, 1.0)


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
        key = "WORKBENCH" if "WORKBENCH" in want else ("EEVEE" if "EEVEE" in want else want)
        scene.render.engine = next(e for e in names if key in e)


def render_tops(scene, objs, out):
    """Flat top views on the sprite grid (16 image px per sprite px), one per frame."""
    set_engine(scene, "BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 12 * 16, 14 * 16
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    cam = camera(scene, "ss_top", (0, 0, 5), (0, 0, 0), ortho=14 / 12)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    for f in ALL:
        set_frame(objs, f)
        scene.render.filepath = str(out / f"top_{f}.png")
        bpy.ops.render.render(write_still=True)


def render_views(scene, objs, out, frames=(245, 283)):
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
    sun = bpy.data.objects.new("ss_sun", bpy.data.lights.new("ss_sun", "SUN"))
    sun.data.energy = 4.5
    sun.rotation_euler = (Vector((0.45, -0.5, -1.0))).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("ss_fill", bpy.data.lights.new("ss_fill", "SUN"))
    fill.data.energy = 1.3
    fill.rotation_euler = (Vector((-0.6, 0.6, -0.3))).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill)
    scene.render.resolution_x = scene.render.resolution_y = 420
    D = 3.0
    ext = 1.35
    t15, t32 = math.radians(15), math.radians(32)
    views = {
        "top": camera(scene, "v_top", (0, 0, D), (0, 0, 0), ortho=ext),
        "side": camera(scene, "v_side", (D, 0, 0), (0, 0, 0), ortho=ext, up="Z"),
        "front": camera(scene, "v_front", (0, D, 0), (0, 0, 0), ortho=ext, up="Z"),
        "rear": camera(scene, "v_rear", (0, -D, 0), (0, 0, 0), ortho=ext, up="Z"),
        "q34": camera(scene, "v_q34", (2.2, 2.0, 2.1), (0, 0, 0), lens=62, up="Z"),
        "q34r": camera(scene, "v_q34r", (-2.2, -2.2, 1.9), (0, 0, 0), lens=62, up="Z"),
        "game15": camera(scene, "v_game15", (0, -4.5 * math.sin(t15), 4.5 * math.cos(t15)), (0, 0, 0), lens=60),
        "game32": camera(scene, "v_game32", (0, -4.5 * math.sin(t32), 4.5 * math.cos(t32)), (0, 0, 0), lens=60),
        "under": camera(scene, "v_under", (0, 0, -D), (0, 0, 0), ortho=ext),
    }
    views["top"].rotation_euler = (0, 0, 0)
    views["side"].rotation_euler = (math.pi / 2, 0, math.pi / 2)
    views["front"].rotation_euler = (math.pi / 2, 0, math.pi)
    views["rear"].rotation_euler = (math.pi / 2, 0, 0)
    views["under"].rotation_euler = (math.pi, 0, 0)
    for f in frames:
        set_frame(objs, f)
        for k, cam in views.items():
            if f != frames[0] and k not in ("top", "game15", "q34", "rear"):
                continue
            scene.camera = cam
            scene.render.filepath = str(out / f"view_{k}_{f}.png")
            bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    bake = "--nobake" not in argv
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    coll = common.reset_collection("side_ship")
    sprite = common.load_sprite(WT, REF)
    body, extras, mats = build(sprite, coll)
    T.cull_hidden(body)
    shell = common.outline_shell(body, coll, voxel=0.008, faces=500, smooth=6, inside=0.004)
    shell.name = f"{NAME}_outline"
    if bake:
        for o in [shell] + extras:
            o.hide_render = True
        bake_maps(body, tempfile.mkdtemp(prefix="ss_bake_"), "side_ship")
    objs = [body, shell] + extras
    tris = {}
    for o in objs:
        o.data.calc_loop_triangles()
        tris[o.name] = len(o.data.loop_triangles)
    print("triangles", tris, sum(tris.values()))
    for o in objs:
        o.hide_render = False
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"], image_format="WEBP" if bake else "AUTO")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        shell.hide_render = True
        render_tops(scene, [body] + extras, views)
        render_views(scene, [body] + extras, views)


if __name__ == "__main__":
    main()
