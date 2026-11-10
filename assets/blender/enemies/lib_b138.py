"""lib_b138: the five objects of newshd.shp built as what they are (D123, from design A).

  newshd-88 / newshd-34  edge tiles of the floating rock heap assembly-newshd-89 (level 1.1): chunky
                         boulders in the heap's own style, closed in a round faceted belly.
  newshd-157 (-f2, -f3)  a flying clamshell pod: two armoured shells round a socketed red eye,
                         closing over frames 157 -> 159 -> 161; faces down screen, closed belly.
  newshd-16              a tusked hover-crawler advancing down the screen (it hovers: no legs
                         are drawn), closed rounded keel.
  newshd-239             a fixed wall spawner: a brick wall tile with an armoured hatch and a U-shaped
                         glowing slot (glow bands follow frames 239 / 241 / 243).

Coordinates: sprite px (c, r) from the frame's top-left, z px up; Blender X = (c - W/2)/12,
Y = (H/2 - r)/12, Z = z/12. Underside: plain closed shapes only. Each script calls
lib.build(<name>, __file__).
"""

import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import sprite_mask as SM  # noqa: E402

PX = 1 / 12
INFO = {}


# --- helpers (copied here, shared files untouched) -----------------------------------------------

def sprite(name):
    return common.load_sprite(WT, name)


def frame_px(spr, index):
    return next(f for f in spr["frames"] if f["index"] == index)["pixels"]


def inner_mask(name, index):
    idx, colors = SM.load(name, frame=index)
    return SM.masks(idx, colors)["inner"]


