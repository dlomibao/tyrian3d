"""assembly-newsh5-229, design A: the grey and red gunship of SAVARA IV and APPROACH (episode 4,
4.3 main=16 and 4.19 main=47), one craft of three units: newsh5-229 + newsh5-231 (the 48x28 wing and
shoulder section) and newsh5-268 (the 24x28 torpedo fuselage and nose) hanging under its centre at
+12/+28 px, all on one link. It flies NOSE DOWN the screen (the sky-layer motion is y +1..+9), so the
bottom of the sprite is the front.

What it is (read from the 48x56 composite):
- a round grey fuselage (9 px across) from a short tail cone at row 2 to a pointed nose at row 51,
  with a joint ring where the nose cone starts (row 40), a dark wrap-around sensor window on the nose
  (rows 40-42; its 1 px white glint is sheen), four dark vents on the forward flanks (rows 34-38) and
  a circumferential panel line at row 25 (the dark band); a dorsal channel between two rails on the
  aft body (the dark centre line between two lit lines, rows 17-25);
- a broad rounded shoulder housing over the aft fuselage (rows 9-16, 17 px), with a red armoured
  dorsal hump on it (the red shield shape, rows 10-15), a thin red dorsal fin running from the hump
  back over the tail (the light red stripe, rows 1-11);
- two grey tailplanes at the very back (rows 2-4) carried on red root strakes that sweep forward
  and down into the fuselage (rows 5-9);
- two swept-back grey wings (rows 14-32) at mid fuselage height with a little anhedral, their root
  leading edges running forward to strake points beside the nose (rows 29-32, drawn in 268), a
  raised panel on each wing behind a panel line parallel to the leading edge (the light/dark
  diagonal lines), a red blister on each trailing-edge root (rows 16-17);
- red intake fairings in the wing roots beside the fuselage (rows 15-28);
- a long gun on each wing tip: grey breech (rows 13-20) and red barrel pointing forward (rows 20-27).
Grey satin steel, red painted panels. The sprite's dark right-hand halves are shade, its bright
streaks sheen: lighting, not paint (rubric).

Built once in assembly pixel coordinates (x = pixel column edge, y = row edge, down, z up; Blender
X = (x - 24) / 12, Y = (14 - y) / 12, Z = z / 12, origin at the centre of 229+231), mirrored about the
centre of pixel column 24 (x = 24.5), then cut into the three pieces with common.split_assembly.
One frame each.

Run: blender -b --python assembly-newsh5-229.py -- [--pieces]
Exports public/models/enemies/newsh5-229.glb and newsh5-231.glb (each piece at its own origin with its
outline shell) and their spriteModels entries; newsh5-268.py runs this builder and exports newsh5-268.
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector, geometry

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402

WT = common.repo_root(__file__)
import usp_talon as T  # noqa: E402

NAME = "assembly-newsh5-229"
PIECES = ["newsh5-229", "newsh5-231", "newsh5-268"]
LAYOUT = [("newsh5-229", -12, 0), ("newsh5-231", 12, 0), ("newsh5-268", 0, 28)]  # px from (24, 14)
AX = 24.5  # mirror axis (pixel edge coordinates)

PARTS = ["none", "fuselage", "nose", "shoulder", "hump", "fin", "tailplane", "strake", "wing", "panel",
         "gun", "barrel", "nacelle", "blister", "window", "vent", "rail"]
P = {n: i for i, n in enumerate(PARTS)}


# ------------------------------------------------------------------------------------------ 2D maths

def area2(poly):
    return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
               for i in range(len(poly)))


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def poly_dist(x, y, poly):
    n = len(poly)
    return min(seg_dist(x, y, *poly[i], *poly[(i + 1) % n]) for i in range(n))


def inset(poly, d):
    """Offset a simple polygon inward by d (miter, clamped)."""
    s = 1.0 if area2(poly) > 0 else -1.0
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((-e0.y, e0.x)) * s, Vector((-e1.y, e1.x)) * s
        m = n0 + n1
        if m.length < 1e-6:
            m = n0
        m.normalize()
        c = max(0.4, m.dot(n1))
        q = p1 + m * (d / c)
        out.append((q.x, q.y))
    return out


def clip(poly, a, b, c):
    """Sutherland-Hodgman: keep the part of poly where a*x + b*y + c >= 0."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] + c, a * q[0] + b * q[1] + c
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def mirror(poly):
    return [(2 * AX - x, y) for x, y in reversed(poly)]


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------- builders

