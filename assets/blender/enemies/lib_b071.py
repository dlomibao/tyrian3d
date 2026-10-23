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


# --- the horned creature with an eye on an arm (assemblies newshn-201 and newshn-39) -------------

def ridge_loft(bm, sections, across=4, mat=0, smooth=True):
    """A mound lofted down the sprite, sitting on the ground: each section is
    (row, left_col, right_col, ridge_col, height). Its cross-section rises from the left and
    right edges (z = 0) to a rounded crest above ridge_col; a section whose left and right are
    equal collapses to a point at that height (a tip). The underside is closed."""
    rings = []
    n = 2 * across + 1
    for row, left, right, ridge, h in sections:
        if right - left < 1e-6:
            rings.append([bm.verts.new((X(ridge), Y(row), h))])
            continue
        ring = []
        for k in range(n):
            u = -1 + 2 * k / (n - 1)
            c = ridge + u * ((ridge - left) if u < 0 else (right - ridge))
            # the edges are pixel edges, not centres
            c += -0.5 if k == 0 else (0.5 if k == n - 1 else 0.0)
            ring.append(bm.verts.new((X(c), Y(row), h * max(0.0, 1 - abs(u) ** 2.2) ** 0.55)))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1:
            faces += [bm.faces.new((r0[0], r1[k + 1], r1[k])) for k in range(n - 1)]
            faces.append(bm.faces.new((r0[0], r1[0], r1[-1])))
        elif len(r1) == 1:
            faces += [bm.faces.new((r0[k], r0[k + 1], r1[0])) for k in range(n - 1)]
            faces.append(bm.faces.new((r0[-1], r0[0], r1[0])))
        else:
            faces += [bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k])) for k in range(n - 1)]
            faces.append(bm.faces.new((r0[-1], r0[0], r1[0], r1[-1])))  # underside
    for ring in (rings[0], rings[-1]):
        if len(ring) > 1:
            faces.append(bm.faces.new(ring))
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


# Each pose (A: the eye held against the body, B: half raised, C: swung out and up) gives the eye
# (col, row, half width px, half height px), the lens (col, row of the cyan pixel), the arm from
# the shoulder to the eye and the hooked tentacle hanging from under the eye, as
# (col, row, half width px) in the coordinates of newshn-163 (rows past 27 run into newshn-201).
POSES = {
    "A": dict(
        eye=(13.5, 14.0, 2.0, 2.5), lens=(13.0, 14.0),
        arm=[(10.4, 12.6), (11.8, 13.2), (13.0, 13.8)],
        tentacle=[(13.3, 16.6, 0.7), (14.0, 17.9, 0.9), (14.0, 19.1, 1.2), (13.7, 20.4, 1.9),
                  (13.9, 21.7, 2.0), (14.3, 22.8, 1.6), (15.0, 23.8, 1.0), (15.8, 25.0, 0.8),
                  (16.0, 26.2, 0.8), (15.7, 27.4, 0.9), (15.3, 28.5, 0.8), (14.6, 29.4, 0.6),
                  (14.0, 30.3, 0.35), (13.8, 30.9, 0.0)]),
    "B": dict(
        eye=(15.4, 11.0, 2.2, 2.5), lens=(15.0, 11.0),
        arm=[(10.4, 12.4), (12.2, 12.2), (13.8, 11.6), (15.0, 11.2)],
        tentacle=[(15.0, 13.9, 0.6), (16.4, 14.7, 0.9), (17.3, 15.6, 1.1), (17.0, 16.8, 1.6),
                  (16.8, 18.0, 2.0), (17.2, 19.2, 2.2), (18.0, 20.2, 1.6), (18.7, 21.3, 0.9),
                  (19.0, 22.5, 0.7), (18.8, 23.8, 0.8), (18.5, 25.0, 0.9), (17.7, 26.2, 0.8),
                  (17.1, 27.2, 0.5), (16.7, 27.9, 0.0)]),
    "C": dict(
        eye=(17.4, 9.0, 2.2, 2.6), lens=(17.0, 9.0),
        arm=[(10.6, 10.6), (12.2, 9.2), (14.0, 8.7), (16.0, 8.8)],
        tentacle=[(17.0, 12.0, 0.6), (18.6, 12.9, 0.9), (19.2, 14.0, 1.3), (18.7, 15.2, 1.8),
                  (18.6, 16.4, 2.0), (19.1, 17.5, 2.2), (19.8, 18.6, 1.6), (20.6, 19.6, 0.9),
                  (21.0, 20.8, 0.7), (20.7, 22.2, 0.9), (20.3, 23.4, 0.9), (19.6, 24.4, 0.8),
                  (19.0, 25.2, 0.5), (18.6, 25.9, 0.0)]),
}


