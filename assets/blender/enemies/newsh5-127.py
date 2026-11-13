"""Design A: blue eyeball (newsh5.shp frames 127, 129, 131), one model per frame.

What it is: a living eyeball, a glossy blue ball looking down the screen (toward the player). The
sprite's lower half is the eye: a dark round iris set into the ball under a shadowed upper rim, a
black pupil, and the lit lower-right inside wall of the recess. The three frames turn the eye: the
ball goes from wide (127) to round (129) to tall (131) and the iris and pupil with it, so each
frame gets its own model (newsh5-127, newsh5-127-f2, newsh5-127-f3), as the game's model does.

Build: the ball is an ellipsoid whose top view is the sprite's inner mask (inside the 1 px ink
ring, D74). The eye is built in rings round the pupil, mapped in the top view from the pupil's
ellipse to the iris (socket) ellipse to the ball's equator, so every rim matches the sprite's
ellipses exactly from above:
  - pupil: a black pit with a crisp rim and a thin dark pupillary ruff round it;
  - iris: a shallow dish, deeper at the pupil, carrying modelled radial striations (fibres) and a
    raised collarette ring a third of the way out, then a dark limbal band;
  - socket wall: deep under the upper rim (the sprite's dark shadow arc), shallow at the lower lip
    (the sprite's lit inner wall), rolled into the ball over a faired fillet with a slight raised
    limbus lip, no razor edge;
  - the ball runs on over the equator and closes underneath (plain, art rule 3).
The ball is near round (half height 9.6 px) and its crown leans back (LEAN): same top-view outline,
but the front sits lower, so under the tilted game camera the eye faces the player and sits in the
lower half of the ball as drawn. The wall fairs back into the ball over a brow outside the lip and
the recess fades out low on the ball, so side and front profiles stay smooth (no notch, no slice).
Colours (median of each region, shading and highlights ignored): ball 58, iris 53, limbus and ruff
51, wall 52, pupil 1. The white patch upper left is sheen of a wet, glossy surface (art rule 2):
the ball is smooth dielectric, not metal. Outline shell (D51) from a sealed copy (a plain ellipsoid
with the eye filled), so the ink rings the silhouette only and never strokes the socket.

Run: blender --background --python assets/blender/enemies/newsh5-127.py
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402

ROOT = common.repo_root(__file__)

NAME = "newsh5-127"

# Per frame, in sprite pixels (pixel-centre column, row; half sizes to the pixel edges): the ball
# at the inner edge of the ink ring, the iris socket and the pupil as seen from above.
FRAMES = {
    127: {"body": (12.0, 12.0, 10.5, 8.5), "socket": (12.6, 15.3, 7.0, 4.5), "pupil": (12.4, 15.1, 2.6, 1.6)},
    129: {"body": (12.0, 12.0, 9.5, 9.5), "socket": (12.5, 15.2, 6.6, 5.0), "pupil": (12.8, 15.2, 1.9, 2.3)},
    131: {"body": (12.0, 12.0, 8.5, 10.5), "socket": (12.5, 15.2, 5.8, 6.0), "pupil": (12.4, 15.6, 1.8, 3.1)},
}

PX = 1 / 12
BALL_C = 9.6 * PX      # half height of the ball: near round, so the crown falls away and lights
                       # as a sphere under the tilted camera, not a puck
LEAN = 0.42            # the crown leans back: the ball is a little lower at the front and higher at
                       # the back (same top-view outline), so the eye on its front faces the tilted
                       # game camera and sits in the lower half of the ball on screen, as drawn
WALL_MAX = 0.85 * PX   # socket wall under the upper rim
WALL_MIN = 0.35 * PX   # ... and at the lower lip
BROW = 0.45            # stations over which the wall's depth fairs back into the ball outside the
                       # socket lip at the upper rim (a smooth brow, no step in the side profile)
BROW_LOW = 0.12        # ... and at the lower lip
FLOOR = 0.9 * PX       # iris depth at the pupil's edge (shallow: the dark colours make the recess)
PIT = 1.3 * PX         # the pupil sinks this much further
COLLARETTE = 0.22 * PX
STRIA_N = 18           # radial fibres round the iris
STRIA_H = 0.10 * PX
LIP = 0.10 * PX        # raised limbus lip just outside the socket
SIDES = 72

BALL, IRIS, LIMBUS, WALL, PUPIL = 58, 53, 51, 52, 1
# (metallic, roughness, Specular IOR Level): the ball is wet and glossy, so the renderer puts tight
# sheen spots on it (art rule 2, D176). A touch of metallic keeps it the sprite's steel-blue under the
# game's sky-tinted hemisphere light (fully dielectric it lit a pale, saturated cyan, flat to the rim).
# The eye inside is satin and a little metallic (less flat diffuse from the overhead sun), so it
# stays the sprite's dark recess (53/51/52 in game, not a pale dish); the pupil is a black hole.
FINISH = {BALL: (0.12, 0.2, 0.8), IRIS: (0.5, 0.55, 0.3), LIMBUS: (0.5, 0.55, 0.3), WALL: (0.5, 0.5, 0.3),
          PUPIL: (0.0, 0.5, 0.25)}


def px(c):
    return (c + 0.5 - 12) / 12


def row(r):
    return (14 - (r + 0.5)) / 12


def arg(flag, default=None):
    a = sys.argv
    return a[a.index(flag) + 1] if flag in a else default


def ellipse_of(fr, key):
    c, r, rx, ry = fr[key]
    return px(c), row(r), rx * PX, ry * PX


def build(sprite, name, fr, coll):
    indices = sorted(FINISH)
    mats = []
    for i in indices:
        m = common.palette_material(sprite, i, name, metallic=FINISH[i][0], roughness=FINISH[i][1])
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = FINISH[i][2]
        mats.append(m)
    slot = {i: k for k, i in enumerate(indices)}
    bx, by, a, b = ellipse_of(fr, "body")
    sx, sy, srx, sry = ellipse_of(fr, "socket")
    ppx, ppy, prx, pry = ellipse_of(fr, "pupil")

    def cz(y):
        """Crown height scale along the ball: lower at the front, higher at the back (LEAN)."""
        return BALL_C * (1 + LEAN * (y - by) / b)

    def top(x, y):
        u = ((x - bx) / a) ** 2 + ((y - by) / b) ** 2
        return cz(y) * math.sqrt(max(0.0, 1 - u))

    th = [2 * math.pi * k / SIDES for k in range(SIDES)]
    cs, sn = [math.cos(t) for t in th], [math.sin(t) for t in th]
    P = [(ppx + prx * c, ppy + pry * s) for c, s in zip(cs, sn)]
    S = [(sx + srx * c, sy + sry * s) for c, s in zip(cs, sn)]
    B = [(bx + a * c, by + b * s) for c, s in zip(cs, sn)]
    # Wall depth: deepest under the upper rim (+Y), shallow at the lower lip.
    wall = [WALL_MIN + (WALL_MAX - WALL_MIN) * max(0.0, (1 + s) / 2) ** 1.4 for s in sn]
    brow = [BROW_LOW + (BROW - BROW_LOW) * max(0.0, (1 + s) / 2) ** 1.2 for s in sn]
    # Radial fibres: narrow ridges, irregular in height so they read as tissue, not a gear.
    stria = [(0.5 + 0.5 * math.cos(STRIA_N * t)) ** 4 * (0.65 + 0.35 * math.sin(5 * t + 1.3) * math.cos(3 * t))
             for t in th]

    def point(k, s):
        """Top-view point of radial line k at station s: 0 pupil centre, 1 pupil edge, 2 socket
        lip, 3 ball equator."""
        if s <= 1:
            return (ppx + (P[k][0] - ppx) * s, ppy + (P[k][1] - ppy) * s)
        if s <= 2:
            t = s - 1
            return (P[k][0] + (S[k][0] - P[k][0]) * t, P[k][1] + (S[k][1] - P[k][1]) * t)
        t = math.sin(math.pi / 2 * (s - 2))
        return (S[k][0] + (B[k][0] - S[k][0]) * t, S[k][1] + (B[k][1] - S[k][1]) * t)

    def depth(k, s):
        """How far below the ball's surface station s of line k lies (negative = proud)."""
        w = wall[k]
        if s <= 1.0:  # pupil pit, a rounded bowl with a crisp rim
            return FLOOR + PIT * (1 - s ** 4) ** 0.5 if s < 1 else FLOOR
        if s <= 1.94:  # iris dish from the pupil out to the foot of the wall
            u = (s - 1) / 0.94
            d = FLOOR + (w - FLOOR) * u ** 1.6
            d -= COLLARETTE * math.exp(-((u - 0.3) / 0.07) ** 2)          # collarette ring
            d -= 0.08 * PX * math.exp(-((u - 0.05) / 0.05) ** 2)           # pupillary ruff
            fade = math.sin(math.pi * min(1, max(0, (u - 0.1) / 0.8)))     # fibres die out at both ends
            return d - STRIA_H * stria[k] * fade
        # Wall: falls from the iris to the lip, then fairs on outside the lip over a brow (wide at
        # the upper rim, narrow at the lower lip) back into the ball, so the profile seen from the
        # side or front is a smooth curve into a recess, never a step or a sliced-off cap.
        f = brow[k]
        w_lip = w * 0.42  # depth left at the coloured lip line; the rest fairs away outside it
        if s <= 2.0:
            v = (s - 1.94) / 0.06
            return w_lip + (w - w_lip) * (1 - v * v * (3 - 2 * v))
        v = min(1.0, (s - 2.0) / f)
        d = w_lip * (1 - v) ** 2 * (1 + 2 * v) if v < 1 else 0.0  # C1 smooth to zero
        if sn[k] < 0:  # a faint raised limbus lip on the lower half only (the lit lower rim)
            d -= LIP * (-sn[k]) * math.exp(-((s - 2.0 - 0.04) / 0.04) ** 2)
        return d

    stations = ([0.35, 0.65, 0.85, 0.96, 1.0, 1.03, 1.06, 1.1]
                + [1.1 + 0.84 * i / 12 for i in range(1, 13)]
                + [1.955, 1.97, 1.985, 2.0, 2.025, 2.05, 2.08, 2.12, 2.17, 2.23, 2.3, 2.38]
                + [2.38 + 0.62 * (i / 8) ** 0.9 for i in range(1, 9)])

    def material_at(s0, s1):
        m = 0.5 * (s0 + s1)
        if m < 1.0:
            return PUPIL
        if m < 1.06:
            return LIMBUS  # dark pupillary margin
        if m < 1.83:
            return IRIS
        if m < 1.94:
            return LIMBUS  # dark limbal band
        if m < 2.0:
            return WALL
        return BALL

    def pos(k, s):
        """The point of station s on line k: on the ball, or `depth` in from it along the ball's
        normal (not straight down: near the equator a vertical offset would bite a deep notch
        out of the ball's profile)."""
        x, y = point(k, s)
        if s >= 3.0:
            return (x, y, 0.0)
        z = top(x, y)
        d = depth(k, s)
        if d > 0:
            # near the ball's silhouette (low on the ball) the recess fades out, so the lower lip
            # never bites the outline seen from the front or low angles
            d *= min(1.0, (z / cz(y)) / 0.45) ** 1.5
        # normal of the leaning ball, from its implicit form u + (z / cz(y))^2 = 1
        c = cz(y)
        nx = (x - bx) / a ** 2
        ny = (y - by) / b ** 2 - z * z * BALL_C * LEAN / (b * c ** 3)
        nz = z / c ** 2
        ln = math.sqrt(nx * nx + ny * ny + nz * nz)
        return (x - d * nx / ln, y - d * ny / ln, z - d * nz / ln)

    bm = bmesh.new()
    rings = []
    for s in stations:
        r = []
        for k in range(SIDES):
            r.append(bm.verts.new(pos(k, s)))
        rings.append(r)
    # Underneath: the lower half of the ellipsoid, a plain closed shape.
    for deg in (82, 74, 66, 58, 50, 42, 34, 26, 18, 10):
        phi = math.radians(deg)
        rings.append([bm.verts.new((bx + (B[k][0] - bx) * math.sin(phi), by + (B[k][1] - by) * math.sin(phi),
                                    -BALL_C * math.cos(phi))) for k in range(SIDES)])
    stations += [3.5] * 10
    centre = bm.verts.new(pos(0, 0.0))
    pole = bm.verts.new((bx, by, -BALL_C))

    def face(vs, mat):
        f = bm.faces.new(vs)
        f.material_index = slot[mat]
        f.smooth = True

    for k in range(SIDES):
        face((centre, rings[0][k], rings[0][(k + 1) % SIDES]), PUPIL)
    for i in range(len(rings) - 1):
        mat = material_at(stations[i], stations[i + 1])
        for k in range(SIDES):
            j = (k + 1) % SIDES
            face((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]), mat)
    for k in range(SIDES):
        face((rings[-1][(k + 1) % SIDES], rings[-1][k], pole), BALL)
    # Crisp edge only at the pupil's rim; everything else is faired.
    ri = stations.index(1.0)
    for k in range(SIDES):
        e = bm.edges.get((rings[ri][k], rings[ri][(k + 1) % SIDES]))
        if e:
            e.smooth = False
    obj = common.mesh_object(name, bm, mats, coll, smooth=None)
    return obj


def sealed_shell(name, fr, coll):
    """Outline shell from a sealed copy: the plain ellipsoid, eye filled (D51/D189)."""
    bx, by, a, b = ellipse_of(fr, "body")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=1.0)
    for v in bm.verts:
        lean = 1 + LEAN * v.co.y if v.co.z > 0 else 1.0  # the body's leaning crown
        v.co = (bx + v.co.x * a, by + v.co.y * b, v.co.z * BALL_C * lean)
    src = common.mesh_object(f"{name}_sealed", bm, [], coll, smooth=True)
    sh = common.outline_shell(src, coll, faces=1600, islands="outer")
    bpy.data.objects.remove(src, do_unlink=True)
    bpy.context.view_layer.update()
    sh.name = f"{name}_outline"
    sh.data.name = f"{name}_outline"
    return sh


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    coll = common.reset_collection(NAME)
    for k, (frame, fr) in enumerate(FRAMES.items()):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj = build(sprite, name, fr, coll)
        sh = sealed_shell(name, fr, coll)
        assert len(sh.data.polygons) > 0, f"{sh.name}: empty outline shell"
        common.export_sprite_model(ROOT, [obj, sh], f"enemies/{name}", [{**base, "frames": [frame]}])


if __name__ == "__main__":
    main()
