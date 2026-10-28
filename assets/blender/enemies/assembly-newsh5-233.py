"""Brain (newsh5.shp frames 233, 235, 237, 239: an assembly of four pieces): a 3D version of its sprites.

Seen in episode 4 (level 22). Four 2x2 enemies side by side make one 96x28 px brain: two
hemispheres split by a dark fissure down the middle, their surface packed with pink folds (gyri)
between dark grooves, brightest on the inner halves. The top is a height field with a vertex at
every pixel corner, each pixel a face in its own palette colour, so the top view is the sprite:
each hemisphere is a rounded body (a 2 px ground that runs out to the outline, rising from
the outline and the fissure to about 5.5 px in the middle) with the folds raised on it as
rounded tubes from the sprite's shading (gyri up to 4.5 px above the sulci between them, also on
the darker shadowed side), about 9-10 px at the highest, and the fissure cut down below the base.
A dark skirt and underside close it.

The whole brain is built once in assembly coordinates and cut into the four pieces with
common.split_assembly. One frame each.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-233.py [-- --preview out.png]
(the preview is the whole brain; each piece also gets <piece>.png next to it).
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b029 as lib  # noqa: E402

PX = 1 / 12

NAME = "assembly-newsh5-233"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-233", "newsh5-235", "newsh5-237", "newsh5-239"]
FISSURE = 47  # column of the dark fissure between the hemispheres


# Heights in sprite px (1 px = 1/12 unit).
GROUND = 2.0  # every hemisphere pixel stands at least this high, right out to the outline
DOME = 3.5  # each hemisphere's rounded body at its middle
ROUND = 9.0  # how far in from the outline (px) the body takes to reach full height
RELIEF = 4.5  # the folds: brightest gyrus tops this far above the darkest grooves
LEVEL_MAX = 12.0  # shading level (ramp 64-79 -> 0-15) that counts as a full-height fold
LOCAL = 4  # window (px either way) for the folds' relative shading
LOCAL_MIX = 0.55  # how much of the relief comes from the relative shading
FISSURE_Z = -1.0  # floor of the fissure
EDGE = 0.75  # outline height, as a share of the pixels' just inside it (a rounded, not feathered, edge)
BASE_Z = -1.7  # underside


def fissure(pixels):
    """The fissure's pixels: the dark (outline-black and darkest-ramp) pixels connected to its
    middle column, within a few columns of it."""
    h, w = len(pixels), len(pixels[0])
    todo = [(r, FISSURE) for r in range(h) if pixels[r][FISSURE] >= 0]
    seen = set(todo)
    while todo:
        r, c = todo.pop()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            n = (r + dr, c + dc)
            if (n not in seen and 0 <= n[0] < h and abs(n[1] - FISSURE) <= 1
                    and pixels[n[0]][n[1]] in (1, 64)):
                seen.add(n)
                todo.append(n)
    return seen


def heights(pixels, gap):
    """Height (px) of every sprite pixel: a rounded body per hemisphere (round to the outline and
    to the fissure, from each pixel's distance to them) plus the folds' relief, read from the
    sprite's shading (bright gyri high, dark sulci cut down between them)."""
    h, w = len(pixels), len(pixels[0])
    inside = lambda r, c: 0 <= r < h and 0 <= c < w and pixels[r][c] >= 0 and (r, c) not in gap  # noqa: E731
    edge = [(r, c) for r in range(-1, h + 1) for c in range(-1, w + 1) if not inside(r, c)
            and any(inside(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1))]
    _, sm = lib._levels(pixels)
    # Soften the shading once more so the folds come out as rounded tubes, not pixel steps.
    soft = [[None] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if sm[r][c] is None:
                continue
            near = [sm[r + dr][c + dc] for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                    if 0 <= r + dr < h and 0 <= c + dc < w and sm[r + dr][c + dc] is not None]
            soft[r][c] = 0.5 * sm[r][c] + 0.5 * sum(near) / len(near)
    z = {}
    for r in range(h):
        for c in range(w):
            if not inside(r, c):
                continue
            d = min(math.hypot(r - er, c - ec) for er, ec in edge) - 0.5
            t = min(d / ROUND, 1.0)
            body = DOME * max(1 - (1 - t) ** 2, 0.0) ** 0.6
            # The folds on the shadowed (right and outer) side are drawn darker but stand as tall:
            # mix the absolute shading with the shading relative to the folds around it.
            near = [soft[r + dr][c + dc] for dr in range(-LOCAL, LOCAL + 1) for dc in range(-LOCAL, LOCAL + 1)
                    if 0 <= r + dr < h and 0 <= c + dc < w and soft[r + dr][c + dc] is not None]
            lo, hi = min(near), max(near)
            rel = (soft[r][c] - lo) / max(hi - lo, 3.0)
            lv = (1 - LOCAL_MIX) * min(max(soft[r][c], 0.0), LEVEL_MAX) / LEVEL_MAX + LOCAL_MIX * rel
            z[r, c] = GROUND + body + RELIEF * lv
    return z


def build(colors, pixels, grid):
    coll = common.reset_collection(NAME)
    sprite = {"name": NAME, "colors": colors}
    used = sorted({v for line in pixels for v in line if v >= 0})
    # One material per palette index the sprite uses, so the top view is the sprite's own colours.
    # Matte: the brain is flesh, not metal (a glossy finish turns it grey from above).
    mats = [common.palette_material(sprite, i, "ns5b233", metallic=0.0,
                                    roughness=1.0) for i in used]
    for m in mats:
        # The viewport shading (this session's previews) reads these, not the node tree: matte too.
        m.roughness = 1.0
        m.metallic = 0.0
        m.specular_intensity = 0.0
    slot = {i: k for k, i in enumerate(used)}
    h, w = len(pixels), len(pixels[0])
    mask = lambda r, c: 0 <= r < h and 0 <= c < w and pixels[r][c] >= 0  # noqa: E731
    gap = fissure(pixels)
    z = heights(pixels, gap)

    bm = bmesh.new()
    corner = lambda i, j: ((j - w / 2) / 12, (h / 2 - i) / 12)  # noqa: E731
    top = {}

    def top_vert(i, j):
        if (i, j) not in top:
            adj = [(i - 1, j - 1), (i - 1, j), (i, j - 1), (i, j)]
            if not all(mask(r, c) for r, c in adj):
                # On the outline: the rounded body turns down into the skirt.
                zs = [z[a] for a in adj if a in z]
                zz = EDGE * sum(zs) / len(zs) if zs else 0.0
            elif all(a in gap for a in adj):
                zz = FISSURE_Z - 0.5  # the floor of a wider stretch of fissure: a shallow V, above the base
            elif any(a in gap for a in adj):
                zz = FISSURE_Z
            else:
                zz = sum(z[a] for a in adj) / 4
            x, y = corner(i, j)
            top[i, j] = bm.verts.new((x, y, zz * PX))
        return top[i, j]

    bottom = {}

    def bottom_vert(i, j):
        if (i, j) not in bottom:
            x, y = corner(i, j)
            bottom[i, j] = bm.verts.new((x, y, BASE_Z * PX))
        return bottom[i, j]

    def face(verts, mat, out, smooth):
        f = bm.faces.new(verts)
        f.material_index = mat
        f.smooth = smooth
        f.normal_update()
        if f.normal.dot(Vector(out)) < 0:
            f.normal_flip()
        return f

    for r in range(h):
        for c in range(w):
            if not mask(r, c):
                continue
            v = pixels[r][c]
            face([top_vert(r + 1, c), top_vert(r + 1, c + 1), top_vert(r, c + 1), top_vert(r, c)],
                 slot[v], (0, 0, 1), (r, c) not in gap)
            # Skirt down to the underside wherever the pixel is on the outline.
            for dr, dc, a, b in ((-1, 0, (r, c), (r, c + 1)), (1, 0, (r + 1, c), (r + 1, c + 1)),
                                 (0, -1, (r, c), (r + 1, c)), (0, 1, (r, c + 1), (r + 1, c + 1))):
                if not mask(r + dr, c + dc):
                    face([top_vert(*a), top_vert(*b), bottom_vert(*b), bottom_vert(*a)],
                         slot[64], (dc, -dr, 0), False)
    # Underside: one strip per run of pixels in a row.
    for r in range(h):
        c = 0
        while c < w:
            if not mask(r, c):
                c += 1
                continue
            c1 = c
            while c1 + 1 < w and mask(r, c1 + 1):
                c1 += 1
            face([bottom_vert(r, c), bottom_vert(r, c1 + 1), bottom_vert(r + 1, c1 + 1), bottom_vert(r + 1, c)],
                 slot[64], (0, 0, -1), False)
            c = c1 + 1

    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj


def main():
    pixels, colors, w, h, (sx0, sy0), layout = lib.assembly_pixels(ROOT, PIECES)
    grid = lib.Grid(w, h)
    obj = build(colors, pixels, grid)
    # Screen position of the grid's centre (the Blender origin).
    cx0, cy0 = sx0 + w / 2, sy0 + h / 2
    pieces = common.split_assembly(obj, [(n, layout[n][0] - cx0, layout[n][1] - cy0) for n in PIECES])
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.write_png(Path(tempfile.mkdtemp()) / "assembly.png", pixels, colors)
        common.render_preview([obj], str(out), str(ref), size=(w, h), view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
