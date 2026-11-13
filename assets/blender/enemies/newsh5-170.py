"""Grey gun pod in a yoke (newsh5.shp frame 170), a 3D version of its sprite.

What it is: a terrain-fixed gun emplacement on BRAINIAC's top layer (armour 30, it fires; often
in rows of three, sometimes with a type-519 part rigid beside it). Read as a machine, the sprite is:

  - a blue-grey U yoke lying on the ground: a crossbar across the rear (rows 3-5) with tall
    knuckle blocks at both ends (rows 1-5, columns 0-2 and 21-23, a bolt head on each: the 109/107
    glints), and two narrow fork arms (columns 0-2 / 21-23, one colour pixel inside the ink) running
    forward and hooking in at rows 11-14 onto two trunnion bosses on the pod's flanks;
  - a grey bell-shaped gun pod hung on those trunnions: a rounded rear dome (rows 7-13, widening
    from 10 to 16 px) with a dark rubber boot where it meets the crossbar (rows 5-6, the dark band),
    and its mouth cut on a slope (pitched up toward the aircraft): a machined lip (row 13's bright
    line, the side frame and the chin, rows 23-25) round a recessed dark face plate;
  - in the face a grey bezel ring holding the sensor/emitter: a dim red socket, two glowing red
    lens halves split by a dark centre slot (columns 11-12), each with an orange lamp at its centre
    (columns 10 and 13, row 20);
  - an elevation actuator from a light blue-grey clevis on the crossbar (columns 11-13, rows 1-3)
    to a lug on the pod's crown (the grey neck, rows 4-7).

Colours are the sprite's indices per region (shading and glints are lighting): pod 6, lip 5,
face 2, bezel 7, boot 2, crossbar 103, knuckles and arms 104, clevis 106, trunnions/bolts 104,
actuator 7, socket 114, lens 116, slot 113, lamps 122. Glow parts are metallic 1 / rough (D126, D173).

Run: blender --background --python assets/blender/enemies/newsh5-170.py [-- --preview out.png]
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
NAME = "newsh5-170"


def find_root():
    for p in HERE.parents:
        if (p / "package.json").exists() and (p / "assets" / "blender" / "common.py").exists():
            return p
    raise SystemExit("repository not found above " + str(HERE))


ROOT = find_root()
sys.path[:0] = [str(ROOT / "assets" / "blender")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (pchip)

# Geometry is built in sprite px: x = column edge - 12 (right +), y = row edge (down the screen +),
# z = height in px. Moved to Blender at the end: X = x/12, Y = (14 - y)/12, Z = z/12.
PXU = 1 / 12

MATS = [  # (key, palette index, metallic, roughness, emission)
    ("pod", 6, 0.6, 0.42, 0.0),
    ("lip", 5, 0.55, 0.56, 0.0),
    ("wall", 4, 0.5, 0.5, 0.0),
    ("face", 2, 0.45, 0.5, 0.0),
    ("bezel", 7, 0.55, 0.62, 0.0),
    ("boot", 2, 0.15, 0.7, 0.0),
    ("yoke", 103, 0.55, 0.44, 0.0),
    ("arm", 104, 0.55, 0.42, 0.0),
    ("clevis", 106, 0.6, 0.38, 0.0),
    ("pin", 104, 0.7, 0.32, 0.0),
    ("rod", 7, 0.85, 0.22, 0.0),
    ("socket", 114, 1.0, 0.7, 0.45),
    ("lens", 116, 1.0, 0.65, 1.6),
    ("slot", 113, 1.0, 0.8, 0.35),
    ("lamp", 122, 1.0, 0.6, 1.15),
]
M = {k: i for i, (k, *_r) in enumerate(MATS)}


# --- generic builders (px space) -----------------------------------------------------------------

def faces_after(bm, n0):
    bm.faces.ensure_lookup_table()
    return bm.faces[n0:]


def loft(bm, rings, mat, cap0=True, cap1=True, smooth=True):
    """Quads between rings of equal length (lists of 3-tuples); a 1-point ring is a tip."""
    n0 = len(bm.faces)
    vr = [[bm.verts.new(p) for p in r] for r in rings]
    for r0, r1 in zip(vr, vr[1:]):
        n = max(len(r0), len(r1))
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f)
    if cap0 and len(vr[0]) > 2:
        bm.faces.new(list(reversed(vr[0])))
    if cap1 and len(vr[-1]) > 2:
        bm.faces.new(vr[-1])
    for f in faces_after(bm, n0):
        f.material_index = mat
        f.smooth = smooth
    return vr


def se_ring(cx, y, hw, zb, zt, n=2.3, sides=32):
    """A superellipse section across y: half width hw, from zb to zt."""
    zm, hh = (zb + zt) / 2, (zt - zb) / 2
    out = []
    for k in range(sides):
        a = 2 * math.pi * (k + 0.5) / sides
        c, s = math.cos(a), math.sin(a)
        out.append((cx + hw * math.copysign(abs(c) ** (2 / n), c), y, zm + hh * math.copysign(abs(s) ** (2 / n), s)))
    return out


def chrect(cx, y, hw, zb, zt, ch):
    """A chamfered rectangle across y (8 points)."""
    x0, x1 = cx - hw, cx + hw
    return [(x1, y, zb + ch), (x1, y, zt - ch), (x1 - ch, y, zt), (x0 + ch, y, zt),
            (x0, y, zt - ch), (x0, y, zb + ch), (x0 + ch, y, zb), (x1 - ch, y, zb)]


def revolve(bm, origin, axis, profile, mat, sides=16, smooth=True):
    """A solid of revolution about `axis` from `origin`: profile [(t, r)], r = 0 a point."""
    o, a = Vector(origin), Vector(axis).normalized()
    ref = Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((1, 0, 0))
    u = a.cross(ref).normalized()
    v = a.cross(u).normalized()
    rings = []
    for t, r in profile:
        c = o + a * t
        if r <= 0:
            rings.append([tuple(c)])
        else:
            rings.append([tuple(c + r * (math.cos(2 * math.pi * (k + 0.5) / sides) * u
                                         + math.sin(2 * math.pi * (k + 0.5) / sides) * v)) for k in range(sides)])
    loft(bm, rings, mat, smooth=smooth)


def hull(bm, points, mat):
    n0 = len(bm.faces)
    verts = [bm.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    for v in [v for v in verts if v.is_valid]:
        for f in v.link_faces:
            f.material_index = mat
            f.smooth = False


def cbox(x0, x1, y0, y1, z0, z1, ch, chz=None):
    return T.cbox(x0, x1, y0, y1, z0, z1, ch, chz)


def local_frame(origin, u, v, n):
    """A matrix mapping local (a, b, h) to px space."""
    u, v, n = Vector(u).normalized(), Vector(v).normalized(), Vector(n).normalized()
    return Matrix(((u.x, v.x, n.x, origin[0]), (u.y, v.y, n.y, origin[1]), (u.z, v.z, n.z, origin[2]),
                   (0, 0, 0, 1)))


def ring_sweep(bm, F, a, b, profile, mat, segs=40, smooth=True):
    """A closed ring round the ellipse (a, b) in a local frame F, cross-section `profile` as a
    closed polygon of (radial offset, height)."""
    rings = []
    for k in range(segs):
        t = 2 * math.pi * k / segs
        p = Vector((a * math.cos(t), b * math.sin(t), 0))
        nr = Vector((math.cos(t) / a, math.sin(t) / b, 0)).normalized()
        rings.append([tuple(F @ (p + nr * d + Vector((0, 0, h)))) for d, h in profile])
    n0 = len(bm.faces)
    vr = [[bm.verts.new(q) for q in r] for r in rings]
    m = len(profile)
    for i in range(segs):
        r0, r1 = vr[i], vr[(i + 1) % segs]
        for k in range(m):
            j = (k + 1) % m
            bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    for f in faces_after(bm, n0):
        f.material_index = mat
        f.smooth = smooth


def dome(bm, F, a, b, h, mat, base=-0.4, segs=24, rings=6, smooth=True):
    """A shallow ellipsoidal dome in frame F: radii (a, b), height h above the plane, its skirt
    sunk to `base`."""
    rs = [[tuple(F @ Vector((a * math.cos(2 * math.pi * k / segs), b * math.sin(2 * math.pi * k / segs), base)))
           for k in range(segs)]]
    for i in range(rings):
        t = i / rings
        s = math.cos(t * math.pi / 2)
        z = h * math.sin(t * math.pi / 2)
        rs.append([tuple(F @ Vector((a * s * math.cos(2 * math.pi * k / segs), b * s * math.sin(2 * math.pi * k / segs), z)))
                   for k in range(segs)])
    rs.append([tuple(F @ Vector((0, 0, h)))])
    loft(bm, rs, mat, cap0=True, cap1=False, smooth=smooth)


# --- the pod ----------------------------------------------------------------------------------------

# Stations down the pod (y = row edge): half width (px), bottom and top heights (px).
POD_Y = [6.5, 6.9, 7.5, 8.5, 9.5, 10.5, 11.5, 13.0, 15.0, 19.0, 22.4, 23.5, 24.5, 25.4, 25.95]
POD_W = [3.6, 4.6, 5.3, 6.3, 7.1, 7.3, 8.05, 8.15, 8.15, 8.15, 8.1, 7.4, 6.45, 5.3, 3.4]
POD_B = [2.6, 1.9, 1.3, 0.9, 0.75, 0.7, 0.7, 0.7, 0.7, 0.75, 0.85, 1.0, 1.3, 1.9, 2.8]
POD_T = [5.0, 5.7, 6.4, 7.1, 7.7, 8.2, 8.6, 8.9, 9.0, 8.9, 8.6, 8.2, 7.6, 6.8, 5.8]
# The mouth's slope: z = FACE_Z0 - FACE_K * (y - FACE_Y0), above which the bell is cut away.
FACE_Y0, FACE_Z0, FACE_K = 13.35, 8.55, 0.335
GROOVES = [9.75, 12.3]   # panel seams round the dome


def pod_plane():
    n = Vector((0, FACE_K, 1)).normalized()
    return Vector((0, FACE_Y0, FACE_Z0)), n


def build_pod(bm):
    fw, fb, ft = (T.pchip(POD_Y, POD_W), T.pchip(POD_Y, POD_B), T.pchip(POD_Y, POD_T))
    ys = sorted(set([POD_Y[0]] + [round(POD_Y[0] + 0.5 * i, 3) for i in range(1, 80) if POD_Y[0] + 0.5 * i < POD_Y[-1]]
                    + [POD_Y[-1]] + [g + d for g in GROOVES for d in (-0.16, 0, 0.16)]))
    rings = []
    for y in ys:
        w, b, t = fw(y), fb(y), ft(y)
        if any(abs(y - g) < 1e-6 for g in GROOVES):
            w, b, t = w - 0.14, b + 0.14, t - 0.14
        rings.append(se_ring(0.0, y, w, b, t, n=2.25, sides=28))
    tip0 = [(0.0, POD_Y[0] - 0.25, (fb(POD_Y[0]) + ft(POD_Y[0])) / 2)]
    tip1 = [(0.0, POD_Y[-1] + 0.12, (fb(POD_Y[-1]) + ft(POD_Y[-1])) / 2)]
    loft(bm, [tip0] + rings + [tip1], M["pod"])
    # Cut the mouth: everything above the sloped plane goes, the hole becomes lip + recessed face.
    co, no = pod_plane()
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no, clear_outer=True)
    bverts = list({v for e in bm.edges if e.is_boundary for v in e.verts})
    bmesh.ops.remove_doubles(bm, verts=bverts, dist=0.12)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges[:])
    edges = [e for e in bm.edges if e.is_boundary]
    print("mouth loop", len(edges))
    res = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    cap = res["faces"]
    for e in edges:
        e.smooth = False
    for f in cap:
        f.material_index = M["lip"]
        f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    r1 = bmesh.ops.inset_region(bm, faces=cap, thickness=0.75, depth=0.0, use_even_offset=True)
    for f in r1["faces"]:
        f.material_index = M["lip"]
        f.smooth = False
    r2 = bmesh.ops.inset_region(bm, faces=cap, thickness=0.18, depth=-0.65, use_even_offset=True)
    for f in r2["faces"]:
        f.material_index = M["wall"]
        f.smooth = False
    for f in cap:
        f.material_index = M["face"]
    for f in list(r1["faces"]) + list(r2["faces"]) + list(cap):
        for e in f.edges:
            e.smooth = False


def face_frame():
    """Local frame on the recessed face plate: a = x, b = down the slope (toward the nose), h = normal."""
    co, n = pod_plane()
    depth = 0.65
    yc = 20.5   # the lens's centre row edge (rows 18-22)
    z = FACE_Z0 - FACE_K * (yc - FACE_Y0)
    o = Vector((0.0, yc, z)) - n * depth
    b = Vector((0, 1, -FACE_K)).normalized()
    return local_frame(o, (1, 0, 0), b, n)


def build_face(bm):
    F = face_frame()
    # Bezel ring round the lens (grey, rows 15-23).
    ring_sweep(bm, F, 3.95, 3.75, [(-0.75, -0.3), (0.75, -0.3), (0.75, 0.25), (0.45, 0.6), (-0.45, 0.6),
                                   (-0.75, 0.3)], M["bezel"], segs=40)
    # Dim red socket under the lens, then two glowing lens halves split by a dark slot.
    dome(bm, F, 3.2, 2.85, 0.35, M["socket"], segs=32)
    for s in (-1, 1):
        G = F @ Matrix.Translation((s * 1.55, 0, 0.25))
        dome(bm, G, 1.45, 2.45, 0.55, M["lens"], base=-0.4, segs=24, rings=5)
        dome(bm, G @ Matrix.Translation((0, 0, 0.38)), 0.62, 0.62, 0.35, M["lamp"], base=-0.3, segs=14, rings=3)
    pts = [tuple(F @ Vector(p)) for p in cbox(-0.55, 0.55, -2.75, 2.75, -0.3, 0.75, 0.2)]
    hull(bm, pts, M["slot"])


# --- the yoke ---------------------------------------------------------------------------------------

def build_yoke(bm):
    # Crossbar across the rear (rows 3-5), a chamfered beam on the ground.
    hull(bm, cbox(-11.0, 11.0, 3.0, 5.6, 0.0, 4.3, 0.7), M["yoke"])
    # A shallow seam rib along its top.
    hull(bm, cbox(-8.4, 8.4, 3.9, 4.7, 4.0, 4.55, 0.25), M["yoke"])
    for s in (-1, 1):
        # Knuckle block at each end (rows 1-5, columns 0-3), with a bolt head on top.
        x0, x1 = (-12.0, -8.6) if s < 0 else (8.6, 12.0)
        hull(bm, cbox(x0, x1, 0.95, 5.35, 0.0, 5.6, 0.75), M["arm"])
        gx0, gx1 = (-9.2, -8.15) if s < 0 else (8.15, 9.2)
        hull(bm, cbox(gx0, gx1, 2.1, 3.6, 0.0, 3.9, 0.3), M["yoke"])
        revolve(bm, (s * 10.4, 4.0, 5.5), (0, 0, 1), [(0, 0.95), (0.35, 0.95), (0.55, 0.65), (0.55, 0.0)],
                M["pin"], sides=6, smooth=False)
        revolve(bm, (s * 10.4, 2.2, 5.5), (0, 0, 1), [(0, 0.6), (0.3, 0.6), (0.45, 0.4), (0.45, 0.0)],
                M["pin"], sides=6, smooth=False)
        # Fork arm: forward along column 1, hooking in onto the trunnion at rows 12-14.
        path = [(-10.5, 5.2, 0.0, 5.2), (-10.5, 7.5, 0.35, 5.5), (-10.5, 9.5, 0.9, 5.9), (-10.45, 11.0, 1.5, 6.3),
                (-10.0, 12.2, 2.0, 6.5), (-9.3, 13.2, 2.3, 6.4), (-8.6, 13.9, 2.5, 6.2)]
        rings = []
        for i, (x, y, zb, zt) in enumerate(path):
            hw = 1.05 if y < 6.0 else 0.82
            # rings stand square to the path in plan
            p0 = path[max(i - 1, 0)]
            p1 = path[min(i + 1, len(path) - 1)]
            tx, ty = p1[0] - p0[0], p1[1] - p0[1]
            ln = math.hypot(tx, ty)
            tx, ty = tx / ln, ty / ln
            sx, sy = ty, -tx   # side vector
            r = [(x + sx * px, y + sy * px, pz) for (px, _py, pz) in chrect(0.0, 0.0, hw, zb, zt, 0.45)]
            if s > 0:
                r = [(-q[0], q[1], q[2]) for q in reversed(r)]
            rings.append(r)
        loft(bm, rings, M["arm"], smooth=False)
        # Trunnion boss on the pod flank (axis x), and a hex cap on the arm's outer face.
        revolve(bm, (s * 9.4, 13.1, 4.4), (-s, 0, 0),
                [(0, 0.0), (0, 1.2), (0.25, 1.48), (1.75, 1.48), (1.75, 0.0)], M["pin"], sides=20)
        revolve(bm, (s * 10.75, 12.4, 4.4), (s, 0, 0), [(0, 0.0), (0, 0.8), (0.3, 0.8), (0.45, 0.55), (0.45, 0.0)],
                M["pin"], sides=6, smooth=False)


def build_actuator(bm):
    xc = 0.5   # columns 11-13
    # Clevis on the crossbar (rows 2-4): two cheeks and a pin.
    hull(bm, cbox(xc - 1.5, xc + 1.5, 2.0, 5.0, 0.0, 4.6, 0.55), M["clevis"])
    for s in (-1, 1):
        hull(bm, cbox(xc + s * 0.75 - 0.55, xc + s * 0.75 + 0.55, 2.2, 4.4, 4.0, 6.0, 0.35), M["clevis"])
    revolve(bm, (xc - 1.55, 3.3, 5.2), (1, 0, 0), [(0, 0.0), (0, 0.5), (3.1, 0.5), (3.1, 0.0)], M["pin"], sides=10)
    # Cylinder (sleeve) and rod down to a lug on the pod's crown.
    a = Vector((xc, 3.3, 5.2))
    b = Vector((xc, 8.9, 7.0))
    d = (b - a)
    L = d.length
    revolve(bm, a, d, [(0.0, 0.0), (0.0, 0.75), (0.6, 0.75), (0.75, 1.25), (3.2, 1.25), (3.4, 1.0), (3.4, 0.0)],
            M["rod"], sides=14)
    revolve(bm, a, d, [(3.3, 0.0), (3.3, 0.62), (L - 0.4, 0.62), (L, 0.0)], M["rod"], sides=12)
    # Crown lug.
    hull(bm, cbox(xc - 1.2, xc + 1.2, 7.7, 9.9, 5.6, 7.55, 0.4), M["pin"])


def build_boot(bm):
    """The dark rubber boot between the crossbar and the pod's rear dome (rows 5-6)."""
    st = [(4.7, 7.3, 0.6, 5.0), (5.05, 8.05, 0.4, 5.45), (5.45, 7.55, 0.75, 5.15), (5.85, 7.85, 0.55, 5.4),
          (6.3, 7.2, 0.95, 5.15), (6.9, 6.2, 1.4, 5.0)]
    loft(bm, [se_ring(0.0, y, w, b, t, n=2.4, sides=32) for y, w, b, t in st], M["boot"])


