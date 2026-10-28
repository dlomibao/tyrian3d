"""Rock shoulder (newsh3.shp frame 262): a 3D version of its sprite.

Seen in episode 4 (levels 2 and 29), beside the big rock arch. The upper-right end of a brown
rock: it fills the tile's lower left and breaks off along a ragged diagonal edge to the upper
right. The model is cut off square where it runs on past the tile's left and bottom edges and
is built from three surfaces the sprite's shading draws:

- the plain, flat at 3 px, filling the lower left (the sprite's even mid-brown),
- the ridge block standing about 2.5 px above it behind a steep face, the sprite's dark band
  from the left edge down to the streak, its drop fading out towards the bottom edge,
- on that block the pale crest, from the upper-left corner down to the middle, about 7 px high:
  a broad lit slope to the lower left and a shadowed fall to the upper right,
- a low rib, the fainter light streak continuing the crest down to the bottom edge,
- the dark rim along the diagonal outline as a bevel falling to about 0.8 px at the edge, and a
  fall towards the tile's right edge at the lower right,
- a small pit, the dark notch at the bottom-left corner.

The sprite's lighting is not paint: the game lights the model and draws its own outline, so the
facets don't take the sprite's per-pixel shades. Its dark rim and cliff band (the outline and the
shadowed faces, 16-19) take a dark brown, not near-black, and the rest is a softened tone map of the
sprite (the plain's browns, a lighter tan on the crest's lit rock), so the shapes above make the
light and dark. Matte rock: no metal, rough. One frame.

Run: blender --background --python assets/blender/enemies/newsh3-262.py [-- --preview out.png]
"""

import math
import random
import sys
from pathlib import Path

import bmesh
from mathutils import Vector, geometry

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common  # noqa: E402

NAME = "newsh3-262"

# Feature lines in sprite px (x = column, y = row, pixel centres at +0.5).
# The crest of the pale ridge (the sprite's 26-27 pixels), from the upper-left corner to the
# lower end of its 24s.
CREST = [(1.0, 2.8), (2.8, 4.6), (4.6, 6.2), (6.0, 8.2), (7.2, 10.2), (8.2, 12.6), (8.9, 15.0),
         (9.6, 17.0)]
# The fainter light streak continuing the ridge down to the bottom edge.
STREAK = [(9.6, 17.0), (11.5, 18.0), (13.4, 19.6), (14.5, 21.3), (15.4, 23.4), (16.3, 25.6),
          (17.0, 28.0)]
# The foot of the cliff: the sprite's dark band under the raised block (rows 14-21), the face
# between the high ridge block (upper right of it) and the plain (lower left of it).
CLIFF = [(0.0, 15.0), (2.0, 15.3), (4.5, 16.1), (6.3, 17.0), (7.5, 18.0), (9.5, 19.0),
         (11.5, 20.2), (13.2, 21.8), (14.4, 23.6), (15.3, 25.8), (16.0, 28.0)]
CLIFF_DROP = [2.6, 2.6, 2.6, 2.5, 2.4, 2.0, 1.3, 0.8, 0.4, 0.15, 0.0]  # px, per CLIFF point
TROUGH = [(19.2, 16.8), (20.6, 20.0), (21.3, 23.0), (21.6, 25.5), (21.2, 28.0)]
NOTCH = (0.9, 25.4)
PINNED = {(6, 4), (8, 4), (8, 3)}  # outline corners (col, row) left unsmoothed

PLAIN = 3.0  # px, the lower-left plain
CREST_UP = 1.5  # px, the crest above the ridge block's top
CREST_HALF = 1.4  # px, half the width of the crest's flat top
EDGE_Z = 0.8  # px, the top at the free outline
EDGE_FALL = 2.2  # px, width of the falling face (the dark rim) along the outline
BOTTOM = 1.5  # px below z = 0 inside


