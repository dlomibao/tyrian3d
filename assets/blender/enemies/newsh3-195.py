"""Domed ring (newsh3.shp frame 195): a 3D version of its sprite.

What it is: a small flying drone (armour 4-30, flies down the screen) built round a thick steel
ring. Seen from above, as the sprite draws it:

  - the ring: a machined steel annulus with a chamfered, rounded-rectangle section. It is widest
    along its north arc (the hub that carries the dome; its inner chamfer is the dark slope the
    sprite shows inside the hole, rows 12-14), slim along its sides (2 px of colour) and heavy again
    along its south arc. Its plan follows the sprite's inner mask all round (a ray cast from the
    hole's centre, smoothed periodically), so the hole keeps the hub's lobe hanging into it.
    Modelled panel lines: one concentric deck groove on the wide arcs and radial seams that split
    the ring into machined segments.
  - the dome: a glossy red canopy dome (pal 70, the median of its pixels) on a steel pod that juts
    north off the hub, rows 2-7; its crown sits forward so its back dips under the hub's deck by
    row 8, as the sprite shows grey there.
  - two red lamps (pal 71) set right through the slim side arcs (columns 3-4 / 20-21, rows 13-15),
    lenses flush with both walls, so they read from the sides too.
  - the emitter: a steel housing (pal 7) on the south arc, standing proud of the lobes either side
    (the sprite's slots at columns 8 and 16), with a red glowing barrel lens (pal 70) along it,
    columns 11-13 rows 20-23, whose domed muzzle faces the way it flies.

One frame (195). Steel is satin (metallic 0.6, roughness ~0.38, F0 via Specular IOR Level, D176);
the lamps and emitter glow (metallic 1 / rough, D126/D173). Shading and the sprite's highlights are
lighting, not paint: one steel colour per part. The outline shell comes from a sealed copy (no
grooves or seams) with islands="outer" (D189).

Run: blender --background --python assets/blender/enemies/newsh3-195.py
Writes public/models/enemies/newsh3-195.glb and src/render/spriteModels/newsh3-195.json only.
With -- --out X.glb it also exports a copy there (for review).
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = next(p for p in HERE.parents if (p / "package.json").exists())
NAME = "newsh3-195"
W, H = 24, 28
U = 1 / 12

# Ring plan: ray cast from the hole's centre (pixel-edge col, row).
CX, CY = 12.5, 16.0
N_STATIONS = 96
SMOOTH = 8
SMOOTH_IN = 16
# Panel seams (degrees, CCW from +X seen from above; 90 = north).
SEAMS = [90 + 34, 90 - 34, 90 + 62, 90 - 62, 160.5, 180.5, -0.5, 19.5, 270 - 30, 270 + 30, 180 + 28, -28]
# The side lamps: ring faces between these angles (columns 3-4 / 20-21, rows 13-15).
LAMPS = [(160.5, 180.5), (-0.5, 19.5)]

# Materials: key -> (palette index, metallic, roughness, emission, specular level)
MATS = [
    ("steel", 6, 0.45, 0.4, 0.0, 0.5),
    ("trim", 7, 0.45, 0.36, 0.0, 0.5),
    ("dome", 70, 0.2, 0.1, 0.0, 0.8),
    ("lamp", 71, 1.0, 0.6, 1.35, 0.5),
    ("emit", 70, 1.0, 0.6, 1.3, 0.5),
]
STEEL, TRIM, DOME, LAMP, EMIT = range(len(MATS))


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def X(c):
    return (c - W / 2) * U


def Y(r):
    return (H / 2 - r) * U


# --- Plan from the sprite ------------------------------------------------------------------------

def inner_mask():
    sys.path.insert(0, str(WT / "tools"))
    import sprite_mask as SM
    idx, colors = SM.load(NAME, ref=WT / "reference" / "models")
    return SM.masks(idx, colors)["inner"]


def radial_profile(inner, n):
    """[(theta, r_in, r_out)] in px from (CX, CY), over the ring's pixels (rows >= 7)."""
    def keep(c, r):
        return 7 <= r < H and 0 <= c < W and inner[r][c]
    out = []
    step = 0.02
    for k in range(n):
        a = 2 * math.pi * k / n
        dx, dy = math.cos(a), -math.sin(a)
        runs, r = [], 0.0
        while r < 16:
            if keep(int(math.floor(CX + dx * r)), int(math.floor(CY + dy * r))):
                if runs and r - runs[-1][1] <= 1.2:
                    runs[-1][1] = r + step
                else:
                    runs.append([r, r + step])
            r += step
        ri, ro = max(runs, key=lambda u: u[1] - u[0])
        out.append([a, ri, ro])
    for k in range(max(SMOOTH, SMOOTH_IN)):
        out = [[a, (out[i - 1][1] + 2 * ri + out[(i + 1) % n][1]) / 4 if k < SMOOTH_IN else ri,
                (out[i - 1][2] + 2 * ro + out[(i + 1) % n][2]) / 4 if k < SMOOTH else ro]
               for i, (a, ri, ro) in enumerate(out)]
    return out


