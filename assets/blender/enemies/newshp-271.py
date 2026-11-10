"""newshp-271: the twin-cannon ground turret (newshp.shp size 2, frames 271/273/275/277), a
hard-surface rebuild as what it is (D65, D120, D122).

WHAT IT IS: a FIXED GROUND TURRET (type e1-3:197, mv 0,0, launchedBy [], level 1.3; spawned on
ground(25) and ridden on the terrain scroll). The 24 x 28 sprite is a whole tile: the gun mount on a
stone pad. Two cannons point DOWN the screen (south, at the player); the four frames are their recoil:
the muzzle and collar slide back along each barrel into the housing (one model per frame, D17/D46).

Reading the sprite (row/col = sprite pixel; x = column edge, y = row edge, z up, all px):
- Housing (brown 167): cols 3-19, rows 2-11, its back corners cut (row 2 cols 5-17 is the lit back
  chamfer), standing on a blue-grey steel plinth (100) that shows as the 1 px rim round the back
  corners (rows 2-6, cols 2-4 and 18-20).
- Two raised armour ribs (168) run down the deck at cols 7-8 and 14-15 (rows 5-11); between them
  a sight block with a dark blue window (99, rows 6/7-8 cols 9-13) facing the direction of fire,
  then a sloped mantlet (164, rows 9-11) down to the trench.
- The deck either side (rows 5-8) carries an access hatch (164).
- The gun embrasures: U-notches in the deck at cols 4-6 / 16-18, rows 9-11, with the barrel's
  breech (102) lying in them.
- Each gun (cols 1-8 / 14-21): a blue-grey recoil sleeve (101, 5 px wide, its bright middle column
  is sheen) riding in a brown cradle (165): a thin side rail on the west (col 1) and a recuperator
  cylinder on the east (cols 7-8). A brown clamp collar (166) and a box muzzle brake (167, cols 1-7)
  whose top port shows the glowing bore (114); the bore glows on the brake's front face too.
- Red lamps (115) in steel brackets either side of the housing (cols 1-2 / 21-22, rows 7-11).
- At the back (rows 0-1): two blue-grey feed pipes (100) with capped couplings and a brown
  junction box (170) between them.
- The stone pad: pavers coloured from the sprite's own stone pixels (trimmed medians); the dark
  strip between the guns (rows 12-22, 1-2) is a recessed gutter (2).

Recoil per frame (row edges): collar, muzzle brake, bore port
    271: collar 16-18, brake 20-27, port 24-26     273: 15-17, 18-25, 22-24
    275: 14-16, 17-23, port 19-22                  277: 13-14, 15-22, 18-21

Colours: trimmed medians of each region. Satin metal. Highlights are sheen, not geometry.
No texture bake (no textures/newshp-271 folder; see notes). Outline shell (D51) from the turret only,
so the game inks the gun mount and not the tile's square edge. Underside: the pad's flat bottom.

Exports public/models/enemies/newshp-271{,-f2,-f3,-f4}.glb and their spriteModels JSON.

    blender --background --python assets/blender/enemies/newshp-271.py
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "newshp-271"
W, H = 24, 28

# --- heights (px) ----------------------------------------------------------------------------------
Z_PAD = 0.6        # paver top
Z_BED = -0.25      # bedding (joints, gutter floor)
Z_PL0, Z_PL1 = 0.4, 2.0   # plinth
Z_DECK = 7.0       # housing deck
Z_RIB = 8.2        # rib tops
Z_SIGHT = 8.35     # sight block top
ZG = 3.6           # gun axis
R_SLV = 2.45       # recoil sleeve radius
R_BR = 1.45        # breech radius
Z_MZ_TOP = 6.55    # muzzle brake top
Z_MZ_BOT = 0.75

GUNS = [  # (sleeve axis x, breech axis x, notch x0, x1)
    (4.5, 5.5, 4.0, 7.0),
    (17.5, 17.5, 16.0, 19.0),
]
FRAMES = [  # (model, frame, collar (y0, y1), brake (y0, y1), port (y0, y1))
    ("newshp-271", 271, (16.0, 18.0), (20.0, 27.0), (24.0, 26.0)),
    ("newshp-271-f2", 273, (15.0, 17.0), (18.0, 25.0), (22.0, 24.0)),
    ("newshp-271-f3", 275, (14.0, 16.0), (17.0, 23.0), (19.0, 22.0)),
    ("newshp-271-f4", 277, (13.0, 14.0), (15.0, 22.0), (18.0, 21.0)),
]


# --- geometry (helpers in the style of newshp-237.py; candidates for a shared lib) -----------------

def V(x, y, z):
    return ((x - W / 2) / 12, (H / 2 - y) / 12, z / 12)


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def ring(self, pts):
        return [self.bm.verts.new(V(*p)) for p in pts]

    def face(self, vs, mat):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        return f

    def stack(self, rings, mats, top=None, bottom=None):
        vr = [self.ring(r) for r in rings]
        n = len(rings[0])
        for b, (r0, r1) in enumerate(zip(vr, vr[1:])):
            m = mats[min(b, len(mats) - 1)]
            for i in range(n):
                j = (i + 1) % n
                self.face((r0[i], r0[j], r1[j], r1[i]), m)
        if top is not None:
            self.face(vr[-1], top)
        if bottom is not None:
            self.face(list(reversed(vr[0])), bottom)
        return vr

    def hull(self, pts, mat):
        bm = self.bm
        verts = [bm.verts.new(V(*p)) for p in pts]
        res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(bm, geom=junk, context="VERTS")
        live = [v for v in verts if v.is_valid]
        faces = list({f for v in live for f in v.link_faces})
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                                 edges=list({e for f in faces for e in f.edges}))
        live = [v for v in verts if v.is_valid]
        for f in {f for v in live for f in v.link_faces}:
            f.material_index = mat

    def obj(self, name, mats, coll):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in mats:
            me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        return o


def inset(plan, d):
    """Inset a convex CCW-or-CW plan polygon by d (miter)."""
    n = len(plan)
    cx = sum(p[0] for p in plan) / n
    cy = sum(p[1] for p in plan) / n
    out = []
    for i in range(n):
        p0, p1, p2 = plan[i - 1], plan[i], plan[(i + 1) % n]
        ns = []
        for a, b in ((p0, p1), (p1, p2)):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1e-9
            nx, ny = -dy / ln, dx / ln
            mx, my = (a[0] + b[0]) / 2 - cx, (a[1] + b[1]) / 2 - cy
            if nx * mx + ny * my > 0:  # make it point inwards
                nx, ny = -nx, -ny
            ns.append((nx, ny))
        bx, by = ns[0][0] + ns[1][0], ns[0][1] + ns[1][1]
        bl = math.hypot(bx, by) or 1e-9
        bx, by = bx / bl, by / bl
        c = max(0.3, bx * ns[0][0] + by * ns[0][1])
        out.append((p1[0] + bx * d / c, p1[1] + by * d / c))
    return out


def prism(M, plan, levels, mats, top, bottom):
    """levels = [(inset, z), ...] bottom to top."""
    rings = [[(x, y, z) for x, y in (inset(plan, d) if d else plan)] for d, z in levels]
    return M.stack(rings, mats, top=top, bottom=bottom)


def octo(x0, y0, x1, y1, c, cy=None):
    cy = c if cy is None else cy
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + cy), (x1, y1 - cy), (x1 - c, y1), (x0 + c, y1),
            (x0, y1 - cy), (x0, y0 + cy)]


def cbox(M, x0, x1, y0, y1, z0, z1, mat, ch=0.2, chz=None):
    M.hull(T.cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


def tube_y(M, xc, zc, stations, mat, seg=20, cap0=True, cap1=True):
    """A round tube along +y: stations [(y, r)] (r 0: a point)."""
    rings = []
    for y, r in stations:
        rings.append([(xc + r * math.cos(2 * math.pi * k / seg), y, zc + r * math.sin(2 * math.pi * k / seg))
                      for k in range(seg)])
    M.stack(rings, [mat], top=mat if cap1 else None, bottom=mat if cap0 else None)


def frame_solid(M, outer, inner, z0, z1, ch, mat, inner_mat=None):
    """A plate with a hole: outer and inner plans with the same point count and order; outer top edge
    chamfered by ch."""
    ob = M.ring([(x, y, z0) for x, y in outer])
    om = M.ring([(x, y, z1 - ch) for x, y in outer])
    ot = M.ring([(x, y, z1) for x, y in inset(outer, ch)])
    it = M.ring([(x, y, z1) for x, y in inner])
    ib = M.ring([(x, y, z0) for x, y in inner])
    im = inner_mat if inner_mat is not None else mat
    n = len(outer)
    for i in range(n):
        j = (i + 1) % n
        M.face((ob[i], ob[j], om[j], om[i]), mat)
        M.face((om[i], om[j], ot[j], ot[i]), mat)
        M.face((ot[i], ot[j], it[j], it[i]), mat)
        M.face((it[i], it[j], ib[j], ib[i]), im)
        M.face((ib[i], ib[j], ob[j], ob[i]), mat)


def ellipsoid_top(M, xc, yc, z0, rx, ry, rz, mat, seg=20, rings=6):
    rs = []
    for i in range(rings):
        p = (math.pi / 2) * i / rings
        rs.append([(xc + rx * math.cos(p) * math.cos(2 * math.pi * k / seg), yc + ry * math.cos(p) * math.sin(2 * math.pi * k / seg),
                    z0 + rz * math.sin(p)) for k in range(seg)])
    vr = M.stack(rs, [mat], bottom=mat)
    apex = M.bm.verts.new(V(xc, yc, z0 + rz))
    for k in range(seg):
        M.face((vr[-1][k], vr[-1][(k + 1) % seg], apex), mat)


# --- materials -------------------------------------------------------------------------------------

class Pal:
    def __init__(self, sprite, tag):
        self.sp, self.tag = sprite, tag
        self.list, self.slot = [], {}

    def __call__(self, index, key=None, metallic=0.35, roughness=0.5, emission=0.0):
        key = key or str(index)
        if key not in self.slot:
            t = self.tag if key == str(index) else f"{self.tag}_{key}"
            self.list.append(common.palette_material(self.sp, index, t, metallic=metallic, roughness=roughness,
                                                     emission_strength=emission))
            self.slot[key] = len(self.list) - 1
        return self.slot[key]


def stone_index(sprite, x0, y0, x1, y1):
    """Trimmed median of the sprite's stone pixels (index <= 11) under a paver, over all frames."""
    vals = []
    for fr in sprite["frames"]:
        px = fr["pixels"]
        for r in range(max(0, int(y0)), min(H, int(math.ceil(y1)))):
            for c in range(max(0, int(x0)), min(W, int(math.ceil(x1)))):
                v = px[r][c]
                if 3 <= v <= 11:
                    vals.append(v)
    if len(vals) < 4:
        return 5
    vals.sort()
    k = len(vals) // 5
    t = vals[k:len(vals) - k] or vals
    return int(round(sorted(t)[len(t) // 2]))


# --- the stone pad ---------------------------------------------------------------------------------

COURSES = [(0.0, 4.6, [0, 5.5, 11.0, 17.5, 24]), (4.6, 10.2, [0, 3.0, 9.5, 15.0, 21.0, 24]),
           (10.2, 16.4, [0, 4.5, 9.0, 14.0, 19.5, 24]), (16.4, 22.2, [0, 2.5, 9.0, 14.0, 21.0, 24]),
           (22.2, 28.0, [0, 4.0, 9.0, 14.0, 18.5, 24])]
GUTTER = (9.0, 12.0, 14.0, 23.6)   # x0, y0, x1, y1
JOINT = 0.11


def pad(M, P, sprite):
    # bedding slab under the whole tile (its top shows in the joints and the gutter)
    prism(M, [(0, 0), (24, 0), (24, 28), (0, 28)], [(0, -0.7), (0, Z_BED)], [P(2)], P(2), P(2))
    gx0, gy0, gx1, gy1 = GUTTER
    for y0, y1, xs in COURSES:
        for x0, x1 in zip(xs, xs[1:]):
            # pavers in the gutter strip are cut back to its edges
            pieces = [(x0, y0, x1, y1)]
            if x0 < gx1 and x1 > gx0 and y1 > gy0 and y0 < gy1:
                pieces = []
                if y0 < gy0:
                    pieces.append((x0, y0, x1, gy0))
                if y1 > gy1:
                    pieces.append((x0, gy1, x1, y1))
                if x0 < gx0:
                    pieces.append((x0, max(y0, gy0), gx0, min(y1, gy1)))
                if x1 > gx1:
                    pieces.append((gx1, max(y0, gy0), x1, min(y1, gy1)))
            for a0, b0, a1, b1 in pieces:
                e = [JOINT if a0 > 0 else 0.0, JOINT if b0 > 0 else 0.0, JOINT if a1 < 24 else 0.0, JOINT if b1 < 28 else 0.0]
                c = stone_index(sprite, a0, b0, a1, b1)
                plan = [(a0 + e[0], b0 + e[1]), (a1 - e[2], b0 + e[1]), (a1 - e[2], b1 - e[3]), (a0 + e[0], b1 - e[3])]
                prism(M, plan, [(0, Z_BED - 0.05), (0, Z_PAD - 0.14), (0.12, Z_PAD)], [P(c), P(c)], P(c), P(c))


# --- the housing ---------------------------------------------------------------------------------

BODY_PLAN = [(5.0, 2.0), (18.0, 2.0), (20.0, 4.6), (20.0, 12.0), (3.0, 12.0), (3.0, 4.6)]
PLINTH_PLAN = [(4.4, 1.55), (18.6, 1.55), (20.55, 4.3), (20.55, 12.35), (2.45, 12.35), (2.45, 4.3)]


def apply_bool(obj, cutter, op="DIFFERENCE"):
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.new("cut", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.material_mode = "TRANSFER"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.context.view_layer.update()


def housing_body(P, coll, name):
    M = Mesh()
    prism(M, BODY_PLAN, [(0, Z_PL1 - 0.3), (0, Z_DECK - 0.75), (0.75, Z_DECK)], [P(167), P(167)], P(167), P(167))
    body = M.obj(f"{name}_body", P.list, coll)
    # gun embrasures: U-notches in the deck where the breeches lie
    for _sx, bx, nx0, nx1 in GUNS:
        C = Mesh()
        cbox(C, nx0, nx1, 8.8, 13.0, ZG - 0.4, Z_DECK + 3, 0, ch=0.02)
        apply_bool(body, C.obj("cut", [P.list[P(167)]], coll))
    # the mantlet: the deck between the ribs slopes down to the front
    C = Mesh()
    pts = []
    for x in (8.9, 14.1):
        pts += [(x, 9.0, Z_DECK + 0.02), (x, 12.0, 3.4), (x, 12.6, 3.0), (x, 12.6, 12), (x, 9.0, 12)]
    C.hull(pts, 0)
    apply_bool(body, C.obj("cut", [P.list[P(164, "mantlet")]], coll))
    return body


def housing_parts(M, P):
    steel = P(100, metallic=0.5, roughness=0.42)
    prism(M, PLINTH_PLAN, [(0, Z_PL0), (0, Z_PL1 - 0.35), (0.35, Z_PL1)], [steel, steel], steel, steel)
    rib = P(168)
    # armour ribs: raised, chamfered, the front end sloping down to the plinth
    for x0, x1 in ((7.0, 9.0), (14.0, 16.0)):
        prof = [(4.6, Z_DECK - 0.3, False), (5.0, Z_RIB, True), (9.6, Z_RIB, True), (12.15, 5.3, True),
                (12.15, Z_PL1 - 0.2, False), (4.6, Z_PL1, False)]
        pts = []
        for y, z, top in prof:
            if top:
                pts += [(x0, y, z - 0.3), (x0 + 0.3, y, z), (x1 - 0.3, y, z), (x1, y, z - 0.3)]
            else:
                pts += [(x0, y, z), (x1, y, z)]
        M.hull(pts, rib)
    # sight block between the ribs: flat top, sloped window face towards the guns' line of fire
    body = P(164, "sight")
    sx0, sx1 = 8.9, 14.1
    pts = []
    for x in (sx0, sx1):
        pts += [(x, 4.9, Z_DECK - 0.3), (x, 5.2, Z_SIGHT), (x, 6.5, Z_SIGHT), (x, 9.0, Z_DECK + 0.02),
                (x, 9.0, Z_DECK - 0.3)]
    pts += [(sx0 + 0.25, 4.9, Z_SIGHT - 0.25), (sx1 - 0.25, 4.9, Z_SIGHT - 0.25)]
    M.hull(pts, body)
    # the window: dark blue glass set proud of the slope in a thin frame
    glass = P(99, "glass", metallic=0.3, roughness=0.15)
    def on_slope(y, off):
        t = (y - 6.5) / (9.0 - 6.5)
        z = Z_SIGHT + (Z_DECK + 0.02 - Z_SIGHT) * t
        nlen = math.hypot(2.5, Z_SIGHT - Z_DECK)
        ny, nz = (Z_SIGHT - Z_DECK) / nlen, 2.5 / nlen
        return y + ny * off, z + nz * off
    gp = []
    for x in (9.35, 13.65):
        for y in (6.85, 8.75):
            for off in (-0.15, 0.07):
                yy, zz = on_slope(y, off)
                gp.append((x, yy, zz))
    M.hull(gp, glass)
    # deck hatches with bolts
    hatch = P(164)
    bolt = P(169, "bolt")
    for x0, x1 in ((3.75, 6.55), (16.45, 19.25)):
        cbox(M, x0, x1, 4.4, 8.0, Z_DECK - 0.2, Z_DECK + 0.2, hatch, ch=0.15, chz=0.1)
        for bx in (x0 + 0.45, x1 - 0.45):
            for by in (4.85, 7.55):
                cbox(M, bx - 0.18, bx + 0.18, by - 0.18, by + 0.18, Z_DECK, Z_DECK + 0.38, bolt, ch=0.07, chz=0.07)
    # notch floors (sills) under the breeches and the breech tubes in the notches
    brz = P(102, metallic=0.5, roughness=0.4)
    for _sx, bx, nx0, nx1 in GUNS:
        cbox(M, nx0 + 0.05, nx1 - 0.05, 8.7, 12.05, Z_PL1 - 0.3, ZG - 0.35, P(164, "sill"), ch=0.1)
        tube_y(M, bx, ZG, [(8.75, R_BR - 0.25), (8.95, R_BR), (12.4, R_BR)], brz, seg=16)
        # breech ring where it enters the sleeve
        tube_y(M, bx, ZG, [(10.6, R_BR + 0.12), (10.95, R_BR + 0.12)], brz, seg=16)
    # lamps: steel brackets on the housing flanks, red lenses on top
    lens = P(115, "lens", metallic=0.0, roughness=0.25, emission=2.5)
    for x0, x1, lx in ((1.15, 3.25, 2.05), (20.75, 22.85, 21.85)):
        cbox(M, x0, x1, 6.8, 12.2, Z_PL0, 3.3, steel, ch=0.3)
        cbox(M, x0 + 0.15, x1 - 0.15, 7.0, 12.0, 3.2, 3.6, P(101, "lensring", metallic=0.5, roughness=0.4), ch=0.15)
        ellipsoid_top(M, lx, 9.55, 3.5, 0.92, 2.42, 1.45, lens)
    # back: two feed pipes with capped couplings on saddles, a junction box between them
    pipe = P(100, "pipe", metallic=0.5, roughness=0.38)
    flange = P(101, "flange", metallic=0.5, roughness=0.42)
    for px in (8.0, 15.0):
        tube_y(M, px, 2.5, [(0.55, 1.75), (3.0, 1.75)], pipe, seg=20)
        tube_y(M, px, 2.5, [(0.02, 1.5), (0.1, 1.95), (0.55, 1.95), (0.62, 1.75)], flange, seg=20)
        tube_y(M, px, 2.5, [(1.55, 1.75), (1.6, 1.92), (1.9, 1.92), (1.95, 1.75)], flange, seg=20)
        cbox(M, px - 1.6, px + 1.6, 0.9, 1.4, Z_PAD - 0.1, 1.6, P(100, "saddle"), ch=0.12)
    cbox(M, 10.05, 12.95, 0.15, 2.6, Z_PAD - 0.1, 3.7, P(170, "box"), ch=0.35)
    cbox(M, 10.4, 12.6, 0.45, 2.3, 3.6, 3.95, P(170, "lid"), ch=0.12)


# --- the guns ------------------------------------------------------------------------------------

def gun(M, P, sx, collar, brake, port):
    c0, c1 = collar
    m0, m1 = brake
    p0, p1 = port
    cradle = P(165)
    sleeve = P(101, metallic=0.6, roughness=0.28)
    # cradle: west side rail, east rail under a recuperator cylinder, joined by a bottom plate
    cbox(M, sx - 3.5, sx + 4.3, 11.95, m0 + 0.4, Z_PAD - 0.1, 1.5, cradle, ch=0.2)
    cbox(M, sx - 3.5, sx - 2.15, 11.95, m0 + 0.4, Z_PAD - 0.1, ZG + 0.4, cradle, ch=0.25)
    cbox(M, sx + 2.55, sx + 4.4, 11.95, m0 + 0.4, Z_PAD - 0.1, 2.9, cradle, ch=0.2)
    tube_y(M, sx + 3.5, 3.15, [(11.95, 0.75), (12.15, 0.95), (m0 + 0.4, 0.95)], P(165, "recup"), seg=14)
    # recoil sleeve (into the brake)
    tube_y(M, sx, ZG, [(11.85, R_SLV - 0.3), (12.05, R_SLV), (m0 + 1.0, R_SLV)], sleeve, seg=24)
    # clamp collar
    cbox(M, sx - 3.5, sx + 4.45, c0, c1, Z_PAD + 0.1, ZG + 3.0, P(166), ch=0.45, chz=0.4)
    # muzzle brake: lower body, then a rim round the top port
    mz = P(167)
    outer = octo(sx - 3.5, m0, sx + 3.5, m1, 1.0, 0.9)
    zmid = ZG + 1.55
    prism(M, outer, [(0.45, Z_MZ_BOT), (0, Z_MZ_BOT + 0.45), (0, zmid)], [mz, mz], mz, mz)
    e = 0.2
    a0, a1 = sx - 1.5, sx + 1.5
    inner = [(a0 + e, p0), (a1 - e, p0), (a1, p0 + e), (a1, p1 - e), (a1 - e, p1), (a0 + e, p1), (a0, p1 - e), (a0, p0 + e)]
    frame_solid(M, outer, inner, zmid - 0.05, Z_MZ_TOP, 0.55, mz, P(164, "port"))
    # the glowing bore seen through the port
    glow = P(114, "bore", metallic=0.0, roughness=0.4, emission=2.2)
    cbox(M, a0 + 0.05, a1 - 0.05, p0 + 0.05, p1 - 0.05, zmid - 0.3, zmid + 0.25, glow, ch=0.05)
    # front face: the bore with a dark lip and the glow inside
    tube_y(M, sx, ZG, [(m1 - 0.2, 1.55), (m1 + 0.04, 1.55), (m1 + 0.1, 1.4)], P(164, "lip"), seg=20)
    tube_y(M, sx, ZG, [(m1 - 0.1, 1.05), (m1 + 0.12, 1.05)], glow, seg=20)
    # brake side vents: two slotted fins each side (the brake's baffles)
    for side in (-1, 1):
        xo = sx + side * 3.5
        for k, yv in enumerate((m0 + 2.2, m0 + 3.6)):
            if yv + 0.9 > m1 - 0.6:
                continue
            cbox(M, min(xo, xo + side * 0.22), max(xo, xo + side * 0.22), yv, yv + 0.8, ZG - 1.4, ZG + 1.4,
                 P(164, "vent"), ch=0.08)


def build(name, frame, collar, brake, port, sprite, coll):
    P = Pal(sprite, name)
    for i in (2, 100, 164, 165, 166, 167, 168):
        P(i)
    G = Mesh()
    pad(G, P, sprite)
    turret = Mesh()
    housing_parts(turret, P)
    for sx, _bx, _a, _b in GUNS:
        gun(turret, P, sx, collar, brake, port)
    tobj = turret.obj(f"{name}_turret", P.list, coll)
    body = housing_body(P, coll, name)
    # every material the parts used must be on the objects (P.list grows while building)
    for o in (tobj, body):
        while len(o.data.materials) < len(P.list):
            o.data.materials.append(P.list[len(o.data.materials)])
    gobj = G.obj(name, P.list, coll)
    # outline shell from a closed copy of the turret (not the pad)
    copies = []
    for o in (tobj, body):
        c = o.copy()
        c.data = o.data.copy()
        coll.objects.link(c)
        copies.append(c)
    join(copies)
    shell = common.outline_shell(copies[0], coll, voxel=0.012, faces=2600, smooth=6, inside=0.004)
    shell.name = shell.data.name = f"{name}_outline"
    bpy.data.objects.remove(copies[0], do_unlink=True)
    join([gobj, tobj, body])
    me = gobj.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    me.calc_loop_triangles()
    print(f"{name}: {len(me.loop_triangles)} triangles")
    return gobj, shell


def join(objs):
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return objs[0]


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    for model, frame, collar, brake, port in FRAMES:
        coll = common.reset_collection(model)
        o, shell = build(model, frame, collar, brake, port, sprite, coll)
        sprites = [{**sp, "frames": [frame]} for sp in sprite["sprites"]]
        common.export_sprite_model(WT, [o, shell], f"enemies/{model}", sprites)


if __name__ == "__main__":
    main()
