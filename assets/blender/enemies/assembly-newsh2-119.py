"""Grey carapace bunker with a stepped pyramid roof (newsh2.shp 81 / 83 / 119 / 121): one 48 x 56 px
ground tile cut into four 24 x 28 pieces (sprite.json `assemblyLayout`; enemy types 125-128, seen in
episode 1 levels 1.28 and 1.3 and in episode 3). A hard-surface model in the player ships' manner
(DECISIONS D50-D53): the sprite is authoritative for the top-down plan, the parts it shows and
their palette colours; the detail goes where the tilted game camera sees it.

- Carapace: a dark grey (pal 4) armour shell, round at the back, splitting into two prongs at the
  front. Vertical flanks with an armour belt, chamfered shoulders and a dark (pal 2) deck whose
  visible strips are the seams between raised chamfered armour plates: a centre band between grooves
  at columns 17-18 and 23-24 (the sprite's dark seam columns), side plates split at row 12.5, a back
  cap split at row 6.5, and on each prong a narrow inner strip and an outer plate split from the long
  front plate at row 35, with hex rivets along the seams. The prong ends are chamfered on the
  outside as the sprite draws them, with a framed louvred vent in each nose and three flank vents.
- Roof: a level stepped tan pyramid on a wide base slab. In plan the slab is the sprite's delta (one
  45-degree edge from the point at row 12 to the wing tips at columns 5 and 36, row 28), its outer
  edge standing above the carapace's crown all round, undercut onto the crown over the shell. The
  pyramid is a four-faced kite on the delta (back point row 12.9, wing corners row 26.6, front point
  row 27.9) with its apex over the plan's middle (row 20.5), cut level into three tiers (ledges on
  risers: the tier seams), every edge chamfered and every big face a sunk panel, a machined cap on
  the apex and hex bolts round the slab. One ridge runs on the axis the whole length: faces left of
  it are lit colours (pal 24 back, 22 front), faces right of it shaded (pal 20 back, 19 front), the
  slab 22 / 20, the sprite's light / dark halves.
- Nose: a tan keel block and a straight, near-constant-width hex ram (about 2.2 px) with a clamp
  collar, from the keel to a short chisel at row 35.3 (pal 23).
- Legs: two tan hydraulic struts a side (pal 23) from clevis brackets on the carapace's shoulder,
  diagonally down to flanged feet in the dirt, on the sprite's 45-degree lines (the right ones a
  row lower, as drawn).
- Ground: the dirt tile, low relief from the sprite's own dirt pattern (palette 17-20 per facet,
  border flat so neighbouring tiles meet), and the sprite's black area at the lower right painted
  on it as a flat pal 1 stain (no modelled debris): the sprite's one asymmetry (the structure
  itself is mirror symmetric about pixel-edge column 20.5). It is built only as the bake's
  occluder and not exported (D67): in the game the HD ground shows round the bunker, and the
  bunker's real shadow falls on it.
Colours are the sprite's per-region medians (darkest shading and brightest highlight pixels left
out). Satin metal (metallic <= 0.2, roughness >= 0.5), no concept projection (maps.json
"bake": "model"): the script bakes the Talon's occlusion / roughness maps (usp_talon.bake_maps)
before the tile is cut into its pieces. Each piece also gets its cut of an outline shell of the
structure (common.outline_shell, D51, nodes newsh2-*_outline; the dirt is left out, so the tile's
square edges draw no ink line). No engines.

The game contract is unchanged: four pieces newsh2-81 / -83 / -119 / -121, cut with
common.split_assembly at the assemblyLayout positions (assembly centre = screen 260,153 = Blender
origin), exported to public/models/enemies/<piece>.glb with their spriteModels entries (one frame
each), palette materials pal_<index>_*.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-119.py
     [-- --preview out.png] [--no-bake] [--review DIR] [--out tile.glb]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)

NAME = "assembly-newsh2-119"
PIECES = ["newsh2-81", "newsh2-83", "newsh2-119", "newsh2-121"]
CX0, CY0 = 260, 153  # assembly centre in screen px = Blender origin
W, H = 48, 56
PX = 1 / 12
AX = 20.5  # mirror axis (pixel-edge column; the middle of pixel column 20)
PAINT_SHADOW = True  # the sprite's lower-right black area, as a flat stain on the dirt

# Material slots -> palette index
(D17, D18, D19, D20, SHELL, PLATE, RECESS, PYR_TOP, PYR, PIPE, COLLAR, SPIKE, SHADOW, STRUT, FRAME,
 PYR_LT, PYR_DK, PYR_DK2) = range(18)
PAL_OF = {D17: 17, D18: 18, D19: 19, D20: 20, SHELL: 4, PLATE: 4, RECESS: 2, PYR_TOP: 22, PYR: 21,
          PIPE: 23, COLLAR: 21, SPIKE: 23, SHADOW: 1, STRUT: 3, FRAME: 6, PYR_LT: 24, PYR_DK: 20, PYR_DK2: 19}
DIRT = (D17, D18, D19, D20, SHADOW)
TEXTURED = (D17, D18, D19, D20, SHELL, PLATE, RECESS, PYR_TOP, PYR, PIPE, COLLAR, SPIKE, STRUT, FRAME, PYR_LT, PYR_DK,
            PYR_DK2)
TINT = (0.97, 0.97, 1.0)


def materials(sprite):
    # Satin: low metallic, roughness >= 0.5, so flat plates catch a soft sheen, never a mirror wedge.
    spec = {D17: ("dirt_dk", 0.0, 0.95), D18: ("dirt", 0.0, 0.95), D19: ("dirt_lt", 0.0, 0.92),
            D20: ("dirt_hi", 0.0, 0.9), SHELL: ("shell", 0.15, 0.6), PLATE: ("plate", 0.15, 0.56),
            RECESS: ("seam", 0.1, 0.75), PYR_TOP: ("pyramid_top", 0.12, 0.62), PYR: ("pyramid", 0.12, 0.64),
            PIPE: ("pipe", 0.2, 0.5), COLLAR: ("collar", 0.15, 0.58), SPIKE: ("spike", 0.2, 0.52),
            SHADOW: ("shadow", 0.0, 1.0), STRUT: ("strut", 0.1, 0.8), FRAME: ("frame", 0.15, 0.55),
            PYR_LT: ("pyramid_lit", 0.12, 0.6), PYR_DK: ("pyramid_shade", 0.12, 0.66),
            PYR_DK2: ("pyramid_shade_low", 0.12, 0.68)}
    return [common.palette_material(sprite, PAL_OF[k], f"nsh2_119_{spec[k][0]}", metallic=spec[k][1],
                                    roughness=spec[k][2]) for k in range(len(PAL_OF))]


# --- geometry helpers (plan coordinates: c = pixel-edge column, r = pixel-edge row, z in px) -----

def P(c, r, z):
    return Vector(((c - W / 2) * PX, (H / 2 - r) * PX, z * PX))


def mirror_half(half):
    """A left half outline from the axis (top) round to the axis (bottom) -> the closed outline."""
    right = [(2 * AX - c, r) for c, r in reversed(half)]
    pts = half + right
    out = []
    for p in pts:
        if not out or (abs(out[-1][0] - p[0]) > 1e-6 or abs(out[-1][1] - p[1]) > 1e-6):
            out.append(p)
    if abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out


def area(pts):
    n = len(pts)
    return sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n)) / 2


def inset(pts, d):
    """Offset a closed outline inward by d (negative grows it), mitred corners (capped)."""
    n = len(pts)
    s = 1 if area(pts) > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0, e1 = (p1 - p0), (p2 - p1)
        if e0.length < 1e-9 or e1.length < 1e-9:
            out.append(tuple(p1))
            continue
        e0.normalize()
        e1.normalize()
        n0 = Vector((-e0.y, e0.x)) * s
        n1 = Vector((-e1.y, e1.x)) * s
        b = n0 + n1
        if b.length < 1e-6:
            b = n0
        b.normalize()
        k = d / max(0.35, b.dot(n0))
        q = p1 + b * k
        out.append((q.x, q.y))
    return out


def clip(poly, x0, x1, y0, y1):
    """Sutherland-Hodgman clip of a polygon to the box x0..x1, y0..y1."""
    def run(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia:
                    out.append(inter(a, b))
                out.append(b)
            elif ia:
                out.append(inter(a, b))
        return out

    def ix(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))

    def iy(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)
    pts = list(poly)
    for inside, inter in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)),
                          (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        if not pts:
            return []
        pts = run(pts, inside, inter)
    # drop near-duplicate points
    out = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-4:
            out.append(p)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 1e-4:
        out.pop()
    return out


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def ring(self, pts, z, zfun=None):
        return [self.bm.verts.new(P(c, r, z + (zfun(c, r) if zfun else 0.0))) for c, r in pts]

    def face(self, verts, mat, smooth=False):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        f.material_index = mat
        f.smooth = smooth
        return f

    def bands(self, rings, mats, cap0=None, cap1=None, smooth=False):
        """Side faces between equal-length rings; mats[i] between ring i and i+1; caps."""
        for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
            n = len(r0)
            for k in range(n):
                j = (k + 1) % n
                self.face((r0[k], r0[j], r1[j], r1[k]), mats[i], smooth)
        if cap0 is not None:
            self.face(list(reversed(rings[0])), cap0)
        if cap1 is not None:
            self.face(rings[-1], cap1)

    def prism(self, pts, z0, z1, ch, mat, top=None, zfun=None, chz=None, belt=None):
        """Vertical walls z0..z1-chz, a chamfer `ch` in to the top cap at z1 (material `top`)."""
        chz = ch if chz is None else chz
        top = mat if top is None else top
        if area(pts) < 0:
            pts = list(reversed(pts))
        rings = [self.ring(pts, z0, zfun)]
        mats = []
        if belt:  # (zb0, zb1, out): a protruding belt round the walls
            zb0, zb1, out = belt
            g = inset(pts, -out)
            rings += [self.ring(pts, zb0, zfun), self.ring(g, zb0 + out * 0.6, zfun), self.ring(g, zb1 - out * 0.6, zfun),
                      self.ring(pts, zb1, zfun)]
            mats += [mat, mat, mat, mat]
        rings += [self.ring(pts, z1 - chz, zfun), self.ring(inset(pts, ch), z1, zfun)]
        mats += [mat, mat]
        self.bands(rings, mats, cap0=mat, cap1=top)

    def tube(self, path, radius, mat, sides=10, caps=True, smooth=True):
        """A pipe through 3D points (c, r, z); `radius` a number or one per point."""
        pts = [P(*p) for p in path]
        radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
        rings = []
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            side = t.cross(ref).normalized()
            up = side.cross(t).normalized()
            # keep a mitre-ish ring at joints: scale by 1/cos(half angle)
            sc = 1.0
            if 0 < i < len(pts) - 1:
                a = (pts[i] - pts[i - 1]).normalized()
                b = (pts[i + 1] - pts[i]).normalized()
                sc = 1 / max(0.5, math.cos(a.angle(b) / 2))
            ring = []
            for k in range(sides):
                ang = 2 * math.pi * (k + 0.5) / sides
                ring.append(self.bm.verts.new(p + (side * math.cos(ang) + up * math.sin(ang)) * radii[i] * PX * sc))
            rings.append(ring)
        self.bands(rings, [mat] * (len(rings) - 1), cap0=mat if caps else None, cap1=mat if caps else None,
                   smooth=smooth)

    def hull(self, pts3, mat):
        verts = [self.bm.verts.new(P(*p)) for p in pts3]
        res = bmesh.ops.convex_hull(self.bm, input=verts)
        junk = [g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)]
        if junk:
            bmesh.ops.delete(self.bm, geom=list(set(junk)), context="VERTS")
        faces = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]
        bmesh.ops.dissolve_limit(self.bm, angle_limit=math.radians(1.0), verts=[v for v in verts if v.is_valid],
                                 edges=list({e for f in faces if f.is_valid for e in f.edges}))
        for f in {f for v in verts if v.is_valid for f in v.link_faces}:
            f.material_index = mat
            f.smooth = False


def pchip(xs, ys):
    import bisect
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


# --- the plan (sprite-fitted) -------------------------------------------------------------------

# Carapace half width at the round back (rows 3-8.5, the sprite's mask incl. its outline ring).
BACK_HW = pchip([3.0, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5], [4.2, 5.5, 7.4, 8.4, 9.4, 10.4, 10.85])
FLANK = AX - 11.05  # 9.45: carapace / prong outer edge from row 18 (the sprite's outline ring)
FLANK_BACK = AX - 10.85  # 9.65: rows 8.5-17.5
PRONG_IN = 18.0    # prong inner edge (the gap is columns 18-22)
CROTCH = 28.8      # the shell's front wall between the prongs
CHAMF_R0, TIP_R = 42.9, 47.0  # prong outer chamfer: from (FLANK, 42.9) at 45 degrees to row 47

SHELL_Z0, SHELL_TOP, SHELL_CH = 0.2, 4.6, 0.85
PLATE_Z0, PLATE_TOP, PLATE_CH, PLATE_CHZ = 4.35, 5.3, 1.05, 0.42
DOME_H, POD_H = 1.8, 0.75  # crown heights (px) of the round upper shell and of each front pod
POD_C = (FLANK + PRONG_IN) / 2  # 13.725: the left pod's centre column
RAISE = 1.6  # the roof stands this much higher than the flat shell's top, over the dome's crown


def crown(c, r):
    """The carapace's crown above its flat top: an elliptic dome over the round upper shell (the
    sprite's light rim, dark inside) blending into a low barrel over each front pod."""
    dx = abs(c - AX)
    u, v = dx / 11.2, max(0.0, 11.0 - r) / 8.5
    hd = DOME_H * max(0.0, 1 - u * u - v * v)
    cm = c if c <= AX else 2 * AX - c
    dp = (cm - POD_C) / 4.6
    hp = POD_H * max(0.0, 1 - dp * dp)
    t = min(1.0, max(0.0, (r - 27.0) / 3.0))
    t = t * t * (3 - 2 * t)
    return hd * (1 - t) + hp * t


