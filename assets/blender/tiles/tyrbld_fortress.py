"""TYRIAN's fortress (map 1-9, layer 2, map rows 334-378, the whole map width): the grey metal
walkways that frame its rock islands, and the red machine beside the vertical walkway, after the
concepts assets/blender/features/concepts/tyr-fortress-a.jpg, -b.jpg and -c.jpg (three overlapping
crops, top to bottom; concept_maps.py registers each onto its own cells).

The pattern is only the walkway (180-201) and machine (160/161/170/171) cells; the rock, purple
blocks, lava pits and craters inside the fortress are other entries or stay on the per-tile models.
What the art and the concepts draw, and how it is built:

- the walkway: a metal deck at L2_DECK over every walkway pixel (the tiles' own outline, so the
  rounded corners and T-junctions come from the art), its slab down to the islands' slab bottom;
  the rails are the art's bright strips (the edges of each walkway row: on the double row 17-18
  they meet in a broken middle strip, as drawn) raised a little, with studs along them as the
  concepts show; the maze pattern is the bake's;
- the machine (cells 20-21 / 2-3, under enemies newsh2 15/17/53/55, seen after they are killed): a
  wrecked block of red armour panels on a dark frame with brass pipes, everything under
  L2_ENEMY_MAX, on the rock the machine tiles paint around it;
- a low round mount on the walkway under the enemy at (30, 5), so it sits on something
  (L2_ENEMY_MIN..L2_ENEMY_MAX).

Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_fortress.py
    python tools/concept_maps.py tile:shapesz-tyrbld-fortress --part tyr-fortress-a:-1,0,16,14 \
        --part tyr-fortress-b:15,0,31,14 --part tyr-fortress-c:29,0,45,14
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-fortress --size 4096
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import math  # noqa: E402

import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import lib_l1bld as lb  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402

RAIL_H = 0.05  # the rails stand this much above the deck
RAIL_LUM = 8  # grey indices from here up are the rails' bright metal (the maze is 4-7)
#: The machine's armour (pattern px polygons, clockwise on screen): (points, base z, top z at the
#: polygon's centre, top slope (dz per px right, dz per px down), chamfer px, material). After the
#: art's red panels and brass parts; tilted and chamfered so each reads as its own raised plate.
MACHINE_PLATES = [
    # the burnt-out casing under everything: a broken, irregular outline
    ([(57, 567), (66, 565), (75, 568), (77, 580), (74, 590), (70, 597), (63, 599), (57, 593), (56, 580)], 0.08, 0.17, (0.002, 0.001), 1.5, "dark"),
    # top-left housing, its top falling to the left (the art's light diagonal edge)
    ([(51, 567), (55, 562), (62, 562), (63, 571), (60, 577), (52, 578)], 0.12, 0.27, (0.005, 0.002), 2.0, "red"),
    # top-right block, falling to the right
    ([(68, 566), (77, 565), (79, 570), (77, 576), (69, 577)], 0.12, 0.27, (-0.006, 0.002), 1.8, "red"),
    # the right bracket: a bent L, sloping down screen-down
    ([(73, 575), (85, 574), (87, 578), (86, 591), (82, 594), (80, 580), (73, 579)], 0.10, 0.23, (0.0, -0.004), 1.2, "red_dark"),
    # the left frame: a bent brass L
    ([(49, 577), (59, 576), (59, 580), (53, 581), (52, 600), (49, 598)], 0.10, 0.21, (0.003, -0.002), 1.0, "brass_dark"),
    # lower brass block, canted
    ([(55, 592), (61, 591), (62, 603), (58, 607), (55, 601)], 0.10, 0.21, (0.004, -0.003), 1.3, "brass"),
    # lower red block, canted the other way
    ([(60, 598), (67, 596), (69, 606), (63, 609), (59, 604)], 0.12, 0.25, (-0.005, 0.004), 1.5, "red"),
    # torn armour shards over the core
    ([(64, 581), (70, 579), (71, 584), (66, 587)], 0.14, 0.22, (0.008, -0.006), 0.8, "red_dark"),
    ([(58, 583), (62, 582), (63, 588), (59, 590)], 0.12, 0.19, (-0.007, 0.004), 0.7, "dark"),
]
#: The bent brass pipe through the core (px, py, z), from the top-right block round to the bottom.
MACHINE_PIPE = [(71.5, 577.0, 0.19), (72.5, 583.0, 0.20), (71.0, 589.0, 0.19), (67.0, 593.5, 0.18), (62.0, 594.5, 0.17)]
MOUNT = (132.0, 854.0, 8.0)  # the enemy's mount on cell (30, 5): centre px, radius px
MOUNT_TOP = 0.24


def walkways(s):
    """The deck over the walkway pixels with the art's bright strips as rails (and studs)."""
    walk = s.walkway(rail_px=2, rail_h=RAIL_H)  # deck + an outline rail ...
    # ... but the rails follow the art: its bright grey strips (both edges of each walkway row, the
    # middle strip on the double row, the corners' rounded rims).
    g = s.grid
    bright = walk & (g >= RAIL_LUM) & (g < 16)
    bright = lb.drop_small(lb.close(bright, 1), 10)
    s.set_region(walk, s.deck, s.m("walk"))
    s.set_region(bright, s.deck + RAIL_H, s.m("rail"))
    s._rail = bright
    s.rail_studs(spacing=12.0, radius_px=1.5, height=0.025)
    return walk


