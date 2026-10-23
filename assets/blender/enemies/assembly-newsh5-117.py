"""Grey bomber (newsh5.shp frames 115, 117, 119 side by side): a 3D version of its sprites.

Seen in episode 4 (levels 4.16 and 4.47). Three 2x2 enemies make one 72 x 28 px plane flying
down the screen: a round grey fuselage (newsh5-117) with a thin tail boom, a red tailplane and
dark slots in its nose, and a long straight wing whose inner half carries a red spar along its
leading edge. Two red bands mark where the wing meets the big grey engine pods at its tips
(newsh5-115 and newsh5-119), and little red and grey stubs stand out in front of and behind the
wing.

The plane is built once in the coordinates of the middle piece (mirrored about its pixel column
12, the plane's axis), then cut into the three pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-117.py [-- --preview out.png]
(the preview is the whole plane; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b037 as L  # noqa: E402

NAME = "assembly-newsh5-117"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-115", "newsh5-117", "newsh5-119"]
CX0, CY0 = 123, 15  # screen centre of newsh5-117, the Blender origin
PX = 1 / 12
E = L.EX  # pixel edge (columns of newsh5-117; newsh5-115 is 24 to the left) to X
R = L.EY  # pixel edge (rows) to Y
AX = L.X(12)  # the plane's axis, the centre of newsh5-117's column 12


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh5_117"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.35, roughness=0.4),  # 0 fuselage grey
        pal(9, metallic=0.35, roughness=0.35),  # 1 engine pods, light grey
        pal(5, metallic=0.3, roughness=0.45),  # 2 wing and pod roots, dark grey
        pal(2, metallic=0.2, roughness=0.8),  # 3 nose slots
        pal(11, metallic=0.7, roughness=0.25),  # 4 spine highlight
        pal(71, metallic=0.3, roughness=0.45),  # 5 red spar and bands
        pal(69, metallic=0.25, roughness=0.5),  # 6 darker red stubs
        pal(70, metallic=0.3, roughness=0.5),  # 7 red tailplane
    ]
    FUSE, POD, WING, SLOT, SPINE, RED, RED_DARK, TAIL = range(8)
    bm = bmesh.new()
    start = len(bm.verts)

    # ---- left half (mirrored about the axis below) ----

    # Engine pod: a fat tube across the screen (newsh5-115 columns 3-15, rows 10-17), its outer
    # end rounded; the light part outboard, a darker root next to the bands.
    yc = R(13.8)
    L.loft_x(bm, yc, [(E(-21.4), 0.0, 0.0, 0.0), (E(-21.0), 2.2 * PX, 0.12, 0.0), (E(-20.2), 3.4 * PX, 0.18, 0.0),
                      (E(-19.2), 3.9 * PX, 0.2, 0.0), (E(-12.0), 3.9 * PX, 0.2, 0.0)], sides=14, mat=POD)
    L.loft_x(bm, yc, [(E(-12.0), 3.9 * PX, 0.2, 0.0), (E(-7.0), 3.9 * PX, 0.2, 0.0)], sides=14, mat=WING)
    # Two red bands round the pod's root (columns 16 and 18).
    L.loft_x(bm, R(14.6), [(E(-8.0), 2.6 * PX, 0.21, 0.0), (E(-7.0), 2.6 * PX, 0.21, 0.0)], sides=14, mat=RED)
    L.loft_x(bm, R(13.0), [(E(-6.0), 4.1 * PX, 0.22, 0.0), (E(-5.0), 4.1 * PX, 0.22, 0.0)], sides=14, mat=RED)

    # Inner wing out to the bands (rows 10-17) with the red spar along its leading edge (rows 13-16).
    L.plate(bm, [(E(-7.0), R(17.8)), (AX, R(17.8)), (AX, R(9.8)), (E(-7.0), R(9.8))], -0.07, 0.07, mat=WING)
    L.loft_x(bm, R(15.0), [(E(-5.0), 2.0 * PX, 0.1, 0.02), (AX, 2.0 * PX, 0.1, 0.02)], sides=10, mat=RED)

    # Red stubs in front of and behind the wing: on the pod (columns 6-9) and next to the bands
    # (columns 19-21).
    for e0, e1, r0, r1 in ((-18.0, -14.0, 6.8, 10.5), (-18.0, -14.0, 17.5, 21.0),
                           (-5.0, -2.0, 5.8, 10.5), (-4.0, -2.0, 17.5, 20.0)):
        w = (e1 - e0) / 2 * PX
        L.loft_y(bm, E((e0 + e1) / 2), [(R(r0), w * 0.6, 0.05, 0.0), (R(r0 + 0.5), w, 0.08, 0.0),
                                        (R(r1 - 0.5), w, 0.08, 0.0), (R(r1), w * 0.6, 0.05, 0.0)],
                  sides=8, mat=RED_DARK)
    # Grey stubs (columns 14-17 and, on the fuselage piece, 1-3).
    for e0, e1, r0, r1 in ((-10.0, -6.0, 6.8, 10.0), (-10.0, -6.0, 17.5, 20.2),
                           (1.0, 4.0, 6.8, 10.0), (1.0, 4.0, 17.5, 20.0)):
        w = (e1 - e0) / 2 * PX
        L.loft_y(bm, E((e0 + e1) / 2), [(R(r0), w * 0.6, 0.05, 0.0), (R(r0 + 0.5), w, 0.07, 0.0),
                                        (R(r1 - 0.5), w, 0.07, 0.0), (R(r1), w * 0.6, 0.05, 0.0)],
                  sides=8, mat=WING)

    # Red tailplane (row 3, columns 8-10).
    L.plate(bm, [(E(8.0), R(4.0)), (AX, R(4.0)), (AX, R(3.0)), (E(8.0), R(3.0))], 0.04, 0.09, mat=TAIL)

    # Dark slots in the nose (columns 10 and 12, rows 18-23).
    for c, r0, r1 in ((10, 17.8, 23.0),):
        L.box(bm, L.X(c) - 0.45 * PX, R(r1), L.X(c) + 0.45 * PX, R(r0), 0.17, 0.235, mat=SLOT)

    L.mirror_since(bm, start, AX)

    # ---- centre parts ----

    # Fuselage (columns 9-15) from behind the wing to the rounded nose (row 26).
    L.loft_y(bm, AX, [(R(6.6), 0.0, 0.0, 0.07), (R(7.0), 2.0 * PX, 0.1, 0.06), (R(8.0), 3.4 * PX, 0.18, 0.05),
                      (R(9.5), 3.6 * PX, 0.22, 0.04), (R(18.0), 3.6 * PX, 0.22, 0.04), (R(22.0), 3.5 * PX, 0.2, 0.03),
                      (R(24.0), 2.9 * PX, 0.16, 0.03), (R(25.3), 1.8 * PX, 0.1, 0.03), (R(26.0), 0.0, 0.0, 0.03)],
              sides=14, mat=FUSE)
    # Light spine along its top.
    L.loft_y(bm, AX, [(R(8.2), 0.0, 0.0, 0.2), (R(9.0), 0.8 * PX, 0.05, 0.215), (R(17.5), 0.8 * PX, 0.05, 0.215),
                      (R(18.3), 0.0, 0.0, 0.2)], sides=8, mat=SPINE)
    # Centre nose slot.
    L.box(bm, AX - 0.45 * PX, R(23.0), AX + 0.45 * PX, R(18.8), 0.19, 0.25, mat=SLOT)
    # Tail boom (rows 1-7) with a bulge at row 4 and a small fin on top.
    L.loft_y(bm, AX, [(R(0.8), 0.0, 0.0, 0.07), (R(1.2), 1.3 * PX, 0.06, 0.07), (R(3.5), 1.5 * PX, 0.07, 0.07),
                      (R(4.2), 2.4 * PX, 0.09, 0.07), (R(5.0), 1.5 * PX, 0.07, 0.07), (R(7.5), 1.6 * PX, 0.08, 0.07)],
              sides=10, mat=FUSE)
    L.plate(bm, [(AX - 0.35 * PX, R(5.5)), (AX + 0.35 * PX, R(5.5)), (AX + 0.35 * PX, R(1.2)),
                 (AX - 0.35 * PX, R(1.2))], 0.1, 0.2, mat=SPINE)

    return L.to_object(NAME, bm, mats, coll)


def composite_png(layout, out):
    """The whole plane's sprite (first frames) as one image, padded to the 24:28 shape that
    render_preview expects for size 6 (72 x 84 px, the plane in the middle)."""
    import numpy as np
    W, H = 72, 84
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


def main():
    sprite = L.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=6, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
