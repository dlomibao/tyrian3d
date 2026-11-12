"""Left corner tower of the red newshf fortress (assembly of newshf-153, 155, 191, 193): a
hard-surface 3D version of its sprites, built from the blueprint's cross-sections.

Seen in episode 1 (levels 1.10, 1.29, 1.38), 2 (2.2), 3 (3.21) and 4 (4.16). Four 2x2 enemies
(drawn on the ground layer, which only says where they are drawn) make one 48 x 56 px block (the fortress's upper left corner): a rounded bastion drum on the
outside, three glowing red barrels lying in slots and reaching up the screen past the deck, ribs
between the slots, breech rings at the barrels' roots, and a body of plates with the barrels'
recoil channels running to the front; barrel 3's breech is a big chamber drum. Each piece has one
frame (enemies/<piece>.glb, its sprite.json "sprites").

What it is (D120/D122 identify the object first; DECISIONS D167): the red FLYING gun fortress at the end of
SAVARA, in three sections that separate, not a ground building. In 1.8 and 1.12 SAVARA it holds at
the top of the screen over open sea; event 20 then pushes the two wing
sections (assembly-newshf-191 with newshf-230 on the left, assembly-newshf-199 with newshf-238 on the
right) out sideways at +-6 px/tick and back, while the centre gun module (assembly-newshf-195) roams
on its own; in 1.17 SAVARA V the same pieces spawn on the sky layer. The model already reads as that
from the game camera: armoured hull plating, barrels and turrets over a closed flat underside, with no
foundations, legs or walls down to a ground. So it was not rebuilt, and its pieces and pivots are
unchanged so the split still works.

The ORIGINAL SPRITE decides the plan (D52, D74): the deck outline is the blueprint's trace of the
D74 inner mask (the drum curve on the left, the staircase back edge under the barrels, the flat
right side and front where the sprite ends); every part's plan is the sprite's pixel columns and
rows (ribs at cols 23/25, 35/37, 47; barrels cols 15-21, 27-33, 39-45, rows 12/6/1.6 to 41/35/30;
breech rings rows 42, 36, 31; channels cols 16-20, 29-32, 41-44). Heights and sections (px, the
blueprint's, cross-sections first):

    part             z            section
    plinth           0 .. 1.9     chamfered slab over the whole deck plan; slot / channel floors
    drum             1.6 .. 4.85  superellipse quarter round (p 2.4) from the slot wall to the plan
                                  edge, V-groove seams, chamfered front end, rounded back nose
    crown rail       .. 5.15      lit rail on the drum crown beside slot 1 (sprite col 13)
    ribs             1.9 .. 5.6   twin fins (shade 72 / lit 75) with a slit between them,
                                  sloped back ends
    breech rings     1.9 .. 8.6   rounded-rect clamp ring round each barrel's root on a pedestal
    plates           1.9 .. 5.0   chamfered plates, modelled seams (real gaps), a few bolts; they run
                                  flush to the block's front edge (y 56), where it meets the base
    channels         1.9 .. 2.4   recoil rail and ties in each channel
    chamber drum     1.6 .. 8.0   barrel 3's breech: elliptic cylinder along y, rear sleeve (rows
                                  32-35, 72) with a seam at col 41, raised bands (rows 36, 42, 74),
                                  body (rows 37-41, 73); the col-45 bright streak is sheen
    barrels          2.6 .. 8.0   rounded rect 7 x 5.4 (r 1.25) with a side groove, chamfered muzzle
                                  and recessed glowing emitter (117 in the 116 cap), V-grooves between the far / glow / root zones,
                                  inlaid "E" marking (yellow spine 123, orange bars 120), saddles
                                  under the cantilever at the slot mouth

Colours: palette materials (pal_<index>), each the trimmed median of the sprite pixels the part
covers (blueprint sprite_regions): drum 66, crown 74, rib shade 72 / lit 75, rings 71 / 74 / 74,
plates 67 / 69 / 69 / 70 / 68 / 69, chamber sleeve 72 / bands 74 / body 73, channels 65, barrels far 116 / glow 117 / root 113.
Satin metal. Only the muzzle bore (EMIT) is emissive: the game copies the full palette colour into
any non-zero emissive (src/render/modelFrames.ts colourFrame), so emission strengths <= 1 act as 1 and
an emissive barrel renders candy red; the barrels and the E marking are plain lit palette colour.

No texture bake (no textures/ folder; plain palette materials). Outline shell (D51): one voxel shell
of the whole tower, cut open (no caps) into a shell per piece. Each piece is exported with its shell
to public/models/enemies/<piece>.glb with its spriteModels entry (common.export_sprite_model).

Run: blender --background --python assets/blender/enemies/assembly-newshf-191.py
    [-- --preview out.png] [--no-export] [--design-out whole.glb]
(--preview: the whole tower beside the composed sprite; --design-out: one review .glb with every
piece in assembly space, custom property tyrian_piece.)
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

GAME_ROOT = common.repo_root(__file__)
NAME = "assembly-newshf-191"
TAG = "newshf-191"
PIECES = ["newshf-191", "newshf-193", "newshf-153", "newshf-155"]
X0, Y0 = 70, -31  # screen pixel of the block's top-left corner (lib_b100.main)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

# ----------------------------------------------------------------------------------------------
# Helpers (copied from assembly-newsh4-124 / the blueprint; px space: x right, y down, z up)
# ----------------------------------------------------------------------------------------------


class Part:
    def __init__(self):
        self.bm = bmesh.new()
        self.groups = []  # (faces, closed) per primitive, oriented in orient()
        self.cur = None

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, verts, mat):
        try:
            face = self.bm.faces.new(verts)
        except ValueError:
            return None
        face.material_index = mat
        if self.cur is not None:
            self.cur.append(face)
        return face

    def orient(self):
        """Outward normals per primitive: closed ones by signed volume, open ones away from
        their centroid (bands round an axis)."""
        for faces, closed in self.groups:
            faces = [f for f in faces if f.is_valid]
            if not faces:
                continue
            if closed:
                vol = 0.0
                for f in faces:
                    vs = [v.co for v in f.verts]
                    for i in range(1, len(vs) - 1):
                        vol += vs[0].dot(vs[i].cross(vs[i + 1]))
                if vol < 0:
                    bmesh.ops.reverse_faces(self.bm, faces=faces)
            else:
                c = sum((f.calc_center_median() for f in faces), Vector()) / len(faces)
                flip = []
                for f in faces:
                    f.normal_update()
                    if f.normal.dot(f.calc_center_median() - c) < 0:
                        flip.append(f)
                if flip:
                    bmesh.ops.reverse_faces(self.bm, faces=flip)


def loft(P, rings, mats, cap0=True, cap1=True):
    """Rings of equal count (or a single point) in order; mats per span (or one)."""
    if not isinstance(mats, (list, tuple)):
        mats = [mats] * (len(rings) - 1)
    P.cur = []
    P.groups.append((P.cur, cap0 and cap1 or (len(rings[0]) == 1 or len(rings[-1]) == 1)))
    vr = [[P.v(p) for p in ring] for ring in rings]
    for i, (a, b) in enumerate(zip(vr, vr[1:])):
        m = mats[min(i, len(mats) - 1)]
        n = max(len(a), len(b))
        for k in range(n):
            j = (k + 1) % n
            if len(a) == 1:
                P.f((a[0], b[k], b[j]), m)
            elif len(b) == 1:
                P.f((a[k], a[j], b[0]), m)
            else:
                P.f((a[k], a[j], b[j], b[k]), m)
    if cap0 and len(vr[0]) > 2:
        P.f(list(reversed(vr[0])), mats[0])
    if cap1 and len(vr[-1]) > 2:
        P.f(vr[-1], mats[-1])


def offset_poly(poly, d):
    """Inset (d > 0) a polygon by moving each vertex along its miter."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    s = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]

        def nrm(a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1e-9
            return (-dy / ln * s, dx / ln * s)
        n1, n2 = nrm(p0, p1), nrm(p1, p2)
        mx, my = n1[0] + n2[0], n1[1] + n2[1]
        ln = math.hypot(mx, my) or 1e-9
        mx, my = mx / ln, my / ln
        cos = max(0.4, mx * n2[0] + my * n2[1])
        out.append((p1[0] + mx * d / cos, p1[1] + my * d / cos))
    return out


def prism(P, outline, z0, z1, mat, ch=0.35, chb=0.0, side_mat=None):
    """A plate over `outline` from z0 to z1, top edges chamfered `ch`, bottom `chb` (45 deg)."""
    pts = list(outline)
    n = len(pts)
    th = z1 - z0
    ch = min(ch, th * 0.45)
    chb = min(chb, th * 0.3)
    levels = []
    if chb > 0:
        levels += [(offset_poly(pts, chb), z0), (pts, z0 + chb)]
    else:
        levels.append((pts, z0))
    if ch > 0:
        levels += [(pts, z1 - ch), (offset_poly(pts, ch), z1)]
    else:
        levels.append((pts, z1))
    rings = [[(x, y, z) for x, y in poly] for poly, z in levels]
    sm = side_mat if side_mat is not None else mat
    loft(P, rings, [sm] * (len(rings) - 2) + [mat])


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def block(P, x0, y0, x1, y1, z1, mat, ch=0.35, z0=1.9, chb=0.0):
    prism(P, rect(x0, y0, x1, y1), z0, z1, mat, ch=ch, chb=chb)


def catmull(ctrl, n=6):
    out = []
    L = len(ctrl)

    def get(i):
        return ctrl[max(0, min(L - 1, i))]
    for i in range(L - 1):
        p0, p1, p2, p3 = get(i - 1), get(i), get(i + 1), get(i + 2)
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(tuple(ctrl[-1]))
    return out


def cyl(P, x, y, z, r, h, mat, n=6):
    """A bolt head: base centre (x, y, z), up z."""
    a = [(x + r * math.cos(2 * math.pi * (k + 0.5) / n), y + r * math.sin(2 * math.pi * (k + 0.5) / n), z) for k in range(n)]
    b = [(px, py, z + h) for px, py, _ in a]
    c = [(x + 0.7 * (px - x), y + 0.7 * (py - y), z + h + 0.08) for px, py, _ in a]
    loft(P, [a, b, c], mat)


# ----------------------------------------------------------------------------------------------
# Materials: (name, palette index, metallic, roughness, emission)
# ----------------------------------------------------------------------------------------------

SLOTS = [
    ("FLOOR", 65, 0.3, 0.6, 0),       # plinth, slot and channel floors, slits
    ("DRUM", 66, 0.3, 0.42, 0),       # the bastion drum
    ("SEAM", 64, 0.3, 0.6, 0),        # V-groove seams
    ("CROWN", 74, 0.3, 0.38, 0),     # crown rail beside slot 1
    ("RIBSH", 72, 0.3, 0.42, 0),      # rib fins, shade side
    ("RIBLIT", 75, 0.3, 0.38, 0),    # rib fins, lit side
    ("RING1", 71, 0.3, 0.38, 0),     # breech ring, barrel 1
    ("RING", 74, 0.3, 0.38, 0),      # breech rings, barrels 2 and 3
    ("PLA", 67, 0.3, 0.45, 0),        # plate a
    ("PLB", 69, 0.3, 0.42, 0),        # plates b, c, f
    ("PLD", 70, 0.3, 0.42, 0),        # plate d, saddles
    ("PLE", 68, 0.3, 0.42, 0),        # plate e
    ("CHAM", 73, 0.3, 0.36, 0),      # chamber drum
    ("CHAMB", 72, 0.3, 0.4, 0),      # chamber rear sleeve (rows 32-35)
    ("RAIL", 66, 0.3, 0.45, 0),      # channel rails, bolts
    ("FAR", 116, 0.25, 0.42, 0),    # barrel far end
    ("GLOW", 117, 0.2, 0.4, 0),       # barrel glow zone
    ("ROOT", 113, 0.25, 0.45, 0),  # barrel root
    ("EMIT", 117, 0.1, 0.45, 0.9),    # muzzle emitter face: glowing bore in the 116 cap
    ("SPINE", 123, 0.1, 0.4, 0),    # marking: yellow spine
    ("BARS", 120, 0.1, 0.4, 0),       # marking: orange bars
    ("RGROOVE", 112, 0.3, 0.5, 0),  # barrel zone grooves
]
(FLOOR, DRUM, SEAM, CROWN, RIBSH, RIBLIT, RING1, RING, PLA, PLB, PLD, PLE, CHAM, CHAMB, RAIL, FAR, GLOW, ROOT,
 EMIT, SPINE, BARS, RGROOVE) = range(len(SLOTS))


def merged_sprite():
    data = common.load_sprite(GAME_ROOT, PIECES[0])
    for name in PIECES[1:]:
        data["colors"].update(common.load_sprite(GAME_ROOT, name)["colors"])
    return data


def materials(sprite):
    return [common.palette_material(sprite, i, f"{TAG}-{n.lower()}", metallic=m, roughness=r, emission_strength=e)
            for n, i, m, r, e in SLOTS]


# ----------------------------------------------------------------------------------------------
# Plan (blueprint trace of the D74 inner mask)
# ----------------------------------------------------------------------------------------------

Z_FLOOR, Z_DECK, Y_FRONT = 1.9, 5.0, 55.4
Y_EDGE = 56.0  # the block's front edge (the cut to the base): plates run flush to it
DRUM_CURVE = catmull([(14.2, 25.0), (13.0, 26.5), (11.6, 27.9), (10.4, 29.5), (9.1, 31.4), (8.0, 33.0), (7.0, 34.9),
                      (6.2, 37.2), (6.0, 40.5), (6.05, 44.6), (6.9, 47.0), (8.0, 49.4), (9.0, 51.9), (10.0, 54.0),
                      (10.6, Y_FRONT)], 3)
BACK = [(14.2, 25.0), (15.0, 24.3), (22.0, 19.6), (27.0, 19.6), (34.0, 15.6), (37.0, 15.6), (37.5, 14.6),
        (39.0, 14.6), (46.0, 13.5), (48.0, 13.5)]
DECK = list(reversed(DRUM_CURVE)) + BACK[1:] + [(48.0, Y_FRONT)]


def drum_out(y):
    for a, b in zip(DRUM_CURVE, DRUM_CURVE[1:]):
        if (y - a[1]) * (y - b[1]) <= 0 and a[1] != b[1]:
            return a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1])
    return 14.2 if y < 30 else 10.6


