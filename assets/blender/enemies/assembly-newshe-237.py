"""Design A of assembly-newshe-237: a falling red crystal shard, point down, split by a crack, with a
white-hot ridge and a glowing point (newshe.shp 199 over 237, one frame each; STARGATE 3.8).

What it is: one long faceted crystal lying along the screen's Y (24 x 56 px). A broad, gently
sloped left flank rises to a hot ridge on column 12; right of the ridge the crystal is split by a
through-crack (the transparent slit, columns 15-17, rows 10-42) that leaves a lower, slimmer sliver on
its right side. Both parts share the short pyramid termination at the top and fuse into the long
glowing point at the bottom. Facets are crisp (flat shaded, planar stations); each facet takes the
sprite's own median palette index (the gem/rock facet-ramp rule, D175/D182), the ridge and the point
glow (metallic 1, rough, D126/D173).

Pieces: built once in assembly coordinates (Blender origin = the shard's centre, screen 224,153),
cut by common.split_assembly into newshe-199 (top) and newshe-237 (bottom); each piece gets its own
outline shell from a sealed copy (D90/D118), checked to cover every part of the piece.

Run: Blender --background --python assets/blender/enemies/assembly-newshe-237.py
Exports public/models/enemies/<piece>.glb (+ src/render/spriteModels/<piece>.json) for each piece."""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = ROOT = common.repo_root(__file__)

NAME = "assembly-newshe-237"
PIECES = ["newshe-199", "newshe-237"]
# piece centres relative to the shard centre (screen 224,153): 199 at (224,139), 237 at (224,167)
LAYOUT = [("newshe-199", 0, -14), ("newshe-237", 0, 14)]
TAG = "n237a"


def X(u):
    """Sprite column edge u (column c spans c..c+1) to Blender X."""
    return (u - 12) / 12


def Y(v):
    """Sprite row edge v to Blender Y (up the screen is +Y)."""
    return (28 - v) / 12


def pl(points, v):
    """Piecewise-linear function through (v, value) points, clamped at the ends."""
    if v <= points[0][0]:
        return points[0][1]
    for (v0, a), (v1, b) in zip(points, points[1:]):
        if v <= v1:
            t = 0 if v1 == v0 else (v - v0) / (v1 - v0)
            return a + (b - a) * t
    return points[-1][1]


# --- Outline (sprite inner mask, fitted with straight facet lines) ---------------------------------

# Main body: left girdle edge (the whole crystal's left side), from the top apex to the bottom point.
MAIN_L = [(1.5, 12.6), (4.5, 7.0), (7.5, 4.0), (31.5, 4.0), (32.4, 4.9), (40.5, 6.0), (48.5, 9.4),
          (53.6, 12.6), (54.3, 13.05)]
# Main body: right edge (the crack's left wall between rows 9 and 43; the tip's right side below).
MAIN_R = [(1.5, 13.3), (3.0, 15.4), (7.0, 15.0), (16.6, 15.0), (17.2, 14.0), (31.6, 14.0), (32.2, 13.0),
          (42.6, 13.0), (43.5, 14.1), (44.5, 17.8), (49.5, 15.2), (53.6, 13.7), (54.3, 13.15)]
# Ridge height (u) of the prism and position (column edge of the ridge's centre). The top
# termination is not in MAIN_H: it ramps up from the apex to the chevron break (the sprite's second,
# inner arc at rows 8-10), see TERM and main_ring().
MAIN_H = [(1.5, 1.0), (31.5, 1.0), (42.0, 0.92), (47.0, 0.68), (54.3, 0.12)]
MAIN_P = [(1.5, 12.95), (8.0, 12.5), (46.0, 12.5), (54.3, 13.1)]
# Left bevel width (px): one column on the prism, wider down the lit taper.
# Over the cap it widens into the hood's rim band (sprite rows 3-7: 116-123 along the shoulder).
MAIN_BEV = [(1.5, 0.6), (3.0, 2.4), (5.5, 2.0), (8.0, 1.1), (31.5, 1.0), (34.0, 1.6), (44.0, 1.6),
            (50.0, 1.1), (54.3, 0.2)]
# Station breaks for the facet colours (ridge glow ramp, the glowing point) and the cap's facets.
# Stations are in the chevron coordinate w (see main_ring): w = v on the girdle and the ridge.
MAIN_BREAKS = [2.5, 3.5, 5.5, 6.5, 7.9, 8.9, 10.5, 12.0, 14.0, 16.0, 19.5, 23.5, 44.0, 47.0]