# --- assembly ---------------------------------------------------------------------------------------

def to_object(bm, name, mats, coll):
    m = Matrix(((PXU, 0, 0, 0), (0, -PXU, 0, 14 * PXU), (0, 0, PXU, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def build(sprite, coll):
    mats = [common.palette_material(sprite, idx, f"{NAME}" if k in ("pod",) else f"{NAME}_{k}",
                                    metallic=met, roughness=rough, emission_strength=em)
            for k, idx, met, rough, em in MATS]
    parts = []
    for fn in (build_pod, build_face, build_yoke, build_actuator, build_boot):
        bm = bmesh.new()
        fn(bm)
        parts.append(to_object(bm, f"{NAME}_{fn.__name__}", mats, coll))
    # Join into one mesh, smooth shaded with sharp edges by angle (kept sharp flags too).
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = parts[0]
    obj.name = NAME
    obj.data.name = NAME
    me = obj.data
    me.set_sharp_from_angle(angle=math.radians(34))
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    shell = common.outline_shell(obj, coll, islands="outer")
    assert len(shell.data.polygons) > 0, "empty outline shell"
    common.export_sprite_model(ROOT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = ROOT / "reference" / "models" / NAME / frame["image"]
        common.render_preview([obj], out, str(ref), size=frame["size"])
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"tris {tris}, shell faces {len(shell.data.polygons)}")


if __name__ == "__main__":
    main()
