"""newshs-9 + newshs-93 (design A): the two newshs.shp grey fighters that shared lib_b040, rebuilt
hard-surface to the D65 standard. One script, three models (as before): newshs-9 (frames 9/10/28/29),
newshs-93 (frame 93, hatch shut) and newshs-93-f2 (frame 131, red eye open).

Reading of newshs-9 (12 x 14, symmetric about column edge 5.5; tools/calibration/rubric.md):
- Column 5 is a round fuselage (cols 4-6, 3 px): the bright 13/14 stripe down its middle with
  darker 10/9/8 flanks is a cylinder's sheen, not a ridge. It runs from the nose (row 1, the 15
  glint) to the nozzle (row 11).
- Rows 1-3: the hammerhead, two blunt tip pods (cols 2-3 / 7-8, lit 12/14 inner edge) on a low
  cross wing (the dark 5/8/7 beside the nose is the wing, sunk between pods and fuselage); the
  pods' tails curve in over row 3 (inner mask cols 3-7) and the neck (row 4) is the bare fuselage.
- Rows 5-9: two rounded side nacelles (cols 2-3 / 7-8, 14/13 tops), blunt front on row 5, widest
  6-8, tails curling in on row 9; the dark cols 4 / 6 are the crevices between them and the body.
- Row 10: a glowing band round the fuselage (120 centre, 116 sides on frame 9; the frames step it
  up to 122/118, 124/121, 126/123); row 9's collar and row 11's nozzle brighten with it (10 -> 11
  -> 12): palette_material frames=, one model for all four frames (D17).

Reading of newshs-93 (24 x 28, symmetric about column edge 12, nose down the screen):
- Rows 2-13: a wide shield-shaped back plate, cols 3-20. Cols 3-4 / 19-20: rounded side rails
  (the left lit 8 edge and the right 2-3 are light and shade of the same rail). Col 5 / 18: deep
  slots (2). Rows 2-3, cols 3-5 / 18-20: red lamps (113 housings, 115 lenses) capping the rails,
  their housings standing a pixel past the back edge (row 1 ink).
- Row 3, cols 6-17: a bright lip (11 -> 5 across: lighting) along the back edge of a raised
  trapezoid deck panel (5) that narrows (rows 7-9) into the armoured head; two sloped ribs (cols
  10 / 13, rows 5-7, 7 -> 10) run down it into the head.
- Cols 9-14, rows 8-13: the head, an armour block (lit 10/11 front lip on row 8) with a hatch on
  top (cols 10-13, rows 9-11): black (1) when shut on frame 93; on 131 a red eye (115 rim, 117
  core, 121/122 hot centre) and the eye's light warms what is under it (rows 12-17 one or two
  steps brighter: the struts, the apron under the head and the pod's back).
- Rows 8-13 beside the head (cols 5-8 / 15-18, 2-3): a recessed lower deck, in shade.
- Cols 7 / 16, rows 12-17: two thin struts from the back plate over the waist to the lower hull.
- Row 14: the waist (outline steps in a pixel); row 15: the lower hull's flange (back to cols
  3-20) with ridges along its top edge (6); rows 16-26: the lower hull tapers to the nose in a V.
- Cols 9-14, rows 15-26: a central pod (top lit 9/10 on rows 16-18), dark channels (cols 8 / 15)
  either side of it, with a long blue canopy (145-150, glint on the right) on rows 19-24 that
  narrows to a point on row 24; the pod's nose (rows 25-26, 2-3) is in shade.

Colours: the region's trimmed median palette index (darkest / brightest sixth left out).
Hard surface (D50-D53, D65): superellipse lofts with pchip plan stations fitted to the inner mask
(D74), V-cut panel lines, recessed bores and ports, chamfered blocks (usp_talon.hull/cbox);
satin metal; no projection bake; outline shell (D51) from a closed proxy. Undersides: closed, plain.

Units while building: sprite px (x = column edge - W/2, y = row edge down the screen, z up),
moved to Blender by finish() (1/12, y flipped about the block's centre row).

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshs-9.py (also writes newshs-93 and newshs-93-f2;
the old newshs-93.py is retired). Review renders: ... -- --render DIR
"""

import copy
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import common  # noqa: E402
WT = common.repo_root(__file__)
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
PX = 1 / 12


# --- geometry helpers (copied here; candidates for a shared lib) ----------------------------------
def finish(part, mats, coll, H, ox=0.0, smooth_angle=None):
    """usp_talon.finish for any block height: X = (x + ox) / 12, Y = (H / 2 - y) / 12, Z = z / 12."""
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, ox * PX), (0, -PX, 0, H / 2 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle or part.smooth_angle))
    return obj


def spow(v, e):
    return math.copysign(abs(v) ** e, v)


def ring_pts(cx, y, w, zc, ht, hb, n, p):
    """A superellipse section (exponent p: 2 = ellipse, higher = squarer, a chamfered round-rect)."""
    out = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        c, s = math.cos(a), math.sin(a)
        out.append((cx + w * spow(c, 2 / p), y, zc + (ht if s > 0 else hb) * spow(s, 2 / p)))
    return out


