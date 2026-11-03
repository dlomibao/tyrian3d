"""The level-1 boss's damaged and destroyed pieces (newsh4.shp, D65's assembly-newsh4-124).

Each of the boss's twenty pieces is an enemy of its own. Hit hard enough, eleven of them change
frame: the wings, pylons and cable mounts (162-208) take burn holes; the right wingtip (208) and
the cable on the right (170) are shot away; and when an arm is destroyed its shoulder becomes a
wreck of torn plating and twisted frame (240, 244), the rest of the arm (86, 94, 124, 126, 130,
132 -> 238, 246, 276, 278, 282, 284) all but empty. Without models these frames drew as extruded
sprites beside the HD boss.

This script builds them from the boss's own build (assembly-newsh4-124.py, imported, so the
intact parts are exactly D65's), damaged the way each damaged sprite is:

- **The damaged sprite decides.** The machine is built whole; then every damaged piece's pixels
  are compared with its normal frame (both decoded from data/newsh4.shp, palette 5 as the
  catalogue's):
  - pixels the damaged frame no longer paints are cut away, top to bottom (an exact boolean
    with a footprint that follows the new outline at MMPX 2x, its stairs smoothed);
  - pixels it paints differently (burns, holes, wreckage) are a crater: cut from the model's
    own top surface (ray cast from above) down by a depth that grows with how much darker the
    damaged pixel is, its walls in scorched black; a piece whose new paint covers more than
    half of it (the two shoulder wrecks) is cut deep;
  - a debris relief fills each crater: a flat-shaded height field at MMPX 2x of the damaged
    pixels, each cell in its own pixel's palette colour (`pal_<i>`, so palettes, fades and the
    hit flash still apply), height from the pixel's brightness (bright torn plate and bent frame
    stand up, dark burns sink) plus a little seeded jitter so it reads as torn metal.
- **Finishing as D65:** hidden faces culled, cut into the pieces (common.split_assembly), each
  damaged piece baked (occlusion/edge colour multiplier and roughness/metal map, bake_piece) in
  place among the damaged machine, and its own outline shell (D51) cut from a shell of the damaged
  machine.
- **Export:** enemies/<piece>-d for each of the eleven, with its spriteModels entry for the damaged
  frame. The destroyed frames that draw nothing (238, 276, 278, 282, 284) need no model. Two damaged
  frames show the same picture as their normal frame (280 = 128; 242 = 90 but for five pixels of one
  edge), so they are drawn with the normal models instead (src/render/damage/cModels/same-picture.json).
- **Damage prototype (approach C):** common.export_sprite_model writes the JSONs into
  src/render/spriteModels/; move them to src/render/damage/cModels/ so the default game is unchanged.

Started on the pix-boss-damaged-frames branch (an agent's WIP, stopped there); carried over to
damage-approach as the approach C prototype.

blender -b --factory-startup --python assets/blender/enemies/assembly-newsh4-124-damaged.py -- \
    [--no-bake] [--no-export] [--design-out whole.glb] [--only newsh4-88,...]
"""

import importlib.util
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiles"))
import common  # noqa: E402
from lib_tiles import mmpx2x  # noqa: E402

