"""Green fighter (newshf.shp frames 1, 3, 5): a 3D version of its sprite.

Seen in episode 1 (from level section 10) and episode 4. It flies nose down the screen: a
pointed hull with swept wings at the back, two yellow eyes, a pale spike behind with brown horns
either side, and a mottled green skin with a pale spine, near-black gaps and a dark vent with a
pale light in its lower half. The three frames roll it about its long axis: on frame 1 its back
turns to the left (the eyes, spike and markings sit a pixel left, the right wing is lit and both
wings look shorter), frame 3 is level (wings at full span, with two extra orange lights on the left
horn and right wing tip), and frame 5 rolls the other way. The sprite shows that roll only as its
markings sliding sideways, and so does the model.

One body (frame 1's outline, the frame the others are drawn from): a smooth hull whose height is a
round profile of the distance to the smoothed outline, cresting at about 5 px along the spine and
falling to about 1.5 px over the narrow wing strips, with a shallower belly below (about 2 px under
the spine, under 1 px at the wings), so the ship is about 7 px thick and its wings about 2. The
belly and the walls are the hull's mid-tone green. Over it each frame has its own skin, a surface
with one face per pixel (common.frame_part) in that pixel's marking colour or else the hull's mid-
tone (see marking: the sprite's outline ring and shading are left to the game's light and outline);
frames 3 and 5 lie a hair under frame 1's skin so they never show through it. The lower vent is a
2x2 px pit 1 px deep with the pale light in it. The spike and horns are tapered cones (shared by all
frames), the eyes small emissive domes (frame 1, where the review compares), and the right
shoulder's orange light a dome on every frame.

The ship's centre line is column 13 (x = 1.5 px), not the block's centre.

Run: blender --background --python assets/blender/enemies/newshf-1.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshf-1"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
SPINE = 13.5  # pixel-corner column of the ship's centre line
EDGE = 0.45  # half the thickness of the hull at its outline, px
CREST = 5.2  # top of the hull along the spine, px
BELLY = 2.0  # depth of the belly under the spine, px
RADIUS = 4.5  # distance from the outline (px) at which the profile tops out
SINK = {1: 0.0, 3: 0.2, 5: 0.35}  # how far each frame's skin lies under frame 1's (interior only), px
VENT = [(17, 11), (17, 12), (18, 11), (18, 12)]  # the lower vent's pixels: a pit with a pale light
VENT_DEPTH = 1.0

# The sprite draws its light: a near-black outline ring, a mottle of greens that is mostly shading
# (dark on the lower right, the lit wing on the roll), highlights. The game lights the model and
# draws its own outline, so each skin keeps only the real markings: the pale spine plates, the
# near-black vent and gaps inside the hull, the brown wing-root panels and horn bases, the eyes and
# lights. Everything else is the hull's mid-tone green, and the light shades it.
HULL = 40  # the hull's mid-tone green: skins, walls and belly
PALE = 44  # the pale spine plates
DARK = 32  # the vent and the gaps inside the hull
BROWN = {20: 24, 22: 24, 23: 24, 24: 24, 25: 26, 26: 26}  # horn bases and wing-root panels
EYE, LIGHT = 125, 122
WALL, UNDER = HULL, HULL  # side walls and belly
HORN = 24  # the horns' mid-tone brown
METAL = dict(metallic=0.35, roughness=0.45)  # painted metal hull


def marking(hull, r, c, i):
    """The palette index a skin face at pixel (r, c), drawn as `i` in its frame, gets: its marking
    colour, or the hull's mid-tone where the sprite only draws light or the outline there."""
    if i in (EYE, LIGHT):
        return i
    if i in BROWN:
        return BROWN[i]
    rim = not all(hull.inside(r + dr, c + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    spine = abs(c + 0.5 - SPINE) <= 2.5
    if i in (1, 32, 33) and spine and not rim:
        return DARK  # the vent and the gaps by the spike (dark pixels elsewhere are outline or shade)
    if i >= PALE and spine:
        return PALE  # the pale plates along the spine (pale wing pixels are the lit wing)
    return HULL


def lateral(x):
    """How much of the crest a corner `x` columns off the spine keeps: the hull's full height near
    the spine, falling to the wing roots and wings."""
    u = abs(x - SPINE)
    return max(0.35, min(1.0, 1.0 - (u - 1.5) / 4.5))


def profile(t):
    return 1.0 - (1.0 - t) ** 2


class Hull:
    """Frame 1's outline: pixel corners, their smoothed xy, top and bottom heights (px)."""

    def __init__(self, pix):
        self.pix = pix
        rows, cols = len(pix), len(pix[0])
        self.inside = lambda r, c: 0 <= r < rows and 0 <= c < cols and pix[r][c] >= 0  # noqa: E731
        self.cells = [(r, c) for r in range(rows) for c in range(cols) if self.inside(r, c)]
        self.corners = {k for r, c in self.cells for k in ((r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1))}
        self.edge = {k for k in self.corners if not all(self.inside(*p) for p in self.around(k))}

        # Boundary edges between pixel corners, in order around each cell.
        sides = []
        for r, c in self.cells:
            for (dr, dc), (a, b) in (((-1, 0), ((r, c), (r, c + 1))), ((1, 0), ((r + 1, c + 1), (r + 1, c))),
                                     ((0, -1), ((r + 1, c), (r, c))), ((0, 1), ((r, c + 1), (r + 1, c + 1)))):
                if not self.inside(r + dr, c + dc):
                    sides.append((a, b))
        self.sides = sides
        links = {}
        for a, b in sides:
            links.setdefault(a, []).append(b)
            links.setdefault(b, []).append(a)
        # Round the outline's staircase twice: each outline corner moves halfway to the midpoint of its
        # two neighbours along the outline (one-pixel steps become diagonals, straight runs stay put).
        xy = {k: (float(k[1]), float(k[0])) for k in self.corners}
        for _ in range(2):
            nxt = dict(xy)
            for k, ns in links.items():
                if len(ns) == 2:
                    a, b = xy[ns[0]], xy[ns[1]]
                    nxt[k] = (0.5 * xy[k][0] + 0.25 * (a[0] + b[0]), 0.5 * xy[k][1] + 0.25 * (a[1] + b[1]))
            xy = nxt
        self.xy = xy

        segs = [(xy[a], xy[b]) for a, b in sides]

        def dist(p):
            best = 1e9
            for (ax, ay), (bx, by) in segs:
                dx, dy = bx - ax, by - ay
                t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy or 1)))
                best = min(best, math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy))
            return best

        top, bot = {}, {}
        for k in self.corners:
            if k in self.edge:
                top[k], bot[k] = EDGE, -EDGE
                continue
            s = profile(min(dist(xy[k]), RADIUS) / RADIUS) * lateral(xy[k][0])
            top[k] = EDGE + (CREST - EDGE) * s
            bot[k] = -(EDGE + (BELLY - EDGE) * s)
        # Smooth the heights (interior corners) so no pixel stands out as a bump.
        for _ in range(3):
            for h in (top, bot):
                new = dict(h)
                for k in self.corners - self.edge:
                    ns = [n for n in ((k[0] + 1, k[1]), (k[0] - 1, k[1]), (k[0], k[1] + 1), (k[0], k[1] - 1))
                          if n in h]
                    new[k] = 0.5 * h[k] + 0.5 * sum(h[n] for n in ns) / len(ns)
                h.update(new)
        # The vent: a pit under its pixels.
        pit = {k for r, c in VENT for k in ((r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1))}
        floor = min(top[k] for k in pit) - VENT_DEPTH
        for k in pit:
            top[k] = floor
        self.top, self.bot = top, bot

    @staticmethod
    def around(k):
        r, c = k
        return [(r + dr, c + dc) for dr in (-1, 0) for dc in (-1, 0)]

    def co(self, k, z):
        x, y = self.xy[k]
        return ((x - 12) / 12, (14 - y) / 12, z / 12)

    def skin_z(self, r, c):
        """Top of the skin at a point inside pixel (r, c) (fractional), by bilinear interpolation."""
        r0, c0 = int(math.floor(r)), int(math.floor(c))
        fr, fc = r - r0, c - c0
        get = lambda k: self.top.get(k, EDGE)  # noqa: E731
        return ((1 - fr) * ((1 - fc) * get((r0, c0)) + fc * get((r0, c0 + 1)))
                + fr * ((1 - fc) * get((r0 + 1, c0)) + fc * get((r0 + 1, c0 + 1))))


