"""The yoke mid-boss's lower claws with their ribbed red rods (3.6 FLEET): assembly-newshk-238 (newshk.shp 238 +
242, two pieces).

What it is: newshk-238 / -242 are the bottom ends of the grey yoke mid-boss's two C-shaped claw arms
(assembly-newshk-237, built in batch 1): pixel for pixel the yoke's claw pieces newshk-237 / -243 shifted 12 px in
(their boxes sit 12 px nearer the yoke's axis), with the claw tip completed where 237's box cut it off, and a
ribbed red rod reaching from each claw's jaw face towards the other claw (3 px short of meeting): the closed-claw
state of the yoke, the two rods an emitter/clamp pair.

So the claw is the yoke's own geometry (assembly-newshk-237.py: the same lofts, stations and materials, in the same
yoke coordinates: column edge e -> X = (e - 36) / 12, row edge r -> Y = (42 - r) / 12), and each piece is cut out of
the yoke frame at its box (238: yoke columns 12-35, rows 56-83; 242: columns 36-59), which is why the arm's lower
end is cut along the top/left box edges exactly where the yoke's arm pieces join on.
Added to the yoke's claw (left half; the right half is its mirror about yoke column 36, as in the sprite):
- the claw tip carried 1 px further in (to yoke column edge 25) where 238 draws it (237's box cut it off);
- a dark red lug and a red clamp collar on the jaw's end (238 columns 11-14, rows 15-17);
- the machined bracket box on the claw tip (238 columns 9-12, rows 19-24): a raised frame (palette 12, the
  sprite's median there) open to the north round a darker floor (5) (batch 1's 237/243 claws could take the same);
- a dark socket plate (238 column 13, rows 17-25) in which the rod's root flange sits;
- the rod: root flange (column 14, 9 px tall), then a 5 px core with four 7 px glowing ribs (columns 16, 18,
  20, 22), its end a chamfered rib; round in section (a pipe stays a pipe), glowing red (D126/D173).
Outline: the two halves are disjoint (common.outline_shell keeps only the largest island), so each half gets its
own shell from a sealed copy of that half, held inside (D90/D118), then cut with its piece.

Run: blender -b --factory-startup --python assembly-newshk-238_A.py -- [--pieces DIR] [--blend f.blend]
Exports one model per piece with common.export_sprite_model (enemies/<piece>.glb + spriteModels json).
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

sys.path.insert(0, str(WT / "tools"))
import sprite_mask  # noqa: E402

REF = WT / "reference" / "models"
NAME = "assembly-newshk-238"
YOKE = "assembly-newshk-237"
PX = 1 / 12
AXIS = 36.5  # yoke mirror axis (centre of yoke column 36 = assembly-238 column 24)
PIECES = ["newshk-238", "newshk-242"]
# Piece centres in yoke pixels relative to the yoke origin (36, 42): 238 = yoke edge (24, 70), 242 = (48, 70).
LAYOUT = [("newshk-238", -12, 28), ("newshk-242", 12, 28)]


def X(e):
    return (e - 36.0) * PX


def Y(r):
    return (42.0 - r) * PX


# --- the yoke's inner mask (D74), as assembly-newshk-237.py ------------------------------------------------------

def inner_spans():
    idx, colors = sprite_mask._load_assembly(YOKE, REF)
    inner = sprite_mask.masks(idx, colors)["inner"]
    out = {}
    for r, row in enumerate(inner):
        sp, c = [], 0
        while c < 37:
            if row[c]:
                s = c
                while c < 37 and row[c]:
                    c += 1
                sp.append((s, c))
            else:
                c += 1
        out[r] = sp
    return out


SPANS = inner_spans()


def mask_l(r):
    return SPANS[r][0][0]


def mask_r_first(r):
    return SPANS[r][0][1]


# --- materials -------------------------------------------------------------------------------------------------

def set_spec(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = level
            return


SLOTS = ["HULL", "ARM", "DEEP", "JOINT", "CLAW", "DARK", "RIB", "CORE", "FLANGE", "SOCKET", "FRAME"]
S = {k: i for i, k in enumerate(SLOTS)}


def materials(sprite, tag="nshk238"):
    def pal(i, t=tag, **kw):
        return common.palette_material(sprite, i, t, **kw)
    m = [
        pal(10, metallic=0.5, roughness=0.36),  # HULL (the yoke's light plates; unused on the claw, kept for slots)
        pal(9, metallic=0.5, roughness=0.38),  # ARM arm and claw tip (the yoke's)
        pal(3, metallic=0.3, roughness=0.6),  # DEEP
        pal(4, metallic=0.4, roughness=0.5),  # JOINT
        common.palette_material(sprite, 116, tag + "glow", metallic=1.0, roughness=0.75, emission_strength=1.0),
        pal(5, metallic=0.45, roughness=0.42),  # DARK lower arm (the yoke's)
        # The rod: glowing ribs (sprite median 117), a darker glowing core between them (113), the root flange (118).
        common.palette_material(sprite, 117, tag + "rib", metallic=1.0, roughness=0.6, emission_strength=1.0),
        common.palette_material(sprite, 113, tag + "core", metallic=1.0, roughness=0.55, emission_strength=1.0),
        common.palette_material(sprite, 118, tag + "flange", metallic=1.0, roughness=0.6, emission_strength=1.0),
        pal(2, metallic=0.4, roughness=0.55),  # SOCKET the dark plate the rod's root sits in
        pal(12, metallic=0.55, roughness=0.32),  # FRAME the machined bracket box on the claw tip (sprite median 12)
    ]
    for k in ("RIB", "FLANGE"):
        set_spec(m[S[k]], 0.8)
    return m


def merged_sprite(names):
    sp = common.load_sprite(WT, names[0])
    for n in names[1:]:
        sp["colors"].update(common.load_sprite(WT, n)["colors"])
    return sp


# --- geometry helpers (copied from assembly-newshk-237.py) -------------------------------------------------------

def prof(u0, u1, zb, zt, ct0, ct1, cb, crown=0.0, tilt=0.0, ntop=3, rnd=0):
    w = u1 - u0
    h = (zt - zb) / PX
    ct0 = max(0.05, min(ct0, 0.45 * w, 0.7 * h))
    ct1 = max(0.05, min(ct1, 0.45 * w, 0.7 * h))
    cb = max(0.05, min(cb, 0.45 * w, 0.3 * h))

    def top(u):
        s = (u - u0) / w * 2 - 1
        return zt + crown * (1 - s * s) + tilt * (s + 1) / 2

    a, b = u1 - ct1, u0 + ct0
    pts = [(u0 + cb, zb), (u1 - cb, zb), (u1, zb + cb * PX), (u1, top(u1) - ct1 * PX)]
    for k in range(1, rnd + 1):
        th = math.pi / 2 * k / (rnd + 1)
        u = a + ct1 * math.cos(th)
        pts.append((u, top(u) - ct1 * PX * (1 - math.sin(th))))
    for k in range(ntop + 1):
        u = a + (b - a) * k / ntop
        pts.append((u, top(u)))
    for k in range(rnd, 0, -1):
        th = math.pi / 2 * k / (rnd + 1)
        u = b - ct0 * math.cos(th)
        pts.append((u, top(u) - ct0 * PX * (1 - math.sin(th))))
    pts += [(u0, top(u0) - ct0 * PX), (u0, zb + cb * PX)]
    return pts


def loft(bm, axis, stations, mat, ntop=3, cap0=True, cap1=True, rnd=0):
    n0 = len(bm.faces)
    rings = []
    for st in stations:
        t, a0, a1, zb, zt, ct0, ct1, cb, cr, tl = st
        ring = []
        for u, z in prof(a0, a1, zb, zt, ct0, ct1, cb, cr, tl, ntop, rnd):
            co = (X(u), Y(t), z) if axis == "y" else (X(t), Y(u), z)
            ring.append(bm.verts.new(co))
        rings.append((t, ring))
    n = len(rings[0][1])
    for (t0, r0), (t1, r1) in zip(rings, rings[1:]):
        mi = mat((t0 + t1) / 2) if callable(mat) else mat
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = mi
            f.smooth = True
    for flag, (t, ring) in ((cap0, rings[0]), (cap1, rings[-1])):
        if flag:
            f = bm.faces.new(ring)
            f.material_index = mat(t) if callable(mat) else mat
            f.smooth = True
    return n0


def frange(a, b, step):
    n = max(1, int(round((b - a) / step)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def smooth(table, lo, hi, passes=2):
    ks = sorted(table)
    for _ in range(passes):
        v = dict(table)
        for i in range(1, len(ks) - 1):
            if lo < ks[i] < hi:
                table[ks[i]] = (v[ks[i - 1]] + 2 * v[ks[i]] + v[ks[i + 1]]) / 4
    return table


def curve(table):
    ks = sorted(table)
    return T.pchip(ks, [table[k] for k in ks])


def stations(t0, t1, a0, a1, zb, zt, ct0, ct1, cb, crown=0.0, tilt=0.0, step=0.5):
    f = lambda v, t: v(t) if callable(v) else v  # noqa: E731
    return [(t, f(a0, t), f(a1, t), f(zb, t), f(zt, t), f(ct0, t), f(ct1, t), f(cb, t), f(crown, t), f(tilt, t))
            for t in frange(t0, t1, step)]


def rod_x(bm, sections, row_c, zc, mat, sides=20):
    """A round rod along X (columns): sections (col_edge, ry_px, rz_units, slot) -> rings; band k takes the slot of
    its start section. Both ends capped."""
    n0 = len(bm.faces)
    rings = []
    for c, ry, rz, _ in sections:
        rings.append([bm.verts.new((X(c), Y(row_c) + ry * PX * math.cos(a), zc + rz * math.sin(a)))
                      for a in (2 * math.pi * (j + 0.5) / sides for j in range(sides))])
    for (r0, r1), sec in zip(zip(rings, rings[1:]), sections):
        for k in range(sides):
            j = (k + 1) % sides
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = sec[3]
            f.smooth = True
    f = bm.faces.new(list(reversed(rings[0])))
    f.material_index = sections[0][3]
    f = bm.faces.new(rings[-1])
    f.material_index = sections[-1][3]
    return n0


# --- the yoke's lower left claw (assembly-newshk-237.py build_left, rows 48 on) ----------------------------------

ARM_ZT, ARM_ZB = 0.27, -0.23
XS = {64: 15, 65: 15, 66: 15, 67: 16, 68: 16, 69: 17, 70: 17, 71: 18, 72: 18, 73: 19, 74: 19}
TIP_R = 25.0  # 238 draws the claw tip to yoke column 24 (237's box cut it at 23)


def arm_tables():
    xl, xr = {}, {}
    for r, v in zip(range(15, 21), (11, 10, 10, 10, 9, 8)):
        xl[r + 0.5] = v
        xr[r + 0.5] = 17.6
    xl[21.5], xr[21.5] = 6, 20
    for r, v in zip(range(22, 27), (19, 18, 17, 16, 15)):
        xl[r + 0.5], xr[r + 0.5] = 2, v
    for r in range(27, 65):
        xl[r + 0.5], xr[r + 0.5] = mask_l(r), mask_r_first(r)
    for r in range(65, 75):
        xl[r + 0.5], xr[r + 0.5] = mask_l(r), XS[r] + 0.5
    smooth(xl, 52.0, 80)
    smooth(xr, 27.6, 80)
    return curve(xl), curve(xr)


def arm_mat(t):
    if 52.9 <= t <= 58.6:
        return S["ARM"]
    if 58.6 < t <= 60.6:
        return S["JOINT"]
    if t > 60.6:
        return S["DARK"]
    return S["ARM"]


def arm_zt(t):
    z = ARM_ZT if t < 59 else 0.22 if t > 61 else ARM_ZT + (0.22 - ARM_ZT) * (t - 59) / 2
    if 58.8 < t < 60.4:
        z -= 0.025
    return z


ROD_ROW = 76.5  # rod axis: 238 rows 17-23 -> yoke 73-79, centre edge 76.5
ROD_Z = 0.03


def build_left(bm):
    xl, xr = arm_tables()
    # The arm from above the box (row 48) down to the lower arm (row 74.5): the yoke's loft, cut at the box later.
    loft(bm, "y", stations(48.0, 74.6, xl, xr, ARM_ZB, arm_zt, 1.6, 1.1, 0.9, crown=0.012, step=0.8), arm_mat)
    loft(bm, "y", stations(53.2, 58.5, lambda t: xl(t) + 0.9, lambda t: xr(t) - 0.5, ARM_ZT - 0.03,
                           ARM_ZT + 0.035, 0.7, 0.7, 0.2, crown=0.01), S["HULL"])
    # The claw tip (rows 71-81), carried to TIP_R where 238 draws it.
    tl, tr = {}, {}
    for r in range(71, 82):
        tl[r + 0.5] = mask_l(r)
        tr[r + 0.5] = XS[r] if r <= 74 else TIP_R
    smooth(tl, 71.6, 81.0)
    tl, tr = curve(tl), curve(tr)
    loft(bm, "y", stations(70.6, 81.8, tl, tr, ARM_ZB + 0.03, 0.285, 1.3, 1.1, 0.9, crown=0.01), S["ARM"])
    # The jaw pad (rows 64-74).
    jl, jr = {}, {}
    for r in range(64, 75):
        jl[r + 0.5] = XS[r] - 0.7
        jr[r + 0.5] = mask_r_first(r)
    smooth(jl, 64.6, 74.0)
    smooth(jr, 65.6, 74.0, passes=1)
    jl, jr = curve(jl), curve(jr)
    loft(bm, "y", stations(63.9, 75.0, jl, jr, -0.15, 0.2, 0.3, 1.0, 0.6, tilt=-0.07), S["CLAW"])

    # --- new on 238: lug, collar, socket and the ribbed rod ------------------------------------------------------
    # Lug on the jaw's end (238 cols 11-12, rows 15-17 -> yoke 23-25, 71-74): the claw's mount for the collar, dark
    # red as the sprite draws it there (113; column 10 stays the jaw pad's red, column 11 is the seam's ink).
    loft(bm, "y", stations(71.9, 74.6, 23.0, 25.2, ARM_ZB + 0.05, 0.24, 0.5, 0.4, 0.4, crown=0.008, step=0.5),
         S["CORE"])
    # Dark socket plate on the claw's inner face (238 col 13 rows 17-25 -> yoke 25, 73-82).
    loft(bm, "y", stations(72.9, 81.9, 24.6, 26.15, ARM_ZB + 0.06, 0.16, 0.3, 0.3, 0.3, step=0.6), S["SOCKET"])
    # The machined bracket box on the claw tip (238 cols 9-12, rows 19-24 -> yoke 21-25, 75-80): a raised frame,
    # open at its north end, round a darker floor (the sprite's light L/U frame round dark 4-8 pixels).
    loft(bm, "y", stations(75.1, 79.0, 22.0, 24.0, 0.1, 0.292, 0.15, 0.15, 0.2, step=3.9), S["DARK"])
    for c0, c1 in ((21.1, 22.0), (24.0, 24.9)):
        loft(bm, "y", stations(75.1, 79.95, c0, c1, 0.1, 0.318, 0.3, 0.3, 0.2, step=4.85), S["FRAME"], rnd=1)
    loft(bm, "x", stations(21.1, 24.9, 79.0, 79.95, 0.1, 0.318, 0.3, 0.45, 0.2, step=3.8), S["FRAME"], rnd=1)
    # Red clamp collar over the flange's top (238 cols 13-14, rows 16-17 -> yoke 25-26, 72-73).
    loft(bm, "y", stations(71.95, 74.2, 24.9, 27.95, 0.02, 0.3, 0.35, 0.35, 0.3, crown=0.01, step=0.4), S["CLAW"])
    # The rod: root flange (col 26, 9 px), core 5 px across, ribs 7 px at cols 28/30/32/34 (238 16/18/20/22).
    zr = 0.88  # a touch flatter than round: the arm is only 0.5 thick
    ff, rr, rc = 4.5, 3.5, 1.95
    sec = [(25.9, ff - 0.6, (ff - 0.6) * PX * zr, S["FLANGE"]), (26.05, ff, ff * PX * zr, S["FLANGE"]),
           (26.85, ff, ff * PX * zr, S["FLANGE"]), (27.0, ff - 0.7, (ff - 0.7) * PX * zr, S["FLANGE"]),
           (27.02, rc, rc * PX * zr, S["CORE"])]
    # Each rib a rounded ring (a half-round rim, not a flat disc): radius rc + (rr - rc) * (1 - (2u - 1)^2)^0.22
    # across its 1 px column u; the last rib is the rod's end, chamfered in.
    us = (0.0, 0.06, 0.16, 0.3, 0.5, 0.7, 0.84, 0.94, 1.0)
    for c in (28, 30, 32, 34):
        for u in us:
            if c == 34 and u > 0.5:
                break
            r = rc + (rr - rc) * max(0.0, 1 - (2 * u - 1) ** 2) ** 0.22
            sec.append((c + u, r, r * PX * zr, S["RIB"] if 0 < u < 1 else S["CORE"]))
        if c == 34:
            sec += [(34.8, rr - 0.25, (rr - 0.25) * PX * zr, S["RIB"]), (34.95, rr - 0.8, (rr - 0.8) * PX * zr, S["RIB"]),
                    (35.0, rr - 1.6, (rr - 1.6) * PX * zr, S["RIB"])]
    rod_x(bm, sec, ROD_ROW, ROD_Z, S["CORE"])


def mirror_bm(bm):
    orig = list(bm.verts)
    dup = bmesh.ops.duplicate(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces))
    ax = 2 * X(AXIS)
    for v in dup["geom"]:
        if isinstance(v, bmesh.types.BMVert):
            v.co.x = ax - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[f for f in dup["geom"] if isinstance(f, bmesh.types.BMFace)])
    bmesh.ops.delete(bm, geom=orig, context="VERTS")


def to_object(name, bm, mats, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    try:
        me.set_sharp_from_angle(angle=math.radians(38))
    except AttributeError:
        pass
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def half(sprite, coll, right):
    bm = bmesh.new()
    build_left(bm)
    if right:
        mirror_bm(bm)
    return to_object(f"{NAME}-{'R' if right else 'L'}", bm, materials(sprite), coll)


# --- assembly splitting (as assembly-newshk-237.py: cut faces filled with the neighbouring material) ------------

def split_pieces(obj, layout, coll, cap=True):
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        caps = []
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            cut = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                         plane_no=no, clear_outer=True)
            edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge) and e.is_valid]
            if edges and cap:
                caps += bmesh.ops.holes_fill(bm, edges=edges, sides=0)["faces"]
        for f in caps:
            if not f.is_valid:
                continue
            f.smooth = False
            near = [g.material_index for e in f.edges for g in e.link_faces if g is not f and g not in caps]
            if near:
                f.material_index = max(set(near), key=near.count)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        out[name] = ob
    return out


def shell_of(coll, obj, faces):
    src = obj.copy()
    src.data = obj.data.copy()
    coll.objects.link(src)
    sh = common.outline_shell(src, coll, faces=faces, inside=0.004)
    bpy.data.objects.remove(src)
    return sh


def tri(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = merged_sprite(PIECES)
    coll = common.reset_collection("nshk238A")
    halves = {"newshk-238": half(sprite, coll, False), "newshk-242": half(sprite, coll, True)}
    parts, shells = {}, {}
    for name, cx, cy in LAYOUT:
        ob = halves[name]
        sh = shell_of(coll, ob, 1600)
        parts.update(split_pieces(ob, [(name, cx, cy)], coll))
        shells.update(split_pieces(sh, [(name, cx, cy)], coll, cap=False))
        for o in (ob, sh):
            o.hide_render = True
            o.hide_set(True)
    for name, ob in parts.items():
        ob.location = (0, 0, 0)
        sh = shells[name]
        sh.name = f"{name}_outline"
        sh.data.materials.clear()
        sh.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
        sh["tyrian_outline"] = True
        sh.location = (0, 0, 0)
        assert len(sh.data.polygons) > 0, f"{name}: empty outline shell"
    report = {n: tri(o) for n, o in parts.items()}
    report.update({n + "_outline": tri(o) for n, o in shells.items()})
    print("TRIS", report)
    export = list(parts.values()) + list(shells.values())
    for name in PIECES:
        common.export_sprite_model(WT, [parts[name], shells[name]], f"enemies/{name}", common.load_sprite(WT, name)["sprites"])
    if "--pieces" in argv:  # per-piece glbs for an in-game check through a scratch dev-server overlay
        d = Path(argv[argv.index("--pieces") + 1])
        for name in PIECES:
            common.export_glb([parts[name], shells[name]], d / f"{name}.glb")
    if "--blend" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=argv[argv.index("--blend") + 1])


if __name__ == "__main__":
    main()
