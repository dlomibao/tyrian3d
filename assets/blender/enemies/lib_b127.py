"""Helpers shared by batch b127's models: the wrecked machine of newshu.shp (level 1.19 and 3.23),
built whole in one pixel grid and cut into its 2x2 pieces.

Not a model itself: tools/build-models.sh skips lib_ modules. Scripts import it with
`import lib_b127 as lib` after putting assets/blender and assets/blender/enemies on sys.path.

Coordinates: parts are placed by pixel column/row of a grid that holds the whole machine (the
pieces at their places on the newshu.shp sheet). `Grid` maps those to Blender units with its own
centre as the origin. Column/row *edges* (0 = the left/top edge of column/row 0) are used
throughout, so a part covering columns 30-32 runs from edge 30 to edge 33.
"""

import math
import struct
import sys
import zlib
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

SHEET_COLS = 19  # newshu.shp is 19 tiles wide; a 2x2 sprite n covers tiles n, n+1, n+19, n+20


class Grid:
    """A pixel grid w x h (columns x rows) starting at column c0, row r0 of the machine's
    coordinates, whose centre is the Blender origin."""

    def __init__(self, w, h, c0=0, r0=0):
        self.w, self.h, self.c0, self.r0 = w, h, c0, r0

    def x(self, c):
        """Column edge to Blender X."""
        return (c - self.c0 - self.w / 2) / 12

    def y(self, r):
        """Row edge to Blender Y (sprite up is +Y)."""
        return (self.h / 2 - (r - self.r0)) / 12

    def xy(self, c, r):
        return self.x(c), self.y(r)


def sheet_origin(frame):
    """Top-left (column, row) of a 2x2 newshu.shp sprite on the sheet, in pixels."""
    return ((frame - 1) % SHEET_COLS) * 12, ((frame - 1) // SHEET_COLS) * 14


class Mats:
    """Palette materials made on demand: slot(index) gives the material slot for a palette index."""

    def __init__(self, sprite, tag, settings):
        self.sprite, self.tag, self.settings = sprite, tag, settings
        self.list, self.slots = [], {}

    def __call__(self, index):
        if index not in self.slots:
            kw = dict(metallic=0.4, roughness=0.5)
            kw.update(self.settings.get(index, {}))
            self.slots[index] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, self.tag, **kw))
        return self.slots[index]