def seg_dist(p, line):
    """(distance to polyline, fraction along it, signed side: + = right of travel in sprite px,
    index of the nearest segment, fraction along that segment)."""
    best = (1e9, 0.0, 0.0, 0, 0.0)
    total = sum((Vector(line[i + 1]) - Vector(line[i])).length for i in range(len(line) - 1))
    run = 0.0
    for i in range(len(line) - 1):
        a, b = Vector(line[i]), Vector(line[i + 1])
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
        q = a + ab * t
        d = (p - q).length
        if d < best[0]:
            side = ab.x * (p.y - a.y) - ab.y * (p.x - a.x)
            best = (d, (run + ab.length * t) / total, side, i, t)
        run += ab.length
    return best


def cos_bump(t):
    return math.cos(min(1.0, t) * math.pi / 2) if t < 1.0 else 0.0


def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def height(p):
    """The top's height in px at sprite point p, before the fall to the free outline.

    Three surfaces: the plain at PLAIN px (lower left), the ridge block standing CLIFF_DROP above
    it behind a steep face along CLIFF (the sprite's dark band), and the pale crest along CREST on
    that block, with a broad lit slope to the lower left and a shadowed fall to the upper right."""
    z = PLAIN
    # The ridge block: everything on the upper-right side of the cliff line, lifted by the
    # cliff's drop there; the face is about 1.6 px wide, as wide as the dark band.
    d, _, side, i, t = seg_dist(p, CLIFF)
    drop = CLIFF_DROP[i] + (CLIFF_DROP[i + 1] - CLIFF_DROP[i]) * t
    s = d if side < 0 else -d  # + = upper-right side (the block)
    z += drop * smooth(-0.5, 1.2, s)
    # The crest: 1.6 px above the block at its upper end, 1.0 px at its lower end. Lit side (lower
    # left) a broad, even slope; shadow side (upper right) a narrow round top, then a falling face.
    d, t, side, _, _ = seg_dist(p, CREST)
    # A rounded, flat-topped band about CREST_HALF * 2 px wide (the sprite's evenly lit pale
    # band), not a spine; the shadow side then levels off onto the block (the mid-brown flank).
    # It narrows and settles towards its lower end, where the sprite's pale band thins to 24s.
    up = CREST_UP - 0.8 * smooth(0.5, 1.0, t)
    half = CREST_HALF * (1.0 - 0.35 * smooth(0.5, 1.0, t))
    if side < 0:  # upper right: a short rounded shoulder, then level
        z += up * (1.0 - smooth(half, half + 1.6, d))
    else:  # lower left: the broad lit slope, shorter where the crest nears the cliff
        z += up * (1.0 - smooth(half, half + 3.6 - 1.4 * t, d))
    # The light streak continuing the ridge down to the bottom edge: a low rounded rib.
    d, t, _, _, _ = seg_dist(p, STREAK)
    z += (0.6 - 0.2 * t) * cos_bump(d / 1.8)
    # The dark lower right: the surface falls away towards the tile's right edge (a face turned
    # from the light, continuing the diagonal edge's fall), past the trough line.
    # Only a slight dip: the corner stays on the plain's level, its dark shades are colour.
    f = min(1.0, max(0.0, (p.x - 18.5) / 4.0)) * min(1.0, max(0.0, (p.y - 16.0) / 3.0))
    z -= 0.3 * math.sin(f * math.pi / 2)
    # The notch at the bottom-left corner.
    d = (p - Vector(NOTCH)).length
    z = min(z, 2.0 + 0.9 * d)
    return max(z, 1.2)


def _offset(line, off):
    """Points along `line` shifted `off` px to its left (upper side for a line running right)."""
    out = []
    for i in range(len(line) - 1):
        a, b = Vector(line[i]), Vector(line[i + 1])
        nrm = Vector((b.y - a.y, -(b.x - a.x))).normalized()
        out.append(a + nrm * off)
        out.append((a + b) / 2 + nrm * off)
    out.append(Vector(line[-1]) + nrm * off)
    return out


