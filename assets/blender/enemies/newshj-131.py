"""Green pod on a red mount (newshj.shp frame 131): a 3D version of its sprite.

Seen in episode 2 (levels 2.2 and 2.6). A ground emplacement: a dark red mount, with red studs
at its upper corners and two red side housings below, each with a yellow lamp, carries a
bulbous green carapace. The carapace has rounded shoulders, a ridge down each side, a raised
pale centre with a white-hot sheen, a head with two pale spots at the top and a split tail
between the housings. It is mirror symmetric about pixel column 12.

Run: blender --background --python assets/blender/enemies/newshj-131.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b096 as lib  # noqa: E402

NAME = "newshj-131"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)
AXIS = 12  # mirror column


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(114, metallic=0.1, roughness=0.75),  # 0 dark red mount
        pal(116, metallic=0.4, roughness=0.45),  # 1 red housings
        pal(120, metallic=0.3, roughness=0.4),  # 2 bright red ridges
        pal(119, emission_strength=1.5),  # 3 red corner studs
        pal(124, emission_strength=4.0),  # 4 yellow lamps
        pal(40, metallic=0.1, roughness=0.5),  # 5 green carapace
        pal(41, metallic=0.1, roughness=0.45),  # 6 shoulders
        pal(44, metallic=0.1, roughness=0.35),  # 7 pale ridges and centre
        pal(42, metallic=0.1, roughness=0.45),  # 8 side ribs and tail lobes
        pal(46, metallic=0.1, roughness=0.25),  # 9 sheen and pale spots
        pal(37, metallic=0.1, roughness=0.6),  # 10 dark groove down the tail
        pal(113, metallic=0.3, roughness=0.6),  # 11 dark red corner blocks
    ]
    MOUNT, HOUSING, RIDGE, STUD, LAMP, BODY, SHOULDER, PALE, RIB, SHEEN, GROOVE, BLOCK = range(12)
    bm = bmesh.new()

    # ---- left half (mirrored) ----
    # Corner block with a glowing stud (rows 6-7, columns 5-7).
    lib.plate(bm, G, [(5, 6), (8, 6), (8, 8.5), (5, 8.5)], 0.0, 0.17, mat=BLOCK)
    lib.dome(bm, G, 6, 6.4, 1.3, 0.9, 0.05, z0=0.16, mat=STUD, segments=10, rings=3)
    # Side housing (rows 16-22, column 6) with a bright ridge and the yellow lamp.
    lib.loft_y(bm, G, 6, [(16.0, 0.0, 0.0, 0.08), (16.6, 1.5, 0.12, 0.08), (21.0, 1.6, 0.13, 0.08),
                          (22.0, 1.2, 0.1, 0.08), (22.6, 0.0, 0.0, 0.08)], sides=10, mat=HOUSING)
    lib.loft_y(bm, G, 6, [(16.6, 0.0, 0.0, 0.18), (17.2, 0.6, 0.05, 0.18), (18.4, 0.6, 0.05, 0.19),
                          (19.0, 0.0, 0.0, 0.19)], sides=6, mat=RIDGE)
    lib.dome(bm, G, 6, 19.1, 0.75, 0.8, 0.07, z0=0.17, mat=LAMP, segments=10, rings=3)
    # Red rim round the bottom of the mount, from the housing in under the tail (rows 22-23).
    lib.sweep(bm, G, [(6.0, 21.0, 0.08, 1.4, 0.07), (7.0, 22.4, 0.08, 1.4, 0.07), (9.0, 23.0, 0.08, 1.2, 0.06),
                      (11.0, 23.0, 0.08, 1.1, 0.06), (12.0, 23.0, 0.08, 1.1, 0.06)], sides=8, mat=MOUNT)
    # Shoulder pod (columns 3-5, rows 8-15) with a pale highlight down its inner side.
    lib.loft_y(bm, G, 4.4, [(7.9, 0.0, 0.0, 0.16), (8.6, 1.6, 0.11, 0.17), (10.0, 2.1, 0.15, 0.18),
                            (13.5, 2.1, 0.15, 0.18), (14.8, 1.6, 0.11, 0.16), (15.5, 0.0, 0.0, 0.14)],
               sides=10, mat=SHOULDER)
    lib.loft_y(bm, G, 5.1, [(8.7, 0.0, 0.0, 0.29), (9.3, 0.7, 0.04, 0.3), (13.3, 0.7, 0.04, 0.3),
                            (14.0, 0.0, 0.0, 0.28)], sides=6, mat=PALE)
    # Side rib (column 8, rows 8-14).
    lib.loft_y(bm, G, 8, [(7.8, 0.0, 0.0, 0.24), (8.5, 0.8, 0.07, 0.27), (14.0, 0.8, 0.07, 0.27),
                          (15.0, 0.0, 0.0, 0.22)], sides=6, mat=RIB)
    # Tail lobe (columns 9-10, rows 16-21).
    lib.loft_y(bm, G, 9.9, [(15.4, 0.0, 0.0, 0.14), (16.0, 1.3, 0.09, 0.14), (17.5, 1.6, 0.11, 0.14),
                            (20.0, 1.6, 0.1, 0.13), (21.2, 1.0, 0.07, 0.12), (21.7, 0.0, 0.0, 0.11)],
               sides=8, mat=RIB)
    # Pale spot on the head (row 6, column 11).
    lib.dome(bm, G, 11, 6.2, 0.7, 0.7, 0.04, z0=0.2, mat=SHEEN, segments=8, rings=2)

    lib.mirror_all(bm, G.X(AXIS))

    # ---- centre ----
    # The mount, under everything (rows 6-23).
    left = [(5, 6), (5, 16), (4, 16), (4, 17), (5, 17), (5, 22), (6, 22), (6, 23), (8, 23), (8, 24)]
    outline = left + [(25 - c, r) for c, r in reversed(left)]
    lib.plate(bm, G, list(reversed(outline)), 0.0, 0.08, mat=MOUNT)
    # Main carapace (columns 3-21, rows 8-15).
    lib.loft_y(bm, G, AXIS, [(7.7, 4.0, 0.06, 0.12), (8.3, 7.4, 0.12, 0.12), (9.4, 8.8, 0.15, 0.12),
                             (11.0, 9.5, 0.17, 0.12), (13.6, 9.5, 0.16, 0.12), (14.8, 8.8, 0.13, 0.12),
                             (15.7, 7.0, 0.08, 0.11), (16.2, 3.5, 0.05, 0.1)], sides=14, mat=BODY)
    # Head (columns 9-15, rows 5-7), between the corner blocks.
    lib.loft_y(bm, G, AXIS, [(4.6, 0.0, 0.0, 0.1), (5.1, 2.8, 0.08, 0.1), (6.0, 3.5, 0.11, 0.1),
                             (8.0, 3.5, 0.12, 0.12), (9.0, 3.0, 0.12, 0.14)], sides=10, mat=BODY)
    # Raised pale centre (columns 10-14, rows 6-15) and its sheen.
    lib.loft_y(bm, G, AXIS, [(6.3, 0.0, 0.0, 0.2), (7.0, 1.6, 0.05, 0.2), (8.3, 2.6, 0.1, 0.22),
                             (10.0, 2.8, 0.15, 0.22), (12.5, 2.8, 0.15, 0.22), (14.4, 2.4, 0.11, 0.2),
                             (15.5, 0.0, 0.0, 0.18)], sides=12, mat=PALE)
    lib.dome(bm, G, AXIS, 11.0, 1.6, 2.0, 0.04, z0=0.35, mat=SHEEN, segments=10, rings=3)
    # Tail between the lobes (column 12, rows 16-22), darker down its middle.
    lib.loft_y(bm, G, AXIS, [(15.5, 2.4, 0.08, 0.11), (17.0, 2.0, 0.08, 0.11), (20.5, 1.8, 0.07, 0.1),
                             (21.6, 1.4, 0.06, 0.1), (22.6, 0.0, 0.0, 0.09)], sides=8, mat=GROOVE)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = lib.preview_args()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], str(out), ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
