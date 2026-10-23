"""Rock bunker hatch (newshg.shp, assembly of newshg-153 over newshg-191): a 3D version of its sprites.

Seen in episode 2 (levels 2.2, 2.21, 2.22 and 2.24), a pair on each side of a waterfall. Two 2x2
pieces stacked make one 24x56 px structure: grey cliff boulders split by a dark crevice (the top
piece), a steel hatch housing set into the foot of the cliff between two rock pillars, and grass
with a half-buried boulder below it (the bottom piece). The hatch's shutter rises and fire
glows in the pit behind it as something is launched, so the frames change shape:

- newshg-153 (frames 153, 155): shutter closed. newshg-153-f2 (157): shutter lifting, a bar
  half way up. newshg-153-f3 (159): bar near the top, fire below. newshg-153-f4 (161): shutter
  up under the lintel, bright fire.
- newshg-191 (191): the shutter's lower edge closed on the sill. newshg-191-f2 (193): open and
  dark. newshg-191-f3 (195, 197, 199): open with fire glowing at the pit's mouth.

The whole structure is built for each state in assembly coordinates, painted from that state's
sprite frames, and cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshg-191.py [-- --preview out.png]
(the preview is the whole structure, closed; each exported model also gets <model>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b077 as L  # noqa: E402

NAME = "assembly-newshg-191"
ROOT = common.repo_root(__file__)
TOP, BOTTOM = "newshg-153", "newshg-191"
G = L.Grid(24, 56)  # assembly pixels: newshg-153 is rows 0-27, newshg-191 rows 28-55
U = L.U
LAYOUT = [(TOP, 0, -14), (BOTTOM, 0, 14)]  # piece centres in pixels from the assembly centre

# Shutter states: (door top row, door bottom row, door height z, lip index, glow) in assembly
# pixel rows (edges); glow is None or (palette index, strength, rows from, rows to).
STATES = {
    "closed": (20.6, 31.0, 0.24, 4, None),
    "lifting": (20.6, 28.0, 0.25, 4, None),
    "half": (23.0, 26.0, 0.25, 5, (116, 2.5, 26.0, 31.0)),
    "high": (22.4, 24.0, 0.27, 8, (119, 3.5, 24.5, 31.0)),
    "up": (20.6, 23.0, 0.29, 9, (122, 5.0, 22.5, 31.0)),
}
# (model, piece, state, frame indices of that piece's sprite.json)
MODELS = [
    ("newshg-153", TOP, "closed", [0, 1]),
    ("newshg-153-f2", TOP, "half", [2]),
    ("newshg-153-f3", TOP, "high", [3]),
    ("newshg-153-f4", TOP, "up", [4]),
    ("newshg-191", BOTTOM, "closed", [0]),
    ("newshg-191-f2", BOTTOM, "lifting", [1]),
    ("newshg-191-f3", BOTTOM, "up", [2, 3, 4]),
]

GREYS = range(2, 13)
GREENS = set(range(32, 36)) | set(range(192, 200))


def build(tag, colors, pixels, state):
    """The whole structure in one shutter state, painted from `pixels` (24 x 56 palette rows)."""
    coll = common.reset_collection(tag)
    grid = L.Grid(24, 56, pixels, weight=lambda i: 1.8 if 194 <= i <= 199 else 1.0)
    M = L.Mats(tag, colors)

    def rock_slot(i):
        if i in GREYS:
            return M(i, metallic=0.05, roughness=0.85)
        if i in GREENS:
            return M(i, metallic=0.0, roughness=1.0)
        return None

    ROCK = M(5, metallic=0.05, roughness=0.85)
    STEEL = M(5, metallic=0.6, roughness=0.4)
    STEEL_LIT = M(7, metallic=0.6, roughness=0.35)
    STEEL_DARK = M(3, metallic=0.5, roughness=0.45)
    PIT = M(2, metallic=0.2, roughness=0.8)
    bm = bmesh.new()
    X, Y, EX, EY = G.x, G.y, G.ex, G.ey

    noise = L.noise2(5, 0.035)

    def height(c, r):
        """The ground: cliff boulders above the housing, rock pillars beside it, grass below."""
        z = max(
            0.26 if r < 18.0 else 0.0,  # rock floor of the cliff (the crevice bottom)
            L.mound(c, r, 6.0, 3.0, 9.5, 7.5, 0.6),  # left boulder, lit along its lower edge
            L.mound(c, r, 19.5, 2.5, 7.0, 7.5, 0.6),  # right boulder
            L.mound(c, r, 15.0, 2.5, 2.4, 3.0, 0.44),  # lit knob at the top of the crevice
            L.mound(c, r, 7.5, 11.0, 6.5, 5.0, 0.48),  # block under the left boulder
            L.mound(c, r, 21.5, 12.0, 4.5, 8.0, 0.48),  # right rock face beside the crevice
            L.mound(c, r, 7.0, 16.0, 9.0, 3.0, 0.36),  # ledge over the housing
            L.mound(c, r, 0.5, 26.0, 3.8, 11.0, 0.42, 0.3),  # left pillar
            L.mound(c, r, 22.6, 27.0, 4.2, 15.0, 0.44, 0.3),  # right pillar
            L.mound(c, r, 0.4, 36.0, 1.8, 5.0, 0.2),  # the left pillar's foot
            L.mound(c, r, 4.6, 36.5, 4.8, 4.8, 0.17),  # boulder half hidden in the grass
            L.mound(c, r, 17.0, 36.0, 3.5, 4.0, 0.08),  # dark rocks in the housing's shadow
            0.035,  # grass
        )
        if z > 0.06:
            z += noise(c, r)
        if 3.0 <= c <= 19.6 and 17.6 <= r <= 32.0:
            z = 0.03  # under the housing
        return z

    L.terrain(bm, grid, 0, 0, 24, 56, height, rock_slot, cell=2.0)
    L.tufts(bm, grid, 0, 32, 24, 56, lambda i: i >= 196 and i in GREENS, rock_slot, height, seed=11)

    # ---- the hatch housing (rows 18-31, columns 3-19) ----
    top = 0.32
    L.box(bm, EX(3), EY(20.5), EX(19.6), EY(17.6), 0.0, top, mat_index=STEEL)  # lintel
    L.box(bm, EX(3.2), EY(20.0), EX(19.2), EY(18.9), top, top + 0.02, mat_index=STEEL_LIT)  # lit lip (row 19)
    L.box(bm, EX(3), EY(31.0), EX(4.5), EY(20.5), 0.0, top, mat_index=STEEL_LIT)  # left post
    L.box(bm, EX(18.5), EY(31.0), EX(19.6), EY(20.5), 0.0, top, mat_index=STEEL_DARK)  # right post
    L.box(bm, EX(3), EY(32.0), EX(19.6), EY(31.0), 0.0, top * 0.6, mat_index=STEEL)  # sill (row 31)
    L.box(bm, EX(4.5), EY(31.0), EX(18.5), EY(20.5), 0.0, 0.03, mat_index=PIT)  # pit floor
    # Bolts on the ledge (row 15) and in the lintel corners.
    for c in (6, 13, 17):
        L.blob(bm, (X(c), Y(15.2), 0.3), (0.7 * U, 0.7 * U, 0.05), segments=6, rings=3, mat_index=STEEL_LIT)

    # Shutter: a panel across the opening between its top and bottom rows, with a lit lower lip.
    d0, d1, dz, lip, glow = STATES[state]
    L.box(bm, EX(4.6), EY(d1), EX(18.4), EY(d0), dz - 0.03, dz, mat_index=STEEL_DARK)
    lip_rows = 1.0 if d1 - d0 > 2 else (d1 - d0) * 0.6
    L.box(bm, EX(4.6), EY(d1), EX(18.4), EY(d1 - lip_rows), dz - 0.035, dz + 0.012, mat_index=M(lip, metallic=0.6,
                                                                                               roughness=0.35))
    # Fire glowing in the pit below the shutter.
    if glow:
        index, strength, g0, g1 = glow
        M_glow = M(index, emission_strength=strength)
        cy = (g0 + g1) / 2 + 1.0
        L.blob(bm, (X(11.3), Y(cy), 0.03), (4.6 * U, (g1 - g0) / 2 * U, 0.12), segments=12, rings=6, mat_index=M_glow)
        L.blob(bm, (X(11.3), Y(cy + 0.8), 0.05), (2.2 * U, (g1 - g0) / 4 * U, 0.14), segments=10, rings=5,
               mat_index=M(126 if 126 in [int(k) for k in colors] else index, emission_strength=strength + 1))

    obj = L.to_object(tag, bm, M.list, coll)
    return obj


def frame_pixels(name, index):
    return common.load_sprite(ROOT, name)["frames"][index]["pixels"]


def main():
    top, bottom = common.load_sprite(ROOT, TOP), common.load_sprite(ROOT, BOTTOM)
    colors = L.merged_colors([top, bottom])
    out = L.preview_arg()
    built = {}
    for model, piece, state, frames in MODELS:
        data = top if piece == TOP else bottom
        ti = frames[0] if piece == TOP else 0
        bi = frames[0] if piece == BOTTOM else 0
        pixels = top["frames"][ti]["pixels"] + bottom["frames"][bi]["pixels"]
        obj = build(f"{model}_whole", colors, pixels, state)
        pieces = common.split_assembly(obj, [(p, cx, cy) for p, cx, cy in LAYOUT])
        frame_numbers = [data["sprites"][0]["frames"][i] for i in frames]
        common.export_sprite_model(ROOT, [pieces[piece]], f"enemies/{model}",
                                   L.frames_subset(data["sprites"], frame_numbers))
        built[model] = (obj, pieces[piece], data, frames[0])
    if out:
        import tempfile
        ref = L.composite_png([(top, 0, 12, 0), (bottom, 0, 12, 28)], 48, 56, Path(tempfile.mkdtemp()) / "a.png")
        whole = built["newshg-153"][0]
        common.render_preview([whole], str(out), ref, size=4, view_px=480)
        for model, (_, piece_obj, data, fi) in built.items():
            img = ROOT / "reference" / "models" / data["name"] / data["frames"][fi]["image"]
            common.render_preview([piece_obj], str(out.parent / f"{model}.png"), img, size=2)


if __name__ == "__main__":
    main()
