"""Large grey asteroid with a glowing vent (newshd.shp frames 18, 55, 93): a 3D version of its sprite.

Seen in episodes 1-3. The same kind of lumpy grey rock as newshd-5 (see lib_b014.rock), built as
a rounded boulder about 10 px tall that leans up towards the bright crown in the upper centre,
with the sprite's three lobes (big bright upper-left, lit lower-centre, smaller right), the dark
cracks between them cut in, and its crater, bright patch and dark dents in relief, covering the
sprite's dark outline ring. On the right lobe (columns 18-20, rows 10-14) a glowing lens is set
into the rock: a plate flush with the rock face (red with darker corners) carrying a 2 px dome
painted with the sprite's orange cross and yellow-white core. The frames only cool the glow
(bright, dim, out), so one model covers them all: the
vent dims on frame 55 (palette_material frames=) and is gone on frame 93 (common.frame_part), and
the rock round it, lit by the glow on frame 18, darkens on the other two.

Run: blender --background --python assets/blender/enemies/newshd-18.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402
from lib_b014 import common, px, row  # noqa: E402

NAME = "newshd-18"
FIRE = (115, 117, 119, 120, 122, 124, 126, 166, 168)  # the vent and its scorched lip
VENT = (px(19), row(12))  # the vent's centre
VW, VH = 1.7 / 12, 2.6 / 12  # its half width and half height


# The rock's top: a rounded boulder (half_height), highest under the sprite's bright crown in the
# upper centre and falling away to the dark lower-right flank.
HALF_HEIGHT = 0.64  # ~7.7 px above the waist before relief
CROWN = (px(11), row(7))  # the bright crown the rock leans up towards
TILT = 0.22  # how much higher the crown side stands than the opposite flank (fraction of height)
# Relief the sprite draws (sprite col, row, radius px, height px): the crater ridge with its pit in the
# upper centre, the bright patch beside the vent, and the dark dents lower-left and lower-right.
CRATER = (10.5, 6.5, 3.0, 0.9, -1.0)  # centre col/row, ring radius, ring height, pit depth (px)
BUMPS = [(17.5, 8.0, 1.6, 1.0),        # bright patch left of / above the vent
         (14.5, 16.0, 1.8, -1.3),      # dark cluster lower-right
         (6.5, 15.0, 1.4, -0.8)]       # dark pixels at the lower-left rim
# The sprite's big forms: three rounded lobes (centre col, row, radius x, radius y, height px), the
# big bright one upper-left highest, a lit one lower-centre and a smaller one on the right that
# carries the vent ...
LOBES = [(9.5, 7.0, 4.5, 3.8, 1.6),
         (9.5, 15.0, 3.0, 3.0, 0.9),
         (17.5, 9.0, 3.2, 4.0, 1.0)]
# ... and the dark cracks between them, cut in (polyline of sprite col/row, half width px, depth px):
# the diagonal one from the left edge in under the big lobe, and the one between it and the right lobe.
CRACKS = [([(3.5, 13.5), (6.5, 12.5), (9.0, 11.5), (11.0, 10.8), (13.5, 10.5)], 1.0, 1.6),
          ([(13.6, 4.5), (13.8, 7.0), (14.2, 9.5)], 0.9, 1.0)]
# The vent: a flat rectangular panel over columns 18-20, rows 10-14 (edges in sprite px).
VENT_C0, VENT_C1, VENT_R0, VENT_R1 = 18, 21, 10, 15


def reshape(bm, cx, cy):
    """Tilt the rock up towards its crown and add the sprite's crater, bumps and dents (top only,
    fading out towards the rim so the silhouette stays the sprite's)."""
    import math
    dx, dy = CROWN[0] - cx, CROWN[1] - cy
    dl = math.hypot(dx, dy)
    dx, dy = dx / dl, dy / dl
    rmax = max(math.hypot(v.co.x - cx, v.co.y - cy) for v in bm.verts)
    zmax = max(v.co.z for v in bm.verts)
    for v in bm.verts:
        if v.co.z <= 0:
            continue
        x, y = v.co.x, v.co.y
        fade = min(1.0, v.co.z / (zmax * 0.35))
        v.co.z *= 1 + TILT * ((x - cx) * dx + (y - cy) * dy) / rmax
        c, r, rad, ring, pit = CRATER
        d = math.hypot(x - px(c), y - row(r)) * 12
        dz = ring * math.exp(-((d - rad) / 1.4) ** 2) + pit * math.exp(-(d / 1.4) ** 2)
        for bc, br, brad, bh in BUMPS:
            d = math.hypot(x - px(bc), y - row(br)) * 12
            dz += bh * math.exp(-(d / brad) ** 2)
        for lc, lr, lrx, lry, lh in LOBES:
            q = ((x - px(lc)) * 12 / lrx) ** 2 + ((y - row(lr)) * 12 / lry) ** 2
            dz += lh * math.exp(-q)
        for pts, half, depth in CRACKS:
            d = min(seg_dist(x, y, a, b) for a, b in zip(pts, pts[1:])) * 12
            dz -= depth * math.exp(-(d / half) ** 2)
        v.co.z += dz / 12 * fade


