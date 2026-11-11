"""Design B for tyrbld_purple_orb (TYRIAN's purple orb machine, map 1-9, layer 2; tiles
155 156 157 / 165 149 167 / 175 176 177). Hard surface (D65, D141), silhouette first: the outline
is the art's (eight round bosses round a square carved block), and every form is a big, clearly
stepped prism so it reads from the small tilted game camera; detail second.

Build: tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/tyrbld_purple_orb.py
(or blender --background --factory-startup --python <this> -- [--no-bake] [--preview <dir>/x.png]).
"bake": "model" in assets/blender/textures/shapesz-tyrbld-purple-orb/maps.json: AO/roughness bake only.
No D51 outline shell: tile models draw no ink outline (structureInstances.ts turns it off, tiles join
edge to edge, D8), so a shell would only add an instanced draw and a shadow caster (D141).

Stack (z, model units; 0 = island rock top; every cell carries a top enemy, so all <= 0.32):
  plinth 87          -0.04 .. 0.06   the cast base under the block (chamfered octagon)
  boss skirts 87     -0.03 .. 0.085  round (16-gon) mounting collars under the D115 broken sockets
  broken sockets      0.00 .. 0.30   Structure.broken_sockets(0.0) (lib_sockets, D115, unchanged)
  plate 88            0.05 .. 0.15   the carved plate, corners cut under the bosses; its top is
                                     the floor of the groove cross and of the frame
  panels 88 (87 bev)  0.14 .. 0.205  four raised quarter panels, groove cross through the orb;
                     .. 0.217        raised fields on them, cut by the carved ring (r 13.6-15.5)
  tablets 90          0.19 .. 0.235  light tablets on the cross's four arms by the collar, bolts 102
  collar 88 (87)      0.14 .. 0.25   stepped stone ring round the well (r 8.8-12.6), cut for the port
  well floor 84       0.13 .. 0.226  a 1.4 px band round the bezel
  bezel 102           0.15 .. 0.22   steel ring holding the orb, 8 studs 103
  orb 51              0.15 .. 0.315  blue glass lens (art median 51), satin, glow 4.2 (in-game ~ the art)
  capsules 52         0.225 .. 0.30  blue capsule lights (glow 3.4) in steel cradles 102 (art "\" and "/")
  port 82             0.14 .. 0.232  rounded-square recess below the orb (art 80-82, x 34-37, y 46-50)
  port frame 88       0.14 .. 0.262  posts and bottom bar round it, 0.012 over the collar

"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402

# ---- Layout (pattern px, 72 x 84, origin top-left, y down), measured on the art -----------------
ORB = (36.4, 39.6)  # blue component centre (x 30-42, y 34-44)
ORB_R = 6.2
BEZEL_R = (6.0, 7.4)  # steel ring: art 99-103 at x 29 and 43
WELL_R = 8.8  # art: only a 1-2 px darker band (80-84) round the bezel, mostly shading
COLLAR_R = (8.8, 12.6)
CARVED_R = (13.6, 15.5)  # the art's carved ring round the orb: a groove through the panels' fields
PLINTH = (12.6, 10.8, 61.6, 66.8)
PLINTH_CUT = 6.0
PLATE = (13.6, 11.6, 60.4, 65.8)
PLATE_CUT = 7.5
PANEL_BOX = (16.6, 15.6, 57.0, 62.2)
PANEL_CUT = 4.5
GROOVE = 0.9  # half width of the groove cross (px)
# Boss skirts (cx, cy, r): fitted to the art's boss outlines (see fit in notes).
SKIRTS = {
    155: (11.9, 12.3, 9.1), 156: (36.0, 12.6, 9.0), 157: (60.1, 12.9, 9.1),
    165: (10.9, 40.0, 8.2), 167: (60.1, 41.6, 9.85),
    175: (12.4, 67.7, 9.0), 176: (36.0, 69.2, 9.1), 177: (60.0, 69.4, 9.2),
}
# Light tablets on the groove cross's arms (x0, y0, x1, y1): N and S pairs either side of the
# vertical groove (art 90 blocks x 29-35 / 37-40, y 20-28 and x 29-35, y 54-59), W and E pairs
# either side of the horizontal groove (art 90 at x 21-24, y 33-38 / 40-44 and x 47-50, y 33-38).
TABLETS = [
    (29.6, 20.4, 35.1, 28.6), (37.7, 20.4, 43.2, 28.6),
    (29.6, 51.2, 35.1, 59.2), (37.7, 51.2, 43.2, 59.2),
    (20.6, 32.4, 25.2, 38.3), (20.6, 40.9, 25.2, 46.8),
    (47.6, 32.4, 52.2, 38.3), (47.6, 40.9, 52.2, 46.8),
]
CAPSULES = [((28.2, 47.0), 42.7, 9.0, 1.7), ((44.1, 47.4), -43.8, 9.0, 1.7)]  # centre, angle (deg, screen), length, r
PORT = (34.1, 46.1, 37.9, 50.9)  # dark square recess (art 80-82 at x 34-37, y 46-50), set in purple
PORT_FRAME = 0.8  # purple 88 frame round it, open at the top where it meets the bezel

Z_PLINTH = (-0.04, 0.06)
Z_SKIRT = (-0.03, 0.085)
Z_PLATE = (0.05, 0.15)
Z_PANEL = (0.14, 0.205)
Z_TABLET = (0.19, 0.235)
Z_COLLAR = (0.14, 0.25)
Z_WELL = (0.13, 0.226)  # dark disk inside the collar, above the panels' fields (0.217)
Z_BEZEL = (0.20, 0.258)
Z_ORB = (0.15, 0.315)
Z_CAPS = (0.225, 0.30)

# Palette indices: the art's own per region (trimmed medians; see notes).
I_PLINTH, I_BODY, I_EDGE, I_LIGHT = 87, 88, 87, 90
I_WELL, I_PORT, I_STEEL, I_STUD = 84, 82, 102, 103
I_ORB, I_CAPS = 51, 52


def own_mask(s):
    """The art's mask of the model's own parts: purple stone plus the blue orb/capsules, holes filled."""
    m = s.purple_mask() | (s.footprint & s.ramp_mask(3))
    m = lb.close(m, 1)
    # Fill holes: background = the ~m parts that touch the border.
    bg = np.zeros_like(m)
    for ys, xs in lt.components(~m):
        if ys.min() == 0 or xs.min() == 0 or ys.max() == m.shape[0] - 1 or xs.max() == m.shape[1] - 1:
            bg[ys, xs] = True
    return ~bg


def octagon(x0, y0, x1, y1, cut):
    return [(x0 + cut, y0), (x1 - cut, y0), (x1, y0 + cut), (x1, y1 - cut), (x1 - cut, y1), (x0 + cut, y1), (x0, y1 - cut), (x0, y0 + cut)]


def clip_poly(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman clip of a polygon to a box."""
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia:
                    out.append(inter(a, b))
                out.append(b)
            elif ia:
                out.append(inter(a, b))
        return out

    def ix(xc):
        return lambda a, b: (xc, a[1] + (b[1] - a[1]) * (xc - a[0]) / (b[0] - a[0]))

    def iy(yc):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yc - a[1]) / (b[1] - a[1]), yc)

    pts = list(poly)
    pts = clip(pts, lambda p: p[0] >= x0, ix(x0))
    pts = clip(pts, lambda p: p[0] <= x1, ix(x1))
    pts = clip(pts, lambda p: p[1] >= y0, iy(y0))
    pts = clip(pts, lambda p: p[1] <= y1, iy(y1))
    return pts


