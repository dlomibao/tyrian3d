"""Grey twin-blade fighter (newshm.shp frames 89, 91, 93): the sprite in 3D, hard-surface.

What it is: a small free-flying fighter that flies nose-down the screen. Two long armoured blades
run side by side from a broad swept shoulder at the back to two pointed prongs at the front, a
3 px slot between them. Each blade carries a raised crest rail along its inner edge (the sprite's
bright line, columns 10 and 14) that runs back past the shoulder as a tall nozzle cheek; outboard
of the crest the blade falls in a chamfered slope to a flat wing plate with a raised rim at the
wing tip (the shoulder's lit outer column), then a chamfered edge. At the back of the slot sits a
small engine whose nozzle throat glows dark red (row 11); two cross struts (the light rungs at
rows 12 and 14) tie the blades together over the dark slot floor. The flame (frames 89/91/93,
one per frame) leaves the nozzle between the cheeks and swells to 5 px behind them before it
tapers to its tip (rows 5/4/3).

Authored in sprite pixel-edge coordinates (c = column 0..24 east, r = row 0..28 south, z = px up)
and moved to Blender at the end: X = (c - 12) / 12, Y = (14 - r) / 12, Z = z / 12. The sprite is
symmetric about c = 12.5. Plan edges sit on the inner edge of the sprite's ink border (D74), as one
pchip curve through the staircase (D52, D118). Colours: the sprite's own palette indices per region
(trimmed medians: shoulder 9, prong 8, crest/cheek 10, slot 3, struts 8, nozzle 112), satin metal.
Underside: a rounded closed belly, nothing more. Texture: AO/roughness bake only (no concept
projection), outline shell from a sealed copy (D51, D90).

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshm-89.py  (extra: -- --no-bake)
"""

import bisect
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402

HERE = Path("/Users/dlomibao/projects/tyrian-scratch/e2-enemies-1/newshm-89/final")
ROOT = WT
NAME = "newshm-89"
TAG = "newshm89A"
AXIS = 12.5  # the sprite's mirror line (column edge)

# --- palette slots: name, palette index, metallic, roughness, emission ------------------------
SLOTS = [
    ("plate", 9, 0.55, 0.38, 0.0),   # shoulder wing plates (trimmed median 9)
    ("prong", 8, 0.55, 0.38, 0.0),   # prongs (median 8)
    ("crest", 10, 0.6, 0.32, 0.0),   # crest rail and nozzle cheeks (median 10)
    ("deep", 3, 0.3, 0.6, 0.0),      # slot floor
    ("strut", 8, 0.6, 0.34, 0.0),    # cross struts (shared index with prong; separate slot name only)
    ("vent", 6, 0.4, 0.5, 0.0),      # shoulder vent slats
    ("heat", 112, 0.5, 0.45, 0.0),   # heat-tinted engine pod and nozzle bell (row 11)
    ("throat", 112, 0.0, 0.6, 0.8),  # glowing nozzle throat
    ("f114", 114, 0.0, 0.5, 1.0),
    ("f117", 117, 0.0, 0.5, 1.0),
    ("f121", 121, 0.0, 0.5, 1.0),
    ("f123", 123, 0.0, 0.5, 1.0),
    ("f124", 124, 0.0, 0.5, 1.0),
    ("f126", 126, 0.0, 0.5, 1.1),
    ("f127", 127, 0.0, 0.5, 1.4),
]
S = {n: k for k, (n, *_rest) in enumerate(SLOTS)}
EMISSIVE = {k for k, s in enumerate(SLOTS) if s[4] > 0}


def V(c, r, z):
    return Vector(((c - 12) / 12, (14 - r) / 12, z / 12))


# --- curves (pchip, from usp_talon / newsh2-49) ------------------------------------------------

def pchip(xs, ys):
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


def curve(pts):
    return pchip([p[0] for p in pts], [p[1] for p in pts])


# --- mesh builder -------------------------------------------------------------------------------

