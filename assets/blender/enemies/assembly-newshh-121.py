"""Curled blue biomechanical creature grown into GYGES's organic wall (newshh.shp 81, 83, 119, 121).

What it is: a fixed growth in the wall of 2.2 GYGES (event 15 sky layer, drifting (0,+2) px/tick, exactly with the
layer-2 scenery), the companion of assembly-newshh-45. Four 2x2 enemies make one 48 x 56 px block: wall texture all
round and, on it, a curled glossy blue creature: a round head-bulb at the top right, a segmented feeler running left
along the top and curling down the left side, a short hooked feeler off the bulb, a neck down to a big oval thorax
(the brightest dome), a feeler wrapping the thorax's right side, a dark crease, then the abdomen curled under it with
its segment lumps, ending in a round lobe at the bottom left. Black roots hang from the abdomen's right into the wall.

This design leads with the silhouette and the read at the small tilted game camera: the masses are one fused metaball
skin (bulb, neck, thorax, crease, abdomen, lobe), so it reads as one animal, not glued blobs, and the feelers are
round segmented pipes on top of it (biomechanical ribs). No wall plate (D130): the HD layer-2 terrain is the wall.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshh-121.py
(or blender -b --python this -- [--out whole.glb] [--views DIR] for checks)
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)

NAME = "assembly-newshh-121"
HERE = Path(__file__).resolve().parent
SCRATCH = Path("/Users/dlomibao/projects/tyrian-scratch/e2-enemies-2/assembly-newshh-121/final")
PIECES = [("newshh-81", 0, 0), ("newshh-83", 24, 0), ("newshh-119", 0, 28), ("newshh-121", 24, 28)]
W, H = 48, 56
PX = 1 / 12
Z_B = -0.24  # the creature's flat underside (it lies on the layer-2 wall); tops within +0.35 of the pass
K_META = 0.574  # a lone metaball ellipsoid (radius 1, stiffness 2, threshold 0.6) reaches 0.574 x its size


def X(c):
    return (c + 0.5 - W / 2) * PX


def Y(r):
    return (H / 2 - (r + 0.5)) * PX


def load_grid():
    grid = [[-1] * W for _ in range(H)]
    merged = None
    for name, c0, r0 in PIECES:
        data = common.load_sprite(WT, name)
        if merged is None:
            merged = data
        else:
            merged["colors"].update(data["colors"])
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                grid[r0 + r][c0 + c] = v
    return grid, merged


# --- the creature's parts (sprite px; heights in units) -------------------------------------------
# Masses: name, col, row, rx, ry (px), top z (u), angle (deg, top view), palette index (the part's own
# trimmed median in the sprite).
MASSES = [
    ("bulb", 33.2, 5.0, 7.4, 5.3, 0.20, -8, 53),
    ("bulb_hook", 39.0, 9.6, 2.0, 2.2, -0.04, 0, 51),
    ("neck", 30.0, 11.4, 7.6, 3.0, 0.02, -6, 50),
    ("knot", 21.6, 15.2, 2.7, 1.9, 0.10, 0, 54),
    ("thorax", 22.0, 21.9, 15.8, 7.1, 0.29, 0, 52),
    ("abdomen", 23.6, 39.6, 10.0, 5.4, 0.06, 0, 51),
    ("seg_a", 21.4, 37.0, 3.4, 2.4, 0.13, 0, 52),
    ("seg_b", 27.6, 37.4, 3.0, 2.4, 0.11, 0, 51),
    ("seg_c", 31.2, 41.4, 2.0, 2.4, 0.08, 0, 51),
    ("seg_d", 15.6, 36.6, 2.6, 1.9, 0.09, 0, 52),
    ("seg_e", 20.2, 40.6, 2.0, 1.7, 0.08, 0, 51),
    ("lobe", 11.0, 42.6, 5.4, 6.0, 0.23, 0, 53),
    ("lobe_foot", 13.4, 47.8, 4.4, 2.4, -0.02, 0, 51),
    ("flank", 7.6, 21.0, 3.0, 5.6, 0.02, 0, 52),
    ("tail_root", 9.0, 27.0, 3.0, 2.2, -0.03, 30, 52),
]
# The waist between thorax and abdomen (the sprite's dark band, rows 29-35): a row of ring segments,
# corrugated like a biomechanical hose, not one flat roll.
for k, c in enumerate((15.6, 19.6, 23.6, 27.6, 31.4)):
    MASSES.append((f"waist_{k}", c, 32.4 - 0.25 * (k % 2), 2.3, 2.7, 0.01, 0, 49))
# Feelers: name, [(col, row, radius px)], lift (how far the pipe's centre sits above Z_B, x radius), palette.
FEELERS = [
    ("feeler_top", [(29.0, 3.2, 1.45), (24.0, 3.2, 1.5), (19.5, 3.8, 1.5), (16.3, 4.8, 1.5), (13.4, 7.2, 1.45),
                    (10.6, 10.2, 1.45), (8.0, 13.0, 1.4), (6.2, 15.8, 1.35), (5.5, 19.0, 1.25), (5.6, 22.6, 1.1), (6.6, 25.6, 0.95)],
     0.9, 54),
    ("feeler_inner", [(16.4, 5.2, 0.95), (14.4, 7.2, 1.05), (12.4, 9.2, 1.1), (10.8, 11.2, 1.05), (9.4, 13.0, 0.95)], 0.9, 54),
    ("feeler_hook", [(39.6, 7.4, 0.95), (39.3, 10.2, 1.0), (37.8, 12.3, 0.9), (35.6, 13.4, 0.8)], 1.0, 51),
    ("feeler_wrap", [(38.6, 20.6, 0.95), (38.4, 23.4, 1.15), (37.0, 26.6, 1.15), (34.5, 28.8, 1.05),
                     (31.2, 30.4, 0.95), (27.0, 31.2, 0.85)], 1.3, 52),
]
# Roots hanging from the abdomen into the wall's dark hollow, laid on the sprite's dark-grey streaks
# (indices 96-99) in that hollow: the main one down cols 39-40 (rows 30-46) bending down-left to the
# wall at row 49, one down col 35 along the abdomen's edge (rows 37-45), and a short one off the
# main root down col 43 (rows 38-42). They are in the hollow, which the creature IoU leaves free; their
# own fit is measured against the streak pixels.
ROOTS = [
    [(38.2, 29.6, 0.85), (39.5, 31.8, 0.95), (39.7, 34.5, 1.05), (39.9, 38.0, 1.05), (39.8, 41.5, 1.0),
     (39.4, 44.6, 0.9), (38.2, 46.4, 0.8), (36.2, 47.8, 0.75), (34.4, 49.0, 0.65)],
    [(34.2, 35.0, 0.7), (35.0, 37.4, 0.75), (35.1, 40.0, 0.75), (34.9, 42.4, 0.7), (34.2, 44.6, 0.6),
     (33.4, 45.6, 0.55)],
    [(40.4, 36.2, 0.55), (42.0, 37.8, 0.6), (42.9, 40.0, 0.6), (43.0, 42.4, 0.5)],
]
ROOT_PAL = 48
SPEC = {48: 0.2, 49: 0.2, 50: 0.15, 51: 0.18}  # Specular IOR Level per palette index (0.5 = Blender's default 4% F0)
SKIN_FACES = 16000  # the metaball skin's triangles after its decimate (feelers and roots add ~4k)
CAP_SEAMS = "--opencut" not in sys.argv
SHELL_OVERLAP = 1.5 * PX  # each piece's cut of the shell runs this far into its neighbour


# --- geometry helpers ------------------------------------------------------------------------------

def catmull(points, step=0.3):
    """Resample a polyline of tuples through Catmull-Rom (uniform), about `step` px apart."""
    pts = [tuple(p) for p in points]
    ext = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        seg = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        n = max(2, int(seg / step))
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(pts[-1])
    return out


def sweep(bm, path, sides=14, mat=0, rib_period=0.0, rib_amp=0.0):
    """A round pipe along path [(x, y, z, r)] (units), its radius ribbed every `rib_period` units, with
    rounded (hemispherical) ends. Rings stand perpendicular to the path."""
    pts = [Vector(p[:3]) for p in path]
    rs = [p[3] for p in path]
    # Arc length for the ribs.
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + (b - a).length)
    if rib_period > 0:
        rs = [r * (1 + rib_amp * max(0.0, math.cos(2 * math.pi * si / rib_period)) ** 4) for r, si in zip(rs, s)]
    rings = []
    up = Vector((0, 0, 1))

    def frame(i):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.normalize()
        n = up.cross(t)
        if n.length < 1e-6:
            n = Vector((1, 0, 0))
        n.normalize()
        b = t.cross(n)
        return t, n, b

    def ring(p, r, n, b):
        return [bm.verts.new(p + r * (math.cos(2 * math.pi * k / sides) * n + math.sin(2 * math.pi * k / sides) * b))
                for k in range(sides)]

    t0, n0, b0 = frame(0)
    t1, n1, b1 = frame(len(pts) - 1)
    caps0 = []
    for k in (3, 2, 1):
        a = k / 4 * math.pi / 2
        caps0.append(ring(pts[0] - t0 * rs[0] * math.sin(a), rs[0] * math.cos(a), n0, b0))
    tip0 = bm.verts.new(pts[0] - t0 * rs[0])
    for i, (p, r) in enumerate(zip(pts, rs)):
        _, n, b = frame(i)
        rings.append(ring(p, r, n, b))
    caps1 = []
    for k in (1, 2, 3):
        a = k / 4 * math.pi / 2
        caps1.append(ring(pts[-1] + t1 * rs[-1] * math.sin(a), rs[-1] * math.cos(a), n1, b1))
    tip1 = bm.verts.new(pts[-1] + t1 * rs[-1])
    allr = caps0 + rings + caps1
    faces = []
    for ra, rb in zip(allr, allr[1:]):
        for k in range(sides):
            faces.append(bm.faces.new((ra[k], ra[(k + 1) % sides], rb[(k + 1) % sides], rb[k])))
    for k in range(sides):
        faces.append(bm.faces.new((tip0, allr[0][(k + 1) % sides], allr[0][k])))
        faces.append(bm.faces.new((tip1, allr[-1][k], allr[-1][(k + 1) % sides])))
    for f in faces:
        f.material_index = mat
        f.smooth = True
    return faces


def feeler_path(pts, lift, ribs=True):
    """(col, row, r px) control points to a pipe path in units, centre `lift` x r above Z_B."""
    fine = catmull(pts, 0.45)
    return [(X(c), Y(r), Z_B + lift * rad * PX, rad * PX) for c, r, rad in fine]


def creature_mask(grid):
    """The creature's pixels: every blue (48-62) plus the dark crevices between its parts (a dark pixel
    with two blue 4-neighbours), not the wall's dark hollow at the bottom right."""
    blue = [[48 <= grid[r][c] <= 62 for c in range(W)] for r in range(H)]
    out = [[False] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if blue[r][c]:
                out[r][c] = True
            elif grid[r][c] < 48 and not (r >= 29 and c >= 33):
                n = sum(1 for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if 0 <= r + dr < H and 0 <= c + dc < W and blue[r + dr][c + dc])
                out[r][c] = n >= 2
    return out


GROOVES = [(24.6, 34.2, 44.0, 0.05), (18.6, 34.2, 43.0, 0.045), (29.6, 35.0, 44.0, 0.04)]  # col, rows, depth (u)
SKIN_SX, SKIN_S, SKIN_SZ = 2.0, 0.28, 0.15
SKIN_PAL, SKIN_Q = 50, 1.8  # skin away from every mass: the dark crevice blue  # the skin's edge lands on the mask's pixel edge; its top 0.4 x SZ


def masses_mesh(coll, mats_index, mask):
    """The fused skin: one metaball ellipsoid per mass, clipped flat at Z_B (a closed, plain underside).
    Faces take the palette slot of the mass whose ellipsoid they sit nearest the surface of."""
    mb = bpy.data.metaballs.new(f"{NAME}_meta")
    mb.resolution = 0.013
    mb.render_resolution = 0.013
    mb.threshold = 0.6
    ob = bpy.data.objects.new(f"{NAME}_meta", mb)
    coll.objects.link(ob)
    # The low skin over every creature pixel: one soft ball per pixel, sized so their fields sum to the
    # threshold right on the mask's edge (a 3 px strip keeps its 3 px), fusing into one sheet.
    for r in range(H):
        for c in range(W):
            if mask[r][c]:
                e = mb.elements.new(type="ELLIPSOID")
                e.co = (X(c), Y(r), Z_B)
                e.radius = 1.0
                e.stiffness = SKIN_S
                e.size_x = e.size_y = SKIN_SX * PX
                e.size_z = SKIN_SZ
    shapes = []
    for name, c, r, rx, ry, top, ang, pal in MASSES:
        az = (top - Z_B) / 1.35
        zc = Z_B + 0.35 * az
        e = mb.elements.new(type="ELLIPSOID")
        e.co = (X(c), Y(r), zc)
        e.radius = 1.0
        e.stiffness = 2.0
        e.size_x, e.size_y, e.size_z = rx * PX / K_META, ry * PX / K_META, az / K_META
        # Sprite rows grow down, so a top-view angle measured on screen turns the other way in Blender.
        e.rotation = Quaternion((0, 0, 1), math.radians(-ang))
        shapes.append((Vector((X(c), Y(r), zc)), rx * PX, ry * PX, az, math.radians(-ang), mats_index[pal]))
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bm = bmesh.new()
    bm.from_mesh(me)
    cut = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, Z_B),
                                 plane_no=(0, 0, -1), clear_outer=True)
    edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    # Scanfill, so the loops round the open curl stay holes in the flat underside.
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges, normal=(0, 0, -1))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # Shallow transverse grooves between the abdomen's segment lumps (z only: the outline is untouched).
    for gc, gr0, gr1, depth in GROOVES:
        for v in bm.verts:
            if v.co.z > Z_B + 0.05 and gr0 <= (H / 2 - v.co.y) / PX <= gr1:
                d = ((v.co.x / PX + W / 2) - gc) / 0.55
                v.co.z -= min(depth, (v.co.z - Z_B) * 0.5) * math.exp(-d * d)
    bm = decimated(coll, bm, SKIN_FACES)
    # Palette regions: each slot's field is the smallest q of its masses (the crevice skin's is the
    # constant SKIN_Q); a face belongs to the slot with the smallest field. The skin is cut along the
    # field's iso-lines (where two slots' fields are equal) after the decimate, so each region's border
    # is a smooth curve of the ellipsoids, not the decimated triangles' sawtooth (round 1 review).
    slots = sorted({s for *_, s in shapes} | {mats_index[SKIN_PAL]})

    def fields(p):
        f = {s: (SKIN_Q if s == mats_index[SKIN_PAL] else 1e9) for s in slots}
        for (co, ax, ay, az, ang, s) in shapes:
            d = p - co
            ca, sa = math.cos(ang), math.sin(ang)
            u, v = d.x * ca + d.y * sa, -d.x * sa + d.y * ca
            q = (u / ax) ** 2 + (v / ay) ** 2 + (d.z / az) ** 2
            if q < f[s]:
                f[s] = q
        return f

    iso_cut(bm, slots, fields)
    for f in bm.faces:
        fl = fields(f.calc_center_median())
        f.material_index = min(fl, key=fl.get)
        f.smooth = abs(f.normal.z + 1) > 1e-3
    bpy.data.meshes.remove(me)
    return bm


