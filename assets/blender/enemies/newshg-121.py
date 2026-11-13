"""Merged item newshg-121 (+ newshg-127, newshg-49, newshg-77): four episode-2 flyers.

WHAT THEY ARE (all fly free, closed all round, round undersides):
- newshg-121 (frames 121/123/125): a grabber-claw drone. A pearl orb sits in a cradle on a yoke; two
  jointed arms (upper pod, lower pod, bone hook) hang from the yoke ends on vertical hinge pins and
  close in over the frames while the pearl charges (dark -> lit -> white-hot glow).
- newshg-127 (127/129/131): a gimbal eye pod. A steel-blue ball held in a hoop band that runs over its
  top to two pivot bosses at its sides; a lens in a socket on its lower face turns per frame.
- newshg-49 (49/51/53): a golden stag beetle flying head-down the screen: ridged elytra (back), a
  wide pronotum shield with front lobes, a small head, two long curved mandibles and swept hind legs
  that close in over the frames.
- newshg-77 (77..93, 115..119): a molten crystal that morphs pyramid -> ball -> cube -> pyramid. One
  closed body per frame: true bevelled polyhedra for the sharp frames (tetrahedron point-on, box
  corner-on) with glowing near edges; soft polyhedra / a ball for the morph frames, their lava seams
  painted from the frame in emissive palette colours, the dark crust as facets on the sprite's ramp.

Every part is fitted to the frame's inner mask (D74): tubes measure their width from the mask along
their centreline; crystal bodies are radially fitted. Colours are the sprite's own palette index per
region (median, lighting trimmed). Outline shell per frame from a sealed joined copy (D90/D118).

    blender -b --factory-startup -P newshg-121_A.py
Run: blender --background --python assets/blender/enemies/newshg-121.py [-- claw pod beetle crystal]
Exports every model of the four items (enemies/newshg-121[-f2,-f3], newshg-127, newshg-49[-f2,-f3],
newshg-77[-f2..-f5]) with their src/render/spriteModels entries; newshg-127.py, newshg-49.py and
newshg-77.py run just their own group of this script (the merged item, one design).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

REF = WT / "reference" / "models"
SHELL = {"voxel": 0.018, "inside": 0.004, "faces": 900, "smooth": 6}


def X(u):
    return (u - 12) / 12


def Y(v):
    return (14 - v) / 12


def P3(u, v, z=0.0):
    return Vector((X(u), Y(v), z))


# --- sprite access --------------------------------------------------------------------------------

class Fr:
    """One sprite frame: palette indices and the rule's inner mask, in pixel-edge coords (u, v)."""

    def __init__(self, name, index):
        idx, colors = SM.load(name, index, REF)
        partners = SM.pulse_partners(idx, SM.load_frames(name, REF))
        m = SM.masks(idx, colors, partners)
        self.idx, self.inner, self.colors, self.free = idx, m["inner"], colors, m["free"]
        self.h, self.w = len(idx), len(idx[0])

    def ins(self, u, v):
        c, r = math.floor(u), math.floor(v)
        return 0 <= r < self.h and 0 <= c < self.w and self.inner[r][c]

    def pal(self, u, v):
        c, r = math.floor(u), math.floor(v)
        if 0 <= r < self.h and 0 <= c < self.w:
            return self.idx[r][c]
        return -1

    def at(self, x, y):
        return self.pal(x * 12 + 12, 14 - y * 12)

    def region(self, c0, c1, r0, r1):
        return [self.idx[r][c] for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if self.idx[r][c] >= 0]


def filled(fr):
    """The frame with holes in its inner mask closed (pixels not reachable from the edge through
    non-inner pixels, 4-way), for lofting a body through a see-through pixel."""
    out = [[False] * fr.w for _ in range(fr.h)]
    stack = [(c, r) for r in range(fr.h) for c in range(fr.w) if r in (0, fr.h - 1) or c in (0, fr.w - 1)]
    while stack:
        c, r = stack.pop()
        if not (0 <= r < fr.h and 0 <= c < fr.w) or out[r][c] or fr.inner[r][c]:
            continue
        out[r][c] = True
        stack += [(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)]
    fr.inner = [[not out[r][c] for c in range(fr.w)] for r in range(fr.h)]
    return fr


def luma_of(colors, i):
    r, g, b = colors[i]
    return 0.299 * r + 0.587 * g + 0.114 * b


def region_index(fr, vals, trim=0.2, ink=True):
    """Median palette index of a region, the darkest and brightest `trim` (lighting) left out."""
    vals = [v for v in vals if v >= 0 and (not ink or luma_of(fr.colors, v) >= 20)]
    vals.sort(key=lambda v: luma_of(fr.colors, v))
    k = int(len(vals) * trim)
    core = vals[k:len(vals) - k] or vals
    return core[len(core) // 2]


# --- geometry helpers (copied/adapted from lib_b034; shared files are not edited) ---------------

def ring_loft(bm, rings, mat, cap_start=True, cap_end=True):
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    for r0, r1 in zip(verts, verts[1:]):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0]))).material_index = mat
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1]).material_index = mat
    return verts


def ellipsoid(bm, centre, radii, segments=24, rings=12, mat=0, bottom=1.0):
    cx, cy, cz = centre
    rx, ry, rz = radii
    top = bm.verts.new((cx, cy, cz + rz))
    bot = bm.verts.new((cx, cy, cz - rz * bottom))
    grid = []
    for i in range(1, rings):
        phi = math.pi * i / rings
        s, c = math.sin(phi), math.cos(phi)
        zz = c * rz if c > 0 else c * rz * bottom
        grid.append([bm.verts.new((cx + rx * s * math.cos(2 * math.pi * k / segments),
                                   cy + ry * s * math.sin(2 * math.pi * k / segments), cz + zz))
                     for k in range(segments)])
    for k in range(segments):
        j = (k + 1) % segments
        bm.faces.new((top, grid[0][k], grid[0][j])).material_index = mat
        bm.faces.new((bot, grid[-1][j], grid[-1][k])).material_index = mat
    for a, b in zip(grid, grid[1:]):
        for k in range(segments):
            j = (k + 1) % segments
            bm.faces.new((a[k], b[k], b[j], a[j])).material_index = mat


