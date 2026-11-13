"""Design A for newshc-1 (newshc.shp frames 1-13): a steel deck hatch whose two leaves part and a
red glowing pod on two armoured legs rises out of the pit beneath.

blender -b --factory-startup -P assets/blender/enemies/newshc-1.py [-- --no-bake] [-- newshc-1-f2 ...]
(tools/build-models.sh assets/blender/enemies/newshc-1.py)

Exports (public/models/enemies/<stage>.glb and src/render/spriteModels/<stage>.json):
  newshc-1_A.glb     stage 1, frame 1: hatch shut, the two leaves meet on a raised diagonal seam
  newshc-1-f2_A.glb  frame 3: the leaves scissor open about a pin at the seam's south-east end;
                     the pod's brown dome shows in the wedge-shaped gap
  newshc-1-f3_A.glb  frames 5, 7: leaves gone, the pod half out of the dark pit, legs folded;
                     on 7 its vents start to glow (palette frames)
  newshc-1-f4_A.glb  frames 9, 11, 13: the pod up on braced legs; the pit is open (transparent in
                     the sprite, so no floor); the core slit and window band brighten per frame

Read of the sprite (24 x 28 px): a deck tile of plates (101) with dark grooves (98) between them,
a raised 1 px hatch coaming (105) round cols 2-20 / rows 3-24, the interior plates (102) with a
panel grid (cols 4, 10, 18; rows 8, 14, 20, 22), and in frame 1 a lit seam (106) running from the
north-west corner to the south-east corner. The pit (frames 5+) is a horseshoe: a well under the
pod (rows 6-15) and two leg channels (rows 16-22) either side of a deck tongue (cols 10-12).
The sprite's top row and right column are ink (the game draws its own outline, D74): the deck
stops at their inner edge.
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshc-1"
PX = 1 / 12
STAGES = {"newshc-1": [1], "newshc-1-f2": [3], "newshc-1-f3": [5, 7], "newshc-1-f4": [9, 11, 13]}

# --- heights (units) -------------------------------------------------------------------------------
SLAB = (0.0, 0.05)        # dark groove slab under every plate
OUT_TOP = 0.11            # outer deck plates
RIM_TOP = 0.15            # hatch coaming
INT_TOP = 0.10            # interior plates and hatch leaves
PLATE_Z0 = 0.045
GROOVE_W, GROOVE_D = 0.55, 0.026   # px, units
AXIS = 11.5               # pod and legs mirror about this pixel edge coordinate (col 11 centre)

# --- materials: (palette index, kwargs) by slot ------------------------------------------------------
SLOTS = [
    ("GROOVE", 98, dict(metallic=0.35, roughness=0.65)),
    ("DECK", 101, dict(metallic=0.45, roughness=0.42)),
    ("INNER", 102, dict(metallic=0.45, roughness=0.4)),
    ("RIM", 105, dict(metallic=0.55, roughness=0.32)),
    ("SEAM", 106, dict(metallic=0.6, roughness=0.3)),
    ("SUB", 104, dict(metallic=0.5, roughness=0.36)),
    ("WALL", 51, dict(metallic=0.3, roughness=0.6)),
    ("FLOOR", 2, dict(metallic=0.2, roughness=0.8)),
    ("LEG", 6, dict(metallic=0.45, roughness=0.48)),
    ("JOINT", 4, dict(metallic=0.5, roughness=0.45)),
    ("SHELL", 113, dict(metallic=0.35, roughness=0.36)),
    ("VENT", 121, dict(metallic=0.0, roughness=0.4, emission_strength=2.5)),
    ("CORE", 116, dict(metallic=0.0, roughness=0.35, emission_strength=3.0)),
    ("WINDOW", 114, dict(metallic=0.1, roughness=0.3, emission_strength=1.2)),
    ("FANG", 112, dict(metallic=0.4, roughness=0.4)),
    ("DOME", 166, dict(metallic=0.35, roughness=0.42)),
    ("TAN", 84, dict(metallic=0.3, roughness=0.45)),
    ("MAUVE", 168, dict(metallic=0.35, roughness=0.42)),
    ("RIB", 113, dict(metallic=0.35, roughness=0.36)),   # the shell's rib ridges (the shell's colour)
]
S = {name: i for i, (name, _, _) in enumerate(SLOTS)}

# Per-stage palette overrides (index) and per-frame palette animation (D17).
STAGE_PAL = {
    "newshc-1-f2": {"FLOOR": 4},
    "newshc-1-f3": {"SHELL": 163, "RIB": 163, "VENT": 69, "CORE": 69, "WINDOW": 165, "LEG": 103},
}
STAGE_ANIM = {
    # frame 7: the pod reddens and its vents light; the pit goes black
    # the folded legs are drawn in the deck's blue-grey on 5 (103), steel grey on 7
    "newshc-1-f3": {"SHELL": {7: 67}, "RIB": {7: 67}, "VENT": {7: 117}, "CORE": {7: 115}, "WINDOW": {7: 68},
                    "FLOOR": {7: 1}, "LEG": {7: 6}},
    # the core slit and the window band either side of it brighten 9 -> 11 -> 13
    "newshc-1-f4": {"CORE": {11: 124, 13: 127}, "WINDOW": {11: 117, 13: 125}, "SHELL": {13: 114},
                    "RIB": {13: 114}},
}
NO_EMIT_STAGES = {"newshc-1-f3": ("VENT", "CORE", "WINDOW")}


def materials(sprite, stage):
    pal = STAGE_PAL.get(stage, {})
    anim = STAGE_ANIM.get(stage, {})
    out = []
    for name, idx, kw in SLOTS:
        kw = dict(kw)
        if name in NO_EMIT_STAGES.get(stage, ()):
            kw["emission_strength"] = 0.6 if name == "VENT" else 0.0
        out.append(common.palette_material(sprite, pal.get(name, idx), f"{stage}_{name.lower()}",
                                           frames=anim.get(name), **kw))
    return out


# --- coordinates ---------------------------------------------------------------------------------------

def wx(u):
    return (u - 12) * PX


def wy(v):
    return (14 - v) * PX


def W(u, v, z=0.0):
    return Vector((wx(u), wy(v), z))


def to_world(poly):
    return [(wx(u), wy(v)) for u, v in poly]


def area(pts):
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                     for i in range(len(pts)))


def ccw(pts):
    return pts if area(pts) > 0 else pts[::-1]


def offset(pts, d):
    """Inward miter offset of a CCW polygon by d (units)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e1 = (p1 - p0).normalized()
        e2 = (p2 - p1).normalized()
        n1 = Vector((-e1.y, e1.x))
        n2 = Vector((-e2.y, e2.x))
        m = n1 + n2
        k = 1 + n1.dot(n2)
        if k < 0.2:
            k = 0.2
        q = p1 + m * (d / k)
        out.append((q.x, q.y))
    return out


