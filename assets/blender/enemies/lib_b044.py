"""Helpers shared by batch b044's model scripts (the grey pod halves newsha-161/163, the spiked
ice mine newsha-167 and the "WARNING MISSILE SHIPS!!" sign newsha-49/51).

Coordinates: sprite column c / row r of a 24x28 block. px/row give a pixel's centre, ex/ey a
pixel edge (the left or top edge of column c / row r). Fractions are fine.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


def px(c, w=24):
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    return (h / 2 - (r + 0.5)) / 12


def ex(c, w=24):
    return (c - w / 2) / 12


def ey(r, h=28):
    return (h / 2 - r) / 12


def ring_loft(bm, rings, mat_fn, smooth=True, cap_start=True, cap_end=True):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order.
    `mat_fn(centre)` gives each face's material index from the face centre (a Vector), or pass an
    int. Returns the new faces."""
    fn = mat_fn if callable(mat_fn) else (lambda _c, m=mat_fn: m)
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    faces = []
    for r0, r1 in zip(verts, verts[1:]):
        n = max(len(r0), len(r1))
        if n == 1:
            continue
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            faces.append(bm.faces.new(face))
    if cap_start and len(verts[0]) > 2:
        faces.append(bm.faces.new(list(reversed(verts[0]))))
    if cap_end and len(verts[-1]) > 2:
        faces.append(bm.faces.new(verts[-1]))
    for f in faces:
        f.material_index = fn(f.calc_center_median())
        f.smooth = smooth
    return faces


def loft_x(bm, sections, sides=12, mat=0, smooth=True, y0=0.0, cap_start=True, cap_end=True):
    """A body of elliptical rings along +X: sections are (x, half_width_y, half_height_z, z_centre)
    in units, around the line y = y0. A zero-size section is a point (a nose)."""
    rings = []
    for x, w, h, z in sections:
        if w == 0 and h == 0:
            rings.append([(x, y0, z)])
            continue
        rings.append([(x, y0 + w * math.cos(2 * math.pi * (i + 0.5) / sides),
                       z + h * math.sin(2 * math.pi * (i + 0.5) / sides)) for i in range(sides)])
    return ring_loft(bm, rings, mat, smooth=smooth, cap_start=cap_start, cap_end=cap_end)


def ellipsoid(bm, centre, radii, segments=12, rings=6, mat=0, smooth=True):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    rx, ry, rz = radii
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * rx, cy + v.co.y * ry, cz + v.co.z * rz))
    new = list(set(bm.faces) - before)
    for f in new:
        f.material_index = mat
        f.smooth = smooth
    return new


def cone(bm, base, tip, radius, sides=6, mat=0, smooth=False):
    """A pointed cone from a round base centre to a tip (3D points)."""
    a, b = Vector(base), Vector(tip)
    axis = (b - a).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    ring = [tuple(a + radius * (math.cos(2 * math.pi * (i + 0.5) / sides) * u +
                                math.sin(2 * math.pi * (i + 0.5) / sides) * v)) for i in range(sides)]
    return ring_loft(bm, [ring, [tuple(b)]], mat, smooth=smooth)


def frustum(bm, x0, y0, x1, y1, z0, z1, inset=0.0, mat=0):
    """A box from (x0, y0, z0) to (x1, y1, z1) whose top face is inset by `inset` on every side
    (a bevelled block)."""
    bot = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]
    top = [(x0 + inset, y0 + inset, z1), (x1 - inset, y0 + inset, z1),
           (x1 - inset, y1 - inset, z1), (x0 + inset, y1 - inset, z1)]
    return ring_loft(bm, [bot, top], mat, smooth=False)


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


def mirror_x(obj):
    """Mirror an object's mesh about X = 0 in place (normals kept outward)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for v in bm.verts:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def run(name, build, file):
    """The usual main: build, export every model and, with -- --preview <png>, preview each.

    `build(sprite)` returns a list of (model_name, objects, sprites, frame_index) to export; the
    first is previewed at the --preview path, the others next to it as <model_name>.png."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites, _ in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        for k, (model, objects, _, fi) in enumerate(models):
            frame = sprite["frames"][fi]
            ref = root / "reference" / "models" / name / frame["image"]
            path = out if k == 0 else out.parent / f"{model}.png"
            common.render_preview(objects, str(path), ref, size=frame["size"])
    return sprite


# --- newsha-161 / newsha-163: the two halves of a grey pod ---------------------------------------

