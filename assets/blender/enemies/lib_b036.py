"""Helpers shared by batch b036's enemy scripts (newshd asteroids and the falling canister).
build-models.sh skips lib_ modules.

- Grid: sprite (or assembly) pixel coordinates to Blender X/Y, and the pixel under a point.
- Mats: palette materials made on demand, one slot per palette index (and finish).
- paint: give faces the material of the sprite pixel under them (seen from above).
- rock: a lumpy rock whose outline follows the sprite's filled pixels (Grid, Mats and paint are
  after lib_b006).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units
OUTLINE = (-1, 1, 32)  # transparent and the dark outline the game draws itself


class Grid:
    """Pixel grid of width w and height h (pixels), centred on the origin: column c, row r (pixel
    centres at c + 0.5, r + 0.5) map to X = (c + 0.5 - w/2)/12, Y = (h/2 - (r + 0.5))/12. Fractional
    columns/rows are allowed; x(c) is the centre of column c."""

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

    def at(self, c, r):
        """The palette index of the pixel containing the (fractional, pixel-edge) point c, r."""
        ci, ri = int(math.floor(c)), int(math.floor(r))
        if 0 <= ri < self.h and 0 <= ci < self.w:
            return self.pixels[ri][ci]
        return -1

    def sample(self, x, y, skip=OUTLINE, reach=2):
        """The palette index of the pixel under (x, y); transparent and outline pixels are skipped
        for the nearest other pixel within `reach` pixels (None if there is none)."""
        c, r = int(round(self.col(x))), int(round(self.row(y)))
        best = None
        for d in range(reach + 1):
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


class Mats:
    """Palette materials, one slot per (palette index, finish). `colors` maps index -> RGB (merge
    several sprites' `colors` for an assembly)."""

    def __init__(self, tag, colors):
        self.sprite = {"name": tag, "colors": colors}
        self.tag = tag
        self.list = []
        self.slots = {}

    def __call__(self, index, metallic=0.3, roughness=0.5, emission_strength=0.0):
        key = (index, metallic, roughness, emission_strength)
        if key not in self.slots:
            tag = self.tag if not emission_strength else f"{self.tag}_glow"
            if any(k[0] == index and k != key for k in self.slots):
                tag = f"{self.tag}_{len(self.list)}"
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, tag, metallic=metallic,
                                                     roughness=roughness, emission_strength=emission_strength))
        return self.slots[key]


def merged_colors(sprites):
    colors = {}
    for s in sprites:
        colors.update(s["colors"])
    return colors


def paint(bm, first_face, grid, slot_for, min_nz=None):
    """Set the material of every face added since face index `first_face` from the sprite pixel
    under its centre: slot_for(palette_index) -> material slot (or None to leave it). Faces whose
    normal points further down than min_nz keep their material."""
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    for f in bm.faces[first_face:]:
        if min_nz is not None and f.normal.z < min_nz:
            continue
        c = f.calc_center_median()
        idx = grid.sample(c.x, c.y)
        if idx is None:
            continue
        slot = slot_for(idx)
        if slot is not None:
            f.material_index = slot


def luminance(colors, index):
    rgb = colors.get(str(index))
    return sum(rgb) / (3 * 255) if rgb else 0.0


def blurred(grid, colors, sigma=1.6):
    """The sprite's brightness (0-1) blurred with a gaussian of `sigma` px, as a function of a
    fractional pixel centre (c, r); outline and transparent pixels don't count."""
    vals = {}
    for r, line in enumerate(grid.pixels):
        for c, v in enumerate(line):
            if v not in OUTLINE:
                vals[(c, r)] = luminance(colors, v)
    reach = int(math.ceil(sigma * 2.5))

    def f(c, r):
        tot = wsum = 0.0
        ci, ri = int(round(c)), int(round(r))
        for dr in range(-reach, reach + 1):
            for dc in range(-reach, reach + 1):
                v = vals.get((ci + dc, ri + dr))
                if v is None:
                    continue
                w = math.exp(-((ci + dc - c) ** 2 + (ri + dr - r) ** 2) / (2 * sigma * sigma))
                tot += w * v
                wsum += w
        return tot / wsum if wsum else 0.0
    return f


