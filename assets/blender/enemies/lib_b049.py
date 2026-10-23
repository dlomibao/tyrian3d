"""Helpers shared by batch b049's models: the big wall of fire in level 4.6 (newsh3.shp).

Six 2x2 enemies make one 48x84 px fire: two columns of flame (newsh3-39 over newsh3-77 on the
left, newsh3-44 over newsh3-82 on the right) standing on a bed of lava (newsh3-118 under the
left column, newsh3-117 under the right). The catalogue splits it into two assemblies of three
pieces (assembly-newsh3-117 and assembly-newsh3-118), so both scripts build the whole fire here,
in fire pixel coordinates, and each cuts out its own pieces.

build-models.sh skips lib_ files; the model scripts import this next to them.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

TAG = "b049fire"
W, H = 48, 84  # the whole fire in sprite pixels
# Grid position (column, row) of each piece's 24x28 block in the fire.
GRID = {
    "newsh3-39": (0, 0), "newsh3-44": (1, 0),
    "newsh3-77": (0, 1), "newsh3-82": (1, 1),
    "newsh3-118": (0, 2), "newsh3-117": (1, 2),
}
FLAME_ROWS = 56  # rows 0-55 are flame, 56-83 lava


def X(c):
    """Fire pixel column (centre at integer c, fractions allowed) to Blender X."""
    return (c + 0.5 - W / 2) / 12


def Y(r):
    """Fire pixel row (centre at integer r) to Blender Y: sprite up is +Y."""
    return (H / 2 - (r + 0.5)) / 12


def root():
    return common.repo_root(__file__)


# --- sprite data ---------------------------------------------------------------------------------

def fire_pixels(base):
    """The six pieces' first frames composed into one 84 x 48 grid of palette indices."""
    grid = [[-1] * W for _ in range(H)]
    for name, (gx, gy) in GRID.items():
        data = common.load_sprite(base, name)
        for r, line in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(line):
                grid[gy * 28 + r][gx * 24 + c] = v
    return grid


def merged_sprite(base):
    """newsh3-77's sprite.json with the colours of every piece, so any index used is valid."""
    data = common.load_sprite(base, "newsh3-77")
    for name in GRID:
        data["colors"].update(common.load_sprite(base, name)["colors"])
    return data


def layout(base, pieces):
    """split_assembly layout for `pieces`, relative to the fire's centre, checked against the
    sprite.json assemblyLayout of the first piece."""
    out = []
    for name in pieces:
        gx, gy = GRID[name]
        out.append((name, gx * 24 + 12 - W / 2, gy * 28 + 14 - H / 2))
    entries = {e["model"]: e for e in common.load_sprite(base, pieces[0])["assemblyLayout"]}
    ref = out[0]
    for name, cx, cy in out:
        e = entries[name]
        e0 = entries[ref[0]]
        assert (e["cx"] - e0["cx"], e["cy"] - e0["cy"]) == (cx - ref[1], cy - ref[2]), name
    return out


# --- geometry ------------------------------------------------------------------------------------

def inside(grid, c, r, rows):
    """Is fire pixel (c, r) (centres at integers) part of the region `rows` (a range)?"""
    ci, ri = int(round(c)), int(round(r))
    if ri not in rows or not 0 <= ci < W:
        return False
    v = grid[ri][ci]
    return v >= 2  # -1 transparent, 1 the sprite's outline


