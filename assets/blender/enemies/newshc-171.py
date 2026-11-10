"""newshc-171 design: the small orb pod (newshc.shp 171-304, 12x14, palette 5), hard-surface (D50-D53,
D65), its top view on the sprite's inner mask (D74; the sprite has no ink border, only its darkest prong
tips and stem tip are ink).

What the sprite shows:
- Plan: a U cradle (cols 4-9, rows 6-12, its round end down the screen) holding a purple orb (cols 5-8,
  rows 7-10); two prongs one pixel wide (cols 4 and 9) running from the cradle's sides up to row 1 (row 0
  on frame 247, ink); a stem two pixels wide (cols 6-7) from the cradle's back to row 4, a pixel longer
  on the left on 228, on the right on 266 and on both on 304; dark pixels (54) either side of the stem
  root at row 6.
- Colours: the prongs and the stem darken up the screen (62 near the cradle to 50/51 at the tips) and
  a pulse of light runs up them frame by frame; the cradle 58 sides / 61 lip; the orb 87-94 with a dark
  85 lower edge (its limb shading, plus a seating ring here).

Design: a ground-mounted plasma fork. A machined cradle (lofted chamfered U section, rounded nose) with
a spherical socket cut into it; the orb seated in a dark gasket ring. The prongs are two segmented
emitter rails: one chamfered, slightly tapered cell per sprite row on a dark core spine, the cells lit
row by row (palette_material frames=, D17), so the sprite's light pulse runs up them; the rails run
down the cradle's flanks as its rim and slope down to the ground towards their tips, each ending in a
small emitter dome. The stem is a pair of segmented feed rods out of a collar on the cradle's back, over
a dark rear bulkhead; the rods' plunger tips extend a row on the frames the sprite draws them longer
(common.frame_part). Underside: flat closed bottoms only.

Run: Blender -b --factory-startup -P assets/blender/enemies/newshc-171.py [-- --no-bake]
"""

import math
import statistics
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402
ROOT = common.repo_root(__file__)
import usp_talon as T  # noqa: E402
from usp_talon import Part, hull, pchip  # noqa: E402

NAME = "newshc-171"
MODEL = f"enemies/{NAME}"
BAKE_DIR = Path("/Users/dlomibao/projects/tyrian-scratch/e1-enemies-2/newshc-171/final/bake")
PX = 1 / 12

# Coordinates in sprite px: x = column edge (0..12, the axis at 7), y = row edge (0 top of the
# screen .. 14), z up from the ground.
CX = 7.0
ORB_Y, ORB_Z, ORB_R = 9.0, 2.35, 1.8
SOCKET_R = 1.95
TINT = (0.95, 0.97, 1.0)

# Material slots.
CUP, TOP, FLANGE, DEEP, ORB, GASKET, COLLAR = range(7)
ARM = [7 + i for i in range(9)]           # rail cells, sprite rows 1..9
ROD_L4, ROD_L5, ROD_R4, ROD_R5 = 16, 17, 18, 19


def region_index(sprite, cells, rule="median"):
    """{frame: palette index} of a region per frame: the low median of its pixels."""
    out = {}
    for fr in sprite["frames"]:
        vals = [fr["pixels"][r][c] for r, c in cells if fr["pixels"][r][c] >= 0]
        out[fr["index"]] = int(statistics.median_low(sorted(vals)))
    return out


def anim_mat(sprite, cells, tag, **kw):
    per = region_index(sprite, cells)
    base = per[sprite["frames"][0]["index"]]
    frames = {f: i for f, i in per.items() if i != base}
    return common.palette_material(sprite, base, f"{NAME}-{tag}", frames=frames or None, **kw)


