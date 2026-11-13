"""assembly-newshg-191: a steel launch hatch set into the foot of a rock cliff.

newshg-153 over newshg-191 (24x56 px), a fixed ground structure flanking the waterfall in TORM and
BOTANY A/B. Built as WHAT IT IS (D120/D122): a real rock outcrop whose south face is a steep cliff,
with a steel portal (lintel, posts, sill, header beam) set into its foot, a shutter that slides up in
guide tracks into a slot in the lintel, a dark launch bay behind it with a burner on its floor whose
fire glows (emissive, D126), two rock spurs running down from the face to the grass, a half-buried
boulder and a pile of dark rocks in front. The grass is ground (D130): no floor plate.

It stands (D82): the cliff is 22 px tall, so the art's oblique view (1 px up the screen per px of
height, screen row s = v - h) is what the sprite shows. Every view is projected from one true model.
Its back slopes down north at a little under 45 degrees (v - h >= 0.5), so it is a real outcrop from
the side and the rear and nothing of it pokes above the sprite's top row in the art view.

Coordinates while building: sprite px, c = column (east), v = plan row (south), h = height.
Blender: X = (c - 12) / 12, Y = (28 - v) / 12, Z = h / 12 (assembly centre at the origin).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshg-191.py
  or blender --background --python assembly-newshg-191.py -- [--out DIR] [--no-render]
Exports the 7 game models through common.export_sprite_model: public/models/enemies/newshg-153.glb,
-f2, -f3, -f4 (the top piece) and newshg-191.glb, -f2, -f3 (the bottom piece), each with its
src/render/spriteModels entry. Each root carries tyrian_oblique 1 (D82) and the cliff-wide
tyrian_depth_band [0, 0.4, 0, top] (D165), so both pieces' depths agree at the seam. The outline
shell comes from a sealed copy (bay and crevice plugged), held inside the rock: ink on the silhouette only.
With --out DIR it also measures the art-view IoU and per-region colour per frame
(DIR/work/metrics.json, which needs DIR/work/sprite_data.json) and renders the review views into
DIR/work/; without --out it only exports.
"""

import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)
ROOT = WT

NAME = "assembly-newshg-191"
TAG = "ng191"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None  # no --out: export only
WORK = OUT / "work" if OUT else None
if WORK:
    WORK.mkdir(parents=True, exist_ok=True)
RENDER = WORK is not None and "--no-render" not in argv

S = 1 / 12  # units per px


def P(c, v, h):
    return Vector(((c - 12) * S, (28 - v) * S, h * S))


# ---------------------------------------------------------------------------------------------
# Sprite data and materials
# ---------------------------------------------------------------------------------------------
TOP = common.load_sprite(WT, "newshg-153")
BOT = common.load_sprite(WT, "newshg-191")
MERGED = {"name": "newshg-153+191", "colors": {**TOP["colors"], **BOT["colors"]}}

ROCK, STEEL, GLOW = "rock", "steel", "glow"


class Mats:
    """Material slots per object: (palette index, kind, emission) -> slot."""

    def __init__(self):
        self.list, self.slot = [], {}

    def __call__(self, pal, kind=ROCK, emit=0.0):
        key = (pal, kind, emit)
        if key not in self.slot:
            if kind == ROCK:
                m = common.palette_material(MERGED, pal, f"{TAG}_rock", metallic=0.0, roughness=0.88)
            elif kind == STEEL:
                m = common.palette_material(MERGED, pal, f"{TAG}_steel", metallic=0.55, roughness=0.42)
            else:
                m = common.palette_material(MERGED, pal, f"{TAG}_glow{str(emit).replace('.', '')}", metallic=0.0,
                                            roughness=0.6, emission_strength=emit)
            self.slot[key] = len(self.list)
            self.list.append(m)
        return self.slot[key]


