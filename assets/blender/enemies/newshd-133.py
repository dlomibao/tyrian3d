"""Small grey stone (newshd.shp frame 133): a 3D version of its sprite.

Seen in episodes 1-3. The sprite is a round lump 11 px wide and 12 px tall, near-black at its rim,
slate blue-grey inside with pale patches left of centre: a chipped rock lit from the upper left.
So the model is an irregular faceted stone whose outline is traced to the sprite's, its dark rim
included, about as tall as it is wide (+-5 px round the midplane): the convex hull of points on
that ball, each pulled in by a fixed random amount, so it has big flat faces and ridges.

The sprite's near-black rim, darker lower-right and pale patches are its drawn lighting, not paint:
the game draws its own dark outline, and the pale patches are lit faces of the stone. So every face
takes one mid-tone blue-grey (pal 106, near the mean of the sprite's interior) in a matte material
(metallic 0, roughness 0.8), flat shaded, and the game's sun lights the facets toward the upper
left. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-133.py [-- --preview out.png]
"""

import math
import random
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
ROUND = 0.5  # how far the traced outline is pulled toward a circle (its mean radius)
# The sprite's highlight (the mean of its near-white pixels, col 4.2 row 6.5) sits ~0.8 px left of
# the disc's centre: tilt the pole that far toward it.
TILT = math.asin(0.8 / 5.6)
BODY = 106  # the sprite's lit blue-grey, near the mean of its interior: its mid-tone
METALLIC, ROUGHNESS = 0.0, 0.8  # matte stone: the game's sun lights the facets, nothing shines
SEED = 133
# Rings of hull points from the top down: (angle from the pole in degrees, points, the range of
# how far each is pulled in toward the centre). The equator ring stays on the outline.
RINGS = [(0, 1, 0.92, 0.95), (28, 4, 0.86, 0.96), (58, 7, 0.88, 0.98), (90, 12, 1.0, 1.02),
         (122, 6, 0.86, 0.96), (155, 3, 0.85, 0.95)]
MERGE_DEG = 6  # neighbouring hull faces closer than this to flat become one facet


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

    def place(theta, phi, scale=1.0):
        n = tilt @ Vector((math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi), math.cos(theta)))
        r = lib.radius_at(radii, math.atan2(n.y, n.x)) * scale
        return Vector((cx + n.x * r, cy + n.y * r, n.z * HALF_HEIGHT * scale))

    # Points on the traced ball, each pulled in a little by a fixed random amount, and their convex
    # hull: big flat faces meeting at ridges, a chipped stone rather than a ball.
    rng = random.Random(SEED)
    bm = bmesh.new()
    for theta_deg, count, lo, hi in RINGS:
        offset = rng.uniform(0, 2 * math.pi)
        for k in range(count):
            phi = offset + 2 * math.pi * (k + rng.uniform(-0.3, 0.3)) / count
            theta = math.radians(theta_deg + rng.uniform(-8, 8)) if theta_deg else 0.0
            bm.verts.new(place(theta, phi, rng.uniform(lo, hi)))
    hull = bmesh.ops.convex_hull(bm, input=bm.verts[:])
    loose = [v for v in hull["geom_interior"] + hull["geom_unused"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(MERGE_DEG), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
