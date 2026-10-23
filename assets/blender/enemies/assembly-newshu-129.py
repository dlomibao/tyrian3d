"""Glass orb (newshu.shp, four 2x2 pieces: newshu-91, -93 top, newshu-129, -131 bottom): a 3D
version of its sprites, built whole and cut into the four pieces.

Seen in episode 1 (level section 19), episode 3 and episode 4. A big glass ball with green
organic machinery inside: a large lumpy mass on the left with a glowing core, a small glowing bud
at the top, a lobe on the right, a lamp at the lower right fed by a vein, ribs curving round the
bottom and a raised rim around the lower-right edge. The animation changes its whole colour,
not its shape, so each piece gets three models that share the geometry:

- <piece>: dim grey glass (the first frame and the last frame of the fade),
- <piece>-f2: glowing green (lit up, and the first fade steps, which are still mostly green),
- <piece>-f3: a closed, smooth purple shell (one frame).

Run: blender --background --python assets/blender/enemies/assembly-newshu-129.py [-- --preview out.png]
(the preview shows the whole orb; out-f2.png and out-f3.png show the green and purple states).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b005 as lib  # noqa: E402

NAME = "assembly-newshu-129"
ROOT = common.repo_root(__file__)
W, H = 48, 56  # the four pieces' 2x2 block, in sprite px
# Each piece's centre relative to the block's centre, in screen px (sprite.json assemblyLayout:
# newshu-91 at (225, 75), -93 at (249, 75), -129 at (225, 103), -131 at (249, 103)).
PIECES = [("newshu-91", -12, -14), ("newshu-93", 12, -14), ("newshu-129", -12, 14), ("newshu-131", 12, 14)]

SHELL, ORGAN, LOBE, CORE, RIB, LAMP, RIM = range(7)
# Palette index per part and state (grey/green indices correspond pixel for pixel in the sprites).
STATES = {
    "grey": {"suffix": "", "mats": {SHELL: (4, {}), ORGAN: (102, {}), LOBE: (104, {}),
                                    CORE: (141, {"emission_strength": 1.5}), RIB: (8, {}),
                                    LAMP: (55, {"emission_strength": 2.0}), RIM: (107, {})}},
    "green": {"suffix": "-f2", "mats": {SHELL: (38, {}), ORGAN: (195, {}), LOBE: (198, {"emission_strength": 1.0}),
                                        CORE: (206, {"emission_strength": 4.0}),
                                        RIB: (201, {"emission_strength": 2.5}),
                                        LAMP: (207, {"emission_strength": 4.0}),
                                        RIM: (200, {"emission_strength": 1.5})}},
    "purple": {"suffix": "-f3", "mats": {SHELL: (86, {}), RIM: (89, {})}},
}


def P(c, r):
    """Block column/row (pixel centre) to Blender XY."""
    return lib.grid_x(c, W), lib.grid_y(r, H)


def px(n):
    return n / 12


def classify(frame):
    """grey, green or purple by the colour families of a frame's pixels."""
    green = grey = purple = 0
    for row in frame["pixels"]:
        for v in row:
            if v < 0 or v == 1:
                continue
            if 192 <= v <= 207 or 32 <= v <= 43 or v == 55:
                green += 1
            elif 80 <= v <= 95:
                purple += 1
            else:
                grey += 1
    total = green + grey + purple
    if purple > 0.8 * total:
        return "purple"
    return "green" if green > 0.35 * total else "grey"


def build(state, palette):
    coll = common.reset_collection(f"{NAME}-{state}")
    spec = STATES[state]["mats"]
    tag = f"{NAME}-{state}"
    # Unused parts take the shell's material so slot indices stay fixed.
    mats = []
    for part in range(7):
        index, kw = spec.get(part, spec[SHELL])
        kw = dict(kw)
        if part == SHELL:
            kw.update(metallic=0.15, roughness=0.18)
        elif part == RIM:
            kw.setdefault("metallic", 0.5)
            kw.setdefault("roughness", 0.3)
        else:
            kw.setdefault("metallic", 0.1)
            kw.setdefault("roughness", 0.45)
        mats.append(common.palette_material(palette, index, tag, **kw))

    bm = bmesh.new()
    cx, cy = P(23, 27)
    dome = lib.Dome(px(23), 0.72, cx, cy)
    dome.build(bm, SHELL, segments=40, rings=20)

    # The raised rim round the lower-right edge (a bright crescent outside a dark groove).
    rim = [P(43.6, 32.5), P(42.2, 37.5), P(40, 41.5), P(37, 44.4), P(33, 46.6), P(28, 48.0), P(21.5, 48.5)]
    lib.surface_tube(bm, dome, rim, px(1.4), lift=px(0.5), mat_index=RIM, sides=6, samples=18, taper=0.2,
                     flat=0.8)

    if state != "purple":
        organs(bm, dome)
    return common.mesh_object(f"{NAME}-{state}", bm, mats, coll, smooth=True)


