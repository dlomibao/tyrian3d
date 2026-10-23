"""Helpers shared by batch b081's enemy models (newshv.shp ground pieces: the twin cannons of
level 4.18, the drill of levels 2.12/2.19, the red-lamp turret and the green gem).

Not a model itself: tools/build-models.sh skips lib_ modules. Scripts import it with
`import lib_b081 as lib` after putting assets/blender and assets/blender/enemies on sys.path.
Several helpers are copied from lib_b003 (not imported, so batches stay independent).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units


def ex(e, w=24):
    """Sprite column edge (0 = left edge of column 0) to Blender X."""
    return (e - w / 2) / 12


def ey(e, h=28):
    """Sprite row edge (0 = top edge of row 0) to Blender Y."""
    return (h / 2 - e) / 12


def move(bm, start, dx=0.0, dy=0.0, dz=0.0):
    """Move every vertex added since index `start`."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x += dx
        v.co.y += dy
        v.co.z += dz


def scale(bm, start, sx=1.0, sy=1.0, sz=1.0, cx=0.0, cy=0.0, cz=0.0):
    """Scale every vertex added since `start` about (cx, cy, cz)."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x = cx + (v.co.x - cx) * sx
        v.co.y = cy + (v.co.y - cy) * sy
        v.co.z = cz + (v.co.z - cz) * sz


def loft_x(bm, sections, sides=8, mat_index=0, cap_start=True, cap_end=True):
    """common.loft along +X instead of +Y: sections are (x, half_depth_y, half_height, z)."""
    start = len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat_index, cap_start=cap_start, cap_end=cap_end)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.x, v.co.y = v.co.y, v.co.x


def ellipsoid(bm, centre, radii, sides=16, rings=8, mat_index=0):
    """An ellipsoid (radii rx, ry, rz) at `centre`, lofted along Y."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    sections = [(-ry, 0.0, 0.0, 0.0)]
    for i in range(1, rings):
        a = math.pi * i / rings
        sections.append((ry * -math.cos(a), rx * math.sin(a), rz * math.sin(a), 0.0))
    sections.append((ry, 0.0, 0.0, 0.0))
    start = len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat_index)
    move(bm, start, cx, cy, cz)


def dome(bm, centre, radii, sides=16, rings=4, mat_index=0):
    """The upper half of an ellipsoid standing on z = centre z (closed underneath)."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    verts = []
    for i in range(rings):
        a = math.pi / 2 * i / rings
        r, z = math.cos(a), math.sin(a)
        verts.append([bm.verts.new((cx + rx * r * math.cos(2 * math.pi * k / sides),
                                    cy + ry * r * math.sin(2 * math.pi * k / sides), cz + rz * z))
                      for k in range(sides)])
    top = bm.verts.new((cx, cy, cz + rz))
    bm.faces.new(list(reversed(verts[0]))).material_index = mat_index
    for r0, r1 in zip(verts, verts[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((r0[k], r0[j], r1[j], r1[k])).material_index = mat_index
    for k in range(sides):
        bm.faces.new((verts[-1][k], verts[-1][(k + 1) % sides], top)).material_index = mat_index


def prism(bm, outline, z0, z1, mat_index=0):
    """Extrude an XY outline from z0 up to z1."""
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0):
    """An axis-aligned box."""
    prism(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat_index)


def mirror_x(bm, start, axis=0.0):
    """Duplicate the geometry whose vertices were all added since index `start`, mirrored about the
    vertical plane x = axis, keeping each face's material and smooth flag."""
    bm.verts.ensure_lookup_table()
    src = set(bm.verts[start:])
    copies = {v: bm.verts.new((2 * axis - v.co.x, v.co.y, v.co.z)) for v in list(src)}
    for f in [f for f in bm.faces if all(v in src for v in f.verts)]:
        nf = bm.faces.new([copies[v] for v in reversed(f.verts)])
        nf.material_index = f.material_index
        nf.smooth = f.smooth


def set_smooth(bm, face_start, smooth=True):
    """Mark the faces added since index `face_start` smooth (or flat)."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[face_start:]:
        f.smooth = smooth


def mesh_object_mixed(name, bm, materials, collection):
    """Like common.mesh_object, but keeps each face's own smooth flag (see set_smooth)."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in materials:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def merged_colors(root, names):
    """A sprite-like dict whose `colors` merge the palettes of several sprite.json files."""
    merged = {"name": "+".join(names), "colors": {}}
    for n in names:
        merged["colors"].update(common.load_sprite(root, n)["colors"])
    return merged


