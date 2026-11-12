"""assembly-newshg-203: a fixed jungle rocket-launcher emplacement (newshg-165 | newshg-167
over newshg-203 | newshg-205, 48 x 56 px).

WHAT IT IS: a fixed emplacement (types 768/770/771, mv 0, armor 40, launch freq 70, ani9 glows only)
standing on the HD jungle floor; the sprite's floor pixels are NOT modelled (D130). Read as one
machine:
  * a squat PIVOT POST (glowing red vent slit along its sloped top) carries a trunnion hub;
  * a box-section BOOM climbs from the hub north-east to the breech of
  * a big grey ROCKET POD (chamfered box section, dark armour panels on its crown, a red slit
    across them, three side lamps, a bright breech collar), raised high and pitched up (D82
    reading: the launcher drawn rising up the screen is an elevated, inclined tube), ending in a
    chamfered cap with a glowing red muzzle rim and four launch bores;
  * an ELEVATION HOUSING (chamfered box, ribs on its top) beside the post, with a hydraulic ram up
    to the boom's belly;
  * an OUTRIGGER strut along the boom's west flank that bends down to a ground foot, with a prong.
The launcher's flame (newshg-167 frames 243 / 283) is two separate emissive objects (frame_part).

Coordinates: sprite px, x = column (east), y = row (south), z up. Along the launcher: S = x - y
(toward the muzzle), T = x + y (across; 1 px across = sqrt 2 in T). Blender: X = (x - 24) / 12,
Y = (28 - y) / 12, Z = z / 12 (assembly centre = origin, as common.split_assembly expects).

Exports the four pieces (split_assembly) as enemies/newshg-165, -167 (one model per flame frame), -203, -205.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshg-203.py
(design check, scratch only: blender --background --python <this> -- --measure --render)
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b124 as lib  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "assembly-newshg-203"
ROOT = common.repo_root(__file__)
PIECES = ["newshg-165", "newshg-167", "newshg-203", "newshg-205"]
# Assembly pixel (0, 0) is the top-left corner of newshg-165; layout centres relative to the origin.
CX0, CY0 = 92, -4
R2 = math.sqrt(2)
U = 1 / 12
SPRITE = lib.merged_sprite(ROOT, PIECES)
# Design-time measurement (top view vs the sprite masks) only with --measure and the scratch masks.
SCRATCH = Path("/Users/dlomibao/projects/tyrian-scratch/e2-enemies-1/assembly-newshg-203")
SD = None
if (SCRATCH / "sprite_data.js").exists() and "--measure" in sys.argv:
    _js = (SCRATCH / "sprite_data.js").read_text()
    SD = json.loads(_js[_js.index("=") + 1:].rstrip().rstrip(";"))

# Muzzle flame plans (S along the launcher, T across) for newshg-167's short (1) and long (2) flames.
FLAME_STATES = {
    1: [[18, 46.6, 53.4], [20, 46.6, 54], [21, 46.6, 54.6], [25, 46.8, 54.6], [27, 47.4, 53.3], [29, 48.6, 52.6],
        [31, 49.2, 52.2], [33, 50.6, 51.8]],
    2: [[18, 46, 54.2], [20, 44.4, 54.6], [26, 44.4, 56.6], [28, 45.6, 56.6], [30, 46, 55], [31, 46.4, 54.6],
        [33, 46.8, 53.6], [38, 47.4, 53.6], [41, 48.6, 51.6], [43, 48.4, 51.6], [46, 48.6, 50.8]],
}


# ---- the launcher line -----------------------------------------------------------------------------
def P(S, Tc, h):
    return ((S + Tc) / 2, (Tc - S) / 2, h)


AXD = Vector(P(1, 0, 0)) - Vector(P(0, 0, 0))   # unit S step in xy (length 1/sqrt2)
# Pod: axis height climbs from the breech to the muzzle.
S_BR, S_CAP, S_MZ = -13.6, 13.3, 21.0
H_BR, H_MZ = 9.5, 15.5
KP = (H_MZ - H_BR) / (S_MZ - S_BR)


def pod_h(S):
    return H_BR + (S - S_BR) * KP


# plan edges of the pod (T at the upper-left and lower-right edges), from the inner mask
T0f = T.pchip([-14.0, 9.5, 11.0, 13.0, 14.0, 16.0, 17.0, 18.0, 20.0, 21.3],
               [43.55, 43.55, 44.5, 44.8, 45.8, 46.4, 47.0, 47.6, 47.8, 48.5])
T1f = T.pchip([-14.0, -12.6, -11.0, -9.4, 13.3, 14.0, 15.0, 16.0, 17.0, 18.0, 20.0, 21.3],
              [53.6, 54.6, 56.6, 58.45, 58.45, 57.6, 56.6, 55.6, 54.6, 53.9, 53.6, 53.4])


def pod_surface(S, Tc, cl=1.3):
    """Height of the pod's top at (S, T): the crown, or the upper-left 45-degree chamfer."""
    ht = pod_h(S) + HDf(S)
    edge = T0f(S) + cl * R2
    return ht - max(0.0, (edge - Tc) / R2)


