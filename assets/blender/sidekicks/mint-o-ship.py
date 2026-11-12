"""Mint-O-Ship sidekick, design A (option 16; tyrian.shp#8 frames 112, 131, 150; 12x14 block).

WHAT IT IS: a trailing companion drone (style 3: it follows the ship's path), a small egg-shaped
pod of satin green metal with a charging lens on top. Not a weapon mount: a self-flying probe,
so it carries its own aft thruster and a small forward emitter.

Reading of the sprite (no ink ring: its edge 192 is luma 28, so the whole 94 px mask is covered,
D74). x is px from the pod's centre line (column edge 7), y the sprite row edge (down = rear), z up:
- Outline: half width 1 / 3 / 4 / 4 / 5 x5 / 4 / 3 / 2 / 1 on rows 0-12: an egg, blunt at the
  nose (2 px jumping to 6), widest rows 4-8, tapering to the tail. Round in plan, so round in
  section: no tiers, no corners.
- Bright streak upper left (207, 140, 143 on rows 2-6): sheen on the polished dome, not geometry.
- Dark crescent below/right of the lens (192-195, rows 7-9) and the bright right rim (200-201 on
  col 10, 205 / 202 at rows 9-10): the terminator and rim light of a lit ball, i.e. lighting. Only
  the lens collar's own shadow is real (the collar stands 0.5 px proud).
- The lens: cols 6-7, rows 5-6 (x -1..1, centre row 6): 203 on 112, 205 with a white-hot pixel
  (47 at col 6 row 5) on 131, white 127 on 150. One lens part recoloured per frame
  (palette_material frames=, D17) plus frame 131's hot bead as a frame part.

Colours (median index per region; the 192 edge ring and the 204-207/140/143 highlights left out):
shell 198 (rows 1-11), belly 195 (unseen: one step darker), collar and trims 194, panel grooves
193, small lights 205.

Engineering detail where the tilted game camera sees it: a recessed equator seam with a running
light each side, two shallow panel grooves (nose cap row 2.5, aft cowl row 10.1), a machined lens
collar with four bolt heads, a recessed forward emitter in the nose and a thruster bell in the
tail. Underside: the plain closed belly.

Scratch design: exports only to this folder.
    Blender -b --factory-startup -P mint-o-ship_A.py -- [--views DIR] [--no-bake]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

ROOT = common.repo_root(__file__)
WT = ROOT
MODEL = "sidekicks/mint-o-ship"
HERE = Path("/Users/dlomibao/projects/tyrian-scratch/sidekicks-2/mint-o-ship/final")  # scratch: bake maps and views
NAME = "sidekick-mint-o-ship"
TAG = "mint-o-ship"
PX = 1 / 12
W, H = 12, 14
F1, F2, F3 = 112, 131, 150
AXIS_COL = 7.0  # the pod's centre line (the block's centre is column edge 6)

(SHELL, BELLY, SEAM, GROOVE, TRIM, LENS, LIGHT, HOT, BORE, COLLAR) = range(10)
TEXTURED = (SHELL, BELLY, SEAM, GROOVE, TRIM, COLLAR)


def materials(sprite):
    pal = common.palette_material
    return [
        pal(sprite, 198, f"{TAG}-shell", metallic=0.5, roughness=0.38),   # satin green shell
        pal(sprite, 195, f"{TAG}-belly", metallic=0.45, roughness=0.5),
        pal(sprite, 193, f"{TAG}-seam", metallic=0.3, roughness=0.6),     # recessed seam walls
        pal(sprite, 193, f"{TAG}-groove", metallic=0.3, roughness=0.6),   # panel grooves
        pal(sprite, 194, f"{TAG}-trim", metallic=0.65, roughness=0.32),   # machined collar, lips
        pal(sprite, 203, f"{TAG}-lens", metallic=0.0, roughness=0.15, emission_strength=0.7,
            frames={F2: 205, F3: 127}),
        pal(sprite, 205, f"{TAG}-light", metallic=0.0, roughness=0.3, emission_strength=0.9),
        pal(sprite, 47, f"{TAG}-hot", metallic=0.0, roughness=0.2, emission_strength=2.5),
        pal(sprite, 192, f"{TAG}-bore", metallic=0.2, roughness=0.7),     # emitter / nozzle throats
        pal(sprite, 198, f"{TAG}-collar", metallic=0.6, roughness=0.3),   # lens housing: the shell's green, machined
    ]


# --- the hull: an egg lofted along y ------------------------------------------------------------

# (row edge, half width px): a smooth line through the sprite's outline steps, checked cell by
# cell against the mask (each inside cell >= 50% covered, each outside cell < 50%).
OUTLINE = [(0.0, 0.0), (0.04, 0.55), (0.14, 0.82), (0.3, 1.02), (0.5, 1.18), (0.7, 1.36), (0.85, 1.58),
           (1.0, 1.98), (1.15, 2.36), (1.3, 2.64), (1.6, 3.02), (2.0, 3.42), (2.5, 3.83), (3.0, 4.15),
           (3.5, 4.42), (4.0, 4.68), (4.5, 4.88), (5.0, 4.98), (6.0, 5.05), (7.0, 5.05), (8.0, 4.95),
           (8.5, 4.8), (9.0, 4.5), (9.5, 4.05), (10.0, 3.55), (10.5, 3.03), (11.0, 2.5), (11.5, 1.95),
           (12.0, 1.42), (12.4, 1.05), (12.7, 0.75), (12.9, 0.45), (13.0, 0.0)]
_ys, _ws = zip(*OUTLINE)
_wf = T.pchip(list(_ys), list(_ws))


def half_width(y):
    return max(0.0, _wf(y))


TOP = 0.95     # dome height / half width at the widest station
BOT = 0.74     # belly depth / half width there
FULL_T, FULL_B = 0.72, 0.8  # height ~ w**FULL: fuller than the plan toward the ends (an egg from the side)


def heights(w):
    return TOP * 5.0 * (w / 5.0) ** FULL_T, BOT * 5.0 * (w / 5.0) ** FULL_B
E_TOP, E_BOT = 2.25, 2.05  # superellipse exponents (full, round shoulders)
SEAM_H = 0.32  # px: half height of the equator seam
SEAM_D = 0.28  # px: its depth
GROOVES = [(2.1, 0.09, 0.11), (10.0, 0.09, 0.11)]  # (row, half width, depth)
NOSE_Y, TAIL_Y = 0.16, 12.72  # the loft's ends: the emitter and the thruster sit in them
NA = 14  # points on each half arc


def se(t, rx, rz, e):
    c, s = math.cos(t), math.sin(t)
    return (rx * math.copysign(abs(c) ** (2 / e), c), rz * math.copysign(abs(s) ** (2 / e), s))


def section(y, inset=0.0):
    """The ring at station y: [(x, z, material of the band from this point to the next)].
    Upper arc (shell), left seam notch, lower arc (belly), right seam notch."""
    w = half_width(y)
    rt, rb = heights(w)
    h = min(SEAM_H, 0.3 * rb)
    d = min(SEAM_D, 0.12 * w)
    a0 = math.asin(min(0.999, (h / rt) ** (E_TOP / 2)))
    b0 = math.asin(min(0.999, (h / rb) ** (E_BOT / 2)))
    pts = []
    for i in range(NA + 1):
        t = a0 + (math.pi - 2 * a0) * i / NA
        x, z = se(t, w, rt, E_TOP)
        pts.append((x, z, SHELL if i < NA else SEAM))
    xl = pts[-1][0]
    pts.append((xl + d, h, SEAM))
    pts.append((xl + d, -h, SEAM))
    for i in range(NA + 1):
        t = math.pi + b0 + (math.pi - 2 * b0) * i / NA
        x, z = se(t, w, rb, E_BOT)
        pts.append((x, z, BELLY if i < NA else SEAM))
    xr = pts[-1][0]
    pts.append((xr - d, -h, SEAM))
    pts.append((xr - d, h, SEAM))
    if inset:
        k = max(0.0, (w - inset) / w)
        pts = [(x * k, z * k, m) for x, z, m in pts]
    return pts


def stations():
    """Loft stations: dense at the round ends (cosine spacing), with each groove's four rings."""
    n = 36
    ys = [NOSE_Y + (TAIL_Y - NOSE_Y) * (1 - math.cos(math.pi * i / n)) / 2 for i in range(n + 1)]
    out = [(y, 0.0, None) for y in ys]
    for yg, gw, gd in GROOVES:
        out = [s for s in out if abs(s[0] - yg) > gw * 1.6]
        out += [(yg - gw, 0.0, None), (yg - gw * 0.55, gd, GROOVE), (yg + gw * 0.55, gd, GROOVE),
                (yg + gw, 0.0, None)]
    return sorted(out)


