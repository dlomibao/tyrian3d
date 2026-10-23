"""Helpers shared by batch b134's enemy scripts (build-models.sh skips lib_ modules).

- Grid: sprite (or assembly) pixel coordinates to Blender X/Y, and the pixel under a point.
- Mats: palette materials created on demand, one slot per palette index.
- rock: an angular boulder, the convex hull of a footprint at the ground and a raised top.
- paint: give faces the material of the sprite pixels under them (seen from above).
- ground_tile: a flat patch of ground over one piece, painted from the sprite in 2 x 2 px cells.
(Grid and Mats follow lib_b006.)
"""

import sys
from collections import Counter
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units


class Grid:
    """Pixel grid of width w and height h (pixels), centred on the origin: column c, row r (pixel
    centres at c + 0.5, r + 0.5) map to X = (c + 0.5 - w/2)/12, Y = (h/2 - (r + 0.5))/12. Fractional
    columns/rows are allowed; x(c) is the centre of column c."""

    def __init__(self, w, h, pixels):
        self.w, self.h, self.pixels = w, h, pixels

    def x(self, c):
        return (c + 0.5 - self.w / 2) * U

    def y(self, r):
        return (self.h / 2 - (r + 0.5)) * U

    def at(self, x, y):
        """Palette index of the pixel containing (x, y), or -1 outside the grid."""
        c = int(x / U + self.w / 2)
        r = int(self.h / 2 - y / U)
        if 0 <= r < self.h and 0 <= c < self.w:
            return self.pixels[r][c]
        return -1


class Mats:
    """Palette materials, one slot per palette index (with the finish given the first time)."""

    def __init__(self, tag, colors):
        self.sprite = {"name": tag, "colors": colors}
        self.tag = tag
        self.list = []
        self.slots = {}

    def __call__(self, index, metallic=0.1, roughness=0.8, emission_strength=0.0):
        if index not in self.slots:
            self.slots[index] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, self.tag, metallic=metallic,
                                                     roughness=roughness, emission_strength=emission_strength))
        return self.slots[index]


def rock(bm, grid, base, top, peak=None, cuts=0, mat_index=0):
    """An angular boulder: the convex hull of a footprint `base` [(col, row)] on the ground (z = 0)
    and a raised `top` [(col, row, z)] (and an optional `peak` (col, row, z)). Its faces are
    subdivided `cuts` times so the sprite's shading can be painted onto them. Returns the new faces."""
    before = set(bm.faces)
    verts = [bm.verts.new((grid.x(c), grid.y(r), 0.0)) for c, r in base]
    verts += [bm.verts.new((grid.x(c), grid.y(r), z)) for c, r, z in top]
    if peak:
        verts.append(bm.verts.new((grid.x(peak[0]), grid.y(peak[1]), peak[2])))
    hull = bmesh.ops.convex_hull(bm, input=verts)
    unused = list({v for v in hull["geom_unused"] + hull["geom_interior"] if isinstance(v, bmesh.types.BMVert)})
    if unused:
        bmesh.ops.delete(bm, geom=unused, context="VERTS")
    faces = [f for f in bm.faces if f not in before]
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.normal_update()
    # Drop the bottom (it sits on the ground) and split the rest for painting.
    bottom = [f for f in faces if f.normal.z < -0.99]
    bmesh.ops.delete(bm, geom=bottom, context="FACES_ONLY")
    faces = [f for f in bm.faces if f not in before]
    if cuts:
        edges = list({e for f in faces for e in f.edges})
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
        faces = [f for f in bm.faces if f not in before]
    for f in faces:
        f.material_index = mat_index
        f.smooth = False
    return faces


def shrink(base, inset, z, dc=0.0, dr=0.0):
    """The footprint `base` [(col, row)] pulled `inset` px towards its centre (and moved dc, dr px),
    raised to z: [(col, row, z)], for the top or shoulder of a rock."""
    import math
    mc = sum(c for c, _ in base) / len(base)
    mr = sum(r for _, r in base) / len(base)
    out = []
    for c, r in base:
        d = math.hypot(c - mc, r - mr) or 1
        k = max(0.0, d - inset) / d
        out.append((mc + (c - mc) * k + dc, mr + (r - mr) * k + dr, z))
    return out


