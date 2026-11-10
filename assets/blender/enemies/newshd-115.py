"""newshd-115, a twin-engine strike drone with two heat-glowing side nacelles
(newshd.shp frame 115, 2x2 = 24 x 28 px; level 1.2 ASTEROID2, palette 5).

What it is (scout): a FLYING CRAFT. Type 283 spawns on the sky layer at the screen edges with
mv(0, 2) and swings round on a curve (0,2 -> 1,1 -> 2,0 -> 1,-1); turret 5 is its gun. So it flies
free (closed round belly), and faces its direction of travel: the nose is DOWN-screen (sprite row
27), the engines are at the top (rows 0-2).

Reading of the sprite (tools/calibration/rubric.md "Reading a sprite"), pixel edges (col, row):
- Rear wing bar: rows 2-9, cols 2-23 (corners clipped one px), browns 163-175, median 166. The pale
  167-175 column at col 6 and the light row 7-8 band are sheen on its top, not parts.
- Central fuselage: cols 8-17 from the wing to row 22, then a tapered nose to a point at row 27
  (cols 9-16, 10-16, 10-15, 11-14). Brown 163-169 (median 165); the light column 11-13 (169-173) is
  sheen on a rounded dorsal spine; col 14-16 darker (161-163) is the shaded right flank.
- Side nacelles: cols 4-8 and 17-21, rows 8-22, red ramp 112-118 (median 115) with a hot core
  along their middle (cols 5-6 / 18-19, 118-126, peak 124-126 at rows 14-16): the fire ramp, so the
  nacelles are red-painted armour with a glowing heat channel down their tops (emissive), round
  noses (rows 19-22 taper).
- Exhaust: rows 0-1, cols 6-17, dark reds 113-118 with two hot spots at cols 9-10 and 14-15 (121-124):
  two hard exhaust bells at the rear of the fuselage, a glowing disc (121, core 124) inside each.
- No glass colours anywhere: no canopy (a drone). The gun (turret 5) is the nose cannon.

Built in sprite px (x = column - 12, y = row, z up; usp_talon.finish moves it to Blender).
The craft's axis is x = 0.5 (the sprite is drawn about column edge 12.5).

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshd-115.py
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshd-115"
AX = 0.5          # craft axis (x)
POD_X = 6.5       # nacelle axis offset from the craft axis (pods at x -6 and 7)

# --- palette roles (the sprite's own indices, medians of each region) --------------------------
PAL = {
    "WING": 165, "WING_PLATE": 166, "WING_EDGE": 164, "HULL": 165, "HULL_DK": 163, "SPINE": 167,
    "POD": 116, "POD_DK": 114, "POD_RAIL": 117, "GLOW": 121, "HOT": 124,
    "NOZZLE": 115, "NOZZLE_DK": 114, "NOZZLE_LIP": 117, "GUN": 161,
}


# --- sections ----------------------------------------------------------------------------------

def superellipse(cx, cz, w, top, bot, n=20, e_top=2.6, e_bot=2.0):
    """A closed (x, z) loop: half-width w, top height `top`, belly depth `bot` below cz (round)."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        e = e_top if s >= 0 else e_bot
        x = cx + w * math.copysign(abs(c) ** (2 / e), c)
        z = cz + (top if s >= 0 else bot) * math.copysign(abs(s) ** (2 / e), s)
        pts.append((x, z))
    return pts


# Fuselage stations along y (rows): half-width, top, belly depth, centre height.
FY = [1.6, 2.6, 6.0, 9.5, 14.0, 19.0, 21.5, 22.6, 23.6, 24.6, 25.6, 26.5, 27.1]
FW = [3.6, 4.3, 4.5, 4.5, 4.5, 4.5, 4.55, 4.5, 3.62, 3.35, 2.45, 1.6, 0.45]
FT = [1.3, 1.4, 1.6, 2.7, 3.5, 3.4, 3.1, 2.8, 2.45, 2.1, 1.75, 1.4, 1.05]
FB = [2.0, 2.3, 2.6, 2.7, 2.7, 2.6, 2.4, 2.1, 1.8, 1.55, 1.3, 1.0, 0.6]
FC = [0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]
fw, ft, fb, fc = (T.pchip(FY, v) for v in (FW, FT, FB, FC))