class Builder:
    def __init__(self):
        self.bm = bmesh.new()

    def face(self, verts, mat):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        f.material_index = mat
        return f

    def rings(self, rings, mat, cap0=True, cap1=True, band_mats=None, cap_mats=None):
        """Loft closed rings of (c, r, z); band_mats[k][i] = material of quad i between rings k, k+1."""
        vr = [[self.bm.verts.new(V(*p)) for p in ring] for ring in rings]
        n = len(vr[0])
        for k in range(len(vr) - 1):
            for i in range(n):
                j = (i + 1) % n
                m = band_mats[k][i] if band_mats else mat
                self.face([vr[k][i], vr[k][j], vr[k + 1][j], vr[k + 1][i]], m)
        c0, c1 = cap_mats if cap_mats else (mat, mat)
        if cap0:
            self.face(list(reversed(vr[0])), c0)
        if cap1:
            self.face(vr[-1], c1)
        return vr

    def lathe(self, a, b, radii, n, mat, rot=0.0, squash=1.0, cap0=True, cap1=True):
        a, b = Vector(a), Vector(b)
        ax = b - a
        d = ax.normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(up).normalized()
        v = d.cross(u).normalized()
        rings = []
        for fr, rad in radii:
            c = a + ax * fr
            rings.append([tuple(c + u * math.cos(rot + 2 * math.pi * i / n) * rad
                                + v * math.sin(rot + 2 * math.pi * i / n) * rad * squash) for i in range(n)])
        return self.rings(rings, mat, cap0=cap0, cap1=cap1)

    def prism(self, pts, z0, z1, mat, ch=0.0, chb=0.0):
        """A plate over a (c, r) outline from z0 to z1, top edge chamfered in by ch."""
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)

        def shrink(d):
            out = []
            for c, r in pts:
                v = Vector((cx - c, cy - r))
                out.append((c + v.normalized().x * min(d, v.length * 0.45), r + v.normalized().y * min(d, v.length * 0.45)))
            return out
        rings = []
        if chb > 0:
            rings.append([(c, r, z0) for c, r in shrink(chb)])
            rings.append([(c, r, z0 + chb) for c, r in pts])
        else:
            rings.append([(c, r, z0) for c, r in pts])
        if ch > 0:
            rings.append([(c, r, z1 - ch) for c, r in pts])
            rings.append([(c, r, z1) for c, r in shrink(ch)])
        else:
            rings.append([(c, r, z1) for c, r in pts])
        return self.rings(rings, mat)

    def hexbolt(self, c, r, z, rad=0.26, h=0.18, mat=None):
        self.lathe((c, r, z - 0.15), (c, r, z + h), [(0, rad), (0.7, rad), (1, rad * 0.7)], 6, mat, rot=0.3)


# --- the blade plan (left blade; the right is its mirror about c = 12.5) -----------------------
INNER_C = 11.0  # the slot edge (inner edge of the ink border at column 11)
R_REAR, R_TIP = 8.0, 26.15
# outer edge column through the middles of the inner mask's steps
OUTER = curve([
    (8.0, 10.0), (8.6, 9.55), (9.5, 8.45), (10.5, 6.95), (11.5, 5.9), (12.3, 5.12), (12.9, 4.98),
    (14.2, 4.98), (14.9, 5.35), (15.6, 6.05), (16.4, 6.85), (17.5, 7.05), (18.6, 7.25),
    (19.6, 7.75), (21.4, 8.15), (22.3, 8.65), (23.4, 9.2), (24.3, 9.75), (25.3, 10.1), (25.85, 10.45),
    (26.15, 10.95),
])
CREST = curve([(8.0, 4.4), (9.5, 4.6), (11.0, 4.9), (15.0, 4.9), (17.0, 4.3), (21.0, 3.4), (24.5, 2.4),
               (26.15, 1.25)])
PLATE = curve([(8.0, 3.2), (9.5, 2.8), (11.0, 2.75), (15.0, 2.75), (16.5, 2.5), (20.0, 2.2), (24.5, 1.5),
               (26.15, 0.9)])
RIM = curve([(10.5, 0.0), (11.6, 0.4), (14.6, 0.4), (15.8, 0.0), (26.15, 0.0)])
BELLY = curve([(8.0, 0.5), (10.0, 1.0), (15.0, 1.25), (18.0, 0.95), (24.0, 0.65), (26.15, 0.3)])
SEAMS = (11.7, 16.3, 21.2)  # transverse panel lines (V grooves)
SHOULDER_END = 16.3


