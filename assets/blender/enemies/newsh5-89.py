"""Blue asteroid (newsh5.shp frame 89): a 3D version of its sprite.

Seen in episode 4 (levels 22, 25, 31). A round, cracked blue rock: dark plates split by pale
veins. The model is a floating ball, a full sphere of the sprite's 23 px disc (drawn in a little on
the diagonals, as the sprite's stepped circle is). Its top is a height field over the sprite's own
pixel grid, so from above each pixel is a flat-shaded quad in that pixel's own palette index, with
the darkest plates cut in straight down as pits up to 2 px deep (never above the sphere, so no
raised rims); the sides and the underside carry the sprite's dark navy rim mottling and a mirror
of the top. Matte materials (roughness 1, no specular). One frame.

Run: blender --background --python assets/blender/enemies/newsh5-89.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-89"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


OUTLINE_NAVY = False  # True: the sprite's black outline pixels take the dark navy just inside them
BLUR = 0  # smoothing passes over the pit depths
PIT = 2.0  # depth of a pit under the sprite's darkest pixels, sprite px
SQ = 0.02  # how far the diagonals are drawn in (fraction of the radius)
SQ_POW = 1.5  # how narrow that is round each diagonal
NOTCH = True  # keep the outline's inner step corners off the rim
SMOOTH = False  # flat: every pixel quad shades as one block, so the sheen breaks up into pixels too
RIM_MAX = 53  # brightest palette index on the sides (the band round the equator)
EDGE_MAX = 51  # brightest palette index for the outline pixels on the top cap


def build(sprite):
    coll = common.reset_collection(NAME)
    # Matte, non-metallic stone; no specular sheen (the sprite has none).
    # One material per palette index the sprite uses, so from above every pixel keeps its own shade.
    shades = sorted(int(k) for k in sprite["colors"])
    mats = [common.palette_material(sprite, i, NAME, metallic=0.0, roughness=1.0) for i in shades]
    for m in mats:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.0
    pixels = sprite["frames"][0]["pixels"]
    rows, cols = len(pixels), len(pixels[0])

    def slot(i):
        return min(range(len(shades)), key=lambda k: abs(shades[k] - i))

    def at(c, rr):
        return pixels[rr][c] if 0 <= rr < rows and 0 <= c < cols else -1

    # A floating ball: a full sphere of the sprite's 23 px disc (columns 0-22, rows 2-24, centre
    # column 11, row 13), centred on the ground line so its crest stands 11.5 px up. In sprite px
    # from the centre: u = column - 11 (right), v = 13 - row (up).
    C0, R0 = 11, 13
    R = 11.5
    cx, cy = lib.px(C0), lib.row(R0)

    def pixel_at(u, v):
        return at(int(round(C0 + u)), int(round(R0 - v)))

    def ring_sample(rho, phi):
        """The sprite pixel rho px from the centre at angle phi, stepping inwards past the outline."""
        while rho > 0:
            i = pixel_at(rho * math.cos(phi), rho * math.sin(phi))
            if i >= 0:
                return i
            rho -= 0.5
        return pixel_at(0, 0)

    def interior(c, rr):
        """True when the sprite pixel is at least two pixels inside the disc's outline."""
        return all(at(c + dc, rr + dr) >= 0 for dr in (-2, 0, 2) for dc in (-2, 0, 2))

    def outline(c, rr):
        return any(at(c + dc, rr + dr) < 0 for dr in (-1, 0, 1) for dc in (-1, 0, 1))

    # The top cap is a height field over the sprite's own pixel grid, so from above every pixel is
    # one quad in that pixel's colour: the veins, pits and highlights land where the sprite has
    # them. Its corners: (i, j) is the corner at column i - 0.5, row j - 0.5.
    pix = [(c, rr) for rr in range(rows) for c in range(cols) if pixels[rr][c] >= 0]
    pset = set(pix)
    corners = {}
    for c, rr in pix:
        for i, j in ((c, rr), (c + 1, rr), (c + 1, rr + 1), (c, rr + 1)):
            corners[(i, j)] = (i - 0.5 - C0, R0 - (j - 0.5))

    def is_boundary(i, j):
        return len({(c, rr) for c in (i - 1, i) for rr in (j - 1, j)} & pset) < 4

    def around(i, j):
        return [(c, rr) for c in (i - 1, i) for rr in (j - 1, j) if (c, rr) in pset]

    boundary = sorted((k for k in corners if is_boundary(*k)),
                      key=lambda k: math.atan2(corners[k][1], corners[k][0]))
    # The inner corners of the outline's steps (three of their four pixels filled) stay inside the
    # rim: pulled out to it, they would drag the second-ring pixel behind them into a bright spike
    # down the side. The notch each leaves is filled in the outline's colour.
    rim = [k for k in boundary if not (NOTCH and len(around(*k)) == 3)]
    bphi = [math.atan2(corners[k][1], corners[k][0]) for k in rim]
    brho = [math.hypot(*corners[k]) for k in rim]

    def rho_boundary(phi):
        n = len(bphi)
        for a in range(n):
            p0, p1 = bphi[a], bphi[(a + 1) % n] + (2 * math.pi if a == n - 1 else 0)
            q = phi if phi >= p0 else phi + 2 * math.pi
            if p0 <= q <= p1:
                t = (q - p0) / (p1 - p0)
                return brho[a] + t * (brho[(a + 1) % n] - brho[a])
        return brho[0]

    # The cap's stepped edge is pulled onto the circle at 75 degrees from the pole; the pixels
    # outside 7 px ease out to it, the inner ones keep their places.
    TH_B = math.radians(75)
    RHO_B, KEEP = R * math.sin(TH_B), 7.0

    def warp(k):
        u, v = corners[k]
        rho, phi = math.hypot(u, v), math.atan2(v, u)
        if k in bset:
            rho2 = RHO_B
        elif rho <= KEEP:
            rho2 = rho
        else:
            rho2 = KEEP + (rho - KEEP) * (RHO_B - KEEP) / (rho_boundary(phi) - KEEP)
        return rho2, phi

    bset = set(rim)

    # Dark plates are shallow pits (sprite px, inwards along the radius); everything else sits on
    # the true sphere. A corner sinks by the mean of its four pixels' depths, fading out towards
    # the rim, so the pits are smooth dimples with no raised rims.
    def pdepth(c, rr):
        i = at(c, rr)
        if i < 0 or not interior(c, rr):
            return 0.0
        return -1.0 if i <= 49 else -0.6 if i == 50 else -0.25 if i == 51 else 0.0

    bm = bmesh.new()

    # The sprite's stepped circle is a little flatter on the four diagonals than a true circle
    # (its pixel centres there sit 11.3-11.4 px out): there the outer shell, outside KEEP px, is
    # drawn in by up to SQ (11.5 -> about 11.1 px), easing back to the circle within 22 degrees.
    def squeeze(phi):
        return 1.0 - SQ * max(0.0, math.cos(4 * (phi - math.pi / 4))) ** SQ_POW

    def xy(rho, phi):
        f = 1.0 + (squeeze(phi) - 1.0) * max(0.0, min(1.0, (rho - KEEP) / (R - KEEP)))
        return cx + rho * f * math.cos(phi) / 12, cy + rho * f * math.sin(phi) / 12

    def sphere_pt(rho, phi, sign, depth=0.0):
        # Pits sink straight down, so from above every pixel quad stays where the sprite has it.
        z = math.sqrt(max(R * R - rho * rho, 0.0))
        return (*xy(rho, phi), (sign * z + depth) / 12)

    # Pit depth per corner (never above the sphere, so no raised rims), lightly blurred so the
    # dimples have sloped walls, PIT px deep under the darkest pixels.
    depth = {k: sum(pdepth(c, rr) for c in (k[0] - 1, k[0]) for rr in (k[1] - 1, k[1])) / 4 for k in corners}
    for _ in range(BLUR):
        nxt = {}
        for (i, j), d in depth.items():
            nb = [depth[q] for q in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)) if q in depth]
            nxt[(i, j)] = 0.5 * d + 0.5 * sum(nb) / len(nb)
        depth = nxt
    top, bot = {}, {}
    for k in corners:
        rho, phi = warp(k)
        d = depth[k] * PIT
        nz = math.sqrt(max(R * R - rho * rho, 0.0)) / R
        d *= max(0.0, min(1.0, (nz - 0.35) / 0.3))
        top[k] = bm.verts.new(sphere_pt(rho, phi, 1, d))
        bot[k] = bm.verts.new(sphere_pt(rho, phi, -1))

    def colour_top(c, rr):
        if OUTLINE_NAVY and outline(c, rr):
            u, v = c - C0, R0 - rr
            return min(ring_sample(math.hypot(u, v) - 1.0, math.atan2(v, u)), EDGE_MAX)
        return pixels[rr][c]

    def colour_bottom(c, rr):
        # The underside mirrors the top through the equator, without its two white highlights.
        return min(colour_top(c, rr), 61)

    for c, rr in pix:
        q = [(c, rr), (c + 1, rr), (c + 1, rr + 1), (c, rr + 1)]
        for vs, col, flip in ((top, colour_top(c, rr), False), (bot, colour_bottom(c, rr), True)):
            ring = [vs[k] for k in q]
            if flip:
                ring.reverse()
            bm.faces.new(ring).material_index = slot(col)
    # Fill the notches: each run of inner step corners between two rim corners is one polygon.
    if NOTCH:
        n = len(boundary)
        start = next(a for a in range(n) if boundary[a] in bset)
        run = [boundary[start]]
        for a in range(1, n + 1):
            k = boundary[(start + a) % n]
            run.append(k)
            if k in bset:
                if len(run) > 2:
                    inner = run[1:-1]
                    pxs = {q for c in inner for q in around(*c)}
                    col = min(colour_top(*q) for q in pxs if outline(*q))
                    for vs, colour in ((top, col), (bot, min(col, 61))):
                        bm.faces.new([vs[q] for q in run]).material_index = slot(colour)
                run = [k]
    # Split each pixel quad along its better diagonal: the squeezed quads at the cap's edge would
    # otherwise leave zero-area slivers that shade as dark dots.
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY")

    # The band round the equator, from the top cap's edge (75 degrees) to the bottom cap's (105),
    # in the dark navy of the sprite's second ring rather than its black outline.
    thetas = [math.radians(a) for a in (75, 80, 85, 90, 95, 100, 105)]
    rho_row = [10.0, 9.0, 8.0, 8.0, 9.0, 10.0]
    phis = [warp(k)[1] for k in rim]
    rings = [[top[k] for k in rim]]
    for th in thetas[1:-1]:
        rings.append([bm.verts.new((*xy(R * math.sin(th), p),
                                    R * math.cos(th) / 12)) for p in phis])
    rings.append([bot[k] for k in rim])
    n = len(rim)
    for b in range(len(rings) - 1):
        lower = b >= 3
        rho_s = rho_row[b]
        for a in range(n):
            p0, p1 = phis[a], phis[(a + 1) % n]
            if p1 < p0:
                p1 += 2 * math.pi
            col = ring_sample(rho_s, 0.5 * (p0 + p1))
            v00, v01 = rings[b][a], rings[b][(a + 1) % n]
            v10, v11 = rings[b + 1][a], rings[b + 1][(a + 1) % n]
            for tri in ((v00, v10, v11), (v00, v11, v01)):
                bm.faces.new(tri).material_index = slot(min(col, RIM_MAX))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bad = [e for e in bm.edges if not e.is_manifold]
    if bad:
        raise RuntimeError(f"{len(bad)} non-manifold edges")
    return common.mesh_object(NAME, bm, mats, coll, smooth=SMOOTH)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
