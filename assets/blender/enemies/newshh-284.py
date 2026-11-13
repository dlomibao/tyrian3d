"""newshh-284: a small blue-steel gun drone (newshh.shp frame 284, 24x28 block, one frame).

What it is: a squat flying gun drone (enemy type 795, top layer, turret 131 fires). It swoops
sideways at up to 14 px/tick (GRYPHON) and weaves while drifting down (MISTAKES): it flies free, so
it is centred near z = 0 with a round, closed underside. Nose down the screen (row 20), as drawn.

Reading of the sprite (column/row edges of the 24x28 block; inner mask = outer minus the ink ring,
D74; the edge columns 0/23 at rows 9-14 are colour to the edge, so the wing tips reach x = +-12):
- Two engine nacelles, columns 6-10 and 13-17, rows 2-10: square-ended at the back (row 2), the
  shell grey 101 with a lit top deck (column 9/14, 103).
- On each nacelle, a long teal glass strip, columns 7-8 / 15-16, rows 2-10 (ramp 210-218, median
  212): a raised sensor/intake window; its rear end (row 2, 50/51) is dark: the intake mouth.
  The 218 pixels (row 7) are sheen on the glass, not geometry.
- Between the nacelles, columns 11-12, rows 3-10: a dark recessed channel (50) crossed by slats lit
  at rows 6 and 9 (99): a cooling grille.
- A pale transverse crest, rows 10-12, columns 5-18 (median 105): a collar across the front of the
  nacelles, its forward slope lit.
- A broad tapered wing, rows 4-15 at the root to rows 9-14 at the tips (median 101): straight front
  edge at row 16, swept rear edge stepping 3 -> 4 -> 5 -> 6 -> 9; two raised chordwise ribs per side
  (columns 2, 4 / 19, 21, median 103) on it.
- A faceted chisel nose, rows 13-19 (median 102), half width 5, 4, 3, 2 px per row to a blunt tip
  at row 20; dark gun ports (98) at row 13, columns 8 and 15: two short level gun barrels
  (turret 131) in housings (100) on the nose flanks.
Underside: the same lofts closed round below, nothing else.

Run: blender --background --python assets/blender/enemies/newshh-284.py [-- --views DIR]
Exports public/models/enemies/newshh-284.glb (model + outline shell, D51/D90) and the
src/render/spriteModels entry: one frame, pal_<index> materials.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshh-284"
PX = 1 / 12

# Material slots -> palette index (trimmed medians of each region, darkest/brightest left out).
(WING, RIB, POD, POD_TOP, GLASS, MOUTH, BEZEL, CORE, SLAT, CREST, NOSE, FLANK, GUN, PORT,
 EXH) = range(15)
PAL = {WING: 101, RIB: 103, POD: 101, POD_TOP: 103, GLASS: 212, MOUTH: 51, BEZEL: 104, CORE: 50,
       SLAT: 99, CREST: 105, NOSE: 102, FLANK: 101, GUN: 100, PORT: 98, EXH: 50}
# (metallic, roughness, emission): satin blue steel; glass glossy with a faint glow so it stays teal.
SPEC = {WING: (0.38, 0.45, 0), RIB: (0.45, 0.38, 0), POD: (0.38, 0.45, 0), POD_TOP: (0.45, 0.38, 0),
        GLASS: (0.35, 0.14, 0.3), MOUTH: (0.3, 0.5, 0), BEZEL: (0.55, 0.36, 0), CORE: (0.4, 0.6, 0),
        SLAT: (0.45, 0.45, 0), CREST: (0.45, 0.36, 0), NOSE: (0.42, 0.4, 0), FLANK: (0.38, 0.45, 0),
        GUN: (0.6, 0.38, 0), PORT: (0.3, 0.6, 0), EXH: (0.4, 0.6, 0)}


STEEL = (WING, RIB, POD, POD_TOP, BEZEL, CREST, NOSE, FLANK, SLAT)
STEEL_SPEC = 0.5 * ((0.8 / 2.8) ** 2 / 0.04)  # F0 of IOR 1.8 (0.082) as a Specular IOR Level


def P(u, r, z):
    """Sprite space (u px right of centre, r row edge down the block, z px up) -> model units."""
    return (u * PX, (14.0 - r) * PX, z * PX)


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()
        self.facet = {}
        self.part = 0

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, vs, mat, smooth=True):
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        face.smooth = smooth
        return face

    def loft(self, rings, matfn, cap0=None, cap1=None, smooth=True, facets=None):
        """rings: point lists of equal length (closed loops). matfn(band, edge) -> material.
        cap0/cap1: material of an end cap (None: no cap). facets(edge) -> id: edges between
        faces of different ids are hard (the chamfers of a hard-surface section stay crisp)."""
        self.part += 1
        base = self.part * 1000
        vs = [[self.v(p) for p in rg] for rg in rings]
        for k, (a, b) in enumerate(zip(vs, vs[1:])):
            n = len(a)
            for i in range(n):
                j = (i + 1) % n
                fc = self.f((a[i], a[j], b[j], b[i]), matfn(k, i), smooth)
                if fc is not None:
                    self.facet[fc] = base + (facets(i) if facets else 0)
        for cap, ring, rev in ((cap0, vs[0], False), (cap1, vs[-1], True)):
            if cap is not None:
                fc = self.f(list(reversed(ring)) if rev else list(ring), cap, smooth=False)
                if fc is not None:
                    self.facet[fc] = base + 999

    def harden(self, angle=32):
        """Sharp edges: between facets of a section, and wherever faces meet at more than `angle`."""
        lim = math.radians(angle)
        for e in self.bm.edges:
            lf = e.link_faces
            if len(lf) != 2:
                continue
            a, b = lf[0], lf[1]
            fa, fb = self.facet.get(a), self.facet.get(b)
            if (fa is not None and fb is not None and fa != fb) or e.calc_face_angle(0.0) > lim:
                e.smooth = False

    def hull(self, pts, mat):
        """Convex hull of points (a chamfered block), its faces in one material."""
        T.hull(self, [tuple(p) for p in pts], mat)


# usp_talon.hull appends orientation hints to part.hints; we recalc normals instead.
Mesh.hints = []


def cbox(u0, u1, r0, r1, z0, z1, ch, chz=None):
    """A chamfered box in sprite space (corner points in model units)."""
    return [P(*p) for p in T.cbox(u0, u1, r0, r1, z0, z1, ch, chz)]


# --- Plan curves (pchip through the middles of the inner mask's steps, D52/D118) -----------------

# Wing rear edge, |u| -> row edge: the mask's rear edge steps 3 (|u|<6), 4 (<7), 5 (<9), 6 (<11), 9.
REAR = T.pchip([3.0, 6.0, 7.0, 9.0, 10.5, 11.0, 11.5, 11.85, 12.0], [3.2, 3.5, 4.5, 5.5, 6.2, 6.8, 8.0, 9.0, 9.6])
# Wing front edge: row 16 out to |u| 11, row 15 at the tip column, the corner rounded.
FRONT = T.pchip([0.0, 10.2, 11.0, 11.6, 12.0], [16.0, 16.0, 15.55, 15.15, 14.5])
# Nose half width per row edge: 5, 4, 3, 2 px at rows 16-19 to a blunt tip at row 20.
NOSE_HW = T.pchip([10.5, 13.0, 15.5, 16.5, 17.5, 18.5, 19.5, 20.0], [5.7, 5.7, 5.55, 4.95, 3.95, 2.95, 1.95, 1.1])
NOSE_TOP = T.pchip([10.5, 12.5, 16.0, 20.0], [3.3, 3.2, 2.5, 1.3])
NOSE_BOT = T.pchip([10.5, 15.0, 20.0], [-2.1, -1.8, -0.3])


def section(cu, hw, ztop, zmid, zbot, ch, chz=None, n=8):
    """A hard-topped, round-bottomed section in (u, z): flat deck, 45-ish chamfered shoulders,
    straight sides down to zmid, then a half ellipse underneath. n+5 points; edge n+2 is the deck,
    n+1 / n+3 the shoulders."""
    chz = ch if chz is None else chz
    pts = []
    for k in range(n + 1):
        a = -math.pi * k / n
        pts.append((cu + hw * math.cos(a), zmid + (zmid - zbot) * math.sin(a)))
    pts += [(cu - hw, ztop - chz), (cu - hw + ch, ztop), (cu + hw - ch, ztop), (cu + hw, ztop - chz)]
    return pts


def sec_facets(n):
    """Facet ids for section(): the round belly is one smooth facet, every flat edge its own."""
    return lambda i: 0 if i < n else i


def frange(a, b, step):
    out, x = [], a
    while x < b - 1e-9:
        out.append(x)
        x += step
    out.append(b)
    return out


# --- Parts ----------------------------------------------------------------------------------------

def build_wing(M):
    """One tapered plate from tip to tip, a chamfered hexagon section lofted along the span."""
    z0 = 0.35

    def sec(u, shrink=0.0, thin=1.0):
        a = abs(u)
        rf, rr = FRONT(a) - shrink, REAR(a) + shrink
        t = (1.55 - 0.85 * max(0.0, a - 4.0) / 8.0) * thin
        b = (1.15 - 0.6 * max(0.0, a - 4.0) / 8.0) * thin
        cf, cr = min(0.7, (rf - rr) * 0.2), min(0.5, (rf - rr) * 0.15)
        pts = [(rf, z0), (rf - cf, z0 + t), (rr + cr, z0 + t), (rr, z0 + 0.15 * t),
               (rr + cr * 1.2, z0 - b), (rf - cf * 1.4, z0 - b)]
        return [P(u, r, z) for r, z in pts]

    inner = [x * 0.5 for x in range(-20, 21)]  # -10 .. 10 by 0.5
    us = [-11.92, -11.75, -11.5, -11.2, -10.9, -10.6, -10.3] + inner + [10.3, 10.6, 10.9, 11.2, 11.5, 11.75, 11.92]
    rings = [sec(u) for u in us]
    rings = [sec(-12.0, 0.3, 0.7)] + rings + [sec(12.0, 0.3, 0.7)]
    # Wing tips mirror: the loft runs -u -> +u, so the ring order (r, z) is the same at every station.
    M.loft(rings, lambda k, i: WING, cap0=WING, cap1=WING, facets=lambda i: i)


def wing_top(u):
    a = abs(u)
    return 0.35 + (1.55 - 0.85 * max(0.0, a - 4.0) / 8.0)


def build_ribs(M):
    """Two raised chordwise ribs per side (columns 2 and 4), level along their length."""
    for uc in (7.5, 9.5):
        for s in (-1, 1):
            u = s * uc
            r0, r1 = REAR(uc) + 0.9, FRONT(uc) - 0.9
            zt = wing_top(uc + 0.4) - 0.1
            M.hull(cbox(u - 0.48, u + 0.48, r0, r1, zt - 0.3, zt + 0.55, 0.22, 0.2), RIB)


def build_core(M):
    """The body under and between the nacelles: its deck is the floor of the dark grille channel."""
    rs = frange(3.0, 12.0, 1.5)
    rings = []
    for r in rs:
        hw = 4.6 if r > 3.2 else 4.2
        rings.append([P(u, r, z) for u, z in section(0.0, hw, 2.2, 0.4, -2.0, 0.8)])
    M.loft(rings, lambda k, i: CORE, cap0=CORE, cap1=CORE, facets=sec_facets(8))


def build_slats(M):
    """Grille slats across the channel between the nacelles (lit 99 at rows 6 and 9)."""
    for rc in (3.9, 6.4, 9.2):
        M.hull(cbox(-1.6, 1.6, rc - 0.45, rc + 0.45, 1.8, 2.85, 0.15, 0.15), SLAT)


def build_pods(M):
    """Two engine nacelles (columns 6-10 / 13-17), square-ended rear (row 2) to the crest (row 10.6)."""
    N = 8
    for s in (-1, 1):
        cu = s * 3.6
        st = [(2.0, 1.7, 3.5, 0.5), (2.12, 2.15, 3.85, 0.7), (2.4, 2.38, 4.0, 0.85), (2.9, 2.42, 4.05, 0.9)]
        st += [(r, 2.42, 4.05, 0.9) for r in frange(3.6, 10.6, 1.4)]
        rings = []
        for r, hw, zt, ch in st:
            pts = section(cu, hw, zt, 2.0, 0.2, ch, 0.8, n=N)
            rings.append([P(u, r, z) for u, z in pts])

        def mat(k, i):
            return POD_TOP if i == N + 2 else POD
        M.loft(rings, mat, cap0=EXH, cap1=POD, facets=sec_facets(N))
        # Exhaust nozzle: a dark ring proud of the rear face.
        ring_o = [P(cu + 1.15 * math.cos(2 * math.pi * j / 12), 1.7, 2.1 + 0.95 * math.sin(2 * math.pi * j / 12)) for j in range(12)]
        ring_i = [P(cu + 0.95 * math.cos(2 * math.pi * j / 12), 2.3, 2.1 + 0.8 * math.sin(2 * math.pi * j / 12)) for j in range(12)]
        M.loft([ring_i, ring_o], lambda k, i: GUN, cap0=None, cap1=EXH)


def build_glass(M):
    """The teal glass strip on each nacelle (columns 7-8 / 15-16): a raised lens in a bezel, its
    rear end the dark intake mouth (row 2)."""
    N = 8
    for s in (-1, 1):
        cu = s * 4.0
        # bezel plate
        M.hull(cbox(cu - 1.25, cu + 1.25, 2.35, 10.4, 3.7, 4.2, 0.2, 0.15), BEZEL)
        rings = []
        rs = [2.45, 2.6, 3.0, 3.25] + frange(3.8, 9.6, 1.0) + [10.0, 10.25]
        for r in rs:
            e = 1.0 if 2.6 <= r <= 10.0 else 0.8
            h = 0.5 if 2.6 <= r <= 10.0 else 0.25
            pts = []
            for j in range(N + 1):
                a = math.pi * j / N
                pts.append((cu + e * 0.95 * math.cos(a), 4.15 + h * math.sin(a)))
            pts.append((cu - e * 0.95, 4.05))
            pts.append((cu + e * 0.95, 4.05))
            rings.append([P(u, r, z) for u, z in pts])

        def mat(k, i):
            return MOUTH if k < 3 else GLASS
        M.loft(rings, mat, cap0=MOUTH, cap1=GLASS, facets=lambda i: 0 if i < N else i)


def build_crest(M):
    """The pale collar across the nacelles' fronts (rows 10-12, columns 5-18), its front slope lit."""
    sec = [(10.1, 0.8), (10.1, 3.45), (10.45, 3.85), (11.35, 3.85), (12.95, 2.5), (12.95, 0.8)]

    def ring(u, inset):
        c = Vector((11.5, 2.3))
        out = []
        for r, z in sec:
            p = Vector((r, z))
            p = p + (c - p).normalized() * inset if inset else p
            out.append(P(u, p.x, p.y))
        return out
    us = [-6.85, -6.6] + frange(-6.0, 6.0, 1.0) + [6.6, 6.85]
    rings = [ring(u, 0.3 if abs(u) > 6.7 else 0.0) for u in us]
    M.loft(rings, lambda k, i: CREST, cap0=CREST, cap1=CREST, smooth=False)