def luma(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def region_pal(spr, pix, cells):
    """Median palette index of the cells' pixels between the 15th and 85th luma percentile."""
    col = spr["colors"]
    vals = sorted((pix[r][c] for r, c in cells if pix[r][c] >= 0), key=lambda i: luma(col[str(i)]))
    if not vals:
        return None
    lo, hi = int(len(vals) * 0.15), max(int(len(vals) * 0.85), int(len(vals) * 0.15) + 1)
    t = vals[lo:hi]
    return t[len(t) // 2]


class Mesh:
    """A bmesh in sprite px with a palette slot list."""

    def __init__(self, W, H):
        self.bm = bmesh.new()
        self.W, self.H = W, H

    def v(self, p):
        return self.bm.verts.new(p)

    def finish(self, name, mats, coll, sharp=32.0, origin_c=None):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        oc = self.W / 2 if origin_c is None else origin_c
        for v in bm.verts:
            c, r, z = v.co
            v.co = Vector(((c - oc) * PX, (self.H / 2 - r) * PX, z * PX))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(sharp))
        return obj


def loft(bm, rings, mat, cap0=True, cap1=True):
    """Join closed rings (same length) of px points; caps at the ends."""
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    for a, b in zip(vs, vs[1:]):
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            try:
                f = bm.faces.new((a[i], a[j], b[j], b[i]))
                f.material_index = mat
            except ValueError:
                pass
    for ring, on in ((vs[0], cap0), (vs[-1], cap1)):
        if on:
            try:
                f = bm.faces.new(ring)
                f.material_index = mat
            except ValueError:
                pass
    return vs


def hull_into(bm, pts, mat, merge=2.0):
    tmp = bmesh.new()
    vs = [tmp.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(tmp, input=vs, use_existing_faces=False)
    loose = [v for v in tmp.verts if not v.link_faces]
    bmesh.ops.delete(tmp, geom=loose, context="VERTS")
    bmesh.ops.dissolve_limit(tmp, angle_limit=math.radians(merge), verts=tmp.verts[:], edges=tmp.edges[:])
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
    me = bpy.data.meshes.new("tmp")
    tmp.to_mesh(me)
    tmp.free()
    for p in me.polygons:
        p.material_index = mat
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def hull2d(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def densify(poly, step):
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    return out


def superdome(t, tr, p=2.4, q=2.0):
    """0 at t = 0 and 1, 1 at the ridge tr: a rounded, shouldered section."""
    u = (t - tr) / (tr if t < tr else (1 - tr))
    return max(0.0, 1 - abs(u) ** p) ** (1 / q)


TT = [0.0, 0.03, 0.09, 0.18, 0.3, 0.42, 0.55, 0.68, 0.8, 0.9, 0.96, 1.0]
TB = [0.85, 0.65, 0.5, 0.35, 0.15]


def section(y, L, R, H, Bel, tr, p=2.4, lip=0.0):
    """A closed section across columns L..R at row y: domed top (ridge at tr), round belly."""
    pts = []
    for t in TT:
        z = H * superdome(t, tr, p)
        pts.append((L + t * (R - L), y, z))
    for t in TB:
        u = (t - 0.5) / 0.5
        pts.append((L + t * (R - L), y, -Bel * math.sqrt(max(0.0, 1 - u * u))))
    return pts


def row_runs(mask, c0, c1):
    """Per row: (first, last+1) of mask columns within [c0, c1), or None."""
    out = []
    for r, row in enumerate(mask):
        cols = [c for c in range(max(0, int(c0)), min(len(row), int(math.ceil(c1)))) if row[c]]
        out.append((min(cols), max(cols) + 1) if cols else None)
    return out


def clamp_box(bm, x0=None, x1=None, y0=None, y1=None, fill=True):
    """Cut a bmesh to a box (px), capping the cuts when fill."""
    planes = []
    if x0 is not None:
        planes.append(((x0, 0, 0), (-1, 0, 0)))
    if x1 is not None:
        planes.append(((x1, 0, 0), (1, 0, 0)))
    if y0 is not None:
        planes.append(((0, y0, 0), (0, -1, 0)))
    if y1 is not None:
        planes.append(((0, y1, 0), (0, 1, 0)))
    for co, no in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no, clear_outer=True)
        if fill:
            cut = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if cut:
                try:
                    bmesh.ops.holes_fill(bm, edges=cut, sides=0)
                except Exception:
                    pass


def bevel_obj(obj, width_px=0.3, angle=20):
    mod = obj.modifiers.new("chamfer", "BEVEL")
    mod.width = width_px * PX
    mod.segments = 1
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle)
    mod.harden_normals = False
    apply_mods(obj)


def apply_mods(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    obj.modifiers.clear()
    old = obj.data
    obj.data = me
    bpy.data.meshes.remove(old)


def rock_mat(spr, i, tag):
    return common.palette_material(spr, i, tag, metallic=0.0, roughness=0.85)


# --- the boulder (newshd-88 / newshd-34) -----------------------------------------------------------

BOULDER_HALF = {"88": ("newshd-88", 0), "34": ("newshd-34", 12)}
# Cells of the pair's 24x14 frame (rows, cols): the lit crown at the top left, the middle mass, the
# low front rock, the right flank (in tile 34) and the bottom-right toe. Heights in px.
CELLS = [   # seeds (c, r) of the pair frame; each inner pixel joins the nearest seed (weighted)
    {"name": "crown", "h": 9.6, "seed": (9.8, 2.8), "w": 1.15},
    {"name": "leftcap", "h": 7.0, "seed": (4.2, 2.0), "w": 0.85},
    {"name": "flank", "h": 7.2, "seed": (15.6, 3.6), "w": 1.0},
    {"name": "midleft", "h": 8.2, "seed": (6.2, 8.0), "w": 1.05},
    {"name": "midright", "h": 7.4, "seed": (13.0, 8.6), "w": 1.0},
    {"name": "lowleft", "h": 5.8, "seed": (6.5, 12.6), "w": 0.85},
    {"name": "lowright", "h": 6.4, "seed": (15.0, 12.4), "w": 0.95},
]
GROW = 1.0
BELLY = 3.6   # px under z 0, the floating rock's lowest point


def boulder(coll, which):
    name, ox = BOULDER_HALF[which]
    sp88, sp34 = sprite("newshd-88"), sprite("newshd-34")
    grid = [[-1] * 24 for _ in range(14)]
    inner = [[False] * 24 for _ in range(14)]
    for n, o, s in (("newshd-88", 0, sp88), ("newshd-34", 12, sp34)):
        pix = s["frames"][0]["pixels"]
        m = inner_mask(n, s["frames"][0]["index"])
        for r in range(14):
            for c in range(12):
                grid[r][o + c] = pix[r][c]
                inner[r][o + c] = m[r][c]
    colors = dict(sp34["colors"]); colors.update(sp88["colors"])
    spr = dict(sp88); spr["colors"] = colors
    rng = random.Random(88)
    mats, slot = [], {}
    bm_all = bmesh.new()
    regions = {}
    owner = {}
    for r in range(14):
        for c in range(24):
            if inner[r][c]:
                d = [math.hypot(c + 0.5 - k["seed"][0], (r + 0.5 - k["seed"][1]) * 1.15) / k["w"] for k in CELLS]
                owner[(r, c)] = d.index(min(d))

    def run_at(y):
        r = int(min(13, max(0, math.floor(y))))
        cols = [c for c in range(24) if inner[r][c]]
        return min(cols), max(cols) + 1

    for ci_, cell in enumerate(CELLS):
        px = [rc for rc, k in owner.items() if k == ci_]
        if not px:
            continue
        pal = region_pal(spr, grid, [(r, c) for r, c in px if 3 <= grid[r][c] <= 12])
        if pal not in slot:
            slot[pal] = len(mats)
            mats.append(rock_mat(spr, pal, name))
        own = [(r, c) for r, c in px if ox <= c < ox + 12]
        if own:
            regions[cell["name"]] = {"pal": pal, "px": [[r, c - ox] for r, c in own]}
        corners = {(c + dc, r + dr) for r, c in px for dr in (0, 1) for dc in (0, 1)}
        foot0 = hull2d(list(corners))
        cx = sum(p[0] for p in foot0) / len(foot0)
        cy = sum(p[1] for p in foot0) / len(foot0)
        pk = (cell["seed"][0] * 0.6 + cx * 0.4, cell["seed"][1] * 0.6 + cy * 0.4)
        foot = []
        for x, y in densify(foot0, 2.2):
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy) or 1
            gx, gy = x + GROW * dx / d, y + GROW * dy / d
            L, R = run_at(min(13.99, max(0.0, gy if 0 < gy < 14 else y)))
            gx = min(max(gx, L), R)
            gy = min(max(gy, 0.0), 14.0)
            foot.append((gx, gy))
        h = cell["h"] * 0.85
        pts = []
        prof = [(1.0, 0.0), (0.85, 0.45), (0.6, 0.83), (0.3, 1.0)]
        for s, zf in prof:
            for x, y in (foot if s == 1.0 else foot[::2]):
                jx, jy = rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25)
                px_ = pk[0] + (x - pk[0]) * s + (jx if s < 1 else 0)
                py_ = pk[1] + (y - pk[1]) * s + (jy if s < 1 else 0)
                pts.append((px_, py_, h * zf * rng.uniform(0.94, 1.0)))
        # round floating belly, faceted like the rock
        for s, zf in ((0.88, -0.4), (0.62, -0.78), (0.3, -1.0)):
            for x, y in foot[1::2]:
                pts.append((cx + (x - cx) * s, cy + (y - cy) * s, BELLY * zf * rng.uniform(0.9, 1.0)))
        tmp = bmesh.new()
        hull_into(tmp, pts, slot[pal], merge=3.0)
        clamp_box(tmp, x0=ox, x1=ox + 12, y0=0, y1=14)
        me = bpy.data.meshes.new("t")
        tmp.to_mesh(me); tmp.free()
        bm_all.from_mesh(me)
        bpy.data.meshes.remove(me)
    m = Mesh(24, 14)
    m.bm.free(); m.bm = bm_all
    obj = m.finish(name, mats, coll, sharp=25, origin_c=ox + 6)
    bevel_obj(obj, 0.28, 15)
    INFO.update({"regions": regions, "frames": [sp88["frames"][0]["index"] if which == "88" else 34]})
    # outline shell from the whole pair, cut open at the tile seam
    whole = []
    return [obj], [obj]


