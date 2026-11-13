"""Domed city (newshr.shp, nine 2x2 pieces in a 3x3 block, 72x84 px), design A: a glazed egg dome
over an arcology of blue-grey towers, standing on the level's own ground.

What it is: a real ground structure (every spawn is terrain-fixed on the ground layer, IXMUCANE 3.4
and SAWBLADES 3.9). An egg-plan glass bubble, narrow end up the screen, about 40 px tall, its crown
set north of the plan's middle. The glass is open over the city: the renderer draws every model
material opaque, so the panes where the sprite draws the towers through the glass are left out. The
window is cut along the sprite's city edge as the game camera sees the glass (apparent(): a raised
point climbs the screen), so the purple stays where the sprite draws it: the north cap with the
glare, the NE crescent and flank and the foot ring; dielectric glossy glass (D176), one index (84).
Under it a skyline on a plinth, tallest at the back (north, up into the dome's upper volume),
stepping down to the south, each a chamfered prism with a set-back crown, spandrel
bands every 3 px and a parapeted roof. The glass is its own object per piece, tagged tyrian_ground
so it casts no shadow on the city.

Sprite reading (rubric "Reading a sprite"): the white glare upper left and the bright rim down
the right side are the glossy glass's sheen (no geometry, no paint: the glare is polished panes
whose shading normals face the sun's half vector at the game camera, M_SHEEN); the dark ring round the
dome's foot and the shadow on the cobbles are lighting, not modelled; the cobbled ground is the
level's own ground (D130: no floor plate, the dome stands on the HD terrain). Region colours are
the sprite's medians: glass 84 (85 on the lit north cap, 83 on the shaded south flank), towers
by their own block's median in the 96-110 ramp.

Units: c, r = assembly px edges (0, 0 = top left of newshr-5); X = (c - 36) / 12,
Y = (42 - r) / 12, Z = h / 12.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshr-85.py (exports each piece with its shell to
public/models/enemies/<piece>.glb); options after --: [--out x.glb] [--pieces DIR] [--review DIR].
"""

import json
import math
import random
import sys
import types
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
sys.path.insert(0, str(ROOT / "tools"))
import sprite_mask as S  # noqa: E402

# ---- the object mask (D130: the sprite's cobbled ground is not modelled), inlined ----
GRID = [["newshr-5", "newshr-7", "newshr-9"],
        ["newshr-43", "newshr-45", "newshr-47"],
        ["newshr-81", "newshr-83", "newshr-85"]]
W, H = 72, 84


def index_map():
    m = [[-1] * W for _ in range(H)]
    cols = {}
    for gr, names in enumerate(GRID):
        for gc, name in enumerate(names):
            d = json.loads((ROOT / "reference" / "models" / name / "sprite.json").read_text())
            cols.update({int(k): tuple(v) for k, v in d["colors"].items()})
            fr = d["frames"][0]
            for r, row in enumerate(fr["pixels"]):
                for c, v in enumerate(row.split()):
                    m[gr * 28 + r][gc * 24 + c] = int(v)
    return m, cols


def dome_colour(v):
    return 80 <= v <= 111


