"""Vent block with a gun (newshc.shp size 2, frames 39/41/43), design A (D65 hard surface).

IDENTITY: a FIXED GROUND STRUCTURE, a gun emplacement standing on the blue tiled floor of the
twin-pillar machine (assembly-newshc-283). Type e1-3:143: mv(0,0), no acceleration, turret 144
every 30 ticks, armour 15, launchedBy []. It stands on the floor; nothing about it flies.

Reading of the sprite (24x28, a full tile; pixel (c, r) covers [c, c+1] x [r, r+1], r down):
- Floor round it: 101/102 tiles and 99/100 grout over a dark 96-98 slab, traced pixel by pixel
  the way the machine's floor is (same heights and finishes). Dark floor in the tile's edge ring
  counts as ink (sprite_mask.py) and the slab stops inside it. Built only as an occluder for the
  AO bake and deleted before export, and left out of the outline shell (D130, as D86's dirt): it
  is the tile's ground, which the game draws in HD, and it showed as a box of pixel tiles.
- The block: a battered armoured housing, its ink at col 1 / col 20 / row 1 / row 24, chamfered
  back corners (rows 2-4). The flanks slope in (left cols 2-5 shade 4-5-6 toward the top, right
  cols 17-19 darker 4-3: lighting from the upper left on sloped walls, not paint). Panel seams cross
  both flanks at rows 7-8 and 13-14 (the 2/3 notches at cols 4-5 and 17-18): three armour bands
  with a modelled gap between them.
- The top plate (7, cols 6-16, rows 2-14), its left chamfer catching the light (col 6, 9/10 =
  sheen), cut by two vent slots (cols 8-14; rows 4-7 and 11-13) over a dark interior (4). Each
  slot holds a louvre of heating bars, one per pixel row; per frame the bars glow from the front
  row back (39: upper slot's front bar dark red; 41: two upper bars and the lower front bar; 43:
  three upper bars, two lower). Their colour is the frame's pixels: each bar in three segments
  (cols 9-10, 11-12, 13-14), the hot middle orange where the sprite has 121/122/123.
- The front (rows 14-24): an apron sloping from the plate's lip down to the floor. Ribs run down
  it at cols 7, 9, 14 and 16 (their tops are the bright J curves at rows 14-17); from row 20 the
  apron splits into claw-like fingers (dark slots at cols 6, 8, 15, 17). In the middle (cols
  10-13) a gun channel: dark walls at cols 10 and 13 and the gun's barrel in it at cols 11-12, its
  bright breech/mantlet at rows 14-17 and its muzzle (dark) at rows 22-23. The gun points south,
  at the player.

Colours (median palette index per region, darkest shading / brightest highlights left out):
body 5 (the lit left flank and apron; the right flank's 3-4 is its shadow side), plate 7, ribs 5,
slot interior 4, gun channel 3, mantlet and barrel 7, muzzle brake 5, bolt heads 8; floor 97/99/100/101/102.

  Blender -b -P newshc-39.py -- [--views DIR] [--no-bake]
Exports public/models/enemies/newshc-39.glb and src/render/spriteModels/newshc-39.json.
"""

import json
import math
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path("/Users/dlomibao/projects/tyrian-scratch/e1-enemies-4/newshc-39/final")  # bake scratch + stats only
NAME = "newshc-39"
TAG = "nshc39A"
PX = 1 / 12
W, H = 24, 28
FRAMES = (39, 41, 43)
FLOOR_IDX = set(range(96, 103))

# palette index -> (metallic, roughness, emission strength)
PROPS = {
    # satin: the body (5) rough and only half metallic, so the apron and flanks stay the sprite's
    # mid grey under the game's lights instead of a pale ramp; the plate (7) is the light part
    3: (0.15, 0.8, 0), 4: (0.2, 0.75, 0), 5: (0.2, 0.74, 0), 6: (0.3, 0.6, 0), 7: (0.45, 0.42, 0),
    8: (0.5, 0.36, 0),
    97: (0.25, 0.75, 0), 99: (0.25, 0.7, 0), 100: (0.25, 0.7, 0), 101: (0.3, 0.6, 0), 102: (0.3, 0.6, 0),
}
GLOW_EM = {113: 1.5, 114: 2.0, 115: 2.5, 116: 3.0, 117: 3.5, 118: 4.0, 119: 4.5, 121: 5.0, 122: 5.5, 123: 6.0}

