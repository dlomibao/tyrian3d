"""Helpers shared by batch b073's model scripts (build-models.sh skips lib_ modules).

Batch b073 is the grey stone fortress set of newshd/newshs/newshm/newshp.shp (episodes 1-3): tiles
of machinery laid on a stone-brick floor. Every piece fills (most of) its tile, so each model is a
low floor plate with the machinery built on top of it, base at z = 0.

- Grid: sprite (or assembly) pixel coordinates to Blender X/Y.
- Mats: palette materials created on demand, one slot per (index, finish).
- floor: the flat stone floor plate, its top painted in a few grey tones from the sprite.
- painted: a surface over a pixel rectangle whose faces take the sprite's colours (numerals, decals).
- box, prism, pillow (bevelled block), dome, ellipsoid, tube, loft_x/loft_y, capsule.
- finish: bmesh to object keeping each face's smooth flag.
- run / run_assembly: build, export and preview (single tiles or several pieces cut from one model).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

U = 1 / 12  # one sprite pixel in units
FLOOR = 0.03  # top of the floor plate


class Grid:
    """Pixel grid w x h centred on the origin. x(c)/y(r) give a pixel centre (fractions allowed),
    ex(c)/ey(r) the left/top edge of column c/row r."""

    def __init__(self, w=24, h=28, pixels=None):
        self.w, self.h, self.pixels = w, h, pixels

    def x(self, c):
        return (c + 0.5 - self.w / 2) * U

    def y(self, r):
        return (self.h / 2 - (r + 0.5)) * U

    def ex(self, c):
        return (c - self.w / 2) * U

    def ey(self, r):
        return (self.h / 2 - r) * U

    def at(self, c, r):
        if self.pixels is None or not (0 <= r < self.h and 0 <= c < self.w):
            return -1
        return self.pixels[r][c]


class Mats:
    """Palette materials, one slot per (palette index, finish)."""

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

    def stone(self, index):
        """The stone floor / wall finish."""
        return self(index, metallic=0.05, roughness=0.85)

    def metal(self, index):
        return self(index, metallic=0.6, roughness=0.35)

    def glow(self, index, strength=3.0):
        return self(index, metallic=0.0, roughness=0.4, emission_strength=strength)


def merged_colors(root, names):
    colors = {}
    for n in names:
        colors.update(common.load_sprite(root, n)["colors"])
    return colors


# --- primitives ---------------------------------------------------------------------------------

def _faces_since(bm, n):
    bm.faces.ensure_lookup_table()
    return bm.faces[n:]


def _tag(bm, n, mat, smooth):
    for f in _faces_since(bm, n):
        f.material_index = mat
        f.smooth = smooth


def box(bm, x0, y0, x1, y1, z0, z1, mat=0, smooth=False):
    """Axis-aligned box (Blender coordinates)."""
    n = len(bm.faces)
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2)
    _tag(bm, n, mat, smooth)


def rect(grid, c0, r0, c1, r1):
    """Outline of the pixel-edge rectangle columns c0..c1, rows r0..r1 (counter-clockwise)."""
    g = grid
    return [(g.ex(c0), g.ey(r1)), (g.ex(c1), g.ey(r1)), (g.ex(c1), g.ey(r0)), (g.ex(c0), g.ey(r0))]


def chamfer(grid, c0, r0, c1, r1, k):
    """An octagon in the pixel-edge rectangle with corners cut by k pixels."""
    g = grid
    return [(g.ex(c0 + k), g.ey(r1)), (g.ex(c1 - k), g.ey(r1)), (g.ex(c1), g.ey(r1 - k)), (g.ex(c1), g.ey(r0 + k)),
            (g.ex(c1 - k), g.ey(r0)), (g.ex(c0 + k), g.ey(r0)), (g.ex(c0), g.ey(r0 + k)), (g.ex(c0), g.ey(r1 - k))]


def prism(bm, outline, z0, z1, mat=0, smooth=False):
    """Extrude an outline (Blender XY points, either winding) from z0 to z1."""
    if _area(outline) < 0:
        outline = list(reversed(outline))
    n = len(bm.faces)
    common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2)
    _tag(bm, n, mat, smooth)


def _area(pts):
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts))) / 2


def inset(outline, d):
    """Offset a counter-clockwise polygon inward by d (mitred corners)."""
    n = len(outline)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(outline[i - 1]), Vector(outline[i]), Vector(outline[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x))
        n1 = Vector((-e1.y, e1.x))
        bis = n0 + n1
        if bis.length < 1e-6:
            bis = n0
        bis.normalize()
        cos = max(bis.dot(n0), 0.3)
        q = p1 + bis * (d / cos)
        out.append((q.x, q.y))
    return out


def ring_loft(bm, rings, mat=0, smooth=False, cap_start=True, cap_end=True):
    """Join rings of 3D points (same length, or one point for a tip) in order."""
    n0 = len(bm.faces)
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    for r0, r1 in zip(verts, verts[1:]):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            bm.faces.new(face)
    if cap_start and len(verts[0]) > 2:
        bm.faces.new(list(reversed(verts[0])))
    if cap_end and len(verts[-1]) > 2:
        bm.faces.new(verts[-1])
    _tag(bm, n0, mat, smooth)
    return verts


def pillow(bm, outline, z0, z1, bevel, mat=0, top_mat=None, bevel_h=None, smooth=False):
    """A block with a chamfered top: outline (Blender XY) from z0 up to z1 - bevel_h, then in by
    `bevel` up to z1. top_mat colours the flat top."""
    if _area(outline) < 0:
        outline = list(reversed(outline))
    bh = bevel if bevel_h is None else bevel_h
    top = inset(outline, bevel)
    n = len(bm.faces)
    ring_loft(bm, [[(x, y, z0) for x, y in outline], [(x, y, z1 - bh) for x, y in outline],
                   [(x, y, z1) for x, y in top]], mat=mat, smooth=smooth)
    if top_mat is not None:
        bm.faces.ensure_lookup_table()
        bm.faces[-1].material_index = top_mat
    return n


def ellipse(cx, cy, rx, ry, n=16, power=2.0, phase=0.5):
    """Points of a (super)ellipse, counter-clockwise. power > 2 squares it off."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * (i + phase) / n
        c, s = math.cos(a), math.sin(a)
        e = 2 / power
        pts.append((cx + rx * math.copysign(abs(c) ** e, c), cy + ry * math.copysign(abs(s) ** e, s)))
    return pts