def build_nose(M):
    """Faceted chisel nose from under the crest to the blunt tip (row 20): a narrow deck, broad
    chamfer facets down to straight flanks, a round belly."""
    N = 8
    rs = frange(10.5, 19.5, 0.5) + [19.8, 20.0]
    rings = []
    for r in rs:
        hw = NOSE_HW(r)
        zt = NOSE_TOP(r)
        ch = hw * 0.55
        chz = min(1.4, zt - 0.6)
        pts = section(0.0, hw, zt, 0.45, NOSE_BOT(r), ch, chz, n=N)
        rings.append([P(u, r, z) for u, z in pts])

    def mat(k, i):
        return NOSE if i in (N + 1, N + 2, N + 3) else FLANK
    M.loft(rings, mat, cap0=None, cap1=NOSE, facets=sec_facets(N))
    # Tip cap inset: a small blunt muzzle plate at the tip.
    M.hull(cbox(-0.8, 0.8, 19.7, 20.15, 0.2, 1.1, 0.15), GUN)


def build_guns(M):
    """Twin gun housings on the nose flanks (dark ports at row 13, columns 8 / 15) with short level
    barrels forward (turret 131)."""
    for s in (-1, 1):
        u = s * 3.5
        # fairing on the nose facet (hull grey), its front a dark gun port
        M.hull(cbox(u - 0.85, u + 0.85, 12.2, 14.4, 1.9, 3.15, 0.3, 0.25), FLANK)
        M.hull(cbox(u - 0.6, u + 0.6, 14.3, 14.55, 2.0, 2.95, 0.12), PORT)
        rings = []
        for r, rad in ((14.4, 0.42), (15.6, 0.42), (15.6, 0.5), (16.2, 0.5)):
            rings.append([P(u + rad * math.cos(2 * math.pi * j / 8), r, 2.45 + rad * math.sin(2 * math.pi * j / 8))
                          for j in range(8)])
        M.loft(rings, lambda k, i: GUN, cap0=GUN, cap1=PORT)


