"""Helpers shared by batch b050's model scripts: the two walls of fire in level 4.6 (newsh3.shp).

Each wall is an assembly of four 2x2 pieces: a column three pieces tall (a big flame licking up to
a tall tip) and a curling tongue of fire beside its bottom piece. The fire is built from its
sprite: a rounded body following the flame's outline, with a 3D tongue of flame along every
bright streak in the sprite (the streaks run up the flames). Tongues are layered by brightness:
each streak's tongue takes the colour of most of the streak, and where it burns hotter a thinner
core of the brighter colour rides on top, so the brightest parts stand highest.

Coordinates: the assembly is composited into one grid of palette indices (W x H px, grid column
c / row r); the Blender origin is the grid's centre, sprite up is +Y, one px is 1/12 unit.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12
FIRE = 112  # palette indices 112 (deep red) to 127 (white) are the fire ramp


# --- the composite grid --------------------------------------------------------------------------

class Grid:
    """An assembly's pieces (first frames) composited into one grid of palette indices."""

    def __init__(self, root, pieces, x0, y0, w, h):
        """`pieces` is [(model, cx, cy)] in screen px; (x0, y0) is the grid's top-left screen px."""
        self.w, self.h, self.x0, self.y0 = w, h, x0, y0
        self.cells = [[-1] * w for _ in range(h)]
        self.colors = {}
        self.layout = []
        for name, cx, cy in pieces:
            data = common.load_sprite(root, name)
            self.colors.update(data["colors"])
            for r, line in enumerate(data["frames"][0]["pixels"]):
                for c, v in enumerate(line):
                    if v >= FIRE:  # index 1 is outline, which the game draws itself
                        self.cells[cy - 14 - y0 + r][cx - 12 - x0 + c] = v
            # split_assembly wants each piece's centre relative to the Blender origin, in px with y down.
            self.layout.append((name, cx - (x0 + w / 2), cy - (y0 + h / 2)))

    def v(self, r, c):
        """Brightness 0..15 of a cell, -1 outside the fire."""
        if 0 <= r < self.h and 0 <= c < self.w and self.cells[r][c] >= FIRE:
            return self.cells[r][c] - FIRE
        return -1

    def X(self, c):
        """Grid column (pixel centre, fractions allowed) to Blender X."""
        return (c + 0.5 - self.w / 2) * PX

    def Y(self, r):
        """Grid row (pixel centre) to Blender Y."""
        return (self.h / 2 - r - 0.5) * PX

    def sprite(self):
        """A sprite-like dict with every piece's colours, for common.palette_material."""
        return {"name": "fire", "colors": self.colors}


# --- the body: a rounded slab following the outline ---------------------------------------------

def _boundary_loops(grid):
    """Closed loops of pixel corners (grid units, y down) round the fire, with the fire on the
    left seen from above (outer loops counter-clockwise in Blender, holes clockwise)."""
    nxt = {}
    def edge(a, b):
        nxt.setdefault(a, []).append(b)
    for r in range(grid.h):
        for c in range(grid.w):
            if grid.v(r, c) < 0:
                continue
            if grid.v(r + 1, c) < 0:
                edge((c, r + 1), (c + 1, r + 1))
            if grid.v(r, c + 1) < 0:
                edge((c + 1, r + 1), (c + 1, r))
            if grid.v(r - 1, c) < 0:
                edge((c + 1, r), (c, r))
            if grid.v(r, c - 1) < 0:
                edge((c, r), (c, r + 1))
    loops = []
    while nxt:
        start = next(iter(nxt))
        loop = [start]
        prev, cur = None, start
        while True:
            outs = nxt[cur]
            if len(outs) > 1 and prev is not None:
                # Two pixels touching at a corner: keep them apart (turn towards the fire).
                d = (cur[0] - prev[0], cur[1] - prev[1])
                def turn(p):
                    e = (p[0] - cur[0], p[1] - cur[1])
                    return d[0] * e[1] - d[1] * e[0]  # in grid coords (y down), < 0 is a left turn on screen
                outs.sort(key=turn)
            n = outs.pop(0)
            if not outs:
                del nxt[cur]
            prev, cur = cur, n
            if cur == start:
                break
            loop.append(cur)
        loops.append(loop)
    return loops


