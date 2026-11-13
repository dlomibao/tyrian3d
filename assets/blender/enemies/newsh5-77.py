"""Grey bomb (newsh5.shp frame 77), DESIGN A: a turned steel bomb falling nose first down the screen.

What it is (episode 4: DREAD-NOT 4.18 drifting down at (0,+3); BRAINIAC 4.22 dropped from between
the halves of the newsh5-85 bomber; APPROACH 4.47): a small free-fall bomb, one body of revolution
whose long axis lies in the screen plane, nose toward the bottom of the screen. From the tail:

  - a stabiliser drum (rows 1-3): a flat steel disc 11 px across with chamfered rims and a V
    groove round its middle (the sprite's dark row 2 between two lit rims); its back face is a
    machined dish with a raised hub and six bolt heads; its front face carries four X-pattern
    gussets that brace it to the tail cone (row 4) and the upper collar (rows 5-6);
  - a thin neck rod (rows 7-8) into a ribbed fuze-well collar (rows 9-13: two raised rings, the
    sprite's bright rows 10 and 12);
  - a rounded shoulder (row 14) into the upper body (rows 15-17), a panel seam at row 15;
  - the red retaining strap (rows 17-18) round the flare where the body steps out, with a bead at
    each edge;
  - the bulb (rows 18-21), a seam where the nose cone joins, the ogive nose (rows 22-24) and a
    blunt fuze stub with a ring groove and a recessed tip (rows 24-25).

Every turned part is as deep as it is wide, and the top-view outline is the sprite's INNER mask
(D74: the game's ink outline adds the sprite's dark border ring). The sprite's dark outline ring,
its darker lower and right-hand pixels and its near-white streaks are lighting on polished steel
(art rule 2): the steel is one satin grey (the region median, index 5) and only the strap is
painted (median 115).

Run: blender --background --python assets/blender/enemies/newsh5-77.py
Exports public/models/enemies/newsh5-77.glb (body + outline shell) and its spriteModels entry.
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = next(p for p in HERE.parents if (p / "package.json").exists())
NAME = "newsh5-77"
MODEL = f"enemies/{NAME}"

U = 1 / 12          # one sprite px in Blender units
AX = 0.5 * U        # the turning axis: sprite column 12's centre (x = col + 0.5 - 12 px)
SIDES = 28          # facets round the axis (a vertex on top, z = +r, and one at each side)
SHARP_DEG = 32      # profile turns sharper than this get a hard edge
STEEL, RED = 5, 115
STEEL_MAT = (0.3, 0.3, 1.8)  # metallic, roughness, Specular IOR Level (D176: F0 ~0.14 gives the polished-steel read; in game mean luma 85 vs the original 82)
STRAP = (16.95, 19.05)  # the strap's span of row edges (s)


# --- The profile (pure python) ----------------------------------------------------------------------
# s: sprite row edge (0 = top of row 0, the tail end; 26 = bottom of row 25, the nose tip); r: radius px.

def pchip(xs, ys, n_per=3):
    """Fritsch-Carlson monotone cubic through the stations; returns the dense (x, y) samples."""
    k = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(k - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(k - 1)]
    m = [0.0] * k
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, k - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    out = []
    for i in range(k - 1):
        for j in range(n_per):
            t = j / n_per
            h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
            h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
            out.append((xs[i] + t * h[i], h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]))
    out.append((xs[-1], ys[-1]))
    return out


def rounded(spec):
    """spec: [(s, r, rad, n)]; each corner with rad > 0 is replaced by a quadratic Bezier between
    setback points rad along each neighbouring segment (n segments: 1 = a chamfer)."""
    out = []
    for i, (s, r, rad, n) in enumerate(spec):
        if rad <= 0 or i == 0 or i == len(spec) - 1:
            out.append((s, r))
            continue
        (sa, ra), (sb, rb) = spec[i - 1][:2], spec[i + 1][:2]
        la, lb = math.hypot(sa - s, ra - r), math.hypot(sb - s, rb - r)
        d = min(rad, 0.45 * la, 0.45 * lb)
        p1 = (s + d * (sa - s) / la, r + d * (ra - r) / la)
        p2 = (s + d * (sb - s) / lb, r + d * (rb - r) / lb)
        for j in range(n + 1):
            t = j / n
            out.append(((1 - t) ** 2 * p1[0] + 2 * (1 - t) * t * s + t * t * p2[0],
                        (1 - t) ** 2 * p1[1] + 2 * (1 - t) * t * r + t * t * p2[1]))
    return out


def profile():
    """The bomb's half section, tail hub on the axis to nose tip on the axis."""
    tail = rounded([
        (1.10, 0.0, 0, 1),          # hub face centre
        (1.10, 1.05, 0.12, 2),      # hub rim
        (1.38, 1.20, 0.08, 2),      # hub side into the dish
        (1.38, 3.60, 0.10, 2),      # dish floor
        (1.00, 4.05, 0.08, 2),      # dish wall up to the back rim face
        (1.00, 5.55, 0.32, 1),      # back rim chamfer
        (2.22, 5.55, 0.10, 1),      # groove lip
        (2.50, 5.02, 0.0, 1),       # V groove root
        (2.78, 5.55, 0.10, 1),      # groove lip
        (4.02, 5.55, 0.28, 1),      # front rim chamfer
        (4.02, 4.40, 0.18, 3),      # front face into the tail cone
        (5.05, 2.55, 0.30, 3),      # cone into the upper collar (concave)
        (6.85, 2.55, 0.20, 1),      # collar front chamfer
        (6.85, 1.45, 0.14, 2),      # into the neck rod
        (9.10, 1.45, 0.14, 2),      # neck into the fuze-well collar
        (9.10, 2.45, 0.20, 1),
        (10.18, 2.45, 0.0, 1),      # rib 1
        (10.30, 2.76, 0.0, 1),
        (10.72, 2.76, 0.0, 1),
        (10.84, 2.45, 0.0, 1),
        (12.18, 2.45, 0.0, 1),      # rib 2
        (12.30, 2.76, 0.0, 1),
        (12.72, 2.76, 0.0, 1),
        (12.84, 2.45, 0.0, 1),
        (13.90, 2.45, 0.0, 1),
    ])
    shoulder = pchip([13.90, 14.15, 14.55, 15.0, 15.45], [2.45, 3.35, 4.05, 4.42, 4.50])[1:]
    body = rounded([
        (15.45, 4.50, 0, 1),
        (15.62, 4.50, 0, 1),        # panel seam (row 15)
        (15.70, 4.36, 0, 1),
        (15.78, 4.50, 0, 1),
        (16.95, 4.50, 0, 1),        # strap: back bead
        (16.95, 4.63, 0, 1),
        (17.15, 4.63, 0, 1),
        (17.15, 4.57, 0, 1),
        (17.42, 4.57, 0.22, 3),     # the flare under the strap
        (18.02, 5.55, 0.22, 3),
        (18.85, 5.55, 0, 1),        # front bead
        (18.85, 5.66, 0, 1),
        (19.05, 5.66, 0, 1),
        (19.05, 5.48, 0, 1),
        (21.58, 5.48, 0, 1),        # nose-cone seam
        (21.66, 5.34, 0, 1),
        (21.74, 5.48, 0, 1),
    ])
    nose = pchip([21.74, 22.4, 23.1, 23.8, 24.35, 24.62], [5.48, 5.12, 4.35, 3.35, 2.55, 2.15])[1:]
    tip = rounded([
        (24.62, 2.15, 0, 1),
        (24.66, 1.78, 0.04, 1),     # step down to the fuze stub
        (25.14, 1.78, 0, 1),        # ring groove
        (25.22, 1.58, 0, 1),
        (25.30, 1.78, 0, 1),
        (25.80, 1.78, 0.30, 3),     # rounded nose of the stub
        (26.00, 1.00, 0.10, 2),
        (26.00, 0.55, 0.05, 1),     # tip recess
        (25.90, 0.45, 0.05, 1),
        (25.90, 0.0, 0, 1),
    ])
    pts = tail + shoulder + body + nose + tip
    clean = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 1e-4:
            clean.append(p)
    return clean


