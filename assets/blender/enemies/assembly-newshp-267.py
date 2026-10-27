"""Brown pump tower on a stone plinth (newshp.shp, assembly of 5 pieces): a 3D version of its sprites.

Seen in episode 1 (level 1.5), 2 (2.8) and 3 (3.15). Five 2x2 ground enemies make one 48 x 84 px
structure (sprite.json `assemblyLayout`): a grey stone block (newshp-229, -231, -267, -269) with a
lighter raised plinth, a dark trench down its right side and a grille at the bottom right; on it
a blocky brown machine with gold plates, a gold box behind it, a dark lattice column running up
the screen to a golden onion-shaped tank of three stacked tiers (newshp-115, whose three frames
move the shine from tier to tier: bottom, middle, top; one model covers them, each tier with its
own material that brightens on its frame, animate_tank), and an arm with gold bands reaching down
the screen.

The whole structure is built once in assembly pixels (column 0, row 0 is the top-left corner of
newshp-115; the platform is rows 28-83), then cut into the five pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshp-267.py [-- --preview out.png]
(the preview is the whole structure; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b123 as lib  # noqa: E402

NAME = "assembly-newshp-267"
ROOT = common.repo_root(__file__)
PIECES = ["newshp-115", "newshp-229", "newshp-231", "newshp-267", "newshp-269"]
# Assembly pixel (0, 0) is screen (164, -32); the 48 x 84 px assembly's centre is screen (188, 10).
CX0, CY0 = 188, 10
G = lib.Grid(48, 84)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshp267"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.1, roughness=0.85),  # 0 rough stone
        pal(9, metallic=0.15, roughness=0.75),  # 1 light plinth
        pal(12, metallic=0.2, roughness=0.6),  # 2 plinth rim highlight
        pal(2, metallic=0.1, roughness=0.9),  # 3 dark trench / shadowed stone
        pal(7, metallic=0.2, roughness=0.7),  # 4 grille ribs
        pal(167, metallic=0.3, roughness=0.5),  # 5 brown machine
        pal(170, metallic=0.35, roughness=0.45),  # 6 light brown edges
        pal(164, metallic=0.3, roughness=0.55),  # 7 dark brown
        pal(162, metallic=0.3, roughness=0.6),  # 8 darkest brown (column, front faces)
        pal(23, metallic=0.35, roughness=0.35),  # 9 gold
        pal(25, metallic=0.35, roughness=0.3),  # 10 light gold
        pal(18, metallic=0.3, roughness=0.6),  # 11 dark brown seams
        pal(26, metallic=0.4, roughness=0.3),  # 12 tank gold
        pal(31, metallic=0.3, roughness=0.2),  # 13 tank shine
        pal(20, metallic=0.4, roughness=0.5),  # 14 tank dark bands
        pal(165, metallic=0.3, roughness=0.5),  # 15 column rungs
    ]
    (STONE, PLINTH, RIM, DARK, RIB, BROWN, LBROWN, DBROWN, DDBROWN, GOLD, LGOLD, SEAM,
     TANK, SHINE, TBAND, RUNG) = range(16)
    bm = bmesh.new()
    box, plate = (lambda *a, **k: lib.box(bm, G, *a, **k)), (lambda *a, **k: lib.plate(bm, G, *a, **k))

    # ---- stone platform (rows 28-83) ----
    box(0, 28.02, 48, 84, 0.0, 0.08, mat=STONE)
    # Raised light plinth the machine stands on, with a bright rim down its left side.
    plate([(4, 28.02), (41, 28.02), (41, 63), (45, 63), (45, 70), (4, 70)], 0.0, 0.14, mat=PLINTH)
    box(4, 28.02, 5, 70, 0.0, 0.17, mat=RIM)
    box(4, 69, 45, 70, 0.0, 0.155, mat=RIM)
    # Dark trench down the right of the plinth, and the shadowed stone beside and below the machine.
    box(41, 30, 45, 63, 0.0, 0.085, mat=DARK)
    plate([(19, 57), (34, 57), (34, 63), (33, 64), (19, 64)], 0.14, 0.15, mat=DARK)
    box(38, 44, 41, 63, 0.14, 0.15, mat=DARK)
    # Grille at the bottom right: a dark pit with ribs.
    box(20, 70, 41, 82, 0.0, 0.085, mat=DARK)
    for c in (24, 28, 32, 36, 40):
        box(c, 71, c + 1, 82, 0.0, 0.12, mat=RIB)
    # A few raised stone blocks round the edges.
    for c0, r0, c1, r1 in ((0, 28.02, 4, 36), (0, 41, 4, 56), (0, 71, 9, 76), (44, 71, 48, 76),
                           (45, 30, 48, 47), (45, 49, 48, 60)):
        lib.bevel_box(bm, G, c0, r0, c1, r1, 0.0, 0.11, 0.02, mat=STONE)

    # ---- the machine ----
    # Lower body (rows 44-56), split by a dark seam at columns 25-26, with a lit rounded left edge.
    lib.bevel_box(bm, G, 6, 44, 25, 57, 0.1, 0.42, 0.04, mat=BROWN)
    lib.bevel_box(bm, G, 26, 44, 39, 57, 0.1, 0.44, 0.04, mat=BROWN)
    box(25, 45, 26, 56, 0.1, 0.38, mat=SEAM)
    lib.loft_y(bm, G, 6.9, [(44.5, 0.0, 0.0, 0.3), (45.2, 1.0, 0.1, 0.3), (56.5, 1.0, 0.1, 0.3),
                            (57.0, 0.0, 0.0, 0.3)], sides=8, mat=LBROWN)
    # Lower-left extension (rows 56-63), darker and lower, its corner cut.
    plate([(6, 57), (13, 57), (13, 64), (10, 64), (6, 61)], 0.1, 0.34, mat=DBROWN)
    # Dark front step under the right half (rows 56-60).
    box(20, 57, 38, 60, 0.1, 0.26, mat=DDBROWN)
    # Gold plate on the lower right body (columns 31-35, rows 52-55).
    lib.bevel_box(bm, G, 31, 52, 36, 56, 0.4, 0.47, 0.015, mat=GOLD)

    # Upper block (rows 36-44, columns 24-40), taller, with a light top edge and a gold plate.
    box(26, 43, 41, 44, 0.1, 0.36, mat=SEAM)
    lib.bevel_box(bm, G, 24, 36, 40, 43, 0.1, 0.54, 0.04, mat=BROWN)
    box(24, 36, 40, 37, 0.1, 0.545, mat=LBROWN)
    lib.bevel_box(bm, G, 28, 37, 33, 43, 0.5, 0.58, 0.015, mat=GOLD)
    box(29, 38, 30, 42, 0.5, 0.59, mat=LGOLD)
    # Gold box behind it (rows 28-36, columns 24-34), lit on its left.
    lib.bevel_box(bm, G, 24, 28.02, 34, 36, 0.1, 0.5, 0.03, mat=GOLD)
    box(24, 28.02, 26, 36, 0.1, 0.505, mat=LGOLD)

    # Arm reaching down the screen (columns 11-19, rows 56-82): brown frame, gold bar, gold band.
    lib.bevel_box(bm, G, 11, 56, 20, 69, 0.1, 0.4, 0.03, mat=BROWN)
    box(11, 58, 12, 69, 0.1, 0.405, mat=LBROWN)
    lib.bevel_box(bm, G, 13, 57, 18, 68, 0.36, 0.45, 0.02, mat=GOLD)
    box(14, 58, 15, 67, 0.36, 0.455, mat=LGOLD)
    lib.bevel_box(bm, G, 11, 68, 20, 76, 0.1, 0.36, 0.03, mat=DBROWN)
    box(11, 68, 20, 70, 0.1, 0.37, mat=LBROWN)
    lib.bevel_box(bm, G, 11, 76, 20, 79, 0.1, 0.39, 0.03, mat=GOLD)
    box(11, 76, 20, 77, 0.1, 0.395, mat=LGOLD)
    lib.bevel_box(bm, G, 11, 79, 20, 82, 0.08, 0.3, 0.03, mat=DDBROWN)

    # Dark lattice column from the machine up the screen to the tank (columns 11-19, rows 27-57).
    lib.bevel_box(bm, G, 11, 28.02, 19, 57, 0.2, 0.6, 0.03, mat=DDBROWN)
    box(12, 28.02, 14, 57, 0.2, 0.61, mat=RUNG)
    for r in (31, 36, 39, 45, 50):
        box(11, r, 19, r + 1, 0.2, 0.615, mat=RUNG)

    # ---- the onion tank (newshp-115): three stacked golden tiers rising up the screen ----
    lib.ellipsoid(bm, G, 14.0, 22.6, 0.16, 9.6, 5.6, 0.3, mat=TANK, segments=20, rings=10, zmin=0.0)
    lib.ellipsoid(bm, G, 14.0, 14.6, 0.44, 7.6, 3.8, 0.22, mat=TANK, segments=18, rings=9)
    lib.ellipsoid(bm, G, 14.2, 7.6, 0.68, 5.6, 4.0, 0.21, mat=TANK, segments=16, rings=8)
    # Dark collars between the tiers and a shine on each.
    lib.ellipsoid(bm, G, 14.0, 17.8, 0.36, 6.6, 1.6, 0.12, mat=TBAND, segments=14, rings=6)
    lib.ellipsoid(bm, G, 14.0, 11.3, 0.6, 5.0, 1.3, 0.1, mat=TBAND, segments=14, rings=6)
    lib.ellipsoid(bm, G, 10.6, 21.0, 0.4, 2.4, 1.4, 0.05, mat=SHINE, segments=10, rings=5)
    lib.ellipsoid(bm, G, 11.2, 13.8, 0.62, 1.8, 1.0, 0.035, mat=SHINE, segments=10, rings=5)
    lib.ellipsoid(bm, G, 11.8, 7.0, 0.86, 1.4, 1.0, 0.03, mat=SHINE, segments=10, rings=5)

    return lib.to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newshp-267's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshp-267")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole structure's sprite (first frames) as one image, padded to the 24:28 shape that
    render_preview expects (84 x 98 px, the structure in the middle)."""
    import numpy as np
    W, H = 84, 98
    img = np.zeros((H, W, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        x0, y0 = cx + W // 2 - 12, cy + H // 2 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


# newshp-115's tank tiers, top to bottom: {frame: palette index} for each (tank gold 26 otherwise).
# The lit tier brightens on its frame; the big bottom tier also falls into shadow on the others.
TIER_FRAMES = [("top", {119: 29}), ("mid", {117: 29}), ("bottom", {115: 29, 117: 24, 119: 24})]


def animate_tank(piece, sprite):
    """newshp-115: give each of the tank's three tiers (the three islands of tank-gold faces)
    its own animated material, on this piece only (the others keep the static one)."""
    import bmesh as bm_mod
    tank = 12  # TANK in build()
    first = len(piece.data.materials)
    for tier, frames in TIER_FRAMES:
        piece.data.materials.append(common.palette_material(sprite, 26, f"nshp115-{tier}", metallic=0.4,
                                                            roughness=0.3, frames=frames))
    bm = bm_mod.new()
    bm.from_mesh(piece.data)
    todo = {f for f in bm.faces if f.material_index == tank}
    islands = []
    while todo:
        stack, island = [todo.pop()], []
        while stack:
            f = stack.pop()
            island.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g in todo:
                        todo.remove(g)
                        stack.append(g)
        islands.append(island)
    assert len(islands) == 3, f"expected 3 tank tiers, found {len(islands)}"
    islands.sort(key=lambda isl: -sum(f.calc_center_median().y for f in isl) / len(isl))  # top first
    for k, island in enumerate(islands):
        for f in island:
            f.material_index = first + k
    bm.to_mesh(piece.data)
    bm.free()
    return piece


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    animate_tank(pieces["newshp-115"], sprite)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        out = Path(out)
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=7, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
    if "--frame-previews" in sys.argv:
        out = sys.argv[sys.argv.index("--frame-previews") + 1]
        common.render_frame_previews([pieces["newshp-115"]], out, common.load_sprite(ROOT, "newshp-115"), ROOT)


if __name__ == "__main__":
    main()
