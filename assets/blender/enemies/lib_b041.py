"""Helpers for batch b041 (the newsh8 rock fortress, assembly-newsh8-243): the assembled pixel
grid, a watershed that splits the rock into its boulders, a boulder (pod) builder and a painter
that colours each face with the sprite pixel under it.

The segmentation part imports nothing from Blender so it can be checked with plain python3.
"""

import heapq
import json
import math
from pathlib import Path


# --- the assembled sprite ------------------------------------------------------------------------

def assembled_grid(root, layout, origin, size, frames=None):
    """Palette indices of the whole object (-1 transparent): layout entries are sprite.json
    assemblyLayout dicts; `origin` is the screen pixel (cx, cy) of grid cell (0, 0)'s corner and
    `size` (w, h) the grid size. `frames` overrides the frame index per model."""
    w, h = size
    grid = [[-1] * w for _ in range(h)]
    cache = {}
    for e in layout:
        name = e["model"]
        if name not in cache:
            cache[name] = json.loads((Path(root) / "reference" / "models" / name / "sprite.json").read_text())
        idx = int(e["frame"].split("|")[2])
        if frames and name in frames:
            idx = frames[name]
        frame = next(f for f in cache[name]["frames"] if f["index"] == idx)
        x0, y0 = e["cx"] - 12 - origin[0], e["cy"] - 14 - origin[1]
        for r, line in enumerate(frame["pixels"]):
            vals = line.split() if isinstance(line, str) else line
            for c, v in enumerate(vals):
                v = int(v)
                if v >= 0:
                    grid[y0 + r][x0 + c] = v
    return grid


# --- watershed ---------------------------------------------------------------------------------

def blur(values, mask, rx=1, ry=1):
    """Box blur of `values` over the mask cells only."""
    h, w = len(values), len(values[0])
    out = [[0.0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if not mask[r][c]:
                continue
            s = n = 0
            for dr in range(-ry, ry + 1):
                for dc in range(-rx, rx + 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and mask[rr][cc]:
                        wt = 1.0 / (1 + abs(dr) + abs(dc))
                        s += values[rr][cc] * wt
                        n += wt
            out[r][c] = s / n
    return out


def watershed(values, mask, radius=2, min_size=8, rx=1, ry=1):
    """Split the mask into regions around the local maxima of the blurred `values` (bright
    boulder tops), flooding downhill so regions meet along the dark cracks. Regions smaller than
    `min_size` px are merged into the neighbour they share most border with. Returns a label grid
    (-1 outside the mask) and the number of labels."""
    h, w = len(values), len(values[0])
    b = blur(values, mask, rx, ry)
    labels = [[-1] * w for _ in range(h)]
    seeds = []
    for r in range(h):
        for c in range(w):
            if not mask[r][c]:
                continue
            v = b[r][c]
            best = True
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    rr, cc = r + dr, c + dc
                    if (dr or dc) and 0 <= rr < h and 0 <= cc < w and mask[rr][cc]:
                        o = b[rr][cc]
                        # ties go to the earlier cell so plateaus get one seed
                        if o > v or (o == v and (rr, cc) < (r, c)):
                            best = False
            if best:
                seeds.append((r, c))
    heap = []
    for i, (r, c) in enumerate(seeds):
        labels[r][c] = i
        heapq.heappush(heap, (-b[r][c], r, c))
    while heap:
        _, r, c = heapq.heappop(heap)
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w and mask[rr][cc] and labels[rr][cc] < 0:
                labels[rr][cc] = labels[r][c]
                heapq.heappush(heap, (-b[rr][cc], rr, cc))
    # Unreached mask cells (islands without a seed) get their own label.
    n = len(seeds)
    for r in range(h):
        for c in range(w):
            if mask[r][c] and labels[r][c] < 0:
                stack = [(r, c)]
                labels[r][c] = n
                while stack:
                    a, bb = stack.pop()
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        rr, cc = a + dr, bb + dc
                        if 0 <= rr < h and 0 <= cc < w and mask[rr][cc] and labels[rr][cc] < 0:
                            labels[rr][cc] = n
                            stack.append((rr, cc))
                n += 1
    # Merge small regions.
    while True:
        sizes = {}
        for r in range(h):
            for c in range(w):
                if labels[r][c] >= 0:
                    sizes[labels[r][c]] = sizes.get(labels[r][c], 0) + 1
        small = [k for k, s in sizes.items() if s < min_size]
        if not small:
            break
        k = min(small, key=lambda k: sizes[k])
        border = {}
        for r in range(h):
            for c in range(w):
                if labels[r][c] != k:
                    continue
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and labels[rr][cc] >= 0 and labels[rr][cc] != k:
                        border[labels[rr][cc]] = border.get(labels[rr][cc], 0) + 1
        if not border:
            sizes.pop(k)
            # an isolated speck: keep it but stop considering it
            for r in range(h):
                for c in range(w):
                    if labels[r][c] == k:
                        labels[r][c] = -2 - k  # parked; restored below
            continue
        to = max(border, key=border.get)
        for r in range(h):
            for c in range(w):
                if labels[r][c] == k:
                    labels[r][c] = to
    for r in range(h):
        for c in range(w):
            if labels[r][c] <= -2:
                labels[r][c] = -2 - labels[r][c]
    # Renumber.
    ids = {}
    for r in range(h):
        for c in range(w):
            if labels[r][c] >= 0:
                labels[r][c] = ids.setdefault(labels[r][c], len(ids))
    return labels, len(ids)


def regions(labels, n):
    """Per label: {row: (cmin, cmax)} and the pixel list."""
    out = [dict(rows={}, px=[]) for _ in range(n)]
    for r, line in enumerate(labels):
        for c, k in enumerate(line):
            if k < 0:
                continue
            reg = out[k]
            reg["px"].append((r, c))
            lo, hi = reg["rows"].get(r, (c, c))
            reg["rows"][r] = (min(lo, c), max(hi, c))
    return out


def write_png(path, rows):
    """Write an RGBA image (rows of (r, g, b, a) 0-255 tuples, top row first) as a PNG."""
    import struct
    import zlib
    h, w = len(rows), len(rows[0])
    raw = b"".join(b"\0" + bytes(v for px in row for v in px) for row in rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


# --- geometry (Blender) --------------------------------------------------------------------------

def pod(bm, sections, sides=8, mat_index=0, z0=0.0):
    """A boulder lofted down the sprite: sections are (y, x_left, x_right, up, down) in units,
    each a ring whose top arc rises `up` above z0 and whose bottom sinks `down` below it.
    The ends are closed by a single point at the end ring's centre, slightly raised."""
    rings = []
    for y, xl, xr, up, down in sections:
        cx, hw = (xl + xr) / 2, (xr - xl) / 2
        ring = []
        for i in range(sides):
            a = 2 * math.pi * i / sides
            s = math.sin(a)
            ring.append(bm.verts.new((cx + hw * math.cos(a), y, z0 + (up if s > 0 else down) * s)))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mat_index
            faces.append(f)
    for ring, (y, xl, xr, up, down) in ((rings[0], sections[0]), (rings[-1], sections[-1])):
        tip = bm.verts.new(((xl + xr) / 2, y, z0 + (up - down) * 0.25))
        for i in range(sides):
            j = (i + 1) % sides
            f = bm.faces.new((ring[i], ring[j], tip))
            f.material_index = mat_index
            faces.append(f)
    return faces
