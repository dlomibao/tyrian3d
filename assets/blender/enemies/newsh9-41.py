"""Grey ground emplacement (newsh9.shp frame 41), a 3D version of its sprite.

What it is: a fixed dart-launching ground turret (e4:325/326, ground layer, UNDERDELI and LAVA RUN;
armour 30). It launches the newsh-caret-171 darts forward (down the screen). Built as a squat
armoured emplacement:
  - a horseshoe armour cowl: a low skirt wall, a sloped glacis and a rounded crest that runs down
    the left flank, round the front and up the right flank (the sprite's bright 108-111 arc is light
    on that crest, not paint);
  - inside the horseshoe a recessed deck carrying the launcher: a ribbed central column (the launch
    rail housing, its segment joint the dark 102 band at row 12) slung between two dark trunnion
    drums (cols 4-7 and 16-19) with hubbed outer ends;
  - a vaulted rear housing (rows 3-7) with a V cradle cut into its back, holding a dark domed cap
    (the knob, rows 2-4);
  - a glowing red core bulging out of the front glacis (rows 19-25): a crimson lens bulb (pal 244)
    with a hot centre (pal 248, the 247-253 cluster).

Reading the 24x28 sprite (one frame): a closed 1 px ink ring, so the top view goes to the INNER mask
(D74). Colours (region medians, the darkest and brightest steps left out as lighting): hull,
column and housing 105; drums 4-5 (pal 5); knob 6; core 243-244; hot centre 248.
Underside: flat and closed (everything stands on z = 0).

Run: blender --background --python assets/blender/enemies/newsh9-41.py [-- --preview out.png]
"""

import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

NAME = "newsh9-41"
MODEL = f"enemies/{NAME}"
WT = common.repo_root(__file__)
P = 1 / 12  # one sprite px in Blender units

# material slots: (palette index, metallic, roughness, specular IOR level, emission)
MATS = [
    (105, 0.55, 0.40, 0.55, 0.0),   # 0 hull cowl
    (105, 0.60, 0.32, 0.65, 0.0),   # 1 column / housing (machined, a bit more polished)
    (102, 0.50, 0.50, 0.45, 0.0),   # 2 seams and grooves
    (4, 0.6, 0.30, 0.55, 0.0),      # 3 trunnion drums
    (6, 0.60, 0.28, 0.65, 0.0),     # 4 knob cap
    (244, 1.0, 0.85, 0.5, 0.95),    # 5 core bulb (glow, D126/D173)
    (248, 1.0, 0.85, 0.5, 1.25),    # 6 hot launch ring
    (104, 0.55, 0.42, 0.5, 0.0),    # 7 deck
    (243, 1.0, 0.9, 0.5, 0.5),      # 8 launch bore (dim)
    (4, 0.6, 0.35, 0.55, 0.0),      # 9 (spare)
    (102, 0.5, 0.42, 0.5, 0.0),     # 10 outer glacis and skirt (that region's own median, 101-102)
    (105, 0.6, 0.24, 1.0, 0.0),     # 11 crest (polished: the sprite's 108-111 arc is sheen on it)
]
HULL, MACH, SEAM, DRUM, KNOB, CORE, HOT, DECK, BORE, COLLAR, GLACIS, CREST = range(len(MATS))


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def sx(c):
    """Sprite column edge -> px X (right +)."""
    return c - 12.0


def sy(r):
    """Sprite row edge -> px Y (sprite up = +Y)."""
    return 14.0 - r


def sse(t, p):
    return math.copysign(abs(t) ** (2.0 / p), t)


# ---------------------------------------------------------------------------------------------
# plan curves (sprite edge coordinates)

# The hull's outer edge, left half from the back corner round to the front centre (the inner mask's
# steps smoothed: x = 2 for rows 10-21, rounded front corners, row 24 behind the core).
HULL_HALF = [(2.15, 9.75), (2.0, 10.6), (2.0, 21.0), (2.2, 22.0), (2.75, 22.85), (3.6, 23.5),
             (4.8, 24.0), (6.4, 24.35), (8.2, 24.6), (10.0, 24.75), (12.0, 24.8)]
