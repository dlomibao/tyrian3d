"""BRAINIAC's brain boss : one 96 x 84 px brain made of ten 2x2 pieces in three
assemblies (assembly-newsh5-198: newsh5-196/198/200, the upper rows; assembly-newsh5-233:
newsh5-233/235/237/239, the middle rows; assembly-newsh5-272: newsh5-272/274/276, the lower rows),
plus newsh5-95, the green energy arrow that shares lib_b029.

What it is (sprite read as a whole, BRAINIAC 4.15, every piece on link 254, same link rigid): a giant
brain seen from above. Two hemispheres split by the black longitudinal fissure down the middle, packed
with pink folds (gyri) between dark grooves; the south end darkens and curls under (where the fissure
forks round the brainstem). Below it hang two glossy blue eye lobes, a short brainstem under them and
dark red nerve tendrils: on each side an outer strut and a straight strand from the brain's underside
and a strand from the eye's side, merging into a loop that swings in to the stem's two forked roots.

Build (organic, faired, no pixel steps):
- the brain is one closed solid: a lattice (LAT px) over the brain's inner mask (sprite_mask's inner:
  the ink ring is the game's outline), each node's height from the distance d to the outline. The
  outline band is an elliptic quarter (vertical tangent at the outline, so the side is a bulging round
  wall, not a cliff): nodes in the band slide out towards the outline as they rise (s = D(1 - cos),
  z = He sin). A dome rises over it (Hu), the hemispheres round down into the fissure (a deep cleft;
  a shallower one along the fork round the stem), and the south end sinks. The gyri are displaced along
  the surface normal from the sprite's own fold shading (a fine minus a broad blur of its brightness),
  so they follow the sprite's folds, also down the sides. Flat closed underside.
- eyes: glossy ellipsoids fitted to each eye's pixels; brainstem and tendrils: round swept tubes along
  the sprite's own strands, mirror symmetric about x = 48.5 px.
- colour: palette materials only. Flesh tones from the sprite's broad brightness pulled towards its
  median (68) plus a step for crests (+) and grooves (-); the fissure floor black (1). Eyes 52, tendrils
  and stem 66/67. Matte-moist flesh (metallic 0, roughness 0.55), glossy eyes (0.22).
- the whole brain is cut into the ten pieces (common.split_assembly); its outline shell is made once
  from the sealed whole (islands="outer", D189) and cut open per piece so no ink crosses a seam. Every
  piece carries one `tyrian_anchor` (D181) so the tall dome's pieces meet on screen.

Shared builder (used only by assembly-newsh5-233/198/272.py and newsh5-95.py): `build_models()` builds
the whole brain and the arrow; `export(names)` writes each named model to public/models/enemies/<name>.glb
and its src/render/spriteModels entry. Each wrapper script exports only its own models.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]  # the repo root, from this file's place
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "tools")]
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

PX = 1 / 12
W, H = 96, 84
AXIS = 48.5  # the lower parts' mirror axis (edge coordinates, px)
TAG = "ns5brainA"

# (piece, grid column of its left edge, grid row of its top edge) in the 96 x 84 brain grid
LAY = [("newsh5-196", 12, 0), ("newsh5-198", 36, 0), ("newsh5-200", 60, 0),
       ("newsh5-233", 0, 28), ("newsh5-235", 24, 28), ("newsh5-237", 48, 28), ("newsh5-239", 72, 28),
       ("newsh5-272", 12, 56), ("newsh5-274", 36, 56), ("newsh5-276", 60, 56)]
ASSEMBLY = {"newsh5-196": "assembly-newsh5-198", "newsh5-198": "assembly-newsh5-198", "newsh5-200": "assembly-newsh5-198",
            "newsh5-233": "assembly-newsh5-233", "newsh5-235": "assembly-newsh5-233", "newsh5-237": "assembly-newsh5-233",
            "newsh5-239": "assembly-newsh5-233",
            "newsh5-272": "assembly-newsh5-272", "newsh5-274": "assembly-newsh5-272", "newsh5-276": "assembly-newsh5-272"}

# --- brain shape (px) ---
LAT = 0.75        # lattice step
D_EDGE = 8.0      # width of the outline's rounded band
HE = 8.5          # height the band rises to
HU = 13.5         # the dome over it (crown = HE + HU at the hemispheres' middles)
D_DOME = 21.0     # distance from the outline over which the dome rises
SOFT = 0.3        # soft-min radius of the outline distance (rounds the pixel steps)
OFFSET = 0.5      # the outline sits this far from the outside pixels' centres
SOUTH = 0.34      # how far the south end sinks (share of the height), rows 42-66
NORTH = 0.08      # and the north end, rows 18-3
RELIEF = 3.2      # gyri: most a fold stands out of (or a groove sinks into) the surface
SIDE_FREQ = 0.2   # the sides' gyri: noise frequency per px (sulci on its zero lines, ~4 px apart)
BAND_RELIEF = 0.55  # share of the relief on the outline band's steep side
FOLD_K = 1.4     # px of relief per palette step of fold shading
FINE, BROAD = 1.0, 2.9   # blur radii (px) of the fold shading
# the fissure: polylines (edge coordinates) and how deep each cuts (share of the height) and its width
FISSURES = [
    (0.6, 4.2, [(48.6, 4.0), (48.6, 8.0), (49.4, 13.0), (49.4, 21.0), (50.0, 24.0), (49.6, 28.0), (49.0, 32.0),
                 (48.6, 35.0), (47.8, 38.0), (47.0, 41.0), (46.4, 44.0), (46.2, 48.0), (46.2, 54.0), (46.4, 58.0),
                 (46.0, 61.0), (45.2, 64.0)]),
    (0.4, 3.6, [(47.0, 44.5), (49.5, 46.5), (51.2, 49.0), (51.0, 53.0), (50.3, 56.0), (50.8, 59.0), (51.6, 61.0),
                 (52.4, 64.0)]),
]
FLOOR_W = 0.6     # px either side of a fissure line painted black (the main one only)

# --- colours (palette indices) ---
MEDIAN = 68       # the sprite's flesh median
TONE_KEEP = 0.6   # share of the sprite's broad brightness the flesh keeps
TONE_RELIEF = 3.2  # palette steps from a groove's bottom to a fold's crest, either way
EYE, TUBE, STEM = 52, 67, 66


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def P(c, r, z=0.0):
    """Edge coordinates (column, row, height px) to Blender."""
    return Vector(((c - W / 2) * PX, (H / 2 - r) * PX, z * PX))


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def mat(sprite, idx, tag, metallic=0.0, roughness=0.55, glow=0.0, frames=None, spec=None):
    m = common.palette_material(sprite, idx, tag, metallic=metallic, roughness=roughness,
                                emission_strength=glow, frames=frames)
    if spec is not None:
        bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
        for key in ("Specular IOR Level", "Specular"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = spec
                break
    return m


# --- the sprite --------------------------------------------------------------------------------------

def brain_grid():
    G = np.full((H, W), -1, dtype=int)
    colors = {}
    for name, c0, r0 in LAY:
        d = common.load_sprite(WT, name)
        colors.update(d["colors"])
        a = np.array(d["frames"][0]["pixels"], dtype=int)
        sub = G[r0:r0 + 28, c0:c0 + 24]
        sub[a >= 0] = a[a >= 0]
    return G, colors


def components(mask):
    """Label 4-connected components; returns the largest as a bool array."""
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=int)
    best, best_n, k = None, 0, 0
    for r in range(h):
        for c in range(w):
            if mask[r, c] and not lab[r, c]:
                k += 1
                stack, n = [(r, c)], 0
                lab[r, c] = k
                while stack:
                    y, x = stack.pop()
                    n += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                            lab[yy, xx] = k
                            stack.append((yy, xx))
                if n > best_n:
                    best, best_n = k, n
    return lab == best


def blur_field(values, inside, pts, sigma):
    """Gaussian blur of per-pixel `values` over the `inside` pixels, sampled at points (row, col) px."""
    iy, ix = np.nonzero(inside)
    v = values[iy, ix].astype(float)
    cy, cx = iy + 0.5, ix + 0.5
    out = np.empty(len(pts))
    for s0 in range(0, len(pts), 1500):
        p = pts[s0:s0 + 1500]
        d2 = (p[:, 0:1] - cy[None, :]) ** 2 + (p[:, 1:2] - cx[None, :]) ** 2
        w = np.exp(-0.5 * d2 / sigma ** 2)
        out[s0:s0 + 1500] = (w * v[None, :]).sum(1) / np.maximum(w.sum(1), 1e-9)
    return out


class Outline:
    """Soft distance (px) from points to the outline of a pixel mask: soft-min of the distances to the
    outside pixels' centres next to it, less OFFSET."""

    def __init__(self, mask):
        h, w = mask.shape
        pad = np.zeros((h + 2, w + 2), dtype=bool)
        pad[1:-1, 1:-1] = mask
        near = np.zeros_like(pad)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                near |= np.roll(np.roll(pad, dy, 0), dx, 1)
        oy, ox = np.nonzero(near & ~pad)
        self.oy, self.ox = oy - 1 + 0.5, ox - 1 + 0.5  # outside pixel centres (row, col)

    def __call__(self, pts):
        out = np.empty(len(pts))
        for s0 in range(0, len(pts), 1500):
            p = pts[s0:s0 + 1500]
            do = np.sqrt((p[:, 0:1] - self.oy[None, :]) ** 2 + (p[:, 1:2] - self.ox[None, :]) ** 2)
            dmin = do.min(1)
            out[s0:s0 + 1500] = dmin - SOFT * np.log(np.exp(-(do - dmin[:, None]) / SOFT).sum(1)) - OFFSET
        return out


