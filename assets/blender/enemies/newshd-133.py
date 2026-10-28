"""Small grey-blue ball (newshd.shp frame 133): a 3D version of its sprite.

Seen in episodes 1-3. The sprite is a round disc 11 px wide and 12 px tall, near-black at its rim,
slate blue-grey inside and a small near-white spot just left of centre: a shiny ball. So the model
is a smooth sphere (smooth shaded) whose outline is traced to the sprite's, its dark rim included,
and which stands about as tall as it is wide (+-5.5 px round the midplane).

The sphere is built from rings round a pole tilted a little toward the sprite's highlight. The
sprite's near-black rim, darker lower-right and near-white spot are its drawn lighting, not paint:
the game draws its own dark outline and its sun and environment light make the shine, so the whole
ball takes the sprite's mid-tone slate blue-grey (pal 103) and a polished-metal material (metallic,
fairly smooth) that puts a highlight on it from the game's light. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-133.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402

common = lib.common

NAME = "newshd-133"
HALF_HEIGHT = 5.6 / 12  # units: the ball is about 11 px tall, centred on the midplane
GROW = 0.15  # px past the sprite's outer pixel edge, so its outline pixels are covered
SEGMENTS = 20
ROUND = 0.5  # how far the traced outline is pulled toward a circle (its mean radius)
# The sprite's highlight (the mean of its near-white pixels, col 4.2 row 6.5) sits ~0.8 px left of
# the disc's centre: tilt the pole that far toward it.
TILT = math.asin(0.8 / 5.6)
# Rings from the pole down, as the sine of the ring's angle from the pole (its fraction of the
# radius seen from above), then the angles of the underside rings. Geometry only: one colour.
BODY = 103  # the sprite's mid-tone slate blue-grey (its interior, between 102 and 105)
METALLIC, ROUGHNESS = 0.8, 0.35  # a polished metal ball: the game's lights make its highlight
BANDS = [0.17, 0.33, 0.52, 0.70, 0.86, 0.96, 1.0]
UNDER = [math.radians(125), math.radians(155), math.pi]


def outline(pixels, steps=96, grow=GROW, smooth=8):
    """The whole sprite (dark rim included) as a radius per direction from its centre, smoothed
    and pulled toward a circle: (cx, cy, radii) in units for a 12x14 block."""
    h, w = len(pixels), len(pixels[0])
    cells = [(c + 0.5, r + 0.5) for r in range(h) for c in range(w) if pixels[r][c] != -1]
    cu = (min(c for c, _ in cells) + max(c for c, _ in cells)) / 2
    cv = (min(r for _, r in cells) + max(r for _, r in cells)) / 2

    def inside(u, v):
        return 0 <= u < w and 0 <= v < h and pixels[int(v)][int(u)] != -1

    radii = []
    for k in range(steps):
        a = 2 * math.pi * k / steps
        du, dv = math.cos(a), -math.sin(a)  # Blender +Y is up the sprite (-v)
        t = 0.0
        while inside(cu + du * (t + 0.05), cv + dv * (t + 0.05)) and t < 20:
            t += 0.05
        radii.append(t + grow)
    for _ in range(smooth):
        radii = [(radii[k - 1] + 2 * radii[k] + radii[(k + 1) % steps]) / 4 for k in range(steps)]
    mean = sum(radii) / steps
    radii = [r + (mean - r) * ROUND for r in radii]
    return (cu - 6) / 12, (7 - cv) / 12, [r / 12 for r in radii]


def build(sprite):
    coll = common.reset_collection(NAME)
    pixels = sprite["frames"][0]["pixels"]
    cx, cy, radii = outline(pixels)

    mats = [common.palette_material(sprite, BODY, NAME, metallic=METALLIC, roughness=ROUGHNESS)]

    tilt = Matrix.Rotation(-TILT, 3, "Y")  # pole leans toward -X (the sprite's left)

    def place(theta, phi):
        n = tilt @ Vector((math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi), math.cos(theta)))
        r = lib.radius_at(radii, math.atan2(n.y, n.x))
        return Vector((cx + n.x * r, cy + n.y * r, n.z * HALF_HEIGHT))

    rings = [math.asin(s) for s in BANDS] + UNDER
    bm = bmesh.new()
    top = bm.verts.new(place(0.0, 0.0))
    prev = None
    for theta in rings:
        if theta >= math.pi - 1e-6:  # the bottom pole closes the last band
            bot = bm.verts.new(place(math.pi, 0.0))
            for k in range(SEGMENTS):
                f = bm.faces.new((prev[(k + 1) % SEGMENTS], prev[k], bot))
            break
        ring = [bm.verts.new(place(theta, 2 * math.pi * k / SEGMENTS)) for k in range(SEGMENTS)]
        for k in range(SEGMENTS):
            k1 = (k + 1) % SEGMENTS
            if prev is None:
                f = bm.faces.new((top, ring[k], ring[k1]))
            else:
                f = bm.faces.new((prev[k], ring[k], ring[k1], prev[k1]))
        prev = ring
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
