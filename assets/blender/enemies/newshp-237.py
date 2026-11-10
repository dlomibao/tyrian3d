"""Mine bunker, missile silo and homing mine (newshp.shp 237-283, 53 and 171-285), design A.

What they are (scout, level 1.3 ASTEROID?; the old docstrings' "1.21" was the old catalogue):
- newshp-237 (type 198): a FIXED GROUND BUNKER on the terrain layer (mv 0,0) that launches the
  homing mine. A squat cast casemate on a stone terrace: a rounded, battered housing with a
  square well; in the well an armoured shutter slides north under the rim and a red lens (the
  launcher's eye) rises in a round bezel. Five shapes, one model each (D17/D46, every frame kept):
      newshp-237     shutter back, lens up        (237, 239: the lens brightens, palette frames)
      newshp-237-f2  shutter half shut, edge row 8 (245)
      newshp-237-f3  shutter shut                 (279)
      newshp-237-f4  shutter nearly shut, edge 10 (281)
      newshp-237-f5  shutter back, lens sunk      (283)
- newshp-53 (type 457): the SAME housing on the same ground acting as a MISSILE SILO: its armoured
  hatch is lifted on two rams and slid north over the rim, opening the shaft where the next
  missile's nose waits.
- newshp-171 (type 199): the LAUNCHED HOMING MINE: a small free-flying ball (oblate sphere,
  closed round underside) with a machined equator belt, upper hemisphere in four panels, and the
  cross lamp in a boss on top. Its 7 frames only brighten the lamp (palette frames).

The ground (the 24 x 28 sprite is a whole tile): a stone terrace the bunker stands on, its lit
kerb along row 14, a ribbed concrete glacis falling south to a rubble floor, a ditch along the east
side, rubble stones where the sprite draws them. The outline shell is made from the building only
(housing, hatch), so the game inks the bunker and not the tile's square border.

Units: X = (x - W/2) / 12, Y = (H/2 - y) / 12, Z = z / 12 (x, y sprite pixel edges, y down; z px).
No texture bake (no textures/ folder for these; at 24 px the maps would not read).

Exports public/models/enemies/<model>.glb and src/render/spriteModels/<model>.json for all seven
models (newshp-237, -f2..-f5, newshp-53, newshp-171), each with its outline shell. newshp-53.py and
newshp-171.py build just their own model from here.

    blender --background --python assets/blender/enemies/newshp-237.py [-- model ...]
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

# --- heights (px) --------------------------------------------------------------------------------
Z_FLOOR = 0.3      # rubble floor south of the glacis and in the ditch
Z_TERR = 1.4       # terrace top (the bunker's footing)
Z_KERB = 1.85      # the lit kerb along row 14
Z_BANK = 0.9       # east bank beyond the ditch
H_PLINTH = 0.5     # housing plinth
Z_DECK = Z_TERR + 4.0   # housing deck
Z_WELL = Z_TERR + 0.35  # well floor
Z_SHUT = Z_DECK - 1.1   # shutter top
SHUT_T = 0.9            # shutter thickness

# --- geometry helpers ----------------------------------------------------------------------------


class Ctx:
    def __init__(self, w, h):
        self.cx, self.cy = w / 2, h / 2

    def v(self, x, y, z):
        return ((x - self.cx) / 12, (self.cy - y) / 12, z / 12)


def rrect(x0, y0, x1, y1, r, seg=4):
    """Closed plan of a rounded rectangle (px, y down), seg+1 points per corner, start NE."""
    r = max(min(r, (x1 - x0) / 2 - 1e-3, (y1 - y0) / 2 - 1e-3), 0.0)
    if r <= 1e-3:
        seg = 0
    pts = []
    corners = [(x1 - r, y0 + r, -90, 0), (x1 - r, y1 - r, 0, 90), (x0 + r, y1 - r, 90, 180), (x0 + r, y0 + r, 180, 270)]
    for cx, cy, a0, a1 in corners:
        for k in range(seg + 1):
            a = math.radians(a0 + (a1 - a0) * k / max(seg, 1))
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def rr_levels(x0, y0, x1, y1, r, levels, seg=4, zf=None):
    """Rings of a rounded box: levels = [(inset, z), ...]; zf(x, y, z) bends z (slopes)."""
    rings = []
    for d, z in levels:
        ring = []
        for x, y in rrect(x0 + d, y0 + d, x1 - d, y1 - d, max(r - d, 0.15) if r > 0 else 0.0, seg):
            ring.append((x, y, zf(x, y, z) if zf else z))
        rings.append(ring)
    return rings


class Mesh:
    def __init__(self, ctx):
        self.ctx = ctx
        self.bm = bmesh.new()

    def ring(self, pts):
        return [self.bm.verts.new(self.ctx.v(*p)) for p in pts]

    def face(self, vs, mat, smooth=False):
        f = self.bm.faces.new(vs)
        f.material_index = mat
        f.smooth = smooth
        return f

    def stack(self, rings, mats, top=None, bottom=None, smooth=False):
        """Loft rings (same point count) bottom to top; mats per band; caps."""
        vr = [self.ring(r) for r in rings]
        n = len(rings[0])
        for b, (r0, r1) in enumerate(zip(vr, vr[1:])):
            for i in range(n):
                j = (i + 1) % n
                self.face((r0[i], r0[j], r1[j], r1[i]), mats[min(b, len(mats) - 1)], smooth)
        if top is not None:
            self.face(vr[-1], top)
        if bottom is not None:
            self.face(list(reversed(vr[0])), bottom)
        return vr

    def bridge(self, ra, rb, mat):
        n = len(ra)
        for i in range(n):
            j = (i + 1) % n
            self.face((ra[i], ra[j], rb[j], rb[i]), mat)

    def obj(self, name, mats, coll, sharp=35):
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


def rbox(M, x0, y0, x1, y1, z0, z1, r, ch, top, wall, chm=None, seg=3, zf=None, bottom=True):
    """A box with rounded plan corners (r) and its top edge chamfered (ch), all px."""
    lv = [(0, z0), (0, z1 - ch), (ch, z1)] if ch > 0 else [(0, z0), (0, z1)]
    rings = rr_levels(x0, y0, x1, y1, r, lv, seg, zf)
    mats = [wall, chm if chm is not None else top]
    M.stack(rings, mats, top=top, bottom=top if bottom else None)


def stone(M, rnd, x0, y0, x1, y1, z0, h, top, wall):
    """A rubble stone: an irregular 5-7 sided block inside its box, chamfered, its top tilted."""
    n = rnd.choice((5, 6, 6, 7))
    cxs, cys = (x0 + x1) / 2, (y0 + y1) / 2
    ax, ay = (x1 - x0) / 2 - 0.15, (y1 - y0) / 2 - 0.15
    a0 = rnd.uniform(0, 2 * math.pi)
    plan = []
    for k in range(n):
        a = a0 + 2 * math.pi * (k + rnd.uniform(-0.18, 0.18)) / n
        f = rnd.uniform(0.86, 1.0)
        c, s_ = math.cos(a), math.sin(a)
        # push towards the box (a squarish stone fills its pixels): superellipse-ish radius
        m = max(abs(c), abs(s_)) ** 0.55
        plan.append((cxs + ax * f * c / m, cys + ay * f * s_ / m))
    tx, ty = rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1)
    hz = h * rnd.uniform(0.8, 1.15)

    def lvl(d, z):
        out = []
        for x, y in plan:
            dx, dy = x - cxs, y - cys
            L = math.hypot(dx, dy) or 1
            out.append((x - d * dx / L, y - d * dy / L, z + (tx * dx + ty * dy if z > z0 else 0)))
        return out
    rings = [lvl(0, z0 - 0.15), lvl(0.05, z0 + hz * 0.55), lvl(0.45, z0 + hz)]
    M.stack(rings, [wall, top], top=top, bottom=wall)


def bolt(M, x, y, z, r, mat, h=0.22, seg=6):
    ring0 = [(x + r * math.cos(2 * math.pi * k / seg), y + r * math.sin(2 * math.pi * k / seg), z - 0.1) for k in range(seg)]
    ring1 = [(x + r * math.cos(2 * math.pi * k / seg), y + r * math.sin(2 * math.pi * k / seg), z + h * 0.6) for k in range(seg)]
    ring2 = [(x + 0.6 * r * math.cos(2 * math.pi * k / seg), y + 0.6 * r * math.sin(2 * math.pi * k / seg), z + h) for k in range(seg)]
    M.stack([ring0, ring1, ring2], [mat], top=mat, bottom=mat)


def cyl(M, x, y, z0, z1, r, mat, seg=16, ch=0.0, top=None, r_top=None, smooth=True):
    rt = r if r_top is None else r_top
    rings = [[(x + r * math.cos(2 * math.pi * k / seg), y + r * math.sin(2 * math.pi * k / seg), z0) for k in range(seg)]]
    if ch:
        rings.append([(x + rt * math.cos(2 * math.pi * k / seg), y + rt * math.sin(2 * math.pi * k / seg), z1 - ch) for k in range(seg)])
        rings.append([(x + (rt - ch) * math.cos(2 * math.pi * k / seg), y + (rt - ch) * math.sin(2 * math.pi * k / seg), z1) for k in range(seg)])
    else:
        rings.append([(x + rt * math.cos(2 * math.pi * k / seg), y + rt * math.sin(2 * math.pi * k / seg), z1) for k in range(seg)])
    M.stack(rings, [mat], top=mat if top is None else top, bottom=mat, smooth=smooth)


def dome(M, x, y, z0, rx, ry, rz, mat, seg=16, rings=5, z_base=None):
    """Half ellipsoid on z0 with a short skirt down to z_base (closed)."""
    rs = []
    if z_base is not None:
        rs.append([(x + rx * math.cos(2 * math.pi * k / seg), y + ry * math.sin(2 * math.pi * k / seg), z_base) for k in range(seg)])
    for i in range(rings):
        p = (math.pi / 2) * i / rings
        rs.append([(x + rx * math.cos(p) * math.cos(2 * math.pi * k / seg), y + ry * math.cos(p) * math.sin(2 * math.pi * k / seg),
                    z0 + rz * math.sin(p)) for k in range(seg)])
    vr = M.stack(rs, [mat], bottom=mat, smooth=True)
    apex = M.bm.verts.new(M.ctx.v(x, y, z0 + rz))
    for k in range(seg):
        M.face((vr[-1][k], vr[-1][(k + 1) % seg], apex), mat, True)


# --- materials -----------------------------------------------------------------------------------


class Pal:
    def __init__(self, sprite, tag, metallic=0.25, roughness=0.7):
        self.sp, self.tag = sprite, tag
        self.list, self.slot = [], {}
        self.d = dict(metallic=metallic, roughness=roughness)

    def __call__(self, index, key=None, **kw):
        key = key or str(index)
        if key not in self.slot:
            args = dict(self.d)
            args.update(kw)
            t = self.tag if key == str(index) else f"{self.tag}_{key}"
            self.list.append(common.palette_material(self.sp, index, t, **args))
            self.slot[key] = len(self.list) - 1
        return self.slot[key]


# --- the ground tile -----------------------------------------------------------------------------

LEFT_RUBBLE = [(0, 0, 3, 3, 0.9, 7, 5), (0, 5, 4, 8, 0.8, 7, 5), (0, 10, 3, 13, 0.9, 8, 5)]
LEDGE_STONE = (0, 14.6, 5, 17.4, 0.7, 8, 5)
GLACIS_STONES = [(0, 19, 4, 23, 0.6, 6, 4)]
FLOOR_STONES = [(0, 24, 3, 27, 0.8, 7, 4), (4, 24, 7, 28, 0.8, 7, 5), (8, 24, 11, 27, 0.6, 6, 4),
                (12, 24, 15, 27, 0.6, 6, 4), (16, 24, 19, 28, 0.6, 6, 4), (20, 24, 23, 27, 0.7, 7, 3)]
BANK_STONES = [(21, 0, 24, 3, 0.6, 6, 4), (22, 5, 24, 8, 0.5, 5, 3), (22, 14, 24, 18, 0.5, 5, 3),
               (20.2, 19, 24, 23, 0.6, 5, 3)]

GL_Y0, GL_Y1 = 15.4, 23.0   # glacis from the kerb down to the floor


def glacis_z(y):
    t = min(max((y - GL_Y0) / (GL_Y1 - GL_Y0), 0.0), 1.0)
    return Z_TERR + (Z_FLOOR - Z_TERR) * t


def ground(M, P):
    rnd = random.Random(237)
    # floor plate, whole tile
    rbox(M, 0, 0, 24, 28, -0.3, Z_FLOOR, 0.0, 0.0, P(5), P(4))
    # ditch floor (deep shadow strip) along the east side
    rbox(M, 19.4, 1.5, 21.2, 14.2, Z_FLOOR - 0.1, Z_FLOOR + 0.03, 0.3, 0.0, P(2), P(2))
    rbox(M, 16.9, 14.0, 21.2, 23.0, Z_FLOOR - 0.1, Z_FLOOR + 0.03, 0.3, 0.0, P(2), P(2))
    # terrace under the bunker and the west rubble
    rbox(M, -0.01, -0.01, 19.5, 14.6, Z_FLOOR - 0.1, Z_TERR, 0.4, 0.3, P(6), P(5), P(6))
    # the lit kerb along row 14
    rbox(M, -0.01, 13.9, 16.6, 15.4, Z_TERR - 0.2, Z_KERB, 0.3, 0.3, P(8), P(6), P(9))
    # the glacis: a sloped concrete face from the kerb to the floor, ribbed (buttress slabs)
    zf = lambda x, y, z: z + glacis_z(y) - Z_TERR  # noqa: E731
    rings = rr_levels(-0.01, GL_Y0 - 0.2, 16.9, GL_Y1, 0.2, [(0, Z_TERR - 0.2), (0, Z_TERR)], 2)
    rings[0] = [(x, y, Z_FLOOR - 0.1) for x, y, _ in rings[0]]
    rings[1] = [(x, y, zf(x, y, Z_TERR)) for x, y, _ in rings[1]]
    M.stack(rings, [P(3)], top=P(3), bottom=P(3))
    for x0, x1, top in ((5.0, 9.0, 5), (10.0, 13.0, 4), (15.9, 16.9, 3)):
        lv = [(0, Z_TERR - 0.3), (0, Z_TERR + 0.25), (0.3, Z_TERR + 0.5)]
        rings = rr_levels(x0, GL_Y0 - 0.1, x1, GL_Y1 - 0.4, 0.3, lv, 2, zf)
        M.stack(rings, [P(top - 1 if top > 3 else 2), P(top + 1)], top=P(top), bottom=P(top))
    # glacis west part between the ribs: rough fill a little proud, so the stones sit in it
    rbox(M, 0, GL_Y0, 4.9, GL_Y1 - 0.5, Z_FLOOR, Z_TERR - 0.1, 0.3, 0.0, P(5), P(4), zf=lambda x, y, z: z if z < Z_TERR - 0.5 else glacis_z(y) + 0.05)
    # east bank beyond the ditch
    rbox(M, 21.0, -0.01, 24.01, 23.0, Z_FLOOR - 0.1, Z_BANK, 0.4, 0.25, P(4), P(3), P(5))
    # rubble stones
    for x0, y0, x1, y1, h, top, wall in LEFT_RUBBLE:
        stone(M, rnd, x0, y0, x1, y1, Z_TERR, h, P(top), P(wall))
    x0, y0, x1, y1, h, top, wall = LEDGE_STONE
    stone(M, rnd, x0, y0, x1, y1, Z_KERB - 0.3, h, P(top), P(wall))
    for x0, y0, x1, y1, h, top, wall in GLACIS_STONES:
        stone(M, rnd, x0, y0, x1, y1, glacis_z((y0 + y1) / 2), h, P(top), P(wall))
    for x0, y0, x1, y1, h, top, wall in FLOOR_STONES:
        stone(M, rnd, x0, y0, x1, y1, Z_FLOOR, h, P(top), P(wall))
    for x0, y0, x1, y1, h, top, wall in BANK_STONES:
        stone(M, rnd, x0, y0, x1, y1, Z_BANK if y1 < 19 else Z_FLOOR + 0.2, h + (0 if y1 < 19 else 0.3), P(top), P(wall))


# --- the housing ---------------------------------------------------------------------------------

HX0, HY0, HX1, HY1 = 3.5, -0.01, 19.0, 14.0   # footprint
HR = 3.0                                     # plan corner radius
WX0, WY0, WX1, WY1 = 7.0, 2.0, 17.0, 12.4    # well opening at the deck
SEG = 4


def housing(M, P, ctx, coll, name, mats):
    """The cast housing, built whole, then split at the transverse joint (row 6.5) into a north
    and a south casting with a recessed band between them. Returns the joined object's bmesh
    added to M."""
    deck, wall, lip, inner, floor_ = P(9), P(9), P(11), P(6), P(3)
    lv = [(0, Z_TERR - 0.2), (0, Z_TERR + H_PLINTH), (0.25, Z_TERR + H_PLINTH + 0.05),
          (1.0, Z_DECK - 0.45), (1.45, Z_DECK)]

    def shell(extra_in, drop):
        H = Mesh(ctx)
        rings = rr_levels(HX0, HY0, HX1, HY1, HR, [(d + (extra_in if i > 1 else 0), z - (drop if i == len(lv) - 1 else 0))
                                                   for i, (d, z) in enumerate(lv)], SEG)
        vr = H.stack(rings, [P(7), P(7), wall, lip], bottom=wall)
        # inner lip (chamfer) and walls down to the well floor
        il = [(x, y, Z_DECK - drop) for x, y in rrect(WX0 - 0.45, WY0 - 0.45, WX1 + 0.45, WY1 + 0.45, 1.0, SEG)]
        iw = [(x, y, Z_DECK - 0.5 - drop) for x, y in rrect(WX0, WY0, WX1, WY1, 0.6, SEG)]
        ib = [(x, y, Z_WELL) for x, y in rrect(WX0 + 0.35, WY0 + 0.2, WX1 - 0.35, WY1 - 0.2, 0.5, SEG)]
        vil, viw, vib = H.ring(il), H.ring(iw), H.ring(ib)
        H.bridge(vr[-1], vil, deck)
        H.bridge(vil, viw, P(7))
        H.bridge(viw, vib, inner)
        H.face(list(reversed(vib)), floor_)
        return H.obj(name + "_h", mats, coll)

    def box_obj(x0, y0, x1, y1, z0, z1):
        B = Mesh(ctx)
        rbox(B, x0, y0, x1, y1, z0, z1, 0.0, 0.0, P(5), P(5))
        return B.obj(name + "_cut", mats, coll)

    def boolean(o, cutter, op):
        mod = o.modifiers.new("b", "BOOLEAN")
        mod.operation = op
        mod.object = cutter
        mod.solver = "EXACT"
        try:
            mod.material_mode = "TRANSFER"
        except Exception:
            pass
        common._apply_modifiers(o)
        bpy.data.objects.remove(cutter, do_unlink=True)

    north = shell(0, 0)
    boolean(north, box_obj(-5, -5, 30, 6.3, -5, 20), "INTERSECT")
    south = shell(0, 0)
    boolean(south, box_obj(-5, 6.7, 30, 40, -5, 20), "INTERSECT")
    # the gap through the well (lip, walls, floor) is filled flush; only the rims get the
    # recessed joint band
    mid = shell(0, 0)
    boolean(mid, box_obj(WX0 - 0.5, 6.3, WX1 + 0.5, 6.7, -5, 20), "INTERSECT")
    band_w = shell(0.45, 0.45)
    boolean(band_w, box_obj(-5, 6.2, WX0 - 0.5, 6.8, -5, 20), "INTERSECT")
    band_e = shell(0.45, 0.45)
    boolean(band_e, box_obj(WX1 + 0.5, 6.2, 30, 6.8, -5, 20), "INTERSECT")
    return [north, south, mid, band_w, band_e]


def deck_bolts(M, P):
    """Bolt heads along the castings' joint (where the sprite's row-6/7 lit pixels sit) and at
    the deck corners."""
    for x in (5.2, 17.3):
        for y in (5.6, 7.4):
            bolt(M, x, y, Z_DECK, 0.42, P(10))
    for x, y in ((5.6, 1.6), (16.9, 1.6), (5.6, 12.6), (16.9, 12.6)):
        bolt(M, x, y, Z_DECK, 0.4, P(10))


def shutter(M, P, edge):
    """The armoured shutter in the well: its south (leading) edge at row `edge`, the rest slid
    north under the rim. A bullnose leading edge (lit top roll, grey face), a recessed panel."""
    x0, x1 = WX0 + 0.55, WX1 - 0.55
    ytop = edge - 1.0           # where the top meets the leading bevel
    y_n = 0.9                   # far end, hidden under the rim
    zt, zb = Z_SHUT, Z_SHUT - SHUT_T
    # body: plan from y_n to edge, top chamfered along the leading edge (rings by hand)
    sec = [(edge, zb), (edge, zt - 0.55), (edge - 0.45, zt - 0.12), (ytop, zt)]
    rings = []
    for y, z in sec:
        rings.append([(x0, y, z), (x1, y, z)])
    vs = []
    for (y, z) in sec:
        vs.append((M.bm.verts.new(M.ctx.v(x0, y, z)), M.bm.verts.new(M.ctx.v(x1, y, z))))
    back_t = (M.bm.verts.new(M.ctx.v(x0, y_n, zt)), M.bm.verts.new(M.ctx.v(x1, y_n, zt)))
    back_b = (M.bm.verts.new(M.ctx.v(x0, y_n, zb)), M.bm.verts.new(M.ctx.v(x1, y_n, zb)))
    profile = [vs[0], vs[1], vs[2], vs[3], back_t, back_b]
    mats = [P(7), P(11), P(12), P(9), P(7), P(6)]  # face, bevel low, bevel high (lit roll), top, back, bottom
    for i in range(len(profile)):
        a, b = profile[i], profile[(i + 1) % len(profile)]
        M.face((a[0], a[1], b[1], b[0]), mats[i])
    M.face([p[0] for p in profile], P(7))
    M.face([p[1] for p in reversed(profile)], P(7))
    # recessed panel on the top (shows when shut): a panel line round an inner plate
    if edge > 7.5:
        rbox(M, x0 + 1.0, WY0 + 1.0, x1 - 1.0, edge - 1.6, zt - 0.3, zt + 0.12, 0.3, 0.12, P(9), P(7), P(10))
        for x in (x0 + 0.5, x1 - 0.5):
            for y in (WY0 + 0.4, edge - 1.4):
                bolt(M, x, y, zt, 0.28, P(10), h=0.18)


def socket(M, P, lens, LP=None):
    """The lens bezel on the well floor (cols 9-14, rows 6-10) and the lens, if up."""
    cx, cy = 12.0, 8.2
    # square-ish bezel block with round bore
    rbox(M, 8.9, 5.6, 15.1, 10.9, Z_WELL - 0.1, Z_WELL + 1.2, 1.2, 0.35, P(4) if LP is None else LP["socket"], P(4) if LP is None else P(5), P(5) if LP is None else P(7))
    if lens:
        # lens up: a red glass dome on a short barrel, hot core on top
        cyl(M, cx, cy, Z_WELL + 1.0, Z_WELL + 1.9, 2.15, P(5), seg=20)
        dome(M, cx, cy, Z_WELL + 1.9, 2.0, 2.0, 1.3, LP["lens"], seg=20, rings=5)
        dome(M, cx, cy, Z_WELL + 2.95, 1.05, 1.05, 0.4, LP["core"], seg=12, rings=3)
    else:
        # lens sunk: the dark bore in the bezel
        cyl(M, cx, cy, Z_WELL + 1.15, Z_WELL + 1.26, 2.6, P(2), seg=20, smooth=False)


def silo(M, P):
    """newshp-53's well: the shaft, its south step, the missile nose, the lifted hatch on rams."""
    # the dark shaft floor deep down and its south step (row 10-11, lit 5)
    rbox(M, WX0 + 0.4, 9.9, WX1 - 0.4, WY1 - 0.2, Z_WELL - 0.1, Z_WELL + 1.5, 0.3, 0.3, P(5), P(4), P(6))
    rbox(M, WX0 + 0.5, WY0 + 0.2, WX1 - 0.5, 9.9, Z_WELL - 0.1, Z_WELL + 0.05, 0.3, 0.0, P(1), P(1))
    # the missile's nose waiting in the shaft (dark, just lit at its tip)
    cyl(M, 12.0, 8.6, Z_WELL, Z_WELL + 0.8, 1.5, P(3), seg=16)
    dome(M, 12.0, 8.6, Z_WELL + 0.8, 1.5, 1.5, 1.4, P(3), seg=16, rings=4)
    # rams: two pistons from the well floor up under the hatch's south part
    for x in (9.2, 14.8):
        cyl(M, x, 5.4, Z_WELL, Z_DECK + 0.4, 0.55, P(6), seg=10)
        cyl(M, x, 5.4, Z_DECK - 1.6, Z_DECK + 0.55, 0.36, P(11), seg=10)
    # the hatch: a thick chamfered armour block, lifted and slid north over the rim (rows 0-6.6)
    hz0, hz1 = Z_DECK + 0.45, Z_DECK + 2.3
    rbox(M, 7.7, 0.15, 16.4, 6.7, hz0, hz1, 0.7, 0.55, P(9), P(7), P(12))
    # its recessed top panel and bolts
    rbox(M, 9.2, 1.4, 14.9, 5.3, hz1 - 0.3, hz1 + 0.1, 0.4, 0.12, P(9), P(7), P(10))
    for x in (8.6, 15.5):
        for y in (1.0, 5.8):
            bolt(M, x, y, hz1, 0.3, P(10), h=0.18)
    # guide rails on the north rim the hatch rides on
    for x in (8.4, 15.7):
        rbox(M, x - 0.45, 0.4, x + 0.45, 2.2, Z_DECK - 0.2, hz0 + 0.05, 0.15, 0.1, P(7), P(6))


