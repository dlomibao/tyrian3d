"""Grey bomb (newsh5.shp frame 77): a 3D version of its sprite.

Seen in episode 4 (levels 4.18, 4.22 and 4.47). A round steel bomb falling nose first down the
screen: a wide flat cap with a groove round it at the back, a thin neck between two collars, a
fat body with a red band round it and a pointed nose with stabiliser fins. Turned round its long
axis (which lies in the screen plane), flattened a little so it stays low.

Run: blender --background --python assets/blender/enemies/newsh5-77.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b013 as lib  # noqa: E402

NAME = "newsh5-77"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U
MAX_H = 3.4  # px: the round sections are flattened to at most this half height


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(11, metallic=0.75, roughness=0.25),  # 0 bright steel cap and collars
        pal(8, metallic=0.7, roughness=0.3),  # 1 steel body
        pal(5, metallic=0.6, roughness=0.4),  # 2 dark steel neck and nose
        pal(3, metallic=0.5, roughness=0.5),  # 3 grooves
        pal(117, metallic=0.3, roughness=0.35),  # 4 red band
    ]
    CAP, BODY, DARK, GROOVE, BAND = range(5)
    g = lib.Grid(24, 28)
    ax = g.x(12)
    bm = bmesh.new()

    def part(sections, mat, cap_start=True, cap_end=True):
        """A round section of the bomb: (row edge, half width px) pairs down the screen."""
        v0 = len(bm.verts)
        common.loft(bm, [(g.y(r - 0.5), w * U, min(w, MAX_H) * U, 0.0) for r, w in sections],
                    sides=16, mat_index=mat, cap_start=cap_start, cap_end=cap_end)
        common.shift_x(bm, v0, ax)

    # common.loft runs along +Y, so list each part from its bottom (nose end) up.
    part([(26.4, 0.0), (25.6, 1.1), (24.8, 2.2), (23.8, 3.3), (22.8, 4.2), (22.0, 5.0)], DARK)  # nose
    part([(22.0, 5.0), (19.0, 5.0)], BODY)  # body below the band (rows 19-21)
    part([(19.1, 4.9), (18.9, 5.0), (17.1, 5.0), (16.9, 4.9)], BAND)  # red band (rows 17-18)
    part([(17.0, 4.6), (15.2, 4.6), (14.8, 4.2), (14.4, 2.0)], BODY)  # body top (rows 15-16)
    part([(14.6, 1.5), (13.4, 1.5)], DARK)  # waist (row 14)
    part([(13.8, 2.5), (10.0, 2.5), (9.6, 1.6)], CAP)  # lower collar (rows 10-13)
    part([(9.8, 1.5), (6.8, 1.5)], DARK)  # neck (rows 7-9)
    part([(7.0, 1.6), (6.6, 2.5), (4.8, 2.5), (4.4, 1.8)], CAP)  # upper collar (rows 5-6)
    part([(4.6, 2.0), (4.1, 2.6), (3.9, 3.4)], DARK)  # under the cap (row 4)
    part([(4.0, 3.2), (3.8, 4.4), (3.2, 4.8), (2.9, 4.8)], CAP)  # cap rim (row 3)
    part([(3.2, 4.8), (2.0, 4.8)], GROOVE)  # groove round the cap (row 2)
    part([(2.1, 5.4), (0.9, 5.4), (0.6, 4.6)], CAP)  # cap (row 1)
    lib.set_smooth(bm, 0)

    # Two stabiliser fins on the nose (the one to the right shows on the sprite at columns 15-16).
    for ang in (math.radians(35), math.radians(215)):
        d = (math.cos(ang), math.sin(ang))
        t = 0.35 * U  # half thickness
        pts = [(19.6, 3.6), (19.6, 6.4), (23.2, 4.6), (24.6, 2.0)]  # (row edge, radius px)
        verts = []
        for r, rad in pts:
            cx, cz = ax + d[0] * rad * U, d[1] * rad * U * (MAX_H / 5.0)
            verts.append([bm.verts.new((cx - d[1] * t * s, g.y(r - 0.5), cz + d[0] * t * s)) for s in (-1, 1)])
        a = [v[0] for v in verts]
        b = [v[1] for v in verts]
        bm.faces.new(a).material_index = BODY
        bm.faces.new(list(reversed(b))).material_index = BODY
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((a[j], a[i], b[i], b[j])).material_index = BODY

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, [obj], sprite)


if __name__ == "__main__":
    main()
