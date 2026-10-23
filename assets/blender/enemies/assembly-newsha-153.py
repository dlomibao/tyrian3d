"""Skull crate (newsha.shp, assembly of 8 pieces): a 3D version of its sprites.

A ground object: eight 2x2 enemies side by side (sprite.json `assemblyLayout`) make one wooden
chest, 74 x 38 px. Two planked wooden ends, two grey metal straps (each a top cap, a long middle
and a bottom cap that wraps under), and a framed centre panel with a recessed skull. A grey
carrying handle on two brackets lies back over the chest's far side. The layout also lists
newsha-125 (a loose grey ring above the chest), which is not part of this batch and isn't
exported here.

The whole chest is built once in assembly coordinates, then cut into the pieces with
common.split_assembly. Every piece has a single frame.

Run: blender --background --python assets/blender/enemies/assembly-newsha-153.py [-- --preview out.png]
(the preview is the whole chest; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b132 as lib  # noqa: E402
from lib_b132 import E, F  # noqa: E402

NAME = "assembly-newsha-153"
ROOT = common.repo_root(__file__)
PIECES = ["newsha-153", "newsha-155", "newsha-157", "newsha-159",
          "newsha-191", "newsha-193", "newsha-195", "newsha-197"]
# The pixel map has column 0 at screen x 124 and row 0 at screen y -3 (newsha-153's top-left is
# column 0, row 28). Its pixel edge (48, 56), screen (172, 53), is the Blender origin.
CX0, CY0 = 172, 53
lib.ORIGIN[:] = [48, 56]

TOP = 0.66  # top of the wooden planks


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsha153"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(26, metallic=0.0, roughness=0.8),  # 0 wood planks
        pal(21, metallic=0.0, roughness=0.9),  # 1 dark wood between planks
        pal(11, metallic=0.75, roughness=0.3),  # 2 strap middle
        pal(13, metallic=0.75, roughness=0.25),  # 3 strap caps
        pal(10, metallic=0.75, roughness=0.35),  # 4 strap bottom caps
        pal(18, metallic=0.0, roughness=0.85),  # 5 dark recess and the skull
        pal(24, metallic=0.0, roughness=0.8),  # 6 frame, left side
        pal(27, metallic=0.0, roughness=0.75),  # 7 frame, lit right and bottom
        pal(22, metallic=0.0, roughness=0.85),  # 8 panel behind the skull
        pal(25, metallic=0.0, roughness=0.8),  # 9 teeth and eye sockets
        pal(6, metallic=0.8, roughness=0.3),  # 10 handle
        pal(9, metallic=0.8, roughness=0.3),  # 11 handle brackets
        pal(14, metallic=0.85, roughness=0.2),  # 12 bracket caps
        pal(4, metallic=0.6, roughness=0.5),  # 13 dark metal under the straps
        pal(20, metallic=0.0, roughness=0.9),  # 14 shaded top of the centre
    ]
    (WOOD, GROOVE, STRAP, CAP, BOTCAP, DARK, FRAME_L, FRAME_LIT, PANEL, TOOTH, HANDLE, BRACKET,
     BCAP, UNDER, SHADE) = range(15)
    bm = bmesh.new()
    bev = 0.03

    # Wooden ends (columns 13-23 and 72-83): dark core with planks across, gaps between them.
    for c0, c1, planks in ((13, 24, [(47, 54), (55, 61), (62, 69), (70, 75), (76, 82)]),
                           (72, 84, [(47, 51), (52, 60), (61, 68), (69, 75), (76, 82)])):
        lib.box(bm, c0 + 0.3, 47.3, c1 - 0.3, 81.7, 0.0, TOP - 0.06, mat=GROOVE)
        for r0, r1 in planks:
            lib.box(bm, c0, r0, c1, r1, 0.0, TOP, mat=WOOD, bevel=bev)

    # Metal straps (columns 25-33 and 62-70): top cap, middle, bottom cap that wraps under.
    for c0 in (25, 62):
        c1 = c0 + 9
        lib.box(bm, c0 + 0.3, 46.3, c1 - 0.3, 82.7, 0.0, TOP, mat=UNDER)
        lib.strap(bm, c0, c1, 46, 51, 0.0, 0.79, mat=CAP)
        lib.strap(bm, c0, c1, 52, 74, 0.0, 0.75, mat=STRAP)
        lib.strap(bm, c0, c1, 75, 83, 0.0, 0.77, mat=BOTCAP)

    # A dark core under everything, showing in the 1 px gaps between the parts.
    lib.box(bm, 13.5, 47.5, 83.5, 81.5, 0.0, 0.5, mat=GROOVE)

    # Centre (columns 35-60): a dark core, a raised frame round a recessed panel.
    lib.box(bm, 35, 47, 61, 82, 0.0, 0.62, mat=DARK)
    lib.box(bm, 35, 47, 39, 81, 0.0, 0.72, mat=FRAME_L, bevel=bev)
    lib.box(bm, 58, 47, 61, 81, 0.0, 0.72, mat=FRAME_LIT, bevel=bev)
    lib.box(bm, 39, 48, 53, 52, 0.0, 0.69, mat=SHADE, bevel=bev)  # shaded top left
    lib.box(bm, 53, 47, 58, 52, 0.0, 0.72, mat=FRAME_LIT, bevel=bev)
    lib.box(bm, 39, 52, 58, 54, 0.0, 0.72, mat=FRAME_L, bevel=0.015)
    lib.box(bm, 39, 76, 58, 81, 0.0, 0.72, mat=FRAME_LIT, bevel=bev)
    lib.box(bm, 40, 55, 57, 75, 0.0, 0.64, mat=PANEL)

    # The skull in relief on the panel (rows 57-73, columns 42-54).
    skull = [(44, 57), (53, 57), (54, 58), (55, 59), (55, 66), (54, 67), (52, 67), (52, 72), (51, 73),
             (50, 74), (47, 74), (46, 73), (45, 72), (45, 67), (43, 67), (42, 66), (42, 59), (43, 58)]
    lib.relief(bm, skull, 0.6, 0.69, inset=0.4, mat=DARK)
    for c0 in (43, 50):  # eye sockets
        lib.box(bm, c0, 63, c0 + 4, 65.5, 0.6, 0.692, mat=TOOTH)
    lib.box(bm, 48, 65, 49, 66.5, 0.6, 0.692, mat=PANEL)  # nose
    for c0 in (47, 49):  # teeth
        lib.box(bm, c0, 70, c0 + 1, 72, 0.6, 0.692, mat=TOOTH)

    # Handle: a grey bar arching back over the far side from two brackets (columns 36-40, 54-58).
    for c0 in (36, 54):
        lib.box(bm, c0, 43, c0 + 5, 47, 0.3, 0.76, mat=BRACKET, bevel=0.02)
        lib.box(bm, c0 + 1, 43.3, c0 + 4, 44.6, 0.3, 0.775, mat=BCAP)
    path = []
    for i in range(15):
        a = math.pi * i / 14  # 0 = right leg, pi = left leg
        path.append((E(48 + 9 * math.cos(a)), F(43.5 - 9.2 * math.sin(a)), 0.7 + 0.12 * math.sin(a)))
    path = [(path[0][0], F(45.5), 0.7)] + path + [(path[-1][0], F(45.5), 0.7)]
    lib.sweep(bm, path, 1.05 / 12, sides=8, mat=HANDLE)

    for v in bm.verts:  # a chest is a little taller than the plank heights above suggest
        v.co.z *= 1.25
    return lib.to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newsha-155's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsha-155")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = lib.composite_png(ROOT, PIECES, layout, Path(tempfile.mkdtemp()) / "assembly.png",
                                96, 112, (48, 56))
        common.render_preview([obj], str(out), ref, size=8, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
