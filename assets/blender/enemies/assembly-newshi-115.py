"""SAVARA airship, front half (newshi.shp, assembly-newshi-115, 14 pieces): blueprint-led.

User correction: this is a BLIMP. The tail cap is assembly-newshi-154 (the egg's south end: enemies
87-89 of the same formation, drawn on the same ground pass right under this assembly's last row), a
separate enemy object; this envelope tapers into its cut section.

A hard-surface rebuild in the player ships' style (D50-D53, D65), its top-view edge on the INNER
edge of the sprite's ink (D74). Engineering read, cross-sections first:

  envelope  a closed gas envelope floating above the water: elliptical sections (round above and
           below the equator), the plan the sprite's egg (pchip widths from the sprite's inner
           mask: blunt nose at row 28.6, 33.45 px half width from row 65), heights proportional to
           the half width ahead of the crown (an ellipsoidal nose), crown highest at row 70. Fix
           round 5: 36.5 px high on the crown (z -5 .. 31.5: the belly just over the water, the crown
           just over the player's shots and under the player's ship, 0.55 of the width), the tail
           tapering top and bottom into newshi-154's own cut section at row 112 (z 0 .. 14.2, its
           equator 3.4 up). Meridian seams (the sprite's light lines) above and below the equator,
           converging toward the tail; two latitude panel joints round the whole section; a riveted
           joint flange before the tail cut, where newshi-154 carries the envelope on.
  propeller a tilted nose fan (a vectoring propeller): hub housing and spinner on the nose tip,
           thrust axis forward and down (the disc rises TILT px per row toward the screen top, so
           the guard's plan is the sprite's ellipse). Twisted, pitched blades on the sprite's blade
           footprints (per frame: the second frame is the rotor turned), shanks to the spinner.
  duct     the red ring guard (fix round 5): a duct, a short tube round the disc with a bore
           parallel to the thrust axis and a rounded leading lip, its plan the sprite's band; its
           side frames carry it down the nose flanks into clamp blocks on the envelope's equator.
  mast     the duct's top strut: a grey box beam in the guard's plane from the crown down to the
           hub, five red lights in a dark channel on its spine, a clamp over the crown.
  nose     the gull-wing cowl plates and a dark collar plate (the propeller's bearing plate) round
           the nose; the socket, neck tube and red pendant on the nose top.
  gantry   the red dorsal fitting on the envelope (two L brackets, cross bar, rails, slots) and the
           red hatch ring further back.
  pods     (fix round 5) engine pods on pylons: the red pipe and the struts out of the flank are the
           pylons; each side arm's hardware (drum, frame plates, ram, knee, piston) sits on a
           streamlined nacelle hanging under it below the equator, with an intake (red lip, dark
           face, spinner) at the front and a nozzle with the exhaust glow at the back; a small tail
           pod under the foot carries the orange lamp.
  underside  the envelope's round belly; the nacelles (a plausible closed shape only).

Build space: x = sprite column edge (0..96), y = row edge (0..112, down the screen), z up, sprite
px. Blender: X = (x - 48) / 12, Y = (56 - y) / 12, Z = z / 12 (the assembly centre, screen
(150, 24), is the origin, as the current model). Mirror: x -> 97 - x.

Exports the game contract (common.export_sprite_model per piece: enemies/<piece> and, for the four
animated pieces, enemies/<piece>-f2, each with its outline shell). With --out it also writes a review
GLB (all 14 pieces at their places, the four -f2 pieces under an empty "frame2"):

  Blender --background --factory-startup --python assembly-newshi-115_A.py -- [--no-bake]
          [--out path.glb] [--stats stats.json]
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import cbox, pchip  # noqa: E402

NAME = "assembly-newshi-115"
ROOT = common.repo_root(__file__)
HERE = Path(__file__).resolve().parent
OUT = None  # review GLB only with --out
SX0, SY0 = 102, -32          # assembly pixel (0, 0) on screen
W_PX, H_PX = 96, 112
AX = 48.5                    # mirror axis (column edge); x' = 97 - x
PX = 1 / 12
ANIMATED = ["newshi-3", "newshi-5", "newshi-41", "newshi-43"]


def mx(x):
    return 97.0 - x


# ---------------------------------------------------------------------------------------------
# Materials: the sprite's own palette index per region (median of the part's top-view pixels,
# darkest shading and brightest highlights left out), satin metal / satin paint.
# ---------------------------------------------------------------------------------------------
SLOTS = [
    # name, palette index, metallic, roughness, emission
    ("dome", 8, 0.18, 0.34, 0),
    ("rib", 9, 0.18, 0.36, 0),   # fix round 6: the seams sit on the sprite's light lines (9)
    ("collar", 5, 0.15, 0.46, 0),
    ("seam", 6, 0.16, 0.40, 0),
    ("trench", 4, 0.12, 0.55, 0),
    ("slot", 7, 0.05, 0.75, 0),
    ("plinth", 4, 0.14, 0.50, 0),
    ("groove", 7, 0.10, 0.60, 0),
    ("hoop", 69, 0.06, 0.45, 0),
    ("mount", 1, 0.15, 0.45, 0),
    ("mast", 6, 0.16, 0.42, 0),
    ("head", 3, 0.15, 0.48, 0),
    ("channel", 3, 0.06, 0.70, 0),
    ("light1", 116, 0.0, 0.35, 2.5),
    ("light2", 117, 0.0, 0.35, 2.8),
    ("light3", 118, 0.0, 0.35, 3.0),
    ("light4", 119, 0.0, 0.35, 3.2),
    ("pylon", 8, 0.16, 0.40, 0),
    ("neck", 6, 0.18, 0.40, 0),
    ("gantry", 71, 0.06, 0.44, 0),
    ("gslot", 5, 0.05, 0.75, 0),
    ("loop", 72, 0.06, 0.42, 0),
    ("rotor", 13, 0.10, 0.36, 0),
    ("spoke", 1, 0.15, 0.45, 0),
    ("pipe", 70, 0.06, 0.42, 0),
    ("elbow", 5, 0.15, 0.45, 0),
    ("strut", 5, 0.15, 0.48, 0),
    ("strut_red", 70, 0.06, 0.48, 0),
    ("drum", 69, 0.06, 0.42, 0),
    ("frame", 5, 0.16, 0.44, 0),
    ("ram", 69, 0.06, 0.45, 0),
    ("knee", 69, 0.06, 0.44, 0),
    ("piston", 5, 0.28, 0.26, 0),
    ("rod", 69, 0.06, 0.44, 0),
    ("foot", 6, 0.15, 0.46, 0),
    ("lamp", 120, 0.0, 0.30, 4.0),
    ("belly", 1, 0.10, 0.60, 0),
    ("door", 3, 0.15, 0.50, 0),
    ("doorframe", 6, 0.16, 0.42, 0),
    ("cowl", 6, 0.20, 0.34, 0),
    ("cslot", 8, 0.05, 0.80, 0),
    ("pendant", 75, 0.06, 0.42, 0),
    ("socket", 7, 0.15, 0.50, 0),
    ("cowlrim", 6, 0.45, 0.22, 0),  # sheen on the chamfer: the lit rim
    ("lip", 4, 0.05, 0.75, 0),
    ("crown", 8, 0.20, 0.30, 0),
    ("wingout", 5, 0.18, 0.40, 0),
    ("nacelle", 1, 0.20, 0.34, 0),  # fix round 6: the sprite's 1 (dark gaps between the arm plates)
    ("intake", 2, 0.05, 0.80, 0),
]
S = {name: i for i, (name, *_r) in enumerate(SLOTS)}
GLOWING = {S["light1"], S["light2"], S["light3"], S["light4"], S["lamp"]}
UNBAKED = GLOWING | {S["rotor"], S["spoke"]}  # the blades live on their own (unbaked) object


def merged_sprite():
    data = common.load_sprite(ROOT, "newshi-115")
    colors = {}
    for e in data["assemblyLayout"]:
        colors.update(common.load_sprite(ROOT, e["model"])["colors"])
    data["colors"] = colors
    return data


def materials(sprite):
    out = []
    for name, idx, metal, rough, emit in SLOTS:
        m = common.palette_material(sprite, idx, f"nshi115a_{name}", metallic=metal, roughness=rough,
                                    emission_strength=emit)
        out.append(m)
    return out


# ---------------------------------------------------------------------------------------------
# Mesh building in sprite px
# ---------------------------------------------------------------------------------------------
class Part(T.Part):
    """usp_talon's Part; faces without a hint keep the winding they were made with."""

    def f(self, verts, mat, out=None, away=None):
        vs = []
        for v in verts:
            if not vs or vs[-1] is not v:
                vs.append(v)
        while len(vs) > 1 and vs[0] is vs[-1]:
            vs.pop()
        if len({id(v) for v in vs}) < 3 or len(vs) != len({id(v) for v in vs}):
            return None
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        self.hints.append((face, out, away))
        return face

    def orient(self):
        for face, out, away in self.hints:
            if not face.is_valid or (out is None and away is None):
                continue
            face.normal_update()
            c = face.calc_center_median()
            d = Vector(out) if out is not None else c - Vector(away)
            if face.normal.dot(d) < 0:
                face.normal_flip()


def box_prof(c=0.35):
    def prof(hw, hh):
        cc = min(c, hw * 0.45, hh * 0.45)
        return [(hw, hh - cc), (hw - cc, hh), (-hw + cc, hh), (-hw, hh - cc),
                (-hw, -hh + cc), (-hw + cc, -hh), (hw - cc, -hh), (hw, -hh + cc)]
    return prof


def round_prof(n=10):
    def prof(hw, hh):
        return [(hw * math.cos(2 * math.pi * (k + 0.5) / n), hh * math.sin(2 * math.pi * (k + 0.5) / n))
                for k in range(n)]
    return prof


OCT = round_prof(8)


def sweep(P, st, mat, prof=OCT, cap0=True, cap1=True, ups=None, smooth=True):
    """A tube through stations (x, y, z, half_width, half_height): rings perpendicular to the 3D
    path, the width across it (horizontal unless `ups` gives a per-station up vector)."""
    pts = [Vector(s[:3]) for s in st]
    n = len(pts)
    rings = []
    for i, (x, y, z, hw, hh) in enumerate(st):
        t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        t.normalize()
        upr = Vector(ups[i]) if ups else Vector((0, 0, 1))
        if abs(t.dot(upr)) > 0.95:
            upr = Vector((0, 1, 0))
        side = t.cross(upr).normalized()
        up = side.cross(t).normalized()
        if hw <= 0 and hh <= 0:
            rings.append([P.v(pts[i])] * len(prof(1, 1)))
        else:
            rings.append([P.v(pts[i] + side * a + up * b) for a, b in prof(hw, hh)])
    k = len(rings[0])
    faces = []
    for i in range(n - 1):
        c = (pts[i] + pts[i + 1]) / 2
        for a in range(k):
            b = (a + 1) % k
            faces.append(P.f((rings[i][a], rings[i][b], rings[i + 1][b], rings[i + 1][a]), mat, away=tuple(c)))
    if cap0 and st[0][3] > 0:
        P.f(rings[0], mat, out=tuple(pts[0] - pts[1]))
    if cap1 and st[-1][3] > 0:
        P.f(rings[-1], mat, out=tuple(pts[-1] - pts[-2]))
    return faces


def block(P, x0, x1, y0, y1, z0, z1, mat, ch=0.4, chz=None):
    T.hull(P, cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


def densify(poly, step=1.0):
    out = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    return out


def prism(P, poly, z0, z1, mat, ch=0.35, zf=None, step=1.0, top_mat=None):
    """A convex plan polygon from z0 to z1 (both measured above zf(x, y) when given), its top edge
    chamfered `ch`, the top a fan (so it follows a curved base)."""
    zf = zf or (lambda x, y: 0.0)
    pts = densify(poly, step)
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    lo = [P.v((x, y, zf(x, y) + z0)) for x, y in pts]
    mid = [P.v((x, y, zf(x, y) + z1 - ch)) for x, y in pts]
    hi = []
    for x, y in pts:
        d = math.hypot(x - cx, y - cy) or 1
        k = max(0.0, 1 - ch / d)
        hx, hy = cx + (x - cx) * k, cy + (y - cy) * k
        hi.append(P.v((hx, hy, zf(hx, hy) + z1)))
    zc = zf(cx, cy)
    centre = P.v((cx, cy, zc + z1))
    away = (cx, cy, zc + (z0 + z1) / 2)
    n = len(pts)
    tm = mat if top_mat is None else top_mat
    for i in range(n):
        j = (i + 1) % n
        P.f((lo[i], lo[j], mid[j], mid[i]), mat, away=away)
        P.f((mid[i], mid[j], hi[j], hi[i]), mat, away=away)
        P.f((hi[i], hi[j], centre), tm, out=(0, 0, 1))
    P.f(lo, mat, out=(0, 0, -1))


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def mir(poly):
    return [(mx(x), y) for x, y in reversed(poly)]


def mirror_part(P):
    """Orient, then add the mirror image (x -> 97 - x) of everything in P."""
    P.orient()
    P.hints = []
    bm = P.bm
    ret = bmesh.ops.duplicate(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:])
    for g in ret["geom"]:
        if isinstance(g, bmesh.types.BMVert):
            g.co.x = mx(g.co.x)
    bmesh.ops.reverse_faces(bm, faces=[g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)])