def ring(s, px, py, r_out, r_in, z0, z1, mat, sides=32, chamfer_px=0.5, drop=0.02, bevel_mat=None, inner_mat=None):
    """A closed annulus (pattern px radii) from z0 to z1, its top edges chamfered: a stepped ring."""
    c = chamfer_px if drop else 0.0
    prof = [(r_in, z0), (r_out, z0), (r_out, z1 - drop), (r_out - c, z1), (r_in + c, z1), (r_in, z1 - drop)]
    mats = [mat, mat, bevel_mat if bevel_mat is not None else mat, mat, bevel_mat if bevel_mat is not None else mat,
            inner_mat if inner_mat is not None else mat]
    bm = bmesh.new()
    cx, cy = s.x(px), s.y(py)
    rings = []
    for r, z in prof:
        rr = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            rr.append(bm.verts.new((cx + r * lt.PX * math.cos(a), cy + r * lt.PX * math.sin(a), z)))
        rings.append(rr)
    n = len(prof)
    for k in range(n):
        a_, b_ = rings[k], rings[(k + 1) % n]
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((a_[i], a_[j], b_[j], b_[i])).material_index = mats[k]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def clip_convex(poly, clipper):
    """Sutherland-Hodgman clip of `poly` to the convex polygon `clipper` (pattern px, any winding)."""
    area = sum(clipper[i - 1][0] * clipper[i][1] - clipper[i][0] * clipper[i - 1][1] for i in range(len(clipper)))
    sgn = 1.0 if area > 0 else -1.0
    out = list(poly)
    for i in range(len(clipper)):
        (ax, ay), (bx, by) = clipper[i - 1], clipper[i]

        def side(p):
            return sgn * ((bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax))

        pts, out = out, []
        for k in range(len(pts)):
            p, q = pts[k - 1], pts[k]
            sp, sq = side(p), side(q)
            if sq >= 0:
                if sp < 0:
                    u = sp / (sp - sq)
                    out.append((p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u))
                out.append(q)
            elif sp >= 0:
                u = sp / (sp - sq)
                out.append((p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u))
        if not out:
            break
    return out