def fus_loop(y, grow=0.0):
    w, t, b, c = fw(y) + grow, ft(y) + grow, fb(y) + grow, fc(y)
    return superellipse(AX, c, max(w, 0.05), max(t, 0.05), max(b, 0.05), n=22), (AX, c)


# Nacelles: radius along y, axis height.
PY = [6.8, 7.6, 9.0, 19.5, 20.2, 21.0, 21.6, 22.0]
PR = [1.3, 1.85, 2.0, 2.0, 1.8, 1.3, 0.95, 0.45]
# the blunt noses toe in (the sprite's pod tips step a px inboard per row: rows 20 and 21)
pshift = T.pchip([6.0, 19.5, 20.5, 21.5, 22.0], [0.0, 0.0, 0.45, 1.0, 1.15])
pr = T.pchip(PY, PR)
POD_Z = 0.9


def pod_loop_f(cx0):
    inb = 1 if cx0 < AX else -1

    def f(y, grow=0.0):
        r = max(pr(y) + grow, 0.05)
        cx = cx0 + inb * pshift(y)
        return superellipse(cx, POD_Z, r, r * 1.02, r * 0.95, n=18, e_top=2.2, e_bot=2.0), (cx, POD_Z)
    return f


# --- parts -------------------------------------------------------------------------------------

def build_fuselage(P, M):
    """Fuselage core with ribbed armour: shallow grooves across the back between rows 10 and 21
    (step rings), so the 'ribbed body' of the sprite is real geometry; the nose and tail smooth."""
    rings = []
    mats = []
    ys = [1.6, 2.0, 2.6, 4.0, 6.0, 8.0, 9.6]
    for y in ys:
        rings.append((fus_loop, y, 0.0))
        mats.append(M["HULL"])
    # ribs: plate (grow 0) - groove (grow -0.28) - plate
    for y0 in (10.3, 12.9, 15.5, 18.1):
        for y, g, m in ((y0, 0.0, M["HULL_DK"]), (y0, -0.28, M["HULL_DK"]), (y0 + 0.45, -0.28, M["HULL"]),
                        (y0 + 0.45, 0.0, M["HULL"])):
            rings.append((fus_loop, y, g))
            mats.append(m)
        for y in (y0 + 1.2, y0 + 2.0):
            rings.append((fus_loop, y, 0.0))
            mats.append(M["HULL"])
    for y in (21.0, 21.8, 22.6, 23.4, 24.2, 25.0, 25.8, 26.5, 27.1):
        rings.append((fus_loop, y, 0.0))
        mats.append(M["HULL"])
    T.loft_rings(P, rings, mats)


def build_spine(P, M):
    """A raised dorsal keel (the sprite's light centre column is sheen on it): one continuous low
    chamfered ridge from the wing bar's leading edge to the nose, riding over the rib grooves."""
    ys = [8.6, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 21.5, 22.6, 23.6, 24.6, 25.4]
    pts = []
    for y in ys:
        zt = ft(y) + fc(y)
        hw = 0.95 if y < 21.5 else 0.95 - 0.35 * (y - 21.5) / 3.9
        top = 0.42 if y < 22.6 else 0.42 - 0.12 * (y - 22.6) / 2.8
        for x, dz in ((AX - hw, -0.1), (AX + hw, -0.1), (AX - hw * 0.6, top), (AX + hw * 0.6, top)):
            pts.append((x, y, zt + dz))
        pts.append((AX - hw, y, zt - 0.7))
        pts.append((AX + hw, y, zt - 0.7))
    T.hull(P, pts, M["SPINE"])