def materials(sprite):
    pal = lambda i, tag, **kw: common.palette_material(sprite, i, f"{NAME}-{tag}", **kw)  # noqa: E731
    orb = {}
    for fr in sprite["frames"]:   # the orb's lit interior (its 87/85 ring is limb shading)
        v = sorted(fr["pixels"][r][c] for r, c in ((8, 6), (8, 7), (9, 6), (9, 7)))
        orb[fr["index"]] = v[1]
    obase = orb[171]
    mats = [
        pal(58, "cup", metallic=0.35, roughness=0.36),
        pal(61, "top", metallic=0.35, roughness=0.32),
        anim_mat(sprite, [(6, 5), (6, 8)], "flange", metallic=0.3, roughness=0.45),
        pal(51, "deep", metallic=0.2, roughness=0.7),
        common.palette_material(sprite, obase, f"{NAME}-orb", metallic=0.15, roughness=0.3, emission_strength=0.15,
                                frames={f: i for f, i in orb.items() if i != obase} or None),
        pal(85, "gasket", metallic=0.2, roughness=0.55),
        anim_mat(sprite, [(6, 6), (6, 7)], "collar", metallic=0.35, roughness=0.4),
    ]
    for r in range(1, 10):
        mats.append(anim_mat(sprite, [(r, 4), (r, 9)], f"arm{r}", metallic=0.35, roughness=0.34, emission_strength=0.35))
    mats.append(anim_mat(sprite, [(4, 6)], "rodL4", metallic=0.35, roughness=0.4))
    mats.append(anim_mat(sprite, [(5, 6)], "rodL5", metallic=0.35, roughness=0.4))
    mats.append(anim_mat(sprite, [(4, 7)], "rodR4", metallic=0.35, roughness=0.4))
    mats.append(anim_mat(sprite, [(5, 7)], "rodR5", metallic=0.35, roughness=0.4))
    return mats


TEXTURED = (CUP, TOP, FLANGE, DEEP, GASKET, COLLAR, *ARM, ROD_L4, ROD_L5, ROD_R4, ROD_R5)

# --- the cradle ----------------------------------------------------------------------------------

CUP_Y0 = 6.55
_WY = [CUP_Y0, 10.4, 10.9, 11.4, 11.9, 12.4, 12.75, 12.95]
_WV = [2.93, 2.93, 2.84, 2.4, 1.8, 1.12, 0.62, 0.2]
CUP_W = pchip(_WY, _WV)
_HY = [CUP_Y0, 10.6, 11.6, 12.4, 12.95]
CUP_H = pchip(_HY, [2.5, 2.5, 2.3, 1.95, 1.55])
GZ0, GZ1, GD = 0.92, 1.12, 0.07   # the panel groove round the cradle's flanks


def cup_loop(y):
    """The cradle's section: flat bottom, upright flanks with a groove, chamfered top edges.
    Returns (points, material per edge) with the edge i from point i to i+1."""
    w = CUP_W(y)
    h = CUP_H(y)
    c = min(0.38, 0.4 * w)
    cb = min(0.2, 0.3 * w)
    g = min(GD, 0.2 * w)
    right = [(w - cb, 0.0), (w, cb), (w, GZ0), (w - g, GZ0 + 0.05), (w - g, GZ1 - 0.05), (w, GZ1), (w, h - c), (w - c, h)]
    right_m = [CUP, CUP, DEEP, DEEP, DEEP, CUP, CUP]
    left = [(-x, z) for x, z in reversed(right)]
    pts = right + left
    top_m = TOP if 7.7 < y < 12.0 else CUP
    mats = right_m + [top_m] + list(reversed(right_m)) + [CUP]
    return pts, mats


def build_cup(P):
    ys = [CUP_Y0, 7.0, 7.7, 8.5, 9.3, 10.0, 10.4] + [10.4 + 0.15 * i for i in range(1, 17)] + [12.95]
    loops = [cup_loop(y) for y in ys]
    rings = [[P.v((CX + x, y, z)) for x, z in lp[0]] for y, lp in zip(ys, loops)]
    n = len(rings[0])
    for i in range(len(ys) - 1):
        ym = (ys[i] + ys[i + 1]) / 2
        mats = cup_loop(ym)[1]
        for k in range(n):
            j = (k + 1) % n
            P.f((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]), mats[k], away=(CX, ym, 1.0))
    P.f(rings[0], CUP, out=(0, -1, 0))
    P.f(rings[-1], CUP, out=(0, 1, 0))


