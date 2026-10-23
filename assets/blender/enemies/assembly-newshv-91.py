"""Blue twin-pod gunship (newshv.shp 89, 91/129, 93): a 3D version of its three-piece sprite.

Seen in episode 2 (level 2.15). Three 2x2 enemies side by side make one craft 72 px wide: a
central tube with a domed middle, a chin with gun ports under it and two prongs, joined by collars
to two big side hulls (newshv-89 on the left, newshv-93 its mirror on the right). Each hull has
ribbed vents on top, a ridge and rails, and a glossy red ball on its outer side. The centre piece
has a second frame (129) where the guns fire: the middle port glows and a wide flare spreads below
the chin, so it gets its own model, newshv-91-f2.

The whole craft is built once in assembly coordinates (centre piece at the origin, pieces 24 px
apart) and cut into pieces with common.split_assembly so they line up.

Run: blender --background --python assets/blender/enemies/assembly-newshv-91.py [-- --preview out.png]
(the preview writes out.png for the whole craft and out-<piece>.png for each piece).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b003 as lib  # noqa: E402

NAME = "assembly-newshv-91"
ROOT = common.repo_root(__file__)
PIECES = ["newshv-89", "newshv-91", "newshv-93"]
LAYOUT = [("newshv-89", -24, 0), ("newshv-91", 0, 0), ("newshv-93", 24, 0)]
U = 1 / 12


def ax(u):
    """Assembly column edge (0 = left edge of newshv-89, 72 = right edge of newshv-93) to X."""
    return (u - 36) / 12


def ay(r):
    """Row edge (0 = top of the 28 px tall pieces) to Y."""
    return (14 - r) / 12


def poly(points):
    """(column edge, row edge) points to XY."""
    return [(ax(u), ay(r)) for u, r in points]


def build(colors, firing):
    coll = common.reset_collection(NAME + ("-f2" if firing else ""))
    pal = lambda i, **kw: common.palette_material(colors, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(56, metallic=0.5, roughness=0.4),  # 0 hull
        pal(60, metallic=0.5, roughness=0.3),  # 1 tube
        pal(62, metallic=0.55, roughness=0.25),  # 2 bright ribs and ridge
        pal(54, metallic=0.4, roughness=0.5),  # 3 dark lower deck and seams
        pal(70, metallic=0.35, roughness=0.22),  # 4 red balls and lamps
        pal(68, metallic=0.3, roughness=0.5),  # 5 gun ports (cold)
        pal(122, emission_strength=4.0),  # 6 gun port firing
        pal(116, emission_strength=3.0),  # 7 flare, outer red
        pal(121, emission_strength=4.0),  # 8 flare, orange
        pal(125, emission_strength=5.0),  # 9 flare core, yellow
        pal(58, metallic=0.5, roughness=0.35),  # 10 upper hull block and vents
        pal(60, metallic=0.5, roughness=0.3),  # 11 rails
        pal(57, metallic=0.45, roughness=0.4),  # 12 collars, chin and prongs
    ]
    (HULL, TUBE, RIB, DARK, RED, PORT, PORT_HOT, FLARE_R, FLARE_O, FLARE_Y, BLOCK, RAIL,
     COLLAR) = range(13)
    bm = bmesh.new()

    # --- Left side hull (newshv-89, columns 0-23); mirrored for newshv-93 afterwards. ----------
    side_start = len(bm.verts)
    # Main hull outline, inside the sprite's outline pixels, up to the collar at column 24; its
    # top edges are chamfered so it reads as a solid rounded block.
    E = 23.98
    lib.bevel_prism(bm, poly([(9, 6), (15, 6), (15, 5.1), (22, 5.1), (E, 7), (E, 21), (23, 22),
                              (21.2, 23.9), (15, 23.9), (13, 23), (11, 22), (9, 21), (7.1, 20),
                              (7.1, 15), (8, 14), (8, 10), (9, 9)]), -0.2, 0.15, 1.2 * U, 0.06,
                    mat_index=DARK, top_mat=HULL)
    # Raised block right of the ridge (columns 15-24, rows 5-19), brighter near the top.
    lib.bevel_prism(bm, poly([(15.5, 5.6), (21.8, 5.6), (E, 7.5), (E, 19.4), (15.5, 19.4)]),
                    0.0, 0.21, 0.8 * U, 0.04, mat_index=HULL, top_mat=BLOCK)
    # The bright ridge down column 15 (rows 5-23).
    lib.prism(bm, poly([(14.9, 5.2), (16.0, 5.2), (16.0, 23.6), (14.9, 23.6)]), 0.0, 0.24, RIB)
    # Vent block, upper left (columns 9-15, rows 6-11) with three bright ribs (columns 9, 11, 13).
    lib.bevel_prism(bm, poly([(9.2, 6.3), (15, 6.3), (15, 11), (8.5, 11), (8.5, 9.2)]), 0.0, 0.2,
                    0.6 * U, 0.03, mat_index=HULL, top_mat=BLOCK)
    for c in (9, 11, 13):
        lib.prism(bm, poly([(c + 0.1, 6.3), (c + 0.9, 6.3), (c + 0.9, 10.6), (c + 0.1, 10.6)]),
                  0.1, 0.25, RIB)
    # Rails across the block: row 14 (columns 16-24) and row 19 (columns 19-24).
    lib.prism(bm, poly([(16, 13.9), (E, 13.9), (E, 15), (16, 15)]), 0.1, 0.25, RAIL)
    lib.prism(bm, poly([(19, 18.9), (E, 18.9), (E, 19.9), (19, 19.9)]), 0.05, 0.22, RAIL)
    # Lower deck reaching out under the ball (columns 3-8, rows 16-19).
    lib.prism(bm, poly([(3.1, 16), (8, 15.4), (8, 19), (7, 19.6), (3.1, 19)]), -0.18, 0.0, DARK)

    # Glossy red ball on the outer side (columns 2-7, rows 8-15).
    f0 = len(bm.faces)
    lib.ellipsoid(bm, (ax(5.0), ay(11.8), 0.03), (3.1 * U, 3.6 * U, 0.2), sides=14, rings=8,
                  mat_index=RED)
    # A small red lamp under the hull's corner (centre piece column 0, rows 19-20).
    lib.ellipsoid(bm, (ax(24.6), ay(20.0), -0.05), (0.6 * U, 1.0 * U, 0.05), sides=8, rings=4,
                  mat_index=RED)
    lib.set_smooth(bm, f0)
    lib.mirror_x(bm, side_start)

    # --- Centre (newshv-91, columns 24-47) -------------------------------------------------------
    # Collars where the tube meets the hulls (columns 24-28, rows 7-15).
    f0 = len(bm.faces)
    for u0, u1 in ((24.02, 28.0), (44.0, 47.98)):
        start = len(bm.verts)
        lib.loft_x(bm, [(ax(u0), 4.0 * U, 0.22, 0.0), (ax(u0 + 0.6), 4.1 * U, 0.235, 0.0),
                        (ax(u1 - 0.6), 4.1 * U, 0.235, 0.0), (ax(u1), 4.0 * U, 0.22, 0.0)],
                   sides=12, mat_index=COLLAR)
        lib.move(bm, start, dy=ay(11.0))
    # The tube (rows 8-15) with a domed middle, its highlight at row 10.
    tube = [(28.0, 3.4, 0.2), (31, 3.5, 0.23), (34, 3.6, 0.27), (36, 3.65, 0.28), (38, 3.6, 0.27),
            (41, 3.5, 0.23), (44.0, 3.4, 0.2)]
    start = len(bm.verts)
    lib.loft_x(bm, [(ax(u), hy * U, hz, 0.0) for u, hy, hz in tube], sides=14, mat_index=TUBE)
    lib.move(bm, start, dy=ay(11.5))
    lib.set_smooth(bm, f0)

    # Chin under the tube (rows 15-18, columns 4-19 of the piece), with the gun ports along row 15.
    lib.prism(bm, poly([(28, 14.0), (44, 14.0), (44, 16), (43, 17), (42, 18), (30, 18), (29, 17),
                        (28, 16)]), -0.2, 0.06, COLLAR)
    lib.prism(bm, poly([(30.2, 16.9), (41.8, 16.9), (41.8, 18), (30.2, 18)]), -0.15, 0.04, DARK)
    for u0, u1 in ((32, 33), (39, 40)):
        lib.prism(bm, poly([(u0 + 0.1, 14.9), (u1 - 0.1, 14.9), (u1 - 0.1, 16.0), (u0 + 0.1, 16.0)]),
                  0.0, 0.09, PORT)
    lib.prism(bm, poly([(34.1, 14.9), (37.9, 14.9), (37.9, 16.1), (34.1, 16.1)]), 0.0, 0.1,
              PORT_HOT if firing else PORT)
    # Two prongs pointing down the screen (columns 7 and 16 of the piece, rows 16-19).
    f0 = len(bm.faces)
    for u in (31.5, 40.5):
        start = len(bm.verts)
        common.loft(bm, [(ay(16.5), 0.55 * U, 0.6 * U, -0.04), (ay(18.4), 0.5 * U, 0.5 * U, -0.04),
                         (ay(19.0), 0.0, 0.0, -0.04)], sides=8, mat_index=COLLAR)
        lib.move(bm, start, dx=ax(u))
    lib.set_smooth(bm, f0)

    if firing:
        # The muzzle flare (frame 129): a flat, wide burst below the chin, hottest in the middle.
        f0 = len(bm.faces)
        lib.ellipsoid(bm, (ax(36), ay(19.6), -0.04), (11.6 * U, 1.9 * U, 0.05), sides=20, rings=6,
                      mat_index=FLARE_R)
        lib.ellipsoid(bm, (ax(36), ay(19.6), -0.03), (6.5 * U, 1.7 * U, 0.07), sides=16, rings=6,
                      mat_index=FLARE_O)
        lib.ellipsoid(bm, (ax(36), ay(19.5), -0.02), (2.6 * U, 1.2 * U, 0.09), sides=12, rings=6,
                      mat_index=FLARE_Y)
        lib.set_smooth(bm, f0)

    return lib.mesh_object_mixed(coll.name, bm, mats, coll)


def main():
    sprites = {n: common.load_sprite(ROOT, n) for n in PIECES}
    colors = lib.merged_colors(ROOT, PIECES)
    out = None
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])

    whole = build(colors, firing=False)
    pieces = common.split_assembly(whole, LAYOUT)
    hot = build(colors, firing=True)
    pieces["newshv-91-f2"] = common.split_assembly(hot, [("newshv-91-f2", 0, 0)])["newshv-91-f2"]

    def frames(name, keep):
        return [dict(s, frames=[f for f in s["frames"] if f in keep]) for s in sprites[name]["sprites"]]

    exports = {
        "newshv-89": (sprites["newshv-89"]["sprites"], "frame-newshv-89.png", "newshv-89"),
        "newshv-91": (frames("newshv-91", {91}), "frame-newshv-91.png", "newshv-91"),
        "newshv-91-f2": (frames("newshv-91", {129}), "frame-newshv-129.png", "newshv-91"),
        "newshv-93": (sprites["newshv-93"]["sprites"], "frame-newshv-93.png", "newshv-93"),
    }
    for model, (spr, image, ref) in exports.items():
        common.export_sprite_model(ROOT, [pieces[model]], f"enemies/{model}", spr)
    if out:
        whole.hide_render = False
        common.render_preview([whole], out, None, size=6)
        for model, (spr, image, ref) in exports.items():
            common.render_preview([pieces[model]], out.with_name(f"{out.stem}-{model}.png"),
                                  ROOT / "reference" / "models" / ref / image, size=2)


if __name__ == "__main__":
    main()
