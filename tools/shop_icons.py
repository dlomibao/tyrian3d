"""Remastered shop icons: Gemini paints sheets of the item screen's pictures, cut back per icon (DECISIONS.md D210).

The item screen draws each item's picture as JE_drawItem does: a 24x28 block of four 12x14 sprites
(index, +1, +19, +20) from newsh1.shp (weapons, shields, generators, sidekicks: itemGraphic) or from
tyrian.shp's ship sheet (tyrian.shp#8, shipGraphic), in the item screen's palette (0). This tool makes
Gemini input sheets of those pictures and cuts Gemini's answers back into one atlas of remastered
icons that src/app/shopIcons.ts draws in their place.

    NODE_OPTIONS= node tools/shop-icons-inventory.mjs INV.json
        Every distinct icon across episodes 1-4 and the items that show it (61 in Tyrian 2.1).

    python tools/shop_icons.py sheets --inventory INV.json --out DIR
        DIR/<sheet>.png (each icon scaled up nearest-neighbour SHEET_PX x, centred in a 256 px cell, on
        flat neutral grey: half of the icons' pixels are their near-black outline and drop shadow, which
        black would hide), DIR/<sheet>.prompt.txt (naming every icon's object, row by row) and
        DIR/manifest.json (where each icon sits). Derived from the game data, so keep them out of git (D3).

    python tools/shop_icons.py cut --inputs DIR/manifest.json --results RESULTS [--out public/art/shop] [--check PNG]
        RESULTS/<sheet>.png|jpg|webp is Gemini's answer (any size, same aspect). Each cell is registered
        onto its icon by zero-mean normalised cross-correlation (NCC) of luminance against the icon as it
        sits in the input (scale 0.92-1.08, aspect 0.97-1.03, shift up to a fifth of a cell: Gemini keeps a sheet's geometry
        within a few percent, and a wider search lets an added part (a handle, a glow) pull the fit off); the icon
        is resampled from the answer at SCALE texels per original pixel with the original silhouette,
        upscaled smoothly, as alpha (flat_art.smooth_alpha: the outline the item screen draws stays the
        original's); colour under zero alpha is bled from the nearest visible texel. A later sheet's
        icon replaces an earlier one's (retries). Writes the atlas (WebP) and manifest.json:
            { "scale": 6, "image": "icons.webp", "icons": { "newsh1.shp:7": { "x", "y", "w", "h" } } }
        keyed "<sheet id>:<first sprite index>" (a frame is 24x28 x scale), plus cut-report.json with
        each icon's NCC and colour error, and with --check a contact sheet original | remastered.
        --keep reuses committed icons whose answers aren't in RESULTS (cut a retry on its own).

    python tools/shop_icons.py models [--server URL] [--inventory INV.json] [--check PNG]
        (D226) Re-renders every picture the game draws as a 3D model (the player ships: the shop draws
        blit_sprite2x2 of shipGraphic, which the renderer replaces with the ship's model) from the
        models in this checkout, through the game's renderer (?debug=shopicons, captured with
        tools/cdpshot.mjs; a dev server is started on a free port 5220-5299 unless --server), cuts
        each onto its original silhouette as `cut` does, and writes models.webp + models.json beside
        the painted atlas; src/app/shopIcons.ts draws them over the paintings. Prints each icon's
        fit (IoU of the render with its ink against the sprite, the model's own IoU against the
        sprite's inner mask (D74), NCC, colour error); --check writes original | painted | render
        and models-report.json. Re-run whenever a ship model changes.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flat_art import GameData, bleed, load_result, sample, smooth_alpha  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SHOP_PALETTE = 0  # the item screen's palette (shop.ts SHOP_PALETTE: JE_loadPic 1 -> pcxpal[0])
ICON_W, ICON_H = 24, 28
SCALE = 6  # atlas texels per original pixel: 144x168 per icon; the menus show icons ~38 CSS px wide
CELL = 256  # input cell, px
SHEET_PX = 8  # input px per original pixel: 192x224 in a 256 cell
BACKGROUND = (118, 118, 118)  # flat neutral grey
PAD = 8
PRIOR = 0.6  # registration: NCC given up per unit of scale away from the sheet's (see register)
SHIFT_PRIOR = 0.01  # and per original pixel the icon's centre moves from where the sheet put it

# What each icon depicts (art rule: name the object, not the look, D187), from the pictures themselves
# and the items' names. "<sheet>:<index>".
DESCRIBE = {
    "newsh1.shp:3": "a cannon that fires molten globs: a lumpy glowing orange-and-yellow plasma mass",
    "newsh1.shp:7": "a three-barrelled grey pulse cannon on a tan metal mounting bracket",
    "newsh1.shp:9": "a slim grey missile pointing up with an orange band and small tail fins",
    "newsh1.shp:11": "a heavy grey missile pointing up with banded stripes and tail fins",
    "newsh1.shp:41": "a sonic wave emitter: stacked red-orange glowing dish rings on top of grey machinery",
    "newsh1.shp:47": "a laser: twin grey canisters with blue glass windows, side by side",
    "newsh1.shp:49": "a Zica laser: a grey tower with a glowing red-orange core in its centre",
    "newsh1.shp:53": "guided micro bombs: two small grey pods with glowing red tips side by side on a grey rack",
    "newsh1.shp:55": "a mega cannon: a wide grey block with a glowing red grille on top",
    "newsh1.shp:77": "a Protron Z gun: an arched grey pod with a blue glass strip down its centre",
    "newsh1.shp:79": "a wild ball gun: an arched grey pod with a red-orange glowing strip down its centre",
    "newsh1.shp:81": "a Protron gun: an arched grey pod with a segmented red-orange strip down its centre",
    "newsh1.shp:85": "a starburst gun: a grey spiked emitter with prongs fanning out like a star",
    "newsh1.shp:87": "a multi-cannon: a grey gun with several barrels fanned out sideways",
    "newsh1.shp:91": "a Vulcan cannon: a ribbed grey rotary-barrel cylinder with brass bands",
    "newsh1.shp:93": "a rear Vulcan cannon: a ribbed grey rotary-barrel cylinder with red accents and small side fins",
    "newsh1.shp:117": "a lightning cannon: a blue-grey electric coil with a curved blue arc on top",
    "newsh1.shp:119": "a fireball gun: two grey curved prongs arching round a glowing orange core",
    "newsh1.shp:127": "a hot dog launcher: a hot dog in its bun lying on a blue oval dish, with the red words HOT above and DOG below, kept as lettering",
    "newsh1.shp:199": "a guided bomb: a glossy dark blue metal sphere",
    "newsh1.shp:207": "a mega pulse: a black metal sphere with a glowing red-orange spot",
    "newsh1.shp:237": "a scatter wave gun: a grey armoured block with red-orange stripes and a small turret on top",
    # sidekicks
    "newsh1.shp:1": "a single-shot option pod: a small grey gun turret on a tan metal bracket",
    "newsh1.shp:5": "a dual-shot option pod: twin grey gun turrets on a tan metal bracket",
    "newsh1.shp:13": "a mega missile launcher: a grey missile in a tan launch cradle with an orange glow at its base",
    "newsh1.shp:51": "a mini-missile pod: a small grey pod with a glowing red-orange tip",
    "newsh1.shp:89": "a Vulcan shot option pod: a ribbed grey rotary gun cylinder",
    "newsh1.shp:115": "a Zica flamethrower: grey fuel canisters and nozzle with orange glowing parts",
    "newsh1.shp:169": "a plasma storm charge: a bright four-pointed orange-and-yellow star flare",
    "newsh1.shp:193": "a charge cannon: a grey cylindrical cannon with a glowing red ring",
    "newsh1.shp:195": "a phoenix device: grey machinery with small orange flame lights",
    "newsh1.shp:197": "a post-it mine: a round grey mine with a red light in its middle",
    "newsh1.shp:201": "an atom bomb: a bronze sphere with swirled metal bands",
    "newsh1.shp:229": "the companion ship Gerund: a small grey escort craft with red curved side arms",
    "newsh1.shp:231": "the companion ship Quicksilver: a small grey escort craft with red stripes",
    "newsh1.shp:233": "a Protron cannon pod: a grey turret with red-orange bands and curved side arms",
    "newsh1.shp:235": "a front-blaster pod: a wide grey armoured block with red stripes",
    "newsh1.shp:239": "the companion ship Warfly: a slim grey escort craft with red-orange stripes",
    "newsh1.shp:283": "a micro bomb: a glossy blue metal sphere with a red band",
    # ships (tyrian.shp#8)
    "tyrian.shp#8:1": "the Nort Ship's picture: two small stacked green-and-tan cylindrical pods",
    "tyrian.shp#8:81": "the Silver Ship: a silver fighter spacecraft seen from above, nose up, red bands at its tail",
    "tyrian.shp#8:119": "the SuperCarrot: a carrot-shaped orange fighter seen from above, nose up, green leafy fins at its tail",
    "tyrian.shp#8:157": "the Gencore Phoenix: a grey fighter spacecraft seen from above, nose up, with swept wings",
    "tyrian.shp#8:195": "the MicroCorp Stalker: a grey fighter spacecraft seen from above, nose up, with swept wings and a red engine",
    "tyrian.shp#8:233": "the USP Talon: a tan-bronze delta-wing fighter seen from above, nose up",
    "tyrian.shp#8:271": "the U-Ship: a dark U-shaped frame round a small bronze dome, seen from above",
    # shields
    "newsh1.shp:129": "a structural integrity field generator: a blue glass dome over a grey machine base",
    "newsh1.shp:131": "an advanced integrity field generator: a bronze dome over a grey machine base",
    "newsh1.shp:153": "an energy shield: a plain grey metal heater shield with a central ridge",
    "newsh1.shp:155": "an energy shield: a grey metal heater shield with red-orange glowing panels",
    "newsh1.shp:157": "an energy shield: a grey metal heater shield with red-orange glowing panels",
    "newsh1.shp:159": "an energy shield: a grey metal heater shield with red-orange glowing panels",
    "newsh1.shp:161": "a heavy energy shield: a grey metal heater shield with green panels",
    "newsh1.shp:163": "a heavy energy shield: a grey metal heater shield with green panels",
    "newsh1.shp:165": "a heavy energy shield: a grey metal heater shield with green panels",
    # generators
    "newsh1.shp:241": "a power generator: a compact grey machine with blue glass tubes",
    "newsh1.shp:243": "a power generator: a grey machine with blue glass tubes",
    "newsh1.shp:245": "a fusion power generator: a grey machine with blue glass and pipes",
    "newsh1.shp:267": "a fusion power generator: a grey machine with blue glass and pipes",
    "newsh1.shp:269": "a power generator: a grey machine with blue glass tubes",
    "newsh1.shp:271": "a pulse-wave power generator: a grey machine with red-orange glowing parts",
}

# Retries (`sheets --retry NAME`): icons the first answers got wrong, sent again on a sheet of their
# own with wording aimed at what went wrong. A retry sheet is appended to the manifest, so `cut`
# takes its icons over the first answers'.
RETRIES = {
    "retry-1": {
        # Painted larger, as a soft glow with sparks and no outline (NCC 0.24).
        "newsh1.shp:169": "a plasma storm charge: a four-pointed orange-and-yellow star with a white-hot centre, hard-edged like a "
                          "solid metal-cut star, exactly as big as the original with its dark outline round it; no glow, haze or sparks beyond its outline",
        # Painted bright cyan glass; the sprite's dome is dark steel blue (colour error 60).
        "newsh1.shp:129": "a structural integrity field generator: a dark steel-blue glass dome (deep navy blue, as dark as in the "
                          "original, not bright cyan) over a grey machine base",
        # A dark outline, drop shadow and a joining pipe added; the sprite has neither (the fit slid off).
        "tyrian.shp#8:1": "the Nort Ship's picture: two separate small cylindrical pods one above the other, each brown-tan metal "
                          "end caps with a green band round the middle; nothing joins them; no dark outline and no drop shadow, as in the original",
    },
}

# The sheets: which icons (by the kind of item that shows them) and the shop they come from.
SHEETS = [
    ("weapons", "the front and rear guns", lambda kinds: "weapon" in kinds),
    ("sidekicks-ships", "the sidekicks (option pods, companion ships, bombs and missiles) and the player's ships",
     lambda kinds: "weapon" not in kinds and ("sidekick" in kinds or "ship" in kinds)),
    ("shields-generators", "the shields and power generators", lambda kinds: kinds <= {"shield", "generator"}),
]


def composite(gd: GameData, sheet: str, index: int) -> np.ndarray:
    """JE_drawItem's picture as itemIcon draws it: the four sprites in order, each whole, clipped to 24x28."""
    out = np.full((ICON_H, ICON_W), -1, np.int16)
    for off, ox, oy in ((0, 0, 0), (1, 12, 0), (19, 0, 14), (20, 12, 14)):
        s = gd.sprite(sheet, index + off)
        h = min(s.shape[0], ICON_H - oy)
        if h <= 0:
            continue
        sub, src = out[oy:oy + h, ox:ox + 12], s[:h]
        sub[src >= 0] = src[src >= 0]
    return out