def outline(grid, rows, tolerance=0.3):
    """The outline of the region (largest connected part), traced round pixel edges, rounded by
    corner cutting and simplified; Blender XY, counter-clockwise."""
    ins = lambda c, r: inside(grid, c, r, rows)  # noqa: E731
    edges = {}  # corner -> list of (next corner, owning pixel)
    for r in rows:
        for c in range(W):
            if not ins(c, r):
                continue
            # Corners (cc, rr) at pixel edges; walk with the pixel on the right in sprite space.
            if not ins(c, r - 1):
                edges.setdefault((c, r), []).append(((c + 1, r), (c, r)))
            if not ins(c + 1, r):
                edges.setdefault((c + 1, r), []).append(((c + 1, r + 1), (c, r)))
            if not ins(c, r + 1):
                edges.setdefault((c + 1, r + 1), []).append(((c, r + 1), (c, r)))
            if not ins(c - 1, r):
                edges.setdefault((c, r + 1), []).append(((c, r), (c, r)))
    used = set()
    loops = []
    for start, outs in edges.items():
        for nxt, pix in outs:
            if (start, nxt) in used:
                continue
            loop = [start]
            used.add((start, nxt))
            prev_pix, p = pix, nxt
            while p != start:
                loop.append(p)
                cands = [(n, q) for n, q in edges[p] if (p, n) not in used]
                n, q = next(((n, q) for n, q in cands if q == prev_pix), cands[0])
                used.add((p, n))
                prev_pix, p = q, n
            loops.append(loop)
    loop = max(loops, key=len)
    pts = [Vector((c, r)) for c, r in loop]
    for _ in range(2):
        out = []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            out.append(p.lerp(q, 0.25))
            out.append(p.lerp(q, 0.75))
        pts = out
    pts = simplify_closed(pts, tolerance)
    poly = [((p.x - W / 2) / 12, (H / 2 - p.y) / 12) for p in pts]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    if area < 0:
        poly.reverse()
    return poly


def _rdp(pts, tol):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    best, idx = -1.0, 0
    for i in range(1, len(pts) - 1):
        if ab.length < 1e-9:
            d = (pts[i] - a).length
        else:
            d = abs(ab.x * (pts[i].y - a.y) - ab.y * (pts[i].x - a.x)) / ab.length
        if d > best:
            best, idx = d, i
    if best <= tol:
        return [a, b]
    return _rdp(pts[:idx + 1], tol)[:-1] + _rdp(pts[idx:], tol)


def simplify_closed(pts, tol):
    """Ramer-Douglas-Peucker on a closed loop (split at the point farthest from the first)."""
    far = max(range(len(pts)), key=lambda i: (pts[i] - pts[0]).length)
    a = _rdp(pts[:far + 1], tol)
    b = _rdp(pts[far:] + [pts[0]], tol)
    return a[:-1] + b[:-1]