# --- the clamshell pod (newshd-157 / 159 / 161) -----------------------------------------------------

POD = {157: (9.0, 15.0), 159: (9.0, 13.0), 161: (11.0, 11.0)}   # shells' inner edges per frame (px)
SHELL_H = T.pchip([1, 3, 6, 11, 16, 20, 23], [3.6, 5.2, 6.4, 6.4, 5.4, 3.8, 2.2])
SHELL_B = 3.4


def pod(coll, index):
    name = "newshd-157"
    spr = sprite(name)
    pix = frame_px(spr, index)
    m = inner_mask(name, index)
    sl, sr = POD[index]
    eye_c = (sl + sr) / 2 if index != 161 else 11.0
    # palettes (the 157 frame is the reference for the parts' medians)
    p157 = frame_px(spr, 157)
    left_px = [(r, c) for r in range(28) for c in range(0, 8) if p157[r][c] > 1]
    right_px = [(r, c) for r in range(28) for c in range(16, 24) if p157[r][c] > 1]
    pl, pr = region_pal(spr, p157, left_px), region_pal(spr, p157, right_px)
    pal_hub, pal_brow, pal_eye, pal_core = 3, 8, 119, 124
    pals = [pl, pr, pal_hub, pal_brow, pal_eye, pal_core]
    mats = [common.palette_material(spr, pl, name + "s", metallic=0.35, roughness=0.5),
            common.palette_material(spr, pr, name + "s", metallic=0.35, roughness=0.5),
            common.palette_material(spr, pal_hub, name, metallic=0.4, roughness=0.55),
            common.palette_material(spr, pal_brow, name, metallic=0.4, roughness=0.45),
            common.palette_material(spr, pal_eye, name, metallic=0.1, roughness=0.25, emission_strength=1.0),
            common.palette_material(spr, pal_core, name, metallic=0.1, roughness=0.2, emission_strength=1.0)]
    M = Mesh(24, 28)
    bm = M.bm
    # shells: lofted over each row's run of the frame's mask on its side of the split
    for side in (-1, 1):
        c0, c1 = (0, sl) if side < 0 else (sr, 24)
        runs = row_runs(m, c0, c1)
        rows = [r for r, run in enumerate(runs) if run]
        raw = {}
        for r in rows:
            L, R = runs[r]
            raw[r] = (L, min(R, sl)) if side < 0 else (max(L, sr), R)
        sm = {}
        for r in rows:
            nb = [raw[q] for q in (r - 1, r, r + 1) if q in raw]
            wts = [0.25 if q != r else 0.5 for q in (r - 1, r, r + 1) if q in raw]
            L = sum(w * n[0] for w, n in zip(wts, nb)) / sum(wts)
            R = sum(w * n[1] for w, n in zip(wts, nb)) / sum(wts)
            # the split side stays straight (it meets the hub / the other shell)
            if side < 0:
                R = raw[r][1] if raw[r][1] >= sl - 1e-6 else R
            else:
                L = raw[r][0] if raw[r][0] <= sr + 1e-6 else L
            sm[r] = (L, R)
        rings = []
        tr = 0.58 if side < 0 else 0.42
        for k, r in enumerate(rows):
            L, R = sm[r]
            H = float(SHELL_H(r + 0.5))
            if k == 0:
                w = (R - L) * 0.3
                cxm = (L + R) / 2
                rings.append(section(r, cxm - w, cxm + w, H * 0.75, SHELL_B * 0.6, tr))
            rings.append(section(r + 0.5, L, R, H, SHELL_B * min(1.0, (R - L) / 5.0), tr))
            if k == len(rows) - 1:
                w = (R - L) * 0.3
                cxm = (L + R) / 2
                rings.append(section(r + 1, cxm - w, cxm + w, H * 0.75, SHELL_B * 0.5, tr))
        # one ring per row: enough sections; the ridge line runs smooth
        loft(bm, rings, 0 if side < 0 else 1)
        # crest: a narrow chamfered strip standing on the ridge line (the sprite's lit streak),
        # and two transverse armour seams (grooves) across the shell's back
        crest = []
        for r in rows[1:-1]:
            L, R = sm[r]
            H = float(SHELL_H(r + 0.5))
            xr = L + tr * (R - L)
            w = 0.45
            crest.append([(xr - w, r + 0.5, H - 0.5), (xr + w, r + 0.5, H - 0.5), (xr + w * 0.5, r + 0.5, H + 0.35),
                          (xr - w * 0.5, r + 0.5, H + 0.35)])
        if len(crest) > 3:
            loft(bm, crest[1:-1], 0 if side < 0 else 1)
    # hub: a dark socket block under the eye, a lit brow over it, prongs under (open frame only)
    hw = 3.3
    hx0, hx1 = eye_c - hw, eye_c + hw
    if index != 161:   # closed: the shells hide the socket
        hull_into(bm, T.cbox(hx0, hx1, 5.8, 12.2, -2.6, 3.6, 0.5), 2)
        hull_into(bm, T.cbox(hx0 + 0.3, hx1 - 0.3, 5.7, 7.0, 2.8, 4.6, 0.35), 3)
    if index == 157:
        for a, b in ((eye_c - 3.5, eye_c - 2.0), (eye_c + 2.0, eye_c + 3.5)):
            hull_into(bm, T.cbox(a, b, 11.8, 16.0, -1.6, 2.4, 0.35), 2)
    # the eye: a red ball in its socket, a hot lens on its face
    ex, ey, ez, er = eye_c, 8.5, 3.0, 2.05
    if index != 161:
        sph = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=er)
        for v in sph["verts"]:
            v.co = Vector((ex + v.co.x, ey + v.co.y * 0.85, ez + v.co.z * 0.9))
        for f in {f for v in sph["verts"] for f in v.link_faces}:
            f.material_index = 4
        lens = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=6, radius=0.85)
        for v in lens["verts"]:
            v.co = Vector((ex + v.co.x, ey - 0.1 + v.co.y, ez + 1.25 + v.co.z * 0.55))
        for f in {f for v in lens["verts"] for f in v.link_faces}:
            f.material_index = 5
    obj = M.finish(name if index == 157 else f"{name}-f{[157, 159, 161].index(index) + 1}", mats, coll, sharp=34)
    regions = {"left shell": {"pal": pl, "px": [[r, c] for r in range(28) for c in range(24) if m[r][c] and c < sl - 0.5 and pix[r][c] > 1]},
               "right shell": {"pal": pr, "px": [[r, c] for r in range(28) for c in range(24) if m[r][c] and c >= sr + 0.5 and pix[r][c] > 1]}}
    eye_px = [[r, c] for r in range(28) for c in range(24) if pix[r][c] >= 116 and m[r][c]]
    if eye_px:
        regions["eye"] = {"pal": pal_eye, "px": eye_px}
    INFO.update({"regions": regions, "frames": [index]})
    return [obj], [obj]


