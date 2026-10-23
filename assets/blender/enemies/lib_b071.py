"""Helpers shared by batch b071's scripts (level 2.4 ground enemies from newshn.shp).

- `shell`: a blue spiral shell (newshn-125, -15, -13): a dome with a raised spire on its upper
  left, a dark groove spiralling round the spire and a light ridge on the outer whorl.
- `creature`: the grey horned creature with an eye on an arm and a hooked tentacle that is two
  2x2 pieces tall (assemblies newshn-201 and newshn-39, which is its mirror image).

Pixel coordinates are sprite (column, row) centres; fractions are allowed.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12


def X(c):
    """Sprite column (centre) of a 24-wide block to Blender X."""
    return (c + 0.5 - 12) / 12


def Y(r):
    """Sprite row (centre) of a 28-tall block to Blender Y (sprite up is +Y)."""
    return (14 - (r + 0.5)) / 12


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path in XY; a ring of zero size collapses to a point."""
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
    rings = []
    up = Vector((0, 0, 1))
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        if t.length < 1e-6:
            t = Vector((0, 1, 0))
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * PX * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            faces.append(bm.faces.new(f))
    if cap_start and len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end and len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=12, rings=6, smooth=True):
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * rz))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def _dist_polyline(p, line):
    """Distance from p (x, y) to a polyline, and how far along it (0..1) the nearest point is."""
    best, best_t = 1e9, 0.0
    lengths = [math.dist(a, b) for a, b in zip(line, line[1:])]
    total = sum(lengths) or 1.0
    run = 0.0
    for (a, b), seg in zip(zip(line, line[1:]), lengths):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        t = 0.0 if seg == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (seg * seg)))
        d = math.dist(p, (ax + t * dx, ay + t * dy))
        if d < best:
            best, best_t = d, (run + t * seg) / total
        run += seg
    return best, best_t


# --- spiral shells (newshn-125, -15, -13) -------------------------------------------------------

def shell(name, sprite, centre, radii, height, knob, groove, ridge, idx, rings=12, segments=40):
    """A spiral shell sitting on the ground (base at z = 0).

    centre (col, row) and radii (px) give its elliptical footprint and `height` its dome (units).
    knob = (col, row, radius_px, rise): the spire, a smooth cap standing out of the dome. groove
    and ridge are polylines of (col, row): a dark groove sunk into the dome round the spire and a
    light ridge along the outer whorl. idx = (shell, spire, groove, ridge, foot) palette indices."""
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(idx[0], metallic=0.35, roughness=0.35),  # 0 shell
        pal(idx[1], metallic=0.35, roughness=0.25),  # 1 spire
        pal(idx[2], metallic=0.2, roughness=0.6),  # 2 groove
        pal(idx[3], metallic=0.35, roughness=0.25),  # 3 whorl ridge
        pal(idx[4], metallic=0.3, roughness=0.5),  # 4 dark foot
    ]
    SHELL, SPIRE, GROOVE, RIDGE, FOOT = range(5)
    cx, cy = centre
    a, b = radii
    kx, ky, kr, krise = knob
    gdepth, gwidth = height * 0.2, 1.3

    def dome(c, r):
        rho = math.sqrt(((c - cx) / a) ** 2 + ((r - cy) / b) ** 2)
        return rho, height * max(0.0, 1 - min(rho, 1.0) ** 2.2) ** 0.5

    def surface(c, r):
        """The dome with the groove pressed into it."""
        rho, z = dome(c, r)
        dg, tg = _dist_polyline((c, r), groove)
        g = gdepth * math.exp(-(dg / gwidth) ** 2) * min(1.0, (1 - tg) * 4)
        return max(0.0, z - g * max(0.0, 1 - min(rho, 1.0) ** 8))

    bm = bmesh.new()
    rhos = [1 - (1 - i / rings) ** 1.5 for i in range(rings + 1)]  # denser towards the rim
    grid = []
    for i, rho in enumerate(rhos):
        if i == 0:
            grid.append([bm.verts.new((X(cx), Y(cy), surface(cx, cy)))])
            continue
        ring = []
        for j in range(segments):
            phi = 2 * math.pi * j / segments
            c, r = cx + a * rho * math.cos(phi), cy + b * rho * math.sin(phi)
            ring.append(bm.verts.new((X(c), Y(r), surface(c, r) if i < rings else 0.0)))
        grid.append(ring)
    for i in range(rings):
        r0, r1 = grid[i], grid[i + 1]
        for j in range(segments):
            k = (j + 1) % segments
            f = bm.faces.new((r0[0], r1[k], r1[j]) if len(r0) == 1 else (r0[j], r0[k], r1[k], r1[j]))
            f.material_index = FOOT if i >= rings - 1 else SHELL
            f.smooth = True
    bm.faces.new(list(reversed(grid[-1]))).material_index = FOOT

    # The spire: a smooth cap rising out of the dome.
    zk = dome(kx, ky)[1]
    ellipsoid(bm, kx, ky, zk - krise * 0.9, kr, kr, krise * 1.9, mat=SPIRE, segments=16, rings=8)

    # Dark groove line in the bottom of the dent, fading out at its end.
    n = len(groove)
    path = []
    for i, (c, r) in enumerate(groove):
        w = 1.05 * min(1.0, (n - 1 - i) / 2 + 0.3)
        path.append((c, r, surface(c, r) - 0.006, w, 0.03))
    path = [(path[0][0], path[0][1], path[0][2], 0, 0)] + path + [(*groove[-1], surface(*groove[-1]), 0, 0)]
    sweep(bm, path, sides=8, mat=GROOVE)

    # Light ridge along the outer whorl.
    n = len(ridge)
    path = []
    for i, (c, r) in enumerate(ridge):
        t = min(i, n - 1 - i)
        w = 1.1 if t > 0 else 0.5
        path.append((c, r, dome(c, r)[1] - 0.012, w, 0.035 if t > 0 else 0.02))
    path = [(*ridge[0], path[0][2], 0, 0)] + path + [(*ridge[-1], path[-1][2], 0, 0)]
    sweep(bm, path, sides=8, mat=RIDGE)
    return to_object(name, bm, mats, coll)


def shell_main(name, script_globals_build):
    """Build, export and optionally preview a single-frame model built by `build(sprite)`."""
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, name)
    obj = script_globals_build(sprite)
    common.export_sprite_model(root, [obj], f"enemies/{name}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = root / "reference" / "models" / name / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])
