"""Broken sockets (DECISIONS.md D115): the shattered stone the original's tiles paint under the caps of
TYRIAN's purple machines. numpy only (no bpy), so the same code runs in Blender
(lib_tyrbld.Structure.broken_sockets builds the geometry) and in plain Python
(`python assets/blender/tiles/lib_sockets.py --overlay out.png` draws each tile's chunks over its
art, `--maps` neutralises the concept maps under the sockets).

The original draws each cap as an enemy over a tile whose boss is already broken: an octagonal
stone split by dark cracks into angular chunks (tiles 155-157, 165, 167, 175-177). Here:

1. the cracks are polylines read off each tile's art (CRACKS); an end near the rim that points out
   of the stone runs on to it, so a crack splits the stone. The dark arc along a boss's lower
   right is its shading, not a crack (art rule 2);
2. the chunks are the boss's octagon minus those cracks and the art's darkest pits (palette 80-83),
   rasterised at 8 samples per px: each region's outline, simplified, is a chunk polygon (tile px);
3. each chunk takes the palette index its pixels mostly paint, kept to the stone's 86..89.

The geometry (lib_tyrbld): every chunk a prism with a tilted, chamfered top (the plates sag toward
the torn-out middle and burst a little outward), over a dark floor that shows in the cracks, all
under the enemies' ceiling.
"""

import math
import sys

import numpy as np

SUB = 8  # raster samples per px for the chunks
PIT_DARK = 83  # the deepest ink: holes, cut out of the chunks whole
RIM = 0.8  # pits are read inside this fraction of the boss's radius (outside: its shading)
CRACK_HALF = 0.7  # px: half a crack's width between chunks
MIN_CHUNK = 2.0  # px^2: smaller pieces are dropped (the floor shows)

#: Each boss tile's boss: its centre in the tile (px) and radius (px), read off the art. The machines
#: place their bosses where their own art puts them; the layout is read round this centre.
BOSS_AT = {155: (11.5, 12.0), 156: (11.5, 12.0), 157: (12.5, 12.0), 165: (11.5, 12.0), 167: (13.0, 12.0),
           175: (11.5, 13.0), 176: (11.0, 13.0), 177: (12.5, 13.0)}
BOSS_R = 8.5

#: The cracks each boss tile paints (polylines, tile px, x right, y down), read off the tile art at
#: 16-28x: its dark crack lines (80-85) and where its chunks' faces change. Ends inside the stone
#: stay there; ends near the rim run on to it (crack_lines). The art's pits (80-83) are cut out too.
CRACKS = {
    155: [[(11.5, 4.0), (10.6, 8.5), (10.5, 13.0), (10.8, 19.5)], [(6.0, 9.6), (10.6, 8.8)],
          [(10.6, 9.2), (13.0, 9.6), (15.5, 7.5)], [(2.6, 13.8), (5.2, 12.4)]],
    156: [[(12.0, 4.5), (13.2, 7.8), (14.4, 10.0), (14.4, 14.0), (14.6, 18.5)], [(14.4, 10.0), (16.5, 9.6), (18.8, 8.6)],
          [(9.5, 13.3), (12.0, 12.8), (14.4, 13.0)], [(3.0, 15.8), (5.2, 14.5), (7.2, 14.1)],
          [(14.5, 15.5), (17.5, 16.2), (19.8, 16.6)]],
    157: [[(12.6, 5.0), (13.2, 8.5), (13.6, 11.5)], [(13.6, 11.5), (11.0, 13.0), (9.0, 16.5), (8.5, 19.5)],
          [(13.6, 11.5), (16.5, 12.5), (19.5, 11.5)], [(4.5, 8.0), (6.5, 10.5), (9.0, 12.8), (11.0, 13.0)]],
    165: [[(3.0, 8.0), (5.5, 10.0), (8.0, 12.8)],
          [(8.0, 12.8), (11.5, 14.2), (14.5, 14.0), (17.0, 13.0), (17.5, 9.5), (16.0, 6.5), (14.5, 4.5)],
          [(8.0, 12.8), (6.0, 16.5), (4.5, 19.0)], [(14.5, 14.0), (16.5, 16.8)]],
    167: [[(13.6, 4.0), (13.2, 7.5), (11.0, 11.5)],
          [(5.0, 9.0), (8.0, 10.0), (11.0, 11.5), (13.5, 12.0), (16.0, 10.0), (19.0, 9.5)],
          [(13.5, 12.0), (14.6, 14.5), (13.5, 17.5), (12.0, 20.0)]],
    175: [[(5.5, 6.0), (8.0, 8.5), (10.8, 10.4)], [(10.8, 10.4), (14.0, 10.6), (17.0, 9.5), (19.5, 10.0)],
          [(10.8, 10.4), (10.6, 13.5), (9.6, 16.5), (8.0, 19.5)]],
    176: [[(4.5, 6.5), (7.5, 9.0), (9.6, 11.8)], [(9.6, 11.8), (12.5, 12.2), (14.8, 11.0), (16.6, 8.0), (17.5, 6.0)],
          [(9.6, 11.8), (9.2, 14.5), (9.8, 16.6), (12.5, 17.2), (15.0, 17.0)]],
    177: [[(4.0, 10.0), (7.0, 10.6), (10.0, 12.0), (12.5, 13.3)], [(16.6, 4.5), (16.8, 8.0), (16.0, 11.0), (12.5, 13.3)],
          [(12.5, 13.3), (11.5, 16.0), (12.5, 19.5)], [(12.5, 13.3), (16.0, 15.0), (19.5, 15.5)]],
}