def fill_holes(mask):
    """`mask` with its enclosed holes filled."""
    out = mask.copy()
    H, W = mask.shape
    for ys, xs in lt.components(~mask):
        if ys.min() > 0 and xs.min() > 0 and ys.max() < H - 1 and xs.max() < W - 1:
            out[ys, xs] = True
    return out


def plate(s, pts, z0, z1, slope, chamfer_px, mat):
    """A raised armour plate: the polygon `pts` (pattern px) from z0 up to a tilted top (z1 at its
    centre, `slope` = dz per px right / down), with a chamfered rim `chamfer_px` wide."""
    bm = bmesh.new()
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)

    mx, my = s.x(cx), s.y(cy)

    def top(co):  # model y runs up the screen, py down it
        return z1 + slope[0] * (co.x - mx) / lt.PX - slope[1] * (co.y - my) / lt.PX

    ch = chamfer_px * lt.PX
    base = [bm.verts.new((s.x(px), s.y(py), z0)) for px, py in pts]
    face = bm.faces.new(base)
    face.normal_update()
    if face.normal.z < 0:
        face.normal_flip()
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    for v in (g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)):
        v.co.z = top(v.co) - ch
    tops = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.inset_region(bm, faces=tops, thickness=ch, depth=ch, use_even_offset=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.material_index = mat
    s._merge(bm)


def tube(s, path, r_px, mat, sides=10):
    """A pipe of radius r_px along the polyline `path` [(px, py, z)], ends capped."""
    bm = bmesh.new()
    pts = [Vector((s.x(px), s.y(py), z)) for px, py, z in path]
    r = r_px * lt.PX
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        u = d.cross(Vector((0, 0, 1))).normalized()
        w = u.cross(d).normalized()
        rings.append([bm.verts.new(p + r * (math.cos(2 * math.pi * k / sides) * u + math.sin(2 * math.pi * k / sides) * w)) for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.material_index = mat
        f.smooth = True
    s._merge(bm)


def machine(s):
    """The wrecked red machine on cells (20-21, 2-3): its outline is where the art's red panels and
    brass parts cluster (closed and filled), not the black gaps between the stones round it."""
    cells = s.cells_mask(tb.MACHINE)
    g = s.grid
    ramp = np.maximum(g, 0) >> 4
    seed = cells & (g >= 0) & np.isin(ramp, (1, 4, 10))
    body = lb.drop_small(fill_holes(lb.close(lb.drop_small(seed, 4), 2)), 80) & cells
    body = lb.open_(body, 1)
    core = body & (g >= 0) & (g <= 2)
    s.set_region(body, 0.14, s.m(2))  # the machine's dark frame
    s.set_region(lb.erode(core, 1), 0.08, s.m(1))  # the burnt-out core, recessed
    red = s.m(s.dominant(body & (ramp == 4)), metallic=0.35, roughness=0.45)
    red_dark = s.m(67, metallic=0.35, roughness=0.5)
    brass, brass_dark, cap = s.m("brass"), s.m("brass_dark"), s.m(11, metallic=0.6, roughness=0.35)
    mats = {"red": red, "red_dark": red_dark, "brass": brass, "brass_dark": brass_dark, "dark": s.m(3, metallic=0.4, roughness=0.5)}
    for pts, z0, z1, slope, ch, mat in MACHINE_PLATES:
        plate(s, pts, z0, z1, slope, ch, mats[mat])
    # Exhaust caps on the top housings, and the bent brass pipe across the core.
    for px, py in ((56.0, 562.5), (78.0, 564.0)):
        s.lathe([(0.0, 2.4), (1.9, 2.4), (1.9, 1.6), (2.2, 1.0)], px, py, axis="z", z=0.12, mat=cap, sides=10)
    tube(s, MACHINE_PIPE, 1.6, brass)
    # Rock round it (the machine tiles paint stones round the machine).
    s.rock(cells=[(r, c) for r in (20, 21) for c in (2, 3)], exclude=lb.dilate(body, 1), cut=body)
    return body


def mount(s):
    px, py, r = MOUNT
    s.knob(px, py, r, s.deck - 0.02, MOUNT_TOP - 0.03, mat=s.m("metal"), sides=8)
    s.knob(px, py, r * 0.7, MOUNT_TOP - 0.04, MOUNT_TOP, mat=s.m("walk_dark"), sides=8)


def build():
    s = tb.Structure("fortress")
    walkways(s)
    machine(s)
    mount(s)
    objects = s.objects()
    s.check(objects)
    s.export(objects)


build()
