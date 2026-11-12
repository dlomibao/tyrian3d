"""Vulcan Shot Option (sidekick item 4, tyrian.shp#8 frames 167, 186, 205).

What it is: a small mounted rotary-gun pod that flies beside the player's ship, nose up the screen
(style 0, mounted). From the sprite (12x14 block, 9x11 drawn):
- rows 2-6, columns 3-8: the grey barrel cluster (palette 9 barrels, 6 the dark shroud band across
  row 3). Its see-through gaps between the barrels move from frame to frame: 167 shows gaps at
  columns 4 and 7 (left barrel, a 2 px centre pair, right barrel), 186 one gap at column 6, 205
  one gap at column 5 (mirror of 186). A rigid cluster of evenly spaced equal barrels cannot draw
  that (any even count is symmetric from above; 5 can't make 167). Fitted (work/fit9.py): four
  tubes 1.2 px across, three gun barrels on a 2.45 px orbit at 90 degrees and an inset gas
  cylinder on a 1.7 px orbit, the cluster turned to 82 / 122 / 58 degrees on 167 / 186 / 205.
  In the game the three poses cycle every 3 ticks: the cluster indexes back and forth (+40, -64,
  +24 degrees), which at that rate reads as the barrels turning.
- row 3: a fixed shroud ring the barrels run through; on 186 and 205 row 2 is solid too: a
  muzzle collar slid forward over the barrel tips (the recoil buffer). On 167 it is back inside
  the shroud and the barrel tips stand out (the sprite's gaps on row 2).
- rows 6-7: a dark carrier disc where the barrels' breeches meet the drive.
- rows 7-12, columns 4-7: the brown receiver (palette 21-22), a vaulted top (the bright column 5
  and dark column 7 are its lighting) with a raised feed-cover hatch, rounded at the rear (rows
  11-12).
- rows 6-11, columns 2-3 and 8-9: grey side rails (palette 7, top strip 8), the inboard column the
  lit top, the outboard one a round-over; their front cheek prongs flank the carrier at row 6.

The sprite's dark outline ring and its upper-left lighting are left to the game. Two small
asymmetries follow the sprite's mask (tools/sprite_mask.py inner mask, D74): the left cheek prong
is 0.3 px longer than the right (row 6: column 2 inner, column 9 ink), and the model sits 0.12 px
left (row 12: columns 4-6 inner, 7 ink). Both are below what reads at game scale.

Underside: flat closed belly, no detail.

    tools/build-models.sh -j 2 assets/blender/sidekicks/vulcan-shot-option.py
    (or Blender --background --factory-startup --python this -- [--renders DIR])

Exports public/models/sidekicks/vulcan-shot-option.glb + src/render/spriteModels/vulcan-shot-option.json
(one model; the three barrel poses are frame-tagged parts, the receiver shows on every frame).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "vulcan-shot-option"
REF = f"sidekick-{NAME}"
PX = 1 / 12
XS = -0.12  # whole-model x shift, px (see docstring)
FRAMES = (167, 186, 205)

# --- barrel cluster (work/fit9.py) -----------------------------------------------------------------
ZC = 3.1  # cluster axis height, px
CX = 6.0  # cluster axis column edge
R_BARREL = 2.45
R_GAS = 1.7
R_TUBE = 0.6
POSE = {167: 82.0, 186: 122.0, 205: 58.0}  # gas cylinder's angle, degrees from +x toward +z
COLLAR = {167: False, 186: True, 205: True}

# --- palette per region (median of the region's pixels, darkest/brightest left out) ----------------
SLOTS = [  # (slot name, palette index, metallic, roughness)
    ("barrel", 9, 0.55, 0.32),
    ("shroud", 6, 0.5, 0.4),
    ("collar", 9, 0.55, 0.3),
    ("carrier", 5, 0.5, 0.42),
    ("rail", 7, 0.5, 0.4),
    ("rail_top", 8, 0.5, 0.36),
    ("core", 21, 0.2, 0.5),
    ("deck", 22, 0.22, 0.46),
    ("dark", 3, 0.3, 0.6),
    ("bore", 2, 0.0, 0.85),
    ("brown_dk", 19, 0.2, 0.55),
    ("bolt", 10, 0.6, 0.3),
]
M = {name: i for i, (name, *_r) in enumerate(SLOTS)}


def materials(sprite):
    return [common.palette_material(sprite, idx, f"{NAME}_{name}", metallic=met, roughness=rough)
            for name, idx, met, rough in SLOTS]


# --- geometry helpers (sprite px: x = column edge, y = row edge (aft +y), z up) ---------------------

def revolve(part, cx, cz, profile, n, mats, phase=0.0):
    """A solid of revolution about the line (cx, *, cz) along y: profile [(y, r)], r = 0 a pole;
    mats[i] is the material between profile points i and i + 1."""
    rings = []
    for y, r in profile:
        if r <= 1e-6:
            rings.append([part.v((cx, y, cz))])
        else:
            rings.append([part.v((cx + r * math.cos(phase + 2 * math.pi * k / n), y,
                                  cz + r * math.sin(phase + 2 * math.pi * k / n))) for k in range(n)])
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        mat = mats[min(i, len(mats) - 1)]
        y0, y1 = profile[i][0], profile[i + 1][0]
        ctr = (cx, (y0 + y1) / 2, cz)
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                part.f((r0[0], r1[j], r1[k]), mat, out=(0, -1, 0) if y1 >= y0 else (0, 1, 0))
            elif len(r1) == 1:
                part.f((r0[k], r0[j], r1[0]), mat, out=(0, 1, 0) if y1 >= y0 else (0, -1, 0))
            elif abs(y1 - y0) < 1e-6:
                # a flat annulus: faces +y if the ring shrinks going on (a step down toward aft)
                rr0, rr1 = profile[i][1], profile[i + 1][1]
                part.f((r0[k], r0[j], r1[j], r1[k]), mat, out=(0, 1 if rr1 < rr0 else -1, 0))
            else:
                a = r0[k].co
                part.f((r0[k], r0[j], r1[j], r1[k]), mat, out=(a.x - cx, 0, a.z - cz))


def tube_loft(part, loopf, ys, mats_of, cap0=True, cap1=True):
    """Loft closed sections loopf(y) -> [(x, z)] along ys; mats_of(k) is the material of the k-th
    edge of the loop (so the top, flanks and belly can differ)."""
    rings = []
    for y in ys:
        pts = loopf(y)
        rings.append([part.v((x, y, z)) for x, z in pts])
    n = len(rings[0])
    for r0, r1, y0 in zip(rings, rings[1:], ys):
        cxz = (sum(v.co.x for v in r0) / n, sum(v.co.z for v in r0) / n)
        for k in range(n):
            j = (k + 1) % n
            part.f((r0[k], r0[j], r1[j], r1[k]), mats_of(k), away=(cxz[0], r0[k].co.y, cxz[1]))
    if cap0:
        part.f(rings[0], mats_of(0), out=(0, -1, 0))
    if cap1:
        part.f(rings[-1], mats_of(0), out=(0, 1, 0))


def finish(part, mats, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # sprite px -> Blender: X = (x - 6 + XS) / 12, Y = (7 - y) / 12, Z = z / 12 (a reflection in y)
    m = Matrix(((PX, 0, 0, (XS - 6) * PX), (0, -PX, 0, 7 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


# --- the receiver -----------------------------------------------------------------------------------

Z0 = 0.35  # belly
CORE_Y0, CORE_Y1 = 6.95, 12.95
core_hw = T.pchip([6.95, 7.2, 11.0, 11.6, 12.3, 12.6, 12.82, 12.95], [1.7, 2.0, 2.0, 1.98, 1.84, 1.55, 1.1, 0.5])
core_top = T.pchip([6.95, 7.3, 11.0, 12.2, 12.7, 12.95], [5.0, 5.6, 5.6, 5.3, 4.5, 3.4])
core_side = T.pchip([6.95, 7.3, 11.0, 12.2, 12.7, 12.95], [4.1, 4.4, 4.4, 4.2, 3.6, 2.8])
VAULT_N = 9  # points over the vault


def core_loop(y, grow=0.0):
    hw, zt, zs = core_hw(y) + grow, core_top(y) + grow, core_side(y)
    zb = Z0 - grow
    ch = min(0.3, hw * 0.3)
    pts = [(CX + hw - ch, zb), (CX + hw, zb + ch), (CX + hw, zs)]
    for k in range(1, VAULT_N):  # superelliptic vault from the right shoulder over to the left
        t = math.pi * k / VAULT_N
        c, s = math.cos(t), math.sin(t)
        e = 0.7  # squarish vault, round shoulders
        x = CX + hw * math.copysign(abs(c) ** e, c)
        z = zs + (zt - zs) * (abs(s) ** e)
        pts.append((x, z))
    pts += [(CX - hw, zs), (CX - hw, zb + ch), (CX - hw + ch, zb)]
    return pts


def core_mat(k):
    # edges: 0 belly-right chamfer, 1 right flank, 2..VAULT_N+1 vault, then left flank, chamfer, belly
    if 2 <= k <= VAULT_N + 1:
        return M["core"]
    return M["core"]


def build_core(P):
    ys = [6.95, 7.05, 7.2, 7.5] + [7.5 + 0.5 * i for i in range(1, 8)] + [11.3, 11.6, 11.9, 12.2, 12.4, 12.6, 12.72, 12.82, 12.9, 12.95]
    tube_loft(P, core_loop, ys, core_mat)


def deck_loop(y):
    """The feed-cover hatch: the vault's top, 0.16 px proud, inside |dx| < 1.35, closed under."""
    hw, zt, zs = core_hw(y), core_top(y), core_side(y)
    e = 0.7
    pts = []
    W = 1.35
    for k in range(7):
        x = W * (1 - 2 * k / 6)
        c = x / hw
        t = math.acos(max(-1, min(1, math.copysign(abs(c) ** (1 / e), c))))
        z = zs + (zt - zs) * (abs(math.sin(t)) ** e)
        pts.append((CX + x, z + 0.16))
    # back under the surface (closed)
    for k in range(6, -1, -1):
        if k in (0, 6):
            continue
    pts += [(CX - W + 0.15, zt - 0.6), (CX + W - 0.15, zt - 0.6)]
    return pts


