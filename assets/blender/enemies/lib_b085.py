"""Helpers for batch b085: the grey and red ground fortress of episode 4 (newsh9.shp).

The fortress is one big symmetric structure built from 2x2 ground enemies:
  - assembly-newsh9-85 (newsh9-47, -49, -51 over newsh9-85, -87, -89): the lower 72 x 56 px,
  - newsh9-28 and newsh9-32: the two pieces 14 px above newsh9-47 and newsh9-51 (they overlap
    those pieces' top halves exactly, pixel for pixel), with the red fenders and the flanks of
  - the big grey dome on top (newsh9-10 and newsh9-12, another batch's models).

Everything is built once in one frame ("fortress pixels": column 0 is newsh9-47's left edge,
row 0 its top edge, so rows -14..-1 are newsh9-28/-32's upper halves) and cut into the pieces
with common.split_assembly. The structure is mirror symmetric about the edge between columns
35 and 36 (Blender X = 0); Blender Y = 0 is the edge between rows 27 and 28.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
TAG = "nsh9fort"
ASSEMBLY = ["newsh9-47", "newsh9-49", "newsh9-51", "newsh9-85", "newsh9-87", "newsh9-89"]
SINGLES = ["newsh9-28", "newsh9-32"]
# Fortress pixel of each piece's top-left corner.
CORNER = {"newsh9-47": (0, 0), "newsh9-49": (24, 0), "newsh9-51": (48, 0),
          "newsh9-85": (0, 28), "newsh9-87": (24, 28), "newsh9-89": (48, 28),
          "newsh9-28": (0, -14), "newsh9-32": (48, -14)}
# Neighbours used only to trace the dome's outline (not built or exported here).
NEIGHBOURS = {"newsh9-10": (12, -28), "newsh9-12": (36, -28)}
PX = 1 / 12


def X(c):
    """Fortress pixel column (centre; fractions allowed) to Blender X."""
    return (c + 0.5 - 36) / 12


def Y(r):
    """Fortress pixel row (centre) to Blender Y: sprite up is +Y."""
    return (28 - (r + 0.5)) / 12


def layout():
    """(piece, cx, cy) for common.split_assembly: each piece's centre in pixels from the origin."""
    return [(n, c0 + 12 - 36, r0 + 14 - 28) for n, (c0, r0) in CORNER.items()]


# --- the sprites -------------------------------------------------------------------------------

