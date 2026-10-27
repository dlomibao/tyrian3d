"""Green energy arrow (newsh5.shp frames 95, 209, 247): a 3D version of its sprite.

Seen in episode 4 (level 20). A small glowing green arrow pointing left: a faceted arrowhead
(columns 0-4) on a three-pixel shaft that runs to the right edge, with a white-hot core down its
middle. The three frames only fade its glow (bright, mid, dim green), so one model covers them;
the parts use the bright frame's palette indices and step down to the mid and dim greens on frames
209 and 247 (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newsh5-95.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b029 as lib  # noqa: E402

NAME = "newsh5-95"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(12, 14)


def ex(c):
    """Pixel edge (left edge of column c) to Blender X."""
    return G.X(c - 0.5)


def ey(r):
    """Pixel edge (top edge of row r) to Blender Y."""
    return G.Y(r - 0.5)


def bipyramid(bm, outline, apex, top, bottom, mat):
    """A faceted gem: an outline (Blender x, y, counter-clockwise) at z = 0 joined to an apex point
    (x, y) raised to `top` and lowered to `bottom`."""
    ring = [bm.verts.new((x, y, 0.0)) for x, y in outline]
    up = bm.verts.new((apex[0], apex[1], top))
    down = bm.verts.new((apex[0], apex[1], bottom))
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((ring[i], ring[j], up)).material_index = mat
        bm.faces.new((ring[j], ring[i], down)).material_index = mat


def build(sprite):
    coll = common.reset_collection(NAME)
    glow = lambda i, part, frames, **kw: common.palette_material(  # noqa: E731
        sprite, i, f"{NAME}-{part}", frames=frames, **kw)
    # Each colour fades on frame 209 (mid green) and 247 (dim green). The white core of the shaft
    # drops to the inner head's green, the head's hot cross only to the next brighter green.
    mats = [
        glow(199, "body", {209: 196, 247: 192}, metallic=0.1, roughness=0.3, emission_strength=2.5),  # 0 green body
        glow(207, "inner", {209: 204, 247: 200}, metallic=0.1, roughness=0.25, emission_strength=4.0),  # 1 bright green inner head
        glow(47, "core", {209: 204, 247: 200}, metallic=0.0, roughness=0.2, emission_strength=6.0),  # 2 white-hot shaft core
        glow(47, "hot", {209: 207, 247: 203}, metallic=0.0, roughness=0.2, emission_strength=6.0),  # 3 white-hot head centre
    ]
    BODY, INNER, CORE, HOT = range(4)
    bm = bmesh.new()
    yc = G.Y(6)  # the arrow's axis (row 6)

    # Arrowhead: rows 3-9 at column 3-4, tip at column 0 (pixel edges).
    head = [(ex(0), yc), (ex(3), ey(3) - 0.2 / 12), (ex(5), ey(3)), (ex(5), ey(10)), (ex(3), ey(10) + 0.2 / 12)]
    head = [head[0], head[4], head[3], head[2], head[1]]  # counter-clockwise from the tip
    bipyramid(bm, head, (ex(3.4), yc), 0.07, -0.08, BODY)
    # Its bright inner chevron (the 207 pixels along the tip), standing a little proud.
    inner = [(ex(0.7), yc), (ex(3), ey(9.0)), (ex(4.0), ey(8.6)), (ex(4.0), ey(4.4)), (ex(3), ey(4.0))]
    bipyramid(bm, inner, (ex(2.9), yc), 0.105, -0.06, INNER)
    # White-hot centre of the head (the cross of 47 pixels at columns 2-4, rows 5-7).
    hot = [(ex(1.9), yc), (ex(3.5), ey(8.0)), (ex(4.6), yc), (ex(3.5), ey(5.0))]
    bipyramid(bm, hot, (ex(3.4), yc), 0.125, -0.04, HOT)

    # Shaft: columns 4-11, rows 5-7, rounded, flat-ended at the right edge.
    n0 = len(bm.faces)
    lib.sweep(bm, [(ex(4.2), yc, 0.0, 1.5 / 12, 0.075), (ex(11.2), yc, 0.0, 1.5 / 12, 0.075),
                   (ex(12), yc, 0.0, 1.2 / 12, 0.055)], sides=10, mat=BODY)
    # White core down the middle (row 6, columns 2-9), its top just above the shaft's.
    lib.sweep(bm, [(ex(1.6), yc, 0.0, 0.0, 0.0), (ex(2.4), yc, 0.02, 0.6 / 12, 0.09),
                   (ex(9.6), yc, 0.02, 0.6 / 12, 0.075), (ex(10.4), yc, 0.02, 0.0, 0.0)], sides=8, mat=CORE)
    lib.faces_since(bm, n0, smooth=True)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])
    if "--frame-previews" in sys.argv:
        common.render_frame_previews([obj], sys.argv[sys.argv.index("--frame-previews") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
