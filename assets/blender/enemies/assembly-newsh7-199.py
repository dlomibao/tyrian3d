"""assembly-newsh7-199, design A: a grey panelled sphere held in a purple lander cradle
(newsh7.shp 161 | 163 over 199 | 201; CAMANIS 3.1 and ICESECRET 4.20, two side by side on the ice).

What it is (read from the 48x56 sprite): a big satin-grey sphere with engraved panel seams sits in a
purple cradle. Two upright side cheeks (cols 2-4 and 32-35, rows 15-27) hold a tilted strap that runs
round the sphere's south face (the purple lip at rows 24-27 that pinches the grey to 9 px). Under it
four chamfered N-S runner bars (two per side, split by a dark slot at col 17-19) end in a rounded
cross-beam (the lit band at row 33), from which two faceted landing legs run south down to the ice,
each with a toe turned in (rows 40-43) and a chisel foot. Lighting comes from the upper left, so the
bright left columns of each bar and leg are lit bevels, not paint (art rule 2).

The ice in the sprite is ground, not model (D130): nothing is built for it; IoU is measured against the
sprite with the ice ramp (48-62) made transparent (refmask.py).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh7-199.py
Exports public/models/enemies/newsh7-{161,163,199,201}.glb and their spriteModels json (each piece
at its own origin, with its outline shell).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common  # noqa: E402

WT = common.repo_root(__file__)
HERE = Path(__file__).resolve().parent

NAME = "assembly-newsh7-199"
PIECES = ["newsh7-161", "newsh7-163", "newsh7-199", "newsh7-201"]
# Piece centres in the 48x56 block's screen pixels (layout: 161/163 at cy -18, 199/201 at cy 10, cx 224/248).
LAYOUT = [("newsh7-161", -12, -14), ("newsh7-163", 12, -14), ("newsh7-199", -12, 14), ("newsh7-201", 12, 14)]
PX = 1 / 12


def X(u):
    """Pixel-edge column u of the 48x56 block (0 = left edge) to Blender X."""
    return (u - 24) * PX


def Y(v):
    """Pixel-edge row v (0 = top edge) to Blender Y (sprite up = +Y)."""
    return (28 - v) * PX


# ---- the sphere ---------------------------------------------------------------------------------
SU, SV = 18.25, 14.5          # centre (pixel edges)
SRX, SRY = 13.5, 12.5       # plan radii, px (fitted to the inner mask)
SZ, SRZ = 0.50, 0.85          # centre height and vertical radius (units)
CZ, CX, CY = SZ, X(SU), Y(SV)
RX, RY = SRX * PX, SRY * PX


def ell_scale(d):
    """s so that centre + s*d is on the ellipsoid."""
    return 1.0 / math.sqrt((d.x / RX) ** 2 + (d.y / RY) ** 2 + (d.z / SRZ) ** 2)


def ell_normal(p):
    return Vector(((p.x - CX) / RX ** 2, (p.y - CY) / RY ** 2, (p.z - CZ) / SRZ ** 2)).normalized()


# ---- small bmesh helpers ------------------------------------------------------------------------

def hull(bm, pts, mat, smooth=True):
    """Convex hull of `pts` added to `bm` (coplanar triangles merged), material `mat`."""
    tmp = bmesh.new()
    for p in pts:
        tmp.verts.new(p)
    res = bmesh.ops.convex_hull(tmp, input=tmp.verts[:])
    junk = res["geom_interior"] + res["geom_unused"]
    if junk:
        bmesh.ops.delete(tmp, geom=list({g for g in junk if isinstance(g, bmesh.types.BMVert)}), context="VERTS")
    bmesh.ops.dissolve_limit(tmp, angle_limit=math.radians(0.5), verts=tmp.verts[:], edges=tmp.edges[:])
    for f in tmp.faces:
        f.material_index = mat
        f.smooth = smooth
    me = bpy.data.meshes.new("tmp")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def cbar(x0, x1, y0, y1, z0, z1, ch, chz=None):
    """Points of a box with chamfered vertical corners and top edges (Blender coords)."""
    chz = ch if chz is None else chz
    pts = []
    for z, inset in ((z0, 0.0), (z1 - chz, 0.0), (z1, ch)):
        a0, a1, b0, b1 = x0 + inset, x1 - inset, y0 + inset, y1 - inset
        c = ch
        pts += [(a0 + c, b0, z), (a1 - c, b0, z), (a1, b0 + c, z), (a1, b1 - c, z),
                (a1 - c, b1, z), (a0 + c, b1, z), (a0, b1 - c, z), (a0, b0 + c, z)]
    return pts


def loft(bm, rings, mat, cap0=True, cap1=True, smooth=True):
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(vs, vs[1:]):
        for i in range(n):
            f = bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
            f.material_index = mat
            f.smooth = smooth
    for ring, on in ((vs[0], cap0), (vs[-1], cap1)):
        if on:
            f = bm.faces.new(ring)
            f.material_index = mat
            f.smooth = False


# ---- parts ----------------------------------------------------------------------------------------

def build_sphere(bm, M, detail=True):
    """The ellipsoid, cut flat at z=0.08 inside the cradle, with engraved panel seams (V grooves cut
    on vertical planes, so each seam is a straight line from above as in the sprite)."""
    tmp = bmesh.new()
    seg, rings = 96, 44
    zcut = 0.10
    tmax = math.acos((zcut - CZ) / SRZ)
    top = tmp.verts.new((CX, CY, CZ + SRZ))
    grid = []
    for i in range(1, rings + 1):
        t = tmax * i / rings
        row = []
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            row.append(tmp.verts.new((CX + RX * math.sin(t) * math.cos(ph), CY + RY * math.sin(t) * math.sin(ph),
                                      CZ + SRZ * math.cos(t))))
        grid.append(row)
    for j in range(seg):
        tmp.faces.new((top, grid[0][j], grid[0][(j + 1) % seg]))
    for a, b in zip(grid, grid[1:]):
        for j in range(seg):
            tmp.faces.new((a[j], b[j], b[(j + 1) % seg], a[(j + 1) % seg]))
    tmp.faces.new(list(reversed(grid[-1])))
    for f in tmp.faces:
        f.material_index = M["sphere"]
        f.smooth = True

    # Seams: (u0, v0) -> (u1, v1) in pixel edges, extended past the rim where they run off it.
    seams = [
        ((20.8, -2.0), (20.8, 15.3)),    # down from the crown, right of centre
        ((2.0, 15.3), (20.8, 15.3)),     # across the middle, west half
        ((20.8, 15.3), (31.0, 25.4)),    # diagonal to the lower right
        ((9.6, 15.3), (9.6, 32.0)),      # lower left, down
        ((11.2, 5.4), (20.8, 5.4)),      # crown cap, across the top
        ((26.0, 3.0), (26.0, 15.3)),     # upper right, down
    ]
    hw, depth, taper = 0.36 * PX, 0.030, 0.6 * PX
    for (u0, v0), (u1, v1) in (seams if detail else []):
        p0, p1 = Vector((X(u0), Y(v0), 0)), Vector((X(u1), Y(v1), 0))
        d = (p1 - p0)
        L = d.length
        d.normalize()
        n = Vector((-d.y, d.x, 0))
        for off in (-hw, 0.0, hw):
            co = p0 + n * off
            bmesh.ops.bisect_plane(tmp, geom=tmp.verts[:] + tmp.edges[:] + tmp.faces[:], plane_co=co, plane_no=n)
        groove = set()
        for v in tmp.verts:
            q = Vector((v.co.x, v.co.y, 0)) - p0
            dist = q.dot(n)
            if abs(dist) > hw + 1e-6 or v.co.z < CZ - 0.15:
                continue
            t = q.dot(d)
            if t < -1e-6 or t > L + 1e-6:
                continue
            k = min(1.0, t / taper, (L - t) / taper) if (u0, v0) not in ((20.8, -2.0), (2.0, 15.3), (9.6, 32.0)) else 1.0
            k = max(0.0, k)
            w = 1.0 - abs(dist) / hw
            if w > 1e-4 and k > 0:
                v.co -= ell_normal(v.co) * depth * w * k
                groove.add(v)
        for f in tmp.faces:
            if all(v in groove or abs((Vector((v.co.x, v.co.y, 0)) - p0).dot(n)) <= hw + 1e-6 for v in f.verts) \
                    and any(v in groove for v in f.verts):
                f.material_index = M["seam"]
    me = bpy.data.meshes.new("sph")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)

    if not detail:
        return
    # The amber lamp at the lower right rim (sprite pixel 23,24: palette 169).
    lu, lv = 23.6, 24.4
    d = Vector((X(lu) - CX, Y(lv) - CY, 0))
    k = 1 - (d.x / RX) ** 2 - (d.y / RY) ** 2
    p = Vector((X(lu), Y(lv), CZ + SRZ * math.sqrt(max(0.0, k))))
    nrm = ell_normal(p)
    t1 = nrm.orthogonal().normalized()
    t2 = nrm.cross(t1)
    r = 0.62 * PX
    pts = []
    for i in range(10):
        a = 2 * math.pi * i / 10
        for h, rr in ((-0.02, r * 1.05), (0.012, r), (0.03, r * 0.7), (0.042, r * 0.25)):
            pts.append(p + nrm * h + (t1 * math.cos(a) + t2 * math.sin(a)) * rr)
    hull(bm, pts, M["lamp"])


def build_strap(bm, M):
    """The tilted strap round the sphere's south face: a great-circle band in the plane through the
    sphere's E-W axis, tilted so its south point rises to the purple lip at rows 24-27."""
    PSI0 = 9.0  # the ends stop inside the cheeks (south of the equator), not outside the silhouette
    tau = math.radians(18.0)  # tilt of the strap's plane: south side up
    e1 = Vector((1, 0, 0))
    e2 = Vector((0, -math.cos(tau), math.sin(tau)))
    nrm = e1.cross(e2).normalized()  # band width direction
    hw, th, ch = 1.25 * PX, 0.085, 0.3 * PX
    c = Vector((CX, CY, CZ))
    rings = []
    for i in range(0, 61):
        psi = math.radians(PSI0 + (180 - 2 * PSI0) * i / 60)
        dirn = e1 * math.cos(psi) + e2 * math.sin(psi)
        ring = []
        for a, out in ((-hw, -0.01), (-hw, th - ch), (-hw + ch, th), (hw - ch, th), (hw, th - ch), (hw, -0.01)):
            q = dirn * 1.0 + nrm * (a / 1.0)
            q = q * ell_scale(q)
            ring.append(c + q + q.normalized() * out)
        rings.append(ring)
    loft(bm, rings, M["cradle"])