def HDf(S):  # pod half depth
    if S <= S_CAP:
        return 3.3
    return 3.3 - (S - S_CAP) / (S_MZ - S_CAP) * 0.9


# boom: from the hub on the post to the breech
S_HUB, S_BOOM1 = -33.6, -12.8
H_HUB = 6.4
TB0f = T.pchip([-34.0, -29.0, -27.0, -24.0, -21.0, -16.0, -12.8], [43.9, 43.9, 45.2, 45.8, 45.3, 44.6, 44.6])
TB1 = 53.4
TB0 = 44.6


def boom_h(S):
    return H_HUB + (S - S_HUB) * ((pod_h(S_BR) - 0.6 - H_HUB) / (S_BR - S_HUB))


# ---- materials (one slot per region, so the measurement can name each part) ---------------------
MATS, SLOT = [], {}


def M(region, pal, kind="steel", frames=None, strength=1.2):
    key = (region, pal, kind)
    if key in SLOT:
        return SLOT[key]
    tag = f"nB-{region}"
    if kind == "glow":
        m = common.palette_material(SPRITE, pal, tag, metallic=0.0, roughness=0.4, emission_strength=strength,
                                    frames=frames)
    elif kind == "bright":
        m = common.palette_material(SPRITE, pal, tag, metallic=0.55, roughness=0.32)
    elif kind == "dark":
        m = common.palette_material(SPRITE, pal, tag, metallic=0.3, roughness=0.6)
    else:  # satin steel
        m = common.palette_material(SPRITE, pal, tag, metallic=0.45, roughness=0.42)
    m["region"] = region
    MATS.append(m)
    SLOT[key] = len(MATS) - 1
    return SLOT[key]


# ---- geometry helpers (sprite px) ----------------------------------------------------------------
def ring_loft(part, rings, band_mats, cap0=None, cap1=None):
    """rings: list of [points xyz] (same count); band_mats[i] = material of the strip from ring
    vertex i to i+1 (or one int for all). cap0/cap1: material of the end caps (None = open)."""
    V = [[part.v(p) for p in r] for r in rings]
    cs = [Vector(tuple(sum(p[k] for p in r) / len(r) for k in range(3))) for r in rings]
    n = len(rings[0])
    for a in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            m = band_mats[i] if isinstance(band_mats, (list, tuple)) else band_mats
            part.f((V[a][i], V[a][j], V[a + 1][j], V[a + 1][i]), m, away=tuple((cs[a] + cs[a + 1]) / 2))
    if cap0 is not None:
        part.f(V[0], cap0, out=tuple(cs[0] - cs[1]))
    if cap1 is not None:
        part.f(V[-1], cap1, out=tuple(cs[-1] - cs[-2]))
    return V


def box_ring(T0, T1, hb, ht, cl, cr, cb, S):
    """Chamfered box section across the launcher line at S (chamfers in px)."""
    pts = [(T0, hb + cb), (T0 + cb * R2, hb), (T1 - cb * R2, hb), (T1, hb + cb), (T1, ht - cr),
           (T1 - cr * R2, ht), (T0 + cl * R2, ht), (T0, ht - cl)]
    return [P(S, t, h) for t, h in pts]


def frame_of(t):
    t = Vector(t).normalized()
    up = Vector((0, 0, 1))
    side = t.cross(up)
    if side.length < 1e-4:
        side = Vector((1, 0, 0))
    side.normalize()
    up2 = side.cross(t).normalized()
    return side, up2


def tube(part, pts, radii, mat, sides=12, flat=1.0, cap=True, cap_mat=None):
    pts = [Vector(p) for p in pts]
    rings = []
    for i, c in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
        side, up2 = frame_of(t)
        r = radii[i]
        rings.append([tuple(c + r * (math.cos(2 * math.pi * k / sides) * side
                                     + flat * math.sin(2 * math.pi * k / sides) * up2)) for k in range(sides)])
    cm = mat if cap_mat is None else cap_mat
    ring_loft(part, rings, mat, cm if cap else None, cm if cap else None)


