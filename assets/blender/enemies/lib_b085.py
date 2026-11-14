"""The grey and red fortress of episode 4 (newsh9.shp): one object, ten sprite pieces (shared builder).

Used by assembly-newsh9-85.py (newsh9-47/-49/-51 over -85/-87/-89), newsh9-28.py, newsh9-32.py and
assembly-newsh9-10.py (newsh9-10/-12); each wrapper exports only its own models via export_pieces().

What it is: a ground war machine seen from above, mirror symmetric about the edge between fortress
columns 35 and 36 (Blender X = 0), moving down the screen (screen-down is its front). From the back:
- a big grey armoured dome (newsh9-10/-12 and the tops of newsh9-28/-32), its top divided into
  panels by raised seams (a round cap, a seam down the middle to the neck, two seams down the
  flanks);
- two red armour fenders draped over the dome's front flanks and down to the ground, each with a
  rounded crown and a tail curling down the outside;
- between them a grey neck running from the dome down to a grey sensor ball in a collar;
- a dark machinery bay under the fenders: machined blocks, bolts and a red lens each side;
- the lower hull: a broad grey shell with a raised lip along its back edge, a segmented spine down
  the middle, four red pods in dark sockets ringed with bolts, a boss on each flank and two tusks
  at the front.

Seen in episode 4: UNDERDELI (main=14), LAVA RUN (main=4) and DREAD-NOT (main=18).

Fortress pixels: column 0 is newsh9-47's left edge, row 0 its top edge; sprite up is +Y. Everything
is built once and cut into the pieces (common.split_assembly), the outline shell made once from the
sealed whole and cut open per piece (no ink across the cuts). Overlapping pieces carry identical
geometry. Nothing is written outside public/models and src/render/spriteModels.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector, geometry

HERE = Path(__file__).resolve().parent


def _find_repo():
    """The repo: from --repo, else the one holding this file."""
    if "--repo" in sys.argv:
        return Path(sys.argv[sys.argv.index("--repo") + 1])
    for p in [HERE, *HERE.parents]:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("assets/blender/common.py not found above " + str(HERE))


WT = _find_repo()
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

PX = 1 / 12
TAG = "nsh9fort"
ANCHOR = 0.55  # shared tyrian_anchor (D181) on every piece: the same plane for all, no seams

# Fortress pixel of each piece's top-left corner.
CORNER = {"newsh9-47": (0, 0), "newsh9-49": (24, 0), "newsh9-51": (48, 0),
          "newsh9-85": (0, 28), "newsh9-87": (24, 28), "newsh9-89": (48, 28),
          "newsh9-28": (0, -14), "newsh9-32": (48, -14),
          "newsh9-10": (12, -28), "newsh9-12": (36, -28)}
R0 = -28  # first composite row
NR, NC = 84, 72


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def X(c):
    """Fortress pixel column (centre; fractions allowed) to Blender X."""
    return (c + 0.5 - 36) / 12


def Y(r):
    return (28 - (r + 0.5)) / 12


def colf(x):
    return 12 * x + 35.5


def rowf(y):
    return 27.5 - 12 * y


# --- the sprites ---------------------------------------------------------------------------------

def load_all():
    idx = np.full((NR, NC), -1, dtype=int)
    colors = {}
    for name, (c0, r0) in CORNER.items():
        d = json.loads((WT / "reference" / "models" / name / "sprite.json").read_text())
        colors.update({int(k): tuple(v) for k, v in d["colors"].items()})
        for r, line in enumerate(d["frames"][0]["pixels"]):
            for c, v in enumerate(int(t) for t in line.split()):
                if v >= 0:
                    idx[r0 - R0 + r, c0 + c] = v
    m = SM.masks(idx.tolist(), colors)
    inner = np.array(m["inner"], dtype=bool)
    return idx, inner, colors


IDX, INNER, COLORS = load_all()


def px(c, r):
    """Palette index at fortress pixel (col, row), -1 outside."""
    if 0 <= c < NC and R0 <= r < R0 + NR:
        return IDX[r - R0, c]
    return -1


def inner(c, r):
    return 0 <= c < NC and R0 <= r < R0 + NR and INNER[r - R0, c]


def sprite_dict():
    return {"name": "newsh9-47", "colors": {str(k): list(v) for k, v in COLORS.items()}}


# --- outlines ------------------------------------------------------------------------------------

def _rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    ln = ab.length or 1e-9
    best, idx = -1, 0
    for i in range(1, len(pts) - 1):
        d = abs(ab.x * (pts[i] - a).y - ab.y * (pts[i] - a).x) / ln
        if d > best:
            best, idx = d, i
    if best <= eps:
        return [a, b]
    return _rdp(pts[:idx + 1], eps)[:-1] + _rdp(pts[idx:], eps)


def trace(ins, cols=(0, NC), rows=(R0, R0 + NR), eps=0.4):
    """Outline (Blender XY, CCW) of the largest region where ins(col, row) holds, traced round the
    pixel corners, stair steps turned into slopes (run midpoints), simplified (copy of lib_b085)."""
    edges = {}
    for r in range(rows[0], rows[1]):
        for c in range(cols[0], cols[1]):
            if not ins(c, r):
                continue
            if not ins(c, r - 1):
                edges[(c + 1, r)] = (c, r)
            if not ins(c, r + 1):
                edges[(c, r + 1)] = (c + 1, r + 1)
            if not ins(c - 1, r):
                edges[(c, r)] = (c, r + 1)
            if not ins(c + 1, r):
                edges[(c + 1, r + 1)] = (c + 1, r)
    loops, seen = [], set()
    for s in list(edges):
        if s in seen:
            continue
        loop, p = [], s
        while p not in seen and p in edges:
            seen.add(p)
            loop.append(p)
            p = edges[p]
        loops.append(loop)
    pts = [Vector(p) for p in max(loops, key=len)]
    n = len(pts)
    pts = [pts[i] for i in range(n)
           if abs((pts[i] - pts[i - 1]).cross(pts[(i + 1) % n] - pts[i])) > 1e-9]
    pts = [(pts[i] + pts[(i + 1) % len(pts)]) / 2 for i in range(len(pts))]
    far = max(range(len(pts)), key=lambda i: (pts[i] - pts[0]).length)
    pts = _rdp(pts[:far + 1], eps)[:-1] + _rdp(pts[far:] + [pts[0]], eps)[:-1]
    poly = [((p.x - 36) / 12, (28 - p.y) / 12) for p in pts]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    if area < 0:
        poly.reverse()
    return poly


def resample(poly, step, smooth=1):
    """Closed polyline resampled to about `step` units, then lightly smoothed (keeps the area)."""
    P = np.array(poly + [poly[0]], dtype=float)
    seg = np.hypot(*np.diff(P, axis=0).T)
    L = np.concatenate([[0], np.cumsum(seg)])
    n = max(8, int(round(L[-1] / step)))
    t = np.linspace(0, L[-1], n, endpoint=False)
    out = np.stack([np.interp(t, L, P[:, 0]), np.interp(t, L, P[:, 1])], axis=1)
    for _ in range(smooth):
        out = 0.25 * np.roll(out, 1, 0) + 0.5 * out + 0.25 * np.roll(out, -1, 0)
    return out


def inward(P, d):
    """Offset a CCW closed polyline inward by d (miter clamped)."""
    t = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
    nrm = np.stack([-t[:, 1], t[:, 0]], axis=1)  # left normal = inside for CCW
    return P + nrm * d


def seg_dist(pts, P):
    """Distance from each of pts (N,2) to the closed polyline P (M,2)."""
    A = P
    B = np.roll(P, -1, 0)
    AB = B - A
    out = np.full(len(pts), 1e9)
    for i in range(0, len(pts), 512):
        q = pts[i:i + 512, None, :]
        t = np.clip(((q - A) * AB).sum(-1) / ((AB * AB).sum(-1) + 1e-12), 0, 1)
        d = np.linalg.norm(q - (A + t[..., None] * AB), axis=-1)
        out[i:i + 512] = d.min(1)
    return out


def inside_poly(pts, P):
    x, y = pts[:, 0][:, None], pts[:, 1][:, None]
    x0, y0 = P[:, 0][None], P[:, 1][None]
    x1, y1 = np.roll(P[:, 0], -1)[None], np.roll(P[:, 1], -1)[None]
    cond = ((y0 > y) != (y1 > y)) & (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0)
    return cond.sum(1) % 2 == 1


# --- geometry ------------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def mark(self, before, mat, smooth=True):
        for f in set(self.bm.faces) - before:
            f.material_index = mat
            f.smooth = smooth


def plate(M, poly, top, mat, z0=0.0, ch=0.05, chw=1.2, grid=1.4, step=0.7, dist_fn=None):
    """An armour plate standing on z0 over `poly` (Blender XY, CCW): a vertical wall, a chamfer
    `ch` high and `chw` px wide, and a faired top z = top(x, y, d) (d: distance from the edge in
    units), triangulated over a grid of `grid` px (constrained Delaunay)."""
    bm = M.bm
    before = set(bm.faces)
    P = resample(poly, step * PX)
    Q = inward(P, chw * PX)
    g = grid * PX
    xs = np.arange(P[:, 0].min() + g / 2, P[:, 0].max(), g)
    ys = np.arange(P[:, 1].min() + g / 2, P[:, 1].max(), g)
    G = np.array([(x + (0.5 * g if (j % 2) else 0), y) for j, y in enumerate(ys) for x in xs])
    if len(G):
        keep = inside_poly(G, Q)
        G = G[keep]
        if len(G):
            G = G[seg_dist(G, Q) > 0.55 * g]
    n = len(Q)
    pts = [Vector((float(a), float(b))) for a, b in Q] + [Vector((float(a), float(b))) for a, b in G]
    res = geometry.delaunay_2d_cdt(pts, [(i, (i + 1) % n) for i in range(n)], [list(range(n))], 1, 1e-7, True)
    vco, _, faces, orig = res[0], res[1], res[2], res[3]
    allxy = np.array([[v.x, v.y] for v in vco])
    dP = seg_dist(allxy, P)
    zs = [top(float(x), float(y), float(d)) for (x, y), d in zip(allxy, dP)]
    verts = [bm.verts.new((v.x, v.y, z)) for v, z in zip(vco, zs)]
    ring = [None] * n
    for k, o in enumerate(orig):
        for i in o:
            if i < n:
                ring[i] = verts[k]
    for f in faces:
        try:
            bm.faces.new([verts[i] for i in f])
        except ValueError:
            pass
    dE = np.zeros(n)
    edge = [bm.verts.new((float(x), float(y), top(float(x), float(y), 0.0) - ch)) for (x, y) in P]
    base = [bm.verts.new((float(x), float(y), z0)) for (x, y) in P]
    for i in range(n):
        j = (i + 1) % n
        if ring[i] is None or ring[j] is None:
            continue
        bm.faces.new((edge[i], edge[j], ring[j], ring[i]))
        bm.faces.new((base[i], base[j], edge[j], edge[i]))
    bm.faces.new(list(reversed(base)))
    del dE
    M.mark(before, mat)


def ellipsoid(M, c, r, z, rx_px, ry_px, rz, mat, seg=20, rings=10, lower=1.0, tilt=None):
    bm = M.bm
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        k = rz if v.co.z >= 0 else rz * lower
        v.co = Vector((X(c) + v.co.x * rx_px * PX, Y(r) + v.co.y * ry_px * PX, z + v.co.z * k))
    M.mark(before, mat)


def sweep(M, path, mat, sides=8, cap=True, flat=False):
    """A tube along (col, row, z, half_width_px, half_height_units) points; zero size = rounded end."""
    bm = M.bm
    before = set(bm.faces)
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f)
    if cap and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    M.mark(before, mat, smooth=not flat)


def bar(M, path, mat, ch=0.35):
    """A chamfered box-section beam along (col, row, z_bottom, z_top, half_width_px) stations:
    an octagon-cornered section (flat top, chamfered top edges), so it reads machined."""
    bm = M.bm
    before = set(bm.faces)
    rings = []
    for i, (c, r, zb, zt, w) in enumerate(path):
        a = Vector((X(path[max(i - 1, 0)][0]), Y(path[max(i - 1, 0)][1]), 0))
        b = Vector((X(path[min(i + 1, len(path) - 1)][0]), Y(path[min(i + 1, len(path) - 1)][1]), 0))
        t = (b - a).normalized()
        s = Vector((t.y, -t.x, 0))
        p = Vector((X(c), Y(r), 0))
        cw = min(ch, 0.45 * w)
        cz = min(cw * PX, 0.45 * (zt - zb))
        prof = [(-w, zb), (w, zb), (w, zt - cz), (w - cw, zt), (-(w - cw), zt), (-w, zt - cz)]
        rings.append([bm.verts.new(p + s * (u * PX) + Vector((0, 0, z))) for u, z in prof])
    k = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(k):
            j = (i + 1) % k
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    M.mark(before, mat)


def cyl(M, c, r, z0, z1, rad_px, mat, seg=12, axis="z", length_px=0.0):
    """A cylinder: vertical (axis z) from z0 to z1, or along X (axis x) centred at z0 with
    length_px and radius rad_px (rad in px)."""
    bm = M.bm
    before = set(bm.faces)
    if axis == "z":
        res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                    radius1=rad_px * PX, radius2=rad_px * PX, depth=z1 - z0)
        bmesh.ops.translate(bm, vec=(X(c), Y(r), (z0 + z1) / 2), verts=res["verts"])
    else:
        res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                    radius1=rad_px * PX, radius2=rad_px * PX, depth=length_px * PX)
        rot = bpy_matrix_rot_y()
        bmesh.ops.rotate(bm, verts=res["verts"], cent=(0, 0, 0), matrix=rot)
        bmesh.ops.translate(bm, vec=(X(c), Y(r), z0), verts=res["verts"])
    M.mark(before, mat)


def bpy_matrix_rot_y():
    from mathutils import Matrix
    return Matrix.Rotation(math.pi / 2, 3, "Y")


def mirror_all(M):
    bm = M.bm
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def to_object(name, M, mats, coll, sharp_deg=38):
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    try:
        mesh.set_sharp_from_angle(angle=math.radians(sharp_deg))
    except Exception:
        pass
    return obj


# --- design functions ----------------------------------------------------------------------------

H_DOME = 1.7
PEAK = (35.5, -7.0)   # the dome's crown (fortress px)
DOME_C, DOME_R = (35.5, 8.5), 29.2  # the dome's footprint circle (hidden part under the fenders)


def dome_ins(c, r):
    return r <= 9 and inner(c, r) and (c - DOME_C[0]) ** 2 + (r - DOME_C[1]) ** 2 <= DOME_R ** 2


DOME_POLY = None
DOME_POLAR = None


def dome_setup():
    global DOME_POLY, DOME_POLAR
    DOME_POLY = trace(dome_ins, rows=(-28, 12))
    P = resample(DOME_POLY, 0.2 * PX, smooth=2)
    px0 = np.array([X(PEAK[0]), Y(PEAK[1])])
    d = P - px0
    ang = np.arctan2(d[:, 1], d[:, 0])
    rad = np.hypot(d[:, 0], d[:, 1])
    o = np.argsort(ang)
    a, rr = ang[o], rad[o]
    DOME_POLAR = (np.concatenate([a - 2 * np.pi, a, a + 2 * np.pi]), np.concatenate([rr, rr, rr]))


def dome_frac(x, y):
    dx, dy = x - X(PEAK[0]), y - Y(PEAK[1])
    a = math.atan2(dy, dx)
    R = float(np.interp(a, *DOME_POLAR))
    return math.hypot(dx, dy) / max(R, 1e-6)


def dome_z(x, y):
    """The dome's surface height at Blender (x, y); 0 outside its footprint."""
    s = dome_frac(x, y)
    if s >= 1.0:
        return 0.0
    return 0.16 + (H_DOME - 0.16) * math.sqrt(max(0.0, 1.0 - 0.96 * s * s))


