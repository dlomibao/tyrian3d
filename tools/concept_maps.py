"""Texture maps for a model from its concept image (docs/art-pipeline.html, "Texturing").

    python tools/concept_maps.py <name> [--px 16] [--out assets/blender/textures]
    python tools/concept_maps.py tile:<entry> --concept <concept> [--px 8] [--concept-box x0,y0,x1,y1]

The concept (assets/blender/features/concepts/<name>.jpg) is a high-res reimagining of the sprite
that keeps its outline. This cuts it out of its background, lines its outline up with the
sprite's (reference/models/..., from `npm run catalogue`), and writes, in the sprite's own frame
(one sprite pixel = `px` texels, top-left = the sprite's top-left):

  concept.png  the registered concept in colour (for checking the fit)
  detail.png   greyscale surface detail to multiply with the palette colour: panel lines, rivets,
               grime and wear, with the concept's large-scale lighting taken out (the game lights
               the model; D39's "the sprite's lighting is not paint" applies to concepts too)
  height.png   fine relief for a normal map (band-passed luminance)
  mask.png     where the concept has the object
  maps.json    sizes and the fit

Tile models (background structures, DECISIONS.md D34): `tile:<entry>` names a pattern in
src/render/tileModels/<entry>.json (e.g. tile:shapesz-l1bld-bunker); the "sprite" is then the
pattern's tiles at 1x from reference/tiles/<shapes>/tiles.json (index 0 = empty, as are -1 cells),
the concept is assets/blender/features/concepts/<concept>.jpg, and the maps go to
assets/blender/textures/<entry>/ in the pattern's frame. --concept-box gives the object's box in the
concept by hand when its cut-out fails (a building that runs into the image's edge).

The game multiplies the detail by the live palette colour, so palette fades and the hit flash
keep working. Outside the object, and on surfaces the bake marks as steep, the detail is neutral.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprite_shape as S  # noqa: E402

NEUTRAL = 0.85  # detail value where there's no detail: the palette colour, a little darkened
CONTRAST = 2.2  # exponent on the detail's ratio to its surroundings


def foreground(rgb):
    """Mask of the object: pixels that differ from the background colour, sampled at the border
    (plain, white, black or a checkerboard), as one filled blob."""
    h, w, _ = rgb.shape
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(float)
    # A checkerboard has two background colours: take the two main clusters of the border.
    lum = border.mean(1)
    split = [border[lum <= np.median(lum)], border[lum > np.median(lum)]]
    cols = [c.mean(0) for c in split if len(c)]
    dist = np.min([np.linalg.norm(rgb.astype(float) - c, axis=2) for c in cols], axis=0)
    mask = dist > 28
    mask = ndimage.binary_opening(mask, iterations=2)
    lab, n = ndimage.label(mask)
    if n == 0:
        raise SystemExit("no object found in the concept")
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.flatnonzero(sizes >= 0.02 * sizes.max()))
    # Dark parts of a dark object on a dark background drop out: close generously before filling.
    close = max(3, int(0.02 * max(h, w)))
    return ndimage.binary_fill_holes(ndimage.binary_closing(np.pad(keep, close), iterations=close)[close:-close, close:-close])


def load_tile_pattern(entry):
    """The pixels (palette indices, -1 = empty) of a tile model's pattern, as sprite_shape's idx."""
    doc = json.loads((ROOT / "src/render/tileModels" / f"{entry}.json").read_text())
    shapes = Path(doc["shapes"]).stem  # "shapesz.dat" -> "shapesz"
    tiles = json.loads((ROOT / "reference/tiles" / shapes / "tiles.json").read_text())["tiles"]
    pattern = doc["tiles"]
    th, tw = 28, 24
    idx = np.full((len(pattern) * th, len(pattern[0]) * tw), -1, dtype=np.int32)
    for r, row in enumerate(pattern):
        for c, n in enumerate(row):
            if n < 0:
                continue
            px = np.array([[int(v) for v in line.split()] for line in tiles[str(n)]["pixels"]], dtype=np.int32)
            idx[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = np.where(px == 0, -1, px)
    return {"idx": idx}


def bbox(mask):
    ys, xs = np.nonzero(mask)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--px", type=int, default=None,
                    help="texels per sprite pixel (default 16, capped so the map is at most 1024 wide; tile: default 8, at most 4096)")
    ap.add_argument("--out", type=Path, default=ROOT / "assets/blender/textures")
    ap.add_argument("--concept", help="tile:<entry> only: the concept's name (assets/blender/features/concepts/<concept>.jpg)")
    ap.add_argument("--concept-box", help="x0,y0,x1,y1: the object's box in the concept image, instead of its cut-out")
    a = ap.parse_args()

    tile = a.name.startswith("tile:")
    if tile:
        if not a.concept:
            raise SystemExit("tile:<entry> needs --concept <name>")
        sp = load_tile_pattern(a.name[5:])
        out_name, concept_name = a.name[5:], a.concept
    else:
        sp = S.load_assembly(a.name) if a.name.startswith("assembly-") else S.load_sprite(a.name)
        out_name, concept_name = a.name, a.concept or a.name
    idx = sp["idx"]
    H, W = idx.shape
    # A building's pattern is a few hundred px across: fewer texels per px, up to 4096 on its long side.
    k = max(2, min(a.px or 8, 4096 // max(W, H))) if tile else max(4, min(a.px or 16, 1024 // max(W, H)))
    sx0, sy0, sx1, sy1 = bbox(idx >= 0)

    concept = Image.open(ROOT / "assets/blender/features/concepts" / f"{concept_name}.jpg").convert("RGB")
    rgb = np.asarray(concept)
    fg = foreground(rgb)
    if a.concept_box:
        cx0, cy0, cx1, cy1 = (int(v) for v in a.concept_box.split(","))
    else:
        cx0, cy0, cx1, cy1 = bbox(fg)

    # Affine fit: the concept's object box onto the sprite's object box (in texels).
    tw, th = W * k, H * k
    scale_x = (cx1 - cx0) / ((sx1 - sx0) * k)
    scale_y = (cy1 - cy0) / ((sy1 - sy0) * k)
    ty, tx = np.mgrid[0:th, 0:tw].astype(float) + 0.5
    src_x = cx0 + (tx - sx0 * k) * scale_x
    src_y = cy0 + (ty - sy0 * k) * scale_y
    coords = [src_y, src_x]
    reg = np.stack([ndimage.map_coordinates(rgb[..., c].astype(float), coords, order=1, mode="nearest") for c in range(3)], -1)
    concept_mask = ndimage.map_coordinates(fg.astype(float), coords, order=1, mode="constant") > 0.5
    # The object is where the sprite is: concepts keep the sprite's outline, and the sprite's mask
    # is exact where the concept's cut-out can be patchy.
    sprite_mask = np.kron(idx >= 0, np.ones((k, k), bool))
    mask = sprite_mask
    if tile:
        # A building's rim is rocks with black between them, which the model's rocks cover: take the
        # concept's object there too, a few px out from the tiles' pixels.
        mask = sprite_mask | (concept_mask & ndimage.binary_dilation(sprite_mask, iterations=3 * k))

    lum = (reg @ np.array([0.2126, 0.7152, 0.0722])) / 255.0
    lum_obj = np.where(mask, lum, np.nan)
    fill = np.nanmean(lum_obj)
    lum_f = np.where(mask, lum, fill)
    # Take out the concept's lighting: divide by a blur a couple of sprite pixels wide.
    base = ndimage.gaussian_filter(lum_f, 2.0 * k)
    ratio = lum_f / np.maximum(base, 0.03)
    # Contrast: the ratio's swings are small (panel lines are a few percent darker); exaggerate them,
    # and keep a little of the concept's mid-scale tone (a darker band, a lighter plate).
    mid = ndimage.gaussian_filter(lum_f, 0.5 * k) / max(fill, 0.05)
    detail = np.clip(NEUTRAL * (ratio ** CONTRAST) * (mid ** 0.35), 0.15, 1.0)
    detail = np.where(mask, detail, NEUTRAL)
    # Fine relief: band-pass of the luminance, from about a texel to half a sprite pixel.
    height = ndimage.gaussian_filter(lum_f, 0.6) - ndimage.gaussian_filter(lum_f, 0.5 * k)
    height = np.where(mask, height, 0.0)
    height = np.clip(0.5 + height * 4.0, 0, 1)

    out = a.out / out_name
    out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(reg.clip(0, 255).astype(np.uint8)).save(out / "concept.png")
    Image.fromarray((detail * 255).astype(np.uint8)).save(out / "detail.png")
    Image.fromarray((height * 255).astype(np.uint8)).save(out / "height.png")
    Image.fromarray((mask * 255).astype(np.uint8)).save(out / "mask.png")
    meta = {"name": out_name, "concept": concept_name, "tile": tile, "sprite_size": [W, H], "texels_per_px": k, "size": [tw, th],
            "sprite_box": [int(sx0), int(sy0), int(sx1), int(sy1)],
            "concept_box": [int(cx0), int(cy0), int(cx1), int(cy1)], "neutral": NEUTRAL,
            "fit_iou": None}
    # How well the concept's outline matches the sprite's, after the fit.
    meta["fit_iou"] = round(float((sprite_mask & concept_mask).sum() / max(1, (sprite_mask | concept_mask).sum())), 3)
    (out / "maps.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(f"{out}: {tw}x{th}, outline fit IoU {meta['fit_iou']}")


if __name__ == "__main__":
    main()
