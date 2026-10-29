"""Spinning arch (newsh2.shp frames 191-205): a 3D version of its sprite.

Seen in episode 1 (levels 25-41) and episode 3. A horseshoe: a round bronze band over the top,
built of tiles with dark joints, coming down into two hard, chamfered grey leg housings (dark collars
at rows 7 and 12), each ending in a thin rod with a pointed tip; a bronze barrel pod with dark rims
hangs in the middle on twin rods with clamps at both ends. Shapes traced from the concept
(assets/blender/features/concepts/newsh2-191.jpg, registered as textures/newsh2-191/concept.png),
kept inside the sprite's outline.

The eight frames turn the whole thing about the screen's vertical axis, so the model is built once
and exported eight times, each turned about Y to the angle its frame shows (read off how far apart
the two legs are drawn: 12, 9, 6, 4, 0 pixels, then back out on the other side): newsh2-191 (frame
191), newsh2-191-f2 (193) ... newsh2-191-f8 (205). It spins about the centre of column 11.

The concept draws the pod 1-3 px higher and a little smaller than the sprite does; the model keeps
the sprite's pod, and textures/newsh2-191/ holds concept maps warped so the concept's pod and
struts land on it (see the notes in maps.json).

Run: blender --background --python assets/blender/enemies/newsh2-191.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-191"
AXIS = 11  # the column the arch spins about (its centre is pixel edge 11.5)
# Leg spacing per frame (px): the angle each frame is turned by is acos(spacing / 12).
SPACING = [12, 9, 6, 4, 0, -4, -6, -9]
PX = 1 / 12


def X(e):
    """Sprite pixel-edge column to x relative to the spin axis."""
    return (e - 11.5) * PX


def Y(r):
    """Sprite pixel-edge row to y."""
    return (14 - r) * PX


TUBE_R = 1.5  # px: the band is a round tube three pixels across seen face on
TUBE_FLAT = 1.25  # ... and a little deeper than wide, as the edge-on frames draw it wider
CORE_R = 1.3  # the dark core showing in the joints between the bronze tiles
POD_FLAT = 0.8  # the pod's depth over its width
CONCEPT_JOINTS = [(5.3, 4.2), (8.0, 2.3), (10.1, 2.3), (12.1, 2.3), (14.9, 2.3), (17.6, 4.3)]
LEG_C = 5.5  # left leg centre column (edge coordinates); the right one is mirrored about 11.5


def chamfer_ring(cx, y, hx, hz, ch, cz=0.0):
    """Eight points of a chamfered rectangle (half sizes hx, hz, chamfer ch) across the XZ plane at y,
    counter-clockwise from +X seen along -Y."""
    pts = [(hx, -hz + ch), (hx, hz - ch), (hx - ch, hz), (-hx + ch, hz), (-hx, hz - ch), (-hx, -hz + ch),
           (-hx + ch, -hz), (hx - ch, -hz)]
    return [(cx + x * PX, y, cz + z * PX) for x, z in pts]


def prism_y(bm, cx, r0, r1, hx, hz, ch, mat, cz=0.0):
    """A hard chamfered block along Y between pixel-edge rows r0 and r1."""
    rings = [chamfer_ring(cx, Y(r), hx, hz, ch, cz) for r in (r0, r1)]
    lib.ring_loft(bm, rings, mat, smooth=False)


def round_ring(cx, y, rx, rz, n=16):
    return [(cx + rx * PX * math.cos(2 * math.pi * (i + 0.5) / n), y, rz * PX * math.sin(2 * math.pi * (i + 0.5) / n))
            for i in range(n)]


def box(bm, c, half, mat):
    """An axis-aligned box: centre and half sizes in units."""
    res = bmesh.ops.create_cube(bm, size=2.0)
    for v in res["verts"]:
        v.co.x = c[0] + v.co.x * half[0]
        v.co.y = c[1] + v.co.y * half[1]
        v.co.z = c[2] + v.co.z * half[2]
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat
        f.smooth = False


def resample(path, s0, s1, step=1.0 * PX):
    """Points along the polyline `path` from arc length s0 to s1, at its own corners and about every
    `step` between."""
    S = [0.0]
    for a, b in zip(path, path[1:]):
        S.append(S[-1] + math.dist(a, b))

    def at(s):
        for k in range(len(path) - 1):
            if S[k] <= s <= S[k + 1] + 1e-9:
                t = (s - S[k]) / max(1e-9, S[k + 1] - S[k])
                return (path[k][0] + (path[k + 1][0] - path[k][0]) * t, path[k][1] + (path[k + 1][1] - path[k][1]) * t)
        return path[-1]

    marks = sorted({s0, s1, *[s for s in S if s0 < s < s1]})
    out = []
    for a, b in zip(marks, marks[1:]):
        n = max(1, math.ceil((b - a) / step))
        out += [at(a + (b - a) * i / n) for i in range(n)]
    out.append(at(s1))
    return out, S[-1]


def build_one(sprite, name, angle):
    coll = common.reset_collection(name)
    mats, slot = [], {}

    def mat(i, metallic=0.8, roughness=0.3):
        """Material slot of palette index i. Bronze and greys are polished metal (the dark joints,
        collars and clamps a little less): the sprite's highlights and dark sides are its drawn
        light, which the game's lights make on these surfaces."""
        if i not in slot:
            slot[i] = len(mats)
            mats.append(common.palette_material(sprite, i, NAME, metallic=metallic, roughness=roughness))
        return slot[i]

    for i in (4, 5, 21):
        mat(i, 0.7, 0.42)
    for i in (7, 9, 10):  # the steel of the legs: satin, so its flat faces don't mirror the sky
        mat(i, 0.5, 0.5)

    bm = bmesh.new()

    # --- The bronze band: a row of round tiles with dark joints over a dark core, from the top of
    # the left leg housing (row 7) over the top (row 2.5) and down to the right one.
    half = [(LEG_C, 7.0), (LEG_C, 6.2), (5.7, 5.7), (6.3, 4.75), (7.1, 3.85), (8.0, 3.0), (9.4, 2.6),
            (10.6, 2.5), (11.5, 2.5)]
    path = [(X(c), Y(r)) for c, r in half] + [(-X(c), Y(r)) for c, r in reversed(half[:-1])]
    S_total = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
    S_half = S_total / 2
    core, _ = resample(path, 0.0, S_total)
    lib.polyline_tube(bm, [(x, y, 0.0) for x, y in core], CORE_R * PX, sides=8, mat_index=mat(4),
                      caps=False, flat=TUBE_FLAT)
    # Eight tiles, with the joints where the concept draws them (pixel edges), the one at column 12
    # standing for the sprite's dark seam pixel at the top.
    fine, _ = resample(path, 0.0, S_total, step=0.05 * PX)
    fine_s = [0.0]
    for p0, p1 in zip(fine, fine[1:]):
        fine_s.append(fine_s[-1] + math.dist(p0, p1))
    joints = []
    for c, r in CONCEPT_JOINTS:
        j = min(range(len(fine)), key=lambda i: math.dist(fine[i], (X(c), Y(r))))
        joints.append(fine_s[j])
    bounds = [0.0] + sorted(joints) + [S_total]
    gap = 0.13 * PX
    for a, b in zip(bounds, bounds[1:]):
        s0 = a + (gap if a > 1e-9 else 0.0)
        s1 = b - (gap if b < S_total - 1e-9 else 0.0)
        pts, _ = resample(path, s0, s1)
        lib.polyline_tube(bm, [(x, y, 0.0) for x, y in pts], TUBE_R * PX, sides=8, mat_index=mat(25),
                          caps=True, smooth=True, flat=TUBE_FLAT)
    # Tile end caps flat.
    for f in bm.faces:
        if f.material_index == mat(25) and len(f.verts) == 8:
            f.smooth = False

    for s in (-1, 1):
        cx = s * X(LEG_C)
        # --- The leg housing: a hard chamfered block (rows 7.8-12.2), the dark collar where the band
        # meets it (row 7) and the dark collar at row 12, then a slightly narrower lower block down
        # to row 14.4.
        prism_y(bm, cx, 6.85, 7.8, 1.5, 1.42, 0.45, mat(5))
        prism_y(bm, cx, 7.8, 12.2, 1.42, 1.3, 0.45, mat(10))
        prism_y(bm, cx, 12.2, 12.95, 1.5, 1.4, 0.45, mat(5))
        prism_y(bm, cx, 12.95, 14.45, 1.25, 1.15, 0.4, mat(10))
        # The raised side plate on the housing's outer face (the concept's panel, rows 8.3-11).
        box(bm, (cx + s * 1.42 * PX, Y(9.7), 0.0), (0.14 * PX, 1.35 * PX, 0.8 * PX), mat(9))
        # --- The rod below: a thin round bar with a collar at the top, a ring near the end and a
        # pointed tip at row 19.9.
        rod = [(14.45, 0.0), (14.45, 1.45), (15.25, 1.45), (15.25, 1.25), (17.5, 1.25), (17.5, 1.45),
               (18.3, 1.45), (18.3, 1.2), (19.95, 0.15)]
        mats_rod = [mat(5), mat(5), mat(5), mat(9), mat(5), mat(5), mat(5), mat(7)]
        rings = [[(cx, Y(r), 0.0)] if rr == 0 else round_ring(cx, Y(r), rr, rr, n=8) for r, rr in rod]
        lib.ring_loft(bm, rings, mats_rod, cap_start=True, cap_end=True, smooth=True)
        # --- The strut: twin thin rods at rows 10 and 11 from the housing to the pod, a clamp block on
        # the housing and a round clamp collar on the pod's side.
        for r in (10.0, 11.0):
            lib.tube(bm, (s * X(6.8), Y(r), 0.0), (s * X(8.5), Y(r), 0.0), 0.38 * PX, sides=6,
                     mat_index=mat(7), caps=False)
        box(bm, (s * X(7.4), Y(10.5), 0.0), (0.62 * PX, 1.4 * PX, 0.85 * PX), mat(5))
        lib.tube(bm, (s * X(7.75), Y(10.5), 0.0), (s * X(8.55), Y(10.5), 0.0), 1.15 * PX, sides=10,
                 mat_index=mat(4), caps=True, smooth=True)

    # --- The pod: a round bronze barrel lying along Y (rows 6-14.9): a dark rim round its flat top,
    # the barrel body, a dark band where its lower end starts to narrow (the sprite's dark row 12),
    # chamfered lower panels and a dark rim round its small flat bottom.
    sections = [  # (row edge, half width px, material of the band below)
        (6.0, 2.3, 21), (6.2, 2.7, 21), (6.75, 2.8, 25), (7.0, 3.2, 25), (7.6, 3.42, 25), (11.4, 3.42, 21),
        (12.0, 3.42, 25), (12.6, 3.25, 25), (13.4, 2.7, 25), (14.15, 2.0, 21), (14.8, 1.8, 21), (14.95, 1.4, 21)]
    rings = [round_ring(0.0, Y(r), w, w * POD_FLAT) for r, w, _ in sections]
    rings = [[(0.0, Y(5.95), 0.0)]] + rings + [[(0.0, Y(14.97), 0.0)]]
    band_mats = [mat(21)] + [mat(m) for _, _, m in sections[:-1]] + [mat(21)]
    lib.ring_loft(bm, rings, band_mats, smooth=True)
    # Make the rims crisp: the dark bands are flat shaded.
    for f in bm.faces:
        if f.material_index == mat(21):
            f.smooth = False

    # Turn it about the spin axis and put the axis on column 11.
    bmesh.ops.transform(bm, matrix=Matrix.Translation((lib.px(AXIS), 0, 0)) @ lib.rot_y(angle), verts=bm.verts)
    return lib.finish(name, bm, mats, coll)


def build(sprite):
    frames = sprite["sprites"][0]["frames"]
    models = []
    for k, frame in enumerate(frames):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj = build_one(sprite, name, math.acos(SPACING[k] / 12))
        models.append((name, [obj], lib.frames_subset(sprite, [frame])))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
