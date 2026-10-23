"""Helpers shared by batch b004's models (orbs, eyeballs, ears, rocks): sprite coordinates,
ellipsoids and tubes placed anywhere, and per-face colours sampled from the sprite.

build-models.sh skips lib_ files; the model scripts import this next to them.
"""

import math
import random
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def dims(size):
    """Sprite block size in pixels (w, h) for size 1 or 2."""
    return (12, 14) if size == 1 else (24, 28)


def px(c, size=2):
    """Sprite column (pixel centre, or any fractional column) to Blender X."""
    w, _ = dims(size)
    return (c + 0.5 - w / 2) / 12


def row(r, size=2):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    _, h = dims(size)
    return (h / 2 - (r + 0.5)) / 12


def to_col(x, size=2):
    w, _ = dims(size)
    return x * 12 + w / 2 - 0.5


def to_row(y, size=2):
    _, h = dims(size)
    return h / 2 - 0.5 - y * 12


def sample(pixels, x, y, size=2):
    """The palette index of the sprite pixel under Blender (x, y), or -1 outside / transparent."""
    c, r = int(round(to_col(x, size))), int(round(to_row(y, size)))
    if 0 <= r < len(pixels) and 0 <= c < len(pixels[0]):
        return pixels[r][c]
    return -1


def ellipsoid(bm, a, b, c, segments=16, rings=10, mat_index=0):
    """An ellipsoid centred on the origin with semi-axes a (x), b (y), c (z), lofted along Y."""
    sections = [(b, 0.0, 0.0, 0.0)]
    for i in range(1, rings):
        t = math.pi * i / rings
        sections.append((b * math.cos(t), a * math.sin(t), c * math.sin(t), 0.0))
    sections.append((-b, 0.0, 0.0, 0.0))
    common.loft(bm, list(reversed(sections)), sides=segments, mat_index=mat_index)


def transform_from(bm, start, matrix):
    """Apply a 4x4 matrix to every vertex added since index `start`."""
    bm.verts.ensure_lookup_table()
    verts = bm.verts[start:]
    bmesh.ops.transform(bm, matrix=matrix, verts=verts)


def aim(direction, location=(0, 0, 0), roll=0.0):
    """A matrix that turns local +Y toward `direction` (a part built along Y, like a loft) and moves
    it to `location`. `roll` turns it about its own axis first (radians)."""
    d = Vector(direction).normalized()
    q = d.to_track_quat("Y", "Z")
    return Matrix.Translation(location) @ q.to_matrix().to_4x4() @ Matrix.Rotation(roll, 4, "Y")


def tube(bm, points, radii, sides=8, mat_index=0, flat=1.0, cap=True):
    """A tube along a polyline of 3D points, with a radius per point (0 closes to a tip). `flat`
    squashes the cross-section in Z (a ridge lying on a surface)."""
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
        up = Vector((0, 0, 1))
        side = t.cross(up)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        nup = side.cross(t).normalized()
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(p + side * math.cos(ang) * rad + nup * math.sin(ang) * rad * flat))
        rings.append(ring)
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
            bm.faces.new(f).material_index = mat_index
    if cap:
        if len(rings[0]) > 1:
            bm.faces.new(rings[0]).material_index = mat_index
        if len(rings[-1]) > 1:
            bm.faces.new(list(reversed(rings[-1]))).material_index = mat_index


