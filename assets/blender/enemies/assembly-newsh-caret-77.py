"""Rock wall clamp (newsh^.shp 77, 79, 81 over 115, 7, 119): a 3D version of its sprites.

Seen in episode 4 (level 4.2). Six 2x2 pieces make a 72x54 px stretch of the sandy rock wall
(the same wall as newsh3 166-208, which it joins end to end) with a grey machine clamped on it:
a housing in the middle with an upright lug on top, a D-shaped grab handle on each side, a dark
spider leg on each side gripping the rock, and two curved pincers hanging below the wall. The
bottom middle piece (newsh^ 7, 9 and 117) has a blue electric arc between the pincer tips in
frames 7 and 9 and none in 117, so it gets two models: newsh-caret-7 (frames 7 and 9, with a
glowing bolt traced from each frame's arc, shown on its frame with common.frame_part) and
newsh-caret-7-f2 (frame 117, no arc).

The rock is lib_b017.wall_rock (as for the plain wall); the machine is lofted tubes and plates,
mirrored about pixel column 33. Built whole in assembly coordinates and cut into the pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh-caret-77.py [-- --preview out.png]
(the preview is the whole stretch with the arc; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b017 as lib  # noqa: E402

NAME = "assembly-newsh-caret-77"
ROOT = common.repo_root(__file__)
# Top-left pixel of each piece (no layout in the catalogue; the edges and the machine match up
# in this order, frame 7 for the bottom middle piece).
PLACEMENTS = [
    ("newsh-caret-77", 0, 0, 0), ("newsh-caret-79", 24, 0, 0), ("newsh-caret-81", 48, 0, 0),
    ("newsh-caret-115", 0, 28, 0), ("newsh-caret-7", 24, 28, 0), ("newsh-caret-119", 48, 28, 0),
]
AXIS = 33  # the machine is mirror symmetric about the centre of pixel column 33


def build(sheet):
    coll = common.reset_collection(NAME)
    mats = lib.Mats("nshc77", sheet.colors)
    pix = sheet.pix

    # Rock: the wall's own pixels plus what the machine covers on it (not the pincers below it).
    h, w = sheet.h, sheet.w
    mask = [[False] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            v = pix[r][c]
            if 16 <= v <= 31:
                mask[r][c] = True
            elif v >= 1 and v <= 15:
                mask[r][c] = r <= 33 or (r <= 38 and not 17 <= c <= 49)
    bm = bmesh.new()
    lib.wall_rock(bm, sheet, mats, mask, rock_index=lambda v: v if 16 <= v <= 31 else 21)

    X = lambda c: sheet.X(c + 0.5)  # noqa: E731  pixel centre column -> X
    Y = lambda r: sheet.Y(r + 0.5)  # noqa: E731
    P = lambda c, r, z: (X(c), Y(r), z)  # noqa: E731
    U = lib.U
    ax = X(AXIS)
    body = mats(6, metallic=0.6, roughness=0.35)
    plate = mats(8, metallic=0.65, roughness=0.3)
    light = mats(11, metallic=0.7, roughness=0.25)
    dark = mats(4, metallic=0.5, roughness=0.45)
    seam = mats(3, metallic=0.4, roughness=0.6)
    handle = mats(5, metallic=0.6, roughness=0.35)
    smooth = []

    # Housing: a plate over the middle of the clamp, narrowing down into the pincers' roots.
    half = [(33.5, 15.0), (24.5, 15.0), (20.5, 16.8), (18.0, 19.5), (17.5, 22.0), (20.0, 23.8),
            (23.0, 25.5), (25.0, 28.5), (27.5, 31.5), (30.5, 33.8), (33.5, 34.0)]
    outline = [(sheet.X(c), sheet.Y(r)) for c, r in half]
    outline += [(2 * ax - x, y) for x, y in reversed(outline[1:-1])]
    common.slab(bm, outline, 0.2, z=0.32, mat_index=body)
    inner = [(33.5, 16.6), (25.2, 16.6), (21.8, 18.2), (20.2, 20.4), (21.5, 22.4), (24.5, 24.4),
             (26.6, 27.6), (29.0, 30.6), (31.4, 32.4), (33.5, 32.6)]
    inner = [(sheet.X(c), sheet.Y(r)) for c, r in inner]
    inner += [(2 * ax - x, y) for x, y in reversed(inner[1:-1])]
    common.slab(bm, inner, 0.05, z=0.44, mat_index=plate)
    # The seam down its middle (rows 22-33).
    lib.tube(bm, [(P(AXIS + 0.5, 22.0, 0.465), 0.6 * U), (P(AXIS + 0.5, 33.0, 0.45), 0.6 * U)], sides=4,
             mat_index=seam)

    # Lug standing up from the housing's top (columns 29-37, rows 3-15), rounded at its top end.
    lug = [(P(AXIS, 16.0, 0.42), 4.6 * U), (P(AXIS, 7.0, 0.42), 4.6 * U), (P(AXIS, 4.6, 0.42), 3.9 * U),
           (P(AXIS, 3.4, 0.42), 2.4 * U), (P(AXIS, 2.9, 0.42), 0.0)]
    smooth += lib.tube(bm, lug, sides=12, mat_index=plate, flat=0.32)
    smooth += lib.tube(bm, [(P(AXIS, 15.0, 0.545), 0.0), (P(AXIS, 13.5, 0.55), 1.4 * U),
                            (P(AXIS, 7.5, 0.55), 1.4 * U), (P(AXIS, 6.0, 0.545), 0.0)],
                       sides=6, mat_index=light, flat=0.4)

    left = []
    # D-shaped grab handle: out of the rock at its top right, over and down the left side, back
    # into the housing.
    path = [(19.0, 6.0, 0.24), (17.0, 3.6, 0.4), (13.0, 2.9, 0.46), (10.0, 4.6, 0.46), (9.6, 9.0, 0.44),
            (9.8, 14.0, 0.42), (11.2, 17.6, 0.4), (14.5, 19.4, 0.38), (18.5, 19.8, 0.34)]
    left += lib.tube(bm, [(P(c, r, z), 1.8 * U) for c, r, z in path], sides=8, mat_index=handle)
    # Spider leg from the housing's side down to a foot on the rock.
    path = [(19.0, 21.2, 0.36), (16.4, 23.4, 0.38), (13.8, 26.2, 0.38), (11.4, 29.4, 0.36),
            (9.4, 32.6, 0.33), (7.6, 35.2, 0.3)]
    left += lib.tube(bm, [(P(c, r, z), 1.6 * U) for c, r, z in path], sides=8, mat_index=dark)
    left += lib.ellipsoid(bm, P(7.0, 35.6, 0.27), (3.6 * U, 2.0 * U, 0.07), mat_index=dark)
    # Pincer: from under the housing, curving down and in to its tip.
    path = [(27.5, 29.5, 0.34, 3.6), (24.0, 33.5, 0.32, 3.5), (21.5, 37.5, 0.3, 3.2), (20.8, 41.5, 0.29, 2.8),
            (21.2, 45.5, 0.28, 2.3), (22.4, 49.5, 0.27, 1.5), (23.5, 52.2, 0.27, 0.7), (24.0, 53.4, 0.27, 0.0)]
    left += lib.tube(bm, [(P(c, r, z), rad * U) for c, r, z, rad in path], sides=8, mat_index=plate, flat=0.6)
    smooth += left + lib.mirror_faces(bm, left, ax)

    return lib.to_object(NAME, bm, mats.list, coll, smooth_faces=smooth)


def arc(sheet, frame):
    """The electric arc between the pincer tips on one frame of the bottom middle piece (placed at
    column 24, row 28): a glowing bolt through the middle of the arc's pixels in each column
    (columns 24-42, rows 40-55 of the stretch), as thick as the arc is there."""
    coll = common.reset_collection(f"{NAME}_arc_{frame}")
    mats = lib.Mats("nshc77", sheet.colors)
    glow = mats(60, metallic=0.0, roughness=0.4, emission_strength=4.0)
    data = sheet.sprites["newsh-caret-7"]
    pixels = next(f["pixels"] for f in data["frames"] if f["index"] == frame)
    pix = lambda r, c: pixels[r - 28][c - 24]  # noqa: E731
    P = lambda c, r, z: (sheet.X(c + 0.5), sheet.Y(r + 0.5), z)  # noqa: E731
    pts = []
    for c in range(24, 43):
        rows = [r for r in range(40, 56) if 57 <= pix(r, c) <= 62]
        if rows:
            pts.append((c, sum(rows) / len(rows), max(rows) - min(rows) + 1))
    bolt = [(P(c, r, 0.28), max(0.9, min(1.7, n / 2.6)) * lib.U) for c, r, n in pts]
    bm = bmesh.new()
    smooth = lib.tube(bm, bolt, sides=6, mat_index=glow, flat=0.6)
    return lib.to_object(f"{NAME}_arc_{frame}", bm, mats.list, coll, smooth_faces=smooth)


def main():
    sheet = lib.Sheet(ROOT, PLACEMENTS)
    plain = build(sheet)
    pieces = lib.export_pieces(ROOT, plain, sheet, PLACEMENTS[:4] + PLACEMENTS[5:])
    # The bottom middle piece: with an arc per frame for frames 7 and 9, without it for frame 117.
    sprite = sheet.sprites["newsh-caret-7"]["sprites"][0]
    with_arc = [{**sprite, "frames": [7, 9]}]
    no_arc = [{**sprite, "frames": [117]}]
    centre = (24 + 12 - sheet.w / 2, 28 + 14 - sheet.h / 2)
    cut = {}
    for model, sprites in (("newsh-caret-7", with_arc), ("newsh-caret-7-f2", no_arc)):
        cut[model] = common.split_assembly(plain, [(model, *centre)])[model]
    arcs = {}
    for frame in (7, 9):
        name = f"newsh-caret-7-arc-{frame}"
        arcs[frame] = common.frame_part(common.split_assembly(arc(sheet, frame), [(name, *centre)])[name], [frame])
    for model, objs, sprites in (("newsh-caret-7", [cut["newsh-caret-7"], *arcs.values()], with_arc),
                                 ("newsh-caret-7-f2", [cut["newsh-caret-7-f2"]], no_arc)):
        common.export_sprite_model(ROOT, objs, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        lib.previews(ROOT, out, plain, pieces, sheet)
        f7 = ROOT / "reference" / "models" / "newsh-caret-7" / "frame-newsh-caret-7.png"
        common.render_preview([cut["newsh-caret-7"], arcs[7]], str(out.parent / "newsh-caret-7.png"), f7, size=2,
                              frame=7)
        f2 = ROOT / "reference" / "models" / "newsh-caret-7" / "frame-newsh-caret-117.png"
        common.render_preview([cut["newsh-caret-7-f2"]], str(out.parent / "newsh-caret-7-f2.png"), f2, size=2)


if __name__ == "__main__":
    main()
