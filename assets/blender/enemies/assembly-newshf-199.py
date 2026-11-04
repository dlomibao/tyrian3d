"""Right corner tower of the red newshf fortress (assembly of newshf-161, 163, 199, 201): a
hard-surface 3D version of its sprites (M0 shared foundations; D74 inner edge, D51 outline shells).

Seen in episode 1 (Savara, Savara V), 2 (Torm), 3 (Savara Y) and 4 (Savara IV). The sprite is a
48 x 56 px block (pieces 161 | 163 over 199 | 201). Reading it as a machine:

- Three identical launcher modules, 12 columns apart and staggered down the screen (tips at rows 1,
  6, 13). Each is a LANCE (7 px wide, 29 rows) lying in a cradle between two 1 px GUIDE RAILS and
  cantilevered past the housing's front for 7-12 rows, with a trestle under its tip. Lance section
  (cross-section first): flat keel, vertical flanks, a superelliptic crown (shoulder drop 1.7 px over
  2 px), 45-degree keel chamfers. Along it (pchip stations): a rounded chamfered nose (114), a fore
  body (116), a raised machined collar (119), the chamber (118) with a recessed inspection window
  (114) and a glowing core stud (120), a raised hot collar (121), the aft body (116) and a dark root
  (113); V-grooves at every joint, a flush hot inlay strip (122) along the west shoulder where the
  sprite draws its yellow line. The root necks down to a 4 px shaft that enters the bulkhead.
- Behind each lance a BULKHEAD (the lit row 31 / 36 / 43) with a lower gland in its middle where the
  shaft enters (the sprite's darker middle pixels), then a BREECH BLOCK of two armour plates either
  side of a RETRACTION CHANNEL that runs out of the rear wall. Each plate has a wide 45-degree
  chamfer on its west top edge (the sprite's lit 1 px column on every plate's west side), panel
  seams and bolt heads. Module A's channel is closed by a sliding cover and crossed by a cable
  ROLLER (rows 44-51) on two bearing lugs; its axle runs east into a recess in block B.
- On the outside (east) a low round BASTION: a flat top (67) with a rounded lit rim (68), a pchip
  plan edge fitted to the inner mask, seams, a bolted hatch and a vent grille.
- A dark PLINTH (65) under everything: the slot and channel floors.

The top view follows the sprite's inner mask (D74, docs/agents/OUTLINE-BORDER.md) row by row. Palette
materials pal_<index> carry the sprite's own index per part (medians, ink and shading tails out).
Texture: an AO / edge colour multiplier and roughness-metal bake only (the ships' bake), no concept
projection. Each piece is exported with an outline shell (common.outline_shell, D51).

Built in sprite px: u = column edge (0..48, west -> east), v = row edge (0..56, screen top -> bottom),
z up (ground 0). Blender: X = (u - 24) / 12, Y = (28 - v) / 12, Z = z / 12: the block's centre
(screen 214, -3) is the origin, as in lib_b100.

    blender --background --factory-startup --python assets/blender/enemies/assembly-newshf-199.py
        [-- [--out a.glb] [--pieces-dir dir] [--no-bake] [--preview out.png]]

By default each piece is exported through the game contract (public/models/enemies/<piece>.glb and
src/render/spriteModels/<piece>.json, common.export_sprite_model), as lib_b100.main did. --out
instead writes one review .glb with the four pieces in place, each with its outline shell (nothing
in the repo is touched); --pieces-dir also writes <piece>.glb (each at its own origin) there.
--preview renders the whole tower beside the first piece's sprite (common.render_preview).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)

NAME = "assembly-newshf-199"
PIECES = ["newshf-199", "newshf-201", "newshf-161", "newshf-163"]
CX0, CY0 = 214, -3  # screen px of the block's centre (its Blender origin)
PX = 1 / 12
HERE = Path(__file__).resolve().parent


# --- small maths -------------------------------------------------------------------------------

def pchip(xs, ys):
    """Monotone cubic interpolation (Fritsch-Carlson): stations never overshoot."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    if n == 2:
        m = [d[0], d[0]]
    else:
        for i in range(1, n - 1):
            if d[i - 1] * d[i] > 0:
                w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        m[0], m[-1] = d[0], d[-1]

    def f(x):
        i = 0
        while i < n - 2 and x > xs[i + 1]:
            i += 1
        t = min(1.0, max(0.0, (x - xs[i]) / h[i]))
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# --- materials: the sprite's palette index per part ---------------------------------------------
# (pal, metallic, roughness, emission strength). Satin metal for the housing; the lances are the
# fortress's red energy rods, lightly self-lit so they stay red in shadow, their hot bands brighter.
PAL = {
    65: (0.25, 0.75, 0.0),   # plinth, slot and channel floors
    66: (0.35, 0.55, 0.0),   # axle, recesses, seams, trestles
    67: (0.3, 0.55, 0.0),    # bastion top, roller, covers
    68: (0.4, 0.45, 0.0),    # bastion rim
    69: (0.4, 0.45, 0.0),    # plates
    70: (0.4, 0.45, 0.0),    # plate walls
    71: (0.4, 0.42, 0.0),    # rear plates
    72: (0.42, 0.4, 0.0),    # bearing lugs
    73: (0.45, 0.38, 0.0),   # rails, bulkheads
    74: (0.45, 0.36, 0.0),   # rails
    75: (0.45, 0.35, 0.0),   # ridge
    76: (0.45, 0.34, 0.0),   # outer rail
    113: (0.25, 0.45, 0.35),  # lance root
    114: (0.25, 0.45, 0.4),   # nose, window
    116: (0.25, 0.42, 0.6),   # fore / aft body
    118: (0.2, 0.4, 0.9),     # chamber
    119: (0.2, 0.38, 1.4),    # collar
    120: (0.1, 0.35, 2.2),    # core stud
    121: (0.1, 0.35, 2.0),    # hot collar
    122: (0.05, 0.3, 2.8),    # hot inlay strip
}
SLOT = {p: i for i, p in enumerate(PAL)}


