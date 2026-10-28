"""Grey twin-blade fighter (newshm.shp frames 89, 91, 93): a 3D version of its sprite.

Seen in episode 2 (levels 2.10 and 2.19). It flies nose down the screen: two long grey blades
side by side, each a round prong tube with a bright ridge along its inner edge, tapering to a
round tip at the bottom with a gap between them, and a flat bevelled wing plate beside it at the
shoulders, a groove between the two. A dark channel with two light rungs runs
between the shoulders, cut well below them, and an engine between two grey nozzle cheeks at the
back (top of the sprite) blows a flame: a yellow-white core inside an orange-red bulb with a thin
dark-red rim. The three frames only change the flame's length (its tip reaches rows 5, 4 and 3),
so one model covers them all, with a flame per frame (common.frame_part).

The blades reach out over the sprite's 1 px black outline as a bevel in the blade's own grey (the
game draws the dark outline), along a smooth line through the outline's pixel steps, so the top
view covers the sprite's whole outline. The hull is polished metal: mid-tone greys, metallic and
smooth, so the game's lights make the sprite's highlights and shading.

Run: blender --background --python assets/blender/enemies/newshm-89.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b016 as lib  # noqa: E402

NAME = "newshm-89"
# Each frame's flame: (frame, tip row edge, lift px, height scale).
FLAME_FRAMES = [(89, 5.05, 0.5, 1.0), (91, 4.05, 0.25, 0.85), (93, 3.05, 0.0, 0.74)]
P = 1 / 12  # one sprite pixel
CENTRE = lib.px(12)  # the sprite is symmetric about column 12
INNER = 11.75  # the left blade's inner edge (column edge); it covers the outline column 11


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


LIP = 0.45  # the dark inner lip beside the slot (the sprite's outline column 11)
ARC = [math.radians(a) for a in (0, 36, 72, 108, 144, 180)]


def blade_top(w, e):
    """Top of a blade from its inner edge outward, in px (profile_blade scales by 1 px): a round
    prong tube `wt` px wide standing `zt` px tall, a 1 px groove beside it, then a flat wing plate
    `hp` px tall with a lit bevel and a dark outline bevel at the outer edge. Where the blade is
    too narrow for a plate (down the prong) the plate points fold into the tube's outer flank."""
    wt, zt, hp = e[0], e[1], e[2]
    rt = (wt - LIP) / 2
    rz = min(rt, zt - 0.4)
    zc = zt - rz
    pts = [(LIP * (a > 0) + rt * (1 - math.cos(a)), zc + rz * math.sin(a)) for a in ARC]
    edge = (w, 0.6)
    s = min(1.0, max(0.0, (w - wt - 1.9) / 1.0))
    folded = [_lerp((wt, zc), edge, t) for t in (0.2, 0.4, 0.6, 0.8)]
    plate = [(wt + 0.25, hp - 0.9), (wt + 0.6, hp), (w - 1.6, hp), (w - 0.85, hp - 0.35)]
    pts += [_lerp(f, q, s) for f, q in zip(folded, plate)]
    pts.append(edge)
    return pts


def blade_bottom(w, e):
    hb = e[3]
    return [(d, max(0.2, hb * (1 - (d / w) ** 2))) for d, _ in blade_top(w, e)]


