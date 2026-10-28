"""The brain's upper half (newsh5.shp 196, 198, 200, an assembly of three pieces): a 3D version of
its sprites.

Seen in episode 4 (level 4.22). Three 2x2 enemies side by side (sprite.json `assemblyLayout`)
make the top of a giant brain, 72 x 24 px: two dark red hemispheres, split by a deep fissure down
the middle, covered in rounded folds (gyri) with dark grooves between them. A long light fold
sweeps from the lower left up towards the fissure; the brightest lumps are along the bottom edge,
where the brain carries on (below the red star, newsh5-278, which other batches model).

Built as a smooth heightfield over the sprite's pixels (a half-pixel lattice, each pixel in its
own palette colour): two lobes domed up to about 13 px, rounding down to the outline (no plinth) and to
about 1 px at the bottom cut, and into a V cleft at the fissure, with the folds raised and the grooves sunk by how
much brighter or darker the blurred sprite is than its surroundings, so the gyri are round tubes
that follow the sprite's own folds. The light flesh's shading normals lean towards straight up so
the folds shade soft rather than dark and glossy. The pieces are built straight from their
own 24 columns (the piece borders are pixel borders) and share the corners and their normals, so
they meet without a step or a shading line. Each piece has one frame.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-198.py [-- --preview out.png]
(the preview is the whole brain top; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b030 as lib  # noqa: E402

NAME = "assembly-newsh5-198"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-196", "newsh5-198", "newsh5-200"]  # left to right
# Origin: the centre of newsh5-198 (screen cx 162, cy -18). Assembly column a = 0..71 runs across
# the three pieces (newsh5-196 is columns 0-23), rows 0-27 are the pieces' rows.
CX0, CY0 = 162, -18
PX = 1 / 12


def X(a):
    """Assembly column (pixel centre; fractions allowed) to Blender X."""
    return (a - 35.5) / 12


def Y(r):
    """Row (pixel centre) to Blender Y."""
    return (13.5 - r) / 12


def sprite_grid(sprites):
    """The three pieces' first frames side by side: 28 rows x 72 assembly columns of palette indices."""
    import numpy as np
    return np.hstack([np.array(d["frames"][0]["pixels"], dtype=int) for d in sprites])


# Heights in sprite px.
DOME = 13.0  # each lobe's crown above the ground
DOME_R = 9.0  # how far in from the outline the lobes round over to their crowns
RIM = 0.4  # the outline's edge
BOTTOM = 0.0  # underside (on the ground: no plinth)
FOLD = 3.0  # px of fold relief per palette step brighter than the surroundings
RELIEF = 3.4  # the most a fold stands out of (or a sulcus sinks into) the dome, px
FINE, BROAD = 1.4, 3.6  # blur radii (px) of the fold relief: the folds' rounding, their surroundings
RELIEF_IN = 2.5  # the folds fade in over this many px from the outline, so the rim rounds over
VMAX = 13  # brighter pixels (the near-white spots) are sheen on the folds, not taller folds
CLEFT = 0.9  # how much of the height the midline fissure cuts away at its centre line
SOFTEN = 0.0  # how far the light flesh's shading normals tilt towards SOFT_DIR (0 = true normals)
SOFT_DIR = (-0.7, -0.25, 1.0)  # the direction the light flesh's normals lean towards: mostly up and a
# little away from the studio light's grey specular lobe, so the folds light salmon rather than grey
SOFT_FROM, SOFT_TO = 2.0, 6.0  # blurred brightness (palette steps over 64) where the softening fades in
RIM_SMOOTH, RIM_SMOOTH_PASSES = 1.5, 3  # px from the outline whose normals are smoothed, and passes
DARK_DIR, DARK_LEAN = (0.6, -0.6, 0.5), 6.0  # where the black fissure's normals lean, and how far
STEEPEN, DARK = 0.0, 4.0  # the dark flesh's shading slopes are steepened by up to 1 + STEEPEN below DARK
CLEFT_W = 1.4  # px: half-width of the fissure's V at the top
EDGE_SOFT = 0.5  # px: how much the distance to the outline is rounded over the outline's pixel steps
BOTTOM_OUT = 0.35  # px beyond the bottom cut where the lobes would reach the ground (the folds roll
# down to about 1 px at the cut rather than ending in a cliff)


