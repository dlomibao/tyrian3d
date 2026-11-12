"""Twin red missiles (newshf.shp frame 169, ground unit, episodes 1-4): a hard-surface 3D version
of the sprite (D50-D53 style, plan to the inner edge of the ink, D74). One frame, one model.

Reading of the sprite (24x28, two identical missiles 12 px apart, light from the upper left). In
game (level 1.8 SAVARA) the big red ship launches them in pairs from its racks: they fly DOWN the
screen trailing smoke, so the sprite's bottom is the nose and its top the exhaust.
- Body: a round tube 4 px across inside its ink (columns 4-7): lit stripe at column 4, shadow at
  6-7, a dark line beside the centre down its length = the seam between two armour half-shells.
- Tail (rows 4-7): two prongs (columns 4 and 7) either side of a dark socket (row 6) = the two upper
  fins of an X tail running past the body's end, either side of the main nozzle. The lower two
  fins are under them (hidden from above).
- Rows 8-15: the plan swells to 8 px: a strap-on booster on each flank (columns 2 and 9: its nozzle
  rim lit at row 9, a dark groove at row 10, its nose cone faired into the body at rows 13-15),
  on a recessed dark pylon (columns 3 and 8). Clamp rings round the body hold them.
- Rows 17-18: a purple band right round the body.
- Row 22: dark neck (the warhead joint); rows 23-24: cruciform canards round a lighter collar (side
  canards to columns 3 and 8, the top one's lit edge at columns 5-6, dark body between at 4 and 7);
  rows 25-26: the ogive nose and its radome tip.
Plan to the inner edge of the ink border (D74). Colours: each part's median palette index with the
darkest shading and the brightest highlights left out: body 69, boosters, clamps and radome 71, tail
fins 70, band 87, canard roots 73 (the gaps between them 67), pylons and nozzle rims 67, seams 66, nozzle throats 64.

Coordinates while building: sprite px, x = column edge - 12, y = row edge (down), z up;
usp_talon.finish moves them to Blender (X = x / 12, Y = (14 - y) / 12, Z = z / 12).

    blender --background --python assets/blender/enemies/newshf-169.py -- [--no-bake] [--views DIR]

Exports public/models/enemies/newshf-169.glb and src/render/spriteModels/newshf-169.json. The AO /
roughness maps bake to assets/blender/textures/newshf-169/bake/ (git-ignored); --views DIR renders
check views and the top-view palette grid there.
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, hull, loft_rings, pchip, plate  # noqa: E402

NAME = "newshf-169"
REPO = common.repo_root(__file__)
MODEL = f"enemies/{NAME}"
PX = 1 / 12
POD_X = 6.0  # pod centres: column edges 6 and 18

# Material slots and their palette indices.
BODY, CANISTER, PRONG, BAND, FIN, PYLON, SOCKET, NOZZLE, DEEP, CORE, SEAMC = range(11)
PAL_OF = {BODY: 69, CANISTER: 71, PRONG: 70, BAND: 87, FIN: 73, PYLON: 67, SOCKET: 64,
          NOZZLE: 67, DEEP: 64, CORE: 68, SEAMC: 66}
TEXTURED = (BODY, CANISTER, PRONG, BAND, FIN, PYLON, SOCKET, NOZZLE, DEEP, CORE, SEAMC)
TINT = (1.0, 0.97, 0.94)


def materials(sprite):
    def pal(slot, tag, metallic, roughness):
        return common.palette_material(sprite, PAL_OF[slot], f"twinpod_{tag}", metallic=metallic,
                                       roughness=roughness)
    return [
        pal(BODY, "body", 0.2, 0.4),
        pal(CANISTER, "canister", 0.25, 0.36),
        pal(PRONG, "prong", 0.3, 0.34),
        pal(BAND, "band", 0.15, 0.45),
        pal(FIN, "fin", 0.2, 0.38),
        pal(PYLON, "pylon", 0.15, 0.55),
        pal(SOCKET, "socket", 0.05, 0.85),
        pal(NOZZLE, "nozzle", 0.3, 0.5),
        pal(DEEP, "deep", 0.05, 0.9),
        pal(CORE, "core", 0.15, 0.55),
        pal(SEAMC, "seam", 0.1, 0.7),
    ]


# --- the body: a 16-gon core with two armour half-shells over it -------------------------------

N = 16          # vertex k at 90 - k * 22.5 degrees: 0 top, 4 outboard right, 8 keel, 12 left
SHELL = 0.22    # how far the half-shells stand proud of the core
R_OUT = 2.0     # plan half width of the body (inner edge of the ink: columns 4-7)
R_CORE = R_OUT - SHELL
SEAM = 0.16  # half the top seam's gap, in loop steps


def ring(cx, cz, r, n=N, rz=None, phase=0.0):
    rz = r if rz is None else rz
    return [(cx + r * math.cos(math.radians(90 - (k + phase) * 360 / n)),
             cz + rz * math.sin(math.radians(90 - (k + phase) * 360 / n))) for k in range(n)]


# Core radius along the body: the nose socket's floor at 7.25, full radius to the boat tail
# (rows 25-26 narrow to the nozzle).
CORE_Y = [7.25, 21.6, 22.0, 22.9, 25.0, 25.5, 25.9, 26.2]
CORE_R = pchip([7.25, 22.0, 24.9, 25.5], [R_CORE, R_CORE, R_CORE, 1.4])
NECK_R = R_CORE - 0.12


def body_loop(cx):
    def f(y):
        r = CORE_R(y)
        if 21.75 <= y <= 22.85:
            r = NECK_R
        return ring(cx, 0.0, r), (cx, 0.0)
    return f


def build_body(P, D, cx):
    L = body_loop(cx)
    ys = [7.25, 7.6, 8.0, 15.0] + [21.75, 21.75, 22.85, 22.85] + [23.5, 24.4, 24.9, 25.2, 25.5]
    # The neck steps: a ring loft with a recess (rows 21.75-22.85: the dark neck at row 22).
    rings = []
    for y in ys:
        rings.append(y)
    built = []
    for i, y in enumerate(ys):
        if y == 21.75 and (i + 1 < len(ys) and ys[i + 1] == 21.75):
            r = R_CORE
        elif y == 21.75:
            r = NECK_R
        elif y == 22.85 and ys[i - 1] != 22.85:
            r = NECK_R
        elif y == 22.85:
            r = R_CORE
        else:
            r = CORE_R(y)
        built.append(([P.v((x, y, z)) for x, z in ring(cx, 0.0, r)], (cx, y, 0.0), y))
    for (r0, c0, y0), (r1, c1, y1) in zip(built, built[1:]):
        mat = CORE if 21.7 < (y0 + y1) / 2 < 22.9 else (SEAMC if y1 < 22 else BODY)
        for a in range(N):
            b = (a + 1) % N
            if abs(y1 - y0) < 1e-6:
                P.f((r0[a], r0[b], r1[b], r1[a]), CORE, out=(0, 1 if y0 < 22 else -1, 0))
            else:
                P.f((r0[a], r0[b], r1[b], r1[a]), mat, away=c0)
    P.f(built[0][0], SOCKET, out=(0, -1, 0))
    P.f(built[-1][0], DEEP, out=(0, 1, 0))

    def LS(y):
        return ring(cx, 0.0, R_CORE), (cx, 0.0)

    # Armour: the nose ring (rows 7-7.9), the guidance section's half-shells (8.0-15.95), the
    # lower body's half-shells (16.05-16.85, 19.15-21.6), the purple band right round (17-19), the
    # tail shells (22.95-25.0). Half-shells split along the top and keel centre lines: the dark
    # seam down the sprite's body.
    plate(P, LS, 7.0, 7.9, BODY, d=SHELL, c=0.14, depth=0.42, ystep=1.0)
    for y0, y1, mat in ((8.0, 15.95, BODY), (16.05, 16.85, BODY), (19.15, 21.6, BODY)):
        plate(P, LS, y0, y1, mat, SEAM, 8 - SEAM, d=SHELL, c=0.1, ystep=8.0)
        plate(P, LS, y0, y1, mat, 8 + SEAM, 16 - SEAM, d=SHELL, c=0.1, ystep=8.0)
    # The canard collar (rows 23-24): a fin-coloured root saddle under each canard (top at loop
    # step 0, sides at 4 and 12, on round under the keel), and between the top and side ones, in the 45-degree gaps, recessed
    # dark panels (the sprite's dark columns 4 and 7 between the canard roots: col 4 is on the lit
    # side, so that darkness is a real gap, not shading).
    GAP = 0.05
    for a0, a1, mat, dd in ((SEAM, 1.25, FIN, SHELL), (1.25 + GAP, 3.4 - GAP, PYLON, SHELL - 0.1),
                            (3.4, 8 - SEAM, FIN, SHELL)):  # under the side canards: plain
        for base in (0, 8):
            # the second half-shell mirrors the first about the top/keel line (s -> 16 - s)
            s0, s1 = (a0, a1) if base == 0 else (16 - a1, 16 - a0)
            plate(P, LS, 22.95, 24.95, mat, s0, s1, d=dd, c=0.08, ystep=8.0)
    plate(P, LS, 16.95, 19.05, BAND, d=SHELL + 0.06, c=0.1, ystep=4.0)
    # Wiring tunnels along the lower flanks (rows 16-21.5), under the plan's edge: the cable
    # runs from the guidance section to the tail, clipped on at the band.
    for side in (-1, 1):
        a = math.radians(-42)
        x0, z0 = cx + side * (R_OUT + 0.05) * math.cos(a), (R_OUT + 0.05) * math.sin(a)
        tx, tz = side * math.cos(a), math.sin(a)  # outward
        pts = []
        for y in (16.1, 21.5):
            for o, u in ((-0.4, -0.3), (0.12, -0.2), (0.12, 0.2), (-0.4, 0.3)):
                # o: outward from the shell surface, u: along the section's tangent
                px = x0 + tx * o + (-tz * side) * u
                pz = z0 + tz * o + (tx * side) * u
                pts.append((px, y, pz))
        hull(D, pts, NOZZLE)

    # Clamp rings round the guidance section where the canister pylons attach.
    for y0, y1 in ((9.15, 9.75), (15.2, 15.8)):
        plate(D, LS, y0, y1, CANISTER, d=SHELL + 0.22, c=0.1, depth=0.5, ystep=1.0)

    # The warhead (rows 25-26; the missile flies down the screen, so the sprite's bottom is its
    # nose): an ogive from the canard collar, then a radome with a seam ring where they meet.
    nose = [(24.95, R_OUT - 0.04), (25.3, 1.82), (25.65, 1.5), (25.95, 1.2)]
    radome = [(25.95, 1.1), (26.3, 0.9), (26.6, 0.66), (26.82, 0.42), (26.95, 0.2)]
    built = [([P.v((x, y, z)) for x, z in ring(cx, 0.0, r)], (cx, y, 0.0)) for y, r in nose + radome]
    for i, ((r0, c0), (r1, _)) in enumerate(zip(built, built[1:])):
        mat = BODY if i < len(nose) - 1 else (SEAMC if i == len(nose) - 1 else CANISTER)
        for a in range(N):
            b = (a + 1) % N
            if i == len(nose) - 1:
                P.f((r0[a], r0[b], r1[b], r1[a]), mat, out=(0, 1, 0))
            else:
                P.f((r0[a], r0[b], r1[b], r1[a]), mat, away=c0)
    tip = P.v((cx, 27.0, 0.0))
    for a in range(N):
        b = (a + 1) % N
        P.f((built[-1][0][a], built[-1][0][b], tip), CANISTER, out=(0, 1, 0))


# --- the tail (rows 4-8): main nozzle between X-tail fins ---------------------------------------

FIN_ANGLES = (55, 125, -55, -125)  # degrees from +x in the section: two up (the sprite's prongs), two down


def build_tail(P, D, cx):
    # Four swept tail fins in an X. Seen from above the upper two are the sprite's prongs (columns 4
    # and 7, rows 5-7): they run past the body's end either side of the main nozzle (the dark socket
    # at row 6). Planform (radius, row), a wedge section: full thickness at the root, thin edges.
    plan = [(1.7, 10.4, 0.21), (3.3, 8.6, 0.08), (3.3, 5.35, 0.08), (3.05, 5.05, 0.08), (1.75, 5.05, 0.16),
            (1.7, 7.0, 0.21)]
    for deg in FIN_ANGLES:
        a = math.radians(deg)
        ux, uz = math.cos(a), math.sin(a)
        nx, nz = -math.sin(a), math.cos(a)
        pts = []
        for r, y, t in plan:
            for s_ in (-t, t):
                pts.append((cx + r * ux + s_ * nx, y, r * uz + s_ * nz))
        hull(D, pts, PRONG)
    # The main nozzle inside the rear ring: a dark bell narrowing to the throat, a plug cone in it.
    n = 12
    bell = [(7.02, 1.3), (7.4, 1.05), (7.8, 0.72)]
    rings_ = [[D.v((x, y, z)) for x, z in ring(cx, 0.0, r, n)] for y, r in bell]
    for k, (r0, r1) in enumerate(zip(rings_, rings_[1:])):
        for a in range(n):
            b = (a + 1) % n
            m = (r0[a].co + r0[b].co + r1[a].co + r1[b].co) / 4
            D.f((r0[a], r0[b], r1[b], r1[a]), NOZZLE if k == 0 else DEEP, out=(cx - m.x, -0.6, -m.z))
    plug = D.v((cx, 7.15, 0.0))
    for a in range(n):
        b = (a + 1) % n
        D.f((rings_[-1][a], rings_[-1][b], plug), DEEP, out=(0, -1, 0))


# --- strap-on boosters (rows 8-15, columns 2 and 9) -----------------------------

CAN_Y = [8.95, 13.2, 14.3, 15.0, 15.5, 15.9]
CAN_R = pchip(CAN_Y, [0.84, 0.84, 0.84, 0.66, 0.44, 0.18])
CAN_X = pchip([8.2, 13.2, 14.3, 15.0, 15.5, 15.9], [3.17, 3.17, 3.13, 2.88, 2.6, 2.32])
CAN_Z = pchip([8.2, 13.2, 15.9], [0.05, 0.05, 0.25])


def build_canisters(P, D, cx):
    for side in (-1, 1):
        def L(y, grow=0.0, side=side):
            r = CAN_R(y) + grow
            c = (cx + side * CAN_X(y), CAN_Z(y))
            return ring(c[0], c[1], r, 12, phase=0.5), c
        # Strap-on booster: its nozzle at the rear (row 8, the sprite's top), a dark exit; a
        # groove at row 10; its nose cone faired into the body at rows 14-15.
        rings = [(L, 8.45, -0.34), (L, 8.85, -0.44), (L, 8.85, -0.12), (L, 8.95, 0.0),
                 (L, 10.1, 0.0), (L, 10.1, -0.16), (L, 10.6, -0.16), (L, 10.6, 0.0)]
        rings += [(L, y, 0.0) for y in (13.2, 14.3, 15.0, 15.5, 15.9)]
        mats = []
        for (_, y0, g0), (_, y1, g1) in zip(rings, rings[1:]):
            mats.append(NOZZLE if y1 <= 8.85 + 1e-6 else
                        PYLON if (g0 < 0 and g1 < 0) or (abs(y0 - y1) < 1e-6) else CANISTER)
        loft_rings(P, rings, mats, cap0=False)
        c0 = (cx + side * CAN_X(8.5), CAN_Z(8.5))
        hull(D, [(x, y, z) for y in (8.47, 8.7) for x, z in ring(c0[0], c0[1], 0.44, 12, phase=0.5)], DEEP)
        # The pylon between canister and body: a dark web, low between them (the sprite's dark gap
        # at columns 3 and 8), rising aft into a fairing where the canister's tail turns in.
        # Forward of row 13 the web becomes the booster's nose fairing, in the canister's colour
        # (the sprite's bright column 3 at rows 13-14, where the nose cone turns into the body).
        for stations, mat in ((((8.25, 0.5, 3.0), (9.0, 0.6, 3.05), (13.0, 0.6, 3.05)), PYLON),
                              (((12.95, 0.6, 3.05), (14.1, 0.9, 2.95), (15.2, 1.0, 2.7),
                                (15.85, 0.75, 2.4)), CANISTER)):
            pts = []
            for y, zt, xo in stations:
                for x, z in ((1.4, zt), (xo - 0.1, zt), (xo, zt - 0.15), (xo, -0.6), (1.4, -0.75)):
                    pts.append((cx + side * x, y, z))
            hull(D, pts, mat)
        # Two bolts on the clamp collars' tops, either side of the pylon.
        for y in (9.45, 15.5):
            hull(D, [(cx + side * x, yy, z) for x, yy, z in
                     cbox(1.35, 1.75, y - 0.18, y + 0.18, 1.55, 2.08, 0.06)], CANISTER)


# --- cruciform canards round the warhead collar (rows 23-24) ----------------------------------------------------------

def build_fins(P, D, cx):
    t = 0.24  # half thickness
    for side in (-1, 1):
        # side fin: root chord 22.75-25.3 at the body, tip chord 23.05-24.95 at column 3's outer edge
        pts = []
        for x, y0, y1 in ((1.6, 22.7, 25.35), (2.98, 23.06, 24.92)):
            for y in (y0, y1):
                yy = y + (0.12 if y == y0 else -0.12)
                pts += [(cx + side * x, y, -0.05), (cx + side * x, yy, -t - 0.05), (cx + side * x, yy, t - 0.05)]
        hull(D, pts, FIN)
    for sz in (1, -1):
        # top fin (and its twin under the keel): an edge-on blade on the centre line, 1 px over the body
        pts = []
        for z, y0, y1 in ((1.5, 22.6, 25.4), (2.95, 23.0, 24.95)):
            for y in (y0, y1):
                yy = y + (0.12 if y == y0 else -0.12)
                pts += [(cx, y, sz * z), (cx - t, yy, sz * z), (cx + t, yy, sz * z)]
        hull(D, pts, FIN)


def build(coll, sprite):
    mats = materials(sprite)
    parts = []
    for cx in (-POD_X, POD_X):
        P = Part(f"twinpod_body_{cx:+.0f}", smooth_angle=35)
        D = Part(f"twinpod_detail_{cx:+.0f}", smooth_angle=35)
        build_body(P, D, cx)
        build_tail(P, D, cx)
        build_canisters(P, D, cx)
        build_fins(P, D, cx)
        parts += [P, D]
    return [T.finish(p, mats, coll) for p in parts], mats


def bake_maps(obj, out_dir, size=512, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "twinpod")


# --- views and measurements (scratch only) ------------------------------------------------------

def pal_grid(obj):
    """Palette index of the face seen from straight above at each sprite pixel's centre."""
    deps = bpy.context.evaluated_depsgraph_get()
    rows = []
    for r in range(28):
        row = []
        for c in range(24):
            X, Y = (c + 0.5 - 12) * PX, (14 - (r + 0.5)) * PX
            hit, loc, nrm, fi = obj.ray_cast(Vector((X, Y, 5.0)), Vector((0, 0, -1)))
            if not hit:
                row.append(-1)
                continue
            m = obj.data.materials[obj.data.polygons[fi].material_index]
            row.append(int(m.name.split("_")[1]))
        rows.append(row)
    return rows


