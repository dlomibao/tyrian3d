"""GYGES brood organism set piece (level 2.4): one builder for assembly-newshh-125 (newshh.shp 85, 87, 123,
125, the block) and the pieces it hatches: the grey cap newshh-79, the green spore orbs newshh-89/-127/-91 and the
green thorn assembly-newshh-77 (77 over 115). The model scripts next to this file (assembly-newshh-125.py,
newshh-79.py, newshh-89.py, newshh-127.py, newshh-91.py, assembly-newshh-77.py) each call one export_* function.
build-models.sh skips lib_ files.

What it is (spawn timeline, link 70): a terrain-fixed organism grown into the GYGES tube wall. The 48 x 56 block
spawns first; 28 px above it the 24 x 12 silver cap newshh-79 sits on the end of the block's stalk (so 79 is the
organism's cap and the stalk is its stem); from the same spot the organism then releases three glossy green spore
orbs (15, 18, 21 px, weaving +-2/4/8 px) and a green thorn pod (24 x 56, weaving +-16): one hatching sequence.
The damaged frame newshh.shp 41 of the cap has no model of its own: the game draws the intact cap (D87, D173).

- every body is a loft of D sections (a superellipse arch over a flat sole at Z_B, the wall), stations traced from the
  sprite and interpolated along arc length with Catmull-Rom, so the stalk, curled abdomen and purple vein are faired
  tubes; the stalk swells into a low root foot at its east base; the abdomen carries faint segment grooves (z only,
  outline untouched); the vein sleeve has its three rib bulges where the sprite draws its light bands; the two
  purple siphons have a sunken orifice ring;
- no wall plate (D130): the HD GYGES terrain under the block is the same tube wall, so only the creature is modelled;
- the cap (79) is a D-plan shell: round to the north, its south face a rounded lip over the stalk socket;
- the orbs are closed glossy spheres (satin green: the sheen is lighting, no painted spot);
- the thorn is a closed lens-section pod, level (D163): a lofted head with a raised green hood and collar and a
  12-facet spike whose facets take the sprite's own olive ramp (lit left, dark right; D175 facet ramp).
Every piece is centred on its own tile when exported, with an outline shell (D90, D118) tagged tyrian_outline.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)
sys.path.insert(0, str(WT / "tools"))
import sprite_mask  # noqa: E402  (pure standard library, read-only; as assembly-newsh4-195.py)


def inner_extents(name):
    """{row: (first col, last col + 1)} of the sprite's inner mask (opaque minus its ink ring, D74)."""
    idx, colors = sprite_mask.load(name, ref=WT / "reference" / "models")
    inner = sprite_mask.masks(idx, colors)["inner"]
    out = {}
    for r, row in enumerate(inner):
        cols = [c for c, v in enumerate(row) if v]
        if cols:
            out[r] = (cols[0], cols[-1] + 1)
    return out


PX = 1 / 12
W, H = 48, 56  # the block, in sprite px
Z_B = -2.9  # px: the creature's flat sole on the wall (same pass depth as assembly-newshh-121: -0.24 u)
BLOCK = [("newshh-85", 0, 0), ("newshh-87", 24, 0), ("newshh-123", 0, 28), ("newshh-125", 24, 28)]


# --- coordinates: block pixel CORNER coordinates (col 0..48, row 0..56), centre of the block at the origin ---

def X(c):
    return (c - W / 2) * PX


def Y(r):
    return (H / 2 - r) * PX


def load(name):
    return common.load_sprite(WT, name)


