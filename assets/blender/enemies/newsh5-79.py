"""Green eye pod (newsh5.shp frame 79): a 3D version of its sprite.

Seen in episode 4 (EYESPY, 4.13 / main=20). The mother eye of a flight of small grey eyeballs
(newsh5-202 rides at dx -16 / +14 and is launched by it), so it is built the same way they are:
a full, faired ball (as deep as it is wide) with a socket pressed into it, looking down the screen.

Reading the sprite (rubric "Reading a sprite"): a round green ball 19 px across inside its ink ring,
lit from the top left (the 45-47 hot spot is sheen, the dark lower edge is shadow). In its lower
half a crater: its upper wall in shadow, its lower right wall catching the light, and in it a dark
glossy lens with a glint at its upper left (the glint is the gloss, not modelled).

Build: one closed mesh made of rays from the socket centre out to the equator. Along each ray the
socket's floor (the ball's curve, sunk SOCKET_DEPTH), an S-curve wall with a rounded lip, then the
ball's surface out to the equator and under it to the bottom pole. In the socket a seat ring
(machined bezel) and the lens: a glossy dark dome whose axis is the ball's normal at the socket, so
the eye looks forward and down like its escorts. Colours are the sprite's per-region medians:
body 41, socket wall 38, lens 34. Outline shell from a sealed copy (D51).

Run: blender --background --python assets/blender/enemies/newsh5-79.py [-- --preview out.png]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


def find_repo():
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "package.json").exists() and (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("repo root not found")


ROOT = find_repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
import common  # noqa: E402

NAME = "newsh5-79"
PX = 1 / 12
W, H = 24, 28


def ex(e):  # pixel edge column -> X
    return (e - W / 2) * PX


def ey(e):  # pixel edge row -> Y (sprite up is +Y)
    return (H / 2 - e) * PX


# --- Shape, in sprite pixel edges ------------------------------------------------------------------
BALL = (12.5, 12.5, 9.62)          # centre col, row, radius (inner mask: cols/rows 3-21)
SOCKET = (12.6, 15.0, 6.5, 5.25)   # top-view centre and half axes of the socket's lip
SOCKET_DEPTH = 2.4                 # px the floor sits below the ball's surface
LENS = (12.85, 15.6, 3.35, 1.75)   # top-view centre, radius, dome height above the floor (px)
BEZEL = 0.55                       # seat ring tube radius (px)
RAYS = 72

BODY, WALL, LENS_I = 41, 38, 34
GLOSS = {BODY: dict(metallic=0.05, roughness=0.22),   # satin, glossy shell (sheen does the hot spot)
         WALL: dict(metallic=0.05, roughness=0.35),
         LENS_I: dict(metallic=0.0, roughness=0.06)}  # wet dark lens


class Ball:
    def __init__(self):
        c, r, rad = BALL
        self.x0, self.y0, self.r = ex(c), ey(r), rad * PX

    def top(self, x, y):
        u = ((x - self.x0) ** 2 + (y - self.y0) ** 2) / self.r ** 2
        return self.r * math.sqrt(max(0.0, 1 - u))

    def normal(self, x, y):
        return Vector((x - self.x0, y - self.y0, self.top(x, y))).normalized()


def smooth_s(u):
    """S-curve 0..1 with flat ends: the rounded lip (u=1) and floor fillet (u=0)."""
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (6 * u - 15) + 10)


def body(bm, ball):
    """The ball with its socket: one closed mesh. Returns the faces per material."""
    scx, scy, sax, say = SOCKET
    sx, sy = ex(scx), ey(scy)
    a, b = sax * PX, say * PX
    rim, dirs, rho = [], [], []
    for j in range(RAYS):
        phi = 2 * math.pi * j / RAYS
        px_, py_ = ball.x0 + ball.r * math.cos(phi), ball.y0 + ball.r * math.sin(phi)
        ln = math.hypot(px_ - sx, py_ - sy)
        dx, dy = (px_ - sx) / ln, (py_ - sy) / ln
        rim.append((px_, py_, phi))
        dirs.append((dx, dy))
        rho.append(1 / math.sqrt((dx / a) ** 2 + (dy / b) ** 2))  # ray meets the lip ellipse
    D = SOCKET_DEPTH * PX
    faces = {BODY: [], WALL: []}

    def depth(t):  # t = fraction of the lip radius along the ray
        if t <= 0.62:
            return D
        return D * (1 - smooth_s((t - 0.62) / 0.38))

    def ring_at(t, z_extra=0.0):
        out = []
        for (dx, dy), r in zip(dirs, rho):
            x, y = sx + dx * r * t, sy + dy * r * t
            out.append(bm.verts.new((x, y, ball.top(x, y) - depth(t) + z_extra)))
        return out

    def band(inner, outer, mat):
        for j in range(RAYS):
            k = (j + 1) % RAYS
            faces[mat].append(bm.faces.new((inner[j], outer[j], outer[k], inner[k])))

    # socket floor and wall
    centre = bm.verts.new((sx, sy, ball.top(sx, sy) - D))
    ts = [0.2, 0.4, 0.62, 0.72, 0.8, 0.87, 0.93, 0.97, 1.0]
    prev = ring_at(ts[0])
    for j in range(RAYS):
        faces[WALL].append(bm.faces.new((centre, prev[j], prev[(j + 1) % RAYS])))
    for t in ts[1:]:
        cur = ring_at(t)
        band(prev, cur, WALL if t <= 0.93 else BODY)
        prev = cur
    # the ball's surface from the lip out to the equator (denser toward the rim, where it steepens)
    edge = [(sx + dx * r, sy + dy * r) for (dx, dy), r in zip(dirs, rho)]
    n_out = 12
    for i in range(1, n_out + 1):
        g = math.sin(i / n_out * math.pi / 2)
        g = 0.5 * g + 0.5 * (i / n_out) ** 0.7 if i < n_out else 1.0
        cur = []
        for (exx, eyy), (rx, ry, _) in zip(edge, rim):
            x, y = exx + (rx - exx) * g, eyy + (ry - eyy) * g
            cur.append(bm.verts.new((x, y, 0.0 if i == n_out else ball.top(x, y))))
        band(prev, cur, BODY)
        prev = cur
    # under the equator to the bottom pole (a plain closed half: undersides get no detail)
    nb = 8
    for i in range(1, nb):
        lat = math.pi / 2 * i / nb
        cur = [bm.verts.new((ball.x0 + ball.r * math.cos(lat) * math.cos(phi),
                             ball.y0 + ball.r * math.cos(lat) * math.sin(phi),
                             -ball.r * math.sin(lat))) for _, _, phi in rim]
        band(prev, cur, BODY)
        prev = cur
    pole = bm.verts.new((ball.x0, ball.y0, -ball.r))
    for j in range(RAYS):
        faces[BODY].append(bm.faces.new((prev[(j + 1) % RAYS], prev[j], pole)))
    return faces, (sx, sy, D)


def lens_frame(ball, sx, sy):
    """Matrix placing the lens: origin on the socket floor under the lens centre, +Z along the
    ball's normal there (so the eye looks forward and down)."""
    lx, ly = ex(LENS[0]), ey(LENS[1])
    n = ball.normal(lx, ly)
    floor = ball.top(lx, ly) - SOCKET_DEPTH * PX
    rot = n.to_track_quat("Z", "Y").to_matrix().to_4x4()
    return Matrix.Translation((lx, ly, floor)) @ rot


