"""Large grey asteroid (newshd.shp frame 5): a 3D version of its sprite.

Seen in episodes 1-3. A chunky boulder about 16 px thick for its 22 x 20 px footprint, traced to
the sprite's whole outline (dark rim included). Its section is one continuous superellipse
(steep, rounded sides), widest a little below the midplane, meshed evenly by area with the upper
cap subdivided once more so its faces follow the sprite's shading pixel by pixel. The sprite's
two big lit masses (centre and right) stand proud as broad bumps whose upper-left faces catch the
light, and its dark pit, the groove running down from it and the lower-right hollow are cut in.
Faces are painted with the sprite's own grey ramp (as lib_b014.rock does), the upward-facing
outermost band with its near-black outline, the side wall and underside with darker shades of the
same mottling. One frame, one model.

This rock is built here rather than by lib_b014.rock, which other asteroids share: it reuses that
module's sprite helpers (silhouette, shade bands) but its own profile and relief.

Run: blender --background --python assets/blender/enemies/newshd-5.py [-- --preview out.png]
"""

import math
import random
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402

common = lib.common
NAME = "newshd-5"

PX = 1 / 12
TOP = 7.9 * PX       # crown above the waist at the widest part, before the lit masses
BOTTOM = 6.6 * PX    # depth below the midplane
WAIST = -0.8 * PX    # the rock is widest a little below the midplane
SQ = 2.4             # superellipse exponent of the section: >2 steep, rounded sides, one continuous curve
CAP_Z = 0.3          # icosphere verts above this z are subdivided once more
WALL_W = 0.4         # extra mesh density on the steep side wall
SIDE_JIT = 0.7       # px of random inward jitter on the sides and underside
LUMPS = 0.02         # random lumpiness, well under 1 px
FINE = 0.55 * PX     # sprite-luminance texture per 100 luminance, clamped to under 1 px
# Features in sprite edge coordinates (u = column, v = row): (u, v, height px, sigma px).
MASSES = [
    (11.6, 8.6, 2.6, 2.6),   # the centre lit mass (its highlight is the upper-left face)
    (18.2, 8.9, 2.8, 2.2),   # the right lit mass: the bright ridge (15,10)-(18,7) is its upper-left face
    (8.0, 5.0, 0.9, 1.8),    # the small lit knob top-left
    (11.5, 16.5, 1.0, 1.6),  # the lit lump in the lower lobe
]
PIT = (9.2, 11.8, 2.0, 0.9)                     # the dark 2 x 2 px pit below the centre highlight
GROOVE = ((9.4, 12.2), (8.8, 18.0), 1.3, 0.75)  # the dark groove running straight down from it
HOLLOWS = [(15.2, 15.6, 1.1, 1.3),              # the lower-right hollow
           (20.0, 10.6, 0.8, 1.2)]              # the shadow under the right mass
OUTLINE_IDX = (1, 32)
RIM = 1.1 * PX        # faces this close to the outline (seen from above) are its dark rim...
RIM_NZ = 0.25          # ...where they face up; steeper faces there are the side wall
LIFT_MEAN = 0.85       # face colour: this much of the mean shade under it, the rest its brightest


def lum_grid(sprite, pixels):
    """Luminance per body pixel (None outside the body and on the outline)."""
    colors = sprite["colors"]
    return [[lib.luminance(colors[str(v)]) if v not in lib.OUTLINE else None for v in r] for r in pixels]