def seg_dist(pts, line):
    """Distance (px) from points (row, col) to a polyline of (col, row)."""
    best = np.full(len(pts), 1e9)
    for (c0, r0), (c1, r1) in zip(line, line[1:]):
        ax, ay, bx, by = c0, r0, c1, r1
        vx, vy = bx - ax, by - ay
        t = np.clip(((pts[:, 1] - ax) * vx + (pts[:, 0] - ay) * vy) / (vx * vx + vy * vy), 0, 1)
        dx, dy = pts[:, 1] - (ax + t * vx), pts[:, 0] - (ay + t * vy)
        best = np.minimum(best, np.hypot(dx, dy))
    return best


# --- the brain mass ----------------------------------------------------------------------------------

def brain_mass(G, colors, inner):
    rr, cc = np.mgrid[0:H, 0:W]
    eyes_box = (rr >= 65) & (cc >= 39) & (cc <= 57)
    mass = components(inner & (rr <= 67) & ~eyes_box)
    lvl = np.where(G >= 64, G - 64, 0).astype(float)
    lvl = np.minimum(lvl, 13)  # the near-white spots are sheen, not taller folds

    outline = Outline(mass)
    # lattice nodes (row, col) over the mass's bounding box
    ys, xs = np.nonzero(mass)
    r0, r1, c0, c1 = ys.min() - 1, ys.max() + 2, xs.min() - 1, xs.max() + 2
    ni, nj = int((r1 - r0) / LAT) + 1, int((c1 - c0) / LAT) + 1
    nodes = np.array([(r0 + i * LAT, c0 + j * LAT) for i in range(ni) for j in range(nj)])
    d = outline(nodes)
    e = 0.2
    gr = (outline(nodes + [e, 0]) - outline(nodes - [e, 0])) / (2 * e)
    gc = (outline(nodes + [0, e]) - outline(nodes - [0, e])) / (2 * e)
    gn = np.maximum(np.hypot(gr, gc), 1e-6)
    gr, gc = gr / gn, gc / gn
    pr_i = np.clip(np.floor(nodes[:, 0]).astype(int), 0, H - 1)
    pc_i = np.clip(np.floor(nodes[:, 1]).astype(int), 0, W - 1)
    near_mass = np.zeros_like(mass)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            near_mass |= np.roll(np.roll(mass, dy, 0), dx, 1)
    inside = ((d > 0.02) & near_mass[pr_i, pc_i] & mass[np.clip(np.round(nodes[:, 0] - 0.5).astype(int), 0, H - 1),
                                                         np.clip(np.round(nodes[:, 1] - 0.5).astype(int), 0, W - 1)]).reshape(ni, nj)

    # quads with all four corners inside; fix pinched corners by adding the missing quad
    def quads_of(ins):
        q = ins[:-1, :-1] & ins[1:, :-1] & ins[:-1, 1:] & ins[1:, 1:]
        return q
    for _ in range(6):
        q = quads_of(inside)
        # a node shared by exactly two diagonal quads pinches the surface: include a third
        pinch = False
        qp = np.zeros((ni + 1, nj + 1), dtype=bool)
        qp[1:-1, 1:-1] = q
        for i in range(1, ni - 1):
            for j in range(1, nj - 1):
                a, b, c, dd = qp[i, j], qp[i, j + 1], qp[i + 1, j], qp[i + 1, j + 1]  # quads around node (i, j)
                if (a and dd and not b and not c) or (b and c and not a and not dd):
                    # add every node of the quad up-right of the node
                    inside[i - 1, j] = inside[i - 1, j + 1] = inside[i, j] = inside[i, j + 1] = True
                    pinch = True
        if not pinch:
            break
    q = quads_of(inside)
    used = np.zeros((ni, nj), dtype=bool)
    used[:-1, :-1] |= q
    used[1:, :-1] |= q
    used[:-1, 1:] |= q
    used[1:, 1:] |= q
    # boundary nodes: used nodes with a missing quad around them
    qp = np.zeros((ni + 1, nj + 1), dtype=bool)
    qp[1:-1, 1:-1] = q
    full = qp[:-1, :-1] & qp[:-1, 1:] & qp[1:, :-1] & qp[1:, 1:]
    bnd = used & ~full

    D = d.reshape(ni, nj)
    GR, GC = gr.reshape(ni, nj), gc.reshape(ni, nj)
    NR, NC = nodes[:, 0].reshape(ni, nj), nodes[:, 1].reshape(ni, nj)
    # positions: boundary nodes onto the outline; band nodes slide out as they rise
    pr, pc = NR.copy(), NC.copy()
    dd = np.maximum(D, 0.0)
    th = np.clip(dd / D_EDGE, 0, 1) * (math.pi / 2)
    s = np.where(dd < D_EDGE, D_EDGE * (1 - np.cos(th)), dd)
    shift = np.where(bnd, D, dd - s)
    pr -= shift * GR
    pc -= shift * GC
    E = np.where(bnd, 0.0, np.sin(th))
    Gd = 1 - (1 - np.clip(dd / D_DOME, 0, 1)) ** 2
    pts = np.stack([NR.ravel(), NC.ravel()], 1)
    Ff = np.ones(len(pts))
    floor = np.zeros(len(pts), dtype=bool)
    for k, (depth, width, line) in enumerate(FISSURES):
        df = seg_dist(pts, line)
        Ff *= 1 - depth * (1 - np.sin(np.clip(df / width, 0, 1) * math.pi / 2))
        if k == 0:
            floor |= df < FLOOR_W
    Ff = Ff.reshape(ni, nj)
    S = 1 - SOUTH * smoothstep(42, 66, NR) - NORTH * smoothstep(18, 3, NR)
    Z = (HE * E + HU * Gd * np.where(bnd, 0, 1)) * Ff * S
    Z = np.where(bnd, 0.0, Z)

    # fold shading (relief) and broad tone at the nodes (original lattice positions)
    fine = blur_field(lvl, mass, pts, FINE)
    broad = blur_field(lvl, mass, pts, BROAD)
    rel_top = RELIEF * np.tanh(FOLD_K * (fine - broad) / RELIEF)
    rel_top = rel_top.reshape(ni, nj)
    wband = 1 - smoothstep(0.45 * D_EDGE, 1.15 * D_EDGE, D)
    rel = rel_top * (1 - wband)
    keep = smoothstep(0.3, 2.0, D) * np.where(bnd, 0, 1)
    # mesh
    bm = bmesh.new()
    vid = {}
    for i in range(ni):
        for j in range(nj):
            if used[i, j]:
                vid[i, j] = bm.verts.new(P(pc[i, j], pr[i, j], Z[i, j]))
    faces = []
    for i in range(ni - 1):
        for j in range(nj - 1):
            if q[i, j]:
                f = bm.faces.new((vid[i, j], vid[i + 1, j], vid[i + 1, j + 1], vid[i, j + 1]))
                faces.append((f, i, j))
    bm.normal_update()
    for f, _, _ in faces:
        if f.normal.z < 0:
            f.normal_flip()
    bm.normal_update()
    # gyri: displace along the smooth normal. Top: the sprite's own folds; the outline band (the sides):
    # meandering gyri with their sulci on a noise field's zero lines, as on a real brain's side
    from mathutils import noise
    relv = {}
    for (i, j), v in vid.items():
        if not keep[i, j]:
            relv[i, j] = 0.0
            continue
        q3 = Vector((pc[i, j], pr[i, j], Z[i, j] * 1.4)) * SIDE_FREQ
        nz = abs(noise.noise(q3))
        side = RELIEF * 0.85 * (min(nz / 0.42, 1.0) ** 0.55 * 1.6 - 1.0)
        r = (rel[i, j] + wband[i, j] * side) * keep[i, j]
        relv[i, j] = r
        v.co += v.normal * (r * PX)
    # underside: fill the boundary loop
    bedges = [e for e in bm.edges if len(e.link_faces) == 1]
    under = [g for g in bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=bedges)["geom"]
             if isinstance(g, bmesh.types.BMFace)]
    # tones per face: the sprite's broad brightness pulled to the median, plus the face's relief (crests
    # lighter, grooves darker); the fissure floor black
    cen = np.array([(r0 + (i + 0.5) * LAT, c0 + (j + 0.5) * LAT) for _, i, j in faces])
    fb = blur_field(lvl, mass, cen, BROAD)
    fr = np.array([(relv[i, j] + relv[i + 1, j] + relv[i, j + 1] + relv[i + 1, j + 1]) / 4 for _, i, j in faces])
    floor_f = seg_dist(cen, FISSURES[0][2]) < FLOOR_W
    base = np.maximum(fb, 3.0)  # the outline ring's dark is the game's outline, not the flesh
    tone = MEDIAN + np.round((base - (MEDIAN - 64)) * TONE_KEEP + np.clip(fr / RELIEF * TONE_RELIEF, -TONE_RELIEF, TONE_RELIEF))
    tone = np.clip(tone, 65, 75).astype(int)
    tone = np.where(floor_f, 1, tone)
    used_idx = sorted(set(tone.tolist()) | {MEDIAN - 1})
    sprite = {"name": "brain", "colors": colors}
    mats = [mat(sprite, i, TAG, metallic=0.0, roughness=0.9 if i == 1 else 0.5, spec=0.4) for i in used_idx]
    slot = {i: k for k, i in enumerate(used_idx)}
    for (f, _, _), t in zip(faces, tone):
        f.material_index = slot[int(t)]
        f.smooth = True
    for f in under:
        f.material_index = slot[MEDIAN - 1]
        f.smooth = False
    return bm, mats, slot