def minus_disk(poly, cx, cy, r, step=0.35):
    """A convex polygon (pattern px) minus the disk (cx, cy, r), for a polygon star-shaped from the
    centre whose near side faces it (a quarter panel of the groove cross): the boundary is sampled
    densely and every sample inside the disk is pushed out radially onto the circle (an arc)."""
    pts = []
    n = len(poly)
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        k = max(1, int(math.hypot(bx - ax, by - ay) / step))
        for j in range(k):
            u = j / k
            pts.append((ax + (bx - ax) * u, ay + (by - ay) * u))
    out = []
    for x, y in pts:
        d = math.hypot(x - cx, y - cy)
        if d < r:
            x, y = cx + (x - cx) * r / d, cy + (y - cy) * r / d
        if not out or math.hypot(x - out[-1][0], y - out[-1][1]) > 0.05:
            out.append((x, y))
    # drop collinear runs along the straight edges (keeps the face count down)
    keep = []
    for i, p in enumerate(out):
        a, b = out[i - 1], out[(i + 1) % len(out)]
        cross = (p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0])
        if abs(cross) > 1e-4:
            keep.append(p)
    return keep


def collar_with_gap(s, px, py, r_out, r_in, z0, z1, mat, gap, sides=40, **kw):
    """ring() with the part between the screen columns gap = (x0, x1) below the centre cut away
    (bisected, no caps: the port's frame closes the cut)."""
    saved, bm = s.parts, bmesh.new()
    s.parts = bm  # build the ring alone (Building._merge appends to self.parts, a bmesh)
    try:
        ring(s, px, py, r_out, r_in, z0, z1, mat, sides=sides, **kw)
    finally:
        s.parts = saved
    gx0, gx1 = s.x(gap[0]), s.x(gap[1])
    for gx in (gx0, gx1):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(gx, 0, 0), plane_no=(1, 0, 0))
    cy = s.y(py)
    dead = [f for f in bm.faces if gx0 < f.calc_center_median().x < gx1 and f.calc_center_median().y < cy]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    s._merge(bm)


