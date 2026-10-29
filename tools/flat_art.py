"""Flat remastered sprites: Gemini art cut, registered and packed as atlases (DECISIONS.md D42 draws them, D43 is this pipeline).

Shots and pickups stay flat 2D sprites in game, drawn with high-resolution art made by Google Gemini
from input sheets of the original sprites. This tool does both ends of that loop:

    python tools/flat_art.py sheets --inventory INV.json --out DIR
        Gemini input sheets (PNG, original pixels scaled up nearest-neighbour, on a dark checker) and
        DIR/manifest.json saying which sprite sits where. Derived from the game data, so they stay
        out of git (D3); keep them in a scratch folder.

    python tools/flat_art.py cut --inputs DIR/manifest.json --results RESULTS_DIR [--out public/art/sprites]
        For each input sheet, RESULTS_DIR/<sheet name>.png|jpg|webp (Gemini's answer, any size, same
        aspect as the input) is cut item by item, each item's art registered onto its original sprite
        (scale and offset fitted by matching the art's foreground mask to the sprite's mask), given the
        sprite's silhouette as alpha, and packed into one RGBA WebP atlas per original sprite sheet,
        with public/art/sprites/manifest.json:
            { "scale": 8, "sheets": { "tyrian.shp#7": { "image": "tyrian-shp-7.webp",
              "frames": { "59": { "x": .., "y": .., "w": .., "h": .. } } } } }
        A sheet is keyed by the game's Sprite2Sheet.id and a frame by the 1-based sprite index the
        draw list carries (SpriteDraw.sheet.id / SpriteDraw.index). A frame is the sprite's own box
        (12 px wide, as many rows as the sprite decodes to) times `scale`, its top-left at the blit
        position. --check PNG also writes a contact sheet: original (nearest, 8x) | remastered.

The original sprites are read from the game data (--data, default data/): tyrian.shp's Sprite2
tables (src/data/sprites.ts) and palette.dat (src/data/palette.ts).
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SCALE = 8  # atlas texels per original sprite pixel
TILE_W, TILE_H, SHEET_COLS = 12, 14, 19
LEVEL1_PALETTE = 5  # drawList.palette in Episode 1's first level (TYRIAN)

# --- Game data -----------------------------------------------------------------------------------


class GameData:
    """tyrian.shp's tables and palette.dat, read as src/data/sprites.ts and palette.ts do."""

    def __init__(self, data_dir: Path):
        shp = (data_dir / "tyrian.shp").read_bytes()
        count = struct.unpack_from("<H", shp, 0)[0]
        pos = [struct.unpack_from("<I", shp, 2 + i * 4)[0] for i in range(count)] + [len(shp)]
        self.tables = [shp[pos[i]:pos[i + 1]] for i in range(count)]
        pal = (data_dir / "palette.dat").read_bytes()
        self.palettes = []
        for p in range(len(pal) // 768):
            raw = np.frombuffer(pal[p * 768:(p + 1) * 768], dtype=np.uint8).reshape(256, 3).astype(np.int32)
            self.palettes.append(((raw << 2) | (raw >> 4)).astype(np.uint8))

    def sheet(self, sheet_id: str) -> bytes:
        if not sheet_id.startswith("tyrian.shp#"):
            raise ValueError(f"only tyrian.shp sheets are supported, not {sheet_id}")
        return self.tables[int(sheet_id.split("#")[1])]

    def sprite(self, sheet_id: str, index: int) -> np.ndarray:
        """decodeSprite2: palette indices, 12 wide, as many rows as the RLE has; -1 = transparent."""
        sheet = self.sheet(sheet_id)
        off = (index - 1) * 2
        if index < 1 or off + 1 >= len(sheet):
            return np.full((0, TILE_W), -1, dtype=np.int16)
        rows: list[list[int]] = []
        row = [-1] * TILE_W
        p = sheet[off] | (sheet[off + 1] << 8)
        x = 0
        while p < len(sheet) and sheet[p] != 0x0F:
            x += sheet[p] & 0x0F
            n = sheet[p] >> 4
            if n == 0:
                rows.append(row)
                row = [-1] * TILE_W
                x = 0
            else:
                for _ in range(n):
                    p += 1
                    if x < TILE_W and p < len(sheet):
                        row[x] = sheet[p]
                    x += 1
            p += 1
        if any(c >= 0 for c in row):
            rows.append(row)
        return np.array(rows, dtype=np.int16).reshape(len(rows), TILE_W)

    def compose(self, sheet_id: str, index: int, size: int) -> np.ndarray:
        """A 12x14 tile, or the 24x28 block index, +1, +19, +20 (blit_sprite2x2 / a 2x2 enemy)."""
        if size == 1:
            return self.sprite(sheet_id, index)
        out = np.full((28, 24), -1, dtype=np.int16)
        for off, ox, oy in ((0, 0, 0), (1, 12, 0), (19, 0, 14), (20, 12, 14)):
            s = self.sprite(sheet_id, index + off)[:14]
            sub = out[oy:oy + s.shape[0], ox:ox + 12]
            sub[s >= 0] = s[s >= 0]
        return out

    def rgba(self, pic: np.ndarray, palette: int = LEVEL1_PALETTE) -> np.ndarray:
        pal = self.palettes[palette]
        out = np.zeros(pic.shape + (4,), dtype=np.uint8)
        m = pic >= 0
        out[m, :3] = pal[pic[m]]
        out[m, 3] = 255
        return out


# --- Silhouette alpha ----------------------------------------------------------------------------


def smooth_alpha(mask: np.ndarray, scale: int = SCALE, sigma: float = 3.0, ramp: float = 0.2) -> np.ndarray:
    """A pixel mask upscaled `scale`x with rounded staircases and a soft edge of about 1.5 texels.

    The mask is upscaled nearest, blurred (sigma in texels) and passed through a steep ramp around
    0.5, so the edge sits where the original pixel edge was (straight runs keep their place, corners
    round off) and fades over ramp / slope ~ 1.5 texels. Single pixels survive (peak ~0.67).
    """
    from scipy import ndimage

    big = np.kron(mask.astype(np.float32), np.ones((scale, scale), np.float32))
    pad = int(math.ceil(sigma * 3))
    big = np.pad(big, pad)
    blurred = ndimage.gaussian_filter(big, sigma)[pad:-pad, pad:-pad]
    return np.clip((blurred - 0.5) / ramp + 0.5, 0.0, 1.0)


def bleed(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Fill colour under alpha ~0 from the nearest visible texel, so bilinear filtering has no dark fringe."""
    from scipy import ndimage

    inside = alpha > 0.5
    if not inside.any():
        return rgb
    _, (iy, ix) = ndimage.distance_transform_edt(~inside, return_indices=True)
    out = rgb.copy()
    soft = alpha < 0.98
    out[soft] = rgb[iy[soft], ix[soft]]
    return out


# --- Objects: the picture shown in a cell and the atlas frames (tiles) cut from it ----------------


def object_tiles(gd: GameData, sheet: str, index: int, size: int) -> list[dict]:
    """The tiles a frame is drawn as: (sprite index, offset in the picture, its own pixels)."""
    offs = ((0, 0, 0),) if size == 1 else ((0, 0, 0), (1, 12, 0), (19, 0, 14), (20, 12, 14))
    out = []
    for d, ox, oy in offs:
        px = gd.sprite(sheet, index + d)
        if px.shape[0] == 0 or not (px >= 0).any():
            continue
        out.append({"index": index + d, "ox": ox, "oy": oy, "pixels": px})
    return out


def picture(gd: GameData, sheet: str, index: int, size: int) -> np.ndarray:
    """The frame as drawn: its tiles overlaid in draw order, not cropped (a tile may be taller than 14)."""
    tiles = object_tiles(gd, sheet, index, size)
    h = max([size * TILE_H] + [t["oy"] + t["pixels"].shape[0] for t in tiles])
    out = np.full((h, size * TILE_W), -1, np.int16)
    for t in tiles:
        p = t["pixels"]
        sub = out[t["oy"]:t["oy"] + p.shape[0], t["ox"]:t["ox"] + TILE_W]
        sub[p >= 0] = p[p >= 0]
    return out


def trim_box(pic: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(pic >= 0)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def mirror_of(a: np.ndarray, b: np.ndarray) -> tuple[int, int] | None:
    """If b is a horizontally mirrored a, the map from b's coordinates to a's: x_a = -x_b + tx, y_a = y_b + ty."""
    ax0, ay0, ax1, ay1 = trim_box(a)
    bx0, by0, bx1, by1 = trim_box(b)
    ta, tb = a[ay0:ay1, ax0:ax1], b[by0:by1, bx0:bx1]
    if ta.shape == tb.shape and (ta[:, ::-1] == tb).all():
        return ax1 + bx0, ay0 - by0
    return None


# --- Gemini input sheets -------------------------------------------------------------------------

# Which inventory families share a sheet (each sheet at most MAX_CELLS cells; bigger ones are split).
SHEET_GROUPS = [
    ("shots-pulse-multi", ["pulse-cannon", "multi-cannon-front"]),
    ("shots-multi-rear", ["multi-cannon-rear"]),
    ("shots-sonic", ["sonic-wave"]),
    ("shots-misc", ["vulcan", "protron", "heavy-guided-bombs", "sidekick-shots", "enemy-shots"]),
    ("coins", ["coins"]),
    ("gems", ["gems"]),
    ("datacubes", ["datacube"]),
    ("orbs-capsules", ["power-orb", "capsules"]),
]
MAX_CELLS = 12
CELL = 256  # input cell size, px
FILL = 0.6  # the biggest item in a sheet spans this much of a cell


def background(w: int, h: int) -> np.ndarray:
    return np.zeros((h, w, 3), np.uint8)  # black: Gemini answers on black, which keeps the masks clean


def build_sheets(gd: GameData, inventory: dict, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    fams = {f["family"]: f for f in inventory["families"]}
    manifest = {"cell_note": "rect = [x, y, w, h] in input px; art = where the cell's picture (sprite px) sits: input px = (x + px * scale, y + py * scale). Each frame maps its own sprite px (u, v) to picture px: px = sx * u + tx, py = sy * v + ty (sy defaults to 1; sx = -1 for a mirrored sprite sharing the cell; an animation frame sharing a cell maps its bounding box onto the picture's, e.g. a coin's narrower spin frames squash the face).",
                "palette": LEVEL1_PALETTE, "sheets": []}
    for name, members in SHEET_GROUPS:
        cells = []  # one per distinct picture; mirrored sprites join their twin's cell
        for fam in members:
            for obj in fams[fam]["objects"]:
                for fr in obj["frames"]:
                    pic = picture(gd, obj["sheet"], fr, obj["size"])
                    frames = [{"sheet": obj["sheet"], "index": t["index"], "sx": 1, "tx": t["ox"], "ty": t["oy"]}
                              for t in object_tiles(gd, obj["sheet"], fr, obj["size"])]
                    twin = None
                    if obj["size"] == 1:
                        for c in cells:
                            if c["size"] == 1 and c["sheet"] == obj["sheet"]:
                                m = mirror_of(c["pic"], pic)
                                if m:
                                    twin = c
                                    twin["frames"].append({"sheet": obj["sheet"], "index": fr, "sx": -1, "tx": m[0], "ty": m[1]})
                                    break
                    if twin is None:
                        cells.append({"object": obj["name"], "family": fam, "sheet": obj["sheet"], "index": fr, "size": obj["size"], "pic": pic, "frames": frames})
        # Balanced split, keeping each object's frames (a coin's spin) on one sheet where they fit.
        n_sheets = math.ceil(len(cells) / MAX_CELLS)
        per = math.ceil(len(cells) / n_sheets)
        parts: list[list[dict]] = [[]]
        for i, c in enumerate(cells):
            run = sum(1 for d in cells[i:] if d["object"] == c["object"]) if (i == 0 or cells[i - 1]["object"] != c["object"]) else 0
            if parts[-1] and (len(parts[-1]) >= MAX_CELLS or (run > 1 and len(parts[-1]) + min(run, MAX_CELLS) > MAX_CELLS)
                              or (run == 1 and len(parts[-1]) >= per)):
                parts.append([])
            parts[-1].append(c)
        n_sheets = len(parts)
        for s, part in enumerate(parts):
            sheet_name = name if n_sheets == 1 else f"{name}-{s + 1}"
            cols = 3 if len(part) <= 9 and len(part) not in (4, 8) else 4
            if len(part) <= 3:
                cols = len(part)
            rows = math.ceil(len(part) / cols)
            biggest = max(max(trim_box(c["pic"])[2] - trim_box(c["pic"])[0], trim_box(c["pic"])[3] - trim_box(c["pic"])[1]) for c in part)
            px = max(2, min(24, int(CELL * FILL // biggest)))
            img = background(cols * CELL, rows * CELL)
            entry = {"name": sheet_name, "image": f"{sheet_name}.png", "size": [cols * CELL, rows * CELL],
                     "grid": {"rows": rows, "cols": cols, "cell": CELL}, "scale": px, "cells": []}
            for i, c in enumerate(part):
                r, k = divmod(i, cols)
                x0, y0, x1, y1 = trim_box(c["pic"])
                # centre the visible part of the picture in the cell
                ax = k * CELL + (CELL - (x1 - x0) * px) // 2 - x0 * px
                ay = r * CELL + (CELL - (y1 - y0) * px) // 2 - y0 * px
                rgba = gd.rgba(c["pic"])
                big = np.kron(rgba, np.ones((px, px, 1), np.uint8))
                h, w = big.shape[:2]
                region = img[ay:ay + h, ax:ax + w]
                m = big[..., 3] > 0
                region[m] = big[..., :3][m]
                entry["cells"].append({"row": r, "col": k, "rect": [k * CELL, r * CELL, CELL, CELL], "object": c["object"], "family": c["family"],
                                       "art": {"sheet": c["sheet"], "index": c["index"], "size": c["size"], "x": ax, "y": ay,
                                               "w": int(c["pic"].shape[1]), "h": int(c["pic"].shape[0]), "scale": px},
                                       "search": CELL // 5, "frames": c["frames"]})
            Image.fromarray(img).save(out / entry["image"])
            manifest["sheets"].append(entry)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


# --- Cutting Gemini's answer ---------------------------------------------------------------------


def load_result(results: Path, sheet_name: str) -> np.ndarray | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = results / f"{sheet_name}{ext}"
        if p.exists():
            return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0
    return None


def visible_mask(gd: GameData, pic: np.ndarray, palette: int) -> np.ndarray:
    """The picture's pixels that show against the black input background (dark outlines don't)."""
    rgb = gd.rgba(pic, palette)[..., :3].astype(np.float32) / 255.0
    return (pic >= 0) & (rgb.max(-1) > 0.16)


def register(art: np.ndarray, mask: np.ndarray, nominal: tuple[float, float, float, float], window: tuple[int, int, int, int],
             search: float) -> dict:
    """Fit the sprite mask onto the art's foreground.

    art: the result image (H, W, 3) in 0..1. mask: the picture's visible pixels (sprite px).
    nominal: (x0, y0, kx, ky): result px of picture px (0, 0) and result px per picture px, from the
    input sheet's layout. window: (x0, y0, x1, y1) result px to look in. search: max shift, result px.

    Foreground: the art's brightest pixels, as many as the sprite would cover at the nominal scale,
    so a dim glow or halo around a shot is left out and only its core is matched. The fit then tries
    scales 0.8-1.25x (and aspect 0.9-1.1) and, for each, every shift (FFT cross-correlation), keeping
    the best Dice overlap. Returns x0, y0, kx, ky (result px = x0 + kx * px) and the score.
    """
    from scipy import ndimage, signal

    wx0, wy0, wx1, wy1 = window
    crop = art[wy0:wy1, wx0:wx1]
    lum = crop.max(-1)
    x0n, y0n, kxn, kyn = nominal
    # Work at a resolution where the picture is ~64 px across.
    ph, pw = mask.shape
    f = min(1.0, 64.0 / max(pw * kxn, ph * kyn))
    small = ndimage.zoom(ndimage.gaussian_filter(lum, 0.5 / f if f < 1 else 0), f, order=1)
    expected = mask.sum() * kxn * kyn * f * f
    flat = np.sort(small.ravel())[::-1]
    t = flat[min(len(flat) - 1, int(expected))] if expected < len(flat) else flat[-1]
    t = max(t, 0.08)
    fg = (small > t).astype(np.float32)
    best = {"score": -1.0}
    for k in np.arange(0.8, 1.2501, 0.025):
        for a in (0.9, 0.95, 1.0, 1.05, 1.1):
            kx, ky = kxn * k * math.sqrt(a) * f, kyn * k / math.sqrt(a) * f
            mw, mh = max(1, int(round(pw * kx))), max(1, int(round(ph * ky)))
            m = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize((mw, mh), Image.BILINEAR), np.float32) / 255.0
            m = (m > 0.5).astype(np.float32)
            if m.sum() == 0 or mw > fg.shape[1] or mh > fg.shape[0]:
                continue
            corr = signal.fftconvolve(fg, m[::-1, ::-1], mode="valid")  # corr[y, x] = overlap with m at (x, y)
            # shifts allowed: within `search` of the nominal placement (centre to centre)
            nx = (x0n + kxn * pw / 2 - wx0) * f - mw / 2
            ny = (y0n + kyn * ph / 2 - wy0) * f - mh / 2
            yy, xx = np.mgrid[0:corr.shape[0], 0:corr.shape[1]]
            ok = (np.abs(xx - nx) <= search * f) & (np.abs(yy - ny) <= search * f)
            if not ok.any():
                continue
            dice = 2 * corr / (fg.sum() + m.sum())
            dice[~ok] = -1
            i = np.unravel_index(dice.argmax(), dice.shape)
            if dice[i] > best["score"]:
                best = {"score": float(dice[i]), "x0": wx0 + i[1] / f, "y0": wy0 + i[0] / f, "kx": mw / pw / f, "ky": mh / ph / f}
    if best["score"] < 0:  # nothing fitted: keep the nominal placement
        best = {"score": 0.0, "x0": x0n, "y0": y0n, "kx": kxn, "ky": kyn}
    return best


def sample(art: np.ndarray, xs: np.ndarray, ys: np.ndarray, footprint: float) -> np.ndarray:
    """Bilinear samples of art at result px (xs, ys), pre-blurred when shrinking (footprint = result px per texel)."""
    from scipy import ndimage

    src = art
    if footprint > 1.5:
        src = np.stack([ndimage.gaussian_filter(art[..., c], 0.45 * footprint) for c in range(3)], -1)
    return np.stack([ndimage.map_coordinates(src[..., c], [ys - 0.5, xs - 0.5], order=1, mode="nearest") for c in range(3)], -1)


def cut_sheet(gd: GameData, sheet: dict, art: np.ndarray, palette: int) -> list[dict]:
    """Every atlas frame of one input sheet: {sheet, index, rgba (h*8, 96, 4), fit}."""
    H, W = art.shape[:2]
    rx, ry = W / sheet["size"][0], H / sheet["size"][1]
    out = []
    for cell in sheet["cells"]:
        a = cell["art"]
        pic = picture(gd, a["sheet"], a["index"], a["size"])
        mask = visible_mask(gd, pic, palette)
        s = a["scale"]
        nominal = (a["x"] * rx, a["y"] * ry, s * rx, s * ry)
        cx, cy, cw, ch = cell["rect"]
        search = cell.get("search", CELL // 5)
        # Look only around the item (its box grown by the search distance and a quarter of its size):
        # neighbours in the same cell (strips of sprites) would otherwise compete for the foreground.
        gx, gy = search + a["w"] * s / 4, search + a["h"] * s / 4
        window = (int(max(cx, a["x"] - gx) * rx), int(max(cy, a["y"] - gy) * ry),
                  int(math.ceil(min(cx + cw, a["x"] + a["w"] * s + gx) * rx)), int(math.ceil(min(cy + ch, a["y"] + a["h"] * s + gy) * ry)))
        fit = register(art, mask, nominal, window, search * max(rx, ry))
        fit["nominal_scale"] = s * (rx + ry) / 2
        # Silhouette alpha of the whole picture, so tiles of a 2x2 object meet without seams.
        alpha_pic = smooth_alpha(pic >= 0)
        for fr in cell["frames"]:
            own = gd.sprite(fr["sheet"], fr["index"])
            h = own.shape[0]
            v, u = np.mgrid[0:h * SCALE, 0:TILE_W * SCALE].astype(np.float32)
            u, v = (u + 0.5) / SCALE, (v + 0.5) / SCALE
            px, py = fr["sx"] * u + fr["tx"], fr.get("sy", 1) * v + fr["ty"]
            rgb = sample(art, fit["x0"] + fit["kx"] * px, fit["y0"] + fit["ky"] * py, fit["kx"] / SCALE)
            # alpha: from the picture where this tile is the picture (unmirrored, inside it), else its own
            whole = float(fr["tx"]).is_integer() and float(fr["ty"]).is_integer()
            if whole and fr["sx"] == 1 and fr.get("sy", 1) == 1 and int(fr["ty"]) + h <= pic.shape[0] and np.array_equal(pic[int(fr["ty"]):int(fr["ty"]) + h, int(fr["tx"]):int(fr["tx"]) + TILE_W] >= 0, own >= 0):
                ty, tx = int(fr["ty"]), int(fr["tx"])
                alpha = alpha_pic[ty * SCALE:(ty + h) * SCALE, tx * SCALE:(tx + TILE_W) * SCALE]
            else:
                alpha = smooth_alpha(own >= 0)
            rgb = bleed(np.clip(rgb, 0, 1), alpha)
            rgba = np.dstack([rgb * 255, alpha * 255]).round().astype(np.uint8)
            out.append({"sheet": fr["sheet"], "index": fr["index"], "rgba": rgba, "fit": fit, "input": sheet["name"],
                        "cell": [cell["row"], cell["col"]], "mirrored": fr["sx"] < 0, "shared": fr["index"] != a["index"] and fr["sx"] > 0 and cell["art"]["size"] == 1})
    return out


PAD = 8  # texels around each atlas frame (D42 asks ~8 for mipmaps), filled by extending its edge so 2x2 tiles meet cleanly


def pack(frames: list[dict], width: int = 1024) -> tuple[np.ndarray, dict]:
    """Shelf-pack frames (tallest first) into one RGBA atlas; returns it and {index: {x, y, w, h}}."""
    order = sorted(frames, key=lambda f: (-f["rgba"].shape[0], f["index"]))
    x = y = shelf = 0
    places = {}
    for f in order:
        h, w = f["rgba"].shape[:2]
        if x + w + 2 * PAD > width:
            x, y, shelf = 0, y + shelf, 0
        places[f["index"]] = (x + PAD, y + PAD)
        x += w + 2 * PAD
        shelf = max(shelf, h + 2 * PAD)
    H = y + shelf
    H = 1 << max(0, (H - 1).bit_length()) if H > 0 else 1  # power of two height, for old GPUs' mipmaps
    atlas = np.zeros((H, width, 4), np.uint8)
    rects = {}
    for f in order:
        h, w = f["rgba"].shape[:2]
        fx, fy = places[f["index"]]
        padded = np.pad(f["rgba"], ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
        atlas[fy - PAD:fy + h + PAD, fx - PAD:fx + w + PAD] = padded
        rects[str(f["index"])] = {"x": fx, "y": fy, "w": w, "h": h}
    return atlas, rects


def sheet_file(sheet_id: str) -> str:
    """'tyrian.shp#7' -> 'tyrian-shp-7.webp' ('#' can't be in a URL path)."""
    return sheet_id.replace(".", "-").replace("#", "-") + ".webp"


def dump_manifest(m: dict) -> str:
    """The atlas manifest as JSON, one frame per line."""
    lines = ["{", f'  "scale": {m["scale"]},', '  "sheets": {']
    sheets = list(m["sheets"].items())
    for i, (sid, sh) in enumerate(sheets):
        lines.append(f'    {json.dumps(sid)}: {{ "image": {json.dumps(sh["image"])}, "frames": {{')
        frames = list(sh["frames"].items())
        for j, (k, r) in enumerate(frames):
            lines.append(f'      {json.dumps(k)}: {json.dumps(r)}' + ("," if j < len(frames) - 1 else ""))
        lines.append("    } }" + ("," if i < len(sheets) - 1 else ""))
    lines += ["  }", "}", ""]
    return "\n".join(lines)


def cut(gd: GameData, inputs: dict, results: Path, out: Path, palette: int, check: Path | None) -> dict:
    frames: dict[tuple[str, int], dict] = {}
    report = []
    for sheet in inputs["sheets"]:
        art = load_result(results, sheet["name"])
        if art is None:
            print(f"  {sheet['name']}: no result image, skipped")
            continue
        got = cut_sheet(gd, sheet, art, palette)
        for f in got:
            frames[(f["sheet"], f["index"])] = f  # a later sheet overrides an earlier one
        scores = [f["fit"]["score"] for f in got if not f["mirrored"]] or [0.0]
        print(f"  {sheet['name']}: {len(got)} frames, fit score min {min(scores):.2f} mean {np.mean(scores):.2f}")
        report.extend(got)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"scale": SCALE, "sheets": {}}
    for sid in sorted({k[0] for k in frames}):
        atlas, rects = pack([f for k, f in frames.items() if k[0] == sid])
        name = sheet_file(sid)
        Image.fromarray(atlas, "RGBA").save(out / name, "WEBP", quality=92, alpha_quality=100, method=6, exact=True)
        manifest["sheets"][sid] = {"image": name, "frames": dict(sorted(rects.items(), key=lambda kv: int(kv[0])))}
        print(f"  {out / name}: {len(rects)} frames, {atlas.shape[1]}x{atlas.shape[0]}")
    (out / "manifest.json").write_text(dump_manifest(manifest))
    if check:
        contact_sheet(gd, sorted(frames.values(), key=lambda f: (f["sheet"], f["index"])), palette, check)
    return manifest


def contact_sheet(gd: GameData, frames: list[dict], palette: int, path: Path, cols: int = 6) -> None:
    """original (nearest, 8x) | remastered, for every frame, on a checker; label under each pair."""
    from PIL import ImageDraw

    cw, chh = 2 * TILE_W * SCALE + 24, max(f["rgba"].shape[0] for f in frames) + 22
    rows = math.ceil(len(frames) / cols)
    img = Image.new("RGB", (cols * cw, rows * chh), (16, 16, 20))
    yy, xx = np.mgrid[0:chh, 0:TILE_W * SCALE]
    for i, f in enumerate(frames):
        r, c = divmod(i, cols)
        x0, y0 = c * cw + 4, r * chh + 2
        own = gd.sprite(f["sheet"], f["index"])
        orig = np.kron(gd.rgba(own, palette), np.ones((SCALE, SCALE, 1), np.uint8))
        for j, im in enumerate((orig, f["rgba"])):
            h = im.shape[0]
            chk = np.where(((xx[:h] // 8 + yy[:h] // 8) % 2)[..., None] == 1, 52, 36).astype(np.float32) * np.ones(3)
            a = im[..., 3:4].astype(np.float32) / 255
            comp = (im[..., :3] * a + chk * (1 - a)).astype(np.uint8)
            img.paste(Image.fromarray(comp), (x0 + j * (TILE_W * SCALE + 8), y0))
        ImageDraw.Draw(img).text((x0, y0 + f["rgba"].shape[0] + 2),
                                 f"{f['sheet'][7:]}:{f['index']} {f['input']}{' (mirror)' if f['mirrored'] else ' (shared)' if f.get('shared') else ''} fit {f['fit']['score']:.2f}",
                                 fill=(230, 230, 120))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"  check: {path}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=ROOT / "data", help="the Tyrian 2.1 data (default data/)")
    ap.add_argument("--palette", type=int, default=LEVEL1_PALETTE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheets", help="make the Gemini input sheets and their manifest")
    s.add_argument("--inventory", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("cut", help="cut Gemini's results into atlases")
    c.add_argument("--inputs", type=Path, required=True, help="the input sheets' manifest.json")
    c.add_argument("--results", type=Path, required=True, help="folder of <input sheet name>.png|jpg")
    c.add_argument("--out", type=Path, default=ROOT / "public" / "art" / "sprites")
    c.add_argument("--check", type=Path, help="also write a contact sheet here: original | remastered per frame")
    args = ap.parse_args(argv)
    gd = GameData(args.data)
    if args.cmd == "sheets":
        m = build_sheets(gd, json.loads(args.inventory.read_text()), args.out)
        for sh in m["sheets"]:
            print(f"  {args.out / sh['image']}: {len(sh['cells'])} cells, {sh['grid']['rows']}x{sh['grid']['cols']}, {sh['scale']}x")
    else:
        cut(gd, json.loads(args.inputs.read_text()), args.results, args.out, args.palette, args.check)


if __name__ == "__main__":
    main()
