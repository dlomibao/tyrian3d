"""Brass dome works (newsh2.shp 77, 79, 115, 117 in a 2x2; enemy types 121-124): a 3D version of
its sprites.

Seen in levels 1.28, 1.30 and 3.17. Four 2x2 enemies make one 48 x 56 px structure dug into brown
dirt (sprite.json `assemblyLayout`; the layout also lists newsh2-119, a separate neighbour). Each
piece is exported as enemies/newsh2-<frame> with its own spriteModels entry, as before.

A hard-surface rebuild in the manner of the USP Talon (D50-D53), blueprint first. Every part is
drawn as a cross-section in sprite pixels (grid 48 x 56 px, column c / row r as pixel EDGES, z up in
px, 1 px = 1/12 unit) and only then placed; the sprite is authoritative for the plan outline, the
positions of the domes, hatches, slots, gun blocks, nozzles and the gun port, and for the palette
index of each part (median of its pixels with the darkest shading and the brightest sheen left out:
domes and hatches 24, pylons and the pipe housing 4, gun blocks 6, brackets and rims 3, the bed 2).

Blueprint (plan, sprite rows top to bottom):
- BED: one dark steel slab (z 0-1.4) in the sprite's outline including its dark ring, chamfered
  45 degrees all round; a raised rim frames its lower octagon (the sprite's lit grey struts).
- PYLONS (cols 2.6-7.8 and 31.2-36.4, rows 12.6-26.9): two armour plates each, split at row 20 by a
  seam (the sprite's dark row 20, lit row 21), clipped outer corners, bolt heads.
- BIG DOME (centre 19.25, 11.0; 13.3 x 10.5 px; 9 px tall): a revolved section - a machined base
  collar (vertical band, chamfer, step) under a sphere-like cap. On it, conforming to the cap: the
  sprite's H-shaped hatch band (cols 13-24, rows 5.6-20.6) as plates standing proud with 45-degree
  chamfers: an upper hatch with a vent grille, the crossbar (sprite's lit row 11), a dark slot below
  it (rows 12.6-14.4) and the lower hatch with its grille; framed dark slots on both flanks
  (cols 10.2-12.0 and 25.2-27.0, rows 8.6-14.4).
- PIPES: an elbow pipe from each flank of the big dome down into each side dome's socket (cols 7-9
  and 29-31, rows 18-26); two thin rods across the dome's lower right (the sprite's bright diagonal
  from col 30 row 16 to col 23 row 22); short grey pipes from the dome's foot into the housing.
- NECK: a dark plate between the domes, two diagonal braces (the sprite's lit grey diagonal at
  left, its shadowed twin at right) and the grey pipe housing (cols 15.8-23.2, rows 26.8-34.8)
  with a channel carrying a pipe (the sprite's dark col 19 and lit col 20).
- SIDE DOMES (centres 8.5 and 30.5, row 31; 6.5 x 4.6 px, 5.6 px tall; the right unit is the left
  one moved 22 px across, as the sprite draws it): collar and cap, a grey end boss outboard, a
  pipe socket on top, and on the front the grey gun block (cols 5.6-10.8, rows 29.5-35.6): housing,
  lit top plate, two studs, an indicator window down its right side (the sprite's col 10) with a
  small lamp, a main barrel (col 6.5, to row 38: the sprite's see-through pixels are its bright
  muzzle) and a small stub at col 10.
- BOTTOM DOME (centre 19.5, 40.5; 6.5 x 5.2 px; 5.4 px tall) with the gun port where the sprite has
  it (col 19.0, row 41.5): a short machined muzzle normal to the dome, a dark bore.
- BRACKETS: two grey blocks on the lower bed (cols 7.8-12.2 and 26.8-31.2, rows 37.8-42.2).
- DIRT: a floor of 2 x 2 px cells in the sprite's dirt colours, closed underneath.

No concept projection bake (maps.json says "bake": "model", so texture_bake.py skips it, as the
player ships in D50-D53). Unless --no-bake, an ambient occlusion / edge-wear colour multiplier and a
roughness-metalness map are baked (as usp_talon.py) and multiplied into the palette materials. The
colour map is neutral grey here (no D53 cool tint): the tint turned the brass (index 24) olive.
The underside is only a closed slab (undersides are almost never seen).

The structure is built once in assembly coordinates and cut into its four pieces
(common.split_assembly), each keeping its own 24 x 28 px box, plus an outline shell per piece
(common.outline_shell, D51, cut without capping so no seams are outlined).

    blender --background --factory-startup --python assets/blender/enemies/assembly-newsh2-115.py -- \
        [--no-bake] [--preview out.png]
(the preview is the whole structure; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b120 as lib  # noqa: E402

NAME = "assembly-newsh2-115"
ROOT = common.repo_root(__file__)
W, H = 48, 56
PX = 1 / 12


def V(c, r, z):
    """Sprite pixel edges (column, row) and height in px -> Blender units."""
    return Vector(((c - W / 2) * PX, (H / 2 - r) * PX, z * PX))


# ---------------------------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------------------------

BED_TOP = 1.4
BED_OUTLINE = [  # pixel edges, from the sprite mask incl. its dark ring (rows 5-52), row by row
    (6.2, 8.6), (5.0, 9.0), (5.0, 12.0), (3.4, 13.0), (2.0, 14.6), (2.0, 28.4), (1.2, 29.0),
    (1.0, 29.6), (1.0, 33.6), (1.4, 34.0), (2.0, 34.2), (2.0, 38.0), (2.6, 39.0), (6.6, 39.0),
    (7.0, 39.4), (7.0, 44.4), (9.6, 45.4), (11.0, 47.4), (13.4, 50.2), (14.6, 51.0), (20.9, 51.0),
    (21.1, 52.0), (25.9, 52.0), (26.4, 50.8), (27.0, 49.8), (28.0, 49.1), (32.0, 48.9),
    (32.6, 46.6), (33.4, 45.0), (34.0, 40.2), (36.1, 39.3), (38.0, 38.9), (38.1, 36.2),
    (39.3, 35.3), (39.8, 34.4), (39.8, 29.6), (38.0, 28.5), (37.0, 27.6), (37.0, 14.0),
    (36.0, 13.4), (35.0, 12.2), (34.0, 11.5), (34.0, 8.3), (33.2, 7.9), (33.1, 4.9), (30.0, 4.9),
    (24.0, 8.0), (15.0, 8.0),
]
LOWER_RIM = [  # the raised frame round the lower octagon (inside the bed outline)
    (7.6, 37.2), (7.6, 44.0), (10.0, 45.0), (11.6, 47.0), (14.2, 49.8), (25.2, 49.8), (26.6, 48.6),
    (30.6, 47.6), (32.4, 45.0), (32.8, 40.0), (32.8, 37.2),
]

# Domes: centre (c, r), plan radii (rx, ry) of the cap's foot, cap height and collar.
BIG = dict(c=19.5, r=11.1, rx=13.15, ry=10.35, h=12.0, collar=2.6, lip=0.55)
SIDES = [dict(c=8.5, r=31.0, rx=6.3, ry=4.45, h=6.4, collar=1.9, lip=0.4),
         dict(c=30.5, r=31.0, rx=6.3, ry=4.45, h=6.4, collar=1.9, lip=0.4)]
BOT = dict(c=19.5, r=40.55, rx=6.3, ry=5.0, h=6.2, collar=1.9, lip=0.4)
PORT = (19.0, 41.5)

# Palette indices (sprite medians, see the docstring).
PAL = dict(brass=24, brass_dk=22, brass_dd=20, brass_lt=25, rod=26, grey=4, grey_lt=6, grey_dk=3, bed=3,
           deep=1, block=6, window=106, lamp=169, tip=30, glow=30)
DIRT = [16, 17, 18, 19, 20, 21]
METAL = 0.3  # satin, D53
EXP = 2.0  # dome section exponent (2 = elliptical)


# ---------------------------------------------------------------------------------------------
# Mesh helpers (px space)
# ---------------------------------------------------------------------------------------------

class Builder:
    def __init__(self):
        self.bm = bmesh.new()
        self.slots = {}
        self.mats = []

    def mat(self, key):
        return self.slots[key]

    def v(self, c, r, z):
        return self.bm.verts.new(V(c, r, z))

    def face(self, verts, mat, smooth=False):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        f.material_index = mat
        f.smooth = smooth
        return f

    def closed(self, first):
        """Orient the faces added since index `first` (a closed piece) outward."""
        self.bm.faces.ensure_lookup_table()
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[first:])

    def nfaces(self):
        return len(self.bm.faces)

    # -- prisms -------------------------------------------------------------------------------
    def prism(self, outline, z0, z1, mat, ch=0.5, top_mat=None):
        """A prism over an outline in px with its top edge chamfered `ch` px at 45 degrees."""
        lib.bevel_prism(self.bm, [tuple(V(c, r, 0)[:2]) for c, r in outline], z0 * PX, z1 * PX,
                        ch * PX, mat=mat, top_mat=top_mat)

    def rect(self, c0, r0, c1, r1, z0, z1, mat, ch=0.4, cut=0.0, top_mat=None):
        if cut:
            pts = [(c0 + cut, r0), (c1 - cut, r0), (c1, r0 + cut), (c1, r1 - cut), (c1 - cut, r1),
                   (c0 + cut, r1), (c0, r1 - cut), (c0, r0 + cut)]
        else:
            pts = [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]
        self.prism(pts, z0, z1, mat, ch, top_mat)

    # -- revolved domes -----------------------------------------------------------------------
    def dome(self, d, mat, collar_mat, seg=48, rings=12, z0=0.6):
        """A machined dome: vertical collar band, 45-degree chamfer and a step in, then a cap that
        starts vertical and closes over the top (superellipse section, exponent EXP)."""
        c, r, rx, ry, h = d["c"], d["r"], d["rx"], d["ry"], d["h"]
        lip, col = d["lip"], d["collar"]
        k = 1 + lip / rx  # plan scale of the collar's outer face
        prof = [(k, z0, False), (k, col - lip * 0.7, False), (k - lip * 0.7 / rx, col, False)]
        n = rings
        for i in range(n + 1):
            a = (math.pi / 2) * i / n
            ca, sa = math.cos(a), math.sin(a)
            rho = ca ** (2 / EXP) if ca > 0 else 0.0
            z = col + (h - col) * (sa ** (2 / EXP))
            prof.append((rho, z, True))
        first = self.nfaces()
        ringsv = []
        for rho, z, _ in prof[:-1]:
            ringsv.append([self.v(c + rho * rx * math.cos(t), r + rho * ry * math.sin(t), z)
                           for t in (2 * math.pi * (j + 0.5) / seg for j in range(seg))])
        pole = self.v(c, r, prof[-1][1])
        for i in range(len(ringsv) - 1):
            sm = prof[i + 1][2] and prof[i][2]
            m = mat if i >= 3 else collar_mat
            for j in range(seg):
                jj = (j + 1) % seg
                self.face((ringsv[i][j], ringsv[i][jj], ringsv[i + 1][jj], ringsv[i + 1][j]), m, sm)
        for j in range(seg):
            self.face((ringsv[-1][j], ringsv[-1][(j + 1) % seg], pole), mat, True)
        self.face(list(reversed(ringsv[0])), collar_mat)
        self.closed(first)

    @staticmethod
    def surf(d, c, r):
        """Height of dome d's cap over (c, r) in px (its collar height outside the cap)."""
        rho = math.hypot((c - d["c"]) / d["rx"], (r - d["r"]) / d["ry"])
        if rho >= 1:
            return d["collar"]
        # invert rho = cos^(2/EXP): cos a = rho^(EXP/2); z from sin a
        ca = rho ** (EXP / 2)
        sa = math.sqrt(max(0.0, 1 - ca * ca))
        return d["collar"] + (d["h"] - d["collar"]) * sa ** (2 / EXP)

    def cplate(self, d, c0, r0, c1, r1, t, mat, ch=0.35, n=6, sink=0.6, cut=0.0):
        """A plate conforming to dome d over the box (px): its top `t` px above the cap with a
        45-degree chamfer `ch` round it, its sides dropping `sink` below the surface (closed)."""
        first = self.nfaces()
        nu = max(2, int(round(n * (c1 - c0) / max(c1 - c0, r1 - r0))))
        nv = max(2, int(round(n * (r1 - r0) / max(c1 - c0, r1 - r0))))
        nu, nv = max(nu, 2), max(nv, 2)

        def grid(a0, b0, a1, b1, dz, inset):
            g = []
            for j in range(nv + 1):
                row = []
                for i in range(nu + 1):
                    cc = a0 + (a1 - a0) * i / nu
                    rr = b0 + (b1 - b0) * j / nv
                    if cut:  # clip the corners
                        ex = min(cc - a0, a1 - cc)
                        ey = min(rr - b0, b1 - rr)
                        if ex + ey < cut:
                            s = (cut - ex - ey)
                            cc += s if cc - a0 < a1 - cc else -s
                    row.append(self.v(cc, rr, self.surf(d, cc, rr) + dz))
                g.append(row)
            return g
        top = grid(c0 + ch, r0 + ch, c1 - ch, r1 - ch, t, True)
        mid = grid(c0, r0, c1, r1, t - ch, False)
        bot = grid(c0, r0, c1, r1, -sink, False)
        for j in range(nv):
            for i in range(nu):
                self.face((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]), mat)
                self.face((bot[j][i], bot[j + 1][i], bot[j + 1][i + 1], bot[j][i + 1]), mat)
        ring = ([(0, i) for i in range(nu)] + [(j, nu) for j in range(nv)] +
                [(nv, i) for i in range(nu, 0, -1)] + [(j, 0) for j in range(nv, 0, -1)])
        for (j0, i0), (j1, i1) in zip(ring, ring[1:] + ring[:1]):
            self.face((top[j0][i0], top[j1][i1], mid[j1][i1], mid[j0][i0]), mat)
            self.face((mid[j0][i0], mid[j1][i1], bot[j1][i1], bot[j0][i0]), mat)
        # interior verts of mid are unused: remove them
        for j in range(1, nv):
            for i in range(1, nu):
                self.bm.verts.remove(mid[j][i])
        self.closed(first)

    def pipe(self, pts, rad, mat, sides=10, smooth=True, caps=True):
        """A tube through (c, r, z) px points, radius in px."""
        first = self.nfaces()
        lib.sweep(self.bm, [(*V(c, r, z), rad * PX, rad * PX) for c, r, z in pts], sides=sides, mat=mat,
                  smooth=smooth, cap_start=caps, cap_end=caps)
        self.closed(first)

    def cyl(self, c, r, z0, z1, rad, mat, sides=12, axis=None, smooth=False, rad1=None):
        """A cylinder from (c, r, z0) along `axis` (default up) for (z1 - z0) px."""
        axis = Vector(axis or (0, 0, 1)).normalized()
        base = V(c, r, z0)
        top = base + Vector((axis.x, -axis.y, axis.z)) * ((z1 - z0) * PX)
        up = (0, 1, 0) if abs(axis.z) > 0.7 else (0, 0, 1)
        first = self.nfaces()
        r1 = rad if rad1 is None else rad1
        lib.sweep(self.bm, [(*base, rad * PX, rad * PX), (*top, r1 * PX, r1 * PX)], sides=sides, mat=mat,
                  smooth=smooth, up=up)
        self.closed(first)

    def lathe(self, c, r, z, axis, prof, sides=16):
        """Revolve prof = [(radius px, height px along axis, mat), ...] about an axis through
        (c, r, z) px in (c, r, z) convention; a zero radius closes the end."""
        ax = Vector(axis).normalized()
        ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
        u = ax.cross(ref).normalized()
        w = ax.cross(u)
        first = self.nfaces()
        rings = []
        for rad, h, _ in prof:
            o = Vector((c, r, z)) + ax * h
            if rad <= 1e-6:
                rings.append([self.v(o.x, o.y, o.z)])
            else:
                rings.append([self.v(*(o + (u * math.cos(t) + w * math.sin(t)) * rad))
                              for t in (2 * math.pi * k / sides for k in range(sides))])
        for i in range(len(rings) - 1):
            a, b2 = rings[i], rings[i + 1]
            m = prof[i + 1][2]
            for k in range(sides):
                kk = (k + 1) % sides
                if len(a) == 1:
                    self.face((a[0], b2[kk], b2[k]), m)
                elif len(b2) == 1:
                    self.face((a[k], a[kk], b2[0]), m)
                else:
                    self.face((a[k], a[kk], b2[kk], b2[k]), m)
        if len(rings[0]) > 1:
            self.face(list(reversed(rings[0])), prof[0][2])
        if len(rings[-1]) > 1:
            self.face(rings[-1], prof[-1][2])
        self.closed(first)

    def bolt(self, c, r, z, mat, rad=0.4):
        self.cyl(c, r, z - 0.7, z + 0.2, rad, mat, sides=6)


