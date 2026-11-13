"""Sensor pod released by the FLEET boss's hatches (newshk.shp frame 245, 24 x 28 px).

WHAT IT IS: a closed, flying drone pod. The FLEET boss's newsho-191/193 hatches launch it
(launchedBy 737/738) and it drifts down the screen at 2 px/tick (armour 20): a free-flying
octagonal saucer, not a ground emplacement. Built round its own body: an octagonal hull with a
vertical girdle, a chamfered upper bevel to a flat deck and a shallow lower chamfer to a plain
bottom plate (underside: closed, no detail).

Reading the sprite (24 x 28; ink ring top/bottom 100%, the flank columns rows 9-18 are no ink, so
the hull reaches the sprite's left/right edges there and the inner edge of the ink elsewhere):
- Hull: an octagon, flats top/bottom (rows 2-25 inside the ink), flanks full width rows 9-18,
  diagonals through the stair steps. The darker 2-3 px rim is the bevel in shade (lighting).
- A sunken bay across the middle (ink rows 9 and 18, columns 4-19) holding a red DRUM lying along
  X: a barrel with domed ends (its outline narrows at rows 10/17), orange bands round it at
  columns 8 and 15 and a red-orange centre band at columns 11-12.
- A dark SOCKET collar (rows 12-15, columns 10-13) on the drum's crest with a blue LENS (2 x 2 px).
- The drum's AXLE runs out to the hull edge in slots (rows 13-14, columns 0-3 / 20-23), between
  light bearing cheeks (rows 12 and 15).
- Fore and aft: a raised VENT HOUSING (columns 8-15, rows 3-8 / 19-24): light frame (outer bar and
  side rails), a dark intake slot (row 5 / 22) and a louvred grille.

Colours (median per region, darkest shading and highlights left out): deck 10, bevel 9, housing
frame 12, grille 9, slot 4, bay 2, drum 115, side bands 121, centre band 118, socket 112, lens 149,
bearing cheeks 13, axle 4.

Coordinates: sprite px, X = column edge - 12 (east), Y = 14 - row edge (north), Z up from the
bottom plate; 1 px = 1/12 unit.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshk-245.py
Exports the model + its outline shell to public/models/enemies/newshk-245.glb.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshk-245"
MODEL = f"enemies/{NAME}"
PX = 1 / 12

# ---- dimensions (px) -----------------------------------------------------------------------------
# Hull octagon (outer, at the girdle): x + y = DIAG on the diagonals.
HX, HY, DIAG = 12.0, 12.0, 16.75
# Hull profile: (z, inset, corner fillet radius)
HULL = [(0.0, 4.6, 2.2), (0.55, 3.1, 2.0), (1.5, 1.35, 1.8), (2.5, 0.35, 1.6), (3.1, 0.0, 1.5),
        (4.1, 0.0, 1.5), (4.55, 0.3, 1.45), (5.55, 2.15, 1.25), (5.9, 2.7, 1.0)]
DECK = 5.9
# Bay (sunken pit) across the middle
BAY = [(-6.2, 5.05), (6.2, 5.05), (8.4, 2.6), (8.4, -2.6), (6.2, -5.05), (-6.2, -5.05), (-8.4, -2.6), (-8.4, 2.6)]
BAY_FLOOR = 1.2
# Drum: barrel along X, axis at ZC; profile (x, r)
ZC = 5.35
DRUM = [(0.0, 3.95), (4.6, 3.95), (5.6, 3.75), (6.5, 3.25), (7.25, 2.45), (7.8, 1.55), (8.05, 0.9)]
BANDS = [(-3.5, 1.0, 4.2, "side"), (3.5, 1.0, 4.2, "side"), (0.0, 2.0, 4.12, "centre")]
# Socket collar + lens on the crest
SOCK_R, SOCK_TOP = 2.0, ZC + 4.25
LENS_R, LENS_H = 1.15, 0.75
# Axle slot (rows 13-14) and axle
SLOT_Y, SLOT_FLOOR = 1.0, 4.35
AXLE_R = 0.85
# Vent housings (columns 8-15; rows 3/4-8)
VH_X, VH_Y0, VH_Y1, VH_TOP = 4.1, 5.15, 10.35, 7.25

# palette slots
(M_DECK, M_BEVEL, M_FRAME, M_GRILLE, M_SLOT, M_BAY, M_DRUM, M_BAND, M_CBAND, M_SOCK, M_LENS,
 M_CHEEK, M_AXLE, M_FIN) = range(14)
PAL = {M_DECK: 10, M_BEVEL: 9, M_FRAME: 12, M_GRILLE: 9, M_SLOT: 4, M_BAY: 2, M_DRUM: 115,
       M_BAND: 121, M_CBAND: 118, M_SOCK: 112, M_LENS: 149, M_CHEEK: 13, M_AXLE: 4, M_FIN: 10}


def P(x, y, z):
    return Vector((x * PX, y * PX, z * PX))


# ---- geometry helpers ----------------------------------------------------------------------------
def octagon(inset):
    """The hull octagon shrunk by `inset` px (CCW from above): 8 corners."""
    hx, hy, d = HX - inset, HY - inset, DIAG - inset * math.sqrt(2)
    return [(d - hy, hy), (-(d - hy), hy), (-hx, d - hx), (-hx, -(d - hx)),
            (-(d - hy), -hy), (d - hy, -hy), (hx, -(d - hx)), (hx, d - hx)]


def fillet(poly, rad, n=3):
    """Round each corner of a convex polygon with an arc of `rad` px, n points per corner."""
    out = []
    m = len(poly)
    for i in range(m):
        p = Vector(poly[i])
        a = (Vector(poly[i - 1]) - p).normalized()
        b = (Vector(poly[(i + 1) % m]) - p).normalized()
        ang = a.angle(b)
        t = rad / math.tan(ang / 2)
        pa, pb = p + a * t, p + b * t
        bis = (a + b).normalized()
        c = p + bis * (rad / math.sin(ang / 2))
        a0 = math.atan2(pa.y - c.y, pa.x - c.x)
        a1 = math.atan2(pb.y - c.y, pb.x - c.x)
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for k in range(n):
            s = a0 + da * k / (n - 1)
            out.append((c.x + rad * math.cos(s), c.y + rad * math.sin(s)))
    return out


def loft_rings(bm, rings, mat, cap_bottom=True, cap_top=True, top_mat=None):
    """rings: list of [(x, y, z) px] of equal length, bottom to top."""
    vs = [[bm.verts.new(P(*p)) for p in r] for r in rings]
    n = len(rings[0])
    for r0, r1 in zip(vs, vs[1:]):
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mat
    if cap_bottom:
        bm.faces.new(list(reversed(vs[0]))).material_index = mat
    if cap_top:
        bm.faces.new(vs[-1]).material_index = mat if top_mat is None else top_mat
    return vs


def prism(bm, poly, z0, z1, mat, top_mat=None):
    loft_rings(bm, [[(x, y, z0) for x, y in poly], [(x, y, z1) for x, y in poly]], mat, top_mat=top_mat)


def cbox(bm, x0, y0, x1, y1, z0, z1, mat, ch=0.18):
    """A box with chamfered edges (ch px)."""
    tmp = bmesh.new()
    prism(tmp, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat)
    if ch > 0:
        bmesh.ops.bevel(tmp, geom=tmp.edges[:], offset=ch * PX, segments=1, affect="EDGES", profile=0.5)
    me = bpy.data.meshes.new("tmp")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def lathe_x(bm, prof, zc, mat, seg=28, yc=0.0, close=True):
    """A solid of revolution about the X axis through (yc, zc): prof [(x, r)], ascending x."""
    rings = []
    for x, r in prof:
        rings.append([bm.verts.new(P(x, yc + r * math.cos(2 * math.pi * k / seg), zc + r * math.sin(2 * math.pi * k / seg)))
                      for k in range(seg)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(seg):
            j = (k + 1) % seg
            bm.faces.new((r0[k], r1[k], r1[j], r0[j])).material_index = mat
    if close:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat
        bm.faces.new(rings[-1]).material_index = mat
    return rings


def cyl_z(bm, x, y, r, z0, z1, mat, seg=20, top_mat=None):
    poly = [(x + r * math.cos(2 * math.pi * k / seg), y + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
    prism(bm, poly, z0, z1, mat, top_mat=top_mat)


def dome_z(bm, x, y, z, r, h, mat, seg=20, rings=5):
    layers = []
    for k in range(rings):
        a = math.pi / 2 * k / rings
        layers.append([bm.verts.new(P(x + r * math.cos(a) * math.cos(t), y + r * math.cos(a) * math.sin(t), z + h * math.sin(a)))
                       for t in (2 * math.pi * i / seg for i in range(seg))])
    top = bm.verts.new(P(x, y, z + h))
    for r0, r1 in zip(layers, layers[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat
    for i in range(seg):
        bm.faces.new((layers[-1][i], layers[-1][(i + 1) % seg], top)).material_index = mat
    bm.faces.new(list(reversed(layers[0]))).material_index = mat


def obj_from_bm(bm, name, mats, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def boolean(target, cutter, op="DIFFERENCE"):
    mod = target.modifiers.new("b", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    dg = bpy.context.evaluated_depsgraph_get()
    ev = target.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    target.modifiers.clear()
    old = target.data
    target.data = me
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter, do_unlink=True)


# ---- build ---------------------------------------------------------------------------------------
def hull(mats, coll):
    bm = bmesh.new()
    rings = [[(x, y, z) for x, y in fillet(octagon(ins), rad)] for z, ins, rad in HULL]
    loft_rings(bm, rings, M_BEVEL, top_mat=M_DECK)
    h = obj_from_bm(bm, "hull", mats, coll)
    # sunken bay
    bm = bmesh.new()
    prism(bm, fillet(BAY, 0.8), BAY_FLOOR, 20, M_BAY)
    boolean(h, obj_from_bm(bm, "c_bay", mats, coll))
    # axle slots out to the rim
    for s in (1, -1):
        bm = bmesh.new()
        prism(bm, [(s * 7.0, -SLOT_Y), (s * 13.0, -SLOT_Y), (s * 13.0, SLOT_Y), (s * 7.0, SLOT_Y)][:: s], SLOT_FLOOR, 20, M_BAY)
        boolean(h, obj_from_bm(bm, "c_slot", mats, coll))
    # girdle seam: a shallow groove round the vertical band
    bm = bmesh.new()
    outer = [(x * 1.2, y * 1.2) for x, y in fillet(octagon(-1.0), 1.5)]
    inner = fillet(octagon(0.28), 1.5)
    vs_o0 = [bm.verts.new(P(x, y, 3.5)) for x, y in outer]
    vs_o1 = [bm.verts.new(P(x, y, 3.72)) for x, y in outer]
    vs_i0 = [bm.verts.new(P(x, y, 3.5)) for x, y in inner]
    vs_i1 = [bm.verts.new(P(x, y, 3.72)) for x, y in inner]
    n = len(outer)
    for k in range(n):
        j = (k + 1) % n
        bm.faces.new((vs_o0[k], vs_o0[j], vs_o1[j], vs_o1[k]))
        bm.faces.new((vs_i0[j], vs_i0[k], vs_i1[k], vs_i1[j]))
        bm.faces.new((vs_o1[k], vs_o1[j], vs_i1[j], vs_i1[k]))
        bm.faces.new((vs_i0[k], vs_i0[j], vs_o0[j], vs_o0[k]))
    boolean(h, obj_from_bm(bm, "c_seam", mats, coll))
    # deck bolt recesses (rows 6 / 21, columns 6 / 17) and corner panel seams on the bevel
    for sx in (1, -1):
        for sy in (1, -1):
            bm = bmesh.new()
            cyl_z(bm, sx * 5.5, sy * 7.5, 0.45, DECK - 0.35, DECK + 2, M_SLOT, seg=10)
            boolean(h, obj_from_bm(bm, "c_bolt", mats, coll))
            # radial seam across the diagonal bevel: 0.3 px wide, 0.25 px deep, following the bevel
            c = Vector((sx * 9.0, sy * 9.0))
            dirv = Vector((sx, sy)).normalized()
            nrm = Vector((-dirv.y, dirv.x)) * 0.15
            a, b = c - dirv * 2.6, c + dirv * 2.2
            bm = bmesh.new()
            vb, vt = [], []
            for q in (a - nrm, b - nrm, b + nrm, a + nrm):
                ins = (DIAG - abs(q.x) - abs(q.y)) / math.sqrt(2)
                z = 4.55 + (ins - 0.3) / (2.15 - 0.3) * 1.0 - 0.25
                vb.append(bm.verts.new(P(q.x, q.y, z)))
                vt.append(bm.verts.new(P(q.x, q.y, 20)))
            bm.faces.new(vb)
            bm.faces.new(vt)
            for k in range(4):
                j = (k + 1) % 4
                bm.faces.new((vb[k], vb[j], vt[j], vt[k]))
            boolean(h, obj_from_bm(bm, "c_seamd", mats, coll))
    # materials by region after the cuts
    me = h.data
    for f in me.polygons:
        c = f.center / PX
        if abs(c.x) < 8.6 and abs(c.y) < 5.3 and BAY_FLOOR - 0.1 < c.z < DECK - 0.05:
            f.material_index = M_BAY
        elif abs(c.y) < SLOT_Y + 0.05 and abs(c.x) > 7.0 and c.z > SLOT_FLOOR - 0.05 and c.z < DECK - 0.02:
            f.material_index = M_BAY
        elif 3.4 < c.z < 3.8 and f.normal.z < 0.9 and abs(f.normal.z) < 0.9 and (abs(c.x) > 10.5 or abs(c.y) > 10.5 or abs(c.x) + abs(c.y) > 15.5):
            f.material_index = M_SLOT
        elif f.normal.z > 0.99 and c.z > DECK - 0.4 and c.z < DECK - 0.2:
            f.material_index = M_SLOT
    return h


def details(mats, coll):
    bm = bmesh.new()
    # drum barrel
    prof = [(-x, r) for x, r in reversed(DRUM)] + DRUM[1:]
    lathe_x(bm, prof, ZC, M_DRUM, seg=28)
    # bands: raised rings with chamfered edges
    for xc, w, r, kind in BANDS:
        m = M_BAND if kind == "side" else M_CBAND
        h = w / 2
        lathe_x(bm, [(xc - h, 3.85), (xc - h + 0.12, r - 0.08), (xc - h + 0.25, r), (xc + h - 0.25, r),
                     (xc + h - 0.12, r - 0.08), (xc + h, 3.85)], ZC, m, seg=28)
    # end caps: a machined hub at each barrel end
    for s in (1, -1):
        lathe_x(bm, sorted([(s * 7.9, 1.35), (s * 8.35, 1.2), (s * 8.55, 0.9)]), ZC, M_AXLE, seg=16)
    # axle out to the rim and a hub nut in the slot mouth
    for s in (1, -1):
        lathe_x(bm, sorted([(s * 8.3, AXLE_R), (s * 11.2, AXLE_R)]), ZC, M_AXLE, seg=14)
        lathe_x(bm, sorted([(s * 10.9, 1.0), (s * 11.65, 0.95)]), ZC, M_BEVEL, seg=14)
        # bearing cheeks either side of the slot (rows 12 and 15), light
        for sy in (1, -1):
            y0, y1 = sorted((sy * (SLOT_Y + 0.02), sy * (SLOT_Y + 1.0)))
            x0, x1 = sorted((s * 8.4, s * 11.45))
            cbox(bm, x0, y0, x1, y1, 3.9, DECK + 0.65, M_CHEEK, ch=0.2)
    # socket collar and lens on the crest
    cyl_z(bm, 0, 0, SOCK_R, ZC + 2.6, SOCK_TOP, M_SOCK, seg=24)
    cyl_z(bm, 0, 0, SOCK_R - 0.3, SOCK_TOP - 0.01, SOCK_TOP + 0.18, M_SOCK, seg=24)
    dome_z(bm, 0, 0, SOCK_TOP - 0.25, LENS_R, LENS_H, M_LENS, seg=20)
    # vent housings fore and aft
    for s in (1, -1):
        def yb(a, b):
            return sorted((s * a, s * b))
        ya, yb_ = yb(VH_Y1 - 1.25, VH_Y1)
        cbox(bm, -VH_X, ya, VH_X, yb_, 4.0, VH_TOP, M_FRAME, ch=0.3)  # outer bar (row 4)
        for sx in (1, -1):
            x0, x1 = sorted((sx * (VH_X - 1.05), sx * VH_X))
            ya, yb_ = yb(VH_Y0, VH_Y1 - 0.6)
            cbox(bm, x0, ya, x1, yb_, 4.0, VH_TOP, M_FRAME, ch=0.3)  # side rails (cols 8, 15)
        ya, yb_ = yb(VH_Y0 + 0.1, VH_Y1 - 1.2)
        cbox(bm, -VH_X + 1.0, ya, VH_X - 1.0, yb_, 4.0, DECK + 0.45, M_SLOT, ch=0.0)  # recess floor
        ya, yb_ = yb(VH_Y0, 7.95)
        cbox(bm, -VH_X + 1.0, ya, VH_X - 1.0, yb_, 4.0, VH_TOP - 0.55, M_GRILLE, ch=0.2)  # grille block
        for yc in (6.15, 7.35):
            ya, yb_ = yb(yc - 0.28, yc + 0.28)
            cbox(bm, -VH_X + 1.05, ya, VH_X - 1.05, yb_, VH_TOP - 0.6, VH_TOP - 0.2, M_FIN, ch=0.12)  # louvres
        ya, yb_ = yb(VH_Y0, 7.95)
        cbox(bm, -0.45, ya, 0.45, yb_, VH_TOP - 0.6, VH_TOP - 0.15, M_FRAME, ch=0.12)  # centre rib (col 12)
    return obj_from_bm(bm, "details", mats, coll)


def materials(sprite):
    def pal(slot, metallic, rough, emis=0.0, spec=None):
        m = common.palette_material(sprite, PAL[slot], NAME, metallic=metallic, roughness=rough, emission_strength=emis)
        if spec is not None:
            b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            for key in ("Specular IOR Level", "Specular"):
                if key in b.inputs:
                    b.inputs[key].default_value = spec
                    break
        return m
    out = [None] * len(PAL)
    out[M_DECK] = pal(M_DECK, 0.45, 0.42)
    out[M_BEVEL] = pal(M_BEVEL, 0.45, 0.42)
    out[M_FRAME] = pal(M_FRAME, 0.5, 0.36)
    out[M_GRILLE] = pal(M_GRILLE, 0.45, 0.5)
    out[M_SLOT] = pal(M_SLOT, 0.3, 0.6)
    out[M_BAY] = pal(M_BAY, 0.2, 0.75)
    out[M_DRUM] = pal(M_DRUM, 0.4, 0.4)
    out[M_BAND] = pal(M_BAND, 0.45, 0.32)
    out[M_CBAND] = pal(M_CBAND, 0.45, 0.32)
    out[M_SOCK] = pal(M_SOCK, 0.3, 0.45)
    out[M_LENS] = pal(M_LENS, 1.0, 0.3, emis=1.2)
    out[M_CHEEK] = pal(M_CHEEK, 0.5, 0.36)
    out[M_AXLE] = pal(M_AXLE, 0.6, 0.35)
    out[M_FIN] = pal(M_FIN, 0.45, 0.42)
    return out


def tris(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    h = hull(mats, coll)
    d = details(mats, coll)
    # join into one object
    bm = bmesh.new()
    bm.from_mesh(h.data)
    bm.from_mesh(d.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bpy.data.objects.remove(h, do_unlink=True)
    bpy.data.objects.remove(d, do_unlink=True)
    obj = obj_from_bm(bm, NAME, mats, coll)
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(38))
    # outline shell from the sealed whole (before any culling), held inside the hull
    bpy.context.view_layer.update()
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=2500, smooth=6, inside=0.004)
    shell.name = f"{NAME}_outline"
    stats = {"model": tris(obj), "shell": tris(shell)}
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])
    print("STATS", json.dumps(stats))


if __name__ == "__main__":
    main()