def make_materials(sprite):
    mats = []
    for p, (met, rough, em) in PAL.items():
        mats.append(common.palette_material(sprite, p, "nshfA", metallic=met, roughness=rough,
                                            emission_strength=em))
    return mats


# --- mesh building (sprite px) --------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def face(self, verts, pal):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        f.material_index = SLOT[pal]
        return f

    def loft(self, rings, pals, cap0=True, cap1=True, seg_pals=None):
        """Join rings of (u, v, z) points (equal lengths); `pals` one index or one per band;
        `seg_pals` {ring segment: pal} overrides it for those segments along the whole loft."""
        vs = [[self.bm.verts.new(p) for p in r] for r in rings]
        for b, (r0, r1) in enumerate(zip(vs, vs[1:])):
            pal = pals[b] if isinstance(pals, (list, tuple)) else pals
            n = len(r0)
            for i in range(n):
                j = (i + 1) % n
                self.face((r0[i], r0[j], r1[j], r1[i]), (seg_pals or {}).get(i, pal))
        p0 = pals[0] if isinstance(pals, (list, tuple)) else pals
        p1 = pals[-1] if isinstance(pals, (list, tuple)) else pals
        if cap0:
            self.face(list(reversed(vs[0])), p0)
        if cap1:
            self.face(vs[-1], p1)

    def hull(self, points, pal):
        bm = self.bm
        verts = [bm.verts.new(p) for p in points]
        res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(bm, geom=junk, context="VERTS")
        live = [v for v in verts if v.is_valid]
        faces = list({f for v in live for f in v.link_faces})
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                                 edges=list({e for f in faces for e in f.edges}))
        for f in {f for v in verts if v.is_valid for f in v.link_faces}:
            f.material_index = SLOT[pal]

    def box(self, u0, u1, v0, v1, z0, z1, pal, ch=0.25, chz=None):
        """A box with chamfered top edges (the bottom sits on something, so it stays square)."""
        chz = ch if chz is None else chz
        pts = [(u0, v0, z0), (u1, v0, z0), (u1, v1, z0), (u0, v1, z0)]
        if ch <= 0 and chz <= 0:
            pts += [(u0, v0, z1), (u1, v0, z1), (u1, v1, z1), (u0, v1, z1)]
        else:
            for u, su in ((u0, 1), (u1, -1)):
                for v, sv in ((v0, 1), (v1, -1)):
                    pts += [(u + su * ch, v + sv * ch, z1), (u, v + sv * ch, z1 - chz), (u + su * ch, v, z1 - chz)]
        self.hull(pts, pal)

    def bar(self, sec, v0, v1, pal, c0=0.3, c1=0.3, seg_pals=None):
        """A prism along v with section `sec` [(u, z)...] (convex), its two ends chamfered at 45
        degrees on top by c0 / c1 (the section squashed down by c at the end ring)."""
        zb = min(z for _, z in sec)
        zt = max(z for _, z in sec)

        def end(c):
            k = (zt - c - zb) / (zt - zb)
            return [(u, zb + (z - zb) * k) for u, z in sec]
        rings = []
        if c0 > 0:
            rings.append([(u, v0, z) for u, z in end(c0)])
            rings.append([(u, v0 + c0, z) for u, z in sec])
        else:
            rings.append([(u, v0, z) for u, z in sec])
        if c1 > 0:
            rings.append([(u, v1 - c1, z) for u, z in sec])
            rings.append([(u, v1, z) for u, z in end(c1)])
        else:
            rings.append([(u, v1, z) for u, z in sec])
        self.loft(rings, pal, seg_pals=seg_pals)

    def prism(self, outline, z0, z1, pal):
        bot = [self.bm.verts.new((u, v, z0)) for u, v in outline]
        top = [self.bm.verts.new((u, v, z1)) for u, v in outline]
        n = len(outline)
        for i in range(n):
            j = (i + 1) % n
            self.face((bot[i], bot[j], top[j], top[i]), pal)
        self.face(list(reversed(bot)), pal)
        self.face(top, pal)

    def cyl_u(self, u0, u1, v, z, r, pal, sides=16, ch=0.0):
        def ring(u, rr):
            return [(u, v + rr * math.cos(2 * math.pi * (i + 0.5) / sides),
                     z + rr * math.sin(2 * math.pi * (i + 0.5) / sides)) for i in range(sides)]
        if ch > 0:
            self.loft([ring(u0, r - ch), ring(u0 + ch, r), ring(u1 - ch, r), ring(u1, r - ch)], pal)
        else:
            self.loft([ring(u0, r), ring(u1, r)], pal)

    def bolt(self, u, v, z, pal=66, r=0.33, h=0.22):
        """A hex bolt head standing on a surface at height z."""
        ring = lambda zz, rr: [(u + rr * math.cos(math.pi / 3 * i), v + rr * math.sin(math.pi / 3 * i), zz) for i in range(6)]  # noqa: E731
        self.loft([ring(z - 0.05, r), ring(z + h, r), ring(z + h + 0.08, r * 0.7)], pal)