def slab(bm, poly, z0, z1, mat):
    """Extrude an outline from z0 to z1 with triangulated caps (so the pieces cut cleanly)."""
    n = len(bm.faces)
    common.slab(bm, poly, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    new = bm.faces[n:]
    caps = [f for f in new if len(f.verts) > 4]
    bmesh.ops.triangulate(bm, faces=caps, quad_method="BEAUTY", ngon_method="BEAUTY")


def _catmull(pts, spacing):
    """Resample a polyline of Vectors (any dimension) as a Catmull-Rom curve, about `spacing`
    apart (measured in the first two components)."""
    out = [pts[0]]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        seg = (p2.to_2d() - p1.to_2d()).length
        n = max(1, math.ceil(seg / spacing))
        for k in range(1, n + 1):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return out


def _extent(grid, rows, p, d, limit):
    """How far (pixels, up to `limit`) from p along d before leaving the region."""
    t = 0.0
    while t < limit:
        q = p + d * (t + 0.25)
        if not inside(grid, q.x, q.y, rows):
            return t + 0.2
        t += 0.25
    return limit


def strand(bm, grid, rows, path, flat=0.6, sides=8, mat=0, z=0.0, spacing=1.2):
    """A flame tongue: a tube along `path` of (col, row, radius px) in fire pixels, radius 0 for
    a pointed tip. Each ring is narrowed and shifted so it stays inside the sprite's silhouette.
    Its cross-section is an ellipse `flat` times as tall (Z) as it is wide."""
    pts = _catmull([Vector(p) for p in path], spacing)
    rings = []
    for i, p in enumerate(pts):
        c, r, rad = p
        a = pts[max(i - 1, 0)].to_2d()
        b = pts[min(i + 1, len(pts) - 1)].to_2d()
        t = (b - a).normalized()
        side = Vector((-t.y, t.x))  # in pixel space (rows grow downward)
        if rad <= 0.05:
            rings.append([bm.verts.new((X(c), Y(r), z))])
            continue
        centre = Vector((c, r))
        hi = min(rad, _extent(grid, rows, centre, side, rad))
        lo = min(rad, _extent(grid, rows, centre, -side, rad))
        hw = max((hi + lo) / 2, 0.35)
        mid = centre + side * (hi - lo) / 2
        rz = max(rad * 0.7, hw) * flat / 12
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * (k + 0.5) / sides
            q = mid + side * hw * math.cos(ang)
            ring.append(bm.verts.new((X(q.x), Y(q.y), z + rz * math.sin(ang))))
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
            face = bm.faces.new(f)
            face.material_index = mat
            face.smooth = True
    for ring in (rings[0], rings[-1]):
        if len(ring) > 1:
            face = bm.faces.new(ring)
            face.material_index = mat
            face.smooth = False


def dome(bm, grid, rows, c, r, rx, ry, height, z0, segments=14, rings=4, mat=0):
    """A half-ellipsoid lump: footprint centred on fire pixel (c, r) with radii rx, ry pixels
    (pulled in where it would leave the sprite's silhouette), rising `height` units above z0,
    closed underneath."""
    rim = []
    for j in range(segments):
        a = 2 * math.pi * j / segments
        d = Vector((math.cos(a) * rx, -math.sin(a) * ry))
        full = d.length
        reach = _extent(grid, rows, Vector((c, r)), d.normalized(), full)
        rim.append(d * (max(reach, 0.5) / full))
    levels = []
    for i in range(rings):
        phi = math.pi / 2 * i / rings  # 0 at the rim
        s, h = math.cos(phi), math.sin(phi)
        levels.append([bm.verts.new((X(c + d.x * s), Y(r + d.y * s), z0 + height * h)) for d in rim])
    top = bm.verts.new((X(c), Y(r), z0 + height))
    for a, b in zip(levels, levels[1:]):
        for j in range(segments):
            k = (j + 1) % segments
            f = bm.faces.new((a[j], a[k], b[k], b[j]))
            f.material_index, f.smooth = mat, True
    for j in range(segments):
        k = (j + 1) % segments
        f = bm.faces.new((levels[-1][j], levels[-1][k], top))
        f.material_index, f.smooth = mat, True
    f = bm.faces.new(list(reversed(levels[0])))
    f.material_index, f.smooth = mat, False


# --- the fire ------------------------------------------------------------------------------------

PAINT = 99  # faces coloured from the sprite pixel under them

# Flame tongues, top (tip) to bottom: (column, row, radius px). They follow the bright streaks;
# the dark gaps between them are the slab underneath.
STRANDS = [
    # Left tall tongue, running on down as the brightest streak of the left column.
    [(7.0, 4.6, 0), (7.2, 6, 0.8), (7.5, 10, 1.3), (8.0, 15, 2.0), (8.6, 21, 2.8), (8.8, 27, 3.0),
     (8.6, 33, 3.2), (9.0, 40, 3.2), (9.0, 46, 3.2), (8.2, 51, 3.0), (7.6, 55.4, 2.6)],
    # Dim left edge.
    [(5.0, 25.4, 0), (5.0, 28, 1.2), (4.6, 34, 1.8), (4.8, 40, 2.0), (4.8, 46, 1.8), (4.5, 51, 1.8),
     (4.8, 55.4, 1.6)],
    [(11.6, 24.6, 0), (11.8, 27, 1.2), (12.0, 32, 1.6), (12.0, 40, 1.8), (12.0, 46, 1.6),
     (11.2, 51, 1.4), (11.0, 55.4, 1.2)],
    [(15.5, 24.8, 0), (15.8, 27, 1.0), (16.3, 31, 1.8), (16.5, 38, 2.4), (16.3, 44, 2.4),
     (16.0, 48, 1.6), (16.0, 50.5, 0)],
    [(14.0, 33, 0), (14.0, 36, 1.5), (14.2, 42, 1.8), (14.5, 47, 0)],
    [(20.0, 24.6, 0), (20.0, 27, 1.0), (19.6, 31, 1.6), (19.6, 38, 1.8), (19.5, 44, 1.6),
     (19.5, 47, 0)],
    # Small tongue in the middle, running on down as the stem between the two lower lobes.
    [(24.0, 13.6, 0), (24.0, 16, 1.0), (24.0, 20, 2.0), (24.0, 24, 1.2), (23.8, 28, 1.2),
     (23.5, 34, 1.3), (23.2, 40, 1.4), (23.0, 45, 1.8), (23.2, 50, 1.5), (23.5, 55.4, 1.4)],
    [(26.8, 26.5, 0), (27.0, 30, 1.0), (27.0, 36, 1.4), (26.8, 42, 1.5), (26.5, 46, 1.3),
     (26.5, 48, 0)],
    [(29.0, 24.6, 0), (29.0, 28, 1.0), (29.2, 36, 1.0), (29.2, 42, 1.2), (29.0, 46, 0)],
    [(32.5, 25.5, 0), (32.5, 28, 1.0), (32.5, 33, 1.6), (32.2, 38, 1.8), (31.8, 44, 1.4),
     (31.5, 48, 1.2), (32.5, 52, 1.5), (33.5, 55.4, 1.6)],
    [(34.5, 26, 0), (34.5, 29, 1.0), (34.0, 34, 1.5), (34.0, 38, 1.4), (34.5, 42, 0)],
    # Right tall tongue, running on down as the dim right column.
    [(42.0, 4.6, 0), (42.0, 6, 0.8), (42.0, 12, 1.4), (41.8, 17, 1.8), (41.2, 22, 2.5),
     (40.2, 27, 2.8), (39.5, 32, 3.0), (38.8, 38, 3.0), (38.8, 44, 3.0), (39.5, 49, 2.5),
     (40.0, 52, 1.5), (40.0, 54, 0)],
    [(43.5, 21.5, 0), (43.5, 26, 1.4), (43.0, 32, 1.6), (42.5, 38, 1.5), (42.0, 44, 1.4),
     (43.0, 49, 1.4), (43.5, 55.4, 1.4)],
    [(36.5, 43, 0), (36.5, 46, 1.0), (37.0, 50, 1.2), (37.2, 55.4, 1.4)],
]

# Lava lumps, three overlapping rows: (column, row, rx px, ry px, height units).
LUMPS = [
    (3.0, 59.0, 3.8, 3.4, 0.22), (9.8, 58.6, 3.2, 3.0, 0.18), (15.5, 59.5, 2.6, 3.6, 0.15),
    (20.3, 59.5, 2.4, 3.6, 0.15), (25.2, 58.6, 2.6, 3.0, 0.18), (29.6, 58.6, 2.4, 3.0, 0.18),
    (33.6, 59.5, 2.4, 3.6, 0.14), (39.8, 59.0, 3.8, 3.4, 0.22), (45.8, 58.6, 2.8, 3.0, 0.18),
    (2.5, 66.5, 3.6, 4.2, 0.2), (8.0, 66.0, 3.0, 3.6, 0.14), (15.0, 67.5, 3.6, 4.4, 0.16),
    (21.0, 65.5, 3.0, 3.6, 0.16), (25.8, 65.0, 2.4, 3.0, 0.14), (30.5, 67.5, 2.6, 4.4, 0.17),
    (36.2, 66.5, 3.6, 3.8, 0.2), (42.0, 66.5, 3.4, 3.4, 0.15), (46.3, 66.5, 2.2, 3.4, 0.13),
    (3.0, 72.5, 3.2, 3.0, 0.12), (9.5, 71.5, 3.2, 3.0, 0.11), (16.2, 72.0, 3.4, 2.8, 0.12),
    (26.0, 70.0, 2.6, 2.6, 0.1), (31.5, 72.5, 2.6, 2.8, 0.12), (35.5, 72.0, 3.0, 2.6, 0.13),
    (41.0, 72.0, 3.2, 3.0, 0.11), (45.5, 72.5, 2.6, 2.8, 0.11),
]


def emission_for(index):
    if index >= 124:
        return 5.0
    if index >= 122:
        return 3.0
    if index >= 121:
        return 2.0
    return 0.0


def build_fire(sprite, base, name="fire"):
    """The whole fire as one object in fire coordinates (origin at its centre)."""
    coll = common.reset_collection(name)
    grid = fire_pixels(base)
    indices = sorted(int(i) for i in sprite["colors"] if int(i) >= 112)
    mats = [common.palette_material(sprite, i, TAG, metallic=0.1, roughness=0.6,
                                    emission_strength=emission_for(i)) for i in indices]
    slot = {i: k for k, i in enumerate(indices)}
    bm = bmesh.new()

    flame = range(0, FLAME_ROWS)
    lava = range(FLAME_ROWS, H)
    slab(bm, outline(grid, flame), -0.09, 0.03, slot[116])
    slab(bm, outline(grid, lava), -0.1, 0.03, slot[115])
    for path in STRANDS:
        path = [(c, r, rad * 1.7) for c, r, rad in path]
        strand(bm, grid, flame, path, flat=0.6, sides=8, mat=PAINT, spacing=1.5)
    for c, r, rx, ry, h in LUMPS:
        dome(bm, grid, lava, c, r, rx * 1.15, ry * 1.15, h, -0.02, rings=5, mat=PAINT)

    # Colour each tongue and lump face from the sprite pixel under it.
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    for f in bm.faces:
        if f.material_index != PAINT:
            continue
        if f.normal.z < -0.3:
            f.material_index = slot[113]
            continue
        cen = f.calc_center_median()
        c, r = cen.x * 12 + W / 2 - 0.5, H / 2 - 0.5 - cen.y * 12
        f.material_index = slot[nearest_index(grid, c, r)]

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def nearest_index(grid, c, r):
    """The palette index of the fire pixel nearest (c, r) that is part of the fire."""
    best, best_d = 115, 99.0
    ci, ri = int(round(c)), int(round(r))
    for dr in (-2, -1, 0, 1, 2):
        for dc in (-2, -1, 0, 1, 2):
            rr, cc = ri + dr, ci + dc
            if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] >= 112:
                d = (cc - c) ** 2 + (rr - r) ** 2
                if d < best_d:
                    best, best_d = grid[rr][cc], d
    return best


def composite_png(base, out):
    """The whole fire's sprite as one image, padded to the 24:28 shape that render_preview
    expects for size 6 (72 x 84 px, the fire in the middle)."""
    import numpy as np
    grid = fire_pixels(base)
    sprite = merged_sprite(base)
    img = np.zeros((84, 72, 4), dtype=np.float32)
    for r in range(H):
        for c in range(W):
            v = grid[r][c]
            if v >= 0:
                img[r, c + 12] = [*(ch / 255 for ch in sprite["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("fire_sprite", 72, 84, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def run(assembly, pieces):
    """Build the fire, cut out `pieces`, export each, and render previews if asked."""
    base = root()
    sprite = merged_sprite(base)
    obj = build_fire(sprite, base, assembly)
    parts = common.split_assembly(obj, layout(base, pieces))
    for name in pieces:
        data = common.load_sprite(base, name)
        common.export_sprite_model(base, [parts[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(base, Path(tempfile.mkdtemp()) / "fire.png")
        common.render_preview([obj], str(out), str(ref), size=6, view_px=640)
        for name in pieces:
            data = common.load_sprite(base, name)
            img = base / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([parts[name]], str(out.parent / f"{name}.png"), img, size=2)
