"""Helpers shared by batch b068's model scripts (newsh5 ground objects of episode 4).

Not a model script itself: tools/build-models.sh skips lib_ files.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


def X(c, w=24):
    """Sprite column (pixel centre; fractions allowed) to Blender X."""
    return (c + 0.5 - w / 2) / 12


def Y(r, h=28):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (h / 2 - (r + 0.5)) / 12


def EX(e, w=24):
    """Pixel edge (column boundary) to Blender X."""
    return (e - w / 2) / 12


def EY(e, h=28):
    """Pixel edge (row boundary) to Blender Y."""
    return (h / 2 - e) / 12


def set_faces(bm, first, mat=None, smooth=None):
    """Set material and/or smooth flag on every face added since index `first`."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first:]:
        if mat is not None:
            f.material_index = mat
        if smooth is not None:
            f.smooth = smooth


def move(bm, start, dx=0.0, dy=0.0, dz=0.0):
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x += dx
        v.co.y += dy
        v.co.z += dz


def rotate_z(bm, start, angle, cx=0.0, cy=0.0):
    """Rotate every vertex added since `start` about the Z axis through (cx, cy), radians CCW."""
    bm.verts.ensure_lookup_table()
    c, s = math.cos(angle), math.sin(angle)
    for v in bm.verts[start:]:
        x, y = v.co.x - cx, v.co.y - cy
        v.co.x, v.co.y = cx + x * c - y * s, cy + x * s + y * c


def ellipsoid(bm, centre, radii, mat=0, segments=16, rings=8, angle=0.0, floor=None, smooth=True):
    """An ellipsoid with semi-axes `radii` (units), turned by `angle` about Z. With `floor` set,
    vertices below that height are pressed flat onto it (a dome sitting on the ground)."""
    f0 = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    c, s = math.cos(angle), math.sin(angle)
    for v in res["verts"]:
        x, y, z = v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2]
        v.co = Vector((centre[0] + x * c - y * s, centre[1] + x * s + y * c, centre[2] + z))
        if floor is not None and v.co.z < floor:
            v.co.z = floor
    set_faces(bm, f0, mat, smooth)


def blob(bm, centre, radii, mat=0, segments=16, rings=8, power=1.0, angle=0.0, floor=None, smooth=True):
    """A superellipsoid: power < 1 squares it off (0.5 is a rounded box), 1 is an ellipsoid."""
    f0 = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    c, s = math.cos(angle), math.sin(angle)
    for v in res["verts"]:
        x, y, z = (math.copysign(abs(q) ** power, q) * r for q, r in zip(v.co, radii))
        v.co = Vector((centre[0] + x * c - y * s, centre[1] + x * s + y * c, centre[2] + z))
        if floor is not None and v.co.z < floor:
            v.co.z = floor
    set_faces(bm, f0, mat, smooth)


def ellipsoid_z(centre, radii, angle, x, y, floor=0.0):
    """Height of the top of an ellipsoid (as built by `ellipsoid`) above point (x, y)."""
    c, s = math.cos(-angle), math.sin(-angle)
    dx, dy = x - centre[0], y - centre[1]
    lx, ly = dx * c - dy * s, dx * s + dy * c
    t = 1 - (lx / radii[0]) ** 2 - (ly / radii[1]) ** 2
    if t <= 0:
        return floor
    return max(floor, centre[2] + radii[2] * math.sqrt(t))


def sweep(bm, path, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True, phase=0.5):
    """A tube along a path of (x, y, z, half_width, half_height) in units. Rings stand
    perpendicular to the path in XY; the width is across the path and the height along Z. A ring
    of zero size collapses to a point. phase=0 with 4 sides gives a diamond section (a ridge on
    top and a keel below)."""
    pts = [Vector((x, y, z)) for x, y, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (_, _, _, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        if t.length < 1e-9:
            t = Vector((0, 1, 0))
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + phase) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
        rings.append(ring)
    f0 = len(bm.faces)
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
            bm.faces.new(f)
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    set_faces(bm, f0, mat, smooth)


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    """Extrude an XY outline (units, any winding) from z0 to z1."""
    f0 = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    set_faces(bm, f0, mat, smooth)


def box(bm, x0, y0, x1, y1, z0, z1, mat=0):
    prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat=mat)