def decimated(coll, bm, target):
    """bm through a collapse decimate down to about `target` triangles (a new bmesh; bm is freed)."""
    me = bpy.data.meshes.new(f"{NAME}_dec")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(f"{NAME}_dec", me)
    coll.objects.link(ob)
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    print("skin triangles before decimate", n)
    if n > target:
        dec = ob.modifiers.new("decimate", "DECIMATE")
        dec.ratio = target / n
        common._apply_modifiers(ob)
    out = bmesh.new()
    out.from_mesh(ob.data)
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    return out


def iso_cut(bm, slots, fields, eps=1e-5):
    """Cut bm's faces along every slot's border: for each slot s, h_s = field_s - min(other fields) is
    zero exactly on that border, so each edge whose ends have opposite signs is split at its linear
    zero and the new vertices are joined across their faces. The flat underside is left alone."""
    def h(v, s):
        f = fields(v.co)
        return f[s] - min(x for t, x in f.items() if t != s)

    for s in slots:
        hv = {v: h(v, s) for v in bm.verts}
        zero = [v for v, x in hv.items() if abs(x) < eps and v.co.z > Z_B + 1e-4]
        for e in list(bm.edges):
            a, b = e.verts
            ha, hb = hv[a], hv[b]
            if ha * hb >= 0 or abs(ha) < eps or abs(hb) < eps:
                continue
            if a.co.z <= Z_B + 1e-4 and b.co.z <= Z_B + 1e-4:
                continue
            t = ha / (ha - hb)
            pa, pb = a.co.copy(), b.co.copy()
            _, nv = bmesh.utils.edge_split(e, a, t)
            nv.co = pa.lerp(pb, t)
            hv[nv] = 0.0
            zero.append(nv)
        if zero:
            bmesh.ops.connect_verts(bm, verts=zero, check_degenerate=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.normal_update()


# --- build ----------------------------------------------------------------------------------------

def build(sprite, grid):
    coll = common.reset_collection(NAME)
    tag = "nshh121"
    # Same materials as assembly-newshh-45's beast: satin blue hide (metallic 0.3-0.35, roughness 0.4-0.5).
    pals = sorted({m[-1] for m in MASSES} | {f[-1] for f in FEELERS} | {ROOT_PAL})
    # Pal 50 (neck and crevice skin) is less metallic than 45's and has a lower F0: its linear colour
    # (about 0.014 blue) is darker than a dielectric's 4% grey reflection, so the environment's grey
    # washed it out to a grey strap in game (round 1 review). Lower metallic alone makes that worse
    # (more of the grey dielectric lobe); the Specular IOR Level brings F0 down to the colour's level
    # and roughness 0.75 spreads the environment panels' reflection (at 0.55 with F0 0.012 the strap
    # still read grey in game; at 0.75 it is the original's dark blue).
    # Round 2: the same fault showed on pal 51 (the abdomen's right half read slate grey), so every
    # dark index (48-51) gets the lower F0 and a rougher lobe, not only the one a reviewer named.
    params = {48: (0.2, 0.65), 49: (0.3, 0.6), 50: (0.15, 0.75), 51: (0.3, 0.65), 52: (0.35, 0.45),
              53: (0.35, 0.4), 54: (0.35, 0.4)}
    mats, slot = [], {}
    for p in pals:
        slot[p] = len(mats)
        m, rgh = params[p]
        mat = common.palette_material(sprite, p, tag, metallic=m, roughness=rgh)
        if p in SPEC:  # exported as KHR_materials_specular (D176)
            bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = SPEC[p]
        mats.append(mat)

    bm = masses_mesh(coll, slot, creature_mask(grid))
    for name, pts, lift, pal in FEELERS:
        sweep(bm, feeler_path(pts, lift), sides=12, mat=slot[pal], rib_period=1.7 * PX, rib_amp=0.17)
    body = bpy.data.meshes.new(NAME)
    bm.to_mesh(body)
    bm.free()
    for m in mats:
        body.materials.append(m)
    obj = bpy.data.objects.new(NAME, body)
    coll.objects.link(obj)

    bm = bmesh.new()
    for pts in ROOTS:
        sweep(bm, feeler_path(pts, 0.7), sides=10, mat=slot[ROOT_PAL], rib_period=1.4 * PX, rib_amp=0.12)
    rme = bpy.data.meshes.new(f"{NAME}_roots")
    bm.to_mesh(rme)
    bm.free()
    for m in mats:
        rme.materials.append(m)
    roots = bpy.data.objects.new(f"{NAME}_roots", rme)
    coll.objects.link(roots)
    return coll, obj, roots


def joined(coll, objs, name):
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in objs[0].data.materials:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def split_pieces(obj, layout, coll):
    """common.split_assembly, except that each cut's cap takes the colour of the skin it closes (the
    common one leaves caps on material slot 0, here the darkest blue, which showed as a dark line
    along the seams where the pieces' caps meet) and is flat shaded."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        hw, hh = 12 / 12, 14 / 12
        caps = []
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            cut = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                         plane_no=no, clear_outer=True)
            edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge) and e.is_valid]
            if edges and CAP_SEAMS:
                caps += bmesh.ops.holes_fill(bm, edges=edges, sides=0)["faces"]
        for f in caps:
            if not f.is_valid:
                continue
            f.smooth = False
            near = [g.material_index for e in f.edges for g in e.link_faces if g is not f and g not in caps]
            if near:
                f.material_index = max(set(near), key=near.count)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        # The whole creature's normals onto the piece: along a cut the piece's own normals see only one
        # side and shaded a thin line down each seam in game (the abdomen's lumps showed it most).
        ob.location = (x0, y0, 0)
        dt = ob.modifiers.new("normals", "DATA_TRANSFER")
        dt.object = obj
        dt.use_loop_data = True
        dt.data_types_loops = {"CUSTOM_NORMAL"}
        dt.loop_mapping = "POLYINTERP_NEAREST"
        common._apply_modifiers(ob)
        ob.location = (0, 0, 0)
        out[name] = ob
    return out


def split_open(obj, layout, coll):
    """Like common.split_assembly, but the cuts stay open: for the outline shell, which is made once
    from the whole creature and then cut, so no piece's ink runs along a seam (a shell per piece
    rounded each cut edge and drew a dark line across the thorax where the pieces meet)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        hw, hh = 12 / 12 + SHELL_OVERLAP, 14 / 12 + SHELL_OVERLAP
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        sh["tyrian_outline"] = True
        sh.hide_render = True
        coll.objects.link(sh)
        out[name] = sh
    return out


