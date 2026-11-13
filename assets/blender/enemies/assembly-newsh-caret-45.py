"""UNDERDELI's wall crab and gun emplacement (newsh^.shp 157/159/161 and 45), final.

What they are (level 4.7 UNDERDELI only): two kinds of turret fixed in the dark brick wall of the
level, seen from above, their front down the screen.
- The crab (assembly-newsh-caret-45 = newsh-caret-157 | -159 | -161, 72x28 px, mirror symmetric
  about the centre of column 36): a grey armoured head dome with a red trident emblem, a two-lobed
  thorax under it, red shoulder pauldrons either side, under each a ribbed grey upper-arm sleeve
  running out to a grey ball joint, and at each end a big red hooked claw (a bulb that tapers into a
  horn curling down and in). Two red mandibles hook in under the head round a dark mouth plate.
- The gun emplacement (newsh-caret-45, 24x28 px): a ribbed armoured housing at the back with a red
  sensor eye glowing at its front edge, a wide grey turret dome in front of it, a low plinth with
  an armoured block either side and the cannon pointing down the screen between them.

The sprites fill their tiles with the wall's bricks; in game the HD terrain is that same brick wall,
so (D130) no floor plate is built: the machines stand on the terrain. The silhouette is matched to
the sprite with its ground removed (the old model's floor pixels, as D130 measured).

Geometry is built in sprite pixels (x, y edge coordinates: pixel (c, r) spans [c, c+1] x [r, r+1];
z in px) and moved to Blender at the end (one px = 1/12 unit, sprite up = +Y).
The crab is built whole, its outline shell made once from the sealed whole (islands="outer") and
both cut into the three pieces (common.split_assembly; the shells cut open, no ink across seams).

Exports the crab's three pieces (newsh-caret-157/-159/-161, each with its outline shell) to
public/models/enemies/ and their spriteModels entries. The emplacement (newsh-caret-45) is built
here too but exported only by its own script, newsh-caret-45.py, which imports this one.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh-caret-45.py
Optional review output (off by default): -- --design <glb> writes the whole set for the review renders.
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
    if "--repo" in sys.argv:
        return Path(sys.argv[sys.argv.index("--repo") + 1])
    for p in [HERE, *HERE.parents]:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("assets/blender/common.py not found above " + str(HERE))


WT = _find_repo()
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

PIECES = ["newsh-caret-157", "newsh-caret-159", "newsh-caret-161"]
LAYOUT = [("newsh-caret-157", -24, 0), ("newsh-caret-159", 0, 0), ("newsh-caret-161", 24, 0)]
CRAB_AXIS = 36.5  # mirror line (edge coordinate): the centre of column 36


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def merged_sprite(names):
    data = common.load_sprite(WT, names[0])
    for n in names[1:]:
        data["colors"].update(common.load_sprite(WT, n)["colors"])
    return data


# --- mesh building in sprite px ------------------------------------------------------------------

class Mesh:
    """A bmesh in sprite px (x right, y down the sprite, z up), faces tagged with material and smooth."""

    def __init__(self):
        self.bm = bmesh.new()

    def tag(self, faces, mat, smooth):
        for f in faces:
            f.material_index = mat
            f.smooth = smooth

    def new_faces(self, before, mat, smooth):
        self.tag([f for f in self.bm.faces if f not in before], mat, smooth)

    def to_object(self, name, mats, coll, ox, oy=14.0, sharp=35.0):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        for v in bm.verts:
            x, y, z = v.co
            v.co = Vector(((x - ox) / 12, (oy - y) / 12, z / 12))
        # y was flipped: every face's winding with it
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


def resample(outline, n):
    """A closed polygon resampled to n points evenly by arc length."""
    pts = [Vector((x, y)) for x, y in outline]
    segs = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    lens = [(b - a).length for a, b in segs]
    total = sum(lens)
    out = []
    for k in range(n):
        t = total * k / n
        for (a, b), ln in zip(segs, lens):
            if t <= ln or (a, b) == segs[-1]:
                out.append(a.lerp(b, min(t / ln, 1.0) if ln else 0.0))
                break
            t -= ln
    return out


def ell(cx, cy, rx, ry, n=40, a0=0.0, a1=2 * math.pi):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * k / n), cy + ry * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n)]


def blob(M, outline, centre, H, mat, zb=0.0, p=2.0, n=48, rings=9, zfun=None, smooth=True):
    """A faired cushion over a closed outline: rings scaled toward `centre`, height
    zb + H * (1 - s^p)^(1/p) (s = 1 at the outline: a rounded vertical edge), flat base at zb.
    `zfun(x, y)` adds a lean. Returns a height function z(x, y) for points inside (by s)."""
    before = set(M.bm.faces)
    base = resample(outline, n)
    c = Vector(centre)
    ss = [math.cos(0.5 * math.pi * k / rings) for k in range(rings)]  # 1 .. small
    ring_v = []
    for s in ss:
        zs = zb + H * max(0.0, 1 - s ** p) ** (1 / p)
        ring = []
        for q in base:
            pt = c + (q - c) * s
            dz = zfun(pt.x, pt.y) if zfun else 0.0
            ring.append(M.bm.verts.new((pt.x, pt.y, zs + dz)))
        ring_v.append(ring)
    top = M.bm.verts.new((c.x, c.y, zb + H + (zfun(c.x, c.y) if zfun else 0.0)))
    for r0, r1 in zip(ring_v, ring_v[1:]):
        for k in range(n):
            j = (k + 1) % n
            M.bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    for k in range(n):
        M.bm.faces.new((ring_v[-1][k], ring_v[-1][(k + 1) % n], top))
    M.bm.faces.new(list(reversed(ring_v[0])))
    M.new_faces(before, mat, smooth)


def ell_height(cx, cy, rx, ry, H, zb=0.0, p=2.0, zfun=None):
    def z(x, y):
        s = math.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
        return zb + H * max(0.0, 1 - min(s, 1.0) ** p) ** (1 / p) + (zfun(x, y) if zfun else 0.0)
    return z


def sweep(M, path, mat, sides=12, smooth=True, cap0=True, cap1=True, flat=0.0):
    """A tube along (x, y, zc, hw, hh) px: rings across the path in the XY plane (hw) and up (hh).
    A ring of zero size closes to a point. `flat` > 0 flattens the bottom (a section that sits)."""
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
            a = 2 * math.pi * (k + 0.5) / sides
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


def ellipsoid(M, cx, cy, cz, rx, ry, rz, mat, seg=20, rings=10, lower=1.0):
    """An ellipsoid (px); `lower` < 1 squashes the bottom half (it sits)."""
    before = set(M.bm.faces)
    res = bmesh.ops.create_uvsphere(M.bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        x, y, z = v.co
        v.co = Vector((cx + x * rx, cy + y * ry, cz + z * (rz if z > 0 else rz * lower)))
    M.new_faces(before, mat, True)


def hull(M, points, mat, smooth=False):
    """Convex hull of points (chamfered blocks), coplanar faces merged."""
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


def cbox(x0, x1, y0, y1, z0, z1, ch, chz=None, bottom_ch=False):
    """Corner points of a box with chamfered top edges (and bottom ones if asked)."""
    chz = ch if chz is None else chz
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            pts += [(x + sx * ch, y, z1 - chz), (x, y + sy * ch, z1 - chz), (x + sx * ch, y + sy * ch, z1)]
            if bottom_ch:
                pts += [(x + sx * ch, y, z0 + chz), (x, y + sy * ch, z0 + chz), (x + sx * ch, y + sy * ch, z0)]
            else:
                pts += [(x + sx * ch, y, z0), (x, y + sy * ch, z0)]
    return pts


def prism(M, outline, z0, z1, mat, ch=0.0):
    """A polygon outline (px) extruded z0..z1, its top edge chamfered by `ch` (inset toward the
    centroid, so for convex outlines)."""
    pts = [Vector(p) for p in outline]
    c = sum(pts, Vector((0, 0))) / len(pts)
    top = []
    for q in pts:
        d = q - c
        ln = d.length or 1
        top.append(q - d / ln * ch)
    allp = [(q.x, q.y, z0) for q in pts] + [(q.x, q.y, z1 - ch) for q in pts] + [(q.x, q.y, z1) for q in top]
    hull(M, allp, mat)


def mirror_all(M, axis):
    bm = M.bm
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


# --- the crab ------------------------------------------------------------------------------------

def build_crab(coll):
    sprite = merged_sprite(PIECES)
    tag = "nshc45A"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.55, roughness=0.42),  # 0 head armour
        pal(5, metallic=0.55, roughness=0.45),  # 1 thorax, collars
        pal(3, metallic=0.4, roughness=0.6),  # 2 dark grooves, mouth recess
        pal(8, metallic=0.65, roughness=0.35),  # 3 grey ball joints
        pal(6, metallic=0.55, roughness=0.42),  # 4 sleeve, ribs, rims
        pal(72, metallic=0.45, roughness=0.42),  # 5 red shoulder shells
        pal(71, metallic=0.45, roughness=0.42),  # 6 red claws, mandibles
        pal(73, metallic=0.45, roughness=0.38),  # 7 emblem
        pal(68, metallic=0.4, roughness=0.5),  # 8 dark red edges, emblem groove
        pal(3, metallic=0.5, roughness=0.5),  # 9 mouth plate
    ]
    HEAD, THORAX, DARK, BALL, RIB, SHELL, CLAW, EMBLEM, DRED, MOUTH = range(10)
    M = Mesh()

    # ---------- left half (mirrored about column 36's centre) ----------

    # Hooked claw: a bulb (columns 6-14, rows 7-14) tapering into a horn that curls down and in
    # to its tip at row 22.
    BULB = [(9.2, 7.2), (12.8, 7.2), (14.2, 8.0), (15.0, 9.4), (14.6, 11.2), (13.4, 12.2), (12.9, 13.4), (12.2, 14.4),
            (11.0, 15.2), (7.0, 15.0), (6.0, 13.0), (6.6, 10.5), (7.2, 8.8), (8.4, 8.0)]
    blob(M, BULB, (10.4, 10.8), 5.4, SHELL, zb=0.0, p=2.2)
    horn = [(10.2, 12.0, 2.6, 3.2, 2.6), (9.4, 13.5, 2.6, 3.0, 2.6), (8.8, 14.6, 2.4, 2.9, 2.4),
            (8.0, 16.4, 2.0, 2.0, 2.0), (7.7, 18.0, 1.7, 1.7, 1.7), (7.5, 19.3, 1.5, 1.4, 1.5), (7.9, 20.2, 1.3, 1.0, 1.3),
            (8.8, 21.0, 1.1, 0.9, 1.1), (9.2, 21.9, 0.8, 0.6, 0.8), (9.6, 22.5, 0.6, 0.0, 0.0)]
    sweep(M, horn, CLAW, sides=14, flat=0.3)
    # dark red cutting edge along the inner side of the horn (the sprite's shaded inner edge)
    edge = [(12.0, 12.4, 1.6, 0.0, 0.0), (11.8, 13.4, 1.6, 0.5, 0.9), (10.9, 15.0, 1.5, 0.5, 0.8),
            (9.2, 16.8, 1.3, 0.45, 0.7), (8.9, 18.6, 1.1, 0.4, 0.6), (8.9, 20.0, 0.9, 0.0, 0.0)]
    sweep(M, edge, DRED, sides=8)
    # a raised crest round the bulb's top (machined armour edge)
    crest = [(7.0, 13.0, 3.6, 0.0, 0.0), (7.2, 11.0, 4.5, 0.45, 0.35), (8.8, 9.0, 4.8, 0.45, 0.35),
             (11.2, 8.6, 4.6, 0.45, 0.35), (12.9, 9.8, 3.9, 0.0, 0.0)]
    sweep(M, crest, DRED, sides=6)

    # Wrist: grey ball joint (columns 15-22, rows 8-15) with a band round it.
    ellipsoid(M, 18.9, 11.8, 2.2, 3.85, 3.25, 2.6, BALL, seg=22, rings=10, lower=0.85)
    sweep(M, [(18.9 + 3.8 * math.cos(a), 11.8 + 3.2 * math.sin(a), 2.0, 0.4, 0.5)
              for a in [2 * math.pi * k / 24 for k in range(25)]], RIB, sides=6, cap0=False, cap1=False)
    # stub between claw and wrist
    sweep(M, [(13.4, 11.0, 2.4, 0.0, 0.0), (13.6, 11.0, 2.4, 0.9, 1.4), (16.0, 11.0, 2.4, 0.9, 1.4),
              (16.2, 11.0, 2.4, 0.0, 0.0)], RIB, sides=10)

    # hinge housing under the wrist ball (rows 14-16), a short cross pin
    sweep(M, [(16.8, 15.1, 1.4, 0.0, 0.0), (17.0, 15.1, 1.4, 1.0, 1.3), (20.0, 15.1, 1.4, 1.0, 1.3),
              (20.2, 15.1, 1.4, 0.0, 0.0)], THORAX, sides=10)
    # Upper-arm sleeve from the wrist in under the shoulder (rows 12-17), ribbed.
    sleeve = [(19.4, 14.0, 2.0, 0.0, 0.0), (19.8, 14.1, 2.0, 1.2, 1.7), (22.0, 14.5, 2.0, 1.0, 1.6),
              (23.8, 15.6, 2.2, 1.6, 2.0), (25.8, 15.6, 2.5, 2.4, 2.4), (28.2, 15.3, 2.4, 2.5, 2.2),
              (30.0, 15.5, 2.2, 1.3, 1.6), (30.8, 15.6, 2.0, 0.0, 0.0)]
    sweep(M, sleeve, RIB, sides=12, flat=0.4)
    # machined rib collars round the sleeve
    for x, y, w, hz in ((21.6, 14.45, 1.25, 1.85), (24.4, 15.6, 2.2, 2.35), (26.4, 15.35, 2.7, 2.6), (28.4, 15.0, 2.7, 2.45)):
        d = Vector((1.0, 0.18)).normalized()
        sweep(M, [(x - d.x * 0.45, y - d.y * 0.45, 2.4, 0.0, 0.0), (x - d.x * 0.4, y - d.y * 0.4, 2.4, w, hz),
                  (x + d.x * 0.4, y + d.y * 0.4, 2.4, w, hz), (x + d.x * 0.45, y + d.y * 0.45, 2.4, 0.0, 0.0)],
              THORAX, sides=12)

    # Red shoulder pauldron beside the head (columns 23-31, rows 6-12) on a dark collar.
    blob(M, ell(28.2, 9.7, 5.0, 3.4), (27.8, 9.3), 5.6, SHELL, zb=0.6, p=2.3)
    sweep(M, [(28.2 + 4.6 * math.cos(a), 9.7 + 3.0 * math.sin(a), 0.9, 0.35, 0.6)
              for a in [2 * math.pi * k / 28 for k in range(29)]], DRED, sides=6, cap0=False, cap1=False)
    blob(M, ell(28.2, 9.9, 4.4, 2.9), (28.2, 9.9), 1.0, DARK, zb=0.0, p=2.0)

    # Mandible hooking in under the head (rows 18-22, to column 34).
    mand = [(28.8, 17.6, 1.2, 0.0, 0.0), (28.9, 18.2, 1.3, 1.2, 1.3), (29.2, 19.6, 1.4, 1.5, 1.4),
            (29.6, 20.9, 1.4, 1.35, 1.4), (30.8, 21.9, 1.3, 1.4, 1.3), (33.0, 22.5, 1.1, 1.1, 1.1),
            (35.4, 22.6, 0.7, 0.0, 0.0)]
    sweep(M, mand, CLAW, sides=12, flat=0.4)

    # Trident emblem arm on the head (row 4 col 32 to the stem at row 7).
    hz = HEAD_Z
    arm = [(32.4, 4.3), (33.6, 5.3), (34.8, 6.4), (35.8, 7.3), (36.5, 7.6)]
    sweep(M, [(x, y, hz(x, y) + 0.05, 0.75, 0.35) for x, y in arm], EMBLEM, sides=8)

    n_left = len(M.bm.verts)
    mirror_all(M, CRAB_AXIS)
    # The sprite's right claw (newsh-caret-161) is drawn about 1 px fuller on its inner edge than
    # the left one's mirror image (rows 12-21): lean the mirrored claw's inner side in to match.
    M.bm.verts.ensure_lookup_table()
    for v in M.bm.verts[n_left:]:
        x, y = v.co.x, v.co.y
        if 58.4 <= x <= 67.5 and y > 10.5:
            k = 1.05 * min(1.0, max(0.0, (y - 11.0) / 1.0), max(0.0, (18.5 - y) / 1.0))
            v.co.x = x - k * min(1.0, max(0.0, (66.0 - x) / 4.0))
        # and its wrist link sits a little higher under the ball (row 15 is wall there)
        if 49.0 <= x <= 54.6 and y > 14.0:
            v.co.y = 14.0 + (y - 14.0) * 0.55

    # ---------- centre ----------
    cx = CRAB_AXIS
    # Head dome (rows 2-13), leaning a little back (its front lower toward the mandibles).
    blob(M, ell(cx, 8.2, 8.0, 6.0, n=56), (cx, 8.2), 6.4, HEAD, zb=0.0, p=2.2, n=56, rings=11)
    # seam ring round the dome's skirt
    sweep(M, [(cx + 7.4 * math.cos(a), 8.2 + 5.5 * math.sin(a), HEAD_Z(cx + 7.4 * math.cos(a), 8.2 + 5.5 * math.sin(a)) - 0.1,
               0.35, 0.3) for a in [2 * math.pi * k / 40 for k in range(41)]], DARK, sides=6, cap0=False, cap1=False)
    # Trident: centre prong (rows 3-7), its crossbar (row 3), and the stem (rows 7-12) with a groove.
    sweep(M, [(cx, y, HEAD_Z(cx, y) + 0.05, 0.7, 0.35) for y in (3.0, 4.2, 5.4, 6.6, 7.6)], EMBLEM, sides=8)
    sweep(M, [(x, 3.5, HEAD_Z(x, 3.5) + 0.05, 0.6, 0.3) for x in (cx - 1.6, cx - 0.8, cx, cx + 0.8, cx + 1.6)],
          EMBLEM, sides=8)
    sweep(M, [(cx, y, HEAD_Z(cx, y) + 0.06, w, 0.45) for y, w in
              ((7.2, 0.0), (7.5, 1.4), (9.0, 1.6), (10.5, 1.6), (11.8, 1.4), (12.2, 0.0))], EMBLEM, sides=10)
    sweep(M, [(cx, y, HEAD_Z(cx, y) + 0.45, w, 0.12) for y, w in
              ((7.8, 0.0), (8.1, 0.5), (11.2, 0.5), (11.5, 0.0))], DRED, sides=6)

    # Thorax under the head (rows 12-17): two rounded lobes with a groove between.
    for side in (-1, 1):
        lx = cx + side * 2.3
        blob(M, ell(lx, 14.4, 2.5, 2.6), (lx, 14.0), 3.6, THORAX, zb=0.0, p=2.2)
    sweep(M, [(cx, 12.2, 1.0, 0.0, 0.0), (cx, 12.6, 1.2, 0.7, 1.0), (cx, 17.2, 1.2, 0.7, 1.0), (cx, 17.7, 1.0, 0.0, 0.0)],
          DARK, sides=8)
    # Mouth plate between the mandibles (rows 19-21).
    hull(M, cbox(30.4, 42.6, 19.9, 21.0, 0.0, 1.5, 0.45), MOUTH)
    # chin boss on the mouth plate's centre
    ellipsoid(M, cx, 19.9, 1.2, 1.3, 1.0, 1.0, DARK, seg=12, rings=6, lower=0.5)

    obj = M.to_object("crab_whole", [*mats], coll, ox=36.0)
    return obj


HEAD_Z = ell_height(36.5, 8.2, 8.0, 6.0, 6.4, p=2.2)


# --- the gun emplacement -------------------------------------------------------------------------

def build_emplacement(coll):
    sprite = common.load_sprite(WT, "newsh-caret-45")
    tag = "nshc45eA"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(3, metallic=0.4, roughness=0.6),  # 0 plinth, grooves
        pal(4, metallic=0.5, roughness=0.48),  # 1 housing body
        pal(6, metallic=0.55, roughness=0.42),  # 2 housing fins (shaded side), block tops
        pal(7, metallic=0.55, roughness=0.4),  # 3 lit panel, sensor box
        pal(7, metallic=0.6, roughness=0.36),  # 4 dome
        pal(9, metallic=0.6, roughness=0.35),  # 5 block fronts
        pal(10, metallic=0.6, roughness=0.34),  # 6 bright fin
        pal(4, metallic=0.5, roughness=0.45),  # 7 cannon
        pal(119, metallic=1.0, roughness=1.0, emission_strength=1.6),  # 8 eye
        pal(125, metallic=1.0, roughness=1.0, emission_strength=1.4),  # 9 eye core
        pal(116, metallic=0.4, roughness=0.5),  # 10 eye rim
        pal(2, metallic=0.3, roughness=0.7),  # 11 socket
    ]
    PLINTH, BODY, FIN, PANEL, DOME, FRONT, BRIGHT, GUN, EYE, CORE, RIM, SOCK = range(12)
    M = Mesh()

    # Plinth (rows 17-22) under the blocks and the gun.
    hull(M, cbox(2.1, 21.0, 16.0, 22.4, 0.0, 1.2, 0.4), PLINTH)
    # Armoured blocks either side of the cannon (rows 17-21), their front edges bevelled.
    for x0, x1 in ((2.4, 10.2), (14.4, 20.9)):
        hull(M, cbox(x0, x1, 17.2, 21.2, 0.0, 3.0, 0.7, chz=0.9), FIN)
        hull(M, cbox(x0 + 0.5, x1 - 0.5, 20.0, 21.25, 0.0, 2.3, 0.35), FRONT)
        hull(M, cbox(x0 + 1.2, x1 - 1.2, 17.8, 19.4, 2.6, 3.25, 0.2), PANEL)

    # Housing at the back (rows 2-11): a block, its top corners cut, with fins along it.
    out = [(5.0, 2.1), (18.2, 2.1), (20.0, 3.8), (20.0, 10.6), (2.3, 10.6), (2.3, 4.6)]
    prism(M, out, 0.0, 4.4, BODY, ch=0.7)
    for x0, x1, h, m in ((3.0, 5.7, 4.9, PANEL), (5.8, 7.0, 5.6, BRIGHT), (7.9, 9.0, 5.3, FIN),
                         (13.8, 14.8, 5.3, FIN), (15.8, 16.9, 5.4, FIN)):
        y0 = 2.6 if x0 > 3.5 else 3.6
        hull(M, cbox(x0, x1, y0, 10.4, 3.5, h, 0.3), m)
    # sensor box on top (columns 10-12, rows 2-6) with a bright lip
    hull(M, cbox(9.8, 13.2, 2.2, 6.6, 3.5, 6.0, 0.35), PANEL)
    hull(M, cbox(10.0, 13.0, 2.0, 2.9, 5.2, 6.25, 0.25), BRIGHT)
    # The eye: a hooded socket at the housing's front, a red lens glowing in it.
    hull(M, cbox(9.6, 13.4, 6.6, 11.6, 0.6, 4.9, 0.4), SOCK)
    ellipsoid(M, 11.5, 9.4, 4.4, 1.65, 2.3, 0.75, RIM, seg=16, rings=8)
    ellipsoid(M, 11.5, 9.3, 4.6, 1.3, 1.9, 0.75, EYE, seg=16, rings=8)
    ellipsoid(M, 11.5, 8.6, 4.95, 0.75, 0.85, 0.5, CORE, seg=12, rings=6)

    # Turret dome (columns 2-20, rows 10-18) on a collar ring.
    blob(M, ell(11.4, 14.3, 8.6, 3.9, n=56), (11.0, 13.6), 4.6, DOME, zb=0.0, p=2.0, n=56, rings=11)
    sweep(M, [(11.4 + 8.45 * math.cos(a), 14.3 + 3.8 * math.sin(a), 0.9, 0.4, 0.7)
              for a in [2 * math.pi * k / 40 for k in range(41)]], FIN, sides=6, cap0=False, cap1=False)

    # The cannon: a mantlet out of the dome's front, the barrel down the screen, a muzzle sleeve.
    ellipsoid(M, 12.5, 16.6, 2.4, 2.3, 1.8, 2.0, FIN, seg=16, rings=8)
    sweep(M, [(12.5, 16.0, 2.5, 0.0, 0.0), (12.5, 16.2, 2.5, 1.35, 1.35), (12.5, 21.4, 2.5, 1.35, 1.35),
              (12.5, 21.5, 2.5, 0.0, 0.0)], GUN, sides=12)
    sweep(M, [(12.5, 20.6, 2.5, 0.0, 0.0), (12.5, 20.8, 2.5, 1.65, 1.65), (12.5, 22.9, 2.5, 1.65, 1.65),
              (12.5, 23.1, 2.5, 1.1, 1.1), (12.5, 23.15, 2.5, 0.0, 0.0)], PANEL, sides=12)
    obj = M.to_object("newsh-caret-45", mats, coll, ox=12.0)
    return obj


# --- pieces, shells, export ----------------------------------------------------------------------

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


def build_all():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection("assembly-newsh-caret-45")
    crab = build_crab(coll)
    emp = build_emplacement(coll)
    bpy.context.view_layer.update()
    crab_shell = common.outline_shell(crab, coll, voxel=0.012, faces=5000, islands="outer")
    emp_shell = common.outline_shell(emp, coll, voxel=0.01, faces=2500, islands="outer")
    assert len(emp_shell.data.polygons) > 0
    pieces = common.split_assembly(crab, LAYOUT, coll)
    shells = cut_open(crab_shell, LAYOUT, coll)
    for name, _, _ in LAYOUT:
        assert len(shells[name].data.polygons) > 0, f"{name}: empty outline shell"
    return crab, crab_shell, emp, emp_shell, pieces, shells


def export_emplacement(emp, emp_shell):
    data = common.load_sprite(WT, "newsh-caret-45")
    common.export_sprite_model(WT, [emp, emp_shell], "enemies/newsh-caret-45", data["sprites"])


def design_glb(path, crab, crab_shell, emp, emp_shell, pieces, shells):
    """Review output only: the whole crab, each piece at its place, and the emplacement."""
    objs = []
    for name, cx, cy in LAYOUT:
        for o in (pieces[name], shells[name]):
            o["design_model"] = name
            o.location.x += cx / 12
            o.location.y += -cy / 12
            objs.append(o)
    crab["design_model"] = "whole"
    crab_shell["design_model"] = "whole"
    emp["design_model"] = "newsh-caret-45"
    emp_shell["design_model"] = "newsh-caret-45"
    common.export_glb([crab, crab_shell, emp, emp_shell] + objs, Path(path))


def main():
    crab, crab_shell, emp, emp_shell, pieces, shells = build_all()
    for name, _, _ in LAYOUT:
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"])
    if arg("--design"):
        design_glb(arg("--design"), crab, crab_shell, emp, emp_shell, pieces, shells)


if __name__ == "__main__":
    main()
