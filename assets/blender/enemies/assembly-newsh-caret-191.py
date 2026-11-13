"""UNDERDELI's red-domed wall emplacement (newsh^.shp 153/155/191/193, a 2x2 assembly
of 48x56 px), a hard-surface 3D version of its sprites.

What it is (level 4.7 UNDERDELI, harness main=14; terrain-fixed on the dark brick wall, D195):
a sensor/gun turret bolted to the wall, seen from above with its front down the screen.
- Centre: a red ball turret (columns 20-28, rows 14-22) seated in a grey cowl that hoods its back
  and sides (columns 14-34, rows 9-20; the cowl's ends curl forward beside the ball), on a red
  stem running down the wall from the ball (rows 22-30) with a raised collar band near its foot.
- Either side: a grey oval frame lying on the wall (columns 3-16, rows 27-44) around a recessed
  louvred pan, a red armoured pylon standing in its inner half (its top end bevelled at a slant),
  a grey band and a rounded red end cap below it, and a grey gusset bracket reaching in from the
  frame toward the stem's foot, ending in a clamp post.

The sprites fill their tiles with the wall's bricks; in game that wall is the HD terrain, so no
floor plate is built (D130): the machine stands on the terrain at z = 0. Mirror symmetric about
the centre of pixel column 24.

Geometry is built in sprite px (x right, y down the sprite, z up; pixel (c, r) spans [c, c+1] x
[r, r+1]) and moved to Blender at the end (1 px = 1/12 unit, sprite up = +Y, the assembly's
centre (24, 28) at the origin).

Run: blender --background --python assets/blender/enemies/assembly-newsh-caret-191.py [-- --design out.glb]
Exports the four pieces to public/models/enemies/ and src/render/spriteModels/ (each with its outline
shell); --design also writes the whole structure with its pieces for review (not part of a normal build).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent


def _find_repo():
    for p in [HERE, *HERE.parents]:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("assets/blender/common.py not found above " + str(HERE))


WT = _find_repo()
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

NAME = "assembly-newsh-caret-191"
PIECES = ["newsh-caret-153", "newsh-caret-155", "newsh-caret-191", "newsh-caret-193"]
LAYOUT = [("newsh-caret-153", -12, -14), ("newsh-caret-155", 12, -14),
          ("newsh-caret-191", -12, 14), ("newsh-caret-193", 12, 14)]
AXIS = 24.5  # mirror line: the centre of column 24


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def merged_sprite(names):
    data = common.load_sprite(WT, names[0])
    for n in names[1:]:
        data["colors"].update(common.load_sprite(WT, n)["colors"])
    return data


# --- mesh building in sprite px (helpers copied from assembly-newsh-caret-45.py) ------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def new_faces(self, before, mat, smooth):
        for f in self.bm.faces:
            if f not in before:
                f.material_index = mat
                f.smooth = smooth

    def to_object(self, name, mats, coll, ox=24.0, oy=28.0, sharp=35.0):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        for v in bm.verts:
            if v.co.z < 0.0:  # nothing below the wall
                v.co.z = 0.0
        for v in bm.verts:
            x, y, z = v.co
            v.co = Vector(((x - ox) / 12, (oy - y) / 12, z / 12))
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        try:
            me.set_sharp_from_angle(angle=math.radians(sharp))
        except Exception:
            pass
        return obj


def sweep(M, path, mat, sides=12, smooth=True, cap0=True, cap1=True, flat=0.0, phase=0.5):
    """A tube along (x, y, zc, hw, hh) px; a ring of zero size closes to a point. `flat` > 0
    flattens the lower half (a section that sits)."""
    before = set(M.bm.faces)
    pts = [Vector((x, y, z)) for x, y, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([M.bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + phase) / sides
            sa = math.sin(a)
            if flat and sa < 0:
                sa *= flat
            ring.append(M.bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (h * sa)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                M.bm.faces.new((r0[0], r1[j], r1[k]))
            elif len(r1) == 1:
                M.bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                M.bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if cap0 and len(rings[0]) > 1:
        M.bm.faces.new(list(reversed(rings[0])))
    if cap1 and len(rings[-1]) > 1:
        M.bm.faces.new(rings[-1])
    M.new_faces(before, mat, smooth)


def ellipsoid(M, cx, cy, cz, rx, ry, rz, mat, seg=24, rings=12, lower=1.0):
    before = set(M.bm.faces)
    res = bmesh.ops.create_uvsphere(M.bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        x, y, z = v.co
        v.co = Vector((cx + x * rx, cy + y * ry, cz + z * (rz if z > 0 else rz * lower)))
    M.new_faces(before, mat, True)


def hull(M, points, mat, smooth=False):
    before = set(M.bm.faces)
    verts = [M.bm.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(M.bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(M.bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(M.bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    M.new_faces(before, mat, smooth)


def cbox(x0, x1, y0, y1, z0, z1, ch, chz=None):
    chz = ch if chz is None else chz
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            pts += [(x + sx * ch, y, z1 - chz), (x, y + sy * ch, z1 - chz), (x + sx * ch, y + sy * ch, z1),
                    (x + sx * ch, y, z0), (x, y + sy * ch, z0)]
    return pts


def prism(M, outline, z0, z1, mat, ch=0.0, chz=None):
    """A convex polygon outline (px) extruded z0..z1, its top edge chamfered (inset ch, drop chz)."""
    chz = ch if chz is None else chz
    pts = [Vector(p) for p in outline]
    n = len(pts)
    top = []
    for i, q in enumerate(pts):
        a, b = pts[i - 1], pts[(i + 1) % n]
        d1 = (q - a).normalized()
        d2 = (b - q).normalized()
        n1 = Vector((d1.y, -d1.x))
        n2 = Vector((d2.y, -d2.x))
        bis = (n1 + n2)
        bis = bis / max(bis.length, 1e-6)
        s = ch / max(bis.dot(n1), 0.3)
        top.append(q + bis * s)
    # orientation: inset must point inside
    area = sum(pts[i].x * pts[(i + 1) % n].y - pts[(i + 1) % n].x * pts[i].y for i in range(n))
    if area < 0:
        top = [q - (t - q) for q, t in zip(pts, top)]
    allp = [(q.x, q.y, z0) for q in pts] + [(q.x, q.y, z1 - chz) for q in pts] + [(q.x, q.y, z1) for q in top]
    hull(M, allp, mat)


def mirror_all(M, axis):
    bm = M.bm
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def pchip_like(keys, t):
    """Smooth (cosine-eased) interpolation of a list of (t, value) keys."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            u = 0.5 - 0.5 * math.cos(math.pi * u)
            return v0 + (v1 - v0) * u
    return keys[-1][1]


