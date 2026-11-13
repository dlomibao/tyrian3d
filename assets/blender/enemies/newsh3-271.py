"""Ringed turret (newsh3.shp frame 271), hard-surface rebuild (design A).

What it is: a fixed gun emplacement (e4:416, armour 255) that the level slides sideways a few px
per tick (ev55), on the ground or sky layer: a ball turret hung in an open gimbal ring on a
carriage that runs on a rail. Not a craft.

Reading the 24x28 sprite (palette indices; the 1 px ink ring and the shading are lighting):
  - the RING: an annulus (outer edge cols 6-18 at rows 6-8, inner edge ~cols 7-17, bottom at
    row 17) standing open in the middle: rows 10-16 show the ground through, so the model has a
    real hole there. Its inner lip draws light grey (10) on the lit side: a chamfer catching
    light, not paint. Colour: the ring's median, 106 (blue-grey).
  - the DOME: a glossy blue ball (median 53; the 62 glint at row 10 is sheen) seated in the
    ring's upper half (cols 9-15, rows 7-13), held by the ring's front deck and two trunnion
    bosses at its upper sides (the dark gaps at rows 8-9 are the shadow under them).
  - the BARREL: cols 10-14, rows 2-5, pointing up the screen (forward): a grey shroud (4) with
    two blue ribs (cols 11 and 13: 59), a muzzle brake at row 3 (the dark cols 9 and 15) and a
    light collar (row 5: 10) where it passes over the ring into the ball.
  - the ARMS: grey outrigger pylons (left lit 6, right shaded 4: lighting; one material, the lit 6) reaching out
    to the screen edges at rows 7-12 and running down to the bar; each carries a blue pin (a
    short missile, 55) pointing forward at cols 3 and 21, rows 3-8.
  - the BAR: rows 18-19, cols 3-21: a beam (106) with a light rail (10) along its top: the rail
    the turret slides on.
  - the CARRIAGE: rows 20-25, a tapered grey housing (5) with a blue power block (56) between
    grey cheeks, a pod (51) at each upper corner.
Symmetric about x = 12.5 (the sprite's left/right only differ in lighting).

Underside: plain closed bottoms (flat), no detail.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newsh3-271.py
(or blender --background --python assets/blender/enemies/newsh3-271.py [-- --preview out.png]).
Design review outputs only with --out X.glb / --game DIR.
"""

import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import lib_b076 as lib  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newsh3-271"
U = 1 / 12          # one sprite px in Blender units
W, H = 24, 28
CX = 12.5           # the sprite's mirror line (pixel-edge column)

# (key, palette index, metallic, roughness, specular IOR level)
MATS = [
    ("ring", 106, 0.75, 0.38, 0.5),
    ("arm", 6, 0.75, 0.42, 0.5),
    ("rail", 10, 0.85, 0.28, 0.6),
    ("dome", 53, 0.35, 0.16, 0.7),
    ("block", 56, 0.4, 0.3, 0.6),
    ("pod", 51, 0.4, 0.3, 0.6),
    ("pin", 55, 0.4, 0.28, 0.6),
    ("rib", 59, 0.4, 0.3, 0.6),
    ("barrel", 4, 0.8, 0.35, 0.5),
]
RING, ARM, RAIL, DOME, BLOCK, POD, PIN, RIB, BARREL = range(len(MATS))

# Heights (px)
Z_RING = 2.9
Z_ARM = 2.2
Z_DECK = 2.35
Z_HOUSE = 2.0
Z_BLOCK = 2.7
DOME_C = (12.5, 10.6)
DOME_R = 3.65
DOME_ZC = 2.4
DOME_RZ = 3.0
BARREL_ZC = 3.0


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


# --- geometry in sprite px: x = column edge - 12, y = 14 - row edge, z up ------------------------

def P(c, r, z=0.0):
    return Vector((c - 12.0, 14.0 - r, z))


def mirror_loop(pts):
    """Left half points (c, r) top to bottom -> the right half mirrored, a closed loop."""
    return pts + [(2 * CX - c, r) for c, r in reversed(pts)]


def chaikin(pts, n=2, closed=True):
    for _ in range(n):
        out = []
        m = len(pts)
        for i in range(m if closed else m - 1):
            a, b = pts[i], pts[(i + 1) % m]
            out += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]),
                    (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        pts = out
    return pts


def area2(pts):
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts)))