def build_flange(P):
    """The dark rear bulkhead across the cradle's back, under the rails and the stem collar."""
    hull(P, T.cbox(CX - 2.95, CX + 2.95, 6.02, 6.9, 0.0, 1.75, 0.18), FLANGE)
    # Two bolt heads on its top, either side of the collar.
    for x in (CX - 1.5, CX + 1.5):
        pts = []
        for k in range(6):
            a = 2 * math.pi * k / 6
            for z, r in ((1.65, 0.26), (1.88, 0.26), (1.96, 0.15)):
                pts.append((x + r * math.cos(a), 6.42 + r * math.sin(a), z))
        hull(P, pts, FLANGE)


# --- the rails -----------------------------------------------------------------------------------

RAIL_TOP = pchip([1.0, 3.0, 5.0, 6.5, 10.0, 10.95], [1.2, 1.72, 2.25, 2.62, 2.78, 2.6])
X_IN = 0.0   # keep the rails a hair inside their pixel column


def loft_y(P, stations, mats, cap0=None, cap1=None, centre=None):
    """Loft rings along y: stations are (y, [(x, z), ...]) with the same vertex count, mats[i] the
    material of the span from station i to i+1; caps get cap0/cap1 (None: no cap)."""
    rings = [[P.v((x, y, z)) for x, z in loop] for y, loop in stations]
    n = len(rings[0])
    for i in range(len(rings) - 1):
        ym = (stations[i][0] + stations[i + 1][0]) / 2
        cx = sum(x for x, _ in stations[i][1]) / n
        cz = sum(z for _, z in stations[i][1]) / n
        for k in range(n):
            j = (k + 1) % n
            P.f((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]), mats[i], away=(cx, ym, cz))
    if cap0 is not None:
        P.f(rings[0], cap0, out=(0, -1, 0))
    if cap1 is not None:
        P.f(rings[-1], cap1, out=(0, 1, 0))


def rail_loop(x0, x1, y, zb=0.0, inset=0.0, drop=0.0, ch=0.15, taper=0.09):
    t = RAIL_TOP(min(max(y, 1.0), 10.95)) - drop
    x0i, x1i = x0 + inset, x1 - inset
    return [(x0, zb), (x1, zb), (x1i, t - ch), (x1i - ch - taper, t), (x0i + ch + taper, t), (x0i, t - ch)]


def rail_mat(y):
    r = int(math.floor(y))
    return CUP if r >= 10 else ARM[max(r, 1) - 1]


def build_rails(P):
    """Two continuous emitter rails, one lit cell per sprite row between modelled V grooves."""
    for c in (4, 9):
        x0, x1 = c + X_IN, c + 1 - X_IN
        st, mats = [], []
        st.append((1.0, rail_loop(x0, x1, 1.0, inset=0.1, drop=0.14)))
        st.append((1.12, rail_loop(x0, x1, 1.12)))
        mats += [rail_mat(1.05), rail_mat(1.5)]
        for r in range(2, 11):
            st.append((r - 0.07, rail_loop(x0, x1, r - 0.07)))
            mats.append(DEEP)
            st.append((r - 0.025, rail_loop(x0, x1, r - 0.025, inset=0.06, drop=0.1)))
            mats.append(DEEP)
            st.append((r + 0.025, rail_loop(x0, x1, r + 0.025, inset=0.06, drop=0.1)))
            mats.append(DEEP)
            st.append((r + 0.07, rail_loop(x0, x1, r + 0.07)))
            mats.append(rail_mat(r + 0.5))
        st.append((10.82, rail_loop(x0, x1, 10.82)))
        mats.append(CUP)
        st.append((10.95, rail_loop(x0, x1, 10.95, inset=0.1, drop=0.14)))
        loft_y(P, st, mats, cap0=ARM[0], cap1=CUP)
        # the emitter dome on the tip cell
        xc, yc = c + 0.5, 1.55
        t = RAIL_TOP(yc) - 0.02
        pts = []
        for k in range(10):
            a = 2 * math.pi * k / 10
            for z, r in ((t - 0.05, 0.3), (t + 0.1, 0.28), (t + 0.22, 0.17), (t + 0.26, 0.05)):
                pts.append((xc + r * math.cos(a), yc + r * math.sin(a), z))
        hull(P, pts, ARM[0])


