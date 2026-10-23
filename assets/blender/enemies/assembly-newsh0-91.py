"""Winged blue-steel crest (newsh0.shp frames 91 and 93, an assembly of two pieces): a 3D version
of its sprites.

Seen in episode 2 (level 2.12). Two 2x2 enemies side by side make one 48x28 px object, mirror
symmetric about pixel column 24 (newsh0-93's first column): a pale blue spine down the middle
flanked by two horns that curve up and out to points at the top, a grey blade standing beside
each horn, three grey feathers fanning out to each side (a swept blade with a bright leading
edge, a rounded bar, and a darker blade angled down), and the top of a mottled blue body across
the bottom, which runs off the bottom of the tile.

Built whole in assembly coordinates (left half, mirrored about column 24), then cut into the two
pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh0-91.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b025 as lib  # noqa: E402
from lib_b025 import common  # noqa: E402

NAME = "assembly-newsh0-91"
ROOT = common.repo_root(__file__)
PIECES = ["newsh0-91", "newsh0-93"]
G = lib.Grid(48, 28)  # assembly pixels: newsh0-91 is columns 0-23, newsh0-93 columns 24-47
AX = G.x(24)
CX0, CY0 = 126, -17  # the assembly's centre in screen pixels (between the two pieces)


def build(colors):
    coll = common.reset_collection(NAME)
    m = lib.Mats("nsh0_91", colors)
    SPINE = m(58, metallic=0.5, roughness=0.3)
    HORN = m(59, metallic=0.5, roughness=0.3)
    SHINE = m(62, metallic=0.5, roughness=0.25)
    BODY = m(54, metallic=0.45, roughness=0.4)
    BODY_HI = m(57, metallic=0.45, roughness=0.35)
    BLADE = m(9, metallic=0.7, roughness=0.3)
    FEATHER = m(11, metallic=0.7, roughness=0.3)
    EDGE = m(13, metallic=0.7, roughness=0.25)
    BAR = m(9, metallic=0.7, roughness=0.3)
    BAR_HI = m(12, metallic=0.7, roughness=0.25)
    LOWER = m(7, metallic=0.65, roughness=0.35)
    LOWER_HI = m(10, metallic=0.7, roughness=0.3)
    SLOT = m(49, metallic=0.2, roughness=0.7)
    BACK = m(4, metallic=0.5, roughness=0.5)
    bm = bmesh.new()

    # ---- left half, mirrored below ----
    # Dark grey backing under the feathers, so the gaps between them read as shadow.
    lib.pillow(bm, G, [(8, 12.5), (16, 9), (21, 9), (21, 22), (14, 22.5), (12, 22), (8, 17)],
               -0.1, -0.04, round_px=0.8, mat=BACK)
    # Upper feather: a swept blade, bright along its top edge (rows 8-12).
    lib.pillow(bm, G, [(6.2, 8), (14, 8), (16.5, 8.8), (18.5, 10.2), (20.5, 11.2), (20.5, 12.6), (16, 12.2),
                       (12, 12.1), (10.5, 11), (8.5, 10), (6.6, 8.9)], -0.04, 0.05, round_px=0.6, mat=FEATHER)
    lib.sweep(bm, G, [(6.4, 8.4, 0.03, 0.0, 0.0), (7.2, 8.45, 0.035, 0.55, 0.025), (12.5, 8.5, 0.04, 0.6, 0.03),
                      (15.5, 9.2, 0.035, 0.0, 0.0)], sides=6, mat=EDGE)
    # Middle feather: a rounded bar (rows 13-16), lit along its top.
    lib.sweep(bm, G, [(6.4, 14.9, 0.0, 0.0, 0.0), (6.9, 14.9, 0.0, 1.4, 0.06), (8.0, 14.85, 0.0, 2.0, 0.085),
                      (16.0, 14.8, 0.0, 2.0, 0.09), (19.5, 14.6, -0.01, 1.8, 0.08), (21.0, 14.5, -0.02, 1.4, 0.06)],
              sides=10, mat=BAR)
    lib.sweep(bm, G, [(8.6, 13.6, 0.06, 0.0, 0.0), (9.4, 13.6, 0.065, 0.6, 0.025), (14.5, 13.6, 0.07, 0.6, 0.025),
                      (15.5, 13.7, 0.065, 0.0, 0.0)], sides=6, mat=BAR_HI)
    # Lower feather: a darker blade angled down to a point (rows 18-23).
    lib.pillow(bm, G, [(8, 18), (20.5, 17.6), (20.5, 22), (15, 22.2), (14.2, 23), (13.4, 24), (12.4, 23.2),
                       (11, 22), (10, 21), (9.8, 19.2), (8.2, 19)], -0.06, 0.03, round_px=0.6, mat=LOWER)
    lib.sweep(bm, G, [(8.3, 18.45, 0.01, 0.0, 0.0), (9.0, 18.45, 0.015, 0.5, 0.02), (12.5, 18.5, 0.02, 0.5, 0.02),
                      (14.0, 18.6, 0.015, 0.0, 0.0)], sides=6, mat=LOWER_HI)
    # Grey blade standing beside the horn (columns 19-22, rows 1-8).
    lib.sweep(bm, G, [(21.0, 0.6, 0.06, 0.0, 0.0), (21.0, 1.5, 0.07, 0.8, 0.05), (20.8, 3.5, 0.08, 1.4, 0.06),
                      (21.4, 6.0, 0.07, 1.2, 0.055), (22.1, 8.4, 0.05, 0.6, 0.04), (22.3, 9.0, 0.05, 0.0, 0.0)],
              sides=8, mat=BLADE)
    # Horn: from its point at the top (column 18, row 2) curving down and in to the band beside
    # the spine (columns 20-22), which runs off the bottom.
    lib.sweep(bm, G, [(18.2, 1.4, 0.08, 0.0, 0.0), (18.1, 2.6, 0.1, 0.8, 0.05), (18.2, 4.5, 0.12, 1.3, 0.07),
                      (18.7, 7.0, 0.13, 1.5, 0.08), (19.8, 9.5, 0.12, 1.4, 0.075), (21.0, 11.8, 0.11, 1.0, 0.06),
                      (21.2, 14.0, 0.1, 0.8, 0.05), (21.1, 17.0, 0.11, 1.0, 0.055), (21.2, 28.0, 0.12, 1.2, 0.06)],
              sides=10, mat=HORN)
    lib.sweep(bm, G, [(18.1, 2.4, 0.15, 0.0, 0.0), (18.1, 3.2, 0.16, 0.5, 0.025), (18.6, 6.5, 0.2, 0.6, 0.03),
                      (19.4, 8.0, 0.2, 0.0, 0.0)], sides=6, mat=SHINE)
    # Top of the blue body across the bottom (rows 21-28), rounded over its top edge.
    lib.pillow(bm, G, [(12.6, 28), (12.6, 25), (13.6, 24.2), (14, 22.2), (17.5, 21.6), (19.8, 18.5), (20.5, 17),
                       (24.5, 17), (24.5, 28)], -0.12, 0.1, round_px=1.6, round_h=0.55, mat=BODY)
    lib.sweep(bm, G, [(13.8, 25.2, 0.1, 0.0, 0.0), (14.5, 25.2, 0.1, 0.8, 0.03), (17.5, 25.2, 0.1, 0.8, 0.03),
                      (18.3, 25.2, 0.1, 0.0, 0.0)], sides=6, mat=BODY_HI)

    lib.mirror_x(bm, AX, set())

    # ---- centre ----
    # The spine down the middle (column 24, rows 5-28), widening into the neck at row 17.
    lib.loft_y(bm, G, 24, [(4.5, 0.0, 0.0, 0.08), (5.0, 0.8, 0.04, 0.08), (8.0, 0.9, 0.05, 0.08),
                           (13.0, 1.0, 0.05, 0.08), (15.5, 1.3, 0.06, 0.08), (18.0, 2.4, 0.09, 0.07),
                           (21.0, 2.6, 0.1, 0.07), (28.0, 2.6, 0.1, 0.07)], sides=10, mat=SPINE)
    # Dark slots either side of the spine, between it and the horns (columns 22-26, rows 3-18).
    lib.plate(bm, G, [(22, 3.5), (27, 3.5), (27, 18.5), (22, 18.5)], -0.1, -0.03, mat=SLOT)
    return lib.to_object(NAME, bm, m.list, coll)


def composite_png(out):
    """Both pieces' sprites as one image, padded to the 24:28 shape render_preview wants for
    size 4 (48 x 56 px, the object in the middle)."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for k, name in enumerate(PIECES):
        data = common.load_sprite(ROOT, name)
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[14 + r, 24 * k + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    data = {name: common.load_sprite(ROOT, name) for name in PIECES}
    obj = build(lib.merged_colors(ROOT, PIECES))
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in data[PIECES[0]]["assemblyLayout"]]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data[name]["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            img = ROOT / "reference" / "models" / name / data[name]["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
