"""Mine bunker, missile silo and homing mine (newshp.shp 237-283, 53 and 171-285), design A.

What they are (1.3 ASTEROID?, the secret level reached from ASTEROID2):
- newshp-237 (type 198): a FIXED GROUND BUNKER on the terrain layer (mv 0,0) that launches the
  homing mine. A squat casemate of dressed, worn stone (two big blocks with a joint at row 6.5,
  chisel-faceted walls, bevelled top) on a stone terrace, with a square well closed by an armoured
  steel HATCH LID HINGED AT ITS NORTH EDGE. The lid swings up on its hinge, pushed by two
  telescopic rams in the well, and a red lens (the launcher's eye) rises in a round bezel on the
  well floor. One lid, one hinge, one pair of rams through every frame; only the lid's angle and
  the lens change (D17/D46, every frame kept):
      newshp-237-f3  lid shut (0 deg)                           (279)
      newshp-237-f4  lid at 44 deg, its end face on row 9       (281)
      newshp-237-f2  lid at 60 deg, its end face on row 7       (245)
      newshp-237-f5  lid at 75 deg (open), lens sunk            (283)
      newshp-237     lid at 75 deg (open), lens up              (237, 239: the lens brightens)
  The angles come from the sprite: the lid is 9 px long (rows 3-11), so its top projects to
  9 cos(a) px (6, 4, ~1.7 rows) and its 1.3 px end face shows as the row of index 7 under it.
- newshp-53 (type 457): the SAME housing and the SAME lid, hinge and rams used as a MISSILE SILO:
  the hinge sits on the north rim (row 0) and the lid stands at 50 deg (the sprite draws 281's lid
  three rows further north), over a deep shaft with a stepped south wall and the next missile's
  nose waiting in it.
- newshp-171 (type 199): the launched homing mine, unchanged from the current script.

The ground (the 24 x 28 sprite is a whole tile): the stone terrace the bunker stands on with its lit
kerb along row 14, a rough rock glacis falling south, the dark ditch on the east, faceted rubble
stones (each facet's index from how it faces the game's sun round its region's art median, D148's
rock rule) and a course of bevelled paving bricks along rows 24-27 (D148/D150's bricks). The outline
shell is made from the building only (housing, hinge, lid), so the game inks the bunker and not the
tile's square border.

Bake: AO/roughness with the station kit's worn finish (lib_l1bld._bake with lib_l1kit.GRIT, copied
here), "bake": "model" (D65, D148). Rubble stones and the emissive lens are left out of the bake
(plain, as the kit's rocks).

Units: X = (x - W/2) / 12, Y = (H/2 - y) / 12, Z = z / 12 (x, y sprite pixel edges, y down; z px).

    blender --background --python assets/blender/enemies/newshp-237.py [-- [--no-bake] [--render] model ...]

Exports public/models/enemies/<model>.glb and src/render/spriteModels/<model>.json for all seven
models. newshp-53.py and newshp-171.py build just their own model from here.
"""

import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
import os, tempfile  # noqa: E402
HERE = Path(os.environ.get("NEWSHP237_OUT") or tempfile.gettempdir()) / "newshp-237-review"  # --render output, report
HERE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402


# --- heights (px) --------------------------------------------------------------------------------
Z_FLOOR = 0.3      # rubble floor south of the glacis and in the ditch
Z_TERR = 1.4       # terrace top (the bunker's footing)
Z_KERB = 1.85      # the lit kerb along row 14
Z_BANK = 0.9       # east bank beyond the ditch
H_PLINTH = 0.5     # housing plinth
Z_DECK = Z_TERR + 4.0    # housing deck (5.4)
Z_WELL = Z_TERR + 0.35   # well floor (1.75)

# the hatch lid (closed position, px): one lid for every frame and for the silo
LID_X0, LID_X1 = 8.0, 16.0
LID_LEN = 9.0            # along the lid from its hinge-side edge (rows 3-11)
LID_T = 1.3              # thickness: the row of index 7 under the lid when it is raised
ZL_TOP = Z_DECK + 0.35   # lid top when shut (5.75)
ZL_BOT = ZL_TOP - LID_T  # 4.45, where it sits on the seat frame
AX_DZ = -0.45            # the hinge axis sits this far under the lid's top
AX_GAP = 0.25            # from the axis to the lid's hinge-side edge (in plan when shut)
KN_R = 0.55              # hinge knuckle radius
RAM_S = 3.0              # where the rams take the lid, from the axis along it
RAM_X = (8.45, 15.55)

# --- the sun (src/render/view.ts (-6, 20, 8.4) in three's frame) in model space ----------------
SUN = (-6.0 / 22.47, -8.4 / 22.47, 20.0 / 22.47)

# --- the kit's worn finish (lib_l1kit.GRIT, D150) -------------------------------------------------
GRIT = dict(floor=0.56, occl=0.5, edge=0.22, grime=0.12, rough=0.2, scale=1.4, island=0.65, plain_uv=False)


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


def resample(pts, n):
    """n points evenly spaced along the closed polyline pts, the first at pts[0]."""
    seg = []
    tot = 0.0
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        d = math.dist(a, b)
        seg.append((a, b, d))
        tot += d
    out = []
    step = tot / n
    k = 0
    acc = 0.0
    for i in range(n):
        t = i * step
        while k < len(seg) - 1 and acc + seg[k][2] < t:
            acc += seg[k][2]
            k += 1
        a, b, d = seg[k]
        f = (t - acc) / d if d > 0 else 0.0
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


def rr_levels(x0, y0, x1, y1, r, levels, seg=4, zf=None):
    """Rings of a rounded box: levels = [(inset, z), ...]; zf(x, y, z) bends z (slopes)."""
    rings = []
    for d, z in levels:
        ring = []
        for x, y in rrect(x0 + d, y0 + d, x1 - d, y1 - d, max(r - d, 0.15) if r > 0 else 0.0, seg):
            ring.append((x, y, zf(x, y, z) if zf else z))
        rings.append(ring)
    return rings


def rot_x(ay, az, ang):
    """Turn (x, y, z) px about the line y = ay, z = az (along x) by ang: +ang lifts the south side."""
    c, s = math.cos(ang), math.sin(ang)

    def f(p):
        x, y, z = p
        sy, u = y - ay, z - az
        return (x, ay + sy * c - u * s, az + sy * s + u * c)
    return f


class Mesh:
    def __init__(self, ctx):
        self.ctx = ctx
        self.bm = bmesh.new()
        self.xf = None

    def vert(self, p):
        if self.xf is not None:
            p = self.xf(p)
        return self.bm.verts.new(self.ctx.v(*p))

    def ring(self, pts):
        return [self.vert(p) for p in pts]

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

    def obj(self, name, mats, coll, recalc=True):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-6)
        if recalc:
            bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in mats:
            me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        return o


def rbox(M, x0, y0, x1, y1, z0, z1, r, ch, top, wall, chm=None, seg=3, zf=None, bottom=True, bch=0.0):
    """A box with rounded plan corners (r), its top edge chamfered (ch), its bottom edge (bch), px."""
    lv = []
    if bch > 0:
        lv += [(bch, z0), (0, z0 + bch)]
    else:
        lv += [(0, z0)]
    lv += [(0, z1 - ch), (ch, z1)] if ch > 0 else [(0, z1)]
    rings = rr_levels(x0, y0, x1, y1, r, lv, seg, zf)
    mats = ([wall] if bch > 0 else []) + [wall, chm if chm is not None else top]
    M.stack(rings, mats, top=top, bottom=top if bottom else None)


