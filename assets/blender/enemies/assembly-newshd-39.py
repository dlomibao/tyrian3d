"""Rock outcrop (newshd.shp, assembly of 4 pieces): a 3D version of its sprites.

Seen in level 1.5. Four 2x2 ground enemies (newshd-1, -3, -39, -41) side by side make one
48x56 px grey boulder heap: a cluster of rounded, faceted rocks lit from the upper left (bright
lumps on the left and in the middle, darker rocks sloping away on the right and at the bottom).

The heap is built once in assembly coordinates: a low rubble skirt that follows the sprite's
outline, with a dozen faceted boulders on it where the sprite shows lumps. Each face takes the
grey of the sprite pixels under it (quantised palette indices 4-13), so the light ridges and dark
cracks of the sprite stay where they are. Then common.split_assembly cuts it into the 4 pieces.

Run: blender --background --python assets/blender/enemies/assembly-newshd-39.py [-- --preview out.png]
(the preview is the whole heap; each piece also gets <piece>.png next to it).
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

NAME = "assembly-newshd-39"
ROOT = common.repo_root(__file__)
PIECES = ["newshd-1", "newshd-3", "newshd-39", "newshd-41"]
# Assembly pixel (0, 0) is the top-left corner of newshd-1 (screen cx 122 - 12, cy 29 - 14);
# the assembly is 48 x 56 px and its centre (screen 134, 43) is the Blender origin.
CX0, CY0 = 134, 43
W, H = 48, 56
PX = 1 / 12
GROW = 1.15  # boulders overlap into one mass

# Brightness level of each palette index the sprite uses (greys are their own index; the few
# blue-grey pixels count as the grey of the same lightness).
LEVEL = {3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12, 13: 13, 14: 14, 15: 15,
         102: 4, 106: 8, 108: 11, 109: 12, 110: 13, 94: 13}
SHADES = list(range(4, 14))  # palette indices used as materials


def X(c):
    """Assembly pixel column (centre; fractions allowed) to Blender X."""
    return (c + 0.5 - W / 2) / 12


def Y(r):
    """Assembly pixel row (centre) to Blender Y: sprite up is +Y."""
    return (H / 2 - (r + 0.5)) / 12


def to_px(x, y):
    return x * 12 + W / 2 - 0.5, H / 2 - y * 12 - 0.5


# Boulders: (col, row, half-width px, half-length px, rotation deg, height units). Each is the
# upper half of a faceted, slightly lumpy ellipsoid standing on the ground.
BOULDERS = [
    (21.5, 9.5, 6.5, 4.8, -10, 0.55),  # top rock
    (10.0, 16.0, 4.6, 4.4, 20, 0.45),  # left rock with the bright face
    (17.5, 21.5, 6.0, 6.8, 10, 0.75),  # big bright rock in the middle
    (7.5, 25.0, 5.0, 4.0, -15, 0.42),  # lower-left rock
    (8.8, 32.0, 3.6, 4.0, 0, 0.3),  # dark rock under it
    (30.0, 14.5, 7.5, 4.6, -15, 0.38),  # dark rock on the upper right
    (36.0, 22.5, 5.6, 5.8, 0, 0.45),  # right rock
    (26.5, 23.0, 4.5, 5.0, 0, 0.5),  # rock right of the middle
    (22.5, 29.0, 6.0, 3.4, 0, 0.42),  # saddle between the middle rocks
    (19.0, 34.5, 6.8, 4.4, -10, 0.6),  # bright rock low in the middle
    (32.0, 34.0, 6.6, 7.2, 10, 0.4),  # dark rocks on the lower right
    (18.5, 42.0, 5.2, 5.0, 0, 0.4),  # bottom rock
    (28.0, 41.0, 5.6, 3.6, -20, 0.3),  # rock right of the bottom one
    (13.0, 28.5, 3.6, 3.2, 0, 0.35),  # small rock left of the saddle
]


def load_grid():
    """The whole heap's first frames as one 56 x 48 grid of palette indices (-1 transparent)."""
    grid = [[-1] * W for _ in range(H)]
    sprite = common.load_sprite(ROOT, PIECES[0])
    for e in sprite["assemblyLayout"]:
        if e["model"] not in PIECES:
            continue
        data = common.load_sprite(ROOT, e["model"])
        x0, y0 = e["cx"] - CX0 + W // 2 - 12, e["cy"] - CY0 + H // 2 - 14
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[y0 + r][x0 + c] = v
    return grid