class Builder:
    """Mesh parts placed in pixel coordinates of a Grid, with palette materials."""

    def __init__(self, grid, mats):
        self.g, self.m = grid, mats
        self.bm = bmesh.new()

    # -- raw helpers ---------------------------------------------------------------------------
    def _new_faces(self, start, smooth):
        self.bm.faces.ensure_lookup_table()
        for f in self.bm.faces[start:]:
            f.smooth = smooth

    def prism(self, outline, z0, z1, mat, bevel=0.0, top=None, smooth=False):
        """Extrude an outline of (column edge, row edge) points from z0 to z1; `bevel` (px) chamfers
        the top edges, `top` gives the top face its own palette index."""
        pts = [self.g.xy(c, r) for c, r in outline]
        area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
        if area < 0:
            pts.reverse()
        start = len(self.bm.faces)
        bevel_prism(self.bm, pts, z0, z1, bevel / 12, mat_index=self.m(mat),
                    top_mat=None if top is None else self.m(top))
        self._new_faces(start, smooth)

    def box(self, c0, c1, r0, r1, z0, z1, mat, bevel=0.0, top=None):
        """A box over pixel columns c0..c1 and rows r0..r1 (inclusive; fractions allowed)."""
        self.prism([(c0, r0), (c1 + 1, r0), (c1 + 1, r1 + 1), (c0, r1 + 1)], z0, z1, mat, bevel, top)

    def loft_y(self, c, sections, mat, sides=8, smooth=True, cap=True):
        """A loft down the grid centred on column edge `c`: sections are (row edge, half width px,
        half height units, z centre)."""
        start, fstart = len(self.bm.verts), len(self.bm.faces)
        common.loft(self.bm, [(self.g.y(r), w / 12, h, z) for r, w, h, z in sections], sides=sides,
                    mat_index=self.m(mat), cap_start=cap, cap_end=cap)
        self.bm.verts.ensure_lookup_table()
        for v in self.bm.verts[start:]:
            v.co.x += self.g.x(c)
        self._new_faces(fstart, smooth)

    def loft_x(self, r, sections, mat, sides=8, smooth=True, cap=True):
        """A loft across the grid centred on row edge `r`: sections are (column edge, half depth px,
        half height units, z centre)."""
        start, fstart = len(self.bm.verts), len(self.bm.faces)
        common.loft(self.bm, [(self.g.x(c), w / 12, h, z) for c, w, h, z in sections], sides=sides,
                    mat_index=self.m(mat), cap_start=cap, cap_end=cap)
        self.bm.verts.ensure_lookup_table()
        y0 = self.g.y(r)
        for v in self.bm.verts[start:]:
            v.co.x, v.co.y = v.co.y, v.co.x + y0
        self._new_faces(fstart, smooth)

    def ellipsoid(self, c, r, z, rx, ry, rz, mat, sides=12, rings=6):
        """An ellipsoid centred on (column edge, row edge, z) with radii in px (x, y) and units (z)."""
        start, fstart = len(self.bm.verts), len(self.bm.faces)
        secs = [(-ry, 0.0, 0.0, 0.0)]
        for i in range(1, rings):
            a = math.pi * i / rings
            secs.append((-ry * math.cos(a), rx * math.sin(a), rz * math.sin(a), 0.0))
        secs.append((ry, 0.0, 0.0, 0.0))
        common.loft(self.bm, [(y / 12, w / 12, h, zz) for y, w, h, zz in secs], sides=sides,
                    mat_index=self.m(mat))
        self.bm.verts.ensure_lookup_table()
        for v in self.bm.verts[start:]:
            v.co.x += self.g.x(c)
            v.co.y += self.g.y(r)
            v.co.z += z
        self._new_faces(fstart, True)

    def dome(self, c, r, z, rx, ry, rz, mat, sides=16, rings=4, outline=None):
        """A dome (the top half of an ellipsoid, closed underneath) on (column edge, row edge, z),
        radii in px (x, y) and units (z). `outline` (unit-circle points) replaces the round base."""
        bm, mi = self.bm, self.m(mat)
        fstart = len(bm.faces)
        cx, cy = self.g.xy(c, r)
        base = outline or [(math.cos(2 * math.pi * (i + 0.5) / sides), math.sin(2 * math.pi * (i + 0.5) / sides))
                           for i in range(sides)]
        levels = []
        for k in range(rings):
            phi = math.pi / 2 * k / rings
            s, h = math.cos(phi), math.sin(phi)
            levels.append([bm.verts.new((cx + ux * rx / 12 * s, cy - uy * ry / 12 * s, z + rz * h)) for ux, uy in base])
        apex = bm.verts.new((cx, cy, z + rz))
        n = len(base)
        bm.faces.new(list(reversed(levels[0]))).material_index = mi
        for a, b in zip(levels, levels[1:]):
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mi
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((levels[-1][i], levels[-1][j], apex)).material_index = mi
        self._new_faces(fstart, True)

    def cylinder(self, c, r, radius, z0, z1, mat, sides=16, top=None, dome=0.0, sx=1.0, sy=1.0):
        """An upright cylinder on (column edge, row edge), radius in px, with an optional domed top."""
        out = [(c + radius * sx * math.cos(2 * math.pi * (i + 0.5) / sides),
                r + radius * sy * math.sin(2 * math.pi * (i + 0.5) / sides)) for i in range(sides)]
        fstart = len(self.bm.faces)
        self.prism(out, z0, z1, mat, top=top)
        self._new_faces(fstart, True)
        if dome:
            self.dome(c, r, z1, radius * sx * 0.98, radius * sy * 0.98, dome, top if top is not None else mat,
                      sides=sides)

    def pixel_slab(self, pixels, keep, z0, z1, mat):
        """A slab from z0 to z1 over the grid pixels for which keep(index) is true, following the
        pixel edges exactly: the top merged into rectangles, walls only round the outside, no bottom
        (it stands on the ground)."""
        h, w = len(pixels), len(pixels[0])
        inside = lambda c, r: 0 <= r < h and 0 <= c < w and keep(pixels[r][c])  # noqa: E731
        bm, mi = self.bm, self.m(mat)
        verts = {}

        def v(c, r, z):
            key = (c, r, z)
            if key not in verts:
                verts[key] = bm.verts.new((self.g.x(c + self.g.c0), self.g.y(r + self.g.r0), z))
            return verts[key]

        # Top: runs per row, merged downward while the next row has the same run.
        open_runs = {}
        rects = []
        for r in range(h + 1):
            runs = set()
            c = 0
            while r < h and c < w:
                if inside(c, r):
                    c1 = c
                    while c1 + 1 < w and inside(c1 + 1, r):
                        c1 += 1
                    runs.add((c, c1 + 1))
                    c = c1 + 1
                c += 1
            for run in list(open_runs):
                if run not in runs:
                    rects.append((run[0], run[1], open_runs.pop(run), r))
            for run in runs:
                open_runs.setdefault(run, r)
        # Each rectangle's top, with vertices wherever a neighbouring rectangle's corner touches
        # its edges so the surface stays welded.
        corners = set()
        for c0, c1, r0, r1 in rects:
            corners.update(((c0, r0), (c1, r0), (c1, r1), (c0, r1)))
        for c0, c1, r0, r1 in rects:
            ring = [(c, r0) for c in range(c0, c1) if (c, r0) in corners or c == c0]
            ring += [(c1, r) for r in range(r0, r1) if (c1, r) in corners or r == r0]
            ring += [(c, r1) for c in range(c1, c0, -1) if (c, r1) in corners or c == c1]
            ring += [(c0, r) for r in range(r1, r0, -1) if (c0, r) in corners or r == r1]
            face = bm.faces.new([v(c, r, z1) for c, r in reversed(ring)])
            face.material_index = mi
        # Walls along the outside edges, one quad per pixel edge.
        for r in range(h):
            for c in range(w):
                if not inside(c, r):
                    continue
                for dc, dr, a, b in ((0, -1, (c + 1, r), (c, r)), (0, 1, (c, r + 1), (c + 1, r + 1)),
                                     (-1, 0, (c, r), (c, r + 1)), (1, 0, (c + 1, r + 1), (c + 1, r))):
                    if not inside(c + dc, r + dr):
                        f = bm.faces.new((v(*a, z0), v(*b, z0), v(*b, z1), v(*a, z1)))
                        f.material_index = mi
                        f.smooth = False

    def finish(self, name, collection):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        mesh = bpy.data.meshes.new(name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        for mat in self.m.list:
            mesh.materials.append(mat)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        return obj


# --- geometry ------------------------------------------------------------------------------------

def inset_outline(outline, d):
    """Move each vertex of a closed XY outline inward by `d` (along its corner's bisector)."""
    n = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1]
               for i in range(n))
    sign = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = outline[i - 1], outline[i], outline[(i + 1) % n]
        normals = []
        for a, b in ((p0, p1), (p1, p2)):
            ex_, ey_ = b[0] - a[0], b[1] - a[1]
            length = math.hypot(ex_, ey_) or 1.0
            normals.append((-ey_ / length * sign, ex_ / length * sign))
        nx, ny = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
        length = math.hypot(nx, ny) or 1.0
        nx, ny = nx / length, ny / length
        cos_half = max(0.35, nx * normals[0][0] + ny * normals[0][1])
        out.append((p1[0] + nx * d / cos_half, p1[1] + ny * d / cos_half))
    return out