def seg_dist(x, y, a, b):
    """Distance (units) from (x, y) to the segment between sprite points a and b (col, row)."""
    import math
    ax, ay, bx, by = px(a[0]), row(a[1]), px(b[0]), row(b[1])
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - ax - t * dx, y - ay - t * dy)


def repaint(bm, shade, edges, outline):
    """Paint every face again after reshaping, the way lib.rock does (darkest shade underneath).
    Top faces over the sprite's near-black outline ring (or just outside it) take `outline`."""
    bm.normal_update()
    for f in bm.faces:
        k = face_band(shade, edges, f)
        f.material_index = 0 if k is None else k
        if k is not None:
            cen = f.calc_center_median()
            if shade.index(cen.x, cen.y) in lib.OUTLINE:
                f.material_index = outline


def fit_plane(bm, x0, x1, y0, y1, margin):
    """Least-squares plane z = a + b x + c y through the rock's top vertices round a rectangle."""
    import numpy as np
    pts = [v.co for v in bm.verts if v.co.z > 0 and x0 - margin < v.co.x < x1 + margin
           and y0 - margin < v.co.y < y1 + margin]
    A = np.array([[1.0, p.x, p.y] for p in pts])
    z = np.array([p.z for p in pts])
    a, b, c = np.linalg.lstsq(A, z, rcond=None)[0]
    return lambda x, y: a + b * x + c * y


def slab(bm, x0, x1, y0, y1, plane, top, depth, mat):
    """A box whose top follows `plane` (+top) over the rectangle, seen from above as the rectangle."""
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    up = [bm.verts.new((x, y, plane(x, y) + top)) for x, y in corners]
    dn = [bm.verts.new((x, y, plane(x, y) + top - depth)) for x, y in corners]
    faces = [bm.faces.new(up), bm.faces.new(dn[::-1])]
    for i in range(4):
        j = (i + 1) % 4
        faces.append(bm.faces.new((up[i], dn[i], dn[j], up[j])))
    for f in faces:
        f.material_index = mat


def face_band(shade, edges, f):
    """The shade band lib.rock paints a top face with, from a frame's Shade (None: underneath)."""
    if f.normal.z < -0.3:
        return None
    cen = f.calc_center_median()
    pts = [cen] + [cen.lerp(v.co, 0.6) for v in f.verts]
    vals = [x for x in (shade.at(p.x, p.y, blur=0.3) for p in pts) if x is not None]
    if not vals:
        return 1 if f.normal.z > 0.3 else 0
    k = lib.band_of(edges, sum(vals) / len(vals))
    return max(0, k - 1) if f.normal.z < 0.2 else k


def glow_on_rock(sprite, bm, mats):
    """The rock round the vent is lit by its glow on frame 18 and darker on 55 and 93: give the
    faces whose shade changes a material that takes each frame's shade (palette_material frames=).
    Under the vent this also paints the bare rock frame 93 shows once the vent is gone."""
    first = sprite["frames"][0]
    reps, edges = lib.shade_slots(sprite, first["pixels"], 6, FIRE)  # as lib.rock picked them
    shades = [(f["index"], lib.Shade(sprite, f["pixels"], 2, FIRE)) for f in sprite["frames"][1:]]
    bm.normal_update()
    glow = {}
    for f in bm.faces:
        if face_band(shades[0][1], edges, f) is None:
            continue
        k0 = f.material_index
        if k0 >= len(reps):  # the outline ring
            continue
        per = {i: face_band(sh, edges, f) for i, sh in shades}
        frames = {i: reps[k] for i, k in per.items() if reps[k] != reps[k0]}
        if not frames:
            continue
        key = (k0, *(per[i] for i, _ in shades))
        if key not in glow:
            glow[key] = len(mats)
            mats.append(common.palette_material(sprite, reps[k0], f"{NAME}-glow{''.join(map(str, key))}",
                                                metallic=0.0, roughness=0.85 - 0.04 * k0, frames=frames))
        f.material_index = glow[key]