def prompt_for(title: str, rows: int, cols: int, cells: list[dict]) -> str:
    listing = []
    for r in range(rows):
        row = [c for c in cells if c["row"] == r]
        if row:
            listing.append(f"Row {r + 1}: " + "; ".join(f"({c['col'] + 1}) {c['names']}: {c['describe']}" for c in row) + ".")
    n = len(cells)
    empty = rows * cols - n
    return (
        f"This image is a {rows}x{cols} grid of {n} pixel-art item icons from the shop of a 1990s top-down space shooter "
        f"(Tyrian): the pictures of {title}, each centred in its own square cell on a flat neutral grey background"
        + (f" ({'the last cell is' if empty == 1 else f'the last {empty} cells are'} empty grey)" if empty else "") + ". "
        "Repaint every icon as a remastered, high-resolution, hand-painted game-UI item icon: crisp clean edges, fine "
        "mechanical detail (panel lines, rivets, vents, glass), brushed gunmetal with a soft specular sheen, glowing parts "
        "lit from within, one consistent style across the whole set. Keep each icon exactly where it is and exactly the same "
        "size, with the same silhouette, the same parts in the same places, the same colours (dark gunmetal greys, tan and "
        "bronze metal, red-orange glows, blue glass, green panels where shown) and its dark outline and drop shadow towards "
        "the lower right. Don't add parts, text, labels, numbers, frames or borders; don't move, rotate or resize anything; "
        "keep the background the same flat neutral grey. Paint it, don't copy the square pixels. "
        "The icons, row by row, left to right: " + " ".join(listing)
    )


