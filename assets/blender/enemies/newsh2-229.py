"""Shield drone in a spinning ring (newsh2.shp frames 229-243): a 3D version of its sprite.

Seen in episode 1 (levels 25-41) and episode 3. Traced from its concept
(assets/blender/features/concepts/newsh2-229.jpg, registered to the sprite in
assets/blender/textures/newsh2-229/concept.png). A hard-surface shield-shaped core of stacked
chamfered plates: a darker rim shell, two polished armour lobes either side of a dark cut-in centre
seam, a dark top plate between them, and a faceted glowing red-orange lens in a housing on each top
corner. Around it, a ring of two arcs (about 140 degrees each, with gaps top and bottom): each a
polished armour band (outer, chamfered and crowned) over a dark inner mechanism frame with ribs, and
a dark clamp block at each end. The features are listed in assets/blender/features/newsh2-229.json.

The ring turns clockwise 22.5 degrees a frame, so the eight frames are eight models of the same
thing with the ring turned: newsh2-229 (frame 229), newsh2-229-f2 (231) ... newsh2-229-f8 (243).
The sprite's whole drone shifts by a pixel between frames; each model is centred where its frame
draws it (found from the core's top-left light). All eight are exported plain; texture_bake.py
textures them together (frame 229's bake, its UVs copied onto the other frames, which share its
mesh), so the ring's detail turns with the ring and every frame has the same brightness.

Run: blender --background --python assets/blender/enemies/newsh2-229.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402
import lib_b048 as L  # noqa: E402

NAME = "newsh2-229"
U = 1 / 12
HALF_ARC = math.radians(70)
BASE = -1.5  # px, the core's underside

# The arcs' armour band: a closed, convex cross-section (radius px, height px) swept around the ring,
# 7.95-10.6 px radius by -1.3 to 2.4 px high. A rounded superellipse, so it reads as the feature
# list's round tube from edge to edge while keeping the concept's polished armour-band crown.
def _band_profile(r0=7.95, r1=10.6, z0=-1.3, z1=2.4, power=2.6, n=12):
    rc, hw = (r0 + r1) / 2, (r1 - r0) / 2
    zc, hh = (z0 + z1) / 2, (z1 - z0) / 2
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        pts.append((rc + hw * math.copysign(abs(c) ** (2 / power), c), zc + hh * math.copysign(abs(s) ** (2 / power), s)))
    return tuple(pts)


BAND = _band_profile()
BAND_SMOOTH = (True,) * len(BAND)  # smooth all round: no hard profile corners
# The dark mechanism frame inside the band: radii and heights (px).
MECH_R = (6.6, 8.0)
MECH_Z = (-1.0, 0.9)
RIB_ANGLES = (-50, -25, 0, 25, 50)  # degrees from the arc's middle
# Clamp block at each arc end (dark, on the inner side, standing past the band's end).
CLAMP_A = (62, 73)  # degrees from the arc's middle
CLAMP_R = (6.7, 8.7)
CLAMP_Z = (-1.2, 1.7)

# The core's outline (offset from its centre in px, up = +y): half-width per height, flat across the
# top (sprite row 8) and narrowing to a point at the bottom (rows 14-16).
OUTLINE = ((-4.5, 0.9), (-3.8, 1.8), (-2.8, 2.9), (-1.8, 3.9), (-1.0, 4.5), (1.0, 4.5), (2.6, 4.5),
           (3.4, 4.5), (3.7, 4.3), (4.0, 3.85), (4.5, 3.4))
SHELL_Z = 3.0
# Left armour lobe (the right one mirrors it), traced from the concept: straight along the seam,
# its top edge slanting up to the seam under the light, its outer edge inside the rim plates.
LOBE = ((-0.45, 2.9), (-1.0, 2.85), (-2.6, 1.35), (-3.5, 0.7), (-3.45, -1.0), (-2.95, -1.8),
        (-1.95, -2.8), (-1.3, -3.45), (-0.85, -3.85), (-0.45, -3.85))
LOBE_Z = (2.6, 4.6)
SEAM_W = 0.45
TOP_PLATE = ((-1.35, 4.35), (1.35, 4.35), (1.35, 3.25), (0.45, 2.6), (-0.45, 2.6), (-1.35, 3.25))
LIGHT = (2.75, 2.75)  # lens centre offset (x either side, y) px
LENS_R = 1.1
LENS_Z = 3.75


def frame_centre(frame):
    """The drone's centre in a frame, in px edges: 3.5 px right of and below its top-left light."""
    for r, line in enumerate(frame["pixels"]):
        vals = [int(v) for v in (line.split() if isinstance(line, str) else line)]
        if 121 in vals:
            return vals.index(121) + 3.5, r + 3.5
    return 12.5, 13.5


