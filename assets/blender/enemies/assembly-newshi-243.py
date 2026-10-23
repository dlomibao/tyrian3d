"""Red bomber (newshi.shp, assembly of 6 pieces): a 3D version of its sprites.

Seen in episode 1 (levels 1.10, 1.29) and episode 3 (3.21). Six 2x2 enemies make one 96x56 px
plane flying down the screen (sprite.json `assemblyLayout`; the seventh entry, newshf-123, is an
unrelated small fighter flying beside it). Its nose is a separate enemy, newshi-278, modelled on
its own to continue the fuselage below. The plane has a red fuselage with a grey spine that swells
into a bright hump, two dark cockpit windows near the nose, a grey tail cone with a thin tail fin,
two grey engine pods with red side cowls and red front lips mounted beside the tail, and long
wings: grey root blocks with raised rails, red inner panels, a grey spar and grey outer wings
with red vent ribs, ending in rounded grey tip pods.

The whole plane is built once in assembly coordinates (left half, mirrored about pixel column 48,
the sprite's axis), then cut into the pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshi-243.py [-- --preview out.png]
(the preview is the whole plane; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b047 as lib  # noqa: E402

NAME = "assembly-newshi-243"
ROOT = common.repo_root(__file__)
PIECES = ["newshi-201", "newshi-203", "newshi-237", "newshi-239", "newshi-241", "newshi-243"]
# Assembly pixel (0, 0) is the top-left corner of newshi-237's top row neighbour (screen x 115,
# y -25); the plane spans columns 2-94 and rows 3-55 and is symmetric about column 48 (screen
# x 163.5). Blender X = 0 is that axis, Y = 0 the assembly's vertical centre (screen y 3).
AXIS_SCREEN_X, MID_SCREEN_Y = 163.5, 3
G = lib.Grid(axis=48, mid=28)


def body_top(x_px, hw=9.6, hh=0.22):
    """Height of the fuselage's upper surface at x_px pixels from the axis."""
    t = max(0.0, 1 - (x_px / hw) ** 2)
    return hh * t ** 0.5


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshi243"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(70, metallic=0.3, roughness=0.45),  # 0 red fuselage
        pal(69, metallic=0.3, roughness=0.5),  # 1 red wing panels and cowls
        pal(72, metallic=0.3, roughness=0.4),  # 2 light red ribs and nose ridge
        pal(67, metallic=0.2, roughness=0.6),  # 3 deep red seams
        pal(4, metallic=0.5, roughness=0.5),  # 4 dark grey wing and root block
        pal(6, metallic=0.6, roughness=0.4),  # 5 grey rails, tail cone, spar
        pal(8, metallic=0.65, roughness=0.35),  # 6 light grey engine pods, wing tips
        pal(10, metallic=0.7, roughness=0.3),  # 7 bright grey hump and rail tops
        pal(2, metallic=0.6, roughness=0.15),  # 8 dark glass windows, vent slots
    ]
    RED, PANEL, RIB, SEAM, DGREY, GREY, LGREY, BRIGHT, GLASS = range(9)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----

    # Wing: one thin dark grey plate from the root block out to the rounded tip (rows 29-41),
    # its leading edge sweeping back from column 16 to the root (the diagonal from row 42 to 51).
    wing = [(27.6, 29.5), (5.0, 29.5), (3.5, 30.5), (2.5, 32.0), (2.5, 36.5), (3.5, 38.0),
            (5.0, 39.5), (7.0, 40.2), (10.0, 40.8), (16.5, 41.5), (27.6, 47.55)]
    lib.plate(bm, G, wing, -0.035, 0.035, mat=DGREY)
    # Rounded grey tip pod (columns 3-7).
    lib.loft_y(bm, G, 5.2, [(29.7, 0.0, 0.0, 0.01), (30.2, 1.8, 0.045, 0.01), (31.3, 2.6, 0.065, 0.01),
                            (37.5, 2.6, 0.065, 0.01), (38.8, 1.9, 0.05, 0.01), (39.7, 0.0, 0.0, 0.01)],
               sides=10, mat=LGREY)
    # Vent slots with red ribs (rows 30-34, ribs at columns 9, 11, 13, 15).
    lib.rect(bm, G, 7.8, 29.8, 16.2, 34.6, 0.035, 0.04, mat=GLASS)
    for c in (9, 11, 13, 15):
        lib.rect(bm, G, c - 0.5, 29.9, c + 0.5, 34.6, 0.035, 0.06, mat=RED)
    # Grey spar along the wing (rows 35-36) into the upright bar at columns 16-18.
    lib.sweep(bm, G, [(6.5, 35.8, 0.03, 0.0, 0.0), (7.0, 35.8, 0.03, 1.0, 0.035),
                      (16.5, 35.8, 0.03, 1.0, 0.035)], sides=8, mat=GREY)
    lib.loft_y(bm, G, 17.3, [(29.8, 1.3, 0.05, 0.02), (41.6, 1.3, 0.05, 0.02)], sides=8, mat=GREY)
    # Dark recess with two small red lamps under the spar (rows 38-40).
    lib.rect(bm, G, 8.5, 37.6, 15.6, 40.4, 0.035, 0.04, mat=GLASS)
    lib.rect(bm, G, 9.5, 37.7, 10.5, 40.4, 0.035, 0.055, mat=RIB)
    lib.rect(bm, G, 13.5, 37.7, 15.0, 40.4, 0.035, 0.055, mat=RIB)

    # Red inner wing panel (columns 19-28) with ribs at its back and a light bar across (row 36).
    lib.plate(bm, G, [(18.6, 29.7), (27.8, 29.7), (27.8, 47.5), (18.6, 42.9)], 0.02, 0.06, mat=PANEL)
    for c in (20, 22, 24, 26):
        lib.rect(bm, G, c - 0.4, 29.8, c + 0.4, 34.6, 0.06, 0.075, mat=RED)
    lib.rect(bm, G, 18.7, 35.6, 27.8, 36.5, 0.06, 0.075, mat=RED)
    lib.rect(bm, G, 23.6, 37.0, 24.4, 44.0, 0.06, 0.066, mat=SEAM)

    # Grey root block between the wing panel and the fuselage (columns 28-38), running down the
    # side of the nose as a strake to row 55, with two raised rails joined by a crossbar (the H).
    root = [(27.5, 29.5), (38.6, 29.5), (38.6, 52.0), (37.8, 55.5), (34.6, 55.5), (34.6, 51.0),
            (31.0, 49.3), (29.4, 48.4), (27.5, 47.5)]
    lib.plate(bm, G, root, -0.1, 0.08, mat=DGREY)
    lib.loft_y(bm, G, 29.6, [(29.6, 1.1, 0.04, 0.09), (46.8, 1.1, 0.04, 0.09), (47.6, 0.0, 0.0, 0.09)],
               sides=8, mat=GREY)
    lib.loft_y(bm, G, 33.0, [(29.6, 1.6, 0.05, 0.09), (47.6, 1.6, 0.05, 0.09), (48.6, 0.0, 0.0, 0.09)],
               sides=8, mat=BRIGHT)
    lib.rect(bm, G, 30.4, 35.5, 31.6, 36.6, 0.06, 0.125, mat=GREY)
    # Grey flank on the fuselage beside the hump (columns 39-41, rows 33-42).
    lib.rect(bm, G, 37.0, 32.6, 41.6, 43.4, -0.06, 0.17, mat=DGREY)

    # Engine pod beside the tail (columns 29-41, rows 7-22): a grey cylinder (columns 33-38)
    # between red side cowls, a red lip at its front and a slanted grey fin outside.
    lib.loft_y(bm, G, 35.5, [(7.4, 0.0, 0.0, 0.08), (7.9, 1.9, 0.1, 0.08), (8.8, 2.8, 0.15, 0.08),
                             (10.0, 3.1, 0.17, 0.08), (18.4, 3.1, 0.17, 0.08)], sides=12, mat=LGREY)
    lib.sweep(bm, G, [(35.6, 18.0, 0.07, 3.1, 0.15), (35.4, 19.4, 0.06, 2.9, 0.13), (35.0, 20.5, 0.04, 2.6, 0.1),
                      (34.6, 21.4, 0.02, 2.0, 0.07), (34.4, 21.9, 0.01, 0.0, 0.0)], sides=12, mat=RED)
    lib.loft_y(bm, G, 30.8, [(10.4, 0.0, 0.0, 0.06), (10.8, 1.6, 0.1, 0.06), (11.6, 2.1, 0.14, 0.06),
                             (16.8, 2.1, 0.14, 0.06), (17.7, 1.3, 0.1, 0.06), (18.0, 0.0, 0.0, 0.06)],
               sides=8, mat=PANEL)
    lib.loft_y(bm, G, 40.3, [(10.4, 0.0, 0.0, 0.06), (10.8, 1.4, 0.1, 0.06), (11.6, 1.9, 0.14, 0.06),
                             (17.3, 1.9, 0.14, 0.06), (18.2, 1.2, 0.1, 0.06), (18.6, 0.0, 0.0, 0.06)],
               sides=8, mat=PANEL)
    lib.plate(bm, G, [(25.5, 7.6), (27.5, 7.6), (28.6, 12.5), (28.6, 15.6), (27.6, 15.6), (26.5, 12.5),
                      (25.5, 10.5)], 0.0, 0.13, mat=GREY)

    # Ribs across the fuselage's shoulders (rows 24-28), following its surface.
    for r in (25.0, 26.8):
        lib.sweep(bm, G, [(39.6 + i * 1.2, r, body_top(48 - (39.6 + i * 1.2)) - 0.01, 0.45, 0.035)
                          for i in range(6)], sides=6, mat=RIB)
    # Dark cockpit window near the nose (columns 40-44, rows 44-50).
    lib.ellipsoid(bm, G, 42.2, 47.2, body_top(5.8) - 0.03, 2.6, 3.6, 0.07, mat=GLASS, segments=14, rings=7)

    lib.mirror_all(bm)

    # ---- centre parts ----

    # Grey tail cone (rows 6-23) running into the red fuselage (rows 23-55, continued by the nose).
    lib.loft_y(bm, G, 48, [(5.6, 0.0, 0.0, 0.06), (6.2, 2.0, 0.08, 0.06), (7.5, 3.5, 0.12, 0.05),
                           (9.5, 4.6, 0.15, 0.04), (12.0, 5.3, 0.17, 0.03), (15.0, 5.8, 0.18, 0.02),
                           (18.0, 6.0, 0.19, 0.02), (24.0, 6.0, 0.2, 0.0)], sides=12, mat=LGREY)
    lib.loft_y(bm, G, 48, [(22.5, 4.5, 0.14, 0.0), (23.5, 6.5, 0.18, 0.0), (25.0, 8.0, 0.2, 0.0),
                           (26.5, 9.2, 0.22, 0.0), (28.0, 9.6, 0.22, 0.0), (57.0, 9.6, 0.22, 0.0)],
               sides=16, mat=RED)
    # Grey spine along the back (rows 21-33) swelling into a bright hump (rows 33-40).
    lib.loft_y(bm, G, 48, [(20.5, 3.6, 0.09, 0.15), (24.0, 3.0, 0.08, 0.2), (29.0, 3.6, 0.1, 0.21),
                           (33.6, 3.8, 0.1, 0.21)], sides=10, mat=GREY)
    lib.loft_y(bm, G, 48, [(32.4, 0.0, 0.0, 0.2), (32.8, 3.4, 0.1, 0.2), (34.0, 4.6, 0.14, 0.2),
                           (38.6, 4.6, 0.14, 0.2), (39.8, 3.4, 0.09, 0.2), (40.4, 0.0, 0.0, 0.2)],
               sides=12, mat=BRIGHT)
    # Small grey sensor in front of the hump (rows 41-42).
    lib.ellipsoid(bm, G, 48, 41.6, 0.22, 1.6, 1.1, 0.05, mat=BRIGHT, segments=10, rings=5)
    # Light red ridge down the nose (columns 45-51, rows 44-55).
    lib.loft_y(bm, G, 48, [(43.2, 0.0, 0.0, 0.19), (43.8, 2.6, 0.04, 0.19), (45.0, 3.4, 0.06, 0.19),
                           (57.0, 3.4, 0.06, 0.19)], sides=10, mat=RIB)
    # Thin tail fin standing up from the cone (column 48, rows 3-10).
    lib.vfin(bm, G, 48, [(10.5, 0.12), (3.6, 0.14), (3.6, 0.24), (5.0, 0.33), (10.5, 0.33)], 1.0, mat=LGREY)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, "newshi-243", PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - AXIS_SCREEN_X, e["cy"] - MID_SCREEN_Y) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        screen = [(e["model"], e["cx"], e["cy"]) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
        ref = lib.composite_png(ROOT, screen, Path(tempfile.mkdtemp()) / "assembly.png", 163, 3, 96, 112)
        common.render_preview([obj], str(out), ref, size=8, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
