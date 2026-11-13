"""Spiked mine (newsh3.shp frame 246), DESIGN A.

What it is: a contact sea-mine style space mine (e4:384, armour 6, top layer; swoops in and drifts
sideways). A steel ball whose top is a machined collar round a detonator well; in the well a red
hairpin firing element held down by a steel clamp bar. Four ridged bayonet spikes stand out on the
equator (up, down, left, right in the sprite) from round root bosses, and four red Hertz horns
(painted contact rods with domed caps) stand out on the diagonals, tilted a little upward.

Reading the 24x28 sprite (one frame):
  - the 1 px ink ring is the game's outline, so the top view goes to the INNER mask (D74):
    ball 11 px across (cols 7-17, rows 10-18), centre at pixel (12, 14);
    spikes 3 px wide with a 1 px point (rows 3 / 25 and cols 2 / 22), 5 px at their roots;
    horns about 2.1 px thick on the diagonals, their round ends at about 11.6 px out.
  - the bright ring (row 10, col 8) is light on the collar's crest; the dark opening inside it
    (cols 9-15, rows 11-17) is the well; the red upside-down U (cols 9-11 and 13-14, joined along
    row 11) is the hairpin element; the grey column 12 is the clamp bar.
  - colours (region median with the darkest and brightest steps left out as lighting):
    ball 5, spikes 6 (their bright middle stripe is light on the ridge), red 71 (horns and the
    hairpin; their pale ends are sheen), clamp bar 9, well walls 3 and floor 2 (a real cavity).
Underside: the plain lower half of the ball (closed, no detail).

Run: blender --background --python assets/blender/enemies/newsh3-246.py
(exports public/models/enemies/newsh3-246.glb and src/render/spriteModels/newsh3-246.json).
"""

import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = next(p for p in HERE.parents if (p / "package.json").exists())
NAME = "newsh3-246"
P = 1 / 12          # one sprite px
CX, CY = 0.5 * P, -0.5 * P   # ball centre: pixel (12, 14)'s centre

# material slots: (key, palette index, metallic, roughness, specular IOR level)
MATS = [
    ("ball", 6, 0.45, 0.36, 0.55),
    ("spike", 6, 0.4, 0.32, 0.6),
    ("red", 71, 0.25, 0.4, 0.5),
    ("clamp", 8, 0.7, 0.3, 0.55),
    ("well", 2, 0.35, 0.6, 0.35),
    ("floor", 2, 0.4, 0.6, 0.3),
]
BALL, SPIKE, RED, CLAMP, WELL, FLOOR = range(len(MATS))

R = 5.62             # ball radius (px)
SEG = 36            # around the ball
# collar / well (px): the sphere meets the collar at radius COL_R; crest radius / height; well
COL_R = 4.95
CREST_R, CREST_Z = 4.05, 4.85
WELL_R, FLOOR_Z = 3.25, 2.4

