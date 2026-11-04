"""Fireball (newsh3.shp frames 267, 269): one smooth teardrop of fire with its hot layers inlaid.

Seen in 8 levels (docs/roadmap/inventory.json). The sprite is a teardrop of fire, tip up the
screen and a round belly below, with an orange body, a yellow core and white-hot sparks inside a
dark-red rim. Its two frames flicker the inner flame.

- Body: one closed, smooth loft per frame, its plan the sprite's INNER mask (D74: inside the ink
  border, tools/sprite_mask.py) fitted row by row with pchip (left and right edges separately, so
  the flame's lean and lopsided belly stay), a pointed tip and a squircle-rounded belly end.
  Sections are superellipse domes whose height follows their half-width (soft-capped), so the
  round end is an ellipsoid cap and the tip a smooth cone that licks upward.
- Flame layers: not plates but the body's own surface. The sprite's palette levels (blurred) give
  a heat field; the hot layers swell the dome a little (an elongated, blurred version of the same
  field, so the tongues stream along the flame) and the colour regions are cut into the mesh along
  the heat iso-lines (marching triangles), so there are no ledges or seams. The orange layer is
  read from a slightly dilated heat field and stops only at a low red band round the base, so it
  wraps down the flanks as the sprite's orange runs out to its shaded rim.
- Colours: each region's palette index (pal_<index>) is the trimmed median of the sprite pixels of
  that layer (darkest/brightest 15% ignored). No emission: the game copies the full palette colour
  into the emissive of any glowing material (src/render/modelFrames.ts), which washes it out.
- Frames: each frame gets its own body + outline shell (common.outline_shell, D51), shown on that
  frame only (common.frame_part, D17).

Run: blender --background --python assets/blender/enemies/newsh3-267.py
"""

import math
import sys
from pathlib import Path

import bmesh
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)
sys.path.insert(0, str(WT / "tools"))
import sprite_mask as SM  # noqa: E402

NAME = "newsh3-267"
PX = 1 / 12
W, H = 24, 28
S = 4                     # sub-samples per sprite px for the fields

# Body shape (sprite px)
H_RATIO = 1.0             # cap on section height per px of half-width
H_MAX = 6.8               # soft cap on the height
H_SOFT = 0.8
P_DOME = 2.2              # superellipse exponent of a section (2 = half ellipse)
RING = 26                 # segments on a body section's dome
STEP = 0.4                # station spacing
EDGE_SMOOTH = 2
TIP_A = 1.2               # px over which the plan closes to the point
TIP_SPAN = 11.0           # px from the tip that rise
TIP_LIFT = 0.9            # px the point rises
REAR_A = 2.0              # px over which the belly end closes (squircle)
REAR_N = 2.3

# Heat field / layers (levels are palette index - 112)
BLUR = 0.85               # colour field gaussian sigma (px)
BUMP_SIG = (1.9, 0.9)     # bump field sigma (y, x): tongues stream along the flame
T_O, T_Y, T_W = 7.2, 10.0, 13.0
DILATE = 0.5              # px the orange layer's field is dilated (wraps down the flanks)
ZR = 0.42                 # the red band: below this fraction of the section height
MIN_AREA = 2.2            # px^2: smaller islands are dropped
A_O, A_Y = 0.35, 0.8      # px the orange and yellow layers swell the dome
EMIT = {"body": 0.0, "orange": 0.0, "yellow": 0.0, "white": 0.0}
NAMES = ["body", "orange", "yellow", "white"]


def X(x):
    return (x - W / 2) * PX


def Y(y):
    return (H / 2 - y) * PX