# --- models --------------------------------------------------------------------------------------

def bunker(name, sprite, coll, state):
    ctx = Ctx(24, 28)
    P = Pal(sprite, name)
    LP = None
    if state.get("lens"):
        LP = {"socket": P(6, "socket", frames={239: 9}),
              "lens": P(113, "lens", emission_strength=2.0, frames={239: 118}, metallic=0.0, roughness=0.25),
              "core": P(117, "core", emission_strength=4.0, frames={239: 123}, metallic=0.0, roughness=0.2)}
    M = Mesh(ctx)
    ground(M, P)
    if state["kind"] == "eye":
        shutter(M, P, state["edge"])
        socket(M, P, state.get("lens"), LP)
    else:
        silo(M, P)
    deck_bolts(M, P)
    # materials must exist before the housing objects take the list
    for i in (5, 6, 7, 8, 9, 10, 11, 3):
        P(i)
    gnd = M.obj(name, P.list, coll)
    parts = housing(M, P, ctx, coll, name, P.list)
    building = [p for p in parts]
    # one object: ground + housing pieces
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    shell_src = []
    for p in parts:
        c = p.copy()
        c.data = p.data.copy()
        coll.objects.link(c)
        shell_src.append(c)
    for p in parts:
        p.select_set(True)
    gnd.select_set(True)
    bpy.context.view_layer.objects.active = gnd
    bpy.ops.object.join()
    finish(gnd)
    # outline shell from the building only (+ the hatch for the silo)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for c in shell_src:
        c.select_set(True)
    bpy.context.view_layer.objects.active = shell_src[0]
    bpy.ops.object.join()
    src = shell_src[0]
    if state["kind"] == "silo":
        H = Mesh(ctx)
        PH = Pal(sprite, name)
        hz0, hz1 = Z_DECK + 0.45, Z_DECK + 2.3
        rbox(H, 7.7, 0.15, 16.4, 6.7, Z_DECK - 0.5, hz1, 0.7, 0.55, 0, 0, 0)
        h = H.obj(name + "_hs", [], coll)
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        h.select_set(True)
        src.select_set(True)
        bpy.context.view_layer.objects.active = src
        bpy.ops.object.join()
    shell = common.outline_shell(src, coll, voxel=0.014, faces=2500, smooth=6, inside=0.006)
    shell.name = shell.data.name = f"{name}_outline"
    bpy.data.objects.remove(src, do_unlink=True)
    return gnd, shell


