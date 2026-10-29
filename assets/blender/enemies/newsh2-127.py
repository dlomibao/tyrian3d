"""Purple shield craft (newsh2.shp frame 127): a 3D version of its sprite.

Seen in episode 1 (levels 1.25, 1.28, 1.3, 1.36) and episode 3. It flies nose down the screen: a
broad, shield-shaped armoured hull, square-shouldered at the back and narrowing to the nose. Hard
surface, built of stacked chamfered plates: two big shoulder plates across the back with a framed
cyan glass panel between them, a twin-rod yoke running from that panel to a raised blue glass
cockpit in the middle, light cheek plates either side of the cockpit curving in to a pale keel
plate, three round ports cut into each flank, a dark slot below the keel and a teal gun block at
the nose. The features are listed in assets/blender/features/newsh2-127.json. One frame, one model.

Run: blender --background --python assets/blender/enemies/newsh2-127.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b048 as L  # noqa: E402
from lib_b048 import common  # noqa: E402

NAME = "newsh2-127"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = L.PX
AXIS = 12  # the sprite is symmetric about the centre of column 12

# Model x is in px from the axis (pixel-edge column e is at e - 12.5), y is a sprite row edge.
X = lambda e: e * PX  # noqa: E731
Y = L.ey

# Hull cross-section, looking along the craft: (u across -1..1, v bottom 0..top 1). Flat bottom,
# chamfered flanks, flat top: a hard surface, shaded flat.
PROFILE = [(0.82, 0.0), (1.0, 0.32), (0.93, 0.68), (0.66, 0.92), (0.3, 1.0),
           (-0.3, 1.0), (-0.66, 0.92), (-0.93, 0.68), (-1.0, 0.32), (-0.82, 0.0)]
# Hull sections, back to nose: (row edge, half width px, top z, bottom z).
HULL = [(0.9, 7.4, 0.17, -0.06), (1.6, 8.6, 0.21, -0.1), (2.6, 9.8, 0.24, -0.14),
        (3.6, 10.7, 0.26, -0.16), (4.5, 11.0, 0.27, -0.17), (13.5, 11.0, 0.27, -0.17),
        (14.5, 10.1, 0.26, -0.16), (16.5, 9.1, 0.25, -0.15), (18.5, 8.1, 0.23, -0.14),
        (20.5, 7.1, 0.21, -0.12), (22.5, 6.1, 0.19, -0.11), (24.5, 5.1, 0.16, -0.09),
        (26.3, 4.1, 0.12, -0.07), (27.0, 3.0, 0.08, -0.04)]


def hull_loft(bm, mat):
    rings = [[bm.verts.new((u * w * PX, Y(r), zb + v * (zt - zb))) for u, v in PROFILE]
             for r, w, zt, zb in HULL]
    n = len(PROFILE)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    for f in bm.faces:
        f.material_index = mat
        f.smooth = False


def hull_top(x, row):
    """The hull's top surface height (units) and its sideways slope dz/dx at x (px), row."""
    for (r0, w0, t0, b0), (r1, w1, t1, b1) in zip(HULL, HULL[1:]):
        if r0 <= row <= r1:
            k = (row - r0) / (r1 - r0)
            w, zt, zb = w0 + (w1 - w0) * k, t0 + (t1 - t0) * k, b0 + (b1 - b0) * k
            break
    u = abs(x) / w
    top = [(u_, v_) for u_, v_ in PROFILE[:5]][::-1]  # u ascending 0.3 .. 0.82 (upper side)
    top = [(0.0, 1.0)] + top[:-1]
    for (ua, va), (ub, vb) in zip(top, top[1:]):
        if ua <= u <= ub:
            v = va + (vb - va) * (u - ua) / (ub - ua)
            dv = (vb - va) / (ub - ua)
            break
    else:
        v, dv = 0.32, -1.0
    h = zt - zb
    return zb + v * h, -math.copysign(abs(dv * h / (w * PX)), x)


def plate(bm, outline, z0, z1, bevel, mats, light=(-1, 1), dz=None):
    """L.bevel_plate on an outline in (x px, row) with an optional top shaping dz(x px, row)."""
    before = set(bm.verts)
    L.bevel_plate(bm, [(X(x), Y(r)) for x, r in outline], z0, z1, bevel, mats, light=light)
    if dz:
        for v in set(bm.verts) - before:
            if v.co.z > z0 + 1e-5:
                v.co.z += dz(v.co.x / PX, 14 - v.co.y * 12)


