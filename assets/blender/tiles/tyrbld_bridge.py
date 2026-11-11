"""TYRIAN's full-width walkway bridge (map 1-9, layer 2, Background3Over pass: drawn over the player;
pattern 15x3: 121 rock rim / 180 walkway / 141 rocky underside; rows 199-201, 223-225, 236-238),
hard-surface (D65, D141).

What it is (tile 180, read row by row): a riveted metal walkway girder running off both map edges.
Along its north edge a heavy curb plate (rows 0-1, bright 9-11) in 17 px plates, a recessed joint
block with one bolt between them (x 12-18 of each tile, darker 4-8); its south slope (row 2) drops
into a dark slot (row 3, index 2) where the curb meets the deck. The deck (rows 4-24, index 5)
carries a raised Greek-key meander relief (the art's 4/6 lines: lit and shaded edges of raised
bars, painted in the deck's own 5). Along the south edge a round-topped foot rail (rows 25-27,
bright 9-12 with a sheen line, row 26), in 22 px lengths with a recessed collar at x 15-17.

Built here as chamfered sections: a dark core girder, the slot floor, the deck plate, the curb plates
and rail lengths as lofts (beam(): one cross-section, chamfered at both ends, open where the run meets
the map edge), joint blocks and collars, bolts; the meander as one pixel-exact orthogonal relief
(the key pattern is orthogonal) with a chamfer all round each bar (inset_region), including round the
deck patches it encloses. The rim (121) and underside (141) are the island's own rock
(Structure.rock: plain, unbaked, the per-tile relief with the hanging underside face, D84), so they
match the rock round them. Texture: the model's own AO/roughness bake only. No outline shell (D141).

    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/tyrbld_bridge.py
    blender --background --factory-startup --python assets/blender/tiles/tyrbld_bridge.py -- [--no-bake] [--sheet <png>] [--preview <dir>]
"""

import math
import sys
from pathlib import Path

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender" / "tiles"))
sys.path.insert(0, str(WT / "assets" / "blender"))
import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402

OUT = Path(__file__).resolve().parent

# --- Layout (pattern px, 1x; walkway row = py 28..56) ----------------------------------------------
Y0, Y1 = 28.0, 56.0
CURB_Y = (28.0, 30.8)          # curb plate incl. its south slope (rows 0-2)
SLOT_Y = (30.6, 32.1)          # the dark slot under the curb (row 3)
DECK_Y = (32.0, 53.2)          # meander deck (rows 4-24)
RAIL_Y = (53.0, 56.0)          # foot rail (rows 25-27)
MEANDER_ROWS = (32, 53)        # rows holding the key relief (tile rows 4-24)
CURB_JOINT = (11.5, 18.5)      # per tile, x: the darker joint between curb plates
CURB_BOLT_X = 16.5
RAIL_JOINT = (15.0, 17.0)      # per tile, x: the dark collar between rail lengths

# --- Heights (layer 2: z = 0 the islands' rock top; over: <= 0.38) ---------------------------------
CORE_BOT = -0.30
DECK_Z = tb.L2_DECK            # 0.06
GROOVE_Z = DECK_Z - 0.018
LIP_Z = DECK_Z + 0.016
SLOT_Z = 0.022
CURB_TOP = 0.16
JOINT_TOP = 0.118
RAIL_TOP = 0.13

# --- Palette (the art's trimmed medians; measure_colours() prints them) ----------------------------
P_CORE = 4
P_SLOT = 2
P_DECK = 5
P_GROOVE = 4
P_LIP = 6
P_CURB = 9
P_CURB_SLOPE = 4
P_CURB_JOINT = 6
P_BOLT = 8
P_RAIL = 9
P_COLLAR = 5


