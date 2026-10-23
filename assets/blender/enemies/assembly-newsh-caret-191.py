"""Red dome emplacement in the wall (newsh^.shp frames 153, 155, 191, 193, a 2x2 assembly):
a 3D version of its sprites.

Seen in episode 4 (level 4.14). Four 2x2 enemies make one 48x56 px structure set into the dark
brick wall (sprite.json `assemblyLayout`): a red ball dome under a grey arch that hoods its top,
on a red neck with a collar below it, and either side a grey ring lying on the wall around a red
pylon, its top slanting up to the ring's outer side and a rounded red cap below it, with small
grey brackets reaching in towards the neck. Every piece has one frame and fills its tile, so the
wall's floor and bricks are part of the model.

The whole structure is built once in assembly coordinates (left half, mirrored about the centre
of pixel column 24, the sprite's axis), then cut into the four pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh-caret-191.py [-- --preview out.png]
(the preview is the whole structure; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from lib_b139 import (Grid, sweep, loft_y, plate, ellipsoid, dome, floor_bricks, mirror_all,  # noqa: E402
                      to_object, merged_sprite, composite_png, ring, disc)

NAME = "assembly-newsh-caret-191"
ROOT = common.repo_root(__file__)
# Pieces by place: 153 top left, 155 top right, 191 bottom left, 193 bottom right. The layout's
# centre (screen 44, -4) is the Blender origin and assembly pixel (0, 0) is 153's top-left corner.
PIECES = ["newsh-caret-153", "newsh-caret-155", "newsh-caret-191", "newsh-caret-193"]
LAYOUT = [("newsh-caret-153", -12, -14), ("newsh-caret-155", 12, -14),
          ("newsh-caret-191", -12, 14), ("newsh-caret-193", 12, 14)]
G = Grid(48, 56)
AXIS_COL = 24

# Left ring around the pylon: centre (column, row) and radii of its middle line in px.
RING = (9.5, 35.2, 6.0, 7.6)


def composite_pixels():
    """The four pieces' pixels as one 48 x 56 grid."""
    px = {n: common.load_sprite(ROOT, n)["frames"][0]["pixels"] for n in PIECES}
    top = [px["newsh-caret-153"][r] + px["newsh-caret-155"][r] for r in range(28)]
    bottom = [px["newsh-caret-191"][r] + px["newsh-caret-193"][r] for r in range(28)]
    return top + bottom


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshc191"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(2, metallic=0.1, roughness=0.9),  # 0 floor
        pal(3, metallic=0.2, roughness=0.8),  # 1 dark bricks
        pal(5, metallic=0.4, roughness=0.6),  # 2 light bricks
        pal(4, metallic=0.3, roughness=0.7),  # 3 dark housing floor inside the rings and arch
        pal(6, metallic=0.6, roughness=0.4),  # 4 grey arch and rings
        pal(9, metallic=0.75, roughness=0.25),  # 5 bright grey highlights
        pal(72, metallic=0.35, roughness=0.4),  # 6 red
        pal(73, metallic=0.35, roughness=0.35),  # 7 light red rims
        pal(71, metallic=0.3, roughness=0.45),  # 8 darker red neck
        pal(76, metallic=0.3, roughness=0.3),  # 9 red highlight
        pal(7, metallic=0.6, roughness=0.35),  # 10 light grey brackets
    ]
    FLOOR, DARK, LIGHT, HOUSING, GREY, BRIGHT, RED, RIM, NECK, SHINE, BRACKET = range(11)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----

    # Grey ring lying on the wall (columns 3-16, rows 27-43) over a dark housing floor.
    rc, rr, rx, ry = RING
    disc(bm, G, rc, rr, rx + 0.5, ry + 0.5, 0.0, 0.05, mat=HOUSING)
    ring(bm, G, rc, rr, rx, ry, 0.09, 1.7, 0.09, steps=28, sides=8, mat=GREY)
    # Bright glint on its top-left (column 8, rows 27-28).
    ring(bm, G, rc, rr, rx - 0.4, ry - 0.4, 0.175, 0.5, 0.02, a0=100, a1=130, steps=4, sides=6, mat=BRIGHT)

    # Red pylon in the ring (columns 10-14, rows 28-39): a block whose top slants up to its outer
    # corner, light red round its edge with a red panel on top.
    outline = [(10, 28.0), (11, 28.0), (15, 33.0), (15, 40), (10, 40)]
    plate(bm, G, outline, 0.0, 0.3, mat=RIM)
    inner = [(10.8, 29.6), (11.0, 29.6), (14.2, 33.6), (14.2, 39.2), (10.8, 39.2)]
    plate(bm, G, inner, 0.3, 0.315, mat=RED)
    # Rounded cap below it (columns 10-15, rows 41-44), a half cylinder lying across.
    sweep(bm, G, [(9.6, 42.6, 0.05, 0.0, 0.0), (9.9, 42.6, 0.05, 2.0, 0.15), (10.5, 42.6, 0.05, 2.3, 0.19),
                  (15.0, 42.6, 0.05, 2.3, 0.19), (15.8, 42.6, 0.05, 1.7, 0.13), (16.2, 42.6, 0.05, 0.0, 0.0)],
          sides=10, mat=RED)
    ellipsoid(bm, G, 11.3, 41.8, 0.19, 1.4, 0.8, 0.03, mat=SHINE, segments=8, rings=4)

    # Grey arm from the top of the ring in towards the bottom of the neck (columns 11-21,
    # rows 29-35), lighter where it meets the centre.
    sweep(bm, G, [(11.5, 30.0, 0.1, 1.4, 0.07), (15.0, 30.8, 0.1, 1.4, 0.07), (17.5, 32.6, 0.08, 1.3, 0.065),
                  (19.5, 34.0, 0.07, 1.2, 0.06), (20.5, 34.2, 0.07, 0.0, 0.0)], sides=8, mat=GREY)
    plate(bm, G, [(18, 33.6), (22, 33.6), (22, 35.2), (18, 35.2)], 0.0, 0.1, mat=BRACKET)

    # Dark floor under the arch, round the dome.
    disc(bm, G, 21.0, 17.5, 3.5, 4.5, 0.0, 0.05, mat=HOUSING)

    mirror_all(bm, G.X(AXIS_COL))

    # ---- centre parts ----

    # Grey arch hooding the dome (columns 14-34, rows 9-20): a half ring over the top whose ends
    # curl in beside the dome, with a bright edge along its outer top-left.
    def taper(t, full, end):
        e = min(t, 1 - t) / 0.18
        return end + (full - end) * min(e, 1.0) ** 0.6

    ring(bm, G, AXIS_COL, 17.2, 7.7, 5.6, 0.1, lambda t: taper(t, 3.1, 0.9), lambda t: taper(t, 0.14, 0.06),
         a0=-24, a1=204, steps=28, sides=10, mat=GREY)
    ring(bm, G, AXIS_COL, 17.2, 9.6, 7.6, 0.19, 0.5, 0.025, a0=100, a1=165, steps=8, sides=6, mat=BRIGHT)

    # The red ball dome (columns 20-28, rows 14-22) with a highlight near its top.
    dome(bm, G, AXIS_COL, 18.0, 0.04, 4.7, 4.6, 0.42, mat=RED, segments=18, rings=8)
    ellipsoid(bm, G, 23.8, 17.4, 0.4, 1.6, 1.4, 0.045, mat=SHINE, segments=8, rings=4)

    # Neck below it (columns 21-27, rows 22-27) and the collar (rows 27-30), a short cylinder
    # lying across.
    loft_y(bm, G, AXIS_COL, [(21.0, 2.6, 0.12, 0.08), (23.0, 2.6, 0.12, 0.08), (25.0, 3.3, 0.13, 0.08),
                             (27.5, 3.4, 0.13, 0.08)], sides=10, mat=NECK)
    sweep(bm, G, [(20.6, 28.8, 0.08, 0.0, 0.0), (20.8, 28.8, 0.08, 1.6, 0.13), (21.2, 28.8, 0.08, 2.0, 0.17),
                  (26.8, 28.8, 0.08, 2.0, 0.17), (27.2, 28.8, 0.08, 1.6, 0.13), (27.4, 28.8, 0.08, 0.0, 0.0)],
          sides=10, mat=RIM)

    floor_bricks(bm, G, composite_pixels(), FLOOR, DARK, LIGHT)
    return to_object(NAME, bm, mats, coll)


def main():
    sprite = merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    pieces = common.split_assembly(obj, LAYOUT)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(ROOT, LAYOUT, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