def object_idx():
    """The index map with the ground made transparent: the dome's colours, the ink touching them
    (8-neighbourhood), and every hole those enclose."""
    m, cols = index_map()
    keep = [[dome_colour(m[r][c]) for c in range(W)] for r in range(H)]
    ink = [[False] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            v = m[r][c]
            if v >= 0 and not keep[r][c] and not (16 <= v <= 20):
                if any(0 <= r + dr < H and 0 <= c + dc < W and keep[r + dr][c + dc]
                       for dr in (-1, 0, 1) for dc in (-1, 0, 1)):
                    ink[r][c] = True
    obj = [[keep[r][c] or ink[r][c] for c in range(W)] for r in range(H)]
    # fill holes: flood the outside from the border over non-object pixels
    out = [[False] * W for _ in range(H)]
    stack = [(r, c) for r in range(H) for c in (0, W - 1)] + [(r, c) for c in range(W) for r in (0, H - 1)]
    while stack:
        r, c = stack.pop()
        if not (0 <= r < H and 0 <= c < W) or out[r][c] or obj[r][c]:
            continue
        out[r][c] = True
        stack += [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]
    idx = [[m[r][c] if not out[r][c] else -1 for c in range(W)] for r in range(H)]
    return idx, cols


def masks():
    idx, cols = object_idx()
    return S.masks(idx, cols), idx, cols



objmask = types.SimpleNamespace(GRID=GRID, masks=masks)


NAME = "assembly-newshr-85"
GRID = objmask.GRID
PIECES = [n for row in GRID for n in row]
W, H = 72, 84
PX = 1 / 12


def P(c, r, h):
    return Vector(((c - 36.0) * PX, (42.0 - r) * PX, h * PX))


# --------------------------------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------------------------------

def merged_colors():
    cols = {}
    for n in PIECES:
        cols.update(common.load_sprite(ROOT, n)["colors"])
    return cols


class Mats:
    def __init__(self):
        self.sprite = {"name": NAME, "colors": merged_colors()}
        self.list, self.slots = [], {}

    def __call__(self, index, metallic=0.35, roughness=0.45, emit=0.0, spec=None, alpha=1.0, coat=0.0):
        key = (index, metallic, roughness, emit, spec, alpha, coat)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            m = common.palette_material(self.sprite, index, f"nshr85a{len(self.list)}", metallic=metallic,
                                        roughness=roughness, emission_strength=emit)
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if spec is not None:  # D176: polished surfaces need F0 (KHR_materials_specular)
                if "Specular IOR Level" in bsdf.inputs:
                    bsdf.inputs["Specular IOR Level"].default_value = spec
            if coat > 0:  # the sheen patch: a clear coat (KHR_materials_clearcoat, as newshm-115)
                bsdf.inputs["Coat Weight"].default_value = coat
                bsdf.inputs["Coat Roughness"].default_value = COAT_ROUGH
            if alpha < 1.0:
                # Clear glass: glTF alphaMode BLEND (three: transparent, no depth write), single
                # sided so the dome's inner top is culled and only the outer pane tints the city.
                bsdf.inputs["Alpha"].default_value = alpha
                m.diffuse_color = (*m.diffuse_color[:3], alpha)  # the flat review render
                for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
                    try:
                        setattr(m, attr, val)
                    except (AttributeError, TypeError):
                        pass
                m.use_backface_culling = True
            self.list.append(m)
        return self.slots[key]


COAT_ROUGH = 0.12
MAT = Mats()
# Glossy glass (D176): dielectric (metallic 0), F0 through Specular IOR Level, so its reflection of
# the game's sky and room is white and greys the purple toward the sprite's dusky glass (a metallic
# tint coloured the reflection purple too and saturated the glass). One index for the whole pane
# (the sprite's glass median, 84; lit, it reads 84-86 as the sprite's does): its darker south-west
# flank and lighter cap are lighting.
GLASS = dict(metallic=0.0, roughness=0.38, spec=1.0)
M_GLASS = MAT(84, **GLASS)
M_GLASS_IN = MAT(83, 0.0, 0.5, spec=0.6)  # the inner face, seen through the window behind the towers
# The sheen (art rule 2: sheen, not paint or a bump). The sprite's brightest feature is a soft white
# blob on the glass at the north-west of the crown (SPRITE_SHEEN, where it is drawn on screen). The
# glass there faces north-west, away from the game's sun, so it can't catch it as a sphere: the
# panes round that point are polished (M_SHEEN) and their shading normals turned toward the sun's
# half vector at the game camera (half_at), full within SHEEN_R0 px of the blob, easing back to the true
# surface normal by SHEEN_R1 (a fair blend: no facet, the silhouette is untouched).
M_SHEEN = MAT(85, metallic=0.0, roughness=0.3, spec=1.0)
SHEEN_R0, SHEEN_R1 = 1.0, 7.0
TILT = math.radians(15)  # the game camera's default ("tilted") style (src/app/hud.ts cameraTilt)
SUN = Vector((-6.0, -8.4, 20.0)).normalized()  # src/render/sun.ts SUN_POSITION, three -> Blender axes
# The game camera relative to the assembly's middle (Blender units, x east, y north, z up) in
# IXMUCANE at t3300 (view.ts fitCamera for the 15 degree tilt: (0, 19.47, 5.96) three; the assembly's
# middle 20 px left of and 1 px below the playfield's). The sheen's normal is the sun's half vector
# toward it (a directional sun; the camera's ray is not parallel across a 6-unit dome: a fixed half
# vector lit the dome's south-east and left its north-west, where the glare is, dull).
CAM = Vector((20 / 12, -(5.96 - 1 / 12), 19.47))
RISE = 0.30  # sprite px a point climbs the screen per px of its height at that camera (measured in captures)
LEAN = 0.11  # and drifts west (the camera stands east of the dome), in the same measure


def half_at(p):
    """The sun's half vector at point p (Blender units, assembly frame) for the game camera."""
    return (SUN + (CAM - p).normalized()).normalized()


FRAME = dict(metallic=0.55, roughness=0.32, spec=0.7)
M_SILL = MAT(85, **FRAME)  # the foot sill
M_FLOOR = MAT(99, 0.2, 0.7)  # the city's plinth top
M_PODIUM = MAT(99, 0.2, 0.7)  # the streets between the towers: a step under the towers' 100-103
PODIUM = 1.6  # px
TOWER = dict(metallic=0.2, roughness=0.6, spec=0.4)
M_MAST = MAT(104, 0.5, 0.35, spec=0.7)
WIN = dict(metallic=1.0, roughness=0.9)  # D126/D173 glow surface
M_WIN = [MAT(109, emit=1.0, **WIN), MAT(110, emit=1.0, **WIN)]  # the sprite's lit windows


def tower_mats(med):
    """(roof, west wall, south wall, east+north wall, band) for a block whose sprite median is `med`."""
    med = max(101, min(103, med + 1))
    # the sprite's towers are lighter blue-grey faces with lit tops (about 101-104): roofs and lit
    # (west, south) faces at or over the block's median, the shaded east/north a step under
    return (MAT(min(med + 1, 104), **TOWER), MAT(min(med + 1, 104), **TOWER), MAT(med, **TOWER),
            MAT(max(med - 1, 100), **TOWER), MAT(max(med - 1, 100), **TOWER))


# --------------------------------------------------------------------------------------------------
# The plan: the object's inner mask (objmask, D74 rule) as a smooth polar curve round the apex
# --------------------------------------------------------------------------------------------------

MK, OIDX, _COLS = objmask.masks()
INNER = MK["inner"]
APEX = (31.5, 27.0)  # the crown, north of the plan's middle (31.5, 35)
NT = 80  # angular samples
HD = 40.0  # dome height, px (an egg: about half its 84 px length)
T_GLASS = 0.5  # glass thickness, px


def fourier_smooth(vals, harmonics):
    n = len(vals)
    out = [0.0] * n
    for k in range(harmonics + 1):
        a = sum(v * math.cos(2 * math.pi * k * i / n) for i, v in enumerate(vals)) * 2 / n
        b = sum(v * math.sin(2 * math.pi * k * i / n) for i, v in enumerate(vals)) * 2 / n
        if k == 0:
            a /= 2
        for i in range(n):
            out[i] += a * math.cos(2 * math.pi * k * i / n) + b * math.sin(2 * math.pi * k * i / n)
    return out


def ray_extent(test, th, step=0.05, far=60):
    """Distance from APEX along angle th (pixel coords, y down) to where `test(col, row)` last holds."""
    dx, dy = math.cos(th), math.sin(th)
    last = 0.0
    d = 0.0
    while d < far:
        c, r = APEX[0] + dx * d, APEX[1] + dy * d
        ci, ri = int(math.floor(c)), int(math.floor(r))
        if 0 <= ri < H and 0 <= ci < W and test(ci, ri):
            last = d
        d += step
    return last


THETAS = [2 * math.pi * i / NT for i in range(NT)]
_raw = [ray_extent(lambda c, r: INNER[r][c], th) + 0.2 for th in THETAS]
RAD = fourier_smooth(_raw, 9)


# The oculus: glass stays high at the back (north, where the sprite shows purple glass and the
# glare above the towers), comes down at the sides and is only a low rim at the front (south),
# so the tilted camera looks over it at the city, as the sprite does through the clear glass.
# Back and sides follow the sprite's glass/city boundary (farthest city pixel along each ray,
# smoothed); the front never rises above the low rim.
def _city(c, r):
    return 96 <= OIDX[r][c] <= 111


_cw = fourier_smooth([max(ray_extent(_city, th + d, step=0.25) for d in (-0.05, 0.0, 0.05)) for th in THETAS], 3)
SW = [max(0.42, min(0.95, max(w / R + 0.04, 0.6 + 0.35 * ((1 + math.sin(th)) / 2) ** 1.6 if math.sin(th) > 0 else 0.0)))
      for w, R, th in zip(_cw, RAD, THETAS)]


def interp(arr, th):
    f = (th % (2 * math.pi)) / (2 * math.pi) * NT
    i = int(math.floor(f)) % NT
    t = f - math.floor(f)
    return arr[i] * (1 - t) + arr[(i + 1) % NT] * t


def profile(s):
    """Height fraction at plan fraction s from the apex: a bubble, vertical at the foot."""
    s = min(1.0, max(0.0, s))
    return (1 - s ** 2.3) ** 0.5


def surf_px(s, th, inset=0.0):
    """(c, r, h) of the dome surface at plan fraction s along angle th; inset > 0: that far inside."""
    R = interp(RAD, th) - inset
    c, r = APEX[0] + math.cos(th) * s * R, APEX[1] + math.sin(th) * s * R
    return c, r, (HD - inset) * profile(s)


def surf(s, th, inset=0.0):
    return P(*surf_px(s, th, inset))


def surf_normal(s, th):
    e = 1e-3
    a = surf(min(1, s + e), th) - surf(max(0, s - e), th)
    b = surf(s, th + e) - surf(s, th - e)
    n = b.cross(a) if s > 0.01 else Vector((0, 0, 1))
    n.normalize()
    if n.z < 0 and s < 0.98:
        n = -n
    return n


_GF = {}


def glass_field(c, r, radius=9.0):
    """The sprite's glass index round plan point (c, r): the mean of its purple pixels (82-90, the
    darkest shading and the glare left out) within `radius` px, rounded; 84 where there are none."""
    key = (int(c), int(r))
    if key not in _GF:
        vals = [OIDX[rr][cc] for rr in range(int(r - radius), int(r + radius) + 1)
                for cc in range(int(c - radius), int(c + radius) + 1)
                if 0 <= rr < H and 0 <= cc < W and 82 <= OIDX[rr][cc] <= 90
                and (rr - r) ** 2 + (cc - c) ** 2 <= radius * radius]
        _GF[key] = max(82, min(86, round(sum(vals) / len(vals)))) if len(vals) > 6 else 84
    return _GF[key]


def dome_h_inner(c, r):
    """Inner glass height (px) over plan point (c, r), 0 outside."""
    dx, dy = c - APEX[0], r - APEX[1]
    d = math.hypot(dx, dy)
    th = math.atan2(dy, dx)
    R = interp(RAD, th) - T_GLASS
    if d >= R:
        return 0.0
    return (HD - T_GLASS) * profile(d / R)


# --------------------------------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------------------------------

def face(bm, verts, mat, smooth=False):
    f = bm.faces.new(verts)
    f.material_index = mat
    f.smooth = smooth
    return f


def grid_surface(bm, rows, mat_fn, smooth=True, closed=True, flip=False):
    """rows[k][i] verts; quads between consecutive rows, wrapping in i when closed."""
    n = len(rows[0])
    for k in range(len(rows) - 1):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            q = [rows[k][i], rows[k][j], rows[k + 1][j], rows[k + 1][i]]
            if flip:
                q.reverse()
            face(bm, q, mat_fn(k, i), smooth)


def tube(bm, pts, radius, mat, closed=False, sides=6, up=None, squash=1.0):
    """A tube along `pts` (Vectors); sections oriented by `up` (a callable giving the surface normal
    at each point) so a glazing bar sits flat on the glass; capped when open."""
    n = len(pts)
    rings = []
    for k, p in enumerate(pts):
        a = pts[(k - 1) % n] if (closed or k > 0) else p
        b = pts[(k + 1) % n] if (closed or k < n - 1) else p
        t = (b - a)
        t.normalize()
        u = up(k) if up else Vector((0, 0, 1))
        u = (u - t * u.dot(t))
        u.normalize()
        v = t.cross(u)
        ring = []
        for s in range(sides):
            ang = 2 * math.pi * (s + 0.5) / sides
            ring.append(bm.verts.new(p + u * (math.cos(ang) * radius * squash) + v * (math.sin(ang) * radius)))
        rings.append(ring)
    for k in range(n if closed else n - 1):
        r0, r1 = rings[k], rings[(k + 1) % n]
        for s in range(sides):
            s2 = (s + 1) % sides
            face(bm, [r0[s], r0[s2], r1[s2], r1[s]], mat, True)
    if not closed:
        face(bm, list(reversed(rings[0])), mat, False)
        face(bm, rings[-1], mat, False)


def prism(bm, c0, c1, r0, r1, z0, z1, mats, ch=0.35):
    """A chamfered-corner box over px edges c0..c1, r0..r1, z0..z1 (px). mats = (top, west, south,
    east/north). Returns nothing; flat shaded."""
    top, west, south, east = mats
    ch = min(ch, (c1 - c0) / 3, (r1 - r0) / 3)
    # octagon, counter-clockwise seen from above (pixel rows go down = -Y)
    oc = [(c0 + ch, r1), (c1 - ch, r1), (c1, r1 - ch), (c1, r0 + ch), (c1 - ch, r0), (c0 + ch, r0),
          (c0, r0 + ch), (c0, r1 - ch)]
    lo = [bm.verts.new(P(c, r, z0)) for c, r in oc]
    hi = [bm.verts.new(P(c, r, z1)) for c, r in oc]
    face(bm, list(reversed(lo)), east)
    face(bm, hi, top)
    side = [south, east, east, east, east, west, west, west]  # per edge i -> i+1
    # edges: 0-1 south, 1-2 SE chamfer, 2-3 east, 3-4 NE, 4-5 north, 5-6 NW, 6-7 west, 7-0 SW
    side = [south, south, east, east, east, west, west, west]
    for i in range(8):
        j = (i + 1) % 8
        face(bm, [lo[i], lo[j], hi[j], hi[i]], side[i])


def roof_well(bm, c0, c1, r0, r1, z, mats, lip=0.35, depth=0.3):
    """A parapet: a frame `lip` px wide standing `depth` px over the roof at z, inner roof below."""
    top = mats[0]
    prism(bm, c0, c1, r0, r1, z, z + depth, (top, mats[1], mats[2], mats[3]), ch=0.3)
    # the recessed inner roof: a slightly darker plate just above z, inside the lip (seen from above)
    prism(bm, c0 + lip, c1 - lip, r0 + lip, r1 - lip, z + depth - 0.01, z + depth + 0.005,
          (mats[3], mats[3], mats[3], mats[3]), ch=0.2)


# --------------------------------------------------------------------------------------------------
# The glass dome
# --------------------------------------------------------------------------------------------------

K_EGG = 30  # rows from the crown to the foot (the sealed copy's band)


def s_row(k, K=K_EGG):
    """Plan fraction of row k: even in arc length near the crown, dense at the foot."""
    return math.sin(k / K * math.pi / 2) ** 0.85


FOOT_H = 6.0  # px: the window never comes lower than this (the sprite's purple foot ring)


def apparent(c, r, h):
    """Where a point (plan px, h px up) shows at the game camera, in the sprite's pixels: the tilted
    camera carries a raised point up the screen by h * RISE and west by h * LEAN (the sprite draws the dome as the
    game camera sees it: the crown at its top edge, the towers rising up the screen)."""
    return c - h * LEAN, r - h * RISE


def _city_field():
    """The sprite's city share per pixel (towers 96-111 = 1, the glass 80-95 and the ground = 0, the
    ink between towers left out), smoothed (normalised Gaussian, sigma CITY_SIGMA px), so the window's
    edge is a fair curve round the towers the sprite draws through the glass."""
    import numpy as np
    val = np.zeros((H, W))
    wt = np.ones((H, W))
    for r in range(H):
        for c in range(W):
            v = OIDX[r][c]
            if 96 <= v <= 111:
                val[r, c] = 1.0
            elif v >= 0 and not (80 <= v <= 95):
                wt[r, c] = 0.0  # ink inside the dome: no vote
    rad = int(CITY_SIGMA * 3)
    ker = np.exp(-np.arange(-rad, rad + 1) ** 2 / (2 * CITY_SIGMA ** 2))

    def blur(a):
        a = np.pad(a, rad)
        a = np.apply_along_axis(lambda x: np.convolve(x, ker, "same"), 0, a)
        a = np.apply_along_axis(lambda x: np.convolve(x, ker, "same"), 1, a)
        return a[rad:-rad, rad:-rad]

    return blur(val * wt) / np.maximum(blur(wt), 1e-6)


CITY_SIGMA = 1.6
CITY = _city_field()


def city_at(c, r):
    """Bilinear sample of CITY at sprite point (c, r) (pixel centres at +0.5); 0 off the sprite."""
    x, y = c - 0.5, r - 0.5
    x0, y0 = math.floor(x), math.floor(y)
    tx, ty = x - x0, y - y0
    tot = 0.0
    for dy, wy in ((0, 1 - ty), (1, ty)):
        for dx, wx in ((0, 1 - tx), (1, tx)):
            yy, xx = y0 + dy, x0 + dx
            if 0 <= yy < H and 0 <= xx < W:
                tot += wy * wx * CITY[yy, xx]
    return tot


def openness(s, th):
    """> 0 where the glass is left out: the pane faces the game camera, stands above the foot ring,
    and the sprite draws towers (not purple glass) where it shows on screen. A min of fair fields,
    so the window's edge is fair."""
    c, r, h = surf_px(s, th)
    n = surf_normal(s, th)
    ca, ra = apparent(c, r, h)
    return min(city_at(ca, ra) - 0.5, (n.dot((CAM - P(c, r, h)).normalized()) - 0.25) * 2.0, (h - FOOT_H) / 4.0)


def _blob():
    """The sprite's glare: the centroid of its brightest glass pixels (89-95) in the north-west."""
    pts = [(c + 0.5, r + 0.5) for r in range(0, 30) for c in range(0, 36) if 89 <= OIDX[r][c] <= 95]
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


SPRITE_SHEEN = _blob()



def sheen_weight(c, r, h):
    """1 at the sprite's glare (as it shows at the game camera), easing to 0 by SHEEN_R1 px."""
    ca, ra = apparent(c, r, h)
    d = math.hypot(ca - SPRITE_SHEEN[0], ra - SPRITE_SHEEN[1])
    t = min(1.0, max(0.0, (d - SHEEN_R0) / (SHEEN_R1 - SHEEN_R0)))
    return 1.0 - t * t * (3 - 2 * t)


K_GL = 44  # glass rows from the crown to the foot
NT_GL = 120  # glass meridians


def glass_open(bm):
    """The glass: a thin closed solid over the whole egg with the window cut out of it along the
    zero line of openness() (each grid triangle clipped, the cut points interpolated on its edges,
    so the window's edge is the fair curve itself, not a staircase of panes), a rim strip closing
    the cut edge and a foot strip the bottom. The outer face is one glossy purple (M_GLASS) with the
    polished sheen panes round the glare; the inner face shows through the window behind the towers."""
    K, N = K_GL, NT_GL
    dth = 2 * math.pi / N
    par, fval = {}, {}

    def gkey(k, i):
        return ("c",) if k == 0 else ("g", k, i % N)

    for k in range(K + 1):
        for i in range(N if k else 1):
            key = gkey(k, i)
            s, th = s_row(k, K), i * dth
            par[key] = (s, th)
            f = openness(s, th) if k else -1.0
            fval[key] = f if abs(f) > 1e-7 else -1e-7

    def gpar(key, i_hint):
        """(s, th) of a grid key, th unwrapped next to meridian i_hint (the crown: any th)."""
        if key[0] == "c":
            return (0.0, i_hint * dth)
        s, th = par[key]
        i = key[2]
        while i < i_hint - N / 2:
            i += N
        while i > i_hint + N / 2:
            i -= N
        return (s, i * dth)

    def epoint(a, b, i_hint):
        ka, kb = sorted((a, b))
        key = ("e", ka, kb)
        if key not in par:
            pa, pb = gpar(ka, i_hint), gpar(kb, i_hint)
            if ka[0] == "c":
                pa = (0.0, pb[1])
            if kb[0] == "c":
                pb = (0.0, pa[1])
            t = fval[ka] / (fval[ka] - fval[kb])
            par[key] = (pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t)
        return key

    polys, cuts = [], []
    for k in range(K):
        for i in range(N):
            a, b, c_, d = gkey(k, i), gkey(k, i + 1), gkey(k + 1, i + 1), gkey(k + 1, i)
            tris = [(a, c_, d)] if k == 0 else [(a, b, c_), (a, c_, d)]
            for tri in tris:
                out = []
                outside = [v for v in tri if fval[v] > 0]
                if len(outside) == 3:
                    continue
                for m in range(3):
                    p, q = tri[m], tri[(m + 1) % 3]
                    if fval[p] <= 0:
                        out.append(p)
                    if (fval[p] <= 0) != (fval[q] <= 0):
                        out.append(epoint(p, q, i))
                polys.append((out, i))
                if outside:
                    es = [v for v in out if v[0] == "e"]
                    cuts.append((es[0], es[1], outside, i))

    def pos(key, i_hint, inset):
        s, th = par[key] if key[0] == "e" else gpar(key, i_hint)
        return surf(s, th, inset)

    vo, vi = {}, {}

    def vert(store, key, i_hint, inset):
        if key not in store:
            store[key] = bm.verts.new(pos(key, i_hint, inset))
        return store[key]

    def oriented(verts, want):
        """Face over verts, wound so its normal points along `want`."""
        n = (verts[1].co - verts[0].co).cross(verts[2].co - verts[0].co)
        if n.dot(want) < 0:
            verts = list(reversed(verts))
        return verts

    for out, i in polys:
        if len(out) < 3:
            continue
        ov = [vert(vo, k_, i, 0.0) for k_ in out]
        iv = [vert(vi, k_, i, T_GLASS) for k_ in out]
        cen = sum((v.co for v in ov), Vector()) / len(ov)
        if len(set(ov)) < 3:
            continue
        cpx = (cen.x / PX + 36.0, 42.0 - cen.y / PX, cen.z / PX)
        m = M_SHEEN if sheen_weight(*cpx) > 0.0 else M_GLASS
        up = cen - P(APEX[0], APEX[1] + 4, 0)
        face(bm, oriented(ov, up), m, True)
        face(bm, oriented(iv, -up), M_GLASS_IN, True)
    # the rim: a strip between the outer and inner cut edges, facing into the window
    for e1, e2, outside, i in cuts:
        o1, o2 = vo[e1], vo[e2]
        i1, i2 = vi[e1], vi[e2]
        mid = (o1.co + o2.co) / 2
        tow = sum((pos(v, i, 0.0) for v in outside), Vector()) / len(outside) - mid
        f = face(bm, oriented([o1, o2, i2, i1], tow), M_GLASS, False)
        for e in f.edges:
            e.smooth = False
    # the foot
    for i in range(N):
        a, b = gkey(K, i), gkey(K, i + 1)
        if a in vo and b in vo:
            o1, o2, i1, i2 = vo[a], vo[b], vi[a], vi[b]
            face(bm, oriented([o1, o2, i2, i1], Vector((0, 0, -1))), M_SILL)
    n_open = sum(1 for k in fval if fval[k] > 0)
    print(f"glass: {len(polys)} polys, {len(cuts)} cut segments, {n_open} open grid points; "
          f"sprite glare at ({SPRITE_SHEEN[0]:.1f}, {SPRITE_SHEEN[1]:.1f})")


def glass_egg(bm, k0=0):
    """A closed thin solid over the egg from row k0 (> 0) down to the foot: the sealed copy's band
    for the outline shell (D90/D118)."""
    rows = list(range(k0, K_EGG + 1))
    outer = [[bm.verts.new(surf(s_row(k), th)) for th in THETAS] for k in rows]
    inner = [[bm.verts.new(surf(s_row(k), th, T_GLASS)) for th in THETAS] for k in rows]
    for n in range(len(rows) - 1):
        for i in range(NT):
            j = (i + 1) % NT
            face(bm, [outer[n][j], outer[n][i], outer[n + 1][i], outer[n + 1][j]], 0, True)
            face(bm, [inner[n][i], inner[n][j], inner[n + 1][j], inner[n + 1][i]], 0, True)
    for i in range(NT):
        j = (i + 1) % NT
        face(bm, [outer[-1][i], outer[-1][j], inner[-1][j], inner[-1][i]], 0)
        face(bm, [outer[0][j], outer[0][i], inner[0][i], inner[0][j]], 0)


def build_glass(bm):
    # No glazing bars across the window: the sprite draws no lines over the city, only the purple
    # foot ring and the NE crescent (the cut edge and the foot sill carry those).
    glass_open(bm)


def sheen_normals(piece, cx, cy):
    """Turn the glass's shading normals round the glare toward half_at() (see M_SHEEN): per corner, the
    smooth normal blended toward half_at() by sheen_weight at that corner's place on screen. Run on each glass piece
    after the split (cx, cy: its centre in assembly px from the middle)."""
    me = piece.data
    sheen_slots = {i for i, m in enumerate(me.materials) if m == MAT.list[M_SHEEN]}
    hw, hh = 1.0, 14 / 12
    cn = [Vector(c.vector) for c in me.corner_normals]
    out = list(cn)
    n_set = 0
    for poly in me.polygons:
        vs = [me.vertices[v].co for v in poly.vertices]
        # the seam fills too (whatever pane they took their material from): the newshr-7 / newshr-45
        # seam runs through the glare, and a fill left with its flat normal along the seam showed
        # through the pieces' sub-pixel seam gap as a grey dot in the white blob
        seam = (all(abs(abs(v.x) - hw) < 1e-4 for v in vs) or all(abs(abs(v.y) - hh) < 1e-4 for v in vs))
        if poly.material_index not in sheen_slots and not seam:
            continue
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            c, r, h = co.x / PX + cx + 36.0, -co.y / PX + cy + 42.0, co.z / PX
            w = sheen_weight(c, r, h)
            if w > 0:
                n = cn[li] * (1 - w) + half_at(P(c, r, h)) * w
                n.normalize()
                out[li] = n
                n_set += 1
    if n_set:
        me.normals_split_custom_set([tuple(v) for v in out])
        print(f"{piece.name}: sheen normals on {n_set} corners")


def build_dome(bm):
    # The foot sill: a low rounded kerb round the outside of the foot (inside the plan edge).
    sill = [surf(1.0, th, inset=0.35) + Vector((0, 0, 0.35 * PX)) for th in THETAS]
    tube(bm, sill, 0.42 * PX, M_SILL, closed=True, sides=6, squash=0.9)


def build_floor(bm):
    """The city's plinth: a disc filling the dome's foot (closes the underside), its top 0.4 px up,
    with a darker street ring round the tower cluster."""
    ring = [surf(1.0, th, inset=T_GLASS * 0.5) for th in THETAS]
    lo = [bm.verts.new(Vector((p.x, p.y, 0.0))) for p in ring]
    hi = [bm.verts.new(Vector((p.x, p.y, 0.4 * PX))) for p in ring]
    c0 = bm.verts.new(P(APEX[0], APEX[1] + 6, 0.4))
    c1 = bm.verts.new(P(APEX[0], APEX[1] + 6, 0.0))
    for i in range(NT):
        j = (i + 1) % NT
        face(bm, [hi[i], hi[j], c0], M_FLOOR)
        face(bm, [lo[j], lo[i], c1], M_FLOOR)
        face(bm, [lo[i], lo[j], hi[j], hi[i]], M_FLOOR)
    # the city deck: a podium under the towers inside the oculus, its top edge chamfered
    zs = (0.2, PODIUM - 0.35, PODIUM)
    insets = (0.0, 0.0, 0.35)
    rings = []
    for z, ins in zip(zs, insets):
        ring = []
        for th in THETAS:
            sw = interp(SW, th) * 0.9
            c, r, _ = surf_px(sw, th)
            d = math.hypot(c - APEX[0], r - APEX[1])
            k = max(0.0, d - ins) / d if d else 0
            ring.append(bm.verts.new(P(APEX[0] + (c - APEX[0]) * k, APEX[1] + (r - APEX[1]) * k, z)))
        rings.append(ring)
    grid_surface(bm, rings, lambda k, i: M_PODIUM, smooth=False)
    ctr = bm.verts.new(P(APEX[0], APEX[1] + 8, PODIUM))
    cb = bm.verts.new(P(APEX[0], APEX[1] + 8, 0.2))
    for i in range(NT):
        j = (i + 1) % NT
        face(bm, [rings[-1][i], rings[-1][j], ctr], M_PODIUM)
        face(bm, [rings[0][j], rings[0][i], cb], M_PODIUM)


# --------------------------------------------------------------------------------------------------
# The city
# --------------------------------------------------------------------------------------------------

# Building blocks as the sprite draws them (col0, col1, row0, row1, drawn height class). The sprite
# draws them in an oblique view, rising up the screen: the footprint is the lower part of each
# drawn block, its height the rest (the tilted game camera raises them up the screen again).
TOWERS = [
    (29.5, 35, 9, 24, 0.66),  # the central tower, tallest, at the back
    (26, 36, 21.5, 37, 0.46),  # the block at its foot
    (37.5, 45, 19.5, 34, 0.54),  # the right tower
    (36, 45, 33, 41, 0.36),
    (10, 15, 23.5, 41, 0.48),  # the left tower
    (15, 19, 28, 40, 0.3),
    (19, 26, 21, 33, 0.5),
    (19, 23, 33, 41, 0.38),
    (31, 36, 37, 47, 0.3),
    (26.5, 30.5, 37.5, 47, 0.32),  # the light front tower
    (23.5, 26.5, 39.5, 48, 0.24),
    (33, 45, 41, 51, 0.24),
    (44.5, 50, 30, 51, 0.3),
    (49.5, 55, 38.5, 52, 0.18),
    (9, 15.5, 41, 51, 0.22),
    (15, 20.5, 40, 48, 0.22),
    (20.5, 26, 33, 41, 0.28),
    (15, 24, 48, 57, 0.14),
    (24, 33, 47, 60, 0.12),
    (33, 41, 51, 61, 0.12),
    (41, 51, 50, 59, 0.12),
]


def block_median(c0, c1, r0, r1):
    vals = sorted(OIDX[r][c] for r in range(int(r0), int(math.ceil(r1))) for c in range(int(c0), int(math.ceil(c1)))
                  if 97 <= OIDX[r][c] <= 106)
    return vals[len(vals) // 2] if vals else 100


TOWER_BODIES = []


def build_city(bm):
    rng = random.Random(8543)
    floor_z = 0.4
    TOWER_BODIES.clear()
    for (c0, c1, r0, r1, hcls) in TOWERS:
        med = block_median(c0, c1, r0, r1)
        roof, west, south, east, band = tower_mats(med)
        hpx = 38 * (hcls / 0.66) ** 0.8  # drawn height class -> px: a skyline stepping down south
        drawn = r1 - r0
        foot = max(3.5, 0.45 * drawn, drawn - hpx * 0.45)  # drawn length minus the oblique rise
        ins = 0.8 if c1 - c0 > 5 else 0.6  # slender: dark streets between the shafts
        a0, a1, b1 = c0 + ins, c1 - ins, r1 - 0.6
        b0 = max(r0 + 0.6, b1 - foot)
        # under the glass: the inner glass over the footprint, less a margin
        under = min(dome_h_inner(a0 + (a1 - a0) * i / 3, b0 + (b1 - b0) * j / 3)
                    for i in range(4) for j in range(4)) - 1.2
        h = max(2.0, min(hpx, under))
        print(f'tower {c0}-{c1} x {r0}-{r1}: med {med} foot {b0:.1f}-{b1:.1f} h {h:.1f} (want {hpx:.1f})')
        mats = (roof, west, south, east)
        tall = h >= 9
        body = h * (0.8 if tall else 1.0)
        prism(bm, a0, a1, b0, b1, floor_z, body, mats)
        TOWER_BODIES.append((a0, a1, b0, b1, floor_z, body))
        # spandrel bands every 3 px: thin proud strips round the shaft (modelled panel lines)
        z = floor_z + 2.6
        while h >= 6 and z < body - 1.2:
            prism(bm, a0 - 0.1, a1 + 0.1, b0 - 0.1, b1 + 0.1, z, z + 0.35, (band, band, band, band), ch=0.4)
            # lit windows on some floors (south and west faces), a run or two
            if rng.random() < 0.3:  # the sprite shows only a few lit windows
                wm = M_WIN[rng.randrange(2)]
                zw0, zw1 = z + 0.7, z + 1.9
                if zw1 < body - 0.6:
                    x0 = a0 + 0.4 + rng.random() * max(0.0, (a1 - a0) - 2.4) * 0.4
                    x1 = min(a1 - 0.4, x0 + 1.4 + rng.random() * (a1 - a0) * 0.6)
                    if x1 - x0 > 0.8:
                        prism(bm, x0, x1, b1 - 0.2, b1 + 0.06, zw0, zw1, (wm, wm, wm, wm), ch=0.0)
                    y0 = b0 + 0.6 + rng.random() * max(0.0, (b1 - b0) - 3.0) * 0.5
                    y1 = min(b1 - 0.6, y0 + 1.0 + rng.random() * (b1 - b0) * 0.5)
                    if y1 - y0 > 0.8:
                        prism(bm, a0 - 0.06, a0 + 0.2, y0, y1, zw0, zw1, (wm, wm, wm, wm), ch=0.0)
            z += 3.0
        if tall:
            ins = min(0.8, (a1 - a0) * 0.18, (b1 - b0) * 0.18)
            prism(bm, a0 + ins, a1 - ins, b0 + ins, b1 - ins, body, h - 0.3, mats)
            TOWER_BODIES.append((a0 + ins, a1 - ins, b0 + ins, b1 - ins, body - 0.05, h))
            roof_well(bm, a0 + ins, a1 - ins, b0 + ins, b1 - ins, h - 0.3, (roof, west, south, east))
            top_z = h
        else:
            roof_well(bm, a0, a1, b0, b1, body - 0.3, (roof, west, south, east))
            top_z = body
        # a lit skylight on most roofs (the sprite's lit windows read from straight overhead too)
        rx0, rx1, ry0, ry1 = (a0 + ins, a1 - ins, b0 + ins, b1 - ins) if tall else (a0, a1, b0, b1)
        if rx1 - rx0 > 2.2 and ry1 - ry0 > 2.2 and rng.random() < 0.35:
            wm = M_WIN[rng.randrange(2)]
            sx0 = rx0 + 0.7 + rng.random() * max(0.0, rx1 - rx0 - 2.6)
            prism(bm, sx0, min(rx1 - 0.6, sx0 + 1.3), ry1 - 1.5, ry1 - 0.6, top_z - 0.05, top_z + 0.12,
                  (wm, wm, wm, wm), ch=0.0)
        # roof plant on the larger roofs
        if (a1 - a0) > 4 and (b1 - b0) > 4:
            cx, cy = (a0 + a1) / 2, (b0 + b1) / 2
            prism(bm, cx - 1.0, cx + 0.6, cy - 0.8, cy + 0.8, top_z, top_z + 0.8, (roof, west, south, east), ch=0.2)
        if hcls >= 0.6:  # the central tower's mast
            cx, cy = (a0 + a1) / 2, (b0 + b1) / 2
            room = dome_h_inner(cx, cy) - 0.8 - top_z
            if room > 1.0:
                pts = [P(cx, cy, top_z + room * t) for t in (0.0, 0.5, 1.0)]
                tube(bm, pts, 0.28 * PX, M_MAST, sides=6)
                prism(bm, cx - 0.7, cx + 0.7, cy - 0.7, cy + 0.7, top_z, top_z + 0.6, (M_MAST,) * 4, ch=0.25)


# --------------------------------------------------------------------------------------------------
# Build, pieces, shells, export
# --------------------------------------------------------------------------------------------------

def to_obj(bm, name, coll):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in MAT.list:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def build_glass_obj(coll):
    """The glass on its own object, tagged tyrian_ground so it casts no shadow (modelPrep.castsShadow):
    the game's shadow map ignores alpha, and a shadowing egg would black out the city under it."""
    bm = bmesh.new()
    build_glass(bm)  # wound face by face (the cut rim's normals are set there)
    me = bpy.data.meshes.new(NAME + "_glass")
    bm.to_mesh(me)
    bm.free()
    for m in MAT.list:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME + "_glass", me)
    coll.objects.link(obj)
    return obj


def fix_seam_fills(piece):
    """split_assembly fills the glass's cut sections at the piece seams with slot 0: give each fill the
    material of the pane it closes."""
    bm = bmesh.new()
    bm.from_mesh(piece.data)
    hw, hh = 1.0, 14 / 12
    inner = MAT.list[M_GLASS_IN]

    def on_seam(f):
        return all(abs(abs(v.co.x) - hw) < 1e-4 for v in f.verts) or all(abs(abs(v.co.y) - hh) < 1e-4 for v in f.verts)

    for f in bm.faces:
        if on_seam(f):
            nb = [g for e in f.edges for g in e.link_faces if g is not f and not on_seam(g)]
            # the outer pane's material first: a fill that took the inner face's (83, matte, its
            # flat normal facing along the seam) showed as a grey pixel in the middle of the glare,
            # where the newshr-7 / newshr-45 seam crosses it at the game camera
            nb.sort(key=lambda g: piece.data.materials[g.material_index] == inner)
            if nb:
                f.material_index = nb[0].material_index
            # keep the pane's smooth normals off the fill (else a lit seam line across the glass)
            for e in f.edges:
                e.smooth = False
    bm.to_mesh(piece.data)
    bm.free()


def build(coll):
    bm = bmesh.new()
    build_dome(bm)
    build_floor(bm)
    build_city(bm)
    # recalc_face_normals would fight the separate thin parts; orient per component instead
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in MAT.list:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    return obj


def build_sealed(coll):
    """What the outline shells are made from (D90/D118, a closed copy, never the culled model): the
    glass band as a solid and the tower bodies. Not the whole egg: a solid egg cut at the piece
    seams stood walls across the open oculus whose back faces drew as dark bands over the city."""
    bm = bmesh.new()
    # The glass's low band only (to about 10 px up): the ink sits on the dome's foot, as the sprite's
    # outline ring. The whole egg as a solid would put its inner top's back faces under the clear
    # glass as a dark disc over the city (the shell draws wherever no opaque depth covers it).
    k0 = next(k for k in range(1, K_EGG) if HD * profile(s_row(k)) <= FOOT_H)
    glass_egg(bm, k0=k0)
    # The towers get no shell (ink on the silhouette only: a shell per tower drew black rims round
    # every roof inside the dome).
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(NAME + "_sealed")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(NAME + "_sealed", me)
    coll.objects.link(obj)
    return obj


def keeper_box(sp, dx, dy):
    """Fill empty sealed piece `sp` (centre dx, dy px from the middle) with a box 1 px inside the
    widest tower body in it (piece-local coordinates)."""
    c0, c1, r0, r1 = dx + 36 - 12, dx + 36 + 12, dy + 42 - 14, dy + 42 + 14
    best = None
    for a0, a1, b0, b1, z0, z1 in TOWER_BODIES:
        x0, x1, y0, y1 = max(a0, c0) + 1, min(a1, c1) - 1, max(b0, r0) + 1, min(b1, r1) - 1
        if x1 - x0 > 1 and y1 - y0 > 1 and z1 - z0 > 3:
            area = (x1 - x0) * (y1 - y0)
            if best is None or area > best[0]:
                best = (area, x0, x1, y0, y1, z0 + 1, z1 - 1.5)
    _, x0, x1, y0, y1, z0, z1 = best
    bm = bmesh.new()
    off = P(36 + dx, 42 + dy, 0)
    vs = [bm.verts.new(P(x, y, z) - off) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    for q in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)):
        bm.faces.new([vs[i] for i in q])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(sp.data)
    bm.free()
    print(f"{sp.name}: keeper box {x0:.1f}-{x1:.1f} x {y0:.1f}-{y1:.1f} x {z0:.1f}-{z1:.1f} px")


