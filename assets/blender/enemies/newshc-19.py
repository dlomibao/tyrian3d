"""Purple pod (newshc.shp frame 19, 12x14, one frame): a launched shell.

IDENTITY: a LAUNCHED PROJECTILE, not a post on the ground. Type 556 has no spawn events of its own;
newshu-55 (type 257) and newshu-43 (type 250) fire it every 50 ticks with mv(1,-1) cacc(-16,10), so
it arcs away from those machines and flies free. Built as a machined purple shell: a body of
revolution about the sprite's centre column edge (x = 6), round in every cross-section, so the
underside is the same closed round hull as the top (no detail there).

Reading of the sprite (inner mask, D74: the 1 px ink ring is the game's own outline):
- Rows 1-4: the tail drum, half width 5 (row 1: 3, the rounded rear shoulder). Its centre strip is
  lit (87-91), its flanks shade to 85 (left) and 82-84 (right): one round drum lit from the upper
  left, not separate wings. The bright column 4 (90/91/95) is sheen on the round drum.
- Row 5: a dark band (83) right across: a recessed groove ring between the drum and the collar.
- Row 6: a bright lip (94 92 91 91): a machined collar ring (driving band) catching the light.
- Rows 7-12: the nose, half width 4 (rows 7-8), 3 (9-10), 2 (11-12): an ogive (87-88) to a
  rounded tip at row 13. The wide drum is the rear, the narrow ogive the nose: a shell flies
  point first, and the sprite's lit stripe runs unbroken down the nose like a spun body.

Colours: median palette index per region, darkest shading and brightest highlights left out:
drum 86, groove 83, collar 91, nose 87, tip 88; hub and nozzle ring 84 (rear, unseen in the sprite).

Run (Blender, headless):
    tools/build-models.sh -j 2 assets/blender/enemies/newshc-19.py
    (or Blender -b -P this -- [--views DIR] [--no-bake])
Exports public/models/enemies/newshc-19.glb (model + outline shell, D51) and its spriteModels entry.
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

HERE = Path("/Users/dlomibao/projects/tyrian-scratch/e1-enemies-3/newshc-19/final")  # bake scratch + stats only
NAME = "newshc-19"
TAG = "newshc-19"
PX = 1 / 12
W, H = 12, 14
AXIS_C = 6.0   # the shell's axis: sprite column edge 6

DRUM, GROOVE, COLLAR, NOSE, TIP, HUB, VENT = range(7)
PAL_OF = {DRUM: 86, GROOVE: 83, COLLAR: 91, NOSE: 87, TIP: 88, HUB: 84, VENT: 83}
FINISH = {  # metallic, roughness: satin painted metal, a brighter machined collar
    DRUM: (0.35, 0.42), GROOVE: (0.25, 0.6), COLLAR: (0.55, 0.3), NOSE: (0.35, 0.4),
    TIP: (0.45, 0.34), HUB: (0.4, 0.4), VENT: (0.2, 0.65),
}
NMAT = len(PAL_OF)


def pchip_pts(pts):
    xs, ys = zip(*pts)
    return T.pchip(list(xs), list(ys))


# --- profile (y = sprite row edge, down the screen = toward the nose; r = radius in px) -----------

DOME_Y0, DOME_Y1, DOME_A, R_DRUM = 0.92, 2.55, 1.6, 5.0


def dome_r(y):
    """The rounded rear shoulder of the drum: a superellipse from the rear face to the drum wall."""
    t = min(1.0, max(0.0, (DOME_Y1 - y) / (DOME_Y1 - DOME_Y0)))
    return R_DRUM * max(0.0, 1 - t ** DOME_A) ** (1 / DOME_A)


OGIVE = pchip_pts([(7.12, 4.12), (8.0, 4.02), (9.0, 3.56), (10.0, 3.02), (11.0, 2.52),
                   (12.0, 2.02), (12.6, 1.62), (13.0, 1.08), (13.2, 0.55), (13.3, 0.0)])


def profile():
    """Rings along the axis. Two rings at one y make a flat annulus (a step)."""
    rings = [
        (0.84, 0.0), (0.84, 0.72), (0.88, 0.9), (0.92, 0.9),       # hub boss on the rear face
        (0.92, 1.25), (0.98, 1.25), (0.98, 1.85), (0.92, 1.95),       # nozzle ring: a small sunk annulus
    ]
    for y in (0.95, 1.0, 1.08, 1.2, 1.35, 1.52, 1.72, 1.95, 2.2, 2.55):
        rings.append((y, max(dome_r(y), 1.96)))
    rings += [
        (3.55, R_DRUM), (3.62, 4.88), (3.7, 4.88), (3.77, R_DRUM),    # drum joint line
        (5.0, R_DRUM), (5.16, 4.6), (5.84, 4.6), (6.0, 5.08),         # groove band (row 5)
        (6.14, 5.18), (6.42, 5.18), (6.47, 5.06), (6.53, 5.06), (6.58, 5.18),  # collar, a turned line
        (6.86, 5.18), (7.0, 5.0), (7.02, 4.6), (7.12, 4.12),          # collar front chamfer, step in
    ]
    for y in (7.5, 8.0, 8.5, 8.92):
        rings.append((y, OGIVE(y)))
    rings += [(8.95, OGIVE(8.95) - 0.1), (9.05, OGIVE(9.05) - 0.1), (9.08, OGIVE(9.08))]  # nose joint
    for y in (9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.3):
        rings.append((y, OGIVE(y)))
    rings += [(12.32, OGIVE(12.32) - 0.08), (12.4, OGIVE(12.4) - 0.08), (12.42, OGIVE(12.42))]  # fuse seam
    for y in (12.6, 12.8, 13.0, 13.12, 13.22):
        rings.append((y, OGIVE(y)))
    rings.append((13.3, 0.0))
    return rings


def region(y, r):
    if y < 0.97 and r < 1.3:
        return HUB
    if y < 1.0 and r < 1.97:
        return HUB
    if y < 5.08:
        return DRUM
    if y < 5.95:
        return GROOVE
    if y < 7.04:
        return COLLAR
    if y < 12.36:
        return NOSE
    return TIP


# Angular patches: (theta0, theta1 degrees from +x round the axis, 90 = top), (y0, y1),
# depth px (positive = sunk), material (None: the region's own).
def th(dx, r):
    return math.degrees(math.acos(max(-1.0, min(1.0, dx / r))))


PATCHES = [
    # Longitudinal panel seams on the drum's upper flanks (thin grooves; AO reads them).
    (th(3.6, R_DRUM) - 1.5, th(3.6, R_DRUM) + 1.5, 2.6, 4.98, 0.14, None),
    (th(-3.6, R_DRUM) - 1.5, th(-3.6, R_DRUM) + 1.5, 2.6, 4.98, 0.14, None),
    # Vent slots on the drum's sides (seen in side views and 3/4, edge-on from above).
    (-14.0, 14.0, 2.85, 3.4, 0.32, VENT),
    (-14.0, 14.0, 3.95, 4.7, 0.32, VENT),
    (166.0, 194.0, 2.85, 3.4, 0.32, VENT),
    (166.0, 194.0, 3.95, 4.7, 0.32, VENT),
]
WALL = 0.1


def build_body(bm):
    rings = profile()
    angs = set(round(i * 360 / 28 - 180, 4) for i in range(28))
    for t0, t1, y0, y1, d, m in PATCHES:
        r = R_DRUM
        dw = math.degrees(WALL / r)
        for a in (t0, t0 + dw, t1 - dw, t1):
            angs.add(round(((a + 180) % 360) - 180, 4))
    angs = sorted(angs)
    clean = []
    for a in angs:
        if clean and a - clean[-1] < 0.3:
            continue
        clean.append(a)
    angs = clean
    ys_extra = sorted({y for p in PATCHES for y in (p[2], p[2] + WALL, p[3] - WALL, p[3])})
    seq = list(rings)
    for y in ys_extra:
        # drum wall only (patches all lie on the straight drum)
        seq.append((y, R_DRUM))
    order = {id(p): i for i, p in enumerate(seq)}
    seq.sort(key=lambda p: (p[0], order[id(p)]))

    def ain(t0, t1, a):
        a0 = ((t0 + 180) % 360) - 180
        a1 = a0 + (t1 - t0)
        return a0 - 1e-6 <= a <= a1 + 1e-6 or a0 - 1e-6 <= a + 360 <= a1 + 1e-6

    def depth_at(y, r, a):
        if abs(r - R_DRUM) > 1e-6:
            return 0.0
        for t0, t1, y0, y1, dep, m in PATCHES:
            dw = math.degrees(WALL / R_DRUM)
            if y0 + WALL - 1e-6 <= y <= y1 - WALL + 1e-6 and ain(t0 + dw, t1 - dw, a):
                return dep
        return 0.0

    def patch_mat(y, a):
        for t0, t1, y0, y1, dep, m in PATCHES:
            if y0 - 1e-6 <= y <= y1 + 1e-6 and ain(t0, t1, a):
                return m
        return None

    verts = []
    for y, r in seq:
        row = []
        for a in angs:
            rr = max(0.0, r - depth_at(y, r, a)) if r > 0 else 0.0
            t = math.radians(a)
            row.append(bm.verts.new((rr * math.cos(t), y, rr * math.sin(t))))
        verts.append(row)
    n = len(angs)
    for i in range(len(seq) - 1):
        (y0, r0), (y1, r1) = seq[i], seq[i + 1]
        for j in range(n):
            k = (j + 1) % n
            quad = [verts[i][j], verts[i][k], verts[i + 1][k], verts[i + 1][j]]
            if len({v.co.to_tuple(6) for v in quad}) < 3:
                continue
            try:
                f = bm.faces.new(quad)
            except ValueError:
                continue
            a0, a1 = angs[j], angs[k] if k else angs[0] + 360
            m = patch_mat((y0 + y1) / 2, (a0 + a1) / 2)
            if m is None:
                m = region((y0 + y1) / 2, max(r0, r1))
            f.material_index = m
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)


def hull_into(bm, pts, mat):
    vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in vs if v.is_valid]
    for f in {f for v in live for f in v.link_faces}:
        f.material_index = mat


def build_details(bm):
    """Machined fittings on the visible faces: rivet heads round the collar's rear face line and a
    pair of lifting lugs' bolt heads on the drum crown (sheen spots in the sprite stay paint)."""
    # Rivets on the drum just behind the groove, every 30 deg over the top half.
    for deg in range(15, 180, 30):
        a = math.radians(deg)
        nx, nz = math.cos(a), math.sin(a)
        tx, tz = -nz, nx
        for ry in (4.82,):
            pts = []
            for kk in range(6):
                b = math.radians(60 * kk)
                for h, rr in ((-0.12, 0.17), (0.06, 0.15), (0.12, 0.08)):
                    u, v = rr * math.cos(b), rr * math.sin(b)
                    pts.append(((R_DRUM + h) * nx + tx * u, ry + v, (R_DRUM + h) * nz + tz * u))
            hull_into(bm, pts, HUB)