def mirror_only(P):
    """Orient, then move everything in P to its mirror image (x -> 97 - x)."""
    P.orient()
    P.hints = []
    for v in P.bm.verts:
        v.co.x = mx(v.co.x)
    bmesh.ops.reverse_faces(P.bm, faces=P.bm.faces[:])


def finish(P, mats, coll, oriented=False, smooth_angle=32.0):
    if not oriented:
        P.orient()
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, -48 * PX), (0, -PX, 0, 56 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)  # the map is a reflection
    me = bpy.data.meshes.new(P.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(P.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    return obj


# ---------------------------------------------------------------------------------------------
# The dome: widths from the sprite's inner mask (row centres), pchip between stations
# ---------------------------------------------------------------------------------------------
W_ST = [(28.6, 0.0), (28.75, 4.0), (29.0, 6.8), (29.5, 9.6), (30.0, 11.6), (31.0, 14.2), (32.0, 16.2),
        (33.0, 17.6), (34.0, 18.7), (35.0, 19.6), (36.5, 20.8), (38.0, 21.9), (41.0, 23.9), (44.0, 26.0),
        (45.0, 27.0), (46.0, 27.6), (47.5, 28.4), (49.0, 28.75), (50.0, 29.15), (52.0, 29.55), (53.0, 30.0),
        (55.0, 31.2), (58.0, 32.3), (60.0, 32.6), (64.6, 32.6), (65.4, 33.45), (102.6, 33.45), (103.2, 32.6),
        (106.6, 32.5), (107.1, 31.6), (109.6, 31.5), (110.1, 30.6), (112.0, 30.4)]
_wf = pchip([a for a, _ in W_ST], [b for _, b in W_ST])
# Fix round 3: the shell's own width is a smooth version of the plan (no pixel steps), so the pixel
# steps of the curb (rows 65, 103, 107, 110) no longer crease the shell straight across.
WS_ST = [(y, w) for y, w in W_ST if y <= 58.0] + [(62.0, 32.75), (70.0, 33.45), (100.0, 33.45), (106.0, 32.4),
                                                  (109.0, 31.4), (112.0, 30.6)]
_wsf = pchip([a for a, _ in WS_ST], [b for _, b in WS_ST])
# Blimp redesign (user correction: it is an airship). The envelope is a closed, floating body: its
# plan exactly the sprite's egg (widest at the equator), its sections ellipses about an equator that
# runs level under the crown and drops toward the tail. Heights, fix round 5 (the review: too flat):
# the belly goes down to just above the water (5.4 px under the model's origin: the ground-enemy pass
# is 0.45 units up) and the crown up to 31.5 px, just over the player's shots (2.9 units, 29.4 px
# over the origin) and under the player's ship (3.3 units, 34.2 px); the dorsal fittings stay under
# 33.5. That is 36.5 px of height on the crown's 66.9 px width (0.55; 0.6 would need 40 px, into the
# ship's pass or the water). The tail tapers top and bottom into the tail cap, assembly-newshi-154
# (enemies 87-89, the same formation, drawn on the same ground pass right under this assembly's last
# row): at the cut (row 112, 154's top edge) the section is 154's own cut section, a dome from z 0 (its flat
# underside) to 14.2 on the axis, its equator 3.4 up (measured from public/models/enemies/newshi-15x).
ZC = 13.25         # envelope axis height under the crown (sprite px above the model origin)
HMAX = 18.25       # envelope half height at the crown (row 70); half width there 33.45
NXS = 2.0          # section superellipse exponent
NXS_U = 1.8        # fix round 6: the upper half a little rounder over the crown (less flat top, so the
                   # game light falls off across the width as the sprite's shading does)
SEC_M = 0.5        # section exponent: 0.5 = a true ellipse, round above and below the equator
Y_CROWN = 70.0     # the egg's crown (the sprite's highlight ellipses centre near row 70)
TR_HALF, TR_DEPTH, TR_END = 4.0, 2.4, 45.0
Y_END = 112.0      # the cut where the tail cap (assembly-newshi-154) continues the envelope
# along the body (rows): equator height, upper half height, lower half depth
_PR_Y = [20.0, 76.0, 88.0, 98.0, 106.0, 112.0, 114.0]
_zcf = pchip(_PR_Y, [ZC, ZC, 12.2, 9.4, 6.2, 3.4, 3.4])
_huf = pchip(_PR_Y, [HMAX, HMAX, 17.6, 15.6, 13.0, 10.8, 10.8])
_hlf = pchip(_PR_Y, [HMAX, HMAX, 17.2, 13.2, 7.6, 3.4, 3.4])


def dome_w(y):
    return max(0.0, _wf(min(max(y, 28.6), 112.0))) if y >= 28.6 else 0.0


def smooth_w(y):
    return max(0.0, _wsf(min(max(y, 28.6), 112.0))) if y >= 28.6 else 0.0


def nose_k(y):
    """The nose is an ellipsoid: heights in proportion to the plan's half width ahead of the crown."""
    if y >= Y_CROWN:
        return 1.0
    return min(smooth_w(y), 33.45) / 33.45


def env_c(y):
    return float(_zcf(min(max(y, 20.0), 114.0)))


def env_u(y):
    """Envelope upper half height at row y."""
    return float(_huf(min(max(y, 20.0), 114.0))) * nose_k(y)


def env_l(y):
    """Envelope lower half depth at row y."""
    return float(_hlf(min(max(y, 20.0), 114.0))) * nose_k(y)


def dome_h(y):
    return env_u(y)


def shell_w(y):
    # the envelope's equator is the plan's edge (its top-view edge on the sprite's inner mask, D74)
    w = dome_w(y)
    return max(min(smooth_w(y), w), w * 0.55)


def lower_z(x, y):
    """The envelope's lower half (no trench): an ellipse quadrant under the equator."""
    w = shell_w(y)
    if w <= 0:
        return env_c(y)
    u = min(1.0, abs(x - AX) / w)
    return env_c(y) - env_l(y) * max(0.0, 1 - u ** NXS) ** SEC_M


def trench_k(y):
    return min(1.0, shell_w(y) / 9.0)


def surf(x, y, trench=True):
    """Height of the envelope's upper surface at (x, y); ZC at the equator and outside."""
    w = shell_w(y)
    if w <= 0:
        return env_c(y)
    u = min(1.0, abs(x - AX) / w)
    z = env_c(y) + env_u(y) * max(0.0, 1 - u ** NXS_U) ** SEC_M
    if trench and y < TR_END + 0.6:
        k = trench_k(y)
        d = abs(x - AX)
        wall0, wall1 = TR_HALF * k - 0.05, (TR_HALF + 0.3) * k
        f = 1.0 if d <= wall0 else (0.0 if d >= wall1 else (wall1 - d) / (wall1 - wall0))
        g = 1.0 if y <= TR_END else max(0.0, 1 - (y - TR_END) / 0.6)
        z -= TR_DEPTH * k * f * g
    return z


def surf_nt(x, y):
    return surf(x, y, trench=False)


def normal(x, y, trench=False):
    e = 0.05
    dzx = (surf(x + e, y, trench) - surf(x - e, y, trench)) / (2 * e)
    dzy = (surf(x, y + e, trench) - surf(x, y - e, trench)) / (2 * e)
    return Vector((-dzx, -dzy, 1.0)).normalized()


def seam_y(x):
    """The nose cap's rear seam (a V): row 44 at the trench, row ~54 at the flanks."""
    return TR_END - 1 + max(0.0, abs(x - AX) - TR_HALF) * 0.42


U_OUT = [0.20, 0.30, 0.43, 0.52, 0.61, 0.68, 0.746, 0.80, 0.85, 0.895, 0.93, 0.96, 0.98, 0.993, 0.9985, 1.0]
GROOVES = [66.0, 94.0]
# Groove arcs (fix round 3): the sprite's latitude arcs ring the crown, the front one bowing forward
# at the axis (row 62 there, 66 at the flanks), the rear one bowing back (row 97 at the axis).
_arch = pchip([28.0, 54.0, 66.0, 78.0, 84.0, 94.0, 104.0, 112.0], [0.0, 0.0, -4.5, 0.0, 0.0, 4.0, 0.0, 0.0])


def section_offsets(y):
    """Offsets |x - AX| of the section samples, axis outwards."""
    w = shell_w(y)
    k = trench_k(y)
    inner = [0.0, 2.0 * k, (TR_HALF - 0.05) * k, (TR_HALF + 0.3) * k]
    u0 = inner[-1] / w + 0.03 if w > 0 else 1.0
    us = U_OUT if U_OUT[0] >= u0 else [u0 + (u - U_OUT[0]) * (1 - u0) / (1 - U_OUT[0]) for u in U_OUT]
    return inner + [u * w for u in us]


def arch(t, u):
    """Rows warp about the two groove arcs (the panel joints arch like the sprite's)."""
    if t <= 54.0 or t >= 104.0:
        return t
    return t + float(_arch(t)) * (1 - u * u)


def build_dome(P):
    rows = [28.6, 28.75, 29.0, 29.5, 30.0, 30.6, 31.3, 32.0, 33.0, 34.0, 35.0, 36.5, 38.0, 39.5, 41.0, 42.5,
            44.0, 45.0, 45.6, 46.5, 48.0, 50.0, 52.0, 54.0, 56.0, 58.0, 60.0, 62.0, 64.0, 66.0, 68.5, 71.0,
            74.0]
    groove_bottom = set()
    for yc in GROOVES:
        rows += [yc - 0.45, yc - 0.2, yc + 0.2, yc + 0.45]
        groove_bottom |= {round(yc - 0.2, 3), round(yc + 0.2, 3)}
    rows += [76.5, 79.0, 82.0, 86.0, 90.0, 92.0, 96.0, 99.0, 102.0, 104.5, 107.0, 109.5, Y_END]
    rows += [y for y, _ in W_ST if 44.0 <= y < Y_END] + [110.8]
    rows = sorted(set(round(r, 3) for r in rows))
    loops = []
    for t in rows:
        w, ws = dome_w(t), shell_w(t)
        if w <= 0:
            apex = P.v((AX, t, env_c(t)))
            nn = 2 * (len(section_offsets(30.0)) - 1) + 1
            loops.append([apex] * (2 * nn - 2))
            continue
        offs = section_offsets(t)
        right = []
        for d in reversed(offs[1:]):
            right.append(AX + d)
        xs = right + [AX] + [AX - d for d in offs[1:]]
        shell = []
        # the sprite's rear-right corner is cut 3 px shorter on its last row than the left one
        kR = (w - 3.0 * min(1.0, max(0.0, (t - 110.8) / 0.8))) / w
        for x in xs:
            u = min(1.0, abs(x - AX) / ws)
            y = arch(t, u)
            z = surf(x, y)
            p = Vector((x if x <= AX else AX + (x - AX) * kR, y, z))
            if round(t, 3) in groove_bottom and u < 0.999:
                p -= normal(x, y) * 0.45
            shell.append(P.v(tuple(p)))
        # the lower half, left to right (the equator points are the upper list's ends): a round
        # belly, the panel joints carried round it
        lower = []
        for x in reversed(xs[1:-1]):
            u = min(1.0, abs(x - AX) / ws)
            y = arch(t, u)
            z = lower_z(x, y)
            if round(t, 3) in groove_bottom and u < 0.999:
                z += 0.45 * (1 - u * u) ** 0.5
            lower.append(P.v((x if x <= AX else AX + (x - AX) * kR, y, z)))
        loops.append(shell + lower)
    n = len(loops[0])
    nu = 2 * (len(section_offsets(30.0)) - 1) + 1  # upper vertices per loop
    for i in range(len(loops) - 1):
        t0, t1 = rows[i], rows[i + 1]
        r0, r1 = loops[i], loops[i + 1]
        for k in range(n):
            j = (k + 1) % n
            q = (r0[k], r1[k], r1[j], r0[j])
            cx = sum(v.co.x for v in q) / 4
            cy = sum(v.co.y for v in q) / 4
            cz = sum(v.co.z for v in q) / 4
            if k < nu - 1:
                mat = dome_region(cx, cy, cz, t0, t1, groove_bottom)
            else:
                g = round(t0, 3) in groove_bottom or round(t1, 3) in groove_bottom
                mat = S["groove"] if g else S["dome"]
            P.f(q, mat)  # one cyclic ring, built in one direction: the winding is outward
    # the cut at the tail, where the tail cap (assembly-newshi-154) carries the envelope on
    # Fix round 6: the cut closed by a shallow dome (2.4 px aft), so the envelope is closed on its own;
    # in the formation the tail cap (assembly-newshi-154) sits over it.
    last = loops[-1]
    zs = [v.co.z for v in last]
    cc = Vector((AX, Y_END, (min(zs) + max(zs)) / 2))
    prev = last
    for ph in (30.0, 55.0, 75.0):
        a = math.radians(ph)
        ring = [P.v((cc.x + (v.co.x - cc.x) * math.cos(a), Y_END + 2.4 * math.sin(a), cc.z + (v.co.z - cc.z) * math.cos(a)))
                for v in last]
        for i in range(len(ring)):
            j = (i + 1) % len(ring)
            P.f((prev[i], prev[j], ring[j], ring[i]), S["dome"], away=(cc.x, Y_END - 3.0, cc.z))
        prev = ring
    apex = P.v((cc.x, Y_END + 2.4, cc.z))
    for i in range(len(prev)):
        P.f((prev[i], prev[(i + 1) % len(prev)], apex), S["dome"], away=(cc.x, Y_END - 3.0, cc.z))
    return rows, loops


def dome_region(x, y, z, t0, t1, groove_bottom):
    d = abs(x - AX)
    if y < TR_END + 0.6 and d < (TR_HALF + 0.3) * trench_k(y) - 0.02:
        return S["trench"]
    if round(t0, 3) in groove_bottom or round(t1, 3) in groove_bottom:
        if round(t0, 3) in groove_bottom and round(t1, 3) in groove_bottom:
            return S["groove"]
        return S["groove"]
    if y < seam_y(x):
        u = d / max(shell_w(y), 1e-3)
        return S["collar"] if u > 0.746 + 0.004 else S["dome"]
    return S["dome"]


EGG_TAIL = 124.0   # fix round 6: the virtual tail of the egg the meridians are drawn on (inside 154)


def egg_w(y):
    """Half width of the whole egg (this envelope and the tail cap, 154, under it): the plan's own
    width ahead of the crown, then an ellipse closing at EGG_TAIL. The meridian seams are lines of
    constant fraction of it, so they bunch toward the nose (where the plan narrows) and toward the
    tail (where the egg does, though this piece is cut off at row 112, still 30 px wide)."""
    if y <= Y_CROWN:
        return shell_w(y)
    k = min(1.0, (y - Y_CROWN) / (EGG_TAIL - Y_CROWN))
    return min(shell_w(y), 33.45 * math.sqrt(max(0.0, 1 - k * k)))


def meridian(u, p, y):
    """Signed offset from the axis of the meridian seam u at row y."""
    ew = egg_w(y)
    return u * ew * (ew / 33.45) ** p


def on_dome(P, pts, hw, hh, lift, mat, prof=None):
    st, ups = [], []
    for x, y in pts:
        st.append((x, y, surf(x, y) + lift, hw, hh))
        ups.append(tuple(normal(x, y, trench=False)))
    sweep(P, st, mat, prof=prof or box_prof(0.15), ups=ups)


def build_dome_detail(P):
    # Longitudinal seams on meridians (fix round 3): each at a constant fraction of the egg's
    # half width EW, which narrows behind row 82 (the plan is cut off by the sprite's edge, the egg
    # is not), so the seams bow in and converge toward the tail as the sprite's do (cols 23 -> 30 and
    # 34 -> 41 between rows 82 and 110; the inner pair converges faster, as drawn).
    for u, p in ((0.0, 0.0), (0.419, 0.4), (-0.419, 0.4), (0.747, 0.0), (-0.747, 0.0)):
        if u == 0.0:
            y0 = 74.6
        else:
            # start on the V seam
            y0 = 44.0
            for _ in range(30):
                y0 = seam_y(AX + meridian(u, p, y0)) + 0.6
        ys = [y0 + (Y_END - 0.05 - y0) * k / 32 for k in range(33)]
        pts = [(AX + math.copysign(min(abs(meridian(u, p, y)), shell_w(y) - 0.6), u), y) for y in ys]
        on_dome(P, pts, 0.4, 0.2, 0.08, S["rib"])
    # The V seam strap between the nose cap and the dome.
    for s in (1, -1):
        pts = []
        for k in range(17):
            d = TR_HALF + 0.35 + (31.0 - TR_HALF) * k / 16
            x = AX + s * d
            y = seam_y(x)
            if d > shell_w(y) - 0.2:
                d = shell_w(y) - 0.2
                x = AX + s * d
            pts.append((x, y))
        on_dome(P, pts, 0.5, 0.28, 0.12, S["seam"])
    # Blimp: the meridian seams carry on round the lower half (seen from the side at the tilted
    # camera), from the nose to the tail cut; angles below the equator.
    # (fix round 6: on the egg too, so they converge toward the nose and the tail, not run parallel)
    for phi in (30.0, 62.0):
        cp = math.cos(math.radians(phi))
        for s in (1, -1):
            st, ups = [], []
            for k in range(41):
                y = 33.0 + (Y_END - 0.05 - 33.0) * k / 40
                w, h = shell_w(y) - 0.15, env_l(y)
                c_ = min(cp * egg_w(y), w - 0.15) / max(w, 1e-3)
                s_ = math.sqrt(max(0.0, 1 - c_ * c_))
                nx, nz = c_ / max(w, 1e-3), -s_ / max(h, 1e-3)
                L = math.hypot(nx, nz)
                st.append((AX + s * w * c_ + s * nx / L * 0.05, y, env_c(y) - h * s_ + nz / L * 0.05, 0.4, 0.2))
                ups.append((s * nx / L, 0.0, nz / L))
            sweep(P, st, S["rib"], prof=box_prof(0.15), ups=ups)
    # the joint flange at the tail cut (a riveted ring round the section, the tail cap bolts on here)
    st, ups = [], []
    yj = 110.4
    w = shell_w(yj) - 0.45
    for k in range(49):
        a = 2 * math.pi * k / 48
        h = (env_u(yj) if math.sin(a) >= 0 else env_l(yj)) - 0.3
        nx, nz = math.cos(a) / w, math.sin(a) / h
        L = math.hypot(nx, nz)
        x_ = AX + w * math.cos(a)
        z_ = (surf_nt(x_, yj) - 0.3 * nz / L) if math.sin(a) >= 0 else env_c(yj) + h * math.sin(a)
        st.append((x_, yj, z_, 0.55, 0.3))
        ups.append((nx / L, 0.0, nz / L))
    sweep(P, st, S["seam"], prof=box_prof(0.15), ups=ups)


# ---------------------------------------------------------------------------------------------
# The hoop (rotor shroud)
# ---------------------------------------------------------------------------------------------
# The band's plan, measured from the sprite's inner mask (fit round 1): outer and inner radius per angle
# about (48.5, 28) (degrees from the left horizontal; mirrored for the right), the shoulders by the mast
# 6 px deep, thinning to 4 px at the sides. Legs below row 28 per row (outer x, inner x).
HOOP_C = (AX, 28.0)
HOOP_R = [(90, 17.05, 12.6), (99, 17.3, 12.6), (105, 17.6, 12.6), (108, 17.85, 12.6), (111, 17.95, 12.55),
          (114, 17.95, 12.45), (117, 18.1, 12.3), (120, 18.45, 12.3), (123, 18.75, 12.2), (126, 18.85, 12.35),
          (129, 19.1, 12.6), (132, 19.3, 12.7), (135, 19.6, 12.85), (138, 19.95, 13.2), (141, 20.3, 13.5),
          (144, 20.6, 13.85), (147, 20.95, 14.3), (150, 21.35, 14.75), (153, 21.75, 15.3), (156, 22.0, 15.8),
          (159, 22.25, 16.25), (162, 22.45, 16.6), (165, 22.65, 17.05), (168, 22.95, 17.75), (171, 23.15, 18.4),
          (174, 23.35, 18.9), (177, 23.5, 19.3), (180, 23.55, 19.5)]
HOOP_LEG = [(28.0, 24.95, 28.9), (30.0, 25.0, 27.4), (32.0, 25.0, 26.6), (34.0, 25.0, 26.25), (36.0, 25.05, 26.6),
            (38.0, 25.2, 26.6), (39.8, 25.3, 26.9)]
_hro = pchip([a for a, _, _ in HOOP_R], [b for _, b, _ in HOOP_R])
_hri = pchip([a for a, _, _ in HOOP_R], [c for _, _, c in HOOP_R])
# Blimp: the hoop is the ring guard of a tilted nose propeller (a vectoring fan). Its front half is
# a flat annulus in the propeller's disc plane, which rises TILT px per row toward the screen top
# from the hub on the nose tip (so the plan is the sprite's ellipse: A 23.5, B 17); behind the hub
# the ring's legs ease back down the nose flanks into the brackets at the equator.
TILT = 0.85
HUB = (AX, 28.5, ZC)
_TN = math.hypot(1.0, TILT)
AXIS = Vector((0.0, -TILT / _TN, -1.0 / _TN))   # propeller thrust axis: forward and down


def _hz(y):
    """Height of the ring guard's mid-plane at row y."""
    y = float(y)
    if y <= HUB[1]:
        return ZC + TILT * (HUB[1] - y)
    return ZC - 3.4 * (1 - math.exp(-(y - HUB[1]) * TILT / 3.4))


def disc_z(y):
    """The propeller disc: the ring's plane moved 1 px back along the axis (inside the guard)."""
    return ZC + TILT * (HUB[1] - y) - _TN * 1.0


def hoop_pts(deg):
    """Outer and inner plan points of the band at `deg` (0 right, 90 crown, 180 left)."""
    d = deg if deg >= 90 else 180 - deg
    ro, ri = float(_hro(d)), float(_hri(d))
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (HOOP_C[0] + ro * c, HOOP_C[1] - ro * s), (HOOP_C[0] + ri * c, HOOP_C[1] - ri * s)


def hoop_stations():
    st = []
    for y, xo, xi in reversed(HOOP_LEG[1:]):  # left leg, bottom up
        st.append(((xo, y), (xi, y)))
    N = 40
    for k in range(N + 1):
        st.append(hoop_pts(180.0 * (1 - k / N)))
    for y, xo, xi in HOOP_LEG[1:]:
        st.append(((mx(xo), y), (mx(xi), y)))
    return st


DUCT_C = 5.0      # the duct's chord along the thrust axis (px)
DUCT_TMIN = 1.5   # its thinnest wall (on the crown, where the chord takes most of the band's plan)


def build_hoop(P):
    """Fix round 5: the ring guard is a DUCT, a short tube round the propeller disc, not a flat band
    lying in the disc. Each station's section stands in the plane of the thrust axis and the ring's
    radius: an inner wall parallel to the axis (the duct's bore, chord DUCT_C, the blades 1 px into
    it from the trailing edge), a thick rounded lip at the leading edge, the outer skin easing in to
    a thinner trailing edge. Its plan is the sprite's band exactly: the trailing edge's bore on the
    band's inner edge, the leading lip on its outer edge. On the crown the axis runs across the band,
    so the chord takes most of its 4.5 px and the wall is thin; on the sides the axis runs along the
    band, so the wall is the band's whole 4 px (the duct's side frames, which carry it down to the
    clamps on the equator)."""
    st = hoop_stations()
    a_ = AXIS
    ay = -a_.y   # the axis' plan component (north) per px of chord
    rings = []
    for (xo, yo), (xi, yi) in st:
        I3 = Vector((xi, yi, _hz(yi)))
        O3 = Vector((xo, yo, _hz(yo)))
        r3 = O3 - I3
        Lp = math.hypot(xo - xi, yo - yi) or 1e-3
        r_hat = r3.normalized()
        kr = Lp / max(r3.length, 1e-3)   # plan px per px of the in-plane radius
        ny = (yo - yi) / Lp
        # on the side frames below the hub the chord shrinks (their plan runs north-south, and a long
        # chord would carry the bore off the frame's inner edge)
        c = DUCT_C if max(yo, yi) <= HUB[1] else max(1.0, DUCT_C * (1 - (max(yo, yi) - HUB[1]) / 4.0))
        # the lip and skin held 0.5 px inside the band's outer edge (a full-width skin covered the
        # edge pixels the old chamfered band left)
        # (none on the crown, most on the diagonals, where the axis' shift runs off the curve)
        nx = (xo - xi) / Lp
        inset = 0.55 * (1 - ny * ny) + 0.6 * 2 * abs(nx * ny) * max(0.0, min(1.0, (0.8 - abs(ny)) / 0.1))
        inset -= 0.4 * max(0.0, (abs(ny) - 0.8) / 0.2)   # the crown's lip reaches the edge (rounded corner)
        t = max(DUCT_TMIN, (Lp - inset - c * ay * max(0.0, -ny)) / kr)
        # (axial, radial) section corners: trailing edge at 0, leading lip at c; bore at 0, skin at t
        sec = [(0.0, 0.2), (0.0, 0.62 * t), (0.35 * c, t), (0.94 * c, t), (c, 0.9 * t), (c, 0.22 * t),
               (0.88 * c, 0.0), (0.12 * c, 0.0)]
        ring = [I3 + a_ * ax_ + r_hat * rr for ax_, rr in sec]
        cen = I3 + a_ * (0.5 * c) + r_hat * (0.5 * t)
        rings.append(([P.v(tuple(p)) for p in ring], tuple(cen)))
    for (r0, c0), (r1, c1) in zip(rings, rings[1:]):
        cc = tuple((a + b) / 2 for a, b in zip(c0, c1))
        for k in range(8):
            j = (k + 1) % 8
            P.f((r0[k], r0[j], r1[j], r1[k]), S["hoop"], away=cc)
    P.f(rings[0][0], S["hoop"], out=(0, 1, -0.3))
    P.f(rings[-1][0], S["hoop"], out=(0, 1, -0.3))


def build_mounts(P):
    """Dark ribbed brackets taking the hoop's legs into the cap's flanks (rows 35-46); left side. The
    outer edge steps out a pixel every two rows, as the sprite's does."""
    poly = [(25.0, 38.6), (29.6, 38.6), (29.6, 46.0), (21.0, 46.0), (21.0, 45.6), (22.6, 44.0), (23.6, 42.0),
            (24.6, 40.0), (25.0, 39.0)]
    # blimp: a clamp block on the envelope's equator, where the guard's leg is pinned
    prism(P, poly, ZC - 4.2, ZC + 1.6, S["mount"], ch=0.45)
    for xr in (25.8, 27.1, 28.4):
        x1 = xr - 1.6
        sweep(P, [(xr, 39.4, ZC + 1.7, 0.3, 0.3), (x1, 45.2, ZC + 1.7, 0.3, 0.3)], S["mount"], prof=box_prof(0.1))
    # pin through the leg's foot
    zp = _hz(39.9) - 0.6
    sweep(P, [(25.3, 39.9, zp, 0.7, 0.7), (28.6, 39.9, zp, 0.7, 0.7)], S["head"], prof=round_prof(8))


# ---------------------------------------------------------------------------------------------
# Mast, lights, pylon, neck, capsule
# ---------------------------------------------------------------------------------------------
MAST_HH = 1.8   # the beam's half depth (across the ring plane)


def mast_top(y):
    """Top of the guard's top strut (the mast) at row y: the beam lies in the ring plane."""
    return _hz(y) - 0.3 + MAST_HH * _TN


def build_mast(P):
    # blimp: the mast is the ring guard's top strut, a box beam in the guard's plane from the crown
    # down to the hub on the nose (half width 4.4)
    st = [(AX, y, _hz(y) - 0.3, 4.4, MAST_HH) for y in (12.6, 16.0, 19.5, 23.0, 26.7)]
    sweep(P, st, S["mast"], prof=box_prof(0.55))
    # side flanges along the beam's foot
    for s in (1, -1):
        sweep(P, [(AX + s * 4.1, y, _hz(y) - 1.6, 0.5, 0.45) for y in (13.0, 19.5, 26.2)], S["head"], prof=box_prof(0.15))
    # head clamp over the hoop crown
    sweep(P, [(AX, 12.15, _hz(12.15) - 0.4, 4.4, 1.6), (AX, 13.6, _hz(13.6) - 0.4, 4.4, 1.6)], S["head"],
          prof=box_prof(0.5))
    # spine channel (dark) and the five lights in it (rows 14, 16, 18-19, 21-22, 24-25)
    prism(P, rect(46.5, 13.4, 51.0, 26.4), -0.2, 0.12, S["channel"], ch=0.05, zf=lambda x, y: mast_top(y))
    lights = ((13.9, 15.1, "light1"), (15.9, 17.1, "light1"), (17.9, 20.1, "light2"), (20.9, 23.1, "light3"),
              (23.9, 26.1, "light4"))
    for a, b, m in lights:
        prism(P, rect(47.0, a, 50.9, b), 0.0, 0.42, S[m], ch=0.18, zf=lambda x, y: mast_top(y))
    # the nose cap's dark collar plate behind the hub (rows 28-30.2): the propeller's bearing plate
    lip = [(39.6, 28.0), (57.4, 28.0), (58.9, 29.1), (59.6, 30.2), (37.4, 30.2), (38.1, 29.1)]
    prism(P, lip, ZC - 4.6, ZC + 3.6, S["lip"], ch=0.35)
    # the hub: a housing on the nose tip and a spinner along the thrust axis (forward and down)
    hc = Vector(HUB)
    st = []
    for s_, r_ in ((-3.6, 4.0), (-1.2, 4.5), (0.4, 4.5), (0.9, 4.1), (1.2, 3.6), (2.6, 3.1), (3.8, 2.2), (4.7, 1.1),
                   (5.2, 0.0)):
        p_ = hc + AXIS * s_
        st.append((p_.x, p_.y, p_.z, r_ * (1.15 if s_ < 0.5 else 1.0), r_))
    sweep(P, st, S["pylon"], prof=round_prof(16))
    # the neck: a round tube in the trench from a dark socket under the mast foot down to the red
    # clamp on the cross bar, then (slimmer) along the slot between the rails into the hatch ring
    zt = lambda y: surf(AX, y) + 2.2  # noqa: E731  tube axis, sunk 0.5 into the trench floor
    R16 = round_prof(16)
    sweep(P, [(AX, y, zt(y), 2.7, 2.7) for y in (30.0, 34.0, 38.0, 42.0, 45.4)], S["neck"], prof=R16)
    for y in (36.4, 39.6):  # clamp bands
        sweep(P, [(AX, y - 0.35, zt(y), 2.95, 2.95), (AX, y + 0.35, zt(y), 2.95, 2.95)], S["socket"], prof=R16)
    # socket: a dark chamfered housing around the tube's top end (rows 29.4-34.8)
    zs = zt(32.0) + 3.1
    block(P, 44.4, 52.6, 29.4, 34.8, surf(AX, 32.0) - 0.5, zs, S["socket"], ch=0.7)
    sweep(P, [(AX, 34.75, zt(34.8), 2.95, 2.95), (AX, 35.25, zt(34.8), 2.95, 2.95)], S["socket"], prof=R16)
    # red clamp saddled over the tube's crown on the cross bar (rows 41.4-45.2, 3 px wide)
    zc = zt(43.3) + 2.7
    block(P, 47.0, 50.0, 41.4, 45.3, zc - 1.6, zc + 0.8, S["pendant"], ch=0.5)
    # slim tube on beyond the cross bar, between the rails, into the hatch ring
    zl = lambda y: surf_nt(AX, y) + 0.3  # noqa: E731
    sweep(P, [(AX, y, zl(y), 1.5, 1.5) for y in (47.0, 52.0, 57.0, 62.0, 66.5)], S["neck"], prof=round_prof(12))


# ---------------------------------------------------------------------------------------------
# Gantry and loop on the cap
# ---------------------------------------------------------------------------------------------
def build_gantry(P):
    """The red yoke on the cap: two L brackets, a cross bar over the neck, four rails with a cross
    piece each side, dark slots between them; chunky chamfered plate sections."""
    Lb = [rect(37.0, 37.0, 43.4, 41.2), rect(37.4, 41.2, 40.4, 44.4)]
    rails = [rect(38.4, 48.4, 41.2, 61.2), rect(43.4, 47.6, 46.2, 62.6)]
    cross = [rect(38.4, 57.4, 46.4, 60.2)]
    for poly in Lb:
        prism(P, poly, -0.5, 2.2, S["gantry"], ch=0.6, zf=surf_nt)
        prism(P, mir(poly), -0.5, 2.2, S["gantry"], ch=0.6, zf=surf_nt)
    for poly in rails:
        prism(P, poly, -0.5, 1.4, S["gantry"], ch=0.55, zf=surf_nt)
        prism(P, mir(poly), -0.5, 1.9, S["gantry"], ch=0.55, zf=surf_nt)
    for poly in cross:
        prism(P, poly, -0.5, 2.1, S["gantry"], ch=0.5, zf=surf_nt)
        prism(P, mir(poly), -0.5, 2.1, S["gantry"], ch=0.5, zf=surf_nt)
    # dark slots either side of the slim neck tube, and between the rails
    for poly in (rect(46.15, 48.4, 47.2, 62.6), rect(41.15, 48.4, 43.45, 57.5)):
        prism(P, poly, -0.5, 0.2, S["gslot"], ch=0.06, zf=surf_nt)
        prism(P, mir(poly), -0.5, 0.2, S["gslot"], ch=0.06, zf=surf_nt)
    prism(P, rect(41.4, 44.6, 56.6, 48.6), -0.5, 2.6, S["gantry"], ch=0.6, zf=surf_nt)  # cross bar
    # bolts on the cross bar
    for x in (43.0, 54.0):
        prism(P, [(x - 0.6, 46.0), (x + 0.6, 46.0), (x + 0.6, 47.2), (x - 0.6, 47.2)], 2.4, 2.9, S["head"], ch=0.15,
              zf=surf_nt)
    # loop emblem (hatch ring) and its slot
    loop = [(49.4 + 3.4 * math.sin(2 * math.pi * k / 18), 69.5 - 5.0 * math.cos(2 * math.pi * k / 18)) for k in range(18)]
    prism(P, loop, -0.5, 1.0, S["loop"], ch=0.45, zf=surf_nt, step=3)
    prism(P, rect(48.1, 69.0, 50.7, 73.2), -0.5, 1.15, S["gslot"], ch=0.1, zf=surf_nt)


def strip(P, a, b, w, z0, z1, mat, ch=0.2):
    """A straight strip of width w on the dome from a to b (plan points)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    poly = [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]
    prism(P, poly, z0, z1, mat, ch=ch, zf=surf_nt)


def draped_plate(P, poly, z0, z1, mat, top_mat, ch=0.6, zf=surf_nt, step=0.8, rings=(0.72, 0.45, 0.2), bulge=0.0, zlo=None):
    """A plate of constant thickness draped on a curved base: as prism (walls, chamfer in `mat`), but
    its top in `top_mat` follows zf through concentric inner rings instead of one flat fan."""
    pts = densify(poly, step)
    n = len(pts)
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    lo = [P.v((x, y, (zlo or zf)(x, y) + z0)) for x, y in pts]
    mid = [P.v((x, y, zf(x, y) + z1 - ch)) for x, y in pts]
    hi_xy = []
    for x, y in pts:
        d = math.hypot(x - cx, y - cy) or 1
        k = max(0.0, 1 - ch / d)
        hi_xy.append((cx + (x - cx) * k, cy + (y - cy) * k))
    hi = [P.v((x, y, zf(x, y) + z1)) for x, y in hi_xy]
    away = (cx, cy, zf(cx, cy) + (z0 + z1) / 2)
    for i in range(n):
        j = (i + 1) % n
        P.f((lo[i], lo[j], mid[j], mid[i]), mat, away=away)
        P.f((mid[i], mid[j], hi[j], hi[i]), mat, away=away)
    prev = hi
    for f in rings:
        ring = []
        for x, y in hi_xy:
            rx, ry = cx + (x - cx) * f, cy + (y - cy) * f
            ring.append(P.v((rx, ry, zf(rx, ry) + z1 + bulge * (1 - f * f))))
        for i in range(n):
            j = (i + 1) % n
            P.f((prev[i], prev[j], ring[j], ring[i]), top_mat, out=(0, 0, 1))
        prev = ring
    centre = P.v((cx, cy, zf(cx, cy) + z1 + bulge))
    for i in range(n):
        P.f((prev[i], prev[(i + 1) % n], centre), top_mat, out=(0, 0, 1))
    P.f(lo, mat, out=(0, 0, -1))


def gap_strip(P, a, b, w, lift, mat):
    """A thin strip draped on the dome from a to b (plan points), w wide, its top `lift` above it."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    poly = [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)]
    draped_plate(P, poly, -0.6, lift, mat, mat, ch=0.08, step=0.5)


# Fix round 4: the gull wing, read from the sprite's tones (lit from the upper left, so the left
# wing is light and the right one dark; the medians of both sides are the paint):
#   crown  the lit crescent each side of the socket (rows 30.6-45, cols 29-43.6): sprite median 8.
#          A convex pillow (bulged top) so the game light gives it a light centre and dark edges.
#   band   the chevron plate between the sprite's two diagonal ink lines, from the gantry's L
#          bracket (36.8, 39) down and out to (28, 52): sprite median 6. Raised higher than the
#          crown's edge, chamfered all round (a lit rim), on a pal 6 slot.
#   outer  the plate below the hoop's mount on the cap flank (rows 46.4-52.6): sprite median 5.
CROWN_HEAD = [(43.6, 30.6), (38.0, 30.6), (34.5, 31.6), (32.0, 33.2), (30.6, 35.5), (29.8, 38.6), (31.2, 39.6),
              (33.4, 39.4), (35.8, 38.8), (36.8, 37.2), (43.6, 37.0)]
CROWN_TAIL = [(29.8, 38.4), (31.0, 38.6), (32.0, 40.6), (30.6, 42.8), (29.8, 44.8), (29.0, 44.8), (29.2, 41.4)]
WING_BAND = [(36.8, 39.2), (33.4, 40.4), (31.2, 42.8), (29.8, 45.4), (28.8, 48.5), (28.2, 51.8), (29.6, 51.8),
             (30.4, 48.8), (31.8, 46.6), (33.6, 44.8), (37.0, 43.8)]
WING_OUT = [(21.8, 46.4), (28.8, 46.4), (28.0, 51.8), (21.6, 52.6)]


def build_cowl(P):
    """The gull-wing cowl over the nose: a light crown crescent each side of the socket, a dark
    chevron band below it and a darker plate on the flank, separated by pal 6 slots; left built and
    mirrored."""
    def flat(poly, k):
        """Plate top: the dome surface flattened by k toward a level plane at the plate's highest
        point, so the plates stand out of the nose's forward slope as terraces whose tops face up
        (toward the game camera and its light) and whose fronts are risers."""
        zmax = max(surf_nt(x, y) for x, y in densify(poly, 0.5))
        return lambda x, y: (1 - k) * surf_nt(x, y) + k * zmax  # noqa: E731

    for m in (False, True):
        f = mir if m else (lambda p: p)
        for poly, k, z1, mat, top, ch, kw in (
                (CROWN_HEAD, 0.45, 1.0, "crown", "crown", 0.7, dict(rings=(0.88, 0.72, 0.54, 0.34, 0.16), bulge=1.5, step=0.6)),
                (CROWN_TAIL, 0.4, 1.3, "crown", "crown", 0.5, dict(bulge=0.6)),
                (WING_BAND, 0.7, 2.8, "cowlrim", "cowl", 1.0, {}),
                (WING_OUT, 0.6, 1.8, "cowlrim", "wingout", 0.7, {})):
            pp = f(poly)
            draped_plate(P, pp, -0.6, z1, S[mat], S[top], ch=ch, zf=flat(pp, k), zlo=surf_nt, **kw)
        # pal 6 slots under the gaps: along the upper ink line (crown | band) and the lower one
        # (band | outer plate)
        for a, b in (((37.2, 38.2), (29.2, 45.4)), ((29.4, 45.9), (28.3, 52.3))):
            if m:
                a, b = (mx(a[0]), a[1]), (mx(b[0]), b[1])
            gap_strip(P, a, b, 1.3, 0.55, S["cslot"])


# ---------------------------------------------------------------------------------------------
# Rotor blades (per frame), footprints = the sprite's blade pixels inside the ink (hulls)
# ---------------------------------------------------------------------------------------------
# Blade footprints: convex hulls of each blade's pixel squares in the sprite's inner mask (the white
# fins plus their shaded edge pixels; hoop, mast and dome pixels left out), per frame (fit round 1).
BLADES = {
    0: [
        [(35, 28), (32, 25), (32, 23), (34, 21), (38, 21), (40, 24), (41, 26), (41, 28), (38, 28), (38, 30), (37, 30), (36, 29), (36, 28)],
        [(56, 28), (56, 27), (62, 21), (63, 21), (66, 24), (66, 25), (65, 27), (64, 28), (62, 28), (62, 29), (60, 30), (59, 30), (59, 28)],
        [(27, 30), (31, 30), (32, 31), (32, 32), (31, 33), (29, 34), (28, 34), (27, 32)],
        [(68, 35), (65, 32), (65, 31), (68, 30), (70, 30), (71, 32), (71, 35), (71, 37), (69, 37), (69, 35)],
    ],
    1: [
        [(44, 19), (44, 28), (42, 28), (40, 26), (39, 22), (39, 19), (40, 18), (43, 18)],
        [(55, 25), (55, 21), (56, 20), (56, 18), (57, 18), (59, 19), (59, 20), (61, 20), (61, 23), (60, 25), (60, 26), (58, 28), (53, 28), (53, 25)],
        [(28, 29), (28, 28), (29, 26), (31, 24), (34, 24), (36, 27), (36, 30), (35, 31), (33, 32), (31, 32)],
        [(62, 29), (63, 28), (66, 26), (67, 26), (69, 28), (70, 30), (70, 32), (67, 33), (66, 33), (62, 31)],
    ],
}
BLADE_K = (4, 2.2)   # corners per blade, most area one dropped edge may add (px^2)
BLADE_IN = 0.25     # pulled in so the extended corners stay on the sprite


def inset(poly, d):
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    out = []
    for x, y in poly:
        L = math.hypot(x - cx, y - cy) or 1
        out.append((x - (x - cx) / L * d, y - (y - cy) / L * d))
    return out


def offset_in(poly, d):
    """Inward parallel offset of a convex, counter-clockwise polygon (edge lines shifted by d)."""
    n = len(poly)
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0) or 1
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        lines.append(((x0 + nx * d, y0 + ny * d), (x1 - x0, y1 - y0)))
    out = []
    for i in range(n):
        (p, r), (q, t) = lines[i - 1], lines[i]
        den = r[0] * t[1] - r[1] * t[0]
        if abs(den) < 1e-9:
            out.append(q)
            continue
        u = ((q[0] - p[0]) * t[1] - (q[1] - p[1]) * t[0]) / den
        out.append((p[0] + r[0] * u, p[1] + r[1] * u))
    return out


def clean_hull(poly, tol=0.02):
    """Drop collinear vertices and order the hull counter-clockwise."""
    pts = [(float(x), float(y)) for x, y in poly]
    if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) < 0:
        pts.reverse()
    out = []
    for i, p in enumerate(pts):
        a, b = pts[i - 1], pts[(i + 1) % len(pts)]
        if abs((p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0])) > tol:
            out.append(p)
    return out