def organs(bm, dome):
    def lump(c, r, rx, ry, h, mat, angle=0.0, sides=16, rings=4):
        x, y = P(c, r)
        lib.patch(bm, dome, x, y, px(rx), px(ry), h, angle=angle, mat_index=mat, sides=sides, rings=rings)

    def vein(points, radius, mat, lift=0.02, samples=12):
        lib.surface_tube(bm, dome, [P(c, r) for c, r in points], px(radius), lift=lift, mat_index=mat,
                         sides=6, samples=samples, flat=0.7)

    # The big mass filling the left side, its band across the top and its lower lobe.
    lump(13.5, 21, 8, 12, 0.05, ORGAN)
    lump(19, 10.5, 7, 3, 0.05, ORGAN, sides=12, rings=3)
    lump(17, 31, 6.5, 2.6, 0.045, ORGAN, sides=12, rings=3)
    # Its lighter inner lobe and the glowing core (upper left).
    lump(14.2, 19.2, 6.4, 6.8, 0.1, LOBE)
    lump(16.8, 17.5, 4.2, 4.8, 0.14, CORE, sides=12, rings=3)
    # The bud at the top with its glowing tip.
    lump(23, 11.5, 3.2, 2.6, 0.08, LOBE, sides=12, rings=3)
    lump(23.4, 12, 1.6, 1.5, 0.11, CORE, sides=8, rings=2)
    # The lobe right of centre and the small one by the right edge.
    lump(27, 23, 4.5, 6.5, 0.05, ORGAN, sides=12, rings=3)
    lump(25.6, 22.5, 2.2, 4.0, 0.085, LOBE, sides=10, rings=3)
    lump(36.5, 24.5, 2.8, 3.5, 0.05, ORGAN, sides=10, rings=3)
    # The lamp at the lower right, on its own pad.
    lump(36, 36, 3.6, 3.6, 0.05, ORGAN, sides=12, rings=3)
    lump(36, 36, 2.4, 2.4, 0.1, LAMP, sides=10, rings=3)
    # The vein down from the right lobe.
    vein([(30.3, 27.5), (30.6, 31), (30.6, 35), (31, 38.5), (31, 41.5)], 1.1, RIB)
    # Ribs curving round the bottom.
    vein([(3.2, 29), (5.5, 32), (8.5, 35), (11.5, 37.3), (15.5, 38.4), (19.5, 37.4), (22.5, 35.6), (26, 35)], 1.3,
         RIB, samples=16)
    vein([(9.5, 40), (12.5, 42.3), (16.5, 43.8), (19.5, 42.6), (21.4, 40.5)], 1.2, RIB)
    vein([(21.5, 43.2), (24, 44.1), (27, 43.4)], 1.1, RIB, samples=8)


def main():
    sprites = {name: common.load_sprite(ROOT, name) for name, _, _ in PIECES}
    palette = {"name": NAME, "colors": {}}
    for s in sprites.values():
        palette["colors"].update(s["colors"])

    wholes = {}
    for state, info in STATES.items():
        whole = build(state, palette)
        wholes[state] = whole
        layout = [(name + info["suffix"], dx, dy) for name, dx, dy in PIECES]
        pieces = common.split_assembly(whole, layout)
        for name, _, _ in PIECES:
            sprite = sprites[name]
            frames = [f["index"] for f in sprite["frames"] if classify(f) == state]
            assert frames, f"{name} has no {state} frames"
            ref = sprite["sprites"][0]
            subset = [{"sheet": ref["sheet"], "size": ref["size"], "frames": frames}]
            common.export_sprite_model(ROOT, [pieces[name + info["suffix"]]], f"enemies/{name}{info['suffix']}",
                                       subset)

    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        for state, info in STATES.items():
            placed = []
            for name, dx, dy in PIECES:
                sprite = sprites[name]
                frame = next(f for f in sprite["frames"] if classify(f) == state)
                placed.append((frame["pixels"], sprite["colors"], W // 2 + dx - 12, H // 2 + dy - 14))
            ref = out.with_name(f"{out.stem}{info['suffix']}-sprite.png")
            lib.write_png(ref, lib.compose_pixels(placed, W, H, scale=6))
            common.render_preview([wholes[state]], str(out.with_name(f"{out.stem}{info['suffix']}.png")), ref, size=4)


if __name__ == "__main__":
    main()
