"""Helpers shared by batch b010's model scripts (build-models.sh skips lib_ modules).

- Grid coordinates (pixel centres and edges of a w x h px grid, origin at its centre).
- Assembly grids: several 2x2 pieces' pixels placed side by side in one grid, and a PNG of it
  for the preview.
- fire_body: a billowing mass of fire traced row by row from a sprite grid, as nested glowing
  shells (red outside, then orange, yellow and a white-hot core), each a loft down the sprite.
- to_object: like common.mesh_object, but keeps each face's own smooth flag.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402


def gx(c, w=24):
    """Column c (pixel centre; fractions allowed) of a w px wide grid to Blender X."""
    return (c + 0.5 - w / 2) / 12


def gy(r, h=28):
    """Row r (pixel centre) of an h px tall grid to Blender Y: sprite up is +Y."""
    return (h / 2 - (r + 0.5)) / 12


# --- assemblies --------------------------------------------------------------------------------

def assembly_grid(root, pieces):
    """Place pieces side by side. pieces: list of (name, cx, cy) screen centres. Returns
    (grid, colors, (cx0, cy0), w, h): grid[r][c] is a palette index or -1, (cx0, cy0) the screen
    point at the grid's centre, colors merged from every piece."""
    xs = [cx for _, cx, _ in pieces]
    ys = [cy for _, _, cy in pieces]
    left, top = min(xs) - 12, min(ys) - 14
    w, h = max(xs) + 12 - left, max(ys) + 14 - top
    grid = [[-1] * w for _ in range(h)]
    colors = {}
    for name, cx, cy in pieces:
        data = common.load_sprite(root, name)
        colors.update(data["colors"])
        x0, y0 = cx - 12 - left, cy - 14 - top
        for r, line in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(line):
                if v >= 0:
                    grid[y0 + r][x0 + c] = v
    return grid, colors, (left + w / 2, top + h / 2), w, h


def grid_png(grid, colors, out, pad_w=None, pad_h=None):
    """Write a grid of palette indices as a PNG (1 px per sprite px), centred in pad_w x pad_h."""
    h, w = len(grid), len(grid[0])
    pw, ph = pad_w or w, pad_h or h
    x0, y0 = (pw - w) // 2, (ph - h) // 2
    pixels = [0.0] * (pw * ph * 4)
    for r in range(h):
        for c in range(w):
            v = grid[r][c]
            if v < 0:
                continue
            rgb = colors[str(v)]
            i = ((ph - 1 - (y0 + r)) * pw + x0 + c) * 4  # Blender images are bottom-up
            pixels[i:i + 4] = [rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1.0]
    img = bpy.data.images.new("b010_grid", pw, ph, alpha=True)
    img.pixels[:] = pixels
    img.filepath_raw = str(out)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return out


# --- fire --------------------------------------------------------------------------------------

def row_run(line, t, gap=2):
    """The longest run of pixels with index >= t in a row (gaps of up to `gap` pixels bridged),
    as (first, last) column, or None."""
    runs = []
    for c, v in enumerate(line):
        if v >= t:
            if runs and c - runs[-1][1] - 1 <= gap:
                runs[-1][1] = c
            else:
                runs.append([c, c])
    if not runs:
        return None
    return tuple(max(runs, key=lambda r: r[1] - r[0]))


def _ring(cx, y, w, h, z, sides, wobble, phase):
    pts = []
    for i in range(sides):
        a = 2 * math.pi * (i + 0.5) / sides
        ca, sa = math.cos(a), math.sin(a)
        # A squarish section (a superellipse), so the shell keeps its height out towards its
        # edges and each inner shell rises through the one around it close to its own outline.
        sx = math.copysign(abs(ca) ** 0.5, ca)
        sz = math.copysign(abs(sa) ** 0.5, sa)
        bump = 1.0
        if sa > 0:
            bump += wobble * math.sin(9.0 * (cx + w * sx) + 7.0 * y + phase) * sa
        pts.append((cx + w * sx, y, z + h * sz * bump))
    return pts


