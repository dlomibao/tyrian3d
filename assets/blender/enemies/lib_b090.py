"""Helpers for batch b090: the twin armoured gauntlets of level 4.18 (newsh9.shp).

Eight 2x2 ground pieces make one 96 x 56 px structure: two grey armoured fists facing each
other across a gap, mirror images about the centre of assembly pixel column 48. The game lists
them as two assemblies (assembly-newsh9-115: the left fist, newsh9-77/79/115/117, and
assembly-newsh9-119: the right fist, newsh9-81/83/119/121), so `build()` makes the whole
structure once and each assembly script cuts out its own four pieces.

Assembly coordinates are pixel edges: u runs right from the structure's left edge (assembly
pixel column c spans u = c .. c + 1), v runs down from its top edge. Screen pixel (sx, sy) is
u = sx - 196, v = sy - 15. Blender X = (u - 48.5) / 12 (the mirror axis is X = 0) and
Y = (28 - v) / 12.
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
ALL_PIECES = ["newsh9-77", "newsh9-79", "newsh9-81", "newsh9-83",
              "newsh9-115", "newsh9-117", "newsh9-119", "newsh9-121"]
SX0, SY0 = 196, 15  # screen pixel of assembly edge (0, 0)
AXIS_U = 48.5  # mirror axis (centre of pixel column 48)
PX = 1 / 12


def X(u):
    return (u - AXIS_U) / 12


def Y(v):
    return (28 - v) / 12


# --- the sprite ------------------------------------------------------------------------------

def merged_sprite():
    """newsh9-115's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh9-115")
    for name in ALL_PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def layout():
    """(piece, cx, cy) for split_assembly, in units of pixels relative to the Blender origin."""
    data = common.load_sprite(ROOT, "newsh9-115")
    return [(e["model"], e["cx"] - SX0 - AXIS_U, e["cy"] - SY0 - 28) for e in data["assemblyLayout"]]


def grid():
    """The whole structure as a 56 x 96 grid of palette indices (-1 transparent)."""
    data = common.load_sprite(ROOT, "newsh9-115")
    g = [[-1] * 96 for _ in range(56)]
    for e in data["assemblyLayout"]:
        frame = common.load_sprite(ROOT, e["model"])["frames"][0]
        x0, y0 = e["cx"] - SX0 - 12, e["cy"] - SY0 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    g[y0 + r][x0 + c] = v
    return g


def spans(g, c_max=48, pad=0.3):
    """For each row, the (u_left, u_right) edges of the left half's filled pixels (outline
    pixels, index 1 and 254, only count where nothing else is), padded by `pad` px."""
    out = {}
    for r, row in enumerate(g):
        cols = [c for c in range(c_max) if row[c] >= 0 and row[c] not in (1, 254)]
        if cols:
            out[r] = (min(cols) - pad, max(cols) + 1 + pad)
    return out


# --- geometry --------------------------------------------------------------------------------

def _set(faces, mat, smooth):
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def hull(bm, sections, n=14, q_left=0.7, q_right=0.7, smooth=True):
    """Loft rounded-top profiles down the screen. Each section is (v, u_left, u_right, u_apex,
    z_base, z_top, mat): a half superellipse from u_left to u_right whose top is at u_apex,
    closed along z_base. `mat` colours the band from this section to the next. q < 1 is boxier."""
    rings = []
    for v, ul, ur, ua, zb, zt, _ in sections:
        ring = []
        for k in range(n + 1):
            a = math.pi * k / n
            c, s = math.cos(a), max(math.sin(a), 0.0)
            if c >= 0:
                u = ua + (ur - ua) * c ** q_right
                z = zb + (zt - zb) * s ** q_right
            else:
                u = ua - (ua - ul) * (-c) ** q_left
                z = zb + (zt - zb) * s ** q_left
            ring.append(bm.verts.new((X(u), Y(v), z)))
        rings.append(ring)
    m = n + 1
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        mat = sections[i][6]
        faces = []
        for k in range(m):
            j = (k + 1) % m
            faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
        _set(faces, mat, smooth)
    _set([bm.faces.new(list(reversed(rings[0])))], sections[0][6], False)
    _set([bm.faces.new(rings[-1])], sections[-1][6], False)


