"""Waterfall (newshh.shp, a 5 x 2 block of 24 x 28 pieces): a standing jungle cliff with a river over its lip.

WHAT IT IS: a river spilling over the lip of a standing jungle cliff into a plunge pool. Grey rock
buttresses flank the fall, bushes and rock rims frame the pool. Fixed scenery (enemies 739-744,
mv 0, armor 0), only the water animates (ani12, four phases).

HOW (D82 approach C, cross-sections first). The art draws the cliff extending up the screen, so the
model is the real standing cliff in assembly pixels (u east 0..120, v south 0..56 = plan row, z up),
drawn in the art's oblique view: a point (u, v, z) lands on screen row s = v - z (1 px up the screen
per px of height, `tyrian_oblique: 1`). Section through a fall column (u 12..104):

    z 33 . lip (glassy pal 56) rolling over the crest
         |\\  curtain of 1 px strands, a ballistic arc v = 33.5 + T sqrt((33.2 - z)/33.2), T ~ 6.4
         | \\    (each strand pixel of the frame placed where its screen row meets the arc)
    rear  |  \\
    45 deg| wet rock face (pal 1) at v 33.3, seen through the strand gaps
    slope |    \\__ foam ridge (pal 53) v 38..46, splash mounds, sparkles per phase
    ______|________\\________________ pool (pal 54) z 0 to v 56
          closed flat base z -4

The rear slope is exactly edge-on to the oblique view (s = 0), so the whole cliff, buttresses
included, projects inside the sprite rectangle, and the plan footprint is the sprite rectangle too.
The buttresses are the same lofted ridge with their faces stepped forward (foot v 41 left, 45 right)
and taller (35.5 / 41.5 px), their lit tops being the first 6.5 / 4.5 rows of the art; the right
one turns to the water in a south-west face (the art's shadowed band).

Exported upright (D165): the model is the real cliff, `tyrian_oblique` 1 and `tyrian_depth_band`
[0, 0.4, 0, 3.5] on every node (outline shell included) make the game draw it in the art's view,
under background 2 and over nothing it should not cover. It is cut per piece by the ART's footprint
(a vertical plane per column, the 45 degree plane s = v - z per row), so each sprite's animation
frames own the water the art paints over it, and exported through the sprite-model contract:
public/models/enemies/<piece>.glb and src/render/spriteModels/<piece>.json, one assembly of six.
newshh-129 and newshh-205 appear three times side by side: noise along u has period 24 so one cut tiles.

Run: blender --background --python assets/blender/enemies/assembly-newshh-129.py [-- --scratch dir]
(--scratch dir: also writes the measure inputs and the review renders there)
"""

import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newshh-129"
WT = common.repo_root(__file__)
PX = 1 / 12
OVERLAP = 0.6   # px by which neighbouring pieces overlap at their seams
BAND = [0.0, 0.4, 0.0, 3.5]   # tyrian_depth_band: under background 2 (D165), the 3.5 unit cliff squeezed in
W, H = 120, 56
PIECES = ["newshh-117", "newshh-129", "newshh-153", "newshh-157", "newshh-205", "newshh-207"]
CYCLES = {
    "newshh-117": [165, 234, 240, 117], "newshh-129": [167, 236, 242, 129], "newshh-153": [169, 238, 244, 153],
    "newshh-157": [203, 272, 278, 157], "newshh-205": [205, 274, 280, 267], "newshh-207": [207, 276, 282, 269],
}
CX0, CY0 = 128, 25
CREST = 33.2          # top of the fall's rock lip
FACE_V = 33.3         # wet rock face behind the curtain
BASE = -4.0           # closed flat underside
FALL_U0, FALL_U1 = 12.5, 104.5
RIVER_U0, RIVER_U1 = 12.0, 105.0   # the river channel on the cliff top (only the buttress tops stay rock)
WATER_GLOW, ROCK_GLOW, LEAF_GLOW = 0.4, 0.0, 0.25   # emission strengths (D126)
# ROCK_GLOW stays 0: the sprite's rock is dark (tops index 6 = RGB 81 and 4 = 52, faces 3 = 40), and lit
# it renders about its palette grey with its relief; a glow (palette x strength replacing the lit colour)
# only flattened it (median 37 lit -> 33 at 1.0, fix round 2).
BACK_IDX, BACK_GLOW = 52, 0.8   # the water sheet behind the strands: dark, but blue, never black


# --- sprite -------------------------------------------------------------------------------------

