"""Tall buildings (DECISIONS.md D82, docs/agents/TALL-BUILDINGS.md): read a structure's tiles as a
roof with a painted wall below it, say whether it counts as tall, and measure a built model against
its tiles from the game's cameras.

    python tools/tall_buildings.py analyse <shapes> '<pattern json>' [--layer N] [--ground 3,4]
    python tools/tall_buildings.py measure <shapes> '<pattern json>' <model.glb> [--layer N] [--ground 3,4]
                                           [--out DIR]

`analyse` prints the split (roof rows, wall band, foot) per column and the verdict. `measure` renders
the model in Blender (tools/tall_render.py) as the game's camera sees it at each tilt (overhead 0°,
tilted 15°, steep 32°) and at the top, centre and bottom of the screen, projected back onto the ground
plane (so it lines up with the tiles: D6 places a draw so its screen layout is the original's), plus
straight down; then it scores, against the tiles:

- `screen_iou`: the model's silhouette against the building's (roof + painted wall) mask;
- `roof_iou` / `wall_iou`: where the model's roof faces (pointing up) and wall faces land, against the
  painted roof and painted wall;
- `roof_dE` / `wall_dE`: mean CIE76 colour error of the model's flat palette colours in each region;
- `footprint_iou`: the model's section 1 px above its base, seen from straight above, against the
  footprint the split implies (the roof outline moved down to the wall's foot);
- `drift_px`: how far the roof's centre moves on screen between the top and the bottom of the screen
  at that tilt, relative to the tiles (0 for a flat tile; a tall model's parallax).

The split, used by assets/blender/tiles/lib_tall.py as well (plain numpy, no Blender):
- the building is every pixel not in the ground's palette ramps (`--ground`, palette index >> 4;
  default: the ramps that fill the pattern's border);
- in each column the roof/wall edge is the row with the largest drop in brightness from the 6 rows
  above to the 6 below (the wall is painted darker than the roof: the sprite's light comes from
  above), the drops summed over the 25 columns round it (a pillar painted down a wall is as bright as
  the roof but narrow); the foot is the column's lowest building pixel;
- the wall band is foot - edge; the roof is the building above the edge.

A structure is tall when its wall band (median over its columns) is at least TALL_WALL_PX: the game
camera can't show that much wall from any height the pass stack leaves a structure (D5: at 15° a
vertical wall shows 0.31 px per px of height at mid-screen; a ground structure may be 0.8 units, so
3 px of wall), so matching the whole sprite from straight above would stretch the roof over the
wall or turn the wall into a ramp.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
TILE_W, TILE_H = 24, 28

#: A painted wall band at least this tall (px) makes a structure tall.
TALL_WALL_PX = 6
#: ... along at least this share of the building's columns,
TALL_COVER = 0.6
#: ... about as tall everywhere ((90th - 10th percentile) / median of the band),
TALL_SPREAD = 0.5
#: ... darker than the roof by at least this much (mean luminance, 0-1),
TALL_DARKER = 0.08
#: ... with detail that runs up and down (brightness changes across the wall / down it).
TALL_VERTICAL = 1.0
#: The roof must be at least this much brighter than the wall (0-1 luminance) for a split to count.
EDGE_CONTRAST = 0.05
EDGE_WINDOW = 6
#: Columns whose scores are summed to place the edge (about a tile).
EDGE_SPAN = 25

#: The game cameras (src/render/view.ts fitCamera on the playfield, scripts in this file's docstring):
#: camera position relative to the playfield's centre on the ground, in units (y up, z toward the
#: screen's bottom).
CAMERAS = {
    "overhead": (0.0, 21.06, 0.0),
    "tilted": (0.0, 19.47, 5.96),
    "steep": (0.0, 14.37, 10.72),
}
#: Screen rows (playfield px from its top) the measures are taken at.
SCREEN_ROWS = {"top": 30, "centre": 92, "bottom": 154}


def load_tiles(shapes):
    path = ROOT / "reference" / "tiles" / shapes / "tiles.json"
    if not path.exists():
        raise SystemExit(f"{path} is missing: run `TILES_SHAPES={shapes[6:]} npm run tiles`")
    data = json.loads(path.read_text())
    colors = {int(k): tuple(v) for k, v in data["colors"].items()}
    tiles = {int(n): np.array([[int(v) for v in r.split()] for r in t["pixels"]], dtype=np.int32) for n, t in data["tiles"].items()}
    return tiles, colors


def pattern_grid(shapes, pattern, layer=0):
    """The pattern's pixels as palette indices (-1: nothing; index 0 on layers 1-2)."""
    tiles, colors = load_tiles(shapes)
    rows, cols = len(pattern), len(pattern[0])
    out = np.full((rows * TILE_H, cols * TILE_W), -1, dtype=np.int32)
    for r, row in enumerate(pattern):
        for c, n in enumerate(row):
            if n < 0:
                continue
            px = tiles[n].copy()
            if layer > 0:
                px[px == 0] = -1
            out[r * TILE_H:(r + 1) * TILE_H, c * TILE_W:(c + 1) * TILE_W] = px
    return out, colors