def mask_outline(pixels, keep, size=2, inset=0.0):
    """The outline of the sprite pixels for which keep(index) is true, as a polygon (Blender XY,
    counter-clockwise) traced round the pixel corners and then smoothed by corner cutting.
    Only the largest connected region is traced. `inset` (pixels) pulls it inward."""
    h, w = len(pixels), len(pixels[0])
    inside = lambda c, r: 0 <= r < h and 0 <= c < w and keep(pixels[r][c])  # noqa: E731
    # Directed boundary edges, pixel corners in (col, row) with the inside on the left when going
    # counter-clockwise in Blender (rows grow downward, so walk clockwise in sprite space).
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
    loops = []
    seen = set()
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
    # Drop collinear corners, then cut corners twice so stair steps become slopes.
    pts = [Vector((c, r)) for c, r in loop]
    for _ in range(2):
        out = []
        n = len(pts)
        for i in range(n):
            p, q = pts[i], pts[(i + 1) % n]
            out.append(p * 0.75 + q * 0.25)
            out.append(p * 0.25 + q * 0.75)
        pts = out
    poly = [((p.x - w / 2) / 12, (h / 2 - p.y) / 12) for p in pts]
    # Thin out: keep every other point.
    poly = poly[::2]
    # Make sure it's counter-clockwise.
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    if area < 0:
        poly.reverse()
    if inset:
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        out = []
        for i, (x, y) in enumerate(poly):
            ax, ay = poly[i - 1]
            bx, by = poly[(i + 1) % len(poly)]
            tx, ty = bx - ax, by - ay
            ln = math.hypot(tx, ty) or 1
            nx, ny = -ty / ln, tx / ln  # left normal = inward for CCW
            out.append((x + nx * inset / 12, y + ny * inset / 12))
        poly = out
    return poly


