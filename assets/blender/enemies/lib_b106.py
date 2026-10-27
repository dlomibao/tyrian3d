"""Helpers shared by batch b106's model scripts (tyrian.shp#10 ground objects: a key, crystals, a
strawberry and grey light capsules).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block by default (pass w=12, h=14 for size-1 sprites).
Ground objects sit with their base at z = 0.
"""

import math
import sys
from pathlib import Path

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


def ring_loft(bm, rings, mats, cap_start=True, cap_end=True, cap_mats=None):
    """Join rings of 3D points (all the same length, or a single point for a tip) in order.

    `mats` gives a material index per band between consecutive rings (an int applies to all, a
    list of ints per band, or a list of lists per band and segment). Caps close the first/last ring
    (with cap_mats = (start, end) material indices, default the first/last band's)."""
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]

    def mat(band, seg):
        m = mats
        if isinstance(m, list):
            m = m[band]
        if isinstance(m, list):
            m = m[seg]
        return m
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
            bm.faces.new(face).material_index = mat(b, i)
    first = mat(0, 0) if not cap_mats else cap_mats[0]
    last = mat(len(verts) - 2, 0) if not cap_mats else cap_mats[1]
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0]))).material_index = first
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1]).material_index = last
    return verts


def polyline_tube(bm, points, radius, sides=6, mat_index=0, caps=True, flat=1.0):
    """One continuous round tube along a polyline, with mitred joints (rings face the bisector).
    `radius` can be a number or a list with one radius per point. `flat` scales the tube's
    height (z) relative to its width when it runs in the XY plane."""
    from mathutils import Vector
    pts = [Vector(p) for p in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    tangents = []
    for i in range(len(pts)):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tangents.append(t.normalized())
    rings = []
    for c, t, r in zip(pts, tangents, radii):
        up = Vector((0, 0, 1))
        u = t.cross(up)
        if u.length < 1e-6:
            u = Vector((1, 0, 0))
        u.normalize()
        v = u.cross(t).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(tuple(c + r * math.cos(a) * u + r * flat * math.sin(a) * v))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps)


def spheroid(bm, centre, radii, sides=16, rings=8, mat_index=0, z_cut=None, mat_fn=None):
    """An ellipsoid with its poles on Z. With z_cut (a height relative to the centre, e.g. -0.5*rz)
    the bottom is sliced off flat there (for things resting on the ground). mat_fn(lat, lon) can
    pick a material per face from its centre's direction (lat -90..90, lon 0..360 from +X)."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    lats = []
    lo = -math.pi / 2
    if z_cut is not None:
        lo = math.asin(max(-1.0, min(1.0, z_cut / rz)))
    for i in range(rings + 1):
        lats.append(lo + (math.pi / 2 - lo) * i / rings)
    ring_pts = []
    for la in lats[:-1]:
        ring_pts.append([(cx + rx * math.cos(la) * math.cos(2 * math.pi * (k + 0.5) / sides),
                          cy + ry * math.cos(la) * math.sin(2 * math.pi * (k + 0.5) / sides),
                          cz + rz * math.sin(la)) for k in range(sides)])
    ring_pts.append([(cx, cy, cz + rz)])
    if z_cut is None:
        ring_pts[0] = [(cx, cy, cz - rz)]
    if mat_fn is None:
        mats = mat_index
    else:
        mats = []
        for b in range(len(lats) - 1):
            la = math.degrees((lats[b] + lats[b + 1]) / 2)
            mats.append([mat_fn(la, 360 * (k + 1.0) / sides % 360) for k in range(sides)])
    return ring_loft(bm, ring_pts, mats, cap_start=z_cut is not None, cap_end=False)


def prism(bm, outline, z0, z1, mat_index=0):
    """Extrude an XY outline (counter-clockwise) from z0 up to z1."""
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0):
    prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat_index)


def inset_outline(outline, d):
    """Move each vertex of a closed XY outline inward by `d` (convex-ish outlines)."""
    n = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1]
               for i in range(n))
    sign = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = outline[i - 1], outline[i], outline[(i + 1) % n]
        normals = []
        for a, b in ((p0, p1), (p1, p2)):
            ex_, ey_ = b[0] - a[0], b[1] - a[1]
            length = math.hypot(ex_, ey_) or 1.0
            normals.append((-ey_ / length * sign, ex_ / length * sign))
        nx, ny = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
        length = math.hypot(nx, ny) or 1.0
        nx, ny = nx / length, ny / length
        cos_half = max(0.35, nx * normals[0][0] + ny * normals[0][1])
        out.append((p1[0] + nx * d / cos_half, p1[1] + ny * d / cos_half))
    return out


def bevel_prism(bm, outline, z0, z1, bevel, bevel_h=None, mat_index=0, top_mat=None):
    """A prism from z0 to z1 whose top edges are chamfered inward by `bevel` over `bevel_h`."""
    bevel_h = bevel if bevel_h is None else bevel_h
    top = inset_outline(outline, bevel)
    n = len(outline)
    lo = [bm.verts.new((x, y, z0)) for x, y in outline]
    mid = [bm.verts.new((x, y, z1 - bevel_h)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in top]
    bm.faces.new(list(reversed(lo))).material_index = mat_index
    bm.faces.new(hi).material_index = mat_index if top_mat is None else top_mat
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], mid[j], mid[i])).material_index = mat_index
        bm.faces.new((mid[i], mid[j], hi[j], hi[i])).material_index = mat_index


def ellipse(cx, cy, rx, ry, n=16, phase=0.5):
    """n XY points of an ellipse, counter-clockwise from +X."""
    return [(cx + rx * math.cos(2 * math.pi * (i + phase) / n), cy + ry * math.sin(2 * math.pi * (i + phase) / n))
            for i in range(n)]


def run(name, build, file):
    """Build, export every model and, with -- --preview <png>, preview the first (-- --frames <png>:
    each of its frames).

    `build(sprite)` returns a list of (model_name, objects, sprites) to export."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / name / frame["image"]
        common.render_preview(models[0][1], out, ref, size=frame["size"])
    if "--frames" in sys.argv:  # every frame of the first model, one row each
        common.render_frame_previews(models[0][1], sys.argv[sys.argv.index("--frames") + 1], sprite, root)
    return sprite


