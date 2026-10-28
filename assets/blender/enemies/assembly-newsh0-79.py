"""Blue bat-winged beast (newsh0.shp, assembly of 13 pieces): a 3D version of its sprites.

Seen in level 2.12. Pieces of newsh0.shp side by side make one 168 x 84 px creature
(sprite.json `assemblyLayout`): a spiny blue head with two long horns reaching up the screen, a
dark jaw hanging below it, a ribbed grey shell on each shoulder, and two huge feathered wings
that sweep out and up to a grey claw at each tip. Each wing has three feather fingers along its
upper edge, a bright bone along its lower edge from the tip down to the elbow, and an arm from
the elbow back to the body with a dark underside.

The creature is mirror symmetric about the centre of assembly pixel column 96. It is built once
(the left half, mirrored, then the centre parts) in assembly coordinates and cut into this
batch's thirteen pieces with common.split_assembly. The top-row pieces of the layout
(newsh0-1, -3, -7, -9, -13: the horn tips and the left wing claw) are separate catalogue
entries, so they are built here for the fit but not exported. Every piece has one frame.

Assembly pixel (0, 0) is screen (30, -32), the top-left corner of newsh0-1.

Run: blender --background --python assets/blender/enemies/assembly-newsh0-79.py [-- --preview out.png]
(the preview is the whole creature; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newsh0-79"
ROOT = common.repo_root(__file__)
PIECES = ["newsh0-79", "newsh0-81", "newsh0-83", "newsh0-85", "newsh0-87", "newsh0-89", "newsh0-39",
          "newsh0-41", "newsh0-43", "newsh0-45", "newsh0-47", "newsh0-49", "newsh0-51"]
SX0, SY0 = 30, -32  # screen position of assembly pixel (0, 0)
AXIS_EDGE = 96.5  # the mirror axis: the centre of assembly pixel column 96
ROW0 = 56  # assembly row edge at Blender Y = 0 (the middle of this batch's pieces)
PX = 1 / 12


def XE(e):
    """Assembly column edge (pixel c spans edges c..c+1) to Blender X."""
    return (e - AXIS_EDGE) / 12


def YE(e):
    """Assembly row edge to Blender Y: sprite up is +Y."""
    return (ROW0 - e) / 12


def X(c):
    """Assembly pixel column (centre, fractions allowed) to Blender X."""
    return XE(c + 0.5)


def Y(r):
    """Assembly pixel row (centre) to Blender Y."""
    return YE(r + 0.5)


# --- geometry helpers (after assembly-newsht-39.py) --------------------------------------------

def sweep(bm, path, sides=8, mat=0, smooth=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in the XY plane; a ring of zero size collapses to a point."""
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        rings.append([bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a)))
                      for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            faces.append(bm.faces.new(f))
    if len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def loft_y(bm, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite centred on column `col`: sections are (row, half_width_px, half_height, z)."""
    sweep(bm, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1; outline is (col_edge, row_edge) points."""
    pts = [(XE(c), YE(r)) for c, r in outline]
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = smooth


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=12, rings=6):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


def mirror_all(bm):
    """Add a mirror image (about the axis, X = 0) of everything built so far."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


# Wing dihedral: the wings rise linearly from the wing root (column edge 74) out to the tip.
ROOT_X = XE(74)
DIHEDRAL = 0.024  # z per unit of X outboard of the root


def bend_wing(bm):
    """Cut everything at the wing root so each face stays planar, then lift what's outboard."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(ROOT_X, 0, 0), plane_no=(1, 0, 0))
    for v in bm.verts:
        if v.co.x < ROOT_X:
            v.co.z += (ROOT_X - v.co.x) * DIHEDRAL


# --- the creature ------------------------------------------------------------------------------