def radial(poly, cx, cy, n, phase=0.5):
    """Points where rays from (cx, cy) at n even angles meet a closed polygon's boundary, so that
    loops of different shapes (an octagon, an ellipse) get matching vertices for `terraces`."""
    out = []
    for k in range(n):
        a = 2 * math.pi * (k + phase) / n
        dx, dy = math.cos(a), math.sin(a)
        best = None
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            ex, ey = x1 - x0, y1 - y0
            den = dx * ey - dy * ex
            if abs(den) < 1e-12:
                continue
            t = ((x0 - cx) * ey - (y0 - cy) * ex) / den
            u = ((x0 - cx) * dy - (y0 - cy) * dx) / den
            if t > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t < best):
                best = t
        out.append((cx + dx * best, cy + dy * best))
    return out


def ellipse_pts(cx, cy, rx, ry, n, phase=0.5):
    return [(cx + rx * math.cos(2 * math.pi * (k + phase) / n), cy + ry * math.sin(2 * math.pi * (k + phase) / n))
            for k in range(n)]


def terraces(bm, loops, mats, cap_bottom=None, cap_top=None):
    """Join loops of (x, y, z) points (all the same length, same winding) with bands of quads:
    band i between loops i and i+1 gets material mats[i]. Caps close the first and last loop
    with an n-gon of the given material (None leaves it open)."""
    vloops = [[bm.verts.new(p) for p in loop] for loop in loops]
    n = len(loops[0])
    for i, (a, b) in enumerate(zip(vloops, vloops[1:])):
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((a[k], a[j], b[j], b[k]))
            f.material_index = mats[i]
    if cap_bottom is not None:
        bm.faces.new(list(reversed(vloops[0]))).material_index = cap_bottom
    if cap_top is not None:
        bm.faces.new(vloops[-1]).material_index = cap_top


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


def frame_subset(sprite, frames):
    """sprite["sprites"] cut down to the given frame indices (for animations needing several models)."""
    out = []
    for s in sprite["sprites"]:
        keep = [f for f in s["frames"] if f in frames]
        if keep:
            out.append({**s, "frames": keep})
    return out


def preview_arg():
    if "--preview" in sys.argv:
        return Path(sys.argv[sys.argv.index("--preview") + 1])
    return None


