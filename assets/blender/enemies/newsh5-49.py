"""TAN FIGHTER (newsh5.shp frame 49, 24x28), design A: a hard-surface jet fighter, nose DOWN the screen.

What it is. Read from the sprite (the authority) the plane flies down the screen, toward the player, as it
does in 4.19 APPROACH (it sinks +1 px/tick):
  - rows 20-26: the nose. A 5 px fuselage narrows to a 3 px radome (rows 21-23) and a 1 px pitot probe
    (rows 24-25, dark 19/17) ending in the single ink pixel of row 26: a pointed nose, not a tail;
  - rows 17-19: swept canards, tips at row 18 behind their roots at row 19-20;
  - rows 13-16: the cockpit, a bubble canopy (the bright 29/27/26 pixels, cols 11-12) just behind them;
  - rows 6-12: the centre fuselage, 7 px wide: side intake trunks (cols 9 and 15, index 20/21) whose
    mouths face the nose at row 12, and the straight-trailing-edge wings (rows 7-11, the leading edge
    swept back from col 5 row 10 to the root at row 12);
  - cols 2-4, rows 4-12: a grey gun pod / missile on each wingtip, its POINTED end (one ink pixel) at row
    12, i.e. pointing the way the plane flies, its blunt tail (3 ink px) at row 4; the wing passes over
    its middle (rows 7-8 show wing colours);
  - rows 1-4: swept-back tailplanes (tips at row 1, roots at row 3-4) and the vertical fin, whose
    top edge is the 1 px light line down col 12 (27/26), and the exhaust nozzle at row 2.
  (The earlier brief/script read it nose-up with forward-swept "canards" at rows 1-3; the pointed pod
  ends, the probe and the canopy placement say nose-down. The top view is the same either way.)

Built in sprite coordinates: column edge e -> X = (e - 12) / 12, row edge r -> Y = (14 - r) / 12; the
sprite is symmetric about column edge 12.5. Planforms follow the sprite's inner mask (D74: the game
draws the ink ring), interpolated with pchip. Fuselage, canopy, pods and probe are lofts of
superellipse sections; wings, tailplanes, canards and fin are lofts of airfoil sections (round
leading edge, blunt trailing edge) with a modelled hinge groove on the wings. Panel seams are modelled
grooves in the fuselage loft. Colours are the sprite's per-region medians (shading and highlights
dropped: col 11's 27-30 streak is sheen on the round spine, col 13's 18/19 is shade): centre fuselage
and wings 23, tailplanes 24, tail cone, forward fuselage, trunks and canards 21, radome 20, canopy
and fin 26, pods 6 with a light tail cap 8 and a dark muzzle 4, probe 18, intake mouths and nozzle 17.
Underside: the lofts' plain closed bottoms. One outline shell (D51, islands="outer" D189).

Run: blender --background --python assets/blender/enemies/newsh5-49.py
Exports public/models/enemies/newsh5-49.glb and its spriteModels entry.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy


HERE = Path(__file__).resolve()


def _repo():
    for p in HERE.parents:
        if (p / "package.json").exists() and (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("repo root not found")


WT = _repo()
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

PX = 1 / 12
NAME = "newsh5-49"
W, H = 24, 28
AXIS = 12.5


def X(e):
    return (e - W / 2) * PX


def Y(r):
    return (H / 2 - r) * PX


def curve(table):
    ks = sorted(table)
    return T.pchip(ks, [table[k] for k in ks])


def frange(a, b, step):
    n = max(1, int(round((b - a) / step)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def set_spec(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = level
            return


# --- materials ---------------------------------------------------------------------------------------------------

SLOTS = ["HULL", "WING", "STAB", "DARK", "RADOME", "CANOPY", "POD", "PODTAIL", "PODNOSE", "HOLE", "SEAM", "PROBE"]
S = {k: i for i, k in enumerate(SLOTS)}


def materials(sprite, tag="nsh5_49"):
    def pal(i, **kw):
        return common.palette_material(sprite, i, tag, **kw)
    m = [
        pal(23, metallic=0.5, roughness=0.4),   # HULL centre fuselage
        pal(23, metallic=0.5, roughness=0.4),   # WING (same index; a slot of its own for clarity)
        pal(24, metallic=0.5, roughness=0.4),   # STAB tailplanes
        pal(21, metallic=0.5, roughness=0.42),  # DARK tail cone, forward fuselage, trunks, canards
        pal(20, metallic=0.45, roughness=0.45),  # RADOME
        pal(26, metallic=0.65, roughness=0.18),  # CANOPY opaque polished bubble (and the fin)
        pal(6, metallic=0.6, roughness=0.35),   # POD gun pods
        pal(8, metallic=0.6, roughness=0.32),   # PODTAIL light tail caps
        pal(4, metallic=0.6, roughness=0.4),    # PODNOSE dark muzzles
        pal(17, metallic=0.3, roughness=0.7),   # HOLE intake mouths, nozzle
        pal(18, metallic=0.4, roughness=0.6),   # SEAM panel grooves
        common.palette_material(sprite, 18, tag + "probe", metallic=0.7, roughness=0.3),  # PROBE pitot
    ]
    # Same index -> palette_material returns the same datablock; keep slots distinct by index use only.
    set_spec(m[S["CANOPY"]], 0.8)
    return m


# --- geometry helpers -----------------------------------------------------------------------------------------

def _sgnpow(v, e):
    return math.copysign(abs(v) ** e, v)


def sring(cx, y, hw, zb, zc, zt, nt=2.3, nb=3.0, N=24):
    """A superellipse section in the XZ plane at Y=y (units): widest (hw units) at height zc, top zt,
    bottom zb; nt / nb the top / bottom exponents (2 = ellipse, higher = boxier)."""
    pts = []
    for k in range(N):
        th = 2 * math.pi * k / N
        c, s = math.cos(th), math.sin(th)
        n = nt if s >= 0 else nb
        x = cx + hw * _sgnpow(c, 2 / n)
        z = zc + ((zt - zc) if s >= 0 else (zc - zb)) * _sgnpow(s, 2 / n)
        pts.append((x, y, z))
    return pts


def ring_loft(bm, rings, mats, cap0=None, cap1=None):
    """Bridge rings (lists of equal length). mats[i] the slot of band i. cap0/cap1: slot of a fan cap
    (None = no cap; the ring must then have collapsed)."""
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(vs[0])
    for i, (r0, r1) in enumerate(zip(vs, vs[1:])):
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = mats[i](k, n) if callable(mats[i]) else mats[i]
            f.smooth = True
    for slot, r, rev in ((cap0, vs[0], True), (cap1, vs[-1], False)):
        if slot is None:
            continue
        cx = sum(v.co.x for v in r) / n
        cy = sum(v.co.y for v in r) / n
        cz = sum(v.co.z for v in r) / n
        c = bm.verts.new((cx, cy, cz))
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((r[k], r[j], c) if not rev else (r[j], r[k], c))
            f.material_index = slot
            f.smooth = True


def body(bm, rows, hw, zb, zc, zt, mat, cx_e=AXIS, nt=2.3, nb=3.0, N=24, grooves=(), cap0=None, cap1=None,
         gw=0.07, gd=0.035):
    """A superellipse loft down the rows. hw in px; zb/zc/zt in units (callables of the row). grooves:
    rows where a panel seam is cut (a narrow ring pulled in by gd of the half-size, slot SEAM)."""
    f = lambda v, r: v(r) if callable(v) else v  # noqa: E731
    stations = list(rows)
    for g in grooves:
        stations += [g - gw, g, g + gw]
    stations = sorted(set(round(s, 4) for s in stations))
    rings, mids = [], []
    for r in stations:
        k = 1.0
        if any(abs(r - g) < 1e-6 for g in grooves):
            k = 1.0 - gd
        h = f(hw, r) * PX * k
        zcv = f(zc, r)
        rings.append(sring(X(cx_e), Y(r), h, zcv - (zcv - f(zb, r)) * k, zcv, zcv + (f(zt, r) - zcv) * k, f(nt, r), nb, N))
    for a, b in zip(stations, stations[1:]):
        m = (a + b) / 2
        ing = any(abs(m - g) < gw for g in grooves)
        mids.append(S["SEAM"] if ing else (mat(m) if callable(mat) else mat))
    ring_loft(bm, rings, mids, cap0, cap1)


# Airfoil chord stations (0 = leading edge, 1 = trailing edge) and half-thickness shape (blunt TE).
AF_U = [0.0, 0.03, 0.1, 0.22, 0.4, 0.6, 0.8, 1.0]


def af_half(u):
    return 0.5 * (1.15 * math.sqrt(u) * (1 - u) ** 0.85 + 0.12 * u) / 0.62


def airfoil(le, te, zmid, th, grooves=(), crown=0.0):
    """Section points [(chord coordinate, z, groove?)] top LE->TE then bottom TE->LE. le/te are the
    chord ends (any units), th the max thickness. grooves: chord fractions where the top is grooved."""
    us = sorted(set(AF_U + [g + d for g in grooves for d in (-0.035, 0.0, 0.035)]))
    top, bot = [], []
    for u in us:
        c = le + (te - le) * u
        h = af_half(u) * th
        gz = -0.35 * h if any(abs(u - g) < 1e-6 for g in grooves) else 0.0
        top.append((c, zmid + h + gz + crown, any(abs(u - g) < 0.036 for g in grooves)))
        bot.append((c, zmid - h * 0.85, False))
    pts = top + list(reversed(bot[1:-1]))
    return pts


def plate(bm, ts, le, te, zmid, th, mat, along="x", grooves=(), cap0=True, cap1=True, cx_e=AXIS):
    """A lifting surface lofted along `along`: 'x' = spanwise across columns (sections in rows), 'z' = a fin
    standing up (sections in rows, thickness across columns about AXIS). le/te/zmid/th callables of t."""
    rings, seams = [], None
    for t in ts:
        pts = airfoil(le(t), te(t), zmid(t), th(t), grooves)
        if along == "x":
            rings.append([(X(t), Y(c), z) for c, z, _ in pts])
        else:  # fin: t is height z, the "z" of the airfoil is the x offset in px
            rings.append([(X(cx_e + z / PX), Y(c), t) for c, z, _ in pts])
        seams = [g for _, _, g in pts]
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(vs[0])
    for r0, r1 in zip(vs, vs[1:]):
        for k in range(n):
            j = (k + 1) % n
            fc = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            fc.material_index = S["SEAM"] if (seams[k] and seams[j]) else mat
            fc.smooth = True
    for flag, r in ((cap0, vs[0]), (cap1, vs[-1])):
        if flag:
            fc = bm.faces.new(r)
            fc.material_index = mat
            fc.smooth = False


def prof(u0, u1, zb, zt, ct0, ct1, cb, crown=0.0, ntop=3, rnd=1):
    """Chamfered box section across u (column edges) between zb and zt (units), round top chamfers."""
    w = u1 - u0
    h = (zt - zb) / PX
    ct0 = max(0.05, min(ct0, 0.45 * w, 0.7 * h))
    ct1 = max(0.05, min(ct1, 0.45 * w, 0.7 * h))
    cb = max(0.05, min(cb, 0.45 * w, 0.3 * h))

    def top(u):
        s = (u - u0) / w * 2 - 1
        return zt + crown * (1 - s * s)

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


def box_loft(bm, rows, a0, a1, zb, zt, ct0, ct1, cb, mat, cap0=True, cap1=True, cap1_mat=None, rnd=1):
    f = lambda v, r: v(r) if callable(v) else v  # noqa: E731
    rings = []
    for r in rows:
        rings.append([(X(u), Y(r), z) for u, z in prof(f(a0, r), f(a1, r), f(zb, r), f(zt, r), f(ct0, r),
                                                      f(ct1, r), f(cb, r), rnd=rnd)])
    vs = [[bm.verts.new(p) for p in rr] for rr in rings]
    n = len(vs[0])
    for r0, r1 in zip(vs, vs[1:]):
        for k in range(n):
            j = (k + 1) % n
            fc = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            fc.material_index = mat
            fc.smooth = True
    for flag, r, m in ((cap0, vs[0], mat), (cap1, vs[-1], cap1_mat if cap1_mat is not None else mat)):
        if flag:
            fc = bm.faces.new(r)
            fc.material_index = m
            fc.smooth = False
    return rings


def quad(bm, pts, mat):
    fc = bm.faces.new([bm.verts.new(p) for p in pts])
    fc.material_index = mat
    fc.smooth = False


def mirror_x(bm, nv0, nf0, axis):
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    dup = bmesh.ops.duplicate(bm, geom=list(bm.verts[nv0:]) + list(bm.faces[nf0:]))
    ax = 2 * X(axis)
    for v in dup["geom"]:
        if isinstance(v, bmesh.types.BMVert):
            v.co.x = ax - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[f for f in dup["geom"] if isinstance(f, bmesh.types.BMFace)])


def to_object(name, bm, mats, coll):
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    try:
        me.set_sharp_from_angle(angle=math.radians(40))
    except AttributeError:
        pass
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


# --- the fighter ----------------------------------------------------------------------------------------------

def build_left(bm):
    """Wing, pod, tailplane, canard and intake trunk on the left (mirrored about AXIS)."""
    # Main wing: TE straight at row 7.0, LE swept back from (col 5, row 10) to the root (col 9, row 12.5).
    le = curve({2.0: 9.85, 3.5: 9.95, 5.0: 10.08, 7.0: 11.3, 9.0: 12.5, 10.8: 13.6})
    te = lambda x: 7.0  # noqa: E731
    zm = curve({2.0: 0.024, 6.0: 0.022, 10.8: 0.02})
    th = curve({2.0: 0.03, 6.0: 0.042, 10.8: 0.05})
    xs = [2.0, 2.15, 2.7, 4.0, 5.0, 6.0, 7.5, 9.0, 10.8]
    # hinge groove of the aileron/flap: 1.2 px ahead of the trailing edge (chord fraction per station)
    ga = lambda x: 1.0 - 1.2 / max(1.5, le(x) - 7.0)  # noqa: E731
    # one plate per span band so the groove fraction follows the chord
    rings_x = xs
    plate_grooved(bm, rings_x, le, te, zm, th, S["WING"], ga)

    # Wingtip gun pod: centre col edge 3.5, z -0.045; blunt light tail at row 4.35, pointed dark muzzle at 12.65.
    rr = curve({4.6: 0.3, 4.75: 0.45, 5.2: 0.6, 5.7: 0.82, 6.2: 1.02, 6.7: 1.06, 9.4: 1.04, 10.3: 0.97, 11.0: 0.86,
                11.6: 0.6, 12.2: 0.28, 12.6: 0.04})
    zc = -0.052
    rows = frange(4.6, 12.6, 0.8) + [4.68, 4.75, 5.2, 11.6, 12.2, 12.45]
    rows = sorted(set(round(r, 3) for r in rows))
    body(bm, rows, rr, lambda r: zc - rr(r) * PX * 0.98, zc, lambda r: zc + rr(r) * PX * 0.98,
         lambda r: S["PODTAIL"] if r < 5.6 else (S["PODNOSE"] if r > 10.75 else S["POD"]),
         cx_e=3.5, nt=2.0, nb=2.0, N=10, grooves=(5.6, 10.75), cap0=S["PODTAIL"], cap1=S["PODNOSE"], gd=0.05)
    # small dorsal tail fin on each pod (rows 4.5-6.2)
    plate(bm, frange(zc + 0.07, zc + 0.115, 0.045), lambda z: 6.2 - (z - zc - 0.07) * 20, lambda z: 4.5,
          lambda z: 0.0, lambda z: 0.35 * PX, S["POD"], along="z", cx_e=3.5)

    # Tailplane: tip chord rows 1.0-2.0 at col 6, LE swept to the root at (10, 5.6).
    le = curve({6.0: 2.0, 8.0: 3.8, 10.0: 5.6, 11.4: 6.4})
    te = curve({6.0: 1.0, 8.5: 1.0, 9.0: 1.1, 9.6: 1.75, 10.6: 3.0, 11.4: 3.7})
    plate(bm, [6.0, 6.15, 6.8, 8.2, 9.0, 9.6, 10.4, 11.4], le, te,
          lambda x: 0.07, curve({6.0: 0.022, 11.4: 0.034}), S["STAB"])

    # Canard: tips at row 18 (col 6), LE from (6, 18.9) to the root at (10, 20.7); root fillet into row 17.
    le = curve({6.0: 18.9, 8.0: 19.4, 10.0: 20.7, 11.2: 21.4})
    te = curve({6.0: 18.05, 8.6: 17.95, 9.4: 17.25, 10.5: 16.65, 11.2: 16.4})
    plate(bm, [6.0, 6.15, 6.8, 8.0, 8.8, 9.4, 10.2, 11.2], le, te,
          lambda x: 0.06, curve({6.0: 0.024, 11.2: 0.04}), S["DARK"])



def plate_grooved(bm, xs, le, te, zm, th, mat, gfrac):
    """The wing: airfoil loft along x with a hinge groove whose chord fraction varies with x."""
    rings, flags = [], []
    for x in xs:
        g = gfrac(x)
        pts = airfoil(le(x), te(x), zm(x), th(x), grooves=(g,))
        rings.append([(X(x), Y(c), z) for c, z, _ in pts])
        flags.append([gg for _, _, gg in pts])
    n = len(rings[0])
    assert all(len(r) == n for r in rings)
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    for i, (r0, r1) in enumerate(zip(vs, vs[1:])):
        fl = flags[i]
        for k in range(n):
            j = (k + 1) % n
            fc = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            fc.material_index = S["SEAM"] if (fl[k] and fl[j]) else mat
            fc.smooth = True
    for r in (vs[0], vs[-1]):
        fc = bm.faces.new(r)
        fc.material_index = mat
        fc.smooth = False


def build_centre(bm):
    # Fuselage: nozzle at row 1.9, 5 px tube (hw 2.5) rows 3.8-20.3, radome 3 px (rows 21-23), cone to 24.9.
    hw = curve({1.9: 1.35, 2.5: 1.5, 3.2: 2.25, 3.8: 2.5, 5.4: 2.5, 5.75: 2.95, 6.1: 3.4, 6.5: 3.5, 12.72: 3.5,
                12.78: 2.3, 12.95: 2.5, 20.2: 2.48, 20.7: 2.2, 21.2: 1.68,
                22.0: 1.52, 22.8: 1.47, 23.5: 1.25, 24.1: 0.82, 24.5: 0.5, 24.75: 0.28, 24.92: 0.1})
    zt = curve({1.9: 0.095, 3.0: 0.12, 5.0: 0.14, 7.0: 0.165, 12.4: 0.168, 13.0: 0.155, 14.0: 0.152, 17.0: 0.14,
                19.5: 0.122, 21.0: 0.1, 23.0: 0.075, 24.3: 0.052, 24.92: 0.034})
    zb = curve({1.9: -0.035, 3.0: -0.055, 6.0: -0.08, 13.0: -0.08, 17.0: -0.072, 20.0: -0.058,
                23.0: -0.03, 24.3: -0.0, 24.92: 0.016})
    zc = curve({1.9: 0.03, 12.0: 0.03, 20.0: 0.03, 24.92: 0.026})

    def mat(r):
        if r < 5.2:
            return S["DARK"]
        if r < 12.72:
            return S["HULL"]
        if r < 12.78:  # the intake mouths: the step's side faces, facing the nose
            return lambda k, n: S["HOLE"] if abs(math.sin(2 * math.pi * (k + 0.5) / n)) < 0.72 else S["DARK"]
        if r < 20.45:
            return S["DARK"]
        return S["RADOME"]

    rows = frange(1.9, 24.92, 0.75) + [2.05, 2.2, 3.2, 5.4, 5.75, 6.1, 6.5, 12.72, 12.78, 12.95, 20.7, 21.2, 23.9, 24.3, 24.6, 24.85]
    ntc = curve({1.9: 2.3, 5.0: 2.3, 6.5: 2.0, 12.6: 2.0, 13.2: 2.3, 25.0: 2.2})
    body(bm, rows, hw, zb, zc, zt, mat, nt=ntc, nb=3.2, N=18, grooves=(2.6, 5.2, 20.45),
         cap0=S["HOLE"], cap1=S["RADOME"])
    # Nozzle lip: a short ring proud of the tail end, the dark exhaust inside it.
    body(bm, [1.75, 1.9, 2.3], lambda r: 1.42, lambda r: zb(2.0) - 0.004, lambda r: zc(2.0),
         lambda r: zt(2.0) + 0.004, S["SEAM"], nt=2.4, nb=3.2, N=18, cap0=None, cap1=None)
    quad_disc(bm, Y(1.76), 1.15, zb(2.0) + 0.012, zc(2.0), zt(2.0) - 0.012)

    # Pitot probe (rows 24.5-26.0).
    pr = curve({24.5: 0.32, 25.2: 0.3, 25.8: 0.24, 26.0: 0.05})
    body(bm, frange(24.5, 26.0, 0.25), pr, lambda r: 0.026 - pr(r) * PX, lambda r: 0.026,
         lambda r: 0.026 + pr(r) * PX, S["PROBE"], nt=2.0, nb=2.0, N=8, cap0=S["PROBE"], cap1=S["PROBE"])

    # Bubble canopy (rows 13.2-16.6) on the forward fuselage, and its frame bow at row 15.0.
    chw = curve({13.0: 0.3, 13.5: 0.95, 14.3: 1.28, 15.3: 1.3, 16.2: 0.95, 16.8: 0.2})
    czt = curve({13.0: 0.16, 13.6: 0.2, 14.6: 0.236, 15.5: 0.24, 16.3: 0.208, 16.8: 0.17})
    body(bm, frange(13.0, 16.8, 0.34), chw, 0.1, 0.14, czt, S["CANOPY"], nt=2.0, nb=2.0, N=16,
         cap0=S["CANOPY"], cap1=S["CANOPY"])
    body(bm, [14.82, 14.9, 15.04, 15.12], lambda r: chw(r) * 1.06 if 14.85 < r < 15.1 else chw(r) * 0.9,
         0.1, 0.14, lambda r: czt(r) + (0.006 if 14.85 < r < 15.1 else -0.01), S["DARK"], nt=2.0, nb=2.0, N=16,
         cap0=S["DARK"], cap1=S["DARK"])
    # canopy sill: a low rail round the bubble's base
    body(bm, frange(13.15, 16.65, 0.5), lambda r: chw(r) + 0.18, 0.1, 0.14, lambda r: 0.152 + 0.0 * r,
         S["DARK"], nt=2.0, nb=2.0, N=16, cap0=S["DARK"], cap1=S["DARK"])

    # Vertical fin: root rows 1.3-6.4 at z 0.11, tip rows 1.0-2.5 at z 0.36.
    ts = frange(0.11, 0.36, 0.05)
    k = lambda z: (z - 0.11) / 0.25  # noqa: E731
    plate(bm, ts, lambda z: 6.4 - 3.9 * k(z) ** 0.85, lambda z: 0.95, lambda z: 0.0,
          lambda z: (0.9 - 0.25 * k(z)) * PX, S["CANOPY"], along="z")


def quad_disc(bm, y, hwp, zb, zc, zt):
    pts = sring(X(AXIS), y, hwp * PX, zb, zc, zt, 2.4, 3.2, 18)
    fc = bm.faces.new([bm.verts.new(p) for p in reversed(pts)])
    fc.material_index = S["HOLE"]
    fc.smooth = False


def build(sprite, coll):
    bm = bmesh.new()
    build_left(bm)
    mirror_x(bm, 0, 0, AXIS)
    build_centre(bm)
    return to_object(NAME, bm, materials(sprite), coll)


def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection("nsh5_49")
    model = build(sprite, coll)
    src = model.copy()
    src.data = model.data.copy()
    coll.objects.link(src)
    shell = common.outline_shell(src, coll, voxel=0.008, faces=2600, inside=0.004, islands="outer")
    bpy.data.objects.remove(src)
    assert len(shell.data.polygons) > 0, "empty outline shell"
    shell.name = NAME + "_outline"
    tri = lambda o: sum(len(p.vertices) - 2 for p in o.data.polygons)  # noqa: E731
    print("TRIS", NAME, tri(model), "shell", tri(shell))
    common.export_sprite_model(WT, [model, shell], f"enemies/{NAME}", sprite["sprites"])
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--blend" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=argv[argv.index("--blend") + 1])


if __name__ == "__main__":
    main()