# --- the parts -----------------------------------------------------------------------------------

Z_PLINTH = 2.5
LW = 7.0              # lance width (px)
LZ0, LZ1 = 2.6, 6.4   # lance keel and crown
L_SH = 1.7            # shoulder drop
L_RU = 2.0            # shoulder run (horizontal)
RZ = 7.2              # guide rail top
PLATE_Z = 6.2         # breech plate top
ROLL_Z = 4.1          # roller axis (flange radius 4.0: clears the ground)


def lance_section(uc, k=1.0, kz=1.0, dz=0.0):
    """The lance's cross-section at width scale k, height scale kz (u, z): keel chamfers, vertical
    flanks, superelliptic shoulders, a slight crown."""
    hw = LW / 2 * k
    z0 = LZ0
    z1 = LZ0 + (LZ1 - LZ0) * kz + dz
    zs = z1 - L_SH * kz
    ru = min(L_RU * k, hw - 0.3)
    c = 0.35 * k
    pts = [(uc - hw + c, z0), (uc + hw - c, z0), (uc + hw, z0 + c)]
    N = 5
    for i in range(N + 1):  # east shoulder: from the flank top round to the crown
        a = (math.pi / 2) * i / N
        ca, sa = math.cos(a), math.sin(a)
        e = 2 / 2.6
        x = (abs(ca) ** e) * (1 if ca >= 0 else -1)
        y = abs(sa) ** e
        pts.append((uc + hw - ru + ru * x, zs + (z1 - zs) * y))
    for i in range(N, -1, -1):  # west shoulder, mirrored
        a = (math.pi / 2) * i / N
        ca, sa = math.cos(a), math.sin(a)
        e = 2 / 2.6
        x = abs(ca) ** e
        y = abs(sa) ** e
        pts.append((uc - hw + ru - ru * x, zs + (z1 - zs) * y))
    pts.append((uc - hw, z0 + c))
    # Dedupe the two crown points (east i=N and west i=N meet at the crown's ends, not the centre).
    return pts


def lance_top_z(dx, k=1.0):
    """Height of the lance's top at offset dx from its axis (for things set on it)."""
    hw = LW / 2 * k
    ru = L_RU * k
    a = abs(dx)
    if a <= hw - ru:
        return LZ1
    t = min(1.0, (a - (hw - ru)) / ru)
    return LZ1 - L_SH * (1 - (1 - t ** 2.6) ** (1 / 2.6))


