"""Purple weaving drone (newsh^.shp frame 68).

What it is: a small swarm drone, not a ground turret. Armour 6; 68 spawns in UNDERDELI 4.7
(harness main=14): 54 on ground2 from x 20/240 weaving down the screen (ev20, x 0..+-6) and out
of the bottom, 14 more on the ground layer. It flies nose first, down the screen, so the sprite's
cone is its nose. Read from the sprite (12 x 14, one frame, closed ink border):

  - hull (rows 1-7): a faired pod, wide and flat, rounded at the rear (top of the screen) and
    necking in at row 7 to the collar. Satin purple 85.
  - side lobes (columns 2-3 and 9-10, rows 3-6): two thruster nacelles faired into the hull's
    flanks, with dark exhaust nozzles at their rear ends. Darker purple 84.
  - dorsal block (columns 4-8, rows 1-5): a raised sensor housing, chamfered, the bright 89.
    On its deck an inverted U of green lights (columns 5-7, rows 2-4: 195 / 198 / 193): a glowing
    lens strip set into the deck. Louvred side vents.
  - collar (row 8): a polished flange ring, 92 (the sprite's 92/93 is sheen on it).
  - nose cone (rows 9-13): an ogive along the flight axis, 86, two machined ring seams and a
    darker sensor tip, 84.

The ink ring is the game's outline (D74): the top view stops at the inner edge of the border.
Highlights are sheen, the dark row 6 under the block is shadow (art rule 2).

Run: blender --background --python assets/blender/enemies/newsh-caret-68.py [-- --preview out.png]
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] if (HERE.parents[1] / "assets" / "blender" / "common.py").exists() else HERE.parents[2]
NAME = "newsh-caret-68"
MODEL = f"enemies/{NAME}"
sys.path.insert(0, str(ROOT / "assets" / "blender"))

U = 1 / 12      # one sprite px in Blender units
W, H = 12, 14   # the sprite
CX = 6.5        # the model's centre line (column edge): the inner mask is columns 2-10
ZA = 1.0        # the flight axis height (px): nose cone and collar centre
ZB_TOP = 4.3    # the dorsal block's deck (px)

# Materials: (key, palette index, metallic, roughness, emission)
MATS = [
    ("hull", 85, 0.4, 0.42, 0.0),
    ("lobe", 84, 0.4, 0.45, 0.0),
    ("block", 89, 0.45, 0.4, 0.0),
    ("collar", 92, 0.7, 0.4, 0.0),
    ("cone", 86, 0.45, 0.38, 0.0),
    ("tip", 84, 0.45, 0.42, 0.0),
    ("dark", 82, 0.5, 0.55, 0.0),
    ("light", 195, 1.0, 0.85, 1.7),
]
HULL, LOBE, BLOCK, COLLAR, CONE, TIP, DARK, LIGHT = range(len(MATS))


def arg(name, default=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return argv[argv.index(name) + 1] if name in argv else default


def P(c, r, z):
    """Sprite coordinates (column edge, row edge, height px) to Blender (+y up the screen)."""
    return ((c - W / 2) * U, (H / 2 - r) * U, z * U)


# --- Lofting ---------------------------------------------------------------------------------------

def superellipse(n_pts, a, zt, zb, nt, nb, x0=0.0):
    """A closed section round the y axis: half width a, top zt, bottom zb, the top half's exponent
    nt and the bottom's nb (2 = ellipse, higher = squarer, a faired chamfer). Starts at the top."""
    zc = 0.5 * (zt + zb)
    bt, bb = zt - zc, zc - zb
    pts = []
    for i in range(n_pts):
        t = 2 * math.pi * i / n_pts
        s, c = math.sin(t), math.cos(t)
        n = nt if c >= 0 else nb
        b = bt if c >= 0 else bb
        x = a * math.copysign(abs(s) ** (2 / n), s)
        z = zc + b * math.copysign(abs(c) ** (2 / n), c)
        pts.append((x0 + x, z))
    return pts


