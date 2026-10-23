"""Helpers shared by batch b045's model scripts (newshk.shp, level 3.12).

Not a model itself: tools/build-models.sh skips lib_ modules. Scripts import it with
`import lib_b045 as lib` after putting assets/blender/enemies on sys.path.

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block by default (pass w=12, h=14 for size-1 sprites).
Several helpers are copied from lib_b003 and lib_b007.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units


def px(c, w=24):
    """Sprite column (pixel centre) to Blender X."""
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    """Sprite row (pixel centre) to Blender Y (sprite up is +Y)."""
    return (h / 2 - (r + 0.5)) / 12


def ex(e, w=24):
    """Sprite column edge (0 = left edge of column 0) to Blender X."""
    return (e - w / 2) / 12


def ey(e, h=28):
    """Sprite row edge (0 = top edge of row 0) to Blender Y."""
    return (h / 2 - e) / 12


def pts(outline, w=24, h=28):
    """A list of (column edge, row edge) points to Blender XY."""
    return [(ex(c, w), ey(r, h)) for c, r in outline]


def move(bm, start, dx=0.0, dy=0.0, dz=0.0):
    """Move every vertex added since index `start`."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x += dx
        v.co.y += dy
        v.co.z += dz


def faces_since(bm, first):
    bm.faces.ensure_lookup_table()
    return bm.faces[first:]


def set_smooth(bm, face_start, smooth=True):
    """Mark the faces added since index `face_start` smooth (or flat)."""
    for f in faces_since(bm, face_start):
        f.smooth = smooth


def mirror_x(bm, start=0, axis=0.0):
    """Add a mirror image, about the vertical plane X = axis, of the geometry built since vertex
    index `start` (faces whose vertices all lie in that range), keeping materials and smoothing."""
    bm.verts.ensure_lookup_table()
    src = bm.verts[start:]
    copies = {v: bm.verts.new((2 * axis - v.co.x, v.co.y, v.co.z)) for v in src}
    srcset = set(src)
    for f in [f for f in bm.faces if all(v in srcset for v in f.verts)]:
        nf = bm.faces.new([copies[v] for v in reversed(f.verts)])
        nf.material_index = f.material_index
        nf.smooth = f.smooth


def ellipsoid(bm, centre, radii, sides=16, rings=8, mat_index=0, smooth=True, top_only=False):
    """An ellipsoid (radii rx, ry, rz) at `centre`. top_only keeps the upper half (a dome with a
    flat base)."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    f0 = len(bm.faces)
    loops = []
    lo = 0 if top_only else -rings // 2 + 1
    for k in range(lo, rings // 2):
        t = (math.pi / 2) * k / (rings // 2)
        loops.append([bm.verts.new((cx + rx * math.cos(t) * math.cos(a), cy + ry * math.cos(t) * math.sin(a),
                                    cz + rz * math.sin(t)))
                      for a in (2 * math.pi * (i + 0.5) / sides for i in range(sides))])
    top = bm.verts.new((cx, cy, cz + rz))
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((l0[i], l0[j], l1[j], l1[i])).material_index = mat_index
    for i in range(sides):
        bm.faces.new((loops[-1][i], loops[-1][(i + 1) % sides], top)).material_index = mat_index
    if top_only:
        bm.faces.new(list(reversed(loops[0]))).material_index = mat_index
    else:
        bottom = bm.verts.new((cx, cy, cz - rz))
        for i in range(sides):
            bm.faces.new((loops[0][(i + 1) % sides], loops[0][i], bottom)).material_index = mat_index
    set_smooth(bm, f0, smooth)


def prism(bm, outline, z0, z1, mat_index=0, top_mat=None, smooth=False):
    """Extrude an XY outline (either winding) from z0 up to z1. `top_mat` colours the top face."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    if area < 0:
        outline = list(reversed(outline))
    f0 = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)
    if top_mat is not None:
        faces_since(bm, f0)[0].material_index = top_mat
    set_smooth(bm, f0, smooth)


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0, top_mat=None):
    """An axis-aligned box."""
    prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat_index, top_mat)


def inset_outline(outline, d):
    """Move each vertex of a closed counter-clockwise XY outline inward by `d`."""
    n = len(outline)
    out = []
    for i in range(n):
        p0, p1, p2 = outline[i - 1], outline[i], outline[(i + 1) % n]
        normals = []
        for a, b in ((p0, p1), (p1, p2)):
            ex_, ey_ = b[0] - a[0], b[1] - a[1]
            length = math.hypot(ex_, ey_) or 1.0
            normals.append((-ey_ / length, ex_ / length))
        nx, ny = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
        length = math.hypot(nx, ny) or 1.0
        nx, ny = nx / length, ny / length
        cos_half = max(0.35, nx * normals[0][0] + ny * normals[0][1])
        out.append((p1[0] + nx * d / cos_half, p1[1] + ny * d / cos_half))
    return out