def lance(M, c0, r0, tip=0.0):
    """One module's lance: content columns c0..c0+6, content rows from r0 (tip) for 29 rows."""
    uc = c0 + LW / 2
    V = lambda k: r0 + k  # noqa: E731
    # Stations (k from the tip): (k, width scale, height scale, pal of the band that follows).
    st = []
    nose = [(tip, 0.80, 0.58), (tip + 0.3, 0.9, 0.78), (tip + 0.8, 0.97, 0.92), (tip + 1.5, 1.0, 1.0)]
    for k, w, h in nose:
        st.append((k, w, h, 114))
    g = 0.12  # groove half width
    gd = 0.94  # groove depth (scale)

    def groove(k, pal_after):
        st.append((k - g, 1.0, 1.0, 114 if False else st[-1][3]))
        st.append((k, gd, 0.97, pal_after))
        st.append((k + g, 1.0, 1.0, pal_after))

    def collar(k0, k1, pal, pal_after, s=1.07):
        cz = 0.12
        st.append((k0, 1.0, 1.0, st[-1][3]))
        st.append((k0 + cz, s, 1.0 + (s - 1) * 1.6, pal))
        st.append((k1 - cz, s, 1.0 + (s - 1) * 1.6, pal))
        st.append((k1, 1.0, 1.0, pal_after))

    groove(2.0, 116)
    collar(6.0, 7.0, 119, 118)
    collar(14.0, 15.0, 121, 116)
    groove(21.0, 113)
    # Root: the lance's rear end, chamfered, at k 29.
    st.append((28.6, 1.0, 1.0, 113))
    st.append((29.0, 0.9, 0.9, 113))
    # The band material between stations i and i+1 is st[i][3].
    rings = [[(u, V(k), z) for u, z in lance_section(uc, w, h)] for k, w, h, _ in st]
    pals = [s[3] for s in st[:-1]]
    M.loft(rings, pals)
    # The neck: a 4 px round shaft from the root into the bulkhead gland.
    sides = 12
    zc = 4.4
    def nring(k, r):
        return [(uc + r * math.cos(2 * math.pi * (i + 0.5) / sides), V(k), zc + r * 0.85 * math.sin(2 * math.pi * (i + 0.5) / sides)) for i in range(sides)]
    M.loft([nring(28.8, 1.7), nring(30.9, 1.7)], 113)
    # Inspection window (cols c0+2, rows k7..k10): a dark recessed lens in a chamfered bezel.
    zt = lance_top_z(-1.0)
    M.box(c0 + 1.85, c0 + 3.15, V(6.95), V(11.05), zt - 0.8, zt + 0.12, 116, ch=0.18)
    M.box(c0 + 2.05, c0 + 2.95, V(7.15), V(10.85), zt - 0.8, zt + 0.06, 114, ch=0.1)
    # Core stud (col c0+3, rows k8-9): a glowing boss beside the window.
    zc2 = lance_top_z(0.0)
    M.box(c0 + 3.15, c0 + 3.95, V(8.05), V(9.95), zc2 - 0.6, zc2 + 0.22, 120, ch=0.18)
    # Hot inlay strip down the west shoulder (col c0, rows k4..k13): flush, not a bump.
    for k0, k1 in ((4.0, 5.95), (7.05, 13.95)):
        rings = []
        for k in (k0, k1):
            ring = []
            for dx, dz in ((0.12, -0.3), (0.88, -0.3), (0.88, 0.1), (0.12, 0.1)):
                x = c0 + dx
                ring.append((x, V(k), lance_top_z(x - uc) + dz))
            rings.append(ring)
        M.loft(rings, 122)
    # Trestle under the cantilevered tip: a saddle on a tapered post with a foot pad.
    kt = 4.0 + tip * 0.5
    M.loft([[(uc - 1.6, V(kt - 1.2), 0.0), (uc + 1.6, V(kt - 1.2), 0.0), (uc + 1.6, V(kt + 1.2), 0.0), (uc - 1.6, V(kt + 1.2), 0.0)],
            [(uc - 1.6, V(kt - 1.2), 0.45), (uc + 1.6, V(kt - 1.2), 0.45), (uc + 1.6, V(kt + 1.2), 0.45), (uc - 1.6, V(kt + 1.2), 0.45)],
            [(uc - 0.9, V(kt - 0.6), 0.75), (uc + 0.9, V(kt - 0.6), 0.75), (uc + 0.9, V(kt + 0.6), 0.75), (uc - 0.9, V(kt + 0.6), 0.75)],
            [(uc - 0.9, V(kt - 0.6), 2.0), (uc + 0.9, V(kt - 0.6), 2.0), (uc + 0.9, V(kt + 0.6), 2.0), (uc - 0.9, V(kt + 0.6), 2.0)],
            [(uc - 2.6, V(kt - 0.8), 2.3), (uc + 2.6, V(kt - 0.8), 2.3), (uc + 2.6, V(kt + 0.8), 2.3), (uc - 2.6, V(kt + 0.8), 2.3)],
            [(uc - 2.6, V(kt - 0.8), 2.7), (uc + 2.6, V(kt - 0.8), 2.7), (uc + 2.6, V(kt + 0.8), 2.7), (uc - 2.6, V(kt + 0.8), 2.7)]],
           [66, 66, 66, 66, 67])


def rail(M, u0, u1, v0, v1, pal, z1=RZ, nose=1.4, back=0.3):
    """A 1 px guide rail: box section with a chamfered top, its front end sloping down to the
    plinth (a ramped nose), its back end chamfered."""
    ch = 0.25

    def sec(zt):
        return [(u0, Z_PLINTH), (u1, Z_PLINTH), (u1, zt - ch), (u1 - ch, zt), (u0 + ch, zt), (u0, zt - ch)]
    rings = []
    N = 5
    for i in range(N + 1):
        t = i / N
        zt = Z_PLINTH + 1.1 + (z1 - Z_PLINTH - 1.1) * math.sin(t * math.pi / 2)
        rings.append([(u, v0 + nose * t, z) for u, z in sec(zt)])
    rings.append([(u, v1 - back, z) for u, z in sec(z1)])
    rings.append([(u, v1, z) for u, z in sec(z1 - back)])
    M.loft(rings, pal)


def plate(M, u0, u1, v0, v1, z1, pal, cw=1.0, ce=0.2, cn=0.25, cs=0.25, edge_pal=None):
    """An armour plate on the plinth: a wide 45-degree chamfer on its west top edge (cw, the lit
    column the sprite draws on every plate's west side) and small ones elsewhere. The west chamfer
    face takes `edge_pal` (the sprite's lit column) when given."""
    z0 = Z_PLINTH
    sec = [(u0, z0), (u1, z0), (u1, z1 - ce), (u1 - ce, z1), (u0 + cw, z1), (u0, z1 - cw)]
    M.bar(sec, v0, v1, pal, c0=cn, c1=cs, seg_pals={4: edge_pal} if edge_pal is not None else None)


