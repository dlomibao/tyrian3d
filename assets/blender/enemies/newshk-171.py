"""Fireball with a blue eye (3.6 FLEET): newshk-171 (newshk.shp frame 171, size 1; type 710, the projectile
newshk-278's gunship launches, drifting +6 px/tick).

What it is: a small glowing red teardrop of plasma, its point trailing up the screen (it flies down), its fat end
holding a round blue glass eye seated in a glowing orange socket ring. Round in section all along (a lathe of
elliptical rings whose widths come from the sprite's inner mask (D74), pchip-interpolated), a little flatter than
it is wide; the sprite's bright spine streak and the eye's white glint are its sheen (rule 2), not paint.
Colours are the sprite's per-region medians: body 116 (an ember glow, D126: partly lit), socket ring 121 (glow,
metallic 1, rough, D173), eye 57 (polished, Specular IOR Level 1, D176). One outline shell.

Built in sprite coordinates (column edge e -> X = (e - 6) / 12, row edge r -> Y = (7 - r) / 12).
Self-contained (lib_b045 is no longer used).
Run: tools/build-models.sh -j 2 assets/blender/enemies/newshk-171.py
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
NAME = "newshk-171"
W, H = 12, 14

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

# --- the fireball --------------------------------------------------------------------------------------------------

SLOTS = ["BODY", "RING", "EYE"]
S = {k: i for i, k in enumerate(SLOTS)}
AX = 5.5  # the sprite's centre column edge


def materials(sprite, tag="nshk171"):
    m = [
        common.palette_material(sprite, 116, tag + "body", metallic=1.0, roughness=0.55, emission_strength=0.6),
        common.palette_material(sprite, 121, tag + "ring", metallic=1.0, roughness=0.6, emission_strength=1.0),
        common.palette_material(sprite, 57, tag + "eye", metallic=0.6, roughness=0.2),
    ]
    set_spec(m[S["EYE"]], 1.0)
    return m


def lathe(bm, table, zc, flat, mat, sides=20, t0=0.55, t1=14.0, step=0.25):
    """Elliptical rings down the rows: half width table(t) px, half height flat * that (units), centred at zc."""
    n0 = len(bm.faces)
    rings = []
    for t in frange(t0, t1, step):
        w = max(0.0, table(t))
        if w < 1e-3:
            rings.append([bm.verts.new((X(AX), Y(t), zc))])
            continue
        rings.append([bm.verts.new((X(AX) + w * PX * math.cos(a), Y(t), zc + flat * w * PX * math.sin(a)))
                      for a in (2 * math.pi * (j + 0.5) / sides for j in range(sides))])
    for r0, r1 in zip(rings, rings[1:]):
        n = max(len(r0), len(r1))
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[k], r1[j]))
            elif len(r1) == 1:
                bm.faces.new((r0[k], r1[0], r0[j]))
            else:
                bm.faces.new((r0[k], r1[k], r1[j], r0[j]))
    _faces(bm, mat)(n0)


def build(sprite, coll):
    bm = bmesh.new()
    hw = {0.55: 0.0, 0.9: 0.3, 1.5: 0.5, 2.5: 0.55, 3.5: 1.45, 4.5: 1.5, 5.5: 2.35, 6.5: 2.5, 7.5: 3.5, 8.5: 3.5,
          9.5: 3.5, 10.5: 3.5, 11.5: 3.5, 12.5: 2.65, 13.2: 1.6, 13.75: 0.9, 14.0: 0.0}
    smooth(hw, 2.0, 7.6, passes=2)
    lathe(bm, curve(hw), 0.0, 0.8, S["BODY"])
    # The eye's socket ring (glowing orange) and the blue glass eye in it.
    ellipsoid(bm, AX, 9.85, 0.185, 3.0, 2.8, 0.075, S["RING"], seg=24, rings=12)
    ellipsoid(bm, AX, 9.4, 0.2, 2.5, 2.3, 0.115, S["EYE"], seg=24, rings=14)
    return [to_object(NAME, bm, materials(sprite), coll)]


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection("nshk171")
    finish(build(sprite, coll), sprite, coll, 1200)


if __name__ == "__main__":
    main()
