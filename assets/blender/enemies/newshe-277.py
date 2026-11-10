"""Three floating fireballs (newshe.shp frames 277, 279, 281, 283): glowing energy orbs.

What it is (object-identity audit, 2026-11; behaviour.txt): enemy types 678 and 681 in 1.18 ALE and
3.7 STARGATE, armour 10, no turret, no launcher; type 678 drifts down 2 px/tick, type 681 weaves
(cacc 20, rev 2). Its frames (277-283, two ticks each) rotate the trio round the group's centre while
each ball stays the same: a spinning cluster of three fireballs, not three pods parked on sleds
(the D116 build). Each sprite ball is a hot white-yellow core (126/127) ringed in orange (119-123)
inside a dark red body (112-117) that narrows to a tail down the screen, with an orange flame lick
running down its right flank into the tail tip.

Each orb (D65 smooth/round object, no foil, D90/D51 outline shell):
- Body: a teardrop of elliptic sections round Z_MID: the plan is the sprite's INNER mask (D74,
  tools/sprite_mask.py) fitted row by row with pchip, squircle-closed at both ends; the section
  half height follows the half width, so the head is a sphere, the tail tapers to a point and the
  underside is round (floating; nothing more there).
- Core and hot ring: flush emissive zones of the body's upper surface centred on the sprite's core
  pixels: thin patches hugging the surface (smooth elliptic edges; glowing colour regions, not
  bumps): core 126, hot band 121-123, outer ring 119/120 (together the sprite's 118+ glow), dim halo.
- Swirl: a flat, tapered flame band sunk into the right flank (a band on the surface, not a limb) (pchip centreline), dim at its
  root, emissive orange from SWIRL_GLOW_Y down, widening to wrap the tail tip (rows 9-10, all
  orange in the sprite); the sprite's dark seam is its
  shadowed edge against the body.
- Colours: each region's palette index is the trimmed median of the sprite pixels it covers from
  above (ray cast), computed per build. Emission per GLOW (core, hot band,
  ring and the flame lick); body and halo matte (high roughness: soft sheen, not a glassy hotspot).
- Per frame one object (3 orbs) + outline shell per orb, frame_part-tagged. The game contract:
  frame i -> model enemies/newshe-277 / -f2 / -f3 / -f4, each replacing its single frame.

Run: blender --background --python assets/blender/enemies/newshe-277.py -- [--render OUTDIR]
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

# Heights (px). The orb floats: every section is an ellipse round Z_MID, so the underside is round
# (seen from the side at the tilted camera) and the bottom stays above the sprite plane.
Z_MID = 3.2
HZ_K, HZ_MAX = 0.86, 3.0      # section half height = HZ_K * plan half width, capped

# Hot core (the sprite's 126/127 at box col 3 rows 3-4, inside a 119-123 ring): flush emissive
# zones of the orb's upper surface, centred on the core pixels. Region colour, not geometry.
CORE_C = (3.5, 4.0)
# Each zone a thin patch hugging the surface (lifted ZONE_LIFT px, so the boundaries are smooth
# ellipses rather than the body's facets): core (126/127), hot ring (119-123), halo (116-117).
# The tail tip (rows 9-10, all 118-123 in the sprite) glows in the swirl's colour, where it ends.
# The glow is the sprite's group of pixels at 118+ (11 px round the core, a 3 x 4 block): the outer
# ring (119/120) spans it, the hot band (121-123, the 7 px round and including the core) sits inside,
# the core (126/127, 2 px) in the middle. All three emit; the halo (116/117) round them is lit.
ZONES = [("halo", CORE_C, (2.45, 2.8), 0.02), ("ring", CORE_C, (1.8, 2.15), 0.035),
         ("mid", CORE_C, (1.3, 1.65), 0.05), ("core", CORE_C, (0.78, 1.12), 0.065),
         ("swirl", (4.5, 9.7), (1.4, 1.15), 0.06)]

# Flame swirl: a tapered band of flame on the orb's right flank from its back down round into the
# tail tip (box cols 7 -> 4, rows 2 -> 10). (x, y, radius) px; the part behind SWIRL_GLOW_Y is the
# sprite's dim root (114-117), the rest the bright orange lick (119-123).
SWIRL = [(7.25, 1.7, 0.18), (7.5, 2.6, 0.42), (7.6, 3.8, 0.6), (7.55, 5.0, 0.72), (7.2, 6.3, 0.8),
         (6.5, 7.45, 0.85), (5.6, 8.5, 0.9), (4.85, 9.4, 1.0), (4.45, 10.25, 0.85), (4.4, 10.95, 0.35)]
SWIRL_WIDTH = 0.55            # band half width / the radius above
SWIRL_LIFT = 0.07             # px the band's top stands over the body surface
SWIRL_SINK = 0.2              # px its underside sits inside the body
SWIRL_GLOW_Y = 4.4
SLOTS = {"body": 0, "ring": 1, "core": 2, "swirl": 3, "halo": 4, "mid": 5}
# Emission per region. In game an emissive material's emissive is the FULL palette colour
# (src/render/modelFrames.ts colourFrame), so emission is on/off. Glowing: the core, its hot band
# and ring, and the flame lick (the bright part of the swirl and the tail tip, as hot as the ring
# in the sprite). The body and halo stay lit so the orb's roundness reads (tested: an emissive body
# washes the whole ball out to flat pink-red in the viewer). Measured in game (STARGATE, tick 796):
# the scene light already brings these reds near 1, so emissive or lit makes little difference to
# the colour (swirl 120: emissive (249, 100, 85), lit (248, 100, 78)); emission keeps them bright on
# the shadowed side.
GLOW = {"body": 0.0, "halo": 0.0, "ring": 1.0, "mid": 1.0, "core": 1.0, "swirl": 1.0}

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


def section_hz(hw):
    return min(HZ_K * hw, HZ_MAX)


def body_top(x, y):
    """Height of the orb's upper surface over (x, y) box px (Z_MID at or beyond the rim)."""
    c, hw = extent(y)
    if hw <= 1e-3:
        return Z_MID
    q = 1 - ((x - c) / hw) ** 2
    return Z_MID + section_hz(hw) * max(q, 0.0) ** 0.5


