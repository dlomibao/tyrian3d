"""Claw, right-hand (newsh2.shp frame 51): a 3D version of its sprite.

Seen in episode 1 (levels 28-30) and episode 3, usually beside newsh2-49 (this claw mirrored left
to right). A hard-surface armoured arm arches from a rounded purple housing at the top left,
through a grey ringed collar and a dark drum, over and down the right side into a purple armour
box (beige L trim), a lattice bay with a diagonal strut, a slanted lower purple plate and a grey
spine rail ending in the point. From under the housing's left end two struts hang to a clevis
knuckle (two cheeks, a pivot bolt) and the glowing red claw tube in its dark red collar. One frame.
Feature list: assets/blender/features/newsh2-51.json.

Remodelled after the concept (assets/blender/textures/newsh2-51/concept.png, registered to the sprite
by tools/concept_maps.py): every part is traced where the concept draws it, so the baked detail
(texture_bake.py) lands on the matching part, with the outline kept inside the sprite's.

Coordinates are sprite pixel edges (column c, row r) of the 24x28 block; heights z in sprite px.

Run: blender --background --python assets/blender/enemies/newsh2-51.py [-- --preview out.png]
"""

import math
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


def pod_x(bm, stations, mat, sides=16, flat=1.0):
    """A round part lying along X: stations (column, row of its axis, height of its axis px, radius px)."""
    pts = [P(c, r, z) for c, r, z, _ in stations]
    lib.polyline_tube(bm, pts, [q * U for *_, q in stations], sides=sides, mat_index=mat, flat=flat, smooth=True)


