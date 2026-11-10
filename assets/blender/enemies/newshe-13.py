"""newshe-13, the belted orb as a machined two-shell sphere girdled by a red drive belt.

Reading of the sprite (newshe.shp 13/15/17, 24x28 block, the ball 18x17 px at columns 3-20, rows
5-21, no ink ring so the inner mask is the whole sprite): a round steel-blue ball lit from the
upper left (the 61-63 spot is sheen on a glossy round surface, the 59-62 crescent low right is a
reflected rim: lighting, not paint or bumps), girdled across its middle (rows 12-14) by a red-orange
band whose middle row is the brightest. Seen from above the band runs across the ball, so in 3D it
is a ring round the flight (Y) axis: it goes over the top and under the belly. The frames only dim
the band two palette steps a frame; one model covers them all with frame colours (D17).

Design (balance of sprite, game camera and engineering):
- Hull: two hemispherical steel shells (a revolve round Y of the sprite's fitted ellipse, half
  sizes 9 x 8.5 px, squat in Z), each with a fine latitude panel groove and four meridian seams on
  the diagonals, and a machined hub cap at its pole (front and rear) with a ring groove, a raised
  hub and six bolt heads. The poles face front and rear, where the tilted game camera sees them.
- Belt: a drive ring seated in a shadow gap between the shells: two chamfered red flanges (rows 12
  and 14) and between them a recessed channel (row 13, the band's brightest row) divided into cells
  by 12 short ribs.
- Colour (median of each part's pixels without the darkest 53-54 and brightest 61-63 steps): the
  north shell 57, the south shell 56, the north flange 120 (frames 15: 118, 17: 116), the south
  flange 119 (117 / 115), the channel 123 (121 / 119), the ribs one step under the flanges.
  All satin metal, belt included: NO emission (an emissive belt read as a lamp, not a painted band;
  the frames' dimming is carried by the frame colours alone).
- Texture: AO/roughness bake only (usp_talon.bake_maps), no concept projection.
- Outline shell (D51) from a sealed proxy, not from the model: the plain revolve (same A/B/C, no
  shadow gap, seams or grooves, the belt a smooth 1.6% swell over the flanges) with the pole hubs,
  no bolts or ribs, held 0.003 inside the proxy (D90, D118). Remeshed from the model itself the
  shell dipped into the 5%-deep shadow gaps and its back faces drew black dashes along the belt.
- Underside: the same closed revolve; nothing added there.

Run: blender --background --python assets/blender/enemies/newshe-13.py [-- --no-bake]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshe-13"
PX = 1 / 12
GW, GH = 24, 28

# --- the ball (sprite px; x right, y north, z up; origin = the 24x28 block's centre) ------------
CX, CYR = 12.0, 13.5        # ball centre: column edge 12, row 13.5 (rows 5..21 inclusive)
RA, RB = 9.0, 8.5           # half width (columns 3-20) and half length (rows 5-21), px
RC = 5.4                    # half height, px: a squat ball (flying enemy height)
SIDES = 40                  # ring samples round Y
BELT = 1.5                  # belt half width, px (rows 12-14)
GAP = 0.20                  # shadow gap between shell and flange, px
FLANGE_IN = 0.5             # flange / channel boundary, px from the centre line
LAT = 0.56                  # latitude panel groove at this fraction of the half length
SEAMS = (45.0, 135.0, 225.0, 315.0)   # meridian seams, degrees round Y (0 = +X, 90 = top)
SEAM_W, SEAM_D = 1.6, 0.012  # seam half width (degrees) and depth (fraction of radius)
GROOVE_D = 0.014             # latitude groove depth (fraction)
CAP_T = 0.80                 # hub cap ring groove at |t| = this (fraction of half length)
RIBS = 12


def X(c):
    return (c - GW / 2) * PX


def Y(r):
    return (GH / 2 - r) * PX


A, B, C = RA * PX, RB * PX, RC * PX
YC = Y(CYR)


def ell_s(t):
    return math.sqrt(max(0.0, 1.0 - t * t))


def angle_list():
    """Ring angles: uniform plus three samples per meridian seam so the seams cut crisply."""
    angs = [360.0 * (i + 0.5) / SIDES for i in range(SIDES)]
    for s in SEAMS:
        angs += [s - SEAM_W, s, s + SEAM_W]
    angs = sorted(set(round(a % 360.0, 4) for a in angs))
    out = []
    for a in angs:  # drop uniform samples crowding a seam sample
        if out and a - out[-1] < 0.8:
            if any(abs(a - s) < 1e-3 or abs(a - s - SEAM_W) < 1e-3 or abs(a - s + SEAM_W) < 1e-3 for s in SEAMS):
                out[-1] = a
            continue
        out.append(a)
    return out


def seam_k(ang):
    for s in SEAMS:
        if abs(((ang - s + 180) % 360) - 180) < 1e-3:
            return 1.0 - SEAM_D
    return 1.0


def stations():
    """(t, k, seams, mat) per station along Y, t = (y - YC) / B from -1 (south pole) to 1."""
    st = []
    tb = BELT / RB
    tg = (BELT + GAP) / RB
    # shells: cos-spaced stations from the belt gap out to the hub cap groove, and the cap
    def shell(sign, mat):
        t0 = tg + 0.6 / RB
        t1 = CAP_T - 0.012
        n = 6
        pts = [(t0 + (t1 - t0) * i / n, 1.0, True) for i in range(n + 1)]
        pts = [p for p in pts if abs(p[0] - LAT) > 0.03]
        # latitude panel groove
        pts += [(LAT - 0.018, 1.0, True), (LAT - 0.010, 1 - GROOVE_D, True),
                (LAT + 0.010, 1 - GROOVE_D, True), (LAT + 0.018, 1.0, True)]
        # hub cap: a ring groove, then the cap dome out to the hub foot at the pole
        pts += [(CAP_T, 0.975, False), (CAP_T + 0.014, 0.975, False), (CAP_T + 0.022, 1.0, False)]
        pts += [(t, 1.0, False) for t in (0.90, 0.955)]
        pts.sort()
        return [(sign * t, k, sm, mat) for t, k, sm in pts]

    north = shell(1, "N")
    south = shell(-1, "S")
    # shell lip at the belt gap, the gap floor, the flanges and the glowing channel
    belt = []
    for sign, sh, fl in ((1, "N", "FN"), (-1, "S", "FS")):
        for t, k, m in (((BELT + GAP + 0.6) / RB, 1.0, sh), ((BELT + GAP + 0.08) / RB, 0.995, sh),
                        ((BELT + GAP) / RB, 0.95, "GAP"), ((BELT + 0.02) / RB, 0.95, "GAP"),
                        (BELT / RB, 0.985, fl), ((BELT - 0.12) / RB, 1.012, fl),
                        ((FLANGE_IN + 0.12) / RB, 1.012, fl), ((FLANGE_IN + 0.02) / RB, 0.995, fl),
                        (FLANGE_IN / RB, 0.975, "CORE")):
            belt.append((sign * t, k, False, m))
    belt.append((0.0, 0.975, False, "CORE"))
    st = sorted(north + south + belt, key=lambda p: p[0])
    # remove duplicate t
    out = []
    for p in st:
        if out and abs(p[0] - out[-1][0]) < 1e-5:
            continue
        out.append(p)
    return out


def materials(sprite):
    pal = common.palette_material
    m = {
        "N": pal(sprite, 57, NAME, metallic=0.5, roughness=0.3),
        "S": pal(sprite, 56, NAME, metallic=0.5, roughness=0.3),
        "GAP": pal(sprite, 53, NAME, metallic=0.4, roughness=0.55),
        "HUB": pal(sprite, 55, NAME, metallic=0.55, roughness=0.32),
        "FN": pal(sprite, 120, f"{NAME}_flange_n", metallic=0.8, roughness=0.5,
                  frames={15: 118, 17: 116}),
        "FS": pal(sprite, 119, f"{NAME}_flange_s", metallic=0.8, roughness=0.5,
                  frames={15: 117, 17: 115}),
        "CORE": pal(sprite, 123, f"{NAME}_core", metallic=0.8, roughness=0.55,
                    frames={15: 121, 17: 119}),
        "RIB": pal(sprite, 118, f"{NAME}_rib", metallic=0.8, roughness=0.5,
                   frames={15: 116, 17: 114}),
    }
    order = ["N", "S", "GAP", "HUB", "FN", "FS", "CORE", "RIB"]
    return [m[k] for k in order], {k: i for i, k in enumerate(order)}


def revolve(bm, slots, bolts=True):
    angs = angle_list()
    st = stations()
    rings = []
    for t, k, sm, mat in st:
        y = YC + B * t
        s = ell_s(t)
        ring = []
        for a in angs:
            kk = k * (seam_k(a) if sm else 1.0)
            r = math.radians(a)
            ring.append(bm.verts.new((A * s * kk * math.cos(r), y, C * s * kk * math.sin(r))))
        rings.append(ring)
    n = len(angs)
    faces = []
    for (r0, r1, p0, p1) in zip(rings, rings[1:], st, st[1:]):
        # face material: the station pair's inner one decides (belt pieces own their span)
        mat = p1[3] if p0[0] < 0 else p0[3]
        if p0[0] < 0 <= p1[0]:
            mat = "CORE"
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = slots[mat if mat in slots else "N"]
            faces.append(f)
    # pole hubs: close each end with a raised hub (pal 55) and bolt heads
    for end, sign in ((rings[-1], 1), (rings[0], -1)):
        t = st[-1][0] if sign > 0 else st[0][0]
        y = YC + B * t
        ctr = Vector((0.0, y, 0.0))
        # hub: a short step out along Y, then a flat face
        top = [bm.verts.new((v.co.x * 0.92, y + sign * 0.022, v.co.z * 0.92)) for v in end]
        top2 = [bm.verts.new((v.co.x * 0.80, y + sign * 0.030, v.co.z * 0.80)) for v in end]
        for i in range(n):
            j = (i + 1) % n
            q = (end[i], end[j], top[j], top[i]) if sign > 0 else (end[j], end[i], top[i], top[j])
            bm.faces.new(q).material_index = slots["HUB"]
            q = (top[i], top[j], top2[j], top2[i]) if sign > 0 else (top[j], top[i], top2[i], top2[j])
            bm.faces.new(q).material_index = slots["HUB"]
        cap = bm.faces.new(top2 if sign > 0 else list(reversed(top2)))
        cap.material_index = slots["HUB"]
        if not bolts:
            continue
        # six bolt heads round the hub face
        rh = (top2[0].co.x ** 2 + top2[0].co.z ** 2) ** 0.5
        rx = max(abs(v.co.x) for v in top2)
        rz = max(abs(v.co.z) for v in top2)
        for b in range(6):
            a = 2 * math.pi * (b + 0.5) / 6
            bolt(bm, (rx * 0.62 * math.cos(a), y + sign * 0.030, rz * 0.62 * math.sin(a)), sign, slots["N"])
        # a lens at the very centre
        bolt(bm, (0.0, y + sign * 0.030, 0.0), sign, slots["GAP"], r=0.05, h=0.012, sides=16)
    return faces


def bolt(bm, p, sign, mat, r=0.014, h=0.008, sides=8):
    x, y, z = p
    lo, hi = [], []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        lo.append(bm.verts.new((x + r * math.cos(a), y - sign * 0.004, z + r * math.sin(a))))
        hi.append(bm.verts.new((x + r * 0.8 * math.cos(a), y + sign * h, z + r * 0.8 * math.sin(a))))
    for i in range(sides):
        j = (i + 1) % sides
        q = (lo[i], lo[j], hi[j], hi[i]) if sign > 0 else (lo[j], lo[i], hi[i], hi[j])
        bm.faces.new(q).material_index = mat
    bm.faces.new(hi if sign > 0 else list(reversed(hi))).material_index = mat
    bm.faces.new(list(reversed(lo)) if sign > 0 else lo).material_index = mat


def ribs(bm, slots):
    """Short radial ribs across the glowing channel, dividing it into cells."""
    w = 0.9 * FLANGE_IN * PX  # along Y, just inside the flanges
    s = ell_s(0.0)
    for i in range(RIBS):
        a = 2 * math.pi * (i + 0.5) / RIBS
        # point on the channel surface and its outward normal of the ellipse (x/A^2, z/C^2)
        px, pz = A * 0.975 * math.cos(a), C * 0.975 * math.sin(a)
        nrm = Vector((px / A ** 2, 0, pz / C ** 2)).normalized()
        tan = Vector((-nrm.z, 0, nrm.x))
        base = Vector((px, YC, pz)) - nrm * 0.01
        hw = 0.008
        h = 0.028  # a little under the flange tops
        corners = []
        for dy in (-w, w):
            for dt in (-hw, hw):
                for dh in (0.0, h):
                    corners.append(base + Vector((0, dy, 0)) + tan * dt * (0.75 if dh else 1.0) + nrm * dh)
        vs = [bm.verts.new(c) for c in corners]
        # index = dy*4 + dt*2 + dh
        quads = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (1, 3, 7, 5), (0, 4, 6, 2)]
        for q in quads:
            f = bm.faces.new([vs[k] for k in q])
            f.material_index = slots["RIB"]


def split_sharp(bm, deg=34.0):
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(deg)]
    bmesh.ops.split_edges(bm, edges=edges)


def proxy_stations():
    """The shell proxy's stations: the shells' t from stations() with k = 1 (no seams, grooves or
    gap), and over the belt a smooth swell to 1.016 so the shell covers the flange tops (1.012)."""
    tw = (BELT + GAP + 0.6) / RB
    out = []
    for t, k, sm, mat in stations():
        if abs(t) < tw:
            k = 1.0 + 0.016 * math.cos(0.5 * math.pi * abs(t) / tw) ** 2
        else:
            k = 1.0  # the hub cap's ring groove too
        out.append((t, k, False, "N"))
    return out


def shell_proxy(coll, slots):
    """A sealed, crease-free stand-in for the outline shell (see the docstring)."""
    global stations
    real = stations
    st = proxy_stations()
    stations = lambda: st  # noqa: E731
    try:
        bm = bmesh.new()
        revolve(bm, slots, bolts=False)
    finally:
        stations = real
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return common.mesh_object(f"{NAME}_proxy", bm, [], coll, smooth=True)


def build(coll, sprite):
    mats, slots = materials(sprite)
    bm = bmesh.new()
    revolve(bm, slots)
    ribs(bm, slots)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    split_sharp(bm)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return obj, mats, slots


def bake_maps(obj, out_dir, textured, size=512, samples=64):
    tint, tex = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = (0.94, 0.97, 1.0), tuple(textured)
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, tex


def main():
    import tempfile
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, NAME)
    coll = common.reset_collection(NAME)
    obj, mats, slots = build(coll, sprite)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = Path(tempfile.mkdtemp(prefix="newshe13_bake_"))
        bake_maps(obj, bake_dir, [slots[k] for k in ("N", "S", "GAP", "HUB", "FN", "FS", "RIB")])
        fmt = "WEBP"
    proxy = shell_proxy(coll, slots)
    shell = common.outline_shell(proxy, coll, voxel=0.01, faces=1600, smooth=6, inside=0.003)
    bpy.data.objects.remove(proxy, do_unlink=True)
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces (from the sealed proxy)")
    shell.name = shell.data.name = f"{NAME}_outline"
    common.export_sprite_model(root, [obj, shell], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
