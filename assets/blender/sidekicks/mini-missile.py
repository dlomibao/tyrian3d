"""Mini-Missile sidekick, design A (item 10; tyrian.shp#8 frames 163, 182, 201; 12x14 block).

WHAT IT IS: a small mounted side pod (style 0) that fires mini-missiles: a launcher tube with the
next missile's glowing warhead poking out of its muzzle, a feed line back to a squat engine drum.

Reading of the sprite (inner mask, D74: the 1 px ink ring is the game's own outline). x is px from
the centre column edge (6), y the sprite row edge (down the screen = rear), z up:
- Rows 2-3 (half width 1, 2) and row 4 cols 4-7: the warhead, a rounded ogive, glowing (127 hot on
  163, 124 on 182, 119 on 201): one missile nose, round in every section.
- Row 4 cols 3 and 8 (grey 11 / 10): two guide cheeks either side of the warhead, the launch rails
  running ahead of the muzzle.
- Row 5 (8 11 11 10 10 7): a raised muzzle collar right across, half width 3.
- Rows 6-7: the launch tube, half width 3, round (5 left, 3-4 right: shading on a cylinder); its top
  carries a glass slot (cols 5-6, glowing 118-127) between two rails (cols 4 and 7).
- Row 8 (32 115 114 32 inside the ring): a dark yoke 4 px wide at the tube's back, the glowing feed
  line between its cheeks; row 9 the feed line alone, 2 px.
- Rows 10-13: the engine drum, half width 2 / 3 / 3 / 1: a round-shouldered drum, rounded off at the
  back into a dark nozzle (row 13: 4 3). The bright row 11 (15 13 12) is sheen on its top.

Animation: the three frames only recolour the glow; a pulse runs back from the warhead to the feed
line. One model, its glowing parts recoloured per frame (palette_material frames=, D17), the
indices the medians of each part's pixels on each frame.

Colours (median index per region, darkest shading and brightest highlights left out): collar and
cheeks 10, tube 7, slot rails 9, drum 9, its band and hatch 10, yoke and nozzle 3 (the sprite's
near-black 32 there, lifted one step to the darkest grey so it reads as dark metal, not a hole).

Run: tools/build-models.sh -j 2 assets/blender/sidekicks/mini-missile.py
(--views DIR after -- also writes review renders.) Exports public/models/sidekicks/mini-missile.glb
and src/render/spriteModels/mini-missile.json.
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "sidekick-mini-missile"
TAG = "mini-missile"
PX = 1 / 12
W, H = 12, 14
F1, F2, F3 = 163, 182, 201

(TUBE, COLLAR, CHEEK, RAIL, DRUM, BAND, HATCH, YOKE, NOZ,
 WH_TIP, WH_BASE, SLOT_F, SLOT_R, FEED_F, FEED_R) = range(15)
GREYS = (TUBE, COLLAR, CHEEK, RAIL, DRUM, BAND, HATCH, YOKE, NOZ)
PAL_OF = {TUBE: 7, COLLAR: 10, CHEEK: 10, RAIL: 9, DRUM: 9, BAND: 10, HATCH: 10, YOKE: 3, NOZ: 3}
FINISH = {  # metallic, roughness: satin machined steel; the dark parts rougher
    TUBE: (0.35, 0.42), COLLAR: (0.45, 0.32), CHEEK: (0.4, 0.36), RAIL: (0.45, 0.32),
    DRUM: (0.35, 0.4), BAND: (0.5, 0.3), HATCH: (0.35, 0.42), YOKE: (0.25, 0.6), NOZ: (0.2, 0.65),
}
# Glow: base index (frame 163) and the other frames' indices (medians of the part's pixels).
GLOW = {
    WH_TIP: (127, {F2: 124, F3: 120}, 0.65),   # rows 2-3
    WH_BASE: (124, {F2: 120, F3: 115}, 0.65),  # row 4
    SLOT_F: (119, {F2: 121, F3: 120}, 0.8),    # row 6
    SLOT_R: (120, {F2: 123, F3: 126}, 0.8),    # row 7
    FEED_F: (114, {F2: 118, F3: 121}, 0.8),    # row 8
    FEED_R: (114, {F2: 119, F3: 123}, 0.8),    # row 9
}


def materials(sprite):
    mats = []
    for i in range(15):
        if i in GLOW:
            idx, fr, e = GLOW[i]
            mats.append(common.palette_material(sprite, idx, f"{TAG}-g{i}", metallic=0.0, roughness=0.3,
                                                emission_strength=e, frames=fr))
        else:
            m, r = FINISH[i]
            mats.append(common.palette_material(sprite, PAL_OF[i], f"{TAG}-{i}", metallic=m, roughness=r))
    return mats


# --- geometry helpers (sprite px) ---------------------------------------------------------------

def ring_pts(rx, rz, zc, n, expo=2.0, ztop=None):
    pts = []
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        c, s = math.cos(a), math.sin(a)
        x = rx * math.copysign(abs(c) ** (2 / expo), c)
        z = rz * math.copysign(abs(s) ** (2 / expo), s)
        z += zc
        if ztop is not None:
            z = min(z, ztop)
        pts.append((x, z))
    return pts


def revolve(part, prof, matf, n, zc=0.0, kz=1.0, expo=2.0, ztopf=None, cap0=True, cap1=True):
    """A lathe body along y through prof [(y, r)], sections rx = r, rz = kz * r (superellipse
    `expo`), centred at height zc; matf(y_mid, r_mid) gives each band's material; two rings at the
    same y make a flat step."""
    rings = []
    for y, r in prof:
        zt = ztopf(y) if ztopf else None
        pts = ring_pts(max(r, 1e-3), max(r, 1e-3) * kz, zc, n, expo, zt)
        rings.append(([part.v((x, y, z)) for x, z in pts], y, r))
    for (r0, y0, a0), (r1, y1, a1) in zip(rings, rings[1:]):
        mat = matf((y0 + y1) / 2, (a0 + a1) / 2)
        for i in range(n):
            j = (i + 1) % n
            q = (r0[i], r0[j], r1[j], r1[i])
            if abs(y1 - y0) < 1e-6:
                part.f(q, mat, out=(0, 1 if a1 < a0 else -1, 0))
            else:
                part.f(q, mat, away=(0, (y0 + y1) / 2, zc))
    if cap0:
        part.f(rings[0][0], matf(prof[0][0], prof[0][1]), out=(0, -1, 0))
    if cap1:
        part.f(rings[-1][0], matf(prof[-1][0], prof[-1][1]), out=(0, 1, 0))


def block(part, x0, x1, y0, y1, z0, z1, ch, mat, chz=None):
    T.hull(part, T.cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


def bolt(part, x, y, z, rad, h, mat, n=6):
    """A hex bolt head on a horizontal top face."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        pts += [(x + rad * math.cos(a), y + rad * math.sin(a), z - 0.1), (x + rad * 0.8 * math.cos(a), y + rad * 0.8 * math.sin(a), z + h)]
    T.hull(part, pts, mat)