def composite():
    """Per phase: {(col,row): index}, the frames shown, colours (same layout as the shipped script)."""
    base = common.load_sprite(WT, PIECES[0])
    colors, phases, shown = {}, [], []
    datas = {n: common.load_sprite(WT, n) for n in PIECES}
    for d in datas.values():
        colors.update(d["colors"])
    for ph in range(4):
        px, fr = {}, {}
        for e in base["assemblyLayout"]:
            n = e["model"]
            if n not in PIECES:
                continue
            idx = int(e["frame"].split("|")[-1])
            cyc = CYCLES[n]
            idx = cyc[(cyc.index(idx) + ph) % 4]
            fr[n] = idx
            f = next(f for f in datas[n]["frames"] if f["index"] == idx)
            c0, r0 = e["cx"] - 12 - (CX0 - W // 2), e["cy"] - 14 - (CY0 - H // 2)
            for r, row in enumerate(f["pixels"]):
                for c, v in enumerate(row):
                    if 0 <= c0 + c < W and 0 <= r0 + r < H:
                        px[(c0 + c, r0 + r)] = v
        phases.append(px)
        shown.append(fr)
    base["colors"] = colors
    return base, phases, shown


# --- coordinates and noise ----------------------------------------------------------------------

def P(u, v, z):
    """Assembly px -> Blender units (origin at the block centre, +Y north)."""
    return Vector(((u - W / 2) / 12, (H / 2 - v) / 12, z / 12))


def hsh(i, j=0.0, k=0.0):
    x = math.sin(i * 127.1 + j * 311.7 + k * 74.7) * 43758.5453
    return x - math.floor(x)


def vnoise(x, y, seed=0.0):
    """Smooth value noise in -1..1."""
    xi, yi = math.floor(x), math.floor(y)
    fx, fy = x - xi, y - yi
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = hsh(xi, yi, seed), hsh(xi + 1, yi, seed)
    c, d = hsh(xi, yi + 1, seed), hsh(xi + 1, yi + 1, seed)
    return 2 * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy) - 1


def vnu(u, scale, y, seed=0.0):
    """vnoise along u (in units of `scale`) with period 24 px, so the three copies of newshh-129 and of
    newshh-205 are the same cut and tile: a crossfade of the noise across one period."""
    w = (u - 24.0) % 24.0
    t = w / 24.0
    return (1 - t) * vnoise((24.0 + w) / scale, y, seed) + t * vnoise(w / scale, y, seed)


def interp(prof, t):
    if t <= prof[0][0]:
        return prof[0][1]
    for (t0, a), (t1, b) in zip(prof, prof[1:]):
        if t <= t1:
            return a + (b - a) * (t - t0) / (t1 - t0)
    return prof[-1][1]


class Mats:
    def __init__(self, sprite, settings):
        self.sprite, self.settings, self.list, self.slots = sprite, settings, [], {}

    def __call__(self, index, variant=""):
        key = (index, variant)
        if key not in self.slots:
            kw = self.settings(index, variant)
            self.list.append(common.palette_material(self.sprite, index, "nshh129" + variant, **kw))
            self.slots[key] = len(self.list) - 1
        return self.slots[key]


def mat_settings(i, variant=""):
    if variant == "foam":   # churned white water: matte, so no ruler-straight specular lines
        return {"metallic": 0.0, "roughness": 0.6, "emission_strength": WATER_GLOW}
    if variant == "back":   # the sheet of water behind the strands (and on the shelf at their feet)
        return {"metallic": 0.0, "roughness": 0.5, "emission_strength": BACK_GLOW}
    if variant == "lip":    # the river rolling over the crest: soft sheen, no ruled specular rail
        return {"metallic": 0.0, "roughness": 0.55, "emission_strength": WATER_GLOW}
    if variant == "matte":
        return {"metallic": 0.0, "roughness": 0.95, "emission_strength": 0.0}
    if variant == "flow":   # the river on the cliff top: rippled, not a mirror
        return {"metallic": 0.0, "roughness": 0.3, "emission_strength": WATER_GLOW}
    if 48 <= i <= 62:   # water: glows part way (D126) so the lit view holds the sprite's luma
        return {"metallic": 0.0, "roughness": 0.12, "emission_strength": WATER_GLOW}
    if i <= 12:
        return {"metallic": 0.0, "roughness": 0.85, "emission_strength": ROCK_GLOW}
    return {"metallic": 0.0, "roughness": 0.7, "emission_strength": LEAF_GLOW}


# --- the ridge: cliff, buttresses and rear slope as one lofted solid ---------------------------
# Per column u: front foot v_f, face top z_t, top z_top. The lit top spans screen rows 0..(v_f-z_t).

FOOT = [(0, 41.0), (4.0, 41.0), (5.0, 38.0), (6.0, 37.0), (7.0, 36.2), (8.0, 35.4), (9.0, 34.6),
        (10.0, 34.0), (11.0, 33.6), (12.0, 33.4), (12.6, FACE_V), (104.4, FACE_V), (105.0, 33.6),
        (106.0, 34.0), (108.0, 35.0), (110.0, 36.4), (111.0, 37.8), (112.0, 41.0), (113.0, 44.0),
        (114.0, 45.0), (120, 45.0)]
TOPROWS = [(0, 6.5), (11.5, 6.5), (12.3, 0.0), (104.6, 0.0), (106.0, 0.3), (107.5, 1.0), (108.5, 4.5), (120, 4.5)]
TOPZ = [(0, 35.5), (4, 35.5), (9, 35.0), (11.8, 34.6), (12.3, CREST), (104.6, CREST), (105.5, 34.5),
        (110, 38.5), (113, 41.5), (120, 41.5)]


