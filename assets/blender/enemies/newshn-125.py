"""Small blue swirl orb (newshn.shp frame 125): a 3D version of its sprite.

Seen in level 2.4, lying on the ground. The sprite shades it as a glossy ball: a dark rim all
round, a pale highlight upper left, and a swirl marking inside it (a dark groove curving down
from the top edge round the middle, and a pale crescent round the lower right). So the model is
one near-spherical orb filling the sprite's 15 x 16 px circle and about 11 px tall, its surface
one glossy mid-blue with the swirl painted on (the shading, rim and highlight are left to the
game's light), the groove pressed in by under half a pixel. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshn-125.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b071 as lib  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshn-125"
PX = 1 / 12

CENTRE = (11.0, 13.5)  # sprite (col, row) of the orb's centre
RADII = (7.55, 8.05)  # px: the footprint, the sprite's 15 x 16 px circle including its dark rim
EQUATOR = 2.6  # px above the ground: the widest ring
TOP = 10.8  # px: the crown
FOOT = 0.84  # the ground contact ring's radius, as a fraction of the equator's

# The swirl, as (col, row) polylines: the dark groove and the pale crescent.
GROOVE = [(13.4, 8.6), (13.1, 10.0), (13.0, 11.5), (13.0, 12.9), (12.4, 14.0), (11.3, 14.8),
          (10.0, 15.2)]
RIDGE = [(15.4, 11.2), (15.6, 12.8), (15.2, 14.4), (14.3, 15.8), (13.0, 17.0), (11.4, 17.9),
         (9.8, 18.1)]
RELIEF = 0.4  # px: groove depth

# The orb is glass-like and glossy: the sprite's dark rim, its navy lower half and its pale
# upper-left spot are the drawn light (the game lights the ball, makes the shine and draws the
# outline), so the whole surface takes the ramp's mid-tone and only the swirl is painted: the dark
# groove and the pale crescent. The crescent is a marking, not a bulge; only the groove is cut in.
BODY_IDX = 55
GROOVE_IDX, GROOVE_W = 52, 0.8  # px: the painted half-width of the groove
CRESCENT_IDX, CRESCENT_W = 58, 0.75
GLASS = dict(metallic=0.05, roughness=0.12)


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = [common.palette_material(sprite, i, NAME, **GLASS) for i in (BODY_IDX, GROOVE_IDX, CRESCENT_IDX)]
    body_mat, groove_mat, crescent_mat = 0, 1, 2
    foot_mat = body_mat

    cx, cy = CENTRE
    a, b = RADII
    ze, rz = EQUATOR * PX, (TOP - EQUATOR) * PX

    def relief(c, r):
        dg, tg = lib._dist_polyline((c, r), GROOVE)
        fade_g = min(1.0, tg * 4, (1 - tg) * 4)
        return -RELIEF * PX * math.exp(-(dg / 0.8) ** 2) * fade_g

    def to_px(v):
        return v.x * 12 + 12 - 0.5, 14 - 0.5 - v.y * 12

    def paint(f):
        c, r = to_px(f.calc_center_median())
        dg, _ = lib._dist_polyline((c, r), GROOVE)
        dr, _ = lib._dist_polyline((c, r), RIDGE)
        if dg < GROOVE_W:
            f.material_index = groove_mat
        elif dr < CRESCENT_W:
            f.material_index = crescent_mat
        else:
            f.material_index = body_mat
        f.smooth = True

    bm = bmesh.new()
    # The cap: a square grid mapped onto the disc (no pole fan, so the painted bands lie on cells
    # about a sprite pixel across), lifted onto the ellipsoid, pressed in along the groove and
    # raised along the crescent.
    N = 22
    verts = {}
    for i in range(N + 1):
        for j in range(N + 1):
            x, y = -1 + 2 * i / N, -1 + 2 * j / N
            dx, dy = x * math.sqrt(1 - y * y / 2), y * math.sqrt(1 - x * x / 2)
            rho = math.hypot(dx, dy)
            ux, uy = (dx / rho, dy / rho) if rho > 1e-9 else (1.0, 0.0)
            ct = min(1.0, math.sin(rho * math.pi / 2))  # cos of the elevation angle
            st = math.sqrt(max(0.0, 1 - ct * ct))
            c, r = cx + a * ct * ux, cy + b * ct * uy
            n = Vector((ct * ux / a, -ct * uy / b, st / (rz / PX))).normalized()
            verts[i, j] = bm.verts.new(Vector((lib.X(c), lib.Y(r), ze + rz * st)) + n * relief(c, r) * st)
    for i in range(N):
        for j in range(N):
            paint(bm.faces.new((verts[i, j], verts[i + 1, j], verts[i + 1, j + 1], verts[i, j + 1])))

    # The cap's rim (the equator), walked round the square's edge.
    rim = ([verts[i, 0] for i in range(N)] + [verts[N, j] for j in range(N)]
           + [verts[i, N] for i in range(N, 0, -1)] + [verts[0, j] for j in range(N, 0, -1)])
    # Below the equator: the ball's underside curving in to a foot ring on the ground.
    O = Vector((lib.X(cx), lib.Y(cy), 0))
    rings, low_rings = [rim], 3
    for k in range(low_rings, 0, -1):
        t = (k - 1) / low_rings  # 1 just under the equator .. 0 on the ground
        sc = math.sqrt(max(0.0, 1 - (1 - FOOT ** 2) * (1 - t) ** 2))
        rings.append([bm.verts.new(Vector((O.x + (v.co.x - O.x) * sc, O.y + (v.co.y - O.y) * sc, ze * t)))
                      for v in rim])
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(len(rim)):
            k = (j + 1) % len(rim)
            f = bm.faces.new((r0[j], r0[k], r1[k], r1[j]))
            f.material_index = foot_mat
            f.smooth = True
    base = bm.faces.new(list(reversed(rings[-1])))
    base.material_index = foot_mat
    return lib.to_object(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.shell_main(NAME, build)