def build(sprite):
    coll = common.reset_collection(NAME)
    grey = lambda i: common.palette_material(sprite, i, NAME, metallic=0.75, roughness=0.3)  # polished metal  # noqa: E731
    idx = [3, 8, 9, 10, 11, 12, 113]
    mats = [grey(i) for i in idx]
    M = {i: k for k, i in enumerate(idx)}
    FLAME, MID, CORE, YEL, HOT, WHITE = range(len(mats), len(mats) + 6)
    mats += [
        common.palette_material(sprite, 114, NAME, emission_strength=3.0),  # dark-red flame shell
        common.palette_material(sprite, 117, NAME, emission_strength=5.0),  # bright red band
        common.palette_material(sprite, 123, NAME, emission_strength=6.0),  # orange core
        common.palette_material(sprite, 124, NAME, emission_strength=7.0),  # yellow centre stripe
        common.palette_material(sprite, 126, NAME, emission_strength=8.0),  # white-yellow centre
        common.palette_material(sprite, 127, NAME, emission_strength=9.0),  # white-hot at the nozzle
    ]
    bm = bmesh.new()

    # Each blade in six lofts along its length, so each gets the palette shades of its own sprite
    # rows: the nose (rows 9-10, darkened red by the exhaust), the brow (10-11), the lit front
    # edge (11-11.8), the shoulder (11.8-16), the prong (16-19.6) and the tip (19.6-27).
    # Sections: (row edge, outer column edge, tube width px, tube top px, plate top px,
    # underside depth px). The outer edge is a smooth line through the sprite outline's steps
    # (within half a pixel of each), not the steps themselves. The prong tube runs from the inner
    # edge over columns 8-11 (7-11 down the prong, narrowing to the tip), stands 5.3 px at the
    # shoulders and tapers to about 1.5 px at its round tip; the wing plate beside it is flat at
    # 3 px with a groove between them.
    nose = [(9.0, 8.3, 2.65, 2.8, 2.2, 0.6), (9.6, 7.0, 3.75, 3.6, 2.6, 0.9), (10.0, 6.5, 3.75, 3.9, 2.75, 1.05)]
    brow = [(10.0, 6.5, 3.75, 3.9, 2.75, 1.05), (10.4, 6.0, 3.75, 4.2, 2.9, 1.2), (11.0, 5.33, 3.75, 4.75, 3.0, 1.33)]
    front = [(11.0, 5.33, 3.75, 4.75, 3.0, 1.33), (11.3, 5.0, 3.75, 5.0, 3.0, 1.4), (11.8, 4.45, 3.75, 5.2, 3.0, 1.45)]
    shoulder = [
        (11.8, 4.45, 3.75, 5.2, 3.0, 1.45), (12.1, 4.05, 3.75, 5.3, 3.0, 1.5), (14.8, 4.05, 3.75, 5.3, 3.0, 1.5),
        (15.4, 5.0, 4.2, 5.2, 2.9, 1.45), (16.0, 6.0, 4.9, 5.0, 2.8, 1.4),
    ]
    prong = [(16.0, 6.0, 4.9, 5.0, 2.8, 1.4), (18.6, 6.43, 4.9, 4.6, 2.6, 1.3), (19.6, 6.7, 4.1, 4.4, 2.4, 1.2)]
    tip = [
        (19.6, 6.7, 4.1, 4.4, 2.4, 1.2), (22.0, 7.5, 3.3, 3.7, 2.0, 1.0), (24.0, 8.5, 2.3, 3.1, 1.8, 0.8),
        (26.0, 9.5, 1.5, 2.5, 1.5, 0.6), (26.6, 9.95, 1.1, 2.1, 1.3, 0.5), (27.0, 10.4, 0.7, 1.5, 1.0, 0.4),
    ]
    # Top strips inner to outer: inner lip, ridge, tube top, tube outer flank (2), groove, groove
    # wall, plate, lit bevel, outline bevel. The sprite draws its light: the left blade lit (white
    # ridge), the right one shaded, a dark outline ring round both. The game lights the model and
    # draws its own outline, so both blades take the same mid-tone grey of their rows (the
    # average of the sprite's lit and shaded sides), with the ridge one step lighter as its trim;
    # the bright streak along it is the metal's shine. The nose is tinted dark red by the exhaust.
    strips = {
        "nose": [113, 10, 113, 113, 113, 9, 9, 9, 9, 9],
        "brow": [8, 10, 9, 9, 9, 9, 9, 9, 9, 9],
        "front": [9, 11, 10, 10, 10, 10, 10, 10, 10, 10],
        "shoulder": [8, 10, 9, 9, 9, 9, 9, 9, 9, 9],
        "prong": [8, 10, 8, 8, 8, 8, 8, 8, 8, 8],
        "tip": [8, 9, 8, 8, 8, 8, 8, 8, 8, 8],
    }
    parts = (("nose", nose), ("brow", brow), ("front", front), ("shoulder", shoulder), ("prong", prong), ("tip", tip))
    for side in (1, -1):
        for part, secs in parts:
            blade = [(lib.ey(r), lib.ex(INNER), lib.ex(xo), P, P, (wt, zt, hp, hb)) for r, xo, wt, zt, hp, hb in secs]
            lib.profile_blade(bm, blade, blade_top, blade_bottom, [M[i] for i in strips[part]],
                              side=side, mirror_about=CENTRE, under_mat=M[8])

    # The dark channel between the shoulders (rows 11-16, column 12), its floor about 1.5 px up,
    # 3 px below the ridges, with two light rungs across it (rows 12 and 14) standing 1.3 px
    # above the floor.
    x0, x1 = lib.ex(11.4), lib.ex(13.6)
    common.slab(bm, [(x0, lib.ey(16.6)), (x1, lib.ey(16.6)), (x1, lib.ey(10.8)), (x0, lib.ey(10.8))],
                2.6 * P, z=0.2 * P, mat_index=M[3])
    for r in (12, 14):
        y0, y1 = lib.ey(r + 1) + 0.12 * P, lib.ey(r) - 0.12 * P
        common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 1.2 * P, z=2.2 * P, mat_index=M[12])

    # Grey nozzle cheeks either side of the engine (columns 10 and 14, rows 8-10): upright
    # rounded posts about 4.8 px tall, above the flame's shell.
    for side, mat in ((1, M[10]), (-1, M[10])):
        start = len(bm.verts)
        common.loft(bm, [(lib.ey(10.9), 0.65 * P, 2.4 * P, 2.4 * P), (lib.ey(9.0), 0.65 * P, 2.4 * P, 2.4 * P),
                         (lib.ey(8.0), 0.5 * P, 1.9 * P, 2.2 * P)], sides=8, mat_index=mat)
        common.shift_x(bm, start, CENTRE - side * 2 * P)

    body = common.mesh_object(NAME, bm, mats, coll, smooth=True)

    # The flame, from inside the nozzle (row 10.8) out past the back to its tip (row 5 on frame
    # 89, 4 on 91, 3 on 93): nested glowing cones, each standing above the one around it so the
    # top view shows the sprite's rings: a dark-red shell 7 px wide at rows 7-10 narrowing to its
    # 1 px tip (rows 5-6); a bright red band that shows at row 7; the 3 px orange core (rows
    # 8-10, pointed at row 7); a yellow centre stripe down column 12, white-yellow at row 9 and
    # white-hot at row 10, the highest part (5.5 px). Sections are (row edge, half width px,
    # half height px, z centre px).
    flames = [
        (FLAME, [(10.8, 2.8, 1.5, 2.0), (9.6, 3.6, 1.8, 2.0), (8.4, 3.5, 1.8, 2.0), (7.4, 3.2, 1.5, 1.9),
                 (6.6, 1.7, 1.2, 2.2), (5.6, 0.6, 0.7, 1.9), (5.05, 0.0, 0.0, 1.7)], 10),
        (MID, [(10.8, 2.4, 1.0, 3.0), (8.4, 2.6, 1.1, 3.0), (7.6, 2.5, 1.0, 3.0), (7.1, 1.6, 0.7, 2.9),
               (6.95, 0.0, 0.0, 2.8)], 10),
        (CORE, [(10.8, 1.6, 1.0, 3.8), (8.2, 1.6, 1.0, 3.8), (7.8, 1.0, 0.8, 3.8), (7.3, 0.45, 0.5, 3.7),
                (6.95, 0.0, 0.0, 3.6)], 10),
        (YEL, [(10.8, 0.8, 0.6, 4.4), (8.15, 0.8, 0.6, 4.4), (7.95, 0.0, 0.0, 4.4)], 8),
        (HOT, [(10.0, 0.8, 0.5, 4.8), (9.1, 0.8, 0.5, 4.8), (8.95, 0.0, 0.0, 4.8)], 8),
        (WHITE, [(10.8, 0.85, 0.5, 5.0), (10.05, 0.8, 0.5, 5.0), (9.9, 0.0, 0.0, 5.0)], 8),
    ]
    parts = [body]
    # The longer flames are a little flatter and lower (FLAME_FRAMES), as a flame thins when it
    # stretches, so a view showing every frame at once (the review sheet) sees frame 89's flame
    # on top where it reaches; in game only one shows at a time.
    for frame, tip, lift, zs in FLAME_FRAMES:
        k = (10.8 - tip) / (10.8 - 5.05)
        fbm = bmesh.new()
        for mat, secs, sides in flames:
            start = len(fbm.verts)
            common.loft(fbm, [(lib.ey(10.8 - (10.8 - r) * k), w * P, h * zs * P, (z * zs + lift) * P)
                              for r, w, h, z in secs], sides=sides, mat_index=mat)
            common.shift_x(fbm, start, CENTRE)
        parts.append(common.frame_part(common.mesh_object(f"{NAME}-flame-{frame}", fbm, mats, coll, smooth=True), [frame]))
    return parts


if __name__ == "__main__":
    lib.run(NAME, lambda sprite: [(NAME, build(sprite), sprite["sprites"])], __file__)