_spec = importlib.util.spec_from_file_location("nsh4_boss", Path(__file__).with_name("assembly-newsh4-124.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

ROOT = B.ROOT
NAME = "assembly-newsh4-124-damaged"
TAG = "nsh4d"
W, H = B.W, B.H
S = 2  # cells per sprite px (MMPX 2x)

# Each piece's damaged frame (the enemy's dgr: TYRIAN's enemy types 46-65, normal + 152).
DAMAGE = {
    "newsh4-10": 162, "newsh4-12": 164, "newsh4-16": 168, "newsh4-18": 170,
    "newsh4-48": 200, "newsh4-50": 202, "newsh4-54": 206, "newsh4-56": 208,
    "newsh4-86": 238, "newsh4-88": 240, "newsh4-92": 244, "newsh4-94": 246,
    "newsh4-124": 276, "newsh4-126": 278, "newsh4-130": 282, "newsh4-132": 284,
}
# The shoulders whose damaged frames are wrecks (240, 244): rebuilt whole as debris.
WRECKS = {"newsh4-88", "newsh4-92"}
HOLE_LUM = 0.13  # a damaged pixel this dark (or HOLE_RATIO of its old brightness) is a hole
HOLE_RATIO = 0.4
SCORCH_MIN = 0.35  # the darkest a burn makes the plate (colour map multiplier)
PALETTE = 5  # TYRIAN's in-level palette, as the catalogue's sprite.json

CRATER_MIN = 0.7  # px: the shallowest burn
CRATER_MAX = 3.0  # px: a black hole
RELIEF = 1.4  # px: a crater's debris, darkest to brightest
WRECK_RELIEF = 3.2  # px: a wreck's debris
JITTER = 0.35  # px
WRECK_BOTTOM = -1.0  # px: a wreck's underside
SCORCH = 3  # palette index of the crater walls (near black)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


# ----------------------------------------------------------------------------------------------
# The damaged sprite
# ----------------------------------------------------------------------------------------------

def _sheet():
    return (ROOT / "data" / "newsh4.shp").read_bytes()


def _decode(sheet, index):
    """data/sprites.ts decodeSprite2: a 12-wide Sprite2, rows of palette indices (-1 transparent)."""
    op = (index - 1) * 2
    p = sheet[op] | (sheet[op + 1] << 8)
    rows, row, x = [], [-1] * 12, 0
    while p < len(sheet) and sheet[p] != 0x0F:
        x += sheet[p] & 0x0F
        count = sheet[p] >> 4
        if count == 0:
            rows.append(row)
            row, x = [-1] * 12, 0
            p += 1
            continue
        for _ in range(count):
            p += 1
            if x < 12:
                row[x] = sheet[p]
            x += 1
        p += 1
    if any(v >= 0 for v in row):
        rows.append(row)
    return rows


def frame_pixels(sheet, index):
    """A 2x2 group (index, +1, +19, +20) as a 28 x 24 array."""
    out = np.full((28, 24), -1, np.int32)
    for off, ox, oy in ((0, 0, 0), (1, 12, 0), (19, 0, 14), (20, 12, 14)):
        s = _decode(sheet, index + off)
        for y in range(min(14, len(s))):
            out[oy + y, ox:ox + 12] = s[y]
    return out


def palette_rgb():
    pal = (ROOT / "data" / "palette.dat").read_bytes()[PALETTE * 768:(PALETTE + 1) * 768]
    return [tuple(((pal[i * 3 + k] << 2) | (pal[i * 3 + k] >> 4)) & 0xFF for k in range(3)) for i in range(256)]


RGB = palette_rgb()
LUM = np.array([(0.299 * r + 0.587 * g + 0.114 * b) / 255 for r, g, b in RGB] + [0.0])


def boxes():
    """{piece: (x0, y0)}: its 24 x 28 box's top-left in the whole grid (assembly-newsh4-124's)."""
    return {e["model"]: (e["cx"] - B.CX0 + 48, e["cy"] - B.CY0 + 42) for e in B.LAYOUT}


def damaged_grid():
    """The whole boss with every piece of DAMAGE on its damaged frame: (H, W) palette indices."""
    sheet = _sheet()
    grid = np.array(B.GRID, np.int32)
    for name, (x0, y0) in boxes().items():
        if name in DAMAGE:
            grid[y0:y0 + 28, x0:x0 + 24] = frame_pixels(sheet, DAMAGE[name])
    return grid


# ----------------------------------------------------------------------------------------------
# Height fields with smoothed outlines (the cutter and the debris)
# ----------------------------------------------------------------------------------------------

def _xy(cx, cy):
    """A 2x-cell corner to model units (to_object's frame: X = (x - 60) / 12, Y = (56 - y) / 12)."""
    return (cx / S - W / 2) / 12, (H / 2 - cy / S) / 12


def field_solid(bm, cells, z_bot, z_top, mat_top, mat_side, mat_bot, smooth=3, jitter=None):
    """A closed solid over the 2x cells `cells` (bool (2H, 2W)): top and bottom height fields (px,
    arrays like cells: a corner takes the mean of its cells), each cell's top in mat_top(x, y), the
    walls and bottom in mat_side / mat_bot. The outline's stairs are smoothed (`smooth` passes of
    each boundary corner towards its two boundary neighbours, in x and y only); the top is split
    into triangles (flat shaded) so a relief shows its facets."""
    h, w = cells.shape
    ys, xs = np.nonzero(cells)
    corners = {}

    def cell_at(x, y):
        return 0 <= x < w and 0 <= y < h and cells[y, x]

    # Boundary edges: (corner a, corner b), counter-clockwise seen from above.
    bnd = []
    for y, x in zip(ys, xs):
        if not cell_at(x, y - 1):
            bnd.append(((x + 1, y), (x, y), (x, y)))
        if not cell_at(x + 1, y):
            bnd.append(((x + 1, y + 1), (x + 1, y), (x, y)))
        if not cell_at(x, y + 1):
            bnd.append(((x, y + 1), (x + 1, y + 1), (x, y)))
        if not cell_at(x - 1, y):
            bnd.append(((x, y), (x, y + 1), (x, y)))
    nb = {}
    for a, b, _ in bnd:
        nb.setdefault(a, set()).add(b)
        nb.setdefault(b, set()).add(a)
    pos = {c: (float(c[0]), float(c[1])) for c in nb}
    for _ in range(smooth):
        new = {}
        for c, ns in nb.items():
            if len(ns) != 2:  # a pinch: leave it
                new[c] = pos[c]
                continue
            mx = sum(pos[n][0] for n in ns) / 2
            my = sum(pos[n][1] for n in ns) / 2
            new[c] = (0.5 * pos[c][0] + 0.5 * mx, 0.5 * pos[c][1] + 0.5 * my)
        pos = new

    def zc(field, cx, cy):
        vals = [field[y, x] for y in (cy - 1, cy) for x in (cx - 1, cx) if cell_at(x, y)]
        return sum(vals) / len(vals)

    def vert(kind, cx, cy):
        key = (kind, cx, cy)
        v = corners.get(key)
        if v is None:
            px, py = pos.get((cx, cy), (float(cx), float(cy)))
            X, Y = _xy(px, py)
            z = zc(z_top if kind == "t" else z_bot, cx, cy)
            if kind == "t" and jitter is not None:
                z += jitter(cx, cy)
            v = corners[key] = bm.verts.new((X, Y, z / 12))
        return v

    for y, x in zip(ys, xs):
        a, b, c, d = vert("t", x, y + 1), vert("t", x + 1, y + 1), vert("t", x + 1, y), vert("t", x, y)
        m = mat_top(x, y)
        # Alternate the diagonal so the facets don't all lean one way.
        tris = ((a, b, c), (a, c, d)) if (x + y) % 2 else ((a, b, d), (b, c, d))
        for t in tris:
            f = bm.faces.new(t)
            f.material_index = m
            f.smooth = False
        f = bm.faces.new((vert("b", x, y), vert("b", x + 1, y), vert("b", x + 1, y + 1), vert("b", x, y + 1)))
        f.material_index = mat_bot
    side = mat_side if callable(mat_side) else (lambda x, y: mat_side)
    for a, b, c in bnd:
        f = bm.faces.new((vert("b", *a), vert("b", *b), vert("t", *b), vert("t", *a)))
        f.material_index = side(*c)
        f.smooth = False


def blur(a, mask, sigma=1.0):
    """Gaussian blur of `a` over `mask` only (normalised), separable."""
    r = int(math.ceil(sigma * 2.5))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    num = np.where(mask, a, 0.0)
    den = mask.astype(float)
    for axis in (0, 1):
        num = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), axis, num)
        den = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), axis, den)
    return np.where(den > 1e-6, num / np.maximum(den, 1e-6), 0.0)


