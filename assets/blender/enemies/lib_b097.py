"""Helpers shared by the b097 model scripts (newshc.shp ground pieces). Not a model itself:
tools/build-models.sh skips lib_ files."""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


def X(c, w=24):
    """Sprite column (pixel centre, fractions allowed) to Blender X."""
    return (c + 0.5 - w / 2) * PX


def Y(r, h=28):
    """Sprite row (pixel centre, fractions allowed) to Blender Y: sprite up is +Y."""
    return (h / 2 - (r + 0.5)) * PX


def XE(c, w=24):
    """Left edge of sprite column c."""
    return (c - w / 2) * PX


def YE(r, h=28):
    """Top edge of sprite row r."""
    return (h / 2 - r) * PX


def snapshot(bm):
    """The faces and verts that exist now; new_faces/new_verts give what was added since. (Index
    slicing is unreliable once anything has been deleted, as bmesh reuses freed slots.)"""
    return set(bm.faces), set(bm.verts)


def new_faces(bm, snap):
    return [f for f in bm.faces if f not in snap[0]]


def new_verts(bm, snap):
    return [v for v in bm.verts if v not in snap[1]]


def _tag(bm, snap, mat, smooth):
    for f in new_faces(bm, snap):
        f.material_index = mat
        f.smooth = smooth


def box(bm, x0, y0, x1, y1, z0, z1, mat=0, smooth=False):
    """An axis-aligned box in units."""
    snap = snapshot(bm)
    common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1 - z0, z=(z0 + z1) / 2)
    _tag(bm, snap, mat, smooth)


def pbox(bm, c0, r0, c1, r1, z0, z1, mat=0, w=24, h=28, smooth=False):
    """A box covering sprite columns c0..c1 and rows r0..r1 (inclusive, whole pixels)."""
    box(bm, XE(c0, w), YE(r1 + 1, h), XE(c1 + 1, w), YE(r0, h), z0, z1, mat, smooth)


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    """Extrude an outline of (x, y) units (counter-clockwise from above) from z0 to z1."""
    snap = snapshot(bm)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2)
    _tag(bm, snap, mat, smooth)


def pprism(bm, outline, z0, z1, mat=0, w=24, h=28, smooth=False):
    """Like prism, but the outline is (column, row) pixel *edges* (col 0 = left edge of the sprite)."""
    prism(bm, [(XE(c, w), YE(r, h)) for c, r in outline], z0, z1, mat, smooth)


def mask_plate(bm, pixels, keep, z0, z1, mat=0, w=24, h=28):
    """Boxes covering every pixel for which keep(row, col, value) is true: runs along each row,
    merged down the rows where the same run repeats."""
    runs = {}
    for r, line in enumerate(pixels):
        c = 0
        while c < len(line):
            if keep(r, c, line[c]):
                c0 = c
                while c < len(line) and keep(r, c, line[c]):
                    c += 1
                runs.setdefault((c0, c - 1), []).append(r)
            else:
                c += 1
    for (c0, c1), rows in runs.items():
        rows.sort()
        r0 = prev = rows[0]
        for r in rows[1:] + [None]:
            if r is not None and r == prev + 1:
                prev = r
                continue
            pbox(bm, c0, r0, c1, prev, z0, z1, mat, w, h)
            if r is not None:
                r0 = prev = r


def sweep(bm, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True, up=(0, 0, 1)):
    """A tube along a 3D path of (x, y, z, half_width, half_height) in units. Rings stand
    perpendicular to the path; width is across the path, height along the ring's `up`.
    A ring of zero size collapses to a point."""
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
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * math.cos(a)) + u * (hh * math.sin(a))))
        rings.append(ring)
    snap = snapshot(bm)
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
    _tag(bm, snap, mat, smooth)


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=16, rings=8, dome=False, power=1.0):
    """An ellipsoid (units) centred at (x, y, z); dome=True keeps only the upper half, its flat
    base at z (closed). power < 1 squares the outline off (a superellipse seen from above)."""
    snap = snapshot(bm)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    verts = res["verts"]
    if dome:  # rings must be even so there's an equator ring at z = 0
        below = [v for v in verts if v.co.z < -1e-4]
        verts = [v for v in verts if v.co.z >= -1e-4]
        bmesh.ops.delete(bm, geom=below, context="VERTS")
        edges = [e for e in bm.edges if e.is_boundary and all(v in set(verts) for v in e.verts)]
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    for v in verts:
        vx, vy = v.co.x, v.co.y
        if power != 1.0:
            rho = math.hypot(vx, vy)
            if rho > 1e-6:
                cx, cy = vx / rho, vy / rho
                vx = math.copysign(abs(cx) ** power, cx) * rho
                vy = math.copysign(abs(cy) ** power, cy) * rho
        v.co = Vector((x + vx * rx, y + vy * ry, z + v.co.z * rz))
    _tag(bm, snap, mat, True)


