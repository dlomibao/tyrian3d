"""Remastered end-credits art: Gemini paints the credits' pictures and the ship's banking frames (DECISIONS.md D218).

JE_playCredits (mainint.c L2347-2518, src/app/episodeEnd.ts) shows the nine pictures of estsc.shp
(the EXTRA_SHAPES table) fading in beside the rolling text, drawn with blit_sprite_hv(..., 0x0, fade - 15):
hue 0, so only each pixel's low nibble counts and every picture is a grey ramp of palette 6-1's
first 16 colours (a low nibble of 0 is black, which the game draws transparent on the black stage).
A ship weaves up the side: blit_sprite2x2 of ships[1..11].shipGraphic, or +-2 / +-4 when it banks.

    python tools/credits_art.py sheets --out DIR
        DIR/pictures-a.png, pictures-b.png: the pictures on black rectangles, scaled up SHEET_PX x
        (softened: bicubic, which keeps Gemini from copying the pixel blocks), packed in rows on flat
        neutral grey; DIR/ships.png: one row per credits ship, its four banking frames round its
        centre frame, the centre already painted (D210's shop icon) for Gemini to match.
        DIR/<sheet>.prompt.txt and DIR/manifest.json. Derived from the game data: keep them out of git (D3).

    python tools/credits_art.py cut --inputs DIR/manifest.json --results RESULTS [--out public/art/credits] [--check PNG]
        RESULTS/<sheet>.png|jpg|webp is Gemini's answer. Each picture is registered onto its original
        by zero-mean NCC of luminance (scale 0.95-1.05, aspect 0.98-1.02, with a prior toward the
        sheet's placement), resampled at SCALE texels per original pixel as grey (the C draws them in
        a grey ramp), its tones mapped onto the original's grey levels (quantile map, TONE), with the
        original's silhouette (holes of a pixel or two closed) as alpha:
            public/art/credits/picture-<n>.webp and manifest.json
            { "scale": 5, "pictures": { "0": { "image": "picture-0.webp", "w": 700, "h": 800 } } }
        The ships sheet's banking frames are cut with tools/shop_icons.py (the shop icons' format, D210)
        into public/art/credits/ships/: icons.webp and manifest.json keyed "tyrian.shp#8:<sprite>".
        --check writes a contact sheet original | remastered and cut-report.json beside it.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shop_icons  # noqa: E402
from flat_art import GameData, bleed, load_result, sample, smooth_alpha  # noqa: E402
from shop_icons import gray, ncc_map, resize_f  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CREDITS_PALETTE = 5  # g.res.palettes[6 - 1]
SHEET_PX = 5  # input px per original pixel
GAP = 12  # original px of grey between pictures
BACKGROUND = (118, 118, 118)  # flat neutral grey, as D210
SCALE = 5  # output texels per original pixel: the credits show a picture up to 46% of the screen's height
PRIOR = 0.6  # registration: NCC given up per unit of scale away from the sheet's
SHIFT_PRIOR = 0.004  # and per original pixel the picture moves from where the sheet put it
TONE = 1.0  # how far the painting's grey levels are mapped onto the original's (quantile map)

# What each picture shows (D187: name the objects), from the pictures. All are scenes of the game,
# seen from above, the player's fighter at the bottom firing up the screen.
DESCRIBE = {
    0: "the player's fighter with two small side pods at the bottom, firing a column of round fireballs up the screen; "
       "two flaming comet-shaped missiles fly outwards on either side; at the top a dark angular tower pours a thick "
       "column of white smoke with two coiled metal springs in it; the curved edge of a huge dark armoured hull "
       "with glowing white seams on the left; the rest is black space",
    1: "a fortress seen from above: a floor of square grey stone tiles and brick; across the top, a huge round "
       "armoured turret with two long horizontal gun barrels pointing right; the player's fighter with its two "
       "side pods at the bottom, surrounded by glowing white energy orbs",
    2: "an enormous egg-shaped armoured airship hull (a blimp) seen from above over a sea of dark rolling waves, "
       "with curved panel seams and round hatches, gun pods on struts at its sides and a gun turret at its nose; "
       "the player's fighter with two side pods at the bottom between two curled grey worm-like creatures",
    3: "a horned insect-like alien boss at the top: a ribbed carapace head with long curved mandible horns and a "
       "pointed snout, over dark speckled gravel ground; a column of rocks down the right edge; small claw-shaped "
       "shots flying down; the player's fighter with two side pods at the bottom",
    4: "a narrow canyon between walls of stacked metal blocks and slabs, seen from above, leading to a domed "
       "ribbed turret at the top; a wall of grey rubble across it and two columns of round grey smoke puffs "
       "down the middle; the noses of the player's ships at the bottom",
    5: "in black starry space: a spiral drill-shaped machine and a pointed cone at the top left, a small "
       "winged missile with a glowing exhaust flying left, a cluster of glowing fireballs; a huge cratered "
       "rock-and-metal space station curving in from the left, two tall rounded capsule tanks at the right; "
       "the noses of the player's ships at the bottom",
    6: "a ground of rounded cobblestones seen from above, a jumble of big faceted boulders across the top with "
       "a mechanical creature among them; the player's fighter with two side pods at the bottom firing up a trail "
       "of round grey smoke puffs; two small enemy fighters",
    7: "a tall narrow scene in black space: a long pointed blade-shaped missile at the top, a chain of glossy "
       "dark spheres (a segmented worm) curling down the right side, three glowing orbs, two faceted crystal "
       "shards; the player's fighter with two side pods at the bottom",
    8: "a huge mechanical mothership at the top with a central armoured panel and gun turrets hanging on arms at "
       "the sides, more domed turrets at the bottom corners; the player's fighter with two side pods at the bottom "
       "firing three bright white laser beams straight up; small four-pointed sparkles and x-shaped stars in black space",
}

# Sheets of pictures: rows of picture numbers. Two sheets near square, ~5 answer px per original pixel.
SHEETS = {
    "pictures-a": [[0, 1, 2], [3, 4]],
    "pictures-b": [[5, 6, 7], [8]],
}

# Retries (`sheets --retry NAME`): pictures the first answers got wrong, sent again with wording aimed at
# what went wrong and a softer input (soften: Gaussian sigma in original pixels). Appended to the
# manifest, so `cut` takes their pictures over the first answers'.
RETRIES = {
    "retry-1": {
        "rows": [[0, 1], [4]],
        "soften": 0.7,
        "describe": {
            # The round puffs came back as fireballs and flames, and the side trails as comets with heads.
            0: "the player's fighter with two small side pods at the bottom; above it three soft round grey smoke puffs in a "
               "V (smoke, no flames, no fireballs); two tapered grey smoke trails angled outwards, wide at the top outer "
               "end and thinning to a point towards the centre (smoke, no flaming head); at the top a dark angular tower "
               "pours a thick column of white smoke with two coiled metal springs in it; the curved edge of a huge dark "
               "armoured hull with white seams on the left; the rest is black space",
            # Pixel copying: the floor tiles came back as the same square pixel blocks.
            1: "a fortress seen from above: a floor of square grey stone slabs and brick, painted as real bevelled stone "
               "with worn edges and mortar lines (not square pixels); across the top, a huge round armoured turret with two "
               "long horizontal gun barrels pointing right, painted as solid gunmetal with panel lines; the player's fighter "
               "with its two side pods at the bottom, surrounded by glowing white energy orbs",
            # Pixel copying on the walls.
            4: "a narrow canyon seen from above between walls of stacked metal blocks and armour slabs, painted as solid "
               "bevelled metal with panel lines and rivets (not square pixels), leading to a domed ribbed turret at the top; "
               "a band of grey rubble across it and two columns of round grey smoke puffs down the middle; the noses of the "
               "player's ships at the bottom",
        },
    },
    "retry-2": {
        "rows": [[1]],
        "soften": 0.7,
        "describe": {
            # retry-1 painted it, but ran the two gun barrels on as long rods to the right edge.
            1: "a fortress seen from above: a floor of square grey stone slabs and brick, painted as real bevelled stone "
               "with worn edges and mortar lines (not square pixels); across the top, a huge round armoured turret with two "
               "short, chunky horizontal guns pointing right, each ending in a blunt rounded muzzle block about two thirds of "
               "the way across, with the stone and metal wall continuing to the right of the muzzles (the guns do NOT reach "
               "the right edge), painted as solid gunmetal with panel lines; the player's fighter with its two side pods at "
               "the bottom, surrounded by glowing white energy orbs",
        },
    },
}

# The credits' ships: ships[1..11].shipGraphic in every episode's item data (USP Talon and Fang 233,
# SuperCarrot 119, Gencore Phoenix and Maelstrom 157, the Stalkers 195, U-Ship 271, Silver Ship 81).
CREDITS_SHIPS = {
    233: "the USP Talon: a tan-bronze delta-wing fighter",
    119: "the SuperCarrot: a carrot-shaped orange fighter with green leafy fins at its tail",
    157: "the Gencore Phoenix: a grey fighter with swept wings",
    195: "the MicroCorp Stalker: a grey fighter with swept wings and a red engine",
    271: "the U-Ship: a dark U-shaped frame round a small bronze dome",
    81: "the Silver Ship: a silver fighter with red bands at its tail",
}
BANKS = (-4, -2, 0, 2, 4)  # credits ship frame offsets (episodeEnd.ts: shipxc < -20 ... > 20)
SHIP_CELL = shop_icons.CELL
SHIP_PX = shop_icons.SHEET_PX


# --- The pictures ----------------------------------------------------------------------------------


def pictures(data: Path) -> list[np.ndarray]:
    """estsc.shp's sprites (load_sprites), decoded (blit_sprite): raw palette indices, -1 transparent."""
    b = (data / "estsc.shp").read_bytes()
    n = struct.unpack_from("<H", b, 0)[0]
    p, out = 2, []
    for _ in range(n):
        if not b[p]:
            p += 1
            continue
        w, h, size = struct.unpack_from("<HHH", b, p + 1)
        p += 7
        d = b[p:p + size]
        p += size
        pix = np.full((h, w), -1, np.int16)
        x = y = i = 0
        while i < len(d):
            c = d[i]
            if c == 255:
                i += 1
                x += d[i]
            elif c == 254:
                x = w
            elif c == 253:
                x += 1
            else:
                if y < h and x < w:
                    pix[y, x] = c
                x += 1
            if x >= w:
                x, y = 0, y + 1
            i += 1
        out.append(pix[:200])
    return out


