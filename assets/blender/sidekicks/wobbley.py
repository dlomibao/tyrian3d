"""Wobbley (sidekick 5, tyrian.shp#8 frames 246, 265, 284, 303): a 3D version of its sprite.

WHAT IT IS (D122): an energy sidekick, not a machine. The sprite draws a ball of blue plasma
(a round core 6 px across, rows 4-9, columns 3-8, ringed by the dark blue 150 that is its ink)
with a white-hot filament (palette 62/63) wrapped round it, and tendrils of plasma lashing out to
both sides; the tendrils change every frame (whips, a hook, closed loops with 1 px holes) while
the core stays put: the "wobble". So the model is a free-floating plasma orb (style 0 rides beside
the ship, no mount is drawn), per frame:

- the core: a slightly squashed sphere (the sprite's round core, as tall as it is wide), pal 155
  (the median of the core's pixels without the dark ring and white streaks), half glowing;
- the tendrils: round plasma tubes swept along each frame's tendril pixels (tapering to rounded
  tips, closed loops where the sprite draws loops, their holes kept), fused to the core in one
  voxel-remeshed, smoothed skin (plasma, no creases), pal 156 (the tendrils' median);
- the hot filament: a thin white tube (pal 63 on 246, 62 elsewhere: each frame's own white) lying
  half sunk along the white streaks, over the core and out along the tendrils, fully glowing.

The four frames have different outlines, so each frame is its own mesh tagged with frame_part
(D17); frame 166 of the animation is blank and stays the (empty) sprite. Undersides: the closed
round bottom of the same skin, nothing more.

Run: tools/build-models.sh -j 2 assets/blender/sidekicks/wobbley.py (exports public/models/sidekicks/wobbley.glb
and src/render/spriteModels/wobbley.json). Previews: ... -- --renders DIR
"""

import json
import math
import statistics as st
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WT = Path(__file__).resolve().parents[3]  # repository root
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "sidekick-wobbley"
P = 1 / 12  # one sprite pixel
FRAMES = (246, 265, 284, 303)


def X(x):
    """Sprite x (columns, px from the left edge) to Blender X (the 12x14 block centred)."""
    return (x - 6) * P


def Y(y):
    """Sprite y (rows, px from the top edge) to Blender Y (up the screen is +Y)."""
    return (7 - y) * P