def bevel_prism(bm, outline, z0, z1, bevel, mat_index=0, top_mat=None):
    """A prism from z0 to z1 (outline counter-clockwise) whose top edges are chamfered by `bevel`."""
    n = len(outline)
    if bevel <= 0:
        lo = [bm.verts.new((x, y, z0)) for x, y in outline]
        hi = [bm.verts.new((x, y, z1)) for x, y in outline]
        bm.faces.new(list(reversed(lo))).material_index = mat_index
        bm.faces.new(hi).material_index = mat_index if top_mat is None else top_mat
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((lo[i], lo[j], hi[j], hi[i])).material_index = mat_index
        return
    top = inset_outline(outline, bevel)
    lo = [bm.verts.new((x, y, z0)) for x, y in outline]
    mid = [bm.verts.new((x, y, z1 - bevel)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in top]
    bm.faces.new(list(reversed(lo))).material_index = mat_index
    bm.faces.new(hi).material_index = mat_index if top_mat is None else top_mat
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], mid[j], mid[i])).material_index = mat_index
        bm.faces.new((mid[i], mid[j], hi[j], hi[i])).material_index = mat_index


def mask_outline(pixels, keep, cuts=0):
    """The outline (column/row edges) of the largest region of pixels where keep(index) is true,
    traced round the pixel corners; `cuts` rounds of corner cutting turn stair steps into slopes
    (they can fold thin one-pixel spurs over themselves, so the default keeps the steps)."""
    h, w = len(pixels), len(pixels[0])
    inside = lambda c, r: 0 <= r < h and 0 <= c < w and keep(pixels[r][c])  # noqa: E731
    # Directed boundary edges between pixel corners (col, row), the inside always on the same side.
    edges = {}
    def add(p, q):
        edges.setdefault(p, []).append(q)
    for r in range(h):
        for c in range(w):
            if not inside(c, r):
                continue
            if not inside(c, r - 1):
                add((c + 1, r), (c, r))
            if not inside(c, r + 1):
                add((c, r + 1), (c + 1, r + 1))
            if not inside(c - 1, r):
                add((c, r), (c, r + 1))
            if not inside(c + 1, r):
                add((c + 1, r + 1), (c + 1, r))
    # Walk the loops; where two pixels touch only at a corner, turn toward the inside so each loop
    # bounds one 4-connected region.
    loops, used = [], set()
    for s0 in list(edges):
        for q0 in edges[s0]:
            if (s0, q0) in used:
                continue
            loop, p, q = [], s0, q0
            while (p, q) not in used:
                used.add((p, q))
                loop.append(p)
                d = (q[0] - p[0], q[1] - p[1])
                options = [n for n in edges.get(q, []) if (q, n) not in used]
                if not options:
                    break
                if len(options) > 1:
                    # inside is on the side where cross(d, e) < 0 (rows grow downward)
                    options.sort(key=lambda n: d[0] * (n[1] - q[1]) - d[1] * (n[0] - q[0]))
                p, q = q, options[0]
            loops.append(loop)
    pts = max(loops, key=len)
    # Drop collinear corners.
    out = []
    n = len(pts)
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) != 0:
            out.append(b)
    pts = [(float(c), float(r)) for c, r in out]
    for _ in range(cuts):
        cut = []
        n = len(pts)
        for i in range(n):
            (px_, py_), (qx, qy) = pts[i], pts[(i + 1) % n]
            cut.append((px_ * 0.75 + qx * 0.25, py_ * 0.75 + qy * 0.25))
            cut.append((px_ * 0.25 + qx * 0.75, py_ * 0.25 + qy * 0.75))
        pts = cut
    return pts[::2] if cuts else pts