def inset_outline(outline, d):
    """Move each vertex of a closed XY outline inward by `d` along its corner's bisector."""
    n = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1]
               for i in range(n))
    sign = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = outline[i - 1], outline[i], outline[(i + 1) % n]
        normals = []
        for a, b in ((p0, p1), (p1, p2)):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy) or 1.0
            normals.append((-dy / length * sign, dx / length * sign))
        nx, ny = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
        length = math.hypot(nx, ny) or 1.0
        nx, ny = nx / length, ny / length
        cos_half = max(0.35, nx * normals[0][0] + ny * normals[0][1])
        out.append((p1[0] + nx * d / cos_half, p1[1] + ny * d / cos_half))
    return out


def bevel_prism(bm, outline, z0, z1, bevel, bevel_h=None, mat_index=0, top_mat=None):
    """A prism from z0 to z1 whose top edges are chamfered: the walls rise to z1 - bevel_h and a
    sloped band leads in by `bevel` to the flat top. `top_mat` (default mat_index) colours the top."""
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


def frames_subset(sprite, keep):
    """sprite["sprites"] with only the frames in `keep`."""
    return [dict(s, frames=[f for f in s["frames"] if f in keep]) for s in sprite["sprites"]]


def composite_png(root, placements, size, out):
    """Paint several pieces' sprites into one image for an assembly preview: `placements` are
    (model_name, frame_index, cx, cy) with (cx, cy) the piece centre in pixels relative to the
    image centre. The image is size*12 x size*14 px, like a sprite of `size` tiles."""
    import numpy as np
    w, h = size * 12, size * 14
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, fi, cx, cy in placements:
        data = common.load_sprite(root, name)
        frame = data["frames"][fi]
        pw, ph = len(frame["pixels"][0]), len(frame["pixels"])
        x0, y0 = int(cx + w / 2 - pw / 2), int(cy + h / 2 - ph / 2)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < h and 0 <= x0 + c < w:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def preview_arg():
    """The --preview path, or None."""
    if "--preview" in sys.argv:
        return Path(sys.argv[sys.argv.index("--preview") + 1])
    return None


def preview(objects, root, name, sprite, frame=0):
    """Render the preview if the script was run with `-- --preview <png>`."""
    out = preview_arg()
    if out:
        ref = Path(root) / "reference" / "models" / name / sprite["frames"][frame]["image"]
        common.render_preview(objects, str(out), ref, size=sprite["frames"][frame]["size"])


# --- The small gem with a stalk (copied from lib_b003; newshv-38 is the green one) ---------------

def rings_solid(bm, centre, rings, sides=4, angle=0.0, mat_bottom=0):
    """Concentric rings joined into a stepped, pyramid-like solid. `rings` go from the outside in:
    (radius, z, mat_index); a ring of radius 0 is an apex."""
    cx, cy = centre
    verts = []
    for r, z, _ in rings:
        if r == 0:
            verts.append([bm.verts.new((cx, cy, z))])
            continue
        verts.append([bm.verts.new((cx + r * math.cos(angle + 2 * math.pi * i / sides),
                                    cy + r * math.sin(angle + 2 * math.pi * i / sides), z))
                      for i in range(sides)])
    if len(verts[0]) > 1:
        bm.faces.new(list(reversed(verts[0]))).material_index = mat_bottom
    for k in range(len(verts) - 1):
        r0, r1 = verts[k], verts[k + 1]
        m = rings[k + 1][2]
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(f).material_index = m
    if len(verts[-1]) > 1:
        bm.faces.new(verts[-1]).material_index = rings[-1][2]


# --- The twin cannons of level 4.18 (newshv 14 + 16, mirrored as 167 + 169) ---------------------
#
# Four 2x2 pieces in a row make two long grey cannons pointing away from each other, joined in the
# middle by their couplings: 14 | 16 | 167 | 169 (169 and 167 are 14 and 16 mirrored). Each cannon
# is a barrel with an end cap, a bright ring and a blue band near its muzzle, lying on a wedge
# mount with an upper and a lower fin; behind it a back plate, a blue-grey half disc (a turntable)
# and the coupling: a shaft, a bright ball joint, a ring and a dark socket facing the other side.
# The pair is built in "pair" coordinates: column edges u = 0..96 across the four pieces (u = 48 is
# the seam between 16 and 167, the Blender origin) and row edges r = 0..28.

PAIR_PIECES = ["newshv-14", "newshv-16", "newshv-167", "newshv-169"]
PAIR_LAYOUT = {"newshv-14": (-36, 0), "newshv-16": (-12, 0), "newshv-167": (12, 0), "newshv-169": (36, 0)}


def PX(u):
    return (u - 48) / 12


def PY(r):
    return (14 - r) / 12


def ppoly(points):
    return [(PX(u), PY(r)) for u, r in points]


