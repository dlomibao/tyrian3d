"""Blue armoured gunship (newshv.shp frame 48): a 3D version of its sprite.

What it is: a heavy steel-blue gunship of episode 2 (levels 17 and 19, MARKERS and MISTAKES), flying
down the screen nose first (sprite bottom = nose). At its stern (sprite top) a raised armoured spine
runs fore and aft with a dark slot sunk in its top, flanked by two big rounded shoulder plates, each
an outer dome lobe and an inner ridge, their front edges rolling down into a dark band. Under the
shoulders two side pods run forward, ending in grey claws curling in along the flanks. A grey gun bar
crosses the middle, a muzzle at each end, with a red light in a dark housing at its centre. Forward of
it the armoured hull carries twin ridges, a dark transverse groove, and a ribbed nose tapering to a
short tip. Belly: a plain closed rounded underside (it flies free).

Built in sprite pixels (x right, y down the sprite, z up; 12 px = 1 unit), converted at the end.
Colours are the sprite's own palette index per region (armour 56, side pods 53, ridges 58, shadow
band and groove 52, slot 50, gun bar 7, collars 9, claws 5, housing 3, light 117/119); shading and
highlights come from the game's light.

Run: blender --background --python assets/blender/enemies/newshv-48.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newshv-48"
MODEL = f"enemies/{NAME}"

CX = 12.0  # the sprite's mirror line (pixel edge between columns 11 and 12)

# material slots
BODY, POD, RIDGE, DARK, SLOT, GREY, GREY_LT, CLAW, HOUSING, RED, RED_HOT = range(11)
STEEL = (BODY, POD, RIDGE, DARK, GREY, GREY_LT, CLAW)
STEEL_SPEC = 0.5 * ((1.0 / 3.0) ** 2 / 0.04)  # F0 of IOR 2.0


def sgnpow(v, e):
    return math.copysign(abs(v) ** e, v)


def frange(a, b, step):
    n = max(1, round((b - a) / step))
    return [a + (b - a) * i / n for i in range(n + 1)]


def merge_ys(*lists):
    return sorted(set(round(v, 4) for lst in lists for v in lst))


# --- sections and lofts (as newshv-165) -----------------------------------------------------------

def section(cx, zc, hw, ht, hb, sides, nt=2.4, nb=2.0):
    """A closed cross-section (x, z): superellipse top (exponent nt) and bottom (nb)."""
    pts = []
    for k in range(sides):
        a = 2 * math.pi * (k + 0.5) / sides
        c, s = math.cos(a), math.sin(a)
        n = nt if s >= 0 else nb
        x = cx + hw * sgnpow(c, 2 / n)
        z = zc + (ht * sgnpow(s, 2 / nt) if s >= 0 else abs(hb) * sgnpow(s, 2 / nb))
        pts.append((x, z))
    return pts


def loft(bm, ys, secf, mat):
    """A closed body through sections secf(y) -> [(x, z)] at each y; the ends close with a fan to
    the end section's centre. Returns the new faces."""
    faces = []
    rings = []
    for y in ys:
        rings.append([bm.verts.new((x, y, z)) for x, z in secf(y)])
    for r0, r1 in zip(rings, rings[1:]):
        n = len(r0)
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for ring in (rings[0], rings[-1]):
        c = sum((v.co for v in ring), Vector()) / len(ring)
        cv = bm.verts.new(c)
        n = len(ring)
        for i in range(n):
            faces.append(bm.faces.new((ring[i], ring[(i + 1) % n], cv)))
    for f in faces:
        f.material_index = mat
    return faces


