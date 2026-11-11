r"""ASTEROID?'s light bridge (map 1-3 ground, shapesz.dat layer 0, 5 x 13 tiles, map rows 132-136,
cols 1-13), hard-surface on lib_l1kit (the base complex's station kit), so it matches the base complex.

What it is (from the tiles): a long paved station platform in a rocky rim that runs on past the right
edge of the pattern (cols 11-12 rows 2-3 have no rim: the paving and the right hatch run off the edge).
Across it, in pattern row 2, a framed light strip of 24 red capsules (339 x 8: a machined housing, a
light bezel ring round each pill, domed dark-red lenses, faintly lit). At its two ends two big dark
round hatches (305 306 / 315 316) with six spokes and a hub, a dark-bronze bracket either side of the
disc and bronze clamps hugging its lower half, tied by a riveted dark-bronze strap. On the rim's bulge
(row 1, cols 5-8) four seats: two brass gun turrets (358: an octagonal brass body with blue-steel
inserts, red side lamps, a barrel pointing down the screen with a red muzzle) and two orb sockets
(357: a dark bezel, a dark satin dome, two small red eyes). Ground enemies sit on the strip, the hatches
and the seats (the spec's enemy cells), so every top there stays <= ENEMY_MAX 0.38.

Section (kit): bed -0.04..0.14 (talus chamfer), mortar deck 0.30, basket-weave bricks 0.345, kerb
posts 0.366, rim stones 0.36..0.47 (<= 0.374 on enemy cells); strip housing 0.35, lenses 0.376;
hatch clamps 0.372; turrets 0.376; orb domes 0.37.

Palette (trimmed medians of the tiles, see notes): capsule lens 113, capsule bezel 8, strip housing 6,
hatch disc 1, spokes 4, clamps 161, brackets/strap 17, turret brass 164, blue steel 99, turret lamps
115, muzzle 114, orb dome 4, orb eyes 112, orb bezel 3. Kit parts use the kit's PAL_* (paving 6).

Build:
    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/l1bld_light_bridge.py
    blender --background --factory-startup --python assets/blender/tiles/l1bld_light_bridge.py -- [--no-bake] [--preview <dir>] [--views <dir>]
"""

import math
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_l1kit as kit  # noqa: E402
import lib_tiles as lt  # noqa: E402


TW, TH = lt.TILE_W, lt.TILE_H
DECK = kit.DECK_TOP
ENEMY_MAX = lb.ENEMY_MAX

# ---- features (pattern px, read off the tiles) ----
STRIP = (70.5, 58.5, 265.5, 81.5)  # the capsules' housing (light frame rows 60 / 79)
CAP_X0, CAP_PITCH, CAP_W, CAP_Y0, CAP_Y1 = 73, 8, 6, 61, 78  # 24 red components, 6 x 18 px, 8 px apart
HATCHES = [(45.5, 83.5), (285.5, 83.5)]  # dark disc centres (cols 1-2 / 11-12, rows 2-3)
H_RX, H_RY = 17.0, 23.0  # the dark disc's radii (art x 28..62, y 60..107)
TURRETS = [(131.75, 39.0), (203.75, 39.0)]  # 358 (red side lamps x 121/142, muzzle y 52)
ORBS = [(156.5, 42.5), (180.5, 42.5)]  # 357 dark discs
OPEN_Y = (56, 112)  # rows 2-3: the paving runs on past the right edge

# ---- palette (trimmed medians of each region's pixels) ----
P_LENS, P_BEZEL, P_HOUSE = 113, 8, 6
P_DISC, P_SPOKE, P_SEAT, P_CLAMP, P_BRACKET = 1, 4, 3, 161, 17
P_BRASS, P_BLUE, P_LAMP, P_MUZZLE = 164, 99, 115, 114
P_ORB, P_EYE, P_ORB_BEZEL = 4, 112, 3


def depth_open(mask, limit=40, _orig=lb.depth):
    """lb.depth with the pattern's right edge open (the platform runs on past it in rows 2-3): pad the
    mask with its last column before measuring, so no rock band or deck edge forms along x = W."""
    if mask.ndim != 2:
        return _orig(mask, limit)
    pad = np.concatenate([mask, np.repeat(mask[:, -1:], limit + 2, axis=1)], axis=1)
    return _orig(pad, limit)[:, :mask.shape[1]]


