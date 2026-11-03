"""Long segmented pipe on a sled (newsh2.shp, assembly of 8 pieces; enemies 18-20): a hard-surface
model led by the sprite's silhouette and its readability from the small tilted game camera.

The sprite (8 x 2x2 ground sprites in a row, 192 x 28 px, sprite.json `assemblyLayout`) is
authoritative for the plan outline, the parts' positions and their colours:
- a light grey bullet nose (newsh2-7) whose tip droops to rows 12-13, riding on a dark sled prow
  whose south edge curves out row by row to row 18;
- six identical segments (newsh2-9): a dark bolt ring (col 0), a narrow red collar (cols 1-3), a
  grey ring (4-7), a bolt ring (8), a red collar (9-11), a broad grey ring (12-16), a red flange
  (17-20, rows 6-18) on a red bracket down to the ground with a see-through hole (row 16), and a
  short grey ring (21-23) that runs on into the next segment; the flange's top (row 6) is 6 px
  wide, so the grey rings swell into a weld-neck hub either side of it (cols 16 and 21);
- the end piece (newsh2-11): a bigger flange (rows 5-19) on a deeper bracket, a ring, a bolt ring, a
  collar and a long grey cylinder with a rounded end.
The dark band under the pipe (rows 15-18) is the sled: a stepped buttress under every grey ring that
slopes from the pipe's south side to the ground at row 19, with a ledge (the sprite's lighter row
17); a low rail at ground level joins them (seen under the collars, rows 15-16) and a hydraulic line
runs along the pipe's south flank (the collars' dark bottom row 13). Under the collars the ground
shows through (rows 14 and 17-18), as in the sprite.

Detail goes where the tilted game camera looks (top, south side, ends): chamfered ring edges with
machined grooves and rivet rows, hex nuts on the bolt rings, banded collars, flanges with a rim
groove on weld-neck hubs, two tie rods across every red coupling, bracket frames, buttress ledges
with bolts, a nose with a seam ring and a tail with a filleted cap whose end face is a machined ring
of bolts round a recessed hub. The underside is just closed.

Built in sprite px (x = assembly column edge 0..192, y = row edge 0..28 with south +, z up) and moved
to Blender at the end (X = (x - 96) / 12, Y = (14 - y) / 12, Z = z / 12; ground at z = 0), so the
assembly's centre (screen 214, -17) is the origin, as in assets/blender/enemies/assembly-newsh2-9.py.
Palette materials pal_<index> (the sprite's own index per part, see MATS). Texture: each exported
piece bakes its own occlusion / edge colour multiplier and roughness-metal map (the ships' bake,
usp_talon.bake_maps) in its place in the pipe with its neighbours around it; no concept projection
(maps.json "bake": "model", D50). Each piece is exported with an outline shell (common.outline_shell,
D51). One middle segment (screen cx 226) is exported as newsh2-9 and serves all six.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-9.py [-- --preview out.png]
[--no-bake] (the preview is the whole pipe; each piece also gets <piece>.png next to it).
"""

import bisect
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = WT = common.repo_root(__file__)
NAME = "assembly-newsh2-9"
PIECES = ["newsh2-7", "newsh2-9", "newsh2-11"]
CX0, CY0 = 214, -17  # screen px of the assembly's centre (its Blender origin)
W, H = 192, 28
SEG0 = [24 + 24 * k for k in range(6)]  # left edges of the six segments
EXPORT_9 = 226  # screen cx of the newsh2-9 copy that is exported (a middle one)
PX = 1 / 12

YC = 11.0  # pipe axis (row edge): the rings cover rows 7-14
ZC = 6.3  # axis height in px: the big end flange (r 6) just clears the ground
R_RING = 4.0
R_BOLT = 3.85
R_COLLAR = 2.35
R_FAT = 3.0
R_FLANGE = 5.0
R_FLANGE_END = 6.0
SIDES = 28