def loft(bm, rows, section, mat, cap0=True, cap1=True, smooth=True, cx=CX):
    """rows: row-edge stations; section(r) -> [(dx px, z px)]; lofted down the screen (+r)."""
    rings = [[bm.verts.new(P(cx + dx, r, z)) for dx, z in section(r)] for r in rows]
    faces = []
    m = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(m):
            j = (i + 1) % m
            faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    for cap, ring, rev in ((cap0, rings[0], False), (cap1, rings[-1], True)):
        if not cap:
            continue
        ctr = bm.verts.new(tuple(sum(v.co[k] for v in ring) / len(ring) for k in range(3)))
        for i in range(m):
            j = (i + 1) % m
            f = bm.faces.new((ring[j], ring[i], ctr) if not rev else (ring[i], ring[j], ctr))
            faces.append(f)
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


def stations(a, b, step, extra=()):
    n = max(2, int(round((b - a) / step)))
    s = {round(a + (b - a) * i / n, 4) for i in range(n + 1)}
    s |= {round(x, 4) for x in extra if a <= x <= b}
    return sorted(s)


def groove(f, at, depth, half=0.07):
    """f(r) with a V seam of `depth` px centred on each row edge in `at` (modelled panel line)."""
    def g(r):
        v = f(r)
        for a in at:
            d = abs(r - a)
            if d < half * 2:
                v -= depth * max(0.0, 1 - max(0.0, d - half * 0.3) / (half * 1.7))
        return v
    return g


# --- Parts -----------------------------------------------------------------------------------------

def build_hull(bm, T, seams=True):
    # Plan: rear (row edge 1) rounded, widest 3.35 px over rows 3-6, necking to the collar.
    rs = [0.98, 1.15, 1.6, 2.4, 3.2, 6.2, 7.0, 7.6, 8.1, 8.35]
    w = T.pchip(rs, [1.2, 2.0, 2.75, 3.15, 3.3, 3.3, 3.32, 3.1, 2.7, 2.35])
    zt = T.pchip(rs, [1.6, 2.2, 2.75, 3.0, 3.05, 3.05, 3.0, 2.95, 2.9, 2.8])
    zb = T.pchip(rs, [0.6, 0.0, -0.75, -1.15, -1.3, -1.3, -1.25, -1.15, -0.9, -0.7])
    at = (6.55,) if seams else ()
    wg, zg = groove(w, at, 0.12), groove(zt, at, 0.12)
    rows = stations(0.98, 8.35, 0.4, rs + [a + d for a in at for d in (-0.14, -0.07, 0, 0.07, 0.14)])
    return loft(bm, rows, lambda r: superellipse(24, wg(r), zg(r), zb(r), 3.4, 2.4), HULL)


def build_block(bm, T, detail=True):
    # The dorsal sensor housing: columns 4-8 (half 2.45), rows 1-5, chamfered all round.
    rs = [1.02, 1.2, 1.55, 5.45, 5.8, 5.98]
    w = T.pchip(rs, [1.9, 2.3, 2.45, 2.45, 2.3, 1.9])
    zt = T.pchip(rs, [3.6, 4.05, ZB_TOP, ZB_TOP, 4.05, 3.6])

    def sec(r):
        # Tumblehome: the deck 12% narrower than the foot (z 3, where it leaves the hull).
        pts = superellipse(24, w(r), zt(r), 1.8, 6.0, 3.0)
        return [(x * (1 - 0.12 * max(0.0, z - 3.0) / (ZB_TOP - 3.0)), z) for x, z in pts]
    rows = stations(1.02, 5.98, 0.5, rs)
    faces = loft(bm, rows, sec, BLOCK)
    if detail:
        # Louvred vents on each side face: three short slats, dark slots between.
        for side in (-1, 1):
            for k in range(3):
                r0 = 2.6 + k * 0.75
                x = CX + side * 2.36
                box(bm, x - 0.08, x + 0.08, r0, r0 + 0.42, 3.15, 3.8, DARK)
        # Rear access hatch outline: a thin raised frame on the block's rear chamfer is invisible
        # at this size; the deck carries the light strip instead (build_lights).
    return faces