def cyl_x(M, x0, x1, y, z, r, mat, seg=12, ch=0.0, cap=None):
    """A cylinder along x (a hinge knuckle, a pin), its ends chamfered by ch."""
    def ring(x, rr):
        return [(x, y + rr * math.cos(2 * math.pi * k / seg), z + rr * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
    rings = ([ring(x0, r - ch), ring(x0 + ch, r)] if ch else [ring(x0, r)])
    rings += ([ring(x1 - ch, r), ring(x1, r - ch)] if ch else [ring(x1, r)])
    M.stack(rings, [mat], top=mat if cap is None else cap, bottom=mat if cap is None else cap, smooth=True)


def cyl_between(M, a, b, r, mat, seg=10, cap=None):
    """A cylinder from point a to point b (px), radius r."""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    up = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0))
    e1 = d.cross(up).normalized()
    e2 = d.cross(e1).normalized()
    ring0, ring1 = [], []
    for k in range(seg):
        t = 2 * math.pi * k / seg
        off = e1 * (r * math.cos(t)) + e2 * (r * math.sin(t))
        ring0.append(tuple(a + off))
        ring1.append(tuple(b + off))
    M.stack([ring0, ring1], [mat], top=mat if cap is None else cap, bottom=mat if cap is None else cap, smooth=True)


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
    apex = M.vert((x, y, z0 + rz))
    for k in range(seg):
        M.face((vr[-1][k], vr[-1][(k + 1) % seg], apex), mat, True)


def bolt(M, x, y, z, r, mat, h=0.22, seg=6):
    ring0 = [(x + r * math.cos(2 * math.pi * k / seg), y + r * math.sin(2 * math.pi * k / seg), z - 0.1) for k in range(seg)]
    ring1 = [(x + r * math.cos(2 * math.pi * k / seg), y + r * math.sin(2 * math.pi * k / seg), z + h * 0.6) for k in range(seg)]
    ring2 = [(x + 0.6 * r * math.cos(2 * math.pi * k / seg), y + 0.6 * r * math.sin(2 * math.pi * k / seg), z + h) for k in range(seg)]
    M.stack([ring0, ring1, ring2], [mat], top=mat, bottom=mat)


def facet_ramp(normal, base):
    """D148/D150's rock rule round a region's own art index: a facet facing the game's sun takes
    the light end, a facet turned away the dark end (lib_l1kit.facet_index, re-centred on base)."""
    lam = normal[0] * SUN[0] + normal[1] * SUN[1] + normal[2] * SUN[2]
    for lim, idx in ((0.95, 8), (0.88, 7), (0.78, 6), (0.6, 5), (0.35, 4)):
        if lam >= lim:
            return max(1, min(14, base + idx - 6))
    return max(1, base - 3)


# --- materials -----------------------------------------------------------------------------------

STONE = dict(metallic=0.0, roughness=0.78)
STEEL = dict(metallic=0.35, roughness=0.46)


class Pal:
    def __init__(self, sprite, tag):
        self.sp, self.tag = sprite, tag
        self.list, self.slot = [], {}

    def __call__(self, index, key=None, **kw):
        """Material slot of palette `index`; key names a variant (steel, lens, ...)."""
        key = f"{index}" if key is None else f"{index}{key}"
        if key not in self.slot:
            args = dict(STONE)
            args.update(kw)
            t = self.tag if key == str(index) else f"{self.tag}_{key[len(str(index)):]}"
            self.list.append(common.palette_material(self.sp, index, t, **args))
            self.slot[key] = len(self.list) - 1
        return self.slot[key]

    def steel(self, index, **kw):
        a = dict(STEEL)
        a.update(kw)
        return self(index, "steel", **a)

    def index_of(self, slot):
        return int(self.list[slot].name.split("_")[1])


# --- art-driven stones ---------------------------------------------------------------------------

def art_median(sprite_px, x0, y0, x1, y1):
    vals = sorted(sprite_px[y][x] for y in range(max(0, int(y0)), min(28, int(math.ceil(y1))))
                  for x in range(max(0, int(x0)), min(24, int(math.ceil(x1)))))
    if not vals:
        return 5
    k = len(vals) // 6
    core = vals[k:len(vals) - k] or vals
    return core[len(core) // 2]


def stone(M, P, rnd, x0, y0, x1, y1, z0, h, base):
    """A faceted rubble stone filling its box (the kit's stone: foot, shoulder ring at uneven
    heights, smaller crown ring, off-centre peak), each facet coloured by facet_ramp round base."""
    n = rnd.choice((6, 7, 7, 8))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ax, ay = (x1 - x0) / 2 - 0.12, (y1 - y0) / 2 - 0.12
    a0 = rnd.uniform(0, 2 * math.pi)
    ta = rnd.uniform(0, 2 * math.pi)
    tilt = 0.18 + 0.14 * rnd.random()
    foot, sh, cr = [], [], []
    for k in range(n):
        a = a0 + 2 * math.pi * (k + rnd.uniform(-0.2, 0.2)) / n
        c, s_ = math.cos(a), math.sin(a)
        m = max(abs(c), abs(s_)) ** 0.6
        f = rnd.uniform(0.88, 1.0)
        fx, fy = cx + ax * f * c / m, cy + ay * f * s_ / m
        foot.append((fx, fy, z0 - 0.2))
        g = 0.78 + 0.14 * rnd.random()
        zsh = z0 + h * (0.5 + 0.16 * rnd.random() + tilt * math.cos(a - ta))
        sh.append((cx + (fx - cx) * g, cy + (fy - cy) * g, min(zsh, z0 + h - 0.05)))
        a2 = a + rnd.uniform(-0.25, 0.25)
        g2 = 0.42 + 0.16 * rnd.random()
        zc = z0 + h * (0.82 + 0.08 * rnd.random() + 0.5 * tilt * math.cos(a2 - ta))
        cr.append((cx + ax * g2 * math.cos(a2) / m, cy + ay * g2 * math.sin(a2) / m, min(zc, z0 + h - 0.02)))
    po = 0.25 * min(ax, ay) * rnd.random()
    apex = (cx + po * math.cos(ta), cy + po * math.sin(ta), z0 + h)
    F, S, C = M.ring(foot), M.ring(sh), M.ring(cr)
    A = M.vert(apex)
    faces = []
    for i in range(n):
        j = (i + 1) % n
        for t in ((F[i], F[j], S[j]), (F[i], S[j], S[i]), (S[i], S[j], C[j]), (S[i], C[j], C[i]), (C[i], C[j], A)):
            faces.append(M.bm.faces.new(t))
    bottom = M.bm.faces.new(list(reversed(F)))
    bmesh.ops.recalc_face_normals(M.bm, faces=faces + [bottom])
    jit = rnd.choice((-1, 0, 0, 0, 1))
    for f in faces:
        f.normal_update()
        f.material_index = P(facet_ramp(f.normal, base + jit))
        f.smooth = False
    bottom.material_index = P(max(1, base - 2))


def brick(M, P, rnd, x0, y0, x1, y1, z0, z1, idx, bev=0.55):
    """A worn paving brick (D148/D150): a short wall, then every edge bevelled (the long sides more)
    with each corner worn to its own height and inset, the top a little out of level. The bevel
    facets take facet_ramp round the brick's art index (lit to the sun, dark away), the top keeps it."""
    horiz = (x1 - x0) >= (y1 - y0)
    bl = min(bev, 0.3 * ((y1 - y0) if horiz else (x1 - x0)))   # long-side bevel
    be = 0.28                                                  # end bevel
    bx, by = (be, bl) if horiz else (bl, be)
    zm = z1 - 0.32
    lo = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]
    md = [(x0, y0, zm), (x1, y0, zm), (x1, y1, zm), (x0, y1, zm)]
    sg = ((1, 1), (-1, 1), (-1, -1), (1, -1))
    hi = []
    for (x, y, _), (sx, sy) in zip(md, sg):
        w = rnd.uniform(0.75, 1.35)
        hi.append((x + sx * bx * w, y + sy * by * w, z1 - rnd.uniform(0.0, 0.14)))
    L, Mi, H = M.ring(lo), M.ring(md), M.ring(hi)
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.append((M.bm.faces.new((L[i], L[j], Mi[j], Mi[i])), "wall"))
        faces.append((M.bm.faces.new((Mi[i], Mi[j], H[j])), "bev"))
        faces.append((M.bm.faces.new((Mi[i], H[j], H[i])), "bev"))
    faces.append((M.bm.faces.new((H[0], H[1], H[2])), "top"))
    faces.append((M.bm.faces.new((H[0], H[2], H[3])), "top"))
    faces.append((M.bm.faces.new(list(reversed(L))), "bottom"))
    bmesh.ops.recalc_face_normals(M.bm, faces=[f for f, _ in faces])
    for f, kind in faces:
        f.normal_update()
        f.smooth = False
        if kind == "top":
            f.material_index = P(idx)
        elif kind == "bottom":
            f.material_index = P(max(1, idx - 2))
        else:
            f.material_index = P(facet_ramp(f.normal, idx))