# --- eyes, stem, tendrils ----------------------------------------------------------------------------

def ellipsoid(bm, centre, radii, angle, mat_i, seg=24, rings=12, tilt=0.0):
    """Closed ellipsoid; `angle` turns it about Z, `tilt` leans its top towards -Y (south)."""
    rot = Matrix.Rotation(angle, 3, "Z") @ Matrix.Rotation(tilt, 3, "X")
    c = Vector(centre)
    rx, ry, rz = radii
    top = bm.verts.new(c + rot @ Vector((0, 0, rz)))
    bot = bm.verts.new(c + rot @ Vector((0, 0, -rz)))
    lat = []
    for i in range(1, rings):
        ph = math.pi * i / rings
        lat.append([bm.verts.new(c + rot @ Vector((rx * math.sin(ph) * math.cos(2 * math.pi * j / seg),
                                                   ry * math.sin(ph) * math.sin(2 * math.pi * j / seg),
                                                   rz * math.cos(ph)))) for j in range(seg)])
    out = []
    for j in range(seg):
        k = (j + 1) % seg
        out.append(bm.faces.new((top, lat[0][j], lat[0][k])))
        out.append(bm.faces.new((bot, lat[-1][k], lat[-1][j])))
        for a, b in zip(lat, lat[1:]):
            out.append(bm.faces.new((a[j], b[j], b[k], a[k])))
    for f in out:
        f.material_index = mat_i
        f.smooth = True
    return out