def fire_body(bm, grid, shells, sides=16, open_top=False, open_bottom=False, taper_rows=6.0,
              wobble=0.12, min_run=2):
    """Nested fire shells traced from `grid` (rows of palette indices, -1 transparent, centred on
    the origin). shells: list of (threshold, half_height, mat_index), outermost first; each shell
    covers, row by row, the longest run of pixels with index >= threshold and is a loft of
    rounded sections down the sprite. A shell is lower where it is narrow and near its top end
    (over `taper_rows`), so the fire billows. open_top/open_bottom: the grid's first/last row is
    a cut (the fire goes on past it), so the shell ends there flat instead of rounding off."""
    h_px, w_px = len(grid), len(grid[0])
    top = next(r for r, line in enumerate(grid) if any(v >= 0 for v in line))
    for k, (t, half_h, mat) in enumerate(shells):
        runs = [row_run(line, t) for line in grid]
        runs = [r if r and r[1] - r[0] + 1 >= min_run else None for r in runs]
        if k > 0:  # inner shells: soften the row-to-row jumps a little
            soft = []
            for r, run in enumerate(runs):
                if run is None:
                    soft.append(None)
                    continue
                near = [runs[q] for q in (r - 1, r + 1) if 0 <= q < h_px and runs[q] is not None]
                a = (2 * run[0] + sum(n[0] for n in near)) / (2 + len(near))
                b = (2 * run[1] + sum(n[1] for n in near)) / (2 + len(near))
                soft.append((a, b))
            runs = soft
        r = 0
        while r < h_px:
            if runs[r] is None:
                r += 1
                continue
            r0 = r
            while r < h_px and runs[r] is not None:
                r += 1
            r1 = r - 1  # rows r0..r1 have a run
            sections = []
            for rr in range(r0, r1 + 1):
                a, b = runs[rr]
                left, right = gx(a - 0.5, w_px), gx(b + 0.5, w_px)
                w = (right - left) / 2
                hh = min(half_h, 0.28 * w + 0.02)
                if not open_top:  # the whole body rounds off towards its top
                    hh *= math.sqrt(min(1.0, (rr - top + 1) / taper_rows))
                sections.append(((left + right) / 2, gy(rr, h_px), w, hh))
            # Ends: flat at a cut edge of the grid, otherwise rounded off half a pixel out.
            cx, y, w, hh = sections[0]
            if r0 == 0 and open_top:
                sections.insert(0, (cx, gy(-0.5, h_px), w, hh))
            else:
                sections.insert(0, (cx, y + 0.5 / 12, w * 0.75, hh * 0.45))
            cx, y, w, hh = sections[-1]
            if r1 == h_px - 1 and open_bottom:
                sections.append((cx, gy(h_px - 0.5, h_px), w, hh))
            else:
                sections.append((cx, y - 0.5 / 12, w * 0.75, hh * 0.45))
            rings = [[bm.verts.new(p) for p in _ring(cx, y, w, hh, 0.0, sides, wobble, 0.0)]
                     for cx, y, w, hh in sections]
            faces = []
            for q0, q1 in zip(rings, rings[1:]):
                for i in range(sides):
                    j = (i + 1) % sides
                    faces.append(bm.faces.new((q0[i], q0[j], q1[j], q1[i])))
            faces.append(bm.faces.new(list(reversed(rings[0]))))
            faces.append(bm.faces.new(rings[-1]))
            for f in faces:
                f.material_index = mat
                f.smooth = True


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


