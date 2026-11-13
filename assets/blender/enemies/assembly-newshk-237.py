"""Grey yoke mid-boss with a glowing red core (3.6 FLEET): assembly-newshk-237 (newshk.shp 161, 153,
167, 199, 191, 205, 237, 243) plus the beam stub newshk-163.

What it is: a flying craft seen from above, flying "down" the screen (the claws open toward the player; it leaves
at the top). A central pod hangs between two big C-shaped claw arms on a box beam and a thin feed pipe:
- the pod: an octagonal hull, its narrow rear end (north) a lid, its back a raised louvre housing with two rails;
  its front a cradle holding the big red core orb; under the orb a red conduit runs down a keel into
- the hub (newshk-191): a dark nozzle housing with a crossbar on top, a red nozzle glowing in it (frame 193 flares
  it), side brackets and two thin legs reaching south;
- the arms: a long slab with a raised rail, a glowing red vent on its inner face, a bright elbow plate, a dark
  joint collar, a darker lower arm curving in to a light claw tip, its jaw face a glowing red pad.

Built once in assembly coordinates (pixel edges: column e -> X = (e - 36) / 12, row r -> Y = (42 - r) / 12, so the
origin is the centre of newshk-191, as the shipped script), the left half mirrored about column edge 36.5, then cut
into the eight pieces (and the stub) with filled cuts. Every body is a loft of chamfered sections whose plan
extents come from the sprite's inner mask (D74) and are interpolated with pchip, so diagonals are faired and the
top view follows the sprite row by row. Sheen is lighting: no painted highlights. Undersides: chamfered closed
bottoms only. One outline shell from the whole (sealed) model, held inside it (D51/D90/D118), cut per piece.

Self-contained (the old lib_b055.py helper module is no longer used).
Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshk-237.py
Exports one model per piece with common.export_sprite_model (enemies/<piece>.glb + spriteModels json).
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
NAME = "assembly-newshk-237"
PX = 1 / 12
AXIS = 36.5  # the sprite mirrors about the centre of pixel column 36
PIECES = ["newshk-161", "newshk-153", "newshk-167", "newshk-199", "newshk-191", "newshk-205",
          "newshk-237", "newshk-243"]
STUB = "newshk-163"
CX0, CY0 = 141, 71  # screen centre of newshk-191 = assembly edge (36, 42) = Blender origin


def X(e):
    return (e - 36.0) * PX


def Y(r):
    return (42.0 - r) * PX


# --- the sprite's inner mask (D74) ------------------------------------------------------------------------------

def inner_spans():
    idx, colors = sprite_mask._load_assembly(NAME, REF)
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


# --- materials ----------------------------------------------------------------------------------------------------

def set_spec(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = level
            return


SLOTS = ["HULL", "ARM", "LIGHT", "DEEP", "JOINT", "BAND", "PIPE", "LID", "ORB", "STEM", "CLAW", "NOZ", "DARK"]
S = {k: i for i, k in enumerate(SLOTS)}


def materials(sprite, tag="nshk237", orb_frames=None):
    def pal(i, t=tag, **kw):
        return common.palette_material(sprite, i, t, **kw)
    m = [
        pal(10, metallic=0.5, roughness=0.36),  # HULL pod hull, cradle, rails, crossbar
        pal(9, metallic=0.5, roughness=0.38),  # ARM arms, beam, claw tips
        pal(11, metallic=0.55, roughness=0.32),  # LIGHT housing, louvre bars, elbow plate
        pal(3, metallic=0.3, roughness=0.6),  # DEEP grille and vent beds
        pal(4, metallic=0.4, roughness=0.5),  # JOINT the arm's joint collar
        pal(6, metallic=0.45, roughness=0.42),  # BAND hub
        pal(7, metallic=0.5, roughness=0.4),  # PIPE feed pipe, brackets, legs
        pal(8, metallic=0.5, roughness=0.4),  # LID rear lid
        # The core orb: a polished glowing glass sphere, metallic 1 (D173: a glow on a glossy dielectric reads
        # as its reflection), its hot spot the sun's sheen.
        common.palette_material(sprite, 115, tag + "orb", metallic=1.0, roughness=0.28, emission_strength=0.75,
                                frames=orb_frames),
        common.palette_material(sprite, 115, tag + "stem", metallic=1.0, roughness=0.7, emission_strength=1.0,
                                frames=orb_frames),
        common.palette_material(sprite, 116, tag + "glow", metallic=1.0, roughness=0.75, emission_strength=1.0),
        common.palette_material(sprite, 115, tag + "noz", metallic=1.0, roughness=0.7, emission_strength=1.0),
        pal(5, metallic=0.45, roughness=0.42),  # DARK lower arm
    ]
    set_spec(m[S["ORB"]], 1.0)
    return m


def load_sprite(name):
    return common.load_sprite(WT, name)


def merged_sprite(names):
    sp = load_sprite(names[0])
    for n in names[1:]:
        sp["colors"].update(load_sprite(n)["colors"])
    return sp


# --- geometry ---------------------------------------------------------------------------------------------------

def prof(u0, u1, zb, zt, ct0, ct1, cb, crown=0.0, tilt=0.0, ntop=3, rnd=0):
    """A chamfered section across u (pixel edges) between zb and zt (units): flat chamfered bottom, vertical
    sides (so the top view is exactly u0..u1), 45-degree top chamfers ct0 (low-u side) and ct1 (high-u side)
    in px, a crowned top (crown units at the middle) tilted by `tilt` units from the u0 to the u1 edge.
    rnd > 0 rounds each top chamfer into a quarter arc of rnd + 1 segments (inside the same plan, so the top
    view does not change): a single 45-degree facet reads as a faceted rim on a big faired hull."""
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
    """[1, 2, 1] / 4 smoothing of the table's values at keys strictly inside (lo, hi): takes the sprite's
    pixel staircase out of a diagonal edge (a 2-row step pchips into an S-crinkle otherwise)."""
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


def ellipsoid(bm, col, row, z, rxp, ryp, rz, mat, seg=24, rings=14):
    n0 = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((X(col) + v.co.x * rxp * PX, Y(row) + v.co.y * ryp * PX, z + v.co.z * rz))
    _faces(bm, mat)(n0)


# --- the left half ----------------------------------------------------------------------------------------------

ARM_ZT, ARM_ZB = 0.27, -0.23
# Inner edge of the claw's grey (where the red jaw pad begins), rows 64-74.
XS = {64: 15, 65: 15, 66: 15, 67: 16, 68: 16, 69: 17, 70: 17, 71: 18, 72: 18, 73: 19, 74: 19}


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
    if 58.8 < t < 60.4:  # the joint collar: a shallow groove round the arm
        z -= 0.025
    return z


def build_left(bm):
    xl, xr = arm_tables()
    # The arm, shoulder (row 15) to the joint and the lower arm (row 74.5).
    loft(bm, "y", stations(15.0, 74.6, xl, xr, ARM_ZB, arm_zt, 1.6, 1.1, 0.9, crown=0.012, step=0.8), arm_mat)
    # Raised rail along the arm's top (column 4, rows 22-52) where the sprite draws its light line.
    loft(bm, "y", stations(22.6, 52.4, 3.9, 5.2, ARM_ZT - 0.04, ARM_ZT + 0.03, 0.4, 0.4, 0.2, step=1.0), S["HULL"])
    # The bright elbow plate (rows 53-58), proud of the arm.
    loft(bm, "y", stations(53.2, 58.5, lambda t: xl(t) + 0.9, lambda t: xr(t) - 0.5, ARM_ZT - 0.03,
                           ARM_ZT + 0.035, 0.7, 0.7, 0.2, crown=0.01), S["HULL"])
    # The vent on the arm's inner face (rows 39-52): a dark bed with two glowing red slats.
    loft(bm, "y", stations(39.4, 52.6, 8.0, lambda t: xr(t) - 0.1, ARM_ZT - 0.06, ARM_ZT + 0.006, 0.3, 0.6, 0.2),
         S["DEEP"])
    for c in (9.0, 11.0):
        loft(bm, "y", stations(42.2, 51.7, c, c + 1.0, ARM_ZT - 0.03, ARM_ZT + 0.018, 0.25, 0.25, 0.1, step=1.0),
             S["CLAW"])
    # The claw tip (rows 71-81): light, a little proud, reaching in under the jaw pad.
    tl, tr = {}, {}
    for r in range(71, 82):
        tl[r + 0.5] = mask_l(r)
        tr[r + 0.5] = (XS[r] if r <= 74 else mask_r_first(r))
    smooth(tl, 71.6, 81.0)
    tl, tr = curve(tl), curve(tr)
    loft(bm, "y", stations(70.6, 81.8, tl, tr, ARM_ZB + 0.03, 0.285, 1.3, 1.1, 0.9, crown=0.01), S["ARM"])
    # The jaw pad (rows 64-74): a glowing red face sloping down toward the gap.
    jl, jr = {}, {}
    for r in range(64, 75):
        jl[r + 0.5] = XS[r] - 0.7
        jr[r + 0.5] = mask_r_first(r)
    smooth(jl, 64.6, 74.0)
    smooth(jr, 65.0, 74.0, passes=1)
    jl, jr = curve(jl), curve(jr)
    loft(bm, "y", stations(63.9, 74.4, jl, jr, -0.15, 0.2, 0.3, 1.0, 0.6, tilt=-0.07), S["CLAW"])
    # Box beam from the shoulder into the pod (rows 15-21; the south face chamfered deep).
    loft(bm, "x", stations(16.2, 26.5, 15.0, 21.0, -0.08, 0.21, 0.6, 2.2, 0.6, crown=0.008), S["ARM"])
    loft(bm, "x", stations(17.0, 26.0, 16.7, 18.3, 0.15, 0.23, 0.3, 0.3, 0.1, step=1.0), S["HULL"])
    # Feed pipe from the pod's flank over to the arm's shoulder.
    tube(bm, [(26.5, 9.5, 0.25), (17.6, 9.5, 0.25), (15.7, 10.25, 0.25), (14.5, 11.5, 0.24), (13.6, 12.7, 0.23),
              (13.15, 13.9, 0.22), (13.2, 16.0, 0.2)], 1.15, 0.085, S["PIPE"], sides=10, round0=False,
         round1=False)
    # Hub bracket (rows 30-37) and the thin leg (column 26, rows 37-46).
    bl = curve({30.5: 26.0, 31.5: 25.2, 32.5: 25.2, 33.5: 25.2, 34.5: 25.2, 35.5: 25.2, 36.5: 25.2, 37.5: 25.4})
    br = curve({30.5: 31.6, 31.5: 31.6, 32.5: 31.6, 33.5: 31.6, 34.5: 31.2, 35.5: 30.4, 36.5: 29.4, 37.5: 28.2})
    loft(bm, "y", stations(29.9, 37.8, bl, br, -0.13, 0.1, 0.6, 0.4, 0.4), S["PIPE"])
    tube(bm, [(26.35, 36.8, -0.01), (26.45, 41.0, -0.035), (26.5, 46.1, -0.06)], 0.95, 0.07, S["PIPE"], sides=8,
         round0=False)


def mirror(bm, n_verts0, n_faces0):
    """Mirror the geometry built after (n_verts0, n_faces0) about the sprite's axis."""
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    faces = bm.faces[n_faces0:]
    dup = bmesh.ops.duplicate(bm, geom=list(bm.verts[n_verts0:]) + list(faces))
    ax = 2 * X(AXIS)
    for v in dup["geom"]:
        if isinstance(v, bmesh.types.BMVert):
            v.co.x = ax - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[f for f in dup["geom"] if isinstance(f, bmesh.types.BMFace)])


