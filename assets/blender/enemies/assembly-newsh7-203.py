"""Red mortar turret on the ice edge (newsh7.shp, assembly of newsh7-169 and newsh7-203): a 3D
version of its sprites.

Seen in episode 3 (level section 10). Two pieces one above the other make a 24x56 px turret (the
level puts two side by side; sprite.json `assemblyLayout`): newsh7-169 is a red armoured shell
on a tile of ice, with a raised hatch on top, two claws down its front and a grey barrel guide
between them, ending in a red collar; newsh7-203 hangs out over the drop below the ice: the
barrel's grey end knob, a red-hot joint and a grey mortar cup opening upward, with a firing pin
in its dark bore. Its three frames slide the joint and cup out by 0, 1 and 3 px, so newsh7-203
gets a model per frame (newsh7-203, newsh7-203-f2, newsh7-203-f3).

The turret is built once in assembly coordinates (a 24x56 px block, origin at its centre) and
cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh7-203.py [-- --preview out.png]
(the preview is the whole turret; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b108 as lib  # noqa: E402
from lib_b108 import common  # noqa: E402

NAME = "assembly-newsh7-203"
ROOT = common.repo_root(__file__)
TOP, GUN = "newsh7-169", "newsh7-203"
CX0, CY0 = 272, 6  # screen centre of the left turret's 24x56 block (169 at cy -8, 203 at cy 20)
P = 1 / 12
BASE = 0.04  # top of the ice
AXIS = 10.5  # the turret is symmetric about this column


def X(c):
    """Column (centre; fractions allowed) to Blender X."""
    return (c + 0.5 - 12) / 12


def Y(r):
    """Assembly row (0-27 newsh7-169, 28-55 newsh7-203; centre) to Blender Y."""
    return (28 - (r + 0.5)) / 12


AX = X(AXIS)


def build(sprite, slide):
    """The whole turret with the joint and cup slid out by `slide` px."""
    coll = common.reset_collection(f"{NAME}-{slide}")
    tag = "n7_203"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(58, metallic=0.1, roughness=0.35),  # 0 ice
        pal(116, metallic=0.35, roughness=0.4),  # 1 red shell
        pal(118, metallic=0.35, roughness=0.35),  # 2 lighter red hatch / collar band
        pal(113, metallic=0.2, roughness=0.6),  # 3 dark red recess
        pal(120, metallic=0.4, roughness=0.3),  # 4 bright red claw edges
        pal(5, metallic=0.7, roughness=0.4),  # 5 dark grey barrel guide
        pal(13, metallic=0.8, roughness=0.2),  # 6 bright grey rails, pin
        pal(11, metallic=0.8, roughness=0.25),  # 7 grey knob and cup
        pal(3, metallic=0.4, roughness=0.6),  # 8 dark bore
        pal(118, emission_strength=2.5),  # 9 red-hot joint
        pal(9, metallic=0.75, roughness=0.3),  # 10 grey rod
    ]
    ICE, SHELL, HATCH, RECESS, EDGE, GUIDE, RAIL, KNOB, BORE, JOINT, ROD = range(11)
    bm = bmesh.new()

    # Ice under newsh7-169 (rows 0-27).
    e = 0.005  # keep the plate's edges just inside the cut lines
    lib.plate(bm, [(X(-0.5) + e, Y(27.5) + e), (X(23.5) - e, Y(27.5) + e), (X(23.5) - e, Y(-0.5) - e),
                   (X(-0.5) + e, Y(-0.5) - e)], 0.0, BASE, mat=ICE)

    # The shell (rows 0-17, columns 1-20): (row, half width px, height).
    shell = [(-0.3, 5.0, 0.12), (0.6, 6.6, 0.26), (2.0, 8.2, 0.36), (4.0, 9.3, 0.42), (7.0, 9.8, 0.44),
             (10.0, 9.8, 0.4), (12.5, 9.6, 0.32), (15.0, 9.0, 0.22), (16.5, 8.0, 0.12)]
    lib.arch_loft(bm, [(AX, Y(r), w * P, h, BASE) for r, w, h in shell], sides=12, mat=SHELL)
    # Raised hatch on top (rows 1-8, columns 7-14).
    lib.frustum(bm, [(X(6.6), Y(8.6)), (X(14.4), Y(8.6)), (X(14.4), Y(1.6)), (X(6.6), Y(1.6))],
                [(X(7.2), Y(8.0)), (X(13.8), Y(8.0)), (X(13.8), Y(2.4)), (X(7.2), Y(2.4))],
                BASE + 0.28, BASE + 0.475, mat=HATCH)

    # Two claws down the front (columns 2-6 and 15-19, rows 8-21), bright along their crests.
    for side in (-1, 1):
        c = AXIS + side * 7.2
        claw = [(8.0, 2.2, 0.36), (12.0, 2.4, 0.34), (16.0, 2.3, 0.28), (19.0, 2.0, 0.2), (21.2, 1.2, 0.1)]
        lib.arch_loft(bm, [(X(c), Y(r), w * P, h, BASE) for r, w, h in claw], sides=8, mat=SHELL)
        lib.polyline_tube(bm, [(X(c + side * 0.6), Y(r), BASE + h - 0.01) for r, _, h in claw[1:4]],
                          0.6 * P, sides=4, mat_index=EDGE, squash=0.6)

    # Dark recess between the claws (rows 9-21) and the grey barrel guide in it (rows 13-22).
    lib.plate(bm, [(X(4.5), Y(21.5)), (X(16.5), Y(21.5)), (X(16.5), Y(9.0)), (X(4.5), Y(9.0))],
              BASE, BASE + 0.2, mat=RECESS)
    lib.plate(bm, [(X(7.5), Y(22.5)), (X(13.5), Y(22.5)), (X(13.5), Y(12.6)), (X(7.5), Y(12.6))],
              BASE, BASE + 0.27, mat=GUIDE)
    for c in (8.0, 13.0):
        lib.tube(bm, (X(c), Y(13.2), BASE + 0.27), (X(c), Y(21.8), BASE + 0.27), 0.7 * P, sides=6, mat_index=RAIL)
    lib.tube(bm, (X(8.6), Y(17.0), BASE + 0.28), (X(12.4), Y(17.0), BASE + 0.28), 0.7 * P, sides=6, mat_index=RAIL)

    # Red collar round the barrel (rows 21-27, columns 5-16), with a lighter band at its top.
    collar = [(21.0, 4.5, 0.18), (21.8, 6.0, 0.25), (24.5, 6.0, 0.25), (26.0, 5.2, 0.2), (27.0, 3.5, 0.12)]
    lib.arch_loft(bm, [(AX, Y(r), w * P, h, BASE) for r, w, h in collar], sides=10, mat=SHELL)
    lib.arch_loft(bm, [(AX, Y(r), w * P, h, BASE) for r, w, h in ((21.9, 6.15, 0.255), (23.0, 6.15, 0.255))],
                  sides=10, mat=HATCH)

    # The barrel's grey end knob (rows 25-31, columns 7-14).
    zb = BASE + 0.15
    lib.ellipsoid(bm, AX, Y(29.4), zb, 4.0 * P, 3.6 * P, 0.13, mat=KNOB, segments=14, rings=7)

    # Grey rod out of the knob, then the red-hot joint and the cup, slid out by `slide` px.
    d = slide
    lib.tube(bm, (AX, Y(31.0), zb), (AX, Y(37.6 + d), zb + 0.04), 1.0 * P, sides=8, mat_index=ROD)
    joint = []
    for r, w in ((31.8, 1.4), (32.4, 2.0), (34.4, 2.0), (35.2, 1.4)):  # rows 4-6 of the frame
        joint.append([(AX + w * P * math.cos(2 * math.pi * (k + 0.5) / 8), Y(r + d),
                       zb + w * P * math.sin(2 * math.pi * (k + 0.5) / 8)) for k in range(8)])
    lib.ring_loft(bm, joint, JOINT)

    # The mortar cup (rows 7-21 of the frame, columns 5-16), opening upward and tipped a little
    # toward the bottom of the screen so its far wall shows like the sprite's.
    cy = Y(41.2 + d)
    start = len(bm.verts)
    rings = [(0.0, 0.0, 0.0), (0.0, 3.0, 3.2), (0.07, 5.2, 5.6), (0.18, 6.0, 6.5), (0.3, 6.0, 6.5),
             (0.32, 5.6, 6.0), (0.3, 4.8, 5.2), (0.12, 4.2, 4.6)]
    cup = []
    for z, rx, ry in rings:
        if rx == 0:
            cup.append([(AX, cy, z)])
        else:
            cup.append(lib.ellipse_ring(AX, cy, z, rx * P, ry * P, n=16))
    lib.ring_loft(bm, cup, [KNOB, KNOB, KNOB, KNOB, RAIL, BORE, BORE], cap_start=False, cap_end=True)
    # Firing pin standing in the bore.
    lib.tube(bm, (AX, cy, 0.12), (AX, cy, 0.27), 0.9 * P, sides=6, mat_index=RAIL)
    lib.ellipsoid(bm, AX, cy, 0.27, 1.2 * P, 1.2 * P, 0.025, mat=RAIL, segments=8, rings=4)
    lib.rotate_new(bm, start, (AX, cy, 0.0), math.radians(22), "X")
    # Lift the cup so it hangs level with the joint.
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.z += 0.02

    return lib.to_object(f"{NAME}-{slide}", bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, GUN, [TOP])
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["cx"] == CX0]
    gun = common.load_sprite(ROOT, GUN)
    top = common.load_sprite(ROOT, TOP)
    frames = gun["sprites"][0]["frames"]
    objs = {}
    for i, slide in enumerate((0, 1, 3)):
        obj = build(sprite, slide)
        objs[slide] = obj
        pieces = common.split_assembly(obj, layout)
        if i == 0:
            common.export_sprite_model(ROOT, [pieces[TOP]], f"enemies/{TOP}", top["sprites"])
        model = GUN if i == 0 else f"{GUN}-f{i + 1}"
        sprites = [dict(gun["sprites"][0], frames=[frames[i]])]
        common.export_sprite_model(ROOT, [pieces[GUN]], f"enemies/{model}", sprites)
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            img = ROOT / "reference" / "models" / GUN / gun["frames"][i]["image"]
            common.render_preview([pieces[GUN]], str(out.parent / f"{model}.png"), img, size=2)
            if i == 0:
                img = ROOT / "reference" / "models" / TOP / top["frames"][0]["image"]
                common.render_preview([pieces[TOP]], str(out.parent / f"{TOP}.png"), img, size=2)
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56)
        common.render_preview([objs[0]], str(out), ref, size=4)


if __name__ == "__main__":
    main()
