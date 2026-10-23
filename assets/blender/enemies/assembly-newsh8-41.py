"""Grey twin-pod gunship (newsh8.shp, assembly of 6 pieces): a 3D version of its sprites.

Seen in episode 3 (levels 3.4 and 3.19). Six 2x2 enemies side by side make one 72x56 px craft
(sprite.json `assemblyLayout`): a red spine down the middle, from a split grey dome at the top
through a T-shaped guard and a broad arrowhead chest to a long spike, with grey lobes either side
of the spike; and either side a tall grey engine pod with a red cap on top, ribbed vents, a red
slot and a glowing grille at the bottom, joined to the spine by short struts.

The whole craft is built once in assembly coordinates (left half, mirrored about pixel column
35, the sprite's axis), then cut into the six pieces with common.split_assembly. Each piece has
one frame.

Run: blender --background --python assets/blender/enemies/assembly-newsh8-41.py [-- --preview out.png]
(the preview is the whole craft; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b035 as lib  # noqa: E402

NAME = "assembly-newsh8-41"
ROOT = common.repo_root(__file__)
PIECES = ["newsh8-39", "newsh8-41", "newsh8-43", "newsh8-77", "newsh8-79", "newsh8-81"]
# Assembly pixel (0, 0) is the top-left corner of newsh8-39 (screen x 20, y -27); the assembly is
# 72 x 56 px and its centre (screen 56, 1) is the Blender origin.
CX0, CY0 = 56, 1
AXIS_COL = 35
PX = lib.PX


def X(c):
    """Assembly pixel column (centre; fractions allowed) to Blender X."""
    return (c + 0.5 - 36) / 12


def Y(r):
    """Assembly pixel row (centre) to Blender Y: sprite up is +Y."""
    return (28 - (r + 0.5)) / 12


AX = X(AXIS_COL)


def box(bm, c0, r0, c1, r1, z0, z1, mat, bevel=0.0):
    """A box over pixel columns c0..c1 and rows r0..r1 (inclusive pixel centres)."""
    x0, x1 = X(c0 - 0.5), X(c1 + 0.5)
    y0, y1 = Y(r1 + 0.5), Y(r0 - 0.5)
    if bevel:
        lib.bevel_box(bm, x0, y0, x1, y1, z0, z1, bevel=bevel, mat=mat)
    else:
        lib.box(bm, x0, y0, x1, y1, z0, z1, mat=mat)


def sweep_px(bm, pts, **kw):
    """lib.sweep with points given as (col, row, z, half_width_px, half_height_units)."""
    lib.sweep(bm, [(X(c), Y(r), z, w * PX, h) for c, r, z, w, h in pts], **kw)


def merged_sprite():
    """newsh8-41's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh8-41")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh8_41", **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.6, roughness=0.35),  # 0 grey pod body
        pal(9, metallic=0.65, roughness=0.3),  # 1 light grey slats, lips
        pal(4, metallic=0.5, roughness=0.5),  # 2 dark grey recesses
        pal(12, metallic=0.75, roughness=0.2),  # 3 bright grey rails
        pal(6, metallic=0.55, roughness=0.4),  # 4 mid grey panels
        pal(70, metallic=0.35, roughness=0.4),  # 5 red spine
        pal(74, metallic=0.4, roughness=0.3),  # 6 light red ridges
        pal(69, metallic=0.3, roughness=0.5),  # 7 dark red caps and slots
        pal(113, metallic=0.2, roughness=0.6),  # 8 grille frame
        pal(118, emission_strength=3.0),  # 9 grille glow
        pal(124, emission_strength=5.0),  # 10 hot grille bars
        pal(8, metallic=0.75, roughness=0.18),  # 11 glossy grey dome
        pal(2, metallic=0.3, roughness=0.7),  # 12 dome seam
        pal(72, metallic=0.4, roughness=0.35),  # 13 red guard
    ]
    (BODY, SLAT, RECESS, RAIL, PANEL, RED, RIDGE, DRED, FRAME, GLOW, HOT, DOME, SEAM,
     GUARD) = range(14)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----

    # Engine pod (columns 4-23, rows 15-52): a bevelled grey block.
    box(bm, 3.6, 14.6, 22.4, 52.4, -0.26, 0.1, BODY, bevel=0.05)
    # Top band (rows 15-17), the ribbed outer edge (columns 4-7) and the inner column with its
    # bright rail (columns 18-21) all stand above the vents.
    box(bm, 5.5, 15.0, 21.4, 17.2, 0.06, 0.14, PANEL, bevel=0.012)
    box(bm, 4.0, 17.0, 7.3, 38.0, 0.04, 0.125, PANEL, bevel=0.01)
    for r in (18.5, 21, 23, 25, 27, 29.5):
        box(bm, 4.2, r - 0.35, 7.1, r + 0.35, 0.1, 0.14, BODY)
    box(bm, 17.6, 15.0, 21.4, 38.0, 0.05, 0.15, BODY, bevel=0.012)
    sweep_px(bm, [(20.0, 15.2, 0.15, 0.0, 0.0), (20.0, 15.6, 0.15, 0.7, 0.02), (20.0, 37.6, 0.15, 0.7, 0.02),
                  (20.0, 38.0, 0.15, 0.0, 0.0)], sides=6, mat=RAIL)
    # Bright rail down the outer side of the vents (column 8).
    sweep_px(bm, [(8.0, 15.2, 0.14, 0.0, 0.0), (8.0, 15.6, 0.14, 0.75, 0.025), (8.0, 37.6, 0.14, 0.75, 0.025),
                  (8.0, 38.0, 0.14, 0.0, 0.0)], sides=6, mat=RAIL)
    # Vents (rows 18-27): a dark recess with five light slats.
    box(bm, 8.6, 17.6, 17.4, 27.6, 0.05, 0.105, RECESS)
    for r in (19, 21, 23, 25, 27):
        box(bm, 8.6, r - 0.45, 17.4, r + 0.45, 0.08, 0.13, SLAT)
    # Lower panel (rows 28-32), the red slot (rows 33-34) and a light lip (rows 35-37).
    box(bm, 8.6, 28.0, 17.4, 32.4, 0.06, 0.13, PANEL, bevel=0.01)
    box(bm, 10.5, 32.6, 17.4, 34.4, 0.06, 0.11, DRED)
    box(bm, 8.6, 34.6, 17.4, 37.6, 0.06, 0.14, SLAT, bevel=0.012)
    # Glowing grille at the bottom of the pod (rows 40-50), five hot bars in a dark red frame.
    box(bm, 5.5, 39.6, 21.4, 50.4, 0.05, 0.1, FRAME)
    box(bm, 6.5, 40.6, 20.6, 48.6, 0.08, 0.103, GLOW)
    for c in (8, 11, 14, 17, 20):
        sweep_px(bm, [(c, 40.6, 0.1, 0.0, 0.0), (c, 41.2, 0.1, 0.55, 0.012), (c, 48.0, 0.1, 0.55, 0.012),
                      (c, 48.6, 0.1, 0.0, 0.0)], sides=6, mat=HOT)
    # Grey lip below the grille (rows 51-52).
    box(bm, 5.5, 50.6, 20.4, 52.4, 0.04, 0.115, SLAT, bevel=0.01)
    # Grey tube down the pod's inner side (column 23, rows 21-38).
    sweep_px(bm, [(22.9, 20.4, 0.0, 0.0, 0.0), (22.9, 21.0, 0.0, 0.95, 0.08), (22.9, 38.0, 0.0, 0.95, 0.08),
                  (22.9, 38.6, 0.0, 0.0, 0.0)], sides=8, mat=RAIL)
    # Red cap on the top end of the pod (columns 6-14, rows 11-14) and a small red knob (18-20).
    sweep_px(bm, [(6.0, 13.1, 0.02, 0.0, 0.0), (6.5, 13.1, 0.02, 1.7, 0.09), (14.4, 13.1, 0.02, 1.7, 0.09),
                  (14.9, 13.1, 0.02, 0.0, 0.0)], sides=10, mat=DRED)
    sweep_px(bm, [(18.0, 13.0, 0.02, 0.0, 0.0), (18.3, 13.0, 0.02, 1.5, 0.08), (20.2, 13.0, 0.02, 1.5, 0.08),
                  (20.5, 13.0, 0.02, 0.0, 0.0)], sides=8, mat=GUARD)
    # Strut from the pod to the spine's lower lobes (row 40).
    sweep_px(bm, [(22.0, 40.2, -0.02, 1.5, 0.07), (28.5, 40.2, -0.02, 1.5, 0.07)], sides=8, mat=BODY)
    # Grey lobe beside the spike (columns 26-34, rows 39-51).
    lib.ellipsoid(bm, X(30.2), Y(45.2), 0.0, 4.4 * PX, 6.6 * PX, 0.17, mat=BODY, segments=12, rings=6)
    # Dome lobe (the dome is two lobes about the axis, columns 26-44, rows 7-22).
    lib.ellipsoid(bm, X(33.4), Y(14.6), 0.0, 8.2 * PX, 8.0 * PX, 0.28, mat=DOME, segments=16, rings=8)

    lib.mirror_x(bm, 0, axis=AX)

    # ---- the spine (symmetric about the axis) ----
    # Seam between the dome lobes.
    seam = [(AXIS_COL, r, 0.27 * (1 - ((r - 14.6) / 8.0) ** 2) ** 0.5 + 0.004, 0.35, 0.01)
            for r in (7.2, 8.5, 10, 12, 14.6, 16)]
    sweep_px(bm, seam, sides=4, mat=SEAM, smooth=False)
    # Neck (rows 16-22) with a light ridge down it.
    sweep_px(bm, [(AXIS_COL, 15.4, 0.15, 3.0, 0.08), (AXIS_COL, 16.0, 0.15, 4.0, 0.11),
                  (AXIS_COL, 22.6, 0.13, 4.0, 0.11)], sides=10, mat=RED)
    sweep_px(bm, [(AXIS_COL, 16.4, 0.25, 0.0, 0.0), (AXIS_COL, 17.0, 0.25, 0.9, 0.03),
                  (AXIS_COL, 22.0, 0.23, 0.9, 0.03), (AXIS_COL, 22.6, 0.23, 0.0, 0.0)], sides=6, mat=RIDGE)
    # T-shaped guard across rows 23-25 with its ends turned down (rows 24-26).
    sweep_px(bm, [(28.6, 24.0, 0.15, 0.0, 0.0), (29.0, 24.0, 0.15, 1.6, 0.09), (41.0, 24.0, 0.15, 1.6, 0.09),
                  (41.4, 24.0, 0.15, 0.0, 0.0)], sides=10, mat=GUARD)
    for c in (29.0, 41.0):
        sweep_px(bm, [(c, 24.0, 0.12, 0.8, 0.06), (c, 26.2, 0.1, 0.7, 0.05), (c, 26.8, 0.1, 0.0, 0.0)],
                 sides=6, mat=GUARD)
    # Narrow stem (rows 26-29) into the arrowhead chest (rows 30-42) and the long spike (to row 54).
    chest = [(25.8, 1.8, 0.08, 0.12), (26.4, 2.6, 0.09, 0.12), (29.6, 2.6, 0.09, 0.12), (30.6, 7.2, 0.13, 0.1),
             (34.2, 7.5, 0.14, 0.1), (35.0, 11.2, 0.13, 0.09), (38.4, 11.0, 0.13, 0.09), (39.3, 6.2, 0.12, 0.08),
             (42.4, 5.8, 0.11, 0.07), (43.4, 2.6, 0.08, 0.06), (46.4, 2.0, 0.07, 0.05), (47.4, 0.9, 0.05, 0.05),
             (53.8, 0.7, 0.04, 0.04), (55.0, 0.0, 0.0, 0.03)]
    sweep_px(bm, [(AXIS_COL, r, z, w, h) for r, w, h, z in chest], sides=10, mat=RED)
    # Light ridge down the middle of the chest (rows 31-41).
    sweep_px(bm, [(AXIS_COL, 30.6, 0.2, 0.0, 0.0), (AXIS_COL, 31.4, 0.21, 1.6, 0.05),
                  (AXIS_COL, 40.0, 0.2, 1.4, 0.05), (AXIS_COL, 42.0, 0.16, 0.0, 0.0)], sides=8, mat=RIDGE)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        # The whole craft's sprite, padded to the 24:28 shape render_preview expects (72 x 84 px).
        corners = [(name, cx + 36 - 12, cy + 28 - 14) for name, cx, cy in layout]
        ref = lib.composite_png(ROOT, corners, Path(tempfile.mkdtemp()) / "assembly.png", 72, 84, 0, 14)
        common.render_preview([obj], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