# --- the centre -------------------------------------------------------------------------------------------------

def pod_tables():
    xl = {1.5: 31, 2.5: 31, 3.5: 30, 4.5: 29, 5.5: 28, 6.5: 27, 7.5: 26, 8.5: 25, 9.5: 25, 10.5: 24.8, 11.5: 25,
          12.5: 25, 13.5: 24.8, 14.5: 24.3, 15.5: 24.2, 16.5: 24.2, 17.5: 24.2, 18.5: 24.2, 19.5: 24.3, 20.5: 24.6,
          21.5: 25.6, 22.5: 28, 23.5: 29, 24.5: 30, 25.5: 30, 26.5: 30, 27.5: 29.4, 28.5: 29.0}
    return curve(xl)


def pod_zt(t):
    if t < 3.4:
        return 0.4
    if t < 4.2:
        return 0.4 + (0.62 - 0.4) * (t - 3.4) / 0.8
    if t <= 13.2:
        return 0.62
    if t < 14.0:
        return 0.62 + (0.33 - 0.62) * (t - 13.2) / 0.8
    if t <= 21.2:
        return 0.33
    if t < 22.4:
        return 0.33 + (0.18 - 0.33) * (t - 21.2) / 1.2
    return 0.18


def pod_zb(t):
    if t < 4:
        return -0.05 - 0.2 * (t - 0.9) / 3.1
    if t < 21:
        return -0.34
    return -0.34 + 0.14 * min(1, (t - 21) / 4)