def chamfer_corners(poly, r):
    """Cut every corner of a pixel-edge polygon by r px (45 degree chamfers on the steps)."""
    out = []
    n = len(poly)
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        a = (p0 - p1)
        b = (p2 - p1)
        ra = min(r, a.length * 0.45)
        rb = min(r, b.length * 0.45)
        q1 = p1 + a.normalized() * ra
        q2 = p1 + b.normalized() * rb
        out += [(q1.x, q1.y), (q2.x, q2.y)]
    return out


# --- mesh helpers ----------------------------------------------------------------------------------------

def tag(bm, faces, mat, smooth=False):
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def prism(bm, pts, z0, z1, ch, mat, smooth=False):
    """A prism over a world-xy polygon from z0 to z1, its top edge chamfered by ch (units)."""
    pts = ccw(list(pts))
    rings = [[bm.verts.new((x, y, z0)) for x, y in pts]]
    if ch > 0:
        rings.append([bm.verts.new((x, y, z1 - ch)) for x, y in pts])
        rings.append([bm.verts.new((x, y, z1)) for x, y in offset(pts, ch)])
    else:
        rings.append([bm.verts.new((x, y, z1)) for x, y in pts])
    faces = []
    n = len(pts)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    tag(bm, faces, mat, smooth)
    return faces


def ring_prism(bm, outer, inner, z0, z1, ch, mat):
    """A closed frame between two CCW world polygons with the same vertex count, both top edges
    chamfered."""
    outer, inner = ccw(outer), ccw(inner)
    n = len(outer)
    o0 = [bm.verts.new((x, y, z0)) for x, y in outer]
    o1 = [bm.verts.new((x, y, z1 - ch)) for x, y in outer]
    o2 = [bm.verts.new((x, y, z1)) for x, y in offset(outer, ch)]
    i2 = [bm.verts.new((x, y, z1)) for x, y in offset(inner, -ch)]
    i1 = [bm.verts.new((x, y, z1 - ch)) for x, y in inner]
    i0 = [bm.verts.new((x, y, z0)) for x, y in inner]
    loops = [o0, o1, o2, i2, i1, i0, o0]
    faces = []
    for a, b in zip(loops, loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    tag(bm, faces, mat)
    return faces


def rect(u0, v0, u1, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def sweep(bm, path, sides=8, mat=0, smooth=True, up=(0, 0, 1)):
    """A tube along (x, y, z, half_width, half_height) stations (units); zero size = a point.
    (Copied from lib_b097.sweep.)"""
    pts = [Vector((x, y, z)) for x, y, z, _, _ in path]
    upv = Vector(up)
    rings = []
    for i, (x, y, z, w, hh) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.normalize()
        side = t.cross(upv)
        if side.length < 1e-6:
            side = t.cross(Vector((0, 1, 0)))
        side.normalize()
        u = side.cross(t).normalized()
        if w == 0 and hh == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        rings.append([bm.verts.new(pts[i] + side * (w * math.cos(2 * math.pi * (k + 0.5) / sides)) +
                                   u * (hh * math.sin(2 * math.pi * (k + 0.5) / sides))) for k in range(sides)])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                faces.append(bm.faces.new((r0[0], r1[j], r1[k])))
            elif len(r1) == 1:
                faces.append(bm.faces.new((r0[k], r0[j], r1[0])))
            else:
                faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    if len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    tag(bm, faces, mat, smooth)
    return faces


def beam(bm, a, b, w0, w1, h0, h1, ch, mat, up=Vector((0, 0, 1))):
    """A chamfered box beam from point a to b: width w0 -> w1, height h0 -> h1 (units), chamfered
    edges (octagonal section)."""
    a, b = Vector(a), Vector(b)
    t = (b - a).normalized()
    s = t.cross(up)
    if s.length < 1e-6:
        s = t.cross(Vector((1, 0, 0)))
    s.normalize()
    u = s.cross(t).normalized()

    def section(p, w, h):
        c = min(ch, w * 0.4, h * 0.4)
        pts = [(w / 2 - c, h / 2), (w / 2, h / 2 - c), (w / 2, -h / 2 + c), (w / 2 - c, -h / 2),
               (-w / 2 + c, -h / 2), (-w / 2, -h / 2 + c), (-w / 2, h / 2 - c), (-w / 2 + c, h / 2)]
        return [bm.verts.new(p + s * x + u * y) for x, y in pts]
    r0 = section(a, w0, h0)
    r1 = section(b, w1, h1)
    faces = [bm.faces.new((r0[k], r0[(k + 1) % 8], r1[(k + 1) % 8], r1[k])) for k in range(8)]
    faces.append(bm.faces.new(list(reversed(r0))))
    faces.append(bm.faces.new(r1))
    tag(bm, faces, mat)
    return faces


def armour(bm, a, b, w0, w1, h0, h1, ch, mat, breaks=(), up=Vector((0, 0, 1))):
    """A machined armour beam from a to b: a crowned section (flat crown, bevelled shoulders, a
    V panel line down the crown's centre, vertical flanks, chamfered underside) lofted from
    w0 x h0 to w1 x h1; at each fraction t in `breaks` a transverse panel break (the crown dips
    and the flanks step in a hair, square shoulders either side). The plan width stays w at the
    flanks, so the top-view outline is that of a plain beam."""
    a, b = Vector(a), Vector(b)
    t = (b - a).normalized()
    s = t.cross(up)
    if s.length < 1e-6:
        s = t.cross(Vector((1, 0, 0)))
    s.normalize()
    u = s.cross(t).normalized()

    def section(f, sw=1.0, dz=0.0):
        p = a.lerp(b, f)
        w = (w0 + (w1 - w0) * f) * sw
        h = h0 + (h1 - h0) * f
        c = min(ch, w * 0.2, h * 0.3)
        d = 0.32 * h               # shoulder drop
        top = h / 2 - dz
        pts = [(0.06 * w, top), (0.0, top - 0.007), (-0.06 * w, top), (-0.27 * w, top),
               (-w / 2 + c, top - d), (-w / 2, top - d - c), (-w / 2, -h / 2 + c), (-w / 2 + c, -h / 2),
               (w / 2 - c, -h / 2), (w / 2, -h / 2 + c), (w / 2, top - d - c), (w / 2 - c, top - d),
               (0.27 * w, top)]
        return [bm.verts.new(p + s * x + u * y) for x, y in pts]
    L = (b - a).length
    g = min(0.012 / max(L, 1e-6), 0.08)
    stations = [(0.0, 1.0, 0.0)]
    for tb in sorted(breaks):
        stations += [(tb - g, 1.0, 0.0), (tb - g, 0.96, 0.012), (tb + g, 0.96, 0.012), (tb + g, 1.0, 0.0)]
    stations.append((1.0, 1.0, 0.0))
    rings = [section(f, sw, dz) for f, sw, dz in stations]
    n = len(rings[0])
    faces = []
    # consecutive rings: lofts along the beam, and the square step faces where two rings share a
    # station (the panel break's shoulders)
    for r0, r1 in zip(rings, rings[1:]):
        faces += [bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k])) for k in range(n)]
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    tag(bm, faces, mat)
    return faces