def pchip(xs, ys):
    """Monotone cubic interpolation (copied from usp_talon.pchip)."""
    import bisect
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def frange(a, b, step):
    n = max(1, int(math.ceil((b - a) / step - 1e-9)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# --- Sprite analysis --------------------------------------------------------------------------

def gauss_blur(field, weight, sy, sx=None):
    sx = sy if sx is None else sx

    def kern(sig):
        r = int(math.ceil(3 * sig))
        k = np.exp(-0.5 * (np.arange(-r, r + 1) / sig) ** 2)
        return k / k.sum()
    ky, kx = kern(sy), kern(sx)

    def conv(a):
        a = np.apply_along_axis(lambda v: np.convolve(v, ky, mode="same"), 0, a)
        return np.apply_along_axis(lambda v: np.convolve(v, kx, mode="same"), 1, a)
    num = conv(field * weight)
    den = conv(weight)
    return np.where(den > 1e-6, num / np.maximum(den, 1e-6), 0.0)


def upsample(sm):
    """Bilinear upsample of a per-px field to S samples per px (sample centres)."""
    ys = (np.arange(H * S) + 0.5) / S - 0.5
    xs = (np.arange(W * S) + 0.5) / S - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, H - 2)
    x0 = np.clip(np.floor(xs).astype(int), 0, W - 2)
    fy = np.clip(ys - y0, 0, 1)[:, None]
    fx = np.clip(xs - x0, 0, 1)[None, :]
    a = sm[y0][:, x0]
    b = sm[y0][:, x0 + 1]
    c = sm[y0 + 1][:, x0]
    d = sm[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def dilate(f, r):
    """Grey dilation (max) over a disc of radius r samples."""
    out = f.copy()
    ri = int(math.ceil(r))
    pad = np.pad(f, ri, mode="edge")
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            if dx * dx + dy * dy <= r * r:
                out = np.maximum(out, pad[ri + dy:ri + dy + f.shape[0], ri + dx:ri + dx + f.shape[1]])
    return out


def components(mask):
    h, w = mask.shape
    lab = np.zeros(mask.shape, int)
    out = []
    n = 0
    for j in range(h):
        for i in range(w):
            if mask[j, i] and not lab[j, i]:
                n += 1
                stack = [(j, i)]
                lab[j, i] = n
                while stack:
                    y, x = stack.pop()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                            lab[yy, xx] = n
                            stack.append((yy, xx))
                out.append(lab == n)
    return out


def drop_islands(f):
    """Push small positive islands of a field below zero."""
    f = f.copy()
    for c in components(f > 0):
        if c.sum() / (S * S) < MIN_AREA:
            f[c] = -0.05
    return f


def sample(grid, x, y):
    """Bilinear sample of an upsampled field at plan point (x, y) in sprite px."""
    fx, fy = x * S - 0.5, y * S - 0.5
    i0 = int(min(max(math.floor(fx), 0), grid.shape[1] - 2))
    j0 = int(min(max(math.floor(fy), 0), grid.shape[0] - 2))
    tx, ty = min(max(fx - i0, 0.0), 1.0), min(max(fy - j0, 0.0), 1.0)
    return ((grid[j0, i0] * (1 - tx) + grid[j0, i0 + 1] * tx) * (1 - ty)
            + (grid[j0 + 1, i0] * (1 - tx) + grid[j0 + 1, i0 + 1] * tx) * ty)


class Heat:
    """The sprite's heat fields for one frame: colour layer fields and the bump field."""

    def __init__(self, frame, colors):
        self.idx = np.array(frame["pixels"], dtype=int)
        m = SM.masks(self.idx.tolist(), colors)
        self.inner = np.array(m["inner"], dtype=bool)
        level = np.where(self.idx >= 0, self.idx - 112, 0).astype(float)
        wgt = self.inner.astype(float)
        heat = upsample(gauss_blur(level, wgt, BLUR))
        self.heat = heat
        ones = np.ones_like(heat)
        self.f_o = drop_islands(gauss_blur(dilate(heat, DILATE * S), ones, 0.5 * S) - T_O)
        self.f_y = drop_islands(heat - T_Y)
        self.f_w = drop_islands(heat - T_W)
        self.f_o_top = drop_islands(heat - T_O)   # the sprite's own orange part (colour median)
        self.bump = upsample(gauss_blur(level, wgt, *BUMP_SIG))

    def swell(self, x, y):
        b = sample(self.bump, x, y)
        return A_O * smoothstep(T_O - 1.5, T_O + 1.0, b) + A_Y * smoothstep(T_Y - 1.5, T_Y + 1.0, b)

    def fields(self, x, y, zf):
        """Per-layer fields (>= 0 inside) at plan (x, y) and section height fraction zf."""
        fo = min(sample(self.f_o, x, y), 6.0 * (zf - ZR))
        fy = sample(self.f_y, x, y)
        fw = sample(self.f_w, x, y)
        return (fo, fy, fw)


# --- Body -------------------------------------------------------------------------------------

def softmin(a, b, k):
    m = min(a, b)
    return m - k * math.log(math.exp(-(a - m) / k) + math.exp(-(b - m) / k))


class Body:
    """The flame's plan (inner mask, pchip per row) and its section heights."""

    def __init__(self, inner):
        rows = [r for r in range(H) if inner[r].any()]
        L = [float(np.argmax(inner[r])) for r in rows]
        R = [float(W - np.argmax(inner[r][::-1])) for r in rows]
        yc = [r + 0.5 for r in rows]
        # the sprite's row edges are stair steps: relax them (ends fixed) so the sides run smooth
        for _ in range(EDGE_SMOOTH):
            L = [L[0]] + [(L[i - 1] + 2 * L[i] + L[i + 1]) / 4 for i in range(1, len(L) - 1)] + [L[-1]]
            R = [R[0]] + [(R[i - 1] + 2 * R[i] + R[i + 1]) / 4 for i in range(1, len(R) - 1)] + [R[-1]]
        self.fl, self.fr = pchip(yc, L), pchip(yc, R)
        self.y_tip = rows[0] + 0.5 - 0.55        # the point, half a px into the tip row
        self.y_bot = rows[-1] + 1.0               # the last row's lower edge
        self.y_c = self.y_bot - REAR_A            # where the belly end starts closing
        widths = [R[i] - L[i] for i in range(len(rows))]
        self.y_pk = yc[int(np.argmax(widths))]    # the belly's widest row

    def extent(self, y):
        """(centre, half-width) of the plan at y (sprite px)."""
        y = min(max(y, self.y_tip), self.y_bot)
        ya = self.y_tip + TIP_A
        if y < ya:   # pointed tip: in to the point along a gentle curve
            t = (y - self.y_tip) / TIP_A
            l, r = self.fl(ya), self.fr(ya)
            c = 0.5 * (l + r)
            # keep the slope continuous with the side at ya (t ** 0.9 is nearly straight)
            return c, 0.5 * (r - l) * t ** 0.9
        yy = min(y, self.y_bot - 0.5)
        l, r = self.fl(yy), self.fr(yy)
        c, hw = 0.5 * (l + r), 0.5 * (r - l)
        if y > self.y_c:   # the belly end: a squircle quarter in to the centre
            t = min(1.0, (y - self.y_c) / (self.y_bot - self.y_c))
            hw *= max(0.0, 1 - t ** REAR_N) ** (1 / REAR_N)
        return c, hw

    def height(self, y):
        """A convex side profile rising from the tip to the belly's widest row, capped by the
        section's own width (so the tip stays a round cone and the belly end an ellipsoid cap)."""
        _, hw = self.extent(y)
        if hw < 1e-6:
            return 0.0
        s = min(1.0, max(0.0, (y - self.y_tip) / (self.y_pk - self.y_tip)))
        rise = H_MAX * (1 - (1 - s) ** 2)
        return max(0.0, softmin(rise, H_RATIO * hw, H_SOFT))

    def lift(self, y):
        """The tip licks upward: the flame's front third rises off the ground, curving."""
        t = (self.y_tip + TIP_SPAN - y) / TIP_SPAN
        return TIP_LIFT * max(0.0, t) ** 2

    def stations(self):
        ys = [self.y_tip + TIP_A * (i / 6) ** 1.6 for i in range(6)]
        ys += frange(self.y_tip + TIP_A, self.y_c, STEP)[:-1]
        ys += [self.y_c + (self.y_bot - self.y_c) * math.sin(0.5 * math.pi * i / 9) for i in range(10)]
        return ys


def section_profile(k):
    """Ring point k of RING: (u in [-1, 1] across, height fraction)."""
    a = math.pi * k / RING          # 0 = right edge, pi = left edge
    cu, su = math.cos(a), math.sin(a)
    return math.copysign(abs(cu) ** (2 / P_DOME), cu), abs(su) ** (2 / P_DOME)


def build_mesh(body, heat):
    """Vertices (x, y px, z px, height fraction) and triangles (a, b, c, base?) of the body."""
    verts, tris = [], []
    rings = []
    for y in body.stations():
        c, hw = body.extent(y)
        h = body.height(y)
        lift = body.lift(y)
        if hw < 1e-6:
            verts.append([c, y, lift, 0.0])
            rings.append([len(verts) - 1])
            continue
        ring = []
        for k in range(RING + 1):
            u, zf = section_profile(k)
            x = c + hw * u
            z = lift + (h + heat.swell(x, y)) * zf
            verts.append([x, y, z, zf])
            ring.append(len(verts) - 1)
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            base = i == n - 1           # the chord from the left edge back to the right edge
            if len(r0) == 1:
                tris.append([r0[0], r1[j], r1[i], base])
            elif len(r1) == 1:
                tris.append([r0[i], r0[j], r1[0], base])
            else:
                tris.append([r0[i], r0[j], r1[j], base])
                tris.append([r0[i], r1[j], r1[i], base])
    return verts, tris


def cut_layers(verts, tris, heat):
    """Split the triangles along each layer's iso-line (marching triangles); returns triangles with
    the layer each one belongs to (0 body .. 3 white). Base triangles stay body."""
    labels = [[] for _ in tris]
    for li in range(3):
        vals = [heat.fields(v[0], v[1], v[3])[li] for v in verts]
        vals = [v if abs(v) > 1e-5 else 1e-5 for v in vals]
        cache = {}

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                t = vals[a] / (vals[a] - vals[b])
                va, vb = verts[a], verts[b]
                verts.append([va[q] + (vb[q] - va[q]) * t for q in range(4)])
                vals.append(0.0)
                cache[key] = len(verts) - 1
            return cache[key]

        out, out_lab = [], []
        for tri, lab in zip(tris, labels):
            a, b, c, base = tri
            if base:
                out.append(tri)
                out_lab.append(lab + [False])
                continue
            s = [vals[a] > 0, vals[b] > 0, vals[c] > 0]
            if s[0] == s[1] == s[2]:
                out.append(tri)
                out_lab.append(lab + [s[0]])
                continue
            # rotate so vertex p is the odd one out
            vs = [a, b, c]
            odd = [i for i in range(3) if s[i] != s[(i + 1) % 3] and s[i] != s[(i + 2) % 3]][0]
            p, q, r = vs[odd], vs[(odd + 1) % 3], vs[(odd + 2) % 3]
            mq, mr = mid(p, q), mid(p, r)
            sp = vals[p] > 0
            out.append([p, mq, mr, False])
            out_lab.append(lab + [sp])
            out.append([mq, q, r, False])
            out_lab.append(lab + [not sp])
            out.append([mq, r, mr, False])
            out_lab.append(lab + [not sp])
        tris, labels = out, out_lab
    layer = []
    for lab in labels:
        n = 0
        for v in lab:
            if not v:
                break
            n += 1
        layer.append(n)
    return verts, tris, layer


# --- Colours ------------------------------------------------------------------------------------

def trimmed_median(vals):
    v = np.sort(np.array(vals))
    if len(v) >= 6:
        k = int(len(v) * 0.15)
        v = v[k:len(v) - k]
    return int(round(float(np.median(v))))


def region_indices(heat):
    """Palette index per layer: the trimmed median of the sprite pixels of that layer (its own
    heat bands at the pixel centres, the orange without the flank dilation)."""
    idx, inner = heat.idx, heat.inner
    groups = {li: [] for li in range(4)}
    for r in range(H):
        for c in range(W):
            if not inner[r, c]:
                continue
            x, y = c + 0.5, r + 0.5
            f = [sample(heat.f_o_top, x, y), sample(heat.f_y, x, y), sample(heat.f_w, x, y)]
            n = 0
            for v in f:
                if v <= 0:
                    break
                n += 1
            groups[n].append(int(idx[r, c]))
    return {li: trimmed_median(v) for li, v in groups.items() if v}


def build(sprite):
    coll = common.reset_collection(NAME)
    colors = {int(k): tuple(v) for k, v in sprite["colors"].items()}
    objs, report = [], {}
    mat_cache = {}

    def mat(index, emit):
        key = (index, emit)
        if key not in mat_cache:
            mat_cache[key] = common.palette_material(sprite, index, NAME, metallic=0.0, roughness=0.7,
                                                     emission_strength=emit)
        return mat_cache[key]

    for frame in sprite["frames"]:
        fi = frame["index"]
        heat = Heat(frame, colors)
        body = Body(heat.inner)
        regions = region_indices(heat)
        verts, tris = build_mesh(body, heat)
        verts, tris, layer = cut_layers(verts, tris, heat)
        used = sorted(set(layer))
        mats, slot = [], {}
        for li in used:
            pal = regions.get(li, regions[max(k for k in regions if k <= li)])
            slot[li] = len(mats)
            mats.append(mat(pal, EMIT[NAMES[li]]))
        report[fi] = {NAMES[k]: v for k, v in regions.items()}
        bm = bmesh.new()
        bv = [bm.verts.new((X(v[0]), Y(v[1]), v[2] * PX)) for v in verts]
        for (a, b, c, base), li in zip(tris, layer):
            if len({a, b, c}) < 3:
                continue
            try:
                f = bm.faces.new((bv[a], bv[b], bv[c]))
            except ValueError:
                continue
            f.material_index = slot[li]
            f.smooth = not base
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-7)
        body_obj = common.mesh_object(f"{NAME}-{fi}", bm, mats, coll, smooth=None)
        shell = common.outline_shell(body_obj, coll, voxel=0.008, faces=1400, smooth=3)
        shell.name = shell.data.name = f"{NAME}-{fi}_outline"
        body_obj.name = body_obj.data.name = f"{NAME}-{fi}"
        common.frame_part(body_obj, [fi])
        common.frame_part(shell, [fi])
        objs += [body_obj, shell]
        report[fi]["layers_used"] = used
    return objs, report


def main():
    sprite = common.load_sprite(WT, NAME)
    objs, report = build(sprite)
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"])
    print("colours", {k: v for k, v in report.items()})


if __name__ == "__main__":
    main()