def pod_ct(t):
    return 2.6 if t < 13.4 else 1.3 if t < 21.5 else 0.8


def pod_mat(t):
    return S["HULL"]


def build_centre(bm):
    A = AXIS
    xl = pod_tables()
    xr = lambda t: 2 * A - xl(t)  # noqa: E731
    # Pod hull: rear neck (rows 1-3), octagonal dome (4-13), cradle (14-21), keel to the hub (22-29).
    loft(bm, "y", stations(0.95, 29.3, xl, xr, pod_zb, pod_zt, pod_ct, pod_ct, 2.0,
                           crown=lambda t: 0.04 if 4 < t < 13.5 else 0.015), pod_mat, rnd=3)
    # Rear lid (rows 1-3) over the neck.
    loft(bm, "y", stations(0.9, 3.0, 31.0, 42.0, 0.1, 0.5, 0.9, 0.9, 0.3, crown=0.02, step=0.35), S["LID"])
    # Louvre housing on the dome's back (rows 3.6-13), its top stepping down over the grille.
    hz = lambda t: 0.72 if t < 6.6 else 0.67 if t > 7.2 else 0.72 - 0.05 * (t - 6.6) / 0.6  # noqa: E731
    loft(bm, "y", stations(3.6, 13.3, 31.3, 41.7, 0.4, hz, 0.8, 0.8, 0.2, crown=0.012, step=0.4), S["LIGHT"])
    for c0, c1 in ((31.3, 32.6), (40.4, 41.7)):
        loft(bm, "y", stations(3.9, 13.1, c0, c1, 0.57, 0.735, 0.35, 0.35, 0.1, step=1.0), S["HULL"])
    loft(bm, "y", stations(7.0, 12.9, 33.0, 40.0, 0.57, 0.673, 0.2, 0.2, 0.1, step=1.0), S["DEEP"])
    for c in (34.0, 36.0, 38.0):
        loft(bm, "y", stations(7.4, 11.7, c, c + 1.0, 0.62, 0.708, 0.25, 0.25, 0.1, step=1.0), S["LIGHT"])
    # The core orb in its cradle and the red conduit down the keel into the hub.
    ellipsoid(bm, A, 18.45, 0.24, 5.6, 5.45, 0.45, S["ORB"], seg=24, rings=14)
    tube(bm, [(A, 21.5, 0.13), (A, 25.0, 0.16), (A, 30.2, 0.12)], 1.55, 0.11, S["STEM"], sides=10, round0=False,
         round1=False)
    # Hub (rows 29-38): a dark nozzle housing with a crossbar on top and the red nozzle glowing in it.
    hl = curve({29.5: 28.6, 30.5: 28.2, 31.5: 28.0, 32.5: 28.0, 33.5: 28.0, 34.5: 28.4, 35.5: 31.0, 36.5: 32.0,
                37.5: 33.3})
    loft(bm, "y", stations(29.2, 38.0, hl, lambda t: 2 * A - hl(t), -0.19, 0.16, 1.0, 1.0, 1.2, crown=0.02),
         S["BAND"])
    tube(bm, [(27.7, 29.95, 0.17), (45.3, 29.95, 0.17)], 1.05, 0.08, S["HULL"], sides=10)
    ellipsoid(bm, A, 34.4, 0.165, 2.6, 3.3, 0.065, S["NOZ"], seg=16, rings=8)


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


