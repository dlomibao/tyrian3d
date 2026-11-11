"""HD terrain: Gemini-painted background tiles, cut, made seamless and packed as atlases (DECISIONS.md D58, D83).

The remastered look draws the ground (and TYRIAN's ice clouds) upscaled 4x with MMPX at runtime
(DECISIONS.md D34, D45, D48). This tool brings in HD paintings of a tileset's background tiles instead,
made by Google Gemini from input sheets of the original tiles, and packs them as the atlases the game
reads (public/art/terrain/<shapes>/manifest.json + <layer>.webp, the format in D57). A tileset is
shared by many levels (shapesz by 32), so every command takes a list of levels of one tileset:
--level 1-9,1-11,4-16, or --tileset shapesz for every level that uses it (D83).

    python tools/terrain_hd.py --tileset shapesz --work DIR inventory [--out public/art/terrain] [--kind 2:575=terrain]
        Every tile the levels' maps draw on layers 0, 1 and 2 as a tile (tiles a layer-1/2 structure
        model replaces are left out; ground tiles under ground models are still drawn, D34), merged
        over the levels: counts (and per level), usual neighbours over all the maps and one
        representative 3x3 neighbourhood, a material group, whether the atlas already has it
        (hasArt), and a kind: terrain (to paint), structure (layers 1-2: metal plating, pipes,
        machines: to model, not painted unless asked) or empty (one colour: nothing to paint).
        Writes DIR/inventory.json.

    python tools/terrain_hd.py --tileset shapesz --work DIR sheets [--structures] [--recut 0:46] [--blocks]
        Gemini input sheets in DIR/sheets/ for the tiles that still need a painting (no art yet,
        terrain, and no painting of the same tile on another layer to reuse): continuous map regions
        (7x6 tiles, a set cover over every level's map) for the ground and layer 2's terrain, and
        grids of 3x3-tile contexts (the tile with its usual neighbours, on black), one material group
        per sheet. Each sheet is padded to one of Gemini's aspect ratios and softened (one pixel per
        original pixel scaled up bicubic: Gemini copies hard pixel blocks, D59); <name>-blocks.png is
        the nearest-neighbour version. DIR/sheets/manifest.json says where every tile sits and the
        send order (most-used new tiles first); SEND.md and <name>.prompt.txt are for the operator.
        The sheets are rendered from the game data, so they stay out of git (D3).

        --soft 0.5 also writes sheets softened another way (MMPX + a half-pixel blur, D79's repaint
        of TYRIAN's ground) to DIR/sheets/soft/, with softFile and softPrompt in the manifest.

    python tools/terrain_hd.py --tileset shapesz --work DIR fake
        Stand-in "Gemini" answers for testing: each sheet upscaled with MMPX, blurred, shifted,
        rescaled slightly and colour-shifted, in DIR/results-fake/.

    python tools/terrain_hd.py --tileset shapesz --work DIR cut [--results DIR/results] [--out public/art/terrain]
        Cuts every answer (DIR/results/<sheet>.png|jpg|webp, any size, same aspect as the sheet; sheets
        without an answer are skipped) back into tiles at 8 texels per original pixel: each cell is
        registered to the sheet's own picture of it (rescale and shift by normalised cross-correlation),
        each tile in it refined by a small shift, resampled from the art and colour-matched to the
        original tile (mean and low-frequency contrast per channel). The best candidate per tile wins
        (or --combine mean): its fit, less its colour error, copied pixel blocks and made-up marks,
        with a bonus for map regions (D59); --exclude, --pick and --cache adjust and speed this up.
        The winner's broad shading (16 texels) is then replaced by the original's. A tile with no
        painting of its own takes the same tile's painting from another layer (--no-reuse: don't).
        Alpha (layers 1-2) is the original silhouette, MMPX-upscaled among the tile's usual neighbours
        with its contour smoothed at one original pixel (a blurred signed distance, D78), its edges
        solved like the colour's. Then the seams: every tile side's edge strip is solved jointly, least
        squares over every pair of tiles the levels' maps put side by side (weighted by how often) plus
        a weak pull towards the tile's own painting, and each tile's border is moved onto its strips
        (the difference fades in over 40 texels, the outer 4 texels are the strip); --edge-aware leaves
        strips untied where the original has a real edge between the tiles.
        `rimfix <tileset>` then takes the teal ring off blue-grey plating tiles (fix_rim, D113).
        The cut MERGES into the tileset's atlas (D83): every tile it already has is kept as it is (its
        image file untouched, its rect unchanged) and its strips are held, so the new tiles are solved
        against them; the new tiles are packed (16-aligned rects, 16 px edge-extended gutters) into new
        images (<layer>-2.webp, ...) that their rects name. --recut 0:46 cuts a kept tile again;
        --replace cuts everything into fresh atlases (one per layer, as D58-D60 did).
        --base ATLAS_ROOT lets an atlas's tiles compete with the new answers for the tiles being cut
        (a partial round of answers, D79). DIR/cut-report.json says where each tile came from (or that
        it was kept) and how well it fitted.

    python tools/terrain_hd.py --tileset shapesz --work DIR realpha [--out public/art/terrain]
        Redoes only the alpha of the committed atlas's layers 1-2 (as cut makes it, solved over all the
        levels' pairs), keeping its colour; needs DIR/inventory.json, not the answers (D78).

    python tools/terrain_hd.py --tileset shapesz --work DIR check [--out public/art/terrain] [--contact new|all|none|1-9,...]
        Measures seams over every tile edge the levels' maps have: the colour step between the two
        edge texels, against the step between neighbouring texels inside tiles (and the same for
        8-texel strips), in all, for the edges with a tile the last cut made ("new"), for the rest
        ("kept") and per level. Contact sheets (original, nearest, beside HD, 4 px per original pixel,
        12 rows at a time) of the row blocks that show a new tile. Writes DIR/check/ (seams.json lists
        the worst pairs).

The options before the command (--data, --level/--tileset, --work) apply to all of them; --work
defaults to reference/terrain-hd/ (git-ignored). With one level and an empty atlas folder the tool
does what it did for TYRIAN (D58-D60), byte for byte.

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


_SHAPES: dict[Path, list[np.ndarray | None]] = {}


def read_shapes(path: Path) -> list[np.ndarray | None]:
    """The 600 records of a shapes?.dat (None = blank), read once per file."""
    if path not in _SHAPES:
        sb = path.read_bytes()
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
        _SHAPES[path] = shapes
    return _SHAPES[path]


def level_shapes_letter(data_dir: Path, ep: int, num: int) -> str | None:
    """The shapes file letter of level `num` of tyrian<ep>.lvl, or None if there is no such level."""
    p = data_dir / f"tyrian{ep}.lvl"
    if not p.exists():
        return None
    b = p.read_bytes()
    lvl_num = min(struct.unpack_from("<H", b, 0)[0], 42)
    k = (num - 1) * 2
    if k >= lvl_num:
        return None
    pos = struct.unpack_from("<I", b, 2 + 4 * k)[0]
    if pos + 1 >= len(b):
        return None
    letter = chr(b[pos + 1]).lower()
    return letter if (data_dir / f"shapes{letter}.dat").exists() else None


def tileset_levels(data_dir: Path, tileset: str) -> list[str]:
    """Every level (episode-levelfile id, as --level takes) whose map uses `tileset` (shapesz or z).
    The level files' own slots, in episode order; for shapesz these are the 32 levels
    docs/roadmap/inventory.json lists."""
    want = tileset.lower().removeprefix("shapes").removesuffix(".dat")
    out = []
    for ep in range(1, 5):
        for num in range(1, 22):
            if level_shapes_letter(data_dir, ep, num) == want:
                out.append(f"{ep}-{num}")
    return out


def level_list(args) -> list[str]:
    """--tileset X: every level using X; otherwise --level, a comma-separated list."""
    if getattr(args, "tileset", None):
        ids = tileset_levels(Path(args.data), args.tileset)
        if not ids:
            raise SystemExit(f"no level uses tileset {args.tileset}")
        return ids
    return [s.strip() for s in args.level.split(",") if s.strip()]


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
        shapes = read_shapes(data_dir / self.shapes_file)
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


class TilesetData:
    """Several levels that share one shapes file: their maps (`levels[i].grids`), and the tiles and
    palette they have in common. It stands in for a LevelData wherever only tiles and colours are
    needed (sheets, cutting); maps are read per level."""

    def __init__(self, data_dir: Path, level_ids: list[str]):
        if not level_ids:
            raise SystemExit("no levels given")
        self.levels = [LevelData(data_dir, i) for i in level_ids]
        names = {L.shapes_name for L in self.levels}
        if len(names) != 1:
            raise SystemExit(f"levels {', '.join(level_ids)} use different tilesets ({', '.join(sorted(names))}); one tileset per run")
        first = self.levels[0]
        self.ids = [L.id for L in self.levels]
        self.id = ",".join(self.ids)
        self.shapes_name, self.shapes_file = first.shapes_name, first.shapes_file
        self.rgb, self.luma, self.luma_clear = first.rgb, first.luma, first.luma_clear
        self.shapes = read_shapes(data_dir / self.shapes_file)
        self.pixels: dict[int, np.ndarray] = {}
        for L in self.levels:
            for n, px in L.pixels.items():
                self.pixels.setdefault(n, px)

    def tile(self, n: int) -> np.ndarray:
        if n in self.pixels:
            return self.pixels[n]
        s = self.shapes[n]
        return s if s is not None else np.zeros((TILE_H, TILE_W), np.uint8)

    def level(self, level_id: str) -> LevelData:
        return self.levels[self.ids.index(level_id)]


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


def layer_masks(L: LevelData, layer: int, models: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(grid, drawn, under_kept) for one level's layer: drawn = cells drawn as tiles (no structure
    model replaces them); under_kept = cells a ground model stands on (still drawn). Cached."""
    key = (L.id, layer)
    cache = L.__dict__.setdefault("_masks", {})
    if key not in cache:
        g = L.grids[layer]
        rep, kept = replaced_mask(g, layer, models)
        cache[key] = (g, (g >= 0) & ~rep, kept, rep)
    g, drawn, kept, _ = cache[key]
    return g, drawn, kept


def existing_art(out_root: Path, shapes: str) -> dict[int, set[int]]:
    """The tiles that already have HD art in <out_root>/<shapes>/manifest.json, per layer."""
    p = Path(out_root) / shapes / "manifest.json"
    if not p.exists():
        return {}
    m = json.loads(p.read_text())
    return {int(k): {int(t) for t in v.get("tiles", {})} for k, v in m.get("layers", {}).items()}


