"""Spiked mine (newsh3.shp frame 246): a 3D version of its sprite.

Seen in episode 4 (levels 4, 10, 22, 36, 50). A silver ball, about as tall as it is wide, whose top
is a rounded ring (its crest 6.5 px up) around a dark pit 2.5 px deep; two red rods lie in the pit
with their tops at rim height, joined by a bridge at the top, with a steel rib between them. Four
long ridged spikes stand out from its flanks (up, down, left, right) and four red rods with pale
ends stick out on the diagonals. One frame.

The sprite draws its own light (a dark outline, white on the top of the ring, dark lower right);
the game lights the model and draws the outline, so each part takes one mid-tone palette colour
and a material: polished steel for the ball and the spikes (their bright streaks are sheen), red
painted metal for the rods, and the pit is black because it is a hole.

Run: blender --background --python assets/blender/enemies/newsh3-246.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common, px, row  # noqa: E402

NAME = "newsh3-246"
P = 1 / 12  # one sprite pixel
BALL = SPIKE = 9  # palette indices: one mid-tone per part (the ball and spikes are one steel)
ROD, PIT, PIT_WALL, RIB = 73, 1, 2, 11
# (metallic, roughness) per palette index: polished steel, red painted metal, the pit's dark inside
FINISH = {BALL: (0.8, 0.3), RIB: (0.8, 0.25), ROD: (0.4, 0.4), PIT: (0.3, 0.6), PIT_WALL: (0.3, 0.6)}


def lathe(bm, centre, profile, segments):
    """Revolve (rx, ry, z, dx) rings (sprite px) about a vertical axis through `centre`: an
    ellipse rx by ry at height z, moved dx to the right; rx = 0 is a pole."""
    cx, cy = centre
    rings = []
    for rx, ry, z, dx in profile:
        x0 = cx + dx * P
        if rx == 0:
            rings.append([(x0, cy, z * P)])
            continue
        rings.append([(x0 + rx * P * math.cos(2 * math.pi * (i + 0.5) / segments),
                       cy + ry * P * math.sin(2 * math.pi * (i + 0.5) / segments), z * P)
                      for i in range(segments)])
    lib.ring_loft(bm, rings, 0)


def ridged_spike(bm, centre, direction, stations, tip, mat, bottom=1.2):
    """A blade from the ball's centre outwards: a ridged prism (flat 1 px ridge on top, a slope
    either side, a steep dark edge, a keel below) tapering to a point. `stations` are
    (distance, half width, ridge height) in px from `centre`; `tip` is the point's distance.
    One material slot `mat`: the sprite's bright ridge and dark sides are light on polished steel."""
    a = Vector((direction[0], direction[1], 0.0)).normalized()
    s = a.cross(Vector((0, 0, 1))).normalized()
    up = Vector((0, 0, 1))
    c0 = Vector((centre[0], centre[1], 0.0))
    rings = []
    for d, w, h in stations:
        c = c0 + a * d * P
        k = h / stations[0][2]
        rings.append([tuple(c + (s * x + up * z) * P) for x, z in (
            (w, 0.0), (0.6 * w, 0.62 * h), (0.2 * w, h), (-0.2 * w, h), (-0.6 * w, 0.62 * h),
            (-w, 0.0), (0.0, -bottom * k))])
    rings.append([tuple(c0 + a * tip * P + up * 0.1 * P)])
    lib.ring_loft(bm, rings, mat, cap_mats=(mat, mat))