def vane(P, poly, z0, z1, mat, ch=0.75):
    """A flat blade plate: vertical walls, a chamfer all round (uniform offset) and a flat top."""
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    ch = min(ch, 0.3 * min(max(xs) - min(xs), max(ys) - min(ys)))
    lo = [P.v((x, y, z0)) for x, y in poly]
    mid = [P.v((x, y, z1 - ch)) for x, y in poly]
    top_poly = offset_in(poly, ch)
    hi = [P.v((x, y, z1)) for x, y in top_poly]
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    away = (cx, cy, (z0 + z1) / 2)
    for i in range(n):
        j = (i + 1) % n
        P.f((lo[i], lo[j], mid[j], mid[i]), mat, away=away)
        P.f((mid[i], mid[j], hi[j], hi[i]), mat, away=away)
    P.f(tuple(hi), mat, out=(0, 0, 1))
    P.f(tuple(lo), mat, out=(0, 0, -1))


def fin_top(x, y):
    """Blade thickness (vertical): constant, so the blade's faces stay smooth."""
    return 0.9


PITCH = (3.0, 1.4)  # px the trailing edge stands above the disc at the blade's root and tip (twist)


def fin(P, poly, mat, ch=0.3):
    """A propeller blade on its footprint, lying in the tilted disc (disc_z): vertical walls up to a
    chamfer; pitched about its radial axis (the trailing edge raised), the pitch easing from the
    root to the tip (a twisted blade). Footprint = the sprite's blade pixels, so the plan is kept."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    ch = min(ch, 0.25 * min(max(xs) - min(xs), max(ys) - min(ys)))
    inner = offset_in(poly, ch)
    rx, ry = cx - HUB[0], cy - HUB[1]
    rl = math.hypot(rx, ry) or 1
    tx, ty = -ry / rl, rx / rl
    smax = max(abs((x - cx) * tx + (y - cy) * ty) for x, y in poly) or 1
    rads = [(x - HUB[0]) * rx / rl + (y - HUB[1]) * ry / rl for x, y in poly]
    r0, r1 = min(rads), max(rads)

    def zb(x, y):
        r = (x - HUB[0]) * rx / rl + (y - HUB[1]) * ry / rl
        k = min(1.0, max(0.0, (r - r0) / max(r1 - r0, 1e-3)))
        pitch = PITCH[0] + (PITCH[1] - PITCH[0]) * k
        return disc_z(y) + pitch * ((x - cx) * tx + (y - cy) * ty) / smax

    lo = [P.v((x, y, zb(x, y))) for x, y in poly]
    mid = [P.v((x, y, zb(x, y) + fin_top(x, y) - min(ch, 0.5 * fin_top(x, y)))) for x, y in poly]
    hi = [P.v((x, y, zb(x, y) + fin_top(x, y))) for x, y in inner]
    away = (cx, cy, zb(cx, cy) + 0.45)
    for i in range(n):
        j = (i + 1) % n
        P.f((lo[i], lo[j], mid[j], mid[i]), mat, away=away)
        P.f((mid[i], mid[j], hi[j], hi[i]), mat, away=away)
    # top and bottom: the (possibly concave) outline as one face each, triangulated by bmesh
    for ring, up in ((hi, 1.0), (lo, -1.0)):
        face = P.bm.faces.new(ring)
        face.material_index = mat
        face.normal_update()
        if face.normal.z * up < 0:
            face.normal_flip()
        bmesh.ops.triangulate(P.bm, faces=[face])
    # the root: the blade's shank back to the spinner, in the disc
    k_ = min(range(n), key=lambda i: rads[i])
    rx0 = HUB[0] + rx / rl * (r0 + 0.8)
    ry0 = HUB[1] + ry / rl * (r0 + 0.8)
    hub_c = Vector(HUB) + AXIS * 1.0
    a_ = Vector((rx0, ry0, zb(rx0, ry0) + 0.45))
    d_ = hub_c - a_
    e_ = a_ + d_ * max(0.0, 1 - 2.6 / max(d_.length, 1e-3))
    sweep(P, [(a_.x, a_.y, a_.z - 0.3, 0.3, 0.6), (e_.x, e_.y, e_.z, 0.3, 0.6)], S["spoke"], prof=box_prof(0.1))


def convex(pts):
    """Convex hull (monotone chain), counter-clockwise in x-right / y-down plan coordinates."""
    pts = sorted(set(pts))
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, hi = half(pts), half(pts[::-1])
    return lo[:-1] + hi[:-1]


def line_meet(a0, a1, b0, b1):
    rx, ry = a1[0] - a0[0], a1[1] - a0[1]
    tx, ty = b1[0] - b0[0], b1[1] - b0[1]
    den = rx * ty - ry * tx
    if abs(den) < 1e-9:
        return None
    u = ((b0[0] - a0[0]) * ty - (b0[1] - a0[1]) * tx) / den
    return (a0[0] + rx * u, a0[1] + ry * u)


def sharpen(poly, k=4, max_add=2.2):
    """Fewer, sharper corners (fix round 2): the pixel-stair hull read as a rounded lump. Repeatedly
    drop the edge whose removal (its two neighbour edges extended to meet) adds the least area,
    down to k corners, so the blade is the sprite's sharp-edged flat plate."""
    pts = list(poly)
    while len(pts) > k:
        n = len(pts)
        best = None
        for i in range(n):
            a, b, c, d = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
            q = line_meet(a, b, d, c)
            if q is None:
                continue
            add = abs((b[0] - q[0]) * (c[1] - q[1]) - (b[1] - q[1]) * (c[0] - q[0])) / 2
            # the meeting point must lie beyond the dropped edge (outside the convex polygon)
            if (q[0] - b[0]) * (b[0] - a[0]) + (q[1] - b[1]) * (b[1] - a[1]) < 0:
                continue
            if best is None or add < best[0]:
                best = (add, i, q)
        if best is None or best[0] > max_add:
            break
        _, i, q = best
        j = (i + 1) % n
        pts[i] = q
        del pts[j]
    return pts


