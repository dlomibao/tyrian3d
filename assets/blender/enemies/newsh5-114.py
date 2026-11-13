"""Green energy arrow (newsh5.shp frames 114, 228, 266)

What it is: a fast glowing bolt, not a craft (type 349, armour 0, never launched; spawned in
pairs on the top layer in EYESPY 4.20 and DREAD-NOT 4.18 and driven up the screen at (0,-8)).
The sprite is an arrow pointing right, the exact mirror twin of newsh5-95:

  - a round shaft 3 px across (rows 5-7, columns 0-7): a green containment sheath (199) with a
    1 px slot along its crest through which the white-hot core rod (47) shows as row 6's white
    stripe. The sheath's tail is a closed, chamfered end cap (column 0) and the core's tail tip
    glows the brighter green (207, column 1). Two shallow ring grooves (panel seams) break the
    sheath's length; the underside is plain.
  - a faceted blade head (columns 7-11, rows 3-9): a stepped bipyramid with a thin vertical
    knife rim on the sprite's outline, a chamfer, the green outer facets (199), the bright green
    chevron facets (207), the white cross (47: (8,5), (8,7), (9,6)) and its hot centre (8,6) under
    the peak. The shaft plunges into the head's back slope, so its slot and core run on to
    column 7 as in the sprite.

The frames only fade it (same pixels, dimmer greens), so one model covers all three; each part's
material steps down with palette_material frames=, read pixel by pixel from the three frames:

  part     114   228   266
  sheath   199   196   192
  chevron  207   204   200   (and the core's tail tip, column 1)
  core      47   204   200   (shaft stripe, columns 2-7)
  arms      47   207   203   (the cross's arms, (8,5) (8,7) (9,6))
  centre    47    47   205   (the cross's centre, (8,6))

Glow surfaces are metallic 1 / rough (D126, D173). The sprite has no ink border, so the top view
covers every opaque pixel (D74 inner = outer).

Run: blender --background --python assets/blender/enemies/newsh5-114.py [-- --preview out.png]
"""


import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
NAME = "newsh5-114"
MODEL = f"enemies/{NAME}"

U = 1 / 12      # one sprite px in Blender units
W, H = 12, 14   # the sprite
AXIS = 6.5      # the arrow's axis, a row-edge coordinate (row 6's centre)

# Materials: (key, index on frame 114, {frame: index}, emission strength)
MATS = [
    ("sheath", 199, {228: 196, 266: 192}, 0.95),
    ("chevron", 207, {228: 204, 266: 200}, 1.05),
    ("core", 47, {228: 204, 266: 200}, 1.25),
    ("arms", 47, {228: 207, 266: 203}, 1.25),
    ("centre", 47, {228: 47, 266: 205}, 1.4),
]
SHEATH, CHEV, CORE, ARMS, CENTRE = range(len(MATS))
METAL, ROUGH = 1.0, 0.85