def shell_patch(bm, c0, c1, r, zc, rad, a0, a1, mat, flat=1.0, lift=0.18, thick=0.35, n=5):
    """A thin curved plate wrapped on a round part along X (axis at row r, height zc, radius rad px),
    from column c0 to c1, between angles a0..a1 (degrees; 0 = toward the screen top, 90 = up)."""
    rings = []
    for c in (c0, c1):
        ring = []
        for rr in (rad + lift + thick, rad + lift):
            angs = [a0 + (a1 - a0) * i / (n - 1) for i in range(n)]
            if rr != rad + lift + thick:
                angs = angs[::-1]
            for a in angs:
                t = math.radians(a)
                ring.append(P(c, r - rr * math.cos(t), zc + rr * flat * math.sin(t)))
        rings.append(ring)
    lib.ring_loft(bm, rings, mat)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.55, roughness=0.45),  # 0 grey hull
        pal(9, metallic=0.6, roughness=0.35),  # 1 light grey (rings, pins)
        pal(90, metallic=0.3, roughness=0.45),  # 2 purple housing
        pal(87, metallic=0.3, roughness=0.5),  # 3 purple armour
        pal(119, metallic=0.0, roughness=0.15, emission_strength=3.5),  # 4 red claw (glowing glass)
        pal(67, metallic=0.4, roughness=0.4, emission_strength=0.6),  # 5 dark red clamp and caps
        pal(171, metallic=0.35, roughness=0.4),  # 6 beige trim
        pal(109, metallic=0.7, roughness=0.2),  # 7 pale bolt heads
        pal(5, metallic=0.6, roughness=0.25),  # 8 dark drum (glossy black metal)
        pal(2, metallic=0.1, roughness=0.8),  # 9 recess floors
        pal(6, metallic=0.55, roughness=0.4),  # 10 mid grey struts and rails
    ]
    GREY, LIGHT, HOUSING, ARMOUR, RED, DARKRED, BEIGE, BOLT, DRUM, RECESS, STRUT = range(11)
    bm = bmesh.new()

    # --- Arm hull: the heavy grey beam arching from under the housing to the right, traced from the
    # concept (its inner edge widened to the sprite's outline ring). A chamfered slab, three raised
    # top plates split by the concept's seams, a lower lip along the inner curve.
    slab(bm, [(5.2, 4.1), (12.8, 4.1), (19.0, 4.2), (19.0, 7.0), (20.6, 9.4), (20.4, 11.6), (14.6, 11.6), (13.8, 14.1),
              (12.0, 12.4), (10.0, 10.4), (8.0, 8.9), (5.2, 8.0)], -2.2, 2.4, GREY, bevel=0.8, bevel_bottom=0.5)
    slab(bm, [(5.8, 4.6), (8.6, 4.6), (8.6, 7.4), (5.8, 6.7)], 1.8, 3.6, GREY, bevel=0.45, bevel_bottom=0.1)
    slab(bm, [(8.9, 4.6), (12.6, 4.6), (13.2, 6.3), (11.3, 8.8), (10.2, 8.9), (8.9, 7.6)], 1.8, 3.6, GREY,
         bevel=0.45, bevel_bottom=0.1)
    slab(bm, [(11.7, 9.2), (13.6, 6.6), (17.6, 6.6), (19.4, 9.6), (13.6, 9.6), (13.6, 11.6), (12.6, 10.8)],
         1.8, 3.6, GREY, bevel=0.45, bevel_bottom=0.1)

    # --- Top housing: the long purple capsule across the top left (its blunt nose drooping at the
    # left end), a dark ring, then the grey ribbed segment narrowing into the drum.
    HZ = 3.4
    pod_x(bm, [(0.2, 2.9, HZ - 0.4, 0.45), (0.6, 2.8, HZ - 0.2, 1.0), (1.4, 2.5, HZ, 1.45), (2.6, 2.15, HZ, 1.8),
               (4.4, 1.95, HZ, 1.95), (6.4, 1.9, HZ, 1.95), (8.4, 1.9, HZ, 1.9)], HOUSING, flat=1.05)
    shell_patch(bm, 2.1, 4.5, 1.95, HZ, 1.9, 35, 88, BEIGE, flat=1.05, lift=0.0, thick=0.3)
    pod_x(bm, [(8.25, 1.9, HZ, 1.95), (8.85, 1.9, HZ, 1.95)], DRUM, flat=1.05)
    pod_x(bm, [(8.8, 1.9, HZ, 2.0), (9.3, 1.9, HZ, 2.0)], LIGHT, flat=1.05)
    pod_x(bm, [(9.2, 1.9, HZ, 1.85), (11.2, 1.85, HZ, 1.8), (12.4, 2.0, HZ - 0.2, 1.5), (13.4, 2.3, HZ - 0.6, 0.8)],
          GREY, flat=1.05)
    # Dark drum right of the collar, on top of the arch, rounded at its right end.
    DZ = 4.0
    pod_x(bm, [(12.3, 4.2, DZ, 1.0), (13.0, 4.2, DZ, 1.2), (13.4, 4.15, DZ, 1.8), (14.4, 4.15, DZ, 1.95),
               (16.4, 4.15, DZ, 1.95), (17.4, 4.15, DZ, 1.75), (18.0, 4.15, DZ, 1.2), (18.25, 4.15, DZ, 0.4)],
          DRUM, flat=1.0)

    # --- Hanging arm: a grey bracket plate under the housing's nose, a cross beam to the hull with a
    # diagonal brace, two vertical bars (lit left bar, darker frame bar) down to the knuckle, a dark
    # bay behind the open lattice.
    slab(bm, [(0.2, 3.9), (5.4, 3.9), (5.4, 8.6), (3.9, 8.9), (3.9, 12.6), (0.2, 12.6)], -2.6, -1.8, RECESS, bevel=0.15, bevel_bottom=0.1)
    slab(bm, [(0.1, 4.2), (1.6, 4.2), (1.6, 8.8), (0.6, 8.8), (0.1, 8.2)], -1.6, 2.4, GREY, bevel=0.45)
    lib.polyline_tube(bm, [P(1.85, 4.6, 2.2), P(1.85, 4.6, 2.9)], 0.45 * U, sides=8, mat_index=BOLT)
    slab(bm, [(1.5, 4.9), (5.4, 4.9), (5.4, 6.3), (1.5, 6.3)], -0.6, 1.6, STRUT, bevel=0.35, bevel_bottom=0.2)
    lib.polyline_tube(bm, [P(2.3, 7.4, 0.3), P(4.6, 6.1, 0.3)], 0.35 * U, sides=6, mat_index=STRUT, smooth=False)
    lib.polyline_tube(bm, [P(1.4, 5.0, 0.6), P(1.4, 13.2, 0.6)], 0.6 * U, sides=8, mat_index=GREY)
    lib.polyline_tube(bm, [P(2.3, 6.2, 0.1), P(2.3, 13.0, 0.1)], 0.42 * U, sides=8, mat_index=STRUT)
    lib.polyline_tube(bm, [P(0.6, 8.6, -0.2), P(0.6, 14.0, -0.2), P(1.1, 15.6, -0.2)], 0.38 * U, sides=8,
                      mat_index=STRUT)
    for r in (9.2, 11.6):
        lib.polyline_tube(bm, [P(0.6, r, -0.2), P(2.3, r + 0.6, 0.1)], 0.25 * U, sides=6, mat_index=STRUT,
                          smooth=False)

    # --- Knuckle: a clevis of two cheeks with a dark slot between, a pivot pin through both and bolt heads.
    slab(bm, [(2.3, 12.5), (5.1, 12.5), (5.6, 13.0), (5.6, 16.4), (5.1, 16.9), (2.3, 16.9)], -1.4, 2.6, GREY,
         bevel=0.5)
    slab(bm, [(0.2, 13.4), (2.0, 13.4), (2.0, 17.0), (0.7, 17.0), (0.2, 16.4)], -1.4, 2.2, GREY, bevel=0.5)
    slab(bm, [(1.9, 13.0), (2.4, 13.0), (2.4, 16.8), (1.9, 16.8)], -1.4, 0.4, RECESS, bevel=0.1, bevel_bottom=0.1)
    tube_x(bm, 0.0, 5.8, 14.6, 0.6, [0.55, 0.55], LIGHT, sides=8)
    lib.polyline_tube(bm, [P(4.1, 13.3, 2.4), P(4.1, 13.3, 3.0)], 0.4 * U, sides=8, mat_index=BOLT)
    lib.polyline_tube(bm, [P(1.4, 14.5, 2.0), P(1.4, 14.5, 2.6)], 0.55 * U, sides=8, mat_index=BOLT)

    # --- Claw: a dark red collar, the glowing red tube hanging from it, a dark red finned clamp on its
    # right side and a tapered end cap.
    slab(bm, [(0.6, 16.7), (4.9, 16.7), (4.9, 17.9), (0.9, 17.9)], -1.0, 2.0, DARKRED, bevel=0.35)
    lib.polyline_tube(bm, [P(2.15, 17.6, 0.5), P(2.15, 22.9, 0.5)], 0.9 * U, sides=10, mat_index=RED)
    slab(bm, [(3.0, 17.8), (4.9, 17.8), (4.9, 21.6), (4.3, 22.8), (3.0, 22.8)], -0.8, 1.4, DARKRED, bevel=0.3)
    for r in (18.4, 19.2):
        slab(bm, [(3.4, r), (4.8, r), (4.8, r + 0.35), (3.4, r + 0.35)], 1.2, 1.8, DARKRED, bevel=0.1, bevel_bottom=0.05)
    lib.polyline_tube(bm, [P(2.15, 22.7, 0.5), P(2.5, 23.6, 0.5), P(3.4, 24.5, 0.5)], [0.92 * U, 0.8 * U, 0.45 * U],
                      sides=10, mat_index=DARKRED)

    # --- Purple armour box on the right, stacked on the hull, its lower-left edge a diagonal; a raised
    # beige L trim at its upper-left corner and two dark tabs on its right edge.
    slab(bm, [(13.6, 9.4), (20.6, 9.3), (21.6, 10.0), (21.6, 18.4), (19.2, 18.4), (13.6, 13.9)], -1.2, 5.2,
         ARMOUR, bevel=0.9, bevel_bottom=0.4)
    slab(bm, [(13.6, 9.4), (15.95, 9.4), (15.95, 13.3), (14.9, 13.3), (14.9, 10.5), (13.6, 10.5)], 4.2, 5.55,
         BEIGE, bevel=0.3, bevel_bottom=0.1)
    slab(bm, [(16.3, 9.7), (20.1, 9.7), (21.0, 10.8), (21.0, 11.6), (16.3, 11.6)], 4.6, 5.5, ARMOUR, bevel=0.3,
         bevel_bottom=0.1)
    for r0, r1 in ((14.6, 15.5), (16.7, 18.3)):
        slab(bm, [(20.0, r0), (21.75, r0), (21.75, r1), (20.0, r1)], 2.0, 4.6, DRUM, bevel=0.3, bevel_bottom=0.1)

    # --- Lattice bay under the box: a dark floor, a post and a diagonal rail with rungs.
    slab(bm, [(13.9, 13.6), (19.6, 18.0), (19.6, 24.8), (18.6, 25.2), (14.0, 20.8)], -2.4, -1.6, RECESS,
         bevel=0.15, bevel_bottom=0.1)
    lib.polyline_tube(bm, [P(14.4, 13.6, 0.2), P(14.5, 17.4, 0.2)], 0.45 * U, sides=6, mat_index=STRUT, smooth=False)
    lib.polyline_tube(bm, [P(14.6, 14.6, 0.6), P(19.4, 19.6, 0.6)], 0.5 * U, sides=6, mat_index=STRUT, smooth=False)
    for c in (16.2, 17.6):
        lib.polyline_tube(bm, [P(c - 0.4, c + 1.9, -0.6), P(c + 0.6, c + 0.6, 0.4)], 0.3 * U, sides=6,
                          mat_index=STRUT, smooth=False)

    # --- Lower purple plate slanting down-right over the bay.
    slab(bm, [(14.3, 17.1), (15.6, 17.1), (19.1, 20.6), (19.1, 24.6), (18.5, 25.0), (14.3, 20.5)], -0.8, 3.2,
         ARMOUR, bevel=0.7, bevel_bottom=0.3)

    # --- Spine rail down the right edge to the point: a dark bracket under the box, the grey rail, a
    # lighter raised outer plate.
    slab(bm, [(19.0, 18.0), (21.8, 18.0), (21.9, 26.2), (21.3, 27.0), (20.3, 27.0), (19.2, 25.2)], -1.6, 2.0,
         GREY, bevel=0.5, bevel_bottom=0.3)
    slab(bm, [(19.2, 18.3), (21.5, 18.3), (21.5, 20.6), (19.2, 20.6)], 1.6, 3.0, DRUM, bevel=0.3, bevel_bottom=0.1)
    slab(bm, [(20.1, 20.9), (21.7, 20.9), (21.7, 26.1), (21.2, 26.7), (20.3, 26.6)], 1.6, 2.7, STRUT, bevel=0.35,
         bevel_bottom=0.1)

    return [(NAME, [lib.finish(NAME, bm, mats, coll)], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