def shell_of(coll, obj, faces):
    src = obj.copy()
    src.data = obj.data.copy()
    coll.objects.link(src)
    sh = common.outline_shell(src, coll, faces=faces)
    bpy.data.objects.remove(src)
    sh.hide_render = True
    return sh


# --- views ----------------------------------------------------------------------------------------

def setup_render(px, py, engine="EEVEE"):
    scene = bpy.context.scene
    if engine == "WORKBENCH":
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "FLAT"
        scene.display.shading.color_type = "SINGLE"
        scene.display.shading.single_color = (1, 1, 1)
    else:
        for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scene.render.engine = e
                break
            except TypeError:
                pass
        scene.display_settings.display_device = "sRGB"
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
    bg.inputs[0].default_value = (0.05, 0.06, 0.08, 1)
    bg.inputs[1].default_value = 1.0
    for nm, rot, en in (("key", (math.radians(40), 0, math.radians(-35)), 4.0),
                        ("fill", (math.radians(60), 0, math.radians(150)), 1.2)):
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


def views(out_dir, creature, roots):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH" and o not in (creature, roots):
            o.hide_render = True
    # 1. Top-view mask at 8x sprite scale (creature only, flat white) for the IoU.
    setup_render(W * 8, H * 8, "WORKBENCH")
    roots.hide_render = True
    c = cam("top", (0, 0, 10), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    render(out_dir / "mask_top.png")
    roots.hide_render = False
    render(out_dir / "mask_top_roots.png")
    # 2. Lit views.
    lights()
    setup_render(W * 8, H * 8)
    c = cam("top_lit", (0, 0, 10), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    render(out_dir / "top.png")
    D = 9.0
    vs = {
        "game": ((0, -D * math.sin(math.radians(15)), D * math.cos(math.radians(15))), 40),
        "steep": ((0, -D * math.sin(math.radians(32)), D * math.cos(math.radians(32))), 40),
        "front": ((0, -D, 0.0), 40),
        "rear": ((0, D, 0.0), 40),
        "side_e": ((D, 0, 0.0), 40),
        "side_w": ((-D, 0, 0.0), 40),
        "q_fw": ((-D * 0.55, -D * 0.6, D * 0.55), 40),
        "q_fe_low": ((D * 0.75, -D * 0.55, D * 0.3), 40),
        "q_rw": ((-D * 0.5, D * 0.6, D * 0.55), 40),
        "under": ((0, -0.3, -D), 40),
    }
    setup_render(640, 640)
    for nm, (loc, lens) in vs.items():
        cam(nm, loc, (0, 0, 0), lens=lens * 1.6)
        render(out_dir / f"{nm}.png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    grid, sprite = load_grid()
    coll, creature, roots = build(sprite, grid)
    tris = sum(len(p.vertices) - 2 for p in creature.data.polygons) + sum(len(p.vertices) - 2 for p in roots.data.polygons)
    print(f"{NAME}: creature+roots {tris} triangles")
    whole = joined(coll, [creature, roots], f"{NAME}")
    shell = shell_of(coll, whole, 3600)
    shell.name = shell.data.name = f"{NAME}_outline"
    if "--out" in argv:
        common.export_glb([whole, shell], Path(argv[argv.index("--out") + 1]))
    layout = [(name, c0 + 12 - W / 2, r0 + 14 - H / 2) for name, c0, r0 in PIECES]
    parts = split_pieces(whole, layout, coll)
    shells = split_open(shell, layout, coll)
    for name, _, _ in PIECES:
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, [parts[name], shells[name]], f"enemies/{name}", data["sprites"])
        parts[name].hide_render = True
    if "--views" in argv:
        whole.hide_render = True
        views(argv[argv.index("--views") + 1], creature, roots)


if __name__ == "__main__":
    main()