def inset(pts, d):
    """Offset a closed loop (c, r) inward by d px (miter, clamped)."""
    m = len(pts)
    s = 1.0 if area2(pts) > 0 else -1.0  # orientation in (c, r) space
    out = []
    for i in range(m):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % m]
        n1 = Vector((-(b[1] - a[1]), b[0] - a[0])).normalized() * s
        n2 = Vector((-(c[1] - b[1]), c[0] - b[0])).normalized() * s
        n = (n1 + n2)
        if n.length < 1e-6:
            n = n1
        n.normalize()
        k = 1.0 / max(0.5, n.dot(n1))
        out.append((b[0] + n.x * d * k, b[1] + n.y * d * k))
    return out


def ring_verts(bm, loop, z):
    return [bm.verts.new(P(c, r, z)) for c, r in loop]


def bridge(bm, a, b, mat, smooth=False):
    m = len(a)
    for i in range(m):
        j = (i + 1) % m
        f = bm.faces.new((a[i], a[j], b[j], b[i]))
        f.material_index = mat
        f.smooth = smooth


def cap(bm, ring, mat, flip=False):
    f = bm.faces.new(list(reversed(ring)) if flip else ring)
    f.material_index = mat
    return f


def slab(bm, loop, z0, z1, ch, mat, top_mat=None, ch_bottom=0.0, smooth=False):
    """A chamfered extrusion of a closed plan loop (c, r) from z0 to z1."""
    rings = []
    if ch_bottom > 0:
        rings.append((inset(loop, ch_bottom), z0))
        rings.append((loop, z0 + ch_bottom))
    else:
        rings.append((loop, z0))
    rings.append((loop, z1 - ch))
    rings.append((inset(loop, ch), z1))
    vs = [ring_verts(bm, lp, z) for lp, z in rings]
    for a, b in zip(vs, vs[1:]):
        bridge(bm, a, b, mat, smooth)
    cap(bm, vs[0], mat)
    cap(bm, vs[-1], mat if top_mat is None else top_mat)
    return vs


def ellipse_pts(cx, cy, a, b, n, e=2.0, a0=0.0):
    out = []
    for i in range(n):
        t = a0 + 2 * math.pi * i / n
        ct, st = math.cos(t), math.sin(t)
        out.append((cx + a * math.copysign(abs(ct) ** (2 / e), ct), cy + b * math.copysign(abs(st) ** (2 / e), st)))
    return out


def annulus(bm, outer, inner, profile, mat, smooth=True, mats=None):
    """A ring between an outer and an inner loop (same count, matched by index). profile: list of
    (side, inset px toward the other side, z) going round the section; consecutive points are
    bridged and the last joins the first."""
    rings = []
    for side, d, z in profile:
        lp = []
        for po, pi in zip(outer, inner):
            a, b = (po, pi) if side == "o" else (pi, po)
            v = Vector((b[0] - a[0], b[1] - a[1]))
            v.normalize()
            lp.append((a[0] + v.x * d, a[1] + v.y * d))
        rings.append(ring_verts(bm, lp, z))
    for k in range(len(rings)):
        a, b = rings[k], rings[(k + 1) % len(rings)]
        bridge(bm, a, b, mats[k] if mats else mat, smooth)


def faces_of(verts):
    return list({f for v in verts for f in v.link_faces})


def ellipsoid(bm, c, r, z, radii, mat, seg=32, rings=16, zmin=None):
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    vs = res["verts"]
    for v in vs:
        x, y, zz = v.co
        if zmin is not None:
            zz = max(zz, zmin)
        v.co = P(c, r, z) + Vector((x * radii[0], y * radii[1], zz * radii[2]))
    for f in faces_of(vs):
        f.material_index = mat
        f.smooth = True
    return vs


def cylinder_y(bm, c, z, r0, r1, rad, mat, seg=24, smooth=True, caps=True, rad1=None):
    """A cylinder along the screen's vertical (rows r0 -> r1) at column c, height z."""
    res = bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=rad,
                                radius2=rad if rad1 is None else rad1, depth=1.0)
    vs = res["verts"]
    for v in vs:
        x, y, zz = v.co  # along z, from -0.5 to 0.5
        t = zz + 0.5
        rr = r1 + (r0 - r1) * t  # +z end -> r0 (front/top of screen)
        v.co = P(c, rr, z) + Vector((x, 0.0, y))
    for f in faces_of(vs):
        f.material_index = mat
        f.smooth = smooth
    return vs


