"""Helpers shared by batch b059's model scripts (build-models.sh skips lib_ modules).

Both of the batch's objects are 2x2 assemblies (48 x 56 px) from level 2.4: an organic mass
lying on a wall of ribbed grey tubes. Everything here works in assembly pixel coordinates
(column 0-47, row 0-55, the block's centre at the Blender origin):

- the merged pixel grid and colours of an assembly's four pieces,
- the grey tube wall, traced from the sprite (each tube follows a light ridge of the texture
  between its dark grooves, so the tubes sit where the sprite draws them),
- sweeps, ellipsoids and plates placed by pixel,
- a membrane (a bevelled slab with holes) from a pixel mask,
- per-face colours sampled from the sprite pixel under each face,
- a composite reference image of the whole assembly for the preview.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

W, H = 48, 56
PX = 1 / 12


def X(c):
    """Assembly column (pixel centre, fractions allowed) to Blender X."""
    return (c + 0.5 - W / 2) / 12


def Y(r):
    """Assembly row (pixel centre) to Blender Y: sprite up is +Y."""
    return (H / 2 - (r + 0.5)) / 12


def load_grid(root, pieces):
    """pieces: [(name, col0, row0)] each piece's top-left in the assembly. Returns (grid, sprite)
    where grid[r][c] is the palette index and sprite is the first piece's sprite.json with the
    colours of every piece merged in (so any index the assembly uses is valid)."""
    grid = [[-1] * W for _ in range(H)]
    merged = None
    for name, c0, r0 in pieces:
        data = common.load_sprite(root, name)
        if merged is None:
            merged = data
        else:
            merged["colors"].update(data["colors"])
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                grid[r0 + r][c0 + c] = v
    return grid, merged


def sample(grid, x, y):
    c = int(round(x * 12 + W / 2 - 0.5))
    r = int(round(H / 2 - 0.5 - y * 12))
    if 0 <= r < H and 0 <= c < W:
        return grid[r][c]
    return -1


def nearest(slots):
    """A mapper from palette index to the slot whose index is closest (slots: {index: slot}),
    or the first slot for indices outside the ramp."""
    keys = sorted(slots)
    lo, hi = keys[0], keys[-1]

    def f(idx):
        if idx < lo - 2 or idx > hi + 3:
            return slots[lo]
        return slots[min(keys, key=lambda k: abs(k - idx))]
    return f


def paint(bm, first_face, grid, mapper, under=None, min_nz=-0.2):
    """Give faces from index `first_face` on the slot of the sprite pixel under their centre.
    Faces pointing down (normal z < min_nz) get `under` when given."""
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    for f in bm.faces[first_face:]:
        if under is not None and f.normal.z < min_nz:
            f.material_index = under
            continue
        cen = f.calc_center_median()
        f.material_index = mapper(sample(grid, cen.x, cen.y))


def set_smooth(bm, first_face, smooth=True):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        f.smooth = smooth


# --- shapes ------------------------------------------------------------------------------------

def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in top view; zero size collapses a ring to a point."""
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
    rings = []
    up = Vector((0, 0, 1))
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        if t.length < 1e-6:
            t = Vector((0, 1, 0))
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
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
        f.material_index = mat
        f.smooth = smooth
    # Make the faces point outward (the winding depends on the path's direction), judged on a
    # side face between two full rings against the path between them.
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        if len(r0) > 1 and len(r1) > 1:
            f = next(fc for fc in faces if set(fc.verts) == {r0[0], r0[1], r1[1], r1[0]})
            f.normal_update()
            if f.normal.dot(f.calc_center_median() - (pts[i] + pts[i + 1]) / 2) < 0:
                bmesh.ops.reverse_faces(bm, faces=faces)
            break


def smooth_path(points, rounds=2):
    """Corner-cut an open polyline of tuples (keeps the ends)."""
    pts = [tuple(p) for p in points]
    for _ in range(rounds):
        out = [pts[0]]
        for p, q in zip(pts, pts[1:]):
            out.append(tuple(a * 0.75 + b * 0.25 for a, b in zip(p, q)))
            out.append(tuple(a * 0.25 + b * 0.75 for a, b in zip(p, q)))
        out.append(pts[-1])
        pts = out
    return pts


