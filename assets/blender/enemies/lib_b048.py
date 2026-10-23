"""Helpers shared by batch b048's model scripts (newsh2 rock walls with purple octagon plates, and
two newsh2 craft).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block by default.
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


def px(c, w=24):
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    return (h / 2 - (r + 0.5)) / 12


def ex(c, w=24):
    return (c - w / 2) / 12


def ey(r, h=28):
    return (h / 2 - r) / 12


def _mark(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def ellipsoid(bm, x, y, z, rx, ry, rz, mat=0, segments=12, rings=6, smooth=True):
    """An ellipsoid centred at (x, y, z) units with radii in units."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((x + v.co.x * rx, y + v.co.y * ry, z + v.co.z * rz))
    _mark(bm, before, mat, smooth)


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    """Extrude an XY outline (units, either winding) from z0 to z1."""
    before = set(bm.faces)
    if _area(outline) < 0:
        outline = list(reversed(outline))
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    _mark(bm, before, mat, smooth)


def box(bm, x0, y0, x1, y1, z0, z1, mat=0):
    prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat=mat)


def _area(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) / 2


def inset(outline, d):
    """Offset a convex counter-clockwise outline inwards by d (units)."""
    n = len(outline)
    lines = []
    for i in range(n):
        a, b = Vector(outline[i]), Vector(outline[(i + 1) % n])
        t = (b - a).normalized()
        nrm = Vector((-t.y, t.x))  # inward for CCW
        lines.append((a + nrm * d, t))
    out = []
    for i in range(n):
        p0, t0 = lines[i - 1]
        p1, t1 = lines[i]
        den = t0.x * t1.y - t0.y * t1.x
        if abs(den) < 1e-9:
            out.append(tuple(p1))
            continue
        s = ((p1.x - p0.x) * t1.y - (p1.y - p0.y) * t1.x) / den
        out.append(tuple(p0 + t0 * s))
    return out


def bevel_plate(bm, outline, z0, z1, bevel, mats, light=(-1, 1)):
    """A raised plate with chamfered top edges, shaded like the sprite: `mats` is
    (top, light side, mid side, dark side) material indices; sides facing `light` (an XY
    direction, the sprite's top-left by default) get the light one."""
    if _area(outline) < 0:
        outline = list(reversed(outline))
    top_o = inset(outline, bevel)
    zb = z1 - bevel * 0.8
    rings = [[bm.verts.new((x, y, z0)) for x, y in outline],
             [bm.verts.new((x, y, zb)) for x, y in outline],
             [bm.verts.new((x, y, z1)) for x, y in top_o]]
    top, lt, mid, dk = mats
    lx, ly = light
    ln = math.hypot(lx, ly)
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        a, b = Vector(outline[i]), Vector(outline[j])
        t = (b - a).normalized()
        out = Vector((t.y, -t.x))
        d = (out.x * lx + out.y * ly) / ln
        m = lt if d > 0.3 else dk if d < -0.3 else mid
        for r0, r1 in zip(rings, rings[1:]):
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = m
            f.smooth = False
    f = bm.faces.new(rings[-1])
    f.material_index = top
    f.smooth = False
    f = bm.faces.new(list(reversed(rings[0])))
    f.material_index = top
    f.smooth = False


