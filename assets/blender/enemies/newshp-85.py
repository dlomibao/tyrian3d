"""Molten fireball (newshp.shp frames 85, 131, 233): a 3D version of its sprite.

Seen in episode 4 (level section 10). A round ball of churning lava: a white-hot core up and to
the left, bright yellow streaks swirling round the lower right, and dark red rock at the rim and
lower left. The three frames only brighten the whole ball (it pulses), so one model covers them:
every pixel of frame 131 is two palette steps brighter than on frame 85, and on frame 233 five
(up to white), so every colour band steps up the same way on those frames (palette_material
frames=).

The ball is a squashed sphere whose faces take the sprite's colour bands (smoothed from the first
frame where they sit in the top view), with a glowing dome for the core and raised glowing
ridges for the bright streaks.

Run: blender --background --python assets/blender/enemies/newshp-85.py [-- --preview out.png] [--frames frames.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshp-85"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# The ball fills columns 2-20 and rows 5-23 inside its outline: 19 px across.
CX = (11 + 0.5 - 12) / 12
CY = (14 - (14 + 0.5)) / 12
RADIUS = 9.5 / 12
HALF_HEIGHT = 0.28

# Colour bands (palette indices) the ball's faces are sorted into, with their emission strength.
BANDS = [(113, 0.0), (115, 0.0), (117, 0.5), (119, 1.5), (121, 2.5), (123, 3.0), (125, 3.5), (127, 4.5)]
# How many palette steps the whole ball brightens on each later frame (white, 127, is the top).
PULSE = {131: 2, 233: 5}
DARK, MID, WARM, RED, ORANGE, AMBER, YELLOW, WHITE = range(len(BANDS))


def px(x):
    """Sprite column (pixel centre) to Blender X."""
    return (x + 0.5 - 12) / 12


def row(r):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (14 - (r + 0.5)) / 12


def sample(grid, x, y, blur=1.0):
    """The palette index under (x, y) in the top view: a weighted average of the coloured pixels
    nearby (the outline and the transparent background don't count)."""
    c = x * 12 + 12 - 0.5
    r = 14 - 0.5 - y * 12
    total = weight = 0.0
    for rr in range(max(0, int(r) - 2), min(len(grid), int(r) + 4)):
        for cc in range(max(0, int(c) - 2), min(len(grid[0]), int(c) + 4)):
            v = grid[rr][cc]
            if v < 112:
                continue
            w = math.exp(-((rr - r) ** 2 + (cc - c) ** 2) / (2 * blur * blur))
            total += v * w
            weight += w
    return total / weight if weight else 114


def band_of(index):
    return min(range(len(BANDS)), key=lambda i: (abs(BANDS[i][0] - index), -i))


def surface_z(x, y):
    """Height of the ball's upper surface above (x, y)."""
    d = ((x - CX) ** 2 + (y - CY) ** 2) / RADIUS ** 2
    return HALF_HEIGHT * math.sqrt(max(0.0, 1.0 - d))


def ridge(bm, points, radius, mat_index, sides=6):
    """A glowing streak lying on the ball: a tube through sprite (column, row) points, fattest in
    the middle and tapering to points at both ends."""
    pts = [Vector((px(c), row(r), 0.0)) for c, r in points]
    for p in pts:
        p.z = surface_z(p.x, p.y) - radius * 0.2
    n = len(pts)
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        side = Vector((-t.y, t.x, 0.0)).normalized()
        up = t.cross(side).normalized()
        if up.z < 0:
            up = -up
        k = math.sin(math.pi * (i + 0.5) / n) ** 0.6
        rings.append([bm.verts.new(p + side * math.cos(a) * radius * k + up * math.sin(a) * radius * k * 0.7)
                      for a in (2 * math.pi * (j + 0.5) / sides for j in range(sides))])
    ends = [bm.verts.new(pts[0] + (pts[0] - pts[1]).normalized() * radius * 0.6),
            bm.verts.new(pts[-1] + (pts[-1] - pts[-2]).normalized() * radius * 0.6)]
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(sides):
            k = (j + 1) % sides
            bm.faces.new((r0[j], r0[k], r1[k], r1[j])).material_index = mat_index
    for j in range(sides):
        k = (j + 1) % sides
        bm.faces.new((rings[0][k], rings[0][j], ends[0])).material_index = mat_index
        bm.faces.new((rings[-1][j], rings[-1][k], ends[1])).material_index = mat_index


def dome(bm, c, r, rx, ry, height, mat_index, sink=0.0):
    """A glowing dome sitting on the ball, centred on sprite (column, row)."""
    x0, y0 = px(c), row(r)
    z0 = surface_z(x0, y0) - sink
    verts = bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=7, radius=1.0)["verts"]
    for v in verts:
        x, y, z = v.co
        v.co = (x0 + x * rx / 12, y0 + y * ry / 12, z0 + z * height)
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat_index


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = [common.palette_material(sprite, i, f"{NAME}-pulse", metallic=0.05, roughness=0.6 - 0.04 * k,
                                    emission_strength=e,
                                    frames={f: min(i + d, 127) for f, d in PULSE.items() if i < 127})
            for k, (i, e) in enumerate(BANDS)]
    grid = sprite["frames"][0]["pixels"]
    bm = bmesh.new()

    # The ball: an icosphere squashed to a modest height, coloured by the sprite's bands.
    ball = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)["verts"]
    for v in ball:
        x, y, z = v.co
        wx, wy = CX + x * RADIUS, CY + y * RADIUS
        heat = (sample(grid, wx, wy, blur=1.4) - 112) / 15
        # The brighter lava swells a little above the dark crust.
        lift = 1.0 + (0.25 * (heat - 0.4) if z > 0 else 0.0)
        v.co = (wx, wy, z * HALF_HEIGHT * lift)
    for f in {f for v in ball for f in v.link_faces}:
        cen = f.calc_center_median()
        f.material_index = band_of(sample(grid, cen.x, cen.y, blur=0.7)) if cen.z > -0.05 else DARK

    # The white-hot core (rows 8-14, columns 4-11): an orange swell, a yellow dome, a white crown.
    dome(bm, 7.4, 11.3, 4.3, 3.6, 0.07, ORANGE, sink=0.025)
    dome(bm, 7.8, 10.9, 3.0, 2.4, 0.08, YELLOW, sink=0.01)
    dome(bm, 7.8, 10.6, 1.7, 1.3, 0.06, WHITE, sink=-0.04)

    # Bright streaks: the arc round the lower right, the flare at its end, the upper streaks.
    ridge(bm, [(8.8, 18.6), (10.0, 18.0), (11.0, 17.3)], 1.0 / 12, AMBER)
    ridge(bm, [(11.3, 21.9), (12.8, 21.3), (14.1, 20.4), (15.2, 19.5), (16.6, 18.7)], 1.3 / 12, AMBER)
    dome(bm, 15.8, 19.1, 1.4, 1.3, 0.05, WHITE, sink=-0.01)
    ridge(bm, [(18.2, 15.0), (18.5, 16.5), (18.2, 18.1)], 1.0 / 12, ORANGE)
    ridge(bm, [(11.3, 6.2), (12.3, 7.1), (13.2, 8.1), (13.4, 9.5), (13.0, 10.8)], 1.0 / 12, AMBER)
    ridge(bm, [(16.2, 9.6), (16.5, 11.0), (16.2, 12.7)], 0.9 / 12, ORANGE)
    ridge(bm, [(4.0, 14.0), (5.1, 14.1), (6.2, 15.0)], 0.8 / 12, AMBER)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])
    if "--frames" in sys.argv:
        common.render_frame_previews([obj], sys.argv[sys.argv.index("--frames") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
