"""newshs-191 three red capsules in a grey rack, a tile of the stone fortress
(newshs.shp frames 191-201, 24 x 28 px), rebuilt hard-surface to the D65 standard.

Reading of the sprite (tools/calibration/rubric.md):
- Rows 0-3 and 24-27 are the fortress's stone-brick floor; rows 4-23 a grey rack across the whole
  tile (it tiles edge to edge in the fortress's long red bank, assembly-newshd-127).
- Three upright capsules (cols 1-6, 9-14, 17-22; rows 5-22), 6 px wide, with pointed-round ends
  (2 px wide on rows 5 and 22, 4 px on rows 6 and 21). Their dark left edge and brighter middle are
  the shading of a round body, not paint.
- A one-pixel bright rim follows each capsule all round, diagonally at the ends (col 1 row 5, col 2
  row 4): a raised bezel lip round a pocket; the dark pixels just inside it (col 2 row 5 etc.) are
  the pocket's shadow. Between two capsules the two lips stand side by side (cols 7-8).
- The two dark pixels at cols 7-8 row 16 (left partition) are a small dark clamp between the lips;
  the right partition shows grey 6/8 there (a lighter clamp).
- Frames only light one capsule after another: the right one on 191 / 193, the middle on 195 / 197,
  the left on 199 / 201 (lit, then brighter). One model; each capsule's palette index follows the
  frame (palette_material frames=, D17).

Colours (trimmed median per region, darkest / brightest sixth left out, all frames): capsules 114,
lit 115, brighter 116; rim / bezel lip 8; rack deck 6; floor tones from the pixels (as lib_b073).

Hard surface (D50-D53, D65): the rack is a block with a front plinth and three vent panels on its
front face (the face the tilted game camera sees); each slot a lofted bezel lip with chamfered
outer and inner edges dropping into a pocket; each capsule a pchip loft, round in section, sunk
into its pocket. Floor: the stone plate painted per pixel, a separate object marked tyrian_ground
(no shadow, outside the outline). Outline shell (D51) from a closed proxy of rack + capsules.
Underside: closed, plain.

Units while building: sprite px (x = column edge - 12, y = row edge, down the screen, z up),
moved to Blender by usp_talon.finish (1/12, y flipped).

Run: Blender --background --factory-startup --python newshs-191_A.py -- [--out x.glb] [--render DIR]
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newshs-191"
HERE = Path(__file__).resolve().parent
PX = 1 / 12

FLOOR = 0.36          # floor top (0.03 units, as lib_b073's FLOOR, so the fortress tiles meet)
RZ = 3.2              # rack deck height
LIP = 0.4             # bezel lip above the deck
POCKET = 2.0          # pocket floor
Y0, Y1 = 4.0, 24.0    # rack rows 4-23
CY = 14.0             # capsule centre row (edge coordinate)
SLOTS = (-8.0, 0.0, 8.0)  # capsule centres (cols 3.5, 11.5, 19.5)
CELL = 4.0            # half width of a slot's cell
ZC = 3.3              # capsule axis height
HZ = 0.97             # capsule section height / width

# Capsule half width against distance from the centre row (rows 5-22: 2 px wide on rows 5 / 22,
# 4 px on 6 / 21, 6 px from 7 / 20). pchip, so the ends never bulge.
HALF_LEN = 9.3
_PD = [0.0, 5.0, 6.0, 7.0, 8.0, 8.5, 9.0, 9.3]
_PW = [3.0, 3.0, 2.92, 2.45, 1.65, 1.1, 0.6, 0.0]
_prof = T.pchip(_PD, _PW)


def cap_w(dy):
    dy = abs(dy)
    return max(0.0, _prof(min(dy, HALF_LEN)))


# --- materials ----------------------------------------------------------------------------------
class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list = []
        self.slots = {}

    def __call__(self, index, part, frames=None, metallic=0.4, roughness=0.45, emission=0.0):
        key = (index, part)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, f"{NAME}_{part}", metallic=metallic,
                                                     roughness=roughness, emission_strength=emission,
                                                     frames=frames))
        return self.slots[key]


# --- slot outlines ------------------------------------------------------------------------------
NS = 22  # stations per side of a slot outline


def stations():
    """Parameters t in (-1, 1) along one side, clustered towards the ends (cosine spacing)."""
    return [-math.cos(math.pi * k / (NS + 1)) for k in range(1, NS + 1)]


def outline(xc, d, ey=0.55):
    """The capsule's plan outline grown by d px sideways (and ey * d at the ends): a ring of
    2 * NS + 2 points, counter-clockwise in (x, y) with y down = clockwise on screen. Tips included."""
    L = HALF_LEN + ey * d
    ts = stations()
    right = [(xc + cap_w(t * HALF_LEN) + d * (1 - abs(t) ** 6) ** 0.5, CY + t * L) for t in ts]
    left = [(2 * xc - x, y) for x, y in reversed(right)]
    return [(xc, CY - L)] + right + [(xc, CY + L)] + left


def rect_ring(xc, ring):
    """The cell's rectangle sampled to match a slot ring point for point: rays from the slot centre
    through each ring point, the four corners snapped to the ring points nearest their angles.
    Cells are identical and mirror symmetric, so shared edges get the same vertices."""
    x0, x1 = xc - CELL, xc + CELL
    out = []
    for x, y in ring:
        dx, dy = x - xc, y - CY
        ts = []
        if dx > 1e-9:
            ts.append(CELL / dx)
        if dx < -1e-9:
            ts.append(-CELL / dx)
        if dy > 1e-9:
            ts.append((Y1 - CY) / dy)
        if dy < -1e-9:
            ts.append((Y0 - CY) / dy)
        t = min(ts)
        out.append([xc + dx * t, CY + dy * t])
    for cx, cy in ((x0, Y0), (x1, Y0), (x1, Y1), (x0, Y1)):
        a = math.atan2(cy - CY, cx - xc)
        k = min(range(len(ring)), key=lambda i: abs(math.remainder(math.atan2(ring[i][1] - CY, ring[i][0] - xc) - a, 2 * math.pi)))
        out[k] = [cx, cy]
    return [tuple(p) for p in out]


def strip(P, a, b, mat, outf):
    n = len(a)
    for i in range(n):
        j = (i + 1) % n
        q = [a[i], a[j], b[j], b[i]]
        c = sum((Vector(v.co) for v in q), Vector()) / 4
        P.f(q, mat, out=outf(c))


# --- parts --------------------------------------------------------------------------------------
def slot(P, xc, M):
    """Deck cell, bezel lip and pocket round one capsule."""
    up = lambda c: (0, 0, 1)  # noqa: E731
    outw = lambda c: (c.x - xc, c.y - CY, 0.8)  # noqa: E731
    inw = lambda c: (xc - c.x, CY - c.y, 0.3)  # noqa: E731
    inw0 = lambda c: (xc - c.x, CY - c.y, 0.0)  # noqa: E731
    prof = [(1.3, RZ), (1.08, RZ + LIP - 0.17), (0.86, RZ + LIP), (0.32, RZ + LIP), (0.16, RZ + LIP - 0.14),
            (0.12, POCKET)]
    rings2 = [outline(xc, d) for d, _ in prof]
    rings = [[P.v((x, y, z)) for x, y in r] for r, (_, z) in zip(rings2, prof)]
    deck = [P.v((x, y, RZ)) for x, y in rect_ring(xc, rings2[0])]
    strip(P, deck, rings[0], M["deck"], up)
    strip(P, rings[0], rings[1], M["lip"], outw)
    strip(P, rings[1], rings[2], M["lip"], outw)
    strip(P, rings[2], rings[3], M["lip"], up)
    strip(P, rings[3], rings[4], M["lip"], inw)
    strip(P, rings[4], rings[5], M["pocket"], inw0)
    c = P.v((xc, CY, POCKET))
    r = rings[5]
    for i in range(len(r)):
        P.f([r[i], r[(i + 1) % len(r)], c], M["pocket"], out=(0, 0, 1))


def rack_walls(P, M):
    """The rack's sides and bottom (the deck is the slots' cells): front and rear faces, end faces."""
    zb = FLOOR
    corners = [(-12, Y0), (12, Y0), (12, Y1), (-12, Y1)]
    # Each wall is split at the deck vertices along it so it shares them (no cracks at the top edge).
    ring = outline(SLOTS[0], 1.3)
    deck_pts = set()
    for xc in SLOTS:
        for p in rect_ring(xc, outline(xc, 1.3)):
            deck_pts.add((round(p[0], 6), round(p[1], 6)))
    del ring
    edges = [((-12, Y0), (12, Y0), (0, -1, 0)), ((12, Y0), (12, Y1), (1, 0, 0)),
             ((12, Y1), (-12, Y1), (0, 1, 0)), ((-12, Y1), (-12, Y0), (-1, 0, 0))]
    for (ax, ay), (bx, by), out in edges:
        if ay == by:
            pts = sorted({p for p in deck_pts if abs(p[1] - ay) < 1e-6}, key=lambda p: p[0], reverse=ax > bx)
        else:
            pts = sorted({p for p in deck_pts if abs(p[0] - ax) < 1e-6}, key=lambda p: p[1], reverse=ay > by)
        for p, q in zip(pts, pts[1:]):
            P.f([P.v((p[0], p[1], zb)), P.v((q[0], q[1], zb)), P.v((q[0], q[1], RZ)), P.v((p[0], p[1], RZ))],
                M["wall"], out=out)
    P.f([P.v((x, y, zb)) for x, y in corners], M["wall"], out=(0, 0, -1))


def capsule(P, xc, mat):
    """A round capsule along the column: pchip half width, section HZ times as tall as wide."""
    n = 18
    L = HALF_LEN
    ts = [-math.cos(math.pi * k / 26) for k in range(1, 26)]
    rings = []
    for t in ts:
        y = CY + t * L
        w = max(cap_w(t * L), 0.04)
        h = w * HZ
        h_dn = min(h, ZC - POCKET - 0.1)  # the hidden lower half flattened into the pocket
        ring = []
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            sa = math.sin(a)
            ring.append(P.v((xc + w * math.cos(a), y, ZC + (h if sa > 0 else h_dn) * sa)))
        rings.append((y, ring))
    for (ya, a), (yb, b) in zip(rings, rings[1:]):
        ym = (ya + yb) / 2
        for k in range(n):
            j = (k + 1) % n
            P.f([a[k], a[j], b[j], b[k]], mat, away=(xc, ym, ZC))
    for (y, r), tip in ((rings[0], CY - L), (rings[-1], CY + L)):
        c = P.v((xc, tip, ZC))
        for k in range(n):
            P.f([r[k], r[(k + 1) % n], c], mat, away=(xc, CY, ZC))


def front_detail(P, M):
    """Front face (the one the tilted camera sees) and rear: a plinth along the foot, a vent panel
    under each capsule, end clamps on the partitions."""
    for y_face, sgn in ((Y1, 1), (Y0, -1)):
        # plinth: a chamfered strip along the foot of the wall
        y_in, y_out = (y_face - 0.2, y_face + 0.45) if sgn > 0 else (y_face - 0.45, y_face + 0.2)
        T.hull(P, T.cbox(-12, 12, y_in, y_out, FLOOR, 1.05, 0.0, 0.18), M["wall"])
        # cap rail along the top edge of the wall
        y_in, y_out = (y_face - 0.2, y_face + 0.22) if sgn > 0 else (y_face - 0.22, y_face + 0.2)
        T.hull(P, T.cbox(-12, 12, y_in, y_out, RZ - 0.45, RZ + 0.08, 0.0, 0.12), M["lip"])
        if sgn < 0:
            # rear: an access panel behind each capsule, bolted at its corners
            for xc in SLOTS:
                T.hull(P, T.cbox(xc - 3.0, xc + 3.0, y_face - 0.2, y_face + 0.1, 1.35, 2.55, 0.12), M["wall"])
                for bx in (xc - 2.5, xc + 2.5):
                    for bz in (1.6, 2.3):
                        T.hull(P, T.cbox(bx - 0.18, bx + 0.18, y_face - 0.3, y_face - 0.1, bz - 0.18, bz + 0.18, 0.06),
                               M["lip"])
            continue
        for xc in SLOTS:
            # vent panel frame, proud of the wall, with four dark louvre slots
            T.hull(P, T.cbox(xc - 2.9, xc + 2.9, y_face - 0.1, y_face + 0.22, 1.3, 2.6, 0.12), M["lip"])
            for k in range(4):
                x = xc - 2.1 + k * 1.4
                T.hull(P, T.cbox(x - 0.35, x + 0.35, y_face, y_face + 0.27, 1.45, 2.45, 0.06), M["pocket"])
    # end plates on the rack's ends (flush against the neighbouring tile in the fortress's bank)
    for x_face, sgn in ((-12.0, -1), (12.0, 1)):
        x_in, x_out = (x_face, x_face + 0.12) if sgn > 0 else (x_face - 0.12, x_face)
        T.hull(P, T.cbox(x_in, x_out, Y0 + 1.5, Y1 - 1.5, 1.2, RZ - 0.6, 0.05), M["lip"])
        for yy in (Y0 + 2.4, Y1 - 2.4):
            x0, x1 = (x_out, x_out + 0.1) if sgn > 0 else (x_in - 0.1, x_in)
            T.hull(P, T.cbox(x0, x1, yy - 0.2, yy + 0.2, 1.95 - 0.2, 1.95 + 0.2, 0.05), M["clamp"])
    # clamps between the lips (sprite cols 7-8 row 16; dark on the left, grey on the right)
    for x, m in ((-4.0, M["clamp_dk"]), (4.0, M["clamp"])):
        T.hull(P, T.cbox(x - 0.8, x + 0.8, 15.9, 17.1, RZ - 0.1, RZ + LIP + 0.12, 0.15), m)
        for yy in (16.2, 16.8):
            T.hull(P, T.cbox(x - 0.25, x + 0.25, yy - 0.15, yy + 0.15, RZ + LIP + 0.1, RZ + LIP + 0.22, 0.06), M["lip"])
    # end blocks at the tile edges keep the rack's ends square where it meets its neighbours: a
    # chamfered cap strip on top of the deck at each end of the lips' tips (rows 4 / 23 at x = slot)
    # end clips over each capsule's tips (the rim pixels right above / below them, rows 4 and 23)
    for xc in SLOTS:
        for y0, y1, yt in ((Y0 + 0.05, Y0 + 0.95, CY - HALF_LEN), (Y1 - 0.95, Y1 - 0.05, CY + HALF_LEN)):
            T.hull(P, T.cbox(xc - 1.15, xc + 1.15, y0, y1, RZ - 0.1, RZ + LIP + 0.35, 0.18), M["lip"])
            T.hull(P, T.cbox(xc - 0.4, xc + 0.4, (y0 + y1) / 2 - 0.2, (y0 + y1) / 2 + 0.2,
                             RZ + LIP + 0.3, RZ + LIP + 0.45, 0.07), M["deck"])


def shell_proxy(coll):
    e = 0.2
    P = T.Part(f"{NAME}_proxy", smooth_angle=180)
    T.hull(P, T.cbox(-12 - e, 12 + e, Y0 - e, Y1 + e, FLOOR + 0.35, RZ + LIP + e, 0.3), 0)
    for xc in SLOTS:
        pts = []
        for t in [-1 + k / 10 for k in range(21)]:
            y = CY + t * (HALF_LEN + e)
            w = cap_w(t * HALF_LEN) + e
            for k in range(12):
                a = 2 * math.pi * k / 12
                pts.append((xc + w * math.cos(a), y, max(ZC + w * HZ * math.sin(a), RZ)))
        T.hull(P, pts, 0)
    return T.finish(P, [], coll)


def floor(sprite, M, coll):
    """Stone floor plate, 0..FLOOR, its top painted per pixel in four grey tones (as lib_b073),
    the rows under the rack left out."""
    pix = sprite["frames"][0]["pixels"]
    colors = sprite["colors"]
    tones = ((1, 3), (4, 6), (7, 9), (10, 15))
    slots = []
    for lo, hi in tones:
        have = [i for i in range(lo, hi + 1) if str(i) in colors]
        mid = (lo + hi) / 2
        slots.append(M(min(have, key=lambda i: abs(i - mid)), f"stone{lo}", metallic=0.05, roughness=0.85)
                     if have else None)

    def slot_of(i):
        for (lo, hi), s in zip(tones, slots):
            if lo <= i <= hi:
                return s
        return slots[1]

    P = T.Part(f"{NAME}_floor", smooth_angle=5)
    T.hull(P, [(x, y, z) for x in (-12.0, 12.0) for y in (0.0, 28.0) for z in (0.0, FLOOR - 0.01)], slot_of(4))
    for r in list(range(0, int(Y0))) + list(range(int(Y1), 28)):
        c = 0
        while c < 24:
            s = slot_of(pix[r][c])
            e = c + 1
            while e < 24 and slot_of(pix[r][e]) == s:
                e += 1
            vs = [P.v((xx, yy, FLOOR)) for xx, yy in ((c - 12, r), (e - 12, r), (e - 12, r + 1), (c - 12, r + 1))]
            P.f(vs, s, out=(0, 0, 1))
            c = e
    return P


def build():
    sprite = common.load_sprite(WT, NAME)
    for o in list(bpy.data.objects):  # factory startup: the default cube, camera and light
        if o.name in ("Cube", "Camera", "Light"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    for o in list(bpy.data.objects):
        if o.name.startswith(NAME):
            bpy.data.objects.remove(o, do_unlink=True)
    Mt = Mats(sprite)
    M = {
        "deck": Mt(6, "deck", metallic=0.35, roughness=0.5),
        "wall": Mt(6, "wall", metallic=0.3, roughness=0.55),
        "lip": Mt(8, "lip", metallic=0.5, roughness=0.32),
        "pocket": Mt(4, "pocket", metallic=0.3, roughness=0.6),
        "clamp_dk": Mt(4, "clamp_dk", metallic=0.45, roughness=0.4),
        "clamp": Mt(6, "clamp", metallic=0.45, roughness=0.4),
    }
    # Capsules: right lights on 191/193, middle on 195/197, left on 199/201.
    caps = []
    for xc, (f1, f2) in zip(SLOTS, ((199, 201), (195, 197), (191, 193))):
        caps.append(Mt(114, f"capsule{f1}", frames={f1: 115, f2: 116}, metallic=0.0, roughness=0.14,
                       emission=0.8))
    FP = floor(sprite, Mt, coll)
    P = T.Part(NAME, smooth_angle=34)
    for xc, cm in zip(SLOTS, caps):
        slot(P, xc, M)
        capsule(P, xc, cm)
    rack_walls(P, M)
    front_detail(P, M)
    rack = T.finish(P, Mt.list, coll)
    fl = T.finish(FP, Mt.list, coll)
    fl.data.shade_flat()
    fl["tyrian_ground"] = True
    proxy = shell_proxy(coll)
    shell = common.outline_shell(proxy, coll, faces=2500)
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(proxy, do_unlink=True)
    return sprite, [rack, fl, shell]


# --- review renders -----------------------------------------------------------------------------
def set_frame_colours(objs, frame):
    mats = {m for o in objs if o.type == "MESH" for m in o.data.materials if m}
    saved = []
    for m in mats:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        saved.append((m, tuple(m.diffuse_color), tuple(bsdf.inputs["Base Color"].default_value),
                      tuple(bsdf.inputs["Emission Color"].default_value)))
        rgb = m.get("tyrian_frame_rgb", {}).get(str(frame)) if frame is not None else None
        if rgb is not None:
            m.diffuse_color = (*rgb, 1.0)
            bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
            if bsdf.inputs["Emission Strength"].default_value > 0:
                bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
    return saved


def restore(saved):
    for m, dc, bc, ec in saved:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        m.diffuse_color = dc
        bsdf.inputs["Base Color"].default_value = bc
        bsdf.inputs["Emission Color"].default_value = ec


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
    up = "Y" if abs(d.normalized().z) < 0.999 else "Y"
    cam.rotation_euler = d.to_track_quat("-Z", up).to_euler()
    return cam


def renders(objs, sprite, out):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    shell = objs[2]
    # 1) palette-index top views (flat colours, no AA), one per frame, 10 px per sprite px
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 240, 280
    scene.render.resolution_percentage = 100
    shell.hide_render = True
    top = camera(scene, "cam_top", (0, 0, 10), (0, 0, 0), ortho=28 * PX)
    top.rotation_euler = (0, 0, 0)
    scene.camera = top
    for f in sprite["frames"]:
        saved = set_frame_colours(objs, f["index"])
        scene.render.filepath = str(out / f"index_{f['index']}.png")
        bpy.ops.render.render(write_still=True)
        restore(saved)
    # 2) lit views (EEVEE), frame 193 (right capsule bright) and 191
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "Standard"
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
    shell.hide_render = True
    scene.render.resolution_x = scene.render.resolution_y = 480
    s = 2.9
    D = 6.0
    views = [
        ("top", (0, 0, 10), (0, 0, 0), s),
        ("game", (0, -D * 0.55, D * 0.85), (0, 0, 0.1), None),
        ("q34", (D * 0.62, -D * 0.62, D * 0.55), (0, 0, 0.1), None),
        ("q34rear", (-D * 0.62, D * 0.62, D * 0.55), (0, 0, 0.1), None),
        ("front", (0, -10, 0.15), (0, 0, 0.15), s),
        ("rear", (0, 10, 0.15), (0, 0, 0.15), s),
        ("side", (10, 0, 0.15), (0, 0, 0.15), s),
        ("under", (0.01, -0.01, -10), (0, 0, 0), s),
    ]
    for frame in (193,):
        saved = set_frame_colours(objs, frame)
        for name, loc, look, ortho in views:
            cam = camera(scene, f"cam_{name}", loc, look, ortho=ortho, lens=55)
            if name == "top":
                cam.rotation_euler = (0, 0, 0)
            if name == "under":
                cam.rotation_euler = (math.pi, 0, 0)
            scene.camera = cam
            scene.render.filepath = str(out / f"view_{name}.png")
            bpy.ops.render.render(write_still=True)
        restore(saved)
    # game view of every frame (small) for the animation strip
    cam = camera(scene, "cam_game2", (0, -D * 0.55, D * 0.85), (0, 0, 0.1), lens=55)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = 240
    for f in sprite["frames"]:
        saved = set_frame_colours(objs, f["index"])
        scene.render.filepath = str(out / f"game_{f['index']}.png")
        bpy.ops.render.render(write_still=True)
        restore(saved)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite, objs = build()
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"])
    tris = 0
    for o in objs[:2]:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    print(f"built {NAME}: {tris} triangles (rack + floor), shell {len(objs[2].data.polygons)} faces")
    if "--render" in argv:
        renders(objs, sprite, Path(argv[argv.index("--render") + 1]))
