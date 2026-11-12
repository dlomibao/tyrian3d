"""Shared kit for DELIANI's structure tiles (shapesz.dat, map 1-5 and its copy 3-11 New Deli): the steel
girder track of background 2 (layer 1) and the purple hull of background 3 (layer 2). DECISIONS.md D34
(tile models by pattern), D83 (plating, pipes and rails on layers 1-2 are models, not paintings), D65
(hard surface, AO/roughness bake only, no concept projection).

Both are modular kits: every tile is a piece that joins its neighbours edge to edge (a straight girder
meets a corner or a junction; a hull rim meets a rounded corner). So each tile becomes its own model
(a one-tile pattern), built *in context*: the tile is modelled with a neighbour on each side it opens
to (the one the maps use most), the whole 3x3 block is built, bevelled and baked together, and only the
centre is kept (lib_tiles.cut_to_tile). A bevel or an occlusion gradient never stops at a tile edge, so
copies meet without a seam whatever their neighbours, as the pixel art does.

Texture: the model's own bake, two small maps: ambient occlusion at two scales as a grey multiplier, and
roughness/metalness; Base Color = map x palette colour, so palettes and fades still apply (D65: no concept
projection). The girders use usp_talon.bake_maps (Cycles, with an edge lift on their bevels), with the
neighbours in the scene as occluders (the centre cut out). The hull is a height field, so its occlusion is
computed from the field itself, with the neighbours' heights round it (field_bake): Cycles' rays leaving
a finely tessellated curved surface catch its own facets and paint dark triangles on the tubes. Either
way a tile's occlusion near its edges is what it gets in the map.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_tiles as lt  # noqa: E402

TILE_W, TILE_H = lt.TILE_W, lt.TILE_H
PX = lt.PX


# --- Tiles and context -----------------------------------------------------------------------------

def pixels(ts, n):
    """Tile n's 1x pixels (palette indices; 0 = transparent on layers 1-2)."""
    return ts.tiles[n]["px"]


def usual_neighbour(ts, n, side, allowed=None):
    """The tile most often on `side` of n in the maps (tiles.json neighbours), or -1 for none.
    `allowed`: only tiles of this set count (the kit's own)."""
    key = {"L": "left", "R": "right", "U": "up", "D": "down"}[side]
    for nb in ts.tiles[n]["neighbours"][key]:
        t = nb["tile"]
        if t >= 0 and (allowed is None or t in allowed):
            return t
    return -1


def context_cells(ts, n, sides, diagonals=None):
    """The 3x3 block of tiles round n: `sides` maps L/R/U/D to a tile or -1; `diagonals` maps
    UL/UR/DL/DR to a tile or -1 (default empty)."""
    d = diagonals or {}
    return [[d.get("UL", -1), sides.get("U", -1), d.get("UR", -1)],
            [sides.get("L", -1), n, sides.get("R", -1)],
            [d.get("DL", -1), sides.get("D", -1), d.get("DR", -1)]]


def context_grid(ts, cells):
    """The block's 1x pixels as one array: palette index, 0 transparent, -1 where no tile is."""
    rows, cols = len(cells), len(cells[0])
    out = np.full((rows * TILE_H, cols * TILE_W), -1, dtype=np.int32)
    for r, row in enumerate(cells):
        for c, t in enumerate(row):
            if t >= 0:
                out[r * TILE_H:(r + 1) * TILE_H, c * TILE_W:(c + 1) * TILE_W] = pixels(ts, t)
    return out


def region_index(ts, values, drop=0.15, prefer=None):
    """The palette index a region stands for: the median brightness after dropping the darkest and
    brightest `drop` (the art's shading and sheen are lighting, not paint; CLAUDE.md art rule 2).
    `prefer`: only indices of this set count when any are present."""
    vals = [int(v) for v in np.asarray(values).ravel() if v > 0]
    if prefer is not None:
        p = [v for v in vals if v in prefer]
        vals = p or vals
    if not vals:
        return None
    vals.sort(key=lambda v: ts.lum[v])
    k = int(len(vals) * drop)
    core = vals[k:len(vals) - k] or vals
    return core[len(core) // 2]


# --- Geometry --------------------------------------------------------------------------------------

def sharp_edges(bm, angle=40):
    """Edges between two faces meeting at more than `angle` degrees."""
    out = []
    lim = math.radians(angle)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > lim:
            out.append(e)
    return out


def bevel(bm, offset, segments=2, angle=40, profile=0.5, material=-1):
    """Bevel the sharp edges; the new faces take `material` (a slot; -1: Blender's choice, slot 0)."""
    edges = sharp_edges(bm, angle)
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=offset, offset_type="OFFSET", segments=segments, profile=profile,
                        affect="EDGES", clamp_overlap=True, harden_normals=False, material=material)