# --- the pod ------------------------------------------------------------------------------------

DECK_Z = 2.45      # the tube's flat top (the slot deck)
FEED_Z = 0.35      # the feed line's axis


def build_warhead(P):
    prof = [(1.94, 0.0), (1.97, 0.32), (2.06, 0.6), (2.25, 0.88), (2.5, 1.16), (2.8, 1.44), (3.1, 1.66),
            (3.45, 1.84), (3.85, 1.96), (3.9, 1.96), (3.93, 1.84), (4.03, 1.84), (4.06, 1.98),
            (4.5, 2.02), (5.1, 2.02)]
    revolve(P, prof, lambda y, r: WH_TIP if y < 3.92 else WH_BASE, n=20, cap1=False)


def build_tube(P):
    prof = [(4.9, 2.1), (4.9, 2.72), (4.96, 2.96), (5.06, 3.02), (5.32, 3.02), (5.36, 2.92), (5.44, 2.92),
            (5.48, 3.02), (5.84, 3.02), (5.94, 2.88), (5.98, 2.86), (6.95, 2.86), (6.98, 2.8), (7.04, 2.8),
            (7.07, 2.86), (7.98, 2.86), (8.06, 2.52), (8.1, 2.22)]

    def matf(y, r):
        if y < 5.92:
            return COLLAR
        if y > 8.0:
            return YOKE
        return TUBE

    def ztop(y):
        return DECK_Z if 5.9 < y < 8.03 else None
    revolve(P, prof, matf, n=28, ztopf=ztop)
    # Guide cheeks ahead of the muzzle (row 4, cols 3 and 8): launch rails either side of the
    # warhead, chamfered, the front corners cut back.
    for s in (1, -1):
        x0, x1 = sorted((s * 2.1, s * 2.97))
        block(P, x0, x1, 3.92, 5.0, -1.55, 1.55, 0.22, CHEEK)
        # a bolt head on each cheek's top
        bolt(P, s * 2.53, 4.4, 1.55, 0.13, 0.07, BAND)
    # Slot along the top (rows 6-7, cols 5-6): glass, glowing, split at row 7 for the pulse,
    # between two rails (cols 4 and 7) with bolt heads at their ends.
    block(P, -0.92, 0.92, 5.98, 7.0, 2.1, 2.62, 0.06, SLOT_F)
    block(P, -0.92, 0.92, 7.0, 8.0, 2.1, 2.62, 0.06, SLOT_R)
    for s in (1, -1):
        x0, x1 = sorted((s * 0.92, s * 1.32))
        block(P, x0, x1, 5.9, 8.04, 1.9, 2.8, 0.12, RAIL)
        for y in (6.25, 7.7):
            bolt(P, s * 1.12, y, 2.8, 0.13, 0.08, COLLAR)