# --- block dimensions (sprite px; h up) -------------------------------------------------------------
TOP = 6.4          # top of the armoured body (the plate sits on it)
PLATE_TOP = 7.4    # top of the plate (slot depth = 1 px)
GAPS = ((7.65, 7.95), (13.65, 13.95))   # panel seams between the three bands (rows 7-8, 13-14)
SLOPE0 = 17.5      # the plate's lip (rows 14-17, the sprite's light 7-12 band) ends; the apron starts
TOE_H = 0.7        # height of the toe lip at row 24


def apron_h(r):
    """Height of the apron surface at row r (flat lip to SLOPE0, then about 41 degrees to the toe)."""
    if r <= SLOPE0:
        return TOP
    return TOP - (r - SLOPE0) * (TOP - TOE_H) / (24.0 - SLOPE0)


# base at the inner edge of the block's ink (D74): rear row 2, sides cols 2 / 20, toe row 24
BASE = [(5.0, 2.0), (17.0, 2.0), (20.0, 5.0), (20.0, 24.0), (2.0, 24.0), (2.0, 5.0)]
TOPP = [(6.4, 2.3), (16.0, 2.3), (17.0, 3.3), (17.0, SLOPE0), (5.5, SLOPE0), (5.5, 3.1)]


class PxMesh:
    """A bmesh in sprite px whose faces carry palette indices."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.pal = self.bm.faces.layers.int.new("pal")

    def hull(self, pts, pal, bevel=0.0):
        bm = bmesh.new()
        vs = [bm.verts.new(p) for p in pts]
        res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(bm, geom=junk, context="VERTS")
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=list(bm.verts), edges=list(bm.edges))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if bevel > 0:
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect="EDGES",
                            profile=0.5, clamp_overlap=True)
        self.add(bm, pal)
        bm.free()

    def add(self, src, pal):
        me = bpy.data.meshes.new("tmp")
        src.to_mesh(me)
        n0 = len(self.bm.faces)
        self.bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        self.bm.faces.ensure_lookup_table()
        for f in list(self.bm.faces)[n0:]:
            f[self.pal] = pal

    def tube(self, path, rad, pal, n=16, caps=True):
        """A tube through points (c, r, h) with radius per point."""
        bm = bmesh.new()
        pts = [Vector(p) for p in path]
        rings = []
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            a = Vector((0, 0, 1)) if abs(t.x) > 0.7 else Vector((1, 0, 0))  # a frame for any axis
            b = t.cross(a).normalized()
            a = b.cross(t).normalized()
            rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / n) + b * math.sin(2 * math.pi * k / n)) * rad[i])
                          for k in range(n)])
        for r0, r1 in zip(rings, rings[1:]):
            for k in range(n):
                j = (k + 1) % n
                bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
        if caps:
            bm.faces.new(list(reversed(rings[0])))
            bm.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self.add(bm, pal)
        bm.free()


def frustum_pts(inset=0.0, top=TOP):
    pts = []
    for c, r in BASE:
        cc = c + (inset if c < 12 else -inset)
        rr = r + inset if r < 12 else r - inset
        pts.append((cc, rr, 0.0))
    for c, r in TOPP:
        cc = c + (inset if c < 12 else -inset)
        rr = r + inset if r < 8 else r
        pts.append((cc, rr, top - inset))
    # the toe: a short vertical lip at the apron's foot
    for c in (2.0 + inset, 20.0 - inset):
        pts.append((c, 24.0 - inset, TOE_H))
    return pts


def clipped_hull(pts, r0, r1):
    """Points of the convex hull of pts clipped to rows r0..r1 (for a band)."""
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    for rr, keep_hi in ((r0, True), (r1, False)):
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, rr, 0), plane_no=(0, 1, 0),
                               clear_inner=keep_hi, clear_outer=not keep_hi)
    out = [tuple(v.co) for v in bm.verts]
    bm.free()
    return out


def prism_pts(poly, h0, h1, ch):
    """Points of a chamfered prism: straight sides to h1-ch, then a 45-degree chamfer."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    pts = [(c, r, h0) for c, r in poly] + [(c, r, h1 - ch) for c, r in poly]
    for c, r in poly:
        dx, dy = cx - c, cy - r
        pts.append((c + ch * (1 if dx > 0 else -1), r + ch * (1 if dy > 0 else -1), h1))
    return pts