def tidy(bm):
    lt.dissolve_coplanar(bm)


def tidy_flat(bm, angle=0.5):
    """dissolve_coplanar on the flat-shaded faces only (smooth surfaces keep their grid); faces within
    `angle` degrees of each other count as one plane."""
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    edges = [e for e in bm.edges if e.link_faces and not any(f.smooth for f in e.link_faces)]
    verts = [v for v in bm.verts if v.link_faces and not any(f.smooth for f in v.link_faces)]
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(angle), verts=verts, edges=edges, delimit={"MATERIAL"})


def copy_bm(bm):
    me = bpy.data.meshes.new("_tmp_copy")
    bm.to_mesh(me)
    out = bmesh.new()
    out.from_mesh(me)
    bpy.data.meshes.remove(me)
    return out


def outside_centre(bm, cols=1, rows=1):
    """The block without its centre tile: cut along the centre's edges and drop what's inside (the
    occluders for the centre's bake)."""
    hw, hh = TILE_W * cols / 2 * PX, TILE_H * rows / 2 * PX
    for co, no in (((hw, 0, 0), (1, 0, 0)), ((-hw, 0, 0), (1, 0, 0)), ((0, hh, 0), (0, 1, 0)), ((0, -hh, 0), (0, 1, 0))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector(co), plane_no=Vector(no))
    eps = 1e-4
    inner = [f for f in bm.faces if abs(f.calc_center_median().x) < hw - eps and abs(f.calc_center_median().y) < hh - eps]
    bmesh.ops.delete(bm, geom=inner, context="FACES")
    return bm


# --- Smooth part edges (D149) ----------------------------------------------------------------------
# A height-field tile (mask_slab) is a grid of cells, so its outline and every edge between two parts
# (a clamp and its housing, a plate and its seam) run along the cells' edges: the art's pixel
# staircases, which read as stairs at 4K. The edges are moved instead onto smooth curves fitted through
# the art's edges: each edge between two parts is a chain of grid corners, and each corner moves to a
# Gaussian average of its chain, as D118 fitted the Silver Ship's plates through the middles of the
# mask's steps. Straight runs stay where they are, a staircase becomes a straight or curved line, and a
# real corner (two straight runs of at least `corner_run` cells meeting square) stays square.


