"""Helpers shared by batch b117's models (the boulder heap with the buried red-eyed machine,
newshr.shp 159-165 / 197-203 / 235-241 / 273-279): assembly coordinates, the whole sprite as one
pixel grid, simple solids, and boulders whose footprints follow the rocks in the sprite.

Not a model script itself (build-models.sh skips lib_ files).
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


class Grid:
    """Several 2x2 pieces laid out in a grid (sheet order), as one pixel grid. `rows` is a list of
    rows of piece names. Pixel (c, r) of the whole is column c, row r from the top-left; Blender
    X/Y put the origin at the centre of the whole."""

    def __init__(self, root, rows):
        self.root = root
        self.rows = rows
        self.h, self.w = 28 * len(rows), 24 * len(rows[0])
        self.px = [[-1] * self.w for _ in range(self.h)]
        self.colors = {}
        self.sprites = {}
        for j, names in enumerate(rows):
            for i, name in enumerate(names):
                data = common.load_sprite(root, name)
                self.sprites[name] = data
                self.colors.update(data["colors"])
                for r, line in enumerate(data["frames"][0]["pixels"]):
                    for c, v in enumerate(line):
                        self.px[28 * j + r][24 * i + c] = v

    def X(self, c):
        """Pixel column (centre; fractions allowed) to Blender X."""
        return (c + 0.5 - self.w / 2) * PX

    def Y(self, r):
        """Pixel row (centre) to Blender Y."""
        return (self.h / 2 - (r + 0.5)) * PX

    def EX(self, c):
        """Pixel edge column (0 = the left edge of column 0) to Blender X."""
        return (c - self.w / 2) * PX

    def EY(self, r):
        return (self.h / 2 - r) * PX

    def layout(self):
        """(name, cx, cy) for common.split_assembly, relative to the centre of the whole."""
        out = []
        for j, names in enumerate(self.rows):
            for i, name in enumerate(names):
                out.append((name, 24 * i + 12 - self.w / 2, 28 * j + 14 - self.h / 2))
        return out

    def merged_sprite(self):
        """A sprite dict whose colours cover every piece, for palette_material."""
        first = self.sprites[self.rows[0][0]]
        return {"name": first["name"], "colors": dict(self.colors)}

    def composite_png(self, out):
        """The whole thing's sprite as one PNG, padded to the 24:28 shape render_preview expects."""
        import numpy as np
        size = max(self.w // 12, self.h // 14)  # in render_preview's tiles (12x14 px)
        W, H = 12 * size, 14 * size
        img = np.zeros((H, W, 4), dtype=np.float32)
        x0, y0 = (W - self.w) // 2, (H - self.h) // 2
        for r in range(self.h):
            for c in range(self.w):
                v = self.px[r][c]
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in self.colors[str(v)]), 1.0]
        im = bpy.data.images.new("b117_sprite", W, H, alpha=True)
        im.pixels[:] = img[::-1].ravel()
        im.filepath_raw = str(out)
        im.file_format = "PNG"
        im.save()
        bpy.data.images.remove(im)
        return out, size


def inside(poly, x, y):
    """Point in polygon (any orientation)."""
    n, hit = len(poly), False
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


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


# --- solids ------------------------------------------------------------------------------------

