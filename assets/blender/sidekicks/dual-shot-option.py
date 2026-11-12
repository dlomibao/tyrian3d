"""Dual Shot Option (sidekick item 2, tyrian.shp#8 frames 169, 188, 207).

What it is: a mounted side pod, two grey drum guns side by side, nose up the screen. Read from the
12x14 sprite (x = column edge - 6, right; y = 7 - row edge, up the screen; z up; units sprite px):

- Two guns on axes x = -3 / +3, z = 3 (columns 1-4 and 7-10): a polished muzzle ring (row 1, r 2)
  with a black bore, a thin neck (row 2: only columns 2-3 are colour, r 1), a bright collar (rows
  3-4), a dark seam (row 5), a trim ring (row 6), a dark groove (row 7), the drum (row 8) running
  into the rear housing at row 9.
- Each gun rides in an open-topped U cradle (the dark 1 px columns 0/5 and 6/11 beside the bright
  gun columns, rows 3-8: the cradle walls seen from above), a round-bottomed trough whose two inner
  walls meet as a central spine with a clamp strap (the 10 at column 5, row 7). A recoil buffer
  tube runs under each outer wall.
- A merged twin-lobed rear housing (rows 9-12): a dark front collar band (row 9, 3 2 2 2) with a
  dark mouth ring round each gun, the body tapering row by row (12, 10, 8, 4 px wide) to a tail
  plate (row 12) with two small exhaust vents (the 254 / 1 pixels at columns 3 and 8).
- Underneath: a twin-lobed belly and a short mounting pylon (plausible only).

Animation (the game plays 169, 188, 207, 188 after a shot): on 188 and 207 both guns recoil 1 and
2 px down the screen into the housing (the sprite's bands slide down while the cradle walls, the
housing and tail stay) and a muzzle flash shows in front of each barrel. One model: the cradle and
housing always show; each gun pose and its flash is a frame part (common.frame_part, D17).

The sprite draws light (bright upper-left, dark right/bottom ring); the model leaves that to the
game: satin grey metal in each region's own palette index, the 13-15 spots are sheen.

Writes public/models/sidekicks/dual-shot-option.glb and src/render/spriteModels/dual-shot-option.json
(common.export_sprite_model; --out X.glb writes only that glb instead).

    Blender --background --factory-startup --python dual-shot-option.py -- [--out X.glb] [--no-bake]
        [--measure DIR]   (top-view masks per frame + region raycast JSON into DIR)
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
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "dual-shot-option"
REF = f"sidekick-{NAME}"
PX = 1 / 12
FRAMES = [(169, 0), (188, 1), (207, 2)]  # (sprite frame, recoil px)
ZG = 3.0  # gun axis height, px
GX = (-3.0, 3.0)  # gun axes, px

# Palette index per region (median of the sprite's pixels in that region, darkest shading 1-2 and
# highlights 13-15 left out as lighting; see notes in the sheet).
PAL = {
    "muzzle": 8, "neck": 6, "collar": 10, "seam": 5, "ring": 8, "groove": 4, "drum": 6,
    "cradle": 3, "spine": 3, "strap": 5, "buffer": 5, "band": 4, "mouth": 2, "housing": 5, "yoke": 7,
    "tail": 4, "vent": 3, "slot": 3, "bore": 254, "pylon": 4,
}
FLASH = {"red": (119, 3.0), "orange": (122, 3.5), "amber": (123, 4.0), "yellow": (124, 4.5)}


def materials(sprite):
    mats, slot = [], {}
    for key, idx in PAL.items():
        if key == "bore":
            m = common.palette_material(sprite, idx, f"{NAME}_{key}", metallic=0.0, roughness=0.9)
        else:
            rough = {"collar": 0.32, "muzzle": 0.32, "ring": 0.34}.get(key, 0.42)
            m = common.palette_material(sprite, idx, f"{NAME}_{key}", metallic=0.55, roughness=rough)
        slot[key] = len(mats)
        mats.append(m)
    for key, (idx, e) in FLASH.items():
        slot[key] = len(mats)
        mats.append(common.palette_material(sprite, idx, f"{NAME}_flash_{key}", emission_strength=e))
    return mats, slot


# --- geometry -------------------------------------------------------------------------------------

def area2(pts):
    return 0.5 * sum(x0 * z1 - x1 * z0 for (x0, z0), (x1, z1) in zip(pts, pts[1:] + pts[:1]))


def ccw(pts):
    return pts if area2(pts) > 0 else list(reversed(pts))


def seg_normals(pts):
    """Outward normal of each segment of a CCW loop in (x, z)."""
    out = []
    n = len(pts)
    for i in range(n):
        (x0, z0), (x1, z1) = pts[i], pts[(i + 1) % n]
        dx, dz = x1 - x0, z1 - z0
        ln = math.hypot(dx, dz) or 1e-9
        out.append((dz / ln, -dx / ln))
    return out


def loft(P, rings, mats, cap0=True, cap1=True):
    """Rings [(y, [(x, z)...])] ordered front (high y) to back, same point count, CCW in (x, z).
    mats[i] is the material between ring i and i + 1 (and of the caps at either end). Equal-y
    neighbours make a step face (an annulus)."""
    vs = [[P.v((x, y, z)) for x, z in pts] for y, pts in rings]
    for i in range(len(rings) - 1):
        (y0, p0), (y1, p1) = rings[i], rings[i + 1]
        nrm = seg_normals(p0 if area2(p0) >= area2(p1) else p1)
        n = len(p0)
        for a in range(n):
            b = (a + 1) % n
            if abs(y1 - y0) < 1e-6:
                out = (0, -1, 0) if abs(area2(p1)) < abs(area2(p0)) else (0, 1, 0)
            else:
                out = (nrm[a][0], 0, nrm[a][1])
            P.f((vs[i][a], vs[i][b], vs[i + 1][b], vs[i + 1][a]), mats[i], out=out)
    if cap0:
        P.f(vs[0], mats[0], out=(0, 1, 0))
    if cap1:
        P.f(vs[-1], mats[-1], out=(0, -1, 0))


def circle(cx, cz, r, n=12, rz=None, phase=0.5):
    rz = r if rz is None else rz
    return [(cx + r * math.cos(2 * math.pi * (i + phase) / n), cz + rz * math.sin(2 * math.pi * (i + phase) / n))
            for i in range(n)]


def tube(P, cx, cz, stations, n=16):
    """A round part along y: stations [(y, r, mat)] front to back; mat is for the span to the next."""
    rings = [(y, circle(cx, cz, max(r, 0.02), n)) for y, r, _ in stations]
    loft(P, rings, [m for _, _, m in stations[:-1]] + [stations[-2][2]])


def u_loop(cx, ro, ri, top, ch=0.14, n=10):
    """The U cradle's section round a gun at (cx, ZG): an outer half circle `ro` (bottom), walls up
    to `top`, a chamfered wall top, the inner half circle `ri` (the trough)."""
    pts = []
    for i in range(n + 1):  # outer arc, x = cx + ro (angle 0) round the bottom to cx - ro (angle pi)
        a = -math.pi * i / n
        pts.append((cx + ro * math.cos(a), ZG + ro * math.sin(a)))
    # left wall up, top, down the inner face
    pts += [(cx - ro, top - ch), (cx - ro + ch, top), (cx - ri - ch, top), (cx - ri, top - ch), (cx - ri, ZG)]
    for i in range(1, n):  # inner arc from the left (angle pi) round the bottom to the right
        a = -math.pi + math.pi * i / n
        pts.append((cx + ri * math.cos(a), ZG + ri * math.sin(a)))
    pts += [(cx + ri, ZG), (cx + ri, top - ch), (cx + ri + ch, top), (cx + ro - ch, top), (cx + ro, top - ch)]
    return ccw(pts)


def housing_loop(w, h, zc, n=24, p=3.6, dip_top=0.5, dip_bot=0.7):
    """A twin-lobed section (one per gun merged): a superellipse with a valley along the centre top
    and belly."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * (i + 0.5) / n
        c, s = math.cos(t), math.sin(t)
        x = w * math.copysign(abs(c) ** (2 / p), c)
        z = h * math.copysign(abs(s) ** (2 / p), s)
        g = math.exp(-(x / (0.32 * w + 0.4)) ** 2)
        if s > 0:
            z -= dip_top * g * s
        else:
            z += dip_bot * g * (-s)
        pts.append((x, zc + z))
    return ccw(pts)