def lens(g, poly, z0, h, mat, max_in=1.5):
    """A domed red pill lens over a rounded rectangle: rings stepping in and up (smooth), the top a
    flat pill rather than a ridge (kit.Kit.pillow pinches a 6 px pill to a crease)."""
    o = g.outer(poly)
    prof = [(0.0, 0.0), (0.3, 0.42), (0.75, 0.75), (1.2, 0.93), (max_in, 1.0)]
    rings = [[g.v(x, y, z0 + h * t) for x, y in ([tuple(q) for q in kit.ls.inset(o, d)] if d else o)] for d, t in prof]
    n = len(o)
    for lo, hi in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            g.face((lo[i], lo[j], hi[j], hi[i]), mat, smooth=True)
    g.face(rings[-1], mat, smooth=False)


def build(bake=True, views=None, preview=None):
    lb.clear_scene()
    b = lb.Building("light-bridge")
    H, W = b.H, b.W
    fp = b.footprint
    k = kit.Kit(b)
    g = k.g
    M = b.m
    yy, xx = np.mgrid[0:H, 0:W] + 0.5

    m = dict(
        house=M(P_HOUSE, roughness=0.45, metallic=0.5),
        bezel=M(P_BEZEL, roughness=0.35, metallic=0.6),
        lens=M(P_LENS, roughness=0.22, metallic=0.1, emission_strength=0.45),
        sock=M(1, roughness=0.8),
        disc=M(P_DISC, roughness=0.6, metallic=0.3),
        spoke=M(P_SPOKE, roughness=0.45, metallic=0.5),
        seat=M(P_SEAT, roughness=0.45, metallic=0.5),
        clamp=M(P_CLAMP, roughness=0.45, metallic=0.55),
        bracket=M(P_BRACKET, roughness=0.5, metallic=0.5),
        brass=M(P_BRASS, roughness=0.38, metallic=0.6),
        blue=M(P_BLUE, roughness=0.3, metallic=0.55),
        lamp=M(P_LAMP, roughness=0.25, emission_strength=1.2),
        muzzle=M(P_MUZZLE, roughness=0.3, emission_strength=1.0),
        orb=M(P_ORB, roughness=0.2, metallic=0.8),
        eye=M(P_EYE, roughness=0.25, emission_strength=1.0),
        orb_bezel=M(P_ORB_BEZEL, roughness=0.55, metallic=0.4),
        bolt=M(7, roughness=0.4, metallic=0.6),
    )

    def ellm(cx, cy, rx, ry):
        return ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1

    # ---- masks ----
    openm = kit.box_mask((H, W), W - 3, OPEN_Y[0], W, OPEN_Y[1])
    parts = kit.box_mask((H, W), STRIP[0] - 3, STRIP[1] - 3, STRIP[2] + 3, STRIP[3] + 3)
    for cx, cy in HATCHES:
        parts |= ellm(cx, cy, H_RX + 6, H_RY + 3.5)
    for cx, cy in TURRETS:
        parts |= ellm(cx, cy + 1, 12.5, 13.5)
    for cx, cy in ORBS:
        parts |= ellm(cx, cy, 12, 12.2)

    lb.depth = depth_open  # deck_mask / rock_layout measure the rim band with the right edge open
    try:
        k.bed(fp)
        dm = k.deck_mask(fp)
        k.deck(dm)
        k.rock_layout(fp, dm, exclude=kit.dil4(openm, 10))
    finally:
        lb.depth = depth_open.__defaults__[1]
    k.kerb(dm, no_post=parts | kit.dil4(openm, 8))
    k.paving(kit.ero_disk(dm, kit.KERB_W) & ~parts)
    k.rocks()

    # ---- the light strip (339 x 8): housing, bezels, 24 lenses ----
    x0, y0, x1, y1 = STRIP
    LT = kit.LENS_TOP  # 0.350
    g.prism(kit.rbox(x0, y0, x1, y1, 2.0, 2), [], DECK - 0.005, LT - 0.006, m["house"], chamfer=0.9, drop=0.014, bottom=False)
    # end caps: a machined block at each end with two bolts
    for ex0, ex1 in ((x0 - 0.5, x0 + 2.0), (x1 - 2.0, x1 + 0.5)):
        g.prism(kit.rbox(ex0, y0 + 1.5, ex1, y1 - 1.5, 0.6, 1), [], LT - 0.01, LT + 0.004, m["bezel"], chamfer=0.4, drop=0.006, bottom=False)
        for by in (y0 + 5, y1 - 5):
            g.prism(kit.ell((ex0 + ex1) / 2, by, 0.7, 0.7, 6), [], LT, LT + 0.012, m["bolt"], bottom=False)
    for i in range(24):
        cx0 = CAP_X0 + CAP_PITCH * i
        cx1 = cx0 + CAP_W - 1
        corner = CAP_W / 2 - 0.1
        # the light bezel ring round each pill (the art's 1 px pal 8 ring), then a dark seat and the lens
        ring_o = kit.rbox(cx0 - 0.9, CAP_Y0 - 0.9, cx1 + 1.9, CAP_Y1 + 1.9, corner + 0.9, 3)
        ring_i = kit.rbox(cx0 + 0.1, CAP_Y0 + 0.1, cx1 + 0.9, CAP_Y1 + 0.9, corner - 0.1, 3)
        g.prism(ring_o, [ring_i], LT - 0.012, LT + 0.006, m["bezel"], chamfer=0.35, drop=0.006, bottom=False)
        g.prism(ring_i, [], LT - 0.02, LT - 0.002, m["sock"], bottom=False)
        lens(g, kit.rbox(cx0 + 0.1, CAP_Y0 + 0.1, cx1 + 0.9, CAP_Y1 + 0.9, corner - 0.1, 3), LT - 0.004, 0.026, m["lens"])

    # ---- the round hatches (305 306 / 315 316) ----
    def sector(cx, cy, r0x, r0y, r1x, r1y, a0, a1, n=10):
        out = [(cx + r1x * math.cos(math.radians(a0 + (a1 - a0) * t / n)), cy + r1y * math.sin(math.radians(a0 + (a1 - a0) * t / n))) for t in range(n + 1)]
        out += [(cx + r0x * math.cos(math.radians(a1 - (a1 - a0) * t / n)), cy + r0y * math.sin(math.radians(a1 - (a1 - a0) * t / n))) for t in range(n + 1)]
        return out

    for cx, cy in HATCHES:
        rx, ry = H_RX, H_RY
        # seat ring, the dark disc recessed in it, six spokes, hub
        g.prism(kit.ell(cx, cy, rx + 1.5, ry + 1.5, 40), [kit.ell(cx, cy, rx - 2.0, ry - 2.0, 40)], DECK - 0.01, 0.345, m["seat"],
                chamfer=0.7, drop=0.012, bottom=False)
        g.prism(kit.ell(cx, cy, rx - 1.9, ry - 1.9, 40), [], DECK - 0.01, 0.322, m["disc"], bottom=False)
        for j in range(6):
            a = math.pi / 6 + j * math.pi / 3
            dx, dy = math.cos(a), math.sin(a)
            nx, ny = -dy * rx / ry, dx
            p0 = (cx + 5.5 * dx, cy + 6.5 * dy)
            p1 = (cx + (rx - 3.5) * dx, cy + (ry - 3.5) * dy)
            w = 1.0
            poly = [(p0[0] + nx * w, p0[1] + ny * w), (p1[0] + nx * w, p1[1] + ny * w), (p1[0] - nx * w, p1[1] - ny * w), (p0[0] - nx * w, p0[1] - ny * w)]
            g.prism(poly, [], 0.318, 0.336, m["spoke"], chamfer=0.3, drop=0.006, bottom=False)
            # a bolt at the spoke's outer end
            g.prism(kit.ell(p1[0] + 1.2 * dx, p1[1] + 1.2 * dy, 0.7, 0.7, 6), [], 0.318, 0.334, m["bolt"], bottom=False)
        g.prism(kit.ell(cx, cy, 5.0, 6.0, 18), [], 0.318, 0.350, m["spoke"], chamfer=0.8, drop=0.01, bottom=False)
        g.prism(kit.ell(cx, cy, 2.2, 2.6, 10), [], 0.348, 0.358, m["disc"], bottom=False)
        # the dark-bronze side brackets (art x 25-29 / 61-66, y 79-95)
        for a0, a1 in ((150, 205), (-25, 30)):
            g.prism(sector(cx, cy, rx - 0.5, ry - 0.5, rx + 3.6, ry + 2.5, a0, a1, 8), [], DECK - 0.01, 0.362, m["bracket"],
                    chamfer=0.6, drop=0.012, bottom=False)
        # the bronze clamps hugging the disc's lower half (art x 28-37 / 53-63, y 85-99)
        for a0, a1 in ((95, 172), (8, 85)):
            g.prism(sector(cx, cy, rx - 5.0, ry - 5.0, rx + 0.8, ry + 0.8, a0, a1, 12), [], 0.31, 0.372, m["clamp"],
                    chamfer=0.7, drop=0.014, bottom=False)
            # clamp bolt
            am = math.radians((a0 + a1) / 2)
            g.prism(kit.ell(cx + (rx - 2.2) * math.cos(am), cy + (ry - 2.2) * math.sin(am), 0.9, 0.9, 8), [], 0.37, 0.379, m["bolt"], bottom=False)
        # the strap across the disc's lower half (the art's dotted dark-bronze line, y 92-95), riveted
        sy = cy + 10.0
        hx = rx * math.sqrt(max(0.0, 1 - (10.0 / ry) ** 2)) - 3.5
        g.prism(kit.rbox(cx - hx, sy - 1.2, cx + hx, sy + 1.2, 0.5, 1), [], 0.318, 0.342, m["bracket"], chamfer=0.3, drop=0.006, bottom=False)
        for t in np.linspace(-hx + 1.5, hx - 1.5, 7):
            g.prism(kit.ell(cx + t, sy, 0.55, 0.55, 6), [], 0.342, 0.35, m["clamp"], bottom=False)

    # ---- the gun turrets (358) ----
    def octagon(cx, cy, rx, ry, rot=math.pi / 8):
        return [(cx + rx * math.cos(rot + i * math.pi / 4) / math.cos(math.pi / 8), cy + ry * math.sin(rot + i * math.pi / 4) / math.cos(math.pi / 8))
                for i in range(8)]

    for cx, cy in TURRETS:
        g.prism(kit.ell(cx, cy + 1.0, 11.0, 11.5, 28), [], DECK - 0.005, 0.312, m["sock"], chamfer=0.5, drop=0.005, bottom=False)
        # brass body
        g.prism(octagon(cx, cy, 9.2, 9.0), [], 0.305, 0.345, m["brass"], chamfer=0.9, drop=0.014, bottom=False)
        # the cage ring on top, its four blue-steel inserts (left, right, top vents) set into it
        g.prism(octagon(cx, cy, 8.0, 7.8), [octagon(cx, cy, 5.2, 5.0)], 0.34, 0.362, m["brass"], chamfer=0.5, drop=0.008, bottom=False)
        g.prism(kit.ell(cx, cy, 5.3, 5.1, 20), [], 0.34, 0.350, m["blue"], bottom=False)
        g.dome(cx, cy, 4.6, 4.4, 0.348, 0.024, m["blue"], n=16, rings=3)
        # the brass cross-bar over the cupola (art y 37-39)
        g.prism(kit.rbox(cx - 5.4, cy - 1.1, cx + 5.4, cy + 1.1, 0.5, 1), [], 0.355, 0.376, m["brass"], chamfer=0.4, drop=0.006, bottom=False)
        for sx in (-1, 1):
            # side inserts (art x 124-126 / 136-138, y 37-41)
            ix = cx + sx * 6.7
            g.prism(kit.rbox(ix - 1.3, cy - 2.2, ix + 1.3, cy + 2.2, 0.4, 1), [], 0.355, 0.366, m["blue"], bottom=False)
            # red side lamps (art x 121-122 / 141-142, y 35-41)
            lx = cx + sx * 9.9
            g.prism(kit.rbox(lx - 1.4, cy - 4.0, lx + 1.4, cy + 3.0, 0.8, 2), [], DECK - 0.005, 0.322, m["brass"], bottom=False)
            g.dome(lx, cy - 0.5, 1.2, 3.2, 0.32, 0.03, m["lamp"], n=10, rings=2)
            # top vents (art rows 28-29, x 126-129 / 133-136)
            vx = cx + sx * 3.4
            g.prism(kit.rbox(vx - 1.6, cy - 10.3, vx + 1.6, cy - 8.2, 0.4, 1), [], 0.33, 0.35, m["blue"], bottom=False)
        # the barrel down the screen (art x 128-134, y 47-54) with a red muzzle lens on its end
        g.prism(kit.rbox(cx - 2.6, cy + 5.0, cx + 2.6, cy + 12.0, 1.6, 3), [], 0.33, 0.354, m["brass"], chamfer=1.1, drop=0.012, bottom=False)
        g.prism(kit.rbox(cx - 3.4, cy + 11.0, cx + 3.4, cy + 15.5, 1.2, 2), [], DECK - 0.005, 0.358, m["brass"], chamfer=0.6, drop=0.01, bottom=False)
        g.dome(cx - 0.3, cy + 13.4, 1.7, 1.4, 0.356, 0.02, m["muzzle"], n=10, rings=2)
        # a lower window in front of the cupola (art y 40-47 blue)
        g.prism(kit.rbox(cx - 2.2, cy + 5.6, cx + 2.2, cy + 8.0, 0.5, 1), [], 0.34, 0.352, m["blue"], bottom=False)

    # ---- the orb sockets (357) ----
    for cx, cy in ORBS:
        g.prism(kit.ell(cx, cy, 10.8, 11.0, 32), [], DECK - 0.005, 0.322, m["orb_bezel"], chamfer=0.8, drop=0.012, bottom=False)
        g.prism(kit.ell(cx, cy, 9.0, 9.2, 32), [kit.ell(cx, cy, 7.6, 7.8, 32)], 0.32, 0.33, m["bezel"], bottom=False)
        g.dome(cx, cy, 7.8, 8.0, 0.318, 0.05, m["orb"], n=24, rings=5)
        for ey, ry_ in ((38.5, 1.9), (44.5, 1.9)):
            g.dome(cx - 0.6, ey, 1.6, ry_, 0.352, 0.018, m["eye"], n=10, rings=2)

    k.no_needles()
    objects = k.objects()

    res = b.finish(objects, fp, bake=bake, preview=preview, grit=kit.GRIT)
    if views:
        render_views(objects, Path(views), b)
    return objects