# --- materials: the sprite's palette index per part (median of the part's pixels, the outline ink
# (index 1) and the darkest / brightest fifth left out as shading and sheen) -------------------------
# grey rings 6, nose 9 (the cone's rows 9-12, the dark rim row 8 left out), bolt rings 3, collars 70, flanges 72,
# bracket bars 16 and posts 66, feet 69, sled 2 (the sprite draws it in ink 1; 2 keeps it a dark
# surface, not a hole) with its ledge 3, rail 16, hydraulic line 66.
GREY, NOSE, BOLT, COLLAR, FLANGE, BAR, POST, FOOT, SLED, LEDGE, RAIL, LINE, CAP = range(13)
MATS = {  # slot: (palette index, metallic, roughness, role)
    GREY: (6, 0.28, 0.36, "ring"),
    NOSE: (9, 0.25, 0.26, "nose"),
    BOLT: (3, 0.3, 0.42, "bolt"),
    COLLAR: (70, 0.15, 0.45, "collar"),
    FLANGE: (72, 0.18, 0.36, "flange"),
    BAR: (16, 0.2, 0.6, "bar"),
    POST: (66, 0.2, 0.55, "post"),
    FOOT: (69, 0.2, 0.55, "foot"),
    SLED: (2, 0.3, 0.6, "sled"),
    LEDGE: (3, 0.35, 0.5, "ledge"),
    RAIL: (16, 0.25, 0.6, "rail"),
    LINE: (66, 0.2, 0.45, "line"),
    CAP: (6, 0.3, 0.3, "cap"),
}


def sprite_colours():
    cols = {}
    for n in PIECES:
        cols.update(common.load_sprite(WT, n)["colors"])
    return cols


def make_materials(tag="nsh2b"):
    cols = sprite_colours()
    out = []
    for slot in range(len(MATS)):
        i, met, rough, role = MATS[slot]
        out.append(common.material(f"pal_{i}_{tag}_{role}", common.srgb(*cols[str(i)]), metallic=met, roughness=rough))
    return out


# --- curves --------------------------------------------------------------------------------------

