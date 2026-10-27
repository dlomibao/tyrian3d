"""Golden shield emblem (newshd.shp frames 79, 81, 83): a 3D version of its sprite.

Seen in episodes 1-3. A gold plate shaped like a heraldic shield: two pointed shoulders and a
pendant loop along the top, straight sides, and a bowl tapering to a point at the bottom. It
domes up toward the middle, and bright raised ribs run across it: an X from the shoulders down
to a ring round a blue gem, a rib out to each side along the wings' lower edges, and two down to
the point. The frames only brighten the gem (dark blue, blue, pale teal), so one model covers them
all, with the gem glowing and taking each frame's colour (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshd-79.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402
from lib_b014 import common, ex, ey, px, row  # noqa: E402

NAME = "newshd-79"
GEM = (53, 54, 55, 56, 57, 58, 59, 61, 63, 132, 133, 134, 135, 137, 138, 143)

# The left half of the plate's outline in sprite edge coordinates (u right, v down), from the top
# of the pendant loop round the left side to the bottom point; the right half mirrors it.
LEFT = [(12, 3.9), (11, 4.0), (10.2, 4.3), (9.4, 5.0), (8.8, 5.9), (7.4, 5.95), (6.6, 5.3), (5.4, 4.2),
        (4.6, 3.95), (3.2, 4.0), (2.2, 4.8), (1.3, 5.6), (1.0, 6.6), (1.0, 17.8), (1.9, 18.9), (2.9, 19.5),
        (3.1, 21.0), (4.1, 22.0), (5.4, 22.9), (7.8, 23.4), (8.9, 24.3), (10.0, 25.0), (12, 25.1)]
GEM_C = (11.5, 17.5)  # the gem's centre (pixel-centre coordinates: column, row)


def outline():
    right = [(24 - u, v) for u, v in reversed(LEFT[1:-1])]
    # Visually counter-clockwise: down the right side first, then back up the left.
    pts = list(reversed(LEFT)) + list(reversed(right))
    return [(ex(u), ey(v)) for u, v in pts]


def mirror_c(points):
    """Mirror pixel-centre points (column, row) across the sprite's middle (column 11.5)."""
    return [(23 - c, r) for c, r in points]


def build(sprite):
    coll = common.reset_collection(NAME)
    pixels = sprite["frames"][0]["pixels"]
    shade = lib.Shade(sprite, pixels, 2, skip=GEM)
    reps, edges = lib.shade_slots(sprite, pixels, 5, skip=GEM)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [pal(i, metallic=0.75, roughness=0.32) for i in reps]  # 0-4 the gold, darkest first
    RIM = len(mats)
    mats += [
        pal(20, metallic=0.7, roughness=0.45),  # rim and underside
        pal(29, metallic=0.85, roughness=0.2),  # bright ribs
        pal(30, metallic=0.85, roughness=0.18),  # gem ring
        pal(27, metallic=0.8, roughness=0.25),  # pendant loop
    ]
    # The gem and its highlight: dark blue on frame 79, blue on 81, pale teal on 83.
    gem = lambda i, f, **kw: common.palette_material(sprite, i, f"{NAME}-gem", frames=f, **kw)  # noqa: E731
    mats += [
        gem(57, {81: 59, 83: 135}, metallic=0.3, roughness=0.12, emission_strength=2.5),  # gem
        gem(61, {81: 63, 83: 143}, metallic=0.2, roughness=0.1, emission_strength=4.0),  # gem highlight
    ]
    _, RIB, RING, LOOP, GEMM, SHINE = range(RIM, RIM + 6)

    # The plate, domed toward the middle and painted with the sprite's light and dark gold.
    def top(s):
        return 0.035 + 0.15 * (1 - s * s) ** 0.7

    def bottom(s):
        return -(0.035 + 0.06 * (1 - s * s) ** 0.7)

    plate = lib.Pillow(outline(), (0.0, 0.0), top, bottom)
    bm = bmesh.new()
    plate.build(bm, [1.0, 0.9, 0.76, 0.6, 0.42, 0.22], mat_index=RIM)
    lib.paint(bm, shade, edges, list(range(len(reps))), rim_slot=RIM)
    body = common.mesh_object(NAME, bm, mats, coll, smooth=True)

    # Ribs, ring, loop and gem, sitting on the plate.
    bm = bmesh.new()
    lift = 0.012
    on = lambda c, r, dz=0.0: (px(c), row(r), plate.z_top(px(c), row(r)) + lift + dz)  # noqa: E731
    ribs = [
        [(5.6, 7.4), (6.5, 8.4), (7.5, 9.5), (8.5, 10.5), (9.5, 11.5), (10.4, 12.7), (11.0, 14.0)],  # shoulder X
        [(1.9, 12.8), (3.0, 14.0), (4.2, 15.1), (5.6, 15.5), (7.2, 15.4), (8.8, 15.9)],  # upper wing edge
        [(2.0, 18.3), (3.6, 18.1), (5.4, 18.0), (7.0, 17.8), (8.4, 17.6)],  # lower wing edge
        [(9.4, 20.0), (8.8, 21.4), (8.7, 22.6), (9.3, 23.6)],  # down to the point
    ]
    for pts in ribs:
        for side in (pts, mirror_c(pts)):
            # Broad, low ribs: a round tube squashed down onto the plate.
            start = len(bm.verts)
            lib.polyline_tube(bm, [on(c, r, -0.012) for c, r in side], 0.85 / 12, sides=6, mat_index=RIB)
            bm.verts.ensure_lookup_table()
            for v in bm.verts[start:]:
                base = plate.z_top(v.co.x, v.co.y) - 0.012
                v.co.z = base + (v.co.z - base) * 0.45
    # The raised ring round the gem.
    gc, gr = GEM_C
    ring = [on(gc + 2.9 * math.cos(a), gr + 2.9 * math.sin(a))
            for a in (2 * math.pi * k / 20 for k in range(21))]
    lib.polyline_tube(bm, ring, 0.7 / 12, sides=6, mat_index=RING)
    # The pendant loop lying on the top edge, with a hole through it.
    loop = [on(11.5 + 1.55 * math.cos(a), 5.9 + 1.45 * math.sin(a), 0.01)
            for a in (2 * math.pi * k / 16 for k in range(17))]
    lib.polyline_tube(bm, loop, 0.8 / 12, sides=8, mat_index=LOOP)
    # The gem, a glossy dome inside the ring, and its highlight.
    gx, gy = px(gc), row(gr)
    gz = plate.z_top(gx, gy) - 0.01
    lib.dome(bm, gx, gy, 2.15 / 12, 2.15 / 12, 0.085, z=gz, rings=5, sides=16, mat_index=GEMM)
    lib.dome(bm, px(11.0), row(17.0), 0.5 / 12, 0.5 / 12, 0.02, z=gz + 0.065, rings=2, sides=8,
             mat_index=SHINE)
    parts = common.mesh_object(f"{NAME}_parts", bm, mats, coll, smooth=True)
    return [(NAME, [body, parts], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