# --- Per-frame design, in sprite px: x, y are column/row positions (pixel centres at +0.5), z up
# from the core's centre plane, r the tube radius. The tendril paths run through the sprite's
# tendril pixels; the vein paths through its white (62/63) pixels.
DESIGN = {
    246: {
        "core": (5.95, 7.0, 3.0, 2.85, 2.6),  # cx, cy, rx, ry, rz
        "tendrils": [
            # lower-left whip: out of the core's lower left, along row 7-8, its tip curling down col 1
            [(4.3, 8.0, -0.2, 0.85), (3.0, 8.15, 0.1, 0.8), (2.1, 7.95, 0.35, 0.68), (1.45, 8.6, 0.3, 0.55),
             (1.45, 9.45, 0.0, 0.45)],
            # right: a fat lobe flung out (rows 5-7, columns 9-11), its blunt end spread up to row 5 and
            # down to row 7: one thick chain into a rounded crossbar, so the lobe is one smooth lump
            [(8.0, 6.8, 0.0, 1.0), (9.5, 6.75, 0.15, 1.08), (10.4, 6.6, 0.3, 1.12), (10.9, 6.5, 0.35, 1.0)],
            [(11.15, 5.75, 0.45, 0.7), (11.2, 6.45, 0.4, 0.85), (11.15, 7.2, 0.25, 0.7)],
        ],
        "veins": [
            [(1.45, 9.0), (1.8, 8.1), (2.6, 7.55), (3.5, 7.55), (4.4, 8.15), (5.4, 7.6), (6.2, 6.6),
             (7.3, 6.35), (8.4, 6.75), (9.5, 7.3), (10.4, 7.2)],
        ],
        "white": 63,
        "smooth": 14,  # more relaxing: the lobe's two chains fuse without a crease
    },
    265: {
        "core": (6.0, 6.95, 2.95, 2.8, 2.6),
        "tendrils": [
            # left: a hook that closes into a loop (row 5 out to column 0, down, back along row 8)
            [(3.7, 5.45, 0.4, 0.6), (2.2, 5.5, 0.6, 0.58), (0.75, 5.6, 0.5, 0.55), (0.6, 6.6, 0.1, 0.5),
             (1.0, 7.6, -0.3, 0.55), (1.9, 8.35, -0.4, 0.55), (3.2, 8.45, -0.3, 0.6), (4.2, 8.2, -0.2, 0.7)],
            [(3.8, 6.4, 0.2, 0.55), (2.5, 6.45, 0.2, 0.45)],
            # right: a small loop over the top (row 4 to column 10 and back under at row 6-7)
            [(4.6, 4.55, 0.8, 0.5), (6.5, 4.4, 1.2, 0.55), (8.6, 4.6, 1.0, 0.62), (9.9, 4.9, 0.6, 0.5),
             (10.5, 5.7, 0.2, 0.5), (10.1, 6.6, -0.1, 0.5), (9.3, 7.3, -0.2, 0.5), (8.3, 7.3, -0.2, 0.6)],
        ],
        "veins": [
            [(0.9, 5.55), (2.2, 5.55), (3.3, 6.3), (4.4, 7.3)],
            [(5.3, 5.4), (6.4, 6.4), (7.5, 7.0), (8.6, 7.4)],
        ],
        "white": 62,
    },
    284: {
        "core": (6.0, 7.05, 2.45, 2.85, 2.5),
        "tendrils": [
            # left: a straight whip out along rows 6-7 to its tip at column 0
            [(4.0, 6.9, 0.0, 0.85), (2.6, 6.95, 0.2, 0.85), (1.4, 7.05, 0.3, 0.68), (0.55, 7.45, 0.2, 0.45)],
            # right: a thick tail down and out to the lower right (rows 7-10)
            [(7.6, 7.4, 0.0, 1.0), (9.4, 7.85, -0.15, 1.15), (10.3, 9.0, -0.35, 1.0), (11.1, 9.9, -0.5, 0.75),
             (11.45, 10.55, -0.5, 0.42)],
        ],
        "veins": [
            [(3.0, 6.6), (4.3, 6.7), (4.8, 7.6), (5.6, 8.35), (6.6, 8.5), (7.6, 8.1), (8.6, 7.6), (9.6, 8.1)],
        ],
        "white": 62,
    },
    303: {
        "core": (5.7, 7.2, 2.9, 2.95, 2.6),
        "tendrils": [
            # left: a closed loop round the hole at (row 7, column 2)
            [(3.6, 5.5, 0.5, 0.6), (2.4, 6.0, 0.6, 0.8), (1.45, 6.75, 0.4, 0.65), (0.85, 7.6, 0.0, 0.75),
             (0.9, 8.5, -0.3, 0.7), (1.9, 9.0, -0.4, 0.9), (3.2, 9.3, -0.3, 0.7), (4.4, 9.2, -0.2, 0.65)],
            # right: a wider loop round the holes at (7, 9), (8, 9-10), (9, 10)
            [(8.1, 5.8, 0.3, 0.7), (9.6, 6.45, 0.5, 0.55), (10.9, 7.2, 0.4, 0.52), (11.5, 8.5, 0.0, 0.5),
             (11.4, 9.9, -0.3, 0.55), (11.0, 10.5, -0.4, 0.5), (9.9, 10.5, -0.5, 0.5), (9.0, 10.2, -0.5, 0.5), (8.35, 9.4, -0.4, 0.66),
             (7.5, 9.35, -0.3, 0.7)],
        ],
        "veins": [
            [(2.2, 6.6), (3.3, 5.6)],
            # the lower streak zig-zags over rows 8 and 9: (4,9) (4,8) (5,8) (6,9) (7,8)
            [(4.5, 9.45), (4.5, 8.6), (5.5, 8.5), (6.5, 9.4), (7.5, 8.5)],
        ],
        "white": 62,
        "rv": 0.45,
    },
}


