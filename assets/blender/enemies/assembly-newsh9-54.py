"""Grey shield ship, top half (newsh9.shp 16/18 over 54/56): design A (episode 4, lean; D65).

TIME WAR (4.17) spawns one 48 x 112 px craft on the sky layer: four rigid rows of 2x2 enemies on one
link, 16/18 (dy -28), 54/56 (0), 92/94 (+28) and 130/132 (+56). This script builds the top 48 x 56
px (newsh9-16, -18, -54, -56); the lower half is assembly-newsh9-92 (D195), whose grey hull,
raised keel (cols 12-35) and glowing channel (cols 20-27) this half meets at its row 56 seam.

What it is: an egg-shaped grey hull carrying a big glossy blue canopy, split down the middle by a
raised grey spine. The canopy is the hull's own upper surface above two cuts, a plane tilted up
toward the back (so its rim runs from the flank at about row 37 round to row 45 on the centre line,
as the sprite's diagonal rim does) and the waterline: so the glass is one faired bubble in a grey
tub, framed by a lip. The spine carries a sunk hatch at the nose (rows 2-7), a louvre grille (rows
12-16) and a recessed, gridded slot (rows 17-49) between two rails, and ends in a collar housing
with a transverse bar (rows 49-56) from which the lower half's glowing channel runs on. Behind the
rim the grey collar carries the raised keel band of the lower hull (cols 12-35) and a glowing blue
shoulder glass pane low on each flank (rows 49-55), running on into the lower half's.

Colours (sprite palette index per region, median, shading and sheen left to the game's light):
glass 150 (frames 206/208/168/170 -> 153, 126/128/250/252 -> 157: the canopy's moving sheen is the
sprite's whole glass ramp shifting up, D17), hull and collar 5 (as the lower half's hull), spine 7,
rim lip 6, slot floor 3, slot grid 5, shoulder glass 149.

Pieces: built whole on the 48 x 56 grid, cut with common.split_assembly, normals carried across the
cuts; outline shell from a sealed copy (common.outline_shell islands="outer", D189), cut open per
piece. Every frame of each piece is one model (only the glass colour changes).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh9-54.py
Exports public/models/enemies/newsh9-{16,18,54,56}.glb and their spriteModels entries.
"""

import bisect
import json
import math
import os
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def _find_repo():
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "assets" / "blender" / "common.py").exists() and (p / "package.json").exists():
            return p
    env = os.environ.get("TYRIAN_REPO")
    if env:
        return Path(env)
    raise RuntimeError("repo root not found")


ROOT = _find_repo()
sys.path[:0] = [str(ROOT / "assets" / "blender"), str(ROOT / "tools")]
import common  # noqa: E402
import sprite_data  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "assembly-newsh9-54"
PX = 1 / 12
GW, GH = 48, 56
# piece centres relative to the 48 x 56 block's centre, in px (split_assembly's layout)
LAYOUT = [("newsh9-16", -12, -14), ("newsh9-18", 12, -14), ("newsh9-54", -12, 14), ("newsh9-56", 12, 14)]
FRAMES = {"newsh9-16": [16, 168, 250], "newsh9-18": [18, 170, 252],
          "newsh9-54": [54, 206, 126], "newsh9-56": [56, 208, 128]}


def load(name):
    """A piece's frames: the catalogue doesn't list these four pieces, so they are read from the game
    data (tools/sprite_data.py), in FRAMES' order."""
    return sprite_data.load(ROOT, name, "newsh9.shp", FRAMES[name])


def merged_sprite():
    d = load(LAYOUT[0][0])
    for n, _, _ in LAYOUT[1:]:
        d["colors"].update(load(n)["colors"])
    return d


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
            return ys[0] + m[0] * (x - xs[0])
        if x >= xs[-1]:
            return ys[-1] + m[-1] * (x - xs[-1])
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def X(c):
    """Pixel-edge column -> Blender X (units)."""
    return (c - GW / 2) * PX


