"""Spiked ice mine (newsha.shp frames 167, 205, 243): a cryo contact mine.

The sprite is newsha-169's spiked mine drawn in the cyan ramp (identical masks, every index +208),
so the build follows newsha-169's approved layout (D116) and differs in material and cut: a
faceted ice-crystal shell instead of forged steel.

Reading of the sprite (24x28, no ink border: the model goes to the sprite's outer edge, D74):
- Body (columns 4-18, rows 6-20): a ball, lit from the upper left (the bright cluster at (7, 9) is
  sheen, the dark lower rows 17-18 its shadow side). Built as eight cut-crystal gores (each gore
  two facet columns either side of a raised ridge, facet rows every ~12 degrees of latitude, flat
  shaded so the facets catch the light as the sprite's patchy face does), held in a steel cage:
  recessed meridian seams, a proud equatorial clamp band, a cap ring round a hexagonal crystal
  boss on top. Plan: a slightly squared circle (the sprite's body fills its corners).
- Long spikes: four cardinal and four diagonal ice spikes, each a steel hex collar nut on the
  shell, a ferrule ring, a six-sided crystal prism and a six-faceted point. The frames turn the
  mine: every spike has the same 3D length from the centre; its plan tip comes from the sprite and
  the rest of its length rises out of the plane.
- Short spikes (the isolated bright pixels on the ball): seven low crystal studs normal to the
  shell, each a hex collar and a six-faceted crystal point (the glint is sheen on the point).
- Underside: the lower gores close on a flat foot ring at the ground; no detail.

Colours (median palette index per region, darkest <= 211 and brightest >= 221 left out):
shell upper 216, lower 215, spikes 216, collars and band 214, seams 212, studs 217, stud points 219.

    Blender --background --factory-startup --python newsha-167.py -- [--views DIR] [--no-bake]

Exports public/models/enemies/newsha-167.glb (frame 167), -f2 (205), -f3 (243) and their
src/render/spriteModels entries, each with an outline shell (D51).
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "newsha-167"
FRAMES = (167, 205, 243)
PX = 1 / 12

# Material slots and palette indices.
SHELL_UP, SHELL_LO, BAND, SEAM, SPIKE, NUT, HORN, CAP = range(8)
PAL_OF = {SHELL_UP: 216, SHELL_LO: 215, BAND: 214, SEAM: 212, SPIKE: 216, NUT: 214, HORN: 217, CAP: 219}

# Body, in sprite px (x = column edge, y = row edge, z up from the ground).
CX, CY = 11.5, 13.5      # plan centre
A = 7.7                  # plan half width (outer edge of the sprite's body)
P_EXP = 3.0              # plan squircle exponent (2 = circle)
RZ = 6.6                 # vertical semi axis
ZC = 6.0                 # centre height: the shell meets the ground in a flat foot
BAND_PROUD = 0.26
RIDGE = 0.42             # how far each gore's crystal ridge stands proud (px)
L_SPIKE = 13.4           # every long spike's 3D length from the centre

# Long-spike plan tips (pixel-edge coordinates of the farthest point) per frame.
CARD = {
    167: [(11.5, 1.0), (11.5, 24.0), (0.0, 13.5), (22.0, 13.5)],
    205: [(11.5, 2.0), (11.5, 26.0), (0.0, 13.5), (23.0, 13.5)],
    243: [(11.5, 3.0), (11.5, 27.0), (1.0, 13.5), (24.0, 13.5)],
}
DIAG = {
    167: [(2.0, 4.0), (19.0, 6.0), (22.3, 24.0), (3.9, 21.1)],
    205: [(3.0, 5.0), (20.0, 5.0), (21.3, 23.0), (3.0, 22.0)],
    243: [(3.9, 5.9), (21.0, 4.0), (20.0, 22.0), (2.0, 23.0)],
}
# Short crystal studs: plan positions (pixel-edge coordinates) of the isolated bright pixels.
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
CAP_PH = math.radians(70)    # cap ring latitude
BAND_PH = math.radians(6.0)  # band half height (latitude)


def body(M):
    # Plan angle columns: each seam 4 columns (edge, floor, floor, edge), then a gore of 3 interior
    # columns: facet, ridge, facet (the ridge raised so each gore is a cut crystal plate).
    cols = []
    for k in range(8):
        g0 = GROOVES[k]
        g1 = GROOVES[(k + 1) % 8] + (2 * math.pi if k == 7 else 0)
        cols += [(g0 - GW, 0, 0.0), (g0 - GW * 0.45, 1, 0.0), (g0 + GW * 0.45, 1, 0.0), (g0 + GW, 0, 0.0)]
        a, b = g0 + GW, g1 - GW
        for i, lift in ((1, 0.55), (2, 1.0), (3, 0.55)):
            cols.append((a + (b - a) * i / 4, 0, lift))
    cols = cols[1:] + cols[:1]
    ph_min = -math.asin(ZC / RZ)
    c = math.radians(2.2)
    # Latitude rows: (phi, grow, kind, facet lift). Alternate rows lift so the facets break into
    # diamonds rather than plain bands.
    rows = [(ph_min, -0.15, "foot", 0.0), (ph_min + math.radians(4), 0.0, "lo", 0.0)]
    for ph, lf in ((-52, 0.5), (-36, 0.0), (-21, 0.6)):
        rows.append((math.radians(ph), 0.0, "lo", lf))
    rows += [(-BAND_PH - c, 0.0, "lo", 0.0), (-BAND_PH - c, -0.25, "bandwall", 0.0),
             (-BAND_PH, BAND_PROUD - 0.12, "band", 0.0), (-BAND_PH + c, BAND_PROUD, "band", 0.0),
             (BAND_PH - c, BAND_PROUD, "band", 0.0), (BAND_PH, BAND_PROUD - 0.12, "band", 0.0),
             (BAND_PH + c, -0.25, "bandwall", 0.0), (BAND_PH + c, 0.0, "up", 0.0)]
    for ph, lf in ((20, 0.8), (33, 0.15), (46, 0.85), (58, 0.2)):
        rows.append((math.radians(ph), 0.0, "up", lf))
    rows += [(CAP_PH - math.radians(4.0), 0.0, "up", 0.0),
             (CAP_PH - math.radians(1.8), -SEAM_D, "capseam", 0.0),
             (CAP_PH + math.radians(1.6), -SEAM_D, "capseam", 0.0),
             (CAP_PH + math.radians(3.6), 0.18, "cap", 0.0), (math.radians(78), 0.2, "cap", 0.0)]
    grid = []
    for ph, grow, kind, lf in rows:
        ring = []
        for th, floor, lift in cols:
            g = grow
            if floor and kind in ("lo", "up"):
                g -= SEAM_D
            if kind in ("lo", "up") and not floor:
                g += RIDGE * lift * (0.35 + 0.65 * lf)
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
            elif k0 == "capseam" and k1 == "capseam":
                mat = SEAM
            elif "capseam" in (k0, k1) and "cap" in (k0, k1):
                mat = BAND
            elif "capseam" in (k0, k1):
                mat = SEAM
            elif k0 == "cap" and k1 == "cap":
                mat = BAND
            elif k0 in ("up", "cap") and k1 in ("up", "cap"):
                mat = SEAM if (floor and k0 == "up" and k1 == "up") else SHELL_UP
            else:
                mat = SEAM if (floor and k0 == "lo" and k1 == "lo") else SHELL_LO
            M.f((r0[a], r0[b], r1[b], r1[a]), mat)
    # Close the cap ring with a flat steel collar and set a hexagonal crystal boss in it.
    top_ring = grid[-1][0]
    zc = sum(W(shell_point(th, math.radians(78), 0.2)).z for th, _, _ in cols) / n / PX
    ctr = M.v((CX, CY, zc))
    for a in range(n):
        M.f((top_ring[a], top_ring[(a + 1) % n], ctr), SHELL_UP)
    boss = [(-0.3, 2.3), (0.55, 2.3), (0.95, 1.7), (1.25, 0.9)]
    lathe(M, (CX, CY, zc), (0, 0, 1), boss, 6, [SPIKE, SPIKE, SPIKE], phase=0.5, tip=(1.45, HORN))
    M.f(list(reversed(grid[0][0])), SHELL_LO)  # flat foot on the ground


def long_spike(M, tip_xy, thin=False):
    """A long ice spike whose plan tip is tip_xy, L_SPIKE long from the centre, rising out of the
    plane by whatever length the plan does not show."""
    dx, dy = tip_xy[0] - CX, tip_xy[1] - CY
    l = math.hypot(dx, dy)
    L = max(L_SPIKE, l)
    dz = math.sqrt(max(0.0, L * L - l * l))
    d = Vector((dx, dy, dz)) / L
    ts = surface_t(d)
    o = (CX, CY, ZC)
    k = 0.7 if thin else 1.0
    rn, rs = 2.2 * k, 1.75 * k     # collar nut, crystal shaft radius
    nut = [(ts - 1.2, rn), (ts + 0.8, rn), (ts + 1.25, rn - 0.55 * k)]
    lathe(M, o, d, nut, 6, [NUT, NUT], phase=0.5)
    # Ferrule ring, then the six-sided crystal prism tapering a little, then a faceted point.
    t0 = ts + 1.25
    ferrule = [(t0 - 0.1, rs * 1.15), (t0 + 0.55, rs * 1.15), (t0 + 0.7, rs * 1.0)]
    lathe(M, o, d, ferrule, 12, [BAND, BAND])
    shaft = [(t0 + 0.7, rs * 1.0), (L - 1.9, rs * 0.9), (L - 1.25, rs * 0.62)]
    lathe(M, o, d, shaft, 6, [SPIKE, SPIKE], tip=(L, SPIKE))


def stud(M, xy):
    x, y = xy
    s = (sq_norm(x - CX, -(y - CY)) / A) ** 2
    z = ZC + RZ * math.sqrt(max(0.0, 1 - s))
    p = Vector((x, y, z))
    n = shell_normal(p)
    collar = [(-0.6, 0.95), (0.25, 0.95), (0.4, 0.78)]
    lathe(M, p, n, collar, 6, [NUT, NUT], phase=0.5)
    point = [(0.45, 0.72), (1.2, 0.62)]
    lathe(M, p, n, point, 6, [HORN], tip=(2.35, CAP), cap0=False)


def band_bolts(M):
    """Hex bolt heads on the clamp band, a pair flanking each diagonal spike."""
    for th in [math.radians(45 + 90 * k + s * 19) for k in range(4) for s in (-1, 1)]:
        p = Vector(shell_point(th, BAND_PH * 0.5, BAND_PROUD - 0.2))
        n = shell_normal(Vector(shell_point(th, 0.0)))
        n = (Vector((n.x, n.y, 0)).normalized() + Vector((0, 0, 0.9))).normalized()
        lathe(M, p, n, [(-0.1, 0.55), (0.25, 0.55), (0.36, 0.4)], 6, [NUT, NUT], phase=0.5)


def materials(sprite, tag):
    def pal(slot, sub, metallic, roughness):
        return common.palette_material(sprite, PAL_OF[slot], f"{tag}_{sub}", metallic=metallic, roughness=roughness)
    return [
        pal(SHELL_UP, "ice", 0.15, 0.22),
        pal(SHELL_LO, "ice_lo", 0.12, 0.3),
        pal(BAND, "band", 0.5, 0.38),
        pal(SEAM, "seam", 0.2, 0.75),
        pal(SPIKE, "spike", 0.15, 0.2),
        pal(NUT, "nut", 0.5, 0.4),
        pal(HORN, "stud", 0.15, 0.2),
        pal(CAP, "point", 0.2, 0.18),
    ]


def build_frame(sprite, frame, coll):
    i = FRAMES.index(frame)
    tag = NAME if i == 0 else f"{NAME}-f{i + 1}"
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
    # Crystal and nuts flat (facets), only the round ferrules smooth.
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(8))
    return tag, obj


def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = (0.97, 0.99, 1.0), tuple(range(8))
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
    bpy.context.view_layer.update()
    for frame, tag, obj, tris in built:
        fmt = "AUTO"
        if "--no-bake" not in argv:
            bd = Path(tempfile.mkdtemp(prefix=f"bake_{tag}_"))
            bake(obj, bd)
            fmt = "WEBP"
        sh = common.outline_shell(obj, coll, voxel=0.012, faces=1500, smooth=8)
        shells[frame] = sh
        subset = [dict(sp, frames=[frame]) for sp in sprite["sprites"] if frame in sp["frames"]]
        common.export_sprite_model(WT, [obj, sh], f"enemies/{tag}", subset, image_format=fmt)
    if views:
        for frame, tag, obj, tris in built:
            shells[frame].hide_render = True
            which = ("top", "side", "front", "rear", "q34", "game", "under") if frame == 167 else ("q34", "game")
            lit_views(obj, views, str(frame), which)
        (views / "stats.json").write_text(json.dumps(stats))


if __name__ == "__main__":
    main()
