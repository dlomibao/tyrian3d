"""Blue faceted orb (newshv.shp frames 153, 155, 157): a 3D version of its sprite.

Seen in episode 2 (level 2.15). The sprite is a faceted blue gem drawn lit: a bright centre
fading to a near-black rim, with a speckled diamond pattern on its surface (a pale outer diamond
band whose corners nearly reach the rim, mid-dark navy spots at the corners of an inner diamond,
pale speckles along the diagonals) and a white hot spot in the middle. So the model is a tall dome
(top ~8.5 px above the midplane on an ~19 px wide body) over a rounded underside, one smooth curve
with no relief: the white centre and the pale speckles are the gem's shine, which its glossy
material and the game's lights make, not humps. The diamond pattern is the gem's marking and stays
painted, but in three tones only (navy spots, the body's blue, a paler band; see tone), without the
sprite's light: no white hot spots, no darkening toward the rim, and the rim and underside take the
body's colour too, because the game draws the dark outline. The three frames only dim the whole orb
(a pulse), so one model covers them, its colours stepping darker frame by frame. newshv-123 is the
same disc in red (still built by lib_b003.gem_disc).

Run: blender --background --python assets/blender/enemies/newshv-153.py [-- --preview out.png] [--frame-previews frames.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b003 as lib  # noqa: E402

NAME = "newshv-153"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

U = 1 / 12          # one sprite px in units
R = 9.4             # body radius in px: the sprite's circle, its dark edge pixels included
H_TOP = 8.5         # dome height above the midplane, px
H_BOTTOM = 6.5      # underside depth, px
BODY_INDEX = 58     # the gem's mid-tone blue: the body, the rim band and the underside
EDGE_INDEX = 48     # the sprite's near-black outline pixels: modelled as the rim band instead
R_IN = 8.4          # where the pixel grid meets the rim band (the outline pixels are ~1 px wide)
# The rim band from R_IN out to R, as (outer radius px, palette index): the body's colour, as the
# game's outline effect draws the sprite's navy edge.
RELAX_FROM, RELAX, RELAX_STEPS = 6.0, 0.5, 3   # relaxing the pixel corners near the rim (px, weight, passes)
RIM_BANDS = [(8.8, BODY_INDEX), (9.15, BODY_INDEX), (R, BODY_INDEX)]
METALLIC, ROUGHNESS = 0.05, 0.12   # a glossy gem: the sun and environment make its shine


def tone(i, rim_pixel):
    """The painted tone for a sprite pixel of palette index i: the diamond pattern's navy spots,
    the body or the pale band. The sprite's dark pixels next to its outline are rim shading, not
    spots, so they take the body's colour."""
    if i <= 55:
        return BODY_INDEX if rim_pixel else 54
    if i <= 60:
        return BODY_INDEX
    return 61


def dome_z(r):
    """Height (px) of the dome's surface at distance r (px) from the centre."""
    t = min(1.0, r / R)
    return H_TOP * math.sqrt(max(0.0, 1.0 - t * t))


class SpriteField:
    """The sprite's frame-0 palette indices, looked up by position in px from the model's centre
    (x right, y up the screen)."""

    def __init__(self, frame):
        self.grid = [[int(v) for v in (row.split() if isinstance(row, str) else row)] for row in frame["pixels"]]
        self.cx, self.cy = frame["width"] / 2, frame["height"] / 2

    def index(self, x, y):
        row, col = math.floor(self.cy - y), math.floor(self.cx + x)
        if 0 <= row < len(self.grid) and 0 <= col < len(self.grid[0]) and self.grid[row][col] >= 0:
            return self.grid[row][col]
        return None