# ---------------------------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------------------------

def materials(b, sprite):
    tag = "nsh2a115"

    def pal(key, idx, metallic, rough, emit=0.0, name=None):
        b.slots[key] = len(b.mats)
        b.mats.append(common.palette_material(sprite, idx, f"{tag}_{name or key}", metallic=metallic,
                                              roughness=rough, emission_strength=emit))
    pal("brass", PAL["brass"], 0.6 * METAL, 0.36)
    pal("brass_hatch", PAL["brass"], 0.55 * METAL, 0.42, name="hatch")
    pal("brass_dk", PAL["brass_dk"], 0.5 * METAL, 0.45)
    pal("rod", PAL["rod"], 0.65 * METAL, 0.3)
    pal("brass_dd", PAL["brass_dd"], 0.45 * METAL, 0.5)
    pal("grey", PAL["grey"], 0.55 * METAL, 0.46)
    pal("grey_lt", PAL["grey_lt"], 0.55 * METAL, 0.42)
    pal("grey_dk", PAL["grey_dk"], 0.5 * METAL, 0.5)
    pal("bed", PAL["bed"], 0.45 * METAL, 0.55)
    pal("deep", PAL["deep"], 0.2 * METAL, 0.8)
    pal("block", PAL["block"], 0.55 * METAL, 0.42)
    pal("window", PAL["window"], 0.0, 0.08)
    pal("lamp", PAL["lamp"], 0.0, 0.3, emit=2.0)
    pal("tip", PAL["tip"], 0.0, 0.3, emit=2.5)
    for i in DIRT:
        pal(f"dirt{i}", i, 0.0, 0.95)