def beam(s, profile, x0, x1, mat, end=0.7, shrink=0.82, open0=False, open1=False, cap_mat=None, mats=None):
    """A loft along X of one cross-section `profile` [(py, z), ...] (a closed convex loop, pattern px
    and units) from x0 to x1 (pattern px), its ends chamfered: the end ring is the section shrunk
    toward its centroid by `shrink`, `end` px in. An `open` end (the map's edge) is cut square."""
    cy = sum(p[0] for p in profile) / len(profile)
    cz = sum(p[1] for p in profile) / len(profile)
    small = [(cy + (py - cy) * shrink, cz + (z - cz) * shrink) for py, z in profile]
    stations = []
    stations.append((x0, profile if open0 else small))
    if not open0:
        stations.append((x0 + end, profile))
    if not open1:
        stations.append((x1 - end, profile))
    stations.append((x1, profile if open1 else small))
    bm = bmesh.new()
    rings = [[bm.verts.new((s.x(x), s.y(py), z)) for py, z in sec] for x, sec in stations]
    n = len(profile)
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat if mats is None else mats.get(i, mat)
    cm = mat if cap_mat is None else cap_mat
    bm.faces.new(list(reversed(rings[0]))).material_index = cm
    bm.faces.new(rings[-1]).material_index = cm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def meander_masks(s):
    """The deck field's relief (bool, pattern px), pixel-exact: the key pattern is orthogonal, so its
    outline is the art's. The art paints each key line as a dark 4 line (a cut panel groove) beside
    a light 6 line (the raised lip lit along its edge) on the deck's 5: grooves sink, lips rise."""
    g = s.grid
    H, W = g.shape
    rows = np.zeros((H, W), bool)
    rows[MEANDER_ROWS[0]:MEANDER_ROWS[1]] = True
    groove = rows & (g >= 0) & (g <= 4)
    lip = rows & (g >= 6)
    land = rows & (g >= 5)
    return land, lip, groove