def octagon_mask(xx, yy, cx, cy, r, angle=math.pi / 8):
    """Inside the regular octagon of vertex radius r at (cx, cy) (a vertex at `angle`, screen)."""
    a = np.arctan2(yy - cy, xx - cx) - angle
    sector = np.mod(a, math.pi / 4) - math.pi / 8
    rho = r * math.cos(math.pi / 8) / np.cos(sector)
    return np.hypot(xx - cx, yy - cy) <= rho


def octagon(cx, cy, r, angle=math.pi / 8):
    return [(cx + r * math.cos(angle + k * math.pi / 4), cy + r * math.sin(angle + k * math.pi / 4)) for k in range(8)]


def label(mask, diagonal=False):
    """Connected components: an int array (0 = background) and the count."""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    n = 0
    steps = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if diagonal else [])
    for y0, x0 in zip(*np.nonzero(mask)):
        if lab[y0, x0]:
            continue
        n += 1
        lab[y0, x0] = n
        stack = [(y0, x0)]
        while stack:
            y, x = stack.pop()
            for dy, dx in steps:
                u, v = y + dy, x + dx
                if 0 <= u < h and 0 <= v < w and mask[u, v] and not lab[u, v]:
                    lab[u, v] = n
                    stack.append((u, v))
    return lab, n


def crack_lines(tile, cx, cy, r=BOSS_R):
    """The tile's cracks (CRACKS) as segments [((x0, y0), (x1, y1)), ...] in tile px; an end that
    points out of the stone runs on to its rim (a crack splits the stone)."""
    segs = []
    for line in CRACKS[tile]:
        segs += list(zip(line, line[1:]))
    ends = {}
    for line in CRACKS[tile]:
        for p, q in ((line[0], line[1]), (line[-1], line[-2])):
            ends.setdefault(p, []).append(q)
    joined = {p for line in CRACKS[tile] for p in line[1:-1]}
    for p, qs in ends.items():
        if len(qs) != 1 or p in joined:
            continue
        p, q = np.array(p), np.array(qs[0])
        d = (p - q) / max(np.hypot(*(p - q)), 1e-6)
        out = p - (cx, cy)
        if np.hypot(*out) / r > 0.55 and float(d @ out) > 0:
            segs.append((tuple(p), tuple(p + d * r * 0.6)))
    return segs


def seg_distance(xx, yy, segs):
    """Distance from each sample to the nearest segment."""
    best = np.full(xx.shape, np.inf)
    for (x0, y0), (x1, y1) in segs:
        dx, dy = x1 - x0, y1 - y0
        ll = dx * dx + dy * dy
        t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / ll, 0, 1) if ll > 0 else 0.0
        best = np.minimum(best, np.hypot(xx - (x0 + t * dx), yy - (y0 + t * dy)))
    return best


def trace(mask):
    """The outer outline of a bool region as a closed loop of cell corners (sample units)."""
    h, w = mask.shape
    m = np.pad(mask, 1)
    edges = {}
    # Directed boundary edges, all the same way round the region (a lone cell: top leftward, left
    # side down, bottom rightward, right side up).
    for y, x in zip(*np.nonzero(m)):
        if not m[y - 1, x]:
            edges.setdefault((x + 1, y), []).append((x, y))
        if not m[y + 1, x]:
            edges.setdefault((x, y + 1), []).append((x + 1, y + 1))
        if not m[y, x - 1]:
            edges.setdefault((x, y), []).append((x, y + 1))
        if not m[y, x + 1]:
            edges.setdefault((x + 1, y + 1), []).append((x + 1, y))
    loops = []
    while edges:
        start = next(iter(edges))
        loop = [start]
        cur = start
        prev_dir = None
        while True:
            outs = edges.get(cur)
            if not outs:
                break
            if len(outs) > 1 and prev_dir is not None:
                # A saddle: turn the same way every time (keeps diagonal touches apart).
                outs.sort(key=lambda q: (prev_dir[0] * (q[1] - cur[1]) - prev_dir[1] * (q[0] - cur[0])))
            nxt = outs.pop(0)
            if not outs:
                del edges[cur]
            prev_dir = (nxt[0] - cur[0], nxt[1] - cur[1])
            cur = nxt
            if cur == start:
                break
            loop.append(cur)
        loops.append(loop)
    loop = max(loops, key=lambda l: abs(area(l)))
    return [(x - 1, y - 1) for x, y in loop]