def build_wing(P, M):
    """The rear wing bar: a thick chamfered slab (rows 2.2-9.3, x -9.9..10.9) with lengthwise
    armour plates on top (real gaps between them = panel lines) and tip caps."""
    x0, x1 = -9.9, 10.9
    T.hull(P, T.cbox(x0, x1, 2.25, 9.3, -0.4, 2.3, 0.7, 0.7), M["WING"])
    # top plates: inboard of the nacelles, over the nacelle roots, outboard; both sides
    gap = 0.3
    spans = [(-9.4, -7.9), (-7.9 + gap, -4.2), (-4.2 + gap, AX - 0.15)]
    for sx0, sx1 in spans:
        for a, b in ((sx0, sx1), (2 * AX - sx1, 2 * AX - sx0)):
            T.hull(P, T.cbox(a, b, 2.9, 8.7, 2.1, 2.75, 0.3, 0.25), M["WING_PLATE"])
    # wing-tip caps (darker), a little proud at the very ends
    for a, b in ((x0 - 0.05, x0 + 0.9), (x1 - 0.9, x1 + 0.05)):
        T.hull(P, T.cbox(a, b, 2.6, 9.0, -0.5, 2.5, 0.45, 0.4), M["WING_EDGE"])
    # root fillets where the bar's leading edge meets each nacelle's outer flank (sprite row 9,
    # cols 3 and 21: the bar steps in to the pod over one row)
    for sx in (-1, 1):
        xo, xi = AX + sx * 10.0, AX + sx * 6.0
        pts = []
        for x, y in ((xo, 8.6), (xi, 8.6), (xi, 10.6), (AX + sx * 9.1, 10.2)):
            pts += [(x, y, -0.2), (x, y, 1.6 if y > 9.5 else 2.0)]
        T.hull(P, pts, M["WING_EDGE"])
    # leading-edge strip in front of the plates
    for a, b in ((-9.0, -4.0), (5.0, 10.0)):
        T.hull(P, T.cbox(a, b, 8.4, 9.2, 1.4, 2.42, 0.3, 0.3), M["WING_EDGE"])


def build_pods(P, M, glow_parts):
    """Two red nacelles beside the fuselage, round noses forward, roots in the wing; a framed heat
    channel along each top (glowing strip + hot core in the middle rows)."""
    for cx in (AX - POD_X, AX + POD_X):
        f = pod_loop_f(cx)
        ys = [6.8, 7.2, 7.6, 8.2, 9.0, 10.5, 12.0, 13.5, 15.0, 16.5, 17.8, 18.8, 19.5, 20.0, 20.5, 21.0, 21.4, 21.75, 22.0]
        rings = [(f, y, 0.0) for y in ys]
        # a nose band: groove at 18.6
        rings = [r for r in rings if r[1] < 18.6] + [(f, 18.6, 0.0), (f, 18.6, -0.2), (f, 18.95, -0.2), (f, 18.95, 0.0)] \
            + [r for r in rings if r[1] > 18.95]
        mats = []
        for (_, y, _), (_, y2, _) in zip(rings, rings[1:]):
            mats.append(M["POD_DK"] if y >= 18.6 and y2 <= 18.95 else (M["POD_DK"] if y >= 20.5 else M["POD"]))
        mats.append(M["POD"])
        T.loft_rings(P, rings, mats)
        # pylon fairing joining the nacelle to the fuselage flank (inboard side, under the top)
        inb = 1 if cx < AX else -1
        xi = cx + inb * 1.2
        xo = AX - inb * 3.9
        lo, hi = min(xi, xo), max(xi, xo)
        T.hull(P, T.cbox(lo, hi, 9.0, 18.0, -0.3, 2.0, 0.4, 0.4), M["POD_DK"])
        # heat-channel rails on top of the nacelle
        ztop = POD_Z + 1.75 * 1.02
        for dx in (-1.15, 1.15):
            T.hull(P, T.cbox(cx + dx - 0.28, cx + dx + 0.28, 9.6, 16.9, ztop - 0.75, ztop + 0.45, 0.15, 0.15), M["POD_RAIL"])
        # the glowing channel between the rails, and its hot core (separate emissive meshes)
        g = glow_parts["GLOW"]
        T.hull(g, T.cbox(cx - 0.9, cx + 0.9, 9.8, 16.7, ztop - 0.6, ztop + 0.2, 0.12, 0.12), 0)
        h = glow_parts["HOT"]
        T.hull(h, T.cbox(cx - 0.55, cx + 0.55, 12.2, 16.2, ztop - 0.3, ztop + 0.32, 0.15, 0.15), 0)
        # nacelle tail cap behind the wing (rows 6.8: inside the wing, closes the loft)