def finish(o, angle=38):
    me = o.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(angle))


MINE_C = (6.5, 7.5)
MINE_R = 3.85      # belt radius (px), the plan's outer edge
MINE_HZ = 3.0      # half height


def mine(name, sprite, coll):
    ctx = Ctx(12, 14)
    frames = (190, 209, 228, 247, 266, 285)
    P = Pal(sprite, name, metallic=0.45, roughness=0.42)
    lamp = P(112, "lamp", emission_strength=3.0, metallic=0.0, roughness=0.25, frames=dict(zip(frames, (115, 117, 119, 121, 123, 125))))
    core = P(113, "core", emission_strength=5.0, metallic=0.0, roughness=0.2, frames=dict(zip(frames, (117, 119, 121, 123, 125, 127))))
    body = P(7, "body", frames={209: 8, 228: 8, 247: 9, 266: 9, 285: 10})
    seam = P(4, "seam")
    belt = P(6, "belt")
    boss = P(7, "boss")
    M = Mesh(ctx)
    cx, cy = MINE_C
    zc = MINE_HZ
    R = MINE_R - 0.12
    SEGM = 40

    def sph(lat, lon, rr=R, hz=MINE_HZ):
        return (cx + rr * math.cos(lat) * math.cos(lon), cy - rr * math.cos(lat) * math.sin(lon), zc + hz * math.sin(lat))

    # dark core sphere (shows in the panel gaps), with the closed round underside
    lats = [math.radians(a) for a in range(-90, 91, 10)]
    rs = []
    for a in lats[1:-1]:
        rs.append([sph(a, 2 * math.pi * k / SEGM, R - 0.18, MINE_HZ - 0.18) for k in range(SEGM)])
    vr = M.stack(rs, [seam], smooth=True)
    bot = M.bm.verts.new(ctx.v(cx, cy, zc - (MINE_HZ - 0.18)))
    top = M.bm.verts.new(ctx.v(cx, cy, zc + (MINE_HZ - 0.18)))
    for k in range(SEGM):
        M.face((vr[0][(k + 1) % SEGM], vr[0][k], bot), seam, True)
        M.face((vr[-1][k], vr[-1][(k + 1) % SEGM], top), seam, True)
    # lower hemisphere: one smooth shell (no detail), body colour
    lo = [math.radians(a) for a in (-80, -65, -50, -35, -20, -9)]
    rs = [[sph(a, 2 * math.pi * k / SEGM) for k in range(SEGM)] for a in lo]
    vr = M.stack(rs, [body], smooth=True)
    pole = M.bm.verts.new(ctx.v(cx, cy, zc - MINE_HZ))
    for k in range(SEGM):
        M.face((vr[0][(k + 1) % SEGM], vr[0][k], pole), body, True)
    # inner closing ring for the lower shell's top edge (tucked under the belt)
    # equator belt: a machined band, proud of the hull, chamfered edges, with vent slots
    bz0, bz1 = zc - 0.75, zc + 0.75
    brs = []
    for z, rr in ((bz0 - 0.2, R - 0.05), (bz0, MINE_R - 0.1), (bz0 + 0.12, MINE_R), (bz1 - 0.12, MINE_R), (bz1, MINE_R - 0.1), (bz1 + 0.2, R - 0.05)):
        brs.append([(cx + rr * math.cos(2 * math.pi * k / SEGM), cy - rr * math.sin(2 * math.pi * k / SEGM), z) for k in range(SEGM)])
    M.stack(brs, [belt, belt, belt, belt, belt], top=belt, bottom=belt, smooth=True)
    # upper hemisphere: four panels between the lamp-cross arms' diagonals, gaps = panel lines
    gap = math.radians(5.5)
    up = [math.radians(a) for a in (9, 20, 32, 44, 55, 64)]
    for q in range(4):
        a0 = math.radians(45 + 90 * q) + gap
        a1 = math.radians(45 + 90 * (q + 1)) - gap
        n = 9
        grid = [[sph(lat, a0 + (a1 - a0) * j / n) for j in range(n + 1)] for lat in up]
        gv = [[M.bm.verts.new(ctx.v(*p)) for p in row] for row in grid]
        for i in range(len(up) - 1):
            for j in range(n):
                M.face((gv[i][j], gv[i][j + 1], gv[i + 1][j + 1], gv[i + 1][j]), body, True)
        # thickness: an inner offset skin closing the panel (edges at the gaps)
        inner = [[M.bm.verts.new(ctx.v(*sph(lat, a0 + (a1 - a0) * j / n, R - 0.25, MINE_HZ - 0.25))) for j in range(n + 1)] for lat in up]
        for i in range(len(up) - 1):
            for j in range(n):
                M.face((inner[i][j], inner[i + 1][j], inner[i + 1][j + 1], inner[i][j + 1]), seam, True)
        for i in range(len(up) - 1):
            M.face((gv[i][0], gv[i + 1][0], inner[i + 1][0], inner[i][0]), seam)
            M.face((gv[i][n], inner[i][n], inner[i + 1][n], gv[i + 1][n]), seam)
        for j in range(n):
            M.face((gv[0][j], inner[0][j], inner[0][j + 1], gv[0][j + 1]), seam)
            M.face((gv[-1][j], gv[-1][j + 1], inner[-1][j + 1], inner[-1][j]), seam)
    # the lamp boss: a short round collar at the pole
    zt = zc + MINE_HZ * math.sin(math.radians(64))
    rb = R * math.cos(math.radians(64)) + 0.15
    cyl(M, cx, cy, zt - 0.6, zt + 0.35, rb, boss, seg=24, ch=0.18)
    # the cross lamp: a plus-shaped glass prism in the boss, hot core at its centre
    a, b = 0.5, 1.5   # arm half width, arm half length (sprite: 3-px arms, 1 px wide)
    plus = [(a, -b), (a, -a), (b, -a), (b, a), (a, a), (a, b), (-a, b), (-a, a), (-b, a), (-b, -a), (-a, -a), (-a, -b)]
    zl0, zl1 = zt + 0.2, zt + 0.75
    r0 = [(cx + x, cy + y, zl0) for x, y in plus]
    r1 = [(cx + x, cy + y, zl1 - 0.15) for x, y in plus]
    r2 = [(cx + x * 0.82, cy + y * 0.82, zl1) for x, y in plus]
    M.stack([r0, r1, r2], [lamp], top=lamp, bottom=lamp)
    dome(M, cx, cy, zl1 - 0.05, 0.55, 0.55, 0.3, core, seg=10, rings=3)
    o = M.obj(name, P.list, coll)
    finish(o, 50)
    closed = o.copy()
    closed.data = o.data.copy()
    coll.objects.link(closed)
    shell = common.outline_shell(closed, coll, voxel=0.008, faces=1500, smooth=6, inside=0.004)
    shell.name = shell.data.name = f"{name}_outline"
    bpy.data.objects.remove(closed, do_unlink=True)
    return o, shell


