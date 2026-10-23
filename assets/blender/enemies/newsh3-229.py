"""Molten fireball (newsh3.shp frames 229, 231, 233, 235): a 3D version of its sprite.

Seen through episode 4. A ball of dark red crust split by glowing orange and yellow cracks, which
shrinks over its four frames (23, 19, 17 and 13 px across). Each size is its own model (newsh3-229,
-f2, -f3, -f4). Each is a squashed sphere whose top follows the sprite's pixels: the dark crust
stands a little proud and the glowing cracks sit in grooves between the plates.

Run: blender --background --python assets/blender/enemies/newsh3-229.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b052 as lib  # noqa: E402
from lib_b052 import P, X, Y  # noqa: E402

NAME = "newsh3-229"
ROOT = common.repo_root(__file__)
OUTLINE = (254,)

# Palette ramp groups: (highest index in the group, material slot), dark crust to white hot.
GROUPS = [(115, 0), (118, 1), (120, 2), (123, 3), (255, 4)]
# Relief per slot in px: crust plates stand proud, the glowing cracks sit in grooves.
RELIEF = [0.9, 0.6, 0.1, -0.5, -0.7]


def slot_of(i):
    for top, slot in GROUPS:
        if i <= top:
            return slot
    return 4


def ball_mesh(bm, pixels):
    """The ball for one frame: the sprite's pixels draped over a squashed sphere, each a face in
    its pixel's colour, raised or sunk by how hot it is. The underside is a plain dome."""
    filled = [(c, r) for r, line in enumerate(pixels) for c, v in enumerate(line) if v >= 0]
    c0, c1 = min(c for c, _ in filled), max(c for c, _ in filled) + 1
    r0, r1 = min(r for _, r in filled), max(r for _, r in filled) + 1
    cx, cy = (c0 + c1) / 2, (r0 + r1) / 2
    R = (c1 - c0) / 2 - 1.0  # leave the outline ring out
    height = P(R) * 0.34

    cells = {}
    for r, line in enumerate(pixels):
        for c, v in enumerate(line):
            if v < 0 or v in OUTLINE:
                continue
            if math.hypot(c + 0.5 - cx, r + 0.5 - cy) <= R + 0.15:
                cells[(c, r)] = slot_of(v)

    # Corners on the edge of the cell set go to the rim (z = 0) so the two halves close.
    count = {}
    for c, r in cells:
        for e in (((c, r), (c + 1, r)), ((c + 1, r), (c + 1, r + 1)), ((c, r + 1), (c + 1, r + 1)),
                  ((c, r), (c, r + 1))):
            count[e] = count.get(e, 0) + 1
    rim = {p for e, n in count.items() if n == 1 for p in e}

    top, bottom = {}, {}

    def place(c, r):
        dx, dy = c - cx, r - cy
        d = math.hypot(dx, dy)
        if (c, r) in rim or d >= R:
            k = R / d if d else 0.0
            return cx + dx * k, cy + dy * k, None
        return c, r, math.sqrt(1 - (d / R) ** 2)

    def vert(c, r, under):
        store = bottom if under else top
        if (c, r) in store:
            return store[(c, r)]
        x, y, s = place(c, r)
        if s is None:  # rim: shared by both halves
            v = top.get((c, r)) or bottom.get((c, r)) or bm.verts.new((X(x), Y(y), 0.0))
        elif under:
            v = bm.verts.new((X(x), Y(y), -s * height))
        else:
            around = [cells[p] for p in ((c - 1, r - 1), (c, r - 1), (c - 1, r), (c, r)) if p in cells]
            relief = sum(RELIEF[a] for a in around) / len(around)
            v = bm.verts.new((X(x), Y(y), s * height + P(relief) * min(1.0, s * 2.0)))
        store[(c, r)] = v
        return v

    for (c, r), slot in cells.items():
        quad = _dedupe([vert(c, r, False), vert(c, r + 1, False), vert(c + 1, r + 1, False), vert(c + 1, r, False)])
        if len(quad) >= 3:
            bm.faces.new(quad).material_index = slot
        quad = _dedupe([vert(c, r, True), vert(c + 1, r, True), vert(c + 1, r + 1, True), vert(c, r + 1, True)])
        if len(quad) >= 3:
            bm.faces.new(quad).material_index = 1  # underside: red crust


def _dedupe(vs):
    out = []
    for v in vs:
        if v not in out:
            out.append(v)
    return out


def build(sprite, name, frame):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, name, **kw)  # noqa: E731
    mats = [
        pal(114, metallic=0.1, roughness=0.85),  # 0 dark crust
        pal(117, metallic=0.1, roughness=0.75, emission_strength=0.6),  # 1 red crust
        pal(119, roughness=0.5, emission_strength=2.0),  # 2 hot red
        pal(122, roughness=0.4, emission_strength=3.5),  # 3 orange cracks
        pal(125, roughness=0.3, emission_strength=5.0),  # 4 yellow, the hottest
    ]
    bm = bmesh.new()
    ball_mesh(bm, frame["pixels"])
    return common.mesh_object(name, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    base = sprite["sprites"][0]
    for i, frame in enumerate(sprite["frames"]):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, name, frame)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", [{**base, "frames": [frame["index"]]}])
        if "--preview" in sys.argv:
            out = Path(sys.argv[sys.argv.index("--preview") + 1])
            ref = ROOT / "reference" / "models" / NAME / frame["image"]
            common.render_preview([obj], out.with_name(f"{name}.png"), ref, size=2)


if __name__ == "__main__":
    main()