def dilate(m, n=1):
    for _ in range(n):
        o = m.copy()
        o[1:, :] |= m[:-1, :]
        o[:-1, :] |= m[1:, :]
        o[:, 1:] |= m[:, :-1]
        o[:, :-1] |= m[:, 1:]
        m = o
    return m


def erode(m, n=1):
    return ~dilate(~m, n)


def components(m):
    h, w = m.shape
    seen = np.zeros_like(m)
    out = []
    for y0, x0 in zip(*np.nonzero(m)):
        if seen[y0, x0]:
            continue
        stack, comp = [(y0, x0)], []
        seen[y0, x0] = True
        while stack:
            y, x = stack.pop()
            comp.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and m[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True
                        stack.append((yy, xx))
        out.append(comp)
    return out


def top_heights(obj):
    """The intact machine's top surface (px) over every 2x cell, ray cast from above; NaN where it
    has none."""
    deps = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(obj, deps)
    out = np.full((H * S, W * S), np.nan)
    down = Vector((0, 0, -1))
    for y in range(H * S):
        for x in range(W * S):
            X, Y = _xy(x + 0.5, y + 0.5)
            loc, *_ = tree.ray_cast(Vector((X, Y, 5.0)), down)
            if loc is not None:
                out[y, x] = loc.z * 12
    return out


# ----------------------------------------------------------------------------------------------
# The damage
# ----------------------------------------------------------------------------------------------

def plan(normal, damaged, top):
    """Per 2x cell: what to cut (`cut`, with the cut's floor `floor`, px; -inf through the whole
    model) and where debris goes (`debris`, its bottom and top). Only inside DAMAGE's boxes."""
    hs, ws = H * S, W * S
    n2 = np.kron(normal, np.ones((S, S), np.int32))
    d2 = mmpx2x(damaged, LUM)
    dn = np.kron(damaged, np.ones((S, S), np.int32))
    inbox = np.zeros((hs, ws), bool)
    piece = np.full((hs, ws), -1, np.int32)
    heavy = np.zeros((hs, ws), bool)
    bx = boxes()
    for name in DAMAGE:
        x0, y0 = bx[name]
        sl = (slice(y0 * S, (y0 + 28) * S), slice(x0 * S, (x0 + 24) * S))
        inbox[sl] = True
        piece[sl] = list(DAMAGE).index(name)
        if name in WRECKS:
            heavy[sl] = True
    opaque = (d2 >= 0) & inbox
    # Removed: inside a damaged box, not within half a pixel of the damaged frame's paint.
    removed = inbox & ~dilate(opaque, 1)
    # Changed paint (1x, nearest), opened so single stray pixels don't each make a pit.
    changed = inbox & (dn >= 0) & (n2 != dn)
    # A burn (the paint darker, but not black) only darkens the plate: the scorch multiplier.
    ratio = np.where(changed, LUM[dn] / np.maximum(LUM[n2], 0.05), 1.0)
    hole = changed & ((LUM[dn] < HOLE_LUM) | (ratio < HOLE_RATIO))
    burn = changed & ~hole
    scorch = blur(np.where(burn, np.clip(ratio, SCORCH_MIN, 1.0), 1.0), np.ones_like(burn), 1.0)
    changed = dilate(erode(dilate(hole, 1), 1), 0) & opaque
    keep = np.zeros_like(changed)
    for comp in components(changed):
        if len(comp) >= 6:
            for y, x in comp:
                keep[y, x] = True
    # A wreck is all debris: the few pixels it happens to share with the intact part are not a part.
    changed = keep | (opaque & heavy)
    tz = np.where(np.isnan(top), np.nan, top)
    # Where the intact model has no top (paint the normal frame didn't have), the neighbours' mean.
    known = ~np.isnan(tz)
    fill = blur(np.where(known, tz, 0.0), known, 2.0)
    tz = np.where(known, tz, np.where(fill != 0, fill, 2.0))
    drop = np.clip((LUM[n2] - LUM[dn]) * 3.0, 0.0, 1.0)
    depth = CRATER_MIN + (CRATER_MAX - CRATER_MIN) * blur(drop, changed, 1.2)
    floor = tz - depth
    # A wreck is cut right through and rebuilt as debris: its base at a third of the part's height.
    floor = np.where(heavy, np.maximum(tz * 0.35, 0.5), floor)
    floor = np.where(changed, blur(floor, changed, 1.0), floor)
    lum = blur(LUM[np.where(d2 >= 0, d2, -1)], opaque, 1.0)
    amp = np.where(heavy, WRECK_RELIEF, RELIEF)
    lo = np.array([np.percentile(lum[changed & heavy], 10) if (changed & heavy).any() else 0.1])[0]
    lo_l = np.array([np.percentile(lum[changed & ~heavy], 10) if (changed & ~heavy).any() else 0.1])[0]
    base = np.where(heavy, lo, lo_l)
    relief = np.clip((lum - base) / 0.5, 0.0, 1.0) * amp
    # Debris stands from the floor; in a light crater it stays at or under the old surface.
    d_top = floor + 0.25 + relief
    d_top = np.where(heavy, d_top, np.minimum(d_top, tz + 0.2))
    # A wreck's torn edge comes down to its underside over its outer 1.5 px (no wall round it).
    edge = np.zeros(changed.shape)
    m = changed & heavy
    for _ in range(3):
        edge += m
        m = erode(m, 1)
    fall = np.clip(edge / 3.0, 0.2, 1.0)
    d_top = np.where(heavy, WRECK_BOTTOM + (d_top - WRECK_BOTTOM) * fall, d_top)
    colour = debris_colours(d2, changed, lum, piece)
    return {"scorch": scorch, "removed": removed, "changed": changed, "floor": floor, "d_top": d_top, "colour": colour, "tz": tz,
            "heavy": heavy}


def mode_filter(a, mask, passes=2):
    """Each masked cell takes the most common value of its 3x3 masked neighbours (speckle out)."""
    h, w = a.shape
    for _ in range(passes):
        out = a.copy()
        for y, x in zip(*np.nonzero(mask)):
            win = a[max(0, y - 1):y + 2, max(0, x - 1):x + 2][mask[max(0, y - 1):y + 2, max(0, x - 1):x + 2]]
            vals, counts = np.unique(win, return_counts=True)
            out[y, x] = vals[np.argmax(counts)]
        a = out
    return a


def debris_colours(d2, cells, lum, piece):
    """The debris's palette index per cell, as coherent patches rather than the sprite's speckle:
    each cell keeps its pixel's colour ramp (index >> 4: bronze, grey, red...), speckle filtered out,
    and within a piece and ramp takes one of three shades by its smoothed brightness, each shade the
    most common index of the pixels in that band."""
    ramp = mode_filter(np.where(d2 >= 0, d2 >> 4, -1), cells)
    out = np.where(cells, -1, d2)
    for pid in np.unique(piece[cells]):
        for r in np.unique(ramp[cells & (piece == pid)]):
            sel = cells & (piece == pid) & (ramp == r)
            if r < 0 or not sel.any():
                continue
            src = d2[sel]
            src = src[(src >> 4) == r]
            if not len(src):
                src = d2[sel]
            ls = lum[sel]
            t1, t2 = np.percentile(ls, 35), np.percentile(ls, 75)
            band = np.where(ls < t1, 0, np.where(ls < t2, 1, 2))
            # the source pixels' own shades, sorted by brightness, split in the same proportions
            srt = src[np.argsort(LUM[src])]
            parts = [srt[:max(1, int(len(srt) * 0.35))], srt[int(len(srt) * 0.35):max(int(len(srt) * 0.35) + 1, int(len(srt) * 0.75))],
                     srt[int(len(srt) * 0.75):]]
            pick = []
            for k in range(3):
                q = parts[k] if len(parts[k]) else srt
                vals, counts = np.unique(q, return_counts=True)
                pick.append(int(vals[np.argmax(counts)]))
            out[sel] = np.array(pick)[band]
    return out


def no_pinches(m):
    """Fill a cell where two cells touch only at a corner, so the solid over `m` is manifold."""
    m = m.copy()
    while True:
        a = m[:-1, :-1] & m[1:, 1:] & ~m[:-1, 1:] & ~m[1:, :-1]
        b = m[:-1, 1:] & m[1:, :-1] & ~m[:-1, :-1] & ~m[1:, 1:]
        if not (a.any() or b.any()):
            return m
        m[:-1, 1:] |= a
        m[:-1, :-1] |= b


def cutter(cells, z_bot, coll, mat):
    """A solid over the 2x cells `cells` from z_bot (px, per cell) up through the model, in `mat`
    (the walls it cuts take it in the boolean)."""
    bm = bmesh.new()
    cells = no_pinches(cells)
    field_solid(bm, cells, z_bot, np.full(cells.shape, 60.0), lambda x, y: 0, 0, 0, smooth=3)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f"{NAME}_cutter")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(f"{NAME}_cutter", me)
    coll.objects.link(o)
    return o


