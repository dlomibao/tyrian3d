"""Helpers shared by batch b029's model scripts (build-models.sh skips lib_ modules).

- Grid: pixel <-> Blender coordinates for a sprite or a whole assembly (w x h px, centred).
- assembly_pixels: the first frames of an assembly's pieces composed into one pixel grid.
- Body: a lump whose top-view outline follows the sprite row by row (a span per row) with an
  elliptic cross-section, and the surface query that parts laid on it use.
- sweep: a tube along a path (open or closed), lumps: rounded gyri/lobes fitted to the sprite's
  highlights, ellipsoid, plate, and the PNG writer for composite reference images.
"""

import math
import struct
import sys
import zlib
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12


class Grid:
    """A w x h px grid centred on the Blender origin (sprite up is +Y)."""

    def __init__(self, w, h):
        self.w, self.h = w, h

    def X(self, c):
        """Column (pixel centre; fractions allowed) to Blender X."""
        return (c + 0.5 - self.w / 2) / 12

    def Y(self, r):
        """Row (pixel centre) to Blender Y."""
        return (self.h / 2 - (r + 0.5)) / 12

    def col(self, x):
        return x * 12 + self.w / 2 - 0.5

    def row(self, y):
        return self.h / 2 - 0.5 - y * 12


def assembly_pixels(root, names):
    """Compose the first frame of each piece into one grid. Returns (pixels, colors, w, h,
    (sx0, sy0)) where (sx0, sy0) is the screen position of grid pixel (0, 0)."""
    sprites = {n: common.load_sprite(root, n) for n in names}
    layout = {e["model"]: (e["cx"], e["cy"]) for e in sprites[names[0]]["assemblyLayout"] if e["model"] in names}
    x0 = min(cx for cx, _ in layout.values()) - 12
    y0 = min(cy for _, cy in layout.values()) - 14
    w = max(cx for cx, _ in layout.values()) + 12 - x0
    h = max(cy for _, cy in layout.values()) + 14 - y0
    pixels = [[-1] * w for _ in range(h)]
    colors = {}
    for n in names:
        colors.update(sprites[n]["colors"])
        cx, cy = layout[n]
        for r, line in enumerate(sprites[n]["frames"][0]["pixels"]):
            for c, v in enumerate(line):
                if v >= 0:
                    pixels[cy - 14 - y0 + r][cx - 12 - x0 + c] = v
    return pixels, colors, w, h, (x0, y0), layout


def write_png(path, pixels, colors):
    """Write a sprite grid (palette indices, -1 transparent) as an RGBA PNG, 1 px per pixel."""
    h, w = len(pixels), len(pixels[0])
    rows = []
    for line in pixels:
        rows.append(b"\0" + b"".join(bytes((*colors[str(v)], 255)) if v >= 0 else b"\0\0\0\0" for v in line))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b""))
    return path


def faces_since(bm, n, mat=None, smooth=None):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        if mat is not None:
            f.material_index = mat
        if smooth is not None:
            f.smooth = smooth


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


