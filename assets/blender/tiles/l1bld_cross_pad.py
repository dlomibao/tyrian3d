"""The cross-shaped pad of red light capsules on map 1-3's ground (shapesz.dat; 5 x 5 tiles, once on
the map at rows 233-237), after the concept assets/blender/features/concepts/l1-bld-cross-pad.jpg:
a rocky, roughly round platform around a square body of grey metal machinery (panels in a frame
grid, pipe runs) with a raised gunmetal cross in the middle; along each arm three glowing red
capsules in silver frames (338 vertical arm: capsules lying across x; 339 horizontal arm: capsules
standing along y), and in the centre (347) a square, hotter orange core in a chamfered frame.

All five cross cells carry ground enemies (the red lights newshs 157/195/235), drawn at 0.45 over
the building: the cross's top stays between ENEMY_MIN and ENEMY_MAX so they sit on it, and the
building's own lights show once they are destroyed.

The outline is not the tiles' pixel mask: a low mound with a smooth (polar) outline carries chunky
faceted boulders (convex hulls) that reach the ground, so the silhouette is the rocks'. The lenses
and the core are marbled per half pixel from the tiles' own red pixels (dark red with bright
streaks; the core shifted up to a hot orange).

Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/l1bld_cross_pad.py
    python tools/concept_maps.py tile:shapesz-l1bld-cross-pad --concept l1-bld-cross-pad
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-l1bld-cross-pad
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_tiles as lt  # noqa: E402

BODY_DECK = 0.22  # the machinery body's floor
MOUND_TOP = 0.15  # the rocky mound under the boulders
CROSS_TOP = 0.31  # the gunmetal cross (exactly the five enemy cells)
CROSS_STEP = 0.27  # its 2 px chamfer step
STEP_PX = 2
CENTRE = (60.0, 70.0)  # pattern px
# The square machinery body (the cells 363/364/373/374 and the cross), corners chamfered.
BODY = (23, 25, 97, 115)
BODY_CHAMFER = 6
# The cross: the vertical arm is pattern column 2 (rows 1-3), the horizontal arm is row 2 (cols 1-3).
V_ARM = (48, 28, 72, 112)
H_ARM = (24, 56, 96, 84)
# The red lights (pattern px, from the tiles' red pixels): centres and size.
CAP_X = 59.0  # vertical arm: capsules lie across (axis x), 18 x 7 px
CAP_Y_TOP = (33.5, 42.2, 50.8)
CAP_Y_BOTTOM = (89.5, 98.2, 106.8)
CAP_Y = 70.0  # horizontal arm: capsules stand along y, 7 x 18 px
CAP_X_LEFT = (28.0, 35.8, 43.6)
CAP_X_RIGHT = (76.0, 83.8, 91.6)
BEZEL = (22.0, 8.6)  # a light's silver bezel (long x short side, px), as in the concept
LENS = (18.0, 5.6)  # its lens
CORE = (50, 59, 69, 81)  # the centre's glowing square, frame included
# The four machinery quadrants between the arms (inside the arms' chamfer steps).
QUADS = ((25, 28, 46, 54), (74, 28, 95, 54), (25, 86, 46, 112), (74, 86, 95, 112))


def rrect(x0, y0, x1, y1, rad, segs):
    """Outline (pixel coords, counter-clockwise seen from above) of a rounded rectangle; segs=1 makes
    chamfered (octagon) corners."""
    rad = min(rad, (x1 - x0) / 2, (y1 - y0) / 2)
    pts = []
    for cx, cy, a0 in ((x1 - rad, y0 + rad, 0.0), (x0 + rad, y0 + rad, 90.0),
                       (x0 + rad, y1 - rad, 180.0), (x1 - rad, y1 - rad, 270.0)):
        for i in range(segs + 1):
            a = math.radians(a0 + 90.0 * i / segs)
            pts.append((cx + rad * math.cos(a), cy - rad * math.sin(a)))
    return pts


def in_rrect(px, py, x0, y0, x1, y1, rad):
    rad = min(rad, (x1 - x0) / 2, (y1 - y0) / 2)
    if not (x0 <= px <= x1 and y0 <= py <= y1):
        return False
    cx = min(max(px, x0 + rad), x1 - rad)
    cy = min(max(py, y0 + rad), y1 - rad)
    return (px - cx) ** 2 + (py - cy) ** 2 <= rad * rad


def lozenge(b, x0, y0, x1, y1, rad, segs, z0, z1, mat, bevel_px=0.0, bevel_z=0.0):
    """A closed prism over a rounded rectangle from z0 to z1; with bevel_px, its top edge chamfered
    (the outline inset by bevel_px and bevel_z higher, so z1 + bevel_z is the very top)."""
    bm = bmesh.new()
    base = rrect(x0, y0, x1, y1, rad, segs)
    rings = [[(px, py, z0) for px, py in base], [(px, py, z1) for px, py in base]]
    if bevel_px > 0:
        inner = rrect(x0 + bevel_px, y0 + bevel_px, x1 - bevel_px, y1 - bevel_px, max(0.3, rad - bevel_px), segs)
        rings.append([(px, py, z1 + bevel_z) for px, py in inner])
    vr = [[bm.verts.new((b.x(px), b.y(py), z)) for px, py, z in ring] for ring in rings]
    n = len(base)
    bm.faces.new(list(reversed(vr[0]))).material_index = mat
    bm.faces.new(vr[-1]).material_index = mat
    for a, c in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], c[j], c[i])).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)


class Marble:
    """Open, upward-facing sheets of half-pixel quads, each coloured from the tile pixel under it
    (kept out of b.parts so its winding is not recalculated)."""

    def __init__(self, b):
        self.b = b
        self.bm = bmesh.new()

    def sample(self, cx, cy):
        """The tile's red ramp level at a point, bilinear between pixel centres (grey pixels count
        as the darkest red), so the streaks come out rounded rather than in pixel blocks."""
        g = np.clip(self.b.grid.astype(float), 112, 127)
        fx, fy = cx - 0.5, cy - 0.5
        ix, iy = int(math.floor(fx)), int(math.floor(fy))
        tx, ty = fx - ix, fy - iy
        H, W = g.shape

        def at(x, y):
            return g[min(H - 1, max(0, y)), min(W - 1, max(0, x))]

        v = ((1 - tx) * (1 - ty) * at(ix, iy) + tx * (1 - ty) * at(ix + 1, iy)
             + (1 - tx) * ty * at(ix, iy + 1) + tx * ty * at(ix + 1, iy + 1))
        return int(round(v))

    def sheet(self, x0, y0, x1, y1, rad, z, pick, step=0.5):
        b = self.b
        verts = {}

        def v(i, j):
            k = (i, j)
            if k not in verts:
                verts[k] = self.bm.verts.new((b.x(i * step), b.y(j * step), z))
            return verts[k]

        for j in range(int(math.floor(y0 / step)), int(math.ceil(y1 / step))):
            for i in range(int(math.floor(x0 / step)), int(math.ceil(x1 / step))):
                cx, cy = (i + 0.5) * step, (j + 0.5) * step
                if not in_rrect(cx, cy, x0, y0, x1, y1, rad):
                    continue
                g = self.sample(cx, cy)
                # World y is up, pixel y is down: this order faces +z.
                f = self.bm.faces.new((v(i, j + 1), v(i + 1, j + 1), v(i + 1, j), v(i, j)))
                f.material_index = pick(g)


def cylinder(b, p0, p1, zc, r_px, mat, sides=10, caps=True):
    """A straight pipe of constant diameter between two pixel points, its axis at height zc."""
    bm = bmesh.new()
    x0, y0 = b.x(p0[0]), b.y(p0[1])
    x1, y1 = b.x(p1[0]), b.y(p1[1])
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    r = r_px * lt.PX
    rings = []
    for (cx, cy) in ((x0, y0), (x1, y1)):
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new((cx + nx * r * math.cos(a), cy + ny * r * math.cos(a), zc + r * math.sin(a))))
        rings.append(ring)
    for k in range(sides):
        m = (k + 1) % sides
        bm.faces.new((rings[0][k], rings[0][m], rings[1][m], rings[1][k])).material_index = mat
    if caps:
        bm.faces.new(rings[0]).material_index = mat
        bm.faces.new(list(reversed(rings[1]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)


def pipe(b, p0, p1, z_floor, r_px, mat, flange_mat):
    """A pipe lying on the floor between two px points with flanges (collars) at both ends."""
    zc = z_floor + r_px * lt.PX
    cylinder(b, p0, p1, zc, r_px, mat)
    ln = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    ux, uy = (p1[0] - p0[0]) / ln, (p1[1] - p0[1]) / ln
    for (px, py), s in ((p0, 1), (p1, -1)):
        a = (px + s * ux * 0.6, py + s * uy * 0.6)
        c = (px + s * ux * 1.6, py + s * uy * 1.6)
        cylinder(b, a, c, zc, r_px * 1.4, flange_mat, sides=10)


def boulder(b, rng, px, py, r_px, z0, top, mat):
    """A chunky, faceted rock: the convex hull of jittered points on a squashed, tapering blob."""
    bm = bmesh.new()
    rx = r_px * (0.85 + 0.3 * rng.random()) * lt.PX
    ry = r_px * (0.85 + 0.3 * rng.random()) * lt.PX
    rot = rng.random() * math.pi
    ca, sa = math.cos(rot), math.sin(rot)
    # Lean the top off centre (towards a random side) so the rocks are not domes.
    lx, ly = (rng.random() - 0.5) * 0.5 * rx, (rng.random() - 0.5) * 0.5 * ry
    h = top - z0
    pts = []
    for level, scale, n in ((0.0, 1.0, 6), (0.45, 1.0, 5), (0.8, 0.75, 4), (1.0, 0.4, 3)):
        off = rng.random() * 2 * math.pi
        for k in range(n):
            a = off + 2 * math.pi * (k + 0.3 * rng.random()) / n
            s = scale * (0.75 + 0.3 * rng.random())
            ex, ey = rx * s * math.cos(a), ry * s * math.sin(a)
            z = z0 + h * (level if level in (0.0, 1.0) else level + (rng.random() - 0.5) * 0.15)
            if level == 1.0:
                z = top - h * 0.12 * rng.random()
            t = level
            wx, wy = ex + lx * t, ey + ly * t
            pts.append((b.x(px) + wx * ca - wy * sa, b.y(py) + wx * sa + wy * ca, z))
    vs = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=vs)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    for f in bm.faces:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)
    return max(abs(rx), abs(ry)) / lt.PX


def polar_outline(b, bins=96):
    """The footprint's outline as radii from CENTRE per angle bin (lightly smoothed)."""
    ys, xs = np.nonzero(b.footprint)
    dx, dy = xs + 0.5 - CENTRE[0], ys + 0.5 - CENTRE[1]
    ang = (np.arctan2(dy, dx) % (2 * math.pi)) / (2 * math.pi) * bins
    dist = np.hypot(dx, dy)
    R = np.zeros(bins)
    for i in range(bins):
        sel = (ang >= i) & (ang < i + 1)
        R[i] = dist[sel].max() if sel.any() else 0
    mx = np.maximum(np.maximum(np.roll(R, 1), np.roll(R, -1)), R)
    mean = (np.roll(R, 1) + np.roll(R, -1) + R) / 3
    return 0.5 * mx + 0.5 * mean