# spikes: (distance from the centre, half width) stations; ridge height = RIDGE * half width
SPIKE_V = [(6.3, 1.75), (6.8, 1.62), (8.0, 1.45), (9.6, 1.28), (10.5, 0.98), (11.3, 0.5), (12.05, 0.0)]
SPIKE_H = [(6.3, 1.75), (6.6, 1.62), (7.6, 1.45), (8.8, 1.28), (9.7, 0.98), (10.45, 0.5), (11.15, 0.0)]
RIDGE = 0.72
BOSS_R, BOSS_D0, BOSS_D1 = 2.5, 4.4, 6.45     # spike root bosses
# horns: plan distance of the cap centre, radius, elevation
HORN_END, HORN_R, HORN_CAP, HORN_TILT = 10.45, 1.05, 1.18, math.radians(13)


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def spec_level(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level
    return mat


def revolve(bm, profile, mats, segs=SEG, centre=(CX, CY), cap=False):
    """Revolve (r, z) points (px) about the vertical axis through `centre`; r = 0 is a pole.
    `mats` is one material per band (or an int). Returns the bmesh faces made."""
    import lib_b011 as lib
    cx, cy = centre
    rings = []
    for r, z in profile:
        if r <= 1e-6:
            rings.append([(cx, cy, z * P)])
            continue
        rings.append([(cx + r * P * math.cos(2 * math.pi * (i + 0.5) / segs),
                       cy + r * P * math.sin(2 * math.pi * (i + 0.5) / segs), z * P) for i in range(segs)])
    n0 = len(bm.faces)
    lib.ring_loft(bm, rings, mats, cap_start=cap, cap_end=cap)
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


def ball_profile(sealed=False):
    """(r, z, band material to the next point) from the bottom pole to the well floor centre."""
    pts = []
    # the sphere from the bottom pole up to the collar, with two V panel lines either side of the
    # equator (the hemispheres' weld seam band the spikes and horns come out of)
    def sph(deg):
        a = math.radians(deg)
        return (R * math.cos(a), R * math.sin(a))
    top = math.degrees(math.asin(math.sqrt(R * R - COL_R * COL_R) / R))
    for deg in (-90, -78, -64, -50, -37, -25, -15, -7.5):
        pts.append((*sph(deg), BALL))
    for g in (-4.2, 4.2):   # a groove: in, down, out
        a0, a1 = g - 0.9, g + 0.9
        pts.append((*sph(a0), BALL))
        r, z = sph(g)
        pts.append((r - 0.16, z, BALL))
        pts.append((*sph(a1), BALL))
    for deg in (9, 14, 19.5, top):
        pts.append((*sph(deg), BALL))
    # the collar: a short steeper shoulder, a rounded crest, the lip rolling into the well
    z0 = math.sqrt(R * R - COL_R * COL_R)
    pts += [(COL_R - 0.1, z0 + 0.55, BALL), (4.66, 3.95, BALL), (4.42, 4.52, BALL),
            (CREST_R, CREST_Z, BALL), (3.7, CREST_Z - 0.05, BALL)]
    if sealed:
        pts += [(3.5, CREST_Z - 0.2, BALL), (0.0, CREST_Z - 0.2, BALL)]
        return pts
    pts += [(3.42, CREST_Z - 0.25, WELL), (WELL_R + 0.05, CREST_Z - 0.6, WELL), (WELL_R, 3.4, WELL),
            (WELL_R - 0.05, FLOOR_Z + 0.35, WELL),
            (WELL_R - 0.3, FLOOR_Z + 0.04, FLOOR), (WELL_R - 0.55, FLOOR_Z, FLOOR), (0.0, FLOOR_Z, FLOOR)]
    return pts


def build_ball(bm, sealed=False):
    prof = ball_profile(sealed)
    return revolve(bm, [(r, z) for r, z, _ in prof], [m for _, _, m in prof[:-1]])


def ridged_spike(bm, axis, stations, mat):
    """A bayonet spike along unit plan vector `axis` in the equator plane: a ridged section (a
    flat 0.3 w ridge on top, sloped flanks to a chamfered side edge, a matching keel below) whose
    half width follows `stations` (pchip); a point at the last station."""
    import usp_talon as T
    import lib_b011 as lib
    from mathutils import Vector
    a = Vector((axis[0], axis[1], 0.0))
    s = a.cross(Vector((0, 0, 1))).normalized()
    up = Vector((0, 0, 1))
    c0 = Vector((CX, CY, 0.0))
    ds = [d for d, _ in stations]
    wf = T.pchip(ds, [w for _, w in stations])
    d_tip = ds[-1]
    rings = []
    n = 10
    for k in range(n):
        d = ds[0] + (d_tip - ds[0]) * k / n
        w = max(wf(d), 0.02)
        h = RIDGE * w
        c = c0 + a * d * P
        sec = [(w, 0.08 * h), (0.86 * w, 0.42 * h), (0.3 * w, h), (-0.3 * w, h), (-0.86 * w, 0.42 * h),
               (-w, 0.08 * h), (-w, -0.08 * h), (-0.86 * w, -0.4 * h), (-0.22 * w, -0.85 * h),
               (0.22 * w, -0.85 * h), (0.86 * w, -0.4 * h), (w, -0.08 * h)]
        rings.append([tuple(c + (s * x + up * z) * P) for x, z in sec])
    tip = c0 + a * d_tip * P
    n0 = len(bm.faces)
    # one strip per facet with its own vertices: shaded smooth, the normals blend along the
    # spike's length (no banding where the taper bends) while the ridge and edges stay crisp
    m = len(rings[0])
    for j in range(m):
        k = (j + 1) % m
        cols = [(bm.verts.new(r[j]), bm.verts.new(r[k])) for r in rings]
        tv = bm.verts.new(tuple(tip))
        for (a0, a1), (b0, b1) in zip(cols, cols[1:]):
            bm.faces.new((a0, a1, b1, b0)).material_index = mat
        bm.faces.new((cols[-1][0], cols[-1][1], tv)).material_index = mat
    base = [bm.verts.new(p) for p in rings[0]]
    bm.faces.new(list(reversed(base))).material_index = mat
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


def boss(bm, axis, mat):
    """A round root boss for a spike: a short cylinder with a chamfered outer face and a narrower
    neck ring (a nut seat), coming out of the ball."""
    import lib_b011 as lib
    from mathutils import Vector
    a = Vector((axis[0], axis[1], 0.0))
    s = a.cross(Vector((0, 0, 1))).normalized()
    up = Vector((0, 0, 1))
    c0 = Vector((CX, CY, 0.0))
    prof = [(BOSS_D0, BOSS_R - 0.2), (BOSS_D1 - 0.75, BOSS_R), (BOSS_D1 - 0.55, BOSS_R),
            (BOSS_D1 - 0.42, BOSS_R - 0.22), (BOSS_D1 - 0.3, BOSS_R - 0.22), (BOSS_D1 - 0.18, BOSS_R - 0.05),
            (BOSS_D1 - 0.05, BOSS_R - 0.12), (BOSS_D1, BOSS_R - 0.45), (BOSS_D1, 1.0)]
    rings = []
    segs = 16
    for d, r in prof:
        c = c0 + a * d * P
        rings.append([tuple(c + (s * math.cos(2 * math.pi * (i + 0.5) / segs) + up * math.sin(2 * math.pi * (i + 0.5) / segs)) * r * P)
                      for i in range(segs)])
    n0 = len(bm.faces)
    lib.ring_loft(bm, rings, mat, cap_start=True, cap_end=True)
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


def horn(bm, axis, mat):
    """A Hertz horn: a threaded base collar on the ball, the rod tilted up HORN_TILT, a domed cap a
    hair wider than the rod (the soft cap), all painted red."""
    import lib_b011 as lib
    from mathutils import Vector
    a = Vector((axis[0], axis[1], 0.0)).normalized()
    dirv = (a * math.cos(HORN_TILT) + Vector((0, 0, math.sin(HORN_TILT)))).normalized()
    c0 = Vector((CX, CY, 0.4 * P))
    end_len = HORN_END / math.cos(HORN_TILT)    # along the rod to the cap centre
    up0 = Vector((0, 0, 1))
    u = dirv.cross(up0).normalized()
    v = u.cross(dirv).normalized()
    segs = 12
    # (distance along the rod, radius): collar, rod, cap shoulder, dome
    prof = [(4.0, 1.55), (5.5, 1.55), (5.75, 1.4), (6.05, 1.4), (6.3, 1.12), (6.6, HORN_R), (end_len - 0.55, HORN_R),
            (end_len - 0.35, HORN_CAP), (end_len, HORN_CAP)]
    for k in range(1, 6):
        t = math.radians(90 * k / 6)
        prof.append((end_len + HORN_CAP * math.sin(t), HORN_CAP * math.cos(t)))
    prof.append((end_len + HORN_CAP, 0.0))
    rings = []
    for d, r in prof:
        c = c0 + dirv * d * P
        if r <= 0:
            rings.append([tuple(c)])
            continue
        rings.append([tuple(c + (u * math.cos(2 * math.pi * (i + 0.5) / segs) + v * math.sin(2 * math.pi * (i + 0.5) / segs)) * r * P)
                      for i in range(segs)])
    n0 = len(bm.faces)
    lib.ring_loft(bm, rings, mat, cap_start=True, cap_end=False)
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


def hairpin(bm, mat):
    """The red hairpin element lying on the well floor: legs at x -1.9 and +1.6 px, joined by a
    bend at the north (row 11), round ends at the south."""
    import lib_b011 as lib
    r = 1.28
    z = FLOOR_Z + r - 0.08
    xl, xr, yb, yt = -1.95, 1.55, -2.0, 1.55
    xc, rb = (xl + xr) / 2, (xr - xl) / 2
    pts = [(xl, yb)]
    pts += [(xl, yb + (yt - yb) * t) for t in (0.33, 0.66, 1.0)]
    for k in range(1, 8):
        t = math.pi - math.pi * k / 8
        pts.append((xc + rb * math.cos(t), yt + rb * math.sin(t)))
    pts += [(xr, yt), (xr, yt - (yt - yb) * 0.5), (xr, yb)]
    pts3 = [(CX + x * P, CY + y * P, z * P) for x, y in pts]
    n0 = len(bm.faces)
    lib.polyline_tube(bm, pts3, r * P, sides=10, mat_index=mat, caps=False)
    for x in (xl, xr):  # domed ends
        lib.ellipsoid(bm, (CX + x * P, CY + yb * P, z * P), (r * P, r * P, r * P), segments=10, rings=3,
                      mat_index=mat)
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


def clamp(bm, mat):
    """The steel clamp bar down the middle of the well (column 12): from a foot on the north rim,
    over the hairpin's bend, down between its legs to a bolted post on the floor."""
    import usp_talon as T
    import lib_b011 as lib
    n0 = len(bm.faces)
    xb = -0.2
    pts = [(xb, 3.95, CREST_Z - 0.08), (xb, 3.15, CREST_Z + 0.12), (xb, 2.3, 4.8), (xb, 0.6, 4.15), (xb, -1.0, 3.85)]
    pts3 = [(CX + x * P, CY + y * P, z * P) for x, y, z in pts]
    lib.polyline_tube(bm, pts3, 0.36 * P, sides=8, mat_index=mat, caps=True, flat=0.7)
    # the post and its bolt head at the south end
    lib.tube(bm, (CX + xb * P, CY - 1.0 * P, FLOOR_Z * P), (CX + xb * P, CY - 1.0 * P, 3.8 * P), 0.36 * P,
             sides=8, mat_index=mat)
    lib.ellipsoid(bm, (CX + xb * P, CY - 1.0 * P, 3.95 * P), (0.5 * P, 0.5 * P, 0.25 * P), segments=8, rings=2,
                  mat_index=mat, top_only=True)
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


def bolts(bm, mat):
    """Eight domed bolt heads round the collar's outer shoulder (between the spikes and horns)."""
    import lib_b011 as lib
    from mathutils import Matrix, Vector
    n0 = len(bm.faces)
    for k in range(8):
        t = 2 * math.pi * (k + 0.5) / 8
        rr = 4.6
        z = 4.3
        # tilt the head to the shoulder's normal
        nrm = Vector((math.cos(t) * 0.75, math.sin(t) * 0.75, 0.66)).normalized()
        rot = Vector((0, 0, 1)).rotation_difference(nrm).to_matrix()
        lib.ellipsoid(bm, (CX + rr * math.cos(t) * P, CY + rr * math.sin(t) * P, z * P),
                      (0.36 * P, 0.36 * P, 0.2 * P), segments=8, rings=2, mat_index=mat, rot=rot, top_only=True)
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


AXES = [(0, 1), (0, -1), (-1, 0), (1, 0)]
DIAG = [(-1, 1), (1, 1), (-1, -1), (1, -1)]


def build_geometry(bm, sealed=False):
    """Returns (smooth faces, flat faces)."""
    smooth, flat = [], []
    smooth += build_ball(bm, sealed)
    for ax in AXES:
        st = SPIKE_V if ax[0] == 0 else SPIKE_H
        smooth += ridged_spike(bm, ax, st, SPIKE)
        smooth += boss(bm, ax, SPIKE)
    for ax in DIAG:
        smooth += horn(bm, ax, RED)
    if not sealed:
        smooth += hairpin(bm, RED)
        smooth += clamp(bm, CLAMP)
        smooth += bolts(bm, SPIKE)
    return smooth, flat


def build():
    import bmesh
    import bpy
    sys.path.insert(0, str(WT / "assets" / "blender"))
    sys.path.insert(0, str(WT / "assets" / "blender" / "enemies"))
    import common

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    mats = [spec_level(common.palette_material(sprite, idx, NAME, metallic=met, roughness=rough), lvl)
            for key, idx, met, rough, lvl in MATS]

    bm = bmesh.new()
    smooth, flat = build_geometry(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in smooth:
        f.smooth = True
    for f in flat:
        f.smooth = False
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)

    # outline shell from a sealed copy (the well capped at the lip): ink on the silhouette only
    bm = bmesh.new()
    build_geometry(bm, sealed=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    seal_me = bpy.data.meshes.new(NAME + "_seal")
    bm.to_mesh(seal_me)
    bm.free()
    seal = bpy.data.objects.new(NAME + "_seal", seal_me)
    coll.objects.link(seal)
    bpy.context.view_layer.update()
    shell = common.outline_shell(seal, coll, voxel=0.006, faces=3000, smooth=4, inside=0.002, islands="outer")
    bpy.data.objects.remove(seal, do_unlink=True)
    shell.name = f"{NAME}_outline"
    assert len(shell.data.polygons) > 0, "empty outline shell"
    mesh.calc_loop_triangles()
    manifest = {"tris": len(mesh.loop_triangles), "shell_faces": len(shell.data.polygons)}
    objs = [obj, shell]
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"])
    print("MANIFEST", json.dumps({NAME: manifest}))


if __name__ == "__main__":
    build()
