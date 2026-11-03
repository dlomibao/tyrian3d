"""Golden horned arm (newsh4.shp, an assembly of 7 pieces, enemy types 73-79): a hard-surface
model led by the silhouette and its read from the tilted game camera (D50-D53 style), with A's
telescoping collars, elbow pin bosses, hydraulic channel and drum seam grafted on.

The sprite is authoritative (D52): the 168x28 px outline (assembly sprite rows/columns), the
steel clamps, the grille port and the two sensor lenses where the sprite draws them, and each
part's palette index = the median of its sprite pixels without the darkest shading (16-18) and the
brightest sheen (29-31).

Reading of the sprite (columns are assembly px, 0 = left edge of newsh4-231; rows 0 = top):
- A horn (cols 2-113) that tapers from a curled point at the bottom left (col 2, row 25) up and
  along the top of the sprite; a round tube (gradient shading) of telescoping brass plating, each
  plate a little fuller at its root end so the joints step (grooves at cols 9.6, 13.4, 25.5, 46.5,
  64.2, 80.3, 89.2), raised collars at the bright columns 57, 86.6, 94.2 and 104.3.
- A lit ledge along its lower (south) flank from col 46 into the knuckle: the bright row 12.
- Steel saddle clamps: A cols 39-45 rows 7-12, B cols 58-63.5 rows 5-9, C cols 80.6-85.5 rows
  2-7 (a blue-grey slit window at col 81 rows 3-5), D cols 107.6-112.4 rows 1-5.6 (a lens at cols
  108.5-111.5 rows 2.7-4.8).
- A dark grille port in the south flank: cols 95.8-99.6, rows 8-12.6.
- The knuckle (cols 113-133): a round elbow fairing / ball, its lower lobe hanging to row 19.5.
- A ribbed neck (cols 131-136, rows 3-16) and the gripper drum (cols 135-168, rows 1-21, a
  10.5 px cylinder on row 11.5) with a shoulder cone, a flange ring, lengthwise armour plates
  (seams at the sprite's dark rows 13 and 18.5), an end ring and an end cap; a hinge bracket over
  the shoulder (the lit cols 138-141 rows 6-9) and a claw strut along the lit diagonal
  (134, 16) -> (139.5, 21.3).

Built in sprite px with the Talon toolkit (usp_talon.py: Part, hull, cbox, cull_hidden, join,
bake_maps): x = assembly row, y = assembly column (the loft axis), z up; moved to Blender at the
end: X = (col - 84) / 12, Y = (14 - row) / 12, Z = z / 12 (origin = the assembly centre, the
centre of newsh4-267, as the current script). Then cut into the seven pieces with
common.split_assembly, each with its piece of the outline shell (D51), and exported to
public/models/enemies/<piece>.glb with its src/render/spriteModels entry. The colour map is baked
occlusion and edge wear only; maps.json says "bake": "model", so no concept projection (PR #84).

  Blender --background --factory-startup --python assembly-newsh4-231.py -- [--no-bake] [--preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (the Talon's hard-surface toolkit, D50)
from usp_talon import Part, cbox, pchip  # noqa: E402

NAME = "assembly-newsh4-231"
REPO = common.repo_root(__file__)
PIECES = ["newsh4-231", "newsh4-233", "newsh4-235", "newsh4-267", "newsh4-269", "newsh4-271", "newsh4-273"]
W, H = 168, 28
CX0, CY0 = 170, 15
PX = 1 / 12

# Material slots and their palette index (median of the region's sprite pixels, 16-18 and 29-31
# left out; measured by measure_B.py's region table).
(HORN, ROOT, BAND, KNUCKLE, NECK, DRUM_UP, DRUM_LO, RING, CORE, DEEP, LEDGE, ST_A, ST_B, ST_C, ST_D,
 PORT, SLAT, LENS, BRACKET, STRUT, TIP) = range(21)
PAL_OF = {HORN: 20, ROOT: 22, BAND: 22, KNUCKLE: 21, NECK: 21, DRUM_UP: 23, DRUM_LO: 21, RING: 21,
          CORE: 18, DEEP: 16, LEDGE: 23, ST_A: 5, ST_B: 4, ST_C: 6, ST_D: 8, PORT: 3, SLAT: 6, LENS: 106,
          BRACKET: 23, STRUT: 24, TIP: 20}
GLASS = (LENS,)
TEXTURED = tuple(i for i in PAL_OF if i not in GLASS)
METAL = 0.3


def materials(sprite, suffix=""):
    """The arm's palette materials in slot order; `suffix` makes a fresh set (one per piece, so
    each piece's baked maps wire into its own materials)."""
    def pal(slot, tag, metallic, roughness):
        return common.palette_material(sprite, PAL_OF[slot], f"arm_{tag}{suffix}", metallic=metallic * METAL,
                                       roughness=roughness)
    return [
        pal(HORN, "horn", 0.6, 0.38),
        pal(ROOT, "root", 0.6, 0.36),
        pal(BAND, "band", 0.7, 0.3),
        pal(KNUCKLE, "knuckle", 0.65, 0.32),
        pal(NECK, "neck", 0.55, 0.42),
        pal(DRUM_UP, "drum_plate", 0.6, 0.36),
        pal(DRUM_LO, "drum_low", 0.55, 0.42),
        pal(RING, "ring", 0.65, 0.34),
        pal(CORE, "core", 0.4, 0.55),
        pal(DEEP, "recess", 0.2, 0.8),
        pal(LEDGE, "ledge", 0.65, 0.32),
        pal(ST_A, "clamp_a", 1.2, 0.36),
        pal(ST_B, "clamp_b", 1.2, 0.36),
        pal(ST_C, "clamp_c", 1.2, 0.36),
        pal(ST_D, "clamp_d", 1.2, 0.34),
        pal(PORT, "port", 0.8, 0.55),
        pal(SLAT, "slat", 1.2, 0.36),
        common.palette_material(sprite, 106, f"arm_lens{suffix}", metallic=0.0, roughness=0.06),
        pal(BRACKET, "bracket", 0.6, 0.36),
        pal(STRUT, "strut", 0.65, 0.32),
        pal(TIP, "tip", 0.65, 0.34),
    ]


