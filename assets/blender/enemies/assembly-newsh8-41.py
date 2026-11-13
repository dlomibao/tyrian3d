"""Grey twin-pod gunship (newsh8.shp, assembly of 6 pieces, 72 x 56 px): the final model.

Seen in episode 3 (IXMUCANE 3.4, SAWBLADES 3.9). A flying gunship: two grey engine pods either side
of a red spine. The spine runs from a split glossy dome at the front, through a neck, a T-shaped guard
and a stepped arrowhead chest whose wings reach the pods, to a long spike lying in the valley of a
grey twin-lobed keel. Struts tie the pods to the keel.

Each pod (the sprite's own features, front to back): a red cowl drum across its front and a red
muzzle beside it; a front band; a ribbed outer strip with a bright round rail inside it, a louvre bay
of five tilted slats, a raised inner spine strip, a pipe down the inner flank; a plain panel, a red
slot, a light lip band; a seam; then a recessed grille bay with five glowing vertical bars in a dark
red frame, a guard rail standing off the outer side (the sprite's 1 px slit), and a rear bumper.

Sprite px coordinates: column edge u, row edge v; x = u - 36, y = 28 - v, z up (12 px = 1 unit).
The spine's axis is u = 35.5. The right pod is the left pod mirrored about x = 0 (the sprite draws
it one column further out) and stretched 1 px longer, as the sprite draws it.

Colour: each part takes its sprite region's trimmed-median palette index: pods 7, slats/lip 9, louvre
recess 4, ribs 6, rails/pipe 8, dome 5, keel 6 (polished, D176), spine 70, guard 72, cowl/slot 69,
muzzle 71, lower chest/spike 68, grille frame 65, grille 117 with hot bars 124 (glows: metallic 1,
rough, D126/D173). Bright sprite pixels (the dome's highlight, the rails, the spine's ridge) are
sheen. Texture: AO/roughness bake only (usp_talon.bake_maps), no concept projection. Outline shell
(D51/D90) from a closed copy of the whole craft, cut open into the pieces (no ink along the cuts).
Underside: plain closed bottoms.

Run: blender -b --factory-startup -P assembly-newsh8-41.py -- [--no-bake] [--out x.glb]
     [--pieces DIR] (per-piece glbs for an in-game check, named as the game's models)
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
WT = common.repo_root(__file__)
import usp_talon as T  # noqa: E402  (bake_maps, pchip)

NAME = "assembly-newsh8-41"
ROOT = WT
HERE = Path(__file__).resolve().parent
PIECES = ["newsh8-39", "newsh8-41", "newsh8-43", "newsh8-77", "newsh8-79", "newsh8-81"]
CX0, CY0 = 56, 1  # screen px of the assembly centre (pixel edge 36, 28): the Blender origin
AX = 35.5         # the spine's axis (column edge)
PX = 1 / 12

pchip = T.pchip


def X(u):
    return u - 36.0


def Y(v):
    return 28.0 - v


# --- mesh helpers (sprite px) -------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def ring(self, pts):
        return [self.bm.verts.new(p) for p in pts]

    def face(self, vs, mat):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        return f

    def loft(self, rings, mats, cap0=True, cap1=True, smooth=True):
        """rings: lists of 3D points (same count, or a single apex point); mats: one or per band."""
        vr = [self.ring(r) for r in rings]
        if isinstance(mats, int):
            mats = [mats] * (len(vr) - 1)
        for k in range(len(vr) - 1):
            a, b = vr[k], vr[k + 1]
            if len(a) == 1 or len(b) == 1:
                ring, apex = (b, a[0]) if len(a) == 1 else (a, b[0])
                n = len(ring)
                for i in range(n):
                    f = self.face([ring[i], ring[(i + 1) % n], apex], mats[k])
                    if f:
                        f.smooth = smooth
                continue
            n = len(a)
            for i in range(n):
                j = (i + 1) % n
                f = self.face([a[i], a[j], b[j], b[i]], mats[k])
                if f:
                    f.smooth = smooth
        if cap0 and len(vr[0]) > 2:
            self.face(vr[0], mats[0])
        if cap1 and len(vr[-1]) > 2:
            self.face(vr[-1], mats[-1])
        return vr

    def hull(self, pts, mat, smooth=False):
        verts = [self.bm.verts.new(p) for p in pts]
        res = bmesh.ops.convex_hull(self.bm, input=verts, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(self.bm, geom=junk, context="VERTS")
        live = [v for v in verts if v.is_valid]
        faces = list({f for v in live for f in v.link_faces})
        bmesh.ops.dissolve_limit(self.bm, angle_limit=math.radians(1.0), verts=live,
                                 edges=list({e for f in faces for e in f.edges}))
        for f in {f for v in verts if v.is_valid for f in v.link_faces}:
            f.material_index = mat
            f.smooth = smooth


def fillet(poly, radii, seg=4):
    """Round each corner of a closed polygon [(x, y)] by its radius (a quadratic Bezier between
    the points `r` back along each edge)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        if r <= 0:
            out.append(tuple(p1))
            continue
        a = p1 + (p0 - p1).normalized() * min(r, (p0 - p1).length * 0.49)
        b = p1 + (p2 - p1).normalized() * min(r, (p2 - p1).length * 0.49)
        for k in range(seg + 1):
            t = k / seg
            q = a * (1 - t) ** 2 + p1 * 2 * t * (1 - t) + b * t * t
            out.append((q.x, q.y))
    return out


