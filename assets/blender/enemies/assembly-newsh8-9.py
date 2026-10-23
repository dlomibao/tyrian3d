"""Rock worm and its burrow (newsh8.shp, assembly of newsh8-9 over newsh8-87): 3D versions of
their sprites.

Seen in episode 3 (level 3.4). newsh8-9 is a burrow in the rock: a rim of brown boulders round a
dark pit, with three rock fangs hanging off its lower lip. Over its frames a lumpy brown rock
worm pushes out of the pit and down the screen, over the lower lip; newsh8-87, the piece below
it, shows the worm's pointed tip coming on down. In the last frame (85) the burrow is gone and
only the worm is left, with a mushroom-shaped head.

The frames change shape, so each distinct stage gets its own model:
    newsh8-9     frames 9, 11    the empty burrow
    newsh8-9-f2  frame 13        the worm's tip shows in the pit
    newsh8-9-f3  frame 15        ... reaches the lower lip
    newsh8-9-f4  frame 17        ... hangs over it
    newsh8-9-f5  frame 47        ... runs on into the piece below
    newsh8-9-f6  frames 49, 51   the worm fills the lower half
    newsh8-9-f7  frames 53, 55   its head shows in the pit
    newsh8-9-f8  frame 85        the worm alone, head and body
    newsh8-87    frame 87        the tip, just entering the lower piece
    newsh8-87-f2 frame 89        ... longer
    newsh8-87-f3 frame 91        ... longer
    newsh8-87-f4 frames 93, 123  the whole tapering lower body

The worm's outline in each model comes from its frame (the pixels that differ from the empty
burrow), so its top view follows the sprite; it is lofted with lumpy rock rings and coloured from
the frame's own pixels. Each model is cut to its piece's 24x28 box with common.split_assembly,
so the two pieces meet on a flat seam (both have the same centre column; the lower piece sits
28 px below).

Run: blender --background --python assets/blender/enemies/assembly-newsh8-9.py [-- --preview out.png]
(the preview is newsh8-9-f7 over newsh8-87-f4; each model also gets <model>.png next to it).
"""

import math
import random
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b060 as L  # noqa: E402

NAME = "assembly-newsh8-9"
ROOT = common.repo_root(__file__)
UPPER, LOWER = "newsh8-9", "newsh8-87"

# (model name, piece, frames it covers, frame whose pixels shape it, burrow?)
MODELS = [
    ("newsh8-9", UPPER, [9, 11], 9, True),
    ("newsh8-9-f2", UPPER, [13], 13, True),
    ("newsh8-9-f3", UPPER, [15], 15, True),
    ("newsh8-9-f4", UPPER, [17], 17, True),
    ("newsh8-9-f5", UPPER, [47], 47, True),
    ("newsh8-9-f6", UPPER, [49, 51], 51, True),
    ("newsh8-9-f7", UPPER, [53, 55], 55, True),
    ("newsh8-9-f8", UPPER, [85], 85, False),
    ("newsh8-87", LOWER, [87], 87, False),
    ("newsh8-87-f2", LOWER, [89], 89, False),
    ("newsh8-87-f3", LOWER, [91], 91, False),
    ("newsh8-87-f4", LOWER, [93, 123], 93, False),
]

HOLE, DARK, MID, LIGHT, HIGH = range(5)


def materials(sprite):
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh8_9", **kw)  # noqa: E731
    return [
        pal(16, metallic=0.0, roughness=0.9),  # 0 the pit
        pal(19, metallic=0.05, roughness=0.85),  # 1 dark rock
        pal(22, metallic=0.05, roughness=0.8),  # 2 rock
        pal(25, metallic=0.05, roughness=0.75),  # 3 light rock
        pal(28, metallic=0.1, roughness=0.65),  # 4 sunlit rock
    ]


def rock_slot(v, _slot):
    if v < 19.5:
        return DARK
    if v < 22.5:
        return MID
    if v < 25.5:
        return LIGHT
    return HIGH


# --- the burrow ---------------------------------------------------------------------------------

BOULDERS = [  # (col, row, half width px, half height px, z half height, turn)
    # top rim
    (1.4, 1.8, 2.4, 2.6, 0.1, 0.0), (4.6, 1.9, 2.6, 2.6, 0.13, 0.2), (8.2, 1.8, 2.2, 2.4, 0.1, 0.0),
    (10.8, 1.8, 2.6, 2.4, 0.12, -0.2), (14.4, 1.9, 2.6, 2.6, 0.12, 0.1), (18.2, 1.6, 2.6, 2.4, 0.12, 0.3),
    (21.6, 2.0, 2.4, 2.6, 0.1, 0.0),
    # right side
    (20.2, 5.0, 2.4, 2.0, 0.12, 0.4), (21.8, 8.0, 2.0, 2.4, 0.08, 0.0), (21.6, 11.0, 2.2, 2.6, 0.12, 0.0),
    (21.4, 15.0, 2.4, 2.4, 0.09, 0.3), (19.8, 18.0, 2.4, 2.0, 0.1, 0.0),
    # left side
    (1.8, 6.0, 2.2, 2.4, 0.1, 0.0), (1.6, 9.6, 1.8, 2.0, 0.08, 0.0), (3.2, 13.8, 2.6, 3.4, 0.13, 0.1),
    (2.0, 17.4, 2.2, 2.2, 0.08, 0.0),
    # lower lip, over the fangs' roots
    (7.4, 16.2, 2.0, 2.2, 0.11, 0.0), (12.0, 16.2, 2.6, 2.2, 0.12, 0.0), (16.8, 15.6, 2.0, 2.2, 0.11, 0.0),
]