def ring_pts(cx, cz, w, h, n=20, e=2.6):
    return superellipse(cx, cz, w, h, h, n=n, e_top=e, e_bot=e)


def build_engines(P, M, glow, hot):
    """Two exhaust bells at the fuselage's tail (the sprite's rows 0-1: dark red 114-118 with the hot
    spots 121-124 at cols 9-10 and 14-15). Each is a machined, rounded-square convergent bell
    with a thick lip, a throat inside and a glowing disc (pal 121, hot core pal 124) set at the
    throat, visible only from behind. A splitter plate between them closes the tail."""
    NZ = 1.0
    for nx in (AX - 2.75, AX + 2.25):   # the sprite's hot spots: cols 9-10 and 14-15
        # (y, half-width, half-height): outer skin from the root (in the wing) to the mouth
        outer = [(3.0, 2.2, 1.3), (2.25, 2.4, 1.4), (2.25, 2.28, 1.28), (1.95, 2.28, 1.28), (1.95, 2.4, 1.4),
                 (0.9, 2.4, 1.45), (0.3, 2.05, 1.32)]
        inner = [(0.3, 1.7, 1.0), (0.9, 1.8, 1.05), (1.55, 1.6, 0.9)]
        rings = [[P.v((x, y, z)) for x, z in ring_pts(nx, NZ, w, h)] for y, w, h in outer + inner]
        ys = [r[0] for r in outer + inner]
        mats = [M["NOZZLE"], M["NOZZLE_DK"], M["NOZZLE"], M["NOZZLE_DK"], M["NOZZLE"], M["NOZZLE"],
                M["NOZZLE_LIP"], M["NOZZLE_DK"], M["NOZZLE_DK"]]
        n_out = len(outer)
        for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
            n = len(r0)
            for a in range(n):
                b = (a + 1) % n
                quad = (r0[a], r0[b], r1[b], r1[a])
                if abs(ys[i + 1] - ys[i]) < 1e-6:          # a step: groove wall or the lip face
                    w0, w1 = (outer + inner)[i][1], (outer + inner)[i + 1][1]
                    # rings run aft (y falling): a step down faces aft, a step up faces forward
                    P.f(quad, mats[i], out=(0, -1 if w1 < w0 else 1, 0))
                elif i >= n_out:                            # inside the bell: normals face the axis
                    c = sum((v.co for v in quad), Vector()) / 4
                    P.f(quad, mats[i], out=(nx - c.x, 0, NZ - c.z))
                else:
                    P.f(quad, mats[i], away=(nx, ys[i], NZ))
        P.f(rings[0], M["NOZZLE"], out=(0, 1, 0))          # root cap, inside the wing
        P.f(rings[-1], M["NOZZLE_DK"], out=(0, -1, 0))     # throat back wall, faces aft
        # the glowing exhaust disc at the throat and its hot core (thin closed slabs)
        T.loft(glow, lambda y, nx=nx: (ring_pts(nx, NZ, 1.5, 0.84, n=18), (nx, NZ)), [1.43, 1.52], 0)
        T.loft(hot, lambda y, nx=nx: (ring_pts(nx, NZ, 0.8, 0.45, n=14, e=2.2), (nx, NZ)), [1.37, 1.44], 0)
    # splitter between the bells: the fuselage's tail fin
    T.hull(P, T.cbox(AX - 0.55, AX + 0.55, 0.35, 2.8, -0.1, 2.05, 0.22), M["HULL_DK"])


