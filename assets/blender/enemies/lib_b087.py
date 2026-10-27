"""Helpers shared by batch b087's model scripts (not a model: tools/build-models.sh skips lib_ files).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block by default. ring_loft, tube and polyline_tube are
adapted from lib_b007.py.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def px(c, w=24):
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    return (h / 2 - (r + 0.5)) / 12


def ex(c, w=24):
    return (c - w / 2) / 12


def ey(r, h=28):
    return (h / 2 - r) / 12


def _tag(bm, start_faces, mat, smooth):
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start_faces:]:
        if mat is not None:
            f.material_index = mat
        f.smooth = smooth


def ring_loft(bm, rings, mat=0, cap_start=True, cap_end=True, smooth=True):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order."""
    n0 = len(bm.faces)
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    for r0, r1 in zip(verts, verts[1:]):
        n = max(len(r0), len(r1))
        if n == 1:
            continue
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face)
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0])))
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1])
    _tag(bm, n0, mat, smooth)
    return verts


def polyline_tube(bm, points, radius, sides=6, mat=0, caps=True, smooth=True):
    """A round tube along a polyline of 3D points; `radius` a number or one per point."""
    pts = [Vector(p) for p in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    tangents = []
    for i in range(len(pts)):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tangents.append(t.normalized())
    ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    u = tangents[0].cross(ref).normalized()
    rings = []
    for i, (c, t) in enumerate(zip(pts, tangents)):
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u).normalized()
        rings.append([tuple(c + radii[i] * (math.cos(2 * math.pi * (k + 0.5) / sides) * u
                                            + math.sin(2 * math.pi * (k + 0.5) / sides) * v))
                      for k in range(sides)])
    return ring_loft(bm, rings, mat, cap_start=caps, cap_end=caps, smooth=smooth)


def cone(bm, base, tip, radius, sides=6, mat=0, smooth=False):
    """A spike: a round base of `radius` at `base` narrowing to a point at `tip` (3D points)."""
    a, b = Vector(base), Vector(tip)
    axis = (b - a).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    ring = [tuple(a + radius * (math.cos(2 * math.pi * (k + 0.5) / sides) * u
                                + math.sin(2 * math.pi * (k + 0.5) / sides) * v)) for k in range(sides)]
    return ring_loft(bm, [ring, [tuple(b)]], mat, smooth=smooth)


def ellipsoid(bm, center, rx, ry, rz, mat=0, segments=12, rings=6, smooth=True):
    n0 = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = center
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * rx, cy + v.co.y * ry, cz + v.co.z * rz))
    _tag(bm, n0, mat, smooth)


def dome(bm, cx, cy, z0, rx, ry, h, segments=16, rings=5, mat=0, smooth=True, skirt=0.0):
    """The top half of an ellipsoid: an elliptical base (rx, ry) at z0 rising to z0 + h. With
    `skirt` > 0 the base stands on a vertical wall that far below z0."""
    layers = []
    if skirt > 0:
        layers.append([(cx + rx * math.cos(2 * math.pi * (i + 0.5) / segments),
                        cy + ry * math.sin(2 * math.pi * (i + 0.5) / segments), z0 - skirt) for i in range(segments)])
    for k in range(rings):
        a = (math.pi / 2) * k / rings
        s, z = math.cos(a), z0 + h * math.sin(a)
        layers.append([(cx + rx * s * math.cos(2 * math.pi * (i + 0.5) / segments),
                        cy + ry * s * math.sin(2 * math.pi * (i + 0.5) / segments), z) for i in range(segments)])
    layers.append([(cx, cy, z0 + h)])
    return ring_loft(bm, layers, mat, smooth=smooth)


def ellipse_torus(bm, cx, cy, z, rx, ry, tube_w, tube_h, segments=24, sides=8, mat=0, smooth=True,
                  mats=None):
    """A ring lying flat: its centre line is an ellipse (rx, ry) at height z; its cross-section is an
    ellipse tube_w wide (in the plane) and tube_h tall. `mats(angle)` may pick a material per segment."""
    n0 = len(bm.faces)
    rings = []
    for i in range(segments):
        t = 2 * math.pi * i / segments
        c = Vector((cx + rx * math.cos(t), cy + ry * math.sin(t), z))
        nrm = Vector((math.cos(t) / rx, math.sin(t) / ry, 0)).normalized()
        rings.append([bm.verts.new(c + nrm * tube_w * math.cos(2 * math.pi * k / sides)
                                   + Vector((0, 0, tube_h * math.sin(2 * math.pi * k / sides))))
                      for k in range(sides)])
    for i in range(segments):
        r0, r1 = rings[i], rings[(i + 1) % segments]
        m = mats(2 * math.pi * (i + 0.5) / segments) if mats else mat
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r1[k], r1[j], r0[j])).material_index = m
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f.smooth = smooth


