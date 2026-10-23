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

    def __init__(self, w, h, pixels=None, weight=None):
        self.w, self.h, self.pixels = w, h, pixels
        self.weight = weight  # weight(index) -> votes per pixel in mode() (favour bright blades)

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
                votes[v] += self.weight(v) if self.weight else 1
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


def terrain(bm, grid, c0, r0, c1, r1, height, slot_for, cell=2.0, smooth=False):
    """A block over the pixel-edge box (c0, r0)-(c1, r1) whose top is a grid of cell x cell pixel
    squares raised to height(col, row) (pixel-edge coordinates) at each corner: rocks, mounds and
    banks shaped by the caller. Top squares are painted with the most common sprite pixel under
    them; the sides take the material of the top square above. Returns its first face index."""
    first = len(bm.faces)
    nx = max(1, round((c1 - c0) / cell))
    ny = max(1, round((r1 - r0) / cell))
    cs = [c0 + (c1 - c0) * i / nx for i in range(nx + 1)]
    rs = [r0 + (r1 - r0) * j / ny for j in range(ny + 1)]
    top = [[bm.verts.new((grid.ex(c), grid.ey(r), max(0.002, height(c, r)))) for c in cs] for r in rs]
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((top[j + 1][i], top[j + 1][i + 1], top[j][i + 1], top[j][i]))
            f.smooth = smooth
    paint(bm, first, grid, slot_for, up_only=False, area=True)
    tops = faces_since(bm, first)
    ring = ([top[0][i] for i in range(nx + 1)] + [top[j][nx] for j in range(1, ny + 1)]
            + [top[ny][i] for i in range(nx - 1, -1, -1)] + [top[j][0] for j in range(ny - 1, 0, -1)])
    bottom = [bm.verts.new((v.co.x, v.co.y, 0.0)) for v in ring]
    n = len(ring)
    for k in range(n):
        m = (k + 1) % n
        f = bm.faces.new((ring[k], ring[m], bottom[m], bottom[k]))
        e = ring[k].link_faces
        f.material_index = next((t.material_index for t in e if t in tops), 0)
        f.smooth = False
    bm.faces.new(list(reversed(bottom))).smooth = False
    return first


def mound(c, r, c0, r0, rc, rr, h, power=0.5):
    """Height of an elliptic mound centred on pixel edge coords (c0, r0) with radii (rc, rr) px."""
    d = ((c - c0) / rc) ** 2 + ((r - r0) / rr) ** 2
    return h * max(0.0, 1.0 - d) ** power


def noise2(seed, amount=0.03, freq=0.7):
    """A smooth 2D noise function of pixel coordinates (small rocky unevenness)."""
    rnd = random.Random(seed)
    waves = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0, 6.28)) for _ in range(5)]

    def f(c, r):
        return amount * sum(math.sin(freq * (a * c + b * r) * 2 + p) for a, b, p in waves) / 5
    return f


def tufts(bm, grid, c0, r0, c1, r1, pred, slot_for, height, seed=1, tuft_h=0.05):
    """Small pointed grass tufts on the pixels (in the pixel-edge box) for which pred(index) is
    true, standing on height(col, row)."""
    rnd = random.Random(seed)
    for r in range(int(r0), int(r1)):
        for c in range(int(c0), int(c1)):
            v = grid.at(c, r)
            if v < 0 or not pred(v):
                continue
            x, y = grid.x(c) + rnd.uniform(-0.2, 0.2) * U, grid.y(r) + rnd.uniform(-0.2, 0.2) * U
            z = height(c + 0.5, r + 0.5)
            h = tuft_h * rnd.uniform(0.6, 1.0)
            f0 = len(bm.faces)
            base = [bm.verts.new((x + 0.55 * U * math.cos(a), y + 0.55 * U * math.sin(a), z - 0.01))
                    for a in (0.3, 0.3 + 2.1, 0.3 + 4.2)]
            tip = bm.verts.new((x + rnd.uniform(-0.3, 0.3) * U, y + rnd.uniform(-0.3, 0.3) * U, z + h))
            for k in range(3):
                bm.faces.new((base[k], base[(k + 1) % 3], tip))
            slot = slot_for(v)
            for f in faces_since(bm, f0):
                f.material_index = slot if slot is not None else 0
                f.smooth = False


# --- The grey cannon emplacement in the grass (assembly-newshg-231 and its mirror, -267) ---------

CANNON_GREENS = set(range(32, 36)) | set(range(192, 200))