def build_feed(P):
    # The dark yoke at the tube's back (row 8, cols 4-7): two cheeks and a web under the feed line.
    for s in (1, -1):
        x0, x1 = sorted((s * 1.0, s * 2.04))
        block(P, x0, x1, 7.9, 8.98, -1.75, 1.45, 0.2, YOKE)
    block(P, -1.05, 1.05, 7.9, 8.98, -1.75, -0.5, 0.15, YOKE)
    # Feed line (rows 8-9): a glowing conduit, split at row 9, with coupling rings.
    prof = [(7.9, 0.95), (10.4, 0.95)]
    revolve(P, [(7.9, 0.95), (8.96, 0.95)], lambda y, r: FEED_F, n=12, zc=FEED_Z)
    revolve(P, [(9.06, 0.95), (10.4, 0.95)], lambda y, r: FEED_R, n=12, zc=FEED_Z)
    revolve(P, [(8.94, 0.9), (8.96, 1.08), (9.06, 1.08), (9.08, 0.9)], lambda y, r: BAND, n=12, zc=FEED_Z)
    revolve(P, [(9.8, 0.9), (9.83, 1.12), (10.1, 1.12), (10.1, 0.9)], lambda y, r: BAND, n=12, zc=FEED_Z)
    del prof


def build_drum(P):
    prof = [(9.98, 1.0), (10.02, 1.45), (10.15, 1.8), (10.35, 2.15), (10.6, 2.5), (10.85, 2.78), (11.1, 2.94),
            (11.4, 2.98), (11.44, 2.88), (11.52, 2.88), (11.56, 2.98), (12.45, 2.98), (12.47, 3.02),
            (12.76, 3.02), (12.8, 2.9), (12.95, 2.52), (13.1, 1.98), (13.3, 1.56), (13.5, 1.3), (13.68, 1.15),
            (13.72, 1.08)]

    def matf(y, r):
        if y > 13.71 and r < 1.0:
            return NOZ
        if 12.46 < y < 12.78:
            return BAND
        return DRUM
    revolve(P, prof, matf, n=28, kz=0.82, expo=2.6)
    # The nozzle (row 13: the sprite's dark 4 3): a short round bell out of the drum's back, its
    # throat recessed.
    revolve(P, [(13.6, 1.0), (13.95, 0.98), (13.98, 0.9), (13.98, 0.72), (13.6, 0.6)], lambda y, r: NOZ, n=20,
            cap0=False)
    # A hatch plate on the drum's top (rows 11-12), proud of it, with four bolt heads.
    block(P, -1.45, 1.45, 11.05, 12.35, 1.9, 2.56, 0.14, HATCH)
    for x in (-1.12, 1.12):
        for y in (11.35, 12.05):
            bolt(P, x, y, 2.56, 0.12, 0.07, BAND)
    # Underneath: a plain mounting rail (a plausible closed shape only).
    block(P, -0.9, 0.9, 6.3, 11.8, -3.15, -1.9, 0.2, YOKE)


