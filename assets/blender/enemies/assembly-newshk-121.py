"""WARNING sign (newshk.shp frames 121 and 123, assembly of 2 pieces): a 3D version of its sprites.

Seen in episode 3 (level 3.12) and 4 (4.4). Two 2x2 enemies side by side make a green neon
sign, 36 x 22 px: the word WARNING in glowing green strokes on a dark panel, underlined, with the
underline turning up the right side into a bracket and on up and left into an arrow pointing up.

Built whole in assembly coordinates: the dark panel behind the word, each letter as straight
neon tubes, the underline/bracket/arrow as one more run of tubes and a brighter pulse on the
underline; then cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshk-121.py [-- --preview out.png]
(the preview is the whole sign; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b032 as lib  # noqa: E402

common = lib.common
NAME = "assembly-newshk-121"
ROOT = common.repo_root(__file__)
PIECES = [("newshk-121", 0), ("newshk-123", 24)]  # name, first assembly column
W, H = 48, 28  # assembly size in px; its centre (column edge 24, row edge 14) is the origin

R_TUBE = 0.8  # tube half width in px
Z_TUBE = 0.03  # tube centre height

# Strokes as runs of pixel centres (column, row) in assembly px.
LETTERS = [
    # W
    [(2, 13), (2, 19), (6, 19), (6, 13)], [(4, 19), (4, 15)],
    # A
    [(8, 19), (8, 13), (10, 13), (10, 19)], [(8, 16), (10, 16)],
    # R
    [(12, 19), (12, 13), (13.3, 13), (14, 13.7), (14, 19)], [(12, 16), (14, 16)],
    # N
    [(16, 19), (16, 13), (18.7, 15.9)], [(19, 13), (19, 19)],
    # I
    [(22, 13), (22, 19)], [(21, 13), (23, 13)], [(21, 19), (23, 19)],
    # N
    [(25, 19), (25, 13), (27.7, 15.9)], [(28, 13), (28, 19)],
    # G
    [(32.6, 13), (31, 13), (30, 14), (30, 18), (31, 19), (32.4, 19), (33, 18.4), (33, 16), (31.8, 16)],
]
# Underline, up the bracket, back up-left and up to the arrow's tip; then the arrowhead.
ARROW = [(2, 21), (33, 21), (35, 19), (35, 13), (34, 12), (33, 11), (30, 11), (25, 6), (25, 1.6)]
HEAD = [(20, 6), (25, 1), (30, 6)]


def X(c):
    return lib.X(c, W)


def Y(r):
    return lib.Y(r, H)


def stroke(bm, pts, mat, r=R_TUBE, z=Z_TUBE, hh=0.06):
    """Straight tubes between consecutive points, each overrunning its ends by its radius so the
    corners close."""
    for (c0, r0), (c1, r1) in zip(pts, pts[1:]):
        a, b = Vector((X(c0), Y(r0), z)), Vector((X(c1), Y(r1), z))
        d = (b - a).normalized() * (r * lib.PX * 0.9)
        a, b = a - d, b + d
        lib.sweep(bm, [(*a, r * lib.PX, hh), (*b, r * lib.PX, hh)], sides=6, mat=mat, smooth=False)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshk121"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(32, metallic=0.4, roughness=0.5),  # 0 dark panel
        pal(199, roughness=0.3, emission_strength=3.0),  # 1 green letters
        pal(197, roughness=0.3, emission_strength=2.5),  # 2 darker green underline and arrow
        pal(201, roughness=0.3, emission_strength=3.5),  # 3 bright arrowhead
        pal(203, roughness=0.3, emission_strength=5.0),  # 4 the pulse running along the underline
        pal(193, metallic=0.3, roughness=0.5),  # 5 deep green panel rim
    ]
    PANEL, LETTER, LINE, HEADM, PULSE, RIMM = range(6)
    bm = bmesh.new()

    # The dark panel behind the word (columns 1-35, rows 12-22) with a deep green lip.
    ex = lambda c: (c - W / 2) / 12  # noqa: E731  column edge to X
    ey = lambda r: (H / 2 - r) / 12  # noqa: E731  row edge to Y
    lib.bevel_plate(bm, [(ex(1), ey(12)), (ex(36), ey(12)), (ex(36), ey(23)), (ex(1), ey(23))],
                    -0.07, 0.0, 0.03, mat=RIMM, top_mat=PANEL)

    for pts in LETTERS:
        stroke(bm, pts, LETTER)
    stroke(bm, ARROW, LINE)
    stroke(bm, HEAD, HEADM)
    stroke(bm, [(7, 21), (11, 21)], PULSE, r=0.9, hh=0.066)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, [n for n, _ in PIECES])
    obj = build(sprite)
    layout = [(name, off + 12 - W / 2, 0) for name, off in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name, _ in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.composite_png(ROOT, layout, 48, 56, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=4, view_px=480)
        for name, _ in PIECES:
            lib.preview([pieces[name]], ROOT, name, common.load_sprite(ROOT, name),
                        out=out.parent / f"{name}.png")


if __name__ == "__main__":
    main()