def port(bm, x, row, r, mats):
    """A round port in the hull at (x px, row): a raised rim around a dark floor sunk below the
    rim's top, tilted with the hull's surface."""
    rim, dark = mats
    z, slope = hull_top(x, row)
    tilt = math.atan(slope)
    seg = 10
    R = r + 0.55
    zt, zb, zd = 0.04, -0.06, 0.012
    rings = []
    for rad, zz in ((R, zb), (R, zt), (r, zt), (r, zd)):
        rings.append([Vector((rad * PX * math.cos(2 * math.pi * k / seg), rad * PX * math.sin(2 * math.pi * k / seg), zz))
                      for k in range(seg)])
    c, s = math.cos(-tilt), math.sin(-tilt)
    vs = [[bm.verts.new((X(x) + p.x * c + p.z * s, Y(row) + p.y, z + (-p.x * s + p.z * c))) for p in ring]
          for ring in rings]
    for a, b in zip(vs, vs[1:]):
        for k in range(seg):
            j = (k + 1) % seg
            f = bm.faces.new((a[k], a[j], b[j], b[k]))
            f.material_index = rim
            f.smooth = False
    f = bm.faces.new(vs[-1])
    f.material_index = dark
    f.smooth = False


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(84, metallic=0.35, roughness=0.45),  # 0 hull flanks
        pal(87, metallic=0.35, roughness=0.4),  # 1 shoulder and cheek armour plates
        pal(83, metallic=0.3, roughness=0.5),  # 2 dark frames, port rims
        pal(89, metallic=0.35, roughness=0.35),  # 3 pale keel plate, yoke rods
        pal(80, metallic=0.1, roughness=0.8),  # 4 dark ports and slots
        pal(59, metallic=0.6, roughness=0.1, emission_strength=0.6),  # 5 blue glass (cockpit, rear panel)
        pal(102, metallic=0.5, roughness=0.4),  # 6 cockpit frame bar
        pal(134, metallic=0.6, roughness=0.1, emission_strength=1.2),  # 7 glass edges catching the light
        pal(128, metallic=0.5, roughness=0.3),  # 8 rear panel mullions
        pal(54, metallic=0.45, roughness=0.4),  # 9 teal gun block
        pal(131, metallic=0.45, roughness=0.35),  # 10 lit edge of the gun block
        pal(86, metallic=0.35, roughness=0.45),  # 11 centre deck
        pal(101, metallic=0.2, roughness=0.7),  # 12 nose vent
    ]
    HULLM, ARMOUR, DARKP, PALE, PORT, GLASS, BAR, GLASS_HI, MULLION, TEAL, TEAL_LIT, DECK, VENT = range(13)
    bm = bmesh.new()
    hull_loft(bm, HULLM)

    # Centre deck between the shoulder plates (cols 9-15, rows 4-8), a low plate on the hull.
    plate(bm, [(-3.9, 4.3), (3.9, 4.3), (3.9, 8.2), (-3.9, 8.2)], 0.2, 0.3, 0.02, (DECK,) * 4)
    # Dark gap between the yoke rods (column 12).
    L.box(bm, X(-0.5), Y(8.0), X(0.5), Y(4.6), 0.25, 0.305, mat=PORT)

    # Rear glass panel at the back edge (cols 9-15, rows 1-3) in a purple frame.
    plate(bm, [(-4.3, 0.75), (4.3, 0.75), (4.3, 4.6), (-4.3, 4.6)], 0.05, 0.43, 0.03, (ARMOUR,) * 4)
    plate(bm, [(-3.5, 1.0), (3.5, 1.0), (3.5, 4.0), (-3.5, 4.0)], 0.3, 0.45, 0.06,
          (GLASS, GLASS_HI, GLASS, GLASS), light=(0, -1))
    for x0 in (-2.5, 1.5):  # mullions at cols 10 and 14
        L.box(bm, X(x0), Y(3.25), X(x0 + 1.0), Y(1.75), 0.4, 0.453, mat=MULLION)

    # Yoke: two rods (cols 11 and 13, rows 4-8) from the rear panel to the cockpit.
    for x in (-1.0, 1.0):
        L.sweep(bm, [(X(x), Y(4.2), 0.335, 0.5 * PX, 0.5 * PX), (X(x), Y(8.8), 0.335, 0.5 * PX, 0.5 * PX)],
                sides=6, mat=PALE)

    # Cockpit: dark frame (cols 9-15, rows 8-13) and a raised, faceted glass canopy (cols 10-14,
    # rows 9-12) with a grey bar across it at row 10 and its front chamfer catching the light.
    plate(bm, [(-3.5, 8.0), (3.5, 8.0), (3.5, 13.9), (-3.5, 13.9)], 0.15, 0.42, 0.03, (DARKP,) * 4)
    plate(bm, [(-2.6, 8.85), (2.6, 8.85), (2.6, 13.0), (-2.6, 13.0)], 0.3, 0.58, 0.07,
          (GLASS, GLASS_HI, GLASS, GLASS), light=(0, -1))
    L.box(bm, X(-2.63), Y(11.0), X(2.63), Y(10.0), 0.3, 0.52, mat=BAR)  # band round its walls
    L.box(bm, X(-1.75), Y(11.0), X(1.75), Y(10.0), 0.5, 0.585, mat=BAR)  # and across its top

    # Keel plate (cols 9-14, rows 14-19), sloping down towards the nose.
    plate(bm, [(-3.4, 13.9), (3.4, 13.9), (3.2, 19.9), (-3.2, 19.9)], 0.1, 0.44, 0.06, (PALE,) * 4,
          dz=lambda x, r: -0.012 * (r - 13.9))
    # Dark slot between the keel and the nose block (rows 20-21).
    L.box(bm, X(-2.9), Y(22.2), X(2.9), Y(19.7), 0.05, 0.215, mat=PORT)

    # Teal gun block at the nose (cols 9-14, rows 22-26), its top sloping down to the front and
    # its top back edge lit; a small vent slot at col 12, row 25.
    plate(bm, [(-3.6, 22.4), (3.6, 22.4), (3.5, 24.5), (2.7, 26.9), (-2.7, 26.9), (-3.5, 24.5)],
          -0.08, 0.31, 0.085, (TEAL, TEAL_LIT, TEAL, TEAL), light=(0, 1),
          dz=lambda x, r: -0.03 * max(0.0, r - 23.0))
    L.box(bm, X(-0.6), Y(26.0), X(0.6), Y(24.9), 0.1, 0.235, mat=VENT)

    # Left half, mirrored below.
    side = bmesh.new()
    # Shoulder plate over the back-left corner (cols 2-8, rows 1-6): flat top over the light band
    # (cols 5-8), sloping down to the outer edge.
    plate(side, [(-4.4, 1.15), (-4.4, 6.1), (-10.9, 6.1), (-10.9, 4.0), (-9.8, 2.7),
                 (-8.3, 1.7), (-6.6, 1.15)], 0.1, 0.5, 0.06, (ARMOUR,) * 4,
          dz=lambda x, r: -0.035 * max(0.0, -x - 7.3))
    # Cheek plate beside the cockpit (cols 5-8, rows 8-13), curving in to the keel (rows 14-17).
    plate(side, [(-7.6, 7.0), (-3.6, 7.0), (-3.6, 18.2), (-4.4, 18.2), (-7.6, 14.2)], 0.1, 0.42, 0.06,
          (ARMOUR,) * 4, dz=lambda x, r: -0.01 * max(0.0, r - 13.5) - 0.02 * max(0.0, -x - 6.2))
    # Dark seam under the shoulder plate's lower edge (row 6-7).
    L.box(side, X(-9.6), Y(7.0), X(-4.4), Y(6.0), 0.2, 0.282, mat=PORT)
    # Round ports in the flank: by the hull edge, lower flank, beside the keel.
    port(side, -8.2, 12.4, 1.05, (DARKP, PORT))
    port(side, -7.0, 16.1, 0.95, (DARKP, PORT))
    port(side, -5.0, 19.5, 0.85, (DARKP, PORT))
    L.mirror_x(side)
    me = bpy.data.meshes.new("tmp127")
    side.to_mesh(me)
    side.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)

    # Shift onto the sprite's axis (the centre of column 12).
    for v in bm.verts:
        v.co.x += L.px(AXIS)
    return L.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