def build_sheets(gd: GameData, inventory: list[dict], out: Path, retry: str | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"note": "cell rect = [x, y, w, h] input px; the icon's 24x28 picture sits at (x, y), SHEET_PX input px per pixel",
                "palette": SHOP_PALETTE, "sheet_px": SHEET_PX, "sheets": []}
    groups = SHEETS
    describe = DESCRIBE
    if retry:
        manifest = json.loads((out / "manifest.json").read_text())
        manifest["sheets"] = [sh for sh in manifest["sheets"] if sh["name"] != retry]
        keys = set(RETRIES[retry])
        groups = [(retry, "a few of the shop's items", lambda kinds, e=None: True)]
        describe = {**DESCRIBE, **RETRIES[retry]}
        inventory = [e for e in inventory if e["key"] in keys]
    taken: set[str] = set()
    for name, title, pick in groups:
        icons = [e for e in inventory if e["key"] not in taken and pick({u["kind"] for u in e["uses"]})]
        taken.update(e["key"] for e in icons)
        if not icons:
            continue
        cols = math.ceil(math.sqrt(len(icons)))
        rows = math.ceil(len(icons) / cols)
        rows = cols = max(rows, cols)  # square sheets: 1:1 is an aspect Gemini keeps
        img = np.zeros((rows * CELL, cols * CELL, 3), np.uint8)
        img[:] = BACKGROUND
        cells = []
        for i, e in enumerate(icons):
            r, c = divmod(i, cols)
            pic = composite(gd, e["sheet"], e["index"])
            rgba = gd.rgba(pic, SHOP_PALETTE)
            x = c * CELL + (CELL - ICON_W * SHEET_PX) // 2
            y = r * CELL + (CELL - ICON_H * SHEET_PX) // 2
            big = np.kron(rgba, np.ones((SHEET_PX, SHEET_PX, 1), np.uint8))
            m = big[..., 3] > 0
            img[y:y + ICON_H * SHEET_PX, x:x + ICON_W * SHEET_PX][m] = big[..., :3][m]
            names = list(dict.fromkeys(u["name"].split(" Ammo")[0] for u in e["uses"]))[:3]  # the first items (by id) that show it
            cells.append({"key": e["key"], "sheet": e["sheet"], "index": e["index"], "row": r, "col": c,
                          "rect": [c * CELL, r * CELL, CELL, CELL], "x": x, "y": y,
                          "names": " / ".join(names), "describe": describe.get(e["key"], "an item")})
        Image.fromarray(img).save(out / f"{name}.png")
        prompt = prompt_for(title, rows, cols, cells)
        (out / f"{name}.prompt.txt").write_text(prompt + "\n")
        manifest["sheets"].append({"name": name, "image": f"{name}.png", "size": [cols * CELL, rows * CELL],
                                   "grid": {"rows": rows, "cols": cols, "cell": CELL}, "prompt": prompt, "cells": cells})
        print(f"  {out / name}.png: {len(cells)} icons, {rows}x{cols}, prompt {len(prompt)} chars")
    missing = [e["key"] for e in inventory if e["key"] not in taken and not retry]
    if missing:
        print(f"  not on any sheet: {missing}")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


