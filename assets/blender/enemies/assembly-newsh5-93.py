"""Grey machine column (newsh5.shp frames 55 and 93, assembly of 2 pieces): a 3D version of its sprites.

Seen in episode 4 (level 4.8) lying on the ground beside a claw arm (newsh# pieces, modelled
elsewhere). Two 2x2 enemies one above the other make a 24 x 56 px machine (sprite.json
`assemblyLayout`): a grey metal shaft lying along the screen, from a small domed cap at the top
through a flange, a neck and broad rounded shoulders with two glowing red hoses hanging from
them, down past a collar, a ring, a ribbed segment, a thin rod section and a knob to a pointed
bulb at the bottom. Each part is a loft round the shaft's axis (pixel column 11), sitting on the
ground.

The machine is built once in assembly coordinates and cut into newsh5-55 (top) and newsh5-93
(bottom) with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-93.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b068 as L  # noqa: E402

common = L.common
NAME = "assembly-newsh5-93"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-55", "newsh5-93"]
# The machine is 24 x 56 px: newsh5-55's block over newsh5-93's. Its centre (screen 104, 25) is
# the Blender origin, so assembly pixel (c, r) is at X(c), Y(r) below.
CX0, CY0 = 104, 25
AXIS = 11  # the shaft's axis: pixel column 11


def X(c):
    return (c + 0.5 - 12) / 12


def Y(r):
    return (28 - (r + 0.5)) / 12


def shaft(bm, sections, mat, col=AXIS, sides=12):
    """A grounded loft along the shaft: sections are (row, half width px, half height units[, z]);
    each ring sits on the ground (its centre at its own half height) unless a z is given (for the
    point a rounded end closes to)."""
    L.sweep(bm, [(X(col), Y(sec[0]), sec[3] if len(sec) > 3 else sec[2], sec[1] * L.PX, sec[2])
                 for sec in sections], sides=sides, mat=mat)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh5a93"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.6, roughness=0.35),  # 0 grey metal
        pal(11, metallic=0.7, roughness=0.25),  # 1 bright flanges and rings
        pal(5, metallic=0.6, roughness=0.4),  # 2 dark metal
        pal(4, metallic=0.5, roughness=0.5),  # 3 darkest: the spine, grooves
        pal(13, metallic=0.75, roughness=0.2),  # 4 polished rod
        pal(116, roughness=0.35, emission_strength=2.0),  # 5 glowing red hoses
        pal(124, emission_strength=5.0),  # 6 hot nub
        pal(9, metallic=0.6, roughness=0.3),  # 7 light grey
    ]
    METAL, BRIGHT, DARK, SPINE, ROD, HOSE, HOT, LIGHT = range(8)
    bm = bmesh.new()

    # A thin spine joining every part, top to bottom.
    shaft(bm, [(0.6, 1.6, 0.06), (55.0, 1.6, 0.06)], SPINE, sides=8)

    # Domed cap (rows 0-4) and the bright flange under it (rows 5-8).
    shaft(bm, [(-0.3, 0.0, 0.0, 0.09), (0.2, 1.8, 0.07), (1.2, 3.0, 0.11), (2.6, 3.4, 0.13), (4.4, 3.3, 0.12),
               (5.0, 2.4, 0.09)], METAL)
    shaft(bm, [(4.6, 4.5, 0.15), (5.2, 5.5, 0.19), (8.3, 5.3, 0.18), (8.9, 4.0, 0.13)], BRIGHT)
    # Neck (rows 9-12).
    shaft(bm, [(8.8, 2.6, 0.1), (9.4, 3.0, 0.12), (12.2, 3.0, 0.12), (12.8, 2.6, 0.1)], DARK)
    # Broad rounded shoulders (rows 13-17).
    shaft(bm, [(12.4, 3.5, 0.12), (13.3, 5.5, 0.18), (14.4, 6.7, 0.21), (15.5, 7.6, 0.22),
               (16.5, 8.0, 0.22), (17.2, 6.5, 0.18), (17.6, 3.0, 0.1)], METAL, sides=14)
    # Armour plates down the shoulders' outer edges (columns 3-5 and 17-19, rows 16-19).
    for col in (4.0, 18.0):
        shaft(bm, [(15.8, 0.0, 0.0, 0.12), (16.4, 1.3, 0.13), (17.5, 1.6, 0.15), (19.4, 1.6, 0.15), (20.0, 0.0, 0.0, 0.1)],
              DARK, col=col, sides=8)
    # The centre of the shaft between the hoses (rows 17-23), with a polished rod down it.
    shaft(bm, [(17.0, 2.0, 0.1), (23.8, 2.0, 0.1)], LIGHT, sides=10)
    L.sweep(bm, [(X(AXIS), Y(17.5), 0.2, 0.5 * L.PX, 0.02), (X(AXIS), Y(23.5), 0.2, 0.5 * L.PX, 0.02)],
            sides=6, mat=ROD)
    # Two glowing red hoses hanging from the shoulders (columns 6-9 and 13-16, rows 17-22).
    for path in ([(6.3, 17.2), (7.6, 18.6), (8.5, 20.0), (8.6, 22.6)],
                 [(15.7, 17.2), (14.4, 18.6), (13.5, 20.0), (13.4, 22.6)]):
        L.sweep(bm, [(X(c), Y(r), 0.12, 1.15 * L.PX, 0.11) for c, r in path], sides=10, mat=HOSE)
    L.ellipsoid(bm, (X(8.0), Y(19.0), 0.22), (1.0 * L.PX, 1.0 * L.PX, 0.04), mat=HOT, segments=10, rings=5)

    # Collar (rows 24-26) and the short neck under it (rows 27-29).
    shaft(bm, [(23.6, 3.5, 0.13), (24.2, 5.5, 0.19), (26.8, 5.5, 0.19), (27.3, 3.6, 0.13)], LIGHT)
    shaft(bm, [(27.2, 3.4, 0.12), (29.4, 3.0, 0.11)], DARK)
    # Ring (row 30).
    shaft(bm, [(29.4, 3.0, 0.11), (29.9, 4.5, 0.16), (30.9, 4.5, 0.16), (31.4, 2.6, 0.1)], BRIGHT)
    # Ribbed segment (rows 32-37).
    shaft(bm, [(31.5, 2.6, 0.1), (32.1, 3.5, 0.14), (35.6, 3.5, 0.14), (36.5, 3.0, 0.12), (37.6, 2.4, 0.1)], METAL)
    # Thin rod section (rows 38-41): two dark rails with a polished rod between them.
    for col in (9.0, 13.0):
        shaft(bm, [(37.4, 1.0, 0.09), (42.2, 1.0, 0.09)], DARK, col=col, sides=8)
    L.sweep(bm, [(X(AXIS), Y(37.5), 0.1, 0.6 * L.PX, 0.06), (X(AXIS), Y(42.0), 0.1, 0.6 * L.PX, 0.06)],
            sides=8, mat=ROD)
    # Knob (rows 42-46).
    shaft(bm, [(41.6, 3.0, 0.11), (42.4, 4.0, 0.15), (44.6, 4.0, 0.15), (45.5, 3.4, 0.13), (46.6, 2.8, 0.1)], LIGHT)
    # Pointed bulb (rows 47-55).
    shaft(bm, [(46.6, 2.6, 0.1), (47.4, 3.4, 0.14), (48.5, 3.8, 0.15), (51.0, 3.7, 0.15), (52.6, 2.8, 0.12),
               (54.0, 1.6, 0.07), (55.5, 0.0, 0.0, 0.05)], METAL)

    return L.to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newsh5-55's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh5-55")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out):
    """The whole machine's sprite as one image, padded to the 24:28 shape that render_preview
    expects for size 4 (48 x 56 px, the machine in the middle)."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][0]
        x0, y0 = cx + 24 - 12, cy + 28 - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[y0 + r, x0 + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = L.preview_arg()
    if out:
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