def box(bm, x0, y0, x1, y1, z0, z1, mat=0, smooth=False):
    """An axis-aligned box between two corners (units)."""
    common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[-6:]:
        f.smooth = smooth


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """An extruded outline of (x, y) points in units, from z0 to z1 (any winding)."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(outline, outline[1:] + outline[:1]))
    pts = outline if area > 0 else list(reversed(outline))
    n0 = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    _tag(bm, n0, None, smooth)


def height_solid(bm, ys, xs_of, z_of, mat_of, smooth=True, wall_mat=None):
    """A solid standing on z = 0 whose top is a height field: rows at y values `ys` (units, any
    order), each spanning the x values xs_of(y) (left to right, same count every row), with
    height z_of(x, y) (0 or more). Walls drop from the boundary to z = 0 wherever it is above the
    ground; a bottom face closes it. mat_of(x, y) picks each top face's material by its centre."""
    n0 = len(bm.faces)
    grid = []
    for y in ys:
        grid.append([bm.verts.new((x, y, max(0.0, z_of(x, y)))) for x in xs_of(y)])
    nr, nc = len(grid), len(grid[0])
    top = []
    for i in range(nr - 1):
        for j in range(nc - 1):
            q = (grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j])
            f = bm.faces.new(q)
            c = sum((v.co for v in q), Vector()) / 4
            f.material_index = mat_of(c.x, c.y)
            f.smooth = smooth
            top.append(f)
    # Boundary loop (around the grid), each with its ground vertex.
    loop = [grid[0][j] for j in range(nc)] + [grid[i][nc - 1] for i in range(1, nr)] + \
           [grid[nr - 1][j] for j in range(nc - 2, -1, -1)] + [grid[i][0] for i in range(nr - 2, 0, -1)]
    ground = [v if v.co.z < 1e-6 else bm.verts.new((v.co.x, v.co.y, 0.0)) for v in loop]
    n = len(loop)
    for k in range(n):
        a, b = loop[k], loop[(k + 1) % n]
        ga, gb = ground[k], ground[(k + 1) % n]
        if ga is a and gb is b:
            continue
        quad = [a, b] + ([gb] if gb is not b else []) + ([ga] if ga is not a else [])
        f = bm.faces.new(quad)
        f.material_index = wall_mat if wall_mat is not None else mat_of(a.co.x, a.co.y)
        f.smooth = False
    # Bottom: the ground loop, dropping repeated vertices.
    bottom = []
    for g in ground:
        if not bottom or bottom[-1] is not g:
            bottom.append(g)
    if bottom[0] is bottom[-1]:
        bottom.pop()
    f = bm.faces.new(list(reversed(bottom)))
    f.material_index = wall_mat if wall_mat is not None else 0
    return grid


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


def frames_subset(sprite, frames):
    """The sprite's `sprites` entries cut down to the given frame indices."""
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f in frames]
        if keep:
            out.append({**s, "frames": keep})
    return out


