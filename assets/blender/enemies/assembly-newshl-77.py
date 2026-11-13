"""assembly-newshl-77, TIME WAR's (4.17) grey engine nacelle, newshl 77 + 79 side by side.

What it is (behaviour dump, tools/enemy_behaviour.mjs): types 657/658, armour 255, on the sky layer, spawned
at t110 and held still near the top edge, rigid on links 27/28 with newshl-1/3 (dy -56) and newshl-39/41
(dy -28): the lower end of a 48 x 84 px craft, two of them flanking TIME WAR's blue-domed boss. The upper
pieces stay sprites, so the top edge (row 0) is a seam. In game only the lower tier and the exhaust show
under the top edge, seen by the tilted camera from down-screen: so the down-screen faces carry the detail.

Read as a horizontal engine nacelle lying along the screen (the sprite is its top view): a waisted neck
spindle (rows 0-6) with a raised spine fairing (the lit V of rows 0-8) and four red marker lamps (rows 0-1
cols 16-17 / 31-32, row 5 cols 18-19 / 29-30); a forward cooling flange (rows 7-11) with a machined rim land
and a vent channel cut across its back (the dark slot of rows 10-11, cols 20-27) opening onto the collar;
the collar drum (rows 12-15) with a side intake box on the right (the dark 2-3 of rows 13-14, cols 30-33);
the rear flange (rows 16-19: its near-white rim of row 16 is sheen on the front land, art rule 2) with a
stepped rear cone; a waist (row 20) and a red-hot exhaust shroud (rows 21-22) with two hotter ports (the
122/121 at cols 20-21 and 120 at col 28) recessed in its end face.

Sprite rules: plan = the D74 inner mask (tools/sprite_mask.py assembly-newshl-77), per-row left/right
widths taken from it (the neck's top is asymmetric: it flares left into the piece above). Colours: the
palette index per region (neck 6, spine 7, front flange 7, collar 6, rear flange 6, waist 3, shroud 117/118
glow, ports 121, lamps 116/118). The dark rows 12 and 15 are the flanges' shadows on the collar (lighting).

Units: c, r = sprite px EDGES of the 48 x 28 assembly (col 3 spans c 3..4); X = (c - 24) / 12,
Y = (14 - r) / 12 (the seam between the pieces at X = 0); z in px * PX. The nacelle axis is c = 24.5.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshl-77.py
Exports the game models (public/models/enemies/newshl-77|79.glb + spriteModels); with
-- --out <file.glb> only an assembled review copy; review renders only behind --review <dir>.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
NAME = "assembly-newshl-77"
PIECES = ["newshl-77", "newshl-79"]
PX = 1 / 12
AX = 24.5      # nacelle axis (edge coords)
W, H = 48, 28  # assembly sprite size

STEEL = dict(metallic=0.82, roughness=0.42, spec=0.5)
GLOW = dict(metallic=1.0, roughness=0.9)


# --------------------------------------------------------------------------------------------------
# Materials (pattern copied from newshk-281.py: palette index per region, satin steel, glows D126/D173,
# F0 via Specular IOR Level D176)
# --------------------------------------------------------------------------------------------------

class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list, self.slots = [], {}

    def __call__(self, index, metallic=0.82, roughness=0.42, emit=0.0, spec=0.5):
        key = (index, metallic, roughness, emit, spec)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            m = common.palette_material(self.sprite, index, f"nshl77A{len(self.list)}", metallic=metallic,
                                        roughness=roughness, emission_strength=emit)
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if spec is not None and "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = spec
            self.list.append(m)
        return self.slots[key]


# --------------------------------------------------------------------------------------------------
# Helpers (copied in from newshk-281.py: no shared lib edits)
# --------------------------------------------------------------------------------------------------

def _slopes(xs, ys):
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
    return m


class Pchip:
    """Monotone cubic through knots (x, y) (D52 station interpolation)."""

    def __init__(self, xs, ys):
        self.x, self.y = list(xs), list(ys)
        self.m = _slopes(self.x, self.y) if len(xs) > 1 else [0.0]

    def __call__(self, x):
        xs, ys, m = self.x, self.y, self.m
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
        hh = xs[i + 1] - xs[i]
        t = (x - xs[i]) / hh
        return ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * hh * m[i]
                + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * hh * m[i + 1])


def P(c, r, z):
    """Edge coords (c, r) and z in px to Blender units."""
    return Vector(((c - 24) * PX, (14 - r) * PX, z * PX))


def verts(bm, pts):
    return [bm.verts.new(p) for p in pts]


def loft(bm, rings, mat, smooth=True, cap0=True, cap1=True, cap_mat=None):
    """Join rings (lists of BMVert of equal length) with quads; `mat` is an index or f(i, k)."""
    mf = mat if callable(mat) else (lambda i, k: mat)
    n = max(len(r) for r in rings)
    out = []
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        for k in range(n):
            j = (k + 1) % n
            try:
                f = bm.faces.new((a[k], b[k], b[j], a[j]))
            except ValueError:
                continue
            f.material_index = mf(i, k)
            f.smooth = smooth
            out.append(f)
    cm = mf(0, 0) if cap_mat is None else cap_mat
    for ring, ok, rev in ((rings[0], cap0, True), (rings[-1], cap1, False)):
        if ok and len(ring) > 2:
            f = bm.faces.new(list(reversed(ring)) if rev else ring)
            f.material_index = cm
            f.smooth = False
            out.append(f)
    return out


def hull_pts(bm, pts, mat):
    vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in vs if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    live = [v for v in vs if v.is_valid]
    for f in {f for v in live for f in v.link_faces}:
        f.material_index = mat
        f.smooth = False


def chbox(bm, c0, c1, r0, r1, z0, z1, ch, mat, chz=None):
    """A box with chamfered edges (convex hull of the chamfer points), in edge coords / px."""
    chz = ch if chz is None else chz
    pts = []
    for c, sc in ((c0, 1), (c1, -1)):
        for r, sr in ((r0, 1), (r1, -1)):
            for z, sz in ((z0, 1), (z1, -1)):
                pts += [(c + sc * ch, r, z + sz * chz), (c, r + sr * ch, z + sz * chz), (c + sc * ch, r + sr * ch, z)]
    hull_pts(bm, [P(*p) for p in pts], mat)


def cut_into(bm, prism, wall_mat, nmat):
    """Boolean-subtract a closed cutter (built by `prism(cb)` into a fresh bmesh) from the shell in bm, in
    place (exact solver); cut faces get `wall_mat`. (newshk-281.py's cut_into, generalised.)"""
    me = bpy.data.meshes.new("_shell")
    cm = bpy.data.meshes.new("_cut")
    slots = [bpy.data.materials.new("_slot") for _ in range(nmat)]
    for m in (me, cm):
        for sl in slots:
            m.materials.append(sl)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    shell = bpy.data.objects.new("_shell", me)
    cb = bmesh.new()
    prism(cb)
    for f in cb.faces:
        f.material_index = wall_mat
    bmesh.ops.recalc_face_normals(cb, faces=cb.faces)
    cb.to_mesh(cm)
    cb.free()
    cutter = bpy.data.objects.new("_cut", cm)
    sc = bpy.context.scene.collection
    sc.objects.link(shell)
    sc.objects.link(cutter)
    mod = shell.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    mod.material_mode = "INDEX"
    bpy.context.view_layer.update()
    ev = shell.evaluated_get(bpy.context.evaluated_depsgraph_get())
    out = bpy.data.meshes.new_from_object(ev)
    bm.clear()
    bm.from_mesh(out)
    for o in (shell, cutter):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in (me, cm, out):
        bpy.data.meshes.remove(m)
    for sl in slots:
        bpy.data.materials.remove(sl)


def merge(bm, other):
    """Append bmesh `other` into `bm` (and free it)."""
    me = bpy.data.meshes.new("_merge")
    other.to_mesh(me)
    other.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def box_prism(c0, c1, r0, r1, z0, z1):
    def make(cb):
        lo = verts(cb, [P(c, r, z0) for c, r in ((c0, r0), (c1, r0), (c1, r1), (c0, r1))])
        hi = verts(cb, [P(c, r, z1) for c, r in ((c0, r0), (c1, r0), (c1, r1), (c0, r1))])
        loft(cb, [lo, hi], 0, smooth=False)
    return make


def cyl_y_prism(c, z, rad, r0, r1, sides=20):
    """A cylinder along the screen (axis parallel to Y) from row r0 to r1, centre (c, z), radius px."""
    def make(cb):
        rings = []
        for r in (r0, r1):
            rings.append(verts(cb, [P(c + rad * math.cos(2 * math.pi * k / sides), r,
                                      z + rad * math.sin(2 * math.pi * k / sides)) for k in range(sides)]))
        loft(cb, rings, 0, smooth=False)
    return make


def ellipsoid(bm, centre, radii, mat, segments=16, rings=10):
    res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = centre
    for v in res["verts"]:
        v.co = Vector((cx + v.co.x * radii[0], cy + v.co.y * radii[1], cz + v.co.z * radii[2]))
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat
        f.smooth = True


def cylinder_x(bm, c0, c1, r, z, rad_r, rad_z, mat, sides=14, cap_mat=None):
    """A cylinder across the screen (axis along X) from c0 to c1 at row r, height z (px)."""
    rings = []
    for c in (c0, c1):
        rings.append(verts(bm, [P(c, r + rad_r * math.cos(2 * math.pi * k / sides),
                                  z + rad_z * math.sin(2 * math.pi * k / sides)) for k in range(sides)]))
    loft(bm, rings, mat, smooth=True, cap_mat=cap_mat)


# --------------------------------------------------------------------------------------------------
# The hull: one closed loft down the screen through every station (one shell, sealed)
# --------------------------------------------------------------------------------------------------

SIDES = 40

# Segments of the hull: (name, material key, superellipse exponent, stations (r, wl, wr, h)).
# Widths are px left / right of the axis (c = 24.5), h the half height (the hull is symmetric top /
# bottom: the underside is a plain closed mirror). Rows are pixel EDGES (row 7 spans r 7..8); the mask
# widths are taken at row centres from tools/sprite_mask.py's inner mask.
SEGMENTS = [
    # Neck spindle: flares left into the piece above (rows 0-1 reach col 14 / 16), waists at row 4-5 where
    # the side lamps stand.
    ("neck", "neck", 2.2, [(0.0, 10.4, 5.6, 3.9), (0.5, 10.2, 5.6, 3.9), (1.5, 8.4, 6.4, 3.8),
                           (2.5, 7.4, 7.4, 3.7), (3.5, 7.3, 7.3, 3.6), (4.5, 5.2, 6.3, 3.4),
                           (5.5, 5.4, 5.5, 3.4), (6.5, 6.4, 6.4, 3.6), (6.95, 6.9, 6.9, 3.8)]),
    # Forward flange: chamfered front face, a machined rim land rows 9-11, short rear chamfer.
    ("front", "front", 2.4, [(7.0, 9.4, 9.4, 4.3), (7.2, 10.2, 10.2, 4.75), (7.5, 10.7, 10.7, 5.0),
                             (8.5, 11.7, 11.7, 5.4), (9.3, 12.4, 12.4, 5.6), (9.6, 12.5, 12.5, 5.65),
                             (11.5, 12.5, 12.5, 5.6), (11.8, 12.2, 12.2, 5.3), (12.0, 11.5, 11.5, 4.8)]),
    # Collar drum between the flanges (row 12's left is pulled in to col 18: the flange's shadow edge).
    ("collar", "collar", 2.6, [(12.05, 7.0, 8.4, 3.7), (12.6, 7.9, 8.5, 3.85), (13.2, 8.5, 8.5, 3.95),
                               (15.5, 8.5, 8.5, 3.95), (15.95, 8.4, 8.4, 3.85)]),
    # Rear flange: narrow front chamfer (its lit edge is row 16's near-white sheen), rim land, a rear cone
    # with a machined step at r 18.6.
    ("rear", "rear", 2.4, [(16.0, 11.8, 11.8, 5.0), (16.25, 12.5, 12.5, 5.5), (17.6, 12.5, 12.5, 5.5),
                           (18.0, 12.2, 11.8, 5.3), (18.6, 11.4, 10.7, 4.95)]),
    ("rear2", "rear", 2.4, [(18.66, 10.9, 10.3, 4.6), (19.5, 9.5, 9.4, 4.0), (19.95, 8.4, 8.4, 3.6)]),
    # Waist between the flange and the exhaust shroud.
    ("waist", "waist", 2.2, [(20.0, 5.1, 5.1, 2.8), (20.95, 5.1, 5.1, 2.8)]),
    # Exhaust shroud: a boxy, red-hot band (the bar of rows 21-22), chamfered at both ends.
    ("shroud", "shroud", 3.2, [(21.0, 5.9, 5.9, 2.9), (21.2, 6.45, 6.45, 3.3), (22.0, 6.4, 6.45, 3.3),
                               (22.8, 6.0, 6.35, 3.25), (23.0, 5.6, 5.9, 2.9)]),
]


def densify(stations, step=0.5):
    """Stations with pchip in between (no swelling between knots)."""
    rs = [s[0] for s in stations]
    if len(stations) < 3:
        return stations
    f = [Pchip(rs, [s[i] for s in stations]) for i in (1, 2, 3)]
    out = []
    for a, b in zip(rs, rs[1:]):
        n = max(1, int(math.ceil((b - a) / step - 1e-6)))
        for k in range(n):
            r = a + (b - a) * k / n
            out.append((r, f[0](r), f[1](r), f[2](r)))
    out.append(stations[-1])
    return out


def ring_pts(r, wl, wr, h, n):
    pts = []
    e = 2.0 / n
    for k in range(SIDES):
        a = 2 * math.pi * (k + 0.5) / SIDES
        ca, sa = math.cos(a), math.sin(a)
        w = wr if ca > 0 else wl
        dx = w * math.copysign(abs(ca) ** e, ca)
        z = h * math.copysign(abs(sa) ** e, sa)
        pts.append((AX + dx, r, z))
    return pts


def hull_of(r):
    """The hull's (wl, wr, h, n) at row r (for placing parts on its surface)."""
    for name, key, n, st in SEGMENTS:
        if st[0][0] - 1e-6 <= r <= st[-1][0] + 1e-6:
            d = densify(st, 0.05)
            best = min(d, key=lambda s: abs(s[0] - r))
            return best[1], best[2], best[3], n
    return None


def surface_z(c, r):
    wl, wr, h, n = hull_of(r)
    dx = c - AX
    w = wr if dx > 0 else wl
    u = min(abs(dx) / w, 1.0)
    return h * (1 - u ** n) ** (1 / n)


def build(coll, sprite):
    M = Mats(sprite)
    mat = {
        "neck": M(6, **STEEL),
        "front": M(7, **STEEL),
        "collar": M(5, **STEEL),
        "rear": M(5, **STEEL),
        "waist": M(3, metallic=0.75, roughness=0.5, spec=0.5),
        "shroud": M(117, emit=1.0, **GLOW),
    }
    spine = M(7, **STEEL)
    recess = M(4, metallic=0.75, roughness=0.5, spec=0.5)
    floor = M(3, metallic=0.7, roughness=0.55, spec=0.5)
    grille = M(2, metallic=0.6, roughness=0.6, spec=0.5)
    vane = M(4, **STEEL)
    rivet = M(6, **STEEL)
    endplate = M(5, **STEEL)
    hot = M(121, emit=1.0, **GLOW)
    warm = M(119, emit=1.0, **GLOW)
    cool = M(115, emit=1.0, **GLOW)
    lamp_a = M(116, emit=1.0, **GLOW)
    lamp_b = M(118, emit=1.0, **GLOW)
    housing = M(5, **STEEL)

    bm = bmesh.new()
    rings, ring_mat = [], []
    for name, key, n, st in SEGMENTS:
        for r, wl, wr, h in densify(st):
            rings.append(verts(bm, [P(*p) for p in ring_pts(r, wl, wr, h, n)]))
            ring_mat.append((key, r))

    def hull_mat(i, k):
        key, r = ring_mat[i + 1]
        if key != "shroud":
            return mat[key]
        # Shroud glow by position across (the sprite's hot spots at cols 20-21 and 28, cooler ends).
        a = 2 * math.pi * (k + 1.0) / SIDES
        dx = 6.4 * math.copysign(abs(math.cos(a)) ** (2 / 3.2), math.cos(a))
        if 2.6 <= abs(dx) <= 4.7:
            return warm
        if abs(dx) > 5.6:
            return cool
        return mat["shroud"]

    loft(bm, rings, hull_mat, smooth=True, cap_mat=endplate)
    nmat = len(M.list) + 8

    # The vent channel across the forward flange's back (rows 10-11, cols 20-27), open onto the collar.
    cut_into(bm, box_prism(20.0, 28.0, 10.0, 12.3, 3.95, 9.0), recess, nmat)
    # Twin exhaust ports recessed in the shroud's end face (the hot spots at cols 20-21 and 28).
    for c in (AX - 3.7, AX + 3.7):
        cut_into(bm, cyl_y_prism(c, 0.0, 1.7, 22.5, 24.0), endplate, nmat)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    # The intake box on the collar's right flank (rows 13-14, cols 30-34), a dark grille recessed in it
    # (cut on its own: the boolean wants one closed volume).
    ib = bmesh.new()
    chbox(ib, 29.7, 35.0, 12.9, 15.1, -1.2, 3.25, 0.3, mat["collar"], chz=0.25)
    cut_into(ib, box_prism(30.2, 34.4, 13.25, 14.75, 2.55, 6.0), grille, nmat)
    merge(bm, ib)

    # Port cores: glowing discs at the bottom of the port recesses, with a cone (the nozzle throat).
    for c in (AX - 3.7, AX + 3.7):
        rings2 = []
        for r, rad in ((22.52, 1.68), (22.9, 1.2), (23.0, 0.6)):
            rings2.append(verts(bm, [P(c + rad * math.cos(2 * math.pi * k / 16), r,
                                       rad * math.sin(2 * math.pi * k / 16)) for k in range(16)]))
        loft(bm, rings2, hot, smooth=True, cap0=False)

    # Louvre vanes across the vent channel (machined detail; below its lip so the slot reads dark).
    for c in (22.0, 24.5, 27.0):
        chbox(bm, c - 0.3, c + 0.3, 10.15, 12.0, 3.6, 4.45, 0.12, vane)

    # Rivet ring on the rear flange's stepped cone, upper half (the face the game camera looks at).
    wl, wr, h, n = hull_of(19.0)
    for i in range(9):
        a = math.radians(14 + i * (152 / 8))
        ca, sa = math.cos(a), math.sin(a)
        w = wr if ca > 0 else wl
        dx = (w - 0.15) * math.copysign(abs(ca) ** (2 / n), ca)
        z = (h - 0.15) * abs(sa) ** (2 / n)
        ellipsoid(bm, P(AX + dx, 19.0, z), (0.42 * PX, 0.42 * PX, 0.42 * PX), rivet, segments=8, rings=5)

    # The spine fairing: a chamfered trapezoid down the neck (the lit V of rows 0-8), dying into the
    # forward flange. (r, top half width, base half width, top z, base z).
    SP = [(0.0, 0.8, 1.7, 4.55, 2.6), (2.0, 0.9, 1.9, 4.5, 2.6), (4.0, 1.3, 2.6, 4.4, 2.5),
          (5.5, 1.9, 3.3, 4.45, 2.6), (7.0, 2.6, 4.0, 4.95, 3.2), (8.4, 3.0, 4.4, 5.6, 3.9),
          (9.2, 2.6, 3.8, 5.55, 4.0)]
    rs = [s[0] for s in SP]
    fi = [Pchip(rs, [s[i] for s in SP]) for i in range(1, 5)]
    srings = []
    r = 0.0
    while r <= 9.2001:
        tw, bw, zt, zb = (f(r) for f in fi)
        ch = 0.45
        sec = [(bw, zb), (tw + ch, zt - ch * 0.8), (tw, zt), (-tw, zt), (-tw - ch, zt - ch * 0.8), (-bw, zb),
               (0.0, zb - 1.4)]
        srings.append(verts(bm, [P(AX + dx, r, z) for dx, z in sec]))
        r += 0.4
    loft(bm, srings, spine, smooth=False)

    # Marker lamps: red lenses in small bezels. Front pair on the neck's flared top (rows 0-1, cols
    # 16-17 and 31-32; the right one on a short bracket), side pair at the waist (row 5, cols 18-19 /
    # 29-30).
    # Right bracket from the neck out to the lamp.
    chbox(bm, 29.0, 32.6, 0.0, 1.6, 0.6, 2.5, 0.25, housing)
    for c, r, rad, m in ((16.9, 0.8, (1.05, 0.75), lamp_a), (31.9, 0.8, (0.85, 0.75), lamp_a)):
        z = (surface_z(c, r) if c < 29 else 2.5)
        ellipsoid(bm, P(c, r, z - 0.1), (rad[0] * PX, rad[1] * PX, 0.65 * PX), m)
    for c, side, m in ((18.9, -1, lamp_b), (30.1, 1, lamp_b)):
        r = 5.5
        z = 1.7
        # Bezel: a short cylinder pointing out of the flank, the lens dome at its end.
        cylinder_x(bm, AX + side * 4.6, c - side * 0.2, r, z, 0.75, 0.75, housing, sides=12)
        ellipsoid(bm, P(c, r, z), (0.75 * PX, 0.62 * PX, 0.62 * PX), m, segments=12, rings=8)

    me = bpy.data.meshes.new(NAME)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in M.list:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(35))
    return obj, M


