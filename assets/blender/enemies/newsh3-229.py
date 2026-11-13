"""Molten fireball (newsh3.shp frames 229, 231, 233, 235), design A: a lava bomb of crust plates over a glowing core.

The sprite is a ball of dark red crust split by a net of glowing orange and yellow cracks that shrinks over its
four frames (23, 19, 17 and 13 px across, ink included). In the game it is the hot core a red blob (newsh3-128)
leaves when it dies, and a homing fire projectile. Built as what it is: a solid sphere of molten rock whose
cooled skin has cracked into plates.

- Core: a sphere glowing in the sprite's own crack colours (pal 120 / 122 / 124, chosen per face by the sprite
  pixel above it, so the white-hot seams sit where the sprite draws them).
- Crust: thick curved plates on a spherical Voronoi tiling. On the top the plate seeds are fitted to the sprite:
  started at the hearts of its dark cells and moved (a seeded hill climb) until the Voronoi seams overlay the
  sprite's hot pixels best; plates in a hotter cell retreat further, opening a wider molten seam. The underside
  takes an even Fibonacci tiling (a plausible closed shape only). Each plate is a closed slab: a gently domed cap
  in the sprite's crust index under it (median, 114..118), a chamfered rim catching the glow (pal 118, ember),
  and walls that run hotter towards the core (pal 119 over pal 121), so each seam grades red > orange > yellow
  as the sprite's do. No pixel plates: the sprite only places the seams and picks the colours.
- Outline shell: from a sealed sphere just inside the plates' tops, so the ink rings the silhouette only and never
  draws in the seams (D51, D90/D118, islands="outer" D189).
- Glow: metallic 1 / rough 0.9 with the D126 strengths (<= 1 for the reds and oranges).

Each frame is its own model (newsh3-229, -f2, -f3, -f4), all concentric on the sprite's centre (11.5, 13.5).

Run: blender --background --python assets/blender/enemies/newsh3-229.py -- [--review DIR]
  (--review writes review renders and stats; otherwise only the game exports are written.)
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve()
ROOT = next(p for p in HERE.parents if (p / "package.json").exists() and (p / "assets" / "blender").exists())
sys.path.insert(0, str(ROOT / "assets" / "blender"))
import common  # noqa: E402

NAME = "newsh3-229"
W, H = 24, 28
PX = 1 / 12

# Shape, in sprite px (scaled by the ball's radius where noted).
GAP = 1.0  # seam between two plates' rims at the top surface, px
CRACK_W = 0.9  # seam width the seed fit aims for, px (rasterised Voronoi seam)
RC = 0.5  # corner rounding of a plate (offset radius), px
CH_W = 0.3  # chamfer width, px
CH_H = 0.28  # chamfer drop, px
BULGE = 0.22  # cap dome over the sphere, px
THICK = 0.11  # plate thickness as a share of the radius (the core sits this far down)
HOT_EXTRA = 1.2  # extra retreat of a plate whose sprite cell is all hot, px
HOT = 120  # sprite index from which a pixel is a glowing seam
INK_LUMA = 26


# --------------------------------------------------------------------------------------------------
# Reading the sprite
# --------------------------------------------------------------------------------------------------

def analyse(sprite, frame):
    a = np.array(frame["pixels"])
    op = a >= 0
    cols = np.nonzero(op.any(0))[0]
    rows = np.nonzero(op.any(1))[0]
    cx = (cols[0] + cols[-1] + 1) / 2
    cy = (rows[0] + rows[-1] + 1) / 2
    # inner mask: opaque minus the ink ring (dark and 4-adjacent to the outside), as tools/sprite_mask.py
    luma = np.zeros(a.shape)
    for k, (r, g, b) in sprite["colors"].items():
        luma[a == int(k)] = 0.299 * r + 0.587 * g + 0.114 * b
    pad = np.pad(op, 1)
    outside_n = (~pad[:-2, 1:-1]) | (~pad[2:, 1:-1]) | (~pad[1:-1, :-2]) | (~pad[1:-1, 2:])
    ink = op & outside_n & (luma < INK_LUMA)
    inner = op & ~ink
    # fit the radius to the inner mask (supersampled disc IoU)
    ss = 8
    yy, xx = np.mgrid[0:a.shape[0] * ss, 0:a.shape[1] * ss]
    d = np.hypot((xx + 0.5) / ss - cx, (yy + 0.5) / ss - cy)
    big = np.kron(inner, np.ones((ss, ss), bool))
    best = None
    r_out = (cols[-1] + 1 - cols[0]) / 2
    for r in np.arange(r_out - 2.0, r_out + 0.01, 0.05):
        disc = d <= r
        iou = (disc & big).sum() / (disc | big).sum()
        if best is None or iou > best[0]:
            best = (iou, r)
    return {"a": a, "cx": cx, "cy": cy, "R": float(best[1]), "inner": inner, "disc_iou": float(best[0])}


def to_dir(u, v):
    """Top-view point (in radii from the centre, v down) to a point on the unit sphere's upper half."""
    r = math.hypot(u, v)
    if r > 0.985:
        u, v = u * 0.985 / r, v * 0.985 / r
    return np.array([u, v, math.sqrt(max(0.0, 1 - u * u - v * v))])


