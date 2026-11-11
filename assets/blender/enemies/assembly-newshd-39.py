"""Rock outcrop (newshd.shp 1, 3, 39, 41: an assembly of 4 pieces): a 3D version of its sprites.

Seen in levels 1.1 (ASTEROID1) and 1.3 (ASTEROID?). Four 2x2 ground enemies side by side make one
48 x 56 px heap of grey, faceted boulders lit from the upper left, dark cracks between them.
Final of design B (silhouette first), with the judge's grafts (D65 standard, D50-D53).

Ten big, clearly separate boulders with deep V cracks between them, each a chunky solid of a few
dozen PLANAR fracture faces (a convex hull of its sections, chamfered), never a lumpy blob, and a
footprint that is the sprite's outline.

Construction:
  1. The sprite's inner mask (tools/sprite_mask.py, D74: the ink ring is the game's outline) is cut
     into ten cells (PARTS: footprints from the blueprint; leftover pixels to the nearest peak).
     Each cell grows GROW px into its neighbours, so neighbouring boulders interpenetrate and meet
     in V cracks low down (the rock's "panel lines").
  2. Each boulder: its foot polygon (pixel outline through the pixel-edge midpoints: no staircase)
     at z 0, then sections stepped in towards the crown along a pchip profile per kind, jittered;
     the convex hull of those points gives planar fracture faces; coplanar triangles merge; then
     every edge gets a small chamfer.
       dome / ridge / flat / crater kinds as in PARTS. The 'peak' ridge has a blunt, rounded crown
       (wide chamfer, flattened top station, 9.5 px high) so the crater (11.2) stays the highest lit
       mass, as in the sprite (judge graft from design A).
  3. Each boulder is intersected with the outline clip: the union's top view is the sprite's inner
     mask row by row. The clip is vertical for 0.5 px, then leans in along CLIP_PROFILE (3.6 px at
     16 px up) and is simplified at CLIP_TOL, so the outer flanks slope (no cliff walls, no sawtooth
     foot); every boulder's first station leans in TAPER_PX, which also deepens the V cracks between
     cells, the only dark lines (no decorative grooves: the sprite draws none).
     'flat' cells carry a low dome on their tilted fracture plane; the crater's rim rolls into the
     slope through a shoulder ring.
  4. Palette: each boulder takes the median of its cell's sprite pixels between the 15th and 85th
     luminance percentile (ink, deepest shading and brightest glints are lighting). DEVIATION from
     the blueprint's guess: peak and spur are pal_8 (blueprint 7), leftlobe is pal_6 (blueprint 7);
     the sprite's own pixels say 8, 8, 6, so the sprite wins. pal_8 is (105,109,105), faintly green;
     the bake only multiplies by a grey AO term, so it adds no saturation.
     Rock: metallic 0, roughness 0.85. AO/edge colour multiplier + roughness bake per piece, no
     concept projection (--no-bake to skip).
  5. Outline shell (D51) of the whole heap cut open at the piece boxes (about the rock's triangle
     count x1.5), then common.split_assembly cuts newshd-1 / -3 / -39 / -41, one frame each.
  6. It drifts in space (ASTEROID1, spawned on the sky/ground/top layers; D120/D122): no base and no
     skirt. A round closed lens (belly_object) hangs under the heap, its waist the inner outline at
     z 0, with D125's few underside fracture planes; each face takes the colour of the cell above.
     The boulders take D125's rock material (matte, metallic 0, roughness 0.9) and each hull is
     broken by FINE small fracture faces (lib_newshd_rock.cut_planes) so no big plane reads as
     plastic.
Underside: the belly, a plausible closed shape only. Nothing more.

Run: blender -b --factory-startup --python assets/blender/enemies/assembly-newshd-39.py -- [--no-bake]
     [--no-export] [--design-out whole.glb] [--render DIR]
"""

import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
WT = ROOT
sys.path.insert(0, str(ROOT / "tools"))
import sprite_mask as SM  # noqa: E402
import usp_talon as T  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshd_rock as RL  # noqa: E402  (D125's fracture cuts, read only)
from mathutils import noise  # noqa: E402

