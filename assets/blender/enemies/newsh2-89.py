"""Purple armoured pod (newsh2.shp frame 89, 24 x 28 px, palette 5): a hard-surface machine that is
its sprite in 3D (D50-D53).

Seen in episode 1 (levels 1.25, 1.28, 1.3, 1.36; enemy type 30) and episode 3. The sprite is
authoritative for the top-down outline (a deep box with 45-degree chamfered corners, a window
housing proud of the nose edge at row 0, a tapering engine bay), the window (glass cols 9-16 rows
1-4 in a dark housing cols 8-17) and the colours: each part takes the palette index of the sprite's
pixels there (the region's median with the darkest shading and brightest sheen left out). The
concept (assets/blender/features/concepts/newsh2-89.jpg) only guides the sides, front and rear.

Built from closed convex blocks (chamfered hulls) and revolved nacelles, in sprite px (c = column
edge, r = row edge, aft +r, z up from the belly), moved to Blender at the end:
X = (c - 12) / 12, Y = (14 - r) / 12, Z = (z + Z0) / 12. The sprite's centre line is c = 12.5.

- Upper armour box (rows 1-14): a dark core with an overhanging deck rim, the deck covered by
  plates 0.35 proud with real gaps (panel lines); the cage of the sprite on top: the satin bar
  across row 5 between the deck edge plates (cols 4-18, inside the outline), the rectangular frame bars round
  the two side armour plates (bolted), two tall spine bars with a dark channel between them, a vent
  in the right deck edge (sprite col 21) and a small intake on the left (cols 3-4).
- Waist (rows 14-16.6): a lower belt of plates, its rear lip lit (row 16).
- Engine bay (rows 16.6-26): cowls round two ribbed round nacelles with deep flared nozzles (dark
  interior, turbine cone), a two-plate keel between them with a knee at row 20, the dark bay floor.
- Underside: just the closed chamfered belly (undersides are hardly ever seen: no detail).

Texture: no concept projection (its maps.json says "bake": "model", as the player ships, D50): an
ambient occlusion / roughness bake only (usp_talon.bake_maps), Base Color = map x palette colour, so
pal_<index>, fades and the hit flash still apply. An outline shell (common.outline_shell, D51) is
made from the closed parts; the nozzles are named in the extras `tyrian_engines`.
One frame, one model.

Run: blender --background --factory-startup --python assets/blender/enemies/newsh2-89.py
     [-- --preview out.png] [--no-bake] [--out x.glb]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy

BLENDER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BLENDER_DIR))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (fillet, offset_loop, cull_hidden, join, bake_maps)

NAME = "newsh2-89"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
Z0 = -1.2  # belly at z = -0.1 units, as the current model
AX = 12.5  # the sprite's centre line (column edge)

# --- materials ---------------------------------------------------------------------------------
# (slot name, palette index, metallic, roughness). Indices are the sprite's per-region medians
# (outline 1 dropped, darkest and brightest 15% trimmed as lighting/sheen); metal is satin.
MATS = [
    ("core", 82, 0.25, 0.5),      # dark substructure, seams
    ("deck", 84, 0.3, 0.42),      # deck plates and rim
    ("wall", 83, 0.3, 0.45),      # flank armour, side walls
    ("belly", 82, 0.25, 0.55),    # belly (unseen)
    ("glass", 128, 0.0, 0.05),
    ("facet", 134, 0.0, 0.05),
    ("housing", 84, 0.3, 0.4),
    ("topbar", 91, 0.35, 0.32),
    ("frame", 90, 0.35, 0.34),
    ("plate", 89, 0.3, 0.38),
    ("bolt", 88, 0.35, 0.3),
    ("spine", 89, 0.35, 0.3),
    ("spine_side", 88, 0.35, 0.34),
    ("groove", 85, 0.25, 0.5),
    ("vent", 80, 0.1, 0.8),
    ("belt", 82, 0.3, 0.45),
    ("lip", 86, 0.35, 0.34),
    ("cowl", 82, 0.3, 0.45),
    ("nacelle", 81, 0.35, 0.38),
    ("rib", 81, 0.35, 0.4),
    ("shroud", 88, 0.4, 0.3),
    ("nozzle", 80, 0.1, 0.85),
    ("cone", 84, 0.4, 0.35),
    ("keel", 82, 0.3, 0.4),
    ("bay", 80, 0.15, 0.7),
    ("panel", 85, 0.3, 0.42),     # inner deck panel under the cage
    ("deck_lt", 86, 0.3, 0.42),   # deck plates either side of the window (sprite rows 1-4)
    ("deck_dk", 83, 0.3, 0.42),   # deck edge strips (sprite cols 2-4, 19-22)
    ("wall_core", 81, 0.25, 0.5),  # the core's walls between the flank armour
]
M = {name: i for i, (name, *_rest) in enumerate(MATS)}
UNBAKED = {M["glass"], M["facet"]}


def materials(sprite):
    return [common.palette_material(sprite, idx, f"{NAME}_{name}", metallic=met, roughness=rough)
            for name, idx, met, rough in MATS]


# --- 2D helpers (c, r) ---------------------------------------------------------------------------

def mirror_c(c):
    return 2 * AX - c


def clip(poly, axis, value, keep_less):
    """Sutherland-Hodgman: keep the part of a convex polygon with p[axis] <= value (or >=)."""
    def inside(p):
        return p[axis] <= value + 1e-9 if keep_less else p[axis] >= value - 1e-9
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ia, ib = inside(a), inside(b)
        if ia:
            out.append(a)
        if ia != ib:
            t = (value - a[axis]) / (b[axis] - a[axis])
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def clip_rect(poly, c0, r0, c1, r1):
    for axis, v, less in ((0, c0, False), (0, c1, True), (1, r0, False), (1, r1, True)):
        poly = clip(poly, axis, v, less)
    return poly


def inset(poly, d):
    """Inset a convex polygon by d (miter offsets toward its centroid)."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    vn, _ = T.offset_loop(poly, (cx, cy))
    return [(p[0] - n[0] * d, p[1] - n[1] * d) for p, n in zip(poly, vn)]