def zone_patch(b, part, centre, r, lift, nr=6, ns=40, sink=0.15):
    """A closed patch on the body's upper surface inside the ellipse r round `centre`, its top `lift`
    px over the surface, its rim wall sunk `sink` px into the body."""
    cx, cy = centre
    rings = []
    for k in range(1, nr + 1):
        f = k / nr
        rings.append([(cx + r[0] * f * math.cos(2 * math.pi * i / ns), cy + r[1] * f * math.sin(2 * math.pi * i / ns))
                      for i in range(ns)])
    def on_body(x, y):   # keep the patch on the plan (no fold over the rim at the tail tip)
        y = min(y, Y_NOSE - 0.25)
        c, hw = extent(y)
        return min(max(x, c - 0.94 * hw), c + 0.94 * hw), y
    rings = [[on_body(x, y) for x, y in ring] for ring in rings]
    rings = [[(x, y, body_top(x, y) + lift) for x, y in ring] for ring in rings]
    rings.append([(x, y, z - lift - sink) for x, y, z in rings[-1]])
    ids = b.loft(rings, part, True, cap0=False, cap1=True)
    top = b.v((cx, cy, body_top(cx, cy) + lift))
    for i in range(ns):
        b.faces.append(([top, ids[0][i], ids[0][(i + 1) % ns]], part, True))