def prism(part, poly, z0, ztop, mat, ch=0.5, inset=None):
    """Chamfered convex block: plan polygon `poly` (xy) from z0 up to ztop(x, y) (a number or a
    function), its top edge chamfered `ch` (inset in plan and drop)."""
    zt = ztop if callable(ztop) else (lambda x, y, v=ztop: v)
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    pts = []
    for x, y in poly:
        pts.append((x, y, z0))
        pts.append((x, y, zt(x, y) - ch))
        dx, dy = cx - x, cy - y
        d = math.hypot(dx, dy) or 1
        k = (inset if inset is not None else ch) / d
        pts.append((x + dx * k * 1.4, y + dy * k * 1.4, zt(x, y)))
    T.hull(part, pts, mat)


def plate_on_pod(part, Sa, Sb, Ta, Tb, mat, rise=0.3, ch=0.25, z_of=None):
    """A raised plate lying on the pod's sloping crown over Sa..Sb, Ta..Tb."""
    zf = z_of or (lambda S: pod_h(S) + HDf(S))
    pts = []
    for S in (Sa, Sb):
        for Tc in (Ta, Tb):
            pts.append(P(S, Tc, zf(S) - 0.3))
            si = ch if S == Sa else -ch
            ti = ch * R2 if Tc == Ta else -ch * R2
            pts.append(P(S + si, Tc + ti, zf(S + si) + rise))
            pts.append(P(S, Tc, zf(S) + rise - ch))
    T.hull(part, pts, mat)