# --------------------------------------------------------------------------------------------------
# Review renders (only with --review <dir>)
# --------------------------------------------------------------------------------------------------

def review(pieces, shells, out):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    sh = scene.display.shading
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rev")
    scene.world.color = (0.035, 0.04, 0.05)
    scene.render.resolution_percentage = 100
    for s in shells:
        s.hide_render = True
    k = 8

    def cam(name, loc, look, ortho=None, lens=50, rx=900, ry=600):
        d = bpy.data.cameras.new(name)
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        d.clip_end = 500
        o = bpy.data.objects.new(name, d)
        scene.collection.objects.link(o)
        o.location = loc
        direction = Vector(look) - Vector(loc)
        o.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        scene.camera = o
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        return o

    def shot(path, flat=False, transparent=False, cavity=True):
        sh.light = "FLAT" if flat else "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_cavity = cavity and not flat
        sh.cavity_type = "BOTH"
        sh.show_object_outline = False
        sh.show_specular_highlight = not flat
        scene.render.film_transparent = transparent
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    c = cam("top", (0, 0, 20), (0, 0, 0), ortho=W / 12, rx=W * k, ry=H * k)
    c.rotation_euler = (0, 0, 0)
    shot(out / "top_mask.png", flat=True, transparent=True)
    shot(out / "top_flat.png", flat=True)
    shot(out / "top_lit.png")
    cy = (14 - 11.5) / 12  # look at the middle of the modelled part
    ext = 2.6
    views = {
        "south": ((0, -40, 0.0), (0, cy, 0.0)),   # down-screen end: what the game camera faces
        "north": ((0, 40, 0.0), (0, cy, 0.0)),
        "east": ((40, cy, 0.0), (0, cy, 0.0)),
    }
    for nm, (loc, look) in views.items():
        cam(nm, loc, look, ortho=ext, rx=800, ry=360)
        shot(out / f"{nm}.png")
    d = 9
    for nm, el, az in (("q_high", 35, 30), ("q_rear", 30, 215), ("q_low", 12, 150)):
        e, a = math.radians(el), math.radians(az)
        cam(nm, (d * math.cos(e) * math.sin(a), cy - d * math.cos(e) * math.cos(a), d * math.sin(e)), (0, cy, 0),
            lens=60, rx=800, ry=600)
        shot(out / f"{nm}.png")
    t = math.radians(32)
    cam("game", (0, cy - d * math.sin(t), d * math.cos(t)), (0, cy, 0), lens=55, rx=700, ry=600)
    shot(out / "game.png")
    cam("under", (0, 0, -20), (0, 0, 0), ortho=W / 12, rx=W * 6, ry=H * 6)
    shot(out / "under.png")
    for s in shells:
        s.hide_render = False
    cam("game_ink", (0, cy - d * math.sin(t), d * math.cos(t)), (0, cy, 0), lens=55, rx=700, ry=600)
    shot(out / "game_shell.png")