def relief(s, mask, z0, z1, mat, chamfer_px=0.3, drop=0.008):
    """A pixel-exact slab over `mask` from z0 to z1, every top edge (round holes too) chamfered."""
    bm = bmesh.new()
    lt.mask_slab(bm, mask, lt.Frame(s.pattern, 1), z0, z1 - drop, mat, mat, mat)
    lt.dissolve_coplanar(bm)
    tops = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.inset_region(bm, faces=tops, thickness=chamfer_px * lt.PX, depth=drop, use_even_offset=True)
    lt.dissolve_coplanar(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def build_model(s):
    W = s.W
    ncol = W // lt.TILE_W
    m_core = s.m(P_CORE, roughness=0.7, metallic=0.2)
    m_slot = s.m(P_SLOT, roughness=0.8)
    m_deck = s.m(P_DECK, roughness=0.55, metallic=0.0)       # D101: the deck stays non-metallic
    m_groove = s.m(P_GROOVE, roughness=0.6)
    m_lip = s.m(P_LIP, roughness=0.5, metallic=0.0)
    m_curb = s.m(P_CURB, roughness=0.36, metallic=0.3)
    m_slope = s.m(P_CURB_SLOPE, roughness=0.45, metallic=0.4)
    m_cjoint = s.m(P_CURB_JOINT, roughness=0.5, metallic=0.35)
    m_bolt = s.m(P_BOLT, roughness=0.35, metallic=0.55)
    m_rail = s.m(P_RAIL, roughness=0.32, metallic=0.3)
    m_collar = s.m(P_COLLAR, roughness=0.5, metallic=0.35)

    # 1. The core girder under everything, the slot floor and the deck plate.
    s.slab(rect(0, Y0, W, Y1), CORE_BOT, 0.0, m_core, chamfer_px=0)
    s.slab(rect(0, SLOT_Y[0], W, SLOT_Y[1]), -0.02, SLOT_Z, m_slot, chamfer_px=0)
    s.slab(rect(0, DECK_Y[0], W, DECK_Y[1]), -0.02, GROOVE_Z, m_groove, chamfer_px=0)

    # 2. The key relief: the deck plate's top is the grooves' floor; the lands rise to DECK_Z with a
    #    chamfer round every groove, the lips a step higher.
    land, lip, groove = meander_masks(s)
    relief(s, land, GROOVE_Z - 0.01, DECK_Z, m_deck, chamfer_px=0.3, drop=0.006)
    relief(s, lip, DECK_Z - 0.01, LIP_Z, m_lip, chamfer_px=0.3, drop=0.006)
    mm = (land, lip, groove)

    # 3. Curb: plates between joint blocks. Section: a square north face against the rim rock, a
    #    flat top (rows 0-1), the south slope (row 2) down into the slot.
    curb = [(Y0, -0.01), (Y0, CURB_TOP - 0.018), (Y0 + 0.45, CURB_TOP), (29.7, CURB_TOP),
            (CURB_Y[1], CURB_TOP - 0.058), (CURB_Y[1], -0.01)]
    joint = [(Y0, -0.01), (Y0, JOINT_TOP - 0.012), (Y0 + 0.35, JOINT_TOP), (29.5, JOINT_TOP),
             (CURB_Y[1] - 0.15, JOINT_TOP - 0.04), (CURB_Y[1] - 0.15, -0.01)]
    cuts = [0.0]
    for c in range(ncol):
        cuts += [c * 24 + CURB_JOINT[0], c * 24 + CURB_JOINT[1]]
    cuts.append(float(W))
    for i in range(0, len(cuts) - 1, 2):
        a, b = cuts[i], cuts[i + 1]
        beam(s, curb, a, b, m_curb, end=0.6, shrink=0.85, open0=a <= 0, open1=b >= W, mats={3: m_slope})
    for c in range(ncol):
        a, b = c * 24 + CURB_JOINT[0], c * 24 + CURB_JOINT[1]
        beam(s, joint, a - 0.2, b + 0.2, m_cjoint, end=0.4, shrink=0.9)
        s.bolts([(c * 24 + CURB_BOLT_X, 29.2)], JOINT_TOP, r_px=0.9, height=0.022, mat=m_bolt)
        # rivets near each plate's ends (the plates' bright spots are sheen: only the fasteners are geometry)
        s.bolts([(c * 24 + CURB_JOINT[0] - 1.6, 28.9), (c * 24 + CURB_JOINT[1] + 1.6, 28.9)], CURB_TOP,
                r_px=0.55, height=0.012, mat=m_bolt)

    # 4. Foot rail: round-topped lengths between recessed collars. Section: a low inner flank on the
    #    deck, the round crest at row 26, a steeper outer (south) face down to the rock.
    rail = [(RAIL_Y[0], -0.01), (RAIL_Y[0], 0.075), (53.45, 0.105), (54.1, 0.124), (54.7, RAIL_TOP),
            (55.3, 0.124), (55.75, 0.10), (Y1, 0.065), (Y1, -0.01)]
    collar = [(53.25, -0.01), (53.25, 0.07), (53.7, 0.098), (54.7, 0.11), (55.6, 0.095), (55.85, 0.06), (55.85, -0.01)]
    cuts = [0.0]
    for c in range(ncol):
        cuts += [c * 24 + RAIL_JOINT[0], c * 24 + RAIL_JOINT[1]]
    cuts.append(float(W))
    for i in range(0, len(cuts) - 1, 2):
        a, b = cuts[i], cuts[i + 1]
        beam(s, rail, a, b, m_rail, end=0.55, shrink=0.86, open0=a <= 0, open1=b >= W)
    for c in range(ncol):
        a, b = c * 24 + RAIL_JOINT[0], c * 24 + RAIL_JOINT[1]
        beam(s, collar, a - 0.3, b + 0.3, m_collar, end=0.25, shrink=0.95)
    return mm


def measure_colours(s, mm):
    """The art's trimmed median index per region (darkest and brightest 15% dropped as lighting)
    against the region's material index."""
    g = s.grid
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    tx = xx % 24
    band = lambda a, b: (yy >= a) & (yy < b)  # noqa: E731
    cj = (tx >= 12) & (tx < 18)
    rj = (tx >= 15) & (tx < 17)
    regions = [
        ("curb plate", band(28, 30) & ~cj, P_CURB),
        ("curb joint", band(28, 30) & cj, P_CURB_JOINT),
        ("curb slope", band(30, 31), P_CURB_SLOPE),
        ("slot", band(31, 32), P_SLOT),
        ("deck lands", mm[0] & ~mm[1], P_DECK),
        ("key lips", mm[1], P_LIP),
        ("key grooves", mm[2], P_GROOVE),
        ("rail", band(53, 56) & ~rj, P_RAIL),
        ("rail collar", band(53, 56) & rj, P_COLLAR),
    ]
    out = []
    for name, sel, pal in regions:
        v = np.sort(g[sel & (g >= 0)].ravel())
        k = int(len(v) * 0.15)
        core = v[k:len(v) - k] if len(v) - 2 * k > 4 else v
        med = int(np.median(core))
        out.append((name, pal, med))
        print(f"colour {name:14s} pal {pal:3d}  art {med:3d}  ({len(v)} px)")
    return out


# --- Sheet -----------------------------------------------------------------------------------------

def _engine(scene):
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = e
            return e
        except TypeError:
            continue


def render_sheet(objects, s, px=560):
    """Renders of the middle four tiles beside the art: art | top | game camera | 3/4 high, and
    front (south, low) | side (west end) | rear (north) | underside. Lit by a sun from the upper left
    and a dim sky, in the baked materials."""
    import tempfile
    scene = bpy.context.scene
    eng = _engine(scene)
    if eng == "CYCLES":
        scene.cycles.samples = 24
    scene.render.resolution_x = px
    scene.render.resolution_y = int(px * 0.75)
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("sheet")
    scene.world = world
    world.use_nodes = True
    bgn = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs[0].default_value = (0.32, 0.34, 0.4, 1)
    bgn.inputs[1].default_value = 0.7
    sun_d = bpy.data.lights.new("sheet_sun", "SUN")
    sun_d.energy = 3.2
    sun = bpy.data.objects.new("sheet_sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(38), math.radians(-22), math.radians(-30))
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass

    def cam(name, loc, look, ortho=None, lens=50):
        d = bpy.data.cameras.new(name)
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        o = bpy.data.objects.new(name, d)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return o

    view = bpy.data.materials.new("sheet_rock")
    view.diffuse_color = (0.22, 0.2, 0.18, 1)
    bsdf = next(n for n in view.node_tree.nodes if n.type == "BSDF_PRINCIPLED") if view.node_tree else None
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.2, 0.18, 0.16, 1)
        bsdf.inputs["Roughness"].default_value = 0.9
    for o in objects:
        if o.type == "MESH":
            for slot in o.material_slots:
                if slot.material is not None and slot.material.get("tyrian_plain"):
                    slot.material = view

    yc = s.y(42)
    views = [
        cam("top", (0, yc, 10), (0, yc + 1e-4, 0), ortho=8.6),
        cam("game", (0, yc - 7.5, 9.5), (0, yc + 0.6, 0), lens=42),
        cam("q34", (5.5, yc - 5.0, 4.2), (0, yc, -0.1), lens=40),
        cam("front", (0, yc - 9.0, 0.9), (0, yc, -0.15), lens=45),
        cam("side", (-17.0, s.y(42) - 1.2, 0.9), (-14.4, yc, -0.1), lens=35),
        cam("rear", (0, yc + 9.0, 1.4), (0, yc, 0.0), lens=45),
        cam("under", (1.0, yc - 4.0, -6.0), (0, yc, -0.3), lens=40),
    ]
    tmp = Path(tempfile.mkdtemp())
    panels = []
    for v in views:
        scene.camera = v
        p = tmp / f"{v.name}.png"
        scene.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(str(p))
        panels.append(np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)[::-1])
        bpy.data.images.remove(img)
    # The art: cols 5-8 (x 120..216), the three rows, at the top view's scale.
    g = s.grid
    crop = g[:, 120 - 3:216 + 3]
    h, w = crop.shape
    art = np.zeros((h, w, 4), np.float32)
    for y in range(h):
        for x in range(w):
            if crop[y, x] >= 0:
                r, gg, b = s.ts.rgb(crop[y, x])
                art[y, x] = (r / 255, gg / 255, b / 255, 1)
    H_, W_ = panels[0].shape[:2]
    scale = W_ / (8.6 * 12)  # top view: ortho 8.6 units across
    th, tw = int(h * scale), int(w * scale)
    ys = (np.arange(th) * h / th).astype(int)
    xs = (np.arange(tw) * w / tw).astype(int)
    big = art[ys][:, xs]
    ap = np.zeros_like(panels[0])
    ap[..., 3] = 1
    oy, ox = max(0, (th - H_) // 2), max(0, (tw - W_) // 2)
    big = big[oy:oy + H_, ox:ox + W_]
    y0, x0 = (H_ - big.shape[0]) // 2, (W_ - big.shape[1]) // 2
    ap[y0:y0 + big.shape[0], x0:x0 + big.shape[1]] = big
    row1 = np.concatenate([ap] + panels[0:3], axis=1)
    row2 = np.concatenate(panels[3:7] + [np.zeros_like(ap)], axis=1)[:, :row1.shape[1]]
    sheet = np.concatenate([row1, row2], axis=0)
    return sheet


def save_png(arr, path):
    out = bpy.data.images.new("sheet_out", arr.shape[1], arr.shape[0], alpha=True)
    out.pixels[:] = arr[::-1].ravel()
    out.filepath_raw = str(path)
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)


