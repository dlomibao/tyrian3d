"""Helpers shared by batch b052's models (build-models.sh skips lib_ files).

Coordinates are sprite pixel *edges* in a 24x28 block: column c runs from c to c + 1 and row r
from r to r + 1, so a pixel's centre is (c + 0.5, r + 0.5). X(c) and Y(r) turn them into Blender
units (sprite up is +Y, 1 px = 1/12 unit, the block's centre is the origin). Heights in pixels go
through P().

Several helpers are adapted from lib_b002 (loft, slab, dome) and lib_b004 (tube, mask_outline,
sample).
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

W, H = 24, 28


def X(c):
    """Sprite x (pixel edges) to Blender X."""
    return (c - W / 2) / 12


def Y(r):
    """Sprite y (pixel edges, down the sprite) to Blender Y."""
    return (H / 2 - r) / 12


def P(px):
    """Pixels to units."""
    return px / 12


def _ring_point(a, power):
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** power, c), math.copysign(abs(s) ** power, s)


def _bridge(bm, rings, sides, mat, cap_start, cap_end):
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat


def loft(bm, sections, sides=12, mat=0, power=1.0, cap_start=True, cap_end=True):
    """Loft rings along the sprite's rows. Each section is (row, col, half_w, half_h, z) with row
    and col in pixel edges and half_w, half_h, z in pixels. Zero half width and height is a tip.
    power < 1 squares the cross-section off."""
    rings = []
    for r, c, hw, hh, z in sections:
        y, x = Y(r), X(c)
        if hw == 0 and hh == 0:
            rings.append([bm.verts.new((x, y, P(z)))])
            continue
        ring = []
        for i in range(sides):
            u, v = _ring_point(2 * math.pi * (i + 0.5) / sides, power)
            ring.append(bm.verts.new((x + P(hw) * u, y, P(z) + P(hh) * v)))
        rings.append(ring)
    _bridge(bm, rings, sides, mat, cap_start, cap_end)


def loft_x(bm, sections, sides=12, mat=0, power=1.0, cap_start=True, cap_end=True):
    """Like loft but along the sprite's columns: sections are (col, row, half_h_in_y, half_h_in_z, z)."""
    rings = []
    for c, r, hw, hh, z in sections:
        x, y = X(c), Y(r)
        if hw == 0 and hh == 0:
            rings.append([bm.verts.new((x, y, P(z)))])
            continue
        ring = []
        for i in range(sides):
            u, v = _ring_point(2 * math.pi * (i + 0.5) / sides, power)
            ring.append(bm.verts.new((x, y - P(hw) * u, P(z) + P(hh) * v)))
        rings.append(ring)
    _bridge(bm, rings, sides, mat, cap_start, cap_end)


def tube(bm, points, radii, sides=8, mat=0, flat=1.0, cap=True):
    """A tube along a polyline of 3D points (units) with a radius per point (0 closes to a tip).
    `flat` squashes the cross-section vertically."""
    pts = [Vector(p) for p in points]
    rings = []
    for i, (p, rad) in enumerate(zip(pts, radii)):
        if rad == 0:
            rings.append([bm.verts.new(p)])
            continue
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t.normalize()
        side = t.cross(Vector((0, 0, 1)))
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        nup = side.cross(t).normalized()
        rings.append([bm.verts.new(p + side * math.cos(a) * rad + nup * math.sin(a) * rad * flat)
                      for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))])
    # tube's rings run the other way round from loft's, so bridge with flipped faces.
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                f = (r0[0], r1[k], r1[j])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f).material_index = mat
    if cap:
        if len(rings[0]) > 1:
            bm.faces.new(rings[0]).material_index = mat
        if len(rings[-1]) > 1:
            bm.faces.new(list(reversed(rings[-1]))).material_index = mat