def shade(pic: np.ndarray) -> np.ndarray:
    """blit_sprite_hv(hue 0, value 0): the low nibble; 0 = black, drawn transparent by the game."""
    return np.where(pic >= 0, pic & 15, 0)


def grey_rgb(gd: GameData, pic: np.ndarray) -> np.ndarray:
    """The picture as the credits show it, on black: (h, w, 3) uint8."""
    return gd.palettes[CREDITS_PALETTE][shade(pic)]


def silhouette(pic: np.ndarray) -> np.ndarray:
    """Where the picture shows: its visible pixels with holes of a pixel or two closed (the black
    pixels inside a scene are part of it; the empty space round a scene isn't)."""
    from scipy import ndimage

    m = shade(pic) > 0
    closed = ndimage.binary_closing(np.pad(m, 3), np.ones((3, 3), bool), iterations=2)[3:-3, 3:-3]
    return ndimage.binary_fill_holes(closed | m)


def prompt_for(name: str, rows: list[list[int]], describe: dict[int, str] = DESCRIBE) -> str:
    n = sum(len(r) for r in rows)
    order = []
    for r, row in enumerate(rows):
        for c, k in enumerate(row):
            order.append(f"({len(order) + 1}, row {r + 1} {['left', 'middle', 'right'][c] if len(row) == 3 else ['left', 'right'][c] if len(row) == 2 else 'centre'}): {describe[k]}.")
    return (
        f"This image holds {n} small black-and-white pixel-art illustrations from the end credits of a 1990s top-down "
        "space shooter (Tyrian), each a rectangle on a flat neutral grey background, in rows. They are monochrome: "
        "every one is drawn only in shades of grey from black to white. Repaint every illustration as a remastered, "
        "high-resolution, hand-painted monochrome illustration in the same greys: crisp clean edges, fine mechanical and "
        "natural detail (panel lines, rivets, rock facets, smoke, glow), soft light, one consistent style. Keep each "
        "illustration exactly where it is and exactly the same size and shape, with the same composition: every object "
        "in the same place, the same size and the same silhouette, the same light and dark areas, black where it is black. "
        "Grayscale only, no colour. Don't add objects, text, frames or borders; don't move, crop, rotate or resize "
        "anything; keep the grey background between them flat. Paint it, don't copy the square pixels. "
        "The illustrations, left to right, top to bottom: " + " ".join(order)
    )


