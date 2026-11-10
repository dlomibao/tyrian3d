"""Glowing grate (newsha.shp frame 89), a cast hatch frame set in the ground over a
glowing pit, two channel bars across it (DECISIONS D50-D53, D65, D74). Seen in episode 1
(level 1.13).

Read from the sprite (24 x 28 px grid, 18 x 23 px drawn):
- Plan: an egg-shaped, slightly lopsided outline (the east side bulges a pixel out over rows
  13-17). The model's edge is a smooth curve fitted to the sprite's INNER mask (the 1 px ink ring
  is the game's outline, D74): rays from the centre, the 0.5 crossing of the mask blurred by
  0.55 px, so it is round where the sprite is round.
- The frame: a narrow outer band (index 22, dark 19 on the shaded east/south side = lighting) with
  a rounded shoulder, a modelled panel line, then a raised inner deck (index 25; the pale 26-29
  pixels on the west are the deck's lit inner chamfer). The opening is NOT centred: the deck is
  wide on the north-east and south-east where the stripes end. Its contour is fitted to the
  sprite's red + bar pixels, the same way.
- The pit: the red pixels are a glowing floor (median index 116), hottest along the middle of each
  stripe (118-121) and at a core (123): emissive heater strips along x+y = 17, 25, 32 (pixel
  edges), stepped from 118 to 120 toward the core, a low 121 collar ring and a small 123 core boss.
- The bars: two straight channel bars along x+y = 21 and 29 (the 25-19-25 pixel bands, 3 px on
  the diagonal = 2.12 px across). A U-channel: two lit lips (25) and a dark groove floor (20), the
  sprite's 19 line. Their ends run under the deck, held by bolts on the deck.
- Undersides: a flat closed base, nothing more.

Run: blender --background --python assets/blender/enemies/newsha-89.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newsha-89"
PX = 1 / 12
W, H = 24, 28
CX, CY = 11.9, 13.6     # ray centre (pixel-edge coords: x = col, y = row, y down)
N = 88                  # points per ring
RED_IDX = set(range(114, 124))

# heights (sprite px)
Z_FLOOR = 1.15          # glowing pit floor
Z_INNER_FOOT = 1.55     # foot of the inner wall where it meets the floor apron
BAR_Z0 = 0.95
BAR_TOP = 2.25
BAR_GROOVE = 1.85

# The glows. In game a glow material's emissive is its palette colour at intensity max(1, the
# exported strength), and the sun + hemisphere + room light on top of it pushed 119 to salmon pink
# and 123 to cream under the Neutral tone map (round 1). So: strength 1 (the colour itself), and
# metallic 1, so the diffuse light drops out, and a high roughness (GLOW_ROUGH), so the room
# reflection is a soft wash rather than pink-white specular streaks (fix round: roughness 0.2 made
# the strips read as glossy red gel tubes and lifted the floor to ~119 in game): 116 floor -> deep red, 118 strip ends -> red, 120 near the core -> orange-red,
# 121 collar -> orange, 123 core -> amber.
HOT, WARM, COLLAR, CORE = 1.0, 1.0, 1.0, 1.0
GLOW_ROUGH = 0.88
Z_COLLAR = Z_FLOOR + 0.12   # the 121 collar's outer foot: a raised ring clear of floor and strips
R_COLLAR = 1.35


# --- sprite analysis (numpy only, runs in Blender) ---------------------------------------------

def load_masks():
    sp = common.load_sprite(WT, NAME)
    px = np.array(sp["frames"][0]["pixels"])
    opaque = px >= 0
    # the D74 inner mask: drop the ink ring (luma < 26, 4-adjacent to the outside)
    cols = sp["colors"]
    luma = np.zeros(px.shape)
    for k, (r, g, b) in cols.items():
        luma[px == int(k)] = 0.299 * r + 0.587 * g + 0.114 * b
    pad = np.pad(opaque, 1)
    outside_adj = ~pad[:-2, 1:-1] | ~pad[2:, 1:-1] | ~pad[1:-1, :-2] | ~pad[1:-1, 2:]
    border = opaque & outside_adj & (luma < 26)
    inner = opaque & ~border
    red = np.isin(px, list(RED_IDX))
    # pocket = red + the bar pixels between them: close the red mask across the 3 px diagonal bars
    rr, cc = np.indices(px.shape)
    s = rr + cc
    bars = ((s >= 19) & (s <= 21)) | ((s >= 27) & (s <= 29))
    pocket = red.copy()
    # a bar pixel belongs to the pocket when red lies on both sides of it along its row or column
    for r in range(px.shape[0]):
        for c in range(px.shape[1]):
            if bars[r, c] and inner[r, c] and not red[r, c]:
                left = red[r, max(c - 4, 0):c].any()
                right = red[r, c + 1:c + 5].any()
                up = red[max(r - 4, 0):r, c].any()
                down = red[r + 1:r + 5, c].any()
                if (left and right) or (up and down):
                    pocket[r, c] = True
    return sp, px, inner, pocket


def blur(m, sigma):
    k = int(math.ceil(sigma * 3))
    xs = np.arange(-k, k + 1)
    g = np.exp(-xs ** 2 / (2 * sigma ** 2))
    g /= g.sum()
    a = np.pad(m.astype(float), k)
    a = np.apply_along_axis(lambda v: np.convolve(v, g, mode="same"), 0, a)
    a = np.apply_along_axis(lambda v: np.convolve(v, g, mode="same"), 1, a)
    return a, k


def sample(a, k, x, y):
    """Bilinear sample at pixel-edge coords (x, y) of a padded blurred mask (pixel centres at +0.5)."""
    fx, fy = x - 0.5 + k, y - 0.5 + k
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    h, w = a.shape
    def at(i, j):
        return a[j, i] if 0 <= i < w and 0 <= j < h else 0.0
    return (at(x0, y0) * (1 - tx) * (1 - ty) + at(x0 + 1, y0) * tx * (1 - ty)
            + at(x0, y0 + 1) * (1 - tx) * ty + at(x0 + 1, y0 + 1) * tx * ty)


def radii(mask, sigma=0.55, level=0.5, smooth=1):
    a, k = blur(mask, sigma)
    out = []
    for i in range(N):
        t = 2 * math.pi * i / N
        dx, dy = math.cos(t), math.sin(t)
        r, last = 0.0, None
        step = 0.02
        while r < 20:
            v = sample(a, k, CX + dx * r, CY + dy * r)
            if v < level:
                if last is not None:
                    r -= step * (level - v) / max(last - v, 1e-9)
                break
            last = v
            r += step
        out.append(r)
    out = np.array(out)
    for _ in range(smooth):  # light circular smoothing
        out = 0.25 * np.roll(out, 1) + 0.5 * out + 0.25 * np.roll(out, -1)
    return out


def ray(i, r):
    t = 2 * math.pi * i / N
    return CX + math.cos(t) * r, CY + math.sin(t) * r


def B(x, y, z):
    """pixel-edge coords (y down) and px height -> Blender units."""
    return ((x - W / 2) * PX, (H / 2 - y) * PX, z * PX)


# --- frame --------------------------------------------------------------------------------------

def frame_profile(G):
    """(d inward from the outer edge, z, material tag) rings for a rim G px wide on this ray."""
    b = min(1.15, 0.45 * G)
    de = max(G - 0.55, b + 0.45)
    dm = (b + 0.32 + de) / 2
    return [
        (0.35, 0.0, "band"),
        (0.0, 0.4, "band"),
        (0.0, 1.75, "band"),
        (0.05, 1.95, "band"),     # small fillet, then a straight chamfer: a cast, hard edge
        (0.32, 2.25, "band"),
        (0.45, 2.36, "band"),
        (b - 0.1, 2.4, "band"),
        (b, 2.2, "band"),         # panel line between the band and the raised deck
        (b + 0.16, 2.2, "deck"),
        (b + 0.32, 2.62, "deck"),
        (dm, 2.66, "deck"),
        (de, 2.62, "deck"),
        (G - 0.22, 2.42, "deck"),  # inner chamfer (the sprite's pale west lip)
        (G, 2.05, "deck"),
        (G, Z_INNER_FOOT, "deck"),
        (G + 0.25, Z_FLOOR + 0.1, "pit"),   # a short dark apron down to the floor
        (G + 0.35, Z_FLOOR, "pit"),
    ]


def build_frame(bm, Ro, Rp, M):
    rings = []
    tags = None
    for i in range(N):
        G = Ro[i] - Rp[i]
        prof = frame_profile(G)
        tags = [p[2] for p in prof]
        rings.append([(*ray(i, Ro[i] - d), z) for d, z, _ in prof])
    K = len(rings[0])
    V = [[bm.verts.new(B(*rings[i][k])) for k in range(K)] for i in range(N)]
    for i in range(N):
        j = (i + 1) % N
        for k in range(K - 1):
            f = bm.faces.new((V[i][k], V[j][k], V[j][k + 1], V[i][k + 1]))
            tag = tags[k + 1] if tags[k] != tags[k + 1] else tags[k]
            if k == 7:  # the panel-line floor
                tag = "band"
            f.material_index = M[tag]
            f.smooth = True
    # bottom cap and floor (fans to a centre vertex)
    bot = bm.faces.new([V[i][0] for i in reversed(range(N))])
    bot.material_index = M["band"]
    # pit floor: concentric rings for nicer shading, then a fan
    prev = [V[i][K - 1] for i in range(N)]
    lastr = [Ro[i] - frame_profile(Ro[i] - Rp[i])[-1][0] for i in range(N)]
    for sc in (0.7, 0.4):
        ring = [bm.verts.new(B(*ray(i, lastr[i] * sc), Z_FLOOR)) for i in range(N)]
        for i in range(N):
            j = (i + 1) % N
            f = bm.faces.new((prev[i], prev[j], ring[j], ring[i]))
            f.material_index = M["red"]
        prev = ring
    c = bm.verts.new(B(CX, CY, Z_FLOOR))
    for i in range(N):
        f = bm.faces.new((prev[i], prev[(i + 1) % N], c))
        f.material_index = M["red"]


# --- pocket polygon helpers ----------------------------------------------------------------------

def pocket_poly(Rp, grow=0.0):
    return [ray(i, Rp[i] + grow) for i in range(N)]


def inside(poly, x, y):
    c = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (x1 - x0) * (y - y0) / (y1 - y0):
            c = not c
    return c


def line_span(poly, s):
    """Parameter range t along the diagonal x + y = s (point (s/2 + t, s/2 - t)) inside poly."""
    ts = [t / 50 for t in range(-800, 801)]
    ins = [t for t in ts if inside(poly, s / 2 + t, s / 2 - t)]
    return min(ins), max(ins)


# --- bars, strips, bolts -----------------------------------------------------------------------

def prism(bm, path, section, mat, smooth=False, mats=None):
    """Sweep a 2D section (u across, z) along a straight path a->b; u along the perpendicular
    (1, 1)/sqrt2 in pixel coords. Capped. mats: per-section-edge material (optional)."""
    (ax, ay), (bx, by) = path
    ux, uy = 1 / math.sqrt(2), 1 / math.sqrt(2)
    rows = []
    for px_, py_ in ((ax, ay), (bx, by)):
        rows.append([bm.verts.new(B(px_ + ux * u, py_ + uy * u, z)) for u, z in section])
    n = len(section)
    for k in range(n):
        j = (k + 1) % n
        f = bm.faces.new((rows[0][k], rows[0][j], rows[1][j], rows[1][k]))
        f.material_index = mats[k] if mats else mat
        f.smooth = smooth
    for r in (rows[0], list(reversed(rows[1]))):
        f = bm.faces.new(r)
        f.material_index = mat


def build_bars(bm, Rp, M):
    hw = 1.5 / math.sqrt(2)  # 3 diagonal px across
    sec = [(-hw, BAR_Z0), (-hw, BAR_TOP - 0.25), (-hw + 0.15, BAR_TOP), (-0.4, BAR_TOP),
           (-0.28, BAR_GROOVE), (0.28, BAR_GROOVE), (0.4, BAR_TOP), (hw - 0.15, BAR_TOP),
           (hw, BAR_TOP - 0.25), (hw, BAR_Z0)]
    mats = [M["bar"]] * len(sec)
    mats[4] = M["groove"]  # the groove floor (edge 4 -> 5)
    poly = pocket_poly(Rp, grow=0.55)
    ends = []
    for s in (21.0, 29.0):
        t0, t1 = line_span(poly, s)
        a = (s / 2 + t0, s / 2 - t0)
        b = (s / 2 + t1, s / 2 - t1)
        prism(bm, (a, b), sec, M["bar"], mats=mats)
        ends.append((s, t0, t1))
    return ends


def build_strips(bm, Rp, M):
    """Hot heater strips along the middle of each glowing stripe, graded radially from the core
    (116 floor, 118 strip ends, 120 near the middle, a 121 collar, the 123 centre): each strip
    is cut into short segments and each takes the step for its distance from the core, then a
    raised 121 collar round the core boss."""
    cx, cy = 11.5, 13.5
    poly = pocket_poly(Rp, grow=-0.45)
    for s, w in ((17.0, 1.15), (25.0, 1.7), (32.0, 0.95)):
        t0, t1 = line_span(poly, s)
        # cut the strip where it would run under the collar (no stacked faces to z-fight)
        tc = ((cx - s / 2) - (cy - s / 2)) / 2
        dp = math.hypot(s / 2 + tc - cx, s / 2 - tc - cy)
        spans = [(t0, t1)]
        if dp < R_COLLAR:
            h = math.sqrt(R_COLLAR ** 2 - dp ** 2) / math.sqrt(2)
            spans = [(a, b) for a, b in ((t0, min(t1, tc - h)), (max(t0, tc + h), t1)) if b - a > 0.05]
        hw = w / 2
        sec = [(-hw, Z_FLOOR - 0.05), (-hw * 0.75, Z_FLOOR + 0.05), (hw * 0.75, Z_FLOOR + 0.05), (hw, Z_FLOOR - 0.05)]  # flush inlay: glow, not a bump
        for t0, t1 in spans:
          n = max(2, int(math.ceil((t1 - t0) / 0.8)))
          for k in range(n):
            ta, tb = t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n
            tm = (ta + tb) / 2
            d = math.hypot(s / 2 + tm - cx, s / 2 - tm - cy)
            tag = "hot" if d < 3.4 else "warm"  # the sprite keeps 119-121 out to the stripe ends
            a = (s / 2 + ta, s / 2 - ta)
            b = (s / 2 + tb, s / 2 - tb)
            prism(bm, (a, b), sec, M[tag], smooth=True)
    def circ(r, z, rot=0.0, n=8):
        return [bm.verts.new(B(cx + r * math.cos(2 * math.pi * (i + rot) / n), cy + r * math.sin(2 * math.pi * (i + rot) / n), z)) for i in range(n)]
    # collar: a low raised 121 ring round the core, sloping up toward it, with a short outer skirt
    # down into the floor; the middle strip stops at its edge, so nothing stacks under it
    cf = circ(R_COLLAR, Z_FLOOR - 0.05, n=16)
    co, ci = circ(R_COLLAR, Z_COLLAR, n=16), circ(0.7, Z_COLLAR + 0.05, n=16)
    for i in range(16):
        j = (i + 1) % 16
        bm.faces.new((cf[i], cf[j], co[j], co[i])).material_index = M["collar"]
        bm.faces.new((co[i], co[j], ci[j], ci[i])).material_index = M["collar"]
    # core: a low faceted boss at the hottest pixel (col 11, row 13)
    g0, g1, tp = circ(0.72, Z_FLOOR), circ(0.72, Z_FLOOR + 0.12), circ(0.42, Z_FLOOR + 0.2, 0.5)
    for i in range(8):
        j = (i + 1) % 8
        bm.faces.new((g0[i], g0[j], g1[j], g1[i])).material_index = M["core"]
        bm.faces.new((g1[i], g1[j], tp[i])).material_index = M["core"]
        bm.faces.new((tp[i], g1[j], tp[j])).material_index = M["core"]
    bm.faces.new(list(reversed(tp))).material_index = M["core"]


def deck_z_at(Ro, Rp, x, y):
    """Frame top height at a point (for seating bolts); None off the flat deck."""
    t = math.atan2(y - CY, x - CX) % (2 * math.pi)
    i = int(round(t / (2 * math.pi) * N)) % N
    r = math.hypot(x - CX, y - CY)
    d = Ro[i] - r
    G = Ro[i] - Rp[i]
    prof = frame_profile(G)
    if prof[9][0] + 0.25 <= d <= prof[11][0] - 0.25:
        return 2.64
    return None


def bolt(bm, x, y, z, mat, r=0.42):
    def circ(rr, zz):
        return [bm.verts.new(B(x + rr * math.cos(math.pi / 6 + math.pi * i / 3), y + rr * math.sin(math.pi / 6 + math.pi * i / 3), zz)) for i in range(6)]
    a, b, c = circ(r, z - 0.2), circ(r, z + 0.18), circ(r * 0.72, z + 0.3)
    for i in range(6):
        j = (i + 1) % 6
        bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
        bm.faces.new((b[i], b[j], c[j], c[i])).material_index = mat
    bm.faces.new(list(reversed(c))[::-1]).material_index = mat


def build_bolts(bm, Ro, Rp, ends, M):
    """Bolts where each bar end runs under the deck (only where the deck is wide enough)."""
    placed = []
    for s, t0, t1 in ends:
        for t, sgn in ((t0, -1), (t1, 1)):
            for off in (0.55, 0.95, 1.4):
                tt = t + sgn * off
                x, y = s / 2 + tt, s / 2 - tt
                z = deck_z_at(Ro, Rp, x, y)
                if z is not None:
                    bolt(bm, x, y, z, M["deck"])
                    placed.append((round(x, 2), round(y, 2)))
                    break
    return placed


# --- assemble -----------------------------------------------------------------------------------

def build():
    sp, px, inner, pocket = load_masks()
    Ro = radii(inner, sigma=0.55, level=0.5, smooth=4)
    Rp = radii(pocket, sigma=0.6, level=0.5, smooth=2)
    coll = common.reset_collection(NAME)
    pal = lambda i, tag, **kw: common.palette_material(sp, i, f"{NAME}_{tag}", **kw)  # noqa: E731
    mats = [
        pal(22, "band", metallic=0.15, roughness=0.72),   # duller than the deck: the darker outer ring
        pal(25, "deck", metallic=0.3, roughness=0.5),
        pal(116, "pit", emission_strength=1.0, metallic=1.0, roughness=GLOW_ROUGH),
        pal(25, "bar", metallic=0.35, roughness=0.45),
        pal(20, "groove", metallic=0.3, roughness=0.6),
        pal(120, "hot", emission_strength=HOT, metallic=1.0, roughness=GLOW_ROUGH),
        pal(123, "core", emission_strength=CORE, metallic=1.0, roughness=GLOW_ROUGH),
        pal(114, "apron", emission_strength=1.0, metallic=1.0, roughness=GLOW_ROUGH),
        pal(118, "warm", emission_strength=WARM, metallic=1.0, roughness=GLOW_ROUGH),
        pal(121, "collar", emission_strength=COLLAR, metallic=1.0, roughness=GLOW_ROUGH),
    ]
    # deck and bar share pal 25: keep separate slots so their roughness can differ
    M = {"band": 0, "deck": 1, "red": 2, "bar": 3, "groove": 4, "hot": 5, "core": 6, "pit": 7,
         "warm": 8, "collar": 9}
    bm = bmesh.new()
    build_frame(bm, Ro, Rp, M)
    ends = build_bars(bm, Rp, M)
    build_strips(bm, Rp, M)
    placed = build_bolts(bm, Ro, Rp, ends, M)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(40))
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print(f"{NAME}: {len(me.polygons)} faces, {tris} triangles, bolts at {placed}")
    print("Ro", [round(v, 2) for v in Ro[::8]], "Rp", [round(v, 2) for v in Rp[::8]])
    return obj, coll


def shell_source(coll):
    """The outline shell's source: the frame's outer profile up to the deck top, the panel line
    left out, closed by a flat lid at deck height over the pit. A convex puck, so the smoothed shell
    has no dips: built from the model itself (round 1) it filled the pit and the panel line, stood
    outside the model there and drew ink along the bars, round the pit rim and (held inside with
    Shrinkwrap) along the panel line (the D88 failure)."""
    sp, px, inner, pocket = load_masks()
    Ro = radii(inner, sigma=0.55, level=0.5, smooth=4)
    Rp = radii(pocket, sigma=0.6, level=0.5, smooth=2)
    keep = (0, 1, 2, 3, 4, 5, 6, 9, 10, 11)
    bm = bmesh.new()
    V = []
    for i in range(N):
        prof = frame_profile(Ro[i] - Rp[i])
        V.append([bm.verts.new(B(*ray(i, Ro[i] - prof[k][0]), prof[k][1])) for k in keep])
    K = len(keep)
    for i in range(N):
        j = (i + 1) % N
        for k in range(K - 1):
            bm.faces.new((V[i][k], V[j][k], V[j][k + 1], V[i][k + 1]))
    bm.faces.new([V[i][0] for i in reversed(range(N))])
    bm.faces.new([V[i][K - 1] for i in range(N)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f"{NAME}_shellsrc")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(f"{NAME}_shellsrc", me)
    coll.objects.link(obj)
    return obj


def main():
    obj, coll = build()
    src = shell_source(coll)
    shell = common.outline_shell(src, coll, voxel=0.012, faces=1500, smooth=8)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(src)
    sprite = common.load_sprite(WT, NAME)
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])


if __name__ == "__main__":
    main()
