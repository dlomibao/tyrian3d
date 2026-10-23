"""Boulder heap with a buried red-eyed machine (newshr.shp, an assembly of 16 pieces): a 3D
version of its sprites.

Seen in episode 3 (level 3.4). Sixteen 2x2 ground enemies in a 4x4 block (sheet order: frames
159-165, 197-203, 235-241, 273-279) make one 96x112 px heap: rough brown, golden and grey
boulders piled high on the right and over the top, and on the left, sticking out of the rubble,
a dark machine: a radiator grille under the rocks, a big glowing red orb in a grey ring, two red
lenses below it, and a stack of red-lit coils with pipes running off to the left. The machine's
left side is cut straight (it carries on in the neighbouring sprites).

The whole heap is built once in assembly coordinates and cut into its pieces with
common.split_assembly. Each boulder is a faceted mound: its footprint follows one rock of the
sprite (the seed list below names one point on each rock; the pixels are shared out between the
seeds along the dark crevices), it rises higher the further it sits inside the heap, its peak
leans toward the rock's highlight, and its facets take the rock's palette colours (the facets
facing the way the sprite lights it take the lighter one).

Run: blender --background --python assets/blender/enemies/assembly-newshr-273.py [-- --preview out.png]
(the preview is the whole heap; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b117 as lib  # noqa: E402

NAME = "assembly-newshr-273"
ROOT = common.repo_root(__file__)
ROWS = [["newshr-159", "newshr-161", "newshr-163", "newshr-165"],
        ["newshr-197", "newshr-199", "newshr-201", "newshr-203"],
        ["newshr-235", "newshr-237", "newshr-239", "newshr-241"],
        ["newshr-273", "newshr-275", "newshr-277", "newshr-279"]]

# The machine's outline in pixel edges (col, row) of the whole 96x112 block.
MACHINE = [(0, 21), (28, 21), (28, 35), (31, 36), (36, 38), (38, 39), (40, 41), (41, 44), (41, 48),
           (39, 51), (40, 53), (39, 54), (38, 56), (36, 56), (36, 68), (35, 68), (34, 69), (34, 72),
           (33, 72), (33, 75), (30, 75), (30, 86), (15, 86), (15, 87), (10, 87), (10, 82), (7, 82), (7, 86), (0, 86), (0, 71),
           (2, 70), (3, 69), (4, 68), (5, 67), (5, 57), (6, 56), (7, 55), (8, 54), (10, 53), (10, 44),
           (9, 42), (8, 41), (7, 39), (6, 38), (5, 37), (3, 36), (0, 36)]

# One point (col, row) on each boulder, top of the heap to the bottom.
SEEDS = [
    # rubble over the machine
    (4, 10), (13, 9), (5, 16), (15, 16), (24, 17), (27, 12),
    # top of the heap
    (40, 9), (50, 8), (48, 15),
    # middle
    (32, 23), (39, 26), (49, 22), (59, 25), (67, 23), (77, 30), (66, 33), (54, 33), (40, 35),
    (43, 44), (50, 41), (64, 45), (75, 46), (77, 39),
    # lower
    (47, 57), (69, 64), (74, 56), (79, 53), (39, 56), (38, 65),
    (40, 79), (54, 76), (70, 73), (68, 81), (57, 84),
    # bottom
    (35, 89), (46, 89), (38, 96), (52, 98), (59, 88), (70, 87),
]


def build(g, sprite):
    coll = common.reset_collection(NAME)
    tag = "nshr273"
    mats, slots = [], {}

    def slot(index, **kw):
        key = (index, kw.get("emission_strength", 0.0))
        if key not in slots:
            fam = lib.family(index)
            if fam == "grey":
                kw.setdefault("metallic", 0.15)
                kw.setdefault("roughness", 0.75)
            elif fam in ("brown", "gold"):
                kw.setdefault("metallic", 0.0)
                kw.setdefault("roughness", 0.9)
            name = tag if not kw.get("emission_strength") else f"{tag}e"
            mats.append(common.palette_material(sprite, index, name, **kw))
            slots[key] = len(mats) - 1
        return slots[key]

    bm = bmesh.new()

    # ---- the machine ----
    def mslot(i, **kw):
        kw.setdefault("metallic", 0.6)
        kw.setdefault("roughness", 0.4)
        return slot(i, **kw)

    BASE, DARKG, MID, LIGHT, RIM, BRIGHT = mslot(2), mslot(3), mslot(5), mslot(7), mslot(9), mslot(11)
    lib.plate(bm, g, MACHINE, 0.0, 0.28, mat=BASE)

    # Radiator grille under the rubble (columns 0-19, rows 21-37): dark vents, four upright ribs.
    lib.box(bm, g, 0, 21, 19, 27, 0.0, 0.36, mat=BASE)
    lib.box(bm, g, 0, 27, 19, 37, 0.0, 0.38, mat=DARKG)
    for c in (1, 5, 9, 13, 17):
        lib.cyl_y(bm, g, c, 21.2, 36.6, 0.38, 1.1, rz=0.07, mat=LIGHT if c > 1 else MID, sides=6)
    # Grey block right of the grille with a bright bar across it (columns 19-28).
    lib.box(bm, g, 19, 21.5, 28, 37, 0.0, 0.44, mat=MID)
    lib.box(bm, g, 18.5, 26.5, 24, 28, 0.36, 0.45, mat=BASE)
    lib.cyl_x(bm, g, 19.2, 26.5, 30.5, 0.44, 1.0, rz=0.05, mat=BRIGHT)
    lib.cyl_y(bm, g, 22.5, 31, 36, 0.44, 0.9, rz=0.04, mat=RIM)

    # Housing round the orb: a grey collar on the left and a block on the right.
    lib.plate(bm, g, [(5, 37), (14, 36), (14, 40), (10, 44), (10, 53), (14, 57), (6, 57), (6, 54),
                      (9, 52), (9, 43), (6, 39)], 0.0, 0.40, mat=MID)
    lib.plate(bm, g, [(29, 37), (36, 38), (40, 41), (41, 44), (41, 48), (39, 51), (39, 54),
                      (36, 57), (31, 57), (33, 50), (32, 42)], 0.0, 0.46, mat=MID)
    lib.cyl_y(bm, g, 33.6, 44, 56, 0.46, 0.9, rz=0.04, mat=BRIGHT)
    lib.box(bm, g, 37, 42, 40.5, 47, 0.3, 0.5, mat=DARKG)

    # The big red orb (columns 12-32, rows 39-55) in its grey ring, with two hot highlights.
    ORB = slot(116, emission_strength=3.0)
    lib.torus(bm, g, 22, 47.2, 0.36, 10.4, 8.6, 1.5, 0.09, mat=RIM, segments=28, sides=6)
    lib.ellipsoid(bm, g, 22, 47.2, 0.30, 10.0, 8.2, 0.44, mat=ORB, segments=20, rings=10, half=True)
    lib.ellipsoid(bm, g, 18.0, 44.6, 0.67, 2.6, 2.0, 0.07, mat=slot(126, emission_strength=5.0), segments=10, rings=5)
    lib.ellipsoid(bm, g, 28.3, 49.6, 0.60, 2.4, 1.8, 0.07, mat=slot(122, emission_strength=4.0), segments=10, rings=5)

    # Grey works under the orb (rows 56-67) and two red lenses in it.
    lib.box(bm, g, 5, 56, 35, 67, 0.0, 0.38, mat=MID)
    LENS = slot(115, emission_strength=2.5)
    lib.ellipsoid(bm, g, 19.0, 63.5, 0.38, 2.2, 2.7, 0.09, mat=LENS, segments=12, rings=6, half=True)
    lib.ellipsoid(bm, g, 25.5, 63.2, 0.38, 3.3, 3.4, 0.11, mat=LENS, segments=12, rings=6, half=True)

    # Stack of red-lit coils down the middle (columns 17-26, rows 67-83) with bright bands.
    lib.cyl_y(bm, g, 21.5, 67, 83.5, 0.30, 3.6, rz=0.12, mat=DARKG, sides=10)
    COIL = slot(115, emission_strength=3.0)
    for r0, r1 in ((68.8, 73.8), (76.8, 78.8), (79.8, 81.8)):
        lib.cyl_y(bm, g, 21.5, r0, r1, 0.31, 3.9, rz=0.14, mat=COIL, sides=10)
    for r in (68.0, 70.2):
        lib.cyl_x(bm, g, 14, 26.5, r, 0.42, 0.6, rz=0.04, mat=RIM, sides=6)

    # Pipes off to the left (rows 67, 70, 73) and one down the right side (column 29).
    lib.cyl_x(bm, g, 0, 10, 67.2, 0.30, 1.0, mat=MID)
    lib.cyl_x(bm, g, 2, 14, 70.2, 0.30, 1.0, mat=MID)
    lib.cyl_x(bm, g, 0, 18, 73.2, 0.30, 1.0, mat=DARKG)
    lib.cyl_y(bm, g, 29, 56, 86, 0.30, 1.2, mat=DARKG)
    lib.box(bm, g, 9, 74, 30, 86, 0.0, 0.33, mat=DARKG)

    # ---- the boulders ----
    def keep(c, r):
        return not lib.inside(MACHINE, c + 0.5, r + 0.5)

    regions = lib.segment(g, SEEDS, keep)
    dist = lib.distance_in(g, lambda c, r: True)
    for i, region in enumerate(regions):
        if len(region) < 4:
            continue
        cx = sum(c for c, _ in region) / len(region)
        cy = sum(r for _, r in region) / len(region)
        d = dist[int(round(cy))][int(round(cx))]
        base = min(0.6, 0.022 * max(d - 2, 0))
        height = 0.03 * len(region) ** 0.5
        lib.boulder(bm, g, region, slot, base, height, n=9, seed=i)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    g = lib.Grid(ROOT, ROWS)
    sprite = g.merged_sprite()
    obj = build(g, sprite)
    pieces = common.split_assembly(obj, g.layout())
    for name, piece in pieces.items():
        common.export_sprite_model(ROOT, [piece], f"enemies/{name}", g.sprites[name]["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref, size = g.composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=size, view_px=640)
        for name, piece in pieces.items():
            img = ROOT / "reference" / "models" / name / g.sprites[name]["frames"][0]["image"]
            common.render_preview([piece], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
