"""Giant nose (newsh5.shp frames 191 and 193, side by side): a 3D version of its sprites.

Seen in episode 4 (level 4.25), the flying face: two eyeballs (newsh5-270, a separate model) over
a brown nose made of two 2x2 enemies (sprite.json `assemblyLayout`), 48x24 px: a round tip whose
bridge runs up off the top of the sprites, a rounded wing (ala) on each side, two dark nostrils
under them and the column of flesh between the nostrils running down to a point.

The nose is built whole (mirror symmetric about pixel column 24) in assembly coordinates and cut
into newsh5-191 (left) and newsh5-193 (right) with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-191.py [-- --preview out.png]
(the preview is the whole nose; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b013 as lib  # noqa: E402

NAME = "assembly-newsh5-191"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-191", "newsh5-193"]
U = lib.U
AXIS = 24  # mirror axis: the centre of assembly column 24


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    tag = "n5a191"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(22, metallic=0.0, roughness=0.6),  # 0 skin in shadow
        pal(24, metallic=0.0, roughness=0.5),  # 1 skin
        pal(26, metallic=0.0, roughness=0.45),  # 2 lit skin (the tip)
        pal(16, metallic=0.0, roughness=0.9),  # 3 nostrils
        pal(19, metallic=0.0, roughness=0.7),  # 4 dark skin round the nostrils
    ]
    SHADOW, SKIN, LIT, HOLE, DSKIN = range(5)
    G = grid
    ax = G.x(AXIS)
    bm = bmesh.new()

    # Base: a low cushion over the whole silhouette.
    outline = lib.resample(lib.mask_outline(G, lambda v: v >= 0, rounds=3, inset=0.3), 40)
    f0 = lib.pillow(bm, outline, (ax, G.y(11)), 0.0, 0.1, 0.12, rings=4, mat_index=SHADOW)
    lib.set_smooth(bm, f0)

    # Nostrils (columns 13-18 and 30-36, rows 12-19), in darker skin.
    for side in (-1, 1):
        cx = ax + side * 8.4 * U
        f0 = lib.ellipsoid(bm, (cx, G.y(15.3), 0.0), (6.2 * U, 4.8 * U, 0.11), segments=14, rings=6, mat_index=DSKIN)
        lib.set_smooth(bm, f0)
        f0 = lib.ellipsoid(bm, (cx + side * 0.3 * U, G.y(15.6), 0.03), (5.2 * U, 3.5 * U, 0.1),
                           segments=14, rings=6, mat_index=HOLE)
        lib.set_smooth(bm, f0)

    # Alae: the rounded wings either side of the tip (columns 6-15 and 33-42, rows 2-17).
    for side in (-1, 1):
        f0 = lib.ellipsoid(bm, (ax + side * 12.3 * U, G.y(9.2), -0.02), (6.6 * U, 7.6 * U, 0.19),
                           segments=16, rings=8, mat_index=SKIN)
        lib.set_smooth(bm, f0)

    # The column between the nostrils, running down to a point (rows 12-23).
    f0 = lib.ellipsoid(bm, (ax, G.y(16.0), 0.0), (3.6 * U, 6.4 * U, 0.14), segments=14, rings=7, mat_index=SKIN)
    lib.set_smooth(bm, f0)
    f0 = lib.ellipsoid(bm, (ax, G.y(20.0), 0.0), (2.8 * U, 3.3 * U, 0.09), segments=10, rings=5, mat_index=SHADOW)
    lib.set_smooth(bm, f0)

    # The tip (columns 16-31, rows 0-12) and the bridge rising up off the top of the sprites.
    f0 = lib.ellipsoid(bm, (ax, G.y(5.6), 0.0), (8.6 * U, 7.6 * U, 0.28), segments=18, rings=9, mat_index=LIT)
    lib.set_smooth(bm, f0)
    f0 = lib.nfaces(bm)
    v0 = len(bm.verts)
    common.loft(bm, [(G.y(1.0), 7.0 * U, 0.2, 0.0), (G.y(-2.0), 6.6 * U, 0.2, 0.0)], sides=16, mat_index=LIT)
    common.shift_x(bm, v0, ax)
    lib.set_smooth(bm, f0)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    frames = [common.load_sprite(ROOT, n) for n in PIECES]
    pixels = lib.combined_pixels([(frames[0]["frames"][0]["pixels"], 0, 0),
                                  (frames[1]["frames"][0]["pixels"], 24, 0)], 48, 28)
    grid = lib.Grid(48, 28, pixels)
    obj = build(sprite, grid)
    # Piece centres relative to the assembly centre, in pixels (sprite.json cx 70 and 94, cy 49).
    layout = [("newsh5-191", -12, 0), ("newsh5-193", 12, 0)]
    pieces = common.split_assembly(obj, layout)
    for name, data in zip(PIECES, frames):
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        out = Path(out)
        import tempfile
        ref = Path(tempfile.mkdtemp()) / "assembly.png"
        lib.composite_png([(frames[0]["frames"][0]["pixels"], frames[0]["colors"], 0, 14),
                           (frames[1]["frames"][0]["pixels"], frames[1]["colors"], 24, 14)], 48, 56, ref)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name, data in zip(PIECES, frames):
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