def layout():
    return [(name, gc * 24 + 12 - W / 2, gr * 28 + 14 - H / 2)
            for gr, names in enumerate(GRID) for gc, name in enumerate(names)]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    glass = build_glass_obj(coll)
    sealed = build_sealed(coll)
    print("whole tris", sum(len(p.vertices) - 2 for p in obj.data.polygons))
    lay = layout()
    pieces = common.split_assembly(obj, lay, coll)
    glass_pieces = common.split_assembly(glass, [(f"{n}_glass", cx, cy) for n, cx, cy in lay], coll)
    for name, cx, cy in lay:
        g = glass_pieces[f"{name}_glass"]
        fix_seam_fills(g)
        sheen_normals(g, cx, cy)
        g["tyrian_ground"] = True
    sealed_pieces = common.split_assembly(sealed, [(f"{n}_s", cx, cy) for n, cx, cy in lay], coll)
    shells, total, exports = [], 0, {}
    for name, dx, dy in lay:
        p = pieces[name]
        sp = sealed_pieces[f"{name}_s"]
        bpy.context.view_layer.update()
        if len(sp.data.polygons) == 0:
            # no foot band in this piece (the middle): a hidden keeper shell, a small box deep inside
            # its largest tower, so the piece still counts as shelled (modelPrep: with no shell the
            # model's own faces get ink, a rim round every tower)
            keeper_box(sp, dx, dy)
        sh = common.outline_shell(sp, coll, voxel=0.015, faces=3000, smooth=4, inside=0.006, islands="outer")
        sh.name = sh.data.name = f"{name}_outline"
        bpy.data.objects.remove(sp, do_unlink=True)
        shells.append(sh)
        g = glass_pieces[f"{name}_glass"]
        tris = sum(len(f.vertices) - 2 for o in (p, g) for f in o.data.polygons)
        total += tris
        print(f"{name}: {tris} tris")
        exports[name] = (p, g, sh)
    print("total tris", total)
    if "--pieces" in argv:  # piece-local glbs, for judging in the game's renderer (scratch only)
        pdir = Path(argv[argv.index("--pieces") + 1])
        for name, objs in exports.items():
            common.export_glb(list(objs), pdir / f"{name}.glb")
    if "--no-export" not in argv:
        for name, objs in exports.items():
            data = common.load_sprite(ROOT, name)
            common.export_sprite_model(ROOT, list(objs), f"enemies/{name}", data["sprites"])
    for name, dx, dy in lay:
        for o in exports[name]:
            o.location = (dx / 12, -dy / 12, 0)
    bpy.context.view_layer.update()
    bpy.data.objects.remove(sealed, do_unlink=True)
    for o in (obj, glass):
        o.hide_render = True
        o.hide_set(True)
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        common.export_glb(list(pieces.values()) + list(glass_pieces.values()) + shells, out)
        print("exported", out)
    if "--review" in argv:
        rv = Path(argv[argv.index("--review") + 1])
        rv.mkdir(parents=True, exist_ok=True)
        stats = {"tris": total, "pal": sorted({k[0] for k in MAT.slots}),
                 "apex": APEX, "hd": HD}
        (rv / "stats.json").write_text(json.dumps(stats))
        review(list(pieces.values()) + list(glass_pieces.values()), shells, rv)


