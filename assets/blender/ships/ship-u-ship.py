"""U-Ship (player ship, tyrian.shp#8 frame 271 and its banking frames 267-275), rebuilt from its own
frames (DECISIONS.md D228; the standard is the Talon's, D50-D53, D74, D90, D93).

What the sprite draws (reference/models/ship-u-ship/sprite.json, palette 5; columns and rows of the
24x28 block, the ship's centre line the middle of column 11):
- Two steel blades standing on edge, the U's arms: ONE colour pixel wide between their ink (columns 5
  and 17, rows 8-19) on the level frame, 2 px at half bank and 3 px at full bank, where the flank
  turned to the light is the top's grey (7-11) and the other flank is dark (2-5). Along the top: a
  barrel (index 9, rows 8-12), a bright lip (11/12, row 13), a dark collar (6/5, row 14), a receiver
  (10/11, rows 15-17), a second lip (12, row 18) and collar (6/4, row 19).
- A tan band joining them behind the pod, as slim as the blades (rows 20-21 in the arms' columns,
  one pixel a row down the 45 degree corners, row 24 along the bottom): bright on the left limb
  (25, 28, 28, 28), dark on the right (24, 20, 21, 22), a dark clamp (21) between two bright lips
  (28) in the middle of the bottom; in the banking frames it widens as the arms do, bright where a
  flank faces left (25-29) and dark where it faces right (20-22, 163-166): the same blade on edge,
  lit from the left.
- A small brass capsule hung between the arms (columns 9-13, rows 13-19; its nose 3 px wide in row
  13, its tail flat): dark glass over the nose (163 and 16, rows 13-15, all but the right column), a
  cream stripe down the left of the body (28/29, column 10), a dark one down the right (162/163,
  column 12), tan flanks (24). No orange anywhere.
- One strut a side in row 16 (4 beside the arm, 7 or 6 beside the pod); the ink round it, the arm
  and the pod runs together into two black blocks 1 x 3 px (columns 6 and 8, 14 and 16).

How it is built (plain bmesh; x = sprite column, y = sprite row, pixel edges, z up, all in sprite
px; Blender X = (x - 12) / 12, Y = (14 - y) / 12, Z = z / 12):
- One blade section for the whole U, 1.6 px wide and 2.6 px tall: a flat land 1 px wide (the
  sprite's colour pixel), steep dark shoulders 0.3 px a side (D74's rule 3: a thin part keeps half
  its sprite width; the land carries the tone, the shoulders the weight, so the bright line stays
  1 px at any view scale, with or without the game's ink), a short plumb flank and a keel that
  tapers inside the camera's rays, so the blade shows the same width anywhere on screen. Its depth
  is what the banking frames draw (2 and 3 px wide arms).
- Arms: the land cut along the sprite's tone bands, one pal_ material each, the dark collars sunk
  0.14 px and dark all the way round; a chamfered muzzle with a bore.
- Band: the same section swept round the U (corners filleted), the land in the sprite's indices
  per stretch: left limb, right limb, bottom, lips and clamp. The left/right difference is the
  sprite's light; the game's lights are too even to give it (measured: 1.14 to 1 on a face leaning
  53 degrees out, where the sprite has 2.1 to 1), so it is painted (D175's facet ramp).
- Flanks: the land's index where they face left, darker where they face right, as the banking
  frames draw them; the band's aft-facing flank brown over a dark keel.
- Pod: a lofted capsule (ogive nose, flat stern with a dark, unlit nozzle), cut along its meridians
  into the sprite's five columns: flank, cream stripe, centre, dark stripe, flank; glass over the
  nose rows; a dark belly.
- Links: a plate in the sprite's ink from arm to pod, 3 px long at each end and 1 px in the middle
  (the ink blocks, which D74's inner mask keeps), with the strut as a chamfered bar on it.
- Texture: no concept projection (maps.json says "bake": "model"). This script bakes its own two
  maps with Cycles: ambient occlusion with an edge lift (a colour multiplier, scaled per family so
  an up-facing part shows its palette index's own brightness under the game's lights, TINT) and
  roughness/metalness.
- Exported beside it: the outline shell (common.outline_shell, D51) and `tyrian_engines` (the
  menus' engine glow behind the pod; the model itself has no glow).
- Banking: the game rolls and shifts the model (BANK_ROLL, BANK_SHIFT: tools/bank_roll.py --fit, D93).

    Blender --background --factory-startup --python ship-u-ship.py -- [--out path.glb] [--no-bake] [--preview png]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "ship-u-ship"
MODEL = f"ships/{NAME}"
PX = 1 / 12
CX = 11.5  # the ship's centre line: the middle of column 11
ARM = 6.0  # the arms' centre lines, px either side of it (columns 5 and 17)

# Material slots: name, palette index, metalness, roughness, family (the bake's tint).
SPEC = [
    ("barrel", 9, 0.22, 0.36, "steel"),
    ("lip", 11, 0.22, 0.30, "steel"),
    ("collar", 5, 0.2, 0.46, "steel"),
    ("receiver", 10, 0.22, 0.34, "steel"),
    ("keel", 7, 0.15, 0.5, "steel"),
    ("muzzle", 3, 0.1, 0.7, "steel"),
    ("web", 32, 0.1, 0.6, "steel"),
    ("hub", 4, 0.2, 0.42, "steel"),
    ("band_l", 26, 0.16, 0.38, "brass"),
    ("band_r", 21, 0.16, 0.4, "brass"),
    ("band_low", 24, 0.16, 0.4, "brass"),
    ("band_lip", 27, 0.18, 0.34, "brass"),
    ("band_clamp", 20, 0.15, 0.46, "brass"),
    ("band_flank", 23, 0.15, 0.44, "brass"),
    ("band_keel", 21, 0.15, 0.5, "brass"),
    ("pod", 25, 0.17, 0.38, "brass"),
    ("pod_hi", 28, 0.2, 0.3, "brass"),
    ("pod_mid", 22, 0.17, 0.38, "brass"),
    ("pod_seam", 162, 0.1, 0.55, "brass"),
    ("glass", 163, 0.0, 0.05, "glass"),
]
SLOT = {s[0]: i for i, s in enumerate(SPEC)}
# Parts that share another part's material (same palette index and finish): one draw call fewer each.
for _part, _same in (("shoulder", "collar"), ("pylon", "keel"), ("band_shoulder", "band_clamp"), ("pod_belly", "band_keel"),
                     ("pod_stern", "band_keel"), ("nozzle", "pod_seam"), ("pod_nose", "band_flank")):
    SLOT[_part] = SLOT[_same]

# The baked colour map's scale and tint per family (D53). An up-facing matte part comes out about
# 1.25 times its palette colour's luma under the game's lights (D212 measured 1.2-1.3): the scale
# (0.66 linear) takes that back, so the land shows the sprite's index as the sprite does (measured in
# game, DECISIONS.md D228's table). The brass map is a touch cool: three's Neutral tone mapping takes
# most from the smallest channel and pushes lit tan to saturated bronze; the steel's a touch warm
# against the game's blue sky light.
TINT = {"brass": (0.65, 0.67, 0.72), "steel": (0.66, 0.64, 0.61), "glass": (1.0, 1.0, 1.0)}


def materials(sprite):
    out = []
    for name, index, metallic, roughness, _family in SPEC:
        rgb = common.srgb(*sprite["colors"][str(index)])
        out.append(common.material(f"pal_{index}_uship_{name}", rgb, metallic=metallic, roughness=roughness))
    return out


# --- mesh helpers (sprite px) ---------------------------------------------------------------------

class Mesh:
    """Vertices and faces in sprite px; each part is its own closed solid."""

    def __init__(self, name):
        self.name = name
        self.verts = []
        self.faces = []

    def add(self, pts):
        base = len(self.verts)
        self.verts += [(float(x), float(y), float(z)) for x, y, z in pts]
        return list(range(base, base + len(pts)))

    def face(self, ids, slot):
        self.faces.append((list(ids), SLOT[slot]))

    def loft(self, rings, mat, cap0=None, cap1=None):
        """Quads between consecutive rings (same point count); mat(i, j) names the slot of the quad
        between ring i and i + 1 on ring edge j. Caps are n-gons."""
        ids = [self.add(r) for r in rings]
        n = len(rings[0])
        for i in range(len(rings) - 1):
            for j in range(n):
                k = (j + 1) % n
                self.face((ids[i][j], ids[i][k], ids[i + 1][k], ids[i + 1][j]), mat(i, j))
        if cap0:
            self.face(ids[0][::-1], cap0)
        if cap1:
            self.face(ids[-1], cap1)
        return ids

    def prism(self, poly, z0, z1, top, side, c=0.0):
        """A plan polygon (x, y) from z0 up to z1; with c, the top is inset by c over a chamfer."""
        rings = [[(x, y, z0) for x, y in poly]]
        if c > 0:
            rings.append([(x, y, z1 - c) for x, y in poly])
            rings.append([(x, y, z1) for x, y in inset(poly, c)])
        else:
            rings.append([(x, y, z1) for x, y in poly])
        last = len(rings) - 2
        self.loft(rings, lambda i, j: top if (c > 0 and i == last) else side, cap0=side, cap1=top)


def inset(poly, d):
    """A plan polygon moved in by d (each vertex along its two edges' normals)."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    out = []
    for i in range(n):
        (x0, y0), (x1, y1), (x2, y2) = poly[i - 1], poly[i], poly[(i + 1) % n]
        a = math.hypot(x1 - x0, y1 - y0)
        b = math.hypot(x2 - x1, y2 - y1)
        n0 = (-(y1 - y0) / a * sgn, (x1 - x0) / a * sgn)
        n1 = (-(y2 - y1) / b * sgn, (x2 - x1) / b * sgn)
        k = 1 + n0[0] * n1[0] + n0[1] * n1[1]
        out.append((x1 + d * (n0[0] + n1[0]) / k, y1 + d * (n0[1] + n1[1]) / k))
    return out


def path_stations(pts, radius, step=15.0):
    """(point, unit tangent) along a plan polyline, its corners filleted with `radius` in `step`
    degree chords; collinear points stay as stations (material breaks)."""
    out = []
    n = len(pts)
    for i, p in enumerate(pts):
        if i == 0 or i == n - 1:
            q = pts[1] if i == 0 else pts[-2]
            d = (q[0] - p[0], q[1] - p[1]) if i == 0 else (p[0] - q[0], p[1] - q[1])
            m = math.hypot(*d)
            out.append((p, (d[0] / m, d[1] / m)))
            continue
        a, b = pts[i - 1], pts[i + 1]
        d0 = (p[0] - a[0], p[1] - a[1])
        d1 = (b[0] - p[0], b[1] - p[1])
        m0, m1 = math.hypot(*d0), math.hypot(*d1)
        d0 = (d0[0] / m0, d0[1] / m0)
        d1 = (d1[0] / m1, d1[1] / m1)
        turn = math.atan2(d0[0] * d1[1] - d0[1] * d1[0], d0[0] * d1[0] + d0[1] * d1[1])
        if abs(turn) < 1e-6:
            out.append((p, d0))
            continue
        t = radius * math.tan(abs(turn) / 2)
        s = 1 if turn > 0 else -1
        start = (p[0] - d0[0] * t, p[1] - d0[1] * t)
        centre = (start[0] - d0[1] * s * radius, start[1] + d0[0] * s * radius)
        k = max(1, round(abs(math.degrees(turn)) / step))
        a0 = math.atan2(start[1] - centre[1], start[0] - centre[0])
        for j in range(k + 1):
            ang = a0 + turn * j / k
            pt = (centre[0] + radius * math.cos(ang), centre[1] + radius * math.sin(ang))
            tan = (-math.sin(ang) * s, math.cos(ang) * s)
            out.append((pt, tan))
    return out


# --- arms: steel blades ---------------------------------------------------------------------------

ZT = 1.2        # the land's height over the roll axis (the model's origin plane)
LAND = 0.5      # half the land's width: the sprite's one colour pixel
RW = 0.8        # half the blade's width at its shoulders (1.6 px: D74's rule 3)
SHOULDER = 0.55  # the shoulders' drop below the land
RSIDE = 0.1     # the flanks run plumb down to here, then taper into the keel
RKEEL = -1.4
KEEL_W = 0.2
GROOVE = 0.14   # the dark collars' land sits this far down

# The land's tone bands: row from, row to, slot, sunk.
ARM_BANDS = [(8.0, 13.0, "barrel", False), (13.0, 14.0, "lip", False), (14.0, 15.0, "collar", True),
             (15.0, 18.0, "receiver", False), (18.0, 19.0, "lip", False), (19.0, 20.0, "collar", True)]
ARM_EDGES = ["land", "shoulder", "flank", "keel", "keel", "keel", "flank", "shoulder"]
FLANK_LIT = {"barrel": "receiver", "receiver": "lip", "lip": "lip"}


def arm_section(drop=0.0, k=1.0):
    zt = ZT - drop
    kz = 0.86 if k < 1 else 1.0
    return [(-LAND * k, zt), (LAND * k, zt), (RW * k, ZT - SHOULDER), (RW * k, RSIDE), (KEEL_W * k, RKEEL * kz),
            (-KEEL_W * k, RKEEL * kz), (-RW * k, RSIDE), (-RW * k, ZT - SHOULDER)]


def build_arm(sx):
    m = Mesh(f"uship_arm_{'l' if sx < 0 else 'r'}")
    xc = CX + sx * ARM

    def ring(y, drop=0.0, k=1.0):
        return [(xc + sx * u, y, z) for u, z in arm_section(drop, k)]
    # The muzzle: a chamfered tip with a dark bore.
    def bore(y):
        return [(xc + sx * u * 0.42, y, 0.3 + (z - 0.3) * 0.42) for u, z in arm_section()]
    rings = [bore(8.3), bore(7.62), ring(7.62, 0.08, 0.8), ring(7.9)]
    mats = ["muzzle", "muzzle", "barrel"]
    for y0, y1, slot, sunk in ARM_BANDS:
        d = GROOVE if sunk else 0.0
        if sunk:  # the step down into the collar
            rings.append(ring(y0, d))
            mats.append("collar")
        rings.append(ring(y1, d))
        mats.append(slot)
        if sunk and y1 < 20.0:  # and back up
            rings.append(ring(y1))
            mats.append("collar")
    def mat(i, j):
        edge = ARM_EDGES[j]
        if mats[i] == "collar" or mats[i] == "muzzle":  # a collar is dark all the way round
            return mats[i]
        if edge == "land":
            return mats[i]
        if j in (2, 3, 5, 6):
            # The tone bands run on down the flanks, as the banking frames draw them: the flank that
            # faces left (the sprite's light) a step lighter than the land, the one that faces right
            # the land's index on its plumb strip and the keel's dark below.
            faces_left = (j < 4) == (sx < 0)
            return FLANK_LIT[mats[i]] if faces_left else mats[i] if edge == "flank" else "keel"
        return edge
    m.loft(rings, mat, cap0="muzzle", cap1="keel")
    return m


# --- the band: the same blade, in brass, round the back of the U ----------------------------------

BAND_Y0 = 19.9
BAND_R = 1.2    # the corners' fillet radius on the centre line
BAND_YB = 24.5  # the bottom run's centre line (row 24)
BAND_EDGES = ["land", "shoulder", "flank", "keel", "keel", "keel", "flank", "shoulder"]


def build_band():
    m = Mesh("uship_band")
    xl, xr = CX - ARM, CX + ARM
    yb = BAND_YB
    pts = [(xl, BAND_Y0), (xl, 21.5), (xl + 3.0, yb), (10.0, yb), (11.0, yb), (12.0, yb), (13.0, yb), (xr - 3.0, yb),
           (xr, 21.5), (xr, BAND_Y0)]
    st = path_stations(pts, BAND_R)
    sec = arm_section()
    rings = [[(p[0] - t[1] * u, p[1] + t[0] * u, z) for u, z in sec] for p, t in st]

    def mat(i, j):
        edge = BAND_EDGES[j]
        (x0, y0), (x1, y1) = st[i][0], st[i + 1][0]
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        if j in (2, 3, 5, 6):
            # The banking frames draw the outer face bright where it faces left (25-29) and everything
            # else dark: the outer face that faces right (21) and the inside of both limbs (20-22,
            # 163-166). Where the outer face looks aft, a brown plumb strip over the dark keel.
            if j > 4:
                return "band_keel"
            ty = (st[i][1][1] + st[i + 1][1][1]) / 2  # the outer face's normal is (-ty, tx)
            return "band_lip" if ty > 0.5 else "band_keel" if ty < -0.5 or edge == "keel" else "band_flank"
        if edge != "land":
            return "band_" + edge
        if ym > yb - 0.02:  # the bottom run: clamp (column 11) between two lips (10, 12)
            if 11.0 < xm < 12.0:
                return "band_clamp"
            if 10.0 < xm < 13.0:
                return "band_lip"
            return "band_low"
        return "band_l" if xm < CX else "band_r"
    m.loft(rings, mat, cap0="band_keel", cap1="band_keel")
    return m


# --- the pod --------------------------------------------------------------------------------------

POD_ZC = 0.2     # its widest line's height
POD_W = 2.55     # half width (columns 9-13 and a hair)
POD_HT = 1.5     # crown above the widest line
POD_HB = 1.1     # belly below it
POD_Y0, POD_Y1 = 12.8, 20.35
POD_P = 2.3      # the section's superellipse power
S_TOP = [-1.0, -0.94, -0.8, -0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.8, 0.94, 1.0]
S_BOT = [0.85, 0.55, 0.2, -0.2, -0.55, -0.85]
POD_YS = [POD_Y0, 12.9, 13.05, 13.25, 13.5, 13.75, 14.0, 14.5, 15.0, 15.5, 16.0, 17.0, 18.0, 19.0, 19.8, 20.15, POD_Y1]
POD_STERN = 19.8  # the stern rounds off from here
GLASS_Y0, GLASS_Y1 = 13.25, 16.0


def pod_hw(y):
    if y < 15.0:
        t = (y - POD_Y0) / (15.0 - POD_Y0)
        return max(0.03, POD_W * (1 - (1 - t) ** 1.6) ** 0.85)
    if y > POD_STERN:
        return POD_W - 0.2 * ((y - POD_STERN) / (POD_Y1 - POD_STERN)) ** 2
    return POD_W


def pod_h(y):
    """Height factor along the pod: 0 at the nose tip, 1 over the body, rounded off at the stern."""
    if y < 15.75:
        t = (y - POD_Y0) / (15.75 - POD_Y0)
        return max(0.03, (1 - (1 - t) ** 2) ** 0.6)
    if y > POD_STERN:
        return 1 - 0.22 * ((y - POD_STERN) / (POD_Y1 - POD_STERN)) ** 2
    return 1.0


def pod_ring(y, k=1.0):
    hw, h = pod_hw(y) * k, pod_h(y) * k

    def f(s):
        return (1 - abs(s) ** POD_P) ** (1 / POD_P)
    top = [(CX + s * hw, y, POD_ZC + POD_HT * h * f(s)) for s in S_TOP]
    bot = [(CX + s * hw, y, POD_ZC - POD_HB * h * f(s)) for s in S_BOT]
    return top + bot


def build_pod():
    m = Mesh("uship_pod")
    rings = [pod_ring(y) for y in POD_YS]
    ntop = len(S_TOP) - 1
    # The sprite's five columns, as meridian strips: edges of S_TOP.
    col_of = [0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 4]
    n = len(POD_YS)

    def mat(i, j):
        if i == n - 1:  # the stern face
            return "pod_stern"
        if i == n:  # the nozzle's wall
            return "nozzle"
        if j >= ntop:
            return "pod_belly"
        y = (POD_YS[i] + POD_YS[i + 1]) / 2
        col = col_of[j]
        if y < GLASS_Y0:
            return "pod_nose"
        if y < GLASS_Y1:
            return "glass" if col < 4 else "pod"
        if y > 19.0:
            return ["pod", "pod_hi", "pod", "pod_stern", "pod"][col]
        return ["pod", "pod_hi", "pod_mid", "pod_seam", "pod"][col]
    # The stern: a flat face with a dark nozzle sunk into it.
    rings += [pod_ring(POD_Y1, 0.62), [(x, y - 0.4, z) for x, y, z in pod_ring(POD_Y1, 0.5)]]
    m.loft(rings, mat, cap0="pod_nose", cap1="nozzle")
    return m


# --- links: arm to pod ----------------------------------------------------------------------------

def build_link(sx):
    def X(d):  # d px inboard of the arm's centre line
        return CX + sx * (ARM - d)
    # The dark plate (the sprite's ink between arm, strut and pod): 3 px long at each end, 1 px in the middle.
    a0, a1, b0, b1 = 0.65, 1.45, 2.7, 3.6
    poly = [(X(a0), 15.1), (X(a1), 15.1), (X(a1), 16.05), (X(b0), 16.05), (X(b0), 15.1), (X(b1), 15.1), (X(b1), 17.9),
            (X(b0), 17.9), (X(b0), 16.95), (X(a1), 16.95), (X(a1), 17.9), (X(a0), 17.9)]
    side = "l" if sx < 0 else "r"
    m = Mesh(f"uship_link_{side}")
    m.prism(poly, -0.25, 0.32, "web", "web")
    parts = [m]
    # The strut: a chamfered bar on the plate, dark beside the arm (4), lighter toward the pod (7).
    for d0, d1, slot in ((0.75, 1.5, "hub"), (1.5, 2.55, "pylon")):
        box = [(X(d0), 16.12), (X(d1), 16.12), (X(d1), 16.88), (X(d0), 16.88)]
        b = Mesh(f"uship_{slot}_{side}")
        b.prism(box, 0.2, 0.72, slot, slot, c=0.12)
        parts.append(b)
    return parts


# --- to Blender -----------------------------------------------------------------------------------

def to_object(parts, mats, coll, smooth_angle=32.0):
    """Each part cleaned and oriented on its own, then all in one mesh: smooth shaded, edges sharper
    than `smooth_angle` marked sharp."""
    import numpy as np
    bm = bmesh.new()
    scratch = []
    for part in parts:
        pb = bmesh.new()
        vs = [pb.verts.new(((x - 12) * PX, (14 - y) * PX, z * PX)) for x, y, z in part.verts]
        for ids, slot in part.faces:
            try:
                f = pb.faces.new([vs[i] for i in ids])
            except ValueError:
                continue
            f.material_index = slot
        bmesh.ops.remove_doubles(pb, verts=pb.verts, dist=1e-6)
        bmesh.ops.dissolve_degenerate(pb, edges=pb.edges, dist=1e-6)
        bmesh.ops.recalc_face_normals(pb, faces=pb.faces)
        me = bpy.data.meshes.new(part.name)
        pb.to_mesh(me)
        pb.free()
        print(f"u-ship part {part.name}: {len(me.polygons)} faces, volume {_volume(me, np) * 12 ** 3:.2f} px3")
        bm.from_mesh(me)
        scratch.append(me)
    for f in bm.faces:
        f.smooth = True
    lim = math.radians(smooth_angle)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            e.smooth = e.calc_face_angle(0.0) < lim
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for s in scratch:
        bpy.data.meshes.remove(s)
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    return obj


def _volume(me, np):
    """Signed volume: positive when the part's normals point out."""
    me.calc_loop_triangles()
    co = np.array([v.co[:] for v in me.vertices])
    tri = np.array([t.vertices[:] for t in me.loop_triangles])
    if not len(tri):
        return 0.0
    a, b, c = co[tri[:, 0]], co[tri[:, 1]], co[tri[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6)


def build(coll, mats):
    parts = [build_arm(-1), build_arm(1), build_band(), build_pod()]
    for sx in (-1, 1):
        parts += build_link(sx)
    return to_object(parts, mats, coll)


# --- texture: baked occlusion and edge wear (no concept projection) ------------------------------

def bake_maps(obj, out_dir, size=1024, samples=96):
    """As usp_talon.bake_maps: UV (Smart UV Project) and bake a colour multiplier (occlusion at two
    scales plus a lift on bevelled edges, tinted per family) and a roughness/metalness map, then
    wire them in: Base Color = map x palette colour."""
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
        print("u-ship: no GPU bake", err)
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

    col_img = bpy.data.images.new("uship_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("uship_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(slot, m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        L = nt.links.new
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
                    L(v, n.inputs[k])
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
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = TINT[SPEC[slot][4]]
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                L(math_("MULTIPLY", v, tint[k]), comb.inputs[k])
            L(comb.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(i, m, mode) for i, m in enumerate(mats)}
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

    for i, m in enumerate(mats):
        if SPEC[i][4] == "glass":
            continue
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


# The game's roll at bank steps 1 and 2, degrees (spriteModels bank.roll, D93).
BANK_ROLL = [40, 60]
# ... and its sideways shift per frame, game px, hardest left bank to hardest right (bank.shift).
BANK_SHIFT = [-3.5, -1.0, 0.0, 1.0, 3.0]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, NAME)
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    obj = build(coll, mats)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"u-ship: {len(obj.data.polygons)} faces, {tris} triangles")
    # The menu backdrop's engine glow (src/ui/backdrop.ts): just behind the nozzle, glTF axes
    # (x, y up, z aft), orange (palette 121). The model itself carries no glow: the sprite has none.
    obj["tyrian_engines"] = {"color": "#ff8a2a", "at": [[round(-0.5 * PX, 4), round(POD_ZC * PX, 4),
                                                         round((POD_Y1 + 0.4 - 14) * PX, 4)]]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="uship_bake_"))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, faces=1500)
    print(f"u-ship: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(root, [obj, shell], MODEL, common.with_bank_roll(sprite["sprites"], BANK_ROLL, BANK_SHIFT),
                                   image_format=fmt)
    if "--preview" in argv:
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = root / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=level["size"])


if __name__ == "__main__":
    main()