def catmull(pts, n):
    P_ = [np.array(p, dtype=float) for p in pts]
    ext = [P_[0] * 2 - P_[1]] + P_ + [P_[-1] * 2 - P_[-2]]
    segs = len(P_) - 1
    out = []
    for i in range(n):
        s = i / (n - 1) * segs
        k = min(int(s), segs - 1)
        t = s - k
        p0, p1, p2, p3 = ext[k], ext[k + 1], ext[k + 2], ext[k + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    return out


def tube(bm, pts, mat_i, n=None, sides=10, mirror=False):
    """A round tube along (col, row, z, half_width[, half_height]) points (px), closed with domed caps."""
    pts = [p if len(p) == 5 else (*p, p[3]) for p in pts]
    if mirror:
        pts = [(2 * AXIS - c, r, z, hw, hh) for c, r, z, hw, hh in pts]
    n = n or max(6, int(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])) / 0.9))
    cv = catmull(pts, n)
    up = Vector((0, 0, 1))
    rings = []
    for i, p in enumerate(cv):
        a, b = cv[max(i - 1, 0)], cv[min(i + 1, n - 1)]
        t = Vector((b[0] - a[0], -(b[1] - a[1]), (b[2] - a[2]))).normalized()
        side = t.cross(up)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        nrm = side.cross(t).normalized()
        c = P(p[0], p[1], p[2])
        rings.append([bm.verts.new(c + side * (p[3] * PX * math.cos(2 * math.pi * (k + 0.5) / sides))
                                   + nrm * (p[4] * PX * math.sin(2 * math.pi * (k + 0.5) / sides)))
                      for k in range(sides)])
    out = []
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            out.append(bm.faces.new((a[k], a[j], b[j], b[k])))
    # domed caps: a half ring and a tip a little beyond each end
    for ring, i0, i1 in ((rings[0], 0, 1), (rings[-1], n - 1, n - 2)):
        p, q_ = cv[i0], cv[i1]
        dirv = P(p[0], p[1], p[2]) - P(q_[0], q_[1], q_[2])
        dirv = dirv.normalized() if dirv.length > 0 else Vector((0, 0, 1))
        c = sum((v.co for v in ring), Vector()) / sides
        mid = [bm.verts.new(c + (v.co - c) * 0.7 + dirv * (min(p[3], p[4]) * 0.5 * PX)) for v in ring]
        tip = bm.verts.new(c + dirv * (min(p[3], p[4]) * 0.85 * PX))
        for k in range(sides):
            j = (k + 1) % sides
            out.append(bm.faces.new((ring[k], ring[j], mid[j], mid[k])))
            out.append(bm.faces.new((mid[k], mid[j], tip)))
    for f in out:
        f.material_index = mat_i
        f.smooth = True
    return out