def tendril(bm, pts, z, w0, w1, h0, h1, sides=8, mat=0, round_ends=True, rounds=2):
    """A rounded tube through (col, row) points, its width tapering from w0 to w1 px and its
    half height from h0 to h1 units."""
    pts = smooth_path(pts, rounds)
    n = len(pts)
    path = []
    for i, (c, r) in enumerate(pts):
        t = i / (n - 1)
        path.append((c, r, z, w0 + (w1 - w0) * t, h0 + (h1 - h0) * t))
    if round_ends:
        (c0, r0), (c1, r1) = pts[0], pts[1]
        d = math.hypot(c1 - c0, r1 - r0) or 1
        start = (c0 - (c1 - c0) / d * w0 * 0.8, r0 - (r1 - r0) / d * w0 * 0.8, z, 0.0, 0.0)
        (c0, r0), (c1, r1) = pts[-1], pts[-2]
        d = math.hypot(c1 - c0, r1 - r0) or 1
        end = (c0 - (c1 - c0) / d * w1 * 0.8, r0 - (r1 - r0) / d * w1 * 0.8, z, 0.0, 0.0)
        mid0 = (*pts[0], z, w0 * 0.75, h0 * 0.75)
        mid1 = (*pts[-1], z, w1 * 0.75, h1 * 0.75)
        path = [start, mid0] + path[1:-1] + [mid1, end]
    sweep(bm, path, sides=sides, mat=mat)


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, angle=0.0, z_bottom=None):
    """An ellipsoid centred on pixel (col, row) at height z, radii in px (x, y) and units (z),
    rotated by `angle` radians in top view. `z_bottom` flattens its underside to that height.
    Its poles point along the sprite's Y, so its top is quads, not a fan of triangles."""
    before = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    ca, sa = math.cos(angle), math.sin(angle)
    for v in res["verts"]:
        ux, uy, uz = v.co.x, v.co.z, v.co.y  # swap so the poles lie along Y
        ex, ey = ux * rx_px * PX, uy * ry_px * PX
        zz = z + uz * rz
        if z_bottom is not None:
            zz = max(zz, z_bottom)
        v.co = Vector((X(col) + ex * ca - ey * sa, Y(row) + ex * sa + ey * ca, zz))
    bm.faces.ensure_lookup_table()
    faces = bm.faces[before:]
    bmesh.ops.reverse_faces(bm, faces=faces)  # swapping y and z mirrored the sphere
    for f in faces:
        f.material_index = mat
        f.smooth = True