def column_profile(u):
    """(v, z, role) points from the back foot over the top to the front foot (role per segment)."""
    vf, rows, ztop = interp(FOOT, u), interp(TOPROWS, u), interp(TOPZ, u)
    zt = min(vf - rows, ztop)
    vb = ztop + 0.15  # rear edge on screen row ~0
    pts = [(0.15, BASE, "rear"), (0.15, 0.0, "rear")]
    nrear = 40
    river = in_river(u)
    for k in range(1, nrear):  # rear slope, edge-on to the art view
        t = k / nrear
        v = 0.15 + (vb - 0.15) * t
        fade = min(1.0, t * 6, (1 - t) * 8)
        if river:
            # the river running up to the lip: a sunken, rippled sheet with flow ribs along it
            rib = 0.22 * vnu(u, 1.1, v / 11.0, 43.0) + 0.1 * vnu(u, 0.5, v / 4.0, 44.0)
            pts.append((v, max(0.0, ztop * t - (0.55 - rib) * fade), "rear"))
        else:
            # buttress backs: irregular strata (bed height and offset vary along u), ragged ledges
            bed = 3.6 + 1.6 * (0.5 + 0.5 * vnu(u, 7.0, 0.7, 45.0))
            x = v / bed + 0.9 * vnu(u, 4.5, 0.2, 14.0) + 0.35 * vnu(u, 1.6, v / 6.0, 46.0)
            f = x - math.floor(x)
            depth = 0.6 + 1.1 * hsh(math.floor(x), math.floor((u + 3.0 * vnu(u, 5.0, 0.1, 47.0)) / 5.5), 48.0)
            notch = depth * f * f * fade
            crack = sum(0.7 * math.exp(-((u - cu) / 0.3) ** 2) for cu in (3.1, 8.3, 107.2, 112.9, 116.6)
                        if hsh(cu, math.floor(x), 49.0) < 0.6)
            pts.append((v, max(0.0, ztop * t - notch - crack * fade), "rear"))
    # top: from the rear edge over a rounded shoulder to the face top
    for k in range(0, 6):
        t = k / 5
        v = vb + (vf - vb) * (1 - (1 - t) ** 1.6)
        z = ztop + (zt - ztop) * t ** 1.8
        pts.append((v, z, "top"))
    # face, top to foot, finer
    nface = 40
    for k in range(1, nface + 1):
        t = k / nface
        z = zt * (1 - t)
        pts.append((vf + 0.35 * t ** 3, z, "face"))
    pts.append((vf + 0.35, BASE, "face"))
    return pts


def terrace(u, z):
    """The buttress face as layered rock (B's look on A's height): strata about 7 px tall, each leaning
    back as it rises and jutting out again over the one below, so every bed casts a dark lip, and a few
    cracks down the face. Returns px along +v (toward the viewer at the foot); zero net over a bed, so
    the foot and the lit top stay where the art has them."""
    bed = 7.0 + 1.4 * vnu(u, 9.0, 2.0, 21.0)
    t = z / bed
    f = t - math.floor(t)
    r = min(1.0, max(0.0, (f - 0.72) / 0.28))
    saw = 0.35 * f + 0.65 * r * r * (3 - 2 * r)
    crack = 0.0
    for cu in (2.4, 9.6, 106.8, 111.6, 117.4):
        w = 0.28 + 0.1 * vnoise(z / 3.0, cu, 22.0)
        crack -= 0.55 * math.exp(-((u - cu - 0.5 * vnoise(z / 5.0, cu, 23.0)) / w) ** 2)
    ragged = 0.22 * vnoise(u / 0.7, z / 1.3, 24.0) * (1.0 - r)
    return -0.6 * saw + crack + ragged   # softer beds: at 0.9 they drew a brick stair-step in game


def face_disp(u, z, v):
    """Relief across the rock face (px, along +v): jointed columns, ribs and a lit rib where the art
    paints one (left col 6-8, right col 113-115), a groove (left col 3-5)."""
    d = 0.45 * vnu(u, 2.2, z / 5.0, 1.0) + 0.25 * vnu(u, 0.9, z / 1.6, 2.0)
    if u < FALL_U0 or u > FALL_U1:
        d += terrace(u, z)
    if u < FALL_U0:
        d += 0.9 * math.exp(-((u - 7.2) / 1.1) ** 2) - 0.6 * math.exp(-((u - 4.0) / 1.0) ** 2)
    elif u > FALL_U1:
        d += 0.7 * math.exp(-((u - 114.2) / 1.0) ** 2)
    else:
        d = 0.35 * vnu(u, 1.5, z / 3.0, 3.0)  # wet rock behind the curtain: smoother, darker
    return d


def in_river(u):
    """Columns of the river channel on the cliff top (between the buttresses)."""
    return RIVER_U0 <= u <= RIVER_U1


def flow_index(u, v):
    """The river's water: long streaks running to the lip (bands along u, slow along v), no pixel blocks."""
    n = vnu(u, 1.7, v / 9.0, 41.0) + 0.35 * vnu(u, 0.8, v / 5.0, 42.0)
    return 57 if n > 0.55 else 56 if n > 0.15 else 55 if n > -0.35 else 54


def rock_index(u, s, role):
    """The sprite's palette index for the region (trimmed medians): plain stone, one index per region;
    the strata and cracks are geometry, never colour patches (a pixel mosaic reads as low-res)."""
    if role == "rear":
        return 3
    if FALL_U0 <= u <= FALL_U1:
        return 4 if role == "top" else 1
    if role == "top":
        return 6 if u < 60 else 4
    if u < 60:
        return 3
    return 2 if u < 111 else 3


