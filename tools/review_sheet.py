"""One review sheet (PNG) and one metrics file (JSON) for a model, always in the same layout.

    python tools/review_sheet.py <name> [--which proto|current|reshape|both] [--out DIR] [--build]
                                 [--overrides FILE|none] [--label NAME]

<name> is a model or an assembly (whole). `proto` reviews public/models/proto/... (built by
assets/blender/proto/shape_model.py; --build runs the analyser and the generator first),
`current` the hand-made model the game uses now, `reshape` the current model with its heights
rescaled from the analysis (assets/blender/proto/reshape_heights.py). --overrides picks the overrides for --build
(default assets/blender/proto/overrides/<name>.json if present; `none` for the bare analysis);
--label names the proto sheet (<name>-<label>.png) so variants can sit side by side. Needs .shape/<name>/ from tools/sprite_shape.py
(run automatically if missing). Writes <out>/<name>-<which>.png and .json (default .shape/<name>/).

Layout (480 px panels, 4 across, 4 rows):
  1 sprite (nearest)    2 model top, ortho, sprite scale    3 sprite over model 50%    4 diff
  5 side elevation (2 panels wide)                           6 front elevation (2 panels wide)
  7 3/4 front-right     8 3/4 back-left                      9 game camera              10 region map with ids
  11 inferred height    12 metrics
Elevations share one scale for both models of a sprite and carry a ruler in sprite px (12 px = 1 unit).
Diff: red = sprite pixel the model misses, blue = model where the sprite is empty, grey to yellow =
colour error (CIE76 dE, 0 to 40+) of the palette colour seen from above against the sprite's.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sprite_shape as S  # noqa: E402

BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
PANEL = 480
TITLE = 22
BG = (24, 24, 30)


def lab(rgb):
    rgb = np.asarray(rgb, dtype=float) / 255
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or "Traceback" in r.stdout + r.stderr:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit(f"failed: {' '.join(map(str, cmd))}")
    return r.stdout


def fit(img, size=PANEL, nearest=False):
    img = img.convert("RGBA")
    sc = min(size / img.width, size / img.height)
    if nearest and sc >= 1:
        sc = int(sc)
    im = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.NEAREST if nearest else Image.LANCZOS)
    out = Image.new("RGBA", (size, size), BG + (255,))
    out.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    return out


def ruler(img, span, zc):
    """Horizontal lines on an elevation strip (ortho span across its width) every few sprite px
    of height, labelled (z = 0 yellow)."""
    d = ImageDraw.Draw(img)
    P, Wd = img.height, img.width
    per_px = Wd / (span * 12)  # image px per sprite px
    step = next(s for s in (1, 2, 3, 6, 12, 24) if s * per_px >= 14)
    for zpx in range(-60 * step, 60 * step, step):
        z = zpx / 12
        row = P / 2 - (z - zc) / span * Wd
        if not 0 <= row < P:
            continue
        col = (200, 200, 90, 255) if zpx == 0 else (90, 90, 110, 255)
        d.line([(0, row), (Wd, row)], fill=col, width=1)
        d.text((3, row - 11), f"{zpx}px", fill=(170, 170, 120, 255))
    return img


def panel(img, title):
    out = Image.new("RGBA", (img.width, img.height + TITLE), BG + (255,))
    out.alpha_composite(img, (0, TITLE))
    ImageDraw.Draw(out).text((6, 5), title, fill=(230, 230, 230, 255))
    return out


def metrics(doc, an, smp, height, index, target):
    W, H = doc["size"]
    idx, labm = an["idx"], an["lab"]
    colors = {int(k): v for k, v in doc["colors"].items()}
    sprite = idx >= 0
    model = index != -2
    inter, union = (sprite & model).sum(), (sprite | model).sum()
    # Colour seen from above vs the sprite's, per pixel (CIE76).
    pal = np.zeros((256, 3))
    for k, v in colors.items():
        pal[k] = v
    seen = np.where(index >= 0, index, 0)
    both = sprite & model & (index >= 0)
    de = np.full((H, W), np.nan)
    de[both] = np.linalg.norm(lab(pal[idx[both]]) - lab(pal[seen[both]]), axis=-1)
    inferred = an["height"].reshape(H, doc["ss"], W, doc["ss"]).mean(axis=(1, 3))
    per = {}
    for r in doc["regions"]:
        m = labm == int(r["id"][1:])
        hit = m & model
        e = {"profile": r["profile"], "area": int(m.sum()),
             "coverage": round(float(hit.sum() / max(1, m.sum())), 3),
             "colour_dE": None if not (m & both).any() else round(float(np.nanmean(de[m & both])), 1),
             "inferred_mean_px": round(float(inferred[m].mean()), 2), "inferred_max_px": round(float(inferred[m].max()), 2)}
        if target is not None:
            e["target_mean_px"] = round(float(np.nanmean(target[m])), 2)
        if hit.any():
            e["actual_mean_px"] = round(float(np.nanmean(height[hit])), 2)
            e["actual_max_px"] = round(float(np.nanmax(height[hit])), 2)
            e["height_error_px"] = round(e["actual_mean_px"] - (e.get("target_mean_px", e["inferred_mean_px"])), 2)
        per[r["id"]] = e
    lo, hi = np.array(smp["bbox_min"]), np.array(smp["bbox_max"])
    size = hi - lo
    seams = smp["seams"]
    dz = [abs(a - b) for _, _, _, a, b in seams if a is not None and b is not None]
    gaps = sum(1 for _, _, _, a, b in seams if (a is None) != (b is None))
    errs = [abs(v["height_error_px"]) for v in per.values() if "height_error_px" in v]
    return {
        "name": doc["name"], "which": smp["which"], "overrides": doc.get("overrides"),
        "triangles": smp["triangles"], "missing_files": smp["missing"],
        "silhouette_iou": round(float(inter / max(1, union)), 3),
        "silhouette": {"sprite_px": int(sprite.sum()), "model_px": int(model.sum()),
                       "missed_px": int((sprite & ~model).sum()), "extra_px": int((model & ~sprite).sum())},
        "colour_dE_mean": round(float(np.nanmean(de)), 1) if both.any() else None,
        "bbox_units": [round(float(v), 3) for v in size],
        "height_to_width": round(float(size[2] / max(size[0], 1e-6)), 3),
        "max_height_px": round(float(np.nanmax(height)), 2) if model.any() else None,
        "height_error_px_mean": round(float(np.mean(errs)), 2) if errs else None,
        "seams": None if not seams else {"samples": len(seams), "mean_dz_px": round(float(np.mean(dz)), 3) if dz else 0,
                                         "max_dz_px": round(float(np.max(dz)), 3) if dz else 0,
                                         "over_1px": int(sum(1 for v in dz if v > 1)), "gaps": gaps},
        "regions": per,
    }


def diff_image(an, index, colors, de):
    idx = an["idx"]
    H, W = idx.shape
    out = np.zeros((H, W, 3), dtype=np.uint8) + np.array(BG, dtype=np.uint8)
    sprite, model = idx >= 0, index != -2
    t = np.clip(np.nan_to_num(de) / 40, 0, 1)
    both = sprite & model
    out[both] = np.stack([60 + 195 * t, 60 + 175 * t, 60 * (1 - t)], -1)[both].astype(np.uint8)
    out[sprite & ~model] = (230, 40, 40)
    out[model & ~sprite] = (50, 90, 240)
    return Image.fromarray(out)


def sheet(name, which, out, label=None):
    work = ROOT / ".shape" / name
    doc = json.loads((work / "regions.json").read_text())
    if which == "proto":  # the regions as built: the analysis plus the overrides used
        built = json.loads((work / "build.json").read_text()) if (work / "build.json").exists() else {}
        if built.get("overrides"):
            over = json.loads(Path(built["overrides"]).read_text()).get("regions", {})
            doc["regions"] = [{**r, **over.get(r["id"], {})} for r in doc["regions"]]
            doc["overrides"] = built["overrides"]
    an = dict(np.load(work / "analysis.npz"))
    W, H = doc["size"]
    k = max(2, PANEL // max(W, H))
    views = work / f"views-{which}"
    run([BLENDER, "-b", "--factory-startup", "--python", str(ROOT / "assets/blender/proto/review_render.py"), "--",
         name, which, str(views), str(k)])
    smp = json.loads((views / "samples.json").read_text())
    height, index = np.load(views / "height.npy"), np.load(views / "index.npy")
    target = np.load(work / "target_height.npy") if which in ("proto", "reshape") and (work / "target_height.npy").exists() else None
    m = metrics(doc, an, smp, height, index, target)
    colors = {int(k_): v for k_, v in doc["colors"].items()}
    pal = np.zeros((256, 3))
    for k_, v in colors.items():
        pal[k_] = v
    idx = an["idx"]
    de = np.full((H, W), np.nan)
    both = (idx >= 0) & (index >= 0)
    de[both] = np.linalg.norm(lab(pal[idx[both]]) - lab(pal[index[both]]), axis=-1)

    sprite_img = Image.fromarray(S.rgb_image(idx, colors, bg=BG)).resize((W * k, H * k), Image.NEAREST)
    top = Image.open(views / "top.png").convert("RGBA")
    top_bg = Image.new("RGBA", top.size, BG + (255,))
    top_bg.alpha_composite(top)
    flat = Image.open(views / "top_flat.png").convert("RGBA")
    flat_bg = Image.new("RGBA", flat.size, BG + (255,))
    flat_bg.alpha_composite(flat)
    overlay = Image.blend(flat_bg, sprite_img.convert("RGBA"), 0.5)
    span, zc = smp["elevation_span"], smp["elevation_zc"]

    def view(f):
        im = Image.open(views / f).convert("RGBA")
        bg = Image.new("RGBA", im.size, BG + (255,))
        bg.alpha_composite(im)
        return bg

    rmap = S.region_map_image(an["lab"], doc["regions"], idx, colors, scale=k)
    hgt, lo, hi = S.heat(an["height"], an["height_mask"])
    himg = Image.fromarray(hgt).resize((W * k, H * k), Image.NEAREST)
    ImageDraw.Draw(himg).text((4, 4), f"{lo:.1f}..{hi:.1f} px", fill=(255, 255, 255))
    text = metrics_text(m, which)
    tpanel = Image.new("RGBA", (PANEL, PANEL), BG + (255,))
    ImageDraw.Draw(tpanel).multiline_text((8, 6), text, fill=(225, 225, 225, 255), spacing=3)
    panels = [
        panel(fit(sprite_img, nearest=True), "1 sprite"),
        panel(fit(top_bg, nearest=True), "2 model top (ortho, sprite scale, lit)"),
        panel(fit(overlay, nearest=True), "3 sprite over model (flat colours) 50%"),
        panel(fit(diff_image(an, index, colors, de), nearest=True), "4 diff: red missed, blue extra, yellow colour error"),
        panel(ruler(view("side.png"), span, zc), "5 side elevation, ortho (from the right; sprite top is right)"),
        panel(ruler(view("front.png"), span, zc), "6 front elevation, ortho (from the screen bottom)"),
        panel(view("q1.png"), "7 three-quarter, front right"),
        panel(view("q2.png"), "8 three-quarter, back left"),
        panel(view("game.png"), "9 game camera angle"),
        panel(fit(rmap, nearest=True), "10 regions (ids for overrides)"),
        panel(fit(himg, nearest=True), "11 inferred height (analysis)"),
        panel(tpanel, "12 metrics"),
    ]
    head = 30
    out_img = Image.new("RGBA", (PANEL * 4, head + (PANEL + TITLE) * 4), BG + (255,))
    ImageDraw.Draw(out_img).text((8, 8), f"{name} - {which} model - {m['triangles']} tris - IoU {m['silhouette_iou']}"
                                 f" - h/w {m['height_to_width']} - dE {m['colour_dE_mean']}", fill=(255, 220, 120, 255))
    x = y = 0
    for p in panels:
        out_img.alpha_composite(p, (x, head + y))
        x += p.width
        if x >= 4 * PANEL:
            x, y = 0, y + PANEL + TITLE
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    tag = label or which
    png = out / f"{name}-{tag}.png"
    out_img.convert("RGB").save(png)
    m["label"] = tag
    (out / f"{name}-{tag}.json").write_text(json.dumps(m, indent=1))
    print(f"{png} ({m['triangles']} tris, IoU {m['silhouette_iou']}, h/w {m['height_to_width']})")
    return png, m


def stack(a, b):
    """Two elevation strips one above the other in a 2-panel-wide slot."""
    out = Image.new("RGBA", (max(a.width, b.width), PANEL + TITLE), BG + (255,))
    out.alpha_composite(a, (0, 0))
    out.alpha_composite(b, (0, a.height + (PANEL + TITLE - a.height - b.height)))
    return out


def metrics_text(m, which):
    lines = [f"{which}: {m['triangles']} triangles", f"silhouette IoU {m['silhouette_iou']}"
             f"  (missed {m['silhouette']['missed_px']} px, extra {m['silhouette']['extra_px']} px)",
             f"colour dE mean {m['colour_dE_mean']}",
             f"bbox units {m['bbox_units']}  h/w {m['height_to_width']}",
             f"max height {m['max_height_px']} px", f"region height error mean {m['height_error_px_mean']} px"]
    if m["seams"]:
        s = m["seams"]
        lines.append(f"seams: {s['samples']} samples, mean dz {s['mean_dz_px']} px, max {s['max_dz_px']}, >1px {s['over_1px']}, gaps {s['gaps']}")
    lines.append("")
    lines.append("largest regions: id profile area  z inferred/actual  dE")
    regs = sorted(m["regions"].items(), key=lambda kv: -kv[1]["area"])[:16]
    for rid, e in regs:
        tgt = e.get("target_mean_px", e["inferred_mean_px"])
        lines.append(f"{rid:>4} {e['profile']:<7}{e['area']:>5}  {tgt:5.1f}/{e.get('actual_mean_px', float('nan')):5.1f}  {e['colour_dE']}")
    return "\n".join(lines)


def compare(name, out, proto_label="proto"):
    """<name>-compare.png: the sprite and region map, then the current and the prototype model
    (3/4 and game camera) and their front elevations at one scale. Needs both sheets' views."""
    work = ROOT / ".shape" / name
    doc = json.loads((work / "regions.json").read_text())
    an = np.load(work / "analysis.npz")
    colors = {int(k): v for k, v in doc["colors"].items()}
    out = Path(out)

    def v(which, f):
        im = Image.open(work / f"views-{which}" / f).convert("RGBA")
        bg = Image.new("RGBA", im.size, BG + (255,))
        bg.alpha_composite(im)
        return bg

    mc = json.loads((out / f"{name}-current.json").read_text())
    mp = json.loads((out / f"{name}-{proto_label}.json").read_text())
    tag = "prototype" + (" + overrides" if mp.get("overrides") else ", analysis only")
    sm = json.loads((work / "views-proto" / "samples.json").read_text())
    sp = Image.fromarray(S.rgb_image(an["idx"], colors, bg=BG))
    rows = [[panel(fit(sp, nearest=True), "sprite"), panel(v("current", "q1.png"), f"current, 3/4 ({mc['triangles']} tris)"),
             panel(v("proto", "q1.png"), f"{tag}, 3/4 ({mp['triangles']} tris)")],
            [panel(fit(S.region_map_image(an["lab"], doc["regions"], an["idx"], colors), nearest=True), "regions"),
             panel(v("current", "game.png"), "current, game camera"), panel(v("proto", "game.png"), f"{tag}, game camera")]]
    fe = [panel(ruler(v(w, "front.png"), sm["elevation_span"], sm["elevation_zc"]), f"{t}, front elevation (ortho)")
          for w, t in (("current", "current"), ("proto", tag))]
    img = Image.new("RGBA", (3 * PANEL + PANEL, 30 + 2 * (PANEL + TITLE) + fe[0].height), BG + (255,))
    ImageDraw.Draw(img).text((8, 8), f"{name}: current vs {tag} - max height {mc['max_height_px']} vs {mp['max_height_px']} px,"
                             f" h/w {mc['height_to_width']} vs {mp['height_to_width']}, IoU {mc['silhouette_iou']} vs"
                             f" {mp['silhouette_iou']}, tris {mc['triangles']} vs {mp['triangles']}", fill=(255, 220, 120, 255))
    for r, row in enumerate(rows):
        for c, p in enumerate(row):
            img.alpha_composite(p, (c * PANEL, 30 + r * (PANEL + TITLE)))
    y = 30 + 2 * (PANEL + TITLE)
    small = [f.resize((f.width // 2 * 2 // 2, f.height // 2)) for f in fe]
    img.alpha_composite(small[0], (0, y))
    img.alpha_composite(small[1], (small[0].width, y))
    img = img.crop((0, 0, 3 * PANEL, y + small[0].height)) if small[0].width * 2 <= 3 * PANEL else img
    png = out / f"{name}-compare.png"
    img.convert("RGB").save(png)
    print(png)
    return png


def main(argv):
    name = argv[0]
    which = argv[argv.index("--which") + 1] if "--which" in argv else "both"
    out = argv[argv.index("--out") + 1] if "--out" in argv else ROOT / ".shape" / name
    work = ROOT / ".shape" / name
    if "--build" in argv or not (work / "regions.json").exists():
        py = sys.executable
        run([py, str(ROOT / "tools/sprite_shape.py"), name])
        if "--build" in argv:
            extra = ["--overrides", argv[argv.index("--overrides") + 1]] if "--overrides" in argv else []
            run([BLENDER, "-b", "--factory-startup", "--python", str(ROOT / "assets/blender/proto/shape_model.py"), "--", name] + extra)
    label = argv[argv.index("--label") + 1] if "--label" in argv else None
    for w in (["current", "proto"] if which == "both" else [which]):
        sheet(name, w, out, label if w == "proto" else None)
    if which == "both" or "--compare" in argv:
        compare(name, out, label or "proto")


if __name__ == "__main__":
    main(sys.argv[1:])