def area2(o):
    return sum(o[i][0] * o[i - 1][1] - o[i - 1][0] * o[i][1] for i in range(len(o))) * -0.5


def ccw(o):
    return o if area2(o) > 0 else list(reversed(o))


def inset(o, d):
    """Every edge of the CCW polygon moved d inward (mitred)."""
    n = len(o)
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = o[i], o[(i + 1) % n]
        ln = math.hypot(x1 - x0, y1 - y0) or 1e-9
        lines.append(((x0 - (y1 - y0) / ln * d, y0 + (x1 - x0) / ln * d), (x1 - x0, y1 - y0)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-9:
            out.append(q)
            continue
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    return out


def dedupe(o, eps=1e-3):
    out = []
    for p in o:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > eps:
            out.append(p)
    while len(out) > 2 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= eps:
        out.pop()
    return out


def uv_poly(pts):
    """[(u, v)] to CCW [(x, y)]."""
    return ccw(dedupe([(X(u), Y(v)) for u, v in pts]))


def rpoly(pts, radii, seg=4):
    """[(u, v)] with a radius per corner to a CCW filleted [(x, y)]."""
    xy = [(X(u), Y(v)) for u, v in pts]
    return ccw(fillet(xy, radii, seg=seg))


def slab(M, o, z0, z1, mat, ch=0.0, chb=0.0, top=None):
    """A prism over the CCW outline o from z0 to z1, its top edge given a rounded chamfer ch and its
    bottom edge a plain chamfer chb."""
    o = dedupe(o)
    rings = []
    if chb:
        rings.append([(x, y, z0) for x, y in inset(o, chb)])
        rings.append([(x, y, z0 + chb) for x, y in o])
    else:
        rings.append([(x, y, z0) for x, y in o])
    if ch:
        rings.append([(x, y, z1 - ch) for x, y in o])
        rings.append([(x, y, z1 - ch * 0.3) for x, y in inset(o, ch * 0.3)])
        rings.append([(x, y, z1) for x, y in inset(o, ch)])
    else:
        rings.append([(x, y, z1) for x, y in o])
    mats = [mat] * (len(rings) - 1)
    vr = M.loft(rings, mats, cap0=True, cap1=False, smooth=False)
    M.face(vr[-1], mat if top is None else top)


def box(M, u0, v0, u1, v1, z0, z1, mat, ch=0.0, chb=0.0, r=0.0, top=None):
    o = uv_poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    if r:
        o = fillet(o, r, seg=3)
    slab(M, o, z0, z1, mat, ch=ch, chb=chb, top=top)


def rod(M, pts, r, mat, sides=10, cap=True, rz=None):
    """A round bar through [(x, y, z)] (px) with radius r (rz vertical), domed ends."""
    rz = r if rz is None else rz
    P = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        side = t.cross(Vector((0, 0, 1)))
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        up = side.cross(t).normalized()
        rings.append([tuple(p + side * (r * math.cos(2 * math.pi * k / sides)) +
                            up * (rz * math.sin(2 * math.pi * k / sides))) for k in range(sides)])
    if cap:
        t0 = (P[1] - P[0]).normalized()
        t1 = (P[-1] - P[-2]).normalized()
        c0 = [tuple(Vector(q) * 0.55 + (P[0] - t0 * r * 0.45) * 0.45) for q in rings[0]]
        c1 = [tuple(Vector(q) * 0.55 + (P[-1] + t1 * r * 0.45) * 0.45) for q in rings[-1]]
        rings = [[tuple(P[0] - t0 * r * 0.6)], c0] + rings + [c1, [tuple(P[-1] + t1 * r * 0.6)]]
    M.loft(rings, mat, cap0=False, cap1=False, smooth=True)


def station_loft(M, stations, section, mats, apex0=False, apex1=False):
    """Loft along the sprite's rows: stations [v], section(v) -> [(x, z)] closed (CCW seen from the
    front, -y). Ends collapse to a point when apex0/apex1."""
    rings = []
    for v in stations:
        rings.append([(x, Y(v), z) for x, z in section(v)])
    if apex0:
        r = rings[0]
        rings[0] = [tuple(sum(p[k] for p in r) / len(r) for k in range(3))]
    if apex1:
        r = rings[-1]
        rings[-1] = [tuple(sum(p[k] for p in r) / len(r) for k in range(3))]
    M.loft(rings, mats, cap0=not apex0, cap1=not apex1, smooth=True)


def frange(a, b, step):
    n = max(1, int(round((b - a) / step)))
    return [a + (b - a) * k / n for k in range(n + 1)]


# --- materials ----------------------------------------------------------------------------------

(GREY, LIGHT, RECESS, RIB, RAIL, DOME, RED, GUARD, CAP, MUZZLE, RED_DK, FRAME, GRILLE, HOT,
 KEEL, CORE) = range(16)


def merged_sprite():
    data = common.load_sprite(ROOT, "newsh8-41")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def materials(sprite):
    def pal(i, tag, metallic, roughness, emission=0.0, spec=None):
        m = common.palette_material(sprite, i, f"nsh8_41{tag}", metallic=metallic, roughness=roughness,
                                    emission_strength=emission)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if spec is not None:
            bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    return [
        pal(7, "", 0.45, 0.42),             # GREY pod bodies, strips, struts
        pal(9, "", 0.45, 0.36),             # LIGHT slats, lip band, bumper
        pal(4, "", 0.35, 0.6),              # RECESS louvre bay floor, seams
        pal(6, "", 0.45, 0.45),             # RIB cooling fins
        pal(8, "", 0.6, 0.26, spec=0.8),    # RAIL rails and the inner pipe (sheen)
        pal(5, "", 0.55, 0.2, spec=1.0),    # DOME polished dark grey
        pal(70, "", 0.3, 0.38),             # RED spine
        pal(72, "", 0.3, 0.34),             # GUARD T-guard
        pal(69, "", 0.3, 0.4),              # CAP cowl drums, slot
        pal(71, "", 0.3, 0.34),             # MUZZLE
        pal(68, "", 0.3, 0.4),              # RED_DK lower chest, spike
        pal(65, "", 0.4, 0.5),              # FRAME grille frame
        pal(115, "", 1.0, 0.9, emission=0.6),   # GRILLE deep red glow floor (sprite median 115; D126/D173)
        pal(121, "", 1.0, 0.9, emission=0.9),   # HOT orange slots (sprite hot columns 121)
        pal(6, "_keel", 0.55, 0.24, spec=0.9),  # KEEL polished lobes
        pal(124, "", 1.0, 0.9, emission=1.0),   # CORE yellow peak, rows 43-45 only
    ]


GLOWS = (GRILLE, HOT, CORE)

# --- the pod (left; the right one is this mirrored about x = 0 and stretched) --------------------

POD_Z0, POD_DECK, POD_TOP = -3.6, 2.0, 3.0   # body bottom, louvre bay floor / body top, plate tops


def pod(M, right=False):
    # Body: u 4..22, v 14.5..53; the outer side set in at the grille (the sprite's slit, col 5).
    # The right pod's outer front corner is cut back (the sprite draws it so, rows 15-17).
    front = [(4, 18.4), (5.9, 14.5)] if right else [(4, 14.5)]
    bi = [(22, 14.5), (22, 18.6), (22.9, 19.4), (22.9, 53)] if right else [(22, 14.5), (22, 53)]
    body = front + bi + [(4, 53), (4, 49.0), (6.9, 48.6), (6.9, 40.4), (4, 40.0)]
    radii = ([0.6, 0.6] if right else [1.0]) + ([1.0, 0.5, 0.5] if right else [1.0]) + [3.2, 3.2, 0.0, 0.4, 0.4, 0.0]
    o = rpoly(body, radii, seg=3)
    slab(M, o, POD_Z0, POD_DECK, GREY, ch=0.5, chb=1.4)
    # Guard rail off the outer side at the grille (col 4), standing in the slit.
    rod(M, [(X(4.55), Y(39.2), 0.6), (X(4.55), Y(44.5), 0.9), (X(4.55), Y(49.8), 0.6)], 0.55, RAIL,
        sides=8, rz=1.3)
    # Front band (rows 15-17) and the deck plates round the louvre bay, to POD_TOP.
    box(M, 6.2 if right else 4.5, 14.5, 21.6, 17.5, 1.5, POD_TOP, GREY, ch=0.45)
    box(M, 4.0, 17.3, 8.2, 38.6, 1.5, POD_TOP - 0.25, RIB, ch=0.35)          # ribbed outer strip
    box(M, 17.0, 17.3, 22.0, 38.6, 1.5, POD_TOP, GREY, ch=0.35)             # inner strip
    box(M, 18.0, 15.2, 21.0, 38.2, 2.5, POD_TOP + 0.6, GREY, ch=0.35)        # its raised spine
    box(M, 8.6, 28.6, 17.2, 32.5, 1.5, POD_TOP, GREY, ch=0.3)               # plain panel
    box(M, 8.6, 32.4, 10.8, 34.7, 1.5, POD_TOP, GREY, ch=0.2)               # slot's outer cheek
    box(M, 10.6, 32.6, 17.2, 34.6, 1.5, POD_TOP - 0.5, CAP, ch=0.15)        # red slot floor
    box(M, 8.0, 34.5, 21.4, 37.6, 1.5, POD_TOP + 0.35, LIGHT, ch=0.6)       # light lip band
    box(M, 4.2, 37.6, 22.0, 38.6, 1.5, POD_TOP - 0.1, GREY, ch=0.3)         # row 38 band
    # Ribs on the outer strip (rows 19-37, every other row).
    for r in range(19, 38, 2):
        v0 = r + 0.1
        box(M, 4.3, v0, 7.9, v0 + 0.85, 2.0, POD_TOP + 0.35, RIB, ch=0.25)
    # Round rail inside the ribs (col 8) and the louvre slats (rows 19-27).
    rod(M, [(X(8.55), Y(15.0), POD_TOP - 0.05), (X(8.55), Y(38.3), POD_TOP - 0.05)], 0.5, RAIL, sides=8)
    for r in (19, 21, 23, 25, 27):
        c = r + 0.5
        t, h = 0.32, 0.75  # slat half thickness, tilt rise
        pts = []
        for u in (9.0, 16.9):
            pts += [(X(u), Y(c - 0.85), POD_DECK + 0.15 - t), (X(u), Y(c - 0.85), POD_DECK + 0.15 + t),
                    (X(u), Y(c + 0.75), POD_TOP - 0.1 - t), (X(u), Y(c + 0.75), POD_TOP - 0.1 + t)]
        M.hull(pts, LIGHT)
    box(M, 8.6, 17.4, 17.2, 29.0, POD_DECK - 0.6, POD_DECK, RECESS)           # bay floor
    # Seam (row 39), then the grille bay: dark red frame, glowing floor, five hot bars.
    gf = [(7.0, 39.6), (22.0, 39.6), (22.0, 50.6), (6.2, 50.6)]
    o = fillet(uv_poly(gf), 0.4, seg=2)
    inner = uv_poly([(7.0, 40.4), (21.2, 40.4), (21.2, 48.7), (7.0, 48.7)])
    slab(M, o, 1.0, POD_TOP - 0.2, FRAME, ch=0.3)
    box(M, 7.0, 40.4, 21.2, 48.7, 0.8, POD_TOP - 0.15, GRILLE)  # the glow fills the bay to the frame
    for c in (8, 11, 14, 17, 20):
        # 1 px glowing slot per 3 px pitch (thin bar), hottest in the middle rows (43-45).
        rod(M, [(X(c + 0.5), Y(40.6), POD_TOP - 0.05), (X(c + 0.5), Y(48.5), POD_TOP - 0.05)], 0.42, HOT,
            sides=6, cap=False)
        rod(M, [(X(c + 0.5), Y(43.1), POD_TOP + 0.02), (X(c + 0.5), Y(45.9), POD_TOP + 0.02)], 0.45, CORE,
            sides=6, cap=True)
    # Rear bumper (row 52) behind a seam (row 51).
    rb = fillet(uv_poly([(5.6, 51.4), (20.6, 51.4), (19.6, 53.0), (6.6, 53.0)]), 0.6, seg=2)
    slab(M, rb, 0.0, POD_TOP - 0.3, LIGHT, ch=0.6)
    # Inner pipe down the flank (col 23, rows 19-49).
    tu = 23.85 if right else 23.0  # the sprite draws the right pipe one column further in
    rod(M, [(X(tu), Y(19.7 if right else 18.9), 0.4), (X(tu), Y(30.0), 0.5), (X(tu), Y(49.3), 0.4)], 1.05, RAIL, sides=10)
    # Pipe clamps.
    for v in (24.0, 31.0, 37.0):
        box(M, 21.6, v - 0.35, 24.0, v + 0.35, -0.8, 1.7, GREY, ch=0.2)
    # Red cowl drum across the front (cols 6-14, rows 12-13) and the red muzzle (cols 18-20).
    pts = [(X(u), Y(13.25), 1.75) for u in frange(6.8, 14.2, 0.6)]
    rod(M, pts, 1.3, CAP, sides=14, rz=1.45)
    for u in (8.6, 12.4):  # drum bands
        rod(M, [(X(u - 0.25), Y(13.25), 1.75), (X(u + 0.25), Y(13.25), 1.75)], 1.4, RED_DK, sides=14, cap=False, rz=1.55)
    rings = []
    for v, r in ((14.8, 1.8), (13.8, 1.55), (12.8, 1.1), (12.2, 0.85)):
        rings.append([(X(19.5) + r * math.cos(a), Y(v), 1.6 + r * math.sin(a))
                      for a in [2 * math.pi * k / 12 for k in range(12)]])
    rings.append([(X(19.5) + 0.45 * math.cos(2 * math.pi * k / 12), Y(12.05), 1.6 + 0.45 * math.sin(2 * math.pi * k / 12))
                  for k in range(12)])
    vr = M.loft(rings, [MUZZLE, MUZZLE, MUZZLE, MUZZLE], cap0=True, cap1=False)
    M.face(vr[-1], RECESS)  # the bore
    # Strut to the keel (rows 39-42).
    hull_pts = []
    for u, z0, z1 in ((21.0, -1.4, 1.6), (29.8, -1.0, 1.2)):
        for v0, v1 in ((38.6, 42.4),):
            hull_pts += [(X(u), Y(v0 + 0.3), z0), (X(u), Y(v1 - 0.3), z0), (X(u), Y(v0), z0 + 0.4),
                         (X(u), Y(v1), z0 + 0.4), (X(u), Y(v0), z1 - 0.4), (X(u), Y(v1), z1 - 0.4),
                         (X(u), Y(v0 + 0.4), z1), (X(u), Y(v1 - 0.4), z1)]
    M.hull(hull_pts, GREY)


# --- the spine ----------------------------------------------------------------------------------

def dome(M):
    """Split glossy dome (rows 7-22): two clamshell lobes with a groove on the axis."""
    vs = [6.75, 7.0, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5, 21.5, 22.4]
    hw = [0.0, 2.6, 4.4, 6.4, 7.5, 8.4, 8.9, 9.3, 9.45, 9.45, 9.3, 8.9, 8.3, 7.3, 6.1, 4.8, 3.8, 3.0]
    W = pchip(vs, hw)
    hv = [0.0, 1.6, 2.6, 4.0, 5.0, 5.7, 6.15, 6.4, 6.5, 6.45, 6.3, 6.0, 5.5, 4.9, 4.2, 3.5, 2.8, 2.2]
    H = pchip(vs, hv)
    z0 = -2.6
    n = 22
    ss = [math.copysign(abs(t) ** 1.5, t) for t in [-1 + 2 * k / (2 * n) for k in range(2 * n + 1)]]

    def section(v):
        w = max(W(v), 0.05)
        h = H(v)
        top = []
        for s in ss:
            x = s * w
            z = z0 + (h - z0) * (max(0.0, 1 - abs(s) ** 2.3)) ** (1 / 2.3)
            # the split: a groove on the axis with a small raised lip either side
            ax = abs(x)
            if w > 1.2:
                if ax < 0.55:
                    z -= 1.1 * (1 - (ax / 0.55) ** 2) * min(1.0, (w - 1.2) / 2)
                elif ax < 1.4:
                    z += 0.18 * math.sin(math.pi * (ax - 0.55) / 0.85)
            top.append((X(AX) + x, z))
        # closed: the top arc from +x to -x, then a flat-ish bottom back
        top = list(reversed(top))
        bottom = [(X(AX) + s * w * 0.92, z0 - 0.6 * (1 - s * s)) for s in (-0.6, 0.0, 0.6)]
        return top + bottom

    stations = [6.75 + k * 0.25 for k in range(int((22.4 - 6.75) / 0.25) + 1)]
    station_loft(M, stations, section, DOME, apex0=True, apex1=False)


def tent(hw, zr, ze, zb=-1.2, shoulder=0.55, rise=0.72):
    """A chamfered ridge section (x about the axis, z): bottom zb, sides to ze, shoulders, ridge zr."""
    xs = X(AX)
    zs = ze + (zr - ze) * rise
    pts = [(xs - hw * 0.85, zb), (xs + hw * 0.85, zb), (xs + hw, zb + 0.4), (xs + hw, ze),
           (xs + hw * shoulder, zs), (xs + hw * 0.12, zr), (xs - hw * 0.12, zr),
           (xs - hw * shoulder, zs), (xs - hw, ze), (xs - hw, zb + 0.4)]
    return pts


def spine(M):
    # Neck (rows 16-22), emerging from under the dome.
    Wn = pchip([15.5, 18.0, 21.0, 23.2], [3.6, 4.0, 3.9, 4.2])
    station_loft(M, frange(15.5, 23.2, 0.55), lambda v: tent(Wn(v), 4.6, 2.4, zb=-1.4, shoulder=0.5), RED)
    # Neck ridge rib (the light stripe on the axis, rows 17-22).
    rod(M, [(X(AX), Y(16.4), 4.55), (X(AX), Y(22.8), 4.4)], 0.55, GUARD, sides=8, rz=0.35)
    # T guard (rows 23-25) with its claw ends (rows 26-27).
    ends = [(29.0, 22.9), (42.0, 22.9), (42.0, 26.0), (29.0, 26.0)]
    o = fillet(uv_poly(ends), 0.6, seg=2)
    slab(M, o, 1.0, 4.4, GUARD, ch=0.8, chb=0.4)
    for sgn in (-1, 1):
        u0 = AX + sgn * 6.5
        pts = []
        for v, z0, z1, w in ((25.0, 1.2, 3.9, 1.9), (27.0, 1.0, 2.9, 1.5), (28.1, 1.0, 2.0, 0.9)):
            ua, ub = (u0 - sgn * w, u0) if sgn > 0 else (u0, u0 - sgn * w)
            ua, ub = min(u0, u0 - sgn * w), max(u0, u0 - sgn * w)
            for u in (ua, ub):
                pts += [(X(u), Y(v), z0), (X(u), Y(v), z1)]
        M.hull(pts, GUARD)
    # Stem (rows 26-30) into the stepped arrowhead chest (rows 31-44) and the spike (to row 54).
    sv = [25.6, 26.6, 30.3, 30.75, 31.2, 34.4, 34.95, 35.4, 37.4, 38.0, 38.6, 39.5, 40.5, 41.5, 42.5, 43.5,
          44.5, 45.5, 47.0, 50.0, 53.0, 54.4, 55.3]
    sw = [3.5, 2.6, 2.5, 3.6, 7.4, 7.4, 9.0, 11.6, 11.6, 11.0, 8.0, 5.9, 5.2, 4.3, 3.0, 2.3,
          2.0, 1.55, 1.05, 0.85, 0.7, 0.5, 0.05]
    zr = [3.9, 3.9, 3.9, 4.2, 4.6, 4.6, 4.7, 4.7, 4.6, 4.5, 4.4, 4.3, 4.15, 4.0, 3.85, 3.7,
          3.6, 3.45, 3.3, 3.05, 2.75, 2.5, 2.3]
    ze = [2.2, 2.2, 2.2, 2.0, 1.9, 1.9, 1.7, 1.5, 1.5, 1.6, 1.8, 2.0, 2.1, 2.2, 2.3, 2.4,
          2.4, 2.4, 2.35, 2.2, 2.0, 1.9, 1.9]
    zb = [-1.0] * 16 + [1.0, 1.2, 1.4, 1.3, 1.2, 1.2, 1.2]
    Wc, Zr, Ze, Zb = pchip(sv, sw), pchip(sv, zr), pchip(sv, ze), pchip(sv, zb)
    stations = sorted(set(sv + frange(45.5, 55.3, 0.7)))
    mats = [RED if v < 41.0 else RED_DK for v in stations[:-1]]
    station_loft(M, stations, lambda v: tent(Wc(v), Zr(v), Ze(v), zb=Zb(v), shoulder=0.42, rise=0.62),
                 mats, apex1=True)
    # Chest ridge (the light stripe on the axis, rows 31-41).
    rod(M, [(X(AX), Y(30.8), 4.6), (X(AX), Y(35.5), 4.75), (X(AX), Y(41.5), 4.05)], 0.6, GUARD,
        sides=8, rz=0.3)
    # Twin-lobed grey keel under the chest and spike (rows 39-54).
    kv = [38.4, 40.0, 42.0, 43.5, 45.5, 47.0, 48.5, 49.6, 50.6, 51.6, 52.6, 53.6, 54.5]
    kw = [7.6, 8.6, 9.25, 9.4, 9.0, 8.2, 7.2, 6.2, 5.2, 3.9, 2.5, 1.4, 0.5]
    kh = [2.4, 3.1, 3.5, 3.6, 3.5, 3.3, 3.0, 2.7, 2.4, 2.0, 1.6, 1.2, 0.8]
    Wk, Hk = pchip(kv, kw), pchip(kv, kh)
    nk = 16

    def keel(v):
        w, h = Wk(v), Hk(v)
        top = []
        for k in range(2 * nk + 1):
            s = -1 + k / nk
            prof = max(0.0, 1 - abs(s) ** 2.2) ** (1 / 2.2)
            valley = 1 - 0.38 * math.exp(-(s / 0.2) ** 2)
            top.append((X(AX) + s * w, -2.2 + (h + 2.2) * prof * valley))
        top = list(reversed(top))
        bottom = [(X(AX) + s * w * 0.9, -2.2 - 0.9 * (1 - s * s)) for s in (-0.6, 0.0, 0.6)]
        return top + bottom

    station_loft(M, frange(38.4, 54.5, 0.45) + [54.9], keel, KEEL, apex1=True)


# --- build --------------------------------------------------------------------------------------

def build(sprite, coll):
    mats = materials(sprite)
    # Left pod, then the right one: mirrored about x = 0 and 1 px longer (rows 14.5.. stretched).
    objs = []
    for side in (-1, 1):
        M = Mesh()
        pod(M, right=side > 0)
        if side > 0:
            k = 39.5 / 38.5
            for v in M.bm.verts:
                v.co.x = -v.co.x
                vv = 28.0 - v.co.y
                if vv > 14.5:
                    v.co.y = 28.0 - (14.5 + (vv - 14.5) * k)
            bmesh.ops.reverse_faces(M.bm, faces=M.bm.faces)
        objs.append(M)
    S = Mesh()
    dome(S)
    spine(S)
    objs.append(S)
    bm = bmesh.new()
    for M in objs:
        me = bpy.data.meshes.new("tmp")
        M.bm.to_mesh(me)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        M.bm.free()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.scale(bm, vec=(PX, PX, PX), verts=bm.verts)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(35.0))
    return obj


def split_open(obj, layout, coll):
    """Cut the outline shell into the pieces without filling the cuts (no ink along the seams)."""
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
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(o)
        out[name] = o
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    bake = "--no-bake" not in argv
    obj = build(sprite, coll)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles")
    # The outline shell from a closed copy of the whole craft (every part is a closed solid).
    shell = common.outline_shell(obj, coll, voxel=0.025, faces=6000, smooth=6, inside=0.004)
    shell.hide_render = True
    if bake:
        T.TINT = (1.0, 1.0, 1.0)
        T.TEXTURED = tuple(i for i in range(len(obj.data.materials)) if i not in GLOWS)
        T.bake_maps(obj, tempfile.mkdtemp(prefix="nsh8_41A_bake_"), size=1024, samples=64)
    pieces = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll)
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    shown = []
    pieces_dir = Path(argv[argv.index("--pieces") + 1]) if "--pieces" in argv else None
    for name, cx, cy in layout:
        p, sh = pieces[name], shells[name]
        p.data.set_sharp_from_angle(angle=math.radians(35.0))
        sh.name = f"{name}_outline"
        sh.data.shade_smooth()
        sh["tyrian_outline"] = True
        sh.data.materials.clear()
        sh.data.materials.append(outline_mat)
        objs = [p] + ([sh] if len(sh.data.polygons) else [])
        fmt = "WEBP" if bake else "AUTO"
        if pieces_dir:
            pieces_dir.mkdir(parents=True, exist_ok=True)
            common.export_glb(objs, pieces_dir / f"{name}.glb", image_format=fmt)
        common.export_sprite_model(ROOT, objs, f"enemies/{name}", common.load_sprite(ROOT, name)["sprites"],
                                   image_format=fmt)
        for o in objs:
            o.location = (cx / 12, -cy / 12, 0)
        shown += objs
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        common.export_glb(shown, out, image_format="WEBP" if bake else "AUTO")
        print("wrote", out)


if __name__ == "__main__":
    main()
