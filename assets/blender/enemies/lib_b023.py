"""Helpers shared by batch b023's model scripts (newshf fighters, insect ships and pods).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block.

Several of these sprites rock from side to side: their frames show the same craft rolled a little
left, level and rolled right. Those get one model per frame (the level build turned about its long
axis), see `rolled`.
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix

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


def palette(sprite, tag, remap=None):
    """pal(index, **kw) -> palette material; `remap` turns the index a shared builder was written
    for into this sprite's index (recoloured variants of the same craft)."""
    def pal(i, **kw):
        return common.palette_material(sprite, remap(i) if remap else i, tag, **kw)
    return pal


def ring_loft(bm, rings, mats, cap_start=True, cap_end=True):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order.
    `mats` is one material index or a list with one per band."""
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    def mat(band):
        return mats[band] if isinstance(mats, list) else mats
    for b, (r0, r1) in enumerate(zip(verts, verts[1:])):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face).material_index = mat(b)
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0]))).material_index = mat(0)
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1]).material_index = mat(len(verts) - 2)
    return verts


def polyline_tube(bm, points, radius, sides=6, mat_index=0, caps=True, flat=1.0):
    """One continuous round tube along a polyline, with mitred joints. `radius` can be a number or
    a list with one radius per point (0 makes a point). `flat` squashes it vertically."""
    from mathutils import Vector
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
        if radii[i] == 0:
            rings.append([tuple(c)])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            off = radii[i] * (math.cos(a) * u + math.sin(a) * v)
            off.z *= flat
            ring.append(tuple(c + off))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps)


def dome(bm, cx, cy, z, rx, ry, rz, mat_index=0, segs=12, rings=4, full=False):
    """An ellipsoid cap with a flat base at height z rising rz (or, with full=True, a whole
    ellipsoid centred at z), centred at (cx, cy)."""
    if full:
        lats = [-math.pi / 2 + math.pi * k / (2 * rings) for k in range(1, 2 * rings)]
    else:
        lats = [math.pi / 2 * k / rings for k in range(rings)]
    out = [[(cx + rx * math.cos(la) * math.cos(2 * math.pi * (i + 0.5) / segs),
             cy + ry * math.cos(la) * math.sin(2 * math.pi * (i + 0.5) / segs), z + rz * math.sin(la))
            for i in range(segs)] for la in lats]
    out.append([(cx, cy, z + rz)])
    if full:
        out.insert(0, [(cx, cy, z - rz)])
    return ring_loft(bm, out, mat_index, cap_start=not full, cap_end=False)


def at_x(bm, x, fn):
    """Run a builder that builds on X = 0 (common.loft) and move what it made to X = x."""
    start = len(bm.verts)
    fn()
    common.shift_x(bm, start, x)


def mirror_x(bm, x0, start=0):
    """Mirror the geometry added since vertex `start` about X = x0 (adds the mirrored copy)."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    ret = bmesh.ops.duplicate(bm, geom=list(verts) + faces)
    new_verts = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in new_verts:
        v.co.x = 2 * x0 - v.co.x
    new_faces = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=new_faces)


def rolled(objects, angle, x0, suffix, collection):
    """Copies of `objects` turned about the craft's long axis (the line X = x0, Z = 0) by `angle`
    radians: positive lifts the left side (-X), negative the right. Baked into new meshes."""
    m = Matrix.Translation((x0, 0, 0)) @ Matrix.Rotation(angle, 4, "Y") @ Matrix.Translation((-x0, 0, 0))
    out = []
    for obj in objects:
        mesh = obj.data.copy()
        mesh.name = f"{obj.name}{suffix}"
        mesh.transform(m)
        copy = bpy_object(f"{obj.name}{suffix}", mesh, collection)
        out.append(copy)
    return out


def bpy_object(name, mesh, collection):
    import bpy
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def frame_sprites(sprite, indices):
    """The sprites entry (sheet, size, frames) narrowed to the given frame indices."""
    out = []
    for s in sprite["sprites"]:
        frames = [f for f in s["frames"] if f in indices]
        if frames:
            out.append({**s, "frames": frames})
    return out