# Barrels: (x0, x1, top y, root y); section rounded rect hw 3.5, hh 2.7, r 1.25, axis z 5.3.
RODS = [(15.0, 22.0, 12.0, 41.0), (27.0, 34.0, 6.0, 35.0), (39.0, 46.0, 1.6, 30.0)]
RZ, RHH, RRC = 5.3, 2.7, 1.25


def rod_section(xc, y, hw, hh, rc, zc=RZ, k=1.0, n=4, notch=0.22, dip=None):
    """Rounded rect across x at row y, a shallow groove along each side at the axis height and,
    with `dip`, an emitter trough down the middle of the top (the sprite's dark centre and lit
    edges at the barrel's far end). Without `notch` / `dip` (None) the ring has fewer points."""
    W, H = hw * k, hh * k
    R = min(rc * k, W, H)
    pts = []
    corners = [(xc + W - R, zc + H - R, 0.0), (xc - W + R, zc + H - R, math.pi / 2),
               (xc - W + R, zc - H + R, math.pi), (xc + W - R, zc - H + R, 1.5 * math.pi)]
    for ci, (cx, cz, a0) in enumerate(corners):
        for i in range(n + 1):
            a = a0 + (i / n) * math.pi / 2
            pts.append((cx + R * math.cos(a), y, cz + R * math.sin(a)))
        if dip is not None and ci == 0:  # top, going left
            t = zc + H
            pts += [(xc + 1.9 * k, y, t), (xc + 1.35 * k, y, t - dip * k), (xc - 1.35 * k, y, t - dip * k),
                    (xc - 1.9 * k, y, t)]
        if notch and ci == 1:  # left side, going down
            g = notch * k
            pts += [(xc - W, y, zc + 0.35 * k), (xc - W + g, y, zc + 0.18 * k), (xc - W + g, y, zc - 0.18 * k),
                    (xc - W, y, zc - 0.35 * k)]
        if notch and ci == 3:  # right side, going up
            g = notch * k
            pts += [(xc + W, y, zc - 0.35 * k), (xc + W - g, y, zc - 0.18 * k), (xc + W - g, y, zc + 0.18 * k),
                    (xc + W, y, zc + 0.35 * k)]
    return pts


