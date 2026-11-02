"""The armour ship (tyrian.shp#10 frame 279, a 2x2 enemy, enemy type 560): a 3D version of its sprite.

JE_main's low-armour warning (tyrian2.c L1872-1893, src/sim/game.ts armorWarning) sends it whenever a
player's armour is under 6, every 500 frames: it flies down the screen, takes 4 hits, and drops one
of the armour crates 561-563 (frames 127, 129, 131; +2, +4, +8 armour). Any level can show it. One
frame, no animation, no damaged graphic.

The sprite is authoritative for the plan, the parts and the colours (DECISIONS D52):
- Plan (the mask, outline ring included, the axis on column 12's centre, x = +0.5 px): a red wing
  bar across the top (rows 1-9, 23 px wide, its corners rounded off over rows 1-2 and 9), a 9 px
  red fuselage down the middle (columns 8-16) that tapers over rows 23-27 to a point at the bottom
  (the ship flies down the screen, nose first), two brown pods either side of it under the wing
  (columns 4-7 and 17-20, rows 8-21, their fronts tapering in toward the fuselage over rows 19-22),
  and the brown tops of two engines showing behind the wing (rows 0-1, columns 6-17: a lit round
  top at columns 8-10 and 14-15, so two cylinders lying fore and aft).
- Parts as the shading reads them: the wing a thick slab with a crease along column 6 (the lit
  stripe) and its trailing edge falling away (dark rows 7-8); the fuselage spine a single raised
  ridge over the wing (the bright column 12, rows 5-9), then two ridges with a groove between them
  (columns 11 and 13, rows 10-16); the pods round (a highlight column down each, darker edges) with
  a dark band at row 12 (a groove) and a collar where they leave the wing; no glass anywhere (no
  cockpit pixels), so no canopy is invented.
- Colours: each part takes the palette index the sprite uses for it (mid-tones, not its shading):
  hull 70, wing plates 71, spine 73, nose 69, dark core and recesses 66 / 16, pods 22, collars 24,
  pod grooves 18, engines 20. Satin painted metal (low metallic); baked occlusion as the Talon (D50).

How it is built: the USP Talon's hard-surface toolkit (assets/blender/usp_talon.py, D50): low-poly
cages in sprite px (x = column edge - 12 - 0.5, y = row edge, z up), pchip stations, armour plates
standing proud with chamfered edges, hidden faces culled, Cycles-baked occlusion and roughness, and
an outline shell (common.outline_shell, D51).

    Blender --background --factory-startup --python tyrian10-279.py -- [--no-bake] [--preview png]
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402  (the Talon's hard-surface toolkit, D50)
from usp_talon import Part, Section, cbox, frange, hull, loft, loft_rings, pchip, plate  # noqa: E402

NAME = "tyrian10-279"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
AXIS = 0.5  # the sprite's axis: column 12's centre, half a pixel right of the block's centre

HULL, PLATE, SPINE, NOSE, CORE, DEEP, POD, COLLAR, GROOVE, ENGINE, NOZZLE = range(11)
PAL_OF = {HULL: 70, PLATE: 71, SPINE: 73, NOSE: 69, CORE: 66, DEEP: 16, POD: 22, COLLAR: 24, GROOVE: 18,
          ENGINE: 20, NOZZLE: 16}
TEXTURED = (HULL, PLATE, SPINE, NOSE, CORE, DEEP, POD, COLLAR, GROOVE, ENGINE)
TINT = (1.0, 0.97, 0.9)


def materials(sprite):
    def pal(slot, tag, metallic, roughness):
        return common.palette_material(sprite, PAL_OF[slot], f"armourship_{tag}", metallic=metallic,
                                       roughness=roughness)
    return [
        pal(HULL, "hull", 0.15, 0.42),
        pal(PLATE, "plate", 0.18, 0.38),
        pal(SPINE, "spine", 0.2, 0.34),
        pal(NOSE, "nose", 0.18, 0.38),
        pal(CORE, "core", 0.1, 0.55),
        pal(DEEP, "recess", 0.05, 0.85),
        pal(POD, "pod", 0.3, 0.4),
        pal(COLLAR, "collar", 0.4, 0.34),
        pal(GROOVE, "groove", 0.2, 0.6),
        pal(ENGINE, "engine", 0.35, 0.4),
        pal(NOZZLE, "nozzle", 0.1, 0.8),
    ]


def S2(side, a, b, n):
    """Loop range (a, b) on the right side, or its mirror on the left of an n-point symmetric loop."""
    return (a, b) if side > 0 else (n - b, n - a)


# --- fuselage (rows 0-27): half width with the outline ring, top and keel --------------------------

FUSE_W = pchip([0.5, 2.0, 22.0, 23.0, 24.5, 25.5, 26.5, 27.4, 27.9],
               [3.6, 4.3, 4.3, 4.25, 3.95, 3.2, 2.2, 1.0, 0.25])
FY = [0.5, 3.0, 9.0, 16.0, 21.0, 23.0, 25.0, 26.5, 27.9]
FT = pchip(FY, [2.0, 2.9, 3.1, 3.0, 2.8, 2.4, 1.7, 1.1, 0.5])
FB = pchip(FY, [-1.4, -2.0, -2.2, -2.2, -2.0, -1.7, -1.2, -0.8, -0.2])
FUSE_Y0, FUSE_Y1 = 0.6, 27.9
FUSE_PLATE = 0.22
DECK, SHOULDER, FLANK, CHINE = 0.55, 0.32, 0.45, 0.12


def fuselage_loop(y):
    """0 top centre, 1 deck edge, 2 shoulder, 3 flank foot, 4 chine, 5 keel, then the left side (6-9)."""
    w, t, b = max(0.15, FUSE_W(y) - FUSE_PLATE), FT(y), FB(y)
    h = t - b
    right = [(0.0, t), (DECK * w, t), (w, t - SHOULDER * h), (w, b + FLANK * h), (DECK * w, b + CHINE * h),
             (0.0, b)]
    return right + [(-x, z) for x, z in reversed(right[1:-1])], (0.0, (t + b) / 2)


def deck(y):
    return FT(y) + FUSE_PLATE


# --- wing bar (rows 1-9): a spanwise section lofted fore and aft ---------------------------------

WING_Y0, WING_Y1 = 1.05, 9.75
SPAN = pchip([1.05, 1.5, 2.0, 2.6, 3.0, 8.4, 9.0, 9.4, 9.75], [8.6, 9.6, 10.3, 11.1, 11.35, 11.35, 10.9, 10.2, 9.4])
# Thickness falls away to the leading (top) and trailing (bottom) edges; the trailing edge further.
WZT = pchip([1.05, 1.6, 2.6, 4.0, 6.5, 7.6, 8.6, 9.75], [0.9, 1.65, 2.15, 2.3, 2.3, 2.2, 1.85, 0.9])
WZB = pchip([1.05, 2.0, 4.0, 8.0, 9.75], [-0.1, -0.7, -0.95, -0.9, -0.2])
CREASE = 6.0  # the lit stripe at column 6, from the axis
WING_N = 14


def wing_loop(y, grow=0.0):
    """0 top centre, 1 mid top, 2 crease (column 6), 3 outer top, 4 tip top, 5 tip foot, 6 under, 7 keel
    centre, then the left side mirrored (8-13): a 14-point loop."""
    s, zt, zb = SPAN(y) - 0.18, WZT(y), WZB(y)
    tip_t, tip_b = 0.35 * zt + 0.15, 0.35 * zb
    right = [(0.0, zt), (0.5 * CREASE, zt + 0.05), (CREASE, zt + 0.18), (0.83 * s, 0.62 * zt + 0.1), (s, tip_t),
             (s, tip_b), (0.55 * s, 0.85 * zb)]
    # The keel centre closes it; left side mirrored.
    pts = right + [(0.0, zb)] + [(-x, z) for x, z in reversed(right[1:])]
    return pts, (0.0, (zt + zb) / 2)


# --- pods (rows 8-22) ------------------------------------------------------------------------------

POD_Y0, POD_Y1 = 8.0, 22.2
POD_CX = pchip([8.0, 18.8, 19.8, 20.8, 21.6, 22.2], [6.6, 6.6, 6.35, 5.9, 5.4, 5.1])
POD_RX = pchip([8.0, 18.8, 19.8, 20.8, 21.6, 22.2], [2.55, 2.55, 2.35, 1.85, 1.05, 0.3])
POD_CZ = pchip([8.0, 19.0, 22.2], [-0.15, -0.15, -0.35])
POD_RZ = pchip([8.0, 18.8, 19.8, 20.8, 21.6, 22.2], [2.25, 2.25, 2.05, 1.6, 0.95, 0.3])
POD_N = 16


def pod_loop(side, y, grow=0.0):
    cx, cz = side * POD_CX(y), POD_CZ(y)
    rx, rz = POD_RX(y) + grow, POD_RZ(y) + grow
    pts = []
    for k in range(POD_N):
        a = 2 * math.pi * (k + 0.5) / POD_N
        c, s = math.cos(a), math.sin(a)
        e = 0.8  # a little squarer than an ellipse: a machined canister
        pts.append((cx + rx * math.copysign(abs(c) ** e, c), cz + rz * math.copysign(abs(s) ** e, s)))
    return pts, (cx, cz)


# --- engines (rows 0-6): two cylinders under the wing's leading edge --------------------------------

ENGINES = (-3.0, 3.0)  # centres from the axis (columns 8-10 and 14-15 lit)
ENG_R, ENG_Z = 2.25, 0.75
ENG_Y0, ENG_Y1 = 0.1, 6.0


def build_fuselage(P, D):
    L = fuselage_loop
    n = 10
    ys = [FUSE_Y0] + frange(1.0, 27.5, 0.5) + [27.7, FUSE_Y1]
    loft(P, L, ys, CORE)
    for side in (1, -1):
        def S(a, b, side=side):
            return S2(side, a, b, n)
        # Deck plates either side of the spine (columns 8-10 / 14-16), a seam at row 17, and the
        # shoulders and flanks below them.
        for y0, y1 in ((0.9, 9.25), (9.4, 16.85), (17.05, 22.3)):
            plate(P, L, y0, y1, HULL, *S(0.3, 0.98), d=FUSE_PLATE, c=0.1)
            plate(P, L, y0, y1, HULL, *S(1.04, 2.95), d=FUSE_PLATE, c=0.12)
        plate(P, L, 9.4, 22.3, CORE, *S(3.05, 3.95), d=0.16, c=0.08)
    # The nose: one armour shell all round, rows 22.5-27.5, a polished tip.
    plate(P, L, 22.5, 27.55, NOSE, d=FUSE_PLATE, c=0.14, ch1=False, ystep=0.4)
    sec = Section(L, 27.55)
    tip = [sec.at(k, FUSE_PLATE) for k in range(sec.n)]
    hull(P, tip + [(0.0, FUSE_Y1 + 0.05, (FT(FUSE_Y1) + FB(FUSE_Y1)) / 2)], NOSE)
    # Spine: one ridge over the wing (rows 4.5-10), then two with a groove between (rows 10-17).
    pts = []
    for y, h in ((4.4, 0.35), (5.4, 0.7), (10.2, 0.7)):
        top = deck(y) + h
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.75, top - 0.2), (0.45, top), (0.75, FT(y) - 0.2))]
    hull(D, pts, SPINE)
    for sx in (-1, 1):
        pts = []
        for y, h in ((10.0, 0.62), (16.9, 0.62), (17.5, 0.25)):
            top = deck(y) + h
            pts += [(sx * x, y, z) for x, z in ((0.45, top - 0.15), (0.65, top), (1.35, top - 0.15), (1.5, FT(y) - 0.2),
                                                 (0.4, FT(y) - 0.2))]
        hull(D, pts, SPINE)
    hull(D, cbox(-0.38, 0.38, 10.2, 17.0, FT(13) - 0.3, deck(13) + 0.08, 0.04), DEEP)
    # A keel strake under the fuselage.
    pts = []
    for y in (6.0, 21.0):
        b = FB(y) - 0.1
        pts += [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.9, b + 0.5), (0.6, b - 0.45), (0.25, b - 0.55))]
    hull(D, pts, CORE)


def build_wing(P, D):
    L = wing_loop
    n = WING_N
    ys = [WING_Y0, 1.2, 1.5, 1.8] + frange(2.2, 9.2, 0.5) + [9.45, 9.65, WING_Y1]
    loft(P, L, ys, CORE)
    for side in (1, -1):
        def S(a, b, side=side):
            return S2(side, a, b, n)
        # Top armour: an inner plate from the spine to the crease, an outer one from the crease to
        # the tip, split at the crease (the lit stripe is its edge), and a tip cap.
        plate(P, L, 1.6, 9.2, PLATE, *S(0.12, 1.96), d=0.22, c=0.1)
        plate(P, L, 1.6, 9.2, PLATE, *S(2.04, 3.92), d=0.22, c=0.1)
        plate(P, L, 2.0, 8.8, HULL, *S(4.0, 4.98), d=0.18, c=0.08)
        plate(P, L, 2.0, 8.8, CORE, *S(5.02, 5.96), d=0.14, c=0.08)


def build_pods(P, D):
    for side in (1, -1):
        def L(y, grow=0.0, side=side):
            return pod_loop(side, y, grow)

        # Body with a raised collar where it leaves the wing (rows 9-10) and a groove at row 12.
        rings = [(L, POD_Y0, 0.0), (L, 9.0, 0.0), (L, 9.0, 0.22), (L, 10.2, 0.22), (L, 10.2, 0.0),
                 (L, 12.1, 0.0), (L, 12.1, -0.22), (L, 12.9, -0.22), (L, 12.9, 0.0)]
        rings += [(L, y, 0.0) for y in frange(13.5, 18.5, 1.0)]
        rings += [(L, 18.8, 0.0), (L, 18.8, 0.15), (L, 19.3, 0.15), (L, 19.3, 0.0)]
        rings += [(L, y, 0.0) for y in (19.8, 20.3, 20.8, 21.2, 21.6, 21.9, POD_Y1)]
        mats = []
        for (_, y0, g0), (_, y1, g1) in zip(rings, rings[1:]):
            if y0 == y1:
                mats.append(COLLAR if max(g0, g1) > 0 else GROOVE)
            elif g0 > 0 and g1 > 0:
                mats.append(COLLAR)
            elif g0 < 0 and g1 < 0:
                mats.append(GROOVE)
            else:
                mats.append(POD)
        loft_rings(P, rings, mats)
        # A strap and a clamp joining the pod's inner side to the fuselage (rows 14-17).
        x_in = POD_CX(15) - POD_RX(15) + 0.2
        hull(D, [(side * x, y, z) for x, y, z in cbox(3.7, x_in + 0.6, 14.2, 16.6, -1.2, 0.9, 0.2)], CORE)


def build_engines(P, D):
    n = 16
    for cx in ENGINES:
        rings = []
        prof = [(ENG_Y0 + 0.35, ENG_R - 0.25), (ENG_Y0 + 0.6, ENG_R), (ENG_Y1, ENG_R)]
        for y, r in prof:
            rings.append([P.v((cx + r * math.cos(2 * math.pi * (k + 0.5) / n), y,
                               ENG_Z + 0.9 * r * math.sin(2 * math.pi * (k + 0.5) / n))) for k in range(n)])
        for r0, r1, (y, _) in zip(rings, rings[1:], prof):
            for k in range(n):
                kk = (k + 1) % n
                P.f((r0[k], r0[kk], r1[kk], r1[k]), ENGINE, away=(cx, y + 0.3, ENG_Z))
        # The exhaust face: a rim, then a dark recessed nozzle, a cone in it.
        rim = [P.v((cx + (ENG_R - 0.7) * math.cos(2 * math.pi * (k + 0.5) / n), ENG_Y0 + 0.35,
                    ENG_Z + 0.9 * (ENG_R - 0.7) * math.sin(2 * math.pi * (k + 0.5) / n))) for k in range(n)]
        for k in range(n):
            kk = (k + 1) % n
            P.f((rings[0][k], rings[0][kk], rim[kk], rim[k]), ENGINE, out=(0, -1, 0))
        deep = [P.v((cx + (ENG_R - 0.75) * math.cos(2 * math.pi * (k + 0.5) / n), ENG_Y0 + 1.1,
                     ENG_Z + 0.9 * (ENG_R - 0.75) * math.sin(2 * math.pi * (k + 0.5) / n))) for k in range(n)]
        for k in range(n):
            kk = (k + 1) % n
            mx, mz = (rim[k].co.x + rim[kk].co.x) / 2, (rim[k].co.z + rim[kk].co.z) / 2
            P.f((rim[k], rim[kk], deep[kk], deep[k]), NOZZLE, out=(cx - mx, 0, ENG_Z - mz))  # faces the axis
        cone = P.v((cx, ENG_Y0 + 0.55, ENG_Z))
        for k in range(n):
            kk = (k + 1) % n
            P.f((deep[k], deep[kk], cone), NOZZLE, out=(0, -1, 0))
        # Two bands round the casing.
        for y0 in (1.3, 2.6):
            sec_r = ENG_R + 0.18
            band = []
            for y in (y0, y0 + 0.45):
                band.append([D.v((cx + sec_r * math.cos(2 * math.pi * (k + 0.5) / n), y,
                                  ENG_Z + 0.9 * sec_r * math.sin(2 * math.pi * (k + 0.5) / n))) for k in range(n)])
            for k in range(n):
                kk = (k + 1) % n
                D.f((band[0][k], band[0][kk], band[1][kk], band[1][k]), COLLAR, away=(cx, y0, ENG_Z))
            for ring, o in ((band[0], -1), (band[1], 1)):
                inner = [D.v((cx + ENG_R * 0.98 * math.cos(2 * math.pi * (k + 0.5) / n), ring[0].co.y,
                              ENG_Z + 0.9 * ENG_R * 0.98 * math.sin(2 * math.pi * (k + 0.5) / n))) for k in range(n)]
                for k in range(n):
                    kk = (k + 1) % n
                    D.f((ring[k], ring[kk], inner[kk], inner[k]), COLLAR, out=(0, o, 0))
    # The housing between the engines, under the wing's leading edge.
    hull(D, cbox(-1.6, 1.6, 0.8, 4.0, ENG_Z - 1.2, ENG_Z + 1.3, 0.2), ENGINE)


def build(coll, sprite):
    mats = materials(sprite)
    fus = Part("armourship_fuselage", smooth_angle=30)
    det = Part("armourship_details", smooth_angle=35)
    build_fuselage(fus, det)
    wing = Part("armourship_wing", smooth_angle=30)
    build_wing(wing, det)
    pods = Part("armourship_pods", smooth_angle=40)
    build_pods(pods, det)
    eng = Part("armourship_engines", smooth_angle=40)
    build_engines(eng, det)
    return [T.finish(p, mats, coll) for p in (fus, wing, pods, eng, det)]


def bake_maps(obj, out_dir, size=1024, samples=96):
    """The Talon's bake (usp_talon.bake_maps, D50/D53) with this model's tint and textured slots."""
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "armourship")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    objs = build(coll, sprite)
    obj = T.join(objs, NAME)
    # The sprite's axis is column 12's centre: half a pixel right of the 24 px block's centre.
    obj.data.transform(Matrix.Translation((AXIS * PX, 0, 0)))
    T.cull_hidden(obj)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = ROOT / "assets" / "blender" / "textures" / NAME / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(obj, bake_dir, size=512, samples=64)
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.016, faces=1500, smooth=16)
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=2)


if __name__ == "__main__":
    main()
