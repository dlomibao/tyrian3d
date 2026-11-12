"""Zica SuperCharger (sidekick option 12, style 0 mounted side pod; tyrian.shp#8 frames 3-7, 22-26,
41-45, 60-64), blueprint-first, engineering cross-sections (DECISIONS D50-D53, D65, D74, D17).

What it is: an armoured charge pod clamped to the ship's side. A glowing reactor orb sits in an open
cradle in the middle of a dark-blue armoured hull; it charges up, discharges forward through a
transverse emitter head, and bleeds surplus charge off five rear prongs. Charge levels 2-4 throw
orange crackle round the hull.

What the sprite shows (reference/models/sidekick-zica-supercharger, 12x14, palette 5, symmetric about
column edge 6.5; inner mask = what the top view covers, D74):
- row 0, cols 4-8: the emitter head, a transverse bar (59, lit top 61 = sheen);
- row 1, cols 5-7: a round neck (54);
- rows 2-4, cols 3-9: the armour cowl (54), row 2 bright = a lit glacis slope, row 3 dark with two
  lit studs (cols 4 and 8);
- rows 4-9, cols 4-8: the reactor orb, red glass (113-117 rim, 120-127 core; the near-white upper
  left is sheen), in a dark cradle (52, ink 144 where the wall is in shadow);
- rows 5-6, 8, 10 at cols 2 / 10: heat-sink fins (55), the dark rows 7, 9 between them gaps;
- row 10, cols 3-9: a lit bulkhead behind the orb (57);
- rows 11-12, cols 1-11: the rear capacitor block (53): a lit centre spine (col 6) between two
  dark channels (cols 5, 7), plates (cols 4, 8), red charge lamps (cols 3, 9: 115-121 by frame),
  cheeks (cols 1-2, 10-11);
- row 13, cols 2/4/6/8/10: five discharge prongs (54).
- Per frame (D17 frame palette): the orb steps 117/118/119/116, its core 121/122/122/119, the lamps
  117 -> 119/121 with charge. Charge 2-4 add crackle pixels (243-253) round the outline: frame-shown
  emissive arcs (frame_part).

Cross-sections first (sprite px; x = column edge - 6, so the axis is x = 0.5; y = row edge; z up):
- hull: a chamfered box, 7 px wide (hw 3.5), its deck a pchip station curve (glacis 1.55 -> 2.75 ->
  cradle deck 2.2), big lower chamfers for a pod belly; modelled panel grooves at rows 3.05 / 4.45;
- head: a stadium section (2.5 x 1.0 half sizes, end radius 0.85) with chamfered faces, a raised dark
  bezel and a recessed glowing discharge slot on its front face;
- neck: a revolve with a machined clamp flange;
- orb: an oblate glass spheroid sunk in the cradle, its top cap the hot core, seated in a chamfered
  clamp ring with four bolts;
- fins: tapered chamfered plates (convex hulls), top sloping down outward;
- rear block: a gabled core under separate armour plates whose gaps are the sprite's dark channels,
  lamps in raised bezels, a chamfered rear face carrying five collared prongs with insulator rings.
Underside: the hull's chamfered belly and a mount shoe, closed, nothing more.

Core: one glow inside the glass: the orb's latitude bands ring a hot axis tilted up-left (the
sprite's white-hot pixel), one palette step per band 126 -> 119 so they blend into a gradient, then
the per-step red rim; the region median stays 121 (rows 6-8). Crackle (round 2: light, not
tubes): flat 4-sided emissive bolts, straight strokes chained pixel centre to pixel centre with sharp
kinks, matte so lighting barely shades them; the hot 250/253 pixels and lone pixels are small spark
stars; dim 243-245 pixels glow harder in their own dark red. One part per set of crackle positions (frames 6/7 share one; materials animate per frame).

Run: tools/build-models.sh -j 2 assets/blender/sidekicks/zica-supercharger.py
(--out DIR after -- also writes review renders.) Exports public/models/sidekicks/zica-supercharger.glb
and src/render/spriteModels/zica-supercharger.json.
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.append("/Users/dlomibao/projects/tyrian-worktrees/sidekicks-2/tools")
import sprite_mask as SM  # noqa: E402  (pure stdlib: the D74 masks, for the crackle's bridges)

WT = Path("/Users/dlomibao/projects/tyrian-worktrees/sidekicks-2")
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, hull, pchip, frange, loft_rings  # noqa: E402

NAME = "zica-supercharger"
REF = f"sidekick-{NAME}"
HERE = Path(__file__).resolve().parent
PX = 1 / 12
AX = 0.5  # symmetry axis, x (column edge 6.5)

ALL = [3, 4, 5, 6, 7, 22, 23, 24, 25, 26, 41, 42, 43, 44, 45, 60, 61, 62, 63, 64]
STEPS = {3: 0, 22: 1, 41: 2, 60: 3}
ORB = [117, 118, 119, 116]       # per animation step (median of the orb rim + body)
CORE = [121, 122, 122, 119]      # per step (median of rows 6-8, cols 5-7)
LAMP_TOP = {3: 117, 4: 117, 5: 117, 6: 117, 7: 117, 22: 117, 23: 119, 24: 119, 25: 119, 26: 119,
            41: 117, 42: 121, 43: 121, 44: 121, 45: 121, 60: 117, 61: 119, 62: 119, 63: 119, 64: 119}
LAMP = {f: i - 1 for f, i in LAMP_TOP.items()}  # the lamp's lit top row and shaded bottom row: median
# The orb's hot core as fine one-step bands (polar angle from the crown, degrees), so it reads as a
# glow seen through red glass rather than painted rings. Each band steps with the animation: the
# hot centre dims at step 3, the core follows CORE, the rim dims with ORB at step 3 (sprite rows 5-9).
# Round 2: the hot bands widened so the orange-yellow fills most of the dome the 32-degree game camera
# sees (it read as a red button with a small yellow spot), the 117 rim pushed down the sides.
# The core's region medians (sprite rows 6-8, cols 5-7: 121; the orb's rows 5-9, cols 4-8: 117) pin
# the 121 band inside the 3x3 core and the hot bands inside its edge cells, so the gain is in the
# rim steps and in the glow itself (fully emissive, matte, a lower dome).
ORB_BANDS = [(5, 126, "hot"), (9, 125, "hot"), (13, 124, "hot"), (18, 123, "hot"), (23, 122, "core"),
             (40, 121, "core"), (43, 120, "rim"), (47, 119, "rim")]
BAND_DELTA = {"hot": [0, 0, 0, -2], "core": [c - 121 for c in CORE], "rim": [min(0, o - 117) for o in ORB]}

# Material slots.
(HEAD, BEZEL, SLOT, NECK, FLANGE, COWL, GROOVE, CRADLE, BULK, ORBM, COREM, RING, BOLT, FIN, RCORE,
 CHEEK, RPLATE, SPINE, LAMPM, PRONG, INSUL, SHOE, HOT, WHITE) = range(24)
BAND0 = 24  # orb band materials follow (ORB_BANDS), then the crackle's (made as needed)


def step_of(f):
    return max(k for k in STEPS if k <= f)


def materials(sprite):
    def steel(i, tag, rough=0.42, metal=0.45, frames=None):
        return common.palette_material(sprite, i, f"zsc_{tag}", metallic=metal, roughness=rough, frames=frames)

    def glow(i, tag, e, rough=0.3, frames=None):
        return common.palette_material(sprite, i, f"zsc_{tag}", metallic=0.0, roughness=rough,
                                       emission_strength=e, frames=frames)
    orb_frames = {f: ORB[STEPS[step_of(f)]] for f in ALL if ORB[STEPS[step_of(f)]] != 117}
    core_frames = {f: CORE[STEPS[step_of(f)]] for f in ALL if CORE[STEPS[step_of(f)]] != 121}
    lamp_frames = {f: i for f, i in LAMP.items() if i != 116}
    mats = [
        steel(59, "head", rough=0.38),
        steel(51, "bezel", rough=0.6, metal=0.3),
        glow(120, "slot", 1.0),
        steel(54, "neck"),
        steel(54, "flange", rough=0.34),
        steel(54, "cowl"),
        steel(51, "groove", rough=0.65, metal=0.25),
        steel(52, "cradle"),
        steel(57, "bulk", rough=0.38),
        glow(117, "orb", 1.0, rough=0.7, frames=orb_frames),
        glow(121, "core", 1.1, rough=0.7, frames=core_frames),
        steel(52, "ring", rough=0.36),
        steel(58, "bolt", rough=0.32),
        steel(55, "fin", rough=0.4),
        steel(51, "rcore", rough=0.6, metal=0.3),
        steel(53, "cheek"),
        steel(55, "rplate"),
        steel(57, "spine", rough=0.36),
        glow(116, "lamp", 1.0, rough=0.15, frames=lamp_frames),
        steel(54, "prong", rough=0.36),
        steel(53, "insul", rough=0.55, metal=0.2),
        steel(51, "shoe", rough=0.6, metal=0.3),
        glow(124, "hot", 1.15, rough=0.2),
        glow(126, "white", 1.0, rough=0.2),
    ]
    for k, (_, i, grp) in enumerate(ORB_BANDS):
        fr = {f: min(127, max(113, i + BAND_DELTA[grp][STEPS[step_of(f)]])) for f in ALL}
        fr = {f: v for f, v in fr.items() if v != i}
        # fully glowing (no lit share) and matte: a light inside the glass, not glossy plastic
        mats.append(glow(i, f"band{k}", 1.0 if i < 124 else 1.1, rough=0.7, frames=fr or None))
    return mats


# --- sections ------------------------------------------------------------------------------------

def chamfer_box(hw, zb, zt, cb, ct, crown=0.0, ntop=4, cx=AX, seam=None):
    """A chamfered box section across x round cx: bottom chamfer cb, top chamfer ct, a crowned deck,
    and (seam = z) a modelled V seam along both walls, where the belly armour meets the side plates."""
    pts = [(cx + hw - cb, zb), (cx + hw, zb + cb)]
    if seam is not None:
        pts += [(cx + hw, seam - 0.07), (cx + hw - 0.08, seam), (cx + hw, seam + 0.07)]
    pts += [(cx + hw, zt - ct)]
    for i in range(ntop + 1):
        t = 1 - 2 * i / ntop
        x = t * (hw - ct)
        pts.append((cx + x, zt + crown * (1 - t * t)))
    pts += [(cx - hw, zt - ct)]
    if seam is not None:
        pts += [(cx - hw, seam + 0.07), (cx - hw + 0.08, seam), (cx - hw, seam - 0.07)]
    pts += [(cx - hw, zb + cb), (cx - hw + cb, zb)]
    return pts


DECK = pchip([2.0, 2.35, 2.9, 3.8, 4.5, 5.0, 9.9],
             [1.55, 2.35, 2.7, 2.75, 2.35, 2.2, 2.2])
HULL_HW = 3.5
HULL_ZB = 0.25


def hull_sec(y, grow):
    zt = DECK(min(y, 9.9)) + grow
    return chamfer_box(HULL_HW + grow, HULL_ZB - grow, zt, 0.75, 0.32, crown=0.1, seam=1.2), (AX, 1.2)


def groove(y, w=0.05, d=0.09):
    return [(y - w, 0.0), (y - w * 0.4, -d), (y + w * 0.4, -d), (y + w, 0.0)]


def stadium(hw, hh, r, cz, cx=AX, n=4):
    pts = []
    for cxx, czz, a0 in ((hw - r, hh - r, 0), (-(hw - r), hh - r, 90), (-(hw - r), -(hh - r), 180),
                         (hw - r, -(hh - r), 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + cxx + r * math.cos(a), cz + czz + r * math.sin(a)))
    return pts


HEAD_Z = 1.45  # head and neck axis height


def head_sec(y, grow):
    return stadium(2.5 + grow, 1.0 + grow, 0.85 + grow, HEAD_Z), (AX, HEAD_Z)


REAR_HW = 5.5
REAR_Y0, REAR_Y1 = 10.95, 13.0
EAVE, RIDGE = 1.75, 2.25   # the core's gable (the plates stand on it)


def rear_top(x):
    a = abs(x - AX)
    return RIDGE - (RIDGE - EAVE) * min(1.0, a / REAR_HW)


def rear_sec(y, grow):
    hw = REAR_HW + grow
    pts = [(AX + hw - 0.55, HULL_ZB - grow), (AX + hw, HULL_ZB + 0.55 - grow), (AX + hw, EAVE + grow - 0.15)]
    for t in (0.8, 0.45, 0.0, -0.45, -0.8):
        x = AX + t * (hw - 0.2)
        pts.append((x, rear_top(x) + grow))
    pts += [(AX - hw, EAVE + grow - 0.15), (AX - hw, HULL_ZB + 0.55 - grow), (AX - hw + 0.55, HULL_ZB - grow)]
    return pts, (AX, 1.1)


# --- generic pieces ------------------------------------------------------------------------------

def revolve_y(part, prof, cx, cz, n=16, phase=0.0):
    """A solid of revolution round a line along y at (cx, cz); prof [(y, r, mat)] axis to axis."""
    def ring(y, r):
        if r <= 1e-6:
            return [part.v((cx, y, cz))]
        return [part.v((cx + r * math.sin(phase + 2 * math.pi * i / n), y, cz + r * math.cos(phase + 2 * math.pi * i / n)))
                for i in range(n)]
    rings = [ring(y, r) for y, r, _ in prof]
    for k in range(len(prof) - 1):
        (y0, r0, m), (y1, r1, _) = prof[k], prof[k + 1]
        ny, nr = -(r1 - r0), (y1 - y0)
        a, b = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            ang = phase + 2 * math.pi * (i + 0.5) / n
            out = (nr * math.sin(ang), ny, nr * math.cos(ang))
            if len(a) == 1:
                part.f((a[0], b[i], b[j]), m, out=out)
            elif len(b) == 1:
                part.f((a[i], a[j], b[0]), m, out=out)
            else:
                part.f((a[i], a[j], b[j], b[i]), m, out=out)


def revolve_z(part, prof, cx, cy, n=24):
    """A solid of revolution round a vertical line at (cx, cy); prof [(r, z, mat)] along the surface."""
    def ring(r, z):
        if r <= 1e-6:
            return [part.v((cx, cy, z))]
        return [part.v((cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z))
                for i in range(n)]
    rings = [ring(r, z) for r, z, _ in prof]
    for k in range(len(prof) - 1):
        (r0, z0, m), (r1, z1, _) = prof[k], prof[k + 1]
        nr, nz = -(z1 - z0), (r1 - r0)  # the profile runs clockwise in (r, z): outward is to its left
        a, b = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            ang = 2 * math.pi * (i + 0.5) / n
            out = (nr * math.cos(ang), nr * math.sin(ang), nz)
            if len(a) == 1:
                part.f((a[0], b[i], b[j]), m, out=out)
            elif len(b) == 1:
                part.f((a[i], a[j], b[0]), m, out=out)
            else:
                part.f((a[i], a[j], b[j], b[i]), m, out=out)


def hexbolt(part, cx, cy, z, rad=0.2, h=0.14, mat=BOLT):
    pts = []
    for k in range(6):
        t = 2 * math.pi * k / 6
        for dz, rr in ((-0.08, rad), (h, rad * 0.8)):
            pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t), z + dz))
    hull(part, pts, mat)


def gable_plate(part, x0, x1, y0, y1, lift, mat, ch=0.1, skirt=0.3):
    """An armour plate on the rear block's gable from x0 to x1, y0 to y1, standing `lift` proud."""
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            zt = rear_top(x) + lift
            zc = rear_top(x + sx * ch) + lift
            pts += [(x + sx * ch, y + sy * ch, zc), (x, y + sy * ch, zt - ch), (x + sx * ch, y, zt - ch),
                    (x, y, rear_top(x) - skirt)]
    hull(part, pts, mat, merge_angle=2.0)


