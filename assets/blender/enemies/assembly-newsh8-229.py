"""Antlered spider (newsh8.shp, assembly of newsh8-229 and newsh8-231): a 3D version of its sprites.

Seen in episode 3 (levels 3.4 and 3.19). Two 2x2 enemies side by side make one 48x28 px
creature, mirror symmetric about the seam: a glossy red abdomen in the middle with a small red
bead above it on two grey stalks, two grey jointed legs hanging under it, and on each side a
brown thorax from which four brown legs curve out and up like antlers. Each piece's three frames
only move the leg tips by a pixel or two (a walk), so one model covers each piece, with the legs
of each frame as a separate part (common.frame_part).

The whole creature is built once (left half, mirrored about the centre of newsh8-229's pixel
column 23, which is the sprite's axis), coloured from both sprites, then cut into the two
pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh8-229.py [-- --preview out.png]
(the preview is the whole creature; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b060 as L  # noqa: E402

NAME = "assembly-newsh8-229"
ROOT = common.repo_root(__file__)
PIECES = ["newsh8-229", "newsh8-231"]
# Built in newsh8-229's coordinates (its centre is the origin); newsh8-231 sits 24 px to the right.
AXIS = L.px(23)
FRAMES = [(229, 231), (233, 235), (273, 275)]  # the walk's frames: (newsh8-229's, newsh8-231's)


def build(sprite, grids):
    """The body (static) and the legs for each frame of the walk (grids: the joined sprite pixels
    of each frame pair)."""
    coll = common.reset_collection(NAME)
    tag = "nsh8_229"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(24, metallic=0.25, roughness=0.5),  # 0 brown legs
        pal(21, metallic=0.2, roughness=0.6),  # 1 dark brown
        pal(27, metallic=0.3, roughness=0.45),  # 2 light brown
        pal(72, metallic=0.3, roughness=0.2),  # 3 red abdomen
        pal(67, metallic=0.3, roughness=0.3),  # 4 dark red
        pal(75, metallic=0.35, roughness=0.15),  # 5 light red
        pal(10, metallic=0.75, roughness=0.3),  # 6 grey legs and stalks
        pal(5, metallic=0.7, roughness=0.4),  # 7 dark grey joints
    ]
    BROWN, DBROWN, LBROWN, RED, DRED, LRED, GREY, DGREY = range(8)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----
    thorax = []
    thorax += L.ptube(bm, [(11.2, 23.6, -0.03, 0.78), (11.2, 25.0, -0.04, 0.65), (11.2, 25.6, -0.04, 0.0)],
                    sides=6, mat=BROWN)  # little spur under the fourth leg
    # Thorax: a brown hump where the legs meet (columns 13-20, rows 8-18).
    thorax += L.ellipsoid(bm, L.P(17.0, 13.4, 0.0), (2.8 * L.PX, 5.4 * L.PX, 0.1), segments=12, rings=8, mat=BROWN)
    thorax += L.ellipsoid(bm, L.P(15.4, 16.0, 0.0), (2.4 * L.PX, 2.6 * L.PX, 0.09), segments=10, rings=5, mat=BROWN)

    # Grey stalk from the bead down to the abdomen (columns 21-22, rows 8-12).
    L.ptube(bm, [(21.2, 7.6, 0.02, 0.55), (21.9, 8.8, 0.02, 0.55), (22.0, 12.8, 0.0, 0.55)], sides=6, mat=GREY)
    mirror_from = list(bm.faces)
    L.mirror(bm, AXIS, mirror_from)
    bm.faces.ensure_lookup_table()
    legs_all = [f for f in bm.faces if f.material_index in (BROWN, DBROWN)]
    shade = lambda v, s: LBROWN if v >= 25.5 else (BROWN if v >= 20.5 else DBROWN)  # noqa: E731
    L.paint(bm, legs_all, grids[0], shade, w=48, h=28, ox=1.0)

    # ---- centre (on the axis) ----
    # Red bead above (rows 3-8) and the big glossy abdomen (rows 12-20).
    L.ellipsoid(bm, L.P(23, 5.6, 0.04), (1.9 * L.PX, 2.4 * L.PX, 0.1), segments=12, rings=6, mat=RED)
    L.ellipsoid(bm, L.P(23, 16.2, 0.02), (3.5 * L.PX, 3.9 * L.PX, 0.2), segments=18, rings=9, mat=RED)
    L.ellipsoid(bm, L.P(23, 19.0, -0.02), (2.0 * L.PX, 1.6 * L.PX, 0.1), segments=10, rings=5, mat=DRED)
    for side in (-1, 1):  # light ridges down both flanks, where the sprite catches the light
        L.ellipsoid(bm, L.P(23 + side * 1.2, 15.4, 0.12), (1.0 * L.PX, 2.6 * L.PX, 0.11), segments=8, rings=4,
                    mat=LRED)

    body = L.to_object(NAME, bm, mats, coll)
    return body, [leg_variant(sprite, k, grid, mats, coll, shade) for k, grid in enumerate(grids)]


# The legs walk: from frame to frame (229/231, 233/235, 273/275) the antler and the third leg pull
# their tips in a pixel at a time while the second and fourth legs reach a pixel further, and the
# grey leg under the abdomen swings its foot a pixel outward. Rows each leg's tip moves by:
TIP_SHIFT = {"antler": (0, 1, 2), "second": (0, -1, -2), "third": (0, 1, 2), "fourth": (0, -1, -2)}
GREY_SWING = (0.0, 1.0, 2.0)  # columns the grey leg's foot moves out


def leg_variant(sprite, k, grid, mats, coll, shade):
    """The legs as they are on frame k of the walk, both sides, as one object."""
    BROWN, GREY, DGREY = 0, 6, 7
    bm = bmesh.new()

    def tipped(path, d):  # move the tip and the next point by d rows
        return [(c, r + d, z, rad) if i < 2 else (c, r, z, rad) for i, (c, r, z, rad) in enumerate(path)]

    t = {leg: shift[k] for leg, shift in TIP_SHIFT.items()}
    brown = []
    # Antler: from the tip at column 13 down and out to the thorax (rows 1-12).
    brown += L.ptube(bm, tipped([(13.1, 0.6, 0.06, 0.0), (13.1, 1.4, 0.06, 0.78), (13.2, 3.8, 0.05, 0.98),
                                 (14.4, 5.6, 0.04, 1.17), (16.2, 7.0, 0.03, 1.43), (17.2, 8.6, 0.02, 1.95),
                                 (17.4, 11.0, 0.01, 2.08)], t["antler"]), sides=8, mat=BROWN)
    # Second leg: tip at column 9, row 9, curling down into the thorax (row 13).
    brown += L.ptube(bm, tipped([(9.1, 8.6, 0.05, 0.0), (9.1, 9.3, 0.05, 0.78), (9.3, 11.0, 0.04, 1.04),
                                 (10.6, 12.3, 0.03, 1.23), (12.8, 13.0, 0.02, 1.43), (15.5, 13.2, 0.02, 1.56)],
                                t["second"]), sides=8, mat=BROWN)
    # Third leg: tip at column 5, row 12, down and back along row 18 to the thorax.
    brown += L.ptube(bm, tipped([(5.1, 11.6, 0.04, 0.0), (5.1, 12.4, 0.04, 0.78), (5.2, 15.2, 0.03, 1.04),
                                 (6.2, 17.2, 0.02, 1.3), (8.2, 18.5, 0.0, 1.37), (14.0, 18.5, 0.0, 1.43),
                                 (16.0, 17.6, 0.01, 1.56)], t["third"]), sides=8, mat=BROWN)
    # Fourth leg: tip at column 1, row 18, down and back along rows 23-24, then up column 13.
    brown += L.ptube(bm, tipped([(1.2, 17.8, 0.02, 0.0), (1.2, 18.6, 0.02, 0.78), (1.5, 20.8, 0.01, 1.04),
                                 (3.0, 23.0, -0.01, 1.3), (6.0, 23.6, -0.02, 1.37), (11.0, 23.6, -0.02, 1.37),
                                 (12.8, 22.4, -0.02, 1.17), (13.2, 20.5, -0.01, 1.1), (14.2, 18.8, 0.0, 1.17)],
                                t["fourth"]), sides=8, mat=BROWN)
    # Grey jointed leg hanging under the abdomen (columns 15-20, rows 17-25); its knee and foot
    # swing out on the later frames.
    g = GREY_SWING[k]
    grey = L.ptube(bm, [(19.8, 16.6, -0.02, 0.6), (17.8, 18.8, -0.04, 0.7), (16.5 - 0.6 * g, 21.3, -0.06, 0.75),
                        (17.6 - g, 22.8, -0.06, 0.65), (19.2 - g, 24.4, -0.06, 0.55), (20.4 - g, 25.6, -0.06, 0.0)],
                   sides=6, mat=GREY)
    grey += L.ellipsoid(bm, L.P(16.4 - 0.6 * g, 21.6, -0.06), (1.0 * L.PX, 0.9 * L.PX, 0.06), segments=8,
                        rings=4, mat=DGREY)
    brown += L.mirror(bm, AXIS, brown)
    L.mirror(bm, AXIS, grey)
    L.paint(bm, brown, grid, shade, w=48, h=28, ox=1.0)
    return L.to_object(f"{NAME}-legs-{k}", bm, mats, coll)


def main():
    sprite = L.merged_sprite(ROOT, PIECES)
    data = {name: common.load_sprite(ROOT, name) for name in PIECES}
    grids = [[a + b for a, b in zip(L.frame_pixels(data["newsh8-229"], f1), L.frame_pixels(data["newsh8-231"], f2))]
             for f1, f2 in FRAMES]
    obj, leg_objs = build(sprite, grids)
    layout = [("newsh8-229", 0, 0), ("newsh8-231", 24, 0)]
    pieces = common.split_assembly(obj, layout)
    parts = {name: [pieces[name]] for name in PIECES}
    for k, leg_obj in enumerate(leg_objs):
        for i, (name, piece) in enumerate(common.split_assembly(leg_obj, layout).items()):
            frame = FRAMES[k][i]
            piece.name = piece.data.name = f"{name}-legs-{frame}"
            parts[name].append(common.frame_part(piece, [frame]))
    for name in PIECES:
        common.export_sprite_model(ROOT, parts[name], f"enemies/{name}", data[name]["sprites"])
    if "--frames" in sys.argv:
        out_dir = Path(sys.argv[sys.argv.index("--frames") + 1])
        for name in PIECES:
            common.render_frame_previews(parts[name], str(out_dir / f"{name}.png"), data[name], ROOT)
    out = L.preview_args()
    if out:
        ref = L.composite_png(ROOT, [("newsh8-229", 229, 0, 14), ("newsh8-231", 231, 24, 14)], 48, 56,
                              Path(tempfile.mkdtemp()) / "assembly.png")
        whole = [obj, leg_objs[0]]
        for o in whole:
            o.location.x = -1.0
        common.render_preview(whole, str(out), str(ref), size=4, view_px=480)
        for o in whole:
            o.location.x = 0.0
        for name in PIECES:
            first = data[name]["frames"][0]
            common.render_preview(parts[name], str(out.parent / f"{name}.png"),
                                  ROOT / "reference" / "models" / name / first["image"], size=2, frame=first["index"])


if __name__ == "__main__":
    main()
