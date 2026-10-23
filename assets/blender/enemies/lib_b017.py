"""Helpers shared by batch b017's scripts (build-models.sh skips lib_ modules).

Batch b017 is the rock formations of level 4.2: a rock arch and a rock wall (with a grey clamp
machine on one stretch), each several 2x2 pieces. The helpers:

- Sheet: several pieces' first frames composed into one pixel grid (assembly pixel coordinates),
  with the Blender X/Y of its columns and rows.
- Mats: palette materials made on demand, one slot per palette index.
- rock_shell: a solid, faceted rock whose outline follows a pixel mask, with a rounded top and
  bottom and the sprite's light and dark plates as relief; its facets take the sprite colour under
  them.
- tube / ellipsoid / mirror helpers for the hard-surface parts.
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils import geometry as mgeo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units


# --- pixel grids ---------------------------------------------------------------------------------

class Sheet:
    """Pieces' frames composed into one grid. `placements` are (model, col0, row0, frame_index):
    the piece's top-left pixel in the grid. The grid's centre is the Blender origin; X(c) and Y(r)
    take pixel-corner coordinates (a pixel's centre is c + 0.5, r + 0.5)."""

    def __init__(self, root, placements):
        self.colors = {}
        self.sprites = {}
        w = h = 0
        for name, c0, r0, _ in placements:
            if name not in self.sprites:
                self.sprites[name] = common.load_sprite(root, name)
                self.colors.update(self.sprites[name]["colors"])
            w, h = max(w, c0 + 24), max(h, r0 + 28)
        self.w, self.h = w, h
        self.pix = [[-1] * w for _ in range(h)]
        for name, c0, r0, fi in placements:
            frame = self.sprites[name]["frames"][fi]
            for r, row in enumerate(frame["pixels"]):
                for c, v in enumerate(row):
                    if v >= 0:
                        self.pix[r0 + r][c0 + c] = v

    def X(self, c):
        return (c - self.w / 2) * U

    def Y(self, r):
        return (self.h / 2 - r) * U

    def col(self, x):
        return x / U + self.w / 2

    def row(self, y):
        return self.h / 2 - y / U

    def at(self, c, r):
        """Palette index at pixel (c, r) (ints), -1 outside."""
        if 0 <= r < self.h and 0 <= c < self.w:
            return self.pix[r][c]
        return -1

    def nearest(self, c, r, ok, reach=3):
        """The index of the nearest pixel to corner-coordinate point (c, r) that ok(index) accepts."""
        ci, ri = int(math.floor(c)), int(math.floor(r))
        best = None
        for d in range(reach + 1):
            for dr in range(-d, d + 1):
                for dc in range(-d, d + 1):
                    if max(abs(dr), abs(dc)) != d:
                        continue
                    v = self.at(ci + dc, ri + dr)
                    if ok(v):
                        dist = (ci + dc + 0.5 - c) ** 2 + (ri + dr + 0.5 - r) ** 2
                        if best is None or dist < best[0]:
                            best = (dist, v)
            if best is not None:
                return best[1]
        return None

    def composite_png(self, out):
        """The composed sprite as a PNG, padded to the 24:28 shape render_preview expects.
        Returns (path, size in tiles)."""
        import numpy as np
        size = math.ceil(max(self.w / 12, self.h / 14))
        W, H = 12 * size, 14 * size
        img = np.zeros((H, W, 4), dtype=np.float32)
        x0, y0 = (W - self.w) // 2, (H - self.h) // 2
        for r in range(self.h):
            for c in range(self.w):
                v = self.pix[r][c]
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in self.colors[str(v)]), 1.0]
        im = bpy.data.images.new("b017_sheet", W, H, alpha=True)
        im.pixels[:] = img[::-1].ravel()
        im.filepath_raw = str(out)
        im.file_format = "PNG"
        im.save()
        bpy.data.images.remove(im)
        return out, size


class Mats:
    """Palette materials, one slot per (palette index, finish)."""

    def __init__(self, tag, colors):
        self.sprite = {"name": tag, "colors": colors}
        self.tag = tag
        self.list = []
        self.slots = {}

    def __call__(self, index, metallic=0.1, roughness=0.8, emission_strength=0.0):
        key = (index, metallic, roughness, emission_strength)
        if key not in self.slots:
            tag = self.tag
            if any(k[0] == index for k in self.slots):
                tag = f"{self.tag}_{len(self.list)}"
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, tag, metallic=metallic,
                                                     roughness=roughness, emission_strength=emission_strength))
        return self.slots[key]


