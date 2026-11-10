"""Bronze ball (newsha.shp frame 281): a SPACE MINE, a whole free-floating ball.

Identity (scout): type 565, armour 20, no turret or launcher, mv(0,0); in 1.6 MINEMAZE it is set in
mirrored walls of mines that hold still against the scrolling terrain, in 1.7 MINES it is spawned
on ground2. Its sister newsha-283 (dark steel ball) moves freely in 1.7. So it is built as a
whole round ball with a round, closed underside (no flat contact disc, no squash).

Plan outline: the sprite's inner mask (tools/sprite_mask.py, D74) traced as a radius per angle
round the ball's centre and fitted with a low-order Fourier series (orders 0-2) so the ball stays
round where the sprite is round and follows its slightly fuller lower right. Every horizontal
section is that outline scaled by cos(latitude); the vertical half height equals the mean plan
radius, so it is a true ball, not a squashed one.

Colour pal_181: the median of the sprite's pixels with the darkest shading (<= 178, the ink ring
and the lower-right shadow) and the brightest highlight (>= 186) dropped is 180.5; over the lit
upper half (rows <= 14) it is 181. The pale glint at columns 9-11 / rows 9-12 and the rim light on
the lower right edge are sheen on polished bronze (rubric), so they are not modelled.

Surface finish matches newsha-283: satin metal, a single machined equatorial seam (the ball is two
forged halves: a shallow V groove with chamfered lips, pal_179 at its floor) that sits on the
silhouette from above without denting it; nothing on the upper dome (any crown ring reads as a lid).
Underside: the lower hemisphere mirrors the upper one to a round pole (closed, plain).

    blender --background --python assets/blender/enemies/newsha-281.py [-- --renders DIR]

Exports enemies/newsha-281 (ball + outline shell, D51).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)

NAME = "newsha-281"
PX = 1 / 12

BODY = 181        # bronze body colour (median of the lit, unshaded pixels)
SEAM = 179        # groove floor, two steps darker
METALLIC, ROUGH = 0.55, 0.42   # satin bronze, not mirror gold
SEGMENTS = 64
ORDER = 2

# --- Plan outline -------------------------------------------------------------------------------

def get_masks():
    """The sprite's inner and free masks as numpy bools (rows x cols)."""
    import json
    import subprocess
    out = subprocess.run(["python3", str(ROOT / "tools" / "sprite_mask.py"),
                          NAME, "--json"], capture_output=True, text=True, cwd=str(ROOT)).stdout
    d = json.loads(out)
    d = d[0] if isinstance(d, list) else d
    rows = d["masks"]
    inner = np.array([[c == "#" for c in r] for r in rows])
    outer = np.array([[c != "." for c in r] for r in rows])
    return inner, outer


def trace_radius(mask, cx, cy, n=720):
    """Distance from (cx, cy) (continuous sprite px, y down) to the edge of the mask's pixel union
    along n angles (angle measured in the model's frame: x right, y up)."""
    h, w = mask.shape
    th = np.arange(n) * 2 * math.pi / n
    rad = np.zeros(n)
    for i, a in enumerate(th):
        dx, dy = math.cos(a), -math.sin(a)
        r, last = 0.0, 0.0
        while r < 20:
            x, y = cx + dx * r, cy + dy * r
            xi, yi = int(math.floor(x)), int(math.floor(y))
            if 0 <= xi < w and 0 <= yi < h and mask[yi, xi]:
                last = r
            r += 0.02
        rad[i] = last
    return th, rad


def fourier_fit(th, rad, order):
    cols = [np.ones_like(th)]
    for k in range(1, order + 1):
        cols += [np.cos(k * th), np.sin(k * th)]
    A = np.stack(cols, 1)
    coef, *_ = np.linalg.lstsq(A, rad, rcond=None)
    return coef


