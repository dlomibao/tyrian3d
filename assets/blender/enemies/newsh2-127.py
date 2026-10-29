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
# Hull sections, back to nose, traced from the concept (textures/newsh2-127/concept.png) inside the
# sprite's outline: (row edge, half width px, top z, bottom z).
HULL = [(0.05, 4.6, 0.15, -0.05), (1.0, 8.3, 0.19, -0.09), (2.0, 9.4, 0.22, -0.12),
        (3.0, 10.3, 0.24, -0.14), (4.3, 11.0, 0.26, -0.16), (11.5, 11.0, 0.27, -0.17),
        (13.0, 10.5, 0.27, -0.17), (14.0, 9.9, 0.26, -0.16), (16.0, 8.8, 0.25, -0.15),
        (18.0, 7.8, 0.23, -0.14), (20.0, 6.8, 0.21, -0.12), (22.3, 5.8, 0.19, -0.11),
        (23.5, 5.1, 0.17, -0.1), (25.0, 4.7, 0.14, -0.08), (26.3, 4.0, 0.11, -0.06),
        (27.3, 3.0, 0.08, -0.04), (27.8, 1.8, 0.05, -0.02)]
NOSE_ROW = 23.5  # the hull is teal from here on (the nose cowl's flanks)


def E(pts):
    """Concept outlines are traced as (sprite pixel-edge column, row); to model px from the axis."""
    return [(x - 12.5, r) for x, r in pts]


