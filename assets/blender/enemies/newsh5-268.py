"""Grey torpedo craft (newsh5.shp frame 268): a 3D version of its sprite.

Seen in episode 4 (levels 16 and 47). It flies nose down the screen: a round grey body (columns
8-16) cut off at the top of the sprite, two swept fin tips at the top corners, four dark vents
on the body, then a tapering nose with a dark sensor window. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-268.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-268"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

CX = lib.px(12)  # body centreline (columns 8-16)


def E(c, r):
    """Pixel edge coordinates (column, row) to Blender (x, y)."""
    return ((c - 12) / 12, (14 - r) / 12)


# Body: (row at the pixel edge, half width px). The body is a round tube (the sprite's bright
# spine, mid-grey left flank and near-black right flank), so its section is a circle as tall as it
# is wide: 11 px across its dark outline columns 7 and 17 down to row 12, then the nose steps in to
# 9 px and tapers to the point at row 24.
BODY = [(0.0, 5.5), (11.9, 5.5), (12.1, 4.6), (15.0, 4.4), (16.5, 3.9), (19.0, 3.0), (21.0, 2.0),
        (23.0, 1.0), (24.0, 0.0)]
SIDES = 16


class BodySurface:
    """Top of the body loft, for draping the vents and the sensor window."""

    def top(self, x, y):
        r = 14 - y * 12
        for (r0, w0), (r1, w1) in zip(BODY, BODY[1:]):
            if r0 <= r <= r1:
                t = (r - r0) / (r1 - r0)
                w = (w0 + (w1 - w0) * t) / 12
                break
        else:
            return 0.0
        u = (x - CX) / w if w else 1.0
        return w * math.sqrt(max(0.0, 1 - u * u))


# Palette index of the body's faces by the angle of their normal from straight up (degrees,
# negative = left flank; the 16-sided loft has a face centred every 22.5 degrees), sampled from
# the sprite's columns under each face: the body (rows 0-11), the nose and the dark nose tip.
BODY_SHADES = {-90: 1, -67.5: 1, -45: 6, -22.5: 8, 0: 7, 22.5: 3, 45: 3, 67.5: 1, 90: 1}
NOSE_SHADES = {-90: 112, -67.5: 112, -45: 3, -22.5: 6, 0: 6, 22.5: 4, 45: 2, 67.5: 112, 90: 112}
TIP_SHADES = {-90: 112, -67.5: 112, -45: 2, -22.5: 3, 0: 4, 22.5: 3, 45: 2, 67.5: 112, 90: 112}


def shade(angle, table):
    return table[min(table, key=lambda t: abs(t - angle))]


def build(sprite):
    coll = common.reset_collection(NAME)
    mats, slots = [], {}

    def m(i, tag=NAME, **kw):
        """Material slot for palette index i (one material per index and tag)."""
        if (i, tag) not in slots:
            slots[(i, tag)] = len(mats)
            mats.append(common.palette_material(sprite, i, tag, **kw))
        return slots[(i, tag)]

    hull = dict(metallic=0.4, roughness=0.4)
    bm = bmesh.new()

    # Body and nose, top (back, cut off by the sprite edge) to the nose tip: a round loft whose
    # faces take the sprite's shade for their angle.
    start, vstart = len(bm.faces), len(bm.verts)
    common.loft(bm, [((14 - r) / 12, w / 12, w / 12, 0.0) for r, w in reversed(BODY)], sides=SIDES,
                mat_index=m(7, **hull))
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start:]:
        c = f.calc_center_median()
        if len(f.verts) > 4:
            f.material_index = m(1, **hull)  # the cut-off back cap
            continue
        ang = math.degrees(math.atan2(c.x, c.z))
        if c.z < -1e-4:
            ang = math.copysign(90, c.x) if abs(c.x) > 1e-4 else 90
        r = 14 - c.y * 12
        table = TIP_SHADES if r > 19.0 else NOSE_SHADES if r > 12.0 else BODY_SHADES
        f.material_index = m(shade(ang, table), **hull)
    common.shift_x(bm, vstart, CX)

    # Light spine down the top of the body (column 11): near white at rows 0-3, light grey to row 8.
    surf = BodySurface()
    sx = CX - 1 / 12
    for rows, idx in (([0.2, 2.0, 3.6], 12), ([3.4, 6.0, 8.5], 10)):
        lib.tube(bm, [(sx, (14 - r) / 12, surf.top(sx, (14 - r) / 12) - 0.012) for r in rows],
                 [0.05, 0.05, 0.03], sides=6, mat_index=m(idx, metallic=0.6, roughness=0.3), flat=0.8)

    # Four dark vents (rows 6-7 and 9-10, columns 9-10 and 14-15), cut into the round flanks.
    for c in (10.0, 15.0):
        for r in (7.0, 10.0):
            x, y = E(c, r)
            lib.drape_cap(bm, surf, x, y, 1.4 / 12, 1.4 / 12, lift=0.006, dome=0.0, sink=0.05,
                          sides=4, mat_index=m(2, metallic=0.2, roughness=0.6))

    # Sensor window at the front of the nose (rows 12-14, columns 10-14) with its glint.
    x, y = E(12.5, 13.5)
    lib.drape_cap(bm, surf, x, y, 2.7 / 12, 1.7 / 12, lift=0.01, dome=0.02, sink=0.03, sides=12,
                  mat_index=m(1, metallic=0.3, roughness=0.08))
    x, y = E(11.5, 13.4)
    lib.drape_cap(bm, surf, x, y, 0.5 / 12, 0.5 / 12, lift=0.03, dome=0.004, sink=0.0, sides=6,
                  mat_index=m(12, tag=f"{NAME}-glint", emission_strength=2.0))

    # Swept wings at the top corners (rows 0-4, columns 1-7): 2 px plates at the body's mid-height,
    # a grey top with a dark red outer rim, a black inner edge and a maroon root at row 0 (a slightly
    # different maroon on the right, as in the sprite).
    wing = m(6, **hull)
    parts = [
        ([E(2, 0), E(2, 1.5), E(4.5, 4), E(5, 4), E(5, 0)], wing),
        ([E(1, 0), E(1, 1.9), E(4, 4.6), E(4.5, 4), E(2, 1.5), E(2, 0)], m(112, **hull)),
        ([E(5, 0), E(5, 4), E(4.5, 4), E(4, 4.6), E(4.4, 5), E(6, 5), E(6, 2), E(7.6, 2),
          E(7.6, 1), E(6, 1), E(6, 0)], m(1, **hull)),
        ([E(6, 0), E(6, 1), E(7.6, 1), E(7.6, 0)], (m(67, **hull), m(65, **hull))),
    ]
    for pts0, mat in parts:
        for mirror in (False, True):
            side_mat = mat[mirror] if isinstance(mat, tuple) else mat
            pts = [(2 * CX - x, y) for x, y in pts0] if mirror else list(pts0)
            area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
            if area < 0:
                pts = list(reversed(pts))
            common.slab(bm, pts, 2 / 12, z=0.0, mat_index=side_mat)
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
