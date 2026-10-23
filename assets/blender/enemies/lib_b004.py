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