# Hand-set sharp footprints where the hull would fill a notch the sprite keeps (frame, blade).
SHARP = {(1, 1): [(56.2, 17.6), (61.0, 20.0), (61.0, 25.0), (58.0, 28.0), (53.0, 28.0), (53.0, 25.2), (55.0, 23.6)]}


def build_blades(P, frame):
    for bi, poly in enumerate(BLADES[frame]):
        if (frame, bi) in SHARP:
            hp = clean_hull(SHARP[frame, bi])
        else:
            hp = clean_hull(convex([(float(x), float(y)) for x, y in poly]))
            hp = clean_hull(sharpen(hp, *BLADE_K))
        hp = offset_in(hp, BLADE_IN)
        hp = clip_reach(hp)
        blade(P, round_corners(hp))


def round_corners(poly, q=0.16, it=2, grow=1.04):
    """Chaikin corner cutting (q of each edge per side): the footprint's sharp corners become the
    blade's rounded tip and edges (a paddle-shaped blade, not a card)."""
    pts = list(poly)
    for _ in range(it):
        out = []
        for a, b in zip(pts, pts[1:] + pts[:1]):
            out.append((a[0] + (b[0] - a[0]) * q, a[1] + (b[1] - a[1]) * q))
            out.append((a[0] + (b[0] - a[0]) * (1 - q), a[1] + (b[1] - a[1]) * (1 - q)))
        pts = out
        q *= 0.6
    # grown back a little about the centre, so the rounded blade still covers the footprint's pixels
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    pts = [(cx + (x - cx) * grow, cy + (y - cy) * grow) for x, y in pts]
    return clean_hull(pts, tol=0.002)


