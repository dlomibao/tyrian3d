"""Spiked mine (newsh3.shp frame 246): a 3D version of its sprite.

Seen in episode 4 (levels 4, 10, 22, 36, 50). A silver ball, about as tall as it is wide, whose top
is a rounded ring (its crest 6.5 px up) around a dark pit 2.5 px deep; two red rods lie in the pit
with their tops at rim height, joined by a bridge at the top, with a steel rib between them. Four
long ridged spikes stand out from its flanks (up, down, left, right) and four red rods with pale
ends stick out on the diagonals. One frame.

Faces take the palette shade the sprite draws them in (lit from the upper left), so the top view
matches the sprite's colours.

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
LIGHT = Vector((-0.45, 1.0, 1.0)).normalized()  # the sprite's light: from the top and the left
RING_LIGHT = Vector((-0.2, 1.0, 0.15)).normalized()  # the ring's: low, from the top of the screen


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


def ridged_spike(bm, centre, direction, stations, tip, mats, bottom=1.2):
    """A blade from the ball's centre outwards: a ridged prism (flat 1 px ridge on top, a slope
    either side, a steep dark edge, a keel below) tapering to a point. `stations` are
    (distance, half width, ridge height) in px from `centre`; `tip` is the point's distance.
    `mats` = (ridge, lit slope, shaded slope, lit edge, shaded edge, keel) material slots; the lit
    side is the one facing the upper left."""
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
    ridge, lit_slope, dark_slope, lit_edge, dark_edge, keel = mats
    right_lit = s.x * -1 + s.y > 0
    r_slope, l_slope = (lit_slope, dark_slope) if right_lit else (dark_slope, lit_slope)
    r_edge, l_edge = (lit_edge, dark_edge) if right_lit else (dark_edge, lit_edge)
    band = [r_edge, r_slope, ridge, l_slope, l_edge, keel, keel]
    lib.ring_loft(bm, rings, [band] * (len(rings) - 1), cap_mats=(keel, keel))


def build(sprite):
    coll = common.reset_collection(NAME)
    mats, slot = [], {}

    def m(index):
        if index not in slot:
            red = index >= 67
            slot[index] = len(mats)
            mats.append(common.palette_material(sprite, index, NAME, metallic=0.25 if red else 0.15,
                                                roughness=0.45 if red else 0.45))
        return slot[index]

    bm = bmesh.new()
    cx, cy = px(12), row(14)
    parts = []  # (first face, painter) per part, painted once the normals are settled

    def part(painter):
        parts.append((len(bm.faces), painter))

    def lit(f):
        return f.normal.dot(LIGHT)

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
        n = f.normal
        if r < 3.95 and c.z < 6.0 * P:  # the pit: black, as the sprite's opening is
            return m(1) if n.z > 0.7 else m(2)
        if n.z < -0.2:
            return m(4)
        if r < 4.4 and (n.x * dx + n.y * dy) < 0:  # the lip, facing into the pit
            s = -n.y + 0.4 * n.x
            return m(13 if s > 0.3 else 9 if s > -0.2 else 1)
        # The ring is drawn lit from the top of the screen: its top band (the far wall and the
        # crest beside it) near white, its left mid silver, its right and bottom dark. So its shade
        # follows where a face sits around the ring as much as which way it faces.
        around = (-0.35 * dx + dy) / max(r, 1e-6) / 1.06
        s = 0.7 * around + 0.4 * n.dot(RING_LIGHT)
        k = (14 if s > 0.85 else 13 if s > 0.65 else 12 if s > 0.5 else 11 if s > 0.35
             else 10 if s > 0.2 else 9 if s > 0.05 else 7 if s > -0.15 else 5 if s > -0.45 else 4)
        return m(max(k, 7) if n.z > 0.2 and dx < 1.0 else k)  # the near side mid grey, not black
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

    # Four spikes, ridged on top: the ridge is the sprite's bright middle stripe, the slopes its
    # lit (upper-left) and shaded (lower-right) sides, the steep edges its dark outline.
    part(lambda f: f.material_index)
    smats = (m(11), m(7), m(4), m(3), m(2), m(3))
    vertical = [(5, 3.4, 3.0), (6, 3.3, 2.8), (7.5, 2.5, 2.3), (10.5, 2.3, 1.4), (12, 0.8, 0.5)]
    horizontal = [(4.5, 3.5, 3.0), (6.3, 3.05, 2.8), (7.3, 2.55, 2.4), (9.5, 2.3, 1.5), (10.8, 0.8, 0.5)]
    ridged_spike(bm, (cx, cy), (0, 1), vertical, 12.5, smats)
    ridged_spike(bm, (cx, cy), (0, -1), vertical, 12.5, smats)
    ridged_spike(bm, (cx, cy), (-1, 0), horizontal, 11.5, smats)
    ridged_spike(bm, (cx, cy), (1, 0), horizontal, 11.5, smats)

    # Red rods on the diagonals, 3.3 px thick, with a rounded pale end (the lower right one's end
    # is plain red in the sprite). Their top is the sprite's bright salmon stripe, the flanks its
    # darker red, and the sides fall away to the dark red of its outline.
    def paint_rod(f):
        nz = f.normal.z
        return m(75 if nz > 0.95 else 71 if nz > 0.7 else 162 if nz > -0.6 else 67)
    for sx in (-1, 1):
        for sy in (-1, 1):
            ox, oy = cx + sx * 8.3 * P, cy + sy * 8.3 * P
            ix, iy = cx + sx * 3.4 * P, cy + sy * 3.4 * P
            part(paint_rod)
            lib.tube(bm, (ix, iy, 0.3 * P), (ox, oy, 0.3 * P), 1.65 * P, sides=12)
            end = 72 if (sx, sy) == (1, -1) else 76
            part(lambda f, end=end: m(end if f.normal.z > 0.6 else 71 if f.normal.z > 0.3 else 162))
            lib.ellipsoid(bm, (ox, oy, 0.3 * P), (1.75 * P, 1.75 * P, 1.75 * P), segments=8, rings=3)

    # In the pit: two red rods lying along it (columns 9-11 and 13-14, rows 11-16), their tops
    # level with the rim so they catch the light, the bridge joining their tops along row 11 (the
    # sprite's upside-down U), and the steel rib (column 12) standing over them.
    part(paint_rod)
    for c, rad in ((10.0, 1.35), (13.5, 1.15)):
        lib.tube(bm, (px(c), row(10.9), 6.5 * P - rad * P), (px(c), row(16.3), 6.5 * P - rad * P),
                 rad * P, sides=8)
    part(lambda f: m(73 if f.normal.z > 0.4 else 70))
    lib.tube(bm, (px(9.2), row(11.0), 6.0 * P), (px(14.4), row(11.0), 6.0 * P), 0.8 * P, sides=6)
    part(lambda f: m(13 if f.normal.z > 0.4 else 9))
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