def share_rock_images(s):
    """Structure.rock gives every cell its own material (its tag `tyrian_rock_cell`, so the game picks
    that cell's neighbour bands, D84), and each material its own copy of the tile's images: 28 cells
    of the same two tiles wrote 56 identical images (2 MB). Point every cell's texture nodes at one
    image per identical (tile, map) pair; the glTF exporter then writes each image once. The game
    only reads these maps (rockMaterial.ts), so sharing them is safe. (A lib_tiles follow-up.)"""
    import hashlib
    import re
    first, dropped = {}, 0
    for m in s.pal.materials:
        if m is None or m.get("tyrian_rock_cell") is None or not m.node_tree:
            continue
        for node in m.node_tree.nodes:
            if node.type != "TEX_IMAGE" or node.image is None:
                continue
            img = node.image
            base = re.sub(r"_\d+_\d+(-[\w]+)$", r"\1", img.name)
            digest = hashlib.sha1(np.asarray(img.pixels[:], dtype=np.float32).tobytes()).hexdigest()
            key = (base, digest, img.size[0], img.size[1])
            keep = first.setdefault(key, img)
            if keep is not img:
                node.image = keep
                dropped += 1
    for img in list(bpy.data.images):
        if img.users == 0:
            bpy.data.images.remove(img)
    print(f"rock images: {len(first)} kept, {dropped} shared")


