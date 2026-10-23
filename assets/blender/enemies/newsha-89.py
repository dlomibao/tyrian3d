"""Glowing grate (newsha.shp frame 89): a 3D version of its sprite.

Seen in episode 1 (level 1.31). A rounded, slightly lopsided brown frame on the ground holding a
glowing red grate: two brown bars run diagonally (down to the left) across the hot red floor,
splitting it into three glowing stripes that are brightest along their middles. One frame, one
model.

Run: blender --background --python assets/blender/enemies/newsha-89.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b107 as lib  # noqa: E402

NAME = "newsha-89"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)

# Outer edge of the frame (pixel edges), from the dark brown edge pixels (index 17).
OUTLINE = [(10, 2.5), (13, 2.6), (16, 4.5), (19.5, 8), (20, 9), (20.2, 12.5), (20.6, 13.5),
           (20.6, 18), (17.5, 21.2), (15.5, 23), (12.5, 24.5), (9.5, 24.5), (6.5, 22.6),
           (4.5, 20.6), (4.5, 14.2), (3.5, 13.2), (3.5, 9), (6.5, 6), (9.5, 3)]
CENTRE = (12.0, 13.6)
TOP = 0.17  # top of the frame
FLOOR = 0.09  # the glowing floor, sunk in the frame
BARS = 0.135  # top of the brown bars


def scaled(outline, k):
    cx, cy = CENTRE
    return [(cx + (c - cx) * k, cy + (r - cy) * k) for c, r in outline]


def frame(bm, outer, inner, z0, z1, mat):
    """A flat ring between two outlines with the same vertex count."""
    o = [(G.x(c), G.y(r)) for c, r in outer]
    i = [(G.x(c), G.y(r)) for c, r in inner]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(o, o[1:] + o[:1]))
    if area < 0:
        o.reverse()
        i.reverse()
    n = len(o)
    ob = [bm.verts.new((x, y, z0)) for x, y in o]
    ot = [bm.verts.new((x, y, z1)) for x, y in o]
    ib = [bm.verts.new((x, y, z0)) for x, y in i]
    it = [bm.verts.new((x, y, z1)) for x, y in i]
    for k in range(n):
        j = (k + 1) % n
        for f in ((ob[k], ob[j], ot[j], ot[k]), (it[k], it[j], ib[j], ib[k]),
                  (ot[k], ot[j], it[j], it[k]), (ib[k], ib[j], ob[j], ob[k])):
            bm.faces.new(f).material_index = mat


def bar(bm, a, b, width_px, z0, z1, mat):
    """A straight bar between pixel-edge points a and b, width_px wide."""
    pa, pb = Vector((G.x(a[0]), G.y(a[1]))), Vector((G.x(b[0]), G.y(b[1])))
    d = (pb - pa).normalized()
    n = Vector((-d.y, d.x)) * width_px * lib.PX / 2
    pts = [pa + n, pb + n, pb - n, pa - n]
    before = set(bm.faces)
    common.slab(bm, [(p.x, p.y) for p in pts], z1 - z0, z=(z0 + z1) / 2)
    for f in set(bm.faces) - before:
        f.material_index = mat


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(22, metallic=0.2, roughness=0.6),  # 0 brown frame
        pal(26, metallic=0.25, roughness=0.5),  # 1 light inner lip
        pal(118, emission_strength=2.0),  # 2 red glowing floor
        pal(121, emission_strength=3.5),  # 3 bright middles of the stripes
        pal(25, metallic=0.25, roughness=0.55),  # 4 brown bars
        pal(123, emission_strength=5.0),  # 5 hottest spot
    ]
    FRAME, LIP, RED, HOT, BAR, CORE = range(len(mats))
    bm = bmesh.new()

    inner = scaled(OUTLINE, 0.85)
    lip = scaled(OUTLINE, 0.77)
    frame(bm, OUTLINE, inner, 0.0, TOP, FRAME)
    frame(bm, inner, lip, 0.0, TOP - 0.025, LIP)
    lib.plate(bm, G, lip, 0.0, FLOOR, mat=RED)

    # Brighter lines along the middles of the three stripes (parallel to the bars).
    for a, b in (((11.5, 6.0), (6.0, 11.5)), ((16.2, 8.6), (7.6, 17.2)), ((17.6, 13.9), (13.9, 17.6))):
        bar(bm, a, b, 1.3, FLOOR - 0.01, FLOOR + 0.008, HOT)
    lib.ellipsoid(bm, G, 11.9, 13.4, FLOOR, 1.3, 1.3, 0.012, mat=CORE, segments=8, rings=4)

    # Two diagonal bars, down to the left (pixel centres on c + r = 20 and 28).
    bar(bm, (14.2, 6.8), (5.8, 15.2), 2.6, FLOOR - 0.01, BARS, BAR)
    bar(bm, (18.2, 10.8), (8.2, 20.8), 2.6, FLOOR - 0.01, BARS, BAR)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = lib.preview_args()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