def rod_top(x, xc, hw):
    dx = abs(x - xc) - (hw - RRC)
    return RZ + RHH if dx <= 0 else RZ + RHH - RRC + math.sqrt(max(0.0, RRC * RRC - dx * dx))


# ----------------------------------------------------------------------------------------------
# The build
# ----------------------------------------------------------------------------------------------


def build_plinth(P):
    # The base slab over the whole deck plan; its top is the slot and channel floor.
    prism(P, DECK, 0.0, Z_FLOOR, FLOOR, ch=0.2, chb=0.3)


def drum_ring(y, xi, xo, h, zb=1.6, n=10, p=2.4, k=1.0):
    """Quarter superellipse from the crown (xi, h) to the plan edge (xo, zb), closed along the
    inner wall (x = xi) and the base; `k` scales it about (xi, zb) (grooves, end chamfers)."""
    rx = max(0.05, xi - xo) * k
    rz = (h - zb) * k
    ring = [(xi, y, zb)]
    for s in range(n + 1):
        t = (math.pi / 2) * s / n
        sx, cz = math.sin(t), math.cos(t)
        ring.append((xi - rx * sx ** (2 / p), y, zb + rz * cz ** (2 / p)))
    return ring


def build_drum(P):
    def h(y):
        u = min(1.0, max(0.0, (y - 25.25) / 4.5))
        return Z_FLOOR + (Z_DECK - 0.15 - Z_FLOOR) * (0.25 + 0.75 * math.sin(u * math.pi / 2))

    def stations(y0, y1, seams, step=0.75):
        ys = []
        y = y0
        while y < y1 - 0.2:
            ys.append(y)
            y += step
        ys.append(y1)
        out = []
        for y in ys:
            if any(abs(y - s) < 0.5 for s in seams):
                continue
            out.append((y, 1.0, DRUM))
        for s in seams:
            out += [(s - 0.18, 1.0, DRUM), (s, 0.955, SEAM), (s + 0.18, 1.0, SEAM)]
        out.sort()
        return out

    for (y0, y1, xi, seams, nose) in ((25.25, 42.6, 14.0, [33.0], True), (42.4, Y_FRONT, 12.1, [50.0], False)):
        st = stations(y0, y1, seams)
        rings, mats = [], []
        for i, (y, k, m) in enumerate(st):
            if y > Y_FRONT - 0.35:
                k = 0.93  # chamfered front end
            rings.append(drum_ring(y, xi, drum_out(y), h(y), k=k))
            mats.append(m)
        loft(P, rings, mats[1:])

    # Crown rail beside slot 1 (sprite col 13), on the drum's crown.
    block(P, 13.0, 25.8, 14.1, 41.0, Z_DECK + 0.15, CROWN, ch=0.3, z0=3.5)


