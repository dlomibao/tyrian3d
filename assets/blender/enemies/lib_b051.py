"""Helpers shared by batch b051's model scripts (episode 4 fire columns and flame bowls, a grey
pod, a red canister chain link and a grey mech gate).

A Grid maps sprite pixels (one sprite, or several assembly pieces put side by side) to Blender
coordinates and back, so parts can be placed by pixel and faces painted with the palette index of
the pixel under them. build-models.sh skips lib_ files; the model scripts import this next to them.
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

PX = 1 / 12  # one sprite pixel in units


class Grid:
    """Palette indices by (row, column) with the block's centre at the Blender origin."""

    def __init__(self, pixels):
        self.pixels = pixels
        self.h = len(pixels)
        self.w = len(pixels[0])

    def X(self, c):
        """Pixel column (centre; fractions allowed) to Blender X."""
        return (c + 0.5 - self.w / 2) / 12

    def Y(self, r):
        """Pixel row (centre) to Blender Y: sprite up is +Y."""
        return (self.h / 2 - (r + 0.5)) / 12

    def P(self, c, r, z=0.0):
        return Vector((self.X(c), self.Y(r), z))

    def at(self, x, y):
        """The palette index under Blender (x, y), -1 outside or transparent."""
        c = int(math.floor(x * 12 + self.w / 2))
        r = int(math.floor(self.h / 2 - y * 12))
        if 0 <= r < self.h and 0 <= c < self.w:
            return self.pixels[r][c]
        return -1


def sprite_grid(sprite, frame=0):
    return Grid(sprite["frames"][frame]["pixels"])


def assembly(root, names):
    """The pieces `names` of an assembly put together. Returns (grid, layout, sprite) where layout
    is [(name, cx, cy)] relative to the grid's centre, ready for common.split_assembly, and sprite
    is the first piece's sprite.json with every piece's colours merged in."""
    sprites = {n: common.load_sprite(root, n) for n in names}
    lay = [e for e in sprites[names[0]]["assemblyLayout"] if e["model"] in names]
    left = min(e["cx"] - 12 for e in lay)
    top = min(e["cy"] - 14 for e in lay)
    right = max(e["cx"] + 12 for e in lay)
    bottom = max(e["cy"] + 14 for e in lay)
    w, h = right - left, bottom - top
    pixels = [[-1] * w for _ in range(h)]
    for e in lay:
        for r, row in enumerate(sprites[e["model"]]["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    pixels[e["cy"] - 14 - top + r][e["cx"] - 12 - left + c] = v
    cx0, cy0 = left + w / 2, top + h / 2
    layout = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in lay]
    merged = dict(sprites[names[0]])
    merged["colors"] = {}
    for s in sprites.values():
        merged["colors"].update(s["colors"])
    return Grid(pixels), layout, merged


def faces_from(bm, start):
    bm.faces.ensure_lookup_table()
    return bm.faces[start:]


def set_smooth(bm, start, smooth=True):
    for f in faces_from(bm, start):
        f.smooth = smooth


def sweep(bm, g, path, sides=10, mat=0, smooth=True, cap_start=True, cap_end=True, power=1.0):
    """A tube along a path of (col, row, z, half_width_px, half_height_units) in grid `g`. Rings
    stand across the path in the XY plane (width) and along Z (height); a ring of zero size is a
    point (a tip). `power` < 1 squares off the cross-section."""
    pts = [g.P(c, r, z) for c, r, z, _, _ in path]
    up = Vector((0, 0, 1))
    rings = []
    for i, (c, r, z, w, hh) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        if t.length < 1e-9:
            t = Vector((0, 1, 0))
        t.normalize()
        side = t.cross(up)
        if w == 0 and hh == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ca, sa = math.cos(a), math.sin(a)
            ca = math.copysign(abs(ca) ** power, ca)
            sa = math.copysign(abs(sa) ** power, sa)
            ring.append(bm.verts.new(pts[i] + side * (w * PX * ca) + up * (hh * sa)))
        rings.append(ring)
    start = len(bm.faces)
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
    for f in faces_from(bm, start):
        f.material_index = mat
        f.smooth = smooth


def tube3d(bm, points, radii, sides=8, mat=0, smooth=True, caps=True):
    """A round tube along a 3D polyline with a radius per point (0 makes a tip), rings carried
    along by parallel transport so twisting paths (helices) don't pinch."""
    pts = [Vector(p) for p in points]
    tangents = []
    for i in range(len(pts)):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tangents.append(t.normalized())
    ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    u = tangents[0].cross(ref).normalized()
    rings = []
    for c, t, rad in zip(pts, tangents, radii):
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u).normalized()
        if rad == 0:
            rings.append([bm.verts.new(c)])
            continue
        rings.append([bm.verts.new(c + rad * (math.cos(a) * u + math.sin(a) * v))
                      for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))])
    start = len(bm.faces)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                f = (r0[0], r1[k], r1[j])
            elif len(r1) == 1:
                f = (r0[k], r0[j], r1[0])
            else:
                f = (r0[k], r0[j], r1[j], r1[k])
            bm.faces.new(f)
    if caps:
        if len(rings[0]) > 1:
            bm.faces.new(rings[0])
        if len(rings[-1]) > 1:
            bm.faces.new(list(reversed(rings[-1])))
    for f in faces_from(bm, start):
        f.material_index = mat
        f.smooth = smooth


def ellipsoid(bm, centre, radii, segments=16, rings=8, mat=0, smooth=True):
    start = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    a, b, c = radii
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * a, cy + v.co.y * b, cz + v.co.z * c))
    for f in faces_from(bm, start):
        f.material_index = mat
        f.smooth = smooth