# --- masks and fields ----------------------------------------------------------------------------

def trace_loops(mask):
    """Closed outlines (pixel-corner coordinates (c, r)) of a boolean mask [r][c], each with the
    filled side on its left when Y points up (counter-clockwise outer loops in Blender)."""
    h, w = len(mask), len(mask[0])

    def filled(c, r):
        return 0 <= r < h and 0 <= c < w and mask[r][c]

    out = {}
    for r in range(h):
        for c in range(w):
            if not mask[r][c]:
                continue
            if not filled(c, r + 1):
                out.setdefault((c, r + 1), []).append((c + 1, r + 1))
            if not filled(c + 1, r):
                out.setdefault((c + 1, r + 1), []).append((c + 1, r))
            if not filled(c, r - 1):
                out.setdefault((c + 1, r), []).append((c, r))
            if not filled(c - 1, r):
                out.setdefault((c, r), []).append((c, r + 1))
    loops = []
    while out:
        start = next(iter(out))
        loop = [start]
        prev = None
        cur = start
        while True:
            nxt_list = out[cur]
            if len(nxt_list) > 1 and prev is not None:
                # A pinch: take the sharpest left turn so loops stay simple.
                din = (cur[0] - prev[0], cur[1] - prev[1])
                def turn(n):
                    d = (n[0] - cur[0], n[1] - cur[1])
                    return din[0] * d[1] - din[1] * d[0]
                nxt_list.sort(key=turn)
            nxt = nxt_list.pop(0)
            if not nxt_list:
                del out[cur]
            prev, cur = cur, nxt
            if cur == start:
                break
            loop.append(cur)
        loops.append(loop)
    return loops


def _dp(points, tol):
    if len(points) < 3:
        return points
    a, b = Vector(points[0]), Vector(points[-1])
    ab = b - a
    best, idx = -1.0, 0
    for i in range(1, len(points) - 1):
        p = Vector(points[i])
        if ab.length < 1e-9:
            d = (p - a).length
        else:
            d = abs(ab.x * (p.y - a.y) - ab.y * (p.x - a.x)) / ab.length
        if d > best:
            best, idx = d, i
    if best <= tol:
        return [points[0], points[-1]]
    left = _dp(points[:idx + 1], tol)
    return left[:-1] + _dp(points[idx:], tol)


def simplify_loop(loop, tol=0.6):
    """Douglas-Peucker on a closed loop (keeps the two points farthest apart)."""
    n = len(loop)
    if n < 6:
        return loop
    i0 = 0
    far = max(range(n), key=lambda i: (loop[i][0] - loop[0][0]) ** 2 + (loop[i][1] - loop[0][1]) ** 2)
    a = loop[i0:far + 1]
    b = loop[far:] + [loop[0]]
    pts = _dp(a, tol)[:-1] + _dp(b, tol)[:-1]
    return pts