def ellipsoid(bm, x, y, z, a, b, c, segments=12, rings=8, mat=0):
    """An ellipsoid centred on (x, y, z) units with semi-axes a, b, c (units), poles along Y."""
    rs = []
    for i in range(rings + 1):
        t = math.pi * i / rings
        yy = y - b * math.cos(t)
        if i in (0, rings):
            rs.append([bm.verts.new((x, yy, z))])
            continue
        s = math.sin(t)
        rs.append([bm.verts.new((x + a * s * math.cos(ang), yy, z + c * s * math.sin(ang)))
                   for ang in (2 * math.pi * (k + 0.5) / segments for k in range(segments))])
    _bridge(bm, rs, segments, mat, False, False)


def dome(bm, x, y, z, rx, ry, h, rings=4, sides=12, mat=0, bottom=True):
    """A half ellipsoid standing on the plane at height z (units), centre (x, y), radii rx, ry and
    height h (units). bottom closes its base."""
    loops = []
    for k in range(rings):
        t = (math.pi / 2) * k / rings
        loops.append([bm.verts.new((x + rx * math.cos(t) * math.cos(a), y + ry * math.cos(t) * math.sin(a),
                                    z + h * math.sin(t)))
                      for a in (2 * math.pi * i / sides for i in range(sides))])
    tip = bm.verts.new((x, y, z + h))
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((l0[i], l0[j], l1[j], l1[i])).material_index = mat
    for i in range(sides):
        bm.faces.new((loops[-1][i], loops[-1][(i + 1) % sides], tip)).material_index = mat
    if bottom:
        bm.faces.new(list(reversed(loops[0]))).material_index = mat


def torus(bm, x, y, z, R, r, major=12, minor=6, mat=0):
    """A torus lying flat (axis +Z) centred on (x, y, z) units."""
    rings = []
    for i in range(major):
        a = 2 * math.pi * i / major
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((x + (R + r * math.cos(b)) * ca, y + (R + r * math.cos(b)) * sa, z + r * math.sin(b)))
                      for b in (2 * math.pi * k / minor for k in range(minor))])
    for i in range(major):
        r0, r1 = rings[i], rings[(i + 1) % major]
        for k in range(minor):
            j = (k + 1) % minor
            bm.faces.new((r0[k], r1[k], r1[j], r0[j])).material_index = mat


def slab(bm, outline, z0, z1, mat=0, bevel=0.0):
    """Extrude an outline of (col, row) pixel-edge points between heights z0 and z1 (pixels).
    bevel (pixels) pulls the top face toward the centroid for a chamfered edge."""
    pts = [(X(c), Y(r)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    bottom = [bm.verts.new((x, y, P(z0))) for x, y in pts]
    if bevel:
        cx = sum(x for x, _ in pts) / len(pts)
        cy = sum(y for _, y in pts) / len(pts)
        top = []
        for x, y in pts:
            dx, dy = cx - x, cy - y
            d = math.hypot(dx, dy) or 1
            k = min(P(bevel) / d, 0.9)
            top.append(bm.verts.new((x + dx * k, y + dy * k, P(z1))))
    else:
        top = [bm.verts.new((x, y, P(z1))) for x, y in pts]
    bm.faces.new(top).material_index = mat
    bm.faces.new(list(reversed(bottom))).material_index = mat
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bottom[i], bottom[j], top[j], top[i])).material_index = mat


def box(bm, c0, r0, c1, r1, z0, z1, mat=0, bevel=0.0):
    """A box over pixel edges c0..c1, r0..r1 between heights z0..z1 (pixels)."""
    slab(bm, [(c0, r0), (c0, r1), (c1, r1), (c1, r0)], z0, z1, mat=mat, bevel=bevel)


def mirror_x_from(bm, start):
    """Duplicate the geometry added since vertex `start`, mirrored in X (faces flipped)."""
    bm.verts.ensure_lookup_table()
    verts = bm.verts[start:]
    faces = {f for v in verts for f in v.link_faces}
    vmap = {v: bm.verts.new((-v.co.x, v.co.y, v.co.z)) for v in verts}
    for f in faces:
        nf = bm.faces.new([vmap[v] for v in reversed(f.verts)])
        nf.material_index = f.material_index