def luminance(grid, colors):
    lum = np.zeros(256)
    for i, (r, g, b) in colors.items():
        lum[i] = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return np.where(grid >= 0, lum[np.clip(grid, 0, 255)], 0.0)


def ground_ramps(grid):
    """The palette ramps (index >> 4) that fill the pattern's border: the ground round a building."""
    border = np.concatenate([grid[0], grid[-1], grid[:, 0], grid[:, -1]])
    border = border[border >= 0] >> 4
    if len(border) == 0:
        return set()
    ramps, counts = np.unique(border, return_counts=True)
    return {int(r) for r, c in zip(ramps, counts) if c >= 0.15 * len(border)}


def big_components(mask, share=0.1, least=12):
    """The 4-connected components of a bool mask with at least `share` of the biggest's pixels (and
    `least` px): a building and its big parts, not specks of the ground's colours."""
    h, w = mask.shape
    label = np.zeros((h, w), np.int32)
    sizes = {}
    n = 0
    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0, x0] or label[y0, x0]:
                continue
            n += 1
            stack, size = [(y0, x0)], 0
            label[y0, x0] = n
            while stack:
                y, x = stack.pop()
                size += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not label[yy, xx]:
                        label[yy, xx] = n
                        stack.append((yy, xx))
            sizes[n] = size
    if not sizes:
        return mask
    big = max(sizes.values())
    keep = [k for k, v in sizes.items() if v >= max(least, share * big)]
    return np.isin(label, keep)


def split(grid, colors, ground=None):
    """Roof, wall and footprint of a building pattern (module docstring). Returns a dict of masks
    and per-column rows (-1 where a column has no building)."""
    ground = ground_ramps(grid) if ground is None else set(ground)
    building = (grid >= 0) & ~np.isin(grid >> 4, list(ground))
    building = big_components(building)
    # Fill holes along each column (dark windows in the ground's ramp stay building).
    h, w = grid.shape
    top = np.full(w, -1)
    foot = np.full(w, -1)
    for x in range(w):
        ys = np.nonzero(building[:, x])[0]
        if len(ys) >= 3:
            top[x], foot[x] = ys.min(), ys.max() + 1
            building[ys.min():ys.max() + 1, x] = True
    lum = luminance(grid, colors)
    # Smooth across 3 columns so a single dark pixel doesn't pick the edge.
    sm = lum.copy()
    sm[:, 1:-1] = (lum[:, :-2] + lum[:, 1:-1] + lum[:, 2:]) / 3
    # Score every row of every column: the drop in brightness from the rows above to the rows below.
    k = EDGE_WINDOW
    drop = np.full((h, w), np.nan)
    for x in range(w):
        if top[x] < 0:
            continue
        for y in range(top[x] + 3, foot[x] - 2):
            drop[y, x] = sm[max(top[x], y - k):y, x].mean() - sm[y:min(foot[x], y + k), x].mean()
    # Sum the scores over a tile's width of columns: a roof's edge runs straight along the building
    # (a pillar painted down the wall is as bright as the roof, but only a few columns wide).
    filled = np.nan_to_num(drop, nan=0.0)
    count = np.isfinite(drop).astype(float)
    r = EDGE_SPAN // 2
    csum = np.cumsum(np.pad(filled, ((0, 0), (r + 1, r))), axis=1)
    ccnt = np.cumsum(np.pad(count, ((0, 0), (r + 1, r))), axis=1)
    wide = (csum[:, 2 * r + 1:] - csum[:, :-2 * r - 1]) / np.maximum(1, ccnt[:, 2 * r + 1:] - ccnt[:, :-2 * r - 1])
    edge = np.full(w, -1)
    score = np.zeros(w)
    for x in range(w):
        if top[x] < 0:
            continue
        ys = np.arange(top[x] + 3, max(top[x] + 3, foot[x] - 2))
        if len(ys) == 0:
            continue
        y = ys[int(np.argmax(wide[ys, x]))]
        if wide[y, x] > EDGE_CONTRAST:
            edge[x], score[x] = y, wide[y, x]
    valid = edge >= 0
    roof = np.zeros_like(building)
    wall = np.zeros_like(building)
    for x in range(w):
        if top[x] < 0:
            continue
        e = edge[x] if edge[x] >= 0 else foot[x]
        roof[top[x]:e, x] = building[top[x]:e, x]
        wall[e:foot[x], x] = building[e:foot[x], x]
    band = np.where(valid & (edge >= 0), foot - edge, 0)
    cols = band > 0
    wall_px = float(np.median(band[cols])) if cols.any() else 0.0
    roof_px = float(np.median((edge - top)[cols])) if cols.any() else float(np.median((foot - top)[top >= 0])) if (top >= 0).any() else 0.0
    # The footprint: the roof outline moved down by each column's wall band (the building stands
    # where its painted wall meets the ground).
    footprint = np.zeros_like(building)
    for x in range(w):
        if top[x] < 0:
            continue
        shift = band[x] if band[x] > 0 else 0
        ys = np.nonzero(roof[:, x])[0] if band[x] > 0 else np.nonzero(building[:, x])[0]
        ys = ys + shift
        ys = ys[ys < h]
        footprint[ys, x] = True
    return {
        "building": building, "roof": roof, "wall": wall, "footprint": footprint,
        "top": top, "edge": edge, "foot": foot, "band": band,
        "wall_px": wall_px, "roof_px": roof_px, "ground": sorted(ground),
        "contrast": float(np.median(score[cols])) if cols.any() else 0.0,
        **verdict(building, roof, wall, band, cols, lum, wall_px),
    }


