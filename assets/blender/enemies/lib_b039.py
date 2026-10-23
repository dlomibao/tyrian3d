"""Helpers shared by batch b039's model scripts (tyrian.shp #10: the spinning disc, the cyan
pyramid, the strapped crate and the green crystal).

Not a model itself: tools/build-models.sh skips lib_ modules. Scripts import it with
`import lib_b039 as lib` after putting assets/blender and assets/blender/enemies on sys.path.
Coordinates: sprite column c / row r; px/row give a pixel's centre, ex/ey a pixel edge, for a
24x28 block by default (w=12, h=14 for size-1 sprites).
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
    """Join rings of 3D points (all the same length, or a single point for a tip) in order
    (copied from lib_b007). `mats` gives a material index per band between consecutive rings (an
    int for all, a list per band, or a list of lists per band and segment)."""
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


def lathe(bm, profile, sides=24, mats=0, centre=(0.0, 0.0)):
    """A solid of revolution about the vertical through `centre`: `profile` is a list of
    (radius, z) from top to bottom (radius 0 closes to a point). `mats` per band as ring_loft."""
    cx, cy = centre
    rings = []
    for r, z in profile:
        if r == 0:
            rings.append([(cx, cy, z)])
        else:
            rings.append([(cx + r * math.cos(2 * math.pi * (i + 0.5) / sides),
                           cy + r * math.sin(2 * math.pi * (i + 0.5) / sides), z) for i in range(sides)])
    return ring_loft(bm, rings, mats)


def transform(bm, start, fn):
    """Replace every vertex added since `start` by fn((x, y, z)) -> (x, y, z)."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co = fn(tuple(v.co))


def rotate_y(angle, cx=0.0, cz=0.0):
    """A point function turning about the line parallel to Y through (cx, ., cz); positive turns
    +Z toward +X."""
    c, s = math.cos(angle), math.sin(angle)

    def fn(p):
        x, y, z = p[0] - cx, p[1], p[2] - cz
        return (cx + x * c + z * s, y, cz - x * s + z * c)
    return fn


def rotate_z(angle, cx=0.0, cy=0.0):
    """A point function turning about the vertical through (cx, cy), counter-clockwise from above."""
    c, s = math.cos(angle), math.sin(angle)

    def fn(p):
        x, y = p[0] - cx, p[1] - cy
        return (cx + x * c - y * s, cy + x * s + y * c, p[2])
    return fn


def export_frames(root, name, models, sheet_prefix):
    """Export (model_name, objects, frame_indices) models, each claiming only its frames of the
    sprite's one sheet, and with `-- --preview <png>` render each beside its first frame
    (<png> for the first model, <model_name>.png next to it for the others)."""
    sprite = common.load_sprite(root, name)
    base = sprite["sprites"][0]
    size = base["size"]
    for i, (model, objects, frames) in enumerate(models):
        common.export_sprite_model(root, objects, f"enemies/{model}", [{**base, "frames": list(frames)}])
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            if i:
                out = out.with_name(f"{model}.png")
            ref = Path(root) / "reference" / "models" / name / f"frame-{sheet_prefix}-{frames[0]}.png"
            common.render_preview(objects, out, ref, size=size)


def preview(objects, root, name, sprite):
    """Render the usual preview beside the first frame if run with `-- --preview <png>`."""
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = Path(root) / "reference" / "models" / name / sprite["frames"][0]["image"]
        common.render_preview(objects, out, ref, size=sprite["frames"][0]["size"])


def sample(pixels, x, y):
    """The palette index of the sprite pixel under Blender (x, y), or -1 outside / transparent
    (the block size comes from `pixels`)."""
    h, w = len(pixels), len(pixels[0])
    c, r = int(math.floor(x * 12 + w / 2)), int(math.floor(h / 2 - y * 12))
    if 0 <= r < h and 0 <= c < w:
        return pixels[r][c]
    return -1


def paint_from_sprite(bm, pixels, slot_of, faces=None, under_slot=None, min_nz=0.0):
    """Give each face (all, or `faces`) the material slot of the sprite pixel under its centre
    (after lib_b004): slot_of(index) -> slot, or None to leave the face. Faces facing down
    (normal z < min_nz) get `under_slot` if given."""
    import bmesh
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    for f in faces if faces is not None else bm.faces:
        if f.normal.z < min_nz:
            if under_slot is not None:
                f.material_index = under_slot
            continue
        cen = f.calc_center_median()
        slot = slot_of(sample(pixels, cen.x, cen.y))
        if slot is not None:
            f.material_index = slot


def strip(bm, points, width, height, surface, lift=0.0, mat_index=0):
    """A flat band (a strap, a seam) along a polyline of Blender (x, y) points, lying on
    `surface(x, y) -> z`: `width` across, `height` thick, its underside `lift` above the surface
    (negative sinks it in so it hugs a curved surface)."""
    rings = []
    n = len(points)
    for i, (x, y) in enumerate(points):
        a = points[max(i - 1, 0)]
        b = points[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln * width / 2, dx / ln * width / 2
        ring = []
        for sx, sz in ((1, 0), (1, 1), (-1, 1), (-1, 0)):
            px_, py_ = x + nx * sx, y + ny * sx
            z = surface(px_, py_) + lift + height * sz
            ring.append((px_, py_, z))
        rings.append(ring)
    return ring_loft(bm, rings, mat_index)
