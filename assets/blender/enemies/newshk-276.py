"""Octagonal capsule pod with a glowing core (3.6 FLEET): newshk-276 (newshk.shp frame 276, type 702, a swooping
flying pod that fires).

What it is: the yoke mid-boss's pod (assembly-newshk-237.py: the octagonal hull with the louvre housing) as a
free-flying capsule, symmetric end to end: a fat grey barrel lying up the screen (round across, so the sprite
shades it in stripes, bright on the lit left, dark on the right), its ends chamfered so it reads as an octagon from
above, with a girth groove round its middle (rows 13-14). A raised louvre housing runs down the centre (columns
9-16): plain plates at the ends, grilles of three slats each side of the core, and across the groove the core
itself, a glowing red-orange drum in a dark red rim. At each end a narrower lid closes the barrel, and a loop
handle (two posts and a thin bar, the sprite's rows 0-2) stands off it.

Built in sprite coordinates (column edge e -> X = (e - 12) / 12, row edge r -> Y = (14 - r) / 12). The hull is a
loft of rounded sections whose plan extents come from the sprite's inner mask (D74), interpolated with pchip; the
north half's parts are built once and mirrored about row edge 14 (the sprite is symmetric end to end), the
housing and core centred on column edge 12.5 where the sprite draws them. Sheen and the barrel's stripes are
lighting (rule 2). Colours are the sprite's per-region medians: hull 9, groove 6, lids 9, handles 6, housing 11,
grille bed 5, slats 11, core rim 113, core 121 (glow: metallic 1, rough, D126/D173). One outline shell.

Self-contained (lib_b045 is no longer used).
Run: tools/build-models.sh -j 2 assets/blender/enemies/newshk-276.py
"""

import math
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
PX = 1 / 12
NAME = "newshk-276"
W, H = 24, 28

# --- geometry helpers (copied from assembly-newshk-237.py, the yoke; lib_b045 is no longer used) ----------------
# Coordinates: sprite column edge e -> X = (e - W / 2) / 12, row edge r -> Y = (H / 2 - r) / 12 (sprite up = +Y).

def X(e):
    return (e - W / 2) * PX


def Y(r):
    return (H / 2 - r) * PX


def set_spec(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = level
            return


def inner_rows():
    """The sprite's inner mask (D74) as {row: [(c0, c1), ...]} runs of column edges."""
    idx, colors = sprite_mask.load(NAME, ref=REF)
    inner = sprite_mask.masks(idx, colors)["inner"]
    out = {}
    for r, row in enumerate(inner):
        sp, c = [], 0
        while c < len(row):
            if row[c]:
                s = c
                while c < len(row) and row[c]:
                    c += 1
                sp.append((s, c))
            else:
                c += 1
        out[r] = sp
    return out


def prof(u0, u1, zb, zt, ct0, ct1, cb, crown=0.0, tilt=0.0, ntop=3, rnd=0):
    """A chamfered section across u (pixel edges) between zb and zt (units): flat chamfered bottom, vertical
    sides (so the top view is exactly u0..u1), top chamfers ct0 / ct1 (px), a crowned top tilted by `tilt`.
    rnd > 0 rounds each top chamfer into a quarter arc of rnd + 1 segments."""
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


def _faces(bm, mat):
    def done(n0, smooth=True):
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n0:]:
            f.material_index = mat if not callable(mat) else mat(f)
            f.smooth = smooth
    return done


def loft(bm, axis, stations, mat, ntop=3, cap0=True, cap1=True, rnd=0):
    """Stations (t, a0, a1, zb, zt, ct0, ct1, cb, crown, tilt): axis 'y' runs down the rows (t = row edge,
    a0..a1 column edges), axis 'x' along the columns (t = column edge, a0..a1 row edges). `mat` is a slot
    or a function of the band's middle t."""
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
    """[1, 2, 1] / 4 smoothing of the values at keys strictly inside (lo, hi): takes the pixel staircase out
    of a diagonal edge."""
    ks = sorted(table)
    for _ in range(passes):
        v = dict(table)
        for i in range(1, len(ks) - 1):
            if lo < ks[i] < hi:
                table[ks[i]] = (v[ks[i - 1]] + 2 * v[ks[i]] + v[ks[i + 1]]) / 4
    return table