# Colours (palette indices): the sprite draws its light into its pixels (a dark outline ring,
# near-white hot spots on the lit side of each fold, dark lower-right halves), and the game lights
# the model and draws its own outline, so the flesh is painted in a few broad tones instead of the
# sprite's per-pixel shading: the folds' crests, their body, and the grooves between them (the game
# has no ambient occlusion, so the sulci keep a darker red for their depth). The fissure's black
# stays: it is a cut, not shading.
TONE_CREST, TONE_MID, TONE_GROOVE, FISSURE = 72, 70, 68, 1
CREST_AT, GROOVE_AT = 1.2, -1.0  # palette steps of fold relief (fine minus broad blur) per tone


def tone_grid(grid):
    """The palette index each pixel is painted with: a broad tone from its fold relief (the blurred
    sprite's brightness against its surroundings), the outline ring in the body tone, the fissure
    black."""
    import numpy as np
    H, W = grid.shape
    inside = grid != -1
    rr, cc = np.mgrid[0:H, 0:W]
    iy, ix = np.nonzero(inside)
    v = np.clip(grid - 64, 0, VMAX).astype(float)[iy, ix]
    d2 = (iy[:, None] - iy[None, :]) ** 2 + (ix[:, None] - ix[None, :]) ** 2

    def blur(sigma):
        w = np.exp(-0.5 * d2 / sigma ** 2)
        return (w * v[None, :]).sum(1) / w.sum(1)

    relief = blur(FINE) - blur(BROAD)
    out = np.full((H, W), -1, dtype=int)
    tone = np.where(relief > CREST_AT, TONE_CREST, np.where(relief < GROOVE_AT, TONE_GROOVE, TONE_MID))
    out[iy, ix] = tone
    # the outline ring: the game draws the outline, so it takes the body tone rather than the
    # sprite's near-black
    out[tone_grid_ring(grid)] = TONE_MID
    fiss = (grid == 1) & (cc >= 33) & (cc <= 39) & (rr >= 9)
    out[fiss] = FISSURE
    return out


