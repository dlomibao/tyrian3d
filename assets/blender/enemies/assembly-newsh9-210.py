"""Giant eye (newsh9.shp, assembly of 3 pieces): a 3D version of its sprites.

Seen in episode 4 (levels 4.4 and 4.20). Three 2x2 enemies side by side make one 72x28 px object
(sprite.json `assemblyLayout`): the lower half of a huge blue eye in a dark grey socket. The iris
is a big glossy dome with a dark limbal ring, glowing streaks and a glint at its upper left, a
black pupil and a dark crosshair across it; the socket's lid curls round its lower edge.

The eye is built whole in assembly coordinates, then cut into the three pieces with
common.split_assembly (which also trims everything above the sprite's top row).

Run: blender --background --python assets/blender/enemies/assembly-newsh9-210.py [-- --preview out.png]
(the preview is the whole eye; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b019 as lib  # noqa: E402

NAME = "assembly-newsh9-210"
ROOT = common.repo_root(__file__)
PIECES = ["newsh9-210", "newsh9-212", "newsh9-214"]
# Assembly pixel (0, 0) is screen (125, -32); the 72 x 28 px eye's centre (screen 161, -18) is
# the Blender origin.
CENTRE = (161, -18)
W, H = 72, 28
G = lib.Grid(W, H)

# The iris: an ellipse centred on pixel edge point (CX, CY) with radii A x B px, domed DOME units.
CX, CY, A, B = 35.5, 9.0, 20.5, 14.0
DOME = 0.22


def dome_z(c, r):
    """Height of the iris surface over pixel edge point (c, r)."""
    s2 = ((c - CX) / A) ** 2 + ((r - CY) / B) ** 2
    return DOME * math.sqrt(max(0.0, 1.0 - s2))


def mask():
    """Which assembly pixels the sprite fills (any index, the outline included)."""
    grid = [[False] * W for _ in range(H)]
    for i, name in enumerate(PIECES):
        data = common.load_sprite(ROOT, name)
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[r][c + 24 * i] = True
    return grid


def inside(grid, c, r):
    """Is pixel edge point (c, r) inside the sprite? Above the top row the top row's span goes on."""
    ci, ri = int(math.floor(c)), int(math.floor(r))
    if ri < -2:
        return False
    ri = max(ri, 0)
    if ri >= H or ci < 0 or ci >= W:
        return False
    return grid[ri][ci]


def ellipse_point(t, s):
    return CX + s * A * math.cos(t), CY + s * B * math.sin(t)


def socket(bm, grid, mats):
    """The lid: a ring round the iris, from the sprite's outer edge (low) up to a lip just outside
    the iris and down under it. Rings of 6 points are joined round the eye."""
    OUTER, SLOPE, LIP, INNER = mats
    n = 64
    reach = []
    for k in range(n):
        t = 2 * math.pi * k / n
        s = 1.0
        while s < 4.0 and inside(grid, *ellipse_point(t, s + 0.02)):
            s += 0.02
        # Pull the outer edge in by about 0.6 px (the game draws the outline).
        step = math.hypot(A * math.cos(t), B * math.sin(t))
        reach.append(max(1.12, s - 0.6 / step))
    # Smooth out the pixel steps of the sprite's edge.
    reach = [(reach[k - 1] + 2 * reach[k] + reach[(k + 1) % n]) / 4 for k in range(n)]
    rings = []
    for k in range(n):
        t = 2 * math.pi * k / n
        s_out = reach[k]
        s_lip = 1.06
        s_mid = (s_out + s_lip) / 2
        pts = [(s_out, -0.05), (s_mid, 0.03), (s_lip, 0.09), (0.96, 0.03), (0.96, -0.1), (s_out, -0.1)]
        ring = []
        for ss, z in pts:
            c, r = ellipse_point(t, ss)
            ring.append(bm.verts.new((G.x(c), G.y(r), z)))
        rings.append(ring)
    slots = [OUTER, SLOPE, LIP, INNER, OUTER, OUTER]
    for k in range(n):
        r0, r1 = rings[k], rings[(k + 1) % n]
        for i in range(6):
            j = (i + 1) % 6
            f = bm.faces.new((r0[i], r1[i], r1[j], r0[j]))
            f.material_index = slots[i]
            f.smooth = True


def iris(bm, iris_mat, ring_mat):
    """The iris dome: rings of the ellipse from its rim to a centre point."""
    n, steps = 40, 8
    rings = []
    for m in range(steps + 1):
        s = 1.0 - m / steps * 0.98
        ring = []
        for k in range(n):
            t = 2 * math.pi * k / n
            c, r = ellipse_point(t, s)
            ring.append(bm.verts.new((G.x(c), G.y(r), dome_z(c, r))))
        rings.append((s, ring))
    top = bm.verts.new((G.x(CX), G.y(CY), DOME))
    for (s0, r0), (s1, r1) in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = ring_mat if s0 > 0.87 else iris_mat
            f.smooth = True
    last = rings[-1][1]
    for k in range(n):
        f = bm.faces.new((last[k], last[(k + 1) % n], top))
        f.material_index = iris_mat
        f.smooth = True
    under = [bm.verts.new((v.co.x, v.co.y, -0.02)) for v in rings[0][1]]
    for k in range(n):
        j = (k + 1) % n
        f = bm.faces.new((rings[0][1][j], rings[0][1][k], under[k], under[j]))
        f.material_index = ring_mat
    bm.faces.new(list(reversed(under))).material_index = ring_mat