# Left wing outline (column edge, row edge), clockwise from the claw along the fingered upper
# edge to the root, then back along the lower edge. Taken from each column's filled extent.
WING = [
    (5, 13), (7, 11), (9, 14), (10.5, 16), (12, 18), (15, 18), (16, 21), (17.5, 25), (19, 25),
    (20.5, 24), (23, 24.5), (25, 28.5), (28, 31.5), (31, 34.5), (34, 37), (36.5, 38), (37, 32.5),
    (39.5, 31.8), (42, 32.5), (44, 33.5), (46, 36), (48, 38.5), (50, 40.5), (52, 42.5),
    (54, 44), (56, 46.5), (58, 48), (61, 49.8), (66, 47), (72, 43.5), (80, 44), (86, 46),
    (86, 62), (80, 64.5), (76, 66), (56, 66), (54, 67.5), (53.5, 75), (48, 75.5), (45, 74.5), (42, 71.5),
    (40, 68.5), (36, 64.5), (32, 61), (28, 57.5), (24, 54), (20, 50.5), (16, 46.5), (13, 43),
    (11.5, 39.5), (9.5, 35.5), (8.3, 32), (7, 28.5), (5.5, 25),
]
# The dark underside of the arm showing below it (rows 64-69).
UNDER = [(53.5, 64), (79, 64), (79, 68.5), (77, 69.6), (56, 69.6), (53.5, 71)]
# Grey shell on the shoulder: outline of its base.
SHELL = [(62, 46), (66, 44.5), (71, 43), (76, 43.2), (81, 44), (82.5, 47), (79, 53), (78, 57),
         (73, 57), (69, 52), (64, 49)]


def _inside(p, poly):
    x, y = p
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def _edge_dist(p, poly):
    best = 1e9
    for a, b in zip(poly, poly[1:] + poly[:1]):
        a, b, q = Vector(a), Vector(b), Vector(p)
        t = max(0.0, min(1.0, (q - a).dot(b - a) / max((b - a).length_squared, 1e-9)))
        best = min(best, (q - (a + (b - a) * t)).length)
    return best


def offset_poly(poly, off):
    """Grow a closed (col, row) outline outward by `off` px (mitred, capped at 2x), so the model
    covers the sprite's dark edge pixels too. `off` may be a list, one amount per vertex."""
    n = len(poly)
    offs = off if isinstance(off, (list, tuple)) else [off] * n
    pts = [Vector(p) for p in poly]

    def normal(a, b):
        d = (b - a).normalized()
        nv = Vector((d.y, -d.x))
        mid = (a + b) / 2
        return nv if not _inside(tuple(mid + nv * 0.05), poly) else -nv

    out = []
    for i in range(n):
        n1 = normal(pts[i - 1], pts[i])
        n2 = normal(pts[i], pts[(i + 1) % n])
        m = (n1 + n2)
        m = n1 if m.length < 1e-6 else m.normalized()
        k = offs[i] / max(0.5, m.dot(n1))
        p = pts[i] + m * k
        out.append((p.x, p.y))
    return out


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def bump(x):
    """1 at 0, falling smoothly to 0 at |x| = 1."""
    return max(0.0, 1.0 - x * x) ** 2


def cr_of(v):
    """Blender (x, y) back to assembly pixel (col, row) centre coordinates."""
    return v.x * 12 + AXIS_EDGE - 0.5, ROW0 - v.y * 12 - 0.5


def relief_plate(bm, outline, top_fn, bot_fn, step_c, step_r, mat=0, smooth=True):
    """A plate with the outline (col_edge, row_edge) whose top and bottom follow top_fn(c, r) and
    bot_fn(c, r) (units), cut into a grid of step_c x step_r px so it can curve."""
    old_v, old_e, old_f = set(bm.verts), set(bm.edges), set(bm.faces)
    plate(bm, outline, -0.5, 0.5, mat=mat)
    cs = [c for c, _ in outline]
    rs = [r for _, r in outline]

    def new_geom():
        return ([v for v in bm.verts if v not in old_v] + [e for e in bm.edges if e not in old_e]
                + [f for f in bm.faces if f not in old_f])

    c = math.floor(min(cs)) + step_c
    while c < max(cs):
        bmesh.ops.bisect_plane(bm, geom=new_geom(), plane_co=(XE(c), 0, 0), plane_no=(1, 0, 0))
        c += step_c
    r = math.floor(min(rs)) + step_r
    while r < max(rs):
        bmesh.ops.bisect_plane(bm, geom=new_geom(), plane_co=(0, YE(r), 0), plane_no=(0, 1, 0))
        r += step_r
    verts = [v for v in bm.verts if v not in old_v]
    for v in verts:
        c, r = cr_of(v.co)
        v.co.z = top_fn(c, r) if v.co.z > 0 else bot_fn(c, r)
    faces = [f for f in bm.faces if f not in old_f]
    caps = [f for f in faces if abs(f.normal.z) > 0.5]
    res = bmesh.ops.triangulate(bm, faces=caps)
    for f in res["faces"]:
        f.smooth = smooth
        f.material_index = mat


