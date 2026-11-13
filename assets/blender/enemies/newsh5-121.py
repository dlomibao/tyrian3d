"""newsh5-121, design A: the red curled pod of episode 4 (newsh5.shp frames 121, 123, 125; three
models newsh5-121, -f2, -f3, one per frame), D65 standard, faired glossy shell.

What it is: a coiled shell pod, like a small ammonite lying on its side, that sits on the ground
and turns (frames 121 -> 123 -> 125: the coil swings from a wide, tilted oval to a tall narrow
one). Read from the sprite:
  * the inner whorl: the big smooth dome on the left, its top-left the sprite's hot spot (the
    120-124 run is the sheen of a glossy shell under an upper-left light: material, not paint);
  * the aperture: the dark crease (113/112) that runs down from the top of the dome, bends at the
    bottom and hooks left into a dark pocket, the pod's mouth (it launches spores, type 791);
  * the whorls: two broad bands curling round the right side and the bottom (the lighter 116/117
    bands), stepped onto each other at a dark seam (the 113 line at columns 15-17);
  * the stalk: a short stub where the pod hangs at the top of the frame (rows 1-3).
The outer ring of 112/1 is the sprite's ink (tools/sprite_mask.py: 100 % ink), so the shell's rim
follows the INNER mask and the game's own outline lands on the ink.

Colours (trimmed median per region): shell 115, aperture 113, whorl seam floors 114.

Build: per frame a closed shell over a star-shaped footprint (the inner mask, blurred and traced
at 128 angles from the apex), a full dome profile with a vertical tangent at the ground, every
feature an offset along the profile's normal so the seams wrap down the sides. Underside: a flat
floor. Outline shell from the sealed mesh (D51, islands="outer", D189).

Run: blender --background --python assets/blender/enemies/newsh5-121.py
Exports newsh5-121, -f2, -f3 (public/models/enemies + spriteModels entries).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # assets/blender
import common  # noqa: E402

WT = common.repo_root(__file__)
sys.path.insert(0, str(WT / "tools"))
import sprite_mask as SM  # noqa: E402

NAME = "newsh5-121"
PX = 1 / 12
W, H = 24, 28

HEIGHT = 11.0  # px, the coil's crown
SEG = 160  # around the rim
RINGS = 44  # rim to apex

# Per frame, sprite pixel-centre coordinates (column, row).
FRAMES = {
    121: dict(
        apex=(9.6, 10.0),
        crease=[(11.2, 6.2), (12.2, 7.4), (12.7, 9.0), (12.5, 10.6), (11.6, 11.8), (10.2, 12.4), (8.6, 12.4), (7.4, 12.0)],
        mouth=(9.4, 12.5),
        fold1=[(14.0, 5.6), (14.6, 7.5), (14.9, 9.5), (14.7, 11.8), (13.7, 13.6), (12.0, 15.2), (9.6, 16.5), (6.5, 17.2), (4.6, 16.6)],
        seam=[(16.4, 5.6), (17.1, 7.6), (17.3, 10.0), (17.0, 13.3), (16.0, 15.3), (14.5, 17.0), (12.4, 18.4), (9.8, 19.3), (7.0, 19.6)],
        fold2=[(18.5, 8.6), (18.9, 11.0), (18.4, 13.8), (17.2, 16.0), (15.4, 17.9), (13.0, 19.4)],
        stem=(12.0, 3.4),
    ),
    123: dict(
        apex=(9.6, 10.2),
        crease=[(10.9, 5.4), (11.8, 6.8), (12.2, 8.8), (12.1, 10.9), (11.4, 12.3), (10.1, 13.2), (8.6, 13.3), (7.6, 12.9)],
        mouth=(9.6, 13.3),
        fold1=[(13.6, 4.8), (14.2, 7.2), (14.4, 9.8), (14.2, 12.6), (13.4, 14.6), (11.8, 16.4), (9.4, 17.6), (6.6, 17.6), (5.0, 16.8)],
        seam=[(16.3, 5.8), (16.4, 7.8), (16.4, 10.6), (16.2, 14.0), (15.3, 16.0), (13.8, 17.8), (12.0, 19.3), (9.5, 20.3), (7.2, 20.4)],
        fold2=[(17.6, 9.0), (17.8, 11.6), (17.5, 14.2), (16.6, 16.4), (15.0, 18.3), (12.8, 20.0)],
        stem=(11.8, 2.4),
    ),
    125: dict(
        apex=(9.4, 9.8),
        crease=[(10.8, 4.4), (11.2, 6.4), (11.4, 8.6), (11.4, 10.4), (10.9, 11.6), (9.8, 12.2), (8.4, 12.0), (7.6, 11.4)],
        mouth=(9.5, 12.4),
        fold1=[(13.0, 3.8), (13.4, 6.4), (13.6, 9.4), (13.6, 12.6), (13.0, 15.2), (11.8, 17.2), (9.8, 18.6), (7.4, 18.8), (5.6, 18.0)],
        seam=[(15.0, 4.6), (15.2, 7.0), (15.3, 10.5), (15.2, 14.0), (14.5, 16.3), (13.3, 18.2), (11.5, 19.9), (9.2, 21.0), (7.2, 21.0)],
        fold2=[(16.4, 8.0), (16.6, 11.2), (16.4, 14.4), (15.6, 16.8), (14.2, 18.8), (12.2, 20.6)],
        stem=(11.4, 1.6),
    ),
}


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def bx(c):
    """Sprite column (edge coordinate) to Blender X."""
    return (c - W / 2) * PX


def by(r):
    return (H / 2 - r) * PX


# --- footprint ------------------------------------------------------------------------------------

def footprint(px, cols, apex, k=8, sigma=0.6, bias=0.1):
    """Distances (px) from the apex (edge coords) to the rim of the blurred inner mask at SEG angles
    (Blender angle convention: 0 = +X, CCW with sprite up = +Y)."""
    m = np.array(SM.masks(px, cols)["inner"], float)
    big = np.kron(m, np.ones((k, k)))
    s = sigma * k
    rad = int(3 * s) + 1
    g = np.exp(-0.5 * (np.arange(-rad, rad + 1) / s) ** 2)
    g /= g.sum()
    pad = np.pad(big, rad)
    blur = np.apply_along_axis(lambda v: np.convolve(v, g, "valid"), 1, pad)
    blur = np.apply_along_axis(lambda v: np.convolve(v, g, "valid"), 0, blur)
    hh, ww = blur.shape
    ax, ay = apex
    out = []
    for i in range(SEG):
        a = 2 * math.pi * i / SEG
        dx, dy = math.cos(a), -math.sin(a)
        d, last = 0.0, 0.0
        while d < 20:
            x, y = (ax + dx * d) * k, (ay + dy * d) * k
            xi, yi = int(x), int(y)
            if 0 <= xi < ww and 0 <= yi < hh and blur[yi, xi] >= 0.5:
                last = d
            d += 1 / k / 2
        out.append(last + bias)
    out = np.array(out)
    w = np.exp(-0.5 * (np.arange(-6, 7) / 2.2) ** 2)
    w /= w.sum()
    return sum(wi * np.roll(out, j - 6) for j, wi in enumerate(w))


# --- feature fields -------------------------------------------------------------------------------

def catmull(pts, step=0.2):
    p = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = (np.array(q, float) for q in p[i - 1:i + 3])
        n = max(2, int(np.linalg.norm(p2 - p1) / step))
        for j in range(n):
            t = j / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(np.array(p[-2], float))
    return np.array(out)


def path_dist(P, curve):
    """For points P (N,2) the distance to the curve (polyline, M,2) and the arc fraction there."""
    seg = np.linalg.norm(np.diff(curve, axis=0), axis=1)
    arc = np.concatenate([[0], np.cumsum(seg)])
    best = np.full(len(P), 1e9)
    frac = np.zeros(len(P))
    for i in range(len(curve) - 1):
        a, b = curve[i], curve[i + 1]
        e = b - a
        L2 = max(e @ e, 1e-9)
        t = np.clip(((P - a) @ e) / L2, 0, 1)
        q = a + t[:, None] * e
        d = np.linalg.norm(P - q, axis=1)
        upd = d < best
        best[upd] = d[upd]
        frac[upd] = (arc[i] + t[upd] * seg[i])
    return best, frac, arc[-1]


def taper(s, total, a=1.6, b=1.6):
    """0 at the curve's ends, 1 inside (smooth), `a`/`b` px long ramps."""
    u = np.clip(s / a, 0, 1)
    v = np.clip((total - s) / b, 0, 1)
    sm = lambda x: x * x * (3 - 2 * x)  # noqa: E731
    return sm(u) * sm(v)


