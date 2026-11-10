"""Dark steel ball (newsha.shp frame 283, level 1.13), final.

A polished gunmetal ball lying on the ground, a little squashed. The sprite draws it lit from the
upper left: a bright highlight at columns 9-11 / rows 9-11 and a pale rim of reflected light along
the lower right edge (rows 15-21, columns 15-20). Both are sheen on the smooth steel, so the model
is only the ball.

Colour pal_5. The median over all opaque pixels and over the inner mask is 4, but that count is
dominated by the lower-right shadow crescent (indices <= 3), which is lighting. With the shadow
indices dropped the median is 5, and the lit upper half (rows <= 15) also has median 5, so pal_5 is
the steel's own colour and the game's lighting supplies the darker side.

Plan outline: the sprite's inner mask (tools/sprite_mask.py, D74: the game's ink outline adds the
border back) traced as a radius per angle round the ball's centre and smoothed to a low-order
Fourier series (orders 0-2, ORDER), so the ball stays round where the sprite is round and still
follows its slightly egg-shaped outline (fuller toward the lower right, where the rim light widens it).
Every horizontal section is that outline scaled by cos(latitude): a squashed ellipsoid on the plan.

Hard-surface detail where the tilted game camera sees it, kept faint so it never reads as paint:
- an equatorial seam: the ball is two forged halves, a shallow V groove with chamfered lips round
  its widest line (pal_4 at the groove floor), which sits at the silhouette from above without
  denting it (the groove is 2.4 px tall on a 7.5 px half height);
- nothing on the upper dome: it is a plain polished ball from above (fix round 1 removed a crown
  seam ring that read as a lid or dish in the game camera).
Underside: the lower half mirrors the upper one down to a small flat contact disc (closed, plain).

    blender --background --python assets/blender/enemies/newsha-283.py [-- --renders DIR]

Exports enemies/newsha-283 (ball + outline shell, D51).
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

NAME = "newsha-283"
PX = 1 / 12

BODY = 5          # sprite body colour (median of the shaded steel)
SEAM = 4          # groove floor, one step darker
METALLIC, ROUGH = 0.75, 0.32   # satin gunmetal, not a mirror

HALF_H_PX = 7.5   # half height in sprite px (a ball ~19 x 17 px across: squashed to ~0.85)
SEGMENTS = 64     # around
ORDER = 2         # Fourier orders of the plan outline


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

def meridian():
    """(z, plan scale) stations from the contact disc to the crown, as fractions: z in units, the
    plan scale multiplies the outline radius. Seams are V grooves with chamfered lips."""
    H = HALF_H_PX * PX
    zc = H  # equator height: the ball rests on its lower pole
    groove_h = 0.9 * PX       # half height of the machined equator belt
    groove_d = 0.2 * PX       # depth of the V seam at its middle
    lip = 0.3 * PX            # half width of the V seam

    def s_of(z):
        t = (z - zc) / H
        return math.sqrt(max(0.0, 1 - t * t))

    st = []
    # Lower half: from a small contact disc (z = 0.25 px) up to the groove.
    for lat in np.linspace(-80, -10, 8):
        z = zc + H * math.sin(math.radians(lat))
        st.append((z, math.cos(math.radians(lat))))
    def g(dz, inset):
        z = zc + dz
        st.append((z, 1.0 - inset))  # a machined belt: full radius between the lips
    # Equator groove (V with lips): radius inset as fraction of the ~9.5 px radius.
    R = 9.3 * PX
    for dz, ins in [(-groove_h, 0.0), (-lip, 0.0), (-lip * 0.4, groove_d * 0.7 / R), (0.0, groove_d / R),
                    (lip * 0.4, groove_d * 0.7 / R), (lip, 0.0), (groove_h, 0.0)]:
        g(dz, ins)
    # Upper half: a plain smooth dome to the crown (no seam up there: from above any ring on the
    # crown reads as a lid or a dish, and the sprite shows only a glint).
    for lat in np.linspace(14, 88, 14):
        z = zc + H * math.sin(math.radians(lat))
        st.append((z, math.cos(math.radians(lat))))
    st.sort()
    return st, zc + H, zc


def build(coll):
    coef, cx, cy = plan_outline()
    ox, oy = (cx - 12) * PX, (14 - cy) * PX
    th = np.arange(SEGMENTS) * 2 * math.pi / SEGMENTS
    rplan = fourier_eval(coef, th) * PX
    stations, ztop, zc = meridian()
    mats = [common.palette_material(SPRITE, BODY, NAME, metallic=METALLIC, roughness=ROUGH),
            common.palette_material(SPRITE, SEAM, NAME + "_seam", metallic=METALLIC, roughness=0.45)]
    bm = bmesh.new()
    rings = []
    for z, s in stations:
        rings.append([bm.verts.new((ox + rplan[i] * s * math.cos(a), oy + rplan[i] * s * math.sin(a), z))
                      for i, a in enumerate(th)])
    top = bm.verts.new((ox, oy, ztop))
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
        f = bm.faces.new((rings[-1][i], rings[-1][j], top))
        faces.append(f)
    bottom = bm.faces.new(list(reversed(rings[0])))  # the flat contact disc
    faces.append(bottom)
    for f in faces:
        f.smooth = True
    bottom.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    # Sharp edges at the seam lips so the grooves read as machined, the rest smooth.
    obj.data.set_sharp_from_angle(angle=math.radians(28)) if hasattr(obj.data, "set_sharp_from_angle") else None
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
        "front": ((0, -d, 0.3), None),
        "side": ((d, 0, 0.3), None),
        "rear": ((0, d, 0.3), None),
        "q34": ((d * 0.62, -d * 0.62, d * 0.62), None),
        "game": ((0, -d * 0.55, d * 0.85), None),
        "under": ((d * 0.4, -d * 0.5, -d * 0.6), None),
    }
    for name, (loc, _) in views.items():
        c = cam(scene, name, loc, (0, 0, 0.3), ortho=2.4)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    shell.hide_render = False


def main():
    global SPRITE
    SPRITE = common.load_sprite(ROOT, NAME)
    for o in bpy.data.objects:  # the factory scene's cube, camera and light stay out of renders
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
