"""Ground sensor post (newshj.shp frame 1, newshj-1): the real script (design A).

WHAT IT IS: small dark-grey fixed ground hardware (22x25 px inside a 24x28 sprite): a round machined
plinth on the ground carries a fluted collar, a slim neck rising up the screen to a horizontal
sensor head (rounded drum lying east-west, a split seam, a blade antenna on top) at the upper
left; beside the collar a domed equipment housing; on a gusset bracket off the plinth's east rim a
small mushroom knob with a spire. Type 750, terrain-fixed (TORM 2.1, BOTANY B 2.11, BONUS 2.12),
armour 6, no turret, so it is built standing on the HD ground with no pixel floor plate (D130).

The sprite draws it standing, in Tyrian's oblique art view (D82, D165): the plinth's left edge is
a vertical wall 6 rows tall, the collar's highlight a vertical line, the head a lit top edge. Art
camera: orthographic from the south, E = 20 deg up (the plinth's front rim is an ellipse ~0.34 as
tall as it is wide, rows 24-27), so a model point (u, v, z) lands on screen row
    s = VB + sin(E) (v - VB) - cos(E) z          (u = sprite column edge, v = plan row, south +)
The glb holds the true upright post, tagged for src/render/obliqueView.ts:
    tyrian_oblique    [cos E, sin E, axisZ]   axisZ = (VB - 14) * PX  (relative to the sprite centre)
    tyrian_depth_band [0, 0.35, 0, ZTOP*PX]   ground-enemy pass (as assembly-newshj-51, D170)

Build coords: sprite px, X = u east, Y = -v north, Z = up; the plinth's axis at (AX, VB).
Run:  python3 newshj-1_A.py                     IoU in the art view, region colours, diff rows
      blender -b --python newshj-1_A.py -- [--views DIR]   glb + views (scratch only)
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/Users/dlomibao/projects/tyrian-scratch/e2-enemies-2/newshj-1/final")
WT = next(p for p in HERE.parents if (p / "package.json").exists())  # repo root (common.repo_root)
NAME = "newshj-1"

E = 20.0
A, K = math.sin(math.radians(E)), math.cos(math.radians(E))
AX = 11.2        # plinth axis (column edge coordinate)
VB = 24.5        # plan row of the plinth axis
PX = 1.0 / 12.0
BAND = (0.0, 0.35)
W, H = 24, 28

# Palette indices (grey ramp 1-14; sprite medians per region, lighting excluded: see measure)
# Fix round 1: head 4, neck/coupling 2, rib 3, saddle 6 (the sprite's medians); the deck's top bevel is lit
# (pal 5) so the plinth reads as the sprite's flat lit dish. Seam, hseam and lug stay at 2: the sprite's
# median there is pal 1, which is only the outline ink (12,12,12), so they would vanish into the shell.
P = dict(PLINTH=4, DECK=3, BEVEL=5, BUMPER=6, FOOT=3, SEAM=2, BOLT=4,
         COLLAR=3, RIB=3, NECK=2, HEAD=4, HEADEND=6, HSEAM=2, FIN=6, SADDLE=6,
         HOUSING=6, HBAND=3, COUPLING=2, KNOB=5, SPIRE=5, LUG=2)

# Materials (fix round 1): the game render was much darker than the sprite at metallic 0.45 /
# roughness 0.42 (grey luma 56 / p90 84 against the sprite's 68 / 121). Satin metal with a raised F0
# (Specular IOR Level, exported as KHR_materials_specular, D176) so the sprite's sheen comes back as
# lighting; the lit surfaces the sprite shows bright (plinth rim, collar, head) are the smoothest, and
# the head, the sprite's brightest part, the glossiest. In game (TORM 2.1, row 77-1-1-77): see notes.
MAT_METALLIC = 0.38
MAT_SPEC = 1.2                   # Specular IOR Level: F0 = 0.08 * level
ROUGH = dict(head=0.15, sheen=0.2, rest=0.36)
HEAD_PARTS = {"head", "saddle", "fin"}
SHEEN_PARTS = {"plinth", "collar", "rib", "housing", "knob", "spire"}

# Plinth (radius profile r(z)), heights solved from the rows it must land on
R_B = 8.5
H_B = 5.5


# ---------------------------------------------------------------------------------------------
# Geometry (pure Python, measurable without Blender)
# ---------------------------------------------------------------------------------------------

class Geo:
    def __init__(self):
        self.v, self.f, self.smooth = [], [], []

    def add_v(self, p):
        self.v.append(tuple(float(c) for c in p))
        return len(self.v) - 1

    def face(self, idx, pal, part, smooth=True):
        self.f.append((tuple(idx), pal, part))
        self.smooth.append(smooth)

    def loft(self, rings, pals, part, cap0=True, cap1=True, smooth=True):
        ids = [[self.add_v(p) for p in r] for r in rings]
        n = len(rings[0])
        for i in range(len(ids) - 1):
            pal = pals[i] if isinstance(pals, (list, tuple)) else pals
            a, b = ids[i], ids[i + 1]
            for j in range(n):
                k = (j + 1) % n
                self.face((a[j], a[k], b[k], b[j]), pal, part, smooth)
        p0 = pals[0] if isinstance(pals, (list, tuple)) else pals
        p1 = pals[-1] if isinstance(pals, (list, tuple)) else pals
        if cap0:
            self._cap(ids[0], p0, part, True, smooth)
        if cap1:
            self._cap(ids[-1], p1, part, False, smooth)

    def _cap(self, ring, pal, part, flip, smooth):
        c = [sum(self.v[i][a] for i in ring) / len(ring) for a in range(3)]
        ci = self.add_v(c)
        n = len(ring)
        for j in range(n):
            k = (j + 1) % n
            self.face((ring[j], ring[k], ci) if not flip else (ring[k], ring[j], ci), pal, part, smooth)


def sq(t, n):
    return math.copysign(abs(t) ** n, t)


def loop_oval(cx, cy, rx, ry, z, sides=48, n=2.0, phase=0.0):
    out = []
    for i in range(sides):
        a = 2 * math.pi * i / sides + phase
        out.append((cx + rx * sq(math.cos(a), 2.0 / n), cy + ry * sq(math.sin(a), 2.0 / n), z))
    return out


def lathe(g, cx, cy, prof, pals, part, sides=40, n=2.0, smooth=True, phase=0.0):
    rings = [loop_oval(cx, cy, r, r, z, sides, n, phase) for r, z in prof]
    g.loft(rings, pals, part, cap0=prof[0][0] > 1e-6, cap1=prof[-1][0] > 1e-6, smooth=smooth)


def loop_rrect(cx, cy, hw, hd, rad, z, seg=3):
    rad = max(0.01, min(rad, hw - 0.01, hd - 0.01))
    pts = []
    for (qx, qy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oy = cx + qx * (hw - rad), cy + qy * (hd - rad)
        for k in range(seg + 1):
            a = math.radians(a0 + 90.0 * k / seg)
            pts.append((ox + rad * math.cos(a), oy + rad * math.sin(a), z))
    return pts


def obox(g, c, ax, ay, hx, hy, z0, z1, pal, part, ch=0.15, taper=1.0):
    """A chamfered box standing from z0 to z1, its plan axes ax, ay (unit 2D vectors), half sizes hx, hy;
    `taper` scales the top section."""
    ch = min(ch, hx * 0.45, hy * 0.45, (z1 - z0) * 0.45)

    def ring(sx, sy, z, s=1.0):
        pts = loop_rrect(0, 0, sx * s, sy * s, ch * 0.8 * s, 0)
        return [(c[0] + px * ax[0] + py * ay[0], c[1] + px * ax[1] + py * ay[1], z) for px, py, _ in pts]
    rings = [ring(hx - ch, hy - ch, z0), ring(hx, hy, z0 + ch), ring(hx, hy, z1 - ch, taper),
             ring(hx - ch, hy - ch, z1, taper)]
    g.loft(rings, pal, part, smooth=False)


def xloft(g, stations, pals, part, n=3.0, sides=32, smooth=True):
    """A drum lying along +u: stations [(u, v_c, z_c, ry, rz)] (plan half-depth ry, half-height rz)."""
    rings = []
    for u, vc, zc, ry, rz in stations:
        ring = []
        for i in range(sides):
            a = 2 * math.pi * i / sides
            ring.append((u, -vc + ry * sq(math.cos(a), 2.0 / n), zc + rz * sq(math.sin(a), 2.0 / n)))
        rings.append(ring)
    g.loft(rings, pals, part, smooth=smooth)


def build():
    g = Geo()
    cy = -VB

    # ---- plinth: a machined drum with a foot chamfer, a lit bumper band, a recessed upper wall and
    # a chamfered deck rim; the deck is a shallow dish with a raised centre boss.
    prof = [(R_B - 0.45, 0.0), (R_B - 0.1, 0.4), (R_B - 0.05, 1.2), (R_B, 1.7), (R_B, 3.4),
            (R_B - 0.25, 3.8), (R_B - 0.4, 4.7), (R_B - 0.15, 4.95), (R_B - 0.3, H_B - 0.35), (R_B - 0.95, H_B),
            (R_B - 1.3, H_B), (R_B - 1.5, H_B - 0.25), (0.01, H_B - 0.25)]
    pals = [P["FOOT"], P["FOOT"], P["BUMPER"], P["BUMPER"], P["PLINTH"], P["PLINTH"], P["PLINTH"],
            P["PLINTH"], P["BEVEL"], P["DECK"], P["DECK"], P["DECK"]]
    lathe(g, AX, cy, prof, pals, "plinth", sides=56)
    # wall seams (vertical panel joints; the front one is the sprite's dark column 11)
    for k in range(8):
        a = math.radians(-90 + 45 * k)
        ca, sa = math.cos(a), math.sin(a)
        r = R_B - 0.12
        obox(g, (AX + r * ca, cy + r * sa), (ca, sa), (-sa, ca), 0.22, 0.28, 1.75, 5.25, P["SEAM"], "seam", ch=0.06)
    # deck bolts
    for k in range(10):
        a = math.radians(18 + 36 * k)
        lathe(g, AX + 6.6 * math.cos(a), cy + 6.6 * math.sin(a),
              [(0.34, H_B - 0.3), (0.34, H_B + 0.1), (0.2, H_B + 0.22), (0.01, H_B + 0.24)],
              P["BOLT"], "bolt", sides=8, smooth=False)

    # ---- fluted collar under the neck (u 5-11), then a chamfer cone into the neck
    CX, CV = 8.4, VB - 1.2
    NX = 8.1
    lathe(g, CX, -CV, [(3.25, H_B - 0.3), (3.25, H_B + 0.4), (2.95, H_B + 0.6), (2.95, 8.2), (3.05, 8.35),
                       (3.05, 8.65), (2.5, 9.15), (2.05, 9.4), (0.01, 9.4)],
          [P["COLLAR"]] * 8, "collar", sides=40)
    for k in range(10):
        a = math.radians(-90 + 36 * k + 18)
        ca, sa = math.cos(a), math.sin(a)
        obox(g, (CX + 2.98 * ca, -CV + 2.98 * sa), (ca, sa), (-sa, ca), 0.3, 0.32, H_B + 0.6, 8.2, P["RIB"],
             "rib", ch=0.1, taper=0.9)
    # neck: a slim pipe with a mid ring
    lathe(g, NX, -CV, [(2.0, 9.2), (2.0, 12.4), (2.25, 12.6), (2.25, 13.1), (2.0, 13.3), (2.0, 16.2),
                       (0.01, 16.2)], P["NECK"], "neck", sides=28)

    # ---- sensor head: a rounded drum lying east-west on the neck (u 4-12), seam at u 8.6
    HZ, HV, RY, RZ = 16.15, VB - 1.2, 2.3, 2.6
    st = [(4.2, HV, HZ, RY * 0.72, RZ * 0.72), (4.45, HV, HZ, RY * 0.93, RZ * 0.93),
          (4.8, HV, HZ, RY, RZ), (8.35, HV, HZ, RY, RZ)]
    xloft(g, st, [P["HEADEND"], P["HEADEND"], P["HEAD"]], "head", n=2.7)
    xloft(g, [(8.3, HV, HZ, RY * 0.9, RZ * 0.9), (8.9, HV, HZ, RY * 0.9, RZ * 0.9)], P["HSEAM"], "hseam", n=3.2)
    st = [(8.85, HV, HZ, RY, RZ), (11.3, HV, HZ, RY, RZ), (11.65, HV, HZ, RY * 0.93, RZ * 0.93),
          (11.85, HV, HZ, RY * 0.72, RZ * 0.72)]
    xloft(g, st, [P["HEAD"], P["HEADEND"], P["HEADEND"]], "head", n=2.7)
    # blade antenna on top, a tapered fin (u 9-10.8) rising to row ~3.8
    fz0 = HZ + RZ - 0.5
    # a rounded saddle hump under the fin (u 8.05-12.05), lofted along u with chamfered ends
    sz = fz0 + 0.45
    xloft(g, [(8.05, HV, sz, 0.8, 0.75), (8.35, HV, sz, 1.1, 1.05), (11.75, HV, sz, 1.1, 1.05),
              (12.05, HV, sz, 0.8, 0.75)], P["SADDLE"], "saddle", n=3.0, sides=24)
    obox(g, (10.0, -HV), (1, 0), (0, 1), 0.95, 0.38, fz0, fz0 + 2.8, P["FIN"], "fin", ch=0.12, taper=0.8)

    # ---- domed equipment housing beside the collar (u 10.6-15.8)
    HX, HVV = 13.0, VB - 0.6
    prof = [(2.45, H_B - 0.3), (2.45, 7.0), (2.6, 7.2), (2.6, 7.6), (2.45, 7.8), (2.45, 9.0)]
    for i in range(1, 7):
        t = i / 6
        prof.append((2.45 * math.cos(t * math.pi / 2) ** 0.8 + 0.01, 9.0 + 1.7 * math.sin(t * math.pi / 2)))
    pals = [P["HOUSING"], P["HBAND"], P["HBAND"], P["HBAND"]] + [P["HOUSING"]] * (len(prof) - 5)
    lathe(g, HX, -HVV, prof, pals, "housing", sides=36)

    # coupling: a short conduit from the housing's flank into the neck (u 9-11.6)
    xloft(g, [(9.2, CV + 0.2, 10.9, 0.95, 0.95), (11.0, CV + 0.2, 10.9, 0.95, 0.95),
              (11.3, CV + 0.2, 10.9, 1.15, 1.15), (11.8, CV + 0.2, 10.9, 1.15, 1.15)],
          [P["COUPLING"]] * 3, "coupling", n=2.0, sides=20)

    # ---- knob on a gusset off the east rim (u 18-23), mushroom body and a spire
    KX, KV = 20.45, VB - 0.6
    obox(g, (18.6, -KV), (1, 0), (0, 1), 2.0, 1.0, 4.3, 7.0, P["LUG"], "lug", ch=0.3, taper=0.85)
    lathe(g, KX, -KV, [(1.2, H_B + 0.2), (1.45, H_B + 0.6), (2.35, H_B + 1.35), (2.4, 8.6), (2.2, 9.2),
                       (1.6, 9.8), (1.0, 10.1), (0.01, 10.15)], P["KNOB"], "knob", sides=32)
    lathe(g, KX + 0.3, -KV, [(1.25, 9.7), (1.05, 10.6), (0.95, 11.6), (0.7, 12.0), (0.01, 12.1)], P["SPIRE"],
          "spire", sides=14, smooth=False)
    return g


# ---------------------------------------------------------------------------------------------
# Measure in the art view
# ---------------------------------------------------------------------------------------------

def art(p):
    x, y, z = p
    v = -y
    return x, VB + A * (v - VB) - K * z, K * v + A * z


def rasterise(g, k=8):
    import numpy as np
    cov = np.zeros((H * k, W * k), bool)
    depth = np.full((H * k, W * k), -1e9)
    pal = np.full((H * k, W * k), -1, int)
    prt = np.full((H * k, W * k), -1, int)
    names = sorted({f[2] for f in g.f})
    pid = {n: i for i, n in enumerate(names)}
    V = np.array([art(p) for p in g.v])
    for idx, pa, part in g.f:
        for t in range(1, len(idx) - 1):
            tri = V[[idx[0], idx[t], idx[t + 1]]]
            xs, ys = tri[:, 0] * k, tri[:, 1] * k
            x0, x1 = max(0, int(math.floor(xs.min()))), min(W * k - 1, int(math.ceil(xs.max())))
            y0, y1 = max(0, int(math.floor(ys.min()))), min(H * k - 1, int(math.ceil(ys.max())))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx, cy) = zip(xs, ys)
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12:
                continue
            l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
            l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
            l3 = 1 - l1 - l2
            m = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
            if not m.any():
                continue
            d = l1 * tri[0, 2] + l2 * tri[1, 2] + l3 * tri[2, 2]
            sub_d = depth[y0:y1 + 1, x0:x1 + 1]
            cov[y0:y1 + 1, x0:x1 + 1] |= m
            win = m & (d > sub_d)
            sub_d[win] = d[win]
            pal[y0:y1 + 1, x0:x1 + 1][win] = pa
            prt[y0:y1 + 1, x0:x1 + 1][win] = pid[part]
    return cov, pal, prt, names


def measure(g, out_png=None):
    import numpy as np
    sys.path.insert(0, str(WT / "tools"))
    import sprite_mask as SM
    k = 8
    cov, pal, prt, names = rasterise(g, k)
    ref = str(WT / "reference" / "models")
    idx, colors = SM.load(NAME, None, ref)
    m = SM.masks(idx, colors, SM.pulse_partners(idx, SM.load_frames(NAME, ref)))
    res = SM.measure(m, cov.tolist())
    inner = np.array(m["inner"])
    sidx = np.array(idx)
    covg = cov.reshape(H, k, W, k).mean(axis=(1, 3)) >= 0.5
    cen_pal = pal[k // 2::k, k // 2::k]
    cen_prt = prt[k // 2::k, k // 2::k]
    table = []
    for i, n in enumerate(names):
        sel = (cen_prt == i) & inner & covg
        if sel.sum() < 2:
            continue
        sp = np.sort(sidx[sel])
        lo, hi = int(len(sp) * 0.15), int(len(sp) * 0.85)
        core = sp[lo:max(hi, lo + 1)]
        table.append((n, int(sel.sum()), int(np.median(core)), int(np.bincount(cen_pal[sel]).argmax())))
    res["regions"] = table
    rows = []
    for r in range(H):
        line = ""
        for c in range(W):
            s, mm = inner[r, c], covg[r, c]
            line += "#" if s and mm else ("-" if s else ("+" if mm else "."))
        rows.append(f"{r:2d} {line}")
    res["diff"] = rows
    if out_png:
        from PIL import Image
        img = np.zeros((H, W, 3), np.uint8)
        img[inner & covg] = (60, 180, 120)
        img[inner & ~covg] = (230, 60, 60)
        img[~inner & covg] = (80, 120, 255)
        img[np.array(m["border"]) & ~covg] = (70, 70, 70)
        Image.fromarray(img).resize((W * 12, H * 12), Image.NEAREST).save(out_png)
        im2 = np.zeros((H * k, W * k, 3), np.uint8) + 20
        for pi in np.unique(pal):
            if pi >= 0:
                im2[pal == pi] = colors[pi]
        Image.fromarray(im2).resize((W * 12, H * 12), Image.NEAREST).save(str(out_png).replace(".png", "_pal.png"))
    return res


# ---------------------------------------------------------------------------------------------
# Blender: mesh, outline shell, tags, export (scratch only), views
# ---------------------------------------------------------------------------------------------

def blender_main(argv):
    import bpy
    import bmesh
    from mathutils import Matrix
    sys.path.insert(0, str(WT / "assets" / "blender"))
    import common

    views = argv[argv.index("--views") + 1] if "--views" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    sprite = common.load_sprite(WT, NAME)

    g = build()
    def grp(part):
        return "head" if part in HEAD_PARTS else ("sheen" if part in SHEEN_PARTS else "rest")
    keys = sorted({(pa, grp(part)) for _, pa, part in g.f})
    mats = []
    for pa, gr in keys:
        m = common.palette_material(sprite, pa, f"nshj1_{gr}", metallic=MAT_METALLIC, roughness=ROUGH[gr])
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Specular IOR Level"].default_value = MAT_SPEC
        mats.append(m)
    mi = {k: i for i, k in enumerate(keys)}

    bm = bmesh.new()
    bv = [bm.verts.new(p) for p in g.v]
    for (idx, pa, part), sm in zip(g.f, g.smooth):
        try:
            f = bm.faces.new([bv[i] for i in idx])
        except ValueError:
            continue
        f.material_index = mi[(pa, grp(part))]
        f.smooth = sm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # px -> units, re-centred on the sprite centre (col 12, row 14), standing on z = 0
    bmesh.ops.transform(bm, matrix=Matrix.Scale(PX, 4), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(-12 * PX, 14 * PX, 0), verts=bm.verts)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    bpy.context.view_layer.update()
    me.set_sharp_from_angle(angle=math.radians(35))

    # outline shell from a sealed copy (the parts are closed and overlap, so the voxel remesh is one piece)
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=4000, smooth=6, inside=0.004)
    ztop = max(v[2] for v in g.v)
    tag = {"tyrian_oblique": [K, A, (VB - 14) * PX], "tyrian_depth_band": [BAND[0], BAND[1], 0.0, ztop * PX]}
    for o in (obj, shell):
        for kk, vv in tag.items():
            o[kk] = vv
    shell["tyrian_outline"] = True
    shell.parent = obj
    print("tris", sum(len(p.vertices) - 2 for p in me.polygons), "shell faces", len(shell.data.polygons),
          "tag", tag, "ztop units", ztop * PX)
    if "--no-export" not in argv:
        obj.hide_render = shell.hide_render = True
        common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", common.load_sprite(WT, NAME)["sprites"])
    if views:
        render_views(obj, shell, Path(views), ztop)


def render_views(obj, shell, out, ztop):
    import bpy
    from mathutils import Vector
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    shell.hide_render = True
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = 520
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.32, 0.34, 0.38, 1)
    bg.inputs["Strength"].default_value = 0.8
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    for nm, en, rot in (("sun", 3.6, (40, -25, -30)), ("fill", 0.9, (-60, 30, 160))):
        L = bpy.data.lights.new(nm, "SUN")
        L.energy = en
        lo = bpy.data.objects.new(nm, L)
        scene.collection.objects.link(lo)
        lo.rotation_euler = tuple(math.radians(a) for a in rot)
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=1.6, fill_type="NGON", location=(0, 0, -0.002))
    gnd = bpy.context.active_object
    gm = bpy.data.materials.new("gnd")
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (
        0.07, 0.11, 0.06, 1)
    gnd.data.materials.append(gm)
    cx, cy = (AX - 12) * PX, -(VB - 1 - 14) * PX
    c = Vector((cx, cy, ztop * PX * 0.45))
    cam_d = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam

    def shot(fname, direction, ortho=2.6, target=c, hide_ground=False):
        d = Vector(direction).normalized()
        cam.location = target + d * 10
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        if d.z > 0.999:
            cam.rotation_euler = (0.0, 0.0, 0.0)
        cam_d.type = "ORTHO"
        cam_d.ortho_scale = ortho
        gnd.hide_render = hide_ground
        scene.render.filepath = str(out / fname)
        bpy.ops.render.render(write_still=True)

    def az(deg, elev):
        a, e = math.radians(deg), math.radians(elev)
        return (math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))

    shot("top.png", (0, 0, 1), target=Vector((cx, cy, 0)))
    shot("front.png", az(0, 0.01))
    shot("side.png", az(90, 0.01))
    shot("rear.png", az(180, 0.01))
    shot("q34.png", az(-35, 30))
    shot("q34r.png", az(145, 35))
    shot("art.png", az(0, E), ortho=H * PX, target=Vector((0, 0, (VB - 14) * (1 - A) / K * PX)))
    shot("under.png", az(20, -40), hide_ground=True)
    # the game's tilted camera on the art form (each vertex where obliqueView.ts draws it)
    obj.hide_render = True
    af = art_form(obj, ztop)
    shot("game.png", (0, -math.sin(math.radians(15)), math.cos(math.radians(15))), ortho=2.6,
         target=Vector((0, 0, 0.1)))
    shot("game_top.png", (0, 0, 1), ortho=W * PX * 1.0, target=Vector((0, 0, 0.1)))
    af.hide_render = True
    obj.hide_render = False


def art_form(obj, ztop):
    """A copy drawn as obliqueView.ts draws it: (x, -s, h) with h squeezed into BAND (sprite-centred)."""
    import bpy
    me = obj.data.copy()
    az = (VB - 14) * PX
    for v in me.vertices:
        x, y, z = v.co
        zz = -y  # plan +south relative to sprite centre
        s = az + A * (zz - az) - K * z
        h = BAND[0] + min(max(z / (ztop * PX), 0), 1) * (BAND[1] - BAND[0])
        v.co = (x, -s, h)
    o = bpy.data.objects.new("artform", me)
    bpy.context.scene.collection.objects.link(o)
    me.update()
    return o


if __name__ == "__main__":
    if "bpy" in sys.modules:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
        blender_main(argv)
    else:
        g = build()
        r = measure(g, str(SCRATCH / "iou.png"))
        print("iou_rule_grid", r["iou_rule_grid"], "iou_rule", r["iou_rule"], "edge", r["edge_vs_inner_px"],
              "tris", sum(len(f[0]) - 2 for f in g.f))
        for row in r["regions"]:
            print("  region %-10s px %4d sprite median %3d model %3d" % row)
        print("\n".join(r["diff"]))
