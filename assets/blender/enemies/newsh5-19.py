"""Red spore (newsh5.shp frames 19 and 38): a 3D version of its sprite.

What it is: a homing organic projectile (types 640 / 791: armour 5-6, homing) that the brain of
BRAINIAC (4.22) and the face of NOSE DRIP (4.25) spit at the player. Never placed by a level
event; it only exists as something launched. So it is a spore: a soft, wet seed capsule about
10 px across, not a craft.

Reading the 12x14 sprite (frame 19; frame 38 is the same capsule turned a little):
  - outline: the 1 px ink ring (1, 112, 113, 114 at the rim) is lighting/ink, so the top view
    goes to the INNER mask (sprite_mask, D74). The silhouette is a lumpy egg, wider at the top,
    pinched in to the lower left.
  - two lobes split by a suture: column 5 runs dark (114) from the top down to a dark pore
    (113/112 at rows 5 of frame 19, row 6 of frame 38). Left of it the larger lobe (catching the
    sprite's light: 117/118 and the 123/121 glint, which is sheen, not a bump), right of it the
    smaller lobe. Built as a faired two-lobed capsule: a groove (the suture) and a pore with a
    raised lip at its lower end, where the spore will burst.
  - colours (median of each region with the darkest and brightest steps left out): body 115,
    the suture floor 114, the pore throat 113.
  - frame 38: narrower (columns 1-9) and a pixel lower, its suture and pore a pixel lower.
One model, one capsule per frame (common.frame_part), each fitted to its own frame's inner mask:
the top-view outline is the frame's inner mask, rounded (a blurred mask's half level, D74), turned
into a polar radius about the mask's centroid, so the silhouette matches row by row.

Underside: a plain rounded belly (closed).

Run: blender --background --python assets/blender/enemies/newsh5-19.py
(exports public/models/enemies/newsh5-19.glb and src/render/spriteModels/newsh5-19.json)
"""

import json
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WT = next(p for p in HERE.parents if (p / "package.json").exists())
NAME = "newsh5-19"

U = 1 / 12      # one sprite px in Blender units
W, H = 12, 14   # the sprite

BODY, SUTURE, PORE = range(3)
MATS = [  # (key, palette index, metallic, roughness, specular IOR level)
    ("body", 115, 0.6, 0.32, 0.6),
    ("suture", 114, 0.15, 0.5, 0.4),
    ("pore", 113, 0.1, 0.6, 0.3),
]

# Per frame, in sprite px (column, row of pixel centres):
#   lobes: (col, row, sigma px, height gain) swell the top; suture: polyline (col, row);
#   pore: (col, row) the burst pore at the suture's lower end.
FRAMES = {
    19: dict(
        lobes=[(3.2, 4.7, 2.1, 0.28), (7.2, 4.3, 1.7, 0.18), (4.4, 7.6, 1.7, 0.06)],
        suture=[(5.45, 1.7), (4.65, 5.15)],
        pore=(4.65, 5.15),
    ),
    38: dict(
        lobes=[(3.1, 5.3, 2.0, 0.28), (7.0, 4.8, 1.6, 0.18), (4.4, 8.6, 1.6, 0.06)],
        suture=[(5.25, 2.4), (4.8, 5.95)],
        pore=(4.8, 5.95),
    ),
}

H_TOP = 3.9 * U      # dome height above the rim plane
H_BOT = 2.7 * U      # belly depth below it
NSEG = 72            # around
NTOP = 24            # rings rim -> pole on top
NBOT = 7             # rings rim -> pole underneath
SUTURE_W = 0.6       # px, groove half width (gaussian sigma)
SUTURE_D = 1.0      # px, groove depth
PORE_R = 1.25        # px, pore radius
PORE_D = 1.5        # px, pore depth
LIP_H = 0.22
BEAD_W = 0.4       # px, the suture bead's half width
BEAD_H = 0.16       # px
BEAD_SINK = 0.1     # px, the bead's centre below the groove floor
BLUR = 0.42          # px, mask blur (rounds the staircase)
LEVEL = 0.5
SMOOTH_PASSES = 3
PROFILE = 2.35      # superellipse exponent of the dome (2 = ellipse; more = fuller shoulders)


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def X(c):
    """Sprite column (pixel centre at c) -> units."""
    return (c + 0.5 - W / 2) * U


def Y(r):
    return (H / 2 - (r + 0.5)) * U


# --- The outline: inner mask -> smooth polar radius ---------------------------------------------

