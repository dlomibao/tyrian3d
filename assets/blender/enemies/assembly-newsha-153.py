"""Skull chest (newsha.shp, assembly of 8 pieces, 96 x 56 px layout), design A.

What it is: a hovering/skating wooden sea chest (GAUNTLET 3.2, MACES 3.25; custom52 ground2 with
ev19+20+27 cycling x -4..+4, so it slides side to side over the terrain). Seen from above (the
sprite): two planked wooden ends, two grey metal straps that wrap the whole chest (a corner cap
over the back edge and one over the front edge, a 1 px seam between cap and band), a mitred wooden
frame round a recessed panel with a dark skull inlay (eye, nose and tooth holes show the lighter
panel), and a grey carrying handle hinged in two fork brackets on the back edge, folded back and
tilted up a little. Two low metal skids underneath (a closed, plain underside).

Built once in assembly coordinates, cut into the 8 pieces with common.split_assembly; every piece
has a single frame. Outline shells come from a sealed proxy of the outer form (D51/D90/D118), cut
the same way, so the ink stays on the silhouette.

Units: c, r = assembly pixel edges of the 96 x 56 layout (tools/sprite_mask.py assembly-newsha-153
grid), h = px above the chest's lowest point. Blender X = (c - 48) / 12, Y = (28 - r) / 12,
Z = h / 12. The layout centre (48, 28) is screen (172, 53) and the Blender origin.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsha-153.py
(optional after --: --out whole.glb, --review DIR for scratch renders). Exports each piece (mesh +
outline shell) to public/models/enemies/<piece>.glb and src/render/spriteModels/<piece>.json.
lib_b132 (the old pixel-plank helper) is no longer used.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)

NAME = "assembly-newsha-153"
PIECES = ["newsha-153", "newsha-155", "newsha-157", "newsha-159",
          "newsha-191", "newsha-193", "newsha-195", "newsha-197"]
CX0, CY0 = 172, 53  # screen px of the layout centre (48, 28)
W, H = 96, 56


def P(c, r, h):
    return Vector(((c - 48.0) / 12, (28.0 - r) / 12, h / 12))


# ------------------------------------------------------------------------------------------------
# Materials: sprite region medians (darkest shading and brightest sheen left out)
# ------------------------------------------------------------------------------------------------

class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list = []
        self.slot = {}

    def __call__(self, idx, metallic, roughness, key=None):
        key = key or (idx, metallic, roughness)
        if key not in self.slot:
            m = common.palette_material(self.sprite, idx, f"nsha153A_{len(self.list)}",
                                        metallic=metallic, roughness=roughness)
            self.slot[key] = len(self.list)
            self.list.append(m)
        return self.slot[key]


def merged_sprite():
    data = common.load_sprite(ROOT, "newsha-155")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


# ------------------------------------------------------------------------------------------------
# Geometry helpers (copied/adapted here; usp_talon/common are not edited)
# ------------------------------------------------------------------------------------------------

def add_solid(bm, verts, faces, mat, smooth=False):
    vs = [bm.verts.new(v) for v in verts]
    for f in faces:
        try:
            face = bm.faces.new([vs[i] for i in f])
        except ValueError:
            continue
        face.material_index = mat
        face.smooth = smooth


def hull(bm, pts, mat, smooth=False):
    """Convex hull of points (Blender coordinates) as a closed solid."""
    t = bmesh.new()
    for p in pts:
        t.verts.new(p)
    res = bmesh.ops.convex_hull(t, input=t.verts[:])
    bmesh.ops.delete(t, geom=res["geom_interior"] + res["geom_unused"], context="VERTS")
    bmesh.ops.dissolve_limit(t, angle_limit=math.radians(0.5), verts=t.verts[:], edges=t.edges[:])
    t.verts.index_update()
    add_solid(bm, [v.co.copy() for v in t.verts], [[v.index for v in f.verts] for f in t.faces], mat, smooth)
    t.free()


def chbox(bm, c0, c1, r0, r1, h0, h1, ch, mat, chz=None):
    """A box over pixel edges with every edge chamfered by ch px (chz vertically)."""
    chz = ch if chz is None else chz
    pts = []
    for c, sc in ((c0, 1), (c1, -1)):
        for r, sr in ((r0, 1), (r1, -1)):
            for h, sh in ((h0, 1), (h1, -1)):
                pts += [P(c + sc * ch, r, h + sh * chz), P(c, r + sr * ch, h + sh * chz),
                        P(c + sc * ch, r + sr * ch, h)]
    hull(bm, pts, mat)


def ccw(poly):
    a = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    return poly if a > 0 else poly[::-1]


def offset(poly, d):
    """Offset a ccw polygon (Blender XY) inward by d (mitred corners)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((-e0.y, e0.x)), Vector((-e1.y, e1.x))  # inward (left) normals
        m = (n0 + n1)
        if m.length < 1e-6:
            m = n0
        m.normalize()
        k = d / max(0.3, m.dot(n0))
        out.append(tuple(p1 + m * k))
    return out