class Builder:
    def __init__(self):
        self.bm = bmesh.new()
        self.part = self.bm.faces.layers.int.new("part")
        self.tmp = self.bm.faces.layers.int.new("tmp")
        self.sid = 0

    def tag(self, part):
        for f in self.bm.faces:
            if f[self.part] == 0:
                f[self.part] = P[part]

    # A loft along +y. stations: (y, cx, zc, hw, ztop, zbot, ex); ex = superellipse exponent.
    def loft_y(self, stations, sides, mat_fn, part, cap0=True, cap1=True):
        bm = self.bm
        rings = []
        for y, cx, zc, hw, zt, zb, ex in stations:
            if hw <= 1e-4:
                rings.append(([bm.verts.new((cx, y, zc + zt * 0.0))], y))
                continue
            ring = []
            for i in range(sides):
                a = 2 * math.pi * (i + 0.5) / sides - math.pi / 2
                ca, sa = math.cos(a), math.sin(a)
                xx = cx + hw * math.copysign(abs(ca) ** (2 / ex), ca)
                zz = zc + (zt if sa > 0 else zb) * math.copysign(abs(sa) ** (2 / ex), sa)
                ring.append(bm.verts.new((xx, y, zz)))
            rings.append((ring, y))
        for (r0, y0), (r1, y1) in zip(rings, rings[1:]):
            m = mat_fn((y0 + y1) / 2)
            if len(r0) == 1 and len(r1) == 1:
                continue
            for i in range(sides):
                j = (i + 1) % sides
                if len(r0) == 1:
                    bm.faces.new((r0[0], r1[j], r1[i])).material_index = m
                elif len(r1) == 1:
                    bm.faces.new((r0[i], r0[j], r1[0])).material_index = m
                else:
                    bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = m
        for (ring, y), on in ((rings[0], cap0), (rings[-1], cap1)):
            if on and len(ring) > 1:
                c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
                for i in range(len(ring)):
                    bm.faces.new((ring[i], ring[(i + 1) % len(ring)], c)).material_index = mat_fn(y)
        self.tag(part)

    # A plate over a plan outline: crisp chamfered top edge, crowned top and bottom from z functions
    # of (x, y, d) where d is the distance to the outline. Its faces are cut on a grid of `step` px
    # so the crown can follow the functions.
    def slab(self, outline, ztop, zbot, mat, part, step=1.25, chamfer=0.45, mats=None):
        bm = self.bm
        if area2(outline) < 0:
            outline = list(reversed(outline))
        self.sid += 1
        sid = self.sid
        ring1 = inset(outline, chamfer)
        t0 = [bm.verts.new((x, y, 100.0)) for x, y in outline]
        t1 = [bm.verts.new((x, y, 100.0)) for x, y in ring1]
        b0 = [bm.verts.new((x, y, -100.0)) for x, y in outline]
        n = len(outline)
        faces = [bm.faces.new(t1)]
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((t0[i], t0[j], t1[j], t1[i])))
            faces.append(bm.faces.new((b0[i], b0[j], t0[j], t0[i])))
        faces.append(bm.faces.new(list(reversed(b0))))
        for f in faces:
            f.material_index = mat
            f[self.tmp] = sid
        xs = [p[0] for p in outline]
        ys = [p[1] for p in outline]

        def geom():
            fs = [f for f in bm.faces if f[self.tmp] == sid]
            return fs + list({e for f in fs for e in f.edges}) + list({v for f in fs for v in f.verts})
        k0 = math.floor(min(xs) / step) + 1
        while k0 * step < max(xs):
            bmesh.ops.bisect_plane(bm, geom=geom(), plane_co=(k0 * step, 0, 0), plane_no=(1, 0, 0))
            k0 += 1
        k0 = math.floor(min(ys) / step) + 1
        while k0 * step < max(ys):
            bmesh.ops.bisect_plane(bm, geom=geom(), plane_co=(0, k0 * step, 0), plane_no=(0, 1, 0))
            k0 += 1
        fs = [f for f in bm.faces if f[self.tmp] == sid]
        vs = list({v for f in fs for v in f.verts})
        for v in vs:
            x, y = v.co.x, v.co.y
            d = poly_dist(x, y, outline)
            if v.co.z > 0:
                v.co.z = ztop(x, y, d)
            else:
                v.co.z = zbot(x, y, d)
        bm.normal_update()
        tri = [f for f in fs if len(f.verts) > 3 and abs(f.normal.z) > 0.15]
        bmesh.ops.triangulate(bm, faces=tri, quad_method="BEAUTY", ngon_method="BEAUTY")
        for f in bm.faces:
            if f[self.tmp] == sid:
                f[self.tmp] = -1
        self.tag(part)

    # A tube along a path of (x, y, z, rw, rh); rings face the path, with Z kept up.
    def tube(self, pts, sides, mat, part, cap0=True, cap1=True, mats=None, ex=2.0):
        bm = self.bm
        rings = []
        for i, (x, y, z, rw, rh) in enumerate(pts):
            a = Vector(pts[max(0, i - 1)][:3])
            b = Vector(pts[min(len(pts) - 1, i + 1)][:3])
            t = (b - a).normalized()
            side = t.cross(Vector((0, 0, 1)))
            if side.length < 1e-4:
                side = Vector((1, 0, 0))
            side.normalize()
            up = side.cross(t).normalized()
            if up.z < 0:
                up = -up
            c = Vector((x, y, z))
            if rw <= 1e-4:
                rings.append([bm.verts.new(c)])
                continue
            def se(t):
                return math.copysign(abs(t) ** (2 / ex), t)
            rings.append([bm.verts.new(c + side * (rw * se(math.cos(2 * math.pi * (k + 0.5) / sides)))
                                       + up * (rh * se(math.sin(2 * math.pi * (k + 0.5) / sides))))
                          for k in range(sides)])
        for si, (r0, r1) in enumerate(zip(rings, rings[1:])):
            m = mats[si] if mats else mat
            for k in range(sides):
                j = (k + 1) % sides
                if len(r0) == 1:
                    bm.faces.new((r0[0], r1[j], r1[k])).material_index = m
                elif len(r1) == 1:
                    bm.faces.new((r0[k], r0[j], r1[0])).material_index = m
                else:
                    bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = m
        for ring, on, m in ((rings[0], cap0, mats[0] if mats else mat), (rings[-1], cap1, mats[-1] if mats else mat)):
            if on and len(ring) > 1:
                c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
                for k in range(sides):
                    bm.faces.new((ring[k], ring[(k + 1) % sides], c)).material_index = m
        self.tag(part)

    # A patch draped over a surface z = surf(x, y): rows along y, each row from xl(y) to xr(y), lifted
    # `lift` above it, with a skirt down `sink` below the surface.
    def patch(self, y0, y1, ny, half, cx, nx, surf, lift, sink, mat, part):
        bm = self.bm
        grid = []
        for i in range(ny + 1):
            y = y0 + (y1 - y0) * i / ny
            h = half(y)
            row = []
            for k in range(nx + 1):
                x = cx - h + 2 * h * k / nx
                row.append(bm.verts.new((x, y, surf(x, y) + lift)))
            grid.append(row)
        for i in range(ny):
            for k in range(nx):
                bm.faces.new((grid[i][k], grid[i][k + 1], grid[i + 1][k + 1], grid[i + 1][k])).material_index = mat
        border = grid[0][:] + [grid[i][-1] for i in range(1, ny + 1)] + grid[-1][-2::-1] + \
            [grid[i][0] for i in range(ny - 1, 0, -1)]
        low = [bm.verts.new((v.co.x, v.co.y, surf(v.co.x, v.co.y) - sink)) for v in border]
        nb = len(border)
        for i in range(nb):
            j = (i + 1) % nb
            try:
                bm.faces.new((border[i], border[j], low[j], low[i])).material_index = mat
            except ValueError:
                pass
        try:
            bm.faces.new(list(reversed(low))).material_index = mat
        except ValueError:
            pass
        self.tag(part)

    def box_on(self, c, normal, along, w, l, depth, lift, mat, part):
        """A small box sitting on a surface point c (normal, along): w across, l along, top `lift`
        proud, bottom `depth` below the surface."""
        bm = self.bm
        nrm = Vector(normal).normalized()
        al = Vector(along).normalized()
        ac = al.cross(nrm).normalized()
        c = Vector(c)
        vs = []
        for h in (-depth, lift):
            for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                vs.append(bm.verts.new(c + ac * (su * w / 2) + al * (sv * l / 2) + nrm * h))
        b, t = vs[:4], vs[4:]
        fs = [bm.faces.new(list(reversed(b))), bm.faces.new(t)]
        for i in range(4):
            j = (i + 1) % 4
            fs.append(bm.faces.new((b[i], b[j], t[j], t[i])))
        for f in fs:
            f.material_index = mat
        self.tag(part)


