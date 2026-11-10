"""Fireball bolt, newshj-19: a launched fireball spinning end over end (newshj.shp 19/38/57/76).

Object: a projectile, not ground fire (D120 lesson). Its enemy types (752/755/762/767/839) are only
ever launched (by 754/756/763/769 in episode 2, by newsha-91 in 1.13 SOH JIN) and fly straight at
3-4 px/tick; the four frames are one oval blob drawn at four angles (a spinning bolt).

So the model is a free-floating glowing oval: a closed, round-all-over ellipsoid of fire with no
ground skirt. Its plan is the sprite's heat bands (palette index >= threshold), each traced as a
smoothed polar contour of the frame's mask, so from above it shows the sprite's rings, dark red
rim through orange and yellow to the white-hot core; the outer edge is the inner edge of the
sprite's dark-red ink (sprite_mask.py inner mask, D74). The top is a dome over that plan (the hot
core is the crest, the cooler bands wrap the flanks), the underside a shallower plain dome in the
rim colour (round from the side at the tilted camera, no detail). Every face emits its palette
colour (strength 1 on a metallic surface, so the game shows the palette bands, not a pale wash). Each frame is its own model (newshj-19, -f2, -f3, -f4), the
oval turned as the sprite turns it.

    blender -b --factory-startup -P assets/blender/enemies/newshj-19.py
exports public/models/enemies/newshj-19.glb and -f2/-f3/-f4 plus their spriteModels entries.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask  # noqa: E402

NAME = "newshj-19"
PX = 1 / 12
UP = 4          # supersampling of the mask for the contour
SIGMA = 0.50    # blur in sprite px: rounds the pixel corners, keeps straight runs on the pixel edge

# Heat bands from the rim in: (min palette index, emission strength). Band 0 is the whole inner
# mask. Colour = the frame's median index inside the band's own ring.
# In the game the emissive colour is the live palette colour times max(1, strength) (modelFrames.ts
# copies the colour over the exported emissive, and only a strength > 1 survives export as
# KHR_materials_emissive_strength), added to the lit colour, then Neutral tone mapping. At 2-6.5 the
# yellow and orange bands (121-125) washed to cream and pink; at 1 with a metallic surface (no
# diffuse term on top of the glow) each band shows its own palette colour, sheen only from the
# lights. Only the white-hot core (127) goes over.
BANDS = [
    (0,   1.0),
    (120, 1.0),
    (122, 1.0),
    (124, 1.0),
    (126, 1.0),
    (127, 1.3),
]
METALLIC = 1.0
ROUGHNESS = 0.6
CREST_CUT = 0.03     # how far below the crest (and above the bottom pole) the outline shell is cut flat
NA = 96             # angles round the oval
MIN_GAP = 0.45      # px between nested contours
TOP = 0.95          # dome height over the equator, times the oval's half width
BOTTOM = 0.80       # underside depth below the equator, times the oval's half width
ANG_SMOOTH = 4.0    # degrees of angular smoothing on every band contour
PROFILE = 0.5       # dome exponent on (1 - q^2): 0.5 is a true ellipse section, round at the ends seen from the side (0.65 gave a lens)


def frame_masks(sprite, fidx):
    fr = next(f for f in sprite["frames"] if f["index"] == fidx)
    pix = np.array(fr["pixels"])
    h, w = pix.shape
    idx, colors = sprite_mask.load(NAME, fidx)
    partners = sprite_mask.pulse_partners(idx, sprite_mask.load_frames(NAME))
    inner = np.array(sprite_mask.masks(idx, colors, partners)["inner"])
    masks = []
    for k, (lo, *_ ) in enumerate(BANDS):
        m = inner.copy() if k == 0 else (inner & (pix >= lo))
        masks.append(m)
    return pix, masks, w, h


def blur_field(mask, sigma=None):
    m = np.kron(mask.astype(float), np.ones((UP, UP)))
    m = np.pad(m, 3 * UP)
    s = (sigma or SIGMA) * UP
    r = int(math.ceil(3 * s))
    x = np.arange(-r, r + 1)
    g = np.exp(-x * x / (2 * s * s))
    g /= g.sum()
    m = np.apply_along_axis(lambda v: np.convolve(v, g, mode="same"), 0, m)
    m = np.apply_along_axis(lambda v: np.convolve(v, g, mode="same"), 1, m)
    return m


def sample(field, x, y):
    """field value at sprite-px coordinates (x right, y down, pixel edges at integers)."""
    fx = (x + 3) * UP - 0.5
    fy = (y + 3) * UP - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    H, W = field.shape
    if x0 < 0 or y0 < 0 or x0 + 1 >= W or y0 + 1 >= H:
        return 0.0
    a = field[y0, x0] * (1 - tx) + field[y0, x0 + 1] * tx
    b = field[y0 + 1, x0] * (1 - tx) + field[y0 + 1, x0 + 1] * tx
    return a * (1 - ty) + b * ty


def polar(field, cx, cy, n=720):
    rs = np.zeros(n)
    for i in range(n):
        a = 2 * math.pi * i / n
        dx, dy = math.cos(a), -math.sin(a)  # angle counter-clockwise seen from above (y down in px)
        r = 0.0
        while r < 12 and sample(field, cx + dx * r, cy + dy * r) >= 0.5:
            r += 0.01
        rs[i] = r
    return rs


def smooth_polar(rs, deg=ANG_SMOOTH):
    """Circular Gaussian over angle: irons the pixel staircase out of a contour, so the oval's
    flanks are one smooth round surface instead of a row of creases seen from the side."""
    n = len(rs)
    s = deg / 360 * n
    r = int(math.ceil(3 * s))
    x = np.arange(-r, r + 1)
    g = np.exp(-x * x / (2 * s * s))
    g /= g.sum()
    ext = np.concatenate([rs[-r:], rs, rs[:r]])
    return np.convolve(ext, g, mode="same")[r:r + n]


def interp(rs, a):
    n = len(rs)
    f = (a % (2 * math.pi)) / (2 * math.pi) * n
    i = int(f) % n
    t = f - int(f)
    return rs[i] * (1 - t) + rs[(i + 1) % n] * t


def band_color(pix, masks, k):
    ring = masks[k] & ~(masks[k + 1] if k + 1 < len(masks) else np.zeros_like(masks[k]))
    vals = pix[ring & (pix >= 0)]
    if len(vals) == 0:
        vals = pix[masks[k] & (pix >= 0)]
    return int(np.median(vals)) if len(vals) % 2 else int(sorted(vals)[len(vals) // 2])


def build(sprite, fidx, name, coll):
    pix, masks, w, h = frame_masks(sprite, fidx)
    # The bands that exist in this frame (a frame may lack the very hottest index).
    present = [k for k, m in enumerate(masks) if m.sum() >= 1]
    masks = [masks[k] for k in present]
    bands = [BANDS[k] for k in present]
    ys, xs = np.nonzero(masks[min(len(masks) - 1, 3)])
    cx, cy = xs.mean() + 0.5, ys.mean() + 0.5
    radii = [smooth_polar(polar(blur_field(m, SIGMA if k == 0 else 0.42), cx, cy))
             for k, m in enumerate(masks)]
    for k in range(1, len(radii)):
        radii[k] = np.minimum(radii[k], radii[k - 1] - (0.15 if k == len(radii) - 1 else MIN_GAP))
        radii[k] = np.maximum(radii[k], 0.6)
    colors = [band_color(pix, masks, k) for k in range(len(masks))]
    mats = [common.palette_material(sprite, c, NAME, metallic=METALLIC, roughness=ROUGHNESS,
                                    emission_strength=bands[k][1]) for k, c in enumerate(colors)]

    X0 = (cx - w / 2) * PX
    Y0 = (h / 2 - cy) * PX
    half = float(np.percentile(radii[0], 5))        # half the oval's short axis, px
    htop = TOP * half * PX
    hbot = BOTTOM * half * PX
    zeq = hbot                                       # equator height: the underside rests on z = 0
    nb = len(bands)

    def dome(r, ro):
        q = min(1.0, r / ro) if ro > 1e-6 else 1.0
        return zeq + htop * max(0.0, 1.0 - q * q) ** PROFILE

    bm = bmesh.new()
    # Top: rings from the equator (band 0's contour) in to the core; each ring's radius follows its
    # band's contour, the height the dome over the outer contour at that angle.
    rows = []  # (band of the faces inside this ring, ring verts)
    for k in range(nb):
        last = k == nb - 1
        ts = [0.0, 0.03, 0.09, 0.18, 0.32, 0.5, 0.72] if k == 0 else [0.0, 0.35, 0.7]
        for t in ts:
            ring = []
            for j in range(NA):
                a = 2 * math.pi * j / NA
                ro = interp(radii[0], a)
                rk = interp(radii[k], a)
                rn = 0.0 if last else interp(radii[k + 1], a)
                r = rk - t * (rk - rn)
                ring.append(bm.verts.new((X0 + r * PX * math.cos(a), Y0 + r * PX * math.sin(a), dome(r, ro))))
            rows.append((k, ring))
    tip = bm.verts.new((X0, Y0, zeq + htop))
    for i, (k, ring) in enumerate(rows):
        nxt = rows[i + 1][1] if i + 1 < len(rows) else None
        band = rows[i + 1][0] if i + 1 < len(rows) else k
        for j in range(NA):
            jj = (j + 1) % NA
            f = bm.faces.new((ring[j], ring[jj], nxt[jj], nxt[j]) if nxt else (ring[j], ring[jj], tip))
            f.material_index = band
    # Underside: the top's rings mirrored below the equator at the shallower depth, so the ball
    # glows the same from below and a side view shows hot bands above and below the dark-red waist
    # (a glowing ball, not a cooled lump); no detail of its own.
    equator = rows[0][1]
    scale = hbot / htop
    low = [(k, [bm.verts.new((v.co.x, v.co.y, zeq - (v.co.z - zeq) * scale)) for v in ring]) for k, ring in rows[1:]]
    pole = bm.verts.new((X0, Y0, 0.0))
    seq = [(0, equator)] + low
    for i, (k, ring) in enumerate(seq):
        nxt = seq[i + 1][1] if i + 1 < len(seq) else None
        band = seq[i + 1][0] if i + 1 < len(seq) else k
        for j in range(NA):
            jj = (j + 1) % NA
            f = bm.faces.new((nxt[j], nxt[jj], ring[jj], ring[j]) if nxt else (pole, ring[jj], ring[j]))
            f.material_index = band
    for f in bm.faces:
        f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    print(f"frame {fidx}: bands {[b[0] for b in bands]} colours {colors} centre ({cx:.2f},{cy:.2f}) "
          f"half {half:.2f}px top {htop:.3f} bottom {hbot:.3f} "
          f"triangles {sum(len(p.vertices) - 2 for p in mesh.polygons)}")
    return obj


def inset_shell(obj, shell, depth=0.006):
    """Make the outline shell (D90) the model's own surface moved `depth` inward along its vertex
    normals. The voxel-remeshed, decimated shell from common.outline_shell has its own tessellation;
    on this smooth thin oval its facets cross the model's here and there however far its vertices
    are sunk, and its back faces drew as dark dots on the bright face (f2, f4). An offset copy of
    the model's own mesh is parallel to it everywhere, so it stays under the surface; the shell keeps
    its material and its tyrian_outline flag."""
    me = obj.data.copy()
    me.materials.clear()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.normal_update()
    for v in bm.verts:
        v.co = v.co - v.normal * depth
    # Cut the crest and the pole flat a little lower: a plateau faces straight up (no back faces),
    # where the pole's fan of thin faces, pushed out along their normals by the inverted hull,
    # showed as a dark dot in the white core. Never near the silhouette.
    zs = [v.co.z for v in bm.verts]
    top, bot = max(zs) - CREST_CUT, min(zs) + CREST_CUT
    for v in bm.verts:
        v.co.z = min(top, max(bot, v.co.z))
    for f in bm.faces:
        f.material_index = 0
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    for m in shell.data.materials:
        me.materials.append(m)
    old = shell.data
    shell.data = me
    shell.matrix_world = obj.matrix_world.copy()
    bpy.data.meshes.remove(old)
    print(f"{shell.name}: model mesh inset {depth}, {len(me.polygons)} faces")


def main():
    sprite = common.load_sprite(WT, NAME)
    for k, fidx in enumerate([19, 38, 57, 76]):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        coll = common.reset_collection(name)
        obj = build(sprite, fidx, name, coll)
        shell = common.outline_shell(obj, coll, voxel=0.02, faces=500)
        inset_shell(obj, shell)
        sprites = [dict(s, frames=[fidx]) for s in sprite["sprites"]]
        common.export_sprite_model(WT, [obj, shell], f"enemies/{name}", sprites)


if __name__ == "__main__":
    main()
