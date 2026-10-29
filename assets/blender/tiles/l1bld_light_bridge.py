"""The light bridge of map 1-3's ground (shapesz.dat; 5 x 13 tiles, map rows 132-136, cols 1-13),
after the concept assets/blender/features/concepts/l1-bld-light-bridge.jpg: a long paved platform
ringed by a rocky rim, its middle section (cols 4-9, between the rim's notches) a raised body with a
bump at the top; across it a framed trough of 24 red light capsules (the 339 x 8 strip), at its ends
two dark round pads with bronze clamps (305 306 / 315 316), and on the raised bump four round seats
(358 357 357 358). The game draws ground enemies over the strip (newshs 195), the pads (newshs
39/41/85/87) and the seats (newshd 275/127) at 0.45, so all of these stay under ENEMY_MAX.

Built with lib_l1bld.py (the worked example is l1bld_bunker.py). Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/l1bld_light_bridge.py
    python tools/concept_maps.py tile:shapesz-l1bld-light-bridge --concept l1-bld-light-bridge
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-l1bld-light-bridge
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_l1bld as lb  # noqa: E402
import lib_tiles as lt  # noqa: E402

WING_DECK = 0.30  # the paving of the two wings (cols 0-3 and 10-12)
BODY = (96, 0, 240, 140)  # the raised middle body: cols 4-9, the rim's notches mark its sides
BODY_TOP = 0.34
CHAMFER_PX = 2
STRIP = (71, 59, 265, 83)  # the red lights' frame (8 cells of 339, pattern row 2)
STRIP_FLOOR = 0.30  # the trough the capsules lie in
STRIP_FRAME = 0.36
CAPSULES = 24  # three per tile, 8 px apart
PADS = ((46.0, 84.0), (286.0, 84.0))  # centres of the two dark pads (2 x 2 cells each)
PAD_R = 18.5
SEATS = ((132, 42), (156, 42), (180, 42), (204, 42))  # the four orb seats on the bump
PAVE = 4  # the woven paving: darker than PAL["pave"] (6), as in the sprite's dark weave
PAVE_BODY = 5
BRONZE = 165  # the sprite's brackets and outer seats are browns 160-165


def disc(b, px, py, r_px, z0, z1, mat, sides=20, bevel_px=1.0):
    """A closed round plate (pixel centre and radius) from z0 to z1 with a chamfered top edge."""
    bm = bmesh.new()
    cx, cy = b.x(px), b.y(py)

    def ring(r, z):
        return [bm.verts.new((cx + r * lt.PX * math.cos(2 * math.pi * i / sides),
                              cy + r * lt.PX * math.sin(2 * math.pi * i / sides), z)) for i in range(sides)]

    base = ring(r_px, z0)
    edge = ring(r_px, z1 - bevel_px * lt.PX * 0.5)
    top = ring(r_px - bevel_px, z1)
    bm.faces.new(top).material_index = mat
    bm.faces.new(list(reversed(base))).material_index = mat
    for a, c in ((base, edge), (edge, top)):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((a[i], a[j], c[j], c[i])).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)


def capsule(b, px, py, length, radius, z_top, mat, sides=6, steps=2, flat=0.4):
    """A low-poly red capsule lying along y (lib_l1bld.capsule is ~160 triangles; 24 of them are
    the whole budget here): a cylinder with rounded ends, its top at z_top, squashed to `flat` of
    its width so it bulges a little out of the trough instead of standing in it."""
    r = radius * lt.PX
    half = max(0.0, length / 2 * lt.PX - r)
    zc = z_top - r * flat
    cx, cy = b.x(px), b.y(py)
    bm = bmesh.new()
    prof = [(-half - r * math.sin(math.pi / 2 * (1 - i / steps)), r * math.cos(math.pi / 2 * (1 - i / steps)))
            for i in range(steps)]
    prof += [(half + r * math.sin(math.pi / 2 * i / steps), r * math.cos(math.pi / 2 * i / steps))
             for i in range(1, steps + 1)]
    rings = []
    for t, rad in prof:
        rad = max(rad, 0.15 * r)
        rings.append([bm.verts.new((cx + rad * math.cos(2 * math.pi * j / sides + math.pi / sides), cy + t,
                                    zc + flat * rad * math.sin(2 * math.pi * j / sides + math.pi / sides)))
                      for j in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(sides):
            k = (j + 1) % sides
            bm.faces.new((r0[j], r0[k], r1[k], r1[j])).material_index = mat
    bm.faces.new(rings[0]).material_index = mat
    bm.faces.new(list(reversed(rings[-1]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm, smooth=True)


def bar(b, px, py, angle, length, width, z0, z1, mat):
    """A straight bevelled bar through (px, py) at `angle` (radians, pixel frame, y down)."""
    ca, sa = math.cos(angle), math.sin(angle)
    hl, hw = length / 2, width / 2
    bev = min(0.8, hw * 0.6)
    bm = bmesh.new()

    def ring(inset, z):
        out = []
        for u, w in ((-hl + inset, -hw + inset), (hl - inset, -hw + inset), (hl - inset, hw - inset), (-hl + inset, hw - inset)):
            out.append(bm.verts.new((b.x(px + u * ca - w * sa), b.y(py + u * sa + w * ca), z)))
        return out

    base, edge, top = ring(0, z0), ring(0, z1 - bev * lt.PX * 0.5), ring(bev, z1)
    bm.faces.new(top).material_index = mat
    bm.faces.new(list(reversed(base))).material_index = mat
    for a, c in ((base, edge), (edge, top)):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((a[i], a[j], c[j], c[i])).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)


def arc_block(b, px, py, r0, r1, a0, a1, z0, z1, mat, steps=8, bevel_px=0.8):
    """A closed annular sector (radii r0..r1 px, angles a0..a1 degrees in the pixel frame, y down)
    from z0 to z1 with a chamfered top: the pads' bronze brackets."""
    bm = bmesh.new()
    angs = [math.radians(a0 + (a1 - a0) * i / steps) for i in range(steps + 1)]

    def pt(r, a, z):
        return bm.verts.new((b.x(px + r * math.cos(a)), b.y(py + r * math.sin(a)), z))

    # Cross-section loop (inner-bottom, outer-bottom, outer-edge, outer-top, inner-top, inner-edge).
    zc = z1 - bevel_px * lt.PX * 0.5
    sec = [(r0, z0), (r1, z0), (r1, zc), (r1 - bevel_px, z1), (r0 + bevel_px, z1), (r0, zc)]
    loops = [[pt(r, a, z) for r, z in sec] for a in angs]
    n = len(sec)
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((l0[i], l0[j], l1[j], l1[i])).material_index = mat
    bm.faces.new(loops[0]).material_index = mat
    bm.faces.new(list(reversed(loops[-1]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)


def smooth_outline(b, radius=4, thresh=0.4):
    """The painted footprint's outline follows the rim tiles' rocks pixel by pixel, which the terrace
    shows as stair steps. Blur it (box blur, 3 passes) and threshold: a rounder outline that still
    contains the whole painted footprint (and stays inside the covered cells)."""
    f = b.footprint.astype(lb.np.float32)
    k = 2 * radius + 1
    for _ in range(3):
        p = lb.np.pad(f, radius, mode="constant")
        c = lb.np.cumsum(lb.np.cumsum(p, 0), 1)
        c = lb.np.pad(c, ((1, 0), (1, 0)))
        f = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
    return ((f > thresh) & b.cover) | b.footprint


def main():
    b = lb.Building("light-bridge")
    b.footprint = smooth_outline(b, radius=6)  # local only: the deck, rim rocks and check all use it
    b.surface(deck=WING_DECK, channel=False, pits=False, red=False)
    b.set_region(b.footprint, WING_DECK, b.m(PAVE))
    x0, y0, x1, y1 = BODY
    # The raised middle body with a chamfer step on its sides.
    b.raise_box(x0, y0, x1, y1, BODY_TOP - 0.02, b.m(PAVE))
    b.raise_box(x0 + CHAMFER_PX, y0, x1 - CHAMFER_PX, y1, BODY_TOP, b.m(PAVE_BODY))
    # The red lights' trough: a light frame round a recessed dark floor.
    sx0, sy0, sx1, sy1 = STRIP
    b.raise_box(sx0, sy0, sx1, sy1, STRIP_FRAME, b.m("metal"))
    b.raise_box(sx0 + 2, sy0 + 2, sx1 - 2, sy1 - 2, STRIP_FLOOR, b.m("red_dark"))
    # The pads: shallow round wells in the wings (the pad itself is a part, below).
    for px, py in PADS:
        yy, xx = lb.np.mgrid[0:b.H, 0:b.W]
        well = (xx + 0.5 - px) ** 2 + (yy + 0.5 - py) ** 2 <= (PAD_R + 1.5) ** 2
        b.set_region(well, WING_DECK, b.m("dark"))
    deck = b.terrace()

    # 24 capsules standing across the strip (along y), as in the tiles and the concept.
    pitch = (sx1 - sx0 - 2) / CAPSULES
    for i in range(CAPSULES):
        cx = sx0 + 1 + pitch * (i + 0.5)
        capsule(b, cx, (sy0 + sy1) / 2, 17, 3.2, 0.37, b.m("red"), sides=6)

    # The pads: a dark wheel with a raised dark rim, a raised spoke cross (the sprite's X marks) and
    # big bronze brackets wrapping its left and right sides, as in the sprite and the concept.
    bronze = b.m(BRONZE, roughness=0.35, metallic=0.75)
    for px, py in PADS:
        disc(b, px, py, PAD_R, WING_DECK - 0.03, 0.33, b.m("dark", roughness=0.35, metallic=0.4), sides=24)
        disc(b, px, py, PAD_R * 0.78, 0.32, 0.335, b.m(1, roughness=0.5, metallic=0.3), sides=20)
        for a in (math.pi / 4, 3 * math.pi / 4):  # the X
            bar(b, px, py, a, PAD_R * 1.45, 2.6, 0.32, 0.355, b.m(3, roughness=0.4, metallic=0.6))
        for k in range(4):  # short spokes between the X's arms
            a = k * math.pi / 2
            bar(b, px + math.cos(a) * PAD_R * 0.45, py + math.sin(a) * PAD_R * 0.45, a, PAD_R * 0.45, 1.6,
                0.32, 0.345, b.m(2, roughness=0.5, metallic=0.5))
        disc(b, px, py, 4.0, 0.33, 0.362, b.m(4, roughness=0.35, metallic=0.6), sides=12)
        arc_block(b, px, py, PAD_R - 4.0, PAD_R + 2.5, 100, 205, WING_DECK - 0.03, 0.372, bronze)
        arc_block(b, px, py, PAD_R - 4.0, PAD_R + 2.5, -25, 80, WING_DECK - 0.03, 0.372, bronze)
        # the bronze strap across the pad's lower half (the sprite's brown dotted line)
        b.wall_block(px - PAD_R + 2, py + 8, px + PAD_R - 2, py + 10.5, 0.32, 0.35, bronze, bevel=0.3)

    # The orb seats on the bump: bronze housings on the outer two, silver orbs on the inner two (the
    # sprite's bronze-silver-silver-bronze rhythm), each with a red light. Enemies (newshd 275/127)
    # are drawn over them, so they show once those are destroyed.
    for i, (px, py) in enumerate(SEATS):
        if i in (0, 3):
            disc(b, px, py, 10.5, BODY_TOP - 0.03, 0.355, bronze, sides=16)
            disc(b, px, py, 6.5, 0.35, 0.364, b.m(1, roughness=0.25, metallic=0.5), sides=12)
            for side in (-1, 1):  # the red side lamps
                b.dome(px + side * 10.5, py, 2.0, 2.6, 0.33, 0.035, b.m("red"), sides=8, rings=2)
            b.dome(px, py + 7, 2.2, 2.2, 0.35, 0.02, b.m("red"), sides=8, rings=2)
        else:
            disc(b, px, py, 10.5, BODY_TOP - 0.03, 0.35, b.m(4, roughness=0.35, metallic=0.6), sides=16)
            b.dome(px, py, 9.0, 9.0, 0.345, 0.03, b.m(9, roughness=0.25, metallic=0.8), sides=16, rings=3)
            b.dome(px, py, 2.4, 2.4, 0.372, 0.006, b.m("red_dark", emission_strength=1.2), sides=8, rings=1)

    # The rim: big and small rocks in two rows.
    def keep(px, py):  # no rocks on the pads
        return all((px - qx) ** 2 + (py - qy) ** 2 > (PAD_R + 4) ** 2 for qx, qy in PADS)

    n1 = b.rim_rocks(spacing=10.0, inset=4.0, size=(0.55, 0.85), height=(0.38, 0.48), sink=0.10, sides=(5, 6), keep=keep)
    n2 = b.rim_rocks(spacing=16.0, inset=10.0, size=(0.40, 0.55), height=(0.35, 0.41), sink=0.06, sides=(4, 5), keep=keep)
    # The notches' sides under the wings (the rim tiles 382 / 380 at cols 3-4 and 9-10): a close row
    # of small rocks so the deck's side wall there doesn't show as stair steps.
    def notch(px, py):
        return py > 90 and (88 < px < 112 or 228 < px < 256) and keep(px, py)

    n3 = b.rim_rocks(spacing=6.0, inset=3.0, size=(0.6, 0.85), height=(0.38, 0.46), sink=0.10, sides=(5, 5), keep=notch)
    print("rocks", n1, n2, n3)
    objects = b.objects(deck)
    b.check(objects)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects)
    print(f"light-bridge: {tris} triangles", [(o.name, sum(len(p.vertices) - 2 for p in o.data.polygons)) for o in objects])
    b.export(objects)


main()