def inner_mask(frame):
    """The frame's inner mask (tools/sprite_mask.py, D74) as a float array, rows top to bottom."""
    import subprocess
    out = subprocess.run(["python3", str(WT / "tools" / "sprite_mask.py"), NAME, "--frame", str(frame), "--json"],
                         capture_output=True, text=True, check=True).stdout
    rows = json.loads(out)["masks"]
    return np.array([[ch == "#" for ch in r] for r in rows], float)


def blurred_field(mask, k=16, pad=3):
    big = np.kron(np.pad(mask, pad), np.ones((k, k)))
    s = BLUR * k
    xs = np.arange(-int(3 * s) - 1, int(3 * s) + 2)
    g = np.exp(-0.5 * (xs / s) ** 2)
    g /= g.sum()
    big = np.apply_along_axis(lambda v: np.convolve(v, g, "same"), 0, big)
    big = np.apply_along_axis(lambda v: np.convolve(v, g, "same"), 1, big)

    def sample(c, r):
        """Field at sprite coords (c, r are continuous pixel-edge coordinates: column c from 0 at
        the left edge, row r from 0 at the top edge)."""
        fx = (c + pad) * k - 0.5
        fy = (r + pad) * k - 0.5
        x0, y0 = int(math.floor(fx)), int(math.floor(fy))
        tx, ty = fx - x0, fy - y0
        if x0 < 0 or y0 < 0 or x0 + 1 >= big.shape[1] or y0 + 1 >= big.shape[0]:
            return 0.0
        a = big[y0, x0] * (1 - tx) + big[y0, x0 + 1] * tx
        b = big[y0 + 1, x0] * (1 - tx) + big[y0 + 1, x0 + 1] * tx
        return a * (1 - ty) + b * ty
    return sample


_FIELDS = {}


def field_of(frame):
    if frame not in _FIELDS:
        mask = inner_mask(frame)
        rr, cc = np.nonzero(mask)
        _FIELDS[frame] = (blurred_field(mask), (cc.mean() + 0.5, rr.mean() + 0.5))
    return _FIELDS[frame]


def polar_outline(frame, cen=None):
    """(centre (c, r) in edge coords, radius per angle in px) of the rounded inner mask, about
    `cen` (edge coords; default the mask's centroid)."""
    f, centroid = field_of(frame)
    cen = cen or centroid
    radii = []
    for i in range(NSEG):
        a = 2 * math.pi * i / NSEG
        dx, dy = math.cos(a), -math.sin(a)   # +y up in units = -row
        t, step = 0.0, 0.05
        while f(cen[0] + dx * t, cen[1] + dy * t) >= LEVEL and t < 12:
            t += step
        lo, hi = t - step, t
        for _ in range(20):
            mid = (lo + hi) / 2
            if f(cen[0] + dx * mid, cen[1] + dy * mid) >= LEVEL:
                lo = mid
            else:
                hi = mid
        radii.append((lo + hi) / 2)
    # Smooth the outline as points (not radii), so a wobble left by the pixel steps is faired out.
    pts = np.array([(cen[0] + r * math.cos(2 * math.pi * i / NSEG), cen[1] - r * math.sin(2 * math.pi * i / NSEG))
                    for i, r in enumerate(radii)])
    k = np.array([1, 4, 6, 4, 1], float) / 16
    for _ in range(SMOOTH_PASSES):
        pts = sum(k[j] * np.roll(pts, j - 2, axis=0) for j in range(5))
    d = pts - np.array(cen)
    radii = np.hypot(d[:, 0], d[:, 1])
    return cen, radii


def radius_at(cen, radii, c, r):
    """The outline radius (px) about `cen` in the direction of edge-coord point (c, r)."""
    a = math.atan2(-(r - cen[1]), c - cen[0]) % (2 * math.pi)
    t = a / (2 * math.pi) * NSEG
    i = int(t) % NSEG
    u = t - int(t)
    return radii[i] * (1 - u) + radii[(i + 1) % NSEG] * u


# --- The capsule ---------------------------------------------------------------------------------

def seg_dist(p, a, b):
    ab = (b[0] - a[0], b[1] - a[1])
    L = ab[0] ** 2 + ab[1] ** 2
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / L))
    q = (a[0] + ab[0] * t, a[1] + ab[1] * t)
    return math.hypot(p[0] - q[0], p[1] - q[1]), t


def suture_depth(c, r, spec):
    """Groove depth (px) at sprite point (c, r) (pixel-centre coords), fading in at its top end."""
    pts = spec["suture"]
    best, along = 1e9, 0.0
    n = len(pts) - 1
    for i in range(n):
        d, t = seg_dist((c, r), pts[i], pts[i + 1])
        if d < best:
            best, along = d, (i + t) / n
    fade = min(1.0, along / 0.3)
    return SUTURE_D * fade * math.exp(-0.5 * (best / SUTURE_W) ** 2)


