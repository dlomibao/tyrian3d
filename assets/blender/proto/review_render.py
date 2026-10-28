"""Render the fixed review views of a model and sample it by raycasting (for tools/review_sheet.py).

    blender --background --python assets/blender/proto/review_render.py -- <name> <proto|current|reshape> <out_dir> <px_per_px>

Imports the exported .glb files (public/models/proto/... or public/models/...) of the model, or of
every piece of an assembly placed as in the layout, so what's reviewed is exactly what the game
would load. Writes into <out_dir>: top_flat.png (unlit palette colours, k image px per sprite px),
top.png, side.png, front.png, q1.png, q2.png, game.png and samples.json (height and palette index
under each sprite pixel's centre, seam samples, triangles, bounding box).
"""

import json
import math
import re
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent))
ROOT = next(p for p in HERE.parents if (p / "package.json").exists())
import common  # noqa: E402
from shape_model import model_paths, piece_path  # noqa: E402

PX = 1 / 12
PANEL = 480


def srgb_lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)


def import_model(name, which, doc):
    """Import the model's .glb files at their places; returns the mesh objects."""
    W, H = doc["size"]
    paths = model_paths()
    base = ROOT / "public" / "models" / {"proto": "proto", "reshape": "proto-reshape"}.get(which, "")
    meshes = []
    missing = []
    for p in doc["pieces"]:
        frame = p.get("frame")
        if name.startswith("assembly-"):
            path = piece_path(p["model"], frame, paths)
        else:
            path = json.loads((ROOT / "src" / "render" / "spriteModels" / f"{name}.json").read_text())["model"]
        f = base / f"{path}.glb"
        if not f.exists():
            missing.append(str(f))
            continue
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(f))
        new = [o for o in bpy.data.objects if o not in before]
        # Parts shown only on other frames (common.frame_part) go.
        for o in list(new):
            frames = o.get("tyrian_frames")
            if frames is not None and frame is not None and int(frame) not in [int(v) for v in frames]:
                new.remove(o)
                bpy.data.objects.remove(o, do_unlink=True)
        cx = (p["x0"] + p["w"] / 2 - W / 2) * PX
        cy = -(p["y0"] + p["h"] / 2 - H / 2) * PX
        for o in new:
            if o.parent is None:
                o.location = Vector(o.location) + Vector((cx, cy, 0))
        meshes += [o for o in new if o.type == "MESH"]
    bpy.context.view_layer.update()
    return meshes, missing


def palette_colours(meshes, doc):
    """Every pal_<index> material shows its level-palette colour (diffuse_color for Workbench)."""
    for o in meshes:
        for m in o.data.materials:
            if m is None:
                continue
            g = re.match(r"pal_(\d+)", m.name)
            rgb = doc["colors"].get(g.group(1)) if g else None
            if rgb is not None:
                m.diffuse_color = (*[srgb_lin(c) for c in rgb], 1.0)
            elif m.use_nodes:
                bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if bsdf:
                    m.diffuse_color = tuple(bsdf.inputs["Base Color"].default_value)