HC = (12.0, 9.8)          # centre of the radial loft
CREST_RX, CREST_RY, CREST_P = 9.0, 7.55, 2.25
ZC, ZD = 4.4, 3.2         # crest and deck heights (px)


def hull_outline():
    pts = HULL_HALF + [(24 - c, r) for c, r in reversed(HULL_HALF[:-1])]
    return pts


def ray_outline(poly, c, d):
    """Distance from c along unit d to the polygon (closed list)."""
    best = None
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        ex_, ey_ = bx - ax, by - ay
        den = d[0] * ey_ - d[1] * ex_
        if abs(den) < 1e-9:
            continue
        t = ((ax - c[0]) * ey_ - (ay - c[1]) * ex_) / den
        u = ((ax - c[0]) * d[1] - (ay - c[1]) * d[0]) / den
        if t > 1e-6 and -1e-6 <= u <= 1 + 1e-6:
            best = t if best is None else min(best, t)
    return best


def crest_r(phi):
    """Radius of the crest's superellipse about HC in sprite direction phi (deg; 180 left, 90 front)."""
    a = math.radians(phi)
    c, s = abs(math.cos(a)), abs(math.sin(a))
    return 1.0 / ((c / CREST_RX) ** CREST_P + (s / CREST_RY) ** CREST_P) ** (1.0 / CREST_P)


# ---------------------------------------------------------------------------------------------
# geometry helpers (px space; everything is scaled by P at the end)

def loft(bm, rings, mats, cap0=True, cap1=True):
    import lib_b011 as lib
    n0 = len(bm.faces)
    lib.ring_loft(bm, rings, mats, cap_start=cap0, cap_end=cap1)
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


def hull_section(phi, dip=0.0):
    """Closed (s, z, band material) profile of the cowl along the ray at phi (sprite direction)."""
    a = math.radians(phi)
    d = (math.cos(a), math.sin(a))
    ro = ray_outline(hull_outline(), HC, d)
    rc = crest_r(phi)
    L = ro - rc
    g = GLACIS
    pts = [(rc - 2.0, 0.0, HULL), (ro, 0.0, GLACIS), (ro, 0.75, GLACIS), (ro - 0.22, 1.2, GLACIS)]
    b = (ro - 0.4, 1.38)
    t = (rc + 0.5, ZC - 0.22)
    pts.append((b[0], b[1], g))
    bulge = 0.35 if L > 2.5 else 0.1
    for u in (0.2, 0.42, 0.64, 0.84):
        s = b[0] + (t[0] - b[0]) * u
        z = b[1] + (t[1] - b[1]) * (u + bulge * u * (1 - u))
        pts.append((s, z - dip, g))
    pts += [(t[0], t[1], CREST), (rc, ZC, CREST), (rc - 0.45, ZC - 0.14, HULL), (rc - 0.82, ZD + 0.4, HULL),
            (rc - 1.0, ZD, HULL), (rc - 2.0, ZD, HULL)]
    return pts, d


SEAMS = (148.0, 118.0, 62.0, 32.0)


def build_hull(bm):
    st = [(180 - 5.0 * k, 0.0) for k in range(37) if all(abs(180 - 5.0 * k - s) > 1.8 for s in SEAMS)]
    for s in SEAMS:
        st += [(s + 0.6, 0.0), (s, 0.2), (s - 0.6, 0.0)]
    st.sort(key=lambda q: -q[0])
    rings, mats = [], []
    profs = [hull_section(p, dip) for p, dip in st]
    for prof, d in profs:
        rings.append([(sx(HC[0] + d[0] * s), sy(HC[1] + d[1] * s), z) for s, z, _m in prof])
    n = len(rings[0])
    for k in range(len(st) - 1):
        mats.append([profs[k][0][i][2] for i in range(n)])
    return loft(bm, rings, mats)