# --- Blender ----------------------------------------------------------------------------------------

def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def ypos(s):
    return (14.0 - s) * U


def turn(bm, prof, mat_of):
    """Revolve the profile round the Y axis (x = AX): rings of SIDES verts, poles at the axis."""
    rings = []
    for s, r in prof:
        if r < 1e-6:
            rings.append([bm.verts.new((AX, ypos(s), 0.0))])
        else:
            rings.append([bm.verts.new((AX + r * U * math.cos(a), ypos(s), r * U * math.sin(a)))
                          for a in (math.pi / 2 + 2 * math.pi * i / SIDES for i in range(SIDES))])
    faces = []
    for k in range(len(rings) - 1):
        r0, r1 = rings[k], rings[k + 1]
        mi = mat_of(prof[k][0], prof[k + 1][0])
        for i in range(SIDES):
            j = (i + 1) % SIDES
            if len(r0) == 1:
                vs = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                vs = (r0[i], r0[j], r1[0])
            else:
                vs = (r0[i], r0[j], r1[j], r1[i])
            f = bm.faces.new(vs)
            f.material_index = mi
            f.smooth = True
            faces.append(f)
    return rings


def gussets(bm, mi):
    """Four X-pattern gussets on the drum's front face, bracing it to the tail cone and collar."""
    import bmesh  # noqa: F401
    t = 0.32  # px thick
    # the gusset's side outline in (s, r): drum front face down the cone to the collar
    outline = [(4.02, 2.0), (4.02, 4.55), (4.35, 4.35), (5.35, 2.65), (5.9, 2.5), (5.9, 2.0)]
    for q in range(4):
        a = math.pi / 4 + q * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        nx, nz = -sa, ca  # plate normal (tangential)
        vs = []
        for side in (-t / 2, t / 2):
            for s, r in outline:
                vs.append(bm.verts.new((AX + (r * ca + side * nx) * U, ypos(s), (r * sa + side * nz) * U)))
        n = len(outline)
        fs = [bm.faces.new(vs[:n][::-1]), bm.faces.new(vs[n:])]
        for i in range(n):
            j = (i + 1) % n
            fs.append(bm.faces.new((vs[i], vs[j], vs[n + j], vs[n + i])))
        for f in fs:
            f.material_index = mi
            f.smooth = False


