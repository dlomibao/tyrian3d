"""Steel hover drone (newshm.shp frames 123, 125, 127), a hard-surface flying craft that is its
sprite in 3D. Earlier builds made it a four-legged walker; it is not one (re-identified, see below).

What it is: enemy type 777 in 2.5 SOH JIN and 2.9 MISTAKES, armour 6, no gun, a swarm unit drawn on
the ground(25) layer. Seen from above: a hooded rear housing with a dark slot (rows 2-6), a dark
collar carrying the spine and two pairs of blue lamps (rows 6-9), broad shoulders with round pods
(rows 10-14), a waist (row 15) and a long rounded forebody (rows 16-24) with small side pods.

Identity, with evidence (tools/enemy_behaviour.mjs on origin/main, PR #204; D120/D122, D166/D167:
"ground" is only the draw layer):
- Speed: it moves 2-5 px/tick down the screen (dat3 ymove 1-3, then event 19 sets (0,+3..+5)) on
  top of the scroll; in 2.9 the terrain is static (scroll 0) and it still swoops (-3,+2) ->
  (-1..-2,+4) px/tick across ground that is not moving. Weaving 3-5 px/tick diagonal swoops are
  not a stepping gait; D166's gunship flew at 4 px/tick on the same layer.
- Formation: its stack partners are its own type at dx +-20, dy 0, often rigid: rows of three
  flying in line, changing course together on event 19.
- Frames: 123/125/127 differ only laterally. 125 widens the shoulders by one pixel a side
  (rows 10-14) and pushes both flank pods out (rows 17-21); 123 and 127 push one flank pod a row
  longer than the other (mirrors). No foot ever moves fore/aft or shows a foot outline, and the
  head, collar and body never change: no leg cycle. Read as a flier's side vanes and nacelles
  trimming / flaring as it weaves, which is what the frames are built as.
So it is built as a hovering drone: nothing reaches the ground, the underside is a closed round
belly, long parts are level (D163), no floor plate (D130), lamps keep their emission (D126).

Which end is the front: the hood's slot (row 5, cols 11-14) opens on its SOUTH side and the
craft flies DOWN the screen, so the nose is south (the long rounded forebody) and the hood is the
raised sensor/drive housing at the stern, looking forward over the shoulders. The tilted game
camera (from the south) sees the slot, the lamps and the chest, as the sprite draws them.

Frames (one model, per-frame parts, D17/D46): 123 right side vane extended, 127 the mirror; 125
both vanes and both shoulder nacelles flared out a pixel. Each frame is a whole closed object
with its own outline shell, frame_part-tagged.

Sprite rules: plan from the INNER mask (D74), smooth pchip curves through the steps; the bright
crown, centre stripe and pod glints are sheen (satin metal), not geometry; colours are the sprite's
palette index per region (measured by --measure). Texture: AO/roughness bake only (no foil).

Run: blender --background --factory-startup --python enemies/newshm-123.py -- [--no-bake] [--out X.glb]
                                                                         [--measure m.json] [--render DIR]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
from usp_talon import pchip  # noqa: E402

HERE = Path("/Users/dlomibao/projects/tyrian-scratch/e2-enemies-1/newshm-123/final")
NAME = "newshm-123"
FRAMES = (123, 125, 127)
PX = 1 / 12
AX = 1.0  # the figure's axis: column edge 13 -> x = 1 px from the sprite centre

# Materials: (palette index, metallic, roughness, emission)
STEEL, HULL, RAIL, WAIST, DARK, CHANNEL, RECESS, VISOR, LAMP, LAMP_S = range(10)
MATS = {
    STEEL: (56, 0.45, 0.36, 0.0),    # hood, chest, shoulder pads (sprite median 56)
    HULL: (55, 0.45, 0.38, 0.0),     # forebody plates, hip pods (median 55)
    RAIL: (55, 0.5, 0.32, 0.0),      # neck pistons (cols 11 and 14, trimmed median 55)
    WAIST: (52, 0.45, 0.4, 0.0),     # waist drum, vent slats (rows 13-15, trimmed median 52)
    DARK: (52, 0.4, 0.45, 0.0),      # under-structure, belly, joints, lower chest plate
    CHANNEL: (49, 0.35, 0.5, 0.0),   # the neck's dark channel (48-50)
    RECESS: (1, 0.3, 0.55, 0.0),     # collar housing (the sprite's dark 1 pixels round the lamps)
    VISOR: (49, 0.2, 0.4, 0.0),      # the slot (1/49; trimmed median 49): satin dark glass, stays dark
    LAMP: (153, 0.0, 0.3, 1.1),      # big blue lamps, row 9 (153/156)
    LAMP_S: (152, 0.0, 0.3, 1.1),    # small blue lamps, row 7 (152)
}
TINT = (0.97, 0.985, 1.0)


# --- geometry helpers (sprite px: xr from the axis, y = sprite row edge, down the screen, z up) ----

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def face(self, vs, mat):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        return f


def ring(cx, y, hw, zb, zt, n=20, p=2.6, pb=None, hwb=None):
    """A superellipse section (x-z) at row y: half width hw (hwb at the bottom), from zb to zt."""
    pb = p if pb is None else pb
    hwb = hw if hwb is None else hwb
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        e = p if s >= 0 else pb
        w = hw if s >= 0 else hwb
        x = cx + w * math.copysign(abs(c) ** (2 / e), c)
        z = zc + hh * math.copysign(abs(s) ** (2 / e), s)
        pts.append((x, y, z))
    return pts


def loft(m, rings, mat, mats=None):
    """Closed tube through rings (lists of xyz with the same count), capped both ends."""
    vr = [[m.bm.verts.new(p) for p in r] for r in rings]
    n = len(vr[0])
    for k, (a, b) in enumerate(zip(vr, vr[1:])):
        mk = mats[k] if mats else mat
        for i in range(n):
            j = (i + 1) % n
            m.face((a[i], a[j], b[j], b[i]), mk)
    m.face(vr[0], mats[0] if mats else mat)
    m.face(list(reversed(vr[-1])), mats[-1] if mats else mat)
    return vr


def hull(m, pts, mat):
    """Convex hull of points (chamfered blocks)."""
    bm = m.bm
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    live = [v for v in verts if v.is_valid]
    for f in {f for v in live for f in v.link_faces}:
        f.material_index = mat


def cbox(x0, x1, y0, y1, z0, z1, ch, z1b=None, chz=None):
    """Corner points of a chamfered box; the top may slope from z1 (y0 end) to z1b (y1 end)."""
    chz = ch if chz is None else chz
    z1b = z1 if z1b is None else z1b
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            for zz, sz in ((z0, 1), (None, -1)):
                if zz is None:
                    zz = z1 if y == y0 else z1b
                pts += [(x + sx * ch, y, zz + sz * chz), (x, y + sy * ch, zz + sz * chz), (x + sx * ch, y + sy * ch, zz)]
    return pts


def dome(m, cx, cy, rx, ry, z0, h, mat, n=16, k=5, p=2.2, base=0.0):
    """A closed dome: superellipse plan rx x ry at z0 (with a short vertical skirt `base`), rising h."""
    rings = []
    if base > 0:
        rings.append([(cx + x, cy + y, z0 - base) for x, y in _plan(rx, ry, n, p)])
    for i in range(k + 1):
        phi = (math.pi / 2) * i / (k + 1)
        s = math.cos(phi)
        rings.append([(cx + x * s, cy + y * s, z0 + h * math.sin(phi)) for x, y in _plan(rx, ry, n, p)])
    vr = [[m.bm.verts.new(q) for q in r] for r in rings]
    apex = m.bm.verts.new((cx, cy, z0 + h))
    for a, b in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            m.face((a[i], a[j], b[j], b[i]), mat)
    for i in range(n):
        j = (i + 1) % n
        m.face((vr[-1][i], vr[-1][j], apex), mat)
    m.face(list(reversed(vr[0])), mat)


def _plan(rx, ry, n, p):
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        out.append((rx * math.copysign(abs(c) ** (2 / p), c), ry * math.copysign(abs(s) ** (2 / p), s)))
    return out


def cyl(m, p0, p1, r, mat, n=8, r1=None):
    """A capped cylinder (or cone, r1) from p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    q = d.to_track_quat("Z", "Y")
    rot = q.to_matrix().to_4x4()
    mid = (p0 + p1) / 2
    res = bmesh.ops.create_cone(m.bm, cap_ends=True, cap_tris=False, segments=n, radius1=r,
                                radius2=r if r1 is None else r1, depth=d.length,
                                matrix=Matrix.Translation(mid) @ rot)
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat


def mirror(fn):
    for s in (-1, 1):
        fn(s)


# --- the drone --------------------------------------------------------------------------------

# Hood (rows 3-6): plan half width and top height per row edge (pchip).
HOOD_Y = [2.9, 3.05, 3.35, 3.8, 4.4, 5.0, 5.6, 6.1, 6.55]
HOOD_HW = [1.0, 2.2, 3.0, 3.6, 3.95, 4.0, 3.95, 3.85, 3.6]
HOOD_ZT = [4.3, 5.4, 6.3, 7.0, 7.45, 7.55, 7.1, 6.35, 5.7]   # the back rolls down (no flat slab)
HOOD_ZB, HOOD_P = 3.2, 2.1
# Collar (rows 5.5-10.3): dark housing carrying the neck and lamps.
COL_Y = [5.4, 6.0, 8.4, 9.0, 9.5, 10.4]
COL_HW = [3.85, 3.9, 3.9, 4.3, 4.85, 4.85]
COL_ZT = [5.6, 5.6, 5.5, 5.4, 5.3, 5.2]
# Waist drum (rows 14-16.5).
WAI_Y = [13.9, 14.6, 15.2, 15.8, 16.5]
WAI_HW = [4.2, 3.95, 3.7, 3.45, 3.0]
# Forebody (rows 15.6-25): half width, top and bottom heights.
FB_Y = [15.6, 16.4, 18.0, 19.5, 21.0, 22.4, 23.4, 24.1, 24.6, 24.92]
FB_HW = [3.05, 3.1, 3.25, 3.25, 3.15, 3.0, 2.7, 2.2, 1.55, 0.7]
FB_ZT = [6.3, 6.45, 6.4, 6.15, 5.75, 5.25, 4.8, 4.45, 4.15, 3.9]
FB_ZB = [2.2, 2.0, 1.9, 1.9, 2.0, 2.2, 2.5, 2.85, 3.15, 3.35]   # a round belly, level along its length