def prism(bm, poly_px, h0, h1, ch, mat, holes_px=(), hole_floor=None, chb=0.0):
    """A plate over a polygon of (c, r) pixel edges from h0 to h1 px, its top edge chamfered ch px
    (top ring offset inward), the bottom edge chb px; optional holes (polygons) cut through it."""
    outer = ccw([tuple(P(c, r, 0).xy) for c, r in poly_px])
    holes = [ccw([tuple(P(c, r, 0).xy) for c, r in hp])[::-1] for hp in holes_px]  # cw
    z0, z1 = h0 / 12, h1 / 12
    rings = []  # (loop xy, z)
    if chb > 0:
        rings.append((offset(outer, chb / 12), z0))
        rings.append((outer, z0 + chb / 12))
    else:
        rings.append((outer, z0))
    if ch > 0:
        rings.append((outer, z1 - ch / 12))
        rings.append((offset(outer, ch / 12), z1))
    else:
        rings.append((outer, z1))
    verts, faces = [], []

    def ring(loop, z):
        base = len(verts)
        verts.extend(Vector((x, y, z)) for x, y in loop)
        return list(range(base, base + len(loop)))

    ids = [ring(l, z) for l, z in rings]
    n = len(outer)
    for a, b in zip(ids, ids[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append([a[i], a[j], b[j], b[i]])
    # top and bottom faces (with holes)
    hole_top, hole_bot = [], []
    for hl in holes:
        hole_top.append(ring(hl, z1))
        hole_bot.append(ring(hl, z0))
        m = len(hl)
        for i in range(m):
            j = (i + 1) % m
            faces.append([hole_bot[-1][i], hole_bot[-1][j], hole_top[-1][j], hole_top[-1][i]])
    for top, zz, hl_ids, flip in ((ids[-1], z1, hole_top, False), (ids[0], z0, hole_bot, True)):
        loops = [top] + hl_ids
        tris = tessellate_polygon([[verts[i] for i in lp] for lp in loops])
        flat = [i for lp in loops for i in lp]
        for t in tris:
            f = [flat[t[0]], flat[t[1]], flat[t[2]]]
            faces.append(f[::-1] if flip else f)
    add_solid(bm, verts, faces, mat)


def band(bm, outer, inner, c0, c1, ch, mat, closed):
    """A metal band: a cross-section between `outer` and `inner` paths in the (r, h) plane (same
    point count, matched), swept along X from column c0 to c1 with its outer edges chamfered ch px.
    `closed`: the paths are loops (a strap ring); otherwise their ends are capped."""
    n = len(outer)

    def shrink(i, k):
        (ro, ho), (ri, hi) = outer[i], inner[i]
        L = math.hypot(ro - ri, ho - hi) or 1
        t = min(0.6, k / L)
        return (ro + (ri - ro) * t, ho + (hi - ho) * t)

    stations = [(c0, [shrink(i, ch) for i in range(n)]), (c0 + ch, outer), (c1 - ch, outer),
                (c1, [shrink(i, ch) for i in range(n)])]
    verts, faces = [], []

    def ring(c, path):
        base = len(verts)
        verts.extend(P(c, r, h) for r, h in path)
        return list(range(base, base + len(path)))

    outs = [ring(c, pth) for c, pth in stations]
    ins = [ring(c0, inner), ring(c1, inner)]
    m = n if closed else n - 1
    for a, b in zip(outs, outs[1:]):
        for i in range(m):
            j = (i + 1) % n
            faces.append([a[i], a[j], b[j], b[i]])
    for i in range(m):
        j = (i + 1) % n
        faces.append([ins[0][j], ins[0][i], ins[1][i], ins[1][j]])
    for o, k in ((outs[0], ins[0]), (outs[-1], ins[1])):  # end faces (annulus or strip)
        for i in range(m):
            j = (i + 1) % n
            faces.append([o[i], o[j], k[j], k[i]])
    if not closed:
        for idx in (0, n - 1):
            quad = [outs[0][idx], outs[1][idx], outs[2][idx], outs[3][idx], ins[1][idx], ins[0][idx]]
            faces.append(quad)
    add_solid(bm, verts, faces, mat, smooth=True)


def rrect(r0, r1, h0, h1, rad, seg=4):
    """A rounded rectangle loop in the (r, h) plane, starting at the top middle and running toward
    the back (r decreasing) first. Each corner has seg segments; the same order for any size, so
    an inner and outer loop match point for point."""
    pts = []
    corners = [((r0 + rad, h1 - rad), 90, 180), ((r0 + rad, h0 + rad), 180, 270),
               ((r1 - rad, h0 + rad), 270, 360), ((r1 - rad, h1 - rad), 0, 90)]
    for (cr, chh), a0, a1 in corners:
        for k in range(seg + 1):
            a = math.radians(a0 + (a1 - a0) * k / seg)
            pts.append((cr + rad * math.cos(a), chh + rad * math.sin(a)))
    return pts


def corner_path(face_r, top_h, rad, along, down, toward, seg=4):
    """An L path over a chest edge in the (r, h) plane: along the top from r = along to the edge's
    rounded corner (radius rad, edge face at r = face_r, top at h = top_h), then down the face to
    h = down. toward = -1 for the back edge (r decreasing), +1 for the front."""
    cr, chh = face_r - toward * rad, top_h - rad
    pts = [(along, top_h)]
    for k in range(seg + 1):
        a = math.radians(90 - 90 * k / seg)  # 90 -> 0 deg measured from the face normal side
        pts.append((cr + toward * rad * math.cos(a), chh + rad * math.sin(a)))
    pts.append((face_r, down))
    return pts


def sweep(bm, path, radius, sides, mat):
    """A round tube through Blender points, capped."""
    pts = [Vector(p) for p in path]
    rings, prev_u = [], None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(ref).normalized()
        if prev_u is not None and u.dot(prev_u) < 0:
            u = -u
        prev_u = u
        v = t.cross(u).normalized()
        rings.append([p + radius * (math.cos(2 * math.pi * k / sides) * u + math.sin(2 * math.pi * k / sides) * v)
                      for k in range(sides)])
    verts = [v for rg in rings for v in rg]
    faces = []
    for a in range(len(rings) - 1):
        for k in range(sides):
            j = (k + 1) % sides
            faces.append([a * sides + k, a * sides + j, (a + 1) * sides + j, (a + 1) * sides + k])
    faces.append(list(range(sides))[::-1])
    faces.append([(len(rings) - 1) * sides + k for k in range(sides)])
    add_solid(bm, verts, faces, mat, smooth=True)


def cyl_x(bm, c0, c1, r, h, rad, sides, mat, ch=0.0):
    """A cylinder along X at (r, h) with radius rad px, ends chamfered ch px."""
    pts = []
    for c, rr in ((c0, rad - ch), (c0 + ch, rad), (c1 - ch, rad), (c1, rad - ch)):
        for k in range(sides):
            a = 2 * math.pi * k / sides
            pts.append(P(c, r + rr * math.cos(a), h + rr * math.sin(a)))
    hull(bm, pts, mat, smooth=True)


def dome(bm, c, r, h, rad, height, mat, axis="z"):
    """A low rivet dome (hull of rings)."""
    pts = []
    for k in range(8):
        a = 2 * math.pi * k / 8
        for t, s in ((0.0, 1.0), (0.55, 0.8), (1.0, 0.35)):
            dx, dy, dz = rad * s * math.cos(a), rad * s * math.sin(a), height * t
            if axis == "z":
                pts.append(P(c + dx, r + dy, h + dz))
            else:  # facing +r (front face)
                pts.append(P(c + dx, r + dz, h + dy))
    hull(bm, pts, mat, smooth=True)


# ------------------------------------------------------------------------------------------------
# The chest
# ------------------------------------------------------------------------------------------------

# Plan (inner mask of the sprite, pixel edges): body c 13..85, r 19..54; straps c 24..35 and
# 62..73, r 18..55; centre c 35..62 with 1 px notches (r 20 over c 43..53 at the back, r 53 over
# c 42..53 at the front); handle loop r 4..15 with fork brackets r 15..19.
BOT = 1.5     # body bottom (skids below)
TOPW = 15.0   # wood plank tops
LID = 13.4    # under the top planks / frame
SEAM = (9.4,)  # board seams on the walls (with the 5.4 one below)
WALLS = [(BOT, 5.4), (5.4, 9.4), (9.4, LID)]
ENDS = {  # (c0, c1, outer face column, planks as row ranges)
    "L": (13.0, 24.6, 13.0, [(19, 26), (26, 33), (33, 41), (41, 47), (47, 54)]),
    "R": (72.4, 85.0, 85.0, [(19, 24), (24, 32), (32, 40), (40, 47), (47, 54)]),
}
CENTRE = [(35, 19), (42.6, 19), (43.4, 20), (52.6, 20), (53.4, 19), (62, 19), (62, 54), (53.4, 54),
          (52.6, 53), (42.4, 53), (41.6, 54), (35, 54)]
STRAPS = (24.0, 62.0)
HX = (39.0, 57.0)  # handle legs / bracket centres


def build(M, coll):
    WOOD_A = M(26, 0.0, 0.78)
    WOOD_B = M(25, 0.0, 0.8)
    CORE = M(21, 0.0, 0.9)
    PANEL = M(23, 0.0, 0.85)
    SKULL = M(18, 0.0, 0.7)
    BAND = M(10, 0.45, 0.4)   # satin grey steel
    CAP_B = M(9, 0.45, 0.36)
    CAP_F = M(8, 0.45, 0.36)
    IRON = M(7, 0.5, 0.42)
    PIN = M(11, 0.55, 0.32)
    RIVET = M(12, 0.55, 0.32)

    bm = bmesh.new()
    px = bmesh.new()  # sealed proxy of the outer form, for the outline shell

    # --- core and bottom board ---
    chbox(bm, 14.0, 84.0, 20.6, 52.4, BOT, LID + 0.2, 0.2, CORE)
    chbox(bm, 13.4, 84.6, 20.2, 52.8, 0.9, BOT + 0.2, 0.3, CORE)  # inside the 1 px notches

    # --- wooden ends: top planks across X, horizontal wall boards, corner battens ---
    for side, (c0, c1, face, planks) in ENDS.items():
        out = -1 if side == "L" else 1
        for k, (r0, r1) in enumerate(planks):
            mat = WOOD_A if k % 2 == 0 else WOOD_B
            lift = (0.0, 0.15, -0.1, 0.1, 0.0)[k]
            chbox(bm, c0, c1, r0 + 0.12, r1 - 0.12, LID - 0.4, TOPW + lift, 0.38, mat, chz=0.32)
        for k, (h0, h1) in enumerate(WALLS):
            mat = WOOD_B if k % 2 == 0 else WOOD_A
            # front and back boards
            chbox(bm, c0 + 0.2, c1 - 0.2, 53.35, 54.0, h0 + 0.1, h1 - 0.1, 0.28, mat)
            chbox(bm, c0 + 0.2, c1 - 0.2, 19.0, 19.65, h0 + 0.1, h1 - 0.1, 0.28, mat)
            # end face boards
            ec0, ec1 = (face, face + 0.65) if out < 0 else (face - 0.65, face)
            chbox(bm, ec0, ec1, 19.3, 53.7, h0 + 0.1, h1 - 0.1, 0.28, mat)
        # corner battens (vertical) at the outer corners
        bc0, bc1 = (face, face + 1.5) if out < 0 else (face - 1.5, face)
        for r0, r1 in ((19.0, 20.5), (52.5, 54.0)):
            chbox(bm, bc0, bc1, r0, r1, BOT - 0.2, LID + 0.1, 0.35, WOOD_A)
        chbox(px, c0, c1, 19.0, 54.0, BOT - 0.6, TOPW, 0.3, 0)

    # --- centre: lid body, lid seam, mitred frame, recessed panel, skull inlay ---
    prism(bm, CENTRE, BOT, SEAM[0] - 0.3, 0.3, WOOD_B, chb=0.3)
    inset = [(c + (0.5 if c < 48 else -0.5), r + (0.5 if r < 36 else -0.5)) for c, r in CENTRE]
    prism(bm, inset, SEAM[0] - 0.4, SEAM[0] + 0.6, 0.0, CORE)
    prism(bm, CENTRE, SEAM[0] + 0.3, LID, 0.3, WOOD_B, chb=0.3)
    o = CENTRE
    i_tl, i_tr, i_br, i_bl = (39, 26), (58, 26), (58, 48), (39, 48)
    members = [
        ([o[0], o[1], o[2], o[3], o[4], o[5], i_tr, i_tl], WOOD_A),    # back member
        ([o[5], o[6], i_br, i_tr], WOOD_A),                            # right
        ([o[6], o[7], o[8], o[9], o[10], o[11], i_bl, i_br], WOOD_A),  # front
        ([o[11], o[0], i_tl, i_bl], WOOD_A),                           # left
    ]
    for poly, mat in members:
        prism(bm, poly, LID - 0.3, 15.6, 0.7, mat)
    prism(bm, [(39.4, 26.4), (57.6, 26.4), (57.6, 47.6), (39.4, 47.6)], LID - 0.4, 14.0, 0.0, PANEL)
    # skull: a dark inlay plate with eye, nose and tooth holes down to the panel
    skull = [(44.6, 29.4), (52.4, 29.4), (53.8, 30.0), (54.6, 31.4), (54.7, 36.6), (54.2, 38.2),
             (52.6, 38.9), (52.2, 39.4), (52.1, 43.8), (51.3, 45.2), (49.6, 45.7), (47.4, 45.7),
             (45.7, 45.2), (44.9, 43.8), (44.8, 39.4), (44.4, 38.9), (42.8, 38.2), (42.3, 36.6),
             (42.4, 31.4), (43.2, 30.0)]
    eye_l = [(43.2, 35.0), (46.8, 35.0), (47.0, 36.0), (46.0, 37.8), (44.4, 37.8), (43.1, 36.6)]
    eye_r = [(50.0, 35.0), (53.8, 35.0), (53.9, 36.6), (52.6, 37.8), (51.0, 37.8), (49.9, 36.0)]
    nose = [(47.9, 37.2), (49.1, 37.2), (49.0, 38.6), (48.5, 39.2), (48.0, 38.6)]
    teeth = [[(c, 41.9), (c + 0.9, 41.9), (c + 0.9, 43.9), (c, 43.9)] for c in (46.95, 48.95)]
    prism(bm, [(c, r) for c, r in skull], 13.8, 14.75, 0.22, SKULL, holes_px=[eye_l, eye_r, nose] + teeth)
    prism(px, CENTRE, BOT - 0.6, 15.6, 0.4, 0)
    # front lock: a hasp plate in the front notch, its staple and a small padlock body
    chbox(bm, 45.6, 50.4, 52.5, 53.3, 8.4, 14.2, 0.25, IRON)
    for cc in (46.4, 49.6):
        dome(bm, cc, 53.25, 13.2, 0.45, 0.3, RIVET, axis="r")
    hull(bm, [P(c, r, h) for c in (46.6, 49.4) for r, h in ((53.25, 7.2), (53.25, 10.6), (53.75, 10.4), (53.75, 7.4))], PIN)
    hull(bm, [P(c, r, h) for c in (47.2, 48.8) for r, h in ((53.3, 9.4), (53.3, 11.4), (53.9, 11.2), (53.9, 9.6))], IRON)

    # --- straps: a band ringing the chest, a corner cap over the back and the front edge ---
    t_b, t_c = 0.62, 0.36
    for c0 in STRAPS:
        c1 = c0 + 11.0
        inner = rrect(19.0, 54.0, 1.0, TOPW, 1.2)
        outer = rrect(19.0 - t_b, 54.0 + t_b, 1.0 - t_b, TOPW + t_b, 1.2 + t_b)
        band(bm, outer, inner, c0, c1, 0.3, BAND, closed=True)
        top = TOPW + t_b
        for face, along, down, toward, mat in ((19.0 - t_b, 23.2, 7.5, -1, CAP_B),
                                               (54.0 + t_b, 46.4, 7.0, 1, CAP_F)):
            ip = corner_path(face, top, 1.2 + t_b, along, down, toward)
            op = corner_path(face - toward * t_c, top + t_c, 1.2 + t_b + t_c, along, down, toward)
            # outer path: same 'along' and 'down' ends, offset outward
            band(bm, op, ip, c0 - 0.02, c1 + 0.02, 0.3, mat, closed=False)
        # rivets on the caps' faces (front and back), and two on each cap top
        for cc in (c0 + 2.6, c1 - 2.6):
            dome(bm, cc, 54.0 + t_b + t_c - 0.05, 10.2, 0.75, 0.45, RIVET, axis="r")
            dome(bm, cc, 19.0 - t_b - t_c + 0.05, 10.2, 0.75, -0.45, RIVET, axis="r")
        chbox(px, c0, c1, 18.0, 55.0, 0.4, top + t_c, 0.6, 0)

    # --- handle: fork brackets on the back edge, a hinge barrel, a bent bar loop folded back ---
    for hx in HX:
        for cc0, cc1 in ((hx - 2.45, hx - 1.25), (hx + 1.25, hx + 2.45)):  # fork cheeks
            hull(bm, [P(c, r, h) for c in (cc0, cc1) for r, h in
                      ((19.6, 12.0), (19.6, 15.9), (18.6, 16.6), (16.6, 16.9), (15.3, 16.1), (15.1, 14.6),
                       (16.2, 13.2), (18.3, 12.0))], IRON)
            cyl_x(bm, cc0 - 0.25, cc1 + 0.25, 16.6, 14.9, 0.7, 8, PIN, ch=0.15)
        chbox(bm, hx - 3.0, hx + 3.0, 18.4, 21.4, 15.2, 16.2, 0.35, IRON)  # base plate on the frame
        for cc in (hx - 1.8, hx + 1.8):
            dome(bm, cc, 20.4, 16.15, 0.55, 0.35, RIVET)
        cyl_x(bm, hx - 1.2, hx + 1.2, 16.6, 14.9, 1.25, 10, IRON, ch=0.2)  # handle eye on the pin
        hull(px, [P(c, r, h) for c in (hx - 2.6, hx + 2.6) for r, h in
                  ((19.6, 12.0), (19.6, 16.2), (16.6, 17.0), (15.1, 16.1), (15.1, 14.0), (17.0, 12.0))], 0)
    # loop: legs from the eyes straight back, then a round end; tilted up 9 deg from the pin
    tilt = math.radians(9)
    rad_t = 1.18
    cx, cr, rx, ry = 48.0, 13.9, 9.0, 7.75
    path = [(HX[0], 16.6), (HX[0], 15.2), (HX[0], cr)]
    for k in range(1, 24):
        a = math.pi * k / 24
        path.append((cx - rx * math.cos(a), cr - ry * math.sin(a)))
    path += [(HX[1], cr), (HX[1], 15.2), (HX[1], 16.6)]
    pts3 = [P(c, r, 14.9 + (16.6 - r) * math.tan(tilt)) for c, r in path]
    sweep(bm, pts3, rad_t / 12, 10, IRON)
    sweep(px, pts3, (rad_t + 0.05) / 12, 10, 0)

    # --- skids underneath (it skates sideways): plain closed rails ---
    for r0, r1 in ((21.0, 23.4), (49.6, 52.0)):
        hull(bm, [P(c, r, h) for r in (r0, r1) for c, h in
                  ((15.0, 1.2), (16.6, 0.0), (81.4, 0.0), (83.0, 1.2), (83.0, 1.5), (15.0, 1.5))], IRON)
    chbox(px, 13.4, 84.6, 20.2, 52.8, 0.0, 2.0, 0.4, 0)

    mesh = bpy.data.meshes.new(NAME)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for m in M.list:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    mesh.set_sharp_from_angle(angle=math.radians(35))

    pmesh = bpy.data.meshes.new(NAME + "_proxy")
    bmesh.ops.recalc_face_normals(px, faces=px.faces)
    px.to_mesh(pmesh)
    px.free()
    proxy = bpy.data.objects.new(NAME + "_proxy", pmesh)
    coll.objects.link(proxy)
    return obj, proxy


def split_open(obj, layout, coll):
    """common.split_assembly without filling the cut faces: each piece's part of a closed shell,
    left open at the seams (for the outline shell)."""
    result = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name + "_outline")
        bm.to_mesh(mesh)
        bm.free()
        o = bpy.data.objects.new(name + "_outline", mesh)
        coll.objects.link(o)
        result[name] = o
    return result


def layout(sprite):
    return [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    sprite = merged_sprite()
    M = Mats(sprite)
    obj, proxy = build(M, coll)
    lay = layout(sprite)
    pieces = common.split_assembly(obj, lay, coll)
    # One outline shell for the whole chest (from the sealed proxy), cut open at the piece seams
    # without capping, so no ink line runs across the chest where two pieces meet.
    bpy.context.view_layer.update()
    whole_shell = common.outline_shell(proxy, coll, voxel=0.012, faces=3500, inside=0.006)
    shell_parts = split_open(whole_shell, lay, coll)
    shells, total = [], 0
    for name, dx, dy in lay:
        p = pieces[name]
        sh = shell_parts[name]
        sh.name = sh.data.name = f"{name}_outline"
        sh.data.materials.append(whole_shell.data.materials[0])
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        p.data.set_sharp_from_angle(angle=math.radians(35))
        tris = sum(len(f.vertices) - 2 for f in p.data.polygons)
        total += tris
        print(f"{name}: {tris} tris, shell {len(sh.data.polygons)} faces")
        shells.append(sh)
    bpy.data.objects.remove(whole_shell, do_unlink=True)
    if "--pieces" in argv:  # piece-local glbs (game contract layout) into a scratch folder only
        pd = Path(argv[argv.index("--pieces") + 1])
        for (name, _, _), sh in zip(lay, shells):
            common.export_glb([pieces[name], sh], pd / f"{name}.glb")
    for (name, _, _), sh in zip(lay, shells):  # game contract: piece-local export
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name], sh], f"enemies/{name}", data["sprites"])
    for (name, dx, dy), sh in zip(lay, shells):
        for o in (pieces[name], sh):
            o.location = (dx / 12, -dy / 12, 0)
    print("total tris", total)
    bpy.data.objects.remove(proxy, do_unlink=True)
    bpy.context.view_layer.update()
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        common.export_glb([pieces[n] for n, _, _ in lay] + shells, out)
        print("exported", out)
    if "--review" in argv:
        rv = Path(argv[argv.index("--review") + 1])
        rv.mkdir(parents=True, exist_ok=True)
        (rv / "stats.json").write_text(json.dumps({"tris": total, "pal": sorted(m.name for m in M.list)}))
        review(obj, [pieces[n] for n, _, _ in lay], shells, rv)