def Y(r):
    """Pixel-edge row (down the sprite) -> Blender Y (units)."""
    return (GH / 2 - r) * PX


# ---- the hull: half-width, top and belly height (px) by row, and the section's squareness --------
# Half-width: a smooth line through the middle of each step of the sprite's inner (ink-less) mask,
# square from row 30 back to the seam.
W_OF = pchip([2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 11.0, 13.0, 16.0, 19.0, 23.0, 28.0, 30.5, 56.5],
             [5.6, 7.6, 10.0, 12.0, 13.5, 14.6, 15.6, 16.5, 17.5, 18.5, 19.5, 20.5, 21.5, 22.55, 23.0, 23.0])
# Top of the hull on the centre line: the canopy dome peaks about row 26 (16.5 px), falls to the
# collar and meets the lower hull's 8.6 px crown at the seam.
ZT_OF = pchip([2.0, 3.0, 5.0, 9.0, 15.0, 24.0, 30.0, 38.0, 45.0, 50.0, 56.5],
              [5.0, 7.2, 10.0, 13.0, 15.4, 16.6, 16.6, 15.7, 13.4, 12.4, 11.7])
ZB_OF = pchip([2.0, 6.0, 14.0, 36.0, 56.5], [1.2, 2.6, 3.6, 4.2, 4.9])  # belly depth (4.9 at the seam, as the cabin row)


def N_OF(r):
    """Section squareness |x/W|^n + |z/H|^2 = 1: round over the canopy, squarer at the seam (the
    lower hull's crown is flat to about x = 12)."""
    t = min(1.0, max(0.0, (r - 38.0) / 18.0))
    return 2.2 + 0.9 * (3 * t * t - 2 * t * t * t)


def hull_z(x_px, r):
    """Top surface height (px) at x px from the axis, row r."""
    w = W_OF(r)
    u = min(1.0, abs(x_px) / w)
    return ZT_OF(r) * max(0.0, 1 - u ** N_OF(r)) ** 0.5


# The canopy's rim: a plane z = Z45 + B * (row - 45) (px), tilted up toward the back.
RIM_ROW, RIM_B = 45.0, 1.25
RIM_Z = ZT_OF(RIM_ROW)


def rim_z(r):
    return RIM_Z + RIM_B * (r - RIM_ROW)


# The shoulder panes' inner edge (x px from the axis, row).
SH_A, SH_B = (22.8, 47.3), (16.0, 56.5)


def sh_x(r):
    t = (r - SH_A[1]) / (SH_B[1] - SH_A[1])
    return SH_A[0] + (SH_B[0] - SH_A[0]) * t


# ---- mesh helpers -------------------------------------------------------------------------------

def ring_pts(r, sides):
    """One closed section of the hull at row r (px), counter-clockwise seen from the front."""
    w, zt, zb, n = W_OF(r), ZT_OF(r), ZB_OF(r), N_OF(r)
    pts = []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        c, s = math.cos(a), math.sin(a)
        x = w * math.copysign(abs(c) ** (2 / n), c)
        z = zt * abs(s) if s >= 0 else -zb * abs(s) ** 0.5
        # top: z = zt * sqrt(1 - |x/w|^n) exactly
        if s >= 0:
            z = zt * max(0.0, 1 - abs(x / w) ** n) ** 0.5
        pts.append((x, z))
    return pts


def loft_rings(bm, rings, mat, cap0=True, cap1=True, smooth=True):
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        n = len(r0)
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    if cap0:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def build_hull(bm, mat):
    sides = 56
    rows = [2.0, 2.3, 2.7, 3.2, 3.8, 4.5, 5.3, 6.2] + [7.0 + 1.0 * i for i in range(50)]
    rows = [r for r in rows if r < 56.4] + [56.5]
    rings = []
    for r in rows:
        rings.append([bm.verts.new((x * PX, Y(r), z * PX)) for x, z in ring_pts(r, sides)])
    faces = loft_rings(bm, rings, mat, cap0=False, cap1=True)
    # nose: a fan to a point just ahead of the first ring
    tip = bm.verts.new((0.0, Y(1.75), 2.2 * PX))
    r0 = rings[0]
    for i in range(sides):
        j = (i + 1) % sides
        f = bm.faces.new((r0[j], r0[i], tip))
        f.material_index = mat
        f.smooth = True
        faces.append(f)
    return faces


