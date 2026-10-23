"""Blue U-shaped craft (newsh^.shp frames 16, 18, 54, 56, an assembly of four pieces): a 3D
version of its sprites.

Seen in episode 4 (levels 4.10, 4.22, 4.50). Four 2x2 enemies make one 48x56 px object
(sprite.json `assemblyLayout`) shaped like a tuning fork: two big blue pods at the top
(newsh-caret-16, -18), each with a grey clamp round its outer side and a light pipe down its back,
run down into thinner struts with a grey rod and a dark grey joint, which bend inward and meet in a
round bar at the bottom (newsh-caret-54, -56). A small blue bulb on a grey stem points up from the
middle of the bar. Every piece has one frame.

The whole object is built once in assembly coordinates (left half, mirrored about the centre of
pixel column 24, the sprite's axis), then cut into the four pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh-caret-54.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from lib_b012 import Grid, sweep, loft_y, plate, ellipsoid, mirror_all, to_object, merged_sprite, composite_png  # noqa: E402

NAME = "assembly-newsh-caret-54"
ROOT = common.repo_root(__file__)
PIECES = ["newsh-caret-16", "newsh-caret-18", "newsh-caret-54", "newsh-caret-56"]
# Assembly pixel (0, 0) is the top-left corner of newsh-caret-16 (screen 157 - 12, 31 - 14); the
# assembly is 48 x 56 px and its centre (screen 169, 45) is the Blender origin.
CX0, CY0 = 169, 45
G = Grid(48, 56)
AXIS_COL = 24  # mirror symmetric about the centre of pixel column 24


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshc54"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(57, metallic=0.35, roughness=0.3),  # 0 blue pod hull
        pal(54, metallic=0.35, roughness=0.35),  # 1 darker blue struts and bar
        pal(60, metallic=0.4, roughness=0.25),  # 2 light blue pipe
        pal(51, metallic=0.2, roughness=0.6),  # 3 dark blue grooves
        pal(5, metallic=0.7, roughness=0.35),  # 4 grey clamp and rod
        pal(3, metallic=0.5, roughness=0.5),  # 5 dark grey joint
        pal(106, metallic=0.7, roughness=0.3),  # 6 light grey edges
        pal(10, metallic=0.8, roughness=0.2),  # 7 bright grey edge
        pal(7, metallic=0.75, roughness=0.3),  # 8 grey stem
        pal(61, metallic=0.4, roughness=0.2),  # 9 pale blue highlights
        pal(56, metallic=0.35, roughness=0.3),  # 10 mid blue bumps
        pal(58, metallic=0.4, roughness=0.25),  # 11 lower arm highlight
    ]
    POD, STRUT, PIPE, GROOVE, GREY, JOINT, LIGHT, BRIGHT, STEM, PALE, BUMP, ARMLIGHT = range(12)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----

    # The pod (columns 7-18, rows 0-21): a rounded top, widest at rows 8-14, running on under
    # the clamp into the strut.
    pod = [(11.6, 0.0, 0.0, 0.0), (11.6, 0.5, 1.5, 0.07), (11.5, 1.3, 2.4, 0.11), (11.1, 2.4, 3.2, 0.15),
           (11.2, 3.6, 4.0, 0.18), (11.2, 5.0, 4.7, 0.205), (11.6, 7.0, 5.2, 0.22), (12.0, 9.5, 5.6, 0.225),
           (12.0, 14.5, 5.6, 0.225), (12.7, 16.5, 5.4, 0.215), (12.7, 21.0, 5.3, 0.2),
           (12.4, 22.6, 4.6, 0.16)]
    sweep(bm, G, [(c, r, 0.0, w, h) for c, r, w, h in pod], sides=14, mat=POD)

    # Strut below the pod (rows 22-31), the dark grey joint (rows 31-36) and the lower arm, which
    # bends inward into the bar along the bottom (rows 45-52) to the middle.
    sweep(bm, G, [(12.4, 22.0, 0.0, 4.6, 0.16), (12.5, 26.0, 0.0, 4.4, 0.15), (13.0, 29.5, 0.0, 4.0, 0.14),
                  (13.6, 31.8, 0.0, 3.8, 0.135)], sides=12, mat=STRUT)
    sweep(bm, G, [(14.0, 31.0, 0.0, 4.2, 0.155), (14.0, 36.6, 0.0, 4.0, 0.15)], sides=12, mat=JOINT, smooth=False)
    sweep(bm, G, [(13.8, 36.0, 0.0, 3.8, 0.135), (13.6, 40.0, 0.0, 3.9, 0.135), (13.9, 43.5, 0.0, 3.8, 0.135),
                  (15.4, 46.8, 0.0, 3.6, 0.13), (18.4, 48.9, 0.0, 3.1, 0.125), (21.2, 49.7, 0.0, 2.7, 0.12),
                  (AXIS_COL, 50.0, 0.0, 2.6, 0.12)], sides=12, mat=STRUT, cap_end=False)

    # A small blister on the inner side of the pod (columns 18-19, rows 10-14) and a nub beside
    # the strut (columns 17-20, rows 22-30).
    ellipsoid(bm, G, 17.6, 12.0, 0.02, 2.0, 2.8, 0.12, mat=BUMP)
    ellipsoid(bm, G, 18.6, 26.2, 0.0, 2.3, 4.6, 0.12, mat=BUMP)

    # Grey clamp round the outer side of the pod (columns 5-14, rows 17-21): a block sticking out
    # past the pod with a light top edge and a bright inner edge.
    plate(bm, G, [(5, 17), (15, 17), (15, 22), (5, 22)], -0.17, 0.245, mat=GREY)
    plate(bm, G, [(5, 17), (14, 17), (14, 18), (5, 18)], 0.245, 0.265, mat=LIGHT)
    plate(bm, G, [(14, 17), (15, 17), (15, 22), (14, 22)], 0.245, 0.27, mat=BRIGHT)

    # Light pipe down the back of the pod (column 12, rows 12-19), across the clamp to column 8 and
    # on down to the strut, and the dark groove it comes out of (column 9, rows 4-11).
    sweep(bm, G, [(12.0, 11.6, 0.215, 0.0, 0.0), (12.0, 12.2, 0.215, 0.7, 0.035), (12.0, 16.6, 0.21, 0.7, 0.035),
                  (12.0, 19.0, 0.27, 0.7, 0.035), (8.2, 19.0, 0.27, 0.7, 0.035), (8.0, 21.6, 0.2, 0.7, 0.035),
                  (8.4, 23.0, 0.12, 0.6, 0.03), (8.6, 23.6, 0.1, 0.0, 0.0)], sides=6, mat=PIPE)
    sweep(bm, G, [(9.6, 3.6, 0.16, 0.0, 0.0), (9.4, 4.4, 0.18, 0.6, 0.03), (9.0, 7.0, 0.2, 0.6, 0.03),
                  (9.0, 11.0, 0.2, 0.6, 0.03), (10.4, 11.2, 0.215, 0.6, 0.03), (11.8, 11.2, 0.225, 0.6, 0.03),
                  (12.4, 11.2, 0.225, 0.0, 0.0)], sides=6, mat=GROOVE)
    # The highlight down the inner flank of the pod (column 14, rows 4-11).
    sweep(bm, G, [(14.0, 3.6, 0.17, 0.0, 0.0), (14.0, 4.6, 0.19, 0.6, 0.03), (14.2, 10.8, 0.2, 0.6, 0.03),
                  (14.2, 11.6, 0.2, 0.0, 0.0)], sides=6, mat=PALE)

    # Grey rod down the strut (columns 12-13, rows 22-30), slanting through the joint to columns
    # 15-16 and on down the lower arm to the bar.
    sweep(bm, G, [(12.5, 21.8, 0.17, 1.1, 0.045), (12.5, 30.0, 0.15, 1.1, 0.045), (14.4, 33.2, 0.165, 1.0, 0.045),
                  (14.9, 34.6, 0.16, 0.0, 0.0)], sides=6, mat=LIGHT)
    sweep(bm, G, [(14.4, 33.0, 0.165, 0.0, 0.0), (14.6, 33.6, 0.165, 1.0, 0.045), (15.4, 36.8, 0.14, 1.0, 0.045),
                  (15.4, 44.0, 0.13, 1.0, 0.045), (15.9, 45.6, 0.11, 0.0, 0.0)], sides=6, mat=GREY)
    # Highlight down the lower arm (column 13, rows 37-44).
    sweep(bm, G, [(12.9, 36.6, 0.12, 0.0, 0.0), (12.9, 37.4, 0.13, 0.7, 0.03), (12.9, 43.0, 0.13, 0.7, 0.03),
                  (13.3, 44.4, 0.12, 0.0, 0.0)], sides=6, mat=ARMLIGHT)

    # Light collar on top of the bar beside the stem (columns 18-20, rows 45-48).
    ellipsoid(bm, G, 19.0, 46.6, 0.04, 1.7, 1.8, 0.11, mat=BUMP)
    ellipsoid(bm, G, 19.0, 46.4, 0.07, 1.4, 0.8, 0.09, mat=PALE)

    mirror_all(bm, G.X(AXIS_COL))

    # ---- centre parts ----

    # Grey stem (rows 43-47) with the blue bulb on top (rows 36-42), pointing up the screen.
    loft_y(bm, G, AXIS_COL, [(42.0, 1.5, 0.08, 0.02), (47.6, 1.8, 0.09, 0.02)], sides=10, mat=STEM)
    loft_y(bm, G, AXIS_COL, [(36.3, 0.0, 0.0, 0.03), (37.0, 1.4, 0.07, 0.03), (38.4, 2.4, 0.11, 0.03),
                             (40.6, 2.6, 0.115, 0.03), (42.2, 2.0, 0.09, 0.03), (43.0, 0.0, 0.0, 0.03)],
           sides=12, mat=BUMP)
    ellipsoid(bm, G, AXIS_COL - 0.6, 38.8, 0.1, 0.9, 1.6, 0.05, mat=PALE)
    # Glossy highlight on the middle of the bar (rows 49-50).
    ellipsoid(bm, G, AXIS_COL, 49.6, 0.07, 3.6, 1.2, 0.06, mat=PALE)

    return to_object(NAME, bm, mats, coll)


def main():
    sprite = merged_sprite(ROOT, PIECES)
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
        ref = composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