FANGS = [  # hanging off the lower lip, pointing down: (col, row, z, radius px)
    [(6.2, 16.0, -0.02, 2.2), (6.0, 18.6, -0.02, 2.0), (5.4, 21.0, -0.03, 1.1), (5.2, 22.6, -0.03, 0.0)],
    [(11.8, 17.0, -0.02, 3.0), (11.8, 20.2, -0.02, 2.8), (11.7, 23.4, -0.03, 1.7), (11.6, 26.3, -0.04, 0.0)],
    [(17.4, 17.0, -0.02, 3.0), (17.8, 20.4, -0.02, 3.0), (17.9, 23.6, -0.03, 1.9), (17.9, 26.6, -0.04, 0.0)],
]


def burrow(bm, pixels):
    """The burrow, coloured from the empty burrow's frame (`pixels`)."""
    # The pit: a dark floor under the whole rim (rows 0-19).
    L.plate(bm, [(0.3, 0.3), (23.7, 0.3), (23.7, 19.3), (19, 19.6), (5, 19.6), (0.3, 19.3)], -0.2, -0.1, mat=HOLE)
    rock = []
    # A thick rock wall round the pit (rows 0-4 on top, columns 0-4 and 19-23 down the sides) and
    # the lower lip across rows 14-19.
    rock += L.ptube(bm, [(1.6, 18.6, -0.07, 2.0), (1.8, 9.0, -0.07, 2.4), (2.6, 2.3, -0.07, 2.4),
                         (12.0, 2.0, -0.07, 2.5), (21.4, 2.3, -0.07, 2.4), (22.0, 9.0, -0.07, 2.4),
                         (21.6, 18.6, -0.07, 2.0)], sides=6, mat=MID, flat=0.7, smooth=False)
    rock += L.ptube(bm, [(3.0, 16.8, -0.06, 2.0), (20.6, 16.6, -0.06, 2.0)], sides=6, mat=MID, flat=0.7,
                    smooth=False)
    rnd = random.Random(9)
    for c, r, rx, ry, rz, turn in BOULDERS:
        rock += L.ellipsoid(bm, L.P(c, r, 0.02), (rx * L.PX, ry * L.PX, rz), segments=7, rings=4, mat=MID,
                            angle=turn, seed=rnd.randrange(1 << 30), rough=0.2, smooth=False)
    for path in FANGS:
        rock += L.ptube(bm, path, sides=6, mat=MID, flat=0.75, smooth=False)
    L.paint(bm, rock, pixels, rock_slot)


# --- the worm -----------------------------------------------------------------------------------

def outline_rows(pixels, base):
    """Per row, the widest run of the worm's pixels (those that differ from the empty burrow
    `base`, or every coloured pixel without one), allowing one-pixel gaps: {row: (lo, hi)}."""
    rows = {}
    for r, line in enumerate(pixels):
        cols = [c for c, v in enumerate(line) if v > 1 and (base is None or v != base[r][c])]
        groups = []
        for c in cols:
            if groups and c - groups[-1][-1] <= 2:
                groups[-1].append(c)
            else:
                groups.append([c])
        if groups:
            g = max(groups, key=lambda g: g[-1] - g[0])
            if g[-1] - g[0] >= 1:
                rows[r] = (g[0], g[-1])
    return rows