# Hood: the termination facets rise steeply from the apex to the inner arc, which is a gentler
# chamfer facet (w 7.9-8.9) before the prism top. In the cap the loft's sections are chevrons, not
# rows: a section's interior points sit CHEV px per column lower away from the ridge, so the facet
# breaks run as the sprite's arcs do (on the ridge at row 8, down to row 10 at column 6).
TERM = [(1.5, 0.35), (7.9, 0.92), (8.9, 1.0)]
CHEV = 0.36
CHEV_FADE = [(9.0, 1.0), (16.0, 0.0)]

# Sliver right of the crack: shares the top termination, fuses into the point.
BLADE_L = [(2.3, 14.6), (8.1, 14.6), (8.5, 18.0), (37.0, 18.0), (38.0, 17.2), (41.5, 17.0), (43.5, 15.0),
           (45.2, 14.4)]
BLADE_R = [(2.3, 15.0), (6.3, 22.0), (31.6, 22.0), (32.3, 21.45), (42.5, 18.9), (44.5, 17.8), (45.2, 17.45)]
BLADE_H = [(2.3, 0.10), (7.5, 0.55), (31.5, 0.55), (44.0, 0.42), (45.2, 0.30)]
BLADE_BREAKS = [3.3, 4.3, 5.2, 6.0, 7.0, 8.0, 14.0]
# Width (px) of the sliver's outer chamfer: wide over the shoulder, where it carries the hood's rim.
BLADE_CW = [(2.3, 1.0), (4.0, 2.2), (7.0, 2.0), (9.0, 1.0)]


def stations(*funcs, extra=()):
    vs = sorted({round(v, 4) for f in funcs for v, _ in f} | {round(v, 4) for v in extra})
    lo = max(f[0][0] for f in funcs)
    hi = min(f[-1][0] for f in funcs)
    return [v for v in vs if lo <= v <= hi]


# --- Materials -------------------------------------------------------------------------------------

def make_materials(sprite):
    def pal(i, metallic=0.45, roughness=0.38, glow=0.0, spec=0.5, tag=TAG):
        if glow:
            m = common.palette_material(sprite, i, f"{tag}g", metallic=1.0, roughness=0.85, emission_strength=glow)
        else:
            m = common.palette_material(sprite, i, tag, metallic=metallic, roughness=roughness)
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    mats = {
        "under": pal(64, metallic=0.1, roughness=0.8),
        "dark": pal(113),            # broad left facet, crack walls, lower walls
        "deep": pal(114),            # sliver's crack-side top
        "mid": pal(115),             # left lower facet, sliver top
        "wall": pal(116),            # right wall, sliver's right bevel
        "flankl": pal(119, metallic=0.75, roughness=0.36),   # left flank beside the ridge (glow spill shows as sheen)
        "bevel": pal(121, metallic=0.4, roughness=0.3),  # lit left bevel
        "flankr": pal(121, glow=0.35),         # right flank beside the hot ridge: ember
        "rid126": pal(126, glow=1.0),         # white-hot ridge
        "rid123": pal(123, glow=1.0),
        "rid120": pal(120, glow=1.0),
        "rid125": pal(125, glow=1.0),
        "tip122": pal(122, glow=0.55),        # glowing point's facets
        "tipwall": pal(117, glow=0.25),
        "rim": pal(121, metallic=0.45, roughness=0.32, spec=0.6),  # hood rim band (outer arc)
        "arc2": pal(121, glow=0.45),  # inner arc (termination break): warm, beside the hot ridge
    }
    order = list(mats)
    return [mats[k] for k in order], {k: i for i, k in enumerate(order)}


# --- Geometry --------------------------------------------------------------------------------------

def loft(bm, sections, strip_mat, bottom_mat):
    """Faceted loft along Y: sections (y, [(x, z) or (x, y, z), ...]) left to right over the top, closed underneath
    by the last->first edge; ends capped. strip_mat(k, i, u) -> material of the facet between points
    i and i+1 of sections k and k+1 (u: the facet's mean sprite column)."""
    rings = [[bm.verts.new(p if len(p) == 3 else (p[0], y, p[1])) for p in pts] for y, pts in sections]
    n = len(rings[0])
    faces = []
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            u = 12 + 12 * sum(v.co.x for v in (r0[i], r0[j], r1[j], r1[i])) / 4
            f.material_index = strip_mat(k, i, u) if j else bottom_mat
            faces.append(f)
    for ring, last in ((rings[0], False), (rings[-1], True)):
        f = bm.faces.new(ring if last else list(reversed(ring)))
        f.material_index = strip_mat(0 if not last else len(rings) - 2, 1, 12.0)
        faces.append(f)
    for f in faces:
        f.smooth = False
    return faces