def pore_shape(c, r, spec):
    """(depth px, lip px) of the pore at (c, r)."""
    pc, pr = spec["pore"]
    d = math.hypot(c - pc, r - pr)
    depth = PORE_D * max(0.0, 1 - (d / PORE_R) ** 2) ** 1.5
    lip = LIP_H * math.exp(-0.5 * ((d - PORE_R * 1.05) / 0.32) ** 2)
    return depth, lip


def lobe_gain(c, r, spec):
    return 1.0 + sum(a * math.exp(-0.5 * ((c - lc) ** 2 + (r - lr) ** 2) / s ** 2) for lc, lr, s, a in spec["lobes"])


def build_capsule(bm, frame, detail=True):
    """One frame's capsule into bmesh `bm`; returns nothing. detail=False: the sealed shape (no
    suture, no pore) for the outline shell."""
    import bmesh  # noqa: F401
    spec = FRAMES[frame]
    pore_edge = (spec["pore"][0] + 0.5, spec["pore"][1] + 0.5)
    # The mesh is polar about the pore (so the pore and the suture running out of it are cut
    # cleanly by the rings and spokes); the dome's height is polar about the mask's centroid.
    (cen_c, cen_r), radii = polar_outline(frame, pore_edge)
    rings_top = []
    for j in range(NTOP):          # j = 0 rim ... NTOP-1 just short of the pore
        phi = (math.pi / 2) * j / NTOP
        ring = []
        for i in range(NSEG):
            a = 2 * math.pi * i / NSEG
            rho = radii[i] * math.cos(phi)
            ring.append((cen_c + rho * math.cos(a), cen_r - rho * math.sin(a), math.sin(phi)))
        rings_top.append(ring)
    top_pole = (cen_c, cen_r, 1.0)
    rings_bot = []
    for j in range(1, NBOT):
        phi = (math.pi / 2) * j / NBOT
        ring = []
        for i in range(NSEG):
            a = 2 * math.pi * i / NSEG
            rho = radii[i] * math.cos(phi)
            ring.append((cen_c + rho * math.cos(a), cen_r - rho * math.sin(a), -math.sin(phi)))
        rings_bot.append(ring)
    bot_pole = (cen_c, cen_r, -1.0)

    def place(ce, re_, sphi):
        """Edge coords + sin of the ring's elevation (+ top, - belly) -> (x, y, z) units before the
        displacement. rho (0 at the pore, 1 at the rim) is cos(phi) of the polar rings."""
        c, r = ce - 0.5, re_ - 0.5
        rho = math.sqrt(max(0.0, 1 - sphi * sphi))
        if sphi > 0:
            s = (1 - rho ** PROFILE) ** (1 / PROFILE)
            # Lobes swell the dome, held to zero at the rim (silhouette stays the mask's).
            g = 1 + (lobe_gain(c, r, spec) - 1) * s ** 0.6
            return [X(c), Y(r), H_TOP * s * g]
        if sphi < 0:
            return [X(c), Y(r), -H_BOT * (1 - rho ** 2.1) ** (1 / 2.1)]
        return [X(c), Y(r), 0.0]

    vt = [[bm.verts.new(place(*p)) for p in ring] for ring in rings_top]
    vtp = bm.verts.new(place(*top_pole))
    vb = [[bm.verts.new(place(*p)) for p in ring] for ring in rings_bot]
    vbp = bm.verts.new(place(*bot_pole))
    faces = []
    for r0, r1 in zip(vt, vt[1:]):
        for i in range(NSEG):
            k = (i + 1) % NSEG
            faces.append(bm.faces.new((r0[i], r0[k], r1[k], r1[i])))
    for i in range(NSEG):
        faces.append(bm.faces.new((vt[-1][i], vt[-1][(i + 1) % NSEG], vtp)))
    under = [vt[0]] + vb
    for r0, r1 in zip(under, under[1:]):
        for i in range(NSEG):
            k = (i + 1) % NSEG
            faces.append(bm.faces.new((r0[k], r0[i], r1[i], r1[k])))
    for i in range(NSEG):
        faces.append(bm.faces.new((vb[-1][(i + 1) % NSEG], vb[-1][i], vbp)))
    for f in faces:
        f.smooth = True
        f.material_index = BODY
    bmesh_normals(bm, faces)
    if not detail:
        return
    # Suture and pore: displace top verts along their normal (so the silhouette is untouched:
    # both lie well inside the rim).
    top_verts = [v for ring in vt[2:] for v in ring] + [vtp]
    info = {}
    for v in top_verts:
        c = v.co.x / U + W / 2 - 0.5
        r = H / 2 - v.co.y / U - 0.5
        g = suture_depth(c, r, spec)
        pd, lip = pore_shape(c, r, spec)
        d = max(g, pd) - lip
        info[v] = (g, pd)
        if abs(d) > 1e-6:
            v.co -= v.normal * d * U
    for f in faces:
        gs = [info.get(v, (0, 0)) for v in f.verts]
        g = sum(a for a, _ in gs) / len(gs)
        p = sum(b for _, b in gs) / len(gs)
        if p > 0.3 * PORE_D:
            f.material_index = PORE
    # The suture's floor: a slim bead (114) laid in the groove, so its edges are clean lines
    # (a face-material strip on the polar mesh came out ragged).
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    tree = BVHTree.FromBMesh(bm)
    (c0, r0), (c1, r1) = spec["suture"][0], spec["suture"][-1]
    n = 14
    path = []
    for i in range(n + 1):
        t = 0.12 + 0.8 * i / n
        c, r = c0 + (c1 - c0) * t, r0 + (r1 - r0) * t
        hit = tree.ray_cast(Vector((X(c), Y(r), 1.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        fade = min(1.0, t / 0.3)
        path.append((X(c), Y(r), hit[0].z - BEAD_SINK * U, BEAD_W * U * (0.55 + 0.45 * fade), BEAD_H * U))
    sweep_bead(bm, path, SUTURE)


def sweep_bead(bm, path, mat, sides=8):
    """A rounded bead along path [(x, y, z, half width, half height)], tapering to points at both
    ends (a copy of lib_b030.sweep's idea; shared files are not edited)."""
    from mathutils import Vector
    pts = [Vector(p[:3]) for p in path]
    up = Vector((0, 0, 1))
    rings = []
    m = len(path)
    for i, (x, y, z, w, h) in enumerate(path):
        t = pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        t.normalize()
        side = t.cross(up)
        e = min(i, m - 1 - i)
        k = (0.0, 0.7, 1.0)[min(e, 2)]
        if k == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        rings.append([bm.verts.new(pts[i] + side * (w * k * math.cos(2 * math.pi * (j + 0.5) / sides))
                                   + up * (h * k * math.sin(2 * math.pi * (j + 0.5) / sides))) for j in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for j in range(sides):
            jj = (j + 1) % sides
            if len(a) == 1:
                f = bm.faces.new((a[0], b[jj], b[j]))
            elif len(b) == 1:
                f = bm.faces.new((a[j], a[jj], b[0]))
            else:
                f = bm.faces.new((a[j], a[jj], b[jj], b[j]))
            f.material_index = mat
            f.smooth = True


def bmesh_normals(bm, faces):
    import bmesh
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    bm.normal_update()


def spec_level(mat, level):
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
    mats = [spec_level(common.palette_material(sprite, idx, NAME + ("" if key == "body" else f"-{key}"),
                                               metallic=met, roughness=rough), lvl)
            for key, idx, met, rough, lvl in MATS]
    objs, manifest = [], {}
    for frame in FRAMES:
        oname = NAME if frame == 19 else f"{NAME}-turn-{frame}"
        bm = bmesh.new()
        build_capsule(bm, frame)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new(oname)
        bm.to_mesh(mesh)
        bm.free()
        for m in mats:
            mesh.materials.append(m)
        obj = bpy.data.objects.new(oname, mesh)
        coll.objects.link(obj)
        common.frame_part(obj, [frame])
        # Outline shell from the sealed capsule (no suture, no pore): ink on the silhouette only.
        bm = bmesh.new()
        build_capsule(bm, frame, detail=False)
        seal_me = bpy.data.meshes.new(oname + "_seal")
        bm.to_mesh(seal_me)
        bm.free()
        seal = bpy.data.objects.new(oname + "_seal", seal_me)
        coll.objects.link(seal)
        bpy.context.view_layer.update()
        shell = common.outline_shell(seal, coll, voxel=0.005, faces=1200, smooth=4, inside=0.002, islands="outer")
        bpy.data.objects.remove(seal, do_unlink=True)
        shell.name = f"{oname}_outline"
        assert len(shell.data.polygons) > 0, "empty outline shell"
        common.frame_part(shell, [frame])
        mesh.calc_loop_triangles()
        manifest[frame] = {"tris": len(mesh.loop_triangles), "shell_faces": len(shell.data.polygons)}
        objs += [obj, shell]
    for o in objs:
        o["design_model"] = NAME
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"])
    print("MANIFEST", json.dumps({NAME: manifest}))


if __name__ == "__main__":
    build()