def worm(bm, pixels, base, z_of_row, extend_top=False, seed=3, sides=10):
    """A lumpy rock loft following the frame's worm outline. `z_of_row` gives the centre height
    by row; `extend_top` runs it up past row 0 (it is cut there) instead of rounding it off."""
    rows = outline_rows(pixels, base)
    if not rows:
        return []
    rs = sorted(rows)
    # Keep the longest run of consecutive rows.
    runs, cur = [], [rs[0]]
    for r in rs[1:]:
        if r - cur[-1] <= 2:
            cur.append(r)
        else:
            runs.append(cur)
            cur = [r]
    runs.append(cur)
    rs = max(runs, key=len)
    sec = []
    for i, r in enumerate(rs):
        near = [rows[q] for q in rs[max(0, i - 1):i + 2]]
        lo = sum(a for a, _ in near) / len(near)
        hi = sum(b for _, b in near) / len(near)
        sec.append((r, (lo + hi) / 2, (hi - lo + 1) / 2))
    r0, c0, w0 = sec[0]
    r1, c1, w1 = sec[-1]
    start = [(r0 - 3.0, c0, w0)] if extend_top else [(r0 - 0.9, c0, w0 * 0.55)]
    end = [(r1 + 0.8, c1, 0.0)]
    sec = start + sec + end

    rnd = random.Random(seed)
    n = len(bm.faces)
    rings = []
    for r, c, w in sec:
        z = z_of_row(r)
        if w <= 0.01:
            rings.append([bm.verts.new(L.P(c, r, z))])
            continue
        hz = min(0.27, w * L.PX * 0.5)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            j = 1 + rnd.uniform(-0.14, 0.14) if w > 1.5 else 1.0
            dr = rnd.uniform(-0.3, 0.3) if w > 1.5 else 0.0
            ring.append(bm.verts.new(L.P(c + w * math.cos(a) * j, r + dr, z + hz * math.sin(a) * j)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            k2 = (k + 1) % sides
            if len(b) == 1:
                bm.faces.new((a[k], a[k2], b[0]))
            elif len(a) == 1:
                bm.faces.new((a[0], b[k2], b[k]))
            else:
                bm.faces.new((a[k], a[k2], b[k2], b[k]))
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    bm.faces.ensure_lookup_table()
    faces = list(bm.faces[n:])
    for f in faces:
        f.material_index = MID
        f.smooth = True
    blur_paint(bm, faces, pixels, lambda v: MID if v < 21.5 else (LIGHT if v < 24.5 else HIGH))

    # The sprite's bright speckles (index 27 and up) as rock lumps on the worm's back.
    shape = {round(r): (c, w, z_of_row(r)) for r, c, w in sec if w > 0.01}
    lumps = []
    for r in sorted(shape):
        if r < 0 or r >= len(pixels):
            continue
        c0, w, z = shape[r]
        for c, v in enumerate(pixels[r]):
            if v < 27 or abs(c - c0) > w - 1.0 or any(abs(c - a) + abs(r - b) < 4.5 for a, b in lumps):
                continue
            lumps.append((c, r))
            hz = min(0.27, w * L.PX * 0.5)
            top = z + hz * math.sqrt(max(0.0, 1 - ((c - c0) / w) ** 2))
            faces += L.ellipsoid(bm, L.P(c, r, top - 0.02), (2.2 * L.PX, 1.9 * L.PX, 0.035), segments=8, rings=4,
                                 mat=HIGH, seed=rnd.randrange(1 << 30), rough=0.15, smooth=True)
    return faces


def blur_paint(bm, faces, pixels, slot_of):
    """Colour each upward face by the mean of the worm pixels in a 3x3 patch under its centre."""
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.normal_update()
        if f.normal.z < 0.05:
            continue
        cen = f.calc_center_median()
        vals = [L.sample(pixels, cen.x + dx * L.PX, cen.y + dy * L.PX) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
        vals = [v for v in vals if v > 1]
        if vals:
            f.material_index = slot_of(sum(vals) / len(vals))


def build_model(name, piece, frame, with_burrow, mats, base_pixels, frame_pixels):
    coll = common.reset_collection(name)
    bm = bmesh.new()
    if with_burrow:
        burrow(bm, base_pixels)
        if frame != 9:
            # Out of the pit (rows 4-9) and up over the lower lip.
            worm(bm, frame_pixels, base_pixels,
                 lambda r: -0.13 + 0.17 * min(1.0, max(0.0, (r - 4.0) / 8.0)), seed=frame)
    elif piece == UPPER:
        worm(bm, frame_pixels, None, lambda r: 0.04, seed=frame)
    else:
        worm(bm, frame_pixels, None, lambda r: 0.04, extend_top=True, seed=frame)
    whole = L.to_object(name + "_whole", bm, mats, coll)
    obj = common.split_assembly(whole, [(name, 0, 0)])[name]
    mesh = whole.data
    bpy.data.objects.remove(whole, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return obj


def main():
    upper = common.load_sprite(ROOT, UPPER)
    lower = common.load_sprite(ROOT, LOWER)
    sprite = L.merged_sprite(ROOT, [UPPER, LOWER])
    mats = materials(sprite)
    base = L.frame_pixels(upper, 9)
    out = L.preview_args()
    built = {}
    for name, piece, frames, frame, with_burrow in MODELS:
        data = upper if piece == UPPER else lower
        obj = build_model(name, piece, frame, with_burrow, mats, base, L.frame_pixels(data, frame))
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", L.frames_subset(data, frames))
        built[name] = (obj, data, frame)
    if out:
        for name, (obj, data, frame) in built.items():
            img = next(f["image"] for f in data["frames"] if f["index"] == frame)
            L.preview([obj], ROOT, data["name"], img, out.parent / f"{name}.png")
        # The two pieces together: newsh8-9-f7 over newsh8-87-f4.
        ref = L.composite_png(ROOT, [(UPPER, 55, 12, 0), (LOWER, 93, 12, 28)], 48, 56,
                              Path(tempfile.mkdtemp()) / "assembly.png")
        top, bottom = built["newsh8-9-f7"][0], built["newsh8-87-f4"][0]
        top.location.y, bottom.location.y = 14 / 12, -14 / 12
        common.render_preview([top, bottom], str(out), str(ref), size=4, view_px=480)
        top.location.y = bottom.location.y = 0.0


if __name__ == "__main__":
    main()