def box(bm, x0, x1, r0, r1, z0, z1, mat):
    vs = [bm.verts.new(P(x, r, z)) for z in (z0, z1) for r in (r0, r1) for x in (x0, x1)]
    idx = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    out = []
    for q in idx:
        f = bm.faces.new([vs[i] for i in q])
        f.material_index = mat
        f.smooth = False
        out.append(f)
    return out


def build_lobes(bm, T, detail=True):
    # Thruster nacelles: centred on column edge 3.0 / 10.0, rows 2.2-7.6, faired into the flanks.
    rs = [2.62, 2.75, 3.2, 4.0, 6.0, 6.7, 7.1, 7.38]
    a0 = T.pchip(rs, [0.55, 0.8, 1.0, 1.05, 1.05, 0.95, 0.7, 0.28])
    zt0 = T.pchip(rs, [1.7, 1.95, 2.25, 2.35, 2.35, 2.2, 1.9, 1.35])
    zb = T.pchip(rs, [0.0, -0.3, -0.55, -0.6, -0.6, -0.5, -0.25, 0.3])
    at = (6.1,) if detail else ()
    a, zt = groove(a0, at, 0.1), groove(zt0, at, 0.1)
    rows = stations(2.62, 7.38, 0.45, rs + [x + d for x in at for d in (-0.14, -0.07, 0, 0.07, 0.14)])
    for side in (-1, 1):
        c = CX + side * 3.5
        loft(bm, rows, lambda r: superellipse(18, a(r), zt(r), zb(r), 2.2, 2.2), LOBE, cx=c)
        if detail:
            # Exhaust nozzle: a short dark cylinder standing out of the rear end.
            nz = 0.5 * (zt0(2.75) + zb(2.75))
            loft(bm, [2.95, 2.6, 2.53], lambda r: superellipse(16, 0.55 if r > 2.55 else 0.45, nz + (0.7 if r > 2.55 else 0.58),
                                                              nz - (0.7 if r > 2.55 else 0.58), 2.2, 2.2), DARK, cx=c)


def build_rear(bm):
    # Main exhaust: a dark nozzle in the hull's rounded rear, under the block.
    loft(bm, [1.6, 0.95, 0.88], lambda r: circle(20, 0.75 if r > 0.9 else 0.62, zc=0.85), DARK)


def circle(n, rad, zc=ZA, sq=2.0):
    return superellipse(n, rad, zc + rad, zc - rad, sq, sq)


def build_collar(bm, T):
    rs = [7.95, 8.05, 8.4, 8.47, 8.53, 8.6, 8.92, 9.05]
    rad = [2.15, 2.45, 2.45, 2.32, 2.32, 2.45, 2.45, 2.2]
    f = dict(zip(rs, rad))
    return loft(bm, rs, lambda r: circle(20, f[r]), COLLAR)


def build_cone(bm, T, seams=True):
    rs = [9.0, 10.0, 11.0, 12.0, 13.0, 13.98]
    rad = T.pchip(rs, [2.3, 2.27, 1.98, 1.48, 0.86, 0.06])
    at = (10.1, 11.5) if seams else ()
    rg = groove(rad, at, 0.09)
    rows = stations(9.0, 12.6, 0.45, [a + d for a in at for d in (-0.14, -0.07, 0, 0.07, 0.14)])
    out = loft(bm, rows, lambda r: circle(20, rg(r)), CONE, cap1=False)
    tip = [12.6, 12.9, 13.2, 13.5, 13.75, 13.9, 13.98]
    out += loft(bm, tip, lambda r: circle(20, max(rad(r), 0.03)), TIP, cap0=False)
    return out


