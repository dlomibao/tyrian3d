"""Blue eyeball (newsh5.shp frames 127, 129, 131): a 3D version of its sprite.

Seen in episode 4 (levels 20 and 25). A glossy blue ball with a dark socket and black pupil
looking down the screen. The three frames turn the ball, so the ball's outline and the eye's shape
change: one model per frame (newsh5-127, newsh5-127-f2, newsh5-127-f3).

The ball is a full ellipsoid as tall as it is wide (its outline is the sprite's, dark rim
included), with the socket cut into it: a wall that is deep under the upper lid (the sprite's dark
shadow line) and shallow at the lit lower lip, a dished floor, and the pupil as a deeper pit. The
mesh is built in rings round the eye (pupil, floor, socket rim, then out to the ball's equator and
round underneath), so every rim is a smooth curve and the faces take their palette shade from the
sprite pixels above them.

Run: blender --background --python assets/blender/enemies/newsh5-127.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-127"
ROOT = common.repo_root(__file__)

# Per frame, in sprite pixels (column, row of pixel centres, fractional is fine): the ball (centre,
# half width, half height, out to the dark outline), the socket and the pupil seen from above
# (centre, rx, ry).
FRAMES = {
    127: {"body": (12.0, 12.0, 11.5, 9.5), "socket": (12.4, 14.1, 6.6, 3.7),
          "pupil": (13.0, 15.1, 2.6, 1.5)},
    129: {"body": (12.0, 12.0, 10.5, 10.5), "socket": (12.3, 14.2, 6.3, 4.5),
          "pupil": (13.0, 15.7, 1.8, 2.0)},
    131: {"body": (12.0, 12.0, 9.5, 11.5), "socket": (12.4, 14.4, 5.6, 5.5),
          "pupil": (12.7, 15.6, 1.7, 2.9)},
}

BALL_C = 10.0 / 12   # half height of the ball (units): as tall as it is wide
WALL_MAX = 2.0 / 12  # socket wall under the upper lid
WALL_MIN = 0.4 / 12  # ... and at the lower lip
FLOOR = 2.7 / 12     # floor depth at the pupil's edge
PUPIL = 1.4 / 12     # the pupil sinks this much further at its centre
SIDES = 40

# Palette shades the faces may take (the sprite's blue ramp), nearest wins.
BODY_RAMP = (52, 54, 56, 58, 59, 61)
FLOOR_RAMP = (50, 52, 54, 56, 58)
WALL_INDEX = 50
PUPIL_INDEX = 1
UNDER_INDEX = 54


def nearest(ramp, value):
    return min(ramp, key=lambda i: abs(i - value))


def build(sprite, pixels, name, frame):
    coll = common.reset_collection(name)
    indices = sorted(set(BODY_RAMP + FLOOR_RAMP + (WALL_INDEX, PUPIL_INDEX, UNDER_INDEX)))
    mats = [common.palette_material(sprite, i, name, metallic=0.1 if i > 1 else 0.0,
                                    roughness=0.3 if i > 1 else 0.75) for i in indices]
    slot = {i: k for k, i in enumerate(indices)}

    bc, br, ba, bb = frame["body"]
    bx, by, a, b = lib.px(bc), lib.row(br), ba / 12, bb / 12
    sc, sr, srx, sry = frame["socket"]
    sx, sy, srx, sry = lib.px(sc), lib.row(sr), srx / 12, sry / 12
    pc, pr, prx, pry = frame["pupil"]
    ppx, ppy, prx, pry = lib.px(pc), lib.row(pr), prx / 12, pry / 12

    def top(x, y):
        u = ((x - bx) / a) ** 2 + ((y - by) / b) ** 2
        return BALL_C * math.sqrt(max(0.0, 1 - u))

    angles = [2 * math.pi * k / SIDES for k in range(SIDES)]
    cs, sn = [math.cos(t) for t in angles], [math.sin(t) for t in angles]
    pupil_pt = [(ppx + prx * c, ppy + pry * s) for c, s in zip(cs, sn)]
    socket_pt = [(sx + srx * c, sy + sry * s) for c, s in zip(cs, sn)]
    body_pt = [(bx + a * c, by + b * s) for c, s in zip(cs, sn)]
    # Wall height: deepest under the upper lid (+Y), shallow at the lower lip.
    wall = [WALL_MIN + (WALL_MAX - WALL_MIN) * ((1 + s) / 2) ** 1.5 for s in sn]

    lerp = lambda p, q, t: (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)  # noqa: E731
    bm = bmesh.new()
    rings, kinds = [], []  # kinds[i] = material rule of the band between ring i and i + 1

    def ring(points, zs):
        rings.append([bm.verts.new((x, y, z)) for (x, y), z in zip(points, zs)])

    # Pupil: centre, an inner ring, its edge.
    centre = bm.verts.new((ppx, ppy, top(ppx, ppy) - FLOOR - PUPIL))
    for s, drop, kind in ((0.75, 0.95, "pupil"), (1.0, 0.0, "floor")):
        pts = [lerp((ppx, ppy), p, s) for p in pupil_pt]
        ring(pts, [top(x, y) - FLOOR - PUPIL * drop for x, y in pts])
        kinds.append(kind)
    # Floor: from the pupil's edge out to the foot of the socket wall, curving up as a dish.
    for t in (0.45, 0.8, 1.0):
        pts = [lerp(p, q, t) for p, q in zip(pupil_pt, socket_pt)]
        ring(pts, [top(x, y) - (w + (FLOOR - w) * (1 - t * t)) for (x, y), w in zip(pts, wall)])
        kinds.append("floor")
    kinds[-1] = "wall"
    # Socket lip on the ball's surface.
    ring(socket_pt, [top(x, y) for x, y in socket_pt])
    kinds.append("body")
    lip = len(rings) - 1
    # Out to the equator, denser toward it where the ball turns down.
    steps = 7
    for k in range(1, steps + 1):
        f = math.sin(math.pi / 2 * k / steps)
        pts = [lerp(p, q, f) for p, q in zip(socket_pt, body_pt)]
        ring(pts, [0.0 if k == steps else top(x, y) for x, y in pts])
        kinds.append("body")
    kinds[-1] = "under"
    # Underneath: the lower half of the ellipsoid.
    for deg in (70, 48, 26):
        phi = math.radians(deg)
        pts = [(bx + (x - bx) * math.sin(phi), by + (y - by) * math.sin(phi)) for x, y in body_pt]
        ring(pts, [-BALL_C * math.cos(phi)] * SIDES)
        kinds.append("under")
    pole = bm.verts.new((bx, by, -BALL_C))

    def face(verts, mat):
        f = bm.faces.new(verts)
        f.material_index = slot[mat]
        return f

    def shade(verts, ramp):
        """The sprite's palette index averaged over the face, nearest on the ramp."""
        cx = sum(v.co.x for v in verts) / len(verts)
        cy = sum(v.co.y for v in verts) / len(verts)
        pts = [(cx + (v.co.x - cx) * t, cy + (v.co.y - cy) * t) for v in verts for t in (0.5, 1.0)]
        pts += [(cx, cy)]
        vals = []
        for x, y in pts:
            i = lib.sample(pixels, x, y)
            if i >= 48:
                vals.append(max(i, 52) if ramp is BODY_RAMP else i)
        return nearest(ramp, sum(vals) / len(vals)) if vals else ramp[0]

    painted = []
    first = rings[0]
    for k in range(SIDES):
        face((centre, first[k], first[(k + 1) % SIDES]), PUPIL_INDEX)
    for i, kind in enumerate(kinds[:len(rings) - 1]):
        r0, r1 = rings[i], rings[i + 1]
        for k in range(SIDES):
            j = (k + 1) % SIDES
            quad = (r0[k], r0[j], r1[j], r1[k])
            if kind == "pupil":
                mat = PUPIL_INDEX
            elif kind == "wall":
                mat = WALL_INDEX
            elif kind == "floor":
                mat = shade(quad, FLOOR_RAMP)
            elif kind == "body":
                mat = shade(quad, BODY_RAMP)
            else:
                mat = UNDER_INDEX
            f = face(quad, mat)
            if kind in ("body", "floor"):
                painted.append(f)
    last = rings[-1]
    for k in range(SIDES):
        face((last[(k + 1) % SIDES], last[k], pole), UNDER_INDEX)

    # Drop speckles: a painted face whose neighbours mostly share another shade takes it.
    painted_set = set(painted)
    new_index = {}
    for f in painted:
        counts = {}
        for e in f.edges:
            for g in e.link_faces:
                if g is not f and g in painted_set:
                    counts[g.material_index] = counts.get(g.material_index, 0) + 1
        best = max(counts, key=counts.get) if counts else f.material_index
        if best != f.material_index and counts[best] >= 3:
            new_index[f] = best
    for f, i in new_index.items():
        f.material_index = i

    # Crisp edges at the socket lip and the pupil's rim.
    for r in (rings[lip], rings[1]):
        for k in range(SIDES):
            e = bm.edges.get((r[k], r[(k + 1) % SIDES]))
            if e:
                e.smooth = False
    return common.mesh_object(name, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    pixels_of = {int(f["image"].rsplit("-", 1)[1].split(".")[0]): f["pixels"] for f in sprite["frames"]}
    for i, (index, frame) in enumerate(FRAMES.items()):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, pixels_of[index], name, frame)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", [{**base, "frames": [index]}])
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            ref = ROOT / "reference" / "models" / NAME / f"frame-newsh5-{index}.png"
            common.render_preview([obj], out.with_name(f"{name}.png"), ref, size=2)


if __name__ == "__main__":
    main()
