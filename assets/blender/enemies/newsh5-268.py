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


# Body: (row at the pixel edge, half width px, half height px).
BODY = [(0.0, 4.5, 3.4), (8.0, 4.5, 3.4), (11.6, 4.4, 3.3), (12.4, 3.7, 2.9), (15.5, 3.4, 2.6),
        (18.5, 2.5, 1.9), (20.5, 1.7, 1.3), (22.5, 0.8, 0.7), (23.7, 0.0, 0.0)]


class BodySurface:
    """Top of the body loft, for draping the vents and the sensor window."""

    def top(self, x, y):
        r = 14 - y * 12
        for (r0, w0, h0), (r1, w1, h1) in zip(BODY, BODY[1:]):
            if r0 <= r <= r1:
                t = (r - r0) / (r1 - r0)
                w, h = (w0 + (w1 - w0) * t) / 12, (h0 + (h1 - h0) * t) / 12
                break
        else:
            return 0.0
        u = (x - CX) / w if w else 1.0
        return h * math.sqrt(max(0.0, 1 - u * u))


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.4, roughness=0.35),  # 0 grey body
        pal(5, metallic=0.4, roughness=0.4),  # 1 darker nose and fins
        pal(10, metallic=0.6, roughness=0.3),  # 2 light spine
        pal(2, metallic=0.2, roughness=0.6),  # 3 dark vents
        pal(3, metallic=0.3, roughness=0.08),  # 4 dark sensor glass
        pal(12, emission_strength=2.0),  # 5 the sensor's glint
    ]
    BODYM, NOSE, SPINE, VENT, GLASS, GLINT = range(6)
    bm = bmesh.new()

    # Body and nose, top (back, cut off by the sprite edge) to the nose tip.
    start = len(bm.verts)
    common.loft(bm, [((14 - r) / 12, w / 12, h / 12, 0.0) for r, w, h in reversed(BODY)], sides=14,
                mat_index=BODYM)
    common.shift_x(bm, start, CX)
    for f in bm.faces:
        if f.calc_center_median().y < (14 - 12.0) / 12:
            f.material_index = NOSE
    # Light spine down the top of the body (column 11-12 highlight) and a band at row 8.
    surf = BodySurface()
    rows = [0.3, 4.0, 8.0, 11.5]
    lib.tube(bm, [(CX, (14 - r) / 12, surf.top(CX, (14 - r) / 12) - 0.005) for r in rows],
             [0.045] * 4, sides=6, mat_index=SPINE, flat=0.5)

    # Four dark vents (rows 6-7 and 9-10, columns 9-10 and 14-15).
    for c in (10.0, 15.0):
        for r in (7.0, 10.0):
            x, y = E(c, r)
            lib.drape_cap(bm, surf, x, y, 1.4 / 12, 1.4 / 12, lift=0.004, dome=0.0, sink=0.03,
                          sides=4, mat_index=VENT)

    # Sensor window at the front of the nose (rows 12-14, columns 10-14) with its glint.
    x, y = E(12.5, 13.5)
    lib.drape_cap(bm, surf, x, y, 2.7 / 12, 1.7 / 12, lift=0.01, dome=0.02, sink=0.03, sides=12,
                  mat_index=GLASS)
    x, y = E(11.5, 13.4)
    lib.drape_cap(bm, surf, x, y, 0.5 / 12, 0.5 / 12, lift=0.03, dome=0.004, sink=0.0, sides=6,
                  mat_index=GLINT)

    # Swept fin tips at the top corners (rows 0-3, columns 2-6), joined to the body by a root.
    fin = [E(2, 0), E(2, 1.8), E(3.2, 3.0), E(4.2, 4.0), E(5.0, 3.6), E(5.4, 1.2), E(8.6, 1.0), E(8.6, 0)]
    for mirror in (False, True):
        pts = [(2 * CX - x, y) for x, y in fin] if mirror else fin
        area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
        if area < 0:
            pts = list(reversed(pts))
        common.slab(bm, pts, 0.07, z=0.0, mat_index=NOSE)
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