def shell_outline():
    half = [(AX, 3.0)]
    r = 3.0
    while r < 8.5 - 1e-9:
        half.append((AX - BACK_HW(r), r))
        r += 0.25
    half += [(FLANK_BACK, 8.5), (FLANK_BACK, 17.55), (FLANK, 17.75), (FLANK, CHAMF_R0),
             (FLANK + (TIP_R - CHAMF_R0), TIP_R), (PRONG_IN, TIP_R), (PRONG_IN, CROTCH + 0.4),
             (PRONG_IN + 0.4, CROTCH), (AX, CROTCH)]
    return mirror_half(half)


def vent(M, a, b, r_face, out, z0, z1, slats=4):
    """A framed louvred vent on a wall facing north (out -1) or south (out +1) at row r_face."""
    def rows(d0, d1):
        lo, hi = sorted((r_face + out * d0, r_face + out * d1))
        return lo, hi
    lo, hi = rows(-0.25, 0.2)
    M.prism([(a, lo), (b, lo), (b, hi), (a, hi)], z0, z1, 0.12, SHELL)
    a2, b2 = a + 0.3, b - 0.3
    lo, hi = rows(0.1, 0.28)
    M.prism([(a2, lo), (b2, lo), (b2, hi), (a2, hi)], z0 + 0.25, z1 - 0.25, 0.0, RECESS)
    lo, hi = rows(0.1, 0.36)
    step = (z1 - z0 - 0.7) / max(1, slats - 1)
    for k in range(slats):
        z = z0 + 0.45 + k * step
        M.prism([(a2, lo), (b2, lo), (b2, hi), (a2, hi)], z, z + 0.12, 0.0, SHELL)


