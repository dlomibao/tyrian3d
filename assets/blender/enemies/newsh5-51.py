"""Molten fireball (newsh5.shp frame 51, a 24x28 cell, 22 px disc).

What it is: a ball of molten rock flung through the sky (SURFACE's sky-layer weaver, LAVA EXIT).
Airborne, so it is round and closed all over: a sphere of the sprite's inner disc (21 px across
inside its ink ring, D74), not a ground dome.

Reading the sprite (rubric "Reading a sprite"): the black ring is ink. Inside, hot yellow and
orange plates (119-127) parted by a network of thin dark red cracks (112-117). The brightness does
not follow the art's upper-left light (its white-hot 126/127 spots sit lower left and right), so
the plates glow: their colour is their own heat, not lighting.

So: the crust is broken into flat plates (one planar cut per plate, the cuts meeting so the ball is
all plates); each plate is then raised a little on chamfered walls (inset), so between two plates
the walls meet in a V crack. The walls are the dark cracks (rock, matte, lit: dark red 114-116,
rule 2: a lit face, not paint), the plate tops glow in the sprite's own shade under them (D126,
metallic 1 / rough, D173), a narrow chamfer rim round each plate one shade cooler. Plates sit
where the sprite draws its hot patches (local maxima of its shade field), so its cracks fall where
the sprite draws them; the sides and the underside carry the same plates on an even spiral (no
tuning underneath). AO/roughness bake only (no concept projection); D90 outline shell from a
sealed copy kept out of the bake (D118).

    blender -b --factory-startup -P assets/blender/enemies/newsh5-51.py -- [--no-bake] [--out file.glb]
"""

import math
import random
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import lib_newshd_rock as lib  # noqa: E402

NAME = "newsh5-51"
U = 1 / 12  # one sprite px in Blender units

# The inner disc (inside the ink ring): columns 2-22, rows 3-23 (pixel edges 2..23, 3..24).
CU, CV, R = 12.5, 13.5, 10.5
SPACING = 3.3  # plate spacing on the sides and underside, sprite px
TOP_SPACING = 3.0  # minimum spacing of the sprite's own hot patches
JITTER = (0.88, 1.15)  # random scale of each plate's cut radius
COVER = 0.78  # plate cut radius as a share of the distance to the nearest plate (> 0.5: cuts meet)
STEP = (0.0, 0.5)  # extra depth of each plate's cut, px (random): plates step against each other
WALL_T, WALL_D = 0.18, 0.40  # the crack walls: inset width and rise, px
RIM_T, RIM_D = 0.30, 0.10  # the chamfer rim round each plate top, px
CORE_S, CORE_D, CORE_MIN, DOME = 0.5, 0.04, 2.6, 0.06  # hot core: scale of the top, rise, min plate px, dome px
GROW = -0.15  # px the waist is grown past the inner mask (the raised plates push it back out)
SEED = 51
TILT = 3.5  # deg: random lean of each plate's cut
PATCH = 1e9  # px^2 (off: their curved region insets folded inside out; they stay crack): crust islands (gaps the cuts left at a Voronoi corner) bigger than this rise as a plate
DEBUG = '--debug' in sys.argv
SHORT = 0.25  # px: shorter plate edges collapse before the inset
MIN_PLATE = 1.6  # px: plates smaller than this square stay crack
FOLD_DOT = 0.2  # a face this far past tangent toward the ball centre marks its plate as folded
PLANE_DOT, PLANE_TOL = 0.995, 0.05  # a face on its plate's cut (loose: SHORT collapses move corners)
RIM_SHORT = 0.6  # px: raised-top sides shorter than this shut before the rim inset
FOLD = 1.6  # plates whose inradius is under FOLD wall widths stay crack (their inset would fold)
SHADE_Q = 0.6  # quantile of the sprite's hot pixels over a plate that sets the plate's shade
GLOW = 0.9  # D126: share of the plate colour that glows (the rest lit, so the plates still model)
CRACK = (114, 115, 116)  # crack wall shades: deep, mid, upper lip

SPEC = {
    "mid": 122, "metallic": 0.0, "roughness": 0.85,
    "h_top": R * U, "h_bot": R * U, "rise": 1.0, "fall": 1.0, "top_pow": 1.0, "bot_pow": 1.0,
    "summit": (CU, CV), "summit_gain": 0.0, "ridges": [], "tilt": 0.0,
    "lumps": 0.0, "waist": 0.0, "seed": 51, "smooth": 8, "steps": 96, "grow": GROW,
}