def tube(P, st, n=16, p=2.6, cap0=True, cap1=True):
    """A loft through stations (y, cx, w, zc, ht, hb, mat[, how]); mat is a material slot or a
    function of the section angle (radians, 0 = +x, pi/2 = up); `how` orients the segment that
    starts at this station: None (away from the axis), "in" (a bore, facing the axis), "-y"/"+y"
    (a flat step). A station with w ~ 0 is a single tip vertex."""
    rings = []
    for s in st:
        y, cx, w, zc, ht, hb = s[:6]
        if w < 1e-3:
            rings.append([P.v((cx, y, zc))])
        else:
            rings.append([P.v(q) for q in ring_pts(cx, y, w, zc, ht, hb, n, p)])
    for i in range(len(st) - 1):
        a, b = rings[i], rings[i + 1]
        mat = st[i][6]
        how = st[i][7] if len(st[i]) > 7 else None
        cx = (st[i][1] + st[i + 1][1]) / 2
        zc = (st[i][3] + st[i + 1][3]) / 2
        for k in range(n):
            j = (k + 1) % n
            q = [a[k % len(a)], a[j % len(a)], b[j % len(b)], b[k % len(b)]]
            # a w ~ 0 station is one pole vertex: drop the repeat so the segment closes as a
            # triangle fan (a quad with a repeated vertex is refused and left the end open)
            q = [v for i, v in enumerate(q) if v is not q[i - 1]]
            ang = 2 * math.pi * (k + 1) / n
            m = mat(ang) if callable(mat) else mat
            c = sum((Vector(v.co) for v in q), Vector()) / len(q)
            if how == "in":
                P.f(q, m, out=(cx - c.x, 0, zc - c.z))
            elif how == "-y":
                P.f(q, m, out=(0, -1, 0))
            elif how == "+y":
                P.f(q, m, out=(0, 1, 0))
            else:
                P.f(q, m, out=(c.x - cx, 0, c.z - zc))
    for r, s, cap, d in ((rings[0], st[0], cap0, -1), (rings[-1], st[-1], cap1, 1)):
        if cap and len(r) > 2:
            m = s[6] if not callable(s[6]) else s[6](math.pi / 2)
            c = P.v((s[1], s[0], s[3]))
            for k in range(len(r)):
                P.f([r[k], r[(k + 1) % len(r)], c], m, out=(0, d, 0))


