"""SuperCarrot (player ship, tyrian.shp#8 frame 119 and its banking frames 115-123): a 3D version
of its sprite.

A flying carrot, point up the screen: a root as round in section as it is wide, painted face by
face from the sprite pixel under it (dark outline shoulder, red rim, orange, a yellow highlight),
one brown eye with a glowing pupil sunk in a dark socket, and a tuft of three flat green leaves trailing behind. Centred on sprite column 11.5.

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
OUTLINE = 112  # the sprite's black outline: the steep sides of the root and the leaves' edges
BODY_RAMP = (117, 126)  # red .. pale yellow
LEAF_RAMP = (192, 203)  # dark .. bright green
EYE_SHADES = {176, 180, 181, 182, 183, 184, 185, 186}


def _densify(points, step=0.8):
    """A leaf's path with extra points about `step` px apart (linear in every value), so its
    faces are about a sprite pixel long and take the shade of the pixel under them."""
    out = [points[0]]
    for p0, p1 in zip(points, points[1:]):
        n = max(1, round(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / step))
        for k in range(1, n + 1):
            t = k / n
            out.append(tuple(a + (b - a) * t for a, b in zip(p0, p1)))
    return out


def build(sprite):
    coll = common.reset_collection(NAME)
    pixels = sprite["frames"][len(sprite["frames"]) // 2]["pixels"]  # frame 119, level flight

    def at(col, row):
        c, r = int(math.floor(col)), int(math.floor(row))
        return pixels[r][c] if 0 <= r < len(pixels) and 0 <= c < len(pixels[0]) else -1

    BODY, IRIS, PUPIL, LEAF, STEM, SOCKET = range(6)  # part tags, repainted with palette indices below
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

    # The iris (brown, 5 px) rising out of the socket to just above the surface, and the glowing
    # pupil (the pale pixel at column 11, row 11) on it.
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
    dome(bm, 11.5, 11.5, 0.75, 0.75, 0.35, z=5.85, rings=2, sides=8, mat=PUPIL)

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
        # A thin blade with a midrib and bevelled edges, flat shaded; about a pixel per face so
        # each face takes the shade of the sprite pixel under it.
        tube(bm, _densify([(c, r, w * 1.15, h, z) for c, r, w, h, z in leaf]), sides=10, mat=LEAF)

    # Paint with the sprite's palette shades, face by face from the sprite pixel under the face's
    # centre: seen from above the model shows the sprite's own colours. Shades are smoothed a
    # little with the pixel's neighbours on the same ramp so the round root grades instead of
    # breaking into patches. The steep sides under the sprite's black outline pixels take the
    # outline colour (the outline is the root's shaded flank); faces underneath, which the sprite
    # never shows, take the part's darkest shade.
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    slots, mats = {}, []

    def slot(i, **kw):
        if i not in slots:
            slots[i] = len(mats)
            mats.append(common.palette_material(sprite, i, NAME, **kw))
        return slots[i]

    def half_width(row):
        """The root's half width (px) at a sprite row."""
        return next((w0 + (w1 - w0) * (row - r0) / (r1 - r0)
                     for (r0, w0), (r1, w1) in zip(body, body[1:]) if r0 <= row <= r1), 0.0)

    def ramp_mean(col, row, ramp, sigma=0.6):
        """The sprite's shade at the point (col, row) on the ramp, blurred: a Gaussian-weighted
        mean of the pixels on the ramp within 2 px (pixels of other colours are ignored)."""
        lo, hi = ramp
        tot = n = 0
        for dc in (-2, -1, 0, 1, 2):
            for dr in (-2, -1, 0, 1, 2):
                v = at(col + dc, row + dr)
                if lo <= v <= hi:
                    px, py = math.floor(col + dc) + 0.5, math.floor(row + dr) + 0.5
                    w = math.exp(-((px - col) ** 2 + (py - row) ** 2) / (2 * sigma * sigma))
                    tot, n = tot + w * v, n + w
        return round(tot / n) if n > 0.05 else None

    def nearest_ramp(col, row, ramp, fallback):
        """ramp_mean, or the nearest pixel on the ramp within 2 px when this one isn't on it."""
        m = ramp_mean(col, row, ramp)
        if m is not None:
            return m
        best = None
        for dc in (-2, -1, 0, 1, 2):
            for dr in (-2, -1, 0, 1, 2):
                m = ramp_mean(col + dc, row + dr, ramp)
                if m is not None and (best is None or dc * dc + dr * dr < best[0]):
                    best = (dc * dc + dr * dr, m)
        return best[1] if best else fallback

    for f in bm.faces:
        c = f.calc_center_median()
        col, row = c.x * 12 + 12, 14 - c.y * 12
        s = at(col, row)
        nz = f.normal.z
        part = f.material_index
        f.smooth = part != LEAF  # the leaves stay flat shaded
        if part == BODY:
            dx = col - AXIS
            r = math.hypot(dx, c.z * 12) or 1
            up = c.z * 12 / r  # 1 = on top, 0 = the flank, -1 underneath
            if c.z > 0 and math.hypot(col - EYE[0], row - EYE[1]) < 2.1:
                i = 176  # the bottom of the socket, under the iris
            elif up < -0.35:
                i = 117  # underneath, which the sprite never shows
            elif up < 0.1 or half_width(row) - abs(dx) < 1.0:
                i = OUTLINE  # the dark flank: the sprite's 1 px outline is the root's shaded side
            elif s == 176:
                i = 176  # the socket's shadow under the eye
            else:
                i = nearest_ramp(col, row, BODY_RAMP, 121)
            f.material_index = slot(i, metallic=0.0, roughness=0.9 if i == OUTLINE else 0.6 if i == 176 else 0.55)
        elif part == IRIS:
            i = s if s in EYE_SHADES else 183
            f.material_index = slot(i, metallic=0.1, roughness=0.35)
        elif part == SOCKET:
            f.material_index = slot(176, metallic=0.0, roughness=0.6)
        elif part == PUPIL:
            f.material_index = slot(126, emission_strength=4.0)
        else:  # the leaves and the stem
            if nz < -0.3:
                i = 193  # underneath
            elif s == OUTLINE:
                i = OUTLINE  # the leaves' dark edges
            else:
                i = nearest_ramp(col, row, LEAF_RAMP, 195)
            f.material_index = slot(i, metallic=0.0, roughness=0.9 if i == OUTLINE else 0.85)

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
