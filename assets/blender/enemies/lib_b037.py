"""Helpers shared by batch b037's model scripts (build-models.sh skips lib_ files).

Coordinates are sprite pixels: X(c) and Y(r) take a pixel column / row centre (fractions allowed),
EX(e) and EY(e) take a pixel edge. Sprite up is +Y, one pixel is 1/12 unit, and the centre of the
24x28 block is the origin.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12


def X(c, w=24):
    """Pixel column centre to Blender X."""
    return (c + 0.5 - w / 2) / 12


def Y(r, h=28):
    """Pixel row centre to Blender Y (sprite up is +Y)."""
    return (h / 2 - (r + 0.5)) / 12


def EX(e, w=24):
    """Pixel edge (column boundary) to Blender X."""
    return (e - w / 2) / 12


def EY(e, h=28):
    """Pixel edge (row boundary) to Blender Y."""
    return (h / 2 - e) / 12


def tag_faces(bm, first, mat, smooth):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first:]:
        f.material_index = mat
        f.smooth = smooth


def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (x, y, z, half_width, half_height) in units. Rings stand perpendicular
    to the path (in the XY plane); width is across the path, height along Z. A ring of zero size
    collapses to a point."""
    first = len(bm.faces)
    pts = [Vector((x, y, z)) for x, y, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
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
            bm.faces.new(f)
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    tag_faces(bm, first, mat, smooth)


def loft_y(bm, x, sections, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A loft down the screen at Blender X `x`: sections are (y, half_width, half_height, z)."""
    sweep(bm, [(x, y, z, w, h) for y, w, h, z in sections], sides=sides, mat=mat, smooth=smooth,
          cap_start=cap_start, cap_end=cap_end)


def loft_x(bm, y, sections, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A loft across the screen at Blender Y `y`: sections are (x, half_width_in_y, half_height, z)."""
    sweep(bm, [(x, y, z, w, h) for x, w, h, z in sections], sides=sides, mat=mat, smooth=smooth,
          cap_start=cap_start, cap_end=cap_end)


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (x, y) in units (counter-clockwise or not)."""
    first = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    tag_faces(bm, first, mat, smooth)


def box(bm, x0, y0, x1, y1, z0, z1, mat=0):
    plate(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat=mat)


def ellipsoid(bm, centre, radii, mat=0, segments=16, rings=8, smooth=True):
    first = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    rx, ry, rz = radii
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * rx, cy + v.co.y * ry, cz + v.co.z * rz))
    tag_faces(bm, first, mat, smooth)
    return res["verts"]


def diamond_loft(bm, x, sections, mat=0, smooth=False, cap=True):
    """A faceted ridge down the screen: sections are (y, half_width, top_z, bottom_z); each section
    is a diamond with corners at the sides (z = mid) and on the ridge (top_z) and keel (bottom_z).
    Zero half width collapses to a point at z = top."""
    first = len(bm.faces)
    rings = []
    for y, w, top, bot in sections:
        mid = 0.5 * (top + bot) if w else top
        if w == 0:
            rings.append([bm.verts.new((x, y, mid))])
            continue
        rings.append([bm.verts.new(co) for co in ((x + w, y, mid), (x, y, top), (x - w, y, mid), (x, y, bot))])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(4):
            j = (k + 1) % 4
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[j], r1[k]))
            elif len(r1) == 1:
                bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if cap and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    tag_faces(bm, first, mat, smooth)


def mirror_since(bm, first_vert, axis_x):
    """Add a mirror image about X = axis_x of every face whose vertices were all added since
    vertex index `first_vert`."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[first_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = list({e for f in faces for e in f.edges})
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def paint_from_pixels(bm, first_face, pixels, slot_of, w=24, h=28, keep=None):
    """Give each face added since `first_face` the slot for the sprite pixel under its centre
    (seen from above). slot_of(index) returns a slot or None to keep the face's slot; pixels
    outside the sprite (or transparent) keep it too. `keep` is a set of slots that are not painted."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        if keep and f.material_index in keep:
            continue
        c = f.calc_center_median()
        col = int(math.floor(c.x * 12 + w / 2))
        r = int(math.floor(h / 2 - c.y * 12))
        if 0 <= r < h and 0 <= col < w and pixels[r][col] >= 0:
            s = slot_of(pixels[r][col])
            if s is not None:
                f.material_index = s


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


def merged_sprite(root, names):
    """The first name's sprite.json with the colours of every name, so any piece's index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def run(file, name, build):
    """Load the sprite, build, export enemies/<name> with all its frames, preview if asked.
    `build` returns the object, or a list of objects (the body and its frame parts)."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    obj = build(sprite)
    objs = obj if isinstance(obj, list) else [obj]
    common.export_sprite_model(root, objs, f"enemies/{name}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = root / "reference" / "models" / name / sprite["frames"][0]["image"]
        common.render_preview(objs, out, ref, size=sprite["frames"][0]["size"], frame=sprite["frames"][0]["index"])
    return obj


def cube_sphere(bm, centre, radii, cuts=9, mat=0, smooth=True):
    """An ellipsoid made from a subdivided cube pushed out to a sphere: even quads all over, so
    painting it from the sprite (paint_from_pixels) has no pinched pole in the middle of the top."""
    first_face, first_vert = len(bm.faces), len(bm.verts)
    res = bmesh.ops.create_cube(bm, size=2.0)
    edges = list({e for v in res["verts"] for e in v.link_edges})
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
    bm.verts.ensure_lookup_table()
    cx, cy, cz = centre
    rx, ry, rz = radii
    for v in bm.verts[first_vert:]:
        # Spread the grid evenly over the sphere (the cube-to-sphere mapping).
        x, y, z = v.co
        sx = x * math.sqrt(max(0.0, 1 - y * y / 2 - z * z / 2 + y * y * z * z / 3))
        sy = y * math.sqrt(max(0.0, 1 - z * z / 2 - x * x / 2 + z * z * x * x / 3))
        sz = z * math.sqrt(max(0.0, 1 - x * x / 2 - y * y / 2 + x * x * y * y / 3))
        v.co = Vector((cx + sx * rx, cy + sy * ry, cz + sz * rz))
    tag_faces(bm, first_face, mat, smooth)