# --- Registration -----------------------------------------------------------------------------------


def gray(a: np.ndarray) -> np.ndarray:
    return a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11


def resize_f(a: np.ndarray, w: int, h: int) -> np.ndarray:
    return np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((w, h), Image.BILINEAR))


def ncc_map(I: np.ndarray, T: np.ndarray) -> np.ndarray | None:
    """Zero-mean NCC of template T at every valid position (y, x) of its top-left in I."""
    from scipy.signal import fftconvolve

    th, tw = T.shape
    if I.shape[0] < th or I.shape[1] < tw:
        return None
    Tz = T - T.mean()
    tn = math.sqrt(float((Tz * Tz).sum())) or 1.0
    num = fftconvolve(I, Tz[::-1, ::-1], mode="valid")
    c1 = np.cumsum(np.cumsum(np.pad(I, ((1, 0), (1, 0))), 0), 1)
    c2 = np.cumsum(np.cumsum(np.pad(I * I, ((1, 0), (1, 0))), 0), 1)
    box = lambda c: c[th:, tw:] - c[:-th, tw:] - c[th:, :-tw] + c[:-th, :-tw]  # noqa: E731
    s1, s2 = box(c1), box(c2)
    var = np.maximum(s2 - s1 * s1 / (th * tw), 1e-6)
    return num / (np.sqrt(var) * tn)


def icon_on_background(gd: GameData, pic: np.ndarray, margin: int) -> np.ndarray:
    """The icon's RGB (0..1) on the sheet's grey, with `margin` px of grey round it."""
    rgba = gd.rgba(pic, SHOP_PALETTE).astype(np.float32) / 255
    bg = np.array(BACKGROUND, np.float32) / 255
    rgb = rgba[..., :3] * rgba[..., 3:] + bg * (1 - rgba[..., 3:])
    return np.pad(rgb, ((margin, margin), (margin, margin), (0, 0)), mode="constant", constant_values=0) + \
        np.pad(np.zeros(rgb.shape[:2] + (3,), np.float32), ((margin, margin), (margin, margin), (0, 0)), constant_values=1) * bg


def register(art: np.ndarray, ref: np.ndarray, margin: int, nominal: tuple[float, float, float], window: tuple[int, int, int, int],
             q: int = 3) -> dict:
    """Fit the icon (ref: its RGB with `margin` px of grey, 1 px per original pixel) onto the answer.
    nominal: (x0, y0, k) answer px of the icon's (0, 0) and answer px per original pixel. Searches
    scale 0.92-1.08 and aspect 0.97-1.03 inside window (answer px), at q px per original pixel.
    Returns x0, y0, kx, ky (answer px = x0 + kx * u) and the NCC score."""
    from scipy import ndimage

    x0n, y0n, kn = nominal
    wx0, wy0, wx1, wy1 = window
    f = q / kn  # work px per answer px
    # The window may reach past the answer's edges (an icon fills most of its cell): pad with grey.
    H, W = art.shape[:2]
    I = np.full((wy1 - wy0, wx1 - wx0), gray(np.array(BACKGROUND, np.float32) / 255), np.float32)
    sy0, sx0 = max(wy0, 0), max(wx0, 0)
    I[sy0 - wy0:min(wy1, H) - wy0, sx0 - wx0:min(wx1, W) - wx0] = gray(art[sy0:min(wy1, H), sx0:min(wx1, W)])
    I = ndimage.gaussian_filter(resize_f(I, int(round((wx1 - wx0) * f)), int(round((wy1 - wy0) * f))), q * 0.4)
    R = np.kron(gray(ref), np.ones((q, q), np.float32))
    best = {"score": -2.0}
    for s in np.arange(0.92, 1.0801, 0.01):
        for a in (0.97, 0.985, 1.0, 1.015, 1.03):
            sx, sy = s * math.sqrt(a), s / math.sqrt(a)
            tw, th = int(round(R.shape[1] * sx)), int(round(R.shape[0] * sy))
            T = ndimage.gaussian_filter(resize_f(R, tw, th), q * 0.4)
            ncc = ncc_map(I, T)
            if ncc is None:
                continue
            # Priors toward the sheet's own geometry, which Gemini keeps: 5% off in scale costs 0.03,
            # and each original pixel the icon's centre moves 0.01 (an icon of two identical pods, or
            # with a part added, otherwise matches as well one pod or a few pixels over).
            yy, xx = np.mgrid[0:ncc.shape[0], 0:ncc.shape[1]].astype(np.float32)
            cx = (x0n - wx0) * f - margin * q * sx + (R.shape[1] / 2) * (1 - sx)
            cy = (y0n - wy0) * f - margin * q * sy + (R.shape[0] / 2) * (1 - sy)
            adj = ncc - SHIFT_PRIOR * np.hypot(xx - cx, yy - cy) / q
            oy, ox = np.unravel_index(int(np.argmax(adj)), adj.shape)
            score = float(ncc[oy, ox])
            chosen = float(adj[oy, ox]) - PRIOR * (abs(sx - 1) + abs(sy - 1)) / 2
            if chosen > best.get("chosen", -2.0):
                kx, ky = tw / R.shape[1] * kn, th / R.shape[0] * kn
                best = {"score": score, "chosen": chosen, "kx": kx, "ky": ky,
                        "x0": wx0 + ox / f + margin * kx, "y0": wy0 + oy / f + margin * ky}
    best["shift"] = [best["x0"] - x0n, best["y0"] - y0n]
    best["scale"] = [best["kx"] / kn, best["ky"] / kn]
    return best