def build_picture_sheet(gd: GameData, pics: list[np.ndarray], name: str, rows: list[list[int]], soften: float = 0.0,
                        describe: dict[int, str] = DESCRIBE) -> tuple[np.ndarray, dict]:
    row_w = [sum(pics[k].shape[1] for k in row) + GAP * (len(row) + 1) for row in rows]
    row_h = [max(pics[k].shape[0] for k in row) for row in rows]
    w = max(row_w)
    h = sum(row_h) + GAP * (len(rows) + 1)
    side = max(w, h)  # square: 1:1 is an aspect Gemini keeps
    img = np.zeros((side * SHEET_PX, side * SHEET_PX, 3), np.uint8)
    img[:] = BACKGROUND
    y = (side - h) // 2 + GAP
    cells = []
    for row, rh in zip(rows, row_h):
        x = (side - sum(pics[k].shape[1] for k in row) - GAP * (len(row) - 1)) // 2
        for k in row:
            ph, pw = pics[k].shape
            py = y + (rh - ph) // 2
            rgb = Image.fromarray(grey_rgb(gd, pics[k])).resize((pw * SHEET_PX, ph * SHEET_PX), Image.BICUBIC)
            rgb = np.asarray(rgb)
            if soften:
                from scipy import ndimage

                rgb = np.stack([ndimage.gaussian_filter(rgb[..., c].astype(np.float32), soften * SHEET_PX, mode="nearest")
                                for c in range(3)], -1).round().clip(0, 255).astype(np.uint8)
            img[py * SHEET_PX:(py + ph) * SHEET_PX, x * SHEET_PX:(x + pw) * SHEET_PX] = rgb
            cells.append({"picture": k, "x": x * SHEET_PX, "y": py * SHEET_PX, "w": pw, "h": ph})
            x += pw + GAP
        y += rh + GAP
    prompt = prompt_for(name, rows, {**DESCRIBE, **describe})
    return img, {"name": name, "image": f"{name}.png", "size": [side * SHEET_PX, side * SHEET_PX], "sheet_px": SHEET_PX,
                 "aspect": "1:1", "prompt": prompt, "cells": cells}


