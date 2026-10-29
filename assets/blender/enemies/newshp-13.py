"""Brown ground turret (newshp.shp frames 13-93 and newsh2.shp 39-131): a 3D version of its sprites.

Seen in episode 1 (levels 1.3, 1.6) and 3. A grey base plate, longer than it is wide, with two
prongs reaching forward either side of the gun and a red lamp at its back; on it a brown turret
block with a long gun (grey sleeve, brown muzzle). The whole turret turns to aim, in eight
directions, so each direction is its own model, exporting the frames that show it (newsh2.shp
repeats newshp.shp's eight directions):

    newshp-13 up-left, -f2 up, -f3 up-right, -f4 left, -f5 right, -f6 down-left, -f7 down,
    -f8 down-right.

The turret is built once pointing up (+Y) about its turret block, then turned and placed on each
direction's turret block.

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
#  hull offset in px along the turret's own (right, forward) axes). The diagonal and side frames
#  draw the hull a little off the turret's axis, so each direction moves the hull to its sprite.
DIRECTIONS = [
    (NAME, 135, (13.75, 13.25), {("newshp.shp", 13)}, (-1.5, 1.25)),
    (f"{NAME}-f2", 90, (11.5, 13.5), {("newshp.shp", 15), ("newsh2.shp", 45)}, (-0.5, -0.5)),
    (f"{NAME}-f3", 45, (11.25, 13.75), {("newshp.shp", 17), ("newsh2.shp", 93)}, (1.0, 0.25)),
    (f"{NAME}-f4", 180, (15.0, 12.0), {("newshp.shp", 51), ("newsh2.shp", 39)}, (0.0, 0.0)),
    (f"{NAME}-f5", 0, (9.5, 11.5), {("newshp.shp", 55), ("newsh2.shp", 43)}, (0.5, 0.5)),
    (f"{NAME}-f6", -135, (13.75, 11.5), {("newshp.shp", 89), ("newsh2.shp", 129)}, (-1.0, 1.5)),
    (f"{NAME}-f7", -90, (11.5, 11.75), {("newshp.shp", 91), ("newsh2.shp", 41)}, (0.5, 1.5)),
    (f"{NAME}-f8", -45, (10.5, 11.25), {("newshp.shp", 93), ("newsh2.shp", 131)}, (0.5, 2.25)),
]

# Heights in sprite px.
POD_WALL, POD_TOP = 3.2, 4.0      # track pods: wall height, top of their bevel
DECK_WALL, DECK_TOP = 2.3, 2.8    # centre deck between the pods
PRONG_WALL, PRONG_TOP = 2.4, 3.1  # forward prongs
DOME_Z0, DOME_TOP = 2.6, 7.2      # turret: skirt bottom, dome top
GUN_Z = 4.7                       # gun axis


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


def armour(bm, outline, wall, top, bevel, side, lid, off=(0.0, 0.0)):
    """A hard armour block: `outline` (CCW, px) walls up to `wall` px, then a chamfer `bevel` px
    in to a flat lid at `top` px."""
    ox, oy = off
    pts = [(x + ox, y + oy) for x, y in outline]
    rings = [[(x * PX, y * PX, z * PX) for x, y in r] for r, z in
             ((pts, 0.0), (pts, wall), (inset(pts, bevel), top))]
    n = len(bm.faces)
    lib.ring_loft(bm, rings, side, cap_start=False, cap_end=True)
    k = len(pts)
    for i, f in enumerate(lib._faces_since(bm, n)):
        if i >= k:  # the chamfer and the lid
            f.material_index = lid


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


def turret(bm, m, hull=(0.0, 0.0)):
    """The turret pointing up (+Y), its dome centred on the origin; the hull is moved by `hull`
    px (right, forward). Units are pixels / 12."""
    # Track pods down both sides: tall armoured boxes, chamfered front-outer and back-outer
    # corners, their rear ends turning in towards the notch that holds the lamp.
    pod = [(1.5, -5.5), (4.5, -5.5), (5.5, -4.5), (5.5, 1.7), (4.7, 2.5), (2.9, 2.5), (2.9, -2.8), (1.5, -4.1)]
    for o in (pod, mirror(pod)):
        armour(bm, o, POD_WALL, POD_TOP, 0.6, m[4], m[6], hull)
    # The centre deck between them, lower.
    armour(bm, [(-2.9, -3.6), (2.9, -3.6), (2.9, 2.5), (-2.9, 2.5)], DECK_WALL, DECK_TOP, 0.4, m[4], m[5], hull)
    # Prongs reaching forward either side of the gun, chamfered at the front.
    prong = [(1.5, 2.3), (3.6, 2.3), (3.6, 5.6), (2.8, 6.5), (1.5, 6.5)]
    for o in (prong, mirror(prong)):
        armour(bm, o, PRONG_WALL, PRONG_TOP, 0.45, m[5], m[7], hull)
    # The rear notch: a dark housing low between the pods' ends, the red lamp glowing on it.
    armour(bm, [(-1.5, -5.2), (1.5, -5.2), (1.5, -3.4), (-1.5, -3.4)], 1.8, 2.2, 0.3, m[2], m[2], hull)
    armour(bm, [(-0.9, -4.7), (0.9, -4.7), (0.9, -3.5), (-0.9, -3.5)], 2.6, 3.0, 0.25, m[116], m[116], hull)

    # Turret: a dark skirt ring, then a round bronze dome (rounded-rect sections, smooth).
    ring = [[(x * PX, y * PX, z * PX) for x, y in rrect(2.8, 2.4, 1.2, 0.2, 3)] for z in (DOME_Z0, 3.5)]
    lib.ring_loft(bm, ring, m[162], cap_start=False, cap_end=False)
    n = len(bm.faces)
    secs = [(3.4, 2.7, 2.3, 1.2), (5.3, 2.6, 2.25, 1.3), (6.5, 2.1, 1.85, 1.2), (7.05, 1.3, 1.15, 0.9)]
    rings = [[(x * PX, y * PX, z * PX) for x, y in rrect(hw, hh, r, 0.3, 3)] for z, hw, hh, r in secs]
    rings.append([(0.0, 0.3 * PX, DOME_TOP * PX)])
    lib.ring_loft(bm, rings, m[23], cap_start=False, cap_end=False)
    lib.set_smooth(bm, n)
    # The gun: a mantlet on the dome's front, a grey round sleeve, a dark neck, a brown muzzle.
    g6, g8, g2 = m.add(6, key="mantlet"), m[8], m.add(2, key="neck")
    armour(bm, [(-1.1, 1.7), (1.1, 1.7), (1.1, 3.1), (-1.1, 3.1)], 5.4, 5.9, 0.3, g6, g6)
    lib.tube(bm, (0, 2.6 * PX, GUN_Z * PX), (0, 8.2 * PX, GUN_Z * PX), 0.75 * PX, sides=8, mat=g8)
    lib.tube(bm, (0, 8.0 * PX, GUN_Z * PX), (0, 9.2 * PX, GUN_Z * PX), 0.5 * PX, sides=8, mat=g2, caps=False)
    lib.tube(bm, (0, 9.0 * PX, GUN_Z * PX), (0, 11.7 * PX, GUN_Z * PX), 0.9 * PX, sides=8, mat=m[24], radius1=0.8 * PX)


def build(sprite):
    g = lib.Grid(24, 28)
    m = lib.Mats(sprite, NAME, metallic=0.45, roughness=0.45)
    m.add(116, emission_strength=3.0)
    models = []
    for model, angle, (pc, pr), frames, hull in DIRECTIONS:
        coll = common.reset_collection(model)
        bm = bmesh.new()
        turret(bm, m, hull)
        bmesh.ops.transform(bm, matrix=Matrix.Translation((g.x(pc), g.y(pr), 0))
                            @ Matrix.Rotation(math.radians(angle - 90), 4, "Z"), verts=bm.verts)
        obj = lib.to_object(model, bm, m.list, coll)
        models.append((model, [obj], lib.subset(sprite, frames)))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
