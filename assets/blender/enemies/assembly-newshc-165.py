"""Reactor and blue turret (newshc.shp, assembly of newshc-165 and newshc-155): 3D versions of
their sprites.

Seen in episode 3 (level 3.6): a column of ground pieces, a reactor (newshc-165) above and below
a blue turret (newshc-155), with more machinery under them from another batch.

- newshc-165: a split blue orb (two glossy half domes with a pink rod in the slot between them)
  between two glowing red-orange crescent arcs. Its three frames only brighten the arcs, so one
  model covers them.
- newshc-155: a blue hood of two lobes with green strips on its corners, a grey housing with dark
  ports, a purple cannon tilted up toward the bottom of the screen and a grey bracket on the
  ground in front. Its frames only light the green corner lights, so one model covers them.

Both are built in assembly coordinates (screen pixel cx 57, cy 53 is the origin) and cut into
the pieces with common.split_assembly. The second newshc-165 in the layout uses the same model.

Run: blender --background --python assets/blender/enemies/assembly-newshc-165.py [-- --preview out.png]
(each piece gets <piece>.png in the preview's folder, the whole column gets out.png).
"""

import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from lib_b097 import (PX, X, Y, YE, ellipsoid, mirror_x, new_faces, pbox, snapshot, sweep,  # noqa: E402
                      to_object, translate, turret_base)

NAME = "assembly-newshc-165"
ROOT = common.repo_root(__file__)
PIECES = ["newshc-165", "newshc-155"]
CX0, CY0 = 57, 53  # assembly origin in screen pixels: between newshc-165 (cy 39) and newshc-155 (cy 67)