def build_carapace(M):
    out = shell_outline()
    M.prism(out, SHELL_Z0, SHELL_TOP, SHELL_CH, SHELL, top=RECESS, belt=(1.3, 2.1, 0.11))
    deck = inset(out, SHELL_CH + 0.25)
    g = 0.25  # half a seam
    boxes = []
    # Centre band (back cap / band) between grooves at columns 17.5-18.0 and 23.0-23.5, the back cap
    # split at row 6.5, side plates at row 12.5; each plate's light frame is its lit bevel (FRAME).
    cl, cr = 18.0, 2 * AX - 18.0
    boxes += [(cl, cr, 0, 6.5 - g), (cl, cr, 6.5 + g, CROTCH + 1)]
    for side in (1, -1):
        def X(a, b):
            return (a, b) if side == 1 else (2 * AX - b, 2 * AX - a)
        boxes += [X(0, cl - 2 * g) + (0, 12.5 - g), X(0, cl - 2 * g) + (12.5 + g, CROTCH + 0.2)]
        # prongs: outer plate, inner strip (the sprite's groove column 14, light column 15) and the
        # long front plate below the cross groove at row 34
        boxes += [X(0, 14.5 - g) + (CROTCH + 0.7, 34.6 - g), X(14.5 + g, AX) + (CROTCH + 0.7, 34.6 - g),
                  X(0, AX) + (34.6 + g, 60)]
    for x0, x1, y0, y1 in boxes:
        poly = clip(deck, x0, x1, y0, y1)
        if len(poly) >= 3 and abs(area(poly)) > 0.5:
            M.prism(poly, PLATE_Z0, PLATE_TOP, PLATE_CH, PLATE, chz=PLATE_CHZ)
    # Rivet heads along the cross seams and the prong seams, and rim bolts down the dome's flanks.
    studs = []
    for c in (12.2, 14.2, 16.2):
        studs += [(c, 12.5), (c, 34.6)]
    for c in (19.3, 21.7):
        studs += [(c, 6.5)]
    for r in (30.6, 32.4, 33.9):
        studs += [(14.5, r)]
    for r in (8.6, 11.0, 14.6, 17.4):
        studs += [(12.6, r)]
    for c, r in studs:
        for cc in ((c,) if abs(c - AX) < 1e-6 else (c, 2 * AX - c)):
            hexs = [(cc + 0.32 * math.cos(math.radians(60 * k)), r + 0.32 * math.sin(math.radians(60 * k)))
                    for k in range(6)]
            M.prism(hexs, PLATE_Z0, PLATE_TOP + 0.25, 0.1, PLATE)
    # Prong noses: a framed louvred vent in each front face; a wide one in the back wall.
    for side in (1, -1):
        a, b = sorted((14.4, 17.2) if side == 1 else (2 * AX - 14.4, 2 * AX - 17.2))
        vent(M, a, b, TIP_R, 1, 1.0, 3.2)
    vent(M, 18.0, 23.0, 3.35, -1, 1.2, 3.5, slats=5)
    # Flank vents between the legs (visible from the side and the game camera's tilt).
    for side in (1, -1):
        def C(c):
            return c if side == 1 else 2 * AX - c
        for r0 in (22.0, 30.5, 37.0):
            a, b = sorted((C(FLANK - 0.05), C(FLANK + 0.3)))
            M.prism([(a, r0), (b, r0), (b, r0 + 3.2), (a, r0 + 3.2)], 2.3, 3.5, 0.0, RECESS)
            for k in range(4):
                a2, b2 = sorted((C(FLANK - 0.1), C(FLANK + 0.3)))
                rr = r0 + 0.35 + k * 0.78
                M.prism([(a2, rr), (b2, rr), (b2, rr + 0.25), (a2, rr + 0.25)], 2.3, 3.5, 0.0, SHELL)