def build_ribs(P):
    def fin(x0, x1, y0, y1, zt, mat):
        # A fin with a sloped back end (it leans back to the deck edge) and chamfered top.
        pts = [(x0, y0 + 1.2), (x1, y0 + 1.2), (x1, y1), (x0, y1)]
        prism(P, pts, Z_FLOOR, zt, mat, ch=0.3)
        loft(P, [[(x0 + 0.08, y0, Z_FLOOR), (x1 - 0.08, y0, Z_FLOOR), (x1 - 0.08, y0, Z_FLOOR + 0.6), (x0 + 0.08, y0, Z_FLOOR + 0.6)],
                 [(x0 + 0.08, y0 + 1.25, Z_FLOOR), (x1 - 0.08, y0 + 1.25, Z_FLOOR), (x1 - 0.08, y0 + 1.25, zt - 0.3),
                  (x0 + 0.08, y0 + 1.25, zt - 0.3)]], mat)

    fin(23.0, 24.0, 19.6, 42.0, Z_DECK + 0.4, RIBSH)
    fin(25.0, 26.0, 19.6, 35.0, Z_DECK + 0.6, RIBLIT)
    fin(35.0, 36.0, 16.0, 35.0, Z_DECK + 0.4, RIBSH)
    fin(37.0, 38.0, 15.5, 30.0, Z_DECK + 0.6, RIBLIT)
    fin(47.0, 48.0, 13.5, 30.0, Z_DECK + 0.4, RIBSH)