# ---- the machine -----------------------------------------------------------------------------------
def build_pod(part):
    crown, chl, chr_, flank_l, flank_r, under, uch = (
        M("pod_crown", 6), M("pod_chamfer_left", 7), M("pod_chamfer_right", 8), M("pod_flank_left", 6),
        M("pod_flank_right", 5, "dark"), M("pod_under", 3, "dark"), M("pod_under_ch", 4, "dark"))
    seam = M("pod_seam", 6, "dark")
    cap_c, cap_s = M("cap_crown", 6), M("cap_side", 4, "dark")

    def ring(S, grow=0.0, cl=1.3, cr=0.9):
        hd = HDf(S) + grow
        return box_ring(T0f(S) - grow * R2, T1f(S) + grow * R2, pod_h(S) - hd, pod_h(S) + hd, cl, cr, 1.0, S)

    bands = [uch, under, uch, flank_r, chr_, crown, chl, flank_l]
    # Body: breech to cap seam (a groove at the seam), then the cap.
    body_S = [S_BR, -12.8, -11.8, -10.6, -9.4, -7.0, -3.0, 2.0, 7.0, 11.0, 12.5]
    ring_loft(part, [ring(S) for S in body_S], bands, cap0=M("breech_face", 4, "dark"), cap1=seam)
    ring_loft(part, [ring(12.5, -0.3), ring(13.4, -0.3)], seam, cap0=seam, cap1=seam)
    cap_bands = [cap_s, cap_s, cap_s, cap_s, cap_s, cap_c, cap_c, cap_s]
    cap_S = [13.4, 15.0, 17.0, 18.8]
    ring_loft(part, [ring(S, 0.0, 1.5, 1.2) for S in cap_S], cap_bands, cap0=seam, cap1=seam)
    # Glowing red muzzle rim (S 18.8 - 21.3): the sprite's red tip pixels.
    rim = M("muzzle_rim", 117, "glow", frames={243: 124, 283: 124}, strength=1.2)
    ring_loft(part, [ring(S, 0.05, 1.5, 1.2) for S in (18.8, 20.0, S_MZ)], rim, cap0=rim, cap1=None)
    # Muzzle face: a dark recessed plate with four launch bores (seen from the north-east).
    face = M("muzzle_face", 2, "dark")
    fr = ring(S_MZ, -0.45, 1.2, 0.9)
    ring_loft(part, [ring(S_MZ, 0.05, 1.5, 1.2), fr], rim, cap0=None, cap1=None)
    recess = [tuple(Vector(p) - AXD * 0.6) for p in fr]
    ring_loft(part, [fr, recess], face, cap0=None, cap1=face)
    bore = M("bore", 1, "dark")
    Tm = (T0f(S_MZ) + T1f(S_MZ)) / 2
    for dt in (-1.3, 1.3):
        for dh in (-0.9, 0.9):
            c = Vector(P(S_MZ - 0.7, Tm + dt * R2, pod_h(S_MZ) + dh))
            tube(part, [c, c + AXD * 0.55], [0.75, 0.75], M("bore_ring", 6, "dark"), sides=10, cap_mat=bore)

    # Breech collar (bright metal ring round the breech).
    col = M("collar", 6, "bright")
    ring_loft(part, [ring(S, g) for S, g in ((-13.9, 0.15), (-13.4, 0.35), (-11.6, 0.35), (-11.1, 0.15))],
              col, cap0=col, cap1=col)
    # Bolt heads on the clamp collar: crown pair and flank pairs (hex heads, bright).
    bolt = M("collar_bolt", 7, "bright")
    for Tc, up in ((46.4, 1), (56.0, 1)):
        c = Vector(P(-12.5, Tc, pod_h(-12.5) + HDf(-12.5) + 0.3))
        tube(part, [c, c + Vector((0, 0, 0.35))], [0.5, 0.5], bolt, sides=6)
    for S in (-12.2, -11.5):
        for Tc, sg in ((T0f(S) - 0.15, -1), (T1f(S) + 0.15, 1)):
            c = Vector(P(S, Tc + sg * 0.2, pod_h(S)))
            tube(part, [c, c + Vector((sg * 0.08, sg * 0.08, 0))], [0.4, 0.4], bolt, sides=6)
    # Dark armour panels on the crown's right half, split by two panel lines, and the red slit.
    pan = M("pod_panel", 5)
    for Sa, Sb in ((-9.6, -2.6), (-2.1, 0.4), (2.9, 12.2)):
        plate_on_pod(part, Sa, Sb, 51.8, 57.0, pan)
    slit = M("top_slit", 116, "glow", frames={243: 119, 283: 124})
    plate_on_pod(part, 0.7, 2.6, 50.2, 54.6, slit, rise=0.22, ch=0.12)
    # Light rail along the crown's upper-left edge.
    rail = M("pod_rail", 8, "bright")
    for seg in ((-10.6, -7.0, -4.3), (0.6, 6.0, 12.0)):
        tube(part, [P(S, 45.9, pod_h(S) + HDf(S) - 0.05) for S in seg], [0.45] * 3, rail, sides=8, flat=0.6)
    # Three side lamps on the upper-left chamfer (row 23, columns 20-22 of newshg-165).
    lamp = [(115, {241: 121, 281: 117}), (118, {241: 122, 281: 125}), (116, {241: 119, 281: 127})]
    for k, (pal, frames) in enumerate(lamp):
        m = M(f"side_lamp_{k}", pal, "glow", frames=frames)
        pts = []
        for x in (20.06 + k, 20.94 + k):
            for y in (23.06, 23.94):
                z = pod_surface(x - y, x + y)
                pts += [(x, y, z + 0.14), (x, y, z - 0.7)]
        T.hull(part, pts, m)
    # Stiffener ribs down both flanks (machined detail for the side and the tilted camera).
    rib = M("pod_rib", 6)
    for S in (-6.5, -0.5, 5.5, 11.0):
        h0, h1 = pod_h(S) - HDf(S) + 1.1, pod_h(S) + HDf(S) - 1.0
        for Ta, Tb in ((T1f(S) - 0.4, T1f(S) + 0.22), (T0f(S) - 0.22, T0f(S) + 0.4)):
            T.hull(part, [P(S + d, t, h + d * KP) for d in (-0.35, 0.35) for t in (Ta, Tb) for h in (h0, h1)], rib)
    # Lifting lugs on the crown near the cap seam and the breech (small machined blocks).
    lug = M("pod_lug", 9)
    for S in (-8.0, 10.5):
        z = pod_h(S) + HDf(S)
        T.hull(part,
               [P(S + a, 47.6 + b, z + c) for a in (-0.6, 0.6) for b in (-0.9, 0.9) for c in (-0.2, 0.55)], lug)


def build_boom(part):
    top, side, und = M("boom_crown", 7), M("boom_side", 5, "dark"), M("boom_under", 3, "dark")

    def ring(S):
        h = boom_h(S)
        return box_ring(TB0f(S), TB1, h - 1.8, h + 1.8, 0.8, 0.8, 0.6, S)

    Ss = [S_HUB, -30.0, -24.0, -18.0, S_BOOM1]
    ring_loft(part, [ring(S) for S in Ss], [und, und, und, side, top, top, top, side], cap0=side, cap1=side)
    # Trunnion hub across the boom's foot, on the post.
    hub = M("hub", 6)
    a = Vector(P(-31.2, TB0f(-31.2) - 0.3, boom_h(-31.2) - 0.4))
    b = Vector(P(-31.2, TB1 + 0.3, boom_h(-31.2) - 0.4))
    tube(part, [a, b], [1.5, 1.5], hub, sides=16, cap_mat=M("hub_cap", 8, "bright"))
    # Ram clevis on the boom's belly.
    cl = M("clevis", 5, "dark")
    T.hull(part, [P(-21.0 + a2, 51.0 + b2, boom_h(-21.0) - 1.8 + c2)
                  for a2 in (-0.9, 0.9) for b2 in (-1.4, 1.4) for c2 in (-0.9, 0.2)], cl)


