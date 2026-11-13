"""CORE's wall of fire (episode 4, 4.5 CORE, main=6), all four assemblies in one build.

WHAT IT IS. Fourteen 2x2 enemies (types e4:366-379) spawn on one tick (event t5350, top layer,
link 199) as one rigid stack and stay together: a single mass of fire about 84 x 91 px. Tongues of
flame lick up the screen to three tall points (two in the middle, one at each flank), over a body
of fire that bulges out at the bottom into a bed of molten lava lumps; two openings show the floor
through the lower flanks. The catalogue cuts it into four assemblies:
  assembly-newsh3-96   newsh3-22 (left of the twin spikes), -60, -98 (centre-left column), -96 (left lobe)
  assembly-newsh3-99   newsh3-23, -61, -99 (centre-right column), -101 (right lobe)
  assembly-newsh3-117  newsh3-39 (left flank spike), -77 (left flank), -117 (centre-left lava)
  assembly-newsh3-118  newsh3-44 (right flank spike), -82 (right flank), -118 (centre-right lava)
The pieces overlap (the centre columns by 12 px, the lava under the columns and the lobes under the
flanks by 14 rows) and every overlapped pixel is the same in both sprites, so one whole fire cut
into each piece's 24x28 box gives every piece exactly its own sprite.

HOW IT IS BUILT. One faired surface over the fire's outline (the sprite's inner mask: the ink ring
the game draws itself is left off, D74), sampled on a 0.6 px grid whose rim vertices are projected
onto the smooth contour, then decimated with the rim held. Its height is
  * a rounded body: a quarter-round rim (R_RIM px) rising into a gentle crown over the distance
    from the edge, so the thin tongues and points are low blades and the root of the fire is fat;
  * the flame relief: the sprite's band-passed brightness (the tongues' bright streaks stand up as
    rounded ridges, the dark seams between tongues and between the lava lumps sink as grooves).
A plain closed underside (flat, rim wall). Every face takes the palette index of the sprite under
its centre (lightly blurred, so colour bands have smooth contours) and glows (metallic 1, rough,
D126/D173): the white cores fully, the dark red rim partly so the form still shades.

The game raises a later model over an earlier one it overlaps if the earlier one's top is higher
(D181 coverHeight); the overlapping pieces share their tallest point (the crown lies in the four-way
overlap of the centre columns and the lava), checked below.

Used by assembly-newsh3-96/-99/-117/-118.py (build_assembly): each builds the whole fire and exports
only its own pieces (public/models/enemies/<piece>.glb + spriteModels JSON), each with its outline
shell. Optional: -- --views DIR / --review DIR (renders and metrics; no other file is written).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def find_root():
    for p in Path(__file__).resolve().parents:
        if (p / "package.json").exists() and (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("repo root not found")


ROOT = find_root()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import sprite_mask as SM  # noqa: E402

U = 1 / 12  # one sprite px in Blender units

# The pieces in the game's draw order (enemy slots 50..63 at t5560, `tyrianHarness.g.enemy`), each
# with its top-left in the whole fire's grid (enemy ex - 47, ey + 10) and its assembly.
PIECES = [
    ("newsh3-39", 0, 14, "assembly-newsh3-117"),
    ("newsh3-77", 0, 42, "assembly-newsh3-117"),
    ("newsh3-96", 0, 56, "assembly-newsh3-96"),
    ("newsh3-22", 24, 0, "assembly-newsh3-96"),
    ("newsh3-23", 36, 0, "assembly-newsh3-99"),
    ("newsh3-60", 24, 28, "assembly-newsh3-96"),
    ("newsh3-61", 36, 28, "assembly-newsh3-99"),
    ("newsh3-98", 24, 56, "assembly-newsh3-96"),
    ("newsh3-99", 36, 56, "assembly-newsh3-99"),
    ("newsh3-117", 24, 70, "assembly-newsh3-117"),
    ("newsh3-118", 36, 70, "assembly-newsh3-118"),
    ("newsh3-44", 60, 14, "assembly-newsh3-118"),
    ("newsh3-82", 60, 42, "assembly-newsh3-118"),
    ("newsh3-101", 60, 56, "assembly-newsh3-99"),
]
ASSEMBLIES = ["assembly-newsh3-96", "assembly-newsh3-99", "assembly-newsh3-117", "assembly-newsh3-118"]
W, H = 84, 98  # the whole grid (rows 91-97 are empty: the lava pieces' bottom rows)

SP = 0.6  # surface grid spacing, px
UPS = 4  # field resolution, samples per px
R_RIM = 3.2  # px: the rim rounds over this distance from the edge
H_RIM = 3.4  # px: the rim's height at R_RIM
CROWN = 0.45  # px of height per px of distance beyond R_RIM
H_MAX = 10.0  # px: the crown's cap
ROOT_SWELL = 3.0  # px
Z_EDGE = 0.45  # px: height of the surface at the outline
UNDER = -1.0  # px: the flat underside
TUCK = 1.0  # px: the underside's rim sits this far inside the outline
RELIEF = 0.55  # px of relief per palette step of band-passed brightness
RELIEF_MAX = 2.0
DECIMATE = 0.62  # share of the top surface's faces kept
ANCHOR = 6.0 * U  # tyrian_anchor, model units (the top surface's mean height is 6.1 px)
GLOW = {127: 1.0, 126: 1.0, 125: 0.95, 124: 0.92, 123: 0.88, 122: 0.84, 121: 0.8, 120: 0.76,
        119: 0.72, 118: 0.68, 117: 0.64, 116: 0.6, 115: 0.58, 114: 0.55, 113: 0.5, 112: 0.5}


# --- the sprite --------------------------------------------------------------------------------------

def composite():
    grid = np.full((H, W), -1, dtype=int)
    colors = {}
    for name, ox, oy, _ in PIECES:
        data = common.load_sprite(ROOT, name)
        colors.update(data["colors"])
        px = np.array(data["frames"][0]["pixels"], dtype=int)
        m = px >= 0
        sub = grid[oy:oy + 28, ox:ox + 24]
        assert ((sub[m] == -1) | (sub[m] == px[m])).all(), f"{name}: overlap differs"
        sub[m] = px[m]
    # The catalogue's layouts agree with the game's positions inside each assembly.
    for asm in ASSEMBLIES:
        names = [p for p in PIECES if p[3] == asm]
        lay = {e["model"]: e for e in common.load_sprite(ROOT, names[0][0])["assemblyLayout"]}
        a = names[0]
        for p in names[1:]:
            assert (lay[p[0]]["cx"] - lay[a[0]]["cx"], lay[p[0]]["cy"] - lay[a[0]]["cy"]) == (p[1] - a[1], p[2] - a[2]), p
    return grid, colors


def layout():
    """split_assembly layout: piece centres in px from the grid centre, y down."""
    return [(n, ox + 12 - W / 2, oy + 14 - H / 2) for n, ox, oy, _ in PIECES]


# --- fields -----------------------------------------------------------------------------------------

def blur(a, sigma):
    if sigma <= 0:
        return a.copy()
    r = max(1, int(math.ceil(3 * sigma)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    p = np.pad(a, r, mode="edge")
    p = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 0, p)
    p = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 1, p)
    return p


def blur2(a, sx, sy):
    """Anisotropic gaussian blur: sx across the columns, sy along them."""
    out = a.copy()
    for axis, sigma in ((1, sx), (0, sy)):
        r = max(1, int(math.ceil(3 * sigma)))
        k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
        k /= k.sum()
        pad = [(0, 0), (0, 0)]
        pad[axis] = (r, r)
        p = np.pad(out, pad, mode="edge")
        out = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), axis, p)
    return out


def filled_index(grid):
    g = grid.astype(float)
    known = grid >= 0
    g[~known] = 0
    for _ in range(80):
        if known.all():
            break
        acc = np.zeros_like(g)
        cnt = np.zeros_like(g)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            sh = np.roll(np.roll(g, dr, 0), dc, 1)
            sk = np.roll(np.roll(known, dr, 0), dc, 1)
            if dr == -1:
                sk[-1, :] = False
            if dr == 1:
                sk[0, :] = False
            if dc == -1:
                sk[:, -1] = False
            if dc == 1:
                sk[:, 0] = False
            acc += np.where(sk, sh, 0)
            cnt += sk
        new = (~known) & (cnt > 0)
        g[new] = acc[new] / cnt[new]
        known = known | new
    return g


def upsample(a, k):
    """Bilinear upsample of a pixel grid (centres at +0.5) to k samples per px (centres at +0.5/k)."""
    h, w = a.shape
    ys = (np.arange(h * k) + 0.5) / k - 0.5
    xs = (np.arange(w * k) + 0.5) / k - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, h - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, w - 1)
    y1 = np.clip(y0 + 1, 0, h - 1)
    x1 = np.clip(x0 + 1, 0, w - 1)
    ty = np.clip(ys - y0, 0, 1)[:, None]
    tx = np.clip(xs - x0, 0, 1)[None, :]
    return ((a[y0][:, x0] * (1 - tx) + a[y0][:, x1] * tx) * (1 - ty)
            + (a[y1][:, x0] * (1 - tx) + a[y1][:, x1] * tx) * ty)


def chamfer(inside, step):
    """Distance (in px, `step` px per cell) from each inside cell to the outside, 8-neighbour chamfer."""
    h, w = inside.shape
    big = 1e9
    d = np.where(inside, big, 0.0)
    d = np.pad(d, 1)
    a, b = 1.0, math.sqrt(2)
    rows = d.tolist()
    for y in range(1, h + 1):
        r, ru = rows[y], rows[y - 1]
        for x in range(1, w + 1):
            if r[x]:
                r[x] = min(r[x], ru[x] + a, r[x - 1] + a, ru[x - 1] + b, ru[x + 1] + b)
    for y in range(h, 0, -1):
        r, rd = rows[y], rows[y + 1]
        for x in range(w, 0, -1):
            if r[x]:
                r[x] = min(r[x], rd[x] + a, r[x + 1] + a, rd[x + 1] + b, rd[x - 1] + b)
    return np.array(rows)[1:-1, 1:-1] * step


class Field:
    """Samplers over the upsampled grid, at (x, y) in px (x right, y down from the grid's corner)."""

    def __init__(self, arr):
        self.a = arr
        self.h, self.w = arr.shape

    def __call__(self, x, y):
        fx = np.clip(np.asarray(x, float) * UPS - 0.5, 0, self.w - 1.001)
        fy = np.clip(np.asarray(y, float) * UPS - 0.5, 0, self.h - 1.001)
        x0, y0 = fx.astype(int), fy.astype(int)
        tx, ty = fx - x0, fy - y0
        a = self.a
        return ((a[y0, x0] * (1 - tx) + a[y0, x0 + 1] * tx) * (1 - ty)
                + (a[y0 + 1, x0] * (1 - tx) + a[y0 + 1, x0 + 1] * tx) * ty)


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def fields(grid, colors):
    m = SM.masks(grid.tolist(), {int(k): tuple(v) for k, v in colors.items()})
    inner = np.array(m["inner"], float)
    free = np.array(m["free"], float)
    occ = blur(upsample(inner + 0.5 * free, UPS), 0.3 * UPS)
    inside = occ > 0.5
    dist = blur(chamfer(inside, 1.0 / UPS), 0.5 * UPS)
    idx = filled_index(grid)
    band = blur2(idx, 0.8, 1.6) - blur(idx, 3.2)  # tongues: elongated up the flame
    colour = blur(idx, 0.6)
    return {
        "occ": Field(occ), "dist": Field(dist), "band": Field(upsample(band, UPS)),
        "colour": Field(upsample(colour, UPS)), "masks": m,
    }


def height(F, x, y):
    d = F["dist"](x, y)
    t = np.clip(d / R_RIM, 0, 1)
    z = Z_EDGE + (H_RIM - Z_EDGE) * np.sqrt(1 - (1 - t) ** 2) + CROWN * np.maximum(d - R_RIM, 0)
    z = np.minimum(z, H_MAX + (z - H_MAX) * 0.2)
    # The root of the fire swells: a broad crown over the lava and the columns' foot.
    z = z + ROOT_SWELL * np.exp(-((x - 42.0) ** 2 / (2 * 18.0 ** 2) + (y - 74.0) ** 2 / (2 * 13.0 ** 2))) * smoothstep(d / 4.0)
    rel = np.clip(RELIEF * F["band"](x, y), -RELIEF_MAX, RELIEF_MAX) * smoothstep(d / 2.0)
    return z + rel


def piece_boxes():
    return [(n, ox, oy, ox + 24, oy + 28) for n, ox, oy, _ in PIECES]


def cover_pairs():
    """(earlier, later) piece pairs the game stacks (D181 coverHeight: boxes inset 2 px, overlap at
    least a quarter of the smaller box): the later one's top must not be below the earlier one's."""
    out = []
    for i, (a, ax, ay, _) in enumerate(PIECES):
        for b, bx, by, _ in PIECES[i + 1:]:
            w = min(ax + 22, bx + 22) - max(ax + 2, bx + 2)
            h = min(ay + 26, by + 26) - max(ay + 2, by + 2)
            if w > 0 and h > 0 and w * h >= 0.25 * 20 * 24:
                out.append((a, b, (max(ax, bx), max(ay, by), min(ax, bx) + 24, min(ay, by) + 28)))
    return out


def cover_bumps(F, px, py, z, interior, margin=0.3, sigma=3.0):
    """Raise the hot core where two stacked pieces overlap until it is the top of both, so the
    game never lifts the later piece over the earlier one (D181). Smooth gaussian swells at the
    point of the overlap furthest inside the fire."""
    boxes = {n: (x0, y0, x1, y1) for n, x0, y0, x1, y1 in piece_boxes()}
    pairs = cover_pairs()
    d = F["dist"](px, py)

    def top(n):
        x0, y0, x1, y1 = boxes[n]
        m = interior & (px >= x0) & (px <= x1) & (py >= y0) & (py <= y1)
        return z[m].max() if m.any() else 0.0
    for _ in range(30):
        bad = [(a, b, ov) for a, b, ov in pairs if top(b) + 1e-6 < top(a)]
        if not bad:
            break
        a, b, (x0, y0, x1, y1) = bad[0]
        # The swell sits in the overlap, inside the fire, as far as it can from the earlier
        # piece's own part (so it lifts the shared top, not the earlier piece's other tops).
        m = interior & (px >= x0 + 1) & (px <= x1 - 1) & (py >= y0 + 1) & (py <= y1 - 1) & (d >= 2.5)
        ex0, ey0, ex1, ey1 = boxes[a]
        excl = interior & (px >= ex0) & (px <= ex1) & (py >= ey0) & (py <= ey1) & \
            ~((px >= x0) & (px <= x1) & (py >= y0) & (py <= y1))
        cj, ci = np.nonzero(m)
        ej, ei = np.nonzero(excl)
        cxs, cys = px[cj, ci], py[cj, ci]
        exs, eys = px[ej, ei][::3], py[ej, ei][::3]
        far = np.sqrt(((cxs[:, None] - exs[None, :]) ** 2 + (cys[:, None] - eys[None, :]) ** 2).min(1))
        k = int(np.argmax(np.minimum(far, 2.5 * sigma) + 0.05 * d[cj, ci]))
        j, i = cj[k], ci[k]
        cx, cy = px[j, i], py[j, i]
        need = max(top(a), top(b)) + margin - z[j, i]
        z = z + need * np.exp(-((px - cx) ** 2 + (py - cy) ** 2) / (2 * sigma ** 2))
        print(f"cover swell for {a} < {b}: +{need:.2f} px at ({cx:.1f}, {cy:.1f})")
    return z


# --- the surface ------------------------------------------------------------------------------------

def build_body(F, colors, coll):
    occ = F["occ"]
    nx, ny = int(W / SP) + 2, int(H / SP) + 2
    xs = np.arange(nx) * SP - SP / 2
    ys = np.arange(ny) * SP - SP / 2
    gx, gy = np.meshgrid(xs, ys)
    f = occ(gx, gy) - 0.5
    ins = f > 0
    keepq = ins[:-1, :-1] | ins[1:, :-1] | ins[:-1, 1:] | ins[1:, 1:]
    used = np.zeros_like(ins)
    used[:-1, :-1] |= keepq
    used[1:, :-1] |= keepq
    used[:-1, 1:] |= keepq
    used[1:, 1:] |= keepq
    # Outside corners of kept quads go onto the contour (Newton steps on the occupancy field).
    px, py = gx.copy(), gy.copy()
    mv = used & ~ins
    e = 0.05
    for _ in range(6):
        x, y = px[mv], py[mv]
        v = occ(x, y) - 0.5
        gxv = (occ(x + e, y) - occ(x - e, y)) / (2 * e)
        gyv = (occ(x, y + e) - occ(x, y - e)) / (2 * e)
        g2 = gxv * gxv + gyv * gyv + 1e-6
        sx, sy = -v * gxv / g2, -v * gyv / g2
        ln = np.hypot(sx, sy)
        s = np.minimum(1.0, (SP * 0.9) / np.maximum(ln, 1e-9))
        px[mv], py[mv] = x + sx * s, y + sy * s
    z = height(F, px, py)
    z[mv] = Z_EDGE
    z = cover_bumps(F, px, py, z, used & ~mv)
    bm = bmesh.new()
    vid = {}
    for j, i in zip(*np.nonzero(used)):
        vid[(j, i)] = bm.verts.new(((px[j, i] - W / 2) * U, (H / 2 - py[j, i]) * U, z[j, i] * U))
    for j, i in zip(*np.nonzero(keepq)):
        q = [vid[(j, i)], vid[(j, i + 1)], vid[(j + 1, i + 1)], vid[(j + 1, i)]]
        try:
            bm.faces.new(q)
        except ValueError:
            pass
    # Quads whose corners all sat outside but straddle the contour can fold; drop slivers.
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.12 * U)
    bad = [fc for fc in bm.faces if fc.calc_area() < (0.02 * U) ** 2 or len(set(fc.verts)) < 3]
    bmesh.ops.delete(bm, geom=bad, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    # Non-manifold fans at pinch points: dissolve them by splitting verts with >2 boundary edges.
    for _ in range(3):
        pinch = [v for v in bm.verts if sum(1 for ed in v.link_edges if ed.is_boundary) > 2]
        if not pinch:
            break
        bmesh.ops.split_edges(bm, edges=[ed for v in pinch for ed in v.link_edges if ed.is_boundary])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for fc in bm.faces:
        if fc.normal.z < 0:
            fc.normal_flip()
    me = bpy.data.meshes.new("fire_top")
    bm.to_mesh(me)
    bm.free()
    top = bpy.data.objects.new("fire_top", me)
    coll.objects.link(top)
    # Decimate the top with the rim held (vertex group weight 0 on the rim).
    bm = bmesh.new()
    bm.from_mesh(me)
    rim = {v.index for v in bm.verts if v.is_boundary}
    bm.free()
    vg = top.vertex_groups.new(name="inner")
    vg.add([i for i in range(len(me.vertices)) if i not in rim], 1.0, "REPLACE")
    vg.add(list(rim), 0.0, "REPLACE")
    dec = top.modifiers.new("dec", "DECIMATE")
    dec.ratio = DECIMATE
    dec.vertex_group = "inner"
    dec.vertex_group_factor = 50.0
    dec.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = top
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(top.evaluated_get(dg))
    bpy.data.objects.remove(top, do_unlink=True)
    bpy.data.meshes.remove(me)
    # Close it: a short rim wall down to a flat underside.
    bm = bmesh.new()
    bm.from_mesh(me2)
    bpy.data.meshes.remove(me2)
    edges = [ed for ed in bm.edges if ed.is_boundary]
    ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
    nv = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    occ = F["occ"]
    for v in nv:
        # Tucked under: down to the underside and in by TUCK px (the rim wall faces the floor).
        x, y = v.co.x / U + W / 2, H / 2 - v.co.y / U
        e = 0.1
        gx_ = float(occ(x + e, y) - occ(x - e, y))
        gy_ = float(occ(x, y + e) - occ(x, y - e))
        ln = math.hypot(gx_, gy_) or 1.0
        v.co.x += gx_ / ln * TUCK * U
        v.co.y -= gy_ / ln * TUCK * U
        v.co.z = UNDER * U
    ne = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMEdge) and all(v in set(nv) for v in g.verts)]
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=ne)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    vol = sum(fc.calc_area() * fc.normal.dot(fc.calc_center_median()) for fc in bm.faces)
    if vol < 0:  # recalc pointed them all inwards
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    # Materials: the palette index under each top face; underside and wall the dark rim red.
    used_idx = sorted({int(v) for v in np.unique(np.array(list(colors.keys()), int)) if 112 <= int(v) <= 127})
    sprite = {"name": "fire", "colors": colors}
    mats = [common.palette_material(sprite, v, "newsh3fire", metallic=1.0, roughness=0.9,
                                    emission_strength=GLOW.get(v, 0.6)) for v in used_idx]
    mat_of = {v: i for i, v in enumerate(used_idx)}
    cols = F["colour"]
    for fc in bm.faces:
        c = fc.calc_center_median()
        sx, sy = c.x / U + W / 2, H / 2 - c.y / U
        if fc.normal.z < -0.5:
            v = 114  # the underside
        else:
            # Top faces: the sprite's colour; the rim wall: the colour just inside the rim.
            g = F["dist"]
            if c.z < Z_EDGE * U:
                e = 0.2
                gx_ = float(g(sx + e, sy) - g(sx - e, sy))
                gy_ = float(g(sx, sy + e) - g(sx, sy - e))
                ln = math.hypot(gx_, gy_) or 1.0
                sx, sy = sx + gx_ / ln * 1.2, sy + gy_ / ln * 1.2
            v = int(round(float(cols(sx, sy))))
        v = min(127, max(114, v))
        while v not in mat_of:
            v += 1
        fc.material_index = mat_of[v]
        fc.smooth = fc.normal.z > -0.5
    me3 = bpy.data.meshes.new("fire")
    bm.to_mesh(me3)
    bm.free()
    for m in mats:
        me3.materials.append(m)
    obj = bpy.data.objects.new("fire", me3)
    coll.objects.link(obj)
    return obj


