"""Coin and gem value numbers as clean high-resolution flat art (DECISIONS.md D76).

When a coin, gem or data cube is picked up, its value floats where it was as a fixed-position
explosion (mainint.c: JE_setupExplosion(..., enemyDat[].explosionType, fixedPosition = true)): one
sprite of newsh6.shp, explosion types 35-52, drawn for the type's ttl. Drawn as before they were
extruded pixel digits on a dark plate. This paints each of those 18 sprites as vector art instead,
packs them into one atlas and adds them to the flat sprite art (D42) as sheet "newsh6.shp", so they
draw as crisp flat quads in the remastered look and as before in the original look.

    python tools/value_art.py [--data data] [--out public/art/sprites] [--check PNG]

The painting is the sprite itself, redrawn: no Gemini, nothing invented.
- **Strokes**: every digit pixel is joined to its digit neighbours (across, down, and diagonally
  where the pixels only touch at a corner, as in the slanted 1K/2K/5K), and the strokes are those
  centre lines drawn with a rounded-square pen (an L4 distance) a little under a pixel wide, so the
  digits keep the original's shapes and placement but have clean edges and softened corners at any
  size. Antialiased over about a texel.
- **Colour**: the digits' own palette colours, blended smoothly between pixel centres (the
  original's row bands become one gradient), with a soft bevel lit from the upper left.
- **Plate**: the sprite's darkest colour (newsh6's dark navy or dark red), where the sprite has
  one, under the whole silhouette with rounded corners as the flat art has it (smooth_alpha), a
  slight top-to-bottom shade and a faint glow of the digits' colour round them. Sprites without
  a plate (the red 150 / 350 / 500 / 750 run) get a faint dark shadow instead, inside their box.

The atlas is at SCALE 16 (twice the other flat art's 8, a per-sheet "scale" in the manifest): the
numbers are 5-7 px tall and are read, so they get the extra texels. 18 frames, ~40 KB.

Derived from the game data, like the rest of the flat art (credited in CREDITS.md); the original
sprite PNGs are never written to the repo (--check is for a scratch folder).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flat_art import LEVEL1_PALETTE, ROOT, TILE_W, GameData, _smoothstep, bleed, dump_manifest, pack, smooth_alpha  # noqa: E402

SHEET = "newsh6.shp"
IMAGE = "newsh6-shp.webp"
SCALE = 16
# explosion_data (varz.c, src/render/vfx/explosionFrames.ts) for types 35-52: the value sprites.
# drawExplosions blits sprite + 1 and never advances a fixed-position explosion.
VALUE_DATA = [(165, 8), (184, 8), (203, 8), (222, 8), (168, 8), (187, 8), (206, 8), (225, 10), (169, 10),
              (188, 10), (207, 20), (226, 14), (170, 14), (189, 14), (208, 14), (246, 14), (227, 14), (265, 14)]
VALUE_SPRITES = [s + 1 for s, _ in VALUE_DATA]

PEN = 0.43  # stroke half-width, original px (a pixel is 0.5)
PEN_NORM = 4.0  # the pen's corner rounding: 2 round, larger squarer


def lin(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def plate_index(own: np.ndarray, pal: np.ndarray) -> int | None:
    """The sprite's darkest colour, if it's dark enough to be a plate (luma < 0.12)."""
    used = sorted({int(c) for c in own[own >= 0]})
    luma = {c: float(pal[c] @ np.array([0.2126, 0.7152, 0.0722])) / 255 for c in used}
    darkest = min(used, key=lambda c: luma[c])
    return darkest if luma[darkest] < 0.12 else None


def strokes(digit: np.ndarray) -> list[tuple[float, float, float, float]]:
    """Centre-line segments joining each digit pixel to its digit neighbours (px, centres at +0.5)."""
    h, w = digit.shape
    segs = []
    for y in range(h):
        for x in range(w):
            if not digit[y, x]:
                continue
            joined = False
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and digit[ny, nx]:
                    joined = True
                    if (dx, dy) in ((1, 0), (0, 1)):
                        segs.append((x + 0.5, y + 0.5, nx + 0.5, ny + 0.5))
            for dx in (-1, 1):
                nx, ny = x + dx, y + 1
                if not (0 <= nx < w and ny < h and digit[ny, nx]):
                    continue
                # Pixels touching only at a corner (a slanted stroke's step), or a solid 2x2 block
                # (a thick stroke, which the straight joins alone leave with pinholes): join them.
                if digit[y, nx] == digit[ny, x]:
                    joined = True
                    segs.append((x + 0.5, y + 0.5, nx + 0.5, ny + 0.5))
            if not joined:
                segs.append((x + 0.5, y + 0.5, x + 0.5, y + 0.5))
    return segs


def pen_distance(u: np.ndarray, v: np.ndarray, segs: list[tuple[float, float, float, float]]) -> np.ndarray:
    """Distance (L4 norm, so corners are rounded squares) from each texel to the nearest segment."""
    best = np.full(u.shape, np.inf, np.float32)
    for x0, y0, x1, y1 in segs:
        dx, dy = x1 - x0, y1 - y0
        ll = dx * dx + dy * dy
        t = np.clip(((u - x0) * dx + (v - y0) * dy) / ll, 0, 1) if ll > 0 else 0.0
        ex, ey = np.abs(u - (x0 + t * dx)), np.abs(v - (y0 + t * dy))
        d = (ex ** PEN_NORM + ey ** PEN_NORM) ** (1 / PEN_NORM)
        np.minimum(best, d, out=best)
    return best


def colour_field(own: np.ndarray, digit: np.ndarray, pal: np.ndarray, u: np.ndarray, v: np.ndarray, sigma: float = 0.65) -> np.ndarray:
    """The digit pixels' colours, gaussian-blended between pixel centres (linear light)."""
    ys, xs = np.nonzero(digit)
    cols = lin(pal[own[ys, xs]].astype(np.float32) / 255)
    acc = np.zeros(u.shape + (3,), np.float32)
    wsum = np.zeros(u.shape, np.float32)
    for (y, x), c in zip(zip(ys, xs), cols):
        w = np.exp(-(((u - x - 0.5) ** 2 + (v - y - 0.5) ** 2) / (2 * sigma * sigma))).astype(np.float32)
        acc += w[..., None] * c
        wsum += w
    return acc / np.maximum(wsum, 1e-8)[..., None]