def paint_from_sprite(bm, pixels, slot_of, size=2, under_slot=None, min_nz=0.0, average=False):
    """Give each face the material slot of the sprite pixel under its centre (slot_of(index) ->
    slot or None to leave it; `average` takes the mean index over the face, for shades of one
    ramp). Faces facing down (normal z < min_nz) get `under_slot` if given."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    for f in bm.faces:
        cen = f.calc_center_median()
        if f.normal.z < min_nz:
            if under_slot is not None:
                f.material_index = under_slot
            continue
        if average:
            pts = [cen] + [cen.lerp(v.co, 0.6) for v in f.verts]
            vals = [sample(pixels, p.x, p.y, size) for p in pts]
            vals = [v for v in vals if v >= 0]
            idx = round(sum(vals) / len(vals)) if vals else -1
        else:
            idx = sample(pixels, cen.x, cen.y, size)
        slot = slot_of(idx)
        if slot is not None:
            f.material_index = slot


def jitter(seed):
    return random.Random(seed)


def preview(objs, sprite, root, name):
    """Render the preview if the script was given `-- --preview <png>`."""
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = Path(root) / "reference" / "models" / name / sprite["frames"][0]["image"]
        common.render_preview(objs, out, ref, size=sprite["frames"][0]["size"])


class Ellipsoid:
    """An ellipsoid body at (x0, y0, z0) with semi-axes a, b, c, for draping parts on its top."""

    def __init__(self, x0, y0, a, b, c, z0=0.0):
        self.x0, self.y0, self.z0, self.a, self.b, self.c = x0, y0, z0, a, b, c

    def build(self, bm, segments=20, rings=12, mat_index=0):
        start = len(bm.verts)
        ellipsoid(bm, self.a, self.b, self.c, segments, rings, mat_index)
        transform_from(bm, start, Matrix.Translation((self.x0, self.y0, self.z0)))

    def top(self, x, y):
        """Height of the top surface over (x, y); the rim height outside it."""
        u = ((x - self.x0) / self.a) ** 2 + ((y - self.y0) / self.b) ** 2
        return self.z0 + self.c * math.sqrt(max(0.0, 1 - u))


def drape_cap(bm, surface, cx, cy, rx, ry, lift=0.02, dome=0.03, sink=0.02, sides=16, mat_index=0,
              tilt=0.0):
    """A cap (an eye's iris, a boss, a lens) draped over `surface.top(x, y)`: its outline is the
    ellipse (cx, cy, rx, ry) seen from above (rotated by `tilt` radians), its edge sinks `sink`
    below the surface, it rises `lift` above it just inside the edge and `lift + dome` at the
    centre."""
    ct, st = math.cos(tilt), math.sin(tilt)
    def pt(k, scale):
        ang = 2 * math.pi * (k + 0.5) / sides
        ex, ey = rx * scale * math.cos(ang), ry * scale * math.sin(ang)
        return cx + ex * ct - ey * st, cy + ex * st + ey * ct
    rings = []
    for scale, off in ((1.0, -sink), (0.92, lift), (0.55, lift + dome * 0.7)):
        ring = []
        for k in range(sides):
            x, y = pt(k, scale)
            ring.append(bm.verts.new((x, y, surface.top(x, y) + off)))
        rings.append(ring)
    centre = bm.verts.new((cx, cy, surface.top(cx, cy) + lift + dome))
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mat_index
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((rings[-1][k], rings[-1][j], centre)).material_index = mat_index


def eyeball(bm, frame, size, c, slots, sides=24):
    """A floating eyeball as one frame of its sprite shows it. `frame` gives sprite pixels (columns,
    rows; fractional is fine): body (col, row, half width, half height) of the ball; iris, ring and
    pupil (col, row, rx, ry) seen from above, draped on the ball as stacked caps. `c` is the ball's
    half height in units; slots = (ball, iris, ring, pupil) material slots."""
    BODY, IRIS, RING, PUPIL = slots
    bc, br, ba, bb = frame["body"]
    ball = Ellipsoid(px(bc, size), row(br, size), ba / 12, bb / 12, c)
    ball.build(bm, segments=sides, rings=sides // 2, mat_index=BODY)
    for key, slot, lift, dome in (("iris", IRIS, 0.008, 0.02), ("ring", RING, 0.022, 0.012),
                                  ("pupil", PUPIL, 0.03, 0.01)):
        col, r, rx, ry = frame[key]
        drape_cap(bm, ball, px(col, size), row(r, size), rx / 12, ry / 12, lift=lift, dome=dome,
                  sink=0.02, sides=16, mat_index=slot)
    return ball



def chaikin(points, rounds=2, closed=True):
    """Round off a polyline's corners by corner cutting."""
    pts = [Vector(p) for p in points]
    for _ in range(rounds):
        out = []
        n = len(pts) if closed else len(pts) - 1
        if not closed:
            out.append(pts[0])
        for i in range(n):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            out.append(p.lerp(q, 0.25))
            out.append(p.lerp(q, 0.75))
        if not closed:
            out.append(pts[-1])
        pts = out
    return [tuple(p) for p in pts]


def inset_polygon(poly, d):
    """Move each vertex of a counter-clockwise polygon `d` units inward."""
    out = []
    n = len(poly)
    for i, (x, y) in enumerate(poly):
        ax, ay = poly[i - 1][:2]
        bx, by = poly[(i + 1) % n][:2]
        tx, ty = bx - ax, by - ay
        ln = math.hypot(tx, ty) or 1
        out.append((x - ty / ln * d, y + tx / ln * d))
    return out


def ellipse_polygon(cx, cy, rx, ry, n=16, tilt=0.0):
    ct, st = math.cos(tilt), math.sin(tilt)
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        ex, ey = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + ex * ct - ey * st, cy + ex * st + ey * ct))
    return pts


# newsh5-284's outline, pixel edges as (column, row), clockwise on screen (counter-clockwise in
# Blender, whose Y points up the screen).
EAR_OUTLINE = [
    (9, 2), (8, 2.4), (7, 3.2), (5.5, 4.7), (4, 6.5), (3, 8.5), (3, 11), (4, 12.5), (5, 14),
    (6, 16), (7.5, 17.5), (9, 19.5), (10, 21), (11, 23), (12, 24.5), (14, 25.8), (15.5, 26),
    (17, 25.5), (18.6, 24), (19.5, 22.5), (20, 21), (20, 14), (20, 9), (19, 7.5), (18, 6),
    (16.5, 4.5), (15, 3), (13, 2),
]


