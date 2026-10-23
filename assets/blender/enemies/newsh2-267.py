"""Grey shield machine with a brown yoke (newsh2.shp frame 267): a 3D version of its sprite.

Seen in episodes 1, 2 and 3 (levels 1.25, 1.3, 2.6, 3.17). A grey shield-shaped hull that comes
to a point at the bottom, with a shiny grey dome on top. An axle runs sideways through the dome
to a brown yoke whose arms curve down either side and end in grey runners on the ground. Brown
armour pads with cream knobs sit on the hull's upper corners, and a dark spine down its middle
carries two glowing red lights, with a tan stud below them. One frame, one model.

Run: blender --background --python assets/blender/enemies/newsh2-267.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b083 as lib  # noqa: E402

NAME = "newsh2-267"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)
AXIS = 11.5  # the sprite is symmetric about the centre of column 11


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh2_267", **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.55, roughness=0.4),  # 0 grey hull
        pal(11, metallic=0.6, roughness=0.3),  # 1 light grey dome, axle
        pal(4, metallic=0.4, roughness=0.5),  # 2 dark spine
        pal(119, emission_strength=3.0),  # 3 red lights
        pal(121, emission_strength=4.5),  # 4 hot centre of the lights
        pal(23, metallic=0.35, roughness=0.45),  # 5 brown yoke
        pal(9, metallic=0.55, roughness=0.4),  # 6 grey runners, neck
        pal(166, metallic=0.3, roughness=0.5),  # 7 brown armour pads
        pal(29, metallic=0.4, roughness=0.35),  # 8 cream knobs
        pal(26, metallic=0.4, roughness=0.4),  # 9 tan stud
        pal(13, metallic=0.7, roughness=0.2),  # 10 dome highlight
    ]
    HULL, LIGHT, SPINE, RED, HOT, YOKE, RUNNER, PAD, KNOB, TAN, SHINE = range(11)
    bm = bmesh.new()

    # Shield hull, rows 8-26: full width (columns 5-17) down to row 18, then to a point.
    lib.dloft(bm, G, AXIS, [(7.4, 4.8, 0.2), (8.2, 6.5, 0.27), (18.8, 6.5, 0.27), (20.2, 4.9, 0.25),
                            (22.0, 4.1, 0.22), (23.8, 3.3, 0.18), (24.8, 2.4, 0.14), (25.6, 1.5, 0.1),
                            (26.5, 0.7, 0.06), (27.0, 0.2, 0.03)], sides=10, mat=HULL, power=2.4)

    # Dark spine down the middle (columns 9-13, rows 8-14) with two red lights (rows 9 and 11).
    lib.box(bm, G, 9.5, 7.8, 13.5, 15.0, 0.0, 0.29, mat=SPINE, chamfer=0.03)
    for v in (9.0, 11.0):
        lib.box(bm, G, 10.0, v, 13.0, v + 1.0, 0.25, 0.33, mat=RED, chamfer=0.02)
        lib.box(bm, G, 11.0, v + 0.1, 12.0, v + 0.9, 0.3, 0.345, mat=HOT)
    # Tan stud below them (column 11, rows 15-17) on a light cross ridge (row 15).
    lib.sweep(bm, G, [(11.5, 14.8, 0.27, 0.0, 0.0), (11.5, 15.3, 0.27, 0.7, 0.04), (11.5, 17.5, 0.26, 0.6, 0.035),
                      (11.5, 18.2, 0.25, 0.0, 0.0)], sides=6, mat=TAN)
    lib.sweep(bm, G, [(8.6, 15.5, 0.25, 0.0, 0.0), (9.2, 15.5, 0.265, 0.5, 0.025), (13.8, 15.5, 0.265, 0.5, 0.025),
                      (14.4, 15.5, 0.25, 0.0, 0.0)], sides=6, mat=LIGHT)

    # Brown armour pads on the upper corners with cream knobs (left columns 5-8, right 14-17).
    lib.box(bm, G, 5.0, 8.4, 9.2, 13.0, 0.0, 0.29, mat=PAD, chamfer=0.06)
    lib.box(bm, G, 13.8, 8.0, 18.0, 13.0, 0.0, 0.29, mat=PAD, chamfer=0.06)
    lib.dome(bm, G, 7.4, 9.6, 0.26, 1.9, 1.8, 0.1, mat=KNOB, segments=10, rings=3)
    lib.dome(bm, G, 14.1, 9.1, 0.26, 1.5, 1.6, 0.09, mat=KNOB, segments=10, rings=3)

    # The head (columns 8-14, rows 3-7): a grey neck with a shiny dome, and the axle through it.
    lib.cylinder(bm, G, AXIS, 5.6, 0.0, 0.3, 3.5, 2.5, mat=RUNNER, sides=16)
    lib.dome(bm, G, AXIS, 5.6, 0.3, 3.5, 2.5, 0.16, mat=LIGHT, segments=16, rings=4)
    lib.dome(bm, G, 10.4, 4.6, 0.38, 1.1, 0.9, 0.08, mat=SHINE, segments=8, rings=2)
    lib.sweep(bm, G, [(3.6, 5.5, 0.3, 0.6, 0.05), (19.4, 5.5, 0.3, 0.6, 0.05)], sides=8, mat=LIGHT)

    # Left side of the yoke (mirrored): a brown arm from its tip above the axle (row 3) curving
    # out and down to a grey runner on the ground (column 1, rows 10-18).
    start = len(bm.faces)
    lib.sweep(bm, G, [(4.6, 2.9, 0.37, 0.0, 0.0), (4.6, 3.3, 0.37, 0.9, 0.06), (4.2, 5.0, 0.32, 1.0, 0.065),
                      (3.8, 6.6, 0.28, 1.0, 0.065), (2.9, 7.7, 0.24, 0.95, 0.06), (2.0, 8.8, 0.19, 0.9, 0.055),
                      (1.6, 9.9, 0.15, 0.85, 0.05), (1.5, 10.6, 0.13, 0.7, 0.045)], sides=8, mat=YOKE)
    lib.dloft(bm, G, 1.5, [(10.0, 0.75, 0.15), (17.6, 0.75, 0.13), (18.8, 0.55, 0.08)], sides=6,
              mat=RUNNER, power=3)
    lib.mirror_from(bm, start, G.x(AXIS))

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