def blur(a: np.ndarray, sigma_px: float) -> np.ndarray:
    from scipy import ndimage

    return ndimage.gaussian_filter(a, sigma_px * SCALE, mode="constant")


def paint(gd: GameData, index: int, palette: int) -> np.ndarray:
    """Sprite `index` of newsh6.shp as RGBA uint8, (rows * SCALE, 12 * SCALE, 4)."""
    own = gd.sprite(SHEET, index)
    pal = gd.palettes[palette]
    h = own.shape[0]
    plate = plate_index(own, pal)
    digit = (own >= 0) & (own != (plate if plate is not None else -2))
    v, u = np.mgrid[0:h * SCALE, 0:TILE_W * SCALE].astype(np.float32)
    u, v = (u + 0.5) / SCALE, (v + 0.5) / SCALE

    d = pen_distance(u, v, strokes(digit))
    aa = 0.7 / SCALE
    cover = 1 - _smoothstep(PEN - aa, PEN + aa, d)
    col = colour_field(own, digit, pal, u, v)
    # Bevel: the pen's distance field as a height, lit from the upper left.
    gy, gx = np.gradient(-d)
    n = np.hypot(gx, gy) + 1e-6
    lit = ((gx * -0.6 + gy * -0.8) / n) * _smoothstep(PEN * 0.25, PEN, d)
    col = col * (1 + 0.35 * lit)[..., None] + 0.08 * np.clip(lit, 0, 1)[..., None]

    if plate is not None:
        alpha = smooth_alpha(own >= 0, SCALE, sigma=0.375 * SCALE)
        base = lin(pal[plate].astype(np.float32) / 255)
        shade = (1.25 - 0.45 * np.clip(v / h, 0, 1))[..., None]
        glow = blur(cover, 0.9)[..., None] * blur(cover[..., None] * col, 0.9) / np.maximum(blur(cover, 0.9), 1e-6)[..., None]
        bg = base * shade + 0.35 * glow
        rgb = bg * (1 - cover[..., None]) + col * cover[..., None]
        alpha = np.maximum(alpha, cover)
    else:
        # No plate: a faint shadow, so the numbers read over bright ground.
        shadow = np.clip(blur(cover, 0.45) * 1.6, 0, 1) * 0.45
        alpha = cover + shadow * (1 - cover)
        rgb = col * (cover / np.maximum(alpha, 1e-6))[..., None]
    rgb = bleed(srgb(rgb), alpha)
    return np.dstack([rgb * 255, alpha * 255]).round().clip(0, 255).astype(np.uint8)


def check_sheet(gd: GameData, frames: list[dict], palette: int, path: Path) -> None:
    """original (nearest) | painted, for every frame, on a mid-grey and a bright ground."""
    cell_w, cell_h = TILE_W * SCALE, 14 * SCALE
    rows = len(frames)
    img = Image.new("RGB", (cell_w * 4 + 40, cell_h * rows), (60, 64, 70))
    pal = gd.palettes[palette]
    for r, f in enumerate(frames):
        own = gd.sprite(SHEET, f["index"])
        orig = np.zeros(own.shape + (4,), np.uint8)
        m = own >= 0
        orig[m, :3] = pal[own[m]]
        orig[m, 3] = 255
        o = Image.fromarray(orig, "RGBA").resize((cell_w, own.shape[0] * SCALE), Image.NEAREST)
        a = Image.fromarray(f["rgba"], "RGBA")
        for c, (im, ground) in enumerate(((o, (60, 64, 70)), (a, (60, 64, 70)), (o, (200, 170, 110)), (a, (200, 170, 110)))):
            x = c * cell_w + (c // 2) * 40
            img.paste(Image.new("RGB", (cell_w, cell_h), ground), (x, r * cell_h))
            img.paste(im, (x, r * cell_h), im)
    img.save(path)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--out", type=Path, default=ROOT / "public/art/sprites")
    ap.add_argument("--palette", type=int, default=LEVEL1_PALETTE)
    ap.add_argument("--check", type=Path, help="write an original | painted contact sheet here (scratch only)")
    a = ap.parse_args(argv)
    gd = GameData(a.data)
    frames = [{"index": i, "rgba": paint(gd, i, a.palette)} for i in VALUE_SPRITES]
    atlas, rects = pack(frames, width=832)
    Image.fromarray(atlas, "RGBA").save(a.out / IMAGE, "WEBP", quality=92, alpha_quality=100, method=6, exact=True)
    path = a.out / "manifest.json"
    manifest = json.loads(path.read_text()) if path.exists() else {"scale": 8, "sheets": {}}
    manifest["sheets"][SHEET] = {"image": IMAGE, "scale": SCALE, "frames": dict(sorted(rects.items(), key=lambda kv: int(kv[0])))}
    path.write_text(dump_manifest(manifest))
    print(f"{a.out / IMAGE}: {len(rects)} frames, {atlas.shape[1]}x{atlas.shape[0]}, {(a.out / IMAGE).stat().st_size} bytes")
    if a.check:
        check_sheet(gd, frames, a.palette, a.check)
        print(f"check: {a.check}")


if __name__ == "__main__":
    main()