def box(P, x0, x1, y0, y1, z0, z1, ch, mat):
    T.hull(P, T.cbox(x0, x1, y0, y1, z0, z1, ch), mat)


def build_static(P, S):
    # The cradles: U troughs, a chamfered front lip band, panel grooves, ends inside the housing.
    for cx in GX:
        L = lambda ro, ri, top: u_loop(cx, ro, ri, top)  # noqa: E731
        rings = [(4.0, L(2.84, 2.36, 3.66)), (3.86, L(3.0, 2.2, 3.82)), (3.2, L(3.0, 2.2, 3.82)),
                 (3.2, L(2.88, 2.2, 3.72)), (3.04, L(2.88, 2.2, 3.72)), (3.04, L(3.0, 2.2, 3.82)),
                 (-0.42, L(3.0, 2.2, 3.82)), (-0.42, L(2.88, 2.2, 3.72)), (-0.58, L(2.88, 2.2, 3.72)),
                 (-0.58, L(3.0, 2.2, 3.82)), (-2.6, L(3.0, 2.2, 3.82))]
        loft(P, rings, [S["cradle"]] * (len(rings) - 1))
        # Recoil buffer under the outer wall: a tube with end caps and two clamp rings.
        bx = cx + (-2.5 if cx < 0 else 2.5)
        tube(P, bx, 1.55, [(3.55, 0.25, S["buffer"]), (3.4, 0.5, S["buffer"]), (2.6, 0.5, S["cradle"]),
                           (2.6, 0.58, S["cradle"]), (2.1, 0.58, S["buffer"]), (2.1, 0.5, S["buffer"]),
                           (-2.4, 0.5, S["buffer"])], n=12)
    # The central spine over the two inner walls, with a clamp strap (row 7) and bolt heads.
    box(P, -0.85, 0.85, -2.4, 3.92, 2.6, 4.02, 0.18, S["spine"])
    box(P, -1.05, 1.05, -0.88, -0.12, 3.7, 4.22, 0.12, S["strap"])
    for by in (1.8, -1.6):
        tube(P, 0.0, 4.1, [(by + 0.22, 0.22, S["strap"]), (by - 0.22, 0.22, S["strap"])], n=8)
    # The rear housing: twin-lobed, dark front band (row 9), then the body tapering to the tail.
    def curve(xs, ys):  # T.pchip wants ascending stations
        f = T.pchip(xs[::-1], ys[::-1])
        return f
    W = curve([-2.0, -2.5, -3.0, -3.5, -4.0, -4.5, -5.0, -5.5, -6.0],
              [6.0, 5.95, 5.65, 5.2, 4.6, 3.9, 3.0, 2.15, 1.8])
    H = curve([-2.0, -3.0, -4.0, -5.0, -5.6, -6.0], [2.65, 2.6, 2.4, 2.1, 1.9, 1.75])
    ZC = curve([-2.0, -6.0], [3.0, 3.05])
    hl = lambda y, g=0.0, k=1.0: housing_loop(W(y) * k + g, H(y) * k + g, ZC(y))  # noqa: E731
    rings = [(-1.9, hl(-2.0, -0.14)), (-2.04, hl(-2.04)), (-2.86, hl(-2.86, 0.0)),
             (-2.86, hl(-2.86, -0.12)), (-3.02, hl(-3.02, -0.12)), (-3.02, hl(-3.02))]
    mats = [S["band"]] * 3 + [S["housing"]] * 2
    ys = [-3.4, -3.8, -4.2, -4.6, -5.0, -5.3, -5.6, -5.85]
    for y in ys:
        rings.append((y, hl(y)))
        mats.append(S["housing"])
    rings += [(-5.85, hl(-5.85, -0.14)), (-5.98, hl(-5.98, -0.3)), (-6.02, hl(-6.0, -0.45))]
    mats += [S["housing"], S["tail"], S["tail"]]
    loft(P, rings, mats)
    # Exhaust slots along each lobe's crest (the dark columns 3 / 8 in rows 10-11) running back
    # to the vents, and the yoke strap across the valley (row 11's light 10 7 7 7).
    def top_z(y, x):
        pts = [p for p in hl(y) if p[1] > ZC(y)]
        pts.sort()
        for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
            if x0 <= x <= x1:
                return z0 + (z1 - z0) * (x - x0) / max(1e-9, x1 - x0)
        return pts[0][1] if x < pts[0][0] else pts[-1][1]

    def strap_loop(y, x0, x1, up, down=0.3, n=6, ch=0.1):
        xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
        top = [(x, top_z(y, x) + up) for x in xs]
        top[0] = (x0, top_z(y, x0) + up - ch)
        top[-1] = (x1, top_z(y, x1) + up - ch)
        top.insert(1, (x0 + ch, top_z(y, x0 + ch) + up))
        top.insert(-1, (x1 - ch, top_z(y, x1 - ch) + up))
        bot = [(x, top_z(y, x) - down) for x in (x1, x0)]
        return ccw(top + bot)

    for xc in (-2.5, 2.5):
        ys_ = [-2.95, -3.1, -3.6, -4.1, -4.6, -4.95, -5.1]
        ups = [0.0, 0.1, 0.1, 0.1, 0.1, 0.1, 0.0]
        loft(P, [(y, strap_loop(y, xc - 0.34, xc + 0.34, u, n=3, ch=0.08)) for y, u in zip(ys_, ups)],
             [S["slot"]] * (len(ys_) - 1))
    ys_ = [-4.1, -4.22, -4.78, -4.9]
    ups = [0.04, 0.16, 0.16, 0.04]
    loft(P, [(y, strap_loop(y, -1.75, 1.75, u, n=8)) for y, u in zip(ys_, ups)], [S["yoke"]] * 3)
    # Dark mouth rings where the guns enter the housing.
    for cx in GX:
        loft(P, [(-1.78, circle(cx, ZG, 2.36)), (-1.78, circle(cx, ZG, 2.14)),
                 (-2.3, circle(cx, ZG, 2.14)), (-2.3, circle(cx, ZG, 2.5))],
             [S["mouth"], S["mouth"], S["mouth"]], cap0=False, cap1=False)
        loft(P, [(-1.78, circle(cx, ZG, 2.36)), (-1.95, circle(cx, ZG, 2.5)),
                 (-2.3, circle(cx, ZG, 2.5))], [S["band"], S["band"]], cap0=False, cap1=False)
    # Tail exhaust vents at columns 3 / 8 (row 12).
    for vx in (-2.1, 2.1):
        tube(P, vx, 2.8, [(-4.9, 0.42, S["vent"]), (-5.5, 0.42, S["vent"]), (-5.5, 0.26, S["bore"]),
                           (-5.25, 0.26, S["bore"])], n=10)
    # Machined detail the tilted camera sees: a chamfered rail and two bolt heads along each cradle's
    # outer wall top, and bolt heads along the housing's front band (row 9).
    for sx in (-1, 1):
        xo = sx * 5.7
        box(P, xo - 0.17, xo + 0.17, 0.5, 2.7, 3.78, 3.95, 0.05, S["cradle"])
        for by in (-0.2, 3.5):
            box(P, xo - 0.22, xo + 0.22, by - 0.22, by + 0.22, 3.78, 3.98, 0.07, S["cradle"])
        for bx in (4.7, 5.35):
            z = top_z(-2.45, sx * bx) - 0.05
            box(P, sx * bx - 0.2, sx * bx + 0.2, -2.65, -2.25, z, z + 0.2, 0.06, S["band"])
    # Underneath: the mounting pylon in the belly valley.
    box(P, -0.9, 0.9, -4.6, -0.4, -0.6, 1.4, 0.2, S["pylon"])