def dome_rings(sections, step=1.0):
    """Resample (row, half_width_px, top_z, bottom_z) sections every `step` rows."""
    out = []
    rows = [s[0] for s in sections]
    r = rows[0]
    while r <= rows[-1] + 1e-6:
        out.append(_interp(sections, r))
        r += step
    if out[-1][0] < rows[-1] - 1e-6:
        out.append(_interp(sections, rows[-1]))
    return out


def _interp(sections, r):
    for a, b in zip(sections, sections[1:]):
        if a[0] <= r <= b[0]:
            t = (r - a[0]) / (b[0] - a[0])
            return tuple(x + (y - x) * t for x, y in zip(a, b))
    return sections[0] if r < sections[0][0] else sections[-1]


def dome_top(sections, z0, c, r, depth_fn=None):
    """The top surface of dome_loft at assembly pixel (c, r), or None outside it."""
    if not sections[0][0] <= r <= sections[-1][0]:
        return None
    _, w, top, _ = _interp(sections, r)
    u = (c - (AXIS_EDGE - 0.5)) / max(w, 1e-6)
    if abs(u) > 1:
        return None
    s = math.sqrt(1 - u * u)
    z = z0 + (top - z0) * s
    if depth_fn:
        z -= depth_fn(c, r) * math.sqrt(s)
    return z


def dome_loft(bm, sections, z0, mats, n=26, n_bottom=8, depth_fn=None, step=1.0, mat_fn=None, pit_at=0.1):
    """A long rounded body down the centre line: each ring's top is a half ellipse rising from z0 at
    the outline to top_z at the middle, the bottom one falling to bottom_z. depth_fn(c, r) (units)
    cuts grooves and pits into the top; mats = (base, groove, pit) material indices. mat_fn(r, s,
    under), if given, picks the material of every face not in a groove or pit (s: 0 at the outline,
    1 on the centre line; under: a bottom face)."""
    base, groove, pit = mats
    rings, depth, info = [], {}, {}
    for r, w, top, bot in dome_rings(sections, step):
        ring = []
        for k in range(n + 1):
            u = -math.cos(math.pi * k / n)
            s = math.sqrt(max(0.0, 1 - u * u))
            c = (AXIS_EDGE - 0.5) + u * w
            d = depth_fn(c, r) * math.sqrt(s) if depth_fn else 0.0
            v = bm.verts.new((u * w * PX, Y(r), z0 + (top - z0) * s - d))
            depth[v] = d
            info[v] = (r, s, 0.0)
            ring.append(v)
        for k in range(n_bottom - 1, 0, -1):
            u = -math.cos(math.pi * k / n_bottom)
            s = math.sqrt(max(0.0, 1 - u * u))
            v = bm.verts.new((u * w * PX, Y(r), z0 - (z0 - bot) * s))
            depth[v] = 0.0
            info[v] = (r, s, 1.0)
            ring.append(v)
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        m = len(r0)
        for k in range(m):
            j = (k + 1) % m
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            dd = sum(depth[v] for v in f.verts) / 4
            if dd > pit_at:
                f.material_index = pit
            elif dd > 0.05:
                f.material_index = groove
            elif mat_fn:
                rr, ss, uu = (sum(info[v][i] for v in f.verts) / 4 for i in range(3))
                f.material_index = mat_fn(rr, ss, uu > 0.5)
            else:
                f.material_index = base
            f.smooth = True
            faces.append(f)
    for ring in (rings[0], rings[-1]):
        f = bm.faces.new(ring)
        f.material_index = base
    return faces


# Wing thickness (sprite px): thick at the root, thin at the claw, rounded toward every edge.
WING_OUT = None  # the grown wing outline, set in build()


def wing_round(c, r):
    d = _edge_dist((c + 0.5, r + 0.5), WING_OUT) if _inside((c + 0.5, r + 0.5), WING_OUT) else 0.0
    return math.sqrt(min(1.0, (d + 0.35) / 6.5))


def wing_top(c, r):
    t = max(0.0, min(1.0, (c - 4) / 80)) ** 1.1
    return (2.6 + 4.6 * t) * wing_round(c, r) / 12


