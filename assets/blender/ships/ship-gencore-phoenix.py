"""Gencore Phoenix (player ship, tyrian.shp#8 sprite 157 and its banking frames 153-161).

A grey hard-surface fighter, modelled part by part from the user's concept art as it lines up with
the sprite (assets/blender/textures/ship-gencore-phoenix/concept.png, from tools/concept_maps.py):
every part sits where the concept draws it, so the concept-derived texture (texture_bake.py) lands
on the matching part. The sprite still bounds the top-view outline and sets the palette.

Coordinates here are sprite pixel EDGES (x = column edge, y = row edge, 0..24 x 0..28, top-left =
the sprite's top-left), the same frame as concept.png divided by its texels_per_px; z is in sprite
px. From front to back:

- a blunt nose with a light armour plate down its top (concept rows 1-5.5);
- the cockpit: a dark, glossy faceted canopy (x 11-13, y 6-8.3) in a raised octagonal frame, a
  dark grille behind it, and box-section cheeks with small antennas either side;
- the body (y 9.6-17.2): a pointed chevron plate behind the cockpit, the spine ridge down the
  middle, and the two curved "heart" armour plates sweeping from the shoulders in to the spine,
  over a darker outer side strip;
- the rear body: armour plates either side of a dark vent and a channel holding a round rod that
  runs back to the tail, and twin nozzles at the tail;
- the wings: crescent (scythe) blades, convex outside and straight inside, pointed at both ends,
  with a mid plate and a light inner strip stepped on top, a hook curving into the boom, and the
  box-section booms (light top beam over a darker under-frame) joining them to the body.

The sprite's bright spots and streaks are sheen on polished metal, not bumps.

Run: blender --background --python assets/blender/ships/ship-gencore-phoenix.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "ship-gencore-phoenix"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel
W, H = 24, 28  # sprite size; the origin is its centre
CX = W / 2  # the ship's centre line (x edge 12)
ZS = 1.15  # heights above the waterline are stretched by this (the numbers below were laid out at 1)


def ploft(bm, rings, paint, faces, cap_start=True, cap_end=True):
    """A flat-faced loft through rings of edge-space points (x, y, z px), all with the same count
    (a one-point ring is a tip). Each face is recorded with paint(y, x, up), applied once the
    normals are known."""
    vs = [[bm.verts.new(((x - CX) * P, (H / 2 - y) * P, (z * ZS if z > 0 else z) * P)) for x, y, z in ring] for ring in rings]
    for r0, r1 in zip(vs, vs[1:]):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            faces.append((bm.faces.new(f), paint))
    if cap_start and len(vs[0]) > 2:
        faces.append((bm.faces.new(list(reversed(vs[0]))), paint))
    if cap_end and len(vs[-1]) > 2:
        faces.append((bm.faces.new(vs[-1]), paint))


def inset(poly, d):
    """The 2D polygon [(x, y)] offset inwards by d (mitred corners)."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    sgn = 1 if area > 0 else -1
    n = len(poly)
    normals = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        ln = math.hypot(x1 - x0, y1 - y0)
        normals.append((-(y1 - y0) / ln * sgn, (x1 - x0) / ln * sgn))
    out = []
    for i in range(n):
        a, b = normals[i - 1], normals[i]
        k = d / (1 + a[0] * b[0] + a[1] * b[1])
        out.append((poly[i][0] + (a[0] + b[0]) * k, poly[i][1] + (a[1] + b[1]) * k))
    return out


def zf(z):
    return z if callable(z) else (lambda y: z)


def plate(bm, faces, poly, z0, z1, ch, mat):
    """A hard-surface armour plate: the top-view polygon extruded from z0 to z1 with a chamfered top
    edge (ch px in and down). z1 may be a function of y, for a sloped top."""
    z0, z1 = zf(z0), zf(z1)
    top = inset(poly, ch)
    rings = [[(x, y, z0(y)) for x, y in poly], [(x, y, z1(y) - ch) for x, y in poly],
             [(x, y, z1(y)) for x, y in top]]
    ploft(bm, rings, lambda y, x, up: mat, faces)


def mirror(poly):
    return [(W - x, y) for x, y in reversed(poly)]


