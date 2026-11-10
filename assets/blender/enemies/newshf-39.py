"""Design A for newshf-39 (newshf.shp 39/41, 24x28 px): a shiny tan armoured dome turret.

Reading of the sprite (the tile is painted sand edge to edge; the sand is the HD ground's job, D103):
- A tan metal dome, footprint ellipse centre (10.5, 11.6) px (pixel-edge coords), 8.5 x 6.6 px radii,
  lit from the upper left (the white patch is sheen), shaded to the lower right. One smooth, glossy
  bulb: a single pchip profile from the crown (8.6 px) to a low foot lip, no terraces or collars.
  Eight armour panels over the flanks sit flush (0.1 px proud), so their gaps read as engraved
  seams; a ring of bolt heads near the foot.
- A red eye in the crown (centre (9.5, 11.5)) with only a low chamfered lip that follows the dome:
  a wide dark socket bezel (113), a narrow ring (115), a narrow lens (118), a 1.5 px hot core (125),
  modest emission (the sprite's eye is mostly dark red). Frame 41 brightens them (120/121/123/127,
  palette_material frames=).
- A sensor ball at the upper right (centre (17, 5.2), 1.35 px) on an arm from the dome's foot and
  a short post: a banded sphere.
- A barrel (the light stripe with a dark side and a black cast shadow): out of a mount collar on
  the dome's lower right, round the dome's foot and straight down the screen to row 25, with a
  clamp band and a muzzle sleeve with its bore.
Underside: a flat closed disc, no detail.

    
Exports public/models/enemies/newshf-39.glb and src/render/spriteModels/newshf-39.json (D65 style).
Run: blender --background --python assets/blender/enemies/newshf-39.py
Coordinates while building: x = col_edge - 12, y = row_edge - 14 (down the screen), z up, all in
sprite px; finish() maps to Blender X = x/12, Y = -y/12, Z = z/12.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newshf-39"
PX = 1 / 12
TAG = "nshf39A"

# --- the reading, in build coordinates ----------------------------------------------------------
DCX, DCY, DRX, DRY = 10.5 - 12, 11.6 - 14, 8.5, 6.6  # dome footprint
T_CAP = 1.0           # the cap runs all the way to the footprint's edge (one continuous curve)
Z_COLLAR = 0.55       # height of the low foot lip at the rim
Z_APEX = 8.6          # crown height (px): a full, bulbous dome
EYE = (9.5 - 12, 11.5 - 14)
BALL = (17.0 - 12, 5.2 - 14, 2.7, 1.35)
BARREL = [(16.9 - 12, 13.6 - 14, 2.3), (16.4 - 12, 15.3 - 14, 2.0), (15.1 - 12, 16.8 - 14, 1.75),
          (13.0 - 12, 18.1 - 14, 1.55), (11.1 - 12, 19.1 - 14, 1.45), (10.6 - 12, 20.4 - 14, 1.4),
          (10.5 - 12, 22.0 - 14, 1.4), (10.5 - 12, 25.0 - 14, 1.4)]
BR = 1.15


def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson) interpolant through (xs, ys)."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        i = max(0, min(n - 2, next((k for k in range(n - 1) if x <= xs[k + 1]), n - 2)))
        t = (x - xs[i]) / h[i]
        h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
        h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


# Cap profile stations (normalised radius -> height), one pchip curve from the crown to the rim: a
# full glossy bulb whose shoulders roll steeply down into a low foot lip (no terraces or steps).
_cap = pchip([0.0, 0.3, 0.55, 0.75, 0.86, 0.94, 1.0],
             [Z_APEX, Z_APEX - 0.35, Z_APEX - 1.5, Z_APEX - 3.3, Z_APEX - 4.8, Z_APEX - 6.4, Z_COLLAR])


def cap_z(t):
    return _cap(min(max(t, 0.0), T_CAP))


def S(th, t):
    """A point of the dome surface at angle th, normalised radius t (t <= T_CAP)."""
    return Vector((DCX + DRX * t * math.cos(th), DCY + DRY * t * math.sin(th), cap_z(t)))


def S_normal(th, t):
    e = 1e-3
    p = S(th, t)
    if t < 0.02:
        return Vector((0, 0, 1))
    a = S(th + e, t) - p
    b = S(th, min(t + e, T_CAP)) - S(th, max(t - e, 0))
    n = b.cross(a)
    if n.z < 0:
        n = -n
    return n.normalized()


def r_at(th, t):
    """Approximate px distance of S(th, t) from the dome axis (to turn px gaps into angles)."""
    return max(1e-3, t * math.hypot(DRX * math.cos(th), DRY * math.sin(th)))


def dome_height_at(x, y):
    t = math.hypot((x - DCX) / DRX, (y - DCY) / DRY)
    return cap_z(t) if t <= 1 else 0.0


# --- mesh building --------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(Vector(p))

    def f(self, vs, mat):
        if len({id(x) for x in vs}) < 3:
            return None
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        return face

    def grid(self, rows, mat, closed=True, mats=None):
        """Quads between consecutive rings (lists of verts, single-vert rings collapse to fans)."""
        for j, (r0, r1) in enumerate(zip(rows, rows[1:])):
            m = mats[j] if mats else mat
            if len(r0) == 1 and len(r1) == 1:
                continue
            n = max(len(r0), len(r1))
            for i in range(n if closed else n - 1):
                k = (i + 1) % n
                if len(r0) == 1:
                    self.f((r0[0], r1[i], r1[k]), m)
                elif len(r1) == 1:
                    self.f((r0[i], r0[k], r1[0]), m)
                else:
                    self.f((r0[i], r0[k], r1[k], r1[i]), m)


def lathe(M, centre, axis, profile, sides, mats, phase=0.0):
    """Revolve profile [(r, h)] around `axis` through `centre`; mats[i] is the segment i->i+1."""
    axis = Vector(axis).normalized()
    ref = Vector((1, 0, 0)) if abs(axis.x) < 0.9 else Vector((0, 1, 0))
    u = (ref - axis * ref.dot(axis)).normalized()
    w = axis.cross(u)
    rows = []
    for r, h in profile:
        c = Vector(centre) + axis * h
        if r < 1e-6:
            rows.append([M.v(c)])
        else:
            rows.append([M.v(c + (u * math.cos(phase + 2 * math.pi * k / sides) +
                                  w * math.sin(phase + 2 * math.pi * k / sides)) * r) for k in range(sides)])
    M.grid(rows, 0, mats=mats)
    if len(rows[0]) > 1:
        M.f(list(reversed(rows[0])), mats[0])
    if len(rows[-1]) > 1:
        M.f(rows[-1], mats[-1])


def frames_along(pts):
    """Parallel-transport frames (tangent, normal, binormal) along a polyline."""
    ts = []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        ts.append((b - a).normalized())
    n = Vector((0, 0, 1))
    n = (n - ts[0] * n.dot(ts[0])).normalized()
    out = []
    for t in ts:
        n = (n - t * n.dot(t)).normalized()
        out.append((t, n, t.cross(n)))
    return out


def sweep(M, pts, radii, sides, mats, cap0=True, cap1=True):
    """A tube through pts with per-point radius; mats per segment."""
    fr = frames_along(pts)
    rows = []
    for p, (t, n, b), r in zip(pts, fr, radii):
        if r < 1e-6:
            rows.append([M.v(p)])
        else:
            rows.append([M.v(p + (n * math.cos(2 * math.pi * (k + 0.5) / sides) +
                                  b * math.sin(2 * math.pi * (k + 0.5) / sides)) * r) for k in range(sides)])
    M.grid(rows, 0, mats=mats)
    if cap0 and len(rows[0]) > 1:
        M.f(list(reversed(rows[0])), mats[0])
    if cap1 and len(rows[-1]) > 1:
        M.f(rows[-1], mats[-1])
    return rows


def catmull(points, step):
    """Resample a polyline of Vectors as a Catmull-Rom curve, about `step` apart."""
    P = [points[0] * 2 - points[1]] + list(points) + [points[-1] * 2 - points[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(1, int(round((p2 - p1).length / step)))
        for k in range(n):
            s = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3))
    out.append(P[-2])
    return out


# --- parts ---------------------------------------------------------------------------------------

def build_shell(M, SHELL, DARK):
    """The dome shell: one continuous cap surface from crown to rim, a low foot lip, a flat bottom."""
    seg = 56
    ths = [2 * math.pi * k / seg for k in range(seg)]
    ts = [0.06, 0.13, 0.2, 0.27, 0.34, 0.41, 0.48, 0.55, 0.61, 0.67, 0.72, 0.77, 0.81, 0.85, 0.885,
          0.915, 0.94, 0.96, 0.975, 0.988]
    rows = [[M.v(S(0, 0))]]
    for t in ts:
        rows.append([M.v(S(th, t)) for th in ths])
    # Foot: the cap rolls onto a short chamfered lip standing on the ground.
    ring = lambda t, z: [M.v((DCX + DRX * t * math.cos(th), DCY + DRY * t * math.sin(th), z)) for th in ths]  # noqa: E731
    rows += [ring(0.997, Z_COLLAR), ring(1.0, Z_COLLAR - 0.12), ring(1.0, 0.0)]
    mats = [SHELL] * (len(ts)) + [SHELL, SHELL, SHELL]
    M.grid(rows, SHELL, mats=mats)
    M.f(list(reversed(rows[-1])), SHELL)  # flat underside


def petal(M, th0, th1, t0, t1, mat, h=0.1, c=0.08, gap=0.24, nu=7, nv=6):
    """An armour petal on the cap between angles th0..th1 and radii t0..t1, standing h proud, with
    c chamfered edges and a constant px gap to its neighbours (the panel line)."""
    def region(shrink):
        rows = []
        for j in range(nv):
            t = t0 + (t1 - t0) * j / (nv - 1)
            t = min(max(t, t0 + shrink / 7.5 + gap / 15), t1 - shrink / 7.5 - gap / 15)
            r = r_at((th0 + th1) / 2, t)
            g = (gap / 2 + shrink) / r
            a, b = th0 + g, th1 - g
            rows.append([(a + (b - a) * i / (nu - 1), t) for i in range(nu)])
        return rows

    def loop(grid):
        top = grid[0]
        right = [row[-1] for row in grid[1:]]
        bot = list(reversed(grid[-1][:-1]))
        left = [row[0] for row in reversed(grid[1:-1])]
        return top + right + bot + left

    def place(th, t, off):
        return S(th, t) + S_normal(th, t) * off

    top = [[M.v(place(th, t, h)) for th, t in row] for row in region(c)]
    mid_uv = loop(region(0))
    bot = [[M.v(place(th, t, -0.15)) for th, t in row] for row in region(0)]
    # top grid
    for j in range(nv - 1):
        for i in range(nu - 1):
            M.f((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]), mat)
            M.f((bot[j + 1][i], bot[j + 1][i + 1], bot[j][i + 1], bot[j][i]), mat)
    tl, bl = loop(top), loop(bot)
    ml = [M.v(place(th, t, h - c)) for th, t in mid_uv]
    n = len(tl)
    for i in range(n):
        k = (i + 1) % n
        M.f((tl[i], tl[k], ml[k], ml[i]), mat)
        M.f((ml[i], ml[k], bl[k], bl[i]), mat)


def build_cap_panels(M, SHELL):
    """Eight armour panels over the dome's flanks, flush with the shell (they stand 0.1 px proud of
    it, so the gaps read as engraved seams, not terraces); the crown round the eye stays smooth."""
    off2 = math.radians(-8)
    for k in range(8):
        a = off2 + 2 * math.pi * k / 8
        petal(M, a, a + 2 * math.pi / 8, 0.46, 0.93, SHELL, nu=7, nv=9)


def build_bolts(M, SHELL):
    """Hex bolt heads round the collar band."""
    n = 18
    for k in range(n):
        th = 2 * math.pi * (k + 0.5) / n
        t = 0.965
        p = S(th, t)
        nrm = S_normal(th, t)
        lathe(M, p, nrm, [(0.3, -0.25), (0.3, 0.12), (0.2, 0.22), (0, 0.22)], 6, [SHELL] * 3)


def build_eye(M, SHELL, SOCKET, RING, LENS, CORE):
    """The eye sits in the crown with only a low chamfered lip: every ring follows the dome's own
    surface (offset along z), so there is no housing wall or terrace round it. Inside the lip a wide
    dark socket bezel (113), a narrow ring (115), a narrow lens ring (118) and a 1.5 px hot core (125)."""
    x, y = EYE
    sides = 32
    # (radius px, height above the dome surface, material of the band from this ring inwards)
    prof = [(2.95, -0.9, SHELL), (2.95, -0.05, SHELL), (2.8, 0.2, SHELL), (2.55, 0.3, SHELL),
            (2.35, 0.28, SHELL), (2.2, 0.1, SOCKET), (1.85, 0.04, SOCKET), (1.55, 0.06, RING),
            (1.15, 0.1, LENS), (0.78, 0.14, CORE), (0.4, 0.18, CORE)]
    rows = []
    for r, off, _m in prof:
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            px, py = x + r * math.cos(a), y + r * math.sin(a)
            ring.append(M.v((px, py, dome_height_at(px, py) + off)))
        rows.append(ring)
    tip = M.v((x, y, dome_height_at(x, y) + 0.19))
    bot = M.v((x, y, dome_height_at(x, y) - 0.9))
    M.grid(rows, SHELL, mats=[m for _r, _o, m in prof[:-1]])
    for k in range(sides):
        j = (k + 1) % sides
        M.f((rows[-1][k], rows[-1][j], tip), CORE)
        M.f((rows[0][j], rows[0][k], bot), SHELL)


def build_ball(M, SHELL, BALLM, DARK):
    bx, by, bz, br = BALL
    c = Vector((bx, by, bz))
    # sphere as a lathe with an equator band standing proud
    prof = [(0, -br)]
    for k in range(1, 6):
        a = -math.pi / 2 + math.pi * k / 12
        prof.append((br * math.cos(a), br * math.sin(a)))
    prof += [(br * 1.0, -0.12), (br + 0.14, -0.12), (br + 0.14, 0.12), (br * 1.0, 0.12)]
    for k in range(7, 12):
        a = -math.pi / 2 + math.pi * k / 12
        prof.append((br * math.cos(a), br * math.sin(a)))
    prof.append((0, br))
    mats = [BALLM] * 5 + [DARK, DARK, DARK, DARK] + [BALLM] * 6
    lathe(M, c, (0.25, -0.3, 1.0), prof, 14, mats[:len(prof) - 1])
    # arm from the dome's foot to the ball, with a clamp collar at its root, and a post under it
    root = Vector((2.9, -7.0, Z_COLLAR + 0.2))
    sweep(M, [root, root.lerp(c, 0.5), c], [0.52, 0.5, 0.48], 8, [SHELL, SHELL])
    rc = root.lerp(c, 0.18)
    d = (c - root).normalized()
    lathe(M, rc, d, [(0.72, -0.3), (0.72, 0.3)], 8, [DARK])
    sweep(M, [Vector((bx, by, -0.1)), Vector((bx, by, bz - 0.6))], [0.42, 0.42], 8, [DARK])


def build_barrel(M, BARRELM, DARK, BORE):
    pts = catmull([Vector(p) for p in BARREL], 0.5)
    n = len(pts)
    sweep(M, pts, [BR] * n, 12, [BARRELM] * (n - 1))
    fr = frames_along(pts)
    # length along the barrel
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + (b - a).length)
    L = s[-1]

    def at(d):
        for i in range(n - 1):
            if s[i + 1] >= d:
                f = (d - s[i]) / (s[i + 1] - s[i])
                return pts[i].lerp(pts[i + 1], f), fr[i][0]
        return pts[-1], fr[-1][0]

    # mount collar where it leaves the dome (two steps, chamfered)
    p, t = at(1.0)
    lathe(M, p, t, [(BR + 0.2, -1.6), (BR + 0.55, -1.2), (BR + 0.55, 0.15), (BR + 0.3, 0.45),
                    (BR + 0.3, 0.75), (BR + 0.08, 0.9)], 12, [DARK, DARK, DARK, DARK, DARK])
    # a clamp band on the bend
    p, t = at(L * 0.5)
    lathe(M, p, t, [(BR + 0.05, -0.4), (BR + 0.22, -0.28), (BR + 0.22, 0.28), (BR + 0.05, 0.4)], 12,
          [DARK, DARK, DARK])
    # muzzle sleeve with a chamfered lip and a dark bore
    p, t = at(L - 1.25)
    lathe(M, p, t, [(BR - 0.05, -0.2), (BR + 0.18, 0.0), (BR + 0.18, 1.05), (BR + 0.02, 1.27),
                    (0.62, 1.27), (0.62, 0.9), (0, 0.9)], 12,
          [DARK, DARK, DARK, DARK, BORE, BORE])


def finish(M, mats, coll, name):
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 0), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)  # the y reflection flips winding
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    return obj


def build(sprite, coll):
    pal = lambda i, tag="", **kw: common.palette_material(sprite, i, TAG + tag, **kw)  # noqa: E731
    mats = [
        pal(24, metallic=0.2, roughness=0.32),                       # 0 dome shell (region median 24), glossy
        pal(17, metallic=0.4, roughness=0.5),                         # 1 dark collars, clamps, band
        common.palette_material(sprite, 113, TAG + "-socket", metallic=0.3, roughness=0.4,
                                emission_strength=0.4, frames={41: 120}),   # 2 eye socket bezel
        common.palette_material(sprite, 115, TAG + "-ring", emission_strength=0.8, frames={41: 121}),  # 3
        common.palette_material(sprite, 118, TAG + "-eye", emission_strength=1.2, frames={41: 123}),  # 4 lens
        common.palette_material(sprite, 125, TAG + "-core", emission_strength=3.0, frames={41: 127}),  # 5 core
        pal(25, metallic=0.2, roughness=0.4),                       # 6 sensor ball (median 25)
        pal(22, metallic=0.35, roughness=0.36),                       # 7 barrel: light tan pipe (visible-pixel median 21.5, arc 24.5; centre stick 24-27 is sheen)
        pal(16, metallic=0.2, roughness=0.7),                         # 8 bore
    ]
    SHELL, DARK, SOCKET, RING, LENS, CORE, BALLM, BARRELM, BORE = range(9)
    M = Mesh()
    build_shell(M, SHELL, DARK)
    build_cap_panels(M, SHELL)
    build_bolts(M, SHELL)
    build_eye(M, SHELL, SOCKET, RING, LENS, CORE)
    build_ball(M, SHELL, BALLM, DARK)
    build_barrel(M, BARRELM, DARK, BORE)
    return finish(M, mats, coll, NAME)


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    shell = common.outline_shell(obj, coll)
    obj.data.calc_loop_triangles()
    print("triangles", len(obj.data.loop_triangles), "shell", len(shell.data.polygons))
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])


if __name__ == "__main__":
    main()
