"""Star core panel (newsh2.shp frames 153-157): a 3D version of its sprite.

Seen in episode 1 (level 30) and episode 3. The sprite fills its whole block: a dark machinery
plate framed by grey beams down both sides, with beige and brown blocks in the corners, and in
the middle a five-pointed star round a glowing core. The star is built the way the concept
(assets/blender/features/concepts/newsh2-153.jpg, registered to the sprite in
assets/blender/textures/newsh2-153/concept.png) draws it, part by part where it draws them: a
layered, faceted grey prow for the upper point with a vent at its foot, swept-back dark wings with
ball studs and struts behind it, rust-brown shoulder armour on grey side wings for the left and
right points, a gunmetal housing round the glowing red eye, a grey cap and a rust chin block with
a grille under the eye, dark lower arms over a machinery bay of pipes and struts, and two rust
engine pods with side flanges and nozzles for the lower points. Hard surface throughout: chamfered
plates; only the eye is round. The three frames only brighten the core, so one model covers them
all: the core, its centre and (on the last frame) its collar change palette colour per frame
(common.palette_material frames=).

Run: blender --background --python assets/blender/enemies/newsh2-153.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402
import lib_b048 as L  # noqa: E402

NAME = "newsh2-153"
U = 1 / 12
T = -0.05  # top of the deck


def P(bm, pts, z0, z1, bevel, mat):
    """A chamfered plate on an outline of (sprite pixel-edge column, row) points, z0..z1."""
    L.bevel_plate(bm, [(lib.ex(c), lib.ey(r)) for c, r in pts], z0, z1, bevel, (mat,) * 4)


def B(bm, c0, r0, c1, r1, z0, z1, mat):
    """A plain block over pixel edges [c0, c1] x [r0, r1]."""
    L.box(bm, lib.ex(c0), lib.ey(r1), lib.ex(c1), lib.ey(r0), z0, z1, mat=mat)


def tube(bm, pts, r, mat, sides=6):
    """A pipe of constant radius r (px) along (column, row, z) points."""
    L.sweep(bm, [(lib.ex(c), lib.ey(rw), z, r * U, r * U) for c, rw, z in pts], sides=sides, mat=mat, smooth=True)


def prow(bm, mat):
    """The upper point: a faceted grey ridge from the top edge down to the eye, widening and
    rising toward it, with a sharp crest on the axis."""
    across = [(-1.0, 0.0), (-0.8, 0.5), (-0.38, 0.84), (0.0, 1.0), (0.38, 0.84), (0.8, 0.5), (1.0, 0.0)]
    secs = [(0.0, 0.5, 0.07), (1.6, 2.2, 0.15), (3.6, 3.2, 0.23), (6.0, 4.0, 0.3), (8.4, 4.6, 0.35),
            (10.0, 4.3, 0.36), (11.0, 3.0, 0.35), (11.9, 1.2, 0.3)]
    rings = [[(u * w * U, lib.ey(r), T + v * h) for u, v in across] for r, w, h in secs]
    lib.ring_loft(bm, rings, mat)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731

    def anim(i, part, frames, **kw):
        return common.palette_material(sprite, i, f"{NAME}-{part}", frames=frames, **kw)

    mats = [
        pal(2, metallic=0.1, roughness=0.8),  # 0 dark deck
        pal(9, metallic=0.55, roughness=0.4),  # 1 grey beams, ledges
        pal(7, metallic=0.55, roughness=0.4),  # 2 grey prow, side wings, chin cap
        pal(12, metallic=0.6, roughness=0.3),  # 3 prow crest
        pal(67, metallic=0.2, roughness=0.7),  # 4 dark red shoulder armour (sprite 66/67)
        pal(70, metallic=0.25, roughness=0.65),  # 5 rust chin block, pods
        anim(113, "collar", {157: 116}, metallic=0.3, roughness=0.4),  # 6 eye collar
        anim(119, "core", {155: 121, 157: 125}, roughness=0.1, emission_strength=3.5),  # 7 eye glass
        anim(125, "hot", {155: 127, 157: 127}, roughness=0.1, emission_strength=5.0),  # 8 eye centre
        pal(170, metallic=0.3, roughness=0.5),  # 9 beige blocks
        pal(22, metallic=0.3, roughness=0.5),  # 10 brown pod rears, blocks
        pal(4, metallic=0.5, roughness=0.45),  # 11 dark gunmetal: wings, housing, lower arms
        pal(163, metallic=0.3, roughness=0.5),  # 12 dark brown nozzles
        pal(1, metallic=0.1, roughness=0.9),  # 13 bay floor, vents, grilles
        pal(11, metallic=0.7, roughness=0.25),  # 14 stud balls
        pal(5, metallic=0.5, roughness=0.45),  # 15 pipes and struts
        pal(3, metallic=0.5, roughness=0.45),  # 16 dark swept wings
        pal(6, metallic=0.55, roughness=0.4),  # 17 side wings under the shoulders
        anim(121, "glow", {155: 123, 157: 126}, roughness=0.1, emission_strength=4.0),  # 18 orange ring
        pal(15, metallic=0.5, roughness=0.2),  # 19 white sheen at the crest's lower end
    ]
    (DECK, BEAM, GREY, CREST, SHOULDER, RUST, COLLAR, CORE, HOT, BEIGE, BROWN, GUN, NOZZLE, DARK, STUD,
     PIPE, WING, SIDE, GLOW, CREST_HI) = range(20)
    bm = bmesh.new()

    # Deck filling the block, with the central bay (between the pods, under the chin) sunk in it.
    B(bm, 0, 0, 24, 21.6, -0.2, T, DECK)
    B(bm, 0, 21.6, 8.4, 28, -0.2, T, DECK)
    B(bm, 15.6, 21.6, 24, 28, -0.2, T, DECK)
    B(bm, 8.4, 26.6, 15.6, 28, -0.2, T, DECK)
    B(bm, 8.4, 21.6, 15.6, 26.6, -0.2, T - 0.08, DARK)
    for c in (9.6, 11.0, 12.6, 14.0):  # machinery in the bay
        tube(bm, [(c, 21.8, T - 0.03), (c, 26.4, T - 0.03)], 0.4, PIPE)

    # Corner blocks the sprite draws outside the star: beige top left with a strip along the top
    # edge, grey top right, beige and brown along the bottom edge.
    P(bm, [(0, 0), (5.2, 0), (5.2, 3.4), (0, 3.4)], T, T + 0.12, 0.03, BEIGE)
    B(bm, 5.2, 0, 8.6, 1.0, T, T + 0.06, BEIGE)
    P(bm, [(18.8, 0), (24, 0), (24, 3.4), (18.8, 3.4)], T, T + 0.1, 0.03, BEAM)
    B(bm, 8.6, 26.8, 11.0, 28, T, T + 0.05, BEIGE)
    B(bm, 15.4, 27.2, 16.8, 28, T, T + 0.05, BROWN)

    # --- left half, mirrored about the axis (column edge 12) ------------------------------------
    side = bmesh.new()
    # Grey beam down the side edge (the sprite's), sloping up at its top end.
    P(side, [(0, 10.6), (2.0, 9.6), (3.4, 10.4), (3.4, 28), (0, 28)], T, T + 0.2, 0.04, BEAM)

    # Swept-back wing behind the prow: a dark plate with a ball stud and a strut in to the hull.
    P(side, [(0.1, 3.6), (6.0, 5.0), (7.2, 6.6), (7.0, 9.0), (4.6, 9.0)], T, T + 0.12, 0.03, WING)
    L.ellipsoid(side, lib.ex(2.8), lib.ey(6.0), T + 0.14, 0.85 * U, 0.85 * U, 0.08, mat=STUD, segments=8, rings=4)
    tube(side, [(3.4, 6.5, T + 0.15), (6.8, 8.4, T + 0.17)], 0.32, PIPE, sides=4)
    # Rear bracket block with its own stud, between the wing and the prow.
    P(side, [(5.8, 2.6), (8.3, 2.6), (8.9, 3.4), (8.9, 7.6), (5.6, 7.6), (5.6, 3.2)], T, T + 0.19, 0.04, GUN)
    L.ellipsoid(side, lib.ex(7.0), lib.ey(3.9), T + 0.2, 0.7 * U, 0.7 * U, 0.06, mat=STUD, segments=8, rings=4)
    # Layered side plates on the prow's flank (the concept's stepped armour under the ridge).
    P(side, [(8.2, 3.6), (9.4, 3.0), (9.4, 10.8), (7.4, 10.8), (7.0, 9.2)], T, T + 0.24, 0.04, GUN)

    # Side wing (the star's left point): a grey plate from the edge in to the eye housing ...
    # (it tucks under the side beam, which stays the higher of the two, so the beam shows beside it)
    P(side, [(3.0, 10.6), (6.8, 8.9), (8.4, 9.8), (8.4, 16.4), (3.0, 16.4)], T, T + 0.17, 0.04, SIDE)
    # ... with the dark red shoulder armour on it, against the housing, inside the beam ...
    P(side, [(3.5, 12.0), (5.2, 10.8), (7.4, 10.0), (8.6, 10.8), (8.6, 15.9), (3.5, 15.9)],
      T + 0.1, T + 0.29, 0.045, SHOULDER)
    # ... a cable box at its outer step, and the grey lit ledge along its lower edge.
    B(side, 3.9, 12.6, 5.4, 13.8, T + 0.18, T + 0.32, GUN)
    P(side, [(3.6, 15.7), (8.4, 15.7), (8.6, 16.7), (3.8, 16.7)], T + 0.1, T + 0.22, 0.03, BEAM)

    # Lower arm: dark plating under the shoulder and a strut running down to the chin.
    P(side, [(2.6, 16.6), (8.4, 16.6), (9.0, 18.2), (2.8, 18.2)], T, T + 0.15, 0.03, GUN)
    P(side, [(7.8, 17.4), (8.8, 17.2), (10.0, 18.6), (10.0, 21.4), (9.0, 21.4)], T, T + 0.17, 0.03, GUN)
    # Machinery bay under the arm: upright pipes and a pump block.
    for c in (3.9, 5.1, 6.2):
        tube(side, [(c, 18.0, T + 0.02), (c, 21.0, T + 0.02)], 0.38, PIPE)
    B(side, 6.6, 19.0, 8.2, 20.6, T, T + 0.1, GUN)

    # Engine pod (lower point): a rust block with its upper-left corner cut, a brown rear section, a
    # flange on the outer side and a dark nozzle at the back.
    P(side, [(3.4, 22.6), (4.9, 20.8), (7.5, 20.8), (8.2, 21.6), (8.2, 24.8), (3.4, 24.8)], T, T + 0.33, 0.06, RUST)
    P(side, [(3.5, 24.6), (8.1, 24.6), (8.1, 25.8), (7.4, 26.5), (4.2, 26.5), (3.5, 25.8)], T, T + 0.27, 0.05, BROWN)
    P(side, [(1.3, 22.8), (3.6, 22.3), (3.6, 25.6), (1.3, 25.3)], T + 0.1, T + 0.26, 0.04, RUST)
    P(side, [(4.4, 26.3), (7.2, 26.3), (7.0, 27.4), (4.6, 27.4)], T, T + 0.18, 0.03, NOZZLE)

    L.mirror_x(side)
    me = bpy.data.meshes.new("tmp153")
    side.to_mesh(me)
    side.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)

    # --- centre line ---------------------------------------------------------------------------
    prow(bm, GREY)
    tube(bm, [(12, 0.2, T + 0.07), (12, 1.6, T + 0.15), (12, 3.6, T + 0.23), (12, 6.0, T + 0.3),
              (12, 8.4, T + 0.35), (12, 10.0, T + 0.36)], 0.3, CREST, sides=4)
    # The sprite's white highlight on the crest just above the eye (sheen: a brighter, glossier strip).
    tube(bm, [(12, 8.4, T + 0.355), (12, 10.0, T + 0.365), (12, 11.2, T + 0.35)], 0.36, CREST_HI, sides=4)
    # Vent at the prow's foot, above the eye.
    P(bm, [(11.0, 10.6), (13.0, 10.6), (13.0, 11.8), (11.0, 11.8)], T + 0.2, T + 0.33, 0.02, DARK)

    # The eye: a gunmetal housing, a raised dark red collar and a glowing glass orb, hot at the centre.
    cx, cy = 0.0, lib.ey(14.4)
    lib.ring_loft(bm, [lib.ellipse_ring(cx, cy, T, 4.2 * U, 4.0 * U, n=16),
                       lib.ellipse_ring(cx, cy, 0.14, 4.2 * U, 4.0 * U, n=16),
                       lib.ellipse_ring(cx, cy, 0.18, 3.8 * U, 3.6 * U, n=16)], GUN, cap_end=False)
    lib.ring_loft(bm, [lib.ellipse_ring(cx, cy, 0.18, 3.8 * U, 3.6 * U, n=16),
                       lib.ellipse_ring(cx, cy, 0.28, 3.4 * U, 3.3 * U, n=16),
                       lib.ellipse_ring(cx, cy, 0.24, 3.05 * U, 2.95 * U, n=16)], COLLAR, cap_start=False)
    L.ellipsoid(bm, cx, cy, 0.16, 3.05 * U, 2.95 * U, 0.16, mat=CORE, segments=16, rings=8)
    # Hot centre: an orange ring and a yellow cap, each standing just proud of the orb's dome so they
    # read about 3.5 px and 2 px across from above (the sprite's 121/123 and 125 pixels).
    L.ellipsoid(bm, cx, cy, 0.28, 1.9 * U, 1.85 * U, 0.045, mat=GLOW, segments=14, rings=5)
    L.ellipsoid(bm, cx, cy, 0.31, 1.1 * U, 1.05 * U, 0.05, mat=HOT, segments=12, rings=5)

    # Under the eye: a grey cap, then the rust chin block with a grille in its front step.
    P(bm, [(10.6, 17.2), (13.4, 17.2), (13.8, 18.0), (13.2, 18.9), (10.8, 18.9), (10.2, 18.0)],
      T + 0.1, T + 0.28, 0.04, GREY)
    P(bm, [(9.6, 18.4), (14.4, 18.4), (14.6, 20.2), (9.4, 20.2)], T, T + 0.25, 0.05, RUST)
    P(bm, [(9.4, 20.0), (14.6, 20.0), (13.8, 21.8), (10.2, 21.8)], T, T + 0.15, 0.03, RUST)
    for r in (20.3, 20.8, 21.3):
        B(bm, 10.8, r, 13.2, r + 0.28, T + 0.1, T + 0.17, DARK)

    obj = L.to_object(NAME, bm, mats, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