def build_deck(bm):
    import lib_b011 as lib
    pts = []
    for k in range(25):
        phi = 180 - 180 * k / 24
        a = math.radians(phi)
        r = crest_r(phi) - 1.4
        pts.append((HC[0] + math.cos(a) * r, HC[1] + math.sin(a) * r))
    pts += [(19.5, 8.4), (4.5, 8.4)]
    outline = [(sx(c), sy(r)) for c, r in pts]
    n0 = len(bm.faces)
    lib.bevel_prism(bm, outline, 0.0, ZD + 0.05, 0.3, mat_index=DECK)
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


def arch_ring(y, w, top, bot, n=20, power=3.2, xc=0.0):
    """A closed section in the XZ plane at Y=y: a superellipse arch of half width w from bot to top."""
    ring = []
    zc = bot
    h = top - bot
    for i in range(n + 1):
        a = math.pi * i / n
        ring.append((xc + w * sse(math.cos(a), power), y, zc + h * sse(math.sin(a), power)))
    # flat bottom closing back (two corner verts under the arch ends)
    return ring


def build_column(bm):
    # (sprite row edge, half width, top z, material)
    st = [(7.4, 2.5, 5.9, MACH), (7.9, 2.85, 6.25, MACH), (8.5, 3.0, 6.45, MACH), (9.9, 3.0, 6.45, MACH),
          (10.05, 2.85, 6.3, SEAM), (10.25, 2.85, 6.3, MACH), (10.4, 3.0, 6.45, MACH),
          (11.75, 3.0, 6.4, MACH), (11.95, 2.55, 5.95, SEAM), (12.85, 2.55, 5.95, SEAM),
          (13.05, 3.0, 6.3, MACH), (14.6, 3.0, 5.95, MACH), (15.7, 2.9, 5.45, MACH), (16.7, 2.7, 4.85, MACH),
          (17.6, 2.35, 4.25, MACH)]
    rings, mats = [], []
    for r, w, top, m in st:
        rings.append(arch_ring(sy(r), w, top, 2.4, n=18, power=3.0))
        mats.append(m)
    return loft(bm, rings, mats[:-1])


def build_housing(bm):
    """Barrel vault, rows 2.9-8.3, cols 6-18, with a V cradle cut into its back for the knob."""
    xs = [-6.0 + 12.0 * i / 22 for i in range(23)]

    xs = [x * 5.72 / 6.0 for x in xs]

    def vault(x):
        u = abs(x) / 5.72
        if u > 0.93:
            return 4.6 + (1 - u) / 0.07 * 0.75
        return 5.35 + 1.7 * (1 - (u / 0.93) ** 2.4) ** 0.6

    rows = [2.85, 3.3, 3.9, 4.5, 5.1, 5.7, 5.95, 6.1, 6.25, 6.5, 7.3, 8.0, 8.35]
    rings, mats = [], []
    for r in rows:
        n = max(0.0, 2.9 * (5.8 - r) / 2.95)      # notch half width at the top
        seam = 6.0 <= r <= 6.2
        ring = [(-6.0, sy(r), 0.0), (-6.0, sy(r), 2.3), (-5.72, sy(r), 2.55)]
        for x in xs:
            z = vault(x)
            if n > 0:
                z = min(z, 5.1 + max(0.0, abs(x) - 0.3 * n) * 1.5)
            if seam and abs(x) < 5.9:
                z -= 0.18
            if r >= 8.0:   # the front edge rounds over
                z -= (r - 7.95) * 1.1
            ring.append((x, sy(r), z))
        ring += [(5.72, sy(r), 2.55), (6.0, sy(r), 2.3), (6.0, sy(r), 0.0)]
        rings.append(ring)
    for k in range(len(rows) - 1):
        seam = 6.0 <= rows[k] <= 6.2 and 6.0 <= rows[k + 1] <= 6.2
        mats.append(SEAM if seam else MACH)
    return loft(bm, rings, mats)