# --- the body ------------------------------------------------------------------------------------

def build_body(P):
    # Hull: cowl (rows 2-4.5), cradle (4.5-9.95), with modelled panel grooves.
    ys = [2.0, 2.12, 2.35, 2.6, 2.9]
    rings = [(hull_sec, 2.0, -0.18), (hull_sec, 2.14, 0.0)]
    mats = [COWL, COWL]
    for y in [2.35, 2.6, 2.85]:
        rings.append((hull_sec, y, 0.0)); mats.append(COWL)
    for (y, g) in groove(3.05):
        rings.append((hull_sec, y, g)); mats.append(GROOVE if g < 0 or abs(y - 3.0) < 1e-3 else COWL)
    for y in [3.4, 3.8, 4.1]:
        rings.append((hull_sec, y, 0.0)); mats.append(COWL)
    for (y, g) in groove(4.45):
        rings.append((hull_sec, y, g)); mats.append(GROOVE)
    for y in [4.75, 5.0, 10.3]:  # the deck is level from 5.0: no rings needed between
        rings.append((hull_sec, y, 0.0)); mats.append(CRADLE)
    # groove ring materials: segment i colours ring i -> i+1; fix the groove entries
    mats = []
    prev_y = None
    for k in range(len(rings) - 1):
        y0, g0 = rings[k][1], rings[k][2]
        y1, g1 = rings[k + 1][1], rings[k + 1][2]
        if g0 < -0.01 and g1 < -0.01 and abs(g0 - g1) < 1e-6 and y0 > 2.1:
            m = GROOVE
        elif y0 >= 4.5:
            m = CRADLE
        else:
            m = COWL
        mats.append(m)
    loft_rings(P, rings, mats + [mats[-1]])

    # Cowl studs (row 3, cols 4 and 8: the lit pixels on the dark row).
    for c in (4.5, 8.5):
        hexbolt(P, c - 6, 3.55, DECK(3.55) + 0.02, rad=0.24, h=0.16)

    # Bulkhead behind the orb (row 10, lit 57): a chamfered block standing over the deck.
    hull(P, cbox(-3.0, 4.0, 9.98, 11.05, HULL_ZB + 0.3, 2.6, 0.18), BULK)
    # Its lip toward the orb: a raised chamfered sill (machined detail).
    hull(P, cbox(-1.6, 2.6, 9.85, 10.15, 2.2, 2.72, 0.07), BULK)

    # Head: a transverse emitter bar, chamfered faces; the neck behind it.
    loft_rings(P, [(head_sec, 0.0, -0.15), (head_sec, 0.15, 0.0), (head_sec, 0.88, 0.0), (head_sec, 1.0, -0.1)],
               [HEAD, HEAD, HEAD, HEAD])
    # Front: a raised dark bezel round a recessed glowing discharge slot.
    bez_o = stadium(1.95, 0.52, 0.48, HEAD_Z)
    bez_i = stadium(1.62, 0.3, 0.28, HEAD_Z)
    vo0 = [P.v((x, 0.02, z)) for x, z in bez_o]
    vo1 = [P.v((x, -0.07, z)) for x, z in bez_o]
    vi1 = [P.v((x, -0.07, z)) for x, z in bez_i]
    vi0 = [P.v((x, -0.0, z)) for x, z in bez_i]
    n = len(bez_o)
    for i in range(n):
        j = (i + 1) % n
        ox, oz = bez_o[i][0] - AX, bez_o[i][1] - HEAD_Z
        P.f((vo0[i], vo0[j], vo1[j], vo1[i]), BEZEL, out=(ox, 0, oz))
        P.f((vo1[i], vo1[j], vi1[j], vi1[i]), BEZEL, out=(0, -1, 0))
        P.f((vi1[i], vi1[j], vi0[j], vi0[i]), BEZEL, out=(-ox, 0, -oz))
    P.f(list(reversed(vi0)), SLOT, out=(0, -1, 0))
    # Top seam of the bar (a panel line down its middle): a shallow raised strap either side.
    for x0 in (-0.15 + AX - 1.15, AX + 1.0):
        hull(P, cbox(x0, x0 + 0.15, 0.12, 0.88, HEAD_Z + 0.9, HEAD_Z + 1.04, 0.04), HEAD)
    # Neck with its clamp flange.
    revolve_y(P, [(0.85, 0.0, NECK), (0.85, 1.28, NECK), (1.3, 1.28, FLANGE), (1.3, 1.44, FLANGE),
                  (1.36, 1.5, FLANGE), (1.62, 1.5, FLANGE), (1.68, 1.44, NECK), (1.68, 1.28, NECK),
                  (2.25, 1.28, NECK), (2.25, 0.0, NECK)], AX, HEAD_Z, n=10, phase=math.pi / 10)

    # Reactor orb: an oblate glass spheroid sunk in the cradle; its top cap the hot core.
    # (round 2: a lower dome, so its sides take less of the game camera's view)
    OV, OZ, RX, RY, RZ = 7.35, 1.9, 2.45, 2.5, 1.32
    nu = 16
    # latitude rings at the band edges (fine near the crown), then coarser round to the belly
    ths = [b[0] for b in ORB_BANDS] + [68, 84, 105, 140]
    # The bands ring a hot axis tilted toward the upper left (the sprite's white-hot pixel sits at
    # row 6, col 5, up and left of the orb's centre): a glow off-centre inside the glass, not a
    # target painted on its crown.
    ax_ = Vector((-0.17, -0.08, 1.0)).normalized()
    e1_ = Vector((0, 1, 0)).cross(ax_).normalized()
    e2_ = ax_.cross(e1_)

    def orb_pt(th, ph):
        u = math.cos(th) * ax_ + math.sin(th) * (math.cos(ph) * e1_ + math.sin(ph) * e2_)
        return (AX + RX * u.x, OV + RY * u.y, OZ + RZ * u.z)
    ring_pts = []
    for d in ths:
        th = math.radians(d)
        ring_pts.append([P.v(orb_pt(th, 2 * math.pi * k / nu)) for k in range(nu)])
    top = P.v(orb_pt(0.0, 0.0))
    bot = P.v(orb_pt(math.pi, 0.0))
    c0 = (AX, OV, OZ)
    for k in range(nu):
        k2 = (k + 1) % nu
        P.f((top, ring_pts[0][k], ring_pts[0][k2]), BAND0, away=c0)
        P.f((bot, ring_pts[-1][k2], ring_pts[-1][k]), ORBM, away=c0)
    for j in range(len(ring_pts) - 1):
        m = BAND0 + j + 1 if j + 1 < len(ORB_BANDS) else ORBM
        for k in range(nu):
            k2 = (k + 1) % nu
            P.f((ring_pts[j][k], ring_pts[j][k2], ring_pts[j + 1][k2], ring_pts[j + 1][k]), m, away=c0)
    # Clamp ring seating the orb (a chamfered revolve), four bolts on the diagonals.
    revolve_z(P, [(2.3, 1.95, RING), (2.3, 2.48, RING), (2.42, 2.6, RING), (2.66, 2.6, RING),
                  (2.8, 2.46, RING), (2.8, 1.95, RING), (2.3, 1.95, RING)], AX, OV, n=16)
    for a in (45, 135, 225, 315):
        q = math.radians(a)
        hexbolt(P, AX + 2.55 * math.cos(q), OV + 2.55 * math.sin(q), 2.6, rad=0.13, h=0.1)

    # Heat-sink fins (rows 5-6, 8, 10; out to column edges 2 and 11).
    # The forward fin (2 px) is a pair of plates with a cooling slot between them.
    for (v0, v1) in ((5.04, 5.94), (6.06, 6.96), (8.06, 8.94), (10.06, 10.94)):
        for side in (-1, 1):
            xi = AX + side * (HULL_HW - 0.4)
            xo = AX + side * (HULL_HW + 0.98)
            pts = []
            ch = 0.12
            for x, zt in ((xi, 2.3), (xo - side * 0.12, 1.72), (xo, 1.55)):
                for y, sy in ((v0, 1), (v1, -1)):
                    pts += [(x, y + sy * ch, zt), (x, y, zt - ch), (x, y, 0.55 + ch), (x, y + sy * ch, 0.55)]
            hull(P, pts, FIN, merge_angle=2.0)

    # Rear capacitor block: a gabled core with chamfered ends, plates over it.
    loft_rings(P, [(rear_sec, REAR_Y0, 0.0), (rear_sec, REAR_Y1 - 0.25, 0.0), (rear_sec, REAR_Y1, -0.2)],
               [RCORE, RCORE, RCORE])
    gy0, gy1 = REAR_Y0 + 0.08, REAR_Y1 - 0.1
    # cheeks (cols 1-2 / 10-11), lamp bezels (3 / 9), plates (4 / 8), spine (6); channels at 5 / 7.
    for side in (-1, 1):
        def X(c):
            return c - 6 if side < 0 else (13 - c) - 6
        a, b = sorted((X(1.0), X(2.96)))
        gable_plate(P, a, b, gy0, gy1, 0.3, CHEEK)
        a, b = sorted((X(3.0), X(3.98)))
        gable_plate(P, a, b, gy0, gy1, 0.36, BEZEL, ch=0.08)
        a, b = sorted((X(4.02), X(4.96)))
        gable_plate(P, a, b, gy0, gy1, 0.3, RPLATE, ch=0.08)
        # the charge lamp: a glowing pill sunk in its bezel
        cx = (X(3.0) + X(3.98)) / 2
        pill = []
        w = 0.3
        for i in range(5):
            t = math.pi + math.pi * i / 4
            pill.append((cx + w * math.cos(t), 11.55 + w * math.sin(t)))
        for i in range(5):
            t = math.pi * i / 4
            pill.append((cx + w * math.cos(t), 12.5 + w * math.sin(t)))
        zt = rear_top(cx) + 0.36
        pts = [(x, y, zt + 0.06) for x, y in pill] + [(x, y, zt - 0.2) for x, y in pill]
        hull(P, pts, LAMPM)
    gable_plate(P, AX - 0.48, AX + 0.48, gy0, gy1, 0.42, SPINE, ch=0.1)
    # Rear-face seam band: a raised lip along the lower rear edge.
    hull(P, cbox(-5.0 + 0.0, 6.0, 12.86, 13.05, HULL_ZB + 0.45, 1.75, 0.06), CHEEK)

    # Five discharge prongs (row 13): collar, rod, an insulator ring, tapered tip.
    for c in (2.5, 4.5, 6.5, 8.5, 10.5):
        revolve_y(P, [(12.75, 0.0, PRONG), (12.75, 0.46, PRONG), (13.08, 0.4, PRONG),
                      (13.22, 0.44, INSUL), (13.4, 0.44, INSUL), (13.42, 0.32, PRONG),
                      (13.97, 0.0, PRONG)], c - 6, 1.1, n=6,
                     phase=math.pi / 6)

    # Underside: the hardpoint shoe the pod clamps on with (plain, closed).
    hull(P, cbox(-1.0, 2.0, 4.2, 9.8, -0.15, HULL_ZB + 0.2, 0.15), SHOE)