def ear(bm, mirror, slots):
    """The flying ear of episode 4 (newsh5-284, and newsh5-245 its mirror image): a flat ear with a
    rolled rim (helix) all round, a hollow inside with the darker concha and fossa, the Y-shaped
    antihelix ridge, a fleshy lobe and the tragus bumps. Positions are newsh5-284's (lobe at the
    bottom right); `mirror` flips them for newsh5-245.
    slots = (skin, rim, hollow, dark, ridge, highlight)."""
    SKIN, RIM, HOLLOW, DARK, RIDGE, HIGH = slots
    s = -1 if mirror else 1
    P = lambda c, r, z=0.0: (s * px(c), row(r), z)  # noqa: E731
    E = lambda c, r: (s * (c - 12) / 12, (14 - r) / 12)  # noqa: E731  pixel edge coordinates

    outline = chaikin([E(c, r) for c, r in EAR_OUTLINE], rounds=2)
    if mirror:
        outline.reverse()
    outline = [(x, y) for x, y in outline]
    common.slab(bm, outline, 0.12, z=-0.04, mat_index=SKIN)
    # Hollow floor inside the rim, then the darker concha and the fossa above the antihelix.
    common.slab(bm, inset_polygon(outline, 2.2 / 12), 0.03, z=0.02, mat_index=HOLLOW)
    for c, r, rx, ry, tilt in ((15.6, 13.4, 2.3, 4.0, 0.15), (10.8, 6.4, 3.6, 1.5, -0.35),
                               (14.4, 9.6, 1.6, 1.2, 0.0)):
        poly = ellipse_polygon(*E(c + 0.5, r + 0.5), rx / 12, ry / 12, n=14, tilt=s * tilt)
        common.slab(bm, poly, 0.03, z=0.028, mat_index=DARK)
    # Rolled rim round the outline, inset by its radius so the silhouette stays put.
    rim = inset_polygon(outline[::2], 1.9 / 12)
    pts = [(x, y, 0.025) for x, y in rim] + [(rim[0][0], rim[0][1], 0.025)]
    tube(bm, pts, [2.1 / 12] * len(pts), sides=8, mat_index=RIM, flat=0.55, cap=False)

    # Antihelix: a stem from the antitragus up to the fork, then the upper and lower crura.
    stem = chaikin([P(14.6, 19.0, 0.04), P(13.2, 17.2, 0.05), P(12.4, 15.0, 0.055), P(11.6, 12.4, 0.06),
                    P(10.4, 9.8, 0.055), P(9.6, 7.6, 0.045), P(9.4, 6.4, 0.03)], rounds=1, closed=False)
    radii = [0.15 - 0.07 * i / (len(stem) - 1) for i in range(len(stem))]
    radii[-1] = 0.0
    tube(bm, stem, radii, sides=8, mat_index=RIDGE, flat=0.5)
    tube(bm, [P(11.8, 12.2, 0.06), P(12.6, 10.4, 0.05), P(14.0, 9.0, 0.04), P(15.4, 8.4, 0.025)],
         [0.11, 0.1, 0.08, 0.0], sides=8, mat_index=RIDGE, flat=0.5)

    # Lobe: a soft pad at the bottom.
    Ellipsoid(s * px(14.4), row(21.6), 4.4 / 12, 3.6 / 12, 0.12).build(bm, segments=14, rings=8, mat_index=SKIN)
    # Tragus (the bump on the open side) and antitragus (the knob at the stem's foot).
    for c, r, rx, ry, rz in ((17.9, 15.0, 1.5, 2.0, 0.1), (14.9, 19.0, 1.4, 1.1, 0.09)):
        Ellipsoid(s * px(c), row(r), rx / 12, ry / 12, rz, z0=0.02).build(bm, segments=10, rings=6, mat_index=HIGH)
    # The bright highlight on the upper rim (row 5, column 15).
    Ellipsoid(s * px(15.2), row(4.9), 1.2 / 12, 1.0 / 12, 0.05, z0=0.085).build(bm, segments=8, rings=4, mat_index=HIGH)