def box_pts(c0, c1, r0, r1, h0, h1):
    return [(c, r, h) for c in (c0, c1) for r in (r0, r1) for h in (h0, h1)]


# --- the parts -------------------------------------------------------------------------------------

def body(m):
    full = frustum_pts()
    edges = [1.0] + [g for gap in GAPS for g in gap] + [25.0]
    for r0, r1 in zip(edges[::2], edges[1::2]):
        m.hull(clipped_hull(full, r0, r1), 5, bevel=0.14)
    m.hull(frustum_pts(inset=0.28), 5)  # the core seen in the seams


def plate():
    m = PxMesh("plate")
    # carried down over rows 14-17 as the light lip the sprite shows (7-12) before the apron
    poly = [(6.9, 2.4), (15.8, 2.4), (16.6, 3.2), (16.6, SLOPE0 - 0.1), (6.0, SLOPE0 - 0.1), (6.0, 3.3)]
    m.hull(prism_pts(poly, TOP - 0.2, PLATE_TOP, 0.4), 7, bevel=0.08)
    return m


def slot_cutters():
    m = PxMesh("slotcut")
    for r0, r1 in ((4.0, 8.0), (11.0, 14.0)):
        # straight walls into the body top, a 45-degree machined rim at the plate's surface
        pts = box_pts(8.0, 15.0, r0, r1, TOP - 0.01, PLATE_TOP - 0.25)
        pts += [(c, r, PLATE_TOP + 0.6) for c in (7.15, 15.85) for r in (r0 - 0.85, r1 + 0.85)]
        n0 = len(m.bm.faces)
        m.hull(pts, 4)
        # the machined rim (the slanted faces) stays plate; the walls and floor are the dark slot
        m.bm.faces.ensure_lookup_table()
        for f in list(m.bm.faces)[n0:]:
            f.normal_update()
            if 0.2 < abs(f.normal.z) < 0.98:
                f[m.pal] = 7
    return m


def apron_cutters():
    """Finger slots in the apron's foot (cols 6, 8, 15, 17 from row 20) and the gun channel."""
    m = PxMesh("aproncut")
    for c in (6.5, 8.5, 15.5, 17.5):
        pts = []
        for r in (20.2, 25.0):
            for cc in (c - 0.32, c + 0.32):
                pts += [(cc, r, max(apron_h(r) - 1.1, 0.35)), (cc, r, apron_h(r) + 4)]
        m.hull(pts, 3)
    for r0, r1 in ((SLOPE0 - 0.6, 20.0), (20.0, 25.0)):
        pts = []
        for r in (r0, r1):
            for cc in (CH0, CH1):
                pts += [(cc, r, max(apron_h(r) - 1.5, 0.4)), (cc, r, apron_h(r) + 4)]
        m.hull(pts, 3)
    return m


CH0, CH1 = 10.08, 13.92   # the gun channel (its dark walls at cols 10 and 13)
GUN_C = 12.0              # the gun (cols 11-12)