def sample_profile(prof, a):
    n = len(prof)
    t = (a % (2 * math.pi)) / (2 * math.pi) * n
    i = int(math.floor(t)) % n
    f = t - math.floor(t)
    j = (i + 1) % n
    return (prof[i][1] * (1 - f) + prof[j][1] * f, prof[i][2] * (1 - f) + prof[j][2] * f)


def half_height(a):
    s = math.sin(a)
    return 0.105 + 0.045 * max(0.0, s) ** 2 + 0.02 * max(0.0, -s) ** 2


def section(ri, ro, h, groove=1.0, seam=0.0):
    """Ring section points (r px, z units), inner bottom round to outer bottom, closed by the
    loft. `seam` sinks the whole section (a radial panel line), `groove` scales the deck groove."""
    w = ro - ri
    d = seam
    ri, ro, h = ri + d / U, ro - d / U, h - d
    cb = min(0.5, 0.2 * w)            # bottom chamfer (px)
    ciw = min(1.0, 0.3 * w)           # inner top chamfer: the slope seen in the hole
    cih = 0.4 * h
    co = min(0.55, 0.22 * w)          # outer top chamfer (px)
    coh = co * U * 0.9
    zb = -h * 0.85
    g = ri + 0.58 * w                 # deck groove centre
    gd = 0.012 * groove * max(0.0, min(1.0, (w - 3.0) / 1.5))
    pts = [
        (ri + cb, zb), (ri, zb + cb * U * 0.8),
        (ri, h - cih), (ri + ciw * 0.45, h - cih * 0.25), (ri + ciw, h),
        (g - 0.32, h), (g - 0.14, h - gd), (g + 0.14, h - gd), (g + 0.32, h),
        (ro - co, h), (ro - co * 0.3, h - coh * 0.45), (ro, h - coh),
        (ro, zb + cb * U * 0.8), (ro - cb, zb),
    ]
    return pts


def build_ring(bm, prof, mat, detail=True):
    """Loft the section round the plan. Returns the faces."""
    stations = [2 * math.pi * k / N_STATIONS for k in range(N_STATIONS)]
    seam_of = {}
    if detail:
        for s in SEAMS:
            a = math.radians(s) % (2 * math.pi)
            for off, depth in ((-0.012, 0.0), (-0.004, 0.011), (0.004, 0.011), (0.012, 0.0)):
                b = (a + off) % (2 * math.pi)
                stations.append(b)
                seam_of[b] = depth
        stations.sort()
    rings = []
    for a in stations:
        ri, ro = sample_profile(prof, a)
        h = half_height(a)
        pts = section(ri, ro, h, groove=1.0 if detail else 0.0, seam=seam_of.get(a, 0.0))
        ux, uy = math.cos(a), math.sin(a)
        ring = []
        for r, z in pts:
            ring.append(bm.verts.new((X(CX) + ux * r * U, Y(CY) + uy * r * U, z)))
        rings.append(ring)
    faces = []
    n = len(rings)
    m = len(rings[0])
    for k in range(n):
        r0, r1 = rings[k], rings[(k + 1) % n]
        for i in range(m):
            j = (i + 1) % m
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mat
            if detail is not None:
                cen = f.calc_center_median()
                ang = math.degrees(math.atan2(cen.y - Y(CY), cen.x - X(CX)))
                if i not in (0, m - 2, m - 1) and any(lo <= ang <= hi for lo, hi in LAMPS):
                    f.material_index = LAMP
            faces.append(f)
    return faces