def cylinder_x(bm, c0, c1, r, z, rad, mat, seg=20, smooth=True):
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=rad, radius2=rad, depth=1.0)
    vs = res["verts"]
    for v in vs:
        x, y, zz = v.co
        cc = c0 + (c1 - c0) * (zz + 0.5)
        v.co = P(cc, r, z) + Vector((0.0, x, y))
    for f in faces_of(vs):
        f.material_index = mat
        f.smooth = smooth
    return vs


def chamfer_box(bm, c0, c1, r0, r1, z0, z1, ch, mat, chz=None):
    """A box with chamfered edges via usp_talon.cbox + a convex hull, in sprite px."""
    pts = [tuple(P(x, y, z)) for x, y, z in
           [(p[0], p[1], p[2]) for p in T.cbox(c0, c1, r0, r1, z0, z1, ch, chz)]]
    part = T.Part("tmp")
    part.bm = bm
    before = set(bm.faces)
    T.hull(part, pts, mat)
    new = [f for f in bm.faces if f not in before]
    for f in new:
        f.smooth = False
    return new


# --- the parts ------------------------------------------------------------------------------------

RING_O = (12.5, 12.0, 7.35, 7.35, 2.0)     # centre col, row, half width, half height, exponent
RING_I = (12.5, 12.1, 6.45, 5.95, 3.0)
NSEG = 72


def build_ring(bm):
    oc, orr, oa, ob, oe = RING_O
    ic, irr, ia, ib, ie = RING_I
    # Start at the bottom so the loops pair up radially.
    outer = ellipse_pts(oc, orr, oa, ob, NSEG, oe, a0=math.pi / 2)
    inner = ellipse_pts(ic, irr, ia, ib, NSEG, ie, a0=math.pi / 2)
    # A faired hoop: straight walls, a rounded crown (half-round over the ~1 px width).
    wid = 1.0
    prof = [("o", 0.0, 0.0), ("o", 0.0, Z_RING - 0.55)]
    for k in range(1, 4):
        t = math.pi / 2 * k / 4
        prof.append(("o", 0.5 * wid * (1 - math.cos(t)) * 0.9, Z_RING - 0.55 + 0.55 * math.sin(t)))
    for k in range(3, 0, -1):
        t = math.pi / 2 * k / 4
        prof.append(("i", 0.5 * wid * (1 - math.cos(t)) * 0.9, Z_RING - 0.55 + 0.55 * math.sin(t)))
    prof += [("i", 0.0, Z_RING - 0.55), ("i", 0.0, 0.0)]
    annulus(bm, outer, inner, prof, RING, smooth=True)
    # Bolt bosses round the ring top at 8 o'clock, 4 o'clock, 7 and 5 (where the camera sees).
    for deg in (200, 230, 310, 340):
        t = math.radians(deg)
        rmid = 0.5 * (oa + ia)
        c = oc + rmid * math.cos(t)
        r = 12.1 - rmid * math.sin(t)
        cylinder_y_up(bm, c, r, Z_RING - 0.05, 0.42, 0.18, RAIL)


def cylinder_y_up(bm, c, r, z, rad, h, mat, seg=10):
    """A short vertical boss (a bolt head) on a surface at height z."""
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=rad,
                                radius2=rad * 0.8, depth=h)
    for v in res["verts"]:
        v.co = P(c, r, z + h / 2) + Vector((v.co.x, v.co.y, v.co.z))
    for f in faces_of(res["verts"]):
        f.material_index = mat
        f.smooth = False