# The plan: the sprite's mask (dark ring included) as a convex octagon whose 45-degree corners run
# through the middles of the sprite's pixel stairs (rows 1-4 at the nose, 20-25 at the tail),
# lightly filleted so they read round where the sprite's stairs are smooth.
_CORNERS = [(4.5, 1.0), (20.5, 1.0), (24.0, 4.5), (24.0, 19.5), (17.5, 26.0), (7.5, 26.0), (1.0, 19.5), (1.0, 4.5)]
PLAN = T.fillet(_CORNERS, 0.9, 3)
UPPER = clip(PLAN, 1, 14.2, True)


# --- solids --------------------------------------------------------------------------------------

class Model:
    def __init__(self):
        self.parts = []  # (bmesh, smooth_angle)

    def hull(self, pts, mat, by_normal=None, smooth=30):
        """A closed convex block through pts [(c, r, z)]; by_normal(n) -> material overrides."""
        bm = bmesh.new()
        verts = [bm.verts.new(p) for p in pts]
        res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(bm, geom=junk, context="VERTS")
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts[:], edges=bm.edges[:])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:
            f.material_index = mat
            if by_normal:
                m = by_normal(f.normal)
                if m is not None:
                    f.material_index = m
        self.parts.append((bm, smooth))
        return bm

    def prism(self, poly, z0, z1, mat, ch=0.12, chb=0.0, by_normal=None):
        """A plate: polygon poly [(c, r)] from z0 to z1 with a 45-degree chamfer ch on its top edges
        (and chb on its bottom edges)."""
        pts = [(c, r, z0 + chb) for c, r in poly] + [(c, r, z1 - ch) for c, r in poly]
        pts += [(c, r, z1) for c, r in inset(poly, ch)] if ch else []
        pts += [(c, r, z0) for c, r in inset(poly, chb)] if chb else []
        return self.hull(pts, mat, by_normal)

    def box(self, c0, r0, c1, r1, z0, z1, mat, ch=0.12, by_normal=None):
        return self.prism([(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, mat, ch, by_normal=by_normal)

    def revolve(self, cx, cz, profile, n=20, smooth=60):
        """A closed solid of revolution about the axis along r at (cx, cz). profile: [(r, radius,
        material of the band from this point to the next)], radius 0 = on the axis."""
        bm = bmesh.new()
        rings = []
        for r, rad, _ in profile:
            if rad < 1e-6:
                rings.append([bm.verts.new((cx, r, cz))])
            else:
                rings.append([bm.verts.new((cx + rad * math.sin(2 * math.pi * (i + 0.5) / n), r,
                                            cz + rad * math.cos(2 * math.pi * (i + 0.5) / n))) for i in range(n)])
        for (_, _, mat), r0, r1 in zip(profile, rings, rings[1:]):
            for i in range(n):
                j = (i + 1) % n
                if len(r0) == 1:
                    vs = (r0[0], r1[i], r1[j])
                elif len(r1) == 1:
                    vs = (r0[i], r1[0], r0[j])
                else:
                    vs = (r0[i], r1[i], r1[j], r0[j])
                f = bm.faces.new(vs)
                f.material_index = mat
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self.parts.append((bm, smooth))
        return bm

    def strap(self, path, r0, r1, thick, mat, ch=0.14):
        """A bar of rectangular section (r0..r1 along the pod, `thick` outward) lying on a surface
        path [(c, z)] in the cross-section plane, mitred at the bends (one closed hull per run)."""
        cen = (AX, 3.0)
        vn, _ = T.offset_loop_open(path, cen) if hasattr(T, "offset_loop_open") else _open_normals(path, cen)
        for i in range(len(path) - 1):
            pts = []
            for k in (i, i + 1):
                (c, z), (nc, nz) = path[k], vn[k]
                oc, oz = c + nc * thick, z + nz * thick
                ic, iz = c + nc * (thick - ch), z + nz * (thick - ch)
                pts += [(c, r0, z), (c, r1, z), (ic, r0, iz), (ic, r1, iz), (oc, r0 + ch, oz), (oc, r1 - ch, oz)]
            self.hull(pts, mat)


def _open_normals(path, cen):
    """Outward miter normals of an open polyline in (c, z) (away from cen)."""
    segs = []
    for (a, b), (c, d) in zip(path, path[1:]):
        dx, dz = c - a, d - b
        ln = math.hypot(dx, dz)
        nx, nz = dz / ln, -dx / ln
        mx, mz = (a + c) / 2 - cen[0], (b + d) / 2 - cen[1]
        if nx * mx + nz * mz < 0:
            nx, nz = -nx, -nz
        segs.append((nx, nz))
    out = []
    for k in range(len(path)):
        if k == 0:
            out.append(segs[0])
        elif k == len(path) - 1:
            out.append(segs[-1])
        else:
            (ax, az), (bx, bz) = segs[k - 1], segs[k]
            sx, sz = ax + bx, az + bz
            ln = math.hypot(sx, sz)
            ux, uz = sx / ln, sz / ln
            cs = max(0.5, ux * bx + uz * bz)
            out.append((ux / cs, uz / cs))
    return out, segs


def top_or(mat_top, mat_side, lim=0.7):
    return lambda n: mat_top if n.z > lim else mat_side


# --- the pod -------------------------------------------------------------------------------------

DECK = 8.0      # deck slab top
PLATE_T = 8.3   # deck plate tops
WAIST = 7.4
BAY = 3.2


def build_hull(m):
    # Belly: the full plan, 45-degree chamfer underneath (closed, plain: it is never seen).
    m.prism(PLAN, 0.0, BAY, M["belly"], ch=0.0, chb=1.4)
    # Upper box: a dark core inset 0.3 and the deck slab with an overhanging rim on top of it.
    m.prism(inset(UPPER, 0.3), 1.0, 6.9, M["wall_core"], ch=0.0)
    m.hull([(c, r, 6.55) for c, r in inset(UPPER, 0.3)] + [(c, r, 6.85) for c, r in UPPER]
           + [(c, r, 7.2) for c, r in UPPER] + [(c, r, DECK) for c, r in inset(UPPER, 0.8)],
           M["deck"], by_normal=lambda n: M["core"] if n.z > 0.99 else None)
    # Deck plates with real gaps (panel lines), clipped to the flat deck.
    deck_top = inset(UPPER, 0.95)
    rects = [(0, 0, 7.75, 4.85, "deck_lt"), (17.25, 0, 30, 4.85, "deck_lt"),   # either side of the window housing
             (0, 5.15, 4.75, 9.45, "deck_dk"), (0, 9.75, 4.75, 15, "deck_dk"),  # left deck edge strip, two plates
             (20.25, 5.15, 30, 9.45, "deck_dk"), (20.25, 9.75, 30, 15, "deck_dk")]  # right
    for c0, r0, c1, r1, mat in rects:
        poly = clip_rect(deck_top, c0, r0, c1, r1)
        if len(poly) >= 3:
            m.prism(poly, DECK - 0.3, PLATE_T, M[mat], ch=0.12)
    # The inner deck panel under the cage (the sprite's dark gaps between plates and spines).
    m.box(5.05, 5.15, 19.95, 14.05, DECK - 0.3, PLATE_T - 0.05, M["panel"], ch=0.1)
    # Waist: the box steps down to a belt (rows 14-16.6), its sides inset like the core, a rim on top.
    m.hull([(c, r, z) for c, r in ((1.3, 14.0), (23.7, 14.0), (23.7, 16.6), (1.3, 16.6)) for z in (1.0, 6.6)]
           + [(c, r, z) for c, r in ((1.0, 14.0), (24.0, 14.0), (24.0, 16.6), (1.0, 16.6)) for z in (6.9, 7.0)]
           + [(c, r, WAIST) for c, r in ((1.4, 14.0), (23.6, 14.0), (23.6, 16.3), (1.4, 16.3))], M["belt"])
    # Belt plates either side of the spines, and the lit lip along the belt's rear edge (row 16).
    for c0, c1 in ((1.7, 9.7), (15.3, 23.3)):
        m.box(c0, 14.25, c1, 15.75, WAIST - 0.3, WAIST + 0.28, M["belt"], ch=0.1)
        m.hull([(c, r, z) for c in (c0 - 0.2, c1 + 0.2) for r, z in
                ((15.8, WAIST - 0.4), (15.8, WAIST + 0.42), (16.45, WAIST + 0.42), (16.8, WAIST + 0.1), (16.8, 6.4))], M["lip"])
    # Flank armour on the core's walls (rows 7-13) and on the front either side of the housing.
    for c in (1.0, mirror_c(1.0)):
        s = 1 if c < AX else -1
        for r0, r1 in ((6.2, 9.85), (10.15, 13.7), (14.0, 16.4)):
            m.hull([(c + s * dc, r, z) for r in (r0, r1) for dc, z in
                    ((0.45, 2.6), (0.45, 6.35), (0.25, 6.2), (0.25, 2.75))]
                   + [(c + s * 0.05, rr, zz) for rr in (r0 + 0.2, r1 - 0.2) for zz in (2.95, 6.0)], M["wall"])
            for rr in (r0 + 0.55, r1 - 0.55):
                for zz in (3.3, 5.6):
                    m.hull([(c + s * dc, rr + dr, zz + dz) for dc in (0.05, 0.15) for dr in (-0.18, 0.18) for dz in (-0.18, 0.18)]
                           + [(c - s * 0.03, rr + dr, zz + dz) for dr in (-0.1, 0.1) for dz in (-0.1, 0.1)], M["bolt"], smooth=50)
    for c0, c1 in ((4.9, 7.8), (mirror_c(7.8), mirror_c(4.9))):
        m.hull([(c, r, z) for c in (c0, c1) for r, z in ((1.4, 2.0), (1.4, 6.35), (1.05, 6.2), (1.05, 2.15))], M["wall"])
    # Bay floor: the dark floor between the cowls, nacelles and keel.
    m.prism(clip_rect(inset(PLAN, 0.5), 2.5, 16.4, 22.5, 26), BAY - 0.4, BAY + 0.25, M["bay"], ch=0.1)


def build_window(m):
    # Housing: a dark armoured block standing proud of the nose; its front lip is the sprite's row 0.
    m.hull([(c, r, z) for c in (8.0, 17.0) for r, z in
            ((0.6, 3.0), (0.35, 3.4), (0.35, 8.3), (0.55, 8.95), (4.55, 8.95), (4.9, 8.6), (4.9, 3.0))]
           + [(c, r, 8.95) for c in (8.3, 16.7) for r in (0.5, 4.7)], M["housing"],
           by_normal=lambda n: M["core"] if n.y < -0.95 else None)
    # Its armoured front: a brow under the glass and a grille of three slats across a dark recess.
    m.hull([(c, r, z) for c in (8.0, 17.0) for r, z in ((0.05, 7.6), (0.05, 8.3), (0.4, 8.6), (0.4, 7.4))]
           + [(c, 0.2, 8.5) for c in (8.25, 16.75)], M["housing"])
    for z in (4.0, 5.2, 6.4):
        m.hull([(c, r, zz) for c in (8.7, 16.3) for r, zz in ((0.1, z + 0.1), (0.1, z + 0.45), (0.45, z + 0.55), (0.45, z))], M["housing"])
    for c in (8.0, 16.3):
        m.box(c, 0.05, c + 0.7, 0.45, 3.4, 7.7, M["housing"], ch=0.08)
    # Chamfered chin under the housing: the armour wedge raked back to the belly (front view).
    m.hull([(c, r, z) for c in (8.3, 16.7) for r, z in ((0.55, 3.4), (0.75, 2.2), (1.6, 1.0), (2.4, 1.0), (2.4, 3.4))]
           + [(c, r, z) for c in (8.8, 16.2) for r, z in ((0.45, 3.2), (0.65, 2.3))], M["housing"])
    # Cheek plates either side of it, angled, meeting the window housing's sides.
    for c0, c1 in ((5.6, 8.3), (mirror_c(8.3), mirror_c(5.6))):
        m.hull([(c, r, z) for c in (c0, c1) for r, z in ((1.08, 6.3), (1.05, 2.6), (1.6, 1.5), (1.75, 6.3))], M["wall"])
    # Faceted glass block, cols 9-16 rows 0.8-3.9: raked front facet, flat top, bevelled rear.
    def glass_mat(n):
        if n.y > 0.3 or n.x < -0.3:   # rear and left facets: the sprite's bright 134 rows
            return M["facet"]
        return None
    pts = []
    for c, top in ((9.0, False), (16.0, False), (9.35, True), (15.65, True)):
        prof = ((0.8, 8.4), (0.8, 8.7), (1.5, 9.35), (3.5, 9.35), (3.9, 8.95), (3.9, 8.4)) if top else \
               ((0.8, 8.4), (0.8, 8.7), (1.3, 9.05), (3.7, 9.05), (3.9, 8.85), (3.9, 8.4))
        pts += [(c, r, z) for r, z in (prof if top else prof)]
    m.hull(pts, M["glass"], by_normal=glass_mat, smooth=20)


def build_cage(m):
    # Top bar across row 5, on the deck only: the sprite's bar spans cols 4-18, from just outside
    # the left frame bar to the right one (cols 1-3 and 19-22 of that row are deck, not bar).
    bz0, bz1 = DECK - 0.1, PLATE_T + 0.42
    m.hull([(c, r, z) for c in (4.25, 19.0) for r in (5.0, 6.0) for z in (bz0, bz1 - 0.16)]
           + [(c, r, bz1) for c in (4.45, 18.8) for r in (5.16, 5.84)], M["topbar"])
    # Bracket feet where the bar meets the deck edge plates, in deck colour, inside the outline.
    for c0, c1 in ((3.0, 4.35), (18.9, 20.2)):
        m.box(c0, 5.05, c1, 5.95, DECK - 0.1, PLATE_T + 0.16, M["deck"], ch=0.1)
    # Frame bars round the side plates: verticals at cols 5 and 18, the bar along row 13 (split by
    # the spine channel).
    fz0, fz1 = DECK - 0.1, 8.85
    m.box(5.0, 5.9, 6.0, 13.95, fz0, fz1, M["frame"], ch=0.15)
    m.box(18.0, 5.9, 19.0, 13.95, fz0, fz1, M["frame"], ch=0.15)
    m.box(5.9, 13.0, 12.0, 13.95, fz0, fz1 - 0.05, M["frame"], ch=0.15)
    m.box(13.0, 13.0, 18.1, 13.95, fz0, fz1 - 0.05, M["frame"], ch=0.15)
    # Armour plates inside the frames, bevelled, four bolts each.
    for c0, c1 in ((6.15, 9.3), (15.75, 17.85)):
        m.box(c0, 6.15, c1, 12.85, DECK - 0.1, 8.62, M["plate"], ch=0.28)
        for c in (c0 + 0.55, c1 - 0.55):
            for r in (6.7, 12.3):
                m.hull([(c + dc, r + dr, z) for dc in (-0.2, 0.2) for dr in (-0.2, 0.2) for z in (8.4, 8.66)]
                       + [(c + dc, r + dr, 8.76) for dc in (-0.12, 0.12) for dr in (-0.12, 0.12)], M["bolt"], smooth=50)
    # Spines: two tall bars (cols 10-12, 13-15), their tails raked down onto the belt.
    for c0, c1 in ((10.0, 12.0), (13.0, 15.0)):
        prof = ((4.75, DECK - 0.2), (4.75, 9.1), (5.35, 9.55), (13.9, 9.55), (15.85, WAIST + 0.35), (15.85, WAIST - 0.4))
        pts = []
        for r, z in prof:
            top = z > 9.0
            pts += [(c0 + (0.25 if top else 0), r, z), (c1 - (0.25 if top else 0), r, z)]
            if top:
                pts += [(c0, r, z - 0.25), (c1, r, z - 0.25)]
        m.hull(pts, M["spine"], by_normal=top_or(M["spine"], M["spine_side"], 0.6))
    # The dark channel between them.
    m.box(11.95, 4.9, 13.05, 15.6, DECK - 0.2, 8.35, M["groove"], ch=0.05)


def build_deck_details(m):
    # Vent in the right deck edge (sprite col 21, rows 9-12): a framed dark slot with three slats.
    def framed(c0, r0, c1, r1, w, floor_mat, slats=()):
        top = PLATE_T + 0.34
        m.box(c0, r0, c1, r0 + w, PLATE_T - 0.1, top, M["deck"], ch=0.08)
        m.box(c0, r1 - w, c1, r1, PLATE_T - 0.1, top, M["deck"], ch=0.08)
        m.box(c0, r0, c0 + w, r1, PLATE_T - 0.1, top, M["deck"], ch=0.08)
        m.box(c1 - w, r0, c1, r1, PLATE_T - 0.1, top, M["deck"], ch=0.08)
        m.box(c0 + w - 0.05, r0 + w - 0.05, c1 - w + 0.05, r1 - w + 0.05, PLATE_T - 0.3, PLATE_T + 0.06, floor_mat, ch=0.0)
        for r in slats:
            m.box(c0 + w - 0.05, r - 0.1, c1 - w + 0.05, r + 0.1, PLATE_T - 0.2, PLATE_T + 0.2, M["core"], ch=0.04)
    framed(20.45, 8.3, 22.45, 13.1, 0.35, M["vent"], slats=(9.6, 10.7, 11.8))
    framed(2.45, 6.8, 4.35, 8.9, 0.32, M["vent"], slats=(7.85,))


def build_bay(m):
    for side in (1, -1):
        f = (lambda c: c) if side == 1 else mirror_c
        # Cowl: the bay's outer shell, wrapping round the outside of the nacelle, top raked aft.
        pts = [(1.0, 16.4, 2.8), (1.0, 16.4, 6.3), (1.5, 16.4, 6.8), (4.4, 16.4, 6.8), (5.2, 16.4, 2.8),
               (1.0, 19.4, 2.8), (1.0, 19.4, 5.6), (1.5, 19.4, 6.1), (4.3, 19.4, 6.1), (5.1, 19.4, 2.8),
               (3.9, 22.4, 2.8), (3.9, 22.4, 4.3), (4.25, 22.4, 4.6), (4.9, 22.4, 4.6), (5.25, 22.4, 2.8)]
        m.hull([(f(c), r, z) for c, r, z in pts], M["cowl"])
        # Nacelle: buried in the waist, ribbed, then a flared satin shroud and a deep nozzle.
        N, R, S, D, C = M["nacelle"], M["rib"], M["shroud"], M["nozzle"], M["cone"]
        prof = [(16.2, 0.0, N), (16.2, 1.95, N), (17.3, 2.0, R), (17.3, 2.2, R), (17.75, 2.2, R), (17.75, 2.0, N),
                (18.2, 2.0, R), (18.2, 2.2, R), (18.65, 2.2, R), (18.65, 2.0, N), (19.05, 2.05, S),
                (19.25, 2.25, S), (20.45, 2.3, R), (20.55, 2.16, R), (20.7, 2.16, R), (20.8, 2.32, S), (22.0, 2.38, S), (22.45, 2.22, S), (22.45, 1.78, D), (22.15, 1.62, D),
                (20.5, 1.45, D), (20.5, 0.75, C), (21.3, 0.0, C)]
        m.revolve(f(7.5), 4.75, prof)
    # Keel: two plates between the nacelles (cols 10-12 and 13-15), a knee at row 20, raked to the tail.
    for c0, c1 in ((10.05, 11.9), (13.1, 14.95)):
        pts = []
        for r, zt in ((16.3, 6.75), (20.0, 6.45), (25.2, 3.9), (25.6, 3.55)):
            pts += [(c0, r, 2.9), (c1, r, 2.9), (c0, r, zt - 0.3), (c1, r, zt - 0.3), (c0 + 0.3, r, zt), (c1 - 0.3, r, zt)]
        m.hull(pts, M["keel"])


# --- finishing -----------------------------------------------------------------------------------

def finish(m, mats, coll):
    from mathutils import Matrix
    mat4 = Matrix(((PX, 0, 0, -12 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, Z0 * PX), (0, 0, 0, 1)))
    objs = []
    for k, (bm, smooth) in enumerate(m.parts):
        bmesh.ops.transform(bm, matrix=mat4, verts=bm.verts)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"{NAME}_p{k}")
        bm.to_mesh(me)
        bm.free()
        for mt in mats:
            me.materials.append(mt)
        obj = bpy.data.objects.new(f"{NAME}_p{k}", me)
        coll.objects.link(obj)
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(smooth))
        objs.append(obj)
    return objs


def build(coll, sprite):
    mats = materials(sprite)
    m = Model()
    build_hull(m)
    build_window(m)
    build_cage(m)
    build_deck_details(m)
    build_bay(m)
    objs = finish(m, mats, coll)
    obj = T.join(objs, NAME)
    return obj


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(coll, sprite)
    # The outline shell is made from the closed parts, before hidden faces are culled (remeshing
    # the culled, open blocks would wrap both sides of every open plate).
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    # Engine glows: the two nozzles (sprite cols 7.5 and 17.5, axis z 4.75, exit row 22.45), in
    # glTF axes (x, y up, z aft = toward the bottom of the sprite).
    obj["tyrian_engines"] = {"color": "#ff4a12", "at": [
        [round((c - 12) * PX, 4), round((4.75 + Z0) * PX, 4), round((22.3 - 14) * PX, 4)] for c in (7.5, mirror_c(7.5))]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        T.TEXTURED = tuple(i for i in range(len(MATS)) if i not in UNBAKED)
        T.TINT = (1.0, 1.0, 1.0)
        T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"))
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{NAME}_")
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(closed, coll, faces=1200)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