def hull(part, points, mat, merge_angle=1.0):
    """The convex hull of points (a chamfered block or a curved saddle), coplanar triangles merged,
    its normals from the hull itself (a centroid hint flips faces of thin curved plates)."""
    tmp = bmesh.new()
    vs = [tmp.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(tmp, input=vs, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(tmp, geom=junk, context="VERTS")
    bmesh.ops.remove_doubles(tmp, verts=tmp.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
    bmesh.ops.dissolve_limit(tmp, angle_limit=math.radians(merge_angle), verts=tmp.verts[:], edges=tmp.edges[:])
    vmap = {v: part.v(v.co.copy()) for v in tmp.verts}
    for f in tmp.faces:
        face = part.f([vmap[v] for v in f.verts], mat, out=tuple(f.normal))
    tmp.free()


# --- the sprite --------------------------------------------------------------------------------

def load():
    grid = [[-1] * W for _ in range(H)]
    sprites, colors = {}, {}
    root = REPO
    for i, name in enumerate(PIECES):
        data = common.load_sprite(root, name)
        sprites[name] = data
        colors.update(data["colors"])
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                grid[r][24 * i + c] = v
    merged = dict(sprites[PIECES[0]])
    merged["colors"] = colors
    merged["name"] = NAME
    return grid, sprites, merged


def col_edges(grid, c):
    rows = [r for r in range(H) if grid[r][c] != -1]
    return min(rows), max(rows) + 1


# --- sections ----------------------------------------------------------------------------------

def superellipse(n, p):
    """Unit loop (u across = +row, v up), starting at the top and running toward +u (south)."""
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n
        s, c = math.sin(t), math.cos(t)
        pts.append((math.copysign(abs(s) ** (2 / p), s), math.copysign(abs(c) ** (2 / p), c)))
    return pts


HORN_UNIT = superellipse(24, 2.25)
BALL_UNIT = superellipse(24, 2.0)
DRUM_UNIT = superellipse(32, 2.0)


def ring_loft(P, rings, unit, cap0=True, cap1=True, cap_mats=None):
    """Tube through rings [(col, centre row, centre z, half width, half height, mat to next ring)].
    A ring of zero size is a point. Two rings at the same column make a step."""
    built = []
    for c, m, zc, w, h, mat in rings:
        if w <= 1e-6:
            built.append(([P.v((m, c, zc))], (m, c, zc), c, 0.0, mat))
        else:
            built.append(([P.v((m + w * u, c, zc + h * v)) for u, v in unit], (m, c, zc), c, w, mat))
    for (r0, c0, y0, w0, mat), (r1, c1, y1, w1, _) in zip(built, built[1:]):
        n = max(len(r0), len(r1))
        for a in range(n):
            b = (a + 1) % n
            if len(r0) == 1:
                P.f((r0[0], r1[b], r1[a]), mat, away=c1)
            elif len(r1) == 1:
                P.f((r0[a], r0[b], r1[0]), mat, away=c0)
            elif abs(y1 - y0) < 1e-6:
                P.f((r0[a], r0[b], r1[b], r1[a]), mat, out=(0, 1 if w1 < w0 else -1, 0))
            else:
                P.f((r0[a], r0[b], r1[b], r1[a]), mat, away=c0)
    if cap0 and len(built[0][0]) > 1:
        P.f(built[0][0], (cap_mats or (built[0][4], None))[0], out=(0, -1, 0))
    if cap1 and len(built[-1][0]) > 1:
        P.f(built[-1][0], (cap_mats or (None, built[-2][4]))[1], out=(0, 1, 0))


def surface_pt(m, zc, w, h, unit_angle_deg, off, p=2.25):
    """A point on a superellipse section at angle (0 = top, +90 = south), pushed `off` px out."""
    t = math.radians(unit_angle_deg)
    s, c = math.sin(t), math.cos(t)
    u, v = math.copysign(abs(s) ** (2 / p), s), math.copysign(abs(c) ** (2 / p), c)
    # outward normal of the superellipse (approx.: gradient)
    nx = (abs(u) ** (p - 1)) * math.copysign(1, u) / max(w, 1e-6)
    nz = (abs(v) ** (p - 1)) * math.copysign(1, v) / max(h, 1e-6)
    ln = math.hypot(nx, nz) or 1
    return (m + w * u + off * nx / ln, zc + h * v + off * nz / ln)


def angle_of_row(r, m, w, p=2.25, upper=True):
    """The section angle (deg, 0 top, +90 south, -90 north) whose point lies over row r."""
    u = max(-0.999, min(0.999, (r - m) / w))
    s = math.copysign(abs(u) ** (p / 2), u)
    a = math.degrees(math.asin(s))
    return a if upper else math.copysign(180, a) - a


# --- the horn ----------------------------------------------------------------------------------

PLATE = -0.12  # the plates' surface against the smoothed outline, px
GROOVES = [9.6, 13.4, 25.5, 46.5, 64.2, 80.3, 89.2]
BANDS = [57.0, 86.6, 94.2, 104.3, 113.4]
LEDGE_C0, LEDGE_C1 = 45.0, 118.0
CLAMPS = [  # (col0, col1, row0, row1, mat, ribs across)
    (39.0, 45.2, 6.9, 12.4, ST_A, 0),
    (58.0, 63.6, 4.9, 9.2, ST_B, 0),
    (80.6, 85.5, 1.9, 7.0, ST_C, 3),
    (107.6, 112.4, 0.95, 5.6, ST_D, 0),
]


def smooth_edges(raw, cs, half):
    """Local linear regression of the column edges (triangular weights, +-half columns): a smooth
    line through the staircase's midpoints, so the outline matches the sprite row by row without
    the stair steps turning into lumps."""
    out = []
    for c in cs:
        hw = half(c)
        xs, ys, ws = [], [], []
        for k, v in raw.items():
            d = abs(k + 0.5 - c)
            if d <= hw:
                xs.append(k + 0.5)
                ys.append(v)
                ws.append(1 - d / (hw + 1))
        sw = sum(ws)
        mx = sum(w * x for w, x in zip(ws, xs)) / sw
        my = sum(w * y for w, y in zip(ws, ys)) / sw
        sxx = sum(w * (x - mx) ** 2 for w, x in zip(ws, xs))
        sxy = sum(w * (x - mx) * (y - my) for w, x, y in zip(ws, xs, ys))
        out.append(my + (sxy / sxx if sxx > 1e-9 else 0.0) * (c - mx))
    return out


class Horn:
    def __init__(self, grid):
        raw = {c: col_edges(grid, c) for c in range(2, 113)}
        tops = {c: v[0] for c, v in raw.items()}
        bots = {c: v[1] for c, v in raw.items()}
        cs = [c + 0.5 for c in range(2, 113)]
        half = lambda c: 1.6 if c < 8 else (3.0 if c < 20 else 4.5)  # noqa: E731
        st, sb = smooth_edges(tops, cs, half), smooth_edges(bots, cs, half)
        # Past the knuckle seam the horn keeps its rows 1-13 inside the knuckle.
        cs += [113.5, 115.0, 117.0]
        st += [1.0, 1.0, 1.0]
        sb += [13.0, 13.0, 13.0]
        self.T = pchip(cs, st)
        self.B = pchip(cs, sb)

    def ledge_frac(self, c):
        if c <= LEDGE_C0 or c >= LEDGE_C1 + 2:
            return 0.0
        return min(1.0, (c - LEDGE_C0) / 3.0)

    def zc(self, c):
        # The point droops a little toward the tip: a horn that curls down, not a flat stroke.
        return -2.2 * max(0.0, 1 - c / 34.0) ** 2

    def section(self, c, grow=0.0):
        """(centre row, centre z, half width, half height) of the tube at column c."""
        c = max(2.0, c)
        t = self.T(c)
        b = self.B(c) - 1.0 * self.ledge_frac(c)
        m, w = (t + b) / 2, max(0.0, (b - t) / 2)
        dm = ((self.T(c + 1) + self.B(c + 1)) - (self.T(c - 1) + self.B(c - 1))) / 4
        h = 0.95 * w * math.cos(math.atan(dm))
        if c > 116:
            m, w, h = 6.8, 5.8, 5.5
        return m, self.zc(c), max(0.0, w + grow), max(0.0, h + grow)

    def grow(self, c):
        """The plates sit just under the outline (the collars at the joints stand on it); along
        the curled tip (cols 5-45) they are a little fuller, so the thin horn keeps the sprite's
        width at both edges."""
        if c < 3.0 or c > 52.0:
            return PLATE
        full = min(1.0, (c - 3.0) / 3.0, (52.0 - c) / 8.0)
        return PLATE + 0.12 * full


def build_horn(P, D, hz):
    feats = []
    for g in GROOVES:
        feats.append((g, "groove"))
    for b in BANDS:
        feats.append((b, "band"))
    base = []
    c = 2.6
    while c < 117.0:
        base.append(c)
        c += 0.45 if c < 6 else (0.8 if c < 16 else (1.1 if c < 40 else 1.4))
    keep = [c for c in base if all(abs(c - f) > 0.75 for f, _ in feats)]
    rings = [(2.0, *hz.section(2.0)[:2], 0.0, 0.0, TIP)]

    def add(c, grow, mat):
        m, zc, w, h = hz.section(c, grow)
        rings.append((c, m, zc, w, h, mat))

    events = sorted([(c, "base") for c in keep] + feats)
    for c, kind in events:
        mat = TIP if c < 9.6 else (HORN if c < 85.5 else ROOT)
        g = hz.grow(c)
        if kind == "base":
            add(c, g, mat)
        elif kind == "groove":
            # A telescoping joint (graft from design A): the tipward segment steps in just before
            # the joint (a dark gap), then a collar chamfered both sides on the rootward segment's
            # mouth, standing on the outline, then that segment's plating.
            g0, g1 = hz.grow(c - 0.6), hz.grow(c + 0.5)
            nxt = TIP if c + 0.5 < 9.6 else (HORN if c + 0.5 < 85.5 else ROOT)
            add(c - 0.6, g0, mat)
            add(c - 0.48, g0 - 0.3, DEEP)
            add(c - 0.34, g0 - 0.3, DEEP)
            add(c - 0.26, max(g0, g1) + 0.02, nxt)
            add(c - 0.14, max(g0, g1) + 0.16, nxt)
            add(c + 0.22, max(g0, g1) + 0.16, nxt)
            add(c + 0.36, max(g0, g1) + 0.02, nxt)
            add(c + 0.5, g1, nxt)
        else:  # a raised collar, chamfered both sides
            add(c - 0.6, g, mat)
            add(c - 0.38, g + 0.28, BAND)
            add(c + 0.38, g + 0.28, BAND)
            add(c + 0.6, g, ROOT if c > 85 else HORN)
    rings.sort(key=lambda r: r[0])
    ring_loft(P, rings, HORN_UNIT, cap0=False, cap1=True)
    build_ledge(D, hz)
    for c0, c1, r0, r1, mat, ribs in CLAMPS:
        clamp(D, hz, c0, c1, r0, r1, mat, ribs)
    build_port(D, hz)
    build_lenses(D, hz)


def build_ledge(D, hz):
    """A chamfered ledge along the horn's lower south flank (the sprite's lit row 12), from col 45
    into the knuckle: its outer face on the outline, embedded in the tube's flank."""
    cs = []
    c = LEDGE_C0 + 0.5
    while c < LEDGE_C1:
        cs.append(c)
        c += 1.5
    cs.append(LEDGE_C1)
    raw = []
    for c in cs:
        f = hz.ledge_frac(c)
        m, zc, w, h = hz.section(c)
        raw.append((hz.B(c) - (1 - f) * 1.0, m + 0.55 * w, zc - 0.12 * h, zc - 0.62 * h))

    def avg(i, k):
        win = raw[max(0, i - 2):i + 3]
        return sum(r[k] for r in win) / len(win)
    rings = []
    for i, c in enumerate(cs):
        out, inn, top, bot = raw[i][0], avg(i, 1), avg(i, 2), avg(i, 3)
        ch = 0.3
        loop = [(inn, top), (out - ch, top), (out, top - ch), (out, bot + ch), (out - ch, bot), (inn, bot)]
        rings.append([D.v((x, c, z)) for x, z in loop])
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for a in range(6):
            b = (a + 1) % 6
            D.f((r0[a], r0[b], r1[b], r1[a]), LEDGE, away=(hz.section(cs[k])[0], cs[k], hz.section(cs[k])[1]))
    D.f(rings[0], LEDGE, out=(0, -1, 0))
    D.f(rings[-1], LEDGE, out=(0, 1, 0))
    # Hangers tying it to the flank every few columns (the sprite's bright ticks on row 12).
    for c in (52.0, 70.0, 98.0 + 3.0, 108.0):
        m, zc, w, h = hz.section(c)
        b = hz.B(c)
        hull(D, cbox(m + 0.5 * w, b - 0.15, c - 0.35, c + 0.35, zc - 0.7 * h, zc - 0.02 * h, 0.12), BAND)


def inside(hz, p, margin=0.06):
    """A point (row, col, z) moved inside the sprite's outline (the smoothed top and bottom edges
    of the horn at its column), so nothing on the horn sticks out of the sprite seen from above."""
    x, c, z = p
    return (min(max(x, hz.T(c) + margin), hz.B(c) - margin), c, z)


def clamp(D, hz, c0, c1, r0, r1, mat, ribs):
    """A steel saddle clamped over the horn from row r0 to r1 (as seen from above), standing
    0.55 px proud, with chamfered edges: the convex hull of points on the offset surface."""
    pts = []
    d, ch = 0.6, 0.22
    cs = [c0, c0 + ch, (c0 + c1) / 2, c1 - ch, c1]
    for c in cs:
        m, zc, w, h = hz.section(c, hz.grow(c))
        a0 = angle_of_row(max(r0, m - w + 0.05), m, w)
        a1 = angle_of_row(min(r1, m + w - 0.05), m, w)
        if r0 <= m - w + 0.3:
            a0 = -100.0
        end = c in (c0, c1)
        steps = 7
        for k in range(steps + 1):
            a = a0 + (a1 - a0) * k / steps
            edge = k in (0, steps)
            off = d - ch if (end or edge) else d
            aa = a + (2.5 if k == 0 else -2.5 if k == steps else 0.0) if (end and edge) else a
            pts.append((*(lambda q: (q[0], c, q[1]))(surface_pt(m, zc, w, h, aa, off)),))
        # anchor points inside the tube so the hull reaches down into it
        for a in (a0, a1):
            x, z = surface_pt(m, zc, w, h, a, -1.2)
            pts.append((x, c, z))
    pts = [inside(hz, p) for p in pts]
    hull(D, pts, mat)
    # Ribs across the saddle (clamp C's slats).
    for k in range(ribs):
        c = c0 + 0.9 + k * (c1 - c0 - 1.8) / max(1, ribs - 1)
        rp = []
        m, zc, w, h = hz.section(c, hz.grow(c))
        a0 = angle_of_row(max(r0 + 0.3, m - w + 0.2), m, w)
        a1 = angle_of_row(min(r1 - 0.3, m + w - 0.2), m, w)
        for cc in (c - 0.28, c + 0.28):
            for k2 in range(6):
                a = a0 + (a1 - a0) * k2 / 5
                for off in (d + 0.35, d - 0.1):
                    x, z = surface_pt(m, zc, w, h, a, off)
                    rp.append(inside(hz, (x, cc, z)))
        hull(D, rp, SLAT)


def build_port(D, hz):
    """The dark grille port in the south flank (cols 95.8-99.6, rows 8-12.6): a recessed dark
    panel in a steel frame with three slats."""
    c0, c1 = 95.8, 99.6
    ms = [hz.section(c) for c in (c0, c1)]
    m, zc, w, h = hz.section((c0 + c1) / 2)
    a0, a1 = angle_of_row(8.0, m, w), 112.0
    for (lo, hi, off, mat) in ((c0, c1, 0.25, PORT),):
        pts = []
        for c in (lo, hi):
            mm, zz, ww, hh = hz.section(c)
            for k in range(7):
                a = a0 + (a1 - a0) * k / 6
                for o in (off, -1.0):
                    x, z = surface_pt(mm, zz, ww, hh, a, o)
                    pts.append((x, c, z))
        hull(D, pts, mat)
    # frame: two end bars and the slats between
    for c, mat, o in ((c0 + 0.2, ST_A, 0.55), (c1 - 0.2, ST_A, 0.55), (96.9, SLAT, 0.45), (97.8, SLAT, 0.45),
                      (98.7, SLAT, 0.45)):
        rp = []
        mm, zz, ww, hh = hz.section(c)
        for cc in (c - (0.22 if mat == ST_A else 0.16), c + (0.22 if mat == ST_A else 0.16)):
            for k in range(6):
                a = a0 + (a1 - a0) * k / 5
                for off in (o, 0.0):
                    x, z = surface_pt(mm, zz, ww, hh, a, off)
                    rp.append((x, cc, z))
        hull(D, rp, mat)
    # top and bottom frame rails
    for a in (a0, a1):
        rp = []
        for c in (c0, c1):
            mm, zz, ww, hh = hz.section(c)
            for da in (-2.5, 2.5):
                for off in (0.55, 0.0):
                    x, z = surface_pt(mm, zz, ww, hh, a + da, off)
                    rp.append((x, c, z))
        hull(D, rp, ST_A)


def lens(D, c0, c1, r0, r1, zbase, height, mat_rim, n=10):
    """A small domed glass lens in a steel rim over cols c0..c1, rows r0..r1 at height zbase."""
    cc, rr = (c0 + c1) / 2, (r0 + r1) / 2
    a, b = (c1 - c0) / 2, (r1 - r0) / 2
    rim = []
    for k in range(n):
        t = 2 * math.pi * k / n
        for s, z in ((1.18, zbase - 0.6), (1.18, zbase + 0.25), (1.0, zbase + 0.35)):
            rim.append((rr + s * b * math.sin(t), cc + s * a * math.cos(t), z))
    hull(D, rim, mat_rim)
    dome = []
    for ring, (s, z) in enumerate(((0.95, zbase + 0.3), (0.75, zbase + 0.3 + 0.6 * height),
                                   (0.4, zbase + 0.3 + 0.92 * height))):
        for k in range(n):
            t = 2 * math.pi * k / n
            dome.append((rr + s * b * math.sin(t), cc + s * a * math.cos(t), z))
    dome.append((rr, cc, zbase + 0.3 + height))
    hull(D, dome, LENS)


def build_lenses(D, hz):
    # Clamp C's slit window: col 80.8-81.9, rows 2.9-5.0 (the sprite's two blue-grey pixels).
    for (c0, c1, r0, r1, rim) in ((80.85, 81.95, 2.85, 5.05, ST_C), (108.4, 111.6, 2.65, 4.85, ST_D)):
        cm = (c0 + c1) / 2
        m, zc, w, h = hz.section(cm, hz.grow(cm))
        a = angle_of_row((r0 + r1) / 2, m, w)
        x, z = surface_pt(m, zc, w, h, a, 0.6)
        lens(D, c0, c1, r0, r1, z, 0.55 if c1 - c0 > 2 else 0.35, rim)


# --- knuckle, neck, drum ------------------------------------------------------------------------

def build_knuckle(P, grid):
    """The elbow knuckle: a smooth ball whose outline follows the sprite's (top flat on row 1 to
    col 128, the lower lobe down to row 19.9 at cols 124-128, the lower-left edge a smooth curve
    from the horn's underside), as tall as it is wide (the sprite shades it round)."""
    tc = [112.2, 113.0, 128.0, 129.5, 131.0, 132.4, 133.2]
    tv = [3.2, 1.05, 1.05, 1.6, 2.3, 3.0, 3.4]
    bc = [112.2, 113.0, 115.0, 117.0, 119.0, 121.0, 122.8, 124.5, 126.5, 128.3, 130.0, 131.5, 132.4, 133.2]
    bv = [12.0, 12.85, 13.5, 14.15, 14.95, 16.5, 18.0, 19.4, 19.85, 19.6, 18.4, 17.0, 16.1, 15.4]
    T_, B_ = pchip(tc, tv), pchip(bc, bv)
    rings = []
    stations = [112.2, 112.6, 113.2] + [113.8 + 0.8 * i for i in range(24)]
    stations = [s for s in stations if s <= 132.6] + [133.2]
    for c in stations:
        t, b = T_(c), B_(c)
        m, w = (t + b) / 2, (b - t) / 2
        h = 0.97 * w if c > 113 else 0.9 * w
        rings.append((c, m, 0.3 * min(1, max(0, (c - 113) / 4)), w, h, KNUCKLE))
    ring_loft(P, rings, BALL_UNIT)
    return T_, B_


def build_pins(D, T_, B_):
    """The elbow's hinge pin (graft from design A): a steel boss on each flank of the knuckle, its
    face just inside the sprite's outline, with a recessed hub and the pin's end in it. The pin
    axis runs across the arm (sprite rows), so the knuckle reads as a powered elbow from the side."""
    # Centred a little under the equator, where the ball has curved in from the outline, so the
    # boss stands proud of the ball for the side views yet stays inside the outline from above.
    for c, side, zc, r in ((126.3, 1, -3.0, 2.2), (121.0, -1, -3.0, 2.4)):
        edge = B_ if side > 0 else T_
        face = min(edge(c + d) * side for d in (-r, -r / 2, 0, r / 2, r)) * side - side * 0.15
        n = 14
        for r_out, depth0, depth1, mat in ((r, 0.0, 1.8, ST_C), (0.6 * r, 0.28, 0.9, DEEP), (0.32 * r, 0.12, 1.0, BAND)):
            pts = []
            for k in range(n):
                t = 2 * math.pi * k / n
                for d, sc in ((depth0, 1.0 if mat != ST_C else 0.86), (depth0 + 0.12, 1.0), (depth1, 1.0)):
                    pts.append((face - side * d, c + sc * r_out * math.cos(t), zc + sc * r_out * math.sin(t)))
            hull(D, pts, mat)


CHANNEL = [(86.2, 95.2), (100.2, 112.2)]  # cols where the root's south flank is bare
CH_A0, CH_A1 = 64.0, 90.0                # its edges as section angles (0 top, 90 south)


def _flank_loft(D, hz, cs, a0, a1, off_out, off_in, mat):
    """A strip lying along the horn's south flank between section angles a0 and a1, from off_in
    to off_out px from the plating, lofted through columns cs."""
    rings = []
    for c in cs:
        m, zc, w, h = hz.section(c, hz.grow(c))
        loop = []
        for a, off in ((a0, off_in), (a0, off_out), (a1, off_out), (a1, off_in)):
            x, z = surface_pt(m, zc, w, h, a, off)
            loop.append(D.v(inside(hz, (x, c, z))))
        rings.append((loop, (m, c, zc)))
    for (r0, ax), (r1, _) in zip(rings, rings[1:]):
        for k in range(4):
            j = (k + 1) % 4
            D.f((r0[k], r0[j], r1[j], r1[k]), mat, away=ax)
    D.f(rings[0][0], mat, out=(0, -1, 0))
    D.f(rings[-1][0], mat, out=(0, 1, 0))


def build_channel(D, hz):
    """The hydraulic channel in the root's south flank (graft from design A), only where the ledge
    and the grille port leave the flank bare (cols 86-112): a dark channel floor between two
    lips of the plating, two steel lines laid in it, and clips holding the lines at each end."""
    for c0, c1 in CHANNEL:
        n = max(2, int(round((c1 - c0) / 1.0)))
        cs = [c0 + (c1 - c0) * i / n for i in range(n + 1)]
        _flank_loft(D, hz, cs, CH_A0 + 2.5, CH_A1 - 2.5, 0.03, -0.8, DEEP)
        _flank_loft(D, hz, cs, CH_A0, CH_A0 + 2.5, 0.3, -0.8, ROOT)
        _flank_loft(D, hz, cs, CH_A1 - 2.5, CH_A1, 0.3, -0.8, ROOT)
        for a in (72.0, 82.0):
            rings = []
            for c in cs[:1] + [c0 + 0.4] + cs[1:-1] + [c1 - 0.4] + cs[-1:]:
                m, zc, w, h = hz.section(c, hz.grow(c))
                x, z = surface_pt(m, zc, w, h, a, 0.24)
                x = min(x, hz.B(c) - 0.3)
                rings.append((c, x, z, 0.24, 0.24, ST_C))
            ring_loft(D, rings, superellipse(8, 2.0))
        for c in (c0 + 0.5, c1 - 0.5):
            m, zc, w, h = hz.section(c, hz.grow(c))
            pts = []
            for cc in (c - 0.35, c + 0.35):
                for k in range(5):
                    a = 68.0 + 18.0 * k / 4
                    for off in (0.62, -0.4):
                        x, z = surface_pt(m, zc, w, h, a, off)
                        pts.append(inside(hz, (x, cc, z), 0.3))
            hull(D, pts, SLAT)


NECK_M, NECK_W = 9.6, 6.4


def drum_m(c):
    c = min(max(c, 133.0), 139.0)  # (pchip extrapolates linearly)
    return pchip([133.0, 134.5, 136.0, 137.5, 139.0], [9.6, 10.0, 10.6, 11.1, 11.5])(c)


def drum_r(c):
    c = min(max(c, 133.0), 139.0)
    return pchip([133.0, 134.0, 135.0, 136.0, 137.0, 138.0, 139.0],
                 [6.3, 6.75, 7.25, 8.3, 9.25, 9.85, 10.4])(c)


def build_neck(P):
    rings = []
    for c, g, mat in ((130.5, 0.0, NECK), (131.9, 0.0, NECK), (132.1, 0.4, BAND), (132.7, 0.4, BAND),
                      (132.9, 0.0, NECK), (133.4, 0.0, NECK)):
        rings.append((c, NECK_M, 0.0, NECK_W + g, 0.97 * NECK_W + g, mat))
    ring_loft(P, rings, BALL_UNIT)


DRUM_C0 = 141.6  # plates from here to the end ring
DRUM_C1 = 161.6
CORE_R = 9.95   # under the plates


def build_drum(P, D):
    rings = []

    def add(c, r, mat, m=None):
        rings.append((c, drum_m(c) if m is None else m, 0.0, r, r, mat))
    # Shoulder cone from the neck to the flange ring.
    for c in (133.2, 134.0, 135.0, 136.0, 137.0, 138.0):
        add(c, drum_r(c) - 0.05, RING)
    add(139.0, 10.2, RING)
    add(139.3, 10.5, RING)       # flange ring (the bright cols 140-141)
    add(141.0, 10.5, RING)
    add(141.3, CORE_R, CORE)
    add(DRUM_C1 + 0.2, CORE_R, RING)
    add(DRUM_C1 + 0.5, 10.5, RING)  # end ring: three cooling fins between dark grooves
    for g in (163.0, 164.6, 166.2):
        add(g - 0.3, 10.5, RING)
        add(g - 0.1, 10.22, RING)
        add(g + 0.1, 10.22, RING)
        add(g + 0.3, 10.5, RING)
    add(167.4, 10.5, RING)
    add(167.95, 9.9, RING)
    ring_loft(P, rings, DRUM_UNIT, cap0=False, cap1=False)
    # End cap: a recessed face with a hub (the arm leaves the screen here).
    m = 11.5
    cap = [(167.95, 9.9), (167.95, 8.6), (167.45, 8.3), (167.45, 4.0), (167.95, 3.6), (167.95, 0.0)]
    rr = [(c, m, 0.0, r, r, RING) for c, r in cap]
    ring_loft(P, rr, DRUM_UNIT, cap0=False, cap1=False)
    # Armour plates along the drum, lengthwise, seams at the sprite's dark rows 13 and 18.5.
    # The upper plate is two, split by one lengthwise panel line at -61 deg (graft from design A),
    # clear of the bolt rows at -100 and 6 deg.
    for a0, a1, mat in ((-104.0, -62.2, DRUM_UP), (-59.8, 9.0, DRUM_UP), (13.0, 43.0, DRUM_LO),
                        (48.0, 104.0, DRUM_LO)):
        drum_plate(D, DRUM_C0, DRUM_C1, a0, a1, mat)
    # Bolt heads along the plates' seams (rows 13 and 18.5) and the flange ring.
    for a in (6.0, 16.0, 45.5 - 4.5, 51.0, -100.0):
        for c in (143.2, 147.0, 153.4, 157.2, 160.4):
            bolt(D, c, a, 0.55)


def bolt(D, c, a, base):
    """A small hexagonal bolt head standing on the drum surface at column c, angle a."""
    pts = []
    for k in range(6):
        t = 2 * math.pi * k / 6
        for off in (base - 0.2, base + 0.35):
            ang = a + math.degrees(0.42 * math.sin(t) / (CORE_R + base))
            x, cc, z = _drum_pt(c + 0.42 * math.cos(t), ang, off)
            pts.append((x, cc, z))
    hull(D, pts, RING)


def drum_plate(D, c0, c1, a0, a1, mat, d=0.55, ch=0.25):
    pts = []
    n = max(4, int((a1 - a0) / 9))
    for c in (c0, c0 + ch, c1 - ch, c1):
        end = c in (c0, c1)
        for k in range(n + 1):
            a = a0 + (a1 - a0) * k / n
            edge = k in (0, n)
            off = d - ch if (end or edge) else d
            if edge:
                a += 1.4 if k == 0 else -1.4
                if not end:
                    pts.append((*_drum_pt(c, a + (-1.4 if k == 0 else 1.4), d - ch),))
            pts.append(_drum_pt(c, a, off))
        for a in (a0, a1):
            pts.append(_drum_pt(c, a, -0.8))
    hull(D, pts, mat)


def _drum_pt(c, a, off):
    r = CORE_R + off
    t = math.radians(a)
    return (11.5 + r * math.sin(t), c, r * math.cos(t))


def build_brackets(D):
    """The gripper's claws: a hinge bracket over the shoulder (cols 133-141.5, rows 5.2-9.4, the
    sprite's lit cols 138-141) with its pin boss, and a strut along the lit diagonal from the neck's
    south flank (134, 16) to the drum's south side (139.5, 21.3)."""
    # Hinge bracket: a chamfered block riding the neck/shoulder top on the north side.
    hull(D, cbox(5.0, 9.4, 132.4, 141.6, 4.5, 8.7, 0.35), BRACKET)
    # Its pin boss.
    pts = []
    for k in range(10):
        t = 2 * math.pi * k / 10
        for c in (137.4, 139.6):
            pts.append((7.2 + 1.5 * math.sin(t), c, 8.9 + 1.5 * math.cos(t) * 0.6 + 0.3))
    hull(D, pts, ST_C)
    # Claw strut: a bar from (row 15.2, col 133.3) to (row 20.8, col 139.4), z -1 to 4.5.
    a, b = (14.5, 133.6), (20.4, 139.9)
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln * 0.95, dx / ln * 0.95
    pts = []
    for (x, y) in (a, b):
        for s in (-1, 1):
            for z in (-1.5, 3.4):
                pts.append((x + s * nx, y + s * ny, z))
            pts.append((x + s * nx * 0.6, y + s * ny * 0.6, 4.1))
    hull(D, pts, STRUT)


# --- assembly -----------------------------------------------------------------------------------

def finish(part, mats, coll, smooth_angle=None):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # (row, col, z) px -> Blender: X = (col - 84) / 12, Y = (14 - row) / 12, Z = z / 12 (a rotation).
    m = Matrix(((0, PX, 0, -84 * PX), (-PX, 0, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle or part.smooth_angle))
    return obj


def build(coll, grid, sprite):
    mats = materials(sprite)
    hz = Horn(grid)
    horn = Part("arm_horn", smooth_angle=34)
    det = Part("arm_detail", smooth_angle=30)
    build_horn(horn, det, hz)
    body = Part("arm_body", smooth_angle=34)
    T_, B_ = build_knuckle(body, grid)
    build_pins(det, T_, B_)
    build_channel(det, hz)
    build_neck(body)
    build_drum(body, det)
    build_brackets(det)
    return [finish(p, mats, coll) for p in (horn, body, det)]


def bake_maps(obj, out_dir, tag, size=512, samples=64):
    textured = T.TEXTURED
    T.TEXTURED = TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TEXTURED = textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", tag)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    grid, sprites, merged = load()
    coll = common.reset_collection(NAME)
    objs = build(coll, grid, merged)
    obj = T.join(objs, NAME)
    common._apply_modifiers(obj)
    # The outline shell (D51) comes from the closed, uncut parts: after cull_hidden the skin is
    # open where parts meet, and its remesh falls apart into hundreds of islands (outline_shell
    # keeps only the largest). From the closed parts the remesh is one island over the whole arm.
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    shell = common.outline_shell(closed, coll, voxel=0.02, faces=4000, smooth=8)
    bpy.data.objects.remove(closed)
    if "--no-cull" not in argv:
        T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles, shell {len(shell.data.polygons)} faces")
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprites[PIECES[0]]["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout, coll)
    shells = common.split_assembly(shell, layout, coll)
    # Only the pieces render in the bakes (their neighbours give the occlusion across the cuts).
    for o in (obj, shell, *shells.values()):
        o.hide_render = True
    # Baked occlusion and edge wear only (no concept projection: maps.json says "bake": "model",
    # as the player ships, PR #84). One small map per piece, with its own materials, so each GLB
    # carries only its own 512 px maps instead of a copy of one big map for the whole arm.
    fmt = "AUTO"
    bake = "--no-bake" not in argv
    if bake:
        import tempfile
        fmt = "WEBP"
    for name in PIECES:
        p, s = pieces[name], shells[name]
        s.name = f"{name}_outline"
        s["tyrian_outline"] = True
        mats = materials(merged, suffix=f"_{name.split('-')[1]}")
        for i, m in enumerate(mats):
            p.data.materials[i] = m
        if bake:
            bake_maps(p, tempfile.mkdtemp(prefix="arm_bake_"), f"arm_{name.split('-')[1]}", size=512, samples=64)
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        t = sum(len(q.vertices) - 2 for q in p.data.polygons)
        xs = [v.co.x for v in s.data.vertices]
        px = [v.co.x for v in p.data.vertices]
        print(f"piece {name}: {t} triangles; x {min(px):.2f}..{max(px):.2f}, shell "
              f"{len(s.data.polygons)} faces x {min(xs) if xs else 0:.2f}..{max(xs) if xs else 0:.2f}")
        common.export_sprite_model(REPO, [p, s], f"enemies/{name}", sprites[name]["sprites"], image_format=fmt)
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        import tempfile
        import lib_b061 as lib
        ref = lib.write_png(grid, merged["colors"], Path(tempfile.mkdtemp()) / "arm.png", pad_to=(W, W * 14 // 12))
        obj.hide_render = False
        common.render_preview([obj], str(out), ref, size=W // 12, view_px=840)


if __name__ == "__main__":
    main()