def apron_details(m):
    # ribs down the apron (cols 7, 9, 14, 16), ending in claw teeth at the toe
    for c in (7.5, 9.5, 14.5, 16.5):
        pts = []
        for r in (SLOPE0 - 0.3, 23.5):
            for cc in (c - 0.42, c + 0.42):
                pts += [(cc, r, apron_h(r) - 0.6), (cc, r, apron_h(r) + 0.2)]
            for cc in (c - 0.24, c + 0.24):
                pts.append((cc, r, apron_h(r) + 0.34))
        # the tooth: the rib's end turns down over the toe
        for cc in (c - 0.36, c + 0.36):
            pts += [(cc, 24.25, 0.05), (cc, 24.05, 1.0), (cc, 23.6, 0.05)]
        m.hull(pts, 5, bevel=0.06)
    # the gun on the lip: a trunnion mantlet (bright, rows 15-17) between two dark lugs (cols 10
    # and 13), the barrel (5) run down over the channel, a dark muzzle brake at rows 22-23
    GH = PLATE_TOP + 0.75
    for c0, c1 in ((CH0 - 0.05, CH0 + 0.75), (CH1 - 0.75, CH1 + 0.05)):
        pts = box_pts(c0, c1, 15.0, 17.2, PLATE_TOP - 0.1, GH + 0.3)
        pts += [(c, r, GH + 0.75) for c in (c0 + 0.12, c1 - 0.12) for r in (15.6, 16.6)]
        m.hull(pts, 4, bevel=0.06)
    m.tube([(CH0 + 0.75, 16.1, GH), (CH0 + 0.85, 16.1, GH), (CH1 - 0.85, 16.1, GH), (CH1 - 0.75, 16.1, GH)],
           [0.8, 0.98, 0.98, 0.8], 7, n=20)
    a = Vector((GUN_C, 16.1, GH))
    b = Vector((GUN_C, 23.45, 3.0))
    d = (b - a).normalized()

    def at(t):
        return tuple(a + d * t)
    L = (b - a).length
    m.tube([at(0.4), at(1.2), at(L - 1.55)], [0.72, 0.62, 0.56], 5, n=16)                        # barrel
    m.tube([at(L - 1.65), at(L - 1.5), at(L - 0.1), at(L)], [0.6, 0.74, 0.74, 0.64], 3, n=16)     # brake
    # the toe plate under the gun channel (a dark sill the muzzle stands over)
    m.hull(box_pts(CH0 + 0.02, CH1 - 0.02, 22.0, 24.0, 0.0, 0.62), 3, bevel=0.05)


def rear_details(m):
    """A bolted access hatch on the rear wall and lifting eyes on the plate."""
    # rear wall plane: r from 1.5 (h0) to 2.0 (h TOP)
    def wr(h):
        return 2.0 + 0.3 * h / TOP
    pts = []
    for h in (1.2, 4.8):
        for c in (8.0, 14.0):
            pts += [(c, wr(h) - 0.18, h), (c, wr(h) + 0.3, h)]
    m.hull(pts, 5, bevel=0.06)
    for c in (8.5, 13.5):  # hinge knuckles
        m.tube([(c - 0.6, wr(5.05) - 0.12, 5.05), (c + 0.6, wr(5.05) - 0.12, 5.05)], [0.22, 0.22], 6, n=10)
    # countersunk bolt heads on the plate's middle bar and front corners (flush; no sprite feature)
    for c, r in ((7.0, 9.5), (15.6, 9.5), (7.0, 13.4), (15.6, 13.4), (7.0, 5.9), (15.6, 5.9),
                 (7.0, 16.4), (15.6, 16.4)):
        pts = []
        for k in range(6):
            a = math.pi / 3 * k + math.pi / 6
            for rr, h in ((0.3, PLATE_TOP - 0.05), (0.22, PLATE_TOP + 0.1)):
                pts.append((c + rr * math.cos(a), r + rr * math.sin(a), h))
        m.hull(pts, 8)
    # lifting eyes on the plate's rear corners
    for c in (7.4, 15.2):
        m.hull(box_pts(c - 0.3, c + 0.3, 2.85, 3.45, PLATE_TOP - 0.1, PLATE_TOP + 0.35), 6, bevel=0.07)


def floor(m, g, inner):
    slab = set()
    for r in range(H):
        for c in range(W):
            if inner[r][c] == "o" and g[r][c] in FLOOR_IDX:
                continue
            slab.add((c, r))
    floor_slab(m, slab)
    for idx, h in ((99, 0.42), (100, 0.42), (101, 0.62), (102, 0.62)):
        cells = [(c, r) for (c, r) in slab if g[r][c] == idx]
        for a, b, cc, d in rects(cells):
            m.hull(prism_pts([(a + 0.04, b + 0.04), (cc - 0.04, b + 0.04), (cc - 0.04, d - 0.04), (a + 0.04, d - 0.04)],
                             0.2, h, 0.08), idx)


