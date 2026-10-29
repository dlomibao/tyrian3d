"""Zica Flamethrower (sidekick 17, two-player only; tyrian.shp#8 frames 87, 106, 125, 144): a 3D
version of its sprite.

The sprite is 12x14 px and its four animation frames are pixel-identical, so one model covers
them all. It reads as a small flamethrower drone in steel blue:

- The nozzle: a round barrel 4 px across (columns 4-7) out front, rows 1-7. The sprite's
  alternating light and dark rows (1, 3, 5 light; 2, 4, 6 dark) are rings: a flared muzzle ring
  at row 1 with a dark bore cut into its face, then two raised cooling fins at rows 3 and 5 on a
  slimmer core, and a thick collar at row 7 where it enters the housing.
- The housing: a hard chamfered box 6 px wide (columns 3-8, rows 7-13) behind the nozzle. Its top
  deck is split into plates: two side rails and a centre spine, with two recessed glass windows
  in the spine (rows 8 and 11, columns 5-6) glowing dark red (indices 113/114): the fuel sight
  glasses / pilot lights. The bright column 4 is the deck's lit bevel, not a stripe.
- The fuel tanks: a round tank 3 px across either side (columns 0-2 and 9-11, rows 3-13), as tall
  as it is wide, with a raked nose that tapers forward and inward to a point at row 3 (the
  sprite's stepped diagonal), two dark clamp straps where it bolts to the housing and a dark end
  cap at the back. The bright inner column of each tank is the cylinder's highlight.
- Short round struts (row 5, columns 3 and 8) tie the tanks to the barrel ahead of the housing;
  the gap pixels around them are open space.

Mid-tone palette colours on polished metal (the sprite's highlights are sheen and edge light); the
game's lights shade it.

Run: blender --background --python assets/blender/sidekicks/zica-flamethrower.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "sidekick-zica-flamethrower"
MODEL = "sidekicks/zica-flamethrower"
P = 1 / 12  # one sprite pixel
SHARP = math.radians(38)  # creases sharper than this stay crisp; the rest is smooth shaded

BARREL_Z = 0.8  # barrel axis height, px
TANK_Z = 0.4  # tank axis height, px
TANK_X = 1.5  # left tank axis, column edge (mirrored to 10.5)


def ex(col):
    return (col - 6) * P


def ey(row):
    return (7 - row) * P


def ring_loft(bm, rings, mats, cap_start=True, cap_end=True):
    """Join rings of 3D points (all the same length, or a single point for a tip) with quads.
    mats: one material index per segment, or one for all."""
    loops = [[bm.verts.new(p) for p in r] for r in rings]
    if isinstance(mats, int):
        mats = [mats] * (len(loops) - 1)
    n = max(len(l) for l in loops)
    for k, (l0, l1) in enumerate(zip(loops, loops[1:])):
        for i in range(n):
            j = (i + 1) % n
            if len(l0) == 1:
                f = (l0[0], l1[j], l1[i])
            elif len(l1) == 1:
                f = (l0[i], l0[j], l1[0])
            else:
                f = (l0[i], l0[j], l1[j], l1[i])
            bm.faces.new(f).material_index = mats[k]
    if cap_start and len(loops[0]) > 1:
        bm.faces.new(list(reversed(loops[0]))).material_index = mats[0]
    if cap_end and len(loops[-1]) > 1:
        bm.faces.new(loops[-1]).material_index = mats[-1]


def ellipse(col, row, hw, hh, z, sides):
    """A ring across the Y axis at sprite (col, row), half sizes and height in px."""
    if hw == 0 and hh == 0:
        return [(ex(col), ey(row), z * P)]
    return [(ex(col) + hw * P * math.cos(a), ey(row), (z + hh * math.sin(a)) * P)
            for a in (2 * math.pi * (i + 0.5) / sides for i in range(sides))]


def octagon(col, row, hw, hh, z, c):
    """A chamfered box section across the Y axis, counter-clockwise from the right side."""
    pts = [(hw, -(hh - c)), (hw, hh - c), (hw - c, hh), (-(hw - c), hh), (-hw, hh - c), (-hw, -(hh - c)),
           (-(hw - c), -hh), (hw - c, -hh)]
    return [(ex(col) + u * P, ey(row), (z + v) * P) for u, v in pts]


def box(bm, c0, c1, r0, r1, z0, z1, mat, c=0.25):
    """A chamfered box from column edge c0 to c1, row edge r0 to r1, height z0 to z1 (px)."""
    col, hw, hh, z = (c0 + c1) / 2, (c1 - c0) / 2, (z1 - z0) / 2, (z0 + z1) / 2
    hw2, hh2 = hw - c, hh - c
    ring_loft(bm, [octagon(col, r0, hw2, hh2, z, c * 0.5), octagon(col, r0 + c, hw, hh, z, c),
                   octagon(col, r1 - c, hw, hh, z, c), octagon(col, r1, hw2, hh2, z, c * 0.5)], mat)


def cyl_x(bm, x0, x1, row, z, r, sides, mat):
    """A round strut along X from column edge x0 to x1 at row, axis height z (px)."""
    rings = []
    for x in (x0, x1):
        rings.append([(ex(x), ey(row) + r * P * math.cos(a), (z + r * math.sin(a)) * P)
                      for a in (2 * math.pi * (i + 0.5) / sides for i in range(sides))])
    ring_loft(bm, rings, mat)


def build(sprite):
    coll = common.reset_collection(NAME)
    steel = lambda i, m=0.65, r=0.32: common.palette_material(sprite, i, NAME, metallic=m, roughness=r)  # noqa: E731
    mats = [
        steel(60),  # 0 barrel fins and muzzle ring
        steel(55),  # 1 barrel core
        common.palette_material(sprite, 51, NAME, metallic=0.2, roughness=0.8),  # 2 bore / dark recesses
        steel(57),  # 3 collar
        steel(56),  # 4 housing sides
        steel(58),  # 5 deck rails
        steel(60),  # 6 deck spine (same as fins; separate slot keeps the code readable)
        common.palette_material(sprite, 114, NAME, metallic=0.0, roughness=0.15, emission_strength=1.5),  # 7 glass
        steel(59, 0.7, 0.28),  # 8 tank shell
        steel(53),  # 9 straps
        steel(52),  # 10 end caps, struts
    ]
    FIN, CORE, BORE, COLLAR, SIDE, RAIL, SPINE, GLASS, TANK, STRAP, CAP = range(len(mats))
    bm = bmesh.new()

    # --- The nozzle barrel, axis at column edge 6. (row, radius px, material of the segment after it)
    S = 16
    prof = [
        (1.75, 0.0, BORE), (1.75, 1.05, BORE), (1.0, 1.05, FIN), (1.0, 1.55, FIN), (0.95, 1.8, FIN),
        (1.05, 2.05, FIN), (1.85, 2.05, FIN), (1.95, 1.6, CORE), (2.95, 1.6, FIN), (3.05, 2.05, FIN),
        (3.9, 2.05, FIN), (4.0, 1.6, CORE), (4.95, 1.6, FIN), (5.05, 2.05, FIN), (5.9, 2.05, FIN),
        (6.0, 1.6, CORE), (6.45, 1.6, COLLAR), (6.5, 2.25, COLLAR), (6.6, 2.35, COLLAR),
        (7.6, 2.35, COLLAR), (7.6, 0.0, COLLAR),
    ]
    ring_loft(bm, [ellipse(6, r, rad, rad, BARREL_Z, S) for r, rad, _ in prof], [m for *_, m in prof[:-1]],
              cap_start=False, cap_end=False)

    # --- The housing: a chamfered core, with the deck plates on it and the glass sunk between them.
    core_top = 1.8
    box(bm, 3.0, 9.0, 7.0, 13.95, -1.9, core_top, SIDE, c=0.6)
    deck = 2.5
    box(bm, 3.3, 4.95, 7.25, 13.7, core_top - 0.4, deck, RAIL, c=0.3)  # left rail (lit bevel, column 4)
    box(bm, 7.05, 8.7, 7.25, 13.7, core_top - 0.4, deck, RAIL, c=0.3)  # right rail
    for r0, r1 in ((7.25, 8.0), (9.0, 11.0), (12.0, 13.7)):  # the spine, broken by the two windows
        box(bm, 4.95, 7.05, r0, r1, core_top - 0.4, deck, SPINE, c=0.2)
    for r0 in (8.0, 11.0):  # sight glasses, recessed 0.5 px below the deck
        box(bm, 4.95, 7.05, r0, r0 + 1.0, core_top - 0.4, deck - 0.5, GLASS, c=0.1)
    # A rear exhaust/feed block below the deck at the back, dark.
    box(bm, 4.6, 7.4, 13.6, 14.0, -1.2, 1.2, CAP, c=0.2)

    # --- The fuel tanks. (row, axis column, half width, half height, material after)
    T = 12
    tank = [
        (2.95, 2.75, 0.0, 0.0, TANK), (3.3, 2.5, 0.45, 0.5, TANK), (3.8, 2.15, 0.85, 0.9, TANK),
        (4.4, 1.8, 1.2, 1.25, TANK), (5.0, 1.55, 1.45, 1.45, TANK), (5.5, TANK_X, 1.5, 1.5, TANK),
        (7.55, TANK_X, 1.5, 1.5, STRAP), (7.6, TANK_X, 1.68, 1.68, STRAP), (8.3, TANK_X, 1.68, 1.68, STRAP),
        (8.35, TANK_X, 1.5, 1.5, TANK), (11.55, TANK_X, 1.5, 1.5, STRAP), (11.6, TANK_X, 1.68, 1.68, STRAP),
        (12.3, TANK_X, 1.68, 1.68, STRAP), (12.35, TANK_X, 1.5, 1.5, TANK), (13.0, 1.6, 1.4, 1.45, CAP),
        (13.15, 1.7, 1.15, 1.2, CAP), (13.95, 1.75, 1.0, 1.05, CAP), (13.95, 1.75, 0.0, 0.0, CAP),
    ]
    for side in (-1, 1):
        rings = []
        for r, c, hw, hh, _ in tank:
            col = c if side < 0 else 12 - c
            rings.append(ellipse(col, r, hw, hh, TANK_Z, T))
        ring_loft(bm, rings, [m for *_, m in tank[:-1]], cap_start=False, cap_end=False)
        # The strut from the barrel to the tank at row 5 (columns 3 / 8).
        x0, x1 = (4.4, 2.3) if side < 0 else (7.6, 9.7)
        cyl_x(bm, min(x0, x1), max(x0, x1), 5.5, 0.6, 0.5, 8, CAP)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > SHARP:
            e.smooth = False
    return [common.mesh_object(NAME, bm, mats, coll, smooth=True)]


if __name__ == "__main__":
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, NAME)
    objects = build(sprite)
    common.export_sprite_model(root, objects, MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / NAME / frame["image"]
        common.render_preview(objects, out, ref, size=frame["size"])