# --- the tusked crawler (newshd-16) ---------------------------------------------------------------

def surface_strip(L, R, H, tr, p, x0, x1, n=6):
    """Points along the dome section between x0 and x1 (px), on the surface z(x)."""
    out = []
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        t = min(1.0, max(0.0, (x - L) / (R - L)))
        out.append((x, H * superdome(t, tr, p)))
    return out


def crawler(coll):
    name = "newshd-16"
    spr = sprite(name)
    pix = frame_px(spr, 16)
    m = inner_mask(name, 16)
    sides = list(range(3, 9)) + list(range(15, 21))
    panel_px = [(r, c) for r in range(1, 17) for c in sides if 65 <= pix[r][c] <= 75]
    frame_px_ = [(r, c) for r in range(1, 17) for c in sides if 19 <= pix[r][c] <= 29]
    spine_px = [(r, c) for r in range(4, 13) for c in range(9, 15) if 19 <= pix[r][c] <= 29]
    tusk_px = [(r, c) for r in range(17, 28) for c in range(24) if (c < 9 or c > 14) and 19 <= pix[r][c] <= 29]
    groove_px = [(r, c) for r in range(17, 28) for c in range(24) if 34 <= pix[r][c] <= 37]
    jaw_px = [(r, c) for r in range(13, 18) for c in range(9, 15) if 65 <= pix[r][c] <= 75]
    red_px = [(r, c) for r in range(0, 6) for c in range(8, 16) if pix[r][c] >= 115]
    P = {"panel": region_pal(spr, pix, panel_px), "frame": region_pal(spr, pix, frame_px_),
         "spine": region_pal(spr, pix, spine_px), "tusk": region_pal(spr, pix, tusk_px),
         "groove": region_pal(spr, pix, groove_px), "jaw": region_pal(spr, pix, jaw_px),
         "lamp": region_pal(spr, pix, red_px), "dark": 20, "rib": 26, "fang": 21}
    order = ["panel", "frame", "spine", "tusk", "groove", "jaw", "lamp", "dark", "rib", "fang"]
    S = {k: i for i, k in enumerate(order)}
    mats = []
    for k in order:
        if k == "lamp":
            mats.append(common.palette_material(spr, P[k], name + k, metallic=0.1, roughness=0.3, emission_strength=1.0))
        elif k in ("panel", "jaw"):
            mats.append(common.palette_material(spr, P[k], name + k, metallic=0.2, roughness=0.4))
        else:
            mats.append(common.palette_material(spr, P[k], name + k, metallic=0.1, roughness=0.55))
    M = Mesh(24, 28)
    bm = M.bm
    # carapace pods: a brown armoured frame (the sprite's brown rim, band and inner edge) holding two
    # red plates each, set proud of it; rows 1..17 on each side of the spine
    PODH = T.pchip([1, 3, 6, 9, 12, 15, 17], [3.0, 5.2, 6.6, 6.8, 6.4, 5.0, 3.4])
    PP = 2.0
    for side in (-1, 1):
        runs = row_runs(m, 0, 9) if side < 0 else row_runs(m, 15, 24)
        rows = [r for r in range(1, 18) if runs[r]]
        tr = 0.45 if side < 0 else 0.55
        span = {}
        for r in rows:
            L, R = runs[r]
            if side < 0 and r >= 3:
                R = 9.0
            if side > 0 and r >= 3:
                L = 15.0
            span[r] = (L, R)
        rings = []
        for k, r in enumerate(rows):
            L, R = span[r]
            H = float(PODH(r + 0.5))
            if k == 0:
                c_ = (L + R) / 2
                rings.append(section(r, c_ - 0.4, c_ + 0.4, H * 0.7, 1.0, tr))
            rings.append(section(r + 0.5, L, R, H, 2.6, tr, p=PP))
        last = rings[-1]
        rings.append([(x, y + 0.5, z * 0.8) for x, y, z in last])
        loft(bm, rings, S["frame"])
        # red plates: rows 2..8.6 and 9.6..15.6, inset 1 px from the frame's edges, 0.45 px proud
        for ya, yb in ((2.2, 8.65), (9.55, 15.4)):
            plate = []
            ys = [ya + (yb - ya) * k / 6 for k in range(7)]
            for y in ys:
                r = int(y)
                L, R = span[min(max(r, rows[0]), rows[-1])]
                H = float(PODH(y))
                inset_o, inset_i = 1.0, 0.9
                x0, x1 = (L + inset_o, R - inset_i) if side < 0 else (L + inset_i, R - inset_o)
                # tips taper with the pod's own outline at the top rows
                topp = surface_strip(L, R, H, tr, PP, x0, x1, 8)
                ring = [(x, y, z + 0.45) for x, z in topp] + [(x, y, z - 0.4) for x, z in reversed(topp)]
                plate.append(ring)
            loft(bm, plate, S["panel"])
    # spine: a ribbed ridge between the pods, rows 4..14
    SPH = T.pchip([4.5, 6, 9, 13, 14.5], [3.8, 5.0, 5.4, 4.6, 3.0])
    rings = []
    for y in [4.5, 5.0, 6, 8, 10, 12, 13.5, 14.5]:
        rings.append(section(y, 8.6, 15.4, float(SPH(y)), 2.4, 0.5, p=3.0))
    loft(bm, rings, S["dark"])
    for (a, b, mat) in ((9.7, 11.0, "rib"), (12.9, 14.1, "spine")):
        rib = []
        for y in [4.6, 5.2, 7, 9, 11, 12.8]:
            h = float(SPH(y)) + 0.5
            rib.append([(a, y, h - 1.2), (b, y, h - 1.2), (b - 0.25, y, h), (a + 0.25, y, h)])
        loft(bm, rib, S[mat])
    # the red chevron at the back: two glowing bars from the pods' inner tips down to the spine's head
    for (x0, y0) in ((9.3, 3.3), (14.7, 3.3)):
        x1, y1 = 12.0, 5.6
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln * 0.55, dx / ln * 0.55
        z0, z1 = float(PODH(3.5)) - 1.0, float(SPH(5.5)) + 0.2
        pts = []
        for (x, y, z) in ((x0, y0, z0), (x1, y1, z1)):
            pts += [(x + nx, y + ny, z - 1.2), (x - nx, y - ny, z - 1.2), (x + nx * 0.6, y + ny * 0.6, z + 0.5),
                    (x - nx * 0.6, y - ny * 0.6, z + 0.5)]
        hull_into(bm, pts, S["lamp"])
    # jaw: two lobes either side of the open mouth (cols 9..11, 13..15; rows 13..18) on a brow plate
    for a, b in ((9.0, 11.0), (13.0, 15.0)):
        hull_into(bm, T.cbox(a, b, 13.2, 17.9, -1.6, 3.4, 0.45, 0.6), S["jaw"])
    hull_into(bm, T.cbox(9.2, 14.8, 12.6, 14.4, -1.5, 3.9, 0.4), S["jaw"])
    # chin bar (row 18), the fangs' root (row 19) and the fangs with red tips (cols 10, 13; rows 19..21)
    hull_into(bm, T.cbox(5.0, 19.0, 17.7, 19.0, -1.2, 1.9, 0.4), S["dark"])
    hull_into(bm, T.cbox(9.8, 14.2, 18.6, 20.0, -0.9, 1.5, 0.35), S["fang"])
    for cx in (10.5, 13.5):
        hull_into(bm, T.cbox(cx - 0.5, cx + 0.5, 19.0, 21.2, -0.6, 1.3, 0.2), S["fang"])
        hull_into(bm, [(cx - 0.5, 21.1, -0.4), (cx + 0.5, 21.1, -0.4), (cx - 0.5, 21.1, 1.2), (cx + 0.5, 21.1, 1.2),
                       (cx, 22.3, 0.2)], S["lamp"])
    # tusks: curved tapered horns from the body's front corners, bowing out and back in to the tips
    for side in (-1, 1):
        path = [(7.2, 17.3), (6.0, 18.6), (5.1, 19.8), (4.9, 21.0), (5.1, 22.3), (6.0, 23.5), (7.1, 24.6),
                (8.2, 25.6), (8.9, 26.6), (8.7, 27.6)]
        if side > 0:
            path = [(24 - x, y) for x, y in path]
        rad = [1.7, 1.85, 1.85, 1.8, 1.8, 1.75, 1.6, 1.35, 1.0, 0.6]
        zc = [2.3, 2.1, 1.9, 1.7, 1.5, 1.3, 1.1, 0.9, 0.7, 0.5]
        n = 10
        rings, frames = [], []
        for i, ((x, y), rr, z) in enumerate(zip(path, rad, zc)):
            a = path[min(i + 1, len(path) - 1)]; b = path[max(i - 1, 0)]
            tx, ty = a[0] - b[0], a[1] - b[1]
            tl = math.hypot(tx, ty)
            nx, ny = -ty / tl, tx / tl
            frames.append((x, y, nx, ny, rr, z))
            rings.append([(x + nx * rr * math.cos(2 * math.pi * (k + 0.5) / n), y + ny * rr * math.cos(2 * math.pi * (k + 0.5) / n),
                           z + rr * 0.85 * math.sin(2 * math.pi * (k + 0.5) / n)) for k in range(n)])
        tip = (path[-1][0] + (path[-1][0] - path[-2][0]) * 0.4, path[-1][1] + 0.35, 0.45)
        vs = loft(bm, rings, S["tusk"], cap0=True, cap1=False)
        tv = bm.verts.new(tip)
        last = vs[-1]
        for k in range(n):
            f = bm.faces.new((last[k], last[(k + 1) % n], tv))
            f.material_index = S["tusk"]
        # the dark green inlay along the tusk's crown (the sprite's green core stripe)
        g = []
        for x, y, nx, ny, rr, z in frames[:-2]:
            w = 0.42 * rr
            top = z + rr * 0.85
            g.append([(x - nx * w, y - ny * w, top - 0.3), (x + nx * w, y + ny * w, top - 0.3),
                      (x + nx * w * 0.8, y + ny * w * 0.8, top + 0.1), (x - nx * w * 0.8, y - ny * w * 0.8, top + 0.1)])
        loft(bm, g, S["groove"])
    # keel: the closed rounded belly under the body (it hovers; no legs are drawn)
    keel = []
    for y, w in ((3.5, 4.0), (5, 7.0), (8, 8.0), (11, 8.0), (13, 7.0), (14.6, 4.0)):
        keel.append(section(y, 12 - w, 12 + w, 0.0, 2.6, 0.5, p=2.0))
    loft(bm, keel, S["dark"])
    obj = M.finish(name, mats, coll, sharp=34)
    regions = {k: {"pal": P[k], "px": [[r, c] for r, c in v]} for k, v in
               (("panel", panel_px), ("frame", frame_px_), ("spine", spine_px), ("tusk", tusk_px), ("groove", groove_px),
                ("jaw", jaw_px), ("lamp", red_px))}
    INFO.update({"regions": regions, "frames": [16], "underside": "hover-crawler: closed rounded keel, no legs"})
    return [obj], [obj]


