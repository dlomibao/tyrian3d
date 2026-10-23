"""Helpers shared by batch b013's enemy scripts (build-models.sh skips lib_ modules).

- Grid: sprite (or assembly) pixel coordinates to Blender X/Y, and sampling the pixel under a point.
- mask_outline / pillow: a smooth outline traced round sprite pixels, and an inflated body over it.
- ellipsoid, tube, loft_x, box, mirror_x: simple solids.
- paint: give faces the material of the sprite pixel under them (seen from above).
- to_object, preview, composite_png: the usual output plumbing.
"""

import math
import struct
import sys
import zlib
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units


class Grid:
    """Pixel grid w x h px centred on the origin (plus an optional offset in units): column c,
    row r (pixel centre) map to X = (c + 0.5 - w/2)/12, Y = (h/2 - (r + 0.5))/12. Fractions allowed."""

    def __init__(self, w, h, pixels=None, ox=0.0, oy=0.0):
        self.w, self.h, self.pixels, self.ox, self.oy = w, h, pixels, ox, oy

    def x(self, c):
        return (c + 0.5 - self.w / 2) * U + self.ox

    def y(self, r):
        return (self.h / 2 - (r + 0.5)) * U + self.oy

    def col(self, x):
        return (x - self.ox) / U + self.w / 2 - 0.5

    def row(self, y):
        return self.h / 2 - 0.5 - (y - self.oy) / U

    def at(self, c, r):
        if self.pixels is None or not (0 <= r < self.h and 0 <= c < self.w):
            return -1
        return self.pixels[r][c]

    def sample(self, x, y, skip=(-1,), reach=1):
        """The palette index of the pixel under (x, y); pixels in `skip` are passed over for the
        nearest other pixel within `reach` pixels (None if there is none)."""
        c, r = int(round(self.col(x))), int(round(self.row(y)))
        for d in range(reach + 1):
            best = None
            for dr in range(-d, d + 1):
                for dc in range(-d, d + 1):
                    if max(abs(dr), abs(dc)) != d:
                        continue
                    v = self.at(c + dc, r + dr)
                    if v not in skip:
                        dist = dr * dr + dc * dc
                        if best is None or dist < best[0]:
                            best = (dist, v)
            if best:
                return best[1]
        return None


def mask_outline(grid, keep, rounds=2, inset=0.0):
    """The outline of the grid's pixels for which keep(index) is true (largest region), as a
    counter-clockwise Blender XY polygon traced round pixel corners and smoothed by corner cutting.
    `inset` (pixels) pulls it inward."""
    h, w = grid.h, grid.w
    inside = lambda c, r: 0 <= r < h and 0 <= c < w and keep(grid.pixels[r][c])  # noqa: E731
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
    pts = [Vector(p) for p in max(loops, key=len)]
    for _ in range(rounds):
        out = []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            out += [p * 0.75 + q * 0.25, p * 0.25 + q * 0.75]
        pts = out
    poly = [(grid.x(p.x - 0.5), grid.y(p.y - 0.5)) for p in pts][::2]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    if area < 0:
        poly.reverse()
    if inset:
        poly = inset_polygon(poly, inset * U)
    return poly


def inset_polygon(poly, d):
    """Move each vertex of a counter-clockwise polygon `d` units inward."""
    out = []
    for i, (x, y) in enumerate(poly):
        ax, ay = poly[i - 1]
        bx, by = poly[(i + 1) % len(poly)]
        tx, ty = bx - ax, by - ay
        ln = math.hypot(tx, ty) or 1
        out.append((x - ty / ln * d, y + tx / ln * d))
    return out


def resample(poly, n):
    """n points evenly spaced round a closed polygon."""
    segs = [(Vector(poly[i]), Vector(poly[(i + 1) % len(poly)])) for i in range(len(poly))]
    total = sum((b - a).length for a, b in segs)
    out, i, acc = [], 0, 0.0
    for k in range(n):
        t = total * k / n
        while acc + (segs[i][1] - segs[i][0]).length < t:
            acc += (segs[i][1] - segs[i][0]).length
            i += 1
        a, b = segs[i]
        ln = (b - a).length or 1
        p = a.lerp(b, (t - acc) / ln)
        out.append((p.x, p.y))
    return out