def sweep(bm, path, sides=10, mat=0, smooth=True):
    """A tube along a path of (u, v, z, half_width_px, half_height_units); rings stand across
    the path (in XY) and a ring of zero size closes to a point."""
    pts = [Vector((X(u), Y(v), z)) for u, v, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (u, v, z, w, h) in enumerate(path):
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
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1:
                faces.append(bm.faces.new((r0[0], r1[j], r1[k])))
            elif len(r1) == 1:
                faces.append(bm.faces.new((r0[k], r0[j], r1[0])))
            else:
                faces.append(bm.faces.new((r0[k], r0[j], r1[j], r1[k])))
    if len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    _set(faces, mat, smooth)


def plate(bm, outline, z0, z1, mat=0, bevel=0.0):
    """A plate from z0 to z1 over an outline of (u, v) points (any winding). With `bevel` (px)
    its top edge is chamfered inwards by that much over the top 40% of its height."""
    pts = [(X(u), Y(v)) for u, v in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    n = len(pts)
    if bevel <= 0:
        before = set(bm.faces)
        common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
        _set(set(bm.faces) - before, mat, False)
        return
    d = bevel * PX
    inner = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((-e0.y, e0.x)), Vector((-e1.y, e1.x))
        bis = (n0 + n1)
        bis = bis / max(bis.dot(n1), 0.3)
        inner.append(p1 + bis * d)
    zm = z1 - (z1 - z0) * 0.4
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    mid = [bm.verts.new((x, y, zm)) for x, y in pts]
    top = [bm.verts.new((p.x, p.y, z1)) for p in inner]
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bot[i], bot[j], mid[j], mid[i])))
        faces.append(bm.faces.new((mid[i], mid[j], top[j], top[i])))
    _set(faces, mat, False)


def ellipsoid(bm, u, v, z, rx_px, ry_px, rz, mat=0, segments=18, rings=9, z_cut=None):
    """An ellipsoid centred on pixel-edge point (u, v) at height z; vertices below z_cut are
    flattened onto it (so a dome sitting in a body doesn't poke out underneath)."""
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for vert in res["verts"]:
        co = Vector((X(u) + vert.co.x * rx_px * PX, Y(v) + vert.co.y * ry_px * PX, z + vert.co.z * rz))
        if z_cut is not None and co.z < z_cut:
            co.z = z_cut
        vert.co = co
    faces = {f for vert in res["verts"] for f in vert.link_faces}
    _set(faces, mat, True)


def mirror_all(bm):
    """Add the mirror image (about X = 0, the structure's axis) of everything built so far."""
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


# --- the structure ---------------------------------------------------------------------------