PARTS = [
    {"name": "peak", "pal": 7, "h": 11.5, "kind": "ridge", "peak": [-1.74, 16.9], "footprint": [[5, 17.5], [5, 19.5], [3.17, 21], [1.33, 22.5], [-0.5, 24], [-3, 24], [-5.5, 24], [-7.75, 22.75], [-10, 21.5], [-10, 19.5], [-10, 17.5], [-9, 16.5], [-9, 14.5], [-7.75, 13.25], [-6.5, 12], [-4.5, 12], [-3.5, 11], [-1.5, 11], [0.5, 11], [2.25, 12.75], [4, 14.5], [4, 16.5]], "crest": [[1.5, 21.5], [-1.5, 12.5]]},
    {"name": "shelf", "pal": 4, "h": 6.3, "kind": "flat", "peak": [7.78, 14.26], "footprint": [[16, 11.5], [14.5, 13], [13, 14.5], [13, 16.5], [11.75, 17.75], [10.5, 19], [8, 19], [5.5, 19], [4.67, 17.17], [3.83, 15.33], [3, 13.5], [3, 12.5], [4.25, 11.25], [5.5, 10], [8.5, 10], [11.5, 10], [14.5, 10]]},
    {"name": "leftrock", "pal": 6, "h": 8.6, "kind": "dome", "peak": [-12.68, 12.06], "footprint": [[-7, 11.5], [-7, 12.5], [-9, 14.5], [-9.5, 17], [-12.5, 17], [-15.5, 17], [-17.25, 15.25], [-19, 13.5], [-19, 11], [-19, 8.5], [-16.5, 8.33], [-14, 8.17], [-11.5, 8], [-9.25, 9.75]]},
    {"name": "crater", "pal": 10, "h": 12.6, "kind": "crater", "peak": [-4.51, 5.13], "footprint": [[1, 1.5], [1, 4.17], [1, 6.83], [1, 9.5], [-0.5, 11], [-2.5, 11.33], [-4.5, 11.67], [-6.5, 12], [-8.33, 10.5], [-10.17, 9], [-12, 7.5], [-12, 4.5], [-11, 3.5], [-11, 1.5], [-9.5, 0], [-7.17, 0], [-4.83, 0], [-2.5, 0], [-0.75, 0.75]]},
    {"name": "spur", "pal": 7, "h": 9.2, "kind": "dome", "peak": [4.16, 5.22], "footprint": [[8, 0.5], [8, 3], [8, 5.5], [7, 6.5], [7, 9.5], [4.75, 11.25], [2.5, 13], [1.25, 11.75], [0, 10.5], [1, 9.5], [1, 6.83], [1, 4.17], [1, 1.5], [0, 0.5], [2.67, 0.5], [5.33, 0.5]]},
    {"name": "rightrock", "pal": 5, "h": 8.6, "kind": "flat", "peak": [13.39, 5.43], "footprint": [[20, -1.5], [19.9, 1], [19.8, 3.5], [19.7, 6], [19.6, 8.5], [19.5, 11], [17, 10.7], [14.5, 10.4], [12, 10.1], [9.5, 9.8], [7, 9.5], [7.38, 7.13], [7.75, 4.75], [8.13, 2.38], [8.5, 0], [10.5, 0], [12, -1], [13.5, -2], [15.67, -1.83], [17.83, -1.67]]},
    {"name": "leftlobe", "pal": 7, "h": 8, "kind": "dome", "peak": [-15.19, 1.94], "footprint": [[-10, -2.5], [-11, -0.5], [-10, 0.5], [-11, 1.5], [-11.5, 3.67], [-12, 5.83], [-12.5, 8], [-15.5, 8], [-18.5, 8], [-20.25, 6.25], [-22, 4.5], [-22, 2.5], [-22, 0.5], [-20, -0.5], [-20, -2.5], [-18.5, -4], [-17, -5.5], [-15.75, -7.75], [-14.5, -10], [-13.25, -7.75], [-12, -5.5], [-12, -3.5]]},
    {"name": "boulder", "pal": 9, "h": 10.9, "kind": "ridge", "peak": [-3.73, -6.46], "footprint": [[5, -5.5], [5, -2.5], [3.5, 0], [0.5, 0], [-0.5, 1], [-2.5, 0], [-5.17, 0], [-7.83, 0], [-10.5, 0], [-11, -0.5], [-10, -2.5], [-12, -3.5], [-12, -5.5], [-13, -7], [-14, -8.5], [-11.75, -8.75], [-9.5, -9], [-7.5, -10], [-5.5, -11], [-3, -11], [-0.5, -11], [0.5, -10], [3.5, -10], [3.75, -8.25], [4, -6.5]], "crest": [[-6.5, -3.5], [-3, -9.8]]},
    {"name": "lowerright", "pal": 5, "h": 6.9, "kind": "flat", "peak": [8.28, -7.05], "footprint": [[20, -2.5], [17.83, -2.33], [15.67, -2.17], [13.5, -2], [12, -1], [10.5, 0], [7.5, 0], [4.5, 0], [4, -1.5], [5, -2.5], [5, -5.5], [4, -6.5], [4, -9], [4, -11.5], [5.5, -13], [7.5, -13], [9.5, -15], [11.5, -17], [13.5, -17], [13.67, -14.5], [13.83, -12], [14, -9.5], [15.5, -7.75], [17, -6], [18.5, -4.25]]},
    {"name": "toe", "pal": 5, "h": 6.9, "kind": "dome", "peak": [-4.3, -14.44], "footprint": [[11, -17.5], [11, -16.5], [9.25, -14.75], [7.5, -13], [5.5, -13], [4.5, -11.5], [3.5, -10], [0.5, -10], [-0.5, -11], [-3, -11], [-5.5, -11], [-7.5, -10], [-9.5, -9], [-11.75, -9.25], [-14, -9.5], [-14, -11.5], [-13, -13.5], [-12, -15.5], [-11, -17.5], [-9.75, -18.75], [-8.5, -20], [-6.5, -20], [-4.5, -22], [-2.5, -22], [-0.5, -22], [1, -21], [2.5, -20], [4.5, -20], [5.5, -19], [8.25, -18.25]]},
]