def load_block():
    grid = [[-1] * W for _ in range(H)]
    merged = None
    for name, c0, r0 in BLOCK:
        d = load(name)
        if merged is None:
            merged = d
        else:
            merged["colors"].update(d["colors"])
        for r, row in enumerate(d["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                grid[r0 + r][c0 + c] = v
    return grid, merged


# --- curve + loft helpers (sprite px in, units out) --------------------------------------------------------------

def catmull(points, step=0.5):
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
            out.append(tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2
                                    + (-a + 3 * b - 3 * c + d) * t3) for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(pts[-1])
    return out


def d_section(w, zb, zt, sides, n=2.2):
    """A D section: (offset across, z) from the right sole point over the top to the left sole point (px).
    Superellipse exponent n > 2 gives the full organic shoulder of the sprite's tubes."""
    pts = []
    for k in range(sides + 1):
        th = math.pi * k / sides
        c, s = math.cos(th), math.sin(th)
        x = w * math.copysign(abs(c) ** (2 / n), c)
        z = zb + (zt - zb) * abs(s) ** (2 / n)
        pts.append((x, z))
    return pts


def tube(bm, ctrl, sides=16, step=0.5, n=2.2, end0="round", end1="round", zmod=None, wmod=None, mat=0):
    """Loft D sections along a plan centreline. ctrl: [(col, row, half width px, z top px, z sole px)].
    zmod/wmod(s, col, row) -> factor, for grooves and rib bulges (s = arc length in px).
    Ends: "round" (an ellipsoidal end, 0.85 x the half width long) or "flat"."""
    fine = catmull(ctrl, step)
    s = [0.0]
    for a, b in zip(fine, fine[1:]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))

    def tangent(i):
        a, b = fine[max(i - 1, 0)], fine[min(i + 1, len(fine) - 1)]
        t = Vector((b[0] - a[0], b[1] - a[1]))
        return t.normalized() if t.length > 1e-9 else Vector((0, 1))

    stations = []  # (centre col,row, tangent (dc,dr), w, zb, zt)
    for i, (c, r, w, zt, zb) in enumerate(fine):
        t = tangent(i)
        f_z = zmod(s[i], c, r) if zmod else 1.0
        f_w = wmod(s[i], c, r) if wmod else 1.0
        stations.append((c, r, t, w * f_w, zb, zb + (zt - zb) * f_z))

    def endcap(st, sign):
        c, r, t, w, zb, zt = st
        L = 0.85 * w
        extra = []
        for f in (0.3, 0.55, 0.75, 0.9, 0.97):
            k = math.sqrt(max(1 - f * f, 0.0))
            extra.append((c + sign * t.x * L * f, r + sign * t.y * L * f, t, w * k, zb, zb + (zt - zb) * k))
        return extra

    rows = list(stations)
    tip0 = tip1 = None
    if end0 == "round":
        rows = list(reversed(endcap(stations[0], -1))) + rows
        c, r, t, w, zb, zt = stations[0]
        tip0 = (c - t.x * 0.85 * w, r - t.y * 0.85 * w, zb + 0.12 * (zt - zb))
    if end1 == "round":
        rows = rows + endcap(stations[-1], 1)
        c, r, t, w, zb, zt = stations[-1]
        tip1 = (c + t.x * 0.85 * w, r + t.y * 0.85 * w, zb + 0.12 * (zt - zb))

    rings = []
    for c, r, t, w, zb, zt in rows:
        side = (t.y, -t.x)  # right of the direction of travel, in (col, row)
        ring = []
        for x, z in d_section(w, zb, zt, sides, n):
            ring.append(bm.verts.new((X(c + side[0] * x), Y(r + side[1] * x), z * PX)))
        rings.append(ring)
    faces = []
    m = sides + 1
    for ra, rb in zip(rings, rings[1:]):
        for k in range(m):
            j = (k + 1) % m
            faces.append(bm.faces.new((ra[k], ra[j], rb[j], rb[k])))
    tube.meta = (m, len(faces))  # strip faces come first: face i is ring pair i // m, section column k = i % m
    for ring, tip in ((rings[0], tip0), (rings[-1], tip1)):
        if tip is None:
            faces.append(bm.faces.new(ring))
        else:
            tv = bm.verts.new((X(tip[0]), Y(tip[1]), tip[2] * PX))
            for k in range(m):
                faces.append(bm.faces.new((ring[k], ring[(k + 1) % m], tv)))
    for f in faces:
        f.material_index = mat
        f.smooth = True
    return faces


def blob(bm, col, row, rx, ry, zt, zb, angle_deg=0.0, segs=28, rings=14, mat=0, dimple=None):
    """A spheroid dome: plan ellipse (rx, ry px, rotated angle_deg on screen), top zt, flat sole zb (px).
    dimple=(dcol, drow, radius px, depth px): a sunken orifice ring on its top."""
    before = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    for v in res["verts"]:
        u, w, h = v.co.x, v.co.y, v.co.z
        dc, dr = u * rx * ca - w * ry * sa, u * rx * sa + w * ry * ca
        z = zb + max(h, 0.0) * (zt - zb) if h >= 0 else zb
        if dimple is not None and h > 0:
            ddc, ddr, rad, depth = dimple
            d = math.hypot(dc - ddc, dr - ddr) / rad
            z -= depth * math.exp(-(d ** 4)) * (1 if d < 1.6 else 0)
        v.co = Vector((X(col + dc), Y(row + dr), z * PX))
    bm.faces.ensure_lookup_table()
    faces = bm.faces[before:]
    bmesh.ops.remove_doubles(bm, verts=list({v for f in faces for v in f.verts}), dist=1e-6)
    bm.faces.ensure_lookup_table()
    faces = [f for f in bm.faces[before:] if f.is_valid]
    for f in faces:
        f.material_index = mat
        f.smooth = True
    return faces


# --- the block: the organism on the wall --------------------------------------------------------------------------
# Stations (col, row, half width, z top, z sole), px, from the blueprint (cross-sections first), refitted to the
# sprite trace for the top-view rule.
STALK = [(23.3, -2.0, 6.3, 2.2, Z_B), (23.3, 3.0, 6.3, 2.4, Z_B), (23.4, 8.0, 6.6, 2.5, Z_B),
         (24.1, 13.0, 7.1, 2.4, Z_B), (25.0, 18.0, 7.5, 2.2, Z_B), (26.6, 22.6, 8.0, 1.8, Z_B),
         (29.0, 26.2, 7.6, 1.1, Z_B), (31.0, 28.6, 5.0, 0.4, Z_B)]
ABDOMEN = [(5.6, 29.4, 3.0, 0.8, Z_B), (6.9, 33.0, 4.0, 2.0, Z_B), (10.2, 36.8, 5.8, 3.1, Z_B),
           (15.0, 39.6, 7.3, 3.6, Z_B), (21.0, 39.6, 6.9, 3.4, Z_B), (26.6, 38.4, 5.9, 2.9, Z_B),
           (32.0, 37.8, 6.4, 2.4, Z_B), (37.0, 36.6, 5.8, 1.8, Z_B), (40.6, 34.8, 3.6, 0.9, Z_B)]
SLEEVE = [(20.6, 10.0, 2.2, 3.0), (20.7, 11.2, 3.3, 3.6), (20.8, 12.8, 3.4, 3.6), (21.0, 15.0, 3.5, 3.6),
          (21.2, 17.2, 3.4, 3.4), (21.4, 19.2, 3.7, 3.5), (22.4, 21.4, 3.2, 3.1), (23.3, 23.6, 2.5, 2.6),
          (23.9, 25.6, 1.8, 2.1), (24.4, 27.0, 1.1, 1.5)]
SLEEVE_RIBS = [10.4, 14.6, 19.2]  # rows of the sprite's light bands
GLAND = (16.8, 27.7, 8.0, 6.8, 4.2)  # col, row, rx, ry, z top
TIP = (5.4, 28.4, 4.6, 2.6, 1.9, -48.0)  # col, row, rx, ry, z top, plan angle (screen degrees)
PAD = (35.4, 40.9, 5.0, 4.9, 2.7, -25.0)

# Palette per region: the sprite's trimmed median per part (15/85 trim). Stalk by plan row (D176: it can't slope
# steeply enough to shade itself): top 102, middle 100, foot 99. Abdomen 103, its south flank 101; gland 103.
# Purple: sleeve and tip 85, pad 83 (lifted to 84 on the lit crown, the sprite's own next step).
GREYS = {99: (0.25, 0.6, 0.25), 100: (0.25, 0.55, 0.3), 101: (0.25, 0.5, 0.4), 102: (0.25, 0.45, 0.5),
         103: (0.25, 0.4, 0.5), 104: (0.25, 0.4, 0.5)}  # index: metallic, roughness, Specular IOR Level
PURPLES = {83: (0.15, 0.45, 0.3), 84: (0.15, 0.45, 0.3), 85: (0.15, 0.4, 0.35), 87: (0.15, 0.4, 0.4)}


def set_spec(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level


def block_materials(sprite):
    mats, slot = [], {}
    for table in (GREYS, PURPLES):
        for i, (m, rgh, spec) in table.items():
            slot[i] = len(mats)
            mat = common.palette_material(sprite, i, "nshh125A", metallic=m, roughness=rgh)
            set_spec(mat, spec)
            mats.append(mat)
    return mats, slot


def build_block(coll, sprite):
    mats, slot = block_materials(sprite)
    bm = bmesh.new()

    def rowc(f):
        cen = f.calc_center_median()
        return cen.x / PX + W / 2, H / 2 - cen.y / PX, cen.z / PX

    # Stalk: open (flat) north end beyond the block edge (the split cuts it at row 0, under the cap).
    faces = tube(bm, STALK, sides=18, end0="flat", end1="round")
    m, nstrip = tube.meta
    bm.normal_update()
    for i, f in enumerate(faces):
        c, r, z = rowc(f)
        k = i % m if i < nstrip else -1
        # 100 overall (the stalk's trimmed median). By section column (so each border runs straight along the
        # tube): its crown 102 in the north rows (the sprite's 102-104 stripe, rows 0-10), its east flank 99 (the
        # sprite's 97-99 shadow side, D176: a 5 px high tube can't shade itself that dark under the game's sun).
        if 7 <= k <= 10 and r < 10.5:
            f.material_index = slot[102]
        elif 0 <= k <= 2 or k == m - 1:
            f.material_index = slot[99]
        else:
            f.material_index = slot[100]
    # The foot: a low flare on the east side of the stalk's base into the wall (sprite rows 24-31, cols 30-40).
    faces = blob(bm, 33.2, 28.6, 5.0, 3.0, -0.8, Z_B, angle_deg=20, segs=28, rings=10)
    for f in faces:
        f.material_index = slot[99]
    # Fillers: the low web of body in the crease where gland, stalk foot and abdomen meet (the sprite draws it as
    # creature, rows 30-33), and the foot's tail into the abdomen's east end.
    for c, r, rx, ry, zt, ang in ((23.6, 31.4, 3.6, 2.0, -0.2, 0.0), (36.6, 31.0, 2.6, 1.7, -1.0, 0.0)):
        for f in blob(bm, c, r, rx, ry, zt, Z_B, angle_deg=ang, segs=20, rings=8):
            f.material_index = slot[99]

    # Abdomen: the curled grub body, segment grooves every 3.6 px (z only).
    def grooves(s, c, r):
        if s < 3 or c > 39:
            return 1.0
        ph = (s % 3.6) / 3.6 - 0.5
        return 1.0 - 0.07 * math.exp(-((ph / 0.12) ** 2))

    faces = tube(bm, ABDOMEN, sides=20, zmod=grooves)
    m, nstrip = tube.meta
    for i, f in enumerate(faces):
        k = i % m if i < nstrip else -1
        # 103 (the abdomen's median); its outer flank (left of the path: south on the bottom run, west on the
        # west leg) 101, the sprite's darker outer rows, by section column so the border runs along the body.
        f.material_index = slot[101 if k >= m - 6 else 103]

    # Gland: the round egg on the stalk's foot (smooth, sheen is lighting).
    faces = blob(bm, GLAND[0], GLAND[1], GLAND[2], GLAND[3], GLAND[4], Z_B, segs=32, rings=16)
    for f in faces:
        f.material_index = slot[103]

    # Vein sleeve: a ribbed purple tube lying on the stalk's west side, sole sunk into the stalk.
    def rib(r):
        return sum(math.exp(-(((r - rr) / 1.0) ** 2)) for rr in SLEEVE_RIBS)

    sleeve = [(c, r, w, zt, max(Z_B, zt - 2.2 * w)) for c, r, w, zt in SLEEVE]
    faces = tube(bm, sleeve, sides=16, n=2.4, wmod=lambda s, c, r: 1.0 + 0.07 * rib(r),
                 zmod=lambda s, c, r: 1.0 + 0.07 * rib(r))
    for f in faces:
        f.material_index = slot[85]

    # Siphon tip (west) and pad (east), each with a sunken orifice ring.
    c, r, rx, ry, zt, ang = TIP
    faces = blob(bm, c, r, rx, ry, zt, Z_B, angle_deg=ang, segs=24, rings=12, dimple=(-2.6, -1.4, 1.1, 0.7))
    for f in faces:
        f.material_index = slot[85]
    c, r, rx, ry, zt, ang = PAD
    faces = blob(bm, c, r, rx, ry, zt, Z_B, angle_deg=ang, segs=28, rings=12, dimple=(0.6, 0.4, 1.4, 0.8))
    bm.normal_update()
    for f in faces:
        f.material_index = slot[84 if f.normal.z > 0.8 else 83]

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("assembly-newshh-125")
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new("assembly-newshh-125", me)
    coll.objects.link(obj)
    return obj


# --- assembly splitting (copied from assembly-newshh-121: caps take the skin's colour; shells cut open) -----------

def split_pieces(obj, layout, coll, cap=True):
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
            if edges and cap:
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
        out[name] = ob
    return out


def shell_of(coll, obj, faces):
    src = obj.copy()
    src.data = obj.data.copy()
    coll.objects.link(src)
    sh = common.outline_shell(src, coll, faces=faces)
    bpy.data.objects.remove(src)
    sh.hide_render = True
    return sh


def mesh_obj(coll, name, bm, mats):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


# --- newshh-79: the silver cap on the stalk ------------------------------------------------------------------------

def build_cap(coll):
    """Tile pixel corner coords (col 0..24, row 0..28); the shell fills rows 0-12 at the tile's bottom (rows 16-28).
    Sections across X per plan row (pchip-free: the extents are a clean D), arch height rising to the south lip."""
    sp = load("newshh-79")
    px = sp["frames"][0]["pixels"]
    ext = inner_extents("newshh-79")  # the shell's inner mask (its ink ring is the game's outline)
    rows = sorted(ext)
    r0, r1 = rows[0], rows[-1] + 1  # 17, 28
    # Material: median of the shell (trim 15/85) is 106; the south skirt (rows 23-27) reads 104-105 in the sprite and
    # faces the camera, so it takes 105 by plan row; the crown's 108-111 is the sheen of a polished shell (D176 F0).
    mats = []
    slot = {}
    for i, (m, rgh, spec) in {104: (0.55, 0.32, 1.0), 105: (0.55, 0.3, 1.0), 106: (0.6, 0.26, 1.0)}.items():
        slot[i] = len(mats)
        mat = common.palette_material(sp, i, "nshh79A", metallic=m, roughness=rgh)
        set_spec(mat, spec)
        mats.append(mat)

    def TX(c):
        return (c - 12) * PX

    def TY(r):
        return (14 - r) * PX

    z0 = Z_B  # same sole as the block it stands on
    zmax = 4.6  # px: the cap stands a little above the stalk's 2.2 at the seam
    inset = 0.1

    def halfw(rf):
        # Linear interpolation of the row extents (pixel edges), inset for the game's ink.
        rr = min(max(rf - 0.5, r0), r1 - 1)
        a = int(math.floor(rr))
        b = min(a + 1, r1 - 1)
        t = rr - a
        la, ra_ = ext[a]
        lb, rb = ext[b]
        left = la + (lb - la) * t
        right = ra_ + (rb - ra_) * t
        return (left + right) / 2, (right - left) / 2 - inset

    bm = bmesh.new()
    stations = []
    # North rim rounded: rows r0 .. r1, crown height a quarter ellipse from the north rim to the middle, then level,
    # then a rounded lip (radius 1.6 px) at the south face.
    nrow = 40
    for k in range(nrow + 1):
        t = k / nrow
        rf = r0 + 0.25 + (r1 - 0.05 - (r0 + 0.25)) * t
        cen, w = halfw(rf)
        u = (rf - r0) / 6.0  # 0..1 over the north half
        hn = math.sqrt(max(0.0, 1 - (1 - min(u, 1.0)) ** 2))
        lip = 1.6
        dl = (r1 - rf) / lip
        hs = math.sqrt(max(0.0, 1 - (1 - min(dl, 1.0)) ** 2)) if dl < 1 else 1.0
        zt = z0 + (zmax - z0) * (0.18 + 0.82 * hn) * (0.55 + 0.45 * hs)
        stations.append((cen, rf, max(w * (0.75 + 0.25 * hn), 0.3), zt))
    rings = []
    for cen, rf, w, zt in stations:
        ring = [bm.verts.new((TX(cen + x), TY(rf), z * PX)) for x, z in d_section(w, z0, zt, 24, n=2.6)]
        rings.append(ring)
    m = len(rings[0])
    for ra, rb in zip(rings, rings[1:]):
        for k in range(m):
            j = (k + 1) % m
            bm.faces.new((ra[k], ra[j], rb[j], rb[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bm.normal_update()
    for f in bm.faces:
        cen = f.calc_center_median()
        r = 14 - cen.y / PX
        f.material_index = slot[104 if f.normal.y < -0.85 else 105 if r > 23.2 else 106]
        f.smooth = abs(f.normal.y) < 0.95
    return mesh_obj(coll, "newshh-79", bm, mats), sp


# --- the spore orbs ------------------------------------------------------------------------------------------------

ORB_PAL = {"newshh-89": (198, 196, 194), "newshh-127": (196, 195, 194), "newshh-91": (195, 194, 193)}


def build_orb(coll, name):
    sp = load(name)
    px = sp["frames"][0]["pixels"]
    # Inner disc: every colour pixel (the ink ring 1/32-34 left to the game's outline; newshh-91 has none).
    pts = [(c, r) for r, row in enumerate(px) for c, v in enumerate(row) if v >= 192 or v in (46, 47)]
    c0 = min(c for c, _ in pts)
    c1 = max(c for c, _ in pts) + 1
    r0 = min(r for _, r in pts)
    r1 = max(r for _, r in pts) + 1
    ink = name != "newshh-91"
    a = (c1 - c0) / 2 + (0.15 if ink else 0.0)
    b = (r1 - r0) / 2 + (0.15 if ink else 0.0)
    cx, cy = ((c0 + c1) / 2 - 12) * PX, (14 - (r0 + r1) / 2) * PX
    # Major colour: the trimmed median of each orb's green (89: 198, 127: 196, 91: 195), the lower hemisphere a step
    # darker and the underside two (latitude bands: palette rows the sphere can't shade itself into, D176).
    mats, slot = [], {}
    top_i, mid_i, low_i = ORB_PAL[name]
    for i, (m, rgh) in {low_i: (0.0, 0.42), mid_i: (0.0, 0.36), top_i: (0.0, 0.3)}.items():
        slot[i] = len(mats)
        mat = common.palette_material(sp, i, name + "A", metallic=m, roughness=rgh)
        set_spec(mat, 1.0)
        mats.append(mat)
    bm = bmesh.new()
    res = bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=18, radius=1.0)
    c = 0.97 * min(a, b)
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * a * PX, cy + v.co.y * b * PX, v.co.z * c * PX))
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        f.material_index = slot[low_i if n.z < -0.45 else mid_i if n.z < -0.02 else top_i]
        f.smooth = True
    return mesh_obj(coll, name, bm, mats), sp


# --- the thorn pod: assembly-newshh-77 (77 over 115) ---------------------------------------------------------------
# Grid of both pieces: 24 x 56 px (77 rows 0-27, 115 rows 28-55), centre at the origin. The pod: an olive head
# (rows 6-28) under a raised green hood with a ridge, a green brow arch, a pale chin knob and a green collar, then a
# 12-facet olive spike to the nose at row 53. Closed lens sections (round top, flatter round underside), level.
THORN_HEAD_END = 27.9
HOOD_ROWS = (6.6, 14.8)
ARCH = [(8.6, 21.4), (9.4, 19.6), (10.8, 18.0), (12.5, 17.5), (14.4, 17.9), (15.7, 19.4), (16.6, 21.3)]
COLLAR_ROWS = (25.0, 27.9)


def smooth_profile(ext, rows, k=(1, 2, 3, 2, 1)):
    """Row extents -> smoothed (centre, half width) per row centre: no pixel staircase."""
    raw = {r: ((a + b) / 2, (b - a) / 2) for r, (a, b) in ext.items()}
    out = {}
    h = len(k) // 2
    for r in rows:
        sc = sw = sk = 0.0
        for j, kk in enumerate(k):
            q = r + j - h
            if q in raw:
                sc += kk * raw[q][0]
                sw += kk * raw[q][1]
                sk += kk
        out[r] = (sc / sk, sw / sk)
    return out


def build_thorn(coll):
    s77, s115 = load("newshh-77"), load("newshh-115")
    sp = s77
    sp["colors"].update(s115["colors"])
    px = s77["frames"][0]["pixels"] + s115["frames"][0]["pixels"]
    GH = 56

    def TX(c):
        return (c - 12) * PX

    def TY(r):
        return (GH / 2 - r) * PX

    ext = inner_extents("newshh-77")
    ext.update({r + 28: e for r, e in inner_extents("newshh-115").items()})
    rows = sorted(ext)
    prof = smooth_profile(ext, rows)
    xs = [r + 0.5 for r in rows]
    import bisect

    def interp(rf, idx):
        rf = min(max(rf, xs[0]), xs[-1])
        i = min(bisect.bisect_right(xs, rf) - 1, len(xs) - 2)
        t = (rf - xs[i]) / (xs[i + 1] - xs[i])
        return prof[rows[i]][idx] * (1 - t) + prof[rows[i + 1]][idx] * t

    mats, slot = [], {}
    # Major colours (trimmed medians): head olive 37, spike 42 lit / 37 shaded (its facet ramp, ridge 44), hood 197,
    # collar 197, arch 195, chin 43, underside 35.
    table = {35: (0.2, 0.55), 37: (0.25, 0.5), 39: (0.25, 0.45), 42: (0.25, 0.42), 43: (0.25, 0.4), 44: (0.25, 0.4),
             195: (0.3, 0.3), 197: (0.3, 0.28), 201: (0.3, 0.25)}
    for i, (m, rgh) in table.items():
        slot[i] = len(mats)
        mats.append(common.palette_material(sp, i, "nshh77A", metallic=m, roughness=rgh))

    def head_h(rf, w):
        u = min(max((rf - rows[0]) / 2.6, 0.0), 1.0)
        return min(3.3, 0.62 * w) * (0.55 + 0.45 * math.sqrt(1 - (1 - u) ** 2))

    def head_z(c, rf):
        cen, w = interp(rf, 0), interp(rf, 1) - 0.1
        x = min(abs(c - cen) / max(w, 0.1), 1.0)
        return head_h(rf, w) * (1 - x ** 2.3) ** (1 / 2.3)

    bm = bmesh.new()
    sides = 28
    hrings = []
    r_start, r_end = rows[0] + 0.15, THORN_HEAD_END
    nh = 44
    for k in range(nh + 1):
        rf = r_start + (r_end - r_start) * k / nh
        cen, w = interp(rf, 0), interp(rf, 1) - 0.1
        u = min((rf - rows[0]) / 2.0, 1.0)
        w *= math.sqrt(max(1 - (1 - u) ** 2, 0.03))
        h = head_h(rf, w)
        ring = []
        for j in range(sides):
            th = 2 * math.pi * j / sides
            cs, sn = math.cos(th), math.sin(th)
            x = w * math.copysign(abs(cs) ** (2 / 2.3), cs)
            z = (h if sn > 0 else 0.7 * h) * math.copysign(abs(sn) ** (2 / 2.3), sn)
            ring.append(bm.verts.new((TX(cen + x), TY(rf), z * PX)))
        hrings.append(ring)
    srings = []
    ns = 30
    tipr = rows[-1] + 0.9
    s0 = 27.6
    for k in range(ns + 1):
        rf = s0 + (tipr - 0.4 - s0) * k / ns
        cen, w = interp(rf, 0), interp(rf, 1) - 0.05
        w = max(w, 0.08)
        h = min(3.6, 0.62 * w)
        ring = []
        for j in range(12):
            th = 2 * math.pi * j / 12 + math.pi / 2  # a vertex on the top ridge
            cs, sn = math.cos(th), math.sin(th)
            ring.append(bm.verts.new((TX(cen + w * cs), TY(rf), (h if sn > 0 else 0.7 * h) * sn * PX)))
        srings.append(ring)

    def strip(rs, n, smooth):
        out = []
        for ra, rb in zip(rs, rs[1:]):
            for j in range(n):
                f = bm.faces.new((ra[j], ra[(j + 1) % n], rb[(j + 1) % n], rb[j]))
                f.smooth = smooth
                out.append(f)
        return out

    head_faces = strip(hrings, sides, True)
    head_faces.append(bm.faces.new(list(reversed(hrings[0]))))
    head_faces.append(bm.faces.new(hrings[-1]))
    spike_faces = strip(srings, 12, False)
    spike_faces.append(bm.faces.new(list(reversed(srings[0]))))
    tipv = bm.verts.new((TX(interp(tipr, 0)), TY(tipr), 0.0))
    for j in range(12):
        f = bm.faces.new((srings[-1][j], srings[-1][(j + 1) % 12], tipv))
        f.smooth = False
        spike_faces.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    for f in head_faces:
        f.material_index = slot[35 if f.normal.z < -0.3 else 37]

    def raise_region(faces, d, mat):
        faces = [f for f in faces if f.is_valid]
        if not faces:
            return []
        ret = bmesh.ops.extrude_face_region(bm, geom=faces)
        top = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMFace)]
        verts = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
        bm.normal_update()
        topset = set(top)
        for v in verts:
            n = Vector()
            for f in v.link_faces:
                if f in topset:
                    n += f.normal
            if n.length > 0:
                v.co += n.normalized() * d * PX
        for f in top:
            f.material_index = mat
            f.smooth = True
        bm.normal_update()
        for e in ret["geom"]:
            if isinstance(e, bmesh.types.BMEdge):
                for f in e.link_faces:
                    if f not in topset:
                        f.material_index = mat
        return top

    def fc(f):
        cen = f.calc_center_median()
        return cen.x / PX + 12, GH / 2 - cen.y / PX

    # Hood: rows 6.6-14.8, full width over the crown, its lower edge a V narrowing to the ridge at col 12.5.
    def in_hood(c, r):
        if not (HOOD_ROWS[0] - 1 <= r <= HOOD_ROWS[1]):
            return False
        if r < 9.8:
            return True
        half = 4.2 * (HOOD_ROWS[1] - r) / (HOOD_ROWS[1] - 9.8) + 0.8
        return abs(c - 12.6) <= half

    # The hood is its own plate conforming to the head (0.45 px proud, its sole 0.4 px inside the head), lofted
    # row by row so its V edge is a clean line, not the head mesh's face steps.
    def hood_half(r):
        cen, w = interp(r, 0), interp(r, 1) - 0.1
        if r < 9.8:
            return cen, w * 0.97
        return cen, min(w * 0.97, 4.2 * (HOOD_ROWS[1] - r) / (HOOD_ROWS[1] - 9.8) + 0.5)

    hr = []
    nr, nc = 26, 16
    for k in range(nr + 1):
        r = HOOD_ROWS[0] + (HOOD_ROWS[1] - HOOD_ROWS[0]) * k / nr
        cen, hw = hood_half(r)
        hw = max(hw, 0.25)
        top, bot = [], []
        for j in range(nc + 1):
            c = cen - hw + 2 * hw * j / nc
            zs = head_z(c, r)
            top.append(bm.verts.new((TX(c), TY(r), (zs + 0.45) * PX)))
            bot.append(bm.verts.new((TX(c), TY(r), (zs - 0.4) * PX)))
        hr.append(top + list(reversed(bot)))
    hm = len(hr[0])
    hood_faces = []
    for ra, rb in zip(hr, hr[1:]):
        for j in range(hm):
            hood_faces.append(bm.faces.new((ra[j], ra[(j + 1) % hm], rb[(j + 1) % hm], rb[j])))
    hood_faces.append(bm.faces.new(list(reversed(hr[0]))))
    hood_faces.append(bm.faces.new(hr[-1]))
    for f in hood_faces:
        f.material_index = slot[197]
        f.smooth = True
    # Collar ring: rows 25-27.9, all round the top half.
    collar = [f for f in head_faces if f.is_valid and f.normal.z > -0.2
              and COLLAR_ROWS[0] <= fc(f)[1] <= COLLAR_ROWS[1]]
    raise_region(collar, 0.4, slot[197])

    # Hood ridge (201) and brow arch (195): round pipes lying on the head; chin knob (43).
    def pipe(points, rad, mat, lift=0.15):
        fine = catmull(points, 0.35)
        rings = []
        for i, (c, r) in enumerate(fine):
            a, b = fine[max(i - 1, 0)], fine[min(i + 1, len(fine) - 1)]
            t = Vector((TX(b[0]) - TX(a[0]), TY(b[1]) - TY(a[1]), 0)).normalized()
            nrm = Vector((0, 0, 1)).cross(t).normalized()
            z = head_z(c, r) + lift + (0.45 if in_hood(c, r) else 0.0)
            cen = Vector((TX(c), TY(r), z * PX))
            k = 1.0 if 0 < i < len(fine) - 1 else 0.35
            rings.append([bm.verts.new(cen + rad * k * PX * (math.cos(2 * math.pi * j / 10) * nrm
                                                             + math.sin(2 * math.pi * j / 10) * Vector((0, 0, 1))))
                          for j in range(10)])
        faces = []
        for ra, rb in zip(rings, rings[1:]):
            for j in range(10):
                faces.append(bm.faces.new((ra[j], ra[(j + 1) % 10], rb[(j + 1) % 10], rb[j])))
        faces.append(bm.faces.new(list(reversed(rings[0]))))
        faces.append(bm.faces.new(rings[-1]))
        for f in faces:
            f.material_index = mat
            f.smooth = True

    pipe([(12.6, 6.9), (12.6, 9.0), (12.6, 11.5), (12.6, 14.4)], 0.6, slot[201], lift=0.0)
    pipe(ARCH, 0.75, slot[195], lift=0.1)
    knob = blob(bm, 0, 0, 1.6, 1.3, 1.0, -1.0, segs=16, rings=8)
    zk = head_z(11.5, 23.2)
    for f in knob:
        f.material_index = slot[43]
    for v in {v for f in knob for v in f.verts}:
        v.co.x += TX(11.5) - X(0)
        v.co.y += TY(23.2) - Y(0)
        v.co.z += (zk - 0.2) * PX

    # Spike facets: the sprite's own olive ramp by facet (lit west 42, ridge 44, east 37, under 35).
    for f in spike_faces:
        n = f.normal
        if n.z < -0.2:
            f.material_index = slot[35]
        elif n.x < -0.3:
            f.material_index = slot[42]
        elif n.x > 0.3:
            f.material_index = slot[37]
        else:
            f.material_index = slot[44 if f.calc_center_median().x < TX(12.6) else 39]
    ob = mesh_obj(coll, "assembly-newshh-77", bm, mats)
    return ob, sp