def build_rear_hatch(bm):
    """A bolted access hatch on the housing's back wall, and a louvre band either side."""
    import lib_b011 as lib
    import usp_talon as T
    n0 = len(bm.faces)
    yb = sy(2.85)
    for x0, x1, z0, z1 in ((-3.6, 3.6, 0.9, 3.9),):
        lib.bevel_prism(bm, [(x0, yb - 0.1), (x1, yb - 0.1), (x1, yb + 0.35), (x0, yb + 0.35)], z0, z1, 0.0,
                        mat_index=MACH)
    # louvre slats (thin raised bars) on the back wall either side of the hatch
    for side in (-1, 1):
        for k in range(4):
            z = 1.2 + 0.7 * k
            lib.tube(bm, (side * 4.2, yb + 0.05, z), (side * 5.4, yb + 0.05, z), 0.16, sides=4, mat_index=SEAM)
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


def build_knob(bm):
    import lib_b011 as lib
    n0 = len(bm.faces)
    lib.ellipsoid(bm, (0.0, sy(3.65), 5.5), (2.75, 1.85, 2.1), segments=18, rings=5, mat_index=KNOB)
    # a seat ring under it
    lib.ellipsoid(bm, (0.0, sy(3.75), 5.1), (2.95, 2.0, 0.55), segments=18, rings=2, mat_index=SEAM)
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


def build_drum(bm, side):
    """A trunnion drum (axis along X) beside the column; side -1 left, +1 right."""
    import lib_b011 as lib
    yc, zc = sy(10.85), 4.15
    # (distance from x=0 outward, radius, material)
    R = 2.55
    prof = [(2.55, 2.2, DRUM), (2.85, 2.5, DRUM), (3.05, R, DRUM), (3.35, R, SEAM), (3.45, R - 0.18, SEAM),
            (3.6, R - 0.18, DRUM), (3.7, R, DRUM), (5.0, R, DRUM)]
    for k in range(1, 6):   # a domed outer end
        t = math.radians(16 * k)
        prof.append((5.0 + 1.9 * math.sin(t), 0.8 + (R - 0.8) * math.cos(t) ** 0.8, DRUM))
    prof += [(6.85, 1.3, MACH), (7.3, 1.25, MACH), (7.45, 1.0, MACH), (7.47, 0.0, MACH)]
    segs = 16
    rings, mats = [], []
    for d, r, m in prof:
        x = side * d
        if r <= 0:
            rings.append([(x, yc, zc)])
        else:
            rings.append([(x, yc + r * math.cos(2 * math.pi * (i + 0.5) / segs),
                           zc + r * math.sin(2 * math.pi * (i + 0.5) / segs)) for i in range(segs)])
        mats.append(m)
    if side > 0:
        rings = [list(reversed(rg)) for rg in rings]
    faces = loft(bm, rings, mats[:-1], cap0=True, cap1=False)
    # bolt heads round the hub
    n0 = len(bm.faces)
    from mathutils import Matrix
    rot = Matrix.Rotation(math.radians(90 * side), 3, "Y")
    for k in range(0):
        t = 2 * math.pi * (k + 0.5) / 6
        lib.ellipsoid(bm, (side * 6.95, yc + 1.0 * math.cos(t), zc + 1.0 * math.sin(t)),
                      (0.2, 0.2, 0.12), segments=6, rings=2, mat_index=MACH, rot=rot, top_only=True)
    bm.faces.ensure_lookup_table()
    return faces + list(bm.faces[n0:])


def superellipsoid(bm, centre, radii, pp=3.0, pv=2.3, segs=28, rings=10, mat=0, zmin=0.0):
    cx, cy, cz = centre
    rx, ry, rz = radii
    rl = []
    for k in range(-rings, rings + 1):
        t = (math.pi / 2) * k / rings
        if abs(k) == rings:
            rl.append([(cx, cy, max(zmin, cz + rz * (1 if k > 0 else -1)))])
            continue
        cr, zr = sse(math.cos(t), pv), sse(math.sin(t), pv)
        ring = []
        for i in range(segs):
            a = 2 * math.pi * (i + 0.5) / segs
            ring.append((cx + rx * cr * sse(math.cos(a), pp), cy + ry * cr * sse(math.sin(a), pp),
                         max(zmin, cz + rz * zr)))
        rl.append(ring)
    return loft(bm, rl, mat, cap0=False, cap1=False)


