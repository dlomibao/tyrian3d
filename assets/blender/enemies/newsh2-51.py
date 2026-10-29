"""Claw, right-hand (newsh2.shp frame 51): a 3D version of its sprite.

Seen in episode 1 (levels 28-30) and episode 3, usually beside newsh2-49 (this claw mirrored left
to right). A hard-surface armoured arm arches from a rounded purple housing at the top left,
through a grey ringed collar and a dark drum, over and down the right side into a purple armour
box (beige L trim), a lattice bay with a diagonal strut, a slanted lower purple plate and a grey
spine rail ending in the point. From under the housing's left end two struts hang to a clevis
knuckle (two cheeks, a pivot bolt) and the glowing red claw tube in its dark red collar. One frame.
Feature list: assets/blender/features/newsh2-51.json.

Coordinates are sprite pixel edges (column c, row r) of the 24x28 block; heights z in sprite px.

Run: blender --background --python assets/blender/enemies/newsh2-51.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-51"
U = 1 / 12


def P(c, r, z=0.0):
    """Pixel-edge coordinates (column, row, height in px) to world."""
    return (lib.ex(c), lib.ey(r), z * U)


def _inset(poly, d):
    """Mitred inset of a CCW 2D polygon by d (world units)."""
    n = len(poly)
    out = []
    for i in range(n):
        a, b, c = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        d0, d1 = (b - a).normalized(), (c - b).normalized()
        n0, n1 = Vector((-d0.y, d0.x)), Vector((-d1.y, d1.x))
        m = n0 + n1
        k = 1.0 + n0.dot(n1)
        off = m / k * d if k > 0.2 else n1 * d
        out.append((b.x + off.x, b.y + off.y))
    return out


def slab(bm, cr, z0, z1, top_mat, side_mat=None, bevel=0.6, bevel_bottom=0.3):
    """A hard-surface plate: the polygon (pixel-edge (c, r) corners) extruded from z0 to z1 px,
    with chamfered top and bottom edges."""
    poly = [(lib.ex(c), lib.ey(r)) for c, r in cr]
    area = sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))
    if area < 0:
        poly.reverse()
    side = top_mat if side_mat is None else side_mat
    bt, bb = bevel * U, bevel_bottom * U
    lo, hi = _inset(poly, bb), _inset(poly, bt)
    rings = [[(x, y, z0 * U) for x, y in lo], [(x, y, z0 * U + bb) for x, y in poly],
             [(x, y, z1 * U - bt) for x, y in poly], [(x, y, z1 * U) for x, y in hi]]
    lib.ring_loft(bm, rings, [side, side, top_mat], cap_mats=(side, top_mat))


def tube_x(bm, c0, c1, r, zc, radii, mat, sides=12, flat=1.0, smooth=True):
    """A round part lying along X from column c0 to c1 at row r: radii (px) at evenly spaced points."""
    n = len(radii)
    pts = [P(c0 + (c1 - c0) * i / (n - 1), r, zc) for i in range(n)]
    lib.polyline_tube(bm, pts, [q * U for q in radii], sides=sides, mat_index=mat, flat=flat, smooth=smooth)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.6, roughness=0.4),  # 0 grey hull
        pal(9, metallic=0.65, roughness=0.3),  # 1 light grey
        pal(90, metallic=0.35, roughness=0.4),  # 2 purple housing
        pal(87, metallic=0.35, roughness=0.45),  # 3 purple armour
        pal(119, emission_strength=3.5),  # 4 red claw
        pal(67, emission_strength=1.5),  # 5 dark red collar
        pal(171, metallic=0.4, roughness=0.35),  # 6 beige trim
        pal(109, metallic=0.6, roughness=0.25),  # 7 pale bolt
        pal(5, metallic=0.55, roughness=0.45),  # 8 dark drum
        pal(2, metallic=0.2, roughness=0.7),  # 9 recess floor
        pal(6, metallic=0.6, roughness=0.4),  # 10 mid grey struts
    ]
    GREY, LIGHT, HOUSING, ARMOUR, RED, DARKRED, BEIGE, BOLT, DRUM, RECESS, STRUT = range(11)
    bm = bmesh.new()

    # Arm hull: a thick armoured beam from under the housing arching right and down under the armour.
    slab(bm, [(5.0, 4.7), (11.0, 4.7), (13.0, 6.3), (18.6, 6.5), (21.4, 9.4), (21.4, 14.2), (14.2, 14.2),
              (13.0, 13.4), (9.8, 9.5), (5.0, 9.1)], -1.6, 2.6, GREY, bevel=0.9, bevel_bottom=0.5)
    # A panel seam step on its top: the inner (lower-left) half is a raised plate.
    slab(bm, [(5.6, 6.6), (9.8, 6.6), (14.0, 11.2), (14.0, 13.0), (13.4, 13.0), (10.0, 9.3), (5.6, 9.0)],
         2.2, 3.1, GREY, bevel=0.5, bevel_bottom=0.1)

    # Purple armour box over the right side, beige L trim on its upper-left corner.
    slab(bm, [(13.8, 9.8), (20.2, 9.6), (21.6, 10.6), (21.6, 17.6), (20.2, 18.4), (16.0, 15.2), (13.8, 14.2)],
         -0.8, 4.0, ARMOUR, bevel=0.9, bevel_bottom=0.4)
    slab(bm, [(13.9, 9.9), (16.2, 9.9), (16.2, 13.4), (15.2, 13.4), (15.2, 10.9), (13.9, 10.9)],
         3.4, 4.3, BEIGE, bevel=0.25, bevel_bottom=0.1)

    # Lattice bay: a dark recessed floor, a grey diagonal strut across it.
    slab(bm, [(14.6, 14.0), (20.0, 17.0), (20.0, 23.4), (18.0, 24.0), (14.6, 18.4)], -1.6, -0.6, RECESS,
         bevel=0.2, bevel_bottom=0.2)
    lib.polyline_tube(bm, [P(15.2, 15.8, 0.4), P(19.6, 20.2, 0.4)], 0.6 * U, sides=6, mat_index=STRUT, smooth=False)
    lib.polyline_tube(bm, [P(16.0, 15.0, 0.0), P(16.0, 17.8, 0.0)], 0.5 * U, sides=6, mat_index=STRUT, smooth=False)
    # Lower purple plate slanting down-right.
    slab(bm, [(14.6, 17.8), (16.6, 18.0), (19.4, 22.0), (19.4, 24.2), (18.0, 24.2), (14.6, 20.6)], -0.8, 2.2,
         ARMOUR, bevel=0.6, bevel_bottom=0.3)
    # Grey spine rail down the right edge, tapering to the point.
    slab(bm, [(19.4, 14.0), (21.6, 14.0), (21.6, 25.6), (21.0, 26.8), (20.2, 26.6), (19.4, 24.0)], -1.2, 1.8,
         GREY, bevel=0.6, bevel_bottom=0.3)

    # Purple housing lying along X at the top left (rounded ends), beige marking near its left end.
    tube_x(bm, 1.2, 8.6, 2.3, 1.6, [0.9, 1.65, 1.95, 1.95, 1.95, 1.9], HOUSING, sides=14, flat=1.15)
    slab(bm, [(2.8, 1.5), (5.0, 1.5), (5.0, 2.7), (2.8, 2.7)], 3.3, 3.85, BEIGE, bevel=0.2, bevel_bottom=0.1)
    # Grey collar with a raised ring.
    tube_x(bm, 8.2, 12.8, 2.3, 1.4, [1.75, 1.75, 1.7], GREY, sides=12, flat=1.1)
    tube_x(bm, 9.0, 10.0, 2.3, 1.4, [2.05, 2.05], LIGHT, sides=12, flat=1.1)
    tube_x(bm, 11.5, 12.3, 2.3, 1.4, [1.95, 1.95], LIGHT, sides=12, flat=1.1)
    # Dark drum right of the collar, above the hull, rounded at its right end.
    tube_x(bm, 12.6, 18.1, 4.3, 2.0, [1.6, 1.85, 1.85, 1.85, 1.6, 0.8], DRUM, sides=14, flat=1.0)

    # Hanging arm: a bracket under the housing's left end, two struts, a cross brace to the hull.
    slab(bm, [(0.2, 3.6), (3.6, 3.6), (3.6, 5.8), (0.2, 5.8)], -1.0, 1.6, GREY, bevel=0.5, bevel_bottom=0.3)
    lib.polyline_tube(bm, [P(1.5, 5.0, 0.4), P(1.5, 13.0, 0.4)], 0.85 * U, sides=8, mat_index=GREY)
    lib.polyline_tube(bm, [P(2.9, 5.0, -0.3), P(2.9, 13.0, -0.3)], 0.65 * U, sides=8, mat_index=STRUT)
    lib.polyline_tube(bm, [P(1.5, 9.0, 0.0), P(2.9, 10.4, -0.3)], 0.4 * U, sides=6, mat_index=STRUT)
    slab(bm, [(2.6, 6.0), (5.6, 6.0), (5.6, 7.0), (2.6, 7.0)], -0.4, 0.8, STRUT, bevel=0.25, bevel_bottom=0.2)
    # Clevis knuckle: two cheeks with a dark slot, a pivot pin and a bolt head.
    slab(bm, [(0.2, 12.2), (2.2, 12.2), (2.2, 16.8), (0.6, 16.8), (0.2, 16.2)], -1.2, 2.2, GREY, bevel=0.5)
    slab(bm, [(3.0, 12.2), (5.2, 12.2), (5.2, 16.2), (4.6, 16.8), (3.0, 16.8)], -1.2, 1.9, GREY, bevel=0.5)
    slab(bm, [(2.1, 12.4), (3.1, 12.4), (3.1, 16.6), (2.1, 16.6)], -1.2, 0.0, RECESS, bevel=0.1, bevel_bottom=0.1)
    tube_x(bm, -0.1, 5.4, 14.5, 0.3, [0.6, 0.6], LIGHT, sides=8)
    lib.polyline_tube(bm, [P(1.4, 14.4, 2.0), P(1.4, 14.4, 2.6)], 0.6 * U, sides=8, mat_index=BOLT)
    # Link, dark red collar, glowing red claw tube and its end cap.
    lib.polyline_tube(bm, [P(3.0, 15.8, 0.3), P(3.0, 18.0, 0.3)], 0.85 * U, sides=8, mat_index=STRUT)
    slab(bm, [(1.6, 17.5), (4.4, 17.5), (4.4, 18.7), (1.6, 18.7)], -1.0, 1.6, DARKRED, bevel=0.3)
    lib.polyline_tube(bm, [P(3.0, 18.4, 0.3), P(3.0, 22.8, 0.3)], 1.05 * U, sides=10, mat_index=RED)
    lib.polyline_tube(bm, [P(3.0, 22.6, 0.3), P(3.0, 23.4, 0.3), P(3.0, 23.9, 0.3)], [0.95 * U, 0.85 * U, 0.4 * U],
                      sides=10, mat_index=DARKRED)

    return [(NAME, [lib.finish(NAME, bm, mats, coll)], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