def area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def inset(poly, d):
    """A polygon's outline moved d px inward (each corner along its bisector, mitre held to 2d)."""
    pts = np.asarray(poly, float)
    n = len(pts)
    sign = 1.0 if area(poly) > 0 else -1.0
    out = []
    for i in range(n):
        p, a, b = pts[i], pts[i - 1], pts[(i + 1) % n]
        e0 = (p - a) / max(np.hypot(*(p - a)), 1e-9)
        e1 = (b - p) / max(np.hypot(*(b - p)), 1e-9)
        n0 = np.array([-e0[1], e0[0]]) * sign
        n1 = np.array([-e1[1], e1[0]]) * sign
        m = n0 + n1
        lm = np.hypot(*m)
        if lm < 1e-6:
            m, k = n0, d
        else:
            m = m / lm
            k = min(d / max(float(m @ n0), 1e-6), 2 * d)
        out.append(tuple(p + m * k))
    return out


def simplify(poly, tol):
    """Douglas-Peucker on a closed loop."""
    pts = np.asarray(poly, float)
    n = len(pts)
    if n < 4:
        return [tuple(p) for p in pts]
    # Split at the two farthest-apart points.
    i0 = 0
    i1 = int(np.argmax(np.hypot(*(pts - pts[0]).T)))

    def dp(a):
        if len(a) < 3:
            return list(a)
        s, e = a[0], a[-1]
        d = e - s
        ll = np.hypot(*d)
        dist = np.abs(d[0] * (a[:, 1] - s[1]) - d[1] * (a[:, 0] - s[0])) / ll if ll > 0 else np.hypot(*(a - s).T)
        k = int(np.argmax(dist))
        if dist[k] > tol:
            return dp(a[:k + 1])[:-1] + dp(a[k:])
        return [s, e]

    first = dp(pts[i0:i1 + 1])
    second = dp(np.vstack([pts[i1:], pts[:1]]))
    out = first[:-1] + second[:-1]
    return [tuple(map(float, p)) for p in out]