def fire_assembly(root, file, name, pieces, shells_spec, **fire_kw):
    """Build, split and export a fire assembly (and its previews, with -- --preview <png>).
    pieces: [(model, cx, cy)]; shells_spec: [(threshold, half_height, palette index, emission)]."""
    grid, colors, (cx0, cy0), w, h = assembly_grid(root, pieces)
    sprite = {"name": name, "colors": colors}
    coll = common.reset_collection(name)
    mats, shells = [], []
    for i, (t, half_h, index, glow) in enumerate(shells_spec):
        mats.append(common.palette_material(sprite, index, name, metallic=0.0, roughness=0.6,
                                            emission_strength=glow))
        shells.append((t, half_h, i))
    bm = bmesh.new()
    fire_body(bm, grid, shells, **fire_kw)
    obj = to_object(name, bm, mats, coll)
    layout = [(m, cx - cx0, cy - cy0) for m, cx, cy in pieces]
    parts = common.split_assembly(obj, layout)
    for m, _, _ in pieces:
        data = common.load_sprite(root, m)
        common.export_sprite_model(root, [parts[m]], f"enemies/{m}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        size = math.ceil(max(w / 24, h / 28)) * 2
        ref = grid_png(grid, colors, Path(tempfile.mkdtemp()) / "assembly.png", size * 12, size * 14)
        common.render_preview([obj], str(out), str(ref), size=size, view_px=480)
        for m, _, _ in pieces:
            data = common.load_sprite(root, m)
            img = root / "reference" / "models" / m / data["frames"][0]["image"]
            common.render_preview([parts[m]], str(out.parent / f"{m}.png"), img, size=2)
    return obj, parts


# --- hard-surface parts ------------------------------------------------------------------------

def ex(c, w=24):
    """The left edge of column c of a w px wide grid as Blender X."""
    return (c - w / 2) / 12


def ey(r, h=28):
    """The top edge of row r of an h px tall grid as Blender Y."""
    return (h / 2 - r) / 12


def _faces(bm, faces, mat, smooth):
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def box(bm, c0, r0, c1, r1, z0, z1, mat=0, w=24, h=28):
    """A box over pixel edges columns c0..c1, rows r0..r1 (fractions allowed), z0..z1."""
    x0, x1, y1, y0 = ex(c0, w), ex(c1, w), ey(r0, h), ey(r1, h)
    v = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    faces = [bm.faces.new(q) for q in ((v[3], v[2], v[1], v[0]), (v[4], v[5], v[6], v[7]),
                                       (v[0], v[1], v[5], v[4]), (v[1], v[2], v[6], v[5]),
                                       (v[2], v[3], v[7], v[6]), (v[3], v[0], v[4], v[7]))]
    _faces(bm, faces, mat, False)


def extrude_y(bm, profile, y0, y1, mat=0, smooth=False):
    """A prism along Y from y0 to y1 (Blender units, y0 < y1) with a closed (x, z) profile."""
    a = [bm.verts.new((x, y0, z)) for x, z in profile]
    b = [bm.verts.new((x, y1, z)) for x, z in profile]
    n = len(profile)
    faces = [bm.faces.new(a), bm.faces.new(list(reversed(b)))]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    _faces(bm, faces, mat, smooth)


def prism(bm, top, z0, mat=0, smooth=False):
    """A prism whose top face has the given (x, y, z) corners (counter-clockwise from above, z may
    vary: a sloped top) and whose bottom face is flat at z0."""
    t = [bm.verts.new(p) for p in top]
    b = [bm.verts.new((x, y, z0)) for x, y, _ in top]
    n = len(top)
    faces = [bm.faces.new(t), bm.faces.new(list(reversed(b)))]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((b[i], b[j], t[j], t[i])))
    _faces(bm, faces, mat, smooth)


def rod_y(bm, x, sections, sides=8, mat=0, smooth=True):
    """A loft down the sprite at Blender X = x: sections are (y, half_width, half_height, z) in
    units; a section of zero size is a point."""
    rings = []
    for y, w, hh, z in sections:
        if w == 0 and hh == 0:
            rings.append([bm.verts.new((x, y, z))])
            continue
        rings.append([bm.verts.new((x + w * math.cos(2 * math.pi * (i + 0.5) / sides), y,
                                    z + hh * math.sin(2 * math.pi * (i + 0.5) / sides)))
                      for i in range(sides)])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                break
            if len(r0) == 1:
                faces.append(bm.faces.new((r0[0], r1[j], r1[i])))
            elif len(r1) == 1:
                faces.append(bm.faces.new((r0[i], r0[j], r1[0])))
            else:
                faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    if len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
    _faces(bm, faces, mat, smooth)


def stud(bm, x, y, z, r, hz, mat=0, sides=8):
    """A small dome (rivet, lamp) of radius r and height hz standing on z."""
    ring = [bm.verts.new((x + r * math.cos(2 * math.pi * i / sides), y + r * math.sin(2 * math.pi * i / sides), z))
            for i in range(sides)]
    mid = [bm.verts.new((x + 0.6 * r * math.cos(2 * math.pi * i / sides),
                         y + 0.6 * r * math.sin(2 * math.pi * i / sides), z + 0.8 * hz)) for i in range(sides)]
    tip = bm.verts.new((x, y, z + hz))
    faces = [bm.faces.new(list(reversed(ring)))]
    for i in range(sides):
        j = (i + 1) % sides
        faces.append(bm.faces.new((ring[i], ring[j], mid[j], mid[i])))
        faces.append(bm.faces.new((mid[i], mid[j], tip)))
    _faces(bm, faces, mat, True)