def build_cradle(bm, M):
    zt = 0.64
    # Side cheeks: rounded-top uprights; the north end ramps down. Left cols 2-4 rows 16-27; right
    # cols 32-35 rows 15-27, its south end stepping in to col 32 by row 30.
    for u0, u1, vn, vs, step in ((2.0, 5.1, 15.9, 27.0, None), (32.1, 35.9, 14.9, 27.3, (32.1, 30.2))):
        pts = []
        prof = []  # (u, z) cross-section: vertical sides, rounded top
        w = u1 - u0
        for k in range(9):
            a = math.pi * k / 8
            prof.append((u0 + w / 2 - math.cos(a) * w / 2, zt - (1 - math.sin(a)) * 0.10))
        for v, zs in ((vn, 0.55), (vn + 1.4, 1.0), (21.5, 1.0), (21.7, 1.0), (vs, 1.0)):
            for uu, zz in prof:
                if v < 21.6 and uu > 35.0:  # the right cheek's outer face steps out from row 22
                    uu = 35.0
                pts.append((X(uu), Y(v), zz * zs if zs < 1 else zz))
            pts += [(X(u0), Y(v), 0.0), (X(min(u1, 35.0) if v < 21.6 else u1), Y(v), 0.0)]
        if step:
            su, sv = step
            pts += [(X(su), Y(sv), 0.0), (X(su), Y(sv), 0.34), (X(su + 1.2), Y(sv - 1.0), 0.40)]
        hull(bm, pts, M["cradle"])
    # Cup floor between the cheeks (seen only in the gaps round the sphere).
    hull(bm, cbar(X(4.6), X(32.6), Y(29.0), Y(16.2), 0.0, 0.20, 0.3 * PX), M["inner"], smooth=False)
    # Base under the runner bars (its top is the dark groove floor and the centre slot).
    for u0, u1 in ((6.0, 17.5), (19.5, 32.0)):
        hull(bm, cbar(X(u0), X(u1), Y(36.0), Y(23.0), 0.0, 0.25, 0.4 * PX), M["inner"], smooth=False)
    # Pedestal ring under the sphere (inside its plan, so only seen from the side and rear).
    pts = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        for rr, z in ((0.80, 0.0), (0.80, 0.10), (0.76, 0.16), (0.72, 0.30)):
            pts.append((CX + RX * rr * math.cos(a), CY + RY * rr * math.sin(a), z))
    hull(bm, pts, M["inner"])
    # Four runner bars, chamfered; their south ends sink into the cross-beam.
    for u0, u1, u2 in ((6.0, 10.15, 10.15), (11.35, 17.5, 17.5), (19.5, 25.1, 25.1), (26.35, 32.0, 31.6)):
        hull(bm, cbar(X(u0), X(u1), Y(34.0), Y(23.2), 0.0, 0.44, 0.5 * PX, 0.55 * PX), M["cradle"], smooth=False)
    # A raised boss strip down each bar's lit edge (the bright columns 6, 12, 20, 27).
    for u in (6.9, 12.25, 20.45, 27.25):
        hull(bm, cbar(X(u - 0.55), X(u + 0.55), Y(33.2), Y(26.8), 0.30, 0.475, 0.25 * PX), M["cradle"], smooth=False)
    # Cross-beam: rounded top at row 33, sloping front down to the legs' roots.
    for u0, u1 in ((6.0, 17.5), (19.5, 31.3)):
        pts = []
        prof = [(32.3, 0.0), (32.3, 0.40), (32.9, 0.455), (33.6, 0.47), (34.4, 0.44), (35.2, 0.33), (35.95, 0.16),
                (35.95, 0.0)]
        for uu, cut in ((u0, 0.4), (u0 + 0.4, 0.0), (u1 - 0.4, 0.0), (u1, 0.4)):
            for v, z in prof:
                pts.append((X(uu), Y(v), max(0.0, z - cut * 0.08) if z > 0 else 0.0))
        hull(bm, pts, M["cradle"])