def pchip(xs, ys):
    """Monotone cubic interpolation through (xs, ys): smooth, no overshoot."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


# The nose's plan, fitted to newsh2-7's mask: its north edge (row edge) and the bullet's south edge
# (the sled prow takes the rest down to SLED_S).
NOSE_N = pchip([1.9, 2.6, 4.0, 6.0, 9.0, 13.0, 17.0, 19.5, 24.0], [12.7, 12.05, 11.5, 10.5, 9.5, 8.5, 7.45, 7.0, 7.0])
NOSE_S = pchip([1.9, 2.6, 4.0, 6.0, 9.0, 13.0, 17.0, 19.5, 24.0], [13.3, 13.95, 14.2, 14.4, 14.7, 14.95, 15.0, 15.0, 15.0])
SLED_S = pchip([3.6, 4.0, 6.0, 9.0, 13.0, 17.0, 18.6, 24.0], [14.0, 14.5, 15.5, 16.5, 17.5, 18.5, 19.0, 19.0])


# --- mesh building (px space) -----------------------------------------------------------------

def P(x, y, z):
    return Vector(((x - W / 2) * PX, (H / 2 - y) * PX, z * PX))


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, x, y, z):
        return self.bm.verts.new(P(x, y, z))

    def f(self, verts, mat, smooth=True):
        try:
            face = self.bm.faces.new(verts)
        except ValueError:
            return None
        face.material_index = mat
        face.smooth = smooth
        return face


def lathe(M, prof, mats, sides=SIDES, yc=YC, zc=ZC, centre=None, cap0=True, cap1=True, phase=0.5):
    """Revolve a profile [(x, r)] about the pipe axis (row yc, height zc; centre(x) -> (yc, zc) bends
    it). mats is one slot or one per profile segment. r = 0 closes to a point."""
    rings = []
    for x, r in prof:
        cy, cz = centre(x) if centre else (yc, zc)
        if r <= 1e-6:
            rings.append([M.v(x, cy, cz)])
            continue
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + phase) / sides
            ring.append(M.v(x, cy - r * math.sin(a), cz + r * math.cos(a)))
        rings.append(ring)
    if isinstance(mats, int):
        mats = [mats] * (len(prof) - 1)
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                M.f((r0[0], r1[j], r1[k]), mats[i])
            elif len(r1) == 1:
                M.f((r0[k], r0[j], r1[0]), mats[i])
            else:
                M.f((r0[k], r0[j], r1[j], r1[k]), mats[i])
    if cap0 and len(rings[0]) > 1:
        M.f(list(reversed(rings[0])), mats[0], smooth=False)
    if cap1 and len(rings[-1]) > 1:
        M.f(rings[-1], mats[-1], smooth=False)


def prism(M, x0, x1, poly, mat, ch=0.0, mats=None):
    """Extrude a (y, z) polygon from x0 to x1; ch chamfers both ends (the section shrinks toward
    its centroid by ch px). mats: optional slot per polygon edge."""
    cy = sum(p[0] for p in poly) / len(poly)
    cz = sum(p[1] for p in poly) / len(poly)

    def shrink(p):
        dy, dz = p[0] - cy, p[1] - cz
        d = math.hypot(dy, dz) or 1.0
        s = max(0.0, (d - ch) / d)
        return (cy + dy * s, cz + dz * s)
    sections = [(x0, [shrink(p) for p in poly]), (x0 + ch, poly), (x1 - ch, poly), (x1, [shrink(p) for p in poly])] \
        if ch > 0 else [(x0, poly), (x1, poly)]
    rings = [[M.v(x, y, z) for y, z in sec] for x, sec in sections]
    n = len(poly)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            M.f((r0[k], r0[j], r1[j], r1[k]), mats[k] if mats else mat, smooth=False)
    M.f(list(reversed(rings[0])), mat, smooth=False)
    M.f(rings[-1], mat, smooth=False)


def box(M, x0, x1, y0, y1, z0, z1, mat, ch=0.0):
    prism(M, x0, x1, [(y0, z0), (y1, z0), (y1, z1), (y0, z1)], mat, ch=ch)


def stud(M, base, normal, r, h, mat, sides=6, dome=True):
    """A rivet head (dome) or hex nut (flat, chamfered) standing on a surface, base point and normal
    in px space."""
    n = Vector(normal).normalized()
    t = n.cross(Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))).normalized()
    b = n.cross(t)
    base = Vector(base) - n * 0.15  # sunk in a little so it never floats
    h += 0.15

    def ring(rr, hh):
        return [M.v(*(base + n * hh + (t * math.cos(2 * math.pi * k / sides) + b * math.sin(2 * math.pi * k / sides)) * rr))
                for k in range(sides)]
    if dome:
        levels = [ring(r, 0.0), ring(r * 0.8, h * 0.62)]  # a rivet head: 0.2 px, two rings are plenty
    else:
        levels = [ring(r, 0.0), ring(r, h * 0.75), ring(r * 0.78, h)]
    for r0, r1 in zip(levels, levels[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            M.f((r0[k], r0[j], r1[j], r1[k]), mat, smooth=dome)
    M.f(list(reversed(levels[0])), mat, smooth=False)
    if dome:
        apex = M.v(*(base + n * h))
        for k in range(sides):
            M.f((levels[-1][k], levels[-1][(k + 1) % sides], apex), mat)
    else:
        M.f(levels[-1], mat, smooth=False)


def radial(angle, r, yc=YC, zc=ZC):
    """Point at `angle` (0 = top, + toward north... see below) on a circle of radius r round the
    axis, and its outward direction; angle 0 is straight up, +90 points south (+y)."""
    a = math.radians(angle)
    d = Vector((0.0, math.sin(a), math.cos(a)))
    return Vector((0.0, yc, zc)) + d * r, d


# --- parts -------------------------------------------------------------------------------------

def grey_ring(M, x0, x1, rivets=True, ch0=0.45, ch1=0.45, mat=GREY):
    """A machined grey ring: chamfered ends, a shallow groove 0.8 px in from each end, rivets in
    the bands between groove and end (only where the game camera sees them: top and flanks)."""
    g = 0.22  # groove depth
    gw = 0.28
    prof = [(x0, R_RING - ch0), (x0 + ch0, R_RING)]
    mats = [mat]
    if x1 - x0 >= 3.0:
        a, b = x0 + 0.85, x1 - 0.85
        prof += [(a, R_RING), (a, R_RING - g), (a + gw, R_RING - g), (a + gw, R_RING),
                 (b - gw, R_RING), (b - gw, R_RING - g), (b, R_RING - g), (b, R_RING)]
        mats += [mat] * 8  # machined grooves: the same steel, the bake darkens them
    prof += [(x1 - ch1, R_RING), (x1, R_RING - ch1)]
    mats += [mat, mat]
    lathe(M, prof, mats)
    if rivets and x1 - x0 >= 3.0:
        for xr in (x0 + 0.5 + ch0 * 0.3, x1 - 0.5 - ch1 * 0.3):
            for ang in range(-50, 111, 40):
                p, d = radial(ang, R_RING)
                stud(M, (xr, p.y, p.z), d, 0.2, 0.16, mat)


def bolt_ring(M, x0, x1):
    """A dark bolt ring between parts (the sprite's dark columns) with hex nuts round the top."""
    lathe(M, [(x0, R_BOLT - 0.3), (x0 + 0.15, R_BOLT), (x1 - 0.15, R_BOLT), (x1, R_BOLT - 0.3)], BOLT)
    for ang in range(-35, 106, 35):
        p, d = radial(ang, R_BOLT)
        stud(M, ((x0 + x1) / 2, p.y, p.z), d, 0.3, 0.22, BOLT, dome=False)


def collar(M, x0, x1, band=R_COLLAR):
    """A red coupling: a rod with two raised bands. The thin one (r 2.35, the segment's first,
    rows 9-12; the hydraulic line on its south flank gives the sprite's dark row 13) or the fat
    sleeve (r 3.0, rows 8-13: the second collar's outline reaches row 8)."""
    rod = band - 0.3
    w = (x1 - x0)
    a, b = x0 + w * 0.18, x1 - w * 0.18
    lathe(M, [(x0 - 0.2, rod), (a, rod), (a, band - 0.12), (a + 0.12, band), (a + 0.55, band), (a + 0.67, band - 0.12),
              (a + 0.67, rod), (b - 0.67, rod), (b - 0.67, band - 0.12), (b - 0.55, band), (b - 0.12, band),
              (b, band - 0.12), (b, rod), (x1 + 0.2, rod)], COLLAR, sides=20)
    # Two grey tie rods across the coupling, bolt ring to bolt ring, on its upper flanks (at 45
    # degrees they stay inside the sprite's collar rows).
    rr = band + 0.4
    for s in (-1, 1):
        t = math.radians(45 * s)
        lathe(M, [(x0 - 0.3, 0.3), (x1 + 0.3, 0.3)], GREY, sides=6, yc=YC + rr * math.sin(t), zc=ZC + rr * math.cos(t))


def hydraulic_line(M, x0, x1):
    """A thin line along the south flank, through the rings (hidden there), seen at the collars."""
    lathe(M, [(x0, 0.48), (x1, 0.48)], LINE, sides=8, yc=13.45, zc=ZC - 1.05)


def flange(M, x0, x1, r, foot_y):
    """A broad red flange band with chamfered sides and a rim groove, bolts on its faces, on a
    sloped bracket frame down to a foot on the ground (plan: a post at its west column, bars at
    rows foot_y-4 / foot_y-2, a hole between, the foot at foot_y-1 .. foot_y+0.6)."""
    m = (x0 + x1) / 2
    # The sprite's flange top (rows 5-6) is a column wider each side than the flange band: the grey
    # rings swell into a tapered weld-neck hub (1 px long) on both sides, its crown reaching the
    # flange's tips; the red band stands on it with chamfered edges and a rim groove.
    hub = [(-1.0, -0.7), (-0.7, -0.48), (-0.35, -0.38), (0.0, -0.34)]  # (dx from the face, r offset)
    prof = [(x0 - 1.05, R_RING - 0.1)] + [(x0 + dx, r + dr) for dx, dr in hub]
    mats = [GREY] * 4
    prof += [(x0 + 0.34, r), (m - 0.22, r), (m - 0.22, r - 0.2), (m + 0.22, r - 0.2), (m + 0.22, r), (x1 - 0.34, r)]
    mats += [FLANGE] * 7
    prof += [(x1 - dx, r + dr) for dx, dr in reversed(hub)] + [(x1 + 1.05, R_RING - 0.1)]
    mats += [GREY] * 4
    lathe(M, prof, mats, sides=32)
    # Sloped bracket plate: z on the plane through (y_top, z_top) and (y_bot, z_bot).
    y_top = YC + math.sqrt(max(r * r - (r - 1.0) ** 2, 0)) * 0 + (r - 1.0)  # under the flange's south flank
    z_top = ZC - math.sqrt(max(r * r - (y_top - YC) ** 2, 0.0)) + 0.4
    y_bot, z_bot = foot_y - 0.6, 0.55
    th = 0.7

    def zs(y):
        return z_top + (z_bot - z_top) * (y - y_top) / (y_bot - y_top)

    def plate(xa, xb, ya, yb, mat):
        prism(M, xa, xb, [(ya, zs(ya) - th), (yb, zs(yb) - th), (yb, zs(yb)), (ya, zs(ya))], mat, ch=0.12)
    hole0, hole1 = foot_y - 3.0, foot_y - 2.0  # the see-through row
    plate(x0, x0 + 1.0, y_top - 1.0, y_bot, POST)  # west post
    plate(x0 + 0.9, x1 + 0.6, y_top - 1.0, hole0, BAR)  # top bar (mostly under the flange)
    plate(x0 + 0.9, x1 + 0.6, hole1, y_bot, BAR)  # lower bar
    plate(x1, x1 + 0.6, y_top - 1.0, y_bot, POST)  # east post (inside the next buttress)
    # Foot pad on the ground with a chamfered top and two bolts.
    box(M, x0 - 1.0, x1 + 1.0, foot_y - 1.0, foot_y + 0.65, 0.0, 0.75, FOOT, ch=0.2)
    for xb in (x0 + 0.3, x1 - 0.3):
        stud(M, (xb, foot_y - 0.2, 0.75), (0, 0, 1), 0.22, 0.15, BOLT, dome=False)


def buttress(M, x0, x1, ledge=True):
    """The sled under a grey ring: hidden under the pipe from above, its south face slopes from the
    pipe's flank to the ground at row 19 with a ledge across it (the sprite's row 17)."""
    sec = [(8.6, 0.0), (19.0, 0.0), (19.0, 0.35), (17.75, 1.75), (17.75, 2.15), (16.9, 2.15),
           (15.0, ZC - 2.05), (14.4, ZC - 0.6), (8.6, ZC - 0.6)]
    mats = [SLED, SLED, SLED, LEDGE, LEDGE, SLED, SLED, SLED, SLED]
    prism(M, x0, x1, sec, SLED, ch=0.25, mats=mats)
    if ledge and x1 - x0 >= 3.5:
        for xb in (x0 + 0.9, x1 - 0.9):
            stud(M, (xb, 17.3, 2.15), (0, 0, 1), 0.22, 0.14, BOLT, dome=False)


def rail(M, x0, x1, y0=15.45, y1=16.85):
    """The low rail at ground level that ties the buttresses together (seen under the collars: rows
    15-16 under the thin collar, row 16 under the fat one)."""
    prism(M, x0, x1, [(y0, 0.0), (y1, 0.0), (y1, 0.9), (y1 - 0.3, 1.25), (y0 + 0.3, 1.25), (y0, 0.9)], RAIL)


def segment(M, a):
    """One newsh2-9 segment from assembly column a (its 24 columns)."""
    bolt_ring(M, a, a + 1)
    collar(M, a + 1, a + 4)
    grey_ring(M, a + 4, a + 8)
    bolt_ring(M, a + 8, a + 9)
    collar(M, a + 9, a + 12, R_FAT)
    grey_ring(M, a + 12, a + 16.05, ch1=0.0)  # runs into the flange's hub
    flange(M, a + 17, a + 21, R_FLANGE, 19.0)
    if a + 24 < 168:
        grey_ring(M, a + 21.95, a + 24, ch0=0.0, ch1=0.0)
    buttress(M, a + 4, a + 9)
    buttress(M, a + 12, a + 17)
    buttress(M, a + 21, a + 25 if a + 24 < 168 else a + 26)
    rail(M, a - 0.3, a + 4.3)
    rail(M, a + 8.7, a + 12.3, 15.95)
    hydraulic_line(M, a - 0.2, a + 24.2)


def nose(M):
    """newsh2-7: the bullet nose (its tip droops toward rows 12-13 as in the sprite) with a seam
    ring near its base, on a sled prow that curves out to row 18."""
    def centre(x):
        n, s = NOSE_N(x), NOSE_S(x)
        yc = (n + s) / 2
        return yc, ZC - (yc - YC) * 0.9
    xs = [1.9, 2.15, 2.6, 3.2, 4.0, 5.0, 6.0, 7.5, 9.0, 11.0, 13.0, 15.0, 17.0, 18.3, 19.5, 20.5, 20.5, 20.8, 20.8, 24.05]
    prof = []
    for i, x in enumerate(xs):
        r = (NOSE_S(x) - NOSE_N(x)) / 2
        if x == 1.9:
            r = 0.0
        prof.append((x, r))
    # a seam groove at x 20.5-20.8
    prof[16] = (20.5, R_RING - 0.25)
    prof[17] = (20.8, R_RING - 0.25)
    mats = [NOSE] * (len(prof) - 1)
    lathe(M, prof, mats, centre=centre, sides=SIDES)
    # The sled prow: a long buttress whose south edge follows SLED_S, sloping to the ground.
    xs = [3.6, 4.5, 5.5, 6.5, 8.0, 9.5, 11.5, 13.5, 15.5, 17.5, 19.0, 21.3]
    rings = []
    for x in xs:
        yc, zc = centre(x)
        r = (NOSE_S(x) - NOSE_N(x)) / 2
        s = SLED_S(x)
        top = zc - 0.6 * (r / R_RING)
        ledge_y = s - 1.25
        k = min(1.0, (x - 3.6) / 4.0)
        sec = [(yc - r * 0.55, 0.0), (s, 0.0), (s, 0.05 + 0.3 * k), (s - 0.35, 0.05 + 0.65 * k),
               (yc + r * 0.95, max(top - 1.2 * (r / R_RING), 0.6)), (yc + r * 0.5, top), (yc - r * 0.55, top)]
        rings.append([M.v(x, y, z) for y, z in sec])
    n = len(rings[0])
    smats = [SLED, SLED, LEDGE, SLED, SLED, SLED, SLED]
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            M.f((r0[k], r0[j], r1[j], r1[k]), smats[k], smooth=True)
    M.f(list(reversed(rings[0])), SLED, smooth=False)
    M.f(rings[-1], SLED, smooth=False)
    # The first buttress under the nose's base joins the prow to the first segment.
    buttress(M, 20.6, 25.0)


def tail(M):
    """newsh2-11 (assembly columns 168-191): the last ring's end, the big flange on its deep bracket,
    a ring, a bolt ring, a collar, a bolt ring and the long cylinder with a filleted end cap."""
    a = 168
    grey_ring(M, a - 2.05, a + 1.05, ch0=0.0, ch1=0.0)  # hub to hub
    flange(M, a + 2, a + 6, R_FLANGE_END, 20.0)
    grey_ring(M, a + 6.95, a + 10, ch0=0.0)
    bolt_ring(M, a + 10, a + 11)
    collar(M, a + 11, a + 14, R_FAT)
    bolt_ring(M, a + 14, a + 15)
    # The long cylinder: a raised band near its root, a groove, and a filleted cap with a boss.
    x0, x1 = a + 15, a + 24
    prof = [(x0, R_RING - 0.3), (x0 + 0.3, R_RING), (x0 + 1.6, R_RING), (x0 + 1.6, R_RING - 0.2), (x0 + 1.9, R_RING - 0.2),
            (x0 + 1.9, R_RING), (x1 - 2.4, R_RING), (x1 - 2.4, R_RING - 0.2), (x1 - 2.1, R_RING - 0.2), (x1 - 2.1, R_RING)]
    mats = [GREY] * 9
    fil = 1.3
    for k in range(1, 7):
        t = k / 6 * math.pi / 2
        prof.append((x1 - fil + fil * math.sin(t), R_RING - fil + fil * math.cos(t)))
        mats.append(CAP if k > 1 else GREY)
    # The end face (inside the fillet, r < 2.7): a machined ring of bolts round a recessed hub.
    prof += [(x1, 1.55), (x1 - 0.3, 1.45), (x1 - 0.3, 0.75), (x1 - 0.12, 0.62), (x1 - 0.12, 0.0)]
    mats += [CAP, BOLT, BOLT, BOLT, BOLT]
    lathe(M, prof, mats)
    for k in range(8):
        t = 2 * math.pi * (k + 0.5) / 8
        stud(M, (x1, YC - 2.1 * math.sin(t), ZC + 2.1 * math.cos(t)), (1, 0, 0), 0.22, 0.12, BOLT, dome=False)
    for xr in (x0 + 0.85, x1 - 3.0):
        for ang in range(-50, 111, 40):
            p, d = radial(ang, R_RING)
            stud(M, (xr, p.y, p.z), d, 0.2, 0.16, GREY)
    buttress(M, a + 6, a + 11)
    buttress(M, a + 14, a + 23.85)
    rail(M, a + 10.7, a + 14.3, 15.95)
    hydraulic_line(M, a - 0.2, a + 15.5)


def build(coll, mats):
    M = Mesh()
    nose(M)
    for a in SEG0:
        segment(M, a)
    tail(M)
    bm = M.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    return obj


def finish_normals(obj, angle=35.0):
    me = obj.data
    me.set_sharp_from_angle(angle=math.radians(angle))


# --- cull / bake (from usp_talon.py, parameterised) --------------------------------------------

def cull_hidden(obj, grid=4, ndirs=40, others=()):
    """Delete faces no ray from outside can reach (insides of parts pushed into each other)."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    eps = 1.5e-4
    dead = []
    for f in bm.faces:
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    u, v = (i + 0.5) / grid, (j + 0.5) / grid
                    pts.append(vs[0].lerp(vs[1], u).lerp(vs[3].lerp(vs[2], u), v))
        else:
            for vco in vs[:12]:
                for t in (0.4, 0.9):
                    pts.append(c.lerp(vco, t))
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * eps
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    return len(dead)


def bake_maps(obj, tag, size=1024, samples=64):
    """Smart-UV the piece and bake an occlusion / edge colour multiplier and a roughness-metal map
    (usp_talon.bake_maps); wire them into its palette materials (Base Color = map x palette)."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        if o is not None:
            o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.14
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.5, math_("MULTIPLY", occl, 0.6)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(v, comb.inputs[k])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
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
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.pack()

    for m in mats:
        nt = m.node_tree
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


def layout():
    data = common.load_sprite(WT, "newsh2-9")
    lay = data["assemblyLayout"]
    if isinstance(lay, str):
        import ast
        lay = ast.literal_eval(lay)
    return lay


def build_pieces(bake=True):
    """Build the pipe, cut it into its 8 pieces (named <model>@<cx>, placed as in the game), and
    cull and bake the three exported ones with every other piece around them (so the joints shade
    alike). Returns (pieces, exported, coll)."""
    for o in list(bpy.data.objects):  # factory startup's cube, light and camera
        if o.type in ("MESH", "LIGHT", "CAMERA") and NAME not in [c.name for c in o.users_collection]:
            bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    mats = make_materials()
    obj = build(coll, mats)
    lay = layout()
    pieces = common.split_assembly(obj, [(f"{e['model']}@{e['cx']}", e["cx"] - CX0, e["cy"] - CY0) for e in lay])
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()
    for e in lay:
        p = pieces[f"{e['model']}@{e['cx']}"]
        p.location = ((e["cx"] - CX0) * PX, -(e["cy"] - CY0) * PX, 0.0)
        finish_normals(p)
    chosen = {"newsh2-7": "newsh2-7@130", "newsh2-9": f"newsh2-9@{EXPORT_9}", "newsh2-11": "newsh2-11@298"}
    exported = {}
    for name, key in chosen.items():
        p = pieces[key]
        # Each exported piece gets its own copies of the palette materials (its own baked maps).
        tag = name.replace("-", "_")
        for i, m in enumerate(list(p.data.materials)):
            c = m.copy()
            c.name = m.name.replace("_nsh2b_", f"_{tag}_")
            p.data.materials[i] = c
        exported[name] = p
    for name, p in exported.items():
        n = cull_hidden(p)
        tris = sum(len(f.vertices) - 2 for f in p.data.polygons)
        print(f"{name}: culled {n} hidden faces; {len(p.data.polygons)} faces, {tris} triangles")
    if bake:
        for name, p in exported.items():
            bake_maps(p, name.replace("-", "_"))
    return pieces, exported, coll


def export_pieces(exported, coll, bake=True):
    """Export each piece at its own origin with its outline shell, through the sprite-model
    contract (public/models/enemies/<piece>.glb and its spriteModels entry, every sprite frame)."""
    for name in PIECES:
        p = exported[name]
        loc = p.location.copy()
        p.location = (0, 0, 0)
        bpy.context.view_layer.update()
        shell = common.outline_shell(p, coll, faces=1200)
        shell.name = shell.data.name = f"{name}_outline"
        print(f"{name}: shell {len(shell.data.polygons)} faces")
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [p, shell], f"enemies/{name}", data["sprites"],
                                   image_format="WEBP" if bake else "AUTO")
        bpy.data.objects.remove(shell, do_unlink=True)
        p.location = loc


