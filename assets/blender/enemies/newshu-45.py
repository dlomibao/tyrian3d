"""Purple pod with twin burners (newshu.shp frames 45, 47, 49, 51): a 3D version of its sprite.

Seen in episode 1 (level section 19) and episode 3. A rounded purple hull, broad in the middle
and coming to a point at the bottom of the sprite (its nose), with a pale dome on top, two glowing
red slits across its back, pink knobs at the shoulders and a groove with two red rails down the
nose. At the top a dark housing holds two burners whose flames rise out of it. The frames only
change the flames and the slits' glow, so one model covers them all and animates: each frame has
its own pair of flames (common.frame_part), short and dim on 45, longer on 47, a big flaring crown
on 49 and side licks on 51, and the slits, their lips and the lamp brighten from frame to frame
(common.palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshu-45.py [-- --preview out.png]
[--frames out.png] (--frames renders every frame beside its sprite).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshu-45"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def px(x):
    """Sprite column (pixel centre) to Blender X."""
    return (x + 0.5 - 12) / 12


def row(r):
    """Sprite row (pixel centre) to Blender Y."""
    return (14 - (r + 0.5)) / 12


def edge(r):
    """Sprite row boundary (r = top edge of row r) to Blender Y."""
    return (14 - r) / 12


# Hull, top of the sprite to the nose: (row boundary, half width px, half height, z centre).
HULL = [(10.6, 0.0, 0.0, 0.06), (10.9, 6.5, 0.1, 0.06), (11.6, 8.0, 0.15, 0.05), (13.0, 8.6, 0.2, 0.04),
        (14.0, 10.0, 0.27, 0.03), (15.0, 10.9, 0.3, 0.02), (17.0, 11.2, 0.31, 0.0), (19.5, 11.2, 0.3, 0.0),
        (21.0, 10.6, 0.27, 0.0), (22.0, 9.8, 0.24, 0.0), (23.0, 8.8, 0.2, 0.0), (24.0, 7.3, 0.16, 0.0),
        (25.0, 5.8, 0.13, 0.0), (26.0, 3.8, 0.1, 0.0), (27.0, 2.0, 0.07, 0.0), (27.9, 0.0, 0.0, 0.0)]


def hull_top(r, x=0.0):
    """Height of the hull's top surface at row boundary r and Blender X (elliptic across)."""
    import math
    for (r0, w0, h0, z0), (r1, w1, h1, z1) in zip(HULL, HULL[1:]):
        if r0 <= r <= r1:
            t = (r - r0) / (r1 - r0)
            w, h, z = (w0 + (w1 - w0) * t) / 12, h0 + (h1 - h0) * t, z0 + (z1 - z0) * t
            q = 1 - (x / w) ** 2 if w > 0 else 0
            return z + h * math.sqrt(max(q, 0.0))
    return 0.0


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(86, metallic=0.45, roughness=0.4),  # 0 hull purple
        pal(82, metallic=0.4, roughness=0.5),  # 1 dark burner housing
        pal(72, metallic=0.35, roughness=0.45),  # 2 pinkish-red band and knobs
        pal(93, metallic=0.3, roughness=0.15),  # 3 pale dome
        pal(116, emission_strength=3.5),  # 4 red slits and lamp
        pal(117, emission_strength=4.0),  # 5 flames
        pal(120, emission_strength=5.0),  # 6 flame cores
        pal(71, metallic=0.35, roughness=0.45),  # 7 nose rails
        pal(66, metallic=0.2, roughness=0.7),  # 8 dark groove
        pal(96, metallic=0.1, roughness=0.6),  # 9 nose slot
        pal(65, metallic=0.2, roughness=0.6),  # 10 dark centre of the band
        pal(115, emission_strength=3.5),  # 11 dim flames
        pal(118, emission_strength=4.5),  # 12 flame cores (47, 51)
        pal(121, emission_strength=5.5),  # 13 white-hot flame cores (49)
        pal(114, emission_strength=3.0),  # 14 flame licks
        # Animated glows: the slits brighten from red to orange, their dark lips light up and the
        # lamp is off on frame 45.
        common.palette_material(sprite, 114, f"{NAME}-slit", emission_strength=3.5,
                                frames={47: 115, 49: 117, 51: 121}),  # 15 slit ends, short slit
        common.palette_material(sprite, 116, f"{NAME}-slitcore", emission_strength=3.5,
                                frames={49: 118, 51: 122}),  # 16 long slit's centre
        common.palette_material(sprite, 114, f"{NAME}-lip", emission_strength=3.0,
                                frames={45: 1, 49: 116, 51: 118}),  # 17 slit lips
        common.palette_material(sprite, 114, f"{NAME}-lamp", emission_strength=3.5,
                                frames={45: 1}),  # 18 lamp
    ]
    (HULLM, HOUSING, BAND, DOME, SLIT, FLAME, CORE, RAIL, GROOVE, SLOT, BANDDARK, DIM, HOTTER, HOTTEST, LICK,
     SLIT_A, SLIT_B, LIP, LAMP) = range(19)
    bm = bmesh.new()

    common.loft(bm, [(edge(r), w / 12, h, z) for r, w, h, z in HULL], sides=18, mat_index=HULLM)

    # Band across the top of the hull (rows 9-10), dark in the middle between the burners.
    common.loft(bm, [(edge(8.8), 4.9 / 12, 0.07, 0.1), (edge(9.2), 5.0 / 12, 0.09, 0.1),
                     (edge(10.6), 5.0 / 12, 0.1, 0.09), (edge(11.4), 4.6 / 12, 0.08, 0.08)],
                sides=12, mat_index=BAND)
    common.slab(bm, [(px(10.4), edge(10.0)), (px(12.6), edge(10.0)), (px(12.6), edge(8.9)), (px(10.4), edge(8.9))],
                0.04, z=0.19, mat_index=BANDDARK)

    # Burner housing: side walls (columns 7 and 16) and the divider between the burners (11-12).
    for c0, c1, r0 in ((7, 8, 4.9), (16, 17, 4.9), (11, 13, 4.9)):
        r1 = 9.2 if c0 != 11 else 7.2
        common.slab(bm, [(px(c0 - 0.5), edge(r1)), (px(c1 - 0.5), edge(r1)), (px(c1 - 0.5), edge(r0)),
                         (px(c0 - 0.5), edge(r0))], 0.26, z=0.08, mat_index=HOUSING)
    # Housing floor under the burners.
    common.slab(bm, [(px(6.6), edge(9.2)), (px(16.4), edge(9.2)), (px(16.4), edge(5.5)), (px(6.6), edge(5.5))],
                0.05, z=-0.04, mat_index=HOUSING)

    # Pink knobs at the shoulders (rows 11-13, columns 5-6 and 17-18).
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [(edge(13.4), 0.0, 0.0, 0.14), (edge(12.8), 1.0 / 12, 0.05, 0.15),
                         (edge(11.6), 1.1 / 12, 0.055, 0.15), (edge(11.0), 0.0, 0.0, 0.14)],
                    sides=8, mat_index=BAND)
        common.shift_x(bm, start, side * 6.6 / 12)

    # Pale dome on top (rows 11-13, columns 9-14) with a red lamp just below it.
    z = hull_top(12.5)
    common.loft(bm, [(edge(14.0), 0.0, 0.0, z - 0.02), (edge(13.5), 2.2 / 12, 0.07, z - 0.01),
                     (edge(12.5), 2.8 / 12, 0.09, z), (edge(11.4), 2.2 / 12, 0.07, z - 0.01),
                     (edge(10.9), 0.0, 0.0, z - 0.02)], sides=12, mat_index=DOME)
    z = hull_top(13.5)
    common.loft(bm, [(edge(14.0), 0.0, 0.0, z + 0.01), (edge(13.5), 0.9 / 12, 0.035, z + 0.02),
                     (edge(13.0), 0.0, 0.0, z + 0.01)], sides=8, mat_index=LAMP)

    # The two red slits across the back (row 15, columns 11-12; row 17, columns 10-13; the long
    # one's centre is brighter).
    for r, half in ((15, 1.0), (17, 2.0)):
        z = hull_top(r + 0.5)
        common.slab(bm, [(-half / 12, edge(r + 1)), (half / 12, edge(r + 1)), (half / 12, edge(r)), (-half / 12, edge(r))],
                    0.05, z=z, mat_index=SLIT_A)
        if r == 17:
            common.slab(bm, [(-1 / 12, edge(r + 1)), (1 / 12, edge(r + 1)), (1 / 12, edge(r)), (-1 / 12, edge(r))],
                        0.05, z=z + 0.003, mat_index=SLIT_B)
        # Lips either side of each slit: dark on frame 45, lit on the others.
        for side in (-1, 1):
            x0, x1 = sorted((side * half / 12, side * (half + 1) / 12))
            common.slab(bm, [(x0, edge(r + 1)), (x1, edge(r + 1)), (x1, edge(r)), (x0, edge(r))], 0.04, z=z - 0.005,
                        mat_index=LIP)

    # Groove down the nose with two red rails (rows 19-25, columns 10-13).
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [(edge(24.2), 0.0, 0.0, hull_top(24.2, 1.5 / 12)),
                         (edge(23.0), 0.5 / 12, 0.03, hull_top(23.0, 1.5 / 12)),
                         (edge(20.0), 0.55 / 12, 0.035, hull_top(20.0, 1.5 / 12)),
                         (edge(19.6), 0.0, 0.0, hull_top(19.6, 1.5 / 12))], sides=6, mat_index=RAIL)
        common.shift_x(bm, start, side * 1.5 / 12)
    for r0, r1, mat, half in ((19.2, 24.0, GROOVE, 1.0), (23.8, 26.0, SLOT, 1.0)):
        zm = hull_top((r0 + r1) / 2)
        common.slab(bm, [(-half / 12, edge(r1)), (half / 12, edge(r1)), (half / 12, edge(r0)), (-half / 12, edge(r0))],
                    0.03, z=zm - 0.005, mat_index=mat)

    parts = [common.mesh_object(NAME, bm, mats, coll, smooth=True)]

    # Flames rising from the burners (columns 8-10 and 13-15) out of the housing, one pair per
    # frame: (frame, main flame (tip row edge, half width px, material), core (tip, half width,
    # material), outer lick (start column, tip column, tip row edge) or None, flame between the
    # burners (tip row edge) or None).
    frames = [
        (45, (3.9, 1.5, DIM), (6.4, 0.7, FLAME), None, None),
        (47, (1.9, 1.5, DIM), (4.4, 0.75, HOTTER), None, None),
        (49, (0.9, 2.0, FLAME), (3.4, 1.1, HOTTEST), (7.4, 4.0, 2.9), 5.6),
        (51, (1.9, 1.6, DIM), (4.4, 0.8, HOTTER), (7.4, 5.0, 4.6), None),
    ]
    for frame, main, core, lick, middle in frames:
        fbm = bmesh.new()
        for c, side in ((9, -1), (14, 1)):
            flame(fbm, px(c), 9.0, main[0], main[1], 0.075, 0.07, 0.1, main[2])
            flame(fbm, px(c), 8.6, core[0], core[1], 0.045, 0.1, 0.12, core[2])
            if lick:
                c0, c1, tip = lick
                x0 = px(11.5 + side * (11.5 - c0))
                x1 = px(11.5 + side * (11.5 - c1))
                flame(fbm, x0, 8.8, tip, 0.9, 0.05, 0.22, 0.28, LICK, lean=x1 - x0)
        if middle:
            flame(fbm, 0.0, 9.0, middle, 1.4, 0.06, 0.3, 0.32, FLAME)
        parts.append(common.frame_part(common.mesh_object(f"{NAME}-flame-{frame}", fbm, mats, coll, smooth=True),
                                       [frame]))
    return parts


# A flame's half width along its length (0 at the burner, 1 at the tip), from the burner out.
FLAME_PROFILE = [(0.0, 0.0), (0.08, 0.93), (0.33, 1.0), (0.59, 0.67), (0.84, 0.3), (1.0, 0.0)]


def flame(bm, x, base, tip, half_w, half_h, z0, z1, mat, lean=0.0):
    """A flame from row edge `base` up to row edge `tip` at Blender X `x`, rising from z0 to z1 and
    leaning `lean` along X by its tip."""
    start = len(bm.verts)
    y0, y1 = edge(base), edge(tip)
    common.loft(bm, [(y0 + (y1 - y0) * t, half_w / 12 * w, half_h * w, z0 + (z1 - z0) * t)
                     for t, w in FLAME_PROFILE], sides=8, mat_index=mat)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        t = (v.co.y - y0) / (y1 - y0)
        v.co.x += x + lean * t


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objects = build(sprite)
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview(objects, out, ref, size=sprite["frames"][0]["size"], frame=sprite["frames"][0]["index"])
    if "--frames" in sys.argv:
        common.render_frame_previews(objects, sys.argv[sys.argv.index("--frames") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
