"""Flying ear, lobe at the bottom left (newsh5.shp frame 245): a 3D version of its sprite.

Seen in episode 4 (level 20), beside its mirror image newsh5-284. A fleshy tan ear: a convex pod
on a flat base whose rounded rim (helix) rises to a crest about 8-9 px up (lower toward the pod's
ends), a bowl inside it (the concha and fossa) whose floor sits about 3-4 px below the crest, with
the concha's dark channels cut about 1 px deeper, the broad antihelix swell standing 1-2 px proud of
the floor from the lobe up the bowl, and a thick rounded lobe at the bottom left.

Built as one height field over the sprite's own (smoothed) outline: rings of vertices from the
outline in to the middle, raised by a quarter-ellipse of the distance to the edge (a side that is
vertical just above a small rounded lip and curves over to the crest) times a dome over the pod's
principal axes, and lowered where the sprite is drawn dark inside the rim. The sprite's tans,
browns and cream highlights are its drawn lighting on that shape, not paint: the skin is one matte
mid-tan (25) all over, the game's lights shade the rim, bowl and channels, and the game draws the
dark edge, so the sides are skin too. Only the floor of the concha's channels is a shade darker
(24), following the smooth groove field rather than the sprite's pixels. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-245.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-245"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

W, H = 24, 28  # sprite block, px
OUTLINE_IDX = {1, 16, 17}  # the sprite's dark edge pixels (the game draws its own outline)

LIP = 1.2  # the outline ring's height above the flat base: the body is widest just above it, px
CREST = 9.6  # rim crest above the lip where the pod is fullest, px
DOME_MIN = 0.5  # the crest's fraction of CREST at the far ends of the pod (a convex loaf, no shelf)
EDGE_W = 5.0  # how far in from the edge the rounded side reaches full height, px
UNDER_W = 1.6  # the rounded underside lip curls in to the flat base over this, px
BOWL = 5.0  # the bowl inside the rim, below the crest, px
GROOVE = 1.1  # extra depth of the sprite's darkest channels in the bowl floor, px
RIDGE = 1.4  # the antihelix swell standing proud of the bowl floor, px
RIDGE_W = 1.5  # its half width (gaussian sigma), px
# The antihelix in sprite px (pixel-edge coords): from the lobe up the bowl, and its upper fork.
RIDGE_PATHS = [[(8.8, 19.0), (11.5, 15.8), (12.4, 12.5), (13.5, 9.5), (13.6, 7.6)],
               [(12.4, 12.5), (11.0, 10.3), (10.4, 9.4)]]

SIDES = 80  # vertices round the outline
TOP_RINGS = 22
UNDER_RINGS = 4

# Material slots: skin is matte flesh in the sprite's mid-tan; the deep bowl floor and the concha's
# channels are a shade and two darker (the recess the game's unshadowed light can't darken), by the
# smooth bowl depth, not the sprite's pixels. The sprite's outline (1, 16, 17), dark browns and
# cream highlights are its drawn shading.
SKIN, FLOOR, CHANNEL = 25, 24, 23
RAMP = [CHANNEL, FLOOR, SKIN]
SLOT = {i: RAMP.index(i) for i in RAMP}
FLOOR_AT = 3.6  # bowl depth below the rim surface beyond which it is the floor shade, px
CHANNEL_AT = 0.5  # the groove field's level above which the floor is the channel shade
METALLIC, ROUGHNESS = 0.0, 0.72  # skin: no metal, a soft sheen at most
GLOW = 0.06  # a touch of its own palette colour, so the bowl isn't muddy


def gauss_blur(grid, sigma):
    rad = int(math.ceil(sigma * 3))
    k = [math.exp(-0.5 * (i / sigma) ** 2) for i in range(-rad, rad + 1)]
    s = sum(k)
    k = [v / s for v in k]
    h, w = len(grid), len(grid[0])
    tmp = [[sum(k[j + rad] * grid[r][min(w - 1, max(0, c + j))] for j in range(-rad, rad + 1))
            for c in range(w)] for r in range(h)]
    return [[sum(k[j + rad] * tmp[min(h - 1, max(0, r + j))][c] for j in range(-rad, rad + 1))
             for c in range(w)] for r in range(h)]


def bilinear(grid, u, v):
    """Sample a per-pixel grid at continuous sprite coordinates (u, v) = (column, row) edges."""
    h, w = len(grid), len(grid[0])
    x, y = u - 0.5, v - 0.5
    c0, r0 = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - c0, y - r0
    def g(r, c):
        return grid[min(h - 1, max(0, r))][min(w - 1, max(0, c))]
    return ((g(r0, c0) * (1 - fx) + g(r0, c0 + 1) * fx) * (1 - fy)
            + (g(r0 + 1, c0) * (1 - fx) + g(r0 + 1, c0 + 1) * fx) * fy)


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def seg_dist(px_, py_, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = ((px_ - ax) * dx + (py_ - ay) * dy) / (dx * dx + dy * dy or 1)
    t = min(1.0, max(0.0, t))
    return math.hypot(px_ - ax - t * dx, py_ - ay - t * dy)


def resample(poly, n):
    """n points evenly spaced along a closed polygon."""
    segs = list(zip(poly, poly[1:] + poly[:1]))
    lens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs]
    total = sum(lens)
    out, i, acc = [], 0, 0.0
    for k in range(n):
        target = total * k / n
        while acc + lens[i] < target:
            acc += lens[i]
            i += 1
        (ax, ay), (bx, by) = segs[i]
        t = (target - acc) / (lens[i] or 1)
        out.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    return out


class Field:
    """The ear's surface heights over the sprite, in sprite px (u = column, v = row, pixel edges)."""

    def __init__(self, pixels):
        self.pixels = pixels
        inner = lambda i: i >= 0 and i not in OUTLINE_IDX  # noqa: E731
        dark = [[min(1.0, max(0.0, (25.5 - i) / 5.5)) if inner(i) else 0.0 for i in row] for row in pixels]
        wide = gauss_blur(dark, 2.2)
        top = max(max(r) for r in wide)
        self.wide = [[min(1.0, v / (0.55 * top)) for v in r] for r in wide]
        # The dark channels of the concha on the left of the bowl (the sprite's 18-21 there), cut in
        # as grooves; the dark fossa at the top right stays part of the shallow bowl.
        groove = [[1.0 if inner(i) and i <= 21 and 7 <= r <= 17 and c <= 11 else 0.0
                   for c, i in enumerate(row)] for r, row in enumerate(pixels)]
        self.groove = gauss_blur(groove, 0.6)
        # Outline in sprite px (counter-clockwise in Blender), pushed out a little so the sprite's
        # dark edge pixels are covered, then smoothed (Taubin) so the sides carry no stair steps.
        poly = lib.mask_outline(pixels, lambda i: i >= 0, size=2, inset=-0.1)
        pts = resample([(x * 12 + W / 2, H / 2 - y * 12) for x, y in poly], SIDES)
        for _ in range(8):
            for lam in (0.5, -0.53):
                n = len(pts)
                pts = [(p[0] + lam * (0.5 * (pts[k - 1][0] + pts[(k + 1) % n][0]) - p[0]),
                        p[1] + lam * (0.5 * (pts[k - 1][1] + pts[(k + 1) % n][1]) - p[1]))
                       for k, p in enumerate(pts)]
        self.outline = resample(pts, SIDES)
        n = len(self.outline)
        self.cu = sum(p[0] for p in self.outline) / n
        self.cv = sum(p[1] for p in self.outline) / n
        # Principal axes of the outline, for the pod's overall convex dome.
        suu = sum((p[0] - self.cu) ** 2 for p in self.outline)
        svv = sum((p[1] - self.cv) ** 2 for p in self.outline)
        suv = sum((p[0] - self.cu) * (p[1] - self.cv) for p in self.outline)
        ang = 0.5 * math.atan2(2 * suv, suu - svv)
        self.ax = (math.cos(ang), math.sin(ang))
        proj = [((p[0] - self.cu) * self.ax[0] + (p[1] - self.cv) * self.ax[1],
                 -(p[0] - self.cu) * self.ax[1] + (p[1] - self.cv) * self.ax[0]) for p in self.outline]
        self.half = (max(abs(s) for s, _ in proj), max(abs(t) for _, t in proj))

    def edge_dist(self, u, v):
        pts = self.outline
        return min(seg_dist(u, v, *a, *b) for a, b in zip(pts, pts[1:] + pts[:1]))

    def dome(self, u, v):
        """1 in the middle of the pod, DOME_MIN at its far ends: the rim crest follows a convex dome."""
        du, dv = u - self.cu, v - self.cv
        s = (du * self.ax[0] + dv * self.ax[1]) / self.half[0]
        t = (-du * self.ax[1] + dv * self.ax[0]) / self.half[1]
        q = min(1.0, s * s + 0.5 * t * t)
        return DOME_MIN + (1 - DOME_MIN) * math.sqrt(1 - q)

    def ridge(self, u, v):
        d = min(seg_dist(u, v, *a, *b) for path in RIDGE_PATHS for a, b in zip(path, path[1:]))
        return math.exp(-0.5 * (d / RIDGE_W) ** 2)

    def top(self, u, v, d):
        # A rounded side: vertical just above the lip, curving over to the crest (a quarter ellipse).
        x = min(d / EDGE_W, 1.0)
        body = CREST * self.dome(u, v) * math.sqrt(1 - (1 - x) ** 2)
        return LIP + body - smoothstep(2.0, 4.8, d) * self.bowl(u, v)

    def bowl(self, u, v):
        """How far the bowl floor sits below the rim's surface here, px."""
        depth = BOWL * smoothstep(0.1, 0.6, bilinear(self.wide, u, v))
        depth += GROOVE * bilinear(self.groove, u, v)
        depth -= RIDGE * self.ridge(u, v)
        return max(0.0, depth)

    def under(self, d):
        # The lip curls under to the flat base at 0 (no undercut below it).
        x = min(d / UNDER_W, 1.0)
        return LIP * (1 - math.sqrt(1 - (1 - x) ** 2))


