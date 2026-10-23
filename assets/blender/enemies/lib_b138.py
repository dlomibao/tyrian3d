"""Helpers shared by batch b138's model scripts (newshd.shp ground pieces: the grey boulder tiles,
the wall hatch, the opening pod and the brown tusked creature).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block by default (pass size=1 for 12x14 sprites).
Ground pieces stand on z = 0 and build upward.

build-models.sh skips lib_ files; the model scripts import this next to them.
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

OUTLINE = (-1, 1, 32)  # transparent and the dark outline the game draws itself


def dims(size):
    return (12, 14) if size == 1 else (24, 28)


def px(c, size=2):
    return (c + 0.5 - dims(size)[0] / 2) / 12


def row(r, size=2):
    return (dims(size)[1] / 2 - (r + 0.5)) / 12


def ex(c, size=2):
    return (c - dims(size)[0] / 2) / 12


def ey(r, size=2):
    return (dims(size)[1] / 2 - r) / 12


def luminance(rgb):
    r, g, b = rgb
    return 0.3 * r + 0.55 * g + 0.15 * b


# --- Primitives ------------------------------------------------------------------------------------

def ring_loft(bm, rings, mats, cap_start=True, cap_end=True):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order.
    `mats` is a material index, or a list with one per band between rings. Returns the faces."""
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    mat = (lambda b: mats[b]) if isinstance(mats, list) else (lambda b: mats)  # noqa: E731
    faces = []
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
            f = bm.faces.new(face)
            f.material_index = mat(b)
            faces.append(f)
    if cap_start and len(verts[0]) > 2:
        f = bm.faces.new(list(reversed(verts[0])))
        f.material_index = mat(0)
        faces.append(f)
    if cap_end and len(verts[-1]) > 2:
        f = bm.faces.new(verts[-1])
        f.material_index = mat(len(verts) - 2)
        faces.append(f)
    return faces


def box(bm, x0, x1, y0, y1, z0, z1, mat_index=0):
    """An axis-aligned box (units)."""
    common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def prism(bm, outline, z0, z1, mat_index=0):
    """Extrude a counter-clockwise outline (units) from z0 to z1."""
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def pillow(bm, outline, centre, z0, profile, mat_index=0, mats=None):
    """A plate on z0 with the outline `outline` (counter-clockwise, star-shaped about `centre`) whose
    top follows `profile`: a list of (s, z) from the rim (s = 1) inward (s < 1), z absolute. The
    centre is closed with a fan at the last level's height. `mats` gives one material per band
    (len(profile)) if set. Returns the faces."""
    cx, cy = centre
    ring = lambda s, z: [(cx + (x - cx) * s, cy + (y - cy) * s, z) for x, y in outline]  # noqa: E731
    rings = [ring(1.0, z0)] + [ring(s, z) for s, z in profile] + [[(cx, cy, profile[-1][1])]]
    return ring_loft(bm, rings, mats if mats is not None else mat_index, cap_start=True, cap_end=False)


def half_dome(bm, cx, cy, rx, ry, rz, side, z0=0.0, rings=5, sides=10, mat_index=0, inner_mat=None, power=1.0):
    """Half of a ground-standing half-ellipsoid: the part on side `side` (+1 right, -1 left) of the
    plane x = cx, closed by a flat inner face. power < 1 squares off its outline seen from above.
    Returns the faces."""
    loops = []
    for k in range(rings):
        t = (math.pi / 2) * k / rings
        loop = []
        for i in range(sides + 1):
            a = -math.pi / 2 + math.pi * i / sides  # -90..90 degrees
            ca, sa = math.cos(a), math.sin(a)
            ca = max(ca, 0.0) ** power
            sa = math.copysign(abs(sa) ** power, sa)
            x = cx + side * rx * math.cos(t) * ca
            y = cy + ry * math.cos(t) * sa
            loop.append((x, y, z0 + rz * math.sin(t)))
        loops.append(loop)
    top = bm.verts.new((cx, cy, z0 + rz))
    vl = [[bm.verts.new(p) for p in lp] for lp in loops]
    faces = []
    for a, b in zip(vl, vl[1:]):
        for i in range(sides):
            f = bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
            faces.append(f)
    last = vl[-1]
    for i in range(sides):
        faces.append(bm.faces.new((last[i], last[i + 1], top)))
    for f in faces:
        f.material_index = mat_index
    # Flat inner face (the profile on x = cx) and the bottom.
    inner = [l[0] for l in vl] + [top] + [l[-1] for l in reversed(vl)]
    fi = bm.faces.new(inner)
    fi.material_index = inner_mat if inner_mat is not None else mat_index
    fb = bm.faces.new(vl[0])
    fb.material_index = mat_index
    faces += [fi, fb]
    return faces