def body(hull, slot):
    """Belly and side walls (open at the top, where the skins close it)."""
    bm = bmesh.new()
    low = {k: bm.verts.new(hull.co(k, hull.bot[k])) for k in hull.corners}
    for r, c in hull.cells:
        bm.faces.new((low[(r, c)], low[(r, c + 1)], low[(r + 1, c + 1)], low[(r + 1, c)])).material_index = slot[UNDER]
    # The walls have their own vertices, so they shade smoothly round the outline without bending
    # the belly's normals.
    top = {k: bm.verts.new(hull.co(k, hull.top[k])) for k in hull.edge}
    foot = {k: bm.verts.new(hull.co(k, hull.bot[k])) for k in hull.edge}
    for a, b in hull.sides:
        bm.faces.new((top[a], top[b], foot[b], foot[a])).material_index = slot[WALL]
    return bm


def skin(hull, pix, sink, slot):
    """One frame's skin over the hull: a face per pixel of frame 1's outline, in this frame's marking
    colour there (the hull's mid-tone where this frame has no pixel)."""
    bm = bmesh.new()
    v = {k: bm.verts.new(hull.co(k, hull.top[k] - (0.0 if k in hull.edge else sink))) for k in hull.corners}
    for r, c in hull.cells:
        i = pix[r][c] if pix[r][c] >= 0 else HULL
        f = bm.faces.new((v[(r + 1, c)], v[(r + 1, c + 1)], v[(r, c + 1)], v[(r, c)]))
        f.material_index = slot[marking(hull, r, c, i)]
    return bm