def build_pod(sprite, name, nose=1):
    """One half of the grey pod pair (newsha-163 has its nose to the right, nose=1; newsha-161 is
    its mirror image, nose=-1). A body of revolution lying across the screen: a hub against the
    inner tile edge, a ringed light-grey collar, then a cone tapering to the nose, with a dark
    glass canopy on its upper (+Y) flank and a light ridge along its crest.

    Built in newsha-163's sprite coordinates (pixel edges: hub at columns 0-1, nose at 18) and
    mirrored for nose=-1 (newsha-161's column c is newsha-163's column 23 - c)."""
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(105, metallic=0.55, roughness=0.4),  # 0 grey hull
        pal(109, metallic=0.6, roughness=0.3),  # 1 light panels
        pal(101, metallic=0.5, roughness=0.5),  # 2 dark grooves
        pal(98, metallic=0.7, roughness=0.12),  # 3 dark glass canopy
        pal(107, metallic=0.6, roughness=0.3),  # 4 crest ridge, rim
        pal(10, metallic=0.75, roughness=0.3),  # 5 grey hub
        pal(116, metallic=0.3, roughness=0.4, emission_strength=1.5),  # 6 red hub lights
        pal(110, metallic=0.4, roughness=0.1),  # 7 glint on the glass
    ]
    HULL, BAND, GROOVE, GLASS, RIDGE, HUB, RED, GLINT = range(8)
    k = 0.45  # half height / half width of the body's cross-section
    bm = bmesh.new()

    def x(e):
        return ex(e)

    # The hull: (pixel edge along X, half width px).
    hull = [(0.9, 5.4), (1.6, 6.0), (3.0, 6.8), (3.3, 7.8), (6.0, 8.0), (9.0, 7.8), (10.5, 7.1),
            (12.0, 6.3), (13.5, 5.0), (15.5, 3.0), (17.2, 1.2), (18.1, 0.0)]

    def hull_mat(c):
        cx_px = c.x * 12 + 12
        if c.z > 0 and abs(c.y) < 0.9 * PX and 3.0 < cx_px < 13.5:
            return RIDGE  # the bright line along the crest (row 14)
        if c.y > 0.02 and cx_px > 9.0:
            return GLASS  # canopy on the upper flank (columns 9-16, rows 7-13)
        if c.y > 0.02 and 4.9 < cx_px < 6.1:
            return GROOVE  # the groove between the light panels (column 5)
        if c.y > 0.02 and 3.0 < cx_px < 9.0:
            return BAND  # light panels on the upper flank (columns 3-4 and 6-8, rows 6-13)
        return HULL

    sections = []
    for e, w in hull:
        sections.append((x(e), w * PX, w * k * PX, 0.0) if w else (x(e), 0, 0, 0.0))
        if e == 3.3:  # extra rings so the groove's edges (columns 4.9-6.1) are crisp
            for e2 in (4.9, 6.1):
                sections.append((x(e2), 7.95 * PX, 7.95 * k * PX, 0.0))
    sections.sort(key=lambda s: s[0])
    loft_x(bm, sections, sides=16, mat=hull_mat)

    # Rim ring behind the collar (column 1) and the groove in front of it (column 2).
    loft_x(bm, [(x(1.0), 6.2 * PX, 6.2 * k * PX, 0.0), (x(2.0), 6.2 * PX, 6.2 * k * PX, 0.0)], sides=16, mat=RIDGE)
    loft_x(bm, [(x(2.0), 5.9 * PX, 5.9 * k * PX, 0.0), (x(3.0), 6.1 * PX, 6.1 * k * PX, 0.0)], sides=16, mat=GROOVE)

    # Hub against the inner edge (column 0, rows 9-18) with red lights at its ends.
    loft_x(bm, [(x(0.0), 4.6 * PX, 0.17, 0.0), (x(1.0), 4.8 * PX, 0.18, 0.0)], sides=12, mat=HUB)
    ellipsoid(bm, (px(0.5), row(9.4), 0.0), (0.8 * PX, 1.0 * PX, 0.08), mat=RED, segments=8, rings=4)
    ellipsoid(bm, (px(0.5), row(17.6), 0.0), (0.8 * PX, 1.2 * PX, 0.08), mat=RED, segments=8, rings=4)

    # Glint on the glass (column 11, row 9): on the canopy surface.
    w_here, y_here = 6.6, 13.5 - 9.0
    z_here = w_here * k * PX * math.sqrt(max(0.0, 1 - (y_here / w_here) ** 2))
    ellipsoid(bm, (px(11), row(9), z_here), (0.7 * PX, 0.7 * PX, 0.025), mat=GLINT, segments=8, rings=4)

    obj = to_object(name, bm, mats, coll)
    if nose < 0:
        mirror_x(obj)
    return obj