def materials(sprite):
    out = []
    for slot in range(15):
        m, r, e = SPEC[slot]
        mat = common.palette_material(sprite, PAL[slot], f"{NAME}_A_{slot}", metallic=m, roughness=r,
                                      emission_strength=e)
        if slot in STEEL:
            # Polished blue steel: raise F0 (about IOR 1.8) through Specular IOR Level, which the
            # exporter writes as KHR_materials_specular (D176); a bare IOR is dropped.
            bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            bsdf.inputs["Specular IOR Level"].default_value = STEEL_SPEC
        out.append(mat)
    return out


def build(sprite, coll):
    M = Mesh()
    build_wing(M)
    build_ribs(M)
    build_core(M)
    build_slats(M)
    build_pods(M)
    build_glass(M)
    build_crest(M)
    build_nose(M)
    build_guns(M)
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    M.facet = {f: i for f, i in M.facet.items() if f.is_valid}
    M.harden()
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in materials(sprite):
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    return obj


def build_model(sprite):
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles")
    bpy.context.view_layer.update()
    sh = common.outline_shell(sealed, coll, voxel=0.03, faces=1500, smooth=6, inside=0.004)
    sh.name = f"{NAME}_outline"
    bpy.data.objects.remove(sealed, do_unlink=True)
    return [obj, sh], tris


