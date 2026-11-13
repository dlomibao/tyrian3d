"""Spiked mace ball (newsha.shp, assembly of 6 pieces, 72 x 56 px).

WHAT IT IS: the head of a flail: a polished forged-steel ball swinging free on its chain (custom52
ground2 spawns that weave x -8..+8, y -8..+8 px/tick with the terrain; the newsha-125/127 rings
stacked beside it are its chain links, separate units). Not a ground object: built round, its
equator lifted 12 px over the base plane, and every piece carries the shared `tyrian_anchor` at the
equator (D181), so the widest outline, which is what the sprite draws, lands on the sprite.

Reading the sprite (72 x 56, ink border 96%: model edge at the inner edge, D74):
- Ball: a sphere, inner radius ~16.4 px about grid (36.5, 28.5); the white cluster upper left is
  sheen, the dark lower right the shadow side (lighting, not paint).
- Four long spikes N/S/E/W on the equator, tip 27 px out, each out of a brass collar ring that
  seats on the ball (brass rows 12-14, 43; columns 20-22, 51).
- Four short stubby spikes on the diagonals (wide roots that square the ball's corners, tips at
  22.6 px), plain steel.
- Crown: an octagonal brass collar (10 px across flats, 5 px hole) with a chrome point in it,
  seen end on: the spike that points at the camera.
- Underside (plain): a matching brass collar and a stub, closed.

Colours (median per region, ink <= 3 and highlights >= 13 left out): ball 8, long spikes 6,
diagonal spikes 6 (5.5), collars 167, crown collar 169, crown point 9.

Coordinates: sprite px, X = column - 36 (east), Y = 28 - row (north), Z up from the base plane;
1 px = 1/12 unit. Pieces cut with common.split_assembly; the outline shell is made from the
sealed whole (D90/D118) and cut open per piece (no seam ink).

Run:
  Blender --background --factory-startup --python assembly-newsha-115.py -- [--pieces DIR]
Exports each piece + its shell (cut open) to public/models/enemies/newsha-<n>.glb and the spriteModels JSON.
(--pieces DIR also writes the whole model there.)
"""

import json
import math
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = common.repo_root(__file__)
NAME = "assembly-newsha-115"
PX = 1 / 12
PIECES = ["newsha-77", "newsha-79", "newsha-81", "newsha-115", "newsha-117", "newsha-119"]
CX0, CY0 = 246, 57  # screen px of grid (36, 28), the Blender origin

# ---- dimensions (px) -----------------------------------------------------------------------------
BC = Vector((0.5, -0.5, 12.0))  # ball centre: grid (36.5, 28.5), equator 12 px up
RB = 16.35                      # ball radius
ANCHOR = BC.z * PX              # tyrian_anchor: the equator on the camera ray (D181)
SEAM_W, SEAM_D = 0.36, 0.28     # equatorial weld groove half width, depth

# long spike: (t from ball centre, radius); collar: (t, radius)
SPIKE = [(15.6, 3.15), (17.0, 3.05), (18.6, 2.80), (21.4, 2.22), (23.6, 1.55), (25.4, 0.85), (26.6, 0.32)]
SPIKE_TIP = 27.3
COLLAR = [(13.6, 4.45), (15.9, 4.45), (16.35, 4.15), (16.55, 3.55), (16.6, 3.25)]
# a narrow raised ring part way up the spike (machined step), in the spike material's dark tone
# diagonal stub spike
DIAG = [(14.2, 3.0), (16.0, 2.8), (17.0, 2.2), (18.2, 1.6), (19.6, 1.1), (21.0, 0.6), (21.9, 0.28)]
DIAG_TIP = 22.5
DIAG_Z = 0.0                    # elevation of the diagonal spikes (deg)

# crown: octagonal collar and the point in it
CROWN_XY = Vector((1.0, -1.0))  # sprite octagon centre: grid (37, 29)
OCT_AP = 4.85                   # outer apothem (10 px across flats, inner edge of the ink)
OCT_IN = 2.6                    # hole apothem
OCT_H = 1.3                     # collar height above where it meets the ball rim
CROWN_PT = [(0.0, 2.5), (0.9, 2.3), (2.0, 1.75), (3.1, 1.0), (3.9, 0.4)]
CROWN_TIP = 4.5

# palette
M_BALL, M_SEAM, M_SPIKE, M_STEP, M_DIAG, M_COLLAR, M_CROWN, M_POINT = range(8)
PAL = {M_BALL: 8, M_SEAM: 6, M_SPIKE: 6, M_STEP: 5, M_DIAG: 6, M_COLLAR: 167, M_CROWN: 169, M_POINT: 9}


# ---- helpers -------------------------------------------------------------------------------------