def build_inventory(T, art: dict[int, set[int]] | None = None, kinds: dict[str, str] | None = None) -> dict:
    """The tiles drawn by every level of `T` (a TilesetData, or a single LevelData), merged per tile:
    counts summed, neighbours counted over all the maps, one representative 3x3 neighbourhood (the
    occurrence, in any level, whose neighbours are the most usual ones). `art`: the tiles that
    already have HD art (hasArt; the sheets leave them out)."""
    if isinstance(T, LevelData):
        levels = [T]
    else:
        levels = T.levels
    art = art or {}
    models = load_models(T.shapes_file)
    out = {"level": levels[0].id, "levels": [L.id for L in levels], "shapes": T.shapes_name, "palette": LEVEL_PALETTE,
           "tileWidth": TILE_W, "tileHeight": TILE_H,
           "note": "tile = 0-based record in the shapes file; counts are summed over the levels; neighbours count the cells drawn "
                   "as tiles (-1 none, -2 off the map); context = a representative 3x3 neighbourhood from one level's map (rows of "
                   "tile numbers, -1 none); hasArt = already in the tileset's atlas; levels = cells drawn per level",
           "layers": {}}
    for layer in range(3):
        per_level = []  # (L, g, drawn, kept, nbs, full)
        agg: dict[int, dict] = {}
        for L in levels:
            g, drawn, kept = layer_masks(L, layer, models)
            rep = (g >= 0) & ~drawn
            dg = np.where(drawn, g, -1)
            nbs = {k: shifted(dg, dx, dy) for k, (dx, dy) in SIDES.items()}
            full = {k: shifted(g, dx, dy) for k, (dx, dy) in SIDES.items()}
            per_level.append((L, g, drawn, nbs, full))
            for n in sorted(set(g[g >= 0].tolist())):
                at = g == n
                a = agg.setdefault(n, {"count": 0, "drawn": 0, "replaced": 0, "underModel": 0, "levels": {},
                                       "stats": {k: Counter() for k in SIDES}, "rigid": 0})
                mask = at & drawn
                cnt = int(mask.sum())
                a["count"] += int(at.sum())
                a["drawn"] += cnt
                a["replaced"] += int((at & rep).sum())
                a["underModel"] += int((at & kept).sum())
                if cnt:
                    a["levels"][L.id] = cnt
                    for k in SIDES:
                        a["stats"][k].update(nbs[k][mask].tolist())
        # Rigidity: how often a tile has exactly its usual neighbour on all four sides (a piece of a
        # fixed structure: ~1; terrain that meets many different neighbours: low).
        for n, a in agg.items():
            if not a["drawn"]:
                continue
            a["usual"] = {k: a["stats"][k].most_common(1)[0][0] for k in SIDES}
        tiles = {}
        for n in sorted(agg):
            a = agg[n]
            entry = {"tile": n, "count": a["count"], "drawn": a["drawn"], "replaced": a["replaced"], "underModel": a["underModel"]}
            if a["drawn"] == 0:
                entry["drawnAsTile"] = False
                tiles[str(n)] = entry
                continue
            entry["drawnAsTile"] = True
            stats, cnt = a["stats"], a["drawn"]
            entry["levels"] = a["levels"]
            entry["hasArt"] = n in art.get(layer, set())
            entry["neighbours"] = {k: [[t, c] for t, c in stats[k].most_common(6)] for k in EDGE_SIDES}
            entry["diagonals"] = {k: [[t, c] for t, c in stats[k].most_common(3)] for k in SIDES if k not in EDGE_SIDES}
            entry["usual"] = a["usual"]
            # Representative neighbourhood: the occurrence whose neighbours are the most usual ones.
            best = None
            rigid = 0
            freqs = {k: {t: c / cnt for t, c in stats[k].items()} for k in SIDES}
            for L, g, drawn, nbs, full in per_level:
                mask = (g == n) & drawn
                if not mask.any():
                    continue
                ys, xs = np.nonzero(mask)
                score = np.zeros(len(ys))
                same = np.ones(len(ys), bool)
                for k, (dx, dy) in SIDES.items():
                    wgt = 1.0 if k in EDGE_SIDES else 0.5
                    vals = full[k][ys, xs]
                    nv = nbs[k][ys, xs]
                    score += wgt * np.array([freqs[k].get(int(v), 0.0) for v in nv])
                    score -= 2.0 * (vals == -2)  # off the map
                    if k in EDGE_SIDES:
                        same &= nv == a["usual"][k]
                rigid += int(same.sum())
                i = int(np.argmax(score))
                if best is None or score[i] > best[0]:
                    y, x = int(ys[i]), int(xs[i])
                    ctx = [[int(g[y + dy, x + dx]) if 0 <= y + dy < g.shape[0] and 0 <= x + dx < g.shape[1] else -2
                            for dx in (-1, 0, 1)] for dy in (-1, 0, 1)]
                    best = (float(score[i]), {"level": L.id, "x": x, "y": y, "grid": ctx, "score": round(float(score[i]), 3)})
            entry["context"] = best[1]
            entry["group"] = material_group(T, layer, n, entry["underModel"] / max(entry["count"], 1))
            entry["blend"] = layer == 1  # background 2 draws blended (D45)
            entry["selfTiles"] = bool(stats["right"].get(n, 0) + stats["down"].get(n, 0))
            entry["rigidity"] = round(rigid / cnt, 3)
            entry["variety"] = {k: len(stats[k]) for k in EDGE_SIDES}
            tiles[str(n)] = entry
        drawn_t = [t for t in tiles.values() if t["drawnAsTile"]]
        out["layers"][str(layer)] = {
            "width": int(per_level[0][1].shape[1]), "height": int(per_level[0][1].shape[0]),
            "cellsDrawn": sum(int(d.sum()) for _, _, d, _, _ in per_level),
            "cellsReplaced": sum(int(((g >= 0) & ~d).sum()) for _, g, d, _, _ in per_level),
            "tilesDrawn": len(drawn_t),
            "tilesReplacedOnly": sum(1 for t in tiles.values() if not t["drawnAsTile"]),
            "tilesWithArt": sum(1 for t in drawn_t if t["hasArt"]),
            "tilesLeft": sum(1 for t in drawn_t if not t["hasArt"]),
            "cellsLeft": sum(t["drawn"] for t in drawn_t if not t["hasArt"]),
            "tiles": tiles,
        }
    classify_layers(T, out, art, kinds)
    return out


NATURAL = ("brown", "green", "yellow")  # rock, dirt, grass, forest: terrain whatever its shape
FILL_SELF = 0.9  # a fill tile meets itself (or nothing) on at least this share of its edges


def classify_layers(T, inv: dict, art: dict[int, set[int]] | None = None, overrides: dict[str, str] | None = None) -> None:
    """Background 2 and 3 tiles (layers 1-2): terrain to paint, or a piece of a structure to model.
    Level 1's layer-2 cells all sat under models (D58), but other levels draw rock, grass and metal
    there as plain tiles. A tile is "terrain" (HD art, drawn as a cutout or blended) if its main
    palette ramp is natural (brown, green: rock, dirt, grass, canopy), or if it is a fill (its usual
    neighbour on every side is itself and nearly all its edges meet itself or nothing: a backdrop);
    otherwise "structure" (metal plating, pipes, walls, machines: hard-surface models by pattern,
    D34/D47; the sheets leave them out unless asked). A tile that a ground model stands on elsewhere
    (keepTiles) is terrain too: it is painted beneath the model. Also noted per tile: structure models of the
    same tile on other layers (`modelsElsewhere`: add a layer entry to reuse the model) and HD art of
    the same tile on other layers (`artElsewhere`: the cutter can reuse that painting)."""
    art = art or {}
    overrides = overrides or {}
    models = load_models(T.shapes_file)
    by_tile: dict[int, list[str]] = defaultdict(list)
    for e in models:
        for row in e["tiles"]:
            for t in row:
                if t >= 0:
                    by_tile[t].append(f"{e['name']}@{e['layer']}" + ("+keep" if e.get("keepTiles", e["layer"] == 0) else ""))
    for layer_s, d in inv["layers"].items():
        layer = int(layer_s)
        for t in d["tiles"].values():
            if not t["drawnAsTile"]:
                continue
            n = t["tile"]
            other_models = sorted({m for m in by_tile.get(n, []) if not m.split("@")[1].startswith(layer_s)})
            other_art = sorted(L for L, s in art.items() if L != layer and n in s)
            if other_models:
                t["modelsElsewhere"] = other_models
            if other_art:
                t["artElsewhere"] = other_art
            px = T.tile(n)
            if len(np.unique(px if layer == 0 else px[px > 0])) <= 1:
                # One colour (Tyrian's black space): nothing to paint; it falls back to the 4x ground,
                # which looks the same.
                t["kind"], t["why"] = "empty", "one colour, nothing to paint"
                continue
            if layer == 0:
                t["kind"] = "terrain"
                continue
            colour = t["group"].split("-")[1]
            edges = sum(c for s in EDGE_SIDES for _, c in t["neighbours"][s])
            self_or_none = sum(c for s in EDGE_SIDES for m, c in t["neighbours"][s] if m in (n, -1, -2))
            fill = all(t["usual"][s] == n for s in EDGE_SIDES) and self_or_none >= FILL_SELF * max(edges, 1) \
                and not (T.tile(n) == 0).any()
            keep = [m for m in other_models if m.endswith("+keep")]
            if f"{layer}:{n}" in overrides:
                t["kind"], t["why"] = overrides[f"{layer}:{n}"], "set by hand (--kind)"
            elif t.get("hasArt"):
                t["kind"], t["why"] = "terrain", "already has HD art"
            elif colour in NATURAL:
                t["kind"], t["why"] = "terrain", f"natural material ({colour})"
            elif keep:
                t["kind"], t["why"] = "terrain", f"drawn under a ground model elsewhere ({keep[0]}): painted beneath it"
            elif fill:
                t["kind"], t["why"] = "terrain", "fill: meets itself on every side"
            else:
                t["kind"], t["why"] = "structure", f"hard surface ({colour}), part of a pattern"
        tl = [t for t in d["tiles"].values() if t["drawnAsTile"]]
        d["kinds"] = {k: {"tiles": sum(1 for t in tl if t.get("kind") == k),
                          "left": sum(1 for t in tl if t.get("kind") == k and not t["hasArt"]),
                          "cellsLeft": sum(t["drawn"] for t in tl if t.get("kind") == k and not t["hasArt"])}
                      for k in ("terrain", "structure", "empty")}


def cmd_inventory(args) -> None:
    T = TilesetData(Path(args.data), level_list(args))
    kinds = dict(s.strip().split("=", 1) for s in (args.kind or "").split(",") if s.strip())
    bad = [k for k, v in kinds.items() if v not in ("terrain", "structure", "empty")]
    if bad:
        raise SystemExit(f"--kind {','.join(bad)}: the kind is terrain, structure or empty")
    inv = build_inventory(T, existing_art(Path(args.out), T.shapes_name), kinds)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    (work / "inventory.json").write_text(json.dumps(inv, indent=1) + "\n")
    print(f"{T.shapes_name}: {len(T.levels)} level(s): {', '.join(T.ids)}")
    for layer, d in inv["layers"].items():
        groups = Counter(t["group"] for t in d["tiles"].values() if t["drawnAsTile"])
        print(f"layer {layer}: {d['tilesDrawn']} tiles drawn ({d['cellsDrawn']} cells), {d['tilesWithArt']} with art, "
              f"{d['tilesLeft']} left ({d['cellsLeft']} cells); {d['tilesReplacedOnly']} only under models "
              f"({d['cellsReplaced']} cells replaced); groups {dict(groups)}")
        k = d["kinds"]
        print(f"  terrain (HD art) {k['terrain']['left']} left of {k['terrain']['tiles']} ({k['terrain']['cellsLeft']} cells); "
              f"structure (models) {k['structure']['left']} left of {k['structure']['tiles']} ({k['structure']['cellsLeft']} cells); "
              f"empty (one colour, no art needed) {k['empty']['tiles']} ({k['empty']['cellsLeft']} cells)")
    print(f"-> {work / 'inventory.json'}")


# --- Gemini input sheets -------------------------------------------------------------------------

GAP = 6  # units (original pixels) of black between cells and around them
CTX_PER_SHEET = 9
REGION_TILES = (7, 6)  # a continuous region: 7 x 6 tiles = 168 x 168 px, square
TARGET_SIDE = 1024  # px, roughly what Gemini answers with

# What each material group is, for the prompts (Tyrian's palette ramps are one colour each, so the
# group's colours name the material; per tileset, what those colours show was checked on the maps).
# Things with height say "seen straight down" (D59: "top-down" alone got trees drawn from the side).
MATERIALS = {
    "brown": "rocky brown dirt, stones and earth ridges",
    "green": "dense green forest canopy, round tree crowns seen straight down, no trunks",
    "brown-green-edges": "brown dirt meeting the ragged edge of green grass and forest",
    "blue": "icy translucent clouds drifting over the ground",
    "cyan": "icy translucent clouds drifting over the ground",
    "grey": "grey rock and metal",
}
# Overrides per layer: the same colours are other materials on other layers and tilesets.
LAYER_MATERIALS = {
    0: {
        "grey": "grey cratered asteroid rock with scattered stones against black space, and grey metal bases where the "
                "original shows them",
        "red": "clusters of glossy red bubbles, round spheres with bright highlights, against black space",
        "grey-red-edges": "grey asteroid rock meeting clusters of glossy red bubbles",
        "brown-grey-edges": "grey asteroid rock with tan and brown stones, its ragged edge against black space",
        "cyan": "dark blue-grey metal deck plating with raised conduits, panels and rivets",
        "cyan-grey-edges": "dark blue-grey metal deck plating meeting grey machinery",
        "blue-cyan-edges": "dark blue-grey metal deck plating with blue lit panels",
    },
    1: {"blue": "icy translucent clouds drifting over the ground"},
    2: {
        "brown": "brown rock plateaus and rubble of a floating rock mass, seen straight down, the raised plateaus lighter",
        "green": "green grass and forest seen straight down: round tree crowns casting soft shadows, no trunks",
        "grey": "grey and purple metal plating, pipes and machinery seen straight down",
        "cyan": "purple and grey metal plating, pipes and machinery seen straight down",
    },
}


# Single tiles whose colours don't say what they are (checked on the maps).
TILE_MATERIALS = {
    ("shapesz", 1, 518): "a dark blue floor of square glowing panels in a regular grid, seen straight down",
}


def material_text(group: str, layer: int | None = None) -> str:
    key = group.split("-", 1)[1].removesuffix("-modelled")
    if layer is None:
        layer = int(group.split("-", 1)[0][1:]) if group[:1] == "l" and group[1:2].isdigit() else 0
    return LAYER_MATERIALS.get(layer, {}).get(key) or MATERIALS.get(key, f"{key.replace('-', ' ')} terrain")


