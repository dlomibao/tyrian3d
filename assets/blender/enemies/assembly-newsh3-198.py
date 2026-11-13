"""SURFACE's sandy rock wall (episode 4: 4.4 SURFACE, 4.10 DESERTRUN), design A: one object across
three assemblies, built in one script.

- the rock arch, assembly-newsh3-198 (newsh3 162/164/241 over 198/200/202/279/281, 120x56 px);
- the plain wall stretch, assembly-newsh3-166 (newsh3 166/168/170 over 204/206/208, 72x56 px box);
- the wall clamp, assembly-newsh-caret-77 (newsh^ 77/79/81 over 115/7/119): a grey clamping machine
  on the same wall; its bottom middle is newsh-caret-7 (frames 7/9, with an electric arc each) and
  newsh-caret-7-f2 (frame 117, no arc).

Rock: the outline follows the sprite (pixel steps smoothed out); the arch is one mound (crest,
S-shaped drop to the lip, an undercut under the opening). In SURFACE a stretch is inserted between
the arch's 164|241 and 202|279, so the arch's column 72 and both cut ends of every stretch take one
section (seam_height: the crown's profile, no step at the joins); the stretches are the same section
run along their own edges (wall_height, wall_shell; cut ends straight, so stretches tile). The
crown's right cut comes down to newsh3-262's low shoulder and the legs to the ground at the sheet's
bottom; the outline shells lose their faces on the cut ends (trim_caps). The clamp's head and lug
are faired pchip lofts with a rim chamfer, the centre seam and the panel break as grooves. Every
rock face but the underside then takes the D175 facet ramp (lib_newshd_rock.facet_ramp:
flat facets, each one shade of the sprite's own ramp, the lit ones its highlights), matte
(metallic 0, roughness 0.88). The clamp is grey satin metal. Each group gets an outline shell
(D51, D189 islands="outer") from a sealed copy, cut open at the piece seams, and is cut into its
pieces with common.split_assembly.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh3-198.py (exports the arch only).
assembly-newsh3-166.py and assembly-newsh-caret-77.py import this file and export only their own
models (build_and_export). Review flags (scratch only, nothing is written without them):
-- [--only arch,wall,clamp] [--out review.glb] [--game dir].
"""

import json
import math
import re
import sys
from pathlib import Path

import bmesh
import bpy


def _find_repo():
    for p in Path(__file__).resolve().parents:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("repo root (assets/blender/common.py) not found above " + __file__)


WT = _find_repo()
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "assets" / "blender" / "enemies"), str(WT / "tools")]
import common  # noqa: E402
import lib_b017 as lib  # noqa: E402
import lib_newshd_rock as R  # noqa: E402
import sprite_mask as SM  # noqa: E402

ROOT = WT
U = lib.U

# --- the arch (from assembly-newsh3-198.py) ------------------------------------------------------


# The mound's shape, in sprite px. Across the band the top is a broad face: a short rounded
# shoulder at the outer edge, then a gentle ramp up to a crest line FALL px from the opening, then
# an S-shaped drop to the lip (so the lit top faces up and towards the light, and only a narrow
# band near the opening faces away from it).
CREST = 19.5      # crest height under the crown
FOOT = 3.0        # crest height where the legs leave the sheet at the bottom (the legs carry on as flat terrain art in game, so the arch comes down to meet it, not a 1-unit cliff)
LEG_ROW = 34      # rows above this are the crown (full crest height); below, the legs step down
SHOULDER = 6.0    # px from the outer edge to the top of its rounded shoulder...
SHOULDER_H = 0.55 # ... which is this share of the crest height
FALL = 8.0        # from the opening's edge back to the crest line
LIP = 0.2         # share of the local height left at the opening's edge under the crown...
LEG_LIP = 0.6     # ... and down the legs, which stay full-bodied to the sheet's bottom edge
LEG_ROWS = (40, 50)  # rows over which the lip changes from the one to the other
UNDERCUT = 7.0    # how far the rock under that lip is set back
UNDERCUT_SMOOTH = 6  # smoothing passes along the undercut's foot (no saw teeth under the lip)
EDGE = 0.3        # height at the outer edges
BOTTOM = 2.4      # depth of the underside
LOBE = 0.0        # px per unit of large-scale brightness above the mean
PILLOW = 3.5      # how far each lit boulder bulges between the cracks
PILLOW_R = 5.0    # px from the crack on a boulder's upper-left side to its top (a gentle lit face)...
PILLOW_STEEP = 1.3  # ... and from the crack on its lower-right side (a steep shaded drop)
CRACK = 1.8       # deepest crack
DARK_LUM = 0.42   # broad brightness under which the rock is the arch's shaded inside (no boulders)
SOFT_TOL = 1.6    # outline simplification for the distance fields (no stair-step ridges)
CHUNKS = [((20.5, 29.5), 7.0, 3.6)]  # the small lit boulder on the outer edge of the left leg: (c, r), height, radius
TOE = 0.9         # a low strip along the outline before the flank rises (no teeth at the ground)
CORNER = 3.0      # near the cut edges, the outer edge's distance is also measured from the raw outline
CORNER_LIFT = 0.8  # (plus this, so the foot keeps a low toe)
RINGS = (1.0, 2.0, 3.2, 4.7, 6.5, 8.6)  # rows of vertices along the smoothed outline, px in from it
RING_STEP = 1.3   # vertex spacing along those rows
STEP = 1.3        # interior facet size
BOTTOM_STEP = 5.0
TOL = 0.45        # outline simplification
TALL = 2.5        # ... and span more than this many px of height (not the cracks' small walls)
STEEP = 0.55      # facets steeper than this (normal z) take smoothed shades
OPENING_SEED = (75, 50)  # a pixel in the opening under the arch
CUT_COL, CUT_ROWS = 96, 28  # the crown's right end is cut (the rock carries on there)
ROUGH = 0.9       # matte sandstone
# Colours: the sprite draws its light (a dark outline ring, per-pixel shading, near-white
# highlights) and the game lights the model and draws its own outline, so the rock takes a
# smoothed tone of the sprite's colours: the outline ring is left out (filled from inside),
# highlights are capped, and the per-pixel speckle is blurred away. Large-scale tone (the lit
# crown, the darker striated inside of the arch) and the dark crack lines between the boulders
# (real markings, also cut in) stay.
RING = 1.6        # pixels this close to the empty pixels around them are the outline ring
TONE_R = 1        # blur radius of the tone, px (enough to drop single-pixel speckle)
TONE_MAX = 29     # highlights capped at this index (the light makes the shine)
CRACK_DARK = 5    # crack faces this many indices darker than the tone around them


# Where the stretches join the arch (fix round 1). In SURFACE a wall stretch (166/168/170 over
# 204/206/208) or the clamp stretch (77/79/81 over 115/117/119) is inserted between the arch's
# 164 | 241 and 202 | 279, so the arch's column 72 and both cut ends of every stretch are one seam.
# All three take the same section there: seam_height(row), the arch's own crown profile measured
# straight across the band (rows SEAM_R0..SEAM_R1, the inner edges of the sprite's ink there).
SEAM_COL = 72
SEAM_R0, SEAM_R1 = 3.0, 40.0
SEAM_BLEND = (2.0, 9.0)  # px from the seam: the section is exact inside the first, free past the second
WALL_RELIEF = 4.0  # px per unit of the stretches' blurred brightness about its mean
OUTLINE_SMOOTH = 4  # smoothing passes along the arch's outer outline (no inked teeth from pixel steps)
RIGHT_H, RIGHT_BLEND = 6.5, 10.0  # the crown's right cut: newsh3-262's left edge stands 5.6-7.1 px there
BOT_H, BOT_BLEND = 0.5, 9.0  # the legs come down to the ground at the sheet's bottom (terrain legs below)
BOT_EDGE = 0.2    # ... and their cut edge itself stands this high (px) over a bottom at 0 (no dark wall strip)


def crest_at(r, h=56):
    return CREST - (CREST - FOOT) * clamp01((r - LEG_ROW) / (h - LEG_ROW))


def lip_at(r):
    return LIP + (LEG_LIP - LIP) * smoothstep((r - LEG_ROWS[0]) / (LEG_ROWS[1] - LEG_ROWS[0]))


def core_height(d_out, d_in, r, h=56, lip_r=None):
    """The rock band's section (px) at row r, `d_out` px in from its north (outer) edge and `d_in`
    from its south edge (the arch's opening or the stretch's foot): a rounded shoulder, a ramp to
    the crest FALL px from the south edge, an S-shaped fall to the lip there. Also (t, u), the
    shoulder and fall parameters (relief fades out towards both edges with them)."""
    crest = crest_at(r, h)
    t = clamp01((d_out - TOE) / SHOULDER)
    q = clamp01((d_out - TOE - SHOULDER) / max(1.0, d_out + d_in - TOE - SHOULDER - FALL))
    rise = (1 - (1 - t) ** 2) * (SHOULDER_H + (1 - SHOULDER_H) * q)
    u = clamp01(d_in / FALL)
    lip = lip_at(r if lip_r is None else lip_r)
    return crest * rise * (lip + (1 - lip) * smoothstep(u)), t, u


def seam_height(r):
    return max(EDGE, core_height(max(0.0, r - SEAM_R0), max(0.0, SEAM_R1 - r), r)[0])


def seam_weight(dist):
    return 1 - smoothstep((dist - SEAM_BLEND[0]) / (SEAM_BLEND[1] - SEAM_BLEND[0]))