def pillow(bm, outline, centre, z0, top, bottom, rings=5, mat_index=0, power=1.0, bottom_rings=2):
    """An inflated body over an outline: rings shrink toward `centre` (x, y) while rising to `top`
    units above z0 (a rounded dome, sharper with power < 1) and sink to `bottom` below it. The
    outline should be star-shaped about the centre. Returns its first face index."""
    bm.faces.ensure_lookup_table()
    first = len(bm.faces)
    cx, cy = centre
    n = len(outline)

    def ring(s, z):
        return [bm.verts.new((cx + (x - cx) * s, cy + (y - cy) * s, z)) for x, y in outline]

    ups = []
    for k in range(rings):
        t = (math.pi / 2) * k / rings
        ups.append(ring(math.cos(t) ** power, z0 + top * math.sin(t)))
    apex = bm.verts.new((cx, cy, z0 + top))
    downs = [ups[0]]
    for k in range(1, bottom_rings + 1):
        t = (math.pi / 2) * k / (bottom_rings + 1)
        downs.append(ring(math.cos(t), z0 - bottom * math.sin(t)))
    base = bm.verts.new((cx, cy, z0 - bottom))
    for chain, tip, up in ((ups, apex, True), (downs, base, False)):
        for a, b in zip(chain, chain[1:]):
            for i in range(n):
                j = (i + 1) % n
                f = (a[i], a[j], b[j], b[i]) if up else (a[j], a[i], b[i], b[j])
                bm.faces.new(f).material_index = mat_index
        last = chain[-1]
        for i in range(n):
            j = (i + 1) % n
            f = (last[i], last[j], tip) if up else (last[j], last[i], tip)
            bm.faces.new(f).material_index = mat_index
    return first


def ellipsoid(bm, centre, radii, segments=16, rings=8, mat_index=0, bump=None):
    """A UV ellipsoid at `centre` with radii (rx, ry, rz), poles on Z. Returns its first face."""
    bm.faces.ensure_lookup_table()
    first = len(bm.faces)
    cx, cy, cz = centre
    rx, ry, rz = radii
    top = bm.verts.new((cx, cy, cz + rz))
    bot = bm.verts.new((cx, cy, cz - rz))
    rs = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        ring = []
        for j in range(segments):
            th = 2 * math.pi * j / segments
            d = (math.sin(phi) * math.cos(th), math.sin(phi) * math.sin(th), math.cos(phi))
            s = bump(*d) if bump else 1
            ring.append(bm.verts.new((cx + rx * d[0] * s, cy + ry * d[1] * s, cz + rz * d[2] * s)))
        rs.append(ring)
    for j in range(segments):
        k = (j + 1) % segments
        bm.faces.new((top, rs[0][j], rs[0][k])).material_index = mat_index
        bm.faces.new((bot, rs[-1][k], rs[-1][j])).material_index = mat_index
    for a, b in zip(rs, rs[1:]):
        for j in range(segments):
            k = (j + 1) % segments
            bm.faces.new((a[j], b[j], b[k], a[k])).material_index = mat_index
    return first


def tube(bm, points, sides=8, mat_index=0, cap_start=True, cap_end=True, flat=1.0):
    """A loft along any path: points are ((x, y, z), radius); radius 0 makes a point. Rings stand
    perpendicular to the path; `flat` scales their height (for paths in the XY plane)."""
    pts = [(Vector(p), r) for p, r in points]
    rings = []
    for i, (p, r) in enumerate(pts):
        a = pts[max(0, i - 1)][0]
        b = pts[min(len(pts) - 1, i + 1)][0]
        d = (b - a).normalized()
        ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(ref).normalized()
        w = d.cross(u).normalized()
        if r == 0:
            rings.append([bm.verts.new(p)])
            continue
        ring = []
        for k in range(sides):
            a_ = 2 * math.pi * (k + 0.5) / sides
            off = r * math.cos(a_) * u + r * math.sin(a_) * w
            off.z *= flat
            ring.append(bm.verts.new(p + off))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                face = (r0[k], r0[j], r1[0])
            else:
                face = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(face).material_index = mat_index
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat_index