def curve(table):
    """pchip through {t: value} (t at row/col centres)."""
    ks = sorted(table)
    return T.pchip(ks, [table[k] for k in ks])


def stations(t0, t1, a0, a1, zb, zt, ct0, ct1, cb, crown=0.0, tilt=0.0, step=0.5):
    """Sample callables (or constants) of t into loft stations."""
    f = lambda v, t: v(t) if callable(v) else v  # noqa: E731
    return [(t, f(a0, t), f(a1, t), f(zb, t), f(zt, t), f(ct0, t), f(ct1, t), f(cb, t), f(crown, t), f(tilt, t))
            for t in frange(t0, t1, step)]


def catmull(pts, step):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(2, int((p2 - p1).length / step))
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def tube(bm, path, rpx, rz, mat, sides=10, round0=True, round1=True, step=0.12):
    """A pipe along (col, row, z) points: an elliptical section rpx px wide-radius by rz units high, its ends
    domed (round0/round1) or flat."""
    n0 = len(bm.faces)
    P = catmull([Vector((X(c), Y(r), z)) for c, r, z in path], step)
    up = Vector((0, 0, 1))
    frames = []
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        side = t.cross(up)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        nrm = side.cross(t).normalized()
        frames.append((p, t, side, nrm))
    rr = rpx * PX
    seq = []
    if round0:
        p, t, sd, nm = frames[0]
        for d in (1.0, 0.92, 0.7, 0.4):
            seq.append((p - t * (d * min(rr, rz)), sd, nm, math.sqrt(max(0.0, 1 - d * d)) + (0.05 if d == 1.0 else 0)))
    for p, t, sd, nm in frames:
        seq.append((p, sd, nm, 1.0))
    if round1:
        p, t, sd, nm = frames[-1]
        for d in (0.4, 0.7, 0.92, 1.0):
            seq.append((p + t * (d * min(rr, rz)), sd, nm, math.sqrt(max(0.0, 1 - d * d)) + (0.05 if d == 1.0 else 0)))
    rings = []
    for p, sd, nm, k in seq:
        rings.append([bm.verts.new(p + sd * (rr * k * math.cos(a)) + nm * (rz * k * math.sin(a)))
                      for a in (2 * math.pi * (j + 0.5) / sides for j in range(sides))])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    _faces(bm, mat)(n0)


def ellipsoid(bm, col, row, z, rxp, ryp, rz, mat, seg=24, rings=14, zcut=None):
    """An ellipsoid centred on (col, row) edges at height z; zcut flattens everything below that height."""
    n0 = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((X(col) + v.co.x * rxp * PX, Y(row) + v.co.y * ryp * PX, z + v.co.z * rz))
        if zcut is not None and v.co.z < zcut:
            v.co.z = zcut
    _faces(bm, mat)(n0)


def mirror_x(bm, n_verts0, n_faces0, axis):
    """Mirror the geometry built after (n_verts0, n_faces0) about column edge `axis` (a copy is added)."""
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    faces = bm.faces[n_faces0:]
    dup = bmesh.ops.duplicate(bm, geom=list(bm.verts[n_verts0:]) + list(faces))
    ax = 2 * X(axis)
    for v in dup["geom"]:
        if isinstance(v, bmesh.types.BMVert):
            v.co.x = ax - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[f for f in dup["geom"] if isinstance(f, bmesh.types.BMFace)])


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


def shell_of(coll, obj, faces):
    """D51/D90/D118 outline shell from a sealed copy, held inside the model. common.outline_shell keeps only the
    largest loose island, so a model of disjoint parts passes each part as its own object."""
    src = obj.copy()
    src.data = obj.data.copy()
    coll.objects.link(src)
    sh = common.outline_shell(src, coll, faces=faces, inside=0.004)
    bpy.data.objects.remove(src)
    return sh


