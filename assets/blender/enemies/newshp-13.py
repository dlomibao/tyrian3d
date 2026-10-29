"""Brown ground turret (newshp.shp frames 13-93 and newsh2.shp 39-131): a 3D version of its sprites.

Seen in episode 1 (levels 1.3, 1.6) and 3. Shaped after the concept
(assets/blender/features/concepts/newshp-13.jpg) and textured from it (texture_bake.py): a small
tank whose hull has an armoured pod down each side (tall chamfered front and rear fenders, a lower
track cover with pipes between them, a ribbed tread strip outside), a low centre deck, and a red
lamp in a dark housing in the notch between the rear fenders; on it a bronze helmet dome on a dark
ring with a mantlet and a long gun (grey barrel, bronze collar, a thin rod beside it, a chunky
eight-sided bronze muzzle). The whole turret turns to aim, in eight directions, so each direction
is its own model, exporting the frames that show it (newsh2.shp repeats newshp.shp's eight
directions):

    newshp-13 up-left, -f2 up, -f3 up-right, -f4 left, -f5 right, -f6 down-left, -f7 down,
    -f8 down-right.

The hull and turret are built once pointing up (+Y), the dome on the origin; each direction moves
(and for the up-left frame turns) the hull under the dome, then turns and places the lot.

Run: blender --background --python assets/blender/enemies/newshp-13.py [-- --preview out.png]
(-- previews every direction: <out>.png and newshp-13-f<n>.png beside it).
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b067 as lib  # noqa: E402
from lib_b067 import PX, common  # noqa: E402

NAME = "newshp-13"

# (model, aim angle in degrees from +X, turret pivot in pixel-edge coords (col, row), frames,
#  hull offset in px along the turret's own (right, forward) axes[, hull yaw in degrees]). The
#  diagonal and side frames draw the hull a little off the turret's axis, so each direction moves
#  the hull to its sprite; the up-left frame (the one the concept redraws) also turns the hull a
#  little clockwise of the gun, as the concept and sprite draw it.
DIRECTIONS = [
    (NAME, 135, (13.47, 12.54), {("newshp.shp", 13)}, (-1.2, -0.4), -12),
    (f"{NAME}-f2", 90, (11.5, 13.5), {("newshp.shp", 15), ("newsh2.shp", 45)}, (-0.5, -0.5)),
    (f"{NAME}-f3", 45, (11.25, 13.75), {("newshp.shp", 17), ("newsh2.shp", 93)}, (1.0, 0.25)),
    (f"{NAME}-f4", 180, (15.0, 12.0), {("newshp.shp", 51), ("newsh2.shp", 39)}, (0.0, 0.0)),
    (f"{NAME}-f5", 0, (9.5, 11.5), {("newshp.shp", 55), ("newsh2.shp", 43)}, (0.5, 0.5)),
    (f"{NAME}-f6", -135, (13.75, 11.5), {("newshp.shp", 89), ("newsh2.shp", 129)}, (-1.0, 1.5)),
    (f"{NAME}-f7", -90, (11.5, 11.75), {("newshp.shp", 91), ("newsh2.shp", 41)}, (0.5, 1.5)),
    (f"{NAME}-f8", -45, (10.5, 11.25), {("newshp.shp", 93), ("newsh2.shp", 131)}, (0.5, 2.25)),
]

# Heights in sprite px.
TRACK_WALL, TRACK_TOP = 2.0, 2.3    # tread strips along the outer sides
MID_WALL, MID_TOP = 2.9, 3.3        # track covers between the fenders
FENDER_WALL, FENDER_TOP = 3.6, 4.3  # front and rear fender blocks: the tallest hull parts
DECK_WALL, DECK_TOP = 2.4, 2.8      # centre deck between the pods
DOME_Z0, DOME_TOP = 2.6, 7.4        # turret: skirt bottom, dome top
GUN_Z = 4.8                         # gun axis

# Hull plan (px, hull frame: +Y forward, centred between the pods), traced from the concept.
POD_IN, POD_OUT = 1.6, 5.2          # pods' inner and outer sides
HULL_FRONT, HULL_BACK = 6.3, -5.8
FENDER_F = 3.0                      # front fender: from here to the front
FENDER_R = -1.7                     # rear fender: from here to the back
DECK_BACK = -1.9                    # the deck stops here; the rear notch lies behind it


def inset(outline, d):
    """`outline` (CCW, px) with every edge moved `d` px inward."""
    n = len(outline)
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = outline[i], outline[(i + 1) % n]
        ln = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / ln, (x1 - x0) / ln  # inward (left) normal of a CCW edge
        lines.append(((x0 + nx * d, y0 + ny * d), (x1 - x0, y1 - y0)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-9:
            out.append(q)
            continue
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    return out


def armour(bm, outline, wall, top, bevel, side, lid, z0=0.0):
    """A hard armour block: `outline` (CCW, px) walls from `z0` up to `wall` px, then a chamfer
    `bevel` px in to a flat lid at `top` px."""
    rings = [[(x * PX, y * PX, z * PX) for x, y in r] for r, z in
             ((outline, z0), (outline, wall), (inset(outline, bevel), top))]
    n = len(bm.faces)
    lib.ring_loft(bm, rings, side, cap_start=False, cap_end=True)
    k = len(outline)
    for i, f in enumerate(lib._faces_since(bm, n)):
        if i >= k:  # the chamfer and the lid
            f.material_index = lid


def box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def rrect(hw, hh, r, cy=0.0, segs=3):
    """A rounded rectangle (CCW, px), half sizes hw x hh, corner radius r."""
    pts = []
    for cx_, cy_, a0 in ((hw - r, hh - r, 0), (-hw + r, hh - r, 90), (-hw + r, -hh + r, 180), (hw - r, -hh + r, 270)):
        for k in range(segs):
            a = math.radians(a0 + 90 * k / (segs - 1))
            pts.append((cx_ + r * math.cos(a), cy + cy_ + r * math.sin(a)))
    return pts


def mirror(outline):
    return [(-x, y) for x, y in reversed(outline)]


def hull(bm, m):
    """The tank hull in its own frame (+Y forward, px / 12): an armoured pod down each side (tall
    front and rear fenders, a lower track cover between them, a ribbed tread strip outside), a low
    centre deck, and at the back a notch between the rear fenders holding the red lamp."""
    for s in (1, -1):
        def side(o):
            return o if s > 0 else mirror(o)
        # Tread strip along the outer side, with grouser ribs across it.
        armour(bm, side(box(POD_OUT - 0.6, HULL_BACK + 0.5, POD_OUT + 0.1, HULL_FRONT - 0.6)),
               TRACK_WALL, TRACK_TOP, 0.15, m[2], m[3])
        y = HULL_BACK + 0.8
        while y < HULL_FRONT - 0.8:
            armour(bm, side(box(POD_OUT - 0.2, y, POD_OUT + 0.15, y + 0.4)), TRACK_TOP + 0.1, TRACK_TOP + 0.2,
                   0.05, m[3], m[4], z0=0.6)
            y += 0.9
        # Front fender: chamfered front-outer corner.
        armour(bm, side([(POD_IN, FENDER_F), (POD_OUT - 0.5, FENDER_F), (POD_OUT - 0.5, HULL_FRONT - 1.0),
                         (POD_OUT - 1.5, HULL_FRONT), (POD_IN, HULL_FRONT)]),
               FENDER_WALL, FENDER_TOP, 0.45, m[4], m[6])
        # Track cover between the fenders, lower, with two pipes running along it.
        armour(bm, side(box(POD_IN + 0.3, FENDER_R, POD_OUT - 0.4, FENDER_F)), MID_WALL, MID_TOP, 0.3, m[4], m[5])
        for px_ in (POD_IN + 1.0, POD_IN + 1.7):
            x = px_ * s
            lib.tube(bm, (x * PX, (FENDER_R + 0.1) * PX, (MID_TOP + 0.2) * PX),
                     (x * PX, (FENDER_F - 0.1) * PX, (MID_TOP + 0.2) * PX), 0.28 * PX, sides=6, mat=m[7])
        # Rear fender: chamfered back-outer corner, and a short inner corner by the lamp.
        armour(bm, side([(POD_IN, HULL_BACK + 0.4), (POD_IN + 0.4, HULL_BACK), (POD_OUT - 1.4, HULL_BACK),
                         (POD_OUT - 0.4, HULL_BACK + 1.0), (POD_OUT - 0.4, FENDER_R), (POD_IN, FENDER_R)]),
               FENDER_WALL, FENDER_TOP, 0.45, m[4], m[6])
        # Vent slots cut into the front fender's top.
        for k in range(3):
            y0 = FENDER_F + 0.6 + k * 0.6
            armour(bm, side(box(POD_IN + 0.8, y0, POD_IN + 2.0, y0 + 0.3)), FENDER_TOP - 0.25, FENDER_TOP + 0.02,
                   0.0, m[2], m[1], z0=FENDER_TOP - 0.4)
    # Centre deck.
    armour(bm, box(-POD_IN - 0.1, DECK_BACK, POD_IN + 0.1, HULL_FRONT - 0.3), DECK_WALL, DECK_TOP, 0.3, m[4], m[5])
    # Rear notch: a dark housing low between the rear fenders, the red lamp glowing in it.
    armour(bm, box(-POD_IN - 0.1, HULL_BACK + 0.6, POD_IN + 0.1, DECK_BACK + 0.1), 1.6, 1.9, 0.2, m[2], m[3])
    armour(bm, box(-0.8, -4.1, 0.8, -2.8), 2.2, 2.45, 0.2, m[2], m[1])
    armour(bm, box(-0.4, -3.75, 0.4, -3.05), 2.6, 2.75, 0.12, m[116], m[116], z0=2.2)


def turret(bm, m):
    """The turret pointing up (+Y), its dome centred on the origin (px / 12)."""
    # A dark skirt ring, then a round bronze helmet dome, longer than it is wide.
    ring = [[(x * PX, y * PX, z * PX) for x, y in rrect(2.25, 2.65, 1.5, 0.0, 4)] for z in (DOME_Z0, 3.4)]
    lib.ring_loft(bm, ring, m[162], cap_start=False, cap_end=False)
    n = len(bm.faces)
    secs = [(3.3, 2.15, 2.55, 1.6), (4.8, 2.15, 2.55, 1.65), (6.0, 1.8, 2.2, 1.45), (6.9, 1.15, 1.45, 0.95)]
    rings = [[(x * PX, y * PX, z * PX) for x, y in rrect(hw, hh, r, -0.1, 4)] for z, hw, hh, r in secs]
    rings.append([(0.0, -0.1 * PX, DOME_TOP * PX)])
    lib.ring_loft(bm, rings, m[24], cap_start=False, cap_end=False)
    lib.set_smooth(bm, n)
    # The gun: a mantlet block on the dome's front, a grey round barrel with a bronze collar and
    # a thin rod beside it, a dark neck, and a chunky eight-sided bronze muzzle.
    g6, g2 = m.add(6, key="mantlet"), m.add(2, key="neck")
    armour(bm, [(-1.1, 1.9), (1.1, 1.9), (1.1, 4.3), (0.7, 4.8), (-0.7, 4.8), (-1.1, 4.3)], 5.4, 5.9, 0.3, g6, g6,
           z0=2.6)
    lib.tube(bm, (0, 4.4 * PX, GUN_Z * PX), (0, 8.9 * PX, GUN_Z * PX), 0.55 * PX, sides=8, mat=m[8])
    lib.tube(bm, (0, 5.0 * PX, GUN_Z * PX), (0, 6.0 * PX, GUN_Z * PX), 0.7 * PX, sides=8, mat=m[24])
    lib.tube(bm, (-0.85 * PX, 4.6 * PX, (GUN_Z - 0.1) * PX), (-0.85 * PX, 8.7 * PX, (GUN_Z - 0.1) * PX),
             0.22 * PX, sides=6, mat=m[4])
    lib.tube(bm, (0, 8.4 * PX, GUN_Z * PX), (0, 9.0 * PX, GUN_Z * PX), 0.8 * PX, sides=8, mat=g2)
    lib.tube(bm, (0, 8.9 * PX, GUN_Z * PX), (0, 10.7 * PX, GUN_Z * PX), 1.1 * PX, sides=8, mat=m[24])
    lib.tube(bm, (0, 10.6 * PX, GUN_Z * PX), (0, 11.0 * PX, GUN_Z * PX), 1.1 * PX, sides=8, mat=m[22],
             radius1=0.8 * PX)


def build(sprite):
    g = lib.Grid(24, 28)
    m = lib.Mats(sprite, NAME, metallic=0.45, roughness=0.45)
    m.add(116, emission_strength=3.0)
    m.add(24, metallic=0.6, roughness=0.35)
    models = []
    for model, angle, (pc, pr), frames, (hx, hy), *yaw in DIRECTIONS:
        coll = common.reset_collection(model)
        bm = bmesh.new()
        hull(bm, m)
        bmesh.ops.transform(bm, matrix=Matrix.Translation((hx * PX, hy * PX, 0))
                            @ Matrix.Rotation(math.radians(yaw[0] if yaw else 0), 4, "Z"), verts=bm.verts)
        turret(bm, m)
        bmesh.ops.transform(bm, matrix=Matrix.Translation((g.x(pc), g.y(pr), 0))
                            @ Matrix.Rotation(math.radians(angle - 90), 4, "Z"), verts=bm.verts)
        obj = lib.to_object(model, bm, m.list, coll)
        models.append((model, [obj], lib.subset(sprite, frames)))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
