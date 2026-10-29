"""Grey shield machine with a brown yoke (newsh2.shp frame 267): a 3D version of its sprite.

Seen in episodes 1, 2 and 3 (levels 1.25, 1.3, 2.6, 3.17). A grey shield-shaped hull that comes
to a point at the bottom, with a shiny grey dome on top. An axle runs sideways through the dome
to a brown yoke whose arms curve down either side and end in grey runners on the ground. Brown
armour pads with cream knobs sit on the hull's upper corners, and a dark spine down its middle
carries two glowing red lights, with a tan stud below them. One frame, one model.

Run: blender --background --python assets/blender/enemies/newsh2-267.py [-- --preview out.png]
"""

import math
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

    # The drill (rows 8-27): a round drum (columns 5-17) that tapers from row 19 into a conical bit
    # whose point touches the ground at row 27. Its height follows its half width (round section).
    body = [(7.6, 5.2, 0.42), (8.4, 6.9, 0.56), (18.6, 6.9, 0.57), (19.6, 6.3, 0.53), (20.8, 5.6, 0.48),
            (22.3, 4.7, 0.41), (23.7, 3.8, 0.34), (24.8, 2.9, 0.27), (25.7, 2.0, 0.2), (26.6, 1.1, 0.12),
            (27.4, 0.3, 0.05)]
    lib.dloft(bm, G, AXIS, body, sides=14, mat=HULL, power=2.1)

    # Spiral flights round the bit: raised ridges running down and to the left across its top (the
    # sprite's diagonal light bands), following the surface.
    def surf(v, a, lift):
        for (v0, h0, z0), (v1, h1, z1) in zip([s[:3] for s in body], [s[:3] for s in body[1:]]):
            if v0 <= v <= v1:
                t = (v - v0) / (v1 - v0)
                hw, zt = h0 + (h1 - h0) * t, z0 + (z1 - z0) * t
                break
        e = 2 / 2.1
        ca, sa = math.cos(a), math.sin(a)
        x = (hw + lift / lib.PX) * math.copysign(abs(ca) ** e, ca)
        return AXIS + x, v, (zt + lift) * (abs(sa) ** e)

    for v_start in (14.0, 17.6, 21.2):
        path = []
        n = 9
        for k in range(n + 1):
            a = 0.2 + (math.pi - 0.4) * k / n
            v = v_start + 6.5 * k / n
            if v > 26.2:
                break
            u, vv, z = surf(v, a, 0.012)
            path.append((u, vv, z, 0.45, 0.03))
        lib.sweep(bm, G, path, sides=4, mat=RUNNER, smooth=False)

    # Brown shoulder armour (rows 8-13): a faceted collar wrapping the drum, boxier than the drum.
    lib.dloft(bm, G, AXIS, [(7.9, 5.6, 0.5), (8.6, 6.3, 0.6), (9.9, 6.6, 0.61), (10.3, 7.2, 0.61), (12.7, 7.3, 0.61), (13.3, 6.6, 0.53)],
              sides=10, mat=PAD, power=3.2, smooth=False)
    # Cream knobs on the armour's inner top corners.
    lib.dome(bm, G, 7.4, 9.4, 0.54, 1.7, 1.6, 0.14, mat=KNOB, segments=10, rings=3)
    lib.dome(bm, G, 14.2, 9.0, 0.56, 1.3, 1.4, 0.12, mat=KNOB, segments=10, rings=3)

    # Dark spine plate down the middle (columns 9-13, rows 8-18), standing proud of the armour, with
    # the two red lights (rows 9 and 11) set in slots between its bars.
    lib.box(bm, G, 9.5, 7.8, 13.5, 18.7, 0.0, 0.63, mat=SPINE, chamfer=0.03)
    for v0, v1 in ((7.8, 9.0), (10.0, 11.0), (12.0, 14.9)):
        lib.box(bm, G, 9.5, v0, 13.5, v1, 0.6, 0.68, mat=SPINE, chamfer=0.025)
    for u0, u1 in ((9.5, 10.0), (13.0, 13.5)):
        lib.box(bm, G, u0, 7.8, u1, 14.9, 0.6, 0.68, mat=SPINE, chamfer=0.015)
    for v in (9.0, 11.0):
        lib.box(bm, G, 10.0, v, 13.0, v + 1.0, 0.6, 0.65, mat=RED, chamfer=0.015)
        lib.box(bm, G, 11.0, v + 0.15, 12.0, v + 0.85, 0.64, 0.66, mat=HOT)
    # Tan stud below them (column 11, rows 15-17) on a light cross ridge (row 15).
    lib.sweep(bm, G, [(11.5, 14.8, 0.64, 0.0, 0.0), (11.5, 15.3, 0.64, 0.75, 0.06), (11.5, 17.5, 0.63, 0.65, 0.05),
                      (11.5, 18.3, 0.62, 0.0, 0.0)], sides=6, mat=TAN)
    lib.sweep(bm, G, [(8.4, 15.5, 0.55, 0.0, 0.0), (9.0, 15.5, 0.6, 0.5, 0.04), (14.0, 15.5, 0.6, 0.5, 0.04),
                      (14.6, 15.5, 0.55, 0.0, 0.0)], sides=6, mat=LIGHT)

    # The head (columns 8-14, rows 2-7): a grey drum neck with a round shiny dome cap, the highest
    # point, and the axle through it.
    lib.cylinder(bm, G, AXIS, 5.4, 0.0, 0.46, 3.6, 2.8, mat=RUNNER, sides=16)
    lib.box(bm, G, 8.2, 7.4, 14.8, 8.4, 0.0, 0.5, mat=RUNNER, chamfer=0.04)
    lib.dome(bm, G, AXIS, 5.4, 0.46, 3.6, 2.8, 0.3, mat=LIGHT, segments=16, rings=5)
    lib.sweep(bm, G, [(3.4, 5.5, 0.44, 0.65, 0.055), (19.6, 5.5, 0.44, 0.65, 0.055)], sides=8, mat=LIGHT)

    # Left side of the yoke (mirrored): a brown arm from its tip above the axle (row 2) curving
    # out and down to a grey piston runner on the ground (column 1, rows 10-18).
    start = len(bm.faces)
    lib.sweep(bm, G, [(4.6, 2.3, 0.52, 0.0, 0.0), (4.6, 2.8, 0.52, 0.95, 0.08), (4.3, 4.4, 0.5, 1.0, 0.085),
                      (3.8, 6.4, 0.44, 1.0, 0.085), (2.9, 7.7, 0.37, 0.95, 0.08), (2.1, 8.8, 0.3, 0.9, 0.075),
                      (1.6, 9.9, 0.24, 0.9, 0.07), (1.5, 10.8, 0.2, 0.8, 0.06)], sides=8, mat=YOKE)
    lib.sweep(bm, G, [(1.5, 10.0, 0.11, 0.0, 0.0), (1.5, 10.2, 0.11, 1.05, 0.105), (1.5, 18.0, 0.11, 1.05, 0.105),
                      (1.5, 18.9, 0.11, 0.6, 0.06), (1.5, 19.1, 0.11, 0.0, 0.0)], sides=10, mat=RUNNER)
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