def floor_cells(g, inner):
    return {(c, r) for r in range(H) for c in range(W) if not (inner[r][c] == "o" and g[r][c] in FLOOR_IDX)}


def floor_slab(m, slab):
    for a, b, cc, d in rects(slab):
        m.hull(box_pts(a + 0.002, cc - 0.002, b + 0.002, d - 0.002, -0.4, 0.28), 97)


def shell_source(g, inner):
    """What the outline shell is made from (D51): the block's plain frustum and the plate (not the
    floor slab, D130), without the ribs, grooves, slots and gun. Built from the detailed model, the shell's
    back faces showed in the narrow grooves between the ribs as black specks; this has no groove for
    them to show in, and the shell only has to trace the silhouette."""
    m = PxMesh("shellsrc")
    m.hull(frustum_pts(), 5)
    poly = [(6.9, 2.4), (15.8, 2.4), (16.6, 3.2), (16.6, SLOPE0 - 0.1), (6.0, SLOPE0 - 0.1), (6.0, 3.3)]
    m.hull(prism_pts(poly, TOP - 0.2, PLATE_TOP, 0.4), 7)
    return m


def rects(cells):
    todo = set(cells)
    out = []
    for r in range(H):
        for c in range(W):
            if (c, r) not in todo:
                continue
            c1 = c
            while (c1 + 1, r) in todo:
                c1 += 1
            r1 = r
            while all((k, r1 + 1) in todo for k in range(c, c1 + 1)):
                r1 += 1
            for rr in range(r, r1 + 1):
                for k in range(c, c1 + 1):
                    todo.discard((k, rr))
            out.append((c, r, c1 + 1, r1 + 1))
    return out


# --- glow louvres, per frame -------------------------------------------------------------------------

SLOT_ROWS = {"upper": (4, 5, 6, 7), "lower": (11, 12, 13)}
SEGS = ((9, 10, 8.2, 10.95), (11, 12, 11.05, 12.95), (13, 14, 13.05, 14.85))


def glow_index(frame_px, r, c0, c1):
    vals = sorted(frame_px[r][c] for c in (c0, c1))
    if all(v < 96 for v in vals):
        return 4
    return max(v for v in vals if v >= 96)  # upper of the two (keep the hot spot)


def louvres(m, frame_px):
    for rows in SLOT_ROWS.values():
        for r in rows:
            for c0, c1, x0, x1 in SEGS:
                idx = glow_index(frame_px, r, c0, c1)
                if idx == 4:
                    idx = -4  # an unlit bar: its own material (the body's 4 gets the bake's UVs)
                pts = []
                for x in (x0, x1):
                    # a bar tilted like a louvre blade: its front edge low, its back edge high
                    pts += [(x, r + 0.12, TOP + 0.55), (x, r + 0.88, TOP + 0.25), (x, r + 0.88, TOP + 0.05),
                            (x, r + 0.12, TOP + 0.35)]
                m.hull(pts, idx, bevel=0.04)


# --- to Blender -------------------------------------------------------------------------------------

MATS = {}


def mat_of(sprite, idx):
    if idx not in MATS:
        if idx < 0:
            met, rough, _ = PROPS[-idx]
            MATS[idx] = common.palette_material(sprite, -idx, TAG + "s", metallic=met, roughness=rough)
        elif idx in GLOW_EM:
            MATS[idx] = common.palette_material(sprite, idx, TAG, metallic=0.1, roughness=0.5,
                                                emission_strength=GLOW_EM[idx])
        else:
            met, rough, _ = PROPS[idx]
            MATS[idx] = common.palette_material(sprite, idx, TAG, metallic=met, roughness=rough)
    return MATS[idx]