def build_gun(P, S, cx, s):
    """One gun recoiled s px (frame 169 positions minus s)."""
    st = [(5.4, 0.95, "bore"), (5.85, 0.95, "ring"), (5.85, 1.3, "ring"), (6.0, 1.3, "ring"),
          (6.0, 1.72, "muzzle"), (5.87, 2.0, "muzzle"),
          (5.13, 2.0, "muzzle"), (5.0, 1.78, "neck"), (5.0, 1.0, "neck"), (4.05, 1.0, "collar"),
          (4.05, 1.62, "collar"), (3.88, 2.04, "collar"), (3.06, 2.04, "collar"), (3.06, 1.9, "collar"),
          (2.94, 1.9, "collar"), (2.94, 2.04, "collar"), (2.14, 2.04, "collar"), (2.0, 1.82, "seam"),
          (1.0, 1.82, "ring"), (0.86, 2.08, "ring"), (0.14, 2.08, "ring"), (0.0, 1.82, "groove"),
          (-1.0, 1.82, "drum"), (-1.12, 2.0, "drum"), (-1.6, 2.0, "drum"), (-2.0, 1.55, "drum"),
          (-2.25, 1.2, "drum")]
    # Front to back, with the bore's floor first: reorder so y decreases (the bore is a pocket).
    rings = [(st[0][0] - s, circle(cx, ZG, st[0][1]))]
    mats = []
    for (y, r, m) in st[1:]:
        rings.append((y - s, circle(cx, ZG, r)))
        mats.append(S[m])
    # The pocket ring at 5.4 is behind the face at 6.0: loft draws its walls; orientation by hints.
    P2 = P
    vs = [[P2.v((x, y, z)) for x, z in pts] for y, pts in rings]
    for i in range(len(rings) - 1):
        (y0, p0), (y1, p1) = rings[i], rings[i + 1]
        n = len(p0)
        r0, r1 = math.dist(p0[0], (cx, ZG)), math.dist(p1[0], (cx, ZG))
        for a in range(n):
            b = (a + 1) % n
            mid = ((p0[a][0] + p0[b][0]) / 2 - cx, (p0[a][1] + p0[b][1]) / 2 - ZG)
            if i in (0, 2):  # bore wall and the crown's inner wall: face the axis
                out = (-mid[0], 0, -mid[1])
            elif abs(y1 - y0) < 1e-6:
                out = (0, 1, 0) if (i == 1 or r1 > r0) else (0, -1, 0)
            else:
                out = (mid[0], 0, mid[1])
            P2.f((vs[i][a], vs[i][b], vs[i + 1][b], vs[i + 1][a]), mats[i - 1] if i else S["bore"], out=out)
    P2.f(vs[0], S["bore"], out=(0, 1, 0))
    P2.f(vs[-1], S["drum"], out=(0, -1, 0))