def lamps(pix, index):
    """Connected clusters of the eye or light pixels."""
    out, seen = [], set()
    rows, cols = len(pix), len(pix[0])
    for r in range(rows):
        for c in range(cols):
            if pix[r][c] != index or (r, c) in seen:
                continue
            group, todo = [], [(r, c)]
            seen.add((r, c))
            while todo:
                p = todo.pop()
                group.append(p)
                for q in ((p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)):
                    if 0 <= q[0] < rows and 0 <= q[1] < cols and q not in seen and pix[q[0]][q[1]] == index:
                        seen.add(q)
                        todo.append(q)
            out.append(group)
    return out


def add_lamp(bm, hull, group, mat, height):
    """A small emissive oblong dome over a cluster of pixels, `height` px proud of the skin."""
    r0 = min(p[0] for p in group)
    r1 = max(p[0] for p in group) + 1
    c0 = min(p[1] for p in group)
    c1 = max(p[1] for p in group) + 1
    hw, hl = (c1 - c0) / 2 * 0.8, (r1 - r0) / 2 * 0.85
    cx, cr = (c0 + c1) / 2, (r0 + r1) / 2
    zs = [hull.skin_z(cr + dr, cx + dc) for dr in (-hl * 0.7, 0, hl * 0.7) for dc in (-hw * 0.7, 0, hw * 0.7)]
    zc = sum(zs) / len(zs) - 0.15
    y0, y1 = (14 - cr - hl) / 12, (14 - cr + hl) / 12
    ym = (y0 + y1) / 2
    start = len(bm.verts)
    common.loft(bm, [(y0, 0.0, 0.0, zc / 12),
                     (ym - hl * 0.55 / 12, hw / 12, (height + 0.15) / 12, zc / 12),
                     (ym + hl * 0.55 / 12, hw / 12, (height + 0.15) / 12, zc / 12),
                     (y1, 0.0, 0.0, zc / 12)], sides=6, mat_index=mat)
    common.shift_x(bm, start, (cx - 12) / 12)