def build(sprite):
    import bmesh
    coll = common.reset_collection(NAME)
    pixels = sprite["frames"][0]["pixels"]
    # grow: the body reaches out over the sprite's dark outline ring, as the sprite's footprint does.
    bm, mats, shade = lib.rock(sprite, NAME, pixels, size=2, half_height=HALF_HEIGHT, relief=0.05,
                               seed=18, subdiv=3, skip=FIRE, grow=1.25, flat_bottom=0.55)
    for m in mats:  # plain stone, not metal: the sprite's light greys read lighter from above
        next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Metallic"].default_value = 0.0
    cx, cy, _ = lib.silhouette(pixels, 2)
    reshape(bm, cx, cy)

    # Seat the vent: the rock under its rectangle is pressed down to a plane, so the panel lies
    # flat in the rock face.
    x0, x1 = lib.ex(VENT_C0), lib.ex(VENT_C1)
    y1, y0 = lib.ey(VENT_R0), lib.ey(VENT_R1)
    slope = fit_plane(bm, x0, x1, y0, y1, 1.5 / 12)
    # The rock's own slope there, so the plate lies in the rock face (flush all round, no lip
    # standing out on the downhill side) and the lens dome on it carries the relief.
    vx, vy = (x0 + x1) / 2, (y0 + y1) / 2
    plane = slope
    m = 1.0 / 12
    for v in bm.verts:
        if x0 - m < v.co.x < x1 + m and y0 - m < v.co.y < y1 + m and v.co.z > 0:
            v.co.z = min(v.co.z, plane(v.co.x, v.co.y) - 0.012)

    _, edges = lib.shade_slots(sprite, pixels, 6, FIRE)
    mats.append(common.palette_material(sprite, 1, NAME, metallic=0.0, roughness=0.9))
    repaint(bm, shade, edges, len(mats) - 1)
    glow_on_rock(sprite, bm, mats)
    rock = common.mesh_object(NAME, bm, mats, coll, smooth=False)

    # The vent: a flat glowing panel, hard-edged steps as the sprite draws them: red 119 with darker
    # 117 corners, an orange 122 cross and a yellow-white 126 core. It cools a step on frame 55
    # (119 -> 117, 117 -> 115, 122 -> 120, 126 -> 124) and is out on frame 93.
    vent_tag = f"{NAME}-vent"
    vmats = [
        common.palette_material(sprite, 119, vent_tag, metallic=0.0, roughness=0.6, emission_strength=4.0,
                                frames={55: 117}),
        common.palette_material(sprite, 117, vent_tag, metallic=0.0, roughness=0.6, emission_strength=3.0,
                                frames={55: 115}),
        common.palette_material(sprite, 122, vent_tag, emission_strength=5.0, frames={55: 120}),
        common.palette_material(sprite, 126, vent_tag, emission_strength=6.0, frames={55: 124}),
    ]
    RED, DARK, HOT, CORE = range(4)
    vb = bmesh.new()
    cell = lambda c, r: (lib.ex(c), lib.ex(c + 1), lib.ey(r + 1), lib.ey(r))  # noqa: E731
    slab(vb, x0, x1, y0, y1, plane, 0.008, 0.045, RED)  # thin: flush with the rock face
    for c, r in ((VENT_C0, VENT_R0), (VENT_C1 - 1, VENT_R0), (VENT_C0, VENT_R1 - 1), (VENT_C1 - 1, VENT_R1 - 1)):
        slab(vb, *cell(c, r), plane, 0.013, 0.02, DARK)
    plate_verts, plate_faces = set(vb.verts), set(vb.faces)
    # The glowing lens bulges out of the plate as a dome (bright core on its crown, darker red at
    # its foot), about 3 px wide, 5 px long and 2 px tall, sheared onto the rock's slope so its
    # foot sits in the plate all round. Its faces take the sprite's colours under them: the orange
    # cross on row 12 and column 19, the yellow-white core in the middle.
    dome_h = 2.2 / 12
    lib.dome(vb, vx, vy, (x1 - x0) / 2 - 0.004, (y1 - y0) / 2 - 0.004, dome_h, z=-0.01, rings=5, sides=20,
             mat_index=RED, bottom=False)
    base = plane(vx, vy) + 0.008  # the plate's top at the centre
    for v in vb.verts:
        if v not in plate_verts:
            v.co.z += plane(v.co.x, v.co.y) - plane(vx, vy) + base
    vb.normal_update()
    hx0, hx1 = lib.ex(19), lib.ex(20)
    hy1, hy0 = lib.ey(12), lib.ey(13)
    for f in vb.faces:
        if f in plate_faces:
            continue
        c = f.calc_center_median()
        in_col, in_row = hx0 <= c.x <= hx1 and lib.ey(14) <= c.y <= lib.ey(11), hy0 <= c.y <= hy1
        if in_col and in_row and (c.z - plane(c.x, c.y)) > dome_h * 0.6:
            f.material_index = CORE
        elif in_col or in_row:
            f.material_index = HOT
        else:
            f.material_index = RED
    vent = common.frame_part(common.mesh_object(f"{NAME}_vent", vb, vmats, coll, smooth=False), [18, 55])
    return [(NAME, [rock, vent], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
