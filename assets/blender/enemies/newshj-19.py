"""Fireball on the ground, newshj-19 (design A): the fireball on the ground turning on the spot (newshj.shp 19/38/57/76).

A burning mound of fire: nested flame crowns, dark red at the rim through orange and yellow to a
white-hot tip, each crown a ring of pointed tongues that swirl round the centre (it turns on the
spot), each hotter crown rising out of the one around it. Emissive throughout, no hard surface.

Every frame is its own model (the game contract: newshj-19, -f2, -f3, -f4). The plan of each
crown is the sprite's own heat band (palette index >= threshold), traced as a smoothed polar
contour from the frame's mask, so the top view is the sprite's rings; the outer edge goes to the
inner edge of the sprite's dark-red ink (sprite_mask.py inner mask, D74). One mesh per frame: a
polar height field (angles x radial stations), material per band; flat closed underside.

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

# Heat bands from the rim in: (min palette index, crest height units, tongues, tongue amp, emission)
# Band 0 is the whole inner mask. Colour = the frame's median index inside the band's own ring.
BANDS = [
    (0,   0.105, 9, 0.55, 2.0),
    (120, 0.165, 8, 0.50, 2.8),
    (122, 0.225, 7, 0.45, 3.4),
    (124, 0.285, 6, 0.40, 4.2),
    (126, 0.335, 5, 0.30, 5.2),
    (127, 0.400, 0, 0.0, 6.5),
]
NA = 96             # angles round the mound
SWIRL = 0.85         # radians of twist from a band's base to its crest (the turning fire)
MIN_GAP = 0.45       # px between nested contours


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


def interp(rs, a):
    n = len(rs)
    f = (a % (2 * math.pi)) / (2 * math.pi) * n
    i = int(f) % n
    t = f - int(f)
    return rs[i] * (1 - t) + rs[(i + 1) % n] * t


def tongue(a, n, phase):
    if n == 0:
        return 0.0
    c = 0.5 + 0.5 * math.cos(n * (a - phase))
    return c ** 2.2


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
    core = masks[-1]
    ys, xs = np.nonzero(masks[min(len(masks) - 1, 3)])
    cx, cy = xs.mean() + 0.5, ys.mean() + 0.5
    radii = [polar(blur_field(m, SIGMA if k == 0 else 0.42), cx, cy) for k, m in enumerate(masks)]
    for k in range(1, len(radii)):
        radii[k] = np.minimum(radii[k], radii[k - 1] - (0.15 if k == len(radii) - 1 else MIN_GAP))
        radii[k] = np.maximum(radii[k], 0.6)
    colors = [band_color(pix, masks, k) for k in range(len(masks))]
    mats = [common.palette_material(sprite, c, NAME, metallic=0.0, roughness=0.55,
                                    emission_strength=bands[k][4]) for k, c in enumerate(colors)]

    X0 = (cx - w / 2) * PX
    Y0 = (h / 2 - cy) * PX
    bm = bmesh.new()
    nb = len(bands)
    # Radial stations: (band, t in the band 0..1, height function of angle)
    rows = []  # list of (band index, list of verts)
    for i_st in range(nb):
        crest_h, nt, amp = bands[i_st][1], bands[i_st][2], bands[i_st][3]
        prev_valley = 0.0 if i_st == 0 else bands[i_st - 1][1] * 0.80
        phase = i_st * 0.9
        last = i_st == nb - 1
        if last:
            stations = [(0.0, "base"), (0.18, "wall"), (0.45, "mid"), (0.75, "upper"), (1.0, "tip")]
        else:
            stations = [(0.0, "base"), (0.12, "wall"), (0.38, "shoulder"), (0.62, "crest"), (1.0, "valley")]
        for t, kind in stations:
            if i_st > 0 and t == 0.0:
                continue  # shared with the previous band's valley ring
            ring = []
            for j in range(NA):
                th = 2 * math.pi * j / NA
                a = th + SWIRL * t + i_st * 0.25
                ro = interp(radii[i_st], a)
                ri = 0.0 if last else interp(radii[i_st + 1], a)
                r = ro - t * (ro - ri)
                tg = tongue(a, nt, phase)
                crest = crest_h * (0.78 + amp * tg)
                if kind == "base":
                    z = prev_valley
                elif kind == "wall":
                    z = prev_valley + (crest - prev_valley) * (0.55 if i_st == 0 else 0.6)
                elif kind == "shoulder":
                    z = prev_valley + (crest - prev_valley) * 0.9
                elif kind == "crest":
                    z = crest
                elif kind == "valley":
                    z = crest_h * 0.80
                elif kind == "mid":
                    z = prev_valley + (crest_h - prev_valley) * 0.55
                elif kind == "upper":
                    z = prev_valley + (crest_h - prev_valley) * 0.85
                else:
                    z = crest_h
                if kind == "tip":
                    ring = [bm.verts.new((X0, Y0, crest_h))]
                    break
                x = X0 + r * PX * math.cos(a)
                y = Y0 + r * PX * math.sin(a)
                ring.append(bm.verts.new((x, y, z)))
            rows.append((i_st, ring))
    # The outer foot: a short rounded skirt down to the ground just inside the edge, so the wall is
    # not a knife edge and the mound sits on the ground.
    foot = rows[0][1]
    under = [bm.verts.new((v.co.x - (v.co.x - X0) * 0.04, v.co.y - (v.co.y - Y0) * 0.04, -0.012)) for v in foot]
    for j in range(NA):
        k = (j + 1) % NA
        f = bm.faces.new((under[j], under[k], foot[k], foot[j]))
        f.material_index = 0
    centre = bm.verts.new((X0, Y0, -0.012))
    for j in range(NA):
        k = (j + 1) % NA
        f = bm.faces.new((centre, under[k], under[j]))
        f.material_index = 0
    for (b0, r0), (b1, r1) in zip(rows, rows[1:]):
        for j in range(NA):
            k = (j + 1) % NA
            if len(r1) == 1:
                f = bm.faces.new((r0[j], r0[k], r1[0]))
            else:
                f = bm.faces.new((r0[j], r0[k], r1[k], r1[j]))
            f.material_index = b1
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
          f"triangles {sum(len(p.vertices) - 2 for p in mesh.polygons)}")
    return obj


def main():
    sprite = common.load_sprite(WT, NAME)
    for k, fidx in enumerate([19, 38, 57, 76]):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        coll = common.reset_collection(name)
        obj = build(sprite, fidx, name, coll)
        shell = common.outline_shell(obj, coll, voxel=0.01, faces=2500)
        sprites = [dict(s, frames=[fidx]) for s in sprite["sprites"]]
        common.export_sprite_model(WT, [obj, shell], f"enemies/{name}", sprites)


if __name__ == "__main__":
    main()
