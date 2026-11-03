"""Purple eye fortress (newsh2.shp frames 245, 169, 207 side by side): a 3D version of its sprites.

Seen in levels 1.30 and 3.17. Three 2x2 enemies in a row make one 72 x 28 px block set into grey
rock (sprite.json `assemblyLayout`): two octagonal armour hatches (enemy types 38 and 39, pieces
newsh2-245 and newsh2-207) and between them the eye turret (type 41, 20 armour, piece newsh2-169):
a dark blue glass eye in a steel socket on a segmented collar, two glowing blue capsule lights and
a grille below it, with island rock and sand at both ends.

A hard-surface rebuild in the manner of the USP Talon (D50-D53). Every part is drawn in sprite
pixels (column c / row r as pixel EDGES of the 72 x 28 grid, z up in px, 1 px = 1/12 unit) as a
separate chamfered armour block standing on a dark casemate deck, so the sprite's dark seams are
real gaps showing the deck (palette 87, the median of the sprite's seam pixels).

Sprite authority (tools/calibration/rubric.md):
- Outline: the casemate and its hatches; the rock ends (cols 0-12 and 61-71 round the hatches) are
  island rock, the sprite's own pixels as the islands' relief (lib_tiles.sprite_rock, DECISIONS.md
  D66), one rock object per piece with no outline and no shadow, so the fortress stands in the
  island rather than in a rimmed block; the sprite's few transparent pixels in the right-hand rock
  (cols 61-64 rows 20-26, cols 68-69 rows 14-15) are holes in it, showing the island below.
- Features at the sprite's pixel edges: octagons cols 3-20 / 52-69, rows 4-20 (mirrored, as the
  sprite draws them); eye centre (36, 11), steel socket 15 x 12 px, glass 13 x 11 px, clamp at
  rows 5-6; capsule lights from (25.6, 16.6) to (30.8, 22.6) and (46.3, 17.1) to (41.5, 22.5) with
  steel end caps; grille cols 32.5-40.5 rows 18-24 with bars at cols 33, 35, 37, 39.
- Colours: each part's palette index is the trimmed median of the sprite pixels over it; the rock
  takes the islands' colours of the sprite pixels it covers. Satin metal, glass low roughness. Bright
  spots on the eye and plates are sheen: no geometry for them.

Profile: the rear band is a parapet sloping 2.4 -> 3.2 px toward the eye, the front band a glacis
falling to 2 px at the player-side wall, and the deck's long front and rear walls lean back 0.7 px
(a casemate seen from the tilted game camera). The hatches' backing plates sink into the rock.
The rock's dark gaps are at z = 0.
Underside: a flat closed belly at z = -4 px; no detail.

No concept projection bake (maps.json says "bake": "model", so texture_bake.py skips it, as the
player ships in D50-D53). Unless --no-bake, an ambient occlusion / edge colour multiplier and a
roughness-metalness map are baked and multiplied into the palette materials.

Game contract: palette materials pal_<index>_nsh2a245; the three pieces newsh2-245 / -169 / -207 cut
from one build with common.split_assembly at the layout's centres (pivots = piece centres), each
exported as enemies/<piece> with its own spriteModels entry and its one sprite frame, plus an
outline shell per piece (common.outline_shell, D51, cut without capping) round the machine only, and
the piece's rock.

    blender --background --factory-startup --python assets/blender/enemies/assembly-newsh2-245.py -- \
        [--no-bake] [--preview out.png]
(the preview is the whole block; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent),
                str(Path(__file__).resolve().parents[1] / "tiles")]
import common  # noqa: E402
import lib_b053 as lib  # noqa: E402
import lib_tiles as lt  # noqa: E402

NAME = "assembly-newsh2-245"
ROOT = common.repo_root(__file__)
TAG = "nsh2a245"
W, H = 72, 28
BELLY = -4.0  # px
DECK = 1.0  # top of the casemate deck (px); the seams between plates show it
SHELL_TRIS = 900  # outline shell triangles per piece at most
LEAN = 0.7  # px the deck's front and rear walls lean back from top to belly

OCT_L = [(8.0, 4.0), (18.4, 4.0), (20.2, 5.8), (20.2, 15.0), (15.6, 20.0), (8.0, 20.0), (3.0, 15.0), (3.0, 9.0)]


def V(c, r, z):
    """Pixel-edge column, row and height in px to Blender units."""
    return Vector(((c - W / 2) / 12, (H / 2 - r) / 12, z / 12))


def area2(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))


def inset(pts, d):
    """Inset an outline given in (c, r) px by d px."""
    # lib.inset works in a y-up frame; flip rows so the winding sense is right.
    q = lib.inset([(c, -r) for c, r in pts], d)
    return [(c, -r) for c, r in q]


def mirror(pts):
    return [(W - c, r) for c, r in reversed(pts)]


def rect(c0, r0, c1, r1):
    return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]


class Builder:
    def __init__(self):
        self.bm = bmesh.new()

    def _done(self, first, mat, smooth=False):
        self.bm.faces.ensure_lookup_table()
        for f in self.bm.faces[first:]:
            f.material_index = mat
            f.smooth = smooth

    def cprism(self, pts, z0, top, mat, ch=0.4, chh=None, top_mat=None, base_shift=(0.0, 0.0), base=None):
        """A chamfered block over a convex outline (c, r px) from z0 up to top (px, or a function
        top(c, r) for sloped glacis tops); the top edge is chamfered ch px in and chh px down. The
        base ring is moved by base_shift (c, r px) or replaced by `base` (a leaning wall)."""
        bm = self.bm
        first = len(bm.faces)
        topf = top if callable(top) else (lambda c, r, t=top: t)
        chh = ch if chh is None else chh
        flip = area2([(c, -r) for c, r in pts]) < 0
        if flip:
            pts = list(reversed(pts))
            if base is not None:
                base = list(reversed(base))
        inn = inset(pts, ch) if ch > 0 else pts
        bpts = base if base is not None else [(c + base_shift[0], r + base_shift[1]) for c, r in pts]
        lo = [bm.verts.new(V(c, r, z0)) for c, r in bpts]
        mid = [bm.verts.new(V(c, r, topf(c, r) - chh)) for c, r in pts]
        hi = [bm.verts.new(V(c, r, topf(c, r))) for c, r in inn]
        bm.faces.new(list(reversed(lo)))
        tf = bm.faces.new(hi)
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((lo[i], lo[j], mid[j], mid[i]))
            if ch > 0:
                bm.faces.new((mid[i], mid[j], hi[j], hi[i]))
        self._done(first, mat)
        if top_mat is not None:
            tf.material_index = top_mat
        return tf

    def lathe(self, cx, cy, sx, sy, prof, mat, segs=32, smooth=True, closed=True):
        """Surface of revolution about the vertical axis through (cx, cy): prof is a list of
        (radius px, z px), revolved on an ellipse squashed sx, sy. closed=True joins the profile's
        ends (a ring with a solid section); a radius-0 point is a pole."""
        bm = self.bm
        first = len(bm.faces)
        rings = []
        for rad, z in prof:
            if rad <= 1e-9:
                rings.append([bm.verts.new(V(cx, cy, z))] * segs)
                continue
            rings.append([bm.verts.new(V(cx + sx * rad * math.cos(2 * math.pi * k / segs),
                                         cy - sy * rad * math.sin(2 * math.pi * k / segs), z))
                          for k in range(segs)])
        n = len(prof)
        for i in range(n if closed else n - 1):
            r0, r1 = rings[i], rings[(i + 1) % n]
            for k in range(segs):
                j = (k + 1) % segs
                f = []
                for v in (r0[k], r0[j], r1[j], r1[k]):
                    if v not in f:
                        f.append(v)
                if len(f) >= 3:
                    bm.faces.new(f)
        if not closed:
            for ring in (rings[0], rings[-1]):
                if len(set(ring)) > 1:
                    bm.faces.new(ring)
        self._done(first, mat, smooth)
        return first

    def tube(self, p0, p1, rad, mat, z, sides=14, ends=0.0, smooth=True, squash=1.0):
        """A capsule/cylinder from p0 to p1 (c, r px) at height z px with radius rad px; `ends` > 0
        rounds each end with a cap of ends * rad length."""
        (c0, r0), (c1, r1) = p0, p1
        L = math.hypot(c1 - c0, r1 - r0)
        u = ((c1 - c0) / L, (r1 - r0) / L)
        if ends > 0:
            n = 4
            prof = [(rad * ends * (1 - math.sin(math.pi / 2 * k / n)), math.sin(math.pi / 2 * k / n)) for k in range(n + 1)]
            fwd = prof + [(L - d, s) for d, s in reversed(prof)]
        else:
            fwd = [(0, 1), (L, 1)]
        path = []
        for d, s in fwd:
            p = V(c0 + u[0] * d, r0 + u[1] * d, z)
            path.append((p.x, p.y, p.z, rad * s / 12, rad * s * squash / 12))
        first = len(self.bm.faces)
        lib.sweep(self.bm, path, sides=sides, mat=mat, smooth=smooth)
        return first


def build(sprite, grid, coll):
    mats, slot = [], {}

    def mat(idx, metallic, rough, emis=0.0):
        slot[idx] = len(mats)
        mats.append(common.palette_material(sprite, idx, TAG, metallic=metallic, roughness=rough,
                                            emission_strength=emis))

    for i in (85, 86, 87):
        mat(i, 0.3, 0.55)
    for i in (88, 89, 90, 91, 93):
        mat(i, 0.35, 0.42)
    mat(52, 0.1, 0.16)  # glass eye: satin sheen, not a mirror
    mat(101, 0.35, 0.38)
    mat(102, 0.35, 0.38)
    mat(103, 0.35, 0.4)
    mat(55, 0.0, 0.2, emis=1.6)  # capsule light
    S = slot
    B = Builder()
    bm = B.bm

    # ---------------- casemate deck ----------------
    # The purple body under all the plates: cols 12.4-61, full depth, in the sprite's seam colour
    # (87); its long front and rear walls lean back LEAN px from top to belly.
    deck = [(12.4, 0.0), (61.0, 0.0), (61.0, 28.0), (12.4, 28.0)]
    B.cprism(deck, BELLY, DECK, S[87], ch=0.3,
             base=[(12.4, LEAN), (61.0, LEAN), (61.0, 28.0 - LEAN), (12.4, 28.0 - LEAN)])

    def wall_r(z, front):
        """Row of the leaning deck wall at height z px."""
        t = (DECK - z) / (DECK - BELLY) * LEAN
        return 28.0 - t if front else t

    # ---------------- rear band (rows 0-4): parapet sloping up toward the eye ----------------
    rear_top = lambda zr, zf: (lambda c, r: zr + (zf - zr) * min(1.0, max(0.0, r / 4.2)))  # noqa: E731
    for a, b, p in ((13.0, 19.4, 89), (19.9, 28.2, 88)):
        for f in (False, True):
            pts = rect(a, 0.0, b, 4.1)
            B.cprism(mirror(pts) if f else pts, 0.5, rear_top(2.4, 3.2), S[p if not f or p != 89 else 90], ch=0.5)
    # vent slots in the shoulder panels (cols 21-27): dark louvres sunk in the plate
    for f in (False, True):
        for r in (1.2, 2.3):
            pts = rect(21.2, r, 27.0, r + 0.6)
            B.cprism(mirror(pts) if f else pts, 2.0, rear_top(2.55, 3.35), S[85], ch=0.1)
    B.cprism(rect(28.6, 0.0, 43.4, 1.6), 0.5, 2.6, S[90], ch=0.4)

    # ---------------- beams between the hatches and the collar ----------------
    beam_u = [(20.6, 4.5), (25.7, 4.5), (25.7, 11.4), (20.6, 11.4)]
    beam_l = [(20.6, 11.9), (25.7, 11.9), (25.7, 16.2), (24.3, 22.7), (20.6, 22.7)]
    for f in (False, True):
        B.cprism(mirror(beam_u) if f else beam_u, 0.5, 3.6, S[90], ch=0.5)
        B.cprism(mirror(beam_l) if f else beam_l, 0.5, 3.3, S[89], ch=0.5)
        # a machined rib down the upper beam
        rib = rect(22.6, 5.6, 23.6, 10.4)
        B.cprism(mirror(rib) if f else rib, 3.0, 4.0, S[91], ch=0.3)

    # ---------------- front band (rows 20-28): glacis sloping toward the player ----------------
    def glacis(zb, zf, r0):
        return lambda c, r: zb + (zf - zb) * min(1.0, max(0.0, (r - r0) / (28 - r0)))
    fl1 = [(12.4, 20.4), (18.3, 20.4), (19.9, 22.0), (19.9, 28.0), (12.4, 28.0)]
    fl2 = [(20.3, 24.6), (21.5, 23.2), (27.4, 23.2), (28.6, 24.6), (28.6, 28.0), (20.3, 28.0)]
    for f, (p1, p2) in ((False, (89, 88)), (True, (90, 88))):
        B.cprism(mirror(fl1) if f else fl1, 0.5, glacis(3.8, 2.0, 20.4), S[p1], ch=0.5)
        B.cprism(mirror(fl2) if f else fl2, 0.5, glacis(3.1, 2.0, 23.2), S[p2], ch=0.5)
    B.cprism(rect(28.9, 25.3, 43.1, 28.0), 0.5, glacis(2.9, 2.0, 25.3), S[89], ch=0.4)
    # panel lines and fasteners on the glacis blocks (thin dark strips riding the sloped tops)
    for f in (False, True):
        g1 = glacis(3.8, 2.0, 20.4)
        strip = rect(13.4, 24.6, 18.9, 25.0)
        B.cprism(mirror(strip) if f else strip, 0.5, lambda c, r: g1(c, r) + 0.06, S[86], ch=0.0)
        for c, r in ((14.0, 21.6), (18.3, 26.8), (14.0, 26.8)):
            cc = W - c if f else c
            B.lathe(cc, r, 1, 1, [(0.0, 0.5), (0.4, 0.5), (0.4, g1(c, r) + 0.3), (0.0, g1(c, r) + 0.3)], S[87],
                    segs=6, smooth=False)
        for c, r in ((22.3, 13.4), (22.3, 21.2)):
            cc = W - c if f else c
            B.lathe(cc, r, 1, 1, [(0.0, 0.5), (0.4, 0.5), (0.4, 3.6), (0.0, 3.6)], S[87], segs=6, smooth=False)
    # front wall vents (seen by the game camera): dark slot plates on the leaning front wall
    z0v, z1v = -2.8, -0.6
    for c in (15.0, 17.5, 31.0, 34.0, 38.0, 41.0, 54.5, 57.0):
        rt = wall_r(z1v, True)
        rb = wall_r(z0v, True)
        B.cprism(rect(c - 0.9, rt - 0.5, c + 0.9, rt + 0.12), z0v, z1v, S[85], ch=0.1,
                 base_shift=(0.0, rb - rt))
    # buttress ribs on the front and rear walls between the vents, leaning with the walls
    zb0, zb1 = BELLY + 0.4, 0.9
    for c in (13.6, 20.0, 24.3, 28.7, 36.0, 43.3, 47.7, 52.0, 58.6):
        for front in (True, False):
            rt, rb = wall_r(zb1, front), wall_r(zb0, front)
            r0, r1 = (rt - 0.45, rt) if front else (rt, rt + 0.45)
            B.cprism(rect(c - 0.55, r0, c + 0.55, r1), zb0, zb1, S[86], ch=0.15, base_shift=(0.0, rb - rt))

    # ---------------- octagonal armour hatches (types 38 and 39) ----------------
    for f in (False, True):
        o = mirror(OCT_L) if f else OCT_L
        B.cprism(o, -2.6, 4.4, S[88], ch=0.7)  # backing plate, its foot sunk into the rock
        face = inset(o, 1.1)
        B.cprism(face, 3.6, 6.0, S[88], ch=1.1, chh=0.9)  # raised face, broad chamfer
        mc = sum(c for c, _ in o) / len(o)
        mr = sum(r for _, r in o) / len(o)
        inner = [(mc + (c - mc) * 0.66, mr + (r - mr) * 0.66) for c, r in o]
        B.cprism(inner, 5.6, 6.5, S[88], ch=0.4)  # inner armour panel
        # corner bolts on the face
        for c, r in inset(o, 2.35):
            B.lathe(c, r, 1, 1, [(0.0, 5.7), (0.42, 5.7), (0.42, 6.35), (0.0, 6.35)], S[87],
                    segs=6, smooth=False, closed=True)

    # ---------------- eye collar (type 41) ----------------
    collar = [(30.0, 1.0), (42.0, 1.0), (45.6, 4.4), (45.6, 14.4), (42.8, 17.2), (29.2, 17.2), (26.4, 14.4), (26.4, 4.4)]
    B.cprism(collar, 0.5, 4.2, S[88], ch=0.9)
    cx, cy = 36.0, 11.0
    # segmented armour ring round the socket (8 plates, split into convex quads)
    for k in range(8):
        a0 = math.radians(22.5 + 45 * k + 3.2)
        a1 = math.radians(22.5 + 45 * (k + 1) - 3.2)
        R0, R1, sq = 7.0, 8.7, 0.84
        o = [(cx + R1 * math.cos(a0 + (a1 - a0) * s / 3), cy + sq * R1 * math.sin(a0 + (a1 - a0) * s / 3)) for s in range(4)]
        i_ = [(cx + R0 * math.cos(a0 + (a1 - a0) * s / 3), cy + sq * R0 * math.sin(a0 + (a1 - a0) * s / 3)) for s in range(4)]
        for s in range(3):
            B.cprism([o[s], o[s + 1], i_[s + 1], i_[s]], 3.6, 5.0, S[88], ch=0.25)
    # steel socket ring (sprite 101-103) with a lip, matched to the sprite's 15 x 12 px ring
    B.lathe(cx, cy, 1.0, 0.86, [(5.9, 3.8), (7.6, 3.8), (7.6, 4.9), (7.25, 5.6), (6.35, 5.75), (5.95, 5.3)],
            S[102], segs=40, smooth=True)
    # clamp at the top of the ring and two lower lugs (sprite rows 5 and 16)
    B.cprism(rect(34.8, 4.4, 37.3, 6.0), 4.2, 6.6, S[103], ch=0.3)
    for c in (32.2, 39.8):
        B.cprism(rect(c - 0.9, 15.6, c + 0.9, 16.8), 4.0, 5.8, S[101], ch=0.25)
    # the glass eye: a dark blue lens dome
    prof = []
    for k in range(10):
        a = (math.pi / 2) * k / 9
        prof.append((6.15 * math.cos(a), 5.0 + 4.0 * math.sin(a)))
    prof = [(0.0, 4.6), (6.15, 4.6)] + prof
    prof[-1] = (0.0, prof[-1][1])  # pole at the top
    B.lathe(cx, cy, 1.0, 0.86, prof, S[52], segs=36, smooth=True, closed=False)

    # ---------------- chin plate and grille ----------------
    chin_l = [(30.2, 17.6), (32.5, 17.6), (32.5, 25.3), (29.4, 25.3), (28.6, 24.4), (28.6, 19.2)]
    B.cprism(chin_l, 0.5, 3.4, S[86], ch=0.5)
    B.cprism(mirror(chin_l), 0.5, 3.4, S[86], ch=0.5)
    B.cprism(rect(32.5, 24.2, 39.5, 25.3), 0.5, 3.4, S[86], ch=0.4)
    B.cprism(rect(32.5, 17.6, 39.5, 19.0), 0.5, 3.8, S[91], ch=0.35)  # grille frame top (sprite 91-93)
    B.cprism(rect(32.5, 19.0, 39.5, 24.2), 0.5, 1.6, S[85], ch=0.0)  # dark recess
    for c in (33, 35, 37, 39):
        B.cprism(rect(c + 0.1, 19.0, c + 0.9, 24.2), 0.5, 3.1, S[90], ch=0.25)

    # ---------------- capsule lights ----------------
    caps = (((25.6, 16.6), (30.8, 22.6)), ((46.3, 17.1), (41.5, 22.5)))
    for p0, p1 in caps:
        B.tube(p0, p1, 1.95, S[86], 2.0, sides=12, ends=1.0, smooth=True, squash=0.75)  # socket
        B.tube(p0, p1, 1.45, S[55], 3.0, sides=14, ends=1.0, smooth=True)  # glowing pill
        (c0, r0), (c1, r1) = p0, p1
        L = math.hypot(c1 - c0, r1 - r0)
        ux, uy = (c1 - c0) / L, (r1 - r0) / L
        for d0, d1 in ((-0.35, 1.2), (L - 1.2, L + 0.35)):
            B.tube((c0 + ux * d0, r0 + uy * d0), (c0 + ux * d1, r0 + uy * d1), 1.65, S[102], 3.0, sides=14)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj, mats, slot


# ---------------------------------------------------------------------------------------------
# Finishing: cull hidden faces, bake, split, outline shell, export
# ---------------------------------------------------------------------------------------------

def cull_hidden(obj, ndirs=32, n=4):
    """Delete faces no ray from outside reaches (usp_talon.cull_hidden, but sampling each face
    densely over its fan triangles, so a thin visible strip of a big n-gon, such as the ledge of a
    backing plate round the plate on it, keeps its face)."""
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
        nrm = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        for k in range(1, len(vs) - 1):
            a, b, d = vs[0], vs[k], vs[k + 1]
            for i in range(n + 1):
                for j in range(n + 1 - i):
                    u, w = i / n, j / n
                    p = a + (b - a) * u + (d - a) * w
                    pts.append(p.lerp(c, 0.04))
        cand = [d for d in dirs if d.dot(nrm) > 0.05]
        seen = False
        for p in pts:
            o = p + nrm * eps
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


def bake_maps(obj, out_dir, skip=(), size=1024, samples=64):
    """usp_talon.bake_maps: Smart UV, Cycles bake of an occlusion/edge colour multiplier and a
    roughness/metallic map, wired into the palette materials (Base Color = map x palette)."""
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
    except Exception as err:
        print(f"{NAME}: no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{TAG}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{TAG}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, bb=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, bb)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.04
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.25
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            nt.links.new(v, em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    for m in mats:
        if m in skip:
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


def split_open(obj, layout, coll, suffix):
    """split_assembly without capping the cuts (for the outline shells)."""
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


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    grid, colors, x0, y0, layout = lib.assembly_grid(ROOT, "newsh2-245")
    sprite = common.load_sprite(ROOT, "newsh2-245")
    sprite["colors"] = colors
    coll = common.reset_collection(NAME)
    obj, mats, slot = build(sprite, grid, coll)
    cx0, cy0 = x0 + W // 2, y0 + H // 2
    pieces_layout = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in layout]
    # The island rock round the machine (D66); in its place in the row, so the bake sees it.
    rocks = lt.build_sprite_rock(ROOT, [obj], pieces_layout, W, H, coll, "a245rock", grid=grid)
    for name, cx, cy in pieces_layout:
        rocks[name].location = (cx / 12, -cy / 12, 0)
    # The outline shell (D51) comes from the closed, unculled build: the voxel remesh of an open
    # mesh drops parts (the eye dome, the rock's outer end).
    src = obj.copy()
    src.data = obj.data.copy()
    coll.objects.link(src)
    shell = common.outline_shell(src, coll, voxel=0.014, faces=1800)
    shell.hide_render = True
    bpy.data.objects.remove(src)
    cull_hidden(obj)

    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        shell.hide_set(True)  # so the bake's occlusion rays never hit it
        bake_maps(obj, tempfile.mkdtemp(prefix=f"{TAG}_bake_"), skip=(mats[slot[55]],))
        shell.hide_set(False)
        fmt = "WEBP"
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: whole {len(obj.data.polygons)} faces, {tris} triangles")

    pieces = common.split_assembly(obj, pieces_layout, coll)
    shells = split_open(shell, pieces_layout, coll, "_outline")
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    for name, cx, cy in pieces_layout:
        p = pieces[name]
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        s = shells[name]
        st = sum(len(q.vertices) - 2 for q in s.data.polygons)
        if st > SHELL_TRIS:  # keep each piece's shell small
            dec = s.modifiers.new("decimate", "DECIMATE")
            dec.ratio = SHELL_TRIS / st
            common._apply_modifiers(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        s.hide_render = True
        rk = rocks[name]
        rk.location = (0, 0, 0)
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [p, s, rk], f"enemies/{name}", data["sprites"], image_format=fmt)
        pt = sum(len(q.vertices) - 2 for q in p.data.polygons)
        st = sum(len(q.vertices) - 2 for q in s.data.polygons)
        rt = sum(len(q.vertices) - 2 for q in rk.data.polygons)
        print(f"{NAME}: piece {name} at ({cx}, {cy}) px: {pt} triangles; shell {st} triangles; rock {rt} triangles")

    out = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    if out:
        import tempfile
        out = Path(out)
        ref = lib.composite_png(grid, colors, Path(tempfile.mkdtemp()) / "assembly.png", pad_to=(W, H))
        for name, cx, cy in pieces_layout:
            rocks[name].location = (cx / 12, -cy / 12, 0)
        common.render_preview([obj, *rocks.values()], str(out), str(ref), size=W / 12, view_px=640)
        for name, _, _ in pieces_layout:
            rocks[name].location = (0, 0, 0)
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name], rocks[name]], str(out.parent / f"{name}.png"), img, size=2)
    return dict(obj=obj, pieces=pieces, shells=shells, rocks=rocks, grid=grid, layout=pieces_layout, mats=mats)


if __name__ == "__main__":
    main()