# --- crackle ------------------------------------------------------------------------------------

# Arc half width by brightness (sprite px). All stay >= 0.29 so each pixel's cell is at least half
# covered in the top view (the grid IoU rule); the height is a fraction of it (a flat streak of
# light, not a round cable).
def arc_radius(pal):
    return 0.33 if pal >= 250 else (0.32 if pal >= 246 else 0.31)


ARC_FLAT = 0.45  # section half height / half width


def bolt_sweep(part, pts, rads, mats, sides=4, flat=ARC_FLAT):
    """A bolt through pts: straight segments meeting in sharp mitred kinks, a flat 4-sided diamond
    section (half width rads[i], half height rads[i] * flat), segment i -> i + 1 in mats[i]; both
    ends close in a sharp spike. Rings are parallel-transported, so the diamond doesn't twist."""
    P = [Vector(p) for p in pts]
    n = len(P)
    tans = []
    for i in range(n):
        if i == 0:
            t = P[1] - P[0]
        elif i == n - 1:
            t = P[-1] - P[-2]
        else:
            t = (P[i] - P[i - 1]).normalized() + (P[i + 1] - P[i]).normalized()
            if t.length < 1e-4:
                t = P[i + 1] - P[i]
        tans.append(t.normalized())
    e1 = tans[0].cross(Vector((0, 0, 1)))
    if e1.length < 1e-3:
        e1 = tans[0].cross(Vector((1, 0, 0)))
    e1.normalize()
    rings = []
    for i in range(n):
        if i:
            e1 = e1 - tans[i] * e1.dot(tans[i])
            if e1.length < 1e-4:
                e1 = tans[i].cross(Vector((0, 0, 1)))
            e1.normalize()
        e2 = tans[i].cross(e1)
        w = rads[i]
        if 0 < i < n - 1:
            w /= max(0.62, (P[i] - P[i - 1]).normalized().dot(tans[i]))  # mitre: no pinch at kinks
        rings.append([part.v(tuple(P[i] + w * (math.cos(2 * math.pi * k / sides) * e1 +
                                               flat * math.sin(2 * math.pi * k / sides) * e2)))
                      for k in range(sides)])
    for i in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            part.f((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]), mats[i],
                   away=tuple((P[i] + P[i + 1]) / 2))
    for i, d in ((0, -1), (n - 1, 1)):
        tip = part.v(tuple(P[i] + tans[i] * d * rads[i] * 1.3))
        m = mats[0] if i == 0 else mats[-1]
        for k in range(sides):
            part.f((rings[i][k], rings[i][(k + 1) % sides], tip), m, away=tuple(P[i]))


