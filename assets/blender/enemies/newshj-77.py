"""Green-eyed ground pod (newshj.shp frames 77, 79, 81): a 3D version of its sprite.

Seen in episode 2 (levels 2.2 and 2.24), set into the grass below a cliff. A squat grey puck
with a light bevelled rim, a dark socket on top and a green glass lens in it. The three frames
only brighten the lens and move the pod down a pixel each, so one model covers them all: a copy
of the pod per frame (common.frame_part), each a pixel lower, and a lens whose colour steps up
(palette_material frames=). The lens glows.

Run: blender --background --python assets/blender/enemies/newshj-77.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b109 as lib  # noqa: E402
from lib_b109 import PX, common  # noqa: E402

NAME = "newshj-77"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)


def ellipse(cx, cy, rx, ry, n=24):
    import math
    return [(G.x(cx) + rx * PX * math.cos(2 * math.pi * i / n), G.y(cy) + ry * PX * math.sin(2 * math.pi * i / n))
            for i in range(n)]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    anim = lambda i, part, frames, **kw: common.palette_material(  # noqa: E731
        sprite, i, f"{NAME}-{part}", frames=frames, **kw)
    mats = [
        pal(6, metallic=0.6, roughness=0.45),  # 0 dark grey side
        pal(9, metallic=0.65, roughness=0.35),  # 1 grey top
        pal(11, metallic=0.7, roughness=0.3),  # 2 light rim
        # The lens brightens over the frames: {sprite frame: palette index}.
        anim(193, "socket", {79: 194, 81: 196}, metallic=0.3, roughness=0.4),  # 3 dark green socket
        anim(201, "lens", {79: 203, 81: 205}, metallic=0.2, roughness=0.15, emission_strength=3.0),  # 4 green lens
        anim(206, "hot", {79: 207, 81: 207}, emission_strength=5.0),  # 5 lens highlight
        pal(3, metallic=0.5, roughness=0.6),  # 6 dark foot
    ]
    SIDE, TOP, RIM, SOCKET, LENS, HOT, FOOT = range(7)
    bm = bmesh.new()

    # The puck: a dark foot (columns 4-19, rows 17-26), its grey body with a light bevelled rim.
    lib.prism(bm, ellipse(11.9, 21.7, 8.6, 5.9), 0.0, 0.06, mat=FOOT)
    lib.prism(bm, ellipse(11.9, 21.4, 8.3, 5.6), 0.05, 0.19, mat=SIDE, bevel=0.04, side_mat=SIDE, top_mat=TOP)
    lib.prism(bm, ellipse(11.8, 21.0, 7.0, 4.3, n=20), 0.18, 0.205, mat=RIM, bevel=0.012, top_mat=TOP)
    # The socket and the green lens (columns 8-15, rows 18-22).
    lib.dome(bm, G.x(11.9), G.y(20.5), 5.0 * PX, 3.2 * PX, 0.035, z0=0.2, sides=20, rings=3, mat=SOCKET)
    lib.dome(bm, G.x(11.9), G.y(20.3), 4.3 * PX, 2.7 * PX, 0.08, z0=0.21, sides=20, rings=4, mat=LENS)
    lib.ellipsoid(bm, G.x(11.0), G.y(19.8), 0.275, 1.2 * PX, 0.8 * PX, 0.015, segments=10, rings=4, mat=HOT)

    obj = lib.to_object(NAME, bm, mats, coll)
    # The pod sits a pixel lower on each frame (its top at row 15, 16, 17): a copy of it per frame,
    # moved down.
    parts = [common.frame_part(obj, [77])]
    for frame, down in ((79, 1), (81, 2)):
        copy = bpy.data.objects.new(f"{NAME}-{frame}", obj.data.copy())
        copy.data.name = copy.name
        copy.data.transform(Matrix.Translation((0.0, -down * PX, 0.0)))
        coll.objects.link(copy)
        parts.append(common.frame_part(copy, [frame]))
    return parts


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objs = build(sprite)
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"])
    out = lib.preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview(objs, str(out), ref, size=sprite["frames"][0]["size"], frame=77)
    if "--frames" in sys.argv:
        common.render_frame_previews(objs, sys.argv[sys.argv.index("--frames") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