NAME = "assembly-newshd-39"
TAG = "nshd39B"
PIECES = ["newshd-1", "newshd-3", "newshd-39", "newshd-41"]
CX0, CY0 = 134, 43
W, H = 48, 56
PX = 1 / 12
GROW = 1          # px each cell grows into its neighbours (interpenetration -> V cracks)
HSCALE = 1.0      # height scale on the blueprint heights
CHAMFER = 0.28    # px, edge chamfer
SEED = 39
PIT_DEPTH = 1.1  # px, the crater's dish
PEBBLES = False  # rubble at the crack ends (hidden under the boulders' feet: off)
# The outline clip: (height px, inset px) stations. Vertical only for its first 0.5 px, then the
# outer flanks lean in visibly (no cliff walls where a boulder's hull bridges an outline notch).
CLIP_PROFILE = [(-0.2, 0.0), (0.5, 0.05), (3.0, 0.75), (8.0, 2.0), (16.0, 3.6)]
CLIP_TOL = 0.6    # px, Douglas-Peucker tolerance of the clip outline (0.3 left a sawtooth foot)
FOOT_TOL = 0.5    # px, the same for each boulder's foot
# Light comes from the upper left: "flat" fracture faces fall away to the lower right.
AWAY = Vector((0.8, -0.6)).normalized()

# Per-cell overrides on the blueprint (height px, kind) where B reads the sprite differently.
OVERRIDE = {
    "crater": {"h": 10.6},  # 12.6 stood up like a chimney in the tilted view
    "peak": {"h": 9.5},     # a rounded boulder under the crater, not a spike
}
BLUNT = {"peak": 0.75}      # ridge crown: share of the height the top stations keep (flat, rounded)
TAPER_PX = 1.5              # px they lean in at the first station
# D125's rock (lib_newshd_rock): matte stone, its lit faces read by their angle, no glint.
ROUGHNESS = 0.9
# Fine fracture faces per boulder (D125 `fine`): small planar spalls sliced off each hull so the big
# planes break up like the asteroid family's, never smooth plastic slabs.
FINE = (9, 0.03, 0.075)     # count, depth fractions lo / hi
# The floating rock's belly (D120/D122/D125: an asteroid drifting in space, no base): a closed,
# round lens under the heap whose waist is the sprite's inner outline at z 0.
BELLY_DEPTH = 10.5          # px below the waist
BELLY_SECTORS = 96
BELLY_CUTS = [(30, -55, 0.06), (150, -50, 0.06), (260, -58, 0.05), (100, -66, 0.05),
              (200, -30, 0.035), (320, -28, 0.035), (80, -32, 0.035), (235, -40, 0.04),
              (350, -45, 0.045), (120, -20, 0.025), (290, -22, 0.025), (10, -18, 0.02)]



# --- sprite ---------------------------------------------------------------------------------------

def sprite_data():
    idx, colors = SM.load(NAME)
    m = SM.masks(idx, colors)
    return idx, colors, m