# --- the wall hatch (newshd-239) ------------------------------------------------------------------

WALL_Z = 4.0
FLOOR_Z = WALL_Z - 2.0
SLOT_IN = (11.5, 11.2, 7.1, 3.9)    # the hatch foot's ellipse (cx, cy, rx, ry), lower half
SLOT_OUT = (11.5, 12.0, 8.75, 8.0)  # the slot's outer edge


def slot_band(x, y):
    """Glow band of a point of the slot floor: 2 hot (the U's bottom line), 1 mid, 0 the arms' rim."""
    if 16.7 <= y <= 18.3 and abs(x - 11.5) < 4.8:
        return 2
    if y >= 15.6:
        return 1
    return 0


def hatch(coll):
    name = "newshd-239"
    spr = sprite(name)
    f0, f1, f2 = (frame_px(spr, i) for i in (239, 241, 243))
    glow = [(r, c) for r in range(28) for c in range(24) if f0[r][c] >= 112]
    bands = []
    for k in range(3):
        cells = [(r, c) for r, c in glow if slot_band(c + 0.5, r + 0.5) == k]
        bands.append((cells, {fr: region_pal(spr, px, cells) for fr, px in ((239, f0), (241, f1), (243, f2))}))
    wall_px = [(r, c) for r in range(19, 28) for c in range(24)] + [(r, c) for r in range(0, 19) for c in list(range(0, 3)) + list(range(20, 24))]
    plate_px = [(r, c) for r in range(0, 12) for c in range(5, 19)]
    pw = region_pal(spr, f0, wall_px)
    pp = region_pal(spr, f0, plate_px)
    mats = [common.palette_material(spr, pw, name + "w", metallic=0.0, roughness=0.85),
            common.palette_material(spr, max(2, pw - 2), name + "m", metallic=0.0, roughness=0.9),
            common.palette_material(spr, pp, name + "p", metallic=0.45, roughness=0.42),
            common.palette_material(spr, 7, name + "s", metallic=0.45, roughness=0.5),
            common.palette_material(spr, 12, name + "r", metallic=0.5, roughness=0.35)]
    for k, (cells, per) in enumerate(bands):
        mats.append(common.palette_material(spr, per[239], f"{name}g{k}", metallic=0.0, roughness=0.4, emission_strength=1.0,
                                            frames={241: per[241], 243: per[243]}))
    rng = random.Random(239)
    M = Mesh(24, 28)
    bm = M.bm
    N = 24

    def ell(e, a):
        cx, cy, rx, ry = e
        return (cx + rx * math.cos(a), cy + ry * math.sin(a))
    top_y = 11.6
    outer = [(x, max(y, top_y)) for x, y in (ell(SLOT_OUT, math.pi * i / N) for i in range(N + 1))]   # right -> left
    inner = [(x, max(y, top_y)) for x, y in (ell(SLOT_IN, math.pi * i / N) for i in range(N + 1))]
    # the cut region (convex): the outer edge's lower half closed along y = top_y; its edges as
    # 2D half-planes (point, outward normal)
    cpoly = [ell(SLOT_OUT, math.pi * i / 16) for i in range(17)]
    cpoly = [(x, max(y, top_y)) for x, y in cpoly]
    planes = []
    for i in range(len(cpoly)):
        (x0, y0), (x1, y1) = cpoly[i], cpoly[(i + 1) % len(cpoly)]
        if math.hypot(x1 - x0, y1 - y0) < 1e-6:
            continue
        nx, ny = (y1 - y0), -(x1 - x0)      # outward for a clockwise-in-screen polygon (y down)
        cxp, cyp = 11.5, 15.0
        if (cxp - x0) * nx + (cyp - y0) * ny > 0:
            nx, ny = -nx, -ny
        planes.append(((x0, y0), (nx, ny)))

    def clip(src, co, no, keep_outside):
        out = src.copy()
        geom = out.verts[:] + out.edges[:] + out.faces[:]
        n3 = (no[0], no[1], 0) if keep_outside else (-no[0], -no[1], 0)
        res = bmesh.ops.bisect_plane(out, geom=geom, dist=1e-5, plane_co=(co[0], co[1], 0), plane_no=n3, clear_inner=True)
        cut = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if cut:
            bmesh.ops.holes_fill(out, edges=cut, sides=0)
        return out

    def add_brick(pts):
        tmp = bmesh.new()
        hull_into(tmp, pts, 0)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if max(xs) < cpoly[-1][0] or min(xs) > cpoly[0][0] or max(ys) < top_y or min(ys) > SLOT_OUT[1] + SLOT_OUT[3]:
            pieces = [tmp]
        else:
            pieces, rem = [], tmp
            for co, no in planes:
                piece = clip(rem, co, no, True)
                if piece.faces:
                    pieces.append(piece)
                rem = clip(rem, co, no, False)
                if not rem.faces:
                    break
        for pc in pieces:
            me = bpy.data.meshes.new("pc")
            pc.to_mesh(me)
            pc.free()
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)

    courses = [(0, 5), (5, 9.5), (9.5, 14), (14, 19.5), (19.5, 23.5), (23.5, 28)]
    for k, (y0, y1) in enumerate(courses):
        x = -(0 if k % 2 == 0 else 4)
        while x < 24:
            a, b = max(0.0, x) + 0.18, min(24.0, x + 8) - 0.18
            a = 0.0 if a <= 0.2 else a
            b = 24.0 if b >= 23.8 else b
            ya = y0 + 0.18 if y0 > 0 else 0.0
            yb = y1 - 0.18 if y1 < 28 else 28.0
            if b - a > 0.5:
                zt = WALL_Z + rng.uniform(-0.15, 0.15)
                add_brick(T.cbox(a, b, ya, yb, FLOOR_Z - 0.9, zt, 0.25, 0.25))
            x += 8
    # wall core (mortar) under the bricks
    hull_into(bm, T.cbox(0, 24, 0, 28, 0, FLOOR_Z - 0.88, 0.01), 1)
    # the slot floor: a U of quads between the two edges, each band its glow colour; a shallow
    # gutter, deepest on the hot bottom line
    S = 4
    outer = [ell(SLOT_OUT, math.pi * i / N) for i in range(N + 1)]
    inner = [ell(SLOT_IN, math.pi * i / N) for i in range(N + 1)]
    outer = [(x, max(y, top_y)) for x, y in outer]
    inner = [(x, max(y, top_y)) for x, y in inner]
    for i in range(N):
        for j in range(S):
            q = []
            for ii, jj in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                xo, yo = outer[ii]; xi, yi = inner[ii]
                s = jj / S
                x, y = xi + (xo - xi) * s, yi + (yo - yi) * s
                depth = 0.6 * math.sin(math.pi * s) * math.sin(math.pi * ii / N)
                q.append((x, y, FLOOR_Z - 0.2 - depth))
            cx_ = sum(p[0] for p in q) / 4
            cy_ = sum(p[1] for p in q) / 4
            hull_into(bm, q + [(x, y, z - 0.3) for x, y, z in q], 5 + slot_band(cx_, cy_))
    # the shield hatch: rectangular top, rounded foot to row 15.1, standing proud
    base = [(4.0, 0.0), (19.0, 0.0), (19.0, 11.2)] + [(11.5 + 7.5 * math.cos(a), 11.2 + 3.9 * math.sin(a))
                                                    for a in [math.pi * i / 12 for i in range(1, 12)]] + [(4.0, 11.2)]
    pts = [(x, y, FLOOR_Z) for x, y in base]
    cx, cy = 11.5, 7.0
    for s_, z in ((0.985, WALL_Z + 2.6), (0.945, WALL_Z + 3.2)):
        pts += [(cx + (x - cx) * s_, cy + (y - cy) * s_ if y > 0.01 else 0.0, z) for x, y in base]
    hull_into(bm, pts, 2)
    top = WALL_Z + 3.2
    # seams: grooves at col 7 (upper panel) and col 15 (full height), and row 6
    hull_into(bm, T.cbox(7.0, 7.6, 0.0, 6.4, top - 0.5, top + 0.05, 0.0), 3)
    hull_into(bm, T.cbox(15.0, 15.6, 0.0, 12.4, top - 0.5, top + 0.05, 0.0), 3)
    hull_into(bm, T.cbox(4.6, 18.4, 6.0, 6.8, top - 0.5, top + 0.05, 0.0), 3)
    # twin rails down the lower panel (cols 10 and 12, rows 7..12)
    for cxr in (10.5, 12.5):
        hull_into(bm, T.cbox(cxr - 0.4, cxr + 0.4, 7.2, 12.4, top - 0.2, top + 0.55, 0.15), 4)
    for bx, by in ((5.2, 1.0), (17.8, 1.0), (5.2, 10.4), (17.8, 10.4)):
        hull_into(bm, T.cbox(bx - 0.5, bx + 0.5, by - 0.5, by + 0.5, top - 0.2, top + 0.4, 0.2), 4)
    obj = M.finish(name, mats, coll, sharp=30)
    regions = {"wall": {"pal": pw, "px": [[r, c] for r, c in wall_px]},
               "plate": {"pal": pp, "px": [[r, c] for r, c in plate_px]}}
    for k, (cells, per) in enumerate(bands):
        regions[f"glow{k}"] = {"pal": per[239], "px": [[r, c] for r, c in cells], "frames": {str(f): v for f, v in per.items()}}
    INFO.update({"regions": regions, "frames": [239, 241, 243]})
    return [obj], [obj]