def build_rings(P):
    # Breech rings: a rounded-rect clamp round each barrel root, on a pedestal across the slot.
    specs = [(RODS[0], 13.0, 23.0, 41.0, 43.0, RING1), (RODS[1], 25.0, 36.0, 35.0, 37.0, RING),
             (RODS[2], 37.0, 48.0, 30.0, 32.0, RING)]
    for (x0, x1, _, _), px0, px1, y0, y1, mat in specs:
        xc, hw = (x0 + x1) / 2, (x1 - x0) / 2
        block(P, px0, y0, px1, y1, Z_DECK + 1.0, mat, ch=0.45)
        g = 0.55
        rings = [rod_section(xc, y0 - 0.35, hw + g * 0.6, RHH + g * 0.6, RRC + 0.3, notch=0),
                 rod_section(xc, y0 - 0.05, hw + g, RHH + g, RRC + 0.4, notch=0),
                 rod_section(xc, y1 - 0.3, hw + g, RHH + g, RRC + 0.4, notch=0),
                 rod_section(xc, y1, hw + g * 0.5, RHH + g * 0.5, RRC + 0.3, notch=0)]
        loft(P, rings, mat)
        # clamp bolts on the ring's shoulders
        for sx in (-1, 1):
            cyl(P, xc + sx * (hw - 0.4), (y0 + y1) / 2, RZ + RHH + g - 0.25, 0.35, 0.18, RAIL)


