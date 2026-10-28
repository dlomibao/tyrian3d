"""Region parameters -> heights. Numpy only, so Blender's Python and the analyser share it.

A region is a dict from regions.json (tools/sprite_shape.py), merged with its overrides:

    id         "r12": stable for a given sprite and analyser version (raster order of each
               region's first pixel)
    mask       {"x": x0, "y": y0, "w": w, "h": h, "rle": "..."}: pixels in the composed sprite
    profile    "round" | "flat" | "dome" | "taper" | "recess" | "void"
    top        height of the profile above its base, in sprite px (12 px = 1 unit)
    base       z of its foot in px, or null to sit on the regions in `on` (the median height of
               their surface along the shared border, plus `base_offset`)
    bevel      flat: width (and height) of the 45-degree chamfer round its top edge, px
    taper      taper: height scale from the region's top end (1 - taper) to its bottom end (1 + taper)
               along sprite Y, so a negative value makes the top end taller
    recess_depth  recess: depth below its base, px (its base is the surrounding surface)
    relief     amplitude of the brightness relief added to the top (detail: grilles, ribs), px
    order      stacking order (low first); regions are solved in this order
    on         ids of the regions it sits on
    group      id of a body ("g0") in the model's `groups`: the region's surface is the body's (one
               union of balls over all its regions' pixels, scaled to the group's `top`) plus the
               region's own profile as an offset (a band round a pod, a recessed vent in a hull)

Heights are sampled at `ss` x `ss` points per sprite pixel (ss = 2: half-pixel cells).
"""

import numpy as np

PROFILES = ("round", "flat", "dome", "taper", "recess", "void")


# --- Masks ---------------------------------------------------------------------------------------

def rle_encode(mask):
    """Run lengths of a bool array in raster order, starting with a run of False."""
    flat = np.asarray(mask, dtype=bool).ravel()
    runs, cur, n = [], False, 0
    for v in flat:
        if v == cur:
            n += 1
        else:
            runs.append(n)
            cur, n = v, 1
    runs.append(n)
    return " ".join(map(str, runs))


def rle_decode(rle, w, h):
    out = np.zeros(w * h, dtype=bool)
    pos, val = 0, False
    for n in map(int, rle.split()):
        if val:
            out[pos:pos + n] = True
        pos += n
        val = not val
    return out.reshape(h, w)


def region_mask(region, shape):
    """The region's mask as a full-size bool array (shape = composed sprite H x W)."""
    m = region["mask"]
    full = np.zeros(shape, dtype=bool)
    full[m["y"]:m["y"] + m["h"], m["x"]:m["x"] + m["w"]] = rle_decode(m["rle"], m["w"], m["h"])
    return full


def upsample(mask, ss):
    return np.repeat(np.repeat(mask, ss, axis=0), ss, axis=1)


# --- Distances -----------------------------------------------------------------------------------

def _shift_any(mask):
    """Pixels outside `mask` with a 4-neighbour inside it."""
    p = np.pad(mask, 1)
    nb = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return nb & ~mask


def edge_distance(mask, ss=1, chunk=4096):
    """For each sample inside `mask` (a grid of ss samples per px), the distance in px from its
    centre to the mask's edge (the nearest outside sample's centre, less half a sample)."""
    pad = np.pad(mask, 1)
    outside = _shift_any(pad)
    oy, ox = np.nonzero(outside)
    iy, ix = np.nonzero(pad)
    d = np.zeros(pad.shape)
    if len(iy) and len(oy):
        best = np.empty(len(iy))
        for s in range(0, len(iy), chunk):
            dy = iy[s:s + chunk, None] - oy[None, :]
            dx = ix[s:s + chunk, None] - ox[None, :]
            best[s:s + chunk] = np.sqrt((dy * dy + dx * dx).min(axis=1))
        d[iy, ix] = (best - 0.5) / ss
    return d[1:-1, 1:-1]


def ball_union(mask, d, ss=1, chunk=2048):
    """Height of the union of balls centred on the mask's samples, each as wide as its distance to
    the edge: tubes come out round, discs as hemispheres, tapering shapes as tapering tubes."""
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return np.zeros(mask.shape)
    r = d[ys, xs]
    # Centres: samples on the ridge of the distance field (no neighbour clearly further in).
    p = np.pad(d, 1)
    nbmax = np.max([p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx]
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx], axis=0)
    ridge = (d >= nbmax[...] - 0.5 / ss) & mask
    cy, cx = np.nonzero(ridge)
    cr = d[cy, cx] + 0.5 / ss
    h = np.zeros(len(ys))
    for s in range(0, len(ys), chunk):
        dy = (ys[s:s + chunk, None] - cy[None, :]) / ss
        dx = (xs[s:s + chunk, None] - cx[None, :]) / ss
        h2 = cr[None, :] ** 2 - dy * dy - dx * dx
        h[s:s + chunk] = np.sqrt(np.clip(h2.max(axis=1), 0, None))
    out = np.zeros(mask.shape)
    out[ys, xs] = np.maximum(h, 0)
    return out