def se(cx, cy, rx, ry, a, p=2.0):
    """A point of a superellipse (exponent p; 2 = ellipse) at parameter angle a (radians), y down."""
    c, s = math.cos(a), math.sin(a)
    return (cx + rx * math.copysign(abs(c) ** (2 / p), c), cy - ry * math.copysign(abs(s) ** (2 / p), s))


def arc_loft(M, cx, cy, rx, ry, a0, a1, profile, mat, steps=40, smooth=True, width=None, height=None, p=2.0,
             rscale=None):
    """A loft along an elliptical arc (angles in degrees, 0 = right, 90 = up the sprite) of a closed
    section `profile`: (radial offset, z) pairs, radial + outward. width(t) / height(t) scale the
    offsets and heights along the arc (t 0..1). Ends capped."""
    before = set(M.bm.faces)
    closed = abs(a1 - a0) >= 359.9
    rings = []
    for i in range(steps if closed else steps + 1):
        t = i / steps
        a = math.radians(a0 + (a1 - a0) * t)
        pp = p(a) if callable(p) else p
        rs = rscale(t) if rscale else 1.0
        px, py = se(cx, cy, rx * rs, ry * rs, a, pp)
        qa, qb = se(cx, cy, rx * rs, ry * rs, a - 1e-3, pp), se(cx, cy, rx * rs, ry * rs, a + 1e-3, pp)
        tg = Vector((qb[0] - qa[0], qb[1] - qa[1]))
        nrm = Vector((tg.y, -tg.x)).normalized()
        if nrm.dot(Vector((px - cx, py - cy))) < 0:
            nrm = -nrm
        sw = width(t) if width else 1.0
        sh = height(t) if height else 1.0
        rings.append([M.bm.verts.new((px + nrm.x * d * sw, py + nrm.y * d * sw, z * sh)) for d, z in profile])
    n = len(profile)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for r0, r1 in pairs:
        for k in range(n):
            j = (k + 1) % n
            M.bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if not closed:
        M.bm.faces.new(list(reversed(rings[0])))
        M.bm.faces.new(rings[-1])
    M.new_faces(before, mat, smooth)


