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