def build_lights(bm):
    """The inverted U of green lights on the block deck: a glowing bead of 0.78 px, half sunk."""
    zt = ZB_TOP
    path = []
    for i in range(6):
        path.append((5.5, 4.9 - (4.9 - 3.0) * i / 5))
    for i in range(1, 7):
        t = math.pi - (math.pi / 2) * i / 6
        path.append((6.0 + 0.5 * math.cos(t), 3.0 - 0.5 * math.sin(t)))
    path.append((6.5, 2.5))
    for i in range(0, 7):
        t = math.pi / 2 - (math.pi / 2) * i / 6
        path.append((7.0 + 0.5 * math.cos(t), 3.0 - 0.5 * math.sin(t)))
    for i in range(1, 6):
        path.append((7.5, 3.0 + (4.9 - 3.0) * i / 5))
    # Rings perpendicular to the path in plan; section a flattened half-round bead.
    n = 8
    hw, hz = 0.39, 0.17
    rings = []
    for i, (c, r) in enumerate(path):
        c0, r0 = path[max(0, i - 1)]
        c1, r1 = path[min(len(path) - 1, i + 1)]
        tc, tr = c1 - c0, r1 - r0
        ln = math.hypot(tc, tr) or 1
        nc, nr = -tr / ln, tc / ln
        ring = []
        for k in range(n):
            t = 2 * math.pi * k / n
            s, co = math.sin(t), math.cos(t)
            ring.append(bm.verts.new(P(c + nc * hw * s, r + nr * hw * s, zt - 0.06 + hz * (co if co > 0 else co * 1.4))))
        rings.append(ring)
    faces = []
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            faces.append(bm.faces.new((a[k], a[j], b[j], b[k])))
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        ctr = bm.verts.new(tuple(sum(v.co[q] for v in ring) / n for q in range(3)))
        for k in range(n):
            j = (k + 1) % n
            faces.append(bm.faces.new((ring[j], ring[k], ctr) if rev else (ring[k], ring[j], ctr)))
    for f in faces:
        f.material_index = LIGHT
        f.smooth = True
    return faces


def spec(mat, level):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = level
    return mat


def mesh_from(bm, name, coll, mats=None):
    import bmesh
    import bpy
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats or []:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def build():
    import bmesh
    import bpy
    import common
    import usp_talon as T

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    mats = [spec(common.palette_material(sprite, idx, f"{NAME}-{key}", metallic=me, roughness=ro,
                                         emission_strength=em), 0.5)
            for key, idx, me, ro, em in MATS]

    bm = bmesh.new()
    build_hull(bm, T)
    build_block(bm, T)
    build_lobes(bm, T)
    build_collar(bm, T)
    build_cone(bm, T)
    build_lights(bm)
    build_rear(bm)
    obj = mesh_from(bm, NAME, coll, mats)
    bpy.context.view_layer.update()

    # Outline shell from a sealed copy: the same volumes without seams, vents, nozzles or lights,
    # so the ink stays on the silhouette (D51, D189).
    bm = bmesh.new()
    build_hull(bm, T, seams=False)
    build_block(bm, T, detail=False)
    build_lobes(bm, T, detail=False)
    build_collar(bm, T)
    build_cone(bm, T, seams=False)
    seal = mesh_from(bm, NAME + "_seal", coll)
    bpy.context.view_layer.update()
    shell = common.outline_shell(seal, coll, voxel=0.006, faces=2000, smooth=4, inside=0.002, islands="outer")
    bpy.data.objects.remove(seal, do_unlink=True)
    shell.name = f"{NAME}_outline"
    assert len(shell.data.polygons) > 0, "empty outline shell"
    obj.data.calc_loop_triangles()
    tris = len(obj.data.loop_triangles)
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])
    prev = arg("--preview")
    if prev:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj, shell], prev, ref, size=sprite["frames"][0]["size"])
    print("MANIFEST", json.dumps({NAME: {"frames": [68], "tris": tris, "shell_faces": len(shell.data.polygons)}}))


if __name__ == "__main__":
    build()
