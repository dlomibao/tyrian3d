"""HD terrain: Gemini-painted background tiles, cut, made seamless and packed as atlases (DECISIONS.md D58).

The remastered look draws the ground (and TYRIAN's ice clouds) upscaled 4x with MMPX at runtime
(DECISIONS.md D34, D45, D48). This tool brings in HD paintings of a level's background tiles instead,
made by Google Gemini from input sheets of the original tiles, and packs them as the atlases the game
reads (public/art/terrain/<shapes>/manifest.json + <layer>.webp, the format in D57):

    python tools/terrain_hd.py --level 1-9 --work DIR inventory
        Every tile the level's map draws on layers 0, 1 and 2 as a tile (tiles a layer-1/2 structure
        model replaces are left out; ground tiles under ground models are still drawn, D34), with
        counts, usual neighbours and a representative 3x3 neighbourhood from the map, and a
        material group per tile. Writes DIR/inventory.json.

    python tools/terrain_hd.py --work DIR sheets
        Gemini input sheets in DIR/sheets/: grids of 3x3-tile contexts (the tile with its usual
        neighbours, scaled up nearest-neighbour, on black), one material group per sheet, and for
        the ground also sheets of continuous map regions (7x6 tiles). Each sheet is padded to one of
        Gemini's aspect ratios. DIR/sheets/manifest.json says where every tile sits. The sheets are
        rendered from the game data, so they stay out of git (D3).

    python tools/terrain_hd.py --work DIR fake
        Stand-in "Gemini" answers for testing: each sheet upscaled with MMPX, blurred, shifted,
        rescaled slightly and colour-shifted, in DIR/results-fake/.

    python tools/terrain_hd.py --work DIR cut [--results DIR/results] [--out public/art/terrain]
        Cuts every answer (DIR/results/<sheet>.png|jpg|webp, any size, same aspect as the sheet; sheets
        without an answer are skipped) back into tiles at 8 texels per original pixel: each cell is
        registered to the sheet's own picture of it (rescale and shift by normalised cross-correlation),
        each tile in it refined by a small shift, resampled from the art and colour-matched to the
        original tile (mean and low-frequency contrast per channel). The best candidate per tile wins
        (or --combine mean): its fit, less its colour error, copied pixel blocks and made-up marks,
        with a bonus for map regions (D59); --exclude, --pick and --cache adjust and speed this up.
        The winner's broad shading (16 texels) is then replaced by the original's. Alpha (layers 1-2) is the original silhouette, smoothly upscaled among the
        tile's usual neighbours. Then the seams: every tile side's edge strip is solved jointly, least
        squares over every pair of tiles the map puts side by side (weighted by how often) plus a weak
        pull towards the tile's own painting, and each tile's border is moved onto its strips (the
        difference fades in over 40 texels, the outer 4 texels are the strip). One atlas per layer is
        packed (16-aligned rects, 16 px edge-extended gutters): <out>/<shapes>/<layer>.webp and
        manifest.json; DIR/cut-report.json says where each tile came from and how well it fitted.

    python tools/terrain_hd.py --work DIR check [--out public/art/terrain]
        Reassembles the level's map from the atlas, 12 rows at a time, into contact sheets (original,
        nearest, beside HD, 4 px per original pixel) and measures seams over every tile edge the map
        has: the colour step between the two edge texels, against the step between neighbouring
        texels inside tiles (and the same for 8-texel strips). Writes DIR/check/ (seams.json lists the
        worst pairs).

The options before the command (--data, --level, --work) apply to all of them; --work defaults to
reference/terrain-hd/ (git-ignored).

The game data is read from --data (default data/): tyrian<ep>.lvl (src/data/levels.ts),
shapes<x>.dat and palette.dat (src/data/palette.ts); the structure models from
src/render/tileModels/*.json (src/render/remaster/tileModels.ts).
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
TILE_W, TILE_H = 24, 28
MAP_SIZES = [(14, 300), (14, 600), (15, 600)]  # (width, height) in tiles per layer
SCALE = 8  # atlas texels per original pixel
LEVEL_PALETTE = 5  # the in-level palette (pcxpal[2]), as tests/tools/tileReference.test.ts
SHAPES_PER_FILE = 600
# Gemini's image aspect ratios (w, h).
ASPECTS = [(1, 1), (3, 4), (4, 3), (9, 16), (16, 9)]

# --- Game data -----------------------------------------------------------------------------------


def vga6to8(c: int) -> int:
    return ((c << 2) | (c >> 4)) & 0xFF


class LevelData:
    """One level's maps, tiles and palette, read as src/data/levels.ts and palette.ts do."""

    def __init__(self, data_dir: Path, level_id: str):
        ep, num = (int(s) for s in level_id.split("-"))
        self.id = level_id
        b = (data_dir / f"tyrian{ep}.lvl").read_bytes()
        lvl_num = min(struct.unpack_from("<H", b, 0)[0], 42)
        pos = [struct.unpack_from("<I", b, 2 + 4 * i)[0] if i < lvl_num else len(b) for i in range(43)]
        p = pos[(num - 1) * 2]
        self.shape_letter = chr(b[p + 1]).lower()
        p += 2 + 6  # mapFile, shapeFile, mapX, mapX2, mapX3
        p += 2 + 2 * struct.unpack_from("<H", b, p)[0]  # levelEnemy
        p += 2 + 11 * struct.unpack_from("<H", b, p)[0]  # events (11 bytes each)
        map_sh = [list(struct.unpack_from(">128H", b, p + 256 * k)) for k in range(3)]
        p += 3 * 256
        raw_maps = []
        for w, h in MAP_SIZES:
            raw_maps.append(np.frombuffer(b, np.uint8, w * h, p).reshape(h, w))
            p += w * h
        self.shapes_file = f"shapes{self.shape_letter}.dat"
        self.shapes_name = f"shapes{self.shape_letter}"
        sb = (data_dir / self.shapes_file).read_bytes()
        shapes: list[np.ndarray | None] = []
        q = 0
        for _ in range(SHAPES_PER_FILE):
            blank = sb[q] != 0
            q += 1
            if blank:
                shapes.append(None)
            else:
                shapes.append(np.frombuffer(sb, np.uint8, TILE_W * TILE_H, q).reshape(TILE_H, TILE_W).copy())
                q += TILE_W * TILE_H
        # Tile number grids (0-based shapes record, -1 = nothing drawn), as levelTiles() resolves them.
        self.grids: list[np.ndarray] = []
        self.pixels: dict[int, np.ndarray] = {}
        for layer, raw in enumerate(raw_maps):
            lut = np.full(256, -1, np.int32)
            for x in range(72):
                z = map_sh[layer][x] - 1
                if z < 0 or z >= SHAPES_PER_FILE:
                    continue
                shape = shapes[z]
                if layer == 0:
                    lut[x] = z
                    self.pixels.setdefault(z, shape if shape is not None else np.zeros((TILE_H, TILE_W), np.uint8))
                elif shape is not None and (x != 71 if layer == 1 else x < 70):
                    lut[x] = z
                    self.pixels.setdefault(z, shape)
            self.grids.append(lut[raw])
        pal = (data_dir / "palette.dat").read_bytes()[LEVEL_PALETTE * 768:(LEVEL_PALETTE + 1) * 768]
        self.rgb = np.array([vga6to8(c) for c in pal], np.uint8).reshape(256, 3)
        self.luma = self.rgb.astype(np.float32).sum(1) + 1
        self.luma_clear = self.luma.copy()
        self.luma_clear[0] = 0

    def tile(self, n: int) -> np.ndarray:
        return self.pixels[n]


def load_models(shapes_file: str) -> list[dict]:
    out = []
    for f in sorted((ROOT / "src/render/tileModels").glob("*.json")):
        e = json.loads(f.read_text())
        if e["shapes"] == shapes_file:
            e["name"] = f.stem
            out.append(e)
    return out