# --- exports: each piece centred on its own tile, with its outline shell ---------------------------------------------

def _tri(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def _outline(shell, name):
    shell.name = shell.data.name = f"{name}_outline"
    shell["tyrian_outline"] = True
    shell.hide_render = True
    return shell


def _export(objs, name):
    data = load(name)
    common.export_sprite_model(WT, objs, f"enemies/{name}", data["sprites"])


def export_block():
    """assembly-newshh-125: the block cut into newshh-85, -87, -123, -125."""
    coll = common.reset_collection("assembly-newshh-125")
    _, sprite = load_block()
    block = build_block(coll, sprite)
    print("assembly-newshh-125: triangles", _tri(block))
    shell = shell_of(coll, block, 3600)
    layout = [(name, c0 + 12 - W / 2, r0 + 14 - H / 2) for name, c0, r0 in BLOCK]
    parts = split_pieces(block, layout, coll)
    shells = split_pieces(shell, layout, coll, cap=False)
    for name, _, _ in layout:
        _export([parts[name], _outline(shells[name], name)], name)
        parts[name].hide_render = True


def export_cap():
    coll = common.reset_collection("newshh-79")
    cap, _ = build_cap(coll)
    print("newshh-79: triangles", _tri(cap))
    _export([cap, _outline(shell_of(coll, cap, 1200), "newshh-79")], "newshh-79")


def export_orb(name):
    coll = common.reset_collection(name)
    o, _ = build_orb(coll, name)
    print(f"{name}: triangles", _tri(o))
    _export([o, _outline(shell_of(coll, o, 1200), name)], name)


def export_thorn():
    coll = common.reset_collection("assembly-newshh-77")
    thorn, _ = build_thorn(coll)
    print("assembly-newshh-77: triangles", _tri(thorn))
    shell = shell_of(coll, thorn, 1600)
    layout = [("newshh-77", 0, -14), ("newshh-115", 0, 14)]
    parts = split_pieces(thorn, layout, coll)
    shells = split_pieces(shell, layout, coll, cap=False)
    for name, _, _ in layout:
        _export([parts[name], _outline(shells[name], name)], name)
        parts[name].hide_render = True
