"""newsh8-1: the red twin-boom piston rig of 3.4 IXMUCANE and 3.9 SAWBLADES (newsh8.shp
frames 1, 3, 5, 7; four models newsh8-1, -f2, -f3, -f4), hard surface (D50-D53, D65).

What it is: a ground machine that creeps south. Two long red skid booms (pointed at the south end,
rounded at the north) are tied by a grey crossbar rod (row 9) that rides on saddles over the booms
and bands round a red sleeve on the centre line. A hydraulic ram slides through the sleeve: grey
end cap, red head with a red lamp ring and a yellow lens on top (rows t+3), a wider pink barrel
with a grey guide line down its left flank, a dark collar and a rounded red nose. Below the
crossbar dark grey brackets join the sleeve to collar blocks on the booms' inner faces. On the
outer face of each boom a grey carriage (dark red end plates) slides on a slim rail. Over the four
frames the ram slides 1 px south per frame (its lamp sinks into the sleeve on frames 5 and 7)
while the carriages slide 1 px north: an inchworm walker.

Sprite reading (the sprite is authoritative): axis between columns 11 and 12 (edge x 11.5). Ram
top row t = 3 + k (ink), cap t+1, head t+2..t+5 (lamp t+3), barrel 5 px wide t+6..t+9 (collar
t+9), nose 3 px wide t+10..t+12. Carriages rows 4-k..9-k (edges), cols 3-4 / 18-19. Booms cols
4-6 / 16-18 rows 2-24, narrowing to 2 px at row 18 and 1 px at row 22. The pink inner edges of
the booms, the pink spots on the sleeve and the crossbar's white spots are sheen (rubric).

Run: blender --background --python assets/blender/enemies/newsh8-1.py
Exports public/models/enemies/newsh8-1[-f2..-f4].glb (model + outline shell) and the spriteModels entries.
"""

import bisect
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
NAME = "newsh8-1"
FRAMES = [1, 3, 5, 7]
PX = 1 / 12
W, H = 24, 28
AX = 11.5  # mirror axis (edge coordinate)


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


# --- helpers (copied from usp_talon / newsh8-19 design A, not shared) ----------------------------

def pchip(xs, ys):
    """Monotone cubic interpolation (copy of usp_talon.pchip)."""
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


class Mesh:
    """A bmesh in sprite px (x across = column edge coordinate, v = row edge coordinate, south is
    +v, z up)."""

    def __init__(self):
        self.bm = bmesh.new()

    def loft(self, rings, mats, cap0=True, cap1=True, flat=False):
        bm = self.bm
        vs = [[bm.verts.new(p) for p in r] for r in rings]
        mats = mats if isinstance(mats, list) else [mats] * (len(rings) - 1)
        for i, (r0, r1) in enumerate(zip(vs, vs[1:])):
            n = max(len(r0), len(r1))
            for k in range(n):
                j = (k + 1) % n
                if len(r0) == 1:
                    q = (r0[0], r1[k], r1[j])
                elif len(r1) == 1:
                    q = (r0[k], r1[0], r0[j])
                else:
                    q = (r0[k], r1[k], r1[j], r0[j])
                f = bm.faces.new(q)
                f.material_index = mats[i]
                f.smooth = not flat
        if cap0 and len(vs[0]) > 2:
            f = bm.faces.new(list(reversed(vs[0])))
            f.material_index = mats[0]
        if cap1 and len(vs[-1]) > 2:
            f = bm.faces.new(vs[-1])
            f.material_index = mats[-1]

    def lathe_v(self, profile, cx, cz, sides=20, phase=0.0):
        """Solid of revolution about the v axis through (cx, cz): profile [(v, r, mat)]; the band
        to point i+1 takes point i+1's mat; r = 0 is a pole."""
        rings = []
        for v, r, _ in profile:
            if r <= 1e-6:
                rings.append([(cx, v, cz)])
            else:
                rings.append([(cx + r * math.cos(phase + 2 * math.pi * k / sides), v,
                               cz + r * math.sin(phase + 2 * math.pi * k / sides)) for k in range(sides)])
        self.loft(rings, [m for _, _, m in profile[1:]], cap0=False, cap1=False)

    def lathe_x(self, profile, cv, cz, sides=16):
        """Solid of revolution about the x axis through (v = cv, z = cz): profile [(x, r, mat)]."""
        rings = []
        for x, r, _ in profile:
            if r <= 1e-6:
                rings.append([(x, cv, cz)])
            else:
                rings.append([(x, cv + r * math.cos(2 * math.pi * k / sides),
                               cz + r * math.sin(2 * math.pi * k / sides)) for k in range(sides)])
        self.loft(rings, [m for _, _, m in profile[1:]], cap0=False, cap1=False)

    def lathe_z(self, profile, cx, cv, sides=12):
        """Solid of revolution about a vertical axis through (cx, cv): profile [(z, r, mat)]."""
        rings = []
        for z, r, _ in profile:
            if r <= 1e-6:
                rings.append([(cx, cv, z)])
            else:
                rings.append([(cx + r * math.cos(2 * math.pi * k / sides), cv + r * math.sin(2 * math.pi * k / sides), z)
                              for k in range(sides)])
        self.loft(rings, [m for _, _, m in profile[1:]], cap0=False, cap1=False)

    def to_object(self, name, mats, coll, smooth_angle=34.0):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        me.set_sharp_from_angle(angle=math.radians(smooth_angle))
        return obj


