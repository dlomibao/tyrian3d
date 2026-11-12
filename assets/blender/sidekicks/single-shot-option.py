"""Single Shot Option (sidekick 1, tyrian.shp#8 frames 168/187/206), design B: a hard-surface recoiling
gun pod, its top view on the inner edge of the sprite's ink border (D74), built to the D50-D53/D65
standard (lofted chamfered sections, pchip stations, modelled panel grooves, outline shell D51).

What it is (D120/D122): a small mounted weapon pod flying beside the player's ship, muzzle up the
screen. Reading of the sprite (reference/models/sidekick-single-shot-option, 12x14, palette 5):
- rows 0-6 (cols 3-8) are the SLIDE: muzzle ring (row 0, pal 8), a thin barrel neck (row 1, pal 6,
  inner mask 2 px), the bright breech collar (rows 2-3, pal 11), a dark seam (row 4), the slide drum
  (rows 4-7, pal 5) with a raised band that catches the sheen (row 5, the 15/10 pixels).
  On 187 / 206 all of rows 0-6 move 1 / 2 px down: the gun recoils into the housing.
- rows 8-11 are the fixed HOUSING (pal 5): a dark mouth lip (pal 3) where the slide enters (the dark row 8 is the
  shadowed gap), a panel groove, a domed tail cap (pal 6, trim ring 7) with a small exhaust nozzle. Row 11's dark
  pixels are the sprite's ink border (tools/sprite_mask.py), not ports: the tail is round.
- cols 1-2 / 9-10, rows 4-9: two fixed recoil-buffer cylinders (pal 8), lit down their outer edge,
  clamped and webbed to the housing, joined under the slide by a cradle tray (the slide rides in it).
- 187: a 2 px muzzle flash (gold left, red right); 206: a 3 px wide burst (red, yellow, orange) and an
  amber tip, off centre exactly as drawn.
Bright spots are sheen; the outline ring and shading are lighting (rubric). Underside: closed, plain.

Authoring units: sprite px; x = column edge - 6 (east +), y = row edge (aft +), z up. Blender:
X = x/12, Y = (7 - y)/12, Z = z/12.

    blender --background --python assets/blender/sidekicks/single-shot-option.py [-- --measure DIR]

Writes three models, one per frame (single-shot-option, -f2, -f3), each a body, its outline shell
and (on 187/206) a muzzle flash. Design B (recoiling slide in a fixed housing) with design A's
machined detail grafted on.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
sys.path.insert(0, str(ROOT / "tools"))
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, hull  # noqa: E402

NAME = "single-shot-option"
REF = f"sidekick-{NAME}"
PX = 1 / 12
# (frame, recoil px, model suffix)
FRAMES = [(168, 0, ""), (187, 1, "-f2"), (206, 2, "-f3")]

ZC = 3.0     # drum axis height
ZS = 2.25    # sponson axis height
XS = 3.85    # sponson axis |x|
RS = 1.17    # sponson radius

# Material slots -> palette index (sprite medians per region, lighting trimmed; see notes).
SLOTS = [
    ("BORE", 254, 0.0, 0.85),
    ("MUZZLE", 8, 0.35, 0.38),
    ("BARREL", 6, 0.35, 0.42),
    ("BREECH", 11, 0.35, 0.36),
    ("SEAM", 3, 0.3, 0.55),
    ("SLIDE", 5, 0.35, 0.42),
    ("BAND", 7, 0.35, 0.36),
    ("HOUSING", 5, 0.35, 0.45),
    ("LIP", 4, 0.35, 0.45),
    ("GROOVE", 2, 0.3, 0.6),
    ("TAIL", 4, 0.35, 0.45),
    ("SPONSON", 8, 0.35, 0.4),
    ("CAP", 9, 0.35, 0.36),
    ("CLAMP", 4, 0.35, 0.45),
    ("BOLT", 9, 0.4, 0.34),
]
S = {n: i for i, (n, *_) in enumerate(SLOTS)}
FLASH = [("F119", 119, 1.2), ("F121", 121, 1.2), ("F122", 122, 1.3), ("F123", 123, 1.3), ("F124", 124, 1.25)]
for k, (n, *_) in enumerate(FLASH):
    S[n] = len(SLOTS) + k


def materials(sprite):
    mats = [common.palette_material(sprite, i, NAME, metallic=m, roughness=r) for _, i, m, r in SLOTS]
    mats += [common.palette_material(sprite, i, NAME, metallic=0.0, roughness=0.6, emission_strength=e)
             for _, i, e in FLASH]
    return mats


# --- geometry helpers ---------------------------------------------------------------------------

def lathe(P, cx, cz, prof, seg, ez=1.0, smooth=False, phase=0.0):
    """Revolve a profile round an axis along y at (cx, cz). prof: [(y, r, mat)] from the front pole
    to the rear pole (r may be 0 at either end); mat colours the band to the next station. Paired
    stations make chamfers and steps; smooth=True resamples them with pchip (no overshoot)."""
    if smooth:
        pts = [p for k, p in enumerate(prof) if k + 1 == len(prof) or prof[k + 1][0] > p[0] + 1e-6]
        pts = [p for k, p in enumerate(pts) if k == 0 or p[0] > pts[k - 1][0] + 1e-6]
        f = T.pchip([p[0] for p in pts], [p[1] for p in pts])
        out = []
        for (y0, r0, m0), (y1, _, _) in zip(prof, prof[1:]):
            n = max(1, int(round((y1 - y0) / 0.15)))
            out += [(y0 + (y1 - y0) * k / n, r0 if k == 0 else f(y0 + (y1 - y0) * k / n), m0) for k in range(n)]
        out.append(prof[-1])
        prof = out
    rings = []
    for y, r, m in prof:
        if r <= 1e-5:
            rings.append([P.v((cx, y, cz))])
        else:
            rings.append([P.v((cx + r * math.cos(phase + 2 * math.pi * i / seg), y,
                               cz + ez * r * math.sin(phase + 2 * math.pi * i / seg))) for i in range(seg)])
    for k in range(len(prof) - 1):
        (y0, r0, m), (y1, r1, _) = prof[k], prof[k + 1]
        a, b = rings[k], rings[k + 1]
        ny, nr = -(r1 - r0), (y1 - y0)
        for i in range(seg):
            j = (i + 1) % seg
            t = phase + 2 * math.pi * (i + 0.5) / seg
            out = (nr * math.cos(t), ny, nr * math.sin(t) * ez)
            if len(a) == 1:
                P.f([a[0], b[i], b[j]], m, out=out)
            elif len(b) == 1:
                P.f([a[i], b[0], a[j]], m, out=out)
            else:
                P.f([a[i], a[j], b[j], b[i]], m, out=out)
    if len(rings[0]) > 1:
        P.f(rings[0], prof[0][2], out=(0, -1, 0))
    if len(rings[-1]) > 1:
        P.f(rings[-1], prof[-2][2], out=(0, 1, 0))


def bolt(P, x, y, z, nx, ny, nz, r=0.22, h=0.14, mat=None):
    """A small hex bolt head standing on a surface with normal n."""
    n = Vector((nx, ny, nz)).normalized()
    u = n.orthogonal().normalized()
    v = n.cross(u)
    base = Vector((x, y, z)) - n * 0.06
    pts = []
    for k in range(6):
        t = 2 * math.pi * k / 6
        d = u * math.cos(t) + v * math.sin(t)
        pts.append(tuple(base + d * r))
        pts.append(tuple(base + n * h + d * r * 0.8))
    hull(P, pts, S["BOLT"] if mat is None else mat)


def finish(P, mats, coll):
    P.orient()
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 7 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(P.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(P.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(P.smooth_angle))
    return obj


# --- the pod --------------------------------------------------------------------------------------

def slide(P, s):
    """Everything that recoils: muzzle, barrel, breech collar, slide drum (rows shift by s)."""
    def sh(prof):
        return [(y + s, r, m) for y, r, m in prof]
    B, MZ, BR, BC, SE, SL, BD = (S[k] for k in ("BORE", "MUZZLE", "BARREL", "BREECH", "SEAM", "SLIDE", "BAND"))
    lathe(P, 0, ZC, sh([
        (0.42, 0.0, B), (0.42, 0.82, B), (0.22, 0.82, MZ),          # black bore, its floor recessed
        (0.22, 1.35, MZ), (0.06, 1.35, MZ),                          # crown recess in the muzzle face
        (0.06, 1.62, MZ), (0.24, 1.96, MZ), (0.40, 1.96, MZ),        # chamfered muzzle face
        (0.45, 1.80, MZ), (0.55, 1.80, MZ), (0.60, 1.96, MZ),        # machined groove round the brake
        (0.78, 1.96, MZ), (0.95, 1.60, MZ), (0.95, 1.02, BR),        # back chamfer onto the barrel
        (1.30, 1.02, BR), (1.34, 0.86, SE), (1.52, 0.86, SE), (1.56, 1.02, BR),   # cut groove on the neck
        (2.00, 1.02, BC), (2.00, 1.72, BC),                          # collar front face
        (2.34, 2.96, BC), (2.92, 2.96, BC),                          # chamfer, collar
        (2.97, 2.80, BC), (3.10, 2.80, BC), (3.15, 2.96, BC),        # panel groove round the collar
        (3.74, 2.96, BC), (3.90, 2.70, SE),                          # back chamfer
        (3.90, 2.56, SE), (4.32, 2.56, SL),                          # dark seam
        (4.40, 2.95, SL), (4.98, 2.95, BD),                          # slide drum
        (5.08, 3.08, BD), (5.78, 3.08, SL), (5.88, 2.95, SL),        # raised band (row 5's sheen)
        (8.60, 2.95, SL), (9.0, 1.9, SL), (9.0, 0.0, SL),            # runs on inside the housing
    ]), 20)
    # Four bolts on the collar's front chamfer, round the barrel (the tilted camera sees them).
    for a in (45, 135, 225, 315):
        t = math.radians(a)
        rr = 2.38
        nr, ny = 0.96, -0.29
        bolt(P, rr * math.cos(t), 2.18 + s, ZC + rr * math.sin(t), nr * math.cos(t), ny, nr * math.sin(t), r=0.2, h=0.12)


def slide_detail(P, s):
    """Machined detail on the breech collar and the band (design A's grafts, kept inside B's outline)."""
    CL, SE, BD = S["CLAMP"], S["SEAM"], S["BAND"]
    # Two cap-screws on top of the collar, and a recessed ejection port on its right flank.
    for sx in (-1, 1):
        x = sx * 1.5
        z = math.sqrt(2.96 ** 2 - x * x)
        bolt(P, x, 2.62 + s, ZC + z, x / 2.96, 0, z / 2.96, r=0.24, h=0.14)
    hull(P, cbox(2.82, 3.03, 2.45 + s, 3.05 + s, ZC - 0.55, ZC + 0.55, 0.1), SE)
    hull(P, cbox(2.95, 3.07, 2.38 + s, 3.12 + s, ZC - 0.68, ZC - 0.5, 0.04), CL)
    hull(P, cbox(2.95, 3.07, 2.38 + s, 3.12 + s, ZC + 0.5, ZC + 0.68, 0.04), CL)
    # The sight blade on the raised band at the centreline (row 5's bright centre pixel).
    hull(P, cbox(-0.2, 0.2, 5.15 + s, 5.7 + s, ZC + 3.0, ZC + 3.5, 0.08), BD)
    hull(P, cbox(-0.45, 0.45, 5.1 + s, 5.75 + s, ZC + 2.98, ZC + 3.14, 0.05), BD)


def tail_detail(P):
    """Vents on the tail dome and two mounting lugs on the housing top (design A's grafts)."""
    G, CL = S["GROOVE"], S["CLAMP"]
    for a in (0, 90, 180, 270):
        t = math.radians(a)
        rr, yy = 1.62, 11.38
        bolt(P, rr * math.cos(t), yy, ZC + rr * math.sin(t), 0.55 * math.cos(t), 0.7, 0.55 * math.sin(t), r=0.2, h=0.07, mat=G)
    for sx in (-1, 1):
        hull(P, cbox(sx * 1.0 - 0.3, sx * 1.0 + 0.3, 9.9, 10.4, ZC + 2.9, ZC + 3.3, 0.1), CL)


def housing(P):
    H, LP, G, TL, B, M = (S[k] for k in ("HOUSING", "LIP", "GROOVE", "TAIL", "BORE", "SEAM"))
    lathe(P, 0, ZC, [
        (8.15, 0.0, M), (8.15, 3.06, M), (8.28, 3.22, M), (8.72, 3.22, M), (8.84, 3.08, H),       # mouth lip (row 8's dark band)
        (9.40, 3.08, G), (9.46, 2.90, G), (9.62, 2.90, G), (9.68, 3.08, H),                       # panel groove
        (10.48, 3.08, TL), (10.56, 3.0, TL),                                                     # seam onto the tail cap
    ], 22)
    # The domed tail cap (pchip), ending in a small flat with an exhaust nozzle.
    lathe(P, 0, ZC, [(10.55, 2.92, TL), (10.95, 2.48, TL), (11.25, 1.90, TL), (11.52, 1.28, TL),
                     (11.72, 0.70, TL), (11.72, 0.0, TL)], 22, smooth=True)
    # A machined trim ring round the dome and four bolts round the exhaust: what the game camera,
    # looking up the screen, sees first.
    lathe(P, 0, ZC, [(10.98, 0.0, S["BAND"]), (10.98, 2.50, S["BAND"]), (11.04, 2.56, S["BAND"]), (11.16, 2.38, S["BAND"]), (11.16, 0.0, S["BAND"])], 22)
    for a in (45, 135, 225, 315):
        t = math.radians(a)
        rr, yy = 1.12, 11.58
        bolt(P, rr * math.cos(t), yy, ZC + rr * math.sin(t), 0.62 * math.cos(t), 0.78, 0.62 * math.sin(t), r=0.16, h=0.1)
    lathe(P, 0, ZC, [(11.6, 0.0, LP), (11.6, 0.62, LP), (11.86, 0.56, LP), (11.86, 0.34, B),
                     (11.70, 0.34, B), (11.70, 0.0, B)], 16)


def sponsons(P):
    SP, CP, CL = S["SPONSON"], S["CAP"], S["CLAMP"]
    for sx in (-1, 1):
        cx = sx * XS
        lathe(P, cx, ZS, [
            (4.40, 0.0, CP), (4.40, 0.30, CP), (4.50, 0.46, CP), (4.66, 0.74, CP), (4.86, 0.96, CP),   # buffer cap
            (4.92, 0.98, SP), (4.98, RS, SP), (8.58, RS, CP),
            (8.62, 1.0, CP), (8.92, 0.88, CP), (9.25, 0.62, CP), (9.48, 0.30, CP), (9.52, 0.0, CP),   # tapered tail
        ], 14)
        # Clamp bands (bolted on the outboard side).
        for y0 in (5.45, 7.55):
            lathe(P, cx, ZS, [(y0, 0.0, CL), (y0, RS + 0.12, CL), (y0 + 0.05, RS + 0.16, CL),
                              (y0 + 0.45, RS + 0.16, CL), (y0 + 0.5, RS + 0.12, CL), (y0 + 0.5, 0.0, CL)], 14)
            bolt(P, cx + sx * (RS + 0.14), y0 + 0.25, ZS, sx, 0, 0, r=0.17, h=0.12)
        # Web from the sponson to the housing (under the sponson axis), and a mount strut forward.
        x0, x1 = sorted((sx * 2.55, sx * 3.55))
        hull(P, cbox(x0, x1, 8.1, 9.85, 0.7, 2.35, 0.2), CL)
        hull(P, cbox(x0, x1, 5.1, 5.9, 0.75, 1.7, 0.15), CL)
    # The cradle tray under the slide, joining the two buffers (the slide rides in it).
    hull(P, cbox(-3.4, 3.4, 4.9, 8.3, 0.35, 1.25, 0.22), S["CLAMP"])


def flash(P, s):
    """The muzzle flash in front of the recoiled barrel, off centre as drawn."""
    front = s + 0.06
    z = ZC
    if s == 1:  # row 0: gold (col 5) | red (col 6)
        lathe(P, -0.32, z, [(front - 1.0, 0.0, S["F123"]), (front - 0.85, 0.55, S["F123"]), (front - 0.6, 0.85, S["F123"]),
                            (front - 0.3, 0.95, S["F123"]), (front, 0.8, S["F123"]), (front, 0.0, S["F123"])], 12, smooth=True)
        lathe(P, 0.42, z - 0.15, [(front - 0.95, 0.0, S["F119"]), (front - 0.75, 0.55, S["F119"]), (front - 0.4, 0.68, S["F119"]),
                                  (front, 0.55, S["F119"]), (front, 0.0, S["F119"])], 12, smooth=True)
    else:  # row 1: red (col 4) | yellow (col 5) | orange (col 6); row 0: amber tip (col 5)
        lathe(P, -0.5, z + 0.1, [(front - 1.1, 0.0, S["F124"]), (front - 0.85, 0.75, S["F124"]), (front - 0.4, 0.9, S["F124"]),
                                 (front, 0.75, S["F124"]), (front, 0.0, S["F124"])], 12, smooth=True)
        lathe(P, -1.35, z - 0.15, [(front - 0.95, 0.0, S["F119"]), (front - 0.7, 0.62, S["F119"]), (front - 0.3, 0.68, S["F119"]),
                                   (front, 0.45, S["F119"]), (front, 0.0, S["F119"])], 12, smooth=True)
        lathe(P, 0.45, z - 0.15, [(front - 0.95, 0.0, S["F121"]), (front - 0.7, 0.62, S["F121"]), (front - 0.3, 0.66, S["F121"]),
                                  (front, 0.45, S["F121"]), (front, 0.0, S["F121"])], 12, smooth=True)
        lathe(P, -0.5, z + 0.3, [(front - 2.0, 0.0, S["F122"]), (front - 1.7, 0.36, S["F122"]), (front - 1.2, 0.5, S["F122"]),
                                 (front - 0.8, 0.45, S["F122"]), (front - 0.6, 0.0, S["F122"])], 10, smooth=True)


def build(sprite, coll, measure_only=False):
    mats = materials(sprite)
    frames = {}
    for frame, s, _suffix in FRAMES:
        P = Part(f"{NAME}-{frame}", smooth_angle=32.0)
        slide(P, s)
        slide_detail(P, s)
        housing(P)
        tail_detail(P)
        sponsons(P)
        body = finish(P, mats, coll)
        objs = [body]
        if s:
            F = Part(f"{NAME}-{frame}-flash", smooth_angle=60.0)
            flash(F, s)
            objs.append(finish(F, mats, coll))
        shell = None if measure_only else common.outline_shell(body, coll, voxel=0.01, faces=1200, smooth=6, inside=0.004)
        frames[frame] = (objs, shell)
    return frames


# --- measuring ------------------------------------------------------------------------------------

def bvh_of(objs):
    bm = bmesh.new()
    mats = []
    for o in objs:
        tmp = bmesh.new()
        tmp.from_mesh(o.data)
        tmp.transform(o.matrix_world)
        off = len(mats)
        mats += [m.name for m in o.data.materials]
        for f in tmp.faces:
            f.material_index += off
        me = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        tmp.free()
    bm.faces.ensure_lookup_table()
    return BVHTree.FromBMesh(bm), bm, mats


def top_samples(objs, k=8, W=12, H=14):
    tree, bm, mats = bvh_of(objs)
    mask, pal = [], []
    for j in range(H * k):
        row, prow = [], []
        for i in range(W * k):
            x = ((i + 0.5) / k - 6) * PX
            y = (7 - (j + 0.5) / k) * PX
            hit = tree.ray_cast(Vector((x, y, 5)), Vector((0, 0, -1)))
            row.append(hit[0] is not None)
            if hit[0] is not None:
                name = mats[bm.faces[hit[2]].material_index]
                prow.append(int(name.split("_")[1]))
            else:
                prow.append(None)
        mask.append(row)
        pal.append(prow)
    bm.free()
    return mask, pal


def measure(frames, sprite, out_dir):
    import sprite_mask as SM
    res = {}
    for frame, s, _suffix in FRAMES:
        objs, _ = frames[frame]
        mask, pal = top_samples(objs)
        m = SM_masks(SM, frame)
        r = SM.measure(m, mask)
        SM.write_png(out_dir / f"top_mask_{frame}.png", mask)
        # rows of the grid coverage vs inner mask
        k = 8
        grid = []
        for y in range(14):
            line = ""
            for x in range(12):
                c = sum(mask[y * k + jj][x * k + ii] for jj in range(k) for ii in range(k)) / (k * k)
                inner = m["inner"][y][x]
                g = c >= 0.5
                line += "#" if g and inner else ("+" if g else ("-" if inner else "."))
            grid.append(line)
        r["grid"] = grid
        # palette index under each sprite pixel centre region (top-visible)
        tv = [[pal[y * k + k // 2][x * k + k // 2] for x in range(12)] for y in range(14)]
        r["top_pal"] = tv
        res[frame] = r
        print(frame, {kk: v for kk, v in r.items() if kk not in ("grid", "top_pal")})
        print("\n".join(grid))
    (out_dir / "measure.json").write_text(json.dumps(res, indent=1))
    return res


def SM_masks(SM, frame):
    """inner/outer/free masks of one sprite frame, exactly as tools/sprite_mask.py main() builds them."""
    idx, colors = SM.load(REF, frame)
    return SM.masks(idx, colors, SM.pulse_partners(idx, SM.load_frames(REF)))


# --- rendering ------------------------------------------------------------------------------------

def render_views(frames, out_dir):
    scene = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.type != "MESH" or not o.name.startswith(NAME):
            bpy.data.objects.remove(o, do_unlink=True)
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x = scene.render.resolution_y = 520
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.32, 0.34, 0.38, 1)
    bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(35), math.radians(-20), math.radians(-30))
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.8
    fill.rotation_euler = (math.radians(-60), math.radians(30), math.radians(150))
    scene.collection.objects.link(fill)
    cam_d = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam
    c = Vector((0, 0, 2.6 * PX))

    def shoot(path, loc, ortho=None, up=None):
        cam.location = Vector(loc) + c
        d = (c - cam.location)
        cam.rotation_euler = d.to_track_quat("-Z", "Y" if up is None else up).to_euler()
        if ortho:
            cam_d.type = "ORTHO"
            cam_d.ortho_scale = ortho
        else:
            cam_d.type = "PERSP"
            cam_d.lens = 85
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    views = {
        "top": ((0, 0, 3), 1.25),
        "west": ((-3, 0, 0.0001), 1.25),
        "east": ((3, 0, 0.0001), 1.25),
        "front": ((0, 3, 0.0001), 1.25),
        "rear": ((0, -3, 0.0001), 1.25),
        "q_fl": ((-1.6, 1.6, 1.4), None),
        "q_rr": ((1.6, -1.6, 1.4), None),
        "game": ((0, -3 * math.sin(math.radians(32)), 3 * math.cos(math.radians(32))), None),
        "under": ((0, 0.0001, -3), 1.25),
    }
    every = [o for f in frames.values() for o in f[0] + ([f[1]] if f[1] else [])]
    for frame, (objs, shell) in frames.items():
        for o in every:
            o.hide_render = o not in objs
        for v, (loc, ortho) in views.items():
            if frame != 168 and v not in ("top", "game", "east", "q_fl"):
                continue
            shoot(out_dir / f"{v}_{frame}.png", loc, ortho)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, REF)
    base = sprite["sprites"][0]
    coll = common.reset_collection(NAME)
    frames = build(sprite, coll, measure_only="--measure" in argv)
    if "--measure" in argv:
        out = Path(argv[argv.index("--measure") + 1])
        out.mkdir(parents=True, exist_ok=True)
        measure(frames, sprite, out)
    for frame, _s, suffix in FRAMES:
        objs, shell = frames[frame]
        n = sum(len(o.data.loop_triangles) or (o.data.calc_loop_triangles() or len(o.data.loop_triangles)) for o in objs)
        print(f"frame {frame}: {n} triangles")
        if shell is None:
            continue
        common.export_sprite_model(ROOT, objs + [shell], f"sidekicks/{NAME}{suffix}", [{**base, "frames": [frame]}])


if __name__ == "__main__":
    main()