def build(name):
    """The whole structure (both fists) as one object, in assembly coordinates."""
    sprite = merged_sprite()
    coll = common.reset_collection(name)
    tag = "nsh9_115"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.3, roughness=0.4),  # 0 grey armour (the hood)
        pal(5, metallic=0.3, roughness=0.5),  # 1 dark grey body
        pal(3, metallic=0.4, roughness=0.6),  # 2 grooves and steps
        pal(9, metallic=0.7, roughness=0.3),  # 3 light ridge
        pal(69, metallic=0.15, roughness=0.3),  # 4 red domes
        pal(7, metallic=0.35, roughness=0.35),  # 5 light grey plates
        pal(14, emission_strength=2.5),  # 6 white lamp
        pal(6, metallic=0.3, roughness=0.45),  # 7 mid grey plates
        pal(8, metallic=0.35, roughness=0.35),  # 8 lit block
        pal(2, metallic=0.2, roughness=0.7),  # 9 dark channels
    ]
    HOOD, BODY, GROOVE, RIDGE, DOME, LIGHT, LAMP, MID, LIT, CHANNEL = range(10)
    g = grid()
    sp = spans(g)
    bm = bmesh.new()

    # ---- left fist (mirrored below) ----

    # The hood: the big rounded armour over the back of the fist (rows 5-26). A low shelf fills
    # the whole outline, its outer flank sloping down to the diagonal left edge; on it sits the
    # upper lobe, whose lower-left edge is the dark curve from column 22, row 11 round to row 19.
    HZ, SZ = 0.62, 0.44
    shelf = [(5.2, 32.4, 44.3, 40.0, 0.0, 0.2, HOOD)]
    for r in range(6, 25):
        ul, ur = sp[r]
        shelf.append((r + 0.5, ul, min(ur, 45.3), 40.0, 0.0, SZ if r > 7 else 0.3 + (r - 6) * 0.07, HOOD))
    shelf.append((25.5, 21.0, 44.3, 40.0, 0.0, SZ - 0.06, HOOD))
    shelf.append((26.6, 30.0, 41.0, 38.0, 0.0, 0.26, HOOD))
    hull(bm, shelf, n=16, q_left=0.85, q_right=0.35)
    lobe_left = {5: 32.6, 6: 29.6, 7: 27.6, 8: 25.6, 9: 24.6, 10: 23.8, 11: 23.2, 12: 23.0, 13: 23.6,
                 14: 24.4, 15: 25.2, 16: 26.0, 17: 26.6, 18: 27.2}
    lobe = []
    for r, ul in lobe_left.items():
        v = r + 0.5 if r > 5 else 5.3
        zt = HZ if 8 <= r else (0.3 if r == 5 else 0.3 + (r - 5) * 0.11)
        lobe.append((v, ul, 45.1 if r > 6 else 44.2, 39.5, SZ - 0.15, zt, GROOVE if r == 18 else HOOD))
    lobe.append((20.0, 28.5, 44.8, 39.5, SZ - 0.15, SZ + 0.01, HOOD))
    hull(bm, lobe, n=16, q_left=0.6, q_right=0.35)

    # The light ridge down the hood (column 41, rows 8-25).
    sweep(bm, [(41.6, 6.8, HZ - 0.06, 0.0, 0.0), (41.6, 8.0, HZ - 0.02, 1.4, 0.05),
               (41.6, 18.5, HZ - 0.0, 1.6, 0.05), (41.6, 21.0, HZ - 0.06, 1.6, 0.05),
               (41.6, 24.5, SZ + 0.02, 1.6, 0.05), (41.6, 26.0, SZ - 0.08, 0.0, 0.0)], sides=8, mat=RIDGE)
    # The lit block above the step, beside the ridge (rows 13-18, columns 34-41).
    plate(bm, [(34.5, 13.5), (40.5, 13.5), (40.5, 18.7), (34.5, 18.7)], HZ - 0.1, HZ + 0.035, mat=LIT,
          bevel=0.6)
    # The groove down the side of the step (column 39, rows 17-23).
    plate(bm, [(38.8, 19.5), (39.8, 19.5), (39.8, 23.5), (38.8, 23.5)], SZ - 0.1, SZ + 0.02, mat=GROOVE)

    # The body under the knuckles (rows 24-53), dark grey with a rounded top.
    BZ = 0.3
    body = []
    for r in range(24, 53):
        ul, ur = sp[r] if r != 24 else (sp[25][0] + 0.6, sp[25][1])
        v = r + 0.5 if r != 24 else 24.2
        zt = BZ if r < 48 else BZ - (r - 47) * 0.035
        body.append((v, ul, ur, (ul + ur) / 2, 0.0, zt, BODY))
    body.append((53.4, 11.5, 17.5, 14.5, 0.0, 0.1, BODY))
    hull(bm, body, n=14, q_left=0.4, q_right=0.4)

    # Red knuckle domes.
    ellipsoid(bm, 36.8, 33.0, 0.24, 6.8, 5.4, 0.2, mat=DOME, z_cut=0.05)  # big (columns 30-42)
    ellipsoid(bm, 28.8, 44.0, 0.2, 4.9, 5.3, 0.17, mat=DOME, z_cut=0.05)  # small (columns 24-32)
    ellipsoid(bm, 22.2, 29.5, 0.24, 4.2, 3.9, 0.16, mat=DOME, z_cut=0.05)  # upper (columns 18-25)
    ellipsoid(bm, 9.6, 30.0, 0.22, 4.7, 5.1, 0.16, mat=DOME, z_cut=0.05)  # outer (columns 5-13)

    # Light grey bridge between the knuckles (columns 18-30, rows 24-41).
    plate(bm, [(25.0, 24.2), (30.5, 24.2), (30.5, 30.0), (29.5, 38.0), (24.0, 40.5), (18.5, 41.0),
               (18.5, 37.0), (24.5, 33.5)], BZ - 0.1, BZ + 0.05, mat=LIGHT, bevel=0.8)
    # Plate on the lower body (columns 16-24, rows 40-49).
    plate(bm, [(16.5, 41.5), (23.5, 41.0), (24.0, 49.5), (18.0, 50.0), (16.0, 47.5)], BZ - 0.1, BZ + 0.03,
          mat=MID, bevel=0.8)
    # Upright pipe beside the outer knuckle (column 16, rows 27-37).
    sweep(bm, [(16.5, 26.5, BZ + 0.02, 0.0, 0.0), (16.5, 27.5, BZ + 0.02, 1.2, 0.05),
               (16.5, 37.0, BZ + 0.02, 1.2, 0.05), (16.5, 38.0, BZ + 0.02, 0.0, 0.0)], sides=8, mat=LIGHT)
    # Light bar from the small knuckle up to the bridge (columns 19-24, rows 34-40).
    sweep(bm, [(25.0, 34.0, BZ + 0.02, 0.0, 0.0), (24.6, 34.6, BZ + 0.02, 1.6, 0.06),
               (19.8, 40.2, BZ + 0.02, 1.6, 0.06), (19.2, 40.9, BZ + 0.02, 0.0, 0.0)], sides=8, mat=RIDGE)
    # Rod down the outer flank (column 12, row 33 to column 16, row 42) beside a dark channel.
    sweep(bm, [(11.8, 32.6, BZ + 0.0, 0.0, 0.0), (12.2, 33.4, BZ + 0.0, 1.0, 0.045),
               (16.2, 41.6, BZ + 0.0, 1.0, 0.045), (16.6, 42.4, BZ + 0.0, 0.0, 0.0)], sides=8, mat=LIGHT)
    plate(bm, [(14.6, 34.0), (16.6, 34.0), (19.0, 39.5), (18.5, 44.5), (16.8, 44.5)], BZ - 0.06, BZ + 0.012,
          mat=CHANNEL)
    # The white lamp in the lower corner (columns 11-14, rows 45-48) in a grey ring.
    ellipsoid(bm, 13.0, 47.0, BZ - 0.02, 2.4, 2.2, 0.06, mat=MID, segments=12, rings=6)
    ellipsoid(bm, 13.0, 47.0, BZ + 0.02, 1.3, 1.2, 0.05, mat=LAMP, segments=10, rings=5)

    mirror_all(bm)
    return to_object(name, bm, mats, coll), sprite


def composite_png(out):
    """The whole structure's sprite as one image, padded to the 24:28 shape that render_preview
    expects for size 8 (96 x 112 px, the structure in the middle)."""
    import numpy as np
    data = merged_sprite()
    g = grid()
    img = np.zeros((112, 96, 4), dtype=np.float32)
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v >= 0:
                img[r + 28, c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 96, 112, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def export(name, pieces):
    """Build the structure, cut it into pieces and export `pieces`; with --preview also render
    the whole structure and each exported piece."""
    obj, _ = build(name)
    lay = [e for e in layout() if e[0] in pieces]
    cut = common.split_assembly(obj, lay)
    for piece in pieces:
        data = common.load_sprite(ROOT, piece)
        common.export_sprite_model(ROOT, [cut[piece]], f"enemies/{piece}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=8, view_px=640)
        for piece in pieces:
            data = common.load_sprite(ROOT, piece)
            img = ROOT / "reference" / "models" / piece / data["frames"][0]["image"]
            common.render_preview([cut[piece]], str(out.parent / f"{piece}.png"), img, size=2)