def prompt_for(kind: str, what: str, layer: int, n: int, softened: bool = True, space: bool = False) -> str:
    """The Gemini prompt of a sheet. Softened sheets (D59/D60: much less pixel copying) say the picture
    is a soft enlargement; `space` says the black areas of a ground region are empty space."""
    keep = (f"Keep {'everything' if n == 1 or kind == 'region' else 'each piece'} exactly where it is, at the same size, with the "
            "same layout, shapes, outlines and colours, so it still lines up with the original pixel for pixel. ")
    keep += ("The picture is a soft, blurry enlargement of pixel art: paint crisp, detailed texture in its place, lit from above; "
             "don't keep the blur and don't make square pixel blocks or pixel-shaped details. " if softened else
             "Don't copy the pixel blocks or make pixel-shaped details: paint what they show, lit from above. ")
    keep += "The tiles repeat across the map, so keep the texture even up to the edges."
    if layer > 0 or kind == "context":
        bg = " The black background stays pure black: no glow, no shadow, no border."
    elif space:
        bg = " The black areas are empty space: keep them pure black."
    else:
        bg = ""
    src = "softened from pixel art" if softened else "enlarged from pixel art"
    if kind == "region":
        return (f"This is a top-down view of a stretch of terrain from the 1995 shooter Tyrian, {src}. Repaint "
                f"it as high-resolution, detailed, painterly top-down terrain ({what}), like StarCraft Remastered. " + keep + bg +
                " No text, no frame.")
    pieces = "one piece" if n == 1 else f"a grid of {n} pieces"
    return (f"This sheet is {pieces} of top-down terrain from the 1995 shooter Tyrian ({'a' if n == 1 else 'each a'} 3x3 block "
            f"of map tiles, {src}). Repaint {'it' if n == 1 else 'every piece'} as high-resolution, detailed, painterly top-down terrain "
            f"({what}), like StarCraft Remastered{'' if n == 1 else ', all in one consistent style'}. " + keep + bg +
            (" No text, no frame." if n == 1 else " No text, no lines between the pieces."))


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
             "prompt": prompt_for(kind, material_text(group, layer), layer, len(cells)), "cells": []}
    for i, cell in enumerate(cells):
        c, r = i % cols, i // cols
        x = (pl + GAP + c * (cw + GAP)) * scale
        y = (pt + GAP + r * (ch + GAP)) * scale
        sheet["cells"].append({"index": i, "col": c, "row": r, "x": x, "y": y, "w": cw * scale, "h": ch * scale, **cell})
    return sheet


def choose_regions(grids, wanted: set[int], size: tuple[int, int] = REGION_TILES) -> list[tuple]:
    """Windows of `size` tiles that together show every wanted tile away from the window's border (a
    border on the map's own edge is fine): greedy set cover over the windows of every map in `grids`
    ([(level id, grid)], or one grid). Returns (level, x0, y0, wanted tiles it adds)."""
    if isinstance(grids, np.ndarray):
        grids = [(None, grids)]
    rw, rh = size
    cands = []
    seen = set()
    for level, grid in grids:
        key = grid.tobytes() + bytes(str(grid.shape), "ascii")
        if key in seen:  # the same map in another level (TYRIAN is 1-9, 1-15 and 3-8)
            continue
        seen.add(key)
        h, w = grid.shape
        for y0 in range(0, h - rh + 1):
            for x0 in range(0, w - rw + 1):
                xa, xb = (x0 if x0 == 0 else x0 + 1), (x0 + rw if x0 + rw == w else x0 + rw - 1)
                ya, yb = (y0 if y0 == 0 else y0 + 1), (y0 + rh if y0 + rh == h else y0 + rh - 1)
                inner = set(grid[ya:yb, xa:xb].ravel().tolist()) & wanted
                if inner:
                    cands.append((level, x0, y0, inner))
    left, out = set(wanted), []
    while left and cands:
        level, x0, y0, inner = max(cands, key=lambda c: (len(c[3] & left), len(c[3])))
        if not inner & left:
            break
        out.append((level, x0, y0, inner & left))
        left -= inner
    return out


def needs_paint(t: dict, layer: int, structures: bool = False, reuse: bool = True, recut: set[str] = frozenset()) -> bool:
    """Whether a tile still needs a Gemini painting: drawn as a tile, no art yet (or asked for a
    re-cut), terrain (structures only when asked, D58 layer 2), and no painting of the same tile on
    another layer to reuse."""
    if not t.get("drawnAsTile"):
        return False
    key = f"{layer}:{t['tile']}"
    if key in recut:
        return t.get("kind") != "empty"
    if t.get("hasArt"):
        return False
    kind = t.get("kind", "terrain")
    if kind == "empty" or (kind == "structure" and not structures):
        return False
    return not (reuse and t.get("artElsewhere"))


def region_what(T, inv: dict, layer: int, grid: np.ndarray) -> tuple[str, bool]:
    """The material text of a region: its two biggest material groups by cells (and whether it shows
    black space: an empty tile)."""
    tiles = inv["layers"][str(layer)]["tiles"]
    c = Counter()
    space = False
    for v in grid.ravel().tolist():
        t = tiles.get(str(v))
        if not t or not t.get("drawnAsTile"):
            continue
        if t.get("kind") == "empty":
            space = True
            continue
        c[t["group"]] += 1
    texts = []
    total = sum(c.values())
    for g, k in c.most_common():
        if texts and k < 0.15 * total:  # a few cells of another material don't name the region
            break
        s = material_text(g, layer)
        if s not in texts:
            texts.append(s)
        if len(texts) == 2:
            break
    return "; ".join(texts) or "terrain", space


def build_sheets(T, inv: dict, structures: bool = False, reuse: bool = True, recut: set[str] = frozenset(),
                 softened: bool = True) -> list[dict]:
    """The Gemini sheets for the tiles that still need painting (needs_paint), over every level of
    `T`: map regions for the ground (and layer 2's terrain, a continuous mass on the levels that have
    it), 3x3 contexts for every layer (primary on layer 1, optional retries on 0 and 2)."""
    levels = T.levels if hasattr(T, "levels") else [T]
    models = load_models(T.shapes_file)
    sheets = []
    for layer_s, d in inv["layers"].items():
        layer = int(layer_s)
        tiles = [t for t in d["tiles"].values() if needs_paint(t, layer, structures, reuse, recut)]
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
        regions = layer in (0, 2)
        for group, ts in sorted(groups.items()):
            for k, chunk in enumerate(balanced_chunks(ts, CTX_PER_SHEET)):
                cells = [{"kind": "context", "level": t["context"].get("level"), "mapX": t["context"]["x"] - 1,
                          "mapY": t["context"]["y"] - 1,
                          "grid": [[v if v >= 0 else -1 for v in row] for row in t["context"]["grid"]],
                          "tiles": [{"tile": t["tile"], "col": 1, "row": 1, "interior": 1}]} for t in chunk]
                prio = "optional" if regions else "primary"
                sh = make_sheet(T, f"ctx-{group}-{k + 1}", "context", layer, group, cells, prio)
                special = [TILE_MATERIALS[(T.shapes_name, layer, t["tile"])] for t in chunk if (T.shapes_name, layer, t["tile"]) in TILE_MATERIALS]
                what = "; ".join(dict.fromkeys(special)) if len(special) == len(chunk) else material_text(group, layer)
                sh["prompt"] = prompt_for("context", what, layer, len(cells), softened)
                sheets.append(sh)
        if not regions:
            continue
        # Regions: continuous stretches of the maps, every wanted tile inside at least one. Cells a
        # structure model replaces show black (they aren't drawn as tiles).
        grids = []
        for L in levels:
            g, drawn, _ = layer_masks(L, layer, models)
            grids.append((L.id, np.where(drawn, g, -1)))
        by_level = dict(grids)
        wanted = {t["tile"] for t in tiles}
        rw, rh = REGION_TILES
        for k, (level, x0, y0, _) in enumerate(choose_regions(grids, wanted)):
            g = by_level[level]
            sub = g[y0:y0 + rh, x0:x0 + rw]
            cell_tiles = []
            for r in range(rh):
                for c in range(rw):
                    dx = min(c if x0 > 0 else 99, rw - 1 - c if x0 + rw < g.shape[1] else 99)
                    dy = min(r if y0 > 0 else 99, rh - 1 - r if y0 + rh < g.shape[0] else 99)
                    cell_tiles.append({"tile": int(sub[r, c]), "col": c, "row": r, "interior": int(min(dx, dy, 3))})
            cells = [{"kind": "region", "level": level, "mapX": x0, "mapY": y0, "grid": sub.tolist(), "tiles": cell_tiles}]
            sh = make_sheet(T, f"region-l{layer}-{k + 1:02d}", "region", layer, f"l{layer}-ground", cells, "primary")
            what, space = region_what(T, inv, layer, sub)
            sh["prompt"] = prompt_for("region", what, layer, 1, softened, space)
            sheets.append(sh)
    # What each sheet adds: the tiles that need painting it shows, and their cells over all the levels.
    for sh in sheets:
        layer = sh["layer"]
        tiles = inv["layers"][str(layer)]["tiles"]
        new = sorted({ct["tile"] for cell in sh["cells"] for ct in cell["tiles"]
                      if ct["tile"] >= 0 and needs_paint(tiles.get(str(ct["tile"]), {}), layer, structures, reuse, recut)})
        sh["newTiles"] = new
        sh["newCells"] = sum(tiles[str(n)]["drawn"] for n in new)
    return sheets


SOFT_PROMPT = (" The picture is deliberately soft and blurred: invent crisp natural detail (pebbles, cracks, grain, leaves, "
               "grass blades) at full resolution, with no pixel grid, checkerboard or dither pattern.")


def soft_sheet(L, sh: dict, units: np.ndarray, sigma: float) -> Image.Image:
    """The sheet as a softened picture (the D59 retry): MMPX-smoothed, then blurred by `sigma`
    original pixels, so the answer has no pixel blocks or checker dither to copy (Gemini copies what
    it is shown: region-l0-02's answer kept the 6x6 blocks, D59). The blur's period-2 attenuation at
    sigma 0.5 is ~0.3 along an axis and ~0.1 diagonally, where the dither is; shapes a few pixels
    across keep their outline. Black (nothing drawn) stays black: the blur is normalised by coverage."""
    from scipy import ndimage

    luma = L.luma_clear if sh["layer"] > 0 else L.luma
    f = 1 << math.ceil(math.log2(sh["scale"]))
    up = mmpx(np.clip(units, 0, 255).astype(np.uint8), luma, f)
    rgb = L.rgb[up].astype(np.float32)
    vis = ~np.kron(units < 0, np.ones((f, f), bool))
    rgb[~vis] = 0
    img = Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).resize((sh["width"], sh["height"]), Image.LANCZOS)
    m = np.asarray(Image.fromarray(vis.astype(np.uint8) * 255).resize((sh["width"], sh["height"]), Image.NEAREST)) > 127
    a = np.asarray(img).astype(np.float32)
    s = sigma * sh["scale"]
    num = ndimage.gaussian_filter(a * m[..., None], (s, s, 0))
    den = np.maximum(ndimage.gaussian_filter(m.astype(np.float32), s), 1e-3)[..., None]
    a = np.where(m[..., None], num / den, 0)
    return Image.fromarray(a.round().clip(0, 255).astype(np.uint8))


def soften(T, units: np.ndarray, width: int, height: int) -> Image.Image:
    """The sheet at one pixel per original pixel scaled up bicubic: the same geometry without the hard
    pixel blocks Gemini copies (doc section 3, D59)."""
    return Image.fromarray(units_rgb(T, units)).resize((width, height), Image.BICUBIC)


GEMINI_SESSION = 25  # requests before Gemini's "running low on usage" warning (Pro, doc section 3)
RETRY_RATE = 0.3  # TYRIAN: 27 requests for 21 sheets


