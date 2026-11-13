"""Brain spawn drill (newsh5.shp frame 207), design A: a 3D version of its sprite.

Seen in episode 4 (BRAINIAC, 4.15 / main=22): two dozen of these shoot out of the brain, swoop,
then dive straight down the screen. So it is built as what it is: a small armoured burrowing pod,
lying flat and pointing down the screen (-Y), its long tapering drill spike in front.

Reading the sprite (rubric "Reading a sprite"; lit from the top left, the ink ring and the dark
lower edges are lighting):
  rows 1-3   the rear housing: a wide drum (13 px) with a rounded crown; row 3's dark pixels are the
             shadow under its lip, so the lip overhangs an undercut.
  rows 4-5   a bright collar bead (11 then 9 px), the drive ring.
  row 6      a dark groove (9 px), the waist.
  rows 7-11  the casing, 11 px: a band across the top (rows 7-8) and a seam groove (row 9).
  rows 10-16 two shell halves bulging either side of a dark centre seam (columns 10-11 and 13-14
             catch the light); the casing steps in to 9 px at row 12.
  rows 17-25 the drill spike, an ogive from 7 px to a point, with a raised keel down its top centre
             (column 12's bright pixels).

Build: one closed loft along Y in sprite px. Every station is a superelliptic section (fuller on top,
flatter underneath) whose half width follows the sprite's inner mask row by row (pchip between
knots, short chamfered steps where the sprite steps), whose top height steps with it (undercut lip,
bead, waist, shoulders), and whose top carries modelled relief: the two shell lobes, the centre seam,
the row-9 panel line, the keel on the spike and a chine either side of it. The rear is closed by a
domed plate with a machined hub (rear only; the game camera never sees it). The underside is a plain
closed belly. Faces take the palette index of the sprite pixels over them (trimmed medians): housing
71, collar and lobes 72, casing 69, sides and spike 68, grooves 67, centre seam 66, keel 73.
Sharp edges by angle on the step shoulders; the rest smooth. Outline shell from a sealed copy (D51).

Run: tools/build-models.sh -j 2 assets/blender/enemies/newsh5-207.py
Writes public/models/enemies/newsh5-207.glb and src/render/spriteModels/newsh5-207.json.
"""

import bisect
import json
import math
import sys
from pathlib import Path

import bmesh