def ridge(bm, M):
    us = [0.0]
    while us[-1] < 120:
        u = us[-1]
        step = 0.5 if (u < 16 or u > 101) else 1.0
        us.append(min(120.0, u + step))
    rings, roles = [], None
    for u in us:
        prof = column_profile(u)
        roles = [p[2] for p in prof]
        ring = []
        for i, (v, z, role) in enumerate(prof):
            uu, vv, zz = u, v, z
            if role == "face" and z > -0.5:
                vv += face_disp(u, z, v)
                uu += 0.2 * vnu(u, 1.3, z / 2.0, 4.0) if 0 < u < 120 else 0
            elif role == "top":
                # broken rock, not a slab: two octaves of relief over the buttress tops
                rough = 0.0 if FALL_U0 + 1 <= u <= FALL_U1 - 1 else 1.0
                zz += 0.35 * vnu(u, 1.8, v / 1.8, 5.0) + rough * (0.55 * vnu(u, 2.6, v / 2.4, 52.0)
                                                             + 0.3 * vnu(u, 0.9, v / 0.9, 53.0))
                for cu in (3.6, 7.9, 108.4, 113.2, 117.0):   # cracks across the buttress tops
                    zz -= 0.55 * math.exp(-((u - cu - 0.6 * vnoise(v / 2.0, cu, 50.0)) / 0.32) ** 2)
            elif role == "rear" and 0 < z < 30 and not in_river(u):
                zz -= 0.6 * abs(vnu(u, 3.0, v / 3.0, 6.0))
            ring.append(bm.verts.new(P(uu, vv, zz)))
        rings.append((u, ring))
    n = len(rings[0][1])
    for (u0, r0), (u1, r1) in zip(rings, rings[1:]):
        for i in range(n - 1):
            f = bm.faces.new((r0[i], r1[i], r1[i + 1], r0[i + 1]))
            role = roles[i + 1] if roles[i] != roles[i + 1] else roles[i]
            c = f.calc_center_median()
            uc, vc, zc = c.x * 12 + W / 2, H / 2 - c.y * 12, c.z * 12
            if role == "face" and FALL_U0 <= uc <= FALL_U1:
                f.material_index = M(BACK_IDX, "back")   # water sheet behind the strands, not black rock
                f.smooth = True
            elif role == "rear" and in_river(uc) and zc > 0.2:
                f.material_index = M(flow_index(uc, vc), "flow")
                f.smooth = True
            else:
                f.material_index = M(rock_index(uc, (vc - zc) if role != "rear" else vc / 3.0, role))
                f.smooth = False
        # bottom
        f = bm.faces.new((r0[n - 1], r1[n - 1], r1[0], r0[0]))
        f.material_index = M(2)
    # end caps
    for u, ring in (rings[0], rings[-1]):
        f = bm.faces.new(ring if u == 0 else list(reversed(ring)))
        f.material_index = M(3)


# --- the pool, foam ridge and banks: a closed slab --------------------------------------------

def rim_left(v):
    return interp([(33, 4.0), (41, 4.6), (46, 5.4), (50, 7.6), (53.5, 11.0), (56, 13.8)], v)


def rim_right(v):
    return interp([(33, 116.0), (41, 113.4), (46, 113.2), (50, 111.0), (53.5, 107.2), (56, 104.6)], v)


def foam_h(u, v):
    """Foam ridge where the curtain lands (screen rows ~37-45) with splash mounds."""
    vc = 41.2 + 1.1 * vnu(u, 5.0, 0.3, 60.0)          # the band wanders, it is not a ruled line
    amp = 1.3 + 0.5 * vnu(u, 2.6, 0.6, 61.0)
    ridge_ = amp * math.exp(-((v - vc) / (2.4 + 0.5 * vnu(u, 3.5, 0.9, 62.0))) ** 2)
    splash = 0.9 * max(0.0, vnu(u, 1.2, v / 1.1, 7.0)) * math.exp(-((v - vc + 0.6) / 2.8) ** 2)
    edge = min(1.0, max(0.0, (u - 3) / 3), max(0.0, (115 - u) / 3))
    return (ridge_ + splash) * edge


def pool_h(u, v):
    return 0.6 + 0.07 * vnu(u, 2.2, v / 2.0, 8.0) + 0.04 * vnu(u, 1.0, v / 1.0, 9.0)


def surface(u, v):
    """(height, palette index, smooth) of the slab top at plan (u, v)."""
    if u < rim_left(v) or u > rim_right(v):
        return 1.2 + 0.25 * vnu(u, 2, v / 2, 10.0), 3, False, ""   # earth bank under the bushes
    if v < 38.4 and FALL_U0 - 1 < u < FALL_U1 + 1:
        return 0.15 + 0.2 * vnu(u, 1.5, v, 11.0), BACK_IDX, True, "back"   # water at the strands' feet
    fh, ph = foam_h(u, v), pool_h(u, v)
    z = max(fh, ph)
    if fh > 0.25:
        n = vnu(u, 1.6, v / 1.6, 63.0)
        return z, (56 if n > 0.6 else 55 if n > 0.25 else 53), True, "foam"   # base 53, as the art
    m = vnu(u, 2.6, v / 2.2, 64.0) + 0.4 * vnu(u, 1.2, v / 1.1, 65.0)   # mottled pool, blotches not pixels
    return z, (55 if m > 0.6 else 53 if m < -0.55 else 54), True, ""


