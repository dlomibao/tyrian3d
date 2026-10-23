"""Helpers for batch b137 (newshd.shp rock heap in level 1.5 and its loose rock-edge tiles).

The rocks are built as a pile of faceted, partly buried boulders standing on a low rubble apron
that follows the sprite's silhouette. Every boulder vertex is pulled inside the silhouette, and
every face takes the grey of the sprite pixels under it, so the sprite's light ridges and dark
cracks stay where they are. (The boulder and apron idea follows assembly-newshd-39.py, the rock
heap next to this one, so the two heaps read alike.)
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12
ROOT = common.repo_root(__file__)

# Brightness level of each palette index (greys are their own index; the blue-grey pixels count
# as the grey of the same lightness). Outline pixels (1, 32) are left out: the game adds one.
LEVEL = {3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12, 13: 13, 14: 14, 15: 15,
         102: 4, 106: 8, 107: 11, 108: 12}


class Grid:
    """A W x H grid of palette indices (-1 transparent) with its pixel <-> Blender mapping:
    the grid's centre is the origin, sprite up is +Y, one pixel is 1/12 unit."""

    def __init__(self, cells):
        self.cells = cells
        self.h = len(cells)
        self.w = len(cells[0])
        self.rows = {}
        self.cols = {}
        for r, row in enumerate(cells):
            cs = [c for c, v in enumerate(row) if v in LEVEL]
            if cs:
                self.rows[r] = (min(cs), max(cs))
        for c in range(self.w):
            rs = [r for r in range(self.h) if cells[r][c] in LEVEL]
            if rs:
                self.cols[c] = (min(rs), max(rs))

    def X(self, c):
        return (c + 0.5 - self.w / 2) * PX

    def Y(self, r):
        return (self.h / 2 - (r + 0.5)) * PX

    def to_px(self, x, y):
        return x / PX + self.w / 2 - 0.5, self.h / 2 - y / PX - 0.5

    def shade_at(self, c, r):
        """Mean brightness level of the rock pixels in the 3x3 around (c, r), or None."""
        vals = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = int(round(r)) + dr, int(round(c)) + dc
                if 0 <= rr < self.h and 0 <= cc < self.w and self.cells[rr][cc] in LEVEL:
                    vals += [LEVEL[self.cells[rr][cc]]] * (4 if dr == 0 and dc == 0 else 1)
        return sum(vals) / len(vals) if vals else None

    def clamp(self, x, y, inset=0.25):
        """Pull a point inside the silhouette: into its row's span, then its column's span."""
        c, r = self.to_px(x, y)
        rows = sorted(self.rows)
        rr = min(max(int(round(r)), rows[0]), rows[-1])
        while rr not in self.rows:  # a gap row: use the nearest filled row
            rr += 1
        c0, c1 = self.rows[rr]
        c = min(max(c, c0 - 0.5 + inset), c1 + 0.5 - inset)
        cols = sorted(self.cols)
        cc = min(max(int(round(c)), cols[0]), cols[-1])
        while cc not in self.cols:
            cc += 1
        r0, r1 = self.cols[cc]
        r = min(max(r, r0 - 0.5 + inset), r1 + 0.5 - inset)
        return self.X(c), self.Y(r)


def sprite_grid(name):
    data = common.load_sprite(ROOT, name)
    return Grid(data["frames"][0]["pixels"]), data


def assembly_grid(pieces, w, h, cx0, cy0):
    """The first frames of the pieces as one grid, w x h px centred on screen pixel (cx0, cy0)."""
    cells = [[-1] * w for _ in range(h)]
    first = common.load_sprite(ROOT, pieces[0])
    for e in first["assemblyLayout"]:
        if e["model"] not in pieces:
            continue
        data = common.load_sprite(ROOT, e["model"])
        x0, y0 = e["cx"] - cx0 + w // 2 - 12, e["cy"] - cy0 + h // 2 - 14
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    cells[y0 + r][x0 + c] = v
    return Grid(cells)