# --------------------------------------------------------------------------------------------------
# Review renders
# --------------------------------------------------------------------------------------------------

def review(pieces, shells, out):
    scene = bpy.context.scene

    def cam(location, look_at, ortho=None, fov=None, top=False):
        data = bpy.data.cameras.new("cam")
        if ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.sensor_fit = "VERTICAL"
            data.angle_y = math.radians(fov)
        c = bpy.data.objects.new("cam", data)
        scene.collection.objects.link(c)
        c.location = location
        c.rotation_euler = (0, 0, 0) if top else (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
        return c

    def render(c, path, rx, ry):
        scene.camera = c
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(c, do_unlink=True)

    for s in shells:
        s.hide_render = True
    # flat top view for the IoU and region colours (unlit palette colours)
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_shadows = False
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    k = 8
    render(cam((0, 0, 20), (0, 0, 0), ortho=max(W, H) / 12, top=True), out / "top_flat.png", W * k, H * k)
    # the ortho camera's scale covers the larger side; make the frame W x H by using a square then crop
    # game-lit views
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "EEVEE" in e)
    world = scene.world or bpy.data.worlds.new("game")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.45, 0.55, 1.0)
    bg.inputs[1].default_value = 1.0
    sun_data = bpy.data.lights.new("game_sun", "SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("game_sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-6, -8.4, 20)).normalized().to_track_quat("Z", "Y").to_euler()
    # ink: an inverted hull from each outline shell (back faces only), as the game's OutlineEffect
    ink = bpy.data.materials.new("ink")
    ink.use_nodes = True
    bs = next(n for n in ink.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (0, 0, 0, 1)
    bs.inputs["Roughness"].default_value = 1.0
    ink.use_backface_culling = True
    hulls = []
    for s in shells:
        h = s.copy()
        h.data = s.data.copy()
        h.data.materials.clear()
        h.data.materials.append(ink)
        scene.collection.objects.link(h)
        bm = bmesh.new()
        bm.from_mesh(h.data)
        for v in bm.verts:
            v.co += v.normal * 0.045
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.to_mesh(h.data)
        bm.free()
        h.hide_render = False
        hulls.append(h)
    ext = max(W, H) / 12
    render(cam((0, 0, 20), (0, 0, 0), ortho=ext, top=True), out / "top_game.png", 600, 600)
    zc = HD / 2 * PX
    span = 7.0
    render(cam((30, 0, zc), (0, 0, zc), ortho=span), out / "side.png", 600, 360)
    render(cam((0, -30, zc), (0, 0, zc), ortho=span), out / "front.png", 600, 360)
    render(cam((0, 30, zc), (0, 0, zc), ortho=span), out / "rear.png", 600, 360)
    d = 16
    render(cam((d * 0.55, -d * 0.6, d * 0.55), (0, 0, 0.5), fov=35), out / "q1.png", 600, 600)
    render(cam((-d * 0.6, d * 0.5, d * 0.55), (0, 0, 0.5), fov=35), out / "q2.png", 600, 600)
    tilt = TILT
    render(cam((0, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0.6), fov=27), out / "game.png", 600, 600)
    render(cam((0, -d * 0.3, -d * 0.9), (0, 0, 0), fov=35), out / "under.png", 400, 400)


if __name__ == "__main__":
    main()