def rrect(x0, x1, z0, z1, r_tl, r_tr, r_br, r_bl, v, seg=3):
    """A rounded-rectangle section in the x-z plane at v (corner radii; equal point count always)."""
    pts = []
    for (cx, cz, r, a0) in ((x1 - r_tr, z1 - r_tr, r_tr, 0), (x0 + r_tl, z1 - r_tl, r_tl, 90),
                            (x0 + r_bl, z0 + r_bl, r_bl, 180), (x1 - r_br, z0 + r_br, r_br, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), v, cz + r * math.sin(a)))
    return pts


def box(m, x0, x1, v0, v1, z0, z1, ch, mat, chv=None):
    """A chamfered box: a loft along v of rounded sections with chamfered ends."""
    chv = ch if chv is None else chv
    c = min(ch, (x1 - x0) / 2.01, (z1 - z0) / 2.01)
    rings = []
    for v, inset in ((v0, chv), (v0 + chv, 0.0), (v1 - chv, 0.0), (v1, chv)):
        e = min(inset, c * 0.95)
        rings.append(rrect(x0 + e, x1 - e, z0 + e, z1 - e, c - e + 0.02, c - e + 0.02, c - e + 0.02, c - e + 0.02, v, seg=1))
    m.loft(rings, mat, flat=True)


def mirror_x(x):
    return 2 * AX - x


def spec_level(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level
    return mat


def shells_for(obj, coll, voxel=0.010, faces=2500, smooth=4, inside=0.003):
    """D51 outline shell from the sealed mesh (D90/D118: no culled copy; held a hair inside). Unlike
    common.outline_shell it keeps every outer island (the known largest-island bug), dropping only
    islands enclosed by another's bounding box (inner cavities)."""
    bpy.context.view_layer.update()
    me = obj.data.copy()
    me.materials.clear()
    sh = bpy.data.objects.new(f"{obj.name}_outline", me)
    coll.objects.link(sh)
    sh.matrix_world = obj.matrix_world.copy()
    rm = sh.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    common._apply_modifiers(sh)
    bm = bmesh.new()
    bm.from_mesh(sh.data)
    bm.verts.ensure_lookup_table()
    seen, islands = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append(x)
            stack.extend(e.other_vert(x) for e in x.link_edges)
        islands.append(isl)

    def bbox(isl):
        xs, ys, zs = [v.co.x for v in isl], [v.co.y for v in isl], [v.co.z for v in isl]
        return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
    boxes = [bbox(i) for i in islands]

    def inside_of(a, b):
        return all(b[2 * i] <= a[2 * i] + 1e-6 and a[2 * i + 1] <= b[2 * i + 1] + 1e-6 for i in range(3)) and a != b
    drop = set()
    for i, a in enumerate(boxes):
        if len(islands[i]) < 30 or any(inside_of(a, b) for j, b in enumerate(boxes) if j != i):
            drop.add(i)
    kill = {v.index for i in drop for v in islands[i]}
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index in kill], context="VERTS")
    bm.to_mesh(sh.data)
    bm.free()
    print(f"SHELL {obj.name}: {len(islands)} islands, kept {len(islands) - len(drop)}")
    sm = sh.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(sh.data.polygons)
    if n > faces:
        dec = sh.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    common._apply_modifiers(sh)
    if inside > 0:
        sw = sh.modifiers.new("inside", "SHRINKWRAP")
        sw.target = obj
        sw.wrap_method = "NEAREST_SURFACEPOINT"
        sw.wrap_mode = "INSIDE"
        sw.offset = -inside
        common._apply_modifiers(sh)
    sh.data.shade_smooth()
    sh.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    sh["tyrian_outline"] = True
    return sh