# Fix round 6 (re-review: the blades read as loose cards). Every blade is now one airfoil blade of
# the same make, lying in the propeller disc (the plane through DISC_C normal to the thrust axis) and
# rooted on the hub: a thin lens section (rounded leading and trailing edges, flatter underside),
# twisted (pitch BL_PITCH root to tip), its root a round shank into the spinner. The plan of each
# blade's plate is still the sprite's blade footprint (the white diamonds, per frame); the blade
# runs on inward from the footprint's root end to the hub (under the hub housing or, for the low
# blades whose tips show beside the nose, inside the envelope), so all of them meet at the hub.
DISC_C = Vector(HUB) + AXIS * 1.0       # the disc's centre on the thrust axis (disc_z's plane)
NUP = -AXIS                              # the disc's upper (trailing) side
ZUP = Vector((0.0, 0.0, 1.0))
_E1 = Vector((1.0, 0.0, 0.0))
_E2 = AXIS.cross(_E1).normalized()       # in the disc, up the slope (north and up)
BL_TH = 0.55                             # blade half thickness (mid plate)
BL_PITCH = (7.0, 3.0)                    # blade angle to the disc, root to tip (degrees)
BL_REACH = 21.0                          # the blades stop inside the lower guard ring (plan |x - AX|)


def on_disc(x, y):
    return Vector((x, y, disc_z(y)))