# --- Dome pod ------------------------------------------------------------------------------------

DOME_C = (12.5, 6.6)      # plan centre (px edges)
DOME_RX = 5.45
DOME_RN, DOME_RS = 4.9, 1.3
DOME_N = 2.1               # superellipse exponent of the north half
Z_EQ, DOME_HU, DOME_HL = 0.03, 0.29, 0.13


def dome_plan(phi):
    """Plan radius vector (dx, dy) px at angle phi (CCW, +y north)."""
    c, s = math.cos(phi), math.sin(phi)
    ry = DOME_RN if s >= 0 else DOME_RS
    n = DOME_N if s >= 0 else 2.0
    # superellipse |x/rx|^n + |y/ry|^n = 1 along the ray
    k = (abs(c / DOME_RX) ** n + abs(s / ry) ** n) ** (-1 / n)
    return c * k, s * k


def build_dome(bm, seg=28, rings_up=8, rings_dn=4, detail=True):
    cx, cy = X(DOME_C[0]), Y(DOME_C[1])
    plan = [dome_plan(2 * math.pi * (i + 0.5) / seg) for i in range(seg)]

    def ring_at(scale, z, sx=1.0):
        return [bm.verts.new((cx + dx * U * scale * sx, cy + dy * U * scale, z)) for dx, dy in plan]
    up = []
    for k in range(rings_up):
        t = (math.pi / 2) * k / rings_up
        up.append(ring_at(math.cos(t) ** 0.9, Z_EQ + DOME_HU * math.sin(t)))
    crown = bm.verts.new((cx, cy + 0.6 * U, Z_EQ + DOME_HU))
    # Steel pod below: a short vertical lip (the collar), then curving in.
    dn = [ring_at(1.0, Z_EQ - 0.004)]
    dn.append(ring_at(1.0, Z_EQ - 0.03))
    for k in range(1, rings_dn + 1):
        t = (math.pi / 2) * k / (rings_dn + 1)
        dn.append(ring_at(math.cos(t) * 0.97, Z_EQ - 0.03 - DOME_HL * math.sin(t)))
    bottom = bm.verts.new((cx, cy, Z_EQ - 0.03 - DOME_HL))
    faces = []

    def band(r0, r1, mat):
        for i in range(seg):
            j = (i + 1) % seg
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mat
            faces.append(f)
    for r0, r1 in zip(up, up[1:]):
        band(r0, r1, DOME)
    for i in range(seg):
        f = bm.faces.new((up[-1][i], up[-1][(i + 1) % seg], crown))
        f.material_index = DOME
        faces.append(f)
    band(dn[0], up[0], TRIM)
    for r0, r1 in zip(dn, dn[1:]):
        band(r1, r0, TRIM)
    for i in range(seg):
        f = bm.faces.new((dn[-1][(i + 1) % seg], dn[-1][i], bottom))
        f.material_index = TRIM
        faces.append(f)
    return faces


# --- Small parts ---------------------------------------------------------------------------------

