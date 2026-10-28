"""Blue rock wedge (newsh0.shp frame 53): a 3D version of its sprite.

Seen in episode 2 (level 2.12). The bottom-right corner of a mottled blue-steel mass: it fills
the tile's top-left and ends in a long stepped diagonal edge from the top right down to the
bottom left, drawn as a 1 px black outline, with a small dark-grey patch at its top. Its top and
left sides run off the tile (it continues in the sprites next to it), so they are straight walls.

It is a thin flat plate: one flat top about 1 px above the midplane, split into one quad per
sprite pixel (axis-aligned, so the mottling lands exactly where the sprite has it) and coloured
with that pixel's palette index. The black outline pixels along the diagonal are a steep 1 px
bevel between two smooth lines that follow the sprite's stepped edges (the pixels it crosses are
cut along it), so it covers the outline from above without a sawtooth of steps in 3D.

Run: blender --background --python assets/blender/enemies/newsh0-53.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b025 as lib  # noqa: E402
from lib_b025 import common  # noqa: E402

NAME = "newsh0-53"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)
Z_TOP = 2.0 * lib.U  # the flat top, +2 px
Z_BOT = -1.0 * lib.U  # the flat bottom
EDGE_INDEX = 1  # the sprite's black outline
FINISH = (0.0, 0.9)  # metallic, roughness: matte, no specular sheen on the dark-grey patch


def build(sprite):
    coll = common.reset_collection(NAME)
    m = lib.Mats(NAME, sprite["colors"])
    px = sprite["frames"][0]["pixels"]
    rows = [r for r in range(len(px)) if any(v >= 0 for v in px[r])]
    # Per row: e = first black outline column (end of the top), b = end of the sprite.
    e = {r: next((c for c, v in enumerate(px[r]) if v <= EDGE_INDEX), len(px[r])) for r in rows}
    b = {r: max(c for c, v in enumerate(px[r]) if v >= 0) + 1 for r in rows}
    last = rows[-1] + 1
    e[last] = b[last] = 0

    def mat(i):  # matte: the plate reads navy from above, as in the sprite
        return m(i, metallic=FINISH[0], roughness=FINISH[1])

    EDGE = mat(EDGE_INDEX)
    SIDE = mat(52)
    bm = bmesh.new()
    verts = {}

    def v(c, r, top):
        key = (round(c, 5), round(r, 5), top)
        if key not in verts:
            verts[key] = bm.verts.new((G.ex(c), G.ey(r), Z_TOP if top else Z_BOT))
        return verts[key]

    def face(vs, slot):
        f = bm.faces.new(vs)
        f.material_index = slot
        f.smooth = False
        return f

    # The two edges of the black outline, as smooth lines (not the pixel staircase): on each row
    # line, halfway between the rows above and below. `inner` bounds the flat top, `outer` the
    # sprite. Between row lines they run straight.
    def line(ends):
        return {r: (ends[max(r - 1, rows[0])] + ends[r]) / 2 for r in rows + [last]}
    inner, outer = line(e), line(b)

    # Flat top: one axis-aligned quad per sprite pixel, coloured by its own palette index; the
    # pixels the inner line crosses are cut along it.
    def clip_cell(c, r, xa, xb):
        def f(x, y):
            return xa + (xb - xa) * (y - r) - x
        sq = [(c, r + 1), (c + 1, r + 1), (c + 1, r), (c, r)]  # counter-clockwise from above
        out = []
        for p, q in zip(sq, sq[1:] + sq[:1]):
            fp, fq = f(*p), f(*q)
            if fp >= -1e-9:
                out.append(p)
            if (fp > 1e-9 and fq < -1e-9) or (fp < -1e-9 and fq > 1e-9):
                t = fp / (fp - fq)
                out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        return out

    for r in rows:
        xa, xb = inner[r], inner[r + 1]
        for c in range(int(math.ceil(max(xa, xb)))):
            poly = clip_cell(c, r, xa, xb)
            poly = list(dict.fromkeys(v(x, y, True) for x, y in poly))
            if len(poly) >= 3:
                face(poly, mat(px[r][c]))

    # Black outline: a steep bevel from the inner line at the top down to the outer line at the
    # bottom, about 1 px wide from above, covering the sprite's outline pixels.
    def points(ends, top):
        pts = []
        for r in rows:
            xa, xb = ends[r], ends[r + 1]
            pts.append((xa, r))
            lo, hi = sorted((xa, xb))
            ks = [k for k in range(int(math.floor(lo)) + 1, int(math.ceil(hi))) if lo < k < hi]
            for k in sorted(ks, key=lambda k: (k - xa) / (xb - xa)):
                pts.append((k, r + (k - xa) / (xb - xa)))
        pts.append((ends[last], last))
        return pts
    top_edge = points(inner, True)
    bot_edge = points(outer, False)
    if bot_edge[-1][0] > 0:
        bot_edge.append((0, last))
    T = list(dict.fromkeys(v(c, r, True) for c, r in top_edge))
    B = list(dict.fromkeys(v(c, r, False) for c, r in bot_edge))
    ty = [G.row(x.co.y) for x in T]
    by = [G.row(x.co.y) for x in B]
    i = j = 0
    while i < len(T) - 1 or j < len(B) - 1:  # zip the two edges together down the rows
        if j == len(B) - 1 or (i < len(T) - 1 and ty[i + 1] <= by[j + 1]):
            face((T[i], T[i + 1], B[j]), EDGE)
            i += 1
        else:
            face((T[i], B[j + 1], B[j]), EDGE)
            j += 1
    # Top wall (row 0) and left wall (column 0): the rock continues into the next tiles.
    r0 = rows[0]
    face([v(c, r0, True) for c in range(e[r0], -1, -1)] + [v(0, r0, False), v(b[r0], r0, False)], SIDE)
    for r in rows:
        face((v(0, r, True), v(0, r, False), v(0, r + 1, False), v(0, r + 1, True)), SIDE)
    # Flat bottom: the sprite's outline.
    ring = [v(0, r, False) for r in rows] + list(reversed(B))
    face(list(dict.fromkeys(ring)), mat(50))
    return lib.to_object(NAME, bm, m.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], f"enemies/{NAME}", sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite["frames"][0]["image"])


if __name__ == "__main__":
    main()