def _chaikin(pts, iterations=2):
    for _ in range(iterations):
        out = []
        n = len(pts)
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            out.append((0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1))
            out.append((0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1))
        pts = out
    return pts


def _simplify(pts, tol):
    """Drop points closer than `tol` to the line through their neighbours (closed loop)."""
    pts = list(pts)
    changed = True
    while changed and len(pts) > 6:
        changed = False
        best, bi = tol, -1
        n = len(pts)
        for i in range(n):
            (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[(i + 1) % n]
            dx, dy = cx - ax, cy - ay
            ln = math.hypot(dx, dy) or 1e-9
            d = abs((bx - ax) * dy - (by - ay) * dx) / ln
            if d < best:
                best, bi = d, i
        if bi >= 0:
            pts.pop(bi)
            changed = True
    return pts


def body(grid, bm, mat_index, half_thickness=0.05, bevel=0.035, z=0.0, coll=None):
    """A slab following the fire's outline (holes included) with rounded edges, added to `bm`."""
    cu = bpy.data.curves.new("fire_body", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = half_thickness
    cu.bevel_depth = bevel
    cu.bevel_resolution = 1
    cu.offset = -bevel  # keep the outer edge on the outline
    for loop in _boundary_loops(grid):
        if len(loop) < 4:
            continue
        pts = _simplify(_chaikin(loop), 0.18)
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, (gx, gy) in zip(sp.points, pts):
            p.co = ((gx - grid.w / 2) * PX, (grid.h / 2 - gy) * PX, 0.0, 1.0)
        sp.use_cyclic_u = True
    obj = bpy.data.objects.new("fire_body", cu)
    (coll or bpy.context.scene.collection).objects.link(obj)
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.curves.remove(cu)
    tmp = bmesh.new()
    tmp.from_mesh(mesh)
    bpy.data.meshes.remove(mesh)
    bmesh.ops.remove_doubles(tmp, verts=tmp.verts, dist=1e-5)
    bmesh.ops.translate(tmp, vec=(0, 0, z), verts=tmp.verts)
    _append(bm, tmp, mat_index, smooth_sides=True)
    tmp.free()


def _append(bm, src, mat_index, smooth_sides=False):
    vmap = {}
    for v in src.verts:
        vmap[v] = bm.verts.new(v.co)
    for f in src.faces:
        nf = bm.faces.new([vmap[v] for v in f.verts])
        nf.material_index = mat_index
        nf.smooth = smooth_sides and abs(f.normal.z) < 0.98


# --- tongues of flame along the bright streaks --------------------------------------------------

class Transposed:
    """The grid seen sideways (rows and columns swapped), to find streaks running across it."""

    def __init__(self, grid):
        self.grid, self.w, self.h = grid, grid.h, grid.w

    def v(self, r, c):
        return self.grid.v(c, r)

    def pos(self, c, r):
        return self.grid.X(r), self.grid.Y(c)


def _pos(g, c, r):
    return g.pos(c, r) if hasattr(g, "pos") else (g.X(c), g.Y(r))


def _ridges(grid, thr):
    """Per row, the bright local maxima along the row: [(col, brightness)]."""
    out = []
    for r in range(grid.h):
        pts = []
        c = 0
        while c < grid.w:
            v = grid.v(r, c)
            if v < thr:
                c += 1
                continue
            e = c
            while e + 1 < grid.w and grid.v(r, e + 1) == v:
                e += 1
            if grid.v(r, c - 1) < v and grid.v(r, e + 1) < v:
                pts.append(((c + e) / 2, v))
            c = e + 1
        out.append(pts)
    return out


def streaks(grid, thr=5, min_len=3):
    """Chains of ridge points running along the grid's rows: lists of (col, row, brightness),
    first row first. A chain may skip one row."""
    ridge = _ridges(grid, thr)
    active, done = [], []
    for r in range(grid.h - 1, -1, -1):
        used, claimed = set(), []
        for c, v in ridge[r]:
            best = None
            for i, ch in enumerate(active):
                if i in used:
                    continue
                d = abs(ch[-1][0] - c)
                if d <= 1.0 and (best is None or d < abs(active[best][-1][0] - c)):
                    best = i
            if best is None:
                claimed.append([(c, r, v)])
            else:
                used.add(best)
                active[best].append((c, r, v))
                claimed.append(active[best])
        keep = []
        for i, ch in enumerate(active):
            if i in used:
                continue
            if ch[-1][1] - r < 2:  # allow one missing row
                keep.append(ch)
            else:
                done.append(ch)
        active = claimed + keep
    done += active
    return [list(reversed(ch)) for ch in done if len(ch) >= min_len]


def _half_width(grid, c, r, v):
    """Half the width (px) of the streak at (c, r) and its centre's offset: neighbours at most a
    few levels dimmer."""
    lo = max(3, v - 4)
    ci = int(round(c))
    left = right = 0
    while left < 4 and grid.v(r, ci - left - 1) >= lo:
        left += 1
    while right < 4 and grid.v(r, ci + right + 1) >= lo:
        right += 1
    return (left + right + 1) / 2, (right - left) / 2


def sweep(bm, path, sides=6, mat_index=0):
    """A tube along a path of (x, y, z, half_width, half_height) in units; rings stand across the
    path in the XY plane, zero-size rings collapse to points (tips)."""
    pts = [Vector(p[:3]) for p in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
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
    if len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat_index
        f.smooth = True


def _quantile(vals, q):
    s = sorted(vals)
    return s[min(len(s) - 1, int(q * len(s)))]


def tongue(grid, bm, chain, mat_index, z_base, scale=1.0, lift=0.0, sides=6, min_w=0.45, tip=1.4):
    """One tongue of flame along a chain of (col, row, brightness), first row first: pointed at
    its first end (the top of an upright flame), tapering at the other, as wide as the streak and
    rounded on top."""
    step = 2 if len(chain) < 12 else 3
    keep = [chain[i] for i in range(0, len(chain), step)]
    if keep[-1] is not chain[-1]:
        keep.append(chain[-1])
    widths = []
    path = []
    for c, r, v in keep:
        hw, shift = _half_width(grid, c, r, v)
        widths.append(max(min_w, hw * scale))
        x, y = _pos(grid, c + shift * 0.5, r)
        path.append([x, y])
    # A flame's profile: from its point it widens to the streak's full width two thirds of the way
    # down, then narrows a little to its foot.
    wmax = _quantile(widths, 0.7)
    n = len(widths)
    sm = []
    for i in range(n):
        t = (i + 0.5) / n
        f = (t / 0.6) ** 0.6 if t < 0.6 else 1 - 0.3 * ((t - 0.6) / 0.4) ** 2
        sm.append(max(min_w, wmax * f))
    for i in range(1, len(path) - 1):
        for k in (0, 1):
            path[i][k] = (path[i - 1][k] + 2 * path[i][k] + path[i + 1][k]) / 4
    full = []
    for (x, y), hw in zip(path, sm):
        h = (0.55 * hw + 0.25) * PX
        full.append((x, y, z_base + lift + h * 0.35, hw * PX, h))
    def beyond(a, b, d):
        dx, dy = a[0] - b[0], a[1] - b[1]
        ln = math.hypot(dx, dy) or 1.0
        return (a[0] + dx / ln * d * PX, a[1] + dy / ln * d * PX, a[2], 0.0, 0.0)
    if len(full) > 1:
        head, foot = beyond(full[0], full[1], tip), beyond(full[-1], full[-2], 0.8)
    else:
        head = (full[0][0], full[0][1] + tip * PX, full[0][2], 0.0, 0.0)
        foot = (full[0][0], full[0][1] - 0.8 * PX, full[0][2], 0.0, 0.0)
    sweep(bm, [head] + full + [foot], sides=sides, mat_index=mat_index)


def _tongues(g, bm, chains, level_mat, z_base, sides, core_gap, tip):
    count = 0
    for chain in chains:
        vals = [v for _, _, v in chain]
        outer = _quantile(vals, 0.4)
        tongue(g, bm, chain, level_mat(outer), z_base, sides=sides, tip=tip)
        count += 1
        # Runs of the streak that burn clearly hotter than the tongue get a thinner core on top.
        for gap, scale, lift in ((core_gap, 0.6, 0.03), (core_gap + 3, 0.35, 0.055)):
            run = []
            for p in chain + [(0, 0, -1)]:
                if p[2] >= outer + gap:
                    run.append(p)
                    continue
                if len(run) >= 2:
                    rv = _quantile([q[2] for q in run], 0.4)
                    tongue(g, bm, run, level_mat(rv), z_base, scale=scale, lift=lift, sides=sides,
                           min_w=0.4, tip=tip * 0.7)
                    count += 1
                run = []
    return count


def flames(grid, bm, level_mat, z_base, thr=4, core_gap=3, sides=6):
    """Tongues on every upright streak, plus the streaks running sideways (curling fire) that
    the upright ones miss, with hotter cores riding on them. Returns the number of tongues."""
    up = streaks(grid, thr)
    covered = {(int(round(c)) + dc, r) for ch in up for c, r, _ in ch for dc in (-1, 0, 1)}
    side_grid = Transposed(grid)
    side = []
    for ch in streaks(side_grid, thr + 1, min_len=4):
        # In the transposed grid a point is (row, col, v).
        fresh = [p for p in ch if (p[1], int(round(p[0]))) not in covered]
        if len(fresh) >= 0.7 * len(ch):
            side.append(ch)
    n = _tongues(grid, bm, up, level_mat, z_base, sides, core_gap, tip=1.4)
    n += _tongues(side_grid, bm, side, level_mat, z_base, sides, core_gap, tip=0.8)
    return n


# --- materials, objects, previews --------------------------------------------------------------

LEVELS = [(116, 1.8), (118, 2.0), (120, 2.5), (122, 3.0), (124, 4.0), (126, 5.0)]


def fire_materials(sprite, tag):
    """One emissive material per step of the fire ramp, darkest (the body) first."""
    return [common.palette_material(sprite, i, tag, metallic=0.0, roughness=0.6, emission_strength=s)
            for i, s in LEVELS]


def level_of(v):
    """Material slot for brightness v (0..15): the nearest step of LEVELS at or below it."""
    idx = v + FIRE
    slot = 0
    for k, (i, _) in enumerate(LEVELS):
        if idx >= i - 1:
            slot = k
    return slot


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


def composite_png(grid, out, pad_w):
    """The assembly's sprite as one image, padded sideways to `pad_w` px (render_preview wants the
    24:28 shape)."""
    import numpy as np
    img = np.zeros((grid.h, pad_w, 4), dtype=np.float32)
    off = (pad_w - grid.w) // 2
    for r in range(grid.h):
        for c in range(grid.w):
            v = grid.cells[r][c]
            if v >= 0:
                img[r, off + c] = [*(ch / 255 for ch in grid.colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", pad_w, grid.h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def build_wall(root, name, pieces, x0, y0, w, h, file_argv):
    """Build a wall of fire (assembly `name` of `pieces` [(model, cx, cy)]), split it into its
    pieces, export each and, with --preview, render the whole and each piece."""
    grid = Grid(root, pieces, x0, y0, w, h)
    coll = common.reset_collection(name)
    tag = name.replace("assembly-", "")
    mats = fire_materials(grid.sprite(), tag)
    bm = bmesh.new()
    half, bevel = 0.05, 0.035
    zc = -0.07
    body(grid, bm, 0, half_thickness=half, bevel=bevel, z=zc, coll=coll)
    n = flames(grid, bm, level_of, z_base=zc + half + bevel - 0.02)
    print(f"{name}: {n} tongues")
    obj = to_object(name, bm, mats, coll)
    parts = common.split_assembly(obj, grid.layout)
    for model, _, _ in grid.layout:
        data = common.load_sprite(root, model)
        common.export_sprite_model(root, [parts[model]], f"enemies/{model}", data["sprites"])
    if "--preview" in file_argv:
        import tempfile
        out = Path(file_argv[file_argv.index("--preview") + 1])
        size = math.ceil(h * 12 / 14 / 12)
        ref = composite_png(grid, Path(tempfile.mkdtemp()) / "assembly.png", size * 12)
        common.render_preview([obj], str(out), str(ref), size=size, view_px=640)
        for model, _, _ in grid.layout:
            data = common.load_sprite(root, model)
            img = root / "reference" / "models" / model / data["frames"][0]["image"]
            common.render_preview([parts[model]], str(out.parent / f"{model}.png"), img, size=2)
    return obj, parts
