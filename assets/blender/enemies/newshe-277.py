"""Three glowing red eggs (newshe.shp frames 277, 279, 281, 283), hard-surface pods.

The sprite: three identical eggs lying on the ground, each round at the back and narrowing to a
point at the front (down the screen). Each egg is a red orb (back-left) with a white sheen spot on
its upper left, held in an orange hooked crest that runs up its right flank from the pointed nose,
a dark seam between orb and crest. The four frames only move the three eggs round the group's
centre; the egg itself never turns. So one egg is built once and placed three times per frame.

Each egg, hard surface (D50-D53, D65):
- Cradle: a low plinth whose plan is the sprite's INNER mask (D74: inside the ink border,
  tools/sprite_mask.py) fitted row by row with pchip, squircle-closed at both ends; its sections
  are chamfered (vertical wall, a modelled panel-line groove round the wall, a 45-degree chamfer
  to a flat deck). Front (nose) deck orange, rest dark red, as the sprite.
- Orb: a smooth ellipsoid seated in the cradle deck, filling the sprite's orb pixels to the inner
  edge on the left and back. The white spot is sheen (rubric "Reading a sprite"): glossy material,
  no geometry.
- Crest: a swept strake with a chamfered trapezoid section (pchip centreline), from the back right
  down the right flank and round into the nose; two machined transverse panel lines; it stands
  apart from the orb, leaving the sprite's dark seam as a real gap.
- Colours: each part's palette index is the trimmed median (darkest/brightest 15% ignored) of the
  sprite pixels whose centre the part covers from above (ray cast), computed per build.
- No emission (the game copies the palette colour into the emissive of glowing materials and
  washes it out; newsh3-267 notes). Underside: closed flat base, nothing more.
- Per frame one object (3 eggs) + outline shell (common.outline_shell, D51), frame_part-tagged.
  The game contract (finish step): frame i -> model enemies/newshe-277 / -f2 / -f3 / -f4, each
  replacing its single frame, exactly as assets/blender/enemies/newshe-277.py.

Run: blender --background --python assets/blender/enemies/newshe-277.py -- [--render OUTDIR]
Exports enemies/newshe-277, -f2, -f3, -f4 (one frame each) like the script it replaces.
"""

import bisect
import json
import math
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))  # noqa: E402
import common  # noqa: E402

sys.path.insert(0, str(WT / "tools"))
import sprite_mask as SM  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "newshe-277"
W, H = 24, 28
PX = 1 / 12

# Top-left corner (col, row) of each egg's 9 x 12 px box per frame (from the current script; the
# three boxes cover every pixel of each frame).
EGGS = {
    277: [(2, 4), (14, 4), (8, 15)],
    279: [(4, 2), (15, 8), (5, 14)],
    281: [(8, 0), (2, 12), (14, 12)],
    283: [(12, 2), (1, 8), (11, 14)],
}
# The egg's inner mask in its box (rows 1..10 inclusive): row -> (left edge, right edge) px.
INNER = {1: (2, 7), 2: (1, 8), 3: (1, 8), 4: (1, 8), 5: (1, 8), 6: (1, 8), 7: (2, 7), 8: (2, 7),
         9: (3, 6), 10: (3, 6)}
Y_BACK, Y_NOSE = 1.0, 11.0

# Heights (px)
Z_WALL = 0.95        # plinth wall top
Z_DECK = 1.55        # plinth deck
CHAMFER = 0.55
GROOVE = (0.38, 0.55, 0.14)   # wall panel line: z0, z1, depth
NOSE_Y = 8.7         # deck in front of this is the orange nose

ORB_C = (3.6, 4.5, 1.3)
ORB_R = (2.38, 3.15, 2.45)
COLLAR_Z, COLLAR_T = 1.62, 0.17   # machined seat ring round the orb (px)

# Crest centreline: (x, y, width, height) px
CREST = [(7.38, 1.35, 0.5, 1.75), (7.45, 2.1, 0.85, 2.6), (7.47, 3.0, 1.0, 3.05), (7.42, 4.2, 1.1, 3.25), (7.2, 5.7, 1.2, 3.3),
         (6.75, 6.95, 1.4, 3.2), (6.0, 8.0, 1.75, 3.0), (5.15, 9.0, 2.2, 2.7), (4.7, 10.0, 2.3, 2.3),
         (4.55, 10.85, 1.7, 1.7)]