def bulkhead(M, u0, u1, v0, v1, uc, pal_side=73, pal_mid=69):
    """The lit bulkhead behind a lance: one continuous bar across the cradle from rail to rail, as
    high as the rails, so rails and bulkhead read as one light U round the lance's foot (the
    sprite's ring). The lance's shaft enters its north face through a collar."""
    zt = RZ
    sec = [(u0, Z_PLINTH), (u1, Z_PLINTH), (u1, zt - 0.25), (u1 - 0.25, zt), (u0 + 0.25, zt), (u0, zt - 0.25)]
    M.bar(sec, v0, v1, pal_side, c0=0.3, c1=0.3)
    # A collar ring on the bulkhead's face where the shaft enters.
    M.loft([[(uc + 2.0 * math.cos(2 * math.pi * (i + 0.5) / 12), v0 + dv, 4.4 + 1.85 * math.sin(2 * math.pi * (i + 0.5) / 12)) for i in range(12)]
            for dv in (-0.15, 0.25)], 66)


# Bastion plan: its outer (east) edge, fitted to the inner mask row by row (row r centre = r + 0.5).
OUT_V = [27.2, 28.5, 29.5, 30.5, 31.5, 32.5, 33.5, 34.5, 35.5, 36.5, 37.5, 39.5, 42.5, 45.5, 46.5, 47.5,
         48.5, 49.5, 50.5, 51.5, 52.5, 53.5, 54.5, 55.45]
OUT_U = [36.0, 37.0, 38.0, 38.9, 39.4, 40.2, 40.9, 41.3, 41.9, 42.4, 42.9, 43.1, 43.15, 43.05, 42.9, 42.6,
         41.9, 41.3, 41.3, 41.1, 40.4, 40.0, 39.4, 39.0]
outer_u = pchip(OUT_V, OUT_U)
BZ, BR = 5.6, 2.0


def bastion(M):
    vs = []
    v = 27.2
    while v < 55.45:
        vs.append(v)
        v += 0.5
    vs.append(55.45)

    def ring(v, ui):
        uo = max(ui + 0.3, outer_u(v))
        H = 1.4 + (BZ - 1.4) * smoothstep(27.2, 30.6, v)
        R = min(BR, (uo - ui) * 0.7, H * 0.85)
        ch = min(0.3, H * 0.1)
        ring = [(ui, v, 0.0), (ui, v, H - ch), (ui + ch, v, H)]
        for i in range(8):
            a = (math.pi / 2) * i / 7
            ring.append((uo - R + R * math.sin(a), v, H - R + R * math.cos(a)))
        ring.append((uo, v, 0.0))
        return ring
    # The inner wall steps from u 36 to 37 at v 43.45: two lofts meeting there.
    _bastion_loft(M, [ring(v, 36.0) for v in vs if v < 43.45] + [ring(43.45, 36.0)])
    _bastion_loft(M, [ring(43.45, 37.0)] + [ring(v, 37.0) for v in vs if v > 43.45])
    # Seams across the flat top that run on down the rounded rim to the ground (armour segment
    # joints), a bolted hatch and a vent grille.
    for v in (33.5, 41.5, 49.5):
        ui = 36.6 if v < 43.4 else 37.6
        uo = outer_u(v)
        ue = uo - BR
        M.box(ui, ue + 0.05, v - 0.14, v + 0.14, BZ - 0.3, BZ + 0.02, 66, ch=0.0, chz=0.0)
        rings = []
        for dv in (-0.14, 0.14):
            ring = []
            for i in range(8):
                a = (math.pi / 2) * i / 7
                ring.append((ue + (BR + 0.03) * math.sin(a), v + dv, BZ - BR + (BR + 0.03) * math.cos(a)))
            ring += [(uo + 0.03, v + dv, 0.2), (uo - 0.3, v + dv, 0.2)]
            ring += [(ue + (BR - 0.3) * math.sin(a), v + dv, BZ - BR + (BR - 0.3) * math.cos(a))
                     for a in [(math.pi / 2) * i / 7 for i in range(7, -1, -1)]]
            rings.append(ring)
        M.loft(rings, 66)
    M.box(37.9, 40.9, 43.4, 47.6, BZ - 0.2, BZ + 0.28, 67, ch=0.18)
    for u, v in ((38.35, 43.85), (40.45, 43.85), (38.35, 47.15), (40.45, 47.15)):
        M.bolt(u, v, BZ + 0.28, 66, r=0.22, h=0.12)
    for i in range(3):
        v = 36.0 + i * 1.1
        M.box(37.4, 40.6, v, v + 0.55, BZ - 0.25, BZ + 0.05, 65, ch=0.0, chz=0.0)
    for i in range(2):
        v = 51.0 + i * 1.3
        M.box(37.8, 39.7, v, v + 0.7, BZ - 0.2, BZ + 0.12, 66, ch=0.12)