def fit_seeds(info, rng):
    """Plate seeds on the top half, fitted so the spherical Voronoi seams overlay the sprite's hot pixels."""
    a, cx, cy, R = info["a"], info["cx"], info["cy"], info["R"]
    Hh, Ww = a.shape
    yy, xx = np.mgrid[0:Hh, 0:Ww]
    pu = (xx + 0.5 - cx) / R
    pv = (yy + 0.5 - cy) / R
    rho = np.hypot(pu, pv)
    inside = rho < 0.97
    hot = (a >= HOT) & inside
    crust = inside & ~hot
    # distance of each crust pixel to the nearest hot pixel (or the limb)
    ys, xs = np.nonzero(~crust)
    dist = np.sqrt((yy[..., None] - ys) ** 2 + (xx[..., None] - xs) ** 2).min(-1)
    sep = max(2.6, R * 0.33)
    seeds = []
    for k in np.argsort(-dist.ravel(), kind="stable"):
        y, x = divmod(int(k), Ww)
        if not crust[y, x] or dist[y, x] < 0.9:
            continue
        if all((x - sx) ** 2 + (y - sy) ** 2 >= sep ** 2 for sx, sy in seeds):
            seeds.append((x, y))
    S = np.array([to_dir((x + 0.5 - cx) / R, (y + 0.5 - cy) / R) for x, y in seeds])
    P = np.stack([pu, pv, np.sqrt(np.clip(1 - rho ** 2, 0, 1))], -1)[inside]
    HOTm = hot[inside]
    width = CRACK_W / R

    def score(S):
        dots = np.clip(P @ S.T, -1, 1)
        srt = np.sort(dots, 1)
        g = np.arccos(srt[:, -2]) - np.arccos(srt[:, -1])
        crack = g < width
        return (crack & HOTm).sum() / max(1, (crack | HOTm).sum())

    best = score(S)
    for _ in range(3000):
        T = S.copy()
        i = rng.integers(len(T))
        T[i, :2] += rng.normal(0, 0.6 / R, 2)
        T[i] /= np.linalg.norm(T[i])
        if T[i, 2] < 0.12:
            continue
        sc = score(T)
        if sc >= best:
            best, S = sc, T
    # per seed: share of hot pixels in its cell, and the crust index median (lighting trimmed)
    owner = np.argmax(P @ S.T, 1)
    idx = a[inside]
    heat, crust_idx = [], []
    for i in range(len(S)):
        m = owner == i
        heat.append(float(HOTm[m].mean()) if m.any() else 0.0)
        c = idx[m & ~HOTm]
        # the cell's crust shade: its lower-middle tone (35th percentile), so the lit game render keeps
        # the sprite's deep maroon cells instead of washing them to a flat bright red (D175 lesson)
        crust_idx.append(int(np.clip(np.percentile(c, 35), 113, 117)) if len(c) else 115)
    return S, heat, crust_idx, float(best)


def fib_seeds(n, top, min_ang):
    pts = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        w = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - w * w)
        p = np.array([r * math.cos(ga * i), r * math.sin(ga * i), w])
        if w > -0.08:
            continue
        if len(top) and np.max(top @ p) > math.cos(min_ang):
            continue
        pts.append(p)
    return np.array(pts)


# --------------------------------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------------------------------

