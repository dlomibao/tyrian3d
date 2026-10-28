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


def bevel_prism3(bm, outline, z0, z1, bevel, bevel_h, wall, band, top):
    """lib.bevel_prism with its own material for the chamfer band: seen from above the band covers
    the sprite's dark outline pixels, so it gets the outline's dark shade."""
    hi_xy = lib.inset_outline(outline, bevel)
    n = len(outline)
    lo = [bm.verts.new((x, y, z0)) for x, y in outline]
    mid = [bm.verts.new((x, y, z1 - bevel_h)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in hi_xy]
    bm.faces.new(list(reversed(lo))).material_index = wall
    bm.faces.new(hi).material_index = top
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], mid[j], mid[i])).material_index = wall
        bm.faces.new((mid[i], mid[j], hi[j], hi[i])).material_index = band


def build(colors, firing):
    coll = common.reset_collection(NAME + ("-f2" if firing else ""))
    pal = lambda i, **kw: common.palette_material(colors, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(55, metallic=0.25, roughness=0.45),  # 0 hull deck
        pal(59, metallic=0.25, roughness=0.3),  # 1 tube
        pal(62, metallic=0.3, roughness=0.25),  # 2 bright ribs and ridge
        pal(54, metallic=0.25, roughness=0.5),  # 3 dark lower deck and seams
        pal(69, metallic=0.1, roughness=0.2),  # 4 red balls and lamps
        pal(68, metallic=0.2, roughness=0.5),  # 5 gun ports (cold)
        pal(122, emission_strength=4.0),  # 6 gun port firing
        pal(115, emission_strength=2.5),  # 7 flare, outer dark red
        pal(118, emission_strength=3.0),  # 8 flare, red
        pal(121, emission_strength=4.0),  # 9 flare, orange
        pal(58, metallic=0.25, roughness=0.35),  # 10 upper hull block and vents
        pal(60, metallic=0.25, roughness=0.3),  # 11 rails
        pal(56, metallic=0.25, roughness=0.4),  # 12 collars, chin and prongs
        pal(50, metallic=0.2, roughness=0.6),  # 13 outline-dark chamfer bands, vent recess
        pal(52, metallic=0.25, roughness=0.5),  # 14 side walls
        pal(123, emission_strength=4.5),  # 15 flare, yellow-orange
        pal(125, emission_strength=5.0),  # 16 flare core, yellow
        pal(64, metallic=0.2, roughness=0.5),  # 17 ball socket (the ball's dark rim)
    ]
    (HULL, TUBE, RIB, DARK, RED, PORT, PORT_HOT, FLARE_DR, FLARE_R, FLARE_O, BLOCK, RAIL,
     COLLAR, EDGE, WALL, FLARE_YO, FLARE_Y, SOCKET) = range(18)
    bm = bmesh.new()

    # --- Left side hull (newshv-89, columns 0-23); mirrored for newshv-93 afterwards. ----------
    side_start = len(bm.verts)
    # Main hull, traced on the outer edge of the sprite's outline pixels (the dark chamfer band
    # covers them from above). It runs 0.3 px past column 24 into the collar so the pieces meet;
    # the split cuts it at the piece edge.
    E = 24.3
    bevel_prism3(bm, poly([(8, 5), (13.5, 5), (14.2, 4), (21.8, 4), (22.5, 5), (E, 5), (E, 22),
                           (22.2, 22), (21, 23.2), (21, 25), (16, 25), (9, 21.5),
                           (8, 21)]), -0.25, 0.38, 1.2 * U, 0.08, WALL, EDGE, HULL)
    # Raised block right of the ridge (columns 15-24, rows 5-19), brighter near the top: a deck
    # about 1.5 px above the rest of the hull.
    lib.bevel_prism(bm, poly([(15.5, 5.5), (21.8, 5.5), (E, 7.5), (E, 14.5), (15.5, 14.5)]),
                    0.0, 0.52, 0.8 * U, 0.05, mat_index=HULL, top_mat=BLOCK)
    # Its darker lower half (rows 15-19) a step lower.
    lib.bevel_prism(bm, poly([(15.5, 14.2), (E, 14.2), (E, 19.4), (15.5, 19.4)]), 0.0, 0.47,
                    0.6 * U, 0.04, mat_index=HULL, top_mat=HULL)
    # The bright ridge down column 15 (rows 5-23).
    lib.bevel_prism(bm, poly([(14.8, 5.1), (16.1, 5.1), (16.1, 23.8), (14.8, 23.8)]), 0.0, 0.57,
                    0.3 * U, 0.03, mat_index=RIB)
    # Vent block, upper left (columns 9-15, rows 6-11): a recessed dark well with three bright
    # ribs (columns 9, 11, 13) standing 2 px proud of the block.
    lib.bevel_prism(bm, poly([(8.9, 5.6), (15, 5.6), (15, 11), (8.5, 11), (8.5, 9.2)]), 0.0, 0.46,
                    0.6 * U, 0.04, mat_index=HULL, top_mat=BLOCK)
    for c in (9, 11, 13):
        lib.bevel_prism(bm, poly([(c + 0.05, 6.0), (c + 0.95, 6.0), (c + 0.95, 10.7),
                                  (c + 0.05, 10.7)]), 0.3, 0.63, 0.2 * U, 0.02, mat_index=RIB)
    # Rails across the block: row 14 (columns 16-24) and row 19 (columns 19-24).
    lib.bevel_prism(bm, poly([(16, 13.9), (E, 13.9), (E, 15), (16, 15)]), 0.3, 0.62, 0.2 * U,
                    0.02, mat_index=RAIL)
    lib.bevel_prism(bm, poly([(19, 18.9), (E, 18.9), (E, 19.9), (19, 19.9)]), 0.2, 0.56, 0.2 * U,
                    0.02, mat_index=RAIL)
    # Lower deck reaching out under the ball (columns 1-8, rows 15-20), with the small dark tab
    # below the ball (columns 1-3, rows 15-16).
    lib.prism(bm, poly([(1, 15), (8.2, 15), (8.2, 21), (7, 21), (7, 20), (3, 20), (3, 19),
                        (2, 19), (2, 17), (1, 17)]), -0.2, 0.1, DARK)
    lib.bevel_prism(bm, poly([(1.0, 14.8), (3.6, 14.8), (3.6, 16.6), (1.0, 16.6)]), 0.0, 0.2,
                    0.4 * U, 0.04, mat_index=EDGE)

    # Glossy red ball on the outer side (columns 1-8, rows 7-15): a full sphere, about two
    # thirds of it above the lower deck.
    f0 = len(bm.faces)
    lib.ellipsoid(bm, (ax(4.9), ay(11.6), 0.2), (3.3 * U, 3.6 * U, 0.3), sides=16, rings=10,
                  mat_index=RED)
    # A dark socket under it, whose rim shows round the ball from above like the sprite's outline.
    lib.ellipsoid(bm, (ax(4.8), ay(11.7), 0.03), (4.1 * U, 4.5 * U, 0.15), sides=12, rings=6,
                  mat_index=SOCKET)
    lib.set_smooth(bm, f0)
    # The hull's lower corner reaches into the centre piece (columns 24-25, rows 18-21) with a
    # small red lamp on it (column 24, rows 19-20).
    lib.bevel_prism(bm, poly([(23.0, 17.8), (26.0, 17.8), (26.0, 22.0), (23.0, 22.0)]), -0.22,
                    0.22, 0.6 * U, 0.05, mat_index=WALL, top_mat=EDGE)
    f0 = len(bm.faces)
    lib.ellipsoid(bm, (ax(24.6), ay(19.9), 0.22), (0.8 * U, 1.1 * U, 0.08), sides=8, rings=4,
                  mat_index=RED)
    lib.set_smooth(bm, f0)
    lib.mirror_x(bm, side_start)

    # --- Centre (newshv-91, columns 24-47) -------------------------------------------------------
    ZC = 0.16  # the tube's axis height: its underside is level with the hulls'
    # Collars where the tube meets the hulls (columns 24-28, rows 6-16): round, as tall as wide,
    # overlapping into the hulls so the pieces meet.
    f0 = len(bm.faces)
    for u0, u1 in ((23.6, 29.6), (42.4, 48.4)):
        start = len(bm.verts)
        w = (4.9, 5.0, 5.0, 4.7) if u0 < 36 else (4.7, 5.0, 5.0, 4.9)
        lib.loft_x(bm, [(ax(u0), w[0] * U, 0.38, ZC), (ax(u0 + 0.8), w[1] * U, 0.4, ZC),
                        (ax(u1 - 0.8), w[2] * U, 0.4, ZC), (ax(u1), w[3] * U, 0.38, ZC)],
                   sides=14, mat_index=COLLAR)
        lib.move(bm, start, dy=ay(11.0))
    # The tube (rows 7-15), round, bulging in the middle where the sprite's highlight is (row 10).
    tube = [(28.0, 4.0, 0.35), (31, 4.1, 0.38), (34, 4.2, 0.41), (36, 4.25, 0.42),
            (38, 4.2, 0.41), (41, 4.1, 0.38), (44.0, 4.0, 0.35)]
    start = len(bm.verts)
    lib.loft_x(bm, [(ax(u), hy * U, hz, ZC) for u, hy, hz in tube], sides=16, mat_index=TUBE)
    lib.move(bm, start, dy=ay(11.5))
    lib.set_smooth(bm, f0)

    # Chin under the tube (rows 14-18, columns 28-43), with the gun ports along row 15; below it
    # the dark strip of row 18, cut in lower than the chin, and the prongs crossing it.
    lib.bevel_prism(bm, poly([(28, 14.0), (44, 14.0), (44, 16.8), (42.8, 18.0), (29.2, 18.0),
                              (28, 16.8)]), -0.28, 0.2, 0.5 * U, 0.04, mat_index=WALL,
                    top_mat=COLLAR)
    lib.prism(bm, poly([(30.05, 17.5), (41.95, 17.5), (41.95, 19.95), (38.9, 19.95), (38.9, 19.0),
                        (33.1, 19.0), (33.1, 19.95), (30.05, 19.95)]), -0.26, -0.02, EDGE)
    for u0, u1 in ((32, 33), (39, 40)):
        lib.prism(bm, poly([(u0 + 0.05, 14.9), (u1 - 0.05, 14.9), (u1 - 0.05, 16.0),
                            (u0 + 0.05, 16.0)]), 0.0, 0.205, PORT)
    lib.prism(bm, poly([(34.05, 14.9), (37.95, 14.9), (37.95, 16.05), (34.05, 16.05)]), 0.0,
              0.21, PORT_HOT if firing else PORT)
    # Two prongs pointing down the screen (columns 31 and 40, rows 16-19).
    f0 = len(bm.faces)
    for u in (31.5, 40.5):
        start = len(bm.verts)
        common.loft(bm, [(ay(16.5), 0.6 * U, 0.7 * U, 0.02), (ay(19.0), 0.55 * U, 0.6 * U, 0.02),
                         (ay(19.9), 0.0, 0.0, 0.02)], sides=8, mat_index=COLLAR)
        lib.move(bm, start, dx=ax(u))
    lib.set_smooth(bm, f0)

    if firing:
        # The muzzle flare (frame 129): a flat, wide burst below the chin (rows 18-21), dark red at
        # its tips and white-yellow in the middle; nested glowing lenses, hottest on top.
        f0 = len(bm.faces)
        for (rx, ry, rz, z, cy, m) in ((12.0, 2.2, 0.05, 0.03, 19.6, FLARE_DR),
                                       (8.6, 1.9, 0.07, 0.04, 19.55, FLARE_R),
                                       (5.6, 1.6, 0.09, 0.05, 19.5, FLARE_O),
                                       (3.6, 1.2, 0.11, 0.06, 19.5, FLARE_YO),
                                       (2.0, 0.8, 0.13, 0.07, 19.5, FLARE_Y)):
            lib.ellipsoid(bm, (ax(36), ay(cy), z), (rx * U, ry * U, rz), sides=16, rings=4,
                          mat_index=m)
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
