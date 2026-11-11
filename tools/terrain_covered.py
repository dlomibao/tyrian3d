#!/usr/bin/env python3
"""HD terrain for wreck tiles while their live enemy covers them (DECISIONS.md D86).

TYRIAN's dome works (assembly-newsh2-115) and carapace bunker (assembly-newsh2-119) stand on the
tiles of their own wrecks (the tyrbld-bunker-ring and -hull patterns, shapesz 320/321/330/331 and
322/323/332/333), and the rock outcrop (assembly-newshe-39) on the tyrbld-wreck crater (340-342,
350-352). The original's opaque sprites hid those tiles until the enemy died; the models no longer
draw the sprite's dirt, so the renderer draws a ground cell under a covered wreck from its "covered"
painting: the HD tile (D57-D60) with the wreck painted out to dirt. DELIANI's pillar ends
(newshc-55) and twin pillar base (assembly-newshc-283) stand on plain floor tiles with a machine
painted on them (585, 584), which their sprites' floor hid until D130 dropped it (D139): the same,
the machine painted out to the floor. This makes them, one Gemini request per set (SETS: "bunkers",
"wreck", "deliani").

    python tools/terrain_covered.py [--work DIR] sheet SET
        Writes DIR/<set's work>/input.png: each of the set's patterns with one ring of its real map
        neighbours, from the current HD atlas (two side by side, or one centred). Give it to Gemini
        with the prompt it prints, at the sheet's aspect ratio, and save the full-size answer as
        DIR/<set's work>/answer.(png|jpg|jpeg|webp).
    python tools/terrain_covered.py [--work DIR] cut
        For every set: registers the answer to the input (scale and shift, NCC away from the
        wrecks), takes the painting over each wreck (its non-dirt pixels from the original tiles, or
        for a "whole" set the pattern's whole area, grown 12 texels, feathered), corrects its low
        frequencies to the HD tiles round it, keeps the HD tile everywhere else; then writes each set's
        atlas (0-covered.webp: bunkers and wreck; 0-covered-deliani.webp) and the manifest's layer 0
        "covered" rects. `cut --set SET` recomposes only that set (and only its atlas changes).

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
TW, TH = 24 * 8, 28 * 8  # a tile at the atlas scale
BUNKERS_PROMPT = ("Edit this image. It shows two separate pictures side by side (left and right halves, split by a black bar) of "
                  "painted top-down video game terrain: brown cobbled dirt ground. In the middle of each picture there is a "
                  "machine wreck (left: a brass ring with grey machinery; right: a grey armoured hull with brass pipes). Remove "
                  "both machines completely and replace them with plain brown cobbled dirt ground that continues the "
                  "surrounding dirt seamlessly, with the same painterly style, the same pebble size, colours and lighting. No "
                  "machinery, no pipes, no craters, no shadows, no new objects. Keep everything outside the machines exactly as "
                  "it is: same framing, same layout, same black bar, same size.")
WRECK_PROMPT = ("Edit this image. It shows painted top-down video game terrain: brown cobbled dirt ground, with a black scorched "
                "crater full of grey machine wreckage in the middle. Remove the crater, the scorch marks and the wreckage "
                "completely and replace them with plain brown cobbled dirt ground that continues the surrounding dirt "
                "seamlessly, with the same painterly style, the same pebble size and pattern, colours and lighting. No "
                "machinery, no debris, no craters, no dark patches, no shadows, no new objects. Keep everything else exactly as "
                "it is: same framing, same layout, same size.")
DELIANI_PROMPT = ("Edit this image. It shows two separate pictures side by side (left and right halves, split by a black bar) of "
                  "painted top-down video game terrain seen straight down: a dark blue-grey sci-fi metal floor of riveted panels "
                  "and grooves. In the middle of each picture there is a grey machine part with red hatches and its dark shadow "
                  "(left: a grey pod foot with a red hatch; right: a round grey socket with red lights). Remove both machines and "
                  "their shadows completely and replace them with plain blue-grey metal floor panels that continue the surrounding "
                  "floor pattern seamlessly, with the same painterly style, panel size, colours and lighting. No machinery, no red, "
                  "no holes, no shadows, no new objects. Keep everything outside the machines exactly as it is: same framing, same "
                  "layout, same black bar, same size.")
#: DELIANI's floor colours (shapesz on 1-5: the blue-grey ramp 96-109 and 48); the rest of 584/585 is the machine.
DELIANI_FLOOR = [48, *range(96, 110)]
# Each set is one Gemini request: its patterns (name, the pattern's tiles as the tileModels entry lists
# them), each shown with one ring of its real map neighbours, on a sheet of this size. "whole": the
# painting replaces the pattern's whole area (a wreck that fills it, scorched dirt and all), not only its
# non-dirt pixels.
# "level": the map the neighbours come from; "ground": the palette indices that are ground (default
# TYRIAN's dirt ramp 16-21; the rest of a cell is what's painted out); "grow": texels the painted area
# grows round those pixels; "image": the set's atlas.
SETS = {
    "bunkers": {"work": "covered", "sheet": (1600, 900), "prompt": BUNKERS_PROMPT, "whole": False,
                "patterns": [("ring", [[320, 321], [330, 331]]), ("hull", [[322, 323], [332, 333]])]},
    # tyrbld-wreck (and its -cut variant): under the rock outcrop (assembly-newshe-39), ticks ~1320-2100.
    "wreck": {"work": "covered-wreck", "sheet": (1024, 1024), "prompt": WRECK_PROMPT, "whole": True,
              "patterns": [("wreck", [[340, 341, 342], [350, 351, 352]])]},
    # DELIANI (1-5): the pillar end's tile (585, under newshc-55) and the twin pillar base's (584, under
    # newshc-283/267), D139. Grown 3 px: the machines' painted shadows go too.
    "deliani": {"work": "covered-deliani", "sheet": (1600, 900), "prompt": DELIANI_PROMPT, "whole": False,
                "level": "1-5", "ground": DELIANI_FLOOR, "grow": 24, "image": "0-covered-deliani.webp",
                "patterns": [("pillar-end", [[585]]), ("pillar-base", [[584]])]},
}


def atlas_tiles(out_root: Path):
    m = json.loads((out_root / "shapesz" / "manifest.json").read_text())
    layer = m["layers"]["0"]
    images = {}

    def tile(n: int) -> Image.Image:
        r = layer["tiles"][str(n)]
        name = r.get("image", layer["image"])  # a rect may name its own atlas (0-2.webp)
        if name not in images:
            images[name] = Image.open(out_root / "shapesz" / name).convert("RGB")
        return images[name].crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
    return m, tile


def context(L, pattern, listed, avoid=()) -> np.ndarray:
    """The pattern's map neighbourhood, one ring round it: the first copy whose every neighbour has HD
    art, preferring one with the fewest neighbours in `avoid` (other machines to paint out)."""
    g = L.grids[0]
    pr, pc = len(pattern), len(pattern[0])
    ys, xs = np.nonzero(g == pattern[0][0])
    found = []
    for y, x in zip(ys, xs):
        if y >= 1 and x >= 1 and y + pr + 1 <= g.shape[0] and x + pc + 1 <= g.shape[1]:
            nb = g[y - 1:y + pr + 1, x - 1:x + pc + 1]
            if (nb[1:1 + pr, 1:1 + pc] == np.array(pattern)).all() and all(int(n) in listed for n in nb.ravel()):
                found.append(nb)
    if not found:
        raise SystemExit(f"no copy of {pattern} with HD neighbours on the map")
    return min(found, key=lambda nb: int(np.isin(nb, list(avoid)).sum()) - int(np.isin(np.array(pattern), list(avoid)).sum()))


def layout(spec) -> list[tuple[int, int]]:
    """Each pattern's picture's top-left on the sheet: two at the sheet's sides (2 px down), one centred."""
    W, H = spec["sheet"]
    pats = spec["patterns"]
    if len(pats) == 1:
        p = pats[0][1]
        return [((W - (len(p[0]) + 2) * TW) // 2, (H - (len(p) + 2) * TH) // 2)]
    return [(16, 2) if k == 0 else (W - 16 - (len(p[0]) + 2) * TW, 2) for k, (_, p) in enumerate(pats)]


def cmd_sheet(args) -> None:
    spec = SETS[args.set]
    work = Path(args.work) / spec["work"]
    work.mkdir(parents=True, exist_ok=True)
    L = T.LevelData(Path(args.data), spec.get("level", "1-9"))
    m, tile = atlas_tiles(Path(args.out))
    listed = {int(k) for k in m["layers"]["0"]["tiles"]}
    sheet = Image.new("RGB", spec["sheet"])
    ctx = {}
    own = {int(n) for _, p in spec["patterns"] for row in p for n in row}
    for (name, pattern), (x0, y0) in zip(spec["patterns"], layout(spec)):
        nb = context(L, pattern, listed, own)
        ctx[name] = nb.tolist()
        for j in range(nb.shape[0]):
            for i in range(nb.shape[1]):
                sheet.paste(tile(int(nb[j, i])), (x0 + i * TW, y0 + j * TH))
    sheet.save(work / "input.png")
    (work / "context.json").write_text(json.dumps(ctx) + "\n")
    W, H = spec["sheet"]
    print(f"-> {work / 'input.png'} ({W}:{H}). Prompt:\n{spec['prompt']}")


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def register(ans: Image.Image, ref: np.ndarray, sheet: tuple[int, int], x0: int, y0: int, mask: np.ndarray) -> Image.Image:
    """The answer's picture of one pattern (ref's size) registered to the input's."""
    h, w = ref.shape[:2]
    fx, fy = ans.width / sheet[0], ans.height / sheet[1]
    gray = lambda a: np.asarray(a, np.float32).mean(2)  # noqa: E731

    def score(s, sy, ox, oy, q):
        kx, ky = fx * s, fy * sy
        ax, ay = x0 * fx + ox, y0 * fy + oy
        c = gray(ans.crop((ax, ay, ax + w * kx, ay + h * ky)).resize((w // q, h // q), Image.BILINEAR))
        return ncc(c[mask[::q, ::q]], gray(ref[::q, ::q])[mask[::q, ::q]])
    best = max(((score(s, sy, ox, oy, 4), s, sy, ox, oy) for s in np.linspace(0.97, 1.03, 13)
                for sy in np.linspace(0.97, 1.03, 13) for ox in range(-12, 13, 3) for oy in range(-12, 13, 3)))
    _, s, sy, ox, oy = best
    best = max(((score(s, sy, a, b, 2), s, sy, a, b) for a in np.arange(ox - 3, ox + 3.01, 0.5)
                for b in np.arange(oy - 3, oy + 3.01, 0.5)))
    v, s, sy, ox, oy = best
    print(f"  registered: ncc {v:.3f}, scale {s:.3f} x {sy:.3f}, shift {ox:+.1f}, {oy:+.1f}")
    kx, ky = fx * s, fy * sy
    ax, ay = x0 * fx + ox, y0 * fy + oy
    return ans.crop((ax, ay, ax + w * kx, ay + h * ky)).resize((w, h), Image.LANCZOS)


def cut_set(spec, work: Path, L, tile) -> dict:
    """The covered HD tiles of one set's patterns, from its cached answer."""
    answer = next((work / f"answer.{e}" for e in ("png", "jpg", "jpeg", "webp") if (work / f"answer.{e}").exists()), None)
    if answer is None:
        raise SystemExit(f"no answer in {work}")
    ans = Image.open(answer).convert("RGB")
    inp = np.asarray(Image.open(work / "input.png").convert("RGB"), np.float32)
    ctx = json.loads((work / "context.json").read_text())
    covered = {}
    for (name, pattern), (x0, y0) in zip(spec["patterns"], layout(spec)):
        print(name)
        nb = np.array(ctx[name])
        rows, cols = nb.shape
        pr, pc = rows - 2, cols - 2
        # The HD tiles as they are now (the input may be older), and the wreck's pixels.
        orig = np.zeros((rows * TH, cols * TW, 3), np.float32)
        for j in range(rows):
            for i in range(cols):
                orig[j * TH:(j + 1) * TH, i * TW:(i + 1) * TW] = np.asarray(tile(int(nb[j, i])), np.float32)
        wreck = np.zeros((rows * 28, cols * 24), bool)
        for j in range(pr):
            for i in range(pc):
                px = L.tile(pattern[j][i])
                cell = np.ones(px.shape, bool) if spec["whole"] else ~np.isin(px, spec.get("ground", range(16, 22)))  # not ground
                wreck[28 + j * 28:56 + j * 28, 24 + i * 24:48 + i * 24] = cell
        wreck = binary_dilation(np.kron(wreck, np.ones((8, 8), bool)), iterations=spec.get("grow", 12))
        ref = inp[y0:y0 + rows * TH, x0:x0 + cols * TW]
        mask = ~binary_dilation(wreck, iterations=28)
        painted = np.asarray(register(ans, ref, spec["sheet"], x0, y0, mask), np.float32)
        # Low frequencies follow the HD tiles where the painting should match them.
        ok = (~wreck).astype(np.float32)
        w = gaussian_filter(ok, 40) + 1e-6
        for c in range(3):
            painted[..., c] += gaussian_filter((orig[..., c] - painted[..., c]) * ok, 40) / w
        inner = np.zeros(ok.shape, np.float32)
        inner[TH:(rows - 1) * TH, TW:(cols - 1) * TW] = 1
        wt = inner * np.clip(gaussian_filter(wreck.astype(np.float32), 6) * 1.5, 0, 1)
        out = orig * (1 - wt[..., None]) + painted * wt[..., None]
        for j in range(pr):
            for i in range(pc):
                covered[pattern[j][i]] = out[TH + j * TH:2 * TH + j * TH, TW + i * TW:2 * TW + i * TW]
    return covered


def cmd_cut(args) -> None:
    out_root = Path(args.out)
    m, tile = atlas_tiles(out_root)
    by_image: dict[str, dict] = {}
    for name, spec in SETS.items():
        if args.set and name != args.set:
            continue
        L = T.LevelData(Path(args.data), spec.get("level", "1-9"))
        by_image.setdefault(spec.get("image", "0-covered.webp"), {}).update(cut_set(spec, Path(args.work) / spec["work"], L, tile))
    d = out_root / "shapesz"
    # The other atlases' entries stay as they are.
    rects = {k: r for k, r in m["layers"]["0"].get("covered", {}).items() if r.get("image") not in by_image}
    for image, covered in by_image.items():
        # Pack: 16-texel gutters, edge-extended, as terrain_hd.pack_atlas.
        cols = min(4, len(covered))
        rows = (len(covered) + cols - 1) // cols
        cw, ch = TW + 32, TH + 32
        atlas = np.zeros((rows * ch, cols * cw, 3), np.float32)
        for idx, (n, img) in enumerate(sorted(covered.items())):
            x, y = (idx % cols) * cw, (idx // cols) * ch
            atlas[y:y + ch, x:x + cw] = np.pad(img, ((16, 16), (16, 16), (0, 0)), mode="edge")
            rects[str(n)] = {"x": x + 16, "y": y + 16, "w": TW, "h": TH, "image": image}
        Image.fromarray(atlas.round().clip(0, 255).astype(np.uint8)).save(d / image, quality=92, method=6)
        print(f"-> {d / image}, {len(covered)} covered tiles")
    m["layers"]["0"]["covered"] = dict(sorted(rects.items(), key=lambda kv: int(kv[0])))
    (d / "manifest.json").write_text(json.dumps(m, indent=1) + "\n")
    print(f"-> {len(rects)} covered tiles in {d / 'manifest.json'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--work", default=str(ROOT / "reference/terrain-hd"), help="each set's work dir is DIR/<its work>")
    ap.add_argument("--out", default=str(ROOT / "public/art/terrain"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sh = sub.add_parser("sheet")
    sh.add_argument("set", choices=list(SETS))
    sh.set_defaults(fn=cmd_sheet)
    cu = sub.add_parser("cut")
    cu.add_argument("--set", choices=list(SETS), help="recompose only this set's atlas")
    cu.set_defaults(fn=cmd_cut)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
