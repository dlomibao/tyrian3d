"""Helpers shared by batch b063's models (the green orbs, the grey dome and the green spike of
level 2.4): sprite coordinates for any pixel grid, ellipsoids, lofts whose sections follow the
sprite's rows, and per-face colours sampled from the sprite.

Coordinates work on a whole pixel grid (a 24x28 sprite, or several pieces of an assembly pasted
into one grid): the grid's centre is the origin, one pixel is 1/12 unit, sprite up is +Y.

build-models.sh skips lib_ files; the model scripts import this next to them.
"""

import math
import sys
from collections import Counter
from pathlib import Path

import bmesh
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def px(c, w=24):
    """Grid column (pixel centre, or any fractional column) to Blender X."""
    return (c + 0.5 - w / 2) / 12


def row(r, h=28):
    """Grid row (pixel centre) to Blender Y: sprite up is +Y."""
    return (h / 2 - (r + 0.5)) / 12


def sample(pixels, x, y):
    """The palette index of the grid pixel under Blender (x, y), or -1 outside / transparent."""
    h, w = len(pixels), len(pixels[0])
    c = math.floor(x * 12 + w / 2)
    r = math.floor(h / 2 - y * 12)
    if 0 <= r < h and 0 <= c < w:
        return pixels[r][c]
    return -1


def extents(pixels, keep=lambda i: i >= 0):
    """{row: (first column, last column)} of the pixels for which keep(index) is true."""
    out = {}
    for r, line in enumerate(pixels):
        cols = [c for c, v in enumerate(line) if keep(v)]
        if cols:
            out[r] = (cols[0], cols[-1])
    return out


def ellipsoid(bm, cx, cy, a, b, c, z0=0.0, segments=24, rings=14, mat_index=0):
    """An ellipsoid centred on (cx, cy, z0) with semi-axes a (x), b (y), c (z), lofted along Y."""
    sections = [(-b, 0.0, 0.0, 0.0)]
    for i in range(1, rings):
        t = math.pi * (rings - i) / rings
        sections.append((b * math.cos(t), a * math.sin(t), c * math.sin(t), 0.0))
    sections.append((b, 0.0, 0.0, 0.0))
    start = len(bm.verts)
    common.loft(bm, sections, sides=segments, mat_index=mat_index)
    bm.verts.ensure_lookup_table()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((cx, cy, z0)), verts=bm.verts[start:])


def loft_x(bm, sections, sides=12, phase=0.5, mat_index=0, cap_start=True, cap_end=True,
           top_scale=1.0):
    """Like common.loft, but each section is (y, x_centre, half_width, half_height, z_centre), so
    the body can follow a sprite whose rows are not centred on one column. A section of zero width
    and height is a point. Ring vertex k sits at angle 2 pi (k + phase) / sides (phase 0 puts a
    vertex on the top when sides is a multiple of 4). `top_scale` stretches the upper half in Z."""
    rings = []
    for y, xc, w, h, z in sections:
        if w == 0 and h == 0:
            rings.append([bm.verts.new((xc, y, z))])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + phase) / sides
            s = math.sin(a)
            ring.append(bm.verts.new((xc + w * math.cos(a), y, z + h * s * (top_scale if s > 0 else 1.0))))
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
            bm.faces.new(f).material_index = mat_index
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat_index
    return rings


def paint(bm, pixels, slot_of, under_slot=None, min_nz=-0.25, spread=0.55, faces=None):
    """Give each face the material slot most of the sprite pixels under it map to (slot_of(index)
    -> slot or None to skip that pixel), sampling its centre and points toward its corners.
    Faces facing down (normal z < min_nz) get `under_slot` if given."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    for f in faces if faces is not None else bm.faces:
        if f.normal.z < min_nz:
            if under_slot is not None:
                f.material_index = under_slot
            continue
        cen = f.calc_center_median()
        pts = [cen, cen] + [cen.lerp(v.co, spread) for v in f.verts]
        votes = Counter()
        for p in pts:
            s = slot_of(sample(pixels, p.x, p.y))
            if s is not None:
                votes[s] += 1
        if votes:
            f.material_index = votes.most_common(1)[0][0]


def preview(objs, sprite, root, name):
    """Render the preview if the script was given `-- --preview <png>`."""
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = Path(root) / "reference" / "models" / name / sprite["frames"][0]["image"]
        common.render_preview(objs, out, ref, size=sprite["frames"][0]["size"])


def green_orb(sprite, name, coll, lift=0.0):
    """One of level 2.4's glossy green orbs (newshh-89, -91, -127): a squashed sphere filling the
    sprite's disc, its facets coloured by the green ramp under them, so the highlight at the top
    left, the dark lower rim and the bright reflection at the bottom right all sit where the
    sprite draws them. The dark outline ring is left to the game's outline."""
    pixels = sprite["frames"][0]["pixels"]
    used = sorted(int(k) for k in sprite["colors"] if 192 <= int(k) <= 207)
    # Material slots: every step of the green ramp, plus any pale highlight colours.
    ramp = used
    pale = [i for i in (46, 47) if str(i) in sprite["colors"]]
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [pal(i, metallic=0.05, roughness=0.25 if i < 203 else 0.15) for i in ramp]
    mats += [pal(i, metallic=0.1, roughness=0.1) for i in pale]

    def slot_of(i):
        if i in pale:
            return len(ramp) + pale.index(i)
        if 192 <= i <= 207:
            return min(range(len(ramp)), key=lambda k: abs(ramp[k] - i))
        return None  # outline pixels: let the neighbours decide

    # The disc: the extent of every non-outline pixel, grown half a pixel into the outline.
    body = extents(pixels, lambda i: i >= 0)
    rows = sorted(body)
    c0 = min(a for a, _ in body.values())
    c1 = max(b for _, b in body.values())
    cx, cy = (px(c0) + px(c1)) / 2, (row(rows[0]) + row(rows[-1])) / 2
    a = (c1 - c0 + 1) / 24 - 0.4 / 12
    b = (rows[-1] - rows[0] + 1) / 24 - 0.4 / 12
    c = min(0.3, 0.62 * a)
    bm = bmesh.new()
    ellipsoid(bm, cx, cy, a, b, c, z0=lift, segments=32, rings=18)
    paint(bm, pixels, slot_of, under_slot=0, min_nz=-0.3)
    return common.mesh_object(name, bm, mats, coll, smooth=True)