def build_deck(P):
    ys = [7.7, 7.85] + [7.85 + 0.5 * i for i in range(1, 7)] + [11.15, 11.3]
    rings = []
    for y in ys:
        pts = deck_loop(y)
        if y in (7.7, 11.3):  # chamfered ends: shrink toward the surface
            pts = [(CX + (x - CX) * 0.88, z - 0.12) for x, z in pts]
        rings.append([P.v((x, y, z)) for x, z in pts])
    n = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            P.f((r0[k], r0[j], r1[j], r1[k]), M["deck"], away=(CX, r0[k].co.y, 4.0))
    P.f(rings[0], M["deck"], out=(0, -1, 0))
    P.f(rings[-1], M["deck"], out=(0, 1, 0))
    # Two dark latch slots across the hatch's front and rear edge, and a hinge bar at its rear.
    for y0 in (8.15, 10.65):
        T.hull(P, T.cbox(CX - 0.9, CX + 0.9, y0, y0 + 0.22, core_top(y0) + 0.05, core_top(y0) + 0.24, 0.05), M["brown_dk"])


# Rails: x from the outboard edge rail_xo(y) to inside the receiver; z belly to rail_top(y).
rail_xo = T.pchip([7.0, 10.6, 11.1, 11.5, 11.85, 12.05], [2.0, 2.0, 2.35, 2.9, 3.5, 3.9])
rail_top = T.pchip([7.0, 10.8, 11.6, 12.05], [4.0, 4.0, 3.6, 3.0])
RAIL_N = 6