def shell_top(x, y, d=10.0):
    c, r = colf(x), rowf(y)
    t = min(1.0, max(0.0, (r - 22.0) / 28.0))
    z = 0.84 - 0.26 * t
    z -= 0.18 * (abs(x) / 3.0) ** 2
    z -= 0.26 * (1.0 - min(1.0, d / (7.0 * PX))) ** 2
    return max(z, 0.14)


SHELL_I, RIM_I = 6, 11
FENDER_FLOOR = 0.28   # the dome's surface under the fenders (they lie low over its front flanks)
OUTER_RISE = 0.70     # the fenders' outer ends: a top of about 1.2 units in newsh9-47/-51 (D181, D201)


def build():
    coll = common.reset_collection("fortress-A")
    sprite = sprite_dict()
    pal = lambda i, m, rgh, t: common.palette_material(sprite, i, f"{TAG}_{t}", metallic=m, roughness=rgh)  # noqa: E731
    mats = [
        pal(6, 0.6, 0.42, "dome"),    # 0 dome grey
        pal(9, 0.65, 0.35, "seam"),   # 1 light seams
        pal(70, 0.35, 0.38, "fender"),  # 2 red fenders
        pal(2, 0.4, 0.6, "deck"),     # 3 dark bay deck / sockets
        pal(4, 0.55, 0.45, "mach"),   # 4 dark grey machinery
        pal(10, 0.7, 0.3, "bolt"),    # 5 bright bolts / knobs
        pal(6, 0.45, 0.42, "shell"),   # 6 lower shell: mid grey like the sprite's bowl (5-7), not dark
        pal(6, 0.6, 0.4, "spine"),     # 7 spine / neck (same index as the dome, own slot for clarity)
        pal(69, 0.3, 0.3, "lens"),    # 8 red lens
        pal(70, 0.3, 0.3, "pod"),    # 9 red pods
        pal(5, 0.45, 0.42, "ball"),    # 10 sensor ball
        pal(10, 0.55, 0.32, "rim"),  # 11 lip / light rims (the sprite's light band, 8-C)
        pal(3, 0.5, 0.5, "groove"),     # 12 collars, grooves
    ]
    for i, sp in ((SHELL_I, 0.6), (RIM_I, 0.7)):
        bsdf = next(n for n in mats[i].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = sp  # F0 (D176)
    DOME, SEAM, FENDER, DECK, MACH, BOLT, SHELL, SPINE, LENS, POD, BALL, RIM, GROOVE = range(13)
    fender_polys = []
    M = Mesh()
    dome_setup()

    # ================= the two sides: outlines from each side's own pixels =================

    def red(c, r):
        return 64 <= px(c, r) <= 79

    # Red pods (rows 25-47): one per red blob, both sides.
    seen = set()
    pods = []
    for r in range(25, 47):
        for c in range(0, NC):
            if (c, r) in seen or not red(c, r):
                continue
            stack, comp = [(c, r)], []
            while stack:
                p = stack.pop()
                if p in seen or not red(*p) or not (25 <= p[1] <= 47):
                    continue
                seen.add(p)
                comp.append(p)
                stack += [(p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)]
            if len(comp) > 20:
                cs = [q[0] for q in comp]
                rs = [q[1] for q in comp]
                pods.append(((min(cs) + max(cs)) / 2, (min(rs) + max(rs)) / 2,
                             (max(cs) - min(cs) + 1) / 2, (max(rs) - min(rs) + 1) / 2))
    for c, r, rx, ry in pods:
        zs = shell_top(X(c), Y(r))
        ellipsoid(M, c, r, zs - 0.02, rx + 1.0, ry + 1.0, 0.05, DECK, seg=20, rings=6)
        ellipsoid(M, c, r, zs - 0.06, rx - 0.1, ry - 0.1, 0.30, POD, seg=20, rings=10, lower=0.3)
        for k in range(6):
            a = 2 * math.pi * (k + 0.5) / 6
            bc, br = c + (rx + 1.6) * math.cos(a), r + (ry + 1.6) * math.sin(a)
            if inner(int(bc), int(br)):
                ellipsoid(M, bc, br, shell_top(X(bc), Y(br)) - 0.005, 0.55, 0.55, 0.05, RIM, seg=8, rings=4)

    for side in (0, 1):
        C = (lambda c: c) if side == 0 else (lambda c: 71 - c)
        lo, hi = (0, 36) if side == 0 else (36, NC)

        def own(c):
            """Column folded onto the left half (the design's own frame)."""
            return c if c < 36 else 71 - c

        # Red fender: this side's red pixels (rows -7..13), widened onto the ink lines that
        # border them on the dome side (they are the fender's edge, not paint).
        def fender_ins(c, r):
            if not (-7 <= r <= 13 and lo <= c < hi) or abs(c - 35.5) < 4 or not inner(c, r):
                return False
            if red(c, r):
                return True
            if px(c, r) in (1, 2) and any(red(c + dc, r + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                return r <= 2 or own(c) <= 8
            return False

        fpoly = trace(fender_ins, cols=(lo, hi), rows=(-8, 14))

        def fender_top(x, y, d):
            """Low armour over the dome's front flank (it used to ride the dome up to z 1.5, and
            the tilted game camera lifted it over the grey dome above it): a rounded crown where
            the sprite's red is tallest, an arm running in to the neck."""
            c, r = own(colf(x)), rowf(y)
            z = 0.53 - 0.010 * max(0.0, r - 4.0) - 0.010 * max(0.0, 8.0 - c) - 0.004 * max(0.0, c - 21.0)
            z = max(z, 0.46)
            lobe = math.exp(-(((c - 14.5) / 6.5) ** 2 + ((r + 0.5) / 4.0) ** 2))
            z += 0.18 * lobe
            # The thick outer end, where the tail curls down the outside (own columns 4-12): it
            # stands proud of the low plate, so newsh9-47/-51 keep a top above the pod blocks beside
            # them on DREAD-NOT (newsh9-77..83, 1.11 units) and D181 doesn't raise them over those,
            # and every piece after them in turn. The inner end stays low.
            z += OUTER_RISE * math.exp(-(((c - 8.0) / 4.5) ** 2 + ((r - 3.0) / 6.0) ** 2))
            z -= 0.09 * (1.0 - min(1.0, d / (3.0 * PX))) ** 2
            return z

        plate(M, fpoly, fender_top, FENDER, ch=0.04, chw=0.9, grid=1.2)
        fender_polys.append(resample(fpoly, 0.5 * PX, smooth=0))

        # Machinery bay (dark deck) under the fender, to the axis.
        def bay_ins(c, r):
            return 5 <= r <= 22 and lo <= c < hi and inner(c, r)

        bpoly = trace(bay_ins, cols=(lo, hi), rows=(4, 23))
        bpoly = [((min(x, 0.04) if side == 0 else max(x, -0.04)), y) for x, y in bpoly]
        plate(M, bpoly, lambda x, y, d: 0.30, DECK, ch=0.03, chw=0.8, grid=2.5)
        for c0, c1 in ((10.6, 12.4), (13.2, 18.4), (19.2, 25.6)):
            bar(M, [(C(c0), 11.6, 0.30, 0.50, 1.9), (C(c1), 11.6, 0.30, 0.50, 1.9)], MACH, ch=0.5)
        for c, r in ((16.3, 11.0), (20.6, 12.2), (11.5, 11.4)):
            ellipsoid(M, C(c), r, 0.50, 1.1, 1.1, 0.07, BOLT, seg=10, rings=5)
        for k in range(4):
            cc = C(16.5 + 2.3 * k)
            bar(M, [(cc, 14.8, 0.30, 0.45, 0.55), (cc, 18.4, 0.30, 0.45, 0.55)], MACH, ch=0.3)
        # red lens in a dark collar
        lens_px = [(c, r) for r in range(13, 20) for c in range(lo, hi) if red(c, r) and own(c) < 16]
        cs = [c for c, _ in lens_px]
        rs = [r for _, r in lens_px]
        lc, lr = (min(cs) + max(cs)) / 2, (min(rs) + max(rs)) / 2
        lrx, lry = (max(cs) - min(cs) + 1) / 2, (max(rs) - min(rs) + 1) / 2
        ellipsoid(M, lc, lr, 0.38, lrx + 0.7, lry + 0.7, 0.06, GROOVE, seg=16, rings=6)
        ellipsoid(M, lc, lr, 0.40, lrx - 0.2, lry - 0.2, 0.15, LENS, seg=18, rings=8, lower=0.4)

        # Raised lip along the shell's back edge (the light band rows 22-25).
        lip = [(1.4, 25.4), (4.0, 24.2), (8.0, 23.4), (13.0, 23.0), (18.0, 23.2), (23.0, 23.6),
               (28.0, 23.4), (31.5, 22.8)]
        path = []
        for i, (c, r) in enumerate(lip):
            z = shell_top(X(C(c)), Y(r)) + 0.02
            w = 2.3 if 0 < i < len(lip) - 1 else 0.0
            path.append((C(c), r, z, w, 0.07 if w else 0.0))
        sweep(M, path, RIM, sides=8)

        # Flank boss (bright knob at columns 3-6, rows 31-35).
        ellipsoid(M, C(5.0), 33.0, shell_top(X(C(5.0)), Y(33.0), 3 * PX) - 0.03, 2.0, 2.2, 0.09, RIM, seg=14, rings=6)
        # Panel lines on the shell (modelled grooves: thin dark beads)
        for line in ([(6.0, 27.5), (9.0, 39.5), (14.0, 44.5), (20.0, 47.5)],
                     [(19.5, 26.5), (21.0, 31.0)]):
            path = [(C(c), r, shell_top(X(C(c)), Y(r)) + 0.004, 0.35, 0.012) for c, r in line]
            sweep(M, path, GROOVE, sides=4)

        # Dome seam down the flank (follows the surface).
        path = [(C(c), r, dome_z(X(C(c)), Y(r)) + 0.012, 0.6, 0.03)
                for c, r in [(26.6, -11.8), (25.0, -9.6), (23.6, -7.4), (22.6, -5.2), (22.0, -3.0)]]
        sweep(M, path, SEAM, sides=6)

    # ================= centre (symmetric) =================

    # The dome.
    def dome_top(x, y, d):
        """The dome, falling steeply under the fenders' back edges to FENDER_FLOOR beneath them
        (a smooth min, so the grey face above each fender stays faired)."""
        z = dome_z(x, y) if dome_frac(x, y) < 1 else 0.16
        q = np.array([[x, y]])
        for F in fender_polys:
            out = 0.0 if inside_poly(q, F)[0] else float(seg_dist(q, F)[0])
            cap = FENDER_FLOOR + 0.30 * out / PX
            k = 0.10
            h = min(1.0, max(0.0, 0.5 + 0.5 * (cap - z) / k))
            z = cap + (z - cap) * h - k * h * (1 - h) if cap < z + k else z
        return z

    plate(M, DOME_POLY, dome_top, DOME, ch=0.04, chw=0.8, grid=1.1)
    # top cap ring and the seam down the middle
    ring = []
    for k in range(41):
        a = 2 * math.pi * k / 40
        ring.append((35.5 + 9.0 * math.cos(a), -12.6 + 5.4 * math.sin(a)))
    path = [(c, r, dome_z(X(c), Y(r)) + 0.012, 0.6, 0.03) for c, r in ring]
    sweep(M, path, SEAM, sides=6, cap=False)
    path = [(35.5, r, dome_z(X(35.5), Y(r)) + 0.012, 0.6, 0.03) for r in np.linspace(-7.2, -3.0, 6)]
    sweep(M, path, SEAM, sides=6)

    # Neck from the dome's front down to the ball (columns 30-41, rows -5..9).
    st = []
    for r in np.linspace(-5.5, 8.5, 9):
        zt = max(dome_z(X(35.5), Y(r)) + 0.06, 0.0)
        zt = max(zt, 1.12 - 0.02 * (r - 3.0) if r > 3 else zt)
        w = 5.4 if r < 6 else 5.4 - 0.5 * (r - 6)
        st.append((35.5, float(r), 0.25, zt, w))
    # make the neck descend smoothly to the ball top
    bar(M, st, SPINE, ch=1.2)
    ridge = [(35.5, s[1], s[3] + 0.004, 0.55, 0.022) for s in st[1:-1]]
    sweep(M, ridge, SEAM, sides=6)

    # Sensor ball in a collar (columns 26-45, rows 8-21).
    ellipsoid(M, 35.5, 14.6, 0.42, 9.6, 6.4, 0.06, GROOVE, seg=24, rings=6)
    ellipsoid(M, 35.5, 14.4, 0.60, 8.6, 6.9, 0.50, BALL, seg=28, rings=14, lower=0.6)
    # band round the ball's equator (a seam)
    path = [(35.5 + 8.65 * math.cos(a), 14.4 + 6.95 * math.sin(a), 0.60, 0.5, 0.03)
            for a in np.linspace(0, 2 * math.pi, 33)]
    sweep(M, path, GROOVE, sides=4, cap=False)

    # Lower shell.
    def shell_ins(c, r):
        return r >= 20 and inner(c, r)

    spoly = trace(shell_ins, rows=(19, 56))
    plate(M, spoly, shell_top, SHELL, ch=0.04, chw=0.9, grid=1.5)

    # Spine down the shell (columns 31-40, rows 21-49), segmented.
    sp = []
    for r, w in ((21.2, 2.5), (22.6, 4.0), (25.0, 4.7), (40.0, 4.7), (44.0, 4.0), (47.0, 2.8), (49.4, 1.0)):
        sp.append((35.5, r, 0.3, shell_top(0.0, Y(r)) + 0.10, w))
    bar(M, sp, SPINE, ch=1.0)
    for r in (29.5, 35.0, 40.5):
        zt = shell_top(0.0, Y(r)) + 0.10
        path = [(35.5 - 4.2, r, zt + 0.003, 0.0, 0.0), (35.5 - 4.0, r, zt + 0.003, 0.35, 0.012),
                (35.5 + 4.0, r, zt + 0.003, 0.35, 0.012), (35.5 + 4.2, r, zt + 0.003, 0.0, 0.0)]
        sweep(M, path, GROOVE, sides=4)
    ellipsoid(M, 35.5, 23.0, shell_top(0.0, Y(23.0)) + 0.10, 3.4, 1.6, 0.06, BOLT, seg=14, rings=5)
    ellipsoid(M, 35.5, 44.5, shell_top(0.0, Y(44.5)) + 0.10, 1.6, 1.6, 0.05, RIM, seg=12, rings=5)

    obj = to_object("fortress_whole", M, mats, coll)
    return obj, coll


# --- pieces, shells, export ----------------------------------------------------------------------

def layout():
    return [(n, c0 + 12 - 36, r0 + 14 - 28) for n, (c0, r0) in CORNER.items()]


def cut_open(obj, lay, coll):
    """Cut `obj` to each piece's box WITHOUT filling the cut (outline shells: no ink across the
    seam), moved to the piece's origin."""
    out = {}
    for name, cx, cy in lay:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        for poly in me.polygons:
            poly.use_smooth = True
        sh["tyrian_outline"] = True
        out[name] = sh
    return out


def export_pieces(names, preview=None):
    """Build the whole fortress, cut it and export the pieces in `names` (model + outline shell,
    public/models/enemies/<piece>.glb and its spriteModels entry). `preview` (a PNG path) also
    renders each piece beside its sprite into <preview dir>/<piece>.png."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    whole, coll = build()
    bpy.context.view_layer.update()
    shell = common.outline_shell(whole, coll, voxel=0.014, faces=6000, islands="outer")
    lay = layout()
    pieces = common.split_assembly(whole, lay, coll)
    shells = cut_open(shell, lay, coll)
    for name in names:
        p, s = pieces[name], shells[name]
        assert len(s.data.polygons) > 0, f"{name}: empty outline shell"
        for o in (p, s):
            o["tyrian_anchor"] = ANCHOR
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, [p, s], f"enemies/{name}", data["sprites"])
        print("PIECE", name, "tris", sum(len(q.vertices) - 2 for q in p.data.polygons),
              "shell", len(s.data.polygons))
    if preview:
        pdir = Path(preview).parent
        for name in names:
            data = common.load_sprite(WT, name)
            img = WT / "reference" / "models" / name / data["frames"][0]["image"]
            out = Path(preview) if len(names) == 1 else pdir / f"{name}.png"
            common.render_preview([pieces[name]], str(out), img, size=2)
    return whole, pieces