def cut_icon(gd: GameData, art: np.ndarray, sheet: dict, cell: dict) -> dict:
    H, W = art.shape[:2]
    rx, ry = W / sheet["size"][0], H / sheet["size"][1]
    k = SHEET_PX * (rx + ry) / 2
    pic = composite(gd, cell["sheet"], cell["index"])
    margin = 3
    ref = icon_on_background(gd, pic, margin)
    cx, cy, cw, ch = cell["rect"]
    g = CELL // 5  # search: up to a fifth of a cell past the cell's edges
    window = (int((cx - g) * rx), int((cy - g) * ry), int((cx + cw + g) * rx), int((cy + ch + g) * ry))
    fit = register(art, ref, margin, (cell["x"] * rx, cell["y"] * ry, k), window)
    v, u = np.mgrid[0:ICON_H * SCALE, 0:ICON_W * SCALE].astype(np.float32)
    u, v = (u + 0.5) / SCALE, (v + 0.5) / SCALE
    rgb = sample(art, fit["x0"] + fit["kx"] * u, fit["y0"] + fit["ky"] * v, fit["kx"] / SCALE)
    alpha = smooth_alpha(pic >= 0, SCALE, sigma=SCALE * 3 / 8)
    rgb = bleed(np.clip(rgb, 0, 1), alpha)
    # Colour check: the painting brought back to the original's pixels against the original, mean
    # absolute error (0..255) over the icon's pixels, and its mean colour shift.
    small = rgb.reshape(ICON_H, SCALE, ICON_W, SCALE, 3).mean((1, 3))
    orig = gd.rgba(pic, SHOP_PALETTE)[..., :3].astype(np.float32) / 255
    m = pic >= 0
    err = float(np.abs(small[m] - orig[m]).mean() * 255)
    shift = ((small[m] - orig[m]).mean(0) * 255).round(1).tolist()
    rgba = np.dstack([rgb * 255, alpha * 255]).round().astype(np.uint8)
    return {"key": cell["key"], "rgba": rgba, "fit": fit, "colour_mae": err, "colour_shift": shift, "input": sheet["name"],
            "names": cell["names"]}


def pack(icons: list[dict], cols: int) -> tuple[np.ndarray, dict]:
    fw, fh = ICON_W * SCALE + 2 * PAD, ICON_H * SCALE + 2 * PAD
    rows = math.ceil(len(icons) / cols)
    atlas = np.zeros((rows * fh, cols * fw, 4), np.uint8)
    rects = {}
    for i, ic in enumerate(sorted(icons, key=lambda e: (e["key"].split(":")[0], int(e["key"].split(":")[1])))):
        r, c = divmod(i, cols)
        x, y = c * fw, r * fh
        atlas[y:y + fh, x:x + fw] = np.pad(ic["rgba"], ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
        rects[ic["key"]] = {"x": x + PAD, "y": y + PAD, "w": ICON_W * SCALE, "h": ICON_H * SCALE}
    return atlas, rects


def committed_icons(out: Path) -> dict[str, np.ndarray]:
    """The icons in the atlas at `out` (manifest.json + its image), by key; {} if there is none."""
    if not (out / "manifest.json").exists():
        return {}
    old = json.loads((out / "manifest.json").read_text())
    img = np.asarray(Image.open(out / old["image"]).convert("RGBA"))
    return {key: img[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]].copy() for key, r in old["icons"].items()
            if r["w"] == ICON_W * SCALE and r["h"] == ICON_H * SCALE}


def write_atlas(icons: list[dict], out: Path, image: str = "icons.webp", manifest: str = "manifest.json", cols: int = 10) -> None:
    """Pack icons ({"key", "rgba"}) into out/<image> and out/<manifest>."""
    atlas, rects = pack(icons, cols=cols)
    Image.fromarray(atlas, "RGBA").save(out / image, "WEBP", quality=90, alpha_quality=100, method=6, exact=True)
    lines = ["{", f'  "scale": {SCALE},', f'  "image": "{image}",', '  "icons": {']
    items = list(rects.items())
    lines += [f"    {json.dumps(k)}: {json.dumps(r)}" + ("," if i < len(items) - 1 else "") for i, (k, r) in enumerate(items)]
    lines += ["  }", "}", ""]
    (out / manifest).write_text("\n".join(lines))
    print(f"  {out / image}: {len(rects)} icons, {atlas.shape[1]}x{atlas.shape[0]}, {(out / image).stat().st_size // 1024} KB")