def verdict(building, roof, wall, band, cols, lum, wall_px):
    """Whether the split is a painted wall under a roof (module docstring): a band of wall at least
    TALL_WALL_PX tall along most of the building's width, about as tall everywhere, darker than the
    roof, and drawn as a wall (its detail runs up and down: pillars, slats, windows' jambs)."""
    built = (building.any(axis=0)).sum()
    cover = float(cols.sum() / built) if built else 0.0
    b = band[cols]
    spread = float((np.percentile(b, 90) - np.percentile(b, 10)) / max(1.0, np.median(b))) if cols.any() else 9.0
    darker = float(lum[roof].mean() - lum[wall].mean()) if roof.any() and wall.any() else 0.0
    # Detail that runs up and down: brightness changes more across the wall than down it.
    inner = wall[1:-1, 1:-1] & wall[:-2, 1:-1] & wall[2:, 1:-1] & wall[1:-1, :-2] & wall[1:-1, 2:]
    gx = np.abs(lum[1:-1, 2:] - lum[1:-1, :-2])[inner]
    gy = np.abs(lum[2:, 1:-1] - lum[:-2, 1:-1])[inner]
    vertical = float(gx.mean() / max(1e-6, gy.mean())) if inner.any() else 0.0
    tall = (wall_px >= TALL_WALL_PX and cover >= TALL_COVER and spread <= TALL_SPREAD and darker >= TALL_DARKER
            and vertical >= TALL_VERTICAL)
    return {"tall": bool(tall), "cover": round(cover, 2), "spread": round(spread, 2), "darker": round(darker, 3),
            "vertical": round(vertical, 2)}


def ascii_split(s):
    """The split as text: R roof, W wall, F footprint only, . ground; one char per px."""
    h, w = s["building"].shape
    lines = []
    for y in range(h):
        row = []
        for x in range(w):
            if s["roof"][y, x]:
                row.append("R")
            elif s["wall"][y, x]:
                row.append("W")
            elif s["building"][y, x]:
                row.append("b")
            else:
                row.append(".")
        lines.append("".join(row))
    return "\n".join(lines)


def summary(s):
    return {"tall": s["tall"], "wall_px": s["wall_px"], "roof_px": s["roof_px"], "contrast": round(s["contrast"], 3),
            "cover": s["cover"], "spread": s["spread"], "darker": s["darker"], "vertical": s["vertical"],
            "ground_ramps": s["ground"], "building_px": int(s["building"].sum())}


# --- Measuring a model ---------------------------------------------------------------------------

def lab(rgb):
    rgb = np.asarray(rgb, dtype=float) / 255
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 1.0