def wing_bottom(c, r):
    # Nearly flat underneath: the wing sits on z = 0 at the root instead of hanging a belly below.
    t = max(0.0, min(1.0, (c - 4) / 80)) ** 1.4
    return -(0.5 + 0.3 * t) * wing_round(c, r) / 12


def on_wing(path, lift=0.0):
    """Sweep path (col, row, half_width, half_height) -> (col, row, z, w, h) sitting on the wing."""
    return [(c, r, wing_top(c, r) + lift, w, h) for c, r, w, h in path]


# Branching veins on the left wing: a main vein down the middle of the wing from the claw to the
# elbow, with branches forking up into each feather finger along the upper edge.
VEINS = [
    # (points (col, row), half width px at the root end, protrusion units)
    ([(70, 57.5), (60, 56.5), (50, 54), (40, 49), (30, 43), (20, 35.5), (13, 27), (10, 22)], 2.0, 0.2),
    ([(21, 36.5), (17, 30), (14.5, 24), (13.5, 20.5)], 1.7, 0.17),
    ([(17, 30), (19.5, 27.5)], 1.2, 0.11),
    ([(31, 43.5), (27, 37), (23.5, 30.5), (21, 26.5)], 1.7, 0.17),
    ([(27, 37), (30, 34.8)], 1.2, 0.11),
    ([(42, 50), (40, 43), (38.5, 37.5), (38.5, 34.5)], 1.7, 0.17),
    ([(40, 43), (44, 38.5)], 1.2, 0.11),
    ([(52, 54.5), (50, 48), (48.5, 42.5)], 1.6, 0.15),
    ([(50, 48), (54.5, 47.5)], 1.2, 0.11),
    ([(61, 56.5), (59, 51.5)], 1.3, 0.12),
    # lower feathers: short strokes from the main vein down toward the bone
    ([(25, 39.5), (26.5, 45)], 1.2, 0.11),
    ([(35, 46), (36, 52.5)], 1.2, 0.11),
    ([(45, 51.5), (45.5, 57.5)], 1.2, 0.11),
]


def curve(pts, bow=1.4, iters=2):
    """Bend a vein: a two-point stroke gets a bowed midpoint (toward the wing tip side), then
    Chaikin corner cutting rounds every kink, keeping both ends, so the ribs curve and fan."""
    pts = [Vector(p) for p in pts]
    if len(pts) == 2:
        a, b = pts
        d = (b - a).normalized()
        nrm = Vector((-d.y, d.x))
        if nrm.x > 0:
            nrm = -nrm
        pts = [a, (a + b) / 2 + nrm * bow, b]
    for _ in range(iters):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        out.append(pts[-1])
        pts = out
    return [(p.x, p.y) for p in pts]


def vein_path(pts, w0, h0, sink=0.45):
    """A rib sunk into the wing: its centre sits `sink` of its half height below the surface, so
    only a ridge grows out of the plate, fading into it at the far end."""
    n = len(pts)
    out = []
    for i, (c, r) in enumerate(pts):
        f = 1.0 - 0.55 * i / max(1, n - 1)
        h = h0 * f + 0.01
        if i == n - 1:
            out.append((c, r, wing_top(c, r) - 0.03, 0.0, 0.0))
        else:
            out.append((c, r, wing_top(c, r) - sink * h, w0 * f, h))
    return out


# Head and jaw: (row, half_width_px, top_z, bottom_z).
HEAD_Z0 = 0.15
HEAD = [(44, 4.8, 0.50, 0.05), (45, 7.0, 0.62, 0.0), (47, 10.0, 0.80, 0.0), (49, 12.8, 0.92, 0.0),
        (51, 15.3, 1.02, 0.0), (53, 16.6, 1.10, 0.0), (56, 17.8, 1.17, 0.0), (58.5, 18.4, 1.13, 0.0),
        (61, 18.8, 1.05, 0.0), (63, 18.0, 0.97, 0.0), (65, 16.8, 0.88, 0.0), (67, 14.5, 0.78, 0.0),
        (68.5, 11.5, 0.70, 0.0), (69.7, 6.0, 0.62, 0.02)]