def polar_loft(bm, cx, cy, a0, a1, profile, smooth, mat, n):
    """Sweep a (radius px, z px) profile around (cx, cy) from angle a0 to a1, with flat end caps."""
    rings = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        c, s = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((cx + r * U * c, cy + r * U * s, z * U)) for r, z in profile])
    m = len(profile)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(m):
            j = (k + 1) % m
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = mat
            # Smooth along the arc; the profile's corners stay hard (sharp edges) unless the profile
            # is rounded there.
            f.smooth = True
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(m):
            if not (smooth[k] and smooth[k - 1]):
                bm.edges.get((r0[k], r1[k])).smooth = False
    for f in (bm.faces.new(rings[0]), bm.faces.new(list(reversed(rings[-1])))):
        f.material_index = mat
        f.smooth = False


def polar_box(bm, cx, cy, a0, a1, r0, r1, z0, z1, mat, n=2):
    polar_loft(bm, cx, cy, a0, a1, ((r1, z0), (r1, z1), (r0, z1), (r0, z0)), (False,) * 4, mat, n)


def plate(bm, cx, cy, outline, z0, z1, bevel, mat):
    """A chamfered plate on an outline of (x, y) px offsets from the core's centre."""
    L.bevel_plate(bm, [(cx + x * U, cy + y * U) for x, y in outline], z0 * U, z1 * U, bevel * U, (mat,) * 4)


def _densify(outline, step=1.0):
    """The outline with extra points on long edges, so the crown shades smoothly along them."""
    out = []
    for a, b in zip(outline, outline[1:] + outline[:1]):
        k = max(1, math.ceil(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(k)]
    return out


def lobe(bm, cx, cy, outline, mat):
    """An armour lobe: straight crisp sides up to a hard edge, then a rounded smooth-shaded crown
    (a quarter-ellipse in section, many rings) so it shows one soft highlight band with darker edges."""
    corners = set()
    if L._area(outline) < 0:
        outline = list(reversed(outline))
    for i in range(len(outline)):
        a, b, c = Vector(outline[i - 1]), Vector(outline[i]), Vector(outline[(i + 1) % len(outline)])
        if (b - a).normalized().dot((c - b).normalized()) < 0.75:
            corners.add(outline[i])
    outline = _densify(outline)
    z0, z1 = LOBE_Z
    zc, t0 = z1 - 1.25, math.radians(25)
    steps = [(1.0, z0), (1.0, zc)]
    for k in range(1, 8):
        t = t0 + (math.pi / 2 - t0) * k / 7
        steps.append((1 - 0.68 * (1 - math.cos(t) / math.cos(t0)),
                      zc + (z1 - zc) * (math.sin(t) - math.sin(t0)) / (1 - math.sin(t0))))
    mx = sum(x for x, _ in outline) / len(outline)
    my = sum(y for _, y in outline) / len(outline)
    rings = []
    for f, z in steps:
        rings.append([bm.verts.new((cx + (mx + (x - mx) * f) * U, cy + (my + (y - my) * f) * U, z * U))
                      for x, y in outline])
    n = len(outline)
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mat
            f.smooth = k > 0
    for i in range(n):  # the hard edge between the sides and the crown
        bm.edges.get((rings[1][i], rings[1][(i + 1) % n])).smooth = False
    for i, p in enumerate(outline):  # the side walls' corners stay crisp; the crown stays smooth
        if p in corners:
            bm.edges.get((rings[0][i], rings[1][i])).smooth = False
    f = bm.faces.new(rings[-1])
    f.material_index = mat
    f.smooth = True
    f = bm.faces.new(list(reversed(rings[0])))
    f.material_index = mat
    f.smooth = False


def lens(bm, x, y, z, top_mat, side_mat):
    """A faceted glowing lens: a low-poly sphere, its upward facets bright and its sides deeper red."""
    before = set(bm.faces)
    res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=LENS_R * U)
    for v in res["verts"]:
        v.co.z *= 0.85
        v.co += type(v.co)((x, y, z))
    for f in set(bm.faces) - before:
        f.smooth = False
        f.material_index = top_mat if f.calc_center_median().z > z + 0.3 * LENS_R * U else side_mat