def cmd_sheets(args) -> None:
    T = TilesetData(Path(args.data), level_list(args))
    work = Path(args.work)
    inv_path = work / "inventory.json"
    if inv_path.exists():
        inv = json.loads(inv_path.read_text())
        if inv.get("levels", [inv.get("level")]) != T.ids:
            raise SystemExit(f"{inv_path} is for levels {inv.get('levels', [inv.get('level')])}, not {T.ids}: run inventory again")
    else:
        inv = build_inventory(T, existing_art(Path(args.out), T.shapes_name))
    out = work / "sheets"
    out.mkdir(parents=True, exist_ok=True)
    recut = {s.strip() for s in (args.recut or "").split(",") if s.strip()}
    sheets = build_sheets(T, inv, structures=args.structures, reuse=not args.no_reuse, recut=recut, softened=not args.blocks)
    # Send order: primary sheets first, the most-used new tiles first; then the optional retries.
    sheets.sort(key=lambda s: (s["priority"] != "primary", -s["newCells"], s["name"]))
    for i, sh in enumerate(sheets):
        sh["send"] = i + 1
        units = sheet_units(T, sh)
        near = Image.fromarray(units_rgb(T, units)).resize((sh["width"], sh["height"]), Image.NEAREST)
        if args.blocks:
            near.save(out / sh["file"])
        else:
            soften(T, units, sh["width"], sh["height"]).save(out / sh["file"])
            sh["fileBlocks"] = f"{sh['name']}-blocks.png"
            near.save(out / sh["fileBlocks"])
        sh["softened"] = not args.blocks
        if args.soft > 0:  # D79's other softening (MMPX + a blur), for a retry
            (out / "soft").mkdir(exist_ok=True)
            soft_sheet(T, sh, units, args.soft).save(out / "soft" / sh["file"])
            sh["softFile"] = f"soft/{sh['file']}"
            sh["softPrompt"] = sh["prompt"] + SOFT_PROMPT
        (out / f"{sh['name']}.prompt.txt").write_text(sh["prompt"] + "\n")
    primary = [s for s in sheets if s["priority"] == "primary"]
    optional = [s for s in sheets if s["priority"] != "primary"]
    est = math.ceil(len(primary) * (1 + RETRY_RATE))
    requests = {"primary": len(primary), "optional": len(optional), "estimate": est,
                "sessions": math.ceil(est / GEMINI_SESSION),
                "note": f"one request per primary sheet; estimate adds {RETRY_RATE:.0%} retries (TYRIAN: 27 for 21); Gemini warns "
                        f"after about {GEMINI_SESSION} Pro requests, so plan that many per session. Optional sheets are retries for "
                        f"tiles a primary sheet painted badly."}
    manifest = {"level": T.ids[0], "levels": T.ids, "shapes": T.shapes_name, "tileWidth": TILE_W, "tileHeight": TILE_H,
                "note": "x, y, w, h and padding in sheet px; grid = the cell's tiles as rows of tile numbers (-1 none); "
                        "tiles = which tile sits where in the cell (col, row in tiles) and how far it is from the cell's "
                        "border (interior, in tiles; the cutter prefers inner ones); level = the map a cell comes from; "
                        "file = the picture to send (softened), fileBlocks = the same nearest-neighbour; send = order to "
                        "send in; newTiles/newCells = tiles still without art it shows, and their cells in all the levels",
                "requests": requests, "sheets": sheets}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    # A send list for the Gemini operator.
    lines = [f"# Gemini sheets: {T.shapes_name}, {len(T.ids)} level(s)", "",
             f"Requests: {len(primary)} primary sheets (estimate with retries: {est}, about {requests['sessions']} Gemini "
             f"session(s) of {GEMINI_SESSION}); {len(optional)} optional retry sheets.", "",
             "Send each `file` with its prompt (also in `<name>.prompt.txt`) at its aspect ratio; save the answer as "
             "`results/<name>.png` (docs/terrain-pipeline.html section 3). One request at a time, under the Gemini lock.", "",
             "| Send | Sheet | Priority | Layer | Kind | Aspect | Size | New tiles | New cells |", "|---|---|---|---|---|---|---|---|---|"]
    for sh in sheets:
        lines.append(f"| {sh['send']} | {sh['file']} | {sh['priority']} | {sh['layer']} | {sh['kind']} | {sh['aspect']} | "
                     f"{sh['width']}x{sh['height']} | {len(sh['newTiles'])} | {sh['newCells']} |")
    lines += ["", "## Prompts", ""]
    for sh in sheets:
        lines += [f"**{sh['send']}. {sh['name']}** ({sh['aspect']})", "", sh["prompt"], ""]
    (out / "SEND.md").write_text("\n".join(lines) + "\n")
    for sh in sheets:
        print(f"{sh['send']:3d} {sh['file']}: {sh['priority']}, {sh['kind']}, layer {sh['layer']}, {len(sh['cells'])} cells, "
              f"{sh['width']}x{sh['height']} ({sh['aspect']}), scale {sh['scale']}, new tiles {len(sh['newTiles'])} ({sh['newCells']} cells)")
    print(f"requests: {len(primary)} primary (estimate {est} with retries, {requests['sessions']} session(s)), {len(optional)} optional")
    print(f"-> {out / 'manifest.json'}, {out / 'SEND.md'}")


# --- Fake answers (testing) ----------------------------------------------------------------------


def cmd_fake(args) -> None:
    """Each sheet upscaled with MMPX, then blurred, shifted, rescaled a little, colour-shifted and
    given a little noise, at Gemini's usual size: what a faithful but imperfect answer looks like."""
    from scipy import ndimage

    L = TilesetData(Path(args.data), level_list(args))
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
ALPHA_SMOOTH = 8.0  # texels (one original pixel): the silhouette's contour is smoothed at this scale (alpha_level)
ALPHA_RAMP = 2.0  # texels each side of the contour over which alpha goes 0 -> 1
ALPHA_MIN_PAIRS = 5  # a pair of tiles the map has fewer times than this doesn't pull their alpha edges together


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


def alpha_level(L: LevelData, layer: int, tile: int, usual: dict, smooth: float = ALPHA_SMOOTH) -> np.ndarray:
    """The original tile's silhouette as a smooth level field (texels, > 0 inside, the contour at 0;
    layers 1-2), among its usual neighbours: the MMPX 8x upscale's mask, its signed distance (clamped
    to 3 `smooth`), blurred at `smooth` texels. Blurring the distance rounds the 8-texel stairs MMPX
    leaves on slopes other than 45 degrees while straight runs stay where they are (D78); alpha is
    a short ramp across the level's zero (alpha_from_level). Before D78 alpha was the MMPX mask
    blurred at 3 texels, which kept the stairs."""
    from scipy import ndimage

    u = context_units(L, layer, tile, usual)
    luma = L.luma_clear if layer > 0 else L.luma
    up = mmpx(np.clip(u, 0, 255).astype(np.uint8), luma, SCALE)
    vis = np.kron(u >= 0, np.ones((SCALE, SCALE), bool)) & (up != 0)
    if vis.all() or not vis.any():
        sdf = np.full(vis.shape, 3 * smooth if vis.all() else -3 * smooth, np.float32)
    else:
        sdf = np.where(vis, ndimage.distance_transform_edt(vis) - 0.5, 0.5 - ndimage.distance_transform_edt(~vis))
    lev = ndimage.gaussian_filter(np.clip(sdf, -3 * smooth, 3 * smooth).astype(np.float32), smooth)
    ys, xs = slice(TILE_H * SCALE, 2 * TILE_H * SCALE), slice(TILE_W * SCALE, 2 * TILE_W * SCALE)
    return lev[ys, xs]


def alpha_from_level(lev: np.ndarray, ramp: float = ALPHA_RAMP) -> np.ndarray:
    return smoothstep(-ramp, ramp, lev)


def solve_alpha(T, layer: int, inv_tiles: dict, tiles, models: list[dict], min_pairs: int = ALPHA_MIN_PAIRS,
                lam: float = LAMBDA, band_lo: float = BAND_LO, band_hi: float = BAND_HI, held=(),
                smooth: float = ALPHA_SMOOTH, ramp: float = ALPHA_RAMP) -> dict[int, np.ndarray]:
    """Alpha (0..1) for each tile in `tiles` on layer 1-2, seamless across the levels' pairs: each tile's
    level field (alpha_level) has its edge strips solved jointly like the colour (solve_strips) over
    the pairs the levels' maps have at least `min_pairs` times, and moved onto them (apply_strips). A
    tile's level near a side depends on the usual neighbour there, so two tiles that are not each
    other's usual neighbour drew a jog or a sliver where they met (43|44, 63|64). Solving the level, not
    alpha, moves the contour to a common crossing point without a half-transparent line; rare pairs are
    left out so a lone pairing of an empty edge with a full one doesn't drag cloud into the gap.
    `held`: tiles that keep their alpha (a merge's kept tiles, D83): their own level fields are held
    fixed, so the new tiles' edges are pulled onto them."""
    off = 128.0  # apply_strips clips to 0..255; the level is within +-3 smooth (so smooth <= 40)
    lev = {n: (alpha_level(T, layer, n, inv_tiles[str(n)]["usual"], smooth) + off)[..., None] for n in tiles}
    fixed = {n: (alpha_level(T, layer, n, inv_tiles[str(n)]["usual"], smooth) + off)[..., None]
             for n in held if n not in lev and str(n) in inv_tiles}
    if band_lo > 0 or band_hi > 0:
        pairs = Counter({k: c for k, c in all_pairs(T.levels, layer, models, set(lev) | set(fixed)).items() if c >= min_pairs})
        strips = solve_strips(lev, pairs, lam, fixed=fixed or None)
        lev = {n: apply_strips(v, {side: strips[(n, side)] for side in OPPOSITE}, band_lo, band_hi) for n, v in lev.items()}
    return {n: alpha_from_level(v[..., 0] - off, ramp) for n, v in lev.items()}


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


EDGE_FREE = 64.0  # colour step (largest channel, 0-255) between the original's facing edge pixels that still ties two strips
EDGE_FULL = 128.0  # ...and from which they aren't tied at all: the original has a real edge there (rock against space)


def edge_continuity(T, o: str, a: int, b: int, layer: int = 0, free: float = EDGE_FREE, full: float = EDGE_FULL) -> np.ndarray:
    """Per original pixel along the edge between tile a and tile b (o "h": a left of b, "v": a above
    b), how continuous the original is across it: 1 where the facing pixels are alike, 0 where the
    art has a real edge there (rock meeting black space, a cloud's rim against nothing). Smoothed
    over a pixel either way along the edge."""
    from scipy.ndimage import gaussian_filter1d

    A, B = T.tile(a), T.tile(b)
    pa, pb = (A[:, -1], B[:, 0]) if o == "h" else (A[-1], B[0])
    ca, cb = T.rgb[pa].astype(np.float32), T.rgb[pb].astype(np.float32)
    if layer > 0:  # index 0 is transparent: nothing against nothing is continuous, nothing against art isn't
        ca[pa == 0], cb[pb == 0] = 0, 0
    d = gaussian_filter1d(np.abs(ca - cb).max(1), 1.0, mode="nearest")  # max: a saturated red against black counts in full
    return 1.0 - smoothstep(free, full, d)


