"""Ice crystal (newshd.shp frame 191): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.5, 2.8, 3.10, 3.15) lying on the ice fields. A long six-sided
crystal lying down the screen: a flat top face (bright, almost white down its lower half),
a blunt point at the bottom and a broken top end with three icy splinters sticking up the
screen (the longest on the left). One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-191.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b075 as L  # noqa: E402

NAME = "newshd-191"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

ZC, HH = 0.17, 0.22  # crystal axis height and half height: its flat bottom sits on the ground


def hex_loft(bm, col, sections, mat=0):
    """A six-sided loft down the sprite (rows) with a flat top face: sections are (row edge, half
    width px, half height); a zero width is a point."""
    before = set(bm.faces)
    cx = L.XE(col)
    rings = []
    for r, w, hh in sections:
        y = L.YE(r)
        if w == 0:
            rings.append([bm.verts.new((cx, y, ZC))])
            continue
        hw = w * L.PX
        rings.append([bm.verts.new((cx + hw * math.cos(a), y, ZC + hh * math.sin(a)))
                      for a in (math.radians(60 * k) for k in range(6))])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(6):
            j = (k + 1) % 6
            if len(r1) == 1:
                bm.faces.new((r0[k], r0[j], r1[0]))
            elif len(r0) == 1:
                bm.faces.new((r0[0], r1[j], r1[k]))
            else:
                bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if len(rings[0]) > 1:
        bm.faces.new(rings[0])
    if len(rings[-1]) > 1:
        bm.faces.new(list(reversed(rings[-1])))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = False


def splinter(bm, col, base_row, tip_row, w, lean=0.0, mat=0):
    """A thin four-sided icy splinter from the broken top end up the screen to a point."""
    before = set(bm.faces)
    cx = L.X(col)
    base = []
    for k in range(4):
        a = math.radians(45 + 90 * k)
        base.append(bm.verts.new((cx + w * L.PX * math.cos(a), L.YE(base_row), ZC + 0.6 * HH * math.sin(a))))
    tip = bm.verts.new((cx + lean * L.PX, L.YE(tip_row), ZC + 0.05))
    for k in range(4):
        bm.faces.new((base[k], base[(k + 1) % 4], tip))
    bm.faces.new(list(reversed(base)))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = False


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(60, metallic=0.1, roughness=0.12),  # 0 ice, right slope
        pal(63, metallic=0.05, roughness=0.08),  # 1 white top face (lower half)
        pal(62, metallic=0.1, roughness=0.1),  # 2 pale top face
        pal(58, metallic=0.15, roughness=0.2),  # 3 deep blue underside
        pal(59, metallic=0.1, roughness=0.15),  # 4 blue left slope, splinters
        pal(61, metallic=0.1, roughness=0.12),  # 5 light ice
    ]
    ICE, WHITE, PALE, DEEP, SPLINTER, LIGHT = range(6)
    bm = bmesh.new()

    # The crystal: 7 px wide (columns 8-14) from the broken top (row 4.5) to the point (row 28).
    hex_loft(bm, 11.5, [(4.6, 3.2, HH * 0.9), (5.6, 3.5, HH), (24.6, 3.5, HH), (25.6, 3.1, HH * 0.85),
                        (26.6, 2.4, HH * 0.65), (27.4, 1.4, HH * 0.4), (28.0, 0, 0)], mat=ICE)
    # Colour the facets: the two upper facets pale (white from row 12 down), the flanks deep blue.
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        n = f.normal
        cy = f.calc_center_median().y
        if n.z > 0.9:
            f.material_index = WHITE if L.YE(12.5) > cy > L.YE(25.5) else PALE
        elif n.z < -0.2:
            f.material_index = DEEP
        elif n.x < 0:
            f.material_index = SPLINTER
        elif cy < L.YE(10):
            f.material_index = LIGHT

    # Splinters off the broken top end: columns 9 (to row 0), 11 (to row 3) and 13 (to row 1).
    splinter(bm, 9.0, 5.8, 0.0, 1.5, lean=-0.2, mat=LIGHT)
    splinter(bm, 11.2, 5.4, 3.0, 1.4, mat=SPLINTER)
    splinter(bm, 13.1, 5.8, 1.0, 1.5, lean=0.2, mat=LIGHT)
    # A low shard behind the right splinter (the blue pixels at column 14, rows 4-7).
    splinter(bm, 14.0, 6.6, 4.0, 0.9, mat=DEEP)

    return L.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = L.preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], str(out), ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