def to_object(m, sprite, coll):
    bm = m.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    M = Matrix(((PX, 0, 0, -W / 2 * PX), (0, -PX, 0, H / 2 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    pals = sorted({f[m.pal] for f in bm.faces})
    me = bpy.data.meshes.new(m.name)
    slot = {}
    for p in pals:
        slot[p] = len(me.materials)
        me.materials.append(mat_of(sprite, p))
    for f in bm.faces:
        f.material_index = slot[f[m.pal]]
        f.smooth = False
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(m.name, me)
    coll.objects.link(obj)
    return obj


def boolean(obj, cutter, op="DIFFERENCE"):
    mod = obj.modifiers.new("b", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    mod.solver = "EXACT"
    mod.use_self = True
    mod.material_mode = "TRANSFER"  # cut faces take the cutter's palette (4 slots, 3 channel)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


def load_grid(sprite):
    g = sprite["frames"][0]["pixels"]
    out = subprocess.check_output(["python3", str(WT / "tools" / "sprite_mask.py"), NAME, "--json"], cwd=WT)
    inner = json.loads(out)["masks"]
    return g, inner


def build(sprite, coll):
    g, inner = load_grid(sprite)
    bodym = PxMesh("body")
    body(bodym)
    body_o = to_object(bodym, sprite, coll)
    plate_o = to_object(plate(), sprite, coll)
    sc = to_object(slot_cutters(), sprite, coll)
    ac = to_object(apron_cutters(), sprite, coll)
    for o in (body_o, plate_o):
        boolean(o, sc)
    boolean(body_o, ac)
    for o in (sc, ac):
        bpy.data.objects.remove(o, do_unlink=True)
    det = PxMesh("details")
    apron_details(det)
    rear_details(det)
    det_o = to_object(det, sprite, coll)
    fl = PxMesh("floor")
    floor(fl, g, inner)
    fl_o = to_object(fl, sprite, coll)
    for i, mt in enumerate(fl_o.data.materials):  # own flagged copies: deleted after the bake (D130)
        cp = mt.copy()
        cp["tyrian_floor"] = True
        fl_o.data.materials[i] = cp
    obj = join([body_o, plate_o, det_o], TAG)
    me = obj.data
    for p in me.polygons:
        p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(32))
    glows = []
    for fr in sprite["frames"]:
        gm = PxMesh(f"{TAG}-glow-{fr['index']}")
        louvres(gm, fr["pixels"])
        go = to_object(gm, sprite, coll)
        common.frame_part(go, [fr["index"]])
        glows.append(go)
    return obj, glows, fl_o


def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    bpy.context.view_layer.update()
    T.TINT = (0.97, 0.98, 1.0)
    T.TEXTURED = tuple(range(len(obj.data.materials)))
    try:
        T.bake_maps(obj, out_dir, size=1024, samples=48)
    finally:
        T.TINT, T.TEXTURED = tint, textured


# --- measurement and views (scratch) ---------------------------------------------------------------

def cam(scene, name, loc, look, ortho=None, lens=50):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    c = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return c


def pal_grid(objs, frame):
    deps = bpy.context.evaluated_depsgraph_get()
    rows = []
    for r in range(H):
        row = []
        for c in range(W):
            X, Y = (c + 0.5 - W / 2) * PX, (H / 2 - (r + 0.5)) * PX
            best = None
            for o in objs:
                if "tyrian_frames" in o and frame not in list(o["tyrian_frames"]):
                    continue
                ev = o.evaluated_get(deps)
                hit, loc, nrm, fi = ev.ray_cast(Vector((X, Y, 5.0)), Vector((0, 0, -1)))
                if hit and (best is None or loc.z > best[0]):
                    mat = o.data.materials[o.data.polygons[fi].material_index]
                    best = (loc.z, int(mat.name.split("_")[1]))
            row.append(best[1] if best else -1)
        rows.append(row)
    return rows


def top_mask(objs, path):
    scene = bpy.context.scene
    for o in scene.objects:
        o.hide_render = o not in objs
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    K = 20
    scene.render.resolution_x, scene.render.resolution_y = W * K, H * K
    scene.render.resolution_percentage = 100
    c = cam(scene, "top_mask", (0, 0, 10), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    scene.camera = c
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def lit_views(show, out, tag=""):
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o not in show and o.name != "ground"
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.16, 0.18, 0.2, 1)
    bg.inputs[1].default_value = 0.7
    if "sun" not in bpy.data.objects:
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 3.2
        scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(35), math.radians(-30), math.radians(20))
        fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
        fill.data.energy = 0.9
        scene.collection.objects.link(fill)
        fill.rotation_euler = (math.radians(-60), math.radians(40), 0)
        bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.05))
        gr = bpy.context.active_object
        gr.name = "ground"
        gm = bpy.data.materials.new("ground")
        gm.use_nodes = True
        next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.02, 0.03, 0.05, 1)
        gr.data.materials.append(gm)
    V = 480
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 4.0
    views = {
        "top": ((0, 0, d), 2.6, (0, 0, 0)),
        "side": ((d, 0, 0.25), 2.6, (0, 0, 0.25)),
        "front": ((0, -d, 0.25), 2.6, (0, 0, 0.25)),
        "rear": ((0, d, 0.25), 2.6, (0, 0, 0.25)),
        "q34": ((d * 0.55, -d * 0.6, d * 0.55), None, (0, 0, 0.1)),
        "q34b": ((-d * 0.6, d * 0.55, d * 0.5), None, (0, 0, 0.1)),
        "game": ((0, -d * 0.5, d * 0.95), None, (0, 0, 0.1)),
        "under": ((d * 0.4, -d * 0.5, -d * 0.6), None, (0, 0, 0)),
    }
    for name, (loc, ortho, look) in views.items():
        bpy.data.objects["ground"].hide_render = name in ("under", "side", "front", "rear")
        c = cam(scene, f"v_{name}{tag}", loc, look, ortho=ortho, lens=50)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out / f"v_{name}{tag}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(TAG)
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    obj, glows, fl_o = build(sprite, coll)
    T.cull_hidden(obj)
    obj = join([obj, fl_o], TAG)  # the floor joins only for the bake's occlusion (D130)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons) + sum(
        len(p.vertices) - 2 for g in glows for p in g.data.polygons)
    print(f"{TAG}: {tris} triangles")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        top_mask([obj] + glows, views / "top.png")
        grids = {fr: pal_grid([obj] + glows, fr) for fr in FRAMES}
        (views / "pal.json").write_text(json.dumps(grids))
    fmt = "AUTO"
    for o in bpy.data.objects:
        o.hide_render = False
    if "--no-bake" not in argv:
        bd = HERE / "bake"
        bd.mkdir(parents=True, exist_ok=True)
        bake(obj, bd)
        fmt = "WEBP"
    bm = bmesh.new()  # the floor was the bake's occluder only: not exported (D130)
    bm.from_mesh(obj.data)
    fl = {i for i, mt in enumerate(obj.data.materials) if mt and mt.get("tyrian_floor")}
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in fl], context="FACES")
    bm.to_mesh(obj.data)
    bm.free()
    # after the bake, so the shell's source doesn't shade the AO
    shell_src = to_object(shell_source(*load_grid(sprite)), sprite, coll)
    sh = common.outline_shell(shell_src, coll, voxel=0.01, faces=4000, smooth=6, inside=0.006)
    sh.name = f"{TAG}_outline"
    bpy.data.objects.remove(shell_src, do_unlink=True)
    common.export_sprite_model(WT, [obj, sh] + glows, f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    if views:
        sh.hide_render = True
        for g in glows:
            g.hide_render = True
        for fr, g in zip(FRAMES, glows):
            if fr == 43:
                lit_views([obj, g], views)
        # the top of each frame (glow) for the sheet
        scene = bpy.context.scene
        for fr, g in zip(FRAMES, glows):
            for o in scene.objects:
                if o.type == "MESH":
                    o.hide_render = o not in (obj, g)
            c = cam(scene, f"t{fr}", (0, 0, 4), (0, 0, 0), ortho=H * PX)
            c.rotation_euler = (0, 0, 0)
            scene.render.resolution_x, scene.render.resolution_y = W * 16, H * 16
            scene.camera = c
            scene.render.filepath = str(views / f"top_lit_{fr}.png")
            bpy.ops.render.render(write_still=True)
    (HERE / "stats.json").write_text(json.dumps({"triangles": tris}))


if __name__ == "__main__":
    main()
