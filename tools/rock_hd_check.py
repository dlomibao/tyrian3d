"""HD island rock seam check (DECISIONS.md D84): how well the island rock tiles meet across every
seam TYRIAN's map has, measured as tools/terrain_hd.py's `check` measures the HD terrain (D58/D59).

For every pair of island rock tiles the map puts side by side (weighted by how often), the colour step
between the two texels that meet at the seam, against the mean step between neighbouring texels inside
the tiles; and the same for 8-texel bands either side of the seam against bands inside. Colours are
what the game draws (flat, unlit: palette[ramp * 16 + shade], lib_rock_hd.preview_rgb), each tile with
the edge band for the neighbour it has there, as rockMaterial.ts draws it; `--no-bands` measures the
tiles' own textures alone. The original 1x pixel art is measured the same way for reference.

    python tools/rock_hd_check.py [--data DIR] [--out DIR] [--no-bands]

Needs numpy (Pillow for --out: the map's islands, original beside HD). Uses (and fills) the cache
lib_tiles.island_hd uses (reference/tiles/rock-hd-*.npz), so run it after a build for the numbers of
the committed models. Game data from $TYRIAN_DATA or data/.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "assets" / "blender" / "tiles"))
import lib_rock_hd as rh  # noqa: E402

# lib_tiles.ROCK_TILES / ROCK_COLOURS (lib_tiles needs Blender).
ROCK_TILES = (120, 121, 122, 123, 124, 130, 131, 132, 133, 134, 140, 141, 142, 150, 151, 152)
ROCK_COLOURS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 24, 25, 27, 28, 163, 165, 167, 169, 171)
SIDES = {"left": (0, -1), "right": (0, 1), "up": (-1, 0), "down": (1, 0)}


def with_bands(T, n, nb):
    """Tile n's channels as the game draws them with neighbours `nb` {side: tile} (rockMaterial.ts)."""
    H, W = rh.TILE_H * rh.TEX, rh.TILE_W * rh.TEX
    ch = {c: T[n][c].copy() for c in rh.CHANNELS}
    yy = np.broadcast_to((np.arange(H) + 0.5)[:, None], (H, W))
    xx = np.broadcast_to((np.arange(W) + 0.5)[None, :], (H, W))
    D, F = rh.BAND_DEPTH, rh.BAND_FADE
    acc = {c: np.zeros((H, W)) for c in ch}
    ksum = np.zeros((H, W))
    wmax = np.zeros((H, W))
    for side, depth, along in (("left", xx, yy), ("right", W - xx, yy), ("up", yy, xx), ("down", H - yy, xx)):
        b = T[n]["bands"].get(f"{side}:{nb.get(side, -1)}")
        if b is None:
            continue
        w = 1 - rh.smoothstep(D - F, D, depth)
        k = w / (depth + 0.5) ** 3  # the nearest side wins (rockMaterial.ts)
        di = np.clip(np.floor(depth).astype(int), 0, D - 1)
        ai = np.clip(np.floor(along).astype(int), 0, b["shade"].shape[1] - 1)
        for c in ch:
            acc[c] += k * b[c][di, ai]
        ksum += k
        wmax = np.maximum(wmax, w)
    has = ksum > 0
    for c in ch:
        ch[c] = np.where(has, ch[c] * (1 - wmax) + acc[c] / np.maximum(ksum, 1e-12) * wmax, ch[c])
    return ch