def replaced_mask(grid: np.ndarray, layer: int, models: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Cells whose tile a structure model replaces (TileModelIndex.match with the whole map drawn,
    biggest pattern first; drawListRenderer keeps the tile when keepTiles ?? layer === 0), and cells
    a ground model stands on (kept)."""
    h, w = grid.shape
    best = np.zeros((h, w), np.int32)  # size of the biggest matching pattern per cell
    keep_of_best = np.ones((h, w), bool)
    entries = [e for e in models if e["layer"] == layer]
    size = lambda e: sum(1 for row in e["tiles"] for t in row if t >= 0)  # noqa: E731
    entries.sort(key=lambda e: -size(e))
    pad = max([len(e["tiles"]) for e in entries] + [1])
    # The grid with `pad` undrawn rows above and below, so anchors can hang off the map's ends.
    g = np.full((h + 2 * pad, w), -1, np.int32)
    g[pad:pad + h] = grid
    drawn = g >= 0
    for e in entries:
        pat = np.array(e["tiles"])
        R, C = pat.shape
        keep = e.get("keepTiles", layer == 0)
        n = size(e)
        ny, nx = h + R - 1, w - C + 1  # anchors: ay in [-R+1, h), ax in [0, w-C]
        if nx <= 0:
            continue
        ok = np.ones((ny, nx), bool)
        rows_seen = np.zeros((ny, nx), np.int32)
        for r in range(R):
            seen = np.zeros((ny, nx), bool)
            for c in range(C):
                want = pat[r, c]
                if want < 0:
                    continue
                y0 = pad - R + 1 + r
                sub = g[y0:y0 + ny, c:c + nx]
                d = drawn[y0:y0 + ny, c:c + nx]
                ok &= ~d | (sub == want)
                seen |= d
            rows_seen += seen
        ok &= rows_seen > 0
        if "minRows" in e:
            ok &= rows_seen >= min(e["minRows"], R)
        for ay, ax in zip(*np.nonzero(ok)):
            ay -= R - 1
            for r in range(R):
                y = ay + r
                if y < 0 or y >= h:
                    continue
                for c in range(C):
                    if pat[r, c] < 0 or grid[y, ax + c] < 0:
                        continue
                    if n > best[y, ax + c]:
                        best[y, ax + c] = n
                        keep_of_best[y, ax + c] = keep
    replaced = (best > 0) & ~keep_of_best
    under_kept = (best > 0) & keep_of_best
    return replaced, under_kept


# --- MMPX (src/render/remaster/mmpx.ts, vectorised) ------------------------------------------------


def mmpx2x(pix: np.ndarray, luma: np.ndarray) -> np.ndarray:
    """MMPX 2x on palette indices, edges clamped: the same rules, in the same order, as mmpx.ts."""
    h, w = pix.shape
    P = np.pad(pix.astype(np.int32), 3, mode="edge")

    def s(dx: int, dy: int) -> np.ndarray:
        return P[3 + dy:3 + dy + h, 3 + dx:3 + dx + w]

    A, B, C = s(-1, -1), s(0, -1), s(1, -1)
    D, E, F = s(-1, 0), s(0, 0), s(1, 0)
    G, H, I = s(-1, 1), s(0, 1), s(1, 1)
    Pp, S, Q, R = s(0, -2), s(0, 2), s(-2, 0), s(2, 0)
    Bl, Dl, El, Fl, Hl = luma[B], luma[D], luma[E], luma[F], luma[H]
    J, K, L, M = E.copy(), E.copy(), E.copy(), E.copy()
    act = (A != E) | (B != E) | (C != E) | (D != E) | (F != E) | (G != E) | (H != E) | (I != E)

    def any3(b, a0, a1, a2):
        return (b == a0) | (b == a1) | (b == a2)

    def all2(b, a0, a1):
        return (b == a0) & (b == a1)

    def all3(b, a0, a1, a2):
        return (b == a0) & (b == a1) & (b == a2)

    def all4(b, a0, a1, a2, a3):
        return (b == a0) & (b == a1) & (b == a2) & (b == a3)

    def none2(b, a0, a1):
        return (b != a0) & (b != a1)

    def none4(b, a0, a1, a2, a3):
        return (b != a0) & (b != a1) & (b != a2) & (b != a3)

    def put(cond, *pairs):
        c = act & cond
        for dst, src in pairs:
            dst[c] = src[c] if isinstance(src, np.ndarray) else src

    put((D == B) & (D != H) & (D != F) & ((El >= Dl) | (E == A)) & any3(E, A, C, G) & ((El < Dl) | (A != D) | (E != Pp) | (E != Q)), (J, D))
    put((B == F) & (B != D) & (B != H) & ((El >= Bl) | (E == C)) & any3(E, A, C, I) & ((El < Bl) | (C != B) | (E != Pp) | (E != R)), (K, B))
    put((H == D) & (H != F) & (H != B) & ((El >= Hl) | (E == G)) & any3(E, A, G, I) & ((El < Hl) | (G != H) | (E != S) | (E != Q)), (L, H))
    put((F == H) & (F != B) & (F != D) & ((El >= Fl) | (E == I)) & any3(E, C, G, I) & ((El < Fl) | (I != H) | (E != R) | (E != S)), (M, F))

    put((E != F) & all4(E, C, I, D, Q) & all2(F, B, H) & (F != s(3, 0)), (K, F), (M, F))
    put((E != D) & all4(E, A, G, F, R) & all2(D, B, H) & (D != s(-3, 0)), (J, D), (L, D))
    put((E != H) & all4(E, G, I, B, Pp) & all2(H, D, F) & (H != s(0, 3)), (L, H), (M, H))
    put((E != B) & all4(E, A, C, H, S) & all2(B, D, F) & (B != s(0, -3)), (J, B), (K, B))

    put((Bl < El) & all4(E, G, H, I, S) & none4(E, A, D, C, F), (J, B), (K, B))
    put((Hl < El) & all4(E, A, B, C, Pp) & none4(E, D, G, I, F), (L, H), (M, H))
    put((Fl < El) & all4(E, A, D, G, Q) & none4(E, B, C, I, H), (K, F), (M, F))
    put((Dl < El) & all4(E, C, F, I, R) & none4(E, B, A, G, H), (J, D), (L, D))

    hb = H != B
    h1 = hb & (H != A) & (H != E) & (H != C)
    put(h1 & all3(H, G, F, R) & none2(H, D, s(2, -1)), (L, M))
    put(h1 & all3(H, I, D, Q) & none2(H, F, s(-2, -1)), (M, L))
    b1 = hb & (B != I) & (B != G) & (B != E)
    put(b1 & all3(B, A, F, R) & none2(B, D, s(2, 1)), (J, K))
    put(b1 & all3(B, C, D, Q) & none2(B, F, s(-2, 1)), (K, J))
    fd = F != D
    d1 = fd & (D != I) & (D != E) & (D != C)
    put(d1 & all3(D, A, H, S) & none2(D, B, s(1, 2)), (J, L))
    put(d1 & all3(D, G, B, Pp) & none2(D, H, s(1, -2)), (L, J))
    f1 = fd & (F != E) & (F != A) & (F != G)
    put(f1 & all3(F, C, H, S) & none2(F, B, s(-1, 2)), (K, M))
    put(f1 & all3(F, I, B, Pp) & none2(F, H, s(-1, -2)), (M, K))

    out = np.empty((h * 2, w * 2), np.int32)
    out[0::2, 0::2], out[0::2, 1::2], out[1::2, 0::2], out[1::2, 1::2] = J, K, L, M
    return out.astype(pix.dtype)


def mmpx(pix: np.ndarray, luma: np.ndarray, factor: int) -> np.ndarray:
    """MMPX applied until `factor` (a power of two) is reached."""
    while factor > 1:
        pix = mmpx2x(pix, luma)
        factor //= 2
    return pix


# --- Inventory -----------------------------------------------------------------------------------

SIDES = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1),
         "upLeft": (-1, -1), "upRight": (1, -1), "downLeft": (-1, 1), "downRight": (1, 1)}
EDGE_SIDES = ("left", "right", "up", "down")


def shifted(grid: np.ndarray, dx: int, dy: int, fill: int = -2) -> np.ndarray:
    """grid[y + dy, x + dx] at every (y, x); `fill` outside the map (-2: off the map)."""
    h, w = grid.shape
    out = np.full_like(grid, fill)
    ys, yd = slice(max(dy, 0), h + min(dy, 0)), slice(max(-dy, 0), h + min(-dy, 0))
    xs, xd = slice(max(dx, 0), w + min(dx, 0)), slice(max(-dx, 0), w + min(-dx, 0))
    out[yd, xd] = grid[ys, xs]
    return out


def colour_name(rgb: np.ndarray) -> str:
    r, g, b = (int(c) for c in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn < 20:
        return "grey"
    if g >= r and g >= b:
        return "green" if g - b > 20 else "cyan"
    if b >= r and b >= g:
        return "blue" if b - r > 40 else "cyan"
    if r >= g and r >= b:
        if g > b and g > r * 0.6:
            return "brown" if r < 200 else "yellow"
        return "red" if b < r * 0.6 else "purple"
    return "mixed"


def material_group(L: LevelData, layer: int, tile: int, under_model: float) -> str:
    """A material group from the tile's palette ramps (index // 16): Tyrian's ramps are one colour
    each, so the dominant ramps say what the tile is made of. Tiles mostly under a ground model are
    a group of their own ("-modelled": trees, bunkers and boulders stand on them, D34/D47)."""
    p = L.tile(tile)
    p = p[p > 0] if layer > 0 else p.ravel()
    h = np.bincount(p // 16, minlength=16) / max(len(p), 1)
    order = [int(i) for i in np.argsort(-h)]
    name = lambda r: colour_name(L.rgb[r * 16 + 8])  # noqa: E731
    main = name(order[0])
    second = name(order[1]) if h[order[1]] >= 0.12 else None
    if layer == 0 and under_model >= 0.5:
        return f"l0-{main}-modelled"
    if layer == 0 and second and second != main and second != "grey":
        return f"l0-{'-'.join(sorted([main, second]))}-edges"
    return f"l{layer}-{main}"


def build_inventory(L: LevelData) -> dict:
    models = load_models(L.shapes_file)
    out = {"level": L.id, "shapes": L.shapes_name, "palette": LEVEL_PALETTE, "tileWidth": TILE_W, "tileHeight": TILE_H,
           "note": "tile = 0-based record in the shapes file; neighbours count the cells drawn as tiles (-1 none, -2 off the map); "
                   "context = a representative 3x3 neighbourhood from the map (rows of tile numbers, as in the map, -1 none)",
           "layers": {}}
    for layer in range(3):
        g = L.grids[layer]
        rep, kept = replaced_mask(g, layer, models)
        drawn = (g >= 0) & ~rep
        dg = np.where(drawn, g, -1)
        nbs = {k: shifted(dg, dx, dy) for k, (dx, dy) in SIDES.items()}
        full = {k: shifted(g, dx, dy) for k, (dx, dy) in SIDES.items()}
        tiles = {}
        for n in sorted(set(g[g >= 0].tolist())):
            at = g == n
            cnt = int((at & drawn).sum())
            entry = {"tile": n, "count": int(at.sum()), "drawn": cnt, "replaced": int((at & rep).sum()),
                     "underModel": int((at & kept).sum())}
            if cnt == 0:
                entry["drawnAsTile"] = False
                tiles[str(n)] = entry
                continue
            entry["drawnAsTile"] = True
            mask = at & drawn
            stats = {}
            for k in SIDES:
                c = Counter(nbs[k][mask].tolist())
                stats[k] = c
            entry["neighbours"] = {k: [[t, c] for t, c in stats[k].most_common(6)] for k in EDGE_SIDES}
            entry["diagonals"] = {k: [[t, c] for t, c in stats[k].most_common(3)] for k in SIDES if k not in EDGE_SIDES}
            entry["usual"] = {k: stats[k].most_common(1)[0][0] for k in SIDES}
            # Representative neighbourhood: the occurrence whose neighbours are the most usual ones.
            ys, xs = np.nonzero(mask)
            score = np.zeros(len(ys))
            for k, (dx, dy) in SIDES.items():
                wgt = 1.0 if k in EDGE_SIDES else 0.5
                freq = {t: c / cnt for t, c in stats[k].items()}
                vals = full[k][ys, xs]
                score += wgt * np.array([freq.get(int(v), 0.0) for v in nbs[k][ys, xs]])
                score -= 2.0 * (vals == -2)  # off the map
            best = int(np.argmax(score))
            y, x = int(ys[best]), int(xs[best])
            ctx = [[int(g[y + dy, x + dx]) if 0 <= y + dy < g.shape[0] and 0 <= x + dx < g.shape[1] else -2
                    for dx in (-1, 0, 1)] for dy in (-1, 0, 1)]
            entry["context"] = {"x": x, "y": y, "grid": ctx, "score": round(float(score[best]), 3)}
            entry["group"] = material_group(L, layer, n, entry["underModel"] / max(entry["count"], 1))
            entry["blend"] = layer == 1  # background 2 draws blended (D45)
            entry["selfTiles"] = bool(stats["right"].get(n, 0) + stats["down"].get(n, 0))
            tiles[str(n)] = entry
        out["layers"][str(layer)] = {
            "width": int(g.shape[1]), "height": int(g.shape[0]),
            "cellsDrawn": int(drawn.sum()), "cellsReplaced": int(rep.sum()),
            "tilesDrawn": sum(1 for t in tiles.values() if t["drawnAsTile"]),
            "tilesReplacedOnly": sum(1 for t in tiles.values() if not t["drawnAsTile"]),
            "tiles": tiles,
        }
    return out


def cmd_inventory(args) -> None:
    L = LevelData(Path(args.data), args.level)
    inv = build_inventory(L)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    (work / "inventory.json").write_text(json.dumps(inv, indent=1) + "\n")
    for layer, d in inv["layers"].items():
        groups = Counter(t["group"] for t in d["tiles"].values() if t["drawnAsTile"])
        print(f"layer {layer}: {d['tilesDrawn']} tiles drawn ({d['cellsDrawn']} cells), {d['tilesReplacedOnly']} only under "
              f"models ({d['cellsReplaced']} cells replaced); groups {dict(groups)}")
    print(f"-> {work / 'inventory.json'}")


# --- Gemini input sheets -------------------------------------------------------------------------

GAP = 6  # units (original pixels) of black between cells and around them
CTX_PER_SHEET = 9
REGION_TILES = (7, 6)  # a continuous region: 7 x 6 tiles = 168 x 168 px, square
TARGET_SIDE = 1024  # px, roughly what Gemini answers with

MATERIALS = {
    "brown": "rocky brown dirt, stones and earth ridges",
    "green": "dense green forest canopy",
    "brown-green-edges": "brown dirt meeting the ragged edge of green grass and forest",
    "blue": "icy translucent clouds drifting over the ground",
    "cyan": "icy translucent clouds drifting over the ground",
    "grey": "grey rock and metal",
}


def material_text(group: str) -> str:
    key = group.split("-", 1)[1].removesuffix("-modelled")
    return MATERIALS.get(key, f"{key.replace('-', ' ')} terrain")


def prompt_for(kind: str, group: str, layer: int, n: int) -> str:
    what = material_text(group)
    keep = ("Keep each piece exactly where it is, at the same size, with the same layout, shapes, outlines and colours, so it "
            "still lines up with the original pixel for pixel. Don't copy the pixel blocks or make pixel-shaped details: paint "
            "what they show, lit from above. The tiles repeat across the map, so keep the texture even up to the edges.")
    bg = (" The black background stays pure black: no glow, no shadow, no border." if layer > 0 or kind == "context" else "")
    if kind == "region":
        return ("This is a top-down view of a stretch of terrain from the 1995 shooter Tyrian, enlarged from pixel art. Repaint "
                f"it as high-resolution, detailed, painterly top-down terrain ({what}), like StarCraft Remastered. " + keep + bg +
                " No text, no frame.")
    return (f"This sheet is a grid of {n} pieces of top-down terrain from the 1995 shooter Tyrian (each a 3x3 block of map "
            f"tiles, enlarged from pixel art). Repaint every piece as high-resolution, detailed, painterly top-down terrain "
            f"({what}), like StarCraft Remastered, all in one consistent style. " + keep + bg + " No text, no grid lines.")


def fit_aspect(w: int, h: int) -> tuple[int, int, str]:
    """The smallest canvas (in units) of one of Gemini's aspect ratios that holds w x h."""
    best = None
    for a, b in ASPECTS:
        W = max(w, math.ceil(h * a / b))
        H = max(h, math.ceil(W * b / a))
        W = max(W, math.ceil(H * a / b))
        if best is None or W * H < best[0] * best[1]:
            best = (W, H, f"{a}:{b}")
    return best


def grid_for(n: int, cw: int, ch: int) -> tuple[int, int]:
    """Columns and rows for n cells: the biggest cells once the sheet is fitted to an aspect ratio
    and scaled to about TARGET_SIDE, then the least padding."""
    best = None
    for cols in range(1, n + 1):
        rows = math.ceil(n / cols)
        w, h = cols * cw + (cols + 1) * GAP, rows * ch + (rows + 1) * GAP
        W, H, _ = fit_aspect(w, h)
        key = (-max(1, round(TARGET_SIDE / max(W, H))), W * H - w * h, abs(W - H))
        if best is None or key < best[0]:
            best = (key, cols, rows)
    return best[1], best[2]


def balanced_chunks(items: list, size: int) -> list[list]:
    k = max(1, math.ceil(len(items) / size))
    base, extra = divmod(len(items), k)
    out, i = [], 0
    for j in range(k):
        m = base + (1 if j < extra else 0)
        out.append(items[i:i + m])
        i += m
    return out


def cell_units(L: LevelData, layer: int, grid: list[list[int]]) -> np.ndarray:
    """A block of tiles at 1x as palette indices, -1 where nothing is drawn (shown black)."""
    rows, cols = len(grid), len(grid[0])
    out = np.full((rows * TILE_H, cols * TILE_W), -1, np.int32)
    for r, row in enumerate(grid):
        for c, t in enumerate(row):
            if t < 0:
                continue
            px = L.tile(t).astype(np.int32)
            if layer > 0:
                px = np.where(px == 0, -1, px)
            out[r * TILE_H:(r + 1) * TILE_H, c * TILE_W:(c + 1) * TILE_W] = px
    return out


def units_rgb(L: LevelData, units: np.ndarray) -> np.ndarray:
    rgb = L.rgb[np.clip(units, 0, 255)]
    rgb[units < 0] = 0
    return rgb


def sheet_units(L: LevelData, sheet: dict) -> np.ndarray:
    """The whole sheet at 1x (units), palette indices, -1 = black."""
    s = sheet["scale"]
    canvas = np.full((sheet["height"] // s, sheet["width"] // s), -1, np.int32)
    for cell in sheet["cells"]:
        u = cell_units(L, sheet["layer"], cell["grid"])
        x, y = cell["x"] // s, cell["y"] // s
        canvas[y:y + u.shape[0], x:x + u.shape[1]] = u
    return canvas


def choose_regions(grid: np.ndarray, wanted: set[int]) -> list[tuple[int, int, set[int]]]:
    """Windows of REGION_TILES that together show every wanted tile away from the window's border
    (a border on the map's own edge is fine): greedy set cover."""
    h, w = grid.shape
    rw, rh = REGION_TILES
    cands = []
    for y0 in range(0, h - rh + 1):
        for x0 in range(0, w - rw + 1):
            xa, xb = (x0 if x0 == 0 else x0 + 1), (x0 + rw if x0 + rw == w else x0 + rw - 1)
            ya, yb = (y0 if y0 == 0 else y0 + 1), (y0 + rh if y0 + rh == h else y0 + rh - 1)
            inner = set(grid[ya:yb, xa:xb].ravel().tolist()) & wanted
            cands.append((x0, y0, inner))
    left, out = set(wanted), []
    while left:
        x0, y0, inner = max(cands, key=lambda c: (len(c[2] & left), len(c[2])))
        if not inner & left:
            break
        out.append((x0, y0, inner & left))
        left -= inner
    return out


def make_sheet(L: LevelData, name: str, kind: str, layer: int, group: str, cells: list[dict], priority: str) -> dict:
    cw = len(cells[0]["grid"][0]) * TILE_W
    ch = len(cells[0]["grid"]) * TILE_H
    cols, rows = grid_for(len(cells), cw, ch)
    w, h = cols * cw + (cols + 1) * GAP, rows * ch + (rows + 1) * GAP
    W, H, aspect = fit_aspect(w, h)
    scale = max(1, round(TARGET_SIDE / max(W, H)))
    pl, pt = (W - w) // 2, (H - h) // 2
    sheet = {"name": name, "file": f"{name}.png", "kind": kind, "layer": layer, "group": group, "priority": priority,
             "width": W * scale, "height": H * scale, "aspect": aspect, "scale": scale,
             "padding": {"left": pl * scale, "top": pt * scale, "right": (W - w - pl) * scale, "bottom": (H - h - pt) * scale},
             "grid": {"cols": cols, "rows": rows, "cellW": cw * scale, "cellH": ch * scale, "gap": GAP * scale},
             "prompt": prompt_for(kind, group, layer, len(cells)), "cells": []}
    for i, cell in enumerate(cells):
        c, r = i % cols, i // cols
        x = (pl + GAP + c * (cw + GAP)) * scale
        y = (pt + GAP + r * (ch + GAP)) * scale
        sheet["cells"].append({"index": i, "col": c, "row": r, "x": x, "y": y, "w": cw * scale, "h": ch * scale, **cell})
    return sheet


def build_sheets(L: LevelData, inv: dict) -> list[dict]:
    sheets = []
    for layer_s, d in inv["layers"].items():
        layer = int(layer_s)
        tiles = [t for t in d["tiles"].values() if t["drawnAsTile"]]
        if not tiles:
            continue
        groups = defaultdict(list)
        for t in sorted(tiles, key=lambda t: t["tile"]):
            groups[t["group"]].append(t)
        # A group of one or two tiles joins a group of the same colour (or the biggest), so no sheet
        # is nearly empty.
        for gname in sorted(groups, key=lambda k: len(groups[k])):
            if len(groups[gname]) >= 3 or len(groups) == 1:
                continue
            colour = gname.split("-")[1]
            others = [k for k in groups if k != gname]
            same = [k for k in others if colour in k.split("-")[1:]]
            into = max(same or others, key=lambda k: len(groups[k]))
            groups[into] = sorted(groups[into] + groups.pop(gname), key=lambda t: t["tile"])
        # Contexts: every layer, one material group per sheet. On the ground they are the alternative
        # to the regions below (send them for tiles a region painted badly).
        for group, ts in sorted(groups.items()):
            for k, chunk in enumerate(balanced_chunks(ts, CTX_PER_SHEET)):
                cells = [{"kind": "context", "mapX": t["context"]["x"] - 1, "mapY": t["context"]["y"] - 1,
                          "grid": [[v if v >= 0 else -1 for v in row] for row in t["context"]["grid"]],
                          "tiles": [{"tile": t["tile"], "col": 1, "row": 1, "interior": 1}]} for t in chunk]
                prio = "optional" if layer == 0 else "primary"
                sheets.append(make_sheet(L, f"ctx-{group}-{k + 1}", "context", layer, group, cells, prio))
        # Regions: the ground as continuous stretches of map, every tile inside at least one.
        if layer == 0:
            g = L.grids[0]
            wanted = {t["tile"] for t in tiles}
            for k, (x0, y0, _) in enumerate(choose_regions(g, wanted)):
                rw, rh = REGION_TILES
                sub = g[y0:y0 + rh, x0:x0 + rw]
                cell_tiles = []
                for r in range(rh):
                    for c in range(rw):
                        dx = min(c if x0 > 0 else 99, rw - 1 - c if x0 + rw < g.shape[1] else 99)
                        dy = min(r if y0 > 0 else 99, rh - 1 - r if y0 + rh < g.shape[0] else 99)
                        cell_tiles.append({"tile": int(sub[r, c]), "col": c, "row": r, "interior": int(min(dx, dy, 3))})
                cells = [{"kind": "region", "mapX": x0, "mapY": y0, "grid": sub.tolist(), "tiles": cell_tiles}]
                sheets.append(make_sheet(L, f"region-l0-{k + 1:02d}", "region", 0, "l0-ground", cells, "primary"))
    return sheets


def cmd_sheets(args) -> None:
    L = LevelData(Path(args.data), args.level)
    work = Path(args.work)
    inv_path = work / "inventory.json"
    inv = json.loads(inv_path.read_text()) if inv_path.exists() else build_inventory(L)
    out = work / "sheets"
    out.mkdir(parents=True, exist_ok=True)
    sheets = build_sheets(L, inv)
    for sh in sheets:
        units = sheet_units(L, sh)
        img = Image.fromarray(units_rgb(L, units)).resize((sh["width"], sh["height"]), Image.NEAREST)
        img.save(out / sh["file"])
    manifest = {"level": L.id, "shapes": L.shapes_name, "tileWidth": TILE_W, "tileHeight": TILE_H,
                "note": "x, y, w, h and padding in sheet px; grid = the cell's tiles as rows of tile numbers (-1 none); "
                        "tiles = which tile sits where in the cell (col, row in tiles) and how far it is from the cell's "
                        "border (interior, in tiles; the cutter prefers inner ones)",
                "sheets": sheets}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    for sh in sheets:
        print(f"{sh['file']}: {sh['priority']}, {sh['kind']}, {len(sh['cells'])} cells, {sh['grid']['cols']}x{sh['grid']['rows']}, "
              f"{sh['width']}x{sh['height']} ({sh['aspect']}), scale {sh['scale']}")
    print(f"-> {out / 'manifest.json'}")


# --- Fake answers (testing) ----------------------------------------------------------------------


def cmd_fake(args) -> None:
    """Each sheet upscaled with MMPX, then blurred, shifted, rescaled a little, colour-shifted and
    given a little noise, at Gemini's usual size: what a faithful but imperfect answer looks like."""
    from scipy import ndimage

    L = LevelData(Path(args.data), args.level)
    work = Path(args.work)
    manifest = json.loads((work / "sheets/manifest.json").read_text())
    out = work / "results-fake"
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    for k, sh in enumerate(manifest["sheets"]):
        units = sheet_units(L, sh)
        luma = L.luma_clear if sh["layer"] > 0 else L.luma
        f = 1 << math.ceil(math.log2(sh["scale"]))
        up = mmpx(np.clip(units, 0, 255).astype(np.uint8), luma, f)
        rgb = L.rgb[up].astype(np.float32)
        rgb[np.kron(units < 0, np.ones((f, f), bool))] = 0
        img = Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).resize((sh["width"], sh["height"]), Image.LANCZOS)
        a = np.asarray(img).astype(np.float32)
        # A small rescale about the centre and a shift, as Gemini's answers drift.
        zoom = 1 + rng.uniform(-0.015, 0.015)
        shift = rng.uniform(-6, 6, 2)
        h, w = a.shape[:2]
        cy, cx = h / 2, w / 2
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        sy, sx = (yy - cy - shift[1]) / zoom + cy, (xx - cx - shift[0]) / zoom + cx
        a = np.stack([ndimage.map_coordinates(a[..., c], [sy, sx], order=1, mode="constant") for c in range(3)], -1)
        a = ndimage.gaussian_filter(a, (1.5, 1.5, 0))
        a += ndimage.gaussian_filter(rng.normal(0, 10, a.shape[:2]), 1.0)[..., None]
        a = a * rng.uniform(0.94, 1.06, 3) + rng.uniform(-6, 6, 3)
        long = 1024
        size = (long, round(long * h / w)) if w >= h else (round(long * w / h), long)
        img = Image.fromarray(a.clip(0, 255).astype(np.uint8)).resize(size, Image.LANCZOS)
        ext = "jpg" if k % 3 == 2 else "png"  # answers come as either
        img.save(out / f"{sh['name']}.{ext}", quality=92) if ext == "jpg" else img.save(out / f"{sh['name']}.{ext}")
        print(f"{sh['name']}.{ext}: zoom {zoom:.3f}, shift {shift.round(1).tolist()}")
    print(f"-> {out}")


# --- Cutting -------------------------------------------------------------------------------------

LAMBDA = 0.15  # how strongly an edge strip keeps its own painting against its neighbours' (per unit of pair count)
STRIP_TEXELS = 4  # an edge strip is the mean of the outermost texels...
STRIP_SIGMA = 2.0  # ...smoothed along the edge
BAND_LO = 40  # texels over which a strip's correction fades into the tile
BAND_HI = 4  # texels at the edge set to the strip itself
REGION_BONUS = 0.06  # score for paintings from map regions over contexts (their texture matches the neighbours')
LOWFREQ = 16.0  # texels: shading broader than this follows the original tile (match_lowfreq)
SIGMA_REF = 3.0  # blur of the MMPX 8x silhouette for alpha, texels


def gray(a: np.ndarray) -> np.ndarray:
    return a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11


def ncc_search(I: np.ndarray, T: np.ndarray) -> tuple[float, int, int]:
    """Best zero-mean normalised cross-correlation of template T over image I (valid positions):
    (score, x, y) of T's top-left in I."""
    from scipy.signal import fftconvolve

    th, tw = T.shape
    if I.shape[0] < th or I.shape[1] < tw:
        return -1.0, 0, 0
    Tz = T - T.mean()
    tn = math.sqrt(float((Tz * Tz).sum())) or 1.0
    num = fftconvolve(I, Tz[::-1, ::-1], mode="valid")
    c1 = np.cumsum(np.cumsum(np.pad(I, ((1, 0), (1, 0))), 0), 1)
    c2 = np.cumsum(np.cumsum(np.pad(I * I, ((1, 0), (1, 0))), 0), 1)
    box = lambda c: c[th:, tw:] - c[:-th, tw:] - c[th:, :-tw] + c[:-th, :-tw]  # noqa: E731
    n = th * tw
    s1, s2 = box(c1), box(c2)
    var = np.maximum(s2 - s1 * s1 / n, 1e-6)
    ncc = num / (np.sqrt(var) * tn)
    y, x = np.unravel_index(int(np.argmax(ncc)), ncc.shape)
    return float(ncc[y, x]), int(x), int(y)


def resize_f(a: np.ndarray, w: int, h: int) -> np.ndarray:
    """Resize a float image (H, W) or (H, W, C) with PIL's bilinear/area filter."""
    if a.ndim == 2:
        return np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((w, h), Image.BILINEAR))
    return np.stack([resize_f(a[..., c], w, h) for c in range(a.shape[2])], -1)


def register_cell(art: np.ndarray, ref_rgb: np.ndarray, nominal: tuple[float, float, float, float], q: int = 3) -> dict:
    """Fit a cell's painting to its original picture: art px = (ax + u * k, ay + v * k) for unit
    (original pixel) coordinates (u, v) in the cell. `nominal` = (x0, y0, kx, ky) from the sheet's
    geometry. Searches a uniform rescale of +-6% and a shift of up to ~12% of the cell."""
    from scipy import ndimage

    x0, y0, kx, ky = nominal
    hu, wu = ref_rgb.shape[:2]
    m = 0.12 * max(wu, hu) + 4  # search margin, units
    cx, cy = x0 - m * kx, y0 - m * ky
    cw, ch = (wu + 2 * m) * kx, (hu + 2 * m) * ky
    H, W = art.shape[:2]
    # The search area resampled to q px per unit (clipped to the picture; out of bounds is black).
    pad = int(math.ceil(max(cw, ch)))
    big = np.pad(gray(art), pad)
    sx0, sy0 = int(round(cx)) + pad, int(round(cy)) + pad
    crop = big[sy0:sy0 + int(round(ch)), sx0:sx0 + int(round(cw))]
    Iw, Ih = int(round((wu + 2 * m) * q)), int(round((hu + 2 * m) * q))
    I = ndimage.gaussian_filter(resize_f(crop, Iw, Ih), q * 0.6)
    ref = gray(ref_rgb.astype(np.float32))
    best = (-2.0, 0, 0, 1.0)
    for s in np.arange(0.94, 1.0601, 0.01):
        tw, th = int(round(wu * q * s)), int(round(hu * q * s))
        T = ndimage.gaussian_filter(resize_f(np.kron(ref, np.ones((q, q))), tw, th), q * 0.6)
        score, ox, oy = ncc_search(I, T)
        if score > best[0]:
            best = (score, ox, oy, float(tw) / (wu * q))
    score, ox, oy, s = best
    fx, fy = cw / Iw, ch / Ih  # art px per I px
    return {"score": score, "ax": (sx0 - pad) + ox * fx, "ay": (sy0 - pad) + oy * fy, "kx": s * q * fx, "ky": s * q * fy}


def refine_tile(art_g: np.ndarray, ref_g: np.ndarray, fit: dict, u0: float, v0: float, q: int = 4) -> tuple[float, float, float]:
    """Shift-only refinement of one tile inside its cell: (score, du, dv) in units."""
    from scipy import ndimage

    m = 4.0  # units of context around the tile in the template and of slack in the search
    tu0, tv0 = max(u0 - m, 0), max(v0 - m, 0)
    tu1, tv1 = min(u0 + TILE_W + m, ref_g.shape[1]), min(v0 + TILE_H + m, ref_g.shape[0])
    T = ref_g[int(tv0):int(tv1), int(tu0):int(tu1)]
    T = ndimage.gaussian_filter(np.kron(T, np.ones((q, q))), q * 0.5)
    # Sample the art over the template's box plus slack, at q px per unit.
    su = np.arange((tu0 - m) * q, (tu1 + m) * q) / q + 0.5 / q
    sv = np.arange((tv0 - m) * q, (tv1 + m) * q) / q + 0.5 / q
    X = fit["ax"] + su * fit["kx"] - 0.5
    Y = fit["ay"] + sv * fit["ky"] - 0.5
    I = ndimage.map_coordinates(art_g, np.meshgrid(Y, X, indexing="ij"), order=1, mode="constant")
    I = ndimage.gaussian_filter(I, q * 0.5)
    score, ox, oy = ncc_search(I, T)
    return score, ox / q - m, oy / q - m


def sample_tile(art: np.ndarray, fit: dict, u0: float, v0: float) -> np.ndarray:
    """The tile at (u0, v0) units in its cell, resampled from the art at SCALE texels per unit."""
    from scipy import ndimage

    u = u0 + (np.arange(TILE_W * SCALE) + 0.5) / SCALE
    v = v0 + (np.arange(TILE_H * SCALE) + 0.5) / SCALE
    X = fit["ax"] + u * fit["kx"] - 0.5
    Y = fit["ay"] + v * fit["ky"] - 0.5
    src = art
    k = min(fit["kx"], fit["ky"])
    if k > SCALE:  # the answer is finer than the atlas: prefilter
        src = ndimage.gaussian_filter(art, (0.5 * k / SCALE, 0.5 * k / SCALE, 0))
    grid = np.meshgrid(Y, X, indexing="ij")
    return np.stack([ndimage.map_coordinates(src[..., c], grid, order=3, mode="nearest") for c in range(3)], -1).clip(0, 255)


def colour_transfer(hd: np.ndarray, orig_rgb: np.ndarray, mask1: np.ndarray) -> np.ndarray:
    """Match the painting's per-channel mean and low-frequency contrast to the original tile's
    (over its visible pixels), so the palette stays close to the game's."""
    from scipy import ndimage

    m8 = np.kron(mask1, np.ones((SCALE, SCALE), bool))
    if mask1.sum() < 8:
        return hd
    lo_o = ndimage.gaussian_filter(orig_rgb.astype(np.float32), (1, 1, 0))
    hd1 = hd.reshape(TILE_H, SCALE, TILE_W, SCALE, 3).mean((1, 3))
    lo_h = ndimage.gaussian_filter(hd1, (1, 1, 0))
    out = hd.copy()
    for c in range(3):
        mo, mh = orig_rgb[..., c][mask1].mean(), hd[..., c][m8].mean()
        so, sh = lo_o[..., c][mask1].std(), lo_h[..., c][mask1].std()
        gain = float(np.clip(so / sh, 0.7, 1.4)) if sh > 1 else 1.0
        out[..., c] = (hd[..., c] - mh) * gain + mo
    return out.clip(0, 255)


def context_units(L: LevelData, layer: int, tile: int, usual: dict) -> np.ndarray:
    """The tile among its usual neighbours, 3x3 tiles at 1x (palette indices; -1 = empty). Off the
    map (-2) the tile's own copy stands in, as the clamped upscale would."""
    pos = {"upLeft": (0, 0), "up": (0, 1), "upRight": (0, 2), "left": (1, 0), "right": (1, 2),
           "downLeft": (2, 0), "down": (2, 1), "downRight": (2, 2)}
    grid = [[tile] * 3 for _ in range(3)]
    for k, (r, c) in pos.items():
        n = usual.get(k, tile)
        grid[r][c] = tile if n == -2 else n
    return cell_units(L, layer, grid)


def edge_reference(L: LevelData, layer: int, tile: int, usual: dict) -> tuple[np.ndarray, np.ndarray]:
    """The original tile upscaled smoothly among its usual neighbours: the MMPX 8x upscale, blurred
    a little, centre cut out (RGB float, and coverage 0..1). The coverage is the alpha of layers 1-2:
    the original silhouette with a ~1-2 texel soft edge, continuous with the usual neighbours'."""
    from scipy import ndimage

    u = context_units(L, layer, tile, usual)
    luma = L.luma_clear if layer > 0 else L.luma
    up = mmpx(np.clip(u, 0, 255).astype(np.uint8), luma, SCALE)
    vis = np.kron(u >= 0, np.ones((SCALE, SCALE), bool)) & ((up != 0) if layer > 0 else True)
    rgb = L.rgb[up].astype(np.float32)
    m = vis.astype(np.float32)
    num = ndimage.gaussian_filter(rgb * m[..., None], (SIGMA_REF, SIGMA_REF, 0))
    den = ndimage.gaussian_filter(m, SIGMA_REF)
    ref = num / np.maximum(den, 1e-3)[..., None]
    cov = ndimage.gaussian_filter(m, SIGMA_REF)
    alpha = np.clip((cov - 0.5) / 0.3 + 0.5, 0, 1)  # a steep ramp: a ~1-2 texel soft silhouette
    ys, xs = slice(TILE_H * SCALE, 2 * TILE_H * SCALE), slice(TILE_W * SCALE, 2 * TILE_W * SCALE)
    return ref[ys, xs], alpha[ys, xs]


def smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


OPPOSITE = {"left": "right", "right": "left", "up": "down", "down": "up"}


def edge_strip(img: np.ndarray, side: str) -> np.ndarray:
    """The tile's edge on one side as a 1D strip (along the edge, channels), smoothed along it."""
    from scipy.ndimage import gaussian_filter1d

    k = STRIP_TEXELS
    strip = {"left": img[:, :k].mean(1), "right": img[:, -k:].mean(1), "up": img[:k].mean(0), "down": img[-k:].mean(0)}[side]
    return gaussian_filter1d(strip, STRIP_SIGMA, axis=0, mode="nearest")


def map_pairs(grid: np.ndarray, drawn: np.ndarray, have) -> Counter:
    """How often each tile meets each other tile in the map: ("h", left, right) and ("v", top, bottom)."""
    pairs = Counter()
    h, w = grid.shape
    ok = drawn & np.isin(grid, list(have))
    a, b = grid[:, :-1][ok[:, :-1] & ok[:, 1:]], grid[:, 1:][ok[:, :-1] & ok[:, 1:]]
    pairs.update(("h", int(x), int(y)) for x, y in zip(a, b))
    a, b = grid[:-1][ok[:-1] & ok[1:]], grid[1:][ok[:-1] & ok[1:]]
    pairs.update(("v", int(x), int(y)) for x, y in zip(a, b))
    return pairs


def solve_strips(tiles: dict[int, np.ndarray], pairs: Counter, lam: float = LAMBDA) -> dict[tuple[int, str], np.ndarray]:
    """The edge every tile side is pulled to, chosen for all sides at once: least squares over
    every pair of tiles the map puts side by side (weighted by how often) that the two facing strips
    be equal, plus a weaker pull of each strip towards the tile's own painting. Facing strips of
    the most frequent pairs come out (nearly) identical; a tile with many different neighbours on
    a side gets the strip that is closest to all of them, weighted by frequency. Solved per
    orientation and per texel along the edge (one small SPD system, many right-hand sides)."""
    out = {}
    for o, (sa, sb) in {"h": ("right", "left"), "v": ("down", "up")}.items():
        nodes = sorted({(n, side) for n in tiles for side in (sa, sb)})
        idx = {nd: i for i, nd in enumerate(nodes)}
        N = len(nodes)
        M = np.zeros((N, N))
        deg = np.zeros(N)
        for (po, a, b), c in pairs.items():
            if po != o:
                continue
            i, j = idx[(a, sa)], idx[(b, sb)]
            if i == j:
                continue
            M[i, i] += c
            M[j, j] += c
            M[i, j] -= c
            M[j, i] -= c
            deg[i] += c
            deg[j] += c
        lam_i = lam * np.maximum(deg, 1)
        M[np.arange(N), np.arange(N)] += lam_i
        own = np.stack([edge_strip(tiles[n], side) for n, side in nodes])  # (N, L, C)
        rhs = (lam_i[:, None, None] * own).reshape(N, -1)
        sol = np.linalg.solve(M, rhs).reshape(own.shape)
        for nd, i in idx.items():
            out[nd] = sol[i]
    return out


def apply_strips(img: np.ndarray, strips: dict[str, np.ndarray], band_lo: float = BAND_LO, band_hi: float = BAND_HI) -> np.ndarray:
    """Move each edge of the tile to its strip: the difference fades in over `band_lo` texels
    (the painting's detail stays), and the outermost `band_hi` texels become the strip."""
    H, W = img.shape[:2]
    y = np.arange(H)[:, None] + 0.5
    x = np.arange(W)[None, :] + 0.5
    dist = {"left": np.broadcast_to(x, (H, W)), "right": np.broadcast_to(W - x, (H, W)),
            "up": np.broadcast_to(y, (H, W)), "down": np.broadcast_to(H - y, (H, W))}

    def spread(strip: np.ndarray, side: str) -> np.ndarray:
        return np.broadcast_to(strip[:, None, :] if side in ("left", "right") else strip[None, :, :], img.shape)

    out = img.astype(np.float32).copy()
    if band_lo > 0:
        for side, e in strips.items():
            w = (1 - smoothstep(0, band_lo, dist[side]))[..., None]
            out += w * spread(e - edge_strip(img, side), side)
    if band_hi > 0:
        for side, e in strips.items():
            w = (1 - smoothstep(0, band_hi, dist[side]))[..., None]
            out = out * (1 - w) + spread(e, side) * w
    return out.clip(0, 255)


def bleed(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Colour under zero alpha from the nearest visible texel (no dark fringes when filtered)."""
    from scipy import ndimage

    vis = alpha > 0.02
    if vis.all() or not vis.any():
        return rgb
    _, (iy, ix) = ndimage.distance_transform_edt(~vis, return_indices=True)
    return rgb[iy, ix]


BLOCKY_FREE = 2.0  # pixel-block ratio a painting may have before it costs score
BLOCKY_COST = 0.15  # score per unit of pixel-block ratio above BLOCKY_FREE
NOVEL_FREE = 1.0  # novel-detail excess over the tile's median candidate that is free
NOVEL_COST = 0.03  # score per unit of novel-detail excess above NOVEL_FREE


def blockiness(hd: np.ndarray) -> float:
    """How much the painting kept the original's pixel blocks: the colour steps between texels,
    averaged by their phase in the 8-texel period of an original pixel; the strongest phase over the
    mean (x or y). A painting is ~1.0-1.5; a copy of the pixel blocks ~3-4 (steps all at one phase)."""
    g = gray(hd.astype(np.float32))
    dx = np.abs(np.diff(g, axis=1)).mean(0)
    dy = np.abs(np.diff(g, axis=0)).mean(1)
    px = np.array([dx[k::SCALE].mean() for k in range(SCALE)])
    py = np.array([dy[k::SCALE].mean() for k in range(SCALE)])
    return float(max(px.max() / max(px.mean(), 1e-3), py.max() / max(py.mean(), 1e-3)))


DEBLOCK_FROM = 1.6  # pixel-block ratio from which a chosen painting's block edges are softened
DEBLOCK_FULL = 2.4  # ratio at which they are softened fully


def deblock(hd: np.ndarray, start: float = DEBLOCK_FROM, full: float = DEBLOCK_FULL) -> np.ndarray:
    """Soften the pixel-block edges a painting kept (blockiness above `start`): around the texel
    columns and rows where the 8-texel period's steps are strongest, mix in a blur of ~2.5 texels,
    fading out 3 texels either side. The blocks' insides keep their painted detail. Some tiles have
    no better painting (every answer copied the blocks, D59); in game their grid shows as a
    rectangle of pixels in the soft ground."""
    from scipy import ndimage

    b = blockiness(hd)
    k = float(np.clip((b - start) / max(full - start, 1e-3), 0.0, 1.0))
    if k <= 0:
        return hd
    g = gray(hd.astype(np.float32))
    h, w = g.shape

    def boundary_weight(steps: np.ndarray, n: int) -> np.ndarray:
        prof = np.array([steps[p::SCALE].mean() for p in range(SCALE)])
        phase = int(prof.argmax())  # the step between texel phase and phase+1 of each period
        pos = np.arange(n, dtype=np.float32)
        d = np.abs(((pos - phase - 0.5) + SCALE / 2) % SCALE - SCALE / 2)  # distance to the nearest edge
        ratio = prof.max() / max(prof.mean(), 1e-3)
        return np.clip(1.0 - d / 3.0, 0.0, 1.0) * (ratio > 1.3)

    wx = boundary_weight(np.abs(np.diff(g, axis=1)).mean(0), w)
    wy = boundary_weight(np.abs(np.diff(g, axis=0)).mean(1), h)
    wgt = (np.maximum(wx[None, :], wy[:, None]) * k)[..., None]
    soft = ndimage.gaussian_filter(hd.astype(np.float32), (2.5, 2.5, 0), mode="nearest")
    return hd * (1 - wgt) + soft * wgt


def novel_detail(hd: np.ndarray, orig_rgb: np.ndarray, mask1: np.ndarray) -> float:
    """Salient detail the original tile doesn't have (a twig, a crack, a bright blob Gemini made
    up): local high-pass energy of the painting minus the original's, 99.8th percentile. Such marks
    are what makes a tile's repeat visible across the map."""
    from scipy import ndimage

    g = gray(hd.astype(np.float32))
    o = np.kron(gray(orig_rgb.astype(np.float32)), np.ones((SCALE, SCALE)))
    hp = np.abs(g - ndimage.gaussian_filter(g, 6))
    ohp = np.abs(o - ndimage.gaussian_filter(o, 6))
    e = ndimage.gaussian_filter(hp, 4) - ndimage.gaussian_filter(ohp, 4)
    m8 = np.kron(mask1, np.ones((SCALE, SCALE), bool))
    return float(np.percentile(e[m8], 99.8)) if m8.any() else 0.0


def load_result(results: Path, name: str) -> np.ndarray | None:
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = results / f"{name}.{ext}"
        if p.exists():
            return np.asarray(Image.open(p).convert("RGB")).astype(np.float32)
    return None


def candidates(L: LevelData, manifest: dict, results: Path) -> dict[tuple[int, int], list[dict]]:
    """Every painting of every tile found in the answers, registered and colour-matched."""
    out: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for sh in manifest["sheets"]:
        art = load_result(results, sh["name"])
        if art is None:
            continue
        H, W = art.shape[:2]
        fx, fy = W / sh["width"], H / sh["height"]
        if abs(fx / fy - 1) > 0.03:
            print(f"  {sh['name']}: answer {W}x{H} isn't the sheet's aspect ({sh['width']}x{sh['height']}); skipped")
            continue
        art_g = gray(art)
        layer = sh["layer"]
        for cell in sh["cells"]:
            ref_units = cell_units(L, layer, cell["grid"])
            ref_rgb = units_rgb(L, ref_units)
            nominal = (cell["x"] * fx, cell["y"] * fy, sh["scale"] * fx, sh["scale"] * fy)
            fit = register_cell(art, ref_rgb, nominal)
            ref_g = gray(ref_rgb.astype(np.float32))
            for t in cell["tiles"]:
                n = t["tile"]
                if n < 0:
                    continue
                u0, v0 = t["col"] * TILE_W, t["row"] * TILE_H
                score, du, dv = refine_tile(art_g, ref_g, fit, u0, v0)
                if abs(du) > 3 or abs(dv) > 3:
                    score, du, dv = score - 0.2, 0.0, 0.0
                hd = sample_tile(art, fit, u0 + du, v0 + dv)
                px = L.tile(n)
                mask1 = px != 0 if layer > 0 else np.ones_like(px, bool)
                hd = colour_transfer(hd, L.rgb[px].astype(np.float32), mask1)
                hd1 = hd.reshape(TILE_H, SCALE, TILE_W, SCALE, 3).mean((1, 3))
                err = float(np.abs(hd1 - L.rgb[px])[mask1].mean() / 255) if mask1.any() else 0.0
                blk = blockiness(hd)
                out[(layer, n)].append({"hd": hd, "ncc": score, "cellScore": fit["score"], "err": err,
                                        "interior": t["interior"], "sheet": sh["name"], "cell": cell["index"],
                                        "blocky": blk, "novel": novel_detail(hd, L.rgb[px], mask1),
                                        "score": score - err + 0.05 * min(t["interior"], 2),
                                        "fit": {k: round(v, 3) for k, v in fit.items()}})
        print(f"  {sh['name']}: {len(sh['cells'])} cells, answer {W}x{H} ({sh['scale'] * fx:.2f} px per original px)")
    return out


def pack_atlas(tiles: dict[int, np.ndarray], channels: int) -> tuple[np.ndarray, dict]:
    """Tiles on a grid of 16-aligned rects with 16 px edge-extended gutters (FORMAT.md rules 1-3)."""
    tw, th, g = TILE_W * SCALE, TILE_H * SCALE, 16
    n = len(tiles)
    cols = max(1, min(19, math.ceil(math.sqrt(n * (th + g) / (tw + g)))))
    rows = math.ceil(n / cols)
    W, H = g + cols * (tw + g), g + rows * (th + g)
    atlas = np.zeros((H, W, channels), np.float32)
    rects = {}
    order = sorted(tiles)
    for pass_pad in (g, g // 2):  # wide pads first (atlas border), then each tile's own half gutter
        for i, n_ in enumerate(order):
            x, y = g + (i % cols) * (tw + g), g + (i // cols) * (th + g)
            atlas[y - pass_pad:y + th + pass_pad, x - pass_pad:x + tw + pass_pad] = np.pad(tiles[n_], ((pass_pad, pass_pad), (pass_pad, pass_pad), (0, 0)), mode="edge")
    for i, n_ in enumerate(order):
        x, y = g + (i % cols) * (tw + g), g + (i // cols) * (th + g)
        atlas[y:y + th, x:x + tw] = tiles[n_]
        rects[str(n_)] = {"x": x, "y": y, "w": tw, "h": th}
    return atlas, rects


def match_lowfreq(L: LevelData, inv_tile: dict, layer: int, n: int, hd: np.ndarray, sigma: float) -> np.ndarray:
    """Give the painting the original's large-scale shading: its blur at `sigma` texels is swapped
    for the original's (nearest upscale among the tile's usual neighbours, same blur; visible
    pixels only on layers 1-2). Gemini's paintings drift in brightness inside a tile (a darker
    corner, a lighter band), which turns into a visible grid when the tile repeats; the detail
    finer than `sigma` stays the painting's."""
    from scipy import ndimage

    if sigma <= 0:
        return hd
    u = context_units(L, layer, n, inv_tile["usual"])
    vis = (u >= 0) & ((u != 0) if layer > 0 else True)
    rgb = np.kron(L.rgb[np.clip(u, 0, 255)].astype(np.float32), np.ones((SCALE, SCALE, 1)))
    m = np.kron(vis, np.ones((SCALE, SCALE))).astype(np.float32)
    ys, xs = slice(TILE_H * SCALE, 2 * TILE_H * SCALE), slice(TILE_W * SCALE, 2 * TILE_W * SCALE)
    lo_o = (ndimage.gaussian_filter(rgb * m[..., None], (sigma, sigma, 0))
            / np.maximum(ndimage.gaussian_filter(m, sigma), 1e-3)[..., None])[ys, xs]
    mc = m[ys, xs]
    lo_h = (ndimage.gaussian_filter(hd * mc[..., None], (sigma, sigma, 0), mode="nearest")
            / np.maximum(ndimage.gaussian_filter(mc, sigma, mode="nearest"), 1e-3)[..., None])
    return (hd + (lo_o - lo_h) * (mc[..., None] > 0)).clip(0, 255)


def prepare_tile(L: LevelData, inv_tile: dict, layer: int, n: int, hd: np.ndarray) -> np.ndarray:
    """The painting with alpha (layers 1-2: the original silhouette; colour bled under it)."""
    if layer == 0:
        return hd.astype(np.float32)
    _, alpha = edge_reference(L, layer, n, inv_tile["usual"])
    return np.concatenate([bleed(hd, alpha), alpha[..., None] * 255], -1).astype(np.float32)


def cmd_cut(args) -> None:
    L = LevelData(Path(args.data), args.level)
    work = Path(args.work)
    inv = json.loads((work / "inventory.json").read_text())
    manifest = json.loads((work / "sheets/manifest.json").read_text())
    results = Path(args.results) if args.results else work / "results"
    print(f"cutting answers in {results}")
    cache = Path(args.cache) if args.cache else None
    if cache and cache.exists():
        import pickle

        cands = pickle.loads(cache.read_bytes())
        print(f"  candidates from {cache} (delete it after changing the answers)")
    else:
        cands = candidates(L, manifest, results)
        if cache:
            import pickle

            cache.write_bytes(pickle.dumps(cands))
    exclude = {s.strip() for s in (args.exclude or "").split(",") if s.strip()}
    picks = dict(s.strip().split("=", 1) for s in (args.pick or "").split(",") if s.strip())
    out_dir = Path(args.out) / L.shapes_name
    out_dir.mkdir(parents=True, exist_ok=True)
    models = load_models(L.shapes_file)
    atlas_manifest = {"version": 1, "scale": SCALE, "tileWidth": TILE_W, "tileHeight": TILE_H,
                      "credit": "Painted with Google Gemini from Tyrian's background tiles (Daniel Cook's art), cut and made "
                                "seamless by tools/terrain_hd.py; see CREDITS.md",
                      "layers": {}}
    report = {}
    for layer_s, d in inv["layers"].items():
        layer = int(layer_s)
        done = {}
        for key, t in d["tiles"].items():
            n = int(key)
            if not t["drawnAsTile"] or not cands.get((layer, n)):
                continue
            if f"{layer}:{n}" in exclude:
                report[f"{layer}:{n}"] = {"excluded": True}
                continue
            # Made-up marks cost against the tile's other paintings (a canopy has more detail
            # than dirt, so the measure is relative to the tile's median candidate).
            med = float(np.median([c["novel"] for c in cands[(layer, n)]]))
            for c in cands[(layer, n)]:
                c["score"] -= NOVEL_COST * max(0.0, c["novel"] - med - NOVEL_FREE) + args.blocky_cost * max(0.0, c["blocky"] - args.blocky_free)
                c["score"] += args.region_bonus if c["sheet"].startswith("region-") else 0.0
            cs = sorted(cands[(layer, n)], key=lambda c: -c["score"])
            if f"{layer}:{n}" in picks:  # a hand pick after looking at the contact sheets
                want = picks[f"{layer}:{n}"]
                cs = [c for c in cs if f"{c['sheet']}#{c['cell']}" == want] + [c for c in cs if f"{c['sheet']}#{c['cell']}" != want]
                assert f"{cs[0]['sheet']}#{cs[0]['cell']}" == want, f"--pick {layer}:{n}={want}: no such candidate"
            good = [c for c in cs if c["score"] >= cs[0]["score"] - 0.05] if args.combine == "mean" else cs[:1]
            hd = np.mean([c["hd"] for c in good], 0)
            soft = deblock(hd, args.deblock_from, args.deblock_full) if args.deblock_from > 0 else hd
            deblocked = soft is not hd
            hd = soft
            done[n] =prepare_tile(L, t, layer, n, match_lowfreq(L, t, layer, n, hd, args.lowfreq))
            report[f"{layer}:{n}"] = {"from": [f"{c['sheet']}#{c['cell']}" for c in good], "score": round(cs[0]["score"], 3),
                                      "ncc": round(cs[0]["ncc"], 3), "colourErr": round(cs[0]["err"], 3),
                                      "blocky": round(cs[0]["blocky"], 2), "novel": round(cs[0]["novel"], 1),
                                      "candidates": len(cs), **({"picked": True} if f"{layer}:{n}" in picks else {}),
                                      **({"deblocked": round(blockiness(hd), 2)} if deblocked else {})}
        if not done:
            continue
        # Seams: every side's edge strip solved jointly over the pairs the map has, then applied.
        if args.band_lo > 0 or args.band_hi > 0:
            g = L.grids[layer]
            rep, _ = replaced_mask(g, layer, models)
            # Colour only: alpha stays the original silhouette (averaging it across a pair would put
            # a faint line of cloud where one tile's edge is empty and its neighbour's isn't).
            strips = solve_strips({n: img[..., :3] for n, img in done.items()}, map_pairs(g, (g >= 0) & ~rep, done), args.lam)
            for n, img in done.items():
                img[..., :3] = apply_strips(img[..., :3], {side: strips[(n, side)] for side in OPPOSITE}, args.band_lo, args.band_hi)
        ch = 3 if layer == 0 else 4
        atlas, rects = pack_atlas(done, ch)
        img = Image.fromarray(atlas.round().clip(0, 255).astype(np.uint8), "RGB" if ch == 3 else "RGBA")
        name = f"{layer}.webp"
        if args.lossless:
            img.save(out_dir / name, lossless=True, method=6)
        else:
            img.save(out_dir / name, quality=92, method=6, alpha_quality=100)
        atlas_manifest["layers"][layer_s] = {"image": name, "width": img.width, "height": img.height, "tiles": rects}
        missing = [k for k, t in d["tiles"].items() if t["drawnAsTile"] and int(k) not in done]
        print(f"layer {layer}: {len(done)} tiles -> {out_dir / name} ({img.width}x{img.height})"
              + (f"; no art yet for {len(missing)}: {' '.join(missing)}" if missing else ""))
    (out_dir / "manifest.json").write_text(json.dumps(atlas_manifest, indent=1) + "\n")
    (work / "cut-report.json").write_text(json.dumps(report, indent=1) + "\n")
    weak = [k for k, r in report.items() if r.get("ncc", 1.0) < 0.5]
    print(f"-> {out_dir / 'manifest.json'}; per tile: {work / 'cut-report.json'}" + (f"; weak fits (ncc < 0.5): {' '.join(weak)}" if weak else ""))


# --- Check --------------------------------------------------------------------------------------


def load_atlas(out_root: Path, shapes: str) -> dict[int, dict[int, np.ndarray]]:
    d = out_root / shapes
    m = json.loads((d / "manifest.json").read_text())
    tiles: dict[int, dict[int, np.ndarray]] = {}
    for layer_s, lay in m["layers"].items():
        img = np.asarray(Image.open(d / lay["image"]).convert("RGBA")).astype(np.float32)
        tiles[int(layer_s)] = {int(k): img[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]] for k, r in lay["tiles"].items()}
    return tiles


def seam_stats(tiles: dict[int, np.ndarray], grid: np.ndarray, drawn: np.ndarray, band: int = 8) -> dict:
    """Colour steps across every tile edge the map has (both sides with HD art), against the same
    steps between neighbouring texels (and neighbouring `band`-texel strips) inside tiles. Alpha
    weights the steps on translucent layers. 0-255 RGB, mean abs per channel."""
    pairs = map_pairs(grid, drawn, tiles)
    occ = Counter(int(t) for t in grid[drawn] if int(t) in tiles)

    def step(p, q):  # p, q: (N, C) strips facing each other; returns weighted mean abs diff
        wgt = np.minimum(p[:, 3], q[:, 3]) / 255
        if wgt.sum() < 1:
            return None
        return float((np.abs(p[:, :3] - q[:, :3]).mean(1) * wgt).sum() / wgt.sum())

    edge_t, edge_b, rows = [], [], []
    for (o, a, b), n in pairs.items():
        A, B = tiles[a], tiles[b]
        if o == "h":
            t = step(A[:, -1], B[:, 0])
            bb = step(A[:, -band:].mean(1), B[:, :band].mean(1))
        else:
            t = step(A[-1], B[0])
            bb = step(A[-band:].mean(0), B[:band].mean(0))
        if t is None:
            continue
        edge_t.append((t, n))
        edge_b.append((bb, n))
        rows.append({"pair": f"{a}{'|' if o == 'h' else '/'}{b}", "count": n, "texelStep": round(t, 2), "bandStep": round(bb, 2)})
    in_t, in_b = [], []
    for n_, T in tiles.items():
        k = occ.get(n_, 0)
        if not k:
            continue
        vals = [step(T[:, j], T[:, j + 1]) for j in range(T.shape[1] - 1)]
        vals += [step(T[i], T[i + 1]) for i in range(T.shape[0] - 1)]
        bvals = [step(T[:, c - band:c].mean(1), T[:, c:c + band].mean(1)) for c in range(band, T.shape[1] - band + 1, band)]
        bvals += [step(T[c - band:c].mean(0), T[c:c + band].mean(0)) for c in range(band, T.shape[0] - band + 1, band)]
        vals = [v for v in vals if v is not None]
        bvals = [v for v in bvals if v is not None]
        if vals:
            in_t.append((float(np.mean(vals)), k))
            in_b.append((float(np.mean(bvals)), k))
    wm = lambda xs: sum(v * n for v, n in xs) / max(sum(n for _, n in xs), 1)  # noqa: E731
    et, it, eb, ib = wm(edge_t), wm(in_t), wm(edge_b), wm(in_b)
    for r in rows:
        r["ratio"] = round(r["texelStep"] / max(it, 1e-3), 2)
    rows.sort(key=lambda r: -r["texelStep"] * math.sqrt(r["count"]))
    return {"edges": sum(n for _, n in edge_t), "edgeTexelStep": round(et, 2), "insideTexelStep": round(it, 2),
            "texelRatio": round(et / max(it, 1e-3), 3), "edgeBandStep": round(eb, 2), "insideBandStep": round(ib, 2),
            "bandRatio": round(eb / max(ib, 1e-3), 3), "worst": rows[:15]}


def cmd_check(args) -> None:
    L = LevelData(Path(args.data), args.level)
    work = Path(args.work)
    out = work / "check"
    out.mkdir(parents=True, exist_ok=True)
    atlas = load_atlas(Path(args.out), L.shapes_name)
    models = load_models(L.shapes_file)
    report = {}
    for layer, tiles in sorted(atlas.items()):
        g = L.grids[layer]
        rep, _ = replaced_mask(g, layer, models)
        drawn = (g >= 0) & ~rep
        st = seam_stats(tiles, g, drawn)
        report[str(layer)] = st
        print(f"layer {layer}: {st['edges']} edges; texel step across edges {st['edgeTexelStep']} vs inside {st['insideTexelStep']} "
              f"(ratio {st['texelRatio']}); 8-texel band step {st['edgeBandStep']} vs {st['insideBandStep']} (ratio {st['bandRatio']})")
        # Contact sheets: original (nearest) | HD, at 4 px per original pixel, `rows` map rows each.
        S = 4
        k = SCALE // S
        H, W = g.shape
        n_sheets = 0
        for y0 in range(0, H, args.rows):
            sub = g[y0:y0 + args.rows]
            dsub = drawn[y0:y0 + args.rows]
            if not any(int(t) in tiles for t in sub[dsub]):
                continue
            rh = sub.shape[0]
            img = np.full((rh * TILE_H * S, 2 * W * TILE_W * S + 16, 3), 40, np.float32)
            for r in range(rh):
                for c in range(W):
                    if not dsub[r, c]:
                        continue
                    t = int(sub[r, c])
                    px = L.tile(t)
                    o = np.kron(L.rgb[px].astype(np.float32), np.ones((S, S, 1)))
                    oa = np.kron((px != 0) if layer > 0 else np.ones_like(px, bool), np.ones((S, S))).astype(np.float32)[..., None]
                    ys, xs = r * TILE_H * S, c * TILE_W * S
                    cell = img[ys:ys + TILE_H * S, xs:xs + TILE_W * S]
                    img[ys:ys + TILE_H * S, xs:xs + TILE_W * S] = cell * (1 - oa) + o * oa
                    xh = xs + W * TILE_W * S + 16
                    if t in tiles:
                        hd = tiles[t].reshape(TILE_H * S, k, TILE_W * S, k, 4).mean((1, 3))
                        a = hd[..., 3:] / 255
                        cell = img[ys:ys + TILE_H * S, xh:xh + TILE_W * S]
                        img[ys:ys + TILE_H * S, xh:xh + TILE_W * S] = cell * (1 - a) + hd[..., :3] * a
                    else:
                        cell = img[ys:ys + TILE_H * S, xh:xh + TILE_W * S]
                        img[ys:ys + TILE_H * S, xh:xh + TILE_W * S] = cell * (1 - oa) + o * oa
            Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(out / f"l{layer}-rows{y0:03d}.jpg", quality=88)
            n_sheets += 1
        print(f"  {n_sheets} contact sheets (original | HD) in {out}")
    (out / "seams.json").write_text(json.dumps(report, indent=1) + "\n")
    print(f"-> {out / 'seams.json'}")


# --- CLI -----------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(ROOT / "data"), help="the game data (default data/)")
    ap.add_argument("--level", default="1-9", help="episode-levelfile, as reference/tiles names levels (default 1-9, TYRIAN)")
    ap.add_argument("--work", default=str(ROOT / "reference/terrain-hd"), help="working folder (inventory, sheets, results, check)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inventory", help="list the tiles the level draws")
    sub.add_parser("sheets", help="make the Gemini input sheets and their manifest")
    f = sub.add_parser("fake", help="stand-in Gemini answers for testing")
    f.add_argument("--seed", type=int, default=1)
    c = sub.add_parser("cut", help="cut Gemini's answers into atlases")
    c.add_argument("--results", help="folder of answers (default WORK/results)")
    c.add_argument("--out", default=str(ROOT / "public/art/terrain"), help="atlas root (default public/art/terrain)")
    c.add_argument("--combine", choices=["best", "mean"], default="best", help="one candidate per tile, or the mean of the good ones")
    c.add_argument("--blocky-free", type=float, default=BLOCKY_FREE, help=f"pixel-block ratio that costs nothing (default {BLOCKY_FREE})")
    c.add_argument("--blocky-cost", type=float, default=BLOCKY_COST, help=f"score per unit of pixel-block ratio above that (default {BLOCKY_COST})")
    c.add_argument("--region-bonus", type=float, default=REGION_BONUS, help=f"(default {REGION_BONUS}) score added to paintings from map regions (their texture matches their neighbours')")
    c.add_argument("--lowfreq", type=float, default=LOWFREQ, help=f"blur (texels) above which shading follows the original (default {LOWFREQ}; 0: off)")
    c.add_argument("--deblock-from", type=float, default=DEBLOCK_FROM, help=f"pixel-block ratio from which the chosen painting's block edges are softened (default {DEBLOCK_FROM}; 0: off)")
    c.add_argument("--deblock-full", type=float, default=DEBLOCK_FULL, help=f"ratio at which they are softened fully (default {DEBLOCK_FULL})")
    c.add_argument("--exclude", help="tiles to leave out (they fall back to the original), e.g. 0:332,1:41")
    c.add_argument("--pick", help="hand-picked candidates, e.g. 0:68=region-l0-03#0 (sheet#cell as in cut-report.json)")
    c.add_argument("--cache", help="pickle of the registered candidates: written on the first run, read on later ones")
    c.add_argument("--lossless", action="store_true", help="lossless WebP (default quality 92)")
    c.add_argument("--band-lo", type=float, default=BAND_LO, help=f"texels a seam correction fades over (default {BAND_LO}; 0 and --band-hi 0: no seam pass)")
    c.add_argument("--band-hi", type=float, default=BAND_HI, help=f"texels at the edge set to the shared strip (default {BAND_HI})")
    c.add_argument("--lam", type=float, default=LAMBDA, help=f"how much a strip keeps its own painting (default {LAMBDA})")
    k = sub.add_parser("check", help="reassemble the map from the atlas, measure seams")
    k.add_argument("--out", default=str(ROOT / "public/art/terrain"), help="atlas root (default public/art/terrain)")
    k.add_argument("--rows", type=int, default=12, help="map rows per contact sheet")
    args = ap.parse_args(argv)
    {"inventory": cmd_inventory, "sheets": cmd_sheets, "fake": cmd_fake, "cut": cmd_cut, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    main()
