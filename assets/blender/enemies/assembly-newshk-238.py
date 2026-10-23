"""The V ship pulled apart (newshk.shp frames 238 + 242, two pieces): a 3D version of its sprites.

Seen in episode 3 (level 3.12). newshk-207's two halves side by side, 24 px apart, each with a
ribbed red rod reaching from the bowl's inner wall towards the other half (they don't quite
meet). The left half is newshk-207's own half; the right half is its mirror image about the gap
(column edge 24.5 of the left piece), so its outermost column falls outside its block and is cut
off, as in the sprite.

Built whole in assembly coordinates (the left piece's centre is the origin) and cut into the two
pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshk-238.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b045 as lib  # noqa: E402
from lib_b045 import U, common, ex, ey  # noqa: E402

NAME = "assembly-newshk-238"
ROOT = common.repo_root(__file__)
PIECES = ["newshk-238", "newshk-242"]
AXIS = ex(24.5)  # the mirror plane between the halves, in the left piece's coordinates


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = lib.v_ship_materials(sprite, "nshk238")
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshk238", **kw)  # noqa: E731
    mats += [pal(115, metallic=0.4, roughness=0.45), pal(120, metallic=0.5, roughness=0.3),
             pal(113, metallic=0.4, roughness=0.5)]
    CORE, RIB, BRACKET = range(len(mats) - 3, len(mats))
    bm = bmesh.new()
    lib.v_ship_half(bm, 0.0, inner_edge=13.0, wall=True)

    # Red bracket on the bowl's inner wall (columns 12-14, rows 16-17) holding the rod.
    lib.box(bm, ex(12.6), ey(18.2), ex(15), ey(15.8), -0.04, 0.12, BRACKET, top_mat=RIB)
    # The ribbed rod (columns 14-22, rows 17-23 across its ribs, 18-22 across its core).
    sections, band_mats = [], []
    for c in range(14, 23):
        rib = (c - 14) % 2 == 0
        r = (3.5 if rib else 2.5) * U
        sections += [(ex(c), r, r * 0.45), (ex(c + 1), r, r * 0.45)]
        band_mats += [RIB if rib else CORE, CORE]
    band_mats = band_mats[:-1]
    f0 = len(bm.faces)
    lib.loft_x(bm, sections, ey(20.5), 0.03, sides=12, mat_index=band_mats)
    lib.set_smooth(bm, f0)

    lib.mirror_x(bm, 0, axis=AXIS)
    return lib.mesh_object_mixed(NAME, bm, mats, coll)


def composite_png(layout, out):
    """Both pieces' sprites as one image, padded to the 24:28 shape render_preview expects."""
    import numpy as np
    W = 48
    H = 56
    img = np.zeros((H, W, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        for r, line in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(line):
                if v >= 0:
                    img[14 + cy + r, cx + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = lib.merged_colors(ROOT, PIECES)
    obj = build(sprite)
    first = common.load_sprite(ROOT, PIECES[0])
    cx0, cy0 = first["assemblyLayout"][0]["cx"], first["assemblyLayout"][0]["cy"]
    layout = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in first["assemblyLayout"]]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png")
        # Show the whole object centred: move it so the middle of the two pieces is the origin.
        obj.location.x = -AXIS + 0.5 * U
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        obj.location.x = 0
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
