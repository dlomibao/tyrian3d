"""Horseshoe ring craft (newsh3.shp frame 126), a 3D version of its sprite.

What it is: in 4.4 SURFACE it spawns 48 times on the sky layer from both screen edges, weaving
down the screen (x 0..+-6, y +1..+5 px/tick); in 4.5 CORE 4 more on the top layer; armour 6, a
turret. So a small flying ring craft, not ground structure:

- a steel ring round a tall open hole (the hole stays see-through): an arched top (rows 1-5)
  whose outer and inner edges follow the sprite row by row, straight side rails (rows 6-14);
- brass sleeves clamped round both side rails (rows 7-13), proud of the steel, with machined
  grooves at both ends (the sprite's dark rows 6 and 14);
- two bulky drive pods at the bottom (rows 15-21), their inner faces slanted along the hole's V,
  crowned tops (the sprite's diagonal highlights are sheen on that crown, not ridges), a panel
  seam and a slotted vent on each outer flank, a cap plate on top;
- a round cross bar joining the pods under the hole (row 20) with two short pins hanging from
  it (row 21, columns 10 and 14);
- a stubby thruster nozzle under each pod (rows 22-23), dark bore at its end.

Colours (median of each region, darkest and brightest steps left out as lighting): steel ring and
pods pal_6 (left half 7, right half 5: the light comes from the left), brass pal_23, grooves and
seams pal_4, nozzle bores pal_3. Satin metal. Hard surface (D50-D53, D65): lofted chamfered
sections with smooth stations, modelled grooves and seams; outline shell from a sealed copy, every
outer island (D189). Underside: closed, no detail.

Units: built in sprite px (x = u - 12, y = v, z up; u, v sprite pixel edges) and scaled by
usp_talon.finish (X = x / 12, Y = (14 - v) / 12).

Run: blender --background --python assets/blender/enemies/newsh3-126.py [-- --review DIR]
(exports public/models/enemies/newsh3-126.glb and its spriteModels entry; --review writes review renders to DIR).
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve()


def find_repo():
    """The repo: TYRIAN_REPO, else walk up from this script."""
    env = os.environ.get("TYRIAN_REPO")
    if env:
        return Path(env)
    for p in HERE.parents:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    raise SystemExit("set TYRIAN_REPO to the worktree (assets/blender/common.py not found above the script)")


ROOT = find_repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newsh3-126"
W, H = 24, 28
REF = ROOT / "reference" / "models" / NAME
if not (REF / "sprite.json").exists():
    raise SystemExit(f"reference/models/{NAME} is missing in {ROOT} (npm run catalogue builds it)")
UC = 12.5  # the craft's centre line (sprite edge u)


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


# --- materials -----------------------------------------------------------------------------------

MATS = {}
MAT_LIST = []


def mat(sprite, key, index, metallic=0.7, roughness=0.4, spec=0.5):
    if key in MATS:
        return MATS[key]
    m = common.palette_material(sprite, index, f"{NAME}-{key}", metallic=metallic, roughness=roughness)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Specular IOR Level"].default_value = spec
    MATS[key] = len(MAT_LIST)
    MAT_LIST.append(m)
    return MATS[key]


# --- 2D helpers (sprite edge coords u, v) --------------------------------------------------------

def chaikin(pts, rounds=2):
    """Open polyline corner cutting (end points kept)."""
    for _ in range(rounds):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out.append((a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25))
            out.append((a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75))
        out.append(pts[-1])
        pts = out
    return pts


def mirror(pts):
    return [(2 * UC - u, v) for u, v in pts]


def ray_hit(poly, o, d):
    """Smallest t > 0 where the ray o + t d crosses the polyline (None if it does not)."""
    best = None
    for (x1, y1), (x2, y2) in zip(poly, poly[1:]):
        ex_, ey_ = x2 - x1, y2 - y1
        den = d[0] * ey_ - d[1] * ex_
        if abs(den) < 1e-12:
            continue
        t = ((x1 - o[0]) * ey_ - (y1 - o[1]) * ex_) / den
        s = ((x1 - o[0]) * d[1] - (y1 - o[1]) * d[0]) / den
        if t > 1e-9 and -1e-9 <= s <= 1 + 1e-9 and (best is None or t < best):
            best = t
    return best


# The ring's outer and inner edges, left half, from the top centre down (u, v pixel edges),
# placed on the inner edge of the sprite's ink ring (the game draws the ink, D74).
OUTER_L = chaikin([(UC, 0.95), (8.6, 0.95), (6.6, 1.85), (5.75, 3.1), (5.15, 4.25), (4.75, 5.2),
                   (4.15, 6.15), (4.0, 7.0), (4.0, 8.6), (3.0, 9.4), (3.0, 16.0)], 2)
INNER_L = chaikin([(UC, 3.0), (10.4, 3.0), (9.15, 4.2), (8.1, 5.3), (7.0, 6.6), (7.0, 11.7),
                   (7.7, 12.6), (8.0, 13.2), (8.0, 16.0)], 2)
OUTER = list(reversed(OUTER_L)) + mirror(OUTER_L)[1:]  # left bottom -> top -> right bottom
INNER = list(reversed(INNER_L)) + mirror(INNER_L)[1:]
ARCH_C = (UC, 5.9)


def rail_stations():
    """(I, O, kind, t) along the ring: kind 'side' (with v) or 'arch' (with angle)."""
    st = []
    side_v = [14.95, 14.9, 14.1, 14.0, 13.95, 13.0, 12.0, 11.0, 10.0, 9.4, 9.0, 8.6, 8.0, 7.3, 7.05,
              7.0, 6.95, 6.2, 6.15, 6.1, 5.95]
    for v in side_v:
        st.append(("L", v))
    n_arch = 30
    for k in range(n_arch + 1):
        st.append(("A", math.pi * (1 - k / n_arch)))
    for v in reversed(side_v):
        st.append(("R", v))
    out = []
    for kind, t in st:
        if kind == "A":
            d = (math.cos(t), -math.sin(t))
            o = ARCH_C
        else:
            d = (-1.0, 0.0) if kind == "L" else (1.0, 0.0)
            o = (UC, t)
        ti, to = ray_hit(INNER, o, d), ray_hit(OUTER, o, d)
        I = (o[0] + d[0] * ti, o[1] + d[1] * ti)
        O = (o[0] + d[0] * to, o[1] + d[1] * to)
        out.append((I, O, kind, t))
    return out


# --- sections ------------------------------------------------------------------------------------

def rr_profile(w, zb, zt, r_in, r_out, r_bot, seg=3):
    """A rounded rectangle across s in [0, w] (0 = inner edge), z in [zb, zt], anticlockwise
    seen with s right and z up; corner radii r_in (top inner), r_out (top outer), r_bot (bottom)."""
    pts = []
    corners = [((w - r_bot, zb + r_bot), r_bot, -90), ((w - r_out, zt - r_out), r_out, 0),
               ((r_in, zt - r_in), r_in, 90), ((r_bot, zb + r_bot), r_bot, 180)]
    for (cs, cz), r, a0 in corners:
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cs + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def place(I, O, prof, grow_w=0.0):
    """Section points in px space (x, y, z) across from I to O (sprite edge coords)."""
    iu, iv = I
    ou, ov = O
    du, dv = ou - iu, ov - iv
    L = math.hypot(du, dv)
    nu, nv = du / L, dv / L
    out = []
    for s, z in prof:
        u = iu + nu * s
        v = iv + nv * s
        out.append((u - 12.0, v, z))
    return out


def loft(P, rings, mats, cap0=True, cap1=True, closed=False):
    """Loft rings of (x, y, z) points; mats[i] = material of band i (or a function (i, k) -> slot)."""
    vs = [[P.v(p) for p in r] for r in rings]
    n = len(vs[0])
    bands = len(vs) if closed else len(vs) - 1
    for i in range(bands):
        r0, r1 = vs[i], vs[(i + 1) % len(vs)]
        c = sum((Vector(p) for p in rings[i]), Vector()) / n
        for k in range(n):
            j = (k + 1) % n
            m = mats(i, k) if callable(mats) else mats[i]
            P.f((r0[k], r0[j], r1[j], r1[k]), m, away=tuple(c))
    if not closed:
        for ring, rv, cap in ((rings[0], vs[0], cap0), (rings[-1], vs[-1], cap1)):
            if cap:
                c = sum((Vector(p) for p in ring), Vector()) / n
                cv = P.v(tuple(c))
                m0 = mats(0, 0) if callable(mats) else (mats[0] if ring is rings[0] else mats[-1])
                # a fan cap, facing away from the loft's next ring
                nxt = rings[1] if ring is rings[0] else rings[-2]
                cn = sum((Vector(p) for p in nxt), Vector()) / n
                outward = c - cn
                for k in range(n):
                    P.f((rv[k], rv[(k + 1) % n], cv), m0, out=tuple(outward))
    return vs


# --- the parts -----------------------------------------------------------------------------------

def build_ring(sprite, P):
    steel = mat(sprite, "steel", 6, metallic=0.6, roughness=0.34)
    brass = mat(sprite, "brass", 23, metallic=0.7, roughness=0.34)
    groove = mat(sprite, "groove", 4, metallic=0.6, roughness=0.5)
    rings, band_mats = [], []
    sts = rail_stations()
    for I, O, kind, t in sts:
        w = math.hypot(O[0] - I[0], O[1] - I[1])
        zb, zt = -1.25, 1.55
        r_in, r_out, r_bot = 0.75, 1.0, 0.7
        m = steel
        if kind == "A":
            # the arch thins a little towards the crown
            k = math.sin(t)
            zt -= 0.2 * k
            zb += 0.15 * k
            # two panel grooves across the arch shoulders
            if abs(abs(t - math.pi / 2) - math.radians(48)) < math.radians(2.5):
                zt -= 0.3
                m = groove
        else:
            v = t
            if 6.98 <= v <= 13.97:  # brass sleeve (rows 7-13), proud of the steel
                zt += 0.3
                zb -= 0.15
                r_out = 1.1
                m = brass
            elif 6.12 <= v < 6.98 or 13.97 < v:  # grooves either end of the sleeve (rows 6, 14)
                zt -= 0.35
                zb += 0.2
                m = groove
        prof = rr_profile(w, zb, zt, min(r_in, w * 0.3), min(r_out, w * 0.42), min(r_bot, w * 0.3))
        rings.append(place(I, O, prof))
        band_mats.append(m)
    # band i takes the material of the station pair; pick the 'odd one out' (sleeve, groove) wins
    mats = []
    for i in range(len(rings) - 1):
        a, b = band_mats[i], band_mats[i + 1]
        mats.append(a if a == b else (brass if brass in (a, b) else groove))
    loft(P, rings, mats, cap0=True, cap1=True)


def pod_extent(v, side):
    """Left/right u of the left drive pod at row edge v (the right pod is its mirror)."""
    outer = [(14.3, 3.0), (18.6, 3.0), (19.3, 3.85), (21.4, 4.05), (22.0, 4.7)]
    inner = [(14.3, 8.05), (15.0, 8.6), (15.6, 9.15), (16.3, 9.9), (17.6, 10.1), (18.5, 11.0),
             (19.3, 11.9), (20.2, 11.6), (21.2, 10.0), (22.0, 9.1)]

    def lerp(tab, v):
        if v <= tab[0][0]:
            return tab[0][1]
        for (v0, a), (v1, b) in zip(tab, tab[1:]):
            if v <= v1:
                return a + (b - a) * (v - v0) / (v1 - v0)
        return tab[-1][1]
    return lerp(outer, v), lerp(inner, v)


def build_pods(sprite, P):
    steel = mat(sprite, "steel", 6, metallic=0.6, roughness=0.34)
    seam = mat(sprite, "groove", 4, metallic=0.6, roughness=0.5)
    bore = mat(sprite, "bore", 3, metallic=0.5, roughness=0.6)
    vs = [14.85, 15.25, 15.6, 16.3, 17.0, 17.55, 17.7, 17.85, 18.0, 18.5, 19.3, 20.2, 21.0, 21.5,
          21.8, 22.0]
    for side in (-1, 1):
        rings, mats = [], []
        for v in vs:
            u0, u1 = pod_extent(v, side)
            # crowned top, rising toward the middle of the pod; shrink at both ends (chamfers)
            zt = 2.15 + 0.35 * math.sin(math.pi * min(1, max(0, (v - 14.85) / 7.15)))
            zb = -1.7
            if v in (14.85, 22.0):
                zt -= 0.45
                zb += 0.35
            if v in (14.85, 22.0):
                u0 += 0.25
                u1 -= 0.25
            if 17.6 < v < 17.95:  # a seam round the pod
                zt -= 0.3
                u0 += 0.2
            w = u1 - u0
            prof = rr_profile(w, zb, zt, 1.0, 1.7, 0.8)
            I, O = (u1, v), (u0, v)  # 'inner' = hole side
            if side > 0:
                I, O = (2 * UC - u1, v), (2 * UC - u0, v)
            rings.append(place(I, O, prof))
            mats.append(seam if 17.6 < v < 17.95 else steel)
        bands = [seam if (mats[i] == seam or mats[i + 1] == seam) else steel for i in range(len(rings) - 1)]
        loft(P, rings, bands)
        # a slotted vent on the outer flank (three slots), visible from the side and the game camera
        for k in range(3):
            vv = 15.4 + k * 0.75
            uo = pod_extent(vv, side)[0]
            u = uo + 0.05 if side < 0 else 2 * UC - uo - 0.05
            x = u - 12.0
            sx = -1 if side < 0 else 1
            T.hull(P, T.cbox(x - 0.25 * (sx < 0) - 0.05, x + 0.25 * (sx > 0) + 0.05, vv, vv + 0.42, -0.3, 0.9, 0.06),
                   seam)
        # a cap plate on the crown
        cu = 5.9 if side < 0 else 2 * UC - 5.9
        x = cu - 12.0
        T.hull(P, T.cbox(x - 1.25, x + 1.25, 18.4, 20.6, 1.9, 2.75, 0.3, 0.2), steel)
        # the thruster nozzle under the pod's front end: a short tube, a lip ring and a dark bore
        lu = 6.5 if side < 0 else 2 * UC - 6.5
        x = lu - 12.0
        z = -0.35
        ring_pts = []
        for v, r in ((21.2, 1.35), (22.3, 1.45), (22.4, 1.36), (22.55, 1.45), (23.3, 1.5), (23.55, 1.42),
                     (23.8, 1.2)):
            ring_pts.append([(x + r * math.cos(a), v, z + 0.9 * r * math.sin(a))
                             for a in (2 * math.pi * (i + 0.5) / 14 for i in range(14))])
        loft(P, ring_pts, [steel, seam, seam, steel, steel, steel], cap0=True, cap1=False)
        last = ring_pts[-1]
        inner_ring = [(x + 0.75 * math.cos(a), 23.6, z + 0.9 * 0.75 * math.sin(a))
                      for a in (2 * math.pi * (i + 0.5) / 14 for i in range(14))]
        loft(P, [last, inner_ring], [steel], cap0=False, cap1=True)
        # recolour that bore cap
        for f in P.bm.faces[-14:]:
            f.material_index = bore


def build_bar(sprite, P):
    steel = mat(sprite, "steel", 6, metallic=0.6, roughness=0.34)
    seam = mat(sprite, "groove", 4, metallic=0.6, roughness=0.5)
    vc, r, z = 20.5, 0.8, 0.1
    n = 14
    rings = []
    for u in (9.6, 10.4, 10.6, 14.4, 14.6, 15.4):
        rings.append([(u - 12.0, vc + r * math.cos(a), z + r * math.sin(a))
                      for a in (2 * math.pi * (i + 0.5) / n for i in range(n))])
    loft(P, rings, [steel, seam, steel, seam, steel])
    # two short pins hanging from the bar's ends (row 21, columns 10 and 14)
    for u in (10.5, 14.5):
        rings = []
        for v, rr in ((20.5, 0.45), (21.6, 0.42), (21.85, 0.3)):
            rings.append([(u - 12.0 + rr * math.cos(a), v, z - 0.3 + rr * math.sin(a))
                          for a in (2 * math.pi * (i + 0.5) / 10 for i in range(10))])
        loft(P, rings, [steel, steel])


def build(sprite, coll):
    parts = []
    for name, fn, angle in (("ring", build_ring, 40), ("pods", build_pods, 40), ("bar", build_bar, 45)):
        P = T.Part(f"{NAME}_{name}", smooth_angle=angle)
        fn(sprite, P)
        bmesh.ops.triangulate(P.bm, faces=[f for f in P.bm.faces if len(f.verts) > 4])
        parts.append(T.finish(P, MAT_LIST, coll))
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = parts[0]
    obj.name = obj.data.name = NAME
    me = obj.data
    used = sorted({p.material_index for p in me.polygons})
    remap = {k: i for i, k in enumerate(used)}
    idx = [remap[p.material_index] for p in me.polygons]
    mats = [me.materials[k] for k in used]
    me.materials.clear()
    for m in mats:
        me.materials.append(m)
    for p, k in zip(me.polygons, idx):
        p.material_index = k
    return obj


def shell_of(obj, coll):
    """Outline shell (D51) from a sealed copy of the model, every outer island kept (D189)."""
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    bpy.context.view_layer.update()
    sh = common.outline_shell(closed, coll, islands="outer", inside=0.01)
    sh.name = sh.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    assert len(sh.data.polygons) > 0, "empty outline shell"
    return sh


# --- review renders (only with --review) ---------------------------------------------------------

def review(obj, shell, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    PX = 1 / 12

    def cam(name, loc, look, ortho=None, lens=50):
        data = bpy.data.cameras.new(name)
        if ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.lens = lens
        c = bpy.data.objects.new(name, data)
        scene.collection.objects.link(c)
        c.location = loc
        d = Vector(look) - Vector(loc)
        c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return c

    def render(c, path, rx, ry):
        scene.camera = c
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    ext = max(W, H) * PX
    top = cam("top", (0, 0, 20), (0, 0, 0), ortho=ext)
    top.rotation_euler = (0, 0, 0)
    shell.hide_render = True
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    render(top, out / "top_mask.png", W * 8, H * 8)
    render(top, out / "top_flat.png", W * 8, H * 8)
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            pass
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rv")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.06, 0.07, 0.09, 1)
    bg.inputs["Strength"].default_value = 1.0
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 3.5
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(40), math.radians(-25), math.radians(-30))
    d = 5.2
    views = [
        ("top", top, 480, 560),
        ("side", cam("side", (-d, 0, 0.1), (0, 0, 0.1), ortho=2.7), 560, 320),
        ("front", cam("front", (0, -d, 0.1), (0, 0, 0.1), ortho=2.7), 560, 320),
        ("rear", cam("rear", (0, d, 0.1), (0, 0, 0.1), ortho=2.7), 560, 320),
        ("q34", cam("q34", (d * 0.6, -d * 0.6, d * 0.55), (0, 0, 0.0), lens=55), 480, 420),
        ("q34b", cam("q34b", (-d * 0.6, d * 0.55, d * 0.55), (0, 0, 0.0), lens=55), 480, 420),
        ("game", cam("game", (0, -d * math.sin(math.radians(32)), d * math.cos(math.radians(32))), (0, 0, 0),
                     lens=55), 480, 420),
        ("under", cam("under", (0.8, -2.5, -4.0), (0, 0, 0.0), lens=55), 480, 420),
    ]
    for name, c, rx, ry in views:
        render(c, out / f"{name}.png", rx, ry)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    (out / "stats.txt").write_text(f"triangles {tris}\nshell faces {len(shell.data.polygons)}\n"
                                   f"materials {[m.name for m in obj.data.materials]}\n")
    print("review renders in", out, "triangles", tris)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    shell = shell_of(obj, coll)
    common.export_sprite_model(ROOT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])
    print(f"{sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles, shell "
          f"{len(shell.data.polygons)} faces")
    if "--review" in sys.argv:
        review(obj, shell, arg("--review"))


if __name__ == "__main__":
    main()