def run(name, build, file):
    """Build, export every model and, with -- --preview <png>, preview each one: the first at the
    path given, the others beside it as <model>.png, each against its own first frame.

    `build(sprite)` returns a list of (model_name, objects, sprites) to export."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        for k, (model, objects, sprites) in enumerate(models):
            first = sprites[0]["frames"][0]
            frame = next(f for f in sprite["frames"] if f["index"] == first)
            ref = root / "reference" / "models" / name / frame["image"]
            path = out if k == 0 else out.parent / f"{model}.png"
            common.render_preview(objects, str(path), ref, size=frame["size"])
    return sprite


def ellipse_loft(bm, x0, sections, sides=12, mats=0, cap_start=True, cap_end=True):
    """Loft elliptical rings along Y at X = x0. Sections are (y, half_width, half_height, z); a
    section with zero width and height is a point. `mats` is one index or one per band."""
    rings = []
    for y, w, h, z in sections:
        if w == 0 and h == 0:
            rings.append([(x0, y, z)])
            continue
        rings.append([(x0 + w * math.cos(2 * math.pi * (i + 0.5) / sides), y,
                       z + h * math.sin(2 * math.pi * (i + 0.5) / sides)) for i in range(sides)])
    return ring_loft(bm, rings, mats, cap_start=cap_start, cap_end=cap_end)


def wing_loft(bm, sections, mats=0, z_tip_lift=0.0):
    """A wing (or tailplane) lofted across X from aerofoil sections (x, y_lead, y_trail,
    half_thickness, z): y_lead is the leading edge (towards the nose, lower Y for a craft flying down
    the screen), y_trail the trailing edge. Thickest a third of the way back from the leading edge."""
    rings = []
    for x, yl, yt, t, z in sections:
        d = yt - yl
        rings.append([(x, yt, z), (x, yl + d * 0.6, z + t * 0.8), (x, yl + d * 0.25, z + t),
                      (x, yl, z), (x, yl + d * 0.25, z - t * 0.7), (x, yl + d * 0.6, z - t * 0.55)])
    return ring_loft(bm, rings, mats)


def side_plate(bm, x, outline_yz, thickness, mat_index=0):
    """A thin upright plate (a tail fin) at X = x: `outline_yz` is its outline as (y, z) points."""
    t = thickness / 2
    left = [bm.verts.new((x - t, y, z)) for y, z in outline_yz]
    right = [bm.verts.new((x + t, y, z)) for y, z in outline_yz]
    bm.faces.new(left).material_index = mat_index
    bm.faces.new(list(reversed(right))).material_index = mat_index
    n = len(outline_yz)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((left[i], left[j], right[j], right[i])).material_index = mat_index


def rocking_models(name, sprite, level_objects, x0, angles, collection):
    """One model per frame of a craft that rocks side to side: frame k is the level build turned by
    angles[k] (radians, positive lifts the left side) about its long axis X = x0. Models are named
    name, name-f2, name-f3, ... Returns the list of (model_name, objects, sprites) for run()."""
    frames = [f["index"] for f in sprite["frames"]]
    models = []
    for k, (index, angle) in enumerate(zip(frames, angles)):
        model = name if k == 0 else f"{name}-f{k + 1}"
        objs = level_objects if angle == 0 else rolled(level_objects, angle, x0, f"_f{k + 1}", collection)
        models.append((model, objs, frame_sprites(sprite, [index])))
    return models


def build_tailplane(sprite, name, remap=None):
    """The straight-winged grey fighter of newshf-123 (and newshf-77, the same craft in blue-grey:
    remap the indices). Level frame: fuselage down column 12 with a needle nose (rows 20-26), a
    straight wing across rows 12-16 (columns 3-21) with chamfered leading tips, a tailplane at rows
    3-5 (columns 7-17), an upright fin over the tail (rows 1-6) and a dark canopy where the wing
    meets the fuselage (rows 13-16). Returns (objects, collection, x0)."""
    P = 1 / 12
    X0 = px(12)
    coll = common.reset_collection(name)
    pal = palette(sprite, name, remap)
    mats = [
        pal(7, metallic=0.55, roughness=0.4),  # 0 wing grey
        pal(8, metallic=0.6, roughness=0.35),  # 1 fuselage grey
        pal(11, metallic=0.6, roughness=0.25),  # 2 bright spine
        pal(6, metallic=0.55, roughness=0.45),  # 3 tailplane
        pal(2, metallic=0.4, roughness=0.12),  # 4 dark canopy
        pal(10, metallic=0.6, roughness=0.3),  # 5 light nose spine / fin
    ]
    WING, BODY, SPINE, TAILP, CANOPY, LIGHT = range(6)
    bm = bmesh.new()

    # Fuselage: (row edge, half width px, half height px).
    body = [(2.2, 0.0, 0.0), (2.6, 1.0, 0.9), (3.5, 1.6, 1.4), (6.0, 1.5, 1.5), (10.5, 1.5, 1.6),
            (12.0, 2.2, 1.9), (16.5, 2.5, 2.0), (18.6, 2.4, 1.9), (19.8, 1.6, 1.5), (23.6, 1.4, 1.2),
            (24.2, 0.7, 0.7), (26.6, 0.45, 0.45), (27.0, 0.0, 0.0)]
    ellipse_loft(bm, X0, [(ey(r), w * P, h * P, 0.0) for r, w, h in body], sides=10, mats=BODY)
    # Bright spine along the top behind the wing (rows 6-11) and down the nose (rows 19-23).
    ellipse_loft(bm, X0, [(ey(r), w * P, 0.35 * P, z) for r, w, z in
                          ((5.8, 0.0, 0.11), (6.5, 0.6, 0.12), (10.5, 0.6, 0.125), (11.5, 0.0, 0.14))],
                 sides=6, mats=SPINE)
    ellipse_loft(bm, X0, [(ey(r), w * P, 0.3 * P, z) for r, w, z in
                          ((18.8, 0.0, 0.14), (19.6, 0.7, 0.12), (23.4, 0.6, 0.095), (24.1, 0.0, 0.07))],
                 sides=6, mats=LIGHT)

    # Wing, rows 12-16 (17 at the root), columns 3-21, chamfered at the leading tips.
    half = 9.5  # px from the centre line to the tip
    wing = [(-half, 16, 12, 0.35, 0.0), (-6.5, 17, 12, 0.6, 0.0), (0, 17, 12, 1.0, 0.0),
            (6.5, 17, 12, 0.6, 0.0), (half, 16, 12, 0.35, 0.0)]
    wing_loft(bm, [(X0 + x * P, ey(yl), ey(yt), t * P, z) for x, yl, yt, t, z in wing], mats=WING)
    # Tailplane, rows 3-5 (6 at the root), columns 7-17.
    tail = [(-5.5, 4, 3, 0.3, 0.02), (-4.5, 5, 3, 0.45, 0.02), (-2.5, 6, 3, 0.6, 0.02), (0, 6.3, 3, 0.7, 0.02),
            (2.5, 6, 3, 0.6, 0.02), (4.5, 5, 3, 0.45, 0.02), (5.5, 4, 3, 0.3, 0.02)]
    wing_loft(bm, [(X0 + x * P, ey(yl), ey(yt), t * P, z) for x, yl, yt, t, z in tail], mats=TAILP)
    # Upright fin over the tail, swept: from the spine at rows 3-7 up to its top at rows 1-2.
    side_plate(bm, X0, [(ey(1.0), 0.07), (ey(7.0), 0.07), (ey(5.5), 0.14), (ey(2.6), 0.24), (ey(1.0), 0.24)],
               0.75 * P, mat_index=LIGHT)
    # Dark canopy where the wing meets the fuselage (rows 13-16.5).
    dome(bm, X0, ey(14.9), 0.1, 1.7 * P, 2.2 * P, 0.09, mat_index=CANOPY, segs=12, rings=4)

    obj = common.mesh_object(name, bm, mats, coll, smooth=True)
    return [obj], coll, X0