# --- sprites and previews ------------------------------------------------------------------------

def grid_pixels(root, placed, w, h):
    """Palette indices of several pieces' first frames placed in one w x h grid (-1 = empty):
    placed is a list of (model name, column, row) of each piece's top-left corner."""
    grid = [[-1] * w for _ in range(h)]
    colors = {}
    for name, x0, y0 in placed:
        data = common.load_sprite(root, name)
        colors.update(data["colors"])
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < h and 0 <= x0 + c < w:
                    grid[y0 + r][x0 + c] = v
    return grid, colors


def without_strays(pixels):
    """A copy of a pixel grid without pixels that touch no other pixel (stray dots in the sprites)."""
    h, w = len(pixels), len(pixels[0])
    out = [row[:] for row in pixels]
    for r in range(h):
        for c in range(w):
            if pixels[r][c] >= 0 and not any(
                    0 <= r + dr < h and 0 <= c + dc < w and pixels[r + dr][c + dc] >= 0
                    for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc):
                out[r][c] = -1
    return out


def write_png(path, rows):
    """Write an RGBA image (rows of (r, g, b, a) 0-255 tuples, top row first) as a PNG."""
    h, w = len(rows), len(rows[0])
    raw = b"".join(b"\0" + bytes(v for px in row for v in px) for row in rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def grid_png(path, pixels, colors, scale=6):
    """The grid's pixels as a PNG, `scale` image px per sprite px."""
    rows = []
    for row in pixels:
        line = []
        for v in row:
            line.extend([(*colors[str(v)], 255) if v >= 0 else (0, 0, 0, 0)] * scale)
        rows.extend([line] * scale)
    write_png(path, rows)
    return path


# --- the machine's shared parts ------------------------------------------------------------------
# Machine coordinates: the grid of newshu.shp frames 1-5 over 39-43 over 79 (72 x 84 px). The
# other version of the right-hand block (frames 15, 17 over 53, 55) sits on columns 24-71, rows 0-55.

def material_settings():
    """Finish per palette index: greys metallic, reds painted, purples glassy, dark parts rough."""
    out = {}
    for i in range(1, 15):
        out[i] = dict(metallic=0.55, roughness=0.45)
    for i in (2, 3):
        out[i] = dict(metallic=0.35, roughness=0.7)
    for i in range(66, 79):
        out[i] = dict(metallic=0.3, roughness=0.5)
    for i in range(81, 95):
        out[i] = dict(metallic=0.45, roughness=0.3)
    for i in (16, 17, 18, 19, 161, 162, 163, 164, 165):
        out[i] = dict(metallic=0.2, roughness=0.75)
    for i in range(96, 103):
        out[i] = dict(metallic=0.25, roughness=0.6)
    return out


def towers(b, red_column_end=26):
    """The posts along the top (rows 0-19), common to both versions of the machine."""
    # Tall grey post (columns 30-32, rows 5-17): a light rounded cap, a red slot down its top and a
    # red column running on below it.
    b.box(30, 32, 5, 17, 0.0, 0.46, 8, bevel=0.5)
    b.loft_y(31.5, [(4.6, 1.5, 0.05, 0.43), (5.2, 1.6, 0.06, 0.44), (8.5, 1.6, 0.06, 0.44), (9.2, 1.3, 0.04, 0.44)],
             13, sides=8)
    b.box(31, 32, 11, 16, 0.38, 0.475, 72, bevel=0.3, top=68)
    b.box(31, 32, 17, red_column_end, 0.0, 0.3, 72, bevel=0.4, top=73)
    # Small red post (columns 36-37, rows 15-19) and a grey stub beside it.
    b.box(36, 37, 15, 19, 0.0, 0.34, 73, bevel=0.4, top=75)
    b.box(34, 34, 17, 19, 0.0, 0.22, 8, bevel=0.3)
    # The crystal post: grey post (columns 41-44, rows 9-12) with a light-purple crystal lying along
    # its top up to the point at row 0, and a red pillar beside it (columns 45-46, rows 6-13).
    b.box(41, 43, 9, 12, 0.0, 0.42, 5, bevel=0.4, top=8)
    b.box(44, 44, 5, 12, 0.0, 0.38, 6, bevel=0.3)
    b.loft_y(42.4, [(10.0, 1.6, 0.07, 0.43), (7.0, 1.7, 0.08, 0.44), (4.0, 1.5, 0.07, 0.45),
                    (2.0, 1.0, 0.05, 0.45), (0.4, 0.0, 0.0, 0.45)], 91, sides=6)
    b.box(45, 46, 6, 13, 0.0, 0.4, 73, bevel=0.5, top=75)
    # Red block under the crystal post (columns 41-45, rows 13-16), grey and red below it.
    b.box(41, 45, 13, 16, 0.0, 0.34, 72, bevel=0.5, top=76)
    b.box(41, 43, 17, 18, 0.0, 0.26, 10, bevel=0.3)
    b.box(44, 45, 17, 18, 0.0, 0.3, 69, bevel=0.3)
    # Grey drum (columns 47-53, rows 13-19) with a domed lid.
    b.cylinder(50.5, 16.5, 3.6, 0.0, 0.32, 7, sides=16, top=8, dome=0.035)


def grey_column(b, end_row):
    """The round grey column under the red block (columns 41-43, rows 19 down to end_row)."""
    b.loft_y(42.5, [(19.0, 1.6, 0.13, 0.13), (end_row, 1.6, 0.13, 0.13)], 8, sides=8)


def stem(b):
    """The stalk down from the body to the turret (rows 45-56), common to both versions."""
    b.box(29, 35, 45, 47, 0.0, 0.24, 5, bevel=0.4, top=7)
    b.box(33, 33, 48, 54, 0.0, 0.2, 5, bevel=0.2)
    b.box(29, 34, 55, 56, 0.0, 0.24, 6, bevel=0.4, top=8)
    b.box(30, 31, 49, 53, 0.0, 0.16, 85, bevel=0.3, top=88)
    b.loft_y(36.5, [(46.6, 0.7, 0.06, 0.16), (60.5, 0.7, 0.06, 0.16)], 88, sides=6)
    b.box(38, 40, 49, 50, 0.0, 0.18, 19, bevel=0.3, top=4)
    b.box(38, 41, 51, 52, 0.0, 0.22, 72, bevel=0.4, top=73)


def disc(b, face, centre):
    """The round lens on the right (columns 55-70, rows 29-41): a grey D-shaped housing, flat on its
    left, holding a domed face (palette `face`, `centre` for its middle) that bulges to the right."""
    rim = [(55.0, 29.0), (66.0, 29.0), (68.5, 30.5), (70.3, 33.0), (71.0, 35.5), (70.3, 38.5), (68.5, 40.3),
           (66.0, 41.4), (55.0, 41.4)]
    b.prism(rim, 0.0, 0.24, 6, bevel=0.6, top=7)
    b.loft_x(35.6, [(56.0, 3.7, 0.09, 0.22), (60.0, 3.8, 0.1, 0.22), (63.5, 3.6, 0.1, 0.22),
                    (66.0, 2.8, 0.08, 0.22), (67.6, 1.4, 0.05, 0.22), (68.2, 0.0, 0.0, 0.22)], face, sides=12)
    b.ellipsoid(62.0, 35.6, 0.31, 1.1, 1.0, 0.025, centre, sides=8, rings=4)
    # Rounded grey bar under the lens (columns 56-67, rows 39-41) and the low block left of it.
    b.loft_x(40.6, [(55.5, 1.3, 0.1, 0.14), (67.5, 1.3, 0.1, 0.14)], 8, sides=8)
    b.box(50, 57, 45, 47, 0.0, 0.14, 3, bevel=0.3)