def cut(gd: GameData, inputs: dict, results: Path, out: Path, check: Path | None, keep: bool) -> None:
    icons: dict[str, dict] = {}
    for sheet in inputs["sheets"]:
        art = load_result(results, sheet["name"])
        if art is None:
            print(f"  {sheet['name']}: no answer, skipped")
            continue
        got = [cut_icon(gd, art, sheet, c) for c in sheet["cells"]]
        for ic in got:
            icons[ic["key"]] = ic
        s = [ic["fit"]["score"] for ic in got]
        print(f"  {sheet['name']} ({art.shape[1]}x{art.shape[0]}): {len(got)} icons, NCC min {min(s):.3f} mean {np.mean(s):.3f}")
    out.mkdir(parents=True, exist_ok=True)
    if keep:
        for key, rgba in committed_icons(out).items():
            if key not in icons:
                icons[key] = {"key": key, "rgba": rgba, "fit": {"score": float("nan")},
                              "colour_mae": float("nan"), "colour_shift": [], "input": "kept", "names": key}
    write_atlas(list(icons.values()), out)
    report = [{"key": ic["key"], "names": ic["names"], "input": ic["input"], "ncc": round(ic["fit"]["score"], 4),
               "scale": [round(x, 3) for x in ic["fit"].get("scale", [])], "shift_px": [round(x, 1) for x in ic["fit"].get("shift", [])],
               "colour_mae": round(ic["colour_mae"], 1), "colour_shift": ic["colour_shift"]} for ic in sorted(icons.values(), key=lambda e: e["fit"]["score"])]
    if check:
        check.parent.mkdir(parents=True, exist_ok=True)
        (check.parent / "cut-report.json").write_text(json.dumps(report, indent=1))
        contact_sheet(gd, sorted(icons.values(), key=lambda e: (e["key"].split(":")[0], int(e["key"].split(":")[1]))), check)


def contact_sheet(gd: GameData, icons: list[dict], path: Path, cols: int = 6) -> None:
    """original (nearest, SCALE x) | remastered, per icon, on the shop's dark panel colour; label under each pair."""
    from PIL import ImageDraw

    w, h = ICON_W * SCALE, ICON_H * SCALE
    cw, chh = 2 * w + 24, h + 24
    rows = math.ceil(len(icons) / cols)
    img = Image.new("RGB", (cols * cw, rows * chh), (14, 18, 26))
    bg = np.array([22, 28, 40], np.float32)
    for i, ic in enumerate(icons):
        r, c = divmod(i, cols)
        x0, y0 = c * cw + 6, r * chh + 2
        sheet, index = ic["key"].rsplit(":", 1)
        orig = np.kron(gd.rgba(composite(gd, sheet, int(index)), SHOP_PALETTE), np.ones((SCALE, SCALE, 1), np.uint8))
        for j, im in enumerate((orig, ic["rgba"])):
            a = im[..., 3:4].astype(np.float32) / 255
            img.paste(Image.fromarray((im[..., :3] * a + bg * (1 - a)).astype(np.uint8)), (x0 + j * (w + 8), y0))
        ImageDraw.Draw(img).text((x0, y0 + h + 4), f"{ic['key'].replace('.shp', '')} NCC {ic['fit']['score']:.2f} dC {ic['colour_mae']:.0f}",
                                 fill=(230, 230, 120))
    img.save(path)
    print(f"  check: {path}")


# --- Model renders (D226) ---------------------------------------------------------------------------

INK = (16, 8, 0)  # the game's ink outline (outlineColor.ts INK_OUTLINE): under the silhouette where the render left a gap


def free_port(lo: int = 5220, hi: int = 5299) -> int:
    import socket

    for port in range(lo, hi + 1):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit(f"no free port in {lo}-{hi}")


def node_env() -> dict:
    import os

    return {**os.environ, "NODE_OPTIONS": ""}


# cdpshot's expression: the harness's result, once its module has loaded.
WAIT_RENDERS = "(async () => { while (!window.tyrianShopIcons) await new Promise((r) => setTimeout(r, 200)); return await window.tyrianShopIcons.ready; })()"