def strip(bm, x0, x1, r0, r1, top, mat, ch=0.35, chl=True, chr_=True, step=1.0, bottom=None, smooth=False):
    """A bar standing on the hull top between columns-from-axis x0..x1 (px) and rows r0..r1: its top
    at top(r) px, its bottom sunk 1.5 px into the hull, top edges chamfered ch px."""
    n = max(1, int(math.ceil((r1 - r0) / step)))
    rows = [r0 + (r1 - r0) * k / n for k in range(n + 1)]
    rings = []
    for r in rows:
        zt = top(r)
        zb = bottom(r) if bottom else min(hull_z(x0, r), hull_z(x1, r)) - 1.5
        sec = [(x0, zb), (x1, zb)]
        sec += [(x1, zt - ch), (x1 - ch, zt)] if chr_ else [(x1, zt)]
        sec += [(x0 + ch, zt), (x0, zt - ch)] if chl else [(x0, zt)]
        rings.append([bm.verts.new((x * PX, Y(r), z * PX)) for x, z in sec])
    # ring order: bottom-left, bottom-right, up the right, across the top, down the left.
    # Rows run toward -Y, so reverse each ring to keep normals outward after recalc anyway.
    return loft_rings(bm, rings, mat, smooth=smooth)


def tube_path(bm, pts, radius, mat, sides=8, closed=False):
    """A round tube along a path of Vector points (units)."""
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        a = pts[(i - 1) % n] if closed or i > 0 else pts[0]
        b = pts[(i + 1) % n] if closed or i < n - 1 else pts[-1]
        d = (b - a).normalized()
        up = Vector((0, 0, 1))
        side = d.cross(up)
        if side.length < 1e-4:
            side = Vector((1, 0, 0))
        side.normalize()
        nu = side.cross(d).normalized()
        rings.append([bm.verts.new(p + radius * (math.cos(2 * math.pi * k / sides) * side
                                                  + math.sin(2 * math.pi * k / sides) * nu))
                      for k in range(sides)])
    faces = []
    for i in range(n if closed else n - 1):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for k in range(sides):
            j = (k + 1) % sides
            faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    if not closed:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = True
    return faces


def ellipsoid(bm, centre, rx, ry, rz, mat, seg=12, rings=6):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((centre[0] + v.co.x * rx, centre[1] + v.co.y * ry, centre[2] + v.co.z * rz))
    new = list(set(bm.faces) - before)
    for f in new:
        f.material_index = mat
        f.smooth = True
    return new


