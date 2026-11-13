"""Helpers shared by batch b042's model scripts (newsh5 gun pods, falling fireball, small probe).

Coordinates: a `Grid` maps sprite (or assembly) pixel columns and rows to Blender X / Y for a
block of w x h pixels centred on the origin: X(c) and Y(r) give a pixel's centre (fractions
allowed), sprite up is +Y and one pixel is 1/12 unit.
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


class Grid:
    def __init__(self, w=24, h=28):
        self.w, self.h = w, h

    def X(self, c):
        return (c + 0.5 - self.w / 2) / 12

    def Y(self, r):
        return (self.h / 2 - (r + 0.5)) / 12


def _join(bm, rings, mat, smooth, cap_start=True, cap_end=True):
    """Faces between consecutive rings of BMVerts (a ring of one vert is a tip)."""
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        n = max(len(r0), len(r1))
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 2:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 2:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True, power=1.0):
    """A tube along a path of (col, row, z, half_width_px, half_height_units) in grid `g`. Rings
    stand perpendicular to the path in the XY plane; the width is measured across the path and the
    height along Z. A ring of zero size collapses to a point (a rounded or pointed end). `power` < 1
    squares the cross-section off (a superellipse)."""
    pts = [Vector((g.X(c), g.Y(r), z)) for c, r, z, _, _ in path]
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
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ca, sa = math.cos(a), math.sin(a)
            ca = math.copysign(abs(ca) ** power, ca)
            sa = math.copysign(abs(sa) ** power, sa)
            ring.append(bm.verts.new(pts[i] + side * (w * PX * ca) + up * (h * sa)))
        rings.append(ring)
    return _join(bm, rings, mat, smooth, cap_start, cap_end)


def loft_x(bm, g, row, sections, sides=12, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A body of revolution (flattened in Z) along +X, centred on pixel row `row`: sections are
    (col, half_width_px, half_height_units, z)."""
    rings = []
    y0 = g.Y(row)
    for c, w, h, z in sections:
        x = g.X(c)
        if w == 0 and h == 0:
            rings.append([bm.verts.new((x, y0, z))])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new((x, y0 - w * PX * math.cos(a), z + h * math.sin(a))))
        rings.append(ring)
    return _join(bm, rings, mat, smooth, cap_start, cap_end)


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, z_min=None):
    """An ellipsoid centred on a pixel; with z_min the vertices below it are flattened onto it
    (a dome with a flat base)."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        p = Vector((g.X(col) + v.co.x * rx_px * PX, g.Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
        if z_min is not None:
            p.z = max(p.z, z_min)
        v.co = p
    new = set(bm.faces) - before
    for f in new:
        f.material_index = mat
        f.smooth = True
    return new


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges (the top-left corner
    of pixel (c, r) is (c, r)), counter-clockwise seen from above."""
    pts = [(g.X(c - 0.5), g.Y(r - 0.5)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = smooth


def mirror_copy(bm, axis="y", about=0.0, faces=None):
    """Add a mirror image of `faces` (default: everything built so far) about the line X = about
    (axis "x") or Y = about (axis "y")."""
    if faces is None:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    else:
        faces = list(faces)
        verts = {v for f in faces for v in f.verts}
        edges = {e for f in faces for e in f.edges}
        geom = list(verts) + list(edges) + faces
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        if axis == "x":
            v.co.x = 2 * about - v.co.x
        else:
            v.co.y = 2 * about - v.co.y
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


def merged_sprite(root, names):
    """The first piece's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(root, names[0])
    for name in names[1:]:
        data["colors"].update(common.load_sprite(root, name)["colors"])
    return data


def composite_png(root, layout, out, size):
    """The pieces' first frames as one image (screen layout (name, cx, cy) relative to the
    assembly's centre), on a canvas of size*12 x size*14 px that render_preview expects."""
    import numpy as np
    W, H = size * 12, size * 14
    img = np.zeros((H, W, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + W / 2 - 12), int(cy + H / 2 - 14)
        for r, line in enumerate(frame["pixels"]):
            for c, v in enumerate(line):
                if v >= 0 and 0 <= y0 + r < H and 0 <= x0 + c < W:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def export_assembly(root, obj, layout, size):
    """Cut `obj` (built in assembly coordinates) into its pieces, export each with its own sprites
    and, with -- --preview <png>, preview the whole object and each piece (<piece>.png beside it)."""
    pieces = common.split_assembly(obj, layout)
    for name, _, _ in layout:
        data = common.load_sprite(root, name)
        common.export_sprite_model(root, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(root, layout, Path(tempfile.mkdtemp()) / "assembly.png", size)
        common.render_preview([obj], str(out), ref, size=size, view_px=480)
        for name, _, _ in layout:
            data = common.load_sprite(root, name)
            img = root / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
    return pieces


# --- the newsh5 gun pod (assemblies newsh5-43 + 45, and its mirror image newsh5-39 + 41) ------

PX = 1 / 12


def build_gunpod(sprite, name, flip=False):
    """The gun pod of level 4.12 (see the module doc). Built pointing along -X (the newsh5-39 + 41
    composite); flip=False mirrors it to point along +X (newsh5-43 + 45). Origin = the 48 x 28 px
    assembly's centre."""
    coll = common.reset_collection(name)
    mats, slot = [], {}

    def M(index, metallic, roughness):
        if index not in slot:
            slot[index] = len(mats)
            mats.append(common.palette_material(sprite, index, name, metallic=metallic, roughness=roughness))
        return slot[index]

    BULB = M(53, 0.45, 0.34)     # blue gun head
    FIN = M(55, 0.45, 0.36)      # blue fins and spikes
    FLANGE = M(7, 0.8, 0.32)     # grey flange behind the head
    GUN = M(4, 0.6, 0.28)        # dark grey barrel and shaft, corner stub
    CLAMP = M(5, 0.8, 0.3)      # grey clamp, hub, capsule caps
    ROD = M(59, 0.55, 0.28)      # light blue coolant rods
    ORB = M(54, 0.5, 0.16)       # glossy dark blue orb, capsule knobs
    FRAME = M(6, 0.8, 0.38)      # grey ring frame and lugs
    BAR = M(10, 0.8, 0.34)       # light grey clamp bar
    CAPS = M(56, 0.45, 0.32)     # blue capsule

    bm = bmesh.new()
    AX = 13.5  # axis row (edge coords)

    def P(c, r, z):
        return Vector(((c - 24) * PX, (14 - r) * PX, z * PX))

    def mono(pts):
        """Monotone cubic (pchip) through (x, y) points; returns f(x)."""
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        n = len(pts)
        d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
        m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else 2 / (1 / d[i - 1] + 1 / d[i]) for i in range(1, n - 1)] + [d[-1]]

        def f(x):
            x = min(max(x, xs[0]), xs[-1])
            i = max(0, min(n - 2, next((k for k in range(n - 1) if x <= xs[k + 1]), n - 2)))
            h = xs[i + 1] - xs[i]
            t = (x - xs[i]) / h
            return ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
                    + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1])
        return f

    def smooth01(t):
        t = min(max(t, 0.0), 1.0)
        return t * t * (3 - 2 * t)

    def rev(sections, sides=24, mat=0, row=AX, zfun=None, cap_start=True, cap_end=True, smooth=True):
        """Body of revolution along X: sections (c, half_width_px, half_height_px, z_px); a section of
        size 0 is a tip. zfun(c, y_px, z_px) -> z_px reshapes ring points (the barrel channel)."""
        rings = []
        for c, w, h, z in sections:
            if w == 0 and h == 0:
                rings.append([bm.verts.new(P(c, row, z))])
                continue
            ring = []
            for k in range(sides):
                a = 2 * math.pi * (k + 0.5) / sides
                y, zz = w * math.cos(a), h * math.sin(a)
                if zfun is not None:
                    zz = zfun(c, y, zz)
                ring.append(bm.verts.new(P(c, row - y, z + zz)))
            rings.append(ring)
        return _join(bm, rings, mat, smooth, cap_start, cap_end)

    def sw(path, sides=12, mat=0, power=1.0, smooth=True, cap_start=True, cap_end=True):
        """sweep in edge coords: path of (c, r, z_px, half_width_px, half_height_px)."""
        g = Grid(48, 28)
        return sweep(bm, g, [(c - 0.5, r - 0.5, z * PX, w, h * PX) for c, r, z, w, h in path],
                         sides=sides, mat=mat, smooth=smooth, cap_start=cap_start, cap_end=cap_end, power=power)

    def xloft(sections, sides=20, mat=0, power=0.55, smooth=True):
        """Superellipse sections across X: (c, r_top, r_bottom, z_lo_px, z_hi_px)."""
        rings = []
        for c, r0, r1, z0, z1 in sections:
            yc, hy = (r0 + r1) / 2, (r1 - r0) / 2
            zc, hz = (z0 + z1) / 2, (z1 - z0) / 2
            ring = []
            for k in range(sides):
                a = 2 * math.pi * (k + 0.5) / sides
                ca, sa = math.cos(a), math.sin(a)
                ca = math.copysign(abs(ca) ** power, ca)
                sa = math.copysign(abs(sa) ** power, sa)
                ring.append(bm.verts.new(P(c, yc - hy * ca, zc + hz * sa)))
            rings.append(ring)
        return _join(bm, rings, mat, smooth, True, True)

    def fin(profile, phi_deg, thick, mat, z0=0.0, chamfer=0.22, side=1):
        """A fin plate standing out of the axis at phi above the +Y (screen up) side: `profile` is
        its outline as (c, reach_px) where reach is the TOP-VIEW distance from the axis (so the fin
        lands on the sprite's silhouette); thick in px. Edges chamfered."""
        phi = math.radians(phi_deg)
        cp, sp = math.cos(phi), math.sin(phi)
        top, bot = [], []
        for c, reach in profile:
            s = reach / cp
            for n, lst in ((thick / 2, top), (-thick / 2, bot)):
                y = s * cp - n * sp
                z = z0 + s * sp + n * cp
                lst.append(bm.verts.new(P(c, AX - side * y, z)))
        if side < 0:
            top, bot = bot, top
        faces = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
        n = len(top)
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((top[j], top[i], bot[i], bot[j])))
        edges = list({e for f in faces for e in f.edges})
        res = bmesh.ops.bevel(bm, geom=edges, offset=chamfer * PX, segments=1, affect="EDGES", profile=0.5)
        faces = set(faces) | set(res.get("faces", []))
        out = []
        for f in faces:
            if f.is_valid:
                f.material_index = mat
                f.smooth = False
                out.append(f)
        return out

    def ell(c, r, z, rx, ry, rz, mat, seg=20, rings=10):
        g = Grid(48, 28)
        return ellipsoid(bm, g, c - 0.5, r - 0.5, z * PX, rx, ry, rz * PX, mat=mat, segments=seg, rings=rings)

    # ---------------- the gun head: blue bulb with the barrel in a dorsal channel ----------------
    wprof = mono([(2.95, 1.0), (3.2, 1.9), (3.6, 2.6), (4.5, 3.45), (5.5, 4.3), (6.5, 4.85), (7.5, 5.35),
                  (8.5, 5.65), (9.5, 5.95), (10.5, 6.3), (11.5, 6.45), (12.1, 6.45)])
    HZ = 0.78  # height / width of the head's sections
    BZ, BR = 2.9, 1.5  # barrel axis height and radius (px)
    GW = 1.95  # channel half-width (px)

    def channel(c, y, z):
        depth = 1.0 - smooth01((c - 8.4) / 1.5)  # the channel closes over the barrel's breech
        if depth <= 0 or z <= BZ:
            return z
        s = 1.0 - smooth01((abs(y) - GW) / 0.7)
        return z - depth * s * (z - BZ)

    secs = [(2.85, 0.0, 0.0, 0.0)]
    c = 2.95
    while c < 12.1:
        w = wprof(c)
        # a panel seam round the head at c = 10.9
        if 10.7 < c < 11.15:
            w -= 0.28
        secs.append((c, w, w * HZ, 0.0))
        c += 0.25 if c < 4 else (0.15 if 10.6 < c < 11.3 else 0.5)
    secs.append((12.1, 6.45, 6.45 * HZ, 0.0))
    secs.append((12.15, 5.6, 5.6 * HZ, 0.0))
    secs.append((12.15, 0.0, 0.0, 0.0))
    rev(secs, sides=40, mat=BULB, zfun=channel)
    # the barrel: muzzle at the nose, breech buried under the closed channel
    rev([(2.85, 0.0, 0.0, BZ), (2.85, 0.9, 0.9, BZ), (2.95, 1.5, 1.5, BZ), (3.4, 1.5, 1.5, BZ),
         (3.55, 1.35, 1.35, BZ), (3.75, 1.5, 1.5, BZ), (10.4, 1.5, 1.5, BZ), (10.4, 0.0, 0.0, BZ)],
        sides=14, mat=GUN)
    # bore
    rev([(2.8, 0.0, 0.0, BZ), (2.8, 0.55, 0.55, BZ), (2.9, 0.55, 0.55, BZ), (2.9, 0.0, 0.0, BZ)],
        sides=10, mat=GUN, smooth=True)
    # grey flange closing the head (col 12) and its back face down to the collar
    rev([(11.85, 6.1, 6.1 * HZ, 0.0), (12.0, 6.6, 6.6 * HZ, 0.0), (12.9, 6.6, 6.6 * HZ, 0.0),
         (13.0, 6.45, 6.45 * HZ, 0.0), (14.0, 6.35, 6.35 * HZ, 0.0), (14.7, 6.05, 6.05 * HZ, 0.0),
         (15.05, 5.4, 5.4 * HZ, 0.0), (15.3, 4.4, 4.4 * HZ, 0.0), (15.5, 3.4, 3.2, 0.0), (15.6, 3.3, 3.1, 0.0), (15.65, 0.0, 0.0, 0.0)],
        sides=36, mat=FLANGE, cap_start=True)
    # the seam between the flange ring and the aft cone
    rev([(12.88, 6.62, 6.62 * HZ, 0.0), (12.95, 6.25, 6.25 * HZ, 0.0), (13.02, 6.47, 6.47 * HZ, 0.0)],
        sides=36, mat=FLANGE, cap_start=False, cap_end=False)

    # ---------------- shaft, clamp, coolant rods ----------------
    SR = 2.4
    rev([(13.5, SR, SR, 0.0), (23.4, SR, SR, 0.0)], sides=20, mat=GUN)
    rev([(15.4, 2.5, 2.5, 0.0), (15.55, 2.75, 2.75, 0.0), (16.2, 2.75, 2.75, 0.0), (16.35, 2.5, 2.5, 0.0)],
        sides=20, mat=CLAMP)
    for dy in (1.05, -1.05):
        zr = math.sqrt(max(SR * SR - dy * dy, 0)) - 0.15
        rev([(16.25, 0.0, 0.0, zr), (16.3, 0.42, 0.42, zr), (16.45, 0.62, 0.62, zr), (22.2, 0.62, 0.62, zr),
             (22.35, 0.42, 0.42, zr), (22.4, 0.0, 0.0, zr)], sides=10, mat=ROD, row=AX - dy)
    # rod saddles on the clamp side and at the hub
    for cc in (18.9,):
        rev([(cc - 0.3, SR + 0.05, SR + 0.05, 0.0), (cc - 0.2, SR + 0.3, SR + 0.3, 0.0),
             (cc + 0.2, SR + 0.3, SR + 0.3, 0.0), (cc + 0.3, SR + 0.05, SR + 0.05, 0.0)], sides=20, mat=CLAMP)

    # ---------------- hub and orb ----------------
    rev([(21.55, 2.45, 2.45, 0.0), (21.95, 3.4, 3.4, 0.0), (23.0, 3.45, 3.45, 0.0), (23.15, 3.25, 3.25, 0.0),
         (23.3, 3.45, 3.45, 0.0), (24.5, 3.45, 3.45, 0.0), (24.9, 3.0, 3.0, 0.0), (24.9, 0.0, 0.0, 0.0)],
        sides=28, mat=CLAMP)
    rev([(21.5, 0.0, 0.0, 0.0), (21.5, 2.0, 2.0, 0.0), (21.6, 2.45, 2.45, 0.0)], sides=28, mat=CLAMP,
        cap_end=False)
    ell(27.35, AX, 0.0, 3.85, 3.85, 3.7, ORB, seg=28, rings=14)

    # ---------------- upper half (mirrored about the axis) ----------------
    upper = set()
    # X-fins on the shaft (upper-left pair seen from above; the lower pair hides under them)
    for phi in (36.0, -36.0):
        for sd in (1, -1):
            fin([(15.0, 2.0), (17.75, 2.0), (17.75, 5.1), (17.45, 5.45), (15.45, 5.45), (15.0, 5.0)],
                phi, 1.25, FIN, side=sd)
            fin([(17.9, 2.0), (21.0, 2.0), (21.0, 3.0), (19.8, 4.5), (18.3, 4.5), (17.9, 4.1)],
                phi, 1.15, FIN, side=sd)
    # ring frame: diagonal from the hub up into the top arm
    upper.update(sw([(23.4, 10.6, 0.0, 1.15, 1.55), (24.2, 9.5, 0.0, 1.25, 1.6), (25.3, 8.4, 0.0, 1.2, 1.6),
                     (26.25, 7.35, 0.0, 1.1, 1.6), (27.0, 6.5, 0.0, 1.0, 1.6), (27.8, 6.05, 0.0, 1.0, 1.6),
                     (30.0, 6.0, 0.0, 1.0, 1.6), (33.0, 6.0, 0.0, 1.0, 1.6), (35.4, 6.0, 0.0, 1.0, 1.6)],
                    sides=16, mat=FRAME, power=0.55))
    # gusset in the inner corner of the arm and the bar
    upper.update(sw([(32.6, 6.4, 0.0, 0.0, 0.0), (32.9, 6.55, 0.0, 0.7, 1.2), (34.0, 7.3, 0.0, 1.0, 1.4),
                     (35.1, 8.6, 0.0, 0.7, 1.4), (35.4, 9.2, 0.0, 0.0, 0.0)], sides=12, mat=FRAME, power=0.6))
    # light grey clamp bar down the right side, round the corner
    upper.update(sw([(36.0, 5.15, 0.0, 0.0, 0.0), (36.0, 5.2, 0.0, 0.8, 1.2), (36.0, 5.45, 0.0, 1.0, 1.7),
                     (36.0, 7.0, 0.0, 1.0, 1.75), (36.0, 13.5, 0.0, 1.0, 1.75)],
                    sides=16, mat=BAR, power=0.55, cap_end=False))
    # lug on the arm
    upper.update(xloft([(22.95, 3.6, 4.9, -1.1, 1.1), (23.25, 3.0, 5.0, -1.8, 1.8), (24.0, 2.2, 5.0, -2.1, 2.1),
                        (25.1, 2.2, 5.05, -2.1, 2.1), (25.9, 2.2, 5.9, -2.1, 2.1),
                        (28.9, 2.2, 6.0, -2.1, 2.1), (29.6, 3.0, 6.0, -2.0, 2.0), (30.35, 4.05, 6.0, -1.8, 1.8),
                        (30.8, 4.9, 6.0, -1.4, 1.4)], sides=24, mat=FRAME))
    # machined face on the lug: a raised boss with a pin
    upper.update(sw([(26.6, 3.4, 2.0, 0.0, 0.0), (26.6, 3.45, 2.0, 0.9, 0.35), (26.6, 4.6, 2.0, 0.9, 0.35),
                     (26.6, 4.65, 2.0, 0.0, 0.0)], sides=12, mat=GUN))
    # forward spike out of the lug (row 4)
    upper.update(sw([(26.2, 4.5, 0.2, 0.75, 0.75), (23.6, 4.5, 0.2, 0.7, 0.7), (22.2, 4.5, 0.2, 0.55, 0.55),
                     (20.85, 4.5, 0.2, 0.0, 0.0)], sides=10, mat=FIN))
    # grey stub at the corner (row 4, cols 34-36)
    upper.update(sw([(35.6, 5.8, 0.4, 1.3, 1.2), (35.6, 4.5, 0.4, 1.3, 1.15), (35.6, 4.15, 0.4, 1.0, 0.85),
                     (35.6, 4.0, 0.4, 0.0, 0.0)], sides=14, mat=GUN, power=0.7))
    # capsule: grey cap and the knob over it
    CX = 39.8
    upper.update(sw([(CX, 6.8, 0.0, 0.0, 0.0), (CX, 6.82, 0.0, 2.55, 2.45), (CX, 7.08, 0.0, 3.05, 2.95),
                     (CX, 7.85, 0.0, 3.1, 3.0), (CX, 7.95, 0.0, 2.85, 2.75), (CX, 8.05, 0.0, 3.1, 3.0),
                     (CX, 8.6, 0.0, 3.1, 3.0), (CX, 8.8, 0.0, 2.85, 2.75),
                     (CX, 8.95, 0.0, 2.4, 2.3), (CX, 10.05, 0.0, 2.4, 2.3), (CX, 10.1, 0.0, 0.0, 0.0)],
                    sides=28, mat=CLAMP))
    # end face boss of the cap
    upper.update(sw([(CX, 6.6, 0.0, 0.0, 0.0), (CX, 6.62, 0.0, 1.3, 1.25), (CX, 6.9, 0.0, 1.4, 1.35)],
                    sides=16, mat=GUN, cap_end=False))
    upper.update(ell(38.15, 6.1, 0.9, 1.2, 1.0, 1.2, ORB, seg=12, rings=6))
    # capsule body half (blue), with a raised seam band
    upper.update(sw([(CX, 9.9, 0.0, 2.15, 2.05), (CX, 10.45, 0.0, 2.35, 2.25), (CX, 10.95, 0.0, 2.9, 2.8),
                     (CX, 11.35, 0.0, 3.05, 2.95), (CX, 13.5, 0.0, 3.1, 3.0)], sides=28, mat=CAPS,
                    cap_start=False, cap_end=False))

    mirror_copy(bm, "y", (14 - AX) * PX, faces=upper)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)

    if not flip:
        bmesh.ops.scale(bm, vec=(-1, 1, 1), verts=bm.verts)
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return to_object(name, bm, mats, coll)


def split_shell(shell, layout, coll):
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(shell.data)
        bmesh.ops.transform(bm, matrix=shell.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in shell.data.materials:
            me.materials.append(m)
        me.shade_smooth()
        o = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(o)
        o["tyrian_outline"] = True
        out[name] = o
    return out



def export_gunpod(root, obj, layout, flip):
    """Cut the whole pod into its two pieces, make the outline shell from a sealed pre-cull copy of
    the whole (islands="outer", D189), cut it at the piece seam, and export each piece with its
    shell (common.export_sprite_model)."""
    coll = obj.users_collection[0]
    pieces = common.split_assembly(obj, layout, coll)
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    whole = common.outline_shell(sealed, coll, voxel=0.012, faces=4000, smooth=5, inside=0.005, islands="outer")
    bpy.data.objects.remove(sealed, do_unlink=True)
    cut = split_shell(whole, layout, coll)
    bpy.data.objects.remove(whole, do_unlink=True)
    for name, _, _ in layout:
        if not len(cut[name].data.polygons):
            print("WARNING empty outline", name)
        data = common.load_sprite(root, name)
        common.export_sprite_model(root, [pieces[name], cut[name]], f"enemies/{name}", data["sprites"])
    return pieces