def build(bake=True, preview=None, sheet=False):
    lb.clear_scene()
    s = tb.Structure("bridge")
    walk = s.cells_mask(tb.WALK) & s.footprint   # the art's walkway row: the model's own parts
    mm = build_model(s)
    # The island's rock: the rim and the underside rows, the per-tile relief (plain).
    rock_cells = [(r, c) for r in (0, 2) for c in range(15) if s.pattern[r][c] >= 0]
    s.rock(cells=rock_cells)
    share_rock_images(s)
    objects = s.objects()
    s.check(objects)
    iou = s.top_iou(objects, walk)
    measure_colours(s, mm)
    if bake:
        objects = s.bake_model(objects, size=2048, ao=(0.02, 0.12))
    tris = plain = 0
    for o in objects:
        if o.type != "MESH":
            continue
        pl = [bool(m and m.get("tyrian_plain")) for m in o.data.materials]
        for p in o.data.polygons:
            if pl and pl[p.material_index]:
                plain += len(p.vertices) - 2
            else:
                tris += len(p.vertices) - 2
    if preview:
        lt.preview(s.ts, objects, s.pattern, Path(preview) / "shapesz-tyrbld-bridge.png", view_px=480)
    out = s.export(objects, baked=bake)
    print(f"bridge: IoU {iou:.4f}, {tris} triangles hard, {plain} plain, {Path(out).stat().st_size / 1e6:.2f} MB -> {out}")
    if sheet:
        arr = render_sheet(objects, s)
        save_png(arr, Path(sheet))
        print(f"sheet {sheet}")


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
pv = lt.preview_arg()  # a folder; build-models.sh -p passes <dir>/<script>.png
sh = argv[argv.index("--sheet") + 1] if "--sheet" in argv else None
build(bake="--no-bake" not in argv, preview=pv, sheet=sh)