def _bastion_loft(M, rings, cap0=True, cap1=True):
    vs = [[M.bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    for r0, r1 in zip(vs, vs[1:]):
        for i in range(n):
            j = (i + 1) % n
            # Segments: 0 inner wall, 1 inner chamfer, 2 flat top, 3..9 rim, 10 outer foot, 11 bottom.
            pal = 67 if i <= 2 else (68 if i <= 10 else 66)
            M.face((r0[i], r0[j], r1[j], r1[i]), pal)
    if cap0:
        M.face(list(reversed(vs[0])), 67)
    if cap1:
        M.face(vs[-1], 67)


def build(M):
    # --- plinth: the housing's dark lower body and slot floors (z 0..2.5), stepped front edge ---
    plinth = [(1, 14), (2, 14), (2, 13), (3, 13), (3, 14), (11, 14), (11, 15), (12, 15), (12, 16), (14, 16),
              (14, 15), (22, 15), (22, 19), (23, 19), (23, 20), (34, 20), (34, 26), (35, 26), (35, 27),
              (36.4, 27), (36.4, 43.4), (37.4, 43.4), (37.4, 55.45), (1, 55.45)]
    M.prism(plinth, 0.0, Z_PLINTH, 65)

    # --- lances A, B, C (content columns 3-9 / 15-21 / 27-33, tips at rows 1 / 6 / 13) ---
    lance(M, 3, 1, tip=0.6)
    lance(M, 15, 6)
    lance(M, 27, 13)

    # --- guide rails (1 px), the seam between rail pairs shows the plinth ---
    rail(M, 1, 2, 13.6, 44.0, 76)
    rail(M, 11, 12, 15.0, 31.0, 73)
    rail(M, 13, 14, 15.6, 37.0, 74)
    rail(M, 23, 24, 19.6, 36.0, 73)
    rail(M, 25, 26, 20.6, 43.0, 74)
    rail(M, 35, 36, 26.6, 43.4, 73)
    # Pylon webs under the seams (cols 12 and 24): a rail pair reads as one pylon.
    M.box(11.8, 13.2, 16.5, 36.0, Z_PLINTH - 0.1, 4.2, 65, ch=0.0, chz=0.0)
    M.box(23.9, 25.1, 20.6, 55.45, Z_PLINTH - 0.1, 4.2, 65, ch=0.0, chz=0.0)

    # --- bulkheads behind each lance (rows 31, 36, 43) ---
    bulkhead(M, 1.0, 12.0, 30.35, 32.0, 6.5)
    bulkhead(M, 13.0, 24.0, 35.35, 37.0, 18.5, pal_side=74)
    bulkhead(M, 25.0, 36.0, 42.35, 44.0, 30.5)

    # --- breech block A (cols 1-11): a step behind the bulkhead, plates, groove, sliding cover,
    # ridge; the cable roller; rear plates ---
    # (The sprite darkens every column of rows 32-35: a lower step just behind the bulkhead.)
    plate(M, 1.0, 4.0, 32.0, 35.4, 5.4, 71, cw=0.8, edge_pal=75)
    plate(M, 1.0, 4.0, 35.0, 43.4, PLATE_Z, 73, cw=1.0, edge_pal=76)  # west plate, lit rail edge
    M.box(4.0, 5.0, 32.0, 43.4, Z_PLINTH, 4.6, 65, ch=0.0, chz=0.0)  # groove (dark)
    plate(M, 5.0, 8.0, 32.0, 43.4, 5.6, 69, cw=0.35, ce=0.35)  # sliding cover over the channel
    for v in (34.0, 37.5, 41.0):  # cover ribs
        M.box(5.3, 7.7, v, v + 0.5, 5.4, 5.85, 67, ch=0.12)
    plate(M, 8.0, 12.0, 32.0, 35.4, 5.4, 71, cw=0.8, edge_pal=73)
    plate(M, 8.0, 12.0, 35.0, 41.0, PLATE_Z, 73, cw=1.0, edge_pal=75)  # east plate, lit ridge edge
    # Roller (rows 44-51): a cable drum across the module with end flanges and a band.
    # (Its axis is high enough that the flanges clear the ground: nothing goes below z 0.)
    M.cyl_u(1.6, 10.0, 47.6, ROLL_Z, 3.85, 67, sides=24, ch=0.3)
    M.cyl_u(1.0, 1.7, 47.6, ROLL_Z, 4.0, 69, sides=24, ch=0.15)
    M.cyl_u(5.25, 5.75, 47.6, ROLL_Z, 3.95, 66, sides=24)
    M.cyl_u(9.5, 16.4, 47.6, ROLL_Z, 1.6, 67, sides=12)  # axle into block B's recess
    M.box(10.0, 12.0, 41.0, 44.6, Z_PLINTH, 6.6, 72, ch=0.3)  # bearing lugs
    M.box(10.0, 12.0, 48.9, 52.0, Z_PLINTH, 6.6, 72, ch=0.3)
    M.cyl_u(9.85, 12.15, 47.6, ROLL_Z, 2.1, 72, sides=12, ch=0.2)  # bearing housing
    plate(M, 1.0, 4.0, 51.8, 55.45, 6.0, 71, cw=0.8, cs=0.35)  # rear plates
    plate(M, 8.0, 12.0, 51.8, 55.45, 6.0, 71, cw=0.8, cs=0.35)
    M.box(5.0, 8.0, 52.0, 55.45, Z_PLINTH, 2.9, 65, ch=0.1)  # channel track (A's opens at the rear)

    # --- breech block B (cols 13-23): plates either side of the channel (cols 16-19) ---
    plate(M, 13.0, 16.0, 37.0, 45.0, PLATE_Z, 69, edge_pal=74)
    plate(M, 13.0, 16.0, 49.0, 55.45, PLATE_Z, 69, edge_pal=71, cs=0.35)
    M.box(13.0, 16.0, 45.0, 49.0, Z_PLINTH, 3.8, 67, ch=0.0, chz=0.0)  # axle recess
    plate(M, 20.0, 24.0, 37.0, 55.45, PLATE_Z, 69, edge_pal=71, cs=0.35)
    M.box(16.9, 19.9, 38.0, 55.45, Z_PLINTH, 2.9, 65, ch=0.1)  # channel track

    # --- breech block C (cols 25-35): channel cols 28-32 ---
    plate(M, 25.0, 28.0, 44.0, 55.45, PLATE_Z, 67, edge_pal=71, cs=0.35)
    plate(M, 32.9, 36.0, 44.0, 55.45, PLATE_Z, 67, edge_pal=69, cs=0.35)
    M.box(28.9, 32.6, 44.2, 55.45, Z_PLINTH, 2.9, 65, ch=0.1)

    # --- machined detail on the plates: seams, bolts, channel end stops ---
    for u0, u1, v in ((13.0, 16.0, 41.0), (20.0, 24.0, 42.0), (20.0, 24.0, 49.0), (25.0, 28.0, 49.5), (32.9, 36.0, 49.5), (1.0, 4.0, 38.0), (8.0, 12.0, 36.5)):
        M.box(u0 + 0.9, u1 - 0.15, v - 0.12, v + 0.12, PLATE_Z - 0.3, PLATE_Z + 0.02, 67, ch=0.0, chz=0.0)
    for u, v in ((2.9, 33.0), (2.9, 42.6), (10.3, 33.0), (10.3, 40.2), (14.9, 38.0), (14.9, 44.2), (14.9, 50.0), (14.9, 54.4),
                 (21.5, 38.0), (22.9, 45.5), (21.5, 54.4), (26.9, 45.0), (26.9, 54.4), (34.9, 45.0), (34.9, 54.4),
                 (2.9, 52.8), (10.5, 52.8), (2.9, 54.5), (10.5, 54.5)):
        z = 6.0 if v > 51.5 and u < 12.5 else PLATE_Z
        M.bolt(u, v, z, 67, r=0.3, h=0.16)
    # Channel end stops at the rear wall: a bar across each open channel, low on its floor.
    for u0, u1 in ((5.0, 8.0), (16.9, 19.9), (28.9, 32.6)):
        M.box(u0 - 0.05, u1 + 0.05, 54.6, 55.45, Z_PLINTH, 3.5, 70, ch=0.15)
    # West wall: the outer rail's flank carries a bolt row and the plinth two panel seams.
    for v in (18.0, 23.0, 28.0, 33.0, 38.0, 42.5):
        for z in (3.6, 6.0):
            M.loft([[(1.0 - dz, v + 0.33 * math.cos(math.pi / 3 * i), z + 0.33 * math.sin(math.pi / 3 * i)) for i in range(6)]
                    for dz in (-0.05, 0.18)], 66)
    for v in (24.0, 40.0):
        M.box(0.9, 1.05, v - 0.12, v + 0.12, 0.3, Z_PLINTH - 0.2, 66, ch=0.0, chz=0.0)
    M.box(0.9, 1.05, 13.5, 55.3, 0.9, 1.1, 66, ch=0.0, chz=0.0)  # a weld seam along the plinth
    # Rear wall: a ledge band along the plinth's south face (machined step the camera sees).
    M.box(1.0, 37.4, 55.2, 55.45, 0.0, 1.0, 66, ch=0.0, chz=0.0)

    bastion(M)


# --- finishing -----------------------------------------------------------------------------------

def to_object(M, mats, coll, name):
    bm = M.bm
    m = Matrix(((PX, 0, 0, -24 * PX), (0, -PX, 0, 28 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    return obj


def cull_hidden(obj, grid=4, ndirs=40):
    """Delete faces no ray from outside can reach (plinth under the plates, buried ends), as
    usp_talon.cull_hidden does. Faces facing straight down (the underside) are kept: it stays closed."""
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
    dead = []
    for f in bm.faces:
        n = f.normal
        if n.z < -0.9:
            continue
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    a = vs[0].lerp(vs[1], (i + 0.5) / grid)
                    b = vs[3].lerp(vs[2], (i + 0.5) / grid)
                    pts.append(a.lerp(b, (j + 0.5) / grid))
        else:
            for vco in vs:
                for t in (0.35, 0.7, 0.92):
                    pts.append(c.lerp(vco, t))
        cand = [d for d in dirs if d.dot(n) > 0.05 and d.z > -0.2]
        seen = False
        for p in pts:
            o = p + n * 2e-4
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()
    return len(dead)


TINT = (1.0, 0.97, 0.95)


def bake_maps(obj, tag, size=1024, samples=64):
    """UV the model and bake two maps with Cycles (the ships' bake, usp_talon.bake_maps, copied
    here with this model's materials): a grey colour multiplier (ambient occlusion at two scales
    plus a light lift on bevelled edges) and a metallic-roughness map. Base Color = map x palette
    colour, so the palette (fades, hit flash) still sets the colour. Packed into the .glb."""
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
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
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

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, val in enumerate((a, b)):
                if val is None:
                    continue
                if isinstance(val, (int, float)):
                    n.inputs[k].default_value = val
                else:
                    nt.links.new(val, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 16
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 16
        ao_l.inputs["Distance"].default_value = 0.16
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.005
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        comb = node("ShaderNodeCombineColor")
        if mode == "colour":
            val = math_("MINIMUM", math_("ADD", math_("ADD", 0.5, math_("MULTIPLY", occl, 0.6)),
                                         math_("MULTIPLY", edge, 0.18)), 1.0)
            for k in range(3):
                nt.links.new(math_("MULTIPLY", val, TINT[k]), comb.inputs[k])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
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
        img.pack()

    for m in mats:
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


def shell_source(obj, collection, voxel=0.012):
    """Stage 1 of the outline shells (common.outline_shell, D51, reworked): a voxel remesh of the
    WHOLE closed model, taken before cull_hidden opens it and before it is cut into pieces.
    common.outline_shell remeshes each cut piece and keeps only its largest island; this model's
    culled parts are open surfaces, which the remesh turns into thin disconnected sheets, so the
    northern half of each lance was dropped and had no outline. Every outer island is kept here;
    inner shells (cavity walls, facing inward: negative volume) and zero-volume sheets are dropped."""
    me = obj.data.copy()
    me.materials.clear()
    src = bpy.data.objects.new(f"{obj.name}_shellsrc", me)
    collection.objects.link(src)
    src.matrix_world = obj.matrix_world.copy()
    rm = src.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    _apply(src)
    bm = bmesh.new()
    bm.from_mesh(src.data)
    bm.faces.ensure_lookup_table()
    seen, dead = set(), []
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        stack, isl = [f0], []
        seen.add(f0.index)
        while stack:
            f = stack.pop()
            isl.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        vol = sum(f.verts[0].co.dot(f.verts[i].co.cross(f.verts[i + 1].co))
                  for f in isl for i in range(1, len(f.verts) - 1)) / 6
        if vol <= 1e-5:
            dead += isl
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(src.data)
    bm.free()
    return src


def finish_shell(shell, name, faces=1500, smooth=6):
    """Stage 2, per piece (the cut faces are filled by split_assembly): smooth (relaxing the voxel
    steps and pulling it a hair inside convex edges), thin, keep it above the ground, tag it."""
    shell.name = shell.data.name = f"{name}_outline"
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    _apply(shell)
    for v in shell.data.vertices:
        if v.co.z < 0.0:
            v.co.z = 0.0
    shell.data.validate()
    shell.data.materials.clear()
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def _apply(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def merged_sprite():
    data = common.load_sprite(WT, PIECES[0])
    for name in PIECES[1:]:
        data["colors"].update(common.load_sprite(WT, name)["colors"])
    return data


def layout(sprite):
    lay = sprite["assemblyLayout"]
    return [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in lay if e["model"] in PIECES]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    final = out is None
    pieces_dir = Path(argv[argv.index("--pieces-dir") + 1]) if "--pieces-dir" in argv else None
    bake = "--no-bake" not in argv
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    sprite = merged_sprite()
    mats = make_materials(sprite)
    M = Mesh()
    build(M)
    obj = to_object(M, mats, coll, NAME)
    src = shell_source(obj, coll)
    shells = common.split_assembly(src, layout(sprite))
    bpy.data.objects.remove(src, do_unlink=True)
    bpy.context.view_layer.update()
    for name, sh in shells.items():  # free the piece names for the pieces themselves
        sh.name = sh.data.name = f"{name}_outline"
    n = cull_hidden(obj)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: culled {n} hidden faces; {len(obj.data.polygons)} faces, {tris} triangles")
    if bake:
        bake_maps(obj, "nshfA")
    split = common.split_assembly(obj, layout(sprite))
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()
    fmt = "WEBP" if bake else "AUTO"
    placed = []
    for name, cx, cy in layout(sprite):
        p = split[name]
        p.data.shade_smooth()
        p.data.set_sharp_from_angle(angle=math.radians(35))
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        shell = finish_shell(shells[name], name)
        ptris = sum(len(f.vertices) - 2 for f in p.data.polygons)
        print(f"{name}: {ptris} triangles, shell {len(shell.data.polygons)} faces")
        if final:
            data = common.load_sprite(WT, name)
            common.export_sprite_model(WT, [p, shell], f"enemies/{name}", data["sprites"], image_format=fmt)
        if pieces_dir is not None:
            common.export_glb([p, shell], pieces_dir / f"{name}.glb", image_format=fmt)
        p.location = shell.location = (cx * PX, -cy * PX, 0.0)
        placed += [p, shell]
    if out is not None:
        common.export_glb(placed, out, image_format=fmt)
        print(f"exported {out}")
    if "--preview" in argv:
        prev = Path(argv[argv.index("--preview") + 1])
        data = common.load_sprite(WT, PIECES[0])
        img = WT / "reference" / "models" / PIECES[0] / data["frames"][0]["image"]
        common.render_preview([o for o in placed if not o.get("tyrian_outline")], str(prev), img,
                              size=(48, 56))


if __name__ == "__main__":
    main()
