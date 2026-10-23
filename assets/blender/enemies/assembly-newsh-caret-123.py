"""Grey and red machine boss (newsh^.shp, assembly of 8 pieces): a 3D version of its sprites.

Eight 2x2 enemies side by side (two rows of four: newsh-caret-83/85/87/89 over
121/123/125/127, sprite.json `assemblyLayout`) make one 84 x 46 px machine, mirror symmetric
about its middle (the sprite is lit from the left, so its right half is drawn darker): a pink-red
spine down the middle on a wide red plate, red beams reaching out to grey pods at both ends, grey
horns with arms on top, a grey chest block with prongs and red legs below, and grey claws hanging
down at the lower corners. (newsh5-166, listed in the layout, is a separate enemy below it.)

The machine is built once in assembly coordinates (left half, mirrored), then cut into the pieces
with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh-caret-123.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b038 as lib  # noqa: E402

NAME = "assembly-newsh-caret-123"
ROOT = common.repo_root(__file__)
PIECES = ["newsh-caret-83", "newsh-caret-85", "newsh-caret-87", "newsh-caret-89",
          "newsh-caret-121", "newsh-caret-123", "newsh-caret-125", "newsh-caret-127"]
# Assembly grid: pixel (0, 0) is screen pixel (20, 37). The machine's axis is the centre of column
# 48 (edge 48.5), and edge row 27 is the Blender origin's Y. So screen edge (xs, ys) maps to
# X = (xs - 68.5) / 12, Y = -(ys - 64) / 12.
G = lib.Grid(48.5, 27.0)
SX0, SY0 = 68.5, 64.0


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshc123"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(2, metallic=0.2, roughness=0.8),  # 0 dark recesses
        pal(4, metallic=0.5, roughness=0.45),  # 1 dark grey
        pal(6, metallic=0.55, roughness=0.4),  # 2 grey
        pal(8, metallic=0.6, roughness=0.35),  # 3 light grey
        pal(10, metallic=0.7, roughness=0.3),  # 4 bright grey ridges
        pal(67, metallic=0.3, roughness=0.5),  # 5 dark red
        pal(70, metallic=0.3, roughness=0.45),  # 6 red
        pal(73, metallic=0.3, roughness=0.4),  # 7 light red plate
        pal(75, metallic=0.3, roughness=0.35),  # 8 pink spine
        pal(78, metallic=0.3, roughness=0.3),  # 9 pale pink knobs
        pal(5, metallic=0.5, roughness=0.45),  # 10 mid grey
    ]
    DARK, DGREY, GREY, LGREY, BRIGHT, DRED, RED, LRED, PINK, PALE, MGREY = range(11)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----

    # Dark chassis under everything, showing in the gaps between parts.
    lib.plate(bm, G, [(8, 20.5), (14, 19.5), (30, 18.5), (44, 18.5), (44, 12.5), (48.5, 12.5),
                      (48.5, 45), (42, 45), (41, 39), (33, 39.5), (30, 39), (28, 33), (16, 32), (9, 31)],
              -0.2, -0.06, mat=DARK)

    # Horn on the shoulder: a slanted block from row 5 down to the red plate (columns 29-39),
    # with two bright ridges down it, and a thin bar out to the left at row 8.
    lib.plate(bm, G, [(31, 5), (38, 5), (36, 7.5), (36, 11), (40, 12), (40, 18.5), (29, 18.5), (28.2, 9),
                      (29, 7)], -0.1, 0.2, mat=GREY, bevel=0.035)
    lib.box(bm, G, [(34.4, 5.4, 0.2, 1.4, 0.035), (34.0, 10, 0.2, 1.6, 0.04), (34.6, 17.6, 0.2, 1.6, 0.04)],
            mat=BRIGHT)
    lib.box(bm, G, [(38.8, 12.6, 0.18, 1.0, 0.035), (38.8, 17.6, 0.18, 1.0, 0.035)], mat=BRIGHT)
    lib.box(bm, G, [(24.0, 8.5, 0.07, 0.7, 0.05), (29.5, 8.5, 0.08, 0.7, 0.05)], mat=MGREY)

    # Arm out of the horn to the left (rows 11-18): a strut on top, a grey block with a red
    # panel, and a darker end block (columns 15-22).
    lib.box(bm, G, [(18.0, 11.5, 0.06, 0.7, 0.05), (30.0, 11.5, 0.12, 0.7, 0.05)], mat=DGREY)
    lib.plate(bm, G, [(23, 12), (30, 12), (30, 18.5), (23, 18.5)], -0.1, 0.12, mat=GREY, bevel=0.03)
    lib.plate(bm, G, [(23.2, 13), (28, 13), (28, 16), (23.2, 16)], 0.1, 0.14, mat=DRED, bevel=0.012)
    lib.box(bm, G, [(14.6, 14.6, 0.02, 2.3, 0.1), (23.0, 14.8, 0.06, 2.6, 0.11)], mat=DGREY)
    lib.box(bm, G, [(18.0, 17.0, 0.0, 1.2, 0.07), (22.5, 17.6, 0.02, 1.2, 0.07)], mat=DGREY)

    # Red beam out to the pod (rows 19-22), passing under the horn into the red plate.
    lib.box(bm, G, [(13.8, 21.2, 0.08, 1.6, 0.08), (19, 20.6, 0.08, 1.9, 0.09), (33, 20.4, 0.06, 2.0, 0.09)],
            mat=DRED)

    # Wide red plate across the middle (rows 18-25), with a fork down the spine's left side.
    lib.plate(bm, G, [(31.5, 19.5), (34, 18), (40, 18), (42, 19), (48.5, 19), (48.5, 25), (44, 25),
                      (44, 28.2), (40, 28.2), (40, 25.5), (31.5, 25.5)], -0.06, 0.13, mat=LRED, bevel=0.04)

    # Grey pod at the outer end (columns 7-30, rows 20-31): a drum with a bright rim near its
    # blunt end and two red bands.
    lib.sweep(bm, G, [(6.8, 24.2, 0.0, 2.6, 0.12), (7.3, 24.2, 0.0, 3.6, 0.17), (8.6, 24.2, 0.0, 4.0, 0.19),
                      (10.6, 24.6, 0.0, 4.2, 0.2), (13, 25.6, -0.01, 4.9, 0.2), (21, 25.8, -0.01, 5.2, 0.2),
                      (24.5, 25.2, 0.0, 4.4, 0.18), (30.5, 24.6, 0.0, 3.6, 0.15)], sides=12, mat=GREY)
    lib.sweep(bm, G, [(10.2, 24.4, 0.0, 4.4, 0.21), (11.2, 24.6, 0.0, 4.5, 0.215)], sides=12, mat=BRIGHT)
    for c in (15.2, 21.0):
        lib.sweep(bm, G, [(c, 25.6, -0.01, 5.3, 0.215), (c + 2, 25.6, -0.01, 5.4, 0.215)], sides=12, mat=RED)
    lib.sweep(bm, G, [(8, 29.6, -0.02, 1.4, 0.08), (12, 29.6, -0.02, 1.4, 0.08)], sides=8, mat=MGREY)

    # Red blade under the plate, sweeping down and out (rows 26-35).
    lib.plate(bm, G, [(29, 26), (39, 26), (39, 28), (35, 29), (34, 31), (31, 31.2), (29, 32.2), (28, 34),
                      (26.5, 35), (24, 33), (24, 30), (29, 30)], -0.06, 0.1, mat=RED, bevel=0.03)

    # Claw hanging at the lower corner (rows 32-49), with a bright ridge down it, and a dark
    # block beside it.
    lib.sweep(bm, G, [(19.5, 31.0, -0.02, 3.6, 0.1), (21.0, 33.0, -0.02, 4.2, 0.13), (21.6, 36.5, -0.02, 5.4, 0.16),
                      (22.6, 39.0, -0.02, 5.4, 0.16), (24.8, 41.0, -0.03, 5.2, 0.15), (24.2, 44.0, -0.03, 4.6, 0.13),
                      (24.6, 46.5, -0.03, 3.4, 0.1), (25.3, 48.4, -0.03, 1.8, 0.06), (25.5, 49.2, -0.03, 0.0, 0.0)],
              sides=10, mat=MGREY)
    lib.sweep(bm, G, [(25.4, 33.8, 0.11, 0.0, 0.0), (25.2, 35.0, 0.12, 0.7, 0.03), (24.8, 38.5, 0.14, 0.7, 0.03),
                      (26.2, 42.0, 0.13, 0.6, 0.03), (26.2, 45, 0.09, 0.5, 0.025), (26.0, 46, 0.08, 0.0, 0.0)],
              sides=6, mat=BRIGHT)
    lib.plate(bm, G, [(28, 32), (34, 32), (34, 39), (31, 39), (28, 38)], -0.12, 0.06, mat=DGREY, bevel=0.02)

    # Chest block below the plate (rows 29-36) with a bright bar across it.
    lib.plate(bm, G, [(35, 28.8), (48.5, 28.8), (48.5, 37.5), (42, 37.5), (42, 35), (35, 35)],
              -0.12, 0.12, mat=LGREY, bevel=0.035)
    lib.box(bm, G, [(35.4, 32.6, 0.12, 1.0, 0.035), (48.5, 32.6, 0.12, 1.0, 0.035)], mat=BRIGHT)

    # Prongs hanging from the chest (columns 42-49, rows 37-45) and red legs beside them.
    lib.box(bm, G, [(43.6, 36.5, -0.02, 1.6, 0.08), (43.6, 44.8, -0.03, 1.2, 0.06)], mat=GREY)
    lib.box(bm, G, [(46.5, 38.0, -0.02, 0.6, 0.05), (46.5, 43.0, -0.03, 0.5, 0.04)], mat=GREY)
    lib.plate(bm, G, [(35, 36), (41, 36), (41, 38), (35, 38)], -0.08, 0.06, mat=DRED, bevel=0.015)
    lib.box(bm, G, [(39.5, 37.8, -0.02, 1.4, 0.07), (39.5, 41.0, -0.02, 1.4, 0.07)], mat=MGREY)
    lib.sweep(bm, G, [(39.8, 40.4, -0.03, 0.0, 0.0), (39.8, 41.2, -0.03, 2.0, 0.1), (40.0, 46.0, -0.03, 2.2, 0.1),
                      (39.6, 47.6, -0.03, 1.4, 0.07), (39.5, 48.3, -0.03, 0.0, 0.0)], sides=10, mat=RED)
    lib.plate(bm, G, [(34, 39), (37.8, 39), (37.8, 44), (34, 44)], -0.1, 0.05, mat=DGREY, bevel=0.015)

    lib.mirror_all(bm)

    # ---- centre parts (symmetric about the axis) ----

    # Pink spine down the middle (rows 12-32), widest where it crosses the plate, with two pale
    # knobs on it.
    lib.sweep(bm, G, [(48.5, 12.4, 0.12, 0.0, 0.0), (48.5, 12.9, 0.12, 2.6, 0.08), (48.5, 14, 0.13, 3.5, 0.12),
                      (48.5, 17.5, 0.15, 3.6, 0.15), (48.5, 19.5, 0.16, 4.6, 0.2), (48.5, 25.5, 0.16, 4.6, 0.2),
                      (48.5, 28, 0.15, 2.4, 0.14), (48.5, 31.8, 0.14, 1.8, 0.1), (48.5, 32.6, 0.13, 0.0, 0.0)],
              sides=12, mat=PINK)
    lib.sweep(bm, G, [(48.5, 12.9, 0.13, 0.0, 0.0), (48.5, 13.4, 0.15, 3.6, 0.1), (48.5, 14.8, 0.16, 3.7, 0.12),
                      (48.5, 15.3, 0.15, 0.0, 0.0)], sides=12, mat=RED)
    for r in (20.2, 24.8):
        lib.ellipsoid(bm, G, 48.5, r, 0.33, 2.4, 1.6, 0.06, mat=PALE)
    # Prong down the middle of the chest.
    lib.box(bm, G, [(48.5, 36.0, -0.02, 0.6, 0.05), (48.5, 44.6, -0.03, 0.5, 0.04)], mat=GREY)

    return lib.to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newsh-caret-123's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh-caret-123")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    screen = [(e["model"], e["cx"], e["cy"]) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    layout = [(name, cx - SX0, cy - SY0) for name, cx, cy in screen]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        # The whole machine, 96 x 112 px (size 8) centred on the axis: screen (20, 8) at top left.
        ref = lib.composite_png(ROOT, screen, Path(tempfile.mkdtemp()) / "assembly.png", 96, 112, 20, 8)
        common.render_preview([obj], str(out), ref, size=8, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
