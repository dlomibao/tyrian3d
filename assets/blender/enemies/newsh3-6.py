"""Four-pod spinner (newsh3.shp frame 6), a 3D version of its sprite.

What it is: a small weaving drone (armour 4) made of four polished steel pods on the diagonals,
joined at a glossy red sensor ball. Seen from above, as the sprite draws it:

  - the pods: four identical steel nacelles, each symmetric about its diagonal. Plan from the
    sprite's inner mask (half width per station along the diagonal, smoothed and pchip
    interpolated), so each pod is a blunt round bulb at the outer end that narrows into a faired
    neck at the hub; neighbouring pods stand 4 px apart along the axes as the sprite's ink channels
    show. Sections are slightly squared ellipses (a faired hard shell, taller above the waterline
    than below). Machined detail: a recessed panel joint round the body at about 55% of its
    length, a nose-cap seam near the outer end with a recessed exhaust disc in the blunt nose, and
    a small polished sensor lens on the inner shoulder of each pod (the sprite's bright stud with
    its dark rim, at columns 8/15, rows 9/16, mirrored on all four pods, so it is a part, not a
    highlight).
  - the hub: a glossy red ball (pal 70, the median of its pixels) 4 px across at the centre,
    standing proud of the pod necks, on a steel collar the necks run into.

One frame (6). Steel is satin-polished (pal 9, the median of the pod pixels, metallic 0.7 /
roughness 0.32, F0 via Specular IOR Level, D176); the sprite's light upper-left / dark lower-right
pods, dark necks and outline ring are its lighting. Underside: the pods' lower half-sections
close it, no detail. The outline shell comes from a sealed copy (no grooves, lenses or exhaust)
with islands="outer" (D189).

Writes public/models/enemies/newsh3-6.glb and src/render/spriteModels/newsh3-6.json; with
--out X.glb also a copy there (review only).

    blender --background --python assets/blender/enemies/newsh3-6.py [-- --out X.glb]
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
WT = next(p for p in HERE.parents if (p / "package.json").exists())
NAME = "newsh3-6"
W, H = 24, 28
U = 1 / 12
# Hub centre: the pixel edge at column 12, row 13 (the mask is symmetric about it).
HCX, HCY = 0.0, 1.0           # px from the sprite centre (x right, y up)

# Pod plan (px), fitted to the sprite's inner mask (fit2d.py: rule-grid IoU 1.0 over a +-0.1 px box):
# each pod is an ellipse along its diagonal (centre UC, semi axes A along, B across) unioned with a
# round neck strut of half width NW from the hub (p-norm smooth union, a fillet).
UC, A, B, NW, PN = 8.57, 4.07, 3.47, 1.26, 4.0
U0 = 1.4                      # where the neck starts, inside the ball
KT, KB = 0.92, 0.70           # pod section height above / depth below its centre line, x half width
ZC = 2.4                      # pod and neck centre line above the base plane
SIDES = 18
NOSE_SEAM = 2.2               # nose-cap seam, px out from the pod centre
JOINT = -3.55                 # neck socket seam, px from the pod centre (where the strut meets the pod)
STRUT_END = UC - A + 0.45     # the strut (gunmetal, the sprite's dark neck pixels, pal 6) ends at the socket seam
GROOVE = 0.22                 # groove depth (px)
GROOVE_W = 0.2                # groove half width (px along u)
EXH = 0.55                    # exhaust disc: cut this far in from the tip
# Hub ball
BALL_R = 2.05
BALL_Z = 3.1
# Sensor lens per pod: at the sprite's stud, column 8 / row 9 (TL pod), mirrored.
LENS_U = 5.5
LENS_R = 0.75

# Materials: key -> (palette index, metallic, roughness, emission, specular level)
MATS = [
    ("steel", 9, 0.7, 0.32, 0.0, 0.5),
    ("ball", 70, 0.1, 0.14, 0.0, 0.8),
    ("lens", 13, 0.6, 0.22, 0.0, 0.7),
    ("dark", 7, 0.7, 0.45, 0.0, 0.5),
    ("strut", 6, 0.65, 0.4, 0.0, 0.5),
]
STEEL, BALL, LENS, DARK, STRUT = range(len(MATS))


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


# --- Pod plan and sections ----------------------------------------------------------------------

def smax(a, b):
    return (a ** PN + b ** PN) ** (1 / PN)


def pod_wc(u):
    t = min(1.0, abs((u - UC) / A))
    return B * math.sqrt(max(0.0, 1 - t * t))


def sec_dims(u):
    """(half width, top above the centre line, depth below it) of a pod section at u (px)."""
    wc = pod_wc(u)
    wn = NW if u < UC else 0.0
    return smax(wc, wn), smax(KT * wc, wn), smax(KB * wc, wn)


def section(w, top, bot, zc, n=SIDES):
    pts = []
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        cu, sv = math.cos(a), math.sin(a)
        z = zc + (top * sv if sv > 0 else bot * sv)
        pts.append((w * cu, z))
    return pts


def build_pod(detail=True):
    """Rings of the TL pod in local (u, v, z) px, and the nose centre point."""
    tip = UC + A
    us = [U0 + k * 0.8 for k in range(int((UC - A - U0) / 0.8) + 1)]
    for k in range(1, 22):
        phi = math.pi * (1 - k / 22)
        us.append(UC + A * math.cos(phi))
    end = tip - EXH if detail else tip - 0.12
    us = [u for u in us if U0 <= u < end - 0.05] + [end]
    grooves = []
    if detail:
        for g in (UC + NOSE_SEAM, UC + JOINT):
            us = [x for x in us if abs(x - g) > GROOVE_W * 1.8]
            us += [g - GROOVE_W * 1.6, g - GROOVE_W * 0.6, g + GROOVE_W * 0.6, g + GROOVE_W * 1.6]
            grooves.append(g)
    us.sort()
    rings = []
    for u in us:
        w, top, bot = sec_dims(u)
        depth = GROOVE if any(abs(u - g) < GROOVE_W for g in grooves) else 0.0
        f = max(0.05, w - depth) / w
        rings.append([(u, v, z) for v, z in section(w * f, top * f, bot * f, ZC)])
    last = rings[-1]
    if detail:
        # the exhaust: a chamfered lip, then a recessed disc facing out along the diagonal
        lip = [(end + 0.08, v * 0.8, ZC + (z - ZC) * 0.8) for _, v, z in last]
        rec = [(end - 0.16, v * 0.56, ZC + (z - ZC) * 0.56) for _, v, z in last]
        return rings + [lip, rec], (end - 0.1, 0.0, ZC)
    return rings, (tip, 0.0, ZC)


def lens_local():
    """The TL lens in local (u, v) px: the sprite's stud pixel (column 8, row 9) spans u 4.24-5.66
    on the diagonal; the lens sits just outboard of the socket seam, inside that pixel."""
    return LENS_U, 0.0


def to_world(u, v, z, ang):
    """Local TL-pod frame (u outward along the diagonal, v to its right) -> model units."""
    s = 1 / math.sqrt(2)
    d = (-s, s)
    n = (s, s)
    x = d[0] * u + n[0] * v
    y = d[1] * u + n[1] * v
    ca, sa = math.cos(ang), math.sin(ang)
    xr, yr = ca * x - sa * y, sa * x + ca * y
    return ((HCX + xr) * U, (HCY + yr) * U, z * U)


def add_loft(bm, rings, centre, ang, mat, cap_mat):
    vs = [[bm.verts.new(to_world(*p, ang)) for p in ring] for ring in rings]
    n = len(vs[0])
    for b, (r0, r1) in enumerate(zip(vs, vs[1:])):
        um = (rings[b][0][0] + rings[b + 1][0][0]) / 2
        m = STRUT if (um < STRUT_END and cap_mat != STEEL) else mat
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = m
    bm.faces.new(list(reversed(vs[0]))).material_index = STRUT if cap_mat != STEEL else mat
    c = bm.verts.new(to_world(*centre, ang))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((vs[-1][i], vs[-1][j], c)).material_index = cap_mat


def sphere(bm, centre, r, mat, seg=24, rings=12, rz=None, rot=None):
    from mathutils import Vector
    cx, cy, cz = centre
    rz = rz or r
    pts = []
    for k in range(-rings, rings + 1):
        t = (math.pi / 2) * k / rings
        if abs(k) == rings:
            pts.append([(cx, cy, cz + math.copysign(rz, k))])
            continue
        pts.append([(cx + r * math.cos(t) * math.cos(2 * math.pi * (i + 0.5) / seg),
                     cy + r * math.cos(t) * math.sin(2 * math.pi * (i + 0.5) / seg),
                     cz + rz * math.sin(t)) for i in range(seg)])
    if rot is not None:
        c = Vector((cx, cy, cz))
        pts = [[tuple(c + rot @ (Vector(p) - c)) for p in ring] for ring in pts]
    vs = [[bm.verts.new(p) for p in ring] for ring in pts]
    for r0, r1 in zip(vs, vs[1:]):
        nn = max(len(r0), len(r1))
        for i in range(nn):
            j = (i + 1) % nn
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat


def build_hub(bm, detail=True):
    # steel collar under the ball, where the necks meet (radius under the ball's on the axes)
    sphere(bm, (HCX * U, HCY * U, (ZC - 0.2) * U), 1.9 * U, STRUT, seg=16, rings=4, rz=1.5 * U)
    sphere(bm, (HCX * U, HCY * U, BALL_Z * U), BALL_R * U, BALL, seg=24, rings=10)


def build_lenses(bm):
    lu, lv = lens_local()
    w, top, _ = sec_dims(lu)
    t = math.sqrt(max(0.0, 1 - (lv / w) ** 2))
    zs = ZC + top * t
    # tilt the lens to the surface: slope of the top along u
    w2, top2, _ = sec_dims(lu + 0.2)
    slope = (top2 - top) / 0.2
    from mathutils import Matrix
    for k in range(4):
        ang = k * math.pi / 2
        x, y, z = to_world(lu, lv, zs - 0.18, ang)
        s = 1 / math.sqrt(2)
        dx, dy = to_world(1, 0, 0, ang)[0] / U - HCX, to_world(1, 0, 0, ang)[1] / U - HCY
        axis = (-dy, dx, 0.0)
        rot = Matrix.Rotation(-math.atan(slope), 3, axis)
        sphere(bm, (x, y, z), (LENS_R + 0.3) * U, DARK, seg=16, rings=4, rz=0.3 * U, rot=rot)
        sphere(bm, (x, y, z), LENS_R * U, LENS, seg=16, rings=5, rz=0.48 * U, rot=rot)


def spec(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level
    return mat


def build():
    import bmesh
    import bpy
    sys.path.insert(0, str(WT / "assets" / "blender"))
    import common

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    mats = [spec(common.palette_material(sprite, idx, f"{NAME}-{key}", metallic=m, roughness=r,
                                         emission_strength=e), sp)
            for key, idx, m, r, e, sp in MATS]

    def make(detail):
        bm = bmesh.new()
        rings, centre = build_pod(detail)
        for k in range(4):
            add_loft(bm, rings, centre, k * math.pi / 2, STEEL, DARK if detail else STEEL)
        build_hub(bm)
        if detail:
            build_lenses(bm)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return bm

    bm = make(True)
    for f in bm.faces:
        f.smooth = True
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    es = obj.modifiers.new("hard", "EDGE_SPLIT")
    es.split_angle = math.radians(40)
    es.use_edge_sharp = False
    bpy.context.view_layer.update()

    bm = make(False)
    seal_me = bpy.data.meshes.new(NAME + "_seal")
    bm.to_mesh(seal_me)
    bm.free()
    seal = bpy.data.objects.new(NAME + "_seal", seal_me)
    coll.objects.link(seal)
    bpy.context.view_layer.update()
    shell = common.outline_shell(seal, coll, voxel=0.006, faces=2400, smooth=4, inside=0.002, islands="outer")
    bpy.data.objects.remove(seal, do_unlink=True)
    shell.name = f"{NAME}_outline"
    assert len(shell.data.polygons) > 0, "empty outline shell"
    mesh.calc_loop_triangles()
    tris = len(mesh.loop_triangles)
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])
    if arg("--out"):
        common.export_glb([obj, shell], Path(arg("--out")))
    print("MANIFEST", json.dumps({NAME: {"frames": [6], "tris": tris,
                                         "shell_faces": len(shell.data.polygons)}}))


if __name__ == "__main__":
    build()
