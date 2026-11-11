"""Draw a tile model's pattern as the original tiles, for comparing a structure model with its art.

    python tools/tile_pattern.py <entry> out.png [--scale 8] [--grid]

<entry> is a src/render/tileModels/ name (e.g. shapesz-tyrbld-purple-cross). The tiles come from
reference/tiles/<shapes>/tiles.json (`TILES_SHAPES=<x> npm run tiles`); empty cells (-1) and, on
layers 1-2, palette index 0 are transparent, as the game draws them. `--grid` marks the tile cells
and prints each cell's tile number. Never commit the output: it is the original art (CLAUDE.md art
rule 6).
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
TILE_W, TILE_H = 24, 28


def pattern_rgba(entry, scale=8):
    doc = json.loads((ROOT / "src/render/tileModels" / f"{entry}.json").read_text())
    shapes = entry.split("-")[0]
    data = json.loads((ROOT / "reference/tiles" / shapes / "tiles.json").read_text())
    colors = {int(k): v for k, v in data["colors"].items()}
    pattern = doc["tiles"]
    rows, cols = len(pattern), len(pattern[0])
    img = np.zeros((rows * TILE_H, cols * TILE_W, 4), np.uint8)
    for r, row in enumerate(pattern):
        for c, n in enumerate(row):
            if n < 0:
                continue
            px = np.array([[int(v) for v in line.split()] for line in data["tiles"][str(n)]["pixels"]])
            for y in range(TILE_H):
                for x in range(TILE_W):
                    v = px[y, x]
                    if v == 0 and doc["layer"] > 0:
                        continue
                    img[r * TILE_H + y, c * TILE_W + x] = (*colors[v], 255)
    out = Image.fromarray(img).resize((cols * TILE_W * scale, rows * TILE_H * scale), Image.NEAREST)
    return out, pattern


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entry")
    ap.add_argument("out")
    ap.add_argument("--scale", type=int, default=8)
    ap.add_argument("--grid", action="store_true")
    a = ap.parse_args()
    img, pattern = pattern_rgba(a.entry, a.scale)
    if a.grid:
        d = ImageDraw.Draw(img)
        for r, row in enumerate(pattern):
            for c, n in enumerate(row):
                x0, y0 = c * TILE_W * a.scale, r * TILE_H * a.scale
                d.rectangle([x0, y0, x0 + TILE_W * a.scale - 1, y0 + TILE_H * a.scale - 1], outline=(255, 255, 0, 160))
                d.text((x0 + 3, y0 + 2), f"{r},{c}:{n}", fill=(255, 255, 0, 255))
    img.save(a.out)
    print(f"wrote {a.out} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