def crown_carapace(M):
    """Bend the carapace's top (deck, plates, rivets) over crown(): cut it on a 1 x 1.5 px grid so the
    plates curve, then lift every vertex by the crown, weighted in from the top chamfer's foot."""
    bm = M.bm
    z_lo = (SHELL_TOP - SHELL_CH) * PX
    top = [f for f in bm.faces if f.calc_center_median().z > z_lo + 0.2 * PX]
    geom = list({e for f in top for e in f.edges}) + top + list({v for f in top for v in f.verts})
    for k in range(int(W)):
        c = 8.75 + 1.5 * k
        if c > 2 * AX - 8.5:
            break
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=P(c, 0, 0), plane_no=(1, 0, 0))
        geom = list({g for g in geom if g.is_valid} | set(res["geom"]))
    r = 3.75
    while r < TIP_R:
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=P(0, r, 0), plane_no=(0, 1, 0))
        geom = list({g for g in geom if g.is_valid} | set(res["geom"]))
        r += 2.0
    # The light frame: each plate's wide, shallow bevels facing the light (west / north, and the
    # pods' outer diagonal ends, which the sprite draws light on both sides) in pal 6, the rest pal
    # 4; classified on the flat plates, before the crown bends them.
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    for f in bm.faces:
        if f.material_index != PLATE:
            continue
        n = f.normal
        if 0.3 < n.z < 0.99 and (n.x < -0.2 or n.y > 0.2 or (n.y < -0.2 and abs(n.x) > 0.2)):
            f.material_index = FRAME
    for v in bm.verts:
        w = min(1.0, max(0.0, (v.co.z - z_lo) / (SHELL_CH * PX)))
        if w > 0:
            c, rr = v.co.x / PX + W / 2, H / 2 - v.co.y / PX
            v.co.z += w * crown(c, rr) * PX
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    for f in bm.faces:
        if f.material_index in (PLATE, RECESS) and f.normal.z > 0.96 and f.calc_center_median().z > z_lo:
            f.smooth = True  # the crowned tops shade as one curve, the bevels stay crisp


def solid(points, planes=(), offset=0.0):
    """A closed convex solid in its own bmesh: the hull of `points` (c, r, z px), each face plane
    moved in by `offset` px horizontally (an inward offset of the sloped faces), then cut by
    `planes` [(point (c, r, z), normal, keep_below)], each cut filled. Returns the bmesh."""
    bm = bmesh.new()
    vs = [bm.verts.new(P(*p)) for p in points]
    res = bmesh.ops.convex_hull(bm, input=vs)
    junk = [g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)]
    if junk:
        bmesh.ops.delete(bm, geom=list(set(junk)), context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts[:], edges=bm.edges[:])
    bm.normal_update()
    cuts = []
    if offset:
        for f in bm.faces:
            n = f.normal.copy()
            nh = math.hypot(n.x, n.y)
            if nh > 1e-3:
                cuts.append((f.calc_center_median() - n * (offset * PX * nh), n.copy()))
    for co, no, below in planes:
        q = P(*co)
        n = Vector(no).normalized()
        cuts.append((q, n if below else -n))
    for co, no in cuts:
        r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        edges = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def add_bm(M, bm, mat):
    for f in bm.faces:
        f.material_index = mat
        f.smooth = False
    tmp = bpy.data.meshes.new("_part")
    bm.to_mesh(tmp)
    bm.free()
    M.bm.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)


# The stepped pyramid: a level, four-faced kite pyramid on the sprite's delta (a back point at row
# 12.9, 45-degree hips to the wing corners at row 26.6 and a shallow front point at row 27.9), its
# apex over the plan's middle (row 20.5, where the sprite's upper tier meets its lower one), so from
# the side it reads as a level stepped pyramid. One ridge runs on the axis from the back point over
# the apex to the front point: every face left of it is lit (back faces pal 24, front faces pal 22),
# every face right of it shaded (pal 20 back, pal 19 front), the sprite's light / dark halves. It is
# cut level into three tiers, each set in by a ledge on a short riser (the tier seams); every tier
# has chamfered edges and a recessed panel inset in each sloped face; a machined cap plate on the
# apex, hex bolts round the slab's rim.
ROOF_B, ROOF_WR, ROOF_FR = 12.9, 26.6, 27.9  # back point row, wing-corner row, front point row
ROOF_WC = AX - (ROOF_WR - ROOF_B)  # 6.8: left wing corner column
ROOF_APEX_R, ROOF_H = 20.5, 7.4  # apex row and height over the slab
ROOF_CUTS = (2.5, 4.8, 6.6)  # tier cuts over the slab (the last one truncates the apex for the cap)
ROOF_LEDGE, ROOF_RISER = 0.5, 0.3
SLAB_EDGE0, SLAB_EDGE1, SLAB_TOP = 7.25, 7.95, 8.2  # the slab's outer edge (bottom, top) and its top