def lens(bm, frame):
    """The lens: a glossy spheroid, its upper half standing out of the floor (lower half buried)."""
    r, h = LENS[2] * PX, LENS[3] * PX
    segs, rings = 40, 14
    verts = []
    top = bm.verts.new(frame @ Vector((0, 0, h)))
    bot = bm.verts.new(frame @ Vector((0, 0, -h * 0.6)))
    for i in range(1, rings):
        th = math.pi * i / rings
        z = math.cos(th)
        rr = math.sin(th)
        ring = [bm.verts.new(frame @ Vector((r * rr * math.cos(2 * math.pi * k / segs),
                                              r * rr * math.sin(2 * math.pi * k / segs),
                                              (h if z > 0 else h * 0.6) * z))) for k in range(segs)]
        verts.append(ring)
    fs = []
    for k in range(segs):
        fs.append(bm.faces.new((top, verts[0][k], verts[0][(k + 1) % segs])))
        fs.append(bm.faces.new((bot, verts[-1][(k + 1) % segs], verts[-1][k])))
    for a, b_ in zip(verts, verts[1:]):
        for k in range(segs):
            k2 = (k + 1) % segs
            fs.append(bm.faces.new((a[k], b_[k], b_[k2], a[k2])))
    return fs


def bezel(bm, frame):
    """A machined seat ring round the lens's base, half sunk in the floor."""
    R, tr = LENS[2] * PX + BEZEL * PX * 0.6, BEZEL * PX
    segs, sides = 48, 10
    rings = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        ca, sa = math.cos(a), math.sin(a)
        ring = []
        for s in range(sides):
            t = 2 * math.pi * s / sides
            rr = R + tr * math.cos(t)
            ring.append(bm.verts.new(frame @ Vector((rr * ca, rr * sa, tr * 0.9 * math.sin(t) + 0.15 * tr))))
        rings.append(ring)
    fs = []
    for k in range(segs):
        a, b_ = rings[k], rings[(k + 1) % segs]
        for s in range(sides):
            s2 = (s + 1) % sides
            fs.append(bm.faces.new((a[s], b_[s], b_[s2], a[s2])))
    return fs


def build(sprite):
    coll = common.reset_collection(NAME)
    ball = Ball()
    bm = bmesh.new()
    faces, (sx, sy, _) = body(bm, ball)
    fr = lens_frame(ball, sx, sy)
    faces[LENS_I] = lens(bm, fr)
    faces[WALL] += bezel(bm, fr)
    used = sorted(faces)
    for slot, idx in enumerate(used):
        for f in faces[idx]:
            f.material_index = slot
    mats = [common.palette_material(sprite, i, NAME, **GLOSS[i]) for i in used]
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    # Sealed pre-cull copy for the shell: the ball alone is closed; lens and bezel sit inside it.
    shell = common.outline_shell(obj, coll, voxel=0.01, faces=1600, smooth=4, inside=0.002, islands="outer")
    assert len(shell.data.polygons) > 0, "empty outline shell"
    return obj, shell


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj, shell = build(sprite)
    objs = [obj, shell]
    common.export_sprite_model(ROOT, objs, f"enemies/{NAME}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview(objs, out, ref, size=sprite["frames"][0]["size"], frame=sprite["frames"][0]["index"])


main()
