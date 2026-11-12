"""newshv-8 : the MARKERS (2.8) red-lamp marker beacon, newshv.shp frame 8, 24 x 28 px.

WHAT IT IS: a course-marker buoy floating in space. Type 810: mv(0,2), armour 254, no turret, no
launcher, so it never fires; 337 spawn on ground(25) at x = 10..60 and 333 on ground2(75) at
x = 230..280: two columns of beacons lining the course edges. The 2.8 capture shows them over the
starfield (shapesz space tiles), so it is not a ground emplacement: it floats free, a closed,
rounded underside and nothing standing on a floor. Not a turret.

Reading the sprite (rubric "Reading a sprite"; the ink ring and the shading are lighting):
- Rows 8-14, cols 2-21: the rear lamp deck. Its rear corners are cut (row 8 starts at col 3).
- Rows 8-13, cols 2-7 and 16-21: two big glowing red lamp domes, one on each side of the deck,
  their darker red edge (112-114) the lens rim, the hot spot (124/122/121/120 at cols 4-5 and
  18-19, rows 9-10) the lamp's bright core showing through the lens, a little to the rear.
- Rows 6-13, cols 8-15: a pale beacon head (transponder housing) standing up between the lamps:
  a barrel-vaulted crown (rows 6-10; cols 11-12 brightest = a raised spine, cols 10 and 13 a step
  darker on every row = two machined grooves), dark shoulders (cols 8 and 15, 96-101) and a sloped
  front face in shade (rows 11-13, 101-103) carrying a louvred vent.
- Row 14, cols 3-20: a waist, 1 px narrower each side: the seam between the lamp deck and the
  front body.
- Rows 15-19: the front body, its two forward pontoons (cols 2-8 / 15-21, out to row 19, the inner
  front corner cut) and the lower nose between them (to row 17). Row 15, cols 9-14: two small red
  sensor eyes (115 at cols 10 / 13) in dark sockets (the ink at cols 9 / 14).

Colours (trimmed medians of each region's palette indices): body 104, beacon crown 109, crown
shoulders 99, front face 103, lamp lens 116 (glowing, D126), lens rim 113, lamp core 122, eyes 115.
Satin metal (metallic 0.3-0.4, roughness 0.35-0.5).

Units while building: sprite px (x = column edge - 12, y = row edge down the screen = forward,
z up), moved to Blender by finish(): X = x / 12, Y = (14 - y) / 12, Z = z / 12.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshv-8.py  (or blender -b --python newshv-8.py -- [--render DIR] [--bake]
Exports public/models/enemies/newshv-8.glb and src/render/spriteModels/newshv-8.json (common.export_sprite_model).
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(WT / "assets" / "blender")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "newshv-8"
PX = 1 / 12
W, H = 24, 28


# --- helpers (copied from e1 design scripts; candidates for a shared lib) -------------------------
def finish(part, mats, coll, smooth_angle=None):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, H / 2 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
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


class Mats:
    def __init__(self, sprite, tag):
        self.sprite, self.tag = sprite, tag
        self.list, self.slots = [], {}

    def __call__(self, index, part, metallic=0.35, roughness=0.42, emission=0.0):
        key = (index, part)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, f"{self.tag}_{part}", metallic=metallic,
                                                     roughness=roughness, emission_strength=emission))
        return self.slots[key]


def rrect(x0, x1, y0, y1, radii, d=0.0, k=5):
    """Rounded rectangle inset by d, corners (rear-left, rear-right, front-right, front-left) with
    their own radii; the same vertex count whatever the inset, so rings loft into quads."""
    x0, x1, y0, y1 = x0 + d, x1 - d, y0 + d, y1 - d
    pts = []
    corners = [((x0, y0), math.pi, 1.5 * math.pi, (1, 1)), ((x1, y0), 1.5 * math.pi, 2 * math.pi, (-1, 1)),
               ((x1, y1), 0.0, 0.5 * math.pi, (-1, -1)), ((x0, y1), 0.5 * math.pi, math.pi, (1, -1))]
    for (cx, cy), a0, a1, (sx, sy), r in zip([c[0] for c in corners], [c[1] for c in corners],
                                             [c[2] for c in corners], [c[3] for c in corners], radii):
        rr = max(r - d, 0.06)
        ox, oy = cx + sx * rr, cy + sy * rr
        for i in range(k + 1):
            a = a0 + (a1 - a0) * i / k
            pts.append((ox + rr * math.cos(a), oy + rr * math.sin(a)))
    return pts


def squircle(cx, cy, a, p, n=32):
    out = []
    for i in range(n):
        t = 2 * math.pi * (i + 0.5) / n
        c, s = math.cos(t), math.sin(t)
        out.append((cx + a * math.copysign(abs(c) ** (2 / p), c), cy + a * math.copysign(abs(s) ** (2 / p), s)))
    return out


def stack(P, rings, mats, cap_bottom=True, cap_top=True, top_mat=None):
    """Loft horizontal rings [(points2d, z)] bottom to top; mats[i] between ring i and i + 1."""
    built = []
    for pts, z in rings:
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        built.append(([P.v((x, y, z)) for x, y in pts], (cx, cy)))
    for i in range(len(built) - 1):
        r0, (cx, cy) = built[i]
        r1 = built[i + 1][0]
        zm = (rings[i][1] + rings[i + 1][1]) / 2
        n = len(r0)
        for a in range(n):
            b = (a + 1) % n
            q = [r0[a], r0[b], r1[b], r1[a]]
            c = sum((v.co for v in q), Vector()) / 4
            m = mats[i](c) if callable(mats[i]) else mats[i]
            P.f(q, m, out=(c.x - cx, c.y - cy, 0.0 if abs(rings[i + 1][1] - rings[i][1]) > 1e-6 else
                           (1.0 if rings[i + 1][1] >= rings[i][1] else -1.0)))
    if cap_bottom:
        P.f(built[0][0], mats[0] if not callable(mats[0]) else mats[0](Vector()), out=(0, 0, -1))
    if cap_top:
        m = top_mat if top_mat is not None else mats[-1]
        P.f(built[-1][0], m, out=(0, 0, 1))


# Profile of every body block, bottom to top: (inset, z) with z as a fraction-free height; a rounded
# belly (plain, closed), straight walls, a machined seam groove round the sides, chamfered top.
def body_profile(top):
    return [(1.9, 0.0), (1.05, 0.35), (0.42, 0.9), (0.1, 1.45), (0.0, 1.85),
            (0.0, top - 1.05), (0.13, top - 1.0), (0.13, top - 0.82), (0.0, top - 0.77),
            (0.0, top - 0.3), (0.09, top - 0.1), (0.3, top)]


def body_block(P, x0, x1, y0, y1, radii, top, mat, k=5):
    rings = [(rrect(x0, x1, y0, y1, radii, d, k), z) for d, z in body_profile(top)]
    stack(P, rings, [mat] * (len(rings) - 1))


def hull_pts(P, pts, mat):
    T.hull(P, pts, mat)


# =================================================================================================
# the beacon
# =================================================================================================
DECK_TOP = 3.0
LAMP = [(-7.0, 11.0), (7.0, 11.0)]      # lamp centres (x, y): cols 2-7 / 16-21, rows 8-13
LAMP_A, LAMP_P = 2.62, 2.7             # lens half-size and squircle exponent
LENS_Z, LENS_H = 3.25, 2.75            # lens foot and height above it
CORE = (0.0, -0.9, 1.05)               # core patch: dx (outward), dy, radius


def lens_z(dx, dy):
    rho = ((abs(dx) / LAMP_A) ** LAMP_P + (abs(dy) / LAMP_A) ** LAMP_P) ** (1 / LAMP_P)
    return LENS_Z + LENS_H * math.sqrt(max(0.0, 1 - rho * rho))


def build_body(P, M):
    body = M(104, "body", 0.35, 0.42)
    # rear lamp deck (rows 8-14, cols 2-21), rear corners cut
    body_block(P, -10.0, 10.0, 7.95, 14.25, (1.35, 1.35, 0.5, 0.5), DECK_TOP, body)
    # the waist (row 14, cols 3-20): a lower neck between deck and front body = a seam all round
    body_block(P, -9.05, 9.05, 13.6, 15.4, (0.3, 0.3, 0.3, 0.3), DECK_TOP - 0.3, body)
    # front body between the pontoons, the nose to row 17
    body_block(P, -4.6, 4.6, 14.75, 18.0, (0.4, 0.4, 0.55, 0.55), DECK_TOP - 0.15, body)
    # the pontoons (cols 2-8 / 15-21, rows 15-19), the inner front corner cut
    for s in (-1, 1):
        if s < 0:
            body_block(P, -10.0, -3.0, 14.75, 20.0, (0.45, 0.45, 1.35, 0.6), DECK_TOP, body)
        else:
            body_block(P, 3.0, 10.0, 14.75, 20.0, (0.45, 0.45, 0.6, 1.35), DECK_TOP, body)


def build_pontoon_detail(P, M):
    dark = M(99, "vent", 0.3, 0.6)
    trim = M(106, "trim", 0.45, 0.32)
    for s in (-1, 1):
        cx = s * 6.3
        # front vent: a dark grille plate in the pontoon's nose with two bars across it
        T.hull(P, T.cbox(cx - 1.75, cx + 1.75, 19.72, 20.07, 1.55, 2.45, 0.08), dark)
        for zb in (1.83, 2.15):
            T.hull(P, T.cbox(cx - 1.6, cx + 1.6, 19.9, 20.12, zb - 0.07, zb + 0.07, 0.03), trim)
        # four cap bolts on the pontoon's top
        for bx in (cx - 2.3, cx + 2.3):
            for by in (15.9, 18.9):
                if s < 0 and bx > cx and by > 18:
                    bx -= 0.5
                if s > 0 and bx < cx and by > 18:
                    bx += 0.5
                bolt(P, bx, by, DECK_TOP - 0.02, 0.32, 0.2, trim)


def bolt(P, x, y, z, r, h, mat, n=8):
    ring0 = [(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    ring1 = [(x + 0.7 * r * math.cos(2 * math.pi * i / n), y + 0.7 * r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    stack(P, [(ring0, z - 0.1), (ring0, z + h * 0.6), (ring1, z + h)], [mat, mat])


def build_eyes(P, M):
    sock = M(99, "socket", 0.25, 0.6)
    eye = M(115, "eye", 0.0, 0.3, emission=1.2)
    rim = M(106, "trim", 0.45, 0.32)
    top = DECK_TOP - 0.15
    for s in (-1, 1):
        # socket: a dark sensor cowl, cols 9-10 / 13-14 of row 15, the lens at its inner end
        x0, x1 = (-3.05, -0.95) if s < 0 else (0.95, 3.05)
        T.hull(P, T.cbox(x0, x1, 14.95, 16.05, top - 0.3, top + 0.32, 0.18), sock)
        # its bright lip along the front (row 16, cols 10-13 are lighter)
        T.hull(P, T.cbox(x0 + 0.1, x1 - 0.1, 15.95, 16.3, top - 0.2, top + 0.22, 0.08), rim)
        # the red lens (cols 10 / 13): a small dome looking forward and up
        ex = s * 1.5
        rings = []
        n = 12
        for t, (rr, zz) in enumerate(((0.5, top + 0.2), (0.48, top + 0.36), (0.38, top + 0.5), (0.2, top + 0.58),
                                      (0.04, top + 0.61))):
            rings.append(([(ex + rr * math.cos(2 * math.pi * i / n), 15.5 + rr * math.sin(2 * math.pi * i / n))
                           for i in range(n)], zz))
        stack(P, rings, [eye] * 4)


def build_lamps(P, M):
    bezel = M(101, "bezel", 0.4, 0.38)
    rimc = M(113, "lens_rim", 0.0, 0.25, emission=0.55)
    lens = M(116, "lens", 0.0, 0.2, emission=1.0)
    core = M(122, "core", 0.0, 0.2, emission=1.5)
    for cx, cy in LAMP:
        side = 1 if cx > 0 else -1
        # bezel: a machined ring housing the lens, standing on the deck
        outer = lambda d: squircle(cx, cy, 2.98 - d, 3.3)  # noqa: E731
        inner = squircle(cx, cy, LAMP_A + 0.05, LAMP_P)
        rings = [(outer(0.0), DECK_TOP - 0.25), (outer(0.0), DECK_TOP + 0.35), (outer(0.12), DECK_TOP + 0.52),
                 (squircle(cx, cy, 2.75, 3.0), DECK_TOP + 0.58)]
        stack(P, rings, [bezel] * 3, cap_top=True, top_mat=bezel)
        # lens: a squircle dome, its lower band the darker rim
        nr = 9
        rings = []
        mats = []
        for i in range(nr + 1):
            th = (math.pi / 2) * (i / nr) * 0.985
            a = LAMP_A * math.cos(th)
            z = LENS_Z + LENS_H * math.sin(th)
            if i == 0:
                z = DECK_TOP + 0.4
            if i in (4, 7):  # Fresnel steps in the lens
                rings.append((squircle(cx, cy, a + 0.09, LAMP_P), z))
                mats.append(lens)
            rings.append((squircle(cx, cy, a, LAMP_P), z))
            if i < nr:
                mats.append(rimc if i < 1 else lens)
        stack(P, rings, mats)
        # the lamp core seen through the lens: a flush glowing patch conformed to the lens
        px, py, pr = cx + side * CORE[0], cy + CORE[1], CORE[2]
        n = 18
        built = []
        for rr, dz in ((pr, -0.05), (pr * 0.82, 0.035), (pr * 0.5, 0.06), (pr * 0.18, 0.065)):
            pts = [(px + rr * math.cos(2 * math.pi * i / n), py + 0.95 * rr * math.sin(2 * math.pi * i / n))
                   for i in range(n)]
            built.append([P.v((x, y, lens_z(x - cx, y - cy) + dz)) for x, y in pts])
        for r0, r1 in zip(built, built[1:]):
            for a in range(n):
                b = (a + 1) % n
                P.f([r0[a], r0[b], r1[b], r1[a]], core, out=(0, 0, 1))
        P.f(built[-1], core, out=(0, 0, 1))
        cen = P.v((px, py, lens_z(px - cx, py - cy) - 0.25))
        for a in range(n):
            b = (a + 1) % n
            P.f([built[0][b], built[0][a], cen], core, out=(0, 0, -1))


# --- beacon head --------------------------------------------------------------------------------
HEAD_W = 4.0       # half width (cols 8-15)
HEAD_ZB = 1.2      # foot, inside the deck (its rear overhangs the deck to a rounded bottom)
HEAD_TOP = 8.3


def head_stations():
    # (y, half width, crown height, groove depth, region)  region: 0 crown, 1 front face
    ys = [5.95, 6.05, 6.2, 6.45, 6.8, 7.3, 8.2, 9.4, 10.4, 10.75, 11.3, 12.2, 13.1, 13.9, 14.3]
    wf = T.pchip([5.95, 6.3, 6.7, 7.2, 14.3], [2.7, 3.4, 3.82, 4.0, 4.0])
    zf = T.pchip([5.95, 6.05, 6.2, 6.45, 6.8, 7.3, 10.4, 10.75, 14.3],
                 [HEAD_TOP - 2.6, HEAD_TOP - 1.55, HEAD_TOP - 0.85, HEAD_TOP - 0.38, HEAD_TOP - 0.12, HEAD_TOP,
                  HEAD_TOP, HEAD_TOP - 0.3, 3.55])
    out = []
    for y in ys:
        g = 0.22 if 6.3 <= y <= 10.4 else (0.1 if y < 6.3 else 0.0)
        out.append((y, wf(y), zf(y), g, 0 if y <= 10.4 else 1))
    return out


def head_section(w, zt, g):
    zb = HEAD_ZB
    sh = min(1.7, zt - zb - 0.8)
    left = [(-w + 0.55, zb), (-w, zb + 0.5), (-w, zt - sh), (-w + 0.12, zt - sh * 0.55),
            (-w + 0.42, zt - sh * 0.24), (-w + 0.85, zt - 0.08)]
    crown = [(-2.05, zt - 0.2), (-1.78, zt - 0.12), (-1.62, zt - 0.12 - g), (-1.38, zt - 0.06 - g),
             (-1.22, zt - 0.03), (-0.6, zt + 0.1), (0.0, zt + 0.15)]
    half = left + crown
    right = [(-x, z) for x, z in reversed(half[:-1])]
    return half + right


def build_head(P, M):
    crown = M(109, "crown", 0.32, 0.36)
    shoulder = M(99, "shoulder", 0.4, 0.45)
    face = M(103, "face", 0.35, 0.42)
    wall = M(104, "body", 0.35, 0.42)
    st = head_stations()
    rings = []
    for y, w, zt, g, reg in st:
        sec = head_section(w, zt, g)
        rings.append([P.v((x, y, z)) for x, z in sec])
    n = len(rings[0])
    nleft = 6  # first crown vertex index
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        reg = st[i + 1][4]
        cy = (st[i][0] + st[i + 1][0]) / 2
        for a in range(n):
            b = (a + 1) % n
            # faces a..b: shoulders run from vertex 1 to the crown start on each side
            if a <= 1 or a >= n - 3:
                m = wall
            elif a < nleft - 1 or a >= n - nleft:
                m = shoulder
            else:
                m = crown if reg == 0 else face
            if a == n - 1:  # bottom face
                m = shoulder
            zm = (HEAD_ZB + 0.5 * (st[i][2] + st[i + 1][2])) / 2
            P.f([r0[a], r0[b], r1[b], r1[a]], m, away=(0, cy, zm))
    P.f(rings[0], wall, out=(0, -1, 0))
    P.f(rings[-1], face, out=(0, 1, 0))
    # louvred vent on the front face: three slats across it
    zf = T.pchip([st[k][0] for k in range(len(st))], [st[k][2] for k in range(len(st))])
    slat = M(103, "face", 0.35, 0.42)
    for y in (11.35, 12.25, 13.15):
        z = zf(y) + 0.13
        dz = (zf(y + 0.05) - zf(y - 0.05)) / 0.1
        L = math.hypot(1, dz)
        d = (1 / L, dz / L)          # down the slope
        nrm = (-dz / L, 1 / L)       # out of it (forward and up)
        pts = []
        for x in (-2.55, 2.55):
            for al in (-0.24, 0.24):
                for up in (-0.15, 0.24):
                    for xc in (0.0, 0.1):
                        xx = x - math.copysign(xc, x) if up > 0 else x
                        pts.append((xx, y + d[0] * al + nrm[0] * up, z + d[1] * al + nrm[1] * up))
        T.hull(P, pts, slat)
    # a recessed dark panel behind the slats
    T.hull(P, [(x, y + 0.0, zf(y) - 0.05) for x in (-2.75, 2.75) for y in (10.95, 13.6)] +
           [(x, y, zf(y) + 0.06) for x in (-2.75, 2.75) for y in (10.95, 13.6)], M(101, "louvre", 0.3, 0.55))


def build(sprite, coll):
    M = Mats(sprite, NAME)
    P = T.Part(NAME, smooth_angle=34)
    build_body(P, M)
    build_pontoon_detail(P, M)
    build_eyes(P, M)
    build_lamps(P, M)
    build_head(P, M)
    obj = finish(P, [], coll)
    for m in M.list:
        obj.data.materials.append(m)
    return obj, M


# =================================================================================================
# review renders (from the e1 design scripts)
# =================================================================================================
def camera(scene, name, loc, look, ortho=None, lens=50):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return cam


def set_engine(scene, eevee):
    if not eevee:
        scene.render.engine = "BLENDER_WORKBENCH"
        return
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            return
        except TypeError:
            continue


def flat_setup(scene, k):
    set_engine(scene, False)
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = W * k, H * k
    scene.render.resolution_percentage = 100


def renders(obj, shell, out):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o is not obj
    flat_setup(scene, 10)
    top = camera(scene, "cam_top", (0, 0, 10), (0, 0, 0), ortho=max(W, H) * PX)
    top.rotation_euler = (0, 0, 0)
    scene.camera = top
    scene.render.filepath = str(out / "index_8.png")
    bpy.ops.render.render(write_still=True)
    set_engine(scene, True)
    vt = [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items]
    scene.view_settings.view_transform = "AgX" if "AgX" in vt else "Standard"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.05, 0.055, 0.07, 1)
    bg.inputs["Strength"].default_value = 1.0
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 4.0
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(40), math.radians(-25), math.radians(-30))
    fill_d = bpy.data.lights.new("fill", "SUN")
    fill_d.energy = 1.0
    fill = bpy.data.objects.new("fill", fill_d)
    scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(-50), math.radians(30), math.radians(150))
    scene.render.resolution_x = scene.render.resolution_y = 480
    s = max(W, H) * PX * 1.12
    D = max(W, H) * PX * 2.0
    zc = 0.3
    views = [
        ("top", (0, 0, 10), (0, 0, 0), s),
        ("game", (0, -D * 0.55, D * 0.85), (0, 0, 0.0), None),
        ("q34", (D * 0.62, -D * 0.62, D * 0.55), (0, 0, zc), None),
        ("q34rear", (-D * 0.62, D * 0.62, D * 0.55), (0, 0, zc), None),
        ("front", (0, -10, zc), (0, 0, zc), s),
        ("rear", (0, 10, zc), (0, 0, zc), s),
        ("side", (10, 0, zc), (0, 0, zc), s),
        ("under", (0.01, -0.01, -10), (0, 0, 0), s),
    ]
    for name, loc, look, ortho in views:
        cam = camera(scene, f"cam_{name}", loc, look, ortho=ortho, lens=55)
        if name == "top":
            cam.rotation_euler = (0, 0, 0)
        if name == "under":
            cam.rotation_euler = (math.pi, 0, 0)
        scene.camera = cam
        scene.render.filepath = str(out / f"view_{name}.png")
        bpy.ops.render.render(write_still=True)
    # game camera, small
    cam = camera(scene, "cam_game2", (0, -D * 0.55, D * 0.85), (0, 0, 0.0), lens=55)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = 240
    scene.render.filepath = str(out / "game_8.png")
    bpy.ops.render.render(write_still=True)


def tris(objs):
    t = 0
    for o in objs:
        o.data.calc_loop_triangles()
        t += len(o.data.loop_triangles)
    return t


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    obj, M = build(sprite, coll)
    # D118: the shell from a closed copy taken before any culling, kept out of the bake
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    T.cull_hidden(obj)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    fmt = "AUTO"
    if "--bake" in argv:
        closed.hide_render = True
        tint, textured = T.TINT, T.TEXTURED
        T.TINT = (1.0, 1.0, 1.0)
        T.TEXTURED = tuple(i for i, m in enumerate(M.list) if "_lens" not in m.name and "_core" not in m.name
                           and "_eye" not in m.name and "_lens_rim" not in m.name)
        try:
            T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"), size=1024, samples=64)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{NAME}_")
        fmt = "WEBP"
    shell = common.outline_shell(closed, coll, voxel=0.012, faces=1800, smooth=8, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed, do_unlink=True)
    bpy.context.view_layer.update()
    common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    print(f"{NAME}: {tris([obj])} triangles, shell {len(shell.data.polygons)} faces, "
          f"{len(M.list)} materials: {[m.name for m in M.list]}")
    if "--render" in argv:
        shell.hide_render = True
        renders(obj, shell, Path(argv[argv.index("--render") + 1]))


if __name__ == "__main__":
    main()
