"""Falling canister (newshd.shp frame 77), a machined steel munitions canister.

Reading of the sprite (24x28, 13x25 px of picture, no ink border: the model goes to the sprite's
outer edge, D74). The canister flies nose down the screen; its axis is the sprite's column edge
12.5, and it is a body of revolution about that axis (round where the sprite is round):
- Rows 3-7: the domed tail cap (pal 8). The bright cluster at its upper left and the bright line
  down column 10 of the body are sheen on round steel, not geometry. A small hub closes the dome's
  apex (seen from the rear).
- Rows 8-10: a recessed band (pal 6) under the dome, with a dark sensor slot (pal 2) cut into its
  upper right (columns 13-15). Row 10 is the band's lower lip.
- Rows 11-12: a narrower neck (half width 5.5 px, pal 8), chamfered at both ends.
- Rows 13-18: the barrel (half width 6.5 px, pal 8) with a machined longitudinal seam groove (pal
  3, column 15) and a row of rivets either side of it.
- Row 19: a conical shoulder in to the nose collar.
- Rows 20-22: two clamp brackets (pal 5) at 3 and 9 o'clock hold the nose cone: a flange (row 20,
  out to half width 5.5) and an arm (rows 21-22, half width 4.5), two bolts on each flange.
- Rows 20-27: the red nose cone (pal 70), an ogive with a dark red fuse tip (pal 68) and a brown
  conduit fairing (pal 164) down its upper right (columns 13-14).
- Underside: the same body of revolution; no detail.

Colours: the median palette index of each region (darkest shading <= 3 and highlights >= 13 left out):
dome 7-8 (8 used, as the barrel), band 6, neck 8, barrel 8, seam 3, shoulder 8, clamps 5, cone 70,
conduit 164, tip 68 (the cone's darkest end), slot 2.

    tools/build-models.sh -j 2 assets/blender/enemies/newshd-77.py   (extra args after --: [--views DIR] [--no-bake])

Exports public/models/enemies/newshd-77.glb (one frame, 77) with an outline shell (D51) and src/render/spriteModels/newshd-77.json.
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

HERE = Path("/Users/dlomibao/projects/tyrian-scratch/e1-enemies-2/newshd-77/final")
NAME = "newshd-77"
PX = 1 / 12
AXIS_C = 12.5  # the canister's axis: sprite column edge
ZS = 1.0       # cross-section height over width (round)

# Material slots and palette indices.
DOME, BAND, NECK, BODY, SEAM, SLOT, CLAMP, RED, TIP, CONDUIT, BOLT = range(11)
PAL_OF = {DOME: 8, BAND: 6, NECK: 8, BODY: 8, SEAM: 3, SLOT: 2, CLAMP: 5, RED: 70, TIP: 68,
          CONDUIT: 164, BOLT: 6}
FINISH = {  # metallic, roughness: satin steel, painted cone
    DOME: (0.4, 0.38), BAND: (0.35, 0.45), NECK: (0.4, 0.36), BODY: (0.4, 0.38), SEAM: (0.2, 0.7),
    SLOT: (0.1, 0.12), CLAMP: (0.35, 0.44), RED: (0.12, 0.48), TIP: (0.3, 0.4), CONDUIT: (0.2, 0.55),
    BOLT: (0.45, 0.32),
}


# --- profile ------------------------------------------------------------------------------------

def pchip_pts(pts):
    xs, ys = zip(*pts)
    return T.pchip(list(xs), list(ys))


DOME_Y0, DOME_Y1, DOME_A = 2.96, 7.2, 2.0


def dome_r(y):
    t = min(1.0, max(0.0, (DOME_Y1 - y) / (DOME_Y1 - DOME_Y0)))
    return 6.5 * max(0.0, 1 - t ** DOME_A) ** (1 / DOME_A)


CONE = pchip_pts([(20.0, 3.58), (21.5, 3.62), (23.4, 3.56), (24.4, 3.3), (25.5, 2.52),
                  (26.5, 1.56), (27.4, 0.62), (27.95, 0.0)])


def profile():
    """(y, r) rings along the axis, y = sprite row edge (down the screen), r = radius in px.
    Two rings at one y make a flat annulus (a step)."""
    rings = [(2.80, 0.0), (2.80, 0.9), (2.86, 1.05), (3.02, 1.05), (3.02, dome_r(3.02))]
    for y in (3.12, 3.3, 3.55, 3.85, 4.2, 4.6, 5.05, 5.55, 6.1, 6.65, 7.2):
        rings.append((y, dome_r(y)))
    rings += [
        (7.95, 6.5), (8.12, 6.2), (9.92, 6.2), (10.08, 6.5),   # recessed band, its lower lip
        (10.68, 6.5), (11.02, 5.45), (12.98, 5.45), (13.32, 6.5),  # neck
        (16.1, 6.5), (18.88, 6.5), (19.38, 5.6), (19.5, 5.25), (19.92, 4.7),  # barrel, shoulder, collar
        (19.98, 4.7), (19.98, 3.58),  # the collar's face, the cone steps out of it
    ]
    for y in (20.0, 20.6, 21.5, 22.5, 23.4, 24.0, 24.4, 24.9, 25.5, 26.0, 26.5, 26.95, 27.4, 27.7):
        rings.append((y, CONE(y)))
    rings.append((27.95, 0.0))
    return rings


def r_at(rings, y):
    for (y0, r0), (y1, r1) in zip(rings, rings[1:]):
        if y0 <= y <= y1 and y1 > y0:
            if y0 >= 20.0:
                return CONE(y)
            if y1 <= DOME_Y1 and y0 >= 3.02:
                return dome_r(y)
            return r0 + (r1 - r0) * (y - y0) / (y1 - y0)
    raise ValueError(y)


def region(y):
    if y < 3.02:
        return BAND
    if y < 7.95:
        return DOME
    if y < 10.08:
        return BAND
    if y < 13.32:
        return NECK
    if y < 19.5:
        return BODY
    if y < 19.99:
        return CLAMP
    if y < 26.3:
        return RED
    return TIP


def theta_of_dx(dx, r):
    return math.degrees(math.acos(max(-1.0, min(1.0, dx / r))))


# Patches: (theta0, theta1 degrees from +x round the axis, 90 = top), (y0, y1), depth px (negative
# = raised), material. Each gets a chamfered wall about 0.12 px wide.
PATCHES = [
    (theta_of_dx(3.5, 6.2), theta_of_dx(0.4, 6.2), 8.42, 9.9, 0.5, SLOT),        # sensor slot
    (theta_of_dx(3.55, 6.5), theta_of_dx(2.45, 6.5), 13.5, 18.75, 0.32, SEAM),   # seam groove
    (theta_of_dx(2.55, 3.58), theta_of_dx(0.45, 3.58), 20.15, 24.55, -0.24, CONDUIT),  # conduit
    (0.0, 360.0, 7.12, 7.3, 0.14, DOME),                                         # dome joint line
    (0.0, 360.0, 3.9, 4.06, 0.12, DOME),                                         # tail-cap ring
    (0.0, 360.0, 26.22, 26.36, 0.12, TIP),                                       # fuse tip joint
]
WALL = 0.12


def build_body(bm, mats_idx):
    rings = profile()
    # Angles: a base step plus every patch's edges.
    angs = set(round(i * 360 / 32, 4) for i in range(32))
    for t0, t1, y0, y1, d, m in PATCHES:
        if t1 - t0 >= 359:
            continue
        r = r_at(rings, (y0 + y1) / 2)
        dw = math.degrees(WALL / r)
        for a in (t0, t0 + dw, t1 - dw, t1):
            angs.add(round(a, 4))
    angs = sorted(angs)
    clean = []
    for a in angs:
        if clean and a - clean[-1] < 0.25:
            continue
        clean.append(a)
    angs = clean
    # Rings: the profile plus every patch's y edges.
    extra = []
    for t0, t1, y0, y1, d, m in PATCHES:
        for y in (y0, y0 + WALL, y1 - WALL, y1):
            extra.append((y, r_at(rings, y)))
    allr = sorted(rings + extra, key=lambda p: p[0])
    # drop exact duplicates (keep steps: same y, different r, in profile order)
    seq = []
    for p in rings:
        seq.append(p)
    for p in extra:
        if any(abs(p[0] - q[0]) < 1e-6 for q in seq):
            continue
        seq.append(p)
    # sort stable by y but keep the order of same-y steps as given in the profile
    order = {id(p): i for i, p in enumerate(rings)}
    seq.sort(key=lambda p: (p[0], order.get(id(p), 0)))

    def inside(t0, t1, a):
        return t0 - 1e-6 <= a <= t1 + 1e-6

    def depth_at(y, a):
        d = 0.0
        for t0, t1, y0, y1, dep, m in PATCHES:
            full = t1 - t0 >= 359
            r = 6.0
            dw = 0 if full else math.degrees(WALL / max(1.0, r_at(rings, (y0 + y1) / 2)))
            if y0 + WALL - 1e-6 <= y <= y1 - WALL + 1e-6 and (full or inside(t0 + dw, t1 - dw, a)):
                d = dep
        return d

    def patch_mat(y, a):
        for t0, t1, y0, y1, dep, m in PATCHES:
            full = t1 - t0 >= 359
            if y0 - 1e-6 <= y <= y1 + 1e-6 and (full or inside(t0, t1, a)):
                return m
        return None

    verts = []
    for y, r in seq:
        row = []
        for a in angs:
            rr = max(0.0, r - depth_at(y, a)) if r > 0 else 0.0
            th = math.radians(a)
            row.append(bm.verts.new((rr * math.cos(th), y, ZS * rr * math.sin(th))))
        verts.append(row)
    n = len(angs)
    for i in range(len(seq) - 1):
        y0, y1 = seq[i][0], seq[i + 1][0]
        for j in range(n):
            k = (j + 1) % n
            quad = [verts[i][j], verts[i][k], verts[i + 1][k], verts[i + 1][j]]
            if len({v.co.to_tuple(6) for v in quad}) < 3:
                continue
            try:
                f = bm.faces.new(quad)
            except ValueError:
                continue
            ym = (y0 + y1) / 2
            a0, a1 = angs[j], angs[k] if k else 360.0
            am = (a0 + a1) / 2
            m = patch_mat(ym, am)
            if m is None or (m in (DOME, TIP)):
                m = region(ym) if m is None else m
            f.material_index = mats_idx[m]
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)


def hull_into(bm, pts, mat):
    vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in vs if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    for f in {f for v in live if v.is_valid for f in v.link_faces}:
        f.material_index = mat


def cbox(x0, x1, y0, y1, z0, z1, ch):
    return T.cbox(x0, x1, y0, y1, z0, z1, ch)


def tapered(x0, x1, y0, y1, z0, z1, ch, x1_end, y_taper):
    """A chamfered block whose outer side (x1) runs in to x1_end over the last part from y_taper."""
    pts = []
    for (xa, xb, ya, yb) in ((x0, x1, y0, y_taper), (x0, x1_end, y_taper, y1)):
        pts += cbox(xa, xb, ya, yb, z0, z1, ch)
    return pts


def build_details(bm, mi):
    for s in (-1, 1):
        def X(x):
            return s * x
        # Clamp flange (row 20) and arm (rows 21-22).
        fl = cbox(2.9, 5.42, 19.55, 20.95, -1.7, 1.7, 0.22)
        hull_into(bm, [(X(p[0]), p[1], p[2]) for p in fl], mi[CLAMP])
        arm = tapered(2.9, 4.42, 20.85, 23.25, -1.15, 1.15, 0.2, 3.7, 22.6)
        hull_into(bm, [(X(p[0]), p[1], p[2]) for p in arm], mi[CLAMP])
        # Two bolts on each flange top.
        for bx, by in ((4.55, 20.0), (3.75, 20.45)):
            pts = []
            for k in range(6):
                a = math.radians(60 * k + 30)
                for z, rr in ((1.62, 0.36), (1.95, 0.3)):
                    pts.append((X(bx) + rr * math.cos(a), by + rr * math.sin(a), z))
            hull_into(bm, pts, mi[BOLT])
    # Rivets either side of the barrel seam (low domes on the surface).
    for dx in (1.85, 4.15):
        for ry in (14.2, 15.6, 17.0, 18.3):
            r0 = 6.5
            th = math.acos(dx / r0)
            cx, cz = r0 * math.cos(th), r0 * math.sin(th)
            nx, nz = math.cos(th), math.sin(th)
            pts = []
            for k in range(6):
                a = math.radians(60 * k)
                tx, tz = -nz, nx
                for h, rr in ((-0.15, 0.3), (0.12, 0.26), (0.2, 0.14)):
                    u = rr * math.cos(a)
                    v = rr * math.sin(a)
                    pts.append((cx + nx * h + tx * u, ry + v, cz + nz * h + tz * u))
            hull_into(bm, pts, mi[BOLT])


def materials(sprite, tag):
    out = []
    for slot in range(11):
        met, rough = FINISH[slot]
        out.append(common.palette_material(sprite, PAL_OF[slot], f"{tag}_{slot}", metallic=met, roughness=rough))
    return out


def build(sprite, coll):
    tag = NAME
    mi = {k: k for k in range(11)}
    bm = bmesh.new()
    build_body(bm, mi)
    build_details(bm, mi)
    # Sprite px (x right of the axis, y down the screen, z up) to Blender.
    m = Matrix(((PX, 0, 0, (AXIS_C - 12) * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(tag)
    bm.to_mesh(me)
    bm.free()
    for mat in materials(sprite, tag):
        me.materials.append(mat)
    obj = bpy.data.objects.new(tag, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(36))
    return obj


def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    bpy.context.view_layer.update()  # a fresh scene's view layer lists objects only after this
    T.TINT, T.TEXTURED = (0.97, 0.98, 1.0), tuple(range(11))
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
        bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.62))
        g = bpy.context.active_object
        g.name = "ground"
        gm = bpy.data.materials.new("ground")
        gm.use_nodes = True
        next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.09, 0.11, 0.08, 1)
        g.data.materials.append(gm)
    V = 400
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 4.0
    yc = (14 - 15.4) * PX
    views = {
        "top": ((0, yc, d), 2.6, (0, yc, 0)),
        "side": ((d, yc, 0), 2.6, (0, yc, 0)),
        "front": ((0, -d, 0), 2.6, (0, 0, 0)),
        "rear": ((0, d, 0), 2.6, (0, 0, 0)),
        "q34": ((d * 0.6, -d * 0.6 + yc, d * 0.65), None, (0, yc, 0)),
        "q34b": ((-d * 0.6, d * 0.6 + yc, d * 0.55), None, (0, yc, 0)),
        "game": ((0, -d * 0.5 + yc, d * 0.9), None, (0, yc, 0)),
        "under": ((d * 0.4, -d * 0.5, -d * 0.55), None, (0, yc, 0)),
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
    obj = build(sprite, coll)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        top_mask(obj, views / "top_77.png")
        (views / "pal_77.json").write_text(json.dumps(pal_grid(obj)))
    fmt = "AUTO"
    for o in bpy.data.objects:
        o.hide_render = False
    if "--no-bake" not in argv:
        bd = HERE / "bake" / NAME
        bd.mkdir(parents=True, exist_ok=True)
        bake(obj, bd)
        fmt = "WEBP"
    sh = common.outline_shell(obj, coll, voxel=0.012, faces=1500, smooth=8)
    common.export_sprite_model(WT, [obj, sh], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    if views:
        sh.hide_render = True
        lit_views(obj, views, "77", ("top", "side", "front", "rear", "q34", "q34b", "game", "under"))
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "stats.json").write_text(json.dumps({"triangles": tris}))


if __name__ == "__main__":
    main()