def fourier_eval(coef, th):
    th = np.asarray(th, dtype=float)
    r = np.full_like(th, coef[0])
    for k in range(1, (len(coef) - 1) // 2 + 1):
        r += coef[2 * k - 1] * np.cos(k * th) + coef[2 * k] * np.sin(k * th)
    return r


def grid_iou(coef, scale, cx, cy, inner, ss=8):
    """Rule IoU on the sprite grid of the plan outline (pixel covered when >= half covered)."""
    h, w = inner.shape
    o = (np.arange(ss) + 0.5) / ss
    xs = (np.arange(w)[:, None] + o[None, :]).ravel()
    ys = (np.arange(h)[:, None] + o[None, :]).ravel()
    X, Y = np.meshgrid(xs, ys)
    dx, dy = X - cx, -(Y - cy)
    rr = np.hypot(dx, dy)
    a = np.arctan2(dy, dx)
    ins = rr <= fourier_eval(coef, a) * scale
    cov = ins.reshape(h, ss, w, ss).mean(axis=(1, 3)) >= 0.5
    inter = (cov & inner).sum()
    union = (cov | inner).sum()
    return inter / union


def plan_outline():
    inner, _ = get_masks()
    ys, xs = np.nonzero(inner)
    cx = (xs.min() + xs.max() + 1) / 2
    cy = (ys.min() + ys.max() + 1) / 2
    th, rad = trace_radius(inner, cx, cy)
    coef = fourier_fit(th, rad, ORDER)
    best = max(((grid_iou(coef, s, cx, cy, inner), s) for s in np.arange(0.96, 1.04, 0.0025)))
    print(f"plan: centre ({cx}, {cy}) coef {np.round(coef, 3).tolist()} best grid IoU {best[0]:.4f} at scale {best[1]:.4f}")
    return coef * best[1], cx, cy


# --- Meridian profile ----------------------------------------------------------------------------

def meridian(R):
    """(z, plan scale) stations pole to pole: a full ball of vertical half height R (sprite-px
    units), centred at z = R so its lowest point is at z = 0, with a V-grooved equatorial seam."""
    H = R
    zc = H
    groove_h = 0.9 * PX
    groove_d = 0.2 * PX
    lip = 0.3 * PX
    st = []
    for lat in np.linspace(-84, -8, 12):
        st.append((zc + H * math.sin(math.radians(lat)), math.cos(math.radians(lat))))
    Rr = R
    for dz, ins in [(-lip, 0.0), (-lip * 0.4, groove_d * 0.7 / Rr), (0.0, groove_d / Rr),
                    (lip * 0.4, groove_d * 0.7 / Rr), (lip, 0.0)]:
        lat = math.asin(dz / H)
        st.append((zc + dz, math.cos(lat) - ins))
    for lat in np.linspace(8, 84, 12):
        st.append((zc + H * math.sin(math.radians(lat)), math.cos(math.radians(lat))))
    st.sort()
    return st, zc + H, zc - H, zc


def build(coll):
    coef, cx, cy = plan_outline()
    ox, oy = (cx - 12) * PX, (14 - cy) * PX
    th = np.arange(SEGMENTS) * 2 * math.pi / SEGMENTS
    rplan = fourier_eval(coef, th) * PX
    R = coef[0] * PX
    stations, ztop, zbot, zc = meridian(R)
    mats = [common.palette_material(SPRITE, BODY, NAME, metallic=METALLIC, roughness=ROUGH),
            common.palette_material(SPRITE, SEAM, NAME + "_seam", metallic=METALLIC, roughness=0.45)]
    bm = bmesh.new()
    rings = []
    for z, s in stations:
        rings.append([bm.verts.new((ox + rplan[i] * s * math.cos(a), oy + rplan[i] * s * math.sin(a), z))
                      for i, a in enumerate(th)])
    top = bm.verts.new((ox, oy, ztop))
    bot = bm.verts.new((ox, oy, zbot))
    faces = []
    for (z0, _), (z1, _), r0, r1 in zip(stations, stations[1:], rings, rings[1:]):
        mat = 1 if abs((z0 + z1) / 2 - zc) < 0.2 * PX else 0
        for i in range(SEGMENTS):
            j = (i + 1) % SEGMENTS
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mat
            faces.append(f)
    for i in range(SEGMENTS):
        j = (i + 1) % SEGMENTS
        faces.append(bm.faces.new((rings[-1][i], rings[-1][j], top)))
        faces.append(bm.faces.new((rings[0][j], rings[0][i], bot)))
    for f in faces:
        f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    if hasattr(obj.data, "set_sharp_from_angle"):
        obj.data.set_sharp_from_angle(angle=math.radians(28))
    return obj


# --- Renders --------------------------------------------------------------------------------------

def cam(scene, name, loc, look, ortho=None, lens=60):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    c = bpy.data.objects.new(name, data)
    scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return c


def renders(obj, shell, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    scene.render.resolution_percentage = 100
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    # Top flat on the sprite grid (24 x 28 px, k = 10), alpha mask, shell hidden.
    shell.hide_render = True
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_x, scene.render.resolution_y = 240, 280
    top = cam(scene, "top_flat", (0, 0, 10), (0, 0, 0), ortho=28 * PX)
    top.rotation_euler = (0, 0, 0)
    scene.camera = top
    scene.render.filepath = str(out_dir / "top_flat.png")
    bpy.ops.render.render(write_still=True)
    # Lit views.
    sh.light = "STUDIO"
    sh.show_specular_highlight = True
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_object_outline = True
    scene.render.film_transparent = False
    scene.world.color = (0.05, 0.055, 0.06)
    scene.render.resolution_x = scene.render.resolution_y = 400
    d = 4.0
    views = {
        "top": ((0, 0, d), None),
        "front": ((0, -d, 0.72), None),
        "side": ((d, 0, 0.72), None),
        "rear": ((0, d, 0.72), None),
        "q34": ((d * 0.62, -d * 0.62, d * 0.62), None),
        "game": ((0, -d * 0.55, d * 0.85), None),
        "under": ((d * 0.4, -d * 0.5, -d * 0.6), None),
    }
    for name, (loc, _) in views.items():
        c = cam(scene, name, loc, (0, 0, 0.72), ortho=2.4)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    shell.hide_render = False


def main():
    global SPRITE
    SPRITE = common.load_sprite(ROOT, NAME)
    for o in bpy.data.objects:
        o.hide_render = True
    coll = common.reset_collection(NAME)
    obj = build(coll)
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=2000, smooth=4)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"ball: {len(obj.data.polygons)} faces, {tris} tris; shell {len(shell.data.polygons)} faces")
    common.export_sprite_model(ROOT, [obj, shell], f"enemies/{NAME}", SPRITE["sprites"])
    if "--renders" in sys.argv:
        renders(obj, shell, sys.argv[sys.argv.index("--renders") + 1])


SPRITE = None
if __name__ == "__main__":
    main()