def bevel_prism(bm, outline, z0, z1, bevel, bevel_h=None, mat_index=0, top_mat=None, side_mat=None):
    """A prism from z0 to z1 whose top edges are chamfered: the walls rise to z1 - bevel_h and a
    sloped band leads in by `bevel` to the flat top. Either winding."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    if area < 0:
        outline = list(reversed(outline))
    bevel_h = bevel if bevel_h is None else bevel_h
    top = inset_outline(outline, bevel)
    n = len(outline)
    side = mat_index if side_mat is None else side_mat
    lo = [bm.verts.new((x, y, z0)) for x, y in outline]
    mid = [bm.verts.new((x, y, z1 - bevel_h)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in top]
    bm.faces.new(list(reversed(lo))).material_index = side
    bm.faces.new(hi).material_index = mat_index if top_mat is None else top_mat
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], mid[j], mid[i])).material_index = side
        bm.faces.new((mid[i], mid[j], hi[j], hi[i])).material_index = mat_index


def sloped_prism(bm, outline, z0, tops, mat_index=0, side_mat=None):
    """A prism from z0 up to a sloped top: `outline` is a list of (x, y) and `tops` the top height
    at each point (a wedge, a ramp). Either winding."""
    pairs = list(zip(outline, tops))
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    if area < 0:
        pairs.reverse()
    side = mat_index if side_mat is None else side_mat
    lo = [bm.verts.new((x, y, z0)) for (x, y), _ in pairs]
    hi = [bm.verts.new((x, y, t)) for (x, y), t in pairs]
    bm.faces.new(list(reversed(lo))).material_index = side
    bm.faces.new(hi).material_index = mat_index
    n = len(pairs)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i])).material_index = side


def ring_loft(bm, rings, mats, cap_start=True, cap_end=True, cap_mats=None):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order.
    `mats` gives a material index per band (an int for all, a list per band, or a list of lists
    per band and segment). From lib_b007."""
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]

    def mat(band, seg):
        m = mats
        if isinstance(m, list):
            m = m[band]
        if isinstance(m, list):
            m = m[seg]
        return m
    for b, (r0, r1) in enumerate(zip(verts, verts[1:])):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat(b, i)
    first = mat(0, 0) if not cap_mats else cap_mats[0]
    last = mat(len(verts) - 2, 0) if not cap_mats else cap_mats[1]
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0]))).material_index = first
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1]).material_index = last
    return verts


def loft_x(bm, sections, y, z, sides=10, mat_index=0, cap_start=True, cap_end=True):
    """A loft along +X at height z and row y: sections are (x, half_depth_y, half_height)."""
    rings = []
    for x, hy, hz in sections:
        if hy == 0 and hz == 0:
            rings.append([(x, y, z)])
            continue
        rings.append([(x, y + hy * math.cos(a), z + hz * math.sin(a))
                      for a in (2 * math.pi * (i + 0.5) / sides for i in range(sides))])
    return ring_loft(bm, rings, mat_index, cap_start, cap_end)


def polyline_tube(bm, points, radius, sides=6, mat_index=0, caps=True, flat=1.0):
    """One continuous tube along a polyline of 3D points, rings facing the bisector. `radius` is a
    number or one per point; `flat` scales the ring's height (the part along Z) when the path
    runs level. From lib_b007."""
    from mathutils import Vector
    p = [Vector(q) for q in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(p)
    tangents = []
    for i in range(len(p)):
        d0 = (p[i] - p[i - 1]).normalized() if i > 0 else None
        d1 = (p[i + 1] - p[i]).normalized() if i < len(p) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tangents.append(t.normalized())
    rings = []
    up = Vector((0, 0, 1))
    for c, t, r in zip(p, tangents, radii):
        u = t.cross(up)
        if u.length < 1e-6:
            u = Vector((1, 0, 0))
        u.normalize()
        v = u.cross(t).normalized()
        if r == 0:
            rings.append([tuple(c)])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(tuple(c + r * math.cos(a) * u + r * flat * math.sin(a) * v))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps)


