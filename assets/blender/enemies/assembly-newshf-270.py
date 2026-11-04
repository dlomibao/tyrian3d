"""Brown machine body of the SAVARA ground boss (newshf.shp; assembly-newshf-270, the six middle
pieces): a hard-surface 3D version of its sprites built the way the player ships are
(usp_talon.py, DECISIONS D50-D53), its top-view edge on the INNER edge of the sprite's ink (D74).

Seen in levels 1.10, 1.29, 1.38, 2.2, 3.21, 4.16. Six 2x2 ground enemies make a 72 x 56 px body:

    newshf-165  newshf-234  newshf-167     lamp bulkhead: four hooded lamp housings and a dark
    newshf-270  newshf-272  newshf-274     recess with two grey rams (234); brown armour below

Read from the sprite (rear = sprite top, front = sprite bottom, toward the player):
- rows 1-13: four grey lamp housings (cols 1-11, 13-23 and mirrored), each a box with a deep
  window: a rounded hood across its rear (the lit crown, row 3), the lamp at the bottom of the
  window, a lip in front (rows 10-12); the outer housing's lip has a slot (col 6). Between the
  inner housings a sunken recess (cols 24-48) with two thin pipes each side and two grey rams lying
  fore-aft (cols 32-35, 37-40) with bright collars at row 13, their clevises out past the rear.
- rows 13-47: brown armour, a lit rim along its rear edge (row 13). Outboard a rounded shoulder
  (cols 1-4) rolling down and away (lit to row 20, dark after), a dark groove (cols 5-8), an inner
  strip (cols 9-11); then the tube panel (cols 13-23): two rails either side of a channel holding a
  pink tube with a glowing core (col 19), ending in a rounded pod nose (rows 47-55) leaning in.
- centre (cols 24-48): a stepped plate (a dark step rows 17-18, a lit ridge rows 19-20, a plate
  with key-pattern seams rows 21-28) whose front edge is the lintel of an open bay (rows 29-47)
  between two jambs; in the bay two U-shaped troughs (cols 32-35, 37-40) open to the front.
Lamp states (frames of 165 / 167; frame-tagged parts, D17):
  off 165/167 the grey roller hood back (its band rows 1-3), lens dark; dim 203/205, mid 241/243,
  bright 279/281 the hood rolled forward (band to rows 4 / 5-6), lens glowing (bigger and hotter);
  open 232/236 hood gone, the housing dark.
The lamp parts have their own (unbaked) palette materials: they carry no bake UVs, and a baked
material would sample one dark texel on them.

Build space: u = sprite column edge (0..72), v = row edge (0..56, rear -> front), z = up, sprite px.
Blender: X = (u - 36) / 12, Y = (28 - v) / 12, Z = z / 12 (the body centre, screen (154, 53), is
the origin, as the current model). Mirror: u -> 73 - u (pixel c <-> 72 - c).

Exports each piece with common.export_sprite_model to public/models/enemies/<piece>.glb (and its
src/render/spriteModels entry): the body piece, its outline shell (D51) and, on 165 / 167, the five
frame-tagged lamp parts.

Run: blender --background --python assets/blender/enemies/assembly-newshf-270.py -- [--no-bake]
     [--out review.glb]  (the whole assembly in one glb, pieces placed, for review)
     [--review DIR]  (top masks per lamp state, an id pass and the views for a sheet)
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, fillet, frange, hull, loft, pchip  # noqa: E402

NAME = "assembly-newshf-270"
ROOT = common.repo_root(__file__)
PIECES = ["newshf-165", "newshf-234", "newshf-167", "newshf-270", "newshf-272", "newshf-274"]
CX0, CY0 = 154, 53
PX = 1 / 12
MU = 73.0  # mirror: u -> MU - u

METAL = 0.3
TINT = (1.0, 1.0, 1.0)

# ---- materials: slot -> (palette index, metallic before METAL, roughness, emission) -------------
SLOTS = [
    ("DARK", 65, 0.5, 0.55, 0),     # base slab, groove, shoulder skirt, bay floor, pods' undersides
    ("NOSE", 66, 0.55, 0.45, 0),    # pod noses, tube channel, jambs, plate step
    ("STRIP", 67, 0.55, 0.42, 0),   # inner shoulder strip, key plate
    ("RIDGE", 68, 0.6, 0.38, 0),    # ridge, troughs, collars
    ("ARM", 69, 0.55, 0.4, 0),      # armour: shoulder cap, tube-panel rails
    ("TUBE", 71, 0.4, 0.3, 0.5),    # tube casing (a faint glow, the sprite's lit pink slot)
    ("RIM", 72, 0.6, 0.32, 0),      # lit rim along the armour's rear edge
    ("CORE", 79, 0.0, 0.4, 2.2),    # tube core (glows)
    ("WELL", 65, 0.3, 0.75, 0),      # trough wells
    ("BLACK", 1, 0.3, 0.7, 0),      # recess floor, lamp pits, slots (sprite median 1)
    ("G3", 3, 0.6, 0.45, 0),        # lip faces, ram barrels, rear wall
    ("G4", 4, 0.7, 0.36, 0),        # rams
    ("G5", 5, 0.7, 0.38, 0),        # housing walls
    ("G6", 6, 0.7, 0.34, 0),        # lip tops, collars, hoods
    ("G8", 8, 0.75, 0.3, 0),        # bright collar bands
    ("INK", 2, 0.2, 0.8, 0),        # thin dark pipes, divider slots
]
S = {name: i for i, (name, *_rest) in enumerate(SLOTS)}
DARK, NOSE, STRIP, RIDGE, ARM, TUBE, RIM, CORE, WELL, BLACK, G3, G4, G5, G6, G8, INK = range(len(SLOTS))
GLOWING = {CORE}

# Lamp states: name -> (frame of 165, frame of 167, hood drum centre v (None = gone), lens). lens:
# None (dark) or (glow index, core index, v centre, radius u, radius v). The dim glow is 113, the
# trimmed median of the dim frame's lamp pixels.
LAMP_STATES = {
    "off": (165, 167, 2.8, None),
    "dim": (203, 205, 3.55, (113, 116, 8.0, 2.7, 1.5)),
    "mid": (241, 243, 4.1, (115, 119, 8.6, 3.2, 1.9)),
    "bright": (279, 281, 4.1, (117, 123, 8.7, 3.5, 2.05)),
    "open": (232, 236, None, None),
}


def merged_sprite():
    data = common.load_sprite(ROOT, "newshf-270")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def materials(sprite, tag="nshf270"):
    mats = []
    for name, idx, met, rough, em in SLOTS:
        mats.append(common.palette_material(sprite, idx, f"{tag}_{name.lower()}", metallic=met * METAL,
                                            roughness=rough, emission_strength=em))
    return mats


# ---- plan (traced from the D74 inner mask, both sides averaged) -----------------------------------
# Left inner edge u by row centre (rows 1-46), stairs relaxed, pchip.
_ROWS_L = {**{r: 1.0 for r in range(1, 19)}, 19: 1.5, 20: 1.5, 21: 1.5, 22: 2, 23: 2, 24: 2, 25: 2, 26: 3,
           27: 3, 28: 3, 29: 4, 30: 4, 31: 5, 32: 5, 33: 6, 34: 6, 35: 7, 36: 8, 37: 9, 38: 10, 39: 11,
           40: 13, 41: 14, 42: 14, 43: 14, 44: 14, 45: 14, 46: 14}


def _relaxed(table, passes=2):
    keys = sorted(table)
    vals = [table[k] for k in keys]
    for _ in range(passes):
        vals = [vals[0]] + [(vals[i - 1] + 2 * vals[i] + vals[i + 1]) / 4 for i in range(1, len(vals) - 1)] + [vals[-1]]
    return [k + 0.5 for k in keys], vals


_v, _u = _relaxed(_ROWS_L, passes=1)
_UL = pchip(_v, _u)


def uL(v):
    """The left inner edge of the body (rows 1-47); 1.0 down the straight flank."""
    if v <= 18.5:
        return 1.0
    return min(max(_UL(v), 1.0), 14.0)


# The pod nose (rows 47-55): its outer edge; the inner edge is NOSE_IN.
NOSE_V = [46.5, 47.5, 48.5, 49.5, 50.5, 51.5, 52.5, 53.5, 54.5, 55.0]
NOSE_U = [14.0, 14.0, 14.0, 14.4, 14.7, 15.6, 16.6, 18.3, 20.4, 21.8]
noseU = pchip(NOSE_V, NOSE_U)
NOSE_IN = 23.15


# ---- generic geometry helpers -------------------------------------------------------------------

def rsec(uL_, uR_, zB, zTL, zTR=None, rTL=0.4, rTR=0.4, rB=0.2, kT=3, kB=1):
    """A section in (u, z): a quad with filleted corners (bottom chamfers, rounded top corners)."""
    zTR = zTL if zTR is None else zTR
    corners = [(uL_, zB), (uR_, zB), (uR_, zTR), (uL_, zTL)]
    pts = fillet(corners, [rB, rB, rTR, rTL], [kB, kB, kT, kT])
    return pts, ((uL_ + uR_) / 2, (zB + min(zTL, zTR)) / 2)


def vloft(part, vs, secf, mat, cap0=True, cap1=True):
    """A loft along v through secf(v) -> (pts (u, z), centre)."""
    loft(part, secf, vs, mat, cap0=cap0, cap1=cap1)


def extrude(part, poly, axis, a0, a1, mat):
    """Extrude a simple closed polygon (in the plane of the two other axes, in order: axis 0 -> (v, z),
    1 -> (u, z), 2 -> (u, v)) from a0 to a1 along `axis`. Side normals from the polygon's winding."""
    others = [i for i in range(3) if i != axis]
    area = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        area += x0 * y1 - x1 * y0
    ccw = area > 0

    def p3(pt, a):
        c = [0.0, 0.0, 0.0]
        c[others[0]], c[others[1]], c[axis] = pt[0], pt[1], a
        return c
    r0 = [part.v(p3(p, a0)) for p in poly]
    r1 = [part.v(p3(p, a1)) for p in poly]
    for i in range(n):
        j = (i + 1) % n
        dx, dy = poly[j][0] - poly[i][0], poly[j][1] - poly[i][1]
        nx, ny = (dy, -dx) if ccw else (-dy, dx)
        out = [0.0, 0.0, 0.0]
        out[others[0]], out[others[1]] = nx, ny
        part.f((r0[i], r0[j], r1[j], r1[i]), mat, out=tuple(out))
    o0 = [0.0, 0.0, 0.0]
    o0[axis] = -1.0 if a1 > a0 else 1.0
    part.f(r0, mat, out=tuple(o0))
    part.f(r1, mat, out=tuple(-c for c in o0))