def cut_through(obj, cut, mat):
    """The boolean with a cutter that goes right through, keeping none of its walls: on this soup
    of overlapping, partly open parts the exact solver keeps stray strips of a tall cutter's walls.
    The walls are deleted and each part's opening along the cut is capped instead (as
    common.split_assembly caps its cuts)."""
    apply_boolean(obj, cut)
    k = next(i for i, m in enumerate(obj.data.materials) if m == mat)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    walls = [f for f in bm.faces if f.material_index == k]
    rim = {e for f in walls for e in f.edges if any(g.material_index != k for g in e.link_faces)}
    bmesh.ops.delete(bm, geom=walls, context="FACES_ONLY")
    rim = [e for e in rim if e.is_valid and e.is_boundary]
    n0 = len(bm.faces)
    if rim:
        new = bmesh.ops.holes_fill(bm, edges=rim, sides=0)["faces"]
        for f in new:
            f.material_index = k
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    print(f"{NAME}: cut through: {len(walls)} wall faces dropped, {len(bm.faces) - n0} caps")
    bm.to_mesh(obj.data)
    bm.free()


def debris(p, coll, mats, slot):
    """The relief that fills the craters, in the damaged pixels' own palette colours."""
    rng = np.random.default_rng(152)
    jit = rng.uniform(-JITTER, JITTER, (H * S + 1, W * S + 1))
    bm = bmesh.new()
    col = p["colour"]
    cells = p["changed"]
    bottom = np.where(p["heavy"], WRECK_BOTTOM, p["floor"] - 1.0)
    cells = no_pinches(cells)
    col = np.where(cells & ~p["changed"], SCORCH, col)
    paint = lambda x, y: slot(int(col[y, x]))  # noqa: E731
    field_solid(bm, cells, bottom, p["d_top"], paint, paint, slot(SCORCH), smooth=3, jitter=lambda cx, cy: jit[cy, cx])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f"{NAME}_debris")
    bm.to_mesh(me)
    bm.free()
    for m in mats["list"]:
        me.materials.append(m)
    o = bpy.data.objects.new(f"{NAME}_debris", me)
    coll.objects.link(o)
    return o