def slab(bm, M):
    us = [k * 0.5 for k in range(241)]
    vs = [33.0 + k * 0.5 for k in range(46)] + [55.9]   # front inside the art's last row: no cut, no cap
    grid = {}
    for i, u in enumerate(us):
        for j, v in enumerate(vs):
            z = surface(u, v)[0]
            grid[(i, j)] = bm.verts.new(P(u, v, z))
    for i in range(len(us) - 1):
        for j in range(len(vs) - 1):
            f = bm.faces.new((grid[(i, j)], grid[(i, j + 1)], grid[(i + 1, j + 1)], grid[(i + 1, j)]))
            z, idx, sm, var = surface((us[i] + us[i + 1]) / 2, (vs[j] + vs[j + 1]) / 2)
            f.material_index = M(idx, var)
            # the rim rows stay flat: smoothed into the skirt's normals they drew a bright ruled line
            f.smooth = sm and 0 < i < len(us) - 2 and 0 < j < len(vs) - 2
    # skirt + flat base (closed, no detail)
    ring = [grid[(i, 0)] for i in range(len(us))] + [grid[(len(us) - 1, j)] for j in range(1, len(vs))]
    ring += [grid[(i, len(vs) - 1)] for i in range(len(us) - 2, -1, -1)] + [grid[(0, j)] for j in range(len(vs) - 2, 0, -1)]
    low = [bm.verts.new((v.co.x, v.co.y, 0.0)) for v in ring]   # the pool sits on the ground (z 0)
    for k in range(len(ring)):
        a, b = ring[k], ring[(k + 1) % len(ring)]
        f = bm.faces.new((a, b, low[(k + 1) % len(ring)], low[k]))
        f.material_index = M(53, "matte")   # the skirt: matte dark water (glossy, it drew a bright ruled line)
    f = bm.faces.new(list(reversed(low)))
    f.material_index = M(2)


# --- rims, bushes ----------------------------------------------------------------------------

def rock_lump(bm, M, u, v, z, rx, ry, rz, idx, seed):
    """A faceted stone: a jittered low-poly ellipsoid, flat shaded (lit facets, D148)."""
    res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    for vert in res["verts"]:
        x, y, w = vert.co
        j = 1 + 0.22 * (hsh(x * 3 + seed, y * 3, w * 3) - 0.5)
        vert.co = P(u + x * rx * j, v - y * ry * j, z + max(w, -0.3) * rz * j)
    for f in {f for vert in res["verts"] for f in vert.link_faces}:
        f.material_index = M(idx)
        f.smooth = False


def leaf(bm, M, u, v, z, rx, ry, rz, idx, seed):
    """A leafy clump: a smooth lumpy dome (subdivided, lobed), smooth shaded."""
    res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for vert in res["verts"]:
        x, y, w = vert.co
        j = 1 + 0.18 * vnoise(x * 2.2 + seed, y * 2.2 + w * 1.7, 17.0)
        vert.co = P(u + x * rx * j, v - y * ry * j, z + max(w, -0.25) * rz * j)
    for f in {f for vert in res["verts"] for f in vert.link_faces}:
        f.material_index = M(idx)
        f.smooth = True


def stone(bm, M, u, v, z, rx, ry, rz, idx, seed):
    """A rounded boulder of the pool's rim: a smooth subdivided ellipsoid, softly lumpy (B's rim stones;
    the faceted lumps of the first cut read as spikes)."""
    res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for vert in res["verts"]:
        x, y, w = vert.co
        j = 1 + 0.12 * vnoise(x * 1.6 + seed, y * 1.6 + w * 1.3, 18.0)
        vert.co = P(u + x * rx * j, v - y * ry * j, z + max(w, -0.35) * rz * j)
    for f in {f for vert in res["verts"] for f in vert.link_faces}:
        f.material_index = M(idx)
        f.smooth = True


def rims(bm, M):
    """Rounded stones along the pool's two rock rims, overlapping into a continuous kerb."""
    for path, seed in (([(4.6, 40.5), (5.0, 44.0), (5.8, 47.0), (7.6, 50.2), (10.4, 53.0), (13.0, 55.4)], 1.0),
                       ([(113.6, 40.0), (113.4, 43.5), (113.0, 46.5), (111.0, 50.0), (107.6, 53.2), (105.2, 55.6)], 2.0)):
        pts = []
        for (u0, v0), (u1, v1) in zip(path, path[1:]):
            n = max(1, int(math.hypot(u1 - u0, v1 - v0) / 2.4))
            pts += [(u0 + (u1 - u0) * k / n, v0 + (v1 - v0) * k / n) for k in range(n)]
        pts.append(path[-1])
        for k, (u, v) in enumerate(pts):
            r = 1.9 + 0.6 * hsh(k, seed)
            idx = 3 if hsh(k, seed, 1) < 0.65 else (4 if hsh(k, seed, 2) < 0.6 else 2)
            stone(bm, M, u, v + 0.8, 0.5, r, r * 0.95, 1.5 + 0.6 * hsh(k, seed, 3), idx, k + seed * 10)


LIT_GREEN = {32: 33, 33: 34, 34: 193, 35: 193, 36: 194, 192: 193, 193: 194, 194: 195, 195: 197, 197: 197}


