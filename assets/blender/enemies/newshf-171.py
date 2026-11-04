"""Spinning red rod (newshf.shp frames 171, 190, 209, 228) as a machined spindle: a 3D version
of its sprite.

Seen in episodes 1-4 (inventory: levels 1.8, 1.12, 1.17, 2.1, 3.10, 4.3; launched by another unit,
never placed by a level event). The sprite is a 12 px pink-red spindle, 3 px across, pointed at both
ends, brightest in the middle, no ink border (D74: the edge stays at the sprite's outer edge). Its
four frames turn it in plan through 0, 45, 90 and 135 degrees, so each frame is the same spindle,
turned and centred on that frame's pixels, exported as its own model (newshf-171, -f2, -f3, -f4),
each with its outline shell (D51).

Reading (tools/calibration/rubric.md): the bright streak along the middle row is the light on a
round part (a turned bar, not a flat strip); the ramp from dark tips to a bright middle is partly
the spindle's taper and partly the sprite's banding, which a hard-surface part reads as separate
turned pieces. Named parts, each with its region's palette index (median of the region's pixels,
darkest and brightest left out as shading/sheen):
  hub      cols 5-6   pal 75   a centre collar with a split seam and six hex bolts round it
  sleeve   cols 4, 7  pal 73   a recessed bearing sleeve either side of the hub
  shaft    cols 2-3, 8-9 pal 71  fluted shafts (8 shallow flutes), a groove at each inner end
  tip      cols 0-1, 10-11 pal 68  hardened ogive points behind a chamfered ferrule step
Plan: one radius profile r(d) (d = px from the tip) fitted so the rasterised top view matches the
mask on all four frames (pchip through D_KNOTS/R_KNOTS); the modelled grooves cut inside it.
Top-view IoU on the sprite grid (tools/sprite_mask.py --measure): 1.0 on every frame.

Run: blender --background --python assets/blender/enemies/newshf-171.py [-- --preview out.png]
(the preview shows the first frame; the other frames get <name>-fN.png beside it).
"""

import bisect
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402
import lib_b095 as lib  # noqa: E402

NAME = "newshf-171"
ROOT = common.repo_root(__file__)
TAG = "nshf171"
PX = 1 / 12
W, H = 12, 14  # the sprite frame
L = 6.0  # half length, px
SIDES = 40

# Frame -> (centre x, centre y in sprite px edges = mask centroid, plan angle CCW from sprite-right).
FRAMES = {171: (6.0, 6.5, 0.0), 190: (5.5, 7.5, 45.0), 209: (6.5, 7.0, 90.0), 228: (6.5, 7.5, 135.0)}
SUFFIX = {171: "", 190: "-f2", 209: "-f3", 228: "-f4"}

# Plan / section radius against distance from the tip (px), fitted to the four masks (2D raster
# search, opt2d.py / opt3.py beside this script): IoU 1.0 on every frame on the sprite grid.
D_KNOTS = [0.0, 0.3, 0.65, 1.3, 2.08, 3.12, 6.0]
R_KNOTS = [0.95 * r for r in (0.12, 0.55, 0.96, 1.27, 1.47, 1.55, 1.55)]

# Material slots: (palette index, metallic, roughness)
HUB, SLEEVE, SHAFT, TIP, BOLT = range(5)
MATS = {HUB: (75, 0.55, 0.34), SLEEVE: (73, 0.5, 0.4), SHAFT: (71, 0.5, 0.38), TIP: (68, 0.6, 0.32),
        BOLT: (70, 0.55, 0.4)}


def pchip(xs, ys):
    """Monotone cubic interpolation through (xs, ys) (as usp_talon.pchip)."""
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


BASE = pchip(D_KNOTS, R_KNOTS)


def base(s):
    return BASE(L - abs(s))


# Half profile, s from the centre (px) out to the tip: (s, radius offset from BASE or absolute,
# slot of the band that starts here, fluted). Duplicate stations give crisp turned steps.
def half_profile():
    st = []

    def add(s, dr, slot, flute=False):
        st.append((s, base(s) + dr, slot, flute))
    # hub collar: chamfered shoulders, a row of hex bolts round its middle (hex_bolt)
    add(0.0, 0.12, HUB)
    add(0.80, 0.12, HUB)
    add(0.87, 0.04, HUB)
    add(0.90, -0.12, SLEEVE)  # a parting groove between the collar and the sleeve
    add(0.98, -0.12, SLEEVE)
    add(1.01, 0.03, SLEEVE)
    # bearing sleeve, flush with the plan (the diagonal frames need its full width)
    add(1.05, 0.08, SLEEVE)
    add(1.80, 0.07, SLEEVE)
    add(1.84, -0.02, SLEEVE)
    add(1.86, -0.06, SHAFT)  # square step down to the fluted shaft
    add(1.90, -0.06, SHAFT, True)
    add(3.62, 0.01, SHAFT, True)
    add(3.66, 0.01, SHAFT)  # a plain land ring at the shaft's outer end
    add(3.70, 0.03, SHAFT)
    add(3.88, 0.03, SHAFT)
    add(3.93, -0.06, SHAFT)
    add(3.96, -0.2, TIP)  # ferrule step to the hardened point
    add(4.04, -0.2, TIP)
    add(4.10, -0.04, TIP)
    add(4.16, 0.0, TIP)
    for s in (4.6, 5.05, 5.45, 5.75):
        add(s, 0.0, TIP)
    st.append((5.92, base(5.92), TIP, False))
    st.append((6.0, 0.0, TIP, False))  # the point
    return st