def build_flash(P, S, cx, s):
    """Muzzle flash in front of the recoiled muzzle (front at y = 6 - s), leaning outward."""
    side = -1 if cx < 0 else 1
    y0 = 6.0 - s
    if s == 1:  # 188: row 1 three px wide (red, yellow, red) centred 0.5 px outboard; row 0 a red tip
        c = cx + 0.5 * side
        shells = [("red", [(y0 + 0.02, 1.45, 1.0, 0.0), (y0 + 1.0, 1.4, 0.9, 0.0), (y0 + 1.6, 0.55, 0.5, 0.05),
                           (y0 + 2.25, 0.0, 0.0, 0.1)]),
                  ("yellow", [(y0 + 0.03, 0.55, 0.55, 0.9), (y0 + 0.9, 0.5, 0.5, 0.9), (y0 + 1.3, 0.0, 0.0, 0.9)])]
        base = [(c, sh) for sh in shells]
    else:  # 207: row 2 full width (red, yellow, orange, red), row 1 two px (amber, orange), row 0 red tip
        shells = [(cx, ("red", [(y0 + 0.02, 1.95, 1.3, 0.0), (y0 + 0.95, 1.9, 1.2, 0.0), (y0 + 1.15, 1.05, 0.9, 0.05),
                                (y0 + 1.95, 0.95, 0.8, 0.1), (y0 + 2.2, 0.5, 0.5, 0.15), (y0 + 3.25, 0.0, 0.0, 0.2)])),
                  (cx + 0.15 * side, ("orange", [(y0 + 0.03, 1.2, 1.0, 0.6), (y0 + 0.9, 1.15, 0.9, 0.6),
                                                 (y0 + 1.9, 0.75, 0.6, 0.55), (y0 + 2.3, 0.0, 0.0, 0.5)])),
                  (cx - 0.5 * side, ("yellow", [(y0 + 0.04, 0.55, 0.55, 1.15), (y0 + 0.9, 0.5, 0.5, 1.15),
                                                (y0 + 1.25, 0.0, 0.0, 1.15)])),
                  (cx - 0.45 * side, ("amber", [(y0 + 1.0, 0.5, 0.5, 0.95), (y0 + 1.9, 0.45, 0.45, 0.95),
                                               (y0 + 2.2, 0.0, 0.0, 0.95)]))]
        base = shells
    for c, (col, secs) in base:
        # Lean the tip outward as the sprite's row 0 pixel does (column 2 / 9).
        tip = cx + 0.5 * side
        rings = []
        for k, (y, w, h, dz) in enumerate(secs):
            t = (y - y0) / max(1e-6, secs[-1][0] - y0)
            xc = c + (tip - c) * max(0.0, t - 0.4) / 0.6
            rings.append((y, circle(xc, ZG + dz, max(w, 0.01), 8, rz=max(h, 0.01))))
        # Reverse to go front (high y) to back.
        rings = rings[::-1]
        loft(P, rings, [S[col]] * (len(rings) - 1))