def stations(a, b, step):
    n = max(2, int(round((b - a) / step)) + 1)
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def hood_z(x, y):
    """Height of the hood's top surface at (x, y) (its superellipse section)."""
    hw, zt = pchip(HOOD_Y, HOOD_HW)(y), pchip(HOOD_Y, HOOD_ZT)(y)
    zc, hh = (HOOD_ZB + zt) / 2, (zt - HOOD_ZB) / 2
    u = min(abs(x) / hw, 1.0)
    return zc + hh * (1 - u ** HOOD_P) ** (1 / HOOD_P)


def surface_patch(m, f, xs, ys, up, down, mat):
    """A closed plate following height field f over the grid xs x ys, `up` above it, `down` below."""
    top = [[m.bm.verts.new((x, y, f(x, y) + up)) for x in xs] for y in ys]
    bot = [[m.bm.verts.new((x, y, f(x, y) - down)) for x in xs] for y in ys]
    nx, ny = len(xs), len(ys)
    for j in range(ny - 1):
        for i in range(nx - 1):
            m.face((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]), mat)
            m.face((bot[j][i], bot[j + 1][i], bot[j + 1][i + 1], bot[j][i + 1]), mat)
    ring_ = [(0, i) for i in range(nx)] + [(j, nx - 1) for j in range(1, ny)] + \
        [(ny - 1, i) for i in range(nx - 2, -1, -1)] + [(j, 0) for j in range(ny - 2, 0, -1)]
    for k in range(len(ring_)):
        (j0, i0), (j1, i1) = ring_[k], ring_[(k + 1) % len(ring_)]
        m.face((top[j0][i0], bot[j0][i0], bot[j1][i1], top[j1][i1]), mat)