def rail_loop(y, side):
    xo = rail_xo(y)
    zt = rail_top(y)
    r = min(1.2, (zt - Z0) * 0.45)
    xi = 4.3  # buried in the receiver
    out = []
    # build for the left rail in local "inboard distance" u (0 at the outboard edge), mirror for right
    loc = [(0.0 + 0.3, Z0), (0.0, Z0 + 0.3), (0.0, zt - r)]
    for k in range(1, RAIL_N):
        t = (math.pi / 2) * k / RAIL_N
        loc.append((r - r * math.cos(t), zt - r + r * math.sin(t)))
    loc += [(r, zt), (xi - xo, zt), (xi - xo, Z0)]
    for u, z in loc:
        x = xo + u
        out.append(((x if side < 0 else 2 * CX - x), z))
    return out


def rail_mat(k):
    # loc edges: 0 chamfer, 1 flank, 2..RAIL_N+1 round-over, RAIL_N+2 top strip, then inner, belly
    if k == RAIL_N + 2:
        return M["rail_top"]
    return M["rail"]


def build_rails(P):
    ys = [7.0, 7.15] + [7.15 + 0.5 * i for i in range(1, 7)] + [10.6, 10.85, 11.1, 11.3, 11.5, 11.7, 11.85, 11.97, 12.05]
    for side in (-1, 1):
        tube_loft(P, lambda y: rail_loop(y, side), ys, rail_mat)
        # Front cheek prong flanking the carrier disc (row 6): the left one a little longer.
        y0 = 6.35 if side < 0 else 6.65
        x0, x1 = (2.0, 2.92) if side < 0 else (2 * CX - 2.92, 2 * CX - 2.0)
        T.hull(P, T.cbox(x0, x1, y0, 7.2, Z0 + 0.3, 3.7, 0.18), M["rail"])
        # Three vent slots on the outboard flank (seen from the side and the tilted camera).
        xf = 2.0 if side < 0 else 2 * CX - 2.0
        for i in range(3):
            yc = 8.2 + 0.85 * i
            if side < 0:
                T.hull(P, T.cbox(xf - 0.06, xf + 0.2, yc, yc + 0.5, 1.4, 2.6, 0.04), M["dark"])
            else:
                T.hull(P, T.cbox(xf - 0.2, xf + 0.06, yc, yc + 0.5, 1.4, 2.6, 0.04), M["dark"])
        # Two bolt heads on the rail top.
        for yb in (7.7, 10.3):
            xb = 3.1 if side < 0 else 2 * CX - 3.1
            revolve_z(P, xb, yb, 4.0, 0.28, 0.12, 8, M["bolt"])