def build_hull(P):
    sts = stations()
    rings = []
    for y, ins, mat in sts:
        sec = section(y, ins)
        rings.append(([P.v((x, y, z)) for x, z, _ in sec], [m for _, _, m in sec], y, mat))
    n = len(rings[0][0])
    for (r0, m0, y0, g0), (r1, m1, y1, g1) in zip(rings, rings[1:]):
        band = GROOVE if (g0 is not None or g1 is not None) else None
        for i in range(n):
            j = (i + 1) % n
            mat = band if band is not None and m0[i] != SEAM else m0[i]
            q = (r0[i], r0[j], r1[j], r1[i])
            if i in (NA, 2 * NA + 5):      # the seam notch's upper walls face down into it
                P.f(q, mat, out=(0, 0, -1))
            elif i in (NA + 2, 2 * NA + 3):  # its lower walls face up
                P.f(q, mat, out=(0, 0, 1))
            else:
                P.f(q, mat, away=(0, (y0 + y1) / 2, 0))
    return rings[0][0], rings[-1][0]


def ring_end(P, ring, y, step, depth, lip_k, bore_k, glow, sign):
    """Close a loft end with a recessed port: a flat lip (TRIM) stepping in to lip_k of the ring,
    a bore wall `depth` deep (BORE) and a glowing disc at its bottom. sign -1 = nose (faces -y)."""
    cz = 0.0
    pts = [(v.co.x, v.co.z) for v in ring]
    # Round port: each ring vertex steps in to a circle along its own angle (the hull's seam notch
    # stays out of the port).
    rmin = min(math.hypot(x, z) for x, z in pts)
    circ = [(math.cos(math.atan2(z, x)), math.sin(math.atan2(z, x))) for x, z in pts]
    lip = [P.v((c * rmin * lip_k, y, s * rmin * lip_k)) for c, s in circ]
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        P.f((ring[i], ring[j], lip[j], lip[i]), TRIM, out=(0, sign, 0))
    yb = y - sign * depth
    bot = [P.v((c * rmin * bore_k, yb, s * rmin * bore_k)) for c, s in circ]
    for i in range(n):
        j = (i + 1) % n
        mx, mz = (lip[i].co.x + lip[j].co.x) / 2, (lip[i].co.z + lip[j].co.z) / 2
        P.f((lip[i], lip[j], bot[j], bot[i]), BORE, out=(-mx, 0, cz - mz))  # the bore wall faces its axis
    P.f(bot, glow, out=(0, sign, 0))
    del step