def build_hood(m):
    """The hooded head: a rounded helmet shell (rows 3-6) whose front slopes forward and down like a
    bowed hood; the black visor sits in that slope (rows 5-6, cols 11-14) under a rolled brow and
    framed by the hood's rim, so it looks down the screen, the way the drone flies."""
    hw, zt = pchip(HOOD_Y, HOOD_HW), pchip(HOOD_Y, HOOD_ZT)
    ys = stations(HOOD_Y[0], HOOD_Y[-1], 0.4)
    loft(m, [ring(0, y, hw(y), HOOD_ZB, zt(y), n=18, p=HOOD_P, pb=2.6) for y in ys], STEEL)
    # Visor: a black glass plate on the hood's sloping face, narrowing toward the chin.
    vy = stations(5.2, 6.45, 0.25)
    vx = stations(-1, 1, 0.25)
    wid = pchip([5.2, 5.8, 6.45], [2.1, 2.05, 1.7])
    top = [[m.bm.verts.new((t * wid(y), y, hood_z(t * wid(y), y) + 0.1)) for t in vx] for y in vy]
    bot = [[m.bm.verts.new((t * wid(y), y, hood_z(t * wid(y), y) - 0.5)) for t in vx] for y in vy]
    nx, ny = len(vx), len(vy)
    for j in range(ny - 1):
        for i in range(nx - 1):
            m.face((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]), VISOR)
            m.face((bot[j][i], bot[j + 1][i], bot[j + 1][i + 1], bot[j][i + 1]), VISOR)
    rim = [(0, i) for i in range(nx)] + [(j, nx - 1) for j in range(1, ny)] + \
        [(ny - 1, i) for i in range(nx - 2, -1, -1)] + [(j, 0) for j in range(ny - 2, 0, -1)]
    for k in range(len(rim)):
        (j0, i0), (j1, i1) = rim[k], rim[(k + 1) % len(rim)]
        m.face((top[j0][i0], bot[j0][i0], bot[j1][i1], top[j1][i1]), VISOR)
    # The hood's rim round the visor: a rolled brow over it and the cheek edges down its sides.
    edge = [(-wid(y) - 0.25, y) for y in reversed(vy)] + [(t * 2.35, 5.0) for t in stations(-1, 1, 0.2)][1:-1] + \
        [(wid(y) + 0.25, y) for y in vy]
    _tube(m, [(x, y, hood_z(x, y) + 0.08) for x, y in edge], 0.24, STEEL)
    # Chin guard under the visor.
    hull(m, cbox(-1.9, 1.9, 6.3, 6.85, 4.3, 5.75, 0.2, z1b=5.35), RAIL)
    # Back plate: a raised panel on the hood's back slope (seen from behind and above).
    surface_patch(m, hood_z, stations(-1.25, 1.25, 0.625), stations(3.25, 4.1, 0.425), 0.14, 0.35, STEEL)
    # Crest ribs along the hood's crown (machined, low).
    for s in (-1, 1):
        rib = [(s * 1.35, y, hood_z(s * 1.35, y) + 0.04) for y in stations(3.35, 4.6, 0.25)]
        _tube(m, rib, 0.16, STEEL)


def _xs(s, a, b):
    return (min(s * a, s * b), max(s * a, s * b))


def _tube(m, pts, r, mat, n=6):
    """A round tube along a polyline (rings perpendicular to it), capped."""
    rings = []
    for i, p in enumerate(pts):
        p = Vector(p)
        a = Vector(pts[max(0, i - 1)])
        b = Vector(pts[min(len(pts) - 1, i + 1)])
        t = (b - a).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(up).normalized()
        w = u.cross(t).normalized()
        rings.append([tuple(p + u * (r * math.cos(2 * math.pi * k / n)) + w * (r * math.sin(2 * math.pi * k / n)))
                      for k in range(n)])
    loft(m, rings, mat)


def build_collar(m):
    hw, zt = pchip(COL_Y, COL_HW), pchip(COL_Y, COL_ZT)
    ys = stations(COL_Y[0], COL_Y[-1], 0.5)
    loft(m, [ring(0, y, hw(y), 2.4, zt(y), n=12, p=3.2, pb=2.4) for y in ys], RECESS)
    # Ribs across the collar's flanks (rows 6 and 8: the sprite's dark bands between the lamps).
    for y in (6.55, 8.45):
        mirror(lambda s, y=y: hull(m, cbox(*_xs(s, 2.15, 3.7), y - 0.28, y + 0.28, 4.6, zt(y) + 0.45, 0.12), RECESS))
    # Neck: two steel pistons (cols 11 and 14) either side of a dark channel (cols 12-13).
    hull(m, cbox(-1.05, 1.05, 5.9, 10.4, 4.6, 6.05, 0.2, z1b=6.35), CHANNEL)
    for s in (-1, 1):
        x = s * 1.55
        cyl(m, (x, 5.95, 6.15), (x, 8.3, 6.45), 0.58, RAIL, n=12)        # sleeve
        cyl(m, (x, 8.2, 6.45), (x, 10.6, 6.75), 0.42, RAIL, n=12)        # rod
        cyl(m, (x, 8.15, 6.45), (x, 8.45, 6.48), 0.68, DARK, n=12)       # gland collar
    # Lamps: small at row 7 (cols 9 / 16), big ovals at row 9 (cols 8-9 / 16-17), in dark bezels.
    for s in (-1, 1):
        cy, cx = 7.5, s * 3.45
        dome(m, cx, cy, 0.68, 0.62, 5.1, 0.35, RECESS, n=12, k=2, base=0.4)
        dome(m, cx, cy, 0.48, 0.44, 5.42, 0.36, LAMP_S, n=12, k=3)
        cy, cx = 9.55, s * 3.9
        dome(m, cx, cy, 1.15, 0.66, 4.95, 0.35, RECESS, n=14, k=2, base=0.4)
        dome(m, cx, cy, 0.92, 0.48, 5.28, 0.42, LAMP, n=14, k=3)


