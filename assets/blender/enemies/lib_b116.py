"""Helpers shared by batch b116's models (a rock pile made of 2x2 ground pieces).

- composite: the pieces' first frames pasted into one pixel grid in assembly coordinates.
- segment: split the grid into rocks, grown from hand-placed seeds (one or more per rock) along
  the cheapest path, where crossing a shading jump, a colour family change or a dark crevice is
  expensive, so each rock's region follows the boundaries drawn in the sprite.
- boulder: a faceted rock over a region: its outline (traced from the centroid outwards) at the
  ground, bevelled shoulders and a ridge peaking where the rock's highlight is. Every face takes
  the palette index of the sprite pixel of that rock nearest to it, so the top view keeps the
  sprite's shading and the facets give it real relief.
"""

import heapq
import math

# Palette families of the rock pile (newshr.shp, palette 5): brown 160-173, gold 20-28, grey 2-10.
CREVICE = {1, 80, 160}  # outline and the darkest gaps between rocks


def family(v):
    if 160 <= v <= 173:
        return "brown", v - 162
    if 20 <= v <= 28:
        return "gold", v - 20
    if 2 <= v <= 10:
        return "grey", v - 3
    return "other", 0


def composite(load_sprite, root, layout, x0, y0, w, h):
    """Grid h x w of palette indices (-1 empty) and merged colours. layout is
    [(piece, cx, cy)] in screen px; grid pixel (c, r) is screen pixel (x0 + c, y0 + r)."""
    grid = [[-1] * w for _ in range(h)]
    colors = {}
    for name, cx, cy in layout:
        data = load_sprite(root, name)
        colors.update(data["colors"])
        px0, py0 = cx - 12 - x0, cy - 14 - y0
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v != -1 and 0 <= py0 + r < h and 0 <= px0 + c < w:
                    grid[py0 + r][px0 + c] = v
    return grid, colors


def outer_outline(grid):
    """Dark pixels touching the empty outside (4-neighbours): the sprite's outline, not modelled."""
    h, w = len(grid), len(grid[0])
    out = set()
    for r in range(h):
        for c in range(w):
            v = grid[r][c]
            if v in CREVICE:
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rr, cc = r + dr, c + dc
                    if not (0 <= rr < h and 0 <= cc < w) or grid[rr][cc] == -1:
                        out.add((r, c))
                        break
    return out


def segment(grid, seeds, skip):
    """Assign every non-empty pixel not in `skip` to a rock. seeds: list of lists of (col, row).
    Returns a label grid (-1 = none)."""
    h, w = len(grid), len(grid[0])
    INF = float("inf")
    dist = [[INF] * w for _ in range(h)]
    lab = [[-1] * w for _ in range(h)]
    heap = []
    for k, pts in enumerate(seeds):
        for c, r in pts:
            dist[r][c] = 0
            lab[r][c] = k
            heapq.heappush(heap, (0.0, r, c, k))

    def cost(a, b):
        if b in CREVICE:
            return 6.0
        fa, ta = family(a)
        fb, tb = family(b)
        if a in CREVICE:
            return 1.0
        if fa != fb:
            return 25.0
        return 1.0 + 2.5 * abs(ta - tb) ** 1.5

    while heap:
        d, r, c, k = heapq.heappop(heap)
        if d > dist[r][c]:
            continue
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if not (0 <= rr < h and 0 <= cc < w) or grid[rr][cc] == -1 or (rr, cc) in skip:
                continue
            nd = d + cost(grid[r][c], grid[rr][cc])
            if nd < dist[rr][cc]:
                dist[rr][cc] = nd
                lab[rr][cc] = k
                heapq.heappush(heap, (nd, rr, cc, k))
    return lab


def depth_map(grid, skip):
    """Chamfer distance (px) of every pixel from the outside of the pile."""
    h, w = len(grid), len(grid[0])
    INF = 1e9
    d = [[0.0 if grid[r][c] == -1 or (r, c) in skip else INF for c in range(w)] for r in range(h)]
    for r in range(h):
        for c in range(w):
            if r == 0 or c == 0 or r == h - 1 or c == w - 1:
                d[r][c] = min(d[r][c], 1.0)
    for _ in range(2):
        for r in range(h):
            for c in range(w):
                for dr, dc, s in ((-1, 0, 1), (0, -1, 1), (-1, -1, 1.414), (-1, 1, 1.414)):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w:
                        d[r][c] = min(d[r][c], d[rr][cc] + s)
        for r in range(h - 1, -1, -1):
            for c in range(w - 1, -1, -1):
                for dr, dc, s in ((1, 0, 1), (0, 1, 1), (1, 1, 1.414), (1, -1, 1.414)):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w:
                        d[r][c] = min(d[r][c], d[rr][cc] + s)
    return d


def region_outline(pixels, centre, n=16, pad=0.5):
    """Radii (px) of the region around `centre` (col, row) at n angles: how far a ray stays on the
    region (allowing 2 px gaps), plus `pad` for the pixel's extent."""
    s = set(pixels)
    cx, cy = centre
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        dx, dy = math.cos(a), -math.sin(a)  # rows grow downwards; angle counter-clockwise on screen
        t, last, miss = 0.0, 0.0, 0.0
        while t < 80:
            c, r = int(math.floor(cx + 0.5 + dx * t)), int(math.floor(cy + 0.5 + dy * t))
            if (c, r) in s:
                last, miss = t, 0.0
            else:
                miss += 0.25
                if miss > 2.0:
                    break
            t += 0.25
        out.append(max(last + pad, 1.0))
    return out


def boulder(bm, region, colors_at, centre, peak, z_top, X, Y, to_px, mat_of, n=16, z_base=0.0,
            relief=0.12):
    """A faceted rock over `region` (list of (col, row)). centre: (col, row) the rings are traced
    from; peak: (col, row) the top ridge leans to; z_top its top height. X, Y map pixel columns and
    rows to Blender and to_px(vector) back to (col, row). mat_of(index) -> material slot.
    colors_at(col, row) -> palette index of the rock's pixel nearest that point."""
    radii = region_outline(region, centre, n)
    relief = min(relief, 0.3 * sum(radii) / n / 12)  # small rocks stay rounded, not spiky
    cx, cy = centre
    px_, py_ = peak
    # rings: (scale of the outline, blend toward the peak, height)
    rings = [(1.0, 0.0, z_base), (0.97, 0.0, z_top - relief * 1.0), (0.84, 0.1, z_top - relief * 0.4),
             (0.6, 0.3, z_top - relief * 0.15), (0.3, 0.6, z_top - relief * 0.03)]
    verts = []
    for scale, pull, z in rings:
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            rc = cx + math.cos(a) * radii[i] * scale
            rr = cy - math.sin(a) * radii[i] * scale
            rc += (px_ - cx) * pull
            rr += (py_ - cy) * pull
            ring.append(bm.verts.new((X(rc), Y(rr), max(z, z_base))))
        verts.append(ring)
    top = bm.verts.new((X(px_), Y(py_), z_top))
    faces = []
    for r0, r1 in zip(verts, verts[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((verts[-1][i], verts[-1][j], top)))
    bottom = bm.faces.new(list(reversed(verts[0])))
    faces.append(bottom)
    for f in faces:
        f.material_index = mat_of(colors_at(*to_px(f.calc_center_median())))
    return faces