# --- materials ------------------------------------------------------------------------------------

BOOM, DARK, CARR, ROD, BRK, HEAD, LAMP, LENS, BARREL, NOSE, LINE, COLLAR, BOLT = range(13)


def materials(sprite):
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    m = [
        pal(70, metallic=0.3, roughness=0.36),  # BOOM: booms, sleeve, collar blocks (satin red)
        pal(67, metallic=0.4, roughness=0.55),   # DARK: grooves, carriage end plates, barrel collar
        pal(8, metallic=0.55, roughness=0.34),    # CARR: carriages, ram end cap
        pal(7, metallic=0.55, roughness=0.32),    # ROD: crossbar, its bands and saddles, rails
        pal(4, metallic=0.6, roughness=0.45),    # BRK: dark grey brackets under the crossbar
        pal(69, metallic=0.45, roughness=0.45),  # HEAD: ram head
        pal(117, metallic=1.0, roughness=0.85, emission_strength=1.0),  # LAMP ring (D126/D173)
        pal(124, metallic=1.0, roughness=0.85, emission_strength=1.0),  # LENS (yellow)
        pal(75, metallic=0.3, roughness=0.36),  # BARREL: pink ram barrel
        pal(71, metallic=0.45, roughness=0.4),   # NOSE: ram nose
        pal(6, metallic=0.7, roughness=0.36),    # LINE: grey guide line on the barrel
        pal(68, metallic=0.4, roughness=0.5),    # COLLAR: sleeve's south lip
        pal(10, metallic=0.75, roughness=0.3),   # BOLT heads
    ]
    for i in (BOOM, DARK, HEAD, BARREL, NOSE, COLLAR):
        spec_level(m[i], 0.7)
    return m


# --- the parts (sprite px, left side; mirrored) ---------------------------------------------------

BOOM_Z0 = 0.35


def boom(m, side):
    """A skid boom: outer edge straight at x 4.0, inner edge 7.0 (rows 3-17), 6.0 (18-21), 5.0
    (22-24), rounded north end, pointed south end; rounded section with a softer inner-top edge."""
    f_in = pchip([1.45, 1.8, 2.3, 3.1, 17.3, 18.7, 20.5, 21.6, 22.8, 24.2, 24.8, 25.1],
                 [4.75, 5.6, 6.3, 6.95, 6.95, 6.15, 6.0, 5.85, 5.15, 5.0, 4.85, 4.55])
    f_out = pchip([1.45, 1.8, 2.3, 3.0, 22.0, 24.3, 24.85, 25.1], [4.25, 4.08, 4.0, 4.0, 4.0, 4.05, 4.2, 4.4])
    f_zt = pchip([1.45, 1.8, 2.3, 3.2, 15.5, 19.0, 22.0, 24.6, 25.1], [1.6, 2.8, 3.6, 4.1, 4.1, 3.5, 3.0, 2.1, 1.3])
    grooves = [15.0, 19.6]
    stations = sorted(set([1.45, 1.6, 1.8, 2.05, 2.3, 2.7, 3.1, 4.5, 6.5, 8.5, 10.5, 12.5, 14.0, 16.0, 17.0, 17.6,
                           18.1, 18.6, 19.2, 20.5, 21.3, 21.8, 22.3, 22.8, 23.5, 24.2, 24.6, 24.85, 25.0, 25.1]))
    stations = [v for v in stations if v <= 25.1]
    rings, mats = [], []
    gd = 0.13

    def sec(v, inset=0.0):
        a, b, z1 = f_out(v), f_in(v), f_zt(v)
        w = b - a
        hz = z1 - BOOM_Z0
        ro = min(0.55, w * 0.3, hz * 0.3)
        ri = min(1.0, w * 0.45, hz * 0.45)
        rb = min(0.35, w * 0.2, hz * 0.2)
        x0, x1 = (a, b) if side < 0 else (mirror_x(b), mirror_x(a))
        rl, rr = (ro, ri) if side < 0 else (ri, ro)
        return rrect(x0 + inset, x1 - inset, BOOM_Z0 + inset * 0.3, z1 - inset, rl, rr, rb, rb, v, seg=3)
    for v in stations:
        g = next((g for g in grooves if g - 0.4 < v < g + 0.6), None)
        rings.append(sec(v))
        mats.append(BOOM)
    # grooves: inserted as step rings
    out_r, out_m = [], []
    for i, v in enumerate(stations):
        out_r.append(rings[i])
        out_m.append(BOOM)
        for g in grooves:
            if v <= g < (stations[i + 1] if i + 1 < len(stations) else 99):
                for vv, ins, mm in ((g, 0.0, BOOM), (g, gd, DARK), (g + 0.22, gd, DARK), (g + 0.22, 0.0, DARK)):
                    out_r.append(sec(vv, ins))
                    out_m.append(mm)
    m.loft(out_r, out_m[1:], cap0=True, cap1=True)
    # North end cap: grey bumper plate on the rounded nose? (no: the sprite draws red) - none.
    # Slim rail on the outer face where the carriage runs (rows 1.8-10.2).
    xr0, xr1 = 3.72, 4.15
    if side > 0:
        xr0, xr1 = mirror_x(xr1), mirror_x(xr0)
    box(m, xr0, xr1, 2.2, 10.6, 1.45, 2.85, 0.12, ROD)