def groove(d, hw):
    x = np.clip(d / hw, 0, 1)
    return (1 - x * x) ** 2


def bump(d, hw):
    x = np.clip(d / hw, 0, 1)
    return np.cos(x * math.pi / 2) ** 2


def offsets(P, F):
    """Normal offset (px, + out) at points P (sprite px coords) and the material tags."""
    off = np.zeros(len(P))
    tag = np.zeros(len(P), int)  # 0 shell, 1 aperture, 2 seam floor
    # Aperture: a U channel 1.15 px half-wide, 1.4 px deep, deepening into the mouth pocket.
    d, s, T = path_dist(P, catmull(F["crease"]))
    tp = taper(s, T, 1.4, 0.8)
    g = groove(d, 1.45) * tp
    mouth = np.linalg.norm(P - np.array(F["mouth"]), axis=1)
    pocket = groove(mouth, 2.1)
    cre = np.maximum(1.15 * g, 1.6 * pocket)
    off -= cre
    tag[(g > 0.42) | (pocket > 0.45)] = 1
    # Whorl 1: a broad rolled band outside the aperture, its crest 0.7 px proud.
    d, s, T = path_dist(P, catmull(F["fold1"]))
    off += 0.7 * bump(d, 1.7) * taper(s, T, 1.5, 2.5)
    # The seam where whorl 1 laps onto whorl 2: a narrow V, 0.8 px deep.
    d, s, T = path_dist(P, catmull(F["seam"]))
    g2 = groove(d, 0.95) * taper(s, T, 1.2, 2.5)
    off -= 0.8 * g2
    tag[(g2 > 0.55) & (tag == 0)] = 2
    # Whorl 2: the outer rolled band, 0.55 px proud.
    d, s, T = path_dist(P, catmull(F["fold2"]))
    off += 0.55 * bump(d, 1.5) * taper(s, T, 1.5, 2.5)
    return off, tag