# --- Review renders (scratch only) ----------------------------------------------------------------

def _cam(location, look_at, ortho=None, fov=None, top=False, up="Y"):
    data = bpy.data.cameras.new("cam")
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.sensor_fit = "VERTICAL"
        data.angle_y = math.radians(fov)
    cam = bpy.data.objects.new("cam", data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (0, 0, 0) if top else (Vector(look_at) - Vector(location)).to_track_quat("-Z", up).to_euler()
    return cam


def _render(cam, path, rx, ry):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = rx, ry
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)


def views(objs, out):
    out.mkdir(parents=True, exist_ok=True)
    model, shell = objs
    shell.hide_render = True
    sc = bpy.context.scene
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    k = 10
    ext = 28 * PX
    # silhouette (workbench flat)
    try:
        sc.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    sc.display.shading.light = "FLAT"
    sc.display.shading.color_type = "SINGLE"
    sc.display.shading.single_color = (1, 1, 1)
    sc.display.shading.show_object_outline = False
    sc.display.shading.show_cavity = False
    _render(_cam((0, 0, 20), (0, 0, 0), ortho=ext, top=True), out / "top_sil.png", 24 * k, 28 * k)
    sc.display.shading.color_type = "MATERIAL"
    _render(_cam((0, 0, 20), (0, 0, 0), ortho=ext, top=True), out / "top_flat.png", 24 * k, 28 * k)
    # game-lit views (EEVEE), as tools/proto/review_render.py's setup_game
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE"
    world = sc.world or bpy.data.worlds.new("game")
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.45, 0.55, 1.0)
    bg.inputs[1].default_value = 1.0
    sd = bpy.data.lights.new("sun", "SUN")
    sd.energy = 3.0
    sun = bpy.data.objects.new("sun", sd)
    sc.collection.objects.link(sun)
    sun.rotation_euler = Vector((-6, -8.4, 20)).normalized().to_track_quat("Z", "Y").to_euler()
    _render(_cam((0, 0, 20), (0, 0, 0), ortho=ext, top=True), out / "top_game.png", 24 * k, 28 * k)
    span = ext * 1.15
    _render(_cam((30, 0, 0), (0, 0, 0), ortho=span, up="Y"), out / "side.png", 480, 320)
    _render(_cam((0, -30, 0), (0, 0, 0), ortho=span, up="Y"), out / "front.png", 480, 320)
    _render(_cam((0, 30, 0), (0, 0, 0), ortho=span, up="Y"), out / "rear.png", 480, 320)
    d = ext * 1.45 + 1.5
    _render(_cam((d * 0.55, -d * 0.6, d * 0.55), (0, 0, 0), fov=30, up="Y"), out / "q1.png", 480, 480)
    _render(_cam((-d * 0.6, d * 0.5, d * 0.65), (0, 0, 0), fov=30, up="Y"), out / "q2.png", 480, 480)
    tilt = math.radians(32)
    _render(_cam((0, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0), fov=30), out / "game.png", 480, 480)
    # off-axis game camera (enemy near the screen's left side)
    _render(_cam((1.4, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0), fov=30), out / "game_side.png", 480, 480)
    _render(_cam((0.01, -0.6, -20), (0, 0, 0), ortho=ext * 1.1, up="Y"), out / "under.png", 320, 320)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    objs, tris = build_model(sprite)
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"])
    if "--views" in argv:
        views(objs, Path(argv[argv.index("--views") + 1]))


main()
