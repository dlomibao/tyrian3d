"""Red spiked mine (newsh5.shp frame 76): a 3D version of its sprite.

Seen in episode 4 (level 22). A small red ball with four spikes (up, down, left, right), short
studs between them and a hot orange-white core glowing through its top-left. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-76.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-76"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
SIZE = 1


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(118, metallic=0.1, roughness=0.4, emission_strength=0.8),  # 0 bright mid red shell
        pal(115, metallic=0.2, roughness=0.4),  # 1 spikes (dark red, as the sprite draws them)
        pal(121, metallic=0.1, roughness=0.35, emission_strength=2.0),  # 2 orange glow (top left)
        pal(123, emission_strength=2.5),  # 3 yellow-orange glow
        pal(127, emission_strength=3.0),  # 4 white-hot spot
        pal(113, metallic=0.1, roughness=0.5, emission_strength=0.3),  # 5 dark red (rim, underside)
        pal(119, metallic=0.1, roughness=0.35, emission_strength=1.0),  # 6 lit red
        pal(112, metallic=0.3, roughness=0.5),  # 7 dark studs on the diagonals
        pal(1, metallic=0.0, roughness=0.9),  # 8 the dark pit
        common.palette_material(sprite, 115, f"{NAME}-lower", metallic=0.1, roughness=0.45,
                                emission_strength=0.5),  # 9 darker red (lower half)
    ]
    SHELL, SPIKE, WARM, CORE, HOT, SHADE, LIT, STUD, PIT, DIM = range(10)
    P = 1 / 12  # one sprite pixel
    bm = bmesh.new()
    pixels = sprite["frames"][0]["pixels"]

    # Body: a true sphere centred on column 5, row 6, 9.2 px across and 9.2 px tall. It is a cube
    # sphere (even ~1 px faces, no pole fan on top); the four short corner cones fill the
    # sprite's square shoulders, so the plan stays round.
    cx, cy = lib.px(5, SIZE), lib.row(6, SIZE)
    R = 4.6 * P
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=8, use_grid_fill=True)
    for v in bm.verts:
        d = v.co.normalized() * R
        v.co = (d.x + cx, d.y + cy, d.z)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    body_faces = list(bm.faces)

    # Colour: no per-pixel shading paint (it doubled with the 3D lighting into a mottled maroon).
    # The ball is the sprite's bright mid red over its lit upper-left half, one shade darker over
    # the lower half (the sprite draws rows 7-10 darker even before lighting), and the
    # sprite's dark outer ring is a darker red on the steep rim; the underside is darker still.
    # The glow is painted where the sprite has it: the orange-yellow band across row 5 from the
    # left edge to the white-hot pixel (column 5, row 5), the yellow pixel above that, and the
    # sprite's own orange/yellow pixels (row 3 left and right, the top spike's root) where they are.
    def cell(f):
        c = f.calc_center_median()
        return lib.to_col(c.x, SIZE), lib.to_row(c.y, SIZE)

    def spx(col, rw):
        r, c = int(round(rw)), int(round(col))
        if 0 <= r < len(pixels) and 0 <= c < len(pixels[0]):
            return pixels[r][c]
        return -1

    for f in body_faces:
        if f.normal.z < -0.2:
            f.material_index = SHADE
            continue
        col, rw = cell(f)
        if math.hypot(col - 5, rw - 6) > 4.0:
            f.material_index = SHADE
            continue
        p = spx(col, rw)
        e = ((col - 3.2) / 2.5) ** 2 + ((rw - 4.9) / 0.9) ** 2
        if p >= 123 or e < 0.3:
            f.material_index = CORE
        elif p >= 120 or e < 1.0:
            f.material_index = WARM
        elif rw > 6.5:
            f.material_index = DIM
        else:
            f.material_index = SHELL
    up = [f for f in body_faces if f.normal.z > 0.3]

    def near(x, y, rad):
        hits = [f for f in up if math.hypot(f.calc_center_median().x - x, f.calc_center_median().y - y) < rad]
        return hits or [min(up, key=lambda f: (f.calc_center_median() - Vector((x, y, 0))).xy.length)]
    for f in near(lib.px(5, SIZE), lib.row(5, SIZE), 0.45 * P):
        f.material_index = HOT

    # The dark pit just below the centre (column 5, row 8): cut in about 1 px wide and 1.2 px deep.
    pitx, pity = lib.px(5, SIZE), lib.row(8, SIZE)
    pit = near(pitx, pity, 0.6 * P)
    res = bmesh.ops.inset_region(bm, faces=pit, thickness=0.08 * P, depth=-1.2 * P, use_even_offset=True)
    for f in pit + list(res["faces"]):
        f.material_index = PIT

    # Spikes on the equator: up and down 2 px past the body (3 px wide, then a 1 px tip), left and
    # right 1 px past it (3 px tall).
    for (dx, dy), (base, mid, tipd), (rb, rm) in (
            ((0, 1), (4.0, 5.2, 6.4), (1.8, 1.0)), ((0, -1), (4.0, 5.2, 6.4), (1.8, 1.0)),
            ((-1, 0), (4.0, 5.0, 5.9), (1.9, 1.15)), ((1, 0), (4.0, 5.0, 5.9), (1.9, 1.15))):
        pts = [(cx + dx * d * P, cy + dy * d * P, 0.0) for d in (base, mid, tipd)]
        lib.tube(bm, pts, [rb * P, rm * P, 0.0], sides=8, mat_index=SPIKE)
    # Short dark studs on the diagonals, out to the sprite's square corners.
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        ux, uy = math.cos(a), math.sin(a)
        lib.tube(bm, [(cx + ux * 4.4 * P, cy + uy * 4.4 * P, 0.0), (cx + ux * 6.2 * P, cy + uy * 6.2 * P, 0.0)],
                 [1.3 * P, 0.0], sides=6, mat_index=STUD)
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
