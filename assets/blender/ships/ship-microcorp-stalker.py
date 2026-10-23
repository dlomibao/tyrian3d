"""Microcorp Stalker (player ship, tyrian.shp#8 sprite 195 and its banking frames 191-199).

A grey fighter: a shiny conical nose, a round dark cockpit, a narrow neck with two red lights, a
wide rear body with bright strakes and a red engine glow, and two swept wings pointing forward
and out with bright leading edges, tilted up a little (the banking frames show them as wide
plates). The sprite is centred on column 11, half a pixel left of the 24 px block's centre.

Run: blender --background --python assets/blender/ships/ship-microcorp-stalker.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import common  # noqa: E402
from lib_b001 import loft_path, mirrored  # noqa: E402

NAME = "ship-microcorp-stalker"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel
AXIS = 11  # the sprite's mirror column; the model is built about X = 0 and shifted to it at the end


def cx(c):
    """Sprite column centre to X, relative to the mirror column."""
    return (c - AXIS) / 12


def ex(e):
    """Sprite column edge (left edge of column e) to X, relative to the mirror column."""
    return (e - AXIS - 0.5) / 12


def ey(r):
    """Sprite row edge (top edge of row r) to Y."""
    return (14 - r) / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.55, roughness=0.4),  # 0 hull grey
        pal(9, metallic=0.5, roughness=0.4),  # 1 wing grey
        pal(12, metallic=0.65, roughness=0.28),  # 2 bright strakes and leading edges
        pal(10, metallic=0.7, roughness=0.22),  # 3 nose cone
        pal(14, metallic=0.7, roughness=0.18),  # 4 nose highlight
        pal(2, metallic=0.2, roughness=0.15),  # 5 dark cockpit
        pal(117, emission_strength=3.0),  # 6 red side lights
        pal(120, emission_strength=5.0),  # 7 engine glow
        pal(6, metallic=0.45, roughness=0.5),  # 8 dark grey (neck, tail)
    ]
    HULL, WING, BRIGHT, NOSE, SHINE, COCKPIT, RED, GLOW, DARK = range(9)
    bm = bmesh.new()

    # Nose cone (rows 0-6): (row, half width px, half height px, z px).
    nose = [(-0.2, 0, 0, 0.4), (1.0, 0.6, 0.6, 0.4), (3.0, 1.5, 1.4, 0.4), (5.0, 2.4, 2.1, 0.3),
            (6.8, 2.7, 2.3, 0.2), (7.2, 0, 0, 0.2)]
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in nose], sides=12, mat_index=NOSE)
    # Its shine (column 10-11 at rows 3-6), a highlight strip on the upper left of the cone.
    loft_path(bm, [(ey(r), x * P, w * P, w * P, z * P) for r, x, w, z in
                   ((1.6, -0.2, 0, 1.0), (3.0, -0.4, 0.5, 1.5), (4.8, -0.5, 0.7, 2.0), (6.4, -0.5, 0, 2.2))],
              sides=6, mat_index=SHINE)

    # Fuselage from the cockpit back (rows 7-24).
    hull = [(6.6, 2.6, 2.3, 0.2), (7.0, 3.4, 2.7, 0.2), (10.4, 3.5, 2.7, 0.2), (11.0, 2.6, 2.1, 0.1),
            (16.0, 2.6, 2.2, 0.0), (17.0, 3.6, 2.8, 0.0), (21.5, 4.3, 3.0, 0.0), (23.2, 3.4, 2.4, -0.2),
            (24.2, 2.4, 1.8, -0.3), (24.6, 0, 0, -0.3)]
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in hull], sides=14, mat_index=HULL)
    # Darker neck band between cockpit and body (rows 11-16).
    common.loft(bm, [(ey(10.9), 2.75 * P, 2.25 * P, 0.1 * P), (ey(16.1), 2.75 * P, 2.3 * P, 0.0)],
                sides=14, mat_index=DARK)

    # Round dark cockpit on top of the cockpit section (rows 7-10, columns 10-12), lighter centre.
    common.loft(bm, [(ey(6.9), 0, 0, 2.2 * P), (ey(7.3), 1.6 * P, 0.8 * P, 2.4 * P),
                     (ey(8.6), 2.0 * P, 1.0 * P, 2.6 * P), (ey(10.0), 1.6 * P, 0.8 * P, 2.4 * P),
                     (ey(10.5), 0, 0, 2.2 * P)], sides=12, mat_index=COCKPIT)
    common.loft(bm, [(ey(8.0), 0, 0, 3.5 * P), (ey(8.5), 0.5 * P, 0.3 * P, 3.55 * P), (ey(9.0), 0, 0, 3.5 * P)],
                sides=6, mat_index=NOSE)

    # Red lights on both sides of the neck (rows 12-13, columns 8 and 14).
    for s in (-1, 1):
        loft_path(bm, [(ey(11.8), s * 2.9 * P, 0, 0, 0.6 * P), (ey(12.2), s * 2.9 * P, 0.8 * P, 0.9 * P, 0.6 * P),
                       (ey(13.8), s * 2.9 * P, 0.8 * P, 0.9 * P, 0.6 * P), (ey(14.2), s * 2.9 * P, 0, 0, 0.6 * P)],
                  sides=8, mat_index=RED)

    # Bright strakes on the body's shoulders (columns 7 and 15, rows 17-20) and a faint spine.
    strake = [(ey(r), w * P, 0.5 * P, 0.5 * P, z * P) for r, w, z in
              ((16.6, -3.0, 1.6), (17.5, -3.6, 1.8), (20.5, -3.8, 1.8), (21.6, -3.6, 1.4))]
    loft_path(bm, strake, sides=6, mat_index=BRIGHT)
    loft_path(bm, mirrored(strake), sides=6, mat_index=BRIGHT)
    loft_path(bm, [(ey(r), -0.6 * P, 0.6 * P, 0.5 * P, z * P) for r, z in
                   ((16.6, 2.0), (17.5, 2.7), (21.5, 2.9), (23.4, 2.2))], sides=6, mat_index=BRIGHT)

    # Swept wings: tip at row 12 column 2, leading edge down to the body at row 17, outer edge
    # stepping in to the tail at row 24. Raised toward the tip (dihedral).
    wing = [(ex(2.0), ey(11.6)), (ex(3.0), ey(11.9)), (ex(8.6), ey(17.0)), (ex(8.6), ey(24.6)),
            (ex(6.0), ey(25.0)), (ex(5.3), ey(23.0)), (ex(4.3), ey(21.0)), (ex(3.0), ey(18.8)),
            (ex(2.0), ey(18.0))]
    root_x = ex(8.6)
    for mirror in (False, True):
        start = len(bm.verts)
        common.slab(bm, wing, 1.3 * P, z=0.2 * P, mat_index=WING, mirror_x=mirror)
        bm.verts.ensure_lookup_table()
        for v in bm.verts[start:]:
            v.co.z += (abs(v.co.x) - abs(root_x)) * 0.25
    # Bright leading edges, from the tip to the wing root.
    lead = [(ey(r), ex(e), 0.6 * P, 0.6 * P, 0.25 * (abs(ex(e)) - abs(root_x)) + 1.0 * P) for r, e in
            ((11.9, 2.6), (13.5, 4.2), (15.5, 6.3), (17.0, 8.0))]
    loft_path(bm, lead, sides=6, mat_index=BRIGHT)
    loft_path(bm, mirrored(lead), sides=6, mat_index=BRIGHT)

    # Engine: a short nozzle at the tail (rows 24-25) with the red-orange glow (columns 10-12).
    common.loft(bm, [(ey(23.6), 1.9 * P, 1.6 * P, -0.3 * P), (ey(25.2), 1.7 * P, 1.4 * P, -0.3 * P)],
                sides=10, mat_index=DARK, cap_end=False)
    common.loft(bm, [(ey(24.8), 1.5 * P, 1.2 * P, -0.3 * P), (ey(25.6), 1.3 * P, 1.0 * P, -0.3 * P),
                     (ey(25.9), 0, 0, -0.3 * P)], sides=10, mat_index=GLOW)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    # Move from the mirror axis to the sprite's column 11.
    for v in obj.data.vertices:
        v.co.x -= 0.5 * P
    return obj


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
