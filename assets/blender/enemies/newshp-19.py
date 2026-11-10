"""newshp-19 (small missile): hard-surface rebuild as what it is (D65, D120, D122); geometry is
shared with newshp-95 (green palette swap, built by newshp-95.py from this build_missile).

newshp-19 (frames 19/38/57/76, 12 x 14) and newshp-95 (frames 95/114/133/152, the same drawing with
the brown body swapped for green): ONE missile geometry, a palette swap.
- WHAT IT IS: a launched missile. Type 458 (newshp-19) is launched by the silo newshp-53 (type 457)
  with mv(0,3); type 460 (newshp-95) by the flagship launcher newshs-93 (type 459) with mv(0,5).
  Both fly DOWN the screen, so the bottom end (row 13) leads: a closed grey ogive nose. The top end
  is the tail: exhaust nozzle, flame and fins. Free flying, round, closed belly (no ground).
- Symmetric about column edge 6.5. Cols 5-7 (3 px) are a round body: the bright centre column
  with darker flanks is a cylinder's sheen (rubric), not a ridge.
- Rows 10-13: grey nose cone (6/11/8 -> 3/9/4 -> tip 6: the ogive curving away from the light).
- Rows 5-9: the brown (green on 95) motor casing; rows 5 and 9 are a step darker: its two end
  bands, split from the middle by machined grooves.
- Rows 2-4, col 6: grey aft body / nozzle bell (10); cols 5 / 7 rows 3-4 its flanks in shade.
- Rows 1-4, cols 4 / 8: the side tail fins (103, leading edge 101 at row 4 is its chamfer in shade).
  Cruciform: a dorsal and a ventral fin of the same plan stand edge-on over col 6 (sub-pixel).
- Rows 1-2, cols 5 / 7: jet-vane housings flanking the nozzle exit (103 top, 101 sloped aft lip);
  the exhaust heats them: on 57 / 76 they glow red (116/118 and 113/114) -> palette_material frames.
- Row 1-2, col 6: the flame core leaving the nozzle (115 -> 120 -> 121 -> 122), row 0 col 6 its
  tip past the ink ring (112 -> 116); the bell top (row 2, col 6) brightens 10 -> 11 -> 12 -> 14.
  One model for all four frames: only colours change (D17).

Colours: each region's trimmed median palette index. Hard surface (D50-D53, D65): round lofts
with V-cut seams, chamfered hull blocks, recessed bores; satin metal; no projection bake; outline
shells (D51) from closed proxies. Undersides: closed, plain.

Units while building: sprite px (x = column edge - W/2 - ox, y = row edge down the screen, z up),
moved to Blender by finish() (1/12, y flipped about the block's centre row).

Run: blender --background --python assets/blender/enemies/newshp-19.py [-- --preview out.png]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "assets" / "blender")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
PX = 1 / 12


# --- helpers (copied from newshs-9.py / newshd-275.py; candidates for a shared lib) ---------------
def finish(part, mats, coll, H, ox=0.0, smooth_angle=None):
    """X = (x + ox) / 12, Y = (H / 2 - y) / 12, Z = z / 12."""
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, ox * PX), (0, -PX, 0, H / 2 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle or part.smooth_angle))
    return obj


def spow(v, e):
    return math.copysign(abs(v) ** e, v)


def ring_pts(cx, y, w, zc, ht, hb, n, p):
    out = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        c, s = math.cos(a), math.sin(a)
        out.append((cx + w * spow(c, 2 / p), y, zc + (ht if s > 0 else hb) * spow(s, 2 / p)))
    return out


def tube(P, st, n=16, p=2.6, cap0=True, cap1=True):
    """Loft through stations (y, cx, w, zc, ht, hb, mat[, how]); how: None (radial), "in", "-y", "+y"."""
    rings = []
    for s in st:
        y, cx, w, zc, ht, hb = s[:6]
        if w < 1e-3:
            rings.append([P.v((cx, y, zc))])
        else:
            rings.append([P.v(q) for q in ring_pts(cx, y, w, zc, ht, hb, n, p)])
    for i in range(len(st) - 1):
        a, b = rings[i], rings[i + 1]
        mat = st[i][6]
        how = st[i][7] if len(st[i]) > 7 else None
        cx = (st[i][1] + st[i + 1][1]) / 2
        zc = (st[i][3] + st[i + 1][3]) / 2
        for k in range(n):
            j = (k + 1) % n
            q = [a[k % len(a)], a[j % len(a)], b[j % len(b)], b[k % len(b)]]
            q = [v for ii, v in enumerate(q) if v is not q[ii - 1]]
            ang = 2 * math.pi * (k + 1) / n
            m = mat(ang) if callable(mat) else mat
            c = sum((Vector(v.co) for v in q), Vector()) / len(q)
            if how == "in":
                P.f(q, m, out=(cx - c.x, 0, zc - c.z))
            elif how == "-y":
                P.f(q, m, out=(0, -1, 0))
            elif how == "+y":
                P.f(q, m, out=(0, 1, 0))
            else:
                P.f(q, m, out=(c.x - cx, 0, c.z - zc))
    for r, s, cap, d in ((rings[0], st[0], cap0, -1), (rings[-1], st[-1], cap1, 1)):
        if cap and len(r) > 2:
            m = s[6] if not callable(s[6]) else s[6](math.pi / 2)
            c = P.v((s[1], s[0], s[3]))
            for k in range(len(r)):
                P.f([r[k], r[(k + 1) % len(r)], c], m, out=(0, d, 0))


def tube_cloud(st, n=12, p=2.6, grow=0.0):
    pts = []
    for s in st:
        y, cx, w, zc, ht, hb = s[:6]
        if w < 1e-3:
            pts.append((cx, y, zc))
        else:
            pts += ring_pts(cx, y, w + grow, zc, ht + grow, hb + grow, n, p)
    return pts


def box(P, x0, x1, y0, y1, z0, z1, mat, ch=0.2, chz=None):
    T.hull(P, T.cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


class Mats:
    def __init__(self, sprite, tag):
        self.sprite, self.tag = sprite, tag
        self.list, self.slots = [], {}

    def __call__(self, index, part, frames=None, metallic=0.45, roughness=0.4, emission=0.0):
        key = (index, part)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, f"{self.tag}_{part}", metallic=metallic,
                                                     roughness=roughness, emission_strength=emission,
                                                     frames=frames))
        return self.slots[key]


def proxy_shell(name, clouds, coll, H, ox, faces, voxel=0.008):
    """Outline shell (D51) from a closed proxy: the convex hulls of point clouds."""
    P = T.Part(f"{name}_proxy", smooth_angle=180)
    for pts in clouds:
        T.hull(P, pts, 0)
    proxy = finish(P, [], coll, H, ox)
    shell = common.outline_shell(proxy, coll, voxel=voxel, faces=faces)
    shell.name = f"{name}_outline"
    bpy.data.objects.remove(proxy, do_unlink=True)
    bpy.context.view_layer.update()
    return shell


def load_sprite_json(path):
    return json.loads(Path(path).read_text())


# =================================================================================================
# newshp-19 / newshp-95: the missile
# =================================================================================================
M_OX = 0.5      # axis at column edge 6.5 (x = column edge - 6 - 0.5)
R = 1.5         # body radius (cols 5-7)


def missile_stations(M):
    """Body from the nozzle (tail, row 1-2) to the closed ogive nose (row 13): (y, cx, w, zc, ht, hb, mat, how)."""
    def S(y, r, m, how=None):
        return (y, 0.0, r, 0.0, r, r, m, how) if how else (y, 0.0, r, 0.0, r, r, m)
    st = [
        # nozzle: a recessed glowing throat inside the bell, the bell's exit lip facing up the screen
        S(2.5, 0.42, M["core"], "in"), S(1.85, 0.78, M["bell"], "-y"),
        S(1.85, 1.0, M["bell"]), S(2.05, 1.08, M["bell"]), S(2.45, 1.2, M["bell"]),
        S(2.72, 1.3, M["seam"]), S(2.8, 1.22, M["seam"]), S(2.9, 1.38, M["aft"]),
        S(3.05, R, M["aft"]), S(3.8, R, M["aft"]), S(4.75, R, M["aft"]),
        # joint aft body / motor casing (row 5's top edge): a V-cut
        S(4.88, R, M["seam"]), S(4.97, 1.36, M["seam"]), S(5.06, R, M["band"]),
        S(5.45, R, M["band"]), S(5.8, R, M["seam"]), S(5.86, 1.42, M["seam"]), S(5.92, R, M["mid"]),
        S(7.5, R, M["mid"]), S(9.08, R, M["seam"]), S(9.14, 1.42, M["seam"]), S(9.2, R, M["band"]),
        S(9.55, R, M["band"]), S(9.92, R, M["seam"]), S(10.0, 1.36, M["seam"]), S(10.1, R, M["nose"]),
        # nose: a radome joint at row 11, then the ogive to the tip at row 14
        S(10.9, R, M["nose"]), S(10.97, 1.43, M["seam"]), S(11.03, 1.43, M["nose"]),
        S(11.1, R, M["nose"]), S(11.6, 1.47, M["nose"]), S(12.0, 1.38, M["nose"]),
        S(12.45, 1.2, M["nose"]), S(12.9, 0.95, M["nose"]), S(13.3, 0.68, M["nose"]),
        S(13.62, 0.42, M["nose"]), S(13.85, 0.2, M["nose"]), S(13.97, 0.0, M["nose"]),
    ]
    return st


def flame_stations(M):
    def S(y, r, m):
        return (y, 0.0, r, 0.0, r, r, m)
    return [S(2.3, 0.45, M["core"]), S(1.7, 0.56, M["core"]), S(1.25, 0.56, M["core"]),
            S(1.0, 0.5, M["tip"]), S(0.7, 0.4, M["tip"]), S(0.45, 0.24, M["tip"]), S(0.25, 0.0, M["tip"])]


def fin(P, mat, side, axis, s0, s1, te0, le0, te1, le1, t0, t1):
    """A fin: span s0 (root) -> s1 (tip) out from the axis on `axis` ('x' or 'z', sign `side`),
    trailing edge te, leading edge le (y), thickness t; wedge leading/trailing edges, chamfered tip."""
    def at(s, y, t):
        return (side * s, y, t) if axis == "x" else (t, y, side * s)
    pts = []
    for s, te, le, t in ((s0, te0, le0, t0), (s1 - 0.12, te1, le1 - 0.05, t1), (s1, te1 + 0.08, le1 - 0.15, t1 * 0.45)):
        h = t / 2
        pts += [at(s, te, 0.0), at(s, te + 0.18, h), at(s, te + 0.18, -h),
                at(s, le, 0.0), at(s, le - 0.4, h), at(s, le - 0.4, -h)]
    T.hull(P, pts, mat)


def build_missile(sprite, name, coll, frames, body):
    """frames: the model's four sprite frames in order (cold -> hot); body: (band, mid) palette indices."""
    f1, f2, f3 = frames[1], frames[2], frames[3]
    Mt = Mats(sprite, name)
    M = {
        "aft": Mt(8, "aft", metallic=0.5, roughness=0.36),
        "bell": Mt(10, "bell", frames={f1: 11, f2: 12, f3: 14}, metallic=0.55, roughness=0.32),
        "seam": Mt(5, "seam", metallic=0.4, roughness=0.55),
        "band": Mt(body[0], "band", metallic=0.4, roughness=0.42),
        "mid": Mt(body[1], "mid", metallic=0.4, roughness=0.4),
        "nose": Mt(7, "nose", metallic=0.5, roughness=0.34),
        "fin": Mt(103, "fin", metallic=0.5, roughness=0.36),
        # jet-vane housings: heated by the exhaust on the hot frames
        "vane": Mt(103, "vane", frames={f1: 101, f2: 116, f3: 118}, metallic=0.5, roughness=0.38),
        "vane_lip": Mt(101, "vane_lip", frames={f1: 100, f2: 113, f3: 114}, metallic=0.5, roughness=0.4),
        "core": Mt(115, "core", frames={f1: 120, f2: 121, f3: 122}, metallic=0.0, roughness=0.6, emission=1.5),
        "tip": Mt(112, "tip", frames={f1: 116, f2: 116, f3: 116}, metallic=0.0, roughness=0.6, emission=1.5),
    }
    P = T.Part(name, smooth_angle=40)
    bst = missile_stations(M)
    tube(P, bst, n=24, p=2.0)
    tube(P, flame_stations(M), n=12, p=2.0)
    # side fins (cols 4 / 8, rows 1-4): root inside the body, swept leading edge, tip at |x| 2.5
    for s in (-1, 1):
        fin(P, M["fin"], s, "x", 1.2, 2.52, 1.0, 5.35, 1.0, 4.85, 0.4, 0.24)
    # dorsal / ventral fins (edge-on over col 6 from above): same family, shorter root
    for s in (-1, 1):
        fin(P, M["fin"], s, "z", 1.05, 2.45, 2.15, 5.0, 2.3, 4.55, 0.36, 0.22)
    # jet-vane housings beside the nozzle exit (cols 5 / 7, rows 1-2): a block on the fin root with
    # its aft end sloped down to the trailing edge (the 101 lip)
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.62, s * 1.56))
        T.hull(P, [(x, y, z) for x in (x0, x1) for y, h in ((2.02, 0.78), (3.3, 0.78)) for z in (-h, h)]
               + [(x, 3.42, z) for x in (x0 + 0.06, x1 - 0.06) for z in (-0.68, 0.68)], M["vane"])
        T.hull(P, [(x, y, z) for x in (x0, x1) for y, h in ((1.02, 0.34), (2.04, 0.76)) for z in (-h, h)]
               + [(x, 0.95, z) for x in (x0 + 0.06, x1 - 0.06) for z in (-0.26, 0.26)], M["vane_lip"])
    obj = finish(P, Mt.list, coll, 14, M_OX)
    clouds = [tube_cloud(bst[2:], grow=0.04)]
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.3, s * 2.58))
        clouds.append([(x, y, z) for x in (x0, x1) for y in (0.98, 5.35) for z in (-0.25, 0.25)])
        z0, z1 = sorted((s * 0.3, s * 2.5))
        clouds.append([(x, y, z) for x in (-0.2, 0.2) for y in (2.1, 5.0) for z in (z0, z1)])
        x0, x1 = sorted((s * 0.55, s * 1.62))
        clouds.append([(x, y, z) for x in (x0, x1) for y in (0.95, 3.4) for z in (-0.82, 0.82)])
    shell = proxy_shell(name, clouds, coll, 14, M_OX, faces=1600)
    return [obj, shell]



def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(ROOT, "newshp-19")
    coll = common.reset_collection("newshp-19")
    objs = build_missile(sprite, "newshp-19", coll, [19, 38, 57, 76], (23, 25))
    common.export_sprite_model(ROOT, objs, "enemies/newshp-19", sprite["sprites"])
    if "--preview" in sys.argv:
        ref = ROOT / "reference" / "models" / "newshp-19" / sprite["frames"][0]["image"]
        common.render_preview(objs, sys.argv[sys.argv.index("--preview") + 1], ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