# --- lathe parts round a vertical axis ----------------------------------------------------------

def lathe_v(P, cx, cy, prof, matf, n, cap_top=True):
    """Revolve [(r, z)] round the vertical axis at (cx, cy); matf(k) gives band k's material; the
    last point is capped with a fan-free n-gon when cap_top."""
    rings = []
    for r, z in prof:
        rings.append([P.v((cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z))
                      for i in range(n)])
    for k, (a, b) in enumerate(zip(rings, rings[1:])):
        zc = (prof[k][1] + prof[k + 1][1]) / 2
        for i in range(n):
            j = (i + 1) % n
            P.f((a[i], a[j], b[j], b[i]), matf(k), away=(cx, cy, zc - 2.0))
    if cap_top:
        P.f(rings[-1], matf(len(prof) - 1), out=(0, 0, 1))


def shell_top(x, y):
    w = half_width(y)
    if abs(x) >= w:
        return 0.0
    t = (1 - (abs(x) / w) ** E_TOP) ** (1 / E_TOP)
    return heights(w)[0] * t


LENS_X, LENS_Y = 0.0, 6.0
LENS_R = 1.05


def build_lens(P):
    base = shell_top(LENS_X, LENS_Y)
    sink = base - 0.45
    # The collar: rises out of the dome, a chamfered rim, a seat for the lens.
    top = base + 0.42
    prof = [(1.47, sink), (1.47, base - 0.05), (1.44, top - 0.1), (1.35, top), (1.17, top), (1.11, top - 0.08),
            (1.09, top - 0.18)]
    lathe_v(P, LENS_X, LENS_Y, prof, lambda k: COLLAR if k < 4 else TRIM, 20, cap_top=False)
    seat = top - 0.18
    # The lens: a low glowing dome in the seat.
    lp = []
    for k in range(7):
        a = (math.pi / 2) * k / 6
        lp.append((LENS_R * math.cos(a) if k < 6 else 0.0, seat + 0.42 * math.sin(a)))
    lp[-1] = (0.08, seat + 0.42)
    lathe_v(P, LENS_X, LENS_Y, [(1.09, seat)] + lp, lambda k: LENS, 20, cap_top=True)
    # Four bolt heads on the collar rim.
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        bx, by = LENS_X + 1.26 * math.cos(a), LENS_Y + 1.26 * math.sin(a)
        pts = []
        for m in range(6):
            b = 2 * math.pi * m / 6
            pts += [(bx + 0.075 * math.cos(b), by + 0.075 * math.sin(b), top - 0.05),
                    (bx + 0.055 * math.cos(b), by + 0.055 * math.sin(b), top + 0.06)]
        T.hull(P, pts, TRIM)
    return seat