def revolve_z(P, x, y, z, r, h, n, mat):
    """A small round boss standing on a horizontal face (axis z)."""
    pts = []
    for zz, rr in ((z - 0.1, r), (z + h, r), (z + h, 0.0)):
        if rr == 0:
            pts.append([P.v((x, y, zz + 0.04))])
        else:
            pts.append([P.v((x + rr * math.cos(2 * math.pi * k / n), y + rr * math.sin(2 * math.pi * k / n), zz)) for k in range(n)])
    r0, r1, top = pts
    for k in range(n):
        j = (k + 1) % n
        P.f((r0[k], r0[j], r1[j], r1[k]), mat, away=(x, y, z))
        P.f((r1[k], r1[j], top[0]), mat, out=(0, 0, 1))
    P.f(r0, mat, out=(0, 0, -1))


def build_front(P):
    """Fixed parts of the gun: the carrier disc at the breech, the shroud ring at row 3, a drive hub
    in the carrier's front face, and the rear-face power connector of the receiver."""
    # Carrier disc, rows 6.55-7.0, chamfered both faces.
    revolve(P, CX, ZC, [(6.7, 0.0), (6.7, 2.75), (6.8, 3.0), (6.95, 3.0), (7.05, 2.8), (7.05, 0.0)], 28,
            [M["carrier"]] * 2 + [M["carrier"], M["carrier"], M["dark"]])
    # Shroud ring, rows 3.0-4.0: a chamfered band with a darker groove round its middle.
    revolve(P, CX, ZC, [(3.0, 0.0), (3.0, 2.72), (3.12, 2.98), (3.42, 2.98), (3.47, 2.86), (3.55, 2.86),
                        (3.6, 2.98), (3.88, 2.98), (4.0, 2.72), (4.0, 0.0)], 28,
            [M["shroud"], M["shroud"], M["shroud"], M["dark"], M["dark"], M["dark"], M["shroud"], M["shroud"], M["shroud"]])
    # Hub caps in the middle of the shroud's front and rear faces (seen between the barrels).
    revolve(P, CX, ZC, [(2.86, 0.0), (2.86, 0.5), (3.0, 0.65), (3.0, 0.0)], 12, [M["bolt"], M["bolt"], M["bolt"]])