def arg(name, default=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return argv[argv.index(name) + 1] if name in argv else default


def P(c, r, z):
    """Sprite coordinates (column edge, row edge, height in px) to Blender."""
    return ((c - W / 2) * U, (H / 2 - r) * U, z * U)


# --- Head ------------------------------------------------------------------------------------------
# Each ring: the tip, four points down the upper flank from front to back, the back point on the
# axis, then the upper four mirrored about the axis (lower flank, back to front). Points are
# (column edge, row edge, height px).

def mirror_ring(tip, upper, back):
    lower = [(c, 2 * AXIS - r, z) for c, r, z in upper]
    return [tip] + upper + [back] + lower[::-1]


# The outline's leading edge: x = row + LEAD (through the sprite's stair steps, a little outside
# their midline so each stair pixel is well covered and none beyond it is).
LEAD = 5.62
TIP = 12.18
RIM_Z = 0.28      # half height of the knife rim
CHAMF_Z = 0.62    # top of the rim's chamfer
Z1, Z2, Z3, ZA = 1.62, 2.3, 2.78, 2.98  # chevron, cross, centre rings, peak
ZB = -2.55        # underside peak


def head_rings():
    rim = mirror_ring((TIP, AXIS, RIM_Z),
                      [(3.0 + LEAD + 1.75, 4.75, RIM_Z), (3.0 + LEAD, 3.0, RIM_Z), (7.0, 3.0, RIM_Z), (7.0, 5.0, RIM_Z)],
                      (7.0, AXIS, RIM_Z))
    # Chamfer: the rim ring drawn 0.22 px in, toward the head's centre.
    cx, cy = 8.6, AXIS

    def inset(pt, d=0.22):
        c, r, _ = pt
        dx, dy = c - cx, r - cy
        n = math.hypot(dx, dy) or 1.0
        return (c - d * dx / n, r - d * dy / n, CHAMF_Z)
    # Back points stay on the back face (x = 7) so it stays one plane.
    chamf = [inset(p) for p in rim]
    for i, p in enumerate(rim):
        if p[0] == 7.0:
            chamf[i] = (7.0, cy + (p[1] - cy) * 0.94, CHAMF_Z)
    chev = mirror_ring((11.0, AXIS, Z1), [(9.5, 5.0, Z1), (8.5, 4.0, Z1), (8.0, 4.0, Z1), (8.0, 5.0, Z1)],
                       (7.9, AXIS, Z1 - 0.3))
    cross = mirror_ring((10.0, AXIS, Z2), [(9.0, 6.0, Z2), (9.0, 5.0, Z2), (8.0, 5.0, Z2), (7.95, 6.0, Z2)],
                        (7.95, AXIS, Z2 - 0.1))
    centre = mirror_ring((9.0, AXIS, Z3), [(9.0, 6.0, Z3), (8.9, 6.0, Z3), (8.1, 6.0, Z3), (8.0, 6.0, Z3)],
                         (8.0, AXIS, Z3))
    return rim, chamf, chev, cross, centre


def build_head(bm):
    rim, chamf, chev, cross, centre = head_rings()
    rings = [rim, chamf, chev, cross, centre]
    mats = [SHEATH, SHEATH, CHEV, ARMS, CENTRE]  # band k runs from ring k to ring k+1 (last: to the peak)
    vr = [[bm.verts.new(P(*p)) for p in rg] for rg in rings]
    rim_lo = [bm.verts.new(P(c, r, -RIM_Z)) for c, r, _ in rim]
    peak = bm.verts.new(P(8.5, AXIS, ZA))
    under = bm.verts.new(P(8.6, AXIS, ZB))
    n = len(rim)
    out = []
    for k in range(len(rings) - 1):
        a, b = vr[k], vr[k + 1]
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((a[i], a[j], b[j], b[i]))
            f.material_index = mats[k]
            out.append(f)
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((vr[-1][i], vr[-1][j], peak))
        f.material_index = CENTRE
        out.append(f)
        # Knife rim: a vertical band on the outline.
        f = bm.faces.new((rim_lo[i], rim_lo[j], vr[0][j], vr[0][i]))
        f.material_index = SHEATH
        out.append(f)
        # Underside: a plain pyramid.
        f = bm.faces.new((rim_lo[j], rim_lo[i], under))
        f.material_index = SHEATH
        out.append(f)
    for f in out:
        f.smooth = False
    return out


# --- Shaft -----------------------------------------------------------------------------------------
R = 1.5          # sheath radius, px
R_IN = 1.12      # sheath bore
R_CORE = 1.45    # core rib crown (stands just proud of the slot's lips, z 1.41)
CORE_HW, CORE_SIDE = 0.56, 1.12  # core rib half width and edge height
SLOT = 0.5       # half width of the crest slot (row 6 exactly)
GROOVES = (3.0, 5.0)  # ring seams, column edges
X_TAIL, X_SLOT, X_END = 0.0, 1.0, 7.9


def sheath_section(r, n_arc=34):
    """A C section (y px off the axis, z px) open at the crest: outer arc from the slot's lip round
    through the bottom to the other lip, then the bore back. Lips at y = +-SLOT exactly."""
    a0 = math.asin(SLOT / r)
    ai = math.asin(SLOT / R_IN)
    outer = [(r * math.sin(a), r * math.cos(a)) for a in
             (a0 + (2 * math.pi - 2 * a0) * t / n_arc for t in range(n_arc + 1))]
    inner = [(R_IN * math.sin(a), R_IN * math.cos(a)) for a in
             (2 * math.pi - ai - (2 * math.pi - 2 * ai) * t / 8 for t in range(9))]
    return outer + inner


def loft_sections(bm, stations, section, mat, closed=True, cap=True):
    """stations: [(column edge, section arg)]; section(arg) -> [(dy, z)]; lofted along +x."""
    rings = []
    for c, s in stations:
        rings.append([bm.verts.new(P(c, AXIS + dy, z)) for dy, z in section(s)])
    faces = []
    m = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(m if closed else m - 1):
            j = (i + 1) % m
            faces.append(bm.faces.new((a[i], b[i], b[j], a[j])))
    if cap:
        faces.append(bm.faces.new(rings[0][::-1]))
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
    return faces, rings


def core_section(k, n=14):
    """The core rib (y px, z px): a 1.1 px wide bar standing in the sheath's bore, its crown domed
    from CORE_SIDE at its edges to R_CORE * k on the axis (k < 1 tapers the tail tip). It stays
    under the ring grooves and inside the bore; only the crown shows, in the slot."""
    pts = []
    for i in range(n + 1):
        y = CORE_HW * (1 - 2 * i / n)
        pts.append((y, CORE_SIDE * k + (R_CORE * k - CORE_SIDE * k) * (1 - (y / CORE_HW) ** 2)))
    return pts + [(-CORE_HW, 0.0), (CORE_HW, 0.0)]


def circle(r, n=20, phase=0.0):
    return [(r * math.sin(2 * math.pi * (i + phase) / n), r * math.cos(2 * math.pi * (i + phase) / n)) for i in range(n)]


def build_shaft(bm):
    # Tail cap: closed, a chamfered end at column 0 running into the slotted sheath at column 1.
    # Its end face is an emitter: a 0.2 px deep recess (0.85 px radius) holding a glowing nozzle
    # in the chevron green, seen only from behind.
    tail, _ = loft_sections(bm, [(X_TAIL + 0.2, 0.85), (X_TAIL, 0.85), (X_TAIL, 1.22), (X_TAIL + 0.28, R),
                                 (X_SLOT + 0.06, R)], lambda r: circle(r, 36, 0.5), SHEATH)
    nozzle, _ = loft_sections(bm, [(X_TAIL + 0.3, 0.72), (X_TAIL + 0.12, 0.62), (X_TAIL + 0.05, 0.3)],
                              lambda r: circle(r, 24, 0.5), CHEV)
    for f in nozzle:
        f.smooth = True
    # Slotted sheath with two ring grooves.
    st = [(X_SLOT, R)]
    for g in GROOVES:
        st += [(g - 0.14, R), (g - 0.06, R - 0.13), (g + 0.06, R - 0.13), (g + 0.14, R)]
    st += [(X_END, R)]
    sheath, _ = loft_sections(bm, st, sheath_section, SHEATH)
    # Core rod: chevron-green tail tip (column 1), white from column 2 into the head.
    tip, _ = loft_sections(bm, [(X_SLOT - 0.02, 0.8), (X_SLOT + 0.3, 1.0), (2.0, 1.0)], core_section, CHEV)
    core, _ = loft_sections(bm, [(2.0, 1.0), (X_END + 0.05, 1.0)], core_section, CORE)
    for f in tail + sheath:
        f.smooth = True
    for f in tip + core:
        f.smooth = True
    # Hard edges: caps and the chamfer ring stay flat-shaded.
    for f in tail[-2:] + sheath[-2:] + tip[-2:] + core[-2:]:
        f.smooth = False


def spec(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level
    return mat


def build():
    import bmesh
    import bpy
    import common
    root = common.repo_root(__file__)

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(root, NAME)
    coll = common.reset_collection(NAME)
    mats = [spec(common.palette_material(sprite, idx, f"{NAME}-{key}", frames=fr, metallic=METAL,
                                         roughness=ROUGH, emission_strength=float(arg(f"--e-{key}", e))), 0.5)
            for key, idx, fr, e in MATS]

    bm = bmesh.new()
    build_head(bm)
    build_shaft(bm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    bpy.context.view_layer.update()
    # The outline shell from a sealed copy: the head plus the shaft as a plain round rod (no slot,
    # no grooves), so the ink stays on the silhouette and never in the core's slot. Every part
    # overlaps (one island), but "outer" keeps anything that stands free (D189).
    bm = bmesh.new()
    build_head(bm)
    loft_sections(bm, [(X_TAIL, 1.22), (X_TAIL + 0.28, R), (X_END, R)], lambda r: circle(r, 36, 0.5), SHEATH)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    seal_me = bpy.data.meshes.new(NAME + "_seal")
    bm.to_mesh(seal_me)
    bm.free()
    seal = bpy.data.objects.new(NAME + "_seal", seal_me)
    coll.objects.link(seal)
    bpy.context.view_layer.update()
    shell = common.outline_shell(seal, coll, voxel=0.006, faces=1600, smooth=4, inside=0.002, islands="outer")
    bpy.data.objects.remove(seal, do_unlink=True)
    shell.name = f"{NAME}_outline"
    assert len(shell.data.polygons) > 0, "empty outline shell"
    mesh.calc_loop_triangles()
    tris = len(mesh.loop_triangles)
    common.export_sprite_model(root, [obj, shell], MODEL, sprite["sprites"])
    prev = arg("--preview")
    if prev:
        import lib_b013 as lib
        lib.preview(root, [obj], sprite)
    print(f"{NAME}: {tris} tris, outline shell {len(shell.data.polygons)} faces")


if __name__ == "__main__":
    build()