def ell_ring(cx, cy, rx, ry, z, hw, hh, n=48):
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n), z, hw, hh)
            for k in range(n + 1)]


def disc(M, cx, cy, rx, ry, z0, z1, mat, n=40, ch=0.3, p=2.0):
    pts = [se(cx, cy, rx, ry, 2 * math.pi * k / n, p(2 * math.pi * k / n) if callable(p) else p) for k in range(n)]
    prism(M, pts, z0, z1, mat, ch=ch)


# --- the emplacement -----------------------------------------------------------------------------

RING_C = (10.0, 36.0)   # oval frame centre (px edges)
RING_R = (5.85, 7.75)   # its tube centreline radii
RING_SKEW = 0.06
RING_P = lambda a: 2.2 if math.sin(a) > 0 else 2.0  # noqa: E731            # superellipse exponent: the sprite's frame is a squarish oval


def build(coll):
    sprite = merged_sprite(PIECES)
    tag = "nshc191A"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.55, roughness=0.42),   # 0 cowl, oval frames (satin gunmetal)
        pal(4, metallic=0.45, roughness=0.55),   # 1 pan, recesses
        pal(5, metallic=0.55, roughness=0.45),   # 2 louvres, gusset plates, bands
        pal(7, metallic=0.6, roughness=0.38),    # 3 clamp posts, knuckles, cowl lip
        pal(72, metallic=0.45, roughness=0.4),   # 4 red ball, pylons, stem
        pal(73, metallic=0.45, roughness=0.38),  # 5 red collar band, end caps
        pal(70, metallic=0.4, roughness=0.5),    # 6 dark red grooves, stem end
        pal(3, metallic=0.4, roughness=0.6),     # 7 dark sockets
    ]
    GREY, PAN, PLATE, LIGHT, RED, RED2, DRED, DARK = range(8)
    M = Mesh()
    rcx, rcy = RING_C
    rrx, rry = RING_R

    # ================= left side (mirrored about column 24's centre) =================

    # Oval frame lying on the wall: a machined collar of chamfered section.
    n_before_frame = len(M.bm.verts)
    frame_prof = [(-1.15, 0.0), (1.2, 0.0), (1.2, 0.9), (0.75, 1.75), (-0.55, 1.95), (-1.15, 1.3)]
    arc_loft(M, rcx, rcy, rrx, rry, 0, 360, frame_prof, GREY, steps=64, smooth=True, p=RING_P)
    # Recessed pan inside the frame and its louvres (left, outer half; the pylon fills the inner half).
    disc(M, rcx, rcy, rrx - 0.6, rry - 0.6, 0.0, 0.7, PAN, ch=0.15, p=RING_P)
    for y in (31.0, 33.2, 35.4, 37.6, 39.8):
        half = (rrx - 1.0) * max(0.0, 1 - abs((y - rcy) / (rry - 1.0)) ** 2.0) ** 0.5
        x0 = rcx - half
        x1 = min(rcx + 0.6, rcx + half)
        if x1 - x0 > 1.0:
            hull(M, cbox(x0, x1, y - 0.55, y + 0.55, 0.5, 1.45, 0.25), PLATE)
    # bolt heads round the frame's top
    for k in range(6):
        a = math.radians(90 + 60 * k + 30)
        bx, by = se(rcx, rcy, rrx - 0.15, rry - 0.15, a, RING_P(a))
        if bx > rcx + 0.5 and by < rcy:  # under the pylon's slanted top: no bolt
            continue
        ellipsoid(M, bx, by, 1.85, 0.42, 0.42, 0.32, LIGHT, seg=8, rings=4, lower=0.3)
    # The sprite's frame leans: its top is centred on column 9, its foot on column 11. Skew the
    # frame, pan and louvres to match (a frame turned a few degrees, not reshaped).
    M.bm.verts.ensure_lookup_table()
    for v in M.bm.verts[n_before_frame:]:
        v.co.x += RING_SKEW * (v.co.y - rcy)

    # Red armoured pylon in the frame's inner half: its top end cut at a slant, bevelled edges,
    # a groove round its top face.
    pyl = [(10.0, 28.4), (10.9, 28.4), (15.1, 33.0), (15.1, 39.9), (10.0, 39.9)]
    prism(M, pyl, 0.0, 4.6, RED, ch=0.85, chz=0.9)
    inner = [(10.95, 29.9), (11.0, 29.9), (14.15, 33.3), (14.15, 39.0), (10.95, 39.0)]
    prism(M, [(10.85, 29.7), (11.25, 29.7), (14.3, 33.1), (14.3, 39.15), (10.85, 39.15)], 4.5, 4.62, DRED)
    prism(M, inner, 4.5, 4.78, RED, ch=0.12)
    # grey band under the pylon and the rounded red end cap below it (a half drum lying across)
    hull(M, cbox(10.1, 15.4, 39.7, 41.1, 0.0, 3.4, 0.35), PLATE)
    cap = [(9.9, 42.8, 0.0, 0.0, 0.0), (10.1, 42.8, 0.0, 1.5, 2.0), (10.6, 42.8, 0.0, 1.95, 2.9),
           (14.9, 42.8, 0.0, 1.95, 2.9), (15.4, 42.8, 0.0, 1.6, 2.3), (15.7, 42.8, 0.0, 0.0, 0.0)]
    sweep(M, cap, RED2, sides=16, flat=0.02)
    # a groove ring round the cap
    sweep(M, [(12.6, 42.8, 0.0, 0.0, 0.0), (12.7, 42.8, 0.0, 2.05, 2.98), (13.1, 42.8, 0.0, 2.05, 2.98),
              (13.2, 42.8, 0.0, 0.0, 0.0)], DRED, sides=16, flat=0.02)

    # Gusset bracket from the frame toward the stem's foot: a chamfered plate, a strut along its
    # lower edge and a clamp post at its tip.
    prism(M, [(14.6, 30.6), (20.8, 32.4), (20.8, 35.4), (16.0, 37.4)], 0.0, 1.5, PLATE, ch=0.3)
    sweep(M, [(15.5, 37.7, 1.4, 0.0, 0.0), (15.8, 37.5, 1.4, 0.75, 0.9), (18.4, 36.0, 1.5, 0.75, 0.9),
              (20.8, 35.1, 1.6, 0.75, 0.9), (21.1, 35.0, 1.6, 0.0, 0.0)], LIGHT, sides=10, flat=0.3)
    sweep(M, [(15.0, 30.6, 1.3, 0.0, 0.0), (15.2, 30.7, 1.3, 0.6, 0.7), (18.4, 31.6, 1.4, 0.6, 0.7),
              (20.8, 32.4, 1.4, 0.6, 0.7), (21.0, 32.5, 1.4, 0.0, 0.0)], PLATE, sides=10, flat=0.3)

    mirror_all(M, AXIS)
    # clamp posts at the brackets' tips; the sprite draws the right one a pixel further out than
    # the left one's mirror image (columns 21 and 28), so each is placed on its own
    for x0, x1 in ((20.4, 21.9), (27.6, 29.0)):
        hull(M, cbox(x0, x1, 31.7, 35.8, 0.0, 2.6, 0.35), LIGHT)

    # ================= centre =================
    cx = AXIS
    # Grey cowl hooding the ball's back and sides: a loft along an arc of a chamfered section
    # (outer face falling to the wall, a rounded ridge, the inner face dropping toward the ball).
    cowl_prof = [(-1.0, 0.6), (1.0, 0.0), (0.95, 1.6), (0.62, 3.9), (0.25, 5.3), (-0.2, 5.6), (-0.62, 5.0),
                 (-0.95, 3.4), (-1.0, 1.8)]
    width = lambda t: pchip_like([(0.0, 1.2), (0.08, 2.0), (0.15, 2.6), (0.22, 2.5), (0.35, 2.15), (0.5, 2.45), (0.65, 2.15), (0.78, 2.5), (0.85, 2.6), (0.92, 2.0), (1.0, 1.2)], t)  # noqa: E731
    height = lambda t: pchip_like([(0.0, 0.45), (0.14, 0.9), (0.5, 1.12), (0.86, 0.9), (1.0, 0.45)], t)  # noqa: E731
    # its ends curl in toward the ball (rows 19-20, columns 16-19 and 29-32)
    rscale = lambda t: pchip_like([(0.0, 0.84), (0.06, 0.92), (0.11, 0.98), (0.2, 1.0), (0.8, 1.0), (0.89, 0.98), (0.94, 0.92), (1.0, 0.84)], t)  # noqa: E731
    COWL = (cx, 17.0, 8.15, 5.9, -30, 210)
    arc_loft(M, *COWL[:4], COWL[4], COWL[5], cowl_prof, GREY, steps=64, width=width, height=height, rscale=rscale)
    # two machined straps across the cowl's shoulders (raised bands, a hair proud of its skin)
    strap_prof = [(d * (1.0 if z < 0.9 else 1.05), z * 1.05 + 0.06) for d, z in cowl_prof]
    for ang in (38.0, 142.0):
        t0 = (ang - 2.4 - COWL[4]) / (COWL[5] - COWL[4])
        t1 = (ang + 2.4 - COWL[4]) / (COWL[5] - COWL[4])
        arc_loft(M, *COWL[:4], ang - 2.4, ang + 2.4, strap_prof, PLATE, steps=3,
                 width=lambda u, t0=t0, t1=t1: width(t0 + (t1 - t0) * u),
                 height=lambda u, t0=t0, t1=t1: height(t0 + (t1 - t0) * u),
                 rscale=lambda u, t0=t0, t1=t1: rscale(t0 + (t1 - t0) * u))
    # base plate under the cowl and the ball (dark, seen only in the gap between them)
    disc(M, cx, 16.5, 7.8, 4.2, 0.0, 0.8, DARK, ch=0.2)
    # machined lip along the cowl's inner edge
    lip = []
    for i in range(41):
        t = i / 40
        u = 0.04 + 0.92 * t
        a = math.radians(-30 + 240 * u)
        w = width(u)
        rs = rscale(u)
        px, py = se(cx, 17.0, 8.15 * rs, 5.9 * rs, a)
        qa, qb = se(cx, 17.0, 8.15 * rs, 5.9 * rs, a - 1e-3), se(cx, 17.0, 8.15 * rs, 5.9 * rs, a + 1e-3)
        nrm = Vector((qb[1] - qa[1], -(qb[0] - qa[0]))).normalized()
        if nrm.dot(Vector((px - cx, py - 17.0))) < 0:
            nrm = -nrm
        lip.append((px - nrm.x * 0.62 * w, py - nrm.y * 0.62 * w, 5.0 * height(u), 0.3, 0.3))
    sweep(M, lip, LIGHT, sides=8)
    # dark socket ring in the cowl round the ball's foot
    sweep(M, [(cx + 4.85 * math.cos(a), 18.5 - 4.75 * math.sin(a), 0.6, 0.6, 0.7)
              for a in [math.radians(-10 + 200 * k / 30) for k in range(31)]], DARK, sides=8)

    # The red ball turret, its base squashed onto the wall.
    # Seen from above it is a bulb rather than a ball: round on top, fuller low down where it
    # meets the stem (rows 16-21 are all 9 px wide).
    nb = len(M.bm.verts)
    ellipsoid(M, cx, 18.9, 3.4, 4.6, 4.8, 4.4, RED, seg=32, rings=16, lower=0.7)
    M.bm.verts.ensure_lookup_table()
    for v in M.bm.verts[nb:]:
        u = (v.co.y - 18.9) / 4.8
        if u > 0:
            v.co.x = cx + (v.co.x - cx) * (1 + 0.15 * math.sin(math.pi * u))

    # Red stem down the wall from the ball (rows 22-30): a waist under the ball, a collar band near
    # its foot and a dark end plate.
    stem = [(cx, 21.4, 2.6, 2.3, 2.6), (cx, 23.5, 2.6, 1.8, 2.55), (cx, 24.5, 2.6, 3.25, 2.95),
            (cx, 27.1, 2.6, 3.35, 3.0), (cx, 29.8, 2.6, 3.35, 3.0), (cx, 30.2, 2.6, 3.05, 2.7),
            (cx, 30.4, 2.6, 0.0, 0.0)]
    sweep(M, stem, RED, sides=20, flat=0.85)
    sweep(M, [(cx, 27.2, 2.6, 0.0, 0.0), (cx, 27.3, 2.6, 3.55, 3.2), (cx, 29.5, 2.6, 3.55, 3.2),
              (cx, 29.6, 2.6, 0.0, 0.0)], RED2, sides=20, flat=0.85)
    for y in (27.15, 29.65):
        sweep(M, [(cx, y - 0.1, 2.6, 0.0, 0.0), (cx, y - 0.08, 2.6, 3.45, 3.1), (cx, y + 0.08, 2.6, 3.45, 3.1),
                  (cx, y + 0.1, 2.6, 0.0, 0.0)], DRED, sides=20, flat=0.85)
    # end plate and boss on the stem's foot
    sweep(M, [(cx, 29.9, 2.6, 0.0, 0.0), (cx, 30.0, 2.6, 2.4, 2.1), (cx, 30.3, 2.6, 2.4, 2.1),
              (cx, 30.35, 2.6, 0.0, 0.0)], DRED, sides=16, flat=0.85)

    return M.to_object(f"{NAME}_whole", mats, coll)