def rings_to_faces(bm, rings, mat=0, smooth=True, closed=False, cap_start=True, cap_end=True):
    """Join rings of vertices (lists of equal length, or single verts for tips)."""
    n0 = len(bm.faces)
    pairs = list(zip(rings, rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    for r0, r1 in pairs:
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
            bm.faces.new(f)
    if not closed:
        if cap_start and len(rings[0]) > 2:
            bm.faces.new(list(reversed(rings[0])))
        if cap_end and len(rings[-1]) > 2:
            bm.faces.new(rings[-1])
    faces_since(bm, n0, mat, smooth)


def sweep(bm, pts, sides=8, mat=0, smooth=True, closed=False, cap_start=True, cap_end=True):
    """A tube along a path of (x, y, z, half_width, half_height) in Blender units. Rings stand
    across the path in the XY plane (width) and along Z (height); zero size makes a tip."""
    up = Vector((0, 0, 1))
    P = [Vector(p[:3]) for p in pts]
    n = len(P)
    rings = []
    for i, (x, y, z, w, h) in enumerate(pts):
        if closed:
            t = P[(i + 1) % n] - P[(i - 1) % n]
        else:
            t = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(P[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(P[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    rings_to_faces(bm, rings, mat, smooth, closed, cap_start, cap_end)


def catmull(pts, n, closed=False):
    """Resample points (tuples) along a Catmull-Rom spline through them to n points."""
    P = [Vector(p) for p in pts]
    if closed:
        ext = [P[-1]] + P + [P[0], P[1]]
        segs = len(P)
    else:
        ext = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
        segs = len(P) - 1
    out = []
    count = n if closed else n - 1
    for i in range(n):
        s = i / count * segs
        k = min(int(s), segs - 1)
        t = s - k
        p0, p1, p2, p3 = ext[k], ext[k + 1], ext[k + 2], ext[k + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    return out


def ellipsoid(bm, centre, radii, mat=0, segments=12, rings=6, angle=0.0, smooth=True):
    """A closed ellipsoid at `centre` with semi-axes `radii` (x, y, z), turned by `angle` about Z."""
    rot = Matrix.Rotation(angle, 3, "Z")
    c = Vector(centre)
    rx, ry, rz = radii
    n0 = len(bm.faces)

    def v(x, y, z):
        return bm.verts.new(c + rot @ Vector((x * rx, y * ry, z * rz)))

    top, bottom = v(0, 0, 1), v(0, 0, -1)
    lat = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        lat.append([v(math.sin(phi) * math.cos(2 * math.pi * j / segments),
                      math.sin(phi) * math.sin(2 * math.pi * j / segments), math.cos(phi))
                    for j in range(segments)])
    for j in range(segments):
        k = (j + 1) % segments
        bm.faces.new((top, lat[0][j], lat[0][k]))
        bm.faces.new((bottom, lat[-1][k], lat[-1][j]))
        for r0, r1 in zip(lat, lat[1:]):
            bm.faces.new((r0[j], r1[j], r1[k], r0[k]))
    faces_since(bm, n0, mat, smooth)


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of Blender (x, y) points (counter-clockwise)."""
    n0 = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    faces_since(bm, n0, mat, smooth)


class Body:
    """A lump whose top-view outline is a span [left, right] (in columns, pixel edges) per row,
    with an elliptic cross-section: up to `top(r)` above z0 and `bottom(r)` below it.

    spans: list of (row, left_edge_col, right_edge_col, top_height, bottom_height) at row
    positions (fractions allowed; the first and last are the ends). Built along Y."""

    def __init__(self, grid, spans, z0=0.0, power=1.0):
        self.g, self.spans, self.z0, self.power = grid, spans, z0, power

    def _span_at(self, r):
        s = self.spans
        if r <= s[0][0]:
            return s[0]
        if r >= s[-1][0]:
            return s[-1]
        for a, b in zip(s, s[1:]):
            if a[0] <= r <= b[0]:
                t = (r - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0
                return tuple(a[i] + (b[i] - a[i]) * t for i in range(5))

    def build(self, bm, mat=0, sides=20, smooth=True, caps=True):
        g = self.g
        rings = []
        for r, left, right, top, bot in self.spans:
            xc = g.X((left + right) / 2 - 0.5)
            hw = (right - left) / 2 * PX
            y = g.Y(r - 0.5)
            ring = []
            for k in range(sides):
                a = 2 * math.pi * (k + 0.5) / sides
                s = math.sin(a)
                cz = abs(s) ** self.power * (1 if s >= 0 else -1)
                cx = abs(math.cos(a)) ** self.power * (1 if math.cos(a) >= 0 else -1)
                ring.append(bm.verts.new((xc + hw * cx, y, self.z0 + (top if s >= 0 else bot) * cz)))
            rings.append(ring)
        rings_to_faces(bm, rings, mat, smooth, cap_start=caps, cap_end=caps)

    def top(self, x, y):
        """Height of the top surface over Blender (x, y); z0 outside."""
        r = self.g.row(y) + 0.5
        _, left, right, top, _ = self._span_at(r)
        c = self.g.col(x) + 0.5
        hw = (right - left) / 2
        if hw <= 0:
            return self.z0
        u = min(abs(c - (left + right) / 2) / hw, 1.0)
        q = max(1 - u ** (2 / self.power), 0.0) ** (self.power / 2)
        return self.z0 + top * q


def lumps(bm, pixels, grid, surface, slot_of, inside=None, min_level=67, sink=0.25, height=0.04,
          height_per_level=0.006, segments=10, rings=5, max_axis=3.6, min_axis=1.1, radius=3, window=2, spread=2, stretch=2.0):
    """Rounded gyri/lobes fitted to the sprite's shading: each local brightness peak of the
    palette ramp (indices 64-79, brighter = higher) gets an ellipsoid stretched along the bright
    pixels around it (their principal axis), set into `surface.top(x, y)`, with the material slot
    `slot_of(index)` of the brightest pixel at its centre. `inside(c, r)` limits where peaks are
    taken. Returns the number of lumps."""
    h, w = len(pixels), len(pixels[0])

    def lvl(r, c):
        if 0 <= r < h and 0 <= c < w:
            v = pixels[r][c]
            if 64 <= v <= 79:
                return v - 64
            if v == 1:
                return -1
        return None

    sm = [[None] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if lvl(r, c) is None:
                continue
            vals = [lvl(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]
            vals = [v for v in vals if v is not None]
            sm[r][c] = sum(vals) / len(vals)
    count = 0
    for r in range(h):
        for c in range(w):
            s = sm[r][c]
            if s is None or lvl(r, c) < min_level - 64 or (inside and not inside(c, r)):
                continue
            peak = True
            for dr in range(-window, window + 1):
                for dc in range(-window, window + 1):
                    if (dr or dc) and 0 <= r + dr < h and 0 <= c + dc < w:
                        o = sm[r + dr][c + dc]
                        if o is not None and (o > s or (o == s and (dr, dc) < (0, 0))):
                            peak = False
            if not peak:
                continue
            # Pixels around the peak that belong to the same bright fold.
            base = lvl(r, c)
            pts = []
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    v = lvl(r + dr, c + dc)
                    if v is not None and v >= base - spread and dr * dr + dc * dc <= radius * radius + 1:
                        pts.append((dc, dr, 1 + v - (base - spread)))
            sw = sum(p[2] for p in pts)
            mx = sum(p[0] * p[2] for p in pts) / sw
            my = sum(p[1] * p[2] for p in pts) / sw
            cxx = sum((p[0] - mx) ** 2 * p[2] for p in pts) / sw
            cyy = sum((p[1] - my) ** 2 * p[2] for p in pts) / sw
            cxy = sum((p[0] - mx) * (p[1] - my) * p[2] for p in pts) / sw
            tr, det = cxx + cyy, cxx * cyy - cxy * cxy
            l1 = tr / 2 + math.sqrt(max(tr * tr / 4 - det, 0))
            l2 = tr / 2 - math.sqrt(max(tr * tr / 4 - det, 0))
            ang = 0.5 * math.atan2(2 * cxy, cxx - cyy)  # in pixel space (rows go down)
            a = min(max(stretch * math.sqrt(l1), min_axis), max_axis)
            b = min(max(stretch * math.sqrt(max(l2, 0)), min_axis), a)
            pc, pr = c + mx * 0.5, r + my * 0.5
            x, y = grid.X(pc), grid.Y(pr)
            idx = max(v for v in (pixels[r][c], ) if v >= 0)
            slot = slot_of(idx)
            if slot is None:
                continue
            zt = surface.top(x, y)
            hz = height + height_per_level * base
            ellipsoid(bm, (x, y, zt - hz * sink), (a * PX, b * PX, hz), mat=slot, segments=segments,
                      rings=rings, angle=-ang)
            count += 1
    return count


def mirror_since(bm, start_v, axis_x):
    """Add a mirror image (about X = axis_x) of every vertex/face added since vertex index start_v."""
    bm.verts.ensure_lookup_table()
    verts = bm.verts[start_v:]
    faces = {f for v in verts for f in v.link_faces}
    edges = {e for v in verts for e in v.link_edges}
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + list(edges) + list(faces))["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def paint(bm, pixels, grid, slot_of, faces=None, min_nz=0.15, under_slot=None):
    """Give each upward face the material slot of the sprite pixels under it (the rounded mean of
    the indices under its centre and corners, slot_of(index) -> slot or None to leave it)."""
    bm.normal_update()
    h, w = len(pixels), len(pixels[0])
    for f in (faces if faces is not None else bm.faces):
        if f.normal.z < min_nz:
            if under_slot is not None:
                f.material_index = under_slot
            continue
        cen = f.calc_center_median()
        vals = []
        for p in [cen] + [cen.lerp(v.co, 0.5) for v in f.verts]:
            c, r = int(round(grid.col(p.x))), int(round(grid.row(p.y)))
            if 0 <= r < h and 0 <= c < w and pixels[r][c] >= 0:
                vals.append(pixels[r][c] if pixels[r][c] != 1 else 64)
        if vals:
            slot = slot_of(round(sum(vals) / len(vals)))
            if slot is not None:
                f.material_index = slot


def _levels(pixels):
    """Shading level per pixel (palette ramp 64-79 -> 0-15, outline -> -1, else None) and its
    3x3 mean."""
    h, w = len(pixels), len(pixels[0])

    def lvl(r, c):
        if 0 <= r < h and 0 <= c < w:
            v = pixels[r][c]
            if 64 <= v <= 79:
                return v - 64
            if v == 1:
                return -1
        return None

    sm = [[None] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if lvl(r, c) is None:
                continue
            vals = [lvl(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]
            vals = [v for v in vals if v is not None]
            sm[r][c] = (2 * lvl(r, c) + sum(vals)) / (len(vals) + 2)
    return lvl, sm


def trace_ridges(pixels, min_level=5, drop=3.0, max_len=16, inside=None):
    """Follow the bright folds of a shaded sprite: from each unvisited local maximum (brightest
    first) walk both ways along the brightest neighbours, keeping roughly straight on, until the
    shading drops `drop` levels below the start or below `min_level`. Returns paths of
    (col, row, level) pixel centres."""
    h, w = len(pixels), len(pixels[0])
    lvl, sm = _levels(pixels)
    used = [[False] * w for _ in range(h)]
    peaks = []
    for r in range(h):
        for c in range(w):
            s = sm[r][c]
            if s is None or s < min_level or (inside and not inside(c, r)):
                continue
            if all(sm[r + dr][c + dc] is None or sm[r + dr][c + dc] <= s
                   for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                   if 0 <= r + dr < h and 0 <= c + dc < w):
                peaks.append((s, c, r))
    peaks.sort(reverse=True)
    paths = []
    for s0, c0, r0 in peaks:
        if used[r0][c0]:
            continue
        # Principal direction of the bright pixels around the peak.
        pts = [(dc, dr) for dr in range(-2, 3) for dc in range(-2, 3)
               if 0 <= r0 + dr < h and 0 <= c0 + dc < w and sm[r0 + dr][c0 + dc] is not None
               and sm[r0 + dr][c0 + dc] >= s0 - 1.5]
        cxx = sum(p[0] * p[0] for p in pts)
        cyy = sum(p[1] * p[1] for p in pts)
        cxy = sum(p[0] * p[1] for p in pts)
        ang = 0.5 * math.atan2(2 * cxy, cxx - cyy)
        d0 = (math.cos(ang), math.sin(ang))
        halves = []
        for sign in (1, -1):
            d = (d0[0] * sign, d0[1] * sign)
            c, r = c0, r0
            walk = []
            seen = {(c0, r0)}
            for _ in range(max_len // 2):
                best = None
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if not (dr or dc):
                            continue
                        nc, nr = c + dc, r + dr
                        if not (0 <= nr < h and 0 <= nc < w) or (nc, nr) in seen:
                            continue
                        v = sm[nr][nc]
                        if v is None:
                            continue
                        ln = math.hypot(dc, dr)
                        dot = (dc * d[0] + dr * d[1]) / ln
                        if dot < 0.35:
                            continue
                        score = v + 0.8 * dot
                        if best is None or score > best[0]:
                            best = (score, nc, nr, dc / ln, dr / ln)
                if best is None:
                    break
                _, nc, nr, ux, uy = best
                v = sm[nr][nc]
                if v < s0 - drop or v < min_level - 1 or used[nr][nc]:
                    break
                c, r = nc, nr
                seen.add((c, r))
                walk.append((c, r, v))
                dx, dy = 0.6 * d[0] + 0.4 * ux, 0.6 * d[1] + 0.4 * uy
                ln = math.hypot(dx, dy)
                d = (dx / ln, dy / ln)
            halves.append(walk)
        path = list(reversed(halves[1])) + [(c0, r0, s0)] + halves[0]
        for c, r, _ in path:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if 0 <= r + dr < h and 0 <= c + dc < w:
                        used[r + dr][c + dc] = True
        paths.append(path)
    return paths


def ridge_tubes(bm, paths, pixels, grid, surface, slot_of, width=1.3, height=0.035, height_per_level=0.003,
                sink=0.4, sides=6, min_points=1):
    """Lay a rounded fold along each traced path on `surface.top(x, y)`: a tube tapering at its
    ends, coloured by the brightest pixel along it. Single-pixel paths become small domes."""
    count = 0
    for path in paths:
        if len(path) < min_points:
            continue
        idx = max(pixels[r][c] for c, r, _ in path)
        slot = slot_of(idx)
        if slot is None:
            continue
        lvl = max(v for _, _, v in path)
        hz = height + height_per_level * lvl
        if len(path) <= 2:
            c = sum(p[0] for p in path) / len(path)
            r = sum(p[1] for p in path) / len(path)
            x, y = grid.X(c), grid.Y(r)
            ellipsoid(bm, (x, y, surface.top(x, y) - hz * sink), (width * 1.2 * PX, width * 1.2 * PX, hz),
                      mat=slot, segments=8, rings=4)
            count += 1
            continue
        pts2 = [(grid.X(c), grid.Y(r)) for c, r, _ in path]
        # Smooth the pixel staircase, extend the ends half a pixel.
        n = max(4, min(len(path) // 2 + 3, 9))
        curve = catmull(pts2, n)
        a, b = curve[0] - curve[1], curve[-1] - curve[-2]
        if a.length > 0:
            curve[0] = curve[0] + a.normalized() * 0.5 * PX
        if b.length > 0:
            curve[-1] = curve[-1] + b.normalized() * 0.5 * PX
        sec = []
        for i, p in enumerate(curve):
            t = i / (len(curve) - 1)
            k = math.sin(min(min(t, 1 - t) / 0.3, 1.0) * math.pi / 2) ** 0.7
            if i in (0, len(curve) - 1):
                k = 0.0
            z = surface.top(p.x, p.y) - hz * sink
            sec.append((p.x, p.y, z, width * PX * k, hz * k))
        sweep(bm, sec, sides=sides, mat=slot, smooth=True)
        count += 1
    return count