# --- the ground tile -----------------------------------------------------------------------------

LEFT_RUBBLE = [(0, 0, 3.2, 3.4, 1.0), (0, 3.6, 3.3, 6.0, 0.8), (0, 6.2, 3.4, 9.6, 0.9), (0, 9.8, 3.3, 13.4, 1.0)]
LEDGE_STONES = [(0, 14.6, 2.6, 17.6, 0.8), (2.6, 14.7, 5.2, 17.3, 0.7)]
GLACIS_STONES = [(0, 18.4, 2.5, 22.6, 0.7), (2.5, 18.8, 4.9, 22.4, 0.6)]
BANK_STONES = [(21.0, -0.2, 24.0, 2.5, 0.6), (21.6, 2.7, 24.0, 5.0, 0.5), (21.4, 5.2, 24.0, 8.2, 0.55), (22.0, 8.6, 24.0, 12.0, 0.45),
               (22.0, 12.2, 24.0, 18.0, 0.5), (20.2, 18.8, 24.0, 22.8, 0.7)]
BRICKS = [(0, 23.6, 3.8, 27.8), (4.0, 23.6, 7.8, 27.8), (8.0, 23.6, 10.8, 27.8), (11.0, 23.6, 15.8, 27.8),
          (16.0, 23.6, 19.8, 27.8), (20.0, 23.6, 24.0, 27.8)]

GL_Y0, GL_Y1 = 15.4, 23.0   # glacis from the kerb down to the floor


def glacis_z(y):
    t = min(max((y - GL_Y0) / (GL_Y1 - GL_Y0), 0.0), 1.0)
    return Z_TERR + (Z_FLOOR - Z_TERR) * t


def _lerp_pts(pts, y):
    if y <= pts[0][0]:
        return pts[0][1]
    for (ya, va), (yb, vb) in zip(pts, pts[1:]):
        if y <= yb:
            return va + (vb - va) * (y - ya) / (yb - ya)
    return pts[-1][1]


TR_X0 = [(14.9, 16.0), (15.3, 16.9)]                  # west start of the trench mesh (terrace lip)
TR_EDGE = [(11.8, 19.25), (14.4, 17.35)]              # the trench's west lip (plan), by y
TR_EAST = 21.15                                       # tucks under the east bank's chamfer
TR_YS = [-0.3, 1.2, 2.6, 4.0, 5.4, 6.8, 8.2, 9.6, 10.8, 11.8, 13.0, 14.4, 15.3, 16.6, 18.0, 19.4, 20.8, 22.2, 23.4]
TR_U = [(0.0, 0.0), (0.2, 0.55), (0.42, 1.0), (0.66, 1.0), (0.84, 0.45), (1.0, 0.0)]   # (across, depth)


def trench(M, P):
    """The east ditch (sprite cols 17-21): a jittered rock heightfield from the terrace lip down to a
    rubble floor and up to the east bank. Each facet takes facet_ramp round the art's own trench
    median (3: the floor's flat facets land on 3, the sunlit west-facing bank wall on 4-5, the wall
    turned away on 2). The deep shade is left to the AO bake and the game's light (lighting, not paint)."""
    rnd = random.Random(2373)
    z_fl = Z_FLOOR + 0.12
    rows = []
    for j, y in enumerate(TR_YS):
        x0 = _lerp_pts(TR_X0, y)
        xe = _lerp_pts(TR_EDGE, y)
        top = Z_TERR - 0.02 if y < GL_Y0 else glacis_z(y) - 0.02
        last = j == len(TR_YS) - 1
        row = [(x0, y, top)]
        for k, (u, dep) in enumerate(TR_U):
            x = xe + (TR_EAST - xe) * u
            zt = top + (Z_BANK - 0.12 - top) * u
            z = zt + (z_fl - zt) * dep
            if 0 < k < len(TR_U) - 1 and 0 < j and not last:
                x += rnd.uniform(-0.18, 0.18)
                z += rnd.uniform(-0.1, 0.16) * (1.0 if dep > 0.9 else 0.7)
            yy = y + (rnd.uniform(-0.3, 0.3) if 0 < j and not last and 0 < k < len(TR_U) - 1 else 0.0)
            if last:
                z = Z_FLOOR + 0.05
            row.append((x, yy, z))
        rows.append([M.vert(p) for p in row])
    for j in range(len(rows) - 1):
        for i in range(len(rows[0]) - 1):
            q = (rows[j][i], rows[j + 1][i], rows[j + 1][i + 1], rows[j][i + 1])
            tris = ((q[0], q[1], q[2]), (q[0], q[2], q[3])) if (i + j) % 2 else ((q[0], q[1], q[3]), (q[1], q[2], q[3]))
            for tri in tris:
                f = M.bm.faces.new(tri)
                f.normal_update()
                if f.normal.z < 0:
                    f.normal_flip()
                if i == 0:   # the flat terrace lip
                    f.material_index = P(facet_ramp(f.normal, 5))
                else:
                    f.material_index = P(max(2, facet_ramp(f.normal, 2 if f.normal.z > 0.9 else 3)))