def build_body(P):
    # Plates of the lower body, with modelled seams (real gaps down to the floor).
    G = 0.14  # half a seam gap
    plates = [
        (12.6, 43.0, 16.0, 49.5, PLA), (12.6, 49.5, 16.0, Y_EDGE, PLA),
        (21.0, 43.0, 24.0, 49.5, PLB), (21.0, 49.5, 24.0, Y_EDGE, PLB),
        (25.0, 37.0, 29.0, 46.0, PLB), (25.0, 46.0, 29.0, Y_EDGE, PLB),
        (33.0, 37.0, 36.0, 46.0, PLD), (33.0, 46.0, 36.0, Y_EDGE, PLD),
        (37.0, 43.0, 48.0, 47.0, PLE), (37.0, 47.0, 48.0, 51.5, PLE),
        (37.0, 51.5, 41.0, Y_EDGE, PLB), (45.0, 51.5, 48.0, Y_EDGE, PLB),
    ]
    for x0, y0, x1, y1, m in plates:
        seams = (46.0, 47.0, 49.5, 51.5)
        ya = y0 + (G if y0 in seams else 0.0)
        yb = y1 - (G if y1 in seams else 0.0)
        # Front plates run 0.4 px past the block edge; split_assembly cuts them flush at y 56 (their
        # chamfer falls outside the cut), so they meet the base with no gap at row 55.
        if y1 >= Y_EDGE:
            yb = Y_EDGE + 0.4
        prism(P, rect(x0, ya, x1, yb), Z_FLOOR, Z_DECK, m, ch=0.35)
    # A few bolts on the plates (machined detail, top view only a sub-pixel dot).
    for x, y in [(14.3, 51.5), (22.5, 46.0), (22.5, 52.5), (27.0, 41.0), (27.0, 51.0), (34.5, 41.0), (34.5, 51.0),
                 (38.6, 45.0), (46.4, 45.0), (38.6, 49.5), (46.4, 49.5), (39.0, 53.5), (46.5, 53.5)]:
        cyl(P, x, y, Z_DECK, 0.32, 0.14, RAIL)
    # Recoil rails and ties in the channels.
    for x0, x1, y0 in ((16.0, 21.0, 43.0), (29.0, 33.0, 37.0), (41.0, 45.0, 51.5)):
        xc = (x0 + x1) / 2
        block(P, xc - 0.45, y0, xc + 0.45, Y_FRONT - 0.15, Z_FLOOR + 0.55, RAIL, ch=0.15)
        y = y0 + 1.5
        while y < Y_FRONT - 1.0:
            block(P, x0 + 0.25, y, x1 - 0.25, y + 0.5, Z_FLOOR + 0.3, SEAM, ch=0.1)
            y += 3.0