# --- The grey light capsule (tyrian10-165 and its mirror image tyrian10-203) ---------------------

# Its profile along X: (column edge, half depth in Y in px). Rounded end caps (columns 2-4 and
# 19-22), grooves at columns 5, 9, 14 and 18, raised bands at columns 6-8 and 15-17 and a plain
# centre section between them.
CAPSULE_PROFILE = [
    (1.7, 0.0), (2.0, 1.8), (2.6, 2.9), (3.5, 4.4), (4.5, 5.5), (4.95, 6.0), (5.1, 5.4), (5.9, 5.4),
    (6.05, 7.4), (8.95, 7.4), (9.1, 6.0), (9.6, 6.0), (9.75, 6.5), (14.25, 6.5), (14.4, 6.0), (14.9, 6.0),
    (15.05, 7.4), (17.95, 7.4), (18.1, 5.6), (18.9, 5.6), (19.05, 6.4), (20.0, 5.8), (21.0, 4.8), (21.9, 3.4),
    (22.6, 2.0), (23.1, 0.0),
]
CAPSULE_YC = ey(15.5)  # its axis: rows 8-22
CAPSULE_ZC = 0.27  # axis height
CAPSULE_K = 0.52  # height / depth of the cross-section


def capsule_hy(c):
    """Half depth (units) of the capsule's profile at column edge c."""
    for (c0, h0), (c1, h1) in zip(CAPSULE_PROFILE, CAPSULE_PROFILE[1:]):
        if c0 <= c <= c1:
            t = (c - c0) / (c1 - c0) if c1 > c0 else 0.0
            return (h0 + (h1 - h0) * t) / 12
    return 0.0


def capsule_point(c, angle, lift=0.0):
    """A point on the capsule's surface at column edge c and angle (degrees; 0 = far side +Y,
    90 = top, 180 = near side -Y), pushed out by `lift` units."""
    hy = capsule_hy(c)
    a = math.radians(angle)
    return (ex(c), CAPSULE_YC + (hy + lift) * math.cos(a), CAPSULE_ZC + (hy * CAPSULE_K + lift) * math.sin(a))


def capsule_arc(c, a0, a1, lift, n=6):
    return [capsule_point(c, a0 + (a1 - a0) * i / (n - 1), lift) for i in range(n)]