def bushes(bm, M, px):
    """Leafy clumps on the green pixels of the art: each a cluster of three lumpy lobes with a lit tuft
    on top, in the sprite's own local green, spaced about 2 px so they overlap into foliage."""
    green = {(c, r) for (c, r), v in px.items() if 32 <= v <= 36 or v >= 192}
    cand = sorted(green, key=lambda cr: (hsh(cr[0], cr[1], 31.0)))
    placed = []
    for c, r in cand:
        if r < 30:
            continue
        if any((c - pc) ** 2 + (r - pr) ** 2 < 2.1 ** 2 for pc, pr in placed):
            continue
        placed.append((c, r))
    for k, (c, r) in enumerate(placed):
        cu, cs = c + 0.5, r + 0.5
        vals = sorted(px[(c + dc, r + dr)] for dc in range(-2, 3) for dr in range(-2, 3)
                      if (c + dc, r + dr) in green)
        idx = vals[len(vals) // 2]
        if idx not in (32, 33, 34, 35, 36, 192, 193, 194, 195, 197):
            idx = 34
        vine = cs < 41 and cu > 100  # creeper on the right face
        if vine:
            v_face = interp(FOOT, cu) + face_disp(cu, 2, 0) + 0.5
            z = v_face - cs
            leaf(bm, M, cu, v_face, z, 1.1, 0.7, 1.1, 34, 50 + k)
            continue
        rad = 1.8 + 0.6 * hsh(k, 3)
        h = 2.6 + 0.9 * hsh(k, 4)
        v = cs + 1.0 + h * 0.5   # the lobe's top centre lands on the green pixel
        leaf(bm, M, cu, v, 1.0, rad * 1.2, rad * 1.1, h, idx, 70 + k)
        for a in (0.0, 2.1, 4.2):   # side lobes
            ang = a + 3.0 * hsh(k, 5)
            leaf(bm, M, cu + 0.8 * rad * math.cos(ang), v + 0.7 * rad * math.sin(ang), 1.0,
                 rad * 0.65, rad * 0.6, h * 0.7, idx if hsh(k, a, 6) < 0.6 else LIT_GREEN[idx], 110 + k)
        leaf(bm, M, cu - 0.4, v - 0.5, 1.0 + h * 0.62, rad * 0.6, rad * 0.55, h * 0.35, LIT_GREEN[idx], 90 + k)


# --- the curtain (per phase) -------------------------------------------------------------------

def throw(c):
    return 6.4 + 0.7 * vnu(c, 2.5, 0.5, 12.0)


def curtain_v(c, z):
    return FACE_V + 0.25 + throw(c) * math.sqrt(max(0.0, (CREST - z) / CREST))


def z_at(c, s):
    """Height where column c's curtain meets screen row s (bisection on v(z) - z = s)."""
    lo, hi = -1.0, CREST
    for _ in range(40):
        mid = (lo + hi) / 2
        if curtain_v(c, mid) - mid > s:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def s_foot(c):
    return curtain_v(c, 0.0)


SECTION = [(-0.6, 0.0), (-0.35, 0.32), (0.35, 0.32), (0.6, 0.0), (0.35, -0.22), (-0.35, -0.22)]


def strand(bm, M, c, rows):
    """One strand: rings at each pixel-row edge on the arc; each band takes its pixel's index. The
    strand's relief follows its brightness: bright runs stand out as raised, wider ribs, dark ones sink
    back (a ribbed curtain, not a flat sheet of pixel blocks)."""
    u = c + 0.5
    ring_list = []
    lum = [(i - 48) / 14.0 for _, i in rows]
    for n, (s, idx) in enumerate(rows + [(rows[-1][0] + 1, None)]):
        b = (lum[max(0, n - 1)] + lum[min(len(lum) - 1, n)]) / 2   # brightness at this ring
        if 0 < n < len(rows):   # smooth over 3 rows so ribs swell, not step
            b = 0.5 * b + 0.25 * (lum[max(0, n - 2)] + lum[min(len(lum) - 1, n + 1)])
        z = z_at(c, s)
        v = curtain_v(c, z)
        dz = 0.05
        dv = curtain_v(c, z - dz) - v
        t = Vector((0.0, dv, -dz)).normalized()           # down the arc (u, v, z)
        nrm = Vector((0.0, -t.z, t.y)).normalized()        # out of the curtain
        if nrm.y < 0:
            nrm = -nrm
        wob = 0.12 * vnu(c, 1.4286, s / 4.0, 13.0)
        wide, push, thick = 0.8 + 0.35 * b, -0.35 + 1.3 * b, 0.7 + 1.0 * b
        ring = []
        for a, h in SECTION:
            h = h * thick + push
            ring.append(bm.verts.new(P(u + a * wide + wob, v + nrm.y * h, z + nrm.z * h)))
        ring_list.append((ring, idx))
    for (r0, idx), (r1, _) in zip(ring_list, ring_list[1:]):
        m = M(idx)
        for i in range(len(SECTION)):
            j = (i + 1) % len(SECTION)
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index, f.smooth = m, True
    for ring, idx in (ring_list[0], ring_list[-1]):
        f = bm.faces.new(ring if ring is ring_list[0][0] else list(reversed(ring)))
        f.material_index = M(rows[0][1] if ring is ring_list[0][0] else rows[-1][1])


def curtain(bm, M, px):
    for c in range(int(FALL_U0) , int(FALL_U1) + 1):
        foot = int(s_foot(c))
        run = []
        for s in range(LIP_ROWS, foot + 1):   # the first rows start inside the static lip
            v = px.get((c, s), -1)
            if 48 <= v <= 62:
                # a 3-row median down the column: the streaks keep their runs (and each frame its own
                # pattern), the isolated single-pixel flecks that read as a block mosaic go
                nb = sorted(x for x in (px.get((c, s - 1), -1), v, px.get((c, s + 1), -1)) if 48 <= x <= 62)
                run.append((s, nb[len(nb) // 2]))
                continue
            if len(run) >= 1:
                strand(bm, M, c, run)
            run = []
        if run:
            strand(bm, M, c, run)


def sparkles(bm, M, px):
    """The foam band and the pool's glints (per phase): a bubble on every bright pixel of the band at the
    foot of the falls (dense, as the art), sparser glints on the pool below it."""
    for (c, s), v in px.items():
        if s < 36 or v > 62 or v < (57 if s <= 47 else 59):
            continue
        u = c + 0.5
        if u < rim_left(s + 1) or u > rim_right(s + 1):
            continue
        if FALL_U0 <= u <= FALL_U1 and s < s_foot(c):
            continue
        # surface point whose screen row is s + 0.5
        vv = s + 0.5
        for _ in range(6):
            vv = s + 0.5 + surface(u, vv)[0]
        z = surface(u, vv)[0]
        r = 0.42 + 0.05 * (v - 57) + 0.12 * hsh(c, s, 66.0)
        rock_lump(bm, M, u, vv, z + 0.05, r, r, 0.35 + 0.08 * (v - 57), v, c * 7 + s)


LIP = [(30.2, 29.75), (31.6, 31.25), (32.7, 32.6), (33.5, 33.55), (34.3, 33.75), (34.95, 33.45),
       (35.35, 32.85), (35.4, 32.3), (35.1, 31.95), (34.4, 31.8), (33.4, 31.6), (31.8, 30.6)]


LIP_ROWS = 2


def lip(bm, M):
    """The river rolling over the crest (static): a closed, rounded tube of glassy water from the river
    sheet over the edge and down the first 2-3 screen rows of the fall, so the strands start inside it
    (no comb of strand ends along the lip). Its front bulges a little where the fall's bright columns
    leave it (ribs), and the ends are tapered into the buttresses."""
    us = [RIVER_U0 - 0.3 + k * 0.5 for k in range(int((RIVER_U1 - RIVER_U0 + 0.6) / 0.5) + 1)]
    cv = sum(v for v, _ in LIP) / len(LIP)
    cz = sum(z for _, z in LIP) / len(LIP)
    rings = []
    for u in us:
        end = min(1.0, (u - us[0]) / 1.2, (us[-1] - u) / 1.2)
        k = 0.55 + 0.45 * max(0.0, end)
        bulge = 0.18 * vnu(u, 1.3, 0.4, 51.0)
        ring = []
        for i, (v, z) in enumerate(LIP):
            front = 1.0 if 3 <= i <= 8 else 0.0
            ring.append(bm.verts.new(P(u, cv + (v - cv) * k + front * bulge, cz + (z - cz) * k)))
        rings.append(ring)
    m = M(56, "lip")   # rippled, not a mirror: glossy, the tube's highlight drew a rail along the crest
    n = len(LIP)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r1[i], r1[j], r0[j]))
            f.material_index, f.smooth = m, True
    for ring in (rings[0], list(reversed(rings[-1]))):
        f = bm.faces.new(ring)
        f.material_index, f.smooth = m, True


# --- build, cut per piece, export --------------------------------------------------------------

def to_obj(name, bm, M, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in M.list:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def tag_view(o):
    """The glTF extras of the art's view (src/render/obliqueView.ts, D165): the upright model drawn at
    one px up the screen per px of height, its depth squeezed into the band, on every node."""
    o["tyrian_oblique"] = 1.0
    o["tyrian_depth_band"] = list(BAND)
    return o


def build():
    sprite, phases, shown = composite()
    coll = common.reset_collection(NAME)
    M = Mats(sprite, mat_settings)
    bm = bmesh.new()
    ridge(bm, M)
    slab(bm, M)
    rims(bm, M)
    bushes(bm, M, phases[0])
    static = to_obj(NAME + "-static", bm, M, coll)
    lbm = bmesh.new()   # its own object, cut without caps: capped, the overlapping seams drew notches
    lip(lbm, M)
    lipo = to_obj(NAME + "-lip", lbm, M, coll)
    waters = []
    for k, px in enumerate(phases):
        wbm = bmesh.new()
        curtain(wbm, M, px)
        sparkles(wbm, M, px)
        waters.append(to_obj(f"{NAME}-water-{k}", wbm, M, coll))
    return sprite, phases, shown, (static, lipo), waters, coll


def layout():
    """{piece: (col0, row0)}: the top-left of the piece's first appearance in the block, in assembly px."""
    base = common.load_sprite(WT, PIECES[0])
    out = {}
    for e in base["assemblyLayout"]:
        if e["model"] in PIECES and e["model"] not in out:
            out[e["model"]] = (e["cx"] - 12 - (CX0 - W // 2), e["cy"] - 14 - (CY0 - H // 2))
    return out


def all_entries():
    """Every appearance of every piece in the block: [(piece, col0, row0)]."""
    base = common.load_sprite(WT, PIECES[0])
    return [(e["model"], e["cx"] - 12 - (CX0 - W // 2), e["cy"] - 14 - (CY0 - H // 2))
            for e in base["assemblyLayout"] if e["model"] in PIECES]


def split_art(obj, name, c0, r0, coll, caps=True):
    """The part of `obj` the ART draws over the 24 x 28 px box at (c0, r0): vertical planes at its two
    columns, and the 45 degree planes s = v - z = r0 and r0 + 28 (a point at plan row v and height z is
    drawn at screen row v - z) for its rows, the cut faces filled (edge-on in the art's view). The result
    is moved so the box's centre, on the ground, is the origin, as common.split_assembly does."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    e = OVERLAP / 12   # shared seams overlap, so no crack opens where the pieces' edges differ
    el, er = (e if c0 > 0 else 0.0), (e if c0 + 24 < W else 0.0)
    et, eb = (e if r0 > 0 else 0.0), (e if r0 + 28 < H else 0.0)
    x0, x1 = (c0 - W / 2) / 12 - el, (c0 + 24 - W / 2) / 12 + er
    a, b = (H / 2 - r0) / 12 + et * 1.41, (H / 2 - r0 - 28) / 12 - eb * 1.41   # y + z <= a, y + z >= b
    k = 1 / math.sqrt(2)
    for co, no in (((x0, 0, 0), (-1, 0, 0)), ((x1, 0, 0), (1, 0, 0)),
                   ((0, a, 0), (0, k, k)), ((0, b, 0), (0, -k, -k))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges and caps:   # water strands stay open: their ends sit inside the neighbour's overlap
            new = bmesh.ops.holes_fill(bm, edges=edges, sides=0)["faces"]
            newset = set(new)
            for f in new:   # a cap wears the material of the visible surface it closes: the most common
                nb = [o.material_index for e in f.edges for o in e.link_faces   # neighbour, not the base
                      if o not in newset and o.normal.z > -0.5]
                if nb:
                    f.material_index = max(set(nb), key=nb.count)
    bmesh.ops.translate(bm, vec=(-(c0 + 12 - W / 2) / 12, -(H / 2 - r0 - 14) / 12, 0), verts=bm.verts)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in obj.data.materials:
        mesh.materials.append(m)
    piece = bpy.data.objects.new(name, mesh)
    coll.objects.link(piece)
    return piece


def trim_shell(shell, c0, r0):
    """No ink along the cut planes (the block's own rectangle: the art has none, the cliff runs on into
    the jungle's tiles; and the seams between pieces, which drew a line across the fall), nor along the
    river's lip (ink there drew a comb over the top of the curtain)."""
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    lim = 1.0 - 0.06
    drop = []
    for f in bm.faces:
        c = f.calc_center_median()
        u, v, z = c.x * 12 + c0 + 12, r0 + 14 - c.y * 12, c.z * 12
        if abs(c.x) > lim or abs(c.y + c.z) > 14 / 12 - 0.08 \
                or (RIVER_U0 - 1.0 < u < RIVER_U1 + 1.0 and z > 26.0 and v > 26.0):
            drop.append(f)
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.to_mesh(shell.data)
    bm.free()


def make_pieces(statics, waters, shown, coll):
    """{piece: [static, water per phase (frame_part), outline shell]}, each tagged with the art's view."""
    lay = layout()
    parts = {}
    for name, (c0, r0) in lay.items():
        static, lipo = statics
        st = split_art(static, f"{name}-static", c0, r0, coll)
        lp = split_art(lipo, f"{name}-lip", c0, r0, coll, caps=False)
        bpy.context.view_layer.update()
        shell = common.outline_shell(st, coll, voxel=0.04, faces=2000, smooth=4, inside=0.03)
        shell.name = shell.data.name = f"{name}-outline"
        trim_shell(shell, c0, r0)
        group = [st] + ([lp] if len(lp.data.polygons) else [])
        if os.environ.get("NOSHELL"):
            bpy.data.objects.remove(shell, do_unlink=True)
        for k, water in enumerate(waters):
            w = split_art(water, f"{name}-water-{shown[k][name]}", c0, r0, coll, caps=False)
            group.append(common.frame_part(w, [shown[k][name]]))
        if not os.environ.get("NOSHELL"):
            group.append(shell)
        parts[name] = [tag_view(o) for o in group]
    return parts


def main():
    sprite, phases, shown, statics, waters, coll = build()
    parts = make_pieces(statics, waters, shown, coll)
    static = statics[0]
    for name in PIECES:
        data = common.load_sprite(WT, name)
        assert sorted(f["index"] for f in data["frames"]) == sorted(CYCLES[name]), name
        common.export_sprite_model(WT, parts[name], f"enemies/{name}", data["sprites"])
        print(name, {o.name: len(o.data.polygons) for o in parts[name]})
    if "--scratch" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--scratch") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "colors.json").write_text(json.dumps(sprite["colors"]))
        (out / "phases.json").write_text(json.dumps([{f"{c},{r}": v for (c, r), v in px.items()} for px in phases]))
        (out / "shown.json").write_text(json.dumps(shown))
        (out / "layout.json").write_text(json.dumps(all_entries()))
        sys.path.insert(0, str(out))
        import render_F
        render_F.render_all(parts, all_entries(), static, out / "renders")


if __name__ == "__main__":
    main()
