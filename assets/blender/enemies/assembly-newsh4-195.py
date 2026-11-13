"""Bronze boss arm (newsh4.shp, an assembly of 7 pieces, enemy types 66-72): a hard-surface 3D
version of its sprites built the way the player ships are (usp_talon.py, DECISIONS D50-D53).
Seen in levels 1.3 and 3.17.

Seven 2x2 enemies in a row (sprite.json `assemblyLayout`, newsh4 153, 155, 157, 159, 191, 193, 195)
make one 168x28 px arm reaching right. The sprite is authoritative (D52):
- Plan: the union of the parts follows the sprite's column spans (smoothed stairs): the upper arm
  rows 1-22 over cols 0-29 with its slanted lower end (cols 29-36), the pinched neck (rows 3-16), the
  egg-shaped ball joint whose lower-left lobe reaches row 20 (cols 37-56), the 12 px forearm (rows
  1-13) whose top edge steps down from col 79, and the horn claw curving south to its point at
  col 166, row 25.
- Parts as the shading reads them: a round bronze canister (rows 1-13, the bright rows 2-5 are sheen)
  with bright bolted flanges at both ends, over a dark chamfered housing (rows 13-22) with a lit rib
  along each top edge (rows 14 and 20-21), four louvred cooling grilles between them, a hydraulic
  ram on brackets along its south flank and a bright pipe up its slanted end (the 9-ish pixels at
  cols 29-33); a dark ringed neck; the ball (one smooth shell split by a seam); the steel collar
  (cols 57-65) with blue-grey rims; a bright ring (cols 65-67); the grey-brown junction box (cols
  76-83, rows 1-6) and its strap (cols 80-82); the small piped bay (cols 69-72, rows 9-12); the grey
  block (cols 83-89, rows 2-7); two dark steel saddle clamps (cols 105-112 and 121-130), each with a
  raised grey bracket block where the sprite's grey pixels are; the claw one smooth taper whose
  segments are only shallow grooves.
- Colours: each part the palette index of the sprite pixels it covers (median, darkest shading and
  brightest sheen left out): canister 21 (flanges 23), housing 17 (ribs 18), neck 18, ball 20, collar
  4 (rims 106), forearm root 20, junction box 164, grey block and brackets 4, forearm 18 (top plates
  20), clamps 2, claw 18. Satin metal (metallic ~0.15), Cycles-baked occlusion/roughness only (one
  neutral-grey map for the whole arm, so the pieces' seams match), no concept projection (maps.json
  says "bake": "model", as the player ships in PR #84).

The game contract of the earlier model is kept: the whole arm is built once in assembly coordinates
(Blender X = (u - 84) / 12, Y = (14 - v) / 12 for assembly pixel edge (u, v); the arm's centre,
screen (122, -18), is the origin) and cut into the seven pieces with common.split_assembly, each
exported to public/models/enemies/<piece>.glb with its src/render/spriteModels entry; palette
materials pal_<index>; every piece has one frame. Each piece gets its share of an outline shell
(common.outline_shell, D51; node <piece>_outline with the tyrian_outline extra).

Build space (the Talon toolkit's): x = assembly row edge v (south +), y = assembly column edge u
(toward the claw), z = up, all in sprite px.

Run: blender --background --python assets/blender/enemies/assembly-newsh4-195.py
     [-- --no-bake] [--out arm.glb (all pieces in one file, for review)] [--preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (the Talon's hard-surface toolkit, D50)
from usp_talon import Part, cbox, frange, hull, loft, pchip, plate  # noqa: E402

NAME = "assembly-newsh4-195"
ROOT = common.repo_root(__file__)
PIECES = ["newsh4-153", "newsh4-155", "newsh4-157", "newsh4-159", "newsh4-191", "newsh4-193", "newsh4-195"]
CX0, CY0 = 122, -18
W, H = 168, 28
PX = 1 / 12
NS = 20  # sides of the round sections: index 0 bottom, NS/4 south, NS/2 top, 3NS/4 north
TOP, SOUTH, NORTH = NS // 2, NS // 4, 3 * NS // 4

METAL = 0.3
# The baked occlusion map is neutral grey: a cool tint (the Talon's) turns the bronze dull and dark.
TINT = (1.0, 1.0, 1.0)

# Material slots and their palette indices (sprite medians per region, D52).
(CAN, FLANGE, DEEP, HOUS, HRIB, PIPE, NECK, RING, BALL, COLLAR, RIM, PORT, FORE_A, BOX, BOXDK, GREY,
 FORE_B, PLATE, CLAMP, CLAW, EDGE, STEEL, RAIL) = range(23)
PAL_OF = {CAN: 21, FLANGE: 23, DEEP: 16, HOUS: 17, HRIB: 18, PIPE: 24, NECK: 18, RING: 22, BALL: 20,
          COLLAR: 4, RIM: 106, PORT: 80, FORE_A: 20, BOX: 164, BOXDK: 162, GREY: 4, FORE_B: 18,
          PLATE: 20, CLAMP: 2, CLAW: 18, EDGE: 19, STEEL: 7, RAIL: 22}
SURF = {  # (metallic before METAL scaling, roughness)
    CAN: (0.55, 0.36), FLANGE: (0.6, 0.32), DEEP: (0.3, 0.8), HOUS: (0.5, 0.48), HRIB: (0.55, 0.4),
    PIPE: (0.65, 0.3), NECK: (0.5, 0.45), RING: (0.6, 0.34), BALL: (0.6, 0.3), COLLAR: (0.7, 0.4),
    RIM: (0.8, 0.28), PORT: (0.2, 0.7), FORE_A: (0.55, 0.38), BOX: (0.45, 0.5), BOXDK: (0.4, 0.6),
    GREY: (0.7, 0.4), FORE_B: (0.55, 0.42), PLATE: (0.55, 0.36), CLAMP: (0.7, 0.42), CLAW: (0.55, 0.36),
    EDGE: (0.65, 0.3), STEEL: (0.8, 0.32), RAIL: (0.6, 0.32)}


def merged_sprite():
    data = common.load_sprite(ROOT, "newsh4-195")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def materials(sprite):
    mats = []
    for slot in range(len(PAL_OF)):
        i = PAL_OF[slot]
        met, rough = SURF[slot]
        mats.append(common.palette_material(sprite, i, f"nsh4arm_{slot}", metallic=met * METAL, roughness=rough))
    return mats


# --- the sprite --------------------------------------------------------------------------------

def grid():
    g = [[-1] * W for _ in range(H)]
    sprite = common.load_sprite(ROOT, PIECES[0])
    for e in sprite["assemblyLayout"]:
        frame = common.load_sprite(ROOT, e["model"])["frames"][0]
        x0, y0 = e["cx"] - CX0 + W // 2 - 12, e["cy"] - CY0 + H // 2 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, val in enumerate(row):
                if val >= 0:
                    g[y0 + r][x0 + c] = val
    return g


def spans(g):
    """Top and bottom pixel edges of each column (every column is one run)."""
    out = []
    for c in range(W):
        rows = [r for r in range(H) if g[r][c] >= 0]
        out.append((rows[0], rows[-1] + 1) if rows else None)
    return out


def inner_spans():
    """Top and bottom pixel edges of each column of the sprite's INNER mask (D74,
    docs/agents/OUTLINE-BORDER.md: the sprite minus its ink border, thin parts' free border kept),
    the edge the model's plan goes to; the game's ink outline stands in for the border."""
    sys.path.insert(0, str(ROOT / "tools"))
    import sprite_mask  # noqa: E402  (pure standard library)
    idx, colors = sprite_mask.load(NAME)
    m = sprite_mask.masks(idx, colors)
    out = []
    for c in range(W):
        rows = [r for r in range(H) if m["inner"][r][c] or m["free"][r][c]]
        out.append((rows[0], rows[-1] + 1) if rows else None)
    return out


def edge_curve(sp, c0, c1, which, passes=1):
    """A pchip through the column centres of the sprite's top (0) or bottom (1) edge over columns
    c0..c1, its stairs relaxed by a [1 2 1] filter (ends held)."""
    vals = [sp[c][which] for c in range(c0, c1 + 1)]
    for _ in range(passes):
        vals = [vals[0]] + [(vals[i - 1] + 2 * vals[i] + vals[i + 1]) / 4 for i in range(1, len(vals) - 1)] + [vals[-1]]
    return pchip([c + 0.5 for c in range(c0, c1 + 1)], vals)


# --- sections ----------------------------------------------------------------------------------

def sgnpow(x, e):
    return math.copysign(abs(x) ** e, x)


def sup_pts(vc, hw, zc, hz, n, ns=NS):
    pts = []
    for k in range(ns):
        a = -math.pi / 2 + 2 * math.pi * k / ns
        c, s = math.cos(a), math.sin(a)
        # index k runs bottom -> south (+v) -> top -> north; x = v
        pts.append((vc + hw * sgnpow(c, 2 / n), zc + hz * sgnpow(s, 2 / n)))
    return pts


def mkloop(fn, inset=0.0, ns=NS):
    """A Talon-style loop function from fn(u) -> (vc, hw, zc, hz, n), shrunk by `inset` px."""
    def loopf(u):
        vc, hw, zc, hz, n = fn(u)
        return sup_pts(vc, max(hw - inset, 0.05), zc, max(hz - inset, 0.05), n, ns), (vc, zc)
    return loopf


def sweep(part, path, r, mat, sides=8, cap=True):
    """A round tube along (v, u, z) points (build space)."""
    pts = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        n1 = t.cross(up).normalized()
        n2 = t.cross(n1).normalized()
        ring = [part.v(p + n1 * (r * math.cos(2 * math.pi * k / sides)) + n2 * (r * math.sin(2 * math.pi * k / sides)))
                for k in range(sides)]
        rings.append((ring, p))
    for (r0, c0), (r1, c1) in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            part.f((r0[k], r0[j], r1[j], r1[k]), mat, away=tuple(c0))
    if cap:
        part.f(rings[0][0], mat, out=tuple(pts[0] - pts[1]))
        part.f(rings[-1][0], mat, out=tuple(pts[-1] - pts[-2]))


def poly_loft(part, sections, mat, cap0=True, cap1=True):
    """Loft explicit polygons: sections = [(u, [(v, z), ...])], all with the same point count."""
    rings = []
    for u, pts in sections:
        cx = sum(p[0] for p in pts) / len(pts)
        cz = sum(p[1] for p in pts) / len(pts)
        rings.append(([part.v((v, u, z)) for v, z in pts], (cx, u, cz)))
    n = len(rings[0][0])
    for (r0, c0), (r1, c1) in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            part.f((r0[k], r0[j], r1[j], r1[k]), mat, away=c0)
    if cap0:
        part.f(rings[0][0], mat, out=(0, -1, 0))
    if cap1:
        part.f(rings[-1][0], mat, out=(0, 1, 0))


def disc_bolts(part, centre_v, centre_z, u, r, count, size, mat, a0=0.0, out=-1):
    """Hex-ish bolt heads on a face normal to the arm (u = const), facing `out` along u."""
    for k in range(count):
        a = a0 + 2 * math.pi * k / count
        v, z = centre_v + r * math.cos(a), centre_z + r * math.sin(a)
        hull(part, cbox(v - size, v + size, u + out * 0.35, u - out * 0.05, z - size, z + size, size * 0.35), mat)


def surface_z(fn, u, v):
    """Height of the top surface of a fn(u) -> (vc, hw, zc, hz, n) superellipse section at row v."""
    vc, hw, zc, hz, n = fn(u)
    t = min(abs(v - vc) / hw, 1.0)
    return zc + hz * (1 - t ** n) ** (1 / n)


def radial_bolt(part, u, vc, zc, r, a, size, h, mat):
    """A bolt head on a round surface of radius r about (vc, zc) at column u, at angle `a` from the
    top (positive toward the south), standing h proud, its top edges chamfered."""
    nv, nz = math.sin(a), math.cos(a)
    tv, tz = math.cos(a), -math.sin(a)
    pts = []
    for along, s in ((r - 0.15, size), (r + h * 0.6, size), (r + h, size * 0.65)):
        for su in (-s, s):
            for st in (-s, s):
                pts.append((vc + nv * along + tv * st, u + su, zc + nz * along + tz * st))
    hull(part, pts, mat)


# --- the arm -----------------------------------------------------------------------------------

def build(coll, sprite, g):
    mats = materials(sprite)
    sp = inner_spans()
    P = Part("arm_body", smooth_angle=34)   # big round masses
    D = Part("arm_detail", smooth_angle=34)  # plates, boxes, pipes

    # ---------------- upper arm: canister (rows 1-13) --------------------------------------
    can_r = 6.0
    # Top edge on the inner mask (D74): row 2 over the root (cols 0-8, the ink-topped rear flange),
    # row 1 over cols 9-30, a step to row 2 (cols 31-32), then the shoulder drops to row 4 (col 33)
    # into the neck. The bottom (under the housing) stays at row 13.
    can_top = pchip([0.0, 8.3, 9.7, 30.7, 31.3, 32.5, 33.0, 33.7, 35.0],
                    [2.4, 2.4, 1.0, 1.0, 1.9, 2.15, 3.6, 4.2, 4.3])

    def can_fn(u):
        # Round, 12 px across (rows 1-13), shouldering in over cols 31-33 into the neck.
        top = can_top(min(max(u, 0.0), 35.0))
        hw = (13.0 - top) / 2
        s = min(max((u - 30.7) / 3.0, 0.0), 1.0)
        return 13.0 - hw, hw, 0.0, can_r - 1.6 * s, 2.0
    CAN_CORE = mkloop(can_fn, inset=0.45)
    loft(P, CAN_CORE, [0.4] + frange(1.0, 33.0, 1.0) + [33.4], DEEP)
    # Three armour sleeves with real gaps (panel lines) and a shoulder cone.
    for a, b in ((2.0, 10.3), (10.9, 19.7), (20.3, 26.2)):
        plate(P, CAN_CORE, a, b, CAN, d=0.45, c=0.3, depth=0.3, ystep=1.0)
    plate(P, CAN_CORE, 27.75, 33.3, CAN, d=0.45, c=0.3, depth=0.3, ystep=0.8)
    # Raised bands between the sleeves (bright bronze), standing 0.25 px above the sleeves.
    for a, b in ((10.35, 10.85), (19.75, 20.25)):
        plate(D, CAN_CORE, a - 0.15, b + 0.15, FLANGE, d=0.62, c=0.12, depth=0.4, ystep=1.0)
    # Rear flange (the arm's root, col 0): a heavy bright ring and a dark socket with bolts.
    def flange_fn(u):
        return 7.6, 5.4, 0.0, 6.25, 2.0
    loft(D, mkloop(flange_fn), [0.0, 1.85], FLANGE)
    plate(D, mkloop(flange_fn), 0.0, 1.85, FLANGE, d=0.0001, c=0.3, depth=0.5)
    def socket_fn(u):
        return 7.0, 3.2, 0.0, 3.2, 2.0
    loft(D, mkloop(socket_fn), [-0.5, 0.05], DEEP)
    disc_bolts(D, 7.6, 0.0, 0.0, 4.0, 8, 0.42, STEEL, a0=math.pi / 8)
    # Front flange (where the canister shoulders into the neck): a bright bolted ring.
    plate(D, CAN_CORE, 26.3, 27.65, FLANGE, d=0.7, c=0.2, depth=0.5, ystep=1.0)
    # Bolt circles round both flanges' outer faces (the upper half: the part the camera sees).
    for u, vc, r in ((0.92, 7.6, 5.4), (26.97, 7.0, 6.0)):
        for deg in (-66, -33, 0, 33, 66):
            radial_bolt(D, u, vc, 0.0, r, math.radians(deg), 0.36, 0.28, STEEL)

    # ---------------- upper arm: housing (rows 13-22) ---------------------------------------
    # South edge on the inner mask (D74): row 21 under the root (cols 0-11, where the sprite's
    # bottom row is ink), row 22 over cols 12-29 (a cover plate over the ram), then the slanted end.
    south = pchip([29.5, 30.5, 31.5, 32.5, 33.5, 34.5, 35.5, 36.6],
                  [22.0, 21.15, 20.75, 19.75, 18.0, 16.9, 15.25, 14.9])
    root = pchip([0.0, 11.35, 12.35, 29.5], [21.05, 21.05, 22.0, 22.0])

    def hsec(u, grow=0.0):
        sv = root(max(u, 0.0)) if u <= 29.5 else south(u)
        k = 0.0 if u <= 29.5 else min((u - 29.5) / 7.1, 1.0)
        top = 2.6 - 0.9 * k
        bot = -5.8 + 1.8 * k
        g = grow
        # South flank: an upper face on the silhouette, a channel for the ram, a lower face.
        cv = min(sv - 1.4, 19.6)  # the ram channel's inner wall
        return [(12.2, top + g), (sv - 0.9 - g * 0.4, top + g), (sv + g, top - 0.9), (sv + g, -0.7),
                (cv + g, -1.3), (cv + g, -3.5), (sv - 0.5 + g, -4.1), (sv - 1.8, bot - g),
                (13.0, bot - g), (11.8, bot + 1.4)]
    # The housing starts a pixel in from the canister's root: the sprite's col 0 is ink below row 9.
    stations = [1.0, 1.6] + frange(2.6, 11.0, 2.8) + [11.35, 11.85, 12.35] + frange(13.5, 29.5, 2.7) \
        + [30.5, 31.5, 32.5, 33.5, 34.5, 35.5, 36.6]
    poly_loft(P, [(u, hsec(u)) for u in stations], HOUS)
    # Rear flange of the housing.
    poly_loft(D, [(0.75, hsec(1.0, 0.0)), (0.95, hsec(1.0, 0.3)), (2.45, hsec(1.0, 0.3)), (2.7, hsec(1.0, 0.0))], HRIB)
    for v, z in ((14.2, 1.4), (19.6, 1.4), (14.2, -4.4), (18.6, -4.4)):
        hull(D, cbox(v - 0.42, v + 0.42, 0.4, 0.85, z - 0.42, z + 0.42, 0.15), STEEL)
    # Ribs along the housing's top edges (sprite rows 14 and 20-21: lit edges).
    hull(D, cbox(13.3, 14.9, 2.7, 29.0, 2.0, 3.25, 0.4), HRIB)
    hull(D, cbox(19.4, 20.95, 2.7, 28.8, 2.0, 3.15, 0.4), HRIB)
    # Four louvred cooling grilles on the deck between them: a raised frame round a dark well,
    # four bronze slats across it.
    for i in range(4):
        a = 3.6 + i * 6.1
        b = a + 4.6
        for frame in ((15.2, 19.3, a, a + 0.55), (15.2, 19.3, b - 0.55, b), (15.2, 15.75, a, b), (18.75, 19.3, a, b)):
            hull(D, cbox(frame[0], frame[1], frame[2], frame[3], 2.2, 3.05, 0.18), HRIB)
        hull(D, cbox(15.6, 18.9, a + 0.4, b - 0.4, 2.2, 2.62, 0.05), DEEP)
        for j in range(4):
            u = a + 0.85 + j * (b - a - 1.7) / 3
            hull(D, cbox(15.75, 18.75, u - 0.2, u + 0.2, 2.4, 2.92, 0.1), HOUS)
    # Hydraulic ram on brackets along the housing's south flank (seen by the tilted game camera and
    # the side views; inside the sprite's outline from above): cylinder, gland, polished rod, eyes.
    RV, RZ = 20.3, -2.4
    sweep(D, [(RV, 3.6, RZ), (RV, 15.6, RZ)], 0.66, STEEL, sides=12)    # cylinder
    sweep(D, [(RV, 15.6, RZ), (RV, 16.8, RZ)], 0.72, FLANGE, sides=12)  # gland
    sweep(D, [(RV, 16.8, RZ), (RV, 26.6, RZ)], 0.36, RAIL, sides=10)    # rod
    sweep(D, [(RV, 3.0, RZ), (RV, 3.6, RZ)], 0.72, FLANGE, sides=12)    # end cap
    for u in (3.0, 27.2):  # end eyes on brackets bolted to the flank, the pins across them
        hull(D, cbox(19.0, 20.95, u - 0.85, u + 0.85, RZ - 1.3, RZ + 1.3, 0.3), HRIB)
        sweep(D, [(20.45, u, RZ), (21.0, u, RZ)], 0.5, STEEL, sides=8)
    hull(D, cbox(19.0, 21.0, 9.0, 10.2, RZ - 1.0, RZ + 1.0, 0.25), HRIB)  # mid strap
    # Bright hydraulic pipe up the slanted end into the ball (sprite cols 29-33, rows 17-21).
    sweep(D, [(20.6, 25.0, 1.2), (20.7, 28.6, 1.6), (19.7, 30.6, 2.1), (18.2, 32.4, 2.6), (16.4, 34.0, 3.0),
              (14.6, 35.5, 3.4), (13.6, 37.5, 3.6)], 0.62, PIPE, sides=8)

    # ---------------- neck (cols 31-37) ------------------------------------------------------
    def neck_fn(u):
        return 8.6, 4.4, 0.0, 4.4, 2.2  # rows 4.2-13 (the inner mask: row 3 is ink over the neck)
    loft(P, mkloop(neck_fn), [30.5, 33.0, 35.6, 38.2], NECK)
    for a in (32.9, 35.0):
        plate(D, mkloop(neck_fn), a, a + 1.0, EDGE, d=0.3, c=0.18, depth=0.3)

    # ---------------- ball joint (cols 37-57) -------------------------------------------------
    btop = edge_curve(sp, 35, 58, 0, passes=2)
    bbot = edge_curve(sp, 36, 58, 1, passes=1)

    def ball_fn(u):
        t = btop(u)
        b = bbot(u)
        hw = (b - t) / 2
        # A round shell: tallest over the lobe, easing into the 5.5 px forearm.
        k = min(max((u - 36.6) / 2.0, 0.0), 1.0)
        hz = min(hw * 0.95, 8.4)
        hz = 5.0 + (hz - 5.0) * (k * (2 - k))
        return (t + b) / 2, hw, 0.0, hz, 2.1
    BALL_CORE = mkloop(ball_fn, inset=0.4)
    loft(P, BALL_CORE, [36.6] + frange(37.2, 57.6, 0.8), DEEP)
    # The ball's neck-side shoulder is the sprite's dark band (cols 37-40, index 18): a darker
    # socket ring, then the shell in two halves split by a seam.
    plate(P, BALL_CORE, 36.9, 39.9, NECK, d=0.4, c=0.3, depth=0.3, ystep=0.8)
    plate(P, BALL_CORE, 40.3, 46.9, BALL, d=0.4, c=0.3, depth=0.3, ystep=0.8)
    plate(P, BALL_CORE, 47.5, 57.5, BALL, d=0.4, c=0.3, depth=0.3, ystep=0.8)
    # Socket lip where the neck enters the ball.
    plate(D, mkloop(lambda u: (8.7, 5.0, 0.0, 5.3, 2.2)), 36.6, 37.9, EDGE, d=0.3, c=0.25, depth=0.6)

    # ---------------- forearm and claw: one tapering core, armoured -------------------------
    # The inner mask's last full column is 162 (cols 163-165 are the tip's ink, D74).
    ftop = edge_curve(sp, 55, 162, 0, passes=2)
    fbot_s = edge_curve(sp, 55, 162, 1, passes=2)
    # Near the tip the claw's south edge follows the inner mask's own stairs (no relaxing): it is
    # only 2-4 px wide there, and the relaxed curve drops a pixel each side of col 153's notch.
    fbot_r = edge_curve(sp, 140, 162, 1, passes=0)

    def fbot(u):
        k = min(max((u - 144.0) / 4.0, 0.0), 1.0)
        return fbot_s(u) * (1 - k) + fbot_r(min(max(u, 140.5), 162.5)) * k
    U_TIP, U_TAPER = 163.6, 162.2
    hz_f = pchip([56.0, 66.0, 77.0, 84.0, 100.0, 127.0, 140.0, 150.5, 158.5, U_TIP],
                 [5.6, 5.4, 5.3, 5.0, 4.7, 3.9, 3.0, 2.0, 1.2, 0.15])
    zc_f = pchip([56.0, 127.0, 140.0, 153.5, U_TIP], [0.0, 0.0, -0.8, -2.4, -4.2])

    def fore_fn(u):
        t = ftop(min(u, 162.5))
        b = fbot(min(u, 162.5))
        if u > U_TAPER:
            k = (u - U_TAPER) / (U_TIP - U_TAPER)
            c = (t + b) / 2 + 0.4 * k
            hw = max((b - t) / 2 * (1 - k), 0.06)
            return c, hw, zc_f(u), max(hz_f(u), 0.06), 2.0
        n = 2.8 if u < 127 else 2.8 - 0.8 * min((u - 127) / 25, 1.0)
        return (t + b) / 2, (b - t) / 2, zc_f(u), hz_f(u), n
    FORE = mkloop(fore_fn)
    CORE_IN = mkloop(fore_fn, inset=0.4)
    CORE_TIP = mkloop(fore_fn, inset=0.0)

    def FORE_CORE(u):
        # The core comes up flush with the outline past the last claw segment, so the tip itself
        # is the outline (the sprite's last rows) rather than a step inside it.
        if u <= 158.2:
            return CORE_IN(u)
        k = min((u - 158.2) / 1.4, 1.0)
        (pa, c), (pb, _) = CORE_IN(u), CORE_TIP(u)
        return [(a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k) for a, b in zip(pa, pb)], c
    loft(P, FORE_CORE, frange(56.4, 57.2, 1.0) + frange(57.2, 158.6, 1.2) + frange(159.2, U_TAPER, 0.6)
         + frange(U_TAPER + 0.4, U_TIP - 0.3, 0.4) + [U_TIP], DEEP)

    # Collar ring where the ball meets the forearm.
    plate(D, FORE_CORE, 55.6, 57.0, RING, d=0.7, c=0.25, depth=0.6)
    # Steel collar (cols 57-65), its blue-grey rims, the bright ring after it.
    def collar_fn(u):
        vc, hw, zc, hz, n = fore_fn(u)
        return vc, hw, zc, 6.1, 3.2
    plate(D, mkloop(collar_fn, inset=0.4), 57.6, 63.6, COLLAR, d=0.4, c=0.25, depth=0.5, ystep=1.0)
    for a, b in ((57.0, 58.4), (63.6, 65.0)):
        plate(D, mkloop(collar_fn, inset=0.4), a, b, RIM, d=0.55, c=0.2, depth=0.6)
    # Dark port in the collar's south face (sprite 64,9: index 80), seen from the game camera.
    hull(D, cbox(11.6, 12.9, 60.0, 62.2, -1.6, 1.4, 0.25), PORT)
    plate(D, FORE_CORE, 65.0, 67.4, RING, d=0.62, c=0.25, depth=0.5)
    # Forearm root sleeve (cols 67-76, pal 20) and the main forearm sleeves (pal 18).
    plate(D, FORE_CORE, 67.4, 76.2, FORE_A, d=0.4, c=0.25, depth=0.3, ystep=1.2)
    # Piped bay on the south shoulder (cols 69-72, rows 9-12): a recessed box with two pipes.
    hull(D, cbox(9.2, 12.85, 68.8, 72.9, 1.0, 4.3, 0.35), BOX)
    for v in (10.1, 11.7):  # two pipes over the bay, diving into the sleeve at each end
        sweep(D, [(v, 67.6, 3.6), (v, 68.6, 4.65), (v, 73.1, 4.65), (v, 74.2, 3.6)], 0.34, STEEL, sides=6)
    # Junction box (cols 76-83, rows 1-6) and its strap round the arm (cols 80-82).
    plate(D, FORE_CORE, 79.8, 82.9, BOX, d=0.5, c=0.25, depth=0.4)
    hull(D, cbox(1.9, 6.9, 76.1, 78.9, 1.0, 6.25, 0.45), BOX)
    hull(D, cbox(2.1, 6.9, 78.9, 83.8, 1.0, 6.25, 0.45), BOX)
    for u in (77.4, 80.0, 82.6):  # lid seams
        hull(D, cbox(1.7, 6.5, u - 0.18, u + 0.18, 6.1, 6.42, 0.06), BOXDK)
    for v, u in ((2.6, 77.0), (5.6, 77.0), (3.2, 83.0), (5.6, 83.0)):  # bolts
        hull(D, cbox(v - 0.35, v + 0.35, u - 0.35, u + 0.35, 6.1, 6.55, 0.15), STEEL)
    plate(D, FORE_CORE, 76.2, 79.8, FORE_A, d=0.4, c=0.25, depth=0.3)
    # Grey block on the forearm (cols 83-89, rows 2-7), with a vent.
    hull(D, cbox(3.05, 7.4, 83.8, 89.6, 1.0, 6.0, 0.5), GREY)
    for k in range(3):
        u = 85.0 + k * 1.3
        hull(D, cbox(3.0, 6.6, u, u + 0.6, 5.7, 6.15, 0.1), DEEP)
    # Forearm sleeves (pal 18) with gaps, and the lit top plates (pal 20, sprite rows 4-6).
    for a, b in ((83.0, 96.0), (96.6, 104.6), (112.6, 120.8)):
        plate(D, FORE_CORE, a, b, FORE_B, d=0.4, c=0.25, depth=0.3, ystep=1.2)
    # The claw is one smooth taper (as the sprite): its segments meet in narrow, shallow grooves
    # with small chamfers, so no step shows in the outline.
    for a, b in ((130.2, 138.65), (138.95, 150.45), (150.75, 158.2)):
        plate(D, FORE_CORE, a, b, CLAW, d=0.4, c=0.1, depth=0.3, ystep=1.0, ch1=b < 158)
    # 104.6-112.6 and 120.8-130.2 are the clamps' saddles: the sleeve under them.
    plate(D, FORE_CORE, 104.6, 112.6, FORE_B, d=0.4, c=0.2, depth=0.3, ystep=1.2)
    plate(D, FORE_CORE, 120.8, 130.2, FORE_B, d=0.4, c=0.2, depth=0.3, ystep=1.2)
    # Top plates over the sleeves, north of the crown (the sprite's lighter rows 4-6).
    for a, b in ((90.6, 95.6), (97.2, 104.0), (113.4, 120.2)):
        plate(D, mkloop(fore_fn), a, b, PLATE, s0=TOP - 1.2, s1=TOP + 2.6, d=0.3, c=0.25, depth=0.35, ystep=1.0)
    # Clamps: dark steel saddles over the top (rows 5-10 at cols 105-112, rows 7-12 at 121-130),
    # each carrying a raised grey bracket block where the sprite's grey pixels are (rows 5-8 at
    # cols 105-111, rows 7-11 at cols 123-128), bolted at its corners.
    for a, b, s0, s1, (bv0, bv1, bu0, bu1), (rv0, rv1) in (
            (105.0, 112.4, TOP - 2.4, TOP + 3.2, (4.9, 8.9, 105.3, 111.3), (6.0, 7.0)),
            (121.4, 129.6, TOP - 2.6, TOP + 3.0, (8.55, 11.6, 123.6, 128.6), (9.6, 10.6))):
        plate(D, mkloop(fore_fn), a, b, CLAMP, s0=s0, s1=s1, d=0.75, c=0.3, depth=0.5, ystep=1.0)
        lo = min(surface_z(fore_fn, u, v) for u in (bu0, bu1) for v in (bv0, bv1))
        hi = max(surface_z(fore_fn, u, v) for u in (bu0, bu1) for v in (bv0, bv1, (bv0 + bv1) / 2))
        top = hi + 1.35
        # The block is the sprite's dark grey (index 2); its lit row (index 4) a raised rib on top.
        hull(D, cbox(bv0, bv1, bu0, bu1, lo - 0.3, top, 0.4), CLAMP)
        hull(D, cbox(rv0, rv1, bu0 + 0.7, bu1 - 0.7, top - 0.3, top + 0.3, 0.15), GREY)
        for v in (bv0 + 0.55, bv1 - 0.55):
            for u in (bu0 + 0.55, bu1 - 0.55):
                hull(D, cbox(v - 0.28, v + 0.28, u - 0.28, u + 0.28, top - 0.2, top + 0.2, 0.1), STEEL)
    # Claw: the cutting edge along its inner (south) flank, a bright ridge.
    edge = [(fbot(u) - 0.7, u, zc_f(u) - 0.1) for u in frange(130.0, 160.5, 1.5)]
    sweep(D, edge, 0.32, EDGE, sides=6)

    objs = [finish(p, mats, coll) for p in (P, D)]
    return objs


def finish(part, mats, coll):
    """Talon finish with this model's axes: X = (u - 84) / 12, Y = (14 - v) / 12, Z = z / 12."""
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((0, PX, 0, -84 * PX), (-PX, 0, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)  # det > 0: no flip
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


def bake_maps(obj, out_dir, size=2048, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, tuple(i for i in range(len(PAL_OF)) if i != PORT)
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "nsh4arm")


def split_open(obj, layout, coll, suffix):
    """split_assembly without capping the cuts (for the outline shells: a capped cut would be
    outlined as a seam between the pieces)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


def composite_png(g, colors, out):
    """The whole arm's sprite as one image, padded to the 24:28 shape that render_preview expects
    for size 14 (168 x 196 px, the arm in the middle)."""
    import numpy as np
    img = np.zeros((196, 168, 4), dtype=np.float32)
    y0 = (196 - H) // 2
    for r in range(H):
        for c in range(W):
            if g[r][c] >= 0:
                img[y0 + r, c] = [*(ch / 255 for ch in colors[str(g[r][c])]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 168, 196, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    import tempfile
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = merged_sprite()
    g = grid()
    coll = common.reset_collection(NAME)
    objs = build(coll, sprite, g)
    obj = T.join(objs, NAME)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    # Baked occlusion and edge wear only (no concept projection: maps.json says "bake": "model",
    # as the player ships, PR #84); one map for the whole arm, which every piece carries, so the
    # occlusion runs on across the cuts.
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="nsh4arm_bake_"), size=2048, samples=64)
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(obj, coll, voxel=0.02, faces=4000, smooth=12, islands="outer")
    shell.hide_render = True
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    obj.modifiers.clear()
    pieces = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll, "_outline")
    outline_mat = shell.data.materials[0]
    review = []
    for name in PIECES:
        p, s = pieces[name], shells[name]
        p.name = name  # the split names it; make sure no leftover object took the name first
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        s.name = f"{name}_outline"
        s.data.shade_smooth()
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        s["tyrian_outline"] = True
        s.hide_render = True
        pt = sum(len(q.vertices) - 2 for q in p.data.polygons)
        print(f"{NAME}: piece {name}: {pt} triangles, outline {len(s.data.polygons)} faces")
        if "--out" in argv:
            review += [p, s]
        else:
            data = common.load_sprite(ROOT, name)
            common.export_sprite_model(ROOT, [p, s], f"enemies/{name}", data["sprites"], image_format=fmt)
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        common.export_glb(review, out, image_format=fmt)
        print(f"exported {out}")
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        ref = composite_png(g, sprite["colors"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=14, view_px=640)


if __name__ == "__main__":
    main()