def build_egg():
    """One fireball orb: a teardrop body (round head, tail to a point down the screen) of elliptic
    sections, and the flame swirl down its right flank."""
    b = Builder()
    seg = 40
    rings = []
    for y in stations():
        c, hw = extent(y)
        hw = max(hw, 0.03)
        hz = section_hz(hw)
        rings.append([(c + hw * math.cos(2 * math.pi * i / seg), y, Z_MID + hz * math.sin(2 * math.pi * i / seg))
                      for i in range(seg)])
    b.loft(rings, "body", True)
    for part, centre, r, lift in ZONES:
        zone_patch(b, part, centre, r, lift)

    # Swirl: a flat band laid on the body's surface along a pchip centreline (by arc length): each
    # section is a thin closed slab, its top SWIRL_LIFT px over the surface, its underside sunk
    # SWIRL_SINK px into the body, clamped onto the plan so it never pokes past the rim (a coloured
    # band of flame on the ball, not a tube or limb).
    pts = SWIRL
    s = [0.0]
    for p, q in zip(pts, pts[1:]):
        s.append(s[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))
    fx, fy, fr = pchip(s, [p[0] for p in pts]), pchip(s, [p[1] for p in pts]), pchip(s, [p[2] for p in pts])
    total = s[-1]

    def on_plan(x, y):
        y = min(max(y, Y_BACK + 0.3), Y_NOSE - 0.25)
        c, hw = extent(y)
        return min(max(x, c - 0.9 * hw), c + 0.9 * hw), y

    us = [-1 + 2 * j / 8 for j in range(9)]
    srings = []
    for k in range(41):
        t = total * k / 40
        x, y, r = fx(t), fy(t), max(fr(t) * SWIRL_WIDTH, 0.04)
        e = 1e-3 * total
        dx, dy = fx(min(total, t + e)) - fx(max(0, t - e)), fy(min(total, t + e)) - fy(max(0, t - e))
        ln = math.hypot(dx, dy)
        nx, ny = dy / ln, -dx / ln
        c, hw = extent(y)   # slide the section in from the rim rather than fold it onto the rim
        x = max(min(x, c + 0.9 * hw - r * abs(nx)), c - 0.9 * hw + r * abs(nx))
        top, bot = [], []
        for u in us:
            px, py = on_plan(x + nx * r * u, y + ny * r * u)
            zt = body_top(px, py)
            top.append((px, py, zt + SWIRL_LIFT))
            bot.append((px, py, zt - SWIRL_SINK))
        srings.append(top + bot[::-1])
    n0 = len(b.faces)
    b.loft(srings, "swirl", True, closed=True)
    for k in range(n0, len(b.faces)):
        ids, _, sm = b.faces[k]
        if sum(b.verts[i][1] for i in ids) / len(ids) < SWIRL_GLOW_Y:
            b.faces[k] = (ids, "body", sm)
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
    ex, ey, zc = 0.0, 0.0, Z_MID * PX
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

    def mat(index, rough, glow=0.0):
        # A glowing part is a fully rough metal (no diffuse, no white specular): in game its emissive
        # is the full palette colour and the light on top pushes it past 1, where the neutral tone
        # mapping pales orange toward salmon. Measured in game (STARGATE): 121 at (231, 97, 12)
        # shows (250, 124, 95) this way against (251, 134, 106) as a lit dielectric; a small gain.
        if glow:
            return common.palette_material(sprite, index, NAME, metallic=1.0, roughness=1.0, emission_strength=1.0)
        return common.palette_material(sprite, index, NAME, metallic=0.0, roughness=rough)

    # First pass with provisional colours, to classify which sprite pixels each part covers.
    prov = [mat(116, 0.4), mat(120, 0.4), mat(126, 0.4), mat(121, 0.4), mat(117, 0.4), mat(122, 0.4)]
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
    print("region palette (body, hot ring, core, swirl, halo, hot band):", pal,
          {k: len(v) for k, v in hits.items()}, {k: sorted(v) for k, v in hits.items()})
    # Energy, not metal or glass: the body and halo a matte ember (rough, so the light gives a soft
    # sheen and the roundness reads, no hard hotspot), the core, hot band, ring and flame lick
    # emissive in their own palette colours.
    mats = [mat(pal[0], 0.88, GLOW["body"]), mat(pal[1], 0.7, GLOW["ring"]), mat(pal[2], 0.7, GLOW["core"]),
            mat(pal[3], 0.7, GLOW["swirl"]), mat(pal[4], 0.85, GLOW["halo"]), mat(pal[5], 0.7, GLOW["mid"])]

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
