"""Rock pile (newshr.shp, assembly of 12 ground2 pieces, 72 x 112 px block): a 3D version of its sprites.

Seen in episode 3 (level 3.4, the IXMUCANE boss). Twelve 2x2 pieces (three columns of four: sheet frames
153-157, 191-195, 229-233, 267-271) make one pile of boulders: mostly brown rocks lit from the upper
left, a few golden ones, three blue-grey slates and a tall leaning slab on top, a single orange glint on
a golden rock. At first it covers the left edge of the neighbouring heap (assembly-newshr-273) and the
two slide apart in ev20.

What it is: a heap of broken stones. Built whole in assembly coordinates and cut into the 12 pieces with
common.split_assembly, the same way as assembly-newshr-273's rocks:
- one lib_newshd_rock rock body per stone of the sprite (its region found by sharing the pile's pixels
  between the seed points along the dark crevices), lofted from its own region, its waist standing
  higher the further it sits inside the pile, its summit leaning to the sprite's lit side, broken by
  planar fracture faces (chipped stone, crisp edges), the bottom flat on the ground; the D175 facet ramp
  gives every facet one shade of the stone's own palette ramp, lit facets the sprite's highlights, those
  turned away its dark limb (matte, Specular IOR Level 0.15 as D178). The slab and the stones it leans on
  are raised a little (the boost in SEEDS).
- the glint: a small glowing stud (index 123, metallic 1 / roughness 0.9, D126/D173).
- the golden lit faces (pal 20-28) of the stones that are mostly brown keep a facet ramp on the gold
  family (gold_mask): the faces over those pixels are ramped from the gold shades, the rest brown.
- D90/D118 outline shell from a sealed copy of the whole pile, cut per piece without filling.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshr-267.py
     (exports the 12 pieces; with -- --views DIR also writes review renders)
"""

import heapq
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE), str(HERE.parents[2] / "tools")]
import common  # noqa: E402
import lib_newshd_rock as R  # noqa: E402
import sprite_mask as SM  # noqa: E402

ROOT = common.repo_root(__file__)
REF = ROOT / "reference" / "models"

NAME = "assembly-newshr-267"
TAG = "nshr267"
W, H = 72, 112
PX = 1 / 12
ROWS = [["newshr-153", "newshr-155", "newshr-157"],
        ["newshr-191", "newshr-193", "newshr-195"],
        ["newshr-229", "newshr-231", "newshr-233"],
        ["newshr-267", "newshr-269", "newshr-271"]]

# One entry per rock: seed pixels (col, row) it grows from, and a height boost (units).
SEEDS = [
    ([(47, 5), (46, 10)], 0.18),   # tall leaning slab, upper end
    ([(47, 21), (49, 26)], 0.22),  # tall slab, its bright lower face
    ([(31, 10), (32, 7), (29, 9)], 0.0),  # golden rock top left, with its brown back
    ([(38, 17)], 0.05),
    ([(20, 21), (16, 19)], 0.0),   # big rock upper left
    ([(28, 31)], 0.0),
    ([(38, 32), (41, 29)], 0.05),  # golden rock in the middle (with the orange glint)
    ([(52, 44)], 0.05),            # pale rock on the right
    ([(8, 35)], 0.0),              # golden rock on the left edge
    ([(15, 47), (22, 45)], 0.04),  # big flat rock left
    ([(33, 44)], 0.08),            # blue-grey slate
    ([(43, 46)], 0.0),
    ([(40, 53)], 0.0),
    ([(45, 60), (50, 62)], 0.06),  # big pale speckled rock
    ([(30, 54)], 0.0),             # small golden rock
    ([(15, 63)], 0.03),            # golden rock lower left
    ([(9, 61)], 0.0),              # small slate
    ([(26, 62)], 0.0),
    ([(16, 55)], 0.0),
    ([(8, 70)], 0.0),
    ([(8, 77)], -0.03),            # dark rock bottom left
    ([(21, 79)], 0.04),            # slate bottom left
    ([(28, 84)], 0.0),
    ([(29, 95)], 0.0),
    ([(40, 74)], 0.0),
    ([(38, 84)], 0.0),
    ([(48, 74)], 0.0),
    ([(47, 90)], 0.02),            # golden rock bottom right
    ([(40, 94)], -0.03),           # dark rock at the bottom
    ([(18, 86)], 0.0),
]
GLINT = (42, 29)  # the orange glint (index 123) on the middle golden rock
DARK = {1, 2, 160, 161, 66, 80, 112}


