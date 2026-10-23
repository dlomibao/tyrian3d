"""Brain creature's underside (newsh5.shp frames 272, 274, 276: an assembly of three pieces): a 3D
version of its sprites.

Seen in episode 4 (level 22), under a brain made of other pieces. Three 2x2 enemies side by side
make one 72x28 px object: a dark, lumpy red mass across the top that narrows downwards, two
glossy blue eye lobes in the middle of its lower edge, and dark red tendrils hanging below: a
strut and a strand down each side into two loops that meet in a braided stem under the eyes.

The mass is a low lump whose outline follows the sprite row by row, with rounded folds fitted to
its highlights; the eyes are big blue domes coloured from the sprite; the tendrils are tubes. The
lower parts are mirror symmetric about pixel column 36. Built whole in assembly coordinates and
cut into the three pieces with common.split_assembly. One frame each.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-272.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b029 as lib  # noqa: E402

NAME = "assembly-newsh5-272"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-272", "newsh5-274", "newsh5-276"]
AXIS = 36  # the lower parts are mirror symmetric about the centre of this column
PX = lib.PX


def build(colors, pixels, grid):
    coll = common.reset_collection(NAME)
    sprite = {"name": NAME, "colors": colors}
    pal = lambda i, **kw: common.palette_material(sprite, i, "ns5b272", **kw)  # noqa: E731
    mats = [
        pal(64, metallic=0.0, roughness=0.85),  # 0 darkest underside
        pal(66, metallic=0.05, roughness=0.7),  # 1 dark mass
        pal(68, metallic=0.1, roughness=0.55),  # 2 folds
        pal(70, metallic=0.1, roughness=0.45),  # 3 light folds, tendrils
        pal(72, metallic=0.1, roughness=0.4),  # 4 highlights
        pal(50, metallic=0.3, roughness=0.2),  # 5 dark blue eye
        pal(53, metallic=0.3, roughness=0.15),  # 6 blue eye
        pal(56, metallic=0.3, roughness=0.12),  # 7 light blue eye
        pal(58, metallic=0.3, roughness=0.1, emission_strength=1.5),  # 8 eye shine
        pal(68, metallic=0.1, roughness=0.5),  # 9 tendrils (dark red)
    ]
    DARKEST, DARK, FOLD, LIGHT, HIGH, EYE_D, EYE, EYE_L, SHINE, TENDRIL = range(10)

    def red(i):
        if not 64 <= i <= 79:
            return None
        return min((i - 63) // 2, 4)

    def blue(i):
        if 48 <= i <= 51:
            return EYE_D
        if 52 <= i <= 54:
            return EYE
        if 55 <= i <= 57:
            return EYE_L
        if 58 <= i <= 63:
            return SHINE
        return None

    bm = bmesh.new()

    # ---- the mass across the top (rows 0-12) ----
    edges = []
    for r in range(13):
        cols = [c for c, v in enumerate(pixels[r]) if v >= 0]
        edges.append((min(cols), max(cols) + 1))
    sm = []
    for r in range(13):
        a, b = edges[max(r - 1, 0)], edges[min(r + 1, 12)]
        sm.append(((a[0] + 2 * edges[r][0] + b[0]) / 4, (a[1] + 2 * edges[r][1] + b[1]) / 4))

    def heights(r):
        t = min(max((r - 4) / 8, 0.0), 1.0)
        return 0.22 - 0.13 * t, 0.12 - 0.04 * t

    spans = [(0.0, sm[0][0], sm[0][1], *(h * 0.7 for h in heights(0)))]
    for r in range(13):
        spans.append((r + 0.5, sm[r][0], sm[r][1], *heights(r)))
    spans.append((13.0, sm[12][0] + 1.5, sm[12][1] - 1.5, 0.05, 0.05))
    body = lib.Body(grid, spans, power=0.9)
    n0 = len(bm.faces)
    body.build(bm, mat=DARK, sides=40)
    bm.faces.ensure_lookup_table()
    lib.paint(bm, pixels, grid, red, faces=bm.faces[n0:])

    n = lib.lumps(bm, pixels, grid, body, red, inside=lambda c, r: r <= 8, min_level=67, sink=0.5,
                  height=0.035, height_per_level=0.006, segments=10, rings=5, radius=3, window=2,
                  spread=2, stretch=2.6, min_axis=1.8, max_axis=4.5)
    print(f"{n} folds")

    # ---- left half of the lower parts (mirrored below) ----
    start = len(bm.verts)
    X, Y = grid.X, grid.Y

    def tube(points, half_w, half_h, mat, n=10, closed=False):
        curve = lib.catmull([(X(c), Y(r), z) for c, r, z in points], n, closed=closed)
        sec = [(p.x, p.y, p.z, half_w * PX, half_h) for p in curve]
        if not closed:
            sec[0] = (*sec[0][:3], half_w * PX * 0.7, half_h * 0.7)
        lib.sweep(bm, sec, sides=6, mat=mat, closed=closed)

    # Eye lobe (columns 28-35, rows 8-17): a big glossy dome, coloured from the sprite.
    n0 = len(bm.faces)
    lib.ellipsoid(bm, (X(31.7), Y(12.2), 0.04), (4.8 * PX, 4.9 * PX, 0.15), mat=EYE, segments=16, rings=8)
    bm.faces.ensure_lookup_table()
    lib.paint(bm, pixels, grid, blue, faces=bm.faces[n0:], under_slot=EYE_D)
    # Strut from the mass down to the loop (columns 11-23, rows 11-21).
    tube([(12.5, 10.5, -0.02), (13.6, 14.0, -0.03), (15.6, 17.0, -0.03), (18.0, 19.0, -0.03),
          (21.5, 19.6, -0.03), (24.6, 21.0, -0.03)], 1.3, 0.055, TENDRIL, n=10)
    # Thin strand straight down (column 20, rows 11-19).
    tube([(20.0, 10.5, -0.02), (20.0, 14.0, -0.03), (20.3, 17.0, -0.03), (21.5, 19.3, -0.03)], 1.1, 0.05,
         TENDRIL, n=6)
    # The loop (columns 24-35, rows 15-26): its inner side is the braided stem under the eye.
    ring = []
    for k in range(14):
        a = 2 * math.pi * k / 14
        c = 29.6 + 4.6 * math.cos(a)
        r = 20.3 + 4.8 * math.sin(a)
        ring.append((c, r, -0.04))
    tube(ring, 1.25, 0.055, LIGHT, n=20, closed=True)
    # Stem strand from the eye down to the loop's bottom, crossing its twin.
    tube([(34.0, 15.0, 0.0), (35.0, 18.5, -0.03), (36.6, 21.5, -0.04), (35.6, 24.0, -0.04), (33.6, 25.0, -0.04)],
         1.1, 0.05, TENDRIL, n=8)

    lib.mirror_since(bm, start, X(AXIS))
    # Colour both eyes from the sprite (the mirrored one copied the left's colours).
    eye_faces = [f for f in bm.faces if EYE_D <= f.material_index <= SHINE]
    lib.paint(bm, pixels, grid, blue, faces=eye_faces, under_slot=EYE_D)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    pixels, colors, w, h, (sx0, sy0), layout = lib.assembly_pixels(ROOT, PIECES)
    grid = lib.Grid(w, h)
    obj = build(colors, pixels, grid)
    cx0, cy0 = sx0 + w / 2, sy0 + h / 2
    pieces = common.split_assembly(obj, [(n, layout[n][0] - cx0, layout[n][1] - cy0) for n in PIECES])
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.write_png(Path(tempfile.mkdtemp()) / "assembly.png", pixels, colors)
        common.render_preview([obj], str(out), str(ref), size=(w, h), view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
