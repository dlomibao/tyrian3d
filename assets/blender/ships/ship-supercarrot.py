"""SuperCarrot (player ship, tyrian.shp#8 frame 119 and its banking frames 115-123): a 3D version
of its sprite.

A flying carrot, point up the screen: a root as round in section as it is wide, one matte orange
lit by the game (the sprite's outline, red flanks and yellow highlight are its drawn light), one
glossy brown eye sunk in a dark socket, and a tuft of three flat matte green leaves trailing
behind. Centred on sprite column 11.5.

Run: blender --background --python assets/blender/ships/ship-supercarrot.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b002 import P, X, Y, dome, loft, tube  # noqa: E402

NAME = "ship-supercarrot"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.5  # the middle of sprite column 11
EYE = (11.5, 11.0)  # the eye's centre (pixel edges): columns 9-13, rows 9-12, socket below
BODY_SHADE = 121  # the root's mid-tone orange (the sprite's commonest body colour)
IRIS_SHADE = 183  # the eye's mid-tone brown
SOCKET_SHADE = 176  # the eye socket's dark rim
LEAF_SHADE = 198  # the leaves' mid-tone green
STEM_SHADE = 196  # the stem, a shade darker as drawn


def _densify(points, step=0.8):
    """A leaf's path with extra points about `step` px apart (linear in every value), so its
    faceted blade bends smoothly along the path."""
    out = [points[0]]
    for p0, p1 in zip(points, points[1:]):
        n = max(1, round(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / step))
        for k in range(1, n + 1):
            t = k / n
            out.append(tuple(a + (b - a) * t for a, b in zip(p0, p1)))
    return out


def build(sprite):
    coll = common.reset_collection(NAME)

    BODY, IRIS, LEAF, STEM, SOCKET = range(5)  # part tags, repainted with palette indices below
    bm = bmesh.new()

    # The root, tip (row 0) to its back (row 19): (row, half width px) at the pixel rows' edges, so
    # each band of faces is one sprite row and each row's centre falls inside the sprite's row
    # (outline pixels included). Round in section: as thick as it is wide.
    body = [(0.0, 0.0), (1.0, 0.85), (2.0, 1.3), (3.0, 1.85), (4.0, 2.4), (5.0, 2.9), (6.0, 3.35),
            (7.0, 3.9), (8.0, 4.3), (9.0, 4.6), (10.0, 4.95), (11.0, 5.3), (12.0, 5.6), (13.0, 5.95),
            (14.0, 6.3), (15.0, 6.4), (16.0, 6.3), (17.0, 5.9), (18.0, 5.0), (19.0, 3.6), (19.2, 2.0),
            (19.3, 0.0)]
    before = set(bm.verts)
    loft(bm, [(r, AXIS, w, w, 0.0) for r, w in body], sides=36, mat=BODY)
    # The eye socket: a bowl about 6 px across and 1.4 px deep pressed into the top of the root.
    R, D = 3.3, 1.4
    for v in set(bm.verts) - before:
        if v.co.z <= 0:
            continue
        d = math.hypot(v.co.x - X(EYE[0]), v.co.y - Y(EYE[1])) * 12
        if d < R:
            v.co.z -= P(D * (1 - (d / R) ** 2))

    # The iris (brown, 5 px) rising out of the socket to just above the surface; its glossy
    # material catches the light where the sprite draws a pale pixel.
    dome(bm, EYE[0], EYE[1], 2.3, 2.15, 1.75, z=4.25, rings=4, sides=16, mat=IRIS)

    # The socket's dark rim: a thin ring round the iris lying in the bowl (about 1 px wide).
    def surface(col, row):
        """Height (px) of the root's top at (col, row), with the socket's bowl pressed in."""
        hw = next(w0 + (w1 - w0) * (row - r0) / (r1 - r0)
                  for (r0, w0), (r1, w1) in zip(body, body[1:]) if r0 <= row <= r1)
        z = math.sqrt(max(hw * hw - (col - AXIS) ** 2, 0))
        d = math.hypot(col - EYE[0], row - EYE[1])
        return z - (D * (1 - (d / R) ** 2) if d < R else 0)

    n, k, rt = 20, 6, 0.5
    loops = []
    for i in range(n):
        t = 2 * math.pi * i / n
        cx, cy = EYE[0] + 2.35 * math.cos(t), EYE[1] + 0.25 + 2.05 * math.sin(t)  # dark below, as drawn
        z = surface(cx, cy) + 0.1
        loops.append([bm.verts.new((X(cx + rt * math.cos(t) * math.cos(a)), Y(cy + rt * math.sin(t) * math.cos(a)),
                                    P(z + rt * math.sin(a))))
                      for a in (2 * math.pi * j / k for j in range(k))])
    for i in range(n):
        l0, l1 = loops[i], loops[(i + 1) % n]
        for j in range(k):
            bm.faces.new((l0[j], l0[(j + 1) % k], l1[(j + 1) % k], l1[j])).material_index = SOCKET

    # The stem and three flat leaves (about 1 px thick, rounded edges) traced over the sprite's
    # outline: (col, row, half width, half height, z).
    tube(bm, [(AXIS, 18.2, 2.3, 1.4, 0.0), (AXIS, 19.5, 2.25, 1.0, -0.1), (11.0, 20.8, 1.9, 0.6, -0.2)],
         sides=8, mat=STEM, power=0.6)
    leaves = [
        # Left: out from the stem and down to column 5 at row 26.
        [(10.0, 20.6, 1.0, 0.45, -0.2), (8.6, 21.5, 1.8, 0.45, -0.3), (7.2, 22.9, 1.7, 0.45, -0.4),
         (6.2, 24.6, 1.1, 0.4, -0.5), (5.7, 26.2, 0.5, 0.3, -0.5), (5.5, 26.9, 0, 0, -0.5)],
        # Middle: the broad centre straight back to row 27.
        [(11.0, 20.6, 1.8, 0.5, -0.2), (11.3, 22.4, 2.7, 0.5, -0.3), (11.4, 24.5, 2.3, 0.45, -0.4),
         (11.0, 25.5, 1.8, 0.4, -0.5), (10.6, 26.5, 1.3, 0.3, -0.5), (11.1, 27.4, 0.9, 0.3, -0.5),
         (11.3, 28.0, 0, 0, -0.5)],
        # Right: out to column 15 at rows 22-24.
        [(12.0, 21.5, 1.0, 0.45, -0.2), (13.3, 22.2, 1.8, 0.45, -0.3), (14.2, 23.5, 1.7, 0.4, -0.4),
         (14.9, 24.5, 1.3, 0.4, -0.4), (15.8, 24.9, 0, 0, -0.4)],
    ]
    for leaf in leaves:
        # A thin blade with a midrib and bevelled edges, flat shaded.
        tube(bm, _densify([(c, r, w * 1.15, h, z) for c, r, w, h, z in leaf]), sides=10, mat=LEAF)

    # Paint each part its mid-tone and let the game's lights shade it (rubric: the sprite's lighting
    # is not paint): the sprite's black outline ring, its red lower-right flanks and its yellow
    # highlight are the light on a round root, and the game draws its own outline. A carrot and
    # its leaves are organic, so matte; the eye is wet and glossy, so its shine (the sprite's pale
    # pixel at column 11, row 11) comes from the lights, not from geometry. Only the eye socket
    # (a real recess with a dark rim, drawn black under the eye) keeps a dark colour.
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    slots, mats = {}, []

    def slot(i, **kw):
        if i not in slots:
            slots[i] = len(mats)
            mats.append(common.palette_material(sprite, i, NAME, **kw))
        return slots[i]

    for f in bm.faces:
        c = f.calc_center_median()
        col, row = c.x * 12 + 12, 14 - c.y * 12
        part = f.material_index
        f.smooth = part != LEAF  # the leaves stay flat shaded
        if part == BODY:
            if c.z > 0 and math.hypot(col - EYE[0], row - EYE[1]) < 2.1:
                f.material_index = slot(SOCKET_SHADE, metallic=0.0, roughness=0.8)  # under the iris
            else:
                f.material_index = slot(BODY_SHADE, metallic=0.0, roughness=0.55)
        elif part == IRIS:
            f.material_index = slot(IRIS_SHADE, metallic=0.0, roughness=0.2)
        elif part == SOCKET:
            f.material_index = slot(SOCKET_SHADE, metallic=0.0, roughness=0.8)
        elif part == STEM:
            f.material_index = slot(STEM_SHADE, metallic=0.0, roughness=0.8)
        else:  # the leaves
            f.material_index = slot(LEAF_SHADE, metallic=0.0, roughness=0.8)

    bm.faces.index_update()
    flat = {f.index for f in bm.faces if not f.smooth}
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    for poly in obj.data.polygons:
        poly.use_smooth = poly.index not in flat
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = ROOT / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], out, ref, size=level["size"])


if __name__ == "__main__":
    main()