CREST_Z0 = 1.0
CREST_CH = 0.32
GROOVES_T = (0.30, 0.62)      # crest panel lines at these fractions of its length
GROOVE_W, GROOVE_D = 0.045, 0.22
CREST_SPLIT_Y = 5.0           # crest behind this row is the dark back (114-117), in front the
                              # orange hook (119-123), as the sprite's gradient down the flank

# Hot core (the sprite's 126/127 inside a 119-123 ring, cols 2-4 rows 2-5 of the egg box): a raised
# machined cap on the orb's crown in the ring's colour, a smaller lens on it in the core's colour.
CORE_C = (3.5, 4.0)
CORE_R, CORE_LIFT = (1.42, 1.88), 0.13
LENS_R, LENS_LIFT = (0.62, 1.0), 0.24
SLOTS = {"orb": 0, "crest": 1, "cradle": 2, "nose": 3, "crest_front": 3, "core": 4, "lens": 5}


def pchip(xs, ys):
    """Monotone cubic interpolation (copied from usp_talon.pchip)."""
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


# --- Plan ---------------------------------------------------------------------------------------

rows = sorted(INNER)
_yc = [r + 0.5 for r in rows]
_L = [float(INNER[r][0]) for r in rows]
_R = [float(INNER[r][1]) for r in rows]
for _ in range(2):  # relax the stair steps, ends fixed
    _L = [_L[0]] + [(_L[i - 1] + 2 * _L[i] + _L[i + 1]) / 4 for i in range(1, len(_L) - 1)] + [_L[-1]]
    _R = [_R[0]] + [(_R[i - 1] + 2 * _R[i] + _R[i + 1]) / 4 for i in range(1, len(_R) - 1)] + [_R[-1]]
FL, FR = pchip(_yc, _L), pchip(_yc, _R)
BACK_A, NOSE_A = 1.15, 1.1      # px over which each end closes (squircle; the nose is blunt)
BACK_N, NOSE_N = 2.4, 2.6


def extent(y):
    """(centre, half width) of the egg's plan at y px."""
    y = min(max(y, Y_BACK), Y_NOSE)
    yy = min(max(y, Y_BACK + 0.5), Y_NOSE - 0.5)
    l, r = FL(yy), FR(yy)
    c, hw = 0.5 * (l + r), 0.5 * (r - l)
    if y < Y_BACK + BACK_A:
        t = (Y_BACK + BACK_A - y) / BACK_A
        hw *= max(0.0, 1 - t ** BACK_N) ** (1 / BACK_N)
    elif y > Y_NOSE - NOSE_A:
        t = (y - (Y_NOSE - NOSE_A)) / NOSE_A
        hw *= max(0.0, 1 - t ** NOSE_N) ** (1 / NOSE_N)
    return c, hw


def stations():
    ys = [Y_BACK + BACK_A * (1 - math.cos(0.5 * math.pi * i / 7)) for i in range(7)]
    n = 14
    ys += [Y_BACK + BACK_A + (Y_NOSE - NOSE_A - Y_BACK - BACK_A) * i / n for i in range(n)]
    ys += [Y_NOSE - NOSE_A + NOSE_A * math.sin(0.5 * math.pi * i / 8) for i in range(9)]
    return ys


# --- Mesh helpers -------------------------------------------------------------------------------

class Builder:
    """Collects one egg's geometry in box px coordinates (x right, y down the screen, z up) with a
    part tag per face."""

    def __init__(self):
        self.verts, self.faces = [], []   # faces: (vert ids, part, smooth)

    def v(self, p):
        self.verts.append(tuple(p))
        return len(self.verts) - 1

    def loft(self, rings, part, smooth, cap0=True, cap1=True, closed=True):
        ids = [[self.v(p) for p in ring] for ring in rings]
        for a, b in zip(ids, ids[1:]):
            n = len(a)
            for i in range(n if closed else n - 1):
                j = (i + 1) % n
                self.faces.append(([a[i], a[j], b[j], b[i]], part, smooth))
        if cap0:
            self.faces.append((list(reversed(ids[0])), part, False))
        if cap1:
            self.faces.append((list(ids[-1]), part, False))
        return ids


def plinth_profile(c, hw):
    """Closed section loop of the cradle at half width hw: bottom, wall with groove, chamfer, deck."""
    ch = min(CHAMFER, 0.6 * hw)
    gd = min(GROOVE[2], 0.25 * hw)
    z0, z1 = GROOVE[0], GROOVE[1]
    right = [(c + hw, 0.0), (c + hw, z0), (c + hw - gd, z0 + 0.04), (c + hw - gd, z1 - 0.04), (c + hw, z1),
             (c + hw, Z_WALL), (c + hw - ch, Z_DECK)]
    left = [(2 * c - x, z) for x, z in reversed(right)]
    return right + left   # right bottom .. right deck, left deck .. left bottom