def prism(P, poly, z0, z1, mat, ch=0.15, top_mat=None, side_mat=None):
    """A vertical prism over a convex-or-not plan polygon [(x, y)], top edge chamfered by ch
    (inset ch, down ch), flat bottom."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    inset = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x)) * sgn
        n1 = Vector((-e1.y, e1.x)) * sgn
        bis = n0 + n1
        bis = bis.normalized() / max(0.35, bis.normalized().dot(n0)) if bis.length > 1e-6 else n0
        inset.append(p1 + bis * ch)  # inward (n points inward for this orientation)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    bot = [P.v((x, y, z0)) for x, y in poly]
    mid = [P.v((x, y, z1 - ch)) for x, y in poly]
    top = [P.v((v.x, v.y, z1)) for v in inset]
    sm = side_mat if side_mat is not None else mat
    tm = top_mat if top_mat is not None else mat
    for i in range(n):
        j = (i + 1) % n
        ex, ey = poly[j][0] - poly[i][0], poly[j][1] - poly[i][1]
        c = ((poly[i][0] + poly[j][0]) / 2, (poly[i][1] + poly[j][1]) / 2)
        P.f([bot[i], bot[j], mid[j], mid[i]], sm, away=(cx, cy, (z0 + z1) / 2))
        P.f([mid[i], mid[j], top[j], top[i]], tm, out=(c[0] - cx, c[1] - cy, 1.0))
    P.f(top, tm, out=(0, 0, 1))
    P.f(bot, sm, out=(0, 0, -1))


def box(P, x0, x1, y0, y1, z0, z1, ch, mat, chz=None):
    T.hull(P, T.cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


class Mats:
    def __init__(self, sprite, tag):
        self.sprite, self.tag = sprite, tag
        self.list, self.slots = [], {}

    def __call__(self, index, part, frames=None, metallic=0.45, roughness=0.38, emission=0.0):
        key = (index, part)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, f"{self.tag}_{part}", metallic=metallic,
                                                     roughness=roughness, emission_strength=emission,
                                                     frames=frames))
        return self.slots[key]


def proxy_shell(name, parts_pts, coll, H, ox, faces):
    """Outline shell (D51) from a closed proxy: the convex hulls of point clouds, one per part."""
    P = T.Part(f"{name}_proxy", smooth_angle=180)
    for pts in parts_pts:
        T.hull(P, pts, 0)
    proxy = finish(P, [], coll, H, ox)
    shell = common.outline_shell(proxy, coll, voxel=0.008, faces=faces)
    shell.name = f"{name}_outline"
    bpy.data.objects.remove(proxy, do_unlink=True)
    bpy.context.view_layer.update()
    return shell


def tube_cloud(st, n=12, p=2.6, grow=0.0):
    pts = []
    for s in st:
        y, cx, w, zc, ht, hb = s[:6]
        if w < 1e-3:
            pts.append((cx, y, zc))
        else:
            pts += ring_pts(cx, y, w + grow, zc, ht + grow, hb + grow, n, p)
    return pts


# =================================================================================================
# newshs-9: the small grey drone
# =================================================================================================
D_AX = -0.5   # its symmetry axis (column edge 5.5) in x = column edge - 6

# Fuselage half width (px) by row edge; cols 4-6 from the nose (row 1) to the nozzle (row 11).
_FY = [0.95, 1.1, 1.6, 2.2, 2.8, 3.3, 3.7, 4.8, 5.6, 8.6, 9.3, 9.6]
_FW = [0.0, 0.38, 0.55, 0.72, 1.0, 1.36, 1.48, 1.48, 1.08, 1.08, 1.45, 1.48]
fus_w = T.pchip(_FY, _FW)
_FH = [0.0, 0.4, 0.62, 0.8, 1.02, 1.24, 1.3, 1.3, 1.3, 1.3, 1.3, 1.3]
fus_h = T.pchip(_FY, _FH)

# Tip pods of the hammerhead (cols 2-3 / 7-8, rows 1-3), centre and half width by row edge.
_TY = [1.0, 1.35, 2.7, 3.25, 3.7, 4.02]
_TC = [2.5, 2.5, 2.5, 2.25, 1.95, 1.75]
_TW = [0.92, 1.0, 1.0, 0.72, 0.42, 0.0]
tip_c, tip_w = T.pchip(_TY, _TC), T.pchip(_TY, _TW)

# Side nacelles (cols 2-3 / 7-8, rows 5-9).
_NY = [4.85, 5.2, 5.65, 6.15, 7.9, 8.6, 9.2, 9.65, 9.95]
_NC = [2.05, 2.2, 2.35, 2.45, 2.45, 2.35, 2.12, 1.9, 1.75]
_NW = [0.0, 0.42, 0.72, 1.06, 1.1, 1.02, 0.8, 0.45, 0.0]
nac_c, nac_w = T.pchip(_NY, _NC), T.pchip(_NY, _NW)


def drone_stations(M):
    """Fuselage: nose cap, body with V-cut panel lines, collar, glow band, rear collar, nozzle."""
    st = []
    body = M["body"]
    nose = M["nose"]
    ys = [0.95, 1.05, 1.15, 1.3, 1.6, 2.0, 2.4, 2.8, 3.1, 3.4, 3.7]
    for y in ys:
        h = fus_h(y)
        st.append((y, 0.0, fus_w(y), 0.1 + (1.3 - h) * 0.35, h, h * 0.85, nose if y < 1.5 else body))
    # V-cut panel line behind the hammerhead (row 4's front edge) and one behind the nacelles' noses
    for y in (3.87, 3.95, 4.03, 4.5, 4.9, 5.12, 5.2, 5.28, 5.6, 6.2, 7.4, 8.3, 8.6, 8.95, 9.25):
        k = 0.9 if y in (3.95, 5.2) else 1.0
        w, h = fus_w(y), fus_h(y)
        st.append((y, 0.0, w * k, 0.1, h * k, h * 0.85 * k, M["seam"] if y in (3.87, 5.12) else body))
    # collar (row 9's back end), lights with the band
    st += [(9.35, 0.0, 1.42, 0.1, 1.24, 1.05, M["seam"]), (9.42, 0.0, 1.52, 0.1, 1.34, 1.15, M["collar"]),
           (9.95, 0.0, 1.52, 0.1, 1.34, 1.15, M["collar"], "+y")]
    # glow band (row 10), recessed a hair between the collars; top 120-family, sides 116-family
    band = lambda a: M["glow"] if math.sin(a) > 0.55 else M["glow_side"]  # noqa: E731
    st += [(9.95, 0.0, 1.4, 0.1, 1.22, 1.04, band), (10.95, 0.0, 1.4, 0.1, 1.22, 1.04, band, "-y")]
    # rear collar and nozzle bell (row 11), its exit a recessed throat
    st += [(10.95, 0.0, 1.5, 0.1, 1.32, 1.12, M["nozzle"]), (11.15, 0.0, 1.5, 0.1, 1.32, 1.12, M["nozzle"]),
           (11.25, 0.0, 1.38, 0.1, 1.2, 1.0, M["nozzle"]), (11.95, 0.0, 1.22, 0.1, 1.02, 0.86, M["nozzle"], "+y"),
           (11.95, 0.0, 0.82, 0.1, 0.66, 0.56, M["throat"], "in"), (11.55, 0.0, 0.62, 0.1, 0.48, 0.4, M["throat"])]
    return st


def tip_stations(M, side):
    """A hammerhead tip pod: blunt front with a recessed muzzle, round body, tail curling inward."""
    sgn = 1 if side > 0 else -1
    st = []
    zc, ht, hb = 0.05, 0.95, 0.75
    c0 = sgn * tip_c(1.0)
    # muzzle: a recessed bore in the blunt front face
    st += [(1.45, c0, 0.34, zc + 0.1, 0.32, 0.3, M["bore"]), (1.0, c0, 0.38, zc + 0.1, 0.36, 0.33, M["bore"], "in"),
           (1.0, c0, 0.62, zc + 0.08, 0.58, 0.48, M["tip_front"], "-y")]
    for y in (1.0, 1.12):
        k = 0.88 if y == 1.0 else 1.0
        st.append((y, c0, tip_w(y) * k, zc, ht * k, hb * k, M["tip"]))
    for y in (1.6, 2.2, 2.75, 3.0, 3.25, 3.5, 3.7, 3.88, 4.02):
        w = tip_w(y)
        h = ht * min(1.0, 0.35 + w)
        st.append((y, sgn * tip_c(y), w, zc - (1 - min(1, w)) * 0.2, h, hb * min(1.0, 0.35 + w),
                   M["seam"] if abs(y - 2.75) < 1e-6 else M["tip"]))
    # a V panel line round the pod at row 2's back
    return st


def nacelle_stations(M, side):
    sgn = 1 if side > 0 else -1
    zc, ht, hb = -0.05, 1.05, 0.85
    st = []
    # intake: a dark recessed ring in the blunt front
    y0 = 5.05
    c0 = sgn * nac_c(y0)
    st += [(5.35, c0, 0.22, zc + 0.05, 0.2, 0.18, M["bore"]), (y0, c0, 0.28, zc + 0.05, 0.26, 0.22, M["bore"], "in"),
           (y0, c0, nac_w(y0) * 0.75, zc, ht * 0.4, hb * 0.4, M["pod_lip"], "-y")]
    for y in (5.05, 5.2, 5.45, 5.75, 6.15, 6.6):
        w = nac_w(y)
        f = min(1.0, 0.2 + w / 1.1)
        st.append((y, sgn * nac_c(y), w, zc, ht * f, hb * f, M["pod_lip"] if y < 5.3 else M["pod"]))
    for yc in (6.9,):
        for dy, k in ((-0.07, 1.0), (0.0, 0.9), (0.07, 1.0)):
            st.append((yc + dy, sgn * nac_c(yc), nac_w(yc) * k, zc, ht * k, hb * k, M["seam"] if dy < 0 else M["pod"]))
    for y in (7.4, 7.9, 8.35, 8.75, 9.1, 9.4, 9.65, 9.85, 9.95):
        w = nac_w(y)
        f = min(1.0, 0.3 + w / 1.1)
        st.append((y, sgn * nac_c(y), w, zc, ht * f, hb * f, M["pod"]))
    return st


def build_drone(coll):
    name = "newshs-9"
    sprite = common.load_sprite(WT, name)
    Mt = Mats(sprite, name)
    M = {
        "body": Mt(10, "body", metallic=0.5, roughness=0.34),
        "nose": Mt(11, "nose", metallic=0.55, roughness=0.28),
        "seam": Mt(8, "seam", metallic=0.4, roughness=0.5),
        "tip": Mt(11, "tip", metallic=0.5, roughness=0.34),
        "tip_front": Mt(10, "tip_front", metallic=0.5, roughness=0.36),
        "bore": Mt(5, "bore", metallic=0.3, roughness=0.6),
        "wing": Mt(8, "wing", metallic=0.45, roughness=0.42),
        "pod": Mt(11, "pod", metallic=0.5, roughness=0.32),
        "pod_lip": Mt(11, "pod_lip", metallic=0.5, roughness=0.36),
        "deck": Mt(9, "deck", metallic=0.45, roughness=0.42),
        # collar (row 9) and nozzle (row 11) brighten with the band: 10 -> 11 -> 12
        "collar": Mt(10, "collar", frames={10: 11, 28: 11, 29: 11}, metallic=0.5, roughness=0.34),
        "nozzle": Mt(10, "nozzle", frames={10: 11, 28: 12, 29: 12}, metallic=0.5, roughness=0.34),
        "throat": Mt(5, "throat", metallic=0.3, roughness=0.6),
        # the band: no emission (modelFrames.ts copies the full colour into any emissive, so a
        # strength <= 1 still glows at 1 and washes 120 out to salmon in the game's lit, tone-mapped
        # render); a satin metal tinted by its index keeps 120/122/124/126 red-orange to pale yellow
        "glow": Mt(120, "glow", frames={10: 122, 28: 124, 29: 126}, metallic=0.9, roughness=0.5, emission=0.0),
        "glow_side": Mt(116, "glow_side", frames={10: 118, 28: 121, 29: 123}, metallic=0.9, roughness=0.5,
                        emission=0.0),
    }
    P = T.Part(name, smooth_angle=40)
    fst = drone_stations(M)
    tube(P, fst, n=20, p=2.3)
    tips = [tip_stations(M, s) for s in (-1, 1)]
    nacs = [nacelle_stations(M, s) for s in (-1, 1)]
    for st in tips:
        tube(P, st, n=16, p=2.5)
    for st in nacs:
        tube(P, st, n=16, p=2.3)
    # Cross wing of the hammerhead (rows 1.4-3.5): a thin chamfered plate, its top below the pods'
    # and the fuselage's crowns (dark 5/8/7 beside the nose), leading edge swept a little.
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.6, s * 2.3))
        T.hull(P, [(x, y, z) for x in (x0, x1) for y, zs in ((1.3, (-0.15, 0.22)), (3.35, (-0.3, 0.42)))
                   for z in zs] + [(x, 1.12, 0.03) for x in (x0, x1)] + [(x, 3.5, 0.06) for x in (x0, x1)],
               M["wing"])
        # a small fence on top of the wing, between nose and pod
        T.hull(P, T.cbox(s * 1.35 - 0.12, s * 1.35 + 0.12, 2.0, 3.25, 0.3, 0.62, 0.05), M["seam"])
    # Pylon decks joining the nacelles to the body (rows 5.6-9.2), low, in the dark crevice
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.9, s * 2.3))
        T.hull(P, T.cbox(x0, x1, 5.7, 9.1, -0.55, 0.3, 0.2), M["deck"])
    obj = finish(P, Mt.list, coll, 14, D_AX)
    # outline shell from a closed proxy (D51)
    clouds = [tube_cloud(fst[:-2], grow=0.05)] + [tube_cloud(st[2:], grow=0.05) for st in tips + nacs]
    for s in (-1, 1):
        x0, x1 = sorted((s * 0.3, s * 2.4))
        clouds.append(T.cbox(x0, x1, 1.15, 3.45, -0.3, 0.45, 0.1))
        x0, x1 = sorted((s * 0.9, s * 2.3))
        clouds.append(T.cbox(x0, x1, 5.7, 9.1, -0.5, 0.3, 0.1))
    shell = proxy_shell(name, clouds, coll, 14, D_AX, faces=1800)
    return sprite, [obj, shell]


# =================================================================================================
# newshs-93: the grey shield gunship
# =================================================================================================
G_BASE0, G_BASE1 = -1.3, 0.6      # back plate slab (z)
RAIL_TOP = 2.3
PANEL_TOP = 1.55
HEAD_TOP = 3.1


def g_half(y):
    """The inner mask's half width (px) by row edge, the plan the lower hull follows (rows 15-27)."""
    ys = [15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 24.0, 26.0, 27.0]
    ws = [9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 3.0, 2.0, 1.0]
    return T.pchip(ys, ws)(y)


