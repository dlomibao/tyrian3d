"""The falling fireball (assembly-newsh5-203 = newsh5-203 tail over newsh5-241 head),
episode 4 (LAVA EXIT 4.9, BRAINIAC, ICESECRET 4.20).

WHAT IT IS. A ball of fire dropping down the screen, head first: a round, white-hot head (the
newsh5-241 piece, at the bottom of the screen, leading) trailing a flame that narrows to a thin
dark red tip (newsh5-203, 28 px above it, same column, rigid). Seen from above, its colours run
from a dark red rim through orange and yellow to a near-white core; the tail is orange with a red
flank, a separate tongue licking off its left side (rows 13-21) and hot yellow streaks where it
joins the head.

THE MODEL. One faired body of fire lofted down the 24 x 54 px column in sections every 0.6 px: a
teardrop, round in section (a full semi-ellipse crown, a flatter underside), its plan edges the
sprite's own inner mask row by row (D74; the dark 112-114 ink ring is left to the game's outline),
smoothed lightly and interpolated with pchip, so the flame edge is a curve, not pixel steps. The
crown height follows the run's half width, so the head is a ball and the tail a thinning tongue;
the bottom (the head's leading face) rounds off over R_END px. The flame's envelopes are nested in
the surface: every face takes the palette index of the sprite under its centre (blurred a little,
so the bands have smooth contours), and a soft relief (a band-pass of the sprite's brightness)
lifts the hotter envelopes over the cooler ones: the white core swells out of the yellow, the
yellow streaks and tongues out of the orange, and the darker seams between tongues sink, so from
the side it is layered fire, not a painted egg. Everything glows (metallic 1, rough; D126/D173),
the white core fully, the red flanks partly so the form still shades. The tongue that leaves the
tail's left flank (sprite rows 13-21, col 8) is its own small faired lick, rising out of the
flank, its tip standing free where the sprite shows a 1 px gap.

FRAMES. Each piece's two frames are mirror images about pixel column 11 (masks exactly, colours
nearly), so frame 2 (205, 243) is the mirror image of frame 1 (203, 241), frame-tagged
(common.frame_part). The outline shell (D51) is made from the whole closed body (islands="outer",
D189) and cut open at the piece seam, so no ink crosses the fireball where the pieces meet.

    blender -b --factory-startup -P assets/blender/enemies/assembly-newsh5-203.py [-- --measure DIR]

Exports public/models/enemies/newsh5-203.glb and newsh5-241.glb (+ src/render/spriteModels json),
each piece with both frames and its outline shell. --measure DIR (review only) writes top-view masks
and measure.json (sprite_mask's rule IoU per piece frame) to DIR.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector


def _find_repo():
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("repo root not found")


ROOT = _find_repo()
sys.path[:0] = [str(ROOT / "assets" / "blender"), str(ROOT / "tools")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "assembly-newsh5-203"
PIECES = ["newsh5-203", "newsh5-241"]
FRAMES = {"newsh5-203": (203, 205), "newsh5-241": (241, 243)}
LAYOUT = [("newsh5-203", 0, -14), ("newsh5-241", 0, 14)]  # screen px from the assembly centre
W, H = 24, 56  # the assembly grid: tail rows 0-27, head rows 28-55 (head rows 54-55 empty)
U = 1 / 12
MIRROR_X = 23.0  # x' = MIRROR_X - x (px edge coords): mirror about the centre of column 11

ASPECT = 0.82  # crown height per px of half width
HMAX = 7.2  # px
UNDER = 0.76  # underside depth as a share of the crown height
R_END = 7.5  # the head's leading face rounds off over this many px
R_TIP = 2.0  # the tail tip
STEP_Y = 0.7
N_TOP = 36
N_BOT = 10
EDGE_SMOOTH = (1, 5, 1)
RELIEF = 0.42  # px per palette step of band-passed brightness
RELIEF_MAX = 1.1
MIN_PAL = 115  # the darker 112-114 are the ink ring (the game's outline), not the flame's colour
GLOW = {127: 1.0, 126: 1.0, 125: 1.0, 124: 1.0, 123: 0.97, 122: 0.94, 121: 0.9, 120: 0.86,
        119: 0.82, 118: 0.78, 117: 0.74, 116: 0.7, 115: 0.66}
# The tongue off the tail's left flank: (row, centre col edge-coords, half width px, crown px).
TONGUE = [(12.9, 8.5, 0.0, 0.0), (13.4, 8.5, 0.48, 0.55), (14.5, 8.55, 0.55, 0.9),
          (16.0, 8.45, 0.6, 1.4), (17.5, 8.45, 0.6, 1.9), (19.0, 8.5, 0.55, 2.3),
          (20.5, 8.7, 0.45, 2.6), (22.0, 9.2, 0.2, 2.6), (22.6, 9.5, 0.0, 2.4)]


# --- the sprite ----------------------------------------------------------------------------------

def sprite_grids():
    """(index grid H x W of the first frames, the rule mask inner|free H x W, colours)."""
    import sprite_mask as SM
    idx = np.full((H, W), -1, dtype=int)
    mask = np.zeros((H, W), dtype=bool)
    colors = {}
    for name, r0 in (("newsh5-203", 0), ("newsh5-241", 28)):
        data = common.load_sprite(ROOT, name)
        colors.update(data["colors"])
        fr = next(f for f in data["frames"] if f["index"] == FRAMES[name][0])
        px = np.array(fr["pixels"], dtype=int)
        px[(px < 112) | (px > 127)] = -1  # stray pixels (254, 80) off the fireball
        idx[r0:r0 + 28] = px
        rows, cols = SM.load(name, FRAMES[name][0])
        m = SM.masks(rows, cols)
        mask[r0:r0 + 28] = np.array(m["inner"], dtype=bool) | np.array(m["free"], dtype=bool)
    return idx, mask, colors


def blur(a, sigma, sigma_y=None):
    """Gaussian blur (sigma across, sigma_y down the flame; default the same)."""
    def k1(sg):
        r = max(1, int(math.ceil(3 * sg)))
        k = np.exp(-0.5 * (np.arange(-r, r + 1) / sg) ** 2)
        return k / k.sum(), r
    ky, ry = k1(sigma_y or sigma)
    kx, rx = k1(sigma)
    p = np.pad(a, ((ry, ry), (rx, rx)), mode="edge")
    p = np.apply_along_axis(lambda v: np.convolve(v, ky, mode="valid"), 0, p)
    return np.apply_along_axis(lambda v: np.convolve(v, kx, mode="valid"), 1, p)


def filled(grid):
    """The index grid with transparent pixels filled from their nearest opaque neighbours."""
    g = grid.astype(float)
    known = grid >= 0
    g[~known] = 0
    for _ in range(60):
        if known.all():
            break
        acc, cnt = np.zeros_like(g), np.zeros_like(g)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            sh = np.roll(np.roll(g, dr, 0), dc, 1)
            sk = np.roll(np.roll(known, dr, 0), dc, 1)
            if dr == -1:
                sk[-1, :] = False
            if dr == 1:
                sk[0, :] = False
            if dc == -1:
                sk[:, -1] = False
            if dc == 1:
                sk[:, 0] = False
            acc += np.where(sk, sh, 0)
            cnt += sk
        new = (~known) & (cnt > 0)
        g[new] = acc[new] / cnt[new]
        known |= new
    return g


def bilinear(a, x, y):
    h, w = a.shape
    fx = min(max(x - 0.5, 0.0), w - 1.0)
    fy = min(max(y - 0.5, 0.0), h - 1.0)
    x0, y0 = int(fx), int(fy)
    x1, y1 = min(x0 + 1, w - 1), min(y0 + 1, h - 1)
    tx, ty = fx - x0, fy - y0
    return ((a[y0, x0] * (1 - tx) + a[y0, x1] * tx) * (1 - ty)
            + (a[y1, x0] * (1 - tx) + a[y1, x1] * tx) * ty)


def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def edge_curves(mask):
    """Left / right plan edge (px) of the main body as pchip functions of y. On the rows where the
    tongue stands apart (row 13, col 8 with a gap at col 9) the body starts right of the gap."""
    rows = [r for r in range(H) if mask[r].any()]
    xl, xr = {}, {}
    for r in rows:
        on = np.nonzero(mask[r])[0]
        L = float(on[0])
        if r == 13 and not mask[r, 9]:
            L = 10.0
        xl[r], xr[r] = L, float(on[-1] + 1)
    a, b, c = EDGE_SMOOTH

    def soft(e):
        return {r: (a * e.get(r - 1, e[r]) + b * e[r] + c * e.get(r + 1, e[r])) / (a + b + c) for r in rows}
    xl, xr = soft(xl), soft(xr)
    yc = [r + 0.5 for r in rows]
    fl = T.pchip(yc, [xl[r] for r in rows])
    fr = T.pchip(yc, [xr[r] for r in rows])

    def edges(y):
        yy = min(max(y, yc[0]), yc[-1])
        return fl(yy), fr(yy)
    return edges, rows[0], rows[-1] + 1


# --- the body ------------------------------------------------------------------------------------

def to_world(x, y, z):
    return Vector(((x - W / 2) * U, (H / 2 - y) * U, z * U))


def build_body(coll):
    idx, mask, colors = sprite_grids()
    sprite = {"name": NAME, "colors": colors}
    edges, ya, yb = edge_curves(mask)
    fill = filled(idx)
    colour = blur(fill, 0.8)
    rim = blur(fill, 1.6, 3.0)  # the underside's colour: the flank's, smoothed down the flame
    # The tongues and streaks (not the big bands), drawn out down the flame so they read as licks.
    bright = blur(fill, 0.9, 2.0) - blur(fill, 2.8, 4.5)
    core = blur((idx >= 126).astype(float), 1.4)

    used = list(range(MIN_PAL, 128))
    mats, mat_of = [], {}
    for v in used:
        mat_of[v] = len(mats)
        mats.append(common.palette_material(sprite, v, NAME, metallic=1.0, roughness=0.9,
                                            emission_strength=GLOW[v]))

    def pal_at(x, y, under=False):
        v = int(round(bilinear(rim if under else colour, x, y)))
        return mat_of[min(max(v, MIN_PAL), 121 if under else 127)]

    def crown(y, half):
        hgt = min(HMAX, ASPECT * half)
        hgt *= math.sqrt(max(0.0, 1 - (1 - min(1.0, (yb - y) / R_END)) ** 2))
        hgt *= math.sqrt(max(0.0, 1 - (1 - min(1.0, (y - ya) / R_TIP)) ** 2))
        return max(hgt, 0.25)

    ys = [ya + 0.02] + [y for y in T.frange(ya, yb, STEP_Y)][1:-1] + [yb - 0.02]
    us = [-math.cos(math.pi * i / N_TOP) for i in range(N_TOP + 1)]
    ub = [math.cos(math.pi * j / N_BOT) for j in range(1, N_BOT)]
    bm = bmesh.new()
    rings = []
    for y in ys:
        L, R = edges(y)
        cx, half = (L + R) / 2, max((R - L) / 2, 0.3)
        hgt = crown(y, half)
        ring = []
        for u in us:
            x = cx + u * half
            s = math.sqrt(max(0.0, 1 - u * u))
            rel = max(-RELIEF_MAX, min(RELIEF_MAX, RELIEF * bilinear(bright, x, y)))
            rel *= smoothstep(s / 0.5) * (1 - 0.7 * min(1.0, bilinear(core, x, y)))
            rel *= smoothstep((y - ya) / 3) * smoothstep((yb - y) / 4)
            rel *= min(1.0, hgt / 2.5)
            ring.append(bm.verts.new(to_world(x, y, hgt * s + rel)))
        for u in ub:
            x = cx + u * half
            ring.append(bm.verts.new(to_world(x, y, -UNDER * hgt * math.sqrt(max(0.0, 1 - u * u)))))
        rings.append((y, cx, half, ring))
    n = len(rings[0][3])
    for (y0, cx, half, ra), (y1, _, _, rb) in zip(rings, rings[1:]):
        ym = (y0 + y1) / 2
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
            co = (ra[i].co + ra[j].co + rb[i].co + rb[j].co) / 4
            x = co.x / U + W / 2
            under = co.z < -0.05 * U  # the underside: the flank's cooler envelope, not the core again
            if under:
                x = cx + math.copysign(0.85 * half, x - cx)
            f.material_index = pal_at(x, ym, under)
            f.smooth = True
    for k, (y, cx, _, ring) in ((0, rings[0]), (1, rings[-1])):
        cv = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((ring[i], ring[j], cv) if k == 1 else (ring[j], ring[i], cv))
            f.material_index = pal_at(cx, y)
            f.smooth = True
    # The tongue: a small faired lick off the left flank, its root sunk into the body.
    trings = []
    for r, c, w, hz in TONGUE:
        y = r
        if w == 0:
            trings.append([bm.verts.new(to_world(c, y, max(hz * 0.5, 0.2)))])
            continue
        ring = []
        for k in range(12):
            a = 2 * math.pi * (k + 0.5) / 12
            ca, sa = math.cos(a), math.sin(a)
            z = (0.15 + hz * 0.5) + (hz * 0.5 if sa > 0 else hz * 0.35) * sa
            ring.append(bm.verts.new(to_world(c + w * ca, y, z)))
        trings.append(ring)
    for r0, r1, (r, c, _, _) in zip(trings, trings[1:], TONGUE):
        m = max(len(r0), len(r1))
        for k in range(m):
            j = (k + 1) % m
            if len(r0) == 1:
                fv = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                fv = (r0[k], r0[j], r1[0])
            else:
                fv = (r0[k], r0[j], r1[j], r1[k])
            f = bm.faces.new(fv)
            f.material_index = pal_at(8.5, r + 0.5)
            f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    used_i = sorted({f.material_index for f in bm.faces})  # only the materials faces use
    remap = {old: new for new, old in enumerate(used_i)}
    for f in bm.faces:
        f.material_index = remap[f.material_index]
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for i in used_i:
        me.materials.append(mats[i])
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    return obj


def mirrored(obj, name):
    ax = (MIRROR_X / 2 - W / 2) * U
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for v in bm.verts:
        v.co.x = 2 * ax - v.co.x
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in obj.data.materials:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    obj.users_collection[0].objects.link(o)
    for k in ("tyrian_outline",):
        if k in obj:
            o[k] = obj[k]
    return o


def open_cut(obj, cx, cy, name, coll):
    """The part of obj inside piece (cx, cy)'s 24 x 28 box, cuts left open, moved to its centre."""
    x0, y0 = cx / 12, -cy / 12
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    hw, hh = 1.0, 14 / 12
    for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                   ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                               plane_no=no, clear_outer=True)
    bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    o.data.shade_smooth()
    o.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    o["tyrian_outline"] = True
    return o