def build_egg():
    b = Builder()
    # Cradle: a loft along y; the front part's deck faces become the nose.
    rings = []
    for y in stations():
        c, hw = extent(y)
        hw = max(hw, 0.02)
        rings.append([(x, y, z) for x, z in plinth_profile(c, hw)])
    b.loft(rings, "cradle", False)

    # Orb: an ellipsoid, smooth shaded, cut flat inside the cradle (closed by a flat disc there).
    seg, ring_n = 24, 10
    cx, cy, cz = ORB_C
    rx, ry, rz = ORB_R
    phi_max = math.acos(max(-1.0, (0.5 - cz) / rz))
    orb_rings = []
    for k in range(1, ring_n + 1):
        phi = phi_max * k / ring_n            # 0 top .. phi_max at the cut
        orb_rings.append([(cx + rx * math.sin(phi) * math.cos(2 * math.pi * s / seg),
                           cy + ry * math.sin(phi) * math.sin(2 * math.pi * s / seg),
                           cz + rz * math.cos(phi)) for s in range(seg)])
    ids = b.loft(orb_rings, "orb", True, cap0=False, cap1=True)
    top = b.v((cx, cy, cz + rz))
    for i in range(seg):
        j = (i + 1) % seg
        b.faces.append(([top, ids[0][i], ids[0][j]], "orb", True))

    # Seat collar: a chamfered ring round the orb where it enters the deck.
    n = 32
    zc = COLLAR_Z
    k = max(0.0, 1 - ((zc - cz) / rz) ** 2) ** 0.5
    ring = []
    for t, dz, dr in ((0, -0.12, 0.0), (1, 0.0, COLLAR_T), (2, COLLAR_T * 0.9, COLLAR_T * 0.6), (3, COLLAR_T * 1.1, -0.05),
                      (4, -0.12, 0.0)):   # back to the first ring: a closed (torus) section
        ring.append([(cx + (rx * k + dr) * math.cos(2 * math.pi * i / n), cy + (ry * k + dr) * math.sin(2 * math.pi * i / n),
                      zc + dz) for i in range(n)])
    b.loft(ring, "cradle", True, cap0=False, cap1=False)

    # Hot core: cap + lens, each a closed shallow puck following the orb's crown.
    def orb_z(x, y):
        q = 1 - ((x - cx) / rx) ** 2 - ((y - cy) / ry) ** 2
        return cz + rz * max(q, 0.0) ** 0.5

    def puck(c, r, lift, part, sink=0.18, nr=4, ns=20):
        rings = []
        for k2 in range(1, nr + 1):          # top surface, centre out (the edge ring gets a chamfer)
            f = 0.85 * k2 / (nr - 1) if k2 < nr else 1.0
            ring2 = []
            for i in range(ns):
                a = 2 * math.pi * i / ns
                x, y = c[0] + r[0] * f * math.cos(a), c[1] + r[1] * f * math.sin(a)
                lz = lift if k2 < nr else lift * 0.45
                ring2.append((x, y, orb_z(x, y) + lz))
            rings.append(ring2)
        edge = []                            # wall down into the orb
        for i in range(ns):
            a = 2 * math.pi * i / ns
            x, y = c[0] + r[0] * 1.04 * math.cos(a), c[1] + r[1] * 1.04 * math.sin(a)
            edge.append((x, y, orb_z(x, y) - sink))
        rings.append(edge)
        ids2 = b.loft(rings, part, True, cap0=False, cap1=True)
        top2 = b.v((c[0], c[1], orb_z(*c) + lift))
        for i in range(ns):
            j = (i + 1) % ns
            b.faces.append(([top2, ids2[0][i], ids2[0][j]], part, True))
        # the chamfer and wall flat shaded, so the cap reads as machined
        nf = ns * (nr - 2)
        for fi_ in range(len(b.faces) - ns - 1 - ns * nr + nf, len(b.faces) - ns - 1):
            ids_, pt, _ = b.faces[fi_]
            b.faces[fi_] = (ids_, pt, False)

    puck(CORE_C, CORE_R, CORE_LIFT, "core")
    puck(CORE_C, LENS_R, CORE_LIFT + LENS_LIFT, "lens", sink=0.1)

    # Crest: pchip centreline by arc length, chamfered trapezoid section, two panel-line notches.
    pts = CREST
    s = [0.0]
    for p, q in zip(pts, pts[1:]):
        s.append(s[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))
    fx, fy = pchip(s, [p[0] for p in pts]), pchip(s, [p[1] for p in pts])
    fw, fh = pchip(s, [p[2] for p in pts]), pchip(s, [p[3] for p in pts])
    total = s[-1]
    ts = [total * i / 24 for i in range(25)]
    for g in GROOVES_T:
        ts += [total * g - GROOVE_W * 3, total * g - GROOVE_W, total * g + GROOVE_W, total * g + GROOVE_W * 3]
    ts = sorted(ts)
    crest_rings = []
    for t in ts:
        x, y, w, h = fx(t), fy(t), fw(t), fh(t)
        e = 1e-3 * total
        dx, dy = fx(min(total, t + e)) - fx(max(0, t - e)), fy(min(total, t + e)) - fy(max(0, t - e))
        ln = math.hypot(dx, dy)
        nx, ny = dy / ln, -dx / ln        # right of travel (travel runs back -> nose, y down)
        notch = any(abs(t - total * g) <= GROOVE_W * 1.01 for g in GROOVES_T)
        top = h - (GROOVE_D if notch else 0.0)
        ch = min(CREST_CH, 0.35 * w)
        prof = [(-w / 2, CREST_Z0), (-w / 2, top - ch), (-w / 2 + ch, top), (w / 2 - ch, top), (w / 2, top - ch),
                (w / 2, CREST_Z0)]
        crest_rings.append([(x + nx * u, y + ny * u, z) for u, z in prof])
    n0 = len(b.faces)
    b.loft(crest_rings, "crest", False)
    # The front of the crest is the orange hook; the colour changes in the first panel line (its
    # front wall), near the sprite's change between rows 4 and 5 (CREST_SPLIT_Y).
    split_y = fy(total * GROOVES_T[0] + GROOVE_W * 1.01)
    print(f"crest colour split at y {split_y:.2f} px (sprite {CREST_SPLIT_Y})")
    for k2 in range(n0, len(b.faces)):
        ids_, pt, sm = b.faces[k2]
        if sum(b.verts[i][1] for i in ids_) / len(ids_) > split_y:
            b.faces[k2] = (ids_, "crest_front", sm)
    return b


