"""assembly-newshr-39 (newshr.shp, four 2x2 pieces newshr-1, -3 over -39, -41; 48 x 56 px):
the glass-domed city of IXMUCANE (3.4) and SAWBLADES (3.9), always placed as a pair side by side.

What it is: a round dome of dark blue glass over a city, set into the ground. Through the glass the
blue-grey blocks of the city show, lit from the upper left (blue-lit facades, one red beacon); the glass
catches a white sheen at its upper left and a pale reflection along its lower-right rim. The brown dirt
round it and the dark crater ring are the ground and its shading: the dome stands on the HD terrain
(D86/D130: no floor plate painted from the sprite), the ring is lighting plus the game's ink (D74).

Build (one object in assembly coordinates, cut into the four pieces with common.split_assembly):
- glass: one lathe (a revolved profile, 256 segments, dense rings toward the rim) of an elliptic
  footprint fitted to the sprite's inner mask; a faired dome (superellipse section, no crinkles),
  polished dielectric (metallic 0, roughness 0.12, Specular IOR Level 0.9, D176). The city seen through
  the glass is the glass's own palette regions (what you see through it: D103/D114's glass orb), the
  sprite's classes smoothed at 8x so their edges follow curves, not pixel steps: dark glass, grey-blue
  blocks in three tones, blue-lit facades, the red beacon (a glow, D126). The white glint is a clear-
  coated sheen patch (D92) in the block's light tone; the rim reflection a polished pale band.
- footing: a machined ring under the glass's edge (chamfered sill, a panel groove, a cap lip) with
  twelve buttress plates, dark satin metal: what holds the glass on the ground.
- underside: flat, closed.
- D90/D118 outline shell from a sealed copy of the whole dome, cut open per piece (no filling).

Run: Blender -b --factory-startup --python assembly-newshr-39_A.py -- [--out A.glb] [--pieces DIR]
     [--views DIR]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import types  # noqa: E402
def _mk():
    WT = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(WT / "tools"))
    import sprite_mask as SM  # noqa: E402

    REF = WT / "reference" / "models"
    W, H = 48, 56
    # (piece, cx, cy): piece centre in px from the block's centre (sprite.json assemblyLayout).
    PIECES = [("newshr-1", -12, -14), ("newshr-3", 12, -14), ("newshr-39", -12, 14), ("newshr-41", 12, 14)]
    # The dome in pixel-edge coordinates: the glass reaches col 6 on the left, col 43 on the right and
    # row 9 at the top (rows 44-48 below are the crater's shadow): a circle.
    DOME_C = (24.5, 27.5)
    DOME_R = 18.5


    def load():
        idx = -np.ones((H, W), int)
        colors = {}
        for name, dx, dy in PIECES:
            d = json.loads((REF / name / "sprite.json").read_text())
            colors.update(d["colors"])
            x0, y0 = W // 2 + dx - 12, H // 2 + dy - 14
            for r, line in enumerate(d["frames"][0]["pixels"]):
                for c, v in enumerate(line.split()):
                    idx[y0 + r, x0 + c] = int(v)
        return idx, colors


    def dome_mask():
        yy, xx = np.mgrid[0:H, 0:W]
        return (xx + 0.5 - DOME_C[0]) ** 2 + (yy + 0.5 - DOME_C[1]) ** 2 <= DOME_R ** 2


    def masks(fill_holes=False):
        """D74 masks of the dome alone: the sprite with every pixel outside the dome made transparent.
        fill_holes: the sprite's 1 px see-through slits inside the dome (the dark streets) count as dome."""
        idx, colors = load()
        obj = idx.copy()
        obj[~dome_mask()] = -1
        if fill_holes:
            obj[(obj < 0) & dome_mask()] = 1
        cols = {int(k): tuple(v) for k, v in colors.items()}
        m = SM.masks(obj.tolist(), cols)
        return obj, {k: np.array(v) for k, v in m.items()}



    return types.SimpleNamespace(**{k:v for k,v in locals().items() if not k.startswith('_')})
DD = _mk()