def build_hot(P, seat):
    """Frame 131's white-hot pixel (col 6, row 5): a bright bead on the lens, up and left."""
    bx, by = -0.42, 5.55
    rr = math.hypot(bx - LENS_X, by - LENS_Y)
    zs = seat + 0.42 * math.sqrt(max(0.0, 1 - (rr / LENS_R) ** 2))
    prof = [(0.5, zs - 0.12)] + [(0.5 * math.cos(a), zs - 0.12 + 0.24 * math.sin(a))
                                 for a in (0.5, 1.0, 1.35)] + [(0.05, zs + 0.12)]
    lathe_v(P, bx, by, prof, lambda k: HOT, 14, cap_top=True)


def build_lights(P):
    """A running light set in the equator seam each side (rows 6.7-7.7)."""
    for s in (1, -1):
        w = half_width(7.2)
        x0, x1 = sorted((s * (w - SEAM_D - 0.05), s * (w - 0.06)))
        T.hull(P, T.cbox(x0, x1, 6.7, 7.7, -SEAM_H + 0.07, SEAM_H - 0.07, 0.06), LIGHT)


def build(sprite, coll):
    P = T.Part(TAG, smooth_angle=40)
    nose, tail = build_hull(P)
    ring_end(P, nose, NOSE_Y, 0, 0.32, 0.86, 0.72, LIGHT, -1)   # forward emitter
    ring_end(P, tail, TAIL_Y, 0, 0.42, 0.88, 0.66, LIGHT, 1)   # thruster bell
    seat = build_lens(P)
    build_lights(P)
    hp = T.Part(f"{TAG}-hot", smooth_angle=60)
    build_hot(hp, seat)
    mats = materials(sprite)
    body = finish(P, mats, coll, TAG)
    hot = finish(hp, mats, coll, f"{TAG}-hot-131")
    common.frame_part(hot, [F2])
    return body, hot


def finish(P, mats, coll, name):
    P.orient()
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, (AXIS_COL - W / 2) * PX), (0, -PX, 0, H / 2 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(P.smooth_angle))
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    return obj


def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    bpy.context.view_layer.update()
    T.TINT, T.TEXTURED = (0.97, 1.0, 0.97), TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=512, samples=48)
    finally:
        T.TINT, T.TEXTURED = tint, textured


# --- measurement and views (scratch only) -------------------------------------------------------

BASE_RGB = {}


def set_frame(objs, frame):
    """Preview only: recolour per-frame materials and show frame parts as the game does."""
    for obj in objs:
        if "tyrian_frames" in obj.keys():
            obj.hide_render = frame not in list(obj["tyrian_frames"])
        for mat in obj.data.materials:
            bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if mat.name not in BASE_RGB:
                BASE_RGB[mat.name] = tuple(bsdf.inputs["Base Color"].default_value)
            rgbmap = mat.get("tyrian_frame_rgb")
            if rgbmap is None:
                continue
            rgb = rgbmap.get(str(frame))
            col = (*rgb, 1.0) if rgb is not None else BASE_RGB[mat.name]
            col = tuple(col[:3]) + (1.0,)
            bsdf.inputs["Base Color"].default_value = col
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = col