def clip_reach(poly):
    """Clip a convex plan polygon to |x - AX| <= BL_REACH (the lower guard ring runs down the legs)."""
    out = poly
    for s in (1, -1):
        res = []
        n = len(out)
        for i in range(n):
            a, b = out[i], out[(i + 1) % n]
            ina, inb = s * (a[0] - AX) <= BL_REACH, s * (b[0] - AX) <= BL_REACH
            if ina:
                res.append(a)
            if ina != inb:
                xc = AX + s * BL_REACH
                t = (xc - a[0]) / (b[0] - a[0])
                res.append((xc, a[1] + (b[1] - a[1]) * t))
        out = res
    return out


def blade(P, hp):
    """One blade on the plan footprint hp (convex): its plate (a pillowed lens, twisted) on the
    disc and its root (shank and inner blade) from the footprint's inner end to the spinner."""
    C = DISC_C
    n_ = len(hp)
    cx = sum(p[0] for p in hp) / n_
    cy = sum(p[1] for p in hp) / n_
    cen = on_disc(cx, cy)
    d_hat = (cen - C)
    d_hat -= NUP * d_hat.dot(NUP)
    d_hat.normalize()
    t_hat = NUP.cross(d_hat).normalized()     # lateral, in the disc
    rads = [(on_disc(x, y) - C).length for x, y in hp]
    r_in, r_out = min(rads), max(rads)

    def pitch_off(p):
        r = (p - C).length
        k = min(1.0, max(0.0, (r - r_in) / max(r_out - r_in, 1e-3)))
        a = math.radians(BL_PITCH[0] + (BL_PITCH[1] - BL_PITCH[0]) * k)
        # (offsets go straight up, not along the disc normal, so the plan stays the footprint)
        return ZUP * ((p - cen).dot(t_hat) * math.tan(a) / NUP.z)

    def taper(p):
        r = (p - C).length
        return 1.0 - 0.45 * min(1.0, max(0.0, (r - r_in) / max(r_out - r_in, 1e-3)))

    # inset rings (plan), deepest limited by the footprint's in-radius
    def in_radius(poly):
        best = 1e9
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            L = math.hypot(x1 - x0, y1 - y0) or 1
            best = min(best, abs((x1 - x0) * (cy - y0) - (y1 - y0) * (cx - x0)) / L)
        return best
    ccw = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(hp, hp[1:] + hp[:1])) > 0
    base = hp if ccw else list(reversed(hp))
    dmax = min(1.3, 0.55 * in_radius(base))
    levels = [(0.0, 0.0), (0.3, 0.55), (0.65, 0.85), (1.0, 1.0)]
    rings_t, rings_b = [], []
    edge = None
    for fr, hk in levels:
        poly = base if fr == 0 else offset_in(base, dmax * fr)
        if fr > 0 and not (sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])) > 0):
            break
        top, bot = [], []
        for x, y in poly:
            p = on_disc(x, y)
            po = p + pitch_off(p)
            h = BL_TH * hk * taper(p)
            if fr == 0:
                v = P.v(tuple(po))
                top.append(v)
                bot.append(v)
            else:
                top.append(P.v(tuple(po + ZUP * (h / NUP.z))))
                bot.append(P.v(tuple(po - ZUP * (0.55 * h / NUP.z))))
        rings_t.append(top)
        rings_b.append(bot)
    mat = S["rotor"]
    for rings, sgn in ((rings_t, 1.0), (rings_b, -1.0)):
        o = tuple(NUP * sgn)
        for r0, r1 in zip(rings, rings[1:]):
            for i in range(len(r0)):
                j = (i + 1) % len(r0)
                P.f((r0[i], r0[j], r1[j], r1[i]), mat, out=o)
        last = rings[-1]
        cpt = sum((v.co for v in last), Vector()) / len(last)
        cv = P.v(tuple(cpt))
        for i in range(len(last)):
            P.f((last[i], last[(i + 1) % len(last)], cv), mat, out=o)
    # the root: from the footprint's inner end (its vertex nearest the hub, 0.7 px in) to the spinner
    # (the low tips beside the nose, whose plate starts far out, root from their lowest corner, so the
    # inner blade runs under the hub bar and the bow and not across the sprite's open gaps)
    if r_in > 10.0:
        k_ = max(range(n_), key=lambda i: hp[i][1])
    else:
        k_ = min(range(n_), key=lambda i: rads[i])
    rx, ry = hp[k_]
    L = math.hypot(cx - rx, cy - ry) or 1
    rx, ry = rx + (cx - rx) / L * 0.7, ry + (cy - ry) / L * 0.7
    root = on_disc(rx, ry)
    dr = root - C
    rl = dr.length
    u_ = dr / max(rl, 1e-3)
    st, ups = [], []
    r0_ = 2.2
    rs_ = [r0_ + (rl - r0_) * k / 6 for k in range(7)] if rl > r0_ + 0.5 else [r0_, r0_ + 0.5]
    for r in rs_:
        q = C + u_ * r
        hw = 0.55 + 0.5 * min(1.0, max(0.0, (r - 4.6) / 6.0))
        st.append((q.x, q.y, q.z, hw, 0.3))
        ups.append(tuple(NUP))
    shank = [s for s in st if (Vector(s[:3]) - C).length <= 4.7]
    rest = [s for s in st if (Vector(s[:3]) - C).length >= 4.5]
    if len(shank) >= 2:
        sweep(P, shank, S["spoke"], prof=round_prof(8), ups=ups[:len(shank)])
    if len(rest) >= 2:
        sweep(P, rest, S["rotor"], prof=round_prof(8), ups=ups[:len(rest)])


def build_lower_guard(P):
    """Fix round 6 (re-review: the guard was only an upper arch): the duct guard closes under the hub.
    From each leg of the ring at hub height the guard drops down the leg (in plan inside the leg's
    band) and curves in under the nose, below the envelope, to meet under the bow, where it rides on
    the belly (its strut). The blades' lower half lies inside the envelope's bow; the tips that show
    beside the nose turn inside this ring."""
    path = [(25.8, 28.4, ZC + 0.6), (25.8, 30.0, ZC - 3.2), (25.8, 32.5, ZC - 6.8), (25.9, 35.5, ZC - 9.8),
            (26.8, 38.8, ZC - 12.6), (30.0, 41.8, ZC - 14.4), (34.5, 44.0, ZC - 15.4), (41.0, 45.4, ZC - 15.8),
            (AX, 45.8, ZC - 15.9)]
    full = path + [(mx(x), y, z) for x, y, z in reversed(path[:-1])]
    st = [(x, y, z, 0.95, 0.95) for x, y, z in full]
    sweep(P, st, S["hoop"], prof=round_prof(12))
    # saddle where it rides on the belly
    zb = lower_z(AX, 45.8)
    block(P, AX - 2.2, AX + 2.2, 45.0, 46.6, ZC - 16.4, zb + 0.6, S["mount"], ch=0.3)


# ---------------------------------------------------------------------------------------------
# Outrigger arm (left; mirrored)
# ---------------------------------------------------------------------------------------------
ARM_DZ = ZC - 4.0   # the arms (built from z 0) lifted so the engine drum's axis is on the equator


