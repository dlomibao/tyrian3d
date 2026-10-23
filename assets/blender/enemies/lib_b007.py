"""Helpers shared by batch b007's model scripts (newsh7 crystals and gun pods).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block by default (pass w=12, h=14 for size-1 sprites).
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


def tube(bm, p0, p1, radius, sides=6, mat_index=0, caps=True):
    """A thin round bar between two 3D points (pipes, struts, glowing edges)."""
    from mathutils import Vector
    a, b = Vector(p0), Vector(p1)
    axis = (b - a).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    rings = []
    for c in (a, b):
        ring = []
        for i in range(sides):
            t = 2 * math.pi * (i + 0.5) / sides
            ring.append(tuple(c + radius * (math.cos(t) * u + math.sin(t) * v)))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps)


def polyline_tube(bm, points, radius, sides=6, mat_index=0, caps=True):
    """One continuous round tube along a polyline, with mitred joints (rings face the bisector).
    `radius` can be a number or a list with one radius per point."""
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
        u = (u - t * u.dot(t)).normalized()  # carry the frame along (parallel transport)
        v = t.cross(u).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(tuple(c + radii[i] * (math.cos(a) * u + math.sin(a) * v)))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index, cap_start=caps, cap_end=caps)


def ellipse_ring(cx, cy, z, rx, ry, n=10, phase=0.5):
    """n points of an ellipse around (cx, cy) at height z (counter-clockwise from +X)."""
    return [(cx + rx * math.cos(2 * math.pi * (i + phase) / n), cy + ry * math.sin(2 * math.pi * (i + phase) / n), z)
            for i in range(n)]


def run(name, build, file):
    """The usual main: build, export every model and, with -- --preview <png>, preview the first.

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
    return sprite


