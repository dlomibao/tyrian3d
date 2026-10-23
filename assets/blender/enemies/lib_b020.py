"""Helpers shared by batch b020's enemy scripts (build-models.sh skips lib_ modules).

Mats, merged_colors, tube, box, cylinder_x, loft_x and rotate_new_to_x are copied from lib_b006.
- mirror_x: mirror everything in a bmesh across X = 0 (for a sprite drawn facing the other way).
- composite_png: an assembly's first frames as one image, for the whole-object preview.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units


class Mats:
    """Palette materials, one slot per (palette index, finish). `colors` maps index -> RGB (merge
    several sprites' `colors` for an assembly)."""

    def __init__(self, tag, colors):
        self.sprite = {"name": tag, "colors": colors}
        self.tag = tag
        self.list = []
        self.slots = {}

    def __call__(self, index, metallic=0.3, roughness=0.5, emission_strength=0.0):
        key = (index, metallic, roughness, emission_strength)
        if key not in self.slots:
            tag = self.tag if not emission_strength else f"{self.tag}_glow"
            if any(k[0] == index and k != key for k in self.slots):
                tag = f"{self.tag}_{len(self.list)}"
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, tag, metallic=metallic,
                                                     roughness=roughness, emission_strength=emission_strength))
        return self.slots[key]


def merged_colors(sprites):
    colors = {}
    for s in sprites:
        colors.update(s["colors"])
    return colors


def tube(bm, points, sides=8, mat_index=0, cap_start=True, cap_end=True):
    """A loft along any path: points are ((x, y, z), radius); radius 0 makes a point (a spike tip).
    Each ring is perpendicular to the path at that point."""
    from mathutils import Vector
    pts = [(Vector(p), r) for p, r in points]
    rings = []
    for i, (p, r) in enumerate(pts):
        a = pts[max(0, i - 1)][0]
        b = pts[min(len(pts) - 1, i + 1)][0]
        d = (b - a).normalized()
        ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(ref).normalized()
        w = d.cross(u).normalized()
        if r == 0:
            rings.append([bm.verts.new(p)])
            continue
        rings.append([bm.verts.new(p + r * (math.cos(2 * math.pi * (k + 0.5) / sides) * u +
                                            math.sin(2 * math.pi * (k + 0.5) / sides) * w))
                      for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[k])
            elif len(r1) == 1:
                face = (r0[k], r0[j], r1[0])
            else:
                face = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(face).material_index = mat_index
    if cap_start and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat_index
    if cap_end and len(rings[-1]) > 1:
        bm.faces.new(rings[-1]).material_index = mat_index


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0):
    """An axis-aligned box between corners (x0, y0, z0) and (x1, y1, z1) (units)."""
    common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)


def cylinder_x(bm, x0, x1, y, z, ry, rz, sides=12, mat_index=0, caps=True):
    """A cylinder along X from x0 to x1 centred on (y, z) with radii ry (across) and rz (up)."""
    start = len(bm.verts)
    common.loft(bm, [(x0, ry, rz, 0.0), (x1, ry, rz, 0.0)], sides=sides, mat_index=mat_index,
                cap_start=caps, cap_end=caps)
    rotate_new_to_x(bm, start, y, z)


def loft_x(bm, sections, y, z, sides=12, mat_index=0, cap_start=True, cap_end=True):
    """common.loft along X instead of Y: sections are (x, half_across_y, half_height, z_offset)."""
    start = len(bm.verts)
    common.loft(bm, sections, sides=sides, mat_index=mat_index, cap_start=cap_start, cap_end=cap_end)
    rotate_new_to_x(bm, start, y, z)


def rotate_new_to_x(bm, start, y, z):
    """Turn geometry lofted along Y (x across, y along) to run along X, centred on (y, z)."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        across, along = v.co.x, v.co.y
        v.co.x, v.co.y = along, y - across
        v.co.z += z


def mirror_x(bm):
    """Mirror all geometry across X = 0 (normals are fixed by common.mesh_object)."""
    for v in bm.verts:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])


def composite_png(root, layout, w, h, out):
    """The pieces' first frames as one w x h px image; layout is (name, cx, cy) with each piece's
    centre in px relative to the image centre."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(root, name)
        frame = data["frames"][0]
        x0, y0 = int(cx + w / 2 - 12), int(cy + h / 2 - 14)
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