def capsule(s, px, py, angle_deg, length, r, z0, z1, mat):
    """A glowing pill lying on the deck along `angle_deg` (screen, y down): a stretched UV sphere,
    flattened to fit between z0 and z1."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1.0)
    half = length / 2 * lt.PX
    rad = r * lt.PX
    hz = (z1 - z0) / 2
    for v in bm.verts:
        x, y, z = v.co
        # capsule: cylinder middle by pushing the hemispheres apart
        sx = x * rad + (half - rad) * (1 if x > 0 else -1 if x < 0 else 0)
        v.co = Vector((sx, y * rad, z * hz))
    a = -math.radians(angle_deg)  # screen y down -> Blender y up
    rot = Matrix.Rotation(a, 4, "Z")
    bmesh.ops.transform(bm, matrix=Matrix.Translation((s.x(px), s.y(py), z0 + hz)) @ rot, verts=bm.verts)
    for f in bm.faces:
        f.material_index = mat
        f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm, smooth=True)


def rot_box(cx, cy, length, width, angle_deg, corner=0.8):
    """A rounded box (pattern px) centred at (cx, cy), long axis along angle_deg (screen)."""
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    hx, hy = length / 2, width / 2
    pts = []
    for qx, qy, a0 in ((hx - corner, -hy + corner, -90), (hx - corner, hy - corner, 0), (-hx + corner, hy - corner, 90), (-hx + corner, -hy + corner, 180)):
        for k in range(3):
            t = math.radians(a0 + 45 * k)
            x, y = qx + corner * math.cos(t), qy + corner * math.sin(t)
            pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return pts


def build(bake=True, preview=None):
    s = tb.Structure("purple-orb")
    own = own_mask(s)
    plinth = s.m(I_PLINTH, roughness=0.7)
    body = s.m(I_BODY, roughness=0.55)
    edge = s.m(I_EDGE, roughness=0.6)
    light = s.m(I_LIGHT, roughness=0.45)
    well = s.m(I_WELL, roughness=0.85)
    port = s.m(I_PORT, roughness=0.9)
    steel = s.m(I_STEEL, roughness=0.35, metallic=0.7)
    stud = s.m(I_STUD, roughness=0.3, metallic=0.75)
    # Glass at roughness 0.12 mirrored the dark sky and read near-black in the game (fix round 1):
    # satin glass, a stronger glow, so the in-game median comes near the art's mid blue.
    orb = s.m(I_ORB, roughness=0.4, emission_strength=4.2)
    caps = s.m(I_CAPS, roughness=0.35, emission_strength=3.4)

    # --- Silhouette: the cast plinth, then a round skirt under each boss.
    s.slab(octagon(*PLINTH, PLINTH_CUT), *Z_PLINTH, plinth, chamfer_px=1.2, drop=0.025)
    for t, (cx, cy, r) in SKIRTS.items():
        s.slab(s.ngon(cx, cy, r, 20), *Z_SKIRT, plinth, chamfer_px=0.9, drop=0.025, bevel_mat=edge)

    # --- The carved plate and its four raised panels, split by the groove cross through the orb.
    s.slab(octagon(*PLATE, PLATE_CUT), *Z_PLATE, body, chamfer_px=1.6, drop=0.03, bevel_mat=edge)
    pb = octagon(*PANEL_BOX, PANEL_CUT)
    ox, oy = ORB
    x0, y0, x1, y1 = PANEL_BOX
    for qx0, qx1 in ((x0, ox - GROOVE), (ox + GROOVE, x1)):
        for qy0, qy1 in ((y0, oy - GROOVE), (oy + GROOVE, y1)):
            q = clip_poly(pb, qx0, qy0, qx1, qy1)
            # round the inner corner (at the collar) a little
            s.slab(q, *Z_PANEL, body, chamfer_px=1.1, drop=0.025, bevel_mat=edge)
            # Panel line: a raised inner field inset 2 px, so each quarter reads as a framed plate.
            # The field is cut by the art's carved ring round the orb (CARVED_R): an outer field and
            # a thin inner one by the collar, the groove between them at the panel's own top.
            iq = clip_poly(octagon(x0 + 2.2, y0 + 2.2, x1 - 2.2, y1 - 2.2, PANEL_CUT - 0.8), qx0 + 1.6, qy0 + 1.6, qx1 - 1.6, qy1 - 1.6)
            outer = minus_disk(iq, ox, oy, CARVED_R[1], step=1.0)
            s.slab(outer, Z_PANEL[1] - 0.01, Z_PANEL[1] + 0.012, body, chamfer_px=0.6, drop=0.01)
            inner = clip_convex(iq, s.ngon(ox, oy, CARVED_R[0], 48))
            if len(inner) >= 3:
                s.slab(inner, Z_PANEL[1] - 0.01, Z_PANEL[1] + 0.012, body, chamfer_px=0.4, drop=0.008)

    # --- Light tablets on the cross's arms, each two bolts.
    for tx0, ty0, tx1, ty1 in TABLETS:
        s.slab(s.rounded_box(tx0, ty0, tx1, ty1, 1.0), *Z_TABLET, light, chamfer_px=0.7, drop=0.015, bevel_mat=body)
        vertical = (ty1 - ty0) > (tx1 - tx0)
        if vertical:
            pts = [((tx0 + tx1) / 2, ty0 + 1.4), ((tx0 + tx1) / 2, ty1 - 1.4)]
        else:
            pts = [(tx0 + 1.4, (ty0 + ty1) / 2), (tx1 - 1.4, (ty0 + ty1) / 2)]
        s.bolts(pts, Z_TABLET[1], r_px=0.6, height=0.012, mat=steel)

    # --- The collar round the well: a stepped stone ring, the well's dark floor inside.
    # The collar is cut where the port sits (the port's frame closes the cut).
    px0, py0, px1, py1 = PORT
    fx0, fx1 = px0 - PORT_FRAME, px1 + PORT_FRAME
    collar_with_gap(s, ox, oy, COLLAR_R[1], COLLAR_R[0], *Z_COLLAR, body, (fx0 + 0.05, fx1 - 0.05), sides=40,
                    chamfer_px=0.8, drop=0.03, bevel_mat=edge, inner_mat=edge)
    s.slab(s.ngon(ox, oy, WELL_R + 0.1, 40), *Z_WELL, well, chamfer_px=0)
    # --- Steel bezel with eight studs, the orb in it.
    ring(s, ox, oy, BEZEL_R[1], BEZEL_R[0], *Z_BEZEL, steel, sides=32, chamfer_px=0.4, drop=0.015)
    studs = [(ox + 6.7 * math.cos(math.radians(22.5 + 45 * k)), oy + 6.7 * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    s.bolts(studs, Z_BEZEL[1], r_px=0.45, height=0.01, mat=stud)
    s.dome(ox, oy, ORB_R, ORB_R, Z_ORB[0], Z_ORB[1] - Z_ORB[0], orb, sides=32, rings=7)

    # --- The port below the orb: a rounded-square dark recess in a purple frame (no steel: the
    # art's port is 80-82 set straight in 88/90). The frame stands 0.012 over the collar it cuts and
    # is open at the top, where the port runs in under the bezel; the floor sits 0.018 under the
    # collar's top, a real recess.
    fy1 = oy + COLLAR_R[1] + 0.3  # the frame runs out past the collar's outer edge
    ft = py0 + 0.4  # the frame's posts start clear of the bezel (r 7.4 + 0.2)
    z_frame = Z_COLLAR[1] + 0.012
    for bx0, bx1 in ((fx0, px0), (px1, fx1)):  # the two posts
        s.slab(s.rounded_box(bx0, ft, bx1, fy1, 0.3, 1), Z_PANEL[0], z_frame, body, chamfer_px=0.25, drop=0.006, bevel_mat=edge)
    s.slab(s.rounded_box(px0 - 0.05, py1, px1 + 0.05, fy1, 0.3, 1), Z_PANEL[0], z_frame - 0.006, body,
           chamfer_px=0.3, drop=0.006, bevel_mat=edge)  # the bottom bar between them, a step lower
    s.slab(s.rounded_box(px0, py0 - 0.6, px1, py1 + 0.05, 0.7), Z_PANEL[0], Z_COLLAR[1] - 0.018, port, chamfer_px=0)

    # --- Capsule lights in steel cradles, either side of the port.
    for (cx, cy), ang, ln, r in CAPSULES:
        s.slab(rot_box(cx, cy, ln + 0.7, 2 * r + 0.7, ang, 1.0), Z_PANEL[0], Z_COLLAR[1] + 0.012, steel, chamfer_px=0.4, drop=0.01)
        capsule(s, cx, cy, ang, ln, r, Z_CAPS[0], Z_CAPS[1], caps)

    # --- The bosses: the broken sockets the tiles paint under the caps (D115, unchanged).
    s.broken_sockets(0.0)

    # --- The island's rock round it (plain: the bake leaves it alone).
    s.rock(exclude=lb.erode(own, 3))

    objects = s.objects()
    s.check(objects)
    s.top_iou(objects, own)
    if bake:
        objects = s.bake_model(objects)
    if preview:
        lt.preview(s.ts, objects, s.pattern, Path(preview) / f"{tb.SHAPES}-tyrbld-purple-orb.png", view_px=480)
    s.export(objects, baked=bake)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, preview=lt.preview_arg())