def build_mount(part):
    # Pivot post: sloped top (high under the hub, lower to the south), dark chamfers.
    post = M("post", 5)
    poly = [(6.0, 40.6), (11.0, 40.6), (11.0, 49.95), (7.0, 49.95), (6.0, 48.95), (6.0, 44.4)]
    top = lambda x, y: 6.2 - (y - 40.6) * 0.22  # noqa: E731
    prism(part, poly, 0.0, top, post, ch=0.55)
    # The glowing slit along the post's top: one inset lens in three strips down its length, colour
    # per newshg-203 frame (203 / 245 / 279): the sprite's hot yellow-white upper half cooling to a
    # dull red foot.
    for nm, (r0, r1), pal, f245, f279 in (("slit_hi", (42.0, 46.0), 116, 127, 124),
                                          ("slit_mid", (46.0, 49.0), 115, 122, 119),
                                          ("slit_lo", (49.0, 50.0), 114, 116, 114)):
        m = M(nm, pal, "glow", frames={245: f245, 279: f279}, strength=2.2)
        pts = [(x, y, top(x, y) + dz) for x in (6.85, 9.15) for y in (r0 + 0.05, r1 - 0.05) for dz in (-0.5, 0.12)]
        T.hull(part, pts, m)
    # Slit frame: two thin rails either side.
    rail = M("post_rail", 7)
    for x in (6.7, 9.3):
        T.hull(part, [(x + a, y, top(x, y) + dz) for a in (-0.25, 0.25) for y in (41.6, 49.6) for dz in (-0.5, 0.3)],
               rail)

    # Elevation housing: chamfered box, top falling gently to the south, two ribs and a hatch.
    box = M("box", 4)
    bpoly = [(11.0, 41.0), (12.95, 38.95), (16.6, 38.95), (17.6, 39.7), (20.0, 40.9), (20.2, 47.0), (17.0, 50.3),
             (17.0, 51.9), (15.1, 51.9), (14.6, 50.7), (12.2, 50.1), (11.0, 49.0)]
    # The housing's stepped north-east lobe (the sprite's outline steps in at row 47).
    blobe = [(19.5, 40.9), (21.3, 41.4), (22.45, 42.0), (22.45, 45.6), (21.9, 46.2), (19.5, 46.9)]
    btop = lambda x, y: 5.0 - (y - 40.0) * 0.12  # noqa: E731
    prism(part, bpoly, 0.0, btop, box, ch=0.7)
    prism(part, blobe, 0.0, btop, box, ch=0.5)
    rib = M("box_rib", 7, "bright")
    for x in (12.9, 15.3):
        T.hull(part, [(x + a, y, btop(x, y) + dz) for a in (-0.45, 0.45) for y in (42.6, 48.6) for dz in (-0.4, 0.45)],
               rib)
    hatch = M("box_hatch", 6)
    T.hull(part, [(x, y, btop(x, y) + dz) for x in (17.0, 21.0) for y in (42.0, 46.0) for dz in (-0.3, 0.2)]
           + [(x, y, btop(x, y) + 0.35) for x in (17.4, 20.6) for y in (42.4, 45.6)], hatch)
    # Hydraulic ram from the housing up to the boom's belly: sleeve and bright rod.
    a = Vector((15.6, 40.6, btop(15.6, 40.6) - 0.5))
    b = Vector(P(-21.0, 51.0, boom_h(-21.0) - 2.4))
    tube(part, [a, a.lerp(b, 0.55)], [0.95, 0.95], M("ram_sleeve", 9), sides=10)
    tube(part, [a.lerp(b, 0.5), b], [0.6, 0.6], M("ram_rod", 9, "bright"), sides=10)

    # Outrigger: a strut along the boom's west flank, bending down to a ground foot, with a prong.
    st = M("outrigger", 7)
    # Curved guard strut (a C-hook round the post, after design A): from the boom's west flank it
    # bends out over the post and sweeps down to a ground foot, thicker mid-bend.
    path = [P(-27.5, 45.6, boom_h(-27.5) - 0.9), P(-30.5, 44.6, 5.4), P(-34.5, 44.0, 4.5),
            (4.6, 39.0, 3.7), (3.3, 40.9, 2.9), (2.7, 42.4, 1.9), (2.5, 43.8, 1.2), (2.6, 44.4, 0.9)]
    tube(part, path, [0.95, 1.05, 1.1, 1.15, 1.25, 1.25, 1.15, 1.0], st, sides=12, flat=1.0)
    foot = M("outrigger_foot", 3, "dark")
    prism(part, [(1.2, 43.2), (3.2, 43.2), (3.2, 44.9), (1.2, 44.9)], 0.0, 0.7, foot, ch=0.2)
    prism(part, [(3.0, 44.2), (6.0, 44.2), (6.0, 45.95), (3.0, 45.95)], 0.0, 0.9, foot, ch=0.2)
    prong = M("prong", 7)
    tube(part, [(4.0, 40.8, 4.2), (4.3, 42.6, 2.6), (4.4, 44.6, 0.8)], [0.62, 0.6, 0.55], prong, sides=8)
    web = M("web", 3, "dark")
    prism(part, [(3.0, 41.0), (6.1, 41.0), (6.1, 44.8), (3.0, 44.8)], 0.0, 1.6, web, ch=0.25)
    # Brace between the outrigger and the post.
    T.hull(part, [(x, y, z) for x in (3.6, 5.6) for y in (39.6, 41.4) for z in (2.6, 4.4)], st)