def capture_renders(data: Path, keys: list[str], server: str | None) -> dict:
    """The model renders of `keys` from ?debug=shopicons (src/debug/shopIconsHarness.ts), captured with
    tools/cdpshot.mjs from `server`, or from a dev server started (and stopped) here on a free port."""
    import base64
    import io
    import subprocess
    import time
    import urllib.parse
    import urllib.request

    proc = None
    if server is None:
        port = free_port()
        server = f"http://localhost:{port}/"
        proc = subprocess.Popen(["npx", "vite", "--port", str(port), "--strictPort"], cwd=ROOT, env={**node_env(), "TYRIAN_DATA": str(data.resolve())},
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(120):
            try:
                urllib.request.urlopen(server, timeout=2)
                break
            except OSError:
                time.sleep(0.5)
        else:
            proc.kill()
            raise SystemExit(f"dev server on {server} didn't start")
    try:
        url = server.rstrip("/") + "/?debug=shopicons&keys=" + urllib.parse.quote(",".join(keys), safe=",:")
        with __import__("tempfile").TemporaryDirectory() as tmp:
            # stdout to a file: node's writes to a pipe can be cut short by cdpshot's process.exit.
            with open(Path(tmp) / "out.txt", "w") as so:
                run = subprocess.run(["node", str(ROOT / "tools" / "cdpshot.mjs"), url, str(Path(tmp) / "shot.png"), "2000", "1280", "800",
                                      WAIT_RENDERS], cwd=ROOT, env=node_env(), stdout=so, stderr=subprocess.PIPE, text=True, timeout=600)
            stdout = (Path(tmp) / "out.txt").read_text()
    finally:
        if proc:
            proc.terminate()
            proc.wait(10)
    lines = [ln for ln in stdout.splitlines() if ln.startswith("{")]
    if run.returncode != 0 or not lines:
        raise SystemExit(f"capture failed ({url}):\n{run.stderr[-2000:]}\n{stdout[-2000:]}")
    renders = json.loads(lines[-1])
    if "png" not in renders:
        raise SystemExit(f"capture failed ({url}): {lines[-1][:2000]}")
    renders["image"] = np.asarray(Image.open(io.BytesIO(base64.b64decode(renders.pop("png").split(",", 1)[1]))).convert("RGBA"))
    return renders


def cut_render(gd: GameData, key: str, renders: dict) -> dict:
    """One render cut back onto its original silhouette, as D210 cuts a painting: SCALE texels per
    original pixel, the original mask upscaled smoothly as alpha; the render over the ink where it
    leaves a gap inside the silhouette. With its fit to the original: IoU of the render's own
    coverage against the sprite's mask, D210's NCC (register, at the render's own placement) and
    colour error."""
    px, margin = renders["px"], renders["margin"]
    r = renders["icons"][key]
    cw, ch = renders["cell"]
    crop = renders["image"][r["y"]:r["y"] + ch, r["x"]:r["x"] + cw].astype(np.float32) / 255
    # Down to SCALE texels per pixel by area (premultiplied), margin kept.
    f = px / SCALE
    if abs(f - round(f)) > 1e-6 or f < 1:
        raise SystemExit(f"render px {px} must be a multiple of {SCALE}")
    f = int(round(f))
    pre = np.dstack([crop[..., :3] * crop[..., 3:], crop[..., 3:]])
    small = pre.reshape(ch // f, f, cw // f, f, 4).mean((1, 3))
    m = margin * SCALE
    icon = small[m:m + ICON_H * SCALE, m:m + ICON_W * SCALE]
    cover = icon[..., 3]
    ink = np.array(INK, np.float32) / 255
    rgb = icon[..., :3] + ink * (1 - cover[..., None])
    sheet, index = key.rsplit(":", 1)
    pic = composite(gd, sheet, int(index))
    mask = pic >= 0
    alpha = smooth_alpha(mask, SCALE, sigma=SCALE * 3 / 8)
    rgb = bleed(np.clip(rgb, 0, 1), alpha)
    rgba = np.dstack([rgb * 255, alpha * 255]).round().astype(np.uint8)
    # Fit. IoU: the render's coverage, ink included (> half), against the sprite's pixels, at SCALE.
    big = np.kron(mask, np.ones((SCALE, SCALE), bool))
    covered = cover > 0.5
    iou = float((covered & big).sum() / max(1, (covered | big).sum()))
    # The model's own fit (D74, tools/sprite_mask.py): the render without its ink on the sprite's grid
    # (a pixel covered when at least half of it is) against the inner mask, thin parts' border free.
    import sprite_mask

    bare = renders["image"][r["bareY"] + margin * px:r["bareY"] + (margin + ICON_H) * px, r["x"] + margin * px:r["x"] + (margin + ICON_W) * px, 3]
    grid = bare.reshape(ICON_H, px, ICON_W, px).astype(np.float32).mean((1, 3)) / 255 >= 0.5
    pal = gd.palettes[SHOP_PALETTE]
    mm = {k: np.array(v, bool) for k, v in sprite_mask.masks(pic.tolist(), {i: tuple(int(c) for c in pal[i]) for i in range(256)}).items()}
    keep = ~mm["free"]
    rule_iou = float((grid & mm["inner"] & keep).sum() / max(1, ((grid | mm["inner"]) & keep).sum()))
    # NCC: D210's registration, the render over the sheets' grey as the answer, nominally in place.
    bg = np.array(BACKGROUND, np.float32) / 255
    answer = small[..., :3] + bg * (1 - small[..., 3:])
    margin_ref = 3
    ref = icon_on_background(gd, pic, margin_ref)
    window = (m - SCALE * 5, m - SCALE * 5, m + (ICON_W + 5) * SCALE, m + (ICON_H + 5) * SCALE)
    fit = register(answer, ref, margin_ref, (m, m, SCALE), window)
    # The render's placement is exact (the sprite's own spot on screen): its NCC in place, as register
    # scores (q = 3 px per original pixel, the same blur), beside the best fit's.
    from scipy import ndimage

    q = 3
    o = m - margin_ref * SCALE
    A = answer[o:o + ref.shape[0] * SCALE, o:o + ref.shape[1] * SCALE]
    I = ndimage.gaussian_filter(resize_f(gray(A), ref.shape[1] * q, ref.shape[0] * q), q * 0.4)
    T = ndimage.gaussian_filter(np.kron(gray(ref), np.ones((q, q), np.float32)), q * 0.4)
    Iz, Tz = I - I.mean(), T - T.mean()
    fit["in_place"] = float((Iz * Tz).sum() / (math.sqrt(float((Iz * Iz).sum()) * float((Tz * Tz).sum())) or 1.0))
    # Colour: the icon averaged back to the original's pixels against the original (0..255).
    back = rgb.reshape(ICON_H, SCALE, ICON_W, SCALE, 3).mean((1, 3))
    orig = gd.rgba(pic, SHOP_PALETTE)[..., :3].astype(np.float32) / 255
    err = float(np.abs(back[mask] - orig[mask]).mean() * 255)
    shift = ((back[mask] - orig[mask]).mean(0) * 255).round(1).tolist()
    return {"key": key, "rgba": rgba, "fit": fit, "iou": iou, "rule_iou": rule_iou, "colour_mae": err, "colour_shift": shift, "input": r["model"], "names": r["model"]}


def models(gd: GameData, data: Path, inventory: list[dict], out: Path, server: str | None, check: Path | None) -> None:
    keys = [e["key"] for e in inventory]
    renders = capture_renders(data, keys, server)
    names = {e["key"]: " / ".join(dict.fromkeys(u["name"] for u in e["uses"])) for e in inventory}
    print(f"  {len(renders['icons'])} of {len(keys)} pictures are drawn as models; the rest keep their icons")
    before = committed_icons(out)  # the painted icons (D210), shown under the renders
    got = [cut_render(gd, key, renders) for key in renders["icons"]]
    out.mkdir(parents=True, exist_ok=True)
    # Their own atlas, made whole from this run's renders: the painted atlas is never re-encoded, and
    # an icon whose model goes away falls back to its painting.
    write_atlas(got, out, "models.webp", "models.json", cols=4)
    report = [{"key": ic["key"], "items": names.get(ic["key"], ""), "model": ic["input"], "iou": round(ic["iou"], 4), "rule_iou": round(ic["rule_iou"], 4), "ncc": round(ic["fit"]["in_place"], 4),
               "ncc_best_fit": round(ic["fit"]["score"], 4),
               "scale": [round(x, 3) for x in ic["fit"]["scale"]], "shift_px": [round(x, 2) for x in ic["fit"]["shift"]],
               "colour_mae": round(ic["colour_mae"], 1), "colour_shift": ic["colour_shift"]} for ic in got]
    for e in report:
        print(f"  {e['key']:<18} {e['model']:<32} IoU {e['iou']:.3f} (model vs inner mask {e['rule_iou']:.3f})  NCC {e['ncc']:.3f} (best fit {e['ncc_best_fit']:.3f})  dC {e['colour_mae']:.0f}  ({e['items'][:60]})")
    if check:
        check.parent.mkdir(parents=True, exist_ok=True)
        (check.parent / "models-report.json").write_text(json.dumps(report, indent=1))
        contact_models(gd, got, before, check)


def contact_models(gd: GameData, got: list[dict], before: dict[str, np.ndarray], path: Path) -> None:
    """original (nearest) | the icon before | the render's icon, per model icon, on the shop's panel colour."""
    from PIL import ImageDraw

    w, h = ICON_W * SCALE, ICON_H * SCALE
    cw, chh = 3 * (w + 8) + 16, h + 24
    img = Image.new("RGB", (2 * cw, math.ceil(len(got) / 2) * chh), (14, 18, 26))
    bg = np.array([22, 28, 40], np.float32)
    for i, ic in enumerate(got):
        r, c = divmod(i, 2)
        x0, y0 = c * cw + 6, r * chh + 2
        sheet, index = ic["key"].rsplit(":", 1)
        orig = np.kron(gd.rgba(composite(gd, sheet, int(index)), SHOP_PALETTE), np.ones((SCALE, SCALE, 1), np.uint8))
        for j, im in enumerate((orig, before.get(ic["key"]), ic["rgba"])):
            if im is None:
                continue
            a = im[..., 3:4].astype(np.float32) / 255
            img.paste(Image.fromarray((im[..., :3] * a + bg * (1 - a)).astype(np.uint8)), (x0 + j * (w + 8), y0))
        ImageDraw.Draw(img).text((x0, y0 + h + 4), f"{ic['key'].replace('.shp', '')} {ic['input']} IoU {ic['iou']:.2f}/{ic['rule_iou']:.2f} NCC {ic['fit']['in_place']:.2f} dC {ic['colour_mae']:.0f}",
                                 fill=(230, 230, 120))
    img.save(path)
    print(f"  check: {path}")


def inventory_now(data: Path) -> list[dict]:
    """tools/shop-icons-inventory.mjs's list, made now from the game data."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "inventory.json"
        subprocess.run(["node", str(ROOT / "tools" / "shop-icons-inventory.mjs"), str(out)], cwd=ROOT, check=True,
                       env={**node_env(), "TYRIAN_DATA": str(data.resolve())}, stdout=subprocess.DEVNULL)
        return json.loads(out.read_text())


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheets")
    s.add_argument("--inventory", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--retry", choices=sorted(RETRIES), help="append this retry sheet (RETRIES) to DIR/manifest.json")
    c = sub.add_parser("cut")
    c.add_argument("--inputs", type=Path, required=True)
    c.add_argument("--results", type=Path, required=True)
    c.add_argument("--out", type=Path, default=ROOT / "public" / "art" / "shop")
    c.add_argument("--check", type=Path)
    c.add_argument("--keep", action="store_true", help="keep committed icons whose answers aren't in --results")
    m = sub.add_parser("models", help="re-render the icons the game draws as 3D models (D226) and repack the atlas")
    m.add_argument("--inventory", type=Path, help="tools/shop-icons-inventory.mjs's output (default: made now)")
    m.add_argument("--server", help="a running dev server's URL (default: start one on a free port 5220-5299)")
    m.add_argument("--out", type=Path, default=ROOT / "public" / "art" / "shop")
    m.add_argument("--check", type=Path, help="contact sheet original | before | after, with models-report.json beside it")
    args = ap.parse_args(argv)
    gd = GameData(args.data)
    if args.cmd == "sheets":
        build_sheets(gd, json.loads(args.inventory.read_text()), args.out, args.retry)
    elif args.cmd == "models":
        inventory = json.loads(args.inventory.read_text()) if args.inventory else inventory_now(args.data)
        models(gd, args.data, inventory, args.out, args.server, args.check)
    else:
        cut(gd, json.loads(args.inputs.read_text()), args.results, args.out, args.check, args.keep)


if __name__ == "__main__":
    main()