def build_arm(P, side="L"):
    """One outrigger leg in left-side coordinates. The sprite's two legs differ in a few pixels (the
    right pipe sits a pixel further out and stops short of the flank, its strut is notched, its lower
    leg has no outer rail and a red end block): side "R" builds those, then the caller mirrors it."""
    R8, R12 = round_prof(8), round_prof(12)
    right = side == "R"
    # red pipe out of the flank, bending down to the elbow
    if right:
        pipe = [(21.5, 47.0, 4.2, 0.8, 0.9), (17.95, 47.0, 5.0, 1.0, 1.25), (14.8, 47.0, 5.0, 1.0, 1.25), (13.5, 47.3, 5.0, 0.85, 1.25),
                (12.5, 48.0, 4.9, 0.75, 1.25), (11.6, 48.9, 4.8, 0.75, 1.2), (11.0, 50.0, 4.7, 0.9, 1.2),
                (10.9, 51.0, 4.6, 1.0, 1.2)]
    else:
        pipe = [(23.5, 47.0, 5.0, 1.0, 1.25), (14.8, 47.0, 5.0, 1.0, 1.25), (13.5, 47.3, 5.0, 0.85, 1.25),
                (12.5, 48.0, 4.9, 0.75, 1.25), (11.6, 48.9, 4.8, 0.75, 1.2), (11.0, 50.0, 4.7, 0.9, 1.2),
                (10.9, 51.0, 4.6, 1.0, 1.2)]
    sweep(P, pipe, S["pipe"], prof=box_prof(0.38))
    # chunky red collar where the pipe leaves the flank, and a band at the bend
    if not right:
        block(P, 19.0, 20.6, 46.0, 48.7, 2.6, 7.0, S["strut_red"], ch=0.4)
    else:
        block(P, 19.0, 20.6, 47.95, 48.95, 0.0, 3.0, S["elbow"], ch=0.3)
    block(P, 14.6, 15.6, 46.05, 47.95, 3.5, 6.5, S["strut_red"], ch=0.3)
    # elbow block and its step to the dome
    block(P, 7.0, 13.6, 50.9, 54.3, 0.0, 5.0, S["elbow"], ch=0.6)
    block(P, 8.7, 12.0, 50.0, 51.4, 0.0, 4.6, S["elbow"], ch=0.4)
    block(P, 12.4, 15.4, 52.9, 54.5, 0.0, 3.2, S["elbow"], ch=0.4)
    # grey strut (notched on the right) and the red strut to the dome
    if right:
        block(P, 9.8, 19.5, 54.1, 57.9, 1.0, 4.2, S["strut"], ch=0.5)
        block(P, 9.8, 14.95, 57.5, 58.8, 1.0, 4.2, S["strut"], ch=0.4)
        block(P, 16.05, 19.5, 57.5, 58.8, 1.0, 3.6, S["strut"], ch=0.4)
        sweep(P, [(9.2, 59.5, 2.8, 0.75, 1.0), (14.0, 59.5, 2.8, 0.75, 1.0)], S["strut_red"], prof=R8)
        block(P, 10.9, 14.95, 59.9, 60.95, 0.0, 2.6, S["strut_red"], ch=0.3)
    else:
        block(P, 9.8, 19.5, 54.1, 58.8, 1.0, 4.2, S["strut"], ch=0.5)
        sweep(P, [(9.2, 59.5, 2.8, 0.75, 1.0), (19.0, 59.5, 2.8, 0.75, 1.0)], S["strut_red"], prof=R8)
        block(P, 9.5, 13.95, 59.6, 60.95, 0.0, 2.6, S["strut_red"], ch=0.3)
        block(P, 9.5, 10.95, 60.9, 61.95, 0.0, 2.4, S["strut_red"], ch=0.25)
    # drum housing: a horizontal cylinder along y on a base
    block(P, 3.0, 10.0, 54.9, 61.0 if right else 61.8, 0.0, 2.5, S["drum"], ch=0.4)
    if right:
        block(P, 4.0, 10.0, 60.8, 61.8, 0.0, 2.5, S["drum"], ch=0.3)
    block(P, 6.0, 10.0, 54.15, 55.3, 0.0, 2.4, S["drum"], ch=0.3)
    sweep(P, [(6.5, 54.75, 3.9, 0.0, 0.0), (6.5, 55.05, 3.9, 2.8, 2.5), (6.5, 55.6, 3.9, 3.45, 3.25),
              (6.5, 61.1, 3.9, 3.45, 3.25), (6.5, 61.65, 3.9, 2.8, 2.5), (6.5, 61.95, 3.9, 0.0, 0.0)],
          S["drum"], prof=R12)
    for y in (56.6, 60.0):
        sweep(P, [(6.5, y - 0.3, 3.9, 3.6, 3.4), (6.5, y + 0.3, 3.9, 3.6, 3.4)], S["strut_red"], prof=R12)
    # leg frame (a pixel-deep notch beside the ram at rows 71-72)
    block(P, 3.0, 10.0, 61.8, 65.0, 0.0, 3.4, S["frame"], ch=0.5)
    block(P, 3.0, 9.2, 64.8, 67.2, 0.0, 3.4, S["frame"], ch=0.5)
    block(P, 2.0, 10.6, 67.0, 69.2, 0.0, 3.8, S["frame"], ch=0.5)
    block(P, 2.0 if right else 1.2, 7.0, 69.0, 75.0, 0.0, 3.6, S["frame"], ch=0.5)
    if right:
        block(P, 6.8, 9.0, 69.0, 75.0, 0.0, 3.6, S["frame"], ch=0.4)
    else:
        block(P, 6.8, 9.0, 69.0, 71.0, 0.0, 3.6, S["frame"], ch=0.4)
        block(P, 6.8, 8.0, 71.95, 75.0, 0.0, 3.6, S["frame"], ch=0.3)
        block(P, 7.8, 9.0, 72.9, 75.0, 0.0, 3.6, S["frame"], ch=0.3)
    block(P, 7.6, 10.4, 67.6, 70.4, 3.6, 4.3, S["strut"], ch=0.3)  # light block on the frame
    if right:
        block(P, 1.0, 3.9, 69.95, 76.95, 0.0, 2.3, S["frame"], ch=0.4)  # outer rail, short
        block(P, 1.6, 3.9, 76.8, 78.1, 0.0, 2.3, S["frame"], ch=0.3)
        block(P, 1.0, 3.9, 77.95, 80.0, 0.0, 2.3, S["frame"], ch=0.4)
        sweep(P, [(1.6, 76.9, 2.3, 0.55, 0.6), (1.6, 81.9, 2.3, 0.55, 0.6)], S["rod"], prof=R8)
    else:
        block(P, 1.0, 3.5, 68.5, 88.0, 0.0, 2.3, S["frame"], ch=0.4)  # outer rail
    # red ram down the frame and the outer bar
    sweep(P, [(5.5, 62.0, 4.0, 1.4, 1.35), (5.5, 70.9, 4.0, 1.4, 1.35)], S["ram"], prof=R8)
    sweep(P, [(10.0, 68.9, 2.7, 1.0, 1.0), (10.0, 78.9, 2.7, 1.0, 1.0)], S["ram"], prof=R8)
    block(P, 8.0, 10.0, 78.4, 79.95, 0.0, 2.4, S["frame"], ch=0.3)
    block(P, 8.0, 8.95, 79.9, 81.95, 0.0, 2.4, S["frame"], ch=0.25)
    # knee and piston
    sweep(P, [(6.0, 74.6, 3.0, 0.0, 0.0), (6.0, 74.95, 3.0, 2.4, 2.3), (6.0, 75.5, 3.0, 2.95, 2.85),
              (6.0, 78.3, 3.0, 2.95, 2.85), (6.0, 78.9, 3.0, 2.4, 2.3)], S["knee"], prof=R12, cap0=False)
    sweep(P, [(6.0, 78.6, 2.6, 2.0, 2.0), (6.0, 88.2, 2.6, 2.0, 2.0)], S["piston"], prof=R12)
    sweep(P, [(6.0, 81.0, 2.6, 2.15, 2.15), (6.0, 81.6, 2.6, 2.15, 2.15)], S["frame"], prof=R12)  # gland
    if right:
        block(P, 1.9, 8.0, 86.9, 89.0, 0.0, 3.2, S["rod"], ch=0.45)  # red end block
        block(P, 1.9, 4.0, 88.8, 90.0, 0.0, 3.0, S["frame"], ch=0.4)
        block(P, 1.9, 4.7, 89.9, 91.0, 0.0, 3.0, S["frame"], ch=0.4)
        block(P, 6.6, 8.0, 88.8, 91.0, 0.0, 3.0, S["frame"], ch=0.35)
    else:
        block(P, 1.6, 8.0, 87.8, 91.0, 0.0, 3.0, S["frame"], ch=0.5)  # piston end block
    block(P, 1.6, 7.0, 90.8, 92.0, 0.0, 2.8, S["frame"], ch=0.4)
    block(P, 2.7, 6.0, 91.8, 92.6, 0.0, 2.6, S["frame"], ch=0.3)
    # red rod to the foot
    sweep(P, [(2.6, 86.8, 2.2, 0.75, 0.9), (2.7, 90.4, 2.2, 0.75, 0.9), (3.9, 91.6, 2.1, 0.9, 0.95),
              (5.0, 92.6, 2.0, 1.0, 1.0), (5.0, 99.5, 2.0, 1.0, 1.0)], S["rod"], prof=R8)
    block(P, 3.0, 4.3, 97.9, 99.4, 0.0, 2.6, S["rod"], ch=0.3)
    # Fix round 5: an ENGINE POD. The arm's hardware (frame plates, ram, knee, piston) is mounted on
    # top of a streamlined nacelle that hangs under it, below the envelope's equator: a round body
    # from the intake under the drum (row 55) back to the exhaust nozzle under the end block (row
    # 90), inside the arm's plan, so the top view keeps the sprite's hardware. At its front a red
    # intake lip, a dark intake face and a spinner (the fan); at its back a dark nozzle ring with the
    # exhaust glow in it. The rod and foot behind carry a small tail pod with the orange lamp.
    zn = -2.0
    R16 = round_prof(16)
    sweep(P, [(6.2, 55.0, zn, 3.0, 3.1), (6.2, 56.2, zn, 3.4, 3.6), (6.1, 61.0, zn, 3.5, 3.8),
              (6.1, 68.0, zn, 3.5, 3.8), (5.9, 78.0, zn, 3.3, 3.5), (5.6, 85.0, zn, 2.95, 3.0),
              (5.4, 89.0, zn, 2.45, 2.45), (5.4, 90.0, zn, 2.3, 2.25)], S["nacelle"], prof=R16)
    # intake: lip ring, dark face, spinner
    sweep(P, [(6.2, 54.8, zn, 3.05, 3.15), (6.2, 55.4, zn, 3.3, 3.45)], S["strut_red"], prof=R16)
    sweep(P, [(6.2, 54.62, zn, 2.45, 2.55), (6.2, 54.9, zn, 2.45, 2.55)], S["intake"], prof=R16)
    sweep(P, [(6.2, 54.7, zn, 1.15, 1.15), (6.2, 54.45, zn, 0.75, 0.75), (6.2, 54.3, zn, 0.0, 0.0)], S["pylon"],
          prof=round_prof(12), cap1=False)
    # exhaust: nozzle ring and the glow inside it
    sweep(P, [(5.4, 89.8, zn, 2.4, 2.3), (5.4, 90.6, zn, 2.05, 1.95)], S["head"], prof=R16)
    sweep(P, [(5.4, 90.5, zn, 1.55, 1.45), (5.4, 90.75, zn, 1.55, 1.45)], S["lamp"], prof=R16)
    # the tail pod under the foot
    sweep(P, [(3.6, 98.9, 0.5, 0.0, 0.0), (3.6, 99.6, 0.5, 1.7, 1.6), (3.6, 103.0, 0.5, 2.0, 1.8),
              (3.6, 105.2, 0.8, 1.35, 1.3), (3.6, 105.7, 0.9, 0.0, 0.0)], S["nacelle"], prof=R16)
    # foot pad, hood and lamp
    if right:
        foot = [(2.0, 99.2), (6.0, 99.2), (6.0, 104.0), (2.4, 104.0), (1.0, 102.4), (1.0, 100.0)]
    else:
        foot = [(2.0, 99.2), (6.0, 99.2), (6.0, 104.0), (1.0, 104.0), (1.0, 100.0)]
    prism(P, foot, 0.0, 3.4, S["foot"], ch=0.55)
    prism(P, [(1.0, 103.8), (6.0, 103.8), (6.0, 105.9), (2.1, 105.95), (1.0, 104.8)], 0.0, 2.3, S["rod"], ch=0.35)
    block(P, 1.9, 5.4, 104.2, 105.9, 1.7, 2.6, S["lamp"], ch=0.25)


# ---------------------------------------------------------------------------------------------
# Build, bake, split, export
# ---------------------------------------------------------------------------------------------
def build_body(coll, mats):
    P = Part(f"{NAME}_dome")
    build_dome(P)
    build_dome_detail(P)
    build_hoop(P)
    build_lower_guard(P)
    build_mast(P)
    build_gantry(P)
    build_cowl(P)
    dome = finish(P, mats, coll)
    A = Part(f"{NAME}_armL")
    build_arm(A, "L")
    bmesh.ops.translate(A.bm, vec=(0, 0, ARM_DZ), verts=A.bm.verts)  # the pods hang at the equator
    build_mounts(A)
    arm_l = finish(A, mats, coll)
    B = Part(f"{NAME}_armR")
    build_arm(B, "R")
    bmesh.ops.translate(B.bm, vec=(0, 0, ARM_DZ), verts=B.bm.verts)
    build_mounts(B)
    mirror_only(B)
    arm_r = finish(B, mats, coll, oriented=True)
    return [dome, arm_l, arm_r]


def build_rotor(coll, mats, frame):
    B = Part(f"{NAME}_rotor{frame}")
    build_blades(B, frame)
    return finish(B, mats, coll, smooth_angle=30.0)  # twisted blades: smooth faces, crisp edges


def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def copy_obj(o, name, coll):
    c = o.copy()
    c.data = o.data.copy()
    c.name = name
    c.modifiers.clear()
    coll.objects.link(c)
    return c


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


def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT = (0.97, 0.985, 1.0)
    T.TEXTURED = tuple(i for i in range(len(SLOTS)) if i not in UNBAKED)
    try:
        T.bake_maps(obj, out_dir, size=512, samples=48)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "nshi115")


TAIL_DOME_PAD = 3.0   # px past the last row: the closing dome of the tail cut (fix round 6)


def split_open(obj, layout, coll, suffix):
    """Cut the outline shell per piece without capping (as newsh2-115): capped cuts get outlined.
    Fix round 2: each piece keeps the WHOLE shell's vertex normals (custom normals), so the
    outline's hull, pushed out along them, runs on across the cut instead of each piece bending
    its edge its own way."""
    from mathutils.kdtree import KDTree
    full = obj.data.copy()
    full.transform(obj.matrix_world)
    kd = KDTree(len(full.vertices))
    for v in full.vertices:
        kd.insert(v.co, v.index)
    kd.balance()
    nrm = [v.normal.copy() for v in full.vertices]
    edges = [(e.vertices[0], e.vertices[1]) for e in full.edges]
    out = {}
    cy_last = max(cy for _, _, cy in layout)
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hb = (14 + (TAIL_DOME_PAD if cy == cy_last else 0.0)) / 12   # the tail dome stays on the last row
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - hb, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        # the normal each vertex had in the whole shell (a cut vertex: blended from its two ends)
        vn = []
        for v in bm.verts:
            (c0, i0, d0), = kd.find_n(v.co, 1)
            if d0 < 1e-6:
                vn.append(nrm[i0])
                continue
            best = None
            for c1, i1, d1 in kd.find_n(v.co, 8):
                for c2, i2, d2 in kd.find_n(v.co, 8):
                    if i2 <= i1:
                        continue
                    a, b = full.vertices[i1].co, full.vertices[i2].co
                    ab = b - a
                    L2 = ab.length_squared
                    if L2 < 1e-12:
                        continue
                    t = max(0.0, min(1.0, (v.co - a).dot(ab) / L2))
                    e = (a + ab * t - v.co).length
                    if best is None or e < best[0]:
                        best = (e, i1, i2, t)
            if best is None or best[0] > 1e-4:
                vn.append(nrm[i0])
            else:
                _, i1, i2, t = best
                vn.append((nrm[i1] * (1 - t) + nrm[i2] * t).normalized())
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        me.shade_smooth()
        if len(me.vertices):
            me.normals_split_custom_set_from_vertices(vn)
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    bpy.data.meshes.remove(full)
    return out


