"""Flat remastered sprites: Gemini art cut, registered and packed as atlases (DECISIONS.md D42 draws them, D43 is this pipeline).

Shots and pickups stay flat 2D sprites in game, drawn with high-resolution art made by Google Gemini
from input sheets of the original sprites. This tool does both ends of that loop:

    python tools/flat_art.py sheets --inventory INV.json --out DIR
        Gemini input sheets (PNG, original pixels scaled up nearest-neighbour, on a dark checker) and
        DIR/manifest.json saying which sprite sits where. Derived from the game data, so they stay
        out of git (D3); keep them in a scratch folder.

    python tools/flat_art.py cut --inputs DIR/manifest.json --results RESULTS_DIR [--out public/art/sprites] [--merge]
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

        --merge rebuilds only the atlases these inputs feed (e.g. the explosions, newsh6.shp, from
        tools/flat_art_explosions.json, D80). The manifest's other sheets are always kept, and so
        are frames another tool put in a rebuilt sheet (those with their own "scale": value_art.py's
        coin values share newsh6.shp, D76).
        --append (implies --merge) adds only the frames the manifest lacks: every committed frame
        keeps its rect and pixels, and the new ones are packed below them in the same atlas (D214).

    python tools/flat_art.py recolour [--only SHEET:INDEX,...]
        Recolours the frames tools/flat_art_recolour.json lists toward their sprite's own palette ramp
        (and joins beam pieces), in the committed atlases, once; `cut` applies the same file to what it
        cuts (D172).

    python tools/flat_art.py paint [--check PNG]
        Paints the PAINTED frames the committed atlases lack and appends them below their sheet's frames,
        every committed frame kept as it is (as --append does): the hit sparks were added this way (D247).

    python tools/flat_art.py shade [--sheets tyrian.shp#10]
        Writes each frame's shade gain ("shade" in its manifest rect) for the renderer's palette
        effects: the gain that spreads the painting's brightness shades as its sprite's palette
        indices spread (D221). Run it after a cut or recolour of those sheets.

A few frames are painted here instead of cut from Gemini's art (PAINTED: the Vulcan Cannon's
tracers, D56; the shots' hit sparks, D247; the diamond shot #10 76, D258); `cut` draws them with their
painter and packs them with the rest, `paint` adds the missing ones alone.

The original sprites are read from the game data (--data, default data/): tyrian.shp's Sprite2
tables and the newsh<c>.shp sheets (src/data/sprites.ts) and palette.dat (src/data/palette.ts).
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
FIRST_SPRITE2_TABLE = 7  # tyrian.shp#0..#6 are sprite tables (blit_sprite), #7.. Sprite2 sheets (resources.ts)
LEVEL1_PALETTE = 5  # drawList.palette in Episode 1's first level (TYRIAN)

# --- Game data -----------------------------------------------------------------------------------


class GameData:
    """tyrian.shp's tables and palette.dat, read as src/data/sprites.ts and palette.ts do."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        shp = (data_dir / "tyrian.shp").read_bytes()
        count = struct.unpack_from("<H", shp, 0)[0]
        pos = [struct.unpack_from("<I", shp, 2 + i * 4)[0] for i in range(count)] + [len(shp)]
        self.tables = [shp[pos[i]:pos[i + 1]] for i in range(count)]
        self.files: dict[str, bytes] = {}
        pal = (data_dir / "palette.dat").read_bytes()
        self.palettes = []
        for p in range(len(pal) // 768):
            raw = np.frombuffer(pal[p * 768:(p + 1) * 768], dtype=np.uint8).reshape(256, 3).astype(np.int32)
            self.palettes.append(((raw << 2) | (raw >> 4)).astype(np.uint8))

    def sheet(self, sheet_id: str) -> bytes:
        if sheet_id.startswith("newsh") and sheet_id.endswith(".shp"):
            # A comp-shapes sheet (newsh<c>.shp, resources.ts loadCompShapes): the whole file is one Sprite2 sheet.
            if sheet_id not in self.files:
                self.files[sheet_id] = (self.data_dir / sheet_id).read_bytes()
            return self.files[sheet_id]
        if not sheet_id.startswith("tyrian.shp#"):
            raise ValueError(f"only tyrian.shp and newsh*.shp sheets are supported, not {sheet_id}")
        return self.tables[int(sheet_id.split("#")[1])]

    def table_sprite(self, table: int, index: int) -> np.ndarray:
        """A sprite table's sprite (tyrian.shp#0..#6; parseSpriteTable + decodeTableSprite in
        src/data/sprites.ts), 0-based as the C passes it: its own width and height; -1 = transparent."""
        t = self.tables[table]
        count, p = struct.unpack_from("<H", t, 0)[0], 2
        for i in range(count):
            if not t[p]:
                p += 1
                if i == index:
                    break
                continue
            w, h, size = struct.unpack_from("<HHH", t, p + 1)
            p += 7
            if i == index:
                data, px, x, y, k = t[p:p + size], np.full((h, w), -1, np.int16), 0, 0, 0
                while k < len(data):
                    b = data[k]
                    if b == 255:
                        k += 1
                        x += data[k]
                    elif b == 254:
                        x = w
                    elif b == 253:
                        x += 1
                    else:
                        if y < h and x < w:
                            px[y, x] = b
                        x += 1
                    if x >= w:
                        x, y = 0, y + 1
                    k += 1
                return px
            p += size
        return np.full((0, TILE_W), -1, dtype=np.int16)

    def sprite(self, sheet_id: str, index: int) -> np.ndarray:
        """decodeSprite2: palette indices, 12 wide, as many rows as the RLE has; -1 = transparent.
        A sprite table's (tyrian.shp#0..#6) is its own size, 0-based (table_sprite)."""
        if sheet_id.startswith("tyrian.shp#") and int(sheet_id.split("#")[1]) < FIRST_SPRITE2_TABLE:
            return self.table_sprite(int(sheet_id.split("#")[1]), index)
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


def soft_alpha(mask: np.ndarray, sigma: float, lo: float, hi: float, scale: int = SCALE) -> np.ndarray:
    """A softer silhouette than smooth_alpha (inventory "alpha": {"sigma", "lo", "hi"}): the mask
    upscaled, blurred by sigma texels and smoothstepped from lo to hi. With sigma 5 and lo..hi
    0.3..0.55 a one-pixel staircase (a fireball's thin ring) becomes a smooth line instead of dashes,
    and the edge grows by about a third of a sprite pixel (lower lo grows it more, and it is cut at
    the picture's box)."""
    from scipy import ndimage

    big = np.kron(mask.astype(np.float32), np.ones((scale, scale), np.float32))
    pad = int(math.ceil(sigma * 3))
    blurred = ndimage.gaussian_filter(np.pad(big, pad), sigma)[pad:-pad, pad:-pad]
    t = np.clip((blurred - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def shadow_alpha(pic: np.ndarray, silhouette, spec: dict, cover: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Alpha of a picture whose drop shadow is the palette indices spec["indices"]: the rest of the
    picture as the silhouette (times cover, art_coverage, when given), plus the shadow's pixels as a
    blurred translucent layer behind it. Also the shadow's own texels (a mask), whose colour is drawn
    black instead of bled from the body."""
    from scipy import ndimage

    is_shadow = np.isin(pic, spec["indices"])
    body = silhouette((pic >= 0) & ~is_shadow)
    if cover is not None:
        body = body * cover
    big = np.kron(is_shadow.astype(np.float32), np.ones((SCALE, SCALE), np.float32))
    soft = np.clip(ndimage.gaussian_filter(big, spec.get("sigma", 5.0)) * 1.3, 0.0, 1.0)
    return np.maximum(body, spec.get("strength", 0.4) * soft), np.kron(is_shadow, np.ones((SCALE, SCALE), bool))


def art_coverage(art: np.ndarray, fit: dict, shape: tuple[int, int], spec: dict) -> np.ndarray:
    """Where the registered art itself paints the object (inventory "art_alpha": {"lo", "hi", "sigma"}),
    at SCALE texels per picture pixel over the whole picture (shape: its rows, columns): the art's
    brightest channel smoothstepped from lo to hi (Gemini answers on black), its enclosed holes filled
    (a recess painted dark stays opaque, as the original's pixels there are), then blurred by sigma
    texels. Multiplied into the silhouette, it takes out a dark ink ring the original draws round the
    object and the painting leaves as background (D132's key: black under that ring)."""
    from scipy import ndimage

    h, w = shape
    v, u = np.mgrid[0:h * SCALE, 0:w * SCALE].astype(np.float32)
    px, py = (u + 0.5) / SCALE, (v + 0.5) / SCALE
    rgb = sample(art, fit["x0"] + fit["kx"] * px, fit["y0"] + fit["ky"] * py, fit["kx"] / SCALE)
    lo, hi = spec.get("lo", 0.06), spec.get("hi", 0.14)
    t = np.clip((rgb.max(-1) - lo) / (hi - lo), 0.0, 1.0)
    cov = t * t * (3 - 2 * t)
    cov = np.maximum(cov, ndimage.binary_fill_holes(cov > 0.5).astype(np.float32))
    return np.clip(ndimage.gaussian_filter(cov, spec.get("sigma", 1.5)), 0.0, 1.0)


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


# Objects drawn as four separate 12x14 sprites that aren't blit_sprite2x2's index, +1, +19, +20:
# (index offset, x, y) of each quarter from the top-left one. A big explosion is four explosions of
# their own (JE_setupExplosionLarge, varz.ts), each animating its own run of newsh6.shp frames:
# air types 7/9/8/10 start at sprites 1, 39, 20, 58, ground types 2/4/3/5 at 190, 152, 209, 171,
# placed at (x-6, y-14), (x+6, y-14), (x-6, y), (x+6, y). Painted whole, cut into quarters.
LAYOUTS = {
    "explosion-air": ((0, 0, 0), (38, 12, 0), (19, 0, 14), (57, 12, 14)),
    "explosion-ground": ((0, 0, 0), (-38, 12, 0), (19, 0, 14), (-19, 12, 14)),
    # The Zica Flamethrower sidekick's flame (weapon 780): four shots at bx -6/+6, by -7/+7 that move
    # together, quarters of one fireball, each animating 12 frames from tyrian.shp#11 172 (top left),
    # 191 (top right), 210 (bottom left), 229 (bottom right). Painted whole per frame (D214).
    "zica-flame": ((0, 0, 0), (19, 12, 0), (38, 0, 14), (57, 12, 14)),
    # The Plasma Storm sidekick's shot (weapon 88): three blended OPTION_SHAPES table sprites 22, 23, 24
    # (62x24, 65x28, 62x23) at bx -32 and by -24, 0, 28, stacked into one ring of fire (D214).
    "plasma-storm": ((0, 0, 0), (1, 0, 24), (2, 0, 52)),
}


def _pieces(base: int, pieces) -> tuple:
    """A layout of whole enemies that travel together (an asteroid assembly): (sprite index, size,
    left, top) per piece, 2 for a 2x2 enemy (its tiles index, +1, +19, +20), 1 for a 12x14 one."""
    out = []
    for index, size, x, y in pieces:
        quads = ((0, 0, 0), (1, 12, 0), (19, 0, 14), (20, 12, 14)) if size == 2 else ((0, 0, 0),)
        out += [(index - base + d, x + dx, y + dy) for d, dx, dy in quads]
    return tuple(out)


# The asteroid assemblies (newshd.shp, D239's family): painted whole, cut per piece, so the pieces meet.
# Positions are the catalogue's assemblyLayout (assembly-newshd-39, -45) and the heap's tick-80 draws
# (assembly-newshd-89's TILES on the asteroid-crags branch).
LAYOUTS.update({
    "asteroid-39": _pieces(1, ((1, 2, 0, 0), (3, 2, 24, 0), (39, 2, 0, 28), (41, 2, 24, 28))),
    "asteroid-45": _pieces(7, ((7, 2, 0, 0), (9, 2, 24, 0), (45, 2, 0, 28), (47, 2, 24, 28))),
    "asteroid-heap": _pieces(13, ((13, 2, 24, 0), (31, 1, 12, 14), (15, 1, 48, 0), (34, 1, 48, 14), (49, 2, 0, 28),
                                  (51, 2, 24, 28), (53, 2, 48, 28), (88, 1, 12, 56), (89, 2, 24, 56), (91, 2, 48, 56))),
})


def object_tiles(gd: GameData, sheet: str, index: int, size: int, layout: str | None = None) -> list[dict]:
    """The tiles a frame is drawn as: (sprite index, offset in the picture, its own pixels)."""
    offs = LAYOUTS[layout] if layout else ((0, 0, 0),) if size == 1 else ((0, 0, 0), (1, 12, 0), (19, 0, 14), (20, 12, 14))
    out = []
    for d, ox, oy in offs:
        px = gd.sprite(sheet, index + d)
        if px.shape[0] == 0 or not (px >= 0).any():
            continue
        out.append({"index": index + d, "ox": ox, "oy": oy, "pixels": px})
    return out


def picture(gd: GameData, sheet: str, index: int, size: int, layout: str | None = None) -> np.ndarray:
    """The frame as drawn: its tiles overlaid in draw order, not cropped (a tile may be taller than 14)."""
    tiles = object_tiles(gd, sheet, index, size, layout)
    h = max([size * TILE_H] + [t["oy"] + t["pixels"].shape[0] for t in tiles])
    w = max([size * TILE_W] + [t["ox"] + t["pixels"].shape[1] for t in tiles])  # a table sprite is wider
    out = np.full((h, w), -1, np.int16)
    for t in tiles:
        p = t["pixels"]
        sub = out[t["oy"]:t["oy"] + p.shape[0], t["ox"]:t["ox"] + p.shape[1]]
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
    # Explosions (newsh6.shp): the fireball's 12 frames and a big explosion's, air and ground, each
    # frame painted whole (four quarters) so its quarters meet without seams.
    ("e1-pickups-10-small", ["e1-pickups-10-small", "e1-pickups-newshp"]),
    ("e1-pickups-10", ["e1-pickups-10"]),
    ("e1-pickups-9", ["e1-pickups-9"]),
    ("e1-shots-enemy", ["e1-shots-enemy"]),
    ("e1-shots-player", ["e1-shots-player"]),
    ("e1-shots-11", ["e1-shots-11"]),
    ("rest-shots-enemy", ["rest-shots-enemy"]),
    ("rest-shots-player", ["rest-shots-player"]),
    ("rest-shots-11", ["rest-shots-11"]),
    ("rest-pickups", ["rest-pickups"]),
    ("rest-hotdog", ["rest-hotdog"]),  # D108 follow-up: the 2x2 hot-dog alone, with a lettering prompt
    ("fix-shots", ["fix-shots"]),  # D172: sidekick shots the inventory's sidekick scan missed
    # D214: the last player shots (sidekicks and specials sold in later shops), named per cell in the prompt
    ("late-shots-flame", ["late-shots-flame"]),  # Zica Flamethrower: 12 frames, each four quarters (layout zica-flame)
    ("late-shots-ordnance", ["late-shots-ordnance"]),  # missiles, rockets, bombs, mines, a disc, a laser bolt
    ("late-shots-energy", ["late-shots-energy"]),  # fireballs, chevron waves, streaks, plasma balls, the Wobbley
    ("late-shots-plasma", ["late-shots-plasma"]),  # Plasma Storm's ring of fire: three table sprites (layout plasma-storm)
    ("explosions-fireball", ["fireball"]),
    ("explosions-air", ["explosion-air"]),
    ("explosions-ground", ["explosion-ground"]),
    # The loose asteroids (newshd.shp, D239's family), with per-sheet options: "cell" px, "cols",
    # "aspect" (w, h: the sheet padded with black below/right to a ratio Gemini keeps) and "soft"
    # (each picture upscaled bicubic from one pixel per sprite pixel, so Gemini repaints rather than
    # copying the pixel blocks; the terrain sheets' lesson, docs/terrain-pipeline.html section 3).
    ("asteroids-loose", ["asteroids-loose"], {"soft": True}),
    ("asteroids-small", ["asteroids-small"], {"cols": 2, "soft": True}),
    ("asteroids-assemblies", ["asteroids-assemblies"], {"cell": 512, "aspect": (16, 9), "soft": True}),
    ("asteroids-heap", ["asteroids-heap"], {"cell": 1024, "soft": True}),
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
    for name, members, *more in SHEET_GROUPS:
        opts = more[0] if more else {}
        cell_px = opts.get("cell", CELL)
        members = [m for m in members if m in fams]  # an inventory may cover only some families
        if not members:
            continue
        cells = []  # one per distinct picture; mirrored sprites join their twin's cell
        for fam in members:
            for obj in fams[fam]["objects"]:
                for fr in obj["frames"]:
                    layout = obj.get("layout")
                    pic = picture(gd, obj["sheet"], fr, obj["size"], layout)
                    frames = [{"sheet": obj["sheet"], "index": t["index"], "sx": 1, "tx": t["ox"], "ty": t["oy"]}
                              for t in object_tiles(gd, obj["sheet"], fr, obj["size"], layout)]
                    twin = None
                    if obj["size"] == 1 and not obj.get("no_mirror"):
                        for c in cells:
                            if c["size"] == 1 and c["sheet"] == obj["sheet"]:
                                m = mirror_of(c["pic"], pic)
                                if m:
                                    twin = c
                                    twin["frames"].append({"sheet": obj["sheet"], "index": fr, "sx": -1, "tx": m[0], "ty": m[1]})
                                    break
                    if twin is None:
                        cells.append({"object": obj["name"], "family": fam, "sheet": obj["sheet"], "index": fr, "size": obj["size"], "layout": layout, "floor": obj.get("floor"), "alpha": obj.get("alpha"),
                                      "art_alpha": obj.get("art_alpha"), "steady": obj.get("steady"), "pic": pic, "frames": frames})
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
            cols = 3 if len(part) <= 9 and len(part) != 4 else 4
            if len(part) <= 3:
                cols = len(part)
            cols = opts.get("cols", cols)
            rows = math.ceil(len(part) / cols)
            CELL_ = cell_px
            biggest = max(max(trim_box(c["pic"])[2] - trim_box(c["pic"])[0], trim_box(c["pic"])[3] - trim_box(c["pic"])[1]) for c in part)
            px = max(2, min(24, int(CELL_ * FILL // biggest)))
            sw, sh_ = cols * CELL_, rows * CELL_
            if "aspect" in opts:  # pad to a ratio Gemini keeps
                aw, ah = opts["aspect"]
                sw, sh_ = max(sw, int(math.ceil(sh_ * aw / ah))), max(sh_, int(math.ceil(sw * ah / aw)))
            img = background(sw, sh_)
            entry = {"name": sheet_name, "image": f"{sheet_name}.png", "size": [sw, sh_],
                     "grid": {"rows": rows, "cols": cols, "cell": CELL_}, "scale": px, "cells": []}
            for i, c in enumerate(part):
                r, k = divmod(i, cols)
                x0, y0, x1, y1 = trim_box(c["pic"])
                # centre the visible part of the picture in the cell
                ax = k * CELL_ + (CELL_ - (x1 - x0) * px) // 2 - x0 * px
                ay = r * CELL_ + (CELL_ - (y1 - y0) * px) // 2 - y0 * px
                rgba = gd.rgba(c["pic"])
                if opts.get("soft"):  # on black, upscaled bicubic: the same geometry, no pixel blocks
                    rgb = rgba[..., :3] * (rgba[..., 3:] > 0)
                    big = np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize((rgb.shape[1] * px, rgb.shape[0] * px), Image.BICUBIC))
                    h, w = big.shape[:2]
                    region = img[ay:ay + h, ax:ax + w]
                    np.maximum(region, big, out=region)
                else:
                    big = np.kron(rgba, np.ones((px, px, 1), np.uint8))
                    h, w = big.shape[:2]
                    region = img[ay:ay + h, ax:ax + w]
                    m = big[..., 3] > 0
                    region[m] = big[..., :3][m]
                entry["cells"].append({"row": r, "col": k, "rect": [k * CELL_, r * CELL_, CELL_, CELL_], "object": c["object"], "family": c["family"],
                                       "art": {"sheet": c["sheet"], "index": c["index"], "size": c["size"], "layout": c["layout"], "x": ax, "y": ay,
                                               "w": int(c["pic"].shape[1]), "h": int(c["pic"].shape[0]), "scale": px},
                                       "search": CELL_ // 5, "frames": c["frames"], **({"floor": c["floor"]} if c["floor"] else {}), **({"alpha": c["alpha"]} if c["alpha"] else {}),
                                       **({"art_alpha": c["art_alpha"]} if c["art_alpha"] else {}), **({"steady": True} if c["steady"] else {})})
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


def original_colour(gd: GameData, pic: np.ndarray, palette: int, sigma: float = 0.6) -> np.ndarray:
    """The picture's own colours at SCALE texels per pixel, smoothed (sigma in sprite px) and
    normalised by coverage so transparent neighbours don't darken the edges: (h*8, w*8, 3) in 0..1."""
    from scipy import ndimage

    rgba = gd.rgba(pic, palette).astype(np.float32) / 255.0
    big = np.kron(rgba, np.ones((SCALE, SCALE, 1), np.float32))
    a = ndimage.gaussian_filter(big[..., 3], sigma * SCALE)
    rgb = np.stack([ndimage.gaussian_filter(big[..., c] * big[..., 3], sigma * SCALE) for c in range(3)], -1)
    return rgb / np.maximum(a, 1e-3)[..., None]


def cut_sheet(gd: GameData, sheet: dict, art: np.ndarray, palette: int) -> list[dict]:
    """Every atlas frame of one input sheet: {sheet, index, rgba (h*8, 96, 4), fit}."""
    H, W = art.shape[:2]
    rx, ry = W / sheet["size"][0], H / sheet["size"][1]
    out = []
    for cell in sheet["cells"]:
        a = cell["art"]
        pic = picture(gd, a["sheet"], a["index"], a["size"], a.get("layout"))
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
        spec = cell.get("alpha")
        silhouette = (lambda m: soft_alpha(m, spec["sigma"], spec["lo"], spec["hi"])) if spec else smooth_alpha
        alpha_pic = silhouette(pic >= 0)
        # Inventory "shadow": {"indices": [160, 161], "strength": 0.4, "sigma": 5}: the original's drop
        # shadow is pixels of those palette indices. They leave the silhouette; a soft shadow of the
        # given strength (0..1, blurred by sigma texels) stays where they were (D132: the SOH JIN key).
        shadow = cell.get("shadow")
        # Inventory "art_alpha": {"lo": 0.06, "hi": 0.14, "sigma": 1.5}: the silhouette is cut to where the
        # painting covers it (art_coverage), so the original's dark outline ring, which the registration
        # leaves out (visible_mask) and Gemini leaves as black background, isn't drawn as a black band
        # (D132's key). Never grows the silhouette. Outside the painting the colour is black, as the shadow's.
        art_spec = cell.get("art_alpha")
        cover = art_coverage(art, fit, pic.shape, art_spec) if art_spec else None
        shadow_pic = None
        if shadow:
            alpha_pic, shadow_pic = shadow_alpha(pic, silhouette, shadow, cover)
        elif cover is not None:
            alpha_pic = alpha_pic * cover
        if cover is not None:
            shadow_pic = (cover < 0.05) if shadow_pic is None else (shadow_pic | (cover < 0.05))
        # A brightness floor from the original's own colours (inventory "floor": 0..1): where the art
        # is darker than the original pixel there, it's lifted to floor x the original colour. For
        # fire, whose painting may put dark smoke where the original has a thin bright ring.
        floor = cell.get("floor")
        floor_pic = original_colour(gd, pic, palette) * floor if floor else None
        for fr in cell["frames"]:
            own = gd.sprite(fr["sheet"], fr["index"])
            h, tw = own.shape  # tw: 12 for a Sprite2 sprite, a table sprite's own width
            v, u = np.mgrid[0:h * SCALE, 0:tw * SCALE].astype(np.float32)
            u, v = (u + 0.5) / SCALE, (v + 0.5) / SCALE
            px, py = fr["sx"] * u + fr["tx"], fr.get("sy", 1) * v + fr["ty"]
            rgb = sample(art, fit["x0"] + fit["kx"] * px, fit["y0"] + fit["ky"] * py, fit["kx"] / SCALE)
            # alpha: from the picture where this tile is the picture (unmirrored, inside it), else its own
            whole = float(fr["tx"]).is_integer() and float(fr["ty"]).is_integer()
            if whole and fr["sx"] == 1 and fr.get("sy", 1) == 1 and int(fr["ty"]) + h <= pic.shape[0] and np.array_equal(pic[int(fr["ty"]):int(fr["ty"]) + h, int(fr["tx"]):int(fr["tx"]) + tw] >= 0, own >= 0):
                ty, tx = int(fr["ty"]), int(fr["tx"])
                alpha = alpha_pic[ty * SCALE:(ty + h) * SCALE, tx * SCALE:(tx + tw) * SCALE]
            else:
                alpha = silhouette(own >= 0)
            if floor_pic is not None and whole and fr["sx"] == 1:
                ty, tx = int(fr["ty"]), int(fr["tx"])
                under = floor_pic[ty * SCALE:(ty + h) * SCALE, tx * SCALE:(tx + tw) * SCALE]
                if under.shape[:2] == rgb.shape[:2]:
                    rgb = np.maximum(rgb, under)
            rgb = bleed(np.clip(rgb, 0, 1), alpha)
            if shadow_pic is not None and whole and fr["sx"] == 1:
                ty, tx = int(fr["ty"]), int(fr["tx"])
                sh = shadow_pic[ty * SCALE:(ty + h) * SCALE, tx * SCALE:(tx + tw) * SCALE]
                if sh.shape == alpha.shape:  # the shadow is black, not the body's colour bled under it
                    rgb = np.where((sh & (alpha < 0.98))[..., None], 0.0, rgb)
            rgba = np.dstack([rgb * 255, alpha * 255]).round().astype(np.uint8)
            out.append({"sheet": fr["sheet"], "index": fr["index"], "rgba": rgba, "fit": fit, "input": sheet["name"],
                        "object": cell["object"], "first": a["index"], "size": a["size"], "layout": a.get("layout"),
                        "tx": fr["tx"], "ty": fr["ty"], "steady": bool(cell.get("steady")) and whole and fr["sx"] == 1,
                        "cell": [cell["row"], cell["col"]], "mirrored": fr["sx"] < 0, "shared": fr["index"] != a["index"] and fr["sx"] > 0 and cell["art"]["size"] == 1})
    return out


def steady_frames(gd: GameData, frames: dict[tuple[str, int], dict]) -> int:
    """Inventory "steady": true (an animated object whose frames differ only in a small part: the asteroid's
    glowing vent, its crystal's twinkle): each frame painted in its own cell drifts a little from the first
    one, so the still rock shimmered as it animated. Every later frame takes the object's first frame's
    painting except where its sprite differs from the first frame's (grown by a pixel, a soft ~4-texel blend),
    so only the animated part changes. Alpha stays each frame's own. Returns the frames changed."""
    from scipy import ndimage

    objects: dict[str, dict[int, list[dict]]] = {}
    for f in frames.values():
        if f.get("steady"):
            objects.setdefault(f["object"], {}).setdefault(f["first"], []).append(f)
    changed = 0
    for name, by_frame in objects.items():
        firsts = list(by_frame)
        base = by_frame[firsts[0]]
        bf = base[0]
        base_pic = picture(gd, bf["sheet"], firsts[0], bf["size"], bf["layout"])
        base_at = {(t["tx"], t["ty"]): t for t in base}
        for first in firsts[1:]:
            pic = picture(gd, bf["sheet"], first, bf["size"], bf["layout"])
            h, w = min(pic.shape[0], base_pic.shape[0]), min(pic.shape[1], base_pic.shape[1])
            moving = np.ones(pic.shape, bool)
            moving[:h, :w] = pic[:h, :w] != base_pic[:h, :w]
            moving = ndimage.binary_dilation(moving, iterations=1)
            weight = soft_alpha(moving, 4.0, 0.15, 0.6)  # 1 where the sprite animates, 0 on the still rock
            for f in by_frame[first]:
                b = base_at.get((f["tx"], f["ty"]))
                if b is None:
                    continue
                tx, ty = int(f["tx"]) * SCALE, int(f["ty"]) * SCALE
                fh = min(f["rgba"].shape[0], b["rgba"].shape[0], weight.shape[0] - ty)
                fw = min(f["rgba"].shape[1], b["rgba"].shape[1], weight.shape[1] - tx)
                k = weight[ty:ty + fh, tx:tx + fw, None]
                own = f["rgba"][:fh, :fw, :3].astype(np.float32)
                still = b["rgba"][:fh, :fw, :3].astype(np.float32)
                rgba = f["rgba"].copy()
                rgba[:fh, :fw, :3] = (k * own + (1 - k) * still).round().astype(np.uint8)
                f["rgba"] = rgba
                changed += 1
    return changed


PAD = 8  # texels around each atlas frame (D42 asks ~8 for mipmaps), filled by extending its edge so 2x2 tiles meet cleanly


def pack(frames: list[dict], width: int = 1024) -> tuple[np.ndarray, dict]:
    """Shelf-pack frames (tallest first) into one RGBA atlas; returns it and {index: {x, y, w, h}}
    (plus "scale" for a frame drawn at a scale of its own, f["scale"], not the manifest's)."""
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
        rects[str(f["index"])] = {"x": fx, "y": fy, "w": w, "h": h, **({"scale": f["scale"]} if f.get("scale") else {}),
                                  **({"shade": f["shade"]} if f.get("shade") else {})}
    return atlas, rects


def pack_append(old: np.ndarray, old_rects: dict, frames: list[dict]) -> tuple[np.ndarray, dict]:
    """--append: the committed atlas `old` keeps every pixel and rect; `frames` are shelf-packed
    (tallest first) into the rows below its last frame, the atlas growing to the next power-of-two
    height if they don't fit. Returns the atlas and the new frames' rects only."""
    width = old.shape[1]
    top = max((r["y"] + r["h"] + PAD for r in old_rects.values()), default=0)
    order = sorted(frames, key=lambda f: (-f["rgba"].shape[0], f["index"]))
    x, y, shelf = 0, top, 0
    places = {}
    for f in order:
        h, w = f["rgba"].shape[:2]
        if x + w + 2 * PAD > width:
            x, y, shelf = 0, y + shelf, 0
        places[f["index"]] = (x + PAD, y + PAD)
        x += w + 2 * PAD
        shelf = max(shelf, h + 2 * PAD)
    need = y + shelf
    H = max(old.shape[0], 1 << max(0, (need - 1).bit_length()))
    atlas = np.zeros((H, width, 4), np.uint8)
    atlas[:old.shape[0]] = old
    rects = {}
    for f in order:
        h, w = f["rgba"].shape[:2]
        fx, fy = places[f["index"]]
        atlas[fy - PAD:fy + h + PAD, fx - PAD:fx + w + PAD] = np.pad(f["rgba"], ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
        rects[str(f["index"])] = {"x": fx, "y": fy, "w": w, "h": h, **({"scale": f["scale"]} if f.get("scale") else {}),
                                  **({"shade": f["shade"]} if f.get("shade") else {})}
    return atlas, rects


def atlas_frames(out: Path, entry: dict, keep) -> list[dict]:
    """The frames of a committed atlas (`entry`, a manifest sheet in `out`) for which keep(index,
    rect) holds, cut back out as pack() takes them; a frame's own scale (or the sheet's) comes along."""
    picked = [(int(k), r) for k, r in entry["frames"].items() if keep(int(k), r)]
    if not picked:
        return []
    img = np.asarray(Image.open(out / entry["image"]).convert("RGBA"))
    out_frames = []
    for i, r in picked:
        f = {"index": i, "rgba": img[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]].copy()}
        if r.get("scale", entry.get("scale")):
            f["scale"] = r.get("scale", entry.get("scale"))
        if r.get("shade"):
            f["shade"] = r["shade"]  # D221's gain, until `shade` measures the sheet again
        out_frames.append(f)
    return out_frames


def sheet_file(sheet_id: str) -> str:
    """'tyrian.shp#7' -> 'tyrian-shp-7.webp' ('#' can't be in a URL path)."""
    return sheet_id.replace(".", "-").replace("#", "-") + ".webp"


def dump_manifest(m: dict) -> str:
    """The atlas manifest as JSON, one frame per line."""
    lines = ["{", f'  "scale": {m["scale"]},', '  "sheets": {']
    sheets = list(m["sheets"].items())
    for i, (sid, sh) in enumerate(sheets):
        scale = f', "scale": {sh["scale"]}' if "scale" in sh else ""  # a sheet's own scale
        lines.append(f'    {json.dumps(sid)}: {{ "image": {json.dumps(sh["image"])}{scale}, "frames": {{')
        frames = list(sh["frames"].items())
        for j, (k, r) in enumerate(frames):
            lines.append(f'      {json.dumps(k)}: {json.dumps(r)}' + ("," if j < len(frames) - 1 else ""))
        lines.append("    } }" + ("," if i < len(sheets) - 1 else ""))
    lines += ["  }", "}", ""]
    return "\n".join(lines)


# --- Painted frames: art drawn here instead of cut from Gemini's ------------------------------------


def _smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def paint_tracer(gd: GameData, sheet: str, index: int, palette: int) -> np.ndarray:
    """A crisp tracer bullet (or a row of them) over the sprite: rgb (h*8, 96, 3) in 0..1.

    Each tracer runs down a column whose pixels are the sprite's brightest (its hot head); along it
    the colour is that column's own pixels, smoothly interpolated (yellow head, orange, red, dark
    red tail), and across it the colour falls to the neighbouring columns' pixels as on a round
    slug, with a white-hot core in the head and a thin lit line on its upper-left side. No flame,
    no noise: the original's colours and shape, drawn clean and hard (the alpha is the silhouette,
    as for cut frames).
    """
    own = gd.sprite(sheet, index)
    h = own.shape[0]
    col = gd.rgba(own, palette)[..., :3].astype(np.float32) / 255
    luma = (col @ np.array([0.299, 0.587, 0.114], np.float32)) * (own >= 0)
    axes = sorted({int(c) for c in np.nonzero(luma >= luma.max() * 0.95)[1]})

    def along(c: int, v: np.ndarray, fallback: np.ndarray | None = None) -> np.ndarray:
        """Column c's colours at rows v (sprite px), linear between row centres, ends held."""
        rows = np.nonzero(own[:, c] >= 0)[0] if 0 <= c < TILE_W else np.array([], int)
        if rows.size == 0:
            return fallback
        return np.stack([np.interp(v, rows + 0.5, col[rows, c, k]) for k in range(3)], -1)

    v, u = np.mgrid[0:h * SCALE, 0:TILE_W * SCALE].astype(np.float32)
    u, v = (u + 0.5) / SCALE, (v + 0.5) / SCALE
    best = np.full(u.shape, np.inf, np.float32)
    rgb = np.zeros(u.shape + (3,), np.float32)
    for c in axes:
        ds = (u - (c + 0.5)) / 1.5  # signed, -1..1 across a 3 px slug
        core = along(c, v)
        sides = [s for s in (along(c - 1, v), along(c + 1, v)) if s is not None]
        edge = np.mean(sides, 0) if sides else core * 0.6
        d = np.abs(ds)
        w = _smoothstep(0.15, 1.0, d)[..., None]
        out = core * (1 - w) + edge * w
        head = (_smoothstep(0.4, 1.2, v) * (1 - _smoothstep(2.4, 5.0, v)))[..., None]
        hot = (1 - _smoothstep(0.0, 0.45, d))[..., None] * head
        out = out * (1 - 0.7 * hot) + np.array([1.0, 0.97, 0.86], np.float32) * 0.7 * hot
        line = (1 - _smoothstep(0.0, 0.12, np.abs(ds + 0.42)))[..., None] * (1 - _smoothstep(1.0, h, v))[..., None]
        out = np.clip(out + 0.18 * line, 0, 1)
        nearer = d < best
        rgb[nearer] = out[nearer]
        best = np.where(nearer, d, best)
    return rgb


def paint_smooth(gd: GameData, sheet: str, index: int, palette: int) -> tuple[np.ndarray, np.ndarray]:
    """A small soft sprite drawn clean from its own pixels: rgb (h*8, w*8, 3) in 0..1 and alpha.

    The sprite's colours blended smoothly between pixel centres (a normalised gaussian of 0.5 px, so
    the transparent surround doesn't darken the edge). The outline is the sprite's, its corners rounded
    (a 5-texel blur cut at its middle), so the edge stays where the pixels' edge was and is drawn hard,
    like the original's opaque blit. No glow, no noise, nothing added: for sprites that are a smooth
    gradient already (a hit spark's blob, a glowing diamond shot), which Gemini repaints as something else.
    """
    from scipy import ndimage

    own = gd.sprite(sheet, index)
    m = (own >= 0).astype(np.float32)
    col = gd.rgba(own, palette)[..., :3].astype(np.float32) / 255
    big = np.kron(col * m[..., None], np.ones((SCALE, SCALE, 1), np.float32))
    weight = np.kron(m, np.ones((SCALE, SCALE), np.float32))
    pad, sigma = 3 * SCALE, 0.5 * SCALE
    blur = lambda a: ndimage.gaussian_filter(np.pad(a, pad), sigma)[pad:-pad, pad:-pad]  # noqa: E731
    w = blur(weight)
    rgb = np.stack([blur(big[..., k]) for k in range(3)], -1) / np.maximum(w, 1e-4)[..., None]
    return np.clip(rgb, 0, 1), soft_alpha(own >= 0, 5.0, 0.42, 0.58)


def paint_hit_spark(gd: GameData, sheet: str, index: int, palette: int) -> tuple[np.ndarray, np.ndarray]:
    """A shot's hit spark (explosion type 0, newsh6.shp 146-152, D247): paint_smooth of its 6x5 px blob,
    the yellow-orange core of the first frames, the red body, the dark red rim that makes it read on
    bright ground."""
    return paint_smooth(gd, sheet, index, palette)


# Frames drawn by a painter instead of cut from Gemini's art, with why. A painter returns rgb, or
# (rgb, alpha) for an outline of its own (else the silhouette, smooth_alpha).
# The Vulcan Cannon's bullets (D56): Gemini painted them as flame plumes, the Pulse-Cannon's fire
# family, so the two weapons read alike; the original draws slim tracers (yellow head, red tail).
# A shot's hit spark (D247): a 6x5 px blob, its own colours drawn clean; nothing for Gemini to add.
# The diamond shot / dark star #10 76 (D258): a soft salmon gradient Gemini painted as a white gem.
# `python tools/flat_art.py paint` appends the ones an atlas lacks.
PAINTED = {
    ("tyrian.shp#7", 67): paint_tracer,  # Vulcan Cannon, power 1-6
    ("tyrian.shp#7", 70): paint_tracer,  # Vulcan Cannon, power 7-11: two tracers side by side
    ("tyrian.shp#7", 148): paint_tracer,  # Vulcan Shot Option sidekick (weapon 11): three Vulcan tracers (D214)
    **{("newsh6.shp", i): paint_hit_spark for i in range(146, 153)},  # hit sparks, explosion type 0's 7 frames (D247)
    # A muted salmon diamond, a soft gradient from a dark rim to a pinkish centre (GEM WAR's diamond shots,
    # CORE's dark stars): Gemini painted it a pale faceted gem with a white lens flare (2026-11-18 walkthrough).
    ("tyrian.shp#10", 76): paint_smooth,
}


def painted_frame(gd: GameData, sheet: str, index: int, palette: int) -> dict:
    """A PAINTED frame, its alpha the silhouette as cut frames have it (or the painter's own)."""
    own = gd.sprite(sheet, index)
    painted = PAINTED[(sheet, index)](gd, sheet, index, palette)
    painted, alpha = painted if isinstance(painted, tuple) else (painted, smooth_alpha(own >= 0))
    rgb = bleed(np.clip(painted, 0, 1), alpha)
    rgba = np.dstack([rgb * 255, alpha * 255]).round().astype(np.uint8)
    return {"sheet": sheet, "index": index, "rgba": rgba, "fit": {"score": 1.0}, "input": "painted",
            "cell": None, "mirrored": False, "shared": False}


# --- Recolouring toward the sprite's own palette ramp (D172) ---------------------------------------
#
# A painting can come back paler, more orange or darker than its sprite (Gemini lightens fire to
# white, greys a tan glass cube, darkens one frame of a gem's twinkle). Art rule 1 says the sprite's
# colours win, so these frames are recoloured with the sprite's own palette ramp: each texel keeps its
# place in the painting's brightness order (the painting's shapes and detail stay), and takes the
# brightness the sprite has at the same place in its order (histogram matching) and the sprite's
# colour at that brightness (its ramp). tools/flat_art_recolour.json lists the frames; `cut` applies
# it to what it cuts, and `recolour` to the committed atlas.

LUMA = np.array([0.299, 0.587, 0.114], np.float32)
RECOLOUR = ROOT / "tools" / "flat_art_recolour.json"


def ramp_recolour(art: np.ndarray, art_w: np.ndarray, orig: np.ndarray, orig_w: np.ndarray, strength: float = 1.0,
                  layout: float = 0.6, bins: int = 48, keep_hue: bool = False) -> np.ndarray:
    """art (..., 3) in 0..1 recoloured by orig's ramp (see above); art_w and orig_w weight the texels
    (alpha). orig is the sprite's colours smoothed (original_colour), so its brightness spread is
    continuous and the result isn't posterised into the palette's few steps. The brightness order is
    the painting's mixed with the sprite's own at each texel by `layout` (0: the painting's alone; 1:
    the sprite's, a smoothed sprite): where a painting puts its brightest texture off the sprite's
    hot core, the core and rim still land where the sprite has them. `keep_hue`: only the brightness
    is matched, each texel keeping the painting's own hue and saturation (a grey rock with a small
    coloured part, the asteroid's vent and crystal: the ramp's mean colour per brightness would
    tint the grey with the vent's red and grey out the vent)."""
    o_l = (orig @ LUMA).ravel()
    a_l = (art @ LUMA).ravel()
    own_l = a_l.copy()
    if layout > 0:
        a_l = (1 - layout) * a_l + layout * o_l
    aw, ow = art_w.ravel().astype(np.float64), orig_w.ravel().astype(np.float64)
    keep_a, keep_o = aw > 0.02, ow > 0.5
    # art luma -> its quantile (weighted CDF) -> the sprite's luma at that quantile
    ia = np.argsort(a_l[keep_a], kind="stable")
    sa, ca = a_l[keep_a][ia], np.cumsum(aw[keep_a][ia])
    io = np.argsort(o_l[keep_o], kind="stable")
    so, co = o_l[keep_o][io], np.cumsum(ow[keep_o][io])
    q = np.interp(a_l, sa, (ca - 0.5 * aw[keep_a][ia]) / ca[-1])
    lum = np.interp(q, (co - 0.5 * ow[keep_o][io]) / co[-1], so)
    # the sprite's colour at a luma: the mean colour of its texels in each luma bin, interpolated
    lo, hi = float(so[0]), float(so[-1])
    edges = np.linspace(lo, hi + 1e-6, bins + 1)
    b = np.clip(np.digitize(o_l[keep_o], edges) - 1, 0, bins - 1)
    oc = orig.reshape(-1, 3)[keep_o]
    wsum = np.bincount(b, ow[keep_o], bins)
    centres = 0.5 * (edges[:-1] + edges[1:])
    filled = wsum > 1e-6
    ramp = np.stack([np.interp(centres, centres[filled], (np.bincount(b, ow[keep_o] * oc[:, c], bins)[filled] / wsum[filled]))
                     for c in range(3)], -1)
    col = np.stack([np.interp(lum, centres, ramp[:, c]) for c in range(3)], -1)
    if keep_hue:  # the painting's colour per unit luma (grey where it's too dark to have a hue)
        unit = art.reshape(-1, 3) / np.maximum(own_l, 1e-4)[:, None]
        unit = np.where((own_l > 0.03)[:, None], unit, 1.0)
        col = unit * lum[:, None]
    # the ramp's colour has about the target luma already; scale it there exactly (keeps the hue)
    cl = col @ LUMA
    col = col * (lum / np.maximum(cl, 1e-4))[:, None]
    col = np.clip(col, 0.0, 1.0).reshape(art.shape)
    return art * (1 - strength) + col * strength


def recolour_tiles(gd: GameData, sheet: str, first: int, size: int, tiles: dict[int, np.ndarray], palette: int,
                   strength: float = 1.0, layout: float = 0.6, sigma: float = 0.35, arrangement: str | None = None,
                   keep_hue: bool = False, ink: bool = False) -> dict[int, np.ndarray]:
    """Recolour one object's atlas tiles ({index: rgba uint8 (h*8, 96, 4)}), fitted over the whole
    object (a 2x2 pickup's four tiles get one mapping, so they still meet without seams). `arrangement`
    is a LAYOUTS name for an object whose tiles aren't blit_sprite2x2's (the Zica flame, D214).
    `keep_hue`: see ramp_recolour. `ink`: the sprite's dark outline ring (its dark pixels next to
    transparency, which art_alpha cuts away) is left out of the target ramp, so the painting's darkest
    texels match the rock's own dark limb and crevices, not the ink."""
    obj = object_tiles(gd, sheet, first, size, arrangement)
    pic = picture(gd, sheet, first, size, arrangement)
    H, W = pic.shape[0] * SCALE, pic.shape[1] * SCALE
    art = np.zeros((H, W, 3), np.float32)
    aw = np.zeros((H, W), np.float32)
    for t in obj:
        if t["index"] not in tiles:
            continue
        im = tiles[t["index"]].astype(np.float32) / 255
        h = min(im.shape[0], H - t["oy"] * SCALE)
        y0, x0 = t["oy"] * SCALE, t["ox"] * SCALE
        art[y0:y0 + h, x0:x0 + im.shape[1]] = im[:h, :, :3]
        aw[y0:y0 + h, x0:x0 + im.shape[1]] = im[:h, :, 3]
    orig = original_colour(gd, pic, palette, sigma)
    body = pic >= 0
    if ink:
        from scipy import ndimage

        dark = gd.rgba(pic, palette)[..., :3].max(-1) <= 0.16 * 255
        body = body & ~(dark & ndimage.binary_dilation(pic < 0, iterations=1))
    ow = smooth_alpha(body)
    rec = ramp_recolour(art, aw, orig, ow, strength, layout, keep_hue=keep_hue)
    out = {}
    for t in obj:
        if t["index"] not in tiles:
            continue
        im = tiles[t["index"]].copy()
        h = min(im.shape[0], H - t["oy"] * SCALE)
        y0, x0 = t["oy"] * SCALE, t["ox"] * SCALE
        im[:h, :, :3] = np.round(rec[y0:y0 + h, x0:x0 + im.shape[1]] * 255).astype(np.uint8)
        out[t["index"]] = im
    return out


def recolour_entries(config: dict) -> list[dict]:
    """The config's objects, one per (sheet, first tile, size)."""
    out = []
    for e in config.get("objects", []):
        for f in e["frames"]:
            out.append({"sheet": e["sheet"], "first": f, "size": e.get("size", 1), "strength": e.get("strength", 1.0), "layout": e.get("layout", 0.6),
                        "tiles": e.get("tiles"), "keep_hue": e.get("hue") == "art", "ink": bool(e.get("ink"))})
    return out


JOIN_ROWS = 2  # sprite px over which a beam's head or tail fades into its body's colours


def join_edges(gd: GameData, frames: dict[tuple[str, int], np.ndarray], join: dict) -> list[tuple[str, int]]:
    """A beam drawn as pieces stacked edge to edge (the Zica Laser: head, body x n, tail): frame
    join["frame"]'s top and/or bottom continue into frame join["top"] / join["bottom"]. There the
    silhouette's alpha is computed with the neighbour's pixels beyond the edge, so it doesn't fade out
    at the cut (a dark line between pieces), and a head or tail's last JOIN_ROWS rows fade into the
    body's colours at that edge, so the two meet without a seam."""
    sid, f = join["sheet"], join["frame"]
    if (sid, f) not in frames:
        return []
    rgba = frames[(sid, f)].astype(np.float32)
    own = gd.sprite(sid, f) >= 0
    h = own.shape[0]
    ext, top_pad = own, 0
    if join.get("top") is not None:
        above = gd.sprite(sid, join["top"]) >= 0
        top_pad = min(4, above.shape[0])
        ext = np.concatenate([above[-top_pad:], ext], 0)
    if join.get("bottom") is not None:
        below = gd.sprite(sid, join["bottom"]) >= 0
        ext = np.concatenate([ext, below[:min(4, below.shape[0])]], 0)
    alpha = smooth_alpha(ext)[top_pad * SCALE:(top_pad + h) * SCALE]
    rgba[..., 3] = alpha * 255
    n = JOIN_ROWS * SCALE
    for edge in ("top", "bottom"):
        g = join.get(edge)
        if g is None or g == f or (sid, g) not in frames:
            continue
        nb = frames[(sid, g)].astype(np.float32)
        # the body's colours a few texels inside its edge (its own edge texels are bled, not painted)
        row = nb[min(4, nb.shape[0] - 1), :, :3] if edge == "top" else nb[max(0, nb.shape[0] - 5), :, :3]
        t = _smoothstep(0.0, 1.0, (np.arange(n, dtype=np.float32) + 0.5) / n)  # 0 inside .. 1 at the edge
        if edge == "top":
            t = t[::-1]
            sl = slice(0, n)
        else:
            sl = slice(h * SCALE - n, h * SCALE)
        rgba[sl, :, :3] = rgba[sl, :, :3] * (1 - t[:, None, None]) + row[None] * t[:, None, None]
    frames[(sid, f)] = np.clip(np.round(rgba), 0, 255).astype(np.uint8)
    return [(sid, f)]


def apply_recolour(gd: GameData, frames: dict[tuple[str, int], np.ndarray], palette: int, config: dict) -> set[tuple[str, int]]:
    """Recolour the config's objects among frames ({(sheet, index): rgba}) and then join its beams, in place."""
    done: set[tuple[str, int]] = set()
    for e in recolour_entries(config):
        idx = [t["index"] for t in object_tiles(gd, e["sheet"], e["first"], e["size"], e["tiles"])]
        tiles = {i: frames[(e["sheet"], i)] for i in idx if (e["sheet"], i) in frames}
        if not tiles:
            continue
        for i, rgba in recolour_tiles(gd, e["sheet"], e["first"], e["size"], tiles, palette, e["strength"], e["layout"],
                                      arrangement=e["tiles"], keep_hue=e["keep_hue"], ink=e["ink"]).items():
            frames[(e["sheet"], i)] = rgba
            done.add((e["sheet"], i))
    for j in config.get("joins", []):
        done.update(join_edges(gd, frames, j))
    return done


def config_keys(gd: GameData, config: dict) -> set[tuple[str, int]]:
    """Every frame the config reads or writes."""
    keys = set()
    for e in recolour_entries(config):
        keys.update((e["sheet"], t["index"]) for t in object_tiles(gd, e["sheet"], e["first"], e["size"], e["tiles"]))
    for j in config.get("joins", []):
        keys.update((j["sheet"], k) for k in (j["frame"], j.get("top"), j.get("bottom")) if k is not None)
    return keys


def recolour_atlas(gd: GameData, out: Path, palette: int, config: dict) -> set[tuple[str, int]]:
    """Recolour (and join) the committed atlases' listed frames in place, rects unchanged. Run it
    once: it is close to idempotent, but each run re-encodes the atlas."""
    manifest = json.loads((out / "manifest.json").read_text())
    keys = config_keys(gd, config)
    atlases = {}
    frames = {}
    for sid, i in keys:
        sh = manifest["sheets"].get(sid)
        r = sh and sh["frames"].get(str(i))
        if not r:
            continue
        if sid not in atlases:
            atlases[sid] = np.asarray(Image.open(out / sh["image"]).convert("RGBA")).copy()
        frames[(sid, i)] = atlases[sid][r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]].copy()
    done = apply_recolour(gd, frames, palette, config)
    for sid, atlas in atlases.items():
        sh = manifest["sheets"][sid]
        mine = sorted(i for s, i in done if s == sid)
        for i in mine:
            r = sh["frames"][str(i)]
            atlas[r["y"] - PAD:r["y"] + r["h"] + PAD, r["x"] - PAD:r["x"] + r["w"] + PAD] = np.pad(frames[(sid, i)], ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
        Image.fromarray(atlas, "RGBA").save(out / sh["image"], "WEBP", quality=92, alpha_quality=100, method=6, exact=True)
        print(f"  {out / sh['image']}: recoloured {len(mine)} frames ({', '.join(map(str, mine))})")
    return done


def cut(gd: GameData, inputs: dict, results: Path, out: Path, palette: int, check: Path | None, merge: bool = False,
        recolour: dict | None = None, append: bool = False) -> dict:
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
    old = json.loads((out / "manifest.json").read_text()) if (out / "manifest.json").exists() else {"sheets": {}}
    if append:  # --append: the committed frames stay as they are; only frames the manifest lacks are added
        have = {(sid, int(k)) for sid, sh in old["sheets"].items() for k in sh["frames"]}
        skipped = sorted(k for k in frames if k in have)
        for k in skipped:
            del frames[k]
        if skipped:
            print(f"  append: {len(skipped)} frames already in the atlases left as they are")
    cut_sheets = {k[0] for k in frames}
    painted = [k for k in PAINTED if not merge or k[0] in cut_sheets]  # --merge: only for atlases rebuilt now
    if append:
        painted = [k for k in PAINTED if k not in have and k[0] in cut_sheets]
    for (sid, index) in painted:
        frames[(sid, index)] = painted_frame(gd, sid, index, palette)
    print(f"  painted: {len(painted)} frames ({', '.join(f'{s[7:]}:{i}' for s, i in painted)})")
    if recolour is not None:  # the sprite's palette ramp on frames painted too pale, orange or dark (D172)
        rgba = {k: f["rgba"] for k, f in frames.items()}
        changed = apply_recolour(gd, rgba, palette, recolour)
        for k in changed:
            frames[k]["rgba"] = rgba[k]
        if changed:
            print(f"  recoloured: {len(changed)} frames")
    steady = steady_frames(gd, frames)
    if steady:
        print(f"  steady: {steady} frames take their object's first painting outside the sprite's animated pixels")
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"scale": SCALE, "sheets": {}}
    # Keep the atlases this run doesn't rebuild: other tools' sheets (value_art.py), and with --merge
    # the sheets whose Gemini answers aren't at hand.
    manifest["sheets"] = {sid: sh for sid, sh in old["sheets"].items() if sid not in cut_sheets}
    for sid in sorted({k[0] for k in frames}):
        mine = [f for k, f in frames.items() if k[0] == sid]
        if append and sid in old["sheets"]:
            # Every committed frame keeps its rect and pixels (the atlas is re-encoded with the new frames).
            entry = old["sheets"][sid]
            atlas, rects = pack_append(np.asarray(Image.open(out / entry["image"]).convert("RGBA")), entry["frames"], mine)
            Image.fromarray(atlas, "RGBA").save(out / entry["image"], "WEBP", quality=92, alpha_quality=100, method=6, exact=True)
            manifest["sheets"][sid] = {**entry, "frames": dict(sorted({**entry["frames"], **rects}.items(), key=lambda kv: int(kv[0])))}
            print(f"  {out / entry['image']}: +{len(rects)} frames appended ({len(manifest['sheets'][sid]['frames'])} in all), {atlas.shape[1]}x{atlas.shape[0]}")
            continue
        # Frames another tool put in this sheet keep their place in it (value_art.py's coin values
        # in newsh6.shp, D76, which the explosions share, D80): those with a scale of their own.
        if sid in old["sheets"]:
            ours = {f["index"] for f in mine}
            mine += atlas_frames(out, old["sheets"][sid], lambda i, r: i not in ours and ("scale" in r or merge))
        # The narrower of 1024 and 2048 wide unless the wider one halves the (power-of-two) height.
        atlas, rects = min((pack(mine, w) for w in (1024, 2048)), key=lambda ar: ar[0].shape[0] * ar[0].shape[1])
        name = sheet_file(sid)
        Image.fromarray(atlas, "RGBA").save(out / name, "WEBP", quality=92, alpha_quality=100, method=6, exact=True)
        manifest["sheets"][sid] = {"image": name, "frames": dict(sorted(rects.items(), key=lambda kv: int(kv[0])))}
        print(f"  {out / name}: {len(rects)} frames, {atlas.shape[1]}x{atlas.shape[0]}")
    manifest["sheets"] = dict(sorted(manifest["sheets"].items()))
    (out / "manifest.json").write_text(dump_manifest(manifest))
    if check:
        contact_sheet(gd, sorted(frames.values(), key=lambda f: (f["sheet"], f["index"])), palette, check)
    return manifest


# --- Shade gains: the sprite's own shades under the C's palette effects (D221) ----------------------

# The renderer gives a painting the shade 0..15 a palette ramp would have at its brightness
# (spriteArtLayer.ts: Rec. 709 luma of the linear colour, to the power 1/2.2, times 15) wherever the
# C recolours by palette index: the hit flash (blit_sprite2_filter), blit_sprite_hv, the level filter
# and the smoothies' hues. The C keeps each pixel's own shade (index & 15) there. The palette's
# saturated ramps are much darker by luma than by index (the blue gem's bank 3: shade 9 has the luma
# of shade 5), so a painting true to the sprite's colours came out dark under them. A frame's "shade"
# in the manifest scales its luma shade so that its shades spread as its sprite's indices do
# (quantiles 10..95, least squares through 0); a 2x2 object (the inventory's units) gets one gain.
SHADE_SHEETS = ("tyrian.shp#10",)
SHADE_MIN_CHANGE = 0.05  # gains closer to 1 than this are left out of the manifest
SHADE_LIMITS = (0.4, 3.0)
INVENTORY = ROOT / "docs" / "roadmap" / "inventory.json"
REC709 = np.array([0.2126, 0.7152, 0.0722])


def shade_gain(gd: GameData, sheet: str, first: int, size: int, tiles: dict[int, np.ndarray]) -> float | None:
    """The gain for an object whose atlas tiles are `tiles` ({index: rgba uint8}); None if too small to tell."""
    shades, lums = [], []
    for t in object_tiles(gd, sheet, first, size):
        if t["index"] not in tiles:
            continue
        px = t["pixels"]
        shades.append((px[px >= 0] & 15).astype(np.float64))
        im = tiles[t["index"]].astype(np.float64) / 255
        keep = im[..., 3] >= 0.5  # the shader discards texels under 0.5
        lin = im[..., :3][keep] ** 2.2
        lums.append(np.maximum(lin @ REC709, 0) ** (1 / 2.2) * 15)
    s = np.concatenate(shades) if shades else np.zeros(0)
    a = np.concatenate(lums) if lums else np.zeros(0)
    if s.size < 4 or a.size < 16:
        return None
    q = np.linspace(10, 95, 18)
    qa, qs = np.percentile(a, q), np.percentile(s, q)
    if (qa * qa).sum() < 1e-6:
        return None
    return float(np.clip((qa * qs).sum() / (qa * qa).sum(), *SHADE_LIMITS))


def shade_atlas(gd: GameData, out: Path, sheets: tuple[str, ...], inventory: dict) -> None:
    """Write the listed sheets' frames' shade gains into out/manifest.json (the atlases are untouched).
    Run it again after a cut or recolour of those sheets: the gains are measured on the paintings."""
    manifest = json.loads((out / "manifest.json").read_text())
    for sid in sheets:
        sh = manifest["sheets"].get(sid)
        if not sh:
            continue
        img = np.asarray(Image.open(out / sh["image"]).convert("RGBA"))
        tiles = {int(k): img[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]] for k, r in sh["frames"].items() if "scale" not in r}
        first_of: dict[int, int] = {}  # a 2x2 object's tile -> the object's first tile
        for u in inventory.get("units", []):
            if u.get("sheet") == sid and u.get("size") == 2:
                for fl in u["frames"].values():
                    for f in fl:
                        for d in (0, 1, 19, 20):
                            first_of.setdefault(f + d, f)
        gains: dict[int, float | None] = {}
        for i in sorted(tiles):
            first = first_of.get(i, i)
            if first not in gains:
                gains[first] = shade_gain(gd, sid, first, 2 if i in first_of else 1, tiles)
        n = 0
        for k, r in sh["frames"].items():
            i = int(k)
            r.pop("shade", None)
            g = gains.get(first_of.get(i, i)) if "scale" not in r else None
            if g is not None and abs(g - 1) >= SHADE_MIN_CHANGE:
                r["shade"] = round(g, 2)
                n += 1
        print(f"  {sid}: {n} of {len(sh['frames'])} frames get a shade gain")
    (out / "manifest.json").write_text(dump_manifest(manifest))


def append_painted(gd: GameData, out: Path, palette: int, check: Path | None = None) -> None:
    """`paint`: the PAINTED frames missing from the committed atlases, painted and appended below
    their sheet's frames (pack_append: every committed frame keeps its rect and pixels)."""
    manifest = json.loads((out / "manifest.json").read_text())
    missing = [k for k in PAINTED if str(k[1]) not in manifest["sheets"].get(k[0], {}).get("frames", {})]
    if not missing:
        print("  paint: every painted frame is in the atlases")
        return
    frames = [painted_frame(gd, sid, i, palette) for sid, i in missing]
    for sid in sorted({k[0] for k in missing}):
        mine = [f for f in frames if f["sheet"] == sid]
        entry = manifest["sheets"].get(sid)
        if entry is None:
            atlas, rects = pack(mine)
            entry = {"image": sheet_file(sid), "frames": {}}
        else:
            atlas, rects = pack_append(np.asarray(Image.open(out / entry["image"]).convert("RGBA")), entry["frames"], mine)
        Image.fromarray(atlas, "RGBA").save(out / entry["image"], "WEBP", quality=92, alpha_quality=100, method=6, exact=True)
        manifest["sheets"][sid] = {**entry, "frames": dict(sorted({**entry["frames"], **rects}.items(), key=lambda kv: int(kv[0])))}
        print(f"  {out / entry['image']}: +{len(rects)} painted frames ({', '.join(sorted(rects, key=int))}), {atlas.shape[1]}x{atlas.shape[0]}")
    manifest["sheets"] = dict(sorted(manifest["sheets"].items()))
    (out / "manifest.json").write_text(dump_manifest(manifest))
    if check:
        contact_sheet(gd, frames, palette, check, cols=len(frames))


def contact_sheet(gd: GameData, frames: list[dict], palette: int, path: Path, cols: int = 6) -> None:
    """original (nearest, 8x) | remastered, for every frame, on a checker; label under each pair."""
    from PIL import ImageDraw

    fw = max(f["rgba"].shape[1] for f in frames)  # 96 texels, more for a table sprite
    cw, chh = 2 * fw + 24, max(f["rgba"].shape[0] for f in frames) + 22
    rows = math.ceil(len(frames) / cols)
    img = Image.new("RGB", (cols * cw, rows * chh), (16, 16, 20))
    yy, xx = np.mgrid[0:chh, 0:fw]
    for i, f in enumerate(frames):
        r, c = divmod(i, cols)
        x0, y0 = c * cw + 4, r * chh + 2
        own = gd.sprite(f["sheet"], f["index"])
        orig = np.kron(gd.rgba(own, palette), np.ones((SCALE, SCALE, 1), np.uint8))
        for j, im in enumerate((orig, f["rgba"])):
            h, w = im.shape[:2]
            chk = np.where(((xx[:h, :w] // 8 + yy[:h, :w] // 8) % 2)[..., None] == 1, 52, 36).astype(np.float32) * np.ones(3)
            a = im[..., 3:4].astype(np.float32) / 255
            comp = (im[..., :3] * a + chk * (1 - a)).astype(np.uint8)
            img.paste(Image.fromarray(comp), (x0 + j * (fw + 8), y0))
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
    c.add_argument("--merge", action="store_true", help="rebuild only the atlases these inputs feed (and only their painted frames); other sheets are kept either way")
    c.add_argument("--append", action="store_true", help="with --merge: keep every committed frame's rect and pixels, add only the frames the manifest lacks below them (D214)")
    r = sub.add_parser("recolour", help="apply tools/flat_art_recolour.json to the committed atlases once (cut applies it to what it cuts)")
    r.add_argument("--config", type=Path, default=RECOLOUR)
    r.add_argument("--out", type=Path, default=ROOT / "public" / "art" / "sprites")
    r.add_argument("--only", help="comma-separated sheet:index (first tiles / join frames) to apply, e.g. tyrian.shp#7:121")
    p = sub.add_parser("paint", help="append the PAINTED frames the committed atlases lack (every committed frame kept, D214's --append)")
    p.add_argument("--out", type=Path, default=ROOT / "public" / "art" / "sprites")
    p.add_argument("--check", type=Path, help="also write a contact sheet of the appended frames: original | painted")
    g = sub.add_parser("shade", help="write the frames' shade gains (D221) into the manifest; run after a cut or recolour of those sheets")
    g.add_argument("--out", type=Path, default=ROOT / "public" / "art" / "sprites")
    g.add_argument("--sheets", default=",".join(SHADE_SHEETS), help="comma-separated sheet ids (default the pickups, tyrian.shp#10)")
    g.add_argument("--inventory", type=Path, default=INVENTORY, help="for the 2x2 objects (default docs/roadmap/inventory.json)")
    args = ap.parse_args(argv)
    gd = GameData(args.data)
    if args.cmd == "shade":
        shade_atlas(gd, args.out, tuple(args.sheets.split(",")), json.loads(args.inventory.read_text()))
        return
    if args.cmd == "paint":
        append_painted(gd, args.out, args.palette, args.check)
        return
    if args.cmd == "recolour":
        config = json.loads(args.config.read_text())
        if args.only:
            want = {(o.rsplit(":", 1)[0], int(o.rsplit(":", 1)[1])) for o in args.only.split(",")}
            config = {"objects": [{**e, "frames": [f for f in e["frames"] if (e["sheet"], f) in want]} for e in config.get("objects", [])],
                      "joins": [j for j in config.get("joins", []) if (j["sheet"], j["frame"]) in want]}
        recolour_atlas(gd, args.out, args.palette, config)
        return
    if args.cmd == "sheets":
        m = build_sheets(gd, json.loads(args.inventory.read_text()), args.out)
        for sh in m["sheets"]:
            print(f"  {args.out / sh['image']}: {len(sh['cells'])} cells, {sh['grid']['rows']}x{sh['grid']['cols']}, {sh['scale']}x")
    else:
        cut(gd, json.loads(args.inputs.read_text()), args.results, args.out, args.palette, args.check, args.merge or args.append,
            json.loads(RECOLOUR.read_text()) if RECOLOUR.exists() else None, args.append)


if __name__ == "__main__":
    main()