def carriage(m, side, k):
    """Grey carriage on the boom's outer face, rows 4-k..10-k (edges); dark red end plates."""
    v0 = 4.0 - k
    v1 = 10.0 - k
    if k == 3:
        v0 = 1.55  # the sprite's top ring row swallows row 1 on frame 7
    x0, x1 = 3.02, 5.35
    pl = 0.7
    if side > 0:
        x0, x1 = mirror_x(x1), mirror_x(x0)
    # end plates (slightly taller, same plan width)
    box(m, x0, x1, v0, v0 + pl, 0.55, 4.55, 0.18, DARK)
    box(m, x0, x1, v1 - pl, v1, 0.55, 4.55, 0.18, DARK)
    # body
    bx0, bx1 = (x0 + 0.08, x1) if side < 0 else (x0, x1 - 0.08)
    box(m, bx0, bx1, v0 + pl - 0.05, v1 - pl + 0.05, 0.75, 4.4, 0.3, CARR, chv=0.08)
    # a raised clamp bar across its top and two bolts
    cx = (x0 + x1) / 2
    vm = (v0 + v1) / 2
    for dv in (-1.2, 1.2):
        if v0 + pl + 0.3 < vm + dv < v1 - pl - 0.3:
            m.lathe_z([(4.3, 0.0, BOLT), (4.3, 0.36, BOLT), (4.62, 0.36, BOLT), (4.7, 0.22, BOLT), (4.7, 0.0, BOLT)],
                      cx + (0.15 if side < 0 else -0.15), vm + dv, sides=6)


def frame_parts(m):
    """Collar blocks on the booms' inner faces (rows 8-13.6), saddles under the crossbar, the
    crossbar rod (row 9), dark brackets (rows 10-13) and the sleeve (rows 8-11)."""
    for side in (-1, 1):
        f = (lambda x: x) if side < 0 else mirror_x

        def bx(x0, x1, *a, **kw):
            a0, a1 = sorted((f(x0), f(x1)))
            box(m, a0, a1, *a, **kw)
        bx(6.4, 8.0, 8.05, 13.6, 0.45, 4.25, 0.3, BOOM)          # collar block
        bx(4.9, 7.7, 8.85, 10.15, 3.7, 4.85, 0.2, ROD)           # saddle for the rod
        bx(7.6, 9.6, 10.05, 13.0, 1.0, 3.5, 0.25, BRK)           # bracket to the sleeve
        # bolt on the collar block's top
        m.lathe_z([(4.15, 0.0, BOLT), (4.15, 0.33, BOLT), (4.42, 0.33, BOLT), (4.5, 0.2, BOLT), (4.5, 0.0, BOLT)],
                  f(7.2), 12.4, sides=6)
    # crossbar rod with turned end caps
    zc, r = 5.0, 0.62
    m.lathe_x([(5.05, 0.0, ROD), (5.05, r * 0.7, ROD), (5.2, r, ROD), (mirror_x(5.2), r, ROD),
               (mirror_x(5.05), r * 0.7, ROD), (mirror_x(5.05), 0.0, ROD)], 9.5, zc, sides=14)
    # sleeve (rows 8-11): chamfered lips, a grey band where the crossbar passes, a darker south lip
    R = 2.6
    zs = SLEEVE_Z
    m.lathe_v([(7.98, 1.55, BOOM), (7.98, 2.25, BOOM), (8.1, R - 0.05, BOOM), (8.3, R, BOOM),
               (8.95, R, BOOM), (8.95, R + 0.22, ROD), (10.05, R + 0.22, ROD), (10.05, R, BOOM),
               (10.4, R, BOOM), (10.4, R - 0.02, COLLAR), (10.85, R - 0.05, COLLAR), (11.02, 2.3, COLLAR),
               (11.02, 1.6, COLLAR)], AX, zs, sides=20)
    # close the sleeve's ends round the ram (inner bores, so it reads as a sleeve end-on)
    m.lathe_v([(7.98, 1.55, DARK), (8.6, 1.55, DARK), (8.6, 0.0, DARK)], AX, zs, sides=20)
    m.lathe_v([(11.02, 1.6, DARK), (10.4, 1.6, DARK), (10.4, 0.0, DARK)], AX, zs, sides=20)
    # the sleeve's belly support onto the brackets (closed, plain)
    box(m, 9.4, 13.6, 9.6, 11.0, 0.6, 1.6, 0.2, BRK)