# --- The ship's banking frames -----------------------------------------------------------------------


def shop_icon(key: str) -> np.ndarray | None:
    """D210's painted icon (RGBA, 144x168) from the committed shop atlas, or None."""
    shop = ROOT / "public" / "art" / "shop"
    m = json.loads((shop / "manifest.json").read_text())
    r = m["icons"].get(key)
    if not r:
        return None
    atlas = np.asarray(Image.open(shop / m["image"]).convert("RGBA"))
    return atlas[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]]


def build_ship_sheet(gd: GameData) -> tuple[np.ndarray, dict]:
    """One row per credits ship: frames -4, -2, 0, +2, +4 (blit_sprite2x2 of tyrian.shp#8), the
    centre one D210's painting, the others the original pixels (nearest, like D210's sheets). 3:4."""
    cols, rows = len(BANKS), len(CREDITS_SHIPS)
    w, h = cols * SHIP_CELL, rows * SHIP_CELL
    h45 = w * 4 // 3  # 3:4, a ratio Gemini offers
    img = np.zeros((h45, w, 3), np.uint8)
    img[:] = shop_icons.BACKGROUND
    oy = (h45 - h) // 2
    cells, listing = [], []
    iw, ih = shop_icons.ICON_W * SHIP_PX, shop_icons.ICON_H * SHIP_PX
    for r, (g, what) in enumerate(CREDITS_SHIPS.items()):
        for c, d in enumerate(BANKS):
            x = c * SHIP_CELL + (SHIP_CELL - iw) // 2
            y = oy + r * SHIP_CELL + (SHIP_CELL - ih) // 2
            if d == 0:
                hd = shop_icon(f"tyrian.shp#8:{g}")
                rgba = np.asarray(Image.fromarray(hd).resize((iw, ih), Image.LANCZOS)).astype(np.float32) / 255
                a = rgba[..., 3:]
                sub = img[y:y + ih, x:x + iw].astype(np.float32) / 255
                img[y:y + ih, x:x + iw] = ((rgba[..., :3] * a + sub * (1 - a)) * 255).round().astype(np.uint8)
                continue
            pic = shop_icons.composite(gd, "tyrian.shp#8", g + d)
            big = np.kron(gd.rgba(pic, CREDITS_PALETTE), np.ones((SHIP_PX, SHIP_PX, 1), np.uint8))
            m = big[..., 3] > 0
            img[y:y + ih, x:x + iw][m] = big[..., :3][m]
            side = "left" if d < 0 else "right"
            cells.append({"key": f"tyrian.shp#8:{g + d}", "sheet": "tyrian.shp#8", "index": g + d, "row": r, "col": c,
                          "rect": [c * SHIP_CELL, oy + r * SHIP_CELL, SHIP_CELL, SHIP_CELL], "x": x, "y": y,
                          "names": f"{what.split(':')[0]}, banking {'hard ' if abs(d) == 4 else ''}{side}"})
        listing.append(f"Row {r + 1}: {what}, seen from above, nose up.")
    prompt = (
        f"This image is a grid of {rows} rows and {cols} columns of small fighter spacecraft from a 1990s top-down space "
        "shooter (Tyrian), each centred in its own square cell on a flat neutral grey background, seen from above, nose up. "
        "Each row is one ship: the middle column is the ship flying level and is ALREADY PAINTED in the finished style; "
        "the other four columns are the same ship banking (rolling) left (columns 1 and 2, column 1 the hardest) and right "
        "(columns 4 and 5, column 5 the hardest), still as pixel art. Repaint the pixel-art ships of columns 1, 2, 4 and 5 "
        "in exactly the style, materials, colours and detail of the painted ship in the middle of their row, as the same "
        "ship rolled to that side, so all five frames of a row look like one painted ship turning. Keep each ship exactly "
        "where it is and exactly the same size, with the same silhouette as its pixel-art frame, the same parts in the "
        "same places, its dark outline. Leave the middle column as it is. Don't add parts, text, labels, frames or "
        "borders; don't move, rotate or resize anything; keep the background the same flat neutral grey. Paint it, don't "
        "copy the square pixels. The rows: " + " ".join(listing)
    )
    return img, {"name": "ships", "image": "ships.png", "size": [w, h45], "aspect": "3:4", "prompt": prompt,
                 "grid": {"rows": rows, "cols": cols, "cell": SHIP_CELL}, "cells": cells}


