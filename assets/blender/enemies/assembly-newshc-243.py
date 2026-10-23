"""Big blue rifle (newshc.shp frames 239, 241, 243, assembly-newshc-243): a 3D version of its sprites.

Seen in episode 1 (level 1.19) and episode 3 (level 3.23). Three 2x2 enemies side by side make
one rifle lying across the screen, muzzle to the left (newshc-238, modelled by newshc-238.py, is
its muzzle tip): newshc-239 is the barrel with its collars, brackets and the glowing flash under
the muzzle; newshc-241 the receiver with a raised sight box, the grip and magazine and the purple
plate they hang over; newshc-243 the grey canister over the ribbed stock. Each piece is a single
frame.

The rifle is built once in assembly coordinates (lib_b058.build_gun) and cut into the pieces with
common.split_assembly, so they line up.

Run: blender --background --python assets/blender/enemies/assembly-newshc-243.py [-- --preview out.png]
(the preview is the whole rifle with its muzzle tile; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b058 as lib  # noqa: E402

NAME = "assembly-newshc-243"
ROOT = common.repo_root(__file__)


def main():
    obj = lib.build_gun(NAME)
    pieces = common.split_assembly(obj, lib.layout())
    for name in lib.PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=8, view_px=640)
        for name in lib.PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