def tube(bm, points, half_w, half_h, sides=10, mats=None, mat=0):
    """A tube along 3D points with a horizontal and vertical half-size per point (0 = a tip);
    mats[i] colours the segment from point i to i + 1."""
    pts = [Vector(p) for p in points]
    rings = []
    for i, p in enumerate(pts):
        if half_w[i] == 0:
            rings.append([bm.verts.new(p)])
            continue
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t.normalize()
        side = t.cross(Vector((0, 0, 1))).normalized()
        up = side.cross(t).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(p + side * math.cos(a) * half_w[i] + up * math.sin(a) * half_h[i]))
        rings.append(ring)
    faces = []
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        m = mats[i] if mats else mat
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                f = bm.faces.new((r0[0], r1[k], r1[j]))
            elif len(r1) == 1:
                f = bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = m
            faces.append(f)
    for ring, m in ((rings[0], (mats or [mat])[0]), (rings[-1], (mats or [mat])[-1])):
        if len(ring) > 1:
            f = bm.faces.new(ring)
            f.material_index = m
            faces.append(f)
    return faces


def hull(bm, points, mat):
    verts = [bm.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = [g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)]
    if junk:
        bmesh.ops.delete(bm, geom=list(set(junk)), context="VERTS")
    faces = list({f for v in verts if v.is_valid for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=[v for v in verts if v.is_valid],
                             edges=list({e for f in faces for e in f.edges}))
    faces = list({f for v in verts if v.is_valid for f in v.link_faces})
    for f in faces:
        f.material_index = mat
    return faces


def ellipsoid(bm, c, r, mat, rings=8, sides=14):
    """An ellipsoid lofted along y (its lower half squashed to 0.6)."""
    cx, cy, cz = c
    rx, ry, rz = r

    def k(y):
        return math.sqrt(max(0.0, 1 - ((y - cy) / ry) ** 2))

    ys = [cy - ry * math.cos(math.pi * i / rings) for i in range(1, rings)]
    return loft(bm, ys, lambda y: section(cx, cz, max(0.02, rx * k(y)), max(0.02, rz * k(y)),
                                          -max(0.02, 0.6 * rz * k(y)), sides, nt=2.0), mat)


def mirror(bm, faces):
    """Mirror faces about x = CX."""
    vmap = {}
    out = []
    for f in faces:
        if not f.is_valid:
            continue
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = bm.verts.new((2 * CX - v.co.x, v.co.y, v.co.z))
            vs.append(vmap[v])
        nf = bm.faces.new(list(reversed(vs)))
        nf.material_index = f.material_index
        out.append(nf)
    return out


# --- the parts' plan and height profiles (sprite px, fitted to the sprite mask) --------------------

# Hull: rows 9-28, columns 6-17, tapering over rows 25-27 to the nose tip (columns 10-13).
HULL_Y0, HULL_Y1 = 9.0, 27.95
HULL_HW = T.pchip([9.0, 10.0, 13.0, 24.5, 25.5, 26.4, 27.2, 27.95], [5.0, 5.95, 6.0, 6.0, 5.75, 4.9, 2.2, 1.5])
HULL_ZT = T.pchip([9.0, 10.5, 13.0, 16.0, 17.6, 18.4, 19.6, 20.4, 23.0, 25.5, 27.0, 27.95],
                  [3.2, 3.8, 4.4, 4.6, 4.5, 3.6, 3.6, 4.3, 4.1, 3.4, 2.3, 1.3])
HULL_ZB = T.pchip([9.0, 12.0, 24.0, 27.0, 27.95], [1.8, 2.5, 2.5, 1.5, 0.8])
HULL_NT = 2.6


def hull_z(x, y):
    hw = HULL_HW(y)
    t = min(1.0, abs(x - CX) / hw)
    return HULL_ZT(y) * (1 - t ** HULL_NT) ** (1 / HULL_NT)


# Spine: columns 9-14, rows 0-10, a flat-topped armoured ridge sloping down at its front (row 9).
SP_HW = T.pchip([0.0, 0.5, 1.0, 10.0], [2.6, 2.95, 3.0, 3.0])
SP_ZT = T.pchip([0.0, 0.3, 0.8, 2.0, 8.2, 9.0, 10.0], [3.4, 5.4, 6.5, 6.8, 6.8, 5.6, 4.4])
SP_ZB = T.pchip([0.0, 0.4, 1.2, 10.0], [0.3, 0.75, 1.0, 1.0])
SP_NT = 4.0

# Left shoulder plate: from its outer edge XL(y) to the spine (x 9.25), rows 1-10.
SH_Y0, SH_Y1, SH_XR = 0.95, 9.85, 9.25
SH_XL = T.pchip([0.95, 1.5, 2.5, 3.5, 4.5, 6.5, 7.5, 9.85], [5.0, 4.0, 3.0, 2.0, 1.05, 1.05, 1.95, 2.05])
SH_ZT = T.pchip([0.95, 1.6, 2.5, 3.5, 5.5, 6.6, 7.6, 8.6, 9.85], [1.8, 3.6, 4.8, 5.3, 5.2, 4.6, 3.4, 2.4, 1.6])
# Across the plate: the outer dome lobe, a shallow groove (column 6), the inner ridge (column 7).
SH_F = T.pchip([0.0, 0.05, 0.14, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0], [0.1, 0.5, 0.82, 1.0, 0.97, 0.86, 0.93, 0.8, 0.55])
# The plate's rear and front ends round over in height (top and belly), not in plan.
SH_END = T.pchip([0.95, 1.25, 1.9, 8.8, 9.85], [0.3, 0.68, 1.0, 1.0, 0.7])
SH_ZB = -1.9  # the belly's depth at the inner edge

# Left side pod: rows 7.5-17.3 along x 3.6-3.9 (outer edge column 2, column 1 at row 14).
POD_Y = [7.5, 9.0, 10.0, 13.5, 14.5, 15.5, 16.5, 17.5, 18.8]
POD_HW = T.pchip(POD_Y, [1.3, 1.9, 1.95, 1.95, 2.55, 2.05, 1.6, 1.15, 0.4])
POD_CX = T.pchip(POD_Y, [3.9, 3.95, 3.95, 3.9, 3.55, 4.0, 4.5, 5.0, 5.6])
POD_HH = T.pchip(POD_Y, [1.6, 2.1, 2.2, 2.2, 2.1, 1.8, 1.5, 1.1, 0.5])
# Left claw: a fat grey crescent, its root under the pod, its tip curling in to the hull (rows 17-23).
CL_Y = [16.6, 17.5, 18.5, 19.5, 20.5, 21.5, 22.5, 23.25]
CL_CX = T.pchip(CL_Y, [2.9, 3.0, 3.5, 3.95, 4.0, 4.5, 5.0, 5.45])
CL_HW = T.pchip(CL_Y, [0.6, 1.0, 1.45, 1.95, 1.95, 1.5, 1.0, 0.3])
CL_HH = T.pchip(CL_Y, [0.6, 1.0, 1.25, 1.35, 1.3, 1.1, 0.8, 0.3])
CL_ZC = T.pchip(CL_Y, [1.2, 1.3, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8])
POD_ZC = 1.6


def build(bm):
    parts = {}
    # Hull.
    ys = merge_ys(frange(HULL_Y0, 13.0, 1.0), frange(13.0, 18.0, 0.84), [18.0, 18.5, 19.0, 19.5, 20.0],
                  frange(20.0, 26.0, 0.75), frange(26.0, HULL_Y1, 0.4))
    hf = loft(bm, ys, lambda y: section(CX, 0.0, HULL_HW(y), HULL_ZT(y), -HULL_ZB(y), 24, nt=HULL_NT), BODY)
    for f in hf:
        c = f.calc_center_median()
        if 17.95 < c.y < 20.05 and c.z > 0.5:
            f.material_index = DARK  # the transverse groove (rows 18-19)
    # Ridges: the twin ridges on the rear deck (columns 10/13, rows 13-17), the outer rails (columns
    # 6/17, rows 14-17), and the nose ribs (columns 7/16 and 9/14, rows 20-26).
    rails = []
    for x, y0, y1, r in ((10.5, 12.9, 18.0, 0.55), (6.75, 13.4, 18.0, 0.5), (7.6, 20.1, 26.2, 0.5),
                         (9.6, 20.1, 26.4, 0.45)):
        ys_r = frange(y0, y1, 0.75)
        last = len(ys_r) - 1
        dz = [-0.3, -0.05] + [0.1] * (last - 3) + [-0.05, -0.3]
        pts = [(x, y, hull_z(x, y) + dz[i]) for i, y in enumerate(ys_r)]
        hw = [0.0, 0.7 * r] + [r] * (last - 3) + [0.7 * r, 0.0]
        hh = [0.0, 0.6 * r] + [r * 0.85] * (last - 3) + [0.6 * r, 0.0]
        rails += tube(bm, pts, hw, hh, sides=7, mat=RIDGE)
    parts["hull"] = hf + rails + mirror(bm, rails)

    # Spine.
    ys = merge_ys(frange(0.0, 0.8, 0.2), frange(0.8, 8.2, 0.92), frange(8.2, 10.0, 0.3))
    sf = loft(bm, ys, lambda y: section(CX, 0.0, SP_HW(y), SP_ZT(y), -SP_ZB(y), 20, nt=SP_NT), BODY)
    for f in sf:
        c = f.calc_center_median()
        if c.y > 8.75 and c.z > 2.0:
            f.material_index = DARK  # its front face, in the shadow row 9
    # The dark slot (columns 11-12, rows 3-7) between two low lips.
    top = SP_ZT(5.0)
    sf += hull(bm, T.cbox(11.0, 13.0, 2.95, 7.1, top - 1.0, top + 0.03, 0.18, 0.06), SLOT)
    lips = tube(bm, [(10.62, 2.5, top - 0.05), (10.62, 3.0, top + 0.12), (10.62, 7.1, top + 0.12),
                     (10.62, 7.6, top - 0.05)], [0.0, 0.42, 0.42, 0.0], [0.0, 0.3, 0.3, 0.0], sides=8, mat=BODY)
    parts["spine"] = sf + lips + mirror(bm, lips)

    # Left shoulder plate, then mirrored.
    def sh_sec(y):
        xl = SH_XL(y)
        e = SH_END(y)
        zt = SH_ZT(y) * e
        w = SH_XR - xl
        K = 12
        topc = [(xl + w * i / K, zt * SH_F(i / K)) for i in range(K + 1)]
        # Down the outer edge and back under a rounded belly (deepest at the inner edge) to the spine.
        bot = [(xl - 0.02, 0.1 * zt)]
        for i in range(1, 7):
            u = i / 6
            bot.append((xl + w * (0.5 - 0.5 * math.cos(math.pi * u)), e * (-0.3 + (SH_ZB + 0.3) * math.sin(0.5 * math.pi * u) ** 0.8)))
        bot.append((SH_XR, 0.2 * zt))
        return list(reversed(topc)) + bot

    ys = merge_ys(frange(SH_Y0, 2.0, 0.3), frange(2.0, 7.0, 0.62), frange(7.0, SH_Y1, 0.48))
    shf = loft(bm, ys, sh_sec, BODY)
    for f in shf:
        c = f.calc_center_median()
        if c.z > -0.5 and (c.y > 7.0 or c.x > 8.35):
            f.material_index = DARK  # the shadow band (rows 7-9) and the gap to the spine (column 8)
    parts["shoulder"] = shf + mirror(bm, shf)

    # Left side pod, then mirrored.
    ys = merge_ys(frange(7.5, 9.0, 0.5), frange(9.0, 16.0, 0.9), frange(16.0, 18.8, 0.4))
    pf = loft(bm, ys, lambda y: section(POD_CX(y), POD_ZC, POD_HW(y), POD_HH(y), -1.6 * POD_HH(y) / 2.2, 14,
                                        nt=2.3), POD)
    # The grey claw under it, curling in along the flank (columns 2-5, rows 17-22).
    pf += loft(bm, merge_ys(frange(16.6, 23.25, 0.55)),
               lambda y: section(CL_CX(y), CL_ZC(y), CL_HW(y), CL_HH(y), -0.8 * CL_HH(y), 12, nt=2.2), CLAW)
    parts["pod"] = pf + mirror(bm, pf)

    # Gun bar across the middle (columns 6-17, rows 10-13), a collar and short muzzle at each end.
    BY, BZ = 11.8, 4.9
    gun = tube(bm, [(6.6, BY, BZ), (CX, BY, BZ), (2 * CX - 6.6, BY, BZ)], [1.7, 1.75, 1.7], [1.4, 1.45, 1.4],
               sides=14, mat=GREY)
    col = tube(bm, [(5.95, BY, BZ), (6.3, BY, BZ), (7.2, BY, BZ), (7.45, BY, BZ)],
               [1.55, 1.85, 1.85, 1.6], [1.3, 1.6, 1.6, 1.35], sides=14, mat=GREY_LT)
    col += tube(bm, [(6.6, 12.0, BZ - 0.5), (6.6, 13.6, BZ - 0.5), (6.6, 13.95, BZ - 0.5)], [0.62, 0.62, 0.45],
                [0.62, 0.62, 0.45], sides=10, mat=GREY_LT)
    parts["gun"] = gun + col + mirror(bm, col)

    # The red light: a domed lens in a dark housing at the bar's centre (columns 10-13, rows 10-13).
    hs = hull(bm, T.cbox(9.95, 14.05, 9.95, 13.95, 3.4, 6.05, 0.55, 0.35), HOUSING)
    lens = ellipsoid(bm, (CX, 11.4, 5.95), (1.05, 1.45, 0.75), RED)
    lens += ellipsoid(bm, (CX - 0.2, 11.15, 6.3), (0.55, 0.7, 0.5), RED_HOT, rings=6, sides=10)
    parts["light"] = hs + lens
    return parts


def to_blender(bm):
    m = Matrix(((1 / 12, 0, 0, -CX / 12), (0, -1 / 12, 0, 14 / 12), (0, 0, 1 / 12, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(56, metallic=0.3, roughness=0.32),  # BODY: steel-blue armour
        pal(53, metallic=0.3, roughness=0.36),  # POD: the darker side pods
        pal(58, metallic=0.3, roughness=0.3),  # RIDGE: raised ridges and ribs
        pal(52, metallic=0.4, roughness=0.5),  # DARK: shadow band, groove, the spine's front face
        pal(50, metallic=0.1, roughness=0.8),  # SLOT: the dark slot
        pal(7, metallic=0.75, roughness=0.32),  # GREY: gun bar
        pal(9, metallic=0.75, roughness=0.3),  # GREY_LT: collars and muzzles
        pal(5, metallic=0.7, roughness=0.36),  # CLAW: grey claws
        pal(3, metallic=0.5, roughness=0.5),  # HOUSING: the light's dark housing
        pal(117, metallic=1.0, roughness=0.9, emission_strength=1.0),  # RED: the lens (glow, D126/D173)
        pal(119, metallic=1.0, roughness=0.9, emission_strength=1.0),  # RED_HOT: its bright core
    ]
    # Polished steel: metallic 0.3 keeps the palette blue's value, and the F0 of IOR 2.0 through
    # Specular IOR Level (D176, as newsh0-229) gives the plates the sprite's white sheen (60-62).
    for i in STEEL:
        bsdf = next(n for n in mats[i].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = STEEL_SPEC
    bm = bmesh.new()
    build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    to_blender(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=3000)  # from the sealed copy (D90/D118)
    if '--no-cull' not in sys.argv:
        T.cull_hidden(obj, grid=3, ndirs=32)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"])
    print("tris", sum(len(p.vertices) - 2 for p in obj.data.polygons))


if __name__ == "__main__":
    main()