def gunship_rails(P, M, s):
    """A side rail (cols 3-4 / 19-20, rows 2-13): a round-topped bar on the plate's edge, the lamp
    housing capping its back end, V panel lines and a vent strip on its outer face."""
    xc = s * 8.0
    st = []
    zc, ht, hb = 0.55, RAIL_TOP - 0.55, 1.75
    w = 1.02
    st.append((2.05, xc, w * 0.9, zc, ht * 0.9, hb * 0.95, M["rail"]))
    for y in (2.2, 4.4):
        st.append((y, xc, w, zc, ht, hb, M["rail"]))
    for yc in (4.6, 9.0, 12.2):
        for dy, k in ((-0.08, 1.0), (0.0, 0.9), (0.08, 1.0)):
            st.append((yc + dy, xc, w * k, zc, ht * (0.97 if k < 1 else 1.0), hb, M["groove"] if dy < 0 else M["rail"]))
    for y in (13.0, 13.55):
        st.append((y, xc, w, zc, ht, hb, M["rail"]))
    st.append((13.85, xc, w * 0.85, zc - 0.1, ht * 0.85, hb * 0.9, M["rail"]))
    tube(P, st, n=16, p=3.0)
    # lamp housing on the rail's back end (rows 2-3, a pixel past the plate's back edge) and the lens
    hx = s * 7.6
    x0, x1 = sorted((s * 6.8, s * 9.05))
    box(P, x0, x1, 2.0, 3.6, zc - 0.6, RAIL_TOP + 0.25, 0.3, M["lamp_house"])
    # lens: a glowing dome set into the housing's top, toward the inner corner (col 4 / 19)
    lens = []
    for k in range(10):
        a = 2 * math.pi * k / 10
        for zz, rr in ((RAIL_TOP + 0.2, 0.62), (RAIL_TOP + 0.45, 0.48), (RAIL_TOP + 0.58, 0.25)):
            lens.append((hx + rr * math.cos(a), 2.9 + rr * 0.85 * math.sin(a), zz))
    T.hull(P, lens, M["lamp"])
    # vent strip on the outer face of the rail (side view detail)
    for k in range(5):
        y = 6.0 + k * 1.0
        x0, x1 = sorted((s * 8.95, s * 9.05))
        box(P, x0 - (0.05 if s < 0 else 0), x1 + (0.05 if s > 0 else 0), y, y + 0.55, -0.35, 0.35, 0.04, M["groove"])


