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

import math
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
    # Flesh, not metal: mid-tone skin, a little glossy, and the light does the shading (the
    # sprite's near-white streaks are the lit faces of the tip and the alae).
    mats = [
        pal(19, metallic=0.0, roughness=0.6),  # 0 skin between the parts
        pal(21, metallic=0.0, roughness=0.4),  # 1 skin (alae, column)
        pal(22, metallic=0.0, roughness=0.38),  # 2 the tip and bridge
        pal(1, metallic=0.0, roughness=1.0),  # 3 inside the nostrils
        pal(17, metallic=0.0, roughness=0.7),  # 4 dark skin: nostril rims, the column's point
    ]
    SHADOW, SKIN, LIT, HOLE, DSKIN = range(5)
    G = grid
    ax = G.x(AXIS)
    bm = bmesh.new()

    # Base: a low cushion over the whole silhouette (the skin between tip, alae and column).
    outline = lib.resample(lib.mask_outline(G, lambda v: v >= 0, rounds=3, inset=0.3), 40)
    f0 = lib.pillow(bm, outline, (ax, G.y(11)), 0.0, 0.14, 0.12, rings=4, mat_index=SHADOW)
    lib.set_smooth(bm, f0)

    # Nostrils (columns 13-18 and 26-36, rows 12-19): black floors at the level of the cushion,
    # sunk between the alae, the column and the alar rim curling round their outer and lower side.
    for side in (-1, 1):
        cx = ax + side * 8.6 * U
        cy = G.y(14.7)
        f0 = lib.ellipsoid(bm, (cx, cy, 0.0), (4.4 * U, 3.0 * U, 0.155), segments=14, rings=6, mat_index=HOLE)
        lib.set_smooth(bm, f0)
        f0 = lib.nfaces(bm)
        pts = []
        n = 12
        for k in range(n + 1):
            t = k / n
            a = math.radians(150 + 145 * t)  # from outer-top, round the bottom, to the column
            r = 2.1 * U * math.sin(math.pi * min(1.0, 0.15 + t * 0.85)) ** 0.5
            pts.append(((cx - side * 5.0 * U * math.cos(a), cy + 3.1 * U * math.sin(a), 0.0), r))
        lib.tube(bm, pts, sides=8, mat_index=SKIN, flat=1.4)
        lib.set_smooth(bm, f0)

    # Alae: the round wings either side of the tip (columns 6-16 and 32-42, rows 2-15), domes
    # about 10 px across standing about 5 px.
    for side in (-1, 1):
        f0 = lib.ellipsoid(bm, (ax + side * 13.0 * U, G.y(8.3), 0.0), (5.6 * U, 6.4 * U, 0.42),
                           segments=18, rings=10, mat_index=SKIN)
        lib.set_smooth(bm, f0)

    # The column between the nostrils: a rounded keel about 4 px tall under the tip, tapering in
    # width and height to the dark point at row 23.
    f0 = lib.nfaces(bm)
    v0 = len(bm.verts)
    common.loft(bm, [(G.y(23.6), 0.0, 0.0, 0.0), (G.y(22.0), 1.8 * U, 0.08, 0.0),
                     (G.y(19.5), 3.0 * U, 0.2, 0.0), (G.y(16.0), 3.7 * U, 0.3, 0.0),
                     (G.y(12.0), 3.8 * U, 0.36, 0.0)], sides=14, mat_index=SKIN)
    common.shift_x(bm, v0, ax)
    lib.set_smooth(bm, f0)
    f0 = lib.ellipsoid(bm, (ax, G.y(22.2), 0.0), (2.3 * U, 1.9 * U, 0.1), segments=10, rings=5, mat_index=DSKIN)
    lib.set_smooth(bm, f0)

    # The tip (columns 17-30, rows 0-11): a ball about 14 px across standing about 7 px, and the
    # bridge carrying its cross-section up off the top of the sprites.
    rx, ry, rz, cyr = 6.9 * U, 6.6 * U, 0.6, 5.2
    f0 = lib.ellipsoid(bm, (ax, G.y(cyr), 0.0), (rx, ry, rz), segments=22, rings=12, mat_index=LIT)
    lib.set_smooth(bm, f0)
    f0 = lib.nfaces(bm)
    v0 = len(bm.verts)
    k = math.sqrt(1 - ((cyr - 3.0) * U / ry) ** 2)  # the ball's cross-section at row 3
    secs = [(G.y(r), rx * k, rz * k, 0.0) for r in (3.0, 1.5, 0.0, -0.4)]
    common.loft(bm, secs, sides=22, mat_index=LIT)
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
