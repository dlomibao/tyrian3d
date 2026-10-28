"""Infer 3D shape from a Tyrian sprite (prototype; see the model-shape notes in the report).

Input: a model name from reference/models (e.g. newsh5-47) or an assembly (assembly-newshb-115,
composed whole from its pieces). Output: a height field, a region map with a shape class per
region, and debug images. Run with the remaster venv's Python (numpy, scipy, Pillow):

    python tools/sprite_shape.py <name> [<name> ...] --out <dir>

Writes <dir>/<name>/analysis.npz and analysis.json (for assets/blender/proto/shape_model.py) and
debug PNGs. Nothing here is read by the game.
"""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "models"


# --- Loading ------------------------------------------------------------------------------------

def _pixels(frame):
    return np.array([[int(v) for v in row.split()] for row in frame["pixels"]], dtype=np.int16)


def load_sprite(name):
    """{name, idx (H x W palette indices, -1 transparent), colors {index: rgb}, pieces}.
    A plain model is one piece covering the picture; an assembly lists each piece's box."""
    data = json.loads((REF / name / "sprite.json").read_text())
    # The model's own frame (a player ship's level frame), not frames[0], which for a ship that
    # banks is its hardest left bank.
    want = next((s["frames"][0] for s in data.get("sprites") or [] if s.get("frames")), None)
    frame = next((f for f in data["frames"] if f["index"] == want), data["frames"][0])
    idx = _pixels(frame)
    colors = {int(k): tuple(v) for k, v in data["colors"].items()}
    h, w = idx.shape
    return {"name": name, "kind": data.get("kind"), "idx": idx, "colors": colors,
            "pieces": [{"model": name, "x0": 0, "y0": 0, "w": w, "h": h}], "frame": frame["index"]}


def assembly_pieces(asm):
    cat = json.loads((REF / "catalogue.json").read_text())
    return [e["name"] for e in cat if e.get("assembly") == asm]


