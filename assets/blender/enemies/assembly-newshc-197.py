"""Green tank bar (newshc.shp 197/201/205 + 199/203/207, two 2x2 pieces, 48x28 px).

A hard-surface rebuild led by the blueprint's cross-sections, fitted to the sprite's INNER mask
(D74: the game's ink outline goes round the model, so the top-view edge sits on the inner edge of
the sprite's 1 px border; the blueprint was fitted to the outer mask and is shrunk by that ring).

The machine (sprite px; c across the whole bar 0-48, r down the screen, z up from the underside):
- two pressure tanks lying across the bar (axis r 6.5, radius 3.5, rows 3-10), each with a long
  ellipsoidal head at the outer end (6 px deep, tip on column 1), a weld bead where the head meets
  the shell, two raised straps (columns 16 and 18) with lugs under them, and a necked spigot that
  plugs into the central spine; a green cradle (saddle) holds each head from below and in front
  (the sprite's green at rows 8-10, columns 1-3), a small feed line runs along each tank's rear;
- the spine: a chamfered keel block between the tanks (columns 21-27, rows 2-10) whose front
  slopes down to the boom, with a bolted hatch, a grip and lifting lugs on top and vents behind;
- the boom: one round tube across the front of the tanks (rows 10-13) swelling into a bulb at each
  end (rows 10-15) with a band and a collar, necked in under the spine to rows 10-12 with a dark
  coupling sleeve in the middle (the sprite's dark 82 at columns 23-24);
- under the boom on each side a radiator: a dark body (82), a wide plate (84) and four rounded
  fins (82/84/82/86) with dark slots (80) between, a wall at the lamp, hangers up to the boom;
- between the radiators a lamp housing (84) with a bezel (115, 117 on the last frames) round a
  glowing cylindrical lens (112, 119, 123 on the three frames).
Each part takes the sprite's palette index for its region (median, darkest/brightest left out).
Undersides are plain closed shapes.

Build: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshc-197.py
One outline shell is built on the whole bar and cut per piece without capping (no ink line at the
seam); each piece is exported to public/models/enemies/<piece>.glb with its sprite entry.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

WT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "assets" / "blender" / "enemies")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = WT
CX0, CY0 = 69, 123  # screen centre of the 48x28 bar (the seam): the Blender origin
NAME = "assembly-newshc-197"
PIECES = ["newshc-197", "newshc-199"]
Z0 = 3.6  # px: the model's vertical middle-ish sits at z 0 (heights below are from the underside)
TAG = "nshc197A"

# ----------------------------------------------------------------------------------------------
# Materials (slot names -> palette index)
# ----------------------------------------------------------------------------------------------
SLOTS = {}
MATS = []


def load_sprite():
    d = common.load_sprite(WT, PIECES[0])
    d["colors"].update(common.load_sprite(WT, PIECES[1])["colors"])
    return d


def make_materials(sprite):
    def add(key, idx, metallic=0.3, roughness=0.45, **kw):
        SLOTS[key] = len(MATS)
        MATS.append(common.palette_material(sprite, idx, f"{TAG}-{key}", metallic=metallic,
                                            roughness=roughness, **kw))
    add("tank", 40)
    add("tank_dk", 38)  # weld seams and the filler cap
    add("strap", 36)
    add("saddle", 37)
    add("feed", 87)
    add("boom", 88)
    add("collar", 87)
    add("band", 89)
    add("coupling", 82, metallic=0.2, roughness=0.6)
    add("rad_body", 82, metallic=0.2, roughness=0.55)
    add("header", 81, metallic=0.2, roughness=0.6)
    add("plate", 84)
    add("fin82", 82)
    add("fin84", 84)
    add("fin86", 87, frames={201: 89, 203: 89, 205: 92, 207: 92})  # lamp glow on the rib beside it
    add("wall", 84, frames={201: 86, 203: 86, 205: 88, 207: 88})
    add("slot", 80, metallic=0.0, roughness=0.8)
    add("hanger", 83)
    add("spine", 89)
    add("spine_side", 88)
    add("spine_ch", 90)
    add("hatch", 90)
    add("bolt", 91)
    add("hatch_ch", 91)
    add("lug", 88)
    add("vent", 82, metallic=0.1, roughness=0.7)
    add("housing", 84)
    add("rim", 115, metallic=0.1, roughness=0.5, emission_strength=1.5, frames={205: 117, 207: 117})
    add("lens", 112, metallic=0.0, roughness=0.5, emission_strength=4.0,
        frames={201: 119, 203: 119, 205: 123, 207: 123})


# ----------------------------------------------------------------------------------------------
# Geometry helpers (all in sprite px: x = c - 24, y = r, z up; T.finish maps them to Blender)
# ----------------------------------------------------------------------------------------------

def X(c):
    return c - 24.0


def ring_pts(yc, zc, hy, hz, n, power=2.0):
    pts = []
    e = 2.0 / power
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        ca, sa = math.cos(a), math.sin(a)
        pts.append((yc + hy * math.copysign(abs(ca) ** e, ca), zc + hz * math.copysign(abs(sa) ** e, sa)))
    return pts


def loft_x(P, stations, mats, n=24, power=2.0, cap0=True, cap1=True, mirror=False):
    """A tube along x through stations (x, yc, zc, hy, hz); mats[i] is the material of the band
    between stations i and i+1. A station with hy = hz = 0 is a tip (one vertex)."""
    if mirror:
        stations = [(-x, yc, zc, hy, hz) for x, yc, zc, hy, hz in stations]
    rings = []
    for x, yc, zc, hy, hz in stations:
        if hy <= 1e-6 and hz <= 1e-6:
            rings.append(([P.v((x, yc, zc))], (x, yc, zc)))
        else:
            rings.append(([P.v((x, y, z)) for y, z in ring_pts(yc, zc, hy, hz, n, power)], (x, yc, zc)))
    for i, ((r0, c0), (r1, c1)) in enumerate(zip(rings, rings[1:])):
        m = SLOTS[mats[i] if isinstance(mats, (list, tuple)) else mats]
        cen = ((c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2, (c0[2] + c1[2]) / 2)
        if len(r0) == 1 and len(r1) == 1:
            continue
        if len(r0) == 1:
            for j in range(n):
                P.f((r0[0], r1[j], r1[(j + 1) % n]), m, away=cen)
        elif len(r1) == 1:
            for j in range(n):
                P.f((r0[j], r1[0], r0[(j + 1) % n]), m, away=cen)
        else:
            for j in range(n):
                k = (j + 1) % n
                P.f((r0[j], r0[k], r1[k], r1[j]), m, away=cen)
    dx = 1.0 if stations[-1][0] > stations[0][0] else -1.0
    m0 = SLOTS[mats[0] if isinstance(mats, (list, tuple)) else mats]
    m1 = SLOTS[mats[-1] if isinstance(mats, (list, tuple)) else mats]
    if cap0 and len(rings[0][0]) > 1:
        P.f(rings[0][0], m0, out=(-dx, 0, 0))
    if cap1 and len(rings[-1][0]) > 1:
        P.f(rings[-1][0], m1, out=(dx, 0, 0))


def loft_y(P, x, stations, mat, n=16, power=4.0, cap0=True, cap1=True):
    """A tube along y (fins, ribs) through stations (y, xc_off, zc, hx, hz) at column-x x."""
    rings = []
    for y, dx, zc, hx, hz in stations:
        pts = ring_pts(x + dx, zc, hx, hz, n, power)
        rings.append(([P.v((px, y, pz)) for px, pz in pts], (x + dx, y, zc)))
    m = SLOTS[mat]
    for (r0, c0), (r1, c1) in zip(rings, rings[1:]):
        cen = ((c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2, (c0[2] + c1[2]) / 2)
        for j in range(n):
            k = (j + 1) % n
            P.f((r0[j], r0[k], r1[k], r1[j]), m, away=cen)
    if cap0:
        P.f(rings[0][0], m, out=(0, -1, 0))
    if cap1:
        P.f(rings[-1][0], m, out=(0, 1, 0))


def box(P, c0, c1, r0, r1, z0, z1, mat, ch=0.2, chz=None, mirror=False):
    """A chamfered block over columns c0..c1 (left-half columns; mirror=True puts the mirror image
    on the right half), rows r0..r1, heights z0..z1."""
    x0, x1 = X(c0), X(c1)
    if mirror:
        x0, x1 = -x1, -x0
    ch = min(ch, (x1 - x0) / 2.01, (r1 - r0) / 2.01)
    chz = ch if chz is None else min(chz, (z1 - z0) / 2.01)
    T.hull(P, T.cbox(x0, x1, r0, r1, z0, z1, ch, chz), SLOTS[mat])


def both(fn, *a, **kw):
    fn(*a, mirror=False, **kw)
    fn(*a, mirror=True, **kw)


# ----------------------------------------------------------------------------------------------
# Parts
# ----------------------------------------------------------------------------------------------
TANK_Y, TANK_Z, TANK_R = 6.5, 4.5, 3.5


def tank(P, mirror):
    y, z, r = TANK_Y, TANK_Z, TANK_R
    # (column, radius, material of the band from this station to the next)
    sts = []
    tip, depth = 1.0, 6.0
    for t in (0.0, 0.004, 0.02, 0.05, 0.1, 0.17, 0.26, 0.37, 0.5, 0.64, 0.78, 0.9, 1.0):
        sts.append((tip + depth * t, r * math.sqrt(max(0.0, 1.0 - (1.0 - t) ** 2)), "tank"))
    # weld bead where the head meets the shell (a modelled seam: a low raised ring)
    sts += [(7.15, r + 0.12, "tank_dk"), (7.35, r + 0.12, "tank_dk"), (7.5, r, "tank")]
    for c0 in (16.0, 18.0):  # straps: raised 0.22 with 45-degree edges
        rs = r + 0.22
        sts += [(c0 - 0.04, r, "strap"), (c0 + 0.18, rs, "strap"), (c0 + 0.8, rs, "strap"), (c0 + 1.02, r, "tank")]
    # necked spigot into the spine socket (the sprite's dark column 20)
    sts += [(20.05, r, "tank"), (20.35, 2.95, "tank"), (21.6, 2.95, "tank")]
    st = [(X(c), y, z, rr, rr) for c, rr, _ in sts]
    loft_x(P, st, [m for _, _, m in sts[:-1]], n=28, mirror=mirror)
    # filler boss on the head's tip (dark, a low cap)
    boss = [(0.95, 0.0), (1.0, 0.35), (1.1, 0.5), (1.5, 0.55), (1.9, 0.5)]
    loft_x(P, [(X(c), y, z, rr, rr) for c, rr in boss], ["tank_dk"] * 4, n=12, mirror=mirror)
    # strap lugs underneath (closing bolts), half buried in the shell's underside
    for c0 in (16.0, 18.0):
        box(P, c0 + 0.08, c0 + 0.88, y + 2.0, y + 3.3, z - r - 0.5, z - r + 1.0, "strap", ch=0.15, mirror=mirror)
        box(P, c0 + 0.08, c0 + 0.88, y - 3.3, y - 2.0, z - r - 0.5, z - r + 1.0, "strap", ch=0.15, mirror=mirror)
    # cradle under the head: a block with chamfered top, its outer face on column 1
    box(P, 1.0, 5.4, 7.7, 10.8, 0.7, 4.3, "saddle", ch=0.4, mirror=mirror)
    box(P, 1.6, 5.0, 3.6, 7.8, 0.7, 2.3, "saddle", ch=0.35, mirror=mirror)  # its rear foot
    # feed line along the rear underside (seen from behind), clamped twice
    loft_x(P, [(X(5.2), 4.0, 1.7, 0.5, 0.5), (X(21.4), 4.0, 1.7, 0.5, 0.5)], ["feed"], n=12, mirror=mirror)
    for c in (9.0, 14.0):
        box(P, c, c + 0.6, 3.3, 4.7, 1.0, 2.4, "strap", ch=0.12, mirror=mirror)


def boom(P):
    """One tube across the whole bar (stations mirrored about the seam, so no faces on it)."""
    zc = 3.0
    half = []
    tip, depth, by, bh = 1.0, 2.6, 12.55, 2.45
    for t in (0.0, 0.03, 0.1, 0.2, 0.33, 0.5, 0.68, 0.85, 1.0):
        s = math.sqrt(max(0.0, 1.0 - (1.0 - t) ** 2))
        half.append((tip + depth * t, by, bh * s, "boom"))
    for c, yc, hh, m in ((4.2, by, bh, "band"), (4.3, by, bh + 0.14, "band"), (4.7, by, bh + 0.14, "band"),
                         (4.8, by, bh, "boom"), (7.0, by, bh, "boom")):
        half.append((c, yc, hh, m))
    # taper the bulb into the tube (pchip in yc and radius)
    fy = T.pchip([7.0, 8.9], [by, 11.5])
    fh = T.pchip([7.0, 8.9], [bh, 1.5])
    for c in (7.4, 7.8, 8.2, 8.6, 8.9):
        half.append((c, fy(c), fh(c), "boom"))
    for c, yc, hh, m in ((17.3, 11.5, 1.5, "boom"), (17.9, 11.3, 1.3, "boom"), (18.5, 11.05, 1.05, "boom"),
                         (18.8, 11.0, 1.0, "boom"), (22.75, 11.0, 1.0, "boom"), (22.85, 11.0, 0.74, "coupling"),
                         (24.0, 11.0, 0.74, "coupling")):
        half.append((c, yc, hh, m))
    full = half + [(48.0 - c, yc, hh, m) for c, yc, hh, m in reversed(half[:-1])]
    st = [(X(c), yc, zc, hh if i not in (0, len(full) - 1) else 0.0, (hh * 1.05) if i not in (0, len(full) - 1) else 0.0)
          for i, (c, yc, hh, m) in enumerate(full)]
    # simpler band rule: a band takes the material both its stations share, else the outer one's
    band = []
    for i in range(len(full) - 1):
        a, b = full[i][3], full[i + 1][3]
        band.append(a if a == b else "boom")
    loft_x(P, st, band, n=24)
    # collars where the bulbs neck into the tube
    for mirror in (False, True):
        loft_x(P, [(X(c), 11.5, zc, rr, rr * 1.05) for c, rr in ((8.75, 1.45), (8.85, 1.7), (9.45, 1.7), (9.55, 1.45))],
               ["collar", "collar", "collar"], n=24, mirror=mirror)


def radiator(P, mirror):
    # dark body
    box(P, 7.7, 19.0, 12.9, 18.95, 0.4, 1.8, "rad_body", ch=0.2, mirror=mirror)
    box(P, 6.9, 8.0, 12.9, 16.0, 0.4, 1.8, "rad_body", ch=0.2, mirror=mirror)  # step under the bulb
    box(P, 18.9, 21.4, 12.9, 18.0, 0.4, 1.8, "rad_body", ch=0.2, mirror=mirror)
    # header strip along the back under the boom
    box(P, 8.0, 21.0, 12.95, 13.95, 1.7, 2.05, "header", ch=0.1, mirror=mirror)
    # wide plate and fins: rounded-box tubes along y, rounded front ends
    def rib(c0, c1, r0, r1, top, mat):
        xc = X((c0 + c1) / 2)
        if mirror:
            xc = -xc
        hx = (c1 - c0) / 2
        zc = 1.6
        hz = top - zc
        st = [(r0, 0, zc, hx, hz), (r1 - 0.35, 0, zc, hx, hz), (r1 - 0.12, 0, zc - 0.08, hx * 0.93, hz * 0.9),
              (r1, 0, zc - 0.2, hx * 0.8, hz * 0.72)]
        loft_y(P, xc, st, mat, n=16, power=4.0)
    rib(8.95, 12.0, 13.9, 18.95, 2.65, "plate")
    rib(13.05, 13.95, 13.9, 19.3, 2.55, "fin82")
    rib(15.05, 15.95, 13.9, 18.95, 2.55, "fin84")
    rib(17.05, 17.95, 13.9, 18.95, 2.55, "fin82")
    rib(19.0, 20.0, 13.9, 18.0, 2.55, "fin86")
    rib(20.0, 21.0, 13.9, 18.0, 2.45, "wall")  # wall at the lamp
    # slot floors (near black)
    for c in (12.0, 14.0, 16.0, 18.0):
        box(P, c + 0.02, c + 1.02, 13.95, 18.9, 1.75, 1.9, "slot", ch=0.0, mirror=mirror)
    # hangers up to the boom, and the dark block under the necked boom
    for c in (9.4, 16.4):
        box(P, c, c + 1.2, 12.3, 13.7, 1.6, 3.2, "hanger", ch=0.2, mirror=mirror)
    box(P, 18.1, 21.35, 11.4, 14.0, 0.6, 3.3, "header", ch=0.25, mirror=mirror)


def spine(P):
    ch = 0.45
    xo = 3.6  # half width: columns 20.4-27.6
    zt, zb = 8.3, 0.6
    prof_in = [(2.0 + ch, zt), (7.2, zt), (10.0, 5.3 + ch * 0.3)]
    prof_out = [(2.0, zt - ch), (2.0, zb), (7.2 + 0.15, zt - ch), (10.0, 5.3 - ch * 0.5), (10.0, zb)]
    pts = []
    for s in (-1, 1):
        for y, z in prof_in:
            pts.append((s * (xo - ch), y, z))
        for y, z in prof_out:
            pts.append((s * xo, y, z))
    T.hull(P, pts, SLOTS["spine_side"])
    # top plate: a lighter chamfer ring is the hatch's; the block top itself is 89 (recoloured below)
    # hatch: raised, chamfered, with bolts and a grip
    T.hull(P, T.cbox(-2.45, 2.45, 3.0, 6.8, zt - 0.3, zt + 0.5, 0.3), SLOTS["hatch"])
    for bx in (-1.9, 1.9):
        for by in (3.5, 6.3):
            T.hull(P, T.cbox(bx - 0.28, bx + 0.28, by - 0.28, by + 0.28, zt + 0.4, zt + 0.72, 0.1), SLOTS["bolt"])
    T.hull(P, T.cbox(-1.0, 1.0, 5.45, 5.95, zt + 0.4, zt + 0.82, 0.12), SLOTS["spine_ch"])
    # lifting lugs at the rear corners
    for bx in (-2.35, 2.35):
        T.hull(P, T.cbox(bx - 0.45, bx + 0.45, 2.1, 2.85, zt - 0.2, zt + 0.75, 0.2), SLOTS["lug"])
    # rear vents (dark louvres on the rear face)
    for k in range(4):
        z = 2.4 + k * 1.2
        T.hull(P, T.cbox(-2.2, 2.2, 1.92, 2.2, z, z + 0.6, 0.05), SLOTS["vent"])
    # clamp slot in front (dark), between the slope and the boom's coupling
    T.hull(P, T.cbox(-1.0, 1.0, 9.4, 11.6, 2.3, 5.4, 0.1), SLOTS["coupling"])


def lamp(P):
    T.hull(P, T.cbox(X(20.8), X(27.2), 13.9, 17.42, 0.4, 2.0, 0.2), SLOTS["housing"])
    T.hull(P, T.cbox(X(21.0), X(27.0), 13.95, 15.0, 1.6, 2.45, 0.15), SLOTS["rim"])
    T.hull(P, T.cbox(X(21.0), X(27.0), 16.95, 17.42, 1.4, 2.35, 0.12), SLOTS["rim"])
    zc, hz = 1.95, 0.72
    loft_x(P, [(X(21.05), 16.0, zc, 0.0, 0.0), (X(21.1), 16.0, zc, 0.85, hz * 0.8),
               (X(21.3), 16.0, zc, 1.02, hz), (X(26.7), 16.0, zc, 1.02, hz), (X(26.9), 16.0, zc, 0.85, hz * 0.8),
               (X(26.95), 16.0, zc, 0.0, 0.0)], ["lens"] * 5, n=20)


def recolour_spine_top(obj):
    """The spine block's upward faces take 89, its chamfers 90, its sides stay 88."""
    me = obj.data
    s_side, s_top, s_ch = SLOTS["spine_side"], SLOTS["spine"], SLOTS["spine_ch"]
    s_h, s_hch = SLOTS["hatch"], SLOTS["hatch_ch"]
    for p in me.polygons:
        if p.material_index == s_h and 0.4 < p.normal.z < 0.95:
            p.material_index = s_hch  # the hatch's chamfered rim catches light: the sprite's 91-92 edge
        if p.material_index != s_side:
            continue
        nz = p.normal.z
        if nz > 0.95:
            p.material_index = s_top
        elif nz > 0.45 and p.normal.y > -0.2 and abs(p.normal.x) > 0.3:
            p.material_index = s_ch