def sink_shell(shell, model, margin, reach):
    """newshk-281.py's sink_shell (copied): drop every outline-shell vertex to `margin` under the lowest
    top surface within `reach` (seen from above), so the ink stays on the silhouette (D90/D118): the
    shell's voxel remesh fills the vent channel, the intake grille and the creases by the spine."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    moved = 0
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                hh = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if hh[0] is not None:
                    zt = min(zt, hh[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(ROOT, PIECES[0])
    coll = common.reset_collection(NAME)
    obj, M = build(coll, sprite)
    layout = [(e["model"], e["cx"] - 123, e["cy"] + 17) for e in sprite["assemblyLayout"]]
    assert [l[0] for l in layout] == PIECES and [l[1:] for l in layout] == [(-12, 0), (12, 0)], layout
    pieces = common.split_assembly(obj, layout)
    bpy.data.objects.remove(obj, do_unlink=True)
    shells = []
    shells_by = {}
    out_objs = []
    total = 0
    for name, cx, cy in layout:
        p = pieces[name]
        for poly in p.data.polygons:
            poly.use_smooth = True
        p.data.set_sharp_from_angle(angle=math.radians(35))
        tris = sum(len(f.vertices) - 2 for f in p.data.polygons)
        total += tris
        print(f"{name}: {len(p.data.polygons)} faces, {tris} tris")
        # Outline shell from a sealed copy (nothing is culled in this design; D90/D118), every island
        # that widens the top view keeps its ink (D189).
        src = bpy.data.objects.new(f"{name}_sealed", p.data.copy())
        coll.objects.link(src)
        bpy.context.view_layer.update()
        shl = common.outline_shell(src, coll, voxel=0.012, faces=2500, inside=0.004, islands="outer")
        sink_shell(shl, src, 0.5 * PX, 1.2 * PX)
        bpy.data.objects.remove(src, do_unlink=True)
        shl.name = shl.data.name = f"{name}_outline"
        assert len(shl.data.polygons) > 0, f"empty outline shell for {name}"
        # Placed at the piece's place in the assembly (the game's export puts each at its own origin).
        p.location = (cx / 12, -cy / 12, 0)
        shl.location = p.location
        shells.append(shl)
        shells_by[name] = shl
        out_objs += [p, shl]
    print(f"total tris {total}")
    if "--out" in argv:  # a review copy of the whole machine, not the game export
        out = common.export_glb(out_objs, argv[argv.index("--out") + 1])
        print("review copy", out)
    else:
        for name, cx, cy in layout:
            data = common.load_sprite(ROOT, name)
            p, shl = pieces[name], shells_by[name]
            p.location = (0, 0, 0)
            shl.location = (0, 0, 0)
            common.export_sprite_model(ROOT, [p, shl], f"enemies/{name}", data["sprites"])
    if "--review" in argv:
        review([pieces[n] for n in PIECES], shells, Path(argv[argv.index("--review") + 1]))


if __name__ == "__main__":
    main()