def build(sprite):
    coll = common.reset_collection(NAME)
    mats, slot = [], {}

    def m(index):
        if index not in slot:
            metallic, roughness = FINISH[index]
            slot[index] = len(mats)
            mats.append(common.palette_material(sprite, index, NAME, metallic=metallic,
                                                roughness=roughness))
        return slot[index]

    bm = bmesh.new()
    cx, cy = px(12), row(14)
    parts = []  # (first face, painter) per part, painted once the normals are settled

    def part(painter):
        parts.append((len(bm.faces), painter))

    # The ball: 13 x 12.6 px at its widest, 1.6 px up (the blades' roots and the arms fill the
    # sprite's outline around it), bottom pole 4.4 px down. Above the widest point its shoulder is
    # a quarter ellipse, 2.2 px across and 4.9 px up, to a rounded crest 6.5 px up, so the outside
    # curves over like a ball's (a dome / torus ring, not a pot's straight wall); the crest rolls
    # over a lip into a pit about 7.7 x 7 px with a floor 4 px up (2.5 px deep). The pit sits half
    # a px right of the centre, as the sprite's dark opening does (columns 9-16, rows 11-17).
    pit_x = 0.5
    RX, RY, ZW = 6.5, 6.3, 1.6  # the widest ring and its height
    RCX, RCY, ZC = 4.3, 4.0, 6.5  # the crest
    def paint_ball(f):
        c = f.calc_center_median()
        dx, dy = (c.x - cx) / P - pit_x, (c.y - cy) / P
        r = math.hypot(dx, dy)
        if r < 3.95 and c.z < 6.0 * P:  # the pit: black, as the sprite's opening is (a hole)
            return m(PIT) if f.normal.z > 0.7 else m(PIT_WALL)
        # The rest is one steel shade: the sprite's white top band and dark lower right are its
        # light on the ring, which the game's sun and environment now make.
        return m(BALL)
    part(paint_ball)
    shoulder = []
    for t in (0, 20, 38, 54, 68, 80, 90):
        a = math.radians(t)
        shoulder.append((RCX + (RX - RCX) * math.cos(a), RCY + (RY - RCY) * math.cos(a),
                         ZW + (ZC - ZW) * math.sin(a), 0.35 * math.sin(a)))
    lathe(bm, (cx, cy), [(0, 0, -4.4, 0), (0.45 * RX, 0.45 * RY, -4.0, 0),
                         (0.72 * RX, 0.72 * RY, -2.9, 0), (0.9 * RX, 0.9 * RY, -1.0, 0)] + shoulder +
                        [(4.05, 3.75, 6.35, pit_x), (3.9, 3.55, 5.95, pit_x), (3.85, 3.5, 5.3, pit_x),
                         (3.85, 3.5, 4.3, pit_x), (2.6, 2.4, 4.0, pit_x), (0, 0, 4.0, pit_x)],
          segments=28)

    # Four spikes, ridged on top: the ridge catches the light as the sprite's bright middle stripe.
    part(lambda f: f.material_index)
    smats = m(SPIKE)
    vertical = [(5, 3.4, 3.0), (6, 3.3, 2.8), (7.5, 2.5, 2.3), (10.5, 2.3, 1.4), (12, 0.8, 0.5)]
    horizontal = [(4.5, 3.5, 3.0), (6.3, 3.05, 2.8), (7.3, 2.55, 2.4), (9.5, 2.3, 1.5), (10.8, 0.8, 0.5)]
    ridged_spike(bm, (cx, cy), (0, 1), vertical, 12.5, smats)
    ridged_spike(bm, (cx, cy), (0, -1), vertical, 12.5, smats)
    ridged_spike(bm, (cx, cy), (-1, 0), horizontal, 11.5, smats)
    ridged_spike(bm, (cx, cy), (1, 0), horizontal, 11.5, smats)

    # Red rods on the diagonals, 3.3 px thick, with a rounded end. Their salmon top stripe and pale
    # ends are the light on round painted metal, their dark sides the sprite's outline: one red.
    def paint_rod(f):
        return m(ROD)
    for sx in (-1, 1):
        for sy in (-1, 1):
            ox, oy = cx + sx * 8.3 * P, cy + sy * 8.3 * P
            ix, iy = cx + sx * 3.4 * P, cy + sy * 3.4 * P
            part(paint_rod)
            lib.tube(bm, (ix, iy, 0.3 * P), (ox, oy, 0.3 * P), 1.65 * P, sides=12)
            part(paint_rod)
            lib.ellipsoid(bm, (ox, oy, 0.3 * P), (1.75 * P, 1.75 * P, 1.75 * P), segments=8, rings=3)

    # In the pit: two red rods lying along it (columns 9-11 and 13-14, rows 11-16), their tops
    # level with the rim so they catch the light, the bridge joining their tops along row 11 (the
    # sprite's upside-down U), and the steel rib (column 12) standing over them.
    part(paint_rod)
    for c, rad in ((10.0, 1.35), (13.5, 1.15)):
        lib.tube(bm, (px(c), row(10.9), 6.5 * P - rad * P), (px(c), row(16.3), 6.5 * P - rad * P),
                 rad * P, sides=8)
    part(paint_rod)
    lib.tube(bm, (px(9.2), row(11.0), 6.0 * P), (px(14.4), row(11.0), 6.0 * P), 0.8 * P, sides=6)
    part(lambda f: m(RIB))
    lib.tube(bm, (px(12), row(9.6), 6.5 * P), (px(12), row(15.6), 6.0 * P), 0.6 * P, sides=6)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.faces.ensure_lookup_table()
    bounds = [p[0] for p in parts[1:]] + [len(bm.faces)]
    for (f0, painter), f1 in zip(parts, bounds):
        for f in bm.faces[f0:f1]:
            f.material_index = painter(f)
    lib.set_smooth(bm, 0)
    spikes0, spikes1 = parts[1][0], parts[2][0]
    lib.set_smooth(bm, spikes0, False)
    lib.set_smooth(bm, spikes1)

    obj = lib.mesh_object_mixed(NAME, bm, mats, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