# The lower face: no longer hanging under the body but a taper running on from the dome's front
# down to a blunt nose tip about 4 px tall at the sprite's bottom edge, its dark rim at the
# outline low, so it reads as the black V round the nose ribs. Nothing goes below z = 0.
JAW_Z0 = 0.03
# The whole lower face's outline, now only a low dark floor (0.5-1 px): it shows as the dark gaps
# beside the nose (r7/r8) and the black outline round it.
FLOOR = [(60, 4.0, 0.06, 0.0), (61, 15.6, 0.07, 0.0), (65, 19.6, 0.07, 0.0), (68, 21.0, 0.07, 0.0),
         (70, 22.6, 0.07, 0.0), (72, 20.0, 0.07, 0.0), (75, 17.0, 0.07, 0.0), (77, 15.2, 0.07, 0.0),
         (79, 14.0, 0.07, 0.0), (81, 12.2, 0.07, 0.0), (83, 10.3, 0.07, 0.0), (83.5, 9.6, 0.05, 0.0)]
# The lit face on it: wide cheeks under the skull (rows 60-66), narrowing at row 67 to the nose
# between the dark gaps (columns 87-105), which tapers to a blunt tip about 4 px tall.
JAW = [(60, 4.0, 0.40, 0.0), (61, 15.6, 0.62, 0.0), (63, 18.0, 0.70, 0.0), (65, 18.0, 0.72, 0.0),
       (66, 16.0, 0.70, 0.0), (67, 12.5, 0.68, 0.0), (68, 11.0, 0.66, 0.0), (69, 9.3, 0.64, 0.0),
       (71, 8.5, 0.61, 0.0), (74, 7.3, 0.56, 0.0), (76, 6.2, 0.52, 0.0), (77.5, 4.8, 0.48, 0.0),
       (78.8, 3.2, 0.40, 0.0), (79.6, 2.0, 0.22, 0.0)]


def head_depth(c, r):
    """Grooves and eye pits cut into the head (units)."""
    dc = abs(c - (AXIS_EDGE - 0.5))
    d = 0.0
    # transverse groove between the skull and the lower face
    if 2.5 < dc < 9:
        d = max(d, 0.13 * bump((r - 58.3) / 1.1) * smoothstep(2.5, 4.5, dc) * (1 - smoothstep(7, 9, dc)))
    # grooves either side of the spine
    if 46 < r < 58:
        d = max(d, 0.12 * bump((dc - 5.6) / 1.1) * smoothstep(46, 48.5, r))
    # eye pits: round, smooth-rimmed bowls about 3 px deep at the sprite's dark eyes (r5/r6,
    # centred on column 84 / 108, row 59), kept above the lower face under them.
    dist = math.hypot((dc - 12.0) / 4.2, (r - 59.2) / 3.2)
    if dist < 1:
        d = max(d, 0.46 * 0.5 * (1 + math.cos(math.pi * dist)))
    return d


def head_top(c, r):
    z = dome_top(HEAD, HEAD_Z0, c, r, head_depth)
    return z


def jaw_top(c, r):
    return dome_top(JAW, JAW_Z0, c, r)


def body_top(c, r):
    zs = [z for z in (head_top(c, r), jaw_top(c, r)) if z is not None]
    return max(zs) if zs else 0.0


def on_body(path, lift=0.0):
    return [(c, r, body_top(c, r) + lift, w, h) for c, r, w, h in path]


SHELL_OUT = None
SHELL_HUB = (77.0, 55.0)


def shell_top(c, r):
    d = _edge_dist((c + 0.5, r + 0.5), SHELL_OUT) if _inside((c + 0.5, r + 0.5), SHELL_OUT) else 0.0
    f = math.sqrt(min(1.0, (d + 0.3) / 4.5))
    rim = wing_top(c, r) + 0.03 if _inside((c + 0.5, r + 0.5), WING_OUT) else 0.2
    t = max(0.0, min(1.0, (c - 62) / 20)) ** 0.8
    peak = (5.0 + 5.5 * t) / 12
    return rim + max(0.0, peak - rim) * f


