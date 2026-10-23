"""Side gun (newshv.shp frames 44 + 46, a two-piece assembly): a 3D version of its sprites.

Seen in episode 2 (level 2.12). Two 2x2 enemies side by side (sprite.json `assemblyLayout`)
make one 48 x 28 px gun pointing right: newshv-44 is its back, a red glowing engine pod, a
ribbed upper tube over a flat lower block and a keel; newshv-46 is its barrel, which hooks down
at the end over a jaw with a row of red lights. assembly-newshv-85 is its mirror image.

The whole gun is built once (lib_b043.gun) in assembly coordinates, then cut into the two pieces
with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshv-44.py [-- --preview out.png]
(the preview is the whole gun; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b043 as lib  # noqa: E402

NAME = "assembly-newshv-44"
ROOT = common.repo_root(__file__)
PIECES = ["newshv-44", "newshv-46"]
W, H = 48, 28  # the assembly in px; its centre is the Blender origin
MIRROR = False


def layout():
    """Each piece's centre relative to the assembly's centre, in px."""
    data = common.load_sprite(ROOT, PIECES[0])
    entries = [e for e in data["assemblyLayout"] if e["model"] in PIECES]
    cx0 = sum(e["cx"] for e in entries) / len(entries)
    cy0 = sum(e["cy"] for e in entries) / len(entries)
    return [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in entries]


def build(sprite):
    coll = common.reset_collection(NAME)
    bm = bmesh.new()
    lib.gun(bm, lib.Grid(W, H))
    if MIRROR:
        for v in bm.verts:
            v.co.x = -v.co.x
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return lib.to_object(NAME, bm, lib.gun_materials(sprite, "nshv44"), coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    lay = layout()
    lib.silhouette_report(obj, lib.sprite_pixels(ROOT, lay, W, H), lib.Grid(W, H))
    pieces = common.split_assembly(obj, lay)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        out = Path(out)
        ref = lib.composite_png(ROOT, lay, Path(tempfile.mkdtemp()) / "assembly.png", W, 56)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