def hull_section(y, w, zt):
    """A hard-surface section across the hull at row edge y: a centre strip (|x| < v), a flat deck,
    a chamfered shoulder, the chine at the silhouette (half width w), a lower chamfer and a keel."""
    v = min(1.0, 0.45 * w)
    d = max(v + 0.1, w - 0.8)
    right = [(v, zt), (d, zt), (w - 0.3, zt - 0.6), (w, zt * 0.4), (w - 0.5, -1.0), (0.45 * w, -1.6)]
    left = [(-x, z) for x, z in reversed(right)]
    return [(CX + x, y, z) for x, z in right + left]


def build(sprite):
    coll = common.reset_collection(NAME)
    used = {}
    mats = []

    def m(i, metallic=0.8, roughness=0.3, emission=0.0):
        """Material slot for palette index i (one slot per index)."""
        if i not in used:
            used[i] = len(mats)
            mats.append(common.palette_material(sprite, i, NAME, metallic=metallic, roughness=roughness,
                                                emission_strength=emission))
        return used[i]

    # Palette shades picked from the concept's mid-tones per part (its lighting discounted): the
    # concept reads darker and less contrasty than the sprite, so the hull is mostly 5-7 with the
    # light armour (nose plate, chevron, spine, wing strips) at 8, and near-black glass and vents.
    GLASS = m(1, 0.2, 0.08)
    VENT, DARK, SIDE, HULL, ARMOUR, LIGHT = m(2), m(4), m(5), m(6), m(7), m(8)

    bm = bmesh.new()
    faces = []

    # Hull: (row edge, half width, deck height). Blunt nose, narrower at the cockpit (the cheeks and
    # frame sit on it), full width over the body, narrowing behind the booms to the tail.
    HULL_ROWS = [(1.0, 0.8, 2.2), (1.8, 1.4, 2.8), (3.0, 1.85, 3.3), (4.5, 2.2, 3.7), (5.6, 2.5, 3.9),
                 (5.8, 3.6, 3.7), (9.3, 3.6, 3.9), (9.6, 4.75, 4.1), (17.2, 4.75, 4.1), (17.7, 3.8, 4.0),
                 (18.2, 3.75, 4.0), (19.9, 3.6, 3.95), (22.9, 3.6, 3.7), (23.6, 3.6, 3.3), (24.6, 2.7, 2.7),
                 (25.6, 1.6, 2.1)]

    def hull_paint(y, x, up):
        dx = abs(x - CX)
        if up > 0.5 and 18.2 < y < 19.9 and dx < 1.0:
            return VENT  # the dark vent behind the spine
        if up > 0.5 and 19.9 < y < 23.6 and dx < 1.0:
            return DARK  # the channel the rod lies in
        if y > 22.9:
            return DARK  # the darker tail
        if 9.6 < y < 17.2 and dx > 3.0:
            return SIDE  # the darker outer side strip
        return HULL

    ploft(bm, [hull_section(*h) for h in HULL_ROWS], hull_paint, faces)

    # Nose armour plate: a light plate down the nose's top, following its slope.
    nose_z = lambda y: 2.5 + (4.25 - 2.5) * (y - 1.4) / (5.4 - 1.4)  # noqa: E731
    plate(bm, faces, [(11.45, 1.4), (12.55, 1.4), (13.05, 2.5), (13.05, 5.4), (10.95, 5.4), (10.95, 2.5)],
          1.0, nose_z, 0.25, LIGHT)

    # Cockpit frame: a raised octagonal rim (x 10.4-13.6, y 5.6-9.8) around the canopy and grille.
    def octagon(hw, y0, y1, k, z):
        pts = [(-hw + k, y0), (hw - k, y0), (hw, y0 + k), (hw, y1 - k), (hw - k, y1), (-hw + k, y1),
               (-hw, y1 - k), (-hw, y0 + k)]
        return [(CX + x, y, z) for x, y in pts]

    ploft(bm, [octagon(1.6, 5.6, 9.8, 0.6, 3.4), octagon(1.6, 5.6, 9.8, 0.6, 4.75),
               octagon(1.4, 5.75, 9.65, 0.5, 5.1), octagon(1.15, 5.95, 9.45, 0.45, 5.1),
               octagon(1.15, 5.95, 9.45, 0.45, 3.4)],
          lambda y, x, up: ARMOUR, faces, cap_start=False, cap_end=False)

    # Canopy: dark glossy glass, a faceted bubble (x 11-13, y 6-8.3) rising above the frame.
    def glass_ring(y, hw, zt):
        return [(CX + x, y, z) for x, z in ((-hw, 3.6), (-hw, zt - 0.6), (-0.5 * hw, zt), (0.5 * hw, zt),
                                            (hw, zt - 0.6), (hw, 3.6))]

    ploft(bm, [glass_ring(6.0, 0.85, 4.7), glass_ring(6.6, 1.0, 5.5), glass_ring(7.6, 1.0, 5.75),
               glass_ring(8.3, 0.9, 5.1)], lambda y, x, up: GLASS, faces)

    # Grille behind the canopy: a dark block sunk in the frame with two ribs along it.
    plate(bm, faces, [(10.95, 8.35), (13.05, 8.35), (13.05, 9.45), (10.95, 9.45)], 3.4, 4.4, 0.1, VENT)
    for x0 in (11.55, 12.2):
        plate(bm, faces, [(x0, 8.4), (x0 + 0.25, 8.4), (x0 + 0.25, 9.4), (x0, 9.4)], 4.0, 4.75, 0.08, DARK)

    # Cheeks: box-section blocks beside the cockpit, with thin antennas ahead of them.
    cheek = [(8.6, 5.9), (10.1, 5.9), (10.35, 6.2), (10.35, 9.4), (8.3, 9.4), (8.3, 6.2)]
    antenna = [(9.2, 3.9), (9.5, 3.9), (9.5, 6.0), (9.2, 6.0)]
    for poly in (cheek, mirror(cheek)):
        plate(bm, faces, poly, 2.8, 4.75, 0.3, SIDE)
    for poly in (antenna, mirror(antenna)):
        plate(bm, faces, poly, 2.6, 4.6, 0.08, DARK)

    # Chevron plate behind the cockpit, pointing back at the spine.
    plate(bm, faces, [(10.6, 9.9), (13.4, 9.9), (13.4, 11.5), (12.0, 12.9), (10.6, 11.5)], 3.6, 5.3, 0.3, LIGHT)

    # Spine ridge down the body's centre, sloping down towards the vent.
    spine_z = lambda y: 5.65 - 0.65 * (y - 12.4) / (18.1 - 12.4)  # noqa: E731
    plate(bm, faces, [(11.15, 12.4), (12.85, 12.4), (12.75, 17.6), (12.4, 18.1), (11.6, 18.1), (11.25, 17.6)],
          3.6, spine_z, 0.3, LIGHT)

    # Heart plates: the two curved armour plates from the shoulders in to the spine.
    heart = [(8.7, 9.7), (10.3, 9.7), (10.45, 11.4), (10.95, 12.7), (11.05, 16.6), (10.6, 17.6),
             (9.7, 17.1), (9.0, 15.8), (8.7, 14.0)]
    for poly in (heart, mirror(heart)):
        plate(bm, faces, poly, 3.6, 5.0, 0.3, ARMOUR)

    # Rear armour plates either side of the vent and the rod channel.
    rear = [(8.7, 17.7), (10.5, 18.0), (11.0, 18.7), (11.0, 23.6), (10.4, 24.5), (9.2, 23.6), (8.8, 21.5)]
    for poly in (rear, mirror(rear)):
        plate(bm, faces, poly, 3.0, 4.8, 0.3, HULL)

    # The rod: a round bar from the vent to the tail, held by a clamp bar at its front.
    def circle(y, cz, rad, n=16):
        return [(CX + rad * math.cos(a), y, cz + rad * math.sin(a))
                for a in (2 * math.pi * (k + 0.5) / n for k in range(n))]

    ploft(bm, [circle(19.9, 4.1, 0.38), circle(23.8, 4.1, 0.38)], lambda y, x, up: HULL, faces)
    plate(bm, faces, [(11.0, 19.75), (13.0, 19.75), (13.0, 20.15), (11.0, 20.15)], 3.6, 4.65, 0.1, ARMOUR)

    # Twin nozzles at the tail: round tubes with a dark bore.
    for cx in (10.8, 13.2):
        ring = lambda y, rad: [(x - CX + cx, y, z) for x, y, z in circle(y, 1.4, rad, 8)]  # noqa: E731
        ploft(bm, [ring(23.3, 0.7), ring(25.7, 0.7), ring(25.7, 0.45)], lambda y, x, up: DARK, faces,
              cap_start=False, cap_end=False)
        ploft(bm, [ring(25.7, 0.45), ring(25.0, 0.45)], lambda y, x, up: VENT, faces, cap_start=False)

    # Wings: crescent blades, a flat-faced base blade (knife outer edge, a crest near the straight
    # inner edge) with a mid plate and a light inner strip stepped on top.
    # (row edge, outer edge x, inner edge x, crest height, keel depth); left wing.
    WING = [(9.6, 3.9, 5.75, 1.0, -0.3), (11.0, 2.9, 5.75, 1.4, -0.5), (13.0, 1.9, 5.75, 1.8, -0.7),
            (15.0, 1.2, 5.75, 2.1, -0.8), (17.0, 1.0, 5.75, 2.2, -0.8), (19.0, 1.0, 5.8, 2.1, -0.8),
            (20.3, 1.05, 6.0, 1.9, -0.8), (21.6, 1.1, 6.0, 1.7, -0.8), (22.6, 1.3, 5.9, 1.4, -0.7),
            (23.5, 2.7, 5.4, 0.9, -0.5), (24.3, 2.95, 5.0, 0.6, -0.3), (24.75, 3.3, 4.8, 0.4, -0.2)]

    def blade_ring(y, o, i, t, b):
        w = i - o
        return [(o, y, 0.15), (o + 0.45 * w, y, 0.75 * t), (i - 0.8, y, t), (i, y, t - 0.6), (i, y, 0.1),
                (i - 0.9, y, b), (o + 0.4 * w, y, 0.6 * b)]

    def wplate_ring(y, o, i, t, f, g, dz, zb):
        w = i - o
        a, b = o + f * w, i - g
        zt = t + dz
        return [(a, y, zb), (b, y, zb), (b, y, zt - 0.2), (b - 0.2, y, zt), (a + 0.3, y, zt - 0.1),
                (a, y, zt - 0.4)]

    blade = [[(5.3, 8.9, 0.5)]] + [blade_ring(*w) for w in WING] + [[(4.0, 25.0, 0.2)]]
    mid = [[(4.4, 10.0, 1.4)]] + [wplate_ring(y, o, i, t, 0.22, 0.42, 0.45, 0.4 * t)
                                  for y, o, i, t, b in WING[1:-1]] + [[(3.8, 24.1, 0.9)]]
    strip = [[(4.7, 10.2, 1.9)]] + [wplate_ring(y, o, i, t, 0.66, 0.1, 0.75, 0.5 * t)
                                    for y, o, i, t, b in WING[1:-2]] + [[(4.6, 23.2, 1.5)]]
    for flip in (False, True):
        for part, mat in ((blade, SIDE), (mid, ARMOUR), (strip, LIGHT)):
            rings = [[(W - x, y, z) for x, y, z in ring][::-1] if flip else ring for ring in part]
            ploft(bm, rings, lambda y, x, up, mat=mat: mat, faces)

    # Hook: the wing's light inner strip curving into the boom, and the booms: a light, chamfered top
    # beam (the concept's J-shaped bright edge continues along it) over a darker under-frame.
    hook = [(5.5, 17.4), (6.0, 18.8), (7.3, 19.4), (8.6, 19.4), (8.6, 19.95), (5.5, 19.95)]
    boom = [(5.6, 19.4), (9.2, 19.4), (9.2, 21.4), (5.6, 21.4)]
    under = [(5.6, 21.4), (9.2, 21.4), (9.2, 22.9), (5.6, 22.9)]
    for poly, z0, z1, ch, mat in ((hook, -0.5, 1.8, 0.25, LIGHT), (boom, -0.6, 1.9, 0.4, LIGHT),
                                  (under, -1.0, 0.8, 0.2, DARK)):
        for p in (poly, mirror(poly)):
            plate(bm, faces, p, z0, z1, ch, mat)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f, paint in faces:
        cen = f.calc_center_median()
        f.material_index = paint(H / 2 - cen.y * 12, cen.x * 12 + CX, f.normal.z)
    # Smooth shading split at the creases: flat panels and chamfers stay crisp, round parts (the rod)
    # stay round, and the polished metal's sheen runs along each panel.
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    obj.modifiers.new("edges", "EDGE_SPLIT").split_angle = math.radians(30)
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        level = next(f for f in sprite["frames"] if f["index"] == sprite["sprites"][0]["frames"][0])
        ref = ROOT / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], out, ref, size=level["size"])


if __name__ == "__main__":
    main()