def build(sprite, coll):
    bm = bmesh.new()
    build_left(bm)
    mirror(bm, 0, 0)
    build_centre(bm)
    build_right_extra(bm)
    return to_object(NAME, bm, materials(sprite), coll)


def build_right_extra(bm):
    """The one asymmetry: newshk-243's claw is drawn to its box's left edge (column 48) with no ink there (the
    ink would fall in the empty box between the claws), so the right jaw and tip reach 1 px further in."""
    loft(bm, "y", stations(70.9, 74.3, curve({71.5: 48.9, 72.5: 48.0, 73.5: 48.0, 74.0: 48.6}), 51.5, -0.15, 0.13,
                           0.6, 0.3, 0.4, step=0.5), S["CLAW"])
    loft(bm, "y", stations(74.6, 81.8, 48.0, 51.5, ARM_ZB + 0.03, 0.27, 1.0, 0.6, 0.6, step=0.8), S["ARM"])


def build_stub(sprite, coll):
    """newshk-163: the left beam and the feed pipe carried on to column 35 where the pod would hang."""
    bm = bmesh.new()
    loft(bm, "x", stations(22.0, 35.2, 15.0, 21.0, -0.08, 0.21, 0.6, 2.2, 0.6, crown=0.008), S["ARM"])
    loft(bm, "x", stations(22.0, 34.6, 16.7, 18.3, 0.15, 0.23, 0.3, 0.3, 0.1, step=1.0), S["HULL"])
    tube(bm, [(22.0, 9.5, 0.25), (35.0, 9.5, 0.25)], 1.15, 0.085, S["PIPE"], sides=10, round0=False)
    return to_object("stub-" + STUB, bm, materials(sprite), coll)