def plate(bm, outline, z0, z1, mat=0):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges, counter-clockwise
    on screen."""
    pts = [(X(c - 0.5), Y(r - 0.5)) for c, r in outline]
    if sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) < 0:
        pts.reverse()  # common.slab wants it counter-clockwise seen from above
    before = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[before:]:
        f.smooth = False


# --- the membrane: a bevelled slab over a pixel mask, holes and all ------------------------------

def mask_loops(mask):
    """Boundary loops (lists of (col, row) pixel corners) of a boolean mask[r][c]."""
    inside = lambda c, r: 0 <= r < H and 0 <= c < W and mask[r][c]  # noqa: E731
    edges = {}
    for r in range(H):
        for c in range(W):
            if not inside(c, r):
                continue
            if not inside(c, r - 1):
                edges[(c, r)] = (c + 1, r)
            if not inside(c + 1, r):
                edges[(c + 1, r)] = (c + 1, r + 1)
            if not inside(c, r + 1):
                edges[(c + 1, r + 1)] = (c, r + 1)
            if not inside(c - 1, r):
                edges[(c, r + 1)] = (c, r)
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
    return loops


def _round_loop(loop, rounds=2):
    pts = [Vector(p) for p in loop]
    for _ in range(rounds):
        out = []
        n = len(pts)
        for i in range(n):
            p, q = pts[i], pts[(i + 1) % n]
            out.append(p.lerp(q, 0.25))
            out.append(p.lerp(q, 0.75))
        pts = out
    return [(p.x, p.y) for p in pts[::2]]


def membrane(bm, mask, z0, z1, inset_px=1.0, step=0.5, mat=0, min_loop=10):
    """A slab over the mask's pixels (holes kept; loops shorter than `min_loop` corners are
    dropped, which fills pinholes and drops specks) from z0 up to z1, its top edge bevelled:
    it rises `step` of the way at full size, then steps in by `inset_px` for the rest."""
    loops = [lp for lp in mask_loops(mask) if len(lp) >= min_loop]
    before_v = len(bm.verts)
    edges = []
    for lp in loops:
        pts = _round_loop(lp)
        vs = [bm.verts.new((X(c - 0.5), Y(r - 0.5), z0)) for c, r in pts]
        for a, b in zip(vs, vs[1:] + vs[:1]):
            edges.append(bm.edges.new((a, b)))
    res = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)
    faces = [f for f in res["geom"] if isinstance(f, bmesh.types.BMFace)]
    # triangle_fill fills holes too: drop faces whose centre is outside the mask.
    keep, drop = [], []
    for f in faces:
        cen = f.calc_center_median()
        (keep if _inside_loops(cen.x, cen.y, loops) else drop).append(f)
    bmesh.ops.delete(bm, geom=drop, context="FACES_ONLY")
    bmesh.ops.reverse_faces(bm, faces=[f for f in keep if f.normal.z < 0])
    ext = bmesh.ops.extrude_face_region(bm, geom=keep)
    top = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMFace)]
    verts = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, (z1 - z0) * step), verts=verts)
    if inset_px:
        bmesh.ops.inset_region(bm, faces=top, thickness=inset_px * PX, depth=(z1 - z0) * (1 - step),
                               use_even_offset=True)
    bm.verts.ensure_lookup_table()
    new_faces = set()
    for v in bm.verts[before_v:]:
        new_faces.update(v.link_faces)
    for f in new_faces:
        f.material_index = mat
        f.smooth = False
    return new_faces


def covered(mask, min_loop=10):
    """Which pixels the membrane over `mask` covers (pinholes filled, specks dropped)."""
    loops = [lp for lp in mask_loops(mask) if len(lp) >= min_loop]
    return [[_inside_loops(X(c), Y(r), loops) for c in range(W)] for r in range(H)]


def _inside_loops(x, y, loops):
    """Even-odd test of Blender (x, y) against pixel-corner loops."""
    c = x * 12 + W / 2
    r = H / 2 - y * 12
    inside = False
    for lp in loops:
        n = len(lp)
        for i in range(n):
            (c0, r0), (c1, r1) = lp[i], lp[(i + 1) % n]
            if (r0 > r) != (r1 > r):
                cx = c0 + (r - r0) * (c1 - c0) / (r1 - r0)
                if cx > c:
                    inside = not inside
    return inside


# --- the grey tube wall ------------------------------------------------------------------------

def tube_strands(grid, allowed, max_w=6, min_bright=2):
    """Trace the grey tube texture: each row is cut into tubes at the dark grooves (pixels darker
    than `min_bright` above index 96, or outline) and at local brightness minima; tubes wider than
    `max_w` are split. Tubes in neighbouring rows that overlap are linked into strands. Returns a
    list of strands, each a list of (row, first_col, last_col). `allowed(c, r)` masks out pixels
    that belong to something else."""
    def bright(r, c):
        v = grid[r][c]
        if v >= 96 and allowed(c, r):
            return v - 96
        return None

    segs = []
    for r in range(H):
        row = [bright(r, c) for c in range(W)]
        runs, cur = [], []
        for c in range(W):
            if row[c] is not None and row[c] >= min_bright:
                cur.append(c)
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        out = []
        for run in runs:
            pieces, p = [], [run[0]]
            for i in range(1, len(run)):
                c = run[i]
                if i < len(run) - 1 and row[c] < row[c - 1] and row[c] <= row[c + 1] and len(p) >= 2:
                    pieces.append(p)
                    p = [c]
                else:
                    p.append(c)
            pieces.append(p)
            for pc in pieces:
                n = len(pc)
                k = math.ceil(n / max_w)
                for j in range(k):
                    sub = pc[j * n // k:(j + 1) * n // k]
                    out.append((sub[0], sub[-1]))
        segs.append(out)

    strands, owner = [], {}
    for r in range(H):
        used = set()
        for i, s in enumerate(segs[r]):
            best, bo = None, 0
            if r > 0:
                for k, t in enumerate(segs[r - 1]):
                    ov = min(s[1], t[1]) - max(s[0], t[0]) + 1
                    if (ov >= 1 and abs((s[0] + s[1]) / 2 - (t[0] + t[1]) / 2) <= 2
                            and k not in used and ov > bo):
                        best, bo = k, ov
            if best is not None:
                used.add(best)
                sid = owner[(r - 1, best)]
                strands[sid].append((r, s[0], s[1]))
            else:
                sid = len(strands)
                strands.append([(r, s[0], s[1])])
            owner[(r, i)] = sid
    return strands


def tube_wall(bm, grid, allowed, z, mapper, under, sides=6, max_h=0.085, min_rows=2, every=2):
    """Sweep a tube along each traced strand (see tube_strands), painted from the sprite."""
    first = len(bm.faces)
    for st in tube_strands(grid, allowed):
        if len(st) < min_rows:
            continue
        # Centres and widths smoothed along the strand ([1, 2, 1]), so the tube waves gently
        # instead of following every pixel step.
        cs = [(a + e) / 2 for _, a, e in st]
        ws = [(e - a + 1) / 2 * 1.25 for _, a, e in st]
        sm = lambda v, i: (v[max(i - 1, 0)] + 2 * v[i] + v[min(i + 1, len(v) - 1)]) / 4  # noqa: E731
        idx = list(range(0, len(st), every))
        if idx[-1] != len(st) - 1:
            idx.append(len(st) - 1)
        pts = []
        for i in idx:
            hw = sm(ws, i)
            pts.append((sm(cs, i), st[i][0], z, hw, min(max_h, hw * PX * 0.75)))
        # Round ends half a pixel beyond the first and last rows.
        c0, r0, _, w0, h0 = pts[0]
        c1, r1, _, w1, h1 = pts[-1]
        path = ([(c0, r0 - 0.5, z, 0.0, 0.0), (c0, r0 - 0.25, z, w0 * 0.7, h0 * 0.7)] + pts
                + [(c1, r1 + 0.25, z, w1 * 0.7, h1 * 0.7), (c1, r1 + 0.5, z, 0.0, 0.0)])
        sweep(bm, path, sides=sides, mat=0)
    paint(bm, first, grid, mapper, under=under)


# --- object, preview -----------------------------------------------------------------------------

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


def composite_png(grid, colors, out):
    """The assembly's sprite (first frames) as one 48 x 56 image."""
    import numpy as np
    img = np.zeros((H, W, 4), dtype=np.float32)
    for r in range(H):
        for c in range(W):
            v = grid[r][c]
            if v >= 0:
                img[r, c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def export_assembly(root, obj, pieces, sprite_grid, sprite):
    """Split `obj` (built in assembly coordinates) into its pieces, export each, and render the
    previews if asked: the whole assembly to the --preview path and each piece beside it.
    pieces: [(name, col0, row0)] as for load_grid."""
    layout = [(name, c0 + 12 - W / 2, r0 + 14 - H / 2) for name, c0, r0 in pieces]
    parts = common.split_assembly(obj, layout)
    for name, _, _ in pieces:
        data = common.load_sprite(root, name)
        common.export_sprite_model(root, [parts[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(sprite_grid, sprite["colors"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=4, view_px=480)
        for name, _, _ in pieces:
            data = common.load_sprite(root, name)
            img = root / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([parts[name]], str(out.parent / f"{name}.png"), img, size=2)
    return parts


# --- footprints (which pixels a hand-placed part covers in top view) -----------------------------

def in_ellipse(c, r, col, row, rx, ry, angle=0.0, grow=0.0):
    """Is pixel (c, r) inside the top-view ellipse of an ellipsoid placed with `ellipsoid`?"""
    dx, dy = c - col, -(r - row)  # screen rows grow down; Blender Y up
    ca, sa = math.cos(angle), math.sin(angle)
    u, v = dx * ca + dy * sa, -dx * sa + dy * ca
    return (u / (rx + grow)) ** 2 + (v / (ry + grow)) ** 2 <= 1.0


def in_path(c, r, path, grow=0.0):
    """Is pixel (c, r) within a swept path's half width (path of (col, row, z, hw, hh))?"""
    for (c0, r0, _, w0, _), (c1, r1, _, w1, _) in zip(path, path[1:]):
        dx, dy = c1 - c0, r1 - r0
        ln2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((c - c0) * dx + (r - r0) * dy) / ln2))
        px, py = c0 + dx * t, r0 + dy * t
        if math.hypot(c - px, r - py) <= w0 + (w1 - w0) * t + grow:
            return True
    return False