def cylinder(bm, c, axis, r, length, mat, segs=10):
    axis = Vector(axis).normalized()
    c = Vector(c)
    s = axis.cross(Vector((0, 0, 1)))
    if s.length < 1e-6:
        s = axis.cross(Vector((1, 0, 0)))
    s.normalize()
    u = axis.cross(s).normalized()
    a = c - axis * length / 2
    b = c + axis * length / 2
    ra = [bm.verts.new(a + (s * math.cos(2 * math.pi * k / segs) + u * math.sin(2 * math.pi * k / segs)) * r)
          for k in range(segs)]
    rb = [bm.verts.new(b + (s * math.cos(2 * math.pi * k / segs) + u * math.sin(2 * math.pi * k / segs)) * r)
          for k in range(segs)]
    faces = [bm.faces.new((ra[k], ra[(k + 1) % segs], rb[(k + 1) % segs], rb[k])) for k in range(segs)]
    faces.append(bm.faces.new(list(reversed(ra))))
    faces.append(bm.faces.new(rb))
    tag(bm, faces, mat, smooth=True)
    return faces


def to_object(name, bm, mats, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def apply_bool(obj, cutter, op="DIFFERENCE"):
    mod = obj.modifiers.new("b", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = cutter
    mod.use_self = True
    mod.use_hole_tolerant = True
    try:
        mod.material_mode = "INDEX"
    except Exception:
        pass
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    n = len(obj.data.materials)
    for p in obj.data.polygons:
        if p.material_index >= n:
            p.material_index = S["GROOVE"]


def cutter_obj(name, build, mats, coll):
    bm = bmesh.new()
    build(bm)
    o = to_object(name, bm, mats, coll)
    o.hide_render = True
    return o


# --- the deck ----------------------------------------------------------------------------------------------

# Footprint: the inner mask of the shut tile (the sprite's top row is ink except cols 11-17, and its
# right column is ink from row 5 down).
FOOT = [(0, 1), (11, 1), (11, 0), (18, 0), (18, 1), (24, 1), (24, 5), (23, 5), (23, 28), (0, 28)]

# Pit opening (pixel edges), traced from frame 9's transparent pixels plus the dark wall pixels
# round them (the sprite's ink ring there; D74 puts the edge on their inner side). The right
# channel's wall pixels in the coaming (col 20, rows 12-18) are left to the coaming.
PIT = [(8, 6), (15, 6), (15, 7), (16, 7), (16, 8), (17, 8), (17, 10), (20, 10), (20, 12), (21, 12), (21, 19),
       (20, 19), (20, 20), (19, 20), (19, 22), (18, 22), (18, 23), (15, 23), (15, 22), (14, 22), (14, 19), (13, 19),
       (13, 17), (10, 17), (10, 22),
       (9, 22), (9, 23), (6, 23), (6, 22), (5, 22), (5, 19), (3, 19), (3, 10), (6, 10), (6, 8),
       (7, 8), (7, 7), (8, 7)]

# Frames 5 and 7 (pod half out, legs folded): the pit is smaller. Its edge is the inner side of the
# sprite's 1 px dark ring (the game draws that ring as its outline): the well rows 7-14 cols 7-16,
# the channels cols 4-7 and 15-18 down to row 20, the deck tongue between them from row 15.5, and
# the coaming's east side (col 20) left whole.
PIT3 = [(8, 7), (15, 7), (15, 8), (16, 8), (16, 10), (17, 10), (17, 11), (19, 11), (19, 19), (18, 19), (18, 21),
        (14.6, 21), (14.6, 15.4), (8.4, 15.4), (8.4, 21), (5, 21), (5, 19), (4, 19), (4, 11), (7, 11), (7, 8),
        (8, 8)]


def pit_poly(stage):
    return PIT3 if stage == "newshc-1-f3" else PIT


# Groove centre lines (pixel-edge coords): outer deck, then the interior panel grid.
OUTER_GROOVES = [((4.5, -1), (4.5, 3)), ((10.5, -1), (10.5, 3)), ((18.5, -1), (18.5, 3)),
                 ((-1, 5.5), (2, 5.5)), ((-1, 20.5), (2, 20.5)),
                 ((10.5, 25.5), (10.5, 29)), ((18.5, 25.5), (18.5, 29))]
INNER_GROOVES = [((4.5, 4.6), (4.5, 20.5)), ((10.5, 3.5), (10.5, 8.5)), ((10.5, 14.5), (10.5, 24.5)),
                 ((18.5, 3.5), (18.5, 14.5)), ((9.5, 8.5), (18.5, 8.5)), ((4.5, 14.5), (10.5, 14.5)),
                 ((16.5, 14.5), (20.5, 14.5)), ((4.5, 20.5), (10.5, 20.5)), ((10.5, 22.5), (17.5, 22.5))]


def groove_cutters(bm, lines, top):
    for (u0, v0), (u1, v1) in lines:
        h = GROOVE_W / 2
        if abs(u1 - u0) < 1e-6:
            poly = rect(u0 - h, min(v0, v1) - h, u0 + h, max(v0, v1) + h)
        else:
            poly = rect(min(u0, u1) - h, v0 - h, max(u0, u1) + h, v0 + h)
        prism(bm, to_world(poly), top - GROOVE_D, top + 0.05, 0.0, S["GROOVE"])


def pit_cutter(bm, stage, z0=-0.05, z1=0.4):
    prism(bm, to_world(chamfer_corners(pit_poly(stage), 0.32)), z0, z1, 0.0, S["WALL"])


def build_deck(stage, mats, coll):
    pit = stage in ("newshc-1-f2", "newshc-1-f3", "newshc-1-f4")
    objs = []
    # slab (groove colour), its rim chamfered
    bm = bmesh.new()
    prism(bm, to_world(FOOT), SLAB[0], SLAB[1], 0.008, S["GROOVE"])
    objs.append(to_object(f"{stage}_slab", bm, mats, coll))
    # outer plates
    bm = bmesh.new()
    gap = GROOVE_W / 2
    top = [(0, 1), (11, 1), (11, 0), (18, 0), (18, 1), (24, 1), (24, 3 - 0.08), (0, 3 - 0.08)]
    prism(bm, to_world(top), PLATE_Z0, OUT_TOP, 0.014, S["DECK"])
    prism(bm, to_world(rect(0, 3, 2 - 0.08, 25.5 - gap)), PLATE_Z0, OUT_TOP, 0.014, S["DECK"])
    prism(bm, to_world([(21.5 + gap, 3), (24, 3), (24, 5), (23, 5), (23, 25.5 - gap), (21.5 + gap, 25.5 - gap)]),
          PLATE_Z0, OUT_TOP, 0.014, S["DECK"])
    prism(bm, to_world(rect(0, 25.5 + gap, 23, 28)), PLATE_Z0, OUT_TOP, 0.014, S["DECK"])
    # strip between the coaming and the right groove (col 21 is the groove itself) and below it
    prism(bm, to_world(rect(2 - 0.08, 25.0 + 0.04, 21.5 - gap, 25.5 - gap)), PLATE_Z0, OUT_TOP - 0.02, 0.006,
          S["DECK"])
    plates = to_object(f"{stage}_plates", bm, mats, coll)
    c = cutter_obj("gcut", lambda b: groove_cutters(b, OUTER_GROOVES, OUT_TOP), mats, coll)
    apply_bool(plates, c)
    bpy.data.objects.remove(c)
    objs.append(plates)
    # hatch coaming: a 1 px chamfered frame, bolts in its corners
    bm = bmesh.new()
    ring_prism(bm, to_world(rect(2, 3, 21, 25)), to_world(rect(3, 4, 20, 24)), PLATE_Z0, RIM_TOP, 0.022,
               S["RIM"])
    for u, v in ((2.5, 3.5), (20.5, 3.5), (2.5, 24.5), (20.5, 24.5)):
        cylinder(bm, W(u, v, RIM_TOP + 0.004), (0, 0, 1), 0.3 * PX, 0.012, S["SEAM"], segs=8)
    objs.append(to_object(f"{stage}_rim", bm, mats, coll))
    # interior
    if stage == "newshc-1" or stage == "newshc-1-f2":
        objs += build_leaves(stage, mats, coll, open_=stage == "newshc-1-f2")
    if pit:
        bm = bmesh.new()
        prism(bm, to_world(rect(3.02, 4.02, 19.98, 23.98)), PLATE_Z0, INT_TOP, 0.01, S["INNER"])
        interior_details(bm)
        inner = to_object(f"{stage}_inner", bm, mats, coll)
        c = cutter_obj("gcut", lambda b: groove_cutters(b, INNER_GROOVES, INT_TOP), mats, coll)
        apply_bool(inner, c)
        bpy.data.objects.remove(c)
        if stage != "newshc-1-f2":
            objs.append(inner)
        else:
            bpy.data.objects.remove(inner)
        c = cutter_obj("pcut", lambda b: pit_cutter(b, stage), mats, coll)
        for o in objs:
            if o.name.endswith(("_slab", "_inner")):
                apply_bool(o, c)
        bpy.data.objects.remove(c)
        if stage == "newshc-1-f4":
            # the leg slot in the coaming's east side (col 20, rows 12-18: the sprite's pit wall)
            c = cutter_obj("slot", lambda b: prism(b, to_world(rect(19.9, 12.0, 21.08, 19.0)), -0.05, 0.4, 0.0,
                                                   S["WALL"]), mats, coll)
            for o in objs:
                if o.name.endswith("_rim"):
                    apply_bool(o, c)
            bpy.data.objects.remove(c)
        if stage in ("newshc-1-f2", "newshc-1-f3"):
            bm = bmesh.new()
            prism(bm, to_world(offset_px(chamfer_corners(pit_poly(stage), 0.32), -0.15)), 0.0, 0.006, 0.0, S["FLOOR"])
            objs.append(to_object(f"{stage}_floor", bm, mats, coll))
    # groove ends notched through the tile's edge (sprite ink pixels (5,0), (20,0), (27,10), (27,18))
    def notches(b):
        for u0, v0, u1, v1 in ((-0.2, 5.0, 1.0, 6.0), (-0.2, 20.0, 1.0, 21.0), (10.0, 27.0, 11.0, 28.2),
                               (18.0, 27.0, 19.0, 28.2)):
            prism(b, to_world(rect(u0, v0, u1, v1)), -0.05, 0.4, 0.0, S["GROOVE"])
    c = cutter_obj("notch", notches, mats, coll)
    for o in objs:
        if o.name.endswith(("_slab", "_plates")):
            apply_bool(o, c)
    bpy.data.objects.remove(c)
    return objs


def offset_px(poly, d_px):
    """Offset a pixel-edge polygon outward by d_px (negative: inward... sign as given), in px."""
    w = ccw(to_world(poly))
    o = offset(w, -d_px * PX)
    return [(x / PX + 12, 14 - y / PX) for x, y in o]


def interior_details(bm):
    """Fine machined detail on the interior plates: the raised lit plate in the north-west panel,
    a louvred vent in the west panel (cols 5-9, rows 15-19) and the plate south-west."""
    prism(bm, to_world(rect(5.15, 4.35, 7.85, 7.75)), INT_TOP - 0.01, INT_TOP + 0.012, 0.008, S["SUB"])
    prism(bm, to_world(rect(4.95, 20.95, 9.85, 23.7)), INT_TOP - 0.01, INT_TOP + 0.008, 0.006, S["SUB"])
    for k in range(3):
        u = 5.6 + k * 1.6
        prism(bm, to_world(rect(u, 15.4, u + 0.9, 19.6)), INT_TOP - 0.01, INT_TOP + 0.007, 0.005, S["INNER"])


# --- hatch leaves (frames 1, 3) --------------------------------------------------------------------------

SEAM = [(3.3, 4.0), (5.0, 5.6), (6.0, 6.6), (7.5, 8.1), (9.0, 9.5), (10.6, 10.7), (11.9, 11.9),
        (12.6, 13.0), (12.9, 14.5), (13.7, 15.9), (15.1, 17.3), (16.6, 18.6), (18.2, 19.8),
        (19.3, 21.0), (20.0, 22.4)]
PIVOT = (19.6, 23.2)
LEAF_ANGLE = 0.0  # degrees (frame 3 no longer turns the leaves: see GAP)

# Frame 3's opening (pixel edges): the leaves stay shut on their pins and only their centre petals
# (the part over the pod) have dropped into the pit, so the gap is a compact lens on the seam's
# middle, cols 6-17 / rows 7-15, centred near (11.5, 10); both ends of the seam stay closed and lit
# (rows 3-6 north-west, rows 15-24 south-east), as the sprite draws them. Traced from frame 3's
# non-deck pixels (mauve 164-170 / tan 83-92 pod, dark 2-8 pit).
GAP = [(6.3, 7.0), (10.0, 6.8), (15.0, 6.9), (16.2, 7.8), (16.9, 9.6), (17.8, 10.6), (17.7, 11.9), (16.4, 12.9),
       (15.6, 14.1), (15.5, 15.6), (14.2, 15.3), (13.2, 14.9), (11.0, 14.9), (10.4, 13.4), (8.6, 13.4),
       (7.0, 13.0), (6.0, 12.0), (5.9, 9.5)]


def rot_uv(p, ang):
    a = math.radians(ang)
    du, dv = p[0] - PIVOT[0], p[1] - PIVOT[1]
    return (PIVOT[0] + du * math.cos(a) - dv * math.sin(a), PIVOT[1] + du * math.sin(a) + dv * math.cos(a))


def seam_strip(bm, path, sgn, d0, d1, z0, z1, ch):
    """A strip from d0 to d1 px off a uv polyline on side sgn (mitered at the bends), z0 to z1,
    chamfered by ch (units) on its outer top edge, square ends."""
    n = len(path)
    P = [Vector(p) for p in path]
    rings = []
    for i in range(n):
        if i == 0:
            t = (P[1] - P[0]).normalized()
            m, k = Vector((t.y, -t.x)), 1.0
        elif i == n - 1:
            t = (P[-1] - P[-2]).normalized()
            m, k = Vector((t.y, -t.x)), 1.0
        else:
            t0 = (P[i] - P[i - 1]).normalized()
            t1 = (P[i + 1] - P[i]).normalized()
            n0, n1 = Vector((t0.y, -t0.x)), Vector((t1.y, -t1.x))
            m = (n0 + n1).normalized()
            k = max(m.dot(n1), 0.5)
        m = m * sgn / k
        ch_px = ch / PX

        def at(d, z):
            q = P[i] + m * d
            return bm.verts.new(W(q.x, q.y, z))
        rings.append([at(d0, z0), at(d0, z1), at(d1 - ch_px, z1), at(d1, z1 - ch), at(d1, z0)])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(5):
            jj = (j + 1) % 5
            faces.append(bm.faces.new((r0[j], r0[jj], r1[jj], r1[j])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    tag(bm, faces, S["SEAM"])
    return faces


def build_leaves(stage, mats, coll, open_):
    """Two leaves split by the seam; each carries half the raised seam lip along its edge. Open:
    each turns 7.5 degrees about a pin at the seam's south-east end, clipped under the coaming."""
    ne = SEAM + [(20.0, 4.0)]
    sw = SEAM + [(20.0, 24.0), (3.0, 24.0), (3.0, 4.0)]
    out = []
    for leaf, poly, sgn in (("ne", ne, 1), ("sw", sw, -1)):
        bm = bmesh.new()
        prism(bm, to_world(poly), PLATE_Z0, INT_TOP, 0.006, S["INNER"])
        o = to_object(f"{stage}_leaf_{leaf}", bm, mats, coll)
        c = cutter_obj("gcut", lambda b: groove_cutters(b, INNER_GROOVES, INT_TOP), mats, coll)
        apply_bool(o, c)
        bpy.data.objects.remove(c)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        # half of the seam lip on this leaf's edge: a hard raised strip along the seam, its outer
        # top edge chamfered, its inner face square to its twin on the other leaf, square ends
        seam_strip(bm, SEAM[1:-1], sgn, 0.05, 0.55, INT_TOP - 0.006, INT_TOP + 0.016, 0.007)
        if leaf == "sw":
            interior_details(bm)
        bm.to_mesh(o.data)
        bm.free()
        if open_:
            # the centre petals have dropped: cut the lens out of both leaves (seam lip included)
            c = cutter_obj("gap", lambda b: prism(b, to_world(GAP), -0.05, 0.4, 0.0, S["INNER"]), mats, coll)
            apply_bool(o, c)
            bpy.data.objects.remove(c)
        if open_ and LEAF_ANGLE:
            ang = LEAF_ANGLE * sgn
            for vtx in o.data.vertices:
                u, v = vtx.co.x / PX + 12, 14 - vtx.co.y / PX
                u, v = rot_uv((u, v), ang)
                vtx.co.x, vtx.co.y = wx(u), wy(v)
            bm = bmesh.new()
            bm.from_mesh(o.data)
            for co, no in (((wx(2.9), 0, 0), (-1, 0, 0)), ((wx(20.1), 0, 0), (1, 0, 0)),
                           ((0, wy(3.9), 0), (0, 1, 0)), ((0, wy(24.1), 0), (0, -1, 0))):
                geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
                res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
                edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
                if edges:
                    bmesh.ops.holes_fill(bm, edges=edges, sides=0)
            bm.to_mesh(o.data)
            bm.free()
        out.append(o)
    return out


def build_petals(bm):
    """The two centre petals of the open hatch (frame 3), hinged under the gap's rim and hanging
    almost straight down into the pit, so from above they read only as the gap's dark wall."""
    for a, b in (((7.0, 7.0), (15.6, 7.3)), ((8.0, 13.4), (14.6, 15.2))):
        d = Vector((b[0] - a[0], b[1] - a[1]))
        n = Vector((d.y, -d.x)).normalized() * (-1 if a[1] < 10 else 1)   # into the gap (uv)
        p0, p1 = W(*a, PLATE_Z0), W(*b, PLATE_Z0)
        drop = Vector((n.x * 0.35 * PX, -n.y * 0.35 * PX, -0.17))
        q = [p0, p1, p1 + drop, p0 + drop]
        th = Vector((-n.x, n.y, 0)) * 0.012
        vs = [bm.verts.new(v) for v in q] + [bm.verts.new(v + th) for v in q]
        faces = [bm.faces.new(vs[:4]), bm.faces.new(vs[4:][::-1])]
        for i in range(4):
            j = (i + 1) % 4
            faces.append(bm.faces.new((vs[i], vs[i + 4], vs[j + 4], vs[j])))
        tag(bm, faces, S["INNER"])


# --- the pod -------------------------------------------------------------------------------------------------

POD = dict(cu=11.25, cv=9.55, a=4.1, b=2.03, np=3.4, ns=2.2, h=0.25, taper=0.16)


def pod_plan(rho, th):
    a, b, n = POD["a"], POD["b"], POD["np"]
    c, s = math.cos(th), math.sin(th)
    x = a * rho * math.copysign(abs(c) ** (2 / n), c)
    y = b * rho * math.copysign(abs(s) ** (2 / n), s)
    x *= 1 - POD["taper"] * max(0.0, y / b)   # narrower to the south (row 11 is cols 8-12)
    return POD["cu"] + x, POD["cv"] + y   # pixel coords (u, v)


def pod_rho(u, v):
    n = POD["np"]
    t = 1 - POD["taper"] * max(0.0, (v - POD["cv"]) / POD["b"])
    return ((abs(u - POD["cu"]) / (POD["a"] * t)) ** n + (abs(v - POD["cv"]) / POD["b"]) ** n) ** (1 / n)


def dome_z(u, v, z0):
    r = min(pod_rho(u, v), 1.0)
    ns = POD["ns"]
    return z0 + POD["h"] * (1 - r ** ns) ** (1 / ns)


def build_pod(bm, z0, raised):
    """Superelliptic carapace (plan from the sprite, rows 7.3-11.6, cols 7.4-15.5), a short
    vertical band, a tucked belly; N-S inlays: two vent slits (cols 8 and 14), a window band
    (cols 10-12) with the core slit (col 11) on it; a dark steel collar; three mandibles hanging
    off the south face (cols 7-8, 10-12, 14-15, rows 11-14)."""
    NT, NR = 40, 9
    rings = []
    for k in range(1, NR + 1):
        rho = math.sin(0.5 * math.pi * k / NR)
        ring = []
        for j in range(NT):
            th = 2 * math.pi * j / NT
            u, v = pod_plan(rho, th)
            ring.append(bm.verts.new(W(u, v, dome_z(u, v, z0) if k < NR else z0)))
        rings.append(ring)
    top = bm.verts.new(W(POD["cu"], POD["cv"], z0 + POD["h"]))
    faces = []
    for j in range(NT):
        faces.append(bm.faces.new((top, rings[0][j], rings[0][(j + 1) % NT])))
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(NT):
            faces.append(bm.faces.new((r0[j], r1[j], r1[(j + 1) % NT], r0[(j + 1) % NT])))
    # band and belly
    band = []
    for j in range(NT):
        u, v = pod_plan(1.0, 2 * math.pi * j / NT)
        band.append(bm.verts.new(W(u, v, z0 - 0.025)))
    belly = []
    for j in range(NT):
        u, v = pod_plan(0.78, 2 * math.pi * j / NT)
        belly.append(bm.verts.new(W(u, v, z0 - 0.09)))
    for r0, r1 in ((rings[-1], band), (band, belly)):
        for j in range(NT):
            faces.append(bm.faces.new((r0[j], r1[j], r1[(j + 1) % NT], r0[(j + 1) % NT])))
    faces.append(bm.faces.new(list(reversed(belly))))
    tag(bm, faces, S["SHELL"], smooth=True)
    # collar: a dark steel ring just under the band (its lower edge); a closed band whose inner
    # wall sits inside the shell, so the underside has no open edges
    coll = []
    for rho, z in ((1.005, z0 - 0.022), (0.93, z0 - 0.065), (0.80, z0 - 0.065), (0.80, z0 - 0.022)):
        coll.append([bm.verts.new(W(*pod_plan(rho, 2 * math.pi * j / NT), z)) for j in range(NT)])
    cf = []
    for k in range(4):
        r0, r1 = coll[k], coll[(k + 1) % 4]
        for j in range(NT):
            jj = (j + 1) % NT
            cf.append(bm.faces.new((r0[j], r1[j], r1[jj], r0[jj])))
    tag(bm, cf, S["JOINT"], smooth=True)
    # inlays
    # the side lights: 1 px strips at cols 8 and 14, run nearly the pod's full N-S depth (the
    # sprite's lit columns are 5 px tall); the window band cols 10-12 (3 px) with the core (col 11)
    inlay(bm, z0, 8.5, 0.5, 0.012, "VENT", rmax=0.98, dv=0.2, centre_only=True)
    inlay(bm, z0, 14.5, 0.5, 0.012, "VENT", rmax=0.98, dv=0.2, centre_only=True)
    inlay(bm, z0, 11.5, 1.55, 0.01, "WINDOW", rmax=0.97)
    inlay(bm, z0, 11.5, 0.5, 0.016, "CORE", rmax=0.97)
    # rib ridges between the plates (cols 9.6 and 13.4): low sharp ridges in the shell colour
    inlay(bm, z0, 9.65, 0.18, 0.01, "RIB")
    inlay(bm, z0, 13.35, 0.18, 0.01, "RIB")
    # mandibles
    for cu, w, v1, zt in ((8.3, 0.32, 12.7, 0.0), (11.5, 0.6, 12.9, 0.02), (14.5, 0.32, 12.7, 0.0)):
        x = wx(cu)
        zz = z0 - 0.02
        pts = [(x, wy(10.9), zz + 0.05, w * PX, 0.035), (x, wy(11.9), zz + 0.0, w * PX, 0.04),
               (x, wy(12.9), zz - 0.05 + zt, w * 0.75 * PX, 0.03), (x, wy(v1), zz - 0.10 + zt * 2, 0.0, 0.0)]
        sweep(bm, pts, sides=6, mat=S["FANG"], smooth=False)


def inlay(bm, z0, cu, hw, lift, matname, rmax=0.95, dv=0.25, centre_only=False):
    """A strip lying on the carapace along N-S at column cu, half width hw px, standing `lift`
    proud of the surface, closed underneath (sunk 0.02 into the shell)."""
    us = [cu - hw, cu, cu + hw]
    vs = []
    v = POD["cv"] - POD["b"]
    while v <= POD["cv"] + POD["b"]:
        vs.append(v)
        v += dv
    vs = [v for v in vs if all(pod_rho(u, v) < rmax for u in (us if centre_only is False else [cu]))]
    if len(vs) < 2:
        return
    tops = [[bm.verts.new(W(u, v, dome_z(u, v, z0) + lift)) for u in us] for v in vs]
    bots = [[bm.verts.new(W(u, v, dome_z(u, v, z0) - 0.02)) for u in us] for v in vs]
    faces = []
    for i in range(len(vs) - 1):
        for k in range(len(us) - 1):
            faces.append(bm.faces.new((tops[i][k], tops[i][k + 1], tops[i + 1][k + 1], tops[i + 1][k])))
            faces.append(bm.faces.new((bots[i][k], bots[i + 1][k], bots[i + 1][k + 1], bots[i][k + 1])))
        faces.append(bm.faces.new((tops[i][0], tops[i + 1][0], bots[i + 1][0], bots[i][0])))
        faces.append(bm.faces.new((tops[i][-1], bots[i][-1], bots[i + 1][-1], tops[i + 1][-1])))
    for row_t, row_b, rev in ((tops[0], bots[0], False), (tops[-1], bots[-1], True)):
        loop = row_t + row_b[::-1]
        faces.append(bm.faces.new(loop[::-1] if rev else loop))
    tag(bm, faces, S[matname], smooth=False)


# --- legs ------------------------------------------------------------------------------------------------------

def build_legs(bm, z0, raised):
    """Two armoured legs in the pit's channels (mirror about AXIS). Left leg, pixel plan: hip and
    upper strut cols 4-5 rows 11-13, the wide knee housing cols 4-7 rows 14-17, the shin cols 6-7
    rows 18-20; the foot pinned to the channel's south wall. A thin link from the hip to the pod
    flank (under 0.5 px wide at col 6, so the plan reads as the sprite's gap)."""
    lift = 1.0 if raised else 0.62
    for side in (-1, 1):
        def P(u, v, z):
            return W(AXIS + side * (u - AXIS), v, z)
        hip = P(4.8, 11.3, 0.24 * lift + 0.02)
        knee = P(5.55, 14.6, 0.31 * lift + 0.02)
        ankle = P(6.55, 18.9, 0.13 * lift + 0.02)
        foot = P(6.7, 20.6, 0.03)
        # upper strut (femur)
        armour(bm, hip, knee, 1.6 * PX, 2.0 * PX, 0.07, 0.08, 0.012, S["LEG"], breaks=(0.55,))
        # knee housing: the wide armour plate over the knee and upper shin, two plates
        armour(bm, P(5.8, 14.55, 0.33 * lift + 0.02), P(6.0, 18.25, 0.19 * lift + 0.02), 3.4 * PX, 3.2 * PX, 0.08,
               0.06, 0.016, S["LEG"], breaks=(0.42,))
        # shin and foot
        beam(bm, P(6.1, 17.4, 0.18 * lift + 0.02), ankle, 2.2 * PX, 1.9 * PX, 0.06, 0.055, 0.012, S["LEG"])
        beam(bm, ankle, foot, 1.9 * PX, 1.7 * PX, 0.055, 0.045, 0.01, S["LEG"])
        # joints: hip, knee, ankle pins (x-axis), foot pin into the channel wall (y-axis)
        cylinder(bm, hip, (1, 0, 0), 0.75 * PX, 2.0 * PX, S["JOINT"])
        cylinder(bm, knee + Vector((0, 0, -0.01)), (1, 0, 0), 0.8 * PX, 3.2 * PX, S["JOINT"])
        cylinder(bm, ankle, (1, 0, 0), 0.7 * PX, 2.3 * PX, S["JOINT"])
        cylinder(bm, foot, (1, 0, 0), 0.55 * PX, 2.0 * PX, S["JOINT"])
        # anchor rod from the foot to the channel's south wall
        sweep(bm, [(*foot[:3], 0.2 * PX, 0.2 * PX), (*P(6.8, 22.6, 0.03)[:3], 0.2 * PX, 0.2 * PX)], sides=6,
              mat=S["JOINT"])
        # hydraulic ram along the back of the shin (outer side)
        sweep(bm, [(*P(4.55, 15.0, 0.25 * lift + 0.02)[:3], 0.3 * PX, 0.3 * PX),
                   (*P(6.0, 19.2, 0.07 * lift + 0.03)[:3], 0.3 * PX, 0.3 * PX)], sides=6, mat=S["JOINT"])
        # link from the hip to the pod flank
        pod_side = P(7.6, 10.9, z0 + 0.02)
        sweep(bm, [(*hip[:3], 0.22 * PX, 0.22 * PX), (*pod_side[:3], 0.22 * PX, 0.22 * PX)], sides=6,
              mat=S["JOINT"])


def clip_above_ground(obj, zmin=0.004):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, zmin), plane_no=(0, 0, 1), clear_inner=True)
    edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bm.to_mesh(obj.data)
    bm.free()


# --- build a stage ---------------------------------------------------------------------------------------------

def build(stage, sprite, coll):
    mats = materials(sprite, stage)
    objs = build_deck(stage, mats, coll)
    if stage in ("newshc-1-f2", "newshc-1-f3", "newshc-1-f4"):
        bm = bmesh.new()
        if stage == "newshc-1-f2":
            # the pod's crown pushing up through the gap, its top a little proud of the leaves, in its
            # unlit colours: mauve carapace and vent ribs (164-170), the tan window band (83-92)
            z0 = INT_TOP + 0.05 - POD["h"]
            build_pod(bm, z0, False)
            for f in bm.faces:
                if f.material_index in (S["WINDOW"], S["CORE"]):
                    f.material_index = S["TAN"]
                elif f.material_index == S["VENT"]:
                    f.material_index = S["MAUVE"]
                elif f.material_index == S["RIB"]:
                    f.material_index = S["JOINT"]   # the dark grooves at cols 9 and 13
                else:
                    f.material_index = S["DOME"]
            # frame 3 draws the crown over rows 7-11, cols 7-15: a hair larger than the raised
            # pod's plan (whose rim rows are ink on frames 9-13), so stretch it about its centre
            c = W(POD["cu"], POD["cv"])
            for vt in bm.verts:
                vt.co.x = c.x + (vt.co.x - c.x) * 1.04
                vt.co.y = c.y + (vt.co.y - c.y) * 1.16
            build_petals(bm)
        elif stage == "newshc-1-f3":
            z0 = 0.06
            build_pod(bm, z0, False)
            build_legs(bm, z0, False)
        else:
            z0 = 0.16
            build_pod(bm, z0, True)
            build_legs(bm, z0, True)
        o = to_object(f"{stage}_pod", bm, mats, coll)
        clip_above_ground(o)
        objs.append(o)
    for o in objs:
        o.data.shade_smooth()
        o.data.set_sharp_from_angle(angle=math.radians(40))
    return objs, mats


def export(stage, sprite, bake):
    coll = common.reset_collection(stage)
    objs, mats = build(stage, sprite, coll)
    # The raised pod and its legs are a separate island from the deck, and outline_shell keeps
    # only the largest island: give the rig its own shell and join it to the deck's (D51).
    rig = None
    for o in objs:
        if o.name.endswith("_pod") and stage in ("newshc-1-f3", "newshc-1-f4"):
            rig = o.copy()
            rig.data = o.data.copy()
            rig.modifiers.clear()
            rig.hide_render = True   # out of the AO bake
            coll.objects.link(rig)
    obj = T.join(objs, stage)
    closed = obj.copy()
    closed.data = obj.data.copy()
    closed.modifiers.clear()
    closed.hide_render = True
    coll.objects.link(closed)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"built {stage}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if bake:
        tint, textured = T.TINT, T.TEXTURED
        T.TINT = (1.0, 1.0, 1.0)
        T.TEXTURED = tuple(i for i, (n, _, _) in enumerate(SLOTS) if n not in ("VENT", "CORE", "WINDOW"))
        try:
            T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{stage}_bake_"), size=1024, samples=64)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{stage}_")
        fmt = "WEBP"
    shell = common.outline_shell(closed, coll, voxel=0.012, faces=2500, smooth=6, islands="outer")
    bpy.data.objects.remove(closed)
    if rig is not None:
        rshell = common.outline_shell(rig, coll, voxel=0.012, faces=2500, smooth=6, islands="outer")
        bpy.data.objects.remove(rig)
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        shell.select_set(True)
        rshell.select_set(True)
        bpy.context.view_layer.objects.active = shell
        bpy.ops.object.join()
        shell = bpy.context.view_layer.objects.active
        while len(shell.data.materials) > 1:
            shell.data.materials.pop()
        for p in shell.data.polygons:
            p.material_index = 0
        shell["tyrian_outline"] = True
        zs = [v.co.z for v in shell.data.vertices]
        print(f"{stage} outline shell z {min(zs):.3f}..{max(zs):.3f}")
    shell.name = shell.data.name = f"{stage}_outline"
    sprites = []
    for sp in sprite["sprites"]:
        fr = [i for i in sp["frames"] if i in STAGES[stage]]
        if fr:
            sprites.append({**sp, "frames": fr})
    common.export_sprite_model(WT, [obj, shell], f"enemies/{stage}", sprites, image_format=fmt)
    return obj, shell


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(WT, NAME)
    only = [a for a in argv if a.startswith("newshc-1")]
    for stage in STAGES:
        if only and stage not in only:
            continue
        export(stage, sprite, "--no-bake" not in argv)


if __name__ == "__main__" and "--as-module" not in sys.argv:
    main()
