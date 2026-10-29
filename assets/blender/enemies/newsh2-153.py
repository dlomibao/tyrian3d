"""Star core panel (newsh2.shp frames 153-157): a 3D version of its sprite.

Seen in episode 1 (level 30) and episode 3. The sprite fills its whole block: a dark machinery
plate framed by grey beams down both sides, with beige and brown blocks in the corners, and in
the middle a five-pointed star round a glowing core: a grey ridge for the upper point, dark red
arms with grey undersides to the left and right, dark red lower points and a red lip under the
core. Read as hard-surface armour (the concept's reading): a faceted prow, chamfered side beams
and shoulder blocks, two engine pods at the bottom (the lower points) round a dark bay cut into the
deck, and ball studs on dark wing plates behind the prow. The three frames only brighten the core, so one model covers them all: the core, its
centre and (on the last frame) its collar change palette colour per frame (common.palette_material
frames=).

Run: blender --background --python assets/blender/enemies/newsh2-153.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-153"
U = 1 / 12
PLATE_TOP = -0.05


def box(bm, c0, c1, r0, r1, z0, z1, mat):
    """A block over pixel edges [c0, c1] x [r0, r1], from z0 to z1."""
    x0, x1, y0, y1 = lib.ex(c0), lib.ex(c1), lib.ey(r1), lib.ey(r0)
    ring0 = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]
    ring1 = [(x, y1, z) for x, _, z in ring0]
    lib.ring_loft(bm, [ring0, ring1], mat)


def slab(bm, secs, z0, ch, top, side=None):
    """A hard plate lofted along Y with chamfered top edges all round. secs: (row, c0, c1, z_top) in
    sprite rows/columns (pixel edges), in order down the sprite. The top and chamfers get `top`,
    the walls `side`."""
    side = top if side is None else side
    pts = [(lib.ey(r), lib.ex(c0), lib.ex(c1), z) for r, c0, c1, z in secs]

    def ring(y, x0, x1, z, end=False):
        zc = z - ch
        if end:
            return [(x0, y, z0), (x1, y, z0), (x1, y, zc), (x1 - ch, y, zc), (x0 + ch, y, zc), (x0, y, zc)]
        return [(x0, y, z0), (x1, y, z0), (x1, y, zc), (x1 - ch, y, z), (x0 + ch, y, z), (x0, y, zc)]

    rings = [ring(*pts[0], end=True)]
    for i, (y, x0, x1, z) in enumerate(pts):
        if i == 0:
            y -= ch
        elif i == len(pts) - 1:
            y += ch
        rings.append(ring(y, x0, x1, z))
    rings.append(ring(*pts[-1], end=True))
    seg = [side, side, top, top, top, side]
    lib.ring_loft(bm, rings, [seg] * (len(rings) - 1))


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731

    def anim(i, part, frames, **kw):
        return common.palette_material(sprite, i, f"{NAME}-{part}", frames=frames, **kw)

    mats = [
        pal(2, metallic=0.1, roughness=0.8),  # 0 dark plate
        pal(9, metallic=0.6, roughness=0.35),  # 1 grey beams and ledges
        pal(7, metallic=0.6, roughness=0.35),  # 2 grey ridge
        pal(13, metallic=0.7, roughness=0.2),  # 3 ridge crest
        pal(67, metallic=0.35, roughness=0.45),  # 4 dark red armour
        pal(70, metallic=0.4, roughness=0.35),  # 5 red lip
        anim(113, "collar", {157: 116}, metallic=0.3, roughness=0.4),  # 6 core collar
        anim(119, "core", {155: 121, 157: 125}, emission_strength=3.5),  # 7 core
        anim(125, "hot", {155: 127, 157: 127}, emission_strength=5.0),  # 8 core centre
        pal(170, metallic=0.3, roughness=0.5),  # 9 beige blocks
        pal(22, metallic=0.3, roughness=0.5),  # 10 brown blocks
        pal(4, metallic=0.4, roughness=0.5),  # 11 dark grey plates
        pal(163, metallic=0.3, roughness=0.5),  # 12 dark brown nozzle
        pal(1, metallic=0.1, roughness=0.9),  # 13 bay floor
        pal(11, metallic=0.7, roughness=0.25),  # 14 stud balls
    ]
    PLATE, BEAM, RIDGE, CREST, RED, LIP, COLLAR, CORE, HOT, BEIGE, BROWN, DGREY, NOZZLE, FLOOR, STUD = range(15)
    bm = bmesh.new()
    t = PLATE_TOP

    # The deck filling the block, with the dark central bay (rows 21-26, cols 8-15) cut into it.
    box(bm, 0, 24, 0, 21, -0.2, t, PLATE)
    box(bm, 0, 8, 21, 26, -0.2, t, PLATE)
    box(bm, 15, 24, 21, 26, -0.2, t, PLATE)
    box(bm, 0, 24, 26, 28, -0.2, t, PLATE)
    box(bm, 8, 15, 21, 26, -0.2, t - 0.1, FLOOR)

    # Grey beams down both sides: hard chamfered boxes about 3 px tall, sloping down at the top end.
    for c0, c1 in ((0, 3.9), (20.8, 24)):
        slab(bm, [(9.6, c0, c1, t + 0.09), (12.5, c0, c1, t + 0.25), (28, c0, c1, t + 0.25)], t, 0.045, BEAM)

    # Corner blocks: beige top left (with a strip along the top edge), grey top right, beige and
    # brown along the bottom.
    slab(bm, [(0, 0, 5.2, t + 0.13), (4, 0, 5.2, t + 0.13)], t, 0.03, BEIGE)
    box(bm, 5.2, 9.8, 0, 1.2, t, t + 0.07, BEIGE)
    slab(bm, [(0, 18.8, 24, t + 0.12), (4, 18.8, 24, t + 0.12)], t, 0.03, BEAM)
    box(bm, 2, 5, 26, 28, t, t + 0.08, BEIGE)
    box(bm, 8, 11, 26, 28, t, t + 0.06, BEIGE)
    box(bm, 16, 21, 26.2, 28, t, t + 0.07, BROWN)

    # Wing plates behind the prow with a ball stud each and a thin strut in toward the ridge.
    box(bm, 0, 4.6, 4, 8, t, t + 0.05, DGREY)
    box(bm, 17.4, 21.2, 4.6, 8, t, t + 0.05, DGREY)
    for c, r in ((2.3, 6.2), (19.2, 6.2)):
        lib.ellipsoid(bm, (lib.px(c - 0.5), lib.row(r - 0.5), t + 0.07), (1.1 * U, 1.1 * U, 0.08),
                      segments=8, rings=4, mat_index=STUD)
    for a, b in (((3.2, 7.4), (8.6, 8.6)), ((18.2, 7.2), (14.0, 7.6))):
        lib.polyline_tube(bm, [(lib.ex(a[0]), lib.ey(a[1]), t + 0.06), (lib.ex(b[0]), lib.ey(b[1]), t + 0.08)],
                          0.4 * U, sides=4, mat_index=DGREY)

    # Upper point: a faceted grey prow from the top edge down to the core, rising toward the core,
    # with its crest on column 11.
    xc = lib.px(11)
    rings = []
    for r, w, h in ((0.0, 1.6, 0.06), (5.0, 2.8, 0.16), (11.8, 3.9, 0.33)):
        y = lib.ey(r)
        rings.append([(xc - w * U, y, t), (xc - 0.5 * w * U, y, t + 0.7 * h), (xc, y, t + h),
                      (xc + 0.5 * w * U, y, t + 0.7 * h), (xc + w * U, y, t)])
    lib.ring_loft(bm, rings, RIDGE)
    lib.polyline_tube(bm, [(xc, lib.ey(0.1), t + 0.06), (xc, lib.ey(5.0), t + 0.16), (xc, lib.ey(11.8), t + 0.33)],
                      0.35 * U, sides=6, mat_index=CREST)

    # Shoulders: dark red armour blocks against the collar, each with a grey ledge below it.
    slab(bm, [(12, 5.6, 9.4, t + 0.2), (16, 5.0, 9.4, t + 0.2)], t, 0.04, RED)
    slab(bm, [(15.6, 4, 8.6, t + 0.12), (17, 4, 8.6, t + 0.12)], t, 0.03, BEAM)
    slab(bm, [(12.8, 14.6, 19.4, t + 0.2), (16, 14.6, 19.6, t + 0.2)], t, 0.04, RED)
    slab(bm, [(15.6, 14.8, 19.2, t + 0.12), (17, 14.8, 19.2, t + 0.12)], t, 0.03, BEAM)

    # Engine pods: rust-red chamfered blocks, the upper-left corner cut diagonally, with a brown
    # (left) or dark brown (right) rear section.
    slab(bm, [(20, 6, 8.4, t + 0.28), (23, 3, 8.4, t + 0.28), (24, 3, 8.4, t + 0.28)], t, 0.05, RED)
    slab(bm, [(23.9, 3.2, 8.2, t + 0.22), (26, 3.2, 8.2, t + 0.22)], t, 0.04, BROWN)
    slab(bm, [(20.2, 17, 19.8, t + 0.28), (22.8, 15, 20.6, t + 0.28), (25, 15.6, 20.6, t + 0.28)], t, 0.05, RED)
    slab(bm, [(24.9, 16.8, 20.8, t + 0.22), (26.6, 16.8, 20.8, t + 0.22)], t, 0.04, NOZZLE)

    # Chin: a rounded red lip across rows 18-20, under the core.
    lib.polyline_tube(bm, [(lib.ex(9.1), lib.ey(19.2), t + 0.1), (lib.ex(13.9), lib.ey(19.2), t + 0.1)],
                      1.3 * U, sides=8, mat_index=LIP, smooth=True)
    slab(bm, [(19.4, 9.3, 13.7, t + 0.07), (21, 9.6, 13.4, t + 0.05)], t, 0.02, RED)

    # Core: a raised dark red collar round a glowing orb with a hotter centre.
    cx, cy = lib.px(11.5), lib.row(14.5)
    lib.ring_loft(bm, [lib.ellipse_ring(cx, cy, t, 3.5 * U, 3.3 * U, n=12),
                       lib.ellipse_ring(cx, cy, 0.17, 3.4 * U, 3.2 * U, n=12),
                       lib.ellipse_ring(cx, cy, 0.2, 3.0 * U, 2.8 * U, n=12),
                       lib.ellipse_ring(cx, cy, 0.15, 2.7 * U, 2.5 * U, n=12)], COLLAR)
    lib.ellipsoid(bm, (cx, cy, 0.14), (2.8 * U, 2.6 * U, 0.17), segments=12, rings=7, mat_index=CORE)
    lib.ellipsoid(bm, (cx, cy + 0.2 * U, 0.14), (2.0 * U, 1.9 * U, 0.2), segments=10, rings=5, mat_index=HOT)

    obj = lib.finish(NAME, bm, mats, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