def sweep(bm, pts, sides=8, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along 3D points [(x, y, z, half_width, half_height)] in units; rings stand
    perpendicular to the path (in XY), width across it, height along Z. A zero-size ring is a tip."""
    up = Vector((0, 0, 1))
    P = [Vector(p[:3]) for p in pts]
    rings = []
    for i, (x, y, z, w, h) in enumerate(pts):
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
        t.z = 0
        if t.length < 1e-9:
            t = Vector((0, 1, 0))
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(P[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(P[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
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


def mirror_x(bm, faces_before=None):
    """Mirror everything built so far about X = 0 (a duplicate, not a modifier)."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


# --- rock walls with purple octagon plates (newsh2 273-283) -----------------------------------

def composite_png(root, tiles, out, pad_to=None):
    """The tiles' sprites (first frames, side by side in a row) as one image, padded to the 24:28
    shape that render_preview expects. Returns (path, size in tiles)."""
    import numpy as np
    n = len(tiles)
    W = 24 * n
    H = 28 * n
    img = np.zeros((H, W, 4), dtype=np.float32)
    y0 = (H - 28) // 2
    for i, name in enumerate(tiles):
        data = common.load_sprite(root, name)
        for r, rw in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(rw):
                if v >= 0:
                    img[y0 + r, 24 * i + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out, n * 2


# Rocks as (x, y, rx, ry, rz, material key) in tile pixels (x, y are pixel-edge coordinates, so
# column c's centre is c + 0.5); "edge" rocks sit on every tile boundary (both ends included).
WALL_ROCKS = {
    "top": {
        "all": [(6.5, 23.0, 4.2, 3.4, 0.12, "rock"), (12.5, 26.0, 3.5, 2.2, 0.07, "rock_d"),
                (18.0, 25.3, 4.5, 3.0, 0.10, "rock"), (6.5, 27.8, 4.6, 2.5, 0.11, "beige"),
                (21.5, 27.0, 3.0, 1.8, 0.06, "rock_d"), (2.0, 26.0, 2.6, 2.2, 0.07, "rock_d")],
        "edge": [(0.0, 19.6, 5.4, 5.0, 0.15, "rock_l")],
        "left": [(5.0, 1.6, 5.4, 2.9, 0.12, "beige"), (11.6, 1.8, 1.5, 2.2, 0.07, "rock"),
                 (1.6, 10.0, 2.6, 5.2, 0.11, "rock"), (4.5, 5.3, 3.2, 1.6, 0.05, "rock_d")],
        "right": [(15.6, 1.8, 3.6, 2.5, 0.10, "rock"), (21.4, 2.0, 2.6, 2.4, 0.10, "rock"),
                  (22.0, 8.0, 2.5, 4.2, 0.12, "rock_l"), (22.4, 13.0, 1.6, 2.2, 0.05, "rock_d")],
    },
    "bottom": {
        "all": [(5.0, 1.6, 5.4, 2.9, 0.12, "beige"), (15.6, 2.0, 3.0, 2.5, 0.11, "rock_l"),
                (21.4, 1.8, 2.6, 2.3, 0.10, "rock"), (11.6, 1.8, 1.5, 2.2, 0.07, "rock"),
                (4.0, 5.5, 3.0, 1.6, 0.05, "rock_d")],
        "edge": [(0.0, 8.0, 3.8, 3.6, 0.12, "rock_l")],
        "left": [(6.5, 23.0, 4.2, 3.4, 0.12, "rock"), (6.5, 27.8, 4.6, 2.5, 0.11, "beige"),
                 (1.8, 19.6, 3.0, 4.8, 0.14, "rock_l"), (10.0, 23.5, 2.0, 2.0, 0.07, "rock"),
                 (1.6, 13.0, 1.6, 2.2, 0.06, "rock")],
        "right": [(21.8, 19.6, 3.0, 4.8, 0.14, "rock_l"), (18.5, 25.5, 3.6, 2.6, 0.10, "rock"),
                  (21.5, 26.5, 2.5, 1.8, 0.06, "rock_d"), (22.4, 13.0, 1.6, 2.2, 0.05, "rock_d")],
    },
}

# The purple octagon plate every tile has (pixel edges).
OCTAGON = [(8, 4), (16, 4), (21, 9), (21, 15), (16, 20), (8, 20), (3, 15), (3, 9)]


def build_wall(sprite, name, tag, kinds, band):
    """A row of rock-wall tiles, each with a purple octagon plate, and a purple band behind the
    plates along the top (band="top") or bottom ("bottom") of the row. `kinds` is per tile
    "left", "mid" or "right" (the band stops part way into the end tiles). Built in assembly
    coordinates: tile i spans pixel columns 24i..24i+24, the row's centre is the origin.
    Returns (object, [(cx, cy) per tile centre for split_assembly])."""
    n = len(kinds)
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.1, roughness=0.9),  # 0 rock bed and crevices
        pal(7, metallic=0.1, roughness=0.85),  # 1 rock (shadowed)
        pal(8, metallic=0.1, roughness=0.8),  # 2 rock
        pal(10, metallic=0.1, roughness=0.75),  # 3 rock (lit)
        pal(170, metallic=0.05, roughness=0.8),  # 4 beige stone
        pal(88, metallic=0.35, roughness=0.45),  # 5 purple plate
        pal(90, metallic=0.35, roughness=0.4),  # 6 purple lit edge / panel
        pal(89, metallic=0.35, roughness=0.45),  # 7 purple mid
        pal(86, metallic=0.35, roughness=0.5),  # 8 purple shadowed edge
    ]
    BED, ROCK_D, ROCK, ROCK_L, BEIGE, PLATE, LIT, MID, SHADE = range(9)
    key = {"rock_d": ROCK_D, "rock": ROCK, "rock_l": ROCK_L, "beige": BEIGE}
    W = 24 * n
    X = lambda c: (c - W / 2) / 12  # noqa: E731
    Y = lambda r: (14 - r) / 12  # noqa: E731
    bm = bmesh.new()

    # Rock bed under the whole row.
    box(bm, X(0), Y(28), X(W), Y(0), -0.2, -0.03, mat=BED)

    rocks = WALL_ROCKS[band]
    for i, kind in enumerate(kinds):
        o = 24 * i
        for x, y, rx, ry, rz, m in rocks["all"] + rocks.get(kind, []):
            ellipsoid(bm, X(o + x), Y(y), -0.03, rx * PX, ry * PX, rz, mat=key[m])
    for i in range(n + 1):
        for x, y, rx, ry, rz, m in rocks["edge"]:
            ellipsoid(bm, X(24 * i + x), Y(y), -0.03, rx * PX, ry * PX, rz, mat=key[m])

    # The purple band behind the plates, with raised panels between them.
    def band_span(kind):
        return {"left": (12.5 if band == "bottom" else 13, 24), "mid": (0, 24), "right": (0, 12)}[kind]
    x0 = 24 * 0 + band_span(kinds[0])[0]
    x1 = 24 * (n - 1) + band_span(kinds[-1])[1]
    by0, by1 = (0, 11) if band == "top" else (11, 28)
    box(bm, X(x0), Y(by1), X(x1), Y(by0), -0.07, 0.05, mat=PLATE)
    pmats = (LIT, LIT, MID, SHADE)
    pmats2 = (MID, LIT, MID, SHADE)
    for i, kind in enumerate(kinds):
        o = 24 * i
        a, b = band_span(kind)
        if band == "top":
            panels = [((5, 0), (12, 4), pmats), ((13, 0), (19, 4), pmats2)]
        else:
            panels = [((5, 20.2), (12, 28), pmats), ((13, 20.2), (19, 28), pmats2)]
        for (pa, pb, pm) in panels:
            if pa[0] >= a and pb[0] <= b:
                bevel_plate(bm, [(X(o + pa[0]), Y(pb[1])), (X(o + pb[0]), Y(pb[1])),
                                 (X(o + pb[0]), Y(pa[1])), (X(o + pa[0]), Y(pa[1]))],
                            -0.0, 0.08, 0.6 * PX, pm)
    # Plates straddling the boundaries between tiles, between the octagons.
    for i in range(1, n):
        o = 24 * i
        if band == "top":
            pa, pb, pm = (o - 3, 4.6), (o + 3, 11), pmats
        else:
            pa, pb, pm = (o - 4, 11.6), (o + 4, 28), pmats2
        bevel_plate(bm, [(X(pa[0]), Y(pb[1])), (X(pb[0]), Y(pb[1])), (X(pb[0]), Y(pa[1])), (X(pa[0]), Y(pa[1]))],
                    0.0, 0.09, 0.8 * PX, pm)

    # The octagon plate on every tile.
    for i in range(n):
        o = 24 * i
        bevel_plate(bm, [(X(o + c), Y(r)) for c, r in OCTAGON], -0.05, 0.21, 1.3 * PX,
                    (PLATE, LIT, MID, SHADE))

    obj = to_object(name, bm, mats, coll)
    centres = [(24 * i + 12 - W / 2, 0) for i in range(n)]
    return obj, centres