def merged_sprite():
    """newsh9-47's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh9-47")
    for name in CORNER:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite(with_neighbours=False):
    """{(col, row): palette index} of every opaque pixel of the pieces, in fortress pixels."""
    pix = {}
    pieces = dict(CORNER)
    if with_neighbours:
        pieces.update(NEIGHBOURS)
    for name, (c0, r0) in pieces.items():
        frame = common.load_sprite(ROOT, name)["frames"][0]
        for r, line in enumerate(frame["pixels"]):
            for c, v in enumerate(line):
                if v >= 0:
                    pix[(c0 + c, r0 + r)] = v
    return pix


def composite_png(out, rows=(-14, 70)):
    """The fortress's sprites as one image (72 px wide, rows `rows`), for the whole preview."""
    import numpy as np
    pix = composite()
    colors = merged_sprite()["colors"]
    r0, r1 = rows
    img = np.zeros((r1 - r0, 72, 4), dtype=np.float32)
    for (c, r), v in pix.items():
        if r0 <= r < r1 and 0 <= c < 72:
            img[r - r0, c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("fortress_sprite", 72, r1 - r0, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


# --- outlines ----------------------------------------------------------------------------------

def _rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    ln = ab.length or 1e-9
    best, idx = -1, 0
    for i in range(1, len(pts) - 1):
        d = abs(ab.x * (pts[i] - a).y - ab.y * (pts[i] - a).x) / ln
        if d > best:
            best, idx = d, i
    if best <= eps:
        return [a, b]
    return _rdp(pts[:idx + 1], eps)[:-1] + _rdp(pts[idx:], eps)


def trace(inside, cols, rows, eps=0.45):
    """Outline (Blender XY, counter-clockwise) of the pixels where inside(col, row) is true,
    traced round the pixel corners, stair steps turned into slopes, and simplified.
    Only the largest connected region is traced."""
    edges = {}
    for r in range(rows[0], rows[1]):
        for c in range(cols[0], cols[1]):
            if not inside(c, r):
                continue
            if not inside(c, r - 1):
                edges[(c + 1, r)] = (c, r)
            if not inside(c, r + 1):
                edges[(c, r + 1)] = (c + 1, r + 1)
            if not inside(c - 1, r):
                edges[(c, r)] = (c, r + 1)
            if not inside(c + 1, r):
                edges[(c + 1, r + 1)] = (c + 1, r)
    loops, seen = [], set()
    for s in list(edges):
        if s in seen:
            continue
        loop, p = [], s
        while p not in seen and p in edges:
            seen.add(p)
            loop.append(p)
            p = edges[p]
        loops.append(loop)
    pts = [Vector(p) for p in max(loops, key=len)]
    # Drop collinear corners, then put a point at the middle of each run: the midpoints of a
    # staircase lie on the slope it stands for. Then simplify (closed: split at the farthest point).
    n = len(pts)
    pts = [pts[i] for i in range(n)
           if abs((pts[i] - pts[i - 1]).cross(pts[(i + 1) % n] - pts[i])) > 1e-9]
    pts = [(pts[i] + pts[(i + 1) % len(pts)]) / 2 for i in range(len(pts))]
    far = max(range(len(pts)), key=lambda i: (pts[i] - pts[0]).length)
    pts = _rdp(pts[:far + 1], eps)[:-1] + _rdp(pts[far:] + [pts[0]], eps)[:-1]
    poly = [((p.x - 36) / 12, (28 - p.y) / 12) for p in pts]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    if area < 0:
        poly.reverse()
    return poly


# --- geometry ----------------------------------------------------------------------------------

def _mark(bm, before, mat, smooth):
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = smooth


def pillow(bm, poly, z0, z1, steps=(), mat=0, smooth=False):
    """Extrude `poly` (Blender XY, CCW) from z0 to z1, then raise its top in steps of
    (inset px, rise units) so it rounds over like a cushion or shell."""
    before = set(bm.faces)
    top = [bm.verts.new((x, y, z1)) for x, y in poly]
    bot = [bm.verts.new((x, y, z0)) for x, y in poly]
    face = bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    for inset, rise in steps:
        bmesh.ops.inset_region(bm, faces=[face], thickness=inset * PX, depth=rise, use_even_offset=True)
    _mark(bm, before, mat, smooth)
    return face


def polydome(bm, poly, centre, z0, height, profile, mat=0, smooth=True):
    """A dome whose footprint is exactly `poly` (star-shaped about `centre`, Blender XY): rings
    of the outline scaled toward the centre. profile: (scale, height fraction) from the rim in."""
    before = set(bm.faces)
    cx, cy = centre
    rings = []
    for s, f in profile:
        z = z0 + height * f
        if s == 0:
            rings.append([bm.verts.new((cx, cy, z))])
        else:
            rings.append([bm.verts.new((cx + (x - cx) * s, cy + (y - cy) * s, z)) for x, y in poly])
    n = len(poly)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            if len(r1) == 1:
                bm.faces.new((r0[i], r0[j], r1[0]))
            else:
                bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(list(reversed(rings[0])))
    _mark(bm, before, mat, smooth)


def sweep(bm, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True):
    """A tube along a path of (col, row, z, half_width_px, half_height_units). Rings stand
    perpendicular to the path; a ring of zero size collapses to a point (a rounded end)."""
    pts = [Vector((X(c), Y(r), z)) for c, r, z, _, _ in path]
    rings = []
    up = Vector((0, 0, 1))
    before = set(bm.faces)
    for i, (c, r, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
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
    _mark(bm, before, mat, smooth)


def loft_y(bm, col, sections, sides=10, mat=0, smooth=True):
    """A loft down the sprite centred on column `col`: sections are (row, half_width_px,
    half_height_units, z)."""
    sweep(bm, [(col, r, z, w, h) for r, w, h, z in sections], sides=sides, mat=mat, smooth=smooth)


def plate(bm, outline, z0, z1, mat=0, smooth=False):
    """A flat plate from z0 to z1 with an outline of (col, row) pixel edges."""
    pts = [((c - 36) / 12, (28 - r) / 12) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    before = set(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2)
    _mark(bm, before, mat, smooth)


def ellipsoid(bm, col, row, z, rx_px, ry_px, rz, mat=0, segments=16, rings=8, lower=1.0):
    """An ellipsoid centred on pixel (col, row) at height z; `lower` squashes its underside."""
    before = set(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        k = rz if v.co.z >= 0 else rz * lower
        v.co = Vector((X(col) + v.co.x * rx_px * PX, Y(row) + v.co.y * ry_px * PX, z + v.co.z * k))
    _mark(bm, before, mat, True)


def mirror_all(bm):
    """Add the mirror image (about X = 0, the fortress's axis) of everything built so far."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


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


# --- the fortress ------------------------------------------------------------------------------

def build(name="fortress-newsh9"):
    """The whole fortress (rows -14..55 and the dome above) as one object, base at z = 0."""
    sprite = merged_sprite()
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, TAG, **kw)  # noqa: E731
    mats = [
        pal(3, metallic=0.4, roughness=0.6),  # 0 dark base and machinery bay
        pal(6, metallic=0.55, roughness=0.4),  # 1 grey shell
        pal(9, metallic=0.6, roughness=0.3),  # 2 light grey rims
        pal(7, metallic=0.55, roughness=0.35),  # 3 grey spine and dome
        pal(10, metallic=0.6, roughness=0.3),  # 4 bright knobs
        pal(71, metallic=0.3, roughness=0.4),  # 5 red fenders
        pal(70, metallic=0.35, roughness=0.3),  # 6 red pods
        pal(2, metallic=0.2, roughness=0.8),  # 7 black recesses
        pal(4, metallic=0.5, roughness=0.5),  # 8 dark grey machinery
        pal(8, metallic=0.6, roughness=0.3),  # 9 grey ball
        pal(69, metallic=0.3, roughness=0.4),  # 10 small red lenses
        pal(5, metallic=0.5, roughness=0.45),  # 11 grey neck and ribs
        pal(11, metallic=0.6, roughness=0.25),  # 12 bright grey highlights
    ]
    BASE, SHELL, RIM, SPINE, KNOB, FENDER, POD, RECESS, MACH, BALL, LENS, NECK, BRIGHT = range(13)
    pix = composite(with_neighbours=True)
    opaque = lambda c, r: (c, r) in pix  # noqa: E731
    bm = bmesh.new()

    # ---- whole-outline parts (not mirrored) ----

    # Base slab over the whole silhouette: the dark machinery bay between the dome and the shell
    # (rows 9-19) is this showing through.
    base = trace(opaque, (0, 72), (-28, 56))
    pillow(bm, base, 0.0, 0.08, mat=BASE)

    # The lower shell (rows 20-54): a cushion sloping down to its edges and its two tusks.
    shell = trace(lambda c, r: r >= 19 and opaque(c, r), (0, 72), (19, 56))
    polydome(bm, shell, (0.0, Y(33)), 0.06, 0.16,
             [(1.0, 0.0), (0.97, 0.4), (0.92, 0.7), (0.82, 0.9), (0.6, 1.0), (0.0, 1.0)], mat=SHELL, smooth=False)

    # The grey dome behind (its flanks are in newsh9-28/-32; the rest is newsh9-10/-12's).
    dome = trace(lambda c, r: r <= 1 and opaque(c, r), (0, 72), (-28, 2))
    polydome(bm, dome, (0.0, Y(-8)), 0.06, 0.62,
             [(1.0, 0.0), (0.96, 0.3), (0.88, 0.56), (0.75, 0.76), (0.56, 0.9), (0.3, 0.98), (0.0, 1.0)],
             mat=SPINE)

    # ---- left half (mirrored below) ----

    # Red fender under the dome: a big rounded lobe (highlight at column 15, rows 1-3) with a
    # horn reaching in to the neck (rows 2-8) and a tail curling down the outside to row 12.
    sweep(bm, [(3.6, 11.8, 0.16, 0.0, 0.0), (3.9, 11.0, 0.17, 1.8, 0.07), (5.0, 8.6, 0.22, 3.4, 0.11),
               (8.0, 5.6, 0.28, 4.4, 0.15), (12.5, 3.6, 0.33, 5.4, 0.19), (17.5, 3.6, 0.33, 5.0, 0.18),
               (22.0, 4.8, 0.31, 3.6, 0.15), (26.5, 5.2, 0.29, 3.2, 0.13), (29.0, 5.3, 0.27, 2.8, 0.11),
               (30.0, 5.3, 0.26, 0.0, 0.0)], sides=12, mat=FENDER)
    ellipsoid(bm, 15.0, 2.6, 0.33, 6.6, 6.6, 0.24, mat=FENDER, segments=18, rings=9, lower=1.0)

    # Machinery bay under the fender (rows 9-19): a dark block with ribs, two knobs and a lens.
    plate(bm, [(8, 9.5), (25, 9.5), (25, 14), (8, 14)], 0.06, 0.13, mat=MACH)
    for c0 in (11, 15, 19, 23):
        plate(bm, [(c0, 10), (c0 + 1.2, 10), (c0 + 1.2, 13.5), (c0, 13.5)], 0.13, 0.16, mat=NECK)
    ellipsoid(bm, 14.0, 11.2, 0.17, 1.6, 1.3, 0.05, mat=BRIGHT, segments=10, rings=5)
    ellipsoid(bm, 20.8, 12.4, 0.16, 1.2, 1.2, 0.05, mat=KNOB, segments=10, rings=5)
    plate(bm, [(7, 14), (18, 14), (18, 19), (8, 19)], 0.06, 0.1, mat=RECESS)
    ellipsoid(bm, 12.8, 16.3, 0.11, 4.6, 2.6, 0.08, mat=LENS, segments=14, rings=6)
    loft_y(bm, 21.5, [(15.0, 0.0, 0.0, 0.1), (15.4, 2.0, 0.06, 0.1), (17.0, 2.0, 0.06, 0.1),
                      (17.4, 0.0, 0.0, 0.1)], sides=8, mat=RIM)

    # Raised lip along the top of the shell (the light band at rows 22-25).
    sweep(bm, [(0.6, 25.6, 0.18, 0.0, 0.0), (1.2, 25.0, 0.19, 1.4, 0.06), (5.0, 23.6, 0.22, 2.0, 0.07),
               (11.0, 23.2, 0.25, 2.2, 0.07), (18.0, 23.6, 0.25, 2.0, 0.07), (25.0, 24.0, 0.24, 1.8, 0.06),
               (30.0, 23.4, 0.24, 1.6, 0.06), (32.0, 23.0, 0.24, 0.0, 0.0)], sides=8, mat=RIM)

    # Red pods in dark sockets on the shell: outer (column 14, rows 27-37) and inner (26, 33-44).
    for col, rw, rx, ry in ((14.2, 32.0, 4.6, 5.6), (26.0, 38.6, 4.6, 5.6)):
        ellipsoid(bm, col, rw - 0.3, 0.17, rx + 1.1, ry + 1.1, 0.06, mat=RECESS, segments=16, rings=6)
        ellipsoid(bm, col, rw, 0.2, rx, ry, 0.19, mat=POD, segments=16, rings=8, lower=0.5)

    mirror_all(bm)

    # ---- centre parts (symmetric about the axis) ----

    # Neck from the dome down to the ball (rows -2..9), a light ridge down it.
    loft_y(bm, 35.5, [(-3.0, 5.6, 0.2, 0.3), (8.0, 5.6, 0.2, 0.3), (9.5, 4.5, 0.16, 0.3)], sides=12, mat=NECK)
    loft_y(bm, 34.8, [(-1.0, 0.0, 0.0, 0.48), (0.0, 0.9, 0.04, 0.49), (7.0, 0.9, 0.04, 0.49),
                      (8.0, 0.0, 0.0, 0.48)], sides=6, mat=BRIGHT)
    # The grey ball (columns 26-45, rows 8-20).
    ellipsoid(bm, 35.5, 13.6, 0.3, 8.0, 7.0, 0.32, mat=BALL, segments=18, rings=9, lower=0.8)

    # Spine down the shell (columns 31-40, rows 21-49) with a knob at each end.
    loft_y(bm, 35.5, [(21.0, 0.0, 0.0, 0.2), (21.6, 3.5, 0.08, 0.2), (24.0, 4.6, 0.1, 0.21),
                      (43.0, 4.6, 0.1, 0.21), (46.5, 3.2, 0.08, 0.18), (49.6, 0.0, 0.0, 0.14)],
           sides=10, mat=SPINE)
    ellipsoid(bm, 34.5, 22.6, 0.3, 4.2, 2.0, 0.06, mat=KNOB, segments=12, rings=6)
    ellipsoid(bm, 35.5, 40.5, 0.3, 2.0, 2.2, 0.04, mat=RIM, segments=10, rings=5)

    return to_object(name, bm, mats, coll)


def export_pieces(names, preview=None):
    """Build the fortress, cut it into pieces and export `names`; with `preview` (a PNG path),
    render each piece beside its sprite into <preview dir>/<piece>.png."""
    obj = build()
    pieces = common.split_assembly(obj, [e for e in layout() if e[0] in names])
    for name in names:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if preview:
        preview = Path(preview)
        for name in names:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            out = preview if len(names) == 1 else preview.parent / f"{name}.png"
            common.render_preview([pieces[name]], str(out), img, size=2)
    return obj, pieces
