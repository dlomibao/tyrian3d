"""Helpers shared by batch b077's enemy scripts (build-models.sh skips lib_ modules).

- Grid: sprite (or assembly) pixel coordinates to Blender X/Y, and the pixel under a point.
- Mats: palette materials created on demand, one slot per palette index and finish.
- paint: give faces the material of the sprite pixels under them (seen from above).
- ground: a low plate of grass (or any ground) painted from the sprite, with tufts.
- blob, box, prism, sweep, cyl_x: simple solids.
- to_object: like common.mesh_object, but keeps each face's smooth flag.
- frames_subset, composite_png, piece previews.
"""

import math
import random
import sys
from collections import Counter
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units


class Grid:
    """Pixel grid of width w and height h (pixels) centred on the origin: column c, row r (pixel
    centres at c + 0.5, r + 0.5) map to X = (c + 0.5 - w/2)/12, Y = (h/2 - (r + 0.5))/12.
    x(c)/y(r) take pixel-centre coordinates (fractions allowed); ex(c)/ey(r) take pixel edges."""

    def __init__(self, w, h, pixels=None):
        self.w, self.h, self.pixels = w, h, pixels

    def x(self, c):
        return (c + 0.5 - self.w / 2) * U

    def y(self, r):
        return (self.h / 2 - (r + 0.5)) * U

    def ex(self, c):
        return (c - self.w / 2) * U

    def ey(self, r):
        return (self.h / 2 - r) * U

    def col(self, x):
        return x / U + self.w / 2 - 0.5

    def row(self, y):
        return self.h / 2 - 0.5 - y / U

    def at(self, c, r):
        if self.pixels is None or not (0 <= r < self.h and 0 <= c < self.w):
            return -1
        return self.pixels[r][c]

    def sample(self, x, y, skip=(-1, 1), reach=2):
        """The palette index of the pixel under (x, y); transparent and outline pixels are skipped
        for the nearest other pixel within `reach` pixels (None if there is none)."""
        c, r = int(round(self.col(x))), int(round(self.row(y)))
        for d in range(reach + 1):
            best = None
            for dr in range(-d, d + 1):
                for dc in range(-d, d + 1):
                    if max(abs(dr), abs(dc)) != d:
                        continue
                    v = self.at(c + dc, r + dr)
                    if v not in skip:
                        dist = dr * dr + dc * dc
                        if best is None or dist < best[0]:
                            best = (dist, v)
            if best is not None:
                return best[1]
        return None

    def mode(self, x0, y0, x1, y1, skip=(-1, 1), allow=None):
        """The most common palette index of the pixels whose centres lie in the box (units)."""
        c0, c1 = sorted((self.col(x0), self.col(x1)))
        r0, r1 = sorted((self.row(y0), self.row(y1)))
        votes = Counter()
        for r in range(math.ceil(r0 - 0.01), math.floor(r1 + 0.01) + 1):
            for c in range(math.ceil(c0 - 0.01), math.floor(c1 + 0.01) + 1):
                v = self.at(c, r)
                if v in skip or (allow and not allow(v)):
                    continue
                votes[v] += 1
        if not votes:
            return self.sample((x0 + x1) / 2, (y0 + y1) / 2)
        top = max(votes.values())
        return max(v for v, n in votes.items() if n == top)


def stack_rows(*pieces):
    """Pixel rows of pieces laid out side by side: pieces is a list of rows-of-rows to place
    left to right (all the same height)."""
    return [sum((p[r] for p in pieces), []) for r in range(len(pieces[0]))]


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


def faces_since(bm, first):
    bm.faces.ensure_lookup_table()
    return bm.faces[first:]


def set_smooth(bm, first, smooth=True):
    for f in faces_since(bm, first):
        f.smooth = smooth