# --- the stem ------------------------------------------------------------------------------------

ROD_ZC, ROD_R = 0.62, 0.5


def rod_seg(P, xc, y0, y1, r, mat, cap0=0.0, cap1=0.0, sides=12, zc=ROD_ZC):
    pts = []
    for y, rr in ((y0, r - cap0), (y0 + max(cap0, 0.04), r), (y1 - max(cap1, 0.04), r), (y1, r - cap1)):
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            pts.append((xc + rr * math.cos(a), y, zc + rr * math.sin(a)))
    hull(P, pts, mat)


def circle(xc, r, zc=ROD_ZC, n=14):
    return [(xc + r * math.cos(2 * math.pi * (k + 0.5) / n), zc + r * math.sin(2 * math.pi * (k + 0.5) / n)) for k in range(n)]


def build_stem(P):
    """Two feed rods (one sprite column each) out of a collar on the cradle's back; a groove at each
    row line, a chamfered end cap at row 4."""
    R = ROD_R
    for xc, m4, m5 in ((6.5, ROD_L4, ROD_L5), (7.5, ROD_R4, ROD_R5)):
        prof = [(4.02, R - 0.2, m4), (4.12, R - 0.05, m4), (4.2, R, m4), (4.93, R, DEEP), (4.97, R - 0.07, DEEP),
                (5.03, R - 0.07, DEEP), (5.07, R, m5), (6.3, R, m5)]
        st = [(y, circle(xc, r)) for y, r, _ in prof]
        mats = [m for _, _, m in prof[:-1]]
        # the end cap's face, a little recessed ring
        loft_y(P, st, mats, cap0=DEEP, cap1=None)
    # the collar the rods leave the cradle by, with a lip band
    hull(P, T.cbox(CX - 0.98, CX + 0.98, 5.9, 6.95, 0.0, 2.1, 0.2), COLLAR)
    hull(P, T.cbox(CX - 1.04, CX + 1.04, 5.86, 6.08, 0.0, 1.62, 0.06), FLANGE)


def build_ext(P, xc):
    """A rod's plunger tip, run out a row (frame part)."""
    rod_seg(P, xc, 3.03, 4.4, ROD_R - 0.12, 0, cap0=0.14, sides=10)
    rod_seg(P, xc, 3.25, 3.42, ROD_R - 0.06, 0, cap0=0.04, cap1=0.04, sides=10)


# --- the orb -------------------------------------------------------------------------------------

def build_orb(P):
    seg, rings = 28, 14
    top = P.v((CX, ORB_Y, ORB_Z + ORB_R))
    bot = P.v((CX, ORB_Y, ORB_Z - ORB_R))
    ring = []
    for i in range(1, rings):
        th = math.pi * i / rings
        z = ORB_Z + ORB_R * math.cos(th)
        rr = ORB_R * math.sin(th)
        ring.append([P.v((CX + rr * math.cos(2 * math.pi * k / seg), ORB_Y + rr * math.sin(2 * math.pi * k / seg), z))
                     for k in range(seg)])
    c = (CX, ORB_Y, ORB_Z)
    for k in range(seg):
        j = (k + 1) % seg
        P.f((top, ring[0][k], ring[0][j]), ORB, away=c)
        P.f((bot, ring[-1][j], ring[-1][k]), ORB, away=c)
        for i in range(len(ring) - 1):
            P.f((ring[i][k], ring[i][j], ring[i + 1][j], ring[i + 1][k]), ORB, away=c)


