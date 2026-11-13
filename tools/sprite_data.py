"""A sprite's reference data read straight from the game data, for units the catalogue doesn't list.

`npm run catalogue` writes reference/models/<name>/sprite.json for every enemy its played levels draw
(tests/tools/spriteCatalogue.test.ts). A few pieces never show up there (the upper pieces of TIME
WAR's tower and shield ship, UNDERDELI's chin block): the catalogue's world doesn't reach them. A
model script for such a unit reads its frames here instead, decoded from the Sprite2 sheet and
palette.dat in $TYRIAN_DATA (or the repo's data/), in the catalogue's format: `sprites`, `frames`
(each with `index`, `width`, `height` and `pixels` as rows of palette indices, -1 transparent) and
`colors` (the 8-bit RGB of every index used). Nothing is written. Pure standard library, so it runs
under Blender's Python and the system's.

    sys.path.insert(0, str(ROOT / "tools")); import sprite_data
    sprite = sprite_data.load(ROOT, "newsh9-123", "newsh9.shp", [123, 241, 279])
"""

import os
from pathlib import Path

#: Episode 4's sprites are drawn with palette 5 (the catalogue's `palette` for its levels' enemies).
PALETTE = 5


def data_file(root, name):
    """A file of the Tyrian 2.1 data: $TYRIAN_DATA first, then the repo's data/ (a link in worktrees)."""
    for d in (os.environ.get("TYRIAN_DATA"), Path(root) / "data"):
        if d and (Path(d) / name).exists():
            return Path(d) / name
    raise FileNotFoundError(f"{name}: set TYRIAN_DATA to the Tyrian 2.1 data")


def sprite2(sheet, index):
    """src/data/sprites.ts decodeSprite2: Sprite2 #index (1-based) as rows of 12 (-1 transparent)."""
    rows, row = [], [-1] * 12
    p = sheet[(index - 1) * 2] | (sheet[(index - 1) * 2 + 1] << 8)
    x = 0
    while p < len(sheet) and sheet[p] != 0x0F:
        x += sheet[p] & 0x0F
        n = sheet[p] >> 4
        if n == 0:
            rows.append(row)
            row, x = [-1] * 12, 0
        else:
            for _ in range(n):
                p += 1
                if x < 12:
                    row[x] = sheet[p]
                x += 1
        p += 1
    if any(v >= 0 for v in row):
        rows.append(row)
    return rows


def compose(sheet, size, index):
    """A frame's picture as the catalogue composes it: 12x14 (size 1) or the 2x2 block index, +1, +19,
    +20 (24x28), as rows of palette indices."""
    w, h = 12 * size, 14 * size
    out = [[-1] * w for _ in range(h)]
    tiles = [(0, 0, 0)] if size == 1 else [(0, 0, 0), (1, 12, 0), (19, 0, 14), (20, 12, 14)]
    for off, ox, oy in tiles:
        for y, row in enumerate(sprite2(sheet, index + off)[:14]):
            for x, v in enumerate(row):
                out[oy + y][ox + x] = v
    return out


def palette_rgb(root, palette=PALETTE):
    """All 256 colours of a palette as 8-bit [r, g, b] lists (for materials on indices a frame doesn't use)."""
    pal = data_file(root, "palette.dat").read_bytes()[palette * 768:(palette + 1) * 768]
    return [[(v << 2) | (v >> 4) for v in pal[i * 3:i * 3 + 3]] for i in range(256)]


def load(root, name, sheet_name, frames, size=2, palette=PALETTE):
    """sprite.json's content for model `name`: the given frames of `sheet_name` (pixels already parsed
    to lists of ints, as the model scripts' loaders leave them)."""
    sheet = data_file(root, sheet_name).read_bytes()
    pal = data_file(root, "palette.dat").read_bytes()[palette * 768:(palette + 1) * 768]
    eight = lambda v: (v << 2) | (v >> 4)  # noqa: E731  (6-bit VGA to 8-bit, src/data vga6To8)
    out_frames, used = [], set()
    for f in frames:
        px = compose(sheet, size, f)
        used |= {v for row in px for v in row if v >= 0}
        out_frames.append({"sheet": sheet_name, "size": size, "index": f, "width": 12 * size,
                           "height": 14 * size, "pixels": px})
    colors = {str(i): [eight(pal[i * 3]), eight(pal[i * 3 + 1]), eight(pal[i * 3 + 2])] for i in sorted(used)}
    return {"name": name, "sprites": [{"sheet": sheet_name, "size": size, "frames": list(frames)}],
            "palette": palette, "colors": colors, "frames": out_frames}