def catmull(pts, sub):
    """Catmull-Rom through `pts` (tuples), `sub` samples per segment, ends clamped."""
    out = []
    n = len(pts)
    if n == 1:
        return [tuple(pts[0])]
    for i in range(n - 1):
        p0 = pts[max(0, i - 1)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(n - 1, i + 2)]
        for s in range(sub):
            t = s / sub
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(tuple(pts[-1]))
    return out


def resample(pts, step):
    """Points along a polyline every `step` (in its first two coordinates' units)."""
    out = [pts[0]]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        d = math.dist(a[:2], b[:2])
        if d == 0:
            continue
        t = step - acc
        while t <= d:
            f = t / d
            out.append(tuple(x + (y - x) * f for x, y in zip(a, b)))
            t += step
        acc = d - (t - step)
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return out


def sphere(bm, centre, radii, segs=16, rings=10):
    """A closed UV ellipsoid (Blender units)."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    top = bm.verts.new((cx, cy, cz + rz))
    bot = bm.verts.new((cx, cy, cz - rz))
    loops = []
    for j in range(1, rings):
        th = math.pi * j / rings
        loops.append([bm.verts.new((cx + rx * math.sin(th) * math.cos(2 * math.pi * i / segs),
                                    cy + ry * math.sin(th) * math.sin(2 * math.pi * i / segs),
                                    cz + rz * math.cos(th))) for i in range(segs)])
    for i in range(segs):
        k = (i + 1) % segs
        bm.faces.new((top, loops[0][i], loops[0][k]))
        bm.faces.new((bot, loops[-1][k], loops[-1][i]))
        for a, b in zip(loops, loops[1:]):
            bm.faces.new((a[i], b[i], b[k], a[k]))


def chain(bm, path_px, step=0.18, segs=12, rings=8):
    """A round tube as a chain of overlapping spheres along a smooth path (px: x, y, z, r); the voxel
    remesh unions them into one tube with rounded ends."""
    pts = resample(catmull(path_px, 6), step)
    for x, y, z, r in pts:
        sphere(bm, (X(x), Y(y), z * P), (r * P,) * 3, segs, rings)


def new_obj(name, bm, coll):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def apply_mods(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def skin(obj, voxel, smooth_iter, faces):
    """Voxel union, relax, thin to about `faces` faces."""
    rm = obj.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    apply_mods(obj)
    sm = obj.modifiers.new("smooth", "LAPLACIANSMOOTH")
    sm.iterations = smooth_iter
    sm.lambda_factor = 0.6
    sm.use_volume_preserve = True
    n = len(obj.data.polygons)
    dec = obj.modifiers.new("decimate", "DECIMATE")
    dec.ratio = min(1.0, faces / max(1, n))
    apply_mods(obj)
    obj.data.shade_smooth()


def make_materials(sprite):
    mats = {
        "core": common.palette_material(sprite, 155, f"{NAME}-core", metallic=0.0, roughness=0.32, emission_strength=0.45),
        # the tendrils' median is 156 on 246/265 and 155 on 284/303 (D17 frame colours)
        "tendril": common.palette_material(sprite, 156, f"{NAME}-tendril", metallic=0.0, roughness=0.32,
                                           emission_strength=0.5, frames={284: 155, 303: 155}),
        63: common.palette_material(sprite, 63, f"{NAME}-hot63", metallic=0.0, roughness=0.3, emission_strength=1.0),
        62: common.palette_material(sprite, 62, f"{NAME}-hot62", metallic=0.0, roughness=0.3, emission_strength=1.0),
    }
    return mats


def build_frame(f, mats, coll):
    d = DESIGN[f]
    cx, cy, rx, ry, rz = d["core"]
    bm = bmesh.new()
    sphere(bm, (X(cx), Y(cy), 0.0), (rx * P, ry * P, rz * P), 32, 20)
    for path in d["tendrils"]:
        chain(bm, path)
    body = new_obj(f"wobbley_{f}", bm, coll)
    skin(body, voxel=0.0045, smooth_iter=d.get("smooth", 6), faces=1000)
    body.data.materials.append(mats["core"])
    body.data.materials.append(mats["tendril"])
    for p in body.data.polygons:
        c = p.center
        u = (c.x - X(cx)) / (rx * P)
        v = (c.y - Y(cy)) / (ry * P)
        p.material_index = 0 if u * u + v * v <= 1.06 ** 2 else 1

    # The hot filament, laid along the skin's top (half sunk).
    bm2 = bmesh.new()
    bm2.from_mesh(body.data)
    tree = BVHTree.FromBMesh(bm2)
    bm2.free()
    vb = bmesh.new()
    rv = d.get("rv", 0.34)  # px, the filament's radius; it stands 0.13 px proud of the skin, tapering at its ends
    for path in d["veins"]:
        pts = resample(catmull([(x, y) for x, y in path], 6), 0.1)
        n = len(pts)
        for i, (x, y) in enumerate(pts):
            hit = tree.ray_cast(Vector((X(x), Y(y), 1.0)), Vector((0, 0, -1)))
            if hit[0] is None:
                continue
            t = i / max(1, n - 1)
            r = rv * (0.5 + 0.5 * min(1.0, t / 0.2, (1 - t) / 0.2))
            z = hit[0].z - (r - 0.13) * P
            sphere(vb, (X(x), Y(y), z), (r * P,) * 3, 10, 6)
    vein = new_obj(f"wobbley_{f}_vein", vb, coll)
    skin(vein, voxel=0.0035, smooth_iter=3, faces=220)
    vein.data.materials.append(mats[d["white"]])
    # one object per frame
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    body.select_set(True)
    vein.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    common.frame_part(body, [f])
    return body


# --- measuring and rendering (scratch only; adapted from the atom-bombs A design script) ----------

def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = [w for w in str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split()
                 if want.split("_")[1] in w]
        scene.render.engine = names[0]


def camera(scene, name, loc, look, ortho=None, lens=80):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    data.clip_start = 0.01
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


def show_only(objs):
    keep = {o.name for o in objs}
    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in keep
            o.hide_viewport = o.name not in keep


def top_mask(objs, out_png, k=10):
    scene = bpy.context.scene
    show_only(objs)
    set_engine(scene, "BLENDER_WORKBENCH")
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.show_object_outline = False
    scene.display.shading.show_cavity = False
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 12 * k, 14 * k
    scene.render.resolution_percentage = 100
    scene.render.filter_size = 0.0
    cam = camera(scene, "mask_cam", (0, 0, 5), (0, 0, 0), ortho=14 / 12)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    scene.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)


def region_colours(objs, sprite, frame):
    """Palette index seen from straight above at each sprite pixel centre; per region (core,
    tendrils, white filament) the sprite's median index (dark ring 147/150 and the opposite extreme
    trimmed) against the model's."""
    show_only(objs)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    fr = next(x for x in sprite["frames"] if x["index"] == frame)
    pix = fr["pixels"]
    cx, cy, rx, ry, _ = DESIGN[frame]["core"]
    got = {}
    for r in range(14):
        for c in range(12):
            hit, loc, nor, idx, obj, mw = scene.ray_cast(dg, Vector((X(c + 0.5), Y(r + 0.5), 2.0)), Vector((0, 0, -1)))
            if hit:
                ev = obj.evaluated_get(dg)
                mi = ev.data.polygons[idx].material_index
                got[(r, c)] = int(ev.data.materials[mi].name.split("_")[1])
    reg = {"core": [], "tendrils": [], "white": []}
    for r in range(14):
        for c in range(12):
            v = pix[r][c]
            if v < 0 or v in (147, 150):
                continue
            if v in (62, 63):
                reg["white"].append((r, c))
            elif ((c + 0.5 - cx) / rx) ** 2 + ((r + 0.5 - cy) / ry) ** 2 <= 1.0:
                reg["core"].append((r, c))
            else:
                reg["tendrils"].append((r, c))
    out = {}
    for name, cells in reg.items():
        sv = sorted(pix[r][c] for r, c in cells)
        mv = sorted(got.get((r, c), -1) for r, c in cells)
        out[name] = {"sprite": st.median(sv) if sv else None, "model": st.median(mv) if mv else None,
                     "model_hits": {str(k): mv.count(k) for k in sorted(set(mv))}}
    grid = [" ".join(f"{got.get((r, c), -1):>3}" for c in range(12)) for r in range(14)]
    return out, grid


