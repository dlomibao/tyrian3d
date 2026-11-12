"""Spiked mine (newsha.shp frames 169, 207, 245), a hard-surface contact mine.

Reading of the sprite (24x28, no ink border: the model goes to the sprite's outer edge, D74):
- Body (columns 4-18, rows 6-20): a steel sphere, lit from the upper left (the bright cluster at
  (7, 9) is sheen, the dark lower rows 17-18 are its shadow side). Built as two forged half shells
  (upper pal 8, lower pal 7) joined by a proud equatorial clamp band, split into eight gores by
  machined meridian seams, a cap ring round the top. The plan is a slightly squared circle (the
  sprite's body fills its corners, where the diagonal horns' collars sit).
- Long spikes: four cardinal and four diagonal horns, each a hex collar nut on the shell, a round
  shaft and a pointed tip. The three frames turn the mine, so the horns stand at different angles:
  every horn is the same 3D length from the centre; its plan tip comes from the sprite and the
  rest of the length rises out of the plane (a short plan spike is a horn tilted up toward the
  camera). Frames without a visible diagonal spike get that horn steeply raised, its collar in the
  body's corner.
- Short horns (the isolated bright pixels on the ball): seven low contact horns normal to the
  shell, each a collar, a short shaft and a polished cap (the glint is sheen on the cap).
- Underside: the lower shell closes on a flat foot ring at the ground; no detail.

Colours (median palette index per region, darkest shading <= 3 and highlights >= 13 left out):
shell upper 8, lower 7, spikes 8, collars and band 6, seams 4, short horns 9, caps 11.

    Blender --background --factory-startup --python newsha-169_A.py -- [--views DIR] [--no-bake]

Exports enemies/newsha-169 (frame 169), -f2 (207), -f3 (245), each with an outline shell (D51),
plus their src/render/spriteModels entries.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/Users/dlomibao/projects/tyrian-scratch/e1-enemies/newsha-169/final")
NAME = "newsha-169"
FRAMES = (169, 207, 245)
PX = 1 / 12

# Material slots and palette indices.
SHELL_UP, SHELL_LO, BAND, SEAM, SPIKE, NUT, HORN, CAP = range(8)
PAL_OF = {SHELL_UP: 8, SHELL_LO: 7, BAND: 6, SEAM: 4, SPIKE: 8, NUT: 6, HORN: 9, CAP: 11}

# Body, in sprite px (x = column edge, y = row edge, z up from the ground).
CX, CY = 11.5, 13.5      # plan centre
A = 7.7                  # plan half width (outer edge of the sprite's body)
P_EXP = 3.0              # plan squircle exponent (2 = circle)
RZ = 6.6                 # vertical semi axis
ZC = 6.0                 # centre height: the shell meets the ground in a flat foot
BAND_PROUD = 0.26
L_SPIKE = 13.4           # every long horn's 3D length from the centre

# Long-spike plan tips (pixel-edge coordinates of the farthest point) per frame.
CARD = {
    169: [(11.5, 1.0), (11.5, 24.0), (0.0, 13.5), (22.0, 13.5)],
    207: [(11.5, 2.0), (11.5, 26.0), (0.0, 13.5), (23.0, 13.5)],
    245: [(11.5, 3.0), (11.5, 27.0), (1.0, 13.5), (24.0, 13.5)],
}
DIAG = {
    169: [(2.0, 4.0), (19.0, 6.0), (22.3, 24.0), (3.9, 21.1)],
    207: [(3.0, 5.0), (20.0, 5.0), (21.3, 23.0), (3.0, 22.0)],
    245: [(3.9, 5.9), (21.0, 4.0), (20.0, 22.0), (2.0, 23.0)],
}
# Short contact horns: plan positions (pixel-edge coordinates) of the isolated bright pixels.
STUDS = [(7.3, 9.0), (14.5, 7.5), (11.5, 13.0), (6.5, 13.5), (16.5, 12.3), (15.8, 16.8), (7.5, 17.5)]


def W(p):
    """sprite px (x, y, z) -> Blender units."""
    return Vector(((p[0] - 12) * PX, (14 - p[1]) * PX, p[2] * PX))


def sq_norm(x, y):
    return (abs(x) ** P_EXP + abs(y) ** P_EXP) ** (1 / P_EXP)


def shell_point(th, ph, grow=0.0):
    """Point on the body at plan angle th (0 = +x, 90 = up the screen = -y) and latitude ph."""
    c, s = math.cos(th), math.sin(th)
    n = sq_norm(c, s)
    ux, uy = c / n, s / n
    k = 1 + grow / A
    x = CX + A * k * ux * math.cos(ph)
    y = CY - A * k * uy * math.cos(ph)
    z = ZC + RZ * (1 + grow / RZ) * math.sin(ph)
    return (x, y, max(z, 0.0))


def implicit(p):
    x, y, z = p[0] - CX, -(p[1] - CY), p[2] - ZC
    return (sq_norm(x, y) / A) ** 2 + (z / RZ) ** 2


def surface_t(d):
    """Distance from the centre along unit direction d (px space) to the shell."""
    lo, hi = 0.0, 20.0
    for _ in range(40):
        m = (lo + hi) / 2
        p = (CX + d[0] * m, CY + d[1] * m, ZC + d[2] * m)
        if implicit(p) < 1:
            lo = m
        else:
            hi = m
    return lo


def shell_normal(p):
    e = 1e-3
    g = [(implicit((p[0] + (e if i == 0 else 0), p[1] + (e if i == 1 else 0), p[2] + (e if i == 2 else 0)))
          - implicit(p)) / e for i in range(3)]
    return Vector(g).normalized()


# --- mesh helpers --------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(W(p))

    def f(self, vs, mat):
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        return face


def lathe(M, origin, d, profile, sides, mats, phase=0.0, tip=None, cap0=True):
    """Solid of revolution along unit d from origin: profile [(t, r)], mats[i] between ring i and
    i + 1 (and the tip cone). tip = (t, mat) closes the end in a point."""
    d = Vector(d).normalized()
    a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(a).normalized()
    v = d.cross(u).normalized()
    o = Vector(origin)
    rings = []
    for t, r in profile:
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * (k + phase) / sides
            p = o + d * t + (u * math.cos(ang) + v * math.sin(ang)) * r
            ring.append(M.v(tuple(p)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(sides):
            j = (k + 1) % sides
            M.f((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]), mats[i])
    if cap0:
        M.f(list(reversed(rings[0])), mats[0])
    if tip:
        pt = M.v(tuple(o + d * tip[0]))
        for k in range(sides):
            j = (k + 1) % sides
            M.f((rings[-1][k], rings[-1][j], pt), tip[1])
    else:
        M.f(rings[-1], mats[-1])


# --- the body ------------------------------------------------------------------------------------

GROOVES = [math.radians(22.5 + 45 * k) for k in range(8)]
GW = math.radians(4.2)       # seam half width (angle)
SEAM_D = 0.28                # seam depth (px)
CAP_PH = math.radians(71)    # cap ring latitude
BAND_PH = math.radians(6.0)  # band half height (latitude)


def body(M):
    # Plan angle columns: gores of 4 steps, each seam 4 columns (edge, floor, floor, edge).
    cols = []
    for k in range(8):
        g0 = GROOVES[k]
        g1 = GROOVES[(k + 1) % 8] + (2 * math.pi if k == 7 else 0)
        cols += [(g0 - GW, 0), (g0 - GW * 0.45, 1), (g0 + GW * 0.45, 1), (g0 + GW, 0)]
        a, b = g0 + GW, g1 - GW
        for i in range(1, 4):
            cols.append((a + (b - a) * i / 4, 0))
    cols = cols[1:] + cols[:1]  # start on a gore edge; any order round the loop works
    ph_min = -math.asin(ZC / RZ)
    c = math.radians(2.2)
    # Latitude rows: (phi, grow, kind). kind: lo / band / seamring / up / cap.
    rows = [(ph_min, -0.15, "foot"), (ph_min + math.radians(4), 0.0, "lo")]
    for ph in (-55, -42, -30, -19):
        rows.append((math.radians(ph), 0.0, "lo"))
    rows += [(-BAND_PH - c, 0.0, "lo"), (-BAND_PH - c, -0.25, "bandwall"),
             (-BAND_PH, BAND_PROUD - 0.12, "band"), (-BAND_PH + c, BAND_PROUD, "band"),
             (BAND_PH - c, BAND_PROUD, "band"), (BAND_PH, BAND_PROUD - 0.12, "band"),
             (BAND_PH + c, -0.25, "bandwall"), (BAND_PH + c, 0.0, "up")]
    for ph in (17, 28, 39, 50, 60):
        rows.append((math.radians(ph), 0.0, "up"))
    rows += [(CAP_PH - math.radians(3.5), 0.0, "up"), (CAP_PH - math.radians(1.6), -SEAM_D, "capseam"),
             (CAP_PH + math.radians(1.6), -SEAM_D, "capseam"), (CAP_PH + math.radians(3.5), 0.12, "cap"),
             (math.radians(79), 0.12, "cap"), (math.radians(85), 0.12, "cap")]
    grid = []
    for ph, grow, kind in rows:
        ring = []
        for th, floor in cols:
            g = grow
            if floor and kind in ("lo", "up"):
                g -= SEAM_D
            ring.append(M.v(shell_point(th, ph, g)))
        grid.append((ring, kind))
    n = len(cols)
    for i in range(len(grid) - 1):
        (r0, k0), (r1, k1) = grid[i], grid[i + 1]
        for a in range(n):
            b = (a + 1) % n
            floor = cols[a][1] and cols[b][1]
            if "band" in (k0, k1) or "bandwall" in (k0, k1):
                mat = BAND if (k0 == "band" or k1 == "band") else SEAM
                if k0 == "bandwall" and k1 == "bandwall":
                    mat = SEAM
            elif "capseam" in (k0, k1) and k0 != k1 and not (k0 == "cap" or k1 == "cap"):
                mat = SEAM
            elif k0 == "capseam" and k1 == "capseam":
                mat = SEAM
            elif k0 == "capseam" or k1 == "capseam":
                mat = SHELL_UP
            elif k0 in ("up", "cap") and k1 in ("up", "cap"):
                mat = SEAM if (floor and k0 == "up" and k1 == "up") else SHELL_UP
            else:
                mat = SEAM if (floor and k0 == "lo" and k1 == "lo") else SHELL_LO
            M.f((r0[a], r0[b], r1[b], r1[a]), mat)
    top = M.v(shell_point(0, math.pi / 2, 0.12))
    for a in range(n):
        M.f((grid[-1][0][a], grid[-1][0][(a + 1) % n], top), SHELL_UP)
    M.f(list(reversed(grid[0][0])), SHELL_LO)  # flat foot on the ground


def long_spike(M, tip_xy, thin=False):
    """A long horn whose plan tip is tip_xy, L_SPIKE long from the centre, rising out of the
    plane by whatever length the plan does not show."""
    dx, dy = tip_xy[0] - CX, tip_xy[1] - CY
    l = math.hypot(dx, dy)
    L = max(L_SPIKE, l)
    dz = math.sqrt(max(0.0, L * L - l * l))
    d = Vector((dx, dy, dz)) / L
    ts = surface_t(d)
    o = (CX, CY, ZC)
    k = 0.7 if thin else 1.0
    rn, rs = 2.6 * k, 1.68 * k     # collar nut, shaft radius
    nut = [(ts - 1.2, rn), (ts + 0.85, rn), (ts + 1.3, rn - 0.5 * k)]
    lathe(M, o, d, nut, 6, [NUT, NUT], phase=0.5)
    # Shaft: a machined step ring above the nut, a straight pin, then a short hard point.
    t0 = ts + 1.35
    shaft = [(t0, rs * 1.12), (t0 + 0.6, rs * 1.12), (t0 + 0.75, rs * 0.95), (L - 2.5, rs * 0.92),
             (L - 1.1, rs * 0.52)]
    lathe(M, o, d, shaft, 10, [SPIKE, SEAM, SPIKE, SPIKE], tip=(L, SPIKE))


def stud(M, xy):
    # Point on the shell above the plan position, its normal.
    x, y = xy
    s = (sq_norm(x - CX, -(y - CY)) / A) ** 2
    z = ZC + RZ * math.sqrt(max(0.0, 1 - s))
    p = Vector((x, y, z))
    n = shell_normal(p)
    prof = [(-0.6, 1.05), (0.35, 1.05), (0.55, 0.78), (1.5, 0.62), (1.75, 0.55)]
    lathe(M, p, n, prof, 8, [NUT, NUT, HORN, HORN], tip=None)
    cap = [(1.75, 0.55), (2.05, 0.42), (2.22, 0.2)]
    lathe(M, p, n, cap, 8, [CAP, CAP], tip=(2.3, CAP), cap0=False)


def band_bolts(M):
    """Hex bolt heads on the clamp band's top edge, a pair flanking each diagonal horn (the
    band's halves are drawn together at the corners, where the sprite's body fills out)."""
    for th in [math.radians(45 + 90 * k + s * 19) for k in range(4) for s in (-1, 1)]:
        p = Vector(shell_point(th, BAND_PH * 0.5, BAND_PROUD - 0.2))
        n = shell_normal(Vector(shell_point(th, 0.0)))
        n = (Vector((n.x, n.y, 0)).normalized() + Vector((0, 0, 0.9))).normalized()
        lathe(M, p, n, [(-0.1, 0.55), (0.25, 0.55), (0.36, 0.4)], 6, [NUT, NUT], phase=0.5)


BALL_M, COAT_M, COAT_SHELL, COAT_HORN = 0.12, 0.3, 1.0, 1.0  # metallic: ball, horns; coat: ball, horns
# The ball's specular response (demo review, MINES, second round: with the coat alone the shell still
# read about 8% darker than the sprite, its glints all on the horns). The game's lights (view.ts sun,
# RoomEnvironment panels) all reflect off the crown under the overhead and tilted cameras; a plain
# dielectric's 4% F0 leaves them dim, so the shell's F0 goes up to about 0.17 (that of IOR 2.4) with
# Specular IOR Level (the exporter writes it as KHR_materials_specular specularColorFactor 2 x level;
# a bare IOR is dropped unless specular, transmission or volume is exported) and its coat is a
# little rougher, so the sun's lobe on the crown reads as one broad white sheen. Measured frozen at demo 4 curLoc 1325 / 3137 (sprite 114.5 / 114.8 mean,
# 5.3 / 5.2% above 200): F0 of IOR 2.2 gave 112.1 / 116.9, 4.3 / 4.5%; of IOR 2.5 114.2 / 119.6,
# 5.5 / 6.0%. Metallic stays low (raising it darkened the mines).
BALL_SPEC, BALL_COAT_R = 0.5 * ((1.4 / 3.4) ** 2 / 0.04), 0.25  # Specular IOR Level: F0 of IOR 2.4


def materials(sprite, tag):
    # Polished steel with a clear coat (demo review, MINES: the satin version read matte mid-grey
    # beside the sprite's bright silver with white glints on the ball and the horn tips). Metallic
    # stays low so the diffuse keeps the palette grey's brightness; the white glints come from the
    # low roughness and the coat (KHR_materials_clearcoat), strongest on the horns and their caps.
    def pal(slot, sub, metallic, roughness, coat=0.0, coat_rough=0.1, spec=None):
        m = common.palette_material(sprite, PAL_OF[slot], f"{tag}_{sub}", metallic=metallic, roughness=roughness)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = coat_rough
        if spec is not None:
            bsdf.inputs["Specular IOR Level"].default_value = spec
        return m
    return [
        pal(SHELL_UP, "shell", BALL_M, 0.24, COAT_SHELL, BALL_COAT_R, BALL_SPEC),
        pal(SHELL_LO, "shell_lo", BALL_M, 0.3, COAT_SHELL, BALL_COAT_R, BALL_SPEC),
        pal(BAND, "band", BALL_M, 0.24, COAT_SHELL, BALL_COAT_R, BALL_SPEC),
        pal(SEAM, "seam", 0.1, 0.8),
        pal(SPIKE, "spike", COAT_M, 0.2, COAT_HORN, 0.1),
        pal(NUT, "nut", COAT_M, 0.3, COAT_SHELL, 0.2),
        pal(HORN, "horn", COAT_M, 0.18, COAT_HORN, 0.08),
        pal(CAP, "cap", COAT_M, 0.15, COAT_HORN, 0.06),
    ]


def build_frame(sprite, frame, coll):
    tag = NAME if frame == 169 else f"{NAME}-f{FRAMES.index(frame) + 1}"
    M = Mesh()
    body(M)
    for t in CARD[frame]:
        long_spike(M, t)
    for t in DIAG[frame]:
        long_spike(M, t, thin=True)
    for s in STUDS:
        stud(M, s)
    band_bolts(M)
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(tag)
    bm.to_mesh(me)
    bm.free()
    for m in materials(sprite, tag):
        me.materials.append(m)
    obj = bpy.data.objects.new(tag, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    return tag, obj


def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = (0.97, 0.98, 1.0), tuple(range(8))
    try:
        T.bake_maps(obj, out_dir, size=512, samples=48)
    finally:
        T.TINT, T.TEXTURED = tint, textured


# --- views and measurements (scratch only) -------------------------------------------------------

def pal_grid(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(deps)
    rows = []
    for r in range(28):
        row = []
        for c in range(24):
            X, Y = (c + 0.5 - 12) * PX, (14 - (r + 0.5)) * PX
            hit, loc, nrm, fi = ev.ray_cast(Vector((X, Y, 5.0)), Vector((0, 0, -1)))
            if not hit:
                row.append(-1)
                continue
            m = obj.data.materials[obj.data.polygons[fi].material_index]
            row.append(int(m.name.split("_")[1]))
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


def top_mask(obj, path):
    scene = bpy.context.scene
    for o in scene.objects:
        o.hide_render = o is not obj
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
    c = cam(scene, "top_mask", (0, 0, 10), (0, 0, 0), ortho=28 / 12)
    c.rotation_euler = (0, 0, 0)
    scene.camera = c
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def lit_views(obj, out, prefix, which):
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o is not obj
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.16, 0.2, 0.16, 1)
    bg.inputs[1].default_value = 0.7
    if "sun" not in bpy.data.objects:
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 3.2
        scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(40), math.radians(-30), math.radians(20))
        fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
        fill.data.energy = 0.8
        scene.collection.objects.link(fill)
        fill.rotation_euler = (math.radians(-60), math.radians(40), 0)
        # ground plane for the game-like views
        bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.001))
        g = bpy.context.active_object
        g.name = "ground"
        gm = bpy.data.materials.new("ground")
        gm.use_nodes = True
        next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.09, 0.11, 0.08, 1)
        g.data.materials.append(gm)
    V = 400
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 4.0
    zc = ZC * PX
    views = {
        "top": ((0, 0, d), 2.8, (0, 0, 0)),
        "side": ((d, 0, zc), 2.8, (0, 0, zc)),
        "front": ((0, -d, zc), 2.8, (0, 0, zc)),
        "rear": ((0, d, zc), 2.8, (0, 0, zc)),
        "q34": ((d * 0.6, -d * 0.6, d * 0.65), None, (0, 0, zc)),
        "game": ((0, -d * 0.5, d * 0.9), None, (0, 0, zc)),
        "under": ((d * 0.4, -d * 0.5, -d * 0.55), None, (0, 0, zc)),
    }
    for name, (loc, ortho, look) in views.items():
        if name not in which:
            continue
        bpy.data.objects["ground"].hide_render = name in ("under", "side", "front", "rear")
        c = cam(scene, f"{prefix}_{name}", loc, look, ortho=ortho, lens=55)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out / f"{prefix}_{name}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    built = []
    for frame in FRAMES:
        tag, obj = build_frame(sprite, frame, coll)
        T.cull_hidden(obj)
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        print(f"{tag}: {tris} triangles")
        built.append((frame, tag, obj, tris))
    stats = {}
    for frame, tag, obj, tris in built:
        if views:
            views.mkdir(parents=True, exist_ok=True)
            top_mask(obj, views / f"top_{frame}.png")
            (views / f"pal_{frame}.json").write_text(json.dumps(pal_grid(obj)))
        stats[frame] = tris
    shells = {}
    for o in bpy.data.objects:
        o.hide_render = False
    sprites = sprite["sprites"]
    bpy.context.view_layer.update()
    for frame, tag, obj, tris in built:
        import tempfile
        bd = Path(tempfile.mkdtemp(prefix=f"bake_{tag}_")) if "--no-bake" not in argv else None
        fmt = "AUTO"
        if bd:
            bake(obj, bd)
            fmt = "WEBP"
        sh = common.outline_shell(obj, coll, voxel=0.012, faces=1500, smooth=8)
        shells[frame] = sh
        subset = [dict(sp, frames=[frame]) for sp in sprites if frame in sp["frames"]]
        common.export_sprite_model(WT, [obj, sh], f"enemies/{tag}", subset, image_format=fmt)
    if views:
        for frame, tag, obj, tris in built:
            shells[frame].hide_render = True
            which = ("top", "side", "front", "rear", "q34", "game", "under") if frame == 169 else ("q34", "game")
            lit_views(obj, views, str(frame), which)
    if views:
        (views / "stats.json").write_text(json.dumps(stats))


if __name__ == "__main__":
    main()
