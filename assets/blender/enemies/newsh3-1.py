"""newsh3-1, the grey horned diver (newsh3.shp frame 1, 24x28, one frame).

What it is: a fast swarm diver (armour 6, ~50 spawns in SURFACE 4.4, harness main=2; sky layer, dives down
the screen at (0,+3)..(0,+4) px/tick). Built as a craft flying toward the screen bottom (-Y in
Blender, +y in sprite rows):

  - a round armoured nose body (rows 15-26): two dark satin sensor domes (pal 4) side by side,
    split by a dark keel channel (pal 3), seated in a horseshoe fender (pal 7) that runs down both
    flanks and wraps round the bow into two jaw tips flanking a dark front intake (pal 2; the
    sprite's 2 px notch at row 26 is the intake slot);
  - a transverse wing spar (rows 9-14, pal 6) with a sloped, shadowed leading face (the dark row
    14), its ends chamfered as the sprite steps in at rows 13-14;
  - two tail prongs (rows 0-14, pal 5) rising from the spar's ends and trailing aft to points: a
    wedge section with its crest on the inboard edge, leaning in (the sprite's lit inner strips
    are sheen on that crest, art rule 2), each with a modelled seam and a crest strake;
  - a vented engine block between the prongs (rows 3-13, pal 7): rear louvre deck with two
    transverse slots (rows 4 and 6, pal 3), a crosswise ridge (the bright row 8: sheen on it), a
    forward grille (rows 10-11) and two exhaust nozzles on the rear face.

The sprite has no ink border (its ring is palette 18, luma 28 > 26), so the top view covers every
opaque pixel (D74 inner = outer); the gaps at columns 8 and 15 (rows 0-8) stay open.

Run: blender --background --python assets/blender/enemies/newsh3-1.py [-- --out review.glb]
Without --out it exports public/models/enemies/newsh3-1.glb and its spriteModels entry.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve()


def argv_opt(name, default=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return argv[argv.index(name) + 1] if name in argv else default


def find_repo():
    r = argv_opt("--repo")
    if r:
        return Path(r).resolve()
    for p in HERE.parents:
        if (p / "package.json").exists() and (p / "assets" / "blender").exists():
            return p
    raise SystemExit("repo not found: pass -- --repo <worktree>")


ROOT = find_repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newsh3-1"
TAG = "newsh3-1"

# Material slots and their palette index (median of each part's sprite pixels, darkest/brightest
# left out as lighting): prongs 5, spar 6, block and fender 7, domes 4, slots/keel 3, intake 2.
PRONG, SPAR, BLOCK, FENDER, DOME, SLOT, INTAKE, HULL = range(8)
PAL = {PRONG: 5, SPAR: 6, BLOCK: 7, FENDER: 7, DOME: 4, SLOT: 3, INTAKE: 2, HULL: 6}
# (metallic, roughness, Specular IOR Level): satin gunmetal; domes glossier (sheen, not paint).
FINISH = {PRONG: (0.3, 0.3, 0.85), SPAR: (0.3, 0.36, 0.7), BLOCK: (0.3, 0.32, 0.8),
          FENDER: (0.3, 0.3, 0.85), DOME: (0.25, 0.18, 1.0), SLOT: (0.2, 0.7, 0.3),
          INTAKE: (0.2, 0.75, 0.25), HULL: (0.3, 0.34, 0.75)}


# --- generic geometry (sprite px: x = column - 12, y = row edge, z up) ----------------------------

def centroid(pts):
    n = len(pts)
    return tuple(sum(p[i] for p in pts) / n for i in range(3))


def loft(part, rings, mat, cap0=True, cap1=True, matf=None):
    """Bridge rings (lists of (x, y, z), equal length or single-point tips). matf(k, i) -> slot."""
    vr = [[part.v(p) for p in r] for r in rings]
    n = max(len(r) for r in rings)
    for k in range(len(rings) - 1):
        a, b = vr[k], vr[k + 1]
        away = centroid(rings[k] + rings[k + 1])
        for i in range(n):
            j = (i + 1) % n
            m = matf(k, i) if matf else mat
            if len(a) == 1:
                part.f([a[0], b[i], b[j]], m, away=away)
            elif len(b) == 1:
                part.f([a[i], a[j], b[0]], m, away=away)
            else:
                part.f([a[i], a[j], b[j], b[i]], m, away=away)
    if cap0 and len(vr[0]) > 1:
        part.f(vr[0], mat, away=centroid(rings[1]))
    if cap1 and len(vr[-1]) > 1:
        part.f(vr[-1], mat, away=centroid(rings[-2]))


def box(part, x0, x1, y0, y1, z0, z1, mat, ch=0.2, chz=None):
    T.hull(part, T.cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


def mirror(rings):
    return [[(-x, y, z) for x, y, z in r] for r in rings]


def superellipse(cx, cz, hw, ht, hb, n=20, e=2.6, eb=2.2):
    """(x, z) points round a section, top half exponent e, bottom eb."""
    out = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        c, s = math.cos(a), math.sin(a)
        ee = e if s >= 0 else eb
        x = cx + hw * math.copysign(abs(c) ** (2 / ee), c)
        z = cz + (ht if s >= 0 else hb) * math.copysign(abs(s) ** (2 / ee), s)
        out.append((x, z))
    return out


# --- parts -----------------------------------------------------------------------------------------

def prong_outer(y):
    """The prong's outboard edge (x < 0) down the rows: the sprite's stair midline, then the spar."""
    xs = [0.0, 1.0, 2.0, 4.0, 6.0, 8.0, 12.9, 13.6, 14.6]
    vs = [-4.75, -6.35, -7.55, -8.75, -9.85, -10.95, -10.95, -10.2, -9.2]
    return T.pchip(xs, vs)(y)


def prong_section(y, inset=0.0):
    """Left prong at row edge y (x, y, z) going round: the inboard face leans in to a flat crest
    strip (lit from above: the sprite's light inner strips are sheen on it), a seam step, then the
    outboard flank falls steeply to a thin outer edge (the sprite's darker outer half)."""
    xo = prong_outer(y)
    t = min(1.0, max(0.0, (y - 0.15) / 12.5))
    tip = min(1.0, (y - 0.1) / 2.4)
    zc = 1.6 + 3.5 * (t ** 0.7)                        # crest height: 1.6 at the tip, 5.1 at the root
    zc = 0.5 + (zc - 0.5) * (0.5 + 0.5 * math.sin(tip * math.pi / 2))
    zb = -0.6 - 0.35 * t
    xi = -4.05                                         # inboard edge, column 8 (open gap)
    w = xi - xo
    f = min(1.0, w / 3.0)                              # small offsets shrink toward the narrow tip
    lean = 0.45 * f
    cw = min(1.15, 0.36 * w)                           # crest strip width
    zo = zb + 0.3 + 0.2 * t                            # outboard edge height
    xs = xi - 0.16 * f - cw                            # crest strip's outboard edge
    sm = 0.22 * f                                      # seam step width
    D = xs - sm - (xo + 0.3 * f)
    Hh = zc - 0.3 - (zo + 0.22)
    pts = [
        (xi - lean, zb + 0.05),
        (xi - lean * 0.3, zc - 0.5),
        (xi, zc - 0.16),                               # chamfer to the crest
        (xi - 0.16 * f, zc),
        (xs, zc),
        (xs - 0.3 * sm, zc - 0.22),                    # seam step
        (xs - sm, zc - 0.3),
        # Convex outboard flank: near flat by the seam, steepening toward the outer edge.
        (xs - sm - 0.3 * D, zc - 0.3 - 0.07 * Hh),
        (xs - sm - 0.58 * D, zc - 0.3 - 0.26 * Hh),
        (xs - sm - 0.8 * D, zc - 0.3 - 0.55 * Hh),
        (xs - sm - 0.93 * D, zc - 0.3 - 0.8 * Hh),
        (xo + 0.3 * f, zo + 0.22),
        (xo, zo - 0.08),
        (xo + 0.2 * f, zb + 0.1),
        (xo + 0.55 * f, zb),
        (xi - lean - 0.3 * f, zb - 0.05),
    ]
    if inset:
        cx = sum(p[0] for p in pts) / len(pts)
        cz = sum(p[1] for p in pts) / len(pts)
        pts = [(x + (cx - x) * inset, z + (cz - z) * inset) for x, z in pts]
    return [(x, y, z) for x, z in pts]


def build_prongs(part):
    """Two panels with a transverse seam (a real groove) at row 6.5."""
    ys = [0.1, 0.3, 0.75, 1.4, 2.2, 3.2, 4.4, 5.6, 6.3, 6.4, 6.6, 6.7, 7.6, 8.6, 9.6, 11.0, 12.4, 13.3, 14.0, 14.55]
    ins = {6.4: 0.09, 6.6: 0.09}
    rings = [prong_section(y, ins.get(y, 0.0)) for y in ys]
    loft(part, rings, PRONG)
    loft(part, mirror(rings), PRONG)


def spar_front(ax):
    """Leading edge row of the spar at |x|: rows 13 and 14 step in toward the tips."""
    return T.pchip([0.0, 8.6, 9.4, 10.2, 11.0], [14.88, 14.88, 14.2, 13.4, 12.95])(ax)


def build_spar(part):
    xs = [-10.98, -10.6, -10.1, -9.6, -9.0, -8.0, -6.0, -4.0, -2.0, 0.0]
    xs = xs + [-x for x in reversed(xs[:-1])]
    rings = []
    y0 = 9.02
    for x in xs:
        yf = spar_front(abs(x))
        # Full height between the prongs; under the prongs it drops below their outboard slope so
        # no spar end pokes out of them.
        zt = T.pchip([0.0, 4.7, 6.2, 8.2, 11.0], [2.0, 2.0, 1.1, 0.35, 0.1])(abs(x))
        sec = [(y0 + 0.02, min(-0.25, zt - 0.5)), (y0, min(1.45, zt - 0.4)), (y0 + 0.4, zt), (yf - 1.75, zt),
               (yf - 1.45, zt - 0.12), (yf - 0.22, min(0.25, zt - 0.3)), (yf, min(-0.05, zt - 0.45)),
               (yf - 0.3, -0.75), (y0 + 0.3, -0.75)]
        rings.append([(x, y, z) for y, z in sec])
    loft(part, rings, SPAR)
    # Top plates: three armour panels standing 0.15 px proud, with real gaps (panel lines).
    for xa, xb in ((-4.4, -3.15), (-2.7, 2.7), (3.15, 4.4)):
        pr = []
        for x in (xa, (xa + xb) / 2, xb):
            yf = spar_front(abs(x))
            sec = [(y0 + 0.45, 1.85), (y0 + 0.65, 2.15), (yf - 1.95, 2.15), (yf - 1.75, 1.85)]
            pr.append([(x, y, z) for y, z in sec])
        loft(part, pr, SPAR)


def build_block(part):
    # Body: a chamfered box, rows 3-12.8, columns 9-15.
    box(part, -2.98, 2.98, 3.02, 12.9, -0.6, 3.5, BLOCK, ch=0.45, chz=0.35)
    # Rear louvre deck: side rails and cross bars around two slots (rows 4 and 6, columns 11-13).
    for x0, x1 in ((-2.6, -1.1), (1.1, 2.6)):
        box(part, x0, x1, 3.35, 8.1, 3.2, 4.1, BLOCK, ch=0.18)
    for y0, y1 in ((3.35, 4.05), (4.95, 6.05), (6.95, 8.1)):
        box(part, -1.15, 1.15, y0, y1, 3.2, 4.0, BLOCK, ch=0.14)
    for y0, y1 in ((4.0, 5.0), (6.0, 7.0)):
        box(part, -1.12, 1.12, y0, y1, 3.2, 3.55, SLOT, ch=0.05)
    # The crosswise ridge (the bright row 8): a rounded bar.
    rid = []
    for x in (-2.75, -2.55, -1.5, 0.0, 1.5, 2.55, 2.75):
        k = 0.82 if abs(x) > 2.6 else 1.0
        sec = superellipse(8.55, 3.95, 0.62 * k, 0.75 * k, 0.6, n=12, e=2.2, eb=2.0)
        rid.append([(x, y, z) for y, z in sec])
    loft(part, rid, BLOCK)
    # Forward deck, rows 9-12.8, with a recessed grille at rows 10-11.9 (columns 11-13).
    for x0, x1 in ((-2.65, -1.15), (1.15, 2.65)):
        box(part, x0, x1, 9.15, 12.5, 3.2, 3.95, BLOCK, ch=0.2)
    box(part, -1.2, 1.2, 9.15, 9.95, 3.2, 3.9, BLOCK, ch=0.15)
    box(part, -1.2, 1.2, 11.95, 12.5, 3.2, 3.9, BLOCK, ch=0.15)
    box(part, -1.15, 1.15, 9.9, 12.0, 3.2, 3.4, SLOT, ch=0.05)
    for y in (10.45, 11.0, 11.55):  # louvre fins
        box(part, -1.12, 1.12, y - 0.13, y + 0.13, 3.3, 3.75, BLOCK, ch=0.06)
    # Rear face: two exhaust nozzles (seen from behind).
    for x in (-1.5, 1.5):
        outer = [(x + 0.75 * math.cos(a), 3.05, 1.5 + 0.75 * math.sin(a)) for a in
                 (2 * math.pi * (k + 0.5) / 12 for k in range(12))]
        lip = [(x + 0.75 * math.cos(a), 2.75, 1.5 + 0.75 * math.sin(a)) for a in
               (2 * math.pi * (k + 0.5) / 12 for k in range(12))]
        inner = [(x + 0.5 * math.cos(a), 2.75, 1.5 + 0.5 * math.sin(a)) for a in
                 (2 * math.pi * (k + 0.5) / 12 for k in range(12))]
        loft(part, [outer, lip, inner], BLOCK, cap0=False, cap1=False)
        deep = [(px, 3.1, pz) for px, _, pz in inner]
        loft(part, [inner, deep], SLOT, cap0=False, cap1=True)


def hull_profile():
    ys = [12.6, 13.6, 14.6, 15.2, 16.2, 18.0, 20.0, 21.2, 22.2, 23.0, 23.6, 24.1]
    hw = [6.3, 6.7, 6.95, 6.98, 7.2, 7.3, 7.3, 7.0, 6.4, 5.6, 4.7, 3.6]
    zt = [1.2, 1.3, 1.4, 1.4, 1.4, 1.4, 1.5, 1.85, 2.05, 1.85, 1.5, 1.05]
    zb = [-1.3, -1.6, -2.0, -2.1, -2.2, -2.2, -2.2, -2.1, -1.9, -1.6, -1.3, -1.0]
    return ys, hw, zt, zb


def build_hull(part):
    ys, hw, zt, zb = hull_profile()
    rings = []
    for y, w, t, b in zip(ys, hw, zt, zb):
        cz = 0.0
        rings.append([(x, y, z) for x, z in superellipse(0.0, cz, w, t - cz, cz - b, n=24, e=3.2, eb=2.4)])
    loft(part, rings, HULL)


def fender_band(s_list):
    """Left fender: (outer (x, y), inner (x, y), crown z, half height) per station."""
    return s_list


FENDER_ST = [
    # outer xy        inner xy        crown z  bottom z
    ((-8.98, 16.08), (-6.85, 16.08), 2.15, -0.9),
    ((-8.98, 16.6), (-6.85, 16.6), 2.4, -1.0),
    ((-8.98, 18.5), (-6.85, 18.5), 2.45, -1.0),
    ((-8.98, 20.0), (-6.3, 20.0), 2.45, -1.0),
    ((-8.95, 21.4), (-5.4, 21.2), 2.45, -1.0),
    ((-8.75, 22.6), (-4.9, 22.3), 2.4, -1.0),
    ((-8.0, 23.55), (-4.1, 23.2), 2.3, -0.95),
    ((-7.05, 24.5), (-3.2, 24.0), 2.15, -0.9),
    ((-6.05, 25.5), (-2.35, 24.75), 2.0, -0.85),
    ((-5.1, 26.45), (-2.05, 25.7), 1.85, -0.8),
    ((-4.55, 26.95), (-2.05, 26.75), 1.55, -0.7),
]


def fender_section(o, i, zc, zb):
    """Points from the outer edge over the crown to the inner edge and back under (x, y, z)."""
    ox, oy = o
    ix, iy = i
    L = lambda t, dz=0.0: (ox + (ix - ox) * t, oy + (iy - oy) * t)  # noqa: E731
    prof = [(0.0, zb + 0.15), (0.0, zc - 0.55), (0.06, zc - 0.2), (0.2, zc), (0.55, zc - 0.08),
            (0.8, zc - 0.32), (0.93, zc - 0.62), (1.0, zc - 0.95), (1.0, zb + 0.3), (0.85, zb), (0.12, zb)]
    out = []
    for t, z in prof:
        x, y = L(t)
        out.append((x, y, z))
    return out


def build_fender(part):
    rings = [fender_section(o, i, zc, zb) for o, i, zc, zb in FENDER_ST]
    loft(part, rings, FENDER)
    loft(part, mirror(rings), FENDER)


def pod_out(y):
    return T.pchip([14.45, 14.9, 15.6, 16.5, 18.4, 19.4, 20.3, 20.85, 21.05],
                   [-3.6, -5.2, -5.95, -6.05, -6.0, -5.25, -4.25, -3.1, -2.2])(y)


def build_domes(part):
    ys = [14.5, 14.75, 15.2, 15.8, 16.6, 17.5, 18.4, 19.2, 19.9, 20.45, 20.85, 21.05]
    rings = []
    for y in ys:
        xo = pod_out(y)
        xi = -1.12
        u = (y - 14.5) / (21.05 - 14.5)
        hmax = 4.1 + 0.2 * math.sin(u * math.pi)          # dome crown, a little higher mid-length
        end = math.sin(min(1.0, u / 0.12) * math.pi / 2) * math.sin(min(1.0, (1 - u) / 0.14) * math.pi / 2)
        zt = 1.0 + (hmax - 1.0) * (0.3 + 0.7 * end)
        cx = (xo + xi) / 2
        hw = (xi - xo) / 2
        sec = []
        for k in range(14):
            a = math.pi * k / 13                               # 0 .. pi: over the top, right to left
            c, s = math.cos(a), math.sin(a)
            x = cx + hw * math.copysign(abs(c) ** 0.8, c)
            z = 0.6 + (zt - 0.6) * (max(0.0, s) ** 0.55)
            sec.append((x, y, z))
        sec.append((xo + 0.1, y, 0.3))
        sec.append((xi - 0.1, y, 0.3))
        rings.append(sec)
    loft(part, rings, DOME)
    loft(part, mirror(rings), DOME)
    # The keel channel between them: a dark low spine (columns 11-12).
    box(part, -1.15, 1.15, 13.4, 21.3, 0.2, 1.85, SLOT, ch=0.3, chz=0.3)
    # Dome bezels: thin collars where the domes meet the hull (machined rings, hull colour).


def build_intake(part):
    # Intake floor and lip between the jaws (rows 24-25.9, columns 9-14), dark; the 2 px slot at
    # row 26 stays open.
    box(part, -2.6, 2.6, 23.4, 25.95, -0.9, 0.35, INTAKE, ch=0.25)
    # Intake mouth face on the hull nose (seen from the front).
    box(part, -2.3, 2.3, 23.55, 24.2, 0.2, 1.15, INTAKE, ch=0.15)
    # Splitter vane down the middle of the intake.
    box(part, -0.25, 0.25, 23.8, 25.6, 0.2, 0.75, HULL, ch=0.08)


def build_seal(part):
    """Sealed simplified copy for the outline shell: no slots, the keel channel and intake filled."""
    build_prongs(part)
    build_spar(part)
    box(part, -2.98, 2.98, 3.02, 12.9, -0.6, 4.2, BLOCK, ch=0.45, chz=0.35)
    build_hull(part)
    build_fender(part)
    build_domes(part)
    box(part, -1.3, 1.3, 13.4, 21.3, 0.2, 3.3, SLOT, ch=0.3)
    box(part, -2.6, 2.6, 23.4, 25.95, -0.9, 0.9, INTAKE, ch=0.25)


def spec(mat, level):
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = level
    return mat


def materials(sprite):
    mats = []
    for slot in range(len(PAL)):
        m, r, s = FINISH[slot]
        mats.append(spec(common.palette_material(sprite, PAL[slot], f"{TAG}-{slot}", metallic=m, roughness=r), s))
    return mats


def build():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    mats = materials(sprite)

    part = T.Part(NAME, smooth_angle=34.0)
    build_prongs(part)
    build_spar(part)
    build_block(part)
    build_hull(part)
    build_fender(part)
    build_domes(part)
    build_intake(part)
    obj = T.finish(part, mats, coll)

    seal_part = T.Part(NAME + "_seal")
    build_seal(seal_part)
    seal = T.finish(seal_part, mats, coll)
    bpy.context.view_layer.update()
    shell = common.outline_shell(seal, coll, voxel=0.008, faces=2400, smooth=4, inside=0.002, islands="outer")
    bpy.data.objects.remove(seal, do_unlink=True)
    shell.name = f"{NAME}_outline"
    assert len(shell.data.polygons) > 0, "empty outline shell"

    T.cull_hidden(obj)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    ev.data.calc_loop_triangles()
    tris = len(ev.data.loop_triangles)
    out = argv_opt("--out")
    if out:
        common.export_glb([obj, shell], Path(out))
    else:
        common.export_sprite_model(ROOT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])
    print(f"{NAME}: {tris} tris, outline shell {len(shell.data.polygons)} faces")


if __name__ == "__main__":
    build()