def top_profile(w, h, hp, rim):
    """Top of a blade across its width, from the slot edge (d = 0) outward: (d px, z px).
    Inner chamfer, crest rail, slope down to the wing plate, rim, outer chamfer. 11 points."""
    cw = min(1.1, 0.55 * w)
    pts = [(0.0, h - 0.95), (min(0.28, 0.12 * w), h - 0.2), (min(0.6, 0.25 * w), h), (cw, h)]
    rest = max(w - cw, 1e-3)
    hp = min(hp, h - 0.3)
    edge = max(0.45, min(hp * 0.33, 0.85))
    zt = max(edge + 0.35, hp * 0.74 + rim * 0.7)  # deck height at the outer edge
    ch = min(0.32, 0.1 * w)  # 45 degree chamfer where the deck meets the side wall
    pts += [
        (cw + 0.12 * rest, h - 0.25),
        (cw + 0.30 * rest, hp + 0.12),
        (cw + 0.42 * rest, hp),
        (cw + 0.66 * rest, hp * 0.88),
        (cw + 0.74 * rest, hp * 0.86 + rim),
        (cw + 0.86 * rest, hp * 0.8 + rim * 0.8),
        (w - ch, zt),
        (w, zt - ch),
    ]
    return pts


def bottom_profile(w, b):
    """Underside across the width (d from the slot edge outward): a flat closed belly with
    chamfered edges, so the side walls stay hard. 6 points; the last is the outer wall's foot."""
    cb = min(0.4, 0.14 * w)
    return [(0.0, 0.25), (cb, -0.75 * b), (2.2 * cb, -b), (w - 2.2 * cb, -b), (w - cb, -0.75 * b),
            (w, -0.2 * b)]


TOP_MATS = ["prong", "crest", "crest", "crest", "plate", "plate", "plate", "plate", "plate", "plate", "plate"]


def blade_rings(side):
    rs = sorted(set([R_REAR + k * 0.5 for k in range(int((R_TIP - R_REAR) / 0.5) + 1)] + [8.25, 25.4, 25.8]
                    + [s + d for s in SEAMS for d in (-0.14, 0.0, 0.14)] + [R_TIP]))
    rs = [r for r in rs if R_REAR <= r <= R_TIP]
    rings, mids = [], []
    for r in rs:
        xo = OUTER(r)
        w = max(INNER_C - xo, 0.25)
        h = CREST(r)
        tp = top_profile(w, h, PLATE(r), RIM(r))
        b = BELLY(r)
        bot = bottom_profile(w, b)
        ring = [(INNER_C - d, r, z) for d, z in tp] + [(INNER_C - d, r, z) for d, z in reversed(bot)]
        if any(abs(r - s) < 1e-9 for s in SEAMS):  # V groove: pull the top in by 0.3 px
            ring = [(c, rr, z - 0.3 if k < len(tp) else z) for k, (c, rr, z) in enumerate(ring)]
        if side < 0:
            ring = [(2 * AXIS - c, rr, z) for c, rr, z in ring]
            ring.reverse()
        rings.append(ring)
    return rs, rings, len(tp)


def build_blades(b):
    for side in (1, -1):
        rs, rings, nt = blade_rings(side)
        n = len(rings[0])
        band = []
        for r0, r1 in zip(rs, rs[1:]):
            rm = (r0 + r1) / 2
            row = []
            for i in range(n):
                k = i if side > 0 else n - 2 - i  # quad index as the left blade's
                if 0 <= k < nt - 1:
                    name = TOP_MATS[k]
                    if name == "plate" and rm > SHOULDER_END:
                        name = "prong"
                    if name == "crest" and rm < 8.4:
                        name = "crest"
                    row.append(S[name])
                else:
                    row.append(S["prong"])
            band.append(row)
        b.rings(rings, 0, band_mats=band, cap_mats=(S["crest"], S["prong"]))


