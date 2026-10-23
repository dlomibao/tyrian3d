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

    lib.claw_arm(bm, ARM, RIDGE, DARK, bulk)
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