TEXTURED = ("brass", "brass_hatch", "brass_dk", "brass_dd", "rod", "grey", "grey_lt", "grey_dk", "bed", "deep",
            "block")


def build_structure(b):
    M = b.mat
    BR, BH, BD, ROD = M("brass"), M("brass_hatch"), M("brass_dk"), M("rod")
    GR, GL, GD, BED, DEEP, BLK = M("grey"), M("grey_lt"), M("grey_dk"), M("bed"), M("deep"), M("block")

    # ---- bed ----
    b.prism(BED_OUTLINE, 0.0, BED_TOP, BED, ch=0.6)
    # a dark recessed field + raised rim round the lower octagon
    rim_in = [(c, r) for c, r in LOWER_RIM]
    lib_in = lib.inset([tuple(V(c, r, 0)[:2]) for c, r in rim_in], 1.3 * PX)
    pts = [tuple(V(c, r, 0)[:2]) for c, r in rim_in]
    for i in range(len(pts) - 1):  # open frame along the octagon (top edge left open under the side domes)
        lib.bevel_prism(b.bm, [pts[i], pts[i + 1], lib_in[i + 1], lib_in[i]], BED_TOP * PX - 0.01,
                        2.6 * PX, 0.35 * PX, mat=GD)
    # bolts on the rim
    for c, r in ((9.2, 43.2), (13.0, 48.6), (19.5, 49.1), (26.0, 48.4), (31.6, 44.6), (32.2, 39.2), (8.3, 38.4)):
        b.bolt(c, r, 2.6, GR, 0.35)
    # floor plates on the lower bed between the rim and the bottom dome (panel seams)
    b.rect(12.6, 44.0, 26.6, 48.4, BED_TOP - 0.1, 1.9, BED, ch=0.3, cut=1.2)

    # ---- pylons ----
    for side in (0, 1):
        def P(pts):
            return [(c, r) if side == 0 else (39.0 - c, r) for c, r in pts]
        # upper plate (rows 12.6-19.9), lower plate (20.9-26.9)
        b.prism(P([(4.4, 12.6), (7.8, 12.6), (7.8, 19.9), (2.6, 19.9), (2.6, 14.4)]), BED_TOP - 0.1, 4.4, GR, ch=0.6)
        b.prism(P([(2.6, 20.8), (8.0, 20.8), (8.0, 25.4), (6.4, 27.0), (2.6, 27.0)]), BED_TOP - 0.1, 4.0, GR, ch=0.7)
        # a dark seam strip between them, and a lit lip on the lower plate's top (the sprite's row 21)
        b.rect(*([2.8, 19.9, 7.6, 20.8] if side == 0 else [31.4, 19.9, 36.2, 20.8]), BED_TOP - 0.1, 3.0, DEEP, ch=0.2)
        b.rect(*([2.9, 21.0, 7.6, 21.9] if side == 0 else [31.4, 21.0, 36.1, 21.9]), 3.8, 4.35, GL, ch=0.3)
        for c, r in P([(3.5, 15.4), (3.5, 18.8), (3.5, 23.2), (3.5, 26.0), (6.9, 23.2)]):
            b.bolt(c, r, 4.4 if r < 20 else 4.0, GL, 0.3)
        # vertical louvres on the upper plate's outer face (the sprite's lighter outer column)
        for k in range(3):
            rr = 15.0 + k * 1.4
            b.rect(*(([2.3, rr, 2.7, rr + 0.7]) if side == 0 else ([36.3, rr, 36.7, rr + 0.7])), 1.6, 3.6, GD, ch=0.1)

    # ---- big dome ----
    b.dome(BIG, BR, BD, seg=64, rings=14)
    d = BIG
    # H-shaped hatch band (cols 13-24, rows 5.6-20.6): a base band and the hatches on it
    b.cplate(d, 13.2, 5.6, 24.0, 19.9, 0.35, BH, ch=0.3, n=12)
    b.cplate(d, 14.3, 6.6, 20.6, 10.2, 0.85, BH, ch=0.4, n=6)          # upper hatch
    b.cplate(d, 20.9, 6.6, 23.0, 10.2, 0.75, BH, ch=0.3, n=3)          # its side strip
    # vent grille in the upper hatch (dark recess + slats), right half
    b.cplate(d, 17.6, 7.4, 20.0, 9.6, 0.88, DEEP, ch=0.15, n=3)
    for k in range(4):
        rr = 7.55 + k * 0.52
        b.cplate(d, 17.75, rr, 19.85, rr + 0.25, 1.05, BD, ch=0.08, n=2, sink=0.3)
    b.cplate(d, 13.3, 10.5, 23.9, 12.5, 1.05, BH, ch=0.45, n=6)        # crossbar (lit row 11)
    b.cplate(d, 14.8, 12.5, 22.4, 14.5, 0.25, DEEP, ch=0.15, n=5)      # dark slot below it
    b.cplate(d, 14.4, 12.4, 15.8, 14.6, 0.9, BH, ch=0.25, n=2)         # notched tabs
    b.cplate(d, 21.4, 12.4, 22.8, 14.6, 0.9, BH, ch=0.25, n=2)
    b.cplate(d, 14.3, 14.7, 22.9, 19.3, 0.8, BH, ch=0.4, n=8)          # lower hatch
    b.cplate(d, 20.4, 15.3, 22.2, 18.7, 0.85, DEEP, ch=0.12, n=4)      # its grille
    for k in range(5):
        rr = 15.5 + k * 0.64
        b.cplate(d, 20.55, rr, 22.05, rr + 0.32, 1.02, BD, ch=0.08, n=2, sink=0.3)
    # hatch bolts
    for c, r, t in ((14.9, 7.3, 0.85), (14.9, 9.5, 0.85), (15.0, 15.4, 0.8), (15.0, 18.6, 0.8), (19.4, 18.6, 0.8)):
        b.bolt(c, r, Builder.surf(d, c, r) + t, BD, 0.25)
    # flank slots: dark floor inside a raised frame
    for c0, c1 in ((10.2, 12.0), (25.2, 27.0)):
        r0, r1 = 8.6, 14.4
        b.cplate(d, c0, r0, c1, r1, 0.12, DEEP, ch=0.1, n=4)
        w = 0.55
        b.cplate(d, c0 - w, r0 - w, c1 + w, r0, 0.55, BH, ch=0.2, n=3)
        b.cplate(d, c0 - w, r1, c1 + w, r1 + w, 0.55, BH, ch=0.2, n=3)
        b.cplate(d, c0 - w, r0, c0, r1, 0.55, BH, ch=0.15, n=4)
        b.cplate(d, c1, r0, c1 + w, r1, 0.55, BH, ch=0.15, n=4)
    # a seam ring round the cap just above the collar (panel line)
    ring = [(d["c"] + 1.0 * d["rx"] * math.cos(t), d["r"] + 1.0 * d["ry"] * math.sin(t)) for t in
            (2 * math.pi * k / 48 for k in range(48))]
    b.pipe([(c, r, d["collar"] + 0.15) for c, r in ring] + [(ring[0][0], ring[0][1], d["collar"] + 0.15)],
           0.32, BD, sides=6)

    # ---- elbow pipes from the big dome's flanks into the side domes ----
    for sgn, cx in ((1, 8.3), (-1, 30.7)):
        s0 = (cx, 18.2)
        z0 = Builder.surf(d, *s0)
        # flange on the dome
        b.cyl(cx, 18.0, z0 - 0.5, z0 + 0.6, 1.55, BD, sides=14, axis=(0, 1.0, 0.25))
        b.pipe([(cx, 18.6, z0 + 0.4), (cx, 20.4, z0 + 0.5), (cx, 22.0, z0 + 0.1), (cx, 23.4, z0 - 0.9),
                (cx, 24.3, z0 - 2.2), (cx, 25.6, 4.4)], 1.05, BR, sides=12)
        sd = SIDES[0 if sgn == 1 else 1]
        zs = Builder.surf(sd, cx, 26.6)
        b.cyl(cx, 26.4, zs - 0.6, zs + 0.9, 1.6, BD, sides=14, axis=(0, 0.45, 1.0))
    # two thin rods across the big dome's lower right (sprite: bright diagonal col 30 row 16 -> col 23 row 22),
    # rising from a clamp on the collar, hugging the cap and dropping into a socket on the neck plate
    for off in (0.0, 0.85):
        pts = []
        for k in range(9):
            u = k / 8
            c = 30.9 - 6.6 * u - off * 0.6
            r = 15.3 + 6.4 * u + off * 0.6
            z = max(Builder.surf(d, c, r), d["collar"] + 0.6) + 0.42
            pts.append((c, r, z))
        b.pipe(pts, 0.4, ROD, sides=8)
    # where the rods enter the cap: a flanged gland normal to the surface
    gc, gr = 31.0, 15.2
    ga = Vector(((gc - d["c"]) / d["rx"] ** 2 * d["h"], (gr - d["r"]) / d["ry"] ** 2 * d["h"], 1.0)).normalized()
    b.lathe(gc, gr, Builder.surf(d, gc, gr), tuple(ga), [(1.6, -0.8, BD), (1.6, 0.35, BD), (1.3, 0.6, BD), (0.0, 0.6, BD)],
            sides=14)
    b.rect(22.4, 20.9, 25.2, 23.4, 1.9, 4.0, GD, ch=0.35, cut=0.5)  # socket on the neck
    # bolts round the big dome's collar (machined ring)
    for k in range(28):
        t = 2 * math.pi * (k + 0.5) / 28
        c = d["c"] + (d["rx"] + d["lip"] * 0.6) * math.cos(t)
        r = d["r"] + (d["ry"] + d["lip"] * 0.6) * math.sin(t)
        b.bolt(c, r, d["collar"] - 0.05, BD, 0.28)

    # ---- neck ----
    b.prism([(9.6, 21.6), (29.4, 21.6), (29.0, 27.0), (24.0, 28.2), (15.0, 28.2), (10.0, 27.0)],
            BED_TOP - 0.1, 2.0, BED, ch=0.3)
    # diagonal braces (sprite: lit grey diagonal (10,23)->(17,27) and its shadowed twin)
    for sgn in (1, -1):
        def C(c):
            return c if sgn == 1 else 39.0 - c
        b.prism([(C(9.8), 22.6), (C(11.8), 22.6), (C(17.4), 26.4), (C(17.4), 27.8), (C(15.6), 27.8), (C(9.8), 24.2)],
                1.9, 3.3, GR if sgn == 1 else GD, ch=0.45)
    # pipes from the dome's foot into the housing
    for c in (17.6, 21.4):
        b.pipe([(c, 20.4, 2.6), (c, 23.0, 2.6), (c, 26.2, 2.9)], 0.55, GD, sides=8)
    b.cyl(17.6, 23.6, 2.0, 3.4, 0.85, GR, sides=8)
    b.cyl(21.4, 23.6, 2.0, 3.4, 0.85, GR, sides=8)
    # pipe housing (cols 15.8-23.2, rows 26.8-34.8) with a channel and a pipe at col 20
    b.rect(15.8, 26.8, 18.7, 34.8, BED_TOP - 0.1, 4.4, GR, ch=0.55)
    b.rect(20.9, 26.8, 23.2, 34.8, BED_TOP - 0.1, 4.4, GR, ch=0.55)
    b.rect(18.5, 26.8, 21.1, 34.8, BED_TOP - 0.1, 2.6, DEEP, ch=0.1)
    b.pipe([(20.0, 25.4, 3.1), (20.0, 35.2, 3.1)], 0.75, GL, sides=10)
    for r in (28.0, 31.0, 33.8):
        b.pipe([(20.0, r - 0.3, 3.1), (20.0, r + 0.3, 3.1)], 0.95, GR, sides=10)
    for c, r in ((16.6, 27.8), (16.6, 33.8), (22.4, 27.8), (22.4, 33.8)):
        b.bolt(c, r, 4.4, GL, 0.3)

    # ---- side domes and gun blocks ----
    for k, sd in enumerate(SIDES):
        dx = 22.0 * k
        b.dome(sd, BR, BD, seg=40, rings=10)
        # outer end boss (grey) and inner ring (brass)
        oc = sd["c"] - sd["rx"] - sd["lip"] + 0.1 if k == 0 else sd["c"] + sd["rx"] + sd["lip"] - 0.1
        so = -1 if k == 0 else 1
        b.pipe([(oc - so * 0.6, 31.0, 3.0), (oc + so * 0.3, 31.0, 3.0)], 1.8, GL, sides=14)
        b.pipe([(oc + so * 0.3, 31.0, 3.0), (oc + so * 0.55, 31.0, 3.0)], 1.05, GD, sides=12)
        # gun block (cols 5.6-10.8, rows 29.5-35.6)
        g0, g1 = 5.6 + dx, 10.8 + dx
        b.rect(g0, 29.5, g1, 35.6, 1.2, 6.2, BLK, ch=0.5, cut=0.5)
        b.rect(g0 + 2.1, 30.0, g1 - 0.9, 35.0, 6.0, 6.75, GL, ch=0.3)              # lit top plate (cols 8-9)
        b.rect(g0 + 0.5, 30.2, g0 + 1.7, 34.2, 6.0, 6.5, GD, ch=0.15)              # dark vent strip (cols 6-7)
        for kk in range(4):
            rr = 30.6 + kk * 0.9
            b.rect(g0 + 0.6, rr, g0 + 1.6, rr + 0.35, 6.2, 6.62, BLK, ch=0.08)
        b.rect(g0 + 2.6, 29.0, g0 + 3.5, 29.9, 5.5, 7.1, GR, ch=0.15)              # studs
        b.rect(g0 + 3.9, 29.0, g0 + 4.8, 29.9, 5.5, 7.1, GR, ch=0.15)
        # indicator window down the right face (sprite col 10) with a lamp (row 32)
        b.rect(g1 - 0.15, 30.2, g1 + 0.45, 34.2, 3.0, 5.6, M("window"), ch=0.08)
        b.rect(g1 - 0.1, 32.1, g1 + 0.55, 32.9, 3.6, 4.6, M("lamp"), ch=0.05)
        # main barrel (col 6.5 to row 38: the sprite's see-through muzzle) and a stub at col 10
        bc = 6.5 + dx
        b.pipe([(bc, 35.2, 3.0), (bc, 36.0, 3.0)], 1.25, GD, sides=12)
        b.pipe([(bc, 36.0, 3.0), (bc, 37.6, 3.0)], 0.85, GL, sides=12)
        b.lathe(bc, 37.5, 3.0, (0, 1, 0), [(1.0, 0.0, GL), (1.0, 0.55, GL), (0.82, 0.7, GL), (0.55, 0.7, GL),
                                            (0.55, 0.35, M("tip")), (0.0, 0.35, M("tip"))], sides=14)
        b.pipe([(10.2 + dx, 35.2, 2.6), (10.2 + dx, 36.9, 2.6)], 0.6, GR, sides=8)

    # ---- bottom dome and gun port ----
    b.dome(BOT, BR, BD, seg=40, rings=10)
    pc, pr = PORT
    pz = Builder.surf(BOT, pc, pr)
    ax = Vector(((pc - BOT["c"]) / BOT["rx"] * 0.6, (pr - BOT["r"]) / BOT["ry"] * 0.6, 1.0)).normalized()
    nv = tuple(ax)  # (c, r, z) convention, as cyl takes it
    b.lathe(pc, pr, pz, nv, [(2.25, -1.2, M("brass_dd")), (2.25, 0.35, M("brass_dd")), (1.95, 0.6, M("brass_dd")),
                             (1.7, 0.6, M("brass_dd")), (1.55, 0.45, M("brass_dd")), (1.55, 0.1, DEEP),
                             (0.0, 0.1, DEEP)], sides=24)

    # ---- brackets on the lower bed ----
    for c0 in (7.8, 26.8):
        b.rect(c0, 37.8, c0 + 4.4, 42.2, BED_TOP - 0.1, 3.4, GD, ch=0.5, cut=0.5)
        b.rect(c0 + 0.6, 38.4, c0 + 3.8, 41.6, 3.2, 3.8, GD, ch=0.3)
        b.bolt(c0 + 1.2, 41.0, 3.8, GL, 0.3)
        b.bolt(c0 + 3.2, 41.0, 3.8, GL, 0.3)