def build_chest(m):
    # Upper chest plate (rows 10-13, cols 10-14) sloping down toward the front.
    hull(m, cbox(-2.75, 2.75, 9.85, 13.1, 3.4, 7.15, 0.45, z1b=6.55), STEEL)
    # Lower chest plate (row 13-14: the sprite's darker band 51-53) with vent slats.
    hull(m, cbox(-2.45, 2.45, 12.9, 14.5, 3.4, 6.35, 0.3, z1b=5.75), DARK)
    for x in (-1.5, -0.5, 0.5, 1.5):
        hull(m, cbox(x - 0.28, x + 0.28, 13.05, 14.3, 5.6, 6.45, 0.1, z1b=5.95), WAIST)
    # Centre keel ridge of the chest (a low machined rib, not the sprite's sheen stripe).
    hull(m, cbox(-0.35, 0.35, 10.0, 12.9, 6.6, 7.35, 0.15, z1b=6.85), STEEL)


def build_shoulders(m, frame):
    """Shoulder nacelles (rows 10-14): round armoured pods on a cross yoke, closed below by a round
    shell; 125 flares them out one pixel a side (the sprite's wider shoulders)."""
    out = 1.0 if frame == 125 else 0.0
    hull(m, cbox(-(4.95 + out), 4.95 + out, 10.6, 14.85, 3.4, 5.5, 0.5, z1b=5.1), DARK)
    for s in (-1, 1):
        cx = s * (4.55 + 0.9 * out)
        cy = 12.1
        rx = 1.6 if not out else 1.55
        # Pod: a rounded cowl (two stacked shells) over a drum, with a round underside.
        dome(m, cx, cy, rx, 2.3, 4.9, 1.85, STEEL, n=16, k=4, p=2.5, base=1.0)
        dome(m, cx + s * 0.05, cy + 0.2, rx + 0.12, 2.0, 4.2, 0.9, DARK, n=16, k=2, p=2.6, base=0.5)
        dome(m, cx, cy, rx - 0.05, 2.2, 3.95, -1.45, DARK, n=16, k=3, p=2.3)
        for by in (11.3, 13.2):
            dome(m, cx + s * 0.2, by, 0.22, 0.22, 4.9 + 1.85 * 0.8, 0.25, DARK, n=8, k=2)
        cyl(m, (s * 2.6, cy, 5.1), (cx, cy, 5.1), 0.75, DARK, n=12)


def build_waist(m):
    hw = pchip(WAI_Y, WAI_HW)
    ys = stations(WAI_Y[0], WAI_Y[-1], 0.3)
    loft(m, [ring(0, y, hw(y) - 0.1, 2.8, 5.75, n=16, p=2.6) for y in ys], WAIST)
    # two flex rings
    for y in (14.85, 15.55):
        loft(m, [ring(0, y + d, hw(y) + 0.05, 2.7, 5.95, n=16, p=2.6) for d in (-0.16, 0.16)], DARK)