def build_sheets(gd: GameData, out: Path, retry: str | None = None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    pics = pictures(gd.data_dir)
    if retry:
        manifest = json.loads((out / "manifest.json").read_text())
        manifest["sheets"] = [sh for sh in manifest["sheets"] if sh["name"] != retry]
        spec = RETRIES[retry]
        img, sheet = build_picture_sheet(gd, pics, retry, spec["rows"], spec["soften"], spec["describe"])
        Image.fromarray(img).save(out / f"{retry}.png")
        (out / f"{retry}.prompt.txt").write_text(sheet["prompt"] + "\n")
        manifest["sheets"].append(sheet)
        (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
        print(f"  {out / sheet['image']}: {sheet['size'][0]}x{sheet['size'][1]}, {len(sheet['cells'])} pictures, prompt {len(sheet['prompt'])} chars")
        return
    manifest = {"note": "pictures: cell x, y = input px of the picture's top-left, SHEET_PX input px per pixel; "
                        "ships: shop_icons.py's sheet format", "palette": CREDITS_PALETTE, "sheets": []}
    for name, rows in SHEETS.items():
        img, sheet = build_picture_sheet(gd, pics, name, rows)
        Image.fromarray(img).save(out / f"{name}.png")
        manifest["sheets"].append(sheet)
    img, sheet = build_ship_sheet(gd)
    Image.fromarray(img).save(out / "ships.png")
    manifest["ships"] = sheet
    for sh in manifest["sheets"] + [manifest["ships"]]:
        (out / f"{sh['name']}.prompt.txt").write_text(sh["prompt"] + "\n")
        print(f"  {out / sh['image']}: {sh['size'][0]}x{sh['size'][1]} ({sh['aspect']}), {len(sh['cells'])} cut, prompt {len(sh['prompt'])} chars")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))


# --- Cutting the pictures ----------------------------------------------------------------------------