def build_light_capsule(sprite, name, near_lights, lights=None):
    """The grey capsule lying along X with red light strips across its bands and end caps and a
    red and a green lamp on its centre section. tyrian10-165 has the red lights on the far side (up
    the screen) and the green lamp on the near side; tyrian10-203 (near_lights=True) the reverse.

    `lights` animates them (DECISIONS.md D17): {"strip"|"cap_strip"|"red"|"green": (palette index on
    the first frame, {frame: palette index})}, each light's colour on each frame."""
    import bmesh
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.55, roughness=0.35),  # 0 end caps
        pal(11, metallic=0.55, roughness=0.3),  # 1 raised bands
        pal(8, metallic=0.55, roughness=0.35),  # 2 centre section
        pal(3, metallic=0.5, roughness=0.5),  # 3 grooves and seams
        pal(117, roughness=0.3, emission_strength=3.0),  # 4 red light strips
        pal(120, roughness=0.2, emission_strength=4.0),  # 5 red lamp
        pal(195, roughness=0.2, emission_strength=4.0),  # 6 green lamp
    ]
    CAP, BAND, CENTRE, GROOVE, STRIP, RED, GREEN = range(7)
    CAP_STRIP = STRIP
    if lights:
        def lit(key, **kw):
            index, frames = lights[key]
            return common.palette_material(sprite, index, f"{name}-{key}", frames=frames, **kw)
        mats[STRIP:] = [lit("strip", roughness=0.3, emission_strength=3.0),
                        lit("red", roughness=0.2, emission_strength=4.0),
                        lit("green", roughness=0.2, emission_strength=4.0),
                        lit("cap_strip", roughness=0.3, emission_strength=3.0)]  # 7 end-cap strips
        CAP_STRIP = 7

    bm = bmesh.new()
    sections = [(ex(c), hy / 12, hy / 12 * CAPSULE_K, CAPSULE_ZC) for c, hy in CAPSULE_PROFILE]
    start = len(bm.verts)
    common.loft(bm, sections, sides=16, mat_index=CAP)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x, v.co.y = v.co.y, v.co.x + CAPSULE_YC
    for f in bm.faces:
        x = f.calc_center_median().x
        c = x * 12 + 12  # back to a column edge
        if c < 4.97 or c > 18.98:
            f.material_index = CAP
        elif 4.97 <= c < 6.0 or 8.97 <= c < 9.7 or 14.3 <= c < 15.0 or 17.97 <= c <= 18.98:
            f.material_index = GROOVE
        elif 6.0 <= c < 8.97 or 15.0 <= c < 17.97:
            f.material_index = BAND
        else:
            f.material_index = CENTRE
    # Seams along the centre section (rows 12 and 16).
    for angle in (55, 105):
        common_pts = [capsule_point(c, angle, 0.002) for c in (9.75, 12.0, 14.25)]
        polyline_tube(bm, common_pts, 0.3 / 12, sides=4, mat_index=GROOVE)
    body = common.mesh_object(name, bm, mats, coll, smooth=True)

    # Lights: angles are on the far side (0-90) unless near_lights, which mirrors them (180 - a).
    flip = (lambda a: 180 - a) if near_lights else (lambda a: a)
    bm = bmesh.new()
    # Red strips: columns 3 and 21 (rows 11-14) and columns 7 and 16 (rows 8-13).
    for c, a0, a1, m in ((3.5, 8, 80, CAP_STRIP), (21.5, 8, 80, CAP_STRIP), (7.5, 4, 72, STRIP), (16.5, 4, 72, STRIP)):
        polyline_tube(bm, capsule_arc(c, flip(a0), flip(a1), 0.004), 0.55 / 12, sides=6, mat_index=m)
    # The red lamp (columns 11-12, rows 9-11) and the green lamp (rows 19-22), on opposite sides.
    polyline_tube(bm, capsule_arc(12.0, flip(2), flip(50), 0.01, n=5), 1.05 / 12, sides=8, mat_index=RED)
    polyline_tube(bm, capsule_arc(12.0, flip(185), flip(125), 0.01, n=5), 1.05 / 12, sides=8, mat_index=GREEN)
    lights = common.mesh_object(f"{name}_lights", bm, mats, coll, smooth=True)
    return [body, lights]