def gunship_plate(P, M):
    """The back plate (rows 3-13, cols 5-18 between the rails) and the lower deck beside the head."""
    # the main slab under everything, cols 3-20, rows 3-14 (rails sit on its edges)
    poly = [(-8.9, 3.0), (8.9, 3.0), (8.9, 13.9), (-8.9, 13.9)]
    prism(P, poly, G_BASE0, G_BASE1, M["deck"], ch=0.25)
    # slots between rails and the deck panel (col 5 / 18): the slab's top shows as a deep dark slot
    for s in (-1, 1):
        x0, x1 = sorted((s * 6.95, s * 6.05))
        box(P, x0, x1, 4.2, 12.4, G_BASE1 - 0.05, G_BASE1 + 0.02, 0.02, M["slot"])
    # rear face: two recessed exhaust ports and a seam band (the back edge, seen in the rear view)
    for s in (-1, 1):
        x0, x1 = sorted((s * 1.2, s * 4.6))
        box(P, x0, x1, 2.88, 3.05, -0.9, 0.3, 0.05, M["slot"])
        for k in range(3):
            xx = s * (1.8 + k * 1.1)
            box(P, xx - 0.18, xx + 0.18, 2.84, 3.0, -0.8, 0.2, 0.03, M["rail"])


def gunship_panel(P, M):
    """Raised trapezoid deck panel (cols 6-17, rows 3-9) narrowing into the head, its bright back
    lip, the two sloped ribs (cols 10 / 13) and the bolt line along its edges."""
    half = [(-6.0, 3.15), (-6.0, 7.1), (-3.4, 9.4), (-3.0, 9.4)]
    poly = half + [(-x, y) for x, y in reversed(half)]
    prism(P, poly, G_BASE1 - 0.1, PANEL_TOP, M["panel"], ch=0.22)
    # back lip: a round bar along the panel's back edge (row 3), on the slab's back edge
    lip_pts = []
    for x in (-6.0, 6.0):
        for k in range(10):
            a = math.pi * k / 9
            lip_pts.append((x, 3.55 - 0.55 * math.cos(a), PANEL_TOP - 0.05 + 0.5 * math.sin(a)))
        lip_pts += [(x, 3.0, G_BASE1 - 0.1), (x, 4.1, G_BASE1 - 0.1)]
    T.hull(P, lip_pts, M["lip"])
    # sloped ribs from row 5 into the head (rising toward it)
    for s in (-1, 1):
        x = s * 1.5
        T.hull(P, [(x + dx, y, z) for dx in (-0.38, 0.38) for y, z in ((4.6, PANEL_TOP), (8.2, PANEL_TOP))]
               + [(x + dx, y, z) for dx in (-0.22, 0.22) for y, z in ((4.8, PANEL_TOP + 0.3), (8.2, HEAD_TOP - 0.55))],
               M["rib"])
    # bolt heads along the panel's side edges (small, machined)
    for s in (-1, 1):
        for y in (4.3, 5.6, 6.9):
            x = s * 5.3
            box(P, x - 0.22, x + 0.22, y - 0.22, y + 0.22, PANEL_TOP - 0.05, PANEL_TOP + 0.12, 0.08, M["lip"])