def open_cut(obj, x0, x1, y0, y1, centre, name, coll):
    """A copy of obj inside the box (grid px, x right, y down), cuts left open, moved so `centre`
    (grid px) is the origin (from assembly-newshk-51.py)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    planes = (((x0 - W / 2) * U, 0, 0), (-1, 0, 0)), (((x1 - W / 2) * U, 0, 0), (1, 0, 0)), \
             ((0, (H / 2 - y1) * U, 0), (0, -1, 0)), ((0, (H / 2 - y0) * U, 0), (0, 1, 0))
    for co, no in planes:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                               plane_no=no, clear_outer=True)
    cx, cy = (centre[0] - W / 2) * U, (H / 2 - centre[1]) * U
    bmesh.ops.translate(bm, vec=(-cx, -cy, 0), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


# --- measuring and rendering (--review / --views only) ---------------------------------------------

def top_samples(objs, x0, y0, w, h, k=4):
    """Top-view ray casts over grid window (x0, y0, w, h) px: (mask, palette index, height px)."""
    bm = bmesh.new()
    names = []
    for o in objs:
        tmp = bmesh.new()
        tmp.from_mesh(o.data)
        bmesh.ops.transform(tmp, matrix=o.matrix_world, verts=tmp.verts)
        base = len(names)
        names += [m.name for m in o.data.materials]
        for fc in tmp.faces:
            fc.material_index += base
        me = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    mask = np.zeros((h * k, w * k), bool)
    index = np.full((h * k, w * k), -1, int)
    hgt = np.zeros((h * k, w * k))
    for j in range(h * k):
        for i in range(w * k):
            x = (x0 + (i + 0.5) / k - W / 2) * U
            y = (H / 2 - y0 - (j + 0.5) / k) * U
            hit = tree.ray_cast(Vector((x, y, 50.0)), Vector((0, 0, -1)), 100.0)
            if hit[0] is not None:
                mask[j, i] = True
                hgt[j, i] = hit[0].z / U
                nm = names[bm.faces[hit[2]].material_index]
                if nm.startswith("pal_"):
                    index[j, i] = int(nm.split("_")[1])
    bm.free()
    return mask, index, hgt


def setup_render(px):
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x = scene.render.resolution_y = px
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.05, 0.05, 0.06, 1)
    bg.inputs[1].default_value = 1.0
    if "sun" not in bpy.data.objects:
        sd = bpy.data.lights.new("sun", "SUN")
        sd.energy = 3.0
        sun = bpy.data.objects.new("sun", sd)
        scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(40), math.radians(-25), math.radians(15))


def render_views(objs, out_dir, extent, px=640):
    scene = bpy.context.scene
    setup_render(px)
    keep = set(objs)
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o not in keep
    d = extent * 2.2
    views = {
        "top": ((0, 0, d), True),
        "game": ((0, -d * 0.62, d * 0.9), False),
        "q34": ((d * 0.62, -d * 0.62, d * 0.55), False),
        "q34b": ((-d * 0.62, d * 0.62, d * 0.55), False),
        "side": ((d, 0, 0.02), True),
        "front": ((0, -d, 0.02), True),
        "rear": ((0, d, 0.02), True),
        "under": ((d * 0.3, -d * 0.4, -d * 0.8), False),
    }
    for nm, (loc, ortho) in views.items():
        cd = bpy.data.cameras.new("cam")
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = extent
        cam = bpy.data.objects.new("cam", cd)
        scene.collection.objects.link(cam)
        cam.location = Vector(loc)
        if nm == "top":
            cam.rotation_euler = (0, 0, 0)
        else:
            cam.rotation_euler = (-cam.location).to_track_quat("-Z", "Y").to_euler()
        if not ortho:
            cd.sensor_width = 36
            cd.lens = 50 * cam.location.length / (extent * 1.45)
        scene.camera = cam
        scene.render.filepath = str(Path(out_dir) / f"{nm}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cd)


def review(out, parts, grid, colors, F):
    out.mkdir(parents=True, exist_ok=True)
    cmap = {int(k): tuple(v) for k, v in colors.items()}
    rep = {"pieces": {}, "assemblies": {}}
    k = 4
    # Whole fire.
    allp = list(parts.values())
    mask, index, hgt = top_samples(allp, 0, 0, W, H, k)
    m = F["masks"]
    meas = SM.measure(m, mask.tolist())
    rep["whole"] = {kk: meas[kk] for kk in ("iou_rule_grid", "iou_rule", "iou_inner_grid", "iou_outer_grid")}
    np.save(out / "whole_mask.npy", mask)
    np.save(out / "whole_index.npy", index)
    np.save(out / "whole_height.npy", hgt)
    # Each assembly on its own, against sprite_mask's own composite of it.
    for asm in ASSEMBLIES:
        ps = [p for p in PIECES if p[3] == asm]
        x0 = min(p[1] for p in ps)
        y0 = min(p[2] for p in ps)
        x1 = max(p[1] + 24 for p in ps)
        y1 = max(p[2] + 28 for p in ps)
        idx, cl = SM.load(asm)
        assert len(idx) == y1 - y0 and len(idx[0]) == x1 - x0, asm
        mm = SM.masks(idx, cl)
        msk, _, _ = top_samples([parts[p[0]] for p in ps], x0, y0, x1 - x0, y1 - y0, k)
        r = SM.measure(mm, msk.tolist())
        rep["assemblies"][asm] = r["iou_rule_grid"]
    # Each piece against its own sprite (seam borders count as ink there, so lower).
    for name, ox, oy, _ in PIECES:
        idx, cl = SM.load(name)
        mm = SM.masks(idx, cl)
        msk, _, _ = top_samples([parts[name]], ox, oy, 24, 28, k)
        rep["pieces"][name] = SM.measure(mm, msk.tolist())["iou_rule_grid"]
    # Colour: per-pixel index error inside the inner mask, ignoring the darkest and brightest.
    inner = np.array(m["inner"])
    sub = index[k // 2::k, k // 2::k]
    ok = inner & (grid >= 115) & (grid <= 125) & (sub >= 0)
    rep["colour_mean_abs_index_err"] = round(float(np.abs(sub[ok] - grid[ok]).mean()), 3)
    rep["colour_median_sprite"] = int(np.median(grid[inner & (grid >= 112)]))
    rep["colour_median_model"] = int(np.median(sub[inner & (sub >= 0)]))
    rep["height_max_px"] = round(float(hgt.max()), 2)
    (out / "report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))
    # Sprite image for the sheet.
    img = np.zeros((H, W, 4), np.uint8)
    for v, c in cmap.items():
        img[grid == v] = [*c, 255]
    np.save(out / "sprite_rgba.npy", img)
    np.save(out / "inner.npy", inner)


# --- main --------------------------------------------------------------------------------------------

def build_assembly(asm):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    rev = Path(argv[argv.index("--review") + 1]) if "--review" in argv else None
    coll = common.reset_collection("newsh3fire")
    grid, colors = composite()
    F = fields(grid, colors)
    body = build_body(F, colors, coll)
    shell = common.outline_shell(body, coll, voxel=0.02, faces=6000, smooth=6, inside=0.004, islands="outer")
    lay = layout()
    parts = common.split_assembly(body, lay, coll)
    shells = {}
    for name, ox, oy, _ in PIECES:
        sh = open_cut(shell, ox, ox + 24, oy, oy + 28, (ox + 12, oy + 14), f"{name}_outline", coll)
        sh.data.shade_smooth()
        sh.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
        sh["tyrian_outline"] = True
        shells[name] = sh
        # One shared anchor for all fourteen pieces (D181): the top surface's mean height, so the
        # fire's face lands on the sprite near the top edge and the pieces still meet.
        sh["tyrian_anchor"] = ANCHOR
        parts[name]["tyrian_anchor"] = ANCHOR
        assert len(sh.data.polygons) > 0, name
    body.hide_render = shell.hide_render = True
    tops = {}
    tris = {}
    for name, cx, cy in lay:
        parts[name].location = (cx * U, -cy * U, 0)
        shells[name].location = parts[name].location
        tops[name] = max(v.co.z for v in parts[name].data.vertices) / U
        tris[name] = sum(len(p.vertices) - 2 for p in parts[name].data.polygons)
    bpy.context.view_layer.update()
    # D181: a later piece overlapping an earlier one by a quarter of its box must not be lower.
    viol = [(a, round(tops[a], 2), b, round(tops[b], 2)) for a, b, _ in cover_pairs() if tops[b] + 1e-4 < tops[a]]
    print("tops px:", {k: round(v, 2) for k, v in tops.items()})
    print("D181 cover violations:", viol)
    per_asm = {a: sum(tris[p[0]] for p in PIECES if p[3] == a) for a in ASSEMBLIES}
    print("triangles per piece:", tris, "per assembly:", per_asm, "total:", sum(tris.values()))
    assert not viol
    if rev:
        review(rev, parts, grid, colors, F)
        info = {"tops": tops, "violations": viol, "tris": tris, "per_assembly": per_asm}
        (rev / "build.json").write_text(json.dumps(info, indent=1))
    if views:
        views.mkdir(parents=True, exist_ok=True)
        render_views(list(parts.values()), views, extent=100 * U)
    # Export this assembly's pieces, each alone at its origin.
    for name, *_ in [p for p in PIECES if p[3] == asm]:
        objs = [parts[name], shells[name]]
        for o in objs:
            o.location = (0, 0, 0)
        bpy.context.view_layer.update()
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, objs, f"enemies/{name}", data["sprites"])
