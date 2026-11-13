"""Horned gunship with a glowing core (3.6 FLEET): newshk-278 (newshk.shp frame 278, type 706; it weaves on the
sky/top layers and launches type 710, the fireball newshk-171).

What it is: a gunship seen from above, nose down the screen. Two parts:
- the back (rows 0-14): two grey horns rise up the outer edges to points, their roots widening into a dark deck;
  in the middle a grey cradle collar with a dark red inner rim holds a big glowing orange core dome (the
  launcher's charge), braced to each horn; the deck's front edge is a rounded bright lip (row 12) with a small
  red lamp set under it on the centre line (row 13);
- the front (rows 14-27): a wide grey gun block with two tan vent frames on each flank and a raised rail either
  side of a sunken dark red channel down the middle, in which two pink-red feed pipes (crossed by a bracket) and a
  grey centre rod run out over a tapered chin past the nose.
Built in sprite coordinates (column edge e -> X = (e - 12) / 12, row edge r -> Y = (14 - r) / 12). Bodies are lofts
of chamfered sections whose plan extents come from the sprite's inner mask (D74), pchip-interpolated. The sprite's
centre parts (core, lamp, rails, pipes, rod, horns) are symmetric about column edge 12.5 and its vents about 12, so
they are placed where the sprite draws them. Colours are the sprite's per-region medians: horns 7, deck 4, lip 9,
collar 6, core rim 113, core 120 and lamp 116 (glow: metallic 1, rough, D126/D173), block 7 (flanks 8), rails 12,
vents 27 with grey 9 slats, channel 112, pipes 70 / 67, pipe tips 65, rod 8. One outline shell.

Self-contained (lib_b045 is no longer used).
Run: tools/build-models.sh -j 2 assets/blender/enemies/newshk-278.py
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
NAME = "newshk-278"
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

# --- the gunship ---------------------------------------------------------------------------------------------------

SLOTS = ["HORN", "DECK", "LIP", "COLLAR", "RIM", "CORE", "LAMP", "TOP", "SIDE", "RAIL", "TAN", "SLAT", "CHANNEL",
         "PIPE", "PIPE2", "TIP", "ROD"]
S = {k: i for i, k in enumerate(SLOTS)}
AX = 12.5  # the centre parts' axis


def materials(sprite, tag="nshk278"):
    def pal(i, **kw):
        return common.palette_material(sprite, i, tag, **kw)

    def glow(i, t):
        return common.palette_material(sprite, i, tag + t, metallic=1.0, roughness=0.6, emission_strength=1.0)
    return [
        pal(7, metallic=0.5, roughness=0.38),  # HORN
        pal(4, metallic=0.4, roughness=0.5),  # DECK
        pal(9, metallic=0.5, roughness=0.36),  # LIP
        pal(6, metallic=0.5, roughness=0.4),  # COLLAR
        pal(113, metallic=0.4, roughness=0.45),  # RIM
        glow(120, "core"),  # CORE
        glow(116, "lamp"),  # LAMP
        pal(7, metallic=0.5, roughness=0.38),  # TOP the gun block's top
        pal(8, metallic=0.5, roughness=0.38),  # SIDE the gun block's flanks and chin
        pal(12, metallic=0.55, roughness=0.32),  # RAIL
        pal(27, metallic=0.3, roughness=0.45),  # TAN the vent frames
        pal(9, metallic=0.5, roughness=0.4),  # SLAT the vents' grey slats
        pal(112, metallic=0.3, roughness=0.6),  # CHANNEL
        pal(70, metallic=0.4, roughness=0.4),  # PIPE upper pipes and bracket
        pal(67, metallic=0.4, roughness=0.42),  # PIPE2 lower pipes
        pal(65, metallic=0.45, roughness=0.4),  # TIP pipe tips
        pal(8, metallic=0.55, roughness=0.35),  # ROD
    ]


def mirror_about(bm, nv, nf, axis):
    mirror_x(bm, nv, nf, axis)


def back(bm):
    nv, nf = len(bm.verts), len(bm.faces)
    # Left horn: a tapered prong from its point (row 0) down the outer edge, its root widening into the deck.
    hl = curve({0.3: 2.05, 1.5: 1.85, 2.5: 1.05, 3.5: 1.0, 5.5: 1.0, 7.5: 1.0, 9.5: 1.0, 10.8: 1.4})
    hr = curve({0.3: 2.95, 1.5: 3.0, 2.5: 3.05, 3.5: 3.1, 4.5: 3.9, 5.5: 4.9, 6.5: 6.0, 7.5: 7.0, 9.5: 7.0,
                10.8: 6.0})
    hz = lambda t: 0.2 + 0.06 * min(1.0, t / 4.0)  # noqa: E731
    loft(bm, "y", stations(0.25, 10.8, hl, hr, lambda t: -0.02 - 0.1 * min(1.0, t / 5.0), hz, 0.5, 0.8, 0.3,
                           crown=0.012, step=0.35), S["HORN"], rnd=1)
    # Brace from the horn root to the collar (row 8).
    tube(bm, [(3.4, 8.7, 0.24), (5.6, 8.4, 0.25), (7.8, 8.1, 0.25)], 0.8, 0.06, S["LIP"], sides=10, round0=False,
         round1=False)
    mirror_about(bm, nv, nf, AX)


def deck(bm):
    sp = inner_rows()
    dl = {6.6: 6.5, 7.5: 1.0, 8.5: 1.0, 9.5: 1.0, 10.5: 1.0, 11.5: 2.0, 12.5: 4.0, 13.5: 5.0, 14.2: 5.0}
    dr = {6.6: 18.5, 7.5: 24.0, 8.5: 24.0, 9.5: 24.0, 10.5: 23.0, 11.5: 23.0, 12.5: 21.0, 13.5: 20.0, 14.2: 20.0}
    smooth(dl, 10.0, 14.0, passes=1)
    smooth(dr, 10.0, 14.0, passes=1)
    dl, dr = curve(dl), curve(dr)
    loft(bm, "y", stations(6.6, 14.2, dl, dr, -0.15, 0.12, 0.8, 0.8, 0.6, crown=0.01, step=0.4), S["DECK"], rnd=1)
    # The bright lip along the deck's front (row 12) and the red lamp under it (row 13, columns 10-15).
    tube(bm, [(4.7, 12.45, 0.13), (20.3, 12.45, 0.13)], 0.85, 0.07, S["LIP"], sides=12)
    loft(bm, "y", stations(12.9, 14.05, 9.9, 15.1, -0.02, 0.1, 0.3, 0.3, 0.2, step=1.15), S["RIM"], rnd=1)
    tube(bm, [(10.6, 13.5, 0.1), (14.4, 13.5, 0.1)], 0.5, 0.045, S["LAMP"], sides=10)
    # The cradle collar round the core (rows 3.4-11).
    cl = curve({3.6: 11.2, 4.5: 9.0, 5.5: 8.0, 6.5: 7.0, 7.5: 7.0, 8.5: 7.4, 9.5: 8.0, 10.5: 8.6, 11.2: 9.2})
    loft(bm, "y", stations(3.6, 11.2, cl, lambda t: 2 * AX - cl(t), -0.05, 0.22, 1.0, 1.0, 0.4, crown=0.01,
                           step=0.35), S["COLLAR"], rnd=2)
    # The core: a glowing dome in a dark red rim, with a small nub at its rear (rows 2-3).
    ellipsoid(bm, AX, 7.1, 0.21, 3.2, 4.0, 0.07, S["RIM"], seg=24, rings=12)
    ellipsoid(bm, AX, 7.0, 0.2, 2.65, 3.45, 0.2, S["CORE"], seg=24, rings=14, zcut=0.12)
    ellipsoid(bm, AX, 3.4, 0.22, 0.6, 1.0, 0.06, S["RIM"], seg=10, rings=6)


def front(bm):
    # The gun block (rows 13.9-24), split round the channel (columns 9.2-15.8); the flanks follow the mask.
    bl = curve({13.9: 0.0, 21.5: 0.0, 22.5: 0.05, 23.5: 1.0, 24.1: 3.0})
    br = curve({13.9: 24.0, 21.5: 24.0, 22.5: 23.95, 23.5: 23.0, 24.1: 21.0})
    zt = lambda t: 0.16 if t < 22.8 else 0.16 - 0.06 * (t - 22.8) / 1.3  # noqa: E731
    loft(bm, "y", stations(13.9, 24.1, bl, 9.3, -0.2, zt, 1.2, 0.4, 0.8, crown=0.006, step=0.5),
         lambda t: S["TOP"], rnd=1)
    loft(bm, "y", stations(13.9, 24.1, 15.7, br, -0.2, zt, 0.4, 1.2, 0.8, crown=0.006, step=0.5),
         lambda t: S["TOP"], rnd=1)
    # Flank faces: the block's outer columns a step lower (the sprite's 8s).
    for a0, a1 in ((0.0, 1.9), (22.1, 24.0)):
        loft(bm, "y", stations(14.5, 23.3, a0, a1, -0.19, 0.135, 0.9, 0.9, 0.5, step=8.8), S["SIDE"], rnd=1)
    # Channel floor (columns 9-16) and the tapered chin under the nose (rows 23.5-25.9).
    loft(bm, "y", stations(14.2, 24.6, 9.0, 16.0, -0.18, 0.02, 0.2, 0.2, 0.3, step=10.4), S["CHANNEL"])
    nl = curve({23.4: 5.6, 24.5: 6.2, 25.5: 8.3, 26.0: 9.4})
    loft(bm, "y", stations(23.4, 26.0, nl, lambda t: 24.0 - nl(t), -0.14, lambda t: 0.08 - 0.05 * (t - 23.4) / 2.6,
                           0.8, 0.8, 0.6, step=0.4), S["SIDE"], rnd=1)
    # Rails either side of the channel (columns 7 and 17).
    for c in (7.5, 17.5):
        tube(bm, [(c, 14.7, 0.17), (c, 24.3, 0.17)], 0.8, 0.07, S["RAIL"], sides=12)
    # Vent frames (tan) with grey slats: columns 2-5 and 19-22, rows 15-19 and 20-24.
    for c0 in (2.0, 19.0):
        for r0 in (15.0, 20.0):
            loft(bm, "y", stations(r0 + 0.05, r0 + 3.95, c0 + 0.05, c0 + 2.95, 0.0, 0.2, 0.5, 0.5, 0.2, step=3.9),
                 S["TAN"], rnd=1)
            loft(bm, "y", stations(r0 + 0.9, r0 + 3.1, c0 + 1.05, c0 + 1.95, 0.1, 0.215, 0.25, 0.25, 0.1, step=2.2),
                 S["SLAT"], rnd=1)
    # Pipes (columns 10 and 14) down the channel and out past the nose, a bracket across them (rows 16-18).
    for c in (10.5, 14.5):
        tube(bm, [(c, 14.9, 0.06), (c, 21.0, 0.06)], 0.85, 0.07, S["PIPE"], sides=12, round0=False, round1=False)
        tube(bm, [(c, 21.0, 0.06), (c, 24.6, 0.05)], 0.85, 0.07, S["PIPE2"], sides=12, round0=False, round1=False)
        tube(bm, [(c, 24.6, 0.05), (c, 26.4, 0.04)], [0.85, 0.7][0], 0.065, S["TIP"], sides=12, round0=False)
    loft(bm, "y", stations(15.9, 18.0, 9.7, 15.3, 0.0, 0.13, 0.35, 0.35, 0.2, step=2.1), S["PIPE"], rnd=1)
    # The centre rod (column 12) from a socket under the bracket out to its bright tip (row 26.6).
    tube(bm, [(AX, 17.6, 0.05), (AX, 26.2, 0.04)], 0.6, 0.05, S["ROD"], sides=10)


def build(sprite, coll):
    bm = bmesh.new()
    back(bm)
    deck(bm)
    front(bm)
    return [to_object(NAME, bm, materials(sprite), coll)]


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection("nshk278")
    finish(build(sprite, coll), sprite, coll, 2800)


if __name__ == "__main__":
    main()