def build_deck(bm):
    """The ring's front deck the ball sits in, and the two trunnion bosses holding it."""
    ic, irr, ia, ib, ie = RING_I
    # Deck: the ring's inner curve above row 9.6, closed by a straight edge (under the ball in the
    # middle; only its ends show, between the ring and the ball).
    cut = 9.4
    pts = [p for p in ellipse_pts(ic, irr, ia + 0.3, ib + 0.3, 96, ie) if p[1] < cut]
    pts.sort(key=lambda p: math.atan2(p[1] - irr, p[0] - ic))
    left = min(pts, key=lambda p: p[0])
    right = max(pts, key=lambda p: p[0])
    loop = [(right[0] - 0.1, cut)] + pts + [(left[0] + 0.1, cut)]
    loop = chaikin(loop, 1)
    slab(bm, loop, 0.0, Z_DECK, 0.3, RING)
    # Trunnion bosses: short horizontal pivots on the ball's upper sides, ring to ball.
    for c0, c1 in ((7.7, 10.2), (14.8, 17.3)):
        cylinder_x(bm, c0, c1, 8.75, Z_DECK + 0.25, 0.85, RING, seg=16)
        # a pivot cap facing the ball
        cc = c1 - 0.25 if c0 < 12 else c0 + 0.25
        cylinder_x(bm, cc - 0.25, cc + 0.25, 8.75, Z_DECK + 0.25, 0.55, RAIL, seg=12)


def build_dome(bm):
    c, r = DOME_C
    ellipsoid(bm, c, r, DOME_ZC, (DOME_R, DOME_R, DOME_RZ), DOME, seg=32, rings=16, zmin=-0.75)
    # A gun mantlet where the barrel enters the ball (front, under the collar).
    cylinder_y(bm, CX, BARREL_ZC - 0.1, 6.0, 8.2, 1.9, BARREL, seg=24)


def build_barrel(bm):
    z = BARREL_ZC
    # Shroud, row 2 to the collar.
    vs = cylinder_y(bm, CX, z, 2.05, 6.2, 2.45, BARREL, seg=24)
    # The bore: the muzzle face inset and sunk into the shroud.
    front = max((f for f in faces_of(vs) if len(f.verts) > 4), key=lambda f: f.calc_center_median().y)
    res = bmesh.ops.inset_individual(bm, faces=[front], thickness=1.05, depth=0.0)
    for v in front.verts:
        v.co.y -= 1.2
    for f in res["faces"]:
        f.smooth = False
    # Muzzle brake band (row 3: the dark cols 9 and 15).
    cylinder_y(bm, CX, z, 3.0, 4.0, 2.95, BARREL, seg=24)
    # Cooling bands behind it.
    for r0 in (4.55,):
        cylinder_y(bm, CX, z, r0, r0 + 0.35, 2.65, BARREL, seg=24)
    # Collar (row 5, light): the mantlet block on the ring's front the barrel comes out of.
    chamfer_box(bm, 9.05, 15.95, 4.95, 6.7, 0.0, z + 2.0, 0.45, RAIL)
    # Two blue ribs along the top (cols 11 and 13).
    for c in (11.5, 13.5):
        dx = c - CX
        zr = z + math.sqrt(max(0.0, 2.45 ** 2 - dx * dx)) - 0.15
        chamfer_box(bm, c - 0.42, c + 0.42, 2.2, 5.0, zr - 0.3, zr + 0.42, 0.18, RIB)


ARM_L = [(1.0, 7.4), (2.2, 6.15), (3.95, 6.15), (4.2, 7.4), (5.0, 8.5), (6.7, 9.15), (6.7, 9.9), (5.9, 10.4), (5.9, 15.8),
         (6.8, 16.4), (7.0, 17.95), (3.0, 17.95), (3.0, 17.1), (4.0, 16.3), (4.0, 13.3), (1.0, 11.1)]


def build_arms(bm):
    for side in (-1, 1):
        loop = ARM_L if side < 0 else [(2 * CX - c, r) for c, r in reversed(ARM_L)]
        loop = chaikin(loop, 1)
        slab(bm, loop, 0.0, Z_ARM, 0.35, ARM)
        cx = 2.6 if side < 0 else 2 * CX - 2.6
        # Raised hatch on the pylon's lit top (rows 8-10), and a bolt row.
        hatch = [(1.7, 7.9), (3.6, 7.9), (4.4, 9.0), (4.4, 10.4), (1.7, 10.4)]
        if side > 0:
            hatch = [(2 * CX - c, r) for c, r in reversed(hatch)]
        slab(bm, chaikin(hatch, 1), Z_ARM - 0.1, Z_ARM + 0.22, 0.15, ARM)
        # The pin: a short blue missile pointing forward on a grey cradle.
        pc = 3.5 if side < 0 else 2 * CX - 3.5
        pz = Z_ARM + 0.45
        cylinder_y(bm, pc, pz, 4.2, 9.2, 0.55, PIN, seg=14)
        cylinder_y(bm, pc, pz, 3.35, 4.25, 0.55, PIN, seg=14, rad1=0.06, caps=True)  # nose cone
        chamfer_box(bm, pc - 0.6, pc + 0.6, 6.4, 8.8, Z_ARM - 0.2, pz + 0.05, 0.15, ARM)  # cradle
        # lower pylon panel line: a raised strip down the arm's inner edge (rows 11-16)
        sc = 5.2 if side < 0 else 2 * CX - 5.2
        chamfer_box(bm, sc - 0.35, sc + 0.35, 11.0, 16.4, Z_ARM - 0.2, Z_ARM + 0.15, 0.12, RAIL)