SLEEVE_Z = 3.45


def ram(m, k):
    """The ram, its top (ink) row t = 3 + k."""
    t = 3 + k
    z = SLEEVE_Z
    rh = 1.42   # head radius (3 px wide)
    rb = 2.42   # barrel radius (5 px wide)
    prof = [
        (t + 0.95, 0.0, CARR), (t + 0.95, 0.85, CARR), (t + 1.02, rh - 0.12, CARR), (t + 1.15, rh, CARR),
        (t + 1.85, rh, CARR), (t + 1.85, rh - 0.1, DARK), (t + 2.0, rh - 0.1, DARK), (t + 2.0, rh - 0.02, HEAD),
        (t + 2.95, rh - 0.02, HEAD), (t + 2.95, rh + 0.1, LAMP), (t + 4.0, rh + 0.1, LAMP), (t + 4.0, rh - 0.02, HEAD),
        (t + 5.7, rh - 0.02, HEAD), (t + 5.9, rh + 0.25, BARREL), (t + 6.05, rb - 0.15, BARREL), (t + 6.2, rb, BARREL),
        (t + 7.55, rb, BARREL), (t + 7.55, rb - 0.1, DARK), (t + 7.7, rb - 0.1, DARK), (t + 7.7, rb, BARREL),
        (t + 8.85, rb, BARREL), (t + 8.95, rb - 0.12, DARK), (t + 9.0, rb - 0.08, DARK), (t + 9.85, rb - 0.08, DARK),
        (t + 10.0, rb - 0.35, DARK), (t + 10.0, 1.55, NOSE), (t + 11.6, 1.55, NOSE), (t + 12.2, 1.42, NOSE),
        (t + 12.6, 1.15, NOSE), (t + 12.88, 0.7, NOSE), (t + 13.0, 0.0, NOSE),
    ]
    m.lathe_v(prof, AX, z, sides=18, phase=math.pi / 18)
    # yellow lens on the lamp ring's top centre
    m.lathe_z([(z + rh - 0.1, 0.0, LENS), (z + rh - 0.1, 0.5, LENS), (z + rh + 0.22, 0.46, LENS),
               (z + rh + 0.4, 0.3, LENS), (z + rh + 0.46, 0.0, LENS)], AX, t + 3.5, sides=10)
    # grey guide line down the barrel's upper-left flank (the sprite's column 9)
    a = math.radians(140)
    lx, lz = AX + (rb - 0.05) * math.cos(a), z + (rb - 0.05) * math.sin(a)
    m.lathe_v([(t + 6.3, 0.0, LINE), (t + 6.3, 0.32, LINE), (t + 6.45, 0.45, LINE), (t + 8.75, 0.45, LINE),
               (t + 8.9, 0.32, LINE), (t + 8.9, 0.0, LINE)], lx, lz, sides=8)


def build(sprite, k, coll_name):
    coll = common.reset_collection(coll_name)
    m = Mesh()
    for side in (-1, 1):
        boom(m, side)
        carriage(m, side, k)
    frame_parts(m)
    ram(m, k)
    obj = m.to_object(coll_name, materials(sprite), coll)
    # sprite px -> Blender (1/12 px; sprite up = +Y)
    for vtx in obj.data.vertices:
        x, v, z = vtx.co
        vtx.co = Vector(((x - W / 2) * PX, (H / 2 - v) * PX, z * PX))
    obj.data.update()
    obj.data.set_sharp_from_angle(angle=math.radians(34))
    sh = shells_for(obj, coll)
    return obj, sh


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    for k, frame in enumerate(FRAMES):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj, sh = build(sprite, k, name)
        assert len(sh.data.polygons) > 0, f"{sh.name}: empty outline shell"
        common.export_sprite_model(ROOT, [obj, sh], f"enemies/{name}", [{**base, "frames": [frame]}])


if __name__ == "__main__":
    main()