def boundary_moves(labels, sigma=2.0, max_move=0.6, corner_run=3, min_loop=8, pin_x=(), pin_y=(), pin_solid=None,
                   outline_sigma=None, outline_grow=0.0, keep=None):
    """Where each grid corner of `labels` (an int per cell, -1 outside) moves, in cells (dx right, dy
    down), arrays of shape (h + 1, w + 1). A corner on one edge between two parts (two of its four
    edges are part edges) moves along that edge's chain; junctions of three parts, the array's border,
    the columns `pin_x` and rows `pin_y` (tile edges: pinned, so a tile and its neighbour, each built
    in its own block, meet exactly; with `pin_solid`, only where it has solid cells on both sides of
    the line, as an edge with nothing across it has no neighbour to meet), square corners and loops
    shorter than `min_loop` stay put. The
    average is applied twice and the second's shrinkage taken back (2 G(p) - G(G(p))), so a curve keeps
    its size while the steps go. `outline_sigma` (default `sigma`): the outline's own, smaller where the
    model's top view must stay close to the art's 1x mask. `outline_grow` (cells): the outline's
    smoothed stretches are pushed out by this much, as the 2x art and the curve through its steps both
    sit inside the 1x art's steps. `keep` (bool, (h + 1, w + 1)): corners that stay put, e.g. round a
    machined part whose straight edges are already where they belong (D152)."""
    lab = np.asarray(labels)
    h, w = lab.shape
    lp = np.pad(lab, 1, constant_values=-1)
    vb = lp[1:-1, :-1] != lp[1:-1, 1:]  # (h, w + 1): edge (cx, cy)-(cx, cy + 1)
    hb = lp[:-1, 1:-1] != lp[1:, 1:-1]  # (h + 1, w): edge (cx, cy)-(cx + 1, cy)

    def nbrs(cx, cy):
        out = []
        if cy > 0 and vb[cy - 1, cx]:
            out.append((cx, cy - 1))
        if cy < h and vb[cy, cx]:
            out.append((cx, cy + 1))
        if cx > 0 and hb[cy, cx - 1]:
            out.append((cx - 1, cy))
        if cx < w and hb[cy, cx]:
            out.append((cx + 1, cy))
        return out

    def run(cx, cy, ddx, ddy):
        n = 0
        while n < corner_run:
            nx, ny = cx + ddx, cy + ddy
            if ddx and not (0 <= min(cx, nx) and max(cx, nx) <= w and 0 <= cy <= h and hb[cy, min(cx, nx)]):
                break
            if ddy and not (0 <= min(cy, ny) and max(cy, ny) <= h and 0 <= cx <= w and vb[min(cy, ny), cx]):
                break
            cx, cy, n = nx, ny, n + 1
        return n

    pin_x, pin_y = set(pin_x), set(pin_y)
    sp = None if pin_solid is None else np.pad(np.asarray(pin_solid, dtype=bool), 1)

    def pinned(cx, cy):
        if cx not in pin_x and cy not in pin_y:
            return False
        if sp is None:
            return True
        q = sp[cy:cy + 2, cx:cx + 2]  # cells (cy - 1, cy) x (cx - 1, cx)
        return bool((cx in pin_x and q[:, 0].any() and q[:, 1].any()) or (cy in pin_y and q[0].any() and q[1].any()))
    nb = {}
    fixed = set()
    ys, xs = np.nonzero(np.pad(vb, ((0, 1), (0, 0))) | np.pad(vb, ((1, 0), (0, 0)))
                        | np.pad(hb, ((0, 0), (0, 1))) | np.pad(hb, ((0, 0), (1, 0))))
    for cy, cx in zip(ys.tolist(), xs.tolist()):
        n = nbrs(cx, cy)
        nb[(cx, cy)] = n
        if len(n) != 2 or cx in (0, w) or cy in (0, h) or pinned(cx, cy) or (keep is not None and keep[cy, cx]):
            fixed.add((cx, cy))
            continue
        (ax, ay), (bx, by) = n
        if ax != bx and ay != by:  # a turn: square if both runs are long
            if run(cx, cy, ax - cx, ay - cy) >= corner_run and run(cx, cy, bx - cx, by - cy) >= corner_run:
                fixed.add((cx, cy))

    def smooth_open(p, sig):
        K = int(math.ceil(3 * sig))
        wts = np.exp(-0.5 * (np.arange(-K, K + 1) / sig) ** 2)
        n = len(p)
        out = p.copy()
        for i in range(1, n - 1):
            k = min(K, i, n - 1 - i)
            ww = wts[K - k:K + k + 1]
            out[i] = (p[i - k:i + k + 1] * ww[:, None]).sum(0) / ww.sum()
        return out

    def chain_sigma(a, b):
        """The outline (an edge with the outside on one side) takes outline_sigma."""
        if outline_sigma is None:
            return sigma
        (ax, ay), (bx, by) = a, b
        if ax == bx:  # vertical edge: cells left and right
            cy = min(ay, by)
            pair = (lp[cy + 1, ax], lp[cy + 1, ax + 1])
        else:
            cx = min(ax, bx)
            pair = (lp[ay, cx + 1], lp[ay + 1, cx + 1])
        return outline_sigma if -1 in pair else sigma

    def smooth_loop(p, sig):
        n = len(p)
        k = min(int(math.ceil(3 * sig)), (n - 1) // 2)
        ww = np.exp(-0.5 * (np.arange(-k, k + 1) / sig) ** 2)
        idx = (np.arange(n)[:, None] + np.arange(-k, k + 1)[None, :]) % n
        return (p[idx] * ww[None, :, None]).sum(1) / ww.sum()

    dx = np.zeros((h + 1, w + 1))
    dy = np.zeros((h + 1, w + 1))
    seen = set()

    def outward(chain):
        """+1 when the outside (-1) lies to the right of the chain's first edge (x right, y down), -1
        when to the left, 0 when the chain is not on the outline."""
        (ax, ay), (bx, by) = chain[0], chain[1]
        rx, ry = -(by - ay), bx - ax
        cx, cy = int(math.floor((ax + bx) / 2 + 0.5 * rx)), int(math.floor((ay + by) / 2 + 0.5 * ry))
        lx, ly = int(math.floor((ax + bx) / 2 - 0.5 * rx)), int(math.floor((ay + by) / 2 - 0.5 * ry))
        right, left = lp[cy + 1, cx + 1], lp[ly + 1, lx + 1]
        return 1 if right == -1 and left != -1 else (-1 if left == -1 and right != -1 else 0)

    def grow(chain, s, closed):
        """Push the moved stretches of an outline chain out by outline_grow."""
        side = outward(chain)
        if not side or not outline_grow:
            return s
        s = s.copy()
        n = len(chain)
        for i in range(n):
            if not closed and i in (0, n - 1):
                continue
            if math.hypot(s[i][0] - chain[i][0], s[i][1] - chain[i][1]) < 0.05:
                continue
            tx, ty = s[(i + 1) % n] - s[i - 1]
            t = math.hypot(tx, ty)
            if t > 1e-9:
                s[i] = s[i] + outline_grow * side * np.array([-ty, tx]) / t
        return s

    def apply(chain, s):
        for (cx, cy), q in zip(chain, s):
            mx, my = q[0] - cx, q[1] - cy
            m = math.hypot(mx, my)
            if m > max_move:
                mx, my = mx * max_move / m, my * max_move / m
            dx[cy, cx], dy[cy, cx] = mx, my

    # Open chains, from each fixed corner along each of its part edges to the next fixed corner.
    for start in fixed:
        for first in nb[start]:
            if (start, first) in seen:
                continue
            chain = [start]
            prev, cur = start, first
            while True:
                chain.append(cur)
                seen.add((prev, cur))
                seen.add((cur, prev))
                if cur in fixed:
                    break
                a, b = nb[cur]
                prev, cur = cur, (b if a == prev else a)
            if len(chain) < 3:
                continue
            p = np.array(chain, dtype=float)
            sig = chain_sigma(chain[0], chain[1])
            s1 = smooth_open(p, sig)
            apply(chain[1:-1], grow(chain, 2 * s1 - smooth_open(s1, sig), False)[1:-1])
    # Closed loops (no fixed corner on them).
    for c0 in list(nb):
        if c0 in fixed or not nb[c0] or (c0, nb[c0][0]) in seen:
            continue
        chain = [c0]
        prev, cur = c0, nb[c0][0]
        seen.add((prev, cur))
        seen.add((cur, prev))
        while cur != c0:
            chain.append(cur)
            a, b = nb[cur]
            prev, cur = cur, (b if a == prev else a)
            seen.add((prev, cur))
            seen.add((cur, prev))
        if len(chain) < min_loop:
            continue
        p = np.array(chain, dtype=float)
        sig = min(chain_sigma(chain[0], chain[1]), len(chain) / 8)
        s1 = smooth_loop(p, sig)
        apply(chain, grow(chain, 2 * s1 - smooth_loop(s1, sig), True))
    return dx, dy


def move_grid_verts(bm, frame, dx, dy):
    """Move a mask_slab mesh's vertices (still on their grid corners, top and bottom alike) by
    boundary_moves' dx, dy (cells)."""
    h, w = dx.shape[0] - 1, dx.shape[1] - 1
    for v in bm.verts:
        cx = int(round(v.co.x / frame.unit + frame.w / 2))
        cy = int(round(frame.h / 2 - v.co.y / frame.unit))
        if 0 <= cx <= w and 0 <= cy <= h:
            v.co.x += dx[cy, cx] * frame.unit
            v.co.y -= dy[cy, cx] * frame.unit


def machined_bar(bm, frame, rect, top, bottom, chamfer, mat, sharp=30, seg=2.0):
    """A bevelled bar (D152) added to `bm`: a box over `rect` (x0, y0, x1, y1 in `frame`'s cells), one
    segment per `seg` cells along its long side, every edge chamfered by `chamfer` (model units), its top at
    `top(s)` and its bottom at `bottom(s)` (heights at a position s along the long side, in cells, e.g.
    a curved clamp's face), so it bends with the surface it stands in. Smooth along its length, creased
    at its chamfers, so it reads as a machined part."""
    x0, y0, x1, y1 = rect
    along_x = (x1 - x0) >= (y1 - y0)
    s0, s1, a0, a1 = (x0, x1, y0, y1) if along_x else (y0, y1, x0, x1)
    n = max(1, int(round((s1 - s0) / seg)))
    tb = bmesh.new()

    def pt(s, a, up):
        cx, cy = (s, a) if along_x else (a, s)
        return tb.verts.new((frame.x(cx), frame.y(cy), 0.0 if up else -1.0))

    rings = []
    for i in range(n + 1):
        s = s0 + (s1 - s0) * i / n
        rings.append((pt(s, a0, False), pt(s, a0, True), pt(s, a1, True), pt(s, a1, False)))
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(4):
            tb.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k]))
    tb.faces.new(rings[0][::-1])
    tb.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(tb, faces=tb.faces)
    # Final heights before the bevel, so the chamfer is `chamfer` wide in model units.
    for v in tb.verts:
        s = ((v.co.x / frame.unit + frame.w / 2) if along_x else (frame.h / 2 - v.co.y / frame.unit))
        v.co.z = top(s) if v.co.z > -0.5 else bottom(s)
    edges = [e for e in tb.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(40)]
    bmesh.ops.bevel(tb, geom=edges, offset=chamfer, offset_type="OFFSET", segments=1, profile=0.5,
                    affect="EDGES", clamp_overlap=True, harden_normals=False)
    for f in tb.faces:
        f.material_index = mat
        f.smooth = True
    lim = math.radians(sharp)
    for e in tb.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > lim:
            e.smooth = False
    me = bpy.data.meshes.new("_bar")
    tb.to_mesh(me)
    tb.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def corner_heights(height, support):
    """mask_slab's corner heights with `smooth_top`: the mean of the supporting cells round each corner
    (h + 1, w + 1)."""
    hp = np.pad(np.where(support, height, 0.0), 1)
    sp = np.pad(support.astype(float), 1)
    tot = hp[:-1, :-1] + hp[:-1, 1:] + hp[1:, :-1] + hp[1:, 1:]
    cnt = sp[:-1, :-1] + sp[:-1, 1:] + sp[1:, :-1] + sp[1:, 1:]
    return tot / np.maximum(cnt, 1)