def seam_stats(img, alpha, grid, tiles, band=8):
    """D59's measure on per-cell images: {(y, x): (H, W, 3)} of the cells of `grid` in `tiles`."""
    def step(p, q, wp, wq):
        w = np.minimum(wp, wq)
        return None if w.sum() < 1 else float((np.abs(p - q).mean(-1) * w).sum() / w.sum())

    edge_t, edge_b, in_t, in_b = [], [], [], []
    h, w = grid.shape
    for (y, x), A in img.items():
        aA = alpha[(y, x)]
        for dy, dx in ((0, 1), (1, 0)):
            if (y + dy, x + dx) not in img:
                continue
            B, aB = img[(y + dy, x + dx)], alpha[(y + dy, x + dx)]
            if dx:
                t = step(A[:, -1], B[:, 0], aA[:, -1], aB[:, 0])
                bb = step(A[:, -band:].mean(1), B[:, :band].mean(1), aA[:, -1], aB[:, 0])
            else:
                t = step(A[-1], B[0], aA[-1], aB[0])
                bb = step(A[-band:].mean(0), B[:band].mean(0), aA[-1], aB[0])
            if t is not None:
                edge_t.append(t)
                edge_b.append(bb)
        v = [step(A[:, j], A[:, j + 1], aA[:, j], aA[:, j + 1]) for j in range(A.shape[1] - 1)]
        v += [step(A[i], A[i + 1], aA[i], aA[i + 1]) for i in range(A.shape[0] - 1)]
        bv = [step(A[:, c - band:c].mean(1), A[:, c:c + band].mean(1), aA[:, c], aA[:, c]) for c in range(band, A.shape[1] - band + 1, band)]
        bv += [step(A[c - band:c].mean(0), A[c:c + band].mean(0), aA[c], aA[c]) for c in range(band, A.shape[0] - band + 1, band)]
        v, bv = [a for a in v if a is not None], [a for a in bv if a is not None]
        if v:
            in_t.append(np.mean(v))
            in_b.append(np.mean(bv))
    et, it, eb, ib = np.mean(edge_t), np.mean(in_t), np.mean(edge_b), np.mean(in_b)
    return {"seams": len(edge_t), "edgeTexelStep": round(float(et), 2), "insideTexelStep": round(float(it), 2),
            "texelRatio": round(float(et / it), 3), "edgeBandStep": round(float(eb), 2),
            "insideBandStep": round(float(ib), 2), "bandRatio": round(float(eb / ib), 3)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", default=os.environ.get("TYRIAN_DATA", str(ROOT / "data")))
    ap.add_argument("--out", help="write the map's islands, original beside HD, as JPEGs here")
    ap.add_argument("--no-bands", action="store_true", help="the tiles' own textures, without their edge bands")
    args = ap.parse_args(argv)
    os.environ["TYRIAN_DATA"] = args.data
    d = json.loads((ROOT / "reference" / "tiles" / "shapesz" / "tiles.json").read_text())
    colors = {int(k): v for k, v in d["colors"].items()}
    px = {int(n): np.array([[int(v) for v in r.split()] for r in t["pixels"]], np.int32) for n, t in d["tiles"].items()}
    grid = rh.level_map(ROOT, "1-9", 2)
    on_map = {int(n) for n in np.unique(grid) if n >= 0}
    tiles = sorted((set(ROCK_TILES) | on_map) & set(px))
    T = rh.island_tiles(ROOT, tiles, px, colors, [k for k in ROCK_COLOURS if k in colors], band_tiles=tiles)
    pal = rh.Pal(colors)
    cols = np.zeros((256, 3))
    for i, c in colors.items():
        cols[i] = c
    hd, hd_a, orig, orig_a = {}, {}, {}, {}
    h, w = grid.shape
    at = lambda y, x: int(grid[y, x]) if 0 <= y < h and 0 <= x < w else -1  # noqa: E731
    for y in range(h):
        for x in range(w):
            n = at(y, x)
            if n not in ROCK_TILES:
                continue
            nb = {} if args.no_bands else {s: at(y + dy, x + dx) for s, (dy, dx) in SIDES.items()}
            hd[(y, x)] = rh.preview_rgb(pal, with_bands(T, n, nb))
            hd_a[(y, x)] = (T[n]["alpha"] > 0.5).astype(float)
            p = px[n]
            orig[(y, x)] = cols[p]
            orig_a[(y, x)] = (p > 0).astype(float)
    out = {"hd": seam_stats(hd, hd_a, grid, ROCK_TILES), "original1x": seam_stats(orig, orig_a, grid, ROCK_TILES, band=1)}
    out["bands"] = not args.no_bands
    print(json.dumps(out, indent=1))
    if args.out:
        from PIL import Image
        Path(args.out).mkdir(parents=True, exist_ok=True)
        rows = sorted({y for y, _ in hd})
        H, W = rh.TILE_H * rh.TEX, rh.TILE_W * rh.TEX
        for start in range(rows[0], rows[-1] + 1, 24):
            ys = [y for y in rows if start <= y < start + 24]
            if not ys:
                continue
            img = np.full((24 * H, w * W * 2 + 16, 3), 40, np.uint8)
            for (y, x), a in hd.items():
                if start <= y < start + 24:
                    r = y - start
                    big = np.repeat(np.repeat(orig[(y, x)], rh.TEX, 0), rh.TEX, 1)
                    m = np.repeat(np.repeat(orig_a[(y, x)], rh.TEX, 0), rh.TEX, 1)[..., None] > 0
                    img[r * H:(r + 1) * H, x * W:(x + 1) * W] = np.where(m, big, 40)
                    img[r * H:(r + 1) * H, w * W + 16 + x * W:w * W + 16 + (x + 1) * W] = np.where(hd_a[(y, x)][..., None] > 0, a.clip(0, 255), 40)
            Image.fromarray(img).resize((img.shape[1] // 2, img.shape[0] // 2), Image.LANCZOS).save(Path(args.out) / f"rows-{start:03d}.jpg", quality=88)


if __name__ == "__main__":
    main()