def materials(sprite):
    out = []
    for slot in range(NMAT):
        met, rough = FINISH[slot]
        out.append(common.palette_material(sprite, PAL_OF[slot], f"{TAG}_{slot}", metallic=met, roughness=rough))
    return out


def build(sprite, coll):
    bm = bmesh.new()
    build_body(bm)
    build_details(bm)
    m = Matrix(((PX, 0, 0, (AXIS_C - W / 2) * PX), (0, -PX, 0, H / 2 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(TAG)
    bm.to_mesh(me)
    bm.free()
    for mat in materials(sprite):
        me.materials.append(mat)
    obj = bpy.data.objects.new(TAG, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(36))
    return obj


def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    bpy.context.view_layer.update()
    T.TINT, T.TEXTURED = (0.97, 0.98, 1.0), tuple(range(NMAT))
    try:
        T.bake_maps(obj, out_dir, size=512, samples=48)
    finally:
        T.TINT, T.TEXTURED = tint, textured


# --- measurement and views (scratch only) ---------------------------------------------------------

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
            mat = obj.data.materials[obj.data.polygons[fi].material_index]
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
    K = 20
    scene.render.resolution_x, scene.render.resolution_y = W * K, H * K
    scene.render.resolution_percentage = 100
    c = cam(scene, "top_mask", (0, 0, 10), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    scene.camera = c
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def lit_views(obj, out, which):
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o is not obj and o.name != "ground"
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
        bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, -0.9))
        g = bpy.context.active_object
        g.name = "ground"
        gm = bpy.data.materials.new("ground")
        gm.use_nodes = True
        next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.09, 0.11, 0.08, 1)
        g.data.materials.append(gm)
    V = 400
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 2.6
    views = {
        "top": ((0, 0, d), 1.5, (0, 0, 0)),
        "side": ((d, 0, 0), 1.5, (0, 0, 0)),
        "front": ((0, -d, 0), 1.5, (0, 0, 0)),
        "rear": ((0, d, 0), 1.5, (0, 0, 0)),
        "q34": ((d * 0.6, -d * 0.6, d * 0.6), None, (0, 0, 0)),
        "q34b": ((-d * 0.6, d * 0.6, d * 0.5), None, (0, 0, 0)),
        "game": ((0, -d * 0.55, d * 0.95), None, (0, 0, 0)),
        "under": ((d * 0.4, -d * 0.5, -d * 0.6), None, (0, 0, 0)),
    }
    for name, (loc, ortho, look) in views.items():
        if name not in which:
            continue
        bpy.data.objects["ground"].hide_render = name in ("under", "side", "front", "rear")
        c = cam(scene, f"v_{name}", loc, look, ortho=ortho, lens=60)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out / f"v_{name}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(TAG)
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    obj = build(sprite, coll)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{TAG}: {tris} triangles")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        top_mask(obj, views / "top_19.png")
        (views / "pal_19.json").write_text(json.dumps(pal_grid(obj)))
    fmt = "AUTO"
    for o in bpy.data.objects:
        o.hide_render = False
    if "--no-bake" not in argv:
        bd = HERE / "bake"
        bd.mkdir(parents=True, exist_ok=True)
        bake(obj, bd)
        fmt = "WEBP"
    sh = common.outline_shell(obj, coll, voxel=0.008, faces=1200, smooth=8)
    common.export_sprite_model(WT, [obj, sh], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    if views:
        sh.hide_render = True
        lit_views(obj, views, ("top", "side", "front", "rear", "q34", "q34b", "game", "under"))
    (HERE / "stats.json").write_text(json.dumps({"triangles": tris}))


if __name__ == "__main__":
    main()
