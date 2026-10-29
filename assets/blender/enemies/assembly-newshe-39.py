"""Rock outcrop (newshe.shp frames 1, 3, 5, 39, 41, 43; an assembly of 6 pieces): a 3D version of
its sprites.

Seen in episode 1 (levels 1.28 and 1.3) and episode 3 (3.17). Six 2x2 ground enemies side by side
(three across, two down; sprite.json `assemblyLayout`) make one 72 x 56 px heap of grey boulders on
brown dirt, lit from the top left: a big flat-topped block at the back (upper right) with a bright
edge down its left side, smaller boulders to its left, splintered shards below it, and a dark
shadow on the ground in front of them all.

The heap is built once in assembly coordinates: each boulder is the convex hull of its footprint
and its raised top (so it has flat, angular faces), split into small facets that take the colour
of the sprite pixel under them (the sprite's own shading of each face). It is cut into the six
pieces with common.split_assembly, and each piece gets a flat patch of dirt and shadow under it,
painted from its sprite in 2 x 2 px cells.

Run: blender --background --python assets/blender/enemies/assembly-newshe-39.py [-- --preview out.png]
(the preview is the whole heap; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b134 as lib  # noqa: E402

NAME = "assembly-newshe-39"
ROOT = common.repo_root(__file__)
PIECES = ["newshe-1", "newshe-3", "newshe-5", "newshe-39", "newshe-41", "newshe-43"]
# Assembly pixel (0, 0) is the top-left pixel of newshe-1 (screen 224 - 12, -18 - 14); the heap is
# 72 x 56 px and its centre (screen 248, -4) is the Blender origin.
SX0, SY0 = 212, -32
CX0, CY0 = 248, -4

ROCK = set(range(4, 12))  # the grey ramp of the boulders
CREVICE = {2, 3}
STEP = 3  # px between the cuts that let the boulders' facets take the sprite's shading


def boulders(bm, grid):
    """Each boulder: footprint on the ground [(col, row)], raised top [(col, row, z)], optional peak.
    Columns and rows are assembly pixels (fractions are pixel edges and centres)."""
    faces = []
    add = lambda *a, **k: faces.extend(lib.rock(bm, grid, *a, **k))  # noqa: E731
    block = lambda *a, **k: faces.extend(lib.block_rock(bm, grid, *a, **k))  # noqa: E731

    # Low rubble under the heap, filling the gaps between the boulders (the dark rock and crevices
    # between them in the sprite): one mound on the left, one under and in front of the big block.
    block([(0.5, 23), (5, 16), (14, 11.5), (26, 11.5), (31, 14), (31, 32), (20, 33), (8, 31), (1, 29.5)],
          0.2, inset=5.0)
    block([(28, 16), (64, 16), (64.5, 22), (60, 30), (50, 35), (40, 41.5), (33, 42), (28, 33)],
          0.24, inset=6.0)

    # The big block at the back: a flat top (cols 30-59, rows 1-13) edged by the bright ridge that
    # runs from column 29, row 5 down to column 41, row 14; a dark face sloping off to the left, a
    # darker face on the right (cols 58-65) and a mid-grey face in front (rows 12-20). It is the
    # tallest part of the heap (its shadow runs 10-15 px down the screen), a columnar block split
    # down the middle (col 45) by a fissure, as the concept draws it: two hulls whose tops stop
    # short of the split, leaving a V-shaped groove, the right half a little lower.
    S = 45.5  # the fissure
    add([(27.5, 4.5), (32, 2.5), (38, 1), (44, 0), (S + 0.8, 0), (S + 0.8, 20.2), (43, 20),
         (36, 18.5), (30, 16), (27.5, 12)],
        [(30, 5.2, 1.0), (34, 2.6, 1.1), (43, 1.4, 1.15), (S - 1.0, 1.5, 1.14), (S - 1.0, 13.4, 1.04),
         (40, 13.6, 1.0), (31, 9.5, 0.92), (29.2, 12.5, 0.55), (36.5, 17.2, 0.55)])
    add([(S - 0.8, 0), (50, 0.8), (56, 3), (62, 5.5), (65.5, 9), (65.5, 16), (62, 20), (52, 20.5),
         (S - 0.8, 20.2)],
        [(S + 1.0, 1.8, 1.06), (49, 1.8, 1.08), (56, 4, 1.0), (59, 6.8, 0.92), (59.5, 11, 0.84),
         (52, 12.5, 0.92), (S + 1.0, 13.4, 0.98), (64, 9.5, 0.5), (60.5, 17.5, 0.5),
         (52, 18.6, 0.6)])

    # Boulder in front of the block's right half (cols 42-61, rows 15-31), its edge lit at col 44.
    block([(42, 18), (47, 15), (58, 15.5), (61, 19), (58, 23.5), (53, 28.5), (47.5, 31), (44, 29),
           (42, 24)], 0.7, inset=2.5, dr=-1.0)
    # Small splinters to its right (cols 50-61, rows 18-34).
    block([(51, 27), (55.5, 19), (60.5, 18.5), (60.5, 21.5), (57, 29), (53, 34), (50, 33)],
          0.3, inset=1.5)
    # Upper-left boulder (cols 9-25, rows 11-19).
    block([(9, 16.5), (12.5, 12.5), (16, 11), (23, 11), (25.5, 13.5), (25, 18.5), (17, 19.5),
           (11, 19.5)], 0.6, inset=2.0, dr=-0.5)
    # Bright boulder below it (cols 15-27, rows 17-31), the brightest of the small ones.
    block([(15, 19.5), (19, 17), (25, 17), (27.5, 21), (27, 28.5), (23, 31.5), (17.5, 30.5),
           (15, 25.5)], 0.74, inset=2.0, dr=-1.0)
    # Grey boulder between it and the big block (cols 23-32, rows 12-31).
    block([(24, 12.5), (29, 12.5), (32.5, 16), (32.5, 29), (29.5, 32), (25.5, 30.5), (23.5, 18)],
          0.68, inset=2.0, dr=-1.0)
    # Left boulder (cols 0-14, rows 16-30), its left edge catching the light (col 3, row 21).
    block([(0.5, 21), (3, 17.5), (6, 16), (11, 16), (14.5, 19), (14.5, 26), (12, 29.5), (6, 30.5),
           (2, 29.5), (0.2, 25)], 0.62, inset=2.5, dr=-1.0)

    # Shards below the block: a low slab (cols 29-38, rows 19-30) and two tall splinters pointing
    # down the screen (cols 29-37, rows 29-42, and cols 37-45, rows 20-38), and a chip at the foot.
    block([(29, 20.5), (37.5, 19), (38.5, 28), (36, 30.5), (29.5, 30)], 0.42, inset=1.5)
    block([(28.5, 29.5), (36.5, 28.5), (38.5, 33), (37, 39.5), (34.5, 42), (31, 37.5), (28.5, 33)],
          0.52, inset=1.5, dr=-1.0)
    block([(37.5, 21.5), (44, 20), (45.5, 24), (43, 31), (40, 38), (37.5, 34)], 0.5, inset=1.5,
          dr=-1.0)
    block([(45, 33), (48, 29.5), (51.5, 30), (51, 34), (47, 36.5)], 0.18, inset=1.0)
    return faces


def build(colors, grid):
    coll = common.reset_collection(NAME)
    mats = lib.Mats("nshe39", colors)

    def rock_slot(idx, face):
        if face.normal.z < -0.3:
            return mats(3)
        if idx in ROCK:
            return mats(idx, metallic=0.15, roughness=0.75)
        if idx in CREVICE:
            return mats(idx, metallic=0.1, roughness=0.9)
        return mats(4, metallic=0.15, roughness=0.75)  # side faces over the ground and shadow

    bm = bmesh.new()
    boulders(bm, grid)
    lib.slice_grid(bm, grid, step=STEP)
    bm.normal_update()
    faces = bm.faces[:]
    lib.paint(faces, grid, rock_slot)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        f.smooth = False
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats.list:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj, mats


def add_ground(piece, grid, mats, ox, oy):
    """Lay the patch of ground under piece (top-left assembly pixel ox, oy) into its mesh."""
    def slot(idx):
        if idx == -2:
            return mats(17, roughness=0.95, metallic=0.0)
        if idx in ROCK or idx in CREVICE:
            return mats(idx if idx in CREVICE else 3, metallic=0.1, roughness=0.9)
        return mats(idx, metallic=0.0, roughness=0.95)

    bm = bmesh.new()
    bm.from_mesh(piece.data)
    lib.ground_tile(bm, grid, ox, oy, slot)
    piece.data.materials.clear()
    for m in mats.list:
        piece.data.materials.append(m)
    bm.to_mesh(piece.data)
    bm.free()


def main():
    first = common.load_sprite(ROOT, PIECES[0])
    layout = [(e["model"], e["cx"], e["cy"]) for e in first["assemblyLayout"]]
    corners = [(n, cx - 12 - SX0, cy - 14 - SY0) for n, cx, cy in layout]
    pixels, w, h, colors = lib.assembly_pixels(ROOT, corners)
    grid = lib.Grid(w, h, pixels)
    obj, mats = build(colors, grid)
    pieces = common.split_assembly(obj, [(n, cx - CX0, cy - CY0) for n, cx, cy in layout])
    for name, ox, oy in corners:
        add_ground(pieces[name], grid, mats, ox, oy)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        piece = pieces[name]
        print(f"{name}: {len(piece.data.polygons)} faces")
        common.export_sprite_model(ROOT, [piece], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.pixels_png(pixels, colors, Path(tempfile.mkdtemp()) / "assembly.png", pad_to=(72, 84))
        # The whole heap, its pieces laid out in place, beside the composite sprite.
        whole = []
        for name, ox, oy in corners:
            p = pieces[name]
            p.location = ((ox + 12 - w / 2) / 12, (h / 2 - oy - 14) / 12, 0)
            whole.append(p)
        bpy.context.view_layer.update()
        common.render_preview(whole, str(out), ref, size=6, view_px=640)
        for p in whole:
            p.location = (0, 0, 0)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
