"""UNDERDELI's chin hatch (newsh9.shp frames 123 / 241 / 279): final build.

What the sprite shows (rows/columns of the 24x28 cell; the axis on column 12's centre):
a purple-grey armoured block 17 px wide (columns 4-20) and 21 px long (rows 6-26), its back corners
rounded off over row 6 and its front ones over rows 25-26, two little lugs under its front edge
(row 27, columns 7 and 17). Two lit rails run its length at columns 6-7 / 17-18 between darker
shoulders (columns 4-5 / 19-20); between them a flat lid (rows 7-12, its front lip lit at row 12, a
dark groove at row 13), a bright transverse band (rows 14-17: a hinge barrel, split at the centre
by two dark gaps either side of a narrow lit knuckle, columns 11-13), and the doors (rows 18-24)
with a centre rib (column 12 lit, 11 and 13 dark grooves) running to the rounded front edge.
In UNDERDELI (4.7) it spawns with the boss and keeps its steering, on top of newsh9-87 (the boss's
bottom centre, 1 px left and 1 px down): the boss's chin hatch, armour 255. One picture in three
frames: the light walks over it (frame 241 the lid and upper rails bright and the doors dark, 279
the barrel brightest), so one model whose parts change palette index per frame (D17).

Built with the Talon's hard-surface toolkit (usp_talon, D50): a lofted housing with chamfered
shoulders, rails, a lid plate, a hinge barrel, door plates and a rib, in sprite px
(x = column edge - 12, y = row edge, z up), Cycles AO/roughness bake (no projection), outline shell.

    Blender --background --factory-startup --python newsh9-123.py -- [--no-bake] [--out x.glb]  (no --out: public/models + spriteModels)
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve()
ROOT = next(p for p in HERE.parents if (p / "package.json").exists())
sys.path[:0] = [str(ROOT / "assets" / "blender"), str(ROOT / "tools")]
import common  # noqa: E402
import sprite_data  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, frange, hull, pchip  # noqa: E402

NAME = "newsh9-123"
PX = 1 / 12
AXIS = 0.5  # column 12's centre, half a pixel right of the cell's centre
MODEL = f"enemies/{NAME}"

HOUSE, LID, RAIL_UP, RAIL_LO, BARREL, DOOR, RIB, GROOVE, LUG = range(9)
# (palette index on frame 123, {other frame: index}) from each region's median in the sprite.
PAL = {
    HOUSE: (86, {279: 87}),
    LID: (86, {241: 89, 279: 87}),
    RAIL_UP: (88, {241: 91, 279: 89}),
    RAIL_LO: (88, {241: 85, 279: 86}),
    BARREL: (90, {279: 92}),
    DOOR: (88, {241: 85, 279: 86}),
    RIB: (88, {241: 86, 279: 86}),
    GROOVE: (84, {241: 83}),
    LUG: (85, {241: 82, 279: 82}),
}
TAGS = ["house", "lid", "railup", "raillo", "barrel", "door", "rib", "groove", "lug"]
TINT = (1.0, 0.98, 1.0)


def load_sprite():
    """The catalogue doesn't list this piece (no reference/models/newsh9-123), so its three frames are
    read from the game data (tools/sprite_data.py)."""
    return sprite_data.load(ROOT, NAME, "newsh9.shp", [123, 241, 279])


def materials(sprite):
    out = []
    for slot, tag in enumerate(TAGS):
        idx, frames = PAL[slot]
        metal, rough = (0.3, 0.6) if slot == GROOVE else (0.3, 0.46)
        out.append(common.palette_material(sprite, idx, f"{NAME}_{tag}", metallic=metal, roughness=rough,
                                           frames=frames))
    return out


# --- housing ---------------------------------------------------------------------------------------
# Plan half width by row edge (the inner mask: columns 5-19 on row 6, 4-20 rows 7-24, 5-19 row 25,
# 6-18 row 26), rounded corners; deck height falls away over the back and front edges.
Y0, Y1 = 6.0, 26.05
HW = pchip([6.0, 6.35, 6.8, 7.4, 8.0, 22.6, 23.1, 23.6, 24.8, 25.4, 25.8, 26.05],
           [6.6, 7.4, 8.0, 8.4, 8.5, 8.5, 7.95, 7.55, 7.45, 7.1, 6.4, 5.6])
HC = 5.2  # deck height: above newsh9-87's top (4.68 px), which it is drawn over
DZ = pchip([6.0, 6.5, 7.2, 8.0, 23.6, 24.6, 25.4, 26.05], [2.7, 4.0, 4.85, 5.2, 5.2, 4.7, 3.7, 2.2])
WALL = 0.25  # the wall leans in this much toward its foot


def house_loop(y):
    w, t = HW(y), DZ(y)
    s = t / HC
    right = [(0.0, t), (min(4.4, 0.55 * w), t), (min(6.7, w - 0.9), t), (w - 0.55, t - 0.45 * s), (w, t - 1.35 * s), (w, 0.55),
             (w - WALL, 0.0)]
    pts = right + [(0.0, 0.0)] + [(-x, z) for x, z in reversed(right[1:])]
    return pts, (0.0, t / 2)


def build_house(P, D):
    ys = [Y0, 6.12, 6.35, 6.6, 6.9, 7.2, 7.6, 8.0] + frange(8.8, 22.4, 1.7) + [22.6, 22.85, 23.1, 23.35, 23.6, 24.0,
                                                                                24.4, 24.8, 25.1, 25.4, 25.6, 25.8, 25.95, Y1]
    T.loft(P, house_loop, ys, HOUSE)
    # A belt line round the walls (a shallow step at z 1.4), and a rear access panel.
    for sx in (-1, 1):
        hull(D, [(sx * x, y, z) for x, y, z in cbox(8.2, 8.62, 8.5, 22.0, 1.6, 2.0, 0.08)], GROOVE)
        # Three bolt heads on each wall above the belt.
        for y in (10.0, 15.5, 21.0):
            hull(D, [(sx * x, yy, z) for x, yy, z in cbox(8.25, 8.68, y - 0.35, y + 0.35, 2.7, 3.5, 0.12)], RAIL_LO)
    # Rear face (y = 6): a recessed hatch and two vents.
    hull(D, cbox(-4.0, 4.0, 6.05, 6.5, 0.9, 2.9, 0.15), GROOVE)
    for sx in (-1, 1):
        hull(D, [(sx * x, y, z) for x, y, z in cbox(4.8, 6.0, 6.25, 6.6, 1.2, 2.6, 0.12)], GROOVE)


def build_rails(P):
    """Two rails along columns 6-7 / 17-18 (x 4.5-6.6), their crests lit; split at the barrel."""
    for sx in (-1, 1):
        for y0, y1, mat in ((7.3, 14.4, RAIL_UP), (17.6, 24.9, RAIL_LO)):
            pts = []
            for y, h in ((y0, 0.35), (y0 + 0.45, 0.85), (y1 - 0.5, 0.85), (y1, 0.3)):
                top = HC + h
                for x, z in ((4.45, HC - 0.5), (4.5, top - 0.3), (4.95, top), (5.95, top), (6.55, top - 0.35),
                             (6.65, HC - 0.6)):
                    pts.append((sx * x, y, z))
            hull(P, pts, mat)


def build_lid(P, D):
    """The lid between the rails (rows 7-12): a plate 0.3 proud, chamfered, its front lip at row 12.6,
    then the dark groove of row 13 before the barrel."""
    hull(P, cbox(-4.25, 4.25, 7.25, 12.55, HC - 0.3, HC + 0.3, 0.3, 0.2), LID)
    # Two panel seams across the lid and a small recessed grip at its back.
    for y in (9.9,):
        hull(D, cbox(-3.9, 3.9, y - 0.08, y + 0.08, HC + 0.22, HC + 0.34, 0.02), GROOVE)
    hull(D, cbox(-4.4, 4.4, 12.6, 14.2, HC - 0.6, HC - 0.05, 0.1), GROOVE)


BAR_Y, BAR_R = 16.0, 1.95
BAR_Z = HC + 0.05


def barrel_ring(x, r, n=20):
    return [(x, BAR_Y + r * math.cos(2 * math.pi * k / n), BAR_Z + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def tube(P, x0, x1, r, mat, ch=0.18, n=20):
    """A cylinder along x with chamfered ends (a hinge knuckle)."""
    rings = [barrel_ring(x0, r - ch, n), barrel_ring(x0 + ch, r, n), barrel_ring(x1 - ch, r, n), barrel_ring(x1, r - ch, n)]
    vs = [[P.v(p) for p in ring] for ring in rings]
    for a, b in zip(vs, vs[1:]):
        for k in range(n):
            kk = (k + 1) % n
            P.f((a[k], a[kk], b[kk], b[k]), mat, away=((a[k].co.x + b[k].co.x) / 2, BAR_Y, BAR_Z))
    P.f(vs[0], mat, out=(-1, 0, 0))
    P.f(vs[-1], mat, out=(1, 0, 0))


def build_barrel(P, D):
    """The hinge barrel across rows 14-17: two long knuckles and a narrow centre one, with gaps."""
    for sx in (-1, 1):
        a, b = (0.78, 7.7)
        tube(P, sx * a if sx > 0 else -b, sx * b if sx > 0 else -a, BAR_R, BARREL)
        # End collars (a smaller turned boss) at each end.
        tube(D, 7.6 if sx > 0 else -8.1, 8.1 if sx > 0 else -7.6, BAR_R - 0.5, HOUSE)
    tube(P, -0.48, 0.48, BAR_R - 0.05, BARREL, ch=0.12)
    # The pin through the gaps (a dark axle) and a saddle under the barrel.
    tube(D, -0.9, 0.9, 0.7, GROOVE, ch=0.1)
    hull(D, cbox(-7.4, 7.4, 14.3, 17.7, HC - 1.0, BAR_Z - 0.4, 0.3), GROOVE)


def build_doors(P, D):
    """The two doors (rows 18-24) either side of the centre rib, their front edges rolled down."""
    for sx in (-1, 1):
        pts = []
        for y, z in ((18.15, HC + 0.05), (18.5, HC + 0.3), (23.3, HC + 0.3), (24.1, HC - 0.05), (24.6, HC - 0.65)):
            for x in (0.72, 4.25):
                pts += [(sx * x, y, z), (sx * x, y, HC - 0.8)]
            pts += [(sx * (0.72 + 0.12), y, z + 0.0)]
        hull(P, pts, DOOR)
        # A recessed pull slot near each door's front.
        hull(D, [(sx * x, y, z) for x, y, z in cbox(1.6, 3.4, 21.6, 22.15, HC + 0.18, HC + 0.36, 0.08)], GROOVE)
    # The centre rib (astragal): a rounded bar standing over the door seam, rows 18-25.
    pts = []
    for y, h in ((17.9, 0.35), (18.4, 0.62), (23.7, 0.62), (24.6, -0.2)):
        for x, dz in ((0.48, -0.25), (0.28, 0.0), (0.0, 0.05)):
            pts += [(x, y, HC + h + dz), (-x, y, HC + h + dz)]
        pts += [(0.5, y, HC - 0.8), (-0.5, y, HC - 0.8)]
    hull(P, pts, RIB)
    # The dark seam floor either side of the rib (columns 11 and 13).
    hull(D, cbox(-0.85, 0.85, 18.0, 24.4, HC - 0.5, HC + 0.12, 0.05), GROOVE)


def build_lugs(P):
    """Two latch lugs under the front edge (row 27, columns 7 and 17): rounded tongues."""
    for sx in (-1, 1):
        cx = sx * 5.0
        pts = []
        for y, w, z0, z1 in ((24.8, 0.48, 0.9, 2.6), (26.2, 0.48, 1.0, 2.3), (26.7, 0.4, 1.15, 2.0), (26.85, 0.28, 1.3, 1.75)):
            pts += [(cx - w, y, z0), (cx + w, y, z0), (cx - w, y, z1), (cx + w, y, z1)]
        hull(P, pts, LUG)


def build(coll, sprite):
    mats = materials(sprite)
    house = Part("hatch_house", smooth_angle=35)
    det = Part("hatch_detail", smooth_angle=35)
    build_house(house, det)
    rails = Part("hatch_rails", smooth_angle=35)
    build_rails(rails)
    lid = Part("hatch_lid", smooth_angle=30)
    build_lid(lid, det)
    bar = Part("hatch_barrel", smooth_angle=40)
    build_barrel(bar, det)
    doors = Part("hatch_doors", smooth_angle=35)
    build_doors(doors, det)
    lugs = Part("hatch_lugs", smooth_angle=40)
    build_lugs(lugs)
    return [T.finish(p, mats, coll) for p in (house, rails, lid, bar, doors, lugs, det)]


def bake_maps(obj, out_dir, size=512, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, tuple(range(len(TAGS)))
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "hatch123")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = load_sprite()
    coll = common.reset_collection(NAME)
    obj = T.join(build(coll, sprite), NAME)
    obj.data.transform(Matrix.Translation((AXIS * PX, 0, 0)))
    T.cull_hidden(obj)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {sum(len(p.vertices) - 2 for p in obj.data.polygons)} tris")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        bake_maps(obj, tempfile.mkdtemp(prefix="hatch123_"))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.014, faces=1500, smooth=12, islands="outer")
    assert shell.type == "MESH" and len(shell.data.polygons) > 0, "outline shell has no mesh"
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
    else:
        common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