def build_legs(bm, M):
    """Two faceted landing legs from the cross-beam down to the ice, ridge on the inner side, a toe
    turned in at rows 40-43 and a chisel foot at row 47."""
    for (ua, ub, ridge, toe_tip) in ((9.0, 14.2, 12.55, 16.9), (22.85, 28.4, 24.45, 21.0)):
        # (v, half-scale of the width, ridge z)
        stations = [(34.6, 1.0, 0.40), (36.5, 1.0, 0.37), (40.0, 1.0, 0.31), (44.0, 1.0, 0.22), (45.6, 0.92, 0.17),
                    (46.6, 0.62, 0.12), (47.25, 0.22, 0.05)]
        mid = (ua + ub) / 2
        pts = []
        for v, s, zr in stations:
            a, b, rg = mid + (ua - mid) * s, mid + (ub - mid) * s, mid + (ridge - mid) * s
            sh = zr - 0.075
            pts += [(X(a), Y(v), 0.0), (X(b), Y(v), 0.0), (X(a), Y(v), sh), (X(b), Y(v), sh), (X(rg), Y(v), zr)]
        hull(bm, pts, M["leg"], smooth=False)
        # Root flare where the leg meets the beam (row 36 is wider than the leg).
        fa, fb = (8.1, 16.0) if ua < 20 else (22.0, 29.0)
        pts = []
        for v, inset, z in ((34.8, 0.0, 0.40), (36.95, 0.0, 0.30), (37.6, 1.2, 0.24)):
            pts += [(X(fa + inset), Y(v), 0.0), (X(fb - inset), Y(v), 0.0), (X(fa + inset + 0.6), Y(v), z),
                    (X(fb - inset - 0.6), Y(v), z), (X(fa + inset), Y(v), z - 0.06), (X(fb - inset), Y(v), z - 0.06)]
        hull(bm, pts, M["cradle"], smooth=False)
        # Toe: a chamfered wedge turned in toward the centre.
        root = ridge
        sgn = 1 if toe_tip > root else -1
        pts = []
        for u, zt, half in ((root, 0.21, 2.4), (toe_tip - sgn * 1.0, 0.13, 1.7), (toe_tip, 0.07, 1.0)):
            for dv in (-half, half):
                pts += [(X(u), Y(42.5 + dv), 0.0), (X(u), Y(42.5 + dv), zt - 0.03)]
            pts += [(X(u), Y(42.5 - half * 0.6), zt), (X(u), Y(42.5 + half * 0.6), zt)]
        hull(bm, pts, M["leg"], smooth=False)
        # A hinge knuckle where the leg leaves the beam.
        kx = mid
        pts = []
        for i in range(10):
            a = 2 * math.pi * i / 10
            for du in (-1.6, 1.6):
                pts.append((X(kx + du), Y(36.1) + 0.05 * math.cos(a), 0.31 + 0.05 * math.sin(a)))
        hull(bm, pts, M["cradle"])