def outline_spans(grid):
    """Per row, the first and last column of the rock (outline pixels, index 1 and 32, left out)."""
    spans = {}
    for r, row in enumerate(grid):
        cols = [c for c, v in enumerate(row) if v in LEVEL]
        if cols:
            spans[r] = (min(cols), max(cols))
    return spans


def shade_at(grid, c, r):
    """Mean brightness level of the rock pixels in the 3x3 around (c, r), or None."""
    vals = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            rr, cc = int(round(r)) + dr, int(round(c)) + dc
            if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] in LEVEL:
                w = 2 if dr == 0 and dc == 0 else 1
                vals += [LEVEL[grid[rr][cc]]] * w
    return sum(vals) / len(vals) if vals else None


def skirt(bm, spans, inset=3.0, height=0.18):
    """A low rubble apron: the sprite's outline at the ground, sloping in to a flat top."""
    rows = sorted(spans)
    top, bot = rows[0], rows[-1]
    n = 18
    def ring(d, z):
        pts = []
        r0, r1 = top - 0.5 + d, bot + 0.5 - d
        samples = [r0 + (r1 - r0) * i / n for i in range(n + 1)]
        def span(r):
            rr = min(max(int(round(r)), top), bot)
            return spans[rr]
        # down the left side, then up the right side (counter-clockwise seen from above)
        for r in samples:
            c0, _ = span(r)
            pts.append((X(c0 - 0.5 + d), Y(r), z))
        for r in reversed(samples):
            _, c1 = span(r)
            pts.append((X(c1 + 0.5 - d), Y(r), z))
        return [bm.verts.new(p) for p in pts]
    low = ring(0.0, 0.0)
    high = ring(inset, height)
    k = len(low)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((low[i], low[j], high[j], high[i]))
    bm.faces.new(high)


def boulder(bm, col, row, rx, ry, rot, h, rng):
    """The upper half of a lumpy, faceted ellipsoid standing on z = 0."""
    res = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    verts = res["verts"]
    a = math.radians(rot)
    for v in verts:
        p = v.co.copy()
        k = 1.0 + rng.uniform(-0.09, 0.09)
        # flatter crown and fuller shoulders, like a weathered rock
        z = p.z
        if z > 0:
            z = z ** 0.85
        x, y = p.x * rx * GROW * PX * k, p.y * ry * GROW * PX * k
        xr, yr = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        # partly buried: the centre sits below the ground, so the rock rises steeply from it
        v.co = Vector((X(col) + xr, Y(row) + yr, (z * 1.3 - 0.3) * h * k))
    vs = set(verts)
    geom = verts + [e for e in bm.edges if e.verts[0] in vs] + [f for f in bm.faces if f.verts[0] in vs]
    cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0.0), plane_no=(0, 0, 1), clear_inner=True)
    edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    tag = "nshd39"
    mats = [common.palette_material(sprite, i, tag, metallic=0.0, roughness=0.85) for i in SHADES]
    rng = random.Random(39)
    bm = bmesh.new()
    spans = outline_spans(grid)
    skirt(bm, spans)
    for b in BOULDERS:
        boulder(bm, *b, rng)

    # Colour each face by the sprite pixels under it.
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        cen = f.calc_center_median()
        c, r = to_px(cen.x, cen.y)
        lvl = shade_at(grid, c, r)
        if lvl is None:
            lvl = 4
        if f.normal.z < -0.5:  # underside, never seen
            lvl = 4
        idx = min(max(int(round(lvl)), SHADES[0]), SHADES[-1])
        f.material_index = SHADES.index(idx)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return common.mesh_object(NAME, bm, mats, coll, smooth=False)


def merged_sprite():
    """newshd-39's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshd-39")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(sprite, grid, out):
    """The whole heap's sprite as one image (48 x 56, the 24:28 shape render_preview expects)."""
    import numpy as np
    img = np.zeros((H, W, 4), dtype=np.float32)
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if v >= 0:
                img[r, c] = [*(ch / 255 for ch in sprite["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    grid = load_grid()
    obj = build(sprite, grid)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(sprite, grid, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
