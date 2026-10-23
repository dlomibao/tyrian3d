"""Drilling machine (newshv.shp 1/3 over 39/41, assembly of 2 pieces): a 3D version of its sprites.

Seen in episode 2 (levels 2.12 and 2.19). Two 2x2 enemies one above the other make a ground
machine 56 px long: a blue housing (newshv-1: a tall centre block, a rounded left block, a strut
down each side, a slanted block on the right and a grey motor behind it) sitting on the back of a
big grey drill bit that tapers to a point down the screen (newshv-39). The drill lies on its side
with spiral threads; the two frames of each piece (1/3, 39/41) are the drill turning, so each
piece gets a second model, <piece>-f2, with the threads turned by half a pitch.

The machine is built whole in assembly coordinates (columns 0-24, rows 0-56: newshv-1 is rows
0-27, newshv-39 rows 28-55) and cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshv-39.py [-- --preview out.png]
(the preview is the whole machine; each exported model also gets out-<model>.png).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b081 as lib  # noqa: E402

NAME = "assembly-newshv-39"
ROOT = common.repo_root(__file__)
PIECES = ["newshv-1", "newshv-39"]
LAYOUT = {"newshv-1": (0, -14), "newshv-39": (0, 14)}
U = lib.U
AXIS = 12.5  # the drill's axis (column edge)
ZC = 0.34  # height of the drill's axis
FLAT = 0.42  # the drill is flattened: z radius = FLAT * xy radius


def X(c):
    return (c - 12) / 12


def Y(r):
    return (28 - r) / 12


def poly(points):
    return [(X(c), Y(r)) for c, r in points]


def loft_y(bm, col, sections, sides=12, mat=0):
    """A loft down the sprite centred on column edge `col`: sections are (row edge, half width px,
    half height units, z)."""
    s = len(bm.verts)
    common.loft(bm, [(Y(r), w * U, h, z) for r, w, h, z in sections], sides=sides, mat_index=mat)
    lib.move(bm, s, dx=X(col))


# The drill's half width in px at row edges: a rounded shoulder (rows 17-27), then a straight
# taper to the point at row 56.
PROFILE = [(17.6, 0.0), (17.7, 5.0), (18.3, 6.6), (19.0, 7.5), (20.0, 8.4), (21.0, 9.0), (22.0, 9.5),
           (23.0, 9.8), (24.5, 10.0), (26.5, 9.9)]
PROFILE += [(28.0 + i, 9.5 * (1 - i / 28.0)) for i in range(0, 29)]
PROFILE[-1] = (56.0, 0.0)


def drill(bm, phase, mats):
    """The drill bit with two spiral threads, raised and lit, turned by `phase` (0..1)."""
    BRIGHT, DARK, TIP = mats
    sides, pitch = 20, 9.0
    rings = []
    for r, w in PROFILE:
        if w == 0:
            rings.append([bm.verts.new((X(AXIS), Y(r), ZC))])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            f = 2 * a / (2 * math.pi) + r / pitch + phase
            rr = w * U * (1 + 0.04 * math.cos(2 * math.pi * f))
            ring.append(bm.verts.new((X(AXIS) + rr * math.cos(a), Y(r), ZC + rr * FLAT * math.sin(a))))
        rings.append(ring)
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        rm = (PROFILE[i][0] + PROFILE[i + 1][0]) / 2
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                face = (r0[k], r0[j], r1[0])
            else:
                face = (r0[k], r0[j], r1[j], r1[k])
            a = 2 * math.pi * (k + 1) / sides
            f = (2 * a / (2 * math.pi) + rm / pitch + phase) % 1.0
            fc = bm.faces.new(face)
            fc.material_index = TIP if rm > 52.5 else (DARK if 0.32 < f < 0.68 else BRIGHT)
            fc.smooth = True


def build(colors, phase, tag):
    coll = common.reset_collection(f"{NAME}{tag}")
    pal = lambda i, **kw: common.palette_material(colors, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(56, metallic=0.45, roughness=0.35),  # 0 housing faces
        pal(53, metallic=0.4, roughness=0.5),  # 1 housing walls
        pal(60, metallic=0.5, roughness=0.25),  # 2 lit edges and ribs
        pal(52, metallic=0.4, roughness=0.6),  # 3 dark seams and ledges
        pal(55, metallic=0.45, roughness=0.4),  # 4 ledge tops, struts
        pal(11, metallic=0.75, roughness=0.25),  # 5 drill threads (lit)
        pal(9, metallic=0.7, roughness=0.35),  # 6 drill grooves
        pal(12, metallic=0.8, roughness=0.2),  # 7 drill point
        pal(9, metallic=0.7, roughness=0.3),  # 8 shaft
        pal(4, metallic=0.5, roughness=0.5),  # 9 shaft collar, motor sides
        pal(8, metallic=0.6, roughness=0.35),  # 10 motor top
        pal(58, metallic=0.5, roughness=0.3),  # 11 slanted block edge
    ]
    FACE, WALL, LIT, SEAM, LEDGE, THREAD, GROOVE, POINT, SHAFT, COLLAR, MOTOR, EDGE = range(12)
    bm = bmesh.new()

    # --- The drill (rows 17-56) and its shaft under the housing (rows 9-17). ----------------------
    drill(bm, phase, (THREAD, GROOVE, POINT))
    f0 = len(bm.faces)
    loft_y(bm, AXIS, [(9.0, 6.4, 0.22, ZC), (16.4, 6.4, 0.22, ZC)], sides=16, mat=SHAFT)
    loft_y(bm, AXIS, [(16.2, 5.6, 0.2, ZC), (17.9, 5.6, 0.2, ZC)], sides=16, mat=COLLAR)
    lib.set_smooth(bm, f0, True)

    # --- The blue housing (newshv-1 rows 0-18). -----------------------------------------------------
    # Grey motor behind the right side (columns 18-21, rows 4-10).
    lib.bevel_prism(bm, poly([(18, 4.6), (19.6, 4.8), (21.2, 6.2), (22, 7.2), (22, 10.6), (18, 10.6)]),
                    0.0, 0.52, 0.8 * U, 0.06, mat_index=COLLAR, top_mat=MOTOR)
    # Centre block (columns 9-17, rows 0-8): the tallest part.
    lib.bevel_prism(bm, poly([(9, 0.1), (14, 0.1), (15, 1), (17, 1), (18, 3.8), (18, 8.2), (9, 8.2)]),
                    0.0, 0.86, 1.0 * U, 0.07, mat_index=WALL, top_mat=FACE, bevel_mat=LIT)
    # Dark ledge under its front (rows 8-10).
    lib.bevel_prism(bm, poly([(8.6, 7.6), (18.6, 7.6), (19, 10.2), (8.6, 10.2)]), 0.0, 0.62, 0.6 * U,
                    0.04, mat_index=SEAM, top_mat=SEAM)
    # Rounded left block (columns 1-8, rows 1-7) with a lit rib (column 7), on a ledge (rows 7-10).
    lib.bevel_prism(bm, poly([(4, 1), (8.8, 1), (8.8, 7.4), (1, 7.4), (1, 4), (2, 2.8), (3, 1.8)]),
                    0.0, 0.76, 1.8 * U, 0.14, mat_index=WALL, top_mat=FACE, bevel_mat=LIT)
    lib.box(bm, X(6.9), Y(7.0), X(7.9), Y(1.6), 0.5, 0.8, LIT)
    lib.bevel_prism(bm, poly([(1, 6.8), (8.8, 6.8), (8.8, 10.2), (2, 10.2), (1, 9.4)]), 0.0, 0.58,
                    0.6 * U, 0.04, mat_index=SEAM, top_mat=LEDGE)
    # Left strut down to the drill's shoulder (columns 2-5, rows 9-18), with a foot (rows 15-18).
    f0 = len(bm.faces)
    loft_y(bm, 4.0, [(8.8, 2.0, 0.2, 0.44), (16.6, 2.0, 0.2, 0.44), (17.6, 1.6, 0.14, 0.44)],
           sides=10, mat=LEDGE)
    lib.box(bm, X(3.1), Y(14.5), X(3.9), Y(9.4), 0.44, 0.665, LIT)
    lib.set_smooth(bm, f0, True)
    lib.bevel_prism(bm, poly([(2, 15.4), (8, 15.4), (8, 16.8), (6.5, 18.2), (4, 18.4), (2.6, 17)]),
                    0.0, 0.48, 0.6 * U, 0.04, mat_index=WALL, top_mat=LEDGE)
    # Right strut (columns 12-14, rows 10-17) and the slanted block beside it (columns 15-22).
    f0 = len(bm.faces)
    loft_y(bm, 13.5, [(9.0, 1.7, 0.2, 0.46), (17.6, 1.7, 0.2, 0.46)], sides=10, mat=LEDGE)
    lib.box(bm, X(13.0), Y(16.5), X(13.9), Y(10.4), 0.46, 0.665, LIT)
    lib.set_smooth(bm, f0, True)
    lib.bevel_prism(bm, poly([(14.8, 9.2), (19, 9.2), (20, 10), (21, 11), (22, 12), (23, 13), (23, 16),
                              (22, 17), (21, 18), (16.8, 18), (14.8, 16.8)]),
                    0.0, 0.66, 1.2 * U, 0.1, mat_index=WALL, top_mat=FACE, bevel_mat=EDGE)
    lib.box(bm, X(17.0), Y(15.6), X(18.6), Y(14.4), 0.6, 0.67, SEAM)  # the dark seam at row 15

    return lib.mesh_object_mixed(f"{NAME}{tag}", bm, mats, coll)


def main():
    colors = lib.merged_colors(ROOT, PIECES)
    sprites = {n: common.load_sprite(ROOT, n) for n in PIECES}
    out = lib.preview_arg()
    # (model, piece, phase, frame index in that piece's sprite.json)
    exports = [("newshv-1", "newshv-1", 0.0, 0), ("newshv-39", "newshv-39", 0.0, 0),
               ("newshv-1-f2", "newshv-1", 0.5, 1), ("newshv-39-f2", "newshv-39", 0.5, 1)]
    wholes = {}
    for phase, tag in ((0.0, ""), (0.5, "-f2")):
        whole = build(colors, phase, tag)
        wholes[tag] = whole
        cut = common.split_assembly(whole, [(p + tag, *LAYOUT[p]) for p in PIECES])
        for model, piece, ph, fi in exports:
            if ph != phase:
                continue
            frame = sprites[piece]["frames"][fi]
            num = int(frame["image"].split("-")[-1].split(".")[0])
            common.export_sprite_model(ROOT, [cut[model]], f"enemies/{model}",
                                       lib.frames_subset(sprites[piece], {num}))
            if out:
                common.render_preview([cut[model]], str(out.with_name(f"{out.stem}-{model}.png")),
                                      ROOT / "reference" / "models" / piece / frame["image"], size=2)
        if out:
            import tempfile
            ref = lib.composite_png(ROOT, [(p, 0 if phase == 0 else 1, *LAYOUT[p]) for p in PIECES], 5,
                                    Path(tempfile.mkdtemp()) / "drill.png")
            for o in wholes.values():
                o.hide_render = False
            common.render_preview([whole], str(out.with_name(f"{out.stem}{tag}.png")), ref, size=5,
                                  view_px=400)


if __name__ == "__main__":
    main()