def block_rock(bm, grid, base, z, inset=2.0, extra=(), dc=0.0, dr=0.0, cuts=0):
    """A boulder with a flat top `inset` px inside its footprint at height z, a chamfered shoulder,
    and any `extra` (col, row, z) points (ridges, peaks). The top is shifted (dc, dr) px, e.g. up
    the screen to lean it back. Returns the new faces."""
    top = shrink(base, inset, z, dc, dr) + shrink(base, inset * 0.35, z * 0.78, dc * 0.5, dr * 0.5)
    return rock(bm, grid, base, top + list(extra), cuts=cuts)


def slice_grid(bm, grid, step=2, c0=0, r0=0):
    """Cut every face of bm along the pixel grid lines every `step` px (vertical planes, from pixel
    edge c0 / r0), so the facets can follow the sprite's shading when painted."""
    for c in range(c0, grid.w + 1, step):
        x = grid.x(c - 0.5)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(x, 0, 0), plane_no=(1, 0, 0))
    for r in range(r0, grid.h + 1, step):
        y = grid.y(r - 0.5)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, y, 0), plane_no=(0, 1, 0))


def paint(faces, grid, slot_for, samples=0.6):
    """Give each face the material of the most common pixel under it (its centre and points part way
    to its corners): slot_for(palette_index, face) -> slot, or None to leave the face as it is."""
    for f in faces:
        cen = f.calc_center_median()
        pts = [cen] + [cen.lerp(v.co, samples) for v in f.verts]
        counts = Counter(grid.at(p.x, p.y) for p in pts)
        idx = counts.most_common(1)[0][0]
        slot = slot_for(idx, f)
        if slot is not None:
            f.material_index = slot


def ground_tile(bm, grid, ox, oy, slot_for, z=0.02, w=24, h=28, cell=2):
    """A flat patch of ground over the w x h px piece whose top-left pixel is (ox, oy) on `grid`,
    built in the piece's own coordinates (origin at its centre), in cell x cell px squares painted
    with the most common pixel under each (slot_for(index) -> slot), with a skirt down to z = 0."""
    nx, ny = w // cell, h // cell
    vx = lambda i: (i * cell - w / 2) * U  # noqa: E731
    vy = lambda j: (h / 2 - j * cell) * U  # noqa: E731
    top = [[bm.verts.new((vx(i), vy(j), z)) for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            counts = Counter(grid.pixels[oy + j * cell + b][ox + i * cell + a]
                             for a in range(cell) for b in range(cell))
            f = bm.faces.new((top[j + 1][i], top[j + 1][i + 1], top[j][i + 1], top[j][i]))
            f.material_index = slot_for(counts.most_common(1)[0][0])
            f.smooth = False
    # Skirt round the edge.
    ring = ([top[0][i] for i in range(nx + 1)] + [top[j][nx] for j in range(1, ny + 1)]
            + [top[ny][i] for i in range(nx - 1, -1, -1)] + [top[j][0] for j in range(ny - 1, 0, -1)])
    low = [bm.verts.new((v.co.x, v.co.y, 0.0)) for v in ring]
    for k in range(len(ring)):
        m = (k + 1) % len(ring)
        f = bm.faces.new((ring[k], ring[m], low[m], low[k]))
        f.material_index = slot_for(-2)
        f.smooth = False


def assembly_pixels(root, layout):
    """The pixels of every piece of an assembly on one grid. `layout` is [(name, col, row)] with each
    piece's top-left pixel; returns (pixels, width, height, merged colours)."""
    pieces = [(common.load_sprite(root, n), c, r) for n, c, r in layout]
    w = max(c + d["frames"][0]["size"] * 12 for d, c, r in pieces)
    h = max(r + d["frames"][0]["size"] * 14 for d, c, r in pieces)
    pixels = [[-1] * w for _ in range(h)]
    colors = {}
    for d, c0, r0 in pieces:
        colors.update(d["colors"])
        for r, row in enumerate(d["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                pixels[r0 + r][c0 + c] = v
    return pixels, w, h, colors


def pixels_png(pixels, colors, out, pad_to=None):
    """Write a pixel grid as a PNG (transparent where -1), centred on a canvas of pad_to = (w, h)."""
    h, w = len(pixels), len(pixels[0])
    cw, ch = pad_to or (w, h)
    x0, y0 = (cw - w) // 2, (ch - h) // 2
    data = [0.0] * (cw * ch * 4)
    for r, row in enumerate(pixels):
        for c, v in enumerate(row):
            if v >= 0:
                rgb = colors[str(v)]
                k = ((ch - 1 - (y0 + r)) * cw + x0 + c) * 4
                data[k:k + 4] = [rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1.0]
    im = bpy.data.images.new("b134_sprite", cw, ch, alpha=True)
    im.pixels[:] = data
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
