"""Blue asteroid (newsh5.shp frame 89): a 3D version of its sprite.

Seen in episode 4 (levels 22, 25, 31). A round, cracked blue rock: dark plates split by pale
veins. The model is a lumpy, flat-shaded boulder whose facets take the sprite's colour under them
(dark plates, mid blues, pale veins), with the veins standing slightly proud. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-89.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-89"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(50, metallic=0.1, roughness=0.85),  # 0 dark plates and underside
        pal(52, metallic=0.1, roughness=0.8),  # 1 dark blue
        pal(55, metallic=0.1, roughness=0.75),  # 2 mid blue
        pal(58, metallic=0.15, roughness=0.65),  # 3 light blue
        pal(61, metallic=0.2, roughness=0.5),  # 4 pale veins
    ]
    pixels = sprite["frames"][0]["pixels"]

    def slot(i):
        if i < 0:
            return None
        if i <= 50:
            return 0
        if i <= 53:
            return 1
        if i <= 55:
            return 2
        if i <= 57:
            return 3
        return 4

    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    # Refine the top (the part seen in game) once more so the facets can follow the veins.
    bm.normal_update()
    top = {e for f in bm.faces if f.normal.z > -0.15 for e in f.edges}
    bmesh.ops.subdivide_edges(bm, edges=list(top), cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])

    # Rock: the sprite's disc is columns 0-22 and rows 2-24 (centre column 11, row 13).
    cx, cy = lib.px(11), lib.row(13)
    rx, ry, rz = 11.3 / 12, 11.3 / 12, 0.34
    rng = lib.jitter(89)
    lumps = [(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.05, 0.12)) for _ in range(9)]
    for v in bm.verts:
        n = v.co.normalized()
        bump = 1.0
        for lx, ly, lz, s in lumps:
            d = (n.x - lx) ** 2 + (n.y - ly) ** 2 + (n.z - lz) ** 2
            bump += s * max(0.0, 1 - d / 0.6) - s * 0.3
        v.co.x = cx + n.x * rx * bump
        v.co.y = cy + n.y * ry * bump
        v.co.z = n.z * rz * bump
    # Pale veins stand proud, dark cracks sink a little (only on the top).
    for v in bm.verts:
        if v.co.z <= 0.05:
            continue
        i = lib.sample(pixels, v.co.x, v.co.y)
        if i >= 0:
            v.co.z += (i - 54) * 0.003 * min(1.0, v.co.z / 0.15)

    lib.paint_from_sprite(bm, pixels, slot, under_slot=0, min_nz=-0.2, average=True)
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