def spark(part, c, outer, inner, m, rot, npts=4, half_h=0.17):
    """A spark star: a flat bipyramid with npts sharp points (the hot 250/253 pixels), so the bright
    pixels read as a flash where the arc forks or jumps, not a round peg."""
    c = Vector(c)
    top = part.v(tuple(c + Vector((0, 0, half_h))))
    bot = part.v(tuple(c - Vector((0, 0, half_h))))
    ring = []
    for k in range(2 * npts):
        a = rot + math.pi * k / npts
        r = outer if k % 2 == 0 else inner
        ring.append(part.v((c.x + r * math.cos(a), c.y + r * math.sin(a), c.z)))
    nn = len(ring)
    for k in range(nn):
        k2 = (k + 1) % nn
        part.f((top, ring[k], ring[k2]), m, away=tuple(c))
        part.f((bot, ring[k2], ring[k]), m, away=tuple(c))


def crackle(part, pixels, zat, mat_of):
    """Charge arcs through the frame's crackle pixel centres (round 2: light, not tubes): straight
    flat bolts chained pixel to pixel with sharp kinks between, standing just off the hull where
    they cross it and hugging the flank at mid height off it; the hot 250/253 pixels and lone pixels
    get a small spark star. pixels: {(r, c): key}, mat_of(key) -> material slot; key[0] is the
    pixel's palette index on each frame of the part (the brightest sets the bolt's width)."""
    nodes = {}
    for (r, c), key in pixels.items():
        x, y = c + 0.5 - 6, r + 0.5
        # a little in-plane jitter (<= 0.1 px, keeps each cell covered) makes the chain jag
        jx = (((r * 5 + c * 11) % 5) - 2) * 0.05
        jy = (((r * 13 + c * 3) % 5) - 2) * 0.05
        z = zat(x, y)
        rad = arc_radius(max(key[0]))
        jz = (((r * 7 + c * 3) % 3) - 1) * 0.25
        z = 1.35 + jz if z is None else z + rad * ARC_FLAT + 0.1 + (jz + 0.25) * 0.4
        nodes[(r, c)] = (Vector((x + jx, y + jy, z)), rad, mat_of(key), max(key[0]))
    adj = {k: set() for k in nodes}
    for (r, c) in nodes:
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
            q = (r + dr, c + dc)
            if q not in nodes:
                continue
            if dr and dc and ((r + dr, c) in nodes or (r, c + dc) in nodes):
                continue
            adj[(r, c)].add(q)
            adj[q].add((r, c))
    used = set()

    def ekey(a, b):
        return (a, b) if a < b else (b, a)

    def walk(a, b):
        path = [a, b]
        used.add(ekey(a, b))
        while len(adj[path[-1]]) == 2:
            nxt = [q for q in adj[path[-1]] if ekey(path[-1], q) not in used]
            if not nxt:
                break
            used.add(ekey(path[-1], nxt[0]))
            path.append(nxt[0])
        return path
    chains = []
    for a in sorted(nodes):
        if len(adj[a]) != 2:
            for b in sorted(adj[a]):
                if ekey(a, b) not in used:
                    chains.append(walk(a, b))
    for a in sorted(nodes):
        for b in sorted(adj[a]):
            if ekey(a, b) not in used:
                chains.append(walk(a, b))
    for ch in chains:
        pts, rads, mats = [], [], []
        for i, k in enumerate(ch):
            p, rad, m, _ = nodes[k]
            if i:
                # most pixel-to-pixel steps kink half way (sideways and up or down, by a hash of the
                # pixel): a zigzag of straight strokes like a discharge, not smooth wiring; colour
                # changes sit half way too
                q, rq, mq, _ = nodes[ch[i - 1]]
                r_, c_ = ch[i]
                hsh = (r_ * 7 + c_ * 13 + len(pts) * 5) % 6
                amp = (0.2, -0.16, 0.0, -0.2, 0.0, 0.17)[hsh]
                if amp or mq != m:
                    d = p - q
                    side = Vector((-d.y, d.x, 0.0))
                    side = side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))
                    # mostly up/down (the tilted camera sees the zigzag; the top view keeps its cells)
                    mid = (p + q) / 2 + side * amp * 0.55 + Vector((0, 0, 1.1 * amp))
                    pts.append(tuple(mid)); rads.append(min(rad, rq) * 0.85); mats.append(mq)
                mats.append(m)
            pts.append(tuple(p)); rads.append(rad)
        # free ends: a short spike past the pixel centre (covers its cell, reads as the arc's tip)
        for end, nb in ((0, 1), (-1, -2)):
            k = ch[end]
            if len(adj[k]) == 1:
                d = (Vector(pts[end]) - Vector(pts[nb])).normalized()
                tip = tuple(Vector(pts[end]) + d * 0.34)
                if end == 0:
                    pts.insert(0, tip); rads.insert(0, rads[0] * 0.85); mats.insert(0, mats[0])
                else:
                    pts.append(tip); rads.append(rads[-1] * 0.85); mats.append(mats[-1])
        bolt_sweep(part, pts, rads, mats[:len(pts) - 1])
    for (r, c), (p, rad, m, pal) in nodes.items():
        if pal >= 250 or not adj[(r, c)]:
            rot = math.radians((r * 37 + c * 23) % 90)
            spark(part, tuple(p), 0.6, 0.24, m, rot)