def build(sprite, coll):
    P = T.Part(TAG, smooth_angle=36)
    build_warhead(P)
    build_tube(P)
    build_feed(P)
    build_drum(P)
    P.orient()
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, H / 2 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(TAG)
    bm.to_mesh(me)
    bm.free()
    for mat in materials(sprite):
        me.materials.append(mat)
    obj = bpy.data.objects.new(TAG, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(36))
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    return obj


def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    bpy.context.view_layer.update()
    T.TINT, T.TEXTURED = (0.97, 0.98, 1.0), GREYS
    try:
        T.bake_maps(obj, out_dir, size=512, samples=48)
    finally:
        T.TINT, T.TEXTURED = tint, textured


# --- measurement and views (scratch only) -------------------------------------------------------

def set_frame(obj, frame):
    """Preview only: recolour the glowing materials as the game does on `frame`."""
    for mat in obj.data.materials:
        rgbmap = mat.get("tyrian_frame_rgb")
        if mat.name not in BASE_RGB:
            bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            BASE_RGB[mat.name] = tuple(bsdf.inputs["Base Color"].default_value)
        if rgbmap is None:
            continue
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        rgb = rgbmap.get(str(frame))
        col = (*rgb, 1.0) if rgb is not None else BASE_RGB[mat.name]
        col = tuple(col[:3]) + (1.0,)
        bsdf.inputs["Base Color"].default_value = col
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = col


BASE_RGB = {}


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


def lit_views(obj, out):
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
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.09, 0.11, 0.08, 1)
    g.data.materials.append(gm)
    V = 400
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 2.6
    tilt = math.radians(32)
    views = [
        ("top", (0, 0, d), 1.35, F1), ("side", (d, 0, 0), 1.35, F1), ("front", (0, d, 0), 1.0, F1),
        ("rear", (0, -d, 0), 1.0, F1), ("q34", (d * 0.62, d * 0.62, d * 0.62), None, F1),
        ("q34b", (-d * 0.62, -d * 0.62, d * 0.5), None, F1),
        ("game163", (0, -d * math.sin(tilt), d * math.cos(tilt)), None, F1),
        ("game182", (0, -d * math.sin(tilt), d * math.cos(tilt)), None, F2),
        ("game201", (0, -d * math.sin(tilt), d * math.cos(tilt)), None, F3),
        ("under", (d * 0.45, d * 0.45, -d * 0.6), None, F1),
    ]
    for name, loc, ortho, frame in views:
        set_frame(obj, frame)
        g.hide_render = name in ("under", "side", "front", "rear")
        c = cam(scene, f"v_{name}", loc, (0, 0, 0), ortho=ortho, lens=95 if not name.startswith("game") else 140)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out / f"v_{name}.png")
        bpy.ops.render.render(write_still=True)
    set_frame(obj, F1)


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
        top_mask(obj, views / "top.png")
        (views / "pal.json").write_text(json.dumps(pal_grid(obj)))
    fmt = "AUTO"
    for o in bpy.data.objects:
        o.hide_render = False
    if "--no-bake" not in argv:
        bake(obj, tempfile.mkdtemp(prefix="mm_bake_"))
        fmt = "WEBP"
    sh = common.outline_shell(obj, coll, voxel=0.008, faces=1200, smooth=8)
    common.export_sprite_model(WT, [obj, sh], "sidekicks/mini-missile", sprite["sprites"], image_format=fmt)
    if views:
        sh.hide_render = True
        lit_views(obj, views)


if __name__ == "__main__":
    main()