def creature(name, sprite, tag, pose, mirror=False):
    """The whole creature (newshn-163 over newshn-201) in one pose, in newshn-163's coordinates:
    a grey horn-shaped hood on top of a tapering lower body, a dark blue shoulder socket, an
    arm holding a grey eye with a glowing cyan lens, and a hooked tentacle hanging from the eye.
    `mirror` flips it for newshn-1 / newshn-39 (their column c is 22 - c here)."""
    coll = bpy.data.collections.get(tag) or common.reset_collection(tag)
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(103, metallic=0.2, roughness=0.45),  # 0 hood
        pal(101, metallic=0.2, roughness=0.5),  # 1 lower body
        pal(106, metallic=0.25, roughness=0.35),  # 2 light ridges
        pal(53, metallic=0.4, roughness=0.35),  # 3 blue shoulder socket
        pal(105, metallic=0.25, roughness=0.3),  # 4 eye and arm
        pal(103, metallic=0.2, roughness=0.4),  # 5 tentacle
        pal(136, emission_strength=4.0),  # 6 cyan lens
        pal(60, metallic=0.3, roughness=0.2),  # 7 pale rim round the lens
        pal(98, metallic=0.3, roughness=0.6),  # 8 dark recess under the arm
    ]
    HOOD, LOWER, RIDGE, SOCKET, EYE, TENT, LENS, IRIS, DARK = range(9)
    p = POSES[pose]
    bm = bmesh.new()

    # Lower body: from the light lip at rows 15-16, wide (columns 1-10), tapering down and to the
    # right to a point at row 32 (in newshn-201). (row, left, right, ridge, height)
    ridge_loft(bm, [(14.6, 1.0, 10.0, 4.6, 0.299), (15.4, 1.0, 11.0, 4.6, 0.38), (17.0, 1.0, 10.0, 4.6, 0.391),
                    (19.5, 1.0, 10.0, 4.6, 0.38), (21.5, 1.0, 9.0, 4.6, 0.345), (23.0, 2.0, 7.0, 4.6, 0.299),
                    (25.0, 3.0, 7.0, 5.0, 0.253), (27.0, 4.0, 7.0, 5.4, 0.207), (29.0, 5.0, 8.0, 6.4, 0.149),
                    (31.0, 6.0, 8.0, 7.2, 0.092), (32.4, 8.0, 9.0, 8.4, 0.046), (32.9, 8.5, 8.5, 8.5, 0.023)],
               across=4, mat=LOWER)
    # Its light lip across the top and the light crease down its left.
    sweep(bm, [(1.0, 15.6, 0.235, 0.0, 0.0), (1.4, 15.6, 0.258, 0.8, 0.05), (4.6, 15.5, 0.385, 0.9, 0.05),
               (8.6, 15.5, 0.281, 0.8, 0.045), (9.6, 15.5, 0.212, 0.0, 0.0)], sides=6, mat=RIDGE)
    sweep(bm, [(4.6, 16.5, 0.385, 0.0, 0.0), (4.6, 17.2, 0.39, 0.6, 0.03), (4.6, 21.5, 0.35, 0.6, 0.03),
               (5.0, 25.0, 0.258, 0.55, 0.025), (5.4, 27.0, 0.212, 0.5, 0.02), (6.4, 29.0, 0.154, 0.45, 0.02),
               (7.0, 30.4, 0.108, 0.0, 0.0)], sides=6, mat=RIDGE)

    # Hood: a horn from its tip at the top (column 5-6, row 0) widening to columns 3-12.
    ridge_loft(bm, [(0.3, 5.6, 5.6, 6.0, 0.161), (1.2, 5.0, 7.0, 6.2, 0.23), (3.0, 5.0, 8.8, 6.4, 0.31),
                    (4.5, 5.0, 11.6, 6.4, 0.38), (6.5, 4.0, 12.6, 5.8, 0.46), (8.5, 3.0, 11.6, 5.2, 0.517),
                    (10.5, 3.0, 11.0, 5.2, 0.54), (12.5, 3.0, 11.0, 5.4, 0.54), (14.3, 3.0, 11.5, 5.2, 0.506),
                    (15.2, 3.2, 10.5, 5.0, 0.414), (15.6, 4.8, 5.2, 5.0, 0.345)], across=4, mat=HOOD)
    # Light crest down its left side.
    sweep(bm, [(6.0, 0.8, 0.177, 0.0, 0.0), (6.2, 1.6, 0.246, 0.5, 0.025), (6.4, 4.5, 0.396, 0.55, 0.03),
               (5.6, 7.0, 0.476, 0.6, 0.03), (5.2, 9.5, 0.534, 0.6, 0.03), (5.3, 12.5, 0.545, 0.6, 0.03),
               (5.1, 14.2, 0.511, 0.0, 0.0)], sides=6, mat=RIDGE)
    # Dark recess under the arm on the hood's right flank (columns 8-10, rows 11-16).
    ellipsoid(bm, 9.2, 13.5, 0.12, 1.8, 2.8, 0.14, mat=DARK, segments=10, rings=5)
    # Blue shoulder socket (columns 9-12, rows 13-16).
    ellipsoid(bm, 10.8, 14.6, 0.16, 2.0, 2.4, 0.16, mat=SOCKET, segments=12, rings=6)

    # The arm from the shoulder to the eye, the eye and its lens.
    ec, er, ew, eh = p["eye"]
    ez = 0.34
    arm = p["arm"]
    path = [(c, r, 0.24 + (ez - 0.24) * i / (len(arm) - 1), 1.2, 0.08) for i, (c, r) in enumerate(arm)]
    sweep(bm, path, sides=8, mat=EYE)
    ellipsoid(bm, ec, er, ez, ew + 0.3, eh + 0.3, 0.17, mat=EYE, segments=14, rings=7)
    lc, lr = p["lens"]
    ellipsoid(bm, lc, lr - 0.6, ez + 0.13, 1.05, 1.6, 0.05, mat=IRIS, segments=10, rings=5)
    ellipsoid(bm, lc, lr - 0.1, ez + 0.145, 0.85, 1.0, 0.05, mat=LENS, segments=10, rings=5)

    # Hooked tentacle hanging from under the eye down to the ground.
    tent = p["tentacle"]
    n = len(tent)
    path = []
    for i, (c, r, w) in enumerate(tent):
        t = i / (n - 1)
        z = 0.22 * (1 - t) + 0.05 * t
        path.append((c, r, z, w, 0.03 + 0.035 * min(w, 2.0)))
    sweep(bm, path, sides=8, mat=TENT)

    if mirror:
        dx = -1 / 12
        for v in bm.verts:
            v.co.x = -v.co.x + dx
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return to_object(name, bm, mats, coll)