def build_centre(b):
    # Slot floor between the blades (dark), under the struts and engine.
    # Upper slab and a slightly inset lower slab: the step between them is the panel line that
    # rings the block, and both are chamfered (seen from the rear under the nozzle).
    b.prism([(10.9, 10.9), (14.1, 10.9), (14.1, 16.15), (10.9, 16.15)], -0.05, 0.5, S["deep"], ch=0.2)
    b.prism([(11.1, 11.1), (13.9, 11.1), (13.9, 15.95), (11.1, 15.95)], -0.6, -0.05, S["deep"], chb=0.22)
    # Two cross struts (the light rungs, rows 12 and 14): round bars with collars at the blades.
    for r in (12.5, 14.5):
        b.lathe((10.7, r, 2.3), (14.3, r, 2.3), [(0, 0.5), (1, 0.5)], 10, S["strut"])
        for c0, c1 in ((10.95, 11.45), (13.55, 14.05)):
            b.lathe((c0, r, 2.3), (c1, r, 2.3), [(0, 0.66), (1, 0.66)], 8, S["crest"], rot=math.pi / 8)
    # Engine: a short pod hung from the front strut on a pylon, on the flame's axis (ZA). One
    # closed revolve: front cap against the strut, pod, flared bell, a lip turning in at the mouth
    # (row 10.85), the inner wall, and a recessed glowing throat disc that closes it.
    prof = [(12.1, 0.85), (11.9, 1.12), (11.6, 1.26), (11.3, 1.3), (11.22, 1.42), (10.85, 1.42),
            (10.85, 1.2), (11.2, 1.15)]
    n = 16
    rings = [[(AXIS + rad * math.cos(2 * math.pi * i / n), r, ZA + rad * math.sin(2 * math.pi * i / n))
              for i in range(n)] for r, rad in prof]
    b.rings(rings, S["heat"], cap_mats=(S["heat"], S["throat"]))
    b.prism([(12.05, 11.45), (12.95, 11.45), (12.95, 12.4), (12.05, 12.4)], 0.3, ZA - 0.7, S["deep"], ch=0.1)


def build_detail(b):
    for side in (1, -1):
        def m(c):
            return c if side > 0 else 2 * AXIS - c
        # Shoulder vent: three slats sunk into the wing plate (the sprite's darker cols 7-8).
        for k, r in enumerate((12.55, 13.4, 14.25)):
            c0, c1 = m(6.7), m(8.75)
            b.prism([(min(c0, c1), r), (max(c0, c1), r), (max(c0, c1), r + 0.5), (min(c0, c1), r + 0.5)],
                    2.35, 2.95, S["vent"], ch=0.08)
        # Hex bolts on the shoulder plate fore and aft of the vent, and on the prong plate.
        for c, r in ((7.6, 11.95), (7.0, 15.2)):
            b.hexbolt(m(c), r, PLATE(r) + 0.02 * 0, rad=0.24, h=0.16, mat=S["crest"])
        # Prong sensor strip: a narrow raised fairing along the prong's outer slope.
        for r0, r1 in ((17.2, 20.6),):
            pts = []
            for r in (r0, (r0 + r1) / 2, r1):
                pts.append(r)
        # Nozzle cheeks: the crest rail ends at the back in a rounded post either side of the
        # flame (sprite columns 10 and 14, rows 8-10), standing a little proud of the crest.
        b.lathe((m(10.5), 8.0, 4.25), (m(10.5), 11.4, 4.25),
                [(0, 0.12), (0.05, 0.38), (0.13, 0.5), (0.85, 0.5), (1, 0.42)], 10, S["crest"], squash=0.9)


ZA = 2.3  # engine and flame axis height (px): high enough that the tilted camera sees the flame

FLAME_IDX = (114, 117, 121, 123, 124, 126, 127)  # flame palette slots (f_*), coolest first


def flame_colour(px, c, r):
    """The sprite's flame colour at plan point (c, r): its own pixel, or the nearest flame pixel
    inward along the row (beside the cheeks), snapped to the nearest flame slot."""
    row = int(math.floor(r))
    col = int(math.floor(c))
    if not 0 <= row < len(px):
        return 114
    step = 1 if col < 12 else -1
    for k in range(4):
        cc = col + step * k
        if 0 <= cc < len(px[row]) and 112 <= px[row][cc] <= 127:
            v = px[row][cc]
            return min(FLAME_IDX, key=lambda q: abs(q - v))
    return 114