def roof_points(zs):
    return [(AX, ROOF_B, zs), (ROOF_WC, ROOF_WR, zs), (2 * AX - ROOF_WC, ROOF_WR, zs), (AX, ROOF_FR, zs),
            (AX, ROOF_APEX_R, zs + ROOF_H)]


def plan_of(v):
    return v.co.x / PX + W / 2, H / 2 - v.co.y / PX


def roof_colour(f, flat_split=True):
    """Light left of the ridge, shaded right of it, by the face's facing (a face on the ridge itself,
    the ridge chamfer, is lit: the sprite's bright ridge line)."""
    n = f.normal
    c = sum(plan_of(v)[0] for v in f.verts) / len(f.verts)
    if n.z > 0.9:
        left = c < AX - 1e-4
        return PYR_TOP if left else PYR_DK
    left = n.x < 0.03 if abs(n.x) > 0.03 else c < AX + 1e-4
    if n.y > 0.02:  # faces the back (Blender +y)
        return PYR_LT if left else PYR_DK
    return PYR_TOP if left else PYR_DK2


def detail_tier(bm, panel=True):
    """Chamfer a tier's edges and sink a panel into each big sloped face."""
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.11 * PX, segments=1, affect="EDGES", clamp_overlap=True)
    bm.normal_update()
    if panel:
        big = [f for f in bm.faces if 0.15 < f.normal.z < 0.95 and f.calc_area() > (2.2 * PX) ** 2]
        if big:
            bmesh.ops.inset_individual(bm, faces=big, thickness=0.42 * PX, depth=-0.09 * PX, use_even_offset=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()


def merge_bm(M, bm, colour):
    bm.normal_update()
    for f in bm.faces:
        f.material_index = colour(f)
        f.smooth = False
    tmp = bpy.data.meshes.new("_part")
    bm.to_mesh(tmp)
    bm.free()
    M.bm.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)


def build_roof(M):
    # Base slab with the wing blades (the sprite's delta: 45-degree edges from the point to the tips),
    # the wings' lower corners stepped and sharp as the sprite draws them. Its outer edge stands
    # above the carapace's crown all round (nothing hangs below the carapace's top line); a recessed
    # under-face sits on the crown over the shell, and level under the wings past the flanks.
    k0 = 11.8  # the point's row: edge c = AX - (r - k0)
    tip = (AX - (27.65 - k0), 27.65)
    half = [(AX, k0), tip, (tip[0] + 0.2, 28.95), (6.9, 29.95), (FLANK + 0.1, 30.0), (10.6, 28.2),
            (11.2, 27.35), (16.2, 27.35), (16.7, 27.9), (AX, 27.9)]
    base = mirror_half(half)
    if area(base) < 0:
        base = list(reversed(base))
    under = inset(base, 0.65)

    def seat(c, r):
        if FLANK_BACK + 0.6 < c < 2 * AX - FLANK_BACK - 0.6:
            return crown(c, r)
        return SLAB_EDGE0 - 0.45 - 4.2

    S = Mesh()
    rings = [S.ring(under, 4.2, seat), S.ring(under, 4.55, seat), S.ring(base, SLAB_EDGE0),
             S.ring(base, SLAB_EDGE1), S.ring(inset(base, 0.3), SLAB_TOP)]
    S.bands(rings, [PYR] * 4, cap0=PYR, cap1=PYR)
    # hex bolts round the slab's rim, between the pyramid's foot and the slab's edge
    bolts = [(AX - 0.62 * (ROOF_WR - ROOF_B) * t - 0.55, ROOF_B + (ROOF_WR - ROOF_B) * t - 0.25) for t in (0.45, 0.65, 0.85)]
    bolts += [(8.4, 28.6), (12.4, 28.4)]
    for c, r in bolts:
        for cc in (c, 2 * AX - c):
            hexs = [(cc + 0.3 * math.cos(math.radians(60 * k)), r + 0.3 * math.sin(math.radians(60 * k)))
                    for k in range(6)]
            S.prism(hexs, SLAB_TOP - 0.1, SLAB_TOP + 0.28, 0.09, PYR)
    bm = S.bm
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=P(AX, 0, 0), plane_no=(1, 0, 0))
    bm.normal_update()

    def slab_colour(f):
        c = sum(plan_of(v)[0] for v in f.verts) / len(f.verts)
        return PYR_TOP if c < AX else PYR_DK
    merge_bm(M, bm, slab_colour)

    # the pyramid's tiers
    zs = SLAB_TOP
    pts = roof_points(zs)
    cuts = [zs] + [zs + z for z in ROOF_CUTS]
    for k in range(len(cuts) - 1):
        planes = [((AX, 0, cuts[k + 1]), (0, 0, 1), True)]
        if k:
            planes.append(((AX, 0, cuts[k]), (0, 0, 1), False))
        t = solid(pts, planes, offset=ROOF_LEDGE * k)
        foot = []
        if k:
            bot = [f for f in t.faces if f.normal.z < -0.99]
            if bot:
                foot = [plan_of(v) for v in bot[0].verts]
        bmesh.ops.translate(t, vec=(0, 0, ROOF_RISER * k * PX), verts=t.verts)
        detail_tier(t, panel=k < 2)
        merge_bm(M, t, roof_colour)
        if len(foot) >= 3:
            R = Mesh()
            R.prism(foot, cuts[k] + ROOF_RISER * (k - 1) - 0.05, cuts[k] + ROOF_RISER * k, 0.0, PYR)
            R.bm.normal_update()
            bmesh.ops.recalc_face_normals(R.bm, faces=R.bm.faces)
            merge_bm(M, R.bm, roof_colour)
    # machined cap plate on the truncated apex: a low octagon with a centre boss
    ztop = cuts[-1] + ROOF_RISER * (len(cuts) - 2)
    C = Mesh()
    oct8 = [(AX + 0.95 * math.cos(math.radians(22.5 + 45 * k)), ROOF_APEX_R + 0.95 * math.sin(math.radians(22.5 + 45 * k)))
            for k in range(8)]
    C.prism(oct8, ztop - 0.1, ztop + 0.35, 0.12, PYR)
    oct4 = [(AX + 0.45 * math.cos(math.radians(22.5 + 45 * k)), ROOF_APEX_R + 0.45 * math.sin(math.radians(22.5 + 45 * k)))
            for k in range(8)]
    C.prism(oct4, ztop + 0.3, ztop + 0.65, 0.1, PYR)
    C.bm.normal_update()
    merge_bm(M, C.bm, roof_colour)

    # Keel block under the slab's front and the ram spike.
    keel = mirror_half([(AX, 26.0), (16.6, 26.0), (16.6, 28.9), (17.5, 29.75), (AX, 29.75)])
    M.prism(keel, 1.2, SLAB_EDGE1, 0.45, PYR)
    # The ram: a straight, near-constant-width (about 2.2 px) hexagonal bar from inside the keel to
    # the sprite's spike tip at row 35, ending in a short chisel; a clamp collar at the keel. It dips
    # (about 15 degrees) so the tilted game camera sees its full length, not a foreshortened stub.
    stations = [(28.0, 1.12, 4.7), (34.45, 1.06, 2.95), (35.0, 0.78, 2.78), (35.3, 0.4, 2.68)]
    rings = []
    for r, w, zc_ in stations:
        hh = 0.55 * w + 0.15
        pts6 = [(AX + w, zc_), (AX + 0.55 * w, zc_ + hh), (AX - 0.55 * w, zc_ + hh), (AX - w, zc_),
                (AX - 0.55 * w, zc_ - hh), (AX + 0.55 * w, zc_ - hh)]
        rings.append([M.bm.verts.new(P(c, r, z)) for c, z in pts6])
    M.bands(rings, [SPIKE] * (len(rings) - 1), cap0=SPIKE, cap1=SPIKE)
    M.tube([(AX, 29.7, 4.27), (AX, 30.4, 4.08)], 1.28, COLLAR, sides=6, smooth=False)