def build_gasket(P):
    """The dark seating ring where the orb meets the socket's lip."""
    z0 = CUP_H(9.0)
    seg, tub = 32, 8
    R0, r0 = 1.86, 0.14
    rings = []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        rings.append([P.v((CX + (R0 + r0 * math.cos(2 * math.pi * t / tub)) * math.cos(a),
                           ORB_Y + (R0 + r0 * math.cos(2 * math.pi * t / tub)) * math.sin(a),
                           z0 - 0.04 + r0 * math.sin(2 * math.pi * t / tub))) for t in range(tub)])
    for k in range(seg):
        kk = (k + 1) % seg
        a = 2 * math.pi * (k + 0.5) / seg
        cen = (CX + R0 * math.cos(a), ORB_Y + R0 * math.sin(a), z0 - 0.04)
        for t in range(tub):
            tt = (t + 1) % tub
            P.f((rings[k][t], rings[kk][t], rings[kk][tt], rings[k][tt]), GASKET, away=cen)


# --- assembly ------------------------------------------------------------------------------------

def finish(part, mats, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, -6 * PX), (0, -PX, 0, 7 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
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
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


def socket_cut(obj, coll):
    """Cut the orb's spherical socket out of obj (boolean difference, applied)."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=SOCKET_R * PX,
                                         location=((CX - 6) * PX, (7 - ORB_Y) * PX, ORB_Z * PX))
    cutter = bpy.context.active_object
    for m in obj.data.materials:
        cutter.data.materials.append(m)
    for p in cutter.data.polygons:
        p.material_index = TOP
    mod = obj.modifiers.new("socket", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    common._apply_modifiers(obj)
    bpy.data.objects.remove(cutter, do_unlink=True)


def build(coll, sprite):
    mats = materials(sprite)
    cup = Part("cradle", smooth_angle=35)
    build_cup(cup)
    flange = Part("flange", smooth_angle=35)
    build_flange(flange)
    rails = Part("rails", smooth_angle=30)
    build_rails(rails)
    stem = Part("stem", smooth_angle=40)
    build_stem(stem)
    orb = Part("orb", smooth_angle=80)
    build_orb(orb)
    gasket = Part("gasket", smooth_angle=80)
    build_gasket(gasket)
    objs = [finish(p, mats, coll) for p in (cup, rails, stem, orb, gasket, flange)]
    socket_cut(objs[0], coll)
    ext_mat = common.palette_material(sprite, 52, f"{NAME}-plunger", metallic=0.35, roughness=0.38)
    exts = []
    for xc, frames, tag in ((6.5, [228, 304], "L"), (7.5, [266, 304], "R")):
        P = Part(f"{NAME}-plunger-{tag}", smooth_angle=40)
        build_ext(P, xc)
        o = finish(P, [ext_mat], coll)
        exts.append(common.frame_part(o, frames))
    return objs, exts


def bake_maps(obj, out_dir, size=512, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "orbpod171")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    parts, exts = build(coll, sprite)
    obj = T.join(parts, NAME)
    assert all(m is not None for m in obj.data.materials), list(obj.data.materials)
    shell = common.outline_shell(obj, coll, voxel=0.006, faces=1800, smooth=6, inside=0.003)
    shell.name = shell.data.name = f"{NAME}_outline"
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for o in [obj, *exts] for p in o.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles (with plungers)")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        BAKE_DIR.mkdir(parents=True, exist_ok=True)
        shell.hide_render = True
        for e in exts:
            e.hide_render = True
        bake_maps(obj, BAKE_DIR)
        shell.hide_render = False
        for e in exts:
            e.hide_render = False
        fmt = "WEBP"
    common.export_sprite_model(ROOT, [obj, shell, *exts], MODEL, sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