def warp_cells(arrays, dx, dy, k, corners=None):
    """Per-cell arrays resampled at `k` samples per cell through the same moves, so a bake computed
    from them follows the smoothed edges, not the art's steps: each sample takes the cell it came
    from (its position less the corners' moves there, bilinear). `corners` (h + 1, w + 1), e.g.
    corner_heights: also sampled bilinearly at the same source points, as the mesh's surface is, and
    returned last."""
    h, w = dx.shape[0] - 1, dx.shape[1] - 1
    fx = (np.arange(w * k) + 0.5) / k
    fy = (np.arange(h * k) + 0.5) / k
    mx = _resample(dx, h * k, w * k, fy, fx)
    my = _resample(dy, h * k, w * k, fy, fx)
    qx = np.clip(fx[None, :] - mx, 0, w - 1e-6)
    qy = np.clip(fy[:, None] - my, 0, h - 1e-6)
    sx = np.floor(qx).astype(int)
    sy = np.floor(qy).astype(int)
    out = [np.asarray(a)[sy, sx] for a in arrays]
    if corners is not None:
        tx, ty = qx - sx, qy - sy
        c = np.asarray(corners)
        out.append((c[sy, sx] * (1 - tx) + c[sy, sx + 1] * tx) * (1 - ty)
                   + (c[sy + 1, sx] * (1 - tx) + c[sy + 1, sx + 1] * tx) * ty)
    return out