def build_core(bm, cx, cy, M):
    # Rim shell: the whole shield outline, darker side plates, chamfered.
    right = [(w, y) for y, w in OUTLINE]
    shell = right + [(-w, y) for y, w in reversed(OUTLINE)]
    plate(bm, cx, cy, shell, BASE, SHELL_Z, 0.6, M["rim"])
    # The dark centre seam between the lobes, just over the shell's top.
    plate(bm, cx, cy, ((-SEAM_W, 2.8), (SEAM_W, 2.8), (SEAM_W, -3.95), (-SEAM_W, -3.95)), 2.2, SHELL_Z + 0.1, 0.05, M["seam"])
    # Two polished armour lobes.
    for s in (-1, 1):
        lobe(bm, cx, cy, [(s * x, y) for x, y in LOBE], M["lobe"])
    # Dark top plate between the lights, with a V foot pointing down the seam.
    plate(bm, cx, cy, TOP_PLATE, 2.4, 3.9, 0.35, M["top"])
    # Lights: a dark hexagonal housing with a faceted lens on it.
    for s in (-1, 1):
        lx, ly = s * LIGHT[0], LIGHT[1]
        hexo = [(lx + 1.45 * math.cos(math.pi / 3 * k), ly + 1.3 * math.sin(math.pi / 3 * k)) for k in range(6)]
        plate(bm, cx, cy, hexo, 2.2, 3.2, 0.25, M["housing"])
        lens(bm, cx + lx * U, cy + ly * U, LENS_Z * U, M["lens_top"], M["lens_side"])


def build_ring(bm, cx, cy, turn, M):
    for mid in (math.pi, 0.0):
        m = mid - turn
        polar_loft(bm, cx, cy, m - HALF_ARC, m + HALF_ARC, BAND, BAND_SMOOTH, M["band"], 24)
        polar_box(bm, cx, cy, m - math.radians(64), m + math.radians(64), *MECH_R, *MECH_Z, M["mech"], n=16)
        for d in RIB_ANGLES:
            a = m + math.radians(d)
            polar_box(bm, cx, cy, a - math.radians(4), a + math.radians(4), MECH_R[0] - 0.1, MECH_R[1] + 0.05,
                      MECH_Z[0], MECH_Z[1] + 0.5, M["rib"], n=1)
        for s in (-1, 1):
            a0, a1 = (m + s * math.radians(CLAMP_A[0]), m + s * math.radians(CLAMP_A[1]))
            polar_box(bm, cx, cy, min(a0, a1), max(a0, a1), *CLAMP_R, *CLAMP_Z, M["clamp"], n=2)


def build_one(sprite, name, turn, centre):
    coll = common.reset_collection(name)
    pal = lambda i, tag=NAME, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    # Each part in its mid-tone; the sprite's white streaks on the arcs and silver spots on the core
    # are sheen on polished metal, and its black ring is the outline the game draws itself.
    mats = [
        pal(10, metallic=0.6, roughness=0.42),  # 0 ring armour bands: polished but opaque metal
        pal(4, metallic=0.5, roughness=0.5),  # 1 ring mechanism frame
        pal(6, metallic=0.6, roughness=0.4),  # 2 ribs on the frame
        pal(3, metallic=0.5, roughness=0.45),  # 3 clamp blocks at the arc ends
        pal(7, metallic=0.6, roughness=0.45),  # 4 core rim shell (side plates)
        pal(10, f"{NAME}-lobe", metallic=0.55, roughness=0.48),  # 5 core armour lobes: soft sheen
        pal(2, metallic=0.2, roughness=0.7),  # 6 centre seam (dark, cut in)
        pal(6, metallic=0.6, roughness=0.35),  # 7 top plate
        pal(4, metallic=0.5, roughness=0.45),  # 8 light housings
        pal(121, emission_strength=4.0),  # 9 lens, upper facets: orange
        pal(118, emission_strength=4.0),  # 10 lens, side facets: red
    ]
    M = dict(band=0, mech=1, rib=2, clamp=3, rim=4, lobe=5, seam=6, top=7, housing=8, lens_top=9, lens_side=10)
    cx, cy = (centre[0] - 12) * U, (14 - centre[1]) * U
    bm = bmesh.new()
    build_ring(bm, cx, cy, turn, M)
    build_core(bm, cx, cy, M)
    return lib.finish(name, bm, mats, coll)


def build(sprite):
    frames = sprite["sprites"][0]["frames"]
    by_index = {f["index"]: f for f in sprite["frames"]}
    models = []
    for k, frame in enumerate(frames):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        f = by_index[frame]
        obj = build_one(sprite, name, k * math.pi / 8, frame_centre(f))
        models.append((name, [obj], lib.frames_subset(sprite, [frame])))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