# ----------------------------------------------------------------------------------------- the ship

# Fuselage half width (px) by row edge: tail cone rows 2-5, the round 9 px tube to the joint at row
# 39.7, then the nose cone (a step in to 3.75) to the point at row 51.
TAIL = T.pchip([1.95, 2.35, 2.8, 3.5, 4.5, 5.4, 6.4], [0.0, 0.9, 1.3, 1.8, 3.35, 4.3, 4.5])
NOSE = T.pchip([39.7, 41.5, 43.5, 45.5, 47.5, 49.3, 50.5, 51.25], [3.75, 3.62, 3.2, 2.5, 1.65, 0.9, 0.4, 0.0])
KT, KB, EX = 1.0, 0.85, 2.2  # top / bottom radius factors and superellipse exponent of the tube


def body_hw(y):
    if y < 6.4:
        return max(0.0, TAIL(y)) if y > 1.95 else 0.0
    if y <= 39.7:
        return 4.5
    return max(0.0, NOSE(y))


def body_z(x, y):
    """Top of the fuselage at (x, y) (no grooves)."""
    hw = body_hw(y)
    if hw <= 0:
        return 0.0
    u = min(1.0, abs(x - AX) / hw)
    return KT * hw * (1 - u ** EX) ** (1 / EX)


def wing_outline():
    # Left wing, plan in pixel edges, clockwise from the tip of the trailing edge.
    return [(4.1, 13.7), (8.6, 17.8), (10.1, 17.75), (10.9, 16.2), (15.0, 16.0), (15.4, 15.0), (20.0, 15.0),
            (20.0, 28.6), (18.7, 28.75), (17.75, 29.3), (17.0, 30.1), (16.95, 31.5), (16.45, 32.35),
            (15.85, 31.6), (15.15, 30.5), (14.3, 29.55), (13.95, 28.5), (13.2, 27.55), (11.5, 26.85),
            (10.0, 26.05), (5.6, 21.25), (4.0, 21.1)]