def build_chamber(P):
    # Barrel 3's breech chamber: an elliptic cylinder along y with raised bands and a seam.
    xc, zc, rx, rz = 42.5, 4.8, 5.2, 3.2
    n = 28

    def ell(y, k=1.0, kz=None):
        kz = k if kz is None else kz
        return [(xc + rx * k * math.cos(2 * math.pi * (i + 0.5) / n), y, zc + rz * kz * math.sin(2 * math.pi * (i + 0.5) / n))
                for i in range(n)]
    # cradle under it (closes the gap to the floor)
    block(P, 37.4, 32.0, 47.9, 43.0, 3.2, CHAMB, ch=0.2)
    loft(P, [ell(32.0, 0.88), ell(32.25, 0.95), ell(36.05, 0.95)], CHAMB)          # rear sleeve, rows 32-35
    loft(P, [ell(35.95, 0.97), ell(36.1, 0.985), ell(36.9, 0.985), ell(37.05, 0.97)], RING)  # band, row 36
    loft(P, [ell(36.95, 0.94), ell(41.95, 0.94)], CHAM)                              # body, rows 37-41
    loft(P, [ell(41.85, 0.97), ell(42.0, 0.985), ell(42.75, 0.985), ell(43.0, 0.88)], RING)  # band, row 42
    # longitudinal seam on the sleeve (sprite col 41, rows 32-35): a recessed strap line
    a = math.acos(max(-1.0, min(1.0, (41.4 - xc) / (rx * 0.95))))
    zz = zc + rz * 0.95 * math.sin(a)
    sx = 41.4
    loft(P, [[(sx - 0.3, y, zz - 0.06), (sx + 0.3, y, zz + 0.04), (sx + 0.3, y, zz + 0.14), (sx - 0.3, y, zz + 0.08)]
             for y in (32.4, 35.9)], SEAM)


def build_rods(P):
    for i, (x0, x1, y0, y1) in enumerate(RODS):
        xc, hw = (x0 + x1) / 2, (x1 - x0) / 2
        r0 = 1 if y0 == 1.6 else round(y0)

        def sec(y, k=1.0, notch=0.22, dip=0.0):
            return rod_section(xc, y, hw, RHH, RRC, k=k, notch=notch, dip=dip)
        # muzzle: recessed emitter, chamfered lip; the emitter trough runs back over the far end
        D = 0.5
        rings = [sec(y0 + 0.35, 0.6, dip=D), sec(y0 + 0.02, 0.6, dip=D), sec(y0 + 0.02, 0.82, dip=D),
                 sec(y0 + 0.55, dip=D), sec(r0 + 3.6, dip=D), sec(r0 + 4.4)]
        mats = [EMIT, FAR, FAR, FAR, FAR]
        zones = [(r0 + 5.0, FAR), (r0 + 20.0, GLOW), (y1 + 0.6, ROOT)]
        y = y0 + 0.55
        for zi, (ye, m) in enumerate(zones):
            if zi < 2:
                rings += [sec(ye - 0.2)]
                mats += [m]
                rings += [sec(ye, 0.93, notch=0.2), sec(ye + 0.2)]
                mats += [RGROOVE, RGROOVE]
            else:
                rings += [sec(ye)]
                mats += [m]
        loft(P, rings, mats)

        # The "E" marking: thin inlaid plates following the top surface.
        def deco(m, xa, xb, ya, yb):
            xs = [xa + (xb - xa) * k / 5 for k in range(6)]
            top = [(x, rod_top(x, xc, hw) + 0.05) for x in xs]

            def ring(yy):
                return [(x, yy, z) for x, z in top] + [(x, yy, z - 0.12) for x, z in reversed(top)]
            loft(P, [ring(ya), ring(yb)], m)
        deco(SPINE, x0 + 0.08, x0 + 1.0, r0 + 4.1, r0 + 14.9)
        deco(BARS, x0 + 1.0, x0 + 6.0, r0 + 6.05, r0 + 6.95)
        deco(BARS, x0 + 1.0, x0 + 4.0, r0 + 8.05, r0 + 8.95)
        deco(BARS, x0 + 1.0, x0 + 6.9, r0 + 14.05, r0 + 14.95)

        # Saddle under the cantilever at the slot mouth, with cheeks along the barrel's sides.
        edge_y = [21.6, 17.4, 14.6][i]
        block(P, x0 + 0.5, edge_y, x1 - 0.5, edge_y + 2.2, RZ - RHH + 0.15, PLD, ch=0.2)
        for cx0, cx1 in ((x0 - 0.75, x0 - 0.1), (x1 + 0.1, x1 + 0.75)):
            block(P, cx0, edge_y + 0.2, cx1, edge_y + 2.0, RZ + 0.2, PLD, ch=0.2)


def to_object(P, name, mats, coll, smooth_angle=34.0):
    bm = P.bm
    P.orient()
    for v in bm.verts:
        x, y, z = v.co
        v.co = Vector(((x - 24) / 12, (28 - y) / 12, z / 12))
    bmesh.ops.reverse_faces(bm, faces=bm.faces)  # the y flip mirrored the winding
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    return obj