def tone_grid_ring(grid):
    """The inside pixels touching the outside (the bottom cut aside): the sprite's outline ring."""
    import numpy as np
    H, W = grid.shape
    inside = grid != -1
    pad = np.ones((H + 2, W + 2), dtype=bool)
    pad[1:-1, 1:-1] = ~inside
    pad[-1, :] = False  # the bottom cut is not an outline
    ring = np.zeros((H, W), dtype=bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ring |= pad[1 + dy:H + 1 + dy, 1 + dx:W + 1 + dx]
    return inside & ring


def tone_at(grid, py, px):
    """Broad tone (palette index) at points (py, px) in pixel units, from the fold relief there, so
    the tones' borders follow the folds' smooth curves rather than the pixel steps."""
    import numpy as np
    iy, ix = np.nonzero(grid != -1)
    v = np.clip(grid - 64, 0, VMAX).astype(float)[iy, ix]
    out = np.empty(len(py), dtype=int)
    for s0 in range(0, len(py), 2000):
        y, x = py[s0:s0 + 2000], px[s0:s0 + 2000]
        d2 = (y[:, None] - (iy + 0.5)[None, :]) ** 2 + (x[:, None] - (ix + 0.5)[None, :]) ** 2

        def blur(sigma):
            w = np.exp(-0.5 * d2 / sigma ** 2)
            return (w * v[None, :]).sum(1) / w.sum(1)

        relief = blur(FINE) - blur(BROAD)
        out[s0:s0 + 2000] = np.where(relief > CREST_AT, TONE_CREST,
                                     np.where(relief < GROOVE_AT, TONE_GROOVE, TONE_MID))
    return out


def _box_dist(py, px, oy, ox):
    """Distance (px) from points (py, px) to the unit squares centred on (oy, ox): (points x squares)."""
    import numpy as np
    dy = np.maximum(np.abs(py[:, None] - oy[None, :]) - 0.5, 0)
    dx = np.maximum(np.abs(px[:, None] - ox[None, :]) - 0.5, 0)
    return np.sqrt(dy * dy + dx * dx)


def field(grid, py, px):
    """Heights (px) at points (py, px) in pixel units (pixel (r, c) spans rows r..r+1, columns
    c..c+1): two domed lobes rounding down to the outline and into the midline fissure, with the
    gyri standing out of the sulci by how much brighter they are than their surroundings. The
    relief is a continuous Gaussian blur of the sprite's brightness, so each fold is a smooth,
    round-crested tube rather than a per-pixel spike. Returns (heights, blurred brightness in
    palette steps above the darkest flesh)."""
    import numpy as np
    H, W = grid.shape
    inside = grid != -1
    rr, cc = np.mgrid[0:H, 0:W]
    # the outline: transparent pixels, and a transparent border left, right and above (the bottom
    # edge is a cut where the brain carries on)
    pad = np.full((H + 1, W + 2), True)
    pad[1:, 1:-1] = ~inside
    oy, ox = np.nonzero(pad)
    # a soft minimum of the distances to the outside pixels' centres, so the outline's pixel steps
    # don't crease the slope (a hard minimum leaves a ridge or a notch at every step)
    do = np.sqrt((py[:, None] - (oy - 0.5)[None, :]) ** 2 + (px[:, None] - (ox - 0.5)[None, :]) ** 2)
    dmin = do.min(1)
    d_edge = dmin - EDGE_SOFT * np.log(np.exp(-(do - dmin[:, None]) / EDGE_SOFT).sum(1)) - 0.5
    d_edge = np.maximum(d_edge, 0)
    d_edge = np.minimum(d_edge, (H - py) + BOTTOM_OUT)
    # the fissure: the black pixels inside the brain, below its top notch
    fiss = (grid == 1) & (cc >= 33) & (cc <= 39) & (rr >= 9)
    fy, fx = np.nonzero(fiss)
    d_fiss = _box_dist(py, px, fy + 0.5, fx + 0.5).min(1)
    t = np.clip(d_edge / DOME_R, 0, 1)
    # the lobes round over from the outline to their crowns with a finite slope (no wall)
    dome = RIM + (DOME - RIM) * np.sin(0.5 * np.pi * t)
    ft = np.clip(d_fiss / 6.0, 0, 1)
    dome *= 0.62 + 0.38 * np.sqrt(1 - (1 - ft) ** 2)  # the lobes round down into the fissure
    # folds: brightness relative to the surroundings, blurred continuously over the inside pixels
    iy, ix = np.nonzero(inside)
    v = np.clip(grid - 64, 0, VMAX).astype(float)[iy, ix]
    d2 = (py[:, None] - (iy + 0.5)[None, :]) ** 2 + (px[:, None] - (ix + 0.5)[None, :]) ** 2

    def blur(sigma):
        w = np.exp(-0.5 * d2 / sigma ** 2)
        return (w * v).sum(1) / np.maximum(w.sum(1), 1e-9)

    fine = blur(FINE)
    relief = RELIEF * np.tanh(FOLD * (fine - blur(BROAD)) / RELIEF)
    s = np.clip(d_edge / RELIEF_IN, 0, 1)
    relief *= s * s * (3 - 2 * s)
    h = dome + relief
    # the cleft: a V down the fissure pixels' centre line, so its black pixels face sideways
    d_fc = np.sqrt((py[:, None] - (fy + 0.5)[None, :]) ** 2 + (px[:, None] - (fx + 0.5)[None, :]) ** 2).min(1)
    h *= 1 - CLEFT * np.clip(1 - d_fc / CLEFT_W, 0, 1)
    return np.maximum(h, 0.3), fine, d_edge


class Brain:
    """A heightfield over the sprite's pixels on a half-pixel lattice: each pixel a fan of 8
    triangles around its centre (through its corners and edge midpoints) in the pixel's own
    palette colour, smooth-shaded, with low walls down to the ground along the outline. The pieces
    are built straight from their own columns (the piece borders are pixel borders), sharing the
    lattice points and their normals, so they meet without a step or a shading line."""

    def __init__(self, sprite, grid):
        import numpy as np
        self.grid = grid
        H, W = self.H, self.W = grid.shape
        self.inside = grid != -1
        tag = "nsh5brain"
        self.paint = tone_grid(grid)
        order = [TONE_MID, TONE_CREST, TONE_GROOVE, FISSURE]  # material 0 is the body flesh
        # soft, matte flesh (organic: non-metallic and rough, so the folds' highlights are lit
        # faces of their real shape, not sheen); the fissure's black is rougher still, no streak
        self.mats = [common.palette_material(sprite, i, tag, metallic=0.0,
                                             roughness=0.9 if i == FISSURE else 0.7)
                     for i in order]
        self.mat_of = {i: k for k, i in enumerate(order)}
        # each fan triangle's tone from the relief at its centroid (pixels in the outline ring and
        # the fissure keep their one colour)
        import numpy as np
        cents = []
        for r, c in np.argwhere(self.inside):
            for tri in self.fans(r, c):
                cents.append([sum(k[1] for k in tri) / 6, sum(k[2] for k in tri) / 6])
        cents = np.array(cents)
        tri_tone = tone_at(grid, cents[:, 0], cents[:, 1])
        self.tri_tone = {}
        ring = tone_grid_ring(grid)
        for i, (r, c) in enumerate(np.argwhere(self.inside)):
            fixed = self.paint[r, c] == FISSURE or ring[r, c]
            self.tri_tone[int(r), int(c)] = ([int(self.paint[r, c])] * 8 if fixed
                                             else [int(t) for t in tri_tone[8 * i:8 * i + 8]])
        # the outline's sides, the bottom cut and piece ends: the body tone (the game draws the outline)
        self.WALL = self.CUT = self.mat_of[TONE_MID]

        # lattice points (a, b) at pixel coordinates (a / 2, b / 2) that touch an inside pixel
        pts = set()
        for r, c in np.argwhere(self.inside):
            for a in range(2 * r, 2 * r + 3):
                for b in range(2 * c, 2 * c + 3):
                    pts.add((a, b))
        pts = sorted(pts)
        lxy = {(a, b): [X(b / 2 - 0.5), Y(a / 2 - 0.5)] for a, b in pts}
        # soften the outline's pixel steps: relax each outline corner towards its two neighbours
        # along the outline (not along the bottom cut), then put the edge midpoints between them
        links = {}
        mids = {}
        for r, c in np.argwhere(self.inside):
            for (dr, dc), (a, b) in self.SIDES(r, c):
                if r + dr < H and not self.ins(r + dr, c + dc):
                    ka, kb = (2 * a[0], 2 * a[1]), (2 * b[0], 2 * b[1])
                    links.setdefault(ka, []).append(kb)
                    links.setdefault(kb, []).append(ka)
                    mids[((ka[0] + kb[0]) // 2, (ka[1] + kb[1]) // 2)] = (ka, kb)
        for _ in range(2):
            new = {}
            for k, nb in links.items():
                if len(nb) == 2 and k[0] < 2 * H:
                    (x0, y0), (x1, y1), (x2, y2) = lxy[k], lxy[nb[0]], lxy[nb[1]]
                    new[k] = [0.5 * x0 + 0.25 * (x1 + x2), 0.5 * y0 + 0.25 * (y1 + y2)]
            lxy.update(new)
        for m, (ka, kb) in mids.items():
            lxy[m] = [0.5 * (lxy[ka][0] + lxy[kb][0]), 0.5 * (lxy[ka][1] + lxy[kb][1])]
        # heights (and normals) from the field at the points' final positions, so the relaxed
        # outline corners don't leave a notch or a bump at every pixel step
        py = np.array([14 - 12 * lxy[k][1] for k in pts])
        px = np.array([36 + 12 * lxy[k][0] for k in pts])
        hz, bright, dedge = field(grid, py, px)
        lh = {k: float(z) for k, z in zip(pts, hz)}
        for k in list(links) + list(mids):  # the outline itself stays at the rim, so its wall is even
            if k[0] < 2 * H:
                lh[k] = RIM
        self.soft = {("t", *k): SOFTEN * min(max((b - SOFT_FROM) / (SOFT_TO - SOFT_FROM), 0), 1)
                     for k, b in zip(pts, bright)}
        self.steep = {("t", *k): 1 + STEEPEN * min(max((DARK - b) / DARK, 0), 1) for k, b in zip(pts, bright)}
        # the black fissure: its normals lean towards a direction the light leaves dark (away from
        # the upper-left key), so it reads as a clean dark line from above and from the game camera
        # instead of a speckled band with a glossy streak
        rr, cc = np.mgrid[0:H, 0:self.W]
        fy, fx = np.nonzero((grid == 1) & (cc >= 33) & (cc <= 39) & (rr >= 9))
        d_fc = np.sqrt((py[:, None] - (fy + 0.5)[None, :]) ** 2 + (px[:, None] - (fx + 0.5)[None, :]) ** 2).min(1)
        self.shade = {("t", *k): DARK_LEAN * min(max((1.6 - df) / 0.8, 0), 1) for k, df in zip(pts, d_fc)}
        self.lh, self.lxy = lh, lxy
        self.normals = self.top_normals(grid, py, px, pts)
        # smooth the normals over the last px or two at the outline (lattice neighbours, a few
        # passes): the steepened rim's normals otherwise alternate from point to point along the
        # stepped outline and shade as a saw-tooth of glints at the rim's foot
        near = {("t", *k) for k, de in zip(pts, dedge) if de < RIM_SMOOTH}
        for _ in range(RIM_SMOOTH_PASSES):
            new = {}
            for t in near:
                _, a, b = t
                nb = [self.normals[n] for n in (("t", a + 1, b), ("t", a - 1, b), ("t", a, b + 1), ("t", a, b - 1))
                      if n in self.normals]
                v = self.normals[t] * 2
                for n in nb:
                    v = v + n
                new[t] = v.normalized()
            self.normals.update(new)

    def ins(self, r, c):
        return 0 <= r < self.H and 0 <= c < self.W and bool(self.inside[r, c])

    @staticmethod
    def SIDES(r, c):
        """A pixel's four sides: (neighbour offset, (corner a, corner b)) wound so that a wall
        (top a, top b, low b, low a) faces out. Corners are (row, column) of the pixel grid."""
        return (((-1, 0), ((r, c + 1), (r, c))), ((1, 0), ((r + 1, c), (r + 1, c + 1))),
                ((0, -1), ((r, c), (r + 1, c))), ((0, 1), ((r + 1, c + 1), (r, c + 1))))

    def co(self, key):
        """Position of a vertex key: ('t', a, b) a top lattice point, ('l', a, b) the same point on
        the underside."""
        kind, a, b = key
        x, y = self.lxy[a, b]
        return (x, y, (self.lh[a, b] if kind == "t" else BOTTOM) / 12)

    @staticmethod
    def fans(r, c):
        a, b = 2 * r, 2 * c
        # anticlockwise from above (rows run down the screen, so +a is -Y)
        ring = [(a, b), (a + 1, b), (a + 2, b), (a + 2, b + 1), (a + 2, b + 2), (a + 1, b + 2),
                (a, b + 2), (a, b + 1)]
        ring = [("t", *k) for k in ring]
        m = ("t", a + 1, b + 1)
        return [(m, ring[i], ring[(i + 1) % 8]) for i in range(8)]

    def top_normals(self, grid, py, px, pts):
        """Smooth normal of every top vertex, from the height field's own gradient (so the steep rim
        and the folds shade evenly, without the triangles' facets)."""
        from mathutils import Vector
        import numpy as np
        e = 0.25  # px
        h0, _, d0 = field(grid, py, px)

        def slope(dy, dx):
            # central differences inside; on the outline (where the outside is clamped flat) the
            # steeper one-sided difference, so the rim's normals lean out like the slope behind them
            fwd = (field(grid, py + dy, px + dx)[0] - h0) / e
            bwd = (h0 - field(grid, py - dy, px - dx)[0]) / e
            one = np.where(np.abs(fwd) > np.abs(bwd), fwd, bwd)
            return np.where(d0 < 0.75, one, 0.5 * (fwd + bwd))

        gx, gy = slope(0, e), slope(e, 0)
        # rows run down the screen (-Y), so a height rising with the row tilts the normal to +Y
        # soften the shading of the light flesh: tilt its normals part way to straight up, so the
        # gyri shade like the sprite's soft pink folds (lighter, gentler) while the geometry keeps
        # its full relief; the dark grooves and the outline keep their true, steep normals
        # and the near-black outline and grooves shade steeper than they are (their slopes face
        # sideways), so they stay dark from above rather than catching the light
        out = {}
        for k, dx, dy in zip(pts, gx, gy):
            t = ("t", *k)
            m = self.steep[t]
            out[t] = (Vector((-dx * m, dy * m, 1)).normalized() + Vector(SOFT_DIR) * self.soft[t]
                      + Vector(DARK_DIR).normalized() * self.shade[t]).normalized()
        return out

    def pixels(self, c0, c1):
        import numpy as np
        return [(int(r), int(c)) for r, c in np.argwhere(self.inside) if c0 <= c < c1]

    def piece(self, name, c0, c1, offset, coll):
        """The piece made of columns c0..c1-1, moved so `offset` (its centre) is the origin."""
        from mathutils import Vector
        bm = bmesh.new()
        verts, keys = {}, []
        off = Vector(offset)

        def v(key):
            if key not in verts:
                verts[key] = bm.verts.new(Vector(self.co(key)) - off)
                keys.append(key)
            return verts[key]

        for r, c in self.pixels(c0, c1):
            for tri, tone in zip(self.fans(r, c), self.tri_tone[r, c]):
                f = bm.faces.new([v(k) for k in tri])
                f.material_index, f.smooth = self.mat_of[tone], True
            for (dr, dc), (a, b) in self.SIDES(r, c):
                rr, cc = r + dr, c + dc
                seam = not c0 <= cc < c1 and self.ins(rr, cc)
                if self.ins(rr, cc) and not seam:
                    continue
                ka, kb = (2 * a[0], 2 * a[1]), (2 * b[0], 2 * b[1])
                km = ((ka[0] + kb[0]) // 2, (ka[1] + kb[1]) // 2)
                f = bm.faces.new((v(("t", *ka)), v(("t", *km)), v(("t", *kb)), v(("l", *kb)), v(("l", *ka))))
                cut = rr == self.H or seam
                f.material_index = self.CUT if cut else self.WALL
                f.smooth = False  # flat: the 0.4 px outline wall (smooth, it caught glints at the rim's foot)
        # underside: one face
        low = {verts[k] for k in verts if k[0] == "l"}
        bmesh.ops.contextual_create(bm, geom=[e for e in bm.edges if all(x in low for x in e.verts)
                                              and len(e.link_faces) == 1])
        for f in bm.faces:
            if all(x in low for x in f.verts):
                f.material_index, f.smooth = self.WALL, False
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
        obj = lib.to_object(name, bm, self.mats, coll)
        # custom normals: smooth faces take the whole brain's normals (an outline wall the normal of
        # the rim point above), flat faces their own
        me = obj.data
        loops = []
        for p in me.polygons:
            for li in p.loop_indices:
                k = keys[me.loops[li].vertex_index]
                loops.append(self.normals["t", k[1], k[2]] if p.use_smooth else p.normal.copy())
        me.normals_split_custom_set(loops)
        return obj


def merged_sprite():
    """newsh5-198's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh5-198")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(out):
    """The three pieces' sprites as one 72 x 84 image centred on newsh5-198's centre (the shape
    render_preview expects for size 6)."""
    import numpy as np
    img = np.zeros((84, 72, 4), dtype=np.float32)
    for i, name in enumerate(PIECES):
        data = common.load_sprite(ROOT, name)
        for r, rw in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(rw):
                if v >= 0:
                    img[28 + r, 24 * i + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 72, 84, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    grid = sprite_grid([common.load_sprite(ROOT, n) for n in PIECES])
    brain = Brain(sprite, grid)
    coll = common.reset_collection(NAME)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = {}
    for name, cx, cy in layout:
        c0 = 24 * PIECES.index(name)
        pieces[name] = brain.piece(name, c0, c0 + 24, (cx / 12, -cy / 12, 0), coll)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        # the whole top as cut: the pieces put back in place
        for name, cx, cy in layout:
            pieces[name].location = (cx / 12, -cy / 12, 0)
        common.render_preview([pieces[n] for n in PIECES], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            pieces[name].location = (0, 0, 0)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