def mound(b, R, mat, inset=7.0):
    """A low sloped mound under the rocks: ground ring at the outline, a top ring `inset` px in at
    MOUND_TOP, a flat top fanned from the centre."""
    bm = bmesh.new()
    n = len(R)
    rings = []
    for r_off, z in ((0.5, lb.SLAB_BOTTOM), (-inset, MOUND_TOP)):
        ring = []
        for i in range(n):
            a = 2 * math.pi * (i + 0.5) / n
            r = max(4.0, R[i] + r_off)
            ring.append(bm.verts.new((b.x(CENTRE[0] + r * math.cos(a)), b.y(CENTRE[1] + r * math.sin(a)), z)))
        rings.append(ring)
    centre_top = bm.verts.new((b.x(CENTRE[0]), b.y(CENTRE[1]), MOUND_TOP))
    centre_bot = bm.verts.new((b.x(CENTRE[0]), b.y(CENTRE[1]), lb.SLAB_BOTTOM))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i])).material_index = mat
        bm.faces.new((rings[1][i], rings[1][j], centre_top)).material_index = mat
        bm.faces.new((rings[0][j], rings[0][i], centre_bot)).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)


def capsule_light(b, px, py, axis, mats, marble, pick):
    """A red light as the concept draws it: a rounded silver bezel, a dark well, a dark-red lens body
    with a chamfered top and on it the marbled glow (from the tile's own red pixels)."""
    metal, well, lens_body = mats
    L, T = BEZEL
    w, h = (L, T) if axis == "x" else (T, L)
    lozenge(b, px - w / 2, py - h / 2, px + w / 2, py + h / 2, T / 2, 4, CROSS_TOP - 0.04, 0.350, metal,
            bevel_px=0.8, bevel_z=0.006)
    lozenge(b, px - w / 2 + 1.3, py - h / 2 + 1.3, px + w / 2 - 1.3, py + h / 2 - 1.3, T / 2 - 1.3, 4,
            CROSS_TOP, 0.356, well)
    L2, T2 = LENS
    w, h = (L2, T2) if axis == "x" else (T2, L2)
    lozenge(b, px - w / 2, py - h / 2, px + w / 2, py + h / 2, T2 / 2, 4, CROSS_TOP, 0.352, lens_body,
            bevel_px=0.9, bevel_z=0.008)
    marble.sheet(px - w / 2 + 1.0, py - h / 2 + 1.0, px + w / 2 - 1.0, py + h / 2 - 1.0, T2 / 2 - 1.0, 0.3615, pick)