def build_gun(P, M):
    """Turret 5: the nose cannon, a short barrel with a muzzle collar out of the nose tip."""
    def barrel(y, grow=0.0):
        r = (0.55 if y < 26.6 else 0.7) + grow
        return superellipse(AX, 1.25, r, r, r, n=12, e_top=2.0, e_bot=2.0), (AX, 1.25)
    T.loft_rings(P, [(barrel, 23.5, 0.0), (barrel, 26.6, 0.0), (barrel, 26.6, 0.15), (barrel, 27.35, 0.15),
                     (barrel, 27.35, -0.3), (barrel, 27.0, -0.3)], [M["GUN"]] * 6)


def hold_inside(shell, target, d):
    """Pull every shell vertex outside the model back onto it, `d` inside (so the ink shell never
    stands proud of the hull along the panel seams and rib grooves: the D88 crack). Shrinkwrap's
    INSIDE mode keeps vertices `offset` INSIDE the target for a POSITIVE offset (measured on a cube:
    -0.1 leaves them 0.1 outside), so this passes +d; common.outline_shell(inside=d) passes -d."""
    sw = shell.modifiers.new("inside", "SHRINKWRAP")
    sw.target = target
    sw.wrap_method = "NEAREST_SURFACEPOINT"
    sw.wrap_mode = "INSIDE"
    sw.offset = d
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(shell.evaluated_get(dg))
    shell.modifiers.clear()
    old = shell.data
    shell.data = me
    bpy.data.meshes.remove(old)
    me.shade_smooth()


# --- build -------------------------------------------------------------------------------------

def main():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)

    def pal(i, tag="", **kw):
        return common.palette_material(sprite, i, NAME + tag, **kw)

    keys = list(PAL)
    M = {k: n for n, k in enumerate(keys)}
    metal = {"WING": (0.35, 0.45), "WING_PLATE": (0.4, 0.4), "WING_EDGE": (0.35, 0.5), "HULL": (0.35, 0.45),
             "HULL_DK": (0.3, 0.55), "SPINE": (0.45, 0.35), "POD": (0.25, 0.42), "POD_DK": (0.3, 0.5),
             "POD_RAIL": (0.4, 0.4), "NOZZLE": (0.5, 0.45), "NOZZLE_DK": (0.45, 0.5), "NOZZLE_LIP": (0.55, 0.35),
             "GUN": (0.55, 0.4)}
    glows = {"GLOW": 1.6, "HOT": 3.0}
    mats = []
    for k in keys:
        if k in glows:
            mats.append(pal(PAL[k], "_" + k.lower(), metallic=0.0, roughness=0.4, emission_strength=glows[k]))
        else:
            mm, rr = metal[k]
            mats.append(pal(PAL[k], "_" + k.lower(), metallic=mm, roughness=rr))

    body = T.Part(NAME + "_body", smooth_angle=35)
    build_fuselage(body, M)
    build_spine(body, M)
    build_wing(body, M)
    gl = {"GLOW": T.Part(NAME + "_glow"), "HOT": T.Part(NAME + "_hot")}
    build_pods(body, M, gl)
    build_engines(body, M, gl["GLOW"], gl["HOT"])
    build_gun(body, M)

    objs = [T.finish(body, mats, coll),
            T.finish(gl["GLOW"], [mats[M["GLOW"]]], coll),
            T.finish(gl["HOT"], [mats[M["HOT"]]], coll)]
    obj = T.join(objs, NAME)
    shell = common.outline_shell(obj, coll, faces=2500)
    hold_inside(shell, obj, 0.01)
    out = common.export_sprite_model(WT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"built {out.name}: {tris} tris (+ shell {sum(len(p.vertices) - 2 for p in shell.data.polygons)})")


if __name__ == "__main__":
    main()
