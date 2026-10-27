"""Merging ice orbs (newshd.shp frames 228, 247, 266, 285, 304): a 3D version of its sprites.

Seen in levels 2.8 and 3.10. Two small glassy blue orbs sitting on the ground roll together and
merge into one: apart (228), close (247), squeezed into one lumpy orb (266, 304: the same shape,
the seam just shaded on the other side) and a single orb (285). The shape changes, so each
stage is its own model: newshd-228, -f2, -f3 and -f4. On -f3 the glint and the dark seam swap
sides between its two frames (266: glint left, shadow right of the middle; 304: glint right of
the middle, shadow left), so each frame gets its own glint and seam (common.frame_part).

Run: blender --background --python assets/blender/enemies/newshd-228.py [-- --preview out.png]
(writes <out>.png for the first model and <name>-fN.png beside it for the others).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b075 as L  # noqa: E402

NAME = "newshd-228"
ROOT = common.repo_root(__file__)
R = 2.4 * L.PX  # orb radius (the 4 px orb inside its outline)

# (model suffix, frames, orb centres as pixel-edge columns)
STAGES = [
    ("", [228], [3.0, 9.0]),
    ("-f2", [247], [4.0, 8.0]),
    ("-f3", [266, 304], [5.0, 7.0]),
    ("-f4", [285], [6.0]),
]


def build(sprite, name, centres):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(59, metallic=0.3, roughness=0.18),  # 0 blue glassy orb
        pal(62, metallic=0.1, roughness=0.1),  # 1 pale highlight
        pal(55, metallic=0.3, roughness=0.3),  # 2 dark blue underside / seam
    ]
    ORB, SHINE, DARK = range(3)
    bm = bmesh.new()
    y = L.YE(7.0, 14)
    merged = len(centres) == 2 and centres[1] - centres[0] < 3
    for i, c in enumerate(centres):
        x = L.XE(c, 12)
        rx = R * (1.08 if merged else 1.0)
        L.ellipsoid(bm, x, y, R * 0.92, rx, R, R * 0.92, mat=ORB, segments=16, rings=8, zmin=0.0)
        if merged:
            continue  # the merged orb's glint and seam change with the frame (below)
        # The pale glint on its upper left (the 60/62 pixels).
        L.ellipsoid(bm, x - R * 0.35, y + R * 0.3, R * 1.55, R * 0.42, R * 0.38, R * 0.18, mat=SHINE,
                    segments=10, rings=5)
    objs = [L.to_object(name, bm, mats, coll)]
    if merged:
        mid = (L.XE(centres[0], 12) + L.XE(centres[1], 12)) / 2
        # One glint (the 60/62 pixels) and one dark seam where the orbs press together per frame:
        # on 266 the glint is on the left orb and the shadow just right of the middle; on 304 the
        # glint sits just right of the middle and the shadow is on the left orb.
        for frame, glint_x, seam_x, seam_dy in ((266, L.XE(centres[0], 12) - R * 0.35, mid, 0.2),
                                                (304, mid + R * 0.25, L.XE(centres[0], 12) + R * 0.1, 0.4)):
            fbm = bmesh.new()
            L.ellipsoid(fbm, glint_x, y + R * 0.3, R * 1.55, R * 0.42, R * 0.38, R * 0.18, mat=SHINE,
                        segments=10, rings=5)
            L.ellipsoid(fbm, seam_x, y - R * seam_dy, R * 0.75, R * 0.25, R * 0.8, R * 0.85, mat=DARK,
                        segments=10, rings=6, zmin=0.0)
            objs.append(common.frame_part(L.to_object(f"{name}-shade-{frame}", fbm, mats, coll), [frame]))
    return objs


def main():
    sprite = common.load_sprite(ROOT, NAME)
    out = L.preview_arg()
    for suffix, frames, centres in STAGES:
        name = NAME + suffix
        objs = build(sprite, name, centres)
        common.export_sprite_model(ROOT, objs, f"enemies/{name}", L.frames_subset(sprite, frames))
        if out:
            png = out if not suffix else out.parent / f"{name}.png"
            common.render_preview(objs, str(png), L.frame_image(ROOT, sprite, frames[0]), size=1, frame=frames[0])
        if "--frames" in sys.argv and len(frames) > 1:
            sub = {**sprite, "frames": [f for f in sprite["frames"] if f["index"] in frames]}
            common.render_frame_previews(objs, str(Path(sys.argv[sys.argv.index("--frames") + 1]) / f"{name}.png"),
                                         sub, ROOT)
        for o in objs:
            o.hide_render = True


if __name__ == "__main__":
    main()