def mono(xs, eps=0.02):
    out = []
    for x in xs:
        out.append(max(x, out[-1] + eps) if out else x)
    return out


def main_section(v):
    """Sprite columns and heights (before the termination ramp) of the 10 ring points at row v."""
    L, R, H, P, bev = pl(MAIN_L, v), pl(MAIN_R, v), pl(MAIN_H, v), pl(MAIN_P, v), pl(MAIN_BEV, v)
    w = min(0.5, max(0.05, (R - L) * 0.12))  # ridge chamfer half-width
    P = min(max(P, L + w + 0.1), R - w)
    rl, rr = P - w, P + w
    sl = rl - L
    bev = min(bev, sl * 0.55)
    a = L + bev + 0.32 * (sl - bev)
    b = L + 0.8 * sl
    sr = max(R - rr, 0.0)
    c = rr + 0.6 * sr
    ins = min(0.5, (R - L) * 0.2)
    top = mono([L, L + bev, a, b, rl, rr, c, R])
    us = [top[0] + ins] + top + [top[-1] - ins]
    # crack walls fall steeply: right of the ridge the cliff goes down to the girdle
    zs = [0.0, 0.30 * H, 0.60 * H, 0.80 * H, 0.94 * H, H, H, 0.80 * H if sr > 0.3 else 0.85 * H, 0.32 * H, 0.0]
    return list(zip(us, zs))


def main_ring(w):
    """Ring at chevron station w: points 2-7 (inside the girdle and its bevel) sit at row
    v = w + CHEV * |u - ridge| (faded out down the prism), solved per point; the rest at v = w."""
    fade = pl(CHEV_FADE, w)
    ridge = pl(MAIN_P, w)
    base = main_section(w)
    t = pl(TERM, w)
    out = []
    for i in range(len(base)):
        v = w
        if 2 <= i <= 7 and fade > 0:
            for _ in range(6):
                u = main_section(v)[i][0]
                v = w + CHEV * fade * abs(u - ridge)
        u, z = main_section(v)[i]
        out.append((X(u), Y(v), z * t))
    return out


def main_mats(M, vs):
    def f(k, i, u):
        vm = 0.5 * (vs[k] + vs[k + 1])
        tip = vm >= 44.0
        inner = 7.9 <= vm <= 8.9   # the inner arc: the chamfer facet at the termination break
        if i == 0:
            return M["dark"]
        if i == 1:
            if vm < 8.0:
                return M["rim"]
            return M["tip122"] if tip else M["bevel"]
        if i == 2:
            if inner:
                return M["arc2"]
            return M["tip122"] if tip else M["mid"]
        if i == 3:
            if inner:
                return M["arc2"]
            return M["tip122"] if vm >= 46.0 else M["dark"]
        if i == 4:
            if inner:
                return M["arc2"]
            if vm < 7.9:
                return M["mid"]
            return M["tip122"] if tip else M["flankl"]
        if i == 5:
            if vm < 19.5:
                return M["rid126"]
            if vm < 23.5:
                return M["rid123"]
            if vm < 44.0:
                return M["rid120"]
            if vm < 47.0:
                return M["rid123"]
            return M["rid125"]
        if i == 6:
            if vm < 4.6:
                return M["rim"]
            if vm < 7.8:
                return M["mid"]
            return M["tipwall"] if tip else M["flankr"]
        if i == 7:
            if vm < 4.6:
                return M["rim"]
            return M["tipwall"] if tip else M["wall"]
        return M["dark"]
    return f


def blade_section(v):
    L, R, h = pl(BLADE_L, v), pl(BLADE_R, v), pl(BLADE_H, v)
    w = R - L
    ins = min(0.4, w * 0.2)
    cw = min(pl(BLADE_CW, v), w * 0.35)   # outer chamfer: the rim band on the shoulder, 1 px below
    top = mono([L, L + min(1.0, w * 0.25), L + 0.45 * w, R - cw, R], eps=0.01)
    us = [top[0] + ins] + top + [top[-1] - ins]
    zs = [0.0, 0.55 * h, 0.9 * h, h, 0.9 * h, 0.4 * h, 0.0]
    return [(X(u), z) for u, z in zip(us, zs)]