def to_xy(u, v):
    return (u - W / 2) / 12, (H / 2 - v) / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [pal(i, metallic=METALLIC, roughness=ROUGHNESS, emission_strength=GLOW) for i in RAMP]
    field = Field(sprite["frames"][0]["pixels"])
    cu, cv = field.cu, field.cv

    bm = bmesh.new()

    def rings(count, power, height):
        """Rings from the outline (t = 0) toward the middle; returns vertex rings and the centre."""
        out = []
        for k in range(count):
            t = (k / count) ** power
            ring = []
            for u0, v0 in field.outline:
                u, v = u0 + (cu - u0) * t, v0 + (cv - v0) * t
                d = field.edge_dist(u, v) if k else 0.0
                z = height(u, v, d)
                x, y = to_xy(u, v)
                ring.append(bm.verts.new((x, y, z / 12)))
            out.append(ring)
        d = field.edge_dist(cu, cv)
        x, y = to_xy(cu, cv)
        centre = bm.verts.new((x, y, height(cu, cv, d) / 12))
        return out, centre

    top, tc = rings(TOP_RINGS, 1.7, field.top)
    under, uc = rings(UNDER_RINGS, 2.5, lambda u, v, d: field.under(d))
    under[0] = top[0]  # share the edge ring at the midplane

    def skin(rs, centre, flip):
        faces = []
        for r0, r1 in zip(rs, rs[1:]):
            for k in range(SIDES):
                j = (k + 1) % SIDES
                q = (r0[k], r0[j], r1[j], r1[k])
                faces.append(bm.faces.new(q[::-1] if flip else q))
        last = rs[-1]
        for k in range(SIDES):
            j = (k + 1) % SIDES
            tri = (last[k], last[j], centre)
            faces.append(bm.faces.new(tri[::-1] if flip else tri))
        return faces

    # The outline is counter-clockwise in Blender, so (r0[k], r0[j], r1[j], r1[k]) faces up.
    top_faces = skin(top, tc, False)
    under_faces = skin(under, uc, True)
    # The unused first under ring was replaced by the top's edge ring; drop its loose vertices.
    bm.verts.ensure_lookup_table()
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")

    bm.normal_update()
    for f in top_faces:
        c = f.calc_center_median()
        u, v = c.x * 12 + W / 2, H / 2 - c.y * 12
        i = SKIN
        if field.edge_dist(u, v) > 3.0 and field.bowl(u, v) > FLOOR_AT:
            i = CHANNEL if bilinear(field.groove, u, v) > CHANNEL_AT else FLOOR
        f.material_index = SLOT[i]
    for f in under_faces:
        f.material_index = SLOT[SKIN]

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