def dome(bm, cx, cy, rx, ry, h, z=0.0, rings=4, sides=16, mat_index=0, bottom=True):
    """A half ellipsoid standing on height z (units), centred on (cx, cy)."""
    loops = []
    for k in range(rings):
        t = (math.pi / 2) * k / rings
        loops.append([(cx + rx * math.cos(t) * math.cos(a), cy + ry * math.cos(t) * math.sin(a), z + h * math.sin(t))
                      for a in (2 * math.pi * (i + 0.5) / sides for i in range(sides))])
    loops.append([(cx, cy, z + h)])
    return ring_loft(bm, loops, mat_index, cap_start=bottom, cap_end=False)


def polyline_tube(bm, points, radius, sides=6, mat_index=0, caps=True):
    """One round tube along a polyline, mitred at the joints. `radius` is a number or one per point."""
    from mathutils import Vector
    pts = [Vector(p) for p in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    tangents = []
    for i in range(len(pts)):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tangents.append(t.normalized())
    ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    u = tangents[0].cross(ref).normalized()
    rings = []
    for i, (c, t) in enumerate(zip(pts, tangents)):
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u).normalized()
        rings.append([tuple(c + radii[i] * (math.cos(a) * u + math.sin(a) * v))
                      for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))])
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps)


# --- Painting from the sprite ----------------------------------------------------------------------

def pixel_at(pixels, x, y, size=2):
    """The palette index of the sprite pixel under Blender (x, y), or -1 outside."""
    w, h = dims(size)
    c, r = int(math.floor(x * 12 + w / 2)), int(math.floor(h / 2 - y * 12))
    if 0 <= r < len(pixels) and 0 <= c < len(pixels[0]):
        return pixels[r][c]
    return -1


def dominant(pixels, c0, c1, r0, r1, skip=OUTLINE, default=None):
    """The most common palette index in columns [c0, c1) and rows [r0, r1) (ignoring `skip`)."""
    count = {}
    for r in range(max(0, r0), min(len(pixels), r1)):
        for c in range(max(0, c0), min(len(pixels[0]), c1)):
            v = pixels[r][c]
            if v not in skip:
                count[v] = count.get(v, 0) + 1
    if not count:
        return default
    return max(count, key=lambda k: (count[k], k))


# --- Running ---------------------------------------------------------------------------------------