def solve_strips(tiles: dict[int, np.ndarray], pairs: Counter, lam: float = LAMBDA,
                 fixed: dict[int, np.ndarray] | None = None, continuity=None) -> dict[tuple[int, str], np.ndarray]:
    """The edge every tile side is pulled to, chosen for all sides at once: least squares over
    every pair of tiles the map puts side by side (weighted by how often) that the two facing strips
    be equal, plus a weaker pull of each strip towards the tile's own painting. Facing strips of
    the most frequent pairs come out (nearly) identical; a tile with many different neighbours on
    a side gets the strip that is closest to all of them, weighted by frequency. Solved per
    orientation and per texel along the edge (one small SPD system, many right-hand sides).
    `fixed`: tiles whose strips are held at their own edges (the kept tiles of a merge): the free
    strips are solved against them, and they come out unchanged.
    `continuity(o, a, b)`: per original pixel along the edge, how much the pair ties there
    (edge_continuity); where the original has a real edge (rock against black space, D83), the
    strips aren't averaged across it, so the black doesn't turn grey. One system per original pixel
    along the edge then; where every weight is 1 it is the single system above."""
    fixed = fixed or {}
    out = {}
    for o, (sa, sb) in {"h": ("right", "left"), "v": ("down", "up")}.items():
        nodes = sorted({(n, side) for n in tiles for side in (sa, sb)})
        nodes += sorted({(n, side) for n in fixed if n not in tiles for side in (sa, sb)})
        idx = {nd: i for i, nd in enumerate(nodes)}
        N = len(nodes)
        own = np.stack([edge_strip((tiles[n] if n in tiles else fixed[n]), side) for n, side in nodes])  # (N, L, C)
        Lt = own.shape[1]
        edges = []  # (i, j, count, per-pixel weights or None)
        for (po, a, b), c in pairs.items():
            if po != o or (a, sa) not in idx or (b, sb) not in idx:
                continue
            i, j = idx[(a, sa)], idx[(b, sb)]
            if i == j:
                continue
            w = continuity(o, a, b) if continuity else None
            edges.append((i, j, c, None if w is None or w.min() >= 1.0 else w))
        held = np.array([n not in tiles for n, _ in nodes])
        F = ~held
        n_px = Lt // SCALE if Lt % SCALE == 0 else Lt
        groups = [None] if all(w is None for *_, w in edges) else list(range(n_px))
        sol = own.astype(np.float64)  # (a float64 solve, as the single system always gave)
        for gi in groups:
            M = np.zeros((N, N))
            deg = np.zeros(N)
            for i, j, c, w in edges:
                cw = c if (w is None or gi is None) else c * float(w[gi])
                M[i, i] += cw
                M[j, j] += cw
                M[i, j] -= cw
                M[j, i] -= cw
                deg[i] += c
                deg[j] += c
            lam_i = lam * np.maximum(deg, 1)
            M[np.arange(N), np.arange(N)] += lam_i
            sl = slice(None) if gi is None else slice(gi * (Lt // n_px), (gi + 1) * (Lt // n_px))
            part = own[:, sl]
            rhs = (lam_i[:, None, None] * part).reshape(N, -1)
            if held.any():
                # Held strips are known: move their terms to the right-hand side and solve for the rest.
                x = part.reshape(N, -1).copy()
                x[F] = np.linalg.solve(M[np.ix_(F, F)], rhs[F] - M[np.ix_(F, held)] @ x[held])
                sol[:, sl] = x.reshape(part.shape)
            else:
                sol[:, sl] = np.linalg.solve(M, rhs).reshape(part.shape)
        if groups != [None]:
            # Systems per pixel step along the edge: smooth the free strips' joins (held ones stay).
            from scipy.ndimage import gaussian_filter1d

            sol[F] = gaussian_filter1d(sol[F], STRIP_SIGMA, axis=1, mode="nearest")
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


BASE_COST = 0.12  # a base tile (--base) against new answers: its pixel copying is only partly measured (D79)
DITHER_FREE = 1.15  # pixel-period ratio a painting may have before it costs score (a painting is ~1.0-1.1)
DITHER_COST = 0.6  # score per unit above DITHER_FREE


def _alternation(g: np.ndarray, s: int) -> float:
    """Strongest 1-cell alternation of `g` averaged over s x s cells (any phase): the diagonal
    checker [1 -1; -1 1] plus half of each axis' [1 -2 1], mean absolute response."""
    best = 0.0
    for py in range(s):
        for px in range(s):
            h, w = (g.shape[0] - py) // s, (g.shape[1] - px) // s
            m = g[py:py + h * s, px:px + w * s].reshape(h, s, w, s).mean((1, 3))
            dg = np.abs(m[:-1, :-1] + m[1:, 1:] - m[1:, :-1] - m[:-1, 1:]).mean() / 4
            dx = np.abs(m[:, :-2] - 2 * m[:, 1:-1] + m[:, 2:]).mean() / 4
            dy = np.abs(m[:-2] - 2 * m[1:-1] + m[2:]).mean() / 4
            best = max(best, float(dg + 0.5 * dx + 0.5 * dy))
    return best


def pixel_period(hd: np.ndarray) -> float:
    """How much of the original's pixel grid a painting kept, blocks and checker dither alike: the
    alternation from one original pixel to the next (8-texel cells), against the same measure over 6-
    and 11-texel cells, which no pixel grid lines up with. A painting's detail has no preferred
    scale, so it is ~1.0-1.1; a copy of the blocks or the dither is 1.3-1.8 (TYRIAN's light dirt 46
    1.72, grass fringe 89 1.61, canopy 211 1.52 in D59's cut). `blockiness` sees only block edges,
    which D60's deblock softens; this sees the alternation inside them too."""
    g = gray(hd[..., :3].astype(np.float32))
    return float(_alternation(g, SCALE) / max(math.sqrt(_alternation(g, 6) * _alternation(g, 11)), 1e-3))


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


def tile_ncc(hd: np.ndarray, orig_rgb: np.ndarray, mask1: np.ndarray) -> float:
    """NCC of the painting averaged back to one value per original pixel against the original
    (grey): how well it still reads as the tile, on the same footing for every candidate."""
    a = gray(hd[..., :3].astype(np.float32).reshape(TILE_H, SCALE, TILE_W, SCALE, 3).mean((1, 3)))[mask1]
    b = gray(orig_rgb.astype(np.float32))[mask1]
    a, b = a - a.mean(), b - b.mean()
    return float((a * b).sum() / max(math.sqrt((a * a).sum() * (b * b).sum()), 1e-6))


def base_candidates(L: LevelData, base_root: Path, inv: dict) -> dict[tuple[int, int], list[dict]]:
    """The tiles of an existing atlas as candidates (sheet "base"), so a new round of answers for
    some sheets competes with what is already cut instead of needing every answer again."""
    out: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for layer, tiles in load_atlas(base_root, L.shapes_name).items():
        for n, img in tiles.items():
            px = L.tile(n)
            mask1 = px != 0 if layer > 0 else np.ones_like(px, bool)
            hd = img[..., :3].astype(np.float32)
            hd1 = hd.reshape(TILE_H, SCALE, TILE_W, SCALE, 3).mean((1, 3))
            err = float(np.abs(hd1 - L.rgb[px])[mask1].mean() / 255) if mask1.any() else 0.0
            out[(layer, n)].append({"hd": hd, "ncc": 1.0, "ncc1": tile_ncc(hd, L.rgb[px], mask1), "cellScore": 1.0, "err": err,
                                    "interior": 3, "sheet": "base", "cell": 0, "blocky": blockiness(hd), "dither": pixel_period(hd),
                                    "novel": novel_detail(hd, L.rgb[px], mask1), "score": 0.0, "fit": {}})
    return out


def load_result(results: Path, name: str) -> np.ndarray | None:
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = results / f"{name}.{ext}"
        if p.exists():
            return np.asarray(Image.open(p).convert("RGB")).astype(np.float32)
    return None


def candidates(L: LevelData, manifest: dict, results: Path, only: set[str] | None = None) -> dict[tuple[int, int], list[dict]]:
    """Every painting of every tile found in the answers, registered and colour-matched."""
    out: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for sh in manifest["sheets"]:
        if only is not None and sh["name"] not in only:
            continue
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
                dith = pixel_period(hd)
                ncc1 = tile_ncc(hd, L.rgb[px], mask1)
                out[(layer, n)].append({"hd": hd, "ncc": score, "cellScore": fit["score"], "err": err,
                                        "interior": t["interior"], "sheet": sh["name"], "cell": cell["index"],
                                        "blocky": blk, "dither": dith, "ncc1": ncc1, "novel": novel_detail(hd, L.rgb[px], mask1),
                                        "score": score - err + 0.05 * min(t["interior"], 2),
                                        "fit": {k: round(v, 3) for k, v in fit.items()}})
        print(f"  {sh['name']}: {len(sh['cells'])} cells, answer {W}x{H} ({sh['scale'] * fx:.2f} px per original px)")
    return out


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
    """The painting with alpha (layers 1-2: the original silhouette, unsolved, alpha_level; colour
    bled under it). cmd_cut replaces the alpha with solve_alpha's once all the layer's tiles are in."""
    if layer == 0:
        return hd.astype(np.float32)
    alpha = alpha_from_level(alpha_level(L, layer, n, inv_tile["usual"]))
    return np.concatenate([bleed(hd, alpha), alpha[..., None] * 255], -1).astype(np.float32)


def pack_atlas(tiles: dict[int, np.ndarray], channels: int) -> tuple[np.ndarray, dict]:
    """Tiles on a grid of 16-aligned rects with 16 px edge-extended gutters (D57's format rules)."""
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


ATLAS_MAX = 4096  # D57: atlases at most 4096 square
TILES_PER_ATLAS = 19 * ((ATLAS_MAX - 16) // (TILE_H * SCALE + 16))  # 19 columns (3968 px) x 17 rows = 323


def save_atlas(img: Image.Image, path: Path, lossless: bool) -> None:
    if lossless:
        img.save(path, lossless=True, method=6)
    else:
        img.save(path, quality=92, method=6, alpha_quality=100)


def load_tileset_art(out_dir: Path) -> tuple[dict | None, dict[int, dict[int, np.ndarray]]]:
    """An existing atlas folder: its manifest, and every tile's texels per layer (float RGBA; a rect
    may name its own image, D57)."""
    p = out_dir / "manifest.json"
    if not p.exists():
        return None, {}
    m = json.loads(p.read_text())
    imgs: dict[str, np.ndarray] = {}

    def img(name: str) -> np.ndarray:
        if name not in imgs:
            imgs[name] = np.asarray(Image.open(out_dir / name).convert("RGBA")).astype(np.float32)
        return imgs[name]

    tiles: dict[int, dict[int, np.ndarray]] = {}
    for layer_s, lay in m.get("layers", {}).items():
        out = tiles.setdefault(int(layer_s), {})
        for k, r in lay.get("tiles", {}).items():
            a = img(r.get("image", lay["image"]))
            out[int(k)] = a[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]].copy()
    return m, tiles


def all_pairs(levels: list, layer: int, models: list[dict], have) -> Counter:
    """map_pairs over every level's map of this layer (cells drawn as tiles), summed."""
    pairs = Counter()
    for L in levels:
        g, drawn, _ = layer_masks(L, layer, models)
        pairs.update(map_pairs(g, drawn, have))
    return pairs


def set_alpha(T, layer: int, inv_tiles: dict, done: dict[int, np.ndarray], models: list[dict], args,
              held=()) -> None:
    """Layers 1-2: each tile's alpha from solve_alpha (over all the levels' pairs; the `held` tiles,
    a merge's kept ones, pull the new tiles' edges and stay as they are), colour bled under it afresh."""
    alphas = solve_alpha(T, layer, inv_tiles, done, models, args.alpha_min_pairs, args.lam, args.band_lo, args.band_hi, held,
                         getattr(args, "alpha_smooth", ALPHA_SMOOTH), getattr(args, "alpha_ramp", ALPHA_RAMP))
    inset = getattr(args, "rim_inset", 0)
    for n, img in done.items():
        if inset:
            img[..., :3] = bleed(img[..., :3], inside_alpha(img[..., 3] / 255, inset))
        img[..., :3] = bleed(img[..., :3], alphas[n])
        img[..., 3] = alphas[n] * 255


def inside_alpha(alpha: np.ndarray, inset: int) -> np.ndarray:
    """`alpha` eroded by `inset` texels (a tile's edges count as inside: the cloud goes on in the next tile):
    the part of the painting whose colour is kept when a wider soft edge is bled out of it (rim_inset), so
    the original's dark outline colour under the old edge doesn't show through the new one."""
    from scipy import ndimage

    core = ndimage.binary_erosion(alpha > 0.98, iterations=inset, border_value=1)
    return core.astype(np.float32)


def cmd_realpha(args) -> None:
    """Redo the alpha of an atlas's layers 1-2 in place (set_alpha) without the Gemini answers: the
    colour is the atlas's own, bled from what was visible before; layer 0 and the manifest's other
    fields are untouched. Every image of the layer is re-encoded at the same layout (quality 92
    unless --lossless). Tiles the inventory doesn't list (no level given draws them) keep their alpha
    and hold their edges."""
    T = TilesetData(Path(args.data), level_list(args))
    inv = json.loads((Path(args.work) / "inventory.json").read_text())
    if inv.get("levels", [inv.get("level")]) != T.ids:
        raise SystemExit(f"inventory.json is for levels {inv.get('levels', [inv.get('level')])}, not {T.ids}: run inventory again")
    out_dir = Path(args.out) / T.shapes_name
    man, atlas = load_tileset_art(out_dir)
    if man is None:
        raise SystemExit(f"no atlas in {out_dir}")
    models = load_models(T.shapes_file)
    only = {int(x) for x in args.layers.split(",")} if args.layers else None
    for layer, tiles in sorted(atlas.items()):
        if layer == 0 or (only and layer not in only):
            continue
        inv_tiles = inv["layers"][str(layer)]["tiles"]
        done = {n: np.concatenate([bleed(t[..., :3], t[..., 3] / 255), t[..., 3:]], -1) for n, t in tiles.items() if str(n) in inv_tiles}
        set_alpha(T, layer, inv_tiles, done, models, args, held=[n for n in tiles if n not in done])
        lay = man["layers"][str(layer)]
        by_image: dict[str, list[int]] = defaultdict(list)
        for k, r in lay["tiles"].items():
            by_image[r.get("image", lay["image"])].append(int(k))
        for name, ns in sorted(by_image.items()):
            if not any(n in done for n in ns):
                continue
            img_tiles = {n: done.get(n, tiles[n]) for n in ns}
            packed, rects = pack_atlas(img_tiles, 4)
            want = {str(n): {k: v for k, v in lay["tiles"][str(n)].items() if k != "image"} for n in ns}
            assert rects == want, f"atlas layout changed ({name})"
            img = Image.fromarray(packed.round().clip(0, 255).astype(np.uint8), "RGBA")
            if name == lay["image"]:
                assert (img.width, img.height) == (lay["width"], lay["height"]), f"atlas size changed ({name})"
            save_atlas(img, out_dir / name, args.lossless)
            print(f"layer {layer}: alpha redone for {sum(n in done for n in ns)} tiles -> {out_dir / name}")


RIM_FULL = 12  # texels at a tile's edge the rim correction applies to in full...
RIM_FADE = 12  # ...and the texels it then fades out over
RIM_RHO = 0.58  # where a blue-grey hull's green sits between its red and its blue (measured on the plating)


def fix_rim(tile: np.ndarray, full: int = RIM_FULL, fade: int = RIM_FADE, rho: float = RIM_RHO) -> tuple[np.ndarray, float]:
    """A teal rim off a blue-grey tile (D113). The cut's seam strips take the colours of the original's
    edge pixels, a lighter cyan, so a tile of blue-grey plating comes out with a teal ring round it
    (the rim is a stripe of the tile's own edge texels, where the plating's green sits at 0.8 of the
    way from red to blue against 0.58 inside). Within `full` texels of the edge, fading over `fade`
    more, the green is lowered to the plating's own ratio where it is above it; red and blue stay, so
    the rim keeps its brightness. The same colour function everywhere, so two tiles whose edge
    colours were one still meet in one. Returns (tile, the largest green change); a tile whose
    interior isn't blue-leaning (jungle, rock, water) comes back as it was."""
    h, w = tile.shape[:2]
    inner = tile[24:h - 24, 24:w - 24, :3].reshape(-1, 3).mean(0)
    if not inner[2] > inner[1] + 3 > inner[0] + 3:  # blue over green over red: plating
        return tile, 0.0
    yy, xx = np.mgrid[:h, :w]
    depth = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)).astype(np.float32)
    weight = np.clip(1 - (depth - full) / fade, 0, 1)
    r, g, b = tile[..., 0], tile[..., 1], tile[..., 2]
    target = r + rho * (b - r)
    drop = weight * np.where(b > r, np.maximum(g - target, 0), 0)
    out = tile.copy()
    out[..., 1] = g - drop
    return out, float(drop.max())