# --- main ------------------------------------------------------------------------------------------

def _boulder_shell(shell, which):
    """Cut the outline shell open at the tile's inner seam (the other half continues the rock)."""
    bm = bmesh.new(); bm.from_mesh(shell.data)
    x = (6 if which == "88" else -6) * PX
    no = (1, 0, 0) if which == "88" else (-1, 0, 0)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=(x - (0.02 if which == "88" else -0.02), 0, 0),
                           plane_no=no, clear_outer=True)
    bm.to_mesh(shell.data); bm.free()


def build(name, file):
    """Build and export a model (the pod's three frames in one run) to public/models/enemies/."""
    root = common.repo_root(file)
    spr = common.load_sprite(root, name)
    if name in ("newshd-88", "newshd-34"):
        jobs = [(name, name[-2:], spr["sprites"])]
    elif name == "newshd-157":
        jobs = [(m, str(f), [{**s_, "frames": [f]} for s_ in spr["sprites"]])
                for m, f in (("newshd-157", 157), ("newshd-157-f2", 159), ("newshd-157-f3", 161))]
    else:
        jobs = [(name, name.split("-")[1], spr["sprites"])]
    for model, which, sprites in jobs:
        coll = common.reset_collection(model)
        if which in ("88", "34"):
            objs, shell_src = boulder(coll, which)
        elif which in ("157", "159", "161"):
            objs, shell_src = pod(coll, int(which))
        elif which == "16":
            objs, shell_src = crawler(coll)
        else:
            objs, shell_src = hatch(coll)
        shells = [common.outline_shell(o, coll, voxel=0.012, faces=2500, inside=0.004) for o in shell_src]
        if which in ("88", "34"):
            _boulder_shell(shells[0], which)
        print("triangles", sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs))
        common.export_sprite_model(root, objs + shells, f"enemies/{model}", sprites)
