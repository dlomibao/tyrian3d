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


def hard_loft(bm, sections, mat_index, flat):
    """A hard-surface body along +Y: each section is (row, side half width, top half width, top z,
    shoulder z, bottom half width, bottom z), all px, giving a flat top, chamfered shoulders,
    straight sides and a chamfered keel. Its faces are flagged flat-shaded so the edges stay crisp."""
    rings = []
    for r, w, tw, zt, zs, bw, zb in sections:
        pts = [(tw, zt), (w, zs), (w, zb + 0.8), (bw, zb), (-bw, zb), (-w, zb + 0.8), (-w, zs), (-tw, zt)]
        rings.append([bm.verts.new((x * P, ey(r), z * P)) for x, z in pts])
    n = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r1[i], r1[j], r0[j]))
            f.material_index = mat_index
            f[flat] = 1
    for ring, rev in ((rings[0], False), (rings[-1], True)):
        f = bm.faces.new(list(reversed(ring)) if rev else ring)
        f.material_index = mat_index
        f[flat] = 1


def ellipse_dome(bm, x0, y0, a, b, z0, height, mat_index, segs=20, rings=5):
    """A glass bubble: an elliptical dome (semi-axes a across, b along, px) rising `height` px from z0."""
    top = bm.verts.new((x0 * P, y0, (z0 + height) * P))
    loops = []
    for k in range(rings):
        phi = (k / rings) * math.pi / 2  # 0 at the base
        rr, zz = math.cos(phi), z0 + height * math.sin(phi)
        loops.append([bm.verts.new(((x0 + a * rr * math.cos(t)) * P, y0 + b * rr * math.sin(t) * P, zz * P))
                      for t in (2 * math.pi * i / segs for i in range(segs))])
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((l0[i], l0[j], l1[j], l1[i])).material_index = mat_index
    for i in range(segs):
        bm.faces.new((loops[-1][i], loops[-1][(i + 1) % segs], top)).material_index = mat_index
    bm.faces.new(list(reversed(loops[0]))).material_index = mat_index