def sample(pixels, x, y):
    """The palette index of the sprite pixel under Blender (x, y), or -1 outside / transparent."""
    c = int(math.floor(x * 12 + W / 2))
    r = int(math.floor(H / 2 - y * 12))
    if 0 <= r < len(pixels) and 0 <= c < len(pixels[0]):
        return pixels[r][c]
    return -1


def paint(bm, pixels, slot_of, faces=None, under_slot=None, min_nz=0.0):
    """Give each face (of `faces`, default all) the material slot of the sprite pixel under its
    centre (slot_of(index) -> slot, or None to leave it). Faces facing down (normal z < min_nz) get
    `under_slot` if given."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    for f in (faces if faces is not None else bm.faces):
        if f.normal.z < min_nz:
            if under_slot is not None:
                f.material_index = under_slot
            continue
        cen = f.calc_center_median()
        slot = slot_of(sample(pixels, cen.x, cen.y))
        if slot is not None:
            f.material_index = slot


def mask_outline(pixels, keep, inset=0.0):
    """The outline of the sprite pixels for which keep(index) is true, as a polygon (Blender XY,
    counter-clockwise) traced round the pixel corners and smoothed by corner cutting. Only the
    largest region is traced. `inset` (pixels) pulls it inward."""
    h, w = len(pixels), len(pixels[0])
    inside = lambda c, r: 0 <= r < h and 0 <= c < w and keep(pixels[r][c])  # noqa: E731
    edges = {}
    for r in range(h):
        for c in range(w):
            if not inside(c, r):
                continue
            if not inside(c, r - 1):
                edges[(c + 1, r)] = (c, r)
            if not inside(c, r + 1):
                edges[(c, r + 1)] = (c + 1, r + 1)
            if not inside(c - 1, r):
                edges[(c, r)] = (c, r + 1)
            if not inside(c + 1, r):
                edges[(c + 1, r + 1)] = (c + 1, r)
    loops, seen = [], set()
    for s in list(edges):
        if s in seen:
            continue
        loop, p = [], s
        while p not in seen and p in edges:
            seen.add(p)
            loop.append(p)
            p = edges[p]
        loops.append(loop)
    loop = max(loops, key=len)
    pts = [Vector(p) for p in loop]
    for _ in range(2):
        out = []
        n = len(pts)
        for i in range(n):
            p, q = pts[i], pts[(i + 1) % n]
            out.append(p * 0.75 + q * 0.25)
            out.append(p * 0.25 + q * 0.75)
        pts = out
    poly = [((p.x - w / 2) / 12, (h / 2 - p.y) / 12) for p in pts][::2]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    if area < 0:
        poly.reverse()
    if inset:
        out = []
        for i, (x, y) in enumerate(poly):
            ax, ay = poly[i - 1]
            bx, by = poly[(i + 1) % len(poly)]
            tx, ty = bx - ax, by - ay
            ln = math.hypot(tx, ty) or 1
            out.append((x - ty / ln * inset / 12, y + tx / ln * inset / 12))
        poly = out
    return poly


def run(name, build, file, frames=None, model=None):
    """Load the sprite, build, export (optionally only some frames, as model `model`) and preview
    against the first exported frame when the script was given `-- --preview <png>`.

    build(sprite, frame_index) returns the objects. `frames` lists frame numbers (indices into
    sprite["frames"]) the model covers; None means all."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    idx = list(range(len(sprite["frames"]))) if frames is None else frames
    objs = build(sprite, idx[0])
    if frames is None:
        sprites = sprite["sprites"]
    else:
        wanted = {(sprite["frames"][i]["sheet"], sprite["frames"][i]["index"]) for i in frames}
        sprites = []
        for s in sprite["sprites"]:
            fr = [f for f in s["frames"] if (s["sheet"], f) in wanted]
            if fr:
                sprites.append({**s, "frames": fr})
    model = model or name
    common.export_sprite_model(root, objs, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        f = sprite["frames"][idx[0]]
        ref = root / "reference" / "models" / name / f["image"]
        common.render_preview(objs, out, ref, size=f["size"])
    return objs
