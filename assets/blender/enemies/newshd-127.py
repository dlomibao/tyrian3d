"""Grey pod with two red lamps (newshd.shp frames 127, 129, 131): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.6, 2.8, 3.15), in a row of six along the top of the fortress set
(assembly-newshd-127; the pieces repeat, so each is modelled on its own). A wide oval grey metal
pod domes up from the stone floor; a pale plate runs down its middle, its rim standing proud
round a slot cut into the dome that holds two red lamps. The frames only brighten the lamps, so
one model covers them all, the lamps' colour following the frame (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshd-127.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "newshd-127"


def build(sprite):
    coll = common.reset_collection(NAME)
    g = L.Grid(24, 28, sprite["frames"][0]["pixels"])
    m = L.Mats(NAME, sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"])

    # The oval pod: columns 2-22, rows 4-22, a dome about 9 px tall (round in the sprite: a bright
    # upper-left rim, a dark lower-right edge), its seam darker round the bottom. Built as
    # half-ellipse sections along X so the pale plate down its middle (columns 8-15) can stand
    # proud as a rim (columns 8 and 15) round a slot cut into the dome (columns 9-14).
    cx, cy, rx, ry, h, z0 = g.x(11.6), g.y(13.4), 10.4 * L.U, 9.2 * L.U, 0.78, L.FLOOR - 0.01
    RIM, SLOT = 0.8 * L.U, -1.6 * L.U  # the plate's rim above the dome, its slot below

    def surface(x, y, d=0.0):
        """Top of the pod at (x, y), raised by d (the rim / slot offset)."""
        s = max(0.0, 1 - ((x - cx) / rx) ** 2) ** 0.5
        w = ry * s
        if w <= 1e-6:
            return z0
        c = max(-1.0, min(1.0, (y - cy) / w))
        return z0 + max(0.0, h * s + d) * (1 - c * c) ** 0.5

    def section(x, d=0.0, n=12):
        s = max(0.0, 1 - ((x - cx) / rx) ** 2) ** 0.5
        if s < 1e-4:
            return [(x, cy, z0)]
        w, top = ry * s, max(0.0, h * s + d)
        return [(x, cy + w * math.cos(math.pi * k / n), z0 + top * math.sin(math.pi * k / n)) for k in range(n + 1)]

    # Polished grey metal: one mid-tone per part, the lights make the sprite's bright upper-left
    # rim and dark lower-right edge (and the game draws the dark outline round the bottom).
    DOME, PLATE, RIB = (m(i, metallic=0.75, roughness=0.3) for i in (9, 12, 11))
    xl, xr = cx - rx, cx + rx
    a, b, c_, e = g.ex(8), g.ex(9), g.ex(15), g.ex(16)
    left = [xl] + [cx - rx * u for u in (0.97, 0.9, 0.78, 0.62)] + [a]
    right = [e] + [cx + rx * u for u in (0.62, 0.78, 0.9, 0.97)] + [xr]
    L.ring_loft(bm, [section(x) for x in left], mat=DOME, smooth=True, cap_start=False, cap_end=False)
    L.ring_loft(bm, [section(x) for x in right], mat=DOME, smooth=True, cap_start=False, cap_end=False)
    plate = [section(a), section(a, RIM), section(b, RIM), section(b, SLOT)]
    plate += [section(x, SLOT) for x in (g.ex(11), g.ex(13))]
    plate += [section(c_, SLOT), section(c_, RIM), section(e, RIM), section(e)]
    L.ring_loft(bm, plate, mat=PLATE, cap_start=False, cap_end=False)
    L.dome(bm, cx, cy, 10.6 * L.U, 9.4 * L.U, 0.07, z0=L.FLOOR - 0.01, sides=24, rings=1, mat=DOME,
           power=2.2, flat=0.9)
    # Ribs across the pod either side of the plate (light grey at columns 4-6 and 17-19), on its
    # surface.
    for c0, c1 in ((3.2, 7.6), (16.0, 20.4)):
        for r in (9.3, 17.6):
            pts = [(g.x(c), g.y(r), surface(g.x(c), g.y(r))) for c in (c0, (c0 + c1) / 2, c1)]
            L.tube(bm, pts, 0.6 * L.U, sides=6, mat=RIB, flat=0.7)

    # Two red lamps in the slot (columns 10-13, rows 9-12 and 15-18): a dark ring round a bright
    # core, both brightening from red (127) through orange (129) to yellow-orange (131).
    ring = m.anim(112, "lampring", {129: 115, 131: 118}, emission_strength=1.0)
    lamp = m.anim(118, "lamp", {129: 121, 131: 123}, emission_strength=3.0)
    for r in (11.0, 17.0):
        x, y = g.ex(12), g.ey(r)
        zs = surface(x, y, SLOT)
        L.dome(bm, x, y, 2.0 * L.U, 2.0 * L.U, 0.05, z0=zs - 0.02, sides=12, rings=1, mat=ring, flat=0.75)
        L.dome(bm, x, y, 1.3 * L.U, 1.3 * L.U, 0.17, z0=zs - 0.03, sides=12, rings=3, mat=lamp)
    obj = L.finish(NAME, bm, m, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    L.run(NAME, build, __file__)