def build_rock(bm, pixels, slot_of, spacing=2.0, seed=262, paint=None):
    h, w = len(pixels), len(pixels[0])
    rng = random.Random(seed)
    keep = lambda v: v >= 0  # noqa: E731
    loop = lib.trace_mask(pixels, keep)
    on_border = [c in (0, w) or r in (0, h) for c, r in loop]
    pts = [Vector((float(c), float(r))) for c, r in loop]
    keep_i = []
    n = len(pts)
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        if abs((b - a).cross(c - b)) > 1e-6 or on_border[i]:
            keep_i.append(i)
    pts = [pts[i] for i in keep_i]
    border = [on_border[i] for i in keep_i]
    # The notch under the lone rim pixel at (8, 3): keep its floor corners where they are, so the
    # smoothed outline doesn't fill the two empty pixels beside it.
    pinned = [border[k] or tuple(loop[i]) in PINNED for k, i in enumerate(keep_i)]
    for _ in range(3):
        n = len(pts)
        pts = [p if pinned[i] else (pts[i - 1] + 2 * p + pts[(i + 1) % n]) / 4 for i, p in enumerate(pts)]
    n = len(pts)
    free = [(pts[i], pts[(i + 1) % n]) for i in range(n) if not (border[i] and border[(i + 1) % n])]

    def dist_segs(p, segs):
        best = 1e9
        for a, b in segs:
            ab = b - a
            t = max(0.0, min(1.0, (p - a).dot(ab) / (ab.length_squared or 1.0)))
            best = min(best, (a + ab * t - p).length)
        return best

    ring = [(pts[i], pts[(i + 1) % n]) for i in range(n)]

    def inside_poly(p):
        hit = False
        for a, b in ring:
            if (a.y > p.y) != (b.y > p.y):
                x = a.x + (p.y - a.y) * (b.x - a.x) / (b.y - a.y)
                if x > p.x:
                    hit = not hit
        return hit

    coords = [Vector(p) for p in pts]
    feature = []  # points that carry the forms: crest, groove floor, the falling face's top
    crest_rows = [(_offset(CREST, o), 1.2) for o in (CREST_HALF, -CREST_HALF, CREST_HALF + 1.6,
                                                      -(CREST_HALF + 2.0))]
    for line, step in [(CREST, 1.2), (STREAK, 1.4), (TROUGH, 1.6)] + crest_rows + [
                       (_offset(CLIFF, 1.2), 1.2), (_offset(CLIFF, 0.35), 1.2),
                       (_offset(CLIFF, -0.5), 1.2)]:
        for i in range(len(line) - 1):
            a, b = Vector(line[i]), Vector(line[i + 1])
            k = max(1, round((b - a).length / step))
            for j in range(k + (1 if i == len(line) - 2 else 0)):
                feature.append(a.lerp(b, j / k))
    feature.append(Vector(NOTCH))
    # The falling face: a row of points halfway down it and one along its top, EDGE_FALL in
    # from the free outline, so it is made of even facets instead of slivers.
    for off in (EDGE_FALL, EDGE_FALL * 0.45):
        for a, b in free:
            k = max(1, round((b - a).length / 1.5))
            for j in range(k):
                q = a.lerp(b, j / k)
                nrm = Vector((-(b - a).y, (b - a).x)).normalized()
                for s in (1, -1):
                    c = q + nrm * s * off
                    if inside_poly(c) and abs(dist_segs(c, free) - off) < 0.3:
                        feature.append(c)
    kept_feat = []
    for p in feature:
        if inside_poly(p) and dist_segs(p, ring) > 0.6 and all((p - q).length > 0.8 for q in kept_feat):
            kept_feat.append(p)
    coords += kept_feat
    gy = spacing / 2
    while gy < h:
        gx = spacing / 2 + (spacing / 2 if int(gy / spacing) % 2 else 0)
        while gx < w:
            p = Vector((gx + rng.uniform(-0.2, 0.2) * spacing, gy + rng.uniform(-0.2, 0.2) * spacing))
            if (inside_poly(p) and dist_segs(p, ring) > spacing * 0.45
                    and all((p - q).length > spacing * 0.55 for q in kept_feat)):
                coords.append(p)
            gx += spacing
        gy += spacing * 0.87
    n_feat_end = n + len(kept_feat)
    vco, _, faces, orig, _, _ = geometry.delaunay_2d_cdt(coords, [], [list(range(n))], 3, 1e-5, True)
    out_of = {}
    for o, ins in enumerate(orig):
        for i in ins:
            out_of[i] = o
    rough = {}
    for o, ins in enumerate(orig):
        if ins and all(i >= n_feat_end for i in ins):
            rough[o] = rng.uniform(-0.02, 0.02)  # rock texture on the plain's grid points only

    tops, bots = [], []
    for o, p in enumerate(vco):
        p = Vector(p)
        d = dist_segs(p, free)
        k = math.sin(min(1.0, d / EDGE_FALL) * math.pi / 2)
        zt = EDGE_Z + (height(p) + rough.get(o, 0.0) * k - EDGE_Z) * k
        kb = math.sin(min(1.0, d / 4.0) * math.pi / 2)
        zb = -(0.2 + (BOTTOM - 0.2) * kb)
        x, y = (p.x - w / 2) / 12, (h / 2 - p.y) / 12
        tops.append(bm.verts.new((x, y, zt / 12)))
        bots.append(bm.verts.new((x, y, zb / 12)))
    made, top_faces = [], []
    for f in faces:
        ft = bm.faces.new([tops[i] for i in f])
        fb = bm.faces.new([bots[i] for i in reversed(f)])
        fb.material_index = 0
        top_faces.append(ft)
        made += [ft, fb]
    for i in range(n):
        a, b = out_of[i], out_of[(i + 1) % n]
        if a == b:
            continue
        f = bm.faces.new((tops[b], tops[a], bots[a], bots[b]))
        f.material_index = 0
        made.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=made)
    lib.paint_faces(bm, top_faces, paint or pixels, slot_of, under_slot=0, min_nz=-0.2, reach=0.5)
    return made


