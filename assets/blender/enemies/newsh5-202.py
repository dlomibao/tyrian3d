"""Small grey eyeball (newsh5.shp frames 202, 221): a 3D version of its sprite.

Seen in episode 4 (level 20). A small grey ball with a dark socket and pupil looking down the
screen. The two frames turn the ball (round, then tall and narrow), so each gets a model:
newsh5-202 and newsh5-202-f2.

The ball is a full sphere (as tall as it is wide, centred on the midplane). The sprite's light is
not painted on: the ball is one wet, glossy grey (the sprite's mid grey) all over, so the game's
lights make its upper-left highlight and darker edges, and the game draws its dark outline. The
socket is cut about 2.1 px in along the sprite's dark pixels and is one glossy dark grey (the
sprite's mid socket shade); the sprite's one light pixel inside it is the pupil's glint, which the
glossy material catches, so it isn't modelled.

Run: blender --background --python assets/blender/enemies/newsh5-202.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-202"
ROOT = common.repo_root(__file__)

# Per frame, in sprite pixels (12x14 tile, pixel-centre columns and rows): the ball (centre col,
# row, half width, half height) and its half depth; the socket's pixels (col, row) and the glint
# pixel.
FRAMES = {
    202: {"body": (6.0, 6.0, 5.55, 5.55), "depth": 5.5,
          "socket": [(5, 6), (6, 6), (7, 6),
                     (4, 7), (5, 7), (6, 7), (7, 7), (8, 7),
                     (4, 8), (5, 8), (6, 8), (7, 8), (8, 8),
                     (4, 9), (5, 9), (6, 9), (7, 9)], "glint": (5, 7)},
    221: {"body": (6.0, 6.0, 4.55, 6.55), "depth": 5.0,
          "socket": [(6, 5),
                     (5, 6), (6, 6), (7, 6),
                     (5, 7), (6, 7), (7, 7),
                     (5, 8), (6, 8), (7, 8),
                     (5, 9), (6, 9), (7, 9),
                     (5, 10), (6, 10), (7, 10)], "glint": (6, 6)},
}
# "glint" is kept for reference only: the pupil's highlight comes from the glossy material.

SOCKET_DEPTH = 2.1 / 12  # how far the socket floor sits below the ball's surface
RAYS = 40  # vertices around the ball
INNER_RINGS = 4  # body rings between the socket edge and the first latitude line
# Latitude lines (degrees from the top) the body's rings run along out to the equator (90), dense
# near the rim so the elevations' outline stays round.
LATITUDES = (44, 51, 59, 66, 73, 80, 85, 90)
BOTTOM_RINGS = 4  # latitude bands under the equator
BODY = 9  # palette index of the ball: the sprite's mid grey (its body runs 8-12; the lights add the rest)
SOCKET = 3  # palette index of the socket: the sprite's mid socket shade (it runs 1-7)
# Materials: the eyeball is wet and glossy, so the shine is the material's, not geometry or paint.
GLOSS = {BODY: dict(metallic=0.05, roughness=0.25), SOCKET: dict(metallic=0.05, roughness=0.1)}


class Ball:
    """An ellipsoid centred at (x0, y0, 0) with semi-axes a, b, c."""

    def __init__(self, x0, y0, a, b, c):
        self.x0, self.y0, self.a, self.b, self.c = x0, y0, a, b, c

    def top(self, x, y):
        u = ((x - self.x0) / self.a) ** 2 + ((y - self.y0) / self.b) ** 2
        return self.c * math.sqrt(max(0.0, 1 - u))


def socket_radii(cells, sx, sy, dirs):
    """Per ray from the socket centre (sx, sy), how far it runs inside the socket's pixels,
    lightly smoothed over neighbouring rays so the pixel staircase becomes an irregular blob."""
    raw = []
    for dx, dy in dirs:
        t, step = 0.0, 0.01
        while True:
            x, y = sx + dx * (t + step), sy + dy * (t + step)
            c, r = int(round(lib.to_col(x, 1))), int(round(lib.to_row(y, 1)))
            if (c, r) not in cells:
                break
            t += step
        raw.append(t)
    n = len(raw)
    return [(raw[i - 1] + 2 * raw[i] + raw[(i + 1) % n]) / 4 for i in range(n)]


def paint(faces, index):
    for f in faces:
        f.material_index = index


def eyeball(bm, frame):
    bc, br, ba, bb = frame["body"]
    ball = Ball(lib.px(bc, 1), lib.row(br, 1), ba / 12, bb / 12, frame["depth"] / 12)
    cells = set(frame["socket"])
    sx = sum(lib.px(c, 1) for c, _ in cells) / len(cells)
    sy = sum(lib.row(r, 1) for _, r in cells) / len(cells)

    # Rim points evenly round the equator; each ray runs from the socket centre to one of them.
    rim, dirs = [], []
    for j in range(RAYS):
        phi = 2 * math.pi * j / RAYS
        px, py = ball.x0 + ball.a * math.cos(phi), ball.y0 + ball.b * math.sin(phi)
        ln = math.hypot(px - sx, py - sy)
        rim.append((px, py, phi))
        dirs.append(((px - sx) / ln, (py - sy) / ln))
    rho = socket_radii(cells, sx, sy, dirs)
    edge = [(sx + dx * r, sy + dy * r) for (dx, dy), r in zip(dirs, rho)]

    def ring(points, z_of):
        return [bm.verts.new((x, y, z_of(x, y))) for x, y in points]

    part = []  # the faces of the part being built

    def band(inner, outer):
        for j in range(RAYS):
            k = (j + 1) % RAYS
            part.append(bm.faces.new((inner[j], outer[j], outer[k], inner[k])))

    def fan(centre, outer, reverse=False):
        for j in range(RAYS):
            k = (j + 1) % RAYS
            part.append(bm.faces.new((centre, outer[j], outer[k]) if not reverse else (outer[j], centre, outer[k])))

    def scaled(s):
        return [(sx + (x - sx) * s, sy + (y - sy) * s) for x, y in edge]

    # Socket: a floor following the ball's curve SOCKET_DEPTH down, steep walls up to the surface.
    floor = lambda x, y: ball.top(x, y) - SOCKET_DEPTH  # noqa: E731
    prev = bm.verts.new((sx, sy, floor(sx, sy)))
    first = True
    for s in (0.3, 0.6, 0.84):
        cur = ring(scaled(s), floor)
        if first:
            fan(prev, cur)
            first = False
        else:
            band(prev, cur)
        prev = cur
    band(prev, ring(edge, lambda x, y: ball.top(x, y) + 0.002))
    # The socket is one dark grey; the recess and the light shade it.
    paint(part, SOCKET)
    part.clear()

    # Body: its own ring on the socket edge (a sharp lip), then rings spaced along each ray, then
    # latitude lines out to the equator, then under it to the bottom pole.
    def at_latitude(j, theta):
        """Where ray j crosses the ball's latitude `theta` (from the top), seen from above."""
        (dx, dy), s2 = dirs[j], math.sin(theta) ** 2
        ox, oy = (sx - ball.x0) / ball.a, (sy - ball.y0) / ball.b
        ux, uy = dx / ball.a, dy / ball.b
        qa, qb, qc = ux * ux + uy * uy, 2 * (ox * ux + oy * uy), ox * ox + oy * oy - s2
        t = (-qb + math.sqrt(max(0.0, qb * qb - 4 * qa * qc))) / (2 * qa)
        return sx + dx * t, sy + dy * t

    prev = ring(edge, ball.top)
    inner = [at_latitude(j, math.radians(LATITUDES[0])) for j in range(RAYS)]
    for k in range(1, INNER_RINGS + 1):
        f = k / (INNER_RINGS + 1)
        cur = ring([(ex + (ix - ex) * f, ey + (iy - ey) * f) for (ex, ey), (ix, iy) in zip(edge, inner)],
                   ball.top)
        band(prev, cur)
        prev = cur
    for deg in LATITUDES:
        if deg >= 90:
            cur = [bm.verts.new((x, y, 0.0)) for x, y, _ in rim]
        else:
            cur = ring([at_latitude(j, math.radians(deg)) for j in range(RAYS)], ball.top)
        band(prev, cur)
        prev = cur
    for i in range(1, BOTTOM_RINGS):
        lat = math.pi / 2 * i / BOTTOM_RINGS
        cur = [bm.verts.new((ball.x0 + ball.a * math.cos(lat) * math.cos(phi),
                             ball.y0 + ball.b * math.cos(lat) * math.sin(phi),
                             -ball.c * math.sin(lat))) for _, _, phi in rim]
        band(prev, cur)
        prev = cur
    fan(bm.verts.new((ball.x0, ball.y0, -ball.c)), prev, reverse=True)
    # The whole ball, top to bottom, is one grey: the sprite's outline ring and its shading are the
    # game's outline and lights.
    paint(part, BODY)
    return ball


def build(sprite, name, index, frame):
    coll = common.reset_collection(name)
    bm = bmesh.new()
    eyeball(bm, frame)
    # Palette indices to material slots, in index order.
    used = sorted({f.material_index for f in bm.faces})
    slot = {i: s for s, i in enumerate(used)}
    for f in bm.faces:
        f.material_index = slot[f.material_index]
    mats = [common.palette_material(sprite, i, name, **GLOSS[i]) for i in used]
    return common.mesh_object(name, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    for i, (index, frame) in enumerate(FRAMES.items()):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, name, index, frame)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", [{**base, "frames": [index]}])
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            ref = ROOT / "reference" / "models" / NAME / f"frame-newsh5-{index}.png"
            common.render_preview([obj], out.with_name(f"{name}.png"), ref, size=1)


if __name__ == "__main__":
    main()