def join(objs, name):
    """Merge meshes (same material list) into one new object, without operators; the inputs are removed."""
    bm = bmesh.new()
    for o in objs:
        me = o.data.copy()
        me.transform(o.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in objs[0].data.materials:
        me.materials.append(m)
    coll = objs[0].users_collection[0]
    for o in objs:
        bpy.data.objects.remove(o)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def finish(parts, sprite, coll, shell_faces):
    """`parts`: one object per disjoint group of the model. Each gets its own outline shell; the groups and the
    shells are joined into the model and its `<name>_outline` node and exported (enemies/<name>.glb)."""
    shells = [shell_of(coll, p, shell_faces) for p in parts]
    for s in shells:
        assert len(s.data.polygons) > 0, f"{NAME}: empty outline shell"
    model = join(parts, NAME) if len(parts) > 1 else parts[0]
    model.name = NAME
    shell = join(shells, NAME + "_outline") if len(shells) > 1 else shells[0]
    shell.name = NAME + "_outline"
    shell.data.materials.clear()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    tri = lambda o: sum(len(p.vertices) - 2 for p in o.data.polygons)  # noqa: E731
    print("TRIS", NAME, tri(model), "shell", tri(shell), "groups", len(parts))
    common.export_sprite_model(WT, [model, shell], f"enemies/{NAME}", sprite["sprites"])
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--blend" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=argv[argv.index("--blend") + 1])

# --- the capsule ---------------------------------------------------------------------------------------------------

SLOTS = ["HULL", "GROOVE", "LID", "HANDLE", "HOUSING", "BED", "SLAT", "RIM", "CORE"]
S = {k: i for i, k in enumerate(SLOTS)}
AX = 12.5  # the housing's, core's and handles' centre column edge
ZT = 0.36  # the barrel's top


def materials(sprite, tag="nshk276"):
    def pal(i, **kw):
        return common.palette_material(sprite, i, tag, **kw)
    m = [
        pal(9, metallic=0.5, roughness=0.36),  # HULL
        pal(6, metallic=0.45, roughness=0.42),  # GROOVE the girth groove
        pal(9, metallic=0.5, roughness=0.38),  # LID
        pal(6, metallic=0.5, roughness=0.4),  # HANDLE
        pal(11, metallic=0.55, roughness=0.32),  # HOUSING
        pal(5, metallic=0.35, roughness=0.55),  # BED the grille beds
        pal(11, metallic=0.55, roughness=0.32),  # SLAT
        pal(113, metallic=0.4, roughness=0.45),  # RIM the core's dark red rim
        common.palette_material(sprite, 121, tag + "core", metallic=1.0, roughness=0.6, emission_strength=1.0),
    ]
    return m


def mirror_y(bm, n_verts0, n_faces0, axis=14.0):
    """Mirror the geometry built after (n_verts0, n_faces0) about row edge `axis` (a copy is added)."""
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    dup = bmesh.ops.duplicate(bm, geom=list(bm.verts[n_verts0:]) + list(bm.faces[n_faces0:]))
    ay = 2 * Y(axis)
    for v in dup["geom"]:
        if isinstance(v, bmesh.types.BMVert):
            v.co.y = ay - v.co.y
    bmesh.ops.reverse_faces(bm, faces=[f for f in dup["geom"] if isinstance(f, bmesh.types.BMFace)])


def hull(bm):
    sp = inner_rows()
    xl, xr = {}, {}
    for r in range(4, 24):
        runs = sp[r]
        xl[r + 0.5], xr[r + 0.5] = runs[0][0], runs[-1][1]
    for r in range(10, 18):  # the flanks: straight on the left; the right follows the sprite's groove notch
        xl[r + 0.5] = 0.6
    xr.update({10.5: 24.0, 11.5: 23.6, 12.5: 23.05, 13.5: 23.0, 14.5: 23.0, 15.5: 23.05, 16.5: 23.6, 17.5: 24.0})
    xl[3.6], xr[3.6] = 5.6, 19.4
    xl[24.4], xr[24.4] = 5.6, 19.4
    smooth(xl, 3.0, 10.0)
    smooth(xr, 3.0, 10.0)
    smooth(xl, 18.0, 25.0)
    smooth(xr, 18.0, 25.0)
    xl, xr = curve(xl), curve(xr)

    def zt(t):
        d = abs(t - 14.0)
        z = ZT - 0.05 * max(0.0, (d - 8.0) / 2.4) ** 2
        if d < 1.15:  # the girth groove
            z -= 0.035 * (1 - (d / 1.15) ** 4)
        return z

    def mat(t):
        return S["GROOVE"] if abs(t - 14.0) < 1.05 else S["HULL"]
    ct = lambda t: min(4.6, 0.42 * (xr(t) - xl(t)))  # noqa: E731
    loft(bm, "y", stations(3.6, 24.4, xl, xr, -0.26, zt, ct, ct, 3.0, crown=0.03, step=0.35), mat, rnd=3)


def north(bm):
    """The north half's end parts (mirrored to the south)."""
    # The lid closing the barrel's end (rows 1.8-3.8, columns 7-18).
    ll = curve({1.85: 7.15, 2.5: 7.1, 3.1: 6.4, 3.6: 6.05, 4.0: 6.0})
    loft(bm, "y", stations(1.85, 4.0, ll, lambda t: 25.0 - ll(t), -0.12, 0.27, 1.6, 1.6, 1.0, crown=0.015, step=0.3),
         S["LID"], rnd=2)
    # The loop handle: two posts off the lid and a thin bar across their ends.
    for c in (8.0, 17.0):
        tube(bm, [(c, 2.6, 0.12), (c, 0.45, 0.12)], 0.95, 0.075, S["HANDLE"], sides=10, round0=False, round1=False)
    tube(bm, [(8.0, 0.5, 0.12), (17.0, 0.5, 0.12)], 0.25, 0.05, S["HANDLE"], sides=8, round0=False, round1=False)
    # The louvre housing's end plate and grille (rows 3.8-12, columns 9.2-15.8).
    a0, a1 = AX - 3.3, AX + 3.3
    hz = 0.49
    hb = 0.415  # the grille bed's level
    # End plate (rows 3.8-6.9) at full height, then the housing's lower body under the grille, its side walls up.
    loft(bm, "y", stations(3.8, 6.9, a0, a1, 0.2, hz, 0.8, 0.8, 0.2, crown=0.012, step=0.5), S["HOUSING"], rnd=2)
    loft(bm, "y", stations(6.7, 12.2, a0 + 0.3, a1 - 0.3, 0.2, hb, 0.3, 0.3, 0.2, step=5.5), S["BED"])
    loft(bm, "y", stations(6.7, 12.2, a0, a0 + 0.85, 0.2, hz, 0.6, 0.25, 0.2, step=5.5), S["HOUSING"], rnd=1)
    loft(bm, "y", stations(6.7, 12.2, a1 - 0.6, a1, 0.2, hz, 0.25, 0.6, 0.2, step=5.5), S["HOUSING"], rnd=1)
    # Three slats across the bed (columns 10, 12, 14), their tops a little under the housing's.
    for c in (10.0, 12.0, 14.0):
        loft(bm, "y", stations(6.9, 11.8, c + 0.1, c + 0.9, 0.3, hz - 0.02, 0.25, 0.25, 0.1, step=4.9), S["SLAT"],
             rnd=1)


def core(bm):
    # The core across the groove: a dark red rim block (rows 11.9-16.1) holding a glowing drum (rows 12.6-15.4).
    a0, a1 = AX - 3.4, AX + 3.4
    loft(bm, "y", stations(11.9, 16.1, a0, a1, 0.15, 0.44, 0.6, 0.6, 0.2, step=1.05), S["RIM"], rnd=1)
    tube(bm, [(a0 + 0.35, 14.0, 0.44), (a1 - 0.35, 14.0, 0.44)], 1.1, 0.075, S["CORE"], sides=16, round0=True,
         round1=True)


def build(sprite, coll):
    bm = bmesh.new()
    hull(bm)
    nv, nf = len(bm.verts), len(bm.faces)
    north(bm)
    mirror_y(bm, nv, nf)
    core(bm)
    return [to_object(NAME, bm, materials(sprite), coll)]


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection("nshk276")
    finish(build(sprite, coll), sprite, coll, 2600)


if __name__ == "__main__":
    main()