# --- Blender objects ----------------------------------------------------------------------------

def to_world(p, c0, r0):
    x, y, z = p
    return ((c0 + x - W / 2) * PX, (H / 2 - (r0 + y)) * PX, z * PX)


DROPPED = []


def build_frame(egg, boxes, mats, coll, name):
    bm = bmesh.new()
    slot = SLOTS
    for c0, r0 in boxes:
        vs = [bm.verts.new(to_world(p, c0, r0)) for p in egg.verts]
        for ids, part, smooth in egg.faces:
            try:
                f = bm.faces.new([vs[i] for i in ids])
            except ValueError:
                DROPPED.append((name, part, len(ids)))
                continue
            if part == "cradle":
                cy = sum(egg.verts[i][1] for i in ids) / len(ids)
                cz = max(egg.verts[i][2] for i in ids)
                if cy > NOSE_Y and cz > Z_WALL - 0.01:
                    part = "nose"
            f.material_index = slot[part]
            f.smooth = smooth
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    open_e = sum(1 for e in bm.edges if not e.is_manifold)
    if open_e:
        print(f"WARNING {name}: {open_e} non-manifold edges")
    obj = common.mesh_object(name, bm, mats, coll, smooth=None)
    obj["_open_edges"] = open_e
    return obj


SHELL_INSIDE = 0.004


def hold_inside(shell, target, d):
    """Pull every shell vertex outside `target` back onto it, `d` inside (the D88 fix). Done here,
    not with outline_shell(inside=d): in Shrinkwrap's INSIDE mode a NEGATIVE offset lands the
    vertex outside the surface (tested: a point above a cube with offset -0.1 ends 0.1 above it),
    so common.outline_shell's offset=-inside leaves the shell `inside` OUTSIDE the model."""
    sw = shell.modifiers.new("inside", "SHRINKWRAP")
    sw.target = target
    sw.wrap_method = "NEAREST_SURFACEPOINT"
    sw.wrap_mode = "INSIDE"
    sw.offset = d
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    shell.select_set(True)
    bpy.context.view_layer.objects.active = shell
    bpy.ops.object.modifier_apply(modifier=sw.name)


