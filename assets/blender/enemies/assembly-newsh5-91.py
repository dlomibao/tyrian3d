"""Design A: the twisted fire column (assembly-newsh5-91 = newsh5-53 over newsh5-91), episode 4
(4.16 NOSE DRIP: 28 of them drift down the screen at 2 px/tick, top layer, armour 40).

WHAT IT IS. Two burning strands wound round each other like a two-ply rope, 24x56 px, tapering
to a thin flickering point at the top and a blunter point at the bottom. Where the strands lie
side by side the sprite shows them parted (the gaps at rows 10 and 15-20); where they cross the
column narrows to a waist (rows 13, 24, 38). So the model is a real rope: two round fire tubes on
a helix, side by side at the bulges and stacked at the waists, read from every angle.

THE PLAN FIT. Each strand's centre line at sprite row t is x = c(t) + s*A(t)*sin(th(t)),
z = s*A(t)*cos(th(t)) (s = +1, -1), its radius rho(t); c, A and rho are pchip curves through 23
knots, th through 11 knots at the bulges (side by side, 90 + 180k deg) and waists (stacked). The
knots were fitted offline (fit.py, scipy least squares) so the union of the two strands' plans
covers the sprite's inner mask (sprite_mask, D74) row by row, gaps included: fit grid IoU 0.9955.

DETAIL. Each strand is a faired tube with six shallow flame grooves (cut inward only, so the plan
edge stays the fitted one) that twist the other way round the strand at 1.6x the rope's rate: the
plies of the rope, reading as licking flame tongues. Smooth shaded.

COLOUR. Every face takes the palette index of the sprite under its centre, from a weighted blur
of the sprite's flame pixels only (indices 115 up; the 112-114 edge ring is ink and lighting, art
rule 2), clamped to 116..124, so the bright cores of the lower strands and the dimmer red tip land
where the sprite has them. Faces turned down are 116 (no dark apron). All glow (D126/D173: metal 1,
rough 0.9), the hot cores fully, the red flanks partly so the twist still shades.

PIECES. Built once in assembly coordinates, cut by common.split_assembly into newsh5-53 (top) and
newsh5-91 (bottom), one frame each, materials pal_<i>_nsh5_91 as before. The outline shell (D51)
comes from a sealed copy without the grooves, voxel remeshed whole (islands="outer", D189), then
cut at the piece seam without capping, so no ink line crosses the column.

Run: blender --background --python assembly-newsh5-91.py [-- --out FILE]
Exports public/models/enemies/newsh5-53 and newsh5-91 (+ spriteModels JSON); --out FILE also writes the whole column.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]
import common  # noqa: E402

ROOT = common.repo_root(__file__)

NAME = "assembly-newsh5-91"
TAG = "nsh5_91"
W, H = 24, 56
LAYOUT = [("newsh5-53", 0.0, -14.0), ("newsh5-91", 0.0, 14.0)]  # piece centres, px from the column centre
U = 1 / 12

# --- the fitted plan (fit.py) ------------------------------------------------------------------
KN = [0.6, 3.01, 5.42, 7.83, 10.24, 12.65, 15.05, 17.46, 19.87, 22.28, 24.69, 27.1, 29.51, 31.92,
      34.33, 36.74, 39.15, 41.55, 43.96, 46.37, 48.78, 51.19, 53.6]
C = [11.97, 11.99, 12.27, 12.5, 12.39, 12.67, 12.53, 12.5, 12.5, 12.5, 12.5, 12.5, 12.5, 12.5, 12.5,
     12.5, 12.49, 12.49, 12.54, 12.82, 12.61, 12.69, 13.02]
A = [0.0, 0.15, 0.9, 1.77, 2.32, 2.9, 3.49, 3.83, 4.2, 4.43, 4.14, 3.7, 3.44, 3.39, 4.07, 4.07, 4.05,
     3.8, 2.9, 1.67, 1.31, 0.69, 0.0]
RHO = [0.05, 0.28, 0.98, 1.43, 1.31, 1.14, 1.3, 1.37, 1.94, 2.47, 2.47, 2.68, 3.27, 3.5, 3.47, 2.86,
       2.74, 2.84, 3.07, 3.07, 3.19, 1.66, 0.05]
TH_ROWS = [0.6, 5.5, 10.5, 13.5, 18.0, 24.5, 32.5, 38.5, 43.5, 49.5, 53.6]
TH_DEG = [-59.8, 18.4, 93.0, 183.2, 267.0, 355.3, 444.3, 539.8, 631.5, 710.6, 780.2]

STEP = 0.3  # ring spacing, sprite rows
SIDES = 20
GROOVES = 6
GROOVE_DEPTH = 0.13  # share of the strand radius
GROOVE_TWIST = -1.6  # groove turns per rope turn (the other way round)

# Glow per palette index (D126; metal 1, rough: the red flanks still shade)
GLOW = {116: 0.7, 117: 0.72, 118: 0.76, 119: 0.8, 120: 0.85, 121: 0.9, 122: 0.94, 123: 0.97, 124: 1.0}


# --- pchip (Fritsch-Carlson), as scipy's PchipInterpolator ---------------------------------------
def pchip(xs, ys):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    h = np.diff(xs)
    d = np.diff(ys) / h
    n = len(xs)
    m = np.zeros(n)
    for k in range(1, n - 1):
        if d[k - 1] * d[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])

    def end(h0, h1, d0, d1):
        v = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
        if np.sign(v) != np.sign(d0):
            return 0.0
        if np.sign(d0) != np.sign(d1) and abs(v) > abs(3 * d0):
            return 3 * d0
        return v
    m[0] = end(h[0], h[1], d[0], d[1])
    m[-1] = end(h[-1], h[-2], d[-1], d[-2])

    def f(x):
        x = np.asarray(x, float)
        k = np.clip(np.searchsorted(xs, x) - 1, 0, n - 2)
        t = (x - xs[k]) / h[k]
        h00, h10 = (1 + 2 * t) * (1 - t) ** 2, t * (1 - t) ** 2
        h01, h11 = t * t * (3 - 2 * t), t * t * (t - 1)
        return h00 * ys[k] + h10 * h[k] * m[k] + h01 * ys[k + 1] + h11 * h[k] * m[k + 1]
    return f


fC, fA, fR, fT = pchip(KN, C), pchip(KN, A), pchip(KN, RHO), pchip(TH_ROWS, TH_DEG)


def bx(x):
    """Sprite x (px, pixel edges; the column's 24 px span 0..24) to Blender X."""
    return (x - W / 2) * U


def by(t):
    """Sprite row coordinate (pixel edges, 0..56) to Blender Y (sprite up = +Y)."""
    return (H / 2 - t) * U


# --- sprite ------------------------------------------------------------------------------------
def load_sprite():
    colors, idx = {}, np.full((H, W), -1, int)
    names = []
    for name, _, cy in LAYOUT:
        d = common.load_sprite(ROOT, name)
        colors.update(d["colors"])
        oy = int(cy + 14)  # 0 for the top piece, 28 for the bottom
        for y, row in enumerate(d["frames"][0]["pixels"]):
            idx[oy + y] = row
        names.append(name)
    return {"name": NAME, "colors": colors}, idx


def flame_map(idx):
    """Weighted blur of the flame pixels (115+), ignoring the ink/edge ring."""
    w = (idx >= 115).astype(float)
    v = np.where(w > 0, idx, 0).astype(float)
    s = 1.0
    r = 3
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2)

    def blur(a):
        p = np.pad(a, r)
        p = np.apply_along_axis(lambda q: np.convolve(q, k, mode="valid"), 0, p)
        return np.apply_along_axis(lambda q: np.convolve(q, k, mode="valid"), 1, p)
    bw, bv = blur(w), blur(v)
    return np.where(bw > 1e-3, bv / np.maximum(bw, 1e-6), 117.0)