def clip(poly, a, b, off):
    """Keep the part of convex `poly` where a.(u,v) + b >= off."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp = a[0] * p[0] + a[1] * p[1] + b - off
        fq = a[0] * q[0] + a[1] * q[1] + b - off
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def basis(s):
    up = np.array([0.0, 0.0, 1.0]) if abs(s[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(up, s)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(s, e1)
    return e1, e2


def cell_poly(i, seeds, inset):
    """Inset spherical Voronoi cell of seed i, in its gnomonic plane: convex polygon (CCW) or None."""
    s = seeds[i]
    e1, e2 = basis(s)
    poly = [(-3.0, -3.0), (3.0, -3.0), (3.0, 3.0), (-3.0, 3.0)]
    for j, t in enumerate(seeds):
        if j == i or s @ t < 0.0:
            continue
        n = s - t
        a = (float(n @ e1), float(n @ e2))
        b = float(n @ s)
        la = math.hypot(*a)
        poly = clip(poly, a, b, inset * la)
        if len(poly) < 3:
            return None, e1, e2
    clean = []
    for p in poly:
        if not clean or math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 1e-6:
            clean.append(p)
    if len(clean) > 2 and math.hypot(clean[0][0] - clean[-1][0], clean[0][1] - clean[-1][1]) < 1e-6:
        clean.pop()
    if len(clean) < 3:
        return None, e1, e2
    area = sum(clean[k][0] * clean[k - 1][1] - clean[k - 1][0] * clean[k][1] for k in range(len(clean)))
    if area > 0:  # make it CCW
        clean.reverse()
    return clean, e1, e2


def outline_params(Q, m):
    """Parametrise Q (+) disc(r): per sample (vertex, outward unit normal); the ring at r is v + r n."""
    out = []
    n = len(Q)
    for k in range(n):
        p0, p1, p2 = Q[k - 1], Q[k], Q[(k + 1) % n]
        din = (p1[0] - p0[0], p1[1] - p0[1])
        dout = (p2[0] - p1[0], p2[1] - p1[1])
        nin = math.atan2(-din[0], din[1])
        nout = math.atan2(-dout[0], dout[1])
        dturn = (nout - nin + math.pi) % (2 * math.pi) - math.pi
        # outward normals of a CCW polygon are (dy, -dx); we use (-dx, dy) rotated: check orientation below
        for t in range(m):
            ang = nin + dturn * (t / (m - 1) if m > 1 else 0.5)
            out.append((p1, (math.cos(ang), math.sin(ang))))
    return out


def plate(bm, seed, Q, e1, e2, rings_spec, mats, under):
    """One crust plate: closed slab. rings_spec: list of (r_offset, radius, t_center) bottom to top."""
    m = 2 if under else 3
    params = outline_params(Q, m)
    cu = sum(p[0] for p in Q) / len(Q)
    cv = sum(p[1] for p in Q) / len(Q)
    # orientation check: the normal must point away from the centroid
    p, nrm = params[0]
    if (p[0] - cu) * nrm[0] + (p[1] - cv) * nrm[1] < 0:
        params = [(p, (-nn[0], -nn[1])) for p, nn in params]

    def lift(u, v, rad):
        d = seed + u * e1 + v * e2
        d = d / np.linalg.norm(d)
        return d * rad

    rings = []
    for roff, rad, tc in rings_spec:
        ring = []
        for (pp, nn) in params:
            u = pp[0] + roff * nn[0]
            v = pp[1] + roff * nn[1]
            if tc:
                u = cu + (u - cu) * (1 - tc)
                v = cv + (v - cv) * (1 - tc)
            ring.append(bm.verts.new(tuple(lift(u, v, rad))))
        rings.append(ring)
    n = len(params)
    faces = []
    for k in range(len(rings) - 1):
        r0, r1 = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mats[k]
            f.smooth = mats[k] == mats[-1]
            faces.append(f)
    return rings, faces


def build_frame(sprite, frame, coll, rng):
    info = analyse(sprite, frame)
    R = info["R"]  # px
    top, heat, crust_idx, fit = fit_seeds(info, rng)
    sep_ang = max(2.6, R * 0.33) / R
    n_fib = max(12, int(round(len(top) * 2.3)))
    bot = fib_seeds(n_fib, top, sep_ang * 0.8)
    seeds = np.concatenate([top, bot]) if len(bot) else top
    heat = heat + [0.0] * len(bot)
    crust_idx = crust_idx + [114] * len(bot)

    tag = frame_name(frame)
    pal = lambda i, part, **kw: common.palette_material(sprite, i, f"{tag}_{part}", **kw)  # noqa: E731
    caps = sorted(set(crust_idx))
    mats = [
        pal(124, "wall_lo", metallic=1.0, roughness=0.9, emission_strength=1.0),
        pal(122, "wall_hi", metallic=1.0, roughness=0.9, emission_strength=1.0),
        pal(118, "rim", metallic=0.1, roughness=0.8, emission_strength=0.3),
        pal(122, "core_red", metallic=1.0, roughness=0.9, emission_strength=1.0),
        pal(124, "core_orange", metallic=1.0, roughness=0.9, emission_strength=1.0),
        pal(125, "core_hot", metallic=1.0, roughness=0.9, emission_strength=1.0),
    ]
    cap_slot = {}
    for c in caps:
        cap_slot[c] = len(mats)
        mats.append(pal(c, "cap", metallic=0.0, roughness=0.95, emission_strength=0.0))

    Rp = R * PX  # unit radius of the plates' tops
    Rc = Rp * (1 - THICK)
    # seams scale down with the ball (the sprite's seams stay 1-2 px but cover the same share of it)
    small = min(1.0, max(0.6, R / 10.55))
    gap = GAP * small / R / 2  # retreat from the bisector, angle
    bm = bmesh.new()
    n_plates = 0
    for i, s in enumerate(seeds):
        under = s[2] < -0.08
        inset = gap + (RC / R) + HOT_EXTRA * small / R * max(0.0, heat[i] - 0.35) / 0.65
        Q = None
        for shrink in (1.0, 0.6, 0.3):
            Q, e1, e2 = cell_poly(i, seeds, inset * shrink)
            if Q is not None:
                break
        if Q is None:
            continue
        rc = RC / R
        cw = CH_W / R
        bul = BULGE * PX
        cap = cap_slot.get(crust_idx[i], cap_slot[caps[0]]) if not under else cap_slot.get(114, len(mats) - 1)
        if under:
            spec = [(rc, Rc - 0.4 * PX, 0), (rc, Rp - CH_H * PX, 0), (rc - cw, Rp, 0), (rc - cw, Rp + bul, 0.6)]
            mi = [1, 2, cap]
        else:
            spec = [(rc, Rc - 0.4 * PX, 0), (rc, (Rc + Rp) / 2, 0), (rc, Rp - CH_H * PX, 0), (rc - cw, Rp, 0),
                    (rc - cw, Rp + bul * 0.6, 0.35), (rc - cw, Rp + bul * 0.92, 0.75)]
            mi = [0, 1, 2, cap, cap]
        # each plate a separate slab: a small height step (sprite px) so neighbours catch the light apart
        jit = float(rng.uniform(-0.12, 0.12)) * PX
        spec = [(ro, rad + (jit if rad >= Rp - CH_H * PX - 1e-9 else 0.0), tc) for ro, rad, tc in spec]
        rings, _ = plate(bm, s, Q, e1, e2, spec, mi, under)
        # caps: fan the top, close the bottom
        topring = rings[-1]
        cvert = bm.verts.new(tuple(lift_c(s, Q, e1, e2, Rp + bul + jit)))
        for k in range(len(topring)):
            f = bm.faces.new((topring[k], topring[(k + 1) % len(topring)], cvert))
            f.material_index = cap
            f.smooth = True
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = 1
        n_plates += 1

    # core sphere
    core = bmesh.new()
    bmesh.ops.create_uvsphere(core, u_segments=28, v_segments=14, radius=Rc)
    a = info["a"]
    for f in core.faces:
        c = f.calc_center_median()
        d = Vector(c).normalized()
        slot = 3
        if d.z > 0.05:
            # sprite pixel above: max over the pixel and its 4-neighbours (the seam's peak)
            x = info["cx"] + d.x * R
            y = info["cy"] + d.y * R
            vals = []
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                xi, yi = int(math.floor(x + dx * 0.6)), int(math.floor(y + dy * 0.6))
                if 0 <= yi < a.shape[0] and 0 <= xi < a.shape[1] and a[yi, xi] >= 0:
                    vals.append(int(a[yi, xi]))
            v = max(vals) if vals else 0
            slot = 5 if v >= 124 else 4 if v >= 121 else 3
        f.material_index = slot
        f.smooth = True
    me = bpy.data.meshes.new("tmpcore")
    core.to_mesh(me)
    core.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)

    # sprite (u right, v down, w up) -> Blender (x right, y up, z up), centred on the sprite's centre
    ox, oy = (info["cx"] - W / 2) * PX, (H / 2 - info["cy"]) * PX
    for v in bm.verts:
        x, y, z = v.co
        v.co = Vector((ox + x, oy - y, z))
    # the v-flip mirrors the plates; recalc normals per closed piece
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    name = frame_name(frame)
    obj = common.mesh_object(name, bm, mats, coll, smooth=None)

    # outline shell from a sealed sphere just inside the plates' tops (ink on the silhouette only)
    sb = bmesh.new()
    bmesh.ops.create_uvsphere(sb, u_segments=40, v_segments=20, radius=Rp - 0.08 * PX)
    for v in sb.verts:
        v.co = Vector((ox + v.co.x, oy + v.co.y, v.co.z))
    sealed = common.mesh_object(name + "_sealed", sb, [], coll, smooth=True)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sealed, coll, voxel=0.008, faces=800, islands="outer")
    shell.name = shell.data.name = f"{name}_outline"
    bpy.data.objects.remove(sealed, do_unlink=True)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    stats = {"R_px": round(R, 3), "disc_iou": round(info["disc_iou"], 4), "seed_fit_iou": round(fit, 3),
             "plates": n_plates, "top_seeds": int(len(top)), "tris": tris,
             "shell_tris": sum(len(p.vertices) - 2 for p in shell.data.polygons),
             "cap_pals": caps}
    print(name, json.dumps(stats))
    return obj, shell, stats


def lift_c(s, Q, e1, e2, rad):
    cu = sum(p[0] for p in Q) / len(Q)
    cv = sum(p[1] for p in Q) / len(Q)
    d = s + cu * e1 + cv * e2
    return d / np.linalg.norm(d) * rad


def frame_name(frame):
    i = {229: 0, 231: 1, 233: 2, 235: 3}[frame["index"]]
    return NAME if i == 0 else f"{NAME}-f{i + 1}"


# --------------------------------------------------------------------------------------------------
# Review renders (only with --review)
# --------------------------------------------------------------------------------------------------

def review(obj, shell, out):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rev")
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o is not obj
    eng = None
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = e
            eng = e
            break
        except TypeError:
            pass
    if "sun" not in bpy.data.objects:
        sd = bpy.data.lights.new("sun", "SUN")
        sd.energy = 3.0
        sun = bpy.data.objects.new("sun", sd)
        scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(15))
        scene.world.use_nodes = True
        bgn = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
        bgn.inputs[0].default_value = (0.06, 0.065, 0.075, 1)
        bgn.inputs[1].default_value = 3.0
    sh = scene.display.shading
    for c in [o for o in bpy.data.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(c, do_unlink=True)

    def cam(loc, look, ortho=None, lens=50, rx=600, ry=600, rot=None):
        d = bpy.data.cameras.new("cam")
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        d.clip_end = 500
        o = bpy.data.objects.new("cam", d)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = rot if rot else (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = o
        scene.render.resolution_x, scene.render.resolution_y = rx, ry

    def shot(path, flat=False, transparent=False):
        if not flat and eng:
            scene.render.engine = eng
        else:
            scene.render.engine = "BLENDER_WORKBENCH"
            sh.light = "FLAT"
            sh.color_type = "MATERIAL"
            sh.show_cavity = False
            sh.show_object_outline = False
            sh.show_specular_highlight = False
        scene.render.film_transparent = transparent
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    k = 20
    centre = Vector((-0.5 * PX, 0.5 * PX, 0))
    cam((0, 0, 40), (0, 0, 0), ortho=max(W, H) / 12, rx=W * k, ry=H * k, rot=(0, 0, 0))
    shot(out / "top_mask.png", flat=True, transparent=True)
    shot(out / "top_lit.png", transparent=True)
    big = 26 / 12
    for nm, loc in (("side", (60, 0, 0)), ("front", (0, -60, 0)), ("rear", (0, 60, 0))):
        cam(centre + Vector(loc), centre, ortho=big, rx=400, ry=400)
        shot(out / f"{nm}.png")
    dd = big * 2.6
    for nm, az, el in (("q_high", -35, 45), ("q_low", 140, 22)):
        a, e = math.radians(az), math.radians(el)
        cam(centre + Vector((dd * math.cos(e) * math.sin(a), -dd * math.cos(e) * math.cos(a), dd * math.sin(e))),
            centre, rx=400, ry=400)
        shot(out / f"{nm}.png")
    t = math.radians(32)
    cam(centre + Vector((0, -dd * math.sin(t), dd * math.cos(t))), centre, rx=400, ry=400)
    shot(out / "game.png")
    cam(centre + Vector((0, 0, -40)), centre, ortho=big, rx=300, ry=300, rot=(math.pi, 0, 0))
    shot(out / "under.png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    rv = Path(argv[argv.index("--review") + 1]) if "--review" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    rng = np.random.default_rng(229)
    stats, built = {}, []
    for frame in sprite["frames"]:
        name = frame_name(frame)
        coll = common.reset_collection(name)
        obj, shell, st = build_frame(sprite, frame, coll, rng)
        stats[name] = st
        built.append((name, obj, shell))
        common.export_sprite_model(ROOT, [obj, shell], f"enemies/{name}", [{**base, "frames": [frame["index"]]}])
    if rv:  # review renders and stats only behind --review (D190)
        for name, obj, shell in built:
            review(obj, shell, rv / name)
        (rv / "stats.json").write_text(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