FLUTES = 8
FLUTE_DEPTH = 0.17  # px
FLUTE_HALF = 0.21  # rad, half the flute's width; the rest of each 45 degree pitch is land


def flute_cut(a):
    """How deep (px) the fluted shaft is cut at angle a (0 = top): round-bottomed flutes centred
    between lands; the lands fall at 0 and 90 degrees, so the top and the plan's sides are full."""
    pitch = 2 * math.pi / FLUTES
    u = (a - pitch / 2) % pitch
    dlt = min(u, pitch - u)
    return FLUTE_DEPTH * math.sqrt(max(0.0, 1 - (dlt / FLUTE_HALF) ** 2))


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(Vector(p) * PX)

    def f(self, verts, mat, smooth=True):
        try:
            face = self.bm.faces.new(verts)
        except ValueError:
            return None
        face.material_index = mat
        face.smooth = smooth
        return face


def spindle(M, zc):
    """The turned body along +X, centred on the origin, axis at height zc (px)."""
    half = half_profile()
    prof = [(-s, r, slot, fl) for s, r, slot, fl in reversed(half)] + half[1:]
    # The band slot of a segment is the outer station's slot (the slot named where the band starts).
    rings = []
    for s, r, slot, fl in prof:
        if r <= 1e-6:
            rings.append([M.v((s, 0, zc))])
            continue
        ring = []
        for k in range(SIDES):
            a = 2 * math.pi * k / SIDES
            rr = r - (flute_cut(a) if fl else 0.0)
            ring.append(M.v((s, -rr * math.sin(a), zc + rr * math.cos(a))))
        rings.append(ring)
    for i in range(len(prof) - 1):
        s0, s1 = prof[i][0], prof[i + 1][0]
        slot = prof[i + 1][2] if abs(s1) > abs(s0) else prof[i][2]  # the outer station's band
        r0, r1 = rings[i], rings[i + 1]
        for k in range(SIDES):
            j = (k + 1) % SIDES
            if len(r0) == 1:
                M.f((r0[0], r1[j], r1[k]), slot)
            elif len(r1) == 1:
                M.f((r0[k], r0[j], r1[0]), slot)
            else:
                M.f((r0[k], r0[j], r1[j], r1[k]), slot)


def hex_bolt(M, s, ang, zc, r_surf, mat):
    """A small hex bolt head on the hub at axial s, angle ang (0 = top), standing on radius r_surf."""
    n = Vector((0, -math.sin(ang), math.cos(ang)))
    c = Vector((s, 0, zc)) + n * (r_surf - 0.06)
    t = Vector((1, 0, 0))
    b = n.cross(t)
    rad, h = 0.24, 0.13
    rings = []
    for rr, hh in ((rad, 0.0), (rad, h * 0.7), (rad * 0.75, h)):
        rings.append([M.v(c + n * hh + (t * math.cos(math.pi / 3 * k + math.pi / 6) + b * math.sin(math.pi / 3 * k + math.pi / 6)) * rr)
                      for k in range(6)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(6):
            j = (k + 1) % 6
            M.f((r0[k], r0[j], r1[j], r1[k]), mat, smooth=False)
    M.f(list(reversed(rings[0])), mat, smooth=False)
    M.f(rings[-1], mat, smooth=False)


def make_materials(sprite):
    out = []
    for slot in range(len(MATS)):
        i, met, rough = MATS[slot]
        out.append(common.palette_material(sprite, i, TAG, metallic=met, roughness=rough))
    return out


def build_frame(sprite, frame_index, coll, mats):
    cx, cy, ang = FRAMES[frame_index]
    zc = max(R_KNOTS)  # the spindle lies on the ground
    M = Mesh()
    spindle(M, zc)
    r_hub = base(0.4) + 0.12
    for k in range(6):
        hex_bolt(M, 0.0, k * math.pi / 3, zc, r_hub, BOLT)
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(ang), 3, "Z"))
    bmesh.ops.translate(bm, verts=bm.verts, vec=((cx - W / 2) * PX, (H / 2 - cy) * PX, 0))
    bm.normal_update()
    name = NAME + SUFFIX[frame_index]
    obj = common.mesh_object(name, bm, mats, coll, smooth=True)
    obj.data.set_sharp_from_angle(angle=math.radians(30))
    shell = common.outline_shell(obj, coll, voxel=0.006, faces=600, smooth=4)
    return obj, shell


def tris(objs):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)


def build_all():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    mats = make_materials(sprite)
    return sprite, {f: build_frame(sprite, f, coll, mats) for f in FRAMES}


def main():
    sprite, out = build_all()
    prev = lib.preview_arg()
    for i, frame in enumerate(sprite["frames"]):
        f = frame["index"]
        obj, shell = out[f]
        name = NAME + SUFFIX[f]
        common.export_sprite_model(ROOT, [obj, shell], f"enemies/{name}", lib.subset(sprite, [f]))
        print(f"frame {f}: {name} {tris([obj])} tris, shell {tris([shell])} tris")
        if prev:
            path = prev if i == 0 else str(Path(prev).with_name(f"{name}.png"))
            lib.preview(ROOT, NAME, [obj], sprite, frame=i, out=path)


if __name__ == "__main__":
    main()