def ground(M, P, px, rnd):
    """The tile under the bunker. Plain parts (bricks, stones) go to M; the rest too (one mesh)."""
    # floor plate, whole tile, and the bricks' groove floor
    rbox(M, 0, 0, 24, 28, -0.3, Z_FLOOR, 0.0, 0.0, P(3), P(3))
    # terrace under the bunker and the west rubble (its east part is the trench's flat lip, below)
    rbox(M, -0.01, -0.01, 16.2, 14.6, Z_FLOOR - 0.1, Z_TERR, 0.4, 0.5, P(6), P(4), P(4))
    # the east ditch: a rough rock trench (not a void), faceted by D148's rock rule
    trench(M, P)
    # the lit kerb along row 14: a run of dressed kerb stones (each a little different)
    x = -0.01
    k = 0
    for w in (2.7, 2.4, 2.9, 2.6, 2.8, 3.0):
        x1 = min(x + w, 16.6)
        zt = Z_KERB + rnd.uniform(-0.08, 0.08)
        rbox(M, x + 0.08, 13.9 + rnd.uniform(0, 0.1), x1 - 0.08, 15.4 - rnd.uniform(0, 0.1), Z_TERR - 0.2, zt, 0.15, 0.3,
             P(8), P(6), P(9))
        x = x1
        k += 1
        if x >= 16.6:
            break
    # the glacis: a rough rock face sloping from the kerb to the floor (faceted, dark: the art's 4)
    gx0, gx1 = 4.9, 16.9
    nx, ny = 8, 5
    grid = []
    grnd = random.Random(2371)
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            xx = gx0 + (gx1 - gx0) * i / nx
            yy = GL_Y0 - 0.2 + (GL_Y1 - GL_Y0 + 0.2) * j / ny
            jx = grnd.uniform(-0.35, 0.35) if 0 < i < nx else 0
            jy = grnd.uniform(-0.3, 0.3) if 0 < j < ny else 0
            zz = glacis_z(yy) + (grnd.uniform(-0.25, 0.3) if 0 < i < nx and 0 < j < ny else 0)
            row.append(M.vert((xx + jx, yy + jy, zz)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            q = (grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1])
            for tri in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
                f = M.bm.faces.new(tri)
                f.normal_update()
                if f.normal.z < 0:
                    f.normal_flip()
                cxp = sum(v.co.x for v in tri) / 3 * 12 + 12
                cyp = 14 - sum(v.co.y for v in tri) / 3 * 12
                base = art_median(px, cxp - 1.2, cyp - 1.2, cxp + 1.2, cyp + 1.2)
                f.material_index = P(facet_ramp(f.normal, max(base, 3)))
    # skirt under the glacis' edges (closed enough for the outline-free ground)
    rbox(M, gx0, GL_Y0 - 0.3, gx1, GL_Y1, Z_FLOOR - 0.1, Z_FLOOR + 0.2, 0.0, 0.0, P(3), P(3))
    # glacis west part: rough fill a little proud, so the stones sit in it
    rbox(M, 0, GL_Y0, 4.95, GL_Y1 - 0.5, Z_FLOOR, Z_TERR - 0.1, 0.3, 0.0, P(5), P(4),
         zf=lambda x, y, z: z if z < Z_TERR - 0.5 else glacis_z(y) + 0.05)
    # east bank beyond the ditch
    rbox(M, 21.0, -0.01, 24.01, 23.4, Z_FLOOR - 0.1, Z_BANK, 0.4, 0.25, P(4), P(3), P(5))


def rubble(M, P, px, rnd):
    for x0, y0, x1, y1, h in LEFT_RUBBLE:
        stone(M, P, rnd, x0, y0, x1, y1, Z_TERR, h, art_median(px, x0, y0, x1, y1))
    for x0, y0, x1, y1, h in LEDGE_STONES:
        stone(M, P, rnd, x0, y0, x1, y1, Z_KERB - 0.35, h, art_median(px, x0, y0, x1, y1))
    for x0, y0, x1, y1, h in GLACIS_STONES:
        stone(M, P, rnd, x0, y0, x1, y1, glacis_z((y0 + y1) / 2), h, art_median(px, x0, y0, x1, y1))
    for x0, y0, x1, y1, h in BANK_STONES:
        stone(M, P, rnd, x0, y0, x1, y1, Z_BANK if y1 < 19 else Z_FLOOR + 0.2, h + (0 if y1 < 19 else 0.3),
              art_median(px, x0, y0, x1, y1))
    brnd = random.Random(2372)
    for x0, y0, x1, y1 in BRICKS:
        brick(M, P, brnd, x0 + 0.12, y0 + 0.12, x1 - 0.12, y1 - 0.12, Z_FLOOR - 0.1, Z_FLOOR + 0.55 + rnd.uniform(-0.05, 0.05),
              max(art_median(px, x0, y0, x1, y1), 5))


# --- the housing ---------------------------------------------------------------------------------

HX0, HY0, HX1, HY1 = 3.5, -0.01, 19.0, 14.0   # footprint
HR = 3.0                                     # plan corner radius
NPER = 72                                    # facets round the walls


def housing_shell(ctx, P, coll, name, mats, well, seed):
    """The dressed-stone housing: a battered, chisel-faceted wall (every ring jittered a little in
    and the walls flat shaded), a bevelled deck top, an inner chamfer and well walls down to the
    floor. Closed (for the booleans). well = (x0, y0, x1, y1) at the deck."""
    rnd = random.Random(seed)
    WX0, WY0, WX1, WY1 = well
    lv = [(0, Z_TERR - 0.2), (0, Z_TERR + H_PLINTH), (0.25, Z_TERR + H_PLINTH + 0.05),
          (0.6, Z_TERR + 2.2), (1.0, Z_DECK - 0.5), (1.5, Z_DECK)]
    rings = []
    jit = [rnd.uniform(-0.28, 0.06) for _ in range(NPER)]
    jit2 = [rnd.uniform(-0.28, 0.06) for _ in range(NPER)]
    for li, (d, z) in enumerate(lv):
        base = resample(rrect(HX0 + d, HY0 + d, HX1 - d, HY1 - d, max(HR - d, 0.4), 6), NPER)
        cx, cy = (HX0 + HX1) / 2, (HY0 + HY1) / 2
        ring = []
        for i, (x, y) in enumerate(base):
            # outward direction from the plan centre (good enough for a rounded box)
            nx_, ny_ = x - cx, y - cy
            L = math.hypot(nx_, ny_) or 1
            j = 0.0 if li <= 1 else (jit[i] if li in (3, 5) else jit2[i])
            if HY0 + d + 0.01 >= y and li >= 2:   # keep the north edge on the tile
                j = min(j, 0.0)
            zz = z + (rnd.uniform(-0.07, 0.07) if li == 5 else 0.0)
            ring.append((x + j * nx_ / L, max(y + j * ny_ / L, -0.01), zz))
        rings.append(ring)
    H = Mesh(ctx)
    vr = H.stack(rings, [P(7), P(7), P(9), P(9), P(10)], bottom=P(9))
    il = [(x, y, Z_DECK - 0.02) for x, y in resample(rrect(WX0 - 0.45, WY0 - 0.45, WX1 + 0.45, WY1 + 0.45, 1.0, 6), NPER)]
    iw = [(x, y, Z_DECK - 0.5) for x, y in resample(rrect(WX0, WY0, WX1, WY1, 0.5, 6), NPER)]
    ib = [(x, y, Z_WELL) for x, y in resample(rrect(WX0 + 0.3, WY0 + 0.2, WX1 - 0.3, WY1 - 0.2, 0.4, 6), NPER)]
    vil, viw, vib = H.ring(il), H.ring(iw), H.ring(ib)
    H.bridge(vr[-1], vil, P(9))
    H.bridge(vil, viw, P(8))
    H.bridge(viw, vib, P(4))
    H.face(list(reversed(vib)), P(3))
    o = H.obj(name + "_h", mats, coll)
    # wall facet colours: the art lights the west wall (13-14), keeps north/south 9-10, east 8-9
    for f in o.data.polygons:
        n = f.normal
        if f.material_index in (P(9), P(10)) and n.z < 0.8 and f.center.z * 12 < Z_DECK - 0.3:
            if n.x < -0.45:
                f.material_index = P(10)
            elif n.x > 0.55:
                f.material_index = P(8)
            else:
                f.material_index = P(9)
    return o


def box_obj(ctx, P, coll, name, mats, x0, y0, x1, y1, z0, z1):
    B = Mesh(ctx)
    rbox(B, x0, y0, x1, y1, z0, z1, 0.0, 0.0, P(3), P(3))
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


def housing(ctx, P, coll, name, mats, well, seed):
    """Two stone blocks with a deep joint between them across the walls at row 6.5 (the sprite's
    dark notch on both sides), the joint stopping at the well's lip."""
    o = housing_shell(ctx, P, coll, name, mats, well, seed)
    WX0, WY0, WX1, WY1 = well
    for x0, x1 in ((-5, WX0 - 0.7), (WX1 + 0.7, 30)):
        boolean(o, box_obj(ctx, P, coll, name, mats, x0, 6.28, x1, 6.72, Z_TERR + 0.7, 20), "DIFFERENCE")
    return o


# --- the well, the seat frame, the hinge, the lid, the rams ------------------------------------

def seat_frame(M, P, well, ay):
    """The steel seat frame the lid closes on (cols 7 and 16, row 12 in the art: 7, 8)."""
    WX0, WY0, WX1, WY1 = well
    s = P.steel(7)
    z0, z1 = ZL_BOT - 0.55, ZL_BOT
    rbox(M, WX0 + 0.02, ay + 0.3, LID_X0 + 0.35, WY1 - 0.02, z0, z1, 0.0, 0.12, s, s)
    rbox(M, LID_X1 - 0.35, ay + 0.3, WX1 - 0.02, WY1 - 0.02, z0, z1, 0.0, 0.12, s, s)
    rbox(M, LID_X0 + 0.35, max(ay + LID_LEN + AX_GAP - 0.35, WY1 - 0.8), LID_X1 - 0.35, WY1 - 0.02, z0, z1, 0.0, 0.12, P.steel(8), s)


def hinge_static(M, P, ay, az, well):
    """The frame side of the hinge: a steel hinge block bolted to the north rim, three knuckles
    (the art's row 2: 6-8, its lit 8s mid-row are the middle knuckle) and the pin's end caps."""
    WX0, WY0, WX1, WY1 = well
    s7, s8, s10 = P.steel(7), P.steel(8), P.steel(10)
    # the block (its north face set into the deck)
    rbox(M, WX0 - 0.2, ay - 0.95, WX1 + 0.2, ay + 0.2, Z_DECK - 1.6, az - 0.15, 0.2, 0.15, s7, P.steel(6), P.steel(8))
    for x0, x1 in ((WX0 + 0.15, 8.75), (11.1, 12.9), (15.25, WX1 - 0.15)):
        cyl_x(M, x0, x1, ay, az, KN_R, s8, seg=12, ch=0.1)
    cyl_x(M, WX0 - 0.05, WX0 + 0.2, ay, az, 0.32, s10, seg=10)
    cyl_x(M, WX1 - 0.2, WX1 + 0.05, ay, az, 0.32, s10, seg=10)
    for x in (WX0 + 0.6, WX1 - 0.6):
        bolt(M, x, ay - 0.6, az - 0.15, 0.26, s10, h=0.15)


def lid(M, P, ay, az, ang):
    """The armoured hatch lid, built shut and turned `ang` about the hinge axis (y = ay, z = az):
    a chamfered steel plate with a raised top panel and four bolts, its two lid-side knuckles,
    and under it a seal lip, two stiffener ribs, a cross rib and the rams' clevis lugs (the
    underside the tilted camera sees once it stands open)."""
    M.xf = rot_x(ay, az, ang)
    y0 = ay + AX_GAP
    y1 = y0 + LID_LEN - AX_GAP
    # the outer face: satin 9 while the lid is shut or part open; standing open (283, 237/239) the
    # sprite draws the face and its free-end bevel as the lit cap edge (rows 3-4: 11-12)
    up = ang >= math.radians(70)
    top9 = P.steel(11 if up else 9)
    edge7 = P.steel(7)
    bev = P.steel(12 if up else 10)
    under = P.steel(6)
    # plate: bottom chamfer, end/side faces (7: the art's row under a raised lid), top bevel lit
    lv = [(0.2, ZL_BOT), (0, ZL_BOT + 0.2), (0, ZL_TOP - 0.32), (0.32, ZL_TOP)]
    rings = rr_levels(LID_X0, y0, LID_X1, y1, 0.45, lv, 3)
    M.stack(rings, [under, edge7, bev], top=top9, bottom=under)
    # the raised top panel (a panel line round it) and its bolts
    # one uniform satin plate (no per-face palette split: its panel line is geometry and AO only)
    rbox(M, LID_X0 + 1.05, y0 + 1.15, LID_X1 - 1.05, y1 - 1.15, ZL_TOP - 0.2, ZL_TOP + 0.12, 0.35, 0.12, top9, top9, top9)
    for x in (LID_X0 + 0.55, LID_X1 - 0.55):
        for y in (y0 + 0.75, y1 - 0.55):
            bolt(M, x, y, ZL_TOP, 0.26, P.steel(10), h=0.16)
    # lid-side knuckles on the hinge axis (they join the plate's north edge with a web)
    for x0, x1 in ((8.85, 11.0), (13.0, 15.15)):
        cyl_x(M, x0, x1, ay, az, KN_R, edge7, seg=12, ch=0.1)
        rbox(M, x0 + 0.1, ay - 0.05, x1 - 0.1, y0 + 0.4, az - KN_R + 0.05, az + 0.1, 0.0, 0.0, edge7, edge7)
    # underside: seal lip ring (four strips), stiffener ribs, cross rib, clevis lugs
    zl = ZL_BOT - 0.28
    for (a, b, c, d) in ((LID_X0 + 0.45, y0 + 0.45, LID_X1 - 0.45, y0 + 0.85), (LID_X0 + 0.45, y1 - 0.85, LID_X1 - 0.45, y1 - 0.45),
                         (LID_X0 + 0.45, y0 + 0.85, LID_X0 + 0.85, y1 - 0.85), (LID_X1 - 0.85, y0 + 0.85, LID_X1 - 0.45, y1 - 0.85)):
        rbox(M, a, b, c, d, zl, ZL_BOT + 0.05, 0.0, 0.0, P.steel(5), P.steel(5))
    for xr in (10.6, 13.4):
        rbox(M, xr - 0.25, y0 + 0.85, xr + 0.25, y1 - 0.85, ZL_BOT - 0.5, ZL_BOT + 0.05, 0.0, 0.0, under, under)
    rbox(M, LID_X0 + 0.85, y0 + 4.2, LID_X1 - 0.85, y0 + 4.7, ZL_BOT - 0.5, ZL_BOT + 0.05, 0.0, 0.0, under, under)
    for xr in RAM_X:
        rbox(M, xr - 0.42, ay + RAM_S - 0.45, xr + 0.42, ay + RAM_S + 0.45, ZL_BOT - 0.75, ZL_BOT + 0.05, 0.1, 0.0, P.steel(5), P.steel(5))
    M.xf = None


def ram_points(ay, az, ang, base_y):
    """The rams' foot (on the well floor) and head (the lid's clevis) for a lid angle."""
    f = rot_x(ay, az, ang)
    out = []
    for xr in RAM_X:
        head = f((xr, ay + RAM_S, ZL_BOT - 0.55))
        foot = (xr, base_y, Z_WELL + 0.55)
        out.append((foot, head))
    return out


def rams(M, P, ay, az, ang, base_y):
    """Two telescopic rams (body, stage, rod) from pivot blocks on the well floor to the lid."""
    for foot, head in ram_points(ay, az, ang, base_y):
        a, b = Vector(foot), Vector(head)
        D = (b - a).length
        d = (b - a).normalized()
        body = min(3.6, D - 0.6)
        e1 = min(max((D - body) / 2 + 0.3, 0.4), 3.0)
        rbox(M, foot[0] - 0.55, base_y - 0.6, foot[0] + 0.55, base_y + 0.6, Z_WELL - 0.05, Z_WELL + 0.4, 0.15, 0.1, P.steel(5), P.steel(4))
        cyl_x(M, foot[0] - 0.5, foot[0] + 0.5, base_y, Z_WELL + 0.55, 0.32, P.steel(6), seg=10)
        cyl_between(M, a, a + d * body, 0.42, P.steel(5), seg=10)
        s0 = body - 0.3
        cyl_between(M, a + d * s0, a + d * min(s0 + e1, D - 0.3), 0.3, P.steel(7), seg=10)
        cyl_between(M, a + d * min(s0 + e1 - 0.3, D - 0.5), b, 0.2, P.steel(10, roughness=0.3), seg=8)
        cyl_x(M, head[0] - 0.45, head[0] + 0.45, head[1], head[2], 0.24, P.steel(10), seg=8)


def socket(M, P, lens, LP):
    """The launcher's bezel on the well floor (cols 9-14, rows 6-10) and the lens, raised or sunk."""
    cx, cy = 12.0, 8.0
    rbox(M, 9.15, 5.3, 14.85, 10.7, Z_WELL - 0.1, Z_WELL + 1.2, 1.3, 0.35, LP["socket"], P.steel(4), P.steel(7))
    # dark bore ring round the lens (the art's 32 at the lens's corners)
    cyl(M, cx, cy, Z_WELL + 1.1, Z_WELL + 1.27, 2.4, P(32, "bore", metallic=0.0, roughness=0.9), seg=24, smooth=False)
    if lens:
        cyl(M, cx, cy, Z_WELL + 0.9, Z_WELL + 2.2, 2.1, P.steel(5), seg=24, ch=0.15)
        dome(M, cx, cy, Z_WELL + 2.1, 1.95, 1.95, 1.25, LP["lens"], seg=24, rings=5)
        dome(M, cx, cy, Z_WELL + 3.15, 1.0, 1.0, 0.35, LP["core"], seg=12, rings=3)
    else:
        # sunk: the lens's dark glass deep in the bore, the barrel's top ring just showing
        cyl(M, cx, cy, Z_WELL + 0.6, Z_WELL + 1.0, 2.1, P.steel(5), seg=24, ch=0.12)
        dome(M, cx, cy, Z_WELL + 0.95, 1.85, 1.85, 0.3, P(113, "glass", metallic=0.0, roughness=0.25), seg=24, rings=3)


def silo_shaft(M, P, well):
    """newshp-53's well: the deep dark shaft, its stepped south wall (the art's lit row 10) and the
    missile's nose waiting in it."""
    WX0, WY0, WX1, WY1 = well
    rbox(M, WX0 + 0.3, 9.7, WX1 - 0.3, WY1 - 0.2, Z_WELL - 0.1, Z_WELL + 1.4, 0.3, 0.3, P(5), P(4), P(6))
    rbox(M, WX0 + 0.35, WY0 + 0.2, WX1 - 0.35, 9.7, Z_WELL - 0.1, Z_WELL + 0.02, 0.3, 0.0, P(1), P(1))
    cyl(M, 12.0, 6.0, Z_WELL, Z_WELL + 0.6, 1.5, P.steel(3), seg=16)
    dome(M, 12.0, 6.0, Z_WELL + 0.6, 1.5, 1.5, 1.5, P.steel(3), seg=16, rings=4)


def deck_bolts(M, P):
    for x, y in ((5.6, 1.7), (16.9, 1.7), (5.6, 12.5), (16.9, 12.5)):
        bolt(M, x, y, Z_DECK, 0.36, P.steel(10), h=0.18)


# --- models --------------------------------------------------------------------------------------

WELL_EYE = (7.0, 2.0, 17.0, 12.4)
WELL_SILO = (7.0, 1.35, 17.0, 12.4)
AY_EYE = 2.75
AY_SILO = 0.45

STATES = [
    ("newshp-237", "newshp-237", {"kind": "eye", "ang": 75.0, "lens": True}),
    ("newshp-237-f2", "newshp-237", {"kind": "eye", "ang": 60.0}),
    ("newshp-237-f3", "newshp-237", {"kind": "eye", "ang": 0.0}),
    ("newshp-237-f4", "newshp-237", {"kind": "eye", "ang": 44.0}),
    ("newshp-237-f5", "newshp-237", {"kind": "eye", "ang": 75.0}),
    ("newshp-53", "newshp-53", {"kind": "silo", "ang": 50.0}),
]

FRAMES = {
    "newshp-237": (237, 239), "newshp-237-f2": (245,), "newshp-237-f3": (279,),
    "newshp-237-f4": (281,), "newshp-237-f5": (283,),
}


def bunker(name, sprite, coll, state):
    ctx = Ctx(24, 28)
    P = Pal(sprite, name)
    px = sprite["frames"][0]["pixels"]
    silo = state["kind"] == "silo"
    well = WELL_SILO if silo else WELL_EYE
    ay = AY_SILO if silo else AY_EYE
    az = ZL_TOP + AX_DZ
    ang = math.radians(state["ang"])
    LP = {"socket": P.steel(5)}
    if state.get("lens"):
        LP = {"socket": P(5, "socket", frames={239: 8}, **STEEL),
              "lens": P(113, "lens", emission_strength=2.0, frames={239: 118}, metallic=0.0, roughness=0.25),
              "core": P(117, "core", emission_strength=4.0, frames={239: 123}, metallic=0.0, roughness=0.2)}
    for i in (3, 4, 5, 6, 7, 8, 9, 10):   # the slots exist before the objects take the list
        P(i)
    rnd = random.Random(237)
    # plain parts (left out of the bake): rubble stones, bricks
    R = Mesh(ctx)
    rubble(R, P, px, rnd)
    # baked parts: ground, frame, hinge, lid, rams, socket
    G = Mesh(ctx)
    ground(G, P, px, rnd)
    B = Mesh(ctx)   # the building's mechanism (in the outline shell)
    seat_frame(B, P, well, ay)
    hinge_static(B, P, ay, az, well)
    lid(B, P, ay, az, ang)
    deck_bolts(B, P)
    W = Mesh(ctx)   # what sits in the well (not in the shell)
    base_y = 11.1
    rams(W, P, ay, az, ang, base_y)
    if silo:
        silo_shaft(W, P, well)
    else:
        socket(W, P, state.get("lens"), LP)
    for i in range(1, 15):
        if str(i) in sprite["colors"]:
            P(i)
    mats = P.list
    rocks = R.obj(name + "_rocks", mats, coll, recalc=False)
    gnd = G.obj(name, mats, coll)
    mech = B.obj(name + "_mech", mats, coll)
    well_o = W.obj(name + "_well", mats, coll)
    hs = housing(ctx, P, coll, name, mats, well, seed=53 if silo else 237)
    assert all(len(o.data.materials) == len(P.list) for o in (gnd, mech, well_o, hs, rocks))
    # the outline shell from the building only: housing + mechanism (lid, hinge)
    src = [o.copy() for o in (hs, mech)]
    for c, o in zip(src, (hs, mech)):
        c.data = o.data.copy()
        coll.objects.link(c)
    join(src)
    shell = common.outline_shell(src[0], coll, voxel=0.014, faces=2500, smooth=6, inside=0.006)
    shell.name = shell.data.name = f"{name}_outline"
    bpy.data.objects.remove(src[0], do_unlink=True)
    # one baked object (ground, housing, mechanism, well) and the plain rocks
    join([gnd, hs, mech, well_o])
    finish(gnd)
    finish(rocks, 1)
    return gnd, rocks, shell, P


def join(objs):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return objs[0]


def finish(o, angle=32):
    me = o.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(angle))


