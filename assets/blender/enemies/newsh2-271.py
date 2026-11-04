"""Grey rail pod (newsh2.shp frame 271, 24x28 px, enemy type 25, flies sideways nose to the screen
left): a hard-surface machine that is its sprite in 3D (the treatment of the player ships, PR #84 /
D50-D53).

Seen in episode 1 (levels 1.28, 1.30, 1.36) and episode 3. One frame (271), one model.

A round, bullet-shaped steel pod (a nose cap with a dark sensor tip, split from the body by a seam
groove), a raised rib band ahead of a sensor bay sunk in its top (cooling fins, a dark housing, two
red glass lenses with hot orange cores, a grey rear bulkhead), a small brass plaque on the spine, a
brown armour collar wrapped round its rear flanks, and a round engine (flange, ribbed drum, groove,
a deep nozzle with an orange glow). Two railgun rails ride beside it (screen-top and screen-bottom),
each a dark chamfered bar with a light conductor bar in a groove and a bored muzzle, carried by a
brown cranked arm out to the tail and a dark strut through the engine.

The sprite is authoritative (D52, the user's rule; tools/calibration/rubric.md):
- Plan: the top-view edge goes to the INNER edge of the sprite's ink border (D74,
  docs/agents/OUTLINE-BORDER.md): body half width 6.5 px, a pchip nose, a 45 degree rear taper to the
  3.5 px engine, the rails one colour pixel wide (inner row 3, border pixels free) and the arm and
  strut following the inner mask's steps. Mirror plane row edge 13.5.
- Features: the bay, lenses, plaque, collar, engine, struts, arms and rails sit on their pixels.
- Colours: every part takes the palette index of the sprite pixels it covers (trimmed medians:
  nose 5, hull 6, collar 167, bay 4, lip 7, lens 119, core 121, plaque 26, drum 8, nozzle 10, arm
  23, rail 4, conductor 7). Satin metal. Bright sprite pixels are sheen, not modelled bumps.
- Underside: the closed hull of revolution, no detailing.

Built in sprite px (x = column edge, y = row edge, z up, pod axis at y 13.5, z 0), moved to Blender
at the end (X = (x - 12) / 12, Y = (14 - y) / 12, Z = z / 12). Panel lines and recesses are real
cuts (exact booleans).

Texture: no concept projection (its maps.json says "bake": "model", D50). Cycles bakes a colour
multiplier (ambient occlusion, edge lift) and a roughness/metalness map (usp_talon.bake_maps) to
assets/blender/textures/newsh2-271/bake/; Base Color = map x palette colour, so pal_<index>, fades
and the hit flash apply; the lenses and the nozzle glow keep their flat emissive colours. Exported
beside it: an outline shell (common.outline_shell, D51) and `tyrian_engines` (the nozzle).

Run: blender --background --factory-startup --python assets/blender/enemies/newsh2-271.py
     [-- --preview out.png] [--no-bake] [--out x.glb]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (pchip, cull_hidden, bake_maps)

NAME = "newsh2-271"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
AY = 13.5  # mirror row edge / pod axis
SEGS = 32

# Material slots and their palette indices (trimmed medians of the sprite pixels each part covers).
(NOSE, HULL, COLLAR, LINE, BAY, LIP, LENS, CORE, PLATE, DRUM, NOZZLE, DEEP, ARM_M, RAIL, INSERT,
 POST, GLOW) = range(17)
SLOTS = [
    # slot: (pal, tag, metallic, roughness, emission)
    (5, "nose", 0.25, 0.38, 0),
    (6, "hull", 0.25, 0.4, 0),
    (167, "collar", 0.25, 0.45, 0),
    (3, "line", 0.2, 0.7, 0),
    (4, "bay", 0.35, 0.5, 0),
    (7, "lip", 0.3, 0.35, 0),
    (119, "lens", 0.0, 0.08, 2.2),
    (121, "core", 0.0, 0.2, 3.0),
    (26, "plate", 0.35, 0.35, 0),
    (8, "drum", 0.3, 0.32, 0),
    (10, "nozzle", 0.35, 0.28, 0),
    (2, "deep", 0.1, 0.8, 0),
    (23, "arm", 0.25, 0.45, 0),
    (4, "rail", 0.25, 0.42, 0),
    (7, "insert", 0.35, 0.3, 0),
    (4, "bolt", 0.25, 0.42, 0),
    (121, "glow", 0.0, 0.4, 1.4),
]


def materials(sprite):
    out = []
    for pal, tag, met, rough, em in SLOTS:
        out.append(common.palette_material(sprite, pal, f"{NAME}_{tag}", metallic=met, roughness=rough,
                                           emission_strength=em))
    return out


# --- helpers in sprite px -------------------------------------------------------------------------

def frange(a, b, step):
    n = max(1, int(math.ceil((b - a) / step - 1e-9)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def ring_pt(x, r, th, cy=AY, cz=0.0):
    """Point at radius r, angle th (0 = top, +90 deg = screen-bottom side) around the pod axis."""
    return (x, cy + r * math.sin(th), cz + r * math.cos(th))


def revolve(bm, prof, segs=SEGS, cy=AY, cz=0.0, smooth=True):
    """Closed surface of revolution about the x axis line (cy, cz). prof: [(x, r, mat)], the mat of
    the band from this station to the next. r = 0 closes to a point; otherwise the ends get caps."""
    ths = [2 * math.pi * i / segs for i in range(segs)]
    rings = []
    for x, r, _ in prof:
        if r <= 1e-6:
            rings.append([bm.verts.new((x, cy, cz))])
        else:
            rings.append([bm.verts.new(ring_pt(x, r, t, cy, cz)) for t in ths])
    faces = []
    for i in range(len(prof) - 1):
        a, b, m = rings[i], rings[i + 1], prof[i][2]
        if len(a) == 1 and len(b) == 1:
            continue
        for j in range(segs):
            k = (j + 1) % segs
            if len(a) == 1:
                f = bm.faces.new((a[0], b[j], b[k]))
            elif len(b) == 1:
                f = bm.faces.new((a[j], a[k], b[0]))
            else:
                f = bm.faces.new((a[j], a[k], b[k], b[j]))
            f.material_index = m
            f.smooth = smooth
            faces.append(f)
    for ring, m in ((rings[0], prof[0][2]), (rings[-1], prof[-2][2])):
        if len(ring) > 1:
            f = bm.faces.new(ring)
            f.material_index = m
            f.smooth = False
            faces.append(f)
    return faces


def hull_pts(bm, pts, mat, smooth=False):
    """Convex hull of points (chamfered blocks), coplanar faces merged."""
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    live = [v for v in verts if v.is_valid]
    for f in {f for v in live for f in v.link_faces}:
        f.material_index = mat
        f.smooth = smooth


def cbox(x0, x1, y0, y1, z0, z1, ch, chz=None):
    chz = ch if chz is None else chz
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            for z, sz in ((z0, 1), (z1, -1)):
                pts += [(x + sx * ch, y, z + sz * chz), (x, y + sy * ch, z + sz * chz), (x + sx * ch, y + sy * ch, z)]
    return pts


def block(bm, x0, x1, y0, y1, z0, z1, ch, mat, chz=None):
    hull_pts(bm, cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


def prism(bm, poly, z0, z1, mat, bevel=0.0):
    """Extruded polygon (any simple outline, (x, y) in px), top edges chamfered by `bevel`."""
    bot = [bm.verts.new((x, y, z0)) for x, y in poly]
    top = [bm.verts.new((x, y, z1)) for x, y in poly]
    fb = bm.faces.new(list(reversed(bot)))
    ft = bm.faces.new(top)
    n = len(poly)
    sides = [bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i])) for i in range(n)]
    for f in [fb, ft] + sides:
        f.material_index = mat
        f.smooth = False
    if bevel > 0:
        bmesh.ops.recalc_face_normals(bm, faces=[fb, ft] + sides)
        edges = list(ft.edges)
        bmesh.ops.bevel(bm, geom=edges + list(ft.verts), offset=bevel, offset_type="OFFSET", segments=1,
                        profile=0.5, affect="EDGES", clamp_overlap=True)


def tube_y(bm, x, z, y0, y1, rx, rz, mat, sides=12):
    """Rounded bar along y (an elliptic section), capped."""
    rings = []
    for y in (y0, y1):
        rings.append([bm.verts.new((x + rx * math.cos(2 * math.pi * i / sides), y,
                                    z + rz * math.sin(2 * math.pi * i / sides))) for i in range(sides)])
    fs = [bm.faces.new((rings[0][i], rings[0][(i + 1) % sides], rings[1][(i + 1) % sides], rings[1][i]))
          for i in range(sides)]
    fs += [bm.faces.new(rings[0]), bm.faces.new(list(reversed(rings[1])))]
    for f in fs:
        f.material_index = mat
        f.smooth = f in fs[:sides]


def disc_z(bm, x, y, z0, z1, r, mat, sides=10, ch=0.08):
    """Bolt head / pin cap: a short chamfered cylinder along z."""
    pts = []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        for rr, zz in ((r, z0), (r, z1 - ch), (r - ch, z1)):
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a), zz))
    hull_pts(bm, pts, mat)


def sweep_cutter(bm, stations, mat):
    """Closed sweep through stations of 4-point sections (lists of 4 points)."""
    rings = [[bm.verts.new(p) for p in sec] for sec in stations]
    fs = []
    for a, b in zip(rings, rings[1:]):
        for j in range(4):
            k = (j + 1) % 4
            fs.append(bm.faces.new((a[j], a[k], b[k], b[j])))
    fs.append(bm.faces.new(rings[0]))
    fs.append(bm.faces.new(list(reversed(rings[-1]))))
    for f in fs:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=fs)


def long_cut(bm, rfun, x0, x1, th, mat, w=0.32, depth=0.3, step=0.9):
    """Cutter for a lengthwise groove on the pod at angle th, following its radius."""
    secs = []
    for x in frange(x0, x1, step):
        r = rfun(x)
        sec = []
        for t, rho in ((-w / 2, r - depth), (w / 2, r - depth), (w / 2, r + 1.5), (-w / 2, r + 1.5)):
            sec.append((x, AY + rho * math.sin(th) + t * math.cos(th), rho * math.cos(th) - t * math.sin(th)))
        secs.append(sec)
    sweep_cutter(bm, secs, mat)


def ring_cut(bm, rfun, x, th0, th1, mat, w=0.32, depth=0.3, steps=10):
    """Cutter for a ring groove at x over angles th0..th1."""
    xa, xb = x - w / 2, x + w / 2
    secs = []
    for i in range(steps + 1):
        t = th0 + (th1 - th0) * i / steps
        secs.append([ring_pt(xa, rfun(xa) - depth, t), ring_pt(xb, rfun(xb) - depth, t),
                     ring_pt(xb, rfun(xb) + 1.5, t), ring_pt(xa, rfun(xa) + 1.5, t)])
    sweep_cutter(bm, secs, mat)


def to_obj(name, bm, mats, coll):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def cut(target, cutter_bm, mats, coll):
    """target (object) minus the cutters (exact boolean, the cut faces take the cutters' materials)."""
    c = to_obj(target.name + "_cut", cutter_bm, mats, coll)
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = c
    mod.material_mode = "TRANSFER"
    mod.use_hole_tolerant = True
    mod.use_self = True
    dg = bpy.context.evaluated_depsgraph_get()
    ev = target.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = target.data
    target.modifiers.clear()
    target.data = me
    bpy.data.meshes.remove(old)
    cme = c.data
    bpy.data.objects.remove(c)
    bpy.data.meshes.remove(cme)
    return target


# --- the pod ---------------------------------------------------------------------------------------

# Plan outline (half width by column edge, px), fitted to the sprite mask (dark outline pixels
# included, the hitbox read) row by row: a blunt round nose widening to the seam at column 7, the
# body at 7.3 px, the collar a touch proud, rounding down to the engine at column 19.
NOSE_X = [0.0, 0.5, 1.0, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.2]
NOSE_R = [0.35, 0.65, 1.05, 1.5, 2.5, 3.45, 3.95, 4.4, 4.8, 5.55, 6.3, 6.5]
NOSEF = T.pchip(NOSE_X, NOSE_R)

# (x, r, mat of the band that follows)
def pod_profile():
    """The pod core: sensor tip, nose cap, seam groove, a seam ring band (pal 5, the sprite's column
    7), the body with a raised rib band ahead of the bay; under the collar it tapers to the engine."""
    p = []
    for x in frange(0.0, 0.5, 0.25)[:-1]:
        p.append((x, NOSEF(x), BAY))  # dark sensor tip
    for x in [0.5, 0.9, 1.5, 2.2, 3.0, 3.9, 4.9, 6.0, 6.95]:
        p.append((x, NOSEF(x), NOSE))
    p[-1] = (6.95, NOSEF(6.95), LINE)
    F = lambda x: NOSEF(min(x, 9.2))  # noqa: E731  (the body envelope)
    p += [
        (6.95, F(6.95) - 0.45, LINE), (7.2, F(7.2) - 0.45, NOSE),               # seam groove
        (7.2, F(7.2), NOSE), (7.35, F(7.35) + 0.12, NOSE), (7.85, F(7.85) + 0.12, NOSE),  # seam ring band
        (7.95, F(7.95) - 0.05, LINE),
        (8.1, F(8.1) - 0.05, HULL), (8.15, F(8.15), HULL), (8.6, F(8.6), HULL), (9.3, 6.5, HULL),
        (10.85, 6.5, HULL),                               # rib band ahead of the bay
        (10.95, 6.65, HULL), (11.85, 6.65, HULL), (11.95, 6.5, HULL),
        (16.5, 6.5, HULL), (17.5, 5.5, HULL), (18.5, 4.5, HULL), (19.0, 4.0, HULL), (19.0, 0.0, HULL),
    ]
    return p


COLLAR_REAR = [(16.4, 6.65), (16.8, 6.3), (17.5, 5.65), (18.5, 4.65), (18.95, 4.15), (19.1, 3.9)]


def collar_front(th):
    """Where the collar's front edge is at angle th: swept back over the top (the sprite's collar
    starts at column 14 low on the flanks and column 15-16 beside the bay)."""
    c = math.cos(th)
    return 14.0 + 2.1 * max(0.0, (c - 0.6) / 0.4) ** 1.3


def collar_shell(bm, segs=SEGS):
    """The brown armour collar, a shell 0.28 px proud of the body with a chamfered, swept front edge;
    closed inside the body (hidden, culled later)."""
    ths = [2 * math.pi * i / segs for i in range(segs)]
    cols = []
    for t in ths:
        xf = collar_front(t)
        st = [(xf, 6.3), (xf, 6.5), (xf + 0.15, 6.65)] + COLLAR_REAR
        cols.append([bm.verts.new(ring_pt(x, r, t)) for x, r in st])
    front = bm.verts.new((13.9, AY, 0.0))
    rear = bm.verts.new((19.1, AY, 0.0))
    n = len(cols[0])
    for j in range(segs):
        k = (j + 1) % segs
        for i in range(n - 1):
            f = bm.faces.new((cols[j][i], cols[j][i + 1], cols[k][i + 1], cols[k][i]))
            f.material_index = COLLAR
            f.smooth = True
        for f in (bm.faces.new((front, cols[k][0], cols[j][0])), bm.faces.new((rear, cols[j][-1], cols[k][-1]))):
            f.material_index = COLLAR
            f.smooth = False


def rlin(prof):
    xs = [p[0] for p in prof]
    def f(x):
        best = 0.0
        for (xa, ra, _), (xb, rb, _) in zip(prof, prof[1:]):
            if xa <= x <= xb and xb > xa:
                best = max(best, ra + (rb - ra) * (x - xa) / (xb - xa))
        return best
    return f


def build_pod(mats, coll):
    bm = bmesh.new()
    prof = pod_profile()
    revolve(bm, prof)
    collar_shell(bm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    pod = to_obj("pod", bm, mats, coll)
    bm.free()
    rb = rlin(prof)
    rc = rlin([(14.0, 6.65, 0)] + [(x, r, 0) for x, r in COLLAR_REAR])
    R = lambda x: max(rb(x), rc(x))  # noqa: E731
    c = bmesh.new()
    # Sensor bay: a recess in the top, columns 12-18 (sprite rows 11-15).
    block(c, 12.05, 18.15, 11.1, 15.3, 3.7, 10.0, 0.0, BAY)
    # Nose: a ring line at column 3.6 and two lengthwise lines over the top.
    ring_cut(c, R, 3.6, -1.75, 1.75, LINE, w=0.28, depth=0.25)
    for s in (-1, 1):
        long_cut(c, R, 3.8, 6.8, s * 0.9, LINE, w=0.26, depth=0.25)
        # Body: the spine strip's edges (sprite rows 12 and 14, columns 7-10) and the flank lines.
        long_cut(c, R, 7.6, 10.75, s * 0.2, LINE, w=0.26, depth=0.25)
        long_cut(c, R, 7.7, 13.6, s * 1.15, LINE, w=0.3, depth=0.3)
        # Collar joints over the flanks.
        long_cut(c, R, 14.3, 18.0, s * 0.95, LINE, w=0.3, depth=0.3)
        # Vent slots behind the seam on each side (seen from the sides and the game camera).
        for k in range(3):
            th = s * (1.45 + 0.17 * (k - 1))
            long_cut(c, R, 7.75, 8.95, th, DEEP, w=0.2, depth=0.35, step=0.6)
    # Ring line on the body behind the rib band, top half only.
    ring_cut(c, R, 12.9, -1.9, -0.45, LINE, w=0.26, depth=0.25)
    ring_cut(c, R, 12.9, 0.45, 1.9, LINE, w=0.26, depth=0.25)
    cut(pod, c, mats, coll)
    c.free()
    # The bay floor takes the bay colour; its walls stay dark line.
    for f in pod.data.polygons:
        cx, cy, cz = f.center
        if 12.0 < cx < 18.2 and 11.0 < cy < 15.4 and cz > 3.6 and f.normal.z > 0.9 and abs(cz - 3.7) < 0.05:
            f.material_index = BAY
    return pod


def build_bay(bm):
    """The sensor bay's contents: cooling fins, a dark housing, two red lenses with orange cores,
    a divider, and the grey rear bulkhead (the sprite's column 18)."""
    for x0 in (12.45, 13.3):
        block(bm, x0, x0 + 0.4, 11.35, 15.05, 3.6, 5.15, 0.08, LINE)
    block(bm, 14.15, 18.05, 11.55, 15.05, 3.6, 4.8, 0.15, BAY)
    for x0, x1 in ((15.0, 15.98), (17.02, 17.98)):
        block(bm, x0, x1, 12.0, 15.0, 4.5, 5.4, 0.22, LENS)
        block(bm, x0 + 0.12, x1 - 0.12, 13.0, 14.0, 5.2, 5.6, 0.12, CORE)
    block(bm, 16.05, 16.95, 11.75, 15.05, 4.5, 5.4, 0.12, NOSE)
    # Rear bulkhead: a raised grey frame across the bay's back edge.
    pts = []
    for y, ch in ((10.95, 1), (15.95, -1)):
        for x, zt in ((17.98, 5.9), (18.95, 4.9)):
            pts += [(x, y, 2.9), (x, y + ch * 0.2, zt), (x + (0.18 if x < 18.5 else -0.18), y + ch * 0.2, zt),
                    (x + (0.18 if x < 18.5 else -0.18), y, zt - 0.18), (x, y, zt - 0.18)]
    hull_pts(bm, pts, LIP)
    # Front sill under the rib band.
    block(bm, 11.75, 12.2, 11.0, 15.6, 3.7, 6.35, 0.1, HULL)


def build_plate(bm):
    """The brass plaque on the spine (sprite columns 9-11, row 13) and its two rivets."""
    block(bm, 9.0, 11.85, 12.95, 14.05, 5.7, 6.85, 0.16, PLATE)
    for x in (9.35, 11.45):
        disc_z(bm, x, 13.5, 6.75, 7.0, 0.18, NOSE, sides=8, ch=0.06)


def build_engine(bm):
    prof = [
        (18.9, 0.0, DRUM), (18.9, 3.4, DRUM), (19.05, 3.55, DRUM), (19.75, 3.55, DRUM), (19.9, 3.4, DRUM),
        (19.9, 3.3, DRUM), (20.05, 3.45, DRUM), (20.25, 3.55, DRUM), (20.45, 3.45, DRUM), (20.65, 3.55, DRUM),
        (20.85, 3.45, DRUM), (21.0, 3.45, BAY),
        (21.0, 3.15, BAY), (21.9, 3.15, NOZZLE),               # dark groove
        (21.9, 3.25, NOZZLE), (22.05, 3.5, NOZZLE), (23.0, 3.5, NOZZLE), (23.3, 3.0, NOZZLE),
        (24.0, 2.85, NOZZLE),
        (24.0, 2.45, DEEP),                                  # lip, then the deep inner wall
        (23.7, 2.4, DEEP), (22.7, 2.1, GLOW), (22.5, 1.9, GLOW), (22.5, 1.45, BAY),
        (23.0, 1.3, BAY), (23.45, 0.7, BAY), (23.6, 0.0, BAY),          # exhaust plug
    ]
    revolve(bm, prof, segs=24)


def build_rail(bm):
    """The rail: a dark chamfered bar one colour pixel wide (inner row 3, its ink rows 2 and 4 are
    free pixels), columns 8.5-20 (screen-top one)."""
    block(bm, 8.5, 20.0, 2.65, 4.35, -1.1, 1.3, 0.3, RAIL)


def rail_cutters(bm):
    block(bm, 9.0, 16.35, 2.95, 4.05, 0.5, 3.0, 0.0, DEEP)    # groove for the conductor bar
    block(bm, 7.5, 9.4, 3.1, 3.9, -0.5, 0.5, 0.0, DEEP)       # bored muzzle
    block(bm, 9.5, 15.0, 2.4, 2.8, -0.3, 0.3, 0.0, DEEP)      # slot down the outer side
    for i in range(4):                                         # vent louvres at its rear
        x = 15.7 + 0.6 * i
        block(bm, x, x + 0.3, 2.4, 2.85, -0.7, 0.7, 0.0, DEEP)


# The arm and strut: the inner mask's steps (rows 4-9, a diagonal from the rail's end out to column 24,
# then down to the engine drum), convex corners trimmed a little.
ARM_POLY = [(17.5, 4.0), (20.0, 4.0), (20.0, 4.9), (22.85, 4.9), (23.15, 5.0), (23.1, 5.9), (23.9, 6.0),
            (24.0, 6.15), (24.0, 6.9), (23.1, 7.0), (23.0, 7.9), (22.1, 8.0), (22.0, 10.6), (20.0, 10.6),
            (20.0, 9.0), (21.0, 9.0), (21.0, 7.5)]


def build_arm(bm):
    """Brown cranked arm from the rail's back end out to the tail (sprite rows 3-7, columns 17-24)."""
    prism(bm, ARM_POLY, -1.05, 1.75, ARM_M, bevel=0.3)


def arm_cutters(bm):
    block(bm, 20.9, 22.6, 5.25, 5.8, 1.2, 3.0, 0.0, LINE)  # pocket in its top


def build_side(bm):
    """Parts of one side that need no cuts: conductor bar, bolts, strut."""
    block(bm, 9.0, 16.1, 3.15, 3.85, 0.5, 1.28, 0.1, INSERT)
    disc_z(bm, 18.4, 3.75, 1.2, 1.6, 0.35, POST, sides=8)
    disc_z(bm, 22.45, 5.9, 1.6, 2.05, 0.5, POST, sides=10)
    disc_z(bm, 22.45, 5.9, 1.95, 2.2, 0.25, DRUM, sides=8, ch=0.06)
    tube_y(bm, 21.5, 0.0, 7.2, 10.6, 0.7, 1.15, DRUM, sides=10)
    tube_y(bm, 21.5, 0.0, 8.9, 9.6, 0.85, 1.35, LIP, sides=10)


def cut_part(buildf, cutf, mats, coll, name):
    bm = bmesh.new()
    buildf(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = to_obj(name, bm, mats, coll)
    bm.free()
    c = bmesh.new()
    cutf(c)
    cut(o, c, mats, coll)
    c.free()
    return o


def mirror_copy(bm):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)
    vs = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in vs:
        v.co.y = 2 * AY - v.co.y
    fs = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=fs)


def build(sprite, coll):
    mats = materials(sprite)
    pod = build_pod(mats, coll)
    rail = cut_part(build_rail, rail_cutters, mats, coll, "rail")
    arm = cut_part(build_arm, arm_cutters, mats, coll, "arm")
    bm = bmesh.new()
    bm.from_mesh(rail.data)
    bm.from_mesh(arm.data)
    build_side(bm)
    mirror_copy(bm)
    build_bay(bm)
    build_plate(bm)
    build_engine(bm)
    bm.from_mesh(pod.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # Sprite px to Blender.
    m = Matrix(((PX, 0, 0, -12 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    for o in (pod, rail, arm):
        me = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(me)
    obj = to_obj(NAME, bm, mats, coll)
    bm.free()
    me = obj.data
    me.set_sharp_from_angle(angle=math.radians(38))
    return obj, mats


def finish(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50


def bake_maps(obj, out_dir, size=1024, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT = (0.95, 0.97, 1.0)
    T.TEXTURED = tuple(i for i in range(len(SLOTS)) if SLOTS[i][4] == 0)
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", NAME)


def engines(obj, sprite):
    """Engine glow (src/ui/backdrop.ts): the nozzle at column edge 23.8 on the pod axis, in glTF axes
    (x, y up, z = -Blender Y), in the glow's palette colour."""
    rgb = sprite["colors"][str(SLOTS[GLOW][0])]
    obj["tyrian_engines"] = {"color": "#%02x%02x%02x" % tuple(int(c) for c in rgb[:3]),
                             "at": [[round((23.8 - 12) * PX, 4), 0.0, round(-(14 - AY) * PX, 4)]]}


def make(sprite, coll, bake=True):
    """The finished model (culled, weighted normals, maps baked) and its materials."""
    obj, mats = build(sprite, coll)
    T.cull_hidden(obj)
    finish(obj)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles")
    engines(obj, sprite)
    if bake:
        bake_dir = ROOT / "assets" / "blender" / "textures" / NAME / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(obj, bake_dir, size=1024, samples=64)
    return obj, mats


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    bake = "--no-bake" not in argv
    obj, mats = make(sprite, coll, bake)
    fmt = "WEBP" if bake else "AUTO"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(obj, coll, faces=1200)
    shell.name = shell.data.name = f"{NAME}_outline"
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
    else:
        common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    shell.hide_render = True
    if "--preview" in argv:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