def review(whole, pieces, shells, out):
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rev")
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    sh = scene.display.shading
    for s in shells:
        s.hide_render = True
    eng = None
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = e
            eng = e
            break
        except TypeError:
            pass
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 3.2
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(15))
    scene.world.use_nodes = True
    bgn = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs[0].default_value = (0.06, 0.065, 0.075, 1)
    bgn.inputs[1].default_value = 3.0

    def cam(name, loc, look, ortho=None, lens=50, rx=900, ry=600, rot=None):
        d = bpy.data.cameras.new(name)
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        d.clip_end = 500
        o = bpy.data.objects.new(name, d)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = rot if rot else (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = o
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        return o

    def shot(path, flat=False, transparent=False):
        if not flat and eng:
            scene.render.engine = eng
            scene.render.film_transparent = transparent
        else:
            scene.render.engine = "BLENDER_WORKBENCH"
            sh.light = "FLAT"
            sh.color_type = "MATERIAL"
            sh.show_cavity = False
            sh.show_object_outline = False
            sh.show_specular_highlight = False
            scene.render.film_transparent = transparent
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    k = 8
    whole.hide_render = True
    cam("top", (0, 0, 40), (0, 0, 0), ortho=W / 12, rx=W * k, ry=H * k, rot=(0, 0, 0))
    shot(out / "top_mask.png", flat=True, transparent=True)
    shot(out / "top_lit.png")
    zc = 0.6
    for nm, loc, look, orth, rx, ry in (("front", (0, -60, zc), (0, 0, zc), 6.6, 1000, 420),
                                        ("rear", (0, 60, zc), (0, 0, zc), 6.6, 1000, 420),
                                        ("side_l", (-60, 0, zc), (0, 0, zc), 4.4, 700, 420),
                                        ("side_r", (60, 0, zc), (0, 0, zc), 4.4, 700, 420)):
        cam(nm, loc, look, ortho=orth, rx=rx, ry=ry)
        shot(out / f"{nm}.png")
    d = 13.0
    ctr = Vector((0, 0.2, zc))
    for nm, az, el in (("q_fl", -40, 35), ("q_br", 150, 30), ("q_high", 25, 55)):
        a, e = math.radians(az), math.radians(el)
        cam(nm, ctr + Vector((d * math.cos(e) * math.sin(a), -d * math.cos(e) * math.cos(a), d * math.sin(e))), ctr,
            lens=50, rx=1000, ry=700)
        shot(out / f"{nm}.png")
    for nm, tdeg in (("game15", 15), ("game32", 32)):
        t = math.radians(tdeg)
        cam(nm, ctr + Vector((0, -d * math.sin(t), d * math.cos(t))), ctr, lens=50, rx=1000, ry=700)
        shot(out / f"{nm}.png")
    t = math.radians(15)
    cam("game_small", ctr + Vector((0, -d * 2.6 * math.sin(t), d * 2.6 * math.cos(t))), ctr, lens=50, rx=360, ry=250)
    shot(out / "game_small.png")
    cam("under", (0, 0, -40), (0, 0, 0), ortho=W / 12 * 1.05, rx=W * 8, ry=H * 8, rot=(math.pi, 0, 0))
    shot(out / "under.png")


if __name__ == "__main__":
    main()
