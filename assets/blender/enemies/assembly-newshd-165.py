"""Giant stone face (newshd.shp 155, 165 and newshp.shp 123, 127, an assembly of 4 pieces): a 3D
version of its sprites.

Seen in level 1.6. Four 2x2 ground enemies side by side make one 48x56 px carving
(sprite.json `assemblyLayout`): a bald grey stone head lying face up, lit from the upper left.
A domed forehead, a brow over two sunken eye sockets with closed eyes, a long straight nose down
the middle, cheekbones, a firm mouth with thin lips, and a rounded chin. The whole head is one
sculpted surface built in assembly coordinates (a profile down the face times a rounded section
across it, plus the features), then cut into the four pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshd-165.py [-- --preview out.png]
(the preview is the whole head; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b075 as L  # noqa: E402

NAME = "assembly-newshd-165"
ROOT = common.repo_root(__file__)
PIECES = ["newshd-155", "newshp-123", "newshd-165", "newshp-127"]
# Assembly pixel (0, 0) is the top-left corner of newshd-155 (screen cx 56 - 12, cy -18 - 14);
# the assembly is 48 x 56 px and its centre (screen 68, -4) is the Blender origin.
CX0, CY0 = 68, -4
W, H = 48, 56
AXIS = 24.5  # the face's axis: the pixel edge column through the middle of the nose (column 24)


def XE(c):
    return L.XE(c, W)


def YE(r):
    return L.YE(r, H)


def gauss(dx, dy, sx, sy):
    return math.exp(-(dx / sx) ** 2 - (dy / sy) ** 2)


def interp(points, r):
    """Piecewise-linear lookup in a list of (row, value)."""
    if r <= points[0][0]:
        return points[0][1]
    for (r0, v0), (r1, v1) in zip(points, points[1:]):
        if r <= r1:
            t = (r - r0) / (r1 - r0)
            return v0 + (v1 - v0) * t
    return points[-1][1]


# Height of the face down its middle (without the nose): crown, forehead, brow, face, chin.
PROFILE = [(3.0, 0.06), (4.5, 0.26), (7.0, 0.46), (10.0, 0.6), (14.0, 0.69), (18.0, 0.72), (21.5, 0.71),
           (24.0, 0.64), (28.0, 0.61), (34.0, 0.59), (38.0, 0.58), (42.0, 0.56), (45.0, 0.53), (48.0, 0.42),
           (50.5, 0.22), (52.0, 0.05)]
# The nose's height above the face down its ridge: a bridge between the eyes to a tip at row 33.
NOSE = [(21.5, 0.0), (23.0, 0.04), (27.0, 0.08), (31.0, 0.14), (33.0, 0.19), (34.3, 0.1), (35.2, 0.0)]


def height(c, r, hw):
    """Surface height at pixel point (c, r) (edge coordinates), hw = the head's half width there."""
    dx = c - AXIS
    t = min(abs(dx) / hw, 1.0)
    z = interp(PROFILE, r) * (1 - t ** 2.2) ** 0.5
    ax = abs(dx)
    # The domed forehead.
    z += 0.06 * gauss(dx + 0.5, r - 15.5, 8.0, 5.0)
    # Brow ridge over the eyes and the sunken eye sockets (centred on columns 19.5 and 29.5).
    z += 0.035 * gauss(ax - 5.3, r - 21.6, 4.0, 1.1)
    z -= 0.17 * gauss(ax - 5.3, r - 24.8, 3.4, 2.3)
    # Cheekbones beside the nose.
    z += 0.05 * gauss(ax - 7.6, r - 31.0, 2.6, 2.6)
    # Nose: a ridge down the middle with flared wings at its tip.
    z += interp(NOSE, r) * gauss(dx, 0, 1.6, 1)
    z += 0.07 * gauss(ax - 2.4, r - 33.6, 1.4, 1.0)
    # Mouth: the groove under the nose, the upper lip, the line between the lips, the lower lip.
    z -= 0.06 * gauss(dx, r - 35.6, 6.0, 0.8)
    z += 0.04 * gauss(dx + 0.5, r - 38.0, 4.5, 1.2)
    z -= 0.05 * gauss(dx + 0.5, r - 40.0, 5.5, 0.6)
    z += 0.035 * gauss(dx + 1.0, r - 41.2, 3.8, 0.8)
    # Chin.
    z += 0.04 * gauss(dx + 0.5, r - 45.5, 4.0, 2.2)
    return max(z, 0.03)