NAME = "assembly-newshr-39"
W, H = DD.W, DD.H
PX = 1 / 12
TAG = "nshr39"

# --- the footprint and the dome's shape (pixel edges) ---------------------------------------------
SILL = 1.0  # px: the footing's width under the glass
Z_SILL = 2.0 * PX  # top of the footing (units)
STEEP_RHO = 0.9  # the glass steeper than ~55 degrees: no city paint
DOME_H = 1.0  # glass apex above the sill (units)
SUPER = 2.25  # section exponent: (r/R)^SUPER + (z/H)^2 = 1 (2 = ellipse; a little fuller shoulders)


def X(c):
    return (c - W / 2) * PX


def Y(r):
    return (H / 2 - r) * PX


IDX, COLORS = DD.load()
SPR = {"name": NAME, "colors": COLORS}


# --- materials -------------------------------------------------------------------------------------

MATS = {}


def spec_level(m, v):
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = v
            break


def coat(m, weight, rough):
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for key in ("Coat Weight", "Clearcoat"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = weight
            break
    for key in ("Coat Roughness", "Clearcoat Roughness"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = rough
            break


def mat(index, kind="glass"):
    key = (index, kind)
    if key in MATS:
        return MATS[key]
    if kind == "glass":  # polished glass over what shows through it
        m = common.palette_material(SPR, index, f"{TAG}_gl", metallic=0.0, roughness=0.36)
        spec_level(m, 0.5)
    elif kind == "dusk":  # between the lit glass and the shadowed side
        m = common.palette_material(SPR, index, f"{TAG}_gd", metallic=0.0, roughness=0.48)
        spec_level(m, 0.3)
    elif kind == "shade":  # the glass on the dome's shadowed lower side: darker, less reflective
        m = common.palette_material(SPR, index, f"{TAG}_gs", metallic=0.0, roughness=0.6)
        spec_level(m, 0.12)
    elif kind == "sheen":  # the white glint: a clear-coated polished patch (D92)
        m = common.palette_material(SPR, index, f"{TAG}_sh", metallic=0.0, roughness=0.06)
        spec_level(m, 1.0)
        coat(m, 1.0, 0.05)
    elif kind == "rim":  # the pale reflection band along the lower-right rim
        m = common.palette_material(SPR, index, f"{TAG}_rim", metallic=0.0, roughness=0.1)
        spec_level(m, 1.0)
    elif kind == "glow":
        m = common.palette_material(SPR, index, f"{TAG}_glow", metallic=1.0, roughness=0.6, emission_strength=2.5)
    else:  # satin machined metal (footing)
        m = common.palette_material(SPR, index, f"{TAG}_m", metallic=0.45, roughness=0.42)
        spec_level(m, 0.5)
    MATS[key] = m
    return m


def glass_grid(center=(24.68, 27.49), harm=3, nseg=256):
    """The glass top's footprint and input points (px, pixel edges), computed at build time from the
    sprite's dome mask: the inner mask's (holes filled) exit radius per angle about `center`, fitted to
    `harm` Fourier harmonics (a0, co[k] = (cos, sin)); then eight rings of `nseg` points dense toward the
    rim (ring 0 is the glass foot) and a 0.25 px grid inside rho 0.875. glass_triangles() triangulates
    them with the paint contours as constraints."""
    inner = DD.masks(True)[1]["inner"]
    th = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    steps = []  # the march's radii, accumulated in 0.02 px steps
    r = 0.0
    while r < 30:
        steps.append(r)
        r += 0.02
    steps = np.array(steps)
    rad = []
    for t in th:
        ci = np.floor(center[0] + steps * np.cos(t)).astype(int)
        ri = np.floor(center[1] - steps * np.sin(t)).astype(int)
        ok = (ri >= 0) & (ri < H) & (ci >= 0) & (ci < W)
        hit = np.zeros(len(steps), bool)
        hit[ok] = inner[ri[ok], ci[ok]]
        rad.append(steps[np.nonzero(hit)[0][-1]] if hit.any() else 0.0)
    rad = np.array(rad)
    a0 = rad.mean()
    co = np.array([(2 * (rad * np.cos(k * th)).mean(), 2 * (rad * np.sin(k * th)).mean())
                   for k in range(1, harm + 1)])

    def rf(t):
        return a0 + sum(co[k, 0] * np.cos((k + 1) * t) + co[k, 1] * np.sin((k + 1) * t) for k in range(len(co)))

    ring_th = 2 * np.pi * np.arange(nseg) / nseg
    pts = []
    for rho in (1.0, 0.996, 0.988, 0.976, 0.96, 0.94, 0.915, 0.89):
        rg = (rf(ring_th) - SILL) * rho
        pts += list(zip(center[0] + rg * np.cos(ring_th), center[1] - rg * np.sin(ring_th)))
    for y in np.arange(6, 50, 0.25):
        for x in np.arange(4, 46, 0.25):
            t = np.arctan2(-(y - center[1]), x - center[0])
            if np.hypot(x - center[0], y - center[1]) / (rf(t) - SILL) < 0.875:
                pts.append((x, y))
    return {"pts": np.array(pts), "center": np.array(center), "nseg": nseg, "a0": a0, "co": co}


GM = glass_grid()
GC = tuple(GM["center"])
NSEG = int(GM["nseg"])


# --- the paint seen through the glass ---------------------------------------------------------------
# The sprite's classes, each blurred (Gaussian, CITY_SIG px; D114's PartField) and the strongest taken at
# 1/8 px, so region edges are smooth curves, not 1 px steps; then the glass is triangulated with every
# region's edge as a constraint (a constrained Delaunay of the glass grid plus the edges' contour lines),
# so the painted edges are those curves, not the grid's zigzag. The highlights are not regions of the
# sprite: the glint is a small round clear-coated spot fading out through a halo ring (core 109, halo 106
# into the lit block 104), the rim reflection an analytic crescent (polar: constant span along the lower
# right, a few px wide, tapered ends) kept inside the glass's steep foot band; the beacon a disc.

K = 8
# class: (sprite indices, palette index of the paint, material kind)
CLASSES = {
    "glass": ({2, 3, 50, 98, 99, 4}, 98, "glass"),
    "shade": ({1, 48, 64, 80, 82, 97, 160, 161, 162, -1}, 97, "shade"),
    "block": ({100, 101}, 100, "glass"),
    "block_mid": ({102, 103, 5}, 102, "glass"),
    "block_lit": ({104, 105, 106, 6, 7, 8}, 104, "glass"),
    "facade": ({53, 54, 56, 57, 58, 59, 60, 129}, 58, "glass"),
    "red": ({67}, 67, "glow"),
    "street": (set(), 80, "glass"),
    "dusk": (set(), 98, "dusk"),
    "sheen": (set(), 109, "sheen"),
    "halo": (set(), 106, "sheen"),
    "rim": (set(), 110, "rim"),
}
CITY_SIG = 0.75  # px: the class blur
GLINT = (18.6, 17.6, 1.2, 2.1)  # the glint's centre (col, row; pixel edges), core and halo radius (px)
RIM_T = (-12.0, -72.0)  # degrees (counter-clockwise from +col): the rim reflection's span
RIM_RHO = (0.925, 0.08)  # its outer edge (fraction of the glass foot's radius) and greatest width


def rfoot(t):
    """Footprint radius (px) at angle t: the inner mask's exit radius, smoothed to 3 harmonics."""
    co = GM["co"]
    return float(GM["a0"]) + sum(co[k, 0] * np.cos((k + 1) * t) + co[k, 1] * np.sin((k + 1) * t)
                                 for k in range(len(co)))


def glass_rho(px, py):
    t = np.arctan2(-(py - GC[1]), px - GC[0])
    return np.hypot(px - GC[0], py - GC[1]) / (rfoot(t) - SILL)


def blur(a, sig):
    rad = max(1, int(3 * sig))
    t = np.arange(-rad, rad + 1)
    g = np.exp(-t * t / (2 * sig * sig))
    g /= g.sum()
    a = np.apply_along_axis(lambda v: np.convolve(np.pad(v, rad, mode="edge"), g, "valid"), 1, a)
    return np.apply_along_axis(lambda v: np.convolve(np.pad(v, rad, mode="edge"), g, "valid"), 0, a)


def paint_map():
    """(H*K, W*K) class labels per sub-pixel (top view): `lab` on the glass, `darklab` on its steep
    foot band (where the city doesn't show: seen from the side it would smear down the glass)."""
    names = list(CLASSES)
    obj = IDX.copy()
    yy, xx = np.mgrid[0:H, 0:W]
    bright = np.isin(obj, [9, 10, 11, 12, 13, 94, 95, 107, 108, 109, 110])
    obj[bright & (xx < 28) & (yy < 24)] = 104  # under the glint: the lit block
    rim_px = np.isin(obj, [5, 6, 7, 8, 9, 10, 11, 12, 13, 104, 105, 106, 107, 108, 109, 110]) & (xx >= 32) \
        & (yy >= 27) & (np.hypot(xx + 0.5 - GC[0], yy + 0.5 - GC[1]) > 12)
    obj[rim_px] = 98  # under the rim reflection: dark glass
    obj[obj == 67] = 102  # the beacon is a disc, below
    st = np.array([np.isin(obj, list(CLASSES[n][0])).astype(float) for n in names])
    up = np.kron(st, np.ones((1, K, K)))
    for i in range(len(names)):
        if st[i].any():
            up[i] = blur(up[i], CITY_SIG * K)
    # the 1 px facade runs must survive the blur: a bias for the rarer classes
    bias = np.array([1.0 if n in ("glass", "shade", "block", "block_mid") else 1.7 if n == "facade" else 1.25
                     for n in names])
    lab = np.argmax(up * bias[:, None, None], axis=0)
    # dark glass: one region per side, not pixel noise: the sprite's darkest shading (1, 80, ...) over its
    # dark glass (2, 3, 98, 99), averaged over ~3 px, decides where the glass takes the shadowed side's
    # darker index (D176), with a dusk band (98, rougher) between
    sh = np.isin(obj, list(CLASSES["shade"][0])).astype(float)
    dk = sh + np.isin(obj, list(CLASSES["glass"][0])).astype(float)
    frac = blur(sh, 3.0) / np.maximum(blur(dk, 3.0), 1e-3)
    frac = blur(np.kron(frac, np.ones((K, K))), 1.0 * K)
    gi, si, di = names.index("glass"), names.index("shade"), names.index("dusk")
    dark = (lab == gi) | (lab == si)
    darklab = np.where(frac > 0.85, si, np.where(frac > 0.55, di, gi))
    lab[dark] = darklab[dark]
    # the streets: the darkest pixels right beside a block (the dark lines between the buildings)
    city = np.isin(obj, [i for n in ("block", "block_mid", "block_lit", "facade") for i in CLASSES[n][0]])
    nb = np.zeros_like(city)
    nb[1:] |= city[:-1]
    nb[:-1] |= city[1:]
    nb[:, 1:] |= city[:, :-1]
    nb[:, :-1] |= city[:, 1:]
    street = (np.isin(obj, list(CLASSES["shade"][0])) & nb).astype(float)
    st_up = blur(np.kron(street, np.ones((K, K))), 0.6 * K)
    lab[dark & (st_up > 0.42)] = names.index("street")
    # analytic highlights and the beacon (sub-pixel centres, px)
    sy, sx = (np.mgrid[0:H * K, 0:W * K] + 0.5) / K
    gx, gy, r0, r1 = GLINT
    d = np.hypot(sx - gx, sy - gy)
    lab[d < r1] = names.index("halo")
    lab[d < r0] = names.index("sheen")
    for r, c in zip(*np.nonzero(IDX == 67)):
        lab[np.hypot(sx - (c + 0.5), sy - (r + 0.5)) < 0.62] = names.index("red")
    t = np.arctan2(-(sy - GC[1]), sx - GC[0])
    rho = glass_rho(sx, sy)
    t0, t1 = map(math.radians, RIM_T)
    u = np.clip((t - t0) / (t1 - t0), -1, 2)
    sw = np.sin(np.pi * np.clip(u, 0, 1))
    outer = RIM_RHO[0] - 0.02 * (1 - sw)
    rim = (u > 0) & (u < 1) & (rho < outer) & (rho > outer - RIM_RHO[1] * sw ** 0.7)
    lab[rim] = names.index("rim")
    darklab = darklab.copy()
    darklab[darklab == si] = di  # the steep band: one dusk tone, no shadow panel seen from the side
    darklab[rim] = names.index("rim")
    return names, lab, darklab


NAMES, LAB, DARKLAB = paint_map()


def class_fields(lab):
    """Each class's indicator, blurred an eighth of a px: its 0.5 contour is the region's smooth edge."""
    return np.array([blur((lab == i).astype(float), 1.0) for i in range(len(NAMES))])


F_LAB, F_DARK = class_fields(LAB), class_fields(DARKLAB)


def sample(F, px, py):
    """Bilinear sample of the (n, H*K, W*K) fields at px coordinates."""
    fx = min(max(px * K - 0.5, 0.0), W * K - 1.001)
    fy = min(max(py * K - 0.5, 0.0), H * K - 1.001)
    j, i = int(fx), int(fy)
    u, v = fx - j, fy - i
    return (F[:, i, j] * (1 - u) * (1 - v) + F[:, i, j + 1] * u * (1 - v) + F[:, i + 1, j] * (1 - u) * v
            + F[:, i + 1, j + 1] * u * v)


def paint_at(px, py, steep=False):
    """Class name at the top-view point (px, py) (pixel edges)."""
    return NAMES[int(np.argmax(sample(F_DARK if steep else F_LAB, px, py)))]


def contours(F, keep):
    """Marching squares at 0.5 over each field in F: (points px (n, 2), edges) for the cells `keep`
    (a (H*K-1, W*K-1) bool mask) says to keep. Points on the same sample edge are shared."""
    pts, edges = [], []
    for f in F:
        b = f > 0.5
        if b.all() or not b.any():
            continue
        h, w = f.shape
        hid = -np.ones((h, w - 1), int)
        ii, jj = np.nonzero(b[:, :-1] != b[:, 1:])
        tt = (0.5 - f[ii, jj]) / (f[ii, jj + 1] - f[ii, jj])
        base = len(pts)
        hid[ii, jj] = base + np.arange(len(ii))
        pts += list(zip((jj + 0.5 + tt) / K, (ii + 0.5) / K))
        vid = -np.ones((h - 1, w), int)
        ii, jj = np.nonzero(b[:-1, :] != b[1:, :])
        tt = (0.5 - f[ii, jj]) / (f[ii + 1, jj] - f[ii, jj])
        base = len(pts)
        vid[ii, jj] = base + np.arange(len(ii))
        pts += list(zip((jj + 0.5) / K, (ii + 0.5 + tt) / K))
        ids = np.stack([hid[:-1, :], vid[:, 1:], hid[1:, :], vid[:, :-1]], axis=-1)  # top right bottom left
        n = (ids >= 0).sum(-1)
        for i, j in zip(*np.nonzero((n >= 2) & keep)):
            e = [x for x in ids[i, j] if x >= 0]
            if len(e) == 2:
                edges.append((e[0], e[1]))
            elif len(e) == 4:
                edges += [(e[0], e[1]), (e[2], e[3])]
    return np.array(pts), edges


def paint_mat(name):
    s, idx, kind = CLASSES[name]
    return mat(idx, kind)


def glass_triangles():
    """The glass top's triangulation (px): glass_grid()'s grid and rings, a ring at the steep band's edge and
    every paint region's contour as constraints. Returns (points (n, 2), rho (n,), triangles, foot ring
    vertex ids in angle order)."""
    from mathutils.geometry import delaunay_2d_cdt
    pts = np.asarray(GM["pts"], float)
    th = 2 * np.pi * np.arange(2 * NSEG) / (2 * NSEG)
    rs = (rfoot(th) - SILL) * STEEP_RHO
    steep = np.column_stack([GC[0] + rs * np.cos(th), GC[1] - rs * np.sin(th)])
    cy, cx = (np.mgrid[0:H * K - 1, 0:W * K - 1] + 1.0) / K
    crho = glass_rho(cx, cy)
    p1, e1 = contours(F_LAB, crho < STEEP_RHO - 0.006)
    p2, e2 = contours(F_DARK, (crho > STEEP_RHO + 0.006) & (crho < 0.99))
    n0, n1 = len(pts), len(pts) + len(steep)
    n2 = n1 + len(p1)
    allp = np.concatenate([pts, steep, p1.reshape(-1, 2), p2.reshape(-1, 2)])
    edges = [(i, (i + 1) % NSEG) for i in range(NSEG)]
    edges += [(n0 + i, n0 + (i + 1) % len(steep)) for i in range(len(steep))]
    edges += [(n1 + a, n1 + b) for a, b in e1] + [(n2 + a, n2 + b) for a, b in e2]
    vs, _es, fs, ov, _oe, _of = delaunay_2d_cdt([Vector((float(x), float(y))) for x, y in allp], edges, [], 0,
                                               1e-5, True)
    P2 = np.array([(v.x, v.y) for v in vs])
    rho = glass_rho(P2[:, 0], P2[:, 1])
    foot = [None] * NSEG
    for k, orig in enumerate(ov):
        for o in orig:
            if o < NSEG:
                foot[o] = k
                rho[k] = 1.0
    tris = [f for f in fs if len(f) == 3]
    cen = P2[np.array(tris)].mean(axis=1)
    keep = glass_rho(cen[:, 0], cen[:, 1]) < 1.0
    tris = [t for t, k in zip(tris, keep) if k]
    print(f"glass: {len(allp)} input points ({len(p1) + len(p2)} on contours), {len(P2)} vertices, "
          f"{len(tris)} triangles, foot ring complete {all(f is not None for f in foot)}")
    return P2, np.clip(rho, 0, 1), tris, foot


# --- mesh helpers ------------------------------------------------------------------------------------

class Part:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []

    def slot(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def obj(self, coll, sharp=40):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(self.name, me)
        coll.objects.link(o)
        me.set_sharp_from_angle(angle=math.radians(sharp))
        return o




def glass_z(rho):
    """Glass height (units) at a fraction rho of the glass foot's radius: a superellipse section."""
    rho = min(max(rho, 0.0), 1.0)
    return Z_SILL + 0.2 * PX + DOME_H * math.sqrt(max(0.0, 1 - rho ** SUPER))


def build_dome(coll):
    P = Part(NAME)
    bm = P.bm
    metal = mat(101, "metal")
    dark = mat(3, "metal")
    pts, rho, tri, foot = glass_triangles()
    # 1. the glass: smooth, painted with what shows through it, each face by its centre
    gv = [bm.verts.new((X(px), Y(py), glass_z(r))) for (px, py), r in zip(pts, rho)]
    for a, b_, c in tri:
        try:
            f = bm.faces.new((gv[a], gv[b_], gv[c]))
        except ValueError:
            continue
        cx, cy = (pts[a] + pts[b_] + pts[c]) / 3
        steep = float(glass_rho(cx, cy)) > STEEP_RHO
        f.material_index = P.slot(paint_mat(paint_at(cx, cy, steep)))
        f.smooth = True
    ring = [gv[k] for k in foot]  # the glass's foot, rho = 1
    # 2. the footing: rings at (inset px from the footprint edge, z units), from the glass foot out and down
    th = [2 * math.pi * i / NSEG for i in range(NSEG)]
    prof = [
        (SILL - 0.12, Z_SILL),  # glazing bead
        (0.3, Z_SILL),  # cap lip
        (0.0, Z_SILL - 0.2 * PX),
        (0.0, 1.45 * PX),
        (0.14, 1.36 * PX),  # panel groove
        (0.14, 1.2 * PX),
        (0.0, 1.11 * PX),
        (0.0, 0.25 * PX),
        (0.3, 0.0),
    ]
    rows = [ring]
    for d, z in prof:
        rows.append([bm.verts.new((X(GC[0] + (rfoot(t) - d) * math.cos(t)), Y(GC[1] - (rfoot(t) - d) * math.sin(t)), z))
                     for t in th])
    for k in range(len(rows) - 1):
        ra, rb = rows[k], rows[k + 1]
        for i in range(NSEG):
            j = (i + 1) % NSEG
            f = bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
            f.material_index = P.slot(metal)
            f.smooth = False
    # 3. the flat bottom
    centre = bm.verts.new((X(GC[0]), Y(GC[1]), 0.0))
    last = rows[-1]
    for i in range(NSEG):
        j = (i + 1) % NSEG
        f = bm.faces.new((last[j], last[i], centre))
        f.material_index = P.slot(dark)
        f.smooth = False
    # 4. twelve buttress plates standing against the footing's side
    for i in range(12):
        t = 2 * math.pi * (i + 0.5) / 12
        r = rfoot(t)
        nrm = Vector((math.cos(t), math.sin(t), 0))
        tan = Vector((-nrm.y, nrm.x, 0))
        base = Vector((X(GC[0] + r * math.cos(t)), Y(GC[1] - r * math.sin(t)), 0)) - nrm * (0.02 * PX)
        w, d, h = 0.9 * PX, 0.9 * PX, Z_SILL + 0.15 * PX
        pp = []
        for sx in (-1, 1):
            for dd, zz in ((0.0, 0.0), (0.0, h - 0.35 * PX), (-0.35 * PX, h), (-d, h), (-d, 0.0)):
                p = base + tan * (sx * w / 2) + nrm * dd
                pp.append((p.x, p.y, zz))
        n0 = len(bm.faces)
        verts = [bm.verts.new(p) for p in pp]
        res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(bm, geom=junk, context="VERTS")
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n0:]:
            f.material_index = P.slot(metal)
            f.smooth = False
    return P.obj(coll)


# --- shell, pieces -----------------------------------------------------------------------------------

SHELL = {"voxel": 0.03, "inside": 0.004, "faces": 2500, "smooth": 8}  # D90


def flat_caps(o):
    """The cut faces split_assembly fills (on the piece's box sides) are flat and their edges sharp, so the
    glass's smooth normals along the cut don't bend toward them (a bright seam line in game)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    hx, hy = 12 * PX, 14 * PX
    on = lambda v: abs(abs(v.co.x) - hx) < 1e-4 or abs(abs(v.co.y) - hy) < 1e-4  # noqa: E731
    n = 0
    for f in bm.faces:
        if all(on(v) for v in f.verts) and abs(f.normal.z) < 0.2:
            f.smooth = False
            for e in f.edges:
                e.smooth = False
            n += 1
    bm.to_mesh(o.data)
    bm.free()
    return n


def layout():
    return [(n, dx, dy) for n, dx, dy in DD.PIECES]


def split_open(obj, lay, coll):
    out = {}
    for name, cx, cy in lay:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        s = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        out[name] = s
    return out


# --- views ---------------------------------------------------------------------------------------------

def setup_render(px, py, engine="EEVEE"):
    scene = bpy.context.scene
    if engine == "WORKBENCH":
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "FLAT"
        scene.display.shading.color_type = "MATERIAL"
        scene.view_settings.view_transform = "Standard"
    else:
        for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scene.render.engine = e
                break
            except TypeError:
                pass
        try:
            scene.view_settings.view_transform = "Standard"
        except TypeError:
            pass
    scene.render.resolution_x, scene.render.resolution_y = px, py
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def lights():
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.35, 0.37, 0.42, 1)
    bg.inputs[1].default_value = 0.7
    for nm, rot, en in (("key", (math.radians(40), 0, math.radians(135)), 3.5),
                        ("fill", (math.radians(60), 0, math.radians(-40)), 0.8)):
        ld = bpy.data.lights.new(nm, "SUN")
        ld.energy = en
        lo = bpy.data.objects.new(nm, ld)
        lo.rotation_euler = rot
        scene.collection.objects.link(lo)


def cam(name, loc, look, ortho=None, lens=50):
    scene = bpy.context.scene
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    data.clip_end = 200
    c = bpy.data.objects.new(name, data)
    scene.collection.objects.link(c)
    c.location = loc
    d = Vector(look) - Vector(loc)
    c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.camera = c
    return c


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def views(out_dir, obj):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH" and o is not obj:
            o.hide_render = True
    # 1. top view, palette index in red (flat), for IoU and region colours
    setup_render(W * K, H * K, "WORKBENCH")
    keep = {m.name: tuple(m.diffuse_color) for m in obj.data.materials}
    for m in obj.data.materials:
        i = int(m.name.split("_")[1])
        s = i / 255
        lin = ((s + 0.055) / 1.055) ** 2.4 if s > 0.04045 else s / 12.92
        m.diffuse_color = (lin, 0, 0, 1)
    c = cam("top", (0, 0, 20), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    render(out_dir / "idx_top.png")
    for m in obj.data.materials:
        m.diffuse_color = keep[m.name]
    lights()
    setup_render(W * K, H * K)
    c = cam("top_lit", (0, 0, 20), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    render(out_dir / "top.png")
    D = 14.0
    vs = {
        "game": (0, -D * math.sin(math.radians(20)), D * math.cos(math.radians(20))),
        "steep": (0, -D * math.sin(math.radians(40)), D * math.cos(math.radians(40))),
        "front": (0, -D, 0.35),
        "rear": (0, D, 0.35),
        "side_w": (-D, 0, 0.35),
        "side_e": (D, 0, 0.35),
        "q_sw": (-D * 0.55, -D * 0.6, D * 0.5),
        "q_nw": (-D * 0.5, D * 0.6, D * 0.5),
        "under": (0, -0.3, -D),
    }
    setup_render(800, 800)
    for nm, loc in vs.items():
        cam(nm, loc, (0, 0, 0.3), lens=100)
        render(out_dir / f"{nm}.png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    obj = build_dome(coll)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    zmax = max(v.co.z for v in bm.verts)
    bm.free()
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles, non-manifold edges {open_edges}, top {zmax:.3f}")
    print("materials:", [m.name for m in obj.data.materials])
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    shell = common.outline_shell(closed, coll, **SHELL)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    bpy.context.view_layer.update()
    lay = layout()
    pieces = common.split_assembly(obj, lay)
    for q in pieces.values():
        flat_caps(q)
    shells = split_open(shell, lay, coll)
    for name, _, _ in lay:
        print(f"{name}: {sum(len(p.vertices) - 2 for p in pieces[name].data.polygons)} triangles")
    if "--out" in argv:
        objs = []
        for name, cx, cy in lay:
            for o in (pieces[name], shells[name]):
                o.location = (cx / 12, -cy / 12, 0)
                objs.append(o)
        bpy.context.view_layer.update()
        common.export_glb(objs, Path(argv[argv.index("--out") + 1]))
        for o in objs:
            o.location = (0, 0, 0)
        bpy.context.view_layer.update()
    if "--no-export" not in argv:
        for name, _, _ in lay:
            sp = common.load_sprite(WT, name)
            common.export_sprite_model(WT, [pieces[name], shells[name]], f"enemies/{name}", sp["sprites"])
    if "--pieces" in argv:
        d = Path(argv[argv.index("--pieces") + 1])
        d.mkdir(parents=True, exist_ok=True)
        for name, _, _ in lay:
            common.export_glb([pieces[name], shells[name]], d / f"{name}.glb")
    for o in list(pieces.values()) + list(shells.values()):
        o.hide_render = True
    shell.hide_render = True
    if "--views" in argv:
        views(argv[argv.index("--views") + 1], obj)


if __name__ == "__main__":
    main()