def gunship_head(P, M, eye_open):
    """Armour head (cols 9-14, rows 8-13): chamfered block, bright front lip, hatch on top."""
    box(P, -3.0, 3.0, 7.85, 13.4, G_BASE1 - 0.2, HEAD_TOP, 0.42, M["head"], chz=0.32)
    # the lit lip along the head's back (row 8)
    box(P, -2.85, 2.85, 7.8, 8.75, HEAD_TOP - 0.55, HEAD_TOP + 0.12, 0.25, M["head_lip"])
    if not eye_open:
        # shut hatch: one dark panel sunk into the top; its split line is a hairline of near-black
        # (pal 2), so at game scale it stays one solid black 4x3 panel as in the sprite
        box(P, -2.05, 2.05, 8.95, 12.05, HEAD_TOP - 0.25, HEAD_TOP + 0.06, 0.12, M["hatch"])
        box(P, -0.025, 0.025, 9.1, 11.9, HEAD_TOP + 0.04, HEAD_TOP + 0.065, 0.005, M["slot"])
    else:
        # open hatch: the red eye fills the whole 4x3 opening (cols 10-13, rows 9-11). A rounded-
        # rectangle socket rim (115) reaches the opening's corners; the oval lens (117) bulges
        # from it, covering the edge pixels but not the corners; a hot core (121) on row 10 and a
        # duller lower crescent (118) on row 11.
        def sq(a, e=4.0):
            c, s_ = math.cos(a), math.sin(a)
            return (math.copysign(abs(c) ** (2 / e), c), math.copysign(abs(s_) ** (2 / e), s_))
        ring = []
        for k in range(32):
            cx_, cy_ = sq(2 * math.pi * k / 32)
            for zz, rr in ((HEAD_TOP - 0.2, 1.0), (HEAD_TOP + 0.18, 1.0), (HEAD_TOP + 0.26, 0.94)):
                ring.append((1.98 * rr * cx_, 10.5 + 1.48 * rr * cy_, zz))
        T.hull(P, ring, M["eye_rim"])
        eye = []
        for k in range(20):
            a = 2 * math.pi * k / 20
            for zz, rr in ((HEAD_TOP + 0.24, 1.0), (HEAD_TOP + 0.5, 0.86), (HEAD_TOP + 0.7, 0.58), (HEAD_TOP + 0.8, 0.2)):
                eye.append((1.9 * rr * math.cos(a), 10.5 + 1.42 * rr * math.sin(a), zz))
        T.hull(P, eye, M["eye"])
        hot = []
        for k in range(12):
            a = 2 * math.pi * k / 12
            for zz, rr in ((HEAD_TOP + 0.72, 1.0), (HEAD_TOP + 0.86, 0.5)):
                hot.append((0.95 * rr * math.cos(a), 10.45 + 0.42 * rr * math.sin(a), zz))
        T.hull(P, hot, M["eye_hot"])
        low = []
        for k in range(12):
            a = 2 * math.pi * k / 12
            for zz, rr in ((HEAD_TOP + 0.55, 1.0), (HEAD_TOP + 0.68, 0.6)):
                low.append((0.92 * rr * math.cos(a), 11.45 + 0.36 * rr * math.sin(a), zz))
        T.hull(P, low, M["eye_low"])
        # the eye's red spill on the head just in front of it (row 12, cols 11-12)
        box(P, -0.95, 0.95, 12.05, 12.95, HEAD_TOP - 0.05, HEAD_TOP + 0.03, 0.02, M["eye_spill"])
    # side armour cheeks on the head (vertical V seams) and a chin under its front edge (row 12-13)
    for s in (-1, 1):
        x0, x1 = sorted((s * 3.0, s * 3.12))
        box(P, x0, x1, 9.0, 12.4, 0.8, HEAD_TOP - 0.6, 0.03, M["slot"])
    box(P, -2.4, 2.4, 12.6, 13.75, G_BASE1 - 0.1, 1.55, 0.25, M["apron"])


def gunship_waist(P, M):
    """Struts (cols 7 / 16, rows 12-17), the waist seam (row 14) and the lower hull's flange ridges."""
    for s in (-1, 1):
        x = s * 4.5
        st = [(11.6, x, 0.42, 1.25, 0.42, 0.42, M["strut"]), (11.9, x, 0.48, 1.25, 0.48, 0.48, M["strut"]),
              (17.0, x, 0.48, 1.0, 0.48, 0.48, M["strut"]), (17.6, x, 0.4, 0.95, 0.4, 0.4, M["strut"])]
        tube(P, st, n=10, p=2.0)
        # strut feet: chamfered clamp blocks where they meet the plate and the hull
        for y0, y1, z1 in ((11.3, 12.4, 1.6), (16.6, 17.8, 1.3)):
            box(P, x - 0.75, x + 0.75, y0, y1, 0.0, z1, 0.18, M["ridge"])
    # flange ridges (rows 13-15, cols 4-7 / 16-19)
    for s in (-1, 1):
        x0, x1 = sorted((s * 3.7, s * 8.3))
        box(P, x0, x1, 14.35, 15.55, G_BASE1 - 0.2, 1.25, 0.3, M["ridge"])
        x0, x1 = sorted((s * 4.0, s * 7.8))
        box(P, x0, x1, 12.8, 13.9, G_BASE1 - 0.2, 1.05, 0.25, M["ridge"])


def gunship_lower(P, M):
    """Lower hull: the V plates from the flange to the nose (rows 14-21) either side of the pod."""
    right = [(7.95, 13.85), (7.95, 14.95), (8.95, 15.05), (8.95, 15.92), (8.5, 16.0), (3.0, 21.5), (2.0, 22.0)]
    poly = right + [(-x, y) for x, y in reversed(right)]
    prism(P, poly, -1.1, 0.75, M["vplate"], ch=0.3)
    # raised V armour plates, inset from the outline, a panel line between them and the pod
    for s in (-1, 1):
        pts = [(s * 7.6, 16.3), (s * 4.0, 19.9), (s * 3.9, 19.9), (s * 3.9, 16.3)]
        if s < 0:
            pts = list(reversed(pts))
        prism(P, pts, 0.5, 1.15, M["vplate"], ch=0.18)


def pod_stations(M, f2):
    """The central pod (cols 9-14, rows 13-26): a round-topped hull to the pointed nose."""
    ys = [13.2, 13.6, 14.4, 15.5, 16.5, 18.0, 19.5, 21.0, 22.5, 23.5, 24.3, 25.0, 25.6, 26.2, 26.7, 26.95]
    ws = [2.4, 2.8, 2.95, 3.0, 3.0, 3.0, 3.0, 2.98, 2.95, 2.85, 2.55, 2.05, 1.6, 1.05, 0.5, 0.0]
    hs = [1.6, 2.0, 2.3, 2.45, 2.5, 2.5, 2.45, 2.35, 2.2, 2.0, 1.7, 1.35, 1.0, 0.7, 0.4, 0.0]
    st = []
    for y, w, h in zip(ys, ws, hs):
        m = M["pod_nose"] if y > 24.9 else M["pod"]
        st.append((y, 0.0, w, 0.1, h, 1.0, m))
    return st