def register(art: np.ndarray, ref: np.ndarray, margin: int, nominal: tuple[float, float, float], q: int = 2) -> dict:
    """Fit the picture (ref: grey 0..1 with `margin` px of background round it, 1 px per original
    pixel) onto the answer's luminance. nominal: answer px of the picture's (0, 0) and answer px per
    original pixel. Returns x0, y0, kx, ky (answer px = x0 + kx * u) and the NCC."""
    from scipy import ndimage

    x0n, y0n, kn = nominal
    ph, pw = ref.shape
    g = (GAP - 2) * kn  # search within the grey gap round the picture
    wx0, wy0 = int(x0n - margin * kn - g), int(y0n - margin * kn - g)
    wx1, wy1 = int(x0n + (pw - margin) * kn + g), int(y0n + (ph - margin) * kn + g)
    H, W = art.shape[:2]
    bg = gray(np.array(BACKGROUND, np.float32) / 255)
    I = np.full((wy1 - wy0, wx1 - wx0), bg, np.float32)
    sy0, sx0 = max(wy0, 0), max(wx0, 0)
    I[sy0 - wy0:min(wy1, H) - wy0, sx0 - wx0:min(wx1, W) - wx0] = gray(art[sy0:min(wy1, H), sx0:min(wx1, W)])
    f = q / kn
    I = ndimage.gaussian_filter(resize_f(I, int(round((wx1 - wx0) * f)), int(round((wy1 - wy0) * f))), q * 0.5)
    R = np.kron(ref, np.ones((q, q), np.float32))
    best = {"chosen": -9.0}
    for s in np.arange(0.95, 1.0501, 0.005):
        for a in (0.98, 0.99, 1.0, 1.01, 1.02):
            sx, sy = s * math.sqrt(a), s / math.sqrt(a)
            tw, th = int(round(R.shape[1] * sx)), int(round(R.shape[0] * sy))
            T = ndimage.gaussian_filter(resize_f(R, tw, th), q * 0.5)
            ncc = ncc_map(I, T)
            if ncc is None:
                continue
            yy, xx = np.mgrid[0:ncc.shape[0], 0:ncc.shape[1]].astype(np.float32)
            cx = (x0n - wx0) * f - margin * q * sx + (R.shape[1] / 2) * (1 - sx)
            cy = (y0n - wy0) * f - margin * q * sy + (R.shape[0] / 2) * (1 - sy)
            adj = ncc - SHIFT_PRIOR * np.hypot(xx - cx, yy - cy) / q
            oy, ox = np.unravel_index(int(np.argmax(adj)), adj.shape)
            chosen = float(adj[oy, ox]) - PRIOR * (abs(sx - 1) + abs(sy - 1)) / 2
            if chosen > best["chosen"]:
                kx, ky = tw / R.shape[1] * kn, th / R.shape[0] * kn
                best = {"score": float(ncc[oy, ox]), "chosen": chosen, "kx": kx, "ky": ky,
                        "x0": wx0 + ox / f + margin * kx, "y0": wy0 + oy / f + margin * ky}
    best["shift"] = [best["x0"] - x0n, best["y0"] - y0n]
    best["scale"] = [best["kx"] / kn, best["ky"] / kn]
    return best