def materials(sprite):
    tag = "n7_199a"

    def pal(i, metallic, roughness, **kw):
        return common.palette_material(sprite, i, tag, metallic=metallic, roughness=roughness, **kw)

    mats = {
        "sphere": pal(10, 0.62, 0.30),
        "seam": pal(7, 0.55, 0.45),
        "cradle": pal(86, 0.45, 0.40),
        "leg": pal(87, 0.45, 0.40),
        "inner": pal(82, 0.35, 0.60),
        "lamp": pal(169, 1.0, 0.55, emission_strength=0.35),
    }
    bsdf = next(n for n in mats["sphere"].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.65
    order = list(mats)
    return [mats[k] for k in order], {k: i for i, k in enumerate(order)}


def build(coll, detail=True, name=NAME):
    sprite = common.load_sprite(WT, PIECES[0])
    for n in PIECES[1:]:
        sprite["colors"].update(common.load_sprite(WT, n)["colors"])
    mats, M = materials(sprite)
    bm = bmesh.new()
    build_sphere(bm, M, detail)
    build_strap(bm, M)
    build_cradle(bm, M)
    build_legs(bm, M)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(34))
    return obj


def sink_shell(shell, model, margin, reach):
    """Keep the outline shell under the model's top surface (D90/D118: ink on the silhouette only).

    The voxel shell is smoothed, so it bridges the model's creases (the hood's trim strips, the gem bezel, the
    engine-bay channel, the hood/nose step) and stood above the surface there: its back faces drew as dark
    scribbles across the hood and the plate. Every shell vertex is dropped to `margin` under the topmost
    model surface within `reach` of it (seen from straight above). x and y are untouched, so the silhouette (and the ink round it) is
    the same."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    moved = 0
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):  # the lowest top within `reach`: a shell edge spans ~0.6 px, so a vertex
            a = 2 * math.pi * k / 12  # beside a raised strip must not ride at the strip's height
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    pieces = common.split_assembly(obj, LAYOUT)
    # The outline shell's source (D90/D118): a sealed copy without the engraved seams and the lamp, so
    # the smoothed shell can't bridge the grooves and draw ink across the sphere.
    plain = build(coll, detail=False, name=NAME + "_plain")
    sealed = common.split_assembly(plain, LAYOUT)
    bpy.data.objects.remove(plain, do_unlink=True)
    bpy.context.view_layer.update()
    shells = {}
    for name, cx, cy in LAYOUT:
        p = pieces[name]
        p.data.set_sharp_from_angle(angle=math.radians(34))
        src = sealed[name]
        bpy.context.view_layer.update()
        sh = common.outline_shell(src, coll, voxel=0.018, faces=6000, inside=0.012)
        sh.name = sh.data.name = f"{name}_outline"
        if "--sink" in argv:
            sink_shell(sh, src, margin=0.03, reach=0.09)
        bpy.data.objects.remove(src, do_unlink=True)
        shells[name] = sh
    for name, _, _ in LAYOUT:
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"])
    for name, cx, cy in LAYOUT:
        pieces[name].location = shells[name].location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()
    if "--views" in argv:
        import views_A
        views_A.run(obj, list(shells.values()), Path(argv[argv.index("--views") + 1]), show=True)


if __name__ == "__main__":
    main()
