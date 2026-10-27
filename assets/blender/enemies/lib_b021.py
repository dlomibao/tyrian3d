"""Helpers shared by batch b021's model scripts (tyrian.shp#10 bonus items: spinning coins, gems).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block by default (pass w=12, h=14 for size-1 sprites).
ring_loft, tube, polyline_tube and ellipse_ring are copied from lib_b007.
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


def frame_sprites(sprite, indices):
    """The sprite.json `sprites` list cut down to the frames in `indices` (for one model of an
    animation whose frames change shape)."""
    out = []
    for s in sprite["sprites"]:
        frames = [f for f in s["frames"] if f in indices]
        if frames:
            out.append(dict(s, frames=frames))
    return out


def run(name, build, file):
    """The usual main: build, export every model and, with -- --preview <png>, preview each one
    (the first to <png>, the others to <png stem>-<model suffix>.png) beside its first frame.

    `build(sprite)` returns a list of (model_name, objects, sprites) to export."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        images = {(f["sheet"], f["index"]): f for f in sprite["frames"]}
        for i, (model, objects, sprites) in enumerate(models):
            s = sprites[0]
            frame = images[(s["sheet"], s["frames"][0])]
            ref = root / "reference" / "models" / name / frame["image"]
            path = out if i == 0 else out.with_name(f"{out.stem}{model[len(name):]}.png")
            common.render_preview(objects, str(path), ref, size=frame["size"])
    return sprite


# --- Spinning coins (tyrian10-1, -7, -26) ---------------------------------------------------------

# Each coin is drawn in six frames as it spins about the screen's vertical axis: face on, turning,
# edge on, and back. Frame k's coin is turned by COIN_ANGLES[k] degrees about Y; the angles come
# from each frame's width (9, 7, 5, 3, 5, 7 px inside the outline) with a 9 px coin 3 px thick;
# the sign puts the coin's bright edge on the side the sprite shows it (right, then left).
COIN_ANGLES = [0, -60, -76, 90, 76, 60]


def coin_models(sprite, name, face, rim, edge, metallic=0.55, roughness=0.35):
    """One model per frame of a spinning coin: a thick disc with a raised rim and bevelled edge,
    turned about Y to match the frame. `face`, `rim`, `edge` are palette indices."""
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    FACE, RIM, EDGE = range(3)
    frames = [f["index"] for f in sprite["frames"]]
    cx, cy = px(5, 12), row(6, 14)  # the coin's centre: columns 1-9, rows 2-10
    u = 1 / 12
    # (radius px, z px) from the back face's centre round the edge to the front face's centre.
    profile = [(0.0, -1.3), (3.0, -1.3), (3.6, -1.5), (4.5, -0.75), (4.5, 0.75), (3.6, 1.5),
               (3.0, 1.3), (0.0, 1.3)]
    band_mats = [FACE, RIM, EDGE, EDGE, EDGE, RIM, FACE]
    models = []
    for k, frame in enumerate(frames):
        model = name if k == 0 else f"{name}-f{k + 1}"
        coll = common.reset_collection(model)
        mats = [pal(face, metallic=metallic, roughness=roughness),
                pal(rim, metallic=metallic, roughness=roughness * 0.8),
                pal(edge, metallic=metallic, roughness=roughness)]
        bm = bmesh.new()
        rings = []
        for r, z in profile:
            if r == 0:
                rings.append([(0.0, 0.0, z * u)])
            else:
                rings.append(ellipse_ring(0.0, 0.0, z * u, r * u, r * u, n=20))
        ring_loft(bm, rings, band_mats)
        turn = Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(math.radians(COIN_ANGLES[k % 6]), 4, "Y")
        bmesh.ops.transform(bm, matrix=turn, verts=bm.verts)
        obj = common.mesh_object(model, bm, mats, coll, smooth=True)
        _sharpen(obj, 50)
        models.append((model, [obj], frame_sprites(sprite, [frame])))
    return models


def _sharpen(obj, degrees):
    """Smooth shading with sharp edges past `degrees` (keeps a coin's rim crisp)."""
    mesh = obj.data
    try:
        mesh.set_sharp_from_angle(angle=math.radians(degrees))
    except AttributeError:  # older Blender: auto smooth
        mesh.use_auto_smooth = True
        mesh.auto_smooth_angle = math.radians(degrees)


# --- Gems (tyrian10-14, -32, -57, -76) -----------------------------------------------------------

def gem_model(sprite, name, body, crown, ridge, inner, core, glow=0.0, core_glow=2.0, facets=True,
              metallic=0.25, roughness=0.18, brighten=False):
    """A cut gem, diamond-shaped from above (columns 1-11, rows 2-12, centre column 6, row 7):
    a flat-shaded crown rising to a bright point over a deeper pavilion. `facets` adds the ring of
    crown facets that the brighter gems show as a bright inner outline. Palette indices: `body`
    for the pavilion, `crown` for the outer crown facets, `ridge` for the facet ring, `inner` for the
    crown's middle and `core` for the top point (emissive). `glow` makes the crown glow too (gems that pulse with palette cycling).
    `brighten` animates a gem whose frames step every colour one shade up (to the top of its
    16-colour ramp) per frame: palette_material frames= (DECISIONS.md D17)."""
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    if brighten:
        later = [f["index"] for f in sprite["frames"]][1:]

        def pal(i, **kw):
            steps = {f: min(i + k, i | 15) for k, f in enumerate(later, 1)}
            return common.palette_material(sprite, i, f"{name}-pulse", frames=steps, **kw)
    mats = [pal(body, metallic=metallic, roughness=roughness + 0.1),
            pal(crown, metallic=metallic, roughness=roughness, emission_strength=glow),
            pal(ridge, metallic=metallic, roughness=roughness, emission_strength=glow * 1.3),
            pal(inner, metallic=metallic, roughness=roughness, emission_strength=glow * 1.6),
            pal(core, metallic=0.1, roughness=0.15, emission_strength=core_glow)]
    BODY, CROWN, RIDGE, INNER, CORE = range(5)
    cx, cy = px(6, 12), row(7, 14)
    g = 5.5 / 12  # girdle: tip to centre

    def diamond(s, z, twist=0.0):
        """8 points round a diamond (tips N, W, S, E and the edge midpoints) scaled by s."""
        pts = []
        for i in range(8):
            a = math.pi / 2 + i * math.pi / 4
            r = s if i % 2 == 0 else s * (math.sqrt(0.5) + twist)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
        return pts

    bm = bmesh.new()
    # Pavilion up to the girdle, then the crown rising steadily to the bright point.
    rings = [[(cx, cy, -0.21)], diamond(g, -0.04), diamond(g, 0.02)]
    mats_b = [BODY, BODY]
    if facets:
        rings += [diamond(g * 0.74, 0.09, twist=0.06), diamond(g * 0.56, 0.14), diamond(g * 0.28, 0.21)]
        mats_b += [CROWN, RIDGE, INNER]
    else:
        rings += [diamond(g * 0.6, 0.12), diamond(g * 0.28, 0.2)]
        mats_b += [CROWN, INNER]
    rings += [[(cx, cy, 0.26)]]
    mats_b += [CORE]
    ring_loft(bm, rings, mats_b)
    obj = common.mesh_object(name, bm, mats, coll, smooth=False)
    return [(name, [obj], sprite["sprites"])]