def build_flame(part, k):
    """Muzzle flame for frame k (1 short, 2 long): nested emissive lofts along the line, fitted to
    the sprite's flame plan (blueprint states)."""
    st = FLAME_STATES[k]
    Ss = [s for s, _, _ in st if s >= 21]
    T0s = T.pchip([s for s, _, _ in st], [a for _, a, _ in st])
    T1s = T.pchip([s for s, _, _ in st], [b for _, _, b in st])
    s_end = st[-1][0] + 0.2
    layers = [(M(f"flame{k}_outer", 118, "glow", strength=1.1), 1.0, 0.55),
              (M(f"flame{k}_mid", 122, "glow", strength=1.2), 0.72, 0.85),
              (M(f"flame{k}_core", 126, "glow", strength=1.15), 0.42, 1.25)]
    for m, w, hz in layers:
        s0 = st[0][0] + 0.5 if w == 1.0 else S_MZ - 0.6
        stations = [s0 + 0.5 * i for i in range(int((s_end - 0.4 - s0) / 0.5) + 1)] + [s_end]
        L = s_end - S_MZ
        rings = []
        for s in stations:
            f = (s - S_MZ) / L
            tc = (T0s(min(s, st[-1][0])) + T1s(min(s, st[-1][0]))) / 2
            hw = max(0.05, (T1s(min(s, st[-1][0])) - T0s(min(s, st[-1][0]))) / 2 / R2) * w
            if f > 0.6 and w < 1.0:
                hw *= max(0.1, 1 - (f - 0.6) / 0.4 * (1.2 - w))
            if s >= s_end:
                hw = 0.05
            hd = hw * hz * (1.0 if w == 1.0 else 1.0)
            c = Vector(P(s, tc, pod_h(min(s, S_MZ)) + max(0.0, s - S_MZ) * KP * 0.4))
            side = Vector((1, 1, 0)).normalized()
            rings.append([tuple(c + side * hw * math.cos(a) + Vector((0, 0, hd * math.sin(a))))
                          for a in (2 * math.pi * i / 12 for i in range(12))])
        ring_loft(part, rings, m, cap0=m, cap1=m)