# --- bake (lib_l1bld._bake with grit, copied: shared files are not edited) ----------------------

def _emissive(m):
    if m is None or not m.use_nodes:
        return False
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    return bsdf is not None and bsdf.inputs["Emission Strength"].default_value > 0


def bake(obj, size, samples, ao, out_dir, skip, grit=None):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:  # noqa: BLE001
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.002, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    tag = obj.name
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        o_ = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = o_.inputs["Surface"].links[0].from_socket if o_.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        # steel keeps a clean satin bake: no stone grime or per-UV-island mottle on the lid and frame
        # (the island term drew irregular dark shapes across the lid's outer face)
        gr = grit if metal < 0.2 else None
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def mth(op, a, b_=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, val in enumerate((a, b_)):
                if val is None:
                    continue
                if isinstance(val, (int, float)):
                    n.inputs[k].default_value = val
                else:
                    nt.links.new(val, n.inputs[k])
            return n.outputs[0]

        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = ao[0]
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = ao[1]
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = mth("MINIMUM", mth("MULTIPLY", mth("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = mth("MULTIPLY", mth("POWER", ao_s.outputs["AO"], 0.8),
                   mth("ADD", 0.6, mth("MULTIPLY", ao_l.outputs["AO"], 0.4)))
        em = node("ShaderNodeEmission")
        comb = node("ShaderNodeCombineColor")
        mottle = None
        if gr:
            tc = node("ShaderNodeTexCoord")
            nz = node("ShaderNodeTexNoise")
            nz.inputs["Scale"].default_value = gr.get("scale", 6.0)
            nz.inputs["Detail"].default_value = 6.0
            nz.inputs["Roughness"].default_value = 0.62
            nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
            nz2 = node("ShaderNodeTexNoise")
            nz2.inputs["Scale"].default_value = gr.get("scale", 6.0) * 4.5
            nz2.inputs["Detail"].default_value = 3.0
            nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
            stain = mth("MINIMUM", mth("MAXIMUM", mth("MULTIPLY", mth("SUBTRACT", nz.outputs["Fac"], 0.48), 6.0), 0.0), 1.0)
            speck = mth("MINIMUM", mth("MAXIMUM", mth("MULTIPLY", mth("SUBTRACT", nz2.outputs["Fac"], 0.48), 6.0), 0.0), 1.0)
            isl = geo.outputs["Random Per Island"]
            wi = gr.get("island", 0.0)
            mottle = mth("MINIMUM", mth("ADD", mth("ADD", mth("MULTIPLY", stain, 0.6 * (1 - wi)), mth("MULTIPLY", speck, 0.4 * (1 - wi))),
                                        mth("MULTIPLY", isl, wi)), 1.0)
        if mode == "colour":
            if gr:
                val = mth("MINIMUM", mth("ADD", mth("ADD", gr["floor"], mth("MULTIPLY", occl, gr["occl"])),
                                         mth("MULTIPLY", edge, gr["edge"])), 1.0)
                val = mth("MULTIPLY", val, mth("SUBTRACT", 1.0, mth("MULTIPLY", mottle, gr["grime"])))
            else:
                val = mth("MINIMUM", mth("ADD", mth("ADD", 0.62, mth("MULTIPLY", occl, 0.45)), mth("MULTIPLY", edge, 0.12)), 1.0)
            for k in range(3):
                nt.links.new(val, comb.inputs[k])
        else:
            r = mth("ADD", rough, mth("SUBTRACT", mth("MULTIPLY", mth("SUBTRACT", 1.0, occl), 0.3), mth("MULTIPLY", edge, 0.14)))
            if gr:
                r = mth("ADD", r, mth("MULTIPLY", mth("SUBTRACT", mottle, 0.5), 2.0 * gr["rough"]))
            r = mth("MAXIMUM", mth("MINIMUM", r, 1.0), 0.05)
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
        nt.links.new(comb.outputs[0], em.inputs["Color"])
        o_ = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], o_.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=8, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            o_ = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], o_.inputs["Surface"])
        out_dir.mkdir(parents=True, exist_ok=True)
        img.filepath_raw = str(out_dir / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for i, m in enumerate(mats):
        if i in skip:
            continue
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


def bake_bunker(name, gnd, rocks, bakedir, shell=None):
    """Bake the building+ground object; the rocks' materials (shared slots) must stay plain, so the
    rocks get their own copies of the materials they use first."""
    # the rocks keep plain copies of their materials
    for i, m in enumerate(list(rocks.data.materials)):
        used = any(p.material_index == i for p in rocks.data.polygons)
        if used:
            c = m.copy()
            c.name = m.name + "_plain"
            rocks.data.materials[i] = c
    skip = {i for i, m in enumerate(gnd.data.materials) if _emissive(m)}
    # bake against this model alone: the outline shell (it hugs the building a hair outside) and the
    # models built before it in this run (common.reset_collection keeps their collections, all at the
    # origin) would catch the AO rays and bake zebra stripes over the lid and the housing walls
    keep = {gnd.name, rocks.name}
    hidden = [o for o in bpy.context.scene.objects if o.name not in keep and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    bake(gnd, 1024, 64, (0.025, 0.14), bakedir / name, skip, grit=GRIT)
    for o in hidden:
        o.hide_render = False


# --- measuring and rendering ---------------------------------------------------------------------

def measure(name, objs, sprite, frames):
    """Top-down raycast at every sprite pixel centre: hit mask and the palette index seen, against
    the sprite's indices per region. Returns a dict."""
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    keep = set(o.name for o in objs)
    hidden = []
    for o in scene.objects:
        if o.name not in keep or o.get("tyrian_outline"):
            if not o.hide_get():
                hidden.append(o)
    for o in hidden:
        o.hide_viewport = True
    dg.update()
    W, H = 24, 28
    grid = [[None] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            org = Vector(((x + 0.5 - 12) / 12, (14 - y - 0.5) / 12, 5.0))
            hit, loc, nor, idx, ob, mtx = scene.ray_cast(dg, org, Vector((0, 0, -1)))
            if hit:
                m = ob.material_slots[ob.data.polygons[idx].material_index].material if ob.data.polygons else None
                try:
                    grid[y][x] = int(m.name.split("_")[1])
                except Exception:
                    grid[y][x] = -1
    for o in hidden:
        o.hide_viewport = False
    out = {}
    for fi in frames:
        fr = next(f for f in sprite["frames"] if f["index"] == fi)
        px = fr["pixels"]
        hits = sum(1 for y in range(H) for x in range(W) if grid[y][x] is not None)
        opaque = sum(1 for y in range(H) for x in range(W) if px[y][x] >= 0)
        both = sum(1 for y in range(H) for x in range(W) if grid[y][x] is not None and px[y][x] >= 0)
        iou = both / max(1, hits + opaque - both)
        regions = region_boxes(name)
        reg = {}
        for rn, (x0, y0, x1, y1) in regions.items():
            sv = sorted(px[y][x] for y in range(y0, y1) for x in range(x0, x1) if px[y][x] >= 0 and px[y][x] < 32)
            mv = sorted(grid[y][x] for y in range(y0, y1) for x in range(x0, x1) if grid[y][x] is not None and 0 <= grid[y][x] < 32)
            med = lambda v: v[len(v) // 2] if v else None  # noqa: E731
            reg[rn] = {"sprite": med(sv), "model": med(mv)}
        out[fi] = {"iou_grid": round(iou, 4), "regions": reg}
    out["grid"] = [" ".join("%3s" % (v if v is not None else ".") for v in row) for row in grid]
    return out


def region_boxes(name):
    lid_rows = {"newshp-237-f3": (3, 12), "newshp-237-f4": (3, 9), "newshp-237-f2": (3, 7), "newshp-237-f5": (3, 5),
                "newshp-237": (3, 5), "newshp-53": (0, 6)}[name]
    return {"lid_top": (8, lid_rows[0], 16, lid_rows[1]), "housing_w": (4, 0, 7, 13), "housing_e": (17, 0, 19, 13),
            "housing_n": (6, 0, 17, 2), "housing_s": (7, 12, 17, 14), "glacis": (5, 15, 17, 23), "rubble_w": (0, 0, 4, 14),
            "bricks": (0, 24, 24, 28), "ditch": (17, 3, 20, 23)}


def setup_render(scene, res):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    w = scene.world or bpy.data.worlds.new("w")
    scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.32, 0.36, 0.45, 1)
    bg.inputs["Strength"].default_value = 0.9
    sun = bpy.data.objects.get("rsun")
    if sun is None:
        ld = bpy.data.lights.new("rsun", "SUN")
        ld.energy = 3.2
        ld.angle = math.radians(3)
        sun = bpy.data.objects.new("rsun", ld)
        scene.collection.objects.link(sun)
    d = Vector(SUN)
    sun.rotation_euler = d.to_track_quat("Z", "Y").to_euler()


def cam(scene, name, loc, look, ortho=None, lens=50):
    c = bpy.data.objects.get(name)
    if c is None:
        cd = bpy.data.cameras.new(name)
        c = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        c.data.type = "ORTHO"
        c.data.ortho_scale = ortho
    else:
        c.data.type = "PERSP"
        c.data.lens = lens
    c.data.clip_end = 100
    return c


def render_views(name, show, out_dir, under=False):
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o not in show
    views = {
        "top": ((0, 0, 4), (0, 0, 0), 28 / 12, (192, 224)),
        "game": ((0, -3.4 * math.sin(math.radians(32)), 3.4 * math.cos(math.radians(32)) + 0.35), (0, 0, 0.35), None, (420, 420)),
        "q": ((2.3, -2.3, 1.9), (0, 0, 0.4), None, (420, 380)),
        "q2": ((-2.3, 2.1, 1.8), (0, 0, 0.4), None, (420, 380)),
        "east": ((4, 0, 0.6), (0, 0, 0.6), 2.6, (420, 300)),
        "south": ((0, -4, 0.6), (0, 0, 0.6), 2.4, (420, 300)),
        "north": ((0, 4, 0.6), (0, 0, 0.6), 2.4, (420, 300)),
    }
    if under:
        views["under"] = ((1.4, -1.8, -2.0), (0, 0, 0.2), None, (300, 260))
    for v, (loc, look, ortho, res) in views.items():
        setup_render(scene, res)
        c = cam(scene, "cam_" + v, loc, look, ortho, lens=40 if v != "game" else 34)
        scene.camera = c
        scene.render.filepath = str(out_dir / f"{name}_{v}.png")
        bpy.ops.render.render(write_still=True)


# --- the homing mine (unchanged from the current script) ----------------------------------------

MINE_C = (6.5, 7.5)
MINE_R = 3.85
MINE_HZ = 3.0


class MinePal:
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


def mine(name, sprite, coll):
    ctx = Ctx(12, 14)
    frames = (190, 209, 228, 247, 266, 285)
    P = MinePal(sprite, name, metallic=0.45, roughness=0.42)
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

    lats = [math.radians(a) for a in range(-90, 91, 10)]
    rs = []
    for a in lats[1:-1]:
        rs.append([sph(a, 2 * math.pi * k / SEGM, R - 0.18, MINE_HZ - 0.18) for k in range(SEGM)])
    vr = M.stack(rs, [seam], smooth=True)
    bot = M.vert((cx, cy, zc - (MINE_HZ - 0.18)))
    top = M.vert((cx, cy, zc + (MINE_HZ - 0.18)))
    for k in range(SEGM):
        M.face((vr[0][(k + 1) % SEGM], vr[0][k], bot), seam, True)
        M.face((vr[-1][k], vr[-1][(k + 1) % SEGM], top), seam, True)
    lo = [math.radians(a) for a in (-80, -65, -50, -35, -20, -9)]
    rs = [[sph(a, 2 * math.pi * k / SEGM) for k in range(SEGM)] for a in lo]
    vr = M.stack(rs, [body], smooth=True)
    pole = M.vert((cx, cy, zc - MINE_HZ))
    for k in range(SEGM):
        M.face((vr[0][(k + 1) % SEGM], vr[0][k], pole), body, True)
    bz0, bz1 = zc - 0.75, zc + 0.75
    brs = []
    for z, rr in ((bz0 - 0.2, R - 0.05), (bz0, MINE_R - 0.1), (bz0 + 0.12, MINE_R), (bz1 - 0.12, MINE_R), (bz1, MINE_R - 0.1), (bz1 + 0.2, R - 0.05)):
        brs.append([(cx + rr * math.cos(2 * math.pi * k / SEGM), cy - rr * math.sin(2 * math.pi * k / SEGM), z) for k in range(SEGM)])
    M.stack(brs, [belt, belt, belt, belt, belt], top=belt, bottom=belt, smooth=True)
    gap = math.radians(5.5)
    up = [math.radians(a) for a in (9, 20, 32, 44, 55, 64)]
    for q in range(4):
        a0 = math.radians(45 + 90 * q) + gap
        a1 = math.radians(45 + 90 * (q + 1)) - gap
        n = 9
        grid = [[sph(lat, a0 + (a1 - a0) * j / n) for j in range(n + 1)] for lat in up]
        gv = [[M.vert(p) for p in row] for row in grid]
        for i in range(len(up) - 1):
            for j in range(n):
                M.face((gv[i][j], gv[i][j + 1], gv[i + 1][j + 1], gv[i + 1][j]), body, True)
        inner = [[M.vert(sph(lat, a0 + (a1 - a0) * j / n, R - 0.25, MINE_HZ - 0.25)) for j in range(n + 1)] for lat in up]
        for i in range(len(up) - 1):
            for j in range(n):
                M.face((inner[i][j], inner[i + 1][j], inner[i + 1][j + 1], inner[i][j + 1]), seam, True)
        for i in range(len(up) - 1):
            M.face((gv[i][0], gv[i + 1][0], inner[i + 1][0], inner[i][0]), seam)
            M.face((gv[i][n], inner[i][n], inner[i + 1][n], gv[i + 1][n]), seam)
        for j in range(n):
            M.face((gv[0][j], inner[0][j], inner[0][j + 1], gv[0][j + 1]), seam)
            M.face((gv[-1][j], gv[-1][j + 1], inner[-1][j + 1], inner[-1][j]), seam)
    zt = zc + MINE_HZ * math.sin(math.radians(64))
    rb = R * math.cos(math.radians(64)) + 0.15
    cyl(M, cx, cy, zt - 0.6, zt + 0.35, rb, boss, seg=24, ch=0.18)
    a, b = 0.5, 1.5
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


# --- main ----------------------------------------------------------------------------------------

def sprites_for(model, sprite):
    if model not in FRAMES:
        return sprite["sprites"]
    keep = FRAMES[model]
    return [{**s, "frames": [f for f in s["frames"] if f in keep]} for s in sprite["sprites"]
            if any(f in keep for f in s["frames"])]


def main(only=None):
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_bake = "--no-bake" not in args
    do_render = "--render" in args
    if only is None:
        only = {a for a in args if not a.startswith("--")} or None
    sprites = {n: common.load_sprite(WT, n) for n in ("newshp-237", "newshp-53", "newshp-171")}
    rdir = HERE / "renders"
    if do_render:
        rdir.mkdir(exist_ok=True)
    report = {}
    import tempfile
    bakedir = Path(tempfile.mkdtemp(prefix="nshp237_bake_"))
    for model, sp, state in STATES:
        if only and model not in only:
            continue
        coll = common.reset_collection(model)
        gnd, rocks, shell, P = bunker(model, sprites[sp], coll, state)
        tris = sum(len(p.vertices) - 2 for o in (gnd, rocks) for p in o.data.polygons)
        print(f"{model}: {tris} triangles (+ shell {len(shell.data.polygons)})")
        frames = FRAMES.get(model, (53,))
        report[model] = measure(model, [gnd, rocks], sprites[sp], frames)
        report[model]["triangles"] = tris
        if do_bake:
            bake_bunker(model, gnd, rocks, bakedir, shell)
        if do_render:
            render_views(model, [gnd, rocks], rdir, under=(model == "newshp-237"))
        common.export_sprite_model(WT, [gnd, rocks, shell], f"enemies/{model}", sprites_for(model, sprites[sp]),
                                   image_format="WEBP" if do_bake else "AUTO")
    if not only or "newshp-171" in only:
        coll = common.reset_collection("newshp-171")
        o, shell = mine("newshp-171", sprites["newshp-171"], coll)
        common.export_sprite_model(WT, [o, shell], "enemies/newshp-171", sprites["newshp-171"]["sprites"])
    (HERE / ("report_%s.json" % ("_".join(sorted(only)) if only else "all"))).write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