def build_cluster(P, frame):
    th0 = math.radians(POSE[frame])
    front = 2.0
    tubes = [(R_GAS, th0, "gas")] + [(R_BARREL, th0 + math.pi / 2 * k, "gun") for k in (1, 2, 3)]
    for R, a, kind in tubes:
        cx, cz = CX + R * math.cos(a), ZC + R * math.sin(a)
        if kind == "gun":
            prof = [(2.5, 0.0), (2.5, 0.28), (front, 0.28), (front, 0.46), (front + 0.1, 0.6), (6.75, 0.6), (6.75, 0.0)]
            mats = [M["bore"], M["bore"], M["barrel"], M["barrel"], M["barrel"], M["barrel"]]
        else:  # the gas cylinder: closed, a domed front plug
            prof = [(front + 0.2, 0.0), (front + 0.2, 0.32), (front + 0.32, 0.55), (front + 0.45, 0.6), (6.75, 0.6), (6.75, 0.0)]
            mats = [M["dark"], M["barrel"], M["barrel"], M["barrel"], M["barrel"]]
        revolve(P, cx, cz, prof, 12, mats, phase=a)
        # No clamp bands on the tubes: any collar wider than the tube fills the sprite's gaps.
        # A dark machined ring marks each breech where it enters the carrier (row 6.3-6.62).
        revolve(P, cx, cz, [(6.35, 0.0), (6.35, 0.6), (6.7, 0.6), (6.7, 0.0)], 12, [M["shroud"]] * 3, phase=a)
    if COLLAR[frame]:
        # Muzzle collar slid forward over the tips (rows 2.0-3.0), with a dark bore per barrel.
        revolve(P, CX, ZC, [(2.0, 0.0), (2.0, 2.78), (2.12, 2.96), (2.92, 2.96), (2.98, 2.85), (2.98, 0.0)], 28,
                [M["collar"]] * 5)
        for R, a, kind in tubes:
            if kind != "gun":
                continue
            cx, cz = CX + R * math.cos(a), ZC + R * math.sin(a)
            revolve(P, cx, cz, [(1.96, 0.0), (1.96, 0.3), (2.02, 0.3), (2.02, 0.0)], 10, [M["bore"]] * 3, phase=a)


def build_rear(P):
    # Power/feed connector on the receiver's rear face: a short dark boss inside the plan.
    revolve(P, CX, 2.6, [(12.55, 0.0), (12.55, 0.55), (12.86, 0.55), (12.9, 0.42), (12.9, 0.0)], 12,
            [M["brown_dk"]] * 4)


# --- build, export, render -------------------------------------------------------------------------

def build(sprite, coll):
    mats = materials(sprite)
    body = T.Part(f"{NAME}-body", smooth_angle=35)
    build_core(body)
    build_deck(body)
    build_rails(body)
    build_front(body)
    build_rear(body)
    body_obj = finish(body, mats, coll)
    clusters = {}
    for f in FRAMES:
        P = T.Part(f"{NAME}-barrels-{f}", smooth_angle=40)
        build_cluster(P, f)
        o = finish(P, mats, coll)
        common.frame_part(o, [f])
        clusters[f] = o
    return body_obj, clusters


def shells(body, clusters, coll):
    """One outline shell per frame (body + that frame's cluster), shown on that frame only."""
    out = []
    for f, cl in clusters.items():
        me = body.data.copy()
        tmp = bpy.data.objects.new(f"{NAME}-joined-{f}", me)
        coll.objects.link(tmp)
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.from_mesh(cl.data)
        bm.to_mesh(me)
        bm.free()
        sh = common.outline_shell(tmp, coll, voxel=0.012, faces=1500, smooth=4, inside=0.003)
        sh.name = f"{NAME}-outline-{f}"
        common.frame_part(sh, [f])
        bpy.data.objects.remove(tmp, do_unlink=True)
        bpy.context.view_layer.update()
        out.append(sh)
    return out


# Renders ------------------------------------------------------------------------------------------