def to_object(part, name, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((U, 0, 0, -24 * U), (0, -U, 0, 28 * U), (0, 0, U, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in MATS:
        me.materials.append(mt)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(32))
    return obj


# ---- measurement: top view on the sprite grid ------------------------------------------------------
def rasterise(objs, sub=4):
    bm = bmesh.new()
    regions = []
    for o in objs:
        tmp = bmesh.new()
        tmp.from_mesh(o.data)
        off = len(regions)
        regions += [mt.get("region", mt.name) + "|" + mt.name.split("_")[1] for mt in o.data.materials]
        for f in tmp.faces:
            f.material_index += off
        me = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    H, W = SD["h"], SD["w"]
    cov = [[0.0] * W for _ in range(H)]
    top = [[None] * W for _ in range(H)]
    hmax = 0.0
    for r in range(H):
        for c in range(W):
            hits = []
            for i in range(sub):
                for j in range(sub):
                    x = c + (i + 0.5) / sub
                    y = r + (j + 0.5) / sub
                    loc, nrm, idx, d = tree.ray_cast(Vector(((x - 24) * U, (28 - y) * U, 50.0)), Vector((0, 0, -1)))
                    if idx is not None:
                        hits.append(bm.faces[idx].material_index)
                        hmax = max(hmax, loc.z / U)
            cov[r][c] = len(hits) / (sub * sub)
            if hits:
                cc = (r + 0.5, c + 0.5)
                # centre sample decides the top region
                loc, nrm, idx, d = tree.ray_cast(Vector(((cc[1] - 24) * U, (28 - cc[0]) * U, 50.0)), Vector((0, 0, -1)))
                top[r][c] = regions[bm.faces[idx].material_index] if idx is not None else regions[hits[0]]
    bm.free()
    return cov, top, hmax


def iou(cov, k):
    inner, free = SD["inner"][k], SD["free"][k]
    H, W = SD["h"], SD["w"]
    i = u = 0
    miss, extra = [], []
    piece = {}
    for r in range(H):
        for c in range(W):
            if free[r][c]:
                continue
            m = cov[r][c] >= 0.5
            s = bool(inner[r][c])
            pk = (c >= 24) + 2 * (r >= 28)
            pi = piece.setdefault(pk, [0, 0])
            if m and s:
                i += 1
                pi[0] += 1
            if m or s:
                u += 1
                pi[1] += 1
            if s and not m:
                miss.append((r, c))
            if m and not s:
                extra.append((r, c))
    return i / u, {k2: round(v[0] / v[1], 4) if v[1] else 1.0 for k2, v in sorted(piece.items())}, miss, extra


# ---- renders -----------------------------------------------------------------------------------------
def setup_render(w, h, engine="WORKBENCH"):
    sc = bpy.context.scene
    for mt in bpy.data.materials:
        if mt.node_tree:
            bs = next((n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bs is not None:
                mt.diffuse_color = tuple(bs.inputs["Base Color"].default_value)
                mt.metallic = 0.0
                mt.roughness = 0.6
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.3, 0.32, 0.36, 1)
    bg.inputs[1].default_value = 0.45
    if "sun" not in bpy.data.objects:
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 3.5
        sun.rotation_euler = (math.radians(35), math.radians(-20), math.radians(30))
        sc.collection.objects.link(sun)
    try:
        sc.render.engine = "BLENDER_WORKBENCH" if engine == "WORKBENCH" else "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE"
    if engine == "WORKBENCH":
        sh = sc.display.shading
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_shadows = True
        sh.shadow_intensity = 0.55
        sh.show_cavity = True
        sh.cavity_type = "WORLD"
        sh.show_object_outline = False
        sc.display.render_aa = "16"
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"


def camera(loc, target, ortho=None, lens=50):
    sc = bpy.context.scene
    cam = sc.camera
    if cam is None:
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
    cam.location = loc
    d = Vector(target) - Vector(loc)
    up = "Y" if abs(d.normalized().z) < 0.999 else "Y"
    cam.rotation_euler = d.to_track_quat("-Z", up).to_euler()
    if abs(d.normalized().z) > 0.999:
        cam.rotation_euler = (0, 0, 0) if d.z < 0 else (math.pi, 0, 0)
    cam.data.clip_end = 500
    if ortho:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"
        cam.data.lens = lens


def render(objs, path, loc, target, size, ortho=None, lens=50, engine="WORKBENCH"):
    setup_render(*size, engine=engine)
    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            o.hide_render = o not in objs
    camera(loc, target, ortho, lens)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def measure(body, fl):
    out = {"frames": []}
    for k in range(3):
        objs = [body] + ([fl[k]] if k else [])
        cov, top, hmax = rasterise(objs)
        v, pieces, miss, extra = iou(cov, k)
        out["frames"].append({"frame": k, "iou": round(v, 4), "pieces": pieces, "miss": miss, "extra": extra,
                              "hmax_px": round(hmax, 2), "cov": cov, "top": top})
        print(f"frame {k}: IoU {v:.4f} pieces {pieces} miss {len(miss)} extra {len(extra)} hmax {hmax:.2f}")
        print("  miss", miss)
        print("  extra", extra)
    (SCRATCH / "final").mkdir(exist_ok=True)
    (SCRATCH / "final" / "measure.json").write_text(json.dumps(out))


def render_all(body, fl):
    R = SCRATCH / "final" / "renders"
    R.mkdir(exist_ok=True)
    gmat = bpy.data.materials.new("ground")
    gmat.diffuse_color = (0.05, 0.13, 0.05, 1)
    gmat.use_nodes = True
    next(n for n in gmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = \
        (0.02, 0.06, 0.02, 1)
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, -0.002))
    ground = bpy.context.active_object
    ground.data.materials.append(gmat)
    ctr = (0, 0.2, 0.6)
    B0 = [body]
    B0 = [body, ground]
    render(B0, R / "top.png", (0, 0, 30), (0, 0, 0), (480, 560), ortho=56 * U)
    render([body, ground, fl[1]], R / "top_f1.png", (0, 0, 30), (0, 0, 0), (480, 560), ortho=56 * U)
    render([body, ground, fl[2]], R / "top_f2.png", (0, 0, 30), (0, 0, 0), (480, 560), ortho=56 * U)
    G = [body, ground]
    t = math.radians(32)
    render(G + [fl[1]], R / "game.png", (0, -30 * math.sin(t), 30 * math.cos(t)), (0, 0, 0.4), (480, 560), lens=165)
    render(G + [fl[1]], R / "game_eevee.png", (0, -30 * math.sin(t), 30 * math.cos(t)), (0, 0, 0.4), (480, 560),
           lens=165, engine="EEVEE")
    render(G, R / "side_e.png", (25, 0, 0.8), (0, 0, 0.8), (560, 260), ortho=5.0)
    render(G, R / "side_w.png", (-25, 0, 0.8), (0, 0, 0.8), (560, 260), ortho=5.0)
    render(G, R / "front.png", (0, -25, 0.8), (0, 0, 0.8), (560, 260), ortho=5.0)
    render(G, R / "rear.png", (0, 25, 0.8), (0, 0, 0.8), (560, 260), ortho=5.0)
    render(G, R / "broadside.png", (17, -17, 0.9), (0, 0, 0.9), (560, 260), ortho=5.4)
    render(G + [fl[2]], R / "q34_se.png", (5.5, -5.5, 3.6), ctr, (560, 480), lens=45)
    render(G, R / "q34_sw.png", (-5.5, -5.5, 3.8), ctr, (560, 480), lens=45)
    render(G, R / "q34_nw.png", (-5.5, 5.5, 3.6), ctr, (560, 480), lens=45)
    render(G, R / "q34_ne.png", (4.2, 4.6, 2.6), (0.6, 0.8, 1.0), (560, 480), lens=45)
    render([body], R / "under.png", (0, 0, -30), (0, 0, 0), (480, 560), ortho=56 * U * 1.05)



def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    part = T.Part("machine", smooth_angle=32)
    build_pod(part)
    build_boom(part)
    build_mount(part)
    flames = {}
    for k in (1, 2):
        fp = T.Part(f"flame{k}")
        build_flame(fp, k)
        flames[k] = fp
    body = to_object(part, NAME, coll)
    fl = {k: to_object(p, f"newshg-167-flame-f{k + 1}", coll) for k, p in flames.items()}
    for o in fl.values():
        o.data.shade_smooth()
    if SD is not None:
        measure(body, fl)
        if "--render" in sys.argv:
            render_all(body, fl)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in SPRITE["assemblyLayout"]]
    pieces = common.split_assembly(body, layout)
    shells = {}
    for name in PIECES:
        # Outline shell (D51, D90, D118) from a sealed copy of the piece, before any culling.
        src = pieces[name].copy()
        src.data = pieces[name].data.copy()
        coll.objects.link(src)
        sh = common.outline_shell(src, coll, voxel=0.01, faces=1500, smooth=4, inside=0.004)
        bpy.data.objects.remove(src)
        sh.name = sh.data.name = f"{name}_outline"
        shells[name] = sh
        lib.drop_slivers(pieces[name])
    exported = {}
    for name in PIECES:
        sprites = common.load_sprite(ROOT, name)["sprites"]
        parts = [pieces[name], shells[name]]
        if name == "newshg-167":
            frames = sprites[0]["frames"]
            one = lambda k: [dict(sprites[0], frames=[frames[k]])]  # noqa: E731
            common.export_sprite_model(ROOT, parts, f"enemies/{name}", one(0))
            exported[name] = parts
            for k in (1, 2):
                part_l = common.split_assembly(fl[k], [(name, *next((x, y) for n, x, y in layout if n == name))])[name]
                lib.drop_slivers(part_l)
                part_l.name = f"{name}-f{k + 1}-flame"
                common.export_sprite_model(ROOT, parts + [part_l], f"enemies/{name}-f{k + 1}", one(k))
                exported[f"{name}-f{k + 1}"] = parts + [part_l]
        else:
            common.export_sprite_model(ROOT, parts, f"enemies/{name}", sprites)
            exported[name] = parts
    print("exported", list(exported))


main()