STATES = [
    ("newshp-237", "newshp-237", {"kind": "eye", "edge": 5.9, "lens": True}),
    ("newshp-237-f2", "newshp-237", {"kind": "eye", "edge": 8.0}),
    ("newshp-237-f3", "newshp-237", {"kind": "eye", "edge": 12.2}),
    ("newshp-237-f4", "newshp-237", {"kind": "eye", "edge": 10.0}),
    ("newshp-237-f5", "newshp-237", {"kind": "eye", "edge": 5.9}),
    ("newshp-53", "newshp-53", {"kind": "silo"}),
]


FRAMES = {
    "newshp-237": (237, 239), "newshp-237-f2": (245,), "newshp-237-f3": (279,),
    "newshp-237-f4": (281,), "newshp-237-f5": (283,),
}


def sprites_for(model, sprite):
    if model not in FRAMES:
        return sprite["sprites"]
    keep = FRAMES[model]
    return [{**s, "frames": [f for f in s["frames"] if f in keep]} for s in sprite["sprites"]
            if any(f in keep for f in s["frames"])]


def main(only=None):
    if only is None and "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        only = set(args) or None
    sprites = {n: common.load_sprite(WT, n) for n in ("newshp-237", "newshp-53", "newshp-171")}
    for model, sp, state in STATES:
        if only and model not in only:
            continue
        coll = common.reset_collection(model)
        o, shell = bunker(model, sprites[sp], coll, state)
        print(f"{model}: {sum(len(p.vertices) - 2 for p in o.data.polygons)} triangles")
        common.export_sprite_model(WT, [o, shell], f"enemies/{model}", sprites_for(model, sprites[sp]))
    if not only or "newshp-171" in only:
        coll = common.reset_collection("newshp-171")
        o, shell = mine("newshp-171", sprites["newshp-171"], coll)
        print(f"newshp-171: {sum(len(p.vertices) - 2 for p in o.data.polygons)} triangles")
        common.export_sprite_model(WT, [o, shell], "enemies/newshp-171", sprites["newshp-171"]["sprites"])


if __name__ == "__main__":
    main()
