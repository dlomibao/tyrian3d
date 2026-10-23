"""Purple shield craft (newsh2.shp frame 127): a 3D version of its sprite.

Seen in episode 1 (levels 1.25, 1.28, 1.3, 1.36) and episode 3. It flies nose down the screen: a
broad dark purple armoured hull, wide at the back and narrowing to the nose, with a cyan glass
canopy at its back edge, a lit spine and a cyan-lit vent grille in the middle, light cheek ridges,
dark ports in its flanks, a pale chin plate, two side lobes reaching down beside the chin and a
teal gun block at the nose. One frame, one model.

Run: blender --background --python assets/blender/enemies/newsh2-127.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b048 as L  # noqa: E402
from lib_b048 import common  # noqa: E402

NAME = "newsh2-127"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = L.PX
AXIS = 12  # the sprite is symmetric about the centre of column 12


def cx(c):
    """Sprite column (pixel centre) to X, relative to the axis (shifted onto it at the end)."""
    return (c - AXIS) / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(85, metallic=0.35, roughness=0.45),  # 0 hull purple
        pal(88, metallic=0.35, roughness=0.4),  # 1 light ridges
        pal(83, metallic=0.3, roughness=0.5),  # 2 dark purple underside / flanks
        pal(89, metallic=0.35, roughness=0.35),  # 3 pale chin plate and spine
        pal(80, metallic=0.1, roughness=0.8),  # 4 dark ports and slots
        pal(134, metallic=0.6, roughness=0.12),  # 5 cyan glass canopy
        pal(102, metallic=0.4, roughness=0.5),  # 6 grille frame
        pal(59, emission_strength=2.5),  # 7 lit grille slats
        pal(136, emission_strength=3.5),  # 8 bright grille slat
        pal(54, metallic=0.45, roughness=0.4),  # 9 teal gun block
        pal(131, emission_strength=2.0),  # 10 lit edge of the gun block
        pal(86, metallic=0.35, roughness=0.45),  # 11 side lobes
    ]
    HULL, RIDGE, DARKP, PALE, PORT, GLASS, FRAME, SLAT, SLAT_HI, TEAL, TEAL_LIT, LOBE = range(12)
    bm = bmesh.new()
    row = L.row

    # Main hull, back (top of the sprite) to the nose block: (row edge, half width px, half
    # height, z).
    hull = [(0.7, 4.5, 0.05, 0.0), (1.5, 6.5, 0.09, 0.0), (2.5, 8.8, 0.13, 0.0), (3.6, 10.0, 0.16, 0.0),
            (5.0, 10.6, 0.17, 0.0), (13.0, 10.6, 0.17, 0.0), (14.5, 9.8, 0.16, 0.0),
            (16.5, 9.0, 0.14, 0.0), (18.5, 7.9, 0.12, -0.01), (20.5, 6.7, 0.1, -0.01),
            (22.3, 5.6, 0.08, -0.02), (22.8, 4.6, 0.06, -0.02)]
    common.loft(bm, [(L.ey(r), w * PX, h, z) for r, w, h, z in hull], sides=12, mat_index=HULL)
    # Pale chin plate on top (columns 9-14, rows 14-19), sloping down to the nose.
    L.sweep(bm, [(0, L.ey(13.6), 0.165, 3.2 * PX, 0.02), (0, L.ey(17.0), 0.145, 3.0 * PX, 0.02),
                 (0, L.ey(19.9), 0.115, 2.8 * PX, 0.02)], sides=6, mat=PALE, smooth=False)
    # Dark slot across the chin above the gun block (rows 20-21).
    L.box(bm, -3.2 * PX, L.ey(21.8), 3.2 * PX, L.ey(20.0), 0.04, 0.095, mat=PORT)

    # Teal gun block at the nose (columns 8-16, rows 22-26) with its lit top edge.
    L.prism(bm, [(-5.0 * PX, L.ey(21.8)), (5.0 * PX, L.ey(21.8)), (4.7 * PX, L.ey(24.0)),
                 (3.6 * PX, L.ey(27.0)), (-3.6 * PX, L.ey(27.0)), (-4.7 * PX, L.ey(24.0))],
            -0.08, 0.07, mat=TEAL)
    L.box(bm, -4.6 * PX, L.ey(24.0), 4.6 * PX, L.ey(23.0), 0.06, 0.085, mat=TEAL_LIT)
    L.box(bm, -4.8 * PX, L.ey(23.0), 4.8 * PX, L.ey(22.0), 0.05, 0.08, mat=RIDGE)

    # Cyan glass canopy at the back edge (columns 9-15, rows 1-3).
    L.ellipsoid(bm, 0, L.ey(2.2), 0.08, 3.6 * PX, 1.9 * PX, 0.08, mat=GLASS, segments=14, rings=7)

    # Spine (columns 11-13, rows 4-8).
    L.sweep(bm, [(0, L.ey(3.8), 0.15, 0.0, 0.0), (0, L.ey(4.5), 0.16, 1.5 * PX, 0.04),
                 (0, L.ey(8.6), 0.16, 1.5 * PX, 0.04), (0, L.ey(9.0), 0.16, 0.0, 0.0)], sides=6, mat=PALE)

    # Vent grille (columns 10-14, rows 9-12): a dark frame with lit slats.
    L.box(bm, -2.6 * PX, L.ey(13.0), 2.6 * PX, L.ey(9.0), 0.12, 0.19, mat=FRAME)
    for r, m in ((9.15, SLAT), (11.15, SLAT), (12.15, SLAT_HI)):
        L.box(bm, -2.3 * PX, L.ey(r + 0.75), 2.3 * PX, L.ey(r), 0.185, 0.2, mat=m)

    # Left half details, mirrored below.
    side = bmesh.new()
    # Light cheek ridge (columns 5-8, rows 2-14), flat on the hull.
    L.sweep(side, [(cx(6.6), L.ey(2.4), 0.11, 0.0, 0.0), (cx(6.6), L.ey(3.4), 0.135, 2.0 * PX, 0.025),
                   (cx(6.8), L.ey(13.5), 0.135, 2.0 * PX, 0.025), (cx(7.0), L.ey(14.8), 0.12, 0.0, 0.0)],
            sides=6, mat=RIDGE)
    # Dark band across the flank (row 6) and the dark port (columns 3-4, rows 11-13).
    L.ellipsoid(side, cx(3.8), L.ey(12.4), 0.07, 1.3 * PX, 1.8 * PX, 0.05, mat=PORT, segments=8, rings=4)
    L.ellipsoid(side, cx(4.2), L.ey(6.5), 0.1, 2.6 * PX, 0.7 * PX, 0.04, mat=PORT, segments=8, rings=4)
    # Side lobe down beside the chin (columns 3-7, rows 14-21) with dark slots either side.
    L.sweep(side, [(cx(4.0), L.ey(14.2), 0.08, 0.0, 0.0), (cx(4.3), L.ey(15.2), 0.085, 1.4 * PX, 0.035),
                   (cx(5.4), L.ey(18.5), 0.075, 1.4 * PX, 0.035), (cx(6.6), L.ey(21.0), 0.06, 1.2 * PX, 0.03),
                   (cx(7.2), L.ey(22.0), 0.05, 0.0, 0.0)], sides=6, mat=LOBE)
    L.ellipsoid(side, cx(4.8), L.ey(15.8), 0.075, 1.2 * PX, 1.0 * PX, 0.04, mat=PORT, segments=8, rings=4)
    L.ellipsoid(side, cx(7.6), L.ey(19.2), 0.09, 0.9 * PX, 1.6 * PX, 0.04, mat=PORT, segments=8, rings=4)
    L.mirror_x(side)
    me = __import__("bpy").data.meshes.new("tmp127")
    side.to_mesh(me)
    side.free()
    bm.from_mesh(me)
    __import__("bpy").data.meshes.remove(me)

    # Shift onto the sprite's axis (the centre of column 12).
    for v in bm.verts:
        v.co.x += L.px(AXIS)
    return L.to_object(NAME, bm, mats, coll)


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