def tube3(bm, pts, radius, sides=10, mat=0, flat=1.0, closed=False):
    """A round tube along 3D points; `closed` joins the ends into a loop."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * n
    rings = []
    for i in range(n):
        if closed:
            t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        else:
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        a = t.cross(ref).normalized()
        b = t.cross(a).normalized()
        if b.z < 0:
            b = -b
        rings.append([tuple(pts[i] + radii[i] * (math.cos(q) * a + flat * math.sin(q) * b))
                      for q in (2 * math.pi * (k + 0.5) / sides for k in range(sides))])
    if closed:
        rings.append(rings[0])
        verts = [[bm.verts.new(p) for p in ring] for ring in rings[:-1]]
        verts.append(verts[0])
        for r0, r1 in zip(verts, verts[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat
        return
    ring_loft(bm, rings, mat)


def cylinder(bm, x, y, r, z0, z1, mat, sides=10, ch=0.012):
    """A vertical pin with a chamfered top."""
    rings = []
    for z, rr in ((z0, r), (z1 - ch, r), (z1, r - ch)):
        rings.append([(x + rr * math.cos(2 * math.pi * k / sides), y + rr * math.sin(2 * math.pi * k / sides), z)
                      for k in range(sides)])
    ring_loft(bm, rings, mat)


def chaikin(pts, n=2):
    for _ in range(n):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        out.append(pts[-1])
        pts = out
    return pts


def resample(pts, step):
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(seg)
    n = max(2, int(total / step) + 1)
    out = []
    for k in range(n):
        s = total * k / (n - 1)
        i = 0
        while i < len(seg) - 1 and s > seg[i]:
            s -= seg[i]
            i += 1
        t = s / seg[i] if seg[i] else 0
        a, b = pts[i], pts[i + 1]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out, total


def smooth1(a, n=2):
    for _ in range(n):
        a = [a[0]] + [(a[i - 1] + 2 * a[i] + a[i + 1]) / 4 for i in range(1, len(a) - 1)] + [a[-1]]
    return a


def section(sides, exp, zbot):
    out = []
    for k in range(sides):
        q = 2 * math.pi * (k + 0.5) / sides
        c, s = math.cos(q), math.sin(q)
        cx = math.copysign(abs(c) ** (2 / exp), c)
        cz = math.copysign(abs(s) ** (2 / exp), s)
        if cz < 0:
            cz *= zbot
        out.append((cx, cz))
    return out


def fit_tube(bm, fr, pts, mat, z=0.0, hr=0.6, hmax=0.3, hmin=0.02, wmax=99.0, wmin=0.35, keep=None, exp=2.4,
             sides=16, step=0.3, zbot=0.6, cap=(1.0, 1.0), zfun=None, wscale=1.0, smooth=2, sec=None, taper=False,
             hfun=None):
    """A lofted part along a centreline (pixel-edge coords) whose half-width at each station is measured
    from the frame's inner mask along the perpendicular (both sides, clamped to `wmax` px and to the
    `keep(u, v)` region), so its top view follows the sprite. Superellipse sections (exponent `exp`,
    underside scaled by `zbot`), height hr * width (clamped), rounded end caps `cap` px long."""
    P, total = resample(chaikin(pts), step)
    n = len(P)
    T = []
    for i in range(n):
        a, b = P[max(i - 1, 0)], P[min(i + 1, n - 1)]
        d = math.dist(a, b) or 1
        T.append(((b[0] - a[0]) / d, (b[1] - a[1]) / d))
    L, R = [], []
    for p, t in zip(P, T):
        nrm = (-t[1], t[0])
        ext = []
        for sgn in (1, -1):
            d = 0.0
            while d < wmax:
                q = (p[0] + nrm[0] * sgn * (d + 0.05), p[1] + nrm[1] * sgn * (d + 0.05))
                if not fr.ins(*q) or (keep and not keep(*q)):
                    break
                d += 0.05
            ext.append(d)
        L.append(ext[0])
        R.append(ext[1])
    L, R = smooth1(L, smooth), smooth1(R, smooth)
    if taper:  # a hook or horn: never wider toward its tip than it was behind (no lumps)
        W = [(l + r) / 2 for l, r in zip(L, R)]
        k0 = max(range(n), key=lambda i: W[i])
        for i in range(k0 + 1, n):
            if W[i] > W[i - 1] and W[i] > 0:
                f = W[i - 1] / W[i]
                L[i] *= f
                R[i] *= f
                W[i] = W[i - 1]
    sec = sec or section(sides, exp, zbot)
    rings = []
    s_acc = 0.0
    for i, (p, t) in enumerate(zip(P, T)):
        if i:
            s_acc += math.dist(P[i - 1], P[i])
        w = max(wmin, (L[i] + R[i]) / 2 * wscale)
        off = (L[i] - R[i]) / 2
        nrm = (-t[1], t[0])
        cu, cv = p[0] + nrm[0] * off, p[1] + nrm[1] * off
        f = 1.0
        for d, cl in ((s_acc, cap[0]), (total - s_acc, cap[1])):
            if cl and d < cl:
                f = min(f, math.sqrt(max(0.0, 1 - ((cl - d) / cl) ** 2)))
        zc = zfun(s_acc / total) if zfun else z
        h = max(hmin, min(hmax, hr * w / 12)) * (hfun(s_acc / total) if hfun else 1.0)
        n3 = Vector((nrm[0], -nrm[1], 0)).normalized()
        c3 = P3(cu, cv, zc)
        if f < 1e-3:
            rings.append([tuple(c3)])
            continue
        rings.append([tuple(c3 + n3 * (w / 12 * f * cx) + Vector((0, 0, h * f * cz))) for cx, cz in sec])
    ring_loft(bm, rings, mat)


def mirror_pts(pts, axis):
    return [(2 * axis - u, v) for u, v in pts]


def join_copy(objs, name, coll):
    """A sealed copy of all parts in one mesh (for the outline shell)."""
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def finish(model, frames, parts, coll, out):
    """Tag the parts, add one outline shell for them, collect for export."""
    tmp = join_copy(parts, f"{model}_{frames[0]}_seal", coll)
    bpy.context.view_layer.update()
    shell = common.outline_shell(tmp, coll, **SHELL)
    bpy.data.objects.remove(tmp, do_unlink=True)
    shell.name = f"{model}_{frames[0]}_outline"
    for o in parts + [shell]:
        common.frame_part(o, frames)
        o["tyrian_model"] = model
        out.append(o)


def emis(sprite, idx, tag, strength):
    """A glow (D126/D173): metallic 1, rough, so it reads as its colour, not a reflection."""
    return common.palette_material(sprite, idx, tag, metallic=1.0, roughness=0.9, emission_strength=strength)


# --- newshg-121: grabber-claw drone ----------------------------------------------------------------

def plan_pod(bm, fr, keep, mat, z, h, exp_plan=2.5, exp_prof=3.2, zbot=0.5, grow=1.0, sides=20, rings=7,
             plate=None):
    """An armour pod fitted to one blob of the mask: the blob's centroid and second moments give an
    oriented superellipse plan (exponent `exp_plan`), lofted with a chamfer-like superellipse profile
    (flat top, rounded edge; underside `zbot` as deep). `plate` = (mat, scale, lift): a raised armour
    plate on top (a modelled panel step). Returns (centre uv, axis a uv, axis b uv, radii a, b in px)."""
    pts = [(c + 0.5, r + 0.5) for r in range(fr.h) for c in range(fr.w) if fr.inner[r][c] and keep(c + 0.5, r + 0.5)]
    n = len(pts)
    mu = sum(p[0] for p in pts) / n
    mv = sum(p[1] for p in pts) / n
    suu = sum((p[0] - mu) ** 2 for p in pts) / n + 1 / 12
    svv = sum((p[1] - mv) ** 2 for p in pts) / n + 1 / 12
    suv = sum((p[0] - mu) * (p[1] - mv) for p in pts) / n
    tr, det = suu + svv, suu * svv - suv * suv
    l1 = tr / 2 + math.sqrt(max(0.0, tr * tr / 4 - det))
    l2 = tr / 2 - math.sqrt(max(0.0, tr * tr / 4 - det))
    th = 0.5 * math.atan2(2 * suv, suu - svv)
    au = (math.cos(th), math.sin(th))
    bu = (-math.sin(th), math.cos(th))
    ra, rb = 2 * math.sqrt(l1) * grow, 2 * math.sqrt(l2) * grow

    def ring(scale, zz):
        out = []
        for k in range(sides):
            q = 2 * math.pi * (k + 0.5) / sides
            c, s = math.cos(q), math.sin(q)
            ca = math.copysign(abs(c) ** (2 / exp_plan), c) * ra * scale
            cb = math.copysign(abs(s) ** (2 / exp_plan), s) * rb * scale
            u = mu + ca * au[0] + cb * bu[0]
            v = mv + ca * au[1] + cb * bu[1]
            out.append(tuple(P3(u, v, zz)))
        return out

    rs = []
    for i in range(rings + 1):
        phi = -math.pi / 2 + math.pi * i / rings
        c, s = math.cos(phi), math.sin(phi)
        sc = abs(c) ** (2 / exp_prof)
        zz = z + h * math.copysign(abs(s) ** (2 / exp_prof), s) * (zbot if s < 0 else 1.0)
        rs.append([tuple(P3(mu, mv, zz))] if sc < 1e-4 else ring(sc, zz))
    ring_loft(bm, rs, mat)
    if plate:
        pm, psc, lift = plate
        rs = [ring(psc, z + h * 0.5)]
        for i in range(4):
            phi = math.pi / 2 * i / 3
            c, s = math.cos(phi), math.sin(phi)
            sc = psc * abs(c) ** (2 / 3.5)
            zz = z + h * 0.97 + lift * abs(s) ** (2 / 3.5)
            rs.append([tuple(P3(mu, mv, zz))] if sc < 1e-4 else ring(sc, zz))
        ring_loft(bm, rs, pm)
    return (mu, mv), au, bu, ra, rb


def build_claw(coll, out):
    name = "newshg-121"
    sp = common.load_sprite(WT, name)
    AX = 12.5  # mirror axis (pixel-edge u)
    # frame, model, hook shift toward the middle in px, pearl glow
    # The pearl charges over the frames: a lit pearl with a little glow, low enough that the ball's
    # shading and sheen still show (a pearl, not a flat disc).
    states = [(121, name, 0, 0.0), (123, f"{name}-f2", 1, 0.12), (125, f"{name}-f3", 3, 0.25)]
    for frame, model, sc, glow in states:
        fr = Fr(name, frame)
        # The pearl's colour: its own ramp only (80-95, dark purple to pink-white). Frame 125 has a few
        # pixels of 109 (a grey-blue outside the ramp) that a brightness sort put at the median.
        orb_i = region_index(fr, [v for v in fr.region(9, 15, 1, 7) if 80 <= v <= 95], trim=0.25)
        arm_i = region_index(fr, fr.region(2, 9, 10, 19) + fr.region(15, 22, 10, 19))
        claw_i = region_index(fr, fr.region(2, 10, 20, 26) + fr.region(14, 22, 20, 26))
        mats = [
            common.palette_material(sp, arm_i, model, metallic=0.55, roughness=0.32),        # 0 arm armour
            common.palette_material(sp, 84, model, metallic=0.6, roughness=0.45),            # 1 pins, joints
            common.palette_material(sp, claw_i, model, metallic=0.2, roughness=0.42),        # 2 bone hooks
            common.palette_material(sp, orb_i, model, metallic=0.15, roughness=0.18,
                                    emission_strength=glow),                                 # 3 pearl
            common.palette_material(sp, 86, model, metallic=0.6, roughness=0.38),            # 4 cradle, yoke
            common.palette_material(sp, min(arm_i + 1, 92), model, metallic=0.55, roughness=0.28),  # 5 top plates
        ]
        ARM, PIN, CLAW, ORB, CRADLE, PLATE = range(6)
        bm = bmesh.new()
        # Pearl: a ball in a cradle (rows 1-8, columns 8-16).
        ellipsoid(bm, (X(AX), Y(5.0), 0.16), (4.45 / 12, 4.2 / 12, 0.33), segments=22, rings=11, mat=ORB, bottom=0.7)
        # Cradle under it (rows 5-9, the full 9 px): a low cup lofted from the mask.
        fit_tube(bm, fr, [(AX, 4.6), (AX, 9.9)], CRADLE, z=0.03, hr=0.5, hmax=0.15, wmax=4.7,
                 keep=lambda u, v: 4.5 <= v <= 9.95, exp=3.2, zbot=0.7, cap=(1.5, 0.6), sides=18, smooth=4, step=0.5)
        # A clamp ring round the pearl's waist, seated in the cradle.
        tube3(bm, [(X(AX) + 4.15 / 12 * math.cos(a), Y(5.2) + 3.95 / 12 * math.sin(a), 0.09)
                   for a in (2 * math.pi * k / 28 for k in range(28))], 0.4 / 12, sides=5, mat=CRADLE,
              flat=0.8, closed=True)
        # Yoke: a chamfered bar under the cradle out to the shoulders (rows 9-10).
        fit_tube(bm, fr, [(6.6, 9.6), (25 - 6.6, 9.6)], CRADLE, z=0.0, hr=0.0, hmin=0.075, hmax=0.075,
                 wmax=0.9, keep=lambda u, v: 8.9 <= v <= 10.4, exp=4, zbot=1.0, cap=(0.5, 0.5), wmin=0.6, smooth=4, sides=10,
                 step=0.6)
        for side in (0, 1):
            def M(pts, side=side):
                return pts if side == 0 else mirror_pts(pts, AX)

            def K(lo, hi, side=side):
                if side == 0:
                    return lambda u, v: lo <= v <= hi and u <= AX
                return lambda u, v: lo <= v <= hi and u >= AX
            # Upper and lower armour pods (rows 10-14, 15-19), each with a raised top plate.
            cu, au, bu, ra, rb = plan_pod(bm, fr, K(9.95, 14.95), ARM, 0.02, 0.17, grow=0.98,
                                          plate=(PLATE, 0.62, 0.025))
            cl_, al, bl, ral, rbl = plan_pod(bm, fr, K(14.95, 19.95), ARM, -0.01, 0.17, grow=0.98,
                                             plate=(PLATE, 0.62, 0.025))
            # Bone hook (rows 20-26), curving in; the tip dips.
            cl = [(4.1 + sc, 19.6), (4.4 + sc, 22.0), (5.1 + sc, 24.0), (6.3 + sc, 25.4), (7.9 + sc, 26.0)]
            fit_tube(bm, fr, M(cl), CLAW, hr=0.55, hmax=0.11, wmax=2.4, keep=K(19.7, 27), exp=2.2, cap=(0.6, 0.0),
                     zfun=lambda s: -0.03 - 0.06 * max(0.0, s - 0.5) * 2, zbot=0.8, wmin=0.25, smooth=6,
                     taper=True, sides=12, step=0.45)
            # Hinge pins (vertical axes: the arms close in the XY plane): shoulder at the yoke end,
            # elbow between the pods, wrist above the hook.
            sh = (cu[0] + (1 if side == 0 else -1) * 1.4, 10.2)
            el = ((cu[0] + cl_[0]) / 2, (cu[1] + cl_[1]) / 2 + 0.6)
            wr = (cl_[0], 19.9)
            for (u, v), r, ztop in ((sh, 0.95, 0.12), (el, 1.0, 0.14), (wr, 0.85, 0.08)):
                cylinder(bm, X(u), Y(v), r / 12, -0.09, ztop, PIN)
        parts = [common.mesh_object(model, bm, mats, coll, smooth=True)]
        finish(model, [frame], parts, coll, out)


# --- newshg-127: gimbal eye pod --------------------------------------------------------------------

def build_pod(coll, out):
    name = "newshg-127"
    sp = common.load_sprite(WT, name)
    fr = Fr(name, 129)
    body_i = region_index(fr, fr.region(8, 17, 8, 14))
    mats = [
        common.palette_material(sp, body_i, name, metallic=0.55, roughness=0.3),   # 0 ball
        common.palette_material(sp, 59, name, metallic=0.6, roughness=0.28),       # 1 hoop band
        common.palette_material(sp, 52, name, metallic=0.55, roughness=0.45),      # 2 bosses, socket
        common.palette_material(sp, 49, name, metallic=0.2, roughness=0.08),       # 3 lens
        common.palette_material(sp, 55, name, metallic=0.55, roughness=0.4),       # 4 seam
    ]
    BALL, HOOP, BOSS, LENS, SEAM = range(5)
    CU, CV, R, RZ = 13.0, 14.0, 6.0, 0.40
    cx, cy = X(CU), Y(CV)
    bm = bmesh.new()
    # The ball itself: frame 127 draws it a pixel narrower at its waist (no ink ring, the side
    # gaps transparent), so that frame gets a slightly smaller ball (common.frame_part).
    balls = []
    for frames, rx in (([129, 131], 6.2), ([127], 0)):
        bb = bmesh.new()
        if rx:
            ellipsoid(bb, (cx, cy, 0.0), (rx / 12, (rx - 0.05) / 12, RZ), segments=32, rings=16, mat=BALL)
        else:
            # Lofted down its rows from frame 127's mask: the same ball, its waist a pixel in.
            fit_tube(bb, filled(Fr(name, 127)), [(CU, 7.9), (CU, 20.1)], BALL, hr=0.0, hmin=RZ, hmax=RZ, wmax=6.4,
                     keep=lambda u, v: 6.95 <= u <= 19.05, exp=2.0, zbot=1.0, sides=32, cap=(1.2, 1.2), smooth=1,
                     hfun=lambda t: math.sqrt(max(0.05, 1 - (2 * t - 1) ** 2)))
        o = common.mesh_object(f"{name}-ball-{frames[0]}", bb, mats, coll, smooth=True)
        common.frame_part(o, frames)
        o["tyrian_model"] = name
        balls.append(o)
    # A seam groove ring round the upper hemisphere (machined cap line).
    tube3(bm, [(cx + 4.3 / 12 * math.cos(a), cy + 4.3 / 12 * math.sin(a), RZ * math.sqrt(1 - (4.3 / 6) ** 2) - 0.004)
               for a in (2 * math.pi * k / 40 for k in range(40))], 0.22 / 12, sides=5, mat=SEAM, closed=True)
    # Hoop band over the top in the XZ plane (rows 14-15), ending in the pivot bosses at the sides.
    hv = 14.85
    band = []
    a0 = math.acos(4.4 / 6.25)  # the band dives into the ball 5 px out; a thin axle runs on to the boss
    for k in range(25):
        a = a0 + (math.pi - 2 * a0) * k / 24
        rr = 6.25 / 12
        band.append((cx + rr * math.cos(a), Y(hv), (RZ + 0.012) * math.sin(a)))
    tube3(bm, band, 0.75 / 12, sides=8, mat=HOOP, flat=0.35)
    under = [(cx + 6.22 / 12 * math.cos(a), Y(hv), -(RZ + 0.005) * math.sin(a))
             for a in (a0 + (math.pi - 2 * a0) * k / 24 for k in range(25))]
    tube3(bm, under, 0.7 / 12, sides=8, mat=HOOP, flat=0.35)
    for sgn in (-1, 1):
        # Pivot boss: a short cylinder along X (columns 6 / 19, rows 13-15).
        xa = cx + sgn * (R - 1.0) / 12
        x0 = cx + sgn * 6.05 / 12
        x1 = cx + sgn * 6.95 / 12
        rings = []
        for x, rr in ((xa, 0.2), (x0, 0.2), (x0, 1.45), (x1 - sgn * 0.15 / 12, 1.45), (x1, 1.2)):
            rings.append([(x, Y(14.6) + rr / 12 * math.cos(2 * math.pi * k / 14), rr / 12 * math.sin(2 * math.pi * k / 14))
                          for k in range(14)])
        ring_loft(bm, rings, BOSS)
    parts = [common.mesh_object(name, bm, mats, coll, smooth=True)]

    # The lens turns per frame: (frame, centre u, v).
    eyes = []
    for frame, eu, ev in ((127, 12.9, 17.2), (129, 13.7, 17.0), (131, 14.4, 16.8)):
        ebm = bmesh.new()
        dx, dy = X(eu) - cx, Y(ev) - cy
        nrm = Vector((dx / (R / 12) ** 2, dy / (R / 12) ** 2, 0))
        zz = RZ * math.sqrt(max(0.0, 1 - (dx ** 2 + dy ** 2) / (R / 12) ** 2))
        nrm.z = zz / RZ ** 2
        nrm.normalize()
        base = Vector((cx + dx, cy + dy, zz))
        a = nrm.cross(Vector((0, 0, 1))).normalized()
        b = nrm.cross(a).normalized()

        def ring(r, h, sides=16):
            return [tuple(base + nrm * h + r * (math.cos(2 * math.pi * k / sides) * a + math.sin(2 * math.pi * k / sides) * b))
                    for k in range(sides)]
        # Socket bezel (dark ring) and the lens dome set in it.
        ring_loft(ebm, [ring(2.1 / 12, -0.03), ring(2.1 / 12, 0.012), ring(1.75 / 12, 0.022), ring(1.4 / 12, 0.008)],
                  BOSS, cap_end=False)
        ring_loft(ebm, [ring(1.4 / 12, 0.008), ring(1.25 / 12, 0.02), ring(0.8 / 12, 0.032), [tuple(base + nrm * 0.036)]],
                  LENS)
        o = common.mesh_object(f"{name}-eye-{frame}", ebm, mats, coll, smooth=True)
        common.frame_part(o, [frame])
        o["tyrian_model"] = name
        eyes.append(o)
    tmp = join_copy(parts + balls[:1] + eyes[1:2], f"{name}_seal", coll)
    bpy.context.view_layer.update()
    shell = common.outline_shell(tmp, coll, **SHELL)
    bpy.data.objects.remove(tmp, do_unlink=True)
    shell.name = f"{name}_outline"
    for o in parts + [shell]:
        common.frame_part(o, [127, 129, 131])
        o["tyrian_model"] = name
        out.append(o)
    out.extend(eyes)
    out.extend(balls)


# --- newshg-49: golden stag beetle -----------------------------------------------------------------

def build_beetle(coll, out):
    name = "newshg-49"
    sp = common.load_sprite(WT, name)
    AX = 12.5
    for s, (model, frame) in enumerate(((name, 49), (f"{name}-f2", 51), (f"{name}-f3", 53))):
        fr = Fr(name, frame)
        shell_i = region_index(fr, fr.region(7, 17, 1, 8))
        pron_i = region_index(fr, fr.region(5, 19, 9, 11))
        mand_i = region_index(fr, fr.region(4, 10, 15, 26) + fr.region(14, 20, 15, 26))
        mats = [
            common.palette_material(sp, shell_i, model, metallic=0.6, roughness=0.38),   # 0 elytra
            common.palette_material(sp, pron_i, model, metallic=0.6, roughness=0.4),     # 1 pronotum, head
            common.palette_material(sp, mand_i, model, metallic=0.55, roughness=0.36),   # 2 mandibles, legs
            common.palette_material(sp, 18, model, metallic=0.4, roughness=0.6),         # 3 dark joints, seams
        ]
        ELY, PRO, MAND, DARK = range(4)
        bm = bmesh.new()
        # Elytra (rows 1-8): a ridged dome (low superellipse exponent: a crest down the suture).
        # It rises from the rear tip to its highest just behind the pronotum.
        fit_tube(bm, fr, [(AX, 0.85), (AX, 8.95)], ELY, z=0.04, hr=0.7, hmax=0.36, wmax=6.6,
                 keep=lambda u, v: 0.85 <= v <= 8.95 and (v >= 6.6 or abs(u - AX) <= 5.7), exp=1.8, zbot=0.45,
                 cap=(0.7, 0.4), sides=28, step=0.5, smooth=4, wscale=1.05, hfun=lambda t: 0.45 + 0.55 * math.sin(math.pi * min(1.0, 0.1 + t * 0.75)) ** 0.6)
        # Pronotum shield (rows 9-11), lower, with the mid legs at its sides.
        fit_tube(bm, fr, [(AX, 8.3), (AX, 12.3)], PRO, z=0.03, hr=0.5, hmax=0.22, wmax=5.9,
                 keep=lambda u, v: 8.3 <= v <= 12.2, exp=2.4, zbot=0.5, cap=(0.6, 0.7), sides=20, step=0.3, smooth=3)
        # Head (rows 12-13, to 15 when the mandibles close).
        hend = (14.1, 14.4, 16.0)[s]
        fit_tube(bm, fr, [(AX, 11.8), (AX, hend)], PRO, z=0.0, hr=0.55, hmax=0.17, wmax=4.0,
                 keep=lambda u, v: 11.8 <= v <= hend and abs(u - AX) <= 3.6, exp=2.4, zbot=0.6, cap=(0.4, 0.9), sides=14, step=0.45)
        for side in (0, 1):
            def M(pts, side=side):
                return pts if side == 0 else mirror_pts(pts, AX)

            def K(fn, side=side):
                return (lambda u, v: fn(u, v)) if side == 0 else (lambda u, v: fn(2 * AX - u, v))
            # Mandible: from the head, out and down, curving back in to the tip at the bottom.
            m = [(9.9, 13.4), (8.7 + s * 0.8, 15.4), (7.5 + s, 17.2), (6.6 + s, 19.0), (6.1 + s, 21.0),
                 (6.1 + s, 23.0), (6.5 + s, 24.8), (7.2 + s, 26.1), (8.0 + s, 26.95)]
            fit_tube(bm, fr, M(m), MAND, hr=0.6, hmax=0.12, wmax=2.6, wmin=0.3,
                     keep=K(lambda u, v: v >= 13.2 and u <= AX - 0.6), exp=2.2, cap=(0.5, 0.2), zbot=0.7,
                     zfun=lambda t: -0.02 - 0.05 * t, smooth=4, taper=True, sides=10, step=0.45)
            # Hind leg swept back from under the elytra to the top corner.
            tip = ((3.5, 2.1), (4.4, 2.1), (5.5, 2.1))[s]
            mid = ((5.1, 4.4), (5.7, 4.5), (6.0, 4.6))[s]
            fit_tube(bm, fr, M([(8.4, 7.4), mid, tip]), MAND, hr=0.6, hmax=0.11, wmax=1.8, wmin=0.3,
                     keep=K(lambda u, v: v <= 8.6 and u <= 8.6), exp=2.2, cap=(0.4, 0.3), zbot=0.7,
                     zfun=lambda t: 0.0 + 0.03 * t, smooth=4, taper=True, sides=10, step=0.45)
            # Mid leg: a flat lobe out of the pronotum's side (rows 9-11, columns 4-7).
            fit_tube(bm, fr, M([(8.6, 9.9), (6.4, 10.2), (4.4, 11.3)]), MAND, hr=0.55, hmax=0.09, wmax=1.9, wmin=0.3,
                     keep=K(lambda u, v: 8.7 <= v <= 12.2 and u <= 7.4), exp=2.2, cap=(0.0, 0.6), zbot=0.7,
                     z=0.0, smooth=4, taper=True, sides=10, step=0.3)
            # Joint knuckles where the mandibles meet the head.
            u = 9.8 + s * 0.4
            if side:
                u = 2 * AX - u
            ellipsoid(bm, (X(u), Y(13.9 + s * 0.3), 0.0), (0.9 / 12, 0.9 / 12, 0.05), segments=10, rings=6, mat=DARK)
        parts = [common.mesh_object(model, bm, mats, coll, smooth=True)]
        finish(model, [frame], parts, coll, out)


# --- newshg-77: molten morphing crystal ------------------------------------------------------------

GLOW_LEVEL = {119: 119, 120: 119, 121: 121, 122: 121, 123: 124, 124: 124, 125: 124, 126: 127, 127: 127}
GLOW_STRENGTH = {119: 1.0, 121: 1.15, 124: 1.25, 127: 1.6}


def convex_hull2(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def ray_hull(c, d, hull):
    best = 0.0
    n = len(hull)
    for i in range(n):
        a, b = hull[i], hull[(i + 1) % n]
        ex_, ey_ = b[0] - a[0], b[1] - a[1]
        den = d[0] * ey_ - d[1] * ex_
        if abs(den) < 1e-12:
            continue
        t = ((a[0] - c[0]) * ey_ - (a[1] - c[1]) * ex_) / den
        s = ((a[0] - c[0]) * d[1] - (a[1] - c[1]) * d[0]) / den
        if t > 0 and -1e-9 <= s <= 1 + 1e-9:
            best = max(best, t)
    return best


def mask_centroid(fr):
    pts = [(c + 0.5, r + 0.5) for r in range(fr.h) for c in range(fr.w) if fr.inner[r][c]]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def ray_mask(fr, c, d, rmax=16.0):
    last, r = 0.0, 0.0
    while r < rmax:
        if fr.ins(c[0] + d[0] * r, c[1] + d[1] * r):
            last = r
        r += 0.04
    return last + 0.02


def radial_fit(cos, fr, bins=180, win=3, gain=1.0):
    """Scale the points' XY about the mask centroid so their top-view outline lands on the mask.
    `cos`: the vectors to move in place (a bmesh's v.co, or a point list)."""
    cu, cv = mask_centroid(fr)
    c = (X(cu), Y(cv))
    hull = convex_hull2([(p.x, p.y) for p in cos])
    s = []
    for k in range(bins):
        a = 2 * math.pi * k / bins
        dm = (math.cos(a), -math.sin(a))  # uv direction for the same XY angle (v points down)
        rm = ray_mask(fr, (cu, cv), dm) / 12
        rh = ray_hull(c, (math.cos(a), math.sin(a)), hull)
        s.append(rm / rh if rh > 1e-6 else 1.0)
    sm = [sum(s[(k + j) % bins] for j in range(-win, win + 1)) / (2 * win + 1) for k in range(bins)]
    for p in cos:
        dx, dy = p.x - c[0], p.y - c[1]
        a = math.atan2(dy, dx) % (2 * math.pi)
        f = a / (2 * math.pi) * bins
        i0 = int(f) % bins
        t = f - int(f)
        k = (sm[i0] * (1 - t) + sm[(i0 + 1) % bins] * t) ** gain
        p.x = c[0] + dx * k
        p.y = c[1] + dy * k


def tetra_pts(apex_z=0.42):
    V = P3(12.5, 16.6, apex_z)
    T = P3(12.5, 2.7, -0.22)
    BL = P3(3.7, 22.0, -0.48)
    BR = P3(21.3, 22.0, -0.48)
    return [V, T, BL, BR], [(0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 2, 3)]


def box_pts():
    """A rectangular box seen corner-on: near vertex V and the three edges' top-view ends from the
    sprite (frame 93), their z solved so the edges are mutually perpendicular."""
    V = Vector((X(13.6), Y(10.0)))
    ends = [Vector((X(4.6), Y(6.4))), Vector((X(13.3), Y(21.9))), Vector((X(22.4), Y(6.0)))]
    e = [p - V for p in ends]
    d01, d02, d12 = e[0].dot(e[1]), e[0].dot(e[2]), e[1].dot(e[2])
    z0 = math.sqrt(abs(d01 * d02 / d12))
    z1 = -d01 / z0
    z2 = -d02 / z0
    ez = [z0, z1, z2]
    # all three edges must point away from the camera (down): flip if needed
    sgn = -1 if sum(ez) > 0 else 1
    E = [Vector((e[i].x, e[i].y, sgn * ez[i])) for i in range(3)]
    v = Vector((V.x, V.y, 0.0))
    verts = [v, v + E[0], v + E[1], v + E[2], v + E[0] + E[1], v + E[1] + E[2], v + E[0] + E[2],
             v + E[0] + E[1] + E[2]]
    zmid = (max(p.z for p in verts) + min(p.z for p in verts)) / 2
    for p in verts:
        p.z -= zmid
    faces = [(0, 3, 6, 1), (0, 1, 4, 2), (0, 2, 5, 3), (1, 6, 7, 4), (2, 4, 7, 5), (3, 5, 7, 6)]
    return verts, faces


def hull_cover(fr, pts, grow=0.0, hard=False):
    """Soft IoU of the points' top-view hull (grown `grow` px, for the bevel it loses) against the
    frame's inner mask, 4x4 samples per pixel, the rule's free pixels left out."""
    hull = convex_hull2([(p.x * 12 + 12, 14 - p.y * 12) for p in pts])
    n = len(hull)
    cu = sum(h[0] for h in hull) / n
    cv = sum(h[1] for h in hull) / n
    edges = []
    for a, b in zip(hull, hull[1:] + hull[:1]):
        eu, ev = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(eu, ev) or 1
        nu, nv = ev / ln, -eu / ln  # a normal; point it outward
        if (cu - a[0]) * nu + (cv - a[1]) * nv > 0:
            nu, nv = -nu, -nv
        edges.append((nu, nv, a[0] * nu + a[1] * nv + grow))
    u0, u1 = min(h[0] for h in hull) - grow, max(h[0] for h in hull) + grow
    v0, v1 = min(h[1] for h in hull) - grow, max(h[1] for h in hull) + grow
    inter = uni = 0.0
    sub = (0.125, 0.375, 0.625, 0.875)
    for r in range(fr.h):
        for c in range(fr.w):
            if fr.free[r][c]:
                continue
            m = 1.0 if fr.inner[r][c] else 0.0
            cov = 0.0
            if c + 1 > u0 and c < u1 and r + 1 > v0 and r < v1:
                k = 0
                for su in sub:
                    for sv in sub:
                        u, v = c + su, r + sv
                        if all(u * e[0] + v * e[1] <= e[2] for e in edges):
                            k += 1
                cov = k / 16
                if hard:
                    cov = 1.0 if cov >= 0.5 else 0.0
            inter += min(cov, m)
            uni += max(cov, m)
    return inter / uni if uni else 0.0


def optimise_outline(fr, pts, grow=0.0, steps=(0.4, 0.15, 0.06), hard=False):
    """Move each outline point of the hull in XY (coordinate descent) until the top view covers the
    sprite's inner mask best: a few exact corners instead of a dense radially fitted skin (which
    bent the flat faces into folds)."""
    best = hull_cover(fr, pts, grow, hard)
    for st in steps:
        d = st / 12
        improved = True
        while improved:
            improved = False
            hull = set(convex_hull2([(p.x, p.y) for p in pts]))
            for p in pts:
                if (p.x, p.y) not in hull:
                    continue
                for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
                    p.x += dx
                    p.y += dy
                    sc = hull_cover(fr, pts, grow, hard)
                    if sc > best + 1e-5:
                        best = sc
                        improved = True
                        break
                    p.x -= dx
                    p.y -= dy
    return best


def truncate(verts, faces, f):
    """Cut every corner of the polyhedron `f` of the way along its edges (a truncated solid: the
    crystal on its way to the ball keeps flat faces, with new corner facets)."""
    if f <= 0:
        return [v.copy() for v in verts]
    nb = {i: set() for i in range(len(verts))}
    for fc in faces:
        for k in range(len(fc)):
            a, b = fc[k], fc[(k + 1) % len(fc)]
            nb[a].add(b)
            nb[b].add(a)
    return [verts[i] + (verts[j] - verts[i]) * f for i in sorted(nb) for j in sorted(nb[i])]


def hull_body(bm, pts, chamfer=0.0, bevel=0.012):
    """A hard faceted solid: the convex hull of the points (every face exactly planar, so it shades
    flat with no folds), its edges chamfered (`chamfer`, one flat segment: a cut facet) and then
    machine-bevelled (`bevel`, two segments, a soft highlight line on every edge)."""
    vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = list({g: 0 for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(2.5), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if chamfer:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=chamfer, segments=1, affect="EDGES", clamp_overlap=True)
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2, profile=0.5, affect="EDGES",
                        clamp_overlap=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def body_index(v):
    return 112 if v == 64 else v if 112 <= v <= 118 else None


def facet_paint(bm, fr, slot_body):
    """Each facet one colour: the median of the body pixels (ramp 112-118) under it in the top view,
    the sprite's own shading per facet (D175's facet ramp); glow and the pale spots don't count. Side
    and under faces take the ramp's dark end."""
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        if n.z < 0.12:
            f.material_index = slot_body[113 if n.z > -0.3 else 112]
            continue
        poly = [(v.co.x * 12 + 12, 14 - v.co.y * 12) for v in f.verts]
        us, vs_ = [p[0] for p in poly], [p[1] for p in poly]
        vals = []
        for r in range(max(0, math.floor(min(vs_))), min(fr.h, math.ceil(max(vs_)))):
            for c in range(max(0, math.floor(min(us))), min(fr.w, math.ceil(max(us)))):
                q = (c + 0.5, r + 0.5)
                inside = True
                sgn = 0
                for a, b in zip(poly, poly[1:] + poly[:1]):
                    cr = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
                    if abs(cr) < 1e-9:
                        continue
                    s = 1 if cr > 0 else -1
                    if sgn and s != sgn:
                        inside = False
                        break
                    sgn = s
                if inside:
                    b_ = body_index(fr.idx[r][c])
                    if b_ is not None:
                        vals.append(b_)
        if not vals:
            cc = f.calc_center_median()
            vals = [body_index(fr.at(cc.x + dx / 12, cc.y + dy / 12)) for dx in (-0.6, 0, 0.6) for dy in (-0.6, 0, 0.6)]
            vals = [v for v in vals if v is not None]
        vals.sort()
        f.material_index = slot_body[vals[len(vals) // 2] if vals else 114]


def glow_strokes(fr):
    """The sprite's lava cracks as centrelines: each 8-connected run of glow pixels (119-127) of two
    or more, its pixel centres averaged across its length (principal axis). A compact bright blob is
    the sprite's highlight (sheen, not paint: the material makes that) and is left out.
    Returns [(points uv, glow level, pixel count)]."""
    seen, out = set(), []
    for r in range(fr.h):
        for c in range(fr.w):
            if fr.idx[r][c] not in GLOW_LEVEL or (r, c) in seen:
                continue
            st, comp = [(r, c)], []
            seen.add((r, c))
            while st:
                a, b = st.pop()
                comp.append((b + 0.5, a + 0.5, fr.idx[a][b]))
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        q = (a + da, b + db)
                        if 0 <= q[0] < fr.h and 0 <= q[1] < fr.w and q not in seen and fr.idx[q[0]][q[1]] in GLOW_LEVEL:
                            seen.add(q)
                            st.append(q)
            n = len(comp)
            if n < 2:
                continue
            mu = sum(p[0] for p in comp) / n
            mv = sum(p[1] for p in comp) / n
            suu = sum((p[0] - mu) ** 2 for p in comp) / n + 1 / 12
            svv = sum((p[1] - mv) ** 2 for p in comp) / n + 1 / 12
            suv = sum((p[0] - mu) * (p[1] - mv) for p in comp) / n
            tr, det = suu + svv, suu * svv - suv * suv
            l1 = tr / 2 + math.sqrt(max(0.0, tr * tr / 4 - det))
            l2 = tr - l1
            if n >= 6 and math.sqrt(l1 / l2) < 1.6:
                continue
            th = 0.5 * math.atan2(2 * suv, suu - svv)
            au = (math.cos(th), math.sin(th))
            bins = {}
            for p in comp:
                t = round((p[0] - mu) * au[0] + (p[1] - mv) * au[1])
                bins.setdefault(t, []).append(p)
            pts = []
            for t in sorted(bins):
                ps = bins[t]
                pts.append((sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)))
            if len(pts) < 2:
                pts = [(mu - au[0] * 0.6, mv - au[1] * 0.6), (mu + au[0] * 0.6, mv + au[1] * 0.6)]
            else:  # reach the end pixels' far edges
                for i0, i1 in ((0, 1), (-1, -2)):
                    d = Vector((pts[i0][0] - pts[i1][0], pts[i0][1] - pts[i1][1]))
                    if d.length > 1e-6:
                        d.normalize()
                        pts[i0] = (pts[i0][0] + d.x * 0.4, pts[i0][1] + d.y * 0.4)
            lv = sorted(GLOW_LEVEL[p[2]] for p in comp)
            out.append((pts, lv[len(lv) // 2], n))
    return out


def seam_tubes(vb, bvh, strokes, slot_glow):
    """Each crack a round glowing seam laid into the surface: a tube along the stroke, its centre
    sunk below the crust (only its crown shows, smooth-edged), tapering to its ends."""
    for pts, lv, n in strokes:
        P, total = resample(chaikin(pts, 2), 0.35)
        r0 = (0.55 if lv >= 124 else 0.45) / 12
        rings, radii = [], []
        for k, (u, v) in enumerate(P):
            hit = bvh.ray_cast(Vector((X(u), Y(v), 5.0)), Vector((0, 0, -1)))
            if hit[0] is None:
                continue
            s = k / max(1, len(P) - 1)
            rr = r0 * (0.45 + 0.55 * math.sin(math.pi * s) ** 0.5)
            rings.append(hit[0] - hit[1] * rr * 0.35)
            radii.append(rr)
        if len(rings) >= 2:
            tube3(vb, rings, radii, sides=8, mat=slot_glow[lv])


def build_crystal(coll, out):
    name = "newshg-77"
    sp = common.load_sprite(WT, name)
    groups = {name: [77, 79, 119], f"{name}-f2": [81, 117], f"{name}-f3": [83, 85, 87, 89],
              f"{name}-f4": [91], f"{name}-f5": [93, 115]}
    # frame -> (kind, corner truncation, edge chamfer): kind tetra / box / ball. Truncation 0 is the
    # sharp solid (glowing edge bars from the near corner); above 0 a cut crystal on its way to the
    # ball, flat faces throughout (D-rule: a hard surface changing shape, not a soft blob).
    spec = {77: ("tetra", 0, 0), 79: ("tetra", 0, 0), 119: ("tetra", 0.07, 0.02),
            117: ("tetra", 0.15, 0.035), 81: ("tetra", 0.32, 0.04),
            83: ("ball", 0, 0), 85: ("ball", 0, 0), 87: ("ball", 0, 0), 89: ("ball", 0, 0),
            91: ("box", 0.2, 0.045), 93: ("box", 0, 0), 115: ("box", 0, 0)}
    for model, frames in groups.items():
        body_ids = list(range(112, 119))
        mats = [common.palette_material(sp, i, model, metallic=0.25, roughness=0.36) for i in body_ids]
        slot_body = {i: k for k, i in enumerate(body_ids)}
        slot_glow = {}
        for g in (119, 121, 124, 127):
            slot_glow[g] = len(mats)
            mats.append(emis(sp, g, model, GLOW_STRENGTH[g]))
        for frame in frames:
            fr = Fr(name, frame)
            kind, trunc, chamfer = spec[frame]
            bm = bmesh.new()
            vb = bmesh.new()
            sharp = kind != "ball" and trunc == 0
            if kind == "ball":
                cu, cv = mask_centroid(fr)
                body = [v for v in fr.region(0, fr.w - 1, 0, fr.h - 1) if body_index(v) is not None]
                ball_i = region_index(fr, [body_index(v) for v in body], trim=0.25, ink=False)
                ellipsoid(bm, (X(cu), Y(cv), 0.0), (9.4 / 12, 9.4 / 12, 0.6), segments=36, rings=18,
                          mat=slot_body[ball_i])
                radial_fit([v.co for v in bm.verts], fr)
            else:
                verts, faces = tetra_pts() if kind == "tetra" else box_pts()
                if sharp:
                    pts = verts = [v.copy() for v in verts]
                    if frame == 79:  # its sides bow out a little: a shallow ridge down each face
                        pts += [(verts[i] + verts[j]) / 2 for i, j in ((1, 2), (1, 3))]
                else:
                    pts = truncate(verts, faces, trunc)
                    if kind == "tetra":  # the near base edge shows below the base (a narrow facet)
                        pts += [P3(10.6, 22.6, -0.4), P3(14.4, 22.6, -0.4)]
                        # and the sides bow out as it rounds: a ridge facet down each side face
                        pts += [(verts[i] + verts[j]) / 2 for i, j in ((1, 2), (1, 3))]
                radial_fit(pts, fr, bins=120, win=0)
                optimise_outline(fr, pts, grow=0.0 if sharp else -0.1)
                # then the rule's own measure (a pixel counts when half covered), small steps
                optimise_outline(fr, pts, grow=0.0 if sharp else -0.1, steps=(0.2, 0.08), hard=True)
                hull_body(bm, pts, chamfer=chamfer, bevel=0.014 if sharp else 0.012)
                facet_paint(bm, fr, slot_body)
            if not sharp:
                bm.normal_update()
                seam_tubes(vb, BVHTree.FromBMesh(bm), glow_strokes(fr), slot_glow)
            else:
                # Glowing near edges: bars set into the bevel from the near vertex V to its neighbours,
                # each the median glow level of the sprite along it (none where the sprite shows none).
                V = verts[0]
                low = min(range(len(verts)), key=lambda i: verts[i].z)
                edges = set()
                for fc in faces:
                    for i in range(len(fc)):
                        e = tuple(sorted((fc[i], fc[(i + 1) % len(fc)])))
                        if low not in e or kind == "tetra":
                            edges.add(e)
                for i0, i1 in sorted(edges):
                    A, E = verts[i0], verts[i1]
                    if i1 == 0:
                        A, E = E, A
                    lv = []
                    nrm2 = Vector((-(E - A).y, (E - A).x)).normalized()
                    for q in range(2, 19):
                        p = A + (E - A) * (q / 20)
                        for dd in (-0.5, 0, 0.5):
                            v_ = fr.at(p.x + nrm2.x * dd / 12, p.y + nrm2.y * dd / 12)
                            if v_ in GLOW_LEVEL:
                                lv.append(GLOW_LEVEL[v_])
                    if len(lv) < 10:
                        continue
                    lv.sort()
                    g = lv[len(lv) // 2]
                    near = 0 in (i0, i1)
                    pts_ = [A + (E - A) * (q / 12) for q in range(13)]
                    r0 = 0.65 if near else 0.4
                    rad = [(r0 - (0.3 if near else 0.0) * q / 12) / 12 for q in range(13)]
                    tube3(vb, pts_, rad, sides=8, mat=slot_glow[g])
                # hot knot at V: the brightest glow round its pixel
                vu, vv = V.x * 12 + 12, 14 - V.y * 12
                kn = [GLOW_LEVEL[fr.pal(vu + du, vv + dv)] for du in (-1, 0, 1) for dv in (-1, 0, 1)
                      if fr.pal(vu + du, vv + dv) in GLOW_LEVEL]
                if kn:
                    ellipsoid(vb, tuple(V), (0.9 / 12, 0.9 / 12, 0.045), segments=12, rings=6, mat=slot_glow[max(kn)])
            if kind == "ball":
                body = common.mesh_object(f"{model}-{frame}", bm, mats, coll, smooth=True)
            else:
                body = common.mesh_object(f"{model}-{frame}", bm, mats, coll, smooth=False)
            parts = [body]
            if vb.faces:
                parts.append(common.mesh_object(f"{model}-{frame}-glow", vb, mats, coll, smooth=True))
            else:
                vb.free()
            finish(model, [frame], parts, coll, out)


def main(groups=None):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection("newshg-121")
    out = []
    which = groups or (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    which = [w for w in which if w in ("claw", "pod", "beetle", "crystal")] or ["claw", "pod", "beetle", "crystal"]
    if "claw" in which:
        build_claw(coll, out)
    if "pod" in which:
        build_pod(coll, out)
    if "beetle" in which:
        build_beetle(coll, out)
    if "crystal" in which:
        build_crystal(coll, out)
    # One .glb per model, with its frames' sprite entry (D17, D46).
    models = {}
    for o in out:
        models.setdefault(o["tyrian_model"], []).append(o)
    for model, objs in models.items():
        item = "-".join(model.split("-")[:2])
        sprite = common.load_sprite(WT, item)
        frames = {int(f) for o in objs for f in o["tyrian_frames"]}
        sprites = []
        for s in sprite["sprites"]:
            keep = [f for f in s["frames"] if f in frames]
            if keep:
                sprites.append({**s, "frames": keep})
        common.export_sprite_model(WT, objs, f"enemies/{model}", sprites)


if __name__ == "__main__":
    main()