def arg_after(flag):
    """The word after `flag` in the script's own arguments (after `--`), or None."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None


def make_shell(obj, coll):
    """The model's outline shell (D51) from a sealed copy, islands="outer" (D189): ink on the
    silhouette only. Named <obj>_outline."""
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    shell = common.outline_shell(sealed, coll, voxel=0.012, faces=3000, smooth=4, inside=0.004,
                                 islands="outer")
    bpy.data.objects.remove(sealed, do_unlink=True)
    assert len(shell.data.polygons) > 0, f"{obj.name}_outline has no mesh"
    return shell


def export_frames(root, name, sprite, models, outline=True):
    """Export one model per frame group. `models` is a list of (object, [frame indices]); the
    first is `name`, the rest `name-f2`, `name-f3`, ... Each goes out with its _outline shell
    (outline=False for a model that fills its tile and draws no ink). `--review DIR` writes review
    renders and the top-view IoU per model into DIR; `--no-export` skips the export; `--preview
    out.png` is the usual common.render_preview."""
    out = preview_arg()
    review_dir = arg_after("--review")
    for i, (obj, frames) in enumerate(models):
        model_name = name if i == 0 else f"{name}-f{i + 1}"
        coll = obj.users_collection[0]
        obj.data.set_sharp_from_angle(angle=math.radians(35))
        shell = None
        if outline:
            shell = make_shell(obj, coll)
            shell.name = f"{obj.name}_outline"
        if review_dir:
            review(root, name, model_name, obj, shell, frames[0], Path(review_dir))
        if "--no-export" not in sys.argv:
            common.export_sprite_model(root, [obj] + ([shell] if shell else []), f"enemies/{model_name}",
                                       frame_subset(sprite, frames))
        if out:
            frame = next(f for f in sprite["frames"] if f["index"] == frames[0])
            ref = Path(root) / "reference" / "models" / name / frame["image"]
            path = out if i == 0 else out.parent / f"{model_name}.png"
            common.render_preview([obj], str(path), ref, size=frame["size"])


def review(root, name, model_name, obj, shell, frame_index, outdir):
    """Review renders of one model into outdir: <model>_top_flat.png (silhouette, measured against
    the sprite's inner mask: the rule's IoU), <model>_top.png (palette colours, lit), <model>_game.png
    (the tilted game camera), <model>_q.png (3/4). The measure goes to <model>_measure.json."""
    import json
    sys.path.insert(0, str(Path(root) / "tools"))
    import sprite_mask as SM
    outdir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in bpy.data.objects:
        o.hide_render = o is not obj
    W, H = 24, 28
    k = 8

    def shoot(loc, look, path, rx, ry, ortho=None, fov=35):
        d = bpy.data.cameras.new("cam")
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.sensor_fit = "VERTICAL"
            d.angle_y = math.radians(fov)
        c = bpy.data.objects.new("cam", d)
        scene.collection.objects.link(c)
        c.location = loc
        c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = c
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(c, do_unlink=True)

    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.color_type = "MATERIAL"
    sh.show_shadows = False
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    sh.light, sh.show_cavity = "FLAT", False
    shoot((0, 0, 20), (0, 0, 0), outdir / f"{model_name}_top_flat.png", W * k, H * k, ortho=H / 12)
    m = SM.masks(*SM.load(name, frame_index))
    res = SM.measure(m, SM.read_png_mask(outdir / f"{model_name}_top_flat.png"))
    (outdir / f"{model_name}_measure.json").write_text(json.dumps(res, indent=1))
    print("MEASURE", model_name, json.dumps(res))
    sh.light, sh.show_cavity = "STUDIO", True
    shoot((0, 0, 20), (0, 0, 0), outdir / f"{model_name}_top.png", W * k, H * k, ortho=H / 12)
    tilt = math.radians(32)
    shoot((0, -6 * math.sin(tilt), 6 * math.cos(tilt)), (0, 0, 0), outdir / f"{model_name}_game.png", 480, 480,
          fov=30)
    shoot((3.5, -4.2, 3.6), (0, 0, 0.2), outdir / f"{model_name}_q.png", 480, 480, fov=30)
    for o in bpy.data.objects:
        o.hide_render = False


def resample(poly, step):
    """A closed polygon with extra points so no edge is longer than `step` (corners are kept)."""
    out = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / step))
        out.extend((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n))
    return out


def toward_ellipse(points, cx, cy, rx, ry, scale=1.0):
    """For each point, the point on the ellipse (centre cx, cy) in the same direction from the
    centre: an inner loop with one vertex per outer vertex, for `terraces`."""
    out = []
    for x, y in points:
        a = math.atan2(y - cy, x - cx)
        r = scale / math.sqrt((math.cos(a) / rx) ** 2 + (math.sin(a) / ry) ** 2)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def pull(points, cx, cy, d):
    """Move each point `d` units toward (cx, cy) (a rough inset for a bevel)."""
    out = []
    for x, y in points:
        dx, dy = cx - x, cy - y
        n = math.hypot(dx, dy) or 1.0
        out.append((x + dx / n * d, y + dy / n * d))
    return out


def at_z(points, z):
    return [(x, y, z) for x, y in points]


def chamfer_ring(w, h, k=0.55):
    """An 8-point chamfered-rectangle section (across, up): flat sides of half width w, a flat top
    and bottom of half height h, 45-ish chamfers where they meet (k = the flats' share)."""
    return [(w, -h * k), (w, h * k), (w * k, h), (-w * k, h), (-w, h * k), (-w, -h * k), (-w * k, -h), (w * k, -h)]


def chamfer_loft(bm, secs, mat, k=0.55, cap0=True, cap1=True):
    """Loft along +Y of chamfered-rectangle sections (y, half width, half height, z centre)."""
    rings = [[bm.verts.new((x, y, zc + z)) for x, z in chamfer_ring(w, h, k)] for y, w, h, zc in secs]
    f0 = len(bm.faces)
    for a, b in zip(rings, rings[1:]):
        for i in range(8):
            j = (i + 1) % 8
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap0:
        bm.faces.new(list(reversed(rings[0])))
    if cap1:
        bm.faces.new(rings[-1])
    set_faces(bm, f0, mat)


def revolve_axis(bm, origin, axis, profile, sides=16):
    """Rings about an arbitrary axis: profile is [(t, r, mat), ...] (t along the axis, units; r the
    radius; r 0 closes to a point). Each band takes the material of its first ring."""
    o, d = Vector(origin), Vector(axis).normalized()
    a = d.cross(Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))).normalized()
    b = d.cross(a).normalized()
    rings = []
    for t, r, _ in profile:
        c = o + d * t
        if r <= 1e-6:
            rings.append([bm.verts.new(c)])
        else:
            rings.append([bm.verts.new(c + (a * math.cos(2 * math.pi * i / sides) + b * math.sin(2 * math.pi * i / sides)) * r)
                          for i in range(sides)])
    for (ra, rb), (_, _, mat) in zip(zip(rings, rings[1:]), profile):
        n = max(len(ra), len(rb))
        for i in range(n):
            j = (i + 1) % n
            if len(ra) == 1:
                vs = (ra[0], rb[j], rb[i])
            elif len(rb) == 1:
                vs = (ra[i], ra[j], rb[0])
            else:
                vs = (ra[i], ra[j], rb[j], rb[i])
            try:
                f = bm.faces.new(vs)
                f.material_index = mat
            except ValueError:
                pass