def build(coll):
    body = build_body(coll)
    shell = common.outline_shell(body, coll, voxel=0.018, faces=3000, smooth=5, inside=0.004,
                                 islands="outer")
    flip = mirrored(body, f"{NAME}-mirror")
    flip_shell = mirrored(shell, f"{NAME}_outline-mirror")
    out = {}
    for src, sh, k in ((body, shell, 0), (flip, flip_shell, 1)):
        parts = common.split_assembly(src, LAYOUT, coll)
        for name, cx, cy in LAYOUT:
            frame = FRAMES[name][k]
            p = parts[name]
            p.name = p.data.name = f"{name}-{frame}"
            s = open_cut(sh, cx, cy, f"{name}-{frame}_outline", coll)
            assert len(s.data.polygons) > 0, f"{s.name} has no mesh"
            common.frame_part(p, [frame])
            common.frame_part(s, [frame])
            out.setdefault(name, []).extend([p, s])
    for o in (body, shell, flip, flip_shell):
        o.hide_render = True
        o.hide_set(True)
    return body, flip, out


# --- measuring (behind --measure) ------------------------------------------------------------------

def top_mask(objs, w_px, h_px, out_png, k=4, flat=False):
    scene = bpy.context.scene
    hidden = {o.name: o.hide_render for o in scene.objects}
    for o in scene.objects:
        o.hide_render = o not in objs
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL" if flat else "SINGLE"
    scene.display.shading.single_color = (1, 1, 1)
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x, scene.render.resolution_y = w_px * k, h_px * k
    scene.render.resolution_percentage = 100
    cd = bpy.data.cameras.new("topcam")
    cd.type = "ORTHO"
    cd.ortho_scale = max(w_px, h_px) / 12
    cam = bpy.data.objects.new("topcam", cd)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 30)
    scene.camera = cam
    scene.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in scene.objects:
        if o.name in hidden:
            o.hide_render = hidden[o.name]