def build_legs(M):
    """Hydraulic struts on the sprite's 45-degree lines, from a clevis bracket bolted high on the
    carapace's flank (at its shoulder) diagonally down to a flanged foot in the dirt: an octagonal
    cylinder to a clamp band, then a thinner rod; all hard edged."""
    legs = [((10.4, 8.65), (4.6, 14.5)), ((10.4, 13.75), (4.6, 19.6))]
    for side in (1, -1):
        def C(c):
            return c if side == 1 else 2 * AX - c
        for i, (a, d) in enumerate(legs):
            if side == -1:  # the sprite draws the right legs a row lower, the back one a little shorter
                a, d = [(q[0], q[1] + 0.85) for q in (a, d)]
                if i == 0:
                    d = (d[0] + 0.8, d[1] - 0.75)
            A3 = Vector((C(a[0]), a[1], 4.7))
            D3 = Vector((C(d[0]), d[1], 0.55))

            def at(t):
                q = A3.lerp(D3, t)
                return (q.x, q.y, q.z)
            # clevis bracket: a chamfered block on the flank wall from the belt up to the shoulder
            bc, br = C(10.1), a[1] + 0.45
            sq = [(bc - 0.6, br - 0.75), (bc + 0.6, br - 0.75), (bc + 0.6, br + 0.75), (bc - 0.6, br + 0.75)]
            M.prism(sq, 2.0, 5.0, 0.25, COLLAR)
            M.tube([(C(9.3), br, 4.35), (C(10.7), br, 4.35)], 0.4, PIPE, sides=6, smooth=False)  # pivot pin
            M.tube([at(0.04), at(0.08), at(0.52), at(0.56), at(0.6)], [0.8, 0.95, 0.88, 0.88, 0.7], PIPE, sides=8,
                   smooth=False)
            M.tube([at(0.5), at(0.57)], 1.06, PIPE, sides=8, smooth=False)  # clamp band
            M.tube([at(0.57), at(0.97)], [0.56, 0.52], PIPE, sides=8, smooth=False)  # rod
            fc, fr = C(d[0]), d[1]
            foot = [(fc + 0.85 * math.cos(math.radians(45 + 90 * k)), fr + 0.85 * math.sin(math.radians(45 + 90 * k)))
                    for k in range(4)]
            M.prism(foot, 0.2, 0.8, 0.22, COLLAR)