def nozzle_flare(sprite, coll):
    """newshk-191 frame 193: the nozzle flares from a narrow glow to a big one with a yellow-white core
    (assembly columns 33-40, rows 31-38). In assembly coordinates = newshk-191's own."""
    mats = [common.palette_material(sprite, i, "nshk191-flare", metallic=1.0, roughness=0.7, emission_strength=k)
            for i, k in ((119, 1.0), (122, 1.0), (126, 1.1))]
    bm = bmesh.new()
    ellipsoid(bm, AXIS, 34.6, 0.17, 3.4, 3.7, 0.085, 0, seg=20, rings=10)
    ellipsoid(bm, AXIS, 34.8, 0.18, 2.4, 2.6, 0.085, 1, seg=16, rings=8)
    ellipsoid(bm, AXIS, 35.0, 0.19, 1.3, 1.5, 0.08, 2, seg=12, rings=6)
    return common.frame_part(to_object("newshk-191-flare-193", bm, mats, coll), [193])


# --- assembly splitting (cut faces filled with the neighbouring material; shells cut open) -----------------------

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


def animate_orb(piece, sprite):
    """newshk-153: the orb and conduit brighten over its frames, every red shade 2, 6 and 8 steps up on frames
    155, 157 and 159 (the sprite's own shift). Their materials get their own tag so 191 keeps the static ones."""
    mats = materials(sprite, "nshk153", orb_frames={155: 117, 157: 121, 159: 123})
    for slot in ("ORB", "STEM"):
        piece.data.materials[S[slot]] = mats[S[slot]]


def tri(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = merged_sprite(PIECES + [STUB])
    coll = common.reset_collection("nshk237A")
    whole = build(sprite, coll)
    stub = build_stub(sprite, coll)
    shell = shell_of(coll, whole, 2600)
    stub_shell = shell_of(coll, stub, 500)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    parts = split_pieces(whole, layout, coll)
    shells = split_pieces(shell, layout, coll, cap=False)
    sl = [(STUB, 141 - CX0, 43 - CY0)]
    parts.update(split_pieces(stub, sl, coll))
    shells.update(split_pieces(stub_shell, sl, coll, cap=False))
    animate_orb(parts["newshk-153"], sprite)
    flare = nozzle_flare(sprite, coll)
    # Pieces stay at the origin: split_pieces centres each mesh on its piece and the game places it by the
    # assembly layout, so an object location here would apply the offset twice (exploded craft).
    for name, ob in parts.items():
        ob.location = (0, 0, 0)
        sh = shells[name]
        sh.name = f"{name}_outline"
        sh.data.materials.clear()
        sh.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
        sh["tyrian_outline"] = True
        sh.location = (0, 0, 0)
    report = {n: tri(o) for n, o in parts.items()}
    report["total_pieces"] = sum(report.values())
    report["shell"] = tri(shell)
    print("TRIS", report)
    for o in (whole, stub, shell, stub_shell):
        o.hide_render = True
        o.hide_set(True)
    for name in PIECES + [STUB]:
        objs = [parts[name], shells[name]] + ([flare] if name == "newshk-191" else [])
        common.export_sprite_model(WT, objs, f"enemies/{name}", common.load_sprite(WT, name)["sprites"])
    if "--blend" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=argv[argv.index("--blend") + 1])


if __name__ == "__main__":
    main()