def setup(flat):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    sh = scene.display.shading
    sh.light = "FLAT" if flat else "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = not flat
    sh.show_object_outline = not flat
    sh.show_shadows = False
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def camera(location, look_at, ortho=None, fov=None, top=False):
    data = bpy.data.cameras.new("cam")
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    elif fov:
        data.sensor_fit = "VERTICAL"
        data.angle_y = math.radians(fov)
    cam = bpy.data.objects.new("cam", data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    # Camera looks down its -Z with its +Y up: keep +Y towards world up (top view: sprite up).
    cam.rotation_euler = (0, 0, 0) if top else (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    return cam


def render(cam, path, rx, ry):
    scene = bpy.context.scene
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    data = cam.data
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(data)


def samples(doc, meshes):
    """Height and palette index under each sprite pixel's centre; seam samples across piece edges."""
    W, H = doc["size"]
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    down = Vector((0, 0, -1))

    def cast(px, py):
        hit, loc, _n, face, obj, _m = scene.ray_cast(dg, Vector(((px - W / 2) * PX, -(py - H / 2) * PX, 50)), down)
        if not hit:
            return None, None
        mats = obj.data.materials
        ev = obj.evaluated_get(dg)
        mi = ev.data.polygons[face].material_index if face < len(ev.data.polygons) else 0
        name = mats[mi].name if mi < len(mats) and mats[mi] else ""
        g = re.match(r"pal_(\d+)", name)
        return loc.z / PX, (int(g.group(1)) if g else -1)

    height = np.full((H, W), np.nan)
    index = np.full((H, W), -2, dtype=int)
    for y in range(H):
        for x in range(W):
            z, i = cast(x + 0.5, y + 0.5)
            if z is not None:
                height[y, x], index[y, x] = z, i
    seams = []
    if len(doc["pieces"]) > 1:
        edges = set()
        for p in doc["pieces"]:
            edges.add(("x", p["x0"]))
            edges.add(("x", p["x0"] + p["w"]))
            edges.add(("y", p["y0"]))
            edges.add(("y", p["y0"] + p["h"]))
        boxes = [(p["x0"], p["y0"], p["x0"] + p["w"], p["y0"] + p["h"]) for p in doc["pieces"]]

        def inside(x, y):
            return any(a <= x < c and b <= y < d for a, b, c, d in boxes)

        eps = 0.02
        for axis, e in sorted(edges):
            n = H if axis == "x" else W
            for t in range(n):
                a = (e - eps, t + 0.5) if axis == "x" else (t + 0.5, e - eps)
                b = (e + eps, t + 0.5) if axis == "x" else (t + 0.5, e + eps)
                if not (inside(*a) and inside(*b)):
                    continue
                za, _ = cast(*a)
                zb, _ = cast(*b)
                if za is None and zb is None:
                    continue
                seams.append([axis, e, t, za, zb])
    return height, index, seams


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    name, which, out, k = argv[0], argv[1], Path(argv[2]), int(argv[3])
    out.mkdir(parents=True, exist_ok=True)
    doc = json.loads((ROOT / ".shape" / name / "regions.json").read_text())
    W, H = doc["size"]
    clear_scene()
    meshes, missing = import_model(name, which, doc)
    if not meshes:
        raise SystemExit(f"no meshes for {name} ({which}); missing {missing}")
    palette_colours(meshes, doc)
    ext = max(W, H) * PX
    # Top views at k image px per sprite px, centred on the sprite.
    setup(flat=True)
    render(camera((0, 0, 20), (0, 0, 0), ortho=ext, top=True), out / "top_flat.png", W * k, H * k)
    setup(flat=False)
    render(camera((0, 0, 20), (0, 0, 0), ortho=ext, top=True), out / "top.png", W * k, H * k)
    # Elevations: same scale for every model of this size; ground (z = 0) a quarter up the panel.
    # Elevations: 2 panels wide, 1 high, at one scale for every model of this sprite size (so
    # current and prototype compare); ground (z = 0) 30% of the way up.
    span = ext * 1.4
    zc = span / 2 * 0.4
    render(camera((30, 0, zc), (0, 0, zc), ortho=span), out / "side.png", 2 * PANEL, PANEL)
    render(camera((0, -30, zc), (0, 0, zc), ortho=span), out / "front.png", 2 * PANEL, PANEL)
    d = ext * 1.45 + 1.5  # small sprites need the extra margin
    render(camera((d * 0.55, -d * 0.6, d * 0.55), (0, 0, 0), fov=35), out / "q1.png", PANEL, PANEL)
    render(camera((-d * 0.6, d * 0.5, d * 0.55), (0, 0, 0), fov=35), out / "q2.png", PANEL, PANEL)
    render(camera((0, -d * 0.6, d * 0.8), (0, 0, 0), fov=35), out / "game.png", PANEL, PANEL)
    height, index, seams = samples(doc, meshes)
    dg = bpy.context.evaluated_depsgraph_get()
    tris = 0
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in meshes:
        ev = o.evaluated_get(dg)
        ev.data.calc_loop_triangles()
        tris += len(ev.data.loop_triangles)
        for v in ev.data.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    np.save(out / "height.npy", height)
    np.save(out / "index.npy", index)
    (out / "samples.json").write_text(json.dumps({
        "name": name, "which": which, "k": k, "panel": PANEL, "elevation_span": span, "elevation_zc": zc,
        "triangles": tris, "bbox_min": list(lo), "bbox_max": list(hi), "missing": missing, "seams": seams,
    }))
    print(f"review views of {name} ({which}) in {out}: {tris} triangles")


if __name__ == "__main__":
    main()
