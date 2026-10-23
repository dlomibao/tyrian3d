"""Bronze drill missile (newshh.shp, assembly of newshh-17 and newshh-55): a 3D version of its sprites.

Seen in episode 2 (level 2.4). Two 2x2 enemies stacked make one 24x56 px object: a faceted
bronze shell lying along the screen, nose up. The nose (newshh-17) is a long cone; the body
(newshh-55) is three overlapping skirts that widen towards the back, each with a chevron rim,
and a rounded knob near the blunt tail. The sprite lights it from the left, with a sharp ridge
down the middle (light left of it, dark right of it), so the shell is a 12-sided faceted loft
with an edge on top.

Built once in assembly coordinates (24x56 px, centre at the origin) and cut into the two pieces
with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshh-55.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b057 as lib  # noqa: E402

NAME = "assembly-newshh-55"
ROOT = common.repo_root(__file__)
PIECES = ["newshh-55", "newshh-17"]
CX0, CY0 = 143, -4  # screen centre of the 24x56 assembly (newshh-17 above newshh-55)
G = lib.Grid(24, 56)
AXIS = 12  # the shell's centre column (its ridge)
FLAT = 0.42  # half height / half width of the shell's section


def tier(bm, sections, mat, lip_mat):
    """One skirt of the shell: sections (row, half_w px, sweep px); the last is its rim, closed by
    an inward lip in a lighter bronze."""
    secs = [(r, w, FLAT * w / 12, 0.0, s) for r, w, s in sections]
    r, w, s = sections[-1]
    secs[-1] = (r, w, FLAT * w / 12 * 1.18, 0.0, s)  # the rim stands proud of the next skirt
    lib.loft(bm, G, AXIS, secs, sides=12, mat=mat, smooth=False, phase=0.0, cap_end=False)
    # A light band along the rim's edge, then an inward lip.
    lib.loft(bm, G, AXIS, [(r - 0.6, w * 0.99, FLAT * w / 12 * 1.2, 0.0, s), (r + 0.1, w * 1.01, FLAT * w / 12 * 1.2, 0.0, s),
                           (r + 0.5, w * 0.6, FLAT * w * 0.6 / 12, 0.0, s)],
             sides=12, mat=lip_mat, smooth=False, phase=0.0, cap_start=False)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshh55", **kw)  # noqa: E731
    mats = [
        pal(24, metallic=0.6, roughness=0.35),  # 0 bronze shell
        pal(22, metallic=0.6, roughness=0.4),  # 1 darker bronze skirts
        pal(26, metallic=0.65, roughness=0.3),  # 2 light rims
        pal(27, metallic=0.7, roughness=0.25),  # 3 bright knob
        pal(19, metallic=0.5, roughness=0.5),  # 4 dark tail
    ]
    SHELL, SKIRT, RIM, KNOB, TAIL = range(5)
    bm = bmesh.new()

    # Nose (newshh-17): a long cone from its tip at row 14 out to the first rim.
    tier(bm, [(13.7, 0.0, 0.0), (14.6, 0.6, 0.0), (16.5, 1.2, 0.0), (18.5, 2.0, 0.0), (21.0, 2.8, 0.0),
              (23.0, 3.5, 0.0), (26.0, 4.4, 0.0), (29.5, 4.6, 0.0), (31.0, 4.8, 3.6)], SHELL, RIM)
    # Second skirt: comes out from under the nose's rim and widens to 6.5 px by row 37.
    tier(bm, [(29.0, 3.4, 0.0), (31.5, 4.4, 0.0), (33.0, 5.3, 1.0), (35.0, 6.1, 2.6), (37.0, 6.6, 4.4)],
         SKIRT, RIM)
    # Third skirt: widens to 8.5 px with its rim at row 42.
    tier(bm, [(35.5, 5.0, 0.0), (37.5, 6.3, 0.0), (39.5, 7.4, 2.0), (41.0, 8.3, 3.6), (42.0, 8.6, 4.2)],
         SHELL, RIM)
    # Tail section: full width to row 50, then a blunt rounded end.
    secs = [(40.5, 7.0, 0.0), (43.0, 8.4, 0.0), (46.0, 8.6, 0.0), (50.0, 8.6, 0.0), (50.8, 7.2, 0.0),
            (51.5, 5.6, 0.0), (52.4, 4.5, 0.0), (53.3, 3.2, 0.0), (53.9, 1.6, 0.0), (54.1, 0.0, 0.0)]
    lib.loft(bm, G, AXIS, [(r, w, FLAT * w / 12, 0.0, s) for r, w, s in secs], sides=12, mat=SKIRT,
             smooth=False, phase=0.0)
    # Dark band round the tail where it narrows (rows 50-51).
    lib.loft(bm, G, AXIS, [(50.2, 8.0, FLAT * 8.0 / 12 + 0.01, 0.0), (51.2, 6.3, FLAT * 6.3 / 12 + 0.01, 0.0)],
             sides=12, mat=TAIL, smooth=False, phase=0.0)
    # Bright knob on the tail section (rows 46-50, just left of the ridge).
    lib.ellipsoid(bm, G, 11.8, 48.0, FLAT * 8.6 / 12 - 0.06, 2.9, 2.9, 0.09, mat=KNOB, segments=14, rings=7)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        lib.assembly_previews(ROOT, obj, pieces, layout, 4, out)


if __name__ == "__main__":
    main()