def sweep(part, path, r, mat, sides=10, cap=True, rs=None):
    """A round tube along build-space points (radius r, or rs per point)."""
    pts = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        n1 = t.cross(up).normalized()
        n2 = t.cross(n1).normalized()
        rr = rs[i] if rs else r
        ring = [part.v(p + n1 * (rr * math.cos(2 * math.pi * k / sides)) + n2 * (rr * math.sin(2 * math.pi * k / sides)))
                for k in range(sides)]
        rings.append((ring, p))
    for (r0, c0), (r1, c1) in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            part.f((r0[k], r0[j], r1[j], r1[k]), mat, away=tuple(c0))
    if cap:
        part.f(rings[0][0], mat, out=tuple(pts[0] - pts[1]))
        part.f(rings[-1][0], mat, out=tuple(pts[-1] - pts[-2]))


def dome(part, c, axis, r, depth, mat, sides=12, rings=3, scale=(1.0, 1.0)):
    """A dome (half ellipsoid) on a disc of radius r at c, bulging `depth` along unit `axis`."""
    c, ax = Vector(c), Vector(axis).normalized()
    up = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    n1 = ax.cross(up).normalized()
    n2 = ax.cross(n1).normalized()
    loops = []
    for i in range(rings + 1):
        a = (math.pi / 2) * i / (rings + 1)
        rr, h = r * math.cos(a), depth * math.sin(a)
        loops.append([part.v(c + ax * h + n1 * (rr * scale[0] * math.cos(2 * math.pi * k / sides))
                             + n2 * (rr * scale[1] * math.sin(2 * math.pi * k / sides))) for k in range(sides)])
    tip = part.v(c + ax * depth)
    for l0, l1 in zip(loops, loops[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            part.f((l0[k], l0[j], l1[j], l1[k]), mat, away=tuple(c))
    for k in range(sides):
        j = (k + 1) % sides
        part.f((loops[-1][k], loops[-1][j], tip), mat, away=tuple(c))
    part.f(loops[0], mat, out=tuple(-ax))


def inset_poly(poly, d):
    """Offset a simple polygon inward by d (miter joins)."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    normals = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        ln = math.hypot(x1 - x0, y1 - y0) or 1e-9
        normals.append((sgn * -(y1 - y0) / ln, sgn * (x1 - x0) / ln))  # inward
    out = []
    for i in range(n):
        a, b = normals[i - 1], normals[i]
        mx, my = a[0] + b[0], a[1] + b[1]
        ln = math.hypot(mx, my) or 1e-9
        mx, my = mx / ln, my / ln
        cos_half = max(0.3, mx * b[0] + my * b[1])
        out.append((poly[i][0] + mx * d / cos_half, poly[i][1] + my * d / cos_half))
    return out


def cplate(part, poly, z0, z1, ch, mat):
    """A plate on plan polygon `poly` (u, v) from z0 to z1, its top edges chamfered by ch."""
    top = inset_poly(poly, ch)
    rings = [[part.v((x, y, z0)) for x, y in poly], [part.v((x, y, z1 - ch)) for x, y in poly],
             [part.v((x, y, z1)) for x, y in top]]
    n = len(poly)
    cx = sum(x for x, _ in poly) / n
    cy = sum(y for _, y in poly) / n
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    for r0, r1, zf in ((rings[0], rings[1], 0.0), (rings[1], rings[2], 1.0)):
        for i in range(n):
            j = (i + 1) % n
            (x0, y0), (x1, y1) = poly[i], poly[j]
            ln = math.hypot(x1 - x0, y1 - y0) or 1e-9
            out = (sgn * (y1 - y0) / ln, sgn * -(x1 - x0) / ln, zf)
            part.f((r0[i], r0[j], r1[j], r1[i]), mat, out=out)
    part.f(rings[0], mat, out=(0, 0, -1))
    part.f(rings[2], mat, out=(0, 0, 1))


def cyl_u(part, u0, u1, v, z, r, mat, sides=12):
    sweep(part, [(u0, v, z), (u1, v, z)], r, mat, sides=sides)


def mirror_part(part):
    """Orient, then add the mirror image (u -> MU - u) of everything in `part`."""
    part.orient()
    bm = part.bm
    ret = bmesh.ops.duplicate(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:])
    for g in ret["geom"]:
        if isinstance(g, bmesh.types.BMVert):
            g.co.x = MU - g.co.x
    bmesh.ops.reverse_faces(bm, faces=[g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)])


def finish(part, mats, coll, oriented=False):
    if not oriented:
        part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, -36 * PX), (0, -PX, 0, 28 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)  # the map is a reflection
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


# ---- heights (sprite px) -------------------------------------------------------------------------
BASE = 3.0       # nominal deck foot of the armour
SLAB = 1.4       # top of the base slab (under the recess and bay floors)
FOOT = 0.6       # bottom of the armour lofts (they stand on the slab)
HOUSE = 9.0      # lamp housing walls
LIP = 8.1        # lip top in front of each lamp window (row 10)
PIT = 5.2        # floor of each lamp window
RECESS = 2.4     # floor of the centre recess
BAY = 1.8        # floor of the bay
armZ = pchip([13.0, 22.0, 32.0, 40.0, 47.0], [8.1, 7.85, 7.4, 7.0, 6.6])        # tube-panel rails
stripZ = pchip([13.0, 22.0, 30.0, 36.0, 41.0], [8.0, 7.6, 7.0, 6.3, 5.6])       # inner shoulder strip
shZi = pchip([13.0, 18.0, 22.0, 26.0, 30.0, 32.0], [8.0, 7.8, 7.2, 6.2, 5.1, 4.6])  # shoulder, inner edge
shZo = pchip([13.0, 18.0, 22.0, 26.0, 30.0, 32.0], [6.6, 6.2, 5.4, 4.6, 3.9, 3.7])  # shoulder, outer edge


# ---- the body ------------------------------------------------------------------------------------

def build_body(coll, mats):
    L = Part("body_L", smooth_angle=34)   # left half, mirrored
    C = Part("body_C", smooth_angle=34)   # centre, symmetric by construction

    # Base slab: the whole plan (rows 1-47) and the pods (rows 47-55), low, closed underneath; the
    # bottom tucked in so a shadow line runs round the foot.
    def slab(v):
        a = uL(v) + 0.25
        return rsec(a, MU - a, 0.0, SLAB, rTL=0.3, rTR=0.3, rB=0.7, kT=1, kB=1)
    vloft(C, [1.2] + frange(1.6, 46.8, 1.5) + [47.0], slab, DARK)

    # ---------- lamp bulkhead (rows 1-13), left half ----------
    for k, u0 in enumerate((1.0, 13.0)):
        u1 = u0 + 10.85  # col 12 / 24 is a dark slot between housings
        # walls: outer (lit, col u0), inner; the rear wall with an access hatch
        hull(L, cbox(u0, u0 + 1.15, 1.0, 10.2, 0.0, HOUSE, 0.3), G5)
        hull(L, cbox(u1 - 1.15, u1, 1.0, 10.2, 0.0, HOUSE, 0.3), G5)
        hull(L, cbox(u0 + 1.0, u1 - 1.0, 1.0, 2.4, 0.0, HOUSE - 1.0, 0.25), G3)
        # the window's floor and its dark pit
        hull(L, cbox(u0 + 0.9, u1 - 0.9, 2.2, 10.4, 0.0, PIT, 0.15), BLACK)
        # the lip in front: a flat top (row 10) and a face sloping to the armour rim (rows 11-13)
        notch = (u0 + 5.0, u0 + 6.0) if k == 0 else None
        spans = [(u0, notch[0]), (notch[1], u1)] if notch else [(u0, u1)]
        for a, b in spans:
            hull(L, cbox(a, b, 10.0, 11.2, 0.0, LIP, 0.25), G6)
            pts = []
            for uu in (a + 0.12, b - 0.12):
                pts += [(uu, 11.0, 0.0), (uu, 11.0, LIP - 0.1), (uu, 13.1, 0.0), (uu, 13.1, LIP - 0.55)]
            pts += [(a, 11.2, 0.0), (b, 11.2, 0.0), (a, 11.2, LIP - 0.3), (b, 11.2, LIP - 0.3),
                    (a, 12.9, 0.0), (b, 12.9, 0.0), (a, 12.9, LIP - 0.75), (b, 12.9, LIP - 0.75)]
            hull(L, pts, G3)
        if notch:  # the slot in the outer lip: a dark gap down to the stalk
            hull(L, cbox(notch[0], notch[1], 10.0, 13.05, 0.0, PIT + 0.6, 0.1), BLACK)
        # louvres on the outer wall of the outer housing (side views)
        if k == 0:
            for i in range(4):
                v = 2.6 + 2.0 * i
                hull(L, cbox(u0 - 0.25, u0 + 0.2, v, v + 1.1, 2.0, 7.4, 0.08), G3)
        # bolts on the lip corners
        for uu in (u0 + 0.75, u1 - 0.75):
            hull(L, cbox(uu - 0.32, uu + 0.32, 10.25, 10.9, LIP - 0.1, LIP + 0.28, 0.12), G8)
        # hood hinge knuckles at the rear wall
        for uu in (u0 + 1.6, u1 - 1.6):
            cyl_u(L, uu - 0.5, uu + 0.5, 2.0, HOUSE - 1.05, 0.55, G6, sides=8)
        # rear face (seen from behind only): an access hatch with a lift handle, bolted
        hull(L, cbox(u0 + 2.0, u1 - 2.0, 0.7, 1.05, 1.2, 6.6, 0.15), G4)
        hull(L, cbox(u0 + 4.0, u1 - 4.0, 0.56, 0.8, 5.2, 5.8, 0.1), G6)
        for uu in (u0 + 2.6, u1 - 2.6):
            for zz in (1.8, 6.0):
                hull(L, cbox(uu - 0.25, uu + 0.25, 0.58, 0.8, zz - 0.25, zz + 0.25, 0.08), G6)
        # lamp stalk: from the lip slot back to under the lens
        hull(L, cbox(u0 + 5.1, u0 + 5.9, 8.4, 11.0, PIT - 0.2, PIT + 0.9, 0.15), G3)
    # divider slots between the housings (cols 12 and 24): a dark floor
    for a, b in ((11.8, 13.2), (23.8, 24.4)):
        hull(L, cbox(a, b, 1.0, 13.1, 0.0, BASE + 0.4, 0.1), BLACK)

    # ---------- centre recess (cols 24-48, rows 0-17) ----------
    hull(C, cbox(24.0, 49.0, 0.8, 17.2, 0.0, RECESS, 0.2), BLACK)
    # two thin pipes each side (cols 28, 30) and a bracket over them (row 2)
    for uc in (28.5, 30.5):
        sweep(L, [(uc, 1.2, RECESS + 0.45), (uc, 16.9, RECESS + 0.45)], 0.45, INK, sides=8)
    hull(L, cbox(25.6, 31.4, 1.9, 3.0, RECESS, RECESS + 1.2, 0.2), G3)
    for uc in (26.2, 27.0):
        sweep(L, [(uc, 4.0, RECESS + 0.35), (uc, 16.9, RECESS + 0.35)], 0.3, BLACK, sides=6)
    # the rams (cols 32-35): a rod sloping down into the body, a bright collar at row 13, the barrel
    # under the plate; a clevis and pin out past the rear wall (row 0)
    RC = 34.05
    sweep(L, [(RC, 0.9, 5.6), (RC, 12.2, 4.9)], 1.85, G4, sides=16)
    sweep(L, [(RC, 12.1, 4.9), (RC, 14.4, 4.85)], 2.05, G5, sides=16)
    sweep(L, [(RC, 14.3, 4.85), (RC, 18.0, 4.8)], 1.9, G3, sides=16)
    hull(L, cbox(RC - 1.5, RC + 1.5, 0.05, 1.6, 4.1, 7.1, 0.35), G4)  # clevis block
    cyl_u(L, RC - 1.7, RC + 1.7, 0.75, 5.6, 0.45, G6, sides=8)        # pin
    hull(L, cbox(RC - 1.2, RC + 1.2, 0.6, 2.2, RECESS, 4.4, 0.2), G3)   # its bracket on the floor

    # ---------- armour (rows 13-47), left half ----------
    # Lit rim along the armour's rear edge (row 13), over the shoulder and tube panel
    for a, b in ((1.05, 11.8), (13.1, 23.85)):
        vloft(L, [13.0, 14.15], lambda v, a=a, b=b: rsec(a, b, FOOT, 8.35, rTL=0.45, rTR=0.45, kT=2), RIM)

    # Outer shoulder (cols 1-4): rolls down outboard; its top lit to row 20.6, a seam, then the
    # darker skirt down to where the plan cuts it (row ~31)
    def shoulder(v):
        a, b = uL(v), 5.1
        if b - a < 0.35:
            a = b - 0.35
        zi, zo = shZi(v), shZo(v)
        return rsec(a, b, FOOT, zo, zi, rTL=min(2.2, (b - a) * 0.6), rTR=0.3, rB=0.2, kT=4)
    vloft(L, frange(14.15, 20.45, 0.8), shoulder, ARM)
    vloft(L, frange(20.75, 31.6, 0.7) + [32.0], shoulder, DARK)

    # The groove (cols 5-8): a recessed channel between shoulder and strip, its outboard wall the
    # shoulder; past row 31 the plan cuts across it.
    def groove(v):
        a = max(uL(v), 4.9)
        b = 9.25
        if b - a < 0.35:
            a = b - 0.35
        return rsec(a, b, FOOT, 4.5, rTL=0.25, rTR=0.1, kT=1)
    vloft(L, frange(14.15, 37.4, 1.0), groove, DARK)
    # the groove's ink line on its outer lip (col 5): a sharp drop
    # Inner strip (cols 9-11): a raised rail, sloping down to the front, its outer edge on the plan
    def strip(v):
        a = max(uL(v) + 0.05, 9.05)
        b = 11.8
        if b - a < 0.35:
            a = b - 0.35
        return rsec(a, b, FOOT, stripZ(v), rTL=0.55, rTR=0.25, kT=2)
    vloft(L, frange(14.15, 40.6, 0.9) + [41.0], strip, STRIP)

    # Tube panel (cols 13-23): outer rail (13-16), inner rail (22-23), a bridge over the channel's
    # rear end (rows 14-16), the channel floor, the tube.
    def rail_o(v):
        a = max(13.15, uL(v) + 0.05)
        return rsec(a, 17.0, FOOT, armZ(v), rTL=0.75, rTR=0.25, kT=3)
    vloft(L, frange(14.15, 29.6, 1.1), rail_o, ARM)
    vloft(L, frange(29.9, 46.6, 1.1), rail_o, ARM)   # a seam across the rail at row 29.75
    def rail_i(v):
        return rsec(21.6, 23.85, FOOT, armZ(v), rTL=0.45, rTR=0.3, kT=2)
    vloft(L, frange(14.15, 29.6, 1.1), rail_i, ARM)
    vloft(L, frange(29.9, 46.6, 1.1), rail_i, ARM)
    vloft(L, [14.15, 15.5, 16.85], lambda v: rsec(16.8, 21.8, FOOT, armZ(v) - 0.05, rTL=0.1, rTR=0.1, kT=1), ARM)
    vloft(L, [16.85, 18.0], lambda v: rsec(16.8, 21.8, FOOT, armZ(v) - 0.6, rTL=0.5, rTR=0.5, kT=2), NOSE)
    hull(L, cbox(16.9, 21.7, 16.8, 47.0, FOOT, 4.6, 0.15), NOSE)  # channel floor
    # the tube fills the channel (the sprite's pink slot, cols 18-21, rows 19-46) and rides up to
    # the rails' height; it ends at row 47, where the pod nose starts
    TV, TZ, TR = 19.45, 5.95, 1.95
    sweep(L, [(TV, 18.8, TZ), (TV, 46.1, TZ)], TR, TUBE, sides=18, cap=False)
    dome(L, (TV, 18.8, TZ), (0, -1, 0), TR, 1.0, TUBE, sides=18)
    dome(L, (TV, 46.1, TZ), (0, 1, 0), TR, 0.85, TUBE, sides=18)
    sweep(L, [(TV, 23.6, TZ + 1.5), (TV, 45.2, TZ + 1.5)], 0.62, CORE, sides=10, cap=False)
    dome(L, (TV, 23.6, TZ + 1.5), (0, -1, 0), 0.62, 0.7, CORE, sides=10, rings=2)
    dome(L, (TV, 45.2, TZ + 1.5), (0, 1, 0), 0.62, 0.5, CORE, sides=10, rings=2)
    for v in (19.3, 45.6):  # collars where the tube sits in its cradles
        sweep(L, [(TV, v - 0.4, TZ), (TV, v + 0.4, TZ)], TR + 0.18, RIDGE, sides=18)

    # Pod nose (rows 47-55) under the tube panel: tapering, leaning in, falling to the ground.
    noseZ = pchip([46.5, 48.0, 50.0, 52.0, 54.0, 55.0], [6.6, 6.3, 5.4, 4.1, 2.6, 1.6])
    def nose(v):
        a = noseU(v)
        b = NOSE_IN if v < 54.2 else NOSE_IN - (v - 54.2) * 0.6
        w = b - a
        return rsec(a, b, 0.0, noseZ(v), noseZ(v) - 0.3, rTL=min(2.4, w * 0.4), rTR=min(0.6, w * 0.2),
                    rB=0.5, kT=4)
    vloft(L, [46.4] + frange(47.0, 54.6, 0.6) + [54.85, 55.0], nose, NOSE)
    # its front: a dark intake slot on the face toward the player
    hull(L, cbox(16.6, 20.4, 51.0, 52.3, 1.4, 3.0, 0.2), DARK)

    # ---------- centre (cols 24-48) ----------
    # plate step (rows 17-19), ridge (19-21), key plate (21-29): the key plate's front edge is the
    # lintel over the bay
    hull(C, cbox(24.1, 48.9, 16.8, 19.1, 0.0, 5.8, 0.25), NOSE)
    vloft(C, [19.0, 19.5, 20.5, 21.1], lambda v: rsec(24.15, 48.85, 3.0, 7.6, rTL=0.5, rTR=0.5, kT=2), ARM)
    # key plate: tiles with modelled seams (the key-pattern lines, rows 21-28)
    KZ = 6.9
    hull(C, cbox(24.3, 48.7, 21.0, 29.4, 0.0, KZ - 0.35, 0.2), DARK)  # the plate's body under the tiles
    # per half (sprite rows 21-28): a small tile in the outer corner (an L seam: col 29 rows 22-25,
    # row 25 cols 25-28), a triangle by the axis cut off by the diagonal seam (cols 33-35, rows
    # 22-24), and the big L-shaped tile round them
    tiles_L = [
        [(24.4, 21.5), (29.2, 21.5), (29.2, 25.3), (24.4, 25.3)],
        [(33.35, 21.5), (36.2, 21.5), (36.2, 24.35)],
        [(29.65, 21.5), (32.75, 21.5), (36.2, 24.95), (36.2, 29.3), (24.4, 29.3), (24.4, 25.75), (29.65, 25.75)],
    ]
    for poly in tiles_L:
        for side in (poly, [(MU - x, y) for x, y in reversed(poly)]):
            cplate(C, side, KZ - 0.6, KZ, 0.22, STRIP)
    # lintel lip over the bay (row 29): the plate's front edge, overhanging
    hull(C, cbox(27.9, 45.1, 28.6, 29.9, 4.6, KZ - 0.1, 0.3), NOSE)
    # jambs (cols 25-27 and 45-47), their bay-side edges chamfered (lit)
    jambZ = pchip([29.0, 47.0], [6.5, 6.0])
    def jamb(v):
        return rsec(24.15, 28.2, 0.0, jambZ(v), rTL=0.25, rTR=0.75, kT=2)
    vloft(L, frange(29.4, 47.0, 2.0), jamb, NOSE)
    # the bay: floor, a back wall under the lintel, two U troughs open to the front
    hull(C, cbox(27.9, 45.1, 29.5, 47.0, 0.0, BAY, 0.15), DARK)
    for uc in (34.0, 39.0):
        trough(C, uc, 33.0, 44.2, BAY, RIDGE, WELL)
    # a centre pillar line between the troughs (col 36) and ramps in front of them (rows 44-47)
    hull(C, cbox(36.15, 36.85, 30.0, 46.9, 0.0, BAY + 0.6, 0.1), BLACK)

    mirror_part(L)
    objs = [finish(L, mats, coll, oriented=True), finish(C, mats, coll)]
    return objs


def trough(part, uc, v0, v1, z0, mat, well, hw=1.95, h=1.7, wall=0.65):
    """A U-shaped trough (a launch rail) on the floor at z0: a rounded rear end at v0, open at the
    front (v1); its rim `wall` thick, its well dark."""
    # the rim as a swept bar along a U path
    n = 8
    path = [(uc - hw + wall / 2, v1, z0 + h / 2)]
    path.append((uc - hw + wall / 2, v0 + hw, z0 + h / 2))
    for i in range(1, n):
        a = math.pi * (1 - i / n)
        path.append((uc + (hw - wall / 2) * math.cos(a), v0 + hw - (hw - wall / 2) * math.sin(a), z0 + h / 2))
    path.append((uc + hw - wall / 2, v0 + hw, z0 + h / 2))
    path.append((uc + hw - wall / 2, v1, z0 + h / 2))
    # a rounded-rect section bar: approximate with an elliptic tube (h tall, wall wide)
    pts = [Vector(p) for p in path]
    rings = []
    sides = 8
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(Vector((0, 0, 1))).normalized()
        ring = [part.v(p + side * (wall / 2 * math.cos(2 * math.pi * k / sides))
                       + Vector((0, 0, h / 2 * math.sin(2 * math.pi * k / sides)))) for k in range(sides)]
        rings.append((ring, p))
    for (r0, c0), (r1, c1) in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            part.f((r0[k], r0[j], r1[j], r1[k]), mat, away=tuple(c0))
    part.f(rings[0][0], mat, out=(0, 1, 0))
    part.f(rings[-1][0], mat, out=(0, 1, 0))
    # the well inside it
    hull(part, cbox(uc - hw + wall * 0.8, uc + hw - wall * 0.8, v0 + wall * 0.8, v1, z0 - 0.3, z0 + 0.15, 0.1), well)


# ---- lamp states ---------------------------------------------------------------------------------

def hood_drum(P, a, b, vc, r=2.05, rz=2.0, zc=HOUSE - 1.6, n=12):
    """A roll-top hood between the housing walls: a half drum (axis along u, flat base) from u=a to
    b, its ends chamfered, and two raised slats across it."""
    def prof(rr, rrz):
        base = zc - 0.6
        return ([(vc - rr, base), (vc + rr, base)]
                + [(vc + rr * math.cos(math.pi * i / n), zc + rrz * math.sin(math.pi * i / n)) for i in range(n + 1)])
    ch = 0.22
    extrude(P, prof(r, rz), 0, a + ch, b - ch, G6)
    extrude(P, prof(r - ch, rz - ch), 0, a, a + ch + 0.01, G6)
    extrude(P, prof(r - ch, rz - ch), 0, b - ch - 0.01, b, G6)
    for t in (0.3, 0.7):
        u = a + (b - a) * t
        path = [(u, vc + r * 1.03 * math.cos(math.pi * (1 - i / 10)), zc + rz * 1.03 * math.sin(math.pi * (1 - i / 10)))
                for i in range(11)]
        sweep(P, path, 0.17, G6, sides=6)


def build_lamps(coll, sprite, state):
    """The hood and lamp of the four housings for one lamp state, with their own palette materials
    (unbaked: these parts have no bake UVs)."""
    f165, f167, hood, lens = LAMP_STATES[state]
    smats = materials(sprite, tag="nshf270L")
    if lens:
        glow, core, lv, ru, rv = lens
        smats.append(common.palette_material(sprite, glow, f"nshf270_lamp_{state}", metallic=0.0, roughness=0.4,
                                             emission_strength=3.0))
        smats.append(common.palette_material(sprite, core, f"nshf270_lampcore_{state}", metallic=0.0,
                                             roughness=0.4, emission_strength=4.5))
        GL, GC = len(SLOTS), len(SLOTS) + 1
    P = Part(f"lamps_{state}", smooth_angle=40)
    for k, u0 in enumerate((1.0, 13.0)):
        u1 = u0 + 10.85
        a, b = u0 + 1.05, u1 - 1.05
        if hood is not None:
            # the light grey roller hood (the sprite's grey band: rows 1-3 off, down to row 6 lit)
            hood_drum(P, a, b, hood)
    # the lamp: a squat housing on the stalk, a lens tilted toward the front
        lc = (u0 + 5.5, lens[2] if lens else 7.4, PIT + 1.2)
        ax = Vector((0, math.sin(math.radians(35)), math.cos(math.radians(35))))
        sweep(P, [(lc[0], lc[1] - ax.y * 1.0, lc[2] - ax.z * 1.0), lc], 2.2, G3, sides=16)
        if lens:
            dome(P, lc, ax, min(ru, 2.1), 0.9, GL, sides=16, rings=3, scale=(ru / min(ru, 2.1), rv / 1.6))
            dome(P, Vector(lc) + ax * 0.15, ax, min(ru, 2.1) * 0.45, 1.05, GC, sides=12, rings=2,
                 scale=(ru / min(ru, 2.1), rv / 1.6))
        else:
            dome(P, lc, ax, 2.0, 0.7, BLACK, sides=16, rings=3, scale=(1.0, 0.9))
    mirror_part(P)
    obj = finish(P, smats, coll, oriented=True)
    return obj, [f165, f167]


# ---- review renders --------------------------------------------------------------------------------

def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if want.split("_")[-1] in e)


def camera(scene, name, loc, look, ortho=None, lens=50):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    data.clip_start, data.clip_end = 0.01, 100
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return cam


def render(scene, cam, path, w, h):
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)


def review(out_dir, body, lamp_objs, mats):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    keep = [body] + [o for o, _ in lamp_objs.values()]
    for o in scene.objects:
        if o.type == "MESH" and o not in keep:
            o.hide_render = True

    def show_state(st):
        for name, (o, _f) in lamp_objs.items():
            o.hide_render = name != st

    # 1. top masks per lamp state (workbench, flat, transparent), on the 72 x 56 grid, k = 10
    set_engine(scene, "BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "SINGLE"
    sh.single_color = (1, 1, 1)
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.render.film_transparent = True
    top = camera(scene, "top", (0, 0, 20), (0, 0, 0), ortho=6.0)
    top.rotation_euler = (0, 0, 0)
    for st in LAMP_STATES:
        show_state(st)
        render(scene, top, out / f"mask_{st}.png", 720, 560)
    # 2. id pass (state off): each material a flat id colour
    show_state("off")
    sh.color_type = "MATERIAL"
    saved = {}
    all_mats = {m for o in keep for m in o.data.materials}
    ids = {}
    for i, m in enumerate(sorted(all_mats, key=lambda m: m.name)):
        saved[m.name] = tuple(m.diffuse_color)
        c = ((i * 37 % 251 + 3) / 255, (i * 91 % 241 + 7) / 255, (i * 53 % 239 + 11) / 255)
        m.diffuse_color = (*c, 1)
        ids[m.name] = [round(255 * (12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055)) for x in c]
    scene.view_settings.view_transform = "Standard"
    render(scene, top, out / "id_off.png", 720, 560)
    import json
    (out / "ids.json").write_text(json.dumps(ids))
    for m in all_mats:
        m.diffuse_color = (*saved[m.name][:3], 1)
    # 3. beauty views (EEVEE), lamps 'mid'
    set_engine(scene, "BLENDER_EEVEE")
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.32, 0.34, 0.4, 1)
    bg.inputs[1].default_value = 0.8
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(40), math.radians(-25), math.radians(20))
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 1.5
    fill.rotation_euler = (math.radians(-55), math.radians(30), 0)
    scene.collection.objects.link(fill)
    D = 14
    views = {
        "top": ((0, 0, 20), (0, 0, 0), 6.6, (720, 600)),
        "side": ((-D, 0, 0.35), (0, 0, 0.35), 6.6, (720, 300)),
        "front": ((0, -D, 0.35), (0, 0, 0.35), 6.6, (720, 300)),
        "rear": ((0, D, 0.35), (0, 0, 0.35), 6.6, (720, 300)),
        "q34": ((-D * 0.55, -D * 0.6, D * 0.5), (0, 0, 0.2), 8.0, (720, 560)),
        "q34r": ((D * 0.55, D * 0.6, D * 0.5), (0, 0, 0.2), 8.0, (720, 560)),
        "game": ((0, -D * 0.53, D * 0.848), (0, 0, 0), 6.8, (720, 600)),
        "under": ((0, 0, -20), (0, 0, 0), 6.6, (720, 600)),
    }
    show_state("mid")
    for name, (loc, look, ortho, (w, h)) in views.items():
        cam = camera(scene, f"cam_{name}", loc, look, ortho=ortho)
        if name == "top":
            cam.rotation_euler = (0, 0, 0)
        if name == "under":
            cam.rotation_euler = (math.pi, 0, 0)
        render(scene, cam, out / f"view_{name}.png", w, h)
    # lamp states at the game camera, close on the left bulkhead
    for st in LAMP_STATES:
        show_state(st)
        cam = camera(scene, f"cam_lamp_{st}", (-2.0, 1.6 - D * 0.53, D * 0.848), (-2.0, 1.6, 0.4), ortho=2.3)
        render(scene, cam, out / f"lamp_{st}.png", 360, 220)
    show_state("off")


# ---- main ----------------------------------------------------------------------------------------

def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, tuple(i for i in range(len(SLOTS)) if i not in GLOWING)
    try:
        T.bake_maps(obj, out_dir, size=1024, samples=64)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "nshf270")


def split_open(obj, layout, coll, suffix):
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


def main():
    import tempfile
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    objs = build_body(coll, mats)
    body = T.join(objs, NAME)
    T.cull_hidden(body)
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    lamp_objs = {st: build_lamps(coll, sprite, st) for st in LAMP_STATES}
    ltris = {st: sum(len(p.vertices) - 2 for p in o.data.polygons) for st, (o, _f) in lamp_objs.items()}
    print(f"{NAME}: body {tris} triangles; lamps {ltris}")
    if "--review" in argv:
        review(argv[argv.index("--review") + 1], body, lamp_objs, mats)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake(body, tempfile.mkdtemp(prefix="nshf270_bake_"))
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(body, coll, voxel=0.02, faces=1700, smooth=10)
    shell.hide_render = True
    stris = sum(len(p.vertices) - 2 for p in shell.data.polygons)
    print(f"{NAME}: outline shell {stris} triangles")
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    body.modifiers.clear()
    pieces = common.split_assembly(body, layout, coll)
    shells = split_open(shell, layout, coll, "_outline")
    outline_mat = shell.data.materials[0]
    lamp_layout = [e for e in layout if e[0] in ("newshf-165", "newshf-167")]
    per_piece = {}
    for name in PIECES:
        p, s = pieces[name], shells[name]
        p.name = name
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        s.name = f"{name}_outline"
        s.data.shade_smooth()
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        s["tyrian_outline"] = True
        s.hide_render = True
        per_piece[name] = [p, s]
        print(f"{NAME}: piece {name}: {sum(len(q.vertices) - 2 for q in p.data.polygons)} triangles")
    for st, (o, frames) in lamp_objs.items():
        for name, part in common.split_assembly(o, lamp_layout, coll).items():
            if not part.data.polygons:
                continue
            part.name = f"{name}-lamps-{st}"
            common.frame_part(part, [frames[0] if name == "newshf-165" else frames[1]])
            per_piece[name].append(part)
        o.hide_render = True
    # The game export: one model per piece, at its centre (split_assembly), with every frame it covers.
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, per_piece[name], f"enemies/{name}", data["sprites"], image_format=fmt)
    if "--out" in argv:  # the whole assembly in one glb, each piece at its place, for review
        out = Path(argv[argv.index("--out") + 1])
        where = {name: (cx / 12, -cy / 12) for name, cx, cy in layout}
        objs_ = []
        for name in PIECES:
            for o in per_piece[name]:
                o.location = (*where[name], 0.0)
                objs_.append(o)
        common.export_glb(objs_, out, image_format=fmt)
        for o in objs_:
            o.location = (0.0, 0.0, 0.0)
        print(f"exported {out}")


if __name__ == "__main__":
    main()
