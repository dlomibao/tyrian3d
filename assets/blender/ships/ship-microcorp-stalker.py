"""Microcorp Stalker (player ship, tyrian.shp#8 sprite 195 and its banking frames 191-199).

A grey fighter: a shiny conical nose, a round collar with the dark cockpit window cut into it, a
narrow neck with two red lights, a wide rear body with three bright ribs and a red engine glow in a
dark nozzle, and two level swept wings pointing forward and out (a dark base plate with a raised
bright leading-edge strip, a groove and a raised outer panel). The outline covers the sprite's
dark edge pixels. The sprite is centred on column 11, half a pixel left of the 24 px block's centre.

Run: blender --background --python assets/blender/ships/ship-microcorp-stalker.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import common  # noqa: E402
from lib_b001 import loft_path, mirrored  # noqa: E402

NAME = "ship-microcorp-stalker"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel
AXIS = 11  # the sprite's mirror column; the model is built about X = 0 and shifted to it at the end


def cx(c):
    """Sprite column centre to X, relative to the mirror column."""
    return (c - AXIS) / 12


def ex(e):
    """Sprite column edge (left edge of column e) to X, relative to the mirror column."""
    return (e - AXIS - 0.5) / 12


def ey(r):
    """Sprite row edge (top edge of row r) to Y."""
    return (14 - r) / 12


def sx(c):
    """Continuous sprite column coordinate (pixel c spans [c, c + 1]) to X about the mirror axis."""
    return (c - AXIS - 0.5) / 12


def clip(poly, a, b, c):
    """Keep the part of polygon `poly` (list of (col, row)) where a*col + b*row <= c."""
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if (fp < 0 < fq) or (fq < 0 < fp):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def plate(bm, poly, z0, z1, mat_index, mirror=False):
    """A flat plate from z0 to z1 (px) with the outline `poly` in sprite (col, row) coordinates."""
    pts = [(sx(c), ey(r)) for c, r in poly]
    if mirror:
        pts = [(-x, y) for x, y in pts]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    top = [bm.verts.new((x, y, z1 * P)) for x, y in pts]
    bot = [bm.verts.new((x, y, z0 * P)) for x, y in pts]
    bm.faces.new(top).material_index = mat_index
    bm.faces.new(list(reversed(bot))).material_index = mat_index
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((bot[i], bot[j], top[j], top[i])).material_index = mat_index


def notched_loft(bm, sections, arc=13, mat=0, notch_mat=0):
    """A loft along +Y whose rings can have a flat-floored notch cut into the top (a recessed
    window). Each section is (row, half width, half height, z centre, notch half width, notch
    floor z or None), all in px; None leaves the notch flush with the rim (a flat chord)."""
    rings, notched = [], []
    for r, w, h, z, nw, floor in sections:
        tr = math.acos(min(nw / w, 0.99))
        span = math.pi + 2 * tr
        pts = [(w * math.cos(tr - k * span / (arc - 1)), z + h * math.sin(tr - k * span / (arc - 1)))
               for k in range(arc)]
        rim = z + h * math.sin(tr)
        f = rim if floor is None else floor
        pts += [(-0.85 * nw, f), (0.85 * nw, f)]
        rings.append([bm.verts.new((x * P, ey(r), zz * P)) for x, zz in pts])
        notched.append(floor is not None)
    n = arc + 2
    for s, (r0, r1) in enumerate(zip(rings, rings[1:])):
        cut = notched[s] or notched[s + 1]
        for i in range(n):
            j = (i + 1) % n
            face = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            face.material_index = notch_mat if cut and i >= arc - 1 else mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bm.faces.new(rings[-1]).material_index = mat


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    # A polished metal hull: each part takes its sprite mid-tone and lets the game's light shade
    # it and make the shine (the sprite's bright streaks on the nose and the rear body's left side,
    # and its dark right sides and edge ring, are drawn light, not paint or shape).
    mats = [
        pal(9, metallic=0.8, roughness=0.3),  # 0 rear hull grey
        pal(7, metallic=0.75, roughness=0.32),  # 1 wing panels and base plate
        pal(11, metallic=0.8, roughness=0.28),  # 2 bright strakes
        pal(11, metallic=0.85, roughness=0.25),  # 3 nose cone
        pal(14, metallic=0.85, roughness=0.25),  # 4 (unused: the nose's highlight is shine)
        pal(2, metallic=0.05, roughness=0.1),  # 5 dark cockpit window, glossy glass
        pal(117, emission_strength=3.0),  # 6 red side lights
        pal(120, emission_strength=5.0),  # 7 engine glow
        pal(7, metallic=0.7, roughness=0.38),  # 8 neck, a darker grey
        pal(9, metallic=0.8, roughness=0.3),  # 9 cockpit ring
        pal(11, metallic=0.8, roughness=0.28),  # 10 wing leading edges
        pal(3, metallic=0.5, roughness=0.5),  # 11 wing grooves, nozzle
        pal(116, emission_strength=3.0),  # 12 nozzle glow rim
        pal(4, metallic=0.75, roughness=0.32),  # 13 (unused: the dark flanks were the sprite's outline)
    ]
    HULL, WING, BRIGHT, NOSE, SHINE, COCKPIT, RED, GLOW, NECK, RING, LEAD, BASE, GLOW2, FLANK = range(14)
    bm = bmesh.new()

    # Nose cone (rows 0-6), out to the sprite's outline: half width 0.5 * row + 0.5 px covers
    # the staircase's dark edge pixels and none beyond. Round, a little taller than half its width.
    nose = [(-0.4, 0, 0, 0.5), (0.4, 0.7, 0.55, 0.5), (2.0, 1.5, 1.15, 0.45), (4.0, 2.5, 1.9, 0.4),
            (6.0, 3.5, 2.65, 0.35), (6.9, 3.9, 2.85, 0.3)]
    # Its bright streak (columns 10-11, rows 3-6) is the polished cone's shine: no geometry for it.
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in nose], sides=12, mat_index=NOSE)

    # Cockpit ring (rows 7-11): a round collar with the dark window (columns 10-12, rows 7-10)
    # cut into its top, floor about 1.2 px below the rim.
    nw, fl = 1.5, 1.8
    common_ring = (4.25, 2.9, 0.3)
    notched_loft(bm, [(6.6, 3.8, 2.75, 0.3, nw, None), (7.0, *common_ring, nw, None), (7.3, *common_ring, nw, fl),
                      (10.7, *common_ring, nw, fl), (11.0, *common_ring, nw, None), (11.7, 4.15, 2.8, 0.25, nw, None),
                      (12.1, 3.4, 2.4, 0.2, nw, None)], mat=RING, notch_mat=COCKPIT)
    # The lighter dot in the window's middle (column 11, rows 8-9).
    common.loft(bm, [(ey(8.1), 0, 0, (fl + 0.2) * P), (ey(8.5), 0.5 * P, 0.4 * P, (fl + 0.2) * P),
                     (ey(9.3), 0.5 * P, 0.4 * P, (fl + 0.2) * P), (ey(9.7), 0, 0, (fl + 0.2) * P)],
                sides=6, mat_index=WING)

    # Neck (rows 11-16), darker grey, to the outline (columns 8 and 14 at rows 14-15).
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in ((11.5, 3.6, 2.5, 0.1), (16.4, 3.3, 2.4, 0.0))],
                sides=14, mat_index=NECK)
    # Red lights either side of the neck (columns 8 and 14, rows 12-13): round capsules.
    for s in (-1, 1):
        loft_path(bm, [(ey(11.6), s * 3.1 * P, 0, 0, 0.8 * P), (ey(12.0), s * 3.1 * P, 1.0 * P, 1.0 * P, 0.8 * P),
                       (ey(14.0), s * 3.1 * P, 1.0 * P, 1.0 * P, 0.8 * P), (ey(14.4), s * 3.1 * P, 0, 0, 0.8 * P)],
                  sides=8, mat_index=RED)

    # Rear fuselage (rows 16-24): round, about as tall as wide.
    hull = [(16.0, 3.3, 2.4, 0.0), (17.0, 3.9, 2.8, 0.0), (21.5, 4.35, 3.0, 0.0), (23.2, 3.6, 2.5, -0.1),
            (24.3, 2.6, 1.9, -0.2), (24.8, 0, 0, -0.2)]
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in hull], sides=14, mat_index=HULL)
    # Two ribs: bright strakes on the body's edges (columns 7 and 15), bright on both sides so
    # real. The bright streak at column 10, left of the centre line, is the round body's shine.
    strake = [(ey(r), w * P, 0.55 * P, 0.55 * P, z * P) for r, w, z in
              ((16.6, -3.4, 1.2), (17.5, -3.95, 1.3), (20.5, -4.1, 1.3), (21.8, -3.9, 1.1))]
    loft_path(bm, strake, sides=6, mat_index=BRIGHT)
    loft_path(bm, mirrored(strake), sides=6, mat_index=BRIGHT)

    # Swept wings, level at the fuselage's middle: a base plate cut to the sprite's outline in the
    # wing's grey (the game draws the dark edge), a raised bright leading-edge strip, a dark groove
    # behind it (a real panel line, dark on both wings), then a raised outer panel. Sprite (col, row) coordinates, left wing; d = row - col runs
    # across the leading edge (the outline at d = 8.6).
    outer = [(1.2, 11.2), (2.6, 11.2), (8.6, 17.2), (9.6, 17.2), (10.2, 25.8), (5.85, 25.8),
             (2.1, 18.5), (1.2, 18.1)]
    lead = clip(clip(clip(clip(outer, -1, 1, 10.5), 1, -1, -9.25), 1, 0, 7.9), 0, -1, -11.7)
    panel = clip(clip(clip(clip(outer, 1, -1, -11.7), -1, 0, -1.8), 0, -1, -12.0), 0, 1, 25.0)
    # Inside the trailing staircase: col >= 3.9 + (row - 19.5) / 2.
    panel = clip(clip(panel, -1, 0.5, -3.9 + 9.75), 1, 0, 7.3)
    groove = clip(clip(clip(outer, -1, 1, 11.7), 1, -1, -10.5), 1, 0, 7.9)
    for mirror in (False, True):
        plate(bm, outer, 0.2, 1.2, WING, mirror)
        plate(bm, groove, 0.3, 1.3, BASE, mirror)
        plate(bm, panel, 1.1, 1.7, WING, mirror)
        plate(bm, lead, 1.1, 1.9, LEAD, mirror)

    # Engine (rows 24-26): a dark nozzle 4 px wide (row 24), the red-orange exhaust plug in its
    # mouth (columns 10-12, row 25, hottest in the middle) and the nozzle's dark lower lip (row 26).
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in
                     ((23.6, 2.1, 1.5, -0.2), (25.0, 2.0, 1.4, -0.2))], sides=12, mat_index=BASE, cap_end=False)
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in
                     ((25.8, 1.9, 0.9, -0.5), (26.8, 1.7, 0.7, -0.5))], sides=12, mat_index=BASE)
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in
                     ((24.6, 1.65, 1.15, -0.2), (25.9, 1.65, 1.15, -0.2), (26.2, 1.2, 0.8, -0.2), (26.35, 0, 0, -0.2))],
                sides=12, mat_index=GLOW2)
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in
                     ((24.6, 0.75, 1.45, -0.2), (25.9, 0.75, 1.45, -0.2), (26.3, 0, 0, -0.2))],
                sides=8, mat_index=GLOW)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    # Move from the mirror axis to the sprite's column 11.
    for v in obj.data.vertices:
        v.co.x -= 0.5 * P
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