# --- shell ----------------------------------------------------------------------------------------

def profile(rho):
    """Height fraction of the dome at rho (0 apex, 1 rim): vertical at the ground, full crown."""
    return np.clip(1 - rho ** 2.1, 0, 1) ** 0.6


def build(sprite, frame, name, coll):
    F = FRAMES[frame["index"]]
    cols = {int(k): tuple(v) for k, v in sprite["colors"].items()}
    ax, ay = F["apex"][0] + 0.5, F["apex"][1] + 0.5  # edge coords
    rim = footprint(frame["pixels"], cols, (ax, ay))
    # rings: t 0 (rim, on the ground) .. 1 (apex); dense near the rim
    ts = np.linspace(0, 1, RINGS + 1)
    rhos = 1 - ts ** 1.5
    ang = 2 * math.pi * np.arange(SEG) / SEG
    # rho, angle grid -> sprite px coords (pixel centres) and height
    RH, AN = np.meshgrid(rhos[:-1], ang, indexing="ij")
    R = RH * rim[None, :]
    sx = ax + R * np.cos(AN)
    sy = ay - R * np.sin(AN)
    z = HEIGHT * profile(RH)
    # stalk: a short rounded stub at the top of the frame
    sd = np.hypot(sx - (F["stem"][0] + 0.5), sy - (F["stem"][1] + 0.5))
    z = z + 2.2 * np.clip(1 - (sd / 2.0) ** 2, 0, 1) ** 1.5 * np.clip(RH * 1.25 - 0.2, 0, 1)
    # profile normals in (r, z): numerical along rho
    dz = np.gradient(z, axis=0)
    dr = np.gradient(R, axis=0)
    nlen = np.hypot(dz, dr) + 1e-9
    nr, nz = dz / nlen, -dr / nlen  # rows go rim->apex (dr<0): outward normal
    flip = nz < 0
    nr[flip], nz[flip] = -nr[flip], -nz[flip]
    P = np.stack([(sx - 0.5).ravel(), (sy - 0.5).ravel()], 1)  # pixel-centre coords for the paths
    off, tag = offsets(P, F)
    off = off.reshape(R.shape)
    tag = tag.reshape(R.shape)
    # face tags from each face's centre (smoother boundaries than vertex votes)
    cx = (sx + np.roll(sx, -1, 1)) / 2
    cy = (sy + np.roll(sy, -1, 1)) / 2
    cx = (cx[:-1] + cx[1:]) / 2
    cy = (cy[:-1] + cy[1:]) / 2
    _, ftag = offsets(np.stack([(cx - 0.5).ravel(), (cy - 0.5).ravel()], 1), F)
    ftag = majority(ftag.reshape(cx.shape), 3)
    keep = np.clip(z / 1.6, 0, 1)
    keep = keep * keep * (3 - 2 * keep)  # the ground ring stays on the footprint
    off = off * keep
    # radial push only on the steep sides (on the crown a radial push folds the grid over itself)
    steep = np.clip((0.6 - nz) / 0.4, 0, 1)
    R2 = R + off * nr * steep
    z2 = z + off * nz
    X = bx(ax + R2 * np.cos(AN))
    Y = by(ay - R2 * np.sin(AN))
    Z = z2 * PX

    bm = bmesh.new()
    vg = [[bm.verts.new((X[i, k], Y[i, k], Z[i, k])) for k in range(SEG)] for i in range(RINGS)]
    apex = bm.verts.new((bx(ax), by(ay), HEIGHT * PX))
    mats_of = []
    for i in range(RINGS - 1):
        for k in range(SEG):
            j = (k + 1) % SEG
            f = bm.faces.new((vg[i][k], vg[i][j], vg[i + 1][j], vg[i + 1][k]))
            mats_of.append((f, ftag[i, k]))
    for k in range(SEG):
        f = bm.faces.new((vg[-1][k], vg[-1][(k + 1) % SEG], apex))
        mats_of.append((f, 0))
    floor = bm.faces.new(list(reversed(vg[0])))
    mats_of.append((floor, 0))
    for f, m in mats_of:
        f.material_index = m
        f.smooth = True
    floor.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # triangulate the floor n-gon (clean export; it is never seen)
    bmesh.ops.triangulate(bm, faces=[floor])

    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [spec(pal(115, metallic=0.0, roughness=0.28), 0.55),
            spec(pal(113, metallic=0.0, roughness=0.55), 0.3),
            spec(pal(114, metallic=0.0, roughness=0.4), 0.45)]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    bpy.context.view_layer.update()
    sh = common.outline_shell(obj, coll, voxel=0.010, faces=2500, smooth=4, inside=0.003, islands="outer")
    assert len(sh.data.polygons) > 0, f"{sh.name}: empty outline shell"
    return obj, sh


