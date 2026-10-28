"""Brown rock (newshr.shp frame 171): a 3D version of its sprite.

Seen in episode 3 (levels 19 and 4). A small tumbling rock, 9 x 11 px: a rounded lump of brown
stone lit from the upper left, its lightest face near the top and a speck of dark red at its top
tip. One frame, one model: a boulder whose outline follows the sprite, domed (about 4 px above
its midplane at the peak, under the light lobes, and about 3 px below) rather than a flat-topped
bun, with the sprite's light lobes standing about 1 px proud and the dark crevices between them
cut in, and whose faces take the colour of the sprite pixel under them. Matte stone.

Run: blender --background --python assets/blender/enemies/newshr-171.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b022 as lib  # noqa: E402

NAME = "newshr-171"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U

TOP_PX = 4.1     # dome height above the midplane before relief (peak with relief about 4.5 px)
BOTTOM_PX = 3.6  # underside depth below the midplane (about 8 px thick in all)
N = 13           # cube-sphere subdivisions (6 * N * N quads), flat shaded so it reads as facets
JITTER_PX = 0.22  # random vertex offset that breaks the sphere into irregular stone facets


def lumps(x, y, z):
    """Irregular facets so it reads as stone, not an egg."""
    return 1 + 0.08 * math.sin(3.7 * x + 0.9) * math.cos(3.1 * y - 1.2) + 0.06 * math.sin(4.9 * z + 2.3 * y + 0.5)


def jitter(x, y, z, k):
    """Deterministic pseudo-random value in [-1, 1] for a point on the unit sphere."""
    v = math.sin(12.9898 * x + 78.233 * y + 37.719 * z + 4.1 * k) * 43758.5453
    return 2 * (v - math.floor(v)) - 1


def brightness(i):
    return 0.3 if i in (66, 67) else (i - 162) / 9


def relief_field(grid):
    """Per-pixel relief in px: light lobes up to about +1.3 px, dark crevices down to about -1 px,
    smoothed over the neighbouring pixels so the bumps are rounded."""
    raw = {}
    for r in range(grid.h):
        for c in range(grid.w):
            v = grid.pixels[r][c]
            if v != -1:
                raw[(c, r)] = max(-1.0, min(1.3, 2.4 * (brightness(v) - 0.45)))
    out = {}
    for (c, r) in raw:
        tw = tv = 0.0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                k = raw.get((c + dc, r + dr))
                if k is None:
                    continue
                w = 1.0 if dr == dc == 0 else (0.35 if dr == 0 or dc == 0 else 0.15)
                tw += w
                tv += w * k
        out[(c, r)] = tv / tw
    return out


def sample_field(grid, field, x, y):
    """Bilinear sample of the per-pixel field at (x, y) in units (0 outside the sprite)."""
    fc, fr = grid.col(x), grid.row(y)
    c0, r0 = math.floor(fc), math.floor(fr)
    tx, ty = fc - c0, fr - r0
    total = wsum = 0.0
    for dc, dr, w in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)), (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        v = field.get((c0 + dc, r0 + dr))
        if v is not None and w > 0:
            total += w * v
            wsum += w
    return total / wsum if wsum > 0 else 0.0


def boulder(bm, grid, slot_for, under_slot, shrink=0.15):
    """A cube-mapped sphere whose outline from above is the sprite's mask (lib.radial_profile) and
    whose section is a continuous dome: z = H * (1 - t^2.2)^0.5 at normalised radius t, plus the
    smoothed relief field on top (faded out towards the rim)."""
    cells = [(c, r) for r in range(grid.h) for c in range(grid.w) if grid.filled(c, r)]
    cc = sum(c + 0.5 for c, _ in cells) / len(cells)
    cr = sum(r + 0.5 for _, r in cells) / len(cells)
    samples = 144
    prof = lib.radial_profile(grid, cc, cr, samples)
    field = relief_field(grid)

    def radius(a):
        t = (a % (2 * math.pi)) / (2 * math.pi) * samples
        i = int(t)
        f = t - i
        return (prof[i % samples] * (1 - f) + prof[(i + 1) % samples] * f) - shrink

    cube = bmesh.ops.create_cube(bm, size=2.0)
    edges = list({e for v in cube["verts"] for e in v.link_edges})
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=N - 1, use_grid_fill=True)
    bm.verts.ensure_lookup_table()
    ox, oy = (cc - grid.w / 2) * U, (grid.h / 2 - cr) * U
    for v in bm.verts:
        x, y, z = v.co
        sx = x * math.sqrt(max(0.0, 1 - y * y / 2 - z * z / 2 + y * y * z * z / 3))
        sy = y * math.sqrt(max(0.0, 1 - z * z / 2 - x * x / 2 + z * z * x * x / 3))
        sz = z * math.sqrt(max(0.0, 1 - x * x / 2 - y * y / 2 + x * x * y * y / 3))
        h = math.hypot(sx, sy)
        a = math.atan2(sy, sx)
        # Steep sides (h^0.6) so the top view fills the sprite's area; the height is a dome in t.
        t = min(1.0, h ** 0.6) if h > 0 else 0.0
        s = lumps(sx, sy, sz)
        r = radius(a) * U * t * (0.96 + 0.04 * s)
        px, py = ox + r * math.cos(a), oy + r * math.sin(a)
        dome = math.sqrt(max(0.0, 1 - t ** 2.2))
        # The same irregular stone all round: lumps and facet jitter on both halves, so there is no
        # smooth underside and no seam at the midplane (the jitter fades out on the rim, which is
        # the outline from above, so the top view keeps the sprite's mask).
        jz = JITTER_PX * jitter(sx, sy, sz, 1) * min(1.0, dome * 1.5)
        if sz >= 0:
            fade = min(1.0, max(0.0, (1 - t) / 0.4))
            zz = (TOP_PX * dome * (1 + 0.6 * (s - 1)) + sample_field(grid, field, px, py) * fade * dome ** 0.5 + jz) * U
        else:
            zz = (-BOTTOM_PX * dome * (1 + 0.8 * (s - 1)) + jz) * U
        if 0 < t < 1:
            jr = 0.12 * jitter(sx, sy, sz, 2) * U * (1 - abs(sz)) * t
            px, py = px + jr * math.cos(a), py + jr * math.sin(a)
        v.co = (px, py, zz)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < -0.35:
            f.material_index = under_slot
            continue
        c = f.calc_center_median()
        idx = grid.sample(c.x, c.y)
        f.material_index = slot_for(idx if idx is not None else -1)


def build(sprite):
    coll = common.reset_collection(NAME)
    grid = lib.Grid(12, 14, sprite["frames"][0]["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    # Brown stone, each face in the exact shade of the pixel under it (162-171), and the dark red
    # speck (66, 67). Matte.
    shades = {i: mats(i, roughness=1.0) for i in range(162, 172)}
    red = mats(67, roughness=1.0)

    def slot(i):
        if i in (66, 67):
            return red
        return shades.get(i, shades[163])

    bm = bmesh.new()
    boulder(bm, grid, slot, shades[163])
    obj = common.mesh_object(NAME, bm, mats.list, coll, smooth=False)
    for m in mats.list:
        m.roughness = 1.0  # viewport (Workbench) roughness too
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