def build(sprite):
    global WING_OUT, SHELL_OUT
    coll = common.reset_collection(NAME)
    tag = "nsh079"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        # Indices are the ones that best match the sprite's pixels under each part (the wing is a
        # mix of 51-56 that averages 53; its ribs read darker, the shells average 7-9).
        # The wing is the sprite's mid teal-navy (54): 53 rendered a greyish slate from above.
        pal(54, metallic=0.0, roughness=0.8),  # 0 wing and body navy
        pal(54, metallic=0.1, roughness=0.6),  # 1 horns, arms, cheek ridges, spine
        pal(55, metallic=0.15, roughness=0.5),  # 2 bright bones
        pal(48, metallic=0.0, roughness=0.85),  # 3 dark underside, head grooves, face outline
        pal(10, metallic=0.1, roughness=0.75),  # 4 light grey shell ribs and claw (matte)
        pal(6, metallic=0.05, roughness=0.8),  # 5 shell base, the grooves between the ribs
        pal(54, metallic=0.1, roughness=0.7),  # 6 lit navy face ribs, tusks
        pal(52, metallic=0.05, roughness=0.7),  # 7 wing ribs (a shade darker than the wing)
        pal(56, metallic=0.2, roughness=0.45),  # 8 pale highlights (head spikes)
        pal(48, metallic=0.0, roughness=0.9),  # 9 eye pits
        pal(52, metallic=0.0, roughness=0.8),  # 10 lower face, lit navy
        pal(53, metallic=0.05, roughness=0.7),  # 11 head dome
        pal(51, metallic=0.0, roughness=0.8),  # 12 nose tip, darker navy
    ]
    BLUE, RIDGE, BONE, DARK, GREY, GREYD, DEEP, VEIN, PALE, PIT, JAW_M, HEAD_M, NOSE = range(13)
    # Grow the outline over the sprite's dark edge, less along the long lower-left edge from the
    # elbow out to the tip, where a full 0.8 px overhung the sprite.
    offs = [0.8] * len(WING)
    for i in range(40, len(WING)):
        offs[i] = 0.25
    offs[39] = 0.5
    WING_OUT = offset_poly(WING, offs)
    SHELL_OUT = offset_poly(SHELL, 0.5)
    under = offset_poly(UNDER, 0.6)
    bm = bmesh.new()

    # ---- left wing (bent up, then mirrored) ----
    relief_plate(bm, WING_OUT, wing_top, wing_bottom, 4, 4, mat=BLUE)
    # The dark underside of the arm: a skirt sloping from the wing's lower edge down to the ground
    # line, so the arm's shadowed side grows out of the wing instead of a loose tube under it.
    def skirt_top(c, r):
        tc = max(0.0, min(1.0, (c - 4) / 80)) ** 1.1
        z_edge = (2.6 + 4.6 * tc) / 12 * 0.8
        return z_edge * (1 - smoothstep(64.0, 70.0, r)) + 0.02
    relief_plate(bm, under, skirt_top, lambda c, r: -0.03, 4, 1.5, mat=DARK)
    for i, (pts, w0, h0) in enumerate(VEINS):
        sweep(bm, vein_path(curve(pts), w0 * 1.1, h0 * 1.6), sides=6, mat=VEIN)
    # Bright bone along the lower edge from the tip to the elbow, then the arm to the body.
    sweep(bm, on_wing([(8.5, 29, 0.0, 0.0), (10, 32, 1.5, 0.08), (17, 42, 2.0, 0.12), (28, 52, 2.2, 0.15),
                       (38, 59.5, 2.3, 0.17), (45, 63.5, 2.3, 0.18), (49, 64, 2.2, 0.17)], 0.02), sides=8, mat=BONE)
    sweep(bm, on_wing([(42, 64, 0.0, 0.0), (44, 64, 2.0, 0.16), (52, 63.8, 2.3, 0.19),
                       (60, 63.8, 2.3, 0.2), (61, 63.8, 0.0, 0.0)], 0.03), sides=8, mat=BONE)
    sweep(bm, on_wing([(59, 64, 0.0, 0.0), (60, 64, 2.2, 0.19), (70, 64.2, 2.5, 0.22),
                       (79, 64.5, 2.7, 0.24), (82, 64.6, 2.4, 0.2)], 0.03), sides=8, mat=RIDGE)
    # The elbow knob below the arm (columns 42-53, rows 66-74).
    # A half-dome, flat underneath, so nothing hangs below the ground line.
    n_before = set(bm.verts)
    ellipsoid(bm, 48, 70, 0.0, 5.6, 4.6, 0.26, mat=BLUE)
    for v in set(bm.verts) - n_before:
        v.co.z = max(v.co.z, -0.02)
    # Grey claw at the wing tip.
    sweep(bm, [(6.6, 11.6, 0.1, 0.0, 0.0), (7, 13, 0.11, 1.6, 0.1), (7.5, 18, 0.12, 2.5, 0.16),
               (8, 25, 0.11, 2.2, 0.14), (8.6, 30.5, 0.1, 0.0, 0.0)], sides=8, mat=GREY)

    bend_wing(bm)

    # ---- shoulder shell: a convex fan, highest at its body-side edge ----
    relief_plate(bm, SHELL_OUT, shell_top, lambda c, r: 0.12, 2, 2, mat=GREYD)
    hub = SHELL_HUB
    for tip, w in (((62.3, 46.8), 1.6), ((66.3, 44.6), 1.9), ((70.5, 43.4), 2.0), ((74.6, 43.4), 2.0),
                   ((79.2, 44.4), 1.8)):
        path = []
        for k, (f, ww) in enumerate(((0.0, 0.0), (0.08, 1.0), (0.3, 1.1), (0.55, 1.1), (0.8, 0.9), (1.0, 0.6))):
            c, r = tip[0] + (hub[0] - tip[0]) * f, tip[1] + (hub[1] - tip[1]) * f
            z = shell_top(c, r)
            path.append((c, r, z - 0.01, w * ww, 0.0 if k == 0 else 0.085 * ww))
        sweep(bm, path, sides=6, mat=GREY)

    # ---- horn (left): a round tube as tall as it is wide, tapering up the screen ----
    # Widths from the sprite: 8 px at row 28, 10 px by row 34, 11 px at row 41, flaring into the
    # head at rows 43-46.
    # A straight cone: the half width grows evenly from a rounded tip to the base at the dome, and
    # the round section (as tall as it is wide) sits on the ground line, so there is no bulb.
    horn = []
    for c, r, w in ((85.3, 0.9, 0.0), (85.35, 1.6, 1.1), (85.4, 3.0, 1.7), (85.4, 8, 2.15), (85.45, 14, 2.7),
                    (85.6, 21, 3.6), (85.9, 28.5, 4.4), (86.6, 34, 4.9), (87.5, 38.5, 5.15),
                    (88.1, 42, 5.5), (88.6, 45, 5.8), (89.2, 50, 5.0)):
        h = w * PX * 0.95
        horn.append((c, r, 0.06 + max(h, 0.04), w, h))
    sweep(bm, horn, sides=10, mat=RIDGE)
    # Cheek ridges sweeping from the horn's base down the side of the head to the jaw.
    sweep(bm, on_body([(86.5, 46, 0.0, 0.0), (84, 50, 1.7, 0.08), (81, 56, 1.7, 0.08),
                       (79.6, 62, 1.6, 0.07), (80, 66, 0.0, 0.0)], 0.0), sides=6, mat=RIDGE)
    # V crest from the horn base in to the middle of the head.
    sweep(bm, on_body([(89, 44.5, 0.0, 0.0), (90, 45.5, 1.3, 0.07), (94, 50, 1.3, 0.07),
                       (96, 52, 0.0, 0.0)], 0.0), sides=6, mat=PALE)
    # The side lobe of the lower face (r11): a rounded navy ridge running down from the cheek,
    # outside the nose and between the dark gaps, to the nose tip, about 3 px tall.
    lobe = on_body([(83.6, 63, 0.0, 0.0), (83.4, 64.5, 2.0, 0.07), (83.2, 66.5, 2.4, 0.08)], -0.02)
    for c, r, w, h in ((81.0, 69.5, 2.6, 0.13), (81.8, 72, 3.0, 0.14), (83.0, 74, 2.8, 0.13),
                       (84.8, 76.3, 2.0, 0.1), (86.4, 78.6, 1.7, 0.09), (88.2, 80.6, 1.6, 0.08),
                       (90.6, 82.0, 1.2, 0.06), (92.4, 82.6, 0.0, 0.0)):
        lobe.append((c, r, 0.06 + h * 0.75, w, h))
    sweep(bm, lobe, sides=8, mat=NOSE)
    # A lit rib down the nose.
    sweep(bm, on_body([(91, 60.5, 0.0, 0.0), (91.5, 63, 1.3, 0.07), (92.2, 67, 1.3, 0.07),
                       (92.8, 70.5, 1.0, 0.05), (93.2, 72, 0.0, 0.0)], -0.02), sides=6, mat=DEEP)
    # Bright spots on the lower face.
    ellipsoid(bm, 92.5, 61.8, head_top(92.5, 61.8) - 0.01, 1.3, 1.3, 0.06, mat=PALE, segments=8, rings=4)

    mirror_all(bm)

    # ---- centre parts ----
    # Head: a tall skull dome, widest at the shells, with grooves and eye pits cut in.
    # The grooves and the eye pits' walls are a darker navy, only the pits' floors near black, so each
    # eye reads as a clean bowl rather than a hole.
    dome_loft(bm, HEAD, HEAD_Z0, (HEAD_M, NOSE, PIT), n=34, n_bottom=4, depth_fn=head_depth, step=0.9,
              pit_at=0.17)
    # The low dark floor of the lower face, and the lit navy face on it: dark only at its rim and
    # underneath, a darker navy toward the nose tip.
    dome_loft(bm, FLOOR, 0.02, (DARK, DARK, DARK), n=12, n_bottom=2, step=2.0)
    dome_loft(bm, JAW, JAW_Z0, (JAW_M, JAW_M, JAW_M), n=14, n_bottom=4, step=1.0,
              mat_fn=lambda r, s, under: DARK if under or s < 0.3 else NOSE if r > 72.5 else JAW_M)
    # Spine down the middle of the head, and the pale spikes on it.
    loft_y(bm, 96, [(r, w, h, head_top(96, r) - 0.01) for r, w, h in
                    ((45, 0.0, 0.0), (46, 1.6, 0.06), (52, 2.1, 0.09), (57, 2.1, 0.09), (60, 2.0, 0.08),
                     (65, 1.6, 0.06), (67, 0.0, 0.0))], sides=6, mat=RIDGE)
    # A ridge down the middle of the jaw.
    loft_y(bm, 96, [(r, w, h, jaw_top(96, r) - 0.01) for r, w, h in
                    ((68, 0.0, 0.0), (70, 1.7, 0.06), (75, 1.4, 0.05), (78.5, 0.0, 0.0))], sides=6, mat=NOSE)
    for r in (49.5, 54.5, 60.5):
        ellipsoid(bm, 96, r, head_top(96, r) + 0.04, 1.2, 1.2, 0.05, mat=PALE, segments=8, rings=4)

    return to_object(NAME, bm, mats, coll)