def build(sprite, coll):
    mats = materials(sprite)
    P = Part()
    build_plinth(P)
    build_drum(P)
    build_ribs(P)
    build_rings(P)
    build_body(P)
    build_chamber(P)
    build_rods(P)
    return to_object(P, NAME, mats, coll), mats


# ----------------------------------------------------------------------------------------------
# Outline shell, hidden-face culling, split (copied from assembly-newsh4-124)
# ----------------------------------------------------------------------------------------------


def whole_shell(obj, coll, voxel=0.016, faces=1600, smooth=4):
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    coll.objects.link(shell)
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    common._apply_modifiers(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    seen, islands = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append(x)
            stack.extend(e.other_vert(x) for e in x.link_edges)
        islands.append(isl)

    def box(isl):
        return [min(v.co[k] for v in isl) for k in range(3)] + [max(v.co[k] for v in isl) for k in range(3)]
    boxes = [box(i) for i in islands]

    def within(a, b):
        return all(a[k] > b[k] + 1e-4 for k in range(3)) and all(a[k + 3] < b[k + 3] - 1e-4 for k in range(3))
    drop = set()
    for i, a in enumerate(boxes):
        if len(islands[i]) < 12 or any(within(a, b) for j, b in enumerate(boxes) if j != i):
            drop.update(v.index for v in islands[i])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index in drop], context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    common._apply_modifiers(shell)
    return shell


def split_open(obj, layout, coll, suffix):
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


def cull_hidden(obj, grid=3, ndirs=40):
    """Delete faces no ray from outside reaches (buried plate bottoms, overlaps)."""
    from mathutils.bvhtree import BVHTree
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    eps = 2e-4
    dead = []
    for f in bm.faces:
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    u, v = (i + 0.5) / grid, (j + 0.5) / grid
                    pts.append(vs[0].lerp(vs[1], u).lerp(vs[3].lerp(vs[2], u), v))
        else:
            for vco in vs:
                for t in (0.35, 0.7, 0.92):
                    pts.append(c.lerp(vco, t))
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * eps
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    print(f"{NAME}: culled {len(dead)} hidden faces of {len(bm.faces)}")
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    sprite = merged_sprite()
    obj, mats = build(sprite, coll)
    bpy.context.view_layer.update()
    shell = whole_shell(obj, coll)
    cull_hidden(obj)
    cx0, cy0 = X0 + 24, Y0 + 28
    layout = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    shells = split_open(shell, layout, coll, "_outline")
    outline_mat = bpy.data.materials.get("outline_shell") or common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    for s in shells.values():
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
    pieces = common.split_assembly(obj, layout)
    tri = 0
    for p in pieces.values():
        # The cut caps are new faces at 90 deg to the surface they close: mark those edges sharp
        # again, or the weighted normals lean the surface beside a cut towards the big cap (rod 1's
        # glow zone crosses the cut at y 28 and showed a mirror-like streak).
        p.data.shade_smooth()
        p.data.set_sharp_from_angle(angle=math.radians(34.0))
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        p.data.calc_loop_triangles()
        tri += len(p.data.loop_triangles)
    print(f"{NAME}: triangles (pieces, no shells) {tri}; shell faces {sum(len(s.data.polygons) for s in shells.values())}")
    if "--no-export" not in argv:
        for name in PIECES:
            data = common.load_sprite(GAME_ROOT, name)
            extra = [shells[name]] if len(shells[name].data.polygons) else []
            common.export_sprite_model(GAME_ROOT, [pieces[name]] + extra, f"enemies/{name}", data["sprites"])
    if "--design-out" in argv:
        # Review export: one .glb with every piece back in assembly space.
        out = Path(argv[argv.index("--design-out") + 1])
        export = []
        for name, cx, cy in layout:
            for o in [pieces[name]] + ([shells[name]] if len(shells[name].data.polygons) else []):
                o.location = (cx / 12, -cy / 12, 0)
                o["tyrian_piece"] = name
                export.append(o)
        common.export_glb(export, out)
        for o in export:
            o.location = (0, 0, 0)
        print(f"design export {out}")
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        for o in list(pieces.values()) + list(shells.values()):
            o.hide_render = True
        shell.hide_render = True
        common.render_preview([obj], str(out), None, size=(48, 56), view_px=480)


if __name__ == "__main__":
    main()