def patch(bm, c0, r0, rx, ry, lift, bulge, mat, sides=16, rings=3):
    """A cap lying on the iris dome: an ellipse rx x ry px at (c0, r0), lift above the surface at its
    centre falling to just under it at its rim, with a slight bulge."""
    centre = bm.verts.new((G.x(c0), G.y(r0), dome_z(c0, r0) + lift + bulge))
    loops = []
    for m in range(1, rings + 1):
        f = m / rings
        loop = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            c, r = c0 + f * rx * math.cos(a), r0 + f * ry * math.sin(a)
            z = dome_z(c, r) + (lift + bulge * (1 - f * f) if m < rings else -0.004)
            loop.append(bm.verts.new((G.x(c), G.y(r), z)))
        loops.append(loop)
    faces = []
    for k in range(sides):
        j = (k + 1) % sides
        faces.append(bm.faces.new((centre, loops[0][k], loops[0][j])))
        for l0, l1 in zip(loops, loops[1:]):
            faces.append(bm.faces.new((l0[k], l1[k], l1[j], l0[j])))
    for f in faces:
        f.material_index = mat
        f.smooth = True


def ribbon(bm, pts, half_w, lift, mat, samples=10):
    """A thin strip lying on the iris dome along a straight run of pixel edge points (c, r): a box
    section from just under the surface to `lift` above it."""
    (c0, r0), (c1, r1) = pts
    dc, dr = c1 - c0, r1 - r0
    d = math.hypot(dc, dr)
    nc, nr = -dr / d * half_w, dc / d * half_w
    rings = []
    for i in range(samples + 1):
        f = i / samples
        c, r = c0 + dc * f, r0 + dr * f
        ring = []
        for sc, z in ((-1, -0.006), (1, -0.006), (1, lift), (-1, lift)):
            cc, rr = c + sc * nc, r + sc * nr
            ring.append(bm.verts.new((G.x(cc), G.y(rr), dome_z(cc, rr) + z)))
        rings.append(ring)
    faces = lib._join_rings(bm, rings, 4, mat)
    for f in faces:
        f.smooth = False


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh9e"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(2, metallic=0.3, roughness=0.6),  # 0 dark outer socket
        pal(3, metallic=0.4, roughness=0.5),  # 1 socket slope
        pal(5, metallic=0.5, roughness=0.35),  # 2 lid lip
        pal(4, metallic=0.4, roughness=0.5),  # 3 inside of the lid
        pal(130, metallic=0.2, roughness=0.15, emission_strength=1.0),  # 4 iris
        pal(54, metallic=0.2, roughness=0.2),  # 5 dark limbal ring
        pal(97, metallic=0.3, roughness=0.08),  # 6 pupil
        pal(51, metallic=0.2, roughness=0.3),  # 7 crosshair
        pal(156, emission_strength=1.5),  # 8 glowing streaks
        pal(158, emission_strength=1.5),  # 9 lit patch
        pal(141, emission_strength=3.0),  # 10 glint
        pal(62, emission_strength=4.0),  # 11 hot spot of the glint
    ]
    bm = bmesh.new()
    socket(bm, mask(), (0, 1, 2, 3))
    iris(bm, 4, 5)
    # The lit patch at the iris's upper left with its glint (rows 0-8, columns 20-31).
    patch(bm, 26.5, 4.0, 5.5, 4.0, 0.006, 0.006, 9)
    patch(bm, 27.5, 1.8, 2.8, 2.0, 0.012, 0.01, 10)
    patch(bm, 25.5, 8.0, 1.4, 1.2, 0.014, 0.008, 11)
    # Glowing streaks fanning out from the pupil (angles in the sprite, y down).
    for deg, s0, s1 in ((160, 0.5, 0.8), (200, 0.55, 0.85), (-30, 0.4, 0.7), (5, 0.35, 0.8),
                        (35, 0.5, 0.85), (62, 0.55, 0.8)):
        t = math.radians(deg)
        ribbon(bm, [ellipse_point(t, s0), ellipse_point(t, s1)], 0.6, 0.008, 8, samples=6)
    # The pupil (columns 29-38, rows 4-16) and the crosshair through it.
    patch(bm, 34.5, 10.2, 5.4, 6.0, 0.016, 0.012, 6, sides=20)
    ribbon(bm, [(36.5, -1.0), (36.5, 22.6)], 0.55, 0.02, 7, samples=14)
    ribbon(bm, [(15.0, 9.6), (56.0, 8.6)], 0.55, 0.02, 7, samples=16)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.run_assembly(ROOT, NAME, PIECES, CENTRE, build, size=6, grid_w=W, grid_h=H)


if __name__ == "__main__":
    main()