def flat_cut_faces(piece):
    """Shade the faces split_assembly filled at a piece's box edges flat, so they don't bend the
    smooth normals of the surfaces they meet (which showed as a light line along every cut)."""
    hw, hh = 12 / 12, 14 / 12
    mesh = piece.data
    for poly in mesh.polygons:
        cos = [mesh.vertices[i].co for i in poly.vertices]
        for axis, lim in ((0, hw), (1, hh)):
            if all(abs(abs(co[axis]) - lim) < 1e-4 for co in cos) and all(
                    (co[axis] > 0) == (cos[0][axis] > 0) for co in cos):
                poly.use_smooth = False


def merged_sprite():
    """newsh0-79's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh0-79")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole creature's sprite as one image at 2 px per sprite px, padded to the 24:28 shape
    render_preview expects for size 16 (192 x 224 sprite px), centred on the Blender origin."""
    import numpy as np
    w, h = 192 * 2, 224 * 2
    img = np.zeros((h, w, 4), dtype=np.float32)
    for e in layout:
        data = common.load_sprite(ROOT, e["model"])
        frame = data["frames"][0]
        for r, prow in enumerate(frame["pixels"]):
            for c, v in enumerate(prow):
                if v < 0:
                    continue
                ac, ar = e["cx"] - SX0 - 12 + c, e["cy"] - SY0 - 14 + r  # assembly pixel
                x, y = int(2 * (ac - AXIS_EDGE) + w / 2), int(2 * (ar - ROW0) + h / 2)
                img[y:y + 2, x:x + 2] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - SX0 - AXIS_EDGE, e["cy"] - SY0 - ROW0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for piece in pieces.values():
        flat_cut_faces(piece)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(sprite["assemblyLayout"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=16, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