def split_body(obj, layout, coll, pad=0.15):
    """common.split_assembly with each piece's box `pad` px wider (fix round 2): adjacent pieces
    overlap a hair, so the game's per-piece transforms leave no raster crack at a cut through
    which the outline shell's black inside showed (the x = 24 cut down the dome's left rib, where
    the cap could not be filled)."""
    result = {}
    hw, hh = (12 + pad) / 12, (14 + pad) / 12
    cy_last = max(cy for _, _, cy in layout)
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hb = hh + (TAIL_DOME_PAD / 12 if cy == cy_last else 0.0)   # the tail dome stays on the last row
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hb, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
            edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if edges:
                bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for mat in obj.data.materials:
            mesh.materials.append(mat)
        piece = bpy.data.objects.new(name, mesh)
        coll.objects.link(piece)
        result[name] = piece
    return result


def _islands(bm):
    seen, islands = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        stack, isl = [v], []
        seen.add(v)
        while stack:
            x = stack.pop()
            isl.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        islands.append(isl)
    return islands


def _inside(bvh, p):
    """Ray parity against a closed surface (a slanted ray, so it never runs along a face)."""
    d = Vector((0.0123, 0.0371, 1.0)).normalized()
    o, n = p.copy(), 0
    for _ in range(64):
        hit = bvh.ray_cast(o, d)
        if hit[0] is None:
            break
        n += 1
        o = hit[0] + d * 1e-5
    return n % 2 == 1


def shell_mesh(src, coll, voxel=0.035, faces=3200, smooth=24, inside=0.03, target_voxel=0.012):
    """common.outline_shell (D51), rebuilt for fix round 2 (should be shared):
    - held inside a CLEAN target: Shrinkwrap's inside mode trusts the nearest face's normal, and on
      the raw model (overlapping plates, faces inside other parts) it read the outside of the left
      arm and the hoop crown as inside, so the shell stood out there; the target is now a fine voxel
      remesh of the model (one closed surface, normals out);
    - decimated with mirror symmetry about the sprite's axis (x = 48.5 px), so the ink is the same
      on both sides."""
    ax = (AX - 48) * PX

    def remeshed(name, vox):
        me = src.data.copy()
        me.materials.clear()
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        o.matrix_world = src.matrix_world.copy()
        rm = o.modifiers.new("remesh", "REMESH")
        rm.mode = "VOXEL"
        rm.voxel_size = vox
        rm.adaptivity = 0.0
        common._apply_modifiers(o)
        return o

    target = remeshed(f"{src.name}_target", target_voxel)
    # the target keeps its outer surfaces only: a voxel remesh also closes hollows inside the model
    # (a surface facing into the solid), and the nearest-face test then read the solid as outside
    tb = bmesh.new()
    tb.from_mesh(target.data)
    cavity = []
    for isl in _islands(tb):
        vol = 0.0
        for f_ in {f for v in isl for f in v.link_faces}:
            vs = [v.co for v in f_.verts]
            for k in range(1, len(vs) - 1):
                vol += vs[0].dot(vs[k].cross(vs[k + 1])) / 6
        if vol <= 0:
            cavity += isl
    bmesh.ops.delete(tb, geom=cavity, context="VERTS")
    tb.to_mesh(target.data)
    tb.free()
    shell = remeshed(f"{src.name}_outline", voxel)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    islands = _islands(bm)

    def extent(isl):
        xs = [v.co.x for v in isl]
        ys = [v.co.y for v in isl]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))

    keep = {v.index for v in max(islands, key=extent)}
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    bmesh.ops.translate(bm, vec=(-ax, 0, 0), verts=bm.verts)  # mirror axis at the object origin
    bm.to_mesh(shell.data)
    bm.free()
    shell.location.x += ax
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
        dec.use_symmetry = True
        dec.symmetry_axis = "X"
    common._apply_modifiers(shell)
    shell.data.transform(shell.matrix_world)
    shell.matrix_world = Matrix.Identity(4)
    # held inside (D88): every vertex outside the target (ray parity: the nearest face's normal is
    # no guide at the target's edges and in pockets, where smoothing bridges the creases), or nearer
    # it than half `inside`, goes `inside` under the nearest surface point; a few passes, as a move
    # can change the nearest point (Shrinkwrap's inside mode left a third of them out)
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(target, bpy.context.evaluated_depsgraph_get())
    me = shell.data
    before = [f.normal.copy() for f in me.polygons]

    def pull():
        for _ in range(6):
            moved = 0
            for v in me.vertices:
                loc, nor, _i, d = bvh.find_nearest(v.co)
                if loc is None:
                    continue
                ins = _inside(bvh, v.co)
                if ins and d >= 0.5 * inside:
                    continue
                if d > 1e-6:
                    into = (loc - v.co).normalized() if not ins else (v.co - loc).normalized()
                else:
                    into = -nor
                q = loc + into * inside
                if not _inside(bvh, q):
                    q = loc - nor * inside
                v.co = q
                moved += 1
            if not moved:
                break

    def flipped():
        me.update()
        return [f for f in me.polygons if f.normal.dot(before[f.index]) < 0.0]

    # a pull can turn a face over where the shell bridges a pocket: turned over, it faces away from
    # the camera and the outline pass draws it as a stray black line across the plating. Relax
    # those faces' corners toward their neighbours and pull again, until none is turned.
    nbr = {v.index: set() for v in me.vertices}
    for e in me.edges:
        a, b = e.vertices
        nbr[a].add(b)
        nbr[b].add(a)
    hist = []
    for _ in range(5):
        pull()
        bad = flipped()
        hist.append(len(bad))
        if not bad:
            break
        vs = {k for f in bad for k in f.vertices}
        vs |= {n for k in list(vs) for n in nbr[k]}
        for _r in range(3):
            new = {k: sum((me.vertices[n].co for n in nbr[k]), Vector()) / len(nbr[k]) for k in vs if nbr[k]}
            for k, c in new.items():
                me.vertices[k].co = me.vertices[k].co.lerp(c, 0.7)
    else:
        pull()
        hist.append(len(flipped()))
    # the few still turned (thin plates, deep pockets) go: a small hole in the shell is under the
    # opaque plating, a turned face over it would be ink
    dead = {f.index for f in flipped()}
    if dead:
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[k] for k in dead], context="FACES_ONLY")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.to_mesh(me)
        bm.free()
    shell["flipped"] = hist
    shell.data.shade_smooth()
    return shell, target


def prune_stray_ink(shell, visible, passes=3):
    """Delete the shell faces the game camera could see from behind (fix round 2). The outline pass
    draws only the shell's back faces, so one that faces away from a camera yet is not hidden by the
    model (the shell bridging a pocket between the gantry and the dome, a fold the smoothing left)
    is a stray black line across the plating. Cameras: overhead and up to 45 deg from it, all
    round. A hole left there is under the plating; the silhouette's ink is drawn by back faces the
    model itself hides, so it is untouched."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(visible, dg)
    dirs = [Vector((0.0, 0.0, 1.0))]
    for el in (15, 30, 45):
        for k in range(12):
            a = math.radians(30 * k)
            e = math.radians(el)
            dirs.append(Vector((math.sin(e) * math.cos(a), math.sin(e) * math.sin(a), math.cos(e))))
    removed = 0
    for _ in range(passes):
        me = shell.data
        dead = set()
        for f in me.polygons:
            c, n = f.center, f.normal
            for d in dirs:
                if n.dot(d) < -0.05 and bvh.ray_cast(c + d * 1e-4, d)[0] is None:
                    dead.add(f.index)
                    break
        if not dead:
            break
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[k] for k in dead], context="FACES_ONLY")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.to_mesh(me)
        bm.free()
        removed += len(dead)
    return removed


def shell_outside(shell, target, tol=0.01):
    """Shell vertices outside the target (ray parity) or within tol of its surface (left, right of
    the axis)."""
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(target, bpy.context.evaluated_depsgraph_get())
    ax = (AX - 48) * PX
    left = right = 0
    for v in shell.data.vertices:
        loc, _n, _i, d = bvh.find_nearest(v.co)
        if loc is None:
            continue
        if not _inside(bvh, v.co) or d < tol:
            if v.co.x < ax:
                left += 1
            else:
                right += 1
    return left, right


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_path = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    parts = build_body(coll, mats)
    body = join(parts, f"{NAME}_body")
    # the outline shell is made from the model BEFORE its hidden faces go (fix round 2): culled, the
    # parts are open, and the voxel remesh wrapped them as a thin double skin (its inner layer, black
    # in the outline pass, showed through any crack between the pieces)
    solid = copy_obj(body, f"{NAME}_solid", coll)
    T.cull_hidden(body)
    rotors = {f: build_rotor(coll, mats, f) for f in (0, 1)}
    stats = {"body_tris": tri_count(body), "rotor_tris": {f: tri_count(r) for f, r in rotors.items()}}
    print(f"{NAME} A: body {stats['body_tris']} tris, rotor {stats['rotor_tris']}")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake(body, tempfile.mkdtemp(prefix="nshi115a_bake_"))
        fmt = "WEBP"
    layout = [(e["model"], e["cx"] - SX0 - W_PX // 2, e["cy"] - SY0 - H_PX // 2) for e in sprite["assemblyLayout"]]
    names = [n for n, _, _ in layout]
    # Outline shells (D51), one per frame (the blades move), made after the bake.
    shells = {}
    for f in (0, 1):
        tmp = join([copy_obj(solid, f"_sb{f}", coll), copy_obj(rotors[f], f"_sr{f}", coll)], f"_shellsrc{f}")
        sh, tgt = shell_mesh(tmp, coll)  # D88: held inside (a clean target), symmetric
        sh.hide_render = True
        vis = join([copy_obj(body, f"_vb{f}", coll), copy_obj(rotors[f], f"_vr{f}", coll)], f"_visible{f}")
        stats[f"shell_pruned_{f}"] = prune_stray_ink(sh, vis)
        bpy.data.objects.remove(vis, do_unlink=True)
        stats[f"shell_outside_{f}"] = shell_outside(sh, tgt)
        stats[f"shell_flipped_{f}"] = list(sh["flipped"])
        shells[f] = split_open(sh, layout, coll, f"_outline{f}")
        stats[f"shell_tris_{f}"] = tri_count(sh)
        for o_ in (tmp, sh, tgt):
            bpy.data.objects.remove(o_, do_unlink=True)
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    body.modifiers.clear()
    bpieces = split_body(body, layout, coll)
    for n_, o_ in bpieces.items():
        o_.name = f"_bp_{n_}"
    rpieces = {f: split_body(rotors[f], layout, coll) for f in (0, 1)}
    for f in (0, 1):
        for n_, o_ in rpieces[f].items():
            o_.name = f"_rp{f}_{n_}"
    where = {name: (cx / 12, -cy / 12) for name, cx, cy in layout}
    export = []
    game = {}
    frame2 = bpy.data.objects.new("frame2", None)
    coll.objects.link(frame2)
    stats["pieces"] = {}
    for f in (0, 1):
        for name in names:
            if f == 1 and name not in ANIMATED:
                continue
            tag = name if f == 0 else f"{name}-f2"
            b = copy_obj(bpieces[name], f"_b_{tag}", coll)
            r = rpieces[f][name]
            objs = [b]
            if r.data.polygons:
                objs.append(copy_obj(r, f"_r_{tag}", coll))
            piece = join(objs, tag) if len(objs) > 1 else b
            piece.name = tag
            wn = piece.modifiers.new("weighted", "WEIGHTED_NORMAL")
            wn.keep_sharp = True
            wn.weight = 50
            s = shells[f][name]
            s.name = f"{tag}_outline"
            s.data.materials.clear()
            s.data.materials.append(outline_mat)
            s["tyrian_outline"] = True
            for o in (piece, s):
                o.location = (*where[name], 0.0)
                if f == 1:
                    o.parent = frame2
                    o["tyrian_frame2"] = True
            export += [piece, s]
            game[tag] = [piece, s]
            stats["pieces"][tag] = tri_count(piece)
    export.append(frame2)
    stats["total_tris_f1"] = sum(v for k, v in stats["pieces"].items() if not k.endswith("-f2"))
    if out_path:
        common.export_glb(export, out_path, image_format=fmt)
    # ---- the game contract: one glb per piece (and per -f2 piece), as the old script did ----
    for o in export:
        if o.type == "MESH":
            o.parent = None
            o.location = (0.0, 0.0, 0.0)
            o.pop("tyrian_frame2", None)
    for name in names:
        sprites = common.load_sprite(ROOT, name)["sprites"]
        if name in ANIMATED:
            first, second = (dict(s_, frames=[s_["frames"][i]]) for s_ in sprites[:1] for i in (0, 1))
            common.export_sprite_model(ROOT, game[name], f"enemies/{name}", [first], image_format=fmt)
            common.export_sprite_model(ROOT, game[f"{name}-f2"], f"enemies/{name}-f2", [second], image_format=fmt)
        else:
            common.export_sprite_model(ROOT, game[name], f"enemies/{name}", sprites, image_format=fmt)
    print(f"{NAME}: exported {out_path}; {json.dumps(stats)}")
    if "--stats" in argv:
        Path(argv[argv.index("--stats") + 1]).write_text(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