def pal_grid(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(deps)
    rows = []
    for r in range(H):
        row = []
        for c in range(W):
            X, Y = (c + 0.5 - W / 2) * PX, (H / 2 - (r + 0.5)) * PX
            hit, loc, nrm, fi = ev.ray_cast(Vector((X, Y, 5.0)), Vector((0, 0, -1)))
            if not hit:
                row.append(-1)
                continue
            mat = obj.data.materials[ev.data.polygons[fi].material_index]
            row.append(int(mat.name.split("_")[1]))
        rows.append(row)
    return rows


def cam(scene, name, loc, look, ortho=None, lens=50):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    c = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return c


def top_mask(objs, path):
    scene = bpy.context.scene
    for o in scene.objects:
        o.hide_render = o not in objs
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    K = 20
    scene.render.resolution_x, scene.render.resolution_y = W * K, H * K
    scene.render.resolution_percentage = 100
    c = cam(scene, "top_mask", (0, 0, 10), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    scene.camera = c
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def lit_views(objs, out):
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o not in objs and o.name != "ground"
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.16, 0.18, 0.2, 1)
    bg.inputs[1].default_value = 0.7
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(35), math.radians(-30), math.radians(20))
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.8
    scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(-60), math.radians(40), 0)
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, -0.6))
    g = bpy.context.active_object
    g.name = "ground"
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.1, 0.09, 0.11, 1)
    g.data.materials.append(gm)
    V = 400
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 2.6
    tilt = math.radians(32)
    cx = (AXIS_COL - W / 2) * PX
    look = (cx, 0, 0)
    views = [
        ("top", (cx, 0, d), 1.35, F1), ("side", (cx + d, 0, 0), 1.35, F1), ("front", (cx, d, 0), 1.1, F1),
        ("rear", (cx, -d, 0), 1.1, F1), ("q34", (cx + d * 0.62, d * 0.62, d * 0.62), None, F1),
        ("q34b", (cx - d * 0.62, -d * 0.62, d * 0.5), None, F1),
        ("game112", (cx, -d * math.sin(tilt), d * math.cos(tilt)), None, F1),
        ("game131", (cx, -d * math.sin(tilt), d * math.cos(tilt)), None, F2),
        ("game150", (cx, -d * math.sin(tilt), d * math.cos(tilt)), None, F3),
        ("under", (cx + d * 0.45, d * 0.45, -d * 0.6), None, F1),
    ]
    for name, loc, ortho, frame in views:
        set_frame(objs, frame)
        g.hide_render = name in ("under", "side", "front", "rear")
        c = cam(scene, f"v_{name}", loc, look, ortho=ortho, lens=95 if not name.startswith("game") else 75)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out / f"v_{name}.png")
        bpy.ops.render.render(write_still=True)
    set_frame(objs, F1)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(TAG)
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    body, hot = build(sprite, coll)
    T.cull_hidden(body)
    tris = sum(len(p.vertices) - 2 for o in (body, hot) for p in o.data.polygons)
    print(f"{TAG}: {tris} triangles")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        hot.hide_render = True
        top_mask([body], views / "top.png")
        (views / "pal.json").write_text(json.dumps(pal_grid(body)))
    fmt = "AUTO"
    for o in bpy.data.objects:
        o.hide_render = False
    if "--no-bake" not in argv:
        bd = HERE / "bake"
        bd.mkdir(parents=True, exist_ok=True)
        bake(body, bd)
        fmt = "WEBP"
    sh = common.outline_shell(body, coll, voxel=0.008, faces=1200, smooth=8)
    common.export_sprite_model(ROOT, [body, hot, sh], MODEL, sprite["sprites"], image_format=fmt)
    if views:
        sh.hide_render = True
        lit_views([body, hot], views)
    (HERE / "stats.json").write_text(json.dumps({"triangles": tris}))


if __name__ == "__main__":
    main()
