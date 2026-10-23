"""Grey shield gunship (newshs.shp frames 93, 131): a 3D version of its sprite.

Seen in episode 1 (level 23) and episode 3 (level 2). A dark grey, shield-shaped craft flying
nose down the screen: a wide back plate between two side rails with red lamps at their top
corners, a raised trapezoid panel narrowing into an armoured head in the middle, a cross seam
(row 14) and a V-shaped lower hull carrying a pod with a long blue canopy.

The head's hatch is shut in frame 93 (a black panel) and open in frame 131 (a glowing red eye),
so there are two models: newshs-93 (frame 93) and newshs-93-f2 (frame 131).

Run: blender --background --python assets/blender/enemies/newshs-93.py [-- --preview out.png]
"""

import copy
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b040 as lib  # noqa: E402

NAME = "newshs-93"
ROOT = common.repo_root(__file__)
AXIS = 12  # column edge the sprite is symmetric about


def ex(e):
    return lib.ex(e)


def ey(e):
    return lib.ey(e)


def row(r):
    return lib.row(r)


def build(sprite, name, eye_open):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(4, metallic=0.45, roughness=0.5),  # 0 base plate sides, lower hull
        pal(3, metallic=0.4, roughness=0.55),  # 1 base plate top (dark grooves and corners)
        pal(5, metallic=0.45, roughness=0.45),  # 2 raised panel, rail sides
        pal(8, metallic=0.5, roughness=0.4),  # 3 rail tops, head sides
        pal(10, metallic=0.55, roughness=0.35),  # 4 head rim, top lip
        pal(115, emission_strength=3.0),  # 5 red corner lamps
        pal(6, metallic=0.45, roughness=0.45),  # 6 pod, wing ridges
        pal(147, metallic=0.3, roughness=0.15, emission_strength=1.0),  # 7 blue canopy
        pal(7, metallic=0.5, roughness=0.4),  # 8 struts
        pal(1, metallic=0.2, roughness=0.7),  # 9 shut hatch (frame 93)
        pal(117, emission_strength=2.5),  # 10 eye rim (frame 131)
        pal(121, emission_strength=5.0),  # 11 eye core (frame 131)
    ]
    BASE, BASE_TOP, PANEL, RAIL_TOP, RIM, LAMP, POD, GLASS, STRUT, HATCH, EYE_RIM, EYE = range(12)
    bm = bmesh.new()

    # Base plate: the shield (rows 3-13, columns 3-20), the seam notch at row 14, the V lower hull.
    base = lib.mirror_outline([(3, 3.0), (3, 13.9), (3.7, 14.2), (3.7, 14.8), (3, 15.1), (9, 21.0), (9, 24.0),
                               (10, 24.4), (10, 26.0), (11, 27.0)], AXIS)
    lib.bevel_prism(bm, base, -0.1, 0.03, 0.03, mat_index=BASE, top_mat=BASE_TOP, bottom_bevel=0.03)

    # Side rails (columns 3-4, rows 2-13) with red lamps at their top inner corners.
    for side in (-1, 1):
        x0, x1 = sorted((side * ex(3), side * ex(5)))
        lib.bevel_prism(bm, [(x0, ey(14.0)), (x1, ey(14.0)), (x1, ey(2.0)), (x0, ey(2.0))], -0.09, 0.11, 0.025,
                        mat_index=PANEL, top_mat=RAIL_TOP)
        lib.dome(bm, side * abs(lib.px(4)), ey(3.0), 0.8 / 12, 1.1 / 12, 0.045,
                 z=0.105, mat_index=LAMP)
        lib.dome(bm, side * abs(lib.px(5)), ey(3.5), 0.5 / 12, 0.5 / 12, 0.03, z=0.025, mat_index=LAMP)

    # Raised trapezoid panel (index 5) narrowing from the top edge into the head.
    panel = lib.mirror_outline([(6, 3.05), (6, 8.0), (8, 10.0), (9, 12.0)], AXIS)
    lib.bevel_prism(bm, panel, 0.0, 0.075, 0.025, mat_index=PANEL)
    # Bright lip along its top edge (row 3).
    lib.box(bm, ex(6), ey(4.0), ex(18), ey(3.05), 0.0, 0.09, mat_index=RIM, bevel=0.02)

    # Armoured head (columns 9-14, rows 7-13) with the hatch on top.
    head = [(ex(9), ey(13.6)), (ex(15), ey(13.6)), (ex(15), ey(7.0)), (ex(9), ey(7.0))]
    lib.bevel_prism(bm, head, 0.0, 0.17, 0.035, mat_index=RAIL_TOP, top_mat=RIM)
    if eye_open:
        # Open hatch: a red rim ring and a glowing core bulging out of it (rows 9-11, columns 10-13).
        lib.dome(bm, 0.0, ey(10.5), 2.15 / 12, 1.7 / 12, 0.055, z=0.15, sides=16, mat_index=EYE_RIM)
        lib.dome(bm, 0.0, ey(10.4), 1.35 / 12, 1.0 / 12, 0.08, z=0.15, sides=12, mat_index=EYE)
    else:
        # Shut hatch: a black panel set into the head's top.
        lib.box(bm, ex(10), ey(12.0), ex(14), ey(9.0), 0.1, 0.175, mat_index=HATCH, bevel=0.01)

    # Light struts beside the head down to the lower hull (columns 7 and 16, rows 12-17).
    for side in (-1, 1):
        x0, x1 = sorted((side * ex(7), side * ex(8)))
        lib.box(bm, x0, ey(17.5), x1, ey(11.5), 0.0, 0.085, mat_index=STRUT, bevel=0.02)
    # Ridges along the lower hull's top edge, either side of the seam (row 14-15, columns 4-7).
    for side in (-1, 1):
        x0, x1 = sorted((side * ex(3.8), side * ex(8)))
        lib.box(bm, x0, ey(15.6), x1, ey(14.4), 0.0, 0.065, mat_index=POD, bevel=0.02)
    # Lower hull wings: a raised V plate (index 4) from the seam into the pod.
    vplate = lib.mirror_outline([(4.0, 15.4), (9.2, 20.6), (9.6, 22.0)], AXIS)
    lib.bevel_prism(bm, vplate, 0.0, 0.05, 0.02, mat_index=BASE)

    # Pod down the centre (columns 9-14, rows 14-26) and its long blue canopy (rows 19-24).
    pod = [(14.2, 2.2, 1.3, 0.04), (15.3, 2.8, 1.9, 0.04), (17.0, 3.0, 2.0, 0.04), (19.0, 2.95, 1.95, 0.03),
           (21.5, 2.8, 1.8, 0.02), (23.5, 2.6, 1.6, 0.02), (24.6, 2.0, 1.3, 0.01), (25.7, 1.3, 0.9, 0.0),
           (26.6, 0.6, 0.45, 0.0), (26.95, 0.0, 0.0, 0.0)]
    common.loft(bm, [(ey(r), w / 12, h / 12, z) for r, w, h, z in pod], sides=12, mat_index=POD)
    canopy = [(18.9, 0.0, 0.0), (19.4, 1.5, 0.6), (20.5, 1.95, 0.85), (23.2, 1.9, 0.85), (24.4, 1.3, 0.6),
              (25.0, 0.0, 0.0)]
    common.loft(bm, [(ey(r), w / 12, h / 12, 0.17) for r, w, h in canopy], sides=12, mat_index=GLASS)

    return common.mesh_object(name, bm, mats, coll, smooth=True)


def subset(sprite, frames):
    sprites = copy.deepcopy(sprite["sprites"])
    for s in sprites:
        s["frames"] = [f for f in s["frames"] if f in frames]
    return [s for s in sprites if s["frames"]]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    for name, frame, eye_open in ((NAME, 0, False), (f"{NAME}-f2", 1, True)):
        obj = build(sprite, name, eye_open)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", subset(sprite, [sprite["frames"][frame]["index"]]))
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            if frame:
                out = out.with_name(f"{out.stem}-f{frame + 1}{out.suffix}")
            ref = ROOT / "reference" / "models" / NAME / sprite["frames"][frame]["image"]
            common.render_preview([obj], str(out), ref, size=2)
            obj.hide_render = True
            obj.hide_set(True)


if __name__ == "__main__":
    main()