# --- Profiles ------------------------------------------------------------------------------------

def profile_height(region, mask, ss=2, relief=None, cache=None):
    """The region's height above its base at each sample of `mask` (an ss-upsampled bool array
    covering the region, plus whatever regions on top of it hide, see sprite_shape.amodal)."""
    kind = region["profile"]
    top = float(region.get("top", 0.0))
    d = edge_distance(mask, ss)
    if kind in ("round", "taper"):
        h = ball_union(mask, d, ss)
        hmax = h.max() if h.max() > 0 else 1.0
        h = h / hmax * top
        if kind == "taper":
            t = float(region.get("taper", 0.0))
            ys = np.nonzero(mask.any(axis=1))[0]
            y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, 1)
            yy = (np.arange(mask.shape[0])[:, None] - y0) / max(1, y1 - y0)
            h = h * np.clip(1 - t + 2 * t * yy, 0.05, None)
    elif kind == "dome":
        dmax = d.max() if d.max() > 0 else 1.0
        u = np.clip(d / dmax, 0, 1)
        h = top * np.sqrt(np.clip(1 - (1 - u) ** 2, 0, 1))
    elif kind == "flat":
        b = max(0.0, float(region.get("bevel", 0.0)))
        if b > 0:
            h = np.minimum(top, top - b + np.clip(d + 0.5 / ss, 0, None))
            h = np.clip(h, 0, None)
        else:
            h = np.full(mask.shape, top)
    elif kind == "recess":
        h = np.full(mask.shape, -float(region.get("recess_depth", 1.0)))
    elif kind == "void":
        h = np.full(mask.shape, top)
    else:
        raise ValueError(f"unknown profile {kind!r} in region {region.get('id')}")
    amp = float(region.get("relief", 0.0))
    if amp and relief is not None and kind != "recess":
        h = h + amp * relief
    return np.where(mask, h, 0.0)


def body_fields(regions, shape, groups, ss=2):
    """{group id: height field (full size, ss samples per px)} for each body in `groups`
    ({id: {"top": px, "squash": optional}}): the union of balls over its regions, scaled to top."""
    out = {}
    for gid, g in (groups or {}).items():
        m = np.zeros(shape, dtype=bool)
        for r in regions:
            if r.get("group") == gid and not r.get("hide"):
                m |= region_mask(r, shape)
        if not m.any():
            continue
        mu = upsample(m, ss)
        h = ball_union(mu, edge_distance(mu, ss), ss)
        out[gid] = h / max(h.max(), 1e-6) * float(g.get("top", h.max()))
    return out


def solve(regions, shape, ss=2, relief=None, amodal=None, groups=None):
    """Heights for every region, bottom first: {id: (base, top_field)} where top_field is the
    absolute z (px) at each sample of the full ss-upsampled sprite (nan outside the region), and
    the composite height field (the highest surface at each sample).

    relief: a full-size (ss-upsampled) array in -1..1 (sprite_shape writes one); amodal: {id: extra
    pixel mask (full size) the profile also covers, hidden under regions on top}."""
    H, W = shape
    by_id = {r["id"]: r for r in regions}
    masks = {r["id"]: region_mask(r, shape) for r in regions}
    surface = np.full((H * ss, W * ss), np.nan)
    result = {}
    bodies = body_fields(regions, shape, groups, ss)
    for r in sorted(regions, key=lambda r: (r.get("order", 0), r["id"])):
        rid = r["id"]
        m = upsample(masks[rid], ss)
        prof_mask = m
        if amodal and rid in amodal and amodal[rid] is not None:
            prof_mask = m | upsample(amodal[rid], ss)
        base = r.get("base")
        if base is None:
            base = _support_height(m, [by_id[o] for o in r.get("on", []) if o in by_id], result, ss)
            base += float(r.get("base_offset", 0.0))
        h = profile_height(r, prof_mask, ss, relief=relief)
        if r.get("group") in bodies:
            h = h + bodies[r["group"]]
        field = np.where(m, base + h, np.nan)
        result[rid] = (float(base), field)
        surface = np.where(m, field, surface)
    return result, surface


def _support_height(m, supports, solved, ss):
    """Median surface height of the supporting regions along the border of `m` (0 if none)."""
    if not supports:
        return 0.0
    ring = _shift_any(m)
    # A slightly wider ring, so supports separated by an outline sample still count.
    ring2 = _shift_any(m | ring) | ring
    vals = []
    for s in supports:
        if s["id"] not in solved:
            continue
        f = solved[s["id"]][1]
        v = f[ring2 & ~np.isnan(f)]
        if v.size:
            vals.append(v)
    if not vals:
        return 0.0
    return float(np.median(np.concatenate(vals)))
