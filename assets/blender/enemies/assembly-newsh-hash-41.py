"""Spinning four-claw grabber (newsh#.shp, assembly of 4 pieces): a 3D version of its sprites.

Seen in episode 3 (levels 3.4 and 3.19) and episode 4 (4.8). Four 2x2 enemies make one 48x56 px
ground machine: a brown domed hub with an amber glint, and four grey claw arms. Each arm is a
stem out of the hub, a knuckle across its end and two prongs (a thick one and a thin finger)
angled off to the clockwise side. The arms are drawn as one arm turned in 90 degree steps.

Its nine frames are the machine turning and then sinking away:
- frames 0-3 are the claws at four angles 22.5 degrees apart (frame 2 is the arms straight up,
  right, down and left; frame 0 is 45 degrees anticlockwise of that),
- frames 4 and 5 repeat frame 2's angle a shade darker,
- frames 6, 7 and 8 draw the arms shorter and darker each time, until little more than the hub
  is left.

So every piece gets seven models (one per distinct shape), built from the same arm:
<piece> frame 0, -f2 frame 1, -f3 frames 2, 4 and 5, -f4 frame 3, -f5 frame 6, -f6 frame 7 and
-f7 frame 8. The whole machine is built once per shape in assembly coordinates and cut into the
four pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh-hash-41.py [-- --preview out.png]
(the preview is the whole machine at frame 0; out-f2.png ... out-f7.png show the other shapes and
each piece also gets <piece>.png next to it). Add --report to print a top-view silhouette check.
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b094 as lib  # noqa: E402

NAME = "assembly-newsh-hash-41"
ROOT = common.repo_root(__file__)
# Pieces and where they sit in the 48 x 56 px assembly (left, top). newsh#.shp 2x2 sprite n covers
# cells n, n+1, n+19, n+20, so 1 and 3 are the top row and 39 and 41 the bottom row; the hub is
# in the corner of each piece that meets the others (sprite.json `assemblyLayout` places 39 left
# of 41; 1 and 3 above them were off screen when the catalogue looked).
GRID = [("newsh-hash-1", 0, 0), ("newsh-hash-3", 24, 0), ("newsh-hash-39", 0, 28), ("newsh-hash-41", 24, 28)]
PIECES = [g[0] for g in GRID]
HUB = (0.5, 0.5)  # hub centre in pixels from the assembly's centre (it sits on pixel 24, 27)

# The shapes: suffix, frames, arm angle (degrees anticlockwise from frame 2, fitted to the
# sprites' top view), arm scale, shade (0 bright ... 3 darkest), bulk (see build_arm) and the
# scale of the whole machine (the last frame draws even the hub smaller).
SHAPES = [
    ("", [0], 45.0, 1.0, 0, 0.0, 1.0),
    ("-f2", [1], 24.0, 1.0, 0, 0.6, 1.0),
    ("-f3", [2, 4, 5], 0.0, 1.0, 0, 0.0, 1.0),
    ("-f4", [3], -26.0, 1.0, 0, 0.0, 1.0),
    ("-f5", [6], 0.0, 0.9, 1, 0.0, 1.0),
    ("-f6", [7], 0.0, 0.8, 2, 0.0, 1.0),
    ("-f7", [8], 0.0, 0.9, 3, 0.0, 0.55),
]
# Grey arm colours per shade: (body, light ridge, dark underside) palette indices.
SHADES = [(9, 12, 6), (4, 7, 2), (3, 6, 2), (3, 5, 2)]


def build_arm(bm, ARM, RIDGE, DARK, bulk=0.0):
    """One claw arm in pixels from the hub centre, pointing up (+y), prongs leaning right.
    `bulk` (pixels) thickens the main prong on its outer side and lengthens it (frame 1 draws
    the claws fatter while they turn)."""
    z = 0.11
    b = bulk
    # Stem out of the hub, a little narrower where it leaves it.
    lib.sweep(bm, [(0.3, 3.5, z, 1.2, 0.05), (0.3, 6.5, z, 1.4, 0.055), (0.4, 9.5, z, 1.9, 0.06),
                   (0.4, 11.5, z, 2.0, 0.06)], sides=8, mat=ARM)
    # Knuckle across the end of the stem (x -5 .. 4, y 11 .. 15).
    lib.sweep(bm, [(-5.3, 13.0, z, 0.0, 0.0), (-4.6, 13.0, z, 1.9, 0.07), (0.0, 12.8, z, 2.1, 0.075),
                   (3.4, 12.3, z, 1.6, 0.065), (4.4, 12.2, z, 0.0, 0.0)], sides=10, mat=ARM)
    # Main prong: up from the left end of the knuckle, then off at 45 degrees to a blunt tip.
    lib.sweep(bm, [(-2.8 - b, 12.5, z, 2.7 + b / 2, 0.07), (-2.4 - b, 15.0, z, 2.6 + b / 2, 0.07),
                   (-1.0 - b * 0.7, 17.0 + b * 0.7, z, 2.0 + b / 2, 0.065),
                   (1.2 - b * 0.7, 19.3 + b * 0.7, z, 1.8 + b / 2, 0.06),
                   (3.6 - b * 0.7, 21.7 + b * 0.7, z, 1.75 + b / 2, 0.055),
                   (4.4 - b * 0.5, 22.5 + b, z, 1.5 + b / 2, 0.05)],
              sides=8, mat=ARM)
    # Its light upper-left edge.
    lib.sweep(bm, [(-3.9, 13.0, z + 0.05, 0.0, 0.0), (-3.8, 14.5, z + 0.05, 0.6, 0.025),
                   (-2.3, 17.2, z + 0.045, 0.6, 0.025), (2.4, 22.2, z + 0.035, 0.55, 0.02),
                   (3.0, 22.8, z + 0.03, 0.0, 0.0)], sides=6, mat=RIDGE)
    # Thin finger off the right end of the knuckle.
    lib.sweep(bm, [(2.4, 12.2, z, 1.4, 0.055), (4.5, 13.8, z, 1.15, 0.05), (6.6, 15.8, z, 1.05, 0.045),
                   (8.2, 17.3, z, 0.95, 0.04), (8.7, 17.8, z, 0.0, 0.0)], sides=8, mat=ARM)
    # A dark rib under the stem and knuckle so the arm reads as a thick casting from the side.
    lib.sweep(bm, [(0.3, 4.0, 0.05, 1.0, 0.04), (0.3, 11.0, 0.05, 1.5, 0.045), (0.3, 12.5, 0.05, 0.0, 0.0)],
              sides=6, mat=DARK)


def build_hub(bm, HUB_BASE, HUB_DOME, HUB_RIM):
    """The brown hub: an octagonal footing, a rim and a low dome (radius about 5.5 px)."""
    lib.prism(bm, lib.ngon(5.6, 8, start=0.39), 0.0, 0.1, mat=HUB_BASE)
    lib.frustum(bm, 0, 0, 5.2, 4.6, 0.1, 0.16, sides=16, mat=HUB_RIM, cap_top=False)
    lib.ellipsoid(bm, 0, 0, 0.16, 4.6, 4.6, 0.12, mat=HUB_DOME, segments=16, rings=8, z_min=0.15)


def build(sprite, angle, scale, shade, tag, bulk=0.0, whole=1.0):
    coll = common.reset_collection(f"{NAME}{tag}")
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh41", **kw)  # noqa: E731
    arm, ridge, dark = SHADES[shade]
    mats = [
        pal(arm, metallic=0.6, roughness=0.35),  # 0 grey arm
        pal(ridge, metallic=0.6, roughness=0.3),  # 1 light edge
        pal(dark, metallic=0.4, roughness=0.6),  # 2 dark underside
        pal(163, metallic=0.3, roughness=0.6),  # 3 dark brown footing
        pal(25, metallic=0.4, roughness=0.4),  # 4 brown dome
        pal(26, metallic=0.4, roughness=0.4),  # 5 light brown rim
        pal(124, emission_strength=3.0),  # 6 amber glint
    ]
    ARM, RIDGE, DARK, HUB_BASE, HUB_DOME, HUB_RIM, GLOW = range(7)
    bm = bmesh.new()

    build_arm(bm, ARM, RIDGE, DARK, bulk)
    lib.copy_rotated(bm, 0, 0, [-90, -180, -270])  # clockwise round the hub, like the sprite
    lib.transform(bm, 0, angle_deg=angle, scale=scale, scale_z=min(1.0, 0.5 + scale / 2))
    build_hub(bm, HUB_BASE, HUB_DOME, HUB_RIM)
    # The amber glint stays up and left of the hub's centre in every frame (the light is fixed).
    lib.ellipsoid(bm, -1.5, 1.5, 0.25, 2.0, 2.0, 0.045, mat=GLOW, segments=12, rings=6)
    lib.transform(bm, 0, scale=whole, dx_px=HUB[0], dy_px=HUB[1])
    return lib.to_object(f"{NAME}{tag}", bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    layout = [(name, (x0 + 12 - 24) * 1.0, (y0 + 14 - 28) * 1.0) for name, x0, y0 in GRID]
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for suffix, frames, angle, scale, shade, bulk, whole in SHAPES:
        obj = build(sprite, angle, scale, shade, suffix, bulk, whole)
        if "--report" in sys.argv:
            lib.silhouette_report(obj, ROOT, GRID, frames[0], label=f"{NAME}{suffix} frame {frames[0]}")
        pieces = common.split_assembly(obj, [(f"{n}{suffix}", cx, cy) for n, cx, cy in layout])
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            common.export_sprite_model(ROOT, [pieces[f"{name}{suffix}"]], f"enemies/{name}{suffix}",
                                       lib.frame_subset(data["sprites"], frames))
        if preview:
            import tempfile
            out = preview if not suffix else preview.with_name(f"{preview.stem}{suffix}.png")
            ref = lib.composite_png(ROOT, GRID, frames[0], Path(tempfile.mkdtemp()) / "a.png", pad_to=(48, 56))
            common.render_preview([obj], str(out), ref, size=4, view_px=480)
            for name in PIECES:
                data = common.load_sprite(ROOT, name)
                img = ROOT / "reference" / "models" / name / data["frames"][frames[0]]["image"]
                common.render_preview([pieces[f"{name}{suffix}"]], str(out.parent / f"{name}{suffix}.png"), img, size=2)


if __name__ == "__main__":
    main()