# tendril paths (edge coordinates col, row; z px; half width px), the left side (mirrored for the right)
T_OUTER = [(26.2, 63.5, 4.2, 1.5), (25.4, 66.8, 3.0, 1.3), (25.5, 68.5, 2.3, 1.2), (25.3, 70.0, 1.9, 1.0),
           (26.0, 71.5, 1.7, 1.0), (27.0, 72.5, 1.6, 1.0), (28.0, 73.5, 1.55, 1.0), (29.1, 74.5, 1.55, 1.0),
           (31.0, 75.15, 1.6, 1.0), (33.6, 75.5, 1.7, 1.05), (35.4, 76.4, 1.7, 1.05), (36.6, 77.5, 1.6, 1.0),
           (37.6, 78.5, 1.55, 1.0), (38.6, 79.5, 1.5, 1.0), (39.8, 80.5, 1.45, 1.0), (42.3, 81.25, 1.4, 0.95),
           (44.4, 81.1, 1.5, 1.05), (45.7, 80.3, 1.7, 1.1), (46.8, 79.2, 2.0, 1.2)]
T_MID = [(32.5, 63.8, 4.0, 1.4), (32.5, 67.0, 2.8, 1.4), (32.5, 68.4, 2.3, 1.3), (32.5, 70.0, 2.0, 0.95),
         (32.5, 72.0, 1.9, 0.95), (33.0, 73.5, 1.8, 1.0), (33.1, 74.6, 1.75, 1.0), (33.9, 75.6, 1.7, 1.05)]
