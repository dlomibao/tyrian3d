"""Helpers shared by batch b022's enemy scripts (build-models.sh skips lib_ modules).

Grid, Mats and paint are copied from lib_b006. rock() builds a lumpy rock whose outline seen from
above follows the sprite's mask (not an ellipse), with lighter pixels standing a little prouder,
and paints every face with the palette colour of the sprite pixel under it.
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units


class Grid:
    """Pixel grid of width w and height h (pixels), centred on the origin: column c, row r map to
    X = (c + 0.5 - w/2)/12, Y = (h/2 - (r + 0.5))/12."""

    def __init__(self, w, h, pixels=None):
        self.w, self.h, self.pixels = w, h, pixels

    def x(self, c):
        return (c + 0.5 - self.w / 2) * U

    def y(self, r):
        return (self.h / 2 - (r + 0.5)) * U

    def col(self, x):
        return x / U + self.w / 2 - 0.5

    def row(self, y):
        return self.h / 2 - 0.5 - y / U

    def sample(self, x, y, skip=(-1, 1), reach=2):
        """Palette index of the pixel under (x, y); transparent and outline pixels are skipped for
        the nearest other pixel within `reach` pixels (None if there is none)."""
        c, r = int(round(self.col(x))), int(round(self.row(y)))
        for d in range(reach + 1):
            best = None
            for dr in range(-d, d + 1):
                for dc in range(-d, d + 1):
                    if max(abs(dr), abs(dc)) != d:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < self.h and 0 <= cc < self.w:
                        v = self.pixels[rr][cc]
                        if v not in skip:
                            dist = dr * dr + dc * dc
                            if best is None or dist < best[0]:
                                best = (dist, v)
            if best is not None:
                return best[1]
        return None

    def filled(self, c, r):
        """Is pixel (c, r) part of the sprite (outline pixels included)?"""
        return 0 <= r < self.h and 0 <= c < self.w and self.pixels[r][c] != -1


class Mats:
    """Palette materials, one slot per (palette index, finish)."""

    def __init__(self, tag, colors):
        self.sprite = {"name": tag, "colors": colors}
        self.tag = tag
        self.list = []
        self.slots = {}

    def __call__(self, index, metallic=0.0, roughness=0.85, emission_strength=0.0):
        key = (index, metallic, roughness, emission_strength)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, self.tag, metallic=metallic,
                                                     roughness=roughness, emission_strength=emission_strength))
        return self.slots[key]


def radial_profile(grid, cc, cr, samples=144, smooth=2):
    """Distance (in pixels) from the continuous point (cc, cr) (pixel centres at c + 0.5) to the
    edge of the sprite's mask, for `samples` directions (angle measured with sprite up = +Y),
    smoothed over +-`smooth` neighbouring directions so the pixel staircase becomes a curve."""
    raw = []
    for i in range(samples):
        a = 2 * math.pi * i / samples
        dx, dy = math.cos(a), -math.sin(a)  # rows grow downwards
        d = 0.0
        while d < 40 and grid.filled(int(math.floor(cc + dx * (d + 0.05))), int(math.floor(cr + dy * (d + 0.05)))):
            d += 0.05
        raw.append(d)
    out = []
    for i in range(samples):
        vals = [raw[(i + k) % samples] for k in range(-smooth, smooth + 1)]
        out.append(sum(vals) / len(vals))
    return out


def rock(bm, grid, rz, slot_for, brightness, n=10, relief=0.25, lumps=None, shrink=0.15, under_slot=None):
    """A rock filling the sprite's mask seen from above, centred on z = 0 with half height `rz`.

    It is a cube-mapped sphere whose horizontal radius in each direction is the mask's radius
    (less `shrink` pixels), so the silhouette follows the sprite. brightness(index) -> 0..1 lifts
    lighter pixels (top half only) by up to `relief` of rz; lumps(x, y, z) -> scale adds noise.
    Faces take slot_for(palette index); faces pointing down take under_slot. Returns the first
    face index."""
    cells = [(c, r) for r in range(grid.h) for c in range(grid.w) if grid.filled(c, r)]
    cc = sum(c + 0.5 for c, _ in cells) / len(cells)
    cr = sum(r + 0.5 for _, r in cells) / len(cells)
    samples = 144
    prof = radial_profile(grid, cc, cr, samples)

    def radius(a):
        t = (a % (2 * math.pi)) / (2 * math.pi) * samples
        i = int(t)
        f = t - i
        return (prof[i % samples] * (1 - f) + prof[(i + 1) % samples] * f) - shrink

    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    first_face, first_vert = len(bm.faces), len(bm.verts)
    cube = bmesh.ops.create_cube(bm, size=2.0)
    edges = list({e for v in cube["verts"] for e in v.link_edges})
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=n - 1, use_grid_fill=True)
    bm.verts.ensure_lookup_table()
    ox, oy = (cc - grid.w / 2) * U, (grid.h / 2 - cr) * U
    for v in bm.verts[first_vert:]:
        x, y, z = v.co
        sx = x * math.sqrt(max(0.0, 1 - y * y / 2 - z * z / 2 + y * y * z * z / 3))
        sy = y * math.sqrt(max(0.0, 1 - z * z / 2 - x * x / 2 + z * z * x * x / 3))
        sz = z * math.sqrt(max(0.0, 1 - x * x / 2 - y * y / 2 + x * x * y * y / 3))
        h = math.hypot(sx, sy)
        a = math.atan2(sy, sx)
        # Keep the sides steep (a superellipse profile) so the top view fills the sprite's area.
        hr = h ** 0.6 if h > 0 else 0.0
        s = lumps(sx, sy, sz) if lumps else 1.0
        r = radius(a) * U * hr * (0.96 + 0.04 * s)
        px, py = ox + r * math.cos(a), oy + r * math.sin(a)
        zz = rz * sz * s
        if sz > 0:
            idx = grid.sample(px, py)
            if idx is not None:
                zz *= 1 + relief * (brightness(idx) - 0.5) * 2 * min(1.0, h * 1.5)
        v.co = (px, py, zz)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        f.normal_update()
        if under_slot is not None and f.normal.z < -0.35:
            f.material_index = under_slot
            continue
        c = f.calc_center_median()
        idx = grid.sample(c.x, c.y)
        f.material_index = slot_for(idx if idx is not None else -1)
    return first_face


def preview(root, name, objs, sprite, frame=0):
    """Render the --preview PNG if the script was asked for one."""
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        f = sprite["frames"][frame]
        ref = Path(root) / "reference" / "models" / sprite["name"] / f["image"]
        common.render_preview(objs, out, ref, size=f["size"])