def machinery(b, x0, y0, x1, y1, mats, flip_x, flip_y):
    """A quadrant of the body: a low frame grid of bars round 2 x 2 bevelled panels, and pipe runs
    with flanged ends. flip_x / flip_y mirror the pipe layout so it runs towards the arms."""
    frame, panel_a, panel_b, pipe_m, flange = mats
    z = BODY_DECK
    bar = 1.4
    mx = (x0 + x1) / 2
    my = y0 + (y1 - y0) * 0.45
    # Frame: outer bars and a cross dividing the quadrant.
    for bx in ((x0, y0, x1, y0 + bar), (x0, y1 - bar, x1, y1), (x0, y0 + bar, x0 + bar, y1 - bar),
               (x1 - bar, y0 + bar, x1, y1 - bar), (mx - bar / 2, y0 + bar, mx + bar / 2, y1 - bar),
               (x0 + bar, my - bar / 2, x1 - bar, my + bar / 2)):
        b.wall_block(*bx, z - 0.02, z + 0.06, frame, bevel=0.4)
    # Panels in the four cells (alternating light and dark plates, with a bolt-like seam).
    cells = ((x0 + bar, y0 + bar, mx - bar / 2, my - bar / 2), (mx + bar / 2, y0 + bar, x1 - bar, my - bar / 2),
             (x0 + bar, my + bar / 2, mx - bar / 2, y1 - bar), (mx + bar / 2, my + bar / 2, x1 - bar, y1 - bar))
    for k, (cx0, cy0, cx1, cy1) in enumerate(cells):
        m = panel_a if k in (0, 3) else panel_b
        b.wall_block(cx0 + 0.6, cy0 + 0.6, cx1 - 0.6, cy1 - 0.6, z - 0.02, z + 0.035, m, bevel=0.25)
    # Pipes: one along the long side, near the arm, and one across the far cells.
    px_near = x1 - 3.2 if not flip_x else x0 + 3.2
    pipe(b, (px_near, y0 + 2.5), (px_near, y1 - 2.5), z + 0.035, 1.1, pipe_m, flange)
    py_run = (y0 + my) / 2 if not flip_y else (my + y1) / 2
    xa, xb = (x0 + 2.5, x1 - 6.0) if not flip_x else (x0 + 6.0, x1 - 2.5)
    pipe(b, (xa, py_run), (xb, py_run), z + 0.035, 0.9, pipe_m, flange)