def build():
    coll = common.reset_collection(NAME + "_A")
    P = T.Part(NAME, smooth_angle=35.0)
    for m in (False, True):
        tank(P, m)
        radiator(P, m)
    boom(P)
    spine(P)
    lamp(P)
    obj = T.finish(P, MATS, coll)
    obj.data.transform(Matrix.Translation((0, 0, -Z0 / 12)))
    recolour_spine_top(obj)
    return obj, coll


def split_open(obj, layout, coll):
    """split_assembly's cut without capping (for the outline shell: no ink line at the seam)."""
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


def main():
    sprite = load_sprite()
    make_materials(sprite)
    obj, coll = build()
    T.cull_hidden(obj)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(obj)
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=5000, smooth=6, inside=0.01)
    data0 = common.load_sprite(ROOT, PIECES[0])
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in data0["assemblyLayout"] if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll)
    for name, cx, cy in layout:
        pc = pieces[name]
        pc.data.shade_smooth()
        pc.data.set_sharp_from_angle(angle=math.radians(35.0))
        wn = pc.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pc, shells[name]], f"enemies/{name}", data["sprites"])
        pc.data.calc_loop_triangles()
        print(f"piece {name}: {len(pc.data.loop_triangles)} triangles, outline {len(shells[name].data.polygons)} faces")


if __name__ == "__main__":
    main()