def debris_materials(sprite, indices):
    lst, index_of = [], {}
    for i in sorted(indices):
        index_of[i] = len(lst)
        lst.append(common.palette_material(sprite, i, f"{TAG}-debris", metallic=0.3, roughness=0.6))
    return {"list": lst, "slot": lambda i: index_of[i]}


def apply_boolean(obj, cut):
    bpy.context.view_layer.update()
    mod = obj.modifiers.new("damage", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cut
    mod.solver = "EXACT"
    mod.use_self = True
    mod.use_hole_tolerant = True
    mod.material_mode = "TRANSFER"
    common._apply_modifiers(obj)


def apply_boolean_parts(obj, cut, cells):
    """apply_boolean one loose part at a time, for the parts that reach a cut cell (bool (2H, 2W)):
    the build is many overlapping closed parts, and a boolean of all of them at once (self
    intersection) keeps stray pieces of the cutter's walls where it can't tell inside from out."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    seen, parts = set(), []
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        stack, part = [f0], []
        seen.add(f0.index)
        while stack:
            f = stack.pop()
            part.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        parts.append(part)
    hs, ws = cells.shape
    hit = []
    for part in parts:
        xs = [v.co.x for f in part for v in f.verts]
        ys = [v.co.y for f in part for v in f.verts]
        x0 = int(max(0, math.floor((min(xs) * 12 + W / 2) * S)))
        x1 = int(min(ws, math.ceil((max(xs) * 12 + W / 2) * S)))
        y0 = int(max(0, math.floor((H / 2 - max(ys) * 12) * S)))
        y1 = int(min(hs, math.ceil((H / 2 - min(ys) * 12) * S)))
        if x1 > x0 and y1 > y0 and cells[y0:y1, x0:x1].any():
            hit.append(part)
    objs = []
    for k, part in enumerate(hit):
        sub = bmesh.new()
        vmap = {}
        for f in part:
            vs = []
            for v in f.verts:
                if v not in vmap:
                    vmap[v] = sub.verts.new(v.co)
                vs.append(vmap[v])
            try:
                nf = sub.faces.new(vs)
            except ValueError:
                continue
            nf.material_index = f.material_index
            nf.smooth = f.smooth
        me = bpy.data.meshes.new(f"{obj.name}_part{k}")
        sub.to_mesh(me)
        sub.free()
        for m in obj.data.materials:
            me.materials.append(m)
        o = bpy.data.objects.new(me.name, me)
        obj.users_collection[0].objects.link(o)
        objs.append(o)
    bmesh.ops.delete(bm, geom=[f for part in hit for f in part], context="FACES")
    bm.to_mesh(obj.data)
    bm.free()
    print(f"{NAME}: {len(hit)} of {len(parts)} parts reach the cuts")
    keep = []
    for o in objs:
        mod = o.modifiers.new("damage", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cut
        mod.solver = "EXACT"
        mod.use_self = False
        mod.use_hole_tolerant = True
        mod.material_mode = "TRANSFER"
        common._apply_modifiers(o)
        if len(o.data.polygons):
            keep.append(o)
        else:
            bpy.data.objects.remove(o, do_unlink=True)
    return join([obj] + keep)


def join(objs):
    bpy.context.view_layer.update()
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return objs[0]


# ----------------------------------------------------------------------------------------------

def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    colours = dict(B.COLOURS)
    damaged = damaged_grid()
    normal = np.array(B.GRID, np.int32)
    for i in set(np.unique(damaged).tolist()) | {SCORCH}:
        if i >= 0:
            colours.setdefault(str(i), list(RGB[i]))
    sprite = {"name": NAME, "colors": colours}
    obj, mats = B.build(sprite, coll)
    bpy.context.view_layer.update()
    print(f"{NAME}: intact {len(obj.data.polygons)} faces")
    top = top_heights(obj)
    p = plan(normal, damaged, top)
    used = {int(v) for v in np.unique(p["colour"][p["changed"]])} | {SCORCH}
    dm = debris_materials(sprite, used)
    scorch = common.palette_material(sprite, SCORCH, f"{TAG}-scorch", metallic=0.2, roughness=0.75)
    through = p["removed"] | (p["changed"] & p["heavy"])
    cut = cutter(through, np.full(through.shape, -60.0), coll, scorch)
    cut_through(obj, cut, scorch)
    bpy.data.objects.remove(cut, do_unlink=True)
    craters = p["changed"] & ~p["heavy"]
    cut = cutter(craters, p["floor"], coll, scorch)
    apply_boolean(obj, cut)
    bpy.data.objects.remove(cut, do_unlink=True)
    deb = debris(p, coll, dm, dm["slot"])
    obj = join([obj, deb])
    bmesh_clean(obj)
    bpy.context.view_layer.update()
    print(f"{NAME}: {len(obj.data.polygons)} faces after damage")

    shell = B.whole_shell(obj, coll)
    B.cull_hidden(obj)
    layout = [(e["model"], e["cx"] - B.CX0, e["cy"] - B.CY0) for e in B.LAYOUT if e["model"] in B.PIECES]
    shells = B.split_open(shell, layout, coll, "_outline")
    shell.hide_render = True
    outline_mat = bpy.data.materials.get("outline_shell") or common.material("outline_shell", (0.0, 0.0, 0.0),
                                                                             roughness=1.0)
    for s in shells.values():
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        s.hide_render = True
    pieces = common.split_assembly(obj, layout)
    obj.hide_render = True
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
    targets = [n for n in DAMAGE if len(pieces[n].data.polygons) and (only is None or n in only)]
    # The eye is the normal one (the damaged frames leave it alone); build it so the bake sees it.
    eye_centre = next((cx / 12, -cy / 12) for name, cx, cy in layout if name == B.EYE)
    emats = B.eye_materials(sprite, mats)
    eye = B.build_eye(dict(B.EYE_MODELS)["newsh4-1-f3"], emats, coll, eye_centre, "newsh4-1-f3")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        tmp = tempfile.mkdtemp(prefix="nsh4d_bake_")
        B._cycles(48)
        for name, cx, cy in layout:
            pieces[name].location = (cx / 12, -cy / 12, 0)
        for o in eye:
            o.location = eye_centre[0], eye_centre[1], 0
        img = bpy.data.images.new(f"{NAME}_scorch", W * S, H * S, alpha=False, float_buffer=True)
        img.colorspace_settings.name = "Non-Color"
        sc = np.flipud(p["scorch"]).astype(np.float32)
        img.pixels.foreach_set(np.repeat(sc[:, :, None], 4, axis=2).reshape(-1))

        def scorch_mul(nt, node):
            """The scorch multiplier at the point's assembly x, y (the pieces sit in place)."""
            geo = node("ShaderNodeNewGeometry")
            sep = node("ShaderNodeSeparateXYZ")
            nt.links.new(geo.outputs["Position"], sep.inputs[0])
            u = node("ShaderNodeMapRange")
            u.inputs[1].default_value, u.inputs[2].default_value = -W / 24, W / 24
            nt.links.new(sep.outputs[0], u.inputs[0])
            v = node("ShaderNodeMapRange")
            v.inputs[1].default_value, v.inputs[2].default_value = -H / 24, H / 24
            nt.links.new(sep.outputs[1], v.inputs[0])
            comb = node("ShaderNodeCombineXYZ")
            nt.links.new(u.outputs[0], comb.inputs[0])
            nt.links.new(v.outputs[0], comb.inputs[1])
            tex = node("ShaderNodeTexImage")
            tex.image = img
            tex.extension = "EXTEND"
            nt.links.new(comb.outputs[0], tex.inputs["Vector"])
            return tex.outputs["Color"]
        for name in targets:
            B.bake_piece(pieces[name], tmp, colour_mul=scorch_mul)
        for o in list(pieces.values()) + eye:
            o.location = (0, 0, 0)
        fmt = "WEBP"
    for name in targets:
        wn = pieces[name].modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50

    if "--no-export" not in argv:
        for name in targets:
            extra = [shells[name]] if len(shells[name].data.polygons) else []
            sprites = [{"sheet": "newsh4.shp", "size": 2, "frames": [DAMAGE[name]]}]
            common.export_sprite_model(ROOT, [pieces[name]] + extra, f"enemies/{name}-d", sprites,
                                       image_format=fmt)

    if "--design-out" in argv:
        out = Path(argv[argv.index("--design-out") + 1])
        export = []
        for name, cx, cy in layout:
            for o in [pieces[name]] + ([shells[name]] if len(shells[name].data.polygons) else []):
                if not len(o.data.polygons):
                    continue
                o.location = (cx / 12, -cy / 12, 0)
                o["tyrian_piece"] = name
                export.append(o)
        for o in eye:
            o.location = eye_centre[0], eye_centre[1], 0
            export.append(o)
        common.export_glb(export, out, image_format=fmt)
        for o in export:
            o.location = (0, 0, 0)
        print(f"design export {out}")


def bmesh_clean(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()


if __name__ == "__main__":
    main()