def orb(sprite):
    import bmesh
    coll = common.reset_collection(NAME)
    f1, f2 = (f["index"] for f in sprite["frames"][1:3])
    field = SpriteField(sprite["frames"][0])

    mats, slot = [], {}

    def mat(i):
        """Material slot for palette index i, dimming on the pulse frames like the sprite."""
        if i not in slot:
            slot[i] = len(mats)
            mats.append(common.palette_material(
                sprite, i, f"{NAME}-pulse", frames={f1: max(48, i - 2), f2: max(48, i - 4)},
                metallic=METALLIC, roughness=ROUGHNESS))
        return slot[i]

    # Top: one quad per sprite pixel inside the dark outline, coloured with that pixel's palette
    # index, its corners lifted onto the dome. Every corner's distance from the centre is rescaled
    # along its ray so that the pixels' staircase edge lands on the circle of radius R_IN: corners
    # at the same depth inside the outline sit at the same height (no teeth). The outline pixels
    # themselves become a smooth dark navy band from R_IN down to the round rim at R.
    grid = field.grid
    cells = [(row, col) for row in range(len(grid)) for col in range(len(grid[0]))
             if grid[row][col] >= 0 and grid[row][col] != EDGE_INDEX]

    def corners(row, col):
        x0, y0 = col - field.cx, field.cy - row
        return [(x0, y0), (x0 + 1, y0), (x0 + 1, y0 - 1), (x0, y0 - 1)]

    edge_use = {}
    for row, col in cells:
        c = corners(row, col)
        for k in range(4):
            e = frozenset((c[k], c[(k + 1) % 4]))
            edge_use[e] = edge_use.get(e, 0) + 1
    outline = [e for e, n in edge_use.items() if n == 1]

    # The outline as one loop, walked edge to edge.
    nbr = {}
    for e in outline:
        p, q = tuple(e)
        nbr.setdefault(p, []).append(q)
        nbr.setdefault(q, []).append(p)
    assert all(len(v) == 2 for v in nbr.values()), "the sprite's outline isn't one simple loop"
    loop = [min(nbr)]
    prev = None
    while True:
        a, b_ = nbr[loop[-1]]
        nxt = b_ if a == prev else a
        if nxt == loop[0]:
            break
        prev = loop[-1]
        loop.append(nxt)
    assert len(loop) == len(nbr)

    def outline_radius(x, y):
        """Distance from the centre to the pixel outline along the ray through (x, y)."""
        best = None
        for (ax, ay), (bx, by) in zip(loop, loop[1:] + loop[:1]):
            ex, ey = bx - ax, by - ay
            den = x * ey - y * ex
            if abs(den) < 1e-12:
                continue
            t = (ax * ey - ay * ex) / den      # along the ray
            u = (ax * y - ay * x) / den        # along the edge
            if t > 0 and -1e-9 <= u <= 1 + 1e-9:
                best = t if best is None else min(best, t)
        return math.hypot(x, y) * best

    # Pixel corners in the plane: each one's distance from the centre is rescaled so the pixels'
    # edge lands on the circle of radius R_IN. Near the rim the staircase still leaves slivers, so
    # the corners within ~2 px of the edge are relaxed toward their neighbours' average (the edge
    # loop stays put), which evens out the last rows of pixels.
    plane = {}
    links = {}
    for row, col in cells:
        c = corners(row, col)
        for k in range(4):
            x, y = c[k]
            if (x, y) not in plane:
                r = math.hypot(x, y)
                f = R_IN / outline_radius(x, y) if r > 1e-9 else 1.0
                plane[(x, y)] = (x * f, y * f)
            links.setdefault(c[k], set()).update((c[(k + 1) % 4], c[(k + 3) % 4]))
    for _ in range(RELAX_STEPS):
        moved = {}
        for p, (x, y) in plane.items():
            if p in nbr or math.hypot(*p) < RELAX_FROM:
                continue
            ax = sum(plane[q][0] for q in links[p]) / len(links[p])
            ay = sum(plane[q][1] for q in links[p]) / len(links[p])
            moved[p] = (x + RELAX * (ax - x), y + RELAX * (ay - y))
        plane.update(moved)

    bm = bmesh.new()
    verts = {}

    def vert(p):
        """A pixel corner lifted onto the dome."""
        if p not in verts:
            x, y = plane[p]
            r = min(R_IN, math.hypot(x, y))
            verts[p] = bm.verts.new((x * U, y * U, dome_z(r) * U))
        return verts[p]

    for row, col in cells:
        f = bm.faces.new([vert(p) for p in corners(row, col)])
        rim_pixel = any(grid[row + dr][col + dc] == EDGE_INDEX for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)))
        f.material_index = mat(tone(grid[row][col], rim_pixel))

    # The rim band, then the underside: a rounded bowl, H_BOTTOM deep.
    angles = [math.atan2(y, x) for x, y in loop]
    under = [[bm.verts.new((r * math.cos(a) * U, r * math.sin(a) * U, dome_z(r) * U)) for a in angles]
             for r, _ in RIM_BANDS]
    for phi in (15, 32, 50, 68):
        p = math.radians(phi)
        r = R * math.cos(p)
        under.append([bm.verts.new((r * math.cos(a) * U, r * math.sin(a) * U, -H_BOTTOM * math.sin(p) * U))
                      for a in angles])
    bottom = bm.verts.new((0.0, 0.0, -H_BOTTOM * U))
    chain = [[verts[p] for p in loop]] + under
    n = len(loop)
    for k in range(len(chain) - 1):
        m = mat(RIM_BANDS[k][1] if k < len(RIM_BANDS) else BODY_INDEX)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((chain[k][i], chain[k][j], chain[k + 1][j], chain[k + 1][i])).material_index = m
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((under[-1][j], under[-1][i], bottom)).material_index = mat(BODY_INDEX)
    return [common.mesh_object(NAME, bm, mats, coll, smooth=True)]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objects = orb(sprite)
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    lib.preview(objects, ROOT, NAME, sprite)
    if "--frame-previews" in sys.argv:
        common.render_frame_previews(objects, sys.argv[sys.argv.index("--frame-previews") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