def cut_open(obj, lay, coll):
    """Cut the shell to each piece's box WITHOUT filling the cut (no ink across the seams)."""
    out = {}
    for name, cx, cy in lay:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        for poly in me.polygons:
            poly.use_smooth = True
        sh["tyrian_outline"] = True
        out[name] = sh
    return out


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    whole = build(coll)
    bpy.context.view_layer.update()
    shell = common.outline_shell(whole, coll, voxel=0.012, faces=6000, islands="outer")
    assert len(shell.data.polygons) > 0
    pieces = common.split_assembly(whole, LAYOUT, coll)
    shells = cut_open(shell, LAYOUT, coll)
    manifest = {}
    objs = []
    for name, cx, cy in LAYOUT:
        p, s = pieces[name], shells[name]
        assert len(p.data.polygons) > 0, f"{name}: empty piece"
        assert len(s.data.polygons) > 0, f"{name}: empty outline shell"
        for o in (p, s):
            o["design_model"] = name
        manifest[name] = {"offset": [cx / 12, -cy / 12], "tris": sum(len(q.vertices) - 2 for q in p.data.polygons),
                          "shell_faces": len(s.data.polygons)}
        objs += [p, s]
    for name, _, _ in LAYOUT:
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"])
    design = arg("--design")
    if design:
        for name, cx, cy in LAYOUT:
            for o in (pieces[name], shells[name]):
                o.location.x += cx / 12
                o.location.y += -cy / 12
        whole["design_model"] = "whole"
        shell["design_model"] = "whole"
        common.export_glb([whole, shell] + objs, Path(design))
        print("MANIFEST", json.dumps(manifest))


if __name__ == "__main__":
    main()