def offset_poly(poly, d):
    """A convex CCW polygon moved inward by d (mitred corners)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((-e0.y, e0.x)), Vector((-e1.y, e1.x))  # inward normals for CCW
        m = (n0 + n1).normalized()
        out.append(tuple(p1 + m * (d / max(m.dot(n0), 0.2))))
    return out


def chamfer_prism(bm, poly, z0, z1, ch, mat, top_mat=None, chz=None):
    """A convex CCW outline extruded z0..z1 with chamfered top and bottom edges."""
    chz = ch if chz is None else chz
    inner = offset_poly(poly, ch)
    loops = [at_z(inner, z0), at_z(poly, z0 + chz), at_z(poly, z1 - chz), at_z(inner, z1)]
    terraces(bm, loops, [mat, mat, mat], cap_bottom=mat, cap_top=mat if top_mat is None else top_mat)


def chamfer_box(bm, x0, x1, y0, y1, z0, z1, ch, mat, top_mat=None, chz=None):
    chamfer_prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, ch, mat, top_mat, chz)


def build_diagonal_pod(sprite, name, mirror=False):
    """The grey diagonal craft of newsh5-83 (and, mirrored, newsh5-81): a faceted metal missile
    flying up the screen's diagonal along its long axis (83 to the upper right, 81 to the upper
    left; BRAINIAC, groundBottom spawns at the corners), the exhaust coming out of its lower-left end.

    - The body: a chunky chamfered-box loft (flat top and sides, chamfers between) about a level
      axis, its half width following the sprite's inner mask along the diagonal, tapering to the
      nose at the upper right; a darker middle band behind a groove, a slot and a vent on top.
    - The engine housing at the lower left: a lighter boxy block whose sides run with the tile's
      axes, as the sprite draws it (cols 2-9.5, rows 14.3-22), chamfered all round, with a nozzle
      recessed in its rear (chamfered corner) face and a dark seam where it meets the body.
    No foot: the underside is the closed other half. Highlights are sheen, not geometry (rule 2).
    `mirror` flips it left to right (newsh5-81's sprite is newsh5-83's mirror image)."""
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.6, roughness=0.32),  # 0 body (region median 7, satin sheen)
        pal(5, metallic=0.55, roughness=0.38),  # 1 darker middle band (median 4-5)
        pal(2, metallic=0.4, roughness=0.6),  # 2 grooves, slot, nozzle bore
        pal(9, metallic=0.6, roughness=0.3),  # 3 engine housing (lighter, median 9 on top)
        pal(4, metallic=0.6, roughness=0.4),  # 4 nozzle bezel, vents
        pal(1, metallic=0.3, roughness=0.7),  # 5 seam
    ]
    BODY, BAND, GROOVE, HOUSE, BEZEL, SEAM = range(6)
    bm = bmesh.new()
    cx, cy = EX(11.66), EY(12.34)  # the inner mask's centre
    ZC = 0.45  # axis height: the underside is the body's other half
    HK = 0.68  # half height / half width of the body sections
    # Silhouette half width (px) along the axis, measured off the sprite's inner mask.
    PROFILE = [(-12.7, 1.3), (-12.0, 2.0), (-11.0, 2.8), (-10.0, 3.6), (-9.0, 4.4), (-8.0, 5.0), (-7.0, 5.6),
               (-6.0, 6.2), (-5.0, 6.7), (-4.0, 6.9), (-1.0, 7.0), (1.0, 7.4), (3.0, 7.2), (4.0, 6.6),
               (5.0, 6.5), (6.0, 5.7), (7.0, 5.0), (8.0, 4.8), (9.0, 4.0), (10.0, 3.3), (11.0, 2.3),
               (12.0, 1.3), (12.7, 0.9)]
    import usp_talon as T
    wf = T.pchip([p[0] for p in PROFILE], [p[1] for p in PROFILE])

    def width(u):
        return max(0.3, float(wf(min(max(u, PROFILE[0][0]), PROFILE[-1][0]))))

    def secs(us, inset=0.0):
        return [(u * PX, (width(u) - inset) * PX, HK * (width(u) - inset) * PX, ZC) for u in us]

    def frange(a, b, s):
        n = max(1, round((b - a) / s))
        return [a + (b - a) * i / n for i in range(n + 1)]

    # Body: band (inside the housing from u -9), groove, main body to the nose.
    chamfer_loft(bm, secs(frange(-9.0, -1.0, 0.5)), BAND)
    chamfer_loft(bm, secs([-1.0, -0.2], inset=0.5), GROOVE)
    chamfer_loft(bm, secs(frange(-0.2, 5.3, 0.5)), BODY)
    chamfer_loft(bm, secs([5.3, 5.7], inset=0.3), BEZEL)  # fine panel break before the nose section
    chamfer_loft(bm, secs(frange(5.8, 11.8, 0.5) + [12.3, 12.7]), BODY)

    def top_z(u, v):
        """Height of the body's top surface at axis position u, offset v across (px)."""
        w = width(u)
        h = HK * w
        a = abs(v)
        if a <= 0.55 * w:
            return ZC / PX + h
        return ZC / PX + h - (a - 0.55 * w) / (0.45 * w) * h * 0.45

    def sunk_box(u0, u1, v0, v1, mat, proud=0.15):
        """A small axis-aligned block standing `proud` px above the body's top over its footprint."""
        zt = max(top_z(u, v) for u in (u0, u1) for v in (v0, v1)) + proud
        zb = min(top_z(u, v) for u in (u0, u1) for v in (v0, v1)) - 1.2
        chamfer_box(bm, v0 * PX, v1 * PX, u0 * PX, u1 * PX, zb * PX, zt * PX, 0.2 * PX, mat)

    # Slot (sprite row 4, cols 15-17) and vent (row 6, cols 13-15) on the body's top, in (u, v).
    sunk_box(7.7, 9.3, -3.1, -2.0, GROOVE)
    sunk_box(4.7, 6.3, -3.0, -1.6, BEZEL)

    bm.verts.ensure_lookup_table()
    rotate_z(bm, 0, -math.pi / 4)
    move(bm, 0, cx, cy)

    # Engine housing, in tile axes (pixel edges), CCW in Blender XY.
    hz0, hz1 = ZC - 3.8 * PX, ZC + 4.3 * PX
    poly = [(EX(2.0), EY(14.3)), (EX(2.0), EY(19.7)), (EX(4.3), EY(22.0)), (EX(9.5), EY(22.0)), (EX(9.5), EY(14.3))]
    chamfer_prism(bm, poly, hz0, hz1, 0.7 * PX, HOUSE)
    # Panel lines across its top, and the dark seam where it meets the body (its top and right edges).
    t = hz1
    for r in (17.0, 19.4):
        box(bm, EX(2.9), EY(r + 0.35), EX(8.8 - (0.0 if r < 19 else 0.0)), EY(r), t - 0.01, t + 0.004, mat=GROOVE)
    box(bm, EX(2.6), EY(15.25), EX(9.0), EY(14.85), t - 0.01, t + 0.005, mat=SEAM)
    box(bm, EX(8.55), EY(21.4), EX(8.95), EY(15.25), t - 0.01, t + 0.005, mat=SEAM)
    # Nozzle recessed in the rear face (the chamfered corner), pointing down-left (back along the axis).
    nc = ((EX(2.0) + EX(4.3)) / 2, (EY(19.7) + EY(22.0)) / 2, (hz0 + hz1) / 2)
    revolve_axis(bm, nc, (-1, -1, 0), [(-0.8 * PX, 1.2 * PX, BEZEL), (0.06 * PX, 1.2 * PX, BEZEL),
                                       (0.06 * PX, 0.85 * PX, GROOVE), (-0.5 * PX, 0.85 * PX, SEAM),
                                       (-0.5 * PX, 0.0, SEAM)], sides=16)
    for f in bm.faces:
        f.smooth = False

    if mirror:
        for v in bm.verts:
            v.co.x = -v.co.x
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return to_object(name, bm, mats, coll)