# --- Materials -------------------------------------------------------------------------------------

class Mats:
    """Palette materials (pal_<index>_<tag>) for one tile model; `tag` is unique per model, because
    the bake rewires the materials of the model it textures."""

    def __init__(self, ts, tag, **defaults):
        self.ts, self.tag, self.defaults = ts, tag, defaults
        self.list = []
        self.slots = {}

    def __call__(self, index, **kw):
        key = (int(index), tuple(sorted(kw.items())))
        if key not in self.slots:
            opts = dict(self.defaults)
            opts.update(kw)
            emission = opts.pop("emission_strength", 0.0)
            suffix = "".join(f"_{k[0]}{v}" for k, v in sorted(kw.items()))
            name = f"pal_{int(index)}_{self.tag}{suffix}"
            color = common.srgb(*self.ts.rgb(index))
            mat = common.material(name, color, emission=color if emission else None, emission_strength=emission, **opts)
            if emission:
                mat["tyrian_glow"] = True
            self.slots[key] = len(self.list)
            self.list.append(mat)
        return self.slots[key]


# --- Bake and export -------------------------------------------------------------------------------

def top_unwrap(obj, uv, cols=1, rows=1):
    """UVs for a height-field model: its top view (the pattern fills u, v 0..0.98), so the map's texels
    follow the art's grid. Faces that look sideways or down (walls, the underside) are folded onto one
    texel in the margin, so they take one plain value."""
    hw, hh = TILE_W * cols / 2 * PX, TILE_H * rows / 2 * PX
    me = obj.data
    for poly in me.polygons:
        side = poly.normal.z < 0.15
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if side:
                uv.data[li].uv = (0.995, 0.995)
            else:
                uv.data[li].uv = (min(max((co.x + hw) / (2 * hw), 0.0), 1.0) * 0.98, min(max((co.y + hh) / (2 * hh), 0.0), 1.0) * 0.98)