def tag_faces(bm, start, mat, smooth):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start:]:
        f.material_index = mat
        f.smooth = smooth


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of pixel-edge (col, row) points."""
    n = len(bm.faces)
    pts = [(g.EX(c), g.EY(r)) for c, r in outline]
    if sum((pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1])
           for i in range(len(pts))) < 0:
        pts.reverse()
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2)
    tag_faces(bm, n, mat, smooth)


def box(bm, g, c0, r0, c1, r1, z0, z1, mat=0):
    """An axis-aligned box over pixel edges c0..c1, r0..r1."""
    plate(bm, g, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat)


def ellipsoid(bm, g, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, half=False):
    """An ellipsoid centred on pixel (col, row) at height z; half=True keeps only the top (a dome)."""
    n = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    verts = res["verts"]
    if half:
        for v in verts:
            v.co.z = max(v.co.z, 0.0)
    for v in verts:
        v.co = Vector((g.X(col) + v.co.x * rx_px * PX, g.Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    if half:
        bmesh.ops.remove_doubles(bm, verts=verts, dist=1e-5)
    tag_faces(bm, n, mat, True)


def cyl_x(bm, g, c0, c1, row, z, r_px, rz=None, mat=0, sides=8):
    """A cylinder along X from pixel edge c0 to c1 at pixel row `row` (centre), radius r_px."""
    n = len(bm.faces)
    rz = rz if rz is not None else r_px * PX
    rings = []
    for c in (c0, c1):
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new((g.EX(c), g.Y(row) + r_px * PX * math.cos(a), z + rz * math.sin(a))))
        rings.append(ring)
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((rings[0][k], rings[0][j], rings[1][j], rings[1][k]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[1])))
    tag_faces(bm, n, mat, True)


def cyl_y(bm, g, col, r0, r1, z, r_px, rz=None, mat=0, sides=8):
    """A cylinder along Y from pixel edge row r0 to r1 at pixel column `col` (centre)."""
    n = len(bm.faces)
    rz = rz if rz is not None else r_px * PX
    rings = []
    for r in (r0, r1):
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new((g.X(col) + r_px * PX * math.cos(a), g.EY(r), z + rz * math.sin(a))))
        rings.append(ring)
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((rings[0][k], rings[0][j], rings[1][j], rings[1][k]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[1])))
    tag_faces(bm, n, mat, True)


def torus(bm, g, col, row, z, rx_px, ry_px, tube_px, tube_z, mat=0, segments=24, sides=6):
    """An elliptical ring lying flat round pixel (col, row)."""
    n = len(bm.faces)
    rings = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        ring = []
        for k in range(sides):
            b = 2 * math.pi * k / sides
            rr = tube_px * math.cos(b)
            ring.append(bm.verts.new((g.X(col) + (rx_px + rr) * ca * PX, g.Y(row) + (ry_px + rr) * sa * PX,
                                      z + tube_z * math.sin(b))))
        rings.append(ring)
    for i in range(segments):
        r0, r1 = rings[i], rings[(i + 1) % segments]
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    tag_faces(bm, n, mat, True)


# --- boulders ----------------------------------------------------------------------------------

DARK = {1, 160, 161}  # outline and crevice pixels: they part rocks, they don't colour them


def family(v):
    if 2 <= v <= 13:
        return "grey"
    if 18 <= v <= 28:
        return "gold"
    if 160 <= v <= 170:
        return "brown"
    return None


def segment(g, seeds, keep):
    """Share the pixels where keep(c, r) is true among the seeds (col, row): each pixel goes to the
    seed it reaches most cheaply, where crossing dark crevice pixels costs more, so the regions
    follow the rocks drawn in the sprite. Returns one list of (c, r) per seed."""
    import heapq
    INF = float("inf")
    cost = [[INF] * g.w for _ in range(g.h)]
    owner = [[-1] * g.w for _ in range(g.h)]
    heap = []
    for i, (c, r) in enumerate(seeds):
        c, r = int(c), int(r)
        cost[r][c] = 0
        owner[r][c] = i
        heapq.heappush(heap, (0, c, r, i))
    while heap:
        d, c, r, i = heapq.heappop(heap)
        if d > cost[r][c] or owner[r][c] != i:
            continue
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if not (0 <= nc < g.w and 0 <= nr < g.h) or g.px[nr][nc] < 0 or not keep(nc, nr):
                continue
            v = g.px[nr][nc]
            step = 4.0 if v in DARK else 1.0
            if d + step < cost[nr][nc]:
                cost[nr][nc] = d + step
                owner[nr][nc] = i
                heapq.heappush(heap, (d + step, nc, nr, i))
    regions = [[] for _ in seeds]
    for r in range(g.h):
        for c in range(g.w):
            if owner[r][c] >= 0:
                regions[owner[r][c]].append((c, r))
    return regions


def distance_in(g, keep):
    """Chebyshev distance (px) of each pixel to the nearest pixel outside the shape."""
    from collections import deque
    dist = [[0] * g.w for _ in range(g.h)]
    q = deque()
    for r in range(g.h):
        for c in range(g.w):
            if g.px[r][c] >= 0 and keep(c, r):
                dist[r][c] = -1
            else:
                q.append((c, r))
    while q:
        c, r = q.popleft()
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                nc, nr = c + dc, r + dr
                if 0 <= nc < g.w and 0 <= nr < g.h and dist[nr][nc] == -1:
                    dist[nr][nc] = dist[r][c] + 1
                    q.append((nc, nr))
    return dist


def footprint(region, centre, n):
    """n points round `centre` (col, row): in each direction, the farthest corner of the region's
    pixels, so the outline is star-shaped about the centre and covers the region."""
    cx, cy = centre
    best = [0.0] * n
    for c, r in region:
        for dc in (-0.5, 0.5):
            for dr in (-0.5, 0.5):
                x, y = c + 0.5 + dc - cx, r + 0.5 + dr - cy
                d = math.hypot(x, y)
                if d < 1e-6:
                    continue
                a = math.atan2(y, x) % (2 * math.pi)
                k = int(round(a / (2 * math.pi) * n)) % n
                best[k] = max(best[k], d)
    # Directions no pixel fell in take the mean of their neighbours.
    for k in range(n):
        if best[k] == 0:
            best[k] = (best[k - 1] + best[(k + 1) % n]) / 2 or 1.0
    return [(cx + best[k] * math.cos(2 * math.pi * k / n), cy + best[k] * math.sin(2 * math.pi * k / n))
            for k in range(n)]


def region_colours(g, region):
    """The rock's dominant colour family and two palette indices in it: the body (median) and
    the lit facets (upper quartile); plus where its bright pixels lie (col, row)."""
    from collections import Counter
    fams = Counter(family(g.px[r][c]) for c, r in region if g.px[r][c] not in DARK and family(g.px[r][c]))
    if not fams:
        return "brown", 161, 162, None
    fam = fams.most_common(1)[0][0]
    vals = sorted(g.px[r][c] for c, r in region if g.px[r][c] not in DARK and family(g.px[r][c]) == fam)
    body = quantise(vals[(len(vals) * 13) // 20])
    lit = quantise(vals[min(len(vals) - 1, (len(vals) * 9) // 10)])
    top = vals[-max(1, len(vals) // 6):]
    thr = top[0]
    pts = [(c, r) for c, r in region if g.px[r][c] not in DARK and family(g.px[r][c]) == fam and g.px[r][c] >= thr]
    bright = (sum(c for c, _ in pts) / len(pts) + 0.5, sum(r for _, r in pts) / len(pts) + 0.5) if pts else None
    return fam, body, lit, bright


def boulder(bm, g, region, slot, base_z, height, n=9, seed=0, centre=None):
    """A faceted boulder over a region of sprite pixels: its outline follows the region, a skirt
    drops to the ground, and a cap of two inset rings rises to a peak leaning
    toward the region's lit side. `slot(index)` gives the material slot for a palette index.
    Facets that face the same way as the sprite's highlight get the lit colour."""
    rnd = random.Random(seed)
    fam, body, lit, bright = region_colours(g, region)
    if centre is None:
        centre = (sum(c for c, _ in region) / len(region) + 0.5, sum(r for _, r in region) / len(region) + 0.5)
    cx, cy = centre
    outline = footprint(region, centre, n)
    # Peak: pulled toward the bright pixels (the ridge sits between the lit and shaded faces).
    if bright:
        bx, by = bright
        px_, py_ = cx + (bx - cx) * 0.45, cy + (by - cy) * 0.45
        light = Vector(((bx - cx) * PX, -(by - cy) * PX, 0.0))
    else:
        px_, py_ = cx, cy
        light = Vector((0.5, 0.5, 0.0)) * PX
    if light.length < 0.5 * PX:
        light = Vector((0.3, 0.6, 0.0))
    light = Vector((light.x, light.y, light.length * 1.2)).normalized()

    def P(c, r, z):
        return bm.verts.new((g.EX(c), g.EY(r), z))

    z0 = 0.0
    rings = [[P(c, r, z0) for c, r in outline]] if base_z - z0 > 0.02 else []
    zs = [base_z + height * f for f in (0.0, 0.55, 0.88)]
    scales = [1.0, 0.82, 0.42]
    for (z, s) in zip(zs, scales):
        ring = []
        for k, (c, r) in enumerate(outline):
            jz = (rnd.random() - 0.5) * height * 0.18 if s < 1.0 else 0.0
            jc = (rnd.random() - 0.5) * 0.6 if s < 1.0 else 0.0
            ring.append(P(px_ + (c - px_) * s + jc, py_ + (r - py_) * s + jc, z + jz))
        rings.append(ring)
    peak = P(px_, py_, base_z + height)
    start = len(bm.faces)
    faces = []
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            faces.append(bm.faces.new((a[k], a[j], b[j], b[k])))
    for k in range(n):
        faces.append(bm.faces.new((rings[-1][k], rings[-1][(k + 1) % n], peak)))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.smooth = False
        no = f.normal
        if no.z < -0.5:
            f.material_index = slot(body)
            continue
        index = lit if no.dot(light) > 0.4 else body
        f.material_index = slot(index)
    return fam, body, lit


def quantise(v):
    """Round a rock colour to a few steps of its ramp, to keep the material count down."""
    steps = {"brown": (162, 164, 166, 168, 170), "gold": (20, 22, 24, 26), "grey": (3, 5, 7, 9, 11)}
    ramp = steps[family(v)]
    return min(ramp, key=lambda s: abs(s - v))