def luma(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def inside(poly, x, y):
    n, c = len(poly), False
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def cells(m, parts):
    """label[y][x] = part index for every inner-mask pixel (-1 outside)."""
    inner = m["inner"]
    label = [[-1] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if not inner[y][x]:
                continue
            px, py = x + 0.5 - W / 2, H / 2 - y - 0.5
            hit = [i for i, p in enumerate(parts) if inside(p["footprint"], px, py)]
            if hit:
                label[y][x] = hit[0]
            else:
                label[y][x] = min(range(len(parts)), key=lambda i: (parts[i]["peak"][0] - px) ** 2
                                  + (parts[i]["peak"][1] - py) ** 2)
    return label


def cell_colour(idx, colors, label, i):
    vals = sorted((luma(colors[idx[y][x]]), idx[y][x]) for y in range(H) for x in range(W)
                  if label[y][x] == i and idx[y][x] in colors)
    lo, hi = int(len(vals) * 0.15), max(int(len(vals) * 0.85), int(len(vals) * 0.15) + 1)
    band = vals[lo:hi]
    return band[len(band) // 2][1]


def trace(mask):
    """Outer boundary of a pixel region along pixel corners (x right, y down), as a loop."""
    edges = {}
    for y in range(H):
        for x in range(W):
            if not mask[y][x]:
                continue
            def on(yy, xx):
                return 0 <= yy < H and 0 <= xx < W and mask[yy][xx]
            if not on(y - 1, x):
                edges[(x + 1, y)] = (x, y)
            if not on(y, x - 1):
                edges[(x, y)] = (x, y + 1)
            if not on(y + 1, x):
                edges[(x, y + 1)] = (x + 1, y + 1)
            if not on(y, x + 1):
                edges[(x + 1, y + 1)] = (x + 1, y)
    best, seen = [], set()
    for s in list(edges):
        if s in seen:
            continue
        loop, p = [], s
        while p not in seen and p in edges:
            seen.add(p)
            loop.append(p)
            p = edges[p]
        if len(loop) > len(best):
            best = loop
    return best


def midpoints(loop):
    """Corner loop -> polygon through the pixel-edge midpoints, in px frame (X right, Y up)."""
    out = []
    n = len(loop)
    for i in range(n):
        (x1, y1), (x2, y2) = loop[i], loop[(i + 1) % n]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        out.append((mx - W / 2, H / 2 - my))
    return out


def simplify(pts, tol):
    """Douglas-Peucker on a closed loop."""
    def dp(seq):
        if len(seq) < 3:
            return seq
        a, b = Vector(seq[0]), Vector(seq[-1])
        ab = b - a
        L = ab.length or 1e-9
        best, bi = 0, 0
        for i in range(1, len(seq) - 1):
            p = Vector(seq[i])
            d = abs(ab.x * (a.y - p.y) - ab.y * (a.x - p.x)) / L
            if d > best:
                best, bi = d, i
        if best <= tol:
            return [seq[0], seq[-1]]
        return dp(seq[:bi + 1])[:-1] + dp(seq[bi:])
    k = max(range(len(pts)), key=lambda i: pts[i][0] + 0.37 * pts[i][1])
    seq = pts[k:] + pts[:k]
    a = Vector(seq[0])
    j = max(range(len(seq)), key=lambda i: (Vector(seq[i]) - a).length)
    return dp(seq[:j + 1])[:-1] + dp(seq[j:] + [seq[0]])[:-1]


def dilate(mask, inner, n):
    for _ in range(n):
        out = [row[:] for row in mask]
        for y in range(H):
            for x in range(W):
                if mask[y][x] or not inner[y][x]:
                    continue
                if any(0 <= y + dy < H and 0 <= x + dx < W and mask[y + dy][x + dx]
                       for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                    out[y][x] = True
        mask = out
    return mask


# --- geometry --------------------------------------------------------------------------------------

def nearest_on_seg(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return a + ab * t


def boulder_points(foot, part, rng):
    """Section points (px) of one boulder; the hull of these is the rock."""
    h = part["h"] * HSCALE
    kind = part["kind"]
    peak = Vector(part["peak"])
    crest = [Vector(c) for c in part["crest"]] if part.get("crest") else None
    pts = [(x, y, 0.0) for x, y in foot]
    # (inset fraction towards the crown, height fraction); a pchip profile through these stations
    if kind == "flat":
        prof = [(0.0, 0.0), (0.12, 0.42), (0.3, 0.78), (0.5, 0.95)]
    else:
        prof = [(0.0, 0.0), (0.24, 0.36), (0.46, 0.72), (0.66, 0.92), (0.8, 0.99)]
    zf = T.pchip([s for s, _ in prof], [z for _, z in prof])
    stations = [0.14, 0.34, 0.56, 0.74] if kind != "flat" else [0.1, 0.24, 0.38, 0.5]
    for k, s in enumerate(stations):
        # thin the rings out as they rise (fewer, bigger facets near the crown)
        step = 1 if k == 0 else 2 + k // 2
        for j in range(0, len(foot), step):
            p = Vector(foot[j])
            c = nearest_on_seg(p, crest[0], crest[1]) if crest else peak
            q = p + (c - p) * (s + rng.uniform(-0.04, 0.04))
            if k == 0:  # the foot leans in: no cliff wall at the outline, deeper V cracks between cells
                d = (c - p).length
                if d > 1e-6:
                    q = q + (c - p) / d * min(TAPER_PX, 0.4 * d)
            z = h * zf(s) * (1 + rng.uniform(-0.06, 0.04))
            if part["name"] in BLUNT:
                z = min(z, h * BLUNT[part["name"]] + (h * 0.2) * max(0.0, s - 0.56) / 0.18)
            if kind == "flat":
                # the fracture plane: falls away from the light across the cell
                d = (q - peak).dot(AWAY)
                z = min(z, h - 0.32 * max(d, -3) + rng.uniform(-0.3, 0.3))
            pts.append((q.x, q.y, max(z, 0.4)))
    # crown
    if crest and part["name"] in BLUNT:
        # rounded crown: the crest line sags at both ends and the top is a wide pad, not an arris
        a, b = crest
        nrm = Vector((-(b - a).y, (b - a).x)).normalized()
        for t, f in ((0.12, 0.90), (0.35, 0.995), (0.65, 0.99), (0.88, 0.88)):
            c = a + (b - a) * t
            for off, ff in ((0.0, 1.0), (-2.2, 0.93), (2.2, 0.93)):
                q = c + nrm * off
                pts.append((q.x, q.y, h * f * ff))
    elif crest:
        a, b = crest
        for t, f in ((0.0, 0.93), (0.35, 1.0), (0.65, 0.99), (1.0, 0.9)):
            c = a + (b - a) * t
            pts.append((c.x, c.y, h * f))
    elif kind == "flat":
        # a low dome on the tilted fracture plane, not a table top
        def plane(q):
            return h - 0.32 * max((q - peak).dot(AWAY), -3)
        pts.append((peak.x, peak.y, plane(peak) + 0.9))
        for k in range(6):
            a = 2 * math.pi * k / 6 + rng.uniform(-0.2, 0.2)
            q = peak + Vector((math.cos(a), math.sin(a))) * rng.uniform(2.2, 2.8)
            pts.append((q.x, q.y, plane(q) + 0.55))
    elif kind == "crater":
        # the rim, then a shoulder ring that rolls it into the slope (no chimney walls)
        for k in range(9):
            a = 2 * math.pi * k / 9 + rng.uniform(-0.15, 0.15)
            r = 4.3 + rng.uniform(-0.3, 0.3)
            pts.append((peak.x + r * math.cos(a), peak.y + r * math.sin(a), h * rng.uniform(0.95, 1.0)))
        for k in range(11):
            a = 2 * math.pi * (k + 0.5) / 11 + rng.uniform(-0.12, 0.12)
            r = 6.0 + rng.uniform(-0.3, 0.3)
            pts.append((peak.x + r * math.cos(a), peak.y + r * math.sin(a), h * rng.uniform(0.82, 0.86)))
    else:
        r = 1.2
        for k in range(5):
            a = 2 * math.pi * k / 5 + rng.uniform(0, 1)
            pts.append((peak.x + r * math.cos(a), peak.y + r * math.sin(a), h * rng.uniform(0.96, 1.0)))
    return pts


def hull_object(name, pts, mat_index, mats, coll, fine=False):
    bm = bmesh.new()
    verts = [bm.verts.new(Vector(p) * PX) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    drop = [v for v in res["geom_interior"] + res["geom_unused"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.delete(bm, geom=list(set(drop)), context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(6.0), verts=bm.verts[:], edges=bm.edges[:])
    if fine:
        rng = random.Random(sum(map(ord, name)) * 7 + SEED)
        n, lo, hi = FINE
        cuts = []
        for k in range(n):
            az = (k * 137.508 + rng.uniform(-15, 15)) % 360
            el = rng.uniform(28, 74)
            cuts.append((az, el, rng.uniform(lo, hi)))
        RL.cut_planes(bm, cuts)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(3.0), verts=bm.verts[:], edges=bm.edges[:])
    for f in bm.faces:
        f.material_index = mat_index
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def offset_poly(poly, d):
    """Move each vertex of a CCW (Y up) polygon inwards by d along its averaged edge normal."""
    n = len(poly)
    out = []
    for i in range(n):
        a, b, c = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        def nrm(p, q):
            t = (q - p).normalized()
            return Vector((-t.y, t.x))  # left of the edge = inside for CCW
        m = nrm(a, b) + nrm(b, c)
        m = m.normalized() if m.length > 1e-6 else nrm(a, b)
        out.append(tuple(b + m * d))
    return out


def prism_object(name, poly, coll, profile=CLIP_PROFILE):
    """The outline clip: the outline at the ground, leaning in along `profile` (z px, inset px)."""
    area = sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))
    if area < 0:
        poly = poly[::-1]
    bm = bmesh.new()
    rings = [[bm.verts.new((x * PX, y * PX, z * PX)) for x, y in offset_poly(poly, d)] for z, d in profile]
    n = len(poly)
    for lo, hi in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def resample(poly, n):
    """A closed polygon resampled to n points evenly spaced along its length."""
    pts = [Vector(p) for p in poly]
    segs = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    total = sum((b - a).length for a, b in segs)
    out, k, acc = [], 0, 0.0
    for j in range(n):
        t = total * j / n
        while acc + (segs[k][1] - segs[k][0]).length < t:
            acc += (segs[k][1] - segs[k][0]).length
            k += 1
        a, b = segs[k]
        L = (b - a).length or 1e-9
        out.append(a + (b - a) * ((t - acc) / L))
    return out


def belly_object(outline, label, pal, used, mats, coll):
    """The floating rock's underside: a closed round lens under the heap (plausible shape only, no
    detail). Its waist is the inner outline at z 0 (inside the boulders' feet), its rings close in
    on the centroid as they fall, with D125's few underside fracture planes; a low hidden cap on top.
    Each face takes the palette index of the nearest sprite cell above it."""
    area = sum(outline[i - 1][0] * outline[i][1] - outline[i][0] * outline[i - 1][1] for i in range(len(outline)))
    poly = outline if area > 0 else outline[::-1]
    ring0 = [v for v in resample(offset_poly(poly, 0.15), BELLY_SECTORS)]
    c = sum(ring0, Vector((0, 0))) / len(ring0)
    off = Vector((SEED * 1.37, SEED * 0.61, 3.3))
    bm = bmesh.new()
    rings = []
    # bottom rings (phi from -90 towards 0), the waist, then a low cap hidden under the boulders
    # (scale towards the centroid, z px), bottom up: the flank rolls in from the waist at once (no
    # vertical skirt), a rounded lens under the heap
    stations = [(0.16, -10.2), (0.36, -9.3), (0.54, -8.0), (0.69, -6.4), (0.81, -4.7), (0.9, -3.0),
                (0.96, -1.4), (1.0, 0.2), (0.82, 1.0), (0.45, 1.8)]
    for s, z in stations:
        ring = []
        for p in ring0:
            q = c + (p - c) * s
            zz = z
            if z < 0:  # a lumpy stone underside, not a turned bowl
                zz += 1.4 * noise.noise(Vector((q.x * 0.09, q.y * 0.09, 0)) + off) * (1 - s) ** 0.5
            ring.append(bm.verts.new((q.x * PX, q.y * PX, zz * PX)))
        rings.append(ring)
    n = len(ring0)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(n):
            k = (j + 1) % n
            bm.faces.new((r0[j], r0[k], r1[k], r1[j]))
    vb = bm.verts.new((c.x * PX, c.y * PX, -BELLY_DEPTH * PX))
    vt = bm.verts.new((c.x * PX, c.y * PX, 2.1 * PX))
    for j in range(n):
        k = (j + 1) % n
        bm.faces.new((vb, rings[0][k], rings[0][j]))
        bm.faces.new((rings[-1][j], rings[-1][k], vt))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    RL.cut_planes(bm, BELLY_CUTS)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    cells_px = [(x + 0.5 - W / 2, H / 2 - y - 0.5, label[y][x]) for y in range(H) for x in range(W) if label[y][x] >= 0]
    for f in bm.faces:
        fc = f.calc_center_median() / PX
        lab = min(cells_px, key=lambda t: (t[0] - fc.x) ** 2 + (t[1] - fc.y) ** 2)[2]
        f.material_index = used.index(pal[lab])
    me = bpy.data.meshes.new("belly")
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new("belly", me)
    coll.objects.link(o)
    return o


def apply_mods(obj):
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def boolean(obj, other, op):
    mod = obj.modifiers.new(op, "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = other
    apply_mods(obj)


def pit_object(name, part, coll, rng):
    """The crater's faceted pit: a squashed low-poly sphere sunk into the crown."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    h = part["h"] * HSCALE
    px, py = part["peak"]
    R, depth = 6.0, PIT_DEPTH
    for v in bm.verts:
        k = 1 + rng.uniform(-0.04, 0.04)
        v.co = Vector(((px + v.co.x * R * k) * PX, (py + v.co.y * R * 0.92 * k) * PX,
                       (h - depth + R + v.co.z * R) * PX))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def chamfer(obj, width=CHAMFER):
    """A small chamfer on every fracture edge sharper than 15 degrees (bevel modifier, applied)."""
    mod = obj.modifiers.new("chamfer", "BEVEL")
    mod.width = width * PX
    mod.segments = 1
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(15)
    mod.use_clamp_overlap = True
    mod.harden_normals = False
    apply_mods(obj)


def crack_ends(label, inner):
    """Outline pixels (col, row) where two cells meet, one per crack, pulled 1.5 px inside."""
    out = []
    for y in range(H):
        for x in range(W):
            if not inner[y][x]:
                continue
            edge = any(not (0 <= y + dy < H and 0 <= x + dx < W and inner[y + dy][x + dx])
                       for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if not edge:
                continue
            nb = {label[y + dy][x + dx] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if 0 <= y + dy < H and 0 <= x + dx < W and label[y + dy][x + dx] >= 0}
            if len(nb) >= 2:
                out.append((x, y))
    # one per cluster, moved towards the heap's centre
    picked = []
    for x, y in out:
        if all((x - a) ** 2 + (y - b) ** 2 > 16 for a, b in picked):
            picked.append((x, y))
    res = []
    for x, y in picked:
        dx, dy = W / 2 - x, H / 2 - y
        L = math.hypot(dx, dy) or 1
        res.append((round(x + 1.5 * dx / L), round(y + 1.5 * dy / L)))
    return res


def build(coll, idx, colors, m):
    parts = [dict(p) for p in PARTS]
    for p in parts:
        if p["name"] in OVERRIDE:
            p.update(OVERRIDE[p["name"]])
    label = cells(m, parts)
    sprite = {"name": NAME, "colors": {str(k): list(v) for k, v in colors.items()}}
    pal = [cell_colour(idx, colors, label, i) for i in range(len(parts))]
    used = sorted(set(pal) | {4})
    mats = [common.palette_material(sprite, i, TAG, metallic=0.0, roughness=ROUGHNESS) for i in used]
    rng = random.Random(SEED)
    outline = simplify(midpoints(trace(m["inner"])), CLIP_TOL)
    prism = prism_object("clip", outline, coll)
    rocks = []
    info = []
    for i, part in enumerate(parts):
        cell = [[label[y][x] == i for x in range(W)] for y in range(H)]
        grown = dilate(cell, m["inner"], GROW)
        foot = simplify(midpoints(trace(grown)), FOOT_TOL)
        pts = boulder_points(foot, part, rng)
        o = hull_object(f"rock_{part['name']}", pts, used.index(pal[i]), mats, coll, fine=True)
        chamfer(o, 0.9 if part["name"] in BLUNT else CHAMFER)
        if part["kind"] == "crater":
            pit = pit_object("pit", part, coll, rng)
            boolean(o, pit, "DIFFERENCE")
            bpy.data.objects.remove(pit, do_unlink=True)
        boolean(o, prism, "INTERSECT")
        for f in o.data.polygons:  # faces the cutters made take slot 0: give them the rock's colour
            f.material_index = used.index(pal[i])
        rocks.append(o)
        info.append({"name": part["name"], "pal": pal[i], "blueprint_pal": part["pal"], "h": part["h"] * HSCALE,
                     "kind": part["kind"], "pixels": sum(map(sum, cell))})
    # Pebbles where a crack between two boulders runs out at the outline: rubble at the foot.
    for k, (c, r) in enumerate(crack_ends(label, m["inner"]) if PEBBLES else []):
        x, y = c + 0.5 - W / 2, H / 2 - r - 0.5
        vals = sorted((luma(colors[idx[yy][xx]]), idx[yy][xx]) for yy in range(r - 1, r + 2)
                      for xx in range(c - 1, c + 2) if 0 <= yy < H and 0 <= xx < W and m["inner"][yy][xx])
        pi = vals[len(vals) // 2][1] if vals else 5
        pi = pi if pi in used else min(used, key=lambda u: abs(u - pi))
        rad = rng.uniform(1.6, 2.3)
        pts = []
        for j in range(9):
            a = 2 * math.pi * j / 9 + rng.uniform(-0.2, 0.2)
            rr = rad * rng.uniform(0.8, 1.1)
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a), 0.0))
            pts.append((x + 0.6 * rr * math.cos(a + 0.3), y + 0.6 * rr * math.sin(a + 0.3), rad * rng.uniform(0.9, 1.3)))
        pts.append((x, y, rad * 1.5))
        o = hull_object(f"pebble_{k}", pts, used.index(pi), mats, coll)
        chamfer(o, 0.2)
        boolean(o, prism, "INTERSECT")
        for f in o.data.polygons:
            f.material_index = used.index(pi)
        rocks.append(o)
    bpy.data.objects.remove(prism, do_unlink=True)
    rocks.append(belly_object(outline, label, pal, used, mats, coll))
    # one mesh
    bm = bmesh.new()
    for o in rocks:
        b1 = bmesh.new()
        b1.from_mesh(o.data)
        bmesh.ops.remove_doubles(b1, verts=b1.verts[:], dist=1e-5)
        bmesh.ops.dissolve_degenerate(b1, dist=1e-5, edges=b1.edges[:])
        bmesh.ops.recalc_face_normals(b1, faces=b1.faces[:])
        nm = sum(1 for e in b1.edges if not e.is_manifold)
        print(f"B: {o.name} faces {len(b1.faces)} non-manifold edges {nm}")
        b1.to_mesh(o.data)
        b1.free()
        bm.from_mesh(o.data)
    for o in rocks:
        bpy.data.objects.remove(o, do_unlink=True)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    for poly in me.polygons:
        poly.use_smooth = False
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    return obj, mats, info, label, parts


# --- copied helpers (assembly-newsh4-124.py; candidates for common.py) -----------------------------

def whole_shell(obj, coll, voxel=0.016, faces=2400, smooth=4):
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    coll.objects.link(shell)
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    apply_mods(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    seen, islands = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append(x)
            stack.extend(e.other_vert(x) for e in x.link_edges)
        islands.append(isl)

    def volume(isl):
        ids = {v.index for v in isl}
        fs = {f for v in isl for f in v.link_faces}
        vol = 0.0
        for f in fs:
            if f.verts[0].index not in ids:
                continue
            p0 = f.verts[0].co
            for k in range(1, len(f.verts) - 1):
                vol += p0.dot(f.verts[k].co.cross(f.verts[k + 1].co)) / 6.0
        return vol
    drop = set()
    for isl in islands:
        if len(isl) < 12 or volume(isl) < 1e-4:
            drop.update(v.index for v in isl)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index in drop], context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    print(f"shell before decimate: {n} faces")
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    apply_mods(shell)
    return shell


def split_open(obj, layout, coll, suffix):
    """split_assembly without capping the cuts (for the outline shells: no seams outlined)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


def bake_piece(obj, out_dir, size=512, samples=48):
    """AO/edge colour multiplier + roughness/metallic bake into the piece's own palette material copies
    (assembly-newsh4-124.py bake_piece, trimmed). No concept projection."""
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    used = sorted({p.material_index for p in me.polygons})
    for k in used:
        mt = me.materials[k]
        c = mt.copy()
        c.name = f"{mt.name}-{obj.name}"
        me.materials[k] = c
    mats = [me.materials[k] for k in used]
    col_img = bpy.data.images.new(f"{obj.name}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{obj.name}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    saved = {}
    for mt in mats:
        out = next(n for n in mt.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[mt.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(mt, mode):
        nt = mt.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, bb=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, bb)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 16
        ao_s.inputs["Distance"].default_value = 0.05
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 16
        ao_l.inputs["Distance"].default_value = 0.3
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.6, math_("MULTIPLY", ao_l.outputs["AO"], 0.4)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.42, math_("MULTIPLY", occl, 0.66)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            nt.links.new(v, em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.15),
                                          math_("MULTIPLY", edge, 0.12)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {mt.name: bake_shader(mt, mode) for mt in mats}
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
        for mt in mats:
            nt = mt.node_tree
            for n in tmps[mt.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[mt.name] is not None:
                nt.links.new(saved[mt.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    for mt in mats:
        nt = mt.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


# --- review renders --------------------------------------------------------------------------------

def set_engine(name):
    scene = bpy.context.scene
    try:
        scene.render.engine = name
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if name in e)


def setup_workbench(flat):
    scene = bpy.context.scene
    set_engine("BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT" if flat else "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = not flat
    sh.show_object_outline = not flat
    sh.show_shadows = False
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def setup_game():
    scene = bpy.context.scene
    set_engine("BLENDER_EEVEE")
    world = scene.world or bpy.data.worlds.new("game")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.45, 0.55, 1.0)
    bg.inputs[1].default_value = 1.0
    sd = bpy.data.lights.new("game_sun", "SUN")
    sd.energy = 3.0
    sun = bpy.data.objects.new("game_sun", sd)
    bpy.context.scene.collection.objects.link(sun)
    d = Vector((-6, -8.4, 20)).normalized()
    sun.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    return sun


def camera(location, look_at, ortho=None, fov=None, top=False):
    data = bpy.data.cameras.new("cam")
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    elif fov:
        data.sensor_fit = "VERTICAL"
        data.angle_y = math.radians(fov)
    cam = bpy.data.objects.new("cam", data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (0, 0, 0) if top else (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    return cam


def render(cam, path, rx, ry):
    scene = bpy.context.scene
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    data = cam.data
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(data)


def render_views(objs, hide, out, k=8, panel=520):
    out.mkdir(parents=True, exist_ok=True)
    for o in hide:
        o.hide_render = True
    for o in objs:  # Workbench shows diffuse_color
        for mt in o.data.materials:
            bsdf = next((n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            base = bsdf.inputs["Base Color"]
            col = base.links[0].from_node.inputs[7].default_value if base.is_linked else base.default_value
            mt.diffuse_color = tuple(col)
    ext = max(W, H) * PX
    setup_workbench(True)
    render(camera((0, 0, 20), (0, 0, 0), ortho=H * PX, top=True), out / "top_flat.png", W * k, H * k)
    setup_workbench(False)
    render(camera((0, 0, 20), (0, 0, 0), ortho=H * PX, top=True), out / "top.png", W * k, H * k)
    span = ext * 1.3
    zc = 0.08  # the belly hangs below z 0
    render(camera((-30, 0, zc), (0, 0, zc), ortho=span), out / "left.png", 2 * panel, panel)
    render(camera((0, 30, zc), (0, 0, zc), ortho=span), out / "front.png", 2 * panel, panel)
    render(camera((0, -30, zc), (0, 0, zc), ortho=span), out / "rear.png", 2 * panel, panel)
    render(camera((0, 0, -20), (0, 0, 0), ortho=ext * 1.15), out / "under.png", panel, panel)
    d = ext * 1.45 + 1.5
    setup_workbench(False)
    sun = setup_game()
    render(camera((-d * 0.6, d * 0.55, d * 0.75), (0, 0, 0.2), fov=35), out / "q34_fl.png", panel, panel)
    render(camera((d * 0.6, -d * 0.55, d * 0.75), (0, 0, 0.2), fov=35), out / "q34_rr.png", panel, panel)
    render(camera((d * 0.25, d * 0.15, d * 1.05), (0, 0, 0.1), fov=35), out / "high.png", panel, panel)
    tilt = math.radians(32)
    render(camera((0, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0), fov=35), out / "game.png", panel, panel)
    # the same tilt at the game's own size (48 px wide object -> ~64 px tall panel), then scaled
    render(camera((0, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0), fov=35), out / "game_small.png", 96, 96)
    render(camera((0, 0, 20), (0, 0, 0), ortho=H * PX, top=True), out / "top_game.png", W * k, H * k)
    bpy.data.objects.remove(sun, do_unlink=True)
    # top mask: pure silhouette
    setup_workbench(True)
    saved = [tuple(mt.diffuse_color) for o in objs for mt in o.data.materials]
    for o in objs:
        for mt in o.data.materials:
            mt.diffuse_color = (1, 1, 1, 1)
    render(camera((0, 0, 20), (0, 0, 0), ortho=H * PX, top=True), out / "top_mask.png", W * k, H * k)
    i = 0
    for o in objs:
        for mt in o.data.materials:
            mt.diffuse_color = saved[i]
            i += 1
    for o in hide:
        o.hide_render = False


# --- main ------------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    idx, colors, m = sprite_data()
    obj, mats, info, label, parts = build(coll, idx, colors, m)
    shell = whole_shell(obj, coll)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in common.load_sprite(ROOT, "newshd-39")["assemblyLayout"]
              if e["model"] in PIECES]
    shells = split_open(shell, layout, coll, "_outline")
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    for sh in shells.values():
        sh["tyrian_outline"] = True
        sh.data.materials.append(outline_mat)
        sh.data.shade_smooth()
    bpy.data.objects.remove(shell, do_unlink=True)
    pieces = common.split_assembly(obj, layout)
    obj.hide_render = True
    tri = 0
    for p in pieces.values():
        p.data.calc_loop_triangles()
        tri += len(p.data.loop_triangles)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        scene = bpy.context.scene
        set_engine("CYCLES")
        scene.cycles.samples = 48
        scene.cycles.device = "CPU"
        tmp = tempfile.mkdtemp(prefix="nshd39_bake_")
        for sh in shells.values():
            sh.hide_render = True
        for name, cx, cy in layout:  # each piece baked with its neighbours in place round it
            pieces[name].location = (cx / 12, -cy / 12, 0)
        for name in PIECES:
            bake_piece(pieces[name], tmp)
        for p in pieces.values():
            p.location = (0, 0, 0)
        fmt = "WEBP"
    print(f"{NAME}: rock triangles {tri}, outline shell faces {sum(len(sh.data.polygons) for sh in shells.values())}")
    print("pal:", [(i["name"], i["pal"], i["blueprint_pal"]) for i in info])
    if "--render" in argv:
        for name, cx, cy in layout:
            pieces[name].location = (cx / 12, -cy / 12, 0)
        render_views(list(pieces.values()), [obj] + list(shells.values()), Path(argv[argv.index("--render") + 1]))
        for p in pieces.values():
            p.location = (0, 0, 0)
    if "--no-export" not in argv:
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"],
                                       image_format=fmt)
    if "--design-out" in argv:
        export = []
        for name, cx, cy in layout:
            for o in (pieces[name], shells[name]):
                o.location = (cx / 12, -cy / 12, 0)
                o["tyrian_piece"] = name
                export.append(o)
        common.export_glb(export, Path(argv[argv.index("--design-out") + 1]), image_format=fmt)


if __name__ == "__main__":
    main()