def flame_parts(coll, mats, sprite):
    """One closed loft per frame on the nozzle axis: it starts inside the nozzle bell (behind the
    lip) and swells to the sprite's plan behind the cheeks. Each face takes the sprite's flame
    colour at its plan position (top faces) so the top view keeps the sprite's colour bands with
    no intersecting shells; the underside runs one step cooler. (row edge, half width, half height)."""
    out = []
    frames = {int(f["index"]): f["pixels"] for f in sprite["frames"]}  # parsed by common.load_sprite
    n = 12
    for frame, shift in ((89, 0.0), (91, 1.0), (93, 2.0)):
        ws = 7.0 - shift
        plan = [(11.15, 1.0, 1.0), (10.85, 1.12, 1.1), (9.6, 1.45, 1.25), (8.4, 1.48, 1.3), (8.0, 2.25, 1.5),
                (7.6, 2.48, 1.55), (ws + 0.15, 2.45, 1.5), (ws - 0.3, 1.75, 1.15), (ws - 0.8, 1.05, 0.75),
                (ws - 1.3, 0.45, 0.35), (ws - 1.65, 0.05, 0.06)]
        plan = sorted({p[0]: p for p in plan}.values(), key=lambda p: -p[0])
        # stations: the plan points plus every half row, linearly between them (plan unchanged)
        rs = sorted({p[0] for p in plan} | {k * 0.5 for k in range(int(plan[-1][0] * 2) + 1, int(plan[0][0] * 2) + 1)},
                    reverse=True)
        secs = []
        for r in rs:
            for (r0, w0, h0), (r1, w1, h1) in zip(plan, plan[1:]):
                if r1 <= r <= r0:
                    t = 0 if r0 == r1 else (r0 - r) / (r0 - r1)
                    secs.append((r, w0 + (w1 - w0) * t, h0 + (h1 - h0) * t))
                    break
        rings = [[(AXIS + hw * math.cos(2 * math.pi * i / n), r, ZA + hh * math.sin(2 * math.pi * i / n))
                  for i in range(n)] for r, hw, hh in secs]
        px = frames[frame]
        band = []
        for k in range(len(rings) - 1):
            row = []
            for i in range(n):
                j = (i + 1) % n
                pts = (rings[k][i], rings[k][j], rings[k + 1][i], rings[k + 1][j])
                c = sum(p[0] for p in pts) / 4
                r = sum(p[1] for p in pts) / 4
                ang = math.pi * (2 * i + 1) / n  # face centre angle; sin < 0 is the underside
                idx = flame_colour(px, c, r)
                if math.sin(ang) < -0.3:  # underside: one step cooler than the top above it
                    idx = FLAME_IDX[max(0, FLAME_IDX.index(idx) - 1)]
                row.append(S[f"f{idx}"])
            band.append(row)
        b = Builder()
        b.rings(rings, S["f114"], band_mats=band, cap_mats=(S["f127"], S["f114"]))
        obj = finish_mesh(b, f"{NAME}-flame-{frame}", coll, mats, sharp=60)
        common.frame_part(obj, [frame])
        out.append(obj)
    return out


def finish_mesh(b, name, coll, mats, sharp=38):
    bm = b.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    mesh.shade_smooth()
    mesh.set_sharp_from_angle(angle=math.radians(sharp))
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def apply_weighted_normals(obj):
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=wn.name)


# --- bake (AO / roughness only, no concept projection; copied from newsh2-49, D50/D65) ----------

def bake_maps(obj, out_dir, tag, size=1024, samples=64, skip=()):
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
    for o in bpy.context.view_layer.objects:
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
    mats = list(dict.fromkeys(me.materials))
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
        ao_l.inputs["Distance"].default_value = 0.2
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
                     math_("ADD", 0.6, math_("MULTIPLY", ao_l.outputs["AO"], 0.4)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.45, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            nt.links.new(v, em.inputs["Color"])
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
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for m in [q for q in mats if q.name not in skip]:
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    mats = []
    for name, idx, met, rough, em in SLOTS:
        tag = TAG + {"strut": "s", "heat": "h"}.get(name, "")
        mats.append(common.palette_material(sprite, idx, tag, metallic=met, roughness=rough, emission_strength=em))
    b = Builder()
    build_blades(b)
    build_centre(b)
    build_detail(b)
    body = finish_mesh(b, NAME, coll, mats)
    apply_weighted_normals(body)
    flames = flame_parts(coll, mats, sprite)
    tris = sum(len(p.vertices) - 2 for o in [body] + flames for p in o.data.polygons)
    print(f"{NAME} A: {tris} triangles")
    # Sealed copy for the outline shell, taken before the bake and kept out of its scene.
    sealed = body.copy()
    sealed.data = body.data.copy()
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = HERE / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(body, bake_dir, TAG, size=1024, samples=48, skip={mats[i].name for i in EMISSIVE})
        fmt = "WEBP"
    coll.objects.link(sealed)
    shell = common.outline_shell(sealed, coll, voxel=0.03, faces=2000, inside=0.004)
    bpy.data.objects.remove(sealed, do_unlink=True)
    shell.name = f"{NAME}_outline"
    shell.parent = body
    common.export_sprite_model(ROOT, [body, shell] + flames, "enemies/newshm-89", sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
