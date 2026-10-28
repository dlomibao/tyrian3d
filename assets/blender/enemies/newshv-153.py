"""Blue faceted orb (newshv.shp frames 153, 155, 157): a 3D version of its sprite.

Seen in episode 2 (level 2.15). The sprite is shaded as an orb (a bright centre fading to a
near-black rim), with a speckled diamond pattern on its surface: a pale outer diamond band whose
corners nearly reach the rim, mid-dark navy spots at the corners of an inner diamond, pale speckles
running out along the diagonals (brightest at the lower-right), and a soft white highlight in the
middle. So the model is a tall dome (top ~8.5 px above the midplane on an ~19 px wide body) over a
rounded underside, and the pattern is painted on the dome: the top surface is a fine polar mesh
whose every face takes the palette index of the sprite pixel under it, so the speckles and the
diamond come straight from the sprite. The surface itself stays one smooth curve (no per-pixel
lumps): the only relief is a soft ~0.4 px ridge along the pale diamond band (|x| + |y| = 7 px in the
sprite, its corners rounded) and a low round swell at the apex under the white centre, never a frame
or a stud. The rim band is the sprite's near-black navy outline, matte so it doesn't ring with gloss. The three frames only dim the whole
orb (a pulse), so one model covers them, its colours stepping darker frame by frame. newshv-123 is
the same disc in red (still built by lib_b003.gem_disc).

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
RIM_INDEX = 50      # the rim band (the sprite's outline pixels) and the underside's first band
UNDER_INDEX = 53    # the rest of the underside
EDGE_INDEX = 48     # the sprite's near-black outline pixels: modelled as the rim band instead
R_IN = 8.4          # where the pixel grid meets the rim band (the outline pixels are ~1 px wide)
# The rim band from R_IN out to R, as (outer radius px, palette index): it darkens to the navy
# edge like the sprite's last pixels, so the orb's steep side isn't one tall black skirt.
RELAX_FROM, RELAX, RELAX_STEPS = 6.0, 0.5, 3   # relaxing the pixel corners near the rim (px, weight, passes)
RIM_BANDS = [(8.8, 50), (9.15, 49), (R, 48)]
RIM_ROUGHNESS = 0.85      # the rim and underside are matte: no gloss ring round the orb's edge
DIAMOND_L1 = 7.0          # the pale diamond band's centre line, |x| + |y| in px (the sprite's brightest ring)
DIAMOND_RIDGE = 0.4       # its ridge height, px
DIAMOND_WIDTH = 1.0       # its half-width (gaussian), px
DIAMOND_ROUND = 1.5       # how much the diamond's corners are rounded, px
APEX_SWELL = 0.3          # the white centre's low swell at the apex, px
APEX_WIDTH = 2.2          # its radius (gaussian), px
RELIEF_FADE = (7.6, 8.8)  # relief fades out between these radii so the rim stays a clean circle


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


def relief(field, x, y):
    """Smooth relief (px) at (x, y): a soft ridge along the pale diamond and a swell at the apex.
    Both are smooth functions of position, so neighbouring pixels never step against each other."""
    r = math.hypot(x, y)
    lo, hi = RELIEF_FADE
    fade = 1.0 if r <= lo else max(0.0, (hi - r) / (hi - lo))
    k = DIAMOND_ROUND
    l1 = math.sqrt(x * x + k * k) + math.sqrt(y * y + k * k) - 2 * k   # |x| + |y|, corners rounded
    ridge = DIAMOND_RIDGE * math.exp(-((l1 - DIAMOND_L1) / DIAMOND_WIDTH) ** 2)
    swell = APEX_SWELL * math.exp(-(r / APEX_WIDTH) ** 2)
    return fade * ridge + swell


def orb(sprite):
    import bmesh
    coll = common.reset_collection(NAME)
    f1, f2 = (f["index"] for f in sprite["frames"][1:3])
    field = SpriteField(sprite["frames"][0])

    mats, slot = [], {}

    def mat(i, rim=False):
        """Material slot for palette index i, dimming on the pulse frames like the sprite; the rim
        and underside get matte copies."""
        if (i, rim) not in slot:
            slot[(i, rim)] = len(mats)
            mats.append(common.palette_material(
                sprite, i, f"{NAME}-{'rim' if rim else 'pulse'}", frames={f1: max(48, i - 2), f2: max(48, i - 4)},
                metallic=0.0 if rim else 0.2, roughness=RIM_ROUGHNESS if rim else 0.4,
                emission_strength=1.2 if i == 63 else 0.0))
        return slot[(i, rim)]

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
        """A pixel corner lifted onto the dome (plus the smooth relief)."""
        if p not in verts:
            x, y = plane[p]
            r = min(R_IN, math.hypot(x, y))
            lift = 0.0 if p in nbr else relief(field, p[0], p[1])
            verts[p] = bm.verts.new((x * U, y * U, (dome_z(r) + lift) * U))
        return verts[p]

    for row, col in cells:
        f = bm.faces.new([vert(p) for p in corners(row, col)])
        i = grid[row][col]
        f.material_index = mat(i)

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
        m = mat(RIM_BANDS[k][1] if k < len(RIM_BANDS) else RIM_INDEX if k == len(RIM_BANDS) else UNDER_INDEX, rim=True)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((chain[k][i], chain[k][j], chain[k + 1][j], chain[k + 1][i])).material_index = m
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((under[-1][j], under[-1][i], bottom)).material_index = mat(UNDER_INDEX, rim=True)
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