def frame_shell(egg, boxes, mats, coll, name, faces=800):
    """The ink-outline shell for a frame: one common.outline_shell per egg (it keeps only the
    largest island, so a three-egg object got a shell on one egg), joined into one object."""
    shells, solos = [], []
    for k, box in enumerate(boxes):
        solo = build_frame(egg, [box], mats, coll, f"{name}_egg{k}")
        bpy.context.view_layer.update()
        sh = common.outline_shell(solo, coll, voxel=0.006, faces=faces, smooth=3)
        hold_inside(sh, solo, SHELL_INSIDE)
        shells.append(sh)
        solos.append(solo)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for sh in shells:
        sh.select_set(True)
    bpy.context.view_layer.objects.active = shells[0]
    bpy.ops.object.join()
    shell = shells[0]
    shell.name = shell.data.name = f"{name}_outline"
    for solo in solos:
        bpy.data.objects.remove(solo, do_unlink=True)
    return shell


def classify(obj, fi, sprite):
    """Ray cast down at each opaque sprite pixel centre: the part (material slot) on top."""
    frame = next(f for f in sprite["frames"] if f["index"] == fi)
    inner = SM.masks(frame["pixels"], {int(k): tuple(v) for k, v in sprite["colors"].items()})["inner"]   # the ink ring is lighting
    deps = bpy.context.evaluated_depsgraph_get()
    hits = {}
    inv = obj.matrix_world.inverted()
    for r in range(H):
        for c in range(W):
            v = frame["pixels"][r][c]
            if v < 0 or not inner[r][c]:
                continue
            o = inv @ Vector(((c + 0.5 - W / 2) * PX, (H / 2 - r - 0.5) * PX, 5.0))
            ok, loc, nrm, idx = obj.ray_cast(o, Vector((0, 0, -1)))
            if ok:
                hits.setdefault(obj.data.polygons[idx].material_index, []).append(v)
    return hits


def trimmed_median(vals):
    v = sorted(vals)
    if len(v) >= 6:
        k = int(len(v) * 0.15)
        v = v[k:len(v) - k]
    return v[(len(v) - 1) // 2]   # lower median on an even count


def render_setup(scene):
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)


def camera(scene, name, loc, look, ortho=None, lens=50):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