def canopy(P, M):
    """Long blue canopy (cols 10-13, rows 19-24) in a frame on the pod's top, pointed at its front."""
    # square back edge: the glass spans all four columns on row 19 (a flat, capped back face)
    ys = [19.02, 19.3, 19.8, 21.0, 22.5, 23.4, 24.0, 24.55, 25.0]
    ws = [1.9, 1.94, 1.95, 1.95, 1.92, 1.75, 1.3, 0.75, 0.0]
    hz = [0.36, 0.48, 0.56, 0.62, 0.6, 0.52, 0.4, 0.25, 0.0]
    base = 2.2
    st = [(y, 0.0, w, base, h + 0.25, 0.2, M["glass"]) for y, w, h in zip(ys, ws, hz)]
    tube(P, st, n=18, p=2.2)
    # frame: a slightly wider, lower collar under the glass (the 5/4 pixels round it)
    st = [(y, 0.0, w + 0.32 if w > 0 else 0.0, base - 0.1, 0.25, 0.25, M["frame"])
          for y, w in zip([18.85, 19.0, 19.7, 21.0, 22.5, 23.5, 24.2, 24.8, 25.25], [1.9, 1.92, 1.95, 1.95, 1.92, 1.7, 1.2, 0.6, 0])]
    tube(P, st, n=18, p=2.2)


def build_gunship(coll, eye_open):
    base = "newshs-93"
    name = f"{base}-f2" if eye_open else base
    sprite = common.load_sprite(WT, base)
    Mt = Mats(sprite, name)
    warm = 2 if eye_open else 0  # the eye's light on what is under it (frame 131)
    M = {
        "deck": Mt(3, "deck", metallic=0.4, roughness=0.45),
        "rail": Mt(5, "rail", metallic=0.5, roughness=0.36),
        "groove": Mt(2, "groove", metallic=0.3, roughness=0.6),
        "slot": Mt(2, "slot", metallic=0.3, roughness=0.6),
        "panel": Mt(5, "panel", metallic=0.45, roughness=0.38),
        "lip": Mt(8, "lip", metallic=0.5, roughness=0.32),
        "rib": Mt(9, "rib", metallic=0.5, roughness=0.32),
        "head": Mt(8, "head", metallic=0.5, roughness=0.34),
        "head_lip": Mt(10, "head_lip", metallic=0.5, roughness=0.32),
        "hatch": Mt(1, "hatch", metallic=0.3, roughness=0.55),
        "apron": Mt(6 if eye_open else 4, "apron", metallic=0.45, roughness=0.4),
        "strut": Mt(7 + warm, "strut", metallic=0.5, roughness=0.34),
        "ridge": Mt(6, "ridge", metallic=0.45, roughness=0.38),
        "vplate": Mt(4, "vplate", metallic=0.45, roughness=0.4),
        "pod": Mt(5 + (1 if eye_open else 0), "pod", metallic=0.5, roughness=0.36),
        "pod_nose": Mt(3, "pod_nose", metallic=0.45, roughness=0.4),
        "frame": Mt(5, "frame", metallic=0.5, roughness=0.36),
        "glass": Mt(147, "glass", metallic=0.1, roughness=0.12, emission=0.25),
        "lamp_house": Mt(113, "lamp_house", metallic=0.45, roughness=0.4),
        "lamp": Mt(115, "lamp", metallic=0.0, roughness=0.25, emission=2.5),
        "eye_rim": Mt(115, "eye_rim", metallic=0.3, roughness=0.35, emission=0.6),
        "eye": Mt(117, "eye", metallic=0.0, roughness=0.2, emission=3.0),
        "eye_hot": Mt(121, "eye_hot", metallic=0.0, roughness=0.2, emission=4.0),
        "eye_low": Mt(118, "eye_low", metallic=0.0, roughness=0.2, emission=3.0),
        "eye_spill": Mt(114, "eye_spill", metallic=0.2, roughness=0.4, emission=0.5),
    }
    P = T.Part(name, smooth_angle=38)
    gunship_plate(P, M)
    for s in (-1, 1):
        gunship_rails(P, M, s)
    gunship_panel(P, M)
    gunship_head(P, M, eye_open)
    gunship_waist(P, M)
    gunship_lower(P, M)
    pst = pod_stations(M, eye_open)
    tube(P, pst, n=20, p=2.6)
    canopy(P, M)
    # dark channels between pod and V plates (cols 8 / 15, rows 14-19)
    for s in (-1, 1):
        x0, x1 = sorted((s * 3.0, s * 3.9))
        box(P, x0, x1, 14.2, 20.4, 0.6, 0.95, 0.05, M["slot"])
    obj = finish(P, Mt.list, coll, 28, 0.0)
    clouds = [T.cbox(-9.0, 9.0, 2.0, 13.9, G_BASE0, RAIL_TOP + 0.3, 0.4)]
    clouds.append([(x, y, z) for x, y in ((-3.0, 7.8), (3.0, 7.8), (3.0, 13.4), (-3.0, 13.4))
                   for z in (0.0, HEAD_TOP + (0.8 if eye_open else 0.1))])
    clouds.append(T.cbox(-8.0, 8.0, 13.5, 15.1, -1.1, 1.3, 0.2))
    clouds.append(T.cbox(-8.95, 8.95, 15.0, 15.95, -1.1, 1.3, 0.2))
    clouds.append([(x, y, z) for x, y in ((-8.5, 15.95), (8.5, 15.95), (3.0, 21.5), (-3.0, 21.5))
                   for z in (-1.1, 1.15)])
    clouds.append(tube_cloud(pst, grow=0.05))
    clouds.append([(x, y, z) for x in (-1.9, 1.9) for y in (19.2, 24.2) for z in (2.0, 3.05)])
    shell = proxy_shell(name, clouds, coll, 28, 0.0, faces=2500)
    return sprite, [obj, shell]