def distance_field(mask, open_sides="", pad=24):
    """Approximate Euclidean distance (pixels) from each filled pixel's centre to the nearest empty
    pixel. Sides in `open_sides` ('l', 'r', 't', 'b') continue past the grid (the edge column or
    row is repeated), so a piece cut there doesn't round off."""
    h, w = len(mask), len(mask[0])
    H, W = h + 2 * pad, w + 2 * pad

    def src(c, r):
        cc, rr = c - pad, r - pad
        if cc < 0:
            if "l" not in open_sides:
                return False
            cc = 0
        if cc >= w:
            if "r" not in open_sides:
                return False
            cc = w - 1
        if rr < 0:
            if "t" not in open_sides:
                return False
            rr = 0
        if rr >= h:
            if "b" not in open_sides:
                return False
            rr = h - 1
        return mask[rr][cc]

    INF = 1e9
    # Track the nearest empty pixel (8SSEDT-like two passes with offsets).
    near = [[None] * W for _ in range(H)]
    d2 = [[INF] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if not src(c, r):
                near[r][c] = (c, r)
                d2[r][c] = 0.0

    def relax(r, c, dr, dc):
        rr, cc = r + dr, c + dc
        if 0 <= rr < H and 0 <= cc < W and near[rr][cc] is not None:
            n = near[rr][cc]
            dd = (n[0] - c) ** 2 + (n[1] - r) ** 2
            if dd < d2[r][c]:
                d2[r][c] = dd
                near[r][c] = n

    for _ in range(2):
        for r in range(H):
            for c in range(W):
                for dr, dc in ((-1, -1), (-1, 0), (-1, 1), (0, -1)):
                    relax(r, c, dr, dc)
            for c in range(W - 1, -1, -1):
                relax(r, c, 0, 1)
        for r in range(H - 1, -1, -1):
            for c in range(W - 1, -1, -1):
                for dr, dc in ((1, 1), (1, 0), (1, -1), (0, 1)):
                    relax(r, c, dr, dc)
            for c in range(W):
                relax(r, c, 0, -1)
    return [[math.sqrt(d2[r + pad][c + pad]) if d2[r + pad][c + pad] < INF else 99.0 for c in range(w)]
            for r in range(h)]


def blur(field, mask, radius):
    """Box-blur a per-pixel field over the filled pixels only."""
    h, w = len(field), len(field[0])
    out = [[0.0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if not mask[r][c]:
                continue
            s = n = 0.0
            for rr in range(max(0, r - radius), min(h, r + radius + 1)):
                for cc in range(max(0, c - radius), min(w, c + radius + 1)):
                    if mask[rr][cc]:
                        s += field[rr][cc]
                        n += 1
            out[r][c] = s / n
    return out


def bilinear(field, mask, c, r):
    """Sample a per-pixel field at corner-coordinate point (c, r), using filled pixels only."""
    h, w = len(field), len(field[0])
    fc, fr = c - 0.5, r - 0.5
    c0, r0 = int(math.floor(fc)), int(math.floor(fr))
    s = n = 0.0
    for dr in (0, 1):
        for dc in (0, 1):
            cc, rr = c0 + dc, r0 + dr
            if 0 <= rr < h and 0 <= cc < w and mask[rr][cc]:
                wt = (1 - abs(fc - cc)) * (1 - abs(fr - rr))
                s += field[rr][cc] * wt
                n += wt
    if n > 1e-6:
        return s / n
    # Nothing filled around: nearest filled pixel within a few.
    best = None
    for rr in range(max(0, r0 - 3), min(h, r0 + 5)):
        for cc in range(max(0, c0 - 3), min(w, c0 + 5)):
            if mask[rr][cc]:
                d = (cc - fc) ** 2 + (rr - fr) ** 2
                if best is None or d < best[0]:
                    best = (d, field[rr][cc])
    return best[1] if best else 0.0


def _point_in_loops(p, loops):
    x, y = p
    inside = False
    for loop in loops:
        n = len(loop)
        for i in range(n):
            x1, y1 = loop[i]
            x2, y2 = loop[(i + 1) % n]
            if (y1 > y) != (y2 > y):
                xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                if xi > x:
                    inside = not inside
    return inside


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px_, py_ = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px_ - ax) * dx + (py_ - ay) * dy) / L))
    return math.hypot(px_ - ax - t * dx, py_ - ay - t * dy)


def _fill_points(loops, mask, step, seed, margin):
    """Jittered, staggered interior points (corner coordinates) at least `margin` px from the outline."""
    rnd = random.Random(seed)
    h, w = len(mask), len(mask[0])
    segs = [(loop[i], loop[(i + 1) % len(loop)]) for loop in loops for i in range(len(loop))]
    pts = []
    r = step / 2
    k = 0
    while r < h:
        c = step / 2 + (step / 2 if k % 2 else 0)
        while c < w:
            pc = c + rnd.uniform(-0.3, 0.3) * step
            pr = r + rnd.uniform(-0.3, 0.3) * step
            ci, ri = int(pc), int(pr)
            if 0 <= ri < h and 0 <= ci < w and mask[ri][ci] and _point_in_loops((pc, pr), loops):
                if all(_seg_dist((pc, pr), a, b) >= margin for a, b in segs
                       if abs(a[0] - pc) < margin + 30 and abs(a[1] - pr) < margin + 30):
                    pts.append((pc, pr))
            c += step
        r += step * 0.866
        k += 1
    return pts


