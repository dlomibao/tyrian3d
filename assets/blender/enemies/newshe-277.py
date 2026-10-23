"""Three glowing red eggs (newshe.shp frames 277, 279, 281, 283): a 3D version of its sprites.

A ground object: three identical eggs, each round at the back and narrowing to the front, red
with a white-hot core in its back left and an orange glow along its front right edge. The four
frames turn the group of three round its centre, so each frame is its own model (newshe-277,
-f2, -f3, -f4); the eggs themselves are the same in all of them.

Run: blender --background --python assets/blender/enemies/newshe-277.py [-- --preview out.png]
(the preview is frame 277; the other frames get <out>-f2.png ... next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b070 as lib  # noqa: E402

NAME = "newshe-277"
ROOT = common.repo_root(__file__)
# Top-left corner (col, row) of each egg's 9 x 12 px box in each frame (found by matching the egg
# in the frame's pixels; the three of them cover every pixel of each frame).
EGGS = {
    277: [(2, 4), (14, 4), (8, 15)],
    279: [(4, 2), (15, 8), (5, 14)],
    281: [(8, 0), (2, 12), (14, 12)],
    283: [(12, 2), (1, 8), (11, 14)],
}
# The egg's outline, back to front: (row edge from the box's top, half width px).
K = 0.55  # egg height per unit of width
Z = 0.23  # height of the egg's middle
EGG = [(0.0, 0.0), (0.15, 2.0), (0.6, 2.9), (1.5, 3.9), (2.6, 4.5), (4.5, 4.6), (6.6, 4.4),
       (7.6, 3.8), (9.0, 3.0), (10.4, 2.4), (11.5, 1.5), (12.0, 0.0)]


def build(sprite, frame_index, name):
    coll = common.reset_collection(name)
    frame = sprite["frames"][frame_index]
    grid = lib.Grid(24, 28, frame["pixels"])
    mats = lib.Mats(name, sprite["colors"])
    RIM = mats(114, metallic=0.3, roughness=0.45)
    SHELL = mats(116, metallic=0.3, roughness=0.4, emission_strength=0.6)
    WARM = mats(119, emission_strength=2.0)
    GLOW = mats(122, emission_strength=3.0)
    CORE = mats(127, emission_strength=5.0)
    bm = bmesh.new()

    def half(e):
        """The egg's half width (px) at row edge e of its box."""
        for (e0, w0), (e1, w1) in zip(EGG, EGG[1:]):
            if e0 <= e <= e1:
                return w0 + (w1 - w0) * (e - e0) / (e1 - e0)
        return 0.0

    def top(dc, e):
        """Height of the egg's top at dc px right of its middle, row edge e."""
        hw = half(e)
        if hw <= abs(dc):
            return Z
        return Z + (hw / 12 * K + 0.02) * (1 - (dc / hw) ** 2) ** 0.5

    for c0, r0 in EGGS[sprite["sprites"][0]["frames"][frame_index]]:
        x = grid.x(c0 + 4)
        sections = [((14 - (r0 + e)) / 12, hw / 12, hw / 12 * K + (0.02 if hw else 0.0), Z if hw else Z - 0.015)
                    for e, hw in EGG]
        start, first = len(bm.verts), len(bm.faces)
        common.loft(bm, sections, sides=16, mat_index=SHELL)
        common.shift_x(bm, start, x)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[first:]:
            f.smooth = True
        # The darker rim round its back and sides.
        lib.paint(bm, first, grid, lambda v: RIM if v <= 114 else None, up_only=False)
        # The white-hot core in its back left (box col 3, row 4) in a warm halo.
        cx, cy = grid.x(c0 + 3), grid.y(r0 + 3.9)
        for r, h, slot in ((3.2, 0.03, WARM), (2.3, 0.05, GLOW), (1.4, 0.07, CORE)):
            lib.dome(bm, (cx, cy, top(-1, 4.4) - 0.04), (r / 12, r / 12 * 1.05, h + 0.04), segments=14,
                     rings=3, mat_index=slot, base=False)
        # The orange glow along its front right edge.
        path = [(3.6, 5.0), (3.4, 6.4), (2.7, 7.8), (1.8, 9.0), (0.8, 10.0), (0.0, 10.8)]
        lib.tube(bm, [((x + dc / 12, (14 - (r0 + e)) / 12, top(dc, e) - 0.015), 0.85 / 12)
                      for dc, e in path], sides=6, mat_index=GLOW)

    return lib.to_object(name, bm, mats.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    sheet = sprite["sprites"][0]
    for i, frame_no in enumerate(sheet["frames"]):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, i, name)
        sprites = [{**sheet, "frames": [frame_no]}]
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", sprites)
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            if i:
                out = out.with_name(f"{out.stem}-f{i + 1}{out.suffix}")
            ref = ROOT / "reference" / "models" / NAME / sprite["frames"][i]["image"]
            common.render_preview([obj], str(out), ref, size=2)


if __name__ == "__main__":
    main()