# --- finish, bake, renders -----------------------------------------------------------------------

def finish(part, mats, coll):
    """X = x / 12, Y = (7 - y) / 12, Z = z / 12 (sprite centre at the origin, D49)."""
    part.orient()
    bm = part.bm
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


def bake_maps(obj, out_dir, tag, size=1024, samples=48):
    """AO/roughness bake (as charge-cannon_A / enemies/newshm-117.py): glowing parts stay flat."""
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


def set_frame(objs, frame):
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
    cam.rotation_euler = (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    return cam


def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = [e for e in str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split()
                 if e.isupper()]
        key = "WORKBENCH" if "WORKBENCH" in want else "EEVEE"
        scene.render.engine = next(e for e in names if key in e)


def render_tops(scene, objs, out):
    """Flat top views on the sprite grid (16 image px per sprite px), every frame."""
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
    cam = camera(scene, "zsc_top", (0, 0, 5), (0, 0, 0), ortho=14 / 12)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    for f in ALL:
        set_frame(objs, f)
        scene.render.filepath = str(out / f"top_{f}.png")
        bpy.ops.render.render(write_still=True)


def game_glow(objs):
    """Preview the game's glow (D126: palette x strength replaces that share of the lit colour) in
    Eevee, which adds emission on top: base colour x (1 - strength)."""
    for m in {m for o in objs if o.type == "MESH" for m in o.data.materials if m}:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        e = bsdf.inputs["Emission Strength"].default_value
        if e > 0:
            c = bsdf.inputs["Emission Color"].default_value
            k = max(0.0, 1.0 - e)
            bsdf.inputs["Base Color"].default_value = (c[0] * k, c[1] * k, c[2] * k, 1.0)


def render_views(scene, objs, out, frames=(3, 26, 45)):
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
    sun = bpy.data.objects.new("zsc_sun", bpy.data.lights.new("zsc_sun", "SUN"))
    sun.data.energy = 4.5
    sun.rotation_euler = Vector((0.45, -0.5, -1.0)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("zsc_fill", bpy.data.lights.new("zsc_fill", "SUN"))
    fill.data.energy = 1.3
    fill.rotation_euler = Vector((-0.6, 0.6, -0.3)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill)
    scene.render.resolution_x = scene.render.resolution_y = 420
    D, ext = 3.0, 1.45
    t15, t32 = math.radians(15), math.radians(32)
    views = {
        "top": camera(scene, "v_top", (0, 0, D), (0, 0, 0), ortho=ext),
        "side": camera(scene, "v_side", (-D, 0, 0.12), (0, 0, 0.12), ortho=ext),
        "front": camera(scene, "v_front", (0, D, 0.12), (0, 0, 0.12), ortho=ext),
        "rear": camera(scene, "v_rear", (0, -D, 0.12), (0, 0, 0.12), ortho=ext),
        "q34": camera(scene, "v_q34", (-1.9, 2.0, 2.0), (0, 0, 0.1), lens=60),
        "q34r": camera(scene, "v_q34r", (2.0, -2.1, 1.9), (0, 0, 0.1), lens=60),
        "game15": camera(scene, "v_game15", (0, -4.5 * math.sin(t15), 4.5 * math.cos(t15)), (0, 0, 0), lens=55),
        "game32": camera(scene, "v_game32", (0, -4.5 * math.sin(t32), 4.5 * math.cos(t32)), (0, 0, 0), lens=55),
        "under": camera(scene, "v_under", (0, 0, -D), (0, 0, 0), ortho=ext),
    }
    views["top"].rotation_euler = (0, 0, 0)
    views["side"].rotation_euler = (math.pi / 2, 0, -math.pi / 2)
    views["front"].rotation_euler = (math.pi / 2, 0, math.pi)
    views["rear"].rotation_euler = (math.pi / 2, 0, 0)
    views["under"].rotation_euler = (math.pi, 0, 0)
    for f in frames:
        set_frame(objs, f)
        game_glow(objs)
        for k, cam in views.items():
            if f != frames[0] and k not in ("top", "game32", "q34", "q34r"):
                continue
            scene.camera = cam
            scene.render.filepath = str(out / f"view_{k}_{f}.png")
            bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_dir = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    bake = "--nobake" not in argv
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    coll = common.reset_collection("zica_supercharger")
    sprite = common.load_sprite(WT, REF)
    global SM_COLORS, SM_FRAMES
    SM_COLORS = {int(k): tuple(v) for k, v in sprite["colors"].items()}
    SM_FRAMES = [f["pixels"] for f in sprite["frames"]]
    mats = materials(sprite)
    P = Part(NAME, smooth_angle=34.0)
    build_body(P)
    # Body top surface for the crackle (sprite px), before finishing.
    P.orient()
    tree = BVHTree.FromBMesh(P.bm)

    def zat(x, y):
        hit = tree.ray_cast(Vector((x, y, 20.0)), Vector((0, 0, -1)))
        return None if hit[0] is None else hit[0].z
    crackles = []
    groups = {}
    for fr in sprite["frames"]:
        pix = {(r, c): v for r, row in enumerate(fr["pixels"]) for c, v in enumerate(row) if 243 <= v <= 253}
        if not pix:
            continue
        # Inner-mask pixels the hull leaves bare on this frame (dark ink the crackle encloses, e.g.
        # between an arc and the neck): the arc bridges them, in its darkest step.
        mk = SM.masks(fr["pixels"], SM_COLORS, SM.pulse_partners(fr["pixels"], SM_FRAMES))
        for r in range(14):
            for c in range(12):
                if mk["inner"][r][c] and (r, c) not in pix and zat(c + 0.5 - 6, r + 0.5) is None:
                    pix[(r, c)] = 243
                    print("bridge", fr["index"], r, c)
        groups.setdefault(tuple(sorted(pix)), []).append((fr["index"], pix))
    # One part per set of crackle pixel positions; frames that share the positions but not the
    # colours share the part, each bead/thread's material animating its palette index (D17).
    crk_mats = {}

    def mat_of(key):
        if key not in crk_mats:
            frames_, pals = key[1], key[0]
            base = pals[0]
            fmap = {f: i for f, i in zip(frames_, pals) if i != base}
            tag = "crk" + "_".join(str(i) for i in pals)
            crk_mats[key] = len(mats)
            # the dim reds glow harder (still their own palette colour, only brighter under the
            # tone map), so the arc's faint tail reads as a red glow, not dark maroon rubble
            e = 1.9 if base <= 245 else (1.5 if base <= 248 else 1.0)
            # matte: lighting only adds a faint sheen, the glow carries the colour (light, not tubes)
            mats.append(common.palette_material(sprite, base, f"zsc_{tag}", metallic=0.0, roughness=1.0,
                                                emission_strength=e, frames=fmap or None))
        return crk_mats[key]
    for poss, members in groups.items():
        idxs = [f for f, _ in members]
        S = Part(f"{NAME}-crackle-{idxs[0]}", smooth_angle=20.0)
        pixels = {}
        for rc in poss:
            pals = tuple(px[rc] for _, px in members)
            pixels[rc] = (pals, tuple(idxs))
        crackle(S, pixels, zat, mat_of)
        crackles.append((S, idxs))
    crackles_o = []
    for S, idxs in crackles:
        o = finish(S, mats, coll)
        common.frame_part(o, idxs)
        crackles_o.append(o)
    crackles = crackles_o
    body = finish(P, mats, coll)
    shell = common.outline_shell(body, coll, voxel=0.009, faces=380, smooth=6, inside=0.004)
    shell.name = f"{NAME}_outline"
    def open_edges(o):
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        n = sum(1 for e in bm.edges if e.is_boundary)
        bm.free()
        return n
    print("open edges before cull", open_edges(body))
    T.cull_hidden(body)
    print("open edges after cull (the culled buried faces' rims)", open_edges(body))
    if bake:
        for o in [shell] + crackles:
            o.hide_render = True
        bake_maps(body, tempfile.mkdtemp(prefix="zsc_bake_"), "zica_supercharger")
    objs = [body, shell] + crackles
    tris = {}
    for o in objs:
        o.data.calc_loop_triangles()
        tris[o.name] = len(o.data.loop_triangles)
    print("triangles", tris)
    me = body.data
    per = {}
    for t in me.loop_triangles:
        nm = me.materials[t.material_index].name
        per[nm] = per.get(nm, 0) + 1
    print("body triangles by material", sorted(per.items(), key=lambda kv: -kv[1]))
    common.export_sprite_model(WT, objs, "sidekicks/zica-supercharger", sprite["sprites"],
                               image_format="WEBP" if bake else "AUTO")
    if not out_dir:
        return
    renders = out_dir / "renders"
    renders.mkdir(parents=True, exist_ok=True)
    shell.hide_render = True
    for o in crackles:
        o.hide_render = False
    render_tops(scene, [body] + crackles, renders)
    render_views(scene, [body] + crackles, renders)
    (renders / "stats.json").write_text(json.dumps({"triangles": tris}, indent=1))


main()
