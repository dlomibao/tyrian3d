"""Blue manta tank (newshg.shp frame 163): a 3D version of its sprite.

Seen in episode 2 (levels 2.15 and 2.17). A dark steel-blue ground walker seen from above: a
pointed, domed head with a cyan visor band across it and two red eyes low on its face, sitting
on two broad swept haunches that reach down to the bottom corners, where red lamps glow. A light
ridge runs down the inside of each haunch, and a notch opens between them at the back.

Run: blender --background --python assets/blender/enemies/newshg-163.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b077 as L  # noqa: E402

NAME = "newshg-163"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = L.Grid(24, 28)
U = L.U


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(55, metallic=0.4, roughness=0.4),  # 0 head steel blue
        pal(53, metallic=0.35, roughness=0.5),  # 1 haunches, darker blue
        pal(57, metallic=0.45, roughness=0.35),  # 2 light ridges
        pal(50, metallic=0.3, roughness=0.6),  # 3 dark band and groove
        pal(137, emission_strength=2.5),  # 4 cyan visor
        pal(118, emission_strength=4.0),  # 5 red eyes and lamps
        pal(60, metallic=0.5, roughness=0.3),  # 6 pale highlights at the haunch tips
        pal(52, metallic=0.3, roughness=0.55),  # 7 skirt underside
    ]
    HEAD, HAUNCH, RIDGE, DARK, VISOR, RED, PALE, SKIRT = range(8)
    bm = bmesh.new()

    # Skirt: the whole lower silhouette as a low plate (pixel edges, left half mirrored).
    left = [(12, 13.0), (4.3, 13.4), (3.3, 14.3), (2.2, 15.3), (1.2, 16.3), (0.3, 17.3), (0.3, 26.7),
            (5.8, 26.7), (7.8, 25.7), (9.8, 24.7), (10.8, 23.7), (12, 22.7)]
    right = [(24 - c, r) for c, r in reversed(left)]
    outline = [(G.ex(c), G.ey(r)) for c, r in left[1:-1] + [(12, 22.7)] + right[1:-1] + [(12, 13.0)]]
    L.prism(bm, outline, 0.0, 0.08, mat_index=SKIRT)

    # Head: a pointed dome from the tip (row 4) to its widest at row 12, tapering into a keel
    # between the haunches down to the notch (row 22).
    head = [(4.2, 0.0, 0.0, 0.10), (5.0, 1.4, 0.09, 0.10), (6.5, 2.8, 0.15, 0.10), (8.0, 4.4, 0.21, 0.08),
            (9.5, 6.0, 0.25, 0.06), (11.0, 7.5, 0.27, 0.04), (12.5, 8.3, 0.27, 0.03), (14.0, 7.6, 0.26, 0.02),
            (15.5, 5.4, 0.23, 0.02), (17.5, 3.6, 0.2, 0.02), (20.0, 3.0, 0.16, 0.02), (22.0, 2.0, 0.11, 0.02),
            (22.8, 0.0, 0.0, 0.04)]
    first = len(bm.faces)
    common.loft(bm, [(G.y(r), w * U, h, z) for r, w, h, z in head], sides=14, mat_index=HEAD)
    L.set_smooth(bm, first)
    # A dark band across the face under the eyes (rows 13-14).
    first = len(bm.faces)
    common.loft(bm, [(G.y(13.5), 7.85 * U, 0.262, 0.02), (G.y(13.9), 7.9 * U, 0.264, 0.02),
                     (G.y(14.5), 7.3 * U, 0.258, 0.02), (G.y(14.9), 6.8 * U, 0.254, 0.02)],
                sides=14, mat_index=DARK, cap_start=False, cap_end=False)
    L.set_smooth(bm, first)

    # Haunches: broad swept mounds from beside the face out to the bottom corners.
    for side in (-1, 1):
        def pt(c, r):
            x = G.x(c)
            return (x if side < 0 else -x, G.y(r))
        path = [(10.8, 14.6, 0.0, 0.0), (9.4, 16.4, 3.4, 0.15), (7.2, 19.0, 5.4, 0.18),
                (5.0, 21.6, 5.7, 0.18), (3.2, 24.0, 4.3, 0.15), (1.8, 25.6, 2.5, 0.11), (1.2, 26.3, 0.0, 0.0)]
        L.sweep(bm, [(*pt(c, r), 0.04, w * U, h) for c, r, w, h in path], sides=12, mat_index=HAUNCH)
        # Light ridge down the inside of the haunch (the pale V on the sprite).
        ridge = [(11.0, 17.0, 0.17), (9.6, 19.0, 0.185), (8.0, 21.0, 0.185), (6.6, 22.6, 0.165), (5.6, 23.4, 0.13)]
        L.sweep(bm, [(*pt(c, r), z, 0.7 * U, 0.03) for c, r, z in ridge], sides=6, mat_index=RIDGE)
        # Light outer edge of the haunch (rows 16-23 along column 1).
        edge = [(2.5, 15.6, 0.07), (1.4, 17.0, 0.1), (0.9, 19.5, 0.1), (0.9, 23.5, 0.09)]
        L.sweep(bm, [(*pt(c, r), z, 0.6 * U, 0.03) for c, r, z in edge], sides=6, mat_index=RIDGE)
        # Pale tip and the red lamp in the corner.
        L.blob(bm, (*pt(6.0, 23.2), 0.13), (1.3 * U, 0.9 * U, 0.05), segments=8, rings=4, mat_index=PALE)
        L.blob(bm, (*pt(1.2, 25.6), 0.08), (1.4 * U, 1.1 * U, 0.06), segments=8, rings=4, mat_index=RED)
        # Red eye low on the face (columns 8-9, rows 14-16).
        L.blob(bm, (*pt(8.8, 15.0), 0.18), (1.3 * U, 1.4 * U, 0.07), segments=10, rings=5, mat_index=RED)

    # Cyan visor band across the head at row 8, split in the middle.
    for side in (-1, 1):
        x0, x1 = 0.7 * U, 4.6 * U
        L.sweep(bm, [(side * x0, G.y(8.0), 0.285, 0.0, 0.0), (side * (x0 + 0.3 * U), G.y(8.0), 0.285, 0.7 * U, 0.03),
                     (side * (x0 + x1) / 2, G.y(8.0), 0.255, 0.7 * U, 0.03),
                     (side * x1, G.y(8.0), 0.17, 0.7 * U, 0.03), (side * (x1 + 0.4 * U), G.y(8.0), 0.13, 0.0, 0.0)],
                sides=6, mat_index=VISOR)
    # Pale crest at the tip of the head (row 5).
    L.blob(bm, (0.0, G.y(5.6), 0.2), (1.0 * U, 1.0 * U, 0.04), segments=8, rings=4, mat_index=RIDGE)

    L.clip_below(bm, 0.0)
    return L.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = L.preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], str(out), ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