def plate(bm, g, outline, z0, z1, mat=0, smooth=False):
    """A flat prism from z0 to z1 whose outline is (col, row) pixel edges (counter-clockwise on
    screen is fine; normals are recalculated at the end)."""
    pts = [(g.X(c - 0.5), g.Y(r - 0.5)) for c, r in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    start = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    for f in faces_from(bm, start):
        f.smooth = smooth


def box(bm, g, c0, r0, c1, r1, z0, z1, mat=0):
    """A box over pixel columns c0..c1 and rows r0..r1 (inclusive, pixel edges outside them)."""
    plate(bm, g, [(c0, r0), (c1 + 1, r0), (c1 + 1, r1 + 1), (c0, r1 + 1)], z0, z1, mat=mat)


def mirror(bm, ax, start_vert=0):
    """Add a mirror image about x = ax of the geometry from vertex `start_vert` on (all of it by
    default). Faces keep their material and smooth flags."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = list({e for f in faces for e in f.edges})
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * ax - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def paint(bm, g, slot_of, start=0, min_nz=-0.25, under=None, average=True, keep=None):
    """Give faces (from index `start` on) the material slot of the sprite pixels under them:
    slot_of(index) -> slot, or None to leave the face as it is. `average` takes the mean index over
    the face (good for one colour ramp). Faces facing down (normal z < min_nz) get `under` if given.
    `keep` is a set of slots that are never repainted."""
    bm.normal_update()
    for f in faces_from(bm, start):
        if keep and f.material_index in keep:
            continue
        if f.normal.z < min_nz:
            if under is not None:
                f.material_index = under
            continue
        cen = f.calc_center_median()
        pts = [cen] + ([cen.lerp(v.co, 0.6) for v in f.verts] if average else [])
        vals = [g.at(p.x, p.y) for p in pts]
        vals = [v for v in vals if v >= 0]
        if not vals:
            continue
        idx = round(sum(vals) / len(vals)) if average else vals[0]
        slot = slot_of(idx)
        if slot is not None:
            f.material_index = slot


def paint_soft(bm, g, slot_of, nslots, start=0, window=1.5, pct=0.7, under=0, crest=0.75, flank=0.3,
               keep=None):
    """Like paint, but smoothed for noisy sprites (fire): each face takes the `pct` percentile of the
    indices within `window` px of its centre, one slot brighter where it faces straight up (normal
    z > crest), one darker on steep flanks (z < flank) and `under` facing down."""
    bm.normal_update()
    offs = [(dx, dy) for dx in (-1, -0.5, 0, 0.5, 1) for dy in (-1, -0.5, 0, 0.5, 1)]
    for f in faces_from(bm, start):
        if keep and f.material_index in keep:
            continue
        nz = f.normal.z
        if nz < -0.25:
            f.material_index = under
            continue
        cen = f.calc_center_median()
        vals = sorted(v for v in (g.at(cen.x + dx * window * PX, cen.y + dy * window * PX) for dx, dy in offs)
                      if v >= 0)
        if not vals:
            continue
        slot = slot_of(vals[min(len(vals) - 1, int(pct * len(vals)))])
        if slot is None:
            continue
        if nz > crest:
            slot += 1
        elif nz < flank:
            slot -= 1
        f.material_index = max(0, min(nslots - 1, slot))


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


def scale_z(obj, k):
    for v in obj.data.vertices:
        v.co.z *= k


# --- fire --------------------------------------------------------------------------------------

FIRE = [  # (palette index of the slot, first index it covers, emission strength)
    (113, 112, 0.0),
    (115, 114, 1.0),
    (118, 117, 2.0),
    (120, 120, 3.0),
    (122, 122, 4.0),
    (124, 124, 5.0),
]


def fire_materials(sprite, tag):
    """One material per band of the red-orange-yellow fire ramp (indices 112-127), glowing more
    the brighter it is. Slot i covers FIRE[i]."""
    return [common.palette_material(sprite, i, tag, metallic=0.0, roughness=0.6, emission_strength=e)
            for i, _, e in FIRE]


def fire_slot(index):
    if index < 112 or index > 127:
        return None
    slot = 0
    for k, (_, first, _) in enumerate(FIRE):
        if index >= first:
            slot = k
    return slot


# --- preview ------------------------------------------------------------------------------------

def grid_png(g, colors, out, size):
    """The grid's pixels as an image padded (centred) to the 24:28 block of `size` tiles that
    common.render_preview expects."""
    import numpy as np
    W, H = 12 * size, 14 * size
    img = np.zeros((H, W, 4), dtype=np.float32)
    x0, y0 = (W - g.w) // 2, (H - g.h) // 2
    for r, row in enumerate(g.pixels):
        for c, v in enumerate(row):
            if v >= 0:
                img[y0 + r, x0 + c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("grid_png", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def preview_assembly(root, whole, pieces, g, sprite, size):
    """With -- --preview <png>: the whole object beside the composed sprite, and each piece beside
    its own sprite in <piece>.png next to it."""
    if "--preview" not in sys.argv:
        return
    out = Path(sys.argv[sys.argv.index("--preview") + 1])
    ref = grid_png(g, sprite["colors"], Path(tempfile.mkdtemp()) / "assembly.png", size)
    common.render_preview([whole], str(out), str(ref), size=size, view_px=480)
    for name, obj in pieces.items():
        data = common.load_sprite(root, name)
        img = Path(root) / "reference" / "models" / name / data["frames"][0]["image"]
        common.render_preview([obj], str(out.parent / f"{name}.png"), img, size=2)


def preview(root, name, objs, sprite):
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = Path(root) / "reference" / "models" / name / frame["image"]
        common.render_preview(objs, out, ref, size=frame["size"])