# =================================================================================================
# review renders
# =================================================================================================
def set_frame_colours(objs, frame):
    mats = {m for o in objs if o.type == "MESH" for m in o.data.materials if m}
    saved = []
    for m in mats:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        saved.append((m, tuple(m.diffuse_color), tuple(bsdf.inputs["Base Color"].default_value),
                      tuple(bsdf.inputs["Emission Color"].default_value)))
        rgb = m.get("tyrian_frame_rgb", {}).get(str(frame)) if frame is not None else None
        if rgb is not None:
            m.diffuse_color = (*rgb, 1.0)
            bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
            if bsdf.inputs["Emission Strength"].default_value > 0:
                bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
    return saved


def restore(saved):
    for m, dc, bc, ec in saved:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        m.diffuse_color = dc
        bsdf.inputs["Base Color"].default_value = bc
        bsdf.inputs["Emission Color"].default_value = ec


def camera(scene, name, loc, look, ortho=None, lens=50):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return cam


def set_engine(scene, eevee):
    if not eevee:
        scene.render.engine = "BLENDER_WORKBENCH"
        return
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            return
        except TypeError:
            continue


def renders(objs, sprite, out, tag, W, H, frames, lit_frame):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o not in objs
    shell = objs[1]
    k = 10
    # palette-colour top views (flat, no AA) on the sprite grid, one per frame
    set_engine(scene, False)
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = W * k, H * k
    scene.render.resolution_percentage = 100
    shell.hide_render = True
    top = camera(scene, f"cam_top_{tag}", (0, 0, 10), (0, 0, 0), ortho=max(W, H) * PX)
    top.rotation_euler = (0, 0, 0)
    scene.camera = top
    for f in frames:
        saved = set_frame_colours(objs, f)
        scene.render.filepath = str(out / f"index_{f}.png")
        bpy.ops.render.render(write_still=True)
        restore(saved)
    # lit views (EEVEE)
    set_engine(scene, True)
    vt = [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items]
    scene.view_settings.view_transform = "AgX" if "AgX" in vt else "Standard"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.05, 0.055, 0.07, 1)
    bg.inputs["Strength"].default_value = 1.0
    if "sun" not in bpy.data.objects:
        sun_d = bpy.data.lights.new("sun", "SUN")
        sun_d.energy = 4.0
        sun = bpy.data.objects.new("sun", sun_d)
        scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(40), math.radians(-25), math.radians(-30))
        fill_d = bpy.data.lights.new("fill", "SUN")
        fill_d.energy = 1.0
        fill = bpy.data.objects.new("fill", fill_d)
        scene.collection.objects.link(fill)
        fill.rotation_euler = (math.radians(-50), math.radians(30), math.radians(150))
    scene.render.resolution_x = scene.render.resolution_y = 480
    s = max(W, H) * PX * 1.12
    D = max(W, H) * PX * 2.0
    views = [
        ("top", (0, 0, 10), (0, 0, 0), s),
        ("game", (0, -D * 0.55, D * 0.85), (0, 0, 0.0), None),
        ("q34", (D * 0.62, -D * 0.62, D * 0.55), (0, 0, 0.0), None),
        ("q34rear", (-D * 0.62, D * 0.62, D * 0.55), (0, 0, 0.0), None),
        ("front", (0, -10, 0.05), (0, 0, 0.05), s),
        ("rear", (0, 10, 0.05), (0, 0, 0.05), s),
        ("side", (10, 0, 0.05), (0, 0, 0.05), s),
        ("under", (0.01, -0.01, -10), (0, 0, 0), s),
    ]
    saved = set_frame_colours(objs, lit_frame)
    for name, loc, look, ortho in views:
        cam = camera(scene, f"cam_{name}_{tag}", loc, look, ortho=ortho, lens=55)
        if name == "top":
            cam.rotation_euler = (0, 0, 0)
        if name == "under":
            cam.rotation_euler = (math.pi, 0, 0)
        scene.camera = cam
        scene.render.filepath = str(out / f"view_{name}.png")
        bpy.ops.render.render(write_still=True)
    restore(saved)
    cam = camera(scene, f"cam_game2_{tag}", (0, -D * 0.55, D * 0.85), (0, 0, 0.0), lens=55)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = 240
    for f in frames:
        saved = set_frame_colours(objs, f)
        scene.render.filepath = str(out / f"game_{f}.png")
        bpy.ops.render.render(write_still=True)
        restore(saved)


def tris(objs):
    t = 0
    for o in objs:
        o.data.calc_loop_triangles()
        t += len(o.data.loop_triangles)
    return t


def subset(sprite, frames):
    sprites = copy.deepcopy(sprite["sprites"])
    for s in sprites:
        s["frames"] = [f for f in s["frames"] if f in frames]
    return [s for s in sprites if s["frames"]]


def main():
    """Build and export the three models exactly as the old newshs-9.py / newshs-93.py did."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection("newshs-9")
    built = []
    sp9, objs9 = build_drone(coll)
    built.append(("newshs-9", sp9, objs9, 12, 14, [9, 10, 28, 29], 29, sp9["sprites"]))
    sp93, objs93 = build_gunship(coll, False)
    built.append(("newshs-93", sp93, objs93, 24, 28, [93], 93, subset(sp93, [93])))
    _, objs131 = build_gunship(coll, True)
    built.append(("newshs-93-f2", sp93, objs131, 24, 28, [131], 131, subset(sp93, [131])))
    for name, sp, objs, W, H, frames, lit, sprites in built:
        common.export_sprite_model(WT, objs, f"enemies/{name}", sprites)
        print(f"{name}: {tris(objs[:1])} triangles, shell {len(objs[1].data.polygons)} faces")
    return built


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    built = main()
    if "--render" in argv:
        rd = Path(argv[argv.index("--render") + 1])
        for name, sp, objs, W, H, frames, lit, _s in built:
            renders(objs, sp, rd / name, name, W, H, frames, lit)