def measure(out, outdir):
    import sprite_mask as SM
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    res = {}
    for name, cx, cy in LAYOUT:
        objs = [o for o in out[name] if not o.get("tyrian_outline")]
        for k, frame in enumerate(FRAMES[name]):
            o = next(o for o in objs if list(o["tyrian_frames"]) == [frame])
            o.location = (0, 0, 0)
            png = outdir / f"top_{name}@{frame}.png"
            top_mask([o], 24, 28, png)
            rows, cols = SM.load(name, frame)
            m = SM.masks(rows, cols)
            res[f"{name}@{frame}"] = SM.measure(m, SM.read_png_mask(str(png)))
            top_mask([o], 24, 28, outdir / f"flat_{name}@{frame}.png", k=8, flat=True)
    (outdir / "measure.json").write_text(json.dumps(res, indent=1))
    for key, r in res.items():
        print(f"MEASURE {key}: rule grid {r['iou_rule_grid']} rule {r['iou_rule']} edge {r['edge_vs_inner_px']:+.2f}")
    return res


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    coll = common.reset_collection(NAME)
    body, flip, out = build(coll)
    for name, cx, cy in LAYOUT:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, out[name], f"enemies/{name}", data["sprites"])
    if "--measure" in argv:
        measure(out, argv[argv.index("--measure") + 1])


if __name__ == "__main__":
    main()
