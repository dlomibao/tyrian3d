"""Glowing red block in a grey clamp (newshs.shp frames 229-235): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.21, 1.5, 1.6, 2.8, 3.15), two of them side by side in the
fortress set (assembly-newshd-127). A big rounded block of glowing red crystal, about 6 px tall
with its face painted from the sprite's pixels, sits in a dark clamp with a grey bracket behind
it. The frames only pulse its glow (every red of the sprite a shade brighter on 231, two on 233,
four on 235), so one model covers them, its colours brightening with the frame
(palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshs-229.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "newshs-229"


def build(sprite):
    coll = common.reset_collection(NAME)
    g = L.Grid(24, 28, sprite["frames"][0]["pixels"])
    m = L.Mats(NAME, sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"])

    # Grey bracket behind (columns 8-15, rows 2-4) and the dark clamp jaws on the flanks.
    L.pillow(bm, L.rect(g, 7.5, 1.6, 16.5, 4.6), 0.0, 0.2, 0.5 * L.U, mat=m.metal(5), top_mat=m.metal(3))
    L.pillow(bm, L.rect(g, 1, 8, 4.5, 19), 0.0, 0.16, 0.5 * L.U, mat=m.metal(3), top_mat=m.metal(2))
    L.pillow(bm, L.rect(g, 18.5, 8, 22, 19), 0.0, 0.16, 0.5 * L.U, mat=m.metal(3), top_mat=m.metal(2))
    L.pillow(bm, L.rect(g, 7.5, 23.5, 16.5, 25.6), 0.0, 0.12, 0.5 * L.U, mat=m.metal(2))
    # The crystal (columns 4-18, rows 4-23): a rounded pillow about 6 px tall. Its colours are
    # those of frame 231 (the frame the fortress set shows), a shade darker on 229 and brighter on
    # 233 and 235 (palette_material frames=).
    def glow(i, part, strength=2.0):
        return m.anim(i, part, {229: i - 1, 233: min(i + 1, 127), 235: min(i + 3, 127)},
                      emission_strength=strength)

    cx, cy, rx, ry, h, power, flat = g.ex(11.5), g.ey(14), 7.6 * L.U, 10.2 * L.U, 0.5, 4.0, 0.45
    L.dome(bm, cx, cy, rx, ry, h, z0=0.0, sides=24, rings=5, mat=glow(115, "crystal", 2.5), power=power, flat=flat)

    def norm(x, y):
        return (abs((x - cx) / rx) ** power + abs((y - cy) / ry) ** power) ** (1 / power)

    def zf(x, y):
        rho = norm(x, y)
        if rho <= flat:
            return h + 0.012
        c = min(1.0, (rho - flat) / (1 - flat))
        return h * (1 - c * c) ** 0.5 + 0.012 + 0.02 * c

    # Its face (the lit rim along the upper left, the swirl in its heart) painted from the sprite's
    # pixels over the part of it inside its edge, which keeps the body's own colour.
    face = next(f for f in sprite["frames"] if f["index"] == 231)["pixels"]
    inner = [[v if 112 <= v <= 127 and all(norm(g.ex(c + dc), g.ey(r + dr)) < 0.93 for dc in (0, 1) for dr in (0, 1))
              else -1 for c, v in enumerate(row)] for r, row in enumerate(face)]
    bins = {112: 113, 113: 113, 119: 119, 120: 119, 121: 121, 122: 121}
    slot = {}

    def slot_of(i):
        b = bins.get(i, i if i <= 118 else 124)
        if b not in slot:
            slot[b] = glow(b, f"face{b}")
        return slot[b]

    L.painted(bm, L.Grid(24, 28, inner), 4, 4, 19, 24, zf, slot_of)
    obj = L.finish(NAME, bm, m, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    L.run(NAME, build, __file__)
