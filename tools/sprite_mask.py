"""A sprite's outline masks for matching a model's top view (DECISIONS.md D74, docs/agents/OUTLINE-BORDER.md).

Most Tyrian sprites draw a dark ink border, one pixel wide, round the object. The game draws its own
ink outline round every model (src/render/view.ts OUTLINE), so a model's top-view edge goes to the
INNER edge of that border: the model plus the game's ink then lands on the sprite's outer edge.
This tool finds the border and gives the masks:

  outer   every opaque pixel (the whole sprite; what models were matched to before D74)
  border  the ink pixels of the boundary ring: dark (luma < INK_LUMA) and 4-adjacent to the outside
          (transparency or the picture's edge). Where the sprite draws colour to its edge there is
          no border, and the model goes to the outer edge there.
  inner   outer minus border: what a model's top view should cover
  free    border pixels of thin parts (no part of the inner mask 2 px wide touches them): a part
          one colour pixel wide inside its ink, or drawn in ink alone, keeps at least half its
          sprite width, so these pixels count neither way in the rule's IoU

    python3 tools/sprite_mask.py <name> [<name> ...]          border survey line per sprite
    python3 tools/sprite_mask.py <name> --json                 the same as JSON, with the masks as rows
                                                              of . (transparent) o (border) # (inner)
    python3 tools/sprite_mask.py <name> --png out.png [--inner] [--scale K]   a mask as a PNG
    python3 tools/sprite_mask.py <name> --measure top.png      the rule's IoU of a top-view render

<name> is a folder of reference/models (npm run catalogue) or an assembly (assembly-newsh4-124),
composed whole from its pieces. --frame picks a sprite frame (default: the model's own frame).
--measure takes a top-view render of the model on the sprite's grid (the image is W*k x H*k for a
W x H sprite, any whole k; opaque where alpha > 127, or white where there is no alpha), as
assets/blender/proto/review_render.py and the model scripts' top views make; leave out the outline
shell and tyrian_ground rock. The accept line is `iou_rule_grid` >= 0.95 on every frame. Pure
standard library, so it runs under Blender's Python and the system's.
"""

import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "models"

#: A pixel is ink when its luma (Rec. 601) is below this. Catches the outline colours the sprites use
#: (palette 1 and 2, greys 12 and 24; each ramp's darkest steps: 16, 32, 48, 64, 80, 112, ...) and
#: not the dark shading steps above them (palette 18-19, browns of luma 28-39).
INK_LUMA = 26
#: A sprite "has a border" when at least this share of its boundary ring is ink.
CLOSED = 0.85
NONE = 0.2


# --- Loading ---------------------------------------------------------------------------------------

def _rows(frame):
    return [[int(v) for v in row.split()] for row in frame["pixels"]]


def _colors(data):
    return {int(k): tuple(v) for k, v in data["colors"].items()}


def load(name, frame=None, ref=REF):
    """(idx, colors): idx rows of palette indices (-1 transparent), colors {index: (r, g, b)}.
    A plain model's own frame (a player ship's level frame), or `frame`; an assembly composed whole
    from its pieces' layout frames (as tools/sprite_shape.py load_assembly)."""
    if name.startswith("assembly-"):
        return _load_assembly(name, ref)
    data = json.loads((Path(ref) / name / "sprite.json").read_text())
    want = frame if frame is not None else next(
        (s["frames"][0] for s in data.get("sprites") or [] if s.get("frames")), None)
    fr = next((f for f in data["frames"] if f["index"] == want), data["frames"][0])
    return _rows(fr), _colors(data)