def ellipse_frame(bm, y0, a, b, width, z0, z1, mat_index, flat, segs=20):
    """A flat elliptical rim around the canopy (inner semi-axes a, b; `width` px wide)."""
    def loop(ea, eb, z):
        return [bm.verts.new((ea * math.cos(t) * P, y0 + eb * math.sin(t) * P, z * P))
                for t in (2 * math.pi * i / segs for i in range(segs))]
    io, it = loop(a, b, z0), loop(a, b, z1)
    oo, ot = loop(a + width, b + width, z0), loop(a + width, b + width, z1)
    for i in range(segs):
        j = (i + 1) % segs
        for quad in ((it[i], it[j], ot[j], ot[i]), (ot[i], ot[j], oo[j], oo[i]), (io[i], io[j], it[j], it[i])):
            f = bm.faces.new(quad)
            f.material_index = mat_index
            f[flat] = 1


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
        pal(2, metallic=0.1, roughness=0.04),  # 5 dark cockpit glass, glossy
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
    flat = bm.faces.layers.int.new("flat")  # faces to flat-shade (hard edges)

    # Nose cone (rows 0-6), out to the sprite's outline: half width 0.5 * row + 0.5 px covers
    # the staircase's dark edge pixels and none beyond. Round, a little taller than half its width.
    nose = [(-0.4, 0, 0, 0.5), (0.4, 0.7, 0.55, 0.5), (2.0, 1.5, 1.15, 0.45), (4.0, 2.5, 1.9, 0.4),
            (6.0, 3.5, 2.65, 0.35), (6.9, 3.9, 2.85, 0.3)]
    # Its bright streak (columns 10-11, rows 3-6) is the polished cone's shine: no geometry for it.
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in nose], sides=12, mat_index=NOSE)

    # Cockpit housing (rows 7-11): a round collar, and on it the round dark glass bubble (columns
    # 9-13, rows 7-10, about 3x4 px inside a bright frame) raised above the collar. The lighter
    # centre pixel is the glossy glass's glint: no geometry for it.
    common_ring = (4.25, 2.9, 0.3)
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in
                     ((6.6, 3.8, 2.75, 0.3), (7.0, *common_ring), (11.0, *common_ring), (11.7, 4.15, 2.8, 0.25),
                      (12.1, 3.4, 2.4, 0.2))], sides=14, mat_index=RING)
    cy = ey(9.0)
    ellipse_frame(bm, cy, 1.55, 2.0, 0.55, 2.4, 3.55, RING, flat)
    ellipse_dome(bm, 0.0, cy, 1.6, 2.05, 2.9, 1.7, COCKPIT)

    # Neck (rows 11-16), darker grey, to the outline (columns 8 and 14 at rows 14-15).
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in ((11.5, 3.6, 2.5, 0.1), (16.4, 3.3, 2.4, 0.0))],
                sides=14, mat_index=NECK)
    # Red lights either side of the neck (columns 8 and 14, rows 12-13): round capsules.
    for s in (-1, 1):
        loft_path(bm, [(ey(11.6), s * 3.1 * P, 0, 0, 0.8 * P), (ey(12.0), s * 3.1 * P, 1.0 * P, 1.0 * P, 0.8 * P),
                       (ey(14.0), s * 3.1 * P, 1.0 * P, 1.0 * P, 0.8 * P), (ey(14.4), s * 3.1 * P, 0, 0, 0.8 * P)],
                  sides=8, mat_index=RED)

    # Rear fuselage (rows 16-24): a hard, straight-sided body (flat top, chamfered shoulders,
    # straight sides, a keel), widest between the wings and tapering at the tail into the nozzle.
    # (row, side half width, top half width, top z, shoulder z, keel half width, keel z)
    common.loft(bm, [(ey(r), w * P, h * P, z * P) for r, w, h, z in ((15.9, 3.3, 2.4, 0.0), (16.6, 3.3, 2.4, 0.0))],
                sides=14, mat_index=NECK)
    hard_loft(bm, [(16.3, 3.4, 2.0, 2.7, 1.5, 1.8, -2.4), (17.2, 4.0, 2.4, 3.1, 1.9, 2.2, -2.8),
                   (21.6, 4.2, 2.5, 3.2, 2.0, 2.3, -2.9), (23.3, 3.5, 2.0, 2.7, 1.6, 1.9, -2.5),
                   (24.4, 2.4, 1.4, 2.0, 1.1, 1.3, -1.9)], HULL, flat)
    # Bright strakes on the shoulders (columns 7 and 15, rows 17-21): crisp square ribs standing on
    # the shoulder chamfer's outer edge.
    strake = [(ey(r), w * P, 0.55 * P, 0.6 * P, z * P) for r, w, z in
              ((16.6, -3.45, 1.9), (17.4, -3.95, 2.3), (21.0, -4.1, 2.4), (22.3, -3.85, 2.2))]
    for side in (strake, mirrored(strake)):
        start = len(bm.faces)
        loft_path(bm, side, sides=4, mat_index=BRIGHT)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[start:]:
            f[flat] = 1
    # The faint spine down the middle of the top (rows 17-23): a low ridge with a peaked top, whose
    # lit left face is the sprite's lighter column 10.
    spine = [(17.0, 0.0, 3.1), (17.4, 0.7, 3.1), (21.8, 0.75, 3.2), (23.3, 0.55, 2.7), (23.8, 0.0, 2.6)]
    rows = []
    for r, w, z in spine:
        rows.append([bm.verts.new((x * P, ey(r), zz * P)) for x, zz in
                     ((-w, z - 0.1), (0.0, z + 0.55 * (w > 0)), (w, z - 0.1))])
    for r0, r1 in zip(rows, rows[1:]):
        for i in range(2):
            f = bm.faces.new((r0[i], r1[i], r1[i + 1], r0[i + 1]))
            f.material_index = BRIGHT
            f[flat] = 1

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
    wing_start, wing_faces = len(bm.verts), len(bm.faces)
    for mirror in (False, True):
        plate(bm, outer, 0.2, 1.2, WING, mirror)
        plate(bm, groove, 0.3, 1.3, BASE, mirror)
        plate(bm, panel, 1.1, 1.7, WING, mirror)
        plate(bm, lead, 1.1, 1.9, LEAD, mirror)
    # Tilted up toward the tips (a slight dihedral outboard of the body's sides).
    bm.verts.ensure_lookup_table()
    for v in bm.verts[wing_start:]:
        v.co.z += max(0.0, abs(v.co.x) - 3.6 * P) * 0.18
    bm.faces.ensure_lookup_table()
    for f in bm.faces[wing_faces:]:
        f[flat] = 1

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
    # Hard-surface faces flat shaded, so their edges stay crisp; the round parts stay smooth.
    attr = obj.data.attributes["flat"]
    for poly, a in zip(obj.data.polygons, attr.data):
        if a.value:
            poly.use_smooth = False
    obj.data.attributes.remove(attr)
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