def mesh_object_mixed(name, bm, materials, collection):
    """Like common.mesh_object, but keeps each face's own smooth flag (see set_smooth)."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def merged_colors(root, names):
    """A sprite-like dict whose `colors` merge the palettes of several sprite.json files."""
    merged = {"name": "+".join(names), "colors": {}}
    for n in names:
        merged["colors"].update(common.load_sprite(root, n)["colors"])
    return merged


def run(file, name, build):
    """The usual main: load the sprite, build (returns a list of objects), export and, with
    `-- --preview <png>`, render the preview."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    objs = build(sprite)
    common.export_sprite_model(root, objs, f"enemies/{name}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / name / frame["image"]
        common.render_preview(objs, out, ref, size=frame["size"])


# --- The split V ship (newshk-207 whole; newshk-238 + newshk-242 pulled apart) -------------------

def v_ship_materials(sprite, tag):
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    return [
        pal(6, metallic=0.6, roughness=0.4),  # 0 arm grey
        pal(9, metallic=0.6, roughness=0.35),  # 1 hull light grey
        pal(12, metallic=0.7, roughness=0.3),  # 2 bright rims
        pal(4, metallic=0.5, roughness=0.5),  # 3 dark recess walls
        pal(117, metallic=0.3, roughness=0.55),  # 4 red armour
        pal(120, metallic=0.4, roughness=0.35),  # 5 orange armour ridge
        pal(124, emission_strength=4.0),  # 6 yellow eye
        pal(8, metallic=0.6, roughness=0.4),  # 7 recess floor
        pal(3, metallic=0.4, roughness=0.6),  # 8 dark side wall
        pal(7, metallic=0.6, roughness=0.4),  # 9 arm inner ridge
    ]


ARM, HULL, RIM, RECESS, RED, ORANGE, EYE, FLOOR, SIDE, RIDGE = range(10)


def v_ship_half(bm, x0, inner_edge=12.0, wall=False):
    """The left half of the V ship (newshk-207's columns 0-11) in a 24x28 block whose centre is
    at X = x0. The grey hull is a U: thin arms up the outer edge to tips at row 5 and a heavier
    bowl across the bottom (rows 15-26) with a framed recess in the middle; a red armour plate
    lies on each arm, raised along its inner edge where the yellow eye sits. `inner_edge` is the
    column edge the half ends at (12 when mirrored into the whole ship); `wall` adds the lit
    inner wall the split halves show."""
    def P(c, r):
        return (x0 + ex(c), ey(r))
    start = len(bm.verts)
    f0 = len(bm.faces)
    ie = inner_edge

    # Base hull: the whole half silhouette, thin, chamfered.
    base = [P(0, 5), P(1, 5), P(1.6, 7), P(4, 8.6), P(7, 9), P(11, 13), P(11, 18.5), P(ie, 18.5),
            P(ie, 26), P(8, 26), P(1, 19), P(0, 17.5)]
    bevel_prism(bm, base, -0.1, 0.03, 0.03, mat_index=ARM, side_mat=SIDE)

    # Arm: a rounded bar up the outer edge from the shoulder to the tip.
    polyline_tube(bm, [(x0 + ex(0.55), ey(4.8), 0.02), (x0 + ex(0.9), ey(8), 0.05), (x0 + ex(1.4), ey(12), 0.07),
                       (x0 + ex(2.0), ey(15.5), 0.08)], [0.3 * U, 1.0 * U, 1.3 * U, 1.6 * U], sides=8,
                  mat_index=ARM, flat=0.8)
    # Lighter ridge along the arm's inner side, under the red plate's outer edge (columns 2-4).
    polyline_tube(bm, [(x0 + ex(2.2), ey(7.6), 0.04), (x0 + ex(3.0), ey(11), 0.06), (x0 + ex(4.6), ey(14.6), 0.07)],
                  0.6 * U, sides=6, mat_index=RIDGE)

    # Shoulder and bowl: a raised light grey block (rows 15-26) with a bright top edge.
    bowl = [P(0.6, 15), P(6, 15), P(7, 17.6), P(ie, 18.6), P(ie, 26), P(8, 26), P(1.2, 19), P(0.6, 17.5)]
    bevel_prism(bm, bowl, -0.11, 0.12, 0.035, mat_index=HULL, side_mat=SIDE)
    polyline_tube(bm, [(x0 + ex(1.6), ey(15.4), 0.105), (x0 + ex(5.6), ey(15.4), 0.105)], 0.5 * U, sides=6,
                  mat_index=RIM)
    # Lower rim (row 24-25) a little darker: a chamfer is enough; add the bright frame round the
    # recess in the middle (columns 9-14, rows 19-23).
    box(bm, x0 + ex(9), ey(24), x0 + ex(10), ey(19), 0.1, 0.15, RIM)
    box(bm, x0 + ex(9), ey(24), x0 + ex(ie), ey(23), 0.1, 0.15, RIM)
    box(bm, x0 + ex(10), ey(23), x0 + ex(ie), ey(19), 0.07, 0.125, FLOOR, top_mat=FLOOR)
    box(bm, x0 + ex(10), ey(23), x0 + ex(ie), ey(22), 0.1, 0.13, RECESS)
    if wall:
        box(bm, x0 + ex(ie - 1), ey(24), x0 + ex(ie), ey(19), 0.1, 0.16, RIM)

    # Red armour plate on the arm: a wedge, high along its inner edge (the bright orange rim).
    plate = [P(3, 8), P(4, 8.4), P(7, 9), P(11, 13), P(11, 18.2), P(6, 18.2), P(5, 14.5), P(4, 12), P(3, 9.2)]
    tops = [0.09, 0.11, 0.16, 0.2, 0.2, 0.15, 0.12, 0.1, 0.09]
    sloped_prism(bm, plate, -0.02, tops, mat_index=RED)
    # Orange ridge down the plate's inner edge (rows 9-17: 119-122) and the eye at its corner.
    polyline_tube(bm, [(x0 + ex(5.6), ey(9.2), 0.17), (x0 + ex(8.6), ey(11.6), 0.2), (x0 + ex(9.6), ey(13.4), 0.215),
                       (x0 + ex(9.6), ey(18), 0.215)], 0.7 * U, sides=6, mat_index=ORANGE)
    ellipsoid(bm, (x0 + px(9.1), row(13.2), 0.215), (1.1 * U, 1.2 * U, 0.045), sides=10, rings=6, mat_index=EYE)
    return start, f0