def render(scene, cam, path, w, h):
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.camera = cam
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_all(objs, shells, sprite, out, solo):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    render_setup(scene)
    sh = scene.display.shading
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.color = (0.05, 0.05, 0.06)
    k = 10
    top = camera(scene, "top", (0, 0, 10), (0, 0, 0), ortho=max(W, H) * PX)
    top.rotation_euler = (0, 0, 0)
    results = {}
    for fi, obj in objs.items():
        for o in list(objs.values()) + shells + [solo]:
            o.hide_render = o is not obj
        # silhouette for the rule IoU
        sh.light, sh.color_type, sh.single_color = "FLAT", "SINGLE", (1, 1, 1)
        sh.show_cavity = sh.show_object_outline = False
        scene.render.film_transparent = True
        p = out / f"mask_{fi}.png"
        render(scene, top, p, W * k, H * k)
        res = subprocess.run(["python3", str(WT / "tools" / "sprite_mask.py"), NAME, "--frame", str(fi),
                              "--measure", str(p), "--json"], capture_output=True, text=True, cwd=WT)
        try:
            d = json.loads(res.stdout)
            mm = d.get("measure") or d.get("top") or d
            results[fi] = {k2: mm.get(k2) for k2 in ("iou_rule", "iou_rule_grid", "iou_inner")}
            if results[fi]["iou_rule_grid"] is None:
                results[fi] = {kk: vv for kk, vv in d.items() if "iou" in kk or kk == "measure"}
        except Exception:
            results[fi] = {"raw": res.stdout[-600:] + res.stderr[-600:]}
        # lit top view (studio, palette colours)
        sh.light, sh.color_type = "STUDIO", "MATERIAL"
        sh.show_cavity = True
        scene.render.film_transparent = False
        render(scene, top, out / f"top_{fi}.png", W * 16, H * 16)
    # views of frame 277 (one egg close-up and the group)
    for o in list(objs.values()) + shells + [solo]:
        o.hide_render = o is not solo
    sh.light, sh.color_type = "STUDIO", "MATERIAL"
    sh.show_cavity = True
    sh.show_object_outline = True
    # egg 1 centre in world
    ex, ey, zc = 0.0, 0.0, 0.13
    d = 2.2
    views = {
        "side": ((ex + d, ey, zc), (ex, ey, zc), 2.4),
        "side_l": ((ex - d, ey, zc), (ex, ey, zc), 2.4),
        "front": ((ex, ey - d, zc), (ex, ey, zc), 2.4),
        "rear": ((ex, ey + d, zc), (ex, ey, zc), 2.4),
        "q34": ((ex + d * 0.75, ey - d * 0.75, zc + d * 0.75), (ex, ey, zc), 2.4),
        "q34b": ((ex - d * 0.75, ey + d * 0.75, zc + d * 0.75), (ex, ey, zc), 2.4),
        "under": ((ex + 0.3, ey - 0.3, -d), (ex, ey, zc), 2.4),
    }
    for nm, (loc, look, lens_s) in views.items():
        cam = camera(scene, nm, loc, look, ortho=1.05)
        render(scene, cam, out / f"{nm}.png", 480, 480)
    for o in list(objs.values()) + shells + [solo]:
        o.hide_render = o is not objs[277]
    dg = 4.2
    game = camera(scene, "game", (0, -dg * 0.55, dg * 0.85), (0, 0, 0), lens=50)
    render(scene, game, out / "game.png", 640, 640)
    g34 = camera(scene, "g34", (dg * 0.6, -dg * 0.6, dg * 0.5), (0, 0, 0), lens=50)
    render(scene, g34, out / "group34.png", 640, 640)
    return results


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):   # the startup scene's cube, light and camera
        o.hide_render = True
        o.hide_viewport = True
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME + "_A")
    egg = build_egg()

    def mat(index, metallic, rough):
        return common.palette_material(sprite, index, NAME, metallic=metallic, roughness=rough)

    # First pass with provisional colours, to classify which sprite pixels each part covers.
    prov = [mat(117, 0.25, 0.35), mat(116, 0.3, 0.45), mat(115, 0.3, 0.55), mat(121, 0.3, 0.42),
            mat(122, 0.2, 0.3), mat(126, 0.15, 0.25)]
    hits = {k: [] for k in range(len(prov))}
    probe = {}
    frames = [f["index"] for f in sprite["frames"]]
    for i, fi in enumerate(frames):
        o = build_frame(egg, EGGS[fi], prov, coll, f"probe_{fi}")
        bpy.context.view_layer.update()
        for k, v in classify(o, fi, sprite).items():
            hits[k] += v
        probe[fi] = o
    pal = {k: trimmed_median(v) for k, v in hits.items() if v}
    for o in probe.values():
        o.hide_render = o.hide_viewport = True
    print("region palette (orb, crest back, cradle, crest front+nose, core, lens):", pal,
          {k: len(v) for k, v in hits.items()}, {k: sorted(v) for k, v in hits.items()})
    # satin metal; the core and lens a touch glossier (glass-like), no emission (washes out)
    mats = [mat(pal[0], 0.25, 0.34), mat(pal[1], 0.3, 0.42), mat(pal.get(2, 114), 0.3, 0.55),
            mat(pal[3], 0.3, 0.4), mat(pal[4], 0.2, 0.3), mat(pal[5], 0.15, 0.28)]

    objs, shells = {}, []
    sheet = sprite["sprites"][0]
    for i, fi in enumerate(frames):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        o = build_frame(egg, EGGS[fi], mats, coll, name)
        shell = frame_shell(egg, EGGS[fi], mats, coll, name)
        common.frame_part(o, [fi])
        common.frame_part(shell, [fi])
        objs[fi] = o
        shells.append(shell)
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        print(f"frame {fi}: {name} {tris} tris, open edges {o['_open_edges']}, shell {len(shell.data.polygons)} faces")
        common.export_sprite_model(WT, [o, shell], f"enemies/{name}", [{**sheet, "frames": [fi]}])
    print("dropped faces:", len(DROPPED), DROPPED[:10])
    solo_box = [(W / 2 - 4.5, H / 2 - 6.0)]   # one egg centred on the origin, for close-ups
    solo = build_frame(egg, solo_box, mats, coll, "solo")
    solo_shell = frame_shell(egg, solo_box, mats, coll, "solo")
    if "--render" in argv:
        out = Path(argv[argv.index("--render") + 1])
        res = render_all(objs, shells + [solo_shell], sprite, out, solo)
        (out / "metrics.json").write_text(json.dumps({"iou": res, "palette": pal}, indent=1))
        print("IOU", json.dumps(res))


if __name__ == "__main__":
    main()