def render_views(objects, out, b):
    """Top / front / rear / side / 3-4 high / game / underside renders (Eevee, the baked materials)."""
    from mathutils import Vector
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.05, 0.05, 0.06, 1)
    bg.inputs[1].default_value = 2.0
    # HD-ground stand-in: a dark sandy plane at z=0
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.001))
    ground = bpy.context.active_object
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.09, 0.075, 0.06, 1)
    ground.data.materials.append(gm)
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 5.0
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(40), math.radians(-20), math.radians(30))
    w, h = b.W * lt.PX, b.H * lt.PX

    def shot(name, loc, look, ortho=None, lens=50, res=(1600, 800), hide_ground=False):
        cd = bpy.data.cameras.new(name)
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = ortho
        else:
            cd.lens = lens
        cam = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(cam)
        cam.location = loc
        cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = res
        ground.hide_render = hide_ground
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    shot("top", (0, 0, 10), (0, 0, 0), ortho=w * 1.02, res=(1560, 700))
    bpy.data.objects["top"].rotation_euler = (0, 0, 0)
    scene.camera = bpy.data.objects["top"]
    scene.render.filepath = str(out / "top.png")
    bpy.ops.render.render(write_still=True)
    shot("game", (0, -h * 1.15, h * 1.75), (0, -0.2, 0), lens=40, res=(1600, 900))
    shot("front", (0, -w * 1.05, 3.2), (0, 0, 0.0), lens=50, res=(1600, 600))
    shot("rear", (0, w * 1.05, 3.2), (0, 0, 0.0), lens=50, res=(1600, 600))
    shot("side", (w * 0.75, 0, 1.6), (0, 0, 0.1), lens=50, res=(1000, 600))
    shot("q34", (w * 0.55, -w * 0.5, w * 0.42), (0, 0, 0.1), lens=50, res=(1600, 900))
    shot("close_turret", (b.x(168), b.y(40) - 6.0, 5.0), (b.x(168), b.y(46), 0.3), lens=50, res=(1200, 700))
    shot("close_hatch", (b.x(62), b.y(84) - 6.5, 5.5), (b.x(62), b.y(80), 0.3), lens=50, res=(1200, 700))
    shot("under", (w * 0.6, -w * 0.6, -w * 0.4), (0, 0, 0), lens=50, res=(1000, 600), hide_ground=True)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, views=argv[argv.index("--views") + 1] if "--views" in argv else None, preview=lt.preview_arg())