def build_gunship(sprite, name, flip=False, dc=0):
    """The caged gunship of newsh7-51 (and newsh7-237, the same sprite upside down and one column
    to the right: flip=True, dc=1): a ribbed engine block with a thruster at one end, a grey bar
    cage bending into blue blades, a blue spindle, a cross wing and a grey shield-shaped hull.

    Built in newsh7-51's sprite coordinates (centre column 11), then flipped / shifted.
    Returns the list of objects."""
    import bmesh
    from mathutils import Matrix

    cx = px(11)
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731

    place = Matrix.Translation((dc / 12, 0, 0)) @ Matrix.Diagonal((1, -1 if flip else 1, 1, 1))

    def finish(bm):
        bmesh.ops.transform(bm, matrix=place, verts=bm.verts)

    def mx(c):
        """The column mirrored about the centre column."""
        return 22 - c

    # Flat-shaded plates: the engine block with its ribs and the shield hull.
    mats = [
        pal(4, metallic=0.6, roughness=0.45),  # 0 dark grey block and hull
        pal(10, metallic=0.7, roughness=0.3),  # 1 light ribs
        pal(5, metallic=0.6, roughness=0.4),  # 2 darker ribs
        pal(3, metallic=0.55, roughness=0.5),  # 3 darkest hull floor
    ]
    BLOCK, RIB, RIB2, FLOOR = range(4)
    bm = bmesh.new()
    common.slab(bm, [(ex(7), ey(7)), (ex(16), ey(7)), (ex(16), ey(3.4)), (ex(7), ey(3.4))], 0.16,
                mat_index=BLOCK)
    for c, r0, m in ((7, 3, RIB), (9, 4.6, RIB2), (11, 4.6, RIB), (13, 4.6, RIB2), (15, 3, RIB)):
        common.slab(bm, [(ex(c) + 0.01, ey(6.9)), (ex(c + 1) - 0.01, ey(6.9)), (ex(c + 1) - 0.01, ey(r0)),
                         (ex(c) + 0.01, ey(r0))], 0.08, z=0.09, mat_index=m)
    left = [(4, 17), (4.5, 22), (6.5, 24.5), (9, 26.5), (10, 27)]
    hub = [(5.6, 15), (6.2, 14)]
    outline = [(c, r) for c, r in reversed(hub)] + left
    outline = outline + [(mx(c) + 1, r) for c, r in reversed(outline)]  # edges mirror about 11.5
    common.slab(bm, [(ex(c), ey(r)) for c, r in outline], 0.12, z=-0.02, mat_index=FLOOR)
    finish(bm)
    plates = common.mesh_object(f"{name}_plates", bm, mats, coll, smooth=False)

    smats = [
        pal(8, metallic=0.65, roughness=0.35),  # 0 grey nozzle
        pal(112, metallic=0.3, roughness=0.6),  # 1 scorched mouth
        pal(119, emission_strength=3.0),  # 2 red flame
        pal(124, emission_strength=5.0),  # 3 yellow flame core
        pal(9, metallic=0.7, roughness=0.3),  # 4 grey cage bars, hull rim
        pal(56, metallic=0.5, roughness=0.3),  # 5 blue steel
        pal(62, metallic=0.6, roughness=0.2),  # 6 highlight
        pal(58, metallic=0.5, roughness=0.3),  # 7 blade / wing blue
        pal(6, metallic=0.6, roughness=0.4),  # 8 keel grey
        pal(12, metallic=0.7, roughness=0.25),  # 9 bright grey
        pal(48, metallic=0.4, roughness=0.5),  # 10 deep blue
    ]
    NOZ, MOU, FLAME, CORE, BAR, BLUE, HI, BLADE, KEEL, BRIGHT, DEEP = range(11)
    bm = bmesh.new()

    def at(x, fn):
        """Run a loft builder (which builds on X = 0) and move what it made to X = x."""
        start = len(bm.verts)
        fn()
        common.shift_x(bm, start, x)

    # Nozzle and flame out of the block (columns 9-13, rows 1-4 in the middle frame).
    at(cx, lambda: common.loft(bm, [(ey(4.5), 2.4 / 12, 0.075, 0.0), (ey(3.2), 2.5 / 12, 0.08, 0.0)],
                               sides=12, mat_index=NOZ, cap_end=False))
    at(cx, lambda: common.loft(bm, [(ey(3.25), 2.2 / 12, 0.065, 0.0), (ey(3.2), 0.0, 0.0, 0.0)],
                               sides=12, mat_index=MOU))
    at(cx, lambda: common.loft(bm, [(ey(3.6), 2.2 / 12, 0.06, 0.0), (ey(2.6), 2.0 / 12, 0.055, 0.0),
                                    (ey(1.6), 1.2 / 12, 0.04, 0.0), (ey(1.0), 0.0, 0.0, 0.0)],
                               sides=10, mat_index=FLAME))
    at(cx, lambda: common.loft(bm, [(ey(3.6), 1.2 / 12, 0.04, 0.04), (ey(2.8), 1.1 / 12, 0.04, 0.045),
                                    (ey(2.0), 0.0, 0.0, 0.04)], sides=8, mat_index=CORE))

    for side in (-1, 1):
        def sx(c, side=side):
            return px(c) if side < 0 else px(mx(c))
        # Grey cage bar from the block round the corner and down the side (rows 4-9).
        path = [(sx(6.8), row(4), 0.0), (sx(4.2), row(4), 0.0), (sx(2.9), row(4.6), 0.0),
                (sx(2.2), row(5.8), 0.0), (sx(2), row(7.2), 0.0), (sx(2.1), row(9.6), 0.0)]
        polyline_tube(bm, path, 0.6 / 12, sides=8, mat_index=BAR)
        # Blue blade bending in and down to the wing (rows 9-16).
        blade = [(sx(2.1), row(9.3), 0.0), (sx(2.8), row(11), 0.01), (sx(4.0), row(12.4), 0.02),
                 (sx(4.6), row(13.6), 0.02), (sx(4.7), row(15.2), 0.02), (sx(4.8), row(16), 0.02)]
        polyline_tube(bm, blade, 1.0 / 12, sides=8, mat_index=BLADE)
        polyline_tube(bm, [(x, y, z + 0.07) for x, y, z in blade[:4]], 0.4 / 12, sides=6, mat_index=HI)
        # Axle from the spindle's waist out to the blade (row 13).
        tube(bm, (sx(4.8), row(13.5), 0.02), (sx(9.6), row(13.5), 0.02), 0.9 / 12, sides=8, mat_index=BAR)
        # Blue strut on the hull (columns 6-8, rows 16-20).
        at(sx(7.6), lambda: common.loft(bm, [(row(20.8), 0.0, 0.0, 0.04), (row(20.3), 1.1 / 12, 0.05, 0.04),
                                             (row(16.5), 1.1 / 12, 0.05, 0.05), (row(15.8), 0.0, 0.0, 0.05)],
                                        sides=8, mat_index=BLADE))
        at(sx(6.6), lambda: common.loft(bm, [(row(20.6), 0.0, 0.0, 0.03), (row(20.2), 0.35 / 12, 0.04, 0.03),
                                             (row(17), 0.35 / 12, 0.04, 0.04), (row(16.6), 0.0, 0.0, 0.04)],
                                        sides=6, mat_index=DEEP))
        # Grey rim round the lower hull (columns 4-9, rows 17-25), brightest at the lower corner.
        rim = [(sx(4.4), row(17.4), 0.03), (sx(4.9), row(19), 0.04), (sx(5.1), row(21.5), 0.04),
               (sx(6.4), row(22.8), 0.045), (sx(7.9), row(24.1), 0.045), (sx(9.2), row(25.5), 0.04)]
        polyline_tube(bm, rim, 0.65 / 12, sides=8, mat_index=BAR)
        polyline_tube(bm, [(x, y, z + 0.035) for x, y, z in rim[2:5]], 0.35 / 12, sides=6, mat_index=BRIGHT)

    # Cross wing along row 16, tapering to the tips at columns 1 and 21.
    wing = [(px(c), row(16), 0.03) for c in (0.6, 3, 7, 15, 19, 21.4)]
    polyline_tube(bm, wing, [0.45 / 12, 0.8 / 12, 0.9 / 12, 0.9 / 12, 0.8 / 12, 0.45 / 12], sides=8,
                  mat_index=BLADE)
    polyline_tube(bm, [(x, y, z + 0.06) for x, y, z in wing[:3]], [0.2 / 12, 0.3 / 12, 0.3 / 12], sides=6,
                  mat_index=HI)

    # The spindle's upper bulb (rows 8-13) and neck, running into the hull.
    spindle = [(7.4, 1.4), (8, 1.6), (9, 2.3), (10, 3.0), (11, 3.4), (12, 2.5), (13, 1.7), (14.2, 1.5), (15.5, 2.0)]
    at(cx, lambda: common.loft(bm, [(row(rr), w / 12, w * 0.6 / 12, 0.0) for rr, w in spindle],
                               sides=12, mat_index=BLUE))
    at(cx, lambda: common.loft(bm, [(row(rr), 0.45 / 12, 0.3 / 12, w * 0.6 / 12 - 0.01)
                                    for rr, w in spindle[2:-3]], sides=6, mat_index=HI))
    # Keel down the hull's middle (columns 10-12, rows 15-26), with a bright top and tip.
    keel = [(26.7, 0.0, 0.0), (26.2, 1.2, 0.05), (25, 1.6, 0.07), (21, 1.6, 0.08), (17, 1.6, 0.09),
            (15.4, 1.5, 0.08), (15.0, 0.0, 0.0)]
    at(cx, lambda: common.loft(bm, [(row(rr), w / 12, h, 0.03) for rr, w, h in keel], sides=10, mat_index=KEEL))
    at(cx, lambda: common.loft(bm, [(row(16.6), 1.62 / 12, 0.091, 0.03), (row(15.8), 1.55 / 12, 0.085, 0.03)],
                               sides=10, mat_index=BRIGHT))
    at(cx, lambda: common.loft(bm, [(row(25.6), 1.62 / 12, 0.071, 0.03), (row(24.8), 1.62 / 12, 0.071, 0.03)],
                               sides=10, mat_index=BRIGHT))
    finish(bm)
    parts = common.mesh_object(name, bm, smats, coll, smooth=True)
    return [parts, plates]