def creature_assembly(script_file, name, pieces, mirror):
    """Build the creature in its three poses, cut each into its two pieces and export them.
    pieces = [(piece, row_offset, {pose: model})...] with frames per model taken from the piece's
    sprite.json in the order the models are listed: {pose: (model, frame)}."""
    root = common.repo_root(script_file)
    sprites = {p: common.load_sprite(root, p) for p, _, _ in pieces}
    merged = dict(sprites[pieces[0][0]])
    merged["colors"] = {}
    for s in sprites.values():
        merged["colors"].update(s["colors"])
    previews = []
    for pose in ("A", "B", "C"):
        obj = creature(f"{name}-{pose}", merged, name, pose, mirror=mirror)
        layout = [(models[pose][0], 0, rows) for _, rows, models in pieces]
        cut = common.split_assembly(obj, layout)
        for piece, rows, models in pieces:
            model, frame = models[pose]
            src = sprites[piece]["sprites"][0]
            assert frame in src["frames"], (piece, frame)
            subset = [{**src, "frames": [frame]}]
            common.export_sprite_model(root, [cut[model]], f"enemies/{model}", subset)
            previews.append((cut[model], piece, frame, model))
        previews.append((obj, None, pose, None))
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        for obj, piece, frame, model in previews:
            if piece:
                image = next(f["image"] for f in sprites[piece]["frames"] if f["index"] == frame)
                img = root / "reference" / "models" / piece / image
                common.render_preview([obj], str(out.parent / f"{model}.png"), img, size=2)
            else:
                pose = frame
                frames = {p: models[pose][1] for p, _, models in pieces}
                ref = _composite(root, sprites, pieces, frames, tmp / f"{pose}.png")
                obj.location.y += 14 / 12  # centre the two-piece column on the preview
                target = out if pose == "A" else out.parent / f"{out.stem}-{pose}.png"
                common.render_preview([obj], str(target), ref, size=4, view_px=480)
                obj.location.y -= 14 / 12


def _composite(root, sprites, pieces, frames, out):
    """The pieces' frames stacked as they sit in game, centred in a 48 x 56 px image."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for piece, rows, _ in pieces:
        data = sprites[piece]
        frame = next(f for f in data["frames"] if f["index"] == frames[piece])
        for r, line in enumerate(frame["pixels"]):
            for c, v in enumerate(line):
                if v >= 0:
                    img[rows + r, 12 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out
