"""Bronze pod with telescoping arms (newsh2.shp frames 159-167): a 3D version of its sprite.

Seen in episode 1 (levels 25-41), episode 2 and episode 3. A bronze ball with a short post on top,
a grey bar strapped across its upper half (its bright centre and left spots are sheen on the
metal, made by the material, not a hub), and a dark mouth cut in below the bar. Over the five frames the bar's thin arms slide out of the ball one pixel a side at a
time (tips at 8, 9, 10, 11 and 12 px from the centre, outline included) and red-hot fins open round
them. The frames also alternate a shade darker and lighter, and frame 159 is drawn one row higher.
So each frame gets its own model: newsh2-159, newsh2-159-f2 (161) ... newsh2-159-f5 (167).

Rows and columns below are frame 161's (159 is shifted up one row by `up`).

Run: blender --background --python assets/blender/enemies/newsh2-159.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-159"
U = 1 / 12

# Per frame: arm tip (px from centre), shade offset (0 dark, 1 light), rows shifted up, red fins
# as (centre x px, centre row, rx px, ry px, palette index) or None.
FRAMES = [
    (8, 0, 1, None),
    (9, 1, 0, None),
    (10, 0, 0, (7.9, 16.0, 1.0, 1.0, 114)),
    (11, 1, 0, (8.0, 14.4, 1.1, 3.6, 119)),
    (12, 1, 0, (8.5, 14.8, 1.6, 4.2, 119)),
]

# The ball: (row edge, half width px). Its cross-sections are round: half height = ROUND x width.
BODY = ((8.1, 0.0), (8.4, 3.0), (9.0, 4.6), (10.0, 5.9), (11.0, 7.0), (12.0, 7.7), (13.0, 8.0),
        (19.6, 8.0), (20.3, 7.5), (21.2, 6.6), (22.2, 5.3), (23.2, 3.8), (23.8, 2.2), (24.05, 0.0))
ROUND = 0.95


def append_mesh(bm, obj):
    """Copy an object's mesh (faces, material indices, smooth flags) into bm, then delete it."""
    mesh = obj.data
    verts = [bm.verts.new(v.co) for v in mesh.vertices]
    for p in mesh.polygons:
        f = bm.faces.new([verts[i] for i in p.vertices])
        f.material_index = p.material_index
        f.smooth = p.use_smooth
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(mesh)


# The grey bar strapped over the ball (centre on row edge BAR_ROW): a round tube BAR_R px in radius
# on an arch whose outer edge is on the outline at the ball's sides (BAR_A + BAR_R = 8 px) and which
# stands about 3 px proud over the crown. To keep it that proud down to the sides without widening
# the outline, the ball narrows under the bar (to PINCH_W px) and widens back within PINCH_OUT rows.
BAR_ROW, BAR_R, BAR_A, BAR_Z = 14.0, 1.6, 6.4, 9.0
PINCH_W, PINCH_IN, PINCH_OUT = 4.9, 1.35, 2.0


def body_width(r):
    for (r0, w0), (r1, w1) in zip(BODY, BODY[1:]):
        if r0 <= r <= r1:
            return w0 + (w1 - w0) * (r - r0) / (r1 - r0)
    return 0.0


def body_sections(E):
    """Loft sections (y, half width, half height, z) in units: round, pinched under the bar."""
    rows = {r for r, _ in BODY}
    rows |= {9.5, 10.5, 11.5, 12.5, 15.0, 16.0, 17.0, 18.0, 19.0, 20.75, 21.7, 22.7}
    rows |= {BAR_ROW + s * d for s in (-1, 1) for d in (0.0, PINCH_IN, 0.5 * (PINCH_IN + PINCH_OUT), PINCH_OUT)}
    out = []
    for r in sorted(rows):
        w = body_width(r)
        h = ROUND * w
        d = abs(r - BAR_ROW)
        p = 1.0 if d <= PINCH_IN else max(0.0, (PINCH_OUT - d) / (PINCH_OUT - PINCH_IN))
        p = p * p * (3 - 2 * p)
        if w > PINCH_W:
            w -= p * (w - PINCH_W)
        out.append((E(r), w * U, h * U, 0.0))
    return out