def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson) through (xs, ys)."""
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
        i = max(k for k in range(n - 1) if xs[k] <= x)
        t = (x - xs[i]) / h[i]
        h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
        h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(Vector(p))

    def f(self, vs, mat, smooth=True):
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        face.smooth = smooth
        return face


def basis(d):
    d = Vector(d).normalized()
    a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, 1, 0))
    u = d.cross(a).normalized()
    v = d.cross(u).normalized()
    return d, u, v


def lathe(M, origin, d, prof, sides, mats, tip=None, cap0=True, phase=0.5, polygon=False):
    """Solid of revolution along d from origin: prof [(t, r)], mats per band (or one int).
    polygon=True: r is the apothem of a regular polygon (flat sides)."""
    d, u, v = basis(d)
    o = Vector(origin)
    sc = 1 / math.cos(math.pi / sides) if polygon else 1.0
    rings = []
    for t, r in prof:
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + phase) / sides
            ring.append(M.v(o + d * t + (u * math.cos(a) + v * math.sin(a)) * r * sc))
        rings.append(ring)
    mats = mats if isinstance(mats, (list, tuple)) else [mats] * (len(prof))
    for i in range(len(rings) - 1):
        for k in range(sides):
            j = (k + 1) % sides
            M.f((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]), mats[i], smooth=not polygon)
    if cap0:
        M.f(list(reversed(rings[0])), mats[0], smooth=False)
    if tip is not None:
        pt = M.v(o + d * tip)
        for k in range(sides):
            M.f((rings[-1][k], rings[-1][(k + 1) % sides], pt), mats[-1])
    else:
        M.f(rings[-1], mats[-1], smooth=False)


def dense(prof, step):
    """Resample a (t, r) profile with pchip at about `step` px."""
    ts, rs = [p[0] for p in prof], [p[1] for p in prof]
    f = pchip(ts, rs)
    n = max(2, int(math.ceil((ts[-1] - ts[0]) / step)))
    return [(ts[0] + (ts[-1] - ts[0]) * i / n, f(ts[0] + (ts[-1] - ts[0]) * i / n)) for i in range(n + 1)]


# ---- parts ---------------------------------------------------------------------------------------

def ball(M):
    """The forged ball: two hemispheres with a weld groove round the equator."""
    seg = 64
    lats = [-90 + 7.5 * i for i in range(1, 12)]  # -82.5 .. -7.5
    g = math.degrees((SEAM_W + 0.35) / RB)
    s = math.degrees(SEAM_W / RB)
    rows = [(la, 0.0) for la in lats if la < -g - 2]
    rows += [(-g, 0.0), (-s, -SEAM_D), (s, -SEAM_D), (g, 0.0)]
    rows += [(-la, 0.0) for la in reversed(lats) if -la > g + 2]
    grid = []
    for la, dr in rows:
        ring = []
        for k in range(seg):
            a = 2 * math.pi * (k + 0.5) / seg
            r = RB + dr
            ring.append(M.v(BC + Vector((math.cos(a) * math.cos(math.radians(la)),
                                         math.sin(a) * math.cos(math.radians(la)),
                                         math.sin(math.radians(la)))) * r))
        grid.append((ring, dr))
    for i in range(len(grid) - 1):
        (r0, d0), (r1, d1) = grid[i], grid[i + 1]
        mat = M_SEAM if (d0 < 0 or d1 < 0) else M_BALL
        for k in range(seg):
            j = (k + 1) % seg
            M.f((r0[k], r0[j], r1[j], r1[k]), mat)
    bot, top = M.v(BC - Vector((0, 0, RB))), M.v(BC + Vector((0, 0, RB)))
    for k in range(seg):
        j = (k + 1) % seg
        M.f((grid[0][0][j], grid[0][0][k], bot), M_BALL)
        M.f((grid[-1][0][k], grid[-1][0][j], top), M_BALL)


def long_spike(M, d):
    # brass collar ring seated on the ball
    lathe(M, BC, d, COLLAR, 28, M_COLLAR)
    # the spike: a machined step ring at its root, then a pchip ogive to the point
    sp = dense(SPIKE, 0.8)
    t0 = sp[0][0]
    root = [(t0 - 2.0, 3.25), (t0 + 0.9, 3.25), (t0 + 1.15, 3.0)]
    lathe(M, BC, d, root, 20, M_STEP)
    lathe(M, BC, d, [(t0 + 1.1, sp[0][1] * 0.97)] + [p for p in sp if p[0] > t0 + 1.3], 20, M_SPIKE,
          tip=SPIKE_TIP)


def diag_spike(M, d):
    sp = dense(DIAG, 0.7)
    lathe(M, BC, d, sp, 16, M_DIAG, tip=DIAG_TIP)


def crown(M, up=True):
    """The octagonal brass collar on the crown and the chrome point in it (up=False: a plain
    copy under the ball, its point a short stub)."""
    sgn = 1 if up else -1
    xy = CROWN_XY if up else Vector((BC.x, BC.y))
    off = (Vector((xy.x, xy.y)) - Vector((BC.x, BC.y))).length
    zc = BC.z + sgn * math.sqrt(RB ** 2 - off ** 2)                       # ball on the axis
    zr = BC.z + sgn * math.sqrt(max(0.0, RB ** 2 - (off + OCT_AP * 1.08) ** 2))  # ball under the corners
    base = Vector((xy.x, xy.y, zr - sgn * 1.0))
    d = Vector((0, 0, sgn))
    h = abs(zc + sgn * OCT_H - base.z)  # collar top
    tin = abs(zc - base.z) - 0.4         # hole floor, under the ball's surface
    ch = 0.45
    outer = [(0.0, OCT_AP), (h - ch, OCT_AP), (h, OCT_AP - ch)]
    inner = [(h, OCT_IN + ch * 0.6), (h - ch * 0.6, OCT_IN), (tin, OCT_IN)]
    lathe_ring(M, base, d, outer, inner, 8, M_CROWN)
    if up:
        prof = [(tin - 0.2, 2.5), (h - 0.3, 2.5)] + [(h + t, r) for t, r in CROWN_PT[1:]]
        lathe(M, base, d, dense(prof, 0.6), 18, M_POINT, tip=h + CROWN_TIP)
    else:
        lathe(M, base, d, [(tin - 0.2, 2.3), (h + 0.3, 2.1), (h + 1.2, 1.2)], 12, M_POINT, tip=h + 1.8)


def lathe_ring(M, origin, d, outer, inner, sides, mat):
    """A closed ring (nut) of a regular polygon: outer profile up, inner profile down, flat sides."""
    d, u, v = basis(d)
    o = Vector(origin)
    sc = 1 / math.cos(math.pi / sides)
    prof = outer + inner
    rings = []
    for t, r in prof:
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(M.v(o + d * t + (u * math.cos(a) + v * math.sin(a)) * r * sc))
        rings.append(ring)
    n = len(rings)
    for i in range(n):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for k in range(sides):
            j = (k + 1) % sides
            M.f((r0[k], r0[j], r1[j], r1[k]), mat, smooth=False)


def build():
    M = Mesh()
    ball(M)
    for d in ((0, 1, 0), (0, -1, 0), (-1, 0, 0), (1, 0, 0)):
        long_spike(M, d)
    e = math.radians(DIAG_Z)
    for dx, dy in ((-1, 1), (1, 1), (-1, -1), (1, -1)):
        c = math.cos(e) / math.sqrt(2)
        diag_spike(M, (dx * c, dy * c, math.sin(e)))
    crown(M, True)
    crown(M, False)
    bm = M.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.scale(bm, vec=(PX, PX, PX), verts=bm.verts)
    return bm


def materials(sprite):
    spec_hi = 0.5 * ((1.4 / 3.4) ** 2 / 0.04)  # Specular IOR Level for F0 of IOR 2.4 (D176)

    def pal(slot, metallic, rough, coat=0.0, coat_r=0.1, spec=None):
        m = common.palette_material(sprite, PAL[slot], f"nsha115A_{slot}", metallic=metallic, roughness=rough)
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = coat_r
        if spec is not None:
            b.inputs["Specular IOR Level"].default_value = spec
        return m
    return [
        pal(M_BALL, 0.15, 0.36, 0.5, 0.2),   # polished steel ball (D176 F0)
        pal(M_SEAM, 0.3, 0.55),                        # weld groove
        pal(M_SPIKE, 0.55, 0.16, 1.0, 0.08, spec_hi),  # chrome spikes
        pal(M_STEP, 0.5, 0.35),                        # spike root ring
        pal(M_DIAG, 0.55, 0.2, 1.0, 0.1, spec_hi),     # diagonal spikes
        pal(M_COLLAR, 0.35, 0.4),                     # brass collars, satin
        pal(M_CROWN, 0.35, 0.38),                      # crown collar
        pal(M_POINT, 0.55, 0.16, 1.0, 0.08, spec_hi),  # crown point
    ]


def make_object(bm, name, mats, coll):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(40))
    return obj


def split_open(obj, layout, coll):
    """split_assembly's cut without capping (for the outline shell: no ink line at the seams)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        out[name] = sh
    return out