def blade_mats(M, vs):
    # the hood's rim continues down the sliver's shoulder (rows 3-7, cols 15-21: 119-121) as the
    # outer chamfer facets, so it follows the arc; inside it the sliver is dark (rows 6-7: 113-115)
    def f(k, i, u):
        vm = 0.5 * (vs[k] + vs[k + 1])
        if i in (0, 1):
            return M["rim"] if (i == 1 and vm < 4.0) else M["dark"]
        if i == 2:
            return M["rim"] if vm < 4.0 else M["deep"]
        if i == 3:
            return M["rim"] if vm < 4.5 else M["mid"]
        if i == 4:
            return M["rim"] if vm < 8.0 else M["wall"]
        return M["dark"]
    return f


def build(coll, name=NAME):
    sprite = common.load_sprite(WT, PIECES[0])
    for n in PIECES[1:]:
        sprite["colors"].update(common.load_sprite(WT, n)["colors"])
    mats, M = make_materials(sprite)
    bm = bmesh.new()
    vs = stations(MAIN_L, MAIN_R, MAIN_H, MAIN_P, MAIN_BEV, extra=MAIN_BREAKS)
    loft(bm, [(None, main_ring(w)) for w in vs], main_mats(M, vs), M["under"])
    bvs = stations(BLADE_L, BLADE_R, BLADE_H, extra=BLADE_BREAKS)
    loft(bm, [(Y(v), blade_section(v)) for v in bvs], blade_mats(M, bvs), M["under"])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def shell_covers(shell, piece):
    """The shell keeps only the largest voxel island (common.outline_shell): make sure it spans the
    piece's whole footprint (both the main body and the sliver)."""
    import mathutils
    pv = [v.co for v in piece.data.vertices]
    sv = [v.co for v in shell.data.vertices]
    if not sv:
        return False, "empty shell"
    def bb(vs):
        return (min(v.x for v in vs), max(v.x for v in vs), min(v.y for v in vs), max(v.y for v in vs))
    a, b = bb(pv), bb(sv)
    ok = all(abs(x - y) < 0.06 for x, y in zip(a, b))
    # and sample: a vertex of the shell near the sliver's right edge (x > 0.6) and near the left (x < -0.5)
    has_r = any(v.x > 0.6 for v in sv) if any(v.x > 0.65 for v in pv) else True
    has_l = any(v.x < -0.55 for v in sv)
    return ok and has_r and has_l, f"piece bb {tuple(round(x, 3) for x in a)} shell bb {tuple(round(x, 3) for x in b)}"


def cut_open(obj, layout, coll):
    """common.split_assembly without filling the cut: for the outline shell, so no ink is drawn
    across the shard where the two pieces meet."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    layout = [(n, cx, cy) for n, cx, cy in LAYOUT]
    pieces = common.split_assembly(obj, layout)
    # sealed pre-cull copy (D90/D118): one shell round the whole shard (no grooves to bridge, so the
    # same build), then cut open at the piece boundary so no ink is drawn across the joint.
    plain = build(coll, name=NAME + "_plain")
    bpy.context.view_layer.update()
    whole = common.outline_shell(plain, coll, voxel=0.02, faces=1700, inside=0.010)
    shells = cut_open(whole, layout, coll)
    bpy.data.objects.remove(whole, do_unlink=True)
    bpy.data.objects.remove(plain, do_unlink=True)
    report = {}
    for n, _, _ in layout:
        sh = shells[n]
        ok, msg = shell_covers(sh, pieces[n])
        report[n] = {"shell_ok": ok, "shell_verts": len(sh.data.vertices), "msg": msg,
                     "shell_tris": sum(len(p.vertices) - 2 for p in sh.data.polygons),
                     "tris": sum(len(p.vertices) - 2 for p in pieces[n].data.polygons)}
        print(f"SHELL {n}: ok={ok} verts={len(sh.data.vertices)} {msg}")
    for n, _, _ in layout:
        data = common.load_sprite(ROOT, n)
        common.export_sprite_model(ROOT, [pieces[n], shells[n]], f"enemies/{n}", data["sprites"])
    print(json.dumps(report))


if __name__ == "__main__":
    main()
