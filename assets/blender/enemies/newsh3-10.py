"""Twin-claw jet (newsh3.shp frames 10, 48): a 3D version of its sprite.

Seen in episode 4 (levels 2, 6, 10). Two curved steel claws, one above and one below, sweep to
points on the right from a short upright post on the left; between them a jet of fire blasts out
to the right (and a little flame leaks out to the left). The claws are lofted column by column
from the sprite, thick at the root and thin at the tips, with the sprite's greys painted on. The
two frames only flicker the flame, so one model covers both; the flame glows.

Run: blender --background --python assets/blender/enemies/newsh3-10.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common, ex, ey  # noqa: E402

NAME = "newsh3-10"


def smooth(values, n=2):
    out = list(values)
    for _ in range(n):
        out = [out[0]] + [(out[i - 1] + 2 * out[i] + out[i + 1]) / 4 for i in range(1, len(out) - 1)] + [out[-1]]
    return out


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.25, roughness=0.5),  # 0 dark steel
        pal(8, metallic=0.25, roughness=0.45),  # 1 mid steel
        pal(11, metallic=0.3, roughness=0.35),  # 2 light steel
        pal(118, roughness=0.5, emission_strength=3.0),  # 3 red flame
        pal(121, roughness=0.4, emission_strength=4.0),  # 4 orange flame
        pal(123, roughness=0.3, emission_strength=5.0),  # 5 yellow core
    ]
    DARK, MID, LIGHT, RED, ORANGE, YELLOW = range(6)
    pixels = sprite["frames"][0]["pixels"]

    def slot(v):
        if v < 2 or v > 14:
            return None
        if v <= 4:
            return DARK
        if v <= 8:
            return MID
        return LIGHT

    bm = bmesh.new()

    def claw(rows):
        """Loft a claw along X from the per-column extents of its grey pixels in `rows`."""
        ext = lib.col_extents(pixels, lambda v, r: 2 <= v <= 14 and rows[0] <= r <= rows[1])
        cols = sorted(ext)
        mids = smooth([(ext[c][0] + ext[c][1]) / 2 for c in cols])
        halfs = smooth([(ext[c][1] - ext[c][0]) / 2 + 0.25 for c in cols])
        secs = [(ex(cols[0] - 0.1), -ey(mids[0]), 0.0, 0.0, 0.0)]
        for c, m, hw in zip(cols, mids, halfs):
            hw /= 12
            hh = min(0.11, 0.07 + hw * 0.25) if c < 18 else max(0.03, hw * 0.8)
            secs.append((ex(c + 0.5), -ey(m), hw, hh, 0.0))
        secs.append((ex(cols[-1] + 1.1), -ey(mids[-1]), 0.0, 0.0, 0.0))
        start, f0 = len(bm.verts), len(bm.faces)
        lib.loft2(bm, secs, sides=10, mat_index=MID, power=0.85)
        lib.rotate_new(bm, start, -math.pi / 2)
        bm.faces.ensure_lookup_table()
        lib.paint_faces(bm, bm.faces[f0:], pixels, slot, under_slot=DARK, min_nz=-0.2)

    claw((3, 10))
    claw((16, 23))

    # The upright post joining the claws (column 4, rows 9-17), light down its front.
    f0 = len(bm.faces)
    lib.loft2(bm, [(ey(17.5), ex(4.5), 0.0, 0.0, 0.0), (ey(17), ex(4.5), 1.4 / 12, 0.08, 0.0),
                   (ey(13.5), ex(4.5), 1.2 / 12, 0.07, 0.0), (ey(10), ex(4.5), 1.4 / 12, 0.08, 0.0),
                   (ey(9.5), ex(4.5), 0.0, 0.0, 0.0)], sides=8, mat_index=DARK)
    lib.loft2(bm, [(ey(16.5), ex(4.5), 0.0, 0.0, 0.05), (ey(15.5), ex(4.5), 0.45 / 12, 0.03, 0.06),
                   (ey(11.5), ex(4.5), 0.45 / 12, 0.03, 0.06), (ey(10.5), ex(4.5), 0.0, 0.0, 0.05)],
              sides=6, mat_index=LIGHT)

    # The jet: red flame from column 6 to 19 round row 13 with an orange-yellow core near its root,
    # and a short flame out of the left side (columns 0-2).
    yc = ey(13.5)
    jet = [(6.0, 0.0, 0.0), (6.6, 1.0, 0.05), (8.5, 1.9, 0.08), (11.5, 2.0, 0.08), (14.5, 1.6, 0.07),
           (17.5, 1.0, 0.05), (19.6, 0.0, 0.0)]
    start = len(bm.verts)
    lib.loft2(bm, [(ex(c), -yc, w / 12, hh, 0.0) for c, w, hh in jet], sides=10, mat_index=RED,
              wobble=lambda a, y: 1.0 + 0.06 * math.cos(5 * a + y * 20))
    core = [(7.0, 0.0, 0.0), (7.8, 1.1, 0.08), (10.0, 1.5, 0.1), (12.5, 1.2, 0.095), (15.0, 0.0, 0.0)]
    lib.loft2(bm, [(ex(c), -yc, w / 12, hh, 0.005) for c, w, hh in core], sides=8, mat_index=ORANGE)
    hot = [(8.2, 0.0, 0.0), (9.0, 0.8, 0.095), (11.0, 0.8, 0.1), (12.6, 0.0, 0.0)]
    lib.loft2(bm, [(ex(c), -yc, w / 12, hh, 0.01) for c, w, hh in hot], sides=8, mat_index=YELLOW)
    back = [(3.4, 0.0, 0.0), (2.6, 1.2, 0.05), (1.2, 1.0, 0.045), (-0.1, 0.0, 0.0)]
    lib.loft2(bm, [(ex(c), -yc, w / 12, hh, 0.0) for c, w, hh in back], sides=8, mat_index=ORANGE)
    lib.rotate_new(bm, start, -math.pi / 2)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