def finish(P, mats, coll, name, smooth_angle=34):
    P.orient()
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.transform(bm, matrix=Matrix.Scale(PX, 4), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    return obj


# --- bake (copied from ship-u-ship.py's bake_maps, neutral tint, one object, unique image names) ---

def bake_maps(obj, out_dir, textured, size=512, samples=64):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{obj.name}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{obj.name}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    # Per-object material copies so each frame object wires its own maps.
    mats = []
    for i, m in enumerate(me.materials):
        if m is None:
            mats.append(None)
            continue
        if i in textured:
            c = m.copy()
            c.name = m.name + "_" + obj.name.split("-")[-1]
            me.materials[i] = c
            mats.append(c)
        else:
            mats.append(m)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        L = nt.links.new
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
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.02
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.08
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.003
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                L(v, comb.inputs[k])
            L(comb.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
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

    for i in textured:
        m = mats[i]
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


# --- measuring ------------------------------------------------------------------------------------

def measure(objs_by_frame, sprite, out_dir, k=16):
    """Per frame: a top-view mask render (k px per sprite px, transparent film, Workbench flat) and a
    raycast from above at each sprite pixel centre: palette index of the material hit."""
    from mathutils.bvhtree import BVHTree
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_object_outline = False
    scene.display.shading.show_cavity = False
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x, scene.render.resolution_y = 12 * k, 14 * k
    scene.render.resolution_percentage = 100
    cd = bpy.data.cameras.new("mcam")
    cd.type = "ORTHO"
    cd.ortho_scale = 14 * PX
    cam = bpy.data.objects.new("mcam", cd)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 5)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    every = [o for objs in objs_by_frame.values() for o in objs]
    report = {}
    for frame, objs in objs_by_frame.items():
        for o in every:
            o.hide_render = o not in objs
        scene.render.filepath = str(out_dir / f"top-{frame}.png")
        bpy.ops.render.render(write_still=True)
        # raycast
        dg = bpy.context.evaluated_depsgraph_get()
        hits = []
        trees = []
        for o in objs:
            bm = bmesh.new()
            bm.from_object(o, dg)
            bm.transform(o.matrix_world)
            bm.faces.ensure_lookup_table()
            trees.append((BVHTree.FromBMesh(bm), bm, o))
        grid = []
        for r in range(14):
            row = []
            for c in range(12):
                p = Vector(((c + 0.5 - 6) * PX, (7 - r - 0.5) * PX, 5.0))
                best = None
                for tree, bm, o in trees:
                    h = tree.ray_cast(p, Vector((0, 0, -1)), 10.0)
                    if h[0] is not None and (best is None or h[3] < best[0]):
                        mi = bm.faces[h[2]].material_index
                        mname = o.data.materials[mi].name
                        best = (h[3], mname)
                row.append(best[1] if best else None)
            grid.append(row)
        for _, bm, _ in trees:
            bm.free()
        report[str(frame)] = grid
    for o in every:
        o.hide_render = False
    bpy.data.objects.remove(cam, do_unlink=True)
    (out_dir / "raycast.json").write_text(json.dumps(report))


# --- main -----------------------------------------------------------------------------------------

def temp_join(objs, coll, name):
    """A joined copy of `objs` (for the per-frame outline shell)."""
    copies = []
    for o in objs:
        c = o.copy()
        c.data = o.data.copy()
        c.modifiers.clear()
        coll.objects.link(c)
        copies.append(c)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for c in copies:
        c.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    j = bpy.context.view_layer.objects.active
    j.name = name
    return j


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(WT, REF)
    for o in list(bpy.data.objects):  # the factory scene's cube, camera and light
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    mats, S = materials(sprite)
    textured = {S[k] for k in PAL if k != "bore"}

    def weighted(o):
        wn = o.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50

    P = T.Part(f"{NAME}-body")
    build_static(P, S)
    body = finish(P, mats, coll, f"{NAME}-body")
    T.cull_hidden(body)
    tri = lambda o: sum(len(p.vertices) - 2 for p in o.data.polygons)  # noqa: E731
    print(f"{NAME} body: {tri(body)} triangles")
    guns, flashes = {}, {}
    for frame, s in FRAMES:
        G = T.Part(f"{NAME}-guns-{frame}")
        for cx in GX:
            build_gun(G, S, cx, s)
        g = finish(G, mats, coll, f"{NAME}-guns-{frame}")
        print(f"{NAME} guns {frame}: {tri(g)} triangles")
        guns[frame] = g
        if s:
            F = T.Part(f"{NAME}-flash-{frame}")
            for cx in GX:
                build_flash(F, S, cx, s)
            flashes[frame] = finish(F, mats, coll, f"{NAME}-flash-{frame}", smooth_angle=80)
    by_frame = {f: [body, guns[f]] + ([flashes[f]] if f in flashes else []) for f, _ in FRAMES}
    if "--measure" in argv:
        measure(by_frame, sprite, argv[argv.index("--measure") + 1])
    shells = {}
    for frame, _ in FRAMES:
        j = temp_join([body, guns[frame]], coll, f"{NAME}-join-{frame}")
        sh = common.outline_shell(j, coll, faces=900)
        sh.name = f"{NAME}-outline-{frame}"
        bpy.data.objects.remove(j, do_unlink=True)
        shells[frame] = sh
        print(f"{NAME} outline {frame}: {len(sh.data.polygons)} faces")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        every = [body] + list(guns.values())
        for target, show in [(body, guns[169])] + [(guns[f], body) for f, _ in FRAMES]:
            for o in every:
                o.hide_render = o not in (target, show)
            for o in list(flashes.values()) + list(shells.values()):
                o.hide_render = True
            bake_maps(target, tempfile.mkdtemp(prefix="dso_bake_"), textured)
        for o in coll.objects:
            o.hide_render = False
        fmt = "WEBP"
    for o in [body] + list(guns.values()):
        weighted(o)
    for frame, _ in FRAMES:
        common.frame_part(guns[frame], [frame])
        common.frame_part(shells[frame], [frame])
        if frame in flashes:
            common.frame_part(flashes[frame], [frame])
    export = [body] + [guns[f] for f, _ in FRAMES] + list(flashes.values()) + [shells[f] for f, _ in FRAMES]
    print(f"{NAME} per frame triangles: " + ", ".join(
        f"{f}: {tri(body) + tri(guns[f]) + (tri(flashes[f]) if f in flashes else 0)}" for f, _ in FRAMES))
    if "--out" in argv:
        common.export_glb(export, out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(WT, export, f"sidekicks/{NAME}", sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