def _triangulate(loops, interior):
    """CDT of the outline loops plus interior points; returns (coords, triangles, boundary_ids) with
    boundary vertices first, in loop order, and only the triangles inside the outline."""
    coords = [Vector(p) for loop in loops for p in loop] + [Vector(p) for p in interior]
    edges = []
    i = 0
    for loop in loops:
        n = len(loop)
        edges += [(i + k, i + (k + 1) % n) for k in range(n)]
        i += n
    nb = i
    vout, _, fout, orig, _, _ = mgeo.delaunay_2d_cdt(coords, edges, [], 0, 1e-5, True)
    # Map output verts back to input ids where possible.
    ids = []
    for k, o in enumerate(orig):
        ids.append(o[0] if o else None)
    tris = []
    for f in fout:
        cx = sum(vout[j].x for j in f) / len(f)
        cy = sum(vout[j].y for j in f) / len(f)
        if _point_in_loops((cx, cy), loops):
            tris.append(f)
    return vout, tris, ids, nb


def rock_shell(bm, sheet, mask, slot_of, *, top=0.3, bottom=0.22, edge=0.05, radius=10.0, relief=0.12,
               step=2.2, bottom_step=5.0, lum=None, open_sides="", dt_mask=None, tol=0.6, seed=1,
               bottom_slot=0, wall_slot=None, top_lift=None, blur_px=1):
    """A solid rock filling `mask` ([r][c] booleans over the sheet): a faceted top surface that rises
    from `edge` at the outline to `top` (units) `radius` px inside, plus `relief` times the sprite's
    (blurred) brightness about its mean so light plates stand proud and dark cracks sink; a flatter
    bottom down to -`bottom`. slot_of(palette index, (c, r)) -> material slot paints each top facet
    from the sprite pixel under it. `lum(index)` -> 0..1 brightness. `dt_mask` (default `mask`) is
    the mask the rounding is measured from. top_lift(c, r) -> extra height (units) for shaping."""
    h, w = sheet.h, sheet.w
    loops = [simplify_loop(l, tol) for l in trace_loops(mask)]
    loops = [l for l in loops if len(l) >= 3]
    dt = distance_field(dt_mask or mask, open_sides)
    if lum is None:
        lum = lambda v: 0.5  # noqa: E731
    lumf = [[lum(sheet.pix[r][c]) if mask[r][c] else 0.0 for c in range(w)] for r in range(h)]
    lumf = blur(lumf, mask, blur_px)
    vals = [lumf[r][c] for r in range(h) for c in range(w) if mask[r][c]]
    mean = sum(vals) / max(1, len(vals))

    def prof(c, r):
        t = min(1.0, bilinear(dt, mask, c, r) / radius)
        return math.sqrt(max(0.0, 1 - (1 - t) ** 2))

    def ztop(c, r, boundary):
        if boundary:
            return edge
        p = prof(c, r)
        z = edge + (top - edge) * p + relief * (bilinear(lumf, mask, c, r) - mean) * p
        if top_lift:
            z += top_lift(c, r) * p
        return max(edge * 0.5, z)

    def zbot(c, r, boundary):
        if boundary:
            return -edge
        return -(edge + (bottom - edge) * prof(c, r))

    first_face = len(bm.faces)
    ring_top, ring_bot = {}, {}

    def surface(step_px, zf, is_top, seed_):
        interior = _fill_points(loops, mask, step_px, seed_, margin=step_px * 0.45)
        vout, tris, ids, nb = _triangulate(loops, interior)
        verts = {}
        ring = ring_top if is_top else ring_bot
        for k, co in enumerate(vout):
            oid = ids[k]
            if oid is not None and oid < nb:
                if oid not in ring:
                    ring[oid] = bm.verts.new((sheet.X(co.x), sheet.Y(co.y), zf(co.x, co.y, True)))
                verts[k] = ring[oid]
            else:
                verts[k] = bm.verts.new((sheet.X(co.x), sheet.Y(co.y), zf(co.x, co.y, False)))
        faces = []
        for f in tris:
            vs = [verts[j] for j in f]
            if len(set(vs)) < 3:
                continue
            if not is_top:
                vs = list(reversed(vs))
            try:
                face = bm.faces.new(vs)
            except ValueError:
                continue
            faces.append((face, f, vout))
        return faces

    tops = surface(step, ztop, True, seed)
    bots = surface(bottom_step, zbot, False, seed + 7)
    for face, f, vout in tops:
        cc = sum(vout[j].x for j in f) / len(f)
        rr = sum(vout[j].y for j in f) / len(f)
        v = sheet.nearest(cc, rr, lambda i: i >= 0)
        face.material_index = slot_of(v, (cc, rr))
    for face, _, _ in bots:
        face.material_index = bottom_slot
    # Walls between the top and bottom rings.
    i = 0
    for loop in loops:
        n = len(loop)
        for k in range(n):
            a, b = i + k, i + (k + 1) % n
            if a in ring_top and b in ring_top and a in ring_bot and b in ring_bot:
                try:
                    face = bm.faces.new((ring_bot[a], ring_bot[b], ring_top[b], ring_top[a]))
                except ValueError:
                    continue
                mc = (loop[k][0] + loop[(k + 1) % n][0]) / 2
                mr = (loop[k][1] + loop[(k + 1) % n][1]) / 2
                v = sheet.nearest(mc, mr, lambda i_: i_ >= 0)
                face.material_index = wall_slot if wall_slot is not None else slot_of(v, (mc, mr))
        i += n
    return first_face