def main():
    b = lb.Building("cross-pad")
    b.surface(deck=BODY_DECK, channel=False, pits=False, red=False)
    rng = random.Random("cross-pad-rocks")

    # The deck is only the machinery body (an octagon), the rest is the mound with its boulders.
    yy, xx = np.mgrid[0:b.H, 0:b.W] + 0.5
    x0, y0, x1, y1 = BODY
    c = BODY_CHAMFER
    body = ((xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
            & (xx - x0 + yy - y0 >= c) & (x1 - xx + yy - y0 >= c) & (xx - x0 + y1 - yy >= c) & (x1 - xx + y1 - yy >= c))
    b.height[~body] = np.nan
    floor = b.m(5, metallic=0.1, roughness=0.65)
    b.set_region(body, BODY_DECK, floor)
    metal_deck = b.m(3, metallic=0.5, roughness=0.45)
    step_mat = b.m(5, metallic=0.3, roughness=0.6)
    for ax0, ay0, ax1, ay1 in (V_ARM, H_ARM):
        b.raise_box(ax0 - STEP_PX, ay0 - STEP_PX, ax1 + STEP_PX, ay1 + STEP_PX, CROSS_STEP, step_mat)
    for ax0, ay0, ax1, ay1 in (V_ARM, H_ARM):
        b.raise_box(ax0, ay0, ax1, ay1, CROSS_TOP, metal_deck)
    deck = b.terrace(wall_mat=b.m(4, metallic=0.4, roughness=0.6))

    # The mound and its outline.
    R = polar_outline(b)
    rock_mats = [b.m(9, roughness=0.92), b.m(10, roughness=0.92), b.m(8, roughness=0.92)]
    mound(b, R, b.m(5, roughness=0.95))

    # Corner machinery.
    mach = (b.m(8, metallic=0.15, roughness=0.55), b.m(10, metallic=0.15, roughness=0.55),
            b.m(8, metallic=0.1, roughness=0.6), b.m(10, metallic=0.45, roughness=0.35), b.m(12, metallic=0.45, roughness=0.35))
    for k, q in enumerate(QUADS):
        machinery(b, *q, mach, flip_x=(k % 2 == 1), flip_y=(k >= 2))
    # Pipe stubs off the vertical arm's ends, into the rocks (concept: conduits above and below).
    for ys, ye in ((20.0, 27.0), (113.0, 120.0)):
        for px in (52.0, 68.0):
            pipe(b, (px, ys), (px, ye), BODY_DECK - 0.05, 1.1, mach[3], mach[4])
        b.wall_block(49, min(ys, ye) + 1.5, 71, max(ys, ye) - 1.5, BODY_DECK - 0.06, BODY_DECK + 0.02, mach[0], bevel=0.3)

    # Rails along the arms' sides (the concept's conduits between the lights and the paving).
    for rx0, ry0, rx1, ry1 in ((V_ARM[0] + 1, V_ARM[1] + 2, V_ARM[0] + 3, H_ARM[1] - 2),
                               (V_ARM[2] - 3, V_ARM[1] + 2, V_ARM[2] - 1, H_ARM[1] - 2),
                               (V_ARM[0] + 1, H_ARM[3] + 2, V_ARM[0] + 3, V_ARM[3] - 2),
                               (V_ARM[2] - 3, H_ARM[3] + 2, V_ARM[2] - 1, V_ARM[3] - 2),
                               (H_ARM[0] + 2, H_ARM[1] + 1, V_ARM[0] - 2, H_ARM[1] + 3),
                               (H_ARM[0] + 2, H_ARM[3] - 3, V_ARM[0] - 2, H_ARM[3] - 1),
                               (V_ARM[2] + 2, H_ARM[1] + 1, H_ARM[2] - 2, H_ARM[1] + 3),
                               (V_ARM[2] + 2, H_ARM[3] - 3, H_ARM[2] - 2, H_ARM[3] - 1)):
        b.wall_block(rx0, ry0, rx1, ry1, CROSS_TOP - 0.02, CROSS_TOP + 0.02, b.m(7, metallic=0.5, roughness=0.4),
                     bevel=0.5)

    # The lights: three per arm, framed, the lenses marbled from the tiles' red pixels.
    marble = Marble(b)
    lens_q = {113: b.m(113, emission_strength=1.6, roughness=0.3), 115: b.m(115, emission_strength=2.2, roughness=0.25),
              117: b.m(117, emission_strength=2.8, roughness=0.25), 119: b.m(119, emission_strength=3.2, roughness=0.2),
              121: b.m(121, emission_strength=3.4, roughness=0.2)}

    def lens_pick(g):
        if g < 114:
            return lens_q[113]
        if g < 116:
            return lens_q[115]
        if g < 118:
            return lens_q[117]
        if g < 120:
            return lens_q[119]
        return lens_q[121]

    core_q = {114: b.m(114, emission_strength=1.8, roughness=0.3), 118: b.m(118, emission_strength=3.0, roughness=0.25),
              120: b.m(120, emission_strength=3.6, roughness=0.2), 122: b.m(122, emission_strength=4.0, roughness=0.2),
              124: b.m(124, emission_strength=4.4, roughness=0.2)}

    def core_pick(g):
        if g < 113:
            return core_q[114]
        if g < 115:
            return core_q[118]
        if g < 117:
            return core_q[120]
        if g < 119:
            return core_q[122]
        return core_q[124]

    mats = (b.m("metal"), b.m(lb.PAL["red_dark"], metallic=0.3, roughness=0.5),
            b.m(112, emission_strength=1.2, roughness=0.3))
    for py in CAP_Y_TOP + CAP_Y_BOTTOM:
        capsule_light(b, CAP_X, py, "x", mats, marble, lens_pick)
    for px in CAP_X_LEFT + CAP_X_RIGHT:
        capsule_light(b, px, CAP_Y, "y", mats, marble, lens_pick)

    # The core: an octagonal silver frame round a hot orange square with a darker swirl, with clamp
    # plates on its sides as in the concept.
    cx0, cy0, cx1, cy1 = CORE
    lozenge(b, cx0, cy0, cx1, cy1, 3.5, 1, CROSS_TOP - 0.04, 0.360, b.m("metal"), bevel_px=1.0, bevel_z=0.008)
    lozenge(b, cx0 + 2.6, cy0 + 2.6, cx1 - 2.6, cy1 - 2.6, 2.0, 1, CROSS_TOP, 0.364, mats[1])
    lozenge(b, cx0 + 3.4, cy0 + 3.4, cx1 - 3.4, cy1 - 3.4, 1.5, 1, CROSS_TOP, 0.362, b.m(114, emission_strength=1.6),
            bevel_px=1.0, bevel_z=0.006)
    marble.sheet(cx0 + 4.2, cy0 + 4.2, cx1 - 4.2, cy1 - 4.2, 1.0, 0.3695, core_pick)
    ccx, ccy = (cx0 + cx1) / 2, (cy0 + cy1) / 2
    clamp = b.m(7, metallic=0.5, roughness=0.4)
    for bx in ((ccx - 3, cy0 - 1.5, ccx + 3, cy0 + 1.5), (ccx - 3, cy1 - 1.5, ccx + 3, cy1 + 1.5),
               (cx0 - 1.5, ccy - 3, cx0 + 1.5, ccy + 3), (cx1 - 1.5, ccy - 3, cx1 + 1.5, ccy + 3)):
        b.wall_block(*bx, CROSS_TOP, 0.372, clamp, bevel=0.3)

    # The boulders: Poisson-disc over the rock zone (the footprint outside the body), outer band
    # first with big rocks standing on the ground, then smaller ones on the mound.
    d = lb.depth(b.footprint)
    zone = b.footprint & ~lb.erode(body, 3)
    arms = np.zeros_like(zone)
    for ax0, ay0, ax1, ay1 in (V_ARM, H_ARM):
        arms |= b.box_mask(ax0 - 3, ay0 - 3, ax1 + 3, ay1 + 3)
    taken = []

    def place(cands, spacing, r_rng, z_of, top_rng):
        order = list(range(len(cands)))
        rng.shuffle(order)
        for i in order:
            py, px = cands[i]
            px, py = px + 0.5, py + 0.5
            if any((qx - px) ** 2 + (qy - py) ** 2 < (spacing * 0.5 + qs * 0.5) ** 2 for qx, qy, qs in taken):
                continue
            taken.append((px, py, spacing))
            r = r_rng[0] + (r_rng[1] - r_rng[0]) * rng.random()
            top = top_rng[0] + (top_rng[1] - top_rng[0]) * rng.random()
            x0_, y0_ = int(max(0, px - r - 1)), int(max(0, py - r - 1))
            x1_, y1_ = int(min(b.W, px + r + 2)), int(min(b.H, py + r + 2))
            if b.enemy_mask[y0_:y1_, x0_:x1_].any():
                top = min(top, lb.ENEMY_MAX - 0.01)
            boulder(b, rng, px, py, r, z_of(px, py), top, rock_mats[rng.randrange(len(rock_mats))])

    outer = np.argwhere(zone & (d >= 3) & (d <= 6) & ~arms)
    place(outer, 10.0, (5.5, 7.0), lambda px, py: lb.SLAB_BOTTOM, (0.40, lb.RIM_MAX))
    inner = np.argwhere(zone & (d > 6) & ~arms)
    place(inner, 8.0, (4.0, 5.5), lambda px, py: MOUND_TOP - 0.10, (0.30, 0.42))
    # Fill: small rocks wherever the mound still shows.
    fill = np.argwhere(zone & (d >= 2) & ~arms)
    place(fill, 6.0, (3.0, 4.2), lambda px, py: MOUND_TOP - 0.08, (0.24, 0.36))
    print(f"boulders: {len(taken)}")

    objects = b.objects(deck)
    objects.append(lb.mesh_object(f"{lb.SHAPES}-l1bld-{b.name}-marble", marble.bm, b.pal.materials,
                                  objects[0].users_collection[0]))
    b.check(objects)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects)
    print(f"triangles: {tris}")
    b.export(objects)


main()