def measure(shapes, pattern, glb, layer=0, ground=None, out=None, scale=4):
    """Render the model's views (tools/tall_render.py) and score them (module docstring)."""
    from PIL import Image

    grid, colors = pattern_grid(shapes, pattern, layer)
    s = split(grid, colors, ground)
    h, w = grid.shape
    out = Path(out or ROOT / ".shape" / "tall" / Path(glb).stem)
    out.mkdir(parents=True, exist_ok=True)
    views = [("top", "ortho", 0)] + [(f"{cam}-{row}", cam, SCREEN_ROWS[row]) for cam in CAMERAS for row in SCREEN_ROWS]
    spec = {"glb": str(Path(glb).resolve()), "w": w, "h": h, "scale": scale, "out": str(out), "colors": {str(k): v for k, v in colors.items()},
            "views": [{"name": n, "camera": list(CAMERAS[c]) if c in CAMERAS else None, "screen_row": r} for n, c, r in views]}
    (out / "views.json").write_text(json.dumps(spec))
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python", str(ROOT / "tools" / "tall_render.py"), "--", str(out / "views.json")],
                       capture_output=True, text=True)
    if r.returncode != 0 or "Traceback" in r.stdout + r.stderr:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit("tall_render.py failed")
    rgb_of = np.zeros((256, 3))
    for i, c in colors.items():
        rgb_of[i] = c
    sprite_lab = lab(rgb_of[np.clip(grid, 0, 255)])
    results = {"split": summary(s)}
    centres = {}
    for name, cam, row in views:
        img = np.asarray(Image.open(out / f"{name}.png").convert("RGBA")).astype(float)
        # Down to sprite px: a pixel is the model's when most of its samples are covered.
        img = img.reshape(h, scale, w, scale, 4).mean(axis=(1, 3))
        cover = img[..., 3] > 127
        kind = np.asarray(Image.open(out / f"{name}-kind.png").convert("RGB")).astype(int).reshape(h, scale, w, scale, 3)
        kind = np.round(kind.mean(axis=(1, 3)) / 255).astype(int)
        roof_faces = cover & (kind[..., 0] > 0)  # red (or magenta, at the base): faces pointing up
        wall_faces = cover & (kind[..., 1] > 0)  # green (or cyan): walls
        model_lab = lab(img[..., :3])
        de = np.linalg.norm(model_lab - sprite_lab, axis=-1)
        m = {
            "screen_iou": round(iou(cover, s["building"]), 3),
            "roof_iou": round(iou(roof_faces, s["roof"]), 3),
            "wall_iou": round(iou(wall_faces, s["wall"]), 3),
            "roof_dE": round(float(de[s["roof"] & cover].mean()) if (s["roof"] & cover).any() else 99.0, 1),
            "wall_dE": round(float(de[s["wall"] & cover].mean()) if (s["wall"] & cover).any() else 99.0, 1),
        }
        ys, xs = np.nonzero(roof_faces)
        centres[name] = (float(ys.mean()), float(xs.mean())) if len(ys) else None
        results[name] = m
    foot = np.asarray(Image.open(out / "foot.png").convert("RGBA")).astype(float).reshape(h, scale, w, scale, 4).mean(axis=(1, 3))[..., 3] > 127
    results["footprint_iou"] = round(iou(foot, s["footprint"]), 3)
    for cam in CAMERAS:
        a, b = centres.get(f"{cam}-top"), centres.get(f"{cam}-bottom")
        results[f"{cam}-drift_px"] = round(abs(a[0] - b[0]), 1) if a and b else None
    (out / "metrics.json").write_text(json.dumps(results, indent=1))
    return results, s


def main(argv):
    if len(argv) < 3 or argv[0] not in ("analyse", "measure"):
        raise SystemExit(__doc__)
    shapes, pattern = argv[1], json.loads(argv[2])
    layer = int(argv[argv.index("--layer") + 1]) if "--layer" in argv else 0
    ground = [int(v) for v in argv[argv.index("--ground") + 1].split(",")] if "--ground" in argv else None
    if argv[0] == "analyse":
        grid, colors = pattern_grid(shapes, pattern, layer)
        s = split(grid, colors, ground)
        print(ascii_split(s))
        print(json.dumps(summary(s)))
    else:
        out = argv[argv.index("--out") + 1] if "--out" in argv else None
        results, _ = measure(shapes, pattern, argv[3], layer, ground, out)
        print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