def build_cannon_pair(root, name):
    """The whole twin-cannon structure as one object (origin at the seam, base at z = 0)."""
    coll = common.reset_collection(name)
    colors = merged_colors(root, PAIR_PIECES)
    pal = lambda i, **kw: common.palette_material(colors, i, name, **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.7, roughness=0.3),  # 0 barrel
        pal(7, metallic=0.6, roughness=0.45),  # 1 end cap, neck
        pal(12, metallic=0.75, roughness=0.2),  # 2 bright rings, ball joint
        pal(56, metallic=0.6, roughness=0.25),  # 3 blue band
        pal(4, metallic=0.5, roughness=0.55),  # 4 mount top, dark plates
        pal(7, metallic=0.5, roughness=0.45),  # 5 mount edges (lit bevels)
        pal(5, metallic=0.55, roughness=0.45),  # 6 back plate, dark socket
        pal(103, metallic=0.35, roughness=0.45),  # 7 blue-grey half disc
        pal(100, metallic=0.3, roughness=0.6),  # 8 its dark rim
        pal(58, metallic=0.5, roughness=0.3),  # 9 its lit straight edge
        pal(9, metallic=0.65, roughness=0.35),  # 10 shaft
        pal(3, metallic=0.4, roughness=0.6),  # 11 shadowed bracket
        pal(141, metallic=0.4, roughness=0.15, emission_strength=1.5),  # 12 band highlight
        pal(6, metallic=0.55, roughness=0.4),  # 13 dark socket
    ]
    (BARREL, CAP, BRIGHT, BAND, MOUNT, EDGE, PLATE, DISC, DISC_RIM, DISC_EDGE, SHAFT, SHADOW,
     GLINT, SOCKET) = range(14)
    K = 0.68  # barrels are a little flattened: z radius = K * y radius
    bm = bmesh.new()
    start = len(bm.verts)

    # Wedge mount under the back of the barrel (14 columns 13-23 and 16 columns 0-4): an upper
    # fin rising to the top right, a long lower fin falling to the bottom right.
    f0 = len(bm.faces)
    bevel_prism(bm, ppoly([(13, 15), (13.5, 17.2), (15.5, 18.2), (22.4, 25.2), (24, 26), (29, 26),
                           (29, 1), (23, 1), (21, 1.8), (18.8, 3), (16.6, 4.3)]),
                0.0, 0.22, 1.6 * U, 0.08, mat_index=EDGE, top_mat=MOUNT)
    # Back plate the barrel ends against (16 columns 0-4, rows 1-25), a step above the mount.
    bevel_prism(bm, ppoly([(24.3, 1.4), (28.8, 1.4), (28.8, 25.6), (24.3, 25.6)]), 0.1, 0.3,
                0.8 * U, 0.05, mat_index=EDGE, top_mat=PLATE)
    # Bracket under the front of the barrel (14 columns 4-12, rows 15-17).
    bevel_prism(bm, ppoly([(4, 13), (12.6, 13), (12.6, 18), (4, 18)]), 0.0, 0.2, 0.8 * U, 0.06,
                mat_index=EDGE, top_mat=SHADOW)

    # Blue-grey half disc behind the plate (16 columns 5-17, rows 1-25), flat edge at u = 29.
    disc = [(29, 26), (37, 26), (39, 25.0), (40, 24), (41, 22.6), (42, 21), (42.1, 18), (42.3, 15),
            (42.4, 11), (42.1, 8), (41.4, 5.2), (40, 3), (39, 2), (37, 1), (29, 1)]
    bevel_prism(bm, ppoly(disc), 0.0, 0.12, 1.0 * U, 0.04, mat_index=DISC_RIM, top_mat=DISC)
    prism(bm, ppoly([(29, 1.2), (30, 1.2), (30, 25.8), (29, 25.8)]), 0.0, 0.135, DISC_EDGE)
    set_smooth(bm, f0, False)

    # Barrel along X: axis at row edge 10, 5 px radius; centre height so it rests on the mount.
    f0 = len(bm.faces)
    by, bz = PY(10), 0.33
    r5 = 5 * U
    s = len(bm.verts)
    loft_x(bm, [(PX(0.8), 3.4 * U, 3.4 * U * K, 0.0), (PX(1.2), 4.6 * U, 4.6 * U * K, 0.0),
                (PX(2.0), 4.7 * U, 4.7 * U * K, 0.0)], sides=16, mat_index=BRIGHT, cap_end=False)
    loft_x(bm, [(PX(2.0), 4.6 * U, 4.6 * U * K, 0.0), (PX(5.0), 4.6 * U, 4.6 * U * K, 0.0)],
           sides=16, mat_index=CAP, cap_start=False, cap_end=False)
    loft_x(bm, [(PX(5.0), 5.4 * U, 5.4 * U * K, 0.0), (PX(6.0), 5.4 * U, 5.4 * U * K, 0.0)],
           sides=16, mat_index=BRIGHT)
    loft_x(bm, [(PX(6.0), r5, r5 * K, 0.0), (PX(10.0), r5, r5 * K, 0.0)], sides=16,
           mat_index=BARREL, cap_start=False, cap_end=False)
    loft_x(bm, [(PX(10.0), 5.3 * U, 5.3 * U * K, 0.0), (PX(12.0), 5.3 * U, 5.3 * U * K, 0.0)],
           sides=16, mat_index=BAND)
    loft_x(bm, [(PX(12.0), r5, r5 * K, 0.0), (PX(24.6), r5, r5 * K, 0.0)], sides=16,
           mat_index=BARREL, cap_start=False)
    move(bm, s, dy=by, dz=bz)
    # The band's glint on top (the very bright pixels in row 8).
    box(bm, PX(10.1), PY(8.7), PX(11.9), PY(7.6), bz + r5 * K - 0.03, bz + r5 * K + 0.035, GLINT)
    # Bright ring and band carry on round the bracket below the barrel.
    box(bm, PX(5.0), PY(18), PX(6.0), PY(13), 0.0, 0.24, BRIGHT)
    box(bm, PX(10.0), PY(18), PX(12.0), PY(13), 0.0, 0.24, BAND)

    # Coupling along X (axis at row edge 11): shaft, groove, ball joint, ring, dark socket.
    cy, K2 = PY(11), K
    s = len(bm.verts)
    loft_x(bm, [(PX(26.6), 4.2 * U, 4.2 * U * K2, 0.0), (PX(27.2), 4.6 * U, 4.6 * U * K2, 0.0),
                (PX(30.8), 4.6 * U, 4.6 * U * K2, 0.0), (PX(31.3), 3.6 * U, 3.6 * U * K2, 0.0)],
           sides=14, mat_index=BARREL)
    loft_x(bm, [(PX(31.0), 3.2 * U, 3.2 * U * K2, 0.0), (PX(35.5), 3.2 * U, 3.2 * U * K2, 0.0)],
           sides=12, mat_index=SHAFT)
    move(bm, s, dy=cy, dz=bz)
    ellipsoid(bm, (PX(36.6), PY(10.2), bz), (2.4 * U, 4.9 * U, 4.9 * U * K2), sides=14, rings=8,
              mat_index=BRIGHT)
    s = len(bm.verts)
    loft_x(bm, [(PX(37.6), 4.0 * U, 4.0 * U * K2, 0.0), (PX(39.0), 4.0 * U, 4.0 * U * K2, 0.0)],
           sides=14, mat_index=CAP)
    loft_x(bm, [(PX(38.9), 5.4 * U, 5.4 * U * K2, 0.0), (PX(40.1), 5.4 * U, 5.4 * U * K2, 0.0)],
           sides=14, mat_index=BRIGHT)
    loft_x(bm, [(PX(40.0), 5.6 * U, 5.6 * U * K2, 0.0), (PX(45.0), 5.6 * U, 5.6 * U * K2, 0.0),
                (PX(46.2), 4.6 * U, 4.6 * U * K2, 0.0), (PX(46.7), 2.5 * U, 2.5 * U * K2, 0.0)],
           sides=14, mat_index=SOCKET)
    move(bm, s, dy=cy, dz=bz)
    set_smooth(bm, f0, True)

    mirror_x(bm, start, axis=0.0)
    return mesh_object_mixed(name, bm, mats, coll)


def export_cannon_pair(root, name, pieces):
    """Build the pair, cut it, export `pieces` (each with its own sprites) and render previews."""
    whole = build_cannon_pair(root, name)
    cut = common.split_assembly(whole, [(p, *PAIR_LAYOUT[p]) for p in pieces])
    for p in pieces:
        common.export_sprite_model(root, [cut[p]], f"enemies/{p}", common.load_sprite(root, p)["sprites"])
    out = preview_arg()
    if out:
        import tempfile
        ref = composite_png(root, [(p, 0, *PAIR_LAYOUT[p]) for p in PAIR_PIECES], 8,
                            Path(tempfile.mkdtemp()) / "pair.png")
        common.render_preview([whole], str(out), ref, size=8, view_px=480)
        for p in pieces:
            data = common.load_sprite(root, p)
            common.render_preview([cut[p]], str(out.with_name(f"{out.stem}-{p}.png")),
                                  Path(root) / "reference" / "models" / p / data["frames"][0]["image"], size=2)
