"""Helpers shared by batch b078's model scripts (build-models.sh skips lib_ modules).

- P / X / Y: sprite pixel centres (24x28 block) to Blender units.
- rounded_block: the rounded, glossy block that newshm.shp's wall tiles (newshm-1, -15, -17, -53,
  -55, -153) all share: a pillow-topped square block whose south edge rolls down toward the
  viewer, with faces coloured by which way they look (lit north-west rim, dark south front).
- ribbon: a raised strip following a polyline drawn in sprite pixels (emblems on the tiles).
- dome: a half ellipsoid sitting on a plane (gems, balls).
- finish: mesh object with smooth shading on curved faces and flat shading on flat tops.
"""

import math

import bmesh
import bpy

import common


def X(c):
    """Sprite column (pixel centre, may be fractional) to Blender X."""
    return (c + 0.5 - 12) / 12


def Y(r):
    """Sprite row (pixel centre, may be fractional) to Blender Y (sprite up is +Y)."""
    return (14 - (r + 0.5)) / 12


def P(c, r):
    return X(c), Y(r)


# --- the rounded block ---------------------------------------------------------------------------

def _rounded_rect(x0, y0, x1, y1, r, segs):
    """Counter-clockwise outline of a rounded rectangle (units), 4 * (segs + 1) points."""
    r = max(0.0, min(r, (x1 - x0) / 2 - 1e-4, (y1 - y0) / 2 - 1e-4))
    corners = [(x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]
    pts = []
    for cx, cy, a0 in corners:
        for i in range(segs + 1):
            a = math.radians(a0 + 90 * i / segs)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# Rings from the base up: (inset east/west px, inset north px, inset south px, z units, corner px).
BLOCK_PROFILE = [
    (0.0, 0.0, 0.0, 0.00, 6.8),
    (0.0, 0.0, 0.0, 0.14, 6.8),
    (0.3, 0.3, 1.0, 0.22, 6.6),
    (0.8, 0.8, 2.8, 0.29, 6.2),
    (1.4, 1.4, 5.0, 0.345, 5.7),
    (2.1, 2.1, 7.2, 0.38, 5.2),
    (2.8, 2.8, 9.0, 0.397, 4.7),
]
BLOCK_TOP = 0.40  # the flat top (emblems sit on it)


def block_top_rect():
    """The flat top's extent (x0, y0, x1, y1) in units."""
    iew, inn, ins, _, _ = BLOCK_PROFILE[-1]
    return (-(11.5 - iew) / 12, (-13.5 + ins) / 12, (11.5 - iew) / 12, (13.5 - inn) / 12)


def rounded_block(bm, mats, segs=6):
    """The tile block, filling the 24x28 sprite inside its 1 px outline, base at z = 0.

    `mats` maps roles to material indices: top, rim_light (north-west bevel), rim (north and
    east bevels), front (south slope), front_low (south wall), glint (south-east rim light)."""
    rings = []
    for iew, inn, ins, z, rad in BLOCK_PROFILE:
        outline = _rounded_rect((-11.5 + iew) / 12, (-13.5 + ins) / 12, (11.5 - iew) / 12, (13.5 - inn) / 12,
                                rad / 12, segs)
        rings.append([bm.verts.new((x, y, z)) for x, y in outline])
    # Slightly domed top: one more ring inside, raised.
    top_ring = rings[-1]
    n = len(top_ring)
    new_faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            new_faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    cap = bm.faces.new(top_ring)
    bot = bm.faces.new(list(reversed(rings[0])))
    bot.material_index = mats["front_low"]
    cap.material_index = mats["top"]
    for f in new_faces:
        f.normal_update()
        nx, ny, nz = f.normal
        c = f.calc_center_median()
        if ny < -0.35 and abs(ny) >= abs(nx) * 0.6:
            role = "front" if nz > 0.25 else "front_low"
            if c.x > 0.7 and c.y < -0.7 and nz > 0.1:
                role = "glint"
        elif nx < -0.3 and c.y > -0.75:
            role = "rim_light"
        elif ny > 0.3 and c.x < 0.2:
            role = "rim_light"
        elif nx > 0.3 and c.y < -0.75:
            role = "glint"
        else:
            role = "rim"
        f.material_index = mats[role]
    return cap


# --- emblem strips -------------------------------------------------------------------------------

def ribbon(bm, pts, width_px, z0, z1, mat, top_scale=0.6):
    """A raised strip following `pts` (sprite pixel coordinates (col, row)), `width_px` wide at the
    base and narrower on top, from z0 to z1. Joints are mitred."""
    P2 = [P(c, r) for c, r in pts]
    n = len(P2)
    hw = width_px / 24
    offs = []
    for i in range(n):
        if i == 0:
            dx, dy = P2[1][0] - P2[0][0], P2[1][1] - P2[0][1]
            d = math.hypot(dx, dy)
            nx, ny, s = -dy / d, dx / d, 1.0
        elif i == n - 1:
            dx, dy = P2[i][0] - P2[i - 1][0], P2[i][1] - P2[i - 1][1]
            d = math.hypot(dx, dy)
            nx, ny, s = -dy / d, dx / d, 1.0
        else:
            ax, ay = P2[i][0] - P2[i - 1][0], P2[i][1] - P2[i - 1][1]
            bx, by = P2[i + 1][0] - P2[i][0], P2[i + 1][1] - P2[i][1]
            la, lb = math.hypot(ax, ay), math.hypot(bx, by)
            n1 = (-ay / la, ax / la)
            n2 = (-by / lb, bx / lb)
            mx, my = n1[0] + n2[0], n1[1] + n2[1]
            lm = math.hypot(mx, my) or 1.0
            nx, ny = mx / lm, my / lm
            s = min(1.0 / max(nx * n1[0] + ny * n1[1], 0.35), 2.5)
        offs.append((nx * s, ny * s))
    bl, br, tl, tr = [], [], [], []
    for (x, y), (ox, oy) in zip(P2, offs):
        bl.append(bm.verts.new((x + ox * hw, y + oy * hw, z0)))
        br.append(bm.verts.new((x - ox * hw, y - oy * hw, z0)))
        tl.append(bm.verts.new((x + ox * hw * top_scale, y + oy * hw * top_scale, z1)))
        tr.append(bm.verts.new((x - ox * hw * top_scale, y - oy * hw * top_scale, z1)))
    faces = []
    for i in range(n - 1):
        j = i + 1
        faces.append(bm.faces.new((tl[i], tr[i], tr[j], tl[j])))
        faces.append(bm.faces.new((bl[i], tl[i], tl[j], bl[j])))
        faces.append(bm.faces.new((tr[i], br[i], br[j], tr[j])))
        faces.append(bm.faces.new((br[i], bl[i], bl[j], br[j])))
    faces.append(bm.faces.new((bl[0], br[0], tr[0], tl[0])))
    faces.append(bm.faces.new((tl[-1], tr[-1], br[-1], bl[-1])))
    for f in faces:
        f.material_index = mat
    return faces


def disc(bm, c, r, rx_px, ry_px, z0, z1, mat, sides=12, top_scale=0.8, angle0=0.0):
    """A small raised disc / octagon plate centred on pixel (c, r)."""
    cx, cy = P(c, r)
    bot, top = [], []
    for i in range(sides):
        a = angle0 + 2 * math.pi * i / sides
        x, y = math.cos(a) * rx_px / 12, math.sin(a) * ry_px / 12
        bot.append(bm.verts.new((cx + x, cy + y, z0)))
        top.append(bm.verts.new((cx + x * top_scale, cy + y * top_scale, z1)))
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
    for i in range(sides):
        j = (i + 1) % sides
        faces.append(bm.faces.new((bot[i], bot[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat
    return faces


def dome(bm, cx, cy, rx, ry, h, z=0.0, rings=5, sides=16, mat=0, bottom=True, power=1.0):
    """A half ellipsoid (units) standing on z, centred on (cx, cy), `h` tall."""
    verts = []
    for k in range(rings):
        phi = (math.pi / 2) * k / rings
        s, zz = math.cos(phi) ** power, math.sin(phi)
        ring = []
        for i in range(sides):
            a = 2 * math.pi * i / sides
            ring.append(bm.verts.new((cx + rx * s * math.cos(a), cy + ry * s * math.sin(a), z + h * zz)))
        verts.append(ring)
    apex = bm.verts.new((cx, cy, z + h))
    faces = []
    for r0, r1 in zip(verts, verts[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for i in range(sides):
        j = (i + 1) % sides
        faces.append(bm.faces.new((verts[-1][i], verts[-1][j], apex)))
    if bottom:
        faces.append(bm.faces.new(list(reversed(verts[0]))))
    for f in faces:
        f.material_index = mat
    return faces


def finish(name, bm, mats, coll, flat_z=0.97, flat_ranges=()):
    """Mesh object: faces whose normal points almost straight up (flat tops) are flat shaded,
    and so are faces with an index in one of `flat_ranges` ((start, end) face indices); the
    rest are smooth."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = poly.normal.z < flat_z and not any(a <= poly.index < b for a, b in flat_ranges)
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def run(file, name, build):
    """The usual main(): load the sprite, build, export, optional preview."""
    import sys
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    obj = build(sprite)
    objs = obj if isinstance(obj, list) else [obj]
    common.export_sprite_model(root, objs, f"enemies/{name}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = root / "reference" / "models" / name / sprite["frames"][0]["image"]
        common.render_preview(objs, out, ref, size=sprite["frames"][0]["size"])


# --- the newshm wall tiles -----------------------------------------------------------------------

def tile_materials(sprite, name, top, rim_light, rim, front, front_low, glint, metallic=0.35, roughness=0.3):
    """Palette materials for the block roles; returns (mats list, role -> index dict)."""
    roles = dict(top=top, rim_light=rim_light, rim=rim, front=front, front_low=front_low, glint=glint)
    mats, index, by_pal = [], {}, {}
    for role, pal in roles.items():
        if pal not in by_pal:
            by_pal[pal] = len(mats)
            mats.append(common.palette_material(sprite, pal, name, metallic=metallic, roughness=roughness))
        index[role] = by_pal[pal]
    return mats, index