def cmd_rimfix(args) -> None:
    """Take the teal rim (fix_rim) off the blue-grey ground tiles of an atlas, in place: layer 0's
    images are re-encoded at the same layout (quality 92 unless --lossless); the manifest is
    untouched. --dry-run lists the tiles it would change."""
    out_dir = Path(args.out) / args.tileset
    man, atlas = load_tileset_art(out_dir)
    if man is None:
        raise SystemExit(f"no atlas in {out_dir}")
    tiles = atlas.get(0, {})
    lay = man["layers"]["0"]
    done = {}
    for n, t in sorted(tiles.items()):
        fixed, change = fix_rim(t)
        if change > 0.5:
            done[n] = fixed
    print(f"layer 0: {len(done)} of {len(tiles)} tiles have a teal rim: {' '.join(map(str, done))}")
    if args.dry_run or not done:
        return
    by_image: dict[str, list[int]] = defaultdict(list)
    for k, r in lay["tiles"].items():
        by_image[r.get("image", lay["image"])].append(int(k))
    for name, ns in sorted(by_image.items()):
        if not any(n in done for n in ns):
            continue
        packed, rects = pack_atlas({n: done.get(n, tiles[n]) for n in ns}, 4)
        want = {str(n): {k: v for k, v in lay["tiles"][str(n)].items() if k != "image"} for n in ns}
        assert rects == want, f"atlas layout changed ({name})"
        img = Image.fromarray(packed.round().clip(0, 255).astype(np.uint8), "RGBA")
        if name == lay["image"]:
            assert (img.width, img.height) == (lay["width"], lay["height"]), f"atlas size changed ({name})"
        save_atlas(img, out_dir / name, args.lossless)
        print(f"layer 0: rim fixed for {sum(n in done for n in ns)} tiles -> {out_dir / name}")


def cmd_cut(args) -> None:
    T = TilesetData(Path(args.data), level_list(args))
    work = Path(args.work)
    inv = json.loads((work / "inventory.json").read_text())
    if inv.get("levels", [inv.get("level")]) != T.ids:
        raise SystemExit(f"inventory.json is for levels {inv.get('levels', [inv.get('level')])}, not {T.ids}: run inventory again")
    manifest = json.loads((work / "sheets/manifest.json").read_text())
    results = Path(args.results) if args.results else work / "results"
    print(f"cutting answers in {results}")
    cache = Path(args.cache) if args.cache else None
    if cache:
        # Per answer: {sheet: (answer mtime, {key: [candidates]})}; answers added or changed since
        # are registered and added, the rest come from the cache.
        import pickle

        store = pickle.loads(cache.read_bytes()) if cache.exists() else {}
        if not isinstance(store, dict):
            store = {}
    if cache and store and not all(isinstance(k, str) for k in store):
        # A whole-run cache ({(layer, tile): [candidates]}, the format before the per-answer one;
        # tests/tools/terrain_hd_test.py writes one): read as it is (delete it after changing the answers).
        cands = defaultdict(list, store)
        print(f"  candidates from {cache} (a whole-run cache)")
    elif cache:
        import pickle

        stamps = {}
        for sh in manifest["sheets"]:
            p = next((results / f"{sh['name']}.{e}" for e in ("png", "jpg", "jpeg", "webp") if (results / f"{sh['name']}.{e}").exists()), None)
            if p is not None:
                stamps[sh["name"]] = p.stat().st_mtime
        todo = {n for n, t in stamps.items() if store.get(n, (None,))[0] != t}
        fresh = candidates(T, manifest, results, todo) if todo else {}
        for n in todo:
            store[n] = (stamps[n], {k: [c for c in v if c["sheet"] == n] for k, v in fresh.items() if any(c["sheet"] == n for c in v)})
        store = {n: v for n, v in store.items() if n in stamps}
        cache.write_bytes(pickle.dumps(store))
        cands = defaultdict(list)
        for n, (_, by_key) in sorted(store.items()):
            for k, v in by_key.items():
                cands[k].extend(v)
        print(f"  candidates: {len(store) - len(todo)} answers from {cache}, {len(todo)} registered now")
    else:
        cands = candidates(T, manifest, results)
    if args.base:
        # A partial round (D79): every candidate is scored on the same footing (the NCC of its
        # per-pixel means against the original, as the base tiles have no registration score),
        # and the base atlas's tiles compete as candidates for the tiles this run cuts.
        base = base_candidates(T, Path(args.base), inv)
        for key, cs in cands.items():
            for c in cs:
                c.setdefault("ncc1", c["ncc"])
                c.setdefault("dither", pixel_period(c["hd"]))
                c["score"] = c["ncc1"] - c["err"] + 0.05 * min(c["interior"], 2)
        for key, cs in base.items():
            for c in cs:
                c["score"] = c["ncc1"] - c["err"] + 0.05 * 2 - args.base_cost
            cands[key] = list(cands.get(key, [])) + cs
        print(f"  base: {sum(len(v) for v in base.values())} tiles from {args.base}")
    exclude = {s.strip() for s in (args.exclude or "").split(",") if s.strip()}
    picks = dict(s.strip().split("=", 1) for s in (args.pick or "").split(",") if s.strip())
    recut = {s.strip() for s in (args.recut or "").split(",") if s.strip()}
    out_dir = Path(args.out) / T.shapes_name
    out_dir.mkdir(parents=True, exist_ok=True)
    models = load_models(T.shapes_file)
    # Merge (the default): the tiles already in the tileset's atlas are kept as they are, their
    # images untouched, their rects unchanged; new tiles are seam-solved against them and packed
    # into images of their own. --replace cuts every tile again into fresh atlases (D58-D60).
    old_manifest, old_tiles = (None, {}) if args.replace else load_tileset_art(out_dir)
    atlas_manifest = old_manifest or {"version": 1, "scale": SCALE, "tileWidth": TILE_W, "tileHeight": TILE_H,
                                      "credit": "Painted with Google Gemini from Tyrian's background tiles (Daniel Cook's art), cut and "
                                                "made seamless by tools/terrain_hd.py; see CREDITS.md",
                                      "layers": {}}
    atlas_manifest.setdefault("layers", {})
    report = {}
    final: dict[tuple[int, int], np.ndarray] = {}  # every tile's texels after this run (kept and new), for reuse
    for layer, tl in old_tiles.items():
        for n, img in tl.items():
            final[(layer, n)] = img if layer > 0 else img[..., :3]
    written = []
    for layer_s, d in sorted(inv["layers"].items(), key=lambda kv: int(kv[0])):
        layer = int(layer_s)
        old_layer = old_tiles.get(layer, {})
        locked = {n: img for n, img in old_layer.items() if f"{layer}:{n}" not in recut}
        done = {}
        for key, t in d["tiles"].items():
            n = int(key)
            k = f"{layer}:{n}"
            if not t["drawnAsTile"]:
                continue
            if n in locked:
                report[k] = {"kept": True}
                continue
            kind = t.get("kind", "terrain")
            if kind == "empty" or (kind == "structure" and not args.structures and k not in recut):
                continue
            if k in exclude:
                report[k] = {"excluded": True}
                continue
            cs = cands.get((layer, n), [])
            if not cs:
                # No painting of its own: the same tile's painting on another layer (D58's per-layer
                # atlases; layer 2's rock and forest are layer 0's tiles on several levels).
                src = next(((L, m) for L in t.get("artElsewhere", []) for m in [final.get((L, n))] if m is not None), None) \
                    if not args.no_reuse else None
                if src is None:
                    continue
                L_, img = src
                done[n] = prepare_tile(T, t, layer, n, img[..., :3].astype(np.float32))
                report[k] = {"from": [f"layer{L_}:{n}"], "reused": True}
                continue
            # Made-up marks cost against the tile's other paintings (a canopy has more detail
            # than dirt, so the measure is relative to the tile's median candidate).
            # (Not against a base tile: a copy of the pixels has no marks of its own, so it would
            # make every new painting's detail look made up.)
            med = float(np.median([c["novel"] for c in cs if c["sheet"] != "base"] or [0.0]))
            for c in cs:
                c["score"] -= (NOVEL_COST * max(0.0, c["novel"] - med - NOVEL_FREE) if c["sheet"] != "base" else 0.0) + args.blocky_cost * max(0.0, c["blocky"] - args.blocky_free)
                c["score"] -= args.dither_cost * max(0.0, c.get("dither", 1.0) - args.dither_free)
                c["score"] += args.region_bonus if c["sheet"].startswith("region-") or c["sheet"] == "base" else 0.0
            cs = sorted(cs, key=lambda c: -c["score"])
            if k in picks:  # a hand pick after looking at the contact sheets
                want = picks[k]
                cs = [c for c in cs if f"{c['sheet']}#{c['cell']}" == want] + [c for c in cs if f"{c['sheet']}#{c['cell']}" != want]
                assert f"{cs[0]['sheet']}#{cs[0]['cell']}" == want, f"--pick {k}={want}: no such candidate"
            good = [c for c in cs if c["score"] >= cs[0]["score"] - 0.05] if args.combine == "mean" else cs[:1]
            hd = np.mean([c["hd"] for c in good], 0)
            if all(c["sheet"] == "base" for c in good):
                # Already deblocked and given the original's shading when it was cut.
                deblocked = False
                done[n] = prepare_tile(T, t, layer, n, hd)
            else:
                soft = deblock(hd, args.deblock_from, args.deblock_full) if args.deblock_from > 0 else hd
                deblocked = soft is not hd
                hd = soft
                done[n] = prepare_tile(T, t, layer, n, match_lowfreq(T, t, layer, n, hd, args.lowfreq))
            report[k] = {"from": [f"{c['sheet']}#{c['cell']}" for c in good], "score": round(cs[0]["score"], 3),
                         "ncc": round(cs[0]["ncc"], 3), "colourErr": round(cs[0]["err"], 3),
                         "blocky": round(cs[0]["blocky"], 2), "dither": round(cs[0].get("dither", 0.0), 2), "novel": round(cs[0]["novel"], 1),
                         "candidates": len(cs), **({"picked": True} if k in picks else {}),
                         **({"deblocked": round(blockiness(hd), 2)} if deblocked else {})}
        if not done:
            continue
        if args.base and not locked and all(r.get("from") == ["base#0"] for k_, r in report.items() if k_.startswith(f"{layer}:") and "from" in r):
            # Nothing new on this layer (a partial round, D79): keep the base atlas's layer as it is
            # (no second lossy encode).
            import shutil

            base_dir = Path(args.base) / T.shapes_name
            lay = json.loads((base_dir / "manifest.json").read_text())["layers"][layer_s]
            for nm in {lay["image"]} | {r["image"] for r in lay["tiles"].values() if "image" in r}:
                if (base_dir / nm).resolve() != (out_dir / nm).resolve():
                    shutil.copyfile(base_dir / nm, out_dir / nm)
            atlas_manifest["layers"][layer_s] = lay
            for n, img in done.items():
                final[(layer, n)] = img
            print(f"layer {layer}: unchanged, kept from {args.base}")
            continue
        # Seams: every side's edge strip solved jointly over the pairs all the levels' maps have; the
        # kept tiles' strips are held as they are, so the new tiles meet them and they don't move.
        if args.band_lo > 0 or args.band_hi > 0:
            fixed = {n: img[..., :3] for n, img in locked.items()}
            if layer == 0 and not args.no_empty_edges:
                # The empty tiles (one colour, Tyrian's black space, D83) get no painting and draw as
                # the 4x ground, which looks the same; their edges are held at that colour, so a
                # painted tile meets the black where the map puts it next to black instead of
                # taking its strip from whatever else it meets on other maps (a purple plate's
                # bottom edge turned green on BONUS from HARVEST's grass below it; D89).
                for t in d["tiles"].values():
                    n = t["tile"]
                    if t.get("kind") == "empty" and n not in done and n not in fixed:
                        fixed[n] = np.kron(T.rgb[T.tile(n)].astype(np.float32), np.ones((SCALE, SCALE, 1), np.float32))
            have = set(done) | set(fixed)
            pairs = all_pairs(T.levels, layer, models, have)
            # Colour here; alpha is solved on its own below (averaging alpha itself across a pair
            # would put a faint line of cloud where one tile's edge is empty and its neighbour's isn't).
            cont = memo_continuity(T, layer, args.edge_free, args.edge_full) if args.edge_aware else None
            strips = solve_strips({n: img[..., :3] for n, img in done.items()}, pairs, args.lam,
                                  fixed=fixed or None, continuity=cont)
            for n, img in done.items():
                img[..., :3] = apply_strips(img[..., :3], {side: strips[(n, side)] for side in OPPOSITE}, args.band_lo, args.band_hi)
        if layer > 0:
            # Alpha (D78): the smoothed silhouette, its edges solved over the levels' pairs; the kept
            # tiles hold theirs.
            set_alpha(T, layer, d["tiles"], done, models, args, held=list(locked))
        ch = 3 if layer == 0 else 4
        for n, img in done.items():
            final[(layer, n)] = img
        # Images: the layer's existing ones stay as they are; the new tiles go into new ones.
        entry = atlas_manifest["layers"].get(layer_s)
        if entry is not None and not locked:
            entry = None  # every tile of this layer is cut again
        rects_old = {} if entry is None else {k_: r for k_, r in entry["tiles"].items() if int(k_) in locked}
        used = {r.get("image", entry["image"]) for r in rects_old.values()} if entry else set()
        names = [f"{layer}.webp"] + [f"{layer}-{i}.webp" for i in range(2, 100)]
        free = [nm for nm in names if nm not in used]
        order = sorted(done)
        new_rects = {}
        for c0 in range(0, len(order), TILES_PER_ATLAS):
            chunk = {n: done[n] for n in order[c0:c0 + TILES_PER_ATLAS]}
            atlas, rects = pack_atlas(chunk, ch)
            name = free.pop(0)
            img = Image.fromarray(atlas.round().clip(0, 255).astype(np.uint8), "RGB" if ch == 3 else "RGBA")
            save_atlas(img, out_dir / name, args.lossless)
            written.append(name)
            for k_, r in rects.items():
                new_rects[k_] = {**r, "image": name}
            print(f"layer {layer}: {len(chunk)} new tiles -> {out_dir / name} ({img.width}x{img.height})")
        if entry is None:
            main = new_rects[str(order[0])]["image"]
            first = Image.open(out_dir / main)
            entry = {"image": main, "width": first.width, "height": first.height, "tiles": {}}
        else:
            entry = {**entry, "tiles": dict(rects_old)}
            if "variants" in entry:  # variants of re-cut tiles go with them
                entry["variants"] = {k_: v for k_, v in entry["variants"].items() if int(k_) in locked}
                if not entry["variants"]:
                    del entry["variants"]
        for k_, r in new_rects.items():
            entry["tiles"][k_] = {k2: v for k2, v in r.items() if k2 != "image"} if r["image"] == entry["image"] else r
        entry["tiles"] = dict(sorted(entry["tiles"].items(), key=lambda kv: int(kv[0])))
        # The covered tiles (tools/terrain_covered.py, D86) are kept, also when the whole layer is cut
        # again; rerun its `cut` to match a new atlas.
        kept = (atlas_manifest["layers"].get(layer_s) or {}).get("covered")
        if kept:
            entry["covered"] = kept
        atlas_manifest["layers"][layer_s] = entry
        missing = [k_ for k_, t in d["tiles"].items() if needs_art(t, layer, args.structures) and k_ not in entry["tiles"]]
        print(f"layer {layer}: {len(locked)} kept, {len(done)} new, {len(entry['tiles'])} in the atlas"
              + (f"; no art yet for {len(missing)}: {' '.join(missing)}" if missing else ""))
    atlas_manifest["layers"] = dict(sorted(atlas_manifest["layers"].items(), key=lambda kv: int(kv[0])))
    # Images no rect refers to any more (every tile in them was cut again) are removed.
    refs = set()
    for lay in atlas_manifest["layers"].values():
        refs.add(lay["image"])
        refs.update(r["image"] for r in lay["tiles"].values() if "image" in r)
        refs.update(r["image"] for vs in lay.get("variants", {}).values() for r in vs if "image" in r)
        refs.update(r["image"] for r in lay.get("covered", {}).values() if "image" in r)  # D86
    for f in out_dir.glob("*.webp"):
        if f.name not in refs and f.name.split(".")[0].split("-")[0].isdigit():
            f.unlink()
            print(f"  removed {f} (no tile refers to it)")
    (out_dir / "manifest.json").write_text(json.dumps(atlas_manifest, indent=1) + "\n")
    (work / "cut-report.json").write_text(json.dumps(report, indent=1) + "\n")
    weak = [k for k, r in report.items() if r.get("ncc", 1.0) < 0.5]
    print(f"-> {out_dir / 'manifest.json'}; per tile: {work / 'cut-report.json'}" + (f"; weak fits (ncc < 0.5): {' '.join(weak)}" if weak else ""))