def load_grid():
    idx = [[-1] * W for _ in range(H)]
    colors = {}
    for j, names in enumerate(ROWS):
        for i, name in enumerate(names):
            d = json.loads((REF / name / "sprite.json").read_text())
            colors.update(d["colors"])
            for r, line in enumerate(d["frames"][0]["pixels"]):
                for c, v in enumerate(line.split()):
                    idx[28 * j + r][24 * i + c] = int(v)
    m = SM.masks(idx, {int(k): tuple(v) for k, v in colors.items()})
    return idx, colors, m


def segment(idx, keep):
    """Share the pile's pixels out between the rocks' seeds along the dark crevices (a crevice step
    costs 4, a stone step 1); returns each pixel's rock number."""
    INF = float("inf")
    cost = [[INF] * W for _ in range(H)]
    owner = [[-1] * W for _ in range(H)]
    hp = []
    for i, (pts, _) in enumerate(SEEDS):
        for c, r in pts:
            if not keep[r][c]:
                continue
            cost[r][c] = 0
            owner[r][c] = i
            heapq.heappush(hp, (0, c, r, i))
    while hp:
        d, c, r, i = heapq.heappop(hp)
        if d > cost[r][c] or owner[r][c] != i:
            continue
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if not (0 <= nc < W and 0 <= nr < H) or not keep[nr][nc]:
                continue
            step = 4.0 if idx[nr][nc] in DARK else 1.0
            if d + step < cost[nr][nc]:
                cost[nr][nc] = d + step
                owner[nr][nc] = i
                heapq.heappush(hp, (d + step, nc, nr, i))
    return owner


def depth_map(keep):
    """Chebyshev distance (px) to the outside of `keep`."""
    from collections import deque
    dist = [[0 if not keep[r][c] else -1 for c in range(W)] for r in range(H)]
    q = deque((c, r) for r in range(H) for c in range(W) if dist[r][c] == 0)
    # the picture's edge counts as outside too
    while q:
        c, r = q.popleft()
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                nc, nr = c + dc, r + dr
                if 0 <= nc < W and 0 <= nr < H and dist[nr][nc] == -1:
                    dist[nr][nc] = dist[r][c] + 1
                    q.append((nc, nr))
    for r in range(H):
        for c in range(W):
            if dist[r][c] == -1:
                dist[r][c] = 30
    return dist



def X(c):  # pixel edge column -> Blender X (origin at the block's centre)
    return (c - W / 2) * PX


def Y(r):
    return (H / 2 - r) * PX


# --- the sprite ----------------------------------------------------------------------------------------

IDX, COLORS, MASKS = load_grid()
INNER = MASKS["inner"]
SPR = {"name": NAME, "colors": COLORS, "frames": [{"pixels": IDX, "width": W, "height": H}]}


