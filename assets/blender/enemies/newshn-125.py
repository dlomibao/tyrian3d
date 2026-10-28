"""Small blue swirl orb (newshn.shp frame 125): a 3D version of its sprite.

Seen in level 2.4, lying on the ground. The sprite shades it as a glossy ball: a dark rim all
round, a pale highlight upper left, and a swirl marking inside it (a dark groove curving down
from the top edge round the middle, and a pale crescent round the lower right). So the model is
one near-spherical orb filling the sprite's 15 x 16 px circle and about 11 px tall, its surface
painted from the sprite's own palette ramp (lighter upper left, navy toward the rim), with the
groove pressed in and the crescent raised by under half a pixel. One frame, one model.

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
RELIEF = 0.4  # px: groove depth and crescent rise

# Palette ramp 48 (darkest navy) .. 62 (ice blue). The surface is painted in these bands; the
# sprite's black outline (index 1) counts as the darkest navy.
BANDS = [52, 54, 56, 58, 60, 62]
RIM_IDX, RIM_FROM = 49, 0.9  # a dark navy band round the outer edge, past this fraction of the radius
FOOT_IDX = 51


def ramp_sampler(sprite, sigma=0.4):
    """A smooth field of the sprite's ramp values (48..62), sampled at sprite (col, row) centre
    coordinates: the pixels blurred a little so the painted bands follow the shading, not the
    dithering. The black outline and the empty pixels round it count as dark navy."""
    pix = sprite["frames"][0]["pixels"]
    rows, cols = len(pix), len(pix[0])
    raw = [[float(v) if v >= 48 else 51.0 for v in row] for row in pix]
    k = int(math.ceil(2 * sigma))
    w = [math.exp(-(d / sigma) ** 2 / 2) for d in range(-k, k + 1)]

    def blur(get, n, m, axis):
        out = [[0.0] * m for _ in range(n)]
        for i in range(n):
            for j in range(m):
                acc = ws = 0.0
                for d, wd in zip(range(-k, k + 1), w):
                    ii, jj = (i + d, j) if axis == 0 else (i, j + d)
                    if 0 <= ii < n and 0 <= jj < m:
                        acc += get(ii, jj) * wd
                        ws += wd
                out[i][j] = acc / ws
        return out

    once = blur(lambda i, j: raw[i][j], rows, cols, 1)
    field = blur(lambda i, j: once[i][j], rows, cols, 0)

    def value(c, r):
        return field[min(max(r, 0), rows - 1)][min(max(c, 0), cols - 1)]

    def sample(c, r):
        c0, r0 = math.floor(c), math.floor(r)
        tc, tr = c - c0, r - r0
        return ((1 - tc) * (1 - tr) * value(c0, r0) + tc * (1 - tr) * value(c0 + 1, r0)
                + (1 - tc) * tr * value(c0, r0 + 1) + tc * tr * value(c0 + 1, r0 + 1))

    return sample


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = [common.palette_material(sprite, i, NAME, metallic=0.35, roughness=0.3) for i in BANDS]
    mats.append(common.palette_material(sprite, FOOT_IDX, NAME, metallic=0.3, roughness=0.5))
    foot_mat = len(mats) - 1
    mats.append(common.palette_material(sprite, RIM_IDX, NAME, metallic=0.35, roughness=0.3))
    rim_mat = len(mats) - 1
    sample = ramp_sampler(sprite)

    cx, cy = CENTRE
    a, b = RADII
    ze, rz = EQUATOR * PX, (TOP - EQUATOR) * PX

    def relief(c, r):
        dg, tg = lib._dist_polyline((c, r), GROOVE)
        dr, tr = lib._dist_polyline((c, r), RIDGE)
        fade_g = min(1.0, tg * 4, (1 - tg) * 4)
        fade_r = min(1.0, tr * 4, (1 - tr) * 4)
        return RELIEF * PX * (math.exp(-(dr / 0.9) ** 2) * fade_r - math.exp(-(dg / 0.8) ** 2) * fade_g)

    def to_px(v):
        return v.x * 12 + 12 - 0.5, 14 - 0.5 - v.y * 12

    def paint(f):
        c, r = to_px(f.calc_center_median())
        if math.hypot((c - cx) / a, (r - cy) / b) > RIM_FROM:
            f.material_index = rim_mat
        else:
            v = sample(c, r)
            f.material_index = min(range(len(BANDS)), key=lambda m: abs(BANDS[m] - v))
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
