"""Molten rock (newshl.shp 115, newsh3.shp 134 and 135): a 3D version of its sprite.

Seen in episode 4 (levels 6, 40 and 45). A round lump of lava, 11 x 13 px: dark red crust broken by
orange and yellow glowing cracks. Frame 135 is the same rock glowing brighter (every index two
steps up), so one model covers all three frames, its colours stepping up on 135 (palette_material
frames=). The rock is a ball as tall as it is wide, its outline the sprite's rounded octagon, cut
along the pixel boundaries so each face of its top takes the colour of the sprite pixel under it
(one material per palette index); the mottling wraps round its sides and underside.

Run: blender --background --python assets/blender/enemies/newshl-115.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b006 as lib  # noqa: E402

NAME = "newshl-115"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def bump(x, y, z):
    """Gentle lumps so the rock isn't a perfect egg (applied to its height only, so the outline from
    above stays the sprite's)."""
    return 1 + 0.03 * math.sin(3.1 * x + 1.3) * math.cos(2.7 * y - 0.4) + 0.02 * math.sin(4.3 * z + 2.9 * x)


# The outline: rows 4-10 are full width, so the sprite is a rounded octagon rather than an ellipse.
# A superellipse of exponent P with semi-axes RX x RY px covers exactly its 119 pixels.
P = 2.2
RX, RY, RZ = 5.6, 6.6, 5.5  # px: a ball as tall as it is wide (11 px), 13 px long


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    grid = lib.Grid(12, 14, frame["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    used = sorted({v for row in frame["pixels"] for v in row if v >= 112})

    def glow(i):
        # The crust is dull; the cracks glow more the hotter they are.
        if i <= 115:
            return 0.0
        return round(min(3.0, 0.35 * (i - 115)), 2)

    # One material per palette index the sprite uses, so the colours are the sprite's own. Frame 135
    # is the same rock glowing two palette steps brighter: {sprite frame: index}.
    slots = {i: mats(i, metallic=0.0, roughness=max(0.35, 0.9 - 0.04 * (i - 112)),
                     emission_strength=glow(i), frames={135: i + 2}) for i in used}

    bm = bmesh.new()
    # Rows 1-13, columns 0-10: centred on column 5, row 7.
    cx, cy = grid.x(5), grid.y(7)
    a, b, c = RX * lib.U, RY * lib.U, RZ * lib.U

    # A unit sphere from a subdivided cube, reshaped: superellipse outline, round section.
    first = lib.cube_blob(bm, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), n=5, mat_index=slots[used[0]])
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        sx, sy, sz = v.co
        rh = math.hypot(sx, sy)
        f = 1.0
        if rh > 1e-6:
            ux, uy = abs(sx) / rh, abs(sy) / rh
            f = (ux ** P + uy ** P) ** (-1 / P)
        v.co = (cx + a * sx * f, cy + b * sy * f, c * sz * bump(sx, sy, sz))

    # Cut the surface along the sprite's pixel boundaries, so every face lies over one pixel and the
    # top view shows the pixels as squares.
    for col in range(1, 11):
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(grid.x(col) - lib.U / 2, 0, 0), plane_no=(1, 0, 0))
    for row in range(2, 14):
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, grid.y(row) + lib.U / 2, 0), plane_no=(0, 1, 0))

    # Paint: the cap seen from above takes the pixel straight below it. The sprite's dark outline
    # ring and everything below the cap take its mottling wrapped on round the sides and underneath
    # (sampled further in as it goes down), a step or two darker, so the rock is lava all over and
    # its dark rim comes from the lighting instead of a painted black band.
    W0 = 0.2
    bm.faces.ensure_lookup_table()
    for face in bm.faces[first:]:
        ctr = face.calc_center_median()
        w = max(-1.0, min(1.0, ctr.z / c))
        dx, dy = ctr.x - cx, ctr.y - cy
        rh = math.hypot(dx / a, dy / b)
        idx = grid.sample(ctr.x, ctr.y) if w >= W0 else None
        if idx is None or (idx == 112 and rh > 0.7):
            # The sprite's near-black outline ring (or the sides below the cap): wrapped mottling.
            t = (W0 - w) / (W0 + 1)  # 0 at the cap's edge, 1 at the bottom
            k = 0.82 * (1 - 0.7 * t)
            s = k / rh if rh > 1e-6 else 0.0
            idx = grid.sample(cx + dx * s, cy + dy * s, skip=(-1, 1, 112))
            if idx is not None:
                idx = max(113, idx - 3)
                while idx not in slots and idx > 112:
                    idx -= 1
        if idx is not None and idx in slots:
            face.material_index = slots[idx]
    obj = common.mesh_object(NAME, bm, mats.list, coll, smooth=True)

    # Shade it as the smooth ball it is: the pixel cuts leave slivers and n-gons whose averaged
    # normals would dent the shading, so set each vertex's normal from the shape's own gradient.
    from mathutils import Vector
    normals = []
    for v in obj.data.vertices:
        X, Y, Z = (v.co.x - cx) / a, (v.co.y - cy) / b, v.co.z / c
        R = (abs(X) ** P + abs(Y) ** P) ** (1 / P)
        gx = gy = 0.0
        if R > 1e-6:
            gx = R ** (2 - P) * abs(X) ** (P - 1) * math.copysign(1, X) / a
            gy = R ** (2 - P) * abs(Y) ** (P - 1) * math.copysign(1, Y) / b
        n = Vector((gx, gy, Z / c))
        normals.append(n.normalized() if n.length > 1e-9 else Vector((0, 0, 1)))
    obj.data.normals_split_custom_set_from_vertices(normals)
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)
    if "--frames" in sys.argv:
        common.render_frame_previews([obj], sys.argv[sys.argv.index("--frames") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