def tris(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def merged_sprite():
    data = common.load_sprite(ROOT, PIECES[0])
    for n in PIECES:
        data["colors"].update(common.load_sprite(ROOT, n)["colors"])
    return data


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    pieces_dir = Path(argv[argv.index("--pieces") + 1]) if "--pieces" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    bm = build()
    whole = make_object(bm, NAME, mats, coll)
    bm.free()
    shell = common.outline_shell(whole, coll, voxel=0.02, faces=5000, smooth=6, inside=0.006)
    shell.name = f"{NAME}_outline"
    stats = {"whole": tris(whole), "shell": tris(shell)}
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    pieces = common.split_assembly(whole, layout, coll)
    shells = split_open(shell, layout, coll)
    for n in PIECES:
        stats[n] = tris(pieces[n])
        for o in (pieces[n], shells[n]):
            o["tyrian_anchor"] = ANCHOR
        pieces[n].data.set_sharp_from_angle(angle=math.radians(40))
    whole["tyrian_anchor"] = ANCHOR
    shell["tyrian_anchor"] = ANCHOR
    for n in PIECES:
        data = common.load_sprite(ROOT, n)
        common.export_sprite_model(ROOT, [pieces[n], shells[n]], f"enemies/{n}", data["sprites"])
    if pieces_dir:
        common.export_glb([whole, shell], pieces_dir / f"{NAME}.glb")
    print("STATS", json.dumps(stats))


if __name__ == "__main__":
    main()