def run(name, build, file):
    """The usual main: build, export every model and, with -- --preview <png>, preview the first
    (or each model to <png> with -fN suffixes when there are several).

    `build(sprite)` returns a list of (model_name, objects, sprites, frame_index) to export."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites, _ in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        for k, (model, objects, _, fi) in enumerate(models):
            frame = sprite["frames"][fi]
            ref = root / "reference" / "models" / name / frame["image"]
            path = out if k == 0 else out.replace(".png", f"-f{k + 1}.png")
            common.render_preview(objects, path, ref, size=frame["size"])
    return sprite


# --- The grey boulder (newshd.shp tiles 88 and 34, side by side) ----------------------------------
# Tiles 88 (left) and 34 (right) are two 12x14 halves of one grey boulder that crosses the screen
# in level 1.5: 88 holds its left flank (outline down its left side), 34 its right flank. Both are
# built from one height field in the pair's 24x14 frame, so the shared edge matches exactly.

BOULDER = {"newshd-88": 0, "newshd-34": 12}  # tile -> its first column in the pair's frame
BOULDER_SLOTS = {3: 4, 4: 4, 5: 6, 6: 6, 7: 8, 8: 8, 9: 10, 10: 10, 11: 12, 12: 12, 102: 4, 106: 107, 107: 107}


def boulder_pair(root):
    """The pair's 24x14 pixels and each row's first and last interior column (+1)."""
    grid = [[-1] * 24 for _ in range(14)]
    for name, ox in BOULDER.items():
        pix = common.load_sprite(root, name)["frames"][0]["pixels"]
        for r in range(14):
            for c in range(12):
                grid[r][ox + c] = pix[r][c]
    left, right = [], []
    for r in range(14):
        cols = [c for c in range(24) if grid[r][c] not in OUTLINE]
        left.append(min(cols))
        right.append(max(cols) + 1)
    return grid, left, right


def boulder(name, file, height=0.3, relief=0.05, samples=8):
    def build(sprite):
        root = common.repo_root(file)
        coll = common.reset_collection(name)
        grid, left, right = boulder_pair(root)
        ox = BOULDER[name]
        pix = sprite["frames"][0]["pixels"]
        lum_of = {int(k): luminance(v) for k, v in sprite["colors"].items()}
        for other in BOULDER:
            lum_of.update({int(k): luminance(v) for k, v in common.load_sprite(root, other)["colors"].items()})
        vals = [lum_of[v] for r in grid for v in r if v not in OUTLINE]
        mean = sum(vals) / len(vals)

        def edge_at(arr, v):
            """Row-centre values interpolated at row position v (0..14, edges)."""
            t = min(max(v - 0.5, 0.0), 13.0)
            k = min(int(t), 12)
            f = t - k
            return arr[k] * (1 - f) + arr[k + 1] * f

        def lum(gx, v):
            acc, n = 0.0, 0
            for du, dv in ((0, 0), (0.7, 0), (-0.7, 0), (0, 0.7), (0, -0.7)):
                c, r = int(math.floor(gx + du)), int(math.floor(v + dv))
                if 0 <= r < 14 and 0 <= c < 24 and grid[r][c] not in OUTLINE:
                    acc += lum_of[grid[r][c]]
                    n += 1
            return acc / n if n else mean

        slots = sorted({BOULDER_SLOTS[v] for r in pix for v in r if v in BOULDER_SLOTS})
        mats = [common.palette_material(sprite, i, name, metallic=0.1, roughness=0.85) for i in slots]
        slot = {i: k for k, i in enumerate(slots)}
        dark = slot[min(slots)]

        rings = []
        for v in range(15):
            L, R = edge_at(left, v), edge_at(right, v)
            c, w = (L + R) / 2, (R - L) / 2
            tb = math.acos(max(-1.0, min(1.0, (c - 12) / w)))
            lo, hi = (0.0, tb) if ox == 0 else (tb, math.pi)
            ring = []
            for k in range(samples + 1):
                th = lo + (hi - lo) * k / samples
                gx = c - w * math.cos(th)
                s = math.sin(th)
                z = height * (0.85 + 0.15 * w / 9) * s ** 0.55
                z += relief * (lum(gx, v) - mean) / 60.0 * s
                ring.append(((gx - ox - 6) / 12, (7 - v) / 12, max(0.0, z)))
            ring.append(((12 - ox - 6) / 12, (7 - v) / 12, 0.0))
            rings.append(ring)
        bm = bmesh.new()
        ring_loft(bm, rings, 0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.normal_update()
        for f in bm.faces:
            if f.normal.z < 0.3:
                f.material_index = dark
                continue
            cen = f.calc_center_median()
            idx = pixel_at(pix, cen.x, cen.y, size=1)
            f.material_index = slot[BOULDER_SLOTS[idx]] if idx in BOULDER_SLOTS else dark
        obj = common.mesh_object(name, bm, mats, coll, smooth=False)
        return [(name, [obj], sprite["sprites"], 0)]
    return run(name, build, file)