def chunks(tile, px, cx=None, cy=None, r=BOSS_R):
    """The broken socket of one boss tile (its pixels `px`, its boss at (cx, cy) in the tile, by
    default BOSS_AT's): (chunks, segs). Each chunk: dict(poly=[(x, y), ...] tile px, index=palette
    index, centre=(x, y), area=px^2); segs: the crack segments."""
    h, w = px.shape
    if cx is None:
        cx, cy = BOSS_AT[tile]
    segs = crack_lines(tile, cx, cy, r)
    ys, xs = np.mgrid[0:h * SUB, 0:w * SUB]
    xx, yy = (xs + 0.5) / SUB, (ys + 0.5) / SUB
    stone = octagon_mask(xx, yy, cx, cy, r)
    cut = seg_distance(xx, yy, segs) <= CRACK_HALF if segs else np.zeros_like(stone)
    hh, ww = np.mgrid[0:h, 0:w] + 0.5
    pits = ((px >= 80) & (px <= PIT_DARK) & (np.hypot(ww - cx, hh - cy) <= RIM * r)).astype(float)
    # Rounded, not pixel squares: the pits upsampled, blurred over a px and cut at half.
    pit = np.repeat(np.repeat(pits, SUB, 0), SUB, 1)
    k = np.ones(SUB) / SUB
    for axis in (0, 1):
        pit = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), axis, pit)
    pit = pit > 0.5
    region = stone & ~cut & ~pit
    lab, n = label(region)
    out = []
    for k in range(1, n + 1):
        m = lab == k
        a = m.sum() / SUB ** 2
        if a < MIN_CHUNK:
            continue
        loop = simplify(trace(m), 0.3 * SUB)  # px/3: the raster's stair steps go, the shape stays
        poly = [(x / SUB, y / SUB) for x, y in loop]
        if len(poly) < 3:
            continue
        sy, sx = np.nonzero(m)
        cxk, cyk = (sx.mean() + 0.5) / SUB, (sy.mean() + 0.5) / SUB
        idx = px[sy // SUB, sx // SUB]
        idx = idx[(idx >= 86) & (idx <= 95)]
        mode = int(np.bincount(idx).argmax()) if len(idx) else 88
        out.append(dict(poly=poly, index=int(min(89, max(86, mode))), centre=(float(cxk), float(cyk)), area=float(a)))
    return out, segs


def tile_pixels(tiles_json, n):
    return np.array([[int(v) for v in r.split()] for r in tiles_json["tiles"][str(n)]["pixels"]], np.int32)


def overlay(path, scale=16):
    """Draw each boss tile with its chunks (plain Python, PIL)."""
    import json
    from pathlib import Path

    from PIL import Image, ImageDraw

    root = next(p for p in Path(__file__).resolve().parents if (p / "package.json").exists())
    data = json.loads((root / "reference/tiles/shapesz/tiles.json").read_text())
    cols = {int(k): tuple(v) for k, v in data["colors"].items()}
    tiles = list(BOSS_AT)
    sheet = Image.new("RGB", (len(tiles) * (24 * scale + 8), 2 * (28 * scale + 8)), (255, 255, 255))
    for k, n in enumerate(tiles):
        px = tile_pixels(data, n)
        cx, cy = BOSS_AT[n]
        parts, segs = chunks(n, px)
        for row in (0, 1):
            im = Image.new("RGB", (24 * scale, 28 * scale))
            dr = ImageDraw.Draw(im)
            for y in range(28):
                for x in range(24):
                    c = cols.get(int(px[y, x]), (0, 0, 0))
                    if row:
                        c = tuple(v // 2 for v in c)
                    dr.rectangle([x * scale, y * scale, x * scale + scale - 1, y * scale + scale - 1], fill=c)
            if row:
                for p in parts:
                    c = cols[p["index"]]
                    dr.polygon([(x * scale, y * scale) for x, y in p["poly"]], fill=tuple(min(255, int(v * 1.3)) for v in c), outline=(255, 230, 0))
                for (a, b) in segs:
                    dr.line([a[0] * scale, a[1] * scale, b[0] * scale, b[1] * scale], fill=(255, 60, 0), width=1)
            dr.text((4, 4), str(n), fill=(255, 0, 0))
            sheet.paste(im, (k * (24 * scale + 8), row * (28 * scale + 8)))
    sheet.save(path)
    print("wrote", path)


if __name__ == "__main__" and "--overlay" in sys.argv:
    overlay(sys.argv[sys.argv.index("--overlay") + 1])


#: The structures with broken sockets whose models are baked from concept maps (the 2x2, 2x3 and 2x5
#: blocks are exported plain: tools/build-models.sh finds no maps for tyrbld_purple_blocks.py).
ENTRIES = ("shapesz-tyrbld-purple-orb", "shapesz-tyrbld-purple-cross")


def socket_centres(tiles):
    """The broken sockets' centres (pattern px) in a pattern of tile numbers."""
    return [(c * 24 + BOSS_AT[t][0], r * 28 + BOSS_AT[t][1]) for r, row in enumerate(tiles) for c, t in enumerate(row) if t in BOSS_AT]


def neutral_maps():
    """No concept projection on the broken sockets (CLAUDE.md art rule 4, D115): after
    tools/concept_maps.py (and the structure's own map step), set the concept's detail to its
    neutral and the relief flat under every socket, so the bake gives them occlusion only. The rest
    of each structure keeps its maps."""
    import json
    from pathlib import Path

    from PIL import Image

    root = next(p for p in Path(__file__).resolve().parents if (p / "package.json").exists())
    for entry in ENTRIES:
        tiles = json.loads((root / "src/render/tileModels" / f"{entry}.json").read_text())["tiles"]
        d = root / "assets/blender/textures" / entry
        neutral = json.loads((d / "maps.json").read_text())["neutral"]
        for name, value in (("detail.png", neutral), ("height.png", 0.5)):
            im = Image.open(d / name)
            a = np.asarray(im).astype(np.float32) / 255
            h, w = a.shape[:2]
            scale = w / (len(tiles[0]) * 24)
            yy, xx = (np.mgrid[0:h, 0:w] + 0.5) / scale
            wgt = np.zeros((h, w), np.float32)
            for cx, cy in socket_centres(tiles):
                a_ = np.arctan2(yy - cy, xx - cx) - math.pi / 8
                rho = BOSS_R * math.cos(math.pi / 8) / np.cos(np.mod(a_, math.pi / 4) - math.pi / 8)
                edge = rho + 1.0 - np.hypot(xx - cx, yy - cy)  # px inside the socket grown by 1 px
                wgt = np.maximum(wgt, np.clip(edge / 1.0, 0, 1))
            wg = wgt[..., None] if a.ndim == 3 else wgt
            out = a * (1 - wg) + value * wg
            Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), mode=im.mode).save(d / name)
        print(f"{entry}: maps neutral under {len(socket_centres(tiles))} sockets")


if __name__ == "__main__" and "--maps" in sys.argv:
    neutral_maps()