def build_bar(bm):
    # The beam: rows 17.9-20, cols 3-22, a chamfered bar.
    chamfer_box(bm, 3.0, 22.0, 17.9, 20.0, 0.0, 2.3, 0.45, RING)
    # The rail along its top front (row 18): a light rod the turret runs on.
    cylinder_x(bm, 3.6, 21.4, 18.55, 2.3, 0.5, RAIL, seg=16)
    # rail end blocks
    for c in (3.3, 21.7):
        chamfer_box(bm, c - 0.55, c + 0.55, 17.95, 19.3, 1.2, 2.95, 0.2, ARM)


HOUSE_L = [(4.0, 19.6), (4.4, 21.9), (5.6, 23.0), (6.0, 25.1)]


def build_carriage(bm):
    loop = chaikin(mirror_loop(HOUSE_L), 1)
    slab(bm, loop, 0.0, Z_HOUSE, 0.35, ARM)
    # Blue power block between the cheeks, standing proud and out at the back.
    blk = chaikin([(9.0, 19.8), (16.0, 19.8), (16.0, 24.7), (15.0, 26.0), (10.0, 26.0), (9.0, 24.7)], 1)
    slab(bm, blk, 0.0, Z_BLOCK, 0.4, BLOCK)
    # Vent louvres across its top (rows 22-25).
    for r in (22.4, 23.5, 24.6):
        chamfer_box(bm, 9.9, 15.1, r - 0.3, r + 0.3, Z_BLOCK - 0.2, Z_BLOCK + 0.2, 0.14, BLOCK)
    # Grey cheek caps either side of it.
    for c0, c1 in ((7.1, 9.1), (15.9, 17.9)):
        chamfer_box(bm, c0, c1, 20.0, 24.6, Z_HOUSE - 0.3, Z_HOUSE + 0.35, 0.22, ARM)
    # Pods at the upper corners: rollers/motors for the rail.
    for c in (5.6, 2 * CX - 5.6):
        ellipsoid(bm, c, 21.2, 1.2, (1.5, 1.6, 1.4), POD, seg=20, rings=10, zmin=-0.8)


def build_mesh(bm):
    build_ring(bm)
    build_deck(bm)
    build_dome(bm)
    build_barrel(bm)
    build_arms(bm)
    build_bar(bm)
    build_carriage(bm)


def spec_level(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level
    return mat


def to_object(bm, name, mats, coll):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.scale(bm, vec=(U, U, U), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = [spec_level(common.palette_material(sprite, idx, NAME, metallic=met, roughness=rough), lvl)
            for key, idx, met, rough, lvl in MATS]
    bm = bmesh.new()
    build_mesh(bm)
    obj = to_object(bm, NAME, mats, coll)
    obj.data.set_sharp_from_angle(angle=math.radians(35))
    # Outline shell from a sealed copy (the ring hole stays open so ink rings it).
    bpy.context.view_layer.update()
    shell = common.outline_shell(obj, coll, voxel=0.01, faces=2500, smooth=4, inside=0.002, islands="outer")
    shell.name = f"{NAME}_outline"
    assert len(shell.data.polygons) > 0, "empty outline shell"
    obj.data.calc_loop_triangles()
    print("MANIFEST", json.dumps({NAME: {"tris": len(obj.data.loop_triangles),
                                          "shell_faces": len(shell.data.polygons)}}))
    out = arg("--out")
    if out:  # review output only
        common.export_glb([obj, shell], Path(out))
    return [(NAME, [obj, shell], sprite["sprites"])]


def main():
    lib.run(WT, NAME, build, __file__)


if __name__ == "__main__":
    main()
