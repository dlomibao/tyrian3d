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
  * the stalk: a short nub at the top of the frame (rows 1-3), kept low and rounded (a raised stub
    read as a point from the tilted camera, E4 QA).
The outer ring of 112/1 is the sprite's ink (tools/sprite_mask.py: 100 % ink), so the shell's rim
follows the INNER mask and the game's own outline lands on the ink.

Colours (trimmed median per region): shell 115, aperture 113, whorl seam floors 114.

Build: per frame a closed shell over a star-shaped footprint (the inner mask, blurred and traced
at 160 angles from the apex). Its height (polish round, E4 QA: the curl read as pointed from the
tilted camera) is an oval crown fitted to the inner mask, its top on the inner whorl's apex
(crown_field), rolled down to the ground with a vertical tangent near the rim (ROUND): every contour
a smooth oval, so the pod reads as the sprite's rounded curled pod. Every feature is an offset along
the shell's normal so the seams wrap down the sides. Underside: a flat floor. Outline shell from the
sealed mesh (D51, islands="outer", D189).

The glint (E4 QA: the sprite's yellow glint was lost): the shell is one palette index (pal_115);
two generated finish maps on top-view UVs (roughness, and the reflectance through Specular Tint x
Specular IOR Level, D176, as newsh8-102's egg) make it polished with a warm yellow reflectance round
the sprite's hot spot and an orange halo, so the game's room light reflects there as the glint;
elsewhere the reflectance is low and red, so highlights run up the sprite's red ramp (art rule 2:
sheen, not paint; no colour is painted).

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

HEIGHT = 9.0  # px, the coil's crown (11 read as a tall, pointed teardrop from the tilted camera)
SEG = 160  # around the rim
RINGS = 44  # rim to apex
# Rounding (polish round): the crown height is also scaled by a quarter circle of the distance to the
# rim (full height ROUND px in), so the narrow lobe at the top of the frame (the stalk) stays a low,
# rounded nub and the pod reads as the sprite's rounded oval, not a point.
ROUND = 3.0
# The crown's top: this share of the way from the oval's centre to the inner whorl's apex. There the
# shell round the sprite's glint faces up, toward the game's room light, so the glint reads bright.
TOP_SHARE = 1.0
# The glint (art rule 2: sheen, not paint). The sprite's 120-124 run at the upper left of the inner
# whorl is the hot spot of a glossy shell; one palette index everywhere (pal_115), but the shell is
# polished and its reflectance (F0, Specular Tint x Specular IOR Level, D176) warm yellow there, so
# the game's lights reflect as a yellow glint with an orange halo; elsewhere a lower, warm (orange)
# reflectance, so the room light doesn't wash the red pink. Per frame the glint's centre is in GLINT.
SHEEN = {
    "level": 12.5,       # Specular IOR Level: F0 = 0.04 * 2 * level * tint (1.0 at a full tint)
    "rough": 0.34,       # the shell away from the glint
    "rough_min": 0.5,    # at the glint: broad enough that the game's sun, from the south, reaches it
    "rough_r": 1.8,      # Gaussian radius (sprite px) of the glint's finish
    "spec_r": 1.25,      # Gaussian radius of the yellow reflectance
    "glint": (1.0, 0.64, 0.05),   # tint at the glint (the sprite's 123/124: yellow)
    "halo": (0.5, 0.08, 0.0),     # tint at about 1.5 radii (120/121: orange)
    "base": (0.04, 0.001, 0.0),   # the rest of the shell: F0 0.04 red, so the sun's highlights
                                  # run up the sprite's red ramp (117-119), not orange or pink
}

# Per frame, sprite pixel-centre coordinates (column, row).
FRAMES = {
    121: dict(
        apex=(9.6, 10.0),
        crease=[(11.2, 6.2), (12.2, 7.4), (12.7, 9.0), (12.5, 10.6), (11.6, 11.8), (10.2, 12.4), (8.6, 12.4), (7.4, 12.0)],
        mouth=(9.4, 12.5),
        fold1=[(14.0, 5.6), (14.6, 7.5), (14.9, 9.5), (14.7, 11.8), (13.7, 13.6), (12.0, 15.2), (9.6, 16.5), (6.5, 17.2), (4.6, 16.6)],
        seam=[(16.4, 5.6), (17.1, 7.6), (17.3, 10.0), (17.0, 13.3), (16.0, 15.3), (14.5, 17.0), (12.4, 18.4), (9.8, 19.3), (7.0, 19.6)],
        fold2=[(18.5, 8.6), (18.9, 11.0), (18.4, 13.8), (17.2, 16.0), (15.4, 17.9), (13.0, 19.4)],
        glint=(7.9, 11.0),  # top view: the tilted camera lifts it about 3 rows, onto the sprite's (7.9, 8.2)
    ),
    123: dict(
        apex=(9.6, 10.2),
        crease=[(10.9, 5.4), (11.8, 6.8), (12.2, 8.8), (12.1, 10.9), (11.4, 12.3), (10.1, 13.2), (8.6, 13.3), (7.6, 12.9)],
        mouth=(9.6, 13.3),
        fold1=[(13.6, 4.8), (14.2, 7.2), (14.4, 9.8), (14.2, 12.6), (13.4, 14.6), (11.8, 16.4), (9.4, 17.6), (6.6, 17.6), (5.0, 16.8)],
        seam=[(16.3, 5.8), (16.4, 7.8), (16.4, 10.6), (16.2, 14.0), (15.3, 16.0), (13.8, 17.8), (12.0, 19.3), (9.5, 20.3), (7.2, 20.4)],
        fold2=[(17.6, 9.0), (17.8, 11.6), (17.5, 14.2), (16.6, 16.4), (15.0, 18.3), (12.8, 20.0)],
        glint=(7.9, 10.0),
    ),
    125: dict(
        apex=(9.4, 9.8),
        crease=[(10.8, 4.4), (11.2, 6.4), (11.4, 8.6), (11.4, 10.4), (10.9, 11.6), (9.8, 12.2), (8.4, 12.0), (7.6, 11.4)],
        mouth=(9.5, 12.4),
        fold1=[(13.0, 3.8), (13.4, 6.4), (13.6, 9.4), (13.6, 12.6), (13.0, 15.2), (11.8, 17.2), (9.8, 18.6), (7.4, 18.8), (5.6, 18.0)],
        seam=[(15.0, 4.6), (15.2, 7.0), (15.3, 10.5), (15.2, 14.0), (14.5, 16.3), (13.3, 18.2), (11.5, 19.9), (9.2, 21.0), (7.2, 21.0)],
        fold2=[(16.4, 8.0), (16.6, 11.2), (16.4, 14.4), (15.6, 16.8), (14.2, 18.8), (12.2, 20.6)],
        glint=(7.8, 9.1),
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
    tp = taper(s, T, 3.0, 0.8)  # a long fade at the top: a hooked start read as a point
    g = groove(d, 1.45) * tp
    mouth = np.linalg.norm(P - np.array(F["mouth"]), axis=1)
    pocket = groove(mouth, 2.1)
    cre = np.maximum(1.15 * g, 1.6 * pocket)
    off -= cre
    tag[(g > 0.42) | (pocket > 0.45)] = 1
    # Whorl 1: a broad rolled band outside the aperture, its crest 0.7 px proud.
    d, s, T = path_dist(P, catmull(F["fold1"]))
    off += 0.7 * bump(d, 1.7) * taper(s, T, 2.8, 2.5)
    # The seam where whorl 1 laps onto whorl 2: a narrow V, 0.8 px deep.
    d, s, T = path_dist(P, catmull(F["seam"]))
    g2 = groove(d, 0.95) * taper(s, T, 2.6, 2.5)
    off -= 0.8 * g2
    tag[(g2 > 0.55) & (tag == 0)] = 2
    # Whorl 2: the outer rolled band, 0.55 px proud.
    d, s, T = path_dist(P, catmull(F["fold2"]))
    off += 0.55 * bump(d, 1.5) * taper(s, T, 1.5, 2.5)
    return off, tag


# --- shell ----------------------------------------------------------------------------------------

def crown_field(px, cols, top):
    """The crown: an ellipsoid fitted to the inner mask (its moments give the axis and tilt of the oval),
    its top moved toward `top` (the inner whorl's apex, edge coordinates; TOP_SHARE of the way from the
    oval's centre) with each side's half axis stretched to keep the oval's extent,
    so every contour is a smooth oval (the star-shaped polar profile repeated the rim's corners, the
    stalk lobe's among them, up to the crown: a point from the tilted camera). Returns z(sx, sy) in px
    (edge coordinates)."""
    m = np.array(SM.masks(px, cols)["inner"], bool)
    ys, xs = np.nonzero(m)
    pts = np.stack([xs + 0.5, ys + 0.5], 1)
    c = pts.mean(0)
    w, v = np.linalg.eigh(np.cov((pts - c).T))
    eu = v[:, 1]  # the major axis
    ev = np.array([-eu[1], eu[0]])
    corners = np.concatenate([pts + d for d in ((-.5, -.5), (.5, -.5), (-.5, .5), (.5, .5))])
    pu, pv = (corners - c) @ eu, (corners - c) @ ev
    peak = TOP_SHARE * (np.array(top, float) - c)
    tu, tv = peak @ eu, peak @ ev
    axes = (tu - pu.min(), pu.max() - tu, tv - pv.min(), pv.max() - tv)

    def r2(x, y):
        u = (x - c[0]) * eu[0] + (y - c[1]) * eu[1] - tu
        w_ = (x - c[0]) * ev[0] + (y - c[1]) * ev[1] - tv
        au = np.where(u < 0, axes[0], axes[1])
        av = np.where(w_ < 0, axes[2], axes[3])
        return (u / au) ** 2 + (w_ / av) ** 2

    # scale so the whole mask (its pixel corners) just fits: the shell falls to the ground at the rim
    s = math.sqrt(r2(corners[:, 0], corners[:, 1]).max()) / 0.995

    def z(x, y):
        # (1 - r^2)^0.85: a rounded crown that slopes on down its sides (a plain ellipsoid read as a
        # drum: flat top, near-vertical walls)
        return HEIGHT * np.clip(1 - r2(x, y) / s ** 2, 0, 1) ** 0.85
    return z


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
    zf = crown_field(frame["pixels"], cols, (ax, ay))
    z = zf(sx, sy)
    # Rounding: scaled by a quarter circle of the distance to the rim, so the shell rolls down to the
    # ground and the narrow stalk lobe at the top stays a low rounded nub (the old raised stalk stub
    # read as a point; removed).
    rx = ax + rim * np.cos(ang)
    ry = ay - rim * np.sin(ang)
    dist = np.min(np.hypot(sx[..., None] - rx, sy[..., None] - ry), axis=-1)
    q = np.clip(dist / ROUND, 0, 1)
    z = z * np.sqrt(1 - (1 - q) ** 2)  # a rounded roll-off to the ground, no kink
    z[0] = 0.0  # the ground ring stays on the ground
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
    apex = bm.verts.new((bx(ax), by(ay), float(z2[-1].mean()) * PX))
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

    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [finish_material(pal(115, metallic=0.0, roughness=SHEEN["rough"]), name, F["glint"]),
            warm(spec(pal(113, metallic=0.0, roughness=0.55), 0.9)),
            warm(spec(pal(114, metallic=0.0, roughness=0.42), 1.2))]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    # UVs: the top view on the sprite grid (edge coordinates / sprite size), the finish maps' frame.
    uvl = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uvl.data[loop.index].uv = ((co.x / PX + W / 2) / W, (co.y / PX + H / 2) / H)
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


def warm(mat):
    """A warm (orange) reflectance on the seams and the aperture, as on the shell away from the glint."""
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    t = [c / max(SHEEN["base"]) for c in SHEEN["base"]]
    bsdf.inputs["Specular Tint"].default_value = (*t, 1.0)
    return mat


def finish_material(mat, name, glint, res=96):
    """The shell's finish maps (no colour): roughness (G; B metallic 0) and the warm reflectance (Specular
    Tint), polished and yellow round the sprite's glint, on the top-view UVs (sprite grid)."""
    nt = mat.node_tree
    for n in [n for n in nt.nodes if n.type in ("TEX_IMAGE", "SEPARATE_COLOR")]:
        nt.nodes.remove(n)
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Specular IOR Level"].default_value = SHEEN["level"]
    w, h = res, int(round(res * H / W))
    ys, xs = np.mgrid[0:h, 0:w]
    u = (xs + 0.5) / w * W
    v = (1 - (ys + 0.5) / h) * H  # image rows run bottom-up in Blender; v is the sprite row (edge coords)
    gx, gy = glint[0] + 0.5, glint[1] + 0.5
    d2 = (u - gx) ** 2 + (v - gy) ** 2
    rough = SHEEN["rough"] - (SHEEN["rough"] - SHEEN["rough_min"]) * np.exp(-d2 / SHEEN["rough_r"] ** 2)
    core = np.exp(-d2 / SHEEN["spec_r"] ** 2)
    halo = np.exp(-d2 / (1.6 * SHEEN["spec_r"]) ** 2)
    tint = []
    for c in range(3):
        b, hl, g = SHEEN["base"][c], SHEEN["halo"][c], SHEEN["glint"][c]
        t = b + (hl - b) * halo
        t = t + (g - t) * core
        tint.append(np.where(t <= 0.0031308, 12.92 * t, 1.055 * t ** (1 / 2.4) - 0.055))  # glTF reads sRGB

    def image(suffix, rgb, colour):
        px = np.stack([*rgb, np.ones_like(rough)], -1).astype(np.float32)
        key = f"{name}_{suffix}"
        img = bpy.data.images.get(key) or bpy.data.images.new(key, w, h, alpha=False)
        img.scale(w, h)
        img.colorspace_settings.name = "Non-Color"  # pixels written as glTF stores them (the tint sRGB-encoded above)
        img.pixels[:] = px.ravel()
        img.pack()
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = "Linear"
        return tex

    zero = np.zeros_like(rough)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(image("finish", (zero, rough, zero), False).outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    nt.links.new(image("spec", tint, True).outputs["Color"], bsdf.inputs["Specular Tint"])
    return mat


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