def build_forebody(m, frame):
    hw, zt, zb = pchip(FB_Y, FB_HW), pchip(FB_Y, FB_ZT), pchip(FB_Y, FB_ZB)
    # Core (darker, a hair inside) so the plate seam reads as a real gap.
    ys = stations(FB_Y[0], FB_Y[-1], 0.8)
    loft(m, [ring(0, y, max(0.3, hw(y) - 0.3), zb(y) + 0.1, zt(y) - 0.3, n=14, p=2.8, pb=2.3) for y in ys], DARK)
    # Rear plate rows 15.6-20.3, front plate (glacis) 20.6-24.9.
    for a, b in ((15.6, 20.25), (20.6, FB_Y[-1])):
        ys = stations(a, b, 0.6) if a < 20 else [20.6, 21.2, 21.8, 22.4, 22.9, 23.4, 23.8, 24.15, 24.45, 24.7, 24.92]
        loft(m, [ring(0, y, hw(y), zb(y), zt(y), n=16, p=2.8, pb=2.3) for y in ys], HULL)
    # Dorsal armour strip with bolts over the rear plate (a raised plate, machined).
    hull(m, cbox(-1.3, 1.3, 16.0, 19.9, zt(17) - 0.6, zt(16.0) + 0.25, 0.25, z1b=zt(19.9) + 0.22), HULL)
    for y in (16.5, 19.4):
        for s in (-1, 1):
            dome(m, s * 0.85, y, 0.18, 0.18, zt(y) + 0.2, 0.2, DARK, n=8, k=2)
    # Nose grille: dark slats on the front face (seen by the tilted camera from the south).
    for i, z in enumerate((3.7, 4.15)):
        hull(m, cbox(-1.0 + 0.1 * i, 1.0 - 0.1 * i, 24.55 - 0.15 * i, 24.95 - 0.12 * i, z - 0.14, z + 0.14, 0.06), DARK)
    # Side strakes along the flanks under the vane pods: level (D163), closed, well off the ground.
    mirror(lambda s: hull(m, cbox(*_xs(s, 2.3, 3.0), 16.6, 22.3, 2.4, 3.4, 0.3), DARK))
    # Belly keel: a long rounded ventral pod from the collar to the nose, the craft's closed underside.
    ys = stations(6.0, 23.0, 0.85)
    kw = pchip([6.0, 7.0, 12.0, 18.0, 22.0, 23.0], [1.0, 2.2, 2.6, 2.4, 1.6, 0.7])
    kb = pchip([6.0, 8.0, 11.0, 19.0, 22.0, 23.0], [2.7, 1.9, 1.5, 1.5, 2.2, 2.9])   # rounded ends
    loft(m, [ring(0, y, kw(y), kb(y), 3.4, n=14, p=2.2) for y in ys], DARK)


def vane_pod(m, cx, y0, y1, hw, zb, zt, mat):
    """A level, rounded pod along y (both ends blunt-rounded in plan and profile)."""
    ys = stations(y0, y1, 0.3)
    rings = []
    for y in ys:
        t = (2 * y - y0 - y1) / (y1 - y0)
        k = max(0.25, (1 - abs(t) ** 3.0) ** (1 / 3.0))
        zc = (zb + zt) / 2
        h = (zt - zb) / 2 * (0.55 + 0.45 * k)
        rings.append(ring(cx, y, hw * k, zc - h, zc + h, n=14, p=2.6))
    loft(m, rings, mat)


def build_side_vanes(m, frame):
    """The flank pods (rows 17-21): level side vanes on short pylons, trimmed per frame. 123 extends
    the right one a row further, 127 the left, 125 flares both out (the sprite's stepping flanks)."""
    out = 0.8 if frame == 125 else 0.0
    stride = {123: (-0.35, 0.35), 125: (0.2, 0.2), 127: (0.35, -0.35)}[frame]  # (left, right): + = south
    for s, st in zip((-1, 1), stride):
        cx = s * (3.25 + out)
        cy = 19.0 + st
        if frame == 125:
            vane_pod(m, cx, 17.45, 20.6, 0.98, 2.6, 4.85, HULL)
            vane_pod(m, s * 3.3, 19.6, 21.75, 0.62, 2.7, 4.4, HULL)   # the vane's trailing tip, tucked in
        else:
            vane_pod(m, cx, cy - 2.05, cy + 2.05, 0.9, 2.6, 4.85, HULL)
        cyl(m, (s * 2.0, cy, 3.6), (cx, cy, 3.6), 0.55, DARK, n=8)