class Builder:
    def __init__(self, name):
        self.name, self.bm, self.M = name, bmesh.new(), Mats()

    def _new_faces(self, before, mat):
        new = [f for f in self.bm.faces if f not in before]
        for f in new:
            f.material_index = mat
            f.smooth = False
        return new

    def chbox(self, c0, c1, v0, v1, h0, h1, mat, ch=0.0):
        """Box over px ranges, its edges chamfered by `ch` px."""
        bm = self.bm
        before = set(bm.faces)
        ret = bmesh.ops.create_cube(bm, size=1.0)
        vs = ret["verts"]
        lo, hi = P(c0, v1, h0), P(c1, v0, h1)
        for v in vs:
            v.co = Vector((lo.x if v.co.x < 0 else hi.x, lo.y if v.co.y < 0 else hi.y, lo.z if v.co.z < 0 else hi.z))
        if ch > 0:
            edges = list({e for v in vs for e in v.link_edges})
            bmesh.ops.bevel(bm, geom=vs + edges, offset=ch * S, segments=1, profile=0.5, affect="EDGES",
                            clamp_overlap=True)
        return self._new_faces(before, mat)

    def hull(self, pts, mat):
        """Convex hull of px points: a faceted rock chunk."""
        bm = self.bm
        before = set(bm.faces)
        vs = [bm.verts.new(P(*p)) for p in pts]
        ret = bmesh.ops.convex_hull(bm, input=vs)
        drop = list({g for g in ret["geom_interior"] + ret["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        bmesh.ops.delete(bm, geom=drop, context="VERTS")
        return self._new_faces(before, mat)

    def rock(self, ctr, rad, seed, mat, n=30, jitter=0.22, flat=None):
        """A faceted boulder: hull of jittered points on an ellipsoid (px)."""
        rnd = random.Random(seed)
        pts = []
        for i in range(n):
            z = 1 - 2 * (i + 0.5) / n
            r = math.sqrt(max(0.0, 1 - z * z))
            a = i * 2.39996 + rnd.uniform(-0.3, 0.3)
            k = 1 - rnd.uniform(0, jitter)
            pts.append((ctr[0] + rad[0] * r * math.cos(a) * k, ctr[1] + rad[1] * r * math.sin(a) * k,
                        ctr[2] + rad[2] * z * k))
        if flat is not None:
            pts = [(c, v, max(flat, h)) for c, v, h in pts]
        return self.hull(pts, mat)

    def block(self, c0, c1, v0, v1, h0, h1, seed, mat, j=0.5):
        """A rough-hewn stone block: hull of its jittered corners and edge points."""
        rnd = random.Random(seed)
        pts = []
        for c in (c0, (c0 + c1) / 2, c1):
            for v in (v0, v1):
                for h in (h0, (h0 + h1) / 2, h1):
                    jc = rnd.uniform(0, j) * (1 if c == c0 else -1 if c == c1 else rnd.uniform(-0.5, 0.5))
                    jv = rnd.uniform(0, j) * (1 if v == v0 else -1)
                    jh = rnd.uniform(0, j) * (1 if h == h0 else -1 if h == h1 else rnd.uniform(-0.5, 0.5))
                    pts.append((c + jc, v + jv, h + jh))
        return self.hull(pts, mat)

    def facets(self, c0, c1, v0, v1, h0, h1, seed, mat, nc=2, nh=2, lean=1.0, bump=0.6):
        """A rock face block broken into nc x nh chunks, each front leaning back toward its top and
        raised in a ridge, so its big flat face becomes angled facets that catch the light."""
        rnd = random.Random(seed)
        # a backing in the block's colour, so the joints between chunks show its rock, not the massif's
        self.chbox(c0 + 0.1, c1 - 0.1, v0, v1 - 0.35, h0, h1 - 0.3, mat)
        cs = [c0] + sorted(rnd.uniform(c0 + (c1 - c0) * (i + 0.3) / nc, c0 + (c1 - c0) * (i + 0.7) / nc)
                           for i in range(1, nc)) + [c1]
        hs = [h0] + sorted(rnd.uniform(h0 + (h1 - h0) * (i + 0.25) / nh, h0 + (h1 - h0) * (i + 0.75) / nh)
                           for i in range(1, nh)) + [h1]
        for i in range(nc):
            for k in range(nh):
                a, b, lo, hi = cs[i], cs[i + 1], hs[k], hs[k + 1]
                ln = lean * rnd.uniform(0.5, 1.2)
                front = v1 - rnd.uniform(0.0, 0.3)
                pts = []
                for c in (a, b):
                    for h in (lo, hi):
                        pts.append((c, v0, h))
                        t = (h - lo) / (hi - lo)
                        pts.append((c + rnd.uniform(-0.15, 0.15), front - ln * t - rnd.uniform(0, 0.3),
                                    h + rnd.uniform(-0.25, 0.1)))
                # the ridge: a point proud of the front, off centre, splitting it into 3-4 facets
                rc = a + (b - a) * rnd.uniform(0.3, 0.7)
                rh = lo + (hi - lo) * rnd.uniform(0.35, 0.65)
                pts.append((rc, front - ln * 0.5 + bump * rnd.uniform(0.6, 1.2), rh))
                # a chipped top edge
                pts.append((a + (b - a) * rnd.uniform(0.2, 0.8), front - ln - rnd.uniform(0.2, 0.6), hi + rnd.uniform(0.0, 0.3)))
                self.hull(pts, mat)

    def prism_c(self, poly_vh, c0, c1, mat):
        """A (v, h) polygon extruded along c (a slice of the massif)."""
        bm = self.bm
        before = set(bm.faces)
        a = [bm.verts.new(P(c0, v, h)) for v, h in poly_vh]
        b = [bm.verts.new(P(c1, v, h)) for v, h in poly_vh]
        n = len(a)
        bm.faces.new(a[::-1])
        bm.faces.new(b)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
        return self._new_faces(before, mat)

    def ellip(self, ctr, rad, mat, seg=18, rings=10, taper=0.0, zmin=None, noise=0.0, noise_seed=0.0):
        """A smooth ellipsoid (flame), its top tapered to a tongue by `taper`."""
        bm = self.bm
        before = set(bm.faces)
        ret = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
        for v in ret["verts"]:
            x, y, z = v.co
            k = 1 - taper * max(0.0, z)
            c = ctr[0] + rad[0] * x * k
            vv = ctr[1] - rad[1] * y * k
            h = ctr[2] + rad[2] * z
            if zmin is not None:
                h = max(zmin, h)
            if noise:
                a = math.atan2(y, x)
                f = 1 + noise * (math.sin(3 * a + 5 * z + noise_seed) * 0.6 + math.sin(5 * a - 3 * z + 2 * noise_seed) * 0.4)
                c = ctr[0] + (c - ctr[0]) * f
                h = ctr[2] + (h - ctr[2]) * (1 + noise * 0.5 * math.sin(4 * a + noise_seed))
                if zmin is not None:
                    h = max(zmin, h)
            v.co = P(c, vv, h)
        faces = self._new_faces(before, mat)
        for f in faces:
            f.smooth = True
        return faces

    def obj(self, coll):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-5)
        o = common.mesh_object(self.name, self.bm, self.M.list, coll, smooth=None)
        return o


def bisect_keep(bm, co, no):
    """Cut bm with a plane, dropping the side `no` points to, and close the cuts."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    ret = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
    edges = [e for e in ret["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)


def clip_object(obj, planes):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for co, no in planes:
        bisect_keep(bm, co, no)
    bm.to_mesh(obj.data)
    bm.free()


# Art-view bounds: s = v - h >= 0 (top row), h >= 0 (ground), 0 <= c <= 24.
ART_CLIP = [
    ((0, 28 * S, 0), (0, 1, 1)),
    ((0, 0, 0), (0, 0, -1)),
    ((-1.0, 0, 0), (-1, 0, 0)),
    ((1.0, 0, 0), (1, 0, 0)),
]


# ---------------------------------------------------------------------------------------------
# The static structure (cliff, portal, spurs, rocks): the same on every frame
# ---------------------------------------------------------------------------------------------
FACE = 30.0  # the cliff's face plane (v)
TOPH = 22.0  # the cliff's top (h)
BAY = (4.0, 19.0, 22.5, 31.0, 0.25, 11.6)  # c0, c1, v0, v1, h0, h1: the launch bay cut into the rock
NOTCH = (15.7, 17.5, 25.0, 31.0, 14.0, 40.0)  # the crevice cut through the crest


def build_massif(coll):
    """The rock body: a (v, h) profile extruded across, the bay and crevice cut out by booleans
    whose cutters carry the dark rock (pal 1) onto the cut faces."""
    b = Builder("massif")
    prof = [(TOPH + 0.5, 0.0), (FACE, 0.0), (FACE, TOPH - 0.8), (FACE - 0.8, TOPH), (TOPH + 0.5, TOPH)]
    b.prism_c(prof, 0.0, 24.0, b.M(4))
    massif = b.obj(coll)
    for i, (c0, c1, v0, v1, h0, h1) in enumerate((BAY, NOTCH)):
        cb = Builder(f"cutter{i}")
        cb.chbox(c0, c1, v0, v1, h0, h1, cb.M(1))
        cutter = cb.obj(coll)
        mod = massif.modifiers.new(f"cut{i}", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = cutter
        mod.material_mode = "TRANSFER"
        common._apply_modifiers(massif)
        bpy.data.objects.remove(cutter)
    return massif


def build_static(coll):
    b = Builder("static")
    M = b.M
    # ---- the crest: boulders on the cliff top (art rows 0-8), sheen is lighting, not paint ----
    b.rock((7.0, 26.4, 21.4), (5.9, 4.0, 3.6), 11, M(6), n=34)  # big left boulder
    b.rock((2.0, 25.2, 21.0), (2.4, 3.2, 3.0), 12, M(5), n=22)  # small one at the west end
    b.rock((14.6, 24.8, 21.8), (1.9, 2.4, 2.6), 13, M(6), n=20)  # the knob over the crevice
    b.rock((21.0, 26.4, 21.3), (3.4, 3.9, 3.2), 14, M(6), n=28)  # right boulder
    b.rock((10.5, 23.2, 21.0), (3.4, 2.0, 2.0), 15, M(6), n=18)  # back stone between them
    b.rock((22.9, 24.6, 22.2), (1.5, 1.9, 1.7), 16, M(6), n=14)  # stones raising the crest's ends
    b.rock((1.0, 23.8, 21.8), (1.3, 1.7, 1.7), 17, M(5), n=14)
    b.rock((18.6, 25.2, 21.6), (2.0, 2.6, 2.4), 18, M(5), n=20)  # extra crest boulders (graft from A)
    b.rock((4.6, 24.4, 22.2), (2.2, 2.6, 2.2), 19, M(6), n=20)
    # ---- the cliff face, rough blocks proud of the face plane (art rows 8-17) ----
    # Each block is broken into leaning chunks with a ridge (facets), so the face reads as lit rock,
    # not flat slabs; the colours stay the blocks' own (pal 3/4/5).
    b.facets(0.0, 3.2, FACE - 0.4, FACE + 0.7, 12.6, 22.3, 21, M(3), nc=1, nh=3)  # west edge (pal 3)
    b.facets(3.0, 7.6, FACE - 0.4, FACE + 1.2, 16.2, 22.9, 22, M(5), nc=2, nh=2)  # stratum block, west half
    b.facets(7.3, 12.9, FACE - 0.4, FACE + 1.0, 15.8, 22.6, 23, M(5), nc=2, nh=2)  # stratum block, east half
    b.facets(12.7, 15.8, FACE - 0.6, FACE + 0.5, 14.2, 22.2, 24, M(3), nc=1, nh=3, lean=1.3)  # crevice slope
    b.facets(17.4, 20.6, FACE - 0.4, FACE + 0.8, 13.6, 22.4, 25, M(4), nc=1, nh=3)  # east of the crevice
    b.facets(20.3, 24.0, FACE - 0.4, FACE + 0.5, 13.4, 22.2, 26, M(4), nc=2, nh=3, lean=0.8)  # east face
    # loose angular stones on the massif top between the crest boulders (break up its flat top)
    for k, (c, v, r) in enumerate(((12.2, 27.2, 1.2), (9.0, 28.2, 1.1), (3.2, 28.0, 1.0),
                                   (19.8, 28.4, 1.0), (23.0, 27.6, 0.9))):
        b.rock((c, v, TOPH + r * 0.25), (r * 1.3, r, r * 0.8), 81 + k, M(5 if k % 2 else 6), n=10, jitter=0.3)
    # ---- the back of the outcrop: scree slabs on the 45-degree back slope ----
    # Strata stepping down the north side: rough slabs, each tread under the art's top row
    # (v - h >= 0.5), narrower and lower toward the back, with loose rocks on the treads.
    rnd = random.Random(5)
    for k, top in enumerate((5.2, 9.6, 12.8, 17.4, 22.0)):
        v0 = top + 0.6 + rnd.uniform(0.0, 1.2)
        w = 0.8 + (4 - k) * 0.8
        for half, (a, z) in enumerate(((w + rnd.uniform(-0.6, 0.6), 12.6), (11.4, 24 - w + rnd.uniform(-0.6, 0.6)))):
            dt = rnd.uniform(-1.4, 0.0)
            b.block(a, z, min(v0 + rnd.uniform(0, 1.4), max(v0, TOPH + 0.6)), TOPH + 2.0, 0.0, top + dt, 61 + 2 * k + half,
                    M((4, 3, 4, 5, 4)[k]), j=2.2)
        for i in range(2 + (k > 1)):
            c = w + 1.5 + rnd.uniform(0, 24 - 2 * w - 3)
            vt = v0 + rnd.uniform(0.4, 1.8)
            r = rnd.uniform(1.0, 1.6)
            vt = min(vt + r * 0.6, TOPH + 1.0 - r)  # loose rocks stay on the treads, behind the crest
            b.rock((c, vt, top + r * 0.3), (r * 1.4, r, r * 0.7), 71 + 3 * k + i, M(rnd.choice((3, 4, 5))),
                   n=12, jitter=0.2)
    # ---- the steel portal ----
    st = lambda p: M(p, STEEL)  # noqa: E731
    b.chbox(3.2, 15.6, FACE - 0.3, FACE + 0.6, 13.4, 16.2, st(4), ch=0.2)  # header I-beam: web
    b.chbox(3.2, 15.6, FACE - 0.3, FACE + 1.0, 15.7, 16.4, st(4), ch=0.2)  # top flange
    b.chbox(3.2, 15.6, FACE - 0.3, FACE + 1.0, 13.3, 14.0, st(4), ch=0.2)  # bottom flange
    for c in (6.4, 10.0, 13.4):  # anchor bolts through the beam
        b.chbox(c - 0.45, c + 0.45, FACE + 0.8, FACE + 1.25, 14.3, 15.2, st(5), ch=0.15)
    b.chbox(2.9, 20.1, FACE + 0.2, FACE + 2.2, 11.6, 13.2, st(5), ch=0.45)  # lintel
    b.chbox(4.0, 19.0, FACE + 1.2, FACE + 2.0, 11.2, 11.62, st(1))  # drip groove under the lintel
    b.chbox(2.9, 4.1, FACE + 0.2, FACE + 2.2, 0.0, 11.6, st(5), ch=0.3)  # west post
    b.chbox(18.9, 20.1, FACE + 0.2, FACE + 2.2, 0.0, 11.6, st(4), ch=0.3)  # east post
    for c0 in (2.55, 19.85):  # rail clamps on the posts' outer faces
        for h in (3.0, 7.6):
            b.chbox(c0, c0 + 0.6, FACE + 0.6, FACE + 1.9, h, h + 0.9, st(6), ch=0.2)
    b.chbox(4.0, 5.0, FACE + 0.4, FACE + 1.4, 0.3, 11.6, st(1))  # west guide track (the dark jamb)
    b.chbox(18.0, 18.9, FACE + 0.4, FACE + 1.4, 0.3, 11.6, st(2))  # east guide track
    b.chbox(2.9, 20.1, FACE + 1.2, FACE + 2.3, 0.0, 0.75, st(4), ch=0.25)  # sill (art row 31; row 30 is the pit)
    # the threshold step in front of the sill (the sprite's dark row 32): at the tilted game camera it also
    # closes the low view under the sill, where the lifted model showed the ground's own red art
    b.chbox(3.4, 19.6, FACE + 2.2, FACE + 3.6, 0.0, 0.3, st(1), ch=0.1)
    # ---- launch bay contents: burner grate on the floor ----
    b.chbox(4.0, 19.0, FACE - 0.6, FACE + 1.3, 0.0, 0.25, M(1))  # the bay floor out to the sill (dark)
    b.chbox(7.0, 16.0, 26.0, 29.6, 0.25, 0.65, st(2), ch=0.15)
    # ---- rock spurs running from the face down to the grass (art rows 16-41) ----
    def spur(stations, split, mats, seed):
        rnd = random.Random(seed)
        for i in range(len(stations) - 1):
            part, mat = stations[i:i + 2], mats[0] if i < split else mats[1]
            pts = []
            g0, g1 = max(p[1] for p in part), min(p[2] for p in part)  # the foot: the narrower station
            for v, c0, c1, h in part:
                for c in (c0, (c0 + c1) / 2, c1):
                    pts.append((c + rnd.uniform(-0.2, 0.2), v + rnd.uniform(-0.3, 0.3), h - rnd.uniform(0, 0.6)))
                for c in (g0, g1):
                    pts.append((c, v, 0.0))
            b.hull(pts, mat)
    spur([(29.2, 0.0, 3.1, 13.8), (31.6, 0.0, 3.0, 12.0), (33.6, 0.0, 3.0, 9.0), (36.0, 0.0, 3.0, 5.6),
          (37.6, 0.0, 2.1, 3.6), (38.6, 0.0, 1.1, 2.4), (40.9, 0.0, 1.0, 0.4)], 3, (M(3), M(2)), 31)
    spur([(29.2, 20.0, 24.0, 13.8), (31.6, 20.1, 24.0, 12.2), (33.6, 20.3, 24.0, 9.2), (36.0, 20.6, 24.0, 5.6),
          (38.6, 21.0, 24.0, 2.8), (39.6, 21.0, 24.0, 1.6), (40.2, 20.0, 24.0, 1.0), (41.0, 20.0, 24.0, 0.2)], 3, (M(2), M(3)), 32)
    # ---- in front, on the grass: a half-buried boulder and a pile of dark rocks ----
    b.block(3.1, 8.5, 31.9, 39.4, 0.0, 2.6, 41, M(4), j=0.7)  # half-buried boulder
    b.rock((8.3, 39.6, 0.0), (0.9, 1.6, 0.9), 42, M(4), n=10, flat=0.0)
    b.rock((6.4, 40.4, 0.0), (0.7, 0.8, 0.5), 46, M(4), n=8, flat=0.0)
    b.rock((3.9, 41.3, 0.0), (1.1, 1.1, 0.6), 47, M(4), n=8, flat=0.0)
    b.rock((17.5, 35.2, 0.0), (1.6, 3.3, 1.5), 43, M(2), n=16, flat=0.0)  # dark rock pile
    b.block(15.9, 19.0, 36.8, 39.2, 0.0, 1.4, 44, M(2), j=0.3)
    b.block(15.9, 18.0, 38.6, 41.0, 0.0, 1.0, 48, M(2), j=0.3)
    b.rock((19.0, 33.0, 0.0), (1.1, 1.3, 1.0), 45, M(3), n=10, flat=0.0)
    obj = b.obj(coll)
    massif = build_massif(coll)
    # one object: massif + parts
    for o in (obj, massif):
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    massif.select_set(True)
    bpy.ops.object.join()
    obj.name = "static"
    clip_object(obj, ART_CLIP)
    return obj


# ---------------------------------------------------------------------------------------------
# The shutter and the fire, per state
# ---------------------------------------------------------------------------------------------
# state: shutter bottom h, rail front pal, rail top pal (from the sprite rows of each frame)
STATES = {
    "closed": (0.75, 3, 3),
    "stir": (3.4, 4, 4),
    "half": (5.4, 5, 4),
    "high": (6.8, 3, 6),  # f3: the lip at art rows 23-24, the dark slot above it
    "up": (8.5, 4, 8),
}
# fire per state: (c, rc, top h, outer pal, core pal, hot pal or None, outer strength)
FIRE = {
    "half": (11.0, 3.2, 2.0, 113, 115, None),
    "high": (11.7, 4.4, 4.0, 114, 120, None),
    "up": (11.0, 4.6, 7.0, 114, 119, 124),
}
FRAME_STATES = ["closed", "stir", "half", "high", "up"]  # assembly frames 0-4 (153|191 .. 161|199)
SHUT_V = (FACE + 0.65, FACE + 1.15)  # the shutter's plane (between the tracks)
SLOT_TOP = 12.9  # the shutter runs up into a slot in the lintel


def build_shutter(state, coll):
    b = Builder(f"shutter_{state}")
    bot, front, top = STATES[state]
    v0, v1 = SHUT_V
    if bot + 1.0 < SLOT_TOP:
        # panel: pal 2 on f2 and pal 1 on f3, as the sprite (once lifted, the panel above the lip is in
        # the slot's shadow: the sprite's dark slot over the bright lip)
        panel, rib = {"half": (2, 3), "high": (1, 2)}.get(state, (3, 3))
        b.chbox(5.0, 18.0, v0, v1, bot + 0.9, SLOT_TOP, b.M(panel, STEEL))
        for k in (2.8, 5.8, 8.8):  # ribs across it (panel lines)
            if bot + k + 0.4 < 11.4:
                b.chbox(5.3, 17.7, v1, v1 + 0.18, bot + k, bot + k + 0.4, b.M(rib, STEEL), ch=0.05)
    rh = 1.3 if state == "high" else 1.0  # f3: a deeper lip, its front the sprite's pal-3 row 24
    rail = b.chbox(5.0, 18.0, v0 - 0.05, v1 + 0.65, bot, bot + rh, b.M(front, STEEL), ch=0.25)
    for f in rail:
        if f.normal.z > 0.5:
            f.material_index = b.M(top, STEEL)
    return b.obj(coll)


def build_fire(state, coll):
    c, rc, top, outer, core, hot = FIRE[state]
    b = Builder(f"fire_{state}")
    vb = 30.0  # the sprite's fire reaches row 30, just behind the sill (row 31)
    b.ellip((c, vb, top * 0.38), (rc, 1.0, top * 0.62), b.M(outer, GLOW, 1.0), taper=0.45, zmin=0.3,
            noise=0.18, noise_seed=1.0)
    b.ellip((c - 0.2, vb + 0.5, top * 0.34), (rc * 0.55, 0.6, top * 0.5), b.M(core, GLOW, 1.2), taper=0.4,
            zmin=0.35, noise=0.15, noise_seed=2.5)
    if hot:
        b.ellip((c, vb + 0.75, top * 0.36), (rc * 0.24, 0.4, top * 0.26), b.M(hot, GLOW, 1.4), taper=0.3, zmin=0.4)
    return b.obj(coll)


# ---------------------------------------------------------------------------------------------
# Pieces: the art draws newshg-153 above screen row 28 and newshg-191 below, so the cut is the
# oblique plane s = 28 (Y + Z = 0); each piece is moved so its sprite's centre is its origin.
# ---------------------------------------------------------------------------------------------
PIECES = {"newshg-153": (+1, 14), "newshg-191": (-1, 42)}


# The depth band (D165). It was [0, 0.04]: the 22 px cliff squeezed into 0.04 units put the outline
# shell's back faces only a few depth steps behind the rock (OUTLINE_SINK is 5% of the band, 0.002),
# and at the tilted game camera their ink showed through the crest and both flanks as a thick black
# skirt (E2 QA M8, BOTANY A t3300). 0.4, as the sibling cliff assembly-newshh-129 and the D170/D179
# ground structures: still under background 2 (0.45 above ground enemies, D5), and D181's coverHeight
# lifts later draws over it.
BAND = (0.0, 0.4)
SHELL_INSIDE = 0.01  # the shell held this far inside the rock (units), D90/D118
# Plugs that close the model's hollows in the shell's source only (c0, c1, v0, v1, h0, h1, px): the
# launch bay with its portal, posts, clamps and the spurs' roots, the crevice through the crest, and
# the valleys between the crest boulders. Inside the silhouette, so the contour is unchanged, but the
# shell no longer lines them, and its back faces can't ink their walls.
SEAL = [
    (0.0, 24.0, BAY[2], FACE + 2.2, 0.0, 13.2),
    # (split at the crevice: a plug bridging its open slot would show its underside's ink in it)
    (1.0, NOTCH[0] - 0.2, TOPH + 1.0, FACE - 0.5, TOPH - 1.0, TOPH + 1.6),
    (NOTCH[1] + 0.2, 23.0, TOPH + 1.0, FACE - 0.5, TOPH - 1.0, TOPH + 1.6),
    (NOTCH[0] - 0.2, NOTCH[1] + 0.2, NOTCH[2], FACE + 0.5, NOTCH[4], TOPH + 1.0),
]


def sealed_copy(static, coll):
    """The static rock with its hollows plugged (SEAL): the outline shell's source, never exported."""
    b = Builder("sealed_plugs")
    for c0, c1, v0, v1, h0, h1 in SEAL:
        b.chbox(c0, c1, v0, v1, h0, h1, b.M(1))
    plugs = b.obj(coll)
    me = static.data.copy()
    o = bpy.data.objects.new("sealed", me)
    coll.objects.link(o)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.from_mesh(plugs.data)
    bm.to_mesh(me)
    bm.free()
    bpy.data.objects.remove(plugs)
    clip_object(o, ART_CLIP)
    return o


def cut_piece(src, piece, coll, name):
    side, centre = PIECES[piece]
    bm = bmesh.new()
    bm.from_mesh(src.data)
    n = Vector((0, 1, 1)).normalized()
    bisect_keep(bm, (0, 0, 0), tuple(-n if side > 0 else n))
    bmesh.ops.translate(bm, vec=(0, -(28 - centre) * S, 0), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in src.data.materials:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o if len(me.polygons) else (bpy.data.objects.remove(o) or None)


# (model, piece, {sprite frame: state} for the shutter, {frame: state} for the fire)
MODELS = [
    ("newshg-153", "newshg-153", {153: "closed", 155: "stir"}, {}),
    ("newshg-153-f2", "newshg-153", {157: "half"}, {157: "half"}),
    ("newshg-153-f3", "newshg-153", {159: "high"}, {159: "high"}),
    ("newshg-153-f4", "newshg-153", {161: "up"}, {161: "up"}),
    ("newshg-191", "newshg-191", {191: "closed"}, {}),
    ("newshg-191-f2", "newshg-191", {193: "stir"}, {}),
    # The two pieces animate on their own (the top runs 153-161 while the bottom holds 191, then the
    # bottom runs 193-199 under a closed top), so the bottom keeps the fire's rows 28-30 for its own
    # frames: one fire per frame, each node shown only on its frame (tyrian_frames, D17).
    ("newshg-191-f3", "newshg-191", {195: "half", 197: "high", 199: "up"}, {195: "half", 197: "high", 199: "up"}),
]


def main():
    coll = common.reset_collection(NAME)
    static = build_static(coll)
    shutters = {s: build_shutter(s, coll) for s in STATES}
    fires = {s: build_fire(s, coll) for s in FIRE}
    for o in list(shutters.values()) + list(fires.values()):
        clip_object(o, ART_CLIP)

    # ---- export: one empty per game model ----
    export_coll = common.reset_collection(NAME + "_export")
    # The height range of the whole cliff (glTF y = Blender Z, model units), shared by both pieces.
    top = round(max((static.matrix_world @ v.co).z for v in static.data.vertices), 4)
    exported = []
    statics, shells = {}, {}
    sealed = sealed_copy(static, coll)
    for piece in PIECES:
        statics[piece] = cut_piece(static, piece, export_coll, f"{piece}_static")
        # The shell from the sealed copy, held a hair inside (D90/D118): ink on the silhouette only.
        src = cut_piece(sealed, piece, export_coll, f"{piece}_sealed")
        shells[piece] = common.outline_shell(src, export_coll, voxel=0.02, faces=4000, inside=SHELL_INSIDE)
        bpy.data.objects.remove(src)
    bpy.data.objects.remove(sealed)
    for model, piece, shut, fire in MODELS:
        root = bpy.data.objects.new(model, None)
        export_coll.objects.link(root)
        root["tyrian_oblique"] = 1.0
        root["tyrian_depth_band"] = [BAND[0], BAND[1], 0.0, top]  # one cliff-wide [y0, y1] (D165)
        kids = []
        st = bpy.data.objects.new(f"{model}.static", statics[piece].data)
        sh = bpy.data.objects.new(f"{model}.outline", shells[piece].data)
        sh["tyrian_outline"] = True
        kids += [st, sh]
        multi = len(set(shut.values())) > 1
        for frames_states, src, kind in ((shut, shutters, "shutter"), (fire, fires, "fire")):
            by_state = {}
            for f, s in frames_states.items():
                by_state.setdefault(s, []).append(f)
            for s, frames in by_state.items():
                o = cut_piece(src[s], piece, export_coll, f"{model}.{kind}_{s}")
                if o is None:
                    continue
                if multi or kind == "fire" and len(fire) > 1:
                    common.frame_part(o, frames)
                kids.append(o)
        for k in kids:
            if k.name not in export_coll.objects:
                export_coll.objects.link(k)
            k.parent = root
        exported += [root] + kids
    sheet = common.load_sprite(ROOT, "newshg-153")
    for model, piece, shut, fire in MODELS:
        objs = [o for o in exported if o.name == model or o.name.startswith(model + ".")]
        frames = sorted(set(shut) | set(fire))
        sprites = []
        for s in sheet["sprites"] if piece == "newshg-153" else common.load_sprite(ROOT, "newshg-191")["sprites"]:
            keep = [f for f in s["frames"] if f in frames]
            if keep:
                sprites.append({**s, "frames": keep})
        common.export_sprite_model(ROOT, objs, f"enemies/{model}", sprites)

    if WORK is None:
        return
    # ---- measure: art view per assembly frame ----
    metrics = measure(static, shutters, fires, coll)
    (WORK / "metrics.json").write_text(json.dumps(metrics, indent=1))
    for f in metrics["frames"]:
        print("frame", f["frame"], "iou", f["iou"], "pieces", f["iou_pieces"], "miss", f["miss"], "extra", f["extra"])
    if RENDER:
        render_views(static, shutters, fires, coll)
    stats = {"tris_static": sum(len(p.vertices) - 2 for p in static.data.polygons)}
    (WORK / "stats.json").write_text(json.dumps(stats))


# ---------------------------------------------------------------------------------------------
# Measuring (art view) and rendering
# ---------------------------------------------------------------------------------------------
SHEAR = Matrix(((1, 0, 0, 0), (0, 1, 1, 0), (0, 0, 1, 0), (0, 0, 0, 1)))


def sheared_copy(objs, coll, name):
    copies = []
    for o in objs:
        c = o.copy()
        c.data = o.data.copy()
        c.data.transform(SHEAR)
        coll.objects.link(c)
        copies.append(c)
    return copies


def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split()
        scene.render.engine = next(e for e in names if want.split("_")[1] in e)


def ortho_cam(name, loc, rot, scale):
    cam = bpy.data.cameras.new(name)
    cam.type = "ORTHO"
    cam.ortho_scale = scale
    cam.clip_end = 100
    o = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    return o


def only(objs):
    for o in bpy.context.scene.objects:
        o.hide_render = o not in objs and o.type != "CAMERA" and o.type != "LIGHT"


def measure(static, shutters, fires, coll):
    import numpy as np
    data = json.loads((WORK / "sprite_data.json").read_text())
    W, H, K = 24, 56, 8
    scene = bpy.context.scene
    set_engine(scene, "BLENDER_WORKBENCH")
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = False
    scene.display.shading.show_object_outline = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = W * K, H * K
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    cam = ortho_cam("measure_cam", (0, 0, 10), (0, 0, 0), H * S)
    scene.camera = cam
    lin = lambda b: ((b / 255 + 0.055) / 1.055) ** 2.4 if b / 255 > 0.04045 else b / 255 / 12.92  # noqa: E731
    pal = data["palette"]
    luma = {int(k): 0.299 * v[0] + 0.587 * v[1] + 0.114 * v[2] for k, v in pal.items()}
    out = {"frames": []}
    for fi, state in enumerate(FRAME_STATES):
        objs = [static, shutters[state]] + ([fires[state]] if state in fires else [])
        copies = sheared_copy(objs, coll, "m")
        saved = []
        for o in copies:
            for m in o.data.materials:
                if m and m.name.startswith("pal_") and m not in [s[0] for s in saved]:
                    saved.append((m, tuple(m.diffuse_color)))
                    idx = int(m.name.split("_")[1])
                    m.diffuse_color = (lin(idx), lin(0), lin(128), 1)
        only(copies)
        path = WORK / f"measure_f{fi}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        for m, col in saved:
            m.diffuse_color = col
        for o in copies:
            bpy.data.objects.remove(o)
        img = bpy.data.images.load(str(path))
        px = np.array(img.pixels[:], dtype=np.float32).reshape(H * K, W * K, 4)[::-1]
        bpy.data.images.remove(img)
        r8 = np.round(px[..., 0] * 255).astype(int)
        alpha = px[..., 3] > 0.5
        cov = alpha.reshape(H, K, W, K).mean(axis=(1, 3))
        model = cov >= 0.5
        inner = np.array(data["inner"][fi], bool)
        free = np.array(data["free"][fi], bool)
        obj = np.array(data["object"], bool)
        care = ~free
        inter = (model & inner & care).sum()
        union = ((model | inner) & care).sum()
        miss = (inner & ~model & care)
        extra = (model & ~inner & care)
        pieces = []
        for r0, r1 in ((0, 28), (28, 56)):
            sl = slice(r0, r1)
            i_ = (model[sl] & inner[sl] & care[sl]).sum()
            u_ = ((model[sl] | inner[sl]) & care[sl]).sum()
            pieces.append(round(float(i_ / u_), 4))
        # model palette per sprite pixel: the mode of its block
        mpal = np.full((H, W), -1)
        for r in range(H):
            for c in range(W):
                blk = r8[r * K:(r + 1) * K, c * K:(c + 1) * K][alpha[r * K:(r + 1) * K, c * K:(c + 1) * K]]
                if blk.size:
                    vals, cnt = np.unique(blk, return_counts=True)
                    mpal[r, c] = int(vals[cnt.argmax()])
        np.save(WORK / f"mpal_f{fi}.npy", mpal)
        np.save(WORK / f"mask_f{fi}.npy", model)
        sprite = np.array(data["frames"][fi])
        regs = []
        for name, (c0, r0, c1, r1) in REGIONS.items():
            reg = np.zeros((H, W), bool)
            reg[r0:r1 + 1, c0:c1 + 1] = True
            reg &= obj

            def med(vals):
                v = sorted((int(x) for x in vals if x >= 0), key=lambda x: (luma.get(x, 0), x))
                k = int(len(v) * 0.15)
                core = v[k:len(v) - k] if len(v) > 6 else v
                return core[len(core) // 2] if core else None
            regs.append({"region": name, "sprite": med(sprite[reg]), "model": med(mpal[reg]), "px": int(reg.sum())})
        firepx = (sprite >= 112) & (sprite <= 127)
        if firepx.any():
            regs.append({"region": "fire", "sprite": int(np.median(sprite[firepx])),
                         "model": int(np.median(mpal[firepx][mpal[firepx] >= 0])) if (mpal[firepx] >= 0).any() else None,
                         "px": int(firepx.sum()),
                         "model_fire_px": int(((mpal >= 112) & (mpal <= 127)).sum())})
        out["frames"].append({"frame": fi, "state": state, "iou": round(float(inter / union), 4), "iou_pieces": pieces,
                              "miss": int(miss.sum()), "extra": int(extra.sum()),
                              "miss_px": [list(map(int, p)) for p in np.argwhere(miss)],
                              "extra_px": [list(map(int, p)) for p in np.argwhere(extra)], "regions": regs})
    bpy.data.objects.remove(cam)
    return out


REGIONS = {
    "crest_left": (0, 0, 12, 7), "crest_knob": (13, 0, 16, 3), "crest_right": (17, 0, 23, 7),
    "crevice": (16, 4, 17, 16), "block_left": (3, 8, 12, 13), "face_left_edge": (0, 8, 2, 17),
    "face_right": (18, 8, 23, 16), "crevice_slope": (13, 8, 15, 16), "header_band": (3, 14, 15, 16),
    "crease": (0, 17, 23, 17), "roof": (3, 18, 19, 19), "post_left": (3, 20, 3, 30),
    "post_right": (19, 20, 19, 30), "jamb_shadow": (4, 20, 4, 30), "door_panel": (5, 22, 17, 29),
    "sill": (4, 31, 19, 31), "pillar_left": (0, 18, 2, 31), "pillar_left_foot": (0, 32, 2, 41),
    "pillar_right": (20, 18, 23, 31), "pillar_right_foot": (20, 32, 23, 41),
    "boulder": (3, 33, 8, 41), "rock_pile": (15, 33, 19, 41),
}


def render_views(static, shutters, fires, coll):
    scene = bpy.context.scene
    try:
        set_engine(scene, "BLENDER_EEVEE")
    except StopIteration:
        set_engine(scene, "BLENDER_WORKBENCH")
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.035, 0.045, 0.06, 1)
    bg.inputs[1].default_value = 1.0
    for o in [o for o in scene.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o)
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.2
    so = bpy.data.objects.new("sun", sun)
    scene.collection.objects.link(so)
    # light from the upper left of the screen (north-west) and above, a little from the front
    so.rotation_euler = (math.radians(40), 0, math.radians(-140))
    fill = bpy.data.lights.new("fill", "SUN")
    fill.energy = 0.8
    fo = bpy.data.objects.new("fill", fill)
    scene.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(60), 0, math.radians(30))
    # a ground plane for the views (not exported): green-grey like the HD grass
    gm = bpy.data.meshes.new("ground")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4.0)
    bm.to_mesh(gm)
    bm.free()
    ground = bpy.data.objects.new("ground", gm)
    gm.materials.append(common.material("ground_view", (0.02, 0.05, 0.02), roughness=1.0))
    coll.objects.link(ground)
    ground.location = (0, -0.5, -0.002)

    def shot(objs, path, cam, res):
        scene.render.resolution_x, scene.render.resolution_y = res
        only(objs + [ground] if ground_on[0] else objs)
        scene.camera = cam
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    ground_on = [False]
    # game view (oblique-locked: the art view, lit) per frame, no ground (the HD terrain is the game's)
    cam = ortho_cam("art", (0, 0, 10), (0, 0, 0), 56 * S)
    for fi, state in enumerate(FRAME_STATES):
        objs = [static, shutters[state]] + ([fires[state]] if state in fires else [])
        copies = sheared_copy(objs, coll, "a")
        shot(copies, WORK / f"art_f{fi}.png", cam, (240, 560))
        for o in copies:
            bpy.data.objects.remove(o)
    # true views of the open state (fire) and the closed state
    def look(name, direction, up_z=True, scale=5.2, persp=None, tgt=(0, -0.3, 0.75)):
        d = Vector(direction).normalized()
        if persp:
            camd = bpy.data.cameras.new(name)
            camd.lens = persp
            camd.clip_end = 200
            o = bpy.data.objects.new(name, camd)
            scene.collection.objects.link(o)
            o.location = Vector(tgt) + d * 9.5
        else:
            o = ortho_cam(name, Vector(tgt) + d * 20, (0, 0, 0), scale)
        o.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        return o
    views = {
        "plan": look("plan", (0, 0, 1), scale=5.4, tgt=(0, -0.3, 0)),
        "front": look("front", (0, -1, 0.0001), scale=4.2, tgt=(0, -0.3, 1.0)),
        "side": look("side", (1, 0, 0.0001), scale=4.6, tgt=(0, -0.4, 1.0)),
        "rear": look("rear", (0, 1, 0.0001), scale=4.2, tgt=(0, -0.3, 1.0)),
        "q_se": look("q_se", (1, -1.2, 1.0), persp=50),
        "q_sw": look("q_sw", (-1, -1.2, 0.9), persp=50),
        "q_nw": look("q_nw", (-1, 1.2, 0.9), persp=50),
        "under": look("under", (0.3, -0.4, -1), scale=5.4, tgt=(0, -0.3, 0)),
    }
    ground_on[0] = True
    for vname, cam in views.items():
        ground.hide_render = vname == "under"
        for state in ("up", "closed") if vname in ("q_se", "front") else ("up",):
            objs = [static, shutters[state]] + ([fires[state]] if state in fires else [])
            if vname == "under":
                ground_on[0] = False
            shot(objs, WORK / f"view_{vname}_{state}.png", cam, (520, 520) if vname.startswith("q") else (420, 420))
            ground_on[0] = True
    # the tilted game camera (15 deg from straight down, from the south) on the oblique-locked model,
    # and on the true model as the game would draw it without the oblique lock
    gcam = look("game", (0, -math.tan(math.radians(15)), 1), persp=60, tgt=(0, 0, 0))
    gcam.location = Vector((0, 0, 0)) + Vector((0, -math.sin(math.radians(15)), math.cos(math.radians(15)))) * 9
    for state in ("closed", "up"):
        objs = [static, shutters[state]] + ([fires[state]] if state in fires else [])
        copies = sheared_copy(objs, coll, "g")
        shot(copies + [ground], WORK / f"game_lock_{state}.png", gcam, (360, 560))
        for o in copies:
            bpy.data.objects.remove(o)
        shot(objs + [ground], WORK / f"game_true_{state}.png", gcam, (360, 560))


main()
