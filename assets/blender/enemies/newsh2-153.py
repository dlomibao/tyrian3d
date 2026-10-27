"""Star core panel (newsh2.shp frames 153-157): a 3D version of its sprite.

Seen in episode 1 (level 30) and episode 3. The sprite fills its whole block: a dark machinery
plate framed by grey beams down both sides, with beige and brown blocks in the corners, and in
the middle a five-pointed star round a glowing core: a grey ridge for the upper point, dark red
arms with grey undersides to the left and right, dark red lower points and a red lip under the
core. The three frames only brighten the core, so one model covers them all: the core, its
centre and (on the last frame) its collar change palette colour per frame (common.palette_material
frames=).

Run: blender --background --python assets/blender/enemies/newsh2-153.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh
from mathutils import Vector

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


def spike(bm, a, b, w0, h0, z0, mat_up, mat_down, w1=0.0, h1=0.0):
    """A diamond-section point from a (base) to b (tip) in sprite pixels: half width w and half
    height h (units) at each end. Faces turned toward +Y get mat_up, the others mat_down."""
    pa = Vector((lib.px(a[0]), lib.row(a[1]), z0))
    pb = Vector((lib.px(b[0]), lib.row(b[1]), z0))
    d = (pb - pa).normalized()
    side = Vector((-d.y, d.x, 0.0))
    up = Vector((0, 0, 1))
    def ring(p, w, h):
        return [tuple(p + side * w), tuple(p + up * h), tuple(p - side * w), tuple(p - up * h * 0.4)]
    f0 = len(bm.faces)
    rings = [ring(pa, w0, h0)]
    rings.append(ring(pb, w1, h1) if w1 else [tuple(pb)])
    lib.ring_loft(bm, rings, mat_up)
    bm.faces.ensure_lookup_table()
    centre = (pa + pb) / 2
    for f in bm.faces[f0:]:
        f.material_index = mat_up if (f.calc_center_median() - centre).y >= 0 else mat_down


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731

    def anim(i, part, frames, **kw):
        return common.palette_material(sprite, i, f"{NAME}-{part}", frames=frames, **kw)

    mats = [
        pal(2, metallic=0.1, roughness=0.8),  # 0 dark plate
        pal(9, metallic=0.6, roughness=0.35),  # 1 grey beams and undersides
        pal(7, metallic=0.6, roughness=0.35),  # 2 grey ridge
        pal(13, metallic=0.7, roughness=0.2),  # 3 ridge crest
        pal(67, metallic=0.15, roughness=0.5),  # 4 dark red arms
        pal(70, metallic=0.4, roughness=0.35),  # 5 red lip
        anim(113, "collar", {157: 116}, metallic=0.3, roughness=0.4),  # 6 core collar
        anim(119, "core", {155: 121, 157: 125}, emission_strength=3.5),  # 7 core
        anim(125, "hot", {155: 127, 157: 127}, emission_strength=5.0),  # 8 core centre
        pal(170, metallic=0.3, roughness=0.5),  # 9 beige blocks
        pal(22, metallic=0.3, roughness=0.5),  # 10 brown blocks
        pal(4, metallic=0.4, roughness=0.5),  # 11 dark grey plates
    ]
    PLATE, BEAM, RIDGE, CREST, RED, LIP, COLLAR, CORE, HOT, BEIGE, BROWN, DGREY = range(12)
    bm = bmesh.new()

    # The plate filling the block.
    box(bm, 0, 24, 0, 28, -0.2, PLATE_TOP, PLATE)
    # Grey beams down both sides, a grey block top right and a small dark one below it.
    t = PLATE_TOP
    for c0, c1 in ((0, 4), (21, 24)):
        x = (lib.ex(c0) + lib.ex(c1)) / 2
        hw = (lib.ex(c1) - lib.ex(c0)) / 2
        lib.Profile([(lib.ey(r), hw, h, t) for r, h in ((27.95, 0.06), (26, 0.08), (12, 0.08), (10.6, 0.05))],
                    power=4.0).build(bm, sides=12, mat_index=BEAM, smooth=False, dx=x)
    box(bm, 18, 24, 0, 4, t, t + 0.07, BEAM)
    box(bm, 18, 21, 5, 8, t, t + 0.04, DGREY)
    # Corner blocks: beige top left and bottom left, brown along the bottom.
    box(bm, 0, 5, 0, 4, t, t + 0.08, BEIGE)
    box(bm, 3, 8, 24, 26, t, t + 0.06, BROWN)
    box(bm, 2, 5, 26, 28, t, t + 0.07, BEIGE)
    box(bm, 8, 11, 26, 28, t, t + 0.05, BEIGE)
    box(bm, 16, 21, 26, 28, t, t + 0.05, BROWN)

    # Upper point: a grey ridge from the top edge down to the core, crest on column 11.
    xc = lib.px(11)
    rings = []
    for r, w, h in ((0.0, 1.5, 0.03), (5.0, 2.8, 0.08), (11.5, 3.8, 0.15)):
        y = lib.ey(r)
        rings.append([(xc - w * U, y, t), (xc, y, t + h), (xc + w * U, y, t), (xc, y, t - 0.05)])
    lib.ring_loft(bm, rings, RIDGE)
    lib.polyline_tube(bm, [(xc, lib.ey(0.3), t + 0.03), (xc, lib.ey(11.5), t + 0.15)], 0.35 * U, sides=6,
                      mat_index=CREST)

    # Side arms (red over grey) and the lower points (red), all from the core outward.
    z = 0.0
    spike(bm, (10.0, 14.6), (4.0, 15.6), 2.2 * U, 0.1, z, RED, BEAM)
    spike(bm, (13.0, 14.8), (19.6, 15.6), 2.0 * U, 0.1, z, RED, BEAM)
    spike(bm, (10.0, 18.0), (4.0, 23.2), 2.8 * U, 0.1, z - 0.01, RED, RED, w1=0.9 * U, h1=0.03)
    spike(bm, (13.0, 18.4), (18.8, 24.8), 2.8 * U, 0.1, z - 0.01, RED, RED, w1=0.9 * U, h1=0.03)

    # Red lip under the core (rows 18-20).
    lib.ellipsoid(bm, (lib.px(11.0), lib.row(19.0), 0.0), (2.6 * U, 1.3 * U, 0.06), segments=12, rings=6,
                  mat_index=LIP)
    # Core: a dark red collar (rows 12 and 17) round a glowing orb with a hotter centre.
    cx, cy = lib.px(11.5), lib.row(14.5)
    lib.ring_loft(bm, [lib.ellipse_ring(cx, cy, -0.04, 3.4 * U, 3.2 * U, n=16),
                       lib.ellipse_ring(cx, cy, 0.07, 3.3 * U, 3.1 * U, n=16)], COLLAR)
    lib.ellipsoid(bm, (cx, cy, 0.06), (2.9 * U, 2.7 * U, 0.14), segments=16, rings=8, mat_index=CORE)
    lib.ellipsoid(bm, (cx, cy + 0.2 * U, 0.12), (1.6 * U, 1.5 * U, 0.1), segments=12, rings=6, mat_index=HOT)

    obj = lib.finish(NAME, bm, mats, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