def load_assembly(asm):
    """The whole object as one picture, composed from its pieces' layout frames (sprite.json
    assemblyLayout), with each piece's box in that picture."""
    names = assembly_pieces(asm)
    first = json.loads((REF / names[0] / "sprite.json").read_text())
    layout = [e for e in first["assemblyLayout"] if e["model"] in names]
    colors, placed = {}, []
    for e in layout:
        data = json.loads((REF / e["model"] / "sprite.json").read_text())
        colors.update({int(k): tuple(v) for k, v in data["colors"].items()})
        want = int(e["frame"].split("|")[-1])
        frame = next((f for f in data["frames"] if f["index"] == want), data["frames"][0])
        placed.append((e, frame, _pixels(frame)))
    x0 = min(e["cx"] - px.shape[1] // 2 for e, _, px in placed)
    y0 = min(e["cy"] - px.shape[0] // 2 for e, _, px in placed)
    x1 = max(e["cx"] - px.shape[1] // 2 + px.shape[1] for e, _, px in placed)
    y1 = max(e["cy"] - px.shape[0] // 2 + px.shape[0] for e, _, px in placed)
    idx = np.full((y1 - y0, x1 - x0), -1, dtype=np.int16)
    pieces = []
    for e, frame, px in placed:
        h, w = px.shape
        px0, py0 = e["cx"] - w // 2 - x0, e["cy"] - h // 2 - y0
        region = idx[py0:py0 + h, px0:px0 + w]
        region[px >= 0] = px[px >= 0]
        pieces.append({"model": e["model"], "x0": int(px0), "y0": int(py0), "w": int(w), "h": int(h),
                       "frame": frame["index"], "cx": e["cx"], "cy": e["cy"]})
    return {"name": asm, "kind": "assembly", "idx": idx, "colors": colors, "pieces": pieces}


def load(name):
    return load_assembly(name) if name.startswith("assembly-") else load_sprite(name)


def rgb_image(idx, colors, bg=(30, 30, 36)):
    out = np.zeros(idx.shape + (3,), dtype=np.uint8)
    out[...] = bg
    for i in np.unique(idx[idx >= 0]):
        out[idx == i] = colors[int(i)]
    return out


# --- Analysis ------------------------------------------------------------------------------------

from scipy import ndimage as ndi  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shape_profiles as SP  # noqa: E402

VERSION = 1
SS = 2  # height samples per sprite px
#: Light direction found in the data (see `light_survey`): from above the screen, a little left.
#: Unit vector in image axes (x right, y down, z up); refined per sprite by `fit_light`.
DEFAULT_LIGHT = np.array([-0.3, -0.55, 0.78])
FOUR = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)


def lstar(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    y = 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2])
    return 116 * y ** (1 / 3) - 16 if y > 0.008856 else 903.3 * y


def lightness(idx, colors):
    L = np.zeros(idx.shape)
    for i, c in colors.items():
        L[idx == i] = lstar(c)
    return L


def _borders(lab):
    """{(a, b): count} of 4-neighbour pixel pairs with labels a != b (-1 = transparent)."""
    out = {}
    for a, b in ((lab[:, :-1], lab[:, 1:]), (lab[:-1, :], lab[1:, :])):
        diff = a != b
        for x, y in zip(a[diff], b[diff]):
            out[(int(x), int(y))] = out.get((int(x), int(y)), 0) + 1
            out[(int(y), int(x))] = out.get((int(y), int(x)), 0) + 1
    return out


def segment(idx, L, min_px=12):
    """Label map: regions of one hue ramp (idx & 0xf0) split by outlines; thick areas of the
    darkest greys are `void` regions (floors, holes); thin dark lines (outlines) are given to the
    nearest region. Small regions merge into the neighbour they share most border with.
    Returns (lab, kinds) with lab -1 outside the sprite and kinds[label] in {"hue", "void"}."""
    op = idx >= 0
    hue = np.where(op, idx >> 4, -1)
    shade = np.where(op, idx & 15, -1)
    dark = op & (((hue == 0) & (shade <= 2)) | (idx == 0xFE) | (L < 4))
    core = ndi.distance_transform_edt(dark) >= 2.0
    void = ndi.binary_dilation(core, structure=FOUR) & dark
    lab = np.full(idx.shape, -1, dtype=np.int32)
    kinds = []
    vl, nv = ndi.label(void, structure=FOUR)
    for k in range(1, nv + 1):
        m = vl == k
        if m.sum() >= 6:
            lab[m] = len(kinds)
            kinds.append("void")
    for h in np.unique(hue[op & ~dark]):
        hl, nh = ndi.label((hue == h) & ~dark, structure=FOUR)
        for k in range(1, nh + 1):
            lab[hl == k] = len(kinds)
            kinds.append("hue")
    # Merge small regions (texture specks, single highlight pixels) into their main neighbour.
    for _ in range(4):
        sizes = np.bincount(lab[lab >= 0], minlength=len(kinds))
        b = _borders(lab)
        changed = False
        for r in np.argsort(sizes):
            if sizes[r] == 0 or sizes[r] >= min_px:
                continue
            nbs = [(n, c) for (a, n), c in b.items() if a == r and n >= 0 and sizes[n] > 0]
            if not nbs:
                continue
            n = max(nbs, key=lambda t: (t[1], sizes[t[0]]))[0]
            lab[lab == r] = n
            sizes[n] += sizes[r]
            sizes[r] = 0
            changed = True
        if not changed:
            break
    # Texture (foliage, rubble): neighbouring regions made of fine speckle of two or more ramps
    # become one region, so terrain under a structure is one piece, not dozens.
    hue_change = np.zeros(idx.shape)
    for a_, b_, sl_a, sl_b in ((hue[:, :-1], hue[:, 1:], np.s_[:, :-1], np.s_[:, 1:]), (hue[:-1, :], hue[1:, :], np.s_[:-1, :], np.s_[1:, :])):
        ch = ((a_ != b_) & (a_ >= 0) & (b_ >= 0)).astype(float)
        hue_change[sl_a] += ch
        hue_change[sl_b] += ch
    density = ndi.uniform_filter(hue_change, 5)
    sizes = np.bincount(lab[lab >= 0], minlength=len(kinds))
    speck = [k < len(kinds) and kinds[k] == "hue" and sizes[k] > 0 and density[lab == k].mean() > 0.6 for k in range(len(kinds))]
    b = _borders(lab)
    parent = list(range(len(kinds)))

    def root(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for (a_, b_), c in b.items():
        if a_ >= 0 and b_ >= 0 and speck[a_] and speck[b_]:
            parent[root(a_)] = root(b_)
    for k in range(len(kinds)):
        if speck[k] and root(k) != k:
            lab[lab == k] = root(k)
    # Outline pixels (and dark specks left unlabelled) go to the nearest region.
    unl = op & (lab < 0)
    if unl.any() and (lab >= 0).any():
        _, (iy, ix) = ndi.distance_transform_edt(lab < 0, return_indices=True)
        lab[unl] = lab[iy[unl], ix[unl]]
    # Renumber in raster order of each region's first pixel: stable ids.
    order, seen = [], set()
    for v in lab.ravel():
        if v >= 0 and v not in seen:
            seen.add(v)
            order.append(v)
    remap = np.full(len(kinds), -1)
    for new, old in enumerate(order):
        remap[old] = new
    out = np.where(lab >= 0, remap[np.maximum(lab, 0)], -1)
    return out, [kinds[o] for o in order], dark


def normals_of(h):
    gy, gx = np.gradient(h)
    n = np.dstack([-gx, -gy, np.ones_like(h)])
    return n / np.linalg.norm(n, axis=2, keepdims=True)


def light_dirs():
    out = []
    for el in (35, 50, 65):
        for az in range(0, 360, 15):
            a, e = np.radians(az), np.radians(el)
            out.append((np.cos(e) * np.cos(a), -np.cos(e) * np.sin(a), np.sin(e)))  # az 90 = screen up
    return np.array(out)


def fit_shading(L, m, n, light):
    """R^2 of L ~ a + b * max(0, n.l) over mask m (b >= 0), and b."""
    s = np.clip((n[m] * light).sum(axis=1), 0, None)
    y = L[m]
    if y.std() < 1e-6 or s.std() < 1e-6:
        return 0.0, 0.0
    b = np.cov(s, y)[0, 1] / s.var()
    if b <= 0:
        return 0.0, b
    pred = y.mean() + b * (s - s.mean())
    return float(1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()), float(b)


def nearest_ball(m, d):
    """For each pixel of m: the centre and radius of the medial ball that reaches highest over it."""
    ys, xs = np.nonzero(m)
    p = np.pad(d, 1)
    nbmax = np.max([p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx]
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx], axis=0)
    cy, cx = np.nonzero((d >= nbmax - 0.5) & m)
    cr = d[cy, cx] + 0.5
    h2 = cr[None, :] ** 2 - (ys[:, None] - cy[None, :]) ** 2 - (xs[:, None] - cx[None, :]) ** 2
    k = h2.argmax(axis=1)
    return ys, xs, cx[k], cy[k], cr[k]


def _eta2(y, bins, nb):
    tot = ((y - y.mean()) ** 2).sum()
    if tot < 1e-9:
        return 0.0
    within = sum(((y[bins == i] - y[bins == i].mean()) ** 2).sum() for i in range(nb) if (bins == i).any())
    return float(1 - within / tot)


def shading_features(L, m, d, light):
    """How round the shading says the region is (cue 3), as three measures:
    xsec: share of the interior brightness variance explained by the position across the local
          cross-section (signed towards the light), less the same for shuffled pixels;
    align: how much the brightness gradient runs across the edges rather than along them (bands
          parallel to the outline: tubes, domes, but also bevels and sloped panels);
    lambert: R^2 of a Lambert fit of the round shape under the sprite's light (fit_shading)."""
    out = {"xsec": 0.0, "align": 0.0}
    if m.sum() < 15:
        return out
    ys, xs, cx, cy, R = nearest_ball(m, d)
    off = np.c_[xs - cx, ys - cy]
    l2 = np.array(light[:2]) / max(1e-6, np.linalg.norm(light[:2]))
    u = np.clip(np.hypot(off[:, 0], off[:, 1]) / R, 0, 1) * np.sign(off @ l2 + 1e-6)
    inner = d[ys, xs] >= 1.4
    if inner.sum() >= 12 and R.max() >= 2.5:
        y = L[ys, xs][inner]
        b = np.minimum(((u[inner] + 1) * 4).astype(int), 7)
        shuffled = _eta2(np.random.default_rng(0).permutation(y), b, 8)
        out["xsec"] = round(max(0.0, _eta2(y, b, 8) - shuffled), 3)
    gy, gx = np.gradient(ndi.gaussian_filter(d, 0.7))
    gn = np.hypot(gx, gy) + 1e-9
    Lp = np.where(m, L, np.nan)
    ly = (np.roll(Lp, -1, 0) - np.roll(Lp, 1, 0)) / 2
    lx = (np.roll(Lp, -1, 1) - np.roll(Lp, 1, 1)) / 2
    ok = m & (d >= 0.9) & np.isfinite(lx) & np.isfinite(ly) & (gn > 0.3)
    if ok.sum() >= 5:
        nx, ny = gx[ok] / gn[ok], gy[ok] / gn[ok]
        across = ((lx[ok] * nx + ly[ok] * ny) ** 2).sum()
        along = ((-lx[ok] * ny + ly[ok] * nx) ** 2).sum()
        out["align"] = round(float((across - along) / (across + along + 1e-9)), 3)
    return out


def round_score(f, r2):
    """0..1: the shading's vote for a round surface (weights set by eye on the prototype set)."""
    return (0.5 * np.clip(f["xsec"] / 0.2, 0, 1) + 0.3 * np.clip((f["align"] - 0.3) / 0.3, 0, 1)
            + 0.2 * np.clip(r2 / 0.4, 0, 1))


def analyse(s):
    idx, colors = s["idx"], s["colors"]
    Hh, Ww = idx.shape
    op = idx >= 0
    L = lightness(idx, colors)
    lab, kinds, dark = segment(idx, L)
    n_reg = len(kinds)
    masks = [lab == r for r in range(n_reg)]
    area = np.array([m.sum() for m in masks])
    borders = _borders(lab)
    perim = {r: sum(c for (a, _), c in borders.items() if a == r) for r in range(n_reg)}
    # Sprite edges count as border with the outside.
    for r, m in enumerate(masks):
        edge = m[0].sum() + m[-1].sum() + m[:, 0].sum() + m[:, -1].sum()
        borders[(r, -1)] = borders.get((r, -1), 0) + int(edge)
        perim[r] += int(edge)

    # Round candidate per region: union of balls on its own mask.
    rounds, dists = [], []
    for m in masks:
        d = SP.edge_distance(m, 1)
        dists.append(d)
        rounds.append(SP.ball_union(m, d, 1))
    nround = [normals_of(h) for h in rounds]

    # Light: the direction that best explains the shading of the regions as round shapes.
    cand = light_dirs()
    score = np.zeros(len(cand))
    usable = [r for r in range(n_reg) if kinds[r] == "hue" and area[r] >= 15 and L[masks[r]].std() > 4]
    for i, l in enumerate(cand):
        score[i] = sum(fit_shading(L, masks[r], nround[r], l)[0] * np.sqrt(area[r]) for r in usable)
    base_score = sum(fit_shading(L, masks[r], nround[r], DEFAULT_LIGHT)[0] * np.sqrt(area[r]) for r in usable)
    light = DEFAULT_LIGHT
    if usable and score.max() > 1.5 * base_score + 0.5:  # only trust a sprite's own light when it's clearly better
        light = cand[int(np.argmax(score))]

    regions = []
    hue_of = np.where(op, idx >> 4, -1)
    for r in range(n_reg):
        m = masks[r]
        ys, xs = np.nonzero(m)
        vals = idx[m]
        hues, counts = np.unique(hue_of[m], return_counts=True)
        main_hue = int(hues[np.argmax(counts)]) if kinds[r] == "hue" else 0
        # Its material: the index at the 60th percentile of lightness among its main ramp's pixels
        # (a little above the median: the model's own lighting darkens it again).
        own = vals[((vals >> 4) == main_hue) & (L[m] >= 10)] if kinds[r] == "hue" else vals  # not its outline
        own_L = np.array([lstar(colors[int(v)]) for v in own])
        mat = int(own[np.argsort(own_L, kind="stable")[int(len(own) * 0.6)]]) if len(own) else int(vals[0])
        r2, _ = fit_shading(L, m, nround[r], light)
        dmax = float(dists[r].max())
        compact = area[r] / (np.pi * max(dmax + 0.5, 0.5) ** 2)
        out_frac = borders.get((r, -1), 0) / max(1, perim[r])
        reg = {
            "id": f"r{r}", "hue": main_hue * 16, "material": mat, "area": int(area[r]),
            "mask": {"x": int(xs.min()), "y": int(ys.min()), "w": int(xs.max() - xs.min() + 1),
                     "h": int(ys.max() - ys.min() + 1)},
            "centroid": [round(float(xs.mean()), 1), round(float(ys.mean()), 1)],
            "half_width": round(dmax + 0.5, 2), "compactness": round(float(compact), 2),
            "outside_border": round(float(out_frac), 2), "lightness": round(float(L[m].mean()), 1),
            "round_r2": round(r2, 3), "cues": [],
        }
        feats = shading_features(L, m, dists[r], light)
        reg["shading"] = {**feats, "lambert": round(r2, 3), "round_score": round(float(round_score(feats, r2)), 3)}
        mm = m[reg["mask"]["y"]:reg["mask"]["y"] + reg["mask"]["h"], reg["mask"]["x"]:reg["mask"]["x"] + reg["mask"]["w"]]
        reg["mask"]["rle"] = SP.rle_encode(mm)
        regions.append(reg)

    # --- Classification -------------------------------------------------------------------------
    def nbs(r):
        return {b: c for (a, b), c in borders.items() if a == r and b >= 0}

    bbox_edge = np.zeros((Hh, Ww), dtype=bool)
    bbox_edge[0] = bbox_edge[-1] = bbox_edge[:, 0] = bbox_edge[:, -1] = True
    for r, reg in enumerate(regions):
        m = masks[r]
        nb = nbs(r)
        if kinds[r] == "void":
            enclosed = reg["outside_border"] < 0.05
            if enclosed and nb:
                reg.update(profile="recess", top=0.0, recess_depth=1.5, conf=0.6)
                reg["cues"].append("dark area enclosed by the object: recess")
            else:
                reg.update(profile="void", top=0.5, conf=0.5)
                reg["cues"].append("dark fill open to the outside: floor")
            continue
        # Background fill cut straight by the sprite's box (terrain under a ground structure).
        on_box = (m & bbox_edge).sum()
        if on_box >= 0.5 * (Hh + Ww) and reg["area"] > 0.15 * op.sum():
            reg.update(profile="flat", top=0.5, bevel=0.0, relief=0.5, conf=0.5)
            reg["cues"].append("fills to the sprite's box edge: terrain")
            continue
        # Recess: a darker region almost entirely inside one other region.
        if nb and reg["outside_border"] < 0.05:
            host, shared = max(nb.items(), key=lambda t: t[1])
            if shared / perim[r] > 0.7 and reg["lightness"] < regions[host]["lightness"] - 12 and reg["area"] < 0.5 * area[host]:
                depth = float(np.clip((regions[host]["lightness"] - reg["lightness"]) / 15, 0.75, 3.0))
                reg.update(profile="recess", top=0.0, recess_depth=round(depth, 2), conf=0.5)
                reg["cues"].append(f"darker than r{host}, which surrounds it: recess")
                continue
        hw = reg["half_width"]
        sc = reg["shading"]["round_score"]
        why = f"round score {sc:.2f} (xsec {reg['shading']['xsec']:.2f}, align {reg['shading']['align']:.2f}, lambert {reg['round_r2']:.2f})"
        ys_, xs_ = np.nonzero(m)
        ev = np.linalg.eigvalsh(np.cov(np.c_[xs_, ys_].T) + 1e-6 * np.eye(2)) if len(ys_) > 2 else np.ones(2)
        elong = float(np.sqrt(ev[1] / max(ev[0], 1e-6)))
        reg["elongation"] = round(elong, 2)
        rect = reg["area"] / float(reg["mask"]["w"] * reg["mask"]["h"])
        reg["rectangularity"] = round(rect, 2)
        if rect >= 0.65 and elong < 2.0 and hw >= 5:
            bevel = bevel_of(L, m, dists[r])
            top = float(np.clip(0.35 * hw, 1.0, 8.0))
            reg.update(profile="flat", top=round(top, 2), bevel=round(bevel, 2), relief=0.3, conf=0.6)
            reg["cues"].append(f"{why}, but a large near-rectangular block (fill {rect:.2f}, aspect {elong:.1f}): box, {top:.1f} px")
        elif sc >= 0.3 and hw >= 1.5:
            reg["conf"] = round(float(min(1.0, 0.4 + sc)), 2)
            if elong < 1.4:
                reg.update(profile="dome", top=round(hw, 2))
                reg["cues"].append(f"{why}; compact: dome")
            else:
                reg.update(profile="round", top=round(hw, 2))
                reg["cues"].append(f"{why}; elongated: tube")
                tw = taper_of(dists[r], m)
                if tw is not None and abs(tw) > 0.5:
                    reg["profile"] = "taper"
                    reg["taper"] = 0.0
                    reg["cues"].append(f"width changes along its length ({tw:+.2f}): taper (the geometry follows the width)")
        else:
            bevel = bevel_of(L, m, dists[r])
            top = float(np.clip(0.35 * hw, 1.0, 8.0))
            reg.update(profile="flat", top=round(top, 2), bevel=round(bevel, 2), relief=0.3,
                       conf=round(float(min(1.0, 0.7 - sc)), 2))
            reg["cues"].append(f"{why}: flat plate {top:.1f} px thick, bevel {bevel:.1f} from its edge shading")

    stacking(regions, masks, borders, perim, area, kinds)
    shadows_and_faces(regions, masks, L, light, idx)
    groups = bodies(s, regions, masks, L, light)
    for reg in regions:
        if reg["profile"] == "flat" and reg.get("top", 0) < 1.5 and "terrain" not in " ".join(reg["cues"]):
            reg["relief"] = 0.0  # a sliver: relief only adds triangles
        reg.setdefault("relief", 0.0)
        reg.setdefault("bevel", 0.0)
        reg.setdefault("taper", 0.0)
        reg.setdefault("recess_depth", 0.0)
    return {"lab": lab, "L": L, "light": light, "regions": regions, "dark": dark, "masks": masks, "groups": groups}


def bodies(s, regions, masks, L, light):
    """A standalone sprite (not an assembly or terrain) is one body: its whole silhouette is
    inflated as one union of balls and its regions ride on it as offsets: a band round a pod
    stays on the pod's surface, a cockpit sits on a fuselage. The body's height is its half
    width, squashed when the whole silhouette's shading doesn't look round."""
    if s["kind"] == "assembly" or not regions:
        return {}
    keep = [r for r, reg in enumerate(regions) if reg["profile"] not in ("void",) and "terrain" not in " ".join(reg["cues"])]
    if not keep:
        return {}
    m = np.zeros(masks[0].shape, dtype=bool)
    for r in keep:
        m |= masks[r]
    d = SP.edge_distance(m, 1)
    feats = shading_features(L, m, d, light)
    r2, _ = fit_shading(L, m, normals_of(SP.ball_union(m, d, 1)), light)
    score = float(round_score(feats, r2))
    hw = float(d.max() + 0.5)
    squash = float(np.clip(0.45 + score, 0.45, 1.0))
    for r in keep:
        reg = regions[r]
        reg["group"] = "g0"
        reg["base"] = 0.0
        reg["on"] = []
        reg.pop("extends_under", None)
        if reg["profile"] in ("round", "dome", "taper"):
            reg["top"] = 0.0  # follows the body's surface
            reg["profile"] = "round"
        elif reg["profile"] == "flat":
            reg["top"], reg["bevel"] = 0.75, 0.5  # a raised plate on the body
        reg["cues"].append("part of body g0 (the whole sprite inflated as one)")
    below = 0.5 if s["kind"] == "air" else 0.0
    return {"g0": {"top": round(hw * squash, 2), "below": below, "half_width": round(hw, 2), "squash": round(squash, 2),
                   "round_score": round(score, 3),
                   "cue": f"whole silhouette half width {hw:.1f} px x squash {squash:.2f} from its shading (round score {score:.2f}); "
                          f"underside {below} of it mirrored below (air enemies only)"}}


def taper_of(d, m):
    """Relative change in width along the region's main axis (end vs start), or None."""
    ys, xs = np.nonzero(m)
    if len(ys) < 20:
        return None
    pts = np.c_[xs - xs.mean(), ys - ys.mean()]
    _, _, vt = np.linalg.svd(pts, full_matrices=False)
    axis = vt[0]
    t = pts @ axis
    length = t.max() - t.min()
    if length < 3 * (d.max() + 0.5):
        return None  # not elongated
    bins = np.linspace(t.min(), t.max(), 6)
    widths = [d[ys[(t >= a) & (t < b)], xs[(t >= a) & (t < b)]].max(initial=0) for a, b in zip(bins, bins[1:])]
    w0, w1 = np.mean(widths[:2]), np.mean(widths[-2:])
    return float((w1 - w0) / max(w0, w1, 1e-6))


def bevel_of(L, m, d):
    """Width (px) of the band along the edge whose shading differs from the interior's."""
    inner = m & (d >= 3)
    if inner.sum() < 6:
        return 1.0
    ref = np.median(L[inner])
    spread = np.median(np.abs(L[inner] - ref)) + 2
    width = 0.0
    for k in range(3):
        ring = m & (d >= k - 0.01) & (d < k + 0.99)
        if ring.sum() < 4:
            break
        if np.median(np.abs(L[ring] - ref)) > 2 * spread:
            width = k + 1.0
        else:
            break
    return width


def stacking(regions, masks, borders, perim, area, kinds):
    """Which regions sit on which: A sits on B when more of A's border is shared with B than of
    B's border with A (B surrounds it more than it surrounds B); ties go to the smaller region."""
    n = len(regions)
    on = {r: [] for r in range(n)}
    for (a, b), c in borders.items():
        if a < 0 or b < 0 or a >= b:
            continue
        fa, fb = c / perim[a], c / perim[b]
        top, under = (a, b) if (fa, -area[a]) > (fb, -area[b]) else (b, a)
        if regions[under]["profile"] == "recess":
            top, under = under, top  # a recess is cut into its surroundings
        if regions[top]["profile"] == "void" and regions[under]["profile"] != "void":
            continue  # floors are under everything
        on[top].append(under)
    # Order: solve supports first; break cycles by keeping the support with more shared border.
    order, state = {}, {}

    def visit(r, depth=0):
        if state.get(r) == 2:
            return order[r]
        if state.get(r) == 1 or depth > 50:
            return 0
        state[r] = 1
        lvl = 0
        for u in list(on[r]):
            if state.get(u) == 1:  # cycle
                on[r].remove(u)
                continue
            lvl = max(lvl, visit(u, depth + 1) + 1)
        state[r] = 2
        order[r] = lvl
        return lvl

    for r in range(n):
        visit(r)
    for r, reg in enumerate(regions):
        reg["order"] = int(order[r])
        reg["on"] = [f"r{u}" for u in on[r]]
        reg["base"] = 0.0 if not on[r] else None
        if reg["profile"] in ("round", "taper"):
            # Round shapes continue under what sits on them (a clamp over a pipe).
            reg["extends_under"] = [f"r{t}" for t in range(n) if r in on[t] and regions[t]["profile"] != "recess"]
        if reg["profile"] == "void":
            reg["order"] = -1


def shadows_and_faces(regions, masks, L, light, idx):
    """Cue 4: past a block's edge on the side away from the light, a run of pixels clearly darker
    than what lies beyond them is its drop shadow; with the light at ~45 degrees the run's length
    is the block's height. Measured per pixel along the two screen axes nearest the shadow
    direction, so it works inside terrain or any other region the shadow falls on.
    Cue 5: a band along a block's bottom edge, below a lit edge and clearly darker than it, is
    the block's front face seen at the game's slant; its height in rows x 2 sets the block's.
    Both only raise a block's `top` (flat regions of 60+ px)."""
    H, W = L.shape
    away = -np.array(light[:2])
    steps = [(1, 0)] if away[0] > 0.2 else ([(-1, 0)] if away[0] < -0.2 else [])
    steps += [(0, 1)] if away[1] > 0.2 else ([(0, -1)] if away[1] < -0.2 else [])
    for r, reg in enumerate(regions):
        if reg["profile"] != "flat" or reg["area"] < 60:
            continue
        m = masks[r]
        best = 0.0
        for dx, dy in steps:
            runs, edges = [], 0
            ys, xs = np.nonzero(m)
            for y, x in zip(ys, xs):
                y1, x1 = y + dy, x + dx
                if not (0 <= y1 < H and 0 <= x1 < W) or m[y1, x1] or idx[y1, x1] < 0:
                    continue
                edges += 1
                # Walk away from the edge: dark run, then the lit ground beyond it.
                k, vals = 0, []
                while k < 10:
                    yy, xx = y + dy * (k + 1), x + dx * (k + 1)
                    if not (0 <= yy < H and 0 <= xx < W) or idx[yy, xx] < 0 or m[yy, xx]:
                        break
                    vals.append(L[yy, xx])
                    k += 1
                if len(vals) < 3:
                    continue
                vals = np.array(vals)
                for n in range(2, len(vals) - 1):  # 1 px is the neighbour's outline
                    if vals[n:].max() - vals[:n].mean() > 15 and vals[:n].max() < vals[n:].max() - 8:
                        runs.append(n)
                        break
            if edges >= 6 and len(runs) >= 0.4 * edges:
                w = float(np.median(runs))
                reg["cues"].append(f"dark run {w:.0f} px past its {'right' if dx > 0 else 'left' if dx < 0 else 'bottom' if dy > 0 else 'top'} edge "
                                   f"({len(runs)} of {edges} edge px): drop shadow, height ~{w:.0f} px")
                best = max(best, w)
        if best:
            reg["shadow_px"] = best
            reg["top"] = round(max(reg["top"], best), 2)
        # Front face along the bottom edge.
        cols = np.unique(np.nonzero(m)[1])
        bands = []
        for x in cols:
            col = np.nonzero(m[:, x])[0]
            y = col.max()
            while y > col.min() and m[y, x] and L[y, x] < 10:  # the outline
                y -= 1
            seen = []
            for n in range(0, 8):
                yy = y - n
                if yy < col.min() or not m[yy, x]:
                    break
                if seen and L[yy, x] - np.mean(seen) > 15:
                    bands.append(len(seen))
                    break
                seen.append(L[yy, x])
        if len(cols) >= 6 and len(bands) >= 0.5 * len(cols):
            f = float(np.median(bands))
            reg["front_face_px"] = f
            reg["cues"].append(f"darker band {f:.0f} rows high under a lit edge along {len(bands)} of {len(cols)} columns: "
                               f"front face, height ~{2 * f:.0f} px")
            reg["top"] = round(max(reg["top"], 2 * f), 2)


def relief_field(L, lab, ss=SS):
    """High-pass brightness within each region, -1..1, upsampled: light details stand up,
    dark ones (grilles, seams) sink."""
    out = np.zeros(L.shape)
    for r in np.unique(lab[lab >= 0]):
        m = lab == r
        w = ndi.gaussian_filter(m.astype(float), 1.5)
        sm = ndi.gaussian_filter(np.where(m, L, 0), 1.5) / np.maximum(w, 1e-6)
        v = np.clip((L[m] - sm[m]) / 20, -1, 1)
        out[m] = np.where(np.abs(v) > 0.25, v, 0)  # only clear details, not dithering
    up = SP.upsample(out, ss)
    return ndi.gaussian_filter(up, 0.6)


def amodal_masks(regions, shape):
    by = {r["id"]: r for r in regions}
    out = {}
    for r in regions:
        ext = r.get("extends_under") or []
        if ext:
            m = np.zeros(shape, dtype=bool)
            for e in ext:
                if e in by:
                    m |= SP.region_mask(by[e], shape)
            out[r["id"]] = m
    return out


def merge_overrides(regions, overrides):
    if not overrides:
        return regions
    per = overrides.get("regions", overrides)
    out = []
    for r in regions:
        o = per.get(r["id"])
        out.append({**r, **o} if o else dict(r))
    return out


# --- Output --------------------------------------------------------------------------------------

def work_dir(name):
    return ROOT / ".shape" / name


def region_colors(n):
    rng = np.random.default_rng(7)
    return rng.integers(60, 230, (n, 3)).astype(np.uint8)


def label_points(lab, n):
    """A point well inside each region (its distance-field peak) for its id."""
    pts = []
    for r in range(n):
        m = lab == r
        if not m.any():
            pts.append(None)
            continue
        d = ndi.distance_transform_edt(np.pad(m, 1))[1:-1, 1:-1]
        y, x = np.unravel_index(np.argmax(d), d.shape)
        pts.append((int(x), int(y)))
    return pts


def scale_for(w):
    return int(max(4, min(10, 900 // max(w, 1))))


def region_map_image(lab, regions, idx=None, colors=None, scale=None):
    """The region map, each region in its own colour (or the sprite, dimmed) with its id."""
    from PIL import Image, ImageDraw
    H, W = lab.shape
    sc = scale or scale_for(W)
    cols = region_colors(len(regions))
    img = np.zeros((H, W, 3), dtype=np.uint8) + 20
    img[lab >= 0] = cols[lab[lab >= 0]]
    if idx is not None:
        img = (0.45 * img + 0.55 * rgb_image(idx, colors, bg=(20, 20, 20))).astype(np.uint8)
    im = Image.fromarray(img).resize((W * sc, H * sc), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    # Region borders.
    a = np.asarray(im).copy()
    big = np.repeat(np.repeat(lab, sc, 0), sc, 1)
    edge = np.zeros(big.shape, dtype=bool)
    edge[:, 1:] |= big[:, 1:] != big[:, :-1]
    edge[1:, :] |= big[1:, :] != big[:-1, :]
    a[edge] = (0, 0, 0)
    im = Image.fromarray(a)
    dr = ImageDraw.Draw(im)
    for r, p in enumerate(label_points(lab, len(regions))):
        if p is None:
            continue
        x, y = p[0] * sc + sc // 2, p[1] * sc + sc // 2
        text = regions[r]["id"]
        tw = dr.textlength(text)
        dr.rectangle([x - tw / 2 - 1, y - 6, x + tw / 2 + 1, y + 5], fill=(0, 0, 0))
        dr.text((x - tw / 2, y - 6), text, fill=(255, 255, 255))
    return im


def heat(h, mask):
    import matplotlib
    cmap = matplotlib.colormaps["inferno"]
    v = np.where(mask, h, np.nan)
    lo, hi = np.nanmin(v), np.nanmax(v)
    t = (v - lo) / max(hi - lo, 1e-6)
    rgb = (cmap(np.nan_to_num(t))[..., :3] * 255).astype(np.uint8)
    rgb[~mask] = 20
    return rgb, lo, hi


def write(s, a, out=None):
    from PIL import Image, ImageDraw
    out = Path(out or work_dir(s["name"]))
    out.mkdir(parents=True, exist_ok=True)
    idx, lab, L = s["idx"], a["lab"], a["L"]
    H, W = idx.shape
    relief = relief_field(L, lab)
    regions = a["regions"]
    solved, surface = SP.solve(regions, (H, W), SS, relief=relief, amodal=amodal_masks(regions, (H, W)),
                               groups=a["groups"])
    for r in regions:
        base, field = solved[r["id"]]
        r["base_inferred"] = round(base, 2)
        r["top_z_inferred"] = round(float(np.nanmax(field)), 2) if np.isfinite(field).any() else base
    hmask = ~np.isnan(surface)
    hs = np.nan_to_num(surface)
    n = normals_of(hs)
    doc = {
        "name": s["name"], "version": VERSION, "size": [W, H], "ss": SS,
        "light": [round(float(v), 3) for v in a["light"]],
        "pieces": s["pieces"], "units_per_px": 1 / 12,
        "colors": {str(k): list(v) for k, v in s["colors"].items()},
        "model": {"tri_budget": None}, "groups": a["groups"],
        "keys": {"top": "profile height above base, px", "base": "foot z in px, null = sit on `on`",
                 "bevel": "flat: chamfer width px", "taper": "taper: height scale -t..+t from top to bottom end",
                 "recess_depth": "recess: depth px", "relief": "brightness relief amplitude px",
                 "order": "stack order", "profile": "/".join(SP.PROFILES)},
        "regions": regions,
    }
    (out / "regions.json").write_text(json.dumps(doc, indent=1))
    np.savez_compressed(out / "analysis.npz", idx=idx, lab=lab, L=L, relief=relief, height=hs,
                        height_mask=hmask, normals=n)
    sc = scale_for(W)
    region_map_image(lab, regions, scale=sc).save(out / "regions.png")
    region_map_image(lab, regions, idx, s["colors"], scale=sc).save(out / "regions-on-sprite.png")
    rgb, lo, hi = heat(hs, hmask)
    him = Image.fromarray(rgb).resize((W * SS * sc // 2, H * SS * sc // 2), Image.NEAREST)
    ImageDraw.Draw(him).text((4, 4), f"height {lo:.1f}..{hi:.1f} px", fill=(255, 255, 255))
    him.save(out / "height.png")
    nrgb = ((n * 0.5 + 0.5) * 255).astype(np.uint8)
    nrgb[~hmask] = 20
    Image.fromarray(nrgb).resize((W * SS * sc // 2, H * SS * sc // 2), Image.NEAREST).save(out / "normals.png")
    # Shading check: the sprite's lightness beside the inferred shape lit by the fitted light.
    lit = np.clip((n * a["light"]).sum(axis=2), 0, 1)
    lit_px = lit.reshape(H, SS, W, SS).mean(axis=(1, 3))
    pair = np.concatenate([L / 100, lit_px], axis=1)
    pair[np.concatenate([idx < 0, idx < 0], axis=1)] = 0.08
    Image.fromarray((pair * 255).astype(np.uint8)).resize((2 * W * sc, H * sc), Image.NEAREST).save(out / "shading.png")
    Image.fromarray(rgb_image(idx, s["colors"])).resize((W * sc, H * sc), Image.NEAREST).save(out / "sprite.png")
    return out


def main(argv):
    names = [a for a in argv if not a.startswith("--")]
    for name in names:
        s = load(name)
        a = analyse(s)
        out = write(s, a)
        counts = {}
        for r in a["regions"]:
            counts[r["profile"]] = counts.get(r["profile"], 0) + 1
        print(f"{name}: {len(a['regions'])} regions {counts}, light {np.round(a['light'], 2)} -> {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