def needs_art(t: dict, layer: int, structures: bool = False) -> bool:
    """Whether a tile should end up in the atlas: drawn as a tile, not one colour, terrain (or a
    structure when asked)."""
    kind = t.get("kind", "terrain")
    return bool(t.get("drawnAsTile")) and kind != "empty" and (kind != "structure" or structures)


# --- Check --------------------------------------------------------------------------------------


def load_atlas(out_root: Path, shapes: str) -> dict[int, dict[int, np.ndarray]]:
    return load_tileset_art(Path(out_root) / shapes)[1]


def _step(p: np.ndarray, q: np.ndarray, extra: np.ndarray | None = None) -> float | None:
    """Mean abs colour difference of two facing strips (N, 4), weighted by the smaller alpha (and `extra`)."""
    wgt = np.minimum(p[:, 3], q[:, 3]) / 255
    if extra is not None:
        wgt = wgt * extra
    if wgt.sum() < 1:
        return None
    return float((np.abs(p[:, :3] - q[:, :3]).mean(1) * wgt).sum() / wgt.sum())


def _steps_along(T_: np.ndarray, axis: int) -> list[float]:
    """_step between every pair of neighbouring texel columns (axis 1) or rows (axis 0), vectorised."""
    a, b = (T_[:, :-1], T_[:, 1:]) if axis == 1 else (T_[:-1], T_[1:])
    d = np.abs(a[..., :3] - b[..., :3]).mean(-1)
    w = np.minimum(a[..., 3], b[..., 3]) / 255
    red = 0 if axis == 1 else 1  # sum along the strip
    ws = w.sum(red)
    num = (d * w).sum(red)
    return [float(x) for x in (num / np.maximum(ws, 1e-9))[ws >= 1]]


def inside_steps(T_: np.ndarray, band: int = 8) -> tuple[float | None, float | None]:
    """A tile's mean colour step between neighbouring texels, and between neighbouring `band`-texel strips."""
    vals = _steps_along(T_, 1) + _steps_along(T_, 0)
    bvals = [_step(T_[:, c - band:c].mean(1), T_[:, c:c + band].mean(1)) for c in range(band, T_.shape[1] - band + 1, band)]
    bvals += [_step(T_[c - band:c].mean(0), T_[c:c + band].mean(0)) for c in range(band, T_.shape[0] - band + 1, band)]
    bvals = [v for v in bvals if v is not None]
    return (float(np.mean(vals)) if vals else None, float(np.mean(bvals)) if bvals else None)


def memo_continuity(T, layer: int, free: float = EDGE_FREE, full: float = EDGE_FULL):
    """edge_continuity for one layer, remembered per pair."""
    cache: dict = {}

    def cont(o: str, a: int, b: int) -> np.ndarray:
        if (o, a, b) not in cache:
            cache[(o, a, b)] = edge_continuity(T, o, a, b, layer, free, full)
        return cache[(o, a, b)]
    return cont


def seam_stats(tiles: dict[int, np.ndarray], grid, drawn=None, band: int = 8, pair_filter=None, _inside: dict | None = None,
               continuity=None) -> dict:
    """Colour steps across every tile edge the map(s) have (both sides with HD art), against the same
    steps between neighbouring texels (and neighbouring `band`-texel strips) inside tiles. Alpha
    weights the steps on translucent layers. 0-255 RGB, mean abs per channel. `grid`, `drawn`: one
    map, or `grid` a list of (grid, drawn) for several levels (pairs and tile counts summed).
    `pair_filter(a, b)`: only those pairs, and the tiles in them for the inside steps.
    `continuity(o, a, b)` (edge_continuity): also the edge step only where the original itself is
    continuous across the edge (continuousRatio): a real edge in the art (rock against space) is no seam."""
    maps = grid if isinstance(grid, list) else [(grid, drawn)]
    tiles = {n: (t if t.shape[2] == 4 else np.concatenate([t, np.full(t.shape[:2] + (1,), 255, np.float32)], -1)) for n, t in tiles.items()}
    pairs, occ = Counter(), Counter()
    for g, d in maps:
        pairs.update(map_pairs(g, d, tiles))
        occ.update(int(t) for t in g[d] if int(t) in tiles)
    if pair_filter:
        pairs = Counter({p: c for p, c in pairs.items() if pair_filter(p[1], p[2])})
        involved = {x for p in pairs for x in p[1:]}
        occ = Counter({n: c for n, c in occ.items() if n in involved})
    edge_t, edge_b, edge_c, rows = [], [], [], []
    for (o, a, b), n in pairs.items():
        A, B = tiles[a], tiles[b]
        if o == "h":
            t = _step(A[:, -1], B[:, 0])
            bb = _step(A[:, -band:].mean(1), B[:, :band].mean(1))
        else:
            t = _step(A[-1], B[0])
            bb = _step(A[-band:].mean(0), B[:band].mean(0))
        if t is None:
            continue
        if continuity is not None:
            w = np.repeat(continuity(o, a, b), SCALE)
            tc = _step(A[:, -1], B[:, 0], w) if o == "h" else _step(A[-1], B[0], w)
            if tc is not None:
                edge_c.append((tc, n * float(w.mean())))
        edge_t.append((t, n))
        edge_b.append((bb, n))
        rows.append({"pair": f"{a}{'|' if o == 'h' else '/'}{b}", "count": n, "texelStep": round(t, 2), "bandStep": round(bb, 2)})
    cache = _inside if _inside is not None else {}
    in_t, in_b = [], []
    for n_, T_ in tiles.items():
        k = occ.get(n_, 0)
        if not k:
            continue
        if n_ not in cache:
            cache[n_] = inside_steps(T_, band)
        it_, ib_ = cache[n_]
        if it_ is not None:
            in_t.append((it_, k))
            in_b.append((ib_ if ib_ is not None else it_, k))
    wm = lambda xs: sum(v * n for v, n in xs) / max(sum(n for _, n in xs), 1)  # noqa: E731
    et, it, eb, ib = wm(edge_t), wm(in_t), wm(edge_b), wm(in_b)
    for r in rows:
        r["ratio"] = round(r["texelStep"] / max(it, 1e-3), 2)
    rows.sort(key=lambda r: -r["texelStep"] * math.sqrt(r["count"]))
    out = {"edges": sum(n for _, n in edge_t), "edgeTexelStep": round(et, 2), "insideTexelStep": round(it, 2),
           "texelRatio": round(et / max(it, 1e-3), 3), "edgeBandStep": round(eb, 2), "insideBandStep": round(ib, 2),
           "bandRatio": round(eb / max(ib, 1e-3), 3)}
    if continuity is not None:
        ec = wm(edge_c)
        out["continuousEdgeStep"] = round(ec, 2)
        out["continuousRatio"] = round(ec / max(it, 1e-3), 3)
    out["worst"] = rows[:15]
    return out