# --- hard-surface helpers ------------------------------------------------------------------------

def tube(bm, points, sides=8, mat_index=0, cap_start=True, cap_end=True, flat=1.0):
    """A loft along a path of ((x, y, z), radius); radius 0 is a point. `flat` squashes the
    cross-section vertically (0.5 = half as tall as wide)."""
    pts = [(Vector(p), r) for p, r in points]
    rings = []
    for i, (p, r) in enumerate(pts):
        a = pts[max(0, i - 1)][0]
        b = pts[min(len(pts) - 1, i + 1)][0]
        d = (b - a).normalized()
        ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(ref).normalized()
        wv = d.cross(u).normalized()
        if r == 0:
            rings.append([bm.verts.new(p)])
            continue
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * (k + 0.5) / sides
            off = r * (math.cos(ang) * u + math.sin(ang) * wv)
            off.z *= flat
            ring.append(bm.verts.new(p + off))
        rings.append(ring)
    faces = []
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
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat_index
    return faces


def ellipsoid(bm, centre, radii, mat_index=0, segments=12, rings=6):
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * radii[0], cy + v.co.y * radii[1], cz + v.co.z * radii[2]))
    faces = {f for v in res["verts"] for f in v.link_faces}
    for f in faces:
        f.material_index = mat_index
    return list(faces)


def mirror_faces(bm, faces, axis_x):
    """Duplicate `faces` mirrored about the vertical plane x = axis_x."""
    dup = bmesh.ops.duplicate(bm, geom=list(faces))["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
    new_faces = [e for e in dup if isinstance(e, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=new_faces)
    return new_faces


def to_object(name, bm, mats, coll, smooth_faces=()):
    """A mesh object, flat shaded except `smooth_faces`."""
    smooth = set(smooth_faces)
    for f in bm.faces:
        f.smooth = f in smooth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def export_pieces(root, obj, sheet, placements, sprites_for=None, collection=None):
    """Split the whole object into its pieces (placements' 24x28 boxes) and export each. Returns
    {name: object}. `sprites_for(name)` -> the sprites a piece exports (default all its frames)."""
    layout = []
    for name, c0, r0, _ in placements:
        cx = c0 + 12 - sheet.w / 2
        cy = r0 + 14 - sheet.h / 2
        layout.append((name, cx, cy))
    pieces = common.split_assembly(obj, layout, collection)
    for name, _, _ in layout:
        sprites = sprites_for(name) if sprites_for else sheet.sprites[name]["sprites"]
        common.export_sprite_model(root, [pieces[name]], f"enemies/{name}", sprites)
    return pieces


def previews(root, out, obj, pieces, sheet):
    """The whole object beside the composed sprite to `out`, and each piece to <piece>.png."""
    import tempfile
    out = Path(out)
    ref, size = sheet.composite_png(Path(tempfile.mkdtemp()) / "sheet.png")
    common.render_preview([obj], str(out), str(ref), size=size, view_px=640)
    for name, piece in pieces.items():
        data = sheet.sprites[name]
        img = Path(root) / "reference" / "models" / name / data["frames"][0]["image"]
        common.render_preview([piece], str(out.parent / f"{name}.png"), img, size=2)