def set_engine(name):
    scene = bpy.context.scene
    try:
        scene.render.engine = name
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if name.split("_")[1] in e)


def cam(location, look_at=None, ortho=None, fov=None, top=False, up=None):
    data = bpy.data.cameras.new("cam")
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.sensor_fit = "VERTICAL"
        data.angle_y = math.radians(fov or 30)
    c = bpy.data.objects.new("cam", data)
    bpy.context.scene.collection.objects.link(c)
    c.location = location
    if top:
        c.rotation_euler = (0, 0, 0)
    elif up == "bottom":
        c.rotation_euler = (math.pi, 0, 0)
    else:
        c.rotation_euler = (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    return c


def render(c, path, rx, ry):
    scene = bpy.context.scene
    scene.camera = c
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    d = c.data
    bpy.data.objects.remove(c, do_unlink=True)
    bpy.data.cameras.remove(d)


def workbench(flat):
    set_engine("BLENDER_WORKBENCH")
    scene = bpy.context.scene
    sh = scene.display.shading
    sh.light = "FLAT" if flat else "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = not flat
    sh.show_object_outline = False
    sh.show_shadows = False
    scene.view_settings.view_transform = "Standard"


def game_light():
    set_engine("BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE")
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("game")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.45, 0.55, 1.0)
    bg.inputs[1].default_value = 1.0
    sd = bpy.data.lights.new("sun", "SUN")
    sd.energy = 3.0
    sun = bpy.data.objects.new("sun", sd)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-6, -8.4, 20)).normalized().to_track_quat("Z", "Y").to_euler()
    scene.view_settings.view_transform = "Standard"
    return sun


def renders(body, clusters, shells_, out):
    out.mkdir(parents=True, exist_ok=True)
    for s in shells_:
        s.hide_render = True
    k = 32
    ext = 14 * PX
    def show(f):
        for g, o in clusters.items():
            o.hide_render = g != f
    workbench(True)
    for f in FRAMES:
        show(f)
        render(cam((0, 0, 20), ortho=ext, top=True), out / f"top_flat_{f}.png", 12 * k, 14 * k)
    sun = game_light()
    D = 4.2
    for f in FRAMES:
        show(f)
        render(cam((0, 0, 20), ortho=ext, top=True), out / f"top_game_{f}.png", 12 * k, 14 * k)
        tilt = math.radians(32)
        render(cam((0, -D * math.sin(tilt) * 1.0, D * math.cos(tilt)), (0, 0, 0.15), fov=24), out / f"game_{f}.png", 480, 480)
    show(167)
    zc = 0.25
    views = {
        "side": ((6, 0, zc), (0, 0, zc)),
        "side_r": ((-6, 0, zc), (0, 0, zc)),
        "front": ((0, 6, zc), (0, 0, zc)),
        "rear": ((0, -6, zc), (0, 0, zc)),
    }
    for nm, (loc, at) in views.items():
        render(cam(loc, at, ortho=1.45), out / f"{nm}.png", 480, 480)
    render(cam((-1.3, 1.5, 1.4), (0, 0, 0.2), fov=30), out / "q_front_left.png", 480, 480)
    render(cam((1.4, -1.5, 1.3), (0, 0, 0.2), fov=30), out / "q_rear_right.png", 480, 480)
    render(cam((1.5, 1.4, 0.9), (0, 0, 0.2), fov=30), out / "q_front_right_low.png", 480, 480)
    render(cam((0.6, 0.6, -2.2), (0, 0, 0.2), fov=30), out / "underside.png", 480, 480)
    bpy.data.objects.remove(sun, do_unlink=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(WT, REF)
    for o in list(bpy.data.objects):  # the factory scene's cube, light and camera
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    body, clusters = build(sprite, coll)
    sh = shells(body, clusters, coll)
    objs = [body, *clusters.values(), *sh]
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs}
    print("vulcan: triangles", json.dumps(tris))
    common.export_sprite_model(WT, objs, f"sidekicks/{NAME}", sprite["sprites"])
    if "--renders" in argv:
        renders(body, clusters, sh, Path(argv[argv.index("--renders") + 1]))


if __name__ == "__main__":
    main()