def build_dirt(M, sprite_idx, body_mask):
    """The tile's ground: a grid at the pixel corners, low relief from the sprite's dirt pattern,
    each triangle the palette index of the (smoothed) dirt it covers."""
    import numpy as np
    idx = sprite_idx.astype(float)
    dirt = (idx >= 16) & ~body_mask
    # inpaint non-dirt pixels with the mean of their dirt neighbours, repeatedly
    val = np.where(dirt, idx, np.nan)
    for _ in range(30):
        nan = np.isnan(val)
        if not nan.any():
            break
        pad = np.pad(val, 1, constant_values=np.nan)
        stack = np.stack([pad[1 + dy:1 + dy + H, 1 + dx:1 + dx + W] for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
        mean = np.nanmean(np.where(np.isnan(stack), np.nan, stack), axis=0)
        val = np.where(nan & ~np.isnan(mean), mean, val)
    val = np.nan_to_num(val, nan=18.0)

    def blur(a, s):
        k = np.exp(-0.5 * (np.arange(-3, 4) / s) ** 2)
        k /= k.sum()
        a = np.pad(a, 3, mode="wrap")
        a = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, a)
        a = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 1, a)
        return a[3:-3, 3:-3]
    field = blur(val, 0.65)  # per pixel centre
    shadow = np.zeros_like(field)
    if PAINT_SHADOW:
        shadow = blur(((sprite_idx == 1) & ~body_mask).astype(float), 0.6)
    # corner heights: average of the 4 touching pixel centres
    pad = np.pad(field, 1, mode="edge")
    corner = (pad[:-1, :-1] + pad[1:, :-1] + pad[:-1, 1:] + pad[1:, 1:]) / 4  # (H+1, W+1)
    base = 0.45
    relief = (corner - 18.0) * 0.16
    rr, cc = np.mgrid[0:H + 1, 0:W + 1]
    edge = np.minimum.reduce([rr, cc, H - rr, W - cc]).astype(float)
    fade = np.clip(edge / 2.0, 0, 1)
    zc = base + np.clip(relief, -0.25, 0.3) * fade
    verts = [[M.bm.verts.new(P(c, r, zc[r, c])) for c in range(W + 1)] for r in range(H + 1)]

    def cls(v, sh):
        if sh > 0.5:
            return SHADOW
        if v < 17.35:
            return D17
        if v < 18.45:
            return D18
        if v < 19.5:
            return D19
        return D20

    def sample(c, r):  # bilinear field at plan point (pixel-edge coords)
        x, y = c - 0.5, r - 0.5
        x0, y0 = int(math.floor(x)), int(math.floor(y))
        fx, fy = x - x0, y - y0
        def g(a, yy, xx):
            return a[min(max(yy, 0), H - 1), min(max(xx, 0), W - 1)]
        out = []
        for a in (field, shadow):
            out.append((g(a, y0, x0) * (1 - fx) + g(a, y0, x0 + 1) * fx) * (1 - fy)
                       + (g(a, y0 + 1, x0) * (1 - fx) + g(a, y0 + 1, x0 + 1) * fx) * fy)
        return out
    for r in range(H):
        for c in range(W):
            a, b, d, e = verts[r][c], verts[r][c + 1], verts[r + 1][c + 1], verts[r + 1][c]
            # split along the diagonal whose ends differ least in the field
            v_ad = abs(corner[r, c] - corner[r + 1, c + 1])
            v_be = abs(corner[r, c + 1] - corner[r + 1, c])
            tris = ([(a, b, d), (a, d, e)] if v_ad <= v_be else [(a, b, e), (b, d, e)])
            for t in tris:
                cen = sum((v.co for v in t), Vector()) / 3
                pc, pr = cen.x / PX + W / 2, H / 2 - cen.y / PX
                v, sh = sample(pc, pr)
                M.face(t, cls(v, sh))
    # sides and bottom
    ring = ([verts[0][c] for c in range(W + 1)] + [verts[r][W] for r in range(1, H + 1)]
            + [verts[H][c] for c in range(W - 1, -1, -1)] + [verts[r][0] for r in range(H - 1, 0, -1)])
    low = [M.bm.verts.new((v.co.x, v.co.y, 0.0)) for v in ring]
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        M.face((ring[i], ring[j], low[j], low[i]), D18)
    M.face(list(reversed(low)), D18)


def sprite_grid():
    """The four pieces' palette indices on the 48 x 56 assembly grid."""
    import numpy as np
    lay = {"newsh2-81": (0, 0), "newsh2-83": (24, 0), "newsh2-119": (0, 28), "newsh2-121": (24, 28)}
    A = np.full((H, W), -1, int)
    for n, (x, y) in lay.items():
        d = common.load_sprite(ROOT, n)
        A[y:y + 28, x:x + 24] = d["frames"][0]["pixels"]
    return A


# The structure's plan on the assembly grid: per-row spans of the left half (dark outline ring
# included), mirrored about pixel-edge column 20.5 (the right half the sprite hides in the pyramid's
# cast shadow, rows 28-34, is the left one's mirror).
SPANS = {3: [(15, 20)], 4: [(13, 20)], 5: [(12, 20)], 6: [(11, 20)]}
SPANS.update({r: [(10, 20)] for r in range(7, 18)})
SPANS.update({r: [(9, 20)] for r in range(18, 24)})
SPANS.update({24: [(8, 20)], 25: [(7, 20)], 26: [(6, 20)], 27: [(5, 20)], 28: [(5, 20)], 29: [(7, 20)]})
SPANS.update({r: [(9, 17)] for r in range(30, 44)})
SPANS.update({44: [(11, 17)], 45: [(12, 17)], 46: [(13, 17)]})


def masks(A):
    """(body, spike, legs) boolean masks of the sprite's structure (tan leg pixels on the legs'
    45-degree lines, as drawn on each side)."""
    import numpy as np
    body = np.zeros((H, W), bool)
    for r, sp in SPANS.items():
        for a, b in sp:
            body[r, a:b + 1] = True
            body[r, 40 - b:40 - a + 1] = True
    spike = np.zeros_like(body)
    spike[30:35, 19:22] = True
    legs = np.zeros_like(body)
    for (r0, r1), side, k in (((9, 14), -1, 18), ((14, 20), -1, 23), ((10, 14), 1, 21), ((15, 20), 1, 16)):
        for r in range(r0, r1 + 1):
            for c in range(W):
                d = (c + r - k) if side < 0 else (c - r - k)
                if abs(d) <= 1 and A[r, c] >= 20 and not body[r, c]:
                    legs[r, c] = True
    return body, spike, legs


def merged_sprite():
    data = common.load_sprite(ROOT, PIECES[0])
    for n in PIECES[1:]:
        data["colors"].update(common.load_sprite(ROOT, n)["colors"])
    return data


def build(coll):
    """The whole bunker as one object, the structure alone (for the outline shell) and the dirt
    ground (the bake's occluder only, not exported: D67)."""
    A = sprite_grid()
    body, spike, legs = masks(A)
    sprite = merged_sprite()
    mats = materials(sprite)
    objs = []
    for part in ("tile", "structure", "ground"):
        M = Mesh()
        if part == "ground":
            build_dirt(M, A, body | spike | legs)
        else:
            Mc = Mesh()
            build_carapace(Mc)
            crown_carapace(Mc)
            tmp = bpy.data.meshes.new("_carapace")
            Mc.bm.to_mesh(tmp)
            Mc.bm.free()
            M.bm.from_mesh(tmp)
            bpy.data.meshes.remove(tmp)
            build_roof(M)
            build_legs(M)
        bm = M.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        # n-gon caps (concave: the carapace's prongs, the roof's wings) as triangles before the tile
        # is cut into its pieces, so bisecting them can't make crossing faces
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY",
                              ngon_method="EAR_CLIP")
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(NAME if part == "tile" else f"{NAME}_{part}")
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(me.name, me)
        coll.objects.link(obj)
        me.set_sharp_from_angle(angle=math.radians(32))
        objs.append(obj)
    return objs[0], objs[1], objs[2], sprite


