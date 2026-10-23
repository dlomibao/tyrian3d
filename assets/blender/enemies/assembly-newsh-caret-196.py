"""Giant red lips (newsh^.shp frames 196 and 208, an assembly of 2 pieces): a 3D version of
their sprites.

Seen in episode 4 (level 4.20). Two 2x2 enemies side by side make one 48x28 px pair of lips
(sprite.json `assemblyLayout`): a full upper lip with a cupid's bow and two peaks, a fuller lower
lip with a glossy highlight left of centre, and the dark mouth line between them running out to
pointed corners. The lips are symmetric about assembly pixel column 24.

Both lips are lofted along X from the sprite's own per-column top and bottom edges (so the top view
follows the outline), with round cross-sections that make them pout, and their faces take the
shade of the sprite pixel under them. The whole thing is built once in assembly coordinates and
cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh-caret-196.py
[-- --preview out.png] (the preview is the whole pair; each piece also gets <piece>.png).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b046 as lib  # noqa: E402

NAME = "assembly-newsh-caret-196"
ROOT = common.repo_root(__file__)
PIECES = ["newsh-caret-196", "newsh-caret-208"]
# Assembly grid 48 x 28 px: newsh-caret-196 is columns 0-23, newsh-caret-208 columns 24-47.
G = lib.Grid(48, 28)
LAYOUT = [("newsh-caret-196", -12, 0), ("newsh-caret-208", 12, 0)]  # piece centres, px from origin
AXIS = 24  # mirror axis: the centre of assembly column 24
OUTLINE = 16
RAMP = range(66, 76)  # the lips' reds, darkest to lightest


def runs(pixels):
    """Per column, the rows of the upper lip and of the lower lip: [(c, (top, bottom), (top, bottom) or None)]."""
    out = []
    for c in range(len(pixels[0])):
        found, cur = [], None
        for r in range(len(pixels)):
            ok = pixels[r][c] >= 0 and pixels[r][c] != OUTLINE
            if ok and cur is None:
                cur = [r, r]
            elif ok:
                cur[1] = r
            elif cur:
                found.append(tuple(cur))
                cur = None
        if cur:
            found.append(tuple(cur))
        if found:
            out.append((c, found[0], found[1] if len(found) > 1 else None))
    return out


def lip(bm, cols, edges, tips, zc, depth, max_hz, mat):
    """Loft one lip along X: edges[i] = (top row, bottom row) at column cols[i] (pixel rows, edges
    included); tips = ((col, row), (col, row)) for its pointed corners."""
    top = lib.smooth_profile([t - 0.5 for t, _ in edges])
    bot = lib.smooth_profile([b + 0.5 for _, b in edges])
    sections = [(G.X(tips[0][0]), G.Y(tips[0][1]), 0.0, 0.0, zc)]
    for c, t, b in zip(cols, top, bot):
        hy = (b - t) / 2 * lib.PX
        hz = min(max_hz, depth * hy + 0.012)
        sections.append((G.X(c), G.Y((t + b) / 2), hy, hz, zc))
    sections.append((G.X(tips[1][0]), G.Y(tips[1][1]), 0.0, 0.0, zc))
    return lib.loft_x(bm, sections, sides=16, mat=mat)


def build(colors, pixels):
    coll = common.reset_collection(NAME)
    sprite = {"name": NAME, "colors": colors}
    mats = [common.palette_material(sprite, i, "nshc196", metallic=0.0, roughness=0.38) for i in RAMP]
    slot = {i: k for k, i in enumerate(RAMP)}
    bm = bmesh.new()

    cols = runs(pixels)
    upper = [(c, u) for c, u, _ in cols]
    lower = [(c, lo) for c, _, lo in cols if lo]
    faces = []
    # Upper lip: columns 5-43, corners pointed at the ends of the mouth line (row 13).
    faces += lip(bm, [c for c, _ in upper], [e for _, e in upper], ((3.6, 12.8), (44.4, 12.8)),
                 zc=0.02, depth=0.62, max_hz=0.165, mat=slot[70])
    # Lower lip: columns 8-40, tucked under the upper lip's corners.
    faces += lip(bm, [c for c, _ in lower], [e for _, e in lower], ((7.0, 14.3), (41.0, 14.3)),
                 zc=-0.01, depth=0.7, max_hz=0.215, mat=slot[71])
    # The dark mouth line between them, set back into the gap.
    mouth = []
    for c, u, lo in cols:
        if lo:
            y = (G.Y(u[1] + 0.5) + G.Y(lo[0] - 0.5)) / 2
            mouth.append((G.X(c), y, 1.1 * lib.PX, 0.05, -0.05))
    lib.loft_x(bm, [(G.X(5.0), G.Y(13.0), 0.0, 0.0, -0.05)] + mouth + [(G.X(43.0), G.Y(13.0), 0.0, 0.0, -0.05)],
               sides=8, mat=slot[66])

    def shade(vals):
        vals = [v for v in vals if v in slot]
        return slot[min(75, round(sum(vals) / len(vals) + 0.4))] if vals else None

    lib.paint(faces, G, pixels, shade, spread=0.35)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    pixels, colors = lib.assemble_pixels(ROOT, [("newsh-caret-196", 0, 0), ("newsh-caret-208", 24, 0)])
    obj = build(colors, pixels)
    pieces = common.split_assembly(obj, LAYOUT)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        out = Path(out)
        ref = lib.pixels_png(pixels, colors, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
