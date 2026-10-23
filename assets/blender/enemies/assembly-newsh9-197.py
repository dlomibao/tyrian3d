"""Grey armoured shell (newsh9.shp, assembly of 8 pieces): a 3D version of its sprites.

A ground structure in level 4.18. Eight 2x2 enemies side by side make one 96x56 px object
(sprite.json `assemblyLayout`): two big glossy domes at the back, each over a collar of layered
armour scales that sweep out and down to three claw-like points on each side, a rounded shoulder
plate beside each dome's foot, and a broad curved shield across the front between them. It's
grey metal throughout, shaded only by its own shape.

The whole object is built once in assembly coordinates (left half, mirrored about pixel column 48,
the sprite's axis, plus the shield across the middle), then cut into the eight pieces with
common.split_assembly. None of the pieces is animated (one frame each).

Run: blender --background --python assets/blender/enemies/assembly-newsh9-197.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b088 as lib  # noqa: E402

NAME = "assembly-newsh9-197"
ROOT = common.repo_root(__file__)
PIECES = ["newsh9-197", "newsh9-199", "newsh9-201", "newsh9-203",
          "newsh9-159", "newsh9-161", "newsh9-163", "newsh9-165"]
# Assembly pixel (0, 0) is the top-left corner of newsh9-159 (screen cx 132 - 12, cy -18 - 14);
# the object is 96 x 56 px and its centre (screen 168, -4) is the Blender origin.
CX0, CY0 = 168, -4
G = lib.Grid(48, 28)  # pixel edges
AXIS = 48.5  # mirror symmetric about the centre of pixel column 48


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh9_197"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.55, roughness=0.25),  # 0 glossy domes
        pal(6, metallic=0.45, roughness=0.4),  # 1 collar scales
        pal(5, metallic=0.4, roughness=0.45),  # 2 middle scales
        pal(4, metallic=0.4, roughness=0.5),  # 3 lowest scales
        pal(8, metallic=0.5, roughness=0.35),  # 4 shoulder plates
        pal(6, metallic=0.45, roughness=0.4),  # 5 front shield (same grey as the collar)
        pal(10, metallic=0.6, roughness=0.3),  # 6 light rims
        pal(3, metallic=0.3, roughness=0.6),  # 7 dark undersides and walls
        pal(8, metallic=0.5, roughness=0.35),  # 8 ridges along the claws
    ]
    DOME, COLLAR, MID, LOW, SHOULDER, SHIELD, RIM, DARK, RIDGE = range(9)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----

    # Lowest scale, ending in the claw at the bottom-left (tip at column 11, row 54).
    lib.pillow(bm, G, [(11, 54), (11.2, 50), (12, 47), (12.4, 43), (13, 41), (16, 39.2), (22, 38),
                       (29, 39), (29, 46), (25, 49), (17, 49.6), (14, 51), (12.2, 53)],
               [(11.6, 52.5), (14.5, 46), (20, 42.5), (26, 42)], 0.04, 0.2, mat=LOW, wall_mat=DARK)
    # Middle scale: a thin claw down the left side (tip at column 4, row 49) and a broad plate
    # under the collar.
    lib.pillow(bm, G, [(4, 49), (4, 45), (4, 41), (4.6, 38.5), (5.6, 36), (6.8, 34), (8, 31.8),
                       (9, 30.5), (12, 29), (16, 28), (22, 27.5), (28, 28), (29, 36), (26, 39.5),
                       (20, 38.6), (14, 40.3), (9.2, 40.8), (7.6, 42.4), (6.2, 44), (5.2, 46.5),
                       (5, 49)],
               [(4.6, 47.5), (6.5, 41), (10, 36.5), (16, 34), (25, 33)], 0.05, 0.24, mat=MID, wall_mat=DARK)
    # Collar scale under the dome, sweeping out to the claw at the far left (tip at column 1,
    # row 35).
    lib.pillow(bm, G, [(1, 35), (1, 30), (1, 21), (2, 19), (3, 18), (4.2, 16.8), (6, 14.6),
                       (10, 13), (16, 14), (25, 16.5), (30, 19.5), (36, 22.6), (40, 24.4),
                       (40, 27.6), (36, 28.4), (30, 28.4), (22, 28.3), (16, 28.8), (12, 29.4),
                       (9, 30.2), (7, 30.6), (5, 31.2), (3.2, 32.6), (2, 34.4)],
               [(1.8, 33.2), (4, 27), (8, 23), (16, 22), (27, 23.5), (37.5, 26)],
               0.06, 0.3, mat=COLLAR, wall_mat=DARK)
    # Shoulder plate beside the dome's foot, a rounded tile with a light rim.
    lib.pillow(bm, G, [(25, 28.4), (32, 27.6), (38, 27.6), (41, 28.6), (43, 30.2), (44.2, 32.4),
                       (44.6, 34.4), (43.4, 36.6), (40.4, 39.2), (36, 41.2), (29.5, 41.6),
                       (26.2, 40.2), (25, 37), (24.6, 32)],
               [(34, 33.5)], 0.08, 0.38, mat=SHOULDER, wall_mat=DARK)
    lib.sweep(bm, G, [(27.5, 29.0, 0.17, 0.0, 0.0), (29, 28.7, 0.19, 0.6, 0.04), (37.5, 28.5, 0.2, 0.7, 0.045),
                      (40.5, 29.6, 0.2, 0.7, 0.045), (42.4, 31.7, 0.19, 0.7, 0.045), (43.2, 34.2, 0.17, 0.6, 0.04),
                      (42.4, 36.4, 0.15, 0.0, 0.0)], sides=6, mat=RIM)
    # The dome, peaking a little behind its middle.
    lib.pillow(bm, G, [(20, 4), (26.5, 3.8), (33, 4), (35.5, 5), (37.5, 6.4), (39, 8), (40.2, 10.5),
                       (40.8, 13.5), (42, 17.5), (42.8, 21), (42, 24), (39.5, 25.4), (36, 25.2),
                       (32.8, 23.6), (29, 21), (25, 18.6), (20, 17.6), (14, 17.6), (10.2, 17),
                       (8.4, 15.2), (8.2, 13), (9.6, 11.2), (11.4, 9.4), (13.6, 7.4), (16, 5.8),
                       (18, 4.8)],
               [(27, 11.5)], 0.1, 0.64, mat=DOME, wall_mat=DARK,
               rings=(1.0, 0.94, 0.85, 0.72, 0.56, 0.38, 0.18))
    # Light lip where the dome meets the collar.
    lib.sweep(bm, G, [(11, 17.8, 0.24, 0.0, 0.0), (12.5, 18.0, 0.26, 0.6, 0.04), (20, 18.4, 0.29, 0.7, 0.045),
                      (25, 19.4, 0.3, 0.7, 0.045), (29, 21.8, 0.3, 0.7, 0.045), (33, 24.2, 0.28, 0.7, 0.045),
                      (36.5, 25.6, 0.24, 0.6, 0.04), (38.5, 25.9, 0.2, 0.0, 0.0)], sides=6, mat=RIM)

    # Light ridges along the claws (the bright diagonal streaks on each scale).
    lib.sweep(bm, G, [(1.8, 33.4, 0.22, 0.0, 0.0), (3, 31, 0.27, 0.6, 0.04), (6.5, 26.5, 0.3, 0.6, 0.04),
                      (10.5, 23.6, 0.3, 0.0, 0.0)], sides=6, mat=RIDGE)
    lib.sweep(bm, G, [(4.6, 48, 0.16, 0.0, 0.0), (5.2, 45, 0.21, 0.6, 0.035), (7, 40, 0.24, 0.6, 0.04),
                      (10.5, 36.4, 0.25, 0.6, 0.04), (13.5, 34.2, 0.25, 0.0, 0.0)], sides=6, mat=RIDGE)
    lib.sweep(bm, G, [(11.5, 53, 0.13, 0.0, 0.0), (12.4, 50, 0.17, 0.6, 0.035), (14.8, 46, 0.2, 0.6, 0.035),
                      (19, 43, 0.2, 0.0, 0.0)], sides=6, mat=RIDGE)

    lib.mirror_all(bm, G.x(AXIS))

    # ---- centre: the front shield between the shoulder plates, high at its back edge ----
    left = [(48.5, 33.8), (44, 34.2), (38, 35.6), (30, 37.5), (25.2, 40.5), (24.6, 45), (25, 49),
            (26, 50), (27, 51), (29, 52), (32, 53), (35, 54), (38, 55), (41.5, 56)]
    right = [(2 * AXIS - c, r) for c, r in reversed(left[1:])]
    lib.pillow(bm, G, left + right, [(40, 39.5), (57, 39.5)], 0.06, 0.34, mat=SHIELD, wall_mat=DARK,
               rings=(1.0, 0.9, 0.76, 0.58, 0.38, 0.18))
    # Light rim along its back edge.
    lib.sweep(bm, G, [(36, 36.6, 0.2, 0.0, 0.0), (38, 36.0, 0.22, 0.6, 0.035), (44, 34.9, 0.24, 0.7, 0.04),
                      (48.5, 34.6, 0.24, 0.7, 0.04), (53, 34.9, 0.24, 0.7, 0.04), (59, 36.0, 0.22, 0.6, 0.035),
                      (61, 36.6, 0.2, 0.0, 0.0)], sides=6, mat=RIM)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES[0], PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = lib.composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 96, 112, 0, 0)
        common.render_preview([obj], str(out), ref, size=8, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