def bake(obj, out_dir):
    """The Talon's bake (usp_talon.bake_maps, D50/D53) with this model's tint and textured slots:
    a grey colour multiplier (occlusion at two scales and an edge lift) and a metallic-roughness
    map, wired in as Base Color = map x palette colour. No concept projection."""
    import usp_talon as T
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, str(out_dir), size=1024, samples=64)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "nsh2_119")


def cull(obj, grid=4, ndirs=40):
    """usp_talon.cull_hidden's test (a face stays if any of a grid of points on it sees out along
    any direction of its front hemisphere), but only for the ground and for faces looking down: the
    dirt under the bunker and buried bottoms go; the carapace's long deck triangles (seen only
    through the seams) always stay."""
    from mathutils.bvhtree import BVHTree
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    dead = []
    for f in bm.faces:
        if not (f.material_index in DIRT or f.normal.z < -0.7):
            continue
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c] + [c.lerp(v, t) for v in vs for t in (0.4, 0.8, 0.97)]
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = any(tree.ray_cast(p + n * 2e-4, d, 50.0)[0] is None for p in pts for d in cand)
        if not seen:
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()


def recess_caps(obj, d=0.6, back=0.3):
    """common.split_assembly fills each piece's cut with a cap flush with the surface; in the game's
    (and EEVEE's) shadow map those caps darken the neighbour's surface beside the cut in a straight
    band (the pyramid's right half read as a separate dark slab). Keep every piece closed (a
    destroyed neighbour shows a solid face), but rebuild each cap shrunk d px from the surface and
    set back px into the piece, so no cap reaches the skin."""
    hw, hh = 1.0, 14 / 12
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    caps = []
    for f in bm.faces:
        for axis, lim in ((0, hw), (1, hh)):
            if abs(f.normal[axis]) > 0.999 and all(abs(abs(v.co[axis]) - lim) < 1e-4 for v in f.verts):
                caps.append((f, axis, 1 if f.verts[0].co[axis] > 0 else -1))
                break
    made = []
    for f, axis, sgn in caps:
        o = 1 - axis  # the in-plane horizontal axis
        loop = [(v.co[o] / PX, v.co.z / PX) for v in f.verts]
        mat = f.material_index
        plane = f.verts[0].co[axis] - sgn * back * PX
        sh = inset(loop, d)
        ok = abs(area(sh)) > 0.25 * abs(area(loop)) and (area(sh) > 0) == (area(loop) > 0)
        if not ok:
            continue
        vs = []
        for u, z in sh:
            co = [0.0, 0.0, z * PX]
            co[o], co[axis] = u * PX, plane
            vs.append(bm.verts.new(co))
        try:
            nf = bm.faces.new(vs)
        except ValueError:
            continue
        nf.material_index = mat
        nf.normal_update()
        if nf.normal[axis] * sgn < 0:
            nf.normal_flip()
        made.append(nf)
    bmesh.ops.delete(bm, geom=[c[0] for c in caps], context="FACES_ONLY")
    if made:
        bmesh.ops.triangulate(bm, faces=[f for f in made if f.is_valid], ngon_method="EAR_CLIP")
    bm.to_mesh(obj.data)
    bm.free()
    return len(caps), len(made)


def split_open(obj, layout):
    """common.split_assembly's cut without capping the cuts (for the outline shells): a capped
    shell draws an ink line across the structure at every piece seam."""
    out = {}
    coll = obj.users_collection[0]
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + "_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        o = bpy.data.objects.new(name + "_outline", me)
        coll.objects.link(o)
        out[name] = o
    return out


def export_glb(objects, path, image_format="AUTO"):
    """common.export_glb's settings, selecting through the objects' own flags."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for o in bpy.data.objects:
        try:
            o.select_set(False)
        except RuntimeError:
            pass
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_cameras=False, export_lights=False, export_extras=True,
                              export_image_format=image_format, export_image_quality=85)
    return path


def main():
    import tempfile
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    obj, structure, ground, sprite = build(coll)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake(obj, tempfile.mkdtemp(prefix="nsh2_119_bake_"))
        fmt = "WEBP"
    # The dirt only darkened the bake where the legs and carapace meet the ground; the game's HD
    # ground shows round the bunker, and its real shadow falls there (D67).
    bpy.data.objects.remove(ground, do_unlink=True)
    # The outline shell (D51) of the structure alone, cut like the tile: each piece outlines its part.
    shell = common.outline_shell(structure, coll, voxel=0.013, faces=3000, smooth=4)
    structure.hide_render = True
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    shells = split_open(shell, layout)
    total = 0
    for name in PIECES:
        print(f"piece {name}: caps rebuilt {recess_caps(pieces[name])}")
        cull(pieces[name])
        shells[name].name = f"{name}_outline"
        shells[name]["tyrian_outline"] = True
        shells[name].data.shade_smooth()
        tris = sum(len(p.vertices) - 2 for p in pieces[name].data.polygons)
        total += tris
        print(f"piece {name}: {tris} triangles, outline {len(shells[name].data.polygons)} faces")
    print(f"total {total} triangles")
    if "--out" in argv:  # a review copy of the whole tile, not the game export
        export_glb([pieces[n] for n in PIECES] + [shells[n] for n in PIECES], argv[argv.index("--out") + 1],
                   image_format=fmt)
    else:
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"],
                                       image_format=fmt)
    shell.hide_render = True
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
        obj.hide_render = False
        common.render_preview([obj], str(out), None, size=(W, H), view_px=480)
    if "--review" in argv:  # tools for the design review (outside the repo): flat-ID and beauty renders
        import importlib.util
        rv_path = Path(argv[argv.index("--review") + 1])
        spec = importlib.util.spec_from_file_location("review", argv[argv.index("--review-lib") + 1])
        rv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rv)
        for name, cx, cy in layout:
            pieces[name].location = (cx / 12, -cy / 12, 0)
        obj.hide_render = True
        rv.review([pieces[n] for n in PIECES], rv_path, PAL_OF)


if __name__ == "__main__":
    main()