T_EYE = [(41.0, 69.6, 3.2, 1.1), (39.6, 71.0, 2.4, 1.0), (38.7, 72.4, 2.0, 0.95), (37.9, 73.6, 1.9, 0.95),
         (37.6, 74.7, 1.85, 0.95), (37.2, 75.8, 1.8, 1.0), (36.6, 76.9, 1.7, 1.0)]
# the brainstem under the eyes (centre on the axis), half width and half height px
STEM_PATH = [(AXIS, 69.0, 4.6, 4.0, 3.2), (AXIS, 72.0, 4.0, 4.4, 3.3), (AXIS, 74.5, 3.4, 4.3, 3.0),
             (AXIS, 76.3, 2.9, 3.6, 2.6), (AXIS, 77.6, 2.5, 2.4, 2.1), (AXIS, 78.6, 2.3, 2.0, 1.8)]
STEM_ROOT = [(47.9, 78.0, 2.3, 1.3), (47.0, 79.3, 2.0, 1.15), (45.6, 80.4, 1.7, 1.05), (44.2, 81.0, 1.5, 1.0),
             (43.2, 81.2, 1.4, 0.95)]


# each eye's span per row (edge coordinates: row centre, left, right) for the left eye; the right one is
# its mirror. The inner sides meet on the dark divider (column 48).
EYE_SPANS = [(64.05, 44.6, 46.0), (64.5, 43.0, 47.2), (65.5, 40.4, 48.5), (66.5, 40.6, 48.5), (67.5, 40.1, 48.5),
             (68.5, 40.0, 48.5), (69.5, 40.0, 48.5), (70.5, 39.6, 48.5), (71.5, 42.6, 48.5), (72.5, 44.0, 48.4),
             (73.15, 45.4, 47.6)]
EYE_Z = 4.6  # px: the eyes' half height (they stand about 9 px)


