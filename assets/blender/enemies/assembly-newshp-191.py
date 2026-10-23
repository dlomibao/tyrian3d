"""Sinking stone block (newshp.shp, assembly of 4 pieces): a 3D version of its sprites.

Seen in episode 1 (levels 1.6, 1.21), 2 and 3. Four 2x2 enemies side by side make one 48 x 56 px
ground structure (sprite.json `assemblyLayout`): a raised platform of grey dressed stones with
rounded corners (columns 4-42, rows 0-41), on rubbly ground with a lit ledge and a louvred apron
below it falling to a dark trench, the same ground as newshp-237's.

The pieces animate together in three steps that push three of the stones into the platform: a
big one in the upper middle (columns 12-25, rows 7-19), a narrow one on the right (columns 38-42,
rows 11-18) and one low in the middle (columns 20-32, rows 27-34). Each step is a different shape,
so every piece has three models: <piece> (stones flush), <piece>-f2 (stones a little sunk) and
<piece>-f3 (stones deep in their sockets).

The whole block is built once per step in assembly coordinates, then cut into the four pieces
with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshp-191.py [-- --preview out.png]
(the preview is the whole block in its first step; each piece model also gets <model>.png beside it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b067 as lib  # noqa: E402
from lib_b067 import common  # noqa: E402

NAME = "assembly-newshp-191"
ROOT = common.repo_root(__file__)
PIECES = ["newshp-153", "newshp-155", "newshp-191", "newshp-193"]
# Assembly pixel (0, 0) is screen (44, -4), the top-left of newshp-153; the block is 48 x 56 px and
# its centre (screen 68, 24) is the Blender origin.
CX0, CY0 = 68, 24
G = lib.Grid(48, 56)

# Stones of the platform: (c0, r0, c1, r1) inclusive pixel columns / rows, and which one sinks.
STONES = [
    (4, 0, 25, 5), (27, 0, 42, 9), (4, 7, 10, 19), (12, 7, 25, 19, "A"), (27, 11, 36, 14),
    (38, 11, 42, 18, "B"), (27, 16, 36, 25), (38, 20, 42, 25), (4, 21, 14, 29), (16, 21, 18, 41),
    (20, 21, 25, 25), (20, 27, 32, 34, "C"), (34, 27, 42, 41), (20, 36, 32, 41), (4, 31, 14, 41),
]
TOP = 0.32  # the platform's top
FLOOR = 0.18  # the floor of the grooves between the stones
# Per step: (height of the sinking stones' tops, their palette index).
STEPS = [(TOP, 9), (0.29, 8), (0.2, 6)]


def build(sprite, step):
    coll = common.reset_collection(f"{NAME}_{step}")
    m = lib.Mats(sprite, "nshp191")
    bm = bmesh.new()

    # Ground: the left and right rubble strips beside the platform, and below it the ledge, the
    # louvred apron and the trench (newshp-237's ground, stretched by six more louvres).
    lib.ground(bm, G, m, 0, 0, 48, 28)
    lib.rubble(bm, G, m, lib.LEFT_RUBBLE + [lib.LEDGE_STONE], 0, 0)
    lib.rubble(bm, G, m, lib.RIGHT_RUBBLE, 43, 0)
    lib.trench(bm, G, m, 43.5, 0, 45, 28)
    lib.terrain(bm, G, m, dc=0, dr=28, extra=6)

    # The platform: a block with rounded corners up to the groove floor, the stones on top.
    outline = lib.rounded_rect(G, 4, 0, 43, 42, 2.0, segs=3)
    lib.prism(bm, outline, 0.0, FLOOR, m[6], top=m[7])
    z_sunk, idx_sunk = STEPS[step]
    for stone in STONES:
        c0, r0, c1, r1 = stone[:4]
        z1, top = (z_sunk, idx_sunk) if len(stone) > 4 else (TOP, 9)
        lib.frustum(bm, G, c0, r0, c1 + 1, r1 + 1, FLOOR - 0.01, z1, m[top],
                    sides=(m[11], m[12], m[6], m[7]), inset=0.15)
    return lib.to_object(f"{NAME}_{step}", bm, m.list, coll)


def merged_sprite():
    """newshp-191's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshp-191")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(layout, out, step):
    """The whole block's sprite (frames of one step) as one 48 x 56 image."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for name, cx, cy in layout:
        data = common.load_sprite(ROOT, name)
        frame = data["frames"][step]
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
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for step in range(len(STEPS)):
        whole = build(sprite, step)
        pieces = common.split_assembly(whole, layout)
        suffix = "" if step == 0 else f"-f{step + 1}"
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            sprites = [{**s, "frames": [s["frames"][step]]} for s in data["sprites"]]
            model = f"{name}{suffix}"
            pieces[name].name = model
            common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{model}", sprites)
            if preview:
                img = ROOT / "reference" / "models" / name / data["frames"][step]["image"]
                common.render_preview([pieces[name]], str(preview.parent / f"{model}.png"), img, size=2)
        if preview:
            import tempfile
            ref = composite_png(layout, Path(tempfile.mkdtemp()) / "assembly.png", step)
            out = preview if step == 0 else preview.parent / f"{NAME}-f{step + 1}.png"
            common.render_preview([whole], str(out), ref, size=4, view_px=480)


if __name__ == "__main__":
    main()