def add_prong(bm, hull, base, tip, width, height, mat):
    """A tapered cone lying along the hull from `base` (row, col) to its point at `tip` (row, col):
    `width` px across and `height` px tall at the base, sunk into the skin under it."""
    (rb, cb), (rt, ct) = base, tip
    zb = hull.skin_z(rb, cb)
    zt = hull.skin_z(min(rt + 0.5, rb), ct)
    sections = []
    for t, w, h in ((-0.25, 0.9, 0.7), (0.0, 1.0, 1.0), (0.45, 0.7, 0.75), (0.8, 0.35, 0.4), (1.0, 0.0, 0.0)):
        r = rb + (rt - rb) * t
        c = cb + (ct - cb) * t
        zs = zb + (zt - zb) * max(t, 0.0) - (0.4 if t < 0 else 0.0)
        zc = zs + h * height / 2 - 0.25 if t < 1 else zs + 0.4
        sections.append((r, c, w * width / 2, h * height / 2, zc))
    # loft builds along +Y on the centreline; build it straight, then bend each ring over to its column.
    start = len(bm.verts)
    common.loft(bm, [((14 - r) / 12, w / 12, h / 12, z / 12) for r, _, w, h, z in sections], sides=6, mat_index=mat)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        row = 14 - v.co.y * 12
        # The column of the cone's axis at this row (sections run from base to tip).
        f = (row - rb) / (rt - rb) if rt != rb else 0.0
        v.co.x += ((cb + (ct - cb) * f) - 12) / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    frames = {f["index"]: f for f in sprite["frames"]}
    hull = Hull(frames[1]["pixels"])
    used = sorted({marking(hull, r, c, i) for f in sprite["frames"] for r, row in enumerate(f["pixels"])
                   for c, i in enumerate(row) if i >= 0 and hull.inside(r, c)}
                  | {WALL, UNDER, HULL, PALE, HORN})
    mats, slot = [], {}
    for i in used:
        if i == EYE:
            kw = dict(emission_strength=3.0)
        elif i == LIGHT:
            kw = dict(emission_strength=2.5)
        else:
            kw = METAL
        slot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, NAME, **kw))

    # The body, the prongs and the right shoulder's light show on every frame.
    bm = body(hull, slot)
    add_prong(bm, hull, (5.6, 12.5), (1.7, 12.5), 1.5, 2.3, slot[PALE])  # the pale spike
    add_prong(bm, hull, (6.0, 10.5), (2.8, 10.5), 1.4, 2.0, slot[HORN])  # left horn
    add_prong(bm, hull, (6.0, 15.6), (2.8, 15.4), 1.4, 2.0, slot[HORN])  # right horn
    for group in lamps(frames[1]["pixels"], LIGHT):
        add_lamp(bm, hull, group, slot[LIGHT], 0.6)
    parts = [common.mesh_object(f"{NAME}-body", bm, mats, coll, smooth=True)]

    for index in (1, 3, 5):
        bm = skin(hull, frames[index]["pixels"], SINK[index], slot)
        if index == 1:
            for group in lamps(frames[1]["pixels"], EYE):
                add_lamp(bm, hull, group, slot[EYE], 0.9)
        obj = common.mesh_object(f"{NAME}-f{index}", bm, mats, coll, smooth=True)
        parts.append(common.frame_part(obj, [index]))
    # A skin's normals face up; mesh_object's recalculation can't tell for an open sheet.
    for obj in parts[1:]:
        flip = sum(p.normal.z * p.area for p in obj.data.polygons) < 0
        if flip:
            obj.data.flip_normals()
    return parts


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objs = build(sprite)
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview(objs, out, ref, size=sprite["frames"][0]["size"], frame=sprite["frames"][0]["index"])


if __name__ == "__main__":
    main()