def to_object(name, bm, mats, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


# ---- the build ----------------------------------------------------------------------------------

def build(sprite, coll):
    tag = "nsh9t"
    glass_frames = {}
    for n, fr in FRAMES.items():
        glass_frames[fr[1]] = 153
        glass_frames[fr[2]] = 157
    mats = [
        common.palette_material(sprite, 5, tag, metallic=0.7, roughness=0.32),  # 0 hull, collar
        common.palette_material(sprite, 150, tag + "glass", metallic=0.0, roughness=0.08,
                                frames=glass_frames),  # 1 canopy glass
        common.palette_material(sprite, 7, tag, metallic=0.6, roughness=0.34),  # 2 spine
        common.palette_material(sprite, 6, tag, metallic=0.6, roughness=0.3),  # 3 rim lip, collar bar
        common.palette_material(sprite, 3, tag, metallic=0.3, roughness=0.7),  # 4 slot floor, louvre well
        common.palette_material(sprite, 5, tag + "grid", metallic=0.6, roughness=0.4),  # 5 slot grid
        # 6 shoulder glass: as the cabin row's shoulder glass it runs on into (lib_b019, pal 149)
        common.palette_material(sprite, 149, tag + "sglass", metallic=0.05, roughness=0.1,
                                emission_strength=1.2),
    ]
    HULL, GLASS, SPINE, LIP, FLOOR, GRID, SHOULDER = range(7)
    gl = mats[GLASS].node_tree.nodes
    bsdf = next(n for n in gl if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 1.0  # glossy glass F0 ~0.08 (D176)

    bm = bmesh.new()
    hull_faces = build_hull(bm, HULL)

    # Cut the canopy out of the hull top: the rim plane and the waterline.
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    # plane z_px - RIM_B * row = RIM_Z - RIM_B * 45, with row = 28 - 12 Y
    p0 = Vector((0.0, Y(RIM_ROW), RIM_Z * PX))
    nrm = Vector((0.0, RIM_B, 1.0)).normalized()
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=p0, plane_no=nrm)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    WL = 0.4  # px: the waterline sits just above the widest line
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, WL * PX), plane_no=(0, 0, 1))
    # The shoulder glass of the cabin row below (assembly-newsh9-92's 244/246) starts in the collar:
    # a pane on each flank behind a diagonal from (x 22.8, row 47.3) to (x 16, row 56.5).
    for side in (-1, 1):
        p1 = Vector((side * SH_A[0] * PX, Y(SH_A[1]), 0.0))
        p2 = Vector((side * SH_B[0] * PX, Y(SH_B[1]), 0.0))
        d = (p2 - p1).normalized()
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=p1, plane_no=(-d.y, d.x, 0.0))
    bm.normal_update()
    glass = set()
    for f in bm.faces:
        c = f.calc_center_median()
        row = GH / 2 - c.y / PX
        if c.z / PX > WL + 1e-3 and c.z / PX > rim_z(row) + 1e-3:
            f.material_index = GLASS
            glass.add(f)
        elif c.z / PX > WL + 1e-3 and row > SH_A[1] and abs(c.x) / PX > sh_x(row) and abs(f.normal.y) < 0.9:
            f.material_index = SHOULDER
    # The glass boundary as one ordered loop, for the frame lip.
    bedges = [e for e in bm.edges if sum(1 for f in e.link_faces if f in glass) == 1]
    loop = order_loop(bedges)
    pts = [v.co.copy() for v in loop]
    # resample, smooth slightly, and push the lip centre a little inside the surface
    pts = resample(pts, 0.7 * PX)
    # The lip's centre sits LIP_IN inside the hull surface (along its normal), so the frame stands
    # only LIP_R - LIP_IN proud of the glass and barely widens the top view at the waterline.
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromBMesh(bm)
    LIP_R, LIP_IN = 0.55, 0.42
    lip = []
    for p in pts:
        loc, n, _, _ = tree.find_nearest(p)
        out_dir = p - Vector((0.0, p.y, 4.0 * PX))
        if n.dot(out_dir) < 0:
            n = -n
        lip.append(p - n.normalized() * LIP_IN * PX)
    tube_path(bm, lip, LIP_R * PX, LIP, sides=8, closed=True)
    # a small frame along each shoulder pane's inner edge
    for side in (-1, 1):
        fr = []
        for k in range(15):
            t = k / 14
            row = SH_A[1] + (SH_B[1] - SH_A[1]) * t
            x = sh_x(row)
            p = Vector((side * x * PX, Y(row), hull_z(x, row) * PX))
            loc, n, _, _ = tree.find_nearest(p)
            if n.dot(p - Vector((0.0, p.y, 4.0 * PX))) < 0:
                n = -n
            fr.append(p - n.normalized() * 0.3 * PX)
        tube_path(bm, fr, 0.45 * PX, LIP, sides=6)

    # ---- spine ----
    T = lambda r: ZT_OF(r) + 1.8  # noqa: E731  spine top
    # rails either side of the slot, the full length
    strip(bm, -6.0, -4.0, 1.9, 49.0, T, SPINE, ch=0.45, chr_=False)
    strip(bm, 4.0, 6.0, 1.9, 49.0, T, SPINE, ch=0.45, chl=False)
    # the solid nose block between them (rows 1.9-17), with the sunk hatch and the louvre well
    strip(bm, -4.0, -3.0, 1.9, 17.0, T, SPINE, ch=0.0, chl=False, chr_=False)
    strip(bm, 3.0, 4.0, 1.9, 17.0, T, SPINE, ch=0.0, chl=False, chr_=False)
    strip(bm, -3.0, 3.0, 1.9, 2.7, T, SPINE, ch=0.0, chl=False, chr_=False, step=0.8)
    strip(bm, -3.0, 3.0, 2.7, 7.3, lambda r: T(r) - 0.75, SPINE, ch=0.0, chl=False, chr_=False)  # hatch
    strip(bm, -2.4, 2.4, 3.3, 6.7, lambda r: T(r) - 0.55, LIP, ch=0.15)  # hatch lid
    strip(bm, -3.0, 3.0, 7.3, 11.8, T, SPINE, ch=0.0, chl=False, chr_=False)
    strip(bm, -3.0, 3.0, 11.8, 16.6, lambda r: T(r) - 0.8, FLOOR, ch=0.0, chl=False, chr_=False)  # louvre well
    for r in (12.3, 13.4, 14.5, 15.6):
        strip(bm, -3.0, 3.0, r, r + 0.55, lambda q: T(q) - 0.1, SPINE, ch=0.12, step=0.55)
    strip(bm, -3.0, 3.0, 16.6, 17.0, T, SPINE, ch=0.0, chl=False, chr_=False, step=0.4)
    # the slot: a dark floor 1.4 px down between the rails, with a grid in its front half
    strip(bm, -4.0, 4.0, 17.0, 49.0, lambda r: T(r) - 1.4, FLOOR, ch=0.0, chl=False, chr_=False)
    for r in [17.8 + 2.0 * k for k in range(10)]:
        strip(bm, -4.0, 4.0, r, r + 0.6, lambda q: T(q) - 0.5, GRID, ch=0.1, step=0.6)
    for x in (-1.6, 1.0):
        strip(bm, x, x + 0.6, 17.0, 38.0, lambda q: T(q) - 0.5, GRID, ch=0.1)
    # collar housing at the spine's end (rows 49-56), its transverse bar on top
    CT = lambda r: T(49.0) + (12.7 - T(49.0)) * (r - 49.0) / 7.5  # noqa: E731  meets the cabin plate
    strip(bm, -6.0, 6.0, 49.0, 56.5, CT, HULL, ch=0.5)
    bar = [Vector((X(24 + x), Y(52.6), (CT(52.6) + 0.2) * PX)) for x in (-5.6, -3, 0, 3, 5.6)]
    tube_path(bm, bar, 1.25 * PX, LIP, sides=10)

    # ---- collar: the lower hull's keel band (cols 12-35) runs forward to the rim ----
    def keel_top(r):
        return hull_z(12.0, r) + 0.7
    strip(bm, -13.0, -6.0, 45.6, 56.5, keel_top, HULL, ch=0.5, chr_=False)
    strip(bm, 6.0, 13.0, 45.6, 56.5, keel_top, HULL, ch=0.5, chl=False)

    whole = to_object(NAME, bm, mats, coll)
    return whole, mats