def flood(mask, seed):
    """The empty pixels 4-connected to `seed`."""
    h, w = len(mask), len(mask[0])
    out = [[False] * w for _ in range(h)]
    stack = [seed]
    while stack:
        c, r = stack.pop()
        if 0 <= r < h and 0 <= c < w and not mask[r][c] and not out[r][c]:
            out[r][c] = True
            stack += [(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)]
    return out


def clamp01(x):
    return max(0.0, min(1.0, x))


def smoothstep(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def chaikin(loop, iterations=3):
    """Corner-cut a closed polyline (rounds the sprite's pixel steps into a smooth line)."""
    for _ in range(iterations):
        n = len(loop)
        out = []
        for k in range(n):
            a, b = loop[k], loop[(k + 1) % n]
            out.append((a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25))
            out.append((a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75))
        loop = out
    return loop


class Segs:
    """Line segments with a coarse grid for nearest-distance queries."""

    def __init__(self, segs, cell=8.0):
        self.cell = cell
        self.grid = {}
        for a, b in segs:
            c0, c1 = sorted((a[0], b[0]))
            r0, r1 = sorted((a[1], b[1]))
            for gi in range(int(c0 // cell), int(c1 // cell) + 1):
                for gj in range(int(r0 // cell), int(r1 // cell) + 1):
                    self.grid.setdefault((gi, gj), []).append((a, b))

    def nearest(self, p, cap=40.0):
        """(distance, segment) of the nearest segment within `cap`, else (cap, None)."""
        gi, gj = int(p[0] // self.cell), int(p[1] // self.cell)
        best, seg = cap, None
        reach = 0
        while reach * self.cell <= best + self.cell:
            for di in range(-reach, reach + 1):
                for dj in range(-reach, reach + 1):
                    if max(abs(di), abs(dj)) != reach:
                        continue
                    for a, b in self.grid.get((gi + di, gj + dj), ()):
                        d = lib._seg_dist(p, a, b)
                        if d < best:
                            best, seg = d, (a, b)
            reach += 1
            if reach > cap / self.cell + 1:
                break
        return best, seg

    def dist(self, p, cap=40.0):
        return self.nearest(p, cap)[0]


def build_arch(sheet):
    coll = common.reset_collection("arch")
    mats = lib.Mats("nsh3_198", sheet.colors)
    # Sandstone: matte, not metal (its lit faces are real shape, lit by the game's light).
    dark = mats(19, metallic=0.0, roughness=ROUGH)  # the underside (never seen from above)
    rock = {i: mats(i, metallic=0.0, roughness=ROUGH) for i in range(16, 32)}
    h, w = sheet.h, sheet.w
    mask = [[v >= 0 for v in row] for row in sheet.pix]
    hole = flood(mask, OPENING_SEED)
    print("arch seam rows", {c: (min(r for r in range(h) if mask[r][c]), max(r for r in range(h) if mask[r][c]) + 1)
                             for c in (SEAM_COL - 1, SEAM_COL)}, "SEAM", SEAM_R0, SEAM_R1)

    def filled(c, r):
        ci, ri = int(math.floor(c)), int(math.floor(r))
        return 0 <= ri < h and 0 <= ci < w and mask[ri][ci]

    def vkind(c, r):
        """A loop vertex: 'open' (the rock carries on past it), 'hole' (the opening's edge) or 'outer'."""
        e = 1e-3
        if c > w - e or r > h - e or (abs(c - CUT_COL) < e and r <= CUT_ROWS + e):
            return "open"
        ci, ri = int(round(c)), int(round(r))
        for dr in (-1, 0):
            for dc in (-1, 0):
                rr, cc = ri + dr, ci + dc
                if 0 <= rr < h and 0 <= cc < w and hole[rr][cc]:
                    return "hole"
        return "outer"

    def skind(a, b):
        """A loop segment's kind, from the empty pixel just outside its middle."""
        ka, kb = vkind(*a), vkind(*b)
        if ka == kb:
            return ka
        if "hole" in (ka, kb):
            return "hole"
        mc, mr = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1.0
        oc, orr = mc - ty / L * 0.5, mr + tx / L * 0.5  # outward
        ci, ri = int(math.floor(oc)), int(math.floor(orr))
        if not (0 <= ri < h and 0 <= ci < w) or (ci >= CUT_COL and ri < CUT_ROWS):
            return "open"
        return "outer"

    traced = lib.trace_loops(mask)
    loops = [lib.simplify_loop(l, TOL) for l in traced]
    loops = [l for l in loops if len(l) >= 3]
    # Split long outline edges so the outline's vertices are as close together as the rows inside
    # it (long edges fanning out to many row points make sliver facets that read as teeth).
    fine, kinds, seg_kinds = [], [], []
    for loop in loops:
        n = len(loop)
        pts, ks, sk = [], [], []
        for k in range(n):
            a, b = loop[k], loop[(k + 1) % n]
            kind_ab = skind(a, b)
            m = max(1, round(math.dist(a, b) / RING_STEP))
            for j in range(m):
                s = j / m
                pts.append((a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s))
                ks.append(vkind(*a) if j == 0 else kind_ab)
                sk.append(kind_ab)
        # The outline's pixel steps smoothed out along the loop (the cut edges stay put): stepped,
        # the ink drew a row of teeth along the crown's diagonal and the opening's edge.
        n = len(pts)
        for _ in range(OUTLINE_SMOOTH):
            pts = [((pts[k - 1][0] + 2 * pts[k][0] + pts[(k + 1) % n][0]) / 4,
                    (pts[k - 1][1] + 2 * pts[k][1] + pts[(k + 1) % n][1]) / 4)
                   if ks[k] == ks[k - 1] == ks[(k + 1) % n] == sk[k] == sk[k - 1] != "open"
                   else pts[k] for k in range(n)]
        fine.append(pts)
        kinds.append(ks)
        seg_kinds += sk
    loops = fine
    segs = [(loop[k], loop[(k + 1) % len(loop)]) for loop in loops for k in range(len(loop))]
    all_segs = Segs(segs)
    kind_of = dict(zip(segs, seg_kinds))
    raw_outer = Segs([s for s, k in zip(segs, seg_kinds) if k == "outer"])
    open_segs = Segs([s for s, k in zip(segs, seg_kinds) if k == "open"])
    right_segs = Segs([s for s, k in zip(segs, seg_kinds) if k == "open" and min(s[0][0], s[1][0]) >= CUT_COL - 0.01
                       and max(s[0][1], s[1][1]) <= CUT_ROWS + 0.01])
    # The heights are measured from a smoothed outline: measured from the sprite's pixel steps,
    # every step would raise a ridge up the flank.
    soft_outer, soft_hole, soft_loops = [], [], []
    for loop in traced:
        soft = chaikin(lib.simplify_loop(loop, SOFT_TOL))
        if len(soft) < 3:
            continue
        soft_loops.append(soft)
        for k in range(len(soft)):
            sa, sb = soft[k], soft[(k + 1) % len(soft)]
            _, seg = all_segs.nearest(((sa[0] + sb[0]) / 2, (sa[1] + sb[1]) / 2), cap=4.0)
            kind = kind_of.get(seg, "open")
            if kind == "outer":
                soft_outer.append((sa, sb))
            elif kind == "hole":
                soft_hole.append((sa, sb))
    outer = Segs(soft_outer)
    soft_all = Segs([(l[k], l[(k + 1) % len(l)]) for l in soft_loops for k in range(len(l))])
    # The opening carries on below the sheet.
    hole_segs = soft_hole
    for c in range(w):
        if hole[h - 1][c] and (c == 0 or not hole[h - 1][c - 1]):
            hole_segs.append(((c, h), (c, h + 40)))
        if hole[h - 1][c] and (c == w - 1 or not hole[h - 1][c + 1]):
            hole_segs.append(((c + 1, h), (c + 1, h + 40)))
    inner = Segs(hole_segs)

    # Large-scale brightness, the dark cracks between the lit boulders, and the boulder facets
    # between them, per pixel.
    lum = [[clamp01((sheet.pix[r][c] - 16) / 15) if mask[r][c] else 0.0 for c in range(w)] for r in range(h)]
    big = lib.blur(lum, mask, 4)
    near = lib.blur(lum, mask, 2)
    vals = [big[r][c] for r in range(h) for c in range(w) if mask[r][c]]
    mean = sum(vals) / len(vals)
    d_edge = lib.distance_field(mask, "rb")
    lit = [[clamp01((big[r][c] - DARK_LUM - 0.04) / 0.16) if mask[r][c] else 0.0 for c in range(w)]
           for r in range(h)]
    is_crack = [[mask[r][c] and d_edge[r][c] > 2.2 and near[r][c] > 0.45 and lum[r][c] < near[r][c] - 0.1
                 for c in range(w)] for r in range(h)]
    crack = lib.blur([[1.0 if is_crack[r][c] else 0.0 for c in range(w)] for r in range(h)], mask, 1)
    d_crack = lib.distance_field([[mask[r][c] and not is_crack[r][c] for c in range(w)] for r in range(h)], "rb")
    # Each boulder is lit from the upper left like the sprite's: from the crack on its upper-left
    # side its top rises gently (facing the light), and at the crack on its lower-right side it
    # drops steeply (the sprite's dark crack lines sit on the boulders' lower-right edges).
    def pillow_at(c, r):
        d = d_crack[r][c]
        gc = d_crack[r][min(w - 1, c + 1)] - d_crack[r][max(0, c - 1)]
        gr = d_crack[min(h - 1, r + 1)][c] - d_crack[max(0, r - 1)][c]
        g = math.hypot(gc, gr) or 1.0
        away = (gc + gr) / (g * math.sqrt(2))  # +1: the nearest crack is up-left, -1: down-right
        rad = PILLOW_STEEP + (PILLOW_R - PILLOW_STEEP) * clamp01(0.5 + away)
        return smoothstep((d - 0.5) / rad)

    pillow = [[pillow_at(c, r) * lit[r][c] if mask[r][c] else 0.0 for c in range(w)] for r in range(h)]
    pillow = lib.blur(pillow, mask, 1)

    # The rock's tone per pixel (see RING..CRACK_DARK): a blur of the capped sprite colours over
    # the pixels that are neither the outline ring nor cracks; those take their neighbours' tone.
    src_ok = [[mask[r][c] and d_edge[r][c] > RING and not is_crack[r][c] for c in range(w)] for r in range(h)]
    tone = [[0.0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if not mask[r][c]:
                continue
            for rad in (TONE_R, TONE_R + 2, TONE_R + 5):
                s = n = 0.0
                for rr in range(max(0, r - rad), min(h, r + rad + 1)):
                    for cc in range(max(0, c - rad), min(w, c + rad + 1)):
                        if src_ok[rr][cc]:
                            s += min(TONE_MAX, sheet.pix[rr][cc])
                            n += 1
                if n:
                    break
            tone[r][c] = s / n if n else float(min(TONE_MAX, max(16, sheet.pix[r][c])))

    wall_tone = lib.blur(tone, mask, 3)  # the walls' tone, smoother (no stripes down the flanks)

    def tone_index(c, r, on_crack=False, field=tone):
        v = lib.bilinear(field, mask, c, r) - (CRACK_DARK if on_crack else 0)
        return max(16, min(31, round(v)))
    def height(c, r, on_hole=False):
        """The top's height (px) at corner-coordinate point (c, r) (`on_hole`: on the opening's edge)."""
        crest = CREST - (CREST - FOOT) * clamp01((r - LEG_ROW) / (h - LEG_ROW))
        d_out = outer.dist((c, r))
        if open_segs.dist((c, r), cap=CORNER + 1) < CORNER:
            # where the outline meets a cut edge the smoothed outline cuts the corner off: measure
            # from the raw outline too, so the corner comes down to the ground (no fin)
            d_out = min(d_out, raw_outer.dist((c, r)) + CORNER_LIFT)
        t = clamp01((d_out - TOE) / SHOULDER)
        d_in = 0.0 if on_hole else inner.dist((c, r))
        q = clamp01((d_out - TOE - SHOULDER) / max(1.0, d_out + d_in - TOE - SHOULDER - FALL))
        rise = (1 - (1 - t) ** 2) * (SHOULDER_H + (1 - SHOULDER_H) * q)
        u = clamp01(d_in / FALL)
        lip = LIP + (LEG_LIP - LIP) * smoothstep((r - LEG_ROWS[0]) / (LEG_ROWS[1] - LEG_ROWS[0]))
        fall = lip + (1 - lip) * smoothstep(u)
        b = lib.bilinear(big, mask, c, r) - mean
        k = lib.bilinear(crack, mask, c, r)
        bulge = PILLOW * lib.bilinear(pillow, mask, c, r)
        relief = (LOBE * max(-0.3, min(0.4, b)) + bulge - CRACK * k) * t * smoothstep(u * 1.5)
        z = crest * rise * fall + relief
        for (bc, br), top, rad in CHUNKS:
            q = 1 - ((c - bc) ** 2 + (r - br) ** 2) / rad ** 2
            if q > 0:
                z = max(z, top * math.sqrt(q))
        # the seam with the inserted stretches: exactly their section there
        if r < SEAM_R1 + 2:
            wgt = seam_weight(abs(c - SEAM_COL))
            z += (seam_height(r) - z) * wgt
        # the crown's right cut comes down to newsh3-262's low shoulder
        wgt = 1 - smoothstep(right_segs.dist((c, r), cap=RIGHT_BLEND + 1) / RIGHT_BLEND)
        z += (min(z, RIGHT_H) - z) * wgt
        # and the legs come down to the ground at the sheet's bottom edge
        wgt = smoothstep((r - (h - BOT_BLEND)) / BOT_BLEND)
        z += (min(z, BOT_H) - z) * wgt
        return max(EDGE, z)

    def ztop(c, r, boundary_kind):
        if boundary_kind == "outer":
            # the small boulder on the outer edge stands up from the ground there (a short wall)
            z = EDGE
            for (bc, br), top, rad in CHUNKS:
                qq = 1 - ((c - bc) ** 2 + (r - br) ** 2) / rad ** 2
                if qq > 0:
                    z = max(z, 0.6 * top * math.sqrt(qq))
            return z * U
        if boundary_kind == "open" and r > h - 1e-3:
            return min(height(c, r), BOT_EDGE) * U
        return height(c, r, boundary_kind == "hole") * U

    def zbot(c, r, boundary_kind):
        if boundary_kind == "open" and r > h - 1e-3:
            return 0.0  # the legs' bottom cut: a sliver of a wall, no dark strip along the terrain join
        return -(EDGE if boundary_kind else BOTTOM) * U

    # The undercut: the bottom of the wall under the opening's lip is set back into the rock, easing
    # in over a few px where the opening's edge meets the cut edges.
    bottom_loops = []
    for loop, ks in zip(loops, kinds):
        n = len(loop)
        moved = []
        for k in range(n):
            c, r = loop[k]
            if ks[k] != "hole":
                moved.append((c, r))
                continue
            best = 1e9
            for sgn in (1, -1):
                dist, j = 0.0, k
                for _ in range(n):
                    j2 = (j + sgn) % n
                    dist += math.dist(loop[j], loop[j2])
                    j = j2
                    if ks[j] != "hole" or dist > 4:
                        break
                if ks[j] != "hole":
                    best = min(best, dist)
            a = loop[(k - 2) % n]
            b = loop[(k + 2) % n]
            tx, ty = b[0] - a[0], b[1] - a[1]
            L = math.hypot(tx, ty) or 1.0
            # (none at the seam: the stretches' south faces stand straight there)
            amt = UNDERCUT * clamp01(best / 4) * smoothstep((abs(c - SEAM_COL) - SEAM_BLEND[0]) / 5.0)
            moved.append((c + ty / L * amt, r - tx / L * amt))  # inward is (ty, -tx)
        # The undercut's foot follows the pixel steps of the opening's edge: smooth it along the
        # loop so the wall under the lip is one even concave sweep, not a row of teeth.
        for _ in range(UNDERCUT_SMOOTH):
            moved = [((moved[(k - 1) % n][0] + 2 * moved[k][0] + moved[(k + 1) % n][0]) / 4,
                      (moved[(k - 1) % n][1] + 2 * moved[k][1] + moved[(k + 1) % n][1]) / 4)
                     if ks[k] == "hole" and ks[(k - 1) % n] == "hole" and ks[(k + 1) % n] == "hole"
                     else moved[k] for k in range(n)]
        bottom_loops.append(moved)

    # Rows of points following the outline, so the flanks rise in even steps.
    ring_pts = []
    bucket = {}

    def free(p, d):
        gi, gj = int(p[0] // 1), int(p[1] // 1)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for q in bucket.get((gi + di, gj + dj), ()):
                    if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < d * d:
                        return False
        return True

    def add(p, o):
        if not filled(*p) or not lib._point_in_loops(p, loops):
            return
        if all_segs.dist(p, cap=o + 1) < min(0.45, o * 0.85) or soft_all.dist(p, cap=o + 1) < o * 0.85 \
                or not free(p, 0.7):
            return
        ring_pts.append(p)
        bucket.setdefault((int(p[0] // 1), int(p[1] // 1)), []).append(p)

    def normal(a, b):
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        return (b[1] - a[1]) / L, -(b[0] - a[0]) / L  # inward

    # The rows follow the smoothed outline (the heights are measured from it), so they rise in
    # even steps without the sprite's pixel steps.
    for loop in soft_loops:
        n = len(loop)
        # resample at RING_STEP
        samples = []
        for k in range(n):
            a, b = loop[k], loop[(k + 1) % n]
            L = math.dist(a, b)
            m = max(1, round(L / (RING_STEP * 0.5)))
            for i in range(m):
                s = i / m
                samples.append((a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s))
        ns = len(samples)
        acc = RING_STEP
        prev = samples[0]
        for k in range(ns):
            p0 = samples[k]
            acc += math.dist(prev, p0)
            prev = p0
            if acc < RING_STEP:
                continue
            acc = 0.0
            pa, pb = samples[(k - 2) % ns], samples[(k + 2) % ns]
            nx, ny = normal(pa, pb)
            for o in RINGS:
                add((p0[0] + nx * o, p0[1] + ny * o), o)
    inner_pts = [p for p in lib._fill_points(loops, mask, STEP, 1, margin=RINGS[-1] + 0.9) if free(p, 1.0)]

    bm = bmesh.new()
    ring_top, ring_bot = {}, {}
    flat_kinds = [k for ks in kinds for k in ks]

    def surface(outline, interior, zf, ring, is_top):
        vout, tris, ids, nb = lib._triangulate(outline, interior)
        verts = {}
        for k, co in enumerate(vout):
            oid = ids[k]
            if oid is not None and oid < nb:
                if oid not in ring:
                    ring[oid] = bm.verts.new((sheet.X(co.x), sheet.Y(co.y), zf(co.x, co.y, flat_kinds[oid])))
                verts[k] = ring[oid]
            else:
                verts[k] = bm.verts.new((sheet.X(co.x), sheet.Y(co.y), zf(co.x, co.y, None)))
        faces = []
        for f in tris:
            vs = [verts[j] for j in f]
            if len(set(vs)) < 3:
                continue
            if not is_top:
                vs.reverse()
            try:
                face = bm.faces.new(vs)
            except ValueError:
                continue
            faces.append((face, f, vout))
        return faces

    d_hole = lib.distance_field([[not hole[r][c] for c in range(w)] for r in range(h)], "lrtb")
    bot_pts = [p for p in lib._fill_points(loops, mask, BOTTOM_STEP, 8, margin=BOTTOM_STEP * 0.45)
               if lib.bilinear(d_hole, mask, *p) > UNDERCUT + 2]
    tops = surface(loops, ring_pts + inner_pts, ztop, ring_top, True)
    bots = surface(bottom_loops, bot_pts, zbot, ring_bot, False)
    smooth_tops = []
    for face, f, vout in tops:
        cc = sum(vout[j].x for j in f) / len(f)
        rr = sum(vout[j].y for j in f) / len(f)
        # Every facet takes the rock's tone under it (not the sprite's pixel: no outline ring on
        # the low strip along the edge, no painted highlights or per-pixel patchwork); facets on
        # the cracks between the boulders stay darker (except on the steep flanks and the faces
        # into the cave, where a crack pixel would streak down the wall).
        face.normal_update()
        span = max(q.co.z for q in face.verts) - min(q.co.z for q in face.verts)
        steep = abs(face.normal.z) < STEEP and span > TALL * U
        ci, ri = int(math.floor(cc)), int(math.floor(rr))
        on_crack = not steep and 0 <= ri < h and 0 <= ci < w and is_crack[ri][ci]
        face.material_index = rock[tone_index(cc, rr, on_crack)]
        smooth_tops.append(face)
    for face, _, _ in bots:
        face.material_index = dark
    # Walls between the top and bottom rings (outer flanks, the undercut, the cut edges) take the
    # tone just inside them: the game's light shades them and its outline draws the dark edge.
    i = 0
    for loop in loops:
        n = len(loop)
        for k in range(n):
            a, b = i + k, i + (k + 1) % n
            if a in ring_top and b in ring_top and a in ring_bot and b in ring_bot:
                try:
                    face = bm.faces.new((ring_bot[a], ring_bot[b], ring_top[b], ring_top[a]))
                except ValueError:
                    continue
                s0, s1 = loop[k], loop[(k + 1) % n]
                nx, ny = normal(s0, s1)
                pc, pr = (s0[0] + s1[0]) / 2 + nx * 1.5, (s0[1] + s1[1]) / 2 + ny * 1.5
                face.material_index = rock[tone_index(pc, pr, field=wall_tone)]
        i += n
    # The top is smooth shaded (rounded rock, no facet noise); walls, underside and cut faces stay flat.
    return lib.to_object("arch", bm, mats.list, coll, smooth_faces=smooth_tops)


# --- the clamp (from assembly-newsh-caret-77.py) ---

AXIS = 33


def build_clamp(sheet):
    coll = common.reset_collection("clamp")
    mats = lib.Mats("nshc77", sheet.colors)
    pix = sheet.pix

    # Rock: the wall's own pixels plus what the machine covers on it (not the pincers below it).
    h, w = sheet.h, sheet.w
    mask = [[False] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            v = pix[r][c]
            if 16 <= v <= 31:
                mask[r][c] = True
            elif v >= 1 and v <= 15:
                mask[r][c] = r <= 33 or (r <= 38 and not 17 <= c <= 49)
    # Rock-coloured specks off the wall (a few pixels between the jaws and the pincers) would stand
    # up as thin dark posts: only the wall's own large regions are rock.
    seen = set()
    for r0 in range(h):
        for c0 in range(w):
            if not mask[r0][c0] or (c0, r0) in seen:
                continue
            comp, stack = [], [(c0, r0)]
            seen.add((c0, r0))
            while stack:
                c, r = stack.pop()
                comp.append((c, r))
                for cc, rr in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                    if 0 <= rr < h and 0 <= cc < w and mask[rr][cc] and (cc, rr) not in seen:
                        seen.add((cc, rr))
                        stack.append((cc, rr))
            if len(comp) < 12:
                print(f"clamp: rock speck of {len(comp)} px dropped at {comp[0]}")
                for c, r in comp:
                    mask[r][c] = False
    # The band the rock's section is measured from: the wall carries on behind the machine, its
    # foot running straight from one side of the machine to the other.
    edge = [row[:] for row in mask]
    foot = {c: max(r for r in range(h) if mask[r][c]) + 1 for c in (16, 50)}
    for c in range(17, 50):
        bottom = foot[16] + (foot[50] - foot[16]) * (c - 16) / 34
        for r in range(h):
            if r < bottom and any(mask[rr][c] for rr in range(r + 1)):
                edge[r][c] = True
    bm = bmesh.new()
    wall_rock(bm, sheet, mats, mask, rock_index=lambda v: v if 16 <= v <= 31 else 21, edge_mask=edge)
    bm.verts.ensure_lookup_table()
    n_rock = len(bm.verts)

    X = lambda c: sheet.X(c + 0.5)  # noqa: E731  pixel centre column -> X
    Y = lambda r: sheet.Y(r + 0.5)  # noqa: E731
    P = lambda c, r, z: (X(c), Y(r), z)  # noqa: E731
    U = lib.U
    ax = X(AXIS)
    body = mats(6, **METAL)  # satin grey, not mirror (D176: F0 through Specular IOR Level)
    plate = mats(8, **METAL)
    lower = mats(7, **METAL)
    skirt = mats(5, **METAL)
    dark = mats(4, **METAL)
    seam = mats(3, **dict(METAL, roughness=0.7))
    handle = mats(5, **METAL)
    smooth = []

    # Head and lug: faired lofts, seated as one gently curved shell over the ridge (seat_machine).
    head_v0 = len(bm.verts)
    faces, lug_v0 = clamp_head(bm, sheet, ax, dict(side=body, lower=lower, plate=plate, rim=plate, skirt=skirt,
                                                   seam=seam, groove=dark))
    smooth += faces
    head_v1 = len(bm.verts)

    left = []
    # D-shaped grab handle: out of the rock at its top right, over and down the left side, back
    # into the housing.
    path = [(19.0, 6.0, 0.24), (17.0, 3.6, 0.4), (13.0, 2.9, 0.46), (10.0, 4.6, 0.46), (9.6, 9.0, 0.44),
            (9.8, 14.0, 0.42), (11.2, 17.6, 0.4), (14.5, 19.4, 0.38), (18.5, 19.8, 0.34)]
    left += lib.tube(bm, [(P(c, r, z), 1.8 * U) for c, r, z in path], sides=8, mat_index=handle)
    # Spider leg from the housing's side down to a foot on the rock.
    path = [(19.0, 21.2, 0.36), (16.4, 23.4, 0.38), (13.8, 26.2, 0.38), (11.4, 29.4, 0.36),
            (9.4, 32.6, 0.33), (7.6, 35.2, 0.3)]
    left += lib.tube(bm, [(P(c, r, z), 1.6 * U) for c, r, z in path], sides=8, mat_index=dark)
    left += lib.ellipsoid(bm, P(7.0, 35.6, 0.27), (3.6 * U, 2.0 * U, 0.07), mat_index=dark)
    # Pincer: from under the housing, curving down and in to its tip.
    # (centres and half widths from frame 117's pixels inside the ink, rows 39-53)
    path = [(27.5, 29.5, 0.34, 3.6), (25.0, 33.0, 0.32, 4.6), (24.0, 35.0, 0.31, 4.0), (22.5, 37.0, 0.3, 3.5),
            (20.1, 39.5, 0.29, 3.4),
            (20.2, 41.5, 0.29, 3.0), (20.1, 43.5, 0.28, 2.5), (20.5, 45.5, 0.28, 2.0), (21.0, 47.2, 0.27, 1.5),
            (21.6, 49.0, 0.27, 1.0), (22.4, 50.6, 0.27, 0.65), (23.3, 52.0, 0.27, 0.4), (24.0, 53.3, 0.27, 0.0)]
    left += lib.tube(bm, [(P(c, r, z), rad * U) for c, r, z, rad in path], sides=8, mat_index=plate, flat=0.6)
    smooth += left + lib.mirror_faces(bm, left, ax)

    seat_machine(bm, n_rock, [(head_v0, lug_v0, HEAD_SEAT, max), (lug_v0, head_v1, 4.0 * U, max),
                              (head_v1, len(bm.verts), 3.0 * U, None)])
    for mt in mats.list:
        if (pal_of(mt) or 99) <= 15:
            bsdf = next(n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = METAL_SPEC
    return lib.to_object("clamp", bm, mats.list, coll, smooth_faces=smooth)


MACHINE_BASE = 0.3  # the rock top the machine's heights above were drawn for


def seat_machine(bm, n_rock, groups):
    """Sit the machine on the ridge: every machine vertex rises by the rock's height under it (the
    mean, or `pick` of the heights, over a disc of the group's `reach`, so a part bends with the ridge, not with each facet)
    less MACHINE_BASE; past the rock (the pincers below it) the nearest rock edge's height counts,
    so the pincers reach down the ridge's flank. `groups`: (first vertex, end vertex, reach,
    pick); the head takes the highest point of a wide disc, so it lies over the crest as one gently
    curved shell with no rock poking through."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    bm.verts.index_update()
    rock_faces = [f for f in bm.faces if all(v.index < n_rock and v.co.z > 0.0 for v in f.verts)]
    verts = [v.co.copy() for v in bm.verts[:n_rock]]
    tree = BVHTree.FromPolygons(verts, [[v.index for v in f.verts] for f in rock_faces])

    def height(x, y):
        hit = tree.ray_cast(Vector((x, y, 10.0)), Vector((0, 0, -1)))
        if hit[0] is not None:
            return hit[0].z
        near = tree.find_nearest(Vector((x, y, 0.0)))
        return near[0].z if near[0] is not None else MACHINE_BASE

    lifts = []
    for v0, v1, reach, pick in groups:
        pts = [(0.0, 0.0)] + [(math.cos(a) * rr, math.sin(a) * rr) for rr in (reach * 0.5, reach)
                              for a in (k * math.pi / 4 for k in range(8))]
        cache = {}
        for v in bm.verts[v0:v1]:
            key = (round(v.co.x, 3), round(v.co.y, 3))
            if key not in cache:
                hs = [height(v.co.x + dx, v.co.y + dy) for dx, dy in pts]
                cache[key] = pick(hs) if pick else sum(hs) / len(hs)
            v.co.z += cache[key] - MACHINE_BASE
        lifts += list(cache.values())
    print(f"seat_machine: {len(rock_faces)} rock faces, lift {min(lifts) - MACHINE_BASE:.2f}.."
          f"{max(lifts) - MACHINE_BASE:.2f}")


#: The clamp's grey metal: satin, F0 held down (D176's Specular IOR Level) so the game's sun and
#: environment don't wash the mid greys to white.
METAL = dict(metallic=0.15, roughness=0.66)
METAL_SPEC = 0.25
HEAD_SEAT = 6.0 * U
# Head plan (sprite rows, corner coordinates; half widths in px from the axis at column 33.5):
# the outer outline, and the crease where the top plate meets the side panels, which runs from the
# shoulders (column 24) round to the centre at row 24 (the sprite's bright rim); below that the two
# lower halves meet at the centre seam.
HEAD_W = ([14.6, 15.2, 16.8, 19.5, 22.0, 23.8, 25.5, 28.5, 31.5, 33.8],
          [8.4, 9.2, 13.0, 15.5, 16.0, 13.5, 10.5, 8.5, 6.0, 3.0])
HEAD_P = ([14.6, 21.0, 22.0, 23.0, 24.0, 24.6, 34.0], [8.2, 8.8, 7.8, 5.5, 2.0, 0.0, 0.0])
HEAD_HC = ([14.6, 15.4, 18.0, 21.0, 24.0, 27.0, 30.0, 33.8], [0.10, 0.20, 0.23, 0.235, 0.22, 0.18, 0.14, 0.09])
HEAD_Z0, HEAD_ZS, HEAD_RIM, HEAD_CROWN = -0.30, 0.05, 0.022, 0.018
SEAM_HW, SEAM_DEPTH = 0.45, 0.035   # the centre seam (rows 24-33): half width px, depth units
BREAK_ROWS, BREAK_DEPTH = (18.45, 18.6, 19.0, 19.15), 0.028   # the panel break across the plate
LUG_W = ([2.9, 3.4, 4.6, 7.0, 19.0], [1.0, 2.4, 3.9, 4.6, 4.6])
LUG_T = ([2.9, 3.6, 5.0, 19.0], [1.6, 2.8, 3.6, 3.8])  # px above the rock
LUG_B, LUG_R = -6.0, 1.8


def _ngon_tris(bm, verts, mat):
    try:
        face = bm.faces.new(verts)
    except ValueError:
        return []
    face.material_index = mat
    res = bmesh.ops.triangulate(bm, faces=[face], quad_method="BEAUTY", ngon_method="BEAUTY")
    return res["faces"]


def _loft(bm, rings, seg_mat, smooth_seg, cap_mat):
    """Faces between rings of vertices (closed loops of equal length); seg_mat(k, r_mid) -> material of
    segment k between two rings, smooth_seg(k) -> smooth shaded. Caps both ends. Returns smooth faces."""
    smooth = []
    for (ra, ya), (rb, yb) in zip(rings, rings[1:]):
        n = len(ra)
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new((ra[k], ra[j], rb[j], rb[k]))
            f.material_index = seg_mat(k, (ya + yb) / 2)
            if smooth_seg(k):
                smooth.append(f)
    _ngon_tris(bm, list(reversed(rings[0][0])), cap_mat)
    _ngon_tris(bm, list(rings[-1][0]), cap_mat)
    return smooth


def clamp_head(bm, sheet, ax, m):
    """The clamp's head and the lug on top of it, as faired lofts down the sprite's rows (pchip
    stations): chamfered sections with a slightly crowned top plate, a sharp rim chamfer at the
    crease, rounded side panels falling to a short skirt, the centre seam down the lower halves and
    the panel break across the plate at row 18.8 as modelled grooves. Heights are above the rock
    (seat_machine lifts them). Returns the smooth faces."""
    from usp_talon import pchip
    W, Pc, HC = pchip(*HEAD_W), pchip(*HEAD_P), pchip(*HEAD_HC)
    G = SEAM_HW
    rows = sorted(set([round(14.6 + 0.5 * k, 3) for k in range(39)] + list(BREAK_ROWS) + [24.0, 33.8]))
    rows = [r for r in rows if r <= 33.8]

    def groove(r):
        return BREAK_DEPTH if BREAK_ROWS[1] - 1e-6 <= r <= BREAK_ROWS[2] + 1e-6 else 0.0

    def seam_d(r):
        return SEAM_DEPTH * smoothstep((r - 23.4) / 0.8) * (1 - smoothstep((r - 32.6) / 1.0))

    def section(r):
        w_ = W(r)
        p_ = max(G, min(Pc(r), w_ - 1.6))
        hc = HC(r)
        ht = hc + HEAD_RIM
        g = groove(r)
        span = w_ - (p_ + 0.7)
        half = [(w_, HEAD_Z0), (w_, HEAD_ZS), (w_ - 0.5, HEAD_ZS + 0.04),
                (w_ - span / 3, HEAD_ZS + (hc - HEAD_ZS) * 0.62), (w_ - 2 * span / 3, HEAD_ZS + (hc - HEAD_ZS) * 0.9),
                (p_ + 0.7, hc - g), (p_, ht - g), ((p_ + G) / 2, ht + HEAD_CROWN * 0.7 - g), (G, ht + HEAD_CROWN - g)]
        centre = (0.0, ht + HEAD_CROWN - g - seam_d(r))
        left = [(-o, z) for o, z in half] + [centre]
        right = [(o, z) for o, z in reversed(half)]
        return left + right   # 19 points; segment 18 is the bottom

    # segment kinds, left half then right (see section): 0 skirt, 1-4 side, 5 rim, 6-7 plate, 8 centre
    kinds = ["skirt", "side", "side", "side", "side", "rim", "plate", "plate", "centre",
             "centre", "plate", "plate", "rim", "side", "side", "side", "side", "skirt", "bottom"]
    rings = []
    for r in rows:
        y = sheet.Y(r)
        rings.append(([bm.verts.new((ax + o * U, y, MACHINE_BASE + z)) for o, z in section(r)], r))

    def head_mat(k, r):
        kind = kinds[k]
        if kind in ("rim", "plate", "centre") and BREAK_ROWS[0] < r < BREAK_ROWS[3]:
            return m["groove"]
        if kind == "centre":
            return m["seam"] if r > 24.0 else m["plate"]
        if kind == "side":
            return m["side"] if r < 24.0 else m["lower"]
        if kind == "plate":
            return m["plate"] if r < 24.6 else m["lower"]
        return {"rim": m["rim"], "skirt": m["skirt"], "bottom": m["skirt"]}[kind]

    smooth = _loft(bm, rings, head_mat, lambda k: kinds[k] in ("side", "plate"), m["skirt"])
    lug_v0 = len(bm.verts)

    # The lug: a rounded bar standing up from the head's top, its north end rounded in plan and
    # falling off; its south end stands a little proud of the plate (the sprite's dark row 18).
    LW, LT = pchip(*LUG_W), pchip(*LUG_T)
    lrows = [2.9, 3.15, 3.4, 3.8, 4.2, 4.6, 5.2, 6.0, 7.0] + [8.0 + k for k in range(11)] + [18.6, 19.0]
    arc_n = 4

    def lug_section(r):
        a, t = LW(r), LT(r)
        rc = min(LUG_R, a * 0.6)
        pts = [(-a, LUG_B)]
        for i in range(arc_n + 1):
            th = math.pi - (math.pi / 2) * i / arc_n
            pts.append((-a + rc + rc * math.cos(th), t - rc + rc * math.sin(th)))
        pts.append((0.0, t + 0.25))
        pts += [(-o, z) for o, z in reversed(pts[:-1])]
        return pts

    n_l = len(lug_section(10.0))
    lrings = []
    for r in lrows:
        y = sheet.Y(r)
        lrings.append(([bm.verts.new((ax + o * U, y, MACHINE_BASE + z * U)) for o, z in lug_section(r)], r))
    smooth += _loft(bm, lrings, lambda k, r: m["plate"], lambda k: k != n_l - 1, m["plate"])
    return smooth, lug_v0


#: The arc's bolts: strands across the band (fractions of its width per column), their palette
#: index and glow; the middle strands are the hot core, the outer ones the bluer fringe.
ARC_STRANDS = [(0.08, 59, 0.9), (0.3, 60, 1.0), (0.5, 62, 1.4), (0.7, 61, 1.2), (0.92, 59, 0.9)]
ARC_JAG = 0.3        # px: how far a strand's kinks swing about its line (inside the band)
ARC_R = (0.45, 1.0)   # px: a strand's radius range (thin where the band is thin)
ARC_BRANCH = 3       # stray arc pixels off the main band (at least this many) get a short forked bolt


def _open_chaikin(pts, iterations=2):
    for _ in range(iterations):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out.append(tuple(a[i] * 0.75 + b[i] * 0.25 for i in range(len(a))))
            out.append(tuple(a[i] * 0.25 + b[i] * 0.75 for i in range(len(a))))
        out.append(pts[-1])
        pts = out
    return pts


def arc(sheet, frame, z=0.28):
    """The electric arc between the pincer tips on one frame of the bottom middle piece (placed at
    column 24, row 28): a braid of thin glowing tube bolts (D126/D173 glow: metallic 1, rough)
    along jagged, smoothed paths from one claw tip to the other. Per column the strands spread
    across the frame's arc pixels (their main run), kinked by a fixed jitter and pulled together
    where the band narrows, so the top view keeps inside the sprite's arc and covers it; stray arc
    pixels off the band get a short tapering fork. No flat plate (D130)."""
    import random
    coll = common.reset_collection(f"clamp_arc_{frame}")
    mats = lib.Mats("nshc77", sheet.colors)
    data = sheet.sprites["newsh-caret-7"]
    pixels = next(f["pixels"] for f in data["frames"] if f["index"] == frame)
    arcpx = {(c, r) for r in range(28) for c in range(24) if 57 <= pixels[r][c] <= 63}
    cols = sorted({c for c, _ in arcpx})
    rng = random.Random(7000 + frame)
    band = {}
    for c in cols:
        rows = sorted(r for cc, r in arcpx if cc == c)
        runs, cur = [], [rows[0]]
        for r in rows[1:]:
            if r <= cur[-1] + 2:   # (a one-pixel gap is a flicker in the bolt, not two bolts)
                cur += list(range(cur[-1] + 1, r + 1))
            else:
                runs.append(cur)
                cur = [r]
        runs.append(cur)
        # the main run: the one with the most bright pixels (the bolt's core)
        main = max(runs, key=lambda run: (sum(pixels[r][c] for r in run if (c, r) in arcpx), len(run)))
        band[c] = (main[0], main[-1] + 1)   # corner rows: top edge, bottom edge
    # smooth the band edges a little along the columns (no 1 px stair steps in the bolts' lines)
    tops = [band[c][0] for c in cols]
    bots = [band[c][1] for c in cols]
    # (never past the column's own pixels: smoothing only pulls the edges in)
    st = [max(tops[i], (tops[max(0, i - 1)] + 2 * tops[i] + tops[min(len(cols) - 1, i + 1)]) / 4) for i in range(len(cols))]
    sb = [min(bots[i], (bots[max(0, i - 1)] + 2 * bots[i] + bots[min(len(cols) - 1, i + 1)]) / 4) for i in range(len(cols))]
    bm = bmesh.new()
    smooth = []
    P = lambda c, r, zz: (sheet.X(24 + c), sheet.Y(28 + r), zz)  # noqa: E731

    def clamp_in(c, r, zz, rad):
        """Keep a smoothed point's tube inside the band of the columns it spans (the corner cuts
        must not carry a strand over an empty pixel where the band steps). A six-sided tube is
        0.87 of its radius wide from above."""
        span = [cc for cc in {int(math.floor(c - rad * 0.3)), int(math.floor(c + rad * 0.3))} if cc in band]
        if not span:
            return c, r, zz, rad
        t0 = max(band[cc][0] for cc in span)
        t1 = min(band[cc][1] for cc in span)
        if t1 - t0 < 2 * rad * 0.9:
            rad = max(ARC_R[0] * 0.8, (t1 - t0) / 2 / 0.9)
        lo, hi = t0 + rad * 0.9, t1 - rad * 0.9
        return c, (min(max(r, lo), hi) if hi > lo else (t0 + t1) / 2), zz, rad

    for k, (f, idx, glow) in enumerate(ARC_STRANDS):
        slot = mats(idx, metallic=1.0, roughness=1.0, emission_strength=glow)
        path = []
        for i, c in enumerate(cols):
            t0, t1 = st[i], sb[i]
            wid = max(0.0, t1 - t0)
            rad = max(ARC_R[0], min(ARC_R[1], wid / (2 * len(ARC_STRANDS)) + 0.3))
            lo, hi = t0 + rad * 0.9, t1 - rad * 0.9
            r = t0 + wid * f + (rng.uniform(-ARC_JAG, ARC_JAG) if 0 < i < len(cols) - 1 else 0.0)
            r = min(max(r, lo), hi) if hi > lo else (t0 + t1) / 2
            zz = z + (0.25 * U if k % 2 else -0.15 * U) * math.sin(i * 1.3 + k)
            path.append((c + 0.5, r, zz, rad))
        path = [(cols[0] - 0.0, path[0][1], path[0][2], path[0][3] * 0.6)] + path + \
               [(cols[-1] + 1.0, path[-1][1], path[-1][2], path[-1][3] * 0.6)]
        path = [clamp_in(c, r, zz, rad) for c, r, zz, rad in _open_chaikin(path, 2)]
        smooth += lib.tube(bm, [(P(c, r, zz), rad * U) for c, r, zz, rad in path], sides=6, mat_index=slot, flat=0.75)
    # forks: stray arc pixels outside the main band (a clump above or below it)
    stray = {(c, r) for c, r in arcpx if not band[c][0] <= r < band[c][1]}
    seen = set()
    fork = mats(60, metallic=1.0, roughness=1.0, emission_strength=1.0)
    for p in sorted(stray):
        if p in seen:
            continue
        comp, stack = [], [p]
        seen.add(p)
        while stack:
            q = stack.pop()
            comp.append(q)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (q[0] + d[0], q[1] + d[1])
                if n in stray and n not in seen:
                    seen.add(n)
                    stack.append(n)
        if len(comp) < ARC_BRANCH:
            continue
        cc = sum(c for c, _ in comp) / len(comp) + 0.5
        rr = sum(r for _, r in comp) / len(comp) + 0.5
        far = max(comp, key=lambda q: abs(q[1] + 0.5 - (band[q[0]][0] + band[q[0]][1]) / 2))
        fc, fr = far[0] + 0.5, far[1] + 0.5
        root_c = min(cols, key=lambda c: abs(c + 0.5 - cc))
        t0, t1 = band[root_c]
        root_r = t0 + 0.6 if fr < t0 else t1 - 0.6
        pts = [(root_c + 0.5, root_r, z, 0.7), (cc + rng.uniform(-0.4, 0.4), rr, z + 0.1 * U, 0.6), (fc, fr, z, 0.35)]
        pts = _open_chaikin(pts, 2)
        smooth += lib.tube(bm, [(P(c, r, zz), rad * U) for c, r, zz, rad in pts], sides=6, mat_index=fork, flat=0.75)
    print(f"arc {frame}: {len(cols)} columns, {len(ARC_STRANDS)} strands, {len(stray)} stray px")
    return lib.to_object(f"clamp_arc_{frame}", bm, mats.list, coll, smooth_faces=smooth)


# --- the merged item: arch, plain wall stretch, clamp stretch ------------------------------------

ARCH = [
    ("newsh3-162", 24, 0, 0), ("newsh3-164", 48, 0, 0), ("newsh3-241", 72, 0, 0),
    ("newsh3-198", 0, 28, 0), ("newsh3-200", 24, 28, 0), ("newsh3-202", 48, 28, 0),
    ("newsh3-279", 72, 28, 0), ("newsh3-281", 96, 28, 0),
]
WALL = [
    ("newsh3-166", 0, 0, 0), ("newsh3-168", 24, 0, 0), ("newsh3-170", 48, 0, 0),
    ("newsh3-204", 0, 28, 0), ("newsh3-206", 24, 28, 0), ("newsh3-208", 48, 28, 0),
]
CLAMP = [
    ("newsh-caret-77", 0, 0, 0), ("newsh-caret-79", 24, 0, 0), ("newsh-caret-81", 48, 0, 0),
    ("newsh-caret-115", 0, 28, 0), ("newsh-caret-7", 24, 28, 0), ("newsh-caret-119", 48, 28, 0),
]
#: Where each group sits in the review glb (units; the arch on top, the two wall stretches below).
OFFSETS = {"arch": (0.0, 0.0), "wall": (-3.4, -5.4), "clamp": (3.4, -5.4)}
#: D175 facet ramp on the sandstone (the sprite's own shade ramp on facets, lit ones its highlights).
RAMP = {"angle": 24.0, "size": 4.5, "sprite": 0.8, "strength": 1.0, "bias": 0.0}
ROCK_MID = 22
ROCK_FINISH = dict(metallic=0.0, roughness=0.88)


def rock_sprite(sheet, keep=lambda v: 16 <= v <= 31):
    """facet_ramp's sprite: the sheet's pixels, only the rock's own (machine pixels left out)."""
    raw = [[v if v >= 0 and keep(v) else -1 for v in row] for row in sheet.pix]
    # a 3x3 median over the rock's own pixels: the sprite's per-pixel dither and speckle go (they
    # made the facets a camouflage of blobs), its broad lit planes, dark cracks and highlights stay
    h, w = sheet.h, sheet.w
    pix = [row[:] for row in raw]
    for r in range(h):
        for c in range(w):
            if raw[r][c] < 0:
                continue
            vals = sorted(raw[rr][cc] for rr in range(max(0, r - 1), min(h, r + 2))
                          for cc in range(max(0, c - 1), min(w, c + 2)) if raw[rr][cc] >= 0)
            pix[r][c] = vals[len(vals) // 2]
    return {"name": "b017", "colors": sheet.colors, "frames": [{"pixels": pix, "width": sheet.w, "height": sheet.h}]}


class SheetGrid:
    """lib_newshd_rock.Grid for a composed sheet: the inner mask (inside the ink ring, D74)."""

    def __init__(self, sheet):
        self.w, self.h = sheet.w, sheet.h
        colors = {int(k): tuple(v) for k, v in sheet.colors.items()}
        self.inner = SM.masks(sheet.pix, colors)["inner"]

    def uv(self, x, y):
        return x * 12 + self.w / 2, self.h / 2 - y * 12


def pal_of(mat):
    m = re.match(r"pal_(\d+)_", mat.name if mat else "")
    return int(m.group(1)) if m else None


def facet_rock(obj, sheet, keep=lambda v: 16 <= v <= 31):
    """The D175 facet ramp over every rock face but the underside (faces of a rock palette index
    facing up or sideways)."""
    me = obj.data
    rock_slots = {k for k, m in enumerate(me.materials) if pal_of(m) is not None and 16 <= pal_of(m) <= 31}
    faces = [p.index for p in me.polygons if p.material_index in rock_slots and p.normal.z > -0.3]
    slot = next((k for k, m in enumerate(me.materials) if pal_of(m) == ROCK_MID), None)
    if slot is None:
        me.materials.append(common.palette_material({"name": "b017", "colors": sheet.colors}, ROCK_MID,
                                                    f"{obj.name}-mid", **ROCK_FINISH))
        slot = len(me.materials) - 1
    spec = {"mid": ROCK_MID, "ramp": RAMP, **ROCK_FINISH}
    R.facet_ramp(rock_sprite(sheet, keep), SheetGrid(sheet), obj, spec, faces=faces, mid=ROCK_MID, slot=slot)


def split_open(obj, layout, coll):
    """common.split_assembly's cut without capping (for the outline shells: a capped shell would
    draw an ink line across the rock at every piece seam)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        out[name] = sh
    return out


def cut_planes(group, sheet):
    """Where the rock carries on past the sheet (another piece or the terrain's leg tiles): (axis,
    coordinate in units, outward sign, keep(x, y) -> bool limiting the plane to its cut)."""
    X, Y = sheet.X, sheet.Y
    if group == "arch":
        return [("y", Y(sheet.h), -1, lambda x, y: True),                    # the legs' bottom edge
                ("x", X(sheet.w), 1, lambda x, y: True),                     # the right leg's right edge
                ("x", X(CUT_COL), 1, lambda x, y: y > Y(CUT_ROWS) - 0.05),    # the crown's right cut
                ("y", Y(CUT_ROWS), 1, lambda x, y: x > X(CUT_COL) - 0.05)]   # newsh3-281's top edge
    return [("x", X(0), -1, lambda x, y: True), ("x", X(sheet.w), 1, lambda x, y: True)]


def trim_caps(shell, planes, reach=2.5 * U, facing=0.35, all_faces=False):
    """Take the outline shell's faces off the cut ends (faces near a cut plane, facing out through
    it): the inverted hull drew them as an ink line across the rock where it carries on.
    `all_faces`: every shell face that near the cut, whatever way it faces (the arch's legs, where
    the rock runs on into the terrain's leg tiles and its rim must not ink the join)."""
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.normal_update()
    gone = []
    for f in bm.faces:
        c = f.calc_center_median()
        for axis, at, sign, keep in planes:
            k = 0 if axis == "x" else 1
            if abs(c[k] - at) < reach and (f.normal[k] * sign > facing or all_faces) and keep(c.x, c.y):
                gone.append(f)
                break
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    bm.to_mesh(shell.data)
    bm.free()
    print(f"trim_caps {shell.name}: {len(gone)} faces off the cut ends")


def layout_of(sheet, placements):
    return [(name, c0 + 12 - sheet.w / 2, r0 + 14 - sheet.h / 2) for name, c0, r0, _ in placements]


def finish(group, obj, sheet, placements, coll):
    """Shell (from a sealed copy, before anything is culled), pieces, facet normals."""
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    shell = common.outline_shell(sealed, coll, voxel=0.03, faces=4000, smooth=8, inside=0.004, islands="outer")
    bpy.data.objects.remove(sealed)
    trim_caps(shell, cut_planes(group, sheet))
    if group == "arch":  # the legs' bottom edge: no ink at all along the join with the terrain
        trim_caps(shell, cut_planes(group, sheet)[:1], reach=1.6 * U, all_faces=True)
    layout = layout_of(sheet, placements)
    pieces = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll)
    for name, _, _ in layout:
        R.set_facet_normals(pieces[name])
    obj.hide_render = shell.hide_render = True
    return layout, pieces, shells


def ink_off(sheet):
    """Leave the sprite's outline ink ring off the rock (D74: the model's edge goes to the inner edge
    of the ring; the game draws its own ink there), measured per piece as the IoU rule does."""
    colors = {int(k): tuple(v) for k, v in sheet.colors.items()}
    h, w = sheet.h, sheet.w
    orig = [row[:] for row in sheet.pix]

    def outside(c, r):
        """Next to the whole object's outside (not just its piece's edge: a crack line running into
        a seam is not the outline, and taking it off would hole the rock)."""
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cc, rr = c + dc, r + dr
            if 0 <= rr < h and 0 <= cc < w and orig[rr][cc] < 0:
                return True
            if not (0 <= cc < w) and not sheet.open_lr and not (sheet.open_cut and sheet.open_cut(cc, rr)):
                return True
            if (rr < 0 and r == 0) or (rr >= h and r == h - 1 and not (sheet.open_cut and sheet.open_cut(cc, rr))):
                return True
        return False

    for name, c0, r0, fi in sheet.placements:
        rows = [row[c0:c0 + 24] for row in sheet.pix[r0:r0 + 28]]
        border = SM.masks(rows, colors)["border"]
        for r in range(28):
            for c in range(24):
                if border[r][c] and outside(c0 + c, r0 + r):
                    sheet.pix[r0 + r][c0 + c] = -1


def wall_height(sheet, mask, edge_mask=None):
    """The stretches' top height zf(c, r, kind) (units): the arch's crown section (core_height)
    measured from the stretch's own north and south edges, a little relief from the sprite's
    brightness, and exactly seam_height at both cut ends so every stretch joins the arch and the
    next stretch without a step. `edge_mask` (default `mask`): the band whose edges the section is
    measured from (the clamp's rock carries on under its machine)."""
    h, w = sheet.h, sheet.w
    mask_e = edge_mask or mask
    span = {}
    for c in range(w):
        rows = [r for r in range(h) if mask_e[r][c]]
        span[c] = (rows[0], rows[-1] + 1) if rows else (0, h)
    north, south = [], []
    # (measured from the smoothed outline and from the outline itself, whichever is nearer: from the
    # smoothed one only, the crumbling foot's notches stood up as a tall cliff)
    for loop in lib.trace_loops(mask_e):
        soft = chaikin(lib.simplify_loop(loop, SOFT_TOL))
        raw = lib.simplify_loop(loop, 0.6)
        for line in (soft, raw):
            for k in range(len(line)):
                a, b = line[k], line[(k + 1) % len(line)]
                mc, mr = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                if min(a[0], b[0]) > w - 0.6 or max(a[0], b[0]) < 0.6:
                    continue  # a cut end
                r0, r1 = span[max(0, min(w - 1, int(mc)))]
                (north if mr < (r0 + r1) / 2 else south).append((a, b))
    north, south = Segs(north), Segs(south)
    lum = [[clamp01((v - 16) / 15) if 16 <= v <= 31 else 0.4 for v in row] for row in sheet.pix]
    lum = lib.blur(lum, mask, 3)
    vals = [lum[r][c] for r in range(h) for c in range(w) if mask[r][c]]
    mean = sum(vals) / max(1, len(vals))

    def zf(c, r, kind):
        dn, ds = north.dist((c, r)), south.dist((c, r))
        lip_r = min(r, SEAM_R1)
        if kind == "outer" and dn <= ds:
            return EDGE * U
        if kind == "outer" and ds < 0.8:
            z = core_height(dn, 0.0, r, lip_r=lip_r)[0]
        else:  # (on the clamp, the rock's edge between the jaws stands as a cliff)
            z, t, u = core_height(dn, ds, r, lip_r=lip_r)
            z += WALL_RELIEF * (lib.bilinear(lum, mask, c, r) - mean) * t * smoothstep(u * 1.5)
        wgt = seam_weight(min(c, w - c))
        z += (seam_height(r) - z) * wgt
        return max(EDGE, z) * U

    return zf


def wall_shell(bm, sheet, mask, slot_of, zf, *, step=1.3, bottom_step=5.0, tol=0.6, seed=1, bottom_slot=0,
               split=1.3, smooth=2):
    """lib_b017.rock_shell for a stretch cut at both ends, with the height from zf(c, r, kind)
    (kind None inside, "outer" on the outline, "open" on a cut end). The outline's long edges are
    split to `split` px (the cut ends were one edge each, so their section was a flat face)."""
    h, w = sheet.h, sheet.w

    def kind_of(c, r):
        return "open" if c < 1e-3 or c > w - 1e-3 else "outer"

    loops = []
    for loop in lib.trace_loops(mask):
        loop = lib.simplify_loop(loop, tol)
        if len(loop) < 3:
            continue
        pts = []
        for k in range(len(loop)):
            a, b = loop[k], loop[(k + 1) % len(loop)]
            m = max(1, round(math.dist(a, b) / split))
            pts += [(a[0] + (b[0] - a[0]) * j / m, a[1] + (b[1] - a[1]) * j / m) for j in range(m)]
        n = len(pts)
        for _ in range(smooth):  # pixel steps out of the outline (not the cut ends)
            pts = [p if kind_of(*p) == "open" or kind_of(*pts[k - 1]) == "open" or kind_of(*pts[(k + 1) % n]) == "open"
                   else ((pts[k - 1][0] + 2 * p[0] + pts[(k + 1) % n][0]) / 4,
                         (pts[k - 1][1] + 2 * p[1] + pts[(k + 1) % n][1]) / 4) for k, p in enumerate(pts)]
        loops.append(pts)

    ring_top, ring_bot = {}, {}

    def surface(step_px, is_top, seed_):
        interior = lib._fill_points(loops, mask, step_px, seed_, margin=step_px * 0.45)
        vout, tris, ids, nb = lib._triangulate(loops, interior)
        ring = ring_top if is_top else ring_bot
        verts = {}
        for k, co in enumerate(vout):
            oid = ids[k]
            on_ring = oid is not None and oid < nb
            if is_top:
                z = zf(co.x, co.y, kind_of(co.x, co.y) if on_ring else None)
            else:
                z = -EDGE * U if on_ring else -BOTTOM * U
            if on_ring:
                if oid not in ring:
                    ring[oid] = bm.verts.new((sheet.X(co.x), sheet.Y(co.y), z))
                verts[k] = ring[oid]
            else:
                verts[k] = bm.verts.new((sheet.X(co.x), sheet.Y(co.y), z))
        faces = []
        for f in tris:
            vs = [verts[j] for j in f]
            if len(set(vs)) < 3:
                continue
            if not is_top:
                vs.reverse()
            try:
                faces.append((bm.faces.new(vs), f, vout))
            except ValueError:
                continue
        return faces

    for face, f, vout in surface(step, True, seed):
        cc = sum(vout[j].x for j in f) / len(f)
        rr = sum(vout[j].y for j in f) / len(f)
        face.material_index = slot_of(sheet.nearest(cc, rr, lambda i: i >= 0), (cc, rr))
    for face, _, _ in surface(bottom_step, False, seed + 7):
        face.material_index = bottom_slot
    i = 0
    for loop in loops:
        n = len(loop)
        for k in range(n):
            a, b = i + k, i + (k + 1) % n
            if a in ring_top and b in ring_top and a in ring_bot and b in ring_bot:
                try:
                    face = bm.faces.new((ring_bot[a], ring_bot[b], ring_top[b], ring_top[a]))
                except ValueError:
                    continue
                mc = (loop[k][0] + loop[(k + 1) % n][0]) / 2
                mr = (loop[k][1] + loop[(k + 1) % n][1]) / 2
                face.material_index = slot_of(sheet.nearest(mc, mr, lambda i_: i_ >= 0), (mc, mr))
        i += n


def wall_rock(bm, sheet, mats, mask, rock_index=lambda v: v, edge_mask=None):
    """A stretch of the wall over `mask`: wall_shell with wall_height's section."""
    dark = mats(19, **ROCK_FINISH)
    rock = {i: mats(i, **ROCK_FINISH) for i in range(16, 32)}

    def slot(v, p):
        return rock.get(rock_index(v) if v is not None else 22, dark)

    rows = {c: [r for r in range(sheet.h) if mask[r][c]] for c in (0, sheet.w - 1)}
    print("wall seam rows", {c: (v[0], v[-1] + 1) for c, v in rows.items() if v}, "SEAM", SEAM_R0, SEAM_R1)
    wall_shell(bm, sheet, mask, slot, wall_height(sheet, mask, edge_mask), bottom_slot=dark)


def make_sheet(placements, open_lr=False, open_cut=None):
    """`open_cut(c, r)`: True for a point past the sheet's edge where the rock carries on (the ink
    there is a tile edge, not the outline: left on, so the cut edge stays straight, no notches)."""
    sheet = lib.Sheet(ROOT, placements)
    sheet.placements = placements
    sheet.open_lr = open_lr
    sheet.open_cut = open_cut
    ink_off(sheet)
    return sheet


def build_group(group):
    if group == "arch":
        # the right leg's right edge and the legs' bottom edge carry on (newsh3-282, the terrain's legs)
        sheet = make_sheet(ARCH, open_cut=lambda c, r: (c >= 120 and r >= CUT_ROWS) or r >= 56)
        obj = build_arch(sheet)
        facet_rock(obj, sheet)
        return sheet, ARCH, obj, {}
    if group == "wall":
        sheet = make_sheet(WALL, True)
        coll = common.reset_collection("wall")
        mats = lib.Mats("nsh3_166", sheet.colors)
        mask = [[v >= 0 for v in row] for row in sheet.pix]
        bm = bmesh.new()
        wall_rock(bm, sheet, mats, mask)
        obj = lib.to_object("wall", bm, mats.list, coll)
        facet_rock(obj, sheet)
        return sheet, WALL, obj, {}
    sheet = make_sheet(CLAMP, True)
    obj = build_clamp(sheet)
    facet_rock(obj, sheet)
    # the arc spans the pincer tips: at their height (the machine sits on the ridge, seat_machine)
    tips = [v.co.z for v in obj.data.vertices if sheet.Y(51) > v.co.y > sheet.Y(54)]
    z = sum(tips) / len(tips) if tips else 0.28
    arcs = {f: arc(sheet, f, z) for f in (7, 9)}
    return sheet, CLAMP, obj, arcs


def build_and_export(groups, argv=()):
    """Build the given groups ("arch", "wall", "clamp") and export their models to the repo
    (public/models/enemies + src/render/spriteModels). Review copies only behind --out / --game."""
    argv = list(argv)
    export, manifest = [], {}
    for group in groups:
        sheet, placements, obj, arcs = build_group(group)
        coll = obj.users_collection[0]
        layout, pieces, shells = finish(group, obj, sheet, placements, coll)
        ox, oy = OFFSETS[group]
        for name, cx, cy in layout:
            objs = [pieces[name], shells[name]]
            models = []  # (model, objects, sprites)
            if group == "clamp" and name == "newsh-caret-7":
                # frames 7 and 9 carry an arc each; frame 117 is the same cut without (newsh-caret-7-f2)
                f2 = pieces[name].copy()
                f2.data = pieces[name].data.copy()
                f2.name = "newsh-caret-7-f2"
                coll.objects.link(f2)
                f2s = shells[name].copy()
                f2s.data = shells[name].data.copy()
                f2s.name = "newsh-caret-7-f2_outline"
                coll.objects.link(f2s)
                sprite = sheet.sprites[name]["sprites"][0]
                for f, a in arcs.items():
                    cut = common.split_assembly(a, [(f"newsh-caret-7-arc-{f}", cx, cy)], coll)[f"newsh-caret-7-arc-{f}"]
                    common.frame_part(cut, [f])
                    objs.append(cut)
                    a.hide_render = True
                models.append((name, objs, [{**sprite, "frames": [7, 9]}]))
                models.append(("newsh-caret-7-f2", [f2, f2s], [{**sprite, "frames": [117]}]))
            else:
                models.append((name, objs, sheet.sprites[name]["sprites"]))
            for model, mobjs, sprites in models:
                common.export_sprite_model(ROOT, mobjs, f"enemies/{model}", sprites)
            if "--game" in argv:  # review copies of the game's per-piece glbs (scratch only)
                gdir = Path(argv[argv.index("--game") + 1])
                for model, mobjs, _ in models:
                    common.export_glb(mobjs, gdir / f"{model}.glb")
            if "--out" in argv:
                for model, mobjs, sprites in models:
                    at = (ox + cx / 12, oy - cy / 12 - (5.0 if model.endswith("-f2") else 0.0), 0)
                    for o in mobjs:
                        o.location = at
                        export.append(o)
                    frames = [f for sp in sprites for f in sp["frames"]]
                    manifest[model] = {"group": group, "frames": frames, "at": list(at[:2])}
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        common.export_glb(export, out)
        (out.parent / (out.stem + "_manifest.json")).write_text(json.dumps(manifest, indent=1))
        print(f"review glb {out}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    groups = argv[argv.index("--only") + 1].split(",") if "--only" in argv else ["arch"]
    build_and_export(groups, argv)


if __name__ == "__main__":
    main()