def eye(bm, mat_i, mirror):
    """A glossy eye lobe: an ellipsoid squashed row by row onto the sprite's span (round in section, the
    sprite's teardrop from above), leaning a little forward."""
    ys = [s_[0] for s_ in EYE_SPANS]
    y0, y1 = ys[0], ys[-1]
    yc, ry = (y0 + y1) / 2, (y1 - y0) / 2

    def span(y):
        y = min(max(y, y0), y1)
        for a, b in zip(EYE_SPANS, EYE_SPANS[1:]):
            if a[0] <= y <= b[0]:
                t = (y - a[0]) / (b[0] - a[0])
                t = t * t * (3 - 2 * t)
                return a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t
        return EYE_SPANS[-1][1:]
    seg, rings = 24, 14
    lat = []
    for i in range(rings + 1):
        ph = math.pi * i / rings
        y = yc - ry * math.cos(ph)
        l_, r_ = span(y)
        mid, half = (l_ + r_) / 2, max((r_ - l_) / 2, 0.05)
        ring = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            u, w = math.cos(a), math.sin(a)  # across, up
            k = math.sin(ph)
            x = mid + half * u * max(k, 0.0) ** 0.35 if 0 < i < rings else mid
            z = EYE_Z + EYE_Z * w * max(k, 0.0) ** 0.6 if 0 < i < rings else EYE_Z
            # lean: the top sits a little south of the base
            yy = y + 0.6 * (z - EYE_Z) / EYE_Z
            if mirror:
                x = 2 * AXIS - x
            ring.append((x, yy, z))
        lat.append(ring)
    verts = [[bm.verts.new(P(*p)) for p in ring] for ring in lat]
    out = []
    for a, b in zip(verts, verts[1:]):
        for j in range(seg):
            k = (j + 1) % seg
            out.append(bm.faces.new((a[j], a[k], b[k], b[j])))
    for f in out:
        f.material_index = mat_i
        f.smooth = True
    bmesh.ops.remove_doubles(bm, verts=[v for r in verts for v in r], dist=1e-6)
    return out


def lower_parts(bm, G, colors, mats, slot):
    sprite = {"name": "brain", "colors": colors}

    def add(i, **kw):
        if i not in slot:
            slot[i] = len(mats)
            mats.append(mat(sprite, i, TAG, **kw))
        return slot[i]
    eye_m = add(EYE, metallic=0.0, roughness=0.22, spec=0.6)
    tube_m = add(TUBE, metallic=0.0, roughness=0.7)
    stem_m = add(STEM, metallic=0.0, roughness=0.65)
    for mirror in (False, True):
        eye(bm, eye_m, mirror)
    tube(bm, STEM_PATH, stem_m, sides=14)
    for mirror in (False, True):
        tube(bm, T_OUTER, tube_m, mirror=mirror)
        tube(bm, T_MID, tube_m, mirror=mirror)
        tube(bm, T_EYE, tube_m, mirror=mirror)
        tube(bm, STEM_ROOT, stem_m, mirror=mirror)


# --- the arrow (newsh5-95) ----------------------------------------------------------------------------

def build_arrow(coll):
    """newsh5-95: a glowing green arrow pointing left, 12 x 14 px: a faceted arrowhead (columns 0-4) on a
    round shaft (rows 5-7) to the right edge, white-hot down its middle. Frames 209 and 247 fade it."""
    sp = common.load_sprite(WT, "newsh5-95")
    tag = "ns5-95A"

    def g(i, part, frames, glow, rough=0.9):
        # D126/D173: a glow is metallic 1 / rough, strength <= 1 / its brightest channel
        return common.palette_material(sp, i, f"{tag}-{part}", metallic=1.0, roughness=rough,
                                       emission_strength=glow, frames=frames)
    mats = [g(199, "rim", {209: 196, 247: 192}, 0.6),
            g(207, "chev", {209: 204, 247: 200}, 1.0),
            g(47, "cross", {209: 207, 247: 203}, 1.0),
            g(47, "hot", {247: 205}, 1.0),
            g(47, "core", {209: 204, 247: 200}, 1.0)]
    RIM, CHEV, CROSS, HOT, CORE = range(5)
    Wa, Ha = 12, 14

    def A(c, r, z):
        return Vector(((c - Wa / 2) * PX, (Ha / 2 - r) * PX, z * PX))
    bm = bmesh.new()
    yc = 6.5
    # head outline (edge coordinates), counter-clockwise from the tip as seen from above
    upper = [(0.9, 5.45), (1.95, 4.4), (2.95, 3.05), (4.0, 3.0), (5.0, 3.0)]
    ring0 = [(0.0, yc)] + [(c, 2 * yc - r) for c, r in upper] + [(5.0, yc)] + upper[::-1]
    cx = (3.1, yc)
    scales = [1.0, 0.64, 0.36, 0.14]
    zs = [0.25, 1.35, 2.1, 2.45]
    rings = []
    for s, z in zip(scales, zs):
        rings.append([bm.verts.new(A(cx[0] + (c - cx[0]) * s, cx[1] + (r - cx[1]) * s, z)) for c, r in ring0])
    bot_ring = [bm.verts.new(A(c, r, -0.25)) for c, r in ring0]
    apex = bm.verts.new(A(cx[0], yc, 2.6))
    under = bm.verts.new(A(cx[0], yc, -1.9))
    n = len(ring0)
    band_mat = [RIM, CHEV, CROSS]
    for k in range(3):
        a, b = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = band_mat[k]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((rings[3][i], rings[3][j], apex)).material_index = HOT
        bm.faces.new((bot_ring[i], rings[0][i], rings[0][j], bot_ring[j])).material_index = RIM  # the rim's edge
        bm.faces.new((bot_ring[j], under, bot_ring[i])).material_index = RIM
    # shaft: round, radius 1.5 px, from inside the head to the right edge; the top 1 px stripe is the core
    R = 1.5
    sides = 12
    st = [(3.6, 1.0), (10.0, 1.0), (11.0, 1.0), (11.75, 0.93), (12.0, 0.75)]
    sr = []
    for c, k in st:
        sr.append([bm.verts.new(A(c, yc + R * k * math.sin(2 * math.pi * (i + 0.5) / sides),
                                   R * k * math.cos(2 * math.pi * (i + 0.5) / sides))) for i in range(sides)])
    for si, (a, b) in enumerate(zip(sr, sr[1:])):
        c0 = st[si][0]
        for i in range(sides):
            j = (i + 1) % sides
            f = bm.faces.new((a[i], b[i], b[j], a[j]))
            top = i in (0, sides - 1)
            f.material_index = (CORE if c0 < 10 else CHEV if c0 < 11 else RIM) if top else RIM
    capc = bm.verts.new(A(12.0, yc, 0.0))
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((sr[-1][i], capc, sr[-1][j])).material_index = RIM
    capl = bm.verts.new(A(3.6, yc, 0.0))
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((sr[0][j], capl, sr[0][i])).material_index = RIM
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = False
    me = bpy.data.meshes.new("newsh5-95")
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new("newsh5-95", me)
    coll.objects.link(obj)
    # shading: the shaft smooth, the faceted head flat
    for p in me.polygons:
        p.use_smooth = me.vertices[p.vertices[0]].co.x > (4.0 - Wa / 2) * PX and all(
            me.vertices[v].co.x > (3.55 - Wa / 2) * PX for v in p.vertices)
    shell = common.outline_shell(obj, coll, islands="outer", faces=600)
    return [obj, shell]