def material_at(c, r):
    """Which material a point of the face gets: dark for the closed eyes and the mouth lines."""
    dx = c - AXIS
    ax = abs(dx)
    if abs(r - 23.4) < 0.6 and 1.6 < ax < 8.6:
        return "dark"
    if abs(r - 35.6) < 0.6 and ax < 4.5:
        return "dark"
    if abs(r - 40.0) < 0.5 and abs(dx + 0.5) < 4.0:
        return "dark"
    return "stone"


def outline(pixels):
    """The head's left and right edge (pixel edges, inset a little) at each row centre."""
    rows = {}
    for r, row in enumerate(pixels):
        cols = [c for c, v in enumerate(row) if v >= 0]
        if cols:
            rows[r + 0.5] = (min(cols) + 0.35, max(cols) + 1 - 0.35)
    table = sorted(rows.items())
    # Round off the crown and the chin: a narrower row half a pixel past each end.
    (r0, (a0, b0)), (r1, (a1, b1)) = table[0], table[-1]
    table = [(r0 - 0.5, (a0 + 1.5, b0 - 1.5))] + table + [(r1 + 0.5, (a1 + 1.0, b1 - 1.0))]
    # Smooth the pixel staircase so the sides come out as a smooth curve.
    smooth = []
    for i, (r, _) in enumerate(table):
        near = table[max(i - 1, 0):i + 2]
        smooth.append((r, (sum(v[0] for _, v in near) / len(near), sum(v[1] for _, v in near) / len(near))))
    return smooth


def edges_at(table, r):
    left = interp([(k, v[0]) for k, v in table], r)
    right = interp([(k, v[1]) for k, v in table], r)
    return left, right


def assembly_pixels(layout_px):
    grid = [[-1] * W for _ in range(H)]
    for name, (x0, y0) in layout_px.items():
        data = common.load_sprite(ROOT, name)
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[y0 + r][x0 + c] = v
    return grid


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    tag = "nshd165"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.05, roughness=0.75),  # 0 grey stone
        pal(3, metallic=0.0, roughness=0.9),  # 1 dark eye slits and mouth lines
        pal(5, metallic=0.0, roughness=0.85),  # 2 shadowed walls and underside
    ]
    slot = {"stone": 0, "dark": 1}
    SIDE = 2

    table = outline(grid)
    r_top, r_bot = table[0][0], table[-1][0]
    K, N = 50, 32  # rows and columns of the surface grid
    bm = bmesh.new()
    surf = []
    for k in range(K + 1):
        r = r_top + (r_bot - r_top) * k / K
        left, right = edges_at(table, r)
        hw = (right - left) / 2
        row = []
        for j in range(N + 1):
            u = j / N
            # Bunch the columns a little towards the middle, where the nose and mouth are.
            u = 0.5 + (u - 0.5) * (0.75 + 0.25 * abs(2 * u - 1))
            c = left + (right - left) * u
            row.append(bm.verts.new((XE(c), YE(r), height(c, r, max(hw, 0.5)))))
        surf.append(row)
    for k in range(K):
        for j in range(N):
            f = bm.faces.new((surf[k][j], surf[k + 1][j], surf[k + 1][j + 1], surf[k][j + 1]))
            centre = f.calc_center_median()
            c = centre.x * 12 + W / 2
            r = H / 2 - centre.y * 12
            f.material_index = slot[material_at(c, r)]
            f.smooth = True

    # Walls down to the ground round the rim, and the base.
    rim = ([surf[0][j] for j in range(N + 1)] + [surf[k][N] for k in range(1, K + 1)]
           + [surf[K][j] for j in range(N - 1, -1, -1)] + [surf[k][0] for k in range(K - 1, 0, -1)])
    base = [bm.verts.new((v.co.x, v.co.y, 0.0)) for v in rim]
    n = len(rim)
    for i in range(n):
        f = bm.faces.new((rim[i], base[i], base[(i + 1) % n], rim[(i + 1) % n]))
        f.material_index = SIDE
        f.smooth = False
    f = bm.faces.new(list(reversed(base)))
    f.material_index = SIDE

    return L.to_object(NAME, bm, mats, coll)


def merged_sprite():
    data = common.load_sprite(ROOT, PIECES[0])
    for name in PIECES[1:]:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(grid, colors, out):
    import numpy as np
    img = np.zeros((H, W, 4), dtype=np.float32)
    for r in range(H):
        for c in range(W):
            v = grid[r][c]
            if v >= 0:
                img[r, c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    layout_px = {name: (cx + W // 2 - 12, cy + H // 2 - 14) for name, cx, cy in layout}
    grid = assembly_pixels(layout_px)
    obj = build(sprite, grid)
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = L.preview_arg()
    if out:
        import tempfile
        ref = composite_png(grid, sprite["colors"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