def bolts(bm, mi):
    """Six hex bolt heads on the back rim face (facing +Y, up the screen)."""
    rb, hgt, rad = 4.78, 0.22, 0.32
    for q in range(6):
        a = math.pi / 2 + q * math.pi / 3 + math.pi / 6
        cx, cz = AX + rb * U * math.cos(a), rb * U * math.sin(a)
        y0, y1 = ypos(1.0) - 0.02 * U, ypos(1.0 - hgt)
        lo = [bm.verts.new((cx + rad * U * math.cos(b), y0, cz + rad * U * math.sin(b)))
              for b in (k * math.pi / 3 for k in range(6))]
        hi = [bm.verts.new((cx + rad * U * 0.85 * math.cos(b), y1, cz + rad * U * 0.85 * math.sin(b)))
              for b in (k * math.pi / 3 for k in range(6))]
        fs = [bm.faces.new(lo), bm.faces.new(hi[::-1])]
        for i in range(6):
            j = (i + 1) % 6
            fs.append(bm.faces.new((lo[i], hi[i], hi[j], lo[j])))
        for f in fs:
            f.material_index = mi
            f.smooth = False


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
    mats = [spec(common.palette_material(sprite, STEEL, NAME, metallic=STEEL_MAT[0],
                                         roughness=STEEL_MAT[1]), STEEL_MAT[2]),
            spec(common.palette_material(sprite, RED, NAME, metallic=0.1, roughness=0.5), 0.5)]

    prof = profile()

    def mat_of(s0, s1):
        return 1 if STRAP[0] - 1e-6 <= min(s0, s1) and max(s0, s1) <= STRAP[1] + 1e-6 else 0

    bm = bmesh.new()
    turn(bm, prof, mat_of)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    body = bpy.data.meshes.new(NAME + "_body")
    bm.to_mesh(body)
    bm.free()

    # Sealed pre-cull copy for the outline shell: the closed turned body plus the gussets (they touch
    # it and fill the same silhouette); bolts are sub-pixel and get no ink of their own.
    bm = bmesh.new()
    bm.from_mesh(body)
    gussets(bm, 0)
    bolts(bm, 0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    mesh.set_sharp_from_angle(angle=math.radians(SHARP_DEG))
    bpy.context.view_layer.update()
    shell = common.outline_shell(obj, coll, voxel=0.007, faces=2400, smooth=4, inside=0.002, islands="outer")
    assert len(shell.data.polygons) > 0, "empty outline shell"
    mesh.calc_loop_triangles()
    tris = len(mesh.loop_triangles)
    for o in (obj, shell):
        o["design_model"] = NAME
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"], image_format="AUTO")
    print("tris", tris, "shell_faces", len(shell.data.polygons))


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
        build()
    except ImportError:
        print(len(profile()), "profile points")