def build_one(sprite, name, tip, shade, up, fins):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i + shade, NAME, **kw)  # noqa: E731
    # Lighting pass: the ball, post and bar are metal (a bronze pod with a steel bar), so each part
    # is one mid-tone and the game's lights shade it and make the shine; the sprite's dark rim ring,
    # lit shoulders, darker bar flanks and white hot spots were its drawn light, not paint. Slots 1,
    # 4, 9, 10 and 11 are kept for the index names but no longer used.
    bronze = pal(21, metallic=0.55, roughness=0.35)
    steel = pal(6, metallic=0.8, roughness=0.3)
    mats = [
        bronze,  # 0 bronze ball, one mid-tone all over
        bronze,  # 1 (was the lit shoulders)
        pal(165, metallic=0.55, roughness=0.35),  # 2 post, walls and cap
        steel,  # 3 grey bar
        steel,  # 4 (was the shiny hub: sheen, now the bar's material)
        pal(17, metallic=0.0, roughness=0.9),  # 5 dark mouth walls
        pal(4, metallic=0.75, roughness=0.3),  # 6 darker grey arms and bar ends
        pal(25, metallic=0.55, roughness=0.35),  # 7 the left flank's tan rib
        pal(23, metallic=0.55, roughness=0.35),  # 8 the right flank's rib
        bronze,  # 9 (was the lower part and crown)
        bronze,  # 10 (was the dark rim ring)
        steel,  # 11 (was the bar's darker sides)
        common.palette_material(sprite, 16, NAME, metallic=0.0, roughness=0.9),  # 12 mouth floor
    ]
    HULL, SHOULDER, KNOB, BAR, HUB, SLOT, ARM, CAP, RIB, LOWER, RIM, BAR_SIDE, FLOOR = range(13)
    if fins:
        mats.append(common.palette_material(sprite, fins[4], NAME, emission_strength=3.0 if fins[4] == 119 else 1.5))
    FIN = 13
    R = lambda r: lib.row(r - up)  # noqa: E731
    E = lambda r: lib.ey(r - up)  # noqa: E731
    row_of = lambda y: 14.0 - 12.0 * y + up  # noqa: E731  (a y back to a frame-161 row edge)

    # Ball: rows 10-23, columns 4-19, as tall as it is wide (about +-7.6 px round the midplane).
    hull = lib.Profile(body_sections(E))
    hbm = bmesh.new()
    hull.build(hbm, sides=32, mat_index=HULL)
    bmesh.ops.recalc_face_normals(hbm, faces=hbm.faces)
    # The ball is one bronze mid-tone; the only markings painted on are the rib down each flank
    # beside the mouth (tan on the left, lighter bronze on the right). Each face is placed by its
    # row and its angle round the loft (u across, v up, both -1..1), so the rib edges follow the
    # mesh's rings and meridians instead of stair-stepping.
    for f in hbm.faces:
        c = f.calc_center_median()
        r = row_of(c.y)
        w, h, _ = hull.at(c.y)
        if w <= 0 or h <= 0:
            continue
        u, v = c.x / w, c.z / h
        if v < 0.3:
            continue
        if 15.8 < r < 20.2 and -0.66 < u < -0.47:
            f.material_index = CAP
        elif 15.8 < r < 20.2 and 0.47 < u < 0.66:
            f.material_index = RIB
    body = lib.finish(name + "-ball", hbm, mats, coll)

    # The dark mouth under the bar (rows 15-19, columns 9-14) cut about 4.5 px into the ball: a
    # rounded rectangle 6 px wide, straight along the bar and rounding off below, near-black inside.
    mx, my, mrx, mry, depth = -0.1 * U, E(17.8), 3.1 * U, 2.2 * U, 4.5 * U
    n = 24
    outline = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        c, s = math.cos(a), math.sin(a)
        e = 0.45  # superellipse: squarer than an ellipse
        outline.append((mx + mrx * math.copysign(abs(c) ** e, c), my + mry * math.copysign(abs(s) ** e, s)))
    cbm = bmesh.new()
    top = [cbm.verts.new((x, y, 2.0)) for x, y in outline]
    # Straight walls for the first 1.5 px, then a funnel narrowing into the dark (no flat floor
    # facing up to catch the light).
    mid = [cbm.verts.new((x, y, hull.top(x, y) - 1.5 * U)) for x, y in outline]
    floor_z = hull.top(mx, my) - depth
    bot = [cbm.verts.new((mx + 0.12 * (x - mx), my + 0.12 * (y - my), floor_z)) for x, y in outline]
    for k in range(n):
        j = (k + 1) % n
        cbm.faces.new((mid[k], mid[j], top[j], top[k])).material_index = SLOT
        cbm.faces.new((bot[k], bot[j], mid[j], mid[k])).material_index = FLOOR
    cbm.faces.new(list(reversed(bot))).material_index = FLOOR
    cbm.faces.new(top).material_index = SLOT
    cutter = common.mesh_object(name + "-cutter", cbm, mats, coll)
    mod = body.modifiers.new("mouth", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.material_mode = "INDEX"
    with bpy.context.temp_override(object=body, active_object=body):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    for p in body.data.polygons:
        if p.material_index in (SLOT, FLOOR):
            p.use_smooth = False

    bm = bmesh.new()
    append_mesh(bm, body)

    # Post on top (rows 7-10, columns 9-13): a short upright cylinder, squarish so it fills the
    # sprite's top row, standing about 3 px above the ball's front slope, one dark bronze all over
    # (the tan streak across its top in the sprite is sheen).
    kx, ky, krx, kry, kz = -0.5 * U, E(9.0), 2.6 * U, 2.0 * U, 8.0 * U

    def squircle(t, k=4.0):
        c, s = math.cos(t), math.sin(t)
        return math.copysign(abs(c) ** (2 / k), c), math.copysign(abs(s) ** (2 / k), s)

    k_bot = [(kx + krx * squircle(2 * math.pi * i / 16)[0], ky + kry * squircle(2 * math.pi * i / 16)[1])
             for i in range(16)]
    rings = [[(x, y, 0.0) for x, y in k_bot],
             [(x, y, kz - 0.5 * U) for x, y in k_bot],
             [(kx + (x - kx) * 0.85, ky + (y - ky) * 0.85, kz) for x, y in k_bot],
             [(kx + (x - kx) * 0.55, ky + (y - ky) * 0.55, kz + 0.1 * U) for x, y in k_bot]]
    lib.ring_loft(bm, rings, [KNOB, KNOB, KNOB], cap_start=True, cap_end=True, cap_mats=(KNOB, KNOB), smooth=True)
    bm.faces.ensure_lookup_table()
    bm.faces[-1].smooth = False

    # The bar strapped across the ball's upper half (rows 12-15): a 3.2 px round tube on an arch
    # over the pinched ball, 3 px proud from the crown down to the sides; one polished grey.
    yb = E(BAR_ROW)
    pts = []
    for i in range(17):
        t = math.pi * i / 16
        pts.append((-BAR_A * U * math.cos(t), yb, BAR_Z * U * math.sin(t)))
    f0 = len(bm.faces)
    lib.polyline_tube(bm, pts, BAR_R * U, sides=10, mat_index=BAR)
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[f0:])
    # (The sprite's white spots on the bar, columns 10-11 and 7, are its sheen: the steel material
    # makes them, so there is no hub ball.)
    # Dark grey bar ends where the bar meets the sides, and the thin arms out to the tips.
    for s in (-1, 1):
        x0, x1 = 6.6 * U, min(8.3, tip + 0.1) * U
        lib.polyline_tube(bm, [(s * x0, yb, 0.4 * U), (s * x1, yb, 0.4 * U)], 1.75 * U, sides=10, mat_index=ARM)
        if tip > 8.3:
            lib.polyline_tube(bm, [(s * 7.5 * U, yb, 0.4 * U), (s * (tip - 0.4) * U, yb, 0.4 * U),
                                   (s * tip * U, yb, 0.4 * U)],
                              [1.0 * U, 1.0 * U, 0.6 * U], sides=8, mat_index=ARM)

    # Red fins opening round the arms, outside the ball's sides.
    if fins:
        cx, cr, rx, ry, _ = fins
        for s in (-1, 1):
            poly = lib.ellipse_polygon(s * cx * U, R(cr), rx * U, ry * U, n=12)
            if s < 0:
                poly = poly[::-1]
            common.slab(bm, poly, 0.05, z=0.4 * U, mat_index=FIN)

    return lib.finish(name, bm, mats, coll)


def build(sprite):
    frames = sprite["sprites"][0]["frames"]
    models = []
    for k, (frame, spec) in enumerate(zip(frames, FRAMES)):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        models.append((name, [build_one(sprite, name, *spec)], lib.frames_subset(sprite, [frame])))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