# The rock's colour by sprite shade, before softening: the sprite's near-black outline ring and
# shadow (16-18) become a dark brown (the game shades and outlines the rim's falling face and the
# cliff), the plain's lit browns step down one shade (the light brightens them again) and the lit
# crest keeps a tan one or two steps down from its glare.
TONE = {16: 19, 17: 20, 18: 20, 19: 20, 20: 20, 21: 21, 22: 21, 23: 22, 24: 23, 25: 24, 26: 25,
        27: 25}


def paint_map(pixels):
    """The sprite's pixels through TONE, softened with their four neighbours (the pixel itself
    weighted 4): even areas of rock colour instead of a per-pixel patchwork of its shading."""
    h, w = len(pixels), len(pixels[0])
    out = []
    for r in range(h):
        row = []
        for c in range(w):
            if pixels[r][c] < 0:
                row.append(-1)
                continue
            tot, wt = 4 * TONE.get(pixels[r][c], 21), 4
            for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if 0 <= rr < h and 0 <= cc < w and pixels[rr][cc] >= 0:
                    tot, wt = tot + TONE.get(pixels[rr][cc], 21), wt + 1
            row.append(int(math.floor(tot / wt + 0.5)))
        out.append(row)
    return out


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    # One material per rock shade: 21 the mid-brown (also the underside and the cut-off sides),
    # 19-20 the darker brown of the rim and cliff, 22 the plain's lighter brown, 23-25 the tan of
    # the crest's lit rock.
    shades = [21, 19, 20, 22, 23, 24, 25]
    mats = [pal(i, metallic=0.0, roughness=0.9) for i in shades]
    pixels = sprite["frames"][0]["pixels"]

    def slot(v):
        if v < 0:
            return None
        return shades.index(v) if v in shades else 0

    bm = bmesh.new()
    build_rock(bm, pixels, slot, paint=paint_map(pixels))
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]

if __name__ == "__main__":
    lib.run(NAME, build, __file__)