def preview(pieces, exported, out):
    """The whole pipe beside the sprite (out), and each exported piece beside its sprite."""
    import tempfile
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import lib_b129 as lib
    lay = layout()
    for e in lay:
        o = pieces[f"{e['model']}@{e['cx']}"]
        if e["model"] == "newsh2-9" and o is not exported["newsh2-9"]:
            o.data = exported["newsh2-9"].data  # the exported segment's mesh, as the game repeats it
    objs = [pieces[f"{e['model']}@{e['cx']}"] for e in lay]
    tiles = [(e["model"], e["cx"] - CX0 + W // 2 - 12, e["cy"] - CY0 + H // 2 - 14) for e in lay]
    ref, size = lib.composite_png(ROOT, tiles, W, H, Path(tempfile.mkdtemp()) / "assembly.png")
    common.render_preview(objs, str(out), ref, size=size, view_px=900)
    for name in PIECES:
        p = exported[name]
        loc = p.location.copy()
        p.location = (0, 0, 0)
        data = common.load_sprite(ROOT, name)
        img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
        common.render_preview([p], str(out.parent / f"{name}.png"), img, size=2)
        p.location = loc


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bake = "--no-bake" not in argv
    pieces, exported, coll = build_pieces(bake=bake)
    export_pieces(exported, coll, bake=bake)
    if "--preview" in argv:
        preview(pieces, exported, Path(argv[argv.index("--preview") + 1]))
    if "--blend" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=argv[argv.index("--blend") + 1])


if __name__ == "__main__":
    main()