def paint(bm, first_face, grid, slot_for, up_only=True, area=False):
    """Set the material of every face added since `first_face` from the sprite pixel under its
    centre (or, with `area`, the most common pixel under the face): slot_for(index) -> slot, or
    None to leave the face as it is. With up_only, faces not facing up keep their material."""
    bm.normal_update()
    for f in faces_since(bm, first_face):
        if up_only and f.normal.z < 0.3:
            continue
        if area:
            xs = [v.co.x for v in f.verts]
            ys = [v.co.y for v in f.verts]
            idx = grid.mode(min(xs), min(ys), max(xs), max(ys))
        else:
            c = f.calc_center_median()
            idx = grid.sample(c.x, c.y)
        if idx is None:
            continue
        slot = slot_for(idx)
        if slot is not None:
            f.material_index = slot


def box(bm, x0, y0, x1, y1, z0, z1, mat_index=0):
    """An axis-aligned box (units). Returns its first face index."""
    first = len(bm.faces)
    common.slab(bm, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)
    return first


def prism(bm, outline, z0, z1, mat_index=0):
    """An outline (units, any winding) extruded from z0 to z1. Returns its first face index."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
    if area < 0:
        outline = list(reversed(outline))
    first = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat_index)
    return first


def blob(bm, centre, radii, segments=16, rings=8, mat_index=0, bump=None, z_floor=None):
    """A UV ellipsoid at `centre` with radii (rx, ry, rz); bump(direction) -> scale factor makes it
    lumpy. With z_floor, vertices below it are flattened onto it (a rock sitting on the ground).
    Returns its first face index."""
    first = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    rx, ry, rz = radii
    for v in res["verts"]:
        d = v.co.copy()
        k = bump(d) if bump else 1.0
        v.co = Vector((cx + d.x * rx * k, cy + d.y * ry * k, cz + d.z * rz * k))
        if z_floor is not None and v.co.z < z_floor:
            v.co.z = z_floor
    for f in faces_since(bm, first):
        f.material_index = mat_index
        f.smooth = True
    return first


def lumpy(seed, amount=0.12, freq=3.0):
    """A bump function for blob: smooth random lumps."""
    rnd = random.Random(seed)
    waves = [(Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized(),
              rnd.uniform(0, 6.28), rnd.uniform(0.5, 1.0)) for _ in range(4)]

    def bump(d):
        s = sum(w * math.sin(freq * d.dot(a) + p) for a, p, w in waves) / 4
        return 1.0 + amount * s
    return bump


def sweep(bm, path, sides=10, mat_index=0, smooth=True, cap_start=True, cap_end=True, up=(0, 0, 1)):
    """A tube along a path of (x, y, z, half_width, half_height) in units. Rings stand
    perpendicular to the path; the width is measured across the path (perpendicular to it and to
    `up`) and the height along `up`. A ring of zero size collapses to a point. Returns its first
    face index."""
    first = len(bm.faces)
    up = Vector(up)
    pts = [Vector(p[:3]) for p in path]
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t = t - up * t.dot(up)
        t.normalize()
        side = t.cross(up)
        if w == 0 and h == 0:
            rings.append([bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            ring.append(bm.verts.new(pts[i] + side * (w * math.cos(a)) + up * (h * math.sin(a))))
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
    for f in faces_since(bm, first):
        f.material_index = mat_index
        f.smooth = smooth
    return first


def cyl_x(bm, x0, x1, y, z, ry, rz, sides=12, mat_index=0, smooth=True):
    """A cylinder lying along X from x0 to x1 (units) with radii ry (across, in Y) and rz (Z)."""
    return sweep(bm, [(x0, y, z, ry, rz), (x1, y, z, ry, rz)], sides=sides, mat_index=mat_index, smooth=smooth)


def disc_z(bm, cx, cy, z0, z1, rx, ry, sides=16, mat_index=0, smooth=True):
    """A vertical cylinder (elliptic) from z0 to z1."""
    first = len(bm.faces)
    bot = [bm.verts.new((cx + rx * math.cos(2 * math.pi * k / sides), cy + ry * math.sin(2 * math.pi * k / sides), z0))
           for k in range(sides)]
    top = [bm.verts.new((v.co.x, v.co.y, z1)) for v in bot]
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((bot[k], bot[j], top[j], top[k])).smooth = smooth
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    for f in faces_since(bm, first):
        f.material_index = mat_index
    return first


def ground(bm, grid, c0, r0, c1, r1, slot_for, cell=2, z=0.035, tufts=None, seed=1, tuft_h=0.05):
    """A low plate over the pixel-edge box (c0, r0)-(c1, r1), its top split into cell x cell pixel
    squares painted with the most common sprite pixel under each. `tufts(index)` -> True puts a
    small pointed tuft on that pixel (bright grass blades). Returns its first face index."""
    first = len(bm.faces)
    nx = max(1, round((c1 - c0) / cell))
    ny = max(1, round((r1 - r0) / cell))
    xs = [grid.ex(c0 + (c1 - c0) * i / nx) for i in range(nx + 1)]
    ys = [grid.ey(r0 + (r1 - r0) * j / ny) for j in range(ny + 1)]
    top = [[bm.verts.new((x, y, z)) for x in xs] for y in ys]
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((top[j + 1][i], top[j + 1][i + 1], top[j][i + 1], top[j][i]))
    # Sides and bottom.
    ring = ([top[0][i] for i in range(nx + 1)] + [top[j][nx] for j in range(1, ny + 1)]
            + [top[ny][i] for i in range(nx - 1, -1, -1)] + [top[j][0] for j in range(ny - 1, 0, -1)])
    bottom = [bm.verts.new((v.co.x, v.co.y, 0.0)) for v in ring]
    n = len(ring)
    for k in range(n):
        m = (k + 1) % n
        bm.faces.new((ring[k], ring[m], bottom[m], bottom[k]))
    bm.faces.new(list(reversed(bottom)))
    for f in faces_since(bm, first):
        f.smooth = False
    paint(bm, first, grid, slot_for, up_only=False, area=True)
    if tufts:
        rnd = random.Random(seed)
        for r in range(int(r0), int(r1)):
            for c in range(int(c0), int(c1)):
                v = grid.at(c, r)
                if v < 0 or not tufts(v):
                    continue
                x, y = grid.x(c) + rnd.uniform(-0.2, 0.2) * U, grid.y(r) + rnd.uniform(-0.2, 0.2) * U
                h = tuft_h * rnd.uniform(0.6, 1.0)
                f0 = len(bm.faces)
                base = [bm.verts.new((x + 0.55 * U * math.cos(a), y + 0.55 * U * math.sin(a), z - 0.005))
                        for a in (0.3, 0.3 + 2.1, 0.3 + 4.2)]
                tip = bm.verts.new((x + rnd.uniform(-0.3, 0.3) * U, y + rnd.uniform(-0.3, 0.3) * U, z + h))
                for k in range(3):
                    bm.faces.new((base[k], base[(k + 1) % 3], tip))
                slot = slot_for(v)
                for f in faces_since(bm, f0):
                    f.material_index = slot if slot is not None else 0
                    f.smooth = False
    return first


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


def frames_subset(sprites, frames):
    """The sprites list with only the given frame numbers kept (for one model of an animation)."""
    out = []
    for s in sprites:
        keep = [f for f in s["frames"] if f in frames]
        if keep:
            out.append({**s, "frames": keep})
    return out


def composite_png(pieces, w, h, out):
    """Several pieces' frames as one image: pieces is a list of (sprite_data, frame_index, x0, y0)
    with (x0, y0) the piece's top-left pixel in a w x h image."""
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.float32)
    for data, fi, x0, y0 in pieces:
        frame = data["frames"][fi]
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("b077_composite", w, h, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def preview_arg():
    if "--preview" in sys.argv:
        return Path(sys.argv[sys.argv.index("--preview") + 1])
    return None


def face_count(objs):
    return sum(len(o.data.polygons) for o in objs)


def clip_below(bm, z=0.0, fill=True):
    """Cut away everything below height z (a ground object's buried half), filling the cut."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, -1), clear_outer=True)
    if fill:
        edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            res = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
            for f in res["faces"]:
                f.smooth = False


def mirror_x(bm, first_vert, axis_x=0.0):
    """Add a mirror copy (about x = axis_x) of everything built since vertex index `first_vert`."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[first_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = [e for e in bm.edges if all(v in verts for v in e.verts)]
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * axis_x - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])