def tone_map(v: np.ndarray, small: np.ndarray, orig: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Map grey levels so the painting brought back to the original's pixels (small) has the
    original's distribution of greys over the picture (quantile map, monotone)."""
    qs = np.linspace(0, 1, 65)
    src = np.quantile(small[m], qs)
    dst = np.quantile(orig[m], qs)
    src = np.maximum.accumulate(src + np.arange(len(src)) * 1e-6)
    mapped = np.interp(v, src, dst)
    return v + TONE * (mapped - v)


def cut_picture(gd: GameData, art: np.ndarray, sheet: dict, cell: dict, pic: np.ndarray) -> dict:
    H, W = art.shape[:2]
    rx, ry = W / sheet["size"][0], H / sheet["size"][1]
    k = sheet["sheet_px"] * (rx + ry) / 2
    margin = 4
    ref = grey_rgb(gd, pic).astype(np.float32).mean(-1) / 255
    ref = np.pad(ref, margin, constant_values=gray(np.array(BACKGROUND, np.float32) / 255))
    fit = register(art, ref, margin, (cell["x"] * rx, cell["y"] * ry, k))
    ph, pw = pic.shape
    v, u = np.mgrid[0:ph * SCALE, 0:pw * SCALE].astype(np.float32)
    u, v = (u + 0.5) / SCALE, (v + 0.5) / SCALE
    lum = gray(sample(art, fit["x0"] + fit["kx"] * u, fit["y0"] + fit["ky"] * v, fit["kx"] / SCALE))
    sil = silhouette(pic)
    alpha = smooth_alpha(sil, SCALE, sigma=SCALE * 3 / 8)
    orig = grey_rgb(gd, pic).astype(np.float32).mean(-1) / 255

    def err(x: np.ndarray) -> float:
        small = x.reshape(ph, SCALE, pw, SCALE).mean((1, 3))
        return float(np.abs(small[sil] - orig[sil]).mean() * 255)

    raw_err = err(lum)
    small = lum.reshape(ph, SCALE, pw, SCALE).mean((1, 3))
    lum = np.clip(tone_map(lum, small, orig, sil), 0, 1)
    rgb = bleed(np.repeat(lum[..., None], 3, -1), alpha)
    return {"picture": cell["picture"], "rgba": np.dstack([rgb * 255, alpha * 255]).round().astype(np.uint8), "fit": fit,
            "grey_mae_raw": raw_err, "grey_mae": err(lum), "input": sheet["name"]}


def write_pictures(cuts: list[dict], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"scale": SCALE, "pictures": {}}
    for c in sorted(cuts, key=lambda c: c["picture"]):
        name = f"picture-{c['picture']}.webp"
        h, w = c["rgba"].shape[:2]
        Image.fromarray(c["rgba"], "RGBA").save(out / name, "WEBP", quality=88, alpha_quality=90, method=6, exact=True)
        manifest["pictures"][str(c["picture"])] = {"image": name, "w": w, "h": h}
        print(f"  {out / name}: {w}x{h}, {(out / name).stat().st_size // 1024} KB")
    lines = ["{", f'  "scale": {SCALE},', '  "pictures": {']
    items = list(manifest["pictures"].items())
    lines += [f"    {json.dumps(k)}: {json.dumps(v)}" + ("," if i < len(items) - 1 else "") for i, (k, v) in enumerate(items)]
    lines += ["  }", "}", ""]
    (out / "manifest.json").write_text("\n".join(lines))


def contact_sheet(gd: GameData, pics: list[np.ndarray], cuts: list[dict], path: Path, scale: int = 3) -> None:
    """original (nearest) | remastered, per picture, on black, at `scale` x."""
    from PIL import ImageDraw

    cw = max(p.shape[1] for p in pics) * scale * 2 + 30
    ch = max(p.shape[0] for p in pics) * scale + 24
    cols = 3
    rows = math.ceil(len(cuts) / cols)
    img = Image.new("RGB", (cols * cw, rows * ch), (40, 40, 48))
    for i, c in enumerate(sorted(cuts, key=lambda c: c["picture"])):
        r, col = divmod(i, cols)
        pic = pics[c["picture"]]
        ph, pw = pic.shape
        x0, y0 = col * cw + 6, r * ch + 2
        o = Image.fromarray(grey_rgb(gd, pic)).resize((pw * scale, ph * scale), Image.NEAREST)
        img.paste(o, (x0, y0))
        a = c["rgba"].astype(np.float32) / 255
        hd = Image.fromarray((a[..., :3] * a[..., 3:] * 255).astype(np.uint8)).resize((pw * scale, ph * scale), Image.LANCZOS)
        img.paste(hd, (x0 + pw * scale + 12, y0))
        ImageDraw.Draw(img).text((x0, y0 + ph * scale + 4), f"picture {c['picture']} NCC {c['fit']['score']:.2f} "
                                 f"grey err {c['grey_mae_raw']:.0f}->{c['grey_mae']:.0f}", fill=(230, 230, 120))
    img.save(path)
    print(f"  check: {path}")


def cut(gd: GameData, inputs: dict, results: Path, out: Path, check: Path | None) -> None:
    pics = pictures(gd.data_dir)
    cuts = []
    for sheet in inputs["sheets"]:
        art = load_result(results, sheet["name"])
        if art is None:
            print(f"  {sheet['name']}: no answer, skipped")
            continue
        for cell in sheet["cells"]:
            c = cut_picture(gd, art, sheet, cell, pics[cell["picture"]])
            cuts = [x for x in cuts if x["picture"] != c["picture"]] + [c]
            print(f"  picture {c['picture']} ({sheet['name']}): NCC {c['fit']['score']:.3f}, scale "
                  f"{c['fit']['scale'][0]:.3f}x{c['fit']['scale'][1]:.3f}, shift {c['fit']['shift'][0]:.1f},{c['fit']['shift'][1]:.1f} "
                  f"answer px, grey error {c['grey_mae_raw']:.1f} -> {c['grey_mae']:.1f}")
    if cuts:
        write_pictures(cuts, out)
    ships = inputs.get("ships")
    ship_art = load_result(results, "ships") if ships else None
    ship_cuts = []
    if ship_art is not None:
        ship_cuts = [shop_icons.cut_icon(gd, ship_art, ships, c) for c in ships["cells"]]
        so = out / "ships"
        so.mkdir(parents=True, exist_ok=True)
        atlas, rects = shop_icons.pack(ship_cuts, cols=len(BANKS) - 1)
        Image.fromarray(atlas, "RGBA").save(so / "icons.webp", "WEBP", quality=90, alpha_quality=100, method=6, exact=True)
        lines = ["{", f'  "scale": {shop_icons.SCALE},', '  "image": "icons.webp",', '  "icons": {']
        items = list(rects.items())
        lines += [f"    {json.dumps(k)}: {json.dumps(r)}" + ("," if i < len(items) - 1 else "") for i, (k, r) in enumerate(items)]
        lines += ["  }", "}", ""]
        (so / "manifest.json").write_text("\n".join(lines))
        s = [c["fit"]["score"] for c in ship_cuts]
        print(f"  {so / 'icons.webp'}: {len(rects)} frames, NCC min {min(s):.3f} median {np.median(s):.3f}, "
              f"{(so / 'icons.webp').stat().st_size // 1024} KB")
    if check:
        check.parent.mkdir(parents=True, exist_ok=True)
        report = {"pictures": [{"picture": c["picture"], "input": c["input"], "ncc": round(c["fit"]["score"], 4),
                                "scale": [round(x, 3) for x in c["fit"]["scale"]], "shift_px": [round(x, 1) for x in c["fit"]["shift"]],
                                "grey_mae_raw": round(c["grey_mae_raw"], 1), "grey_mae": round(c["grey_mae"], 1)}
                               for c in sorted(cuts, key=lambda c: c["picture"])],
                  "ships": [{"key": c["key"], "names": c["names"], "ncc": round(c["fit"]["score"], 4),
                             "scale": [round(x, 3) for x in c["fit"]["scale"]], "colour_mae": round(c["colour_mae"], 1)}
                            for c in ship_cuts]}
        (check.parent / "cut-report.json").write_text(json.dumps(report, indent=1))
        if cuts:
            contact_sheet(gd, pics, cuts, check)
        if ship_cuts:
            centre = []
            for g in CREDITS_SHIPS:
                hd = shop_icon(f"tyrian.shp#8:{g}")
                if hd is not None:
                    centre.append({"key": f"tyrian.shp#8:{g}", "rgba": hd, "fit": {"score": float("nan")}, "colour_mae": float("nan")})
            frames = sorted(ship_cuts + centre, key=lambda e: (list(CREDITS_SHIPS).index(min(CREDITS_SHIPS, key=lambda g: abs(g - int(e["key"].split(":")[1])))),
                                                               int(e["key"].split(":")[1])))
            shop_icons.contact_sheet(gd, frames, check.with_name(check.stem + "-ships.png"), cols=len(BANKS))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheets")
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--retry", choices=sorted(RETRIES), help="append this retry sheet (RETRIES) to DIR/manifest.json")
    c = sub.add_parser("cut")
    c.add_argument("--inputs", type=Path, required=True)
    c.add_argument("--results", type=Path, required=True)
    c.add_argument("--out", type=Path, default=ROOT / "public" / "art" / "credits")
    c.add_argument("--check", type=Path)
    args = ap.parse_args(argv)
    gd = GameData(args.data)
    if args.cmd == "sheets":
        build_sheets(gd, args.out, args.retry)
    else:
        cut(gd, json.loads(args.inputs.read_text()), args.results, args.out, args.check)


if __name__ == "__main__":
    main()
