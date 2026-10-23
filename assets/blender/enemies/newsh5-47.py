"""Purple belted pod (newsh5.shp frame 47): a 3D version of its sprite.

Seen in episode 4 (levels 4 and 12). An egg-shaped purple pod, lighter above its middle and
darker below, girdled by a maroon belt (rows 11-16) with a gold strap down its front. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-47.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-47"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def E(r):
    """Pixel edge row to Blender Y."""
    return (14 - r) / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(88, metallic=0.35, roughness=0.35),  # 0 light purple upper shell
        pal(86, metallic=0.3, roughness=0.45),  # 1 darker purple lower shell
        pal(243, metallic=0.3, roughness=0.5),  # 2 maroon belt
        pal(250, metallic=0.8, roughness=0.25),  # 3 gold strap
        pal(94, metallic=0.6, roughness=0.2),  # 4 pale strap top
        pal(241, metallic=0.2, roughness=0.6),  # 5 dark belt edges
        pal(82, metallic=0.2, roughness=0.5),  # 6 dark recessed panel below the belt
    ]
    UPPER, LOWER, BELT, GOLD, PALE, EDGE, PANEL = range(7)
    bm = bmesh.new()

    # Shell: columns 1-22, rows 1-25 inside the dark rim.
    shell = lib.Ellipsoid(0.0, E(13.5), 11.2 / 12, 12.8 / 12, 0.3)
    shell.build(bm, segments=24, rings=14, mat_index=UPPER)
    belt_top, belt_bottom = E(10.8), E(17.2)
    for f in bm.faces:
        if f.calc_center_median().y < (belt_top + belt_bottom) / 2:
            f.material_index = LOWER

    # Belt: a ring round the shell from row 10.8 to 17.2, standing a little proud, with dark lips.
    def ring(y, grow):
        u = (y - shell.y0) / shell.b
        k = math.sqrt(max(0.0, 1 - u * u))
        return (y, shell.a * k + grow, shell.c * k + grow, 0.0)
    lips = [ring(belt_bottom - 0.01, 0.0), ring(belt_bottom, 0.03), ring(belt_bottom + 0.06, 0.035)]
    mid = [ring(belt_bottom + (belt_top - belt_bottom) * t, 0.04) for t in (0.3, 0.5, 0.7)]
    tops = [ring(belt_top - 0.06, 0.035), ring(belt_top, 0.03), ring(belt_top + 0.01, 0.0)]
    common.loft(bm, lips[:2], sides=24, mat_index=EDGE, cap_start=False, cap_end=False)
    common.loft(bm, lips[1:] + mid + tops[:2], sides=24, mat_index=BELT, cap_start=False, cap_end=False)
    common.loft(bm, tops[1:], sides=24, mat_index=EDGE, cap_start=False, cap_end=False)

    # Gold strap down the front of the belt (columns 11-12), with its pale top (row 11).
    belt = lib.Ellipsoid(0.0, shell.y0, shell.a + 0.04, shell.b, shell.c + 0.04)
    lib.drape_cap(bm, belt, 0.0, E(14.2), 1.25 / 12, 3.0 / 12, lift=0.004, dome=0.008, sink=0.02,
                  sides=12, mat_index=GOLD)
    lib.drape_cap(bm, belt, 0.0, E(11.6), 1.0 / 12, 0.7 / 12, lift=0.012, dome=0.004, sink=0.0,
                  sides=8, mat_index=PALE)
    # The dark panel under the belt (rows 18-24, columns 5-17), flush with the lower shell.
    lib.drape_cap(bm, shell, 0.0, E(19.6), 7.4 / 12, 4.4 / 12, lift=0.004, dome=0.0, sink=0.01,
                  sides=20, mat_index=PANEL)
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