def inside(c, r, margin=0.6):
    return math.hypot(c + 0.5 - CU, r + 0.5 - CV) < R - margin


def sprite_seeds(pix):
    """The hot plates the sprite draws: local maxima of its shade field (indices blurred over about
    a pixel), at least TOP_SPACING px apart, inside the disc."""
    H, W = len(pix), len(pix[0])
    f = {}
    for r in range(H):
        for c in range(W):
            if not inside(c, r):
                continue
            s = w = 0.0
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and 112 <= pix[rr][cc] <= 127 and inside(cc, rr, 0.0):
                        g = math.exp(-(dr * dr + dc * dc) / 1.6)
                        s += g * pix[rr][cc]
                        w += g
            f[(c, r)] = s / w
    seeds = []
    for k in sorted(f, key=lambda k: -f[k]):
        if all(math.hypot(k[0] - a, k[1] - b) >= TOP_SPACING for a, b in seeds):
            seeds.append(k)
    dirs = []
    for c, r in seeds:
        x, y = c + 0.5 - CU, CV - (r + 0.5)
        z = math.sqrt(max(R * R - x * x - y * y, 0.0))
        dirs.append(Vector((x, y, z)).normalized())
    return dirs


def spiral_seeds(have):
    """Plates on the sides and underside: an even (Fibonacci) spiral with a little jitter, skipping
    points near a plate the sprite already places."""
    n = int(4 * math.pi * R * R / (SPACING * SPACING * 0.87))
    rnd = random.Random(SEED + 100)
    out = []
    for k in range(n):
        z = 1 - 2 * (k + 0.5) / n
        rho = math.sqrt(1 - z * z)
        a = k * math.pi * (3 - math.sqrt(5)) + 0.7
        d = Vector((rho * math.cos(a), rho * math.sin(a), z))
        d = (d + Vector([rnd.uniform(-1, 1) for _ in range(3)]) * 0.25 * SPACING / R).normalized()
        if all(math.acos(max(-1, min(1, d.dot(e)))) * R > 0.8 * SPACING for e in have + out):
            out.append(d)
    return out