def find_repo():
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "package.json").exists() and (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("repo root not found")


ROOT = find_repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
import common  # noqa: E402

NAME = "newsh5-207"
FRAME = 207
W, H = 24, 28
CXE = 12.5  # symmetry axis (pixel edge): the sprite is symmetric about column 12
S = 1 / 12  # Blender units per sprite px


def pchip(xs, ys):
    """Monotone cubic interpolation through (xs, ys): smooth, no overshoot (as usp_talon.pchip)."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def knots(pairs):
    xs, ys = zip(*pairs)
    return pchip(list(xs), list(ys))


# --- Profiles, in sprite px (y = row edge from the top, aft is small y; z up) ----------------------
Y0, Y1 = 0.92, 26.05  # rear plate, spike tip

# Half width: the inner mask's half widths are 5.5 (row 1), 6.5 (2-3), 5.5 (4), 4.5 (5-6),
# 5.5 (7-11), 4.5 (12-16), 3.5 (17-19), 2.5 (20-21), 1.5 (22-23), 0.5 (24-25).
HALF_W = knots([
    (Y0, 5.05), (1.15, 5.55), (1.5, 6.0), (1.9, 6.4), (2.3, 6.55), (3.45, 6.55), (3.75, 6.35),
    (3.92, 5.75), (4.05, 5.5),                    # undercut under the housing lip
    (4.8, 5.45), (5.05, 4.95), (5.3, 4.6),        # collar bead tapering into the waist
    (6.0, 4.45), (6.55, 4.3), (6.9, 4.55),        # waist groove
    (7.05, 5.25), (7.25, 5.55), (11.75, 5.55),    # casing
    (11.95, 5.15), (12.15, 4.6), (16.75, 4.55),   # shoulder down to the shell halves
    (16.95, 4.1), (17.2, 3.65),                   # shoulder down to the spike
    (18.5, 3.42), (19.6, 3.05), (21.5, 2.15), (23.4, 1.2), (24.6, 0.66), (25.5, 0.3), (Y1, 0.03),
])
# Top height above the mid plane.
HT = knots([
    (Y0, 2.1), (1.08, 2.9), (1.4, 3.55), (2.0, 4.0), (2.8, 4.05), (3.45, 3.75), (3.8, 3.15),
    (4.0, 2.75), (4.25, 3.1), (4.6, 3.55), (5.0, 3.7), (5.4, 3.45), (5.9, 3.0),
    (6.5, 2.7), (6.9, 2.85), (7.15, 3.3), (7.5, 3.55), (11.7, 3.5),
    (12.1, 3.15), (12.5, 3.2), (16.6, 2.95), (17.05, 2.55), (17.4, 2.45),
    (19.5, 2.05), (21.5, 1.5), (23.5, 0.9), (25.0, 0.45), (Y1, 0.05),
])
# Belly depth below the mid plane (a plain closed shape).
HB = knots([
    (Y0, 1.5), (1.3, 2.4), (2.2, 2.7), (3.6, 2.6), (4.0, 2.2), (5.0, 2.4), (6.6, 2.1), (7.3, 2.5),
    (11.8, 2.5), (12.3, 2.3), (16.8, 2.2), (17.3, 1.9), (21.5, 1.15), (24.5, 0.5), (Y1, 0.04),
])
N_TOP = 2.6   # superellipse exponents: full shoulders on top, a rounder belly
N_BOT = 2.1


def smooth_bump(t):
    """1 at t=0, 0 at |t|>=1, smooth (cos^2)."""
    t = abs(t)
    return 0.0 if t >= 1 else math.cos(t * math.pi / 2) ** 2


def ramp(y, a, b, c, d):
    """0 before a, up to 1 over a-b, 1 to c, down to 0 over c-d (smoothstep edges)."""
    def ss(u):
        u = min(1.0, max(0.0, u))
        return u * u * (3 - 2 * u)
    if y <= a or y >= d:
        return 0.0
    if y < b:
        return ss((y - a) / (b - a))
    if y > c:
        return 1.0 - ss((y - c) / (d - c))
    return 1.0


def lobe_weight(x, y):
    """0..1: how far up the crown of a shell half (x px from the axis, row edge y)."""
    lob = ramp(y, 9.6, 11.0, 15.0, 16.9)
    return lob * (smooth_bump((x + 1.6) / 1.8) + smooth_bump((x - 1.6) / 1.8))


def relief(s, w, y):
    """Modelled top relief (px of z added) at across-fraction s of the half width w, row edge y."""
    x = s * w
    z = 0.0
    # the two shell halves (sprite columns 10-11 and 13-14: crowns at x = -1.55, +1.55)
    # the centre seam between them (column 12), a narrow V groove
    seam = ramp(y, 9.9, 10.5, 16.2, 16.9)
    z -= 0.55 * seam * smooth_bump(s / 0.1)
    # row 9's panel line across the casing
    z -= 0.32 * smooth_bump((y - 9.45) / 0.32)
    # spike: a raised keel down the top centre and a chine either side of it
    sp = ramp(y, 16.9, 17.6, 24.5, 25.8)
    z += 0.45 * sp * smooth_bump(s / 0.17)
    z -= 0.14 * sp * (smooth_bump((s - 0.4) / 0.1) + smooth_bump((s + 0.4) / 0.1))
    return z


# across-fractions of the half width: dense near the axis (seam, keel), then out to the edge
TOP_S = [0.0, 0.045, 0.095, 0.15, 0.21, 0.28, 0.35, 0.42, 0.5, 0.6, 0.7, 0.79, 0.87, 0.93, 0.975, 1.0]
BOT_S = [0.9, 0.62, 0.3, 0.0]  # from the edge back to the keel line underneath


def ring_at(y):
    """Points (x, z, is_top) round the section at y: top from -edge over to +edge, belly back."""
    w, ht, hb = HALF_W(y), HT(y), HB(y)
    pts = []
    top = [-s for s in reversed(TOP_S[1:])] + TOP_S
    for s in top:
        a = abs(s)
        zt = ht * (1 - a ** N_TOP) ** (1 / N_TOP) if a < 1 else 0.0
        fade = 1 - a ** 3
        pts.append((s * w, zt + relief(s, w, y) * fade, True))
    for s in BOT_S + [-s for s in reversed(BOT_S[:-1])]:
        a = abs(s)
        zb = -hb * (1 - a ** N_BOT) ** (1 / N_BOT)
        pts.append((s * w, zb, False))
    return pts


def stations():
    ys = {Y0, Y1}
    # dense through the steps and panel lines, coarser along the smooth runs
    spans = [(Y0, 2.4, 0.2), (2.4, 3.4, 0.5), (3.4, 4.4, 0.17), (4.4, 7.6, 0.25), (7.6, 9.0, 0.7),
             (9.0, 9.9, 0.18), (9.9, 11.6, 0.55), (11.6, 12.6, 0.2), (12.6, 16.6, 0.7),
             (16.6, 17.8, 0.2), (17.8, 25.0, 0.75), (25.0, Y1, 0.35)]
    for a, b, st in spans:
        n = max(1, round((b - a) / st))
        for i in range(n + 1):
            ys.add(round(a + (b - a) * i / n, 4))
    return sorted(ys)


# --- Materials -------------------------------------------------------------------------------------
HOUSING, COLLAR, CASING, SIDE, GROOVE, SEAM, KEEL = 71, 72, 69, 68, 67, 66, 73
FINISH = {  # satin lacquered metal: low metal, mid roughness (sheen does the sprite's hot spots)
    HOUSING: dict(metallic=0.2, roughness=0.34),
    COLLAR: dict(metallic=0.3, roughness=0.28),    # machined drive ring and shell halves
    CASING: dict(metallic=0.2, roughness=0.36),
    SIDE: dict(metallic=0.2, roughness=0.38),
    GROOVE: dict(metallic=0.2, roughness=0.55),
    SEAM: dict(metallic=0.2, roughness=0.6),
    KEEL: dict(metallic=0.4, roughness=0.26),      # polished cutting edge
}


def region(s, y, top, w=5.0):
    """Palette index for a face centred at across-fraction s, row edge y; top = upper half."""
    ax = abs(s)
    if not top:
        return SIDE if y > 16.9 else CASING
    if y < 3.82:
        return HOUSING
    if y < 4.12:
        return GROOVE
    if y < 5.75:
        return COLLAR
    if y < 7.05:
        return GROOVE
    if 9.15 < y < 9.75:
        return GROOVE
    if y < 16.9:
        if 10.1 < y < 16.75 and ax < 0.07:
            return SEAM
        if y < 9.15:
            return CASING
        return SIDE
    if ax < 0.12 and y < 25.2:
        return KEEL
    return SIDE


def to_blender(x, y, z):
    return ((x + CXE - W / 2) * S, (H / 2 - y) * S, z * S)


def build_body(bm):
    """The loft, its rear plate and tip. Returns {palette index: [faces]}."""
    faces = {}
    ys = stations()
    rings = []
    for y in ys:
        w = max(HALF_W(y), 1e-6)
        rings.append([(bm.verts.new(to_blender(x, y, z)), x / w, top) for x, z, top in ring_at(y)])
    n = len(rings[0])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        ym = (ys[i] + ys[i + 1]) / 2
        for k in range(n):
            k2 = (k + 1) % n
            f = bm.faces.new((a[k][0], a[k2][0], b[k2][0], b[k][0]))
            xm = (a[k][1] + a[k2][1]) / 2
            top = a[k][2] and a[k2][2]
            faces.setdefault(region(xm, ym, top, HALF_W(ym)), []).append(f)
    # rear plate: the rim ring scaled in toward a machined hub, domed slightly aft
    rim = rings[0]
    cz = (HT(Y0) - HB(Y0)) / 2 * 0.3
    prev = [v for v, _, _ in rim]
    plate = [(0.86, Y0 - 0.06, HOUSING), (0.8, Y0 - 0.06, GROOVE), (0.74, Y0 - 0.12, GROOVE),
             (0.7, Y0 - 0.12, HOUSING), (0.4, Y0 - 0.16, HOUSING), (0.34, Y0 - 0.16, COLLAR),
             (0.3, Y0 - 0.24, COLLAR), (0.18, Y0 - 0.26, COLLAR)]
    for sc, yy, mat in plate:
        cur = []
        for v, _, top in rim:
            x, z = v.co.x / S - (CXE - W / 2), v.co.z / S
            cur.append(bm.verts.new(to_blender(x * sc, yy, cz + (z - cz) * sc)))
        for k in range(n):
            k2 = (k + 1) % n
            faces.setdefault(mat, []).append(bm.faces.new((cur[k], cur[k2], prev[k2], prev[k])))
        prev = cur
    hub = bm.verts.new(to_blender(0, Y0 - 0.28, cz))
    for k in range(n):
        faces.setdefault(COLLAR, []).append(bm.faces.new((prev[k], prev[(k + 1) % n], hub)))
    # spike tip
    tip = bm.verts.new(to_blender(0, Y1 + 0.02, 0.02))
    last = [v for v, _, _ in rings[-1]]
    for k in range(n):
        faces.setdefault(SIDE, []).append(bm.faces.new((last[(k + 1) % n], last[k], tip)))
    return faces


def body_top(x, y):
    """The casing's top surface z (px) at x px from the axis, row edge y."""
    w, ht = HALF_W(y), HT(y)
    s = min(1.0, abs(x) / w)
    return ht * (1 - s ** N_TOP) ** (1 / N_TOP) + relief(x / w, w, y) * (1 - s ** 3)


# The two shell halves (sprite columns 10-11 and 13-14, rows 10-16): armour plates standing proud of
# the casing either side of the centre seam, domed, with a chamfered edge.
SHELL = dict(xc=1.5, yc=13.4, a=1.12, b=3.35, p=3.2, dome=0.62, lip=0.24, bury=0.35)


def build_shells(bm):
    faces = []
    c = SHELL
    segs = 28
    rings = [0.0, 0.4, 0.7, 0.88, 0.96, 1.0]
    for side in (-1, 1):
        xc = side * c["xc"]

        def outline(t, r):
            ct, st = math.cos(t), math.sin(t)
            # superellipse |u|^p + |v|^p = 1
            k = (abs(ct) ** c["p"] + abs(st) ** c["p"]) ** (-1 / c["p"])
            return xc + c["a"] * r * k * ct, c["yc"] + c["b"] * r * k * st

        grid = []
        for r in rings:
            ring = []
            prof = (1 - r ** 2.4) ** 0.5  # dome
            for j in range(segs):
                t = 2 * math.pi * j / segs
                x, y = outline(t, r)
                z = body_top(x, y) + c["lip"] + (c["dome"] - c["lip"]) * prof
                ring.append(bm.verts.new(to_blender(x, y, z)))
            grid.append(ring)
        # chamfer and skirt: out 0.12 px and down past the casing surface
        for grow, dz in ((0.1, 0.1), (0.14, -c["bury"])):
            ring = []
            for j in range(segs):
                t = 2 * math.pi * j / segs
                x, y = outline(t, 1.0)
                nx, ny = x - xc, y - c["yc"]
                ln = math.hypot(nx / c["a"], ny / c["b"]) or 1
                x += grow * nx / ln / c["a"] * 1.0
                y += grow * ny / ln / c["b"] * 1.0
                ring.append(bm.verts.new(to_blender(x, y, body_top(x, y) + dz)))
            grid.append(ring)
        centre = grid[0]
        # centre ring collapses to a point: use a fan from its first vertex position
        mid = bm.verts.new(centre[0].co.copy())
        for v in centre:
            bm.verts.remove(v)
        grid = grid[1:]
        for j in range(segs):
            faces.append(bm.faces.new((mid, grid[0][j], grid[0][(j + 1) % segs])))
        for a, b in zip(grid, grid[1:]):
            for j in range(segs):
                j2 = (j + 1) % segs
                faces.append(bm.faces.new((a[j], b[j], b[j2], a[j2])))
        # close the buried skirt underneath
        bot = grid[-1]
        cen = bm.verts.new(to_blender(xc, c["yc"], body_top(xc, c["yc"]) - c["bury"]))
        for j in range(segs):
            faces.append(bm.faces.new((cen, bot[(j + 1) % segs], bot[j])))
    return faces


def build(sprite):
    coll = common.reset_collection(NAME)
    bm = bmesh.new()
    faces = build_body(bm)
    faces.setdefault(COLLAR, []).extend(build_shells(bm))  # the lit shell halves: 72
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    used = sorted(faces)
    for slot, idx in enumerate(used):
        for f in faces[idx]:
            f.material_index = slot
    # smooth, with sharp edges on the step shoulders and panel-line lips (> 38 degrees)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(38):
            e.smooth = False
    mats = [common.palette_material(sprite, i, NAME, **FINISH[i]) for i in used]
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=None)
    shell = common.outline_shell(obj, coll, voxel=0.008, faces=1800, smooth=4, inside=0.002,
                                 islands="outer")
    assert len(shell.data.polygons) > 0, "empty outline shell"
    return obj, shell


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj, shell = build(sprite)
    common.export_sprite_model(ROOT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])


main()