def reactor(bm, M):
    """newshc-165 in its own coordinates."""
    # Crescent arcs, top one built on the left half and mirrored, then copied to the bottom.
    # Path of the bright core (column, row) from the tip at the side to the centre.
    core = [(0.9, 11.0, 0.0, 0.0), (1.1, 9.8, 1.3, 0.07), (1.6, 8.4, 1.8, 0.09), (2.3, 7.1, 2.1, 0.1),
            (3.2, 5.9, 2.3, 0.11), (4.6, 4.7, 2.5, 0.115), (6.4, 3.6, 2.7, 0.12), (8.6, 2.9, 2.9, 0.12),
            (11.5, 2.6, 3.0, 0.12)]
    path = [(X(c), Y(r), 0.13, w * PX, h) for c, r, w, h in core]
    path += [(-x, y, z, w, h) for x, y, z, w, h in reversed(path[:-1])]
    for flip in (1, -1):
        sweep(bm, [(x, flip * y, z, w, h) for x, y, z, w, h in path], sides=10, mat=M["arc"])
        # Hot core along the arc's crest.
        hot = [(x, flip * y, z + h * 0.82, w * 0.35, h * 0.3) for x, y, z, w, h in path[2:-2]]
        sweep(bm, hot, sides=6, mat=M["hot"])
        # Dark red cradle under the arc.
        sweep(bm, [(x, flip * y, 0.03, w * 1.05, 0.03) for x, y, _, w, _ in path[1:-1]], sides=6,
              mat=M["cradle"], smooth=False)

    # The orb: two glossy half domes either side of a slot (columns 4-9 and 14-19, rows 9-18).
    snap = snapshot(bm)
    ellipsoid(bm, 0.0, 0.0, 0.0, 8.3 * PX, 5.3 * PX, 0.34, M["orb"], segments=24, rings=10, dome=True)
    dome = new_faces(bm, snap)
    geom = list({v for f in dome for v in f.verts}) + list({e for f in dome for e in f.edges}) + list(dome)
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(-2.0 * PX, 0, 0), plane_no=(1, 0, 0), clear_outer=True)
    cut = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    for f in bmesh.ops.holes_fill(bm, edges=cut, sides=0)["faces"]:
        f.material_index = M["orb"]
        f.smooth = False
    mirror_x(bm, snap)  # the right half
    # Highlight caps on each half (the pale 61-63 patch at columns 6-8 and 15-17, rows 11-12).
    for side in (-1, 1):
        ellipsoid(bm, side * 4.6 * PX, 1.8 * PX, 0.2, 2.2 * PX, 1.5 * PX, 0.115, M["orb_hi"], segments=10, rings=4)
    # Dark slot between the halves and the pink rod lying in it.
    pbox(bm, 10, 9, 13, 18, 0.0, 0.1, M["slot"])
    sweep(bm, [(0.0, YE(8.9), 0.12, 0.0, 0.0), (0.0, YE(9.3), 0.16, 1.0 * PX, 0.06),
               (0.0, YE(11.5), 0.2, 1.1 * PX, 0.09), (0.0, YE(16.5), 0.19, 1.1 * PX, 0.09),
               (0.0, YE(18.7), 0.15, 1.0 * PX, 0.06), (0.0, YE(19.1), 0.11, 0.0, 0.0)], sides=8, mat=M["rod"])


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshc165", **kw)  # noqa: E731
    mats = [
        pal(119, emission_strength=3.0),  # 0 glowing arc
        pal(123, emission_strength=5.0),  # 1 hot core of the arc
        pal(114, metallic=0.4, roughness=0.5),  # 2 dark red cradle
        pal(59, metallic=0.6, roughness=0.15),  # 3 blue glass orb
        pal(62, metallic=0.5, roughness=0.1),  # 4 orb highlight
        pal(51, metallic=0.3, roughness=0.6),  # 5 dark slot
        pal(76, metallic=0.5, roughness=0.3),  # 6 pink rod
        pal(57, metallic=0.2, roughness=0.4),  # 7 blue hood
        pal(60, metallic=0.4, roughness=0.3),  # 8 hood highlight
        pal(52, metallic=0.3, roughness=0.6),  # 9 dark blue skirt
        pal(39, metallic=0.3, roughness=0.5),  # 10 green corner strips
        pal(106, metallic=0.6, roughness=0.35),  # 11 grey housing
        pal(109, metallic=0.6, roughness=0.3),  # 12 housing top edge
        pal(98, metallic=0.4, roughness=0.6),  # 13 dark ports
        pal(2, metallic=0.2, roughness=0.8),  # 14 dark floor
        pal(7, metallic=0.6, roughness=0.4),  # 15 bracket rails
        pal(4, metallic=0.5, roughness=0.5),  # 16 bracket top bar
        pal(9, metallic=0.6, roughness=0.35),  # 17 centre rod
        pal(91, metallic=0.4, roughness=0.35),  # 18 purple cannon
        pal(89, metallic=0.4, roughness=0.4),  # 19 cannon muzzle rim
        pal(82, metallic=0.2, roughness=0.7),  # 20 bore
        pal(202, emission_strength=2.0),  # 21 green corner lights
        pal(93, metallic=0.4, roughness=0.3),  # 22 cannon highlight
    ]
    M = dict(arc=0, hot=1, cradle=2, orb=3, orb_hi=4, slot=5, rod=6, hood=7, hood_hi=8, skirt=9,
             corner=10, housing=11, housing_hi=12, port=13, floor=14, rail=15, bar=16, rod_grey=17,
             cannon=18, rim=19, bore=20, light=21, cannon_hi=22)
    bm = bmesh.new()

    # newshc-165 (screen cy 39 -> 14 px above the origin).
    snap = snapshot(bm)
    reactor(bm, M)
    translate(bm, snap, dy=14 * PX)

    # newshc-155 (screen cy 67 -> 14 px below the origin).
    snap = snapshot(bm)
    MB = dict(M, rod=M["rod_grey"])
    turret_base(bm, MB, M["corner"])
    # Green lights on the corner strips (columns 2-3, rows 4-6).
    for side in (-1, 1):
        pts = [(3.6, 3.9, 0.0), (3.2, 4.4, 0.8), (2.5, 5.6, 0.8), (2.2, 6.3, 0.0)]
        sweep(bm, [(-side * X(c), Y(r), MB["_on_lobe"](X(c), Y(r), 0.025), w * PX, 0.02 if w else 0.0)
                   for c, r, w in pts], sides=6, mat=M["light"])
    # The cannon: tilted up toward the bottom of the screen, the dark bore showing at rows 10-12.
    base = Vector((0.0, Y(5.2), 0.3))
    muzzle = Vector((0.0, Y(11.2), 0.56))
    axis = (muzzle - base).normalized()
    r = 2.9 * PX
    pts = [base - axis * 0.05, base, muzzle - axis * 0.06]
    sweep(bm, [(p.x, p.y, p.z, r, r) for p in pts], sides=14, mat=M["cannon"], up=(0, 1, 0))
    rim0, rim1 = muzzle - axis * 0.065, muzzle
    sweep(bm, [(rim0.x, rim0.y, rim0.z, r * 1.08, r * 1.08), (rim1.x, rim1.y, rim1.z, r * 1.08, r * 1.08)],
          sides=14, mat=M["rim"], up=(0, 1, 0))
    b0, b1 = muzzle - axis * 0.02, muzzle + axis * 0.004
    sweep(bm, [(b0.x, b0.y, b0.z, r * 0.72, r * 0.72), (b1.x, b1.y, b1.z, r * 0.72, r * 0.72)],
          sides=12, mat=M["bore"], up=(0, 1, 0))
    # A light strip along the cannon's back (the pale 92-95 pixels, rows 5-8).
    s0, s1 = base + Vector((0, 0, r * 0.95)), muzzle - axis * 0.08 + Vector((0, 0, r * 0.95)) * 0.9
    sweep(bm, [(s0.x, s0.y, s0.z, 0.9 * PX, 0.02), (s1.x, s1.y, s1.z, 0.9 * PX, 0.02)], sides=6, mat=M["cannon_hi"],
          up=(0, 1, 0))
    translate(bm, snap, dy=-14 * PX)

    return to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newshc-165's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshc-165")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The two pieces' first frames as one image, padded to the 24:28 shape that render_preview
    expects for size 4 (48 x 56 px, the column in the middle)."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        x0, y0 = cx + 24 - 12, cy + 28 - 14
        for r, line in enumerate(frame["pixels"]):
            for c, v in enumerate(line):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = []
    for e in sprite["assemblyLayout"]:
        if e["model"] in PIECES and e["model"] not in [n for n, _, _ in layout]:
            layout.append((e["model"], e["cx"] - CX0, e["cy"] - CY0))
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