def lum(v):
    r, g, b = COLORS[str(v)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def family(v):
    if 2 <= v <= 13:
        return 0
    if 16 <= v <= 31:
        return 1
    if 160 <= v <= 175:
        return 10
    return None


# --- materials -------------------------------------------------------------------------------------------

MATS = {}


def mat(index, kind="metal"):
    key = (index, kind)
    if key in MATS:
        return MATS[key]
    if kind == "rock":
        m = common.palette_material(SPR, index, TAG, metallic=0.0, roughness=0.9)
        spec_level(m, 0.15)
    elif kind == "glow":
        m = common.palette_material(SPR, index, f"{TAG}_glow", metallic=1.0, roughness=0.9, emission_strength=GLOW[index])
    elif kind == "polish":  # rails, bezel lips: smoother satin metal
        m = common.palette_material(SPR, index, f"{TAG}_pol", metallic=0.55, roughness=0.32)
        spec_level(m, 0.7)
    else:  # satin machine metal
        m = common.palette_material(SPR, index, f"{TAG}_m", metallic=0.4, roughness=0.45)
        spec_level(m, 0.5)
    MATS[key] = m
    return m


GLOW = {123: 1.5}


def spec_level(m, v):
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = v
            break


STONE_BASE = {
    "metallic": 0.0, "roughness": 0.9, "rise": 0.7, "fall": 0.8, "summit_gain": 0.06, "summit_r": 2.4,
    "ridges": [], "valleys": [], "tilt": 0.0, "lumps": 0.02, "grow": 0.4, "smooth": 1, "steps": 48,
    "waist": 0.0, "fine": 1, "fine_depth": (0.03, 0.05), "rim_spalls": 3, "rim_depth": (0.02, 0.035),
    "top_pow": 0.55, "bot_pow": 0.85,
}
CUTS = [(160, 78, 0.10), (20, 74, 0.08), (150, 46, 0.16), (205, 40, 0.13), (110, 52, 0.12),
        (245, 50, 0.12), (10, 44, 0.15), (60, 50, 0.12), (330, 42, 0.14), (290, 56, 0.12)]
RAMP = {"bias": 0.0, "angle": 28.0, "size": 8.0, "sprite": 0.35}  # QA M4: broad, clean faces along the stone's own ramp


class StoneGrid(R.Grid):
    def __init__(self, mask):
        self.w, self.h = W, H
        self.inner = mask


def stones():
    keep = INNER
    own = segment(IDX, keep)
    whole = [[INNER[r][c] for c in range(W)] for r in range(H)]
    dist = depth_map(whole)
    out = []
    for i in range(len(SEEDS)):
        px = [(c, r) for r in range(H) for c in range(W) if own[r][c] == i]
        if len(px) < 5:
            continue
        cu = sum(c + 0.5 for c, _ in px) / len(px)
        cv = sum(r + 0.5 for _, r in px) / len(px)
        vals = sorted((IDX[r][c] for c, r in px if family(IDX[r][c]) is not None), key=lum)
        fams = {}
        for v in vals:
            fams[family(v)] = fams.get(family(v), 0) + 1
        fam = max(fams, key=fams.get)
        fv = [v for v in vals if family(v) == fam]
        k = len(fv) * 15 // 100
        mid_vals = fv[k:len(fv) - k] or fv
        mid = mid_vals[len(mid_vals) // 2]
        thr = sorted(lum(v) for v in fv)[max(0, len(fv) - max(1, len(fv) // 5))]
        lit = [(c + 0.5, r + 0.5) for c, r in px if family(IDX[r][c]) == fam and lum(IDX[r][c]) >= thr]
        bu = sum(p[0] for p in lit) / len(lit) if lit else cu
        bv = sum(p[1] for p in lit) / len(lit) if lit else cv
        d = dist[int(cv)][int(cu)]
        out.append(dict(i=i, px=px, centre=(cu, cv), mid=mid, fam=fam, bright=(bu, bv), depth=d))
    return own, out


def stone_mask(own, i, grow):
    m = [[own[r][c] == i for c in range(W)] for r in range(H)]
    for _ in range(grow):
        m = [[INNER[r][c] and (m[r][c] or any(0 <= r + dr < H and 0 <= c + dc < W and m[r + dr][c + dc]
                                               for dr in (-1, 0, 1) for dc in (-1, 0, 1)))
              for c in range(W)] for r in range(H)]
    return m


def lit_mask(own, i):
    """The stone's pixels without the dark crevice ink between stones (the geometry and the game's ink
    draw those): the facet ramp matches the stone's own shades."""
    m = [[own[r][c] == i and IDX[r][c] not in (1, 160, 161, 66, 80) for c in range(W)] for r in range(H)]
    return m if sum(map(sum, m)) >= 4 else [[own[r][c] == i for c in range(W)] for r in range(H)]


def gold_mask(own, s):
    """The stone's golden pixels (pal 16-31) when the stone itself is ramped in another family: the
    sprite draws their lit faces gold (the top-left nub, the right, left-edge, middle-left and
    bottom-right rocks), so they keep the gold ramp. None when there are too few."""
    if s["fam"] == 1:
        return None
    m = [[own[r][c] == s["i"] and family(IDX[r][c]) == 1 for c in range(W)] for r in range(H)]
    return m if sum(map(sum, m)) >= 4 else None


def on_mask(m, co):
    """Whether a point's top-view pixel (or one of its 4 neighbours, for faces on the rim) is in m."""
    u, v = co.x * 12 + W / 2, H / 2 - co.y * 12
    c, r = int(math.floor(u)), int(math.floor(v))
    if 0 <= r < H and 0 <= c < W and m[r][c]:
        return True
    near = [(c + dc, r + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    hits = sum(1 for cc, rr in near if 0 <= rr < H and 0 <= cc < W and m[rr][cc])
    return hits >= 3


def heap_height(d):
    """The waist height (units) of a stone whose centre lies d px inside the heap."""
    return min(0.55, 0.045 * max(d - 1.5, 0.0))


def build_stone(s, own, coll):
    g = StoneGrid(stone_mask(own, s["i"], 1))
    area = len(s["px"])
    cu, cv = s["centre"]
    bu, bv = s["bright"]
    summit = (cu + 0.35 * (bu - cu), cv + 0.35 * (bv - cv))
    rnd = random.Random(s["i"] * 7 + 3)
    waist = heap_height(s["depth"])
    h_top = min(0.7, 0.10 + 0.032 * math.sqrt(area) + SEEDS[s["i"]][1])
    rot = rnd.uniform(-25, 25)
    spec = dict(STONE_BASE, seed=s["i"] + 1, summit=summit, h_top=h_top, h_bot=waist + 0.1,
                cuts=[((az + rot) % 360, el, dp) for az, el, dp in CUTS if rnd.random() > 0.2])
    sectors = max(12, min(22, int(1.8 * math.sqrt(area))))
    bm, _ = R.rock_body(g, spec, sectors=sectors, rings_top=5, rings_bot=2)
    R.cut_planes(bm, spec["cuts"] + R.fine_cuts(spec))
    R.chip_planes(bm, 6.0)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.translate(bm, vec=(0, 0, waist), verts=bm.verts)
    for v in bm.verts:  # flat on the ground: the underside is a plain closed base
        if v.co.z < 0.0:
            v.co.z = 0.0
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    m = mat(s["mid"], "rock")
    o = common.mesh_object(f"{NAME}_stone{s['i']}", bm, [m], coll, smooth=True)
    st = o.data.attributes.new("stone", "INT", "FACE")
    for dd in st.data:
        dd.value = s["i"]
    return o


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = objs[0]
    o.name = o.data.name = name
    # one slot per material
    uniq = []
    for m in o.data.materials:
        if m not in uniq:
            uniq.append(m)
    remap = [uniq.index(m) for m in o.data.materials]
    fm = [remap[p.material_index] for p in o.data.polygons]
    o.data.materials.clear()
    for m in uniq:
        o.data.materials.append(m)
    for p, k in zip(o.data.polygons, fm):
        p.material_index = k
    return o


def glint(coll, objs):
    """The orange glint: a small faceted glowing stud on the golden rock."""
    gx, gy = GLINT
    zs = [v.co.z for o in objs for v in o.data.vertices
          if abs(v.co.x - X(gx + 0.5)) < 0.1 and abs(v.co.y - Y(gy + 0.5)) < 0.1]
    gz = max(zs) if zs else 0.3
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    for v in bm.verts:
        v.co = (X(gx + 0.5) + v.co.x * 0.28 * PX * 3, Y(gy + 0.5) + v.co.y * 0.28 * PX * 3, gz - 0.01 + max(v.co.z, 0.0) * 0.06)
    m = mat(123, "glow")
    o = common.mesh_object(f"{NAME}_glint", bm, [m], coll, smooth=True)
    st = o.data.attributes.new("stone", "INT", "FACE")
    for dd in st.data:
        dd.value = -1
    return o


def build(coll):
    own, info = stones()
    objs = [build_stone(s, own, coll) for s in info]
    gl = glint(coll, objs)
    obj = join(objs + [gl], NAME)
    st = [d.value for d in obj.data.attributes["stone"].data]
    cen = [p.center.copy() for p in obj.data.polygons]
    for s in info:
        m = mat(s["mid"], "rock")
        slot = list(obj.data.materials).index(m)
        faces = [k for k, v in enumerate(st) if v == s["i"]]
        gold = gold_mask(own, s)
        if gold is not None:  # the sprite's golden rock faces (pal 20-28) keep a gold ramp of their own
            gvals = sorted((IDX[r][c] for c, r in s["px"] if gold[r][c]), key=lum)
            k = len(gvals) * 15 // 100
            gm = (gvals[k:len(gvals) - k] or gvals)[len(gvals[k:len(gvals) - k] or gvals) // 2]
            gmat = mat(gm, "rock")
            if gmat not in list(obj.data.materials):
                obj.data.materials.append(gmat)
            gslot = list(obj.data.materials).index(gmat)
            on_gold = [k for k in faces if on_mask(gold, cen[k])]
            if on_gold:
                for k in on_gold:
                    obj.data.polygons[k].material_index = gslot
                R.facet_ramp(SPR, StoneGrid(gold), obj, dict(STONE_BASE, mid=gm, ramp=RAMP),
                             faces=on_gold, mid=gm, slot=gslot, flat={})
                gs = set(on_gold)
                faces = [k for k in faces if k not in gs]
                print(f"{NAME}: stone {s['i']} gold faces {len(on_gold)} on pal {gm}")
        g = StoneGrid(lit_mask(own, s["i"]))
        R.facet_ramp(SPR, g, obj, dict(STONE_BASE, mid=s["mid"], ramp=RAMP),
                     faces=faces, mid=s["mid"], slot=slot, flat={})
    for m in obj.data.materials:
        if m.name.startswith("pal_") and ("-r" in m.name or m.name.endswith(TAG)):
            spec_level(m, 0.15)
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            bsdf.inputs["Roughness"].default_value = 0.9
            bsdf.inputs["Metallic"].default_value = 0.0
    return obj, info


# --- shell, pieces ----------------------------------------------------------------------------------------

SHELL = dict(R.D90_SHELL, faces=6000, inside=0.008)


def layout():
    out = []
    for j, names in enumerate(ROWS):
        for i, name in enumerate(names):
            out.append((name, 24 * i + 12 - W / 2, 28 * j + 14 - H / 2))
    return out


def split_open(obj, lay, coll):
    out = {}
    for name, cx, cy in lay:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        s = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        out[name] = s
    return out


# --- views ---------------------------------------------------------------------------------------------

def setup_render(px, py, engine="EEVEE"):
    scene = bpy.context.scene
    if engine == "WORKBENCH":
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "FLAT"
        scene.display.shading.color_type = "MATERIAL"
        scene.view_settings.view_transform = "Standard"
    else:
        for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scene.render.engine = e
                break
            except TypeError:
                pass
        try:
            scene.view_settings.view_transform = "Standard"
        except TypeError:
            pass
    scene.render.resolution_x, scene.render.resolution_y = px, py
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def lights():
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.25, 0.25, 0.28, 1)
    bg.inputs[1].default_value = 0.6
    # the art's light comes from the upper left
    for nm, rot, en in (("key", (math.radians(40), 0, math.radians(135)), 3.5),
                        ("fill", (math.radians(60), 0, math.radians(-40)), 0.8)):
        ld = bpy.data.lights.new(nm, "SUN")
        ld.energy = en
        lo = bpy.data.objects.new(nm, ld)
        lo.rotation_euler = rot
        scene.collection.objects.link(lo)


def cam(name, loc, look, ortho=None, lens=50):
    scene = bpy.context.scene
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    data.clip_end = 200
    c = bpy.data.objects.new(name, data)
    scene.collection.objects.link(c)
    c.location = loc
    d = Vector(look) - Vector(loc)
    c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.camera = c
    return c


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def views(out_dir, obj, shell):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH" and o is not obj and o is not shell:
            o.hide_render = True
    shell.hide_render = True
    K = 8
    # 1. top view, palette indices encoded in red (flat), for IoU and region colours
    setup_render(W * K, H * K, "WORKBENCH")
    keep = {m.name: tuple(m.diffuse_color) for m in obj.data.materials}
    for m in obj.data.materials:
        i = int(m.name.split("_")[1])
        s = i / 255
        lin = ((s + 0.055) / 1.055) ** 2.4 if s > 0.04045 else s / 12.92
        m.diffuse_color = (lin, 0, 0, 1)
    c = cam("top", (0, 0, 20), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    render(out_dir / "idx_top.png")
    for m in obj.data.materials:
        m.diffuse_color = keep[m.name]
    # 2. lit views (EEVEE), with the shell drawn as a black inverted hull for the game-camera views
    lights()
    setup_render(W * K, H * K)
    c = cam("top_lit", (0, 0, 20), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    render(out_dir / "top.png")
    D = 22.0
    vs = {
        "game": (0, -D * math.sin(math.radians(20)), D * math.cos(math.radians(20))),
        "steep": (0, -D * math.sin(math.radians(40)), D * math.cos(math.radians(40))),
        "front": (0, -D, 0.25),
        "rear": (0, D, 0.25),
        "side_w": (-D, 0, 0.25),
        "side_e": (D, 0, 0.25),
        "q_sw": (-D * 0.55, -D * 0.6, D * 0.55),
        "q_se": (D * 0.55, -D * 0.6, D * 0.5),
        "q_nw": (-D * 0.5, D * 0.6, D * 0.55),
        "under": (0, -0.5, -D),
    }
    setup_render(900, 900)
    for nm, loc in vs.items():
        cam(nm, loc, (0, 0, 0.2), lens=100)
        render(out_dir / f"{nm}.png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    obj, info = build(coll)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(info)} stones, {tris} triangles, non-manifold edges {open_edges}")
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    shell = common.outline_shell(closed, coll, **SHELL)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    bpy.context.view_layer.update()
    lay = layout()
    pieces = common.split_assembly(obj, lay)
    for q in pieces.values():
        q.data.set_sharp_from_angle(angle=math.radians(35))
        R.set_facet_normals(q)
    shells = split_open(shell, lay, coll)
    for name, _, _ in lay:
        print(f"{name}: {sum(len(p.vertices) - 2 for p in pieces[name].data.polygons)} triangles")
    for name, _, _ in lay:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"])
    for o in list(pieces.values()) + list(shells.values()):
        o.hide_render = True
    if "--views" in argv:
        R.set_facet_normals(obj)
        views(argv[argv.index("--views") + 1], obj, shell)


if __name__ == "__main__":
    main()