def bake(obj, occluder_objs, size=256, samples=48, skip_slots=()):
    """usp_talon.bake_maps on obj with the occluders in the scene (removed after)."""
    import tempfile
    import usp_talon as T
    tint, textured = T.TINT, T.TEXTURED
    T.TINT = (1.0, 1.0, 1.0)
    T.TEXTURED = tuple(i for i in range(len(obj.data.materials)) if i not in skip_slots)
    try:
        T.bake_maps(obj, Path(tempfile.mkdtemp(prefix=f"{obj.name}_bake_")), size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", obj.name)
    for o in occluder_objs:
        bpy.data.objects.remove(o, do_unlink=True)


# A height-field tile (the hull) is baked from its height field instead: Cycles' occlusion rays leaving
# a finely tessellated curved surface catch its own facets and paint dark triangles on the tubes, while
# the field gives the occlusion exactly, with the neighbours' heights round it.

def _shift(a, dy, dx, fill):
    h, w = a.shape
    out = np.full_like(a, fill)
    ys, yd = (slice(dy, h), slice(0, h - dy)) if dy >= 0 else (slice(0, h + dy), slice(-dy, h))
    xs, xd = (slice(dx, w), slice(0, w - dx)) if dx >= 0 else (slice(0, w + dx), slice(-dx, w))
    out[yd, xd] = a[ys, xs]
    return out


def horizon_occlusion(height, solid, unit, radius, dirs=16):
    """Ambient occlusion of a height field (1 = open sky): for each direction the highest horizon
    within `radius` grid px, occlusion the mean of its sine. `unit`: model units per grid px."""
    hgt = np.where(solid, height, -10.0)
    occ = np.zeros(height.shape)
    for k in range(dirs):
        a = 2 * math.pi * k / dirs
        best = np.zeros(height.shape)
        for s in range(1, radius + 1):
            dy, dx = int(round(-s * math.sin(a))), int(round(s * math.cos(a)))
            if dx == 0 and dy == 0:
                continue
            other = _shift(hgt, dy, dx, -10.0)
            slope = (other - hgt) / (math.hypot(dx, dy) * unit)
            best = np.maximum(best, slope)
        occ += np.sin(np.arctan(best))
    return np.clip(1 - occ / dirs, 0, 1)


def _resample(a, out_h, out_w, fy, fx):
    """Bilinear samples of `a` at fractional rows fy (out_h,) and columns fx (out_w,)."""
    h, w = a.shape
    fy = np.clip(fy, 0, h - 1)
    fx = np.clip(fx, 0, w - 1)
    y0 = np.floor(fy).astype(int)
    x0 = np.floor(fx).astype(int)
    y1 = np.minimum(y0 + 1, h - 1)
    x1 = np.minimum(x0 + 1, w - 1)
    ty = (fy - y0)[:, None]
    tx = (fx - x0)[None, :]
    top = a[y0][:, x0] * (1 - tx) + a[y0][:, x1] * tx
    bot = a[y1][:, x0] * (1 - tx) + a[y1][:, x1] * tx
    return top * (1 - ty) + bot * ty


def field_bake(obj, height, solid, rough, metal, scale, size=256, skip_slots=(), side=0.72, cols=1, rows=1):
    """Bake obj's two maps (usp_talon.bake_maps' formulas: an occlusion multiplier, and roughness /
    metalness) from its 3x3 block's height field (`scale` grid px per tile px; the centre tile is the
    model) and wire them into its palette materials (Base Color = map x palette colour)."""
    import tempfile
    unit = PX / scale
    occ_s = horizon_occlusion(height, solid, unit, max(1, int(round(0.04 / unit))))
    occ_l = horizon_occlusion(height, solid, unit, max(2, int(round(0.16 / unit))))
    occl = occ_s ** 0.8 * (0.65 + 0.35 * occ_l)
    th, tw = TILE_H * scale, TILE_W * scale
    c = (slice(th, (rows + 1) * th), slice(tw, (cols + 1) * tw))
    th, tw = th * rows, tw * cols
    # Texel centres to the centre tile's grid (top_unwrap: u, v 0..0.98 over the tile; image rows
    # bottom-up). Grid px centres are at +0.5.
    u = (np.arange(size) + 0.5) / size / 0.98
    v = (np.arange(size) + 0.5) / size / 0.98
    fx = u * tw - 0.5
    fy = (1 - v) * th - 0.5
    col = np.clip(0.48 + 0.62 * _resample(occl[c], size, size, fy, fx), 0, 1)
    rgh = np.clip(_resample(rough[c], size, size, fy, fx) + (1 - _resample(occl[c], size, size, fy, fx)) * 0.3, 0.05, 1)
    mtl = _resample(metal[c], size, size, fy, fx)
    margin = (u[None, :] > 1.0) | (v[:, None] > 1.0)
    col = np.where(margin, side, col)
    out_dir = Path(tempfile.mkdtemp(prefix=f"{obj.name}_field_"))
    images = []
    for name, chans, colour in (("colour", (col, col, col), True), ("rm", (np.ones_like(col), rgh, mtl), False)):
        img = bpy.data.images.new(f"{obj.name}_{name}", size, size, alpha=False)
        if not colour:
            img.colorspace_settings.name = "Non-Color"
        px = np.stack([*chans, np.ones_like(col)], axis=-1).astype(np.float32)
        img.pixels[:] = px.ravel()
        img.filepath_raw = str(out_dir / f"{obj.name}_{name}.png")
        img.file_format = "PNG"
        img.save()
        images.append(img)
    col_img, rm_img = images
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    top_unwrap(obj, uv, cols, rows)
    for i, m in enumerate(me.materials):
        if i in skip_slots:
            continue
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


def export(ts, objects, name, layer, pattern, image_format="WEBP"):
    """public/models/tiles/<shapes>/<name>.glb and src/render/tileModels/<shapes>-<name>.json for
    `pattern` (a tile number for a one-tile pattern; lib_tiles.export_tile_model, with the baked maps
    as WebP)."""
    if isinstance(pattern, int):
        pattern = [[pattern]]
    import json
    model = f"tiles/{ts.name}/{name}"
    out = common.export_glb(objects, ts.root / "public" / "models" / f"{model}.glb", image_format=image_format)
    entry = {"model": model, "shapes": ts.file, "layer": layer, "tiles": [[int(t) for t in row] for row in pattern]}
    path = ts.root / "src" / "render" / "tileModels" / f"{ts.name}-{name}.json"
    path.write_text(json.dumps(entry, indent=1) + "\n")
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects if o.type == "MESH")
    print(f"exported {out} ({out.stat().st_size} bytes, {tris} tris) and {path}")
    return out


def finish(ts, coll, name, bm_block, mats, layer, bake_on=True, size=256, skip_slots=(), field=None, cols=1, rows=1):
    """Cut the block to its centre (`cols` x `rows` tiles), bake it among its neighbours (Cycles, or from
    its height field: `field` = dict(height, solid, rough, metal, scale) of the block)."""
    occ_bm = None if field is not None else outside_centre(copy_bm(bm_block), cols, rows)
    lt.cut_to_tile(bm_block, cols, rows)
    obj = common.mesh_object(name, bm_block, mats.list, coll, smooth=None)
    obj.data.name = name
    if not bake_on:
        if occ_bm is not None:
            occ_bm.free()
    elif field is not None:
        field_bake(obj, size=size, skip_slots=skip_slots, cols=cols, rows=rows, **field)
    else:
        occ = common.mesh_object(name + "_ctx", occ_bm, mats.list, coll, smooth=None)
        bake(obj, [occ], size=size, skip_slots=skip_slots)
    return obj


def build_args():
    """`-- [--preview dir] [--no-bake] [tile ...]`."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = {int(a) for a in argv if a.isdigit()}
    return only, "--no-bake" not in argv