def build_frame(frame, mats, coll):
    m = Mesh()
    build_hood(m)
    build_collar(m)
    build_chest(m)
    build_shoulders(m, frame)
    build_waist(m)
    build_forebody(m, frame)
    build_side_vanes(m, frame)
    bm = m.bm
    # sprite px -> Blender units: X = (xr + AX) / 12, Y = (14 - y) / 12, Z = z / 12
    T = Matrix(((PX, 0, 0, AX * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=T, verts=bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f"{NAME}-{frame}")
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(f"{NAME}-{frame}", me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    return obj


def materials(sprite):
    out = []
    for i in range(len(MATS)):
        pal, met, rough, em = MATS[i]
        tag = f"{NAME}A_{i}"
        out.append(common.palette_material(sprite, pal, tag, metallic=met, roughness=rough, emission_strength=em))
    return out


# --- bake (AO + edge lift, roughness/metal), after usp_talon.bake_maps / newshe-155 ----------------

def bake_maps(obj, out_dir, prefix, textured, size=512, samples=64):
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
    except Exception as err:  # noqa: BLE001
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
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.02, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{prefix}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{prefix}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    b0 = next(n for n in me.materials[0].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for img, c in ((col_img, (*TINT, 1.0)),
                   (rm_img, (1.0, b0.inputs["Roughness"].default_value, b0.inputs["Metallic"].default_value, 1.0))):
        img.pixels.foreach_set([v for _ in range(img.size[0] * img.size[1]) for v in c])
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
        ao_l.inputs["Distance"].default_value = 0.14
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
                                       math_("MULTIPLY", edge, 0.15)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.12)))
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
        bpy.ops.object.bake(type="EMIT", margin=16, margin_type="EXTEND", use_clear=False)
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
    # per-object copies of the materials, so each frame wires its own maps
    for i in textured:
        m = mats[i].copy()
        me.materials[i] = m
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


# --- measure -----------------------------------------------------------------------------------

def measure(objs, sprite, sub=8):
    import sprite_mask as SM
    from mathutils.bvhtree import BVHTree
    res = {}
    W, H = 24, 28
    for frame, obj in objs.items():
        fr = next(f for f in sprite["frames"] if f["index"] == frame)
        pix = fr["pixels"]
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        bm.faces.ensure_lookup_table()
        tree = BVHTree.FromBMesh(bm)
        fmat = [f.material_index for f in bm.faces]
        top = [[False] * (W * sub) for _ in range(H * sub)]
        hz = [[None] * W for _ in range(H)]
        regions = {}
        for r in range(H):
            for c in range(W):
                counts = {}
                zs = []
                for j in range(sub):
                    for i in range(sub):
                        u, v = c + (i + 0.5) / sub, r + (j + 0.5) / sub
                        hit = tree.ray_cast(Vector(((u - 12) * PX, (14 - v) * PX, 5.0)), Vector((0, 0, -1)), 20.0)
                        if hit[0] is not None:
                            top[r * sub + j][c * sub + i] = True
                            counts[fmat[hit[2]]] = counts.get(fmat[hit[2]], 0) + 1
                            zs.append(hit[0].z / PX)
                if sum(counts.values()) >= sub * sub / 2 and pix[r][c] >= 0:
                    mi = max(counts, key=counts.get)
                    regions.setdefault(mi, []).append(pix[r][c])
                    hz[r][c] = round(sum(zs) / len(zs), 1)
        bm.free()
        idx, colors = SM.load(NAME, frame)
        mk = SM.masks(idx, colors)
        meas = SM.measure(mk, top)
        reg = {}
        for mi, vals in regions.items():
            pal = MATS[mi][0]
            trimmed = sorted(v for v in vals if v not in (1,) and v < 61) or sorted(vals)
            reg[f"{mi}:pal{pal}"] = {"n": len(vals), "median_trim": trimmed[len(trimmed) // 2],
                                    "pixels": sorted(vals)}
        res[frame] = {**meas, "regions": reg, "top": ["".join("#" if any(top[r * sub + j][c * sub + i]
                                                                         for j in range(sub) for i in range(sub)
                                                                         if True) and sum(top[r * sub + j][c * sub + i] for j in range(sub) for i in range(sub)) >= sub * sub / 2 else "."
                                                                  for c in range(W)) for r in range(H)]}
    return res


# --- renders ------------------------------------------------------------------------------------

def _camera(name, loc, look, ortho=None, lens=None, up_y=False):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens or 50
    cam = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(look) - Vector(loc)
    if up_y:
        cam.rotation_euler = (0, 0, 0)
    else:
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return cam


def _render(cam, path, w, h):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_all(objs, shells, out):
    out.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError as err:
        sc.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "EEVEE" in e)
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.5, 0.52, 0.58, 1)
    bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    sc.collection.objects.link(sun)
    sun.rotation_euler = Vector((-0.35, -0.5, 1.0)).normalized().to_track_quat("Z", "Y").to_euler()
    # ground plane for the game views
    gm = bpy.data.meshes.new("ground")
    gbm = bmesh.new()
    bmesh.ops.create_grid(gbm, x_segments=1, y_segments=1, size=3.0)
    gbm.to_mesh(gm)
    gbm.free()
    ground = bpy.data.objects.new("ground", gm)
    gmat = common.material("ground_mat", (0.13, 0.12, 0.1), roughness=0.9)
    gm.materials.append(gmat)
    sc.collection.objects.link(ground)
    C = Vector((AX * PX, 0.0, 0.3))
    views = {
        "top": ((C.x, 0, 10), (C.x, 0, 0), 2.6, None, True),
        "side": ((8, 0, C.z), (0, 0, C.z), 2.6, None, False),
        "front": ((C.x, -8, C.z), (C.x, 0, C.z), 2.6, None, False),
        "rear": ((C.x, 8, C.z), (C.x, 0, C.z), 2.6, None, False),
        "q_front": ((3.2, -3.8, 3.3), tuple(C), None, 55, False),
        "q_rear": ((-3.4, 3.4, 3.1), tuple(C), None, 55, False),
        "under": ((1.6, -2.4, -3.6), tuple(C), None, 50, False),
    }
    tilt = math.radians(15)
    dist = 9.0
    views["game"] = ((C.x, -dist * math.sin(tilt), dist * math.cos(tilt)), (C.x, 0, 0), None, 120, False)
    for frame, obj in objs.items():
        for f2, o2 in objs.items():
            o2.hide_render = f2 != frame
        for s in shells.values():
            s.hide_render = True
        for vn, (loc, look, ortho, lens, upy) in views.items():
            if frame != 123 and vn not in ("top", "game", "q_front"):
                continue
            ground.hide_render = vn not in ("game",)
            cam = _camera(f"c_{vn}", loc, look, ortho=ortho, lens=lens, up_y=upy)
            w, h = (480, 560) if vn in ("top", "game") else (560, 480)
            _render(cam, out / f"{vn}-{frame}.png", w, h)
        # small in-game-size game view (the size the model has on screen)
        ground.hide_render = False
        cam = _camera("c_small", views["game"][0], views["game"][1], lens=120)
        _render(cam, out / f"gamesmall-{frame}.png", 96, 112)
    print("rendered", out)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
    sprite = common.load_sprite(WT, NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    objs, shells = {}, {}
    fmt = "AUTO"
    for frame in FRAMES:
        mats = materials(sprite)
        obj = build_frame(frame, mats, coll)
        me = obj.data
        me.calc_loop_triangles()
        print(f"{obj.name}: {len(me.loop_triangles)} triangles")
        objs[frame] = obj
    # outline shells from the closed, unbaked copies (D51, D90/D118: sealed before anything else)
    for frame, obj in objs.items():
        sh = common.outline_shell(obj, coll, voxel=0.012, faces=1600, smooth=6, inside=0.004)
        sh.name = sh.data.name = f"{obj.name}_outline"
        shells[frame] = sh
    if "--no-bake" not in argv:
        bdir = HERE / "bake"
        bdir.mkdir(parents=True, exist_ok=True)
        for frame, obj in objs.items():
            for o in coll.objects:
                o.hide_render = o is not obj
            bake_maps(obj, bdir, f"drone123_{frame}", [i for i in MATS if i not in (LAMP, LAMP_S)])
        for o in coll.objects:
            o.hide_render = False
        fmt = "WEBP"
    for frame in FRAMES:
        common.frame_part(objs[frame], [frame])
        common.frame_part(shells[frame], [frame])
    export = [o for f in FRAMES for o in (objs[f], shells[f])]
    if "--out" in argv:
        glb = Path(opt("--out"))
        common.export_glb(export, glb, image_format=fmt)
        print("exported", glb, glb.stat().st_size)
    else:
        common.export_sprite_model(WT, export, "enemies/newshm-123", sprite["sprites"], image_format=fmt)
    if "--measure" in argv:
        res = measure(objs, sprite)
        Path(opt("--measure")).write_text(json.dumps(res, indent=1))
        for f, r in res.items():
            print("MEASURE", f, "iou_rule_grid", r["iou_rule_grid"], "iou_rule", r["iou_rule"],
                  {k: v["median_trim"] for k, v in r["regions"].items()})
    if "--render" in argv:
        render_all(objs, shells, Path(opt("--render")))


if __name__ == "__main__":
    main()