def run(name, build, file):
    """Build, export every model and, with -- --preview <png>, preview each (the first at <png>,
    the others at <png stem>-f2.png, ...). `build(sprite)` returns a list of
    (model_name, objects, sprites, frame_image)."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites, _ in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        size = sprite["frames"][0]["size"]
        for k, (model, objects, _, image) in enumerate(models):
            path = out if k == 0 else out.with_name(f"{out.stem}-f{k + 1}.png")
            common.render_preview(objects, str(path), root / "reference" / "models" / name / image, size=size)
    if "--frame-previews" in sys.argv:  # every frame of the first model, one row each
        common.render_frame_previews(models[0][1], sys.argv[sys.argv.index("--frame-previews") + 1], sprite, root)
    return sprite


# --- newsha-93 / newsha-17: a dome in a ring on a rubble tile ----------------------------------

def build_pad(sprite, name, cfg, lit):
    """The ground pad of newsha-93 (red) and newsha-17 (green): a 24x28 tile of grey rubble with
    sand patches top-left and bottom-left, a ring lying on it and a dome in the ring (lit=False).
    In the second frame (lit=True) the ring flares wider and brighter and the dome opens into a
    ring round a smaller inner dome with a glint on top. `cfg` gives the palette indices:
    plate, sand, rock, dark_rock, ring, ring_emit, socket, dome, lit_ring, lit_socket, inner,
    glint and optionally ring_glint (white sparkles on the lit ring)."""
    coll = common.reset_collection(f"{name}_{int(lit)}")
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(cfg["plate"], metallic=0.1, roughness=0.9),  # 0 rubble ground
        pal(cfg["sand"], metallic=0.0, roughness=0.95),  # 1 sand
        pal(cfg["rock"], metallic=0.1, roughness=0.85),  # 2 light rocks
        pal(cfg["dark_rock"], metallic=0.1, roughness=0.9),  # 3 dark rocks
        pal(cfg["lit_socket"] if lit else cfg["socket"], metallic=0.2, roughness=0.7),  # 4 socket
        pal(cfg["lit_ring"] if lit else cfg["ring"], metallic=0.4, roughness=0.35,
            emission_strength=3.0 if lit else cfg["ring_emit"]),  # 5 ring
        pal(cfg["dome"], metallic=0.35, roughness=0.25),  # 6 dome (or its ring when lit)
        pal(cfg["inner"], metallic=0.35, roughness=0.3),  # 7 inner dome (lit)
        pal(cfg["glint"], emission_strength=4.0),  # 8 glint
    ]
    PLATE, SAND, ROCK, DARK, SOCKET, RING, DOME, INNER, GLINT = range(9)
    if lit and cfg.get("ring_glint") is not None:
        mats.append(pal(cfg["ring_glint"], emission_strength=5.0))  # 9 ring sparkles
    bm = bmesh.new()

    # The tile: rubble ground filling the block, sand drifts and a few rocks on it.
    box(bm, ex(0), ey(28), ex(24), ey(0), 0.0, 0.06, mat=PLATE)
    plate(bm, [(ex(0), ey(0)), (ex(10.5), ey(0)), (ex(10.5), ey(1.5)), (ex(8.5), ey(3.2)), (ex(5), ey(4.2)),
               (ex(3), ey(4.6)), (ex(0), ey(3.8))], 0.0, 0.09, mat=SAND, smooth=False)
    plate(bm, [(ex(2), ey(28)), (ex(2.6), ey(26)), (ex(4), ey(25.6)), (ex(10.5), ey(25.8)), (ex(11), ey(27)),
               (ex(11.2), ey(28))], 0.0, 0.085, mat=SAND, smooth=False)
    for c, r, rx, ry, rz, m in ((15.5, 1.6, 1.6, 1.4, 0.08, ROCK), (21.8, 1.4, 2.0, 1.4, 0.09, ROCK),
                                (19.5, 3.4, 1.4, 1.0, 0.07, DARK), (22.8, 5.5, 1.2, 1.4, 0.07, ROCK),
                                (22.6, 22.5, 1.4, 1.6, 0.08, ROCK), (21.5, 25.6, 2.0, 1.4, 0.07, DARK),
                                (15.5, 26.6, 1.8, 1.2, 0.07, DARK), (13.5, 24.8, 1.6, 1.0, 0.06, ROCK),
                                (1.0, 25.0, 1.2, 1.4, 0.07, ROCK), (1.2, 21.6, 1.0, 1.2, 0.06, DARK)):
        ellipsoid(bm, (px(c), row(r), 0.05), rx / 12, ry / 12, rz, mat=m, segments=8, rings=4, smooth=False)

    if not lit:
        cx, cy = ex(12), ey(13.6)
        # Dark socket inside the ring, the ring, and the dome sitting in it.
        dome(bm, cx, cy, 0.06, 10.6 / 12, 9.0 / 12, 0.02, segments=24, rings=1, mat=SOCKET, smooth=False)
        ellipse_torus(bm, cx, cy, 0.1, 11.0 / 12, 9.5 / 12, 1.1 / 12, 0.08, segments=32, sides=8, mat=RING)
        dome(bm, ex(12.4), ey(13.6), 0.06, 9.3 / 12, 8.3 / 12, 0.42, segments=24, rings=6, mat=DOME, skirt=0.06)
    else:
        cx, cy = ex(12), ey(13.9)

        dome(bm, cx, cy, 0.06, 10.8 / 12, 10.4 / 12, 0.02, segments=24, rings=1, mat=SOCKET, smooth=False)
        ellipse_torus(bm, cx, cy, 0.12, 10.6 / 12, 10.6 / 12, 1.6 / 12, 0.11, segments=32, sides=8, mat=RING)
        if len(mats) > 9:  # thin white sparkles along the ring's inner top, upper left and lower right
            for a0, a1 in ((112, 160), (290, 338)):
                pts = [(cx + 9.9 / 12 * math.cos(math.radians(a)), cy + 9.9 / 12 * math.sin(math.radians(a)), 0.2)
                       for a in range(a0, a1 + 1, 8)]
                polyline_tube(bm, pts, 0.45 / 12, sides=6, mat=9)
        # The opened dome: a thick ring (its red rim) round a smaller inner dome with a glint.
        ellipse_torus(bm, ex(12.0), ey(13.6), 0.13, 8.2 / 12, 7.4 / 12, 1.1 / 12, 0.12, segments=28, sides=8,
                      mat=DOME)
        dome(bm, ex(11.6), ey(13.8), 0.06, 6.9 / 12, 6.8 / 12, 0.36, segments=20, rings=6, mat=INNER, skirt=0.06)
        gx, gy = px(9.5), row(10)
        dz = 0.06 + 0.36 * math.sqrt(max(0.0, 1 - ((gx - ex(11.6)) ** 2 + (gy - ey(13.8)) ** 2) / (6.9 / 12) ** 2))
        ellipsoid(bm, (gx, gy, dz), 1.3 / 12, 1.3 / 12, 0.03, mat=GLINT, segments=8, rings=4)
    return to_object(f"{name}{'-f2' if lit else ''}", bm, mats, coll)