def ellipsoid(bm, centre, radii, mat, seg=12, rings=6, top_scale=1.0):
    cx, cy, cz = centre
    rx, ry, rz = radii
    verts = []
    for k in range(-rings + 1, rings):
        t = (math.pi / 2) * k / rings
        verts.append([bm.verts.new((cx + rx * math.cos(t) * math.cos(2 * math.pi * (i + 0.5) / seg),
                                    cy + ry * math.cos(t) * math.sin(2 * math.pi * (i + 0.5) / seg),
                                    cz + rz * math.sin(t) * (top_scale if k > 0 else 1.0)))
                      for i in range(seg)])
    top = bm.verts.new((cx, cy, cz + rz * top_scale))
    bot = bm.verts.new((cx, cy, cz - rz))
    faces = []
    for r0, r1 in zip(verts, verts[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for i in range(seg):
        j = (i + 1) % seg
        faces.append(bm.faces.new((verts[-1][i], verts[-1][j], top)))
        faces.append(bm.faces.new((verts[0][j], verts[0][i], bot)))
    for f in faces:
        f.material_index = mat
    return faces


def prism(bm, outline, z0, z1, ch, mat, top_mat=None):
    """A chamfered prism: walls from z0 to z1 - ch, a chamfer band inward by ch to the flat top.
    outline: CCW list of (x, y) units."""
    def inset(pts, d):
        n = len(pts)
        out = []
        for i in range(n):
            p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
            ns = []
            for a, b in ((p0, p1), (p1, p2)):
                ex, ey = b[0] - a[0], b[1] - a[1]
                ln = math.hypot(ex, ey) or 1
                ns.append((-ey / ln, ex / ln))
            nx, ny = ns[0][0] + ns[1][0], ns[0][1] + ns[1][1]
            ln = math.hypot(nx, ny) or 1
            nx, ny = nx / ln, ny / ln
            cos_h = max(0.4, nx * ns[0][0] + ny * ns[0][1])
            out.append((p1[0] + nx * d / cos_h, p1[1] + ny * d / cos_h))
        return out
    lo = [bm.verts.new((x, y, z0)) for x, y in inset(outline, ch * 0.6)]
    lo2 = [bm.verts.new((x, y, z0 + ch * 0.6)) for x, y in outline]
    mid = [bm.verts.new((x, y, z1 - ch)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in inset(outline, ch)]
    faces = [bm.faces.new(list(reversed(lo))), bm.faces.new(hi)]
    n = len(outline)
    for a, b in ((lo, lo2), (lo2, mid), (mid, hi)):
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    for f in faces:
        f.material_index = mat
    if top_mat is not None:
        faces[1].material_index = top_mat
    return faces


HOUSING = [(9.25, 19.9), (15.75, 19.9), (15.75, 22.5), (14.95, 23.85), (10.05, 23.85), (9.25, 22.5)]


def build_housing(bm):
    outline = [(X(c), Y(r)) for c, r in reversed(HOUSING)]  # CCW in Blender (y flips)
    return prism(bm, outline, -0.1, 0.15, 0.03, TRIM)


def build_barrel(bm, sides=14):
    """The emitter: a glowing barrel lens along the housing, its muzzle domed south."""
    cx, cz, rad = X(12.5), 0.085, 1.38 * U
    y0, y1 = Y(20.1), Y(23.6)
    rings = []
    for y, s in ((y0, 0.75), (y0 - 0.02, 1.0), (y1, 1.0), (y1 - 0.025, 0.72), (y1 - 0.038, 0.3)):
        rings.append([bm.verts.new((cx + rad * s * math.cos(2 * math.pi * (i + 0.5) / sides), y,
                                    cz + rad * s * math.sin(2 * math.pi * (i + 0.5) / sides)))
                      for i in range(sides)])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = EMIT
    return faces


def build_lamps(bm):
    out = []
    for c in (4.0, 21.0):
        out += ellipsoid(bm, (X(c), Y(14.5), 0.02), (0.98 * U, 1.55 * U, 0.105), LAMP, seg=14, rings=5)
    return out


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
    prof = radial_profile(inner_mask(), 180)

    def make(detail):
        bm = bmesh.new()
        build_ring(bm, prof, STEEL, detail=detail)
        build_dome(bm)
        build_housing(bm)
        build_barrel(bm)
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
    es.split_angle = math.radians(32)
    es.use_edge_sharp = False
    bpy.context.view_layer.update()

    bm = make(False)
    seal_me = bpy.data.meshes.new(NAME + "_seal")
    bm.to_mesh(seal_me)
    bm.free()
    seal = bpy.data.objects.new(NAME + "_seal", seal_me)
    coll.objects.link(seal)
    bpy.context.view_layer.update()
    shell = common.outline_shell(seal, coll, voxel=0.007, faces=2400, smooth=4, inside=0.002, islands="outer")
    bpy.data.objects.remove(seal, do_unlink=True)
    shell.name = f"{NAME}_outline"
    assert len(shell.data.polygons) > 0, "empty outline shell"
    mesh.calc_loop_triangles()
    tris = len(mesh.loop_triangles)
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])
    out = arg("--out")
    if out:
        common.export_glb([obj, shell], Path(out))
    print("MANIFEST", json.dumps({NAME: {"frames": [195], "tris": tris,
                                         "shell_faces": len(shell.data.polygons)}}))


if __name__ == "__main__":
    build()