def build_spindle(name, sprite, mirror=False):
    """The twin-plate spindle of newshl 24 (and, mirrored left to right, newshl 34): a grey shaft
    running across the sprite with a short nose on the left, a wide body, two tall oval plates
    (the thin one first, the thick one second) joined by a dark web carrying two red lights, a
    narrower shaft and a flange at the sprite's right edge, and red brackets above and below
    that shaft. Built in newshl 24's pixel edge coordinates; mirror=True flips it for newshl 34."""
    coll = common.reset_collection(name)
    m = Mats(name, sprite["colors"])
    metal = lambda i: m(i, metallic=0.55, roughness=0.4)  # noqa: E731
    bm = bmesh.new()

    def X(e):
        return (e - 12) * U

    def Y(e):
        return (14 - e) * U

    ay = Y(13.5)  # the shaft's axis (rows 4-22 and 9-17 are both centred on row 13)

    def run(secs, mat, sides=16):
        loft_x(bm, [(X(e), r * U, h, 0.0) for e, r, h in secs], ay, 0.0, sides=sides, mat_index=mat)

    run([(4.6, 1.4, 0.1), (5.0, 2.6, 0.16), (5.6, 2.8, 0.17), (8.1, 2.8, 0.17)], metal(7))  # nose
    run([(7.9, 4.2, 0.22), (8.3, 4.7, 0.25), (12.3, 4.7, 0.25), (12.8, 4.3, 0.23)], metal(10))  # body
    run([(12.6, 3.9, 0.2), (19.2, 3.9, 0.2)], metal(6))  # shaft through the plates
    run([(12.7, 8.6, 0.22), (13.0, 9.6, 0.27), (13.9, 9.6, 0.27), (14.2, 8.6, 0.22)], metal(9), sides=24)  # thin plate
    run([(16.8, 8.6, 0.22), (17.1, 9.6, 0.27), (18.9, 9.6, 0.27), (19.2, 8.6, 0.22)], metal(9), sides=24)  # thick plate
    run([(19.0, 3.2, 0.17), (22.7, 3.2, 0.17)], metal(7))  # right shaft
    run([(22.5, 4.0, 0.21), (22.9, 4.6, 0.24), (24.0, 4.6, 0.24)], metal(8))  # flange at the edge

    # Dark web between the plates (columns 14-16, rows 4-22), its red lights at rows 5 and 21.
    box(bm, X(14.0), Y(22.6), X(17.0), Y(4.4), -0.12, 0.12, mat_index=m(2, metallic=0.4, roughness=0.6))
    for r, idx in ((5, 116), (21, 114)):
        box(bm, X(15.05), Y(r + 0.95), X(15.95), Y(r + 0.05), 0.08, 0.17,
            mat_index=m(idx, metallic=0.0, roughness=0.4, emission_strength=3.0))

    # Red brackets above (rows 7-8) and below (rows 18-19) the right shaft.
    red_top = m(114, metallic=0.4, roughness=0.5)
    common.slab(bm, [(X(19.0), Y(9)), (X(22), Y(9)), (X(22), Y(8)), (X(24), Y(8)), (X(24), Y(7)), (X(19.0), Y(7))][::-1],
                0.14, z=0.03, mat_index=red_top)
    box(bm, X(21.05), Y(8.95), X(21.95), Y(8.05), 0.05, 0.13, mat_index=m(116, metallic=0.0, roughness=0.4,
                                                                          emission_strength=3.0))
    common.slab(bm, [(X(19.0), Y(20)), (X(23), Y(20)), (X(23), Y(19)), (X(22), Y(19)), (X(22), Y(18)), (X(19.0), Y(18))],
                0.14, z=0.03, mat_index=m(113, metallic=0.4, roughness=0.5))

    if mirror:
        mirror_x(bm)
    obj = common.mesh_object(name, bm, m.list, coll, smooth=True)
    split = obj.modifiers.new("edges", "EDGE_SPLIT")
    split.split_angle = math.radians(40)
    return obj