def polar_outline(grid, c0, r0, segments, margin=0.3, smooth=1, filled=None):
    """For `segments` directions round the pixel point (c0, r0) (pixel centre coordinates), the
    distance in px to the edge of the sprite's filled pixels (the last filled point along the
    ray), plus `margin`. filled(index) says which pixels count (default: not outline)."""
    filled = filled or (lambda v: v not in OUTLINE)
    radii = []
    for k in range(segments):
        a = 2 * math.pi * k / segments
        dc, dr = math.cos(a), -math.sin(a)  # angle counter-clockwise from +X, seen from above
        last, t = 0.0, 0.0
        while t < max(grid.w, grid.h):
            if filled(grid.at(c0 + 0.5 + t * dc, r0 + 0.5 + t * dr)):
                last = t
            t += 0.05
        radii.append(last + margin)
    for _ in range(smooth):
        radii = [(radii[k - 1] + 2 * radii[k] + radii[(k + 1) % segments]) / 4 for k in range(segments)]
    return radii


def rock(bm, grid, centre, top, bottom, lumps=(), shade=0.0, sigma=1.6, colors=None, n=12, power=2.2,
         mat_index=0, flats=(), filled=None, margin=0.3):
    """A rock whose outline (seen from above) follows the sprite's filled pixels: a subdivided cube
    (an even quad grid seen from above) blown up to a sphere, then stretched in each direction
    round `centre` (col, row) out to the outline. The top rises to `top` units in a rounded dome
    (superellipse `power`), the underside sinks to -`bottom`. `lumps` are (col, row, radius_px,
    height) bumps on the top (cosine falloff); `shade` lifts the sprite's brighter areas and sinks
    the darker cracks by about that many units (from the blurred brightness, `colors` = the sprite's
    colours). `flats` are (col, row, radius_px, z) caps that flatten the top down to height z (the
    sprite's flat facets). Returns the index of its first face."""
    c0, r0 = centre
    segs = 180
    radii = polar_outline(grid, c0, r0, segs, margin=margin, smooth=2, filled=filled)
    lum = blurred(grid, colors, sigma) if shade else None
    mean = 0.0
    if lum:
        pts = [(c, r) for r, line in enumerate(grid.pixels) for c, v in enumerate(line) if v not in OUTLINE]
        mean = sum(lum(c, r) for c, r in pts) / len(pts)

    def outline_at(a):
        t = (a % (2 * math.pi)) / (2 * math.pi) * segs
        k = int(t) % segs
        w = t - int(t)
        return radii[k] * (1 - w) + radii[(k + 1) % segs] * w

    def height(c, r, f):
        z = top * max(0.0, 1 - f ** power) ** (1 / power)
        env = max(0.0, 1 - f ** 3)
        for lc, lr, lrad, lh in lumps:
            d = math.hypot(c - lc, r - lr)
            if d < lrad:
                z += lh * (0.5 + 0.5 * math.cos(math.pi * d / lrad)) * env
        for fc, fr, frad, fz in flats:
            d = math.hypot(c - fc, r - fr)
            if d < frad and z > fz:
                w = 1.0 if d < frad * 0.6 else 0.5 + 0.5 * math.cos(math.pi * (d - frad * 0.6) / (frad * 0.4))
                z += (fz - z) * w * env
        if lum:
            z += shade * (lum(c, r) - mean) / 0.25 * env
        return z

    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    first_face, first_vert = len(bm.faces), len(bm.verts)
    cube = bmesh.ops.create_cube(bm, size=2.0)
    edges = list({e for v in cube["verts"] for e in v.link_edges})
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=n - 1, use_grid_fill=True)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[first_vert:]:
        x, y, z = v.co
        sx = x * math.sqrt(max(0.0, 1 - y * y / 2 - z * z / 2 + y * y * z * z / 3))
        sy = y * math.sqrt(max(0.0, 1 - z * z / 2 - x * x / 2 + z * z * x * x / 3))
        sz = z * math.sqrt(max(0.0, 1 - x * x / 2 - y * y / 2 + x * x * y * y / 3))
        rho = min(1.0, math.hypot(sx, sy))
        a = math.atan2(sy, sx)
        rad = rho * outline_at(a)
        c = c0 + rad * math.cos(a)
        r = r0 - rad * math.sin(a)
        if sz >= 0:
            zz = height(c, r, rho)
        else:
            zz = -bottom * abs(sz)
        v.co = (grid.x(c), grid.y(r), zz)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first_face:]:
        f.material_index = mat_index
    return first_face


def preview(root, name, objs, sprite, frame=0):
    """Render the --preview PNG if the script was asked for one."""
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        f = sprite["frames"][frame]
        ref = Path(root) / "reference" / "models" / sprite["name"] / f["image"]
        common.render_preview(objs, out, ref, size=f["size"])