def mirror_x(bm, snap, axis=0.0):
    """Mirror everything built since snapshot(bm) about x = axis (adds a copy)."""
    verts = set(new_verts(bm, snap))
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = [e for e in bm.edges if all(v in verts for v in e.verts)]
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis - v.co.x
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


def palette(sprite, tag):
    return lambda i, **kw: common.palette_material(sprite, i, tag, **kw)


def preview_args():
    if "--preview" in sys.argv:
        return Path(sys.argv[sys.argv.index("--preview") + 1])
    return None


def preview(root, objs, out, sprite, frame=0):
    """Render the model beside its sprite (first frame of the frames it covers)."""
    f = sprite["frames"][frame]
    ref = Path(root) / "reference" / "models" / sprite["name"] / f["image"]
    common.render_preview(objs, str(out), ref, size=f["size"])


def frames_arg():
    """--frames <png>: render every frame of the model beside its sprite (common.render_frame_previews)."""
    if "--frames" in sys.argv:
        return Path(sys.argv[sys.argv.index("--frames") + 1])
    return None


def frame_previews(root, objs, out, sprite, indices=None):
    """common.render_frame_previews for the frames in `indices` (all of the sprite's by default)."""
    frames = [f for f in sprite["frames"] if indices is None or f["index"] in indices]
    common.render_frame_previews(objs, str(out), {**sprite, "frames": frames}, root)


def subset(sprite, indices):
    """sprite.json `sprites` restricted to the given frame indices (sheet frame numbers)."""
    out = []
    for s in sprite["sprites"]:
        frames = [i for i in s["frames"] if i in indices]
        if frames:
            out.append({**s, "frames": frames})
    return out