def _load_assembly(asm, ref):
    cat = json.loads((Path(ref) / "catalogue.json").read_text())
    names = [e["name"] for e in cat if e.get("assembly") == asm]
    first = json.loads((Path(ref) / names[0] / "sprite.json").read_text())
    colors, placed = {}, []
    for e in first["assemblyLayout"]:
        if e["model"] not in names:
            continue
        data = json.loads((Path(ref) / e["model"] / "sprite.json").read_text())
        colors.update(_colors(data))
        want = int(e["frame"].split("|")[-1])
        fr = next((f for f in data["frames"] if f["index"] == want), data["frames"][0])
        placed.append((e, _rows(fr)))
    x0 = min(e["cx"] - len(px[0]) // 2 for e, px in placed)
    y0 = min(e["cy"] - len(px) // 2 for e, px in placed)
    x1 = max(e["cx"] - len(px[0]) // 2 + len(px[0]) for e, px in placed)
    y1 = max(e["cy"] - len(px) // 2 + len(px) for e, px in placed)
    idx = [[-1] * (x1 - x0) for _ in range(y1 - y0)]
    for e, px in placed:
        ox, oy = e["cx"] - len(px[0]) // 2 - x0, e["cy"] - len(px) // 2 - y0
        for y, row in enumerate(px):
            for x, v in enumerate(row):
                if v >= 0:
                    idx[oy + y][ox + x] = v
    return idx, colors


# --- Masks -----------------------------------------------------------------------------------------

def luma(rgb):
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def is_ink(index, colors):
    return index >= 0 and luma(colors[index]) < INK_LUMA


def depth(mask):
    """City-block distance of each opaque pixel from the outside (1 = the boundary ring); the
    picture's edge counts as outside. 0 where transparent."""
    h, w = len(mask), len(mask[0])
    big = h + w
    d = [[big if mask[y][x] else 0 for x in range(w)] for y in range(h)]
    for y in range(h):
        for x in range(w):
            if d[y][x]:
                up = d[y - 1][x] if y > 0 else 0
                left = d[y][x - 1] if x > 0 else 0
                d[y][x] = min(d[y][x], up + 1, left + 1)
    for y in range(h - 1, -1, -1):
        for x in range(w - 1, -1, -1):
            if d[y][x]:
                down = d[y + 1][x] if y < h - 1 else 0
                right = d[y][x + 1] if x < w - 1 else 0
                d[y][x] = min(d[y][x], down + 1, right + 1)
    return d


def _thick(mask):
    """Pixels of `mask` inside some 2x2 block of it: parts at least 2 px wide both ways."""
    h, w = len(mask), len(mask[0])
    out = [[False] * w for _ in range(h)]
    for y in range(h - 1):
        for x in range(w - 1):
            if mask[y][x] and mask[y][x + 1] and mask[y + 1][x] and mask[y + 1][x + 1]:
                out[y][x] = out[y][x + 1] = out[y + 1][x] = out[y + 1][x + 1] = True
    return out


def masks(idx, colors):
    """{"outer", "border", "inner", "free"}: rows of bools (see the module doc). `free` is the
    border pixels of thin parts, where the model may go either way: border that touches (8-way) no
    part of the inner mask 2 px wide, i.e. the ink round a part only 1 px wide inside its ink, or a
    part drawn in ink alone (antennae, legs). Such parts keep at least half their sprite width."""
    outer = [[v >= 0 for v in row] for row in idx]
    h, w = len(idx), len(idx[0])
    d = depth(outer)
    border = [[d[y][x] == 1 and is_ink(v, colors) for x, v in enumerate(row)] for y, row in enumerate(idx)]
    inner = [[o and not b for o, b in zip(ro, rb)] for ro, rb in zip(outer, border)]
    thick = _thick(inner)
    free = [[border[y][x] and not any(thick[yy][xx] for yy in range(max(0, y - 1), min(h, y + 2))
                                      for xx in range(max(0, x - 1), min(w, x + 2)))
             for x in range(w)] for y in range(h)]
    return {"outer": outer, "border": border, "inner": inner, "free": free}


def perimeter(mask):
    """Pixel edges between the mask and the outside (picture edge included)."""
    h, w = len(mask), len(mask[0])
    n = 0
    for y in range(h):
        for x in range(w):
            if not mask[y][x]:
                continue
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                yy, xx = y + dy, x + dx
                if not (0 <= yy < h and 0 <= xx < w and mask[yy][xx]):
                    n += 1
    return n


def survey(idx, colors):
    """How the sprite's border looks: the ring's ink share overall and per side, the share of the
    next layer in that is ink too (a border thicker than 1 px), and a kind."""
    outer = [[v >= 0 for v in row] for row in idx]
    h, w = len(idx), len(idx[0])
    d = depth(outer)
    ring = [(y, x) for y in range(h) for x in range(w) if d[y][x] == 1]
    layer2 = [(y, x) for y in range(h) for x in range(w) if d[y][x] == 2]
    ink = lambda yx: is_ink(idx[yx[0]][yx[1]], colors)  # noqa: E731
    share = lambda px: round(sum(map(ink, px)) / len(px), 3) if px else 0.0  # noqa: E731
    sides = {}
    for side, (dy, dx) in {"top": (-1, 0), "bottom": (1, 0), "left": (0, -1), "right": (0, 1)}.items():
        px = [(y, x) for y, x in ring
              if not (0 <= y + dy < h and 0 <= x + dx < w and outer[y + dy][x + dx])]
        sides[side] = share(px)
    full_rect = all(all(row) for row in outer)
    ring_ink = share(ring)
    kind = ("full-rect" if full_rect else "closed" if ring_ink >= CLOSED else
            "partial" if ring_ink >= NONE else "none")
    border = sum(map(ink, ring))
    free = sum(map(sum, masks(idx, colors)["free"]))
    return {"size": [w, h], "opaque_px": sum(map(sum, outer)), "ring_px": len(ring), "ring_ink": ring_ink,
            "layer2_ink": share(layer2), "sides": sides, "border_px": border, "free_px": free, "kind": kind,
            "inner_px": sum(map(sum, outer)) - border}


def iou(a, b):
    inter = sum(x and y for ra, rb in zip(a, b) for x, y in zip(ra, rb))
    union = sum(x or y for ra, rb in zip(a, b) for x, y in zip(ra, rb))
    return inter / union if union else 1.0


# --- PNG in and out (8-bit, non-interlaced) ---------------------------------------------------------

def write_png(path, mask, scale=1):
    h, w = len(mask) * scale, len(mask[0]) * scale
    raw = b"".join(b"\x00" + bytes(255 if mask[y // scale][x // scale] else 0 for x in range(w)) for y in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))  # noqa: E731
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def read_png_mask(path):
    """Rows of bools: alpha > 127, or grey/red > 127 without alpha. 8-bit, non-interlaced PNGs."""
    data = Path(path).read_bytes()
    pos, idat, w = 8, b"", 0
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        t, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        if t == b"IHDR":
            w, h, bits, ctype, _, _, inter = struct.unpack(">IIBBBBB", body)
            if bits != 8 or inter:
                raise ValueError(f"{path}: only 8-bit non-interlaced PNGs")
        elif t == b"IDAT":
            idat += body
        pos += 12 + n
    bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    stride = w * bpp
    rows, prev = [], bytearray(stride)
    for y in range(h):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = line
        ch = bpp - 1 if ctype in (4, 6) else 0
        rows.append([line[x * bpp + ch] > 127 for x in range(w)])
    return rows


def measure(m, top):
    """IoU of a top-view mask `top` (k image px per sprite px) against the outer and inner masks,
    at the render's resolution and on the sprite's grid (a sprite pixel counts as covered when at
    least half of it is), and how far the edge sits outside the inner mask on average."""
    h, w = len(m["outer"]), len(m["outer"][0])
    th, tw = len(top), len(top[0])
    k = tw // w
    if k < 1 or tw != w * k or th != h * k:
        raise ValueError(f"top view is {tw}x{th}; expected a whole multiple of the sprite's {w}x{h}")
    cov = [[sum(top[y * k + j][x * k + i] for j in range(k) for i in range(k)) / (k * k) for x in range(w)]
           for y in range(h)]
    grid = [[c >= 0.5 for c in row] for row in cov]
    out = {"k": k}
    for key in ("outer", "inner"):
        mm = m[key]
        inter = union = 0
        for y in range(th):
            for x in range(tw):
                s = mm[y // k][x // k]
                inter += s and top[y][x]
                union += s or top[y][x]
        out[f"iou_{key}"] = round(inter / union if union else 1.0, 4)
        out[f"iou_{key}_grid"] = round(iou(grid, mm), 4)
    # The rule's IoU: against the inner mask, thin parts' border pixels (free) counted neither way.
    inter = union = 0
    for y in range(th):
        for x in range(tw):
            if m["free"][y // k][x // k]:
                continue
            s = m["inner"][y // k][x // k]
            inter += s and top[y][x]
            union += s or top[y][x]
    out["iou_rule"] = round(inter / union if union else 1.0, 4)
    gi = sum(g and s for rg, rs, rf in zip(grid, m["inner"], m["free"]) for g, s, f in zip(rg, rs, rf) if not f)
    gu = sum(g or s for rg, rs, rf in zip(grid, m["inner"], m["free"]) for g, s, f in zip(rg, rs, rf) if not f)
    out["iou_rule_grid"] = round(gi / gu if gu else 1.0, 4)
    area = sum(map(sum, cov))
    inner_area = sum(map(sum, m["inner"]))
    out["model_px"] = round(area, 1)
    out["inner_px"] = inner_area
    out["outer_px"] = sum(map(sum, m["outer"]))
    # Area difference spread over the inner outline: + = the model's edge lies outside the inner mask.
    out["edge_vs_inner_px"] = round((area - inner_area) / max(1, perimeter(m["inner"])), 3)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="+")
    ap.add_argument("--frame", type=int)
    ap.add_argument("--ref", default=str(REF), help="the reference/models folder")
    ap.add_argument("--json", action="store_true", help="print JSON (with the masks as strings of . # o)")
    ap.add_argument("--png", help="write the mask to this PNG (outer, or --inner)")
    ap.add_argument("--inner", action="store_true")
    ap.add_argument("--scale", type=int, default=1)
    ap.add_argument("--measure", help="a top-view render on the sprite's grid to compare with both masks")
    a = ap.parse_args(argv)
    for name in a.names:
        idx, colors = load(name, a.frame, a.ref)
        info = survey(idx, colors)
        m = masks(idx, colors)
        if a.png:
            write_png(a.png, m["inner" if a.inner else "outer"], a.scale)
        if a.measure:
            info["measure"] = measure(m, read_png_mask(a.measure))
        if a.json:
            info["masks"] = ["".join("o" if b else "#" if o else "." for o, b in zip(ro, rb))
                             for ro, rb in zip(m["outer"], m["border"])]
            print(json.dumps({"name": name, **info}))
        else:
            s = info["sides"]
            line = (f"{name}: {info['kind']}, ring {info['ring_px']} px, {info['ring_ink']:.0%} ink "
                    f"(top {s['top']:.0%} left {s['left']:.0%} bottom {s['bottom']:.0%} right {s['right']:.0%}), "
                    f"next layer {info['layer2_ink']:.0%} ink; outer {info['opaque_px']} px, inner {info['inner_px']} px, "
                    f"thin-part border {info['free_px']} px")
            if a.measure:
                mm = info["measure"]
                line += (f"\n  top view: rule IoU {mm['iou_rule']} (grid {mm['iou_rule_grid']}); inner {mm['iou_inner']}"
                         f" (grid {mm['iou_inner_grid']}), outer {mm['iou_outer']}"
                         f" (grid {mm['iou_outer_grid']}); edge {mm['edge_vs_inner_px']:+.2f} px vs the inner mask")
            print(line)


if __name__ == "__main__":
    main(sys.argv[1:])