def dome(bm, cx, cy, rx, ry, h, z0=FLOOR, sides=16, rings=4, mat=0, power=2.0, flat=0.0, smooth=True,
         base=True):
    """Half ellipsoid (or squared-off with power > 2) from z0 up to z0 + h. `flat` keeps the top
    that fraction flat (a rounded-edge block)."""
    rs = []
    for k in range(rings + 1):
        t = k / rings
        phi = t * math.pi / 2
        s = math.cos(phi) * (1 - flat) + flat if k < rings else flat
        z = z0 + h * math.sin(phi)
        if s <= 1e-4:
            rs.append([(cx, cy, z0 + h)])
        else:
            rs.append([(x, y, z) for x, y in ellipse(cx, cy, rx * s, ry * s, sides, power)])
    ring_loft(bm, rs, mat=mat, smooth=smooth, cap_start=base)


def ellipsoid(bm, cx, cy, cz, rx, ry, rz, sides=16, rings=8, mat=0, smooth=True):
    n = len(bm.faces)
    res = bmesh.ops.create_uvsphere(bm, u_segments=sides, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * rx, cy + v.co.y * ry, cz + v.co.z * rz))
    _tag(bm, n, mat, smooth)


def tube(bm, points, radius, sides=8, mat=0, smooth=True, caps=True, flat=1.0):
    """A round tube along a 3D polyline (mitred joints). radius: number or one per point.
    flat scales the tube's vertical radius (flat < 1 squashes it)."""
    pts = [Vector(p) for p in points]
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    tangents = []
    for i in range(len(pts)):
        d0 = (pts[i] - pts[i - 1]).normalized() if i > 0 else None
        d1 = (pts[i + 1] - pts[i]).normalized() if i < len(pts) - 1 else None
        t = (d0 + d1) if d0 is not None and d1 is not None else (d0 if d1 is None else d1)
        tangents.append(t.normalized())
    rings = []
    for c, t, r in zip(pts, tangents, radii):
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(ref).normalized()
        v = u.cross(t).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            off = u * (math.cos(a) * r) + v * (math.sin(a) * r)
            off.z *= flat
            ring.append(tuple(c + off))
        rings.append(ring)
    ring_loft(bm, rings, mat=mat, smooth=smooth, cap_start=caps, cap_end=caps)