def contact_sheet(L: LevelData, layer: int, tiles: dict[int, np.ndarray], g: np.ndarray, drawn: np.ndarray, y0: int, rows: int) -> Image.Image:
    """Map rows y0.. of one level, original (nearest) | HD, at 4 px per original pixel."""
    S = 4
    k = SCALE // S
    sub = g[y0:y0 + rows]
    dsub = drawn[y0:y0 + rows]
    rh, W = sub.shape
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
            cell = img[ys:ys + TILE_H * S, xh:xh + TILE_W * S]
            if t in tiles:
                hd = tiles[t]
                if hd.shape[2] == 3:
                    hd = np.concatenate([hd, np.full(hd.shape[:2] + (1,), 255, np.float32)], -1)
                hd = hd.reshape(TILE_H * S, k, TILE_W * S, k, 4).mean((1, 3))
                a = hd[..., 3:] / 255
                img[ys:ys + TILE_H * S, xh:xh + TILE_W * S] = cell * (1 - a) + hd[..., :3] * a
            else:
                img[ys:ys + TILE_H * S, xh:xh + TILE_W * S] = cell * (1 - oa) + o * oa
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))


def cmd_check(args) -> None:
    T = TilesetData(Path(args.data), level_list(args))
    work = Path(args.work)
    out = work / "check"
    out.mkdir(parents=True, exist_ok=True)
    atlas = load_atlas(Path(args.out), T.shapes_name)
    models = load_models(T.shapes_file)
    # Which tiles the last cut made (cut-report.json): their edges are reported on their own, and
    # the contact sheets show the rows that have them.
    rp = work / "cut-report.json"
    cut = json.loads(rp.read_text()) if rp.exists() else {}
    new = {int(k.split(":")[0]): set() for k in cut}
    for k, r in cut.items():
        if "from" in r:
            new[int(k.split(":")[0])].add(int(k.split(":")[1]))
    contact = args.contact
    report = {}
    for layer, tiles in sorted(atlas.items()):
        maps = []
        for L in T.levels:
            g, drawn, _ = layer_masks(L, layer, models)
            maps.append((g, drawn))
        inside: dict = {}
        cont = memo_continuity(T, layer)
        st = seam_stats(tiles, maps, _inside=inside, continuity=cont)
        fresh = new.get(layer, set())
        if fresh:
            st["new"] = seam_stats(tiles, maps, pair_filter=lambda a, b: a in fresh or b in fresh, _inside=inside, continuity=cont)
            st["kept"] = seam_stats(tiles, maps, pair_filter=lambda a, b: a not in fresh and b not in fresh, _inside=inside, continuity=cont)
            del st["kept"]["worst"]
        st["levels"] = {}
        for L, (g, drawn) in zip(T.levels, maps):
            s1 = seam_stats(tiles, g, drawn, _inside=inside, continuity=cont)
            if s1["edges"]:
                st["levels"][L.id] = {k: s1[k] for k in ("edges", "texelRatio", "bandRatio", "continuousRatio")}
        report[str(layer)] = st
        print(f"layer {layer}: {st['edges']} edges; texel step across edges {st['edgeTexelStep']} vs inside {st['insideTexelStep']} "
              f"(ratio {st['texelRatio']}; where the original is continuous {st['continuousRatio']}); 8-texel band step "
              f"{st['edgeBandStep']} vs {st['insideBandStep']} (ratio {st['bandRatio']})")
        for part in ("new", "kept"):
            if part in st:
                p = st[part]
                print(f"  edges with a {'new' if part == 'new' else 'kept'} tile{'' if part == 'new' else ' only'}: {p['edges']}; "
                      f"ratio {p['texelRatio']} (continuous {p['continuousRatio']}), bands {p['bandRatio']}")
        # Contact sheets: original (nearest) | HD; "new": only the row blocks that show a tile the
        # last cut made, "all": every row block, "none".
        n_sheets = 0
        if contact != "none":
            for L, (g, drawn) in zip(T.levels, maps):
                if contact not in ("all", "new") and L.id not in contact.split(","):
                    continue
                if contact == "new" and not fresh and len(T.levels) > 3:
                    continue  # nothing new to look at: a whole tileset's maps would be thousands of sheets
                for y0 in range(0, g.shape[0], args.rows):
                    sub, dsub = g[y0:y0 + args.rows], drawn[y0:y0 + args.rows]
                    shown = {int(t) for t in sub[dsub]}
                    if not shown & set(tiles) or (contact == "new" and fresh and not shown & fresh):
                        continue
                    contact_sheet(L, layer, tiles, g, drawn, y0, args.rows).save(out / f"{L.id}-l{layer}-rows{y0:03d}.jpg", quality=88)
                    n_sheets += 1
        print(f"  {n_sheets} contact sheets (original | HD) in {out}")
    (out / "seams.json").write_text(json.dumps(report, indent=1) + "\n")
    print(f"-> {out / 'seams.json'}")


# --- CLI -----------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(ROOT / "data"), help="the game data (default data/)")
    ap.add_argument("--level", default="1-9", help="episode-levelfile, as reference/tiles names levels (default 1-9, TYRIAN); "
                    "several levels of one tileset comma-separated (1-9,1-11,4-16)")
    ap.add_argument("--tileset", help="every level that uses this tileset (shapesz or z), instead of --level")
    ap.add_argument("--work", default=str(ROOT / "reference/terrain-hd"), help="working folder (inventory, sheets, results, check)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    art_root = str(ROOT / "public/art/terrain")
    i = sub.add_parser("inventory", help="list the tiles the levels draw")
    i.add_argument("--out", default=art_root, help="atlas root, to mark the tiles that already have art (default public/art/terrain)")
    i.add_argument("--kind", help="override the layer 1-2 classification, e.g. 2:575=terrain,1:518=structure")
    s_ = sub.add_parser("sheets", help="make the Gemini input sheets and their manifest")
    s_.add_argument("--out", default=art_root, help="atlas root (default public/art/terrain)")
    s_.add_argument("--structures", action="store_true", help="also sheets for layer 1-2 structure tiles (default: terrain only)")
    s_.add_argument("--no-reuse", action="store_true", help="also paint tiles whose painting on another layer the cutter would reuse")
    s_.add_argument("--recut", help="tiles that have art but should be painted again, e.g. 0:46,1:53")
    s_.add_argument("--blocks", action="store_true", help="send the nearest-neighbour sheets (D58) instead of the softened ones")
    s_.add_argument("--soft", type=float, default=0.0, help="also write sheets softened by MMPX + a blur of this many original pixels (e.g. 0.5, D79) to sheets/soft/, with softFile and softPrompt in the manifest")
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
    c.add_argument("--dither-free", type=float, default=DITHER_FREE, help=f"pixel-period ratio (blocks and checker dither) that costs nothing (default {DITHER_FREE})")
    c.add_argument("--dither-cost", type=float, default=DITHER_COST, help=f"score per unit of pixel-period ratio above that (default {DITHER_COST})")
    c.add_argument("--base", help="atlas root whose tiles compete as candidates (a partial round of answers, D79), e.g. public/art/terrain")
    c.add_argument("--base-cost", type=float, default=BASE_COST, help=f"score taken from a base tile, so a new painting that fits nearly as well replaces it (default {BASE_COST})")
    c.add_argument("--exclude", help="tiles to leave out (they fall back to the original), e.g. 0:332,1:41")
    c.add_argument("--pick", help="hand-picked candidates, e.g. 0:68=region-l0-03#0 (sheet#cell as in cut-report.json)")
    c.add_argument("--cache", help="pickle of the registered candidates per answer: answers new or changed since are registered and added, the rest are read back")
    c.add_argument("--lossless", action="store_true", help="lossless WebP (default quality 92)")
    c.add_argument("--band-lo", type=float, default=BAND_LO, help=f"texels a seam correction fades over (default {BAND_LO}; 0 and --band-hi 0: no seam pass)")
    c.add_argument("--band-hi", type=float, default=BAND_HI, help=f"texels at the edge set to the shared strip (default {BAND_HI})")
    c.add_argument("--lam", type=float, default=LAMBDA, help=f"how much a strip keeps its own painting (default {LAMBDA})")
    for p_ in (c, ra := sub.add_parser("realpha", help="redo the alpha of an atlas's layers 1-2 (no answers needed)")):
        p_.add_argument("--alpha-min-pairs", type=int, default=ALPHA_MIN_PAIRS, help=f"map pairs needed before two tiles' alpha edges are pulled together (default {ALPHA_MIN_PAIRS})")
    ra.add_argument("--out", default=str(ROOT / "public/art/terrain"), help="atlas root (default public/art/terrain)")
    ra.add_argument("--lossless", action="store_true", help="lossless WebP (default quality 92)")
    ra.add_argument("--layers", help="only these layers, e.g. 2 (default: 1 and 2)")
    ra.add_argument("--alpha-smooth", type=float, default=ALPHA_SMOOTH, help=f"texels the contour is smoothed at (default {ALPHA_SMOOTH}; at most 40)")
    ra.add_argument("--alpha-ramp", type=float, default=ALPHA_RAMP, help=f"texels each side of the contour alpha goes 0 -> 1 over (default {ALPHA_RAMP})")
    ra.add_argument("--rim-inset", type=int, default=0, help="texels in from the old edge whose colour is bled outwards, so the original's dark outline "
                    "doesn't ring a wider soft edge (default 0: colour as it is)")
    ra.add_argument("--band-lo", type=float, default=BAND_LO, help=f"texels an alpha seam correction fades over (default {BAND_LO})")
    ra.add_argument("--band-hi", type=float, default=BAND_HI, help=f"texels at the edge set to the shared strip (default {BAND_HI})")
    ra.add_argument("--lam", type=float, default=LAMBDA, help=f"how much a strip keeps its own (default {LAMBDA})")
    c.add_argument("--replace", action="store_true", help="cut every tile again into fresh atlases (default: merge, keeping the "
                   "tiles the atlas already has byte for byte)")
    c.add_argument("--recut", help="tiles the atlas has that should be cut again from the answers, e.g. 0:46,1:53")
    c.add_argument("--structures", action="store_true", help="also cut layer 1-2 structure tiles (default: terrain only)")
    c.add_argument("--no-reuse", action="store_true", help="don't reuse another layer's painting of the same tile")
    c.add_argument("--edge-aware", action="store_true", help="don't tie facing strips where the original has a real edge between "
                   "the tiles (rock against space); off by default: on the fake runs it measured the same as tying everywhere (D83)")
    c.add_argument("--no-empty-edges", action="store_true", help="don't hold the ground's empty tiles (one-colour black space) as "
                   "fixed neighbours in the seam solve (D89)")
    c.add_argument("--edge-free", type=float, default=EDGE_FREE, help=f"step between the original's facing pixels that still ties the strips fully (default {EDGE_FREE})")
    c.add_argument("--edge-full", type=float, default=EDGE_FULL, help=f"step from which it doesn't tie them at all (default {EDGE_FULL})")
    rf = sub.add_parser("rimfix", help="take the teal rim off an atlas's blue-grey ground tiles (no answers needed)")
    rf.add_argument("tileset", help="the tileset's folder name, e.g. shapesx")
    rf.add_argument("--out", default=str(ROOT / "public/art/terrain"), help="atlas root (default public/art/terrain)")
    rf.add_argument("--lossless", action="store_true", help="lossless WebP (default quality 92)")
    rf.add_argument("--dry-run", action="store_true", help="only list the tiles it would change")
    k = sub.add_parser("check", help="reassemble the map from the atlas, measure seams")
    k.add_argument("--out", default=str(ROOT / "public/art/terrain"), help="atlas root (default public/art/terrain)")
    k.add_argument("--rows", type=int, default=12, help="map rows per contact sheet")
    k.add_argument("--contact", default="new", help="contact sheets: new (default: row blocks with a tile the last cut made; "
                   "every row block when nothing is new and at most 3 levels), all, none, or level ids (1-9,1-11)")
    args = ap.parse_args(argv)
    {"inventory": cmd_inventory, "sheets": cmd_sheets, "fake": cmd_fake, "cut": cmd_cut, "realpha": cmd_realpha, "rimfix": cmd_rimfix, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    main()