def render_views(obj, shells, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in list(scene.objects):
        if o is not obj and o not in shells:
            bpy.data.objects.remove(o, do_unlink=True)
    # 1. top mask: flat, no shell, on the sprite's grid (k = 10)
    for sh in shells:
        sh.hide_render = True
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    K = 10
    scene.render.resolution_x, scene.render.resolution_y = 24 * K, 28 * K
    scene.render.resolution_percentage = 100

    def cam(name, loc, look, ortho=None, lens=50):
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

    top = cam("top", (0, 0, 10), (0, 0, 0), ortho=28 / 12)
    top.rotation_euler = (0, 0, 0)
    scene.camera = top
    scene.render.filepath = str(out / "top_mask.png")
    bpy.ops.render.render(write_still=True)
    # 2. lit views with Eevee, the outline shell drawn as an inverted black hull is not needed here
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
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
    bg.inputs[0].default_value = (0.05, 0.05, 0.06, 1)
    bg.inputs[1].default_value = 0.6
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    scene.collection.objects.link(sun)
    sun.rotation_euler = (Vector((0.5, -0.6, -1.0))).to_track_quat("-Z", "Y").to_euler()  # from upper left
    sun.rotation_euler = (math.radians(40), math.radians(-30), math.radians(20))
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.9
    scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(-60), math.radians(40), 0)
    V = 400
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 3.4
    views = {
        "top": ((0, 0, d), 2.6, True),
        "side": ((d, 0, 0), 2.6, True),
        "front": ((0, d, 0), 2.6, True),
        "rear": ((0, -d, 0), 2.6, True),
        "q34": ((d * 0.55, d * 0.55, d * 0.6), None, False),
        "q34r": ((-d * 0.6, -d * 0.5, d * 0.55), None, False),
        "game": ((0, -d * 0.55, d * 0.85), None, False),
        "under": ((d * 0.3, -d * 0.4, -d * 0.7), None, False),
        "close": ((d * 0.25, d * 0.25, d * 0.22), None, False),
    }
    for name, (loc, ortho, is_ortho) in views.items():
        look = (0, 0, 0) if name != "close" else (-POD_X * PX, 0.05, 0.05)
        c = cam(name, loc, look, ortho=ortho if is_ortho else None, lens=50 if name != "close" else 55)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        if name == "close":
            c.location = (-POD_X * PX + 0.35, -1.25, 1.95)
            c.rotation_euler = (Vector(look) - c.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = c
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    (out / "pal_grid.json").write_text(json.dumps(pal_grid(obj)))


def pod_shells(obj, coll):
    """One outline shell per missile (D51). common.outline_shell keeps only the largest connected
    island of its voxel remesh, so one shell over both missiles would outline only one of them:
    make each from a copy of the model cut to one missile."""
    import bmesh
    shells = []
    for sgn, tag in ((-1, "L"), (1, "R")):
        me = obj.data.copy()
        tmp = bpy.data.objects.new(f"{NAME}_{tag}", me)
        coll.objects.link(tmp)
        bm = bmesh.new()
        bm.from_mesh(me)
        dead = [f for f in bm.faces if f.calc_center_median().x * sgn < 0]
        bmesh.ops.delete(bm, geom=dead, context="FACES")
        bm.to_mesh(me)
        bm.free()
        sh = common.outline_shell(tmp, coll, voxel=0.012, faces=900, smooth=12)
        sh.name = f"{NAME}_outline_{tag}"
        bpy.data.objects.remove(tmp, do_unlink=True)
        shells.append(sh)
    return shells


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(REPO, NAME)
    coll = common.reset_collection(NAME)
    objs, mats = build(coll, sprite)
    obj = T.join(objs, NAME)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    import collections
    cnt = collections.Counter()
    for p in obj.data.polygons:
        cnt[obj.data.materials[p.material_index].name] += len(p.vertices) - 2
    print("tris by material", dict(cnt))
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = REPO / "assets" / "blender" / "textures" / NAME / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(obj, bake_dir, size=512, samples=64)
        fmt = "WEBP"
    shells = pod_shells(obj, coll)
    common.export_sprite_model(REPO, [obj] + shells, MODEL, sprite["sprites"], image_format=fmt)
    print(f"{NAME}: outline shells {[len(s.data.polygons) for s in shells]} faces")
    if "--views" in argv:
        render_views(obj, shells, argv[argv.index("--views") + 1])


if __name__ == "__main__":
    main()
