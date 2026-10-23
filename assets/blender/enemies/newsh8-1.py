"""Red piston gantry (newsh8.shp frames 1, 3, 5, 7): a 3D version of its sprites.

Seen in episode 3 (levels 3.4 and 3.19). A ground machine: two long red legs tapering down the
screen, joined near the top by a grey crossbar, with a red sleeve in the middle that a piston
slides through (a grey cap and a red light on its head, a pale barrel and a rounded tip below).
Over the four frames the piston slides one pixel down per frame, so the light disappears into
the sleeve, while the grey clamps on the legs slide one pixel up per frame. Each frame is a
different shape, so each gets its own model: newsh8-1, newsh8-1-f2, -f3 and -f4.

Run: blender --background --python assets/blender/enemies/newsh8-1.py [-- --preview out.png]
(each frame's model is previewed to <model>.png beside out.png).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b082  # noqa: E402
from lib_b082 import PX  # noqa: E402

NAME = "newsh8-1"
ROOT = common.repo_root(__file__)
FRAMES = [1, 3, 5, 7]  # frame k slides the piston k px down and the leg clamps k px up
AXIS = 11  # the machine is mirror symmetric about sprite column 11


def px(c):
    """Sprite column (pixel centre) to Blender X."""
    return (c + 0.5 - 12) / 12


def row(r):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (14 - (r + 0.5)) / 12


def mirror(c):
    return 2 * AXIS - c


def build(sprite, name, k):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(71, metallic=0.3, roughness=0.45),  # 0 red legs and sleeve
        pal(77, metallic=0.3, roughness=0.35),  # 1 light red edges, piston barrel
        pal(9, metallic=0.7, roughness=0.3),  # 2 grey leg clamps
        pal(11, metallic=0.75, roughness=0.25),  # 3 bright grey crossbar
        pal(5, metallic=0.6, roughness=0.4),  # 4 dark grey brackets
        pal(8, metallic=0.7, roughness=0.3),  # 5 piston cap
        pal(69, metallic=0.3, roughness=0.5),  # 6 piston head
        pal(124, emission_strength=4.0),  # 7 head light
        pal(67, metallic=0.3, roughness=0.55),  # 8 dark band
        pal(72, metallic=0.3, roughness=0.4),  # 9 piston tip
    ]
    LEG, EDGE, CLAMP, BAR, BRACKET, CAP, HEAD, LIGHT, BAND, TIP = range(len(mats))
    bm = bmesh.new()
    zl = 0.15  # legs' axis height

    # Legs (columns 4-6 and 16-18, rows 2-24): straight on the outside, narrowing to a point at the
    # bottom; (column, row, half width px, half height). A little wider than the lit pixels, since
    # the near-black edge pixels beside them are part of the leg too.
    leg = [(4.6, 1.7, 0.0, 0.0), (4.6, 2.2, 1.0, 0.09), (5.0, 3.2, 1.5, 0.13), (5.0, 17.5, 1.5, 0.13),
           (4.55, 18.5, 1.05, 0.11), (4.5, 21.5, 1.0, 0.1), (4.1, 22.5, 0.6, 0.08), (4.0, 24.3, 0.5, 0.07),
           (4.0, 24.8, 0.0, 0.0)]
    for side in (-1, 1):
        col = (lambda c: c) if side < 0 else mirror
        lib_b082.loft_xy(bm, [(px(col(c)), row(r), w * 1.15 * PX, h, zl) for c, r, w, h in leg], sides=10, mat=LEG)
        # Light edge along the inside of each leg (column 6 / 16).
        lib_b082.loft(bm, [(row(2.8), 0.0, 0.0, zl + 0.09), (row(3.4), 0.45 * PX, 0.025, zl + 0.1),
                           (row(17.4), 0.45 * PX, 0.025, zl + 0.1), (row(18.2), 0.0, 0.0, zl + 0.08)],
                      sides=6, mat=EDGE, x=px(col(5.9)))
        # Grey clamp on the outside of the leg (columns 3-4 / 18-19), k px higher each frame.
        x0, x1 = sorted((px(col(2.5)), px(col(4.5))))  # pixel edges
        lib_b082.box(bm, x0, x1, row(8.5 - k), row(4.5 - k), 0.03, 0.33, mat=CLAMP, bevel=0.025)

    # Crossbar over the legs and the sleeve (row 9, columns 5-16).
    lib_b082.tube_x(bm, px(4.5), px(16.5), row(9), 0.36, 0.55 * PX, 0.055, mat=BAR, sides=10)
    # Sleeve the piston slides through (rows 8-10, columns 9-13).
    lib_b082.loft(bm, [(row(7.6), 1.8 * PX, 0.1, 0.2), (row(8.0), 2.5 * PX, 0.15, 0.2),
                       (row(10.1), 2.5 * PX, 0.15, 0.2), (row(10.6), 2.0 * PX, 0.11, 0.2)],
                  sides=12, mat=LEG, x=px(AXIS))
    # Dark grey brackets beside the piston under the sleeve (columns 8 and 14-15, rows 11-12).
    lib_b082.box(bm, px(7.5), px(9.0), row(12.6), row(10.4), 0.04, 0.24, mat=BRACKET, bevel=0.015)
    lib_b082.box(bm, px(13.0), px(15.5), row(12.6), row(10.4), 0.04, 0.24, mat=BRACKET, bevel=0.015)

    # Piston, k px further down each frame: rows t (top) to b (tip).
    t, b = 3 + k, 16 + k
    zp, w, h = 0.2, 1.5 * PX, 0.1
    x = px(AXIS)
    lib_b082.loft(bm, [(row(t - 0.45), 0.9 * PX, 0.06, zp), (row(t - 0.1), w * 1.05, h * 1.05, zp),
                       (row(t + 1.5), w * 1.05, h * 1.05, zp)], sides=10, mat=CAP, x=x)
    lib_b082.loft(bm, [(row(t + 1.5), w, h, zp), (row(t + 2.5), w, h, zp)], sides=10, mat=HEAD, x=x)
    lib_b082.loft(bm, [(row(t + 2.5), w * 1.04, h * 1.04, zp), (row(t + 3.5), w * 1.04, h * 1.04, zp)],
                  sides=10, mat=LIGHT, x=x)
    lib_b082.loft(bm, [(row(t + 3.5), w, h, zp), (row(10.0), w, h, zp)], sides=10, mat=HEAD, x=x)
    lib_b082.loft(bm, [(row(10.0), w, h, zp), (row(b - 4.5), w, h, zp)], sides=10, mat=EDGE, x=x)
    lib_b082.loft(bm, [(row(b - 4.5), w * 0.95, h * 0.95, zp), (row(b - 3.5), w * 0.95, h * 0.95, zp)],
                  sides=10, mat=BAND, x=x)
    lib_b082.loft(bm, [(row(b - 3.5), w, h, zp), (row(b - 2.0), w, h, zp), (row(b - 1.0), w * 0.8, h * 0.8, zp),
                       (row(b - 0.3), w * 0.45, h * 0.45, zp), (row(b), 0.0, 0.0, zp)], sides=10, mat=TIP, x=x)

    return lib_b082.to_object(name, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    for k, index in enumerate(FRAMES):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj = build(sprite, name, k)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", [{**base, "frames": [index]}])
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            ref = ROOT / "reference" / "models" / NAME / f"frame-newsh8-{index}.png"
            common.render_preview([obj], str(out.with_name(f"{name}.png")), ref, size=2)


if __name__ == "__main__":
    main()