def merged_sprite(root, pieces):
    """The first piece's sprite.json with every piece's colours, so any piece's index is valid."""
    data = common.load_sprite(root, pieces[0])
    for p in pieces[1:]:
        data["colors"].update(common.load_sprite(root, p)["colors"])
    return data


def wall_main(script_file, name, tiles, kinds, band):
    """Build, split and export a wall assembly; tiles are piece names per tile (a name may repeat,
    each distinct piece is exported once from its first tile)."""
    root = common.repo_root(script_file)
    pieces = list(dict.fromkeys(tiles))
    sprite = merged_sprite(root, pieces)
    obj, centres = build_wall(sprite, name, name.replace("assembly-", "a"), kinds, band)
    layout, seen = [], set()
    for t, (cx, cy) in zip(tiles, centres):
        if t not in seen:
            seen.add(t)
            layout.append((t, cx, cy))
    parts = common.split_assembly(obj, layout)
    for p in pieces:
        data = common.load_sprite(root, p)
        common.export_sprite_model(root, [parts[p]], f"enemies/{p}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref, size = composite_png(root, tiles, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=size, view_px=480)
        for p in pieces:
            data = common.load_sprite(root, p)
            img = root / "reference" / "models" / p / data["frames"][0]["image"]
            common.render_preview([parts[p]], str(out.parent / f"{p}.png"), str(img), size=2)
