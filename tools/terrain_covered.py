#!/usr/bin/env python3
"""HD terrain for wreck tiles while their live enemy covers them (DECISIONS.md D67).

TYRIAN's dome works (assembly-newsh2-115) and carapace bunker (assembly-newsh2-119) stand on the
tiles of their own wrecks (the tyrbld-bunker-ring and -hull patterns, shapesz 320/321/330/331 and
322/323/332/333). The original's opaque sprites hid those tiles until the enemy died; the models no
longer draw the sprite's dirt, so the renderer draws a ground cell under a covered wreck from its
"covered" painting: the HD tile (D57-D60) with the wreck painted out to dirt. This makes them.

    python tools/terrain_covered.py [--work DIR] sheet
        Writes DIR/input.png (16:9): each pattern with one ring of its real map neighbours, from the
        current HD atlas, the two side by side. Give it to Gemini with the prompt it prints, and save
        the full-size answer as DIR/answer.(png|jpg|jpeg|webp).
    python tools/terrain_covered.py [--work DIR] cut
        Registers the answer to the input (scale and shift, NCC away from the wrecks), takes the
        painting over each wreck (its pixels from the original tiles, grown 12 texels, feathered),
        corrects its low frequencies to the HD tiles round it, keeps the HD tile everywhere else, and
        writes public/art/terrain/shapesz/0-covered.webp and the manifest's layer 0 "covered" rects.

Run `cut` again after `terrain_hd.py cut` (which keeps the "covered" entry but not the art behind
it): the covered tiles are recomposed from the cached answer and the new atlas.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import terrain_hd as T  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# (name, the pattern's tiles as the tileModels entry lists them)
PATTERNS = [("ring", [[320, 321], [330, 331]]), ("hull", [[322, 323], [332, 333]])]
TW, TH = 24 * 8, 28 * 8  # a tile at the atlas scale
SHEET = (1600, 900)
PROMPT = ("Edit this image. It shows two separate pictures side by side (left and right halves, split by a black bar) of "
          "painted top-down video game terrain: brown cobbled dirt ground. In the middle of each picture there is a "
          "machine wreck (left: a brass ring with grey machinery; right: a grey armoured hull with brass pipes). Remove "
          "both machines completely and replace them with plain brown cobbled dirt ground that continues the "
          "surrounding dirt seamlessly, with the same painterly style, the same pebble size, colours and lighting. No "
          "machinery, no pipes, no craters, no shadows, no new objects. Keep everything outside the machines exactly as "
          "it is: same framing, same layout, same black bar, same size.")


def atlas_tiles(out_root: Path):
    m = json.loads((out_root / "shapesz" / "manifest.json").read_text())
    layer = m["layers"]["0"]
    img = Image.open(out_root / "shapesz" / layer["image"]).convert("RGB")

    def tile(n: int) -> Image.Image:
        r = layer["tiles"][str(n)]
        return img.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
    return m, tile


def context(L, pattern, listed) -> np.ndarray:
    """The pattern's 4x4 map neighbourhood (first copy whose every neighbour has HD art)."""
    g = L.grids[0]
    ys, xs = np.nonzero(g == pattern[0][0])
    for y, x in zip(ys, xs):
        if y >= 1 and x >= 1 and y + 3 <= g.shape[0] and x + 3 <= g.shape[1]:
            nb = g[y - 1:y + 3, x - 1:x + 3]
            if (nb[1:3, 1:3] == np.array(pattern)).all() and all(int(n) in listed for n in nb.ravel()):
                return nb
    raise SystemExit(f"no copy of {pattern} with HD neighbours on the map")