def apron(bm, g, inset=2.5, height=0.12):
    """A low rubble apron: the sprite's outline (row by row) at the ground, sloping in to a flat
    top `inset` px inside it."""
    rows = sorted(g.rows)
    top, bot = rows[0], rows[-1]

    def span(r):
        rr = min(max(r, top), bot)
        while rr not in g.rows:
            rr += 1
        return g.rows[rr]

    def ring(d, z):
        # One point per side at every row boundary (counter-clockwise from above: down the left
        # side, up the right). The outer ring takes the wider of the two rows it separates, the
        # inner one the narrower, inset by d px.
        ys = [top - 0.5 + d] + [r + 0.5 for r in range(top, bot)] + [bot + 0.5 - d]
        sides = []
        for i, y in enumerate(ys):
            if i == 0 or i == len(ys) - 1:
                a = b = top if i == 0 else bot
            else:
                a, b = int(y - 0.5), int(y + 0.5)
            pick = (min, max) if d == 0 else (max, min)
            cl = pick[0](span(a)[0], span(b)[0]) - 0.5 + d
            cr = pick[1](span(a)[1], span(b)[1]) + 0.5 - d
            if cl > cr:
                cl = cr = (cl + cr) / 2
            sides.append((g.Y(y), g.X(cl), g.X(cr)))
        pts = [(xl, y, z) for y, xl, _ in sides] + [(xr, y, z) for y, _, xr in reversed(sides)]
        return [bm.verts.new(p) for p in pts]

    low = ring(0.0, 0.0)
    high = ring(inset, height)
    k = len(low)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((low[i], low[j], high[j], high[i]))
    bm.faces.new(high)


def boulder(bm, g, col, row, rx, ry, rot, h, rng, subdiv=2, grow=1.3, sink=0.3, peak=0.85):
    """The upper half of a lumpy, faceted ellipsoid standing on z = 0, kept inside the silhouette.
    (col, row) is its centre in grid pixels, rx/ry its half sizes in px, h its height in units."""
    res = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    verts = res["verts"]
    a = math.radians(rot)
    for v in verts:
        p = v.co.copy()
        k = 1.0 + rng.uniform(-0.09, 0.09)
        z = p.z ** peak if p.z > 0 else p.z  # peak < 1: flatter crown, fuller shoulders; > 1: pointed
        x, y = p.x * rx * grow * PX * k, p.y * ry * grow * PX * k
        xr, yr = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        cx, cy = g.clamp(g.X(col) + xr, g.Y(row) + yr)
        v.co = Vector((cx, cy, (z * (1 + sink) - sink) * h * k))
    vs = set(verts)
    geom = verts + [e for e in bm.edges if e.verts[0] in vs] + [f for f in bm.faces if f.verts[0] in vs]
    cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0.0), plane_no=(0, 0, 1), clear_inner=True)
    edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)


def paint(bm, g, shades):
    """Give each face the grey (palette index in `shades`) of the sprite pixels under it."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        cen = f.calc_center_median()
        lvl = g.shade_at(*g.to_px(cen.x, cen.y))
        if lvl is None or f.normal.z < -0.5:  # outside the rock, or an underside never seen
            lvl = shades[0]
        idx = min(max(int(round(lvl)), shades[0]), shades[-1])
        f.material_index = shades.index(idx)


def rock_object(name, g, sprite, boulders, shades, seed, tag, apron_kw=None):
    """Apron plus boulders, painted, as one object. Each boulder is (col, row, rx, ry, rot, h) and
    optionally a dict of boulder() keywords (subdiv, peak, sink)."""
    coll = common.reset_collection(name)
    mats = [common.palette_material(sprite, i, tag, metallic=0.0, roughness=0.85) for i in shades]
    rng = random.Random(seed)
    bm = bmesh.new()
    apron(bm, g, **(apron_kw or {}))
    for b in boulders:
        col, row, rx, ry, rot, h = b[:6]
        kw = {"subdiv": 3 if max(rx, ry) >= 6 else 2}
        kw.update(b[6] if len(b) > 6 else {})
        boulder(bm, g, col, row, rx, ry, rot, h, rng, **kw)
    paint(bm, g, shades)
    return common.mesh_object(name, bm, mats, coll, smooth=False)


def cut_box(obj, x0, x1, y0, y1):
    """Keep the part of `obj` inside x0..x1, y0..y1 (units), filling the cut faces."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for co, no in (((x0, 0, 0), (-1, 0, 0)), ((x1, 0, 0), (1, 0, 0)),
                   ((0, y0, 0), (0, -1, 0)), ((0, y1, 0), (0, 1, 0))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def grid_png(g, colors, out):
    """A grid as an image (for the preview of a whole assembly)."""
    import numpy as np
    img = np.zeros((g.h, g.w, 4), dtype=np.float32)
    for r, row in enumerate(g.cells):
        for c, v in enumerate(row):
            if v >= 0:
                img[r, c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("grid_sprite", g.w, g.h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
