"""Grey pod in a yoke (newsh5.shp frame 170): a 3D version of its sprite.

Seen in episode 4 (level 22). A bell-shaped grey metal pod hangs from a blue-grey yoke: a bar
across the top whose ends turn down as two arms beside the pod, with a small crest and a neck in
the middle. The pod's rounded top catches the light; its lower half is a dark face framed by a
grey lip and cheek ribs, with a glowing red core and two orange lights in it. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-170.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b051 as lib  # noqa: E402

NAME = "newsh5-170"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.5  # the pod's centre column

# Pod down the screen: (row, half width px, half height, z centre).
POD = [(5.0, 0.0, 0.0, 0.0), (5.3, 6.0, 0.12, 0.02), (6.2, 7.6, 0.17, 0.02), (7.6, 7.2, 0.21, 0.01),
       (9.2, 8.0, 0.25, 0.0), (11.5, 8.1, 0.26, 0.0), (14.0, 8.1, 0.25, 0.0), (17.0, 8.0, 0.22, -0.01),
       (20.5, 7.9, 0.2, -0.02), (22.8, 7.2, 0.17, -0.02), (24.2, 6.0, 0.14, -0.02), (25.3, 4.6, 0.09, -0.02),
       (25.8, 0.0, 0.0, -0.02)]


def pod_top(c, r):
    """Height of the pod's upper surface at pixel (c, r)."""
    for (r0, w0, h0, z0), (r1, w1, h1, z1) in zip(POD, POD[1:]):
        if r0 <= r <= r1:
            t = (r - r0) / (r1 - r0)
            w, h, z = w0 + (w1 - w0) * t, h0 + (h1 - h0) * t, z0 + (z1 - z0) * t
            u = min(1.0, abs(c - AXIS) / max(w, 1e-6))
            return z + h * (1 - u ** 2.4) ** (1 / 2.4)
    return 0.0


def build(sprite):
    coll = common.reset_collection(NAME)
    g = lib.sprite_grid(sprite)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(2, metallic=0.25, roughness=0.5),  # 0 near-black face
        pal(4, metallic=0.30, roughness=0.45),  # 1 dark grey
        pal(6, metallic=0.40, roughness=0.4),  # 2 mid grey
        pal(8, metallic=0.35, roughness=0.35),  # 3 light grey
        pal(10, metallic=0.45, roughness=0.3),  # 4 bright grey highlights
        pal(98, metallic=0.25, roughness=0.45),  # 5 dark blue-grey yoke
        pal(102, metallic=0.30, roughness=0.4),  # 6 blue-grey yoke
        pal(105, metallic=0.40, roughness=0.35),  # 7 light blue-grey
        pal(107, metallic=0.35, roughness=0.3),  # 8 bright blue-grey edges
        pal(114, metallic=0.15, roughness=0.4),  # 9 dark red socket
        pal(118, emission_strength=3.0),  # 10 red core
        pal(122, emission_strength=5.0),  # 11 orange lights
    ]
    DARK, GREY4, GREY6, GREY8, GREY10, YDARK, YOKE, YLIGHT, YEDGE, SOCKET, CORE, LIGHT = range(12)

    def grey(i):
        if i < 0 or i > 12:
            return None
        return DARK if i <= 1 else GREY4 if i <= 3 else GREY6 if i <= 5 else GREY8 if i <= 7 else GREY10

    def blue(i):
        if i < 96 or i > 111:
            return None
        return YDARK if i <= 99 else YOKE if i <= 103 else YLIGHT if i <= 105 else YEDGE

    bm = bmesh.new()

    # The pod, a squarish bell, painted with the greys of the pixels over it.
    lib.sweep(bm, g, [(AXIS, r, z, w, h) for r, w, h, z in POD], sides=18, mat=GREY6, power=0.85)
    lib.paint(bm, g, grey, under=DARK)

    # Grey lip across the top of the dark face (row 13) and the chin rim (rows 23-25).
    pts = [(c, 13.2, pod_top(c, 13.2) + 0.005, 0.75, 0.035) for c in [AXIS + 7.4 * math.sin(a) for a in
                                                                       [math.pi / 2 * (k / 6 - 1) for k in range(13)]]]
    lib.sweep(bm, g, pts, sides=6, mat=GREY10)
    # Cheek ribs slanting down beside the core (columns 5-8 and 15-18).
    for s in (-1, 1):
        rib = [(AXIS + s * 6.0, 14.6), (AXIS + s * 5.0, 17.0), (AXIS + s * 4.0, 20.0), (AXIS + s * 3.6, 22.6)]
        lib.sweep(bm, g, [(c, r, pod_top(c, r) + 0.004, 0.7, 0.03) for c, r in rib], sides=6, mat=GREY8)

    # The red core in a dark socket, with its two orange lights.
    zc = pod_top(AXIS, 20.0)
    lib.ellipsoid(bm, (g.X(AXIS), g.Y(20.0), zc - 0.01), (3.6 * lib.PX, 3.2 * lib.PX, 0.05), mat=SOCKET)
    lib.ellipsoid(bm, (g.X(AXIS), g.Y(20.0), zc + 0.01), (2.7 * lib.PX, 2.2 * lib.PX, 0.06), mat=CORE)
    for c in (10.0, 13.0):
        lib.ellipsoid(bm, (g.X(c), g.Y(20.0), zc + 0.05), (0.75 * lib.PX, 0.75 * lib.PX, 0.025),
                      segments=8, rings=4, mat=LIGHT)

    # The yoke: a bar across the top (rows 2-4) whose ends run down beside the pod (columns 0-2
    # and 21-23) and hook in under it at row 13.
    zy = 0.06
    for s in (-1, 1):
        x = lambda d: AXIS + s * d  # noqa: E731
        lib.sweep(bm, g, [(x(10.3), 0.0, zy, 0.0, 0.0), (x(10.4), 0.3, zy, 1.5, 0.07),
                          (x(10.4), 1.5, zy, 1.8, 0.09), (x(10.4), 7.0, zy, 1.8, 0.09),
                          (x(10.3), 10.5, zy - 0.01, 1.7, 0.09), (x(10.0), 12.4, zy - 0.03, 1.4, 0.08),
                          (x(9.1), 13.4, zy - 0.04, 1.2, 0.07), (x(8.4), 13.8, zy - 0.05, 0.0, 0.0)],
                  sides=10, mat=YOKE)
    lib.sweep(bm, g, [(1.2, 3.0, zy, 2.0, 0.08), (21.8, 3.0, zy, 2.0, 0.08)], sides=10, mat=YOKE)
    # Crest and neck in the middle (columns 11-13): the neck drops into the pod's top.
    lib.sweep(bm, g, [(12.0, 0.6, zy + 0.02, 0.0, 0.0), (12.0, 1.0, zy + 0.02, 1.3, 0.06),
                      (12.0, 2.8, zy + 0.03, 1.6, 0.1), (12.0, 4.4, zy, 1.6, 0.1), (12.0, 7.0, 0.1, 1.6, 0.12),
                      (12.0, 8.5, 0.12, 0.0, 0.0)], sides=10, mat=YLIGHT)
    lib.paint(bm, g, blue, start=0, keep={DARK, GREY4, GREY6, GREY8, GREY10, SOCKET, CORE, LIGHT}, under=YDARK)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