def blurred(grid, sigma):
    """Gaussian blur of `grid` over its valid pixels (normalised, so the rim isn't darkened)."""
    h, w = len(grid), len(grid[0])
    k = int(math.ceil(sigma * 2.5))
    out = [[None] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            acc = wsum = 0.0
            for dr in range(-k, k + 1):
                for dc in range(-k, k + 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] is not None:
                        wt = math.exp(-(dr * dr + dc * dc) / (2 * sigma * sigma))
                        acc += wt * grid[rr][cc]
                        wsum += wt
            out[r][c] = acc / wsum if wsum > 1e-6 else None
    return out


def sample(grid, x, y, size=2):
    """Bilinear sample of a per-pixel grid at Blender (x, y); None where no data."""
    u, v = lib.to_edge(x, y, size)
    u -= 0.5
    v -= 0.5
    c0, r0 = int(math.floor(u)), int(math.floor(v))
    fu, fv = u - c0, v - r0
    acc = wsum = 0.0
    for dr, wr in ((0, 1 - fv), (1, fv)):
        for dc, wc in ((0, 1 - fu), (1, fu)):
            r, c = r0 + dr, c0 + dc
            if 0 <= r < len(grid) and 0 <= c < len(grid[0]) and grid[r][c] is not None:
                acc += wr * wc * grid[r][c]
                wsum += wr * wc
    return acc / wsum if wsum > 1e-6 else None


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    size = frame["size"]
    pixels = frame["pixels"]

    shade = lib.Shade(sprite, pixels, size)
    reps, edges = lib.shade_slots(sprite, pixels, 8)
    mats = [common.palette_material(sprite, idx, NAME, metallic=0.15, roughness=0.85 - 0.03 * k)
            for k, idx in enumerate(reps)]
    m_rim = len(mats)
    mats.append(common.palette_material(sprite, 1, NAME, metallic=0.1, roughness=0.9))
    m_blue = len(mats)
    mats.append(common.palette_material(sprite, 102, NAME, metallic=0.2, roughness=0.8))

    # Footprint: the whole sprite, its dark outline included (the body only would leave a 1 px ring).
    full = [[4 if v in OUTLINE_IDX else v for v in r] for r in pixels]
    cx, cy, radii = lib.silhouette(full, size, grow=0.05, smooth=1)
    rmax = max(radii)

    fine = lum_grid(sprite, pixels)
    local = blurred(fine, 1.0)

    def profile_table(h_px, steps=400):
        """The section as (area fraction, s, h): s = horizontal fraction of the outline radius, h =
        height fraction, along one superellipse quarter from the pole (s 0) to the waist (s 1),
        indexed by the fraction of surface area above it so the mesh's density is even all over
        (an icosphere's vertices are spread evenly by area: fraction 1 - |n.z|). Steep parts count
        extra (WALL_W) so the fine upper cap reaches well down the side wall."""
        r_px = 10.0
        pts = []
        for i in range(steps + 1):
            phi = (math.pi / 2) * i / steps
            pts.append((math.sin(phi) ** (2 / SQ), math.cos(phi) ** (2 / SQ)))
        acc = [0.0]
        for (s0, h0), (s1, h1) in zip(pts, pts[1:]):
            dl = math.hypot((s1 - s0) * r_px, (h1 - h0) * h_px)
            steep = abs(h1 - h0) * h_px / dl if dl > 0 else 0.0
            acc.append(acc[-1] + dl * (s0 + s1) / 2 * (1.0 + WALL_W * steep))
        return [(a / acc[-1], s_, h_) for a, (s_, h_) in zip(acc, pts)]

    def lookup(table, f):
        lo, hi = 0, len(table) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if table[mid][0] <= f:
                lo = mid
            else:
                hi = mid
        a0, s0, h0 = table[lo]
        a1, s1, h1 = table[hi]
        t = 0.0 if a1 <= a0 else (f - a0) / (a1 - a0)
        return s0 + (s1 - s0) * t, h0 + (h1 - h0) * t

    upper = profile_table((TOP - WAIST) / PX)
    lower = profile_table((BOTTOM + WAIST) / PX)

    def gauss(u, v, fu, fv, sig):
        return math.exp(-((u - fu) ** 2 + (v - fv) ** 2) / (2 * sig * sig))

    def seg_dist(u, v, p0, p1):
        (x0, y0), (x1, y1) = p0, p1
        dx, dy = x1 - x0, y1 - y0
        t = max(0.0, min(1.0, ((u - x0) * dx + (v - y0) * dy) / (dx * dx + dy * dy)))
        return math.hypot(u - (x0 + t * dx), v - (y0 + t * dy))

    def relief(x, y):
        """Height (units) added to the upper surface at Blender (x, y): the lit masses, the pit,
        groove and hollows, and a faint texture from the sprite's own shading."""
        u, v = lib.to_edge(x, y, size)
        dz = sum(hgt * gauss(u, v, fu, fv, sig) for fu, fv, hgt, sig in MASSES)
        fu, fv, hgt, sig = PIT
        dz -= hgt * gauss(u, v, fu, fv, sig)
        p0, p1, hgt, sig = GROOVE
        dz -= hgt * math.exp(-seg_dist(u, v, p0, p1) ** 2 / (2 * sig * sig))
        dz -= sum(hgt * gauss(u, v, fu, fv, sig) for fu, fv, hgt, sig in HOLLOWS)
        dz *= PX
        lf = sample(fine, x, y)
        ll = sample(local, x, y)
        if lf is not None and ll is not None:
            dz += max(-0.8 * PX, min(0.8 * PX, FINE * (lf - ll) / 100.0))
        return dz

    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
    # The upper cap, the part seen from above, gets one more subdivision so its faces are about
    # half a sprite pixel across and can follow the sprite's shading pixel by pixel.
    cap = {e for f in bm.faces if all(v.co.z > CAP_Z for v in f.verts) for e in f.edges}
    bmesh.ops.subdivide_edges(bm, edges=list(cap), cuts=1, use_grid_fill=True)
    for v in bm.verts:
        v.co.normalize()

    rng = random.Random(5)
    blobs = [(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized(),
              rng.uniform(0.4, 1.0)) for _ in range(10)]

    def lump(n):
        return sum(a * max(0.0, n.dot(d) - 0.55) for d, a in blobs)

    for v in bm.verts:
        n = v.co.normalized()
        ang = math.atan2(n.y, n.x)
        r = lib.radius_at(radii, ang)
        size_k = 0.72 + 0.28 * r / rmax  # the narrow lower lobe is a little lower
        f = 1.0 - abs(n.z)
        if n.z >= 0:
            sf, hf = lookup(upper, f)
            z = WAIST + hf * (TOP - WAIST) * size_k
        else:
            sf, hf = lookup(lower, f)
            z = WAIST - hf * (BOTTOM + WAIST) * size_k
        # Inward-only knobbliness on the sides and underside (none on the widest ring, which is
        # the outline), on the same scale as the top's texture, so the rock is one surface.
        wall = smoothstep(0.0, 1.5 * PX, abs(z - WAIST))  # 0 on the widest ring
        sf *= 1.0 - SIDE_JIT * PX / r * rng.random() * wall * (1.0 - smoothstep(0.75, 0.5, sf))
        if n.z < 0:
            z += (rng.random() - 0.5) * SIDE_JIT * PX * (1.0 - smoothstep(0.6, 0.95, sf))
        x = cx + math.cos(ang) * sf * r
        y = cy + math.sin(ang) * sf * r
        z += n.z * LUMPS * lump(n)
        if n.z > 0:
            # Relief on the whole upper surface, easing out down the steep sides so the outline
            # stays the sprite's and the section stays one continuous curve.
            z += relief(x, y) * (1.0 - smoothstep(0.55, 0.97, sf))
        v.co = Vector((x, y, z))

    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    def inner_band(x, y, inset):
        """The sprite's shade band a little inside the outline from Blender (x, y)."""
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy)
        if d > 1e-6:
            x, y = x - dx / d * inset, y - dy / d * inset
        lum = shade.at(x, y, blur=0.8)
        return 0 if lum is None else lib.band_of(edges, lum)

    for f in bm.faces:
        cen = f.calc_center_median()
        nz = f.normal.z
        if nz < -0.3:
            # The underside: the sprite's mottling carried round, at its darkest.
            f.material_index = min(1, inner_band(cen.x, cen.y, 2.5 * PX))
            continue
        idx = shade.index(cen.x, cen.y)
        dx, dy = cen.x - cx, cen.y - cy
        edge = lib.radius_at(radii, math.atan2(dy, dx)) - math.hypot(dx, dy)  # to the outline
        if idx in OUTLINE_IDX or idx == -1 or edge < RIM:
            if nz > RIM_NZ:
                # The upward-facing rim band is the sprite's near-black outline from above.
                f.material_index = m_rim
            else:
                # The steep wall, edge-on from above: the grey a little inside, two shades
                # darker, so the side reads as the same rock as the top, all the way down.
                f.material_index = max(0, inner_band(cen.x, cen.y, 2.0 * PX) - 2)
            continue
        if idx == 102 and nz < 0.8:
            f.material_index = m_blue
            continue
        pts = [cen] + [cen.lerp(p.co, 0.6) for p in f.verts]
        ls = [shade.at(p.x, p.y, blur=0.3) for p in pts]
        ls = [x for x in ls if x is not None]
        if not ls:
            f.material_index = m_rim
            continue
        lum = LIFT_MEAN * sum(ls) / len(ls) + (1 - LIFT_MEAN) * max(ls)  # highlights stay bright
        k = lib.band_of(edges, lum)
        if nz < 0.2:  # the steep side reads darker
            k = max(0, k - 1)
        f.material_index = k

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
