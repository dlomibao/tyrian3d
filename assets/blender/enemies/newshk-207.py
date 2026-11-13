"""Red-winged V ship (3.6 FLEET): newshk-207 (newshk.shp frame 207, type 704, a weaving flyer).

What it is: a small attack craft seen from above, flying down the screen. A grey U-shaped hull: two narrow
dark-grey arms rise up the outer edges to points (rows 3-14), joined by a heavier light-grey bowl across the
bottom (rows 14-26). Bolted along the inside of each arm is a thick red armour plate (rows 9-18), a wedge that
rises toward its inner edge (the sprite's orange diagonal is that ridge catching the light: sheen, rule 2), with a
glowing yellow eye set in its inner corner (row 13). Between the plates a narrow slot runs down the middle, and
across the plates' lower ends a deep trough (the sprite's dark row 18) separates them from the bowl's raised deck,
which carries a framed square recess on the centre line (rows 19-24) and shoulder blocks at both sides.

Built in sprite coordinates (column edge e -> X = (e - 12) / 12, row edge r -> Y = (14 - r) / 12). Every body is
a loft of chamfered sections whose plan extents come from the sprite's inner mask (D74), interpolated with pchip,
so the top view follows the sprite row by row. The arms, plates, eyes, shoulders and recess frame are built once
and mirrored about column edge 12; the bowl follows the mask on both sides. Undersides: chamfered closed bottoms.
Colours are the sprite's per-region medians: arms 6, bowl/deck 9, plates 117, recess frame 12, recess floor 5,
trough 3, eyes 124 (glow: metallic 1, rough, D126/D173). One outline shell (D51/D90/D118).

Self-contained (lib_b045 is no longer used).
Run: tools/build-models.sh -j 2 assets/blender/enemies/newshk-207.py
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
NAME = "newshk-207"
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

# --- the V ship ----------------------------------------------------------------------------------------------------

SLOTS = ["ARM", "BOWL", "RED", "FRAME", "FLOOR", "DEEP", "EYE"]
S = {k: i for i, k in enumerate(SLOTS)}
AXIS = 12.0
SPANS = None


def materials(sprite, tag="nshk207"):
    def pal(i, **kw):
        return common.palette_material(sprite, i, tag, **kw)
    m = [
        pal(6, metallic=0.5, roughness=0.4),  # ARM the dark-grey arms
        pal(9, metallic=0.5, roughness=0.38),  # BOWL the bowl, its deck and shoulders
        pal(117, metallic=0.45, roughness=0.36),  # RED the armour plates
        pal(12, metallic=0.55, roughness=0.32),  # FRAME the recess frame
        pal(5, metallic=0.4, roughness=0.5),  # FLOOR the recess floor
        pal(3, metallic=0.3, roughness=0.6),  # DEEP the trough
        common.palette_material(sprite, 124, tag + "eye", metallic=1.0, roughness=0.6, emission_strength=1.0),
    ]
    set_spec(m[S["RED"]], 0.7)
    return m


def build_left(bm):
    # The arm: from its point (row 3.6) down the outer edge, widening under the plate into the bowl.
    al = {3.5: 0.15, 4.5: 0.0, 5.5: 0.0, 6.5: 0.0, 7.5: 0.0, 8.5: 0.0, 9.5: 0.0, 10.5: 0.0, 11.5: 0.0, 12.5: 0.0,
          13.5: 0.0, 14.5: 0.6, 15.5: 0.8}
    ar = {3.5: 0.85, 4.5: 1.0, 5.5: 1.05, 6.5: 1.3, 7.5: 2.2, 8.5: 3.2, 9.5: 6.8, 10.5: 7.8, 11.5: 8.9, 12.5: 9.9,
          13.5: 10.9, 14.5: 11.4, 15.5: 11.4}
    smooth(ar, 6.0, 13.0, passes=1)
    al, ar = curve(al), curve(ar)
    zt = lambda t: 0.06 + 0.06 * min(1.0, (t - 3.4) / 5.0)  # noqa: E731
    loft(bm, "y", stations(3.4, 15.6, al, ar, -0.1, zt, 0.8, 0.5, 0.6, crown=0.01, step=0.4), S["ARM"], rnd=1)
    # A raised rib along the arm's outer edge (the sprite's lit column 1-2 line).
    rl = curve({4.5: 0.1, 6.5: 0.2, 9.5: 0.6, 12.5: 1.0, 14.5: 1.4})
    loft(bm, "y", stations(4.2, 14.8, rl, lambda t: rl(t) + 1.3, 0.05, lambda t: zt(t) + 0.035, 0.5, 0.5, 0.2,
                           step=0.6), S["ARM"], rnd=1)
    # The red armour plate: a wedge rising to its inner edge (rows 8.6-18).
    pl = {9.5: 3.0, 10.5: 3.1, 11.5: 3.7, 12.5: 4.2, 13.5: 4.8, 14.5: 5.2, 15.5: 5.9, 16.5: 6.4, 17.5: 7.4}
    pr = {8.5: 3.9, 9.5: 7.0, 10.5: 7.9, 11.5: 8.9, 12.5: 9.9, 13.5: 10.95, 14.5: 11.4, 15.5: 11.45, 16.5: 11.45,
          17.5: 11.45}
    pl[8.7] = 3.0
    pl, pr = curve(pl), curve(pr)
    loft(bm, "y", stations(8.7, 18.0, pl, pr, 0.0, 0.17, 0.5, 1.1, 0.3, tilt=0.09, crown=0.012, step=0.4), S["RED"],
         rnd=1)
    # The eye in the plate's inner corner (row 13, column 9).
    ellipsoid(bm, 9.55, 13.45, 0.245, 0.75, 0.75, 0.035, S["EYE"], seg=14, rings=8)
    # Shoulder block (rows 14.6-19, columns 1-6.6) at the bowl's outer corner.
    loft(bm, "y", stations(14.6, 19.2, 1.0, 6.7, -0.05, 0.19, 0.8, 0.9, 0.4, crown=0.01, step=0.5), S["BOWL"],
         rnd=1)
    # The recess frame's left bar and half the bottom bar (rows 18.9-24, columns 9-10 and 9-12).
    loft(bm, "y", stations(18.9, 24.0, 9.05, 10.1, 0.08, 0.205, 0.3, 0.3, 0.2, step=1.0), S["FRAME"], rnd=1)
    loft(bm, "x", stations(9.05, 12.0, 22.9, 24.0, 0.08, 0.205, 0.3, 0.45, 0.2, step=1.0), S["FRAME"], rnd=1)


def build_centre(bm):
    # The bowl: the mask's span on both sides (rows 13.8-26), its front rounded down.
    bl, br = {}, {}
    for r in range(14, 26):
        (c0, c1), = SPANS[r]
        bl[r + 0.5], br[r + 0.5] = c0, c1
    bl[14.5], br[14.5] = 0.6, 23.0
    smooth(bl, 18.0, 26.0)
    smooth(br, 18.0, 26.0)
    bl[25.9], br[25.9] = 8.6, 15.4
    bl, br = curve(bl), curve(br)
    zt = lambda t: 0.1 if t < 22.5 else 0.1 - 0.09 * ((t - 22.5) / 3.4) ** 1.6  # noqa: E731
    loft(bm, "y", stations(13.8, 25.9, bl, br, -0.2, zt, 1.0, 1.0, 1.0, crown=0.01, step=0.4), S["BOWL"], rnd=1)
    # The trough floor under the plates' lower ends (row 18, columns 6.5-17.5).
    loft(bm, "y", stations(17.6, 18.9, 6.6, 17.4, 0.05, 0.115, 0.1, 0.1, 0.1, step=1.3), S["DEEP"])
    # The raised deck (rows 18.8-25), inset from the bowl's edge.
    dl = lambda t: bl(t) + 0.8  # noqa: E731
    dr = lambda t: br(t) - 0.8  # noqa: E731
    dz = lambda t: 0.16 if t < 22.6 else 0.16 - 0.1 * ((t - 22.6) / 2.4) ** 1.5  # noqa: E731
    loft(bm, "y", stations(18.85, 25.0, dl, dr, 0.0, dz, 0.9, 0.9, 0.3, crown=0.008, step=0.4), S["BOWL"], rnd=1)
    # The recess floor between the frame bars (columns 10-14, rows 19-23).
    loft(bm, "y", stations(19.0, 23.0, 10.0, 14.0, 0.1, 0.17, 0.15, 0.15, 0.1, step=4.0), S["FLOOR"])
    # The slot down the middle between the plates: a dark floor (columns 11.4-12.6, rows 13-18).
    loft(bm, "y", stations(13.9, 18.0, 11.35, 12.65, -0.02, 0.08, 0.1, 0.1, 0.1, step=5.4), S["DEEP"])


def build(sprite, coll):
    global SPANS
    SPANS = inner_rows()
    bm = bmesh.new()
    build_left(bm)
    mirror_x(bm, 0, 0, AXIS)
    build_centre(bm)
    return [to_object(NAME, bm, materials(sprite), coll)]


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection("nshk207")
    finish(build(sprite, coll), sprite, coll, 2400)


if __name__ == "__main__":
    main()