def hull_loft(bm, mat, nose_mat):
    rings = [[bm.verts.new((u * w * PX, Y(r), zb + v * (zt - zb))) for u, v in PROFILE]
             for r, w, zt, zb in HULL]
    n = len(PROFILE)
    for (r, *_), r0, r1 in zip(HULL, rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = nose_mat if r >= NOSE_ROW - 1e-6 else mat
            f.smooth = False
    for f in (bm.faces.new(rings[0]), bm.faces.new(list(reversed(rings[-1])))):
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
        pal(84, metallic=0.4, roughness=0.45),  # 0 hull flanks
        pal(88, metallic=0.45, roughness=0.4),  # 1 shoulder armour (pauldrons)
        pal(83, metallic=0.4, roughness=0.5),  # 2 dark frames, port rims
        pal(88, metallic=0.4, roughness=0.4),  # 3 light cheek plates, cockpit tab
        pal(80, metallic=0.1, roughness=0.8),  # 4 dark ports, slots, recesses
        pal(59, metallic=0.6, roughness=0.08, emission_strength=0.6),  # 5 cockpit glass
        pal(102, metallic=0.8, roughness=0.3),  # 6 yoke, hinge, bars, brackets (polished metal)
        pal(134, metallic=0.6, roughness=0.08, emission_strength=1.2),  # 7 glass edges catching the light
        pal(134, metallic=0.5, roughness=0.08, emission_strength=1.0),  # 8 rear glass panel (lit)
        pal(54, metallic=0.35, roughness=0.5),  # 9 teal nose cowl
        pal(131, metallic=0.5, roughness=0.35),  # 10 lit edges of the cowl
        pal(86, metallic=0.4, roughness=0.45),  # 11 cockpit pod, keel
        pal(101, metallic=0.4, roughness=0.6),  # 12 deck between the shoulders
        pal(85, metallic=0.4, roughness=0.45),  # 13 pauldron rims
        pal(136, metallic=0.0, roughness=0.3, emission_strength=1.2),  # 14 chin light
        pal(128, metallic=0.5, roughness=0.4),  # 15 cowl spine and rim
    ]
    (HULLM, ARMOUR, DARKP, PALE, PORT, GLASS, BAR, GLASS_HI, PANEL, TEAL, TEAL_LIT, POD, DECK, RIM,
     LIGHT, TEAL_RIM) = range(16)
    bm = bmesh.new()
    hull_loft(bm, HULLM, TEAL)

    # --- centre line ---------------------------------------------------------------------------
    # Rear glass panel at the back edge (cols 10-15, rows 0-2): a chamfered dark frame holding a
    # lit cyan glass block.
    plate(bm, E([(10.0, 0.08), (15.0, 0.08), (15.6, 0.6), (15.6, 2.3), (15.0, 2.95), (10.0, 2.95),
                 (9.4, 2.3), (9.4, 0.6)]), 0.08, 0.5, 0.03, (DARKP,) * 4)
    plate(bm, E([(10.5, 0.4), (14.5, 0.4), (14.9, 0.75), (14.9, 2.1), (14.5, 2.5), (10.5, 2.5),
                 (10.1, 2.1), (10.1, 0.75)]), 0.3, 0.54, 0.05, (PANEL, GLASS_HI, PANEL, PANEL), light=(0, -1))

    # Deck in the channel between the shoulders (rows 3-7), dark, below the yoke.
    plate(bm, E([(9.4, 2.9), (15.6, 2.9), (15.6, 6.7), (9.4, 6.7)]), 0.12, 0.28, 0.02, (DECK,) * 4)
    # Yoke: a Y bracket from the panel's lower corners to a knuckle, a hinge rod across it and a
    # bolt either side.
    for x0, x1 in ((10.9, 12.0), (14.1, 13.0)):
        L.sweep(bm, [(X(x0 - 12.5), Y(2.8), 0.37, 0.4 * PX, 0.4 * PX), (X(x1 - 12.5), Y(4.7), 0.37, 0.4 * PX, 0.4 * PX)],
                sides=6, mat=BAR, smooth=False)
    plate(bm, E([(11.6, 4.5), (13.4, 4.5), (13.4, 6.4), (11.6, 6.4)]), 0.2, 0.42, 0.02, (BAR,) * 4)
    L.sweep(bm, [(X(-2.3), Y(5.5), 0.36, 0.45 * PX, 0.45 * PX), (X(2.3), Y(5.5), 0.36, 0.45 * PX, 0.45 * PX)],
            sides=8, mat=BAR)
    for x in (-2.6, 2.6):
        L.ellipsoid(bm, X(x), Y(5.2), 0.3, 0.5 * PX, 0.5 * PX, 0.12, mat=BAR, segments=8, rings=4)

    # Cockpit pod (cols 10-15, rows 6-13): a raised chamfered housing holding the faceted glass
    # canopy, a thin bar across the glass and a light tab at its foot.
    plate(bm, E([(10.6, 6.2), (14.4, 6.2), (15.4, 7.2), (15.5, 12.4), (14.5, 13.6), (10.5, 13.6),
                 (9.5, 12.4), (9.6, 7.2)]), 0.12, 0.45, 0.04, (POD,) * 4)
    plate(bm, E([(11.0, 7.8), (14.0, 7.8), (14.9, 8.7), (14.9, 12.0), (14.0, 12.9), (11.0, 12.9),
                 (10.1, 12.0), (10.1, 8.7)]), 0.3, 0.6, 0.07, (GLASS, GLASS_HI, GLASS, GLASS), light=(0, -1))
    L.box(bm, X(-1.9), Y(10.6), X(1.9), Y(10.0), 0.55, 0.615, mat=BAR)
    plate(bm, E([(11.4, 12.85), (13.6, 12.85), (13.6, 13.8), (11.4, 13.8)]), 0.3, 0.5, 0.03, (PALE,) * 4)

    # Keel plate below the cockpit (rows 13-19), sloping down to the nose, narrowing at its foot.
    plate(bm, E([(9.7, 13.5), (15.3, 13.5), (15.2, 18.2), (14.4, 19.3), (10.6, 19.3), (9.8, 18.2)]),
          0.1, 0.42, 0.05, (POD,) * 4, dz=lambda x, r: -0.012 * (r - 13.5))

    # Chin: a dark recess (rows 19-22) holding a teal light between two brackets.
    L.box(bm, X(10.3 - 12.5), Y(22.4), X(14.7 - 12.5), Y(19.2), 0.04, 0.22, mat=PORT)
    plate(bm, E([(11.1, 19.5), (13.9, 19.5), (13.9, 20.9), (11.1, 20.9)]), 0.12, 0.29, 0.04, (LIGHT,) * 4)
    for x0 in (11.2, 13.2):
        L.box(bm, X(x0 - 12.5), Y(21.9), X(x0 + 0.6 - 12.5), Y(20.6), 0.1, 0.3, mat=BAR)

    # Teal nose cowl (rows 22-28), rounded at the front, its top sloping down to the front; a
    # four-slot grille at its back and a raised spine down the middle.
    cowl_dz = lambda x, r: -0.03 * max(0.0, r - 23.0)  # noqa: E731
    plate(bm, E([(8.3, 22.3), (16.7, 22.3), (17.0, 23.8), (16.5, 25.6), (15.3, 27.0), (14.1, 27.7),
                 (10.9, 27.7), (9.7, 27.0), (8.5, 25.6), (8.0, 23.8)]),
          -0.08, 0.32, 0.07, (TEAL, TEAL_LIT, TEAL, TEAL), light=(0, 1), dz=cowl_dz)
    plate(bm, E([(9.0, 22.3), (16.0, 22.3), (16.0, 22.9), (9.0, 22.9)]), 0.1, 0.345, 0.02, (TEAL_RIM,) * 4)
    for x0 in (10.9, 11.8, 12.7, 13.6):
        L.box(bm, X(x0 - 12.5), Y(23.85), X(x0 + 0.5 - 12.5), Y(23.1), 0.2, 0.33, mat=PORT)
    plate(bm, E([(11.6, 24.2), (13.4, 24.2), (13.4, 27.5), (11.6, 27.5)]), 0.05, 0.35, 0.025,
          (TEAL_RIM, TEAL_LIT, TEAL_RIM, TEAL_RIM), light=(0, 1), dz=cowl_dz)

    # --- left half, mirrored below -------------------------------------------------------------
    side = bmesh.new()
    sh_dz = lambda x, r: -0.035 * max(0.0, -x - 6.3)  # noqa: E731
    # Shoulder pauldron over the back-left: a big plate from the rear panel round the corner to the
    # flank (rows 0-10), the tallest part of the craft, falling away to its outer edge ...
    upper = [(9.4, 5.4), (7.5, 5.6), (5.5, 6.1), (4.0, 6.9), (2.7, 7.9), (1.65, 8.9)]
    plate(side, E([(9.4, 0.15)] + upper + [(1.6, 7.6), (1.6, 6.0), (2.0, 4.0), (3.0, 2.4), (4.4, 1.15),
                                           (6.6, 0.45), (8.0, 0.15)]),
          0.1, 0.56, 0.06, (ARMOUR,) * 4, dz=sh_dz)
    # ... and its rolled rim along the lower edge, a step down.
    plate(side, E(upper[::-1] + [(1.6, 11.0), (2.4, 10.3), (3.4, 9.3), (4.6, 8.3), (6.0, 7.5), (7.8, 6.9),
                                 (9.4, 6.7)]),
          0.1, 0.47, 0.03, (RIM,) * 4, dz=sh_dz)
    # Light cheek plate beside the cockpit (rows 7-17), curving in to the keel.
    plate(side, E([(9.4, 6.9), (9.4, 17.3), (8.4, 16.4), (7.4, 14.8), (6.9, 12.5), (7.0, 8.5), (7.7, 7.0)]),
          0.1, 0.38, 0.05, (PALE,) * 4, dz=lambda x, r: -0.012 * max(0.0, r - 12.0))
    # Round turbine ports in the flank, where the concept draws them.
    port(side, 4.7 - 12.5, 11.1, 1.2, (BAR, PORT))
    port(side, 5.8 - 12.5, 15.2, 1.05, (BAR, PORT))
    port(side, 8.1 - 12.5, 18.6, 1.0, (BAR, PORT))
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