def setup_eevee(scene, res):
    set_engine(scene, "BLENDER_EEVEE")
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.filter_size = 1.2
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.05, 0.055, 0.07, 1)
    bg.inputs["Strength"].default_value = 0.9
    try:
        scene.view_settings.view_transform = "AgX"
    except TypeError:
        pass
    for name, rot, e in (("key", (math.radians(40), math.radians(-25), math.radians(20)), 3.2),
                         ("fill", (math.radians(65), math.radians(40), math.radians(200)), 1.0)):
        if bpy.data.objects.get(name):
            continue
        L = bpy.data.lights.new(name, "SUN")
        L.energy = e
        L.angle = math.radians(8)
        o = bpy.data.objects.new(name, L)
        o.rotation_euler = rot
        scene.collection.objects.link(o)


def render_views(frames, out_dir):
    scene = bpy.context.scene
    setup_eevee(scene, (420, 420))
    D = 3.2
    tilt = math.radians(15)
    views = {
        "top": ((0, 0, 4), (0, 0, 0), 1.35),
        "game": ((0, -D * math.sin(tilt), D * math.cos(tilt)), (0, 0, 0), None),
        "side": ((D, 0, 0.0), (0, 0, 0.0), 1.35),
        "front": ((0, D, 0.0), (0, 0, 0.0), 1.35),
        "rear": ((0, -D, 0.0), (0, 0, 0.0), 1.35),
        "q34": ((D * 0.62, -D * 0.6, D * 0.55), (0, 0, 0.0), None),
        "q34f": ((-D * 0.62, D * 0.62, D * 0.5), (0, 0, 0.0), None),
        "under": ((D * 0.4, -D * 0.5, -D * 0.75), (0, 0, 0), None),
    }
    per_frame = {"top", "game", "q34", "side"}
    for v, (loc, look, ortho) in views.items():
        cam = camera(scene, f"cam_{v}", loc, look, ortho=ortho, lens=95)
        if v == "top":
            cam.rotation_euler = (0, 0, 0)
        scene.camera = cam
        for f in (FRAMES if v in per_frame else FRAMES[:1]):
            show_only([frames[f]])
            scene.render.filepath = str(out_dir / f"{f}_{v}.png")
            bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    renders = Path(argv[argv.index("--renders") + 1]) if "--renders" in argv else None
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    mats = make_materials(sprite)
    frames = {f: build_frame(f, mats, coll) for f in FRAMES}
    tris = {f: sum(len(p.vertices) - 2 for p in o.data.polygons) for f, o in frames.items()}
    print("wobbley A: triangles per frame", tris)
    shells = {}
    for f, o in frames.items():
        sh = common.outline_shell(o, coll, voxel=0.006, faces=620)
        common.frame_part(sh, [f])
        shells[f] = sh
    common.export_sprite_model(WT, [*frames.values(), *shells.values()], "sidekicks/wobbley", sprite["sprites"])
    if renders:
        renders.mkdir(parents=True, exist_ok=True)
        report = {"triangles": tris, "shell_faces": {f: len(s.data.polygons) for f, s in shells.items()},
                  "colours": {}, "grid": {}}
        for f in FRAMES:
            top_mask([frames[f]], renders / f"mask_{f}.png")
            report["colours"][f], report["grid"][f] = region_colours([frames[f]], sprite, f)
        if "--no-views" not in argv:
            render_views(frames, renders)
        (renders / "report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