def majority(tag, iters):
    """Mode filter over each face and its 8 grid neighbours (wrapping round the rim): clears the
    saw teeth a threshold leaves where a material boundary crosses the polar grid obliquely."""
    for _ in range(iters):
        votes = []
        for t in range(3):
            m = (tag == t).astype(int)
            acc = np.zeros_like(m)
            for di in (-1, 0, 1):
                sh = np.roll(m, di, 0)
                if di == 1:
                    sh[0] = m[0]
                if di == -1:
                    sh[-1] = m[-1]
                for dk in (-1, 0, 1):
                    acc += np.roll(sh, dk, 1)
            votes.append(acc)
        tag = np.argmax(np.stack(votes), axis=0)
    return tag


def spec(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level
    return mat


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    manifest, models = {}, []
    for n, frame in enumerate(sprite["frames"]):
        name = NAME if n == 0 else f"{NAME}-f{n + 1}"
        coll = common.reset_collection(name)
        obj, sh = build(sprite, frame, name, coll)
        for o in (obj, sh):
            o["design_model"] = name
        obj.data.calc_loop_triangles()
        manifest[name] = {"frames": [frame["index"]], "tris": len(obj.data.loop_triangles),
                          "shell_faces": len(sh.data.polygons)}
        models.append((name, [obj, sh], frame))
    for name, objs, frame in models:
        subset = []
        for s in sprite["sprites"]:
            keep = [f for f in s["frames"] if f == frame["index"]]
            if keep:
                subset.append({**s, "frames": keep})
        common.export_sprite_model(WT, objs, f"enemies/{name}", subset)
    print("MANIFEST", json.dumps(manifest))


if __name__ == "__main__":
    main()
