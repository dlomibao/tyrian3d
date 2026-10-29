"""The armoured hull bunker on TYRIAN's ground (map 1-9, layer 0; tiles 322 323 / 332 333, three
copies), after the concept assets/blender/features/concepts/tyr-bunker-hull.jpg: a grey, rounded
armoured hood at the top, a brass chevron collar over its front, brass pipes curling down both
flanks, brass clamp plates and brackets across the middle (the "7" and the bar), and below them the
machinery: a grey block and column on the left, a ribbed drum in the middle, a slotted grey slab and
a ribbed cylinder on the right, all on a dark machine bed in the dirt.

Every cell carries a ground enemy (assembly-newsh2-119, the grey carapace bunker) drawn at 0.45, so
the whole model stays under ENEMY_MAX (0.38); it shows once the enemy is killed. The tiles stay drawn
(keepTiles), so the model covers only the bunker's own outline, not the dirt round it.

Geometry is placed in pattern pixels read off the registered concept (concept_maps.py with the span
below, which lines the concept's hood and chevron up with the tiles' own). Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_bunker_hull.py
    python tools/concept_maps.py tile:shapesz-tyrbld-bunker-hull --concept tyr-bunker-hull --span 0.03,0.07,1.15,0.83 --px 32
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-bunker-hull
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import numpy as np  # noqa: E402

import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402

BED = 0.10  # the dark machine bed under everything
HOOD = dict(x0=10.0, x1=31.5, y0=3.0, y1=20.8, round_px=4.5, top=0.33)
CHEVRON_TOP, CHEVRON_BASE = 0.37, 0.06
# The chevron collar's outline (pattern px), with the notch in its inner edge right of the apex.
CHEVRON = [(10.0, 26.6), (10.0, 23.4), (20.2, 13.2), (30.8, 23.4), (30.8, 26.6), (28.6, 26.6), (22.3, 20.3),
           (22.0, 23.0), (21.4, 23.0), (18.2, 19.6), (11.2, 26.6)]
# The brass clamp plates across the middle: the "7" on the left and the bar with its bracket.
SEVEN = [(14.3, 28.3), (16.8, 25.8), (17.6, 25.8), (19.4, 27.5), (19.4, 30.3), (20.6, 30.3), (20.6, 31.6),
         (19.4, 31.6), (19.4, 35.5), (17.5, 35.5), (17.5, 30.6), (14.3, 30.6)]
BAR = [(21.2, 28.4), (26.4, 28.4), (28.4, 26.2), (30.6, 26.2), (30.6, 32.3), (28.8, 32.3), (28.8, 30.6),
       (21.2, 30.6)]
PLATE_TOP = 0.31
# Brass pipes on the flanks: (start, elbow, end) in px, from the hood down and out to the dirt.
PIPES = [
    [(10.5, 10.0, 0.13), (4.8, 14.0, 0.13), (3.8, 17.6, 0.02)],
    [(10.5, 17.0, 0.13), (5.4, 21.0, 0.13), (4.6, 24.4, 0.02)],
    [(31.0, 10.0, 0.13), (36.6, 14.0, 0.13), (37.6, 17.6, 0.02)],
    [(31.0, 17.0, 0.13), (36.0, 21.0, 0.13), (36.8, 24.4, 0.02)],
]
PIPE_R, PIPE_Z = 0.85, 0.13


def plate(s, poly, z0, z1, mat, chamfer_px=0.6, top_mat=None):
    """A flat plate over the plan polygon `poly` (pattern px, clockwise on screen) from z0 to z1,
    its top edge chamfered `chamfer_px` in and down."""
    bm = bmesh.new()
    c = chamfer_px * lt.PX
    base = [bm.verts.new((s.x(px), s.y(py), z0)) for px, py in poly]
    face = bm.faces.new(base)
    face.material_index = mat
    if face.normal.z > 0:
        face.normal_flip()
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    top_verts = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    for v in top_verts:
        v.co.z = z1 - c
    top = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMFace)][0]
    bmesh.ops.inset_region(bm, faces=[top], thickness=c, depth=0.0, use_even_offset=True)
    for v in top.verts:
        v.co.z = z1
    top.material_index = mat if top_mat is None else top_mat
    for f in bm.faces:
        if f is not top and f.material_index != mat:
            f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def tube(s, pts, r_px, mat, sides=8):
    """A pipe along the polyline `pts` [(px, py, z)]: a cylinder per segment, a ball joint at each
    bend."""
    r = r_px * lt.PX
    for (ax, ay, az), (bx, by, bz) in zip(pts, pts[1:]):
        p0 = np.array([s.x(ax), s.y(ay), az])
        p1 = np.array([s.x(bx), s.y(by), bz])
        d = p1 - p0
        L = np.linalg.norm(d)
        if L < 1e-6:
            continue
        d /= L
        u = np.cross(d, [0, 0, 1.0])
        u /= np.linalg.norm(u)
        w = np.cross(u, d)
        bm = bmesh.new()
        rings = []
        for p in (p0, p1):
            rings.append([bm.verts.new(tuple(p + r * (math.cos(2 * math.pi * i / sides) * u + math.sin(2 * math.pi * i / sides) * w)))
                          for i in range(sides)])
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i])).material_index = mat
        bm.faces.new(rings[0]).material_index = mat
        bm.faces.new(list(reversed(rings[1]))).material_index = mat
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        s._merge(bm, smooth=True)
    for px, py, z in pts[1:-1]:
        s.dome(px, py, r_px * 1.15, r_px * 1.15, z - r * 1.1, r * 2.2, mat, sides=8, rings=3)


def ribbed(n, length, r, rib_r, start=0.0):
    """A lathe profile [(t, r)] of `n` ribs along `length` px: rings of radius rib_r between
    grooves of radius r."""
    prof = [(start, r * 0.6), (start, r)]
    step = length / n
    for i in range(n):
        t = start + i * step
        prof += [(t + step * 0.2, rib_r), (t + step * 0.7, rib_r), (t + step * 0.8, r)]
    prof += [(start + length, r), (start + length, r * 0.6)]
    return prof


def main():
    s = tb.Structure("bunker-hull")
    metal, metal_dark, metal_light = s.m("metal"), s.m(6, metallic=0.5, roughness=0.5), s.m(11, metallic=0.6, roughness=0.35)
    dark = s.m("dark")
    brass, brass_dark, brass_light = s.m("brass"), s.m("brass_dark"), s.m("brass_light")

    # The bunker's own outline on the dirt: the hood, the body below it, the clamps either side.
    h = HOOD
    outline = s.box_mask(h["x0"], h["y0"] + h["round_px"], h["x1"], 50.0)
    outline |= s.box_mask(h["x0"] + h["round_px"], h["y0"], h["x1"] - h["round_px"], h["y0"] + h["round_px"])
    for cx in (h["x0"] + h["round_px"], h["x1"] - h["round_px"]):
        outline |= s.ellipse_mask(cx, h["y0"] + h["round_px"], h["round_px"], h["round_px"])
    outline |= s.box_mask(12.5, 50.0, 30.5, 51.5)
    outline |= s.box_mask(6.0, 26.0, h["x0"], 32.0) | s.box_mask(h["x1"], 26.0, 36.5, 32.0)
    s.set_footprint(outline)
    s.set_region(outline & ~s.box_mask(0, 0, s.W, 19.0), BED, dark)

    # Box-like machinery in the deck (terraced): the left block and column, the left grille box,
    # the slotted slab, and the clamp boxes at the sides.
    s.raise_box(10.0, 31.4, 17.6, 35.6, 0.30, metal)
    s.raise_box(13.6, 35.6, 17.2, 46.6, 0.28, metal_dark)
    s.raise_box(10.2, 41.0, 13.6, 46.4, 0.22, metal_dark)
    s.raise_box(22.0, 33.0, 26.6, 50.8, 0.34, metal)
    for x0 in (23.0, 24.9):
        s.raise_box(x0, 35.0, x0 + 0.9, 48.0, 0.29, dark)
    s.raise_box(22.6, 48.8, 26.0, 50.4, 0.30, metal_dark)
    s.raise_box(33.0, 27.0, 36.4, 31.6, 0.24, metal)  # right grey box
    s.raise_box(33.6, 28.0, 35.6, 30.8, 0.20, dark)
    s.raise_box(6.0, 26.4, 8.4, 27.8, 0.20, brass)  # left bracket's prongs
    s.raise_box(6.0, 29.0, 8.4, 30.4, 0.20, brass)
    s.raise_box(8.2, 26.0, 10.6, 32.0, 0.24, brass_dark)
    s.raise_box(30.6, 26.4, 33.0, 32.0, 0.24, brass_dark)
    deck = s.terrace(wall_mat=metal_dark)

    # The hood: a squashed half-cylinder lying along the screen's Y, its far end rounded.
    r = (h["x1"] - h["x0"]) / 2
    cx = (h["x0"] + h["x1"]) / 2
    length = h["y1"] - h["y0"]
    prof = []
    for i in range(6):
        a = math.pi / 2 * i / 5
        prof.append((h["round_px"] * (1 - math.sin(a)) * 1.0, r * (0.55 + 0.45 * math.sin(a))))
    prof = [(h["round_px"] - t, rr) for t, rr in prof]  # t from the far end (screen top) down
    prof = [(t, rr) for t, rr in prof]
    prof += [(length * 0.55, r), (length * 0.55 + 0.4, r * 0.97), (length * 0.55 + 1.0, r), (length, r)]
    # lathe axis "y" runs down the screen from (px, py).
    z_axis = 0.0
    squash = h["top"] / (r * lt.PX)
    s.lathe(prof, cx, h["y0"], axis="y", z=z_axis, squash=squash, sides=20,
            mats=[metal_light] * 5 + [metal, metal_dark, metal, metal])
    # Its middle spine plate and the vent housings either side (the concept's dark grilles).
    s.wall_block(cx - 3.0, h["y0"] + 0.8, cx + 3.0, 12.0, 0.20, h["top"] + 0.025, metal_light, bevel=0.2)
    s.wall_block(11.0, 8.5, 14.2, 13.5, 0.10, 0.27, dark, bevel=0.15)
    s.wall_block(22.4, 7.0, 28.6, 12.0, 0.10, 0.31, dark, bevel=0.15)
    for tx in (24.0, 26.0, 27.8):  # the teeth over the right grille
        s.wall_block(tx - 0.5, 11.0, tx + 0.5, 14.0, 0.20, 0.33, metal, bevel=0.2)

    # The chevron collar over the hood's front and the clamp plates under it.
    plate(s, CHEVRON, CHEVRON_BASE, CHEVRON_TOP, brass, chamfer_px=0.7, top_mat=brass_light)
    plate(s, SEVEN, BED - 0.02, PLATE_TOP, brass, chamfer_px=0.5)
    plate(s, BAR, BED - 0.02, PLATE_TOP - 0.02, brass, chamfer_px=0.5)
    s.wall_block(22.0, 29.0, 27.4, 30.0, PLATE_TOP - 0.06, PLATE_TOP - 0.01, dark, bevel=0.0)  # the bar's grille
    s.wall_block(10.4, 29.2, 15.0, 31.0, BED, 0.27, metal_light, bevel=0.25)  # left horizontal bar

    # Pipes down the flanks.
    for pts in PIPES:
        tube(s, pts, PIPE_R, brass)
        sx, sy, _ = pts[0]
        s.dome(sx, sy, 1.3, 1.3, PIPE_Z - 0.08, 0.16, brass_dark, sides=8, rings=2)  # collar at the hood

    # The ribbed drum in the middle and the ribbed cylinder on the right (lying along Y), the left
    # end cap and the pipes below the drum.
    s.lathe(ribbed(4, 7.4, 1.6, 1.95), 20.0, 36.0, axis="y", z=BED + 0.06, squash=1.0, mat=metal, sides=10)
    s.lathe(ribbed(6, 13.0, 1.9, 2.25, 0.0) + [(14.5, 1.6), (14.6, 0.0)], 28.8, 35.0, axis="y", z=0.08, squash=1.0,
            mat=metal_dark, sides=12)
    for px in (19.0, 21.0):
        s.lathe([(0.0, 0.8), (5.2, 0.8)], px, 43.6, axis="y", z=BED + 0.02, mat=metal_dark, sides=8)
    s.lathe([(0.0, 1.9), (2.6, 1.9), (3.2, 1.5), (3.6, 0.0)], 15.4, 46.8, axis="y", z=0.10, mat=metal, sides=10)

    # A few red status lights, as the concept's small lamps on the right flank.
    s.light(31.8, 24.6, 0.6, 0.18, kind="red", strength=1.5)

    objects = s.objects(deck)
    s.check(objects)
    s.export(objects)


main()
