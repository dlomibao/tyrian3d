"""Rock wall with purple octagon caps over a bank of canisters (newsh2.shp 279, 281, 283): a
hard-surface 3D version of its sprites (as the player ships, DECISIONS.md D50-D53).

Seen in episode 1 (level 1.3) and episode 3. Three 2x2 enemies in a row make one 72 x 28 px block
(sprite.json `assemblyLayout`): newsh2-279 (left), newsh2-281 (middle) and newsh2-283 (right). Built
whole in assembly pixels and cut into its pieces with common.split_assembly (pivot = each piece's
centre, cut faces filled). One sprite frame per piece, one model per piece.

What the sprite fixes (outline, parts, colours; the sprite wins over the concept):
- Island rock round the machine (a band along the top, notches between the caps, piles at the lower
  left, cols 0-12, and lower right, cols 60-71): the sprite's own pixels as the islands' relief
  (lib_tiles.sprite_rock, DECISIONS.md D66), one rock object per piece, no outline, no shadow, so it
  reads as the island going on under the machine rather than a block with a rim.
- Three octagonal armour caps (edges cols 3..21 + 24k, rows 4..20; flats 7 px at top and bottom, 5 px
  at the sides, diagonals 5.5 px, fitted to the sprite's stair-steps), flat palette-88 tops whose lit NW /
  dark SE rims are a chamfer. The tallest parts (top about 8.8 px), overhanging a dark recessed
  pedestal on a low armoured plinth. Top relief stays shallow (segmented armour plates, a two-leaf
  hatch, bolts, a slatted vent on the east plate as the concept draws it): the sprite draws the top flat.
- Between each pair of caps a coupling housing (cols 20..29 / 44..53, rows 11..23, palette 89) with its
  lit chamfer at row 12 and a darker step behind it (row 11); its south end is a half dome (the
  sprite's darker stepped arch at rows 23-27, palette 88) whose south face is an armoured sensor eye.
- Four canisters (cols 13..20, 29..36, 36..44, 53..60; 89, 90, 89, 90): round barrels lying down the
  screen, axis north-south towards the player, with a raised collar, a dark groove band and an end
  flange round a deep glowing bore (the concept's lamps; the sprite cannot see the south faces).
Colours: palette index per part = the trimmed median of the sprite pixels it covers. Satin metal.
Underneath: closed solids standing on the rock, no detail.

Texture: no concept projection (maps.json "bake": "model"); an ambient-occlusion / edge colour
multiplier and a roughness / metalness map baked with Cycles, as the player ships (the rock is
there as an occluder, not baked). Outline shell as common.outline_shell (D51) on the machine of the
whole row, cut into the pieces without filling the seams (no ink line down the joints under the
couplings); the rock has none.

    blender --background --factory-startup --python assets/blender/enemies/assembly-newsh2-279.py \\
        [-- --no-bake] [--no-export] [--out row.glb] [--preview out.png]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "tiles")]
import common  # noqa: E402
import lib_tiles as lt  # noqa: E402

NAME = "assembly-newsh2-279"
PIECES = ["newsh2-279", "newsh2-281", "newsh2-283"]
W, H = 72, 28
PX = 1 / 12

# Material slots -> (palette index, metallic, roughness, emission)
SLOTS = {
    "cap": (88, 0.25, 0.42, 0), "side": (87, 0.25, 0.46, 0), "dark": (86, 0.25, 0.55, 0),
    "mid": (89, 0.25, 0.44, 0), "light": (90, 0.25, 0.42, 0), "lens": (173, 0.0, 0.2, 0.9),
    "lamp": (172, 0.0, 0.3, 1.2), "steel": (85, 0.45, 0.48, 0),
}
NAMES = list(SLOTS)
M = {n: i for i, n in enumerate(NAMES)}


# --- geometry helpers (plan coordinates in sprite px: c east, r south; h up) --------------------

def V(bm, c, r, h):
    return bm.verts.new(((c - W / 2) * PX, (H / 2 - r) * PX, h * PX))


def offset(poly, d):
    """Convex polygon (c, r) moved inward by d px (miter)."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        ex, ey = x1 - x0, y1 - y0
        ln = math.hypot(ex, ey)
        nx, ny = -ey / ln, ex / ln
        if (cx - x0) * nx + (cy - y0) * ny < 0:
            nx, ny = -nx, -ny
        lines.append(((x0 + nx * d, y0 + ny * d), (ex, ey)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-12:
            out.append(q)
            continue
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    return out


def clip(poly, a, b, c):
    """The part of a convex polygon where a*x + b*y <= c."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if fp * fq < 0:
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def bridge(bm, a, b, mat):
    n = len(a)
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((a[i], a[j], b[j], b[i]))
        f.material_index = mat


def prism(bm, poly, z0, z1, top, side, ch_top=0.0, ch_bot=0.0, chamfer=None, bottom=None):
    """A convex plan polygon extruded z0..z1 with optional top/bottom chamfers."""
    chamfer = side if chamfer is None else chamfer
    bottom = side if bottom is None else bottom
    rings, mats = [], []
    if ch_bot > 0:
        rings.append([V(bm, c, r, z0) for c, r in offset(poly, ch_bot)])
        rings.append([V(bm, c, r, z0 + ch_bot) for c, r in poly])
        mats.append(side)
    else:
        rings.append([V(bm, c, r, z0) for c, r in poly])
    rings.append([V(bm, c, r, z1 - ch_top) for c, r in poly])
    mats.append(side)
    if ch_top > 0:
        rings.append([V(bm, c, r, z1) for c, r in offset(poly, ch_top)])
        mats.append(chamfer)
    for a, b, m in zip(rings, rings[1:], mats):
        bridge(bm, a, b, m)
    bm.faces.new(list(reversed(rings[0]))).material_index = bottom
    bm.faces.new(rings[-1]).material_index = top


def rect(c0, r0, c1, r1):
    return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]


def loft(bm, rings, mats, cap0=True, cap1=True):
    """A closed tube through rings of (c, r, h) points (equal lengths); mats[i] spans ring i..i+1."""
    vr = [[V(bm, *p) for p in rg] for rg in rings]
    n = len(vr[0])
    for i, (a, b) in enumerate(zip(vr, vr[1:])):
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((a[k], a[j], b[j], b[k])).material_index = mats[i]
    if cap0:
        bm.faces.new(vr[0]).material_index = mats[0]
    if cap1:
        bm.faces.new(vr[-1]).material_index = mats[-1]


def section(cx, r, hz0, hw, hz, n=20, p=2.3):
    """A superellipse section across the rows at row r (power 2 = round), starting at the top."""
    e = 2 / p
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        s, c = math.sin(a), math.cos(a)
        out.append((cx + hw * math.copysign(abs(s) ** e, s), r, hz0 + hz * math.copysign(abs(c) ** e, c)))
    return out


# --- the parts ----------------------------------------------------------------------------------

CAP_Z0, CAP_Z1 = 5.6, 8.2  # armour slab
CAN_HZ, CAN_AXIS = 2.95, 2.95  # canister half height and axis height (px); tops at 5.9
CANS = [(12.95, 19.95, "mid"), (29.1, 35.95, "light"), (36.05, 43.9, "mid"), (53.05, 59.9, "light")]
HOUSINGS = [(24.5, 20.6), (48.5, 47.9)]  # (centre column, west end of the back step)

def octagon(cx, cr=12.0):
    """A cap's plan fitted to the sprite's stair-stepped octagon (cols cx-9..cx+9, rows 4..20): flats
    7 px across at the top and bottom, 5 px at the sides, 5.5 px diagonals."""
    return [(cx - 3.5, cr - 8), (cx + 3.5, cr - 8), (cx + 9, cr - 2.5), (cx + 9, cr + 2.5),
            (cx + 3.5, cr + 8), (cx - 3.5, cr + 8), (cx - 9, cr + 2.5), (cx - 9, cr - 2.5)]


def cap(bm, k):
    cx = 12 + 24 * k
    oct_ = octagon(cx)
    # armoured plinth (a shallow step round the cap's foot), the recessed pedestal and the slab
    prism(bm, offset(oct_, 0.9), -0.1, 1.25, M["side"], M["side"], ch_top=0.4)
    prism(bm, offset(oct_, 1.5), 1.1, 2.0, M["dark"], M["dark"], ch_top=0.25)
    prism(bm, offset(oct_, 2.2), 0.0, CAP_Z0 + 0.2, M["dark"], M["dark"])
    prism(bm, offset(oct_, 0.3), CAP_Z0, CAP_Z0 + 1.2, M["side"], M["side"], ch_bot=0.3)
    prism(bm, oct_, CAP_Z0 + 1.05, CAP_Z1, M["dark"], M["side"], ch_top=1.0, ch_bot=0.2, chamfer=M["cap"])
    # segmented armour ring: one plate per octagon side, split at the corners
    zt = CAP_Z1 + 0.35
    outer, inner = offset(oct_, 1.3), offset(oct_, 4.1)
    for i in range(8):
        j = (i + 1) % 8
        quad = [outer[i], outer[j], inner[j], inner[i]]
        ex, ey = outer[j][0] - outer[i][0], outer[j][1] - outer[i][1]
        ln = math.hypot(ex, ey)
        ux, uy = ex / ln, ey / ln
        g = 0.17
        quad = [(quad[0][0] + ux * g, quad[0][1] + uy * g), (quad[1][0] - ux * g, quad[1][1] - uy * g),
                (quad[2][0] - ux * g, quad[2][1] - uy * g), (quad[3][0] + ux * g, quad[3][1] + uy * g)]
        if i == 2:  # east side: a slatted vent between two short end plates (the concept's grille)
            r0, r1 = quad[0][1], quad[1][1]
            c0, c1 = min(q[0] for q in quad), max(q[0] for q in quad)
            c0 += 0.25
            prism(bm, [(c0, r0), (c1, r0), (c1, r0 + 1.1), (c0, r0 + 1.1)], CAP_Z1 - 0.05, zt, M["cap"], M["cap"], ch_top=0.12)
            prism(bm, [(c0, r1 - 1.1), (c1, r1 - 1.1), (c1, r1), (c0, r1)], CAP_Z1 - 0.05, zt, M["cap"], M["cap"], ch_top=0.12)
            for s in range(3):
                rr = r0 + 1.4 + s * 0.85
                prism(bm, rect(c0 + 0.35, rr, c1 - 0.2, rr + 0.45), CAP_Z1 - 0.05, zt - 0.08, M["side"], M["side"], ch_top=0.1)
            continue
        prism(bm, quad, CAP_Z1 - 0.05, zt, M["cap"], M["cap"], ch_top=0.14)
    # inner plate: a two-leaf hatch with a real gap across the middle
    ip = offset(oct_, 4.4)
    for a, b, c in ((0, 1, 12.0 - 0.13), (0, -1, -(12.0 + 0.13))):
        prism(bm, clip(ip, a, b, c), CAP_Z1 - 0.05, CAP_Z1 + 0.5, M["cap"], M["cap"], ch_top=0.2)
    # hex bolts at the inner plate's four diagonal corners
    for c, r in (ip[0], ip[1], ip[4], ip[5]):
        bc = cx + (c - cx) * 0.82
        br = 12 + (r - 12) * 0.78
        prism(bm, [(bc + 0.38 * math.cos(a), br + 0.38 * math.sin(a)) for a in [i * math.pi / 3 for i in range(6)]],
              CAP_Z1 + 0.45, CAP_Z1 + 0.68, M["steel"], M["steel"], ch_top=0.08)
    # two small amber lamps on the south face of the slab (the concept's rim lights)
    for dc in (-2.0, 2.0):
        prism(bm, rect(cx + dc - 0.6, 19.75, cx + dc + 0.6, 20.06), CAP_Z0 + 1.55, CAP_Z0 + 2.0, M["lamp"], M["lamp"])
    return oct_


def cylinder_r(bm, c, z, rad, r0, r1, face, side, sides=12):
    """A short cylinder along rows r0..r1 (axis N-S) at column c, height z; south face `face`."""
    a_ = [V(bm, c + rad * math.cos(2 * math.pi * k / sides), r0, z + rad * math.sin(2 * math.pi * k / sides)) for k in range(sides)]
    b_ = [V(bm, c + rad * math.cos(2 * math.pi * k / sides), r1, z + rad * math.sin(2 * math.pi * k / sides)) for k in range(sides)]
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((a_[i], a_[j], b_[j], b_[i])).material_index = side
    bm.faces.new(list(reversed(a_))).material_index = side
    bm.faces.new(b_).material_index = face


def lamp(bm, c, z, r_bezel, r_lens, r0, r1):
    """A round lamp on a south face: a steel bezel ring and a glowing lens set just inside it."""
    cylinder_r(bm, c, z, r_bezel, r0, r1 - 0.08, M["steel"], M["steel"], sides=20)
    cylinder_r(bm, c, z, r_bezel * 0.84, r0, r1 - 0.05, M["dark"], M["dark"], sides=20)
    cylinder_r(bm, c, z, r_lens, r0, r1, M["lens"], M["dark"], sides=16)


def housing(bm, cc, step_c0):
    # darker step behind (sprite row 11; the second one starts further east, as the sprite draws it),
    # the body, the roof hatch with bolts
    prism(bm, rect(step_c0, 10.8, cc + 3.9, 12.4), 0.0, 5.3, M["mid"], M["side"], ch_top=0.35)
    prism(bm, rect(cc - 4.3, 11.8, cc + 4.3, 23.5), 0.0, 6.4, M["mid"], M["side"], ch_top=0.8, chamfer=M["mid"])
    prism(bm, rect(cc - 2.9, 13.4, cc + 2.9, 21.8), 6.3, 6.62, M["mid"], M["mid"], ch_top=0.14)
    prism(bm, rect(cc - 2.0, 17.45, cc + 2.0, 17.75), 6.55, 6.66, M["dark"], M["dark"])
    for dc, r in ((-2.25, 14.1), (2.25, 14.1), (-2.25, 21.1), (2.25, 21.1)):
        prism(bm, [(cc + dc + 0.3 * math.cos(a), r + 0.3 * math.sin(a)) for a in [i * math.pi / 3 for i in range(6)]],
              6.55, 6.8, M["steel"], M["steel"], ch_top=0.07)
    # skirt under the dome
    prism(bm, rect(cc - 4.6, 22.6, cc + 4.6, 27.95), 0.0, 1.0, M["dark"], M["dark"], ch_top=0.2)
    # half dome on the south end (the sprite's darker stepped arch): centre on the south edge
    RC = 27.8
    rx, ry, z0, rz = 4.7, 5.0, 0.7, 5.4
    nphi, nth = 6, 10
    grid = []
    for i in range(nphi + 1):
        phi = (math.pi / 2) * i / nphi
        ring = []
        for j in range(nth + 1):
            th = math.pi * j / nth
            ring.append(V(bm, cc + rx * math.cos(phi) * math.cos(th), RC - ry * math.cos(phi) * math.sin(th),
                          z0 + rz * math.sin(phi)) if i < nphi else None)
        grid.append(ring)
    top = V(bm, cc, RC, z0 + rz)
    for i in range(nphi):
        for j in range(nth):
            if i + 1 < nphi:
                f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
            else:
                f = bm.faces.new((grid[i][j], top, grid[i][j + 1]))
            f.material_index = M["cap"]
    bm.faces.new(list(grid[0])).material_index = M["dark"]
    face = [grid[i][0] for i in range(nphi)] + [top] + [grid[i][nth] for i in reversed(range(nphi))]
    bm.faces.new(face).material_index = M["dark"]

    # the eye: a half-disc armoured rim standing on the dome's south face, and the lamp in it
    def half(s, r0, r1, mat_face, mat_side):
        pts = []
        for k in range(9):
            a = math.pi * k / 8
            pts.append((cc + rx * s * math.cos(a), z0 + 0.25 + (rz - 0.4) * s * math.sin(a)))
        a_ = [V(bm, c, r0, z) for c, z in pts]
        b_ = [V(bm, c, r1, z) for c, z in pts]
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a_[i], a_[j], b_[j], b_[i])).material_index = mat_side
        bm.faces.new(list(reversed(a_))).material_index = mat_side
        bm.faces.new(b_).material_index = mat_face
    half(0.9, RC - 0.05, 27.9, M["side"], M["side"])
    lamp(bm, cc, z0 + 1.9, 1.75, 1.25, RC - 0.3, 27.98)


def can(bm, c0, c1, slot):
    """A canister lying down the screen: a round barrel from under the cap to the south edge, with a
    raised collar, a dark groove band, an end flange and a deep glowing bore in its south end."""
    cx = (c0 + c1) / 2
    hw = (c1 - c0) / 2
    m, d, st = M[slot], M["dark"], M["steel"]
    S = lambda r, s: section(cx, r, CAN_AXIS, hw * s, CAN_HZ * s)  # noqa: E731
    O = lambda r, rad: section(cx, r, CAN_AXIS + 0.1, rad, rad, p=2.0)  # noqa: E731
    rb = min(hw, CAN_HZ) * 0.5
    rings = [S(14.6, 0.9), S(15.1, 1.0),
             S(20.5, 1.0), S(20.65, 1.05), S(21.65, 1.05), S(21.8, 1.0),  # collar
             S(24.8, 1.0), S(24.95, 0.94), S(25.55, 0.94), S(25.7, 1.0),  # groove band
             S(26.9, 1.0), S(27.0, 1.045), S(27.65, 1.045), S(27.95, 0.9),  # flange, chamfered
             O(27.95, rb * 1.35), O(27.85, rb * 1.12), O(27.85, rb), O(26.3, rb)]  # bezel, bore
    mats = [m, m, m, m, m, m, d, d, d, m, m, m, m, st, st, st, d]
    loft(bm, rings, mats + [M["lens"]])  # the bore's floor (the end cap) is the glowing lens


def build(sprite, coll):
    bm = bmesh.new()
    # cradle under the canisters (between them, the dark floor of their seams)
    prism(bm, rect(12.9, 15.0, 60.0, 27.95), 0.0, 1.0, M["dark"], M["dark"], ch_top=0.2)
    # a bracket west of the first canister (the sprite's dark column at col 12, rows 20-22)
    prism(bm, rect(12.2, 19.6, 13.4, 23.0), 0.0, 3.0, M["dark"], M["dark"], ch_top=0.3)
    for k in range(3):
        cap(bm, k)
    for cc, step_c0 in HOUSINGS:
        housing(bm, cc, step_c0)
    for c0, c1, slot in CANS:
        can(bm, c0, c1, slot)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for mat in materials(sprite):
        me.materials.append(mat)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    smooth(obj)
    return obj


def materials(sprite):
    out = []
    for n in NAMES:
        idx, met, rough, em = SLOTS[n]
        out.append(common.palette_material(sprite, idx, "a279", metallic=met, roughness=rough, emission_strength=em))
    return out


def smooth(obj, angle=40):
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(angle))


def merged_sprite(root):
    """The first piece's sprite.json with the colours of all three pieces."""
    sprite = common.load_sprite(root, PIECES[0])
    for p in PIECES[1:]:
        sprite["colors"].update(common.load_sprite(root, p)["colors"])
    return sprite


def layout_px(root):
    """[(piece, cx, cy)] in assembly px relative to the block's centre."""
    s = common.load_sprite(root, PIECES[0])
    lay = [e for e in s["assemblyLayout"] if e["model"] in PIECES]
    x0 = min(e["cx"] for e in lay) - 12
    y0 = min(e["cy"] for e in lay) - 14
    return [(e["model"], e["cx"] - x0 - W / 2, e["cy"] - y0 - H / 2) for e in lay]


# --- bake (as the ships: occlusion / edge colour multiplier, roughness / metalness) ---------------

def bake_maps(obj, out_dir, size=1024, samples=64):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:  # noqa: BLE001
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new("nsh2_279_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nsh2_279_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        L = nt.links.new
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.14
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                L(v, comb.inputs[k])
            L(comb.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        if mode == "colour":
            import numpy as np
            px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
            img.pixels.foreach_get(px)
            px = px.reshape(-1, 4)
            px[px[:, 0] < 0.3] = (0.85, 0.85, 0.85, 1.0)  # unbaked texels (the bake writes >= 0.48)
            img.pixels.foreach_set(px.ravel())
        if mode == "rm":
            # A floor on the roughness: a sub-texel face (a rib's chamfer) can sample an unbaked
            # (black) texel, which would read as a mirror-smooth white speck.
            import numpy as np
            px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
            img.pixels.foreach_get(px)
            px = px.reshape(-1, 4)
            unbaked = px[:, 0] < 0.5  # the bake writes R = 1 everywhere it reaches
            px[unbaked] = (1.0, 0.6, 0.3, 1.0)
            px[:, 1] = np.maximum(px[:, 1], 0.32)
            img.pixels.foreach_set(px.ravel())
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for m in mats:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        if bsdf.inputs["Emission Strength"].default_value > 0:
            continue  # lamps and lenses keep their flat glow
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


def split_open(obj, layout, coll):
    """Cut the outline shell into the pieces without filling the cuts (no outline along the seams)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        out[name] = sh
    return out


def main(script_file, argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = common.repo_root(script_file)
    sprite = merged_sprite(root)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    print(f"{NAME} row: {len(obj.data.polygons)} faces, {sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles")
    layout = layout_px(root)
    # The island rock round the machine (D66), in the row's place so the bake sees it as an occluder.
    rocks = lt.build_sprite_rock(root, [obj], layout, W, H, coll, "a279rock")
    for p, cx, cy in layout:
        rocks[p].location = (cx * PX, -cy * PX, 0)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="nsh2_279_bake_"))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=4500)
    parts = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll)
    for p, _, _ in layout:
        smooth(parts[p])
        rocks[p].location = (0, 0, 0)
        print(f"{NAME} piece {p}: {sum(len(f.vertices) - 2 for f in parts[p].data.polygons)} triangles, "
              f"outline {len(shells[p].data.polygons)} faces, rock {sum(len(f.vertices) - 2 for f in rocks[p].data.polygons)} triangles")
    if "--no-export" not in argv:
        for p, _, _ in layout:
            data = common.load_sprite(root, p)
            common.export_sprite_model(root, [parts[p], shells[p], rocks[p]], f"enemies/{p}", data["sprites"], image_format=fmt)
    for p, cx, cy in layout:  # the pieces back at their places in the row
        parts[p].location = (cx * PX, -cy * PX, 0)
        shells[p].parent = parts[p]
        shells[p].hide_render = True
        rocks[p].parent = parts[p]
    obj.hide_render = True
    shell.hide_render = True
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        common.export_glb([parts[p] for p, _, _ in layout] + [shells[p] for p, _, _ in layout] + [rocks[p] for p, _, _ in layout],
                          out, image_format=fmt)
        print("wrote", out)
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        for p, _, _ in layout:
            data = common.load_sprite(root, p)
            img = root / "reference" / "models" / p / data["frames"][0]["image"]
            loc = parts[p].location.copy()
            parts[p].location = (0, 0, 0)
            common.render_preview([parts[p], rocks[p]], str(out.parent / f"{p}.png"), str(img), size=2)
            parts[p].location = loc
    return parts, shells, layout


if __name__ == "__main__":
    main(__file__)