# --- assembly -----------------------------------------------------------------------------------------

def to_object(bm, mats, name, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def cut_open(obj, layout, coll, suffix="_outline"):
    """Cut `obj` to each piece's 24 x 28 box WITHOUT filling the cut (outline shells: no ink across a
    seam), moved to the piece's origin. layout: [(name, cx px, cy px)]."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}{suffix}")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{name}{suffix}", me)
        coll.objects.link(sh)
        for poly in me.polygons:
            poly.use_smooth = True
        sh["tyrian_outline"] = True
        out[name] = sh
    return out


def build_brain(coll):
    G, colors = brain_grid()
    m = SM.masks(G.tolist(), {int(k): tuple(v) for k, v in colors.items()})
    inner = np.array(m["inner"], dtype=bool)
    bm, mats, slot = brain_mass(G, colors, inner)
    lower_parts(bm, G, colors, mats, slot)
    whole = to_object(bm, mats, "brain_whole", coll)
    crown = max(v.co.z for v in whole.data.vertices)
    # the outline shell from the sealed whole, every outer island (the tendrils stand free of the dome)
    shell = common.outline_shell(whole, coll, voxel=0.016, faces=14000, islands="outer")
    layout = [(n, c0 + 12 - W / 2, r0 + 14 - H / 2) for n, c0, r0 in LAY]
    pieces = common.split_assembly(whole, layout, coll)
    shells = cut_open(shell, layout, coll)
    anchor = round(crown * 0.75, 4)
    models = []
    for n, cx, cy in layout:
        p, s = pieces[n], shells[n]
        for f in p.data.polygons:  # the cut faces stand on the piece box: flat, so no seam shading
            xs = [p.data.vertices[i].co for i in f.vertices]
            if (all(abs(abs(v.x) - 1.0) < 1e-4 for v in xs) or all(abs(abs(v.y) - 14 / 12) < 1e-4 for v in xs)):
                f.use_smooth = False
        assert len(s.data.polygons) > 0, f"{n}: empty outline shell"
        for o in (p, s):
            o["tyrian_anchor"] = anchor
        models.append((n, [p, s], [int(n.split("-")[1])], (cx / 12, -cy / 12)))
    whole.hide_render = True
    shell.hide_render = True
    return models, whole, shell, crown, anchor


def build_models():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection("brainA")
    models, whole, wshell, crown, anchor = build_brain(coll)
    arrow = build_arrow(coll)
    models.append(("newsh5-95", arrow, [95, 209, 247], (6.0, 2.0)))
    return {name: objs for name, objs, _, _ in models}


def export(names):
    """Build everything, export only `names` (each at its own origin) to public/models/enemies/."""
    built = build_models()
    for name in names:
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, built[name], f"enemies/{name}", data["sprites"])
    return built