def build_cannon(tag, colors, pixels, mirror=False):
    """The 48 x 28 px cannon emplacement (newshg-229 + newshg-231, or mirrored newshg-267 +
    newshg-269) in assembly coordinates, centred on the origin, on grass painted from `pixels`
    (the two pieces' rows side by side). Unmirrored, its rounded elbow nose is on the left and the
    strut, collar and end box on the right; `mirror` flips it left to right."""
    coll = common.reset_collection(tag)
    grid = Grid(48, 28, pixels, weight=lambda i: 1.8 if 194 <= i <= 199 else 1.0)
    M = Mats(tag, colors)
    X, Y, EX, EY = grid.x, grid.y, grid.ex, grid.ey
    TUBE = M(7, metallic=0.65, roughness=0.3)
    LIGHT = M(9, metallic=0.65, roughness=0.3)
    RIM = M(11, metallic=0.7, roughness=0.25)
    LENS = M(14 if "14" in colors else 12, metallic=0.5, roughness=0.15)
    DECK = M(2, metallic=0.5, roughness=0.5)
    RIB = M(4, metallic=0.5, roughness=0.45)
    SIDE = M(5, metallic=0.55, roughness=0.45)
    STRUT = M(8, metallic=0.6, roughness=0.35)
    PORT = M(116, emission_strength=3.0)
    FLAME = M(119, emission_strength=4.0)
    HOT = M(123, emission_strength=6.0)
    bm = bmesh.new()

    # ---- the machine, built nose-left ----
    tz, tr, ty = 0.37, 0.2, 4.0  # tube centre height, height radius and centre row (pixel centres)
    # Low dark deck along the front (rows 7-15) with its rounded left end.
    deck = [(1.6, 8.5), (3.0, 7.2), (8.0, 6.8), (31.0, 6.8), (31.0, 14.6), (22.0, 15.4), (4.0, 15.2),
            (2.0, 14.0), (1.2, 11.5)]
    prism(bm, [(EX(c), EY(r)) for c, r in deck], 0.0, 0.2, mat_index=DECK)
    # Grille ribs on the deck (columns 11-19) and a raised panel at its left (columns 5-9).
    for c in (11, 13, 15, 17, 19):
        box(bm, EX(c), EY(15.0), EX(c + 0.9), EY(8.6), 0.2, 0.235, mat_index=RIB)
    box(bm, EX(5.0), EY(11.0), EX(9.5), EY(8.0), 0.2, 0.25, mat_index=SIDE)
    # Glowing port at the seam (columns 20-24, rows 11-13).
    box(bm, EX(20.2), EY(14.0), EX(25.0), EY(10.8), 0.16, 0.225, mat_index=PORT)

    # Main tube along the top (rows 1-7, columns 9-31), with a flange ring at its left end.
    cyl_x(bm, X(8.6), X(31.0), Y(ty), tz, 3.3 * U, tr, sides=14, mat_index=TUBE)
    cyl_x(bm, X(8.6), X(10.2), Y(ty), tz, 3.7 * U, tr + 0.03, sides=14, mat_index=RIM)
    cyl_x(bm, X(30.6), X(31.6), Y(ty), tz, 3.4 * U, tr + 0.015, sides=14, mat_index=RIM)
    # Scope lens (columns 15-17, rows 3-4) and the sliding hatch beside it (columns 19-24).
    blob(bm, (X(16.0), Y(3.6), tz + tr - 0.01), (1.6 * U, 1.1 * U, 0.05), segments=10, rings=5, mat_index=LENS)
    box(bm, EX(14.4), EY(4.8), EX(18.0), EY(2.6), tz + tr - 0.04, tz + tr + 0.01, mat_index=RIB)
    box(bm, EX(19.0), EY(4.8), EX(25.0), EY(2.6), tz + tr - 0.04, tz + tr + 0.015, mat_index=STRUT)
    # Light rail along the tube's lower side (row 6).
    cyl_x(bm, X(9.0), X(30.5), Y(6.2), tz - tr * 0.55, 0.9 * U, 0.05, sides=8, mat_index=LIGHT)

    # Elbow nose: the tube turns down the screen at its left end and is capped (columns 1-9).
    path = [(9.0, ty, 0.0), (7.0, 4.3, 0.0), (5.2, 5.4, -0.01), (3.8, 7.2, -0.03), (3.0, 9.3, -0.05),
            (2.8, 11.0, -0.07)]
    pts = [(X(c), Y(r), tz + dz, 3.3 * U, tr + dz) for c, r, dz in path]
    pts.append((X(2.8), Y(12.2), tz - 0.07, 2.6 * U, tr - 0.1))
    pts.append((X(2.8), Y(12.6), tz - 0.07, 0.0, 0.0))
    sweep(bm, pts, sides=14, mat_index=TUBE)
    # Its lit cap rim (the light arc at columns 2-4, rows 5-11).
    sweep(bm, [(X(c), Y(r), tz - 0.02, 0.6 * U, 0.04) for c, r in
               ((7.2, 2.0), (5.0, 3.0), (3.0, 4.8), (1.6, 7.0), (1.0, 9.5))], sides=6, mat_index=LIGHT)

    # Narrow shaft to the collar (columns 31-38, rows 3-5).
    cyl_x(bm, X(31.0), X(38.2), Y(ty), tz, 1.7 * U, 0.1, sides=10, mat_index=SIDE)
    # Collar (columns 38-40, rows 1-8) and the end box (columns 41-45, rows 3-7).
    cyl_x(bm, X(37.7), X(40.6), Y(ty + 0.3), tz - 0.02, 3.9 * U, tr + 0.04, sides=16, mat_index=LIGHT)
    box(bm, EX(41.0), EY(8.0), EX(46.0), EY(2.6), 0.0, 0.46, mat_index=TUBE)
    box(bm, EX(41.4), EY(5.6), EX(45.6), EY(3.0), 0.46, 0.49, mat_index=LIGHT)

    # Beam under the tube's right end (rows 7-9, columns 23-37).
    box(bm, EX(23.0), EY(9.6), EX(37.5), EY(7.4), 0.08, 0.26, mat_index=STRUT)
    # Diagonal strut from the collar down to its foot (columns 31-41, rows 7-15).
    sweep(bm, [(X(38.6), Y(7.8), 0.32, 1.5 * U, 0.06), (X(36.2), Y(10.2), 0.22, 1.5 * U, 0.06),
               (X(34.0), Y(12.6), 0.12, 1.5 * U, 0.06)], sides=8, mat_index=STRUT)
    sweep(bm, [(X(40.4), Y(8.2), 0.26, 1.0 * U, 0.05), (X(38.6), Y(10.2), 0.2, 1.0 * U, 0.05),
               (X(37.2), Y(11.6), 0.12, 1.0 * U, 0.05)], sides=8, mat_index=RIB)
    box(bm, EX(31.0), EY(15.0), EX(35.2), EY(11.6), 0.0, 0.14, mat_index=SIDE)
    # Exhaust slot glowing beside the strut (columns 39-44, rows 8-13).
    sweep(bm, [(X(43.4), Y(8.8), 0.15, 0.0, 0.0), (X(43.0), Y(9.2), 0.15, 1.1 * U, 0.06),
               (X(40.2), Y(12.4), 0.1, 1.3 * U, 0.06), (X(39.8), Y(12.9), 0.1, 0.0, 0.0)], sides=10, mat_index=FLAME)
    sweep(bm, [(X(42.6), Y(9.8), 0.17, 0.0, 0.0), (X(42.2), Y(10.2), 0.17, 0.5 * U, 0.04),
               (X(41.0), Y(11.6), 0.14, 0.5 * U, 0.04), (X(40.6), Y(12.0), 0.14, 0.0, 0.0)], sides=8, mat_index=HOT)

    for f in bm.faces:
        if f.material_index in (DECK, RIB, SIDE) and len(f.verts) == 4:
            f.smooth = False
    if mirror:
        for v in bm.verts:
            v.co.x = -v.co.x
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])

    # ---- grass over the whole footprint ----
    def grass(i):
        if i in CANNON_GREENS:
            return M(i, metallic=0.0, roughness=1.0)
        return M(33, metallic=0.0, roughness=1.0)  # the machine's shadow on the grass
    flat = lambda c, r: 0.035  # noqa: E731
    terrain(bm, grid, 0, 0, 48, 28, flat, grass, cell=2.0)
    tufts(bm, grid, 0, 0, 48, 28, lambda i: i >= 196 and i in CANNON_GREENS, grass, flat, seed=7)
    return to_object(tag, bm, M.list, coll)


def cannon_main(root, left, right, mirror, name):
    """Build, split and export an assembly of two cannon pieces (left and right model names)."""
    a, b = common.load_sprite(root, left), common.load_sprite(root, right)
    colors = merged_colors([a, b])
    pixels = stack_rows(a["frames"][0]["pixels"], b["frames"][0]["pixels"])
    obj = build_cannon(name, colors, pixels, mirror)
    pieces = common.split_assembly(obj, [(left, -12, 0), (right, 12, 0)])
    for n, data in ((left, a), (right, b)):
        common.export_sprite_model(root, [pieces[n]], f"enemies/{n}", data["sprites"])
    out = preview_arg()
    if out:
        import tempfile
        ref = composite_png([(a, 0, 0, 14), (b, 0, 24, 14)], 48, 56, Path(tempfile.mkdtemp()) / "a.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for n, data in ((left, a), (right, b)):
            img = root / "reference" / "models" / n / data["frames"][0]["image"]
            common.render_preview([pieces[n]], str(out.parent / f"{n}.png"), img, size=2)
