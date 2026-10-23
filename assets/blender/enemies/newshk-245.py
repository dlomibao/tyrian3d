"""Grey octagonal emplacement with a red drum (newshk.shp frame 245): a 3D version of its sprite.

Seen in episode 3 (level 12) as a ground object. A bevelled grey octagonal pad with a raised
vented block above and below the centre, a dark pit across the middle holding a red drum that
lies along X (orange bands round it), a blue lens in a dark socket on top of the drum, and the
drum's axle running out to grooves in the pad's left and right edges.

Run: blender --background --python assets/blender/enemies/newshk-245.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from lib_b074 import box, dome, ex, ey, frustum, loft_x  # noqa: E402

NAME = "newshk-245"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

PAD_TOP = 0.16


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.4, roughness=0.5),  # 0 pad grey
        pal(7, metallic=0.4, roughness=0.55),  # 1 pad bevel, dark grey
        pal(13, metallic=0.45, roughness=0.35),  # 2 light grey frames and lips
        pal(4, metallic=0.3, roughness=0.6),  # 3 dark vents and axle
        pal(2, metallic=0.2, roughness=0.7),  # 4 the pit and grooves
        pal(116, metallic=0.35, roughness=0.35),  # 5 red drum
        pal(121, metallic=0.3, roughness=0.3, emission_strength=2.5),  # 6 orange bands
        pal(119, metallic=0.3, roughness=0.3, emission_strength=1.5),  # 7 red-orange centre band
        pal(112, metallic=0.2, roughness=0.6),  # 8 dark socket
        pal(149, metallic=0.1, roughness=0.15, emission_strength=3.0),  # 9 blue lens
        pal(11, metallic=0.45, roughness=0.4),  # 10 vent rib
    ]
    PAD, BEVEL, LIGHT, VENT, PIT, DRUM, BAND, CBAND, SOCKET, LENS, RIB = range(11)
    bm = bmesh.new()

    # The octagonal pad (sprite rows 1-26, all 24 columns at rows 8-19), bevelled 2 px.
    octagon = [(7, 27), (17, 27), (24, 20), (24, 8), (17, 1), (7, 1), (0, 8), (0, 20)]
    frustum(bm, [(ex(c), ey(r)) for c, r in octagon], 0.0, PAD_TOP, inset=2 / 12, mat_index=BEVEL, mat_top=PAD)

    # The dark pit across the middle (rows 9-18, columns 5-18, corners cut).
    pit = [(6, 19), (18, 19), (19, 17), (19, 11), (18, 9), (6, 9), (5, 11), (5, 17)]
    frustum(bm, [(ex(c), ey(r)) for c, r in pit], PAD_TOP - 0.01, PAD_TOP + 0.012, mat_index=PIT)

    # Raised vented blocks above and below the pit (columns 8-15, rows 4-8 and 19-23).
    for s in (1, -1):
        y = lambda r: s * ey(r)  # noqa: E731
        def ybox(c0, r0, c1, r1, z1, mat, z0=PAD_TOP - 0.01):
            a, b = sorted((y(r0), y(r1)))
            box(bm, ex(c0), a, ex(c1), b, z0, z1, mat)
        ybox(8, 4, 16, 5, 0.27, LIGHT)  # outer bar
        ybox(8, 5, 9, 9, 0.27, LIGHT)  # side bars
        ybox(15, 5, 16, 9, 0.27, LIGHT)
        ybox(9, 5, 15, 9, 0.19, VENT)  # dark vent
        ybox(10, 6, 14, 9, 0.22, PAD)  # the panel inside it
        ybox(12, 5, 13, 9, 0.245, RIB)  # centre rib

    # The red drum lying along X in the pit (columns 5-18, rows 10-17), axis at rows 13-14.
    zc = PAD_TOP + 0.02
    rz = 0.2 / 4  # height per px of half depth
    drum = [(5.0, 2.2), (5.4, 2.9), (6.5, 3.2), (7.0, 3.9), (7.5, 4.0), (16.5, 4.0), (17.0, 3.9), (17.5, 3.2),
            (18.6, 2.9), (19.0, 2.2)]
    loft_x(bm, [(ex(c), h / 12, h * rz) for c, h in drum], 0.0, zc, sides=14, mat_index=DRUM)
    # Orange bands round it at columns 8 and 15, a red-orange one at column 12.
    for c0, mat in ((8, BAND), (15, BAND), (12, CBAND)):
        h = 4.15
        loft_x(bm, [(ex(c0), h / 12, h * rz), (ex(c0 + 1), h / 12, h * rz)], 0.0, zc, sides=14, mat_index=mat)

    # The dark socket on top of the drum (columns 10-13, rows 12-15) and its blue lens.
    top = zc + 4 * rz
    box(bm, ex(10), ey(16), ex(14), ey(12), top - 0.07, top + 0.03, SOCKET)
    dome(bm, ex(12), ey(14), top + 0.03, 1.2 / 12, 1.2 / 12, 0.07, sides=12, rings=3, mat_index=LENS)

    # The axle out to the grooves in the pad's left and right edges (rows 13-14), between light lips.
    for s in (1, -1):
        x0, x1 = sorted((s * ex(0.3), s * ex(5.2)))
        box(bm, x0, ey(15), x1, ey(13), 0.0, PAD_TOP + 0.015, PIT)
        loft_x(bm, [(x0, 0.8 / 12, 0.8 / 12), (x1, 0.8 / 12, 0.8 / 12)], 0.0, PAD_TOP + 0.02, sides=8,
               mat_index=VENT)
        for r in (12, 15):
            xa, xb = sorted((s * ex(1), s * ex(5)))
            box(bm, xa, ey(r + 1), xb, ey(r), 0.0, PAD_TOP + 0.06, LIGHT)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    for poly in obj.data.polygons:
        poly.use_smooth = poly.material_index in (DRUM, BAND, CBAND, LENS) or (
            poly.material_index == VENT and len(poly.vertices) == 4 and abs(poly.normal.x) < 0.5)
    return obj


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
