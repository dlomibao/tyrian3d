"""Molten rock (newshl.shp 115, newsh3.shp 134 and 135), a lump of cooling lava.

What it is: a fireball of rock that the CORE launchers spit at the player, and drifting debris in
TIME WAR / SQUADRON. The sprite draws a round lump, 9 x 11 px inside its ink ring, mottled dark red
(113-118) with orange-yellow hot spots (119-125). Built as what it is: a boulder of dark crust
plates broken apart by glowing fissures. The plates are the sprite's dark patches (one Voronoi
seed per dark local minimum of the sprite, seen from above), the fissures run between them and
open into molten pools where the sprite is bright, so from above the hot spots sit where the
sprite has them. Each plate is a slab tilted a little its own way (they catch the game's light
differently: rock range, D175), with a softened shoulder down into its fissure; the fissure floor
glows (D126: palette colour, strength 1, metallic 1 / rough 0.9 as D173's lava pool) and the
plate edges next to it are embers (part lit, part glowing). Frame 135 is the same rock two palette
steps hotter: every material carries frames={135: i + 2}. D51 outline shell from a sealed copy.

Run: blender --background --python assets/blender/enemies/newshl-115.py
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_newshd_rock as R  # noqa: E402  (Grid.outline: the inner mask's radial outline)

NAME = "newshl-115"
MODEL = f"enemies/{NAME}"
WT = common.repo_root(__file__)
PX = 1 / 12

N = 16             # cube-sphere cuts per face edge (about 0.4 sprite px between vertices)
Q = 2.3            # side profile exponent: fuller shoulders than an ellipse, still round
ZT, ZB = 4.6, 3.6  # crown height and base depth, sprite px (a lump about as deep as it is wide)
SEED = 11
TILT = 0.25         # plate tilt (radians-ish)
RPX = 5.0           # body radius, sprite px (converts plane gaps to px)
HALF0, HALF1 = 0.12, 0.9  # fissure half-width px: a hairline over dark crust, a pool where hot
WALL = 0.32         # lip wall width, px
DEPTH0, DEPTH1 = 0.5, 0.6  # fissure floor depth below the plates, px
GAIN = 1.0
POOL_MIN, POOL_R0, POOL_R1 = 121, 0.27, 0.13  # hot pixels >= this open a round pool of radius R0 + R1*(i-120) px
EMBER = 0.25
CRUST_MIN, CRUST_MAX, CRUST_BIAS = 113, 118, -1.0


def glow_at(i):
    return {119: 0.0, 120: 0.55, 121: 0.8}.get(i, 1.0) if i >= 119 else 0.0


# --- the sprite, read as fields -------------------------------------------------------------------

class Sprite:
    def __init__(self, sprite):
        f = sprite["frames"][0]
        self.w, self.h = f["width"], f["height"]
        self.px = f["pixels"]
        self.g = R.Grid(sprite, NAME)
        inner = self.g.inner
        # Brightness grid: the inner pixels' indices; ring and outside filled from the nearest
        # inner pixels (the ink ring is lighting, not paint).
        val = [[float(self.px[r][c]) if inner[r][c] else None for c in range(self.w)] for r in range(self.h)]
        for _ in range(8):
            nxt = [row[:] for row in val]
            for r in range(self.h):
                for c in range(self.w):
                    if val[r][c] is None:
                        nb = [val[rr][cc] for rr in range(r - 1, r + 2) for cc in range(c - 1, c + 2)
                              if 0 <= rr < self.h and 0 <= cc < self.w and val[rr][cc] is not None]
                        if nb:
                            nxt[r][c] = sum(nb) / len(nb)
            val = nxt
        self.val = val
        self.inner = inner

    def b(self, u, v):
        """Bilinear sprite index at sprite coordinates (u column, v row; pixel centres at +0.5)."""
        a, bb = u - 0.5, v - 0.5
        c0, r0 = math.floor(a), math.floor(bb)
        fa, fb = a - c0, bb - r0

        def at(c, r):
            c = min(max(c, 0), self.w - 1)
            r = min(max(r, 0), self.h - 1)
            return self.val[r][c]
        return ((1 - fa) * (1 - fb) * at(c0, r0) + fa * (1 - fb) * at(c0 + 1, r0)
                + (1 - fa) * fb * at(c0, r0 + 1) + fa * fb * at(c0 + 1, r0 + 1))

    def nearest(self, u, v):
        c, r = int(math.floor(u)), int(math.floor(v))
        c = min(max(c, 0), self.w - 1)
        r = min(max(r, 0), self.h - 1)
        return self.val[r][c]


def build():
    sprite = common.load_sprite(WT, NAME)
    S = Sprite(sprite)
    cu, cv, radii = S.g.outline(steps=144, grow=0.0, smooth=2)

    def to_xy(u, v):
        return (u - S.w / 2) * PX, (S.h / 2 - v) * PX

    cx, cy = to_xy(cu, cv)

    def rho(dz):
        return (1 - abs(dz) ** Q) ** (1 / Q)

    def body(d):
        """Unit direction -> point on the smooth body (outline at the equator)."""
        dx, dy, dz = d
        phi = math.atan2(dy, dx)
        # Grid.outline's angle runs with v pointing down: a = atan2(-dv, du) = atan2(dy, dx).
        rad = R.radius_at(radii, phi) * PX
        rh = rad * rho(dz)
        z = dz * (ZT if dz > 0 else ZB) * PX
        return Vector((cx + rh * math.cos(phi), cy + rh * math.sin(phi), z))

    def uv_of(p):
        return p.x / PX + S.w / 2, S.h / 2 - p.y / PX

    # --- plate seeds: the sprite's dark patches on the top, an even scatter below -----------------
    seeds = []
    for r in range(S.h):
        for c in range(S.w):
            if not S.inner[r][c]:
                continue
            v0 = S.val[r][c]
            nb = [S.val[rr][cc] for rr in range(r - 1, r + 2) for cc in range(c - 1, c + 2)
                  if (rr, cc) != (r, c) and 0 <= rr < S.h and 0 <= cc < S.w]
            if v0 <= 118 and all(v0 <= x for x in nb):
                u, v = c + 0.5, r + 0.5
                x, y = to_xy(u, v)
                phi = math.atan2(y - cy, x - cx)
                rad = R.radius_at(radii, phi) * PX
                t = min(0.97, math.hypot(x - cx, y - cy) / rad)
                dz = (1 - t ** Q) ** (1 / Q)
                k = math.sqrt(max(0.0, 1 - dz * dz))
                seeds.append(Vector((k * math.cos(phi), k * math.sin(phi), dz)).normalized())
    top_seeds = len(seeds)
    rng = random.Random(SEED)
    # Fill the rest of the sphere (sides and base) with a blue-noise scatter of the same spacing.
    min_ang = 0.5
    tries = 0
    while tries < 4000:
        tries += 1
        z = rng.uniform(-1, 1)
        a = rng.uniform(0, 2 * math.pi)
        k = math.sqrt(1 - z * z)
        d = Vector((k * math.cos(a), k * math.sin(a), z))
        if all(d.angle(s) > min_ang for s in seeds):
            seeds.append(d)
    # Each plate is a flat slab: a plane over its seed, tilted a little its own way and set a little
    # in, so the lump is a chunky polyhedron (planar facets catch the game's light differently: the
    # rock range of D175) rather than a smooth egg.
    normals, heights = [], []
    for s in seeds:
        t = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        t -= s * t.dot(s)
        n = (s + (t.normalized() * rng.uniform(0.08, TILT) if t.length > 1e-6 else Vector())).normalized()
        normals.append(n)
        heights.append(rng.uniform(0.95, 0.99))
    print(f"seeds: {top_seeds} from the sprite, {len(seeds) - top_seeds} scattered")
    ang = {}
    hots = [(c + 0.5, r + 0.5, int(S.val[r][c])) for r in range(S.h) for c in range(S.w)
            if S.inner[r][c] and S.val[r][c] >= POOL_MIN]

    def field(d):
        """-> (plate, fissure distance px (negative inside the fissure), radius factor, glow, b)."""
        rs = sorted((heights[i] / max(0.08, d.dot(n)), i) for i, n in enumerate(normals) if d.dot(n) > 0.08)
        (r1, i1), (r2, i2) = rs[0], rs[1]
        key = (min(i1, i2), max(i1, i2))
        if key not in ang:
            ang[key] = max(0.15, normals[i1].angle(normals[i2]))
        e_px = (r2 - r1) / r1 * RPX / ang[key]
        p = body(d) * 1.0
        u, v = uv_of(p)
        b = S.b(u, v)
        g = min(1.0, max(0.0, (b - 118.5) / 5.0))
        half = HALF0 + HALF1 * g
        # Molten pools: where the sprite is hottest the crust is broken through even mid-plate
        # (the sprite's isolated 122-125 spots), so its hot spots sit where it draws them.
        s = e_px - half
        hot = None
        if d.z > -0.2:
            for (hu, hv, hi) in hots:
                sp = math.hypot(u - hu, v - hv) - (POOL_R0 + POOL_R1 * (hi - 120))
                if sp < s:
                    s, hot = sp, hi
        return i1, s, r1, g, (hot if hot is not None else b)

    # --- the mesh: a cube sphere in direction space, cut along the fissure and lip contours --------
    bm = bmesh.new()
    cube = bmesh.ops.create_cube(bm, size=2.0)
    edges = list({e for v in cube["verts"] for e in v.link_edges})
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=N - 1, use_grid_fill=True)
    for v in bm.verts:
        x, y, z = v.co
        sx = x * math.sqrt(max(0.0, 1 - y * y / 2 - z * z / 2 + y * y * z * z / 3))
        sy = y * math.sqrt(max(0.0, 1 - z * z / 2 - x * x / 2 + z * z * x * x / 3))
        sz = z * math.sqrt(max(0.0, 1 - x * x / 2 - y * y / 2 + x * x * y * y / 3))
        v.co = Vector((sx, sy, sz)).normalized()
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    F = {}

    def val(v):
        if v not in F:
            F[v] = field(v.co.normalized())
        return F[v]

    EPS = 0.07
    for level in (0.0, WALL):
        on = set()
        for v in bm.verts:
            if abs(val(v)[1] - level) < EPS:
                on.add(v)
        for e in list(bm.edges):
            a, b = e.verts
            sa, sb = val(a)[1] - level, val(b)[1] - level
            if a in on or b in on or sa * sb >= 0:
                continue
            t = sa / (sa - sb)
            co = (a.co.lerp(b.co, t)).normalized()
            _, nv = bmesh.utils.edge_split(e, a, t)
            nv.co = co
            on.add(nv)
        for f in list(bm.faces):
            lv = [v for v in f.verts if v in on]
            if len(lv) == 2 and not any(lv[1] in e.verts for e in lv[0].link_edges):
                bmesh.ops.connect_verts(bm, verts=lv)
        for v in on:
            F[v] = F.get(v) or field(v.co.normalized())
            p = F[v]
            F[v] = (p[0], level, p[2], p[3], p[4])
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])

    sealed = {}
    bm.verts.index_update()
    # Displace: plates on their planes, the lip rounding down a wall into a glowing fissure floor.
    centre = Vector((cx, cy, 0))
    for v in bm.verts:
        d = v.co.normalized()
        plate, s, r1, g, b = val(v)
        p = body(d)
        rr = max(0.25, (p - centre).length)
        depth = DEPTH0 + DEPTH1 * g
        # Shallow round the waist: the outline from above is the plates' rims, not a bite.
        depth *= 0.1 + 0.9 * min(1.0, abs(d.z) / 0.5) ** 1.5
        if s <= 0:
            k = 0.0
        elif s < WALL:
            t = s / WALL
            k = 1 - (1 - t) ** 2
        else:
            k = 1.0
        scale = r1 - (1 - k) * depth * PX / rr
        sealed[v.index] = centre + (p - centre) * r1  # the plates with no fissures, for the shell
        v.co = centre + (p - centre) * scale
    gain = GAIN
    for v in bm.verts:
        v.co.x = cx + (v.co.x - cx) * gain
        v.co.y = cy + (v.co.y - cy) * gain
        q = sealed[v.index]
        sealed[v.index] = Vector((cx + (q.x - cx) * gain, cy + (q.y - cy) * gain, q.z))

    # --- materials ----------------------------------------------------------------------------------
    mats, slots = [], {}

    def slot(i, kind):
        key = (i, kind)
        if key not in slots:
            if kind == "crust":
                m = common.palette_material(sprite, i, f"{NAME}_crust", metallic=0.0, roughness=0.8,
                                            frames={135: i + 2})
                bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                bsdf.inputs["Specular IOR Level"].default_value = 0.3
            elif kind == "ember":
                m = common.palette_material(sprite, i, f"{NAME}_ember", metallic=0.0, roughness=0.7,
                                            emission_strength=EMBER, frames={135: i + 2})
            else:
                m = common.palette_material(sprite, i, f"{NAME}_melt", metallic=1.0, roughness=0.9,
                                            emission_strength=1.0, frames={135: i + 2})
            slots[key] = len(mats)
            mats.append(m)
        return slots[key]

    def fval(f):
        vals = [F[v] for v in f.verts]
        plates = [x[0] for x in vals]
        return max(plates, key=plates.count), sum(x[1] for x in vals) / len(vals)

    # Plate colour: the sprite's crust shade under the plate (median over its upward faces).
    bm.faces.ensure_lookup_table()
    plate_vals = {}
    for f in bm.faces:
        f.normal_update()
        pl, s = fval(f)
        if s > WALL and f.normal.z > 0.3:
            c = f.calc_center_median()
            plate_vals.setdefault(pl, []).append(S.b(*uv_of(c)))
    plate_idx = {}
    for pl in range(len(seeds)):
        vals = sorted(plate_vals.get(pl, []))
        m = vals[len(vals) // 2] if vals else 116
        plate_idx[pl] = int(min(CRUST_MAX, max(CRUST_MIN, round(m + CRUST_BIAS))))
    for f in bm.faces:
        c = f.calc_center_median()
        hv = sorted(F[v][4] for v in f.verts)
        b = max(S.b(*uv_of(c)), hv[len(hv) // 2])
        pl, s = fval(f)
        if s < 0:  # fissure floor: the sprite's hot colour
            f.material_index = slot(int(min(125, max(120, round(b + 0.5)))), "melt")
        elif s < WALL:  # the wall: an ember a step or two over the crust
            f.material_index = slot(int(min(119, max(plate_idx[pl] + 1, round(b - 1)))), "ember")
        else:
            f.material_index = slot(plate_idx[pl], "crust")
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a, b = e.link_faces
            if a.material_index != b.material_index or a.normal.angle(b.normal, 0) > math.radians(28):
                e.smooth = False
    crust_plate = {}
    bm.faces.index_update()
    for f in bm.faces:
        pl, sv = fval(f)
        if sv >= WALL:
            crust_plate[f.index] = pl
    # The sealed body (fissures closed, a hair inside the plates) for the outline shell (D51): its ink
    # stays on the silhouette and never lies across a fissure.
    sealed_bm = bm.copy()
    sealed_bm.verts.ensure_lookup_table()
    for v in sealed_bm.verts:
        q = sealed[v.index]
        v.co = centre + (q - centre) * 0.985
    coll = common.reset_collection(NAME)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=None)
    sealed_obj = common.mesh_object(f"{NAME}_sealed", sealed_bm, [], coll, smooth=True)
    # Each crust plate shades as one flat slab (its area-weighted normal): chunky rock facets, not
    # a crinkle of triangles; walls and floors keep their own face normals.
    me = obj.data
    acc = {}
    for poly in me.polygons:
        pl = crust_plate.get(poly.index)
        if pl is not None:
            acc[pl] = acc.get(pl, Vector()) + poly.normal * poly.area
    loops = [None] * len(me.loops)
    for poly in me.polygons:
        pl = crust_plate.get(poly.index)
        n = acc[pl].normalized() if pl is not None and acc[pl].length > 0 else poly.normal
        for li in poly.loop_indices:
            loops[li] = n
    me.normals_split_custom_set(loops)
    obj["sealed"] = sealed_obj.name
    print("materials", [m.name for m in mats])
    return obj, coll


def shell_of(obj, coll):
    closed = bpy.data.objects[obj["sealed"]]
    del obj["sealed"]
    sh = common.outline_shell(closed, coll, voxel=0.025, faces=1500, smooth=8, inside=0.0, islands="outer")
    sh.name = sh.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    return sh


def main():
    obj, coll = build()
    sh = shell_of(obj, coll)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    print("triangles", tris, "shell faces", len(sh.data.polygons),
          "bbox px", [round((max(p[i] for p in bb) - min(p[i] for p in bb)) / PX, 2) for i in range(3)])
    sprite = common.load_sprite(WT, NAME)
    common.export_sprite_model(WT, [obj, sh], MODEL, sprite["sprites"])


if __name__ == "__main__":
    main()