def plates(bm, centre, dirs):
    """Break the crust into flat plates: one planar cut per plate, deep enough that neighbouring
    cuts meet. Returns [(plane co, normal)] per plate."""
    body = BVHTree.FromBMesh(bm)
    rnd = random.Random(SEED)
    planes = []
    for i, n in enumerate(dirs):
        nn = min(math.acos(max(-1, min(1, n.dot(e)))) for j, e in enumerate(dirs) if j != i) * R
        a = COVER * nn * rnd.uniform(*JITTER)  # uneven plates: broken crust, not tiles
        h = R - math.sqrt(max(R * R - a * a, 0.0)) + rnd.uniform(*STEP)
        hit = body.ray_cast(centre, n)
        apex = hit[0] if hit[0] is not None else centre + n * (R * U)
        # a few degrees of tilt so the plates step and lean against each other like broken crust
        t = Vector([rnd.uniform(-1, 1) for _ in range(3)])
        nt = (n + (t - n * t.dot(n)) * math.tan(math.radians(TILT))).normalized()
        planes.append((apex - n * (h * U), nt))
    for co, n in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=n, clear_outer=True)
        cut = [x for x in res["geom_cut"] if isinstance(x, bmesh.types.BMEdge)]
        if cut:
            bmesh.ops.holes_fill(bm, edges=cut, sides=0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    # short seams (three plates nearly meeting at two corners) collapse to one corner, so no plate
    # keeps a sliver side the inset would spike on
    short = [e for e in bm.edges if e.calc_length() < SHORT * U]
    if short:
        bmesh.ops.collapse(bm, edges=short, uvs=False)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return planes


def plate_of(f, planes):
    c = f.calc_center_median()
    for k, (co, n) in enumerate(planes):
        if f.normal.dot(n) > PLANE_DOT and abs((c - co).dot(n)) < PLANE_TOL * U:
            return k
    return -1


def raise_plates(bm, planes, scale=None, centre=None):
    """Each plate stands proud on chamfered walls: the walls of two neighbours meet in a V crack.
    Then a narrow chamfer rim round each top. Face roles go into the int layer `role`
    (0 crack wall / leftover crust, 1 rim, 2 top) and `plate` (plate number). `scale` holds each
    plate's inset thickness factor per stage ("wall", "rim"; 0 = off), cut down where that inset
    folded the plate. Returns the folded (stage, plate) pairs."""
    scale = scale or {"wall": {}, "rim": {}}
    role = bm.faces.layers.int.new("role")
    pl = bm.faces.layers.int.new("plate")

    def inradius(f):
        c = f.calc_center_median()
        return min((c - e.verts[0].co).cross(e.verts[1].co - e.verts[0].co).length / max(e.calc_length(), 1e-9)
                   for e in f.edges) / U

    tops = []
    for f in bm.faces:
        k = plate_of(f, planes)
        f[pl] = k
        f[role] = 0
        # a plate too narrow for its wall inset would fold through itself (top inside out): crack
        if (k >= 0 and scale["wall"].get(k, 1.0) > 0 and len(f.verts) >= 3 and f.calc_area() > (MIN_PLATE * U) ** 2
                and inradius(f) > WALL_T * FOLD):
            tops.append(f)
    if DEBUG:
        crust = [f for f in bm.faces if f[pl] < 0]
        print("DBG crust faces", len(crust), "area px2", round(sum(f.calc_area() for f in crust) / U / U, 2),
              "small plates", [round(f.calc_area() / U / U, 2) for f in bm.faces if f[pl] >= 0 and f not in tops])
        have = {f[pl] for f in tops}
        print("DBG missing plates", [(k, [round(x, 2) for x in n]) for k, (co, n) in enumerate(planes) if k not in have])
        for f in sorted(crust, key=lambda f: -f.calc_area())[:6]:
            print("DBG crust", len(f.verts), round(f.calc_area() / U / U, 2), [round(x / U, 1) for x in f.calc_center_median()])
    # crust islands left between plates: each big one rises as one (curved) plate of its own
    crust = {f for f in bm.faces if f[pl] < 0}
    islands, seen = [], set()
    for f in crust:
        if f in seen:
            continue
        stack, isl = [f], []
        seen.add(f)
        while stack:
            cur = stack.pop()
            isl.append(cur)
            for e in cur.edges:
                for nb in e.link_faces:
                    if nb in crust and nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
        islands.append(isl)
    extra = len(planes)
    for isl in islands:
        if sum(f.calc_area() for f in isl) < PATCH * U * U:
            continue
        res = bmesh.ops.inset_region(bm, faces=isl, thickness=WALL_T * U * 0.7, depth=WALL_D * U,
                                     use_even_offset=True, use_boundary=True)
        for f in res["faces"]:
            f[role], f[pl] = 0, extra
        for f in isl:
            f[role], f[pl] = 2, extra
        extra += 1
    if DEBUG:
        print("DBG crust plates", extra - len(planes))
    centre = Vector((0.0, 0.0, 0.0)) if centre is None else centre
    folds = set()

    def min_turn(f, n0):
        """Smallest sine of the turn at a corner of f (negative: a side runs backwards)."""
        vs = [v.co for v in f.verts]
        out = 1.0
        for i in range(len(vs)):
            a, b = vs[i] - vs[i - 1], vs[(i + 1) % len(vs)] - vs[i]
            out = min(out, a.cross(b).dot(n0) / max(a.length * b.length, 1e-12))
        return out

    def inset(faces, stage, t, d, r):
        """Inset each face on its own with its plate's thickness (scale[stage]); a plate whose top
        turns over or whose new side faces lean toward the ball centre is reported as folded."""
        for f in faces:
            k = f[pl]
            sc = scale[stage].get(k, 1.0)
            n0 = f.normal.copy()
            before = min_turn(f, n0)
            res = bmesh.ops.inset_individual(bm, faces=[f], thickness=t * sc * U, depth=d * U,
                                             use_even_offset=False, use_relative_offset=False)
            f.normal_update()
            for g in res["faces"]:
                g[role], g[pl] = r, k
                g.normal_update()
            concave = min_turn(f, n0) < min(-0.05, before - 0.05)
            bad = concave or f.normal.dot(n0) < 0.5 or any(
                g.normal.dot((g.calc_center_median() - centre).normalized()) < -FOLD_DOT
                for g in res["faces"])
            if bad:
                folds.add((stage, k))

    inset(tops, "wall", WALL_T, WALL_D, 0)
    for f in tops:  # the inset keeps the original face as the inner (raised) one
        f[role] = 2
    # the raised tops own their corners now: shut their short edges (corners to the midpoint, then
    # welded; the tops stay flat and convex) so the rim inset cannot turn a short side over
    moved = set()
    for f in tops:
        for e in f.edges:
            a, b = e.verts
            if e.calc_length() < RIM_SHORT * U and a not in moved and b not in moved:
                a.co = b.co = (a.co + b.co) / 2
                moved.update((a, b))
    if moved:
        bmesh.ops.remove_doubles(bm, verts=list(moved), dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm, edges=[e for e in bm.edges if e.calc_length() < 1e-7], dist=1e-7)
    tops = [f for f in bm.faces if f[role] == 2]
    roomy = [f for f in tops if inradius(f) > RIM_T * 2.2 and scale["rim"].get(f[pl], 1.0) > 0
             and ("wall", f[pl]) not in folds]
    inset(roomy, "rim", RIM_T, RIM_D, 1)
    # the hot core: a smaller face inside each top, a hair proud (the plate swells to its centre)
    big = [f for f in roomy if f.calc_area() > (CORE_MIN * U) ** 2 and inradius(f) > 0.8
           and ("rim", f[pl]) not in folds and f.normal.dot((f.calc_center_median() - centre).normalized()) > 0.5]
    res = bmesh.ops.inset_individual(bm, faces=big, thickness=0.0, depth=0.0,
                                     use_even_offset=False, use_relative_offset=False)
    for f in res["faces"]:
        f[role] = 2
    for f in big:  # shrink the inner copy toward its centre (robust on any convex plate), lift it
        f[role] = 3
        c = f.calc_center_median()
        n = f.normal.copy()
        for v in f.verts:
            v.co = c + (v.co - c) * CORE_S + n * (CORE_D * U)
    # the core domes a little: poke its centre up (sheen rolls over it, rule 2)
    res = bmesh.ops.poke(bm, faces=big, offset=DOME * U, use_relative_offset=False)
    for f in res["faces"]:
        f[role] = 3
    # carry the plate number onto the rims and walls (nearest top by adjacency)
    for f in bm.faces:
        if f[role] < 2:
            best = -1
            for e in f.edges:
                for nb in e.link_faces:
                    if nb[role] >= 2:
                        best = nb[pl]
            if best < 0:
                for e in f.edges:
                    for nb in e.link_faces:
                        if nb is not f and nb[role] == 1:
                            for e2 in nb.edges:
                                for nb2 in e2.link_faces:
                                    if nb2[role] >= 2:
                                        best = nb2[pl]
            f[pl] = best
    # (no recalc: the insets keep the winding; a recalc on the raised mesh can flip it whole)
    if DEBUG:
        cc = Vector((0.0, 1 / 12, 0.0))
        dd = Vector((-1, -1, -1)).normalized()
        near = [f for f in bm.faces if (f.calc_center_median() - cc).normalized().dot(dd) > 0.93]
        print("DBG near", len(near), [(f[role], f[pl], round(f.calc_area() / U / U, 2), round(f.normal.dot(dd), 2)) for f in near])
        for f in sorted([f for f in bm.faces if f[role] < 2], key=lambda f: -f.calc_area())[:8]:
            print("DBG wall", f[role], len(f.verts), round(f.calc_area() / U / U, 2), [round(x / U, 1) for x in f.calc_center_median()], f[pl])
    return folds


def plate_shades(sprite, bm, planes, g):
    """Each plate's palette shade: top plates the median of the sprite's hot pixels (119-127) whose
    centres fall on that plate seen from above; plates the sprite never shows draw from the same
    distribution (seeded), so the sides and underside read alike."""
    pix = [[int(v) for v in r] for r in sprite["frames"][0]["pixels"]]
    bm.faces.ensure_lookup_table()
    role = bm.faces.layers.int["role"]
    pl = bm.faces.layers.int["plate"]
    tmp = bm.copy()
    tmp.faces.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(tmp)
    seen = {}
    for r in range(g.h):
        for c in range(g.w):
            if not g.inner[r][c]:
                continue
            p = Vector((g.x(c + 0.5), g.y(r + 0.5), 5.0))
            hit = bvh.ray_cast(p, Vector((0, 0, -1)))
            if hit[0] is None:
                continue
            f = bm.faces[hit[2]]
            k = f[pl]
            if k < 0:
                continue
            seen.setdefault(k, []).append(pix[r][c])
    tmp.free()
    shade, core = {}, {}
    meds = []
    for k, vals in seen.items():
        hot = sorted(v for v in vals if v >= 119) or sorted(vals)
        if len(vals) < 3:
            continue
        # a little over the median: the denser crack network takes more of each plate's footprint,
        # so the tops carry the sprite's heat a shade hotter to keep its overall median
        m = hot[min(len(hot) - 1, int(len(hot) * SHADE_Q))]
        q = hot[min(len(hot) - 1, int(len(hot) * 0.8))]
        shade[k] = max(119, min(125, m))
        core[k] = min(127, max(shade[k] + 2, q))
        meds.append((shade[k], core[k]))
    rnd = random.Random(SEED + 7)
    for k in range(max([len(planes)] + [f[pl] + 1 for f in bm.faces])):
        if k not in shade:
            shade[k], core[k] = rnd.choice(meds)
    return shade, core


def outward(bm, centre):
    """Wind every face outward, consistently. A face whose normal points back toward the ball centre
    is reversed (per face: a whole-mesh recalc_face_normals flips the raised mesh as a whole); then,
    since a few steep crack walls lean past the radial test, the winding is flooded from the plate
    tops (confidently outward) across every manifold edge so neighbours always run a shared edge
    in opposite directions. common.mesh_object's recalc then keeps it."""
    bad = [f for f in bm.faces if f.normal.dot(f.calc_center_median() - centre) < 0]
    if bad:
        bmesh.ops.reverse_faces(bm, faces=bad)
    bm.normal_update()

    def runs(f, e):
        return next(l.vert for l in f.loops if l.edge is e)

    def score(f):
        return f.normal.dot((f.calc_center_median() - centre).normalized())

    done, flipped = set(), 0
    for seed in sorted(bm.faces, key=lambda f: -score(f)):
        if seed in done:
            continue
        done.add(seed)
        stack, comp = [seed], [seed]
        while stack:
            f = stack.pop()
            for e in f.edges:
                lf = e.link_faces
                if len(lf) != 2:
                    continue
                nb = lf[0] if lf[1] is f else lf[1]
                if nb in done:
                    continue
                if runs(nb, e) is runs(f, e):
                    bmesh.ops.reverse_faces(bm, faces=[nb])
                    flipped += 1
                done.add(nb)
                stack.append(nb)
                comp.append(nb)
    bm.normal_update()
    clash = sum(1 for e in bm.edges if len(e.link_faces) == 2
                and runs(e.link_faces[0], e) is runs(e.link_faces[1], e))
    inward = sum(1 for f in bm.faces if score(f) < 0)
    if DEBUG and "role" in bm.faces.layers.int:
        role, pl = bm.faces.layers.int["role"], bm.faces.layers.int["plate"]
        lean = [f for f in bm.faces if score(f) < 0]
        from collections import Counter
        print("DBG lean roles", Counter(f[role] for f in lean), "plates", Counter(f[pl] for f in lean))
        for f in lean[:12]:
            print("DBG lean", f[role], f[pl], len(f.verts), round(f.calc_area() / U / U, 3), round(score(f), 2),
                  [round(x / U, 1) for x in f.calc_center_median()])
    print(f"outward: reversed {len(bad)} by the centre test, {flipped} by the flood; "
          f"{inward} of {len(bm.faces)} faces lean inward, winding clashes {clash}")
    return clash


def build(sprite, coll):
    g = lib.Grid(sprite, NAME)
    bm, _ = lib.rock_body(g, SPEC, sectors=96, rings_top=24, rings_bot=24)
    pix = [[int(v) for v in r] for r in sprite["frames"][0]["pixels"]]
    top = sprite_seeds(pix)
    dirs = top + spiral_seeds(top)
    centre = Vector((g.x(CU), g.y(CV), 0.0))
    def inward(tag):
        if DEBUG:
            bad = sum(1 for f in bm.faces if f.normal.dot(f.calc_center_median() - centre) < 0)
            print("DBG inward", tag, bad, len(bm.faces))
    inward("body")
    planes = plates(bm, centre, dirs)
    inward("plates")
    # an inset that folds a plate through itself leaves faces facing the ball centre: take that
    # plate off the stage that folded it (core, then rim, then the raise) and raise again
    scale = {"wall": {}, "rim": {}}
    flat = bm
    for attempt in range(6):
        bm = flat.copy()
        folds = raise_plates(bm, planes, scale, centre)
        if not folds:
            break
        for stage, k in folds:  # thinner inset for that plate next time; off after three tries
            sc = scale[stage].get(k, 1.0) * 0.5
            scale[stage][k] = sc if sc > 0.15 else 0.0
        if attempt < 5:
            bm.free()
    flat.free()
    print(f"folded insets: {len(folds)} left; thinned "
          + ", ".join(f"{st} {sorted((k, v) for k, v in scale[st].items())}" for st in scale))
    inward("raised")
    outward(bm, centre)
    inward("outward")
    shade, core = plate_shades(sprite, bm, planes, g)
    role = bm.faces.layers.int["role"]
    pl = bm.faces.layers.int["plate"]

    mats, slot = [], {}

    def mat_for(idx, kind):
        key = (idx, kind)
        if key not in slot:
            if kind == "glow":
                m = common.palette_material(sprite, idx, f"{NAME}-g", metallic=1.0, roughness=0.88,
                                            emission_strength=GLOW)
            elif kind == "rim":
                m = common.palette_material(sprite, idx, f"{NAME}-r", metallic=1.0, roughness=0.8,
                                            emission_strength=0.6)
            else:
                m = common.palette_material(sprite, idx, f"{NAME}-c", metallic=0.0, roughness=0.85,
                                            emission_strength=0.12)
            slot[key] = len(mats)
            mats.append(m)
        return slot[key]

    # crack walls: shade by how far down the wall the face sits (deep at the V, a lip at the top)
    for f in bm.faces:
        k = f[pl]
        if f[role] == 3:
            f.material_index = mat_for(core.get(k, 123), "glow")
        elif f[role] == 2:
            f.material_index = mat_for(shade.get(k, 121), "glow")
        elif f[role] == 1:
            f.material_index = mat_for(max(118, min(120, shade.get(k, 121) - 2)), "rim")
        else:
            f.material_index = mat_for(CRACK[0], "crack")
    bmesh.ops.triangulate(bm, faces=bm.faces[:], ngon_method="BEAUTY")
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    # common.mesh_object runs a whole-mesh recalc_face_normals, which turns this (consistently
    # wound) ball inside out: wind it outward again on the mesh itself
    fix = bmesh.new()
    fix.from_mesh(obj.data)
    outward(fix, centre)
    fix.to_mesh(obj.data)
    fix.free()
    obj.data.update()
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(14))
    # matte stone cracks; F0 low on all (D176: Specular IOR Level)
    for m in mats:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        for key in ("Specular IOR Level", "Specular"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = 0.3
                break
    print(f"plates: {len(top)} from the sprite, {len(dirs) - len(top)} on the spiral; shades "
          f"{sorted(set(shade.values()))} cores {sorted(set(core.values()))}")
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None  # review builds only
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, NAME)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    print(f"{NAME} {len(obj.data.polygons)} triangles, non-manifold edges {open_edges}")
    closed = obj.copy()
    closed.data = obj.data.copy()
    fmt = "AUTO"
    if "--no-bake" not in argv:
        tint, textured = T.TINT, T.TEXTURED
        T.TINT, T.TEXTURED = (1.0, 1.0, 1.0), tuple(range(len(obj.data.materials)))
        try:
            T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"), size=512, samples=64)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{NAME}_")
                # the glTF exporter names an image after its file: save it under the new name too
                if img.filepath_raw:
                    new = str(Path(bpy.path.abspath(img.filepath_raw)).with_name(f"{img.name}.png"))
                    img.save(filepath=new)
                    img.filepath_raw = new
        fmt = "WEBP"
    coll.objects.link(closed)
    shell = common.outline_shell(closed, coll, **lib.D90_SHELL)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    print("shell faces", len(shell.data.polygons))
    if out is not None:
        common.export_glb([obj, shell], out, image_format=fmt)
        print("exported", out)
    else:
        common.export_sprite_model(root, [obj, shell], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