def torus(bm, centre, rx, ry, tube, tz=None, segs=24, sides=8, mat=0, pp=2.0):
    cx, cy, cz = centre
    tz = tube if tz is None else tz
    vs = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        ring = []
        for k in range(sides):
            b = 2 * math.pi * k / sides
            rr = 1 + tube * math.cos(b) / ((rx + ry) / 2)
            ring.append(bm.verts.new((cx + rx * rr * sse(math.cos(a), pp), cy + ry * rr * sse(math.sin(a), pp), cz + tz * math.sin(b))))
        vs.append(ring)
    n0 = len(bm.faces)
    for i in range(segs):
        r0, r1 = vs[i], vs[(i + 1) % segs]
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r1[k], r1[j], r0[j])).material_index = mat
    bm.faces.ensure_lookup_table()
    return list(bm.faces[n0:])


CORE_C, CORE_R = (0.0, sy(22.35), 2.3), (4.15, 3.72, 3.05)


def build_core(bm):
    import lib_b011 as lib
    f = superellipsoid(bm, CORE_C, CORE_R, pp=3.1, pv=2.2, segs=24, rings=8, mat=CORE)
    # a retaining collar hugging the bulb above its equator (inside its plan)
    # the socket lip the bulb sits in (hull steel), low round its waist
    f += torus(bm, (0.0, CORE_C[1], 0.95), CORE_R[0] * 0.95, CORE_R[1] * 0.95, 0.42, tz=0.5, segs=32, sides=8,
               mat=GLACIS, pp=3.1)
    # the launch port on top: a glowing ring round a dim bore
    top = CORE_C[2] + CORE_R[2]
    f += torus(bm, (0.0, sy(22.0), top - 0.3), 1.55, 1.42, 0.6, tz=0.38, segs=20, sides=8, mat=HOT)
    n0 = len(bm.faces)
    lib.ellipsoid(bm, (0.0, sy(22.0), top - 0.42), (1.1, 1.0, 0.3), segments=16, rings=3, mat_index=BORE)
    bm.faces.ensure_lookup_table()
    return f + list(bm.faces[n0:])


def build_geometry(bm, sealed=False):
    smooth, flat = [], []
    smooth += build_hull(bm)
    flat += build_deck(bm)
    smooth += build_column(bm)
    smooth += build_housing(bm)
    smooth += build_knob(bm)
    flat += build_rear_hatch(bm)
    for side in (-1, 1):
        smooth += build_drum(bm, side)
    smooth += build_core(bm)
    return smooth, flat


def build():
    import bmesh
    import bpy
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    mats = []
    for k, (idx, met, rough, lvl, em) in enumerate(MATS):
        m = common.palette_material(sprite, idx, f"{NAME}_{k}", metallic=met, roughness=rough, emission_strength=em)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = lvl
        mats.append(m)

    def make(sealed):
        bm = bmesh.new()
        smooth, flat = build_geometry(bm, sealed)
        for v in bm.verts:
            v.co *= P
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in smooth:
            f.smooth = True
        for f in flat:
            f.smooth = False
        return bm

    bm = make(False)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    # auto-smooth-like: split hard creases so chamfers stay crisp
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    try:
        mod = obj.modifiers.new("smooth_by_angle", "NODES")
        obj.modifiers.remove(mod)
    except Exception:
        pass
    try:
        mesh.set_sharp_from_angle(angle=math.radians(40))
    except Exception:
        pass

    bm = make(True)
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
    manifest = {"tris": len(mesh.loop_triangles), "shell_faces": len(shell.data.polygons),
                "bbox_z_px": max(v.co.z for v in mesh.vertices) / P}
    objs = [obj, shell]
    common.export_sprite_model(WT, objs, MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        ref = WT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], arg("--preview"), ref, size=sprite["frames"][0]["size"])
    print("MANIFEST", json.dumps({NAME: manifest}))


if __name__ == "__main__":
    build()