def loft_y(bm, x, sections, sides=10, mat=0, smooth=True, power=2.0, cap_start=True, cap_end=True):
    """Loft along Y at column position x: sections (y, half_w, half_h, z). Zero size = a tip."""
    rings = []
    for y, w, h, z in sections:
        if w == 0 and h == 0:
            rings.append([(x, y, z)])
        else:
            rings.append([(x + px_, y, z + pz) for px_, pz in ellipse(0, 0, w, h, sides, power)])
    ring_loft(bm, rings, mat=mat, smooth=smooth, cap_start=cap_start, cap_end=cap_end)


def loft_x(bm, y, sections, sides=10, mat=0, smooth=True, power=2.0, cap_start=True, cap_end=True):
    """Loft along X at row position y: sections (x, half_w (along Y), half_h, z)."""
    rings = []
    for x, w, h, z in sections:
        if w == 0 and h == 0:
            rings.append([(x, y, z)])
        else:
            rings.append([(x, y + py, z + pz) for py, pz in ellipse(0, 0, w, h, sides, power)])
    ring_loft(bm, rings, mat=mat, smooth=smooth, cap_start=cap_start, cap_end=cap_end)


def mirror_x(bm, start_vert, axis=0.0):
    """Duplicate everything from vertex index start_vert mirrored about x = axis."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + faces)["geom"]
    for e in dup:
        if isinstance(e, bmesh.types.BMVert):
            e.co.x = 2 * axis - e.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


# --- painted surfaces ---------------------------------------------------------------------------

def painted(bm, grid, c0, r0, c1, r1, zfunc, slot_of, skip=(-1,), breaks=(), max_run=99):
    """A surface over pixel columns c0..c1-1 and rows r0..r1-1, one face per run of pixels in a
    row that share a material (slot_of(index) -> slot, or None to leave a hole). Heights come
    from zfunc(x, y) at the corners; `breaks` are column edges a run may not cross (creases)."""
    for r in range(r0, r1):
        c = c0
        while c < c1:
            idx = grid.at(c, r)
            slot = None if idx in skip else slot_of(idx)
            if slot is None:
                c += 1
                continue
            e = c + 1
            while e < c1 and e not in breaks and e - c < max_run:
                j = grid.at(e, r)
                if j in skip or slot_of(j) != slot:
                    break
                e += 1
            xs, ys = (grid.ex(c), grid.ex(e)), (grid.ey(r + 1), grid.ey(r))
            vs = [bm.verts.new((x, y, zfunc(x, y))) for x, y in
                  ((xs[0], ys[0]), (xs[1], ys[0]), (xs[1], ys[1]), (xs[0], ys[1]))]
            f = bm.faces.new(vs)
            f.material_index = slot
            f.smooth = False
            c = e


def dome_z(cx, cy, rx, ry, h, z0=FLOOR, lift=0.018):
    """zfunc for painted(): the height of a dome() (power 2, flat 0) plus `lift`."""
    def z(x, y):
        d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
        return z0 + h * math.sqrt(max(0.0, 1 - d)) + lift
    return z


def grey_tones(mats, colors, tones=((1, 3), (4, 6), (7, 9), (10, 15)), finish=None):
    """slot_of for the stone: grey palette indices 1-15 binned into `tones` (each bin uses its
    most central index the sprite has); anything else gets the second tone."""
    finish = finish or mats.stone
    slots = []
    for lo, hi in tones:
        have = [i for i in range(lo, hi + 1) if str(i) in colors]
        if not have:
            slots.append(None)
            continue
        mid = (lo + hi) / 2
        slots.append(finish(min(have, key=lambda i: abs(i - mid))))
    fallback = next(s for s in (slots[1], slots[2], slots[0], slots[3]) if s is not None)
    slots = [s if s is not None else fallback for s in slots]

    def slot_of(idx):
        for (lo, hi), s in zip(tones, slots):
            if lo <= idx <= hi:
                return s
        return fallback
    return slot_of


def floor(bm, grid, mats, colors, rect=None, top=FLOOR, skirt_mat=None):
    """The stone floor plate: a block from z = 0 to `top` over pixel rect (c0, r0, c1, r1)
    (default the whole tile), its top painted in grey tones from the sprite."""
    c0, r0, c1, r1 = rect or (0, 0, grid.w, grid.h)
    slot_of = grey_tones(mats, colors)
    if skirt_mat is None:
        skirt_mat = slot_of(4)
    n = len(bm.faces)
    box(bm, grid.ex(c0), grid.ey(r1), grid.ex(c1), grid.ey(r0), 0.0, top - 0.002, mat=skirt_mat)
    painted(bm, grid, c0, r0, c1, r1, lambda x, y: top, slot_of)
    return n


# --- object, export, preview --------------------------------------------------------------------

def finish(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth flag."""
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats.list:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def run(name, build, file):
    """Single tile: build(sprite) returns [(model_name, objects, sprites)]; export each and, with
    -- --preview <png>, preview each (the first at <png>, others beside it as <model>.png)."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        for i, (model, objects, sprites) in enumerate(models):
            frame_idx = sprites[0]["frames"][0]
            frame = next(f for f in sprite["frames"] if f["index"] == frame_idx)
            ref = root / "reference" / "models" / name / frame["image"]
            path = out if i == 0 else out.parent / f"{model}.png"
            common.render_preview(objects, str(path), ref, size=frame["size"])
    return sprite


def write_png(path, rows):
    """rows: list of lists of (r, g, b, a) floats 0-1, top row first."""
    import numpy as np
    h, w = len(rows), len(rows[0])
    img = bpy.data.images.new("b073_png", w, h, alpha=True)
    img.pixels[:] = np.array(rows[::-1], dtype=np.float32).ravel()
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def run_assembly(asm_name, pieces, build, file, cols, rows_, frames=None):
    """Several 2x2 pieces laid out cols x rows_ (pieces: list of rows of piece names or None,
    top row first) built as one model and cut apart. build(sprite, grid) builds the whole in the
    grid's coordinates (Grid(24*cols, 28*rows_) centred on the origin) and returns
    (object, extra) where extra is a list of more (model, objects, sprites) to export as is.
    frames: optional {piece: frame position} for the composite preview."""
    root = common.repo_root(file)
    names = [p for row_ in pieces for p in row_ if p]
    colors = merged_colors(root, names)
    w, h = 24 * cols, 28 * rows_
    comp = [[-1] * w for _ in range(h)]
    comp_rgb = [[(0, 0, 0, 0)] * w for _ in range(h)]
    for ri, row_ in enumerate(pieces):
        for ci, n in enumerate(row_):
            if not n:
                continue
            data = common.load_sprite(root, n)
            fr = data["frames"][(frames or {}).get(n, 0)]
            for r, line in enumerate(fr["pixels"]):
                for c, v in enumerate(line):
                    if v >= 0:
                        comp[ri * 28 + r][ci * 24 + c] = v
                        comp_rgb[ri * 28 + r][ci * 24 + c] = (*(ch / 255 for ch in data["colors"][str(v)]), 1.0)
    sprite = {"name": asm_name, "colors": colors, "pixels": comp}
    grid = Grid(w, h, comp)
    obj, extra = build(sprite, grid)
    layout = []
    for ri, row_ in enumerate(pieces):
        for ci, n in enumerate(row_):
            if n:
                layout.append((n, (ci * 24 + 12 - w / 2), (ri * 28 + 14 - h / 2)))
    cut = common.split_assembly(obj, layout)
    for n in names:
        common.export_sprite_model(root, [cut[n]], f"enemies/{n}", common.load_sprite(root, n)["sprites"])
    for model, objects, sprites in extra:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        side = max(w, h * 24 / 28)
        sw, sh = int(round(side)), int(round(side * 28 / 24))
        canvas = [[(0, 0, 0, 0)] * sw for _ in range(sh)]
        oy, ox = (sh - h) // 2, (sw - w) // 2
        for r in range(h):
            for c in range(w):
                canvas[oy + r][ox + c] = comp_rgb[r][c]
        ref = Path(tempfile.mkdtemp()) / "asm.png"
        write_png(ref, canvas)
        common.render_preview([obj], str(out), str(ref), size=sw / 12, view_px=480)
        for n in names:
            data = common.load_sprite(root, n)
            img = root / "reference" / "models" / n / data["frames"][0]["image"]
            common.render_preview([cut[n]], str(out.parent / f"{n}.png"), img, size=2)
        for model, objects, sprites in extra:
            base = model.split("-f")[0]
            data = common.load_sprite(root, base)
            fr = next(f for f in data["frames"] if f["index"] == sprites[0]["frames"][0])
            img = root / "reference" / "models" / base / fr["image"]
            common.render_preview(objects, str(out.parent / f"{model}.png"), img, size=2)
    obj.hide_render = True
    return cut