def build_floor(b, grid):
    """Dirt: 2 x 2 px cells in the sprite's dirt colours, on a thin closed slab."""
    first = b.nfaces()
    verts = {}

    def vert(i, j, z):
        key = (i, j, z)
        if key not in verts:
            verts[key] = b.v(i, j, z)
        return verts[key]
    for j in range(0, H, 2):
        for i in range(0, W, 2):
            pix = [grid[j + dj][i + di] for dj in (0, 1) for di in (0, 1)]
            dirt = [v for v in pix if 16 <= v <= 21] or [18]
            idx = min(DIRT, key=lambda g: abs(g - sum(dirt) / len(dirt)))
            b.face((vert(i, j + 2, 0.25), vert(i + 2, j + 2, 0.25), vert(i + 2, j, 0.25), vert(i, j, 0.25)),
                   b.mat(f"dirt{idx}"))
    # closed underneath: a bottom and four walls
    z0 = -0.4
    lo = [b.v(0, 0, z0), b.v(W, 0, z0), b.v(W, H, z0), b.v(0, H, z0)]
    b.face(lo, b.mat("dirt17"))
    edges = []
    for k in range(4):
        a, c = [(0, 0), (W, 0), (W, H), (0, H)][k], [(0, 0), (W, 0), (W, H), (0, H)][(k + 1) % 4]
        if a[1] == c[1]:  # along columns
            step = 2 if c[0] > a[0] else -2
            pts = [(x, a[1]) for x in range(a[0], c[0] + step, step)]
        else:
            step = 2 if c[1] > a[1] else -2
            pts = [(a[0], y) for y in range(a[1], c[1] + step, step)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            b.face((vert(x0, y0, 0.25), vert(x1, y1, 0.25), b.v(x1, y1, z0), b.v(x0, y0, z0)), b.mat("dirt17"))
    bmesh.ops.remove_doubles(b.bm, verts=list({v for f in b.bm.faces[first:] for v in f.verts}), dist=1e-6)
    b.bm.faces.ensure_lookup_table()
    for f in b.bm.faces[first:]:
        f.normal_update()
        c = f.calc_center_median()
        want = Vector((0, 0, 1)) if abs(f.normal.z) > 0.5 and c.z > 0 else None
        if want is None:
            if abs(f.normal.z) > 0.5:
                want = Vector((0, 0, -1))
            else:
                want = Vector((c.x, c.y, 0))
        if f.normal.dot(want) < 0:
            f.normal_flip()


# ---------------------------------------------------------------------------------------------
# Finishing: cull hidden faces, bake, split, outline shell, export
# ---------------------------------------------------------------------------------------------

def to_object(b, name, coll):
    bm = b.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in b.mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def cull_hidden(obj, grid=4, ndirs=40):
    """Delete faces no ray from outside reaches (usp_talon.cull_hidden)."""
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


def shade(obj, angle=32.0):
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(angle))