def bilinear(a, x, y):
    x = min(a.shape[1] - 1.001, max(0.0, x))
    y = min(a.shape[0] - 1.001, max(0.0, y))
    c, r = int(x), int(y)
    fx, fy = x - c, y - r
    return ((a[r, c] * (1 - fx) + a[r, c + 1] * fx) * (1 - fy) + (a[r + 1, c] * (1 - fx) + a[r + 1, c + 1] * fx) * fy)


# --- geometry ----------------------------------------------------------------------------------
def strand_points(s, ts):
    c, a, th = fC(ts), fA(ts), np.radians(fT(ts))
    x = c + s * a * np.sin(th)
    z = s * a * np.cos(th)
    return [Vector((bx(xx), by(t), zz * U)) for xx, t, zz in zip(x, ts, z)], th


def tube(bm, pts, radii, phase, grooves, mat=0):
    """Round tube along pts, rings parallel transported; `phase` rotates the groove pattern per
    ring. Grooves cut inward only. Ends are points."""
    n = len(pts)
    tang = []
    for i in range(n):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < n - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tang.append(t.normalized())
    u = tang[0].cross(Vector((0, 0, 1))).normalized()
    rings = []
    for i, (c, t, rad) in enumerate(zip(pts, tang, radii)):
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u).normalized()
        if i in (0, n - 1):
            rings.append([bm.verts.new(c)])
            continue
        ring = []
        for k in range(SIDES):
            a = 2 * math.pi * k / SIDES
            g = max(0.0, math.cos(GROOVES * (a - phase[i]))) ** 4 if grooves else 0.0
            rr = rad * (1 - GROOVE_DEPTH * g)
            ring.append(bm.verts.new(c + rr * (math.cos(a) * u + math.sin(a) * v)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(SIDES):
            j = (k + 1) % SIDES
            if len(r0) == 1:
                f = (r0[0], r1[k], r1[j])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f).material_index = mat


def build(coll, sprite, idx, grooves=True, name=NAME):
    fm = flame_map(idx)
    used = list(range(116, 125))
    mats = [common.palette_material(sprite, v, TAG, metallic=1.0, roughness=0.9, emission_strength=GLOW[v])
            for v in used]
    bm = bmesh.new()
    # ends: the tips (rho 0.05) are closed to a point a little past the knots
    ts = np.concatenate([[KN[0] - 0.25], np.arange(KN[0], KN[-1], STEP), [KN[-1], KN[-1] + 0.2]])
    for s in (1, -1):
        pts, th = strand_points(s, ts)
        radii = [max(0.02, float(r)) * U for r in fR(ts)]
        phase = GROOVE_TWIST * th + (0 if s > 0 else math.pi / GROOVES)
        tube(bm, pts, radii, list(phase), grooves)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    for f in bm.faces:
        cen = f.calc_center_median()
        if f.normal.z < -0.3:
            v = 116
        else:
            v = int(round(bilinear(fm, cen.x / U + W / 2 - 0.5, H / 2 - cen.y / U - 0.5) + 1.0))
            if f.normal.z < 0.15:  # flanks: one step under the crest (still glowing, not an apron)
                v -= 1
        f.material_index = used.index(min(124, max(116, v)))
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def split_open(obj, layout, coll):
    """common.split_assembly without capping the cuts (for the outline shell)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        me.shade_smooth()
        out[name] = sh
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    arg = lambda k: argv[argv.index(k) + 1] if k in argv else None  # noqa: E731
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    sprite, idx = load_sprite()
    obj = build(coll, sprite, idx)
    pieces = common.split_assembly(obj, LAYOUT)
    plain = build(coll, sprite, idx, grooves=False, name=NAME + "_plain")
    bpy.context.view_layer.update()
    # Outline shell from a sealed, ungrooved copy of the whole column (D51, D189), cut open at the seam.
    whole_shell = common.outline_shell(plain, coll, voxel=0.011, faces=5000, smooth=4, inside=0.02, islands="outer")
    shells = split_open(whole_shell, LAYOUT, coll)
    for o in (plain, whole_shell):
        bpy.data.objects.remove(o, do_unlink=True)
    for n, sh in shells.items():
        if not sh.data.polygons:
            raise SystemExit(f"{n}_outline has no mesh")
        print("SHELL", n, len(sh.data.vertices), "verts")
    print("TRIS whole", sum(len(p.vertices) - 2 for p in obj.data.polygons))
    for name, _, _ in LAYOUT:
        pieces[name].name = name
        shells[name].name = f"{name}_outline"
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"])
    if arg("--out"):
        for name, cx, cy in LAYOUT:
            pieces[name].location = shells[name].location = (cx / 12, -cy / 12, 0)
        bpy.context.view_layer.update()
        common.export_glb([pieces[n] for n, _, _ in LAYOUT] + [shells[n] for n, _, _ in LAYOUT], Path(arg("--out")))


if __name__ == "__main__":
    main()
