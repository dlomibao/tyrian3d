"""Grey and red gunship (newsh5.shp frames 229 and 231, side by side): a 3D version of its sprites.

Seen in episode 4 (levels 4.16 and 4.47). Two 2x2 enemies make one 48x28 px ship (sprite.json
`assemblyLayout`) flying up the screen: a narrow nose with a red stripe down its spine, a red
shield on its chest between rounded grey shoulders, two grey canards up front with red fins under
them, and two big grey wings swept back and down to pointed tips that each carry a red barrel
pointing down. The lower body runs off the bottom of the sprites between red side panels.

The ship is built whole (left half mirrored about pixel column 24, the sprite's axis) in assembly
coordinates and cut into newsh5-229 (left) and newsh5-231 (right) with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-229.py [-- --preview out.png]
(the preview is the whole ship; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b013 as lib  # noqa: E402

NAME = "assembly-newsh5-229"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-229", "newsh5-231"]
U = lib.U
G = lib.Grid(48, 28)  # assembly pixels: newsh5-229 is columns 0-23, newsh5-231 columns 24-47
AXIS = 24  # mirror axis: the centre of assembly column 24
AX = G.x(AXIS)


def E(c, r):
    """A pixel corner (column edge, row edge) to Blender XY."""
    return (G.x(c - 0.5), G.y(r - 0.5))


def tilt(bm, start, x_root, slope):
    """Lower the vertices added since `start` by `slope` units per unit outward of x_root (droop)."""
    bm.verts.ensure_lookup_table()
    for v in bm.verts[start:]:
        v.co.z -= slope * max(0.0, x_root - v.co.x)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "n5a229"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.6, roughness=0.4),  # 0 grey hull
        pal(7, metallic=0.6, roughness=0.4),  # 1 grey wings
        pal(10, metallic=0.7, roughness=0.3),  # 2 bright grey ribs and tips
        pal(4, metallic=0.5, roughness=0.5),  # 3 dark grey
        pal(70, metallic=0.35, roughness=0.45),  # 4 red panels
        pal(73, metallic=0.35, roughness=0.4),  # 5 light red shield and stripe
        pal(67, metallic=0.3, roughness=0.55),  # 6 dark red fins
    ]
    HULL, WING, RIB, DARK, RED, LRED, DRED = range(7)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----
    start = len(bm.verts)

    # Wing (rows 14-27): swept from the body out and up to a pointed tip at columns 2-4.
    wing = [E(2.5, 13.5), E(4.5, 13.5), E(9, 18), E(14.5, 19.5), E(17, 19.5), E(17, 29),
            E(11.5, 29), E(5.5, 21.5), E(4.5, 20.5), E(2.5, 20.5)]
    v0 = len(bm.verts)
    lib.prism(bm, wing, -0.035, 0.035, mat_index=WING)
    tilt(bm, v0, G.x(16), 0.1)
    # Raised ribs along the wing (the light diagonal lines).
    for (c0, r0), (c1, r1) in (((5.5, 17.0), (11.5, 27.0)), ((8.5, 19.0), (14.0, 26.5))):
        v0 = len(bm.verts)
        lib.tube(bm, [((*E(c0, r0), 0.035), 0.45 * U), ((*E(c1, r1), 0.035), 0.45 * U)],
                 sides=6, mat_index=RIB, flat=0.6)
        tilt(bm, v0, G.x(16), 0.1)
    # Wing tip (columns 3-4, rows 14-19) and the red barrel under it (column 3, rows 20-26).
    v0 = len(bm.verts)
    common.loft(bm, [(G.y(13.3), 0.0, 0.0, 0.0), (G.y(14.5), 0.9 * U, 0.05, 0.0), (G.y(17), 1.3 * U, 0.06, 0.0),
                     (G.y(20.3), 1.3 * U, 0.06, 0.0), (G.y(20.8), 0.0, 0.0, 0.0)], sides=10, mat_index=RIB)
    common.shift_x(bm, v0, G.x(3.5))
    f0 = lib.nfaces(bm)
    v1 = len(bm.verts)
    common.loft(bm, [(G.y(19.5), 0.8 * U, 0.04, -0.01), (G.y(26.3), 0.8 * U, 0.04, -0.01),
                     (G.y(27.0), 0.0, 0.0, -0.01)], sides=8, mat_index=RED)
    common.shift_x(bm, v1, G.x(3))
    lib.set_smooth(bm, f0)
    tilt(bm, v0, G.x(16), 0.1)
    # Red cowl on the wing's root (columns 10-13, rows 16-18).
    f0 = lib.ellipsoid(bm, (G.x(12), G.y(17.2), 0.03), (2.3 * U, 1.6 * U, 0.06), segments=12, rings=6, mat_index=RED)
    lib.set_smooth(bm, f0)

    # Canard (rows 2-4, columns 10-19) and the red fin under it sloping in to the body.
    f0 = lib.nfaces(bm)
    lib.loft_x(bm, [(G.x(9.4), 0.9 * U, 0.03, 0.0), (G.x(10.0), 1.6 * U, 0.05, 0.0),
                    (G.x(21.0), 1.6 * U, 0.05, 0.0)], y=G.y(3.0), z=0.07, sides=10, mat_index=HULL)
    lib.set_smooth(bm, f0)
    fin = [E(11.5, 4.5), E(19.5, 4.5), E(20.5, 6.0), E(19.5, 9.0), E(17.0, 9.0), E(14.5, 6.5), E(11.5, 5.6)]
    lib.prism(bm, fin, -0.01, 0.06, mat_index=RED)
    lib.prism(bm, [E(16.5, 4.5), E(18.5, 4.5), E(18.5, 8.5), E(17.5, 8.5)], 0.06, 0.075, mat_index=LRED)

    # Red side panel down the lower body (columns 16-19, rows 16-27).
    f0 = lib.nfaces(bm)
    v0 = len(bm.verts)
    common.loft(bm, [(G.y(15.6), 0.0, 0.0, 0.0), (G.y(16.6), 1.9 * U, 0.09, 0.0), (G.y(29), 1.9 * U, 0.09, 0.0)],
                sides=10, mat_index=RED)
    common.shift_x(bm, v0, G.x(17.8))
    lib.set_smooth(bm, f0)

    lib.mirror_x(bm, start, AX)

    # ---- centre parts ----

    # Body: the narrow nose (rows 1-8), the shoulders (rows 9-17) and the lower body (rows 18-27).
    f0 = lib.nfaces(bm)
    v0 = len(bm.verts)
    body = [(0.3, 0.0, 0.0, 0.05), (1.0, 1.2, 0.04, 0.05), (2.5, 2.6, 0.07, 0.04), (3.6, 3.5, 0.09, 0.03),
            (8.6, 3.6, 0.1, 0.03), (9.6, 5.6, 0.13, 0.02), (10.6, 7.4, 0.17, 0.01), (12.0, 8.4, 0.19, 0.0),
            (15.5, 8.4, 0.19, 0.0), (17.0, 6.8, 0.17, 0.0), (18.5, 5.0, 0.15, 0.0), (29.0, 5.0, 0.15, 0.0)]
    common.loft(bm, [(G.y(r - 0.5), w * U, h, z) for r, w, h, z in body], sides=14, mat_index=HULL)
    common.shift_x(bm, v0, AX)
    lib.set_smooth(bm, f0)
    # Red stripe down the spine (rows 1-10), into the chest shield.
    f0 = lib.nfaces(bm)
    v0 = len(bm.verts)
    common.loft(bm, [(G.y(0.6), 0.0, 0.0, 0.08), (G.y(1.5), 0.7 * U, 0.02, 0.09), (G.y(3.5), 0.8 * U, 0.025, 0.12),
                     (G.y(8.5), 0.8 * U, 0.025, 0.13), (G.y(10.5), 0.8 * U, 0.025, 0.17)], sides=8, mat_index=LRED)
    common.shift_x(bm, v0, AX)
    # The red shield on the chest (columns 20-28, rows 10-15).
    lib.ellipsoid(bm, (AX, G.y(12.7), 0.15), (4.9 * U, 3.4 * U, 0.075), segments=16, rings=8, mat_index=RED)
    lib.set_smooth(bm, f0)
    # Dark slot under the chest (row 16) and a light keel down the lower body.
    lib.box(bm, AX - 3.5 * U, G.y(16.6), AX + 3.5 * U, G.y(15.9), 0.1, 0.165, mat_index=DARK)
    f0 = lib.nfaces(bm)
    v0 = len(bm.verts)
    common.loft(bm, [(G.y(17.5), 0.0, 0.0, 0.13), (G.y(18.5), 1.0 * U, 0.03, 0.14), (G.y(29), 1.0 * U, 0.03, 0.14)],
                sides=8, mat_index=RIB)
    common.shift_x(bm, v0, AX - 0.5 * U)
    lib.set_smooth(bm, f0)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    # Piece centres relative to the assembly centre, in pixels (sprite.json cx 65 and 89, cy -18).
    layout = [("newsh5-229", -12, 0), ("newsh5-231", 12, 0)]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        out = Path(out)
        import tempfile
        frames = [common.load_sprite(ROOT, n) for n in PIECES]
        # The whole ship's sprite, padded to the 24:28 shape render_preview expects for size 4.
        ref = Path(tempfile.mkdtemp()) / "assembly.png"
        lib.composite_png([(frames[0]["frames"][0]["pixels"], frames[0]["colors"], 0, 14),
                           (frames[1]["frames"][0]["pixels"], frames[1]["colors"], 24, 14)], 48, 56, ref)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name, data in zip(PIECES, frames):
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