def cmd_sheet(args) -> None:
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    L = T.LevelData(Path(args.data), "1-9")
    m, tile = atlas_tiles(Path(args.out))
    listed = {int(k) for k in m["layers"]["0"]["tiles"]}
    sheet = Image.new("RGB", SHEET)
    ctx = {}
    for k, (name, pattern) in enumerate(PATTERNS):
        nb = context(L, pattern, listed)
        ctx[name] = nb.tolist()
        x0 = 16 if k == 0 else SHEET[0] - 16 - 4 * TW
        for j in range(4):
            for i in range(4):
                sheet.paste(tile(int(nb[j, i])), (x0 + i * TW, 2 + j * TH))
    sheet.save(work / "input.png")
    (work / "context.json").write_text(json.dumps(ctx) + "\n")
    print(f"-> {work / 'input.png'} (16:9). Prompt:\n{PROMPT}")


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def register(ans: Image.Image, ref: np.ndarray, x0: int, mask: np.ndarray) -> Image.Image:
    """The answer's picture of one half, as a 4x4-tile image registered to the input's."""
    fx, fy = ans.width / SHEET[0], ans.height / SHEET[1]
    gray = lambda a: np.asarray(a, np.float32).mean(2)  # noqa: E731

    def score(s, sy, ox, oy, q):
        kx, ky = fx * s, fy * sy
        ax, ay = x0 * fx + ox, 2 * fy + oy
        c = gray(ans.crop((ax, ay, ax + 4 * TW * kx, ay + 4 * TH * ky)).resize((4 * TW // q, 4 * TH // q), Image.BILINEAR))
        return ncc(c[mask[::q, ::q]], gray(ref[::q, ::q])[mask[::q, ::q]])
    best = max(((score(s, sy, ox, oy, 4), s, sy, ox, oy) for s in np.linspace(0.97, 1.03, 13)
                for sy in np.linspace(0.97, 1.03, 13) for ox in range(-12, 13, 3) for oy in range(-12, 13, 3)))
    _, s, sy, ox, oy = best
    best = max(((score(s, sy, a, b, 2), s, sy, a, b) for a in np.arange(ox - 3, ox + 3.01, 0.5)
                for b in np.arange(oy - 3, oy + 3.01, 0.5)))
    v, s, sy, ox, oy = best
    print(f"  registered: ncc {v:.3f}, scale {s:.3f} x {sy:.3f}, shift {ox:+.1f}, {oy:+.1f}")
    kx, ky = fx * s, fy * sy
    ax, ay = x0 * fx + ox, 2 * fy + oy
    return ans.crop((ax, ay, ax + 4 * TW * kx, ay + 4 * TH * ky)).resize((4 * TW, 4 * TH), Image.LANCZOS)


def cmd_cut(args) -> None:
    work = Path(args.work)
    out_root = Path(args.out)
    answer = next((work / f"answer.{e}" for e in ("png", "jpg", "jpeg", "webp") if (work / f"answer.{e}").exists()), None)
    if answer is None:
        raise SystemExit(f"no answer in {work}")
    ans = Image.open(answer).convert("RGB")
    inp = np.asarray(Image.open(work / "input.png").convert("RGB"), np.float32)
    ctx = json.loads((work / "context.json").read_text())
    L = T.LevelData(Path(args.data), "1-9")
    m, tile = atlas_tiles(out_root)
    covered = {}
    for k, (name, pattern) in enumerate(PATTERNS):
        print(name)
        nb = np.array(ctx[name])
        x0 = 16 if k == 0 else SHEET[0] - 16 - 4 * TW
        # The HD tiles as they are now (the input may be older), and the wreck's pixels.
        orig = np.zeros((4 * TH, 4 * TW, 3), np.float32)
        for j in range(4):
            for i in range(4):
                orig[j * TH:(j + 1) * TH, i * TW:(i + 1) * TW] = np.asarray(tile(int(nb[j, i])), np.float32)
        wreck = np.zeros((4 * 28, 4 * 24), bool)
        for j in range(2):
            for i in range(2):
                px = L.tile(pattern[j][i])
                wreck[28 + j * 28:56 + j * 28, 24 + i * 24:48 + i * 24] = ~((px >= 16) & (px <= 21))  # not dirt
        wreck = binary_dilation(np.kron(wreck, np.ones((8, 8), bool)), iterations=12)
        ref = inp[2:2 + 4 * TH, x0:x0 + 4 * TW]
        mask = ~binary_dilation(wreck, iterations=28)
        painted = np.asarray(register(ans, ref, x0, mask), np.float32)
        # Low frequencies follow the HD tiles where the painting should match them.
        ok = (~wreck).astype(np.float32)
        w = gaussian_filter(ok, 40) + 1e-6
        for c in range(3):
            painted[..., c] += gaussian_filter((orig[..., c] - painted[..., c]) * ok, 40) / w
        inner = np.zeros(ok.shape, np.float32)
        inner[TH:3 * TH, TW:3 * TW] = 1
        wt = inner * np.clip(gaussian_filter(wreck.astype(np.float32), 6) * 1.5, 0, 1)
        out = orig * (1 - wt[..., None]) + painted * wt[..., None]
        for j in range(2):
            for i in range(2):
                covered[pattern[j][i]] = out[TH + j * TH:2 * TH + j * TH, TW + i * TW:2 * TW + i * TW]
    # Pack: 16-texel gutters, edge-extended, as terrain_hd.pack_atlas.
    cols = 4
    rows = (len(covered) + cols - 1) // cols
    cw, ch = TW + 32, TH + 32
    atlas = np.zeros((rows * ch, cols * cw, 3), np.float32)
    rects = {}
    for idx, (n, img) in enumerate(sorted(covered.items())):
        x, y = (idx % cols) * cw, (idx // cols) * ch
        atlas[y:y + ch, x:x + cw] = np.pad(img, ((16, 16), (16, 16), (0, 0)), mode="edge")
        rects[str(n)] = {"x": x + 16, "y": y + 16, "w": TW, "h": TH, "image": "0-covered.webp"}
    d = out_root / "shapesz"
    Image.fromarray(atlas.round().clip(0, 255).astype(np.uint8)).save(d / "0-covered.webp", quality=92, method=6)
    m["layers"]["0"]["covered"] = rects
    (d / "manifest.json").write_text(json.dumps(m, indent=1) + "\n")
    print(f"-> {d / '0-covered.webp'}, {len(rects)} covered tiles in {d / 'manifest.json'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--work", default=str(ROOT / "reference/terrain-hd/covered"))
    ap.add_argument("--out", default=str(ROOT / "public/art/terrain"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sheet").set_defaults(fn=cmd_sheet)
    sub.add_parser("cut").set_defaults(fn=cmd_cut)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
