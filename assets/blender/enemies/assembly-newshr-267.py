"""Rock pile (newshr.shp, assembly of 12 ground pieces): a 3D version of its sprites.

Seen in episode 3 (level 3.4). Twelve 2x2 ground pieces (three columns of four) make one
72 x 104 px heap of boulders: mostly brown rocks lit from above, a few golden ones and three
blue-grey slates, with a tall leaning slab on top. The pieces to its right (newshr-163, -165,
-201, ...) belong to the neighbouring pile, assembly-newshr-273.

The heap is built whole in assembly coordinates: each boulder is grown over its rock in the
sprite (lib_b116.segment, from the seeds below) and raised as a faceted rock whose height follows
how deep in the heap it sits; every facet takes the colour of the sprite pixel of that rock under
it. Then it is cut into the twelve pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshr-267.py [-- --preview out.png]
(the preview is the whole heap; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b116 as lib  # noqa: E402

NAME = "assembly-newshr-267"
ROOT = common.repo_root(__file__)
PIECES = ["newshr-267", "newshr-269", "newshr-271", "newshr-229", "newshr-231", "newshr-233",
          "newshr-191", "newshr-193", "newshr-195", "newshr-153", "newshr-155", "newshr-157"]
# Grid pixel (0, 0) is screen pixel (102, -32), the top-left corner of newshr-153; the grid is
# 72 x 112 px and its centre (screen 138, 24) is the Blender origin.
SX0, SY0, GW, GH = 102, -32, 72, 112
CX0, CY0 = 138, 24

# One entry per rock: seed pixels (col, row) it grows from, and optionally a height boost.
SEEDS = [
    ([(47, 5), (46, 10)], 0.18),   # tall leaning slab, upper end
    ([(47, 21), (49, 26)], 0.22),  # tall slab, its bright lower face
    ([(31, 10), (32, 7), (29, 9)], 0.0),  # golden rock top left, with its brown back
    ([(38, 17)], 0.05),
    ([(20, 21), (16, 19)], 0.0),   # big rock upper left
    ([(28, 31)], 0.0),
    ([(38, 32), (41, 29)], 0.05),  # golden rock in the middle (with the orange glint)
    ([(52, 44)], 0.05),            # pale rock on the right
    ([(8, 35)], 0.0),              # golden rock on the left edge
    ([(15, 47), (22, 45)], 0.04),  # big flat rock left
    ([(33, 44)], 0.08),            # blue-grey slate
    ([(43, 46)], 0.0),
    ([(40, 53)], 0.0),
    ([(45, 60), (50, 62)], 0.06),  # big pale speckled rock
    ([(30, 54)], 0.0),             # small golden rock
    ([(15, 63)], 0.03),            # golden rock lower left
    ([(9, 61)], 0.0),              # small slate
    ([(26, 62)], 0.0),
    ([(16, 55)], 0.0),
    ([(8, 70)], 0.0),
    ([(8, 77)], -0.03),            # dark rock bottom left
    ([(21, 79)], 0.04),            # slate bottom left
    ([(28, 84)], 0.0),
    ([(29, 95)], 0.0),
    ([(40, 74)], 0.0),
    ([(38, 84)], 0.0),
    ([(48, 74)], 0.0),
    ([(47, 90)], 0.02),            # golden rock bottom right
    ([(40, 94)], -0.03),           # dark rock at the bottom
    ([(18, 86)], 0.0),
]
GLINT = (42, 29)  # the orange glint (index 123) on the middle golden rock


def X(c):
    """Grid column (pixel centre; fractions allowed) to Blender X."""
    return (c + 0.5 - GW / 2) / 12


def Y(r):
    """Grid row (pixel centre) to Blender Y: sprite up is +Y."""
    return (GH / 2 - (r + 0.5)) / 12


def to_px(v):
    return v.x * 12 + GW / 2 - 0.5, GH / 2 - 0.5 - v.y * 12


def layout_screen():
    data = common.load_sprite(ROOT, PIECES[0])
    return [(e["model"], e["cx"], e["cy"]) for e in data["assemblyLayout"] if e["model"] in PIECES]


def build():
    coll = common.reset_collection(NAME)
    grid, colors = lib.composite(common.load_sprite, ROOT, layout_screen(), SX0, SY0, GW, GH)
    sprite = {"name": NAME, "colors": colors}
    skip = lib.outer_outline(grid)
    lab = lib.segment(grid, [s for s, _ in SEEDS], skip)
    depth = lib.depth_map(grid, skip)

    mats, slot = [], {}

    def mat_of(index):
        if index not in slot:
            fam, tone = lib.family(index)
            if index == 123:
                m = common.palette_material(sprite, index, NAME, metallic=0.2, roughness=0.3, emission_strength=4.0)
            elif fam == "gold":
                m = common.palette_material(sprite, index, NAME, metallic=0.25, roughness=0.55)
            elif fam == "grey":
                m = common.palette_material(sprite, index, NAME, metallic=0.15, roughness=0.45)
            else:
                m = common.palette_material(sprite, index, NAME, metallic=0.0, roughness=0.85)
            slot[index] = len(mats)
            mats.append(m)
        return slot[index]

    regions = [[] for _ in SEEDS]
    for r in range(GH):
        for c in range(GW):
            if lab[r][c] >= 0:
                regions[lab[r][c]].append((c, r))

    bm = bmesh.new()
    for k, (seeds, boost) in enumerate(SEEDS):
        region = regions[k]
        if not region:
            continue
        coloured = [(c, r, grid[r][c]) for c, r in region if grid[r][c] not in lib.CREVICE] or \
                   [(c, r, grid[r][c]) for c, r in region]

        def colors_at(col, row, coloured=coloured):
            return min(coloured, key=lambda p: (p[0] - col) ** 2 + (p[1] - row) ** 2)[2]

        n = len(region)
        cx = sum(c for c, _ in region) / n
        cy = sum(r for _, r in region) / n
        # The ridge leans toward the rock's highlight (its brightest quarter of pixels).
        tones = sorted(coloured, key=lambda p: -lib.family(p[2])[1])[:max(1, len(coloured) // 4)]
        hx = sum(p[0] for p in tones) / len(tones)
        hy = sum(p[1] for p in tones) / len(tones)
        peak = (cx + (hx - cx) * 0.5, cy + (hy - cy) * 0.5)
        d = depth[int(round(cy))][int(round(cx))]
        z_top = 0.12 + 0.038 * min(d, 16) + 0.012 * math.sqrt(n) + boost
        relief = min(0.22, 0.05 + 0.008 * math.sqrt(n))
        lib.boulder(bm, region, colors_at, (cx, cy), peak, z_top, X, Y, to_px, mat_of, n=16,
                    relief=relief)

    # The orange glint: a small faceted stud on the golden rock.
    gx, gy = GLINT
    gz = max(v.co.z for v in bm.verts if abs(v.co.x - X(gx)) < 0.12 and abs(v.co.y - Y(gy)) < 0.12)
    start = len(bm.verts)
    common.loft(bm, [(Y(gy) + 0.06, 0.0, 0.0, gz), (Y(gy), 0.05, 0.035, gz), (Y(gy) - 0.06, 0.0, 0.0, gz)],
                sides=6, mat_index=mat_of(123))
    common.shift_x(bm, start, X(gx))

    return common.mesh_object(NAME, bm, mats, coll, smooth=False), grid, colors


def composite_png(grid, colors, out):
    """The heap's sprite as one image padded to the 24:28 shape render_preview expects for size 8
    (96 x 112 px, the 72 px wide heap in the middle)."""
    import numpy as np
    img = np.zeros((112, 96, 4), dtype=np.float32)
    for r in range(GH):
        for c in range(GW):
            v = grid[r][c]
            if v >= 0:
                img[r, c + 12] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 96, 112, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    obj, grid, colors = build()
    layout = [(name, cx - CX0, cy - CY0) for name, cx, cy in layout_screen()]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(grid, colors, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=8, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