def order_loop(edges):
    """Order boundary edges into one loop (the longest) of verts."""
    adj = {}
    for e in edges:
        a, b = e.verts
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    seen, best = set(), []
    for start in adj:
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            nxt = [v for v in adj[cur] if v is not prev and v not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            loop.append(cur)
        if len(loop) > len(best):
            best = loop
    return best


def resample(pts, step):
    """Even spacing along a closed polyline, then light smoothing."""
    n = len(pts)
    seg = [(pts[i], pts[(i + 1) % n]) for i in range(n)]
    total = sum((b - a).length for a, b in seg)
    m = max(8, int(total / step))
    out, acc, i = [], 0.0, 0
    lens = [(b - a).length for a, b in seg]
    for k in range(m):
        t = total * k / m
        while acc + lens[i] < t and i < n - 1:
            acc += lens[i]
            i += 1
        a, b = seg[i]
        u = (t - acc) / lens[i] if lens[i] else 0
        out.append(a.lerp(b, u))
    for _ in range(2):
        out = [(out[k - 1] + 2 * out[k] + out[(k + 1) % m]) / 4 for k in range(m)]
    return out


# ---- cutting, normals, shells (as lib_b019 in e4-enemies-1) -------------------------------------

def keep_normals(piece, whole, offset, fill_mat=0):
    from mathutils.bvhtree import BVHTree
    from mathutils.interpolate import poly_3d_calc
    mesh = piece.data
    hw, hh, eps = 1.0, 14 / 12, 1e-4
    for poly in mesh.polygons:
        vs = [mesh.vertices[i].co for i in poly.vertices]
        if any(all(abs(v.x - b) < eps for v in vs) for b in (-hw, hw)) or \
                any(all(abs(v.y - b) < eps for v in vs) for b in (-hh, hh)):
            poly.use_smooth = False
            poly.material_index = fill_mat  # the cut's fill: plain hull
    src = whole.data
    smooth = [p.index for p in src.polygons if p.use_smooth]
    tree = BVHTree.FromPolygons([v.co.copy() for v in src.vertices], [list(src.polygons[i].vertices) for i in smooth])
    corner = src.corner_normals
    off = Vector((offset[0], offset[1], 0.0))
    normals = []
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            if not poly.use_smooth:
                normals.append(poly.normal.copy())
                continue
            co = mesh.vertices[mesh.loops[li].vertex_index].co + off
            hit, _, fi, _ = tree.find_nearest(co)
            sp = src.polygons[smooth[fi]]
            w = poly_3d_calc([src.vertices[v].co for v in sp.vertices], hit)
            nn = Vector()
            for wk, lk in zip(w, sp.loop_indices):
                nn += wk * corner[lk].vector
            normals.append(nn.normalized() if nn.length > 1e-6 else poly.normal.copy())
    mesh.normals_split_custom_set(normals)


def split_open(obj, layout, coll):
    """Cut the outline shell into the pieces' boxes with no fill (an outline is a skin)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for mm in obj.data.materials:
            me.materials.append(mm)
        s = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        out[name] = s
    return out


def shell_for(whole, coll, faces):
    sealed = whole.copy()
    sealed.data = whole.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sealed, coll, voxel=0.012, faces=faces, smooth=4, inside=0.003, islands="outer")
    bpy.data.objects.remove(sealed)
    bpy.context.view_layer.update()
    return shell


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    sprite = merged_sprite()
    whole, mats = build(sprite, coll)
    shell = shell_for(whole, coll, faces=7000)
    parts = common.split_assembly(whole, LAYOUT)
    shells = split_open(shell, LAYOUT, coll)
    groups = {}
    for name, cx, cy in LAYOUT:
        keep_normals(parts[name], whole, (cx / 12, -cy / 12))
        groups[name] = [parts[name], shells[name]]
    bad = [g[1].name for g in groups.values() if len(g[1].data.polygons) == 0]
    if bad:
        raise SystemExit(f"empty outline shells: {bad}")
    info = {"whole_tris": tris(whole), "shell_tris": tris(shell),
            "pieces": {n: {"tris": tris(g[0]), "outline_tris": tris(g[1])} for n, g in groups.items()}}
    whole.hide_render = True
    shell.hide_render = True
    bpy.context.view_layer.update()
    for name, group in groups.items():
        data = load(name)
        common.export_sprite_model(ROOT, group, f"enemies/{name}", data["sprites"])
    print("BUILD_INFO", json.dumps(info))


if __name__ == "__main__":
    main()