def loft_x(bm, sections, mat=0, smooth=False):
    """Loft a profile along +X: sections are (x, [(y, z), ...]) with the same number of points,
    the profile counter-clockwise seen from +X. Both ends are capped."""
    rings = [[bm.verts.new((x, y, z)) for y, z in prof] for x, prof in sections]
    snap = snapshot(bm)
    n = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r1[i], r1[j], r0[j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    _tag(bm, snap, mat, smooth)


def translate(bm, snap, dx=0.0, dy=0.0, dz=0.0):
    """Move every vertex added since snapshot(bm)."""
    for v in new_verts(bm, snap):
        v.co.x += dx
        v.co.y += dy
        v.co.z += dz


def scale_profile(prof, s, yc, zc=0.0, sz=None):
    """Shrink a (y, z) profile toward (yc, zc)."""
    sz = s if sz is None else sz
    return [(yc + (y - yc) * s, zc + (z - zc) * sz) for y, z in prof]


# --- newshc.shp blue turret base (newshc-155 and newshc-163) ------------------------------------

def turret_base(bm, M, corner_mat, centre_rod_top=16):
    """The shared part of newshc-155/163, in the piece's own coordinates (24x28 block): a blue hood
    of two lobes at the back (rows 2-9), a grey housing across the middle (rows 10-17) with a dark
    port on each side of its sloped front, and a grey U-shaped bracket on the ground below it
    (rows 14-24, columns 8-15). M maps part names to material slots; corner_mat is the slot of
    the strips on the hood's outer corners (green on 155, blue on 163)."""
    # Hood: two lobes meeting at the centre, on a dark skirt.
    LX, LY, LZ, RX, RY, RZ = X(5.6), Y(5.8), 0.04, 5.6 * PX, 4.3 * PX, 0.36

    def on_lobe(x, y, lift):
        d = 1 - ((abs(x) - abs(LX)) / RX) ** 2 - ((y - LY) / RY) ** 2
        return max(LZ + RZ * max(d, 0.0) ** 0.5, 0.12) + lift

    pbox(bm, 0, 5, 23, 10, 0.0, 0.12, M["skirt"])
    for side in (-1, 1):
        ellipsoid(bm, side * LX, LY, LZ, RX, RY, RZ, M["hood"], segments=16, rings=8, dome=True, power=0.7)
        # Strip over the lobe's outer corner (columns 1-5, rows 3-8).
        pts = [(6.0, 2.8, 0.0), (5.0, 3.4, 1.6), (3.4, 4.7, 2.3), (2.3, 6.3, 2.0), (1.6, 7.9, 1.4), (1.3, 8.9, 0.0)]
        sweep(bm, [(-side * X(c), Y(r), on_lobe(X(c), Y(r), -0.005), w * PX, 0.035 if w else 0.0)
                   for c, r, w in pts], sides=8, mat=corner_mat)
        # Highlight ridge along the lobe's crest.
        pts = [(6.0, 3.0, 0.0), (6.1, 3.8, 1.0), (6.3, 6.0, 1.1), (6.5, 7.6, 0.0)]
        sweep(bm, [(-side * X(c), Y(r), on_lobe(X(c), Y(r), 0.0), w * PX, 0.02 if w else 0.0)
                   for c, r, w in pts], sides=6, mat=M["hood_hi"])
    M["_on_lobe"] = on_lobe

    # Grey housing: a block with a flat top at the back and a slope down to the front, its middle
    # (columns 8-15) cut back where the bracket hangs.
    def prof(front, top_front=12.6, front_z=0.04):
        return [(YE(9.6), 0.0), (YE(front), 0.0), (YE(front), front_z), (YE(top_front), 0.29),
                (YE(10.3), 0.32), (YE(9.6), 0.27)]
    full, short = prof(18.0), prof(14.6, 12.2, 0.16)
    yc = YE(13.5)
    loft_x(bm, [(XE(0.6), scale_profile(full, 0.7, yc, 0.12)), (XE(1.4), full), (XE(7.6), full),
                (XE(7.6), short), (XE(16.4), short), (XE(16.4), full), (XE(22.6), full),
                (XE(23.4), scale_profile(full, 0.7, yc, 0.12))], mat=M["housing"])
    # Bright top edge of the housing.
    sweep(bm, [(XE(1.5), YE(11.0), 0.315, 0.9 * PX, 0.02), (XE(22.5), YE(11.0), 0.315, 0.9 * PX, 0.02)],
          sides=6, mat=M["housing_hi"])
    # Dark ports on the sloped front (columns 3-6 and 17-20, rows 14-16).
    n = Vector((0.0, -0.6, 1.0)).normalized()
    for side in (-1, 1):
        p = Vector((side * X(4.6), Y(15.0), 0.0))
        t = (YE(12.6) - p.y) / (YE(12.6) - YE(18.0))
        p.z = 0.29 + (0.04 - 0.29) * t
        a, b = p - n * 0.02, p + n * 0.02
        sweep(bm, [(a.x, a.y, a.z, 1.9 * PX, 1.5 * PX), (b.x, b.y, b.z, 1.9 * PX, 1.5 * PX)], sides=10,
              mat=M["port"], up=(0, 1, 0))

    # Bracket on the ground: rails, a bottom bar, a top bar and a centre rod over a dark floor.
    pbox(bm, 9, 15, 14, 21, 0.0, 0.02, M["floor"])
    for c in (8, 15):
        pbox(bm, c, 14, c, 22, 0.0, 0.13, M["rail"])
    pprism(bm, [(8, 21), (16, 21), (16, 23), (15, 24), (9, 24), (8, 23)], 0.0, 0.11, M["rail"])
    pbox(bm, 9, 15, 14, 15, 0.03, 0.11, M["bar"])
    sweep(bm, [(0.0, YE(centre_rod_top), 0.05, 1.0 * PX, 0.05), (0.0, YE(21), 0.07, 1.0 * PX, 0.06)],
          sides=6, mat=M["rod"])