TINT = (1.0, 1.0, 1.0)  # neutral: usp_talon.py's cool tint (D53) turned the brass olive


def bake_maps(obj, out_dir, slots, size=1024, samples=64):
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
    col_img = bpy.data.images.new("nsh2a115_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nsh2a115_rm", size // 2, size // 2, alpha=False)
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
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
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
    for key in TEXTURED:
        m = mats[slots[key]]
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
        for m in obj.data.materials:
            me.materials.append(m)
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    grid, colors, x0, y0, layout = lib.assembly_grid(ROOT, "newsh2-115")
    sprite = common.load_sprite(ROOT, "newsh2-115")
    sprite["colors"] = colors
    coll = common.reset_collection(NAME)

    b = Builder()
    materials(b, sprite)
    slots = dict(b.slots)
    mats = list(b.mats)
    build_structure(b)
    struct = to_object(b, NAME + "_structure", coll)
    cull_hidden(struct)
    shade(struct)
    fb = Builder()
    fb.slots, fb.mats = slots, mats
    build_floor(fb, grid)
    floor = to_object(fb, NAME + "_floor", coll)

    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        bake_maps(struct, tempfile.mkdtemp(prefix="nsh2a115_bake_"), slots)
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(struct, coll, voxel=0.014, faces=2400)

    # Join the floor in, then cull the floor cells under the bed.
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    struct.select_set(True)
    floor.select_set(True)
    bpy.context.view_layer.objects.active = struct
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = NAME
    cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: whole {len(obj.data.polygons)} faces, {tris} triangles")

    pieces_layout = [(e["model"], e["cx"] - x0 - W / 2, e["cy"] - y0 - H / 2) for e in layout]
    pieces = common.split_assembly(obj, pieces_layout, coll)
    shells = split_open(shell, pieces_layout, coll, "_outline")
    shell.hide_render = True
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    for name, cx, cy in pieces_layout:
        p = pieces[name]
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        s = shells[name]
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        s.hide_render = True
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [p, s], f"enemies/{name}", data["sprites"], image_format=fmt)
        pt = sum(len(q.vertices) - 2 for q in p.data.polygons)
        print(f"{NAME}: piece {name} at ({cx}, {cy}) px: {pt} triangles; shell {len(s.data.polygons)} faces")

    out = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    if out:
        import tempfile
        out = Path(out)
        ref = lib.composite_png(grid, colors, Path(tempfile.mkdtemp()) / "assembly.png", pad_to=(W, H))
        common.render_preview([obj], str(out), str(ref), size=W / 12, view_px=640)
        for name, _, _ in pieces_layout:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
    return dict(obj=obj, pieces=pieces, shells=shells, grid=grid, layout=pieces_layout)


if __name__ == "__main__":
    main()