def wing_mid(x):
    return -0.25 - 0.045 * max(0.0, 19.5 - x)  # a little anhedral


def wing_top(x, y, d, outline):
    # A flat, hard plate: a 45-degree chamfer round the edge, then a plane (thickening linearly
    # toward the root), so the top stays one flat face.
    return wing_mid(x) + 0.3 + min(d, 0.45) + 0.3 + 0.035 * (x - 4.0)


def wing_bot(x, y, d):
    return wing_mid(x) - 0.3 - min(d, 0.3) - 0.1 - 0.02 * (x - 4.0)


def build(coll, sprite, detail=True, name=NAME):
    tag = "n5a229A"
    mats, slot = [], {}

    def m(i, **kw):
        key = (i, tuple(sorted(kw.items())))
        if key not in slot:
            slot[key] = len(mats)
            mats.append(common.palette_material(sprite, i, f"{tag}{len(mats)}", **kw))
        return slot[key]
    steel = dict(metallic=0.4, roughness=0.42)  # satin steel
    paint = dict(metallic=0.3, roughness=0.45)
    AFT, FWD, NOSEM, WING, TAILM = m(5, **steel), m(6, **steel), m(5, **steel), m(6, **steel), m(6, **steel)
    RED, FINR, DARK = m(69, **paint), m(71, **paint), m(1, metallic=0.3, roughness=0.55)
    NAC, SHOULD, RAIL, GUNM = m(68, **paint), m(5, **steel), m(6, **steel), m(7, **steel)
    GLASS = m(2, metallic=0.0, roughness=0.1)
    gl = next(n for n in mats[GLASS].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in gl.inputs:  # F0 via Specular IOR Level (D176): glossy glass, not a hole
        gl.inputs["Specular IOR Level"].default_value = 1.0
    FRAME = m(4, **steel)
    B = Builder()

    # Fuselage: tail cone, tube with a panel-line groove at row 25.3, joint ring at 39.7, nose cone.
    st = []
    for y in [1.95, 2.1, 2.35, 2.6, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.4, 7.5, 9.0, 11.0, 13.0, 15.0, 17.0, 19.0, 21.0, 23.0,
              24.9]:
        hw = body_hw(y)
        st.append((y, AX, 0.0, hw, KT * hw, KB * hw, EX))
    g = 0.32
    st += [(25.1, AX, 0.0, 4.5 - g, KT * 4.5 - g, KB * 4.5 - g, EX), (25.5, AX, 0.0, 4.5 - g, KT * 4.5 - g, KB * 4.5 - g, EX)]
    for y in [25.7, 27.5, 29.5, 31.5, 33.5, 35.5, 37.5, 39.7]:
        st.append((y, AX, 0.0, 4.5, KT * 4.5, KB * 4.5, EX))
    for y in [39.7, 40.4, 41.5, 42.5, 43.5, 44.5, 45.5, 46.5, 47.5, 48.4, 49.3, 50.0, 50.5, 50.9, 51.25]:
        hw = body_hw(y) if y > 39.7 or st[-1][3] > 4.0 else 3.75
        if y == 39.7:
            hw = 3.75
        st.append((y, AX, 0.0, hw, KT * hw, KB * hw, EX))
    B.loft_y(st, 22, lambda y: AFT if y < 25.3 else (FWD if y < 39.7 else NOSEM), "fuselage")

    # Shoulder housing over the aft fuselage (rows 9-16.5), squarer section, front face sloping down.
    sh = [(9.15, 4.5, 4.6), (9.6, 6.0, 5.0), (10.3, 7.3, 5.35), (11.1, 8.2, 5.55), (11.9, 8.5, 5.65),
          (14.6, 8.5, 5.65), (15.4, 8.25, 5.5), (16.1, 7.6, 5.1), (16.6, 6.2, 4.75), (17.0, 4.8, 4.55)]
    B.loft_y([(y, AX, 0.0, hw, zt, -3.4, 2.9) for y, hw, zt in sh], 22, lambda y: SHOULD, "shoulder")

    # Red armoured dorsal hump on the shoulders (rows 10-16, the red shield shape).
    hump = [(22.3, 9.95), (26.7, 9.95), (28.85, 11.9), (28.85, 13.6), (26.4, 15.95), (22.6, 15.95),
            (20.15, 13.6), (20.15, 11.9)]
    B.slab(hump, lambda x, y, d: 5.25 + 0.25 + min(d, 0.5) + 1.25 * smooth01((d - 0.5) / 2.6),
           lambda x, y, d: 3.8, RED, "hump", step=1.0, chamfer=0.5)

    # Dorsal fin (col 24, rows 0.7-12): a thin red blade, raked trailing edge, rounded top.
    ftop = T.pchip([0.75, 1.5, 4.0, 8.0, 11.0, 12.3], [7.5, 8.0, 7.75, 7.25, 6.75, 6.0])
    fs = []
    for y in [0.8, 1.2, 1.7, 2.4, 3.2, 4.2, 5.5, 7.0, 8.5, 10.0, 11.3, 12.3]:
        zt = ftop(y)
        zb = max(body_z(AX, y) - 0.8 if y > 2.3 else -9, zt - 0.35 - (y - 0.8) * 3.0)
        if y > 9.0:
            zb = 4.0
        hw = 0.5 if y > 1.5 else 0.35
        fs.append((y, zb, zt, hw))
    bm = B.bm
    rings = []
    for y, zb, zt, hw in fs:
        sec = [(-hw, zb), (hw, zb), (hw, zt - 0.45), (0.22, zt), (-0.22, zt), (-hw, zt - 0.45)]
        rings.append([bm.verts.new((AX + sx, y, sz)) for sx, sz in sec])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(6):
            j = (k + 1) % 6
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = FINR
    bm.faces.new(list(reversed(rings[0]))).material_index = FINR
    bm.faces.new(rings[-1]).material_index = FINR
    B.tag("fin")

    for side in (0, 1):
        def mx(poly):
            return mirror(poly) if side else poly

        def fx(x):
            return 2 * AX - x if side else x

        # Tailplane (rows 2-5, cols 10-18): an aerofoil slab, rounded tip.
        tp = [(9.85, 2.75), (10.25, 2.05), (11.0, 1.9), (17.0, 1.9), (19.2, 5.15), (11.0, 5.15), (10.25, 4.95), (9.85, 4.35)]
        B.slab(mx(tp), lambda x, y, d: 2.25 + 0.25 + min(d, 0.35) + 0.45 * smooth01((d - 0.35) / 1.2),
               lambda x, y, d: 2.25 - 0.25 - 0.35 * smooth01(d / 1.4), TAILM, "tailplane", step=1.0, chamfer=0.35)
        # Red root strake under it, sweeping forward and down into the fuselage (rows 5-9.8).
        sk = [(11.75, 4.6), (20.8, 4.6), (20.8, 9.85), (18.45, 9.85), (15.0, 6.25), (12.2, 5.95)]

        def sk_mid(x):
            u = abs(x - AX)
            return 1.55 + 0.21 * max(0.0, 12.7 - (u - 0.0)) if u < 12.7 else 1.55
        B.slab(mx(sk), lambda x, y, d: sk_mid(x) + 0.2 + min(d, 0.3) + 0.25 * smooth01((d - 0.3) / 1.2),
               lambda x, y, d: sk_mid(x) - 0.3 - 0.2 * smooth01(d / 1.2), RED, "strake", step=1.0, chamfer=0.3)

        # Wing.
        wo = mx(wing_outline())

        def wt(x, y, d, wo=wo):
            return wing_top(fx(x), y, d, wo)

        def wb(x, y, d):
            return wing_bot(fx(x), y, d)
        B.slab(wo, wt, wb, WING, "wing", step=99, chamfer=0.45)
        if detail:
            # Raised panel behind the panel line that runs parallel to the leading edge (x = y - 9.2),
            # stopping short of the nacelle; and a leading-edge strip in front of it.
            base = wing_outline()
            pa = clip(clip(base, 1, -1, 9.65), -1, 0, 15.3)  # x - y + 9.65 >= 0 and x <= 15.3
            pa = clip(pa, 0, 1, -17.9)  # y >= 17.9 (behind the trailing-edge blister)
            pa = inset(pa, 0.55)
            pb = clip(clip(base, -1, 1, -9.95), 1, -1, 14.3)  # between the panel line and the LE
            pb = clip(pb, -1, 0, 17.0)
            pb = inset(pb, 0.55)
            for poly in (pa, pb):
                if len(poly) < 3 or abs(area2(poly)) < 1.0:
                    continue

                def pt(x, y, d, wo=wo):
                    xx = fx(x)
                    return wing_top(xx, y, poly_dist(xx, y, wing_outline()), None) + 0.2 + min(d, 0.2)

                def pbot(x, y, d, wo=wo):
                    xx = fx(x)
                    return wing_top(xx, y, poly_dist(xx, y, wing_outline()), None) - 0.3
                B.slab(mx(poly), pt, pbot, WING, "panel", step=99, chamfer=0.2)

        # Wing-tip gun: grey breech (rows 13.3-20), red barrel forward to row 27.2, dark bore.
        gx, gz = fx(3.6), wing_mid(3.6) + 0.25
        gst = [(13.3, 0.0), (13.45, 0.55), (13.8, 0.9), (14.4, 1.08), (19.6, 1.08), (20.05, 1.08)]
        B.loft_y([(y, gx, gz, r, r, r, 2.0) for y, r in gst], 12, lambda y: GUNM, "gun", cap0=False, cap1=True)
        bst = [(19.9, 0.86), (26.1, 0.86), (26.15, 0.98), (27.15, 0.98), (27.2, 0.55)]
        B.loft_y([(y, gx, gz, r, r, r, 2.0) for y, r in bst], 12, lambda y: RED, "barrel", cap0=True, cap1=False)
        B.loft_y([(27.2, gx, gz, 0.55, 0.55, 0.55, 2.0), (26.6, gx, gz, 0.55, 0.55, 0.55, 2.0)], 12,
                 lambda y: DARK, "barrel", cap0=False, cap1=True)

        # Red intake fairing in the wing root beside the fuselage (rows 15-29).
        nac = [(15.6, 15.3, 2.75, 0.0, 0.0), (15.75, 15.6, 2.75, 0.55, 0.5), (16.3, 16.9, 2.65, 1.15, 0.95),
               (17.15, 18.6, 2.5, 2.05, 1.35), (17.9, 20.2, 2.35, 1.85, 1.3), (18.6, 21.8, 2.2, 1.3, 1.15),
               (18.95, 23.3, 2.05, 1.05, 1.05), (19.0, 26.5, 1.95, 1.0, 1.0), (18.95, 28.3, 1.8, 0.9, 0.9),
               (19.1, 29.05, 1.6, 0.75, 0.75), (19.3, 29.6, 1.4, 0.45, 0.45), (19.4, 29.95, 1.3, 0.0, 0.0)]
        B.tube([(fx(x), y, z, rw, rh) for x, y, z, rw, rh in nac], 12, NAC, "nacelle", ex=3.0)

        # Red blister on the wing's trailing-edge root (cols 10-13, rows 16-18).
        bx = fx(12.05)
        bz = wing_top(12.05, 17.0, 1.2, None) - 0.2
        blst = [(15.9, 0.0, 0.0), (16.1, 1.0, 0.45), (16.6, 1.75, 0.8), (17.4, 1.95, 0.9), (18.1, 1.6, 0.7),
                (18.55, 0.8, 0.35), (18.7, 0.0, 0.0)]
        B.loft_y([(y, bx, bz, w, h, 0.4, 2.4) for y, w, h in blst], 12, lambda y: RED, "blister")

        if detail:
            # Two vents on this flank (rows 34-36 and 37-39, cols 21-22 / 26-27).
            vx = fx(22.0)
            for vy in (35.0, 38.0):
                z = body_z(vx, vy)
                u = (vx - AX) / 4.5
                nrm = Vector((u * 1.0, 0.0, max(0.2, math.sqrt(max(0.0, 1 - u * u))))).normalized()
                B.box_on((vx, vy, z), nrm, (0, 1, 0), 1.75, 1.6, 0.5, 0.06, DARK, "vent")
                B.box_on((vx, vy, z), nrm, (0, 1, 0), 1.85, 0.3, 0.2, 0.2, FWD, "vent")
            # Rail beside the dorsal channel on the aft body (rows 17-25).
            rx = fx(23.55)
            B.tube([(rx, y, body_z(rx, y) - 0.05, 0.3, 0.32) for y in (17.2, 17.6, 21.0, 24.4, 24.8)], 6, RAIL, "rail")

    if detail:
        # Sensor window on the nose (rows 40-43): dark glossy glass in a frame, wrapped round the nose.
        def wh(y, k=1.0):
            t = (y - 41.35) / 1.6
            return max(0.25, 2.75 * k * (1 - min(1.0, abs(t)) ** 3) ** 0.5)
        B.patch(39.85, 42.85, 6, lambda y: wh(y, 1.0) + 0.3, AX, 10, body_z, 0.07, 0.4, FRAME, "window")
        def dome(x, y):  # the glass bulges a little: a lens, not a flat decal
            u = (x - AX) / 2.9
            t = (y - 41.35) / 1.5
            return body_z(x, y) + 0.32 * max(0.0, 1 - u * u - t * t)
        B.patch(40.05, 42.65, 6, wh, AX, 10, dome, 0.15, 0.45, GLASS, "window")

    bm = B.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # px -> Blender (a reflection in y), then make every closed island face out.
    mtx = Matrix(((1 / 12, 0, 0, -24 / 12), (0, -1 / 12, 0, 14 / 12), (0, 0, 1 / 12, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=mtx, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    for poly in me.polygons:
        poly.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(34))
    return obj


# ------------------------------------------------------------ pieces, normals across seams, shell

def seam_normals(piece, whole, x0, y0):
    """Copied from assembly-newsh9-197 design A: the whole object's corner normals on every face the
    piece shares with it, so shading runs on across the piece seams."""
    from mathutils.bvhtree import BVHTree
    wm = whole.data
    tree = BVHTree.FromPolygons([v.co for v in wm.vertices], [p.vertices[:] for p in wm.polygons])
    cn = wm.corner_normals
    pm = piece.data
    off = Vector((x0, y0, 0))
    out = [None] * len(pm.loops)
    for f in pm.polygons:
        c = f.center + off
        loc, nrm, idx, dist = tree.find_nearest(c)
        ok = idx is not None and dist < 1e-4 and nrm.dot(f.normal) > 0.98
        for li in f.loop_indices:
            if not ok:
                out[li] = f.normal.copy()
                continue
            pv = pm.vertices[pm.loops[li].vertex_index].co + off
            wf = wm.polygons[idx]
            wl = list(wf.loop_indices)
            if len(wl) == 3:
                a, b, c3 = (wm.vertices[wm.loops[k].vertex_index].co for k in wl)
                w = geometry.barycentric_transform(pv, a, b, c3, Vector((1, 0, 0)), Vector((0, 1, 0)),
                                                   Vector((0, 0, 1)))
                out[li] = sum((cn[k].vector * max(0.0, w[j]) for j, k in enumerate(wl)), Vector()).normalized()
            else:
                best = min(wl, key=lambda k: (wm.vertices[wm.loops[k].vertex_index].co - pv).length)
                out[li] = cn[best].vector.copy()
    pm.normals_split_custom_set(out)


def split_open(obj, layout, coll):
    """Cut the outline shell into the pieces without filling the cuts (no ink along the seams), each
    keeping the whole shell's vertex normals (copied from assembly-newsh9-197 design A)."""
    from mathutils.kdtree import KDTree
    mw = obj.matrix_world
    kd = KDTree(len(obj.data.vertices))
    for v in obj.data.vertices:
        kd.insert(mw @ v.co, v.index)
    kd.balance()
    wn = [(mw.to_3x3() @ v.normal).normalized() for v in obj.data.vertices]
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for mm in obj.data.materials:
            me.materials.append(mm)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        for k in obj.keys():
            sh[k] = obj[k]
        for poly in me.polygons:
            poly.use_smooth = True
        nrm = []
        for v in me.vertices:
            near = kd.find_n(Vector((v.co.x + x0, v.co.y + y0, v.co.z)), 2)
            n = sum((wn[i] * (1 / (d + 1e-5)) for _, i, d in near), Vector())
            nrm.append(n.normalized())
        me.normals_split_custom_set_from_vertices(nrm)
        out[name] = sh
    return out


def sink_shell(shell, model, margin, reach):
    """Keep the outline shell under the model's top surface (D90/D118: ink on the silhouette only)."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)),
                                  Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
    shell.data.update()


def main(export=("newsh5-229", "newsh5-231")):
    """Builds the whole craft; exports only the pieces in `export` (newsh5-268.py exports its own)."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    sprite = common.load_sprite(WT, PIECES[0])
    for n in PIECES[1:]:
        sprite["colors"].update(common.load_sprite(WT, n)["colors"])
    obj = build(coll, sprite)
    pieces = common.split_assembly(obj, LAYOUT)
    for name, cx, cy in LAYOUT:
        p = pieces[name]
        for poly in p.data.polygons:
            poly.use_smooth = True
        p.data.set_sharp_from_angle(angle=math.radians(34))
        seam_normals(p, obj, cx / 12, -cy / 12)
    # Outline shell (D51) from a sealed copy without the small detail, made once for the whole craft
    # and cut open into the pieces; every outer island kept (D189: the wing-tip guns stand free).
    plain = build(coll, sprite, detail=False, name=NAME + "_plain")
    bpy.context.view_layer.update()
    shell = common.outline_shell(plain, coll, voxel=0.014, faces=7000, inside=0.01, islands="outer")
    sink_shell(shell, plain, margin=0.03, reach=0.08)
    shells = split_open(shell, LAYOUT, coll)
    for name, sh in shells.items():
        print("SHELL", name, len(sh.data.vertices), "verts")
        assert len(sh.data.polygons) > 0, f"{name}_outline has no mesh"
    bpy.data.objects.remove(plain, do_unlink=True)
    bpy.data.objects.remove(shell, do_unlink=True)
    for name, cx, cy in LAYOUT:
        if name in export:
            data = common.load_sprite(WT, name)
            common.export_sprite_model(WT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"])
    for n, _, _ in LAYOUT:
        print("TRIS", n, sum(len(p.vertices) - 2 for p in pieces[n].data.polygons))
    print("TRIS whole", sum(len(p.vertices) - 2 for p in obj.data.polygons))


if __name__ == "__main__":
    main()