def loft_x(bm, sections, y=0.0, z=0.0, sides=12, mat_index=0, cap_start=True, cap_end=True):
    """common.loft along +X instead of +Y: sections are (x, half_across_y, half_height, z_offset)."""
    start = len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat_index, cap_start=cap_start, cap_end=cap_end)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        across, along = v.co.x, v.co.y
        v.co.x, v.co.y = along, y - across
        v.co.z += z


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0):
    """An axis-aligned box between (x0, y0, z0) and (x1, y1, z1)."""
    common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def prism(bm, outline, z0, z1, mat_index=0):
    """Extrude an XY outline (any winding) from z0 up to z1."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    if area < 0:
        outline = list(reversed(outline))
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def mirror_x(bm, start, axis=0.0):
    """Duplicate the geometry built since vertex index `start` mirrored about X = axis, keeping each
    face's material and smooth flag."""
    bm.verts.ensure_lookup_table()
    src = set(bm.verts[start:])
    copies = {v: bm.verts.new((2 * axis - v.co.x, v.co.y, v.co.z)) for v in list(src)}
    for f in [f for f in bm.faces if all(v in src for v in f.verts)]:
        nf = bm.faces.new([copies[v] for v in reversed(f.verts)])
        nf.material_index = f.material_index
        nf.smooth = f.smooth


def set_smooth(bm, first_face, smooth=True):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        f.smooth = smooth


def nfaces(bm):
    bm.faces.ensure_lookup_table()
    return len(bm.faces)


def paint(bm, first_face, grid, slot_for, min_nz=-2.0, reach=1, skip=(-1,)):
    """Set the material of every face added since `first_face` from the sprite pixel under its
    centre: slot_for(index) -> slot or None to leave it. Faces with normal z < min_nz are left."""
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    for f in bm.faces[first_face:]:
        if f.normal.z < min_nz:
            continue
        c = f.calc_center_median()
        idx = grid.sample(c.x, c.y, skip=skip, reach=reach)
        if idx is None:
            continue
        slot = slot_for(idx)
        if slot is not None:
            f.material_index = slot


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def preview_arg():
    return sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None


def preview(root, objs, sprite, frame=0):
    """Render the --preview PNG if the script was given one."""
    out = preview_arg()
    if out:
        f = sprite["frames"][frame]
        ref = Path(root) / "reference" / "models" / sprite["name"] / f["image"]
        common.render_preview(objs, out, ref, size=f["size"])


def merged_sprite(root, names):
    """The first piece's sprite.json with the colours of every piece merged in."""
    data = common.load_sprite(root, names[0])
    for n in names[1:]:
        data["colors"].update(common.load_sprite(root, n)["colors"])
    return data


def write_png(path, rows):
    """Write an RGBA image (rows of (r, g, b, a) 0-255 tuples, top row first) as a PNG."""
    h, w = len(rows), len(rows[0])
    raw = b"".join(b"\0" + bytes(v for px in row for v in px) for row in rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def composite_png(pieces, w, h, path, scale=4):
    """Several sprite frames on one w x h px canvas (pieces: (pixels, colors, x0, y0)) as a PNG."""
    grid = [[None] * w for _ in range(h)]
    for pixels, colors, x0, y0 in pieces:
        for r, row in enumerate(pixels):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < h and 0 <= x0 + c < w:
                    grid[y0 + r][x0 + c] = (*colors[str(v)], 255)
    rows = []
    for row in grid:
        line = []
        for p in row:
            line.extend([p or (0, 0, 0, 0)] * scale)
        rows.extend([line] * scale)
    write_png(path, rows)
    return path


def combined_pixels(pieces, w, h):
    """One w x h pixel grid from several frames: pieces is (pixels, x0, y0); -1 where empty."""
    grid = [[-1] * w for _ in range(h)]
    for pixels, x0, y0 in pieces:
        for r, row in enumerate(pixels):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < h and 0 <= x0 + c < w:
                    grid[y0 + r][x0 + c] = v
    return grid
