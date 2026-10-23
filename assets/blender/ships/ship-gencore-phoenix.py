"""Gencore Phoenix (player ship, tyrian.shp#8 sprite 157 and its banking frames 153-161).

A grey fighter: a long fuselage with a pointed nose, a dark cockpit slot behind the nose and a
light canopy panel, and two blade-like side pods (taller than they are wide, as the banking
frames show) joined to the fuselage by struts near the tail.

Run: blender --background --python assets/blender/ships/ship-gencore-phoenix.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import common  # noqa: E402
from lib_b001 import box, loft_path, mirrored, px, row  # noqa: E402

NAME = "ship-gencore-phoenix"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.55, roughness=0.4),  # 0 hull grey
        pal(4, metallic=0.45, roughness=0.5),  # 1 dark grey (belly, lower sides)
        pal(8, metallic=0.55, roughness=0.38),  # 2 pod grey
        pal(11, metallic=0.6, roughness=0.3),  # 3 light panels and ridges
        pal(2, metallic=0.2, roughness=0.2),  # 4 dark cockpit slot and vents
        pal(13, metallic=0.6, roughness=0.25),  # 5 bright highlights
        pal(10, metallic=0.55, roughness=0.3),  # 6 canopy panel
    ]
    HULL, DARK, POD, LIGHT, SLOT, BRIGHT, CANOPY = range(7)
    bm = bmesh.new()

    # Fuselage, nose (row 1) to tail (row 25): (row, half width px, half height px, z centre px).
    hull = [(1.2, 0, 0, 0.6), (2, 1.1, 1.0, 0.6), (4, 2.1, 1.7, 0.6), (6, 3.0, 2.2, 0.5),
            (8.4, 3.1, 2.3, 0.4), (9, 4.0, 2.5, 0.3), (12, 4.3, 2.7, 0.3), (15.4, 4.1, 2.6, 0.2),
            (16.2, 3.4, 2.4, 0.1), (19, 3.6, 2.3, 0.0), (21.5, 3.4, 2.1, 0.0), (23, 2.4, 1.6, 0.0),
            (24.4, 1.4, 1.1, 0.0), (25, 0, 0, 0.0)]
    common.loft(bm, [(row(r), w * P, h * P, z * P) for r, w, h, z in hull], sides=14, mat_index=HULL)

    # Belly keel: the darker lower half of the fuselage, a flatter slab under it.
    common.loft(bm, [(row(r), w * 0.85 * P, h * 0.45 * P, (z - h * 0.55) * P) for r, w, h, z in hull[2:-1]],
                sides=10, mat_index=DARK)

    def top(r):
        """Height of the fuselage top on the centreline at row r (px)."""
        for (r0, _, h0, z0), (r1, _, h1, z1) in zip(hull, hull[1:]):
            if r0 <= r <= r1:
                t = (r - r0) / (r1 - r0)
                return (h0 + z0) * (1 - t) + (h1 + z1) * t
        return 0.0

    # Nose highlight (row 3-7, column 11): a light ridge along the top of the nose cone.
    loft_path(bm, [(row(r), px(11.5), 0.8 * P, 0.6 * P, (top(r) - 0.3) * P) for r in (2.6, 4, 5.5, 7.3)],
              sides=6, mat_index=LIGHT)
    # Dark cockpit slot across the fuselage (rows 8-9, columns 10-13).
    loft_path(bm, [(row(7.9), px(11.5), 0, 0, (top(8.5) - 0.3) * P),
                   (row(8.3), px(11.5), 2.0 * P, 0.7 * P, (top(8.5) - 0.3) * P),
                   (row(9.4), px(11.5), 2.3 * P, 0.7 * P, (top(9) - 0.3) * P),
                   (row(9.8), px(11.5), 0, 0, (top(9) - 0.3) * P)], sides=8, mat_index=SLOT)
    # Light canopy panel (rows 10-12, columns 10-12) with its bright centre.
    loft_path(bm, [(row(9.6), px(11.5), 0, 0, (top(10) - 0.4) * P),
                   (row(10.1), px(11.3), 1.6 * P, 0.8 * P, (top(10) - 0.2) * P),
                   (row(11.5), px(11.3), 1.9 * P, 1.0 * P, (top(11.5) - 0.2) * P),
                   (row(12.6), px(11.3), 1.5 * P, 0.8 * P, (top(12.5) - 0.3) * P),
                   (row(13.0), px(11.3), 0, 0, (top(13) - 0.4) * P)], sides=10, mat_index=CANOPY)
    loft_path(bm, [(row(11.3), px(11.3), 0, 0, top(12) * P + 0.025),
                   (row(12.0), px(11.3), 0.6 * P, 0.4 * P, top(12) * P + 0.025),
                   (row(12.7), px(11.3), 0, 0, top(12) * P + 0.02)], sides=6, mat_index=BRIGHT)
    # Spine ridge down the back (rows 14-17, column 11), then the dark vent slot (rows 18-19).
    loft_path(bm, [(row(r), px(11.2), 0.8 * P, 0.6 * P, (top(r) - 0.25) * P) for r in (13.6, 14.5, 16, 17.4)],
              sides=6, mat_index=LIGHT)
    loft_path(bm, [(row(17.8), px(11.6), 0, 0, (top(18) - 0.3) * P),
                   (row(18.2), px(11.6), 1.1 * P, 0.5 * P, (top(18.5) - 0.2) * P),
                   (row(19.6), px(11.6), 1.1 * P, 0.5 * P, (top(19) - 0.2) * P),
                   (row(20.0), px(11.6), 0, 0, (top(19.5) - 0.3) * P)], sides=6, mat_index=SLOT)

    # Side pods: tall blades with a point at the top leaning in, widest rows 14-21 (columns 2-4).
    pod = [(9.6, 4.3, 0, 0, 0.2), (10.5, 4.1, 0.6, 1.4, 0.2), (12, 3.7, 1.1, 2.4, 0.1),
           (14, 3.1, 1.6, 3.0, 0.0), (18, 3.0, 1.6, 3.1, 0.0), (21.5, 3.1, 1.6, 2.9, -0.1),
           (22.7, 3.6, 1.1, 2.0, -0.2), (23.6, 4.0, 0.5, 1.0, -0.2), (24.2, 4.1, 0, 0, -0.2)]
    left = [(row(r), px(c), w * P, h * P, z * P) for r, c, w, h, z in pod]
    loft_path(bm, left, sides=10, mat_index=POD)
    loft_path(bm, mirrored(left), sides=10, mat_index=POD)
    # The bright inner edge of each pod (column 4 / 19 at rows 12-21): a ridge on the inner top.
    ridge = [(row(r), px(c), 0.45 * P, 0.6 * P, z * P) for r, c, z in
             ((10.8, 4.2, 1.2), (13, 4.0, 2.2), (17, 3.9, 2.6), (20.5, 3.9, 2.5), (22.4, 4.1, 1.5))]
    loft_path(bm, ridge, sides=6, mat_index=LIGHT)
    loft_path(bm, mirrored(ridge), sides=6, mat_index=LIGHT)

    # Struts from the pods to the fuselage (rows 20-21, columns 5-8), with a bright top edge.
    for s in (-1, 1):
        x0, x1 = sorted((s * px(4.0), s * px(8.6)))
        box(bm, x0, x1, row(22.2), row(19.5), -1.2 * P, 0.4 * P, mat_index=HULL)
        box(bm, x0, x1, row(21.0), row(19.6), 0.3 * P, 1.1 * P, mat_index=LIGHT)

    # Tail block (rows 22-24, columns 10-13): darker engine housing at the back.
    loft_path(bm, [(row(21.8), px(11.5), 2.4 * P, 1.2 * P, -0.3 * P),
                   (row(24.3), px(11.5), 1.7 * P, 1.0 * P, -0.3 * P),
                   (row(24.8), px(11.5), 0, 0, -0.3 * P)], sides=10, mat_index=DARK)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        level = next(f for f in sprite["frames"] if f["index"] == sprite["sprites"][0]["frames"][0])
        ref = ROOT / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], out, ref, size=level["size"])


if __name__ == "__main__":
    main()
