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
