"""The gold dome bunker on TYRIAN's ground (map 1-9, layer 0; tiles 320 321 / 330 331, 2x2, six
copies on the dirt), after the concept assets/blender/features/concepts/tyr-bunker-ring.jpg: a dark
armoured hull shaped like a shield, at its top a big riveted brass ring round a sunken grille pit
(vertical bars, a cross bar and a diagonal brace), two brass half-domes on the shoulders each with a
grey square nozzle pointing toward the camera, a brass crescent (a C open to the lower right) low in
the middle, grey armour blocks down both flanks, a grey spine and struts between the domes and a
grey truss at the foot.

Every cell carries a ground enemy (assembly-newsh2-115, drawn at 0.45), so the whole bunker stays
under ENEMY_MAX (0.38) and is only seen once the enemy is destroyed: the emplacement it sat on. The
tiles stay drawn (keepTiles): the model covers only the bunker's own outline, not the dirt.
Its export removes the old per-tile model shapesz-bunker-ring. Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_bunker_ring.py
    python tools/concept_maps.py tile:shapesz-tyrbld-bunker-ring --concept tyr-bunker-ring --span -0.054,-0.083,0.946,0.917 --px 32
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-bunker-ring
"""

import math
import sys
from pathlib import Path

import bmesh
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_tyrbld as tb  # noqa: E402
import lib_tiles as lt  # noqa: E402

# Pixel positions (pattern px at 1x, 48 x 56). Gemini drew the bunker about 2 px right and 1.5 px
# low of the tiles, at the same scale: the concept is registered with a span shifted to match
# (--span -0.054,-0.083,0.946,0.917), so the tile art and the aligned concept agree on these.
# The lower third tapers to a rounded point under the truss, as in the tiles and the concept.
OUTLINE = [(1.5, 14.0), (4.5, 9.5), (35.5, 9.5), (39.5, 14.0), (39.5, 37.0), (37.0, 41.5), (34.0, 45.0),
           (29.5, 50.0), (26.5, 52.0), (15.0, 52.0), (11.5, 50.0), (7.0, 45.0), (4.0, 41.5), (1.5, 38.0)]
RING = dict(cx=19.4, cy=11.0, rx=15.4, ry=11.0, band=4.0)  # outer ellipse and band width
DOMES = [(6.6, 29.8), (32.0, 29.8)]
DOME_R = 4.9  # px: a true half-sphere, as tall as its radius allows under TOP
NOZZLES = [(4.2, 31.0, 9.4, 36.6), (29.6, 31.0, 34.8, 36.6)]  # out of the domes' fronts
CRESCENT = dict(cx=19.2, cy=40.0, rx=7.6, ry=5.3, band=3.0, gap=(12.0, 80.0))  # gap: screen angles, deg

HULL = 0.10  # the hull's deck (low, so the domes' sides show)
PIT = 0.03  # the grille pit inside the ring
TOP = 0.375  # highest part (ENEMY_MAX 0.38)
DOME_Z = 0.0  # the domes' equator (sunk into the hull)
EDGE = 0.03  # the bevelled armour band round the hull, above HULL
CENTRE = (20.5, 28.0)  # the outline is sampled as rays from here


def _in_poly(poly, x, y):
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0 + 1e-9):
            inside = not inside
    return inside


def _in_hull(x, y):
    c = RING
    return _in_poly(OUTLINE, x, y) or ((x - c["cx"]) / c["rx"]) ** 2 + ((y - c["cy"]) / c["ry"]) ** 2 <= 1.0


def smooth_outline(n=240, window=4):
    """The hull's outline (shield polygon and ring ellipse) as a smooth closed polygon, pattern px:
    the union sampled along rays from CENTRE, its radius smoothed round the loop (rounds corners
    and the joins between shield and ring). Counter-clockwise on screen (y down)."""
    cx, cy = CENTRE
    rs = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ca, sa = math.cos(a), math.sin(a)
        r = 40.0
        while r > 0 and not _in_hull(cx + r * ca, cy + r * sa):
            r -= 0.02
        rs.append(r)
    w = [math.exp(-(k / (window * 0.6)) ** 2) for k in range(-window, window + 1)]
    sm = [sum(w[k + window] * rs[(i + k) % n] for k in range(-window, window + 1)) / sum(w) for i in range(n)]
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i, r in enumerate(sm)]


def offset(poly, d):
    """The closed polygon moved `d` px inward along its averaged normals."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    out = []
    for i in range(n):
        (xa, ya), (xb, yb) = poly[i - 1], poly[(i + 1) % n]
        tx, ty = xb - xa, yb - ya
        ln = math.hypot(tx, ty)
        nx, ny = -ty / ln, tx / ln
        x, y = poly[i]
        if nx * (x - cx) + ny * (y - cy) < 0:  # make it point outward
            nx, ny = -nx, -ny
        out.append((x - nx * d, y - ny * d))
    return out


def poly_mask(s, poly):
    yy, xx = np.mgrid[0:s.H, 0:s.W] + 0.5
    inside = np.zeros((s.H, s.W), bool)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        cond = (y0 > yy) != (y1 > yy)
        xc = x0 + (yy - y0) * (x1 - x0) / (y1 - y0 + 1e-9)
        inside ^= cond & (xx < xc)
    return inside


def hull_band(s, poly, top_mat, wall_mat):
    """The hull's side as one continuous bevelled band along the smooth outline: from just under
    the ground up a steep wall, a chamfer, a flat armour top, then down into the deck (whose
    pixel-stepped edge it hides)."""
    prof = [(0.0, -0.02), (0.25, HULL - 0.02), (1.2, HULL + EDGE), (3.0, HULL + EDGE), (3.8, HULL - 0.01)]
    mats = [wall_mat, wall_mat, top_mat, top_mat]
    loops = [offset(poly, d) for d, _ in prof]
    bm = bmesh.new()
    rings = [[bm.verts.new((s.x(x), s.y(y), z)) for x, y in loop] for loop, (_, z) in zip(loops, prof)]
    n = len(poly)
    for k in range(len(prof) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mats[k]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = f.material_index == wall_mat
    s._merge(bm)


def band(s, cx, cy, rx, ry, width, z0, z1, mat, gap=None, segments=56, edge_mat=None, start=0.0):
    """A raised band along an ellipse (outer radii rx, ry px; `width` px inward), rounded on top:
    the ring and the crescent. `gap` (a0, a1) in screen degrees (0 = right, 90 = down) is left
    open; the ends are cut square."""
    edge_mat = mat if edge_mat is None else edge_mat
    # Cross-section: (inward offset px, z), outer foot to inner foot.
    zm = z0 + (z1 - z0) * 0.55
    prof = [(0.0, z0), (0.0, zm), (0.15 * width, z1 - 0.025), (0.35 * width, z1), (0.65 * width, z1),
            (0.85 * width, z1 - 0.025), (width, zm), (width, z0)]
    if gap:
        a0, a1 = math.radians(gap[1]), math.radians(gap[0]) + 2 * math.pi
        angles = [a0 + (a1 - a0) * i / segments for i in range(segments + 1)]
        closed = False
    else:
        angles = [math.radians(start) + 2 * math.pi * i / segments for i in range(segments)]
        closed = True
    bm = bmesh.new()
    rings = []
    for a in angles:
        ca, sa = math.cos(a), math.sin(a)
        # Outer point and the inward normal of the ellipse there (screen px, y down).
        px, py = cx + rx * ca, cy + ry * sa
        nx, ny = -ca / rx, -sa / ry
        ln = math.hypot(nx, ny)
        nx, ny = nx / ln, ny / ln
        rings.append([bm.verts.new((s.x(px + nx * d), s.y(py + ny * d), z)) for d, z in prof])
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    k = len(prof)
    for ra, rb in pairs:
        for i in range(k):
            j = (i + 1) % k
            top = 0 < i < k - 2
            f = bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
            f.material_index = mat if top else edge_mat
            f.smooth = True
    if not closed:
        bm.faces.new(rings[0]).material_index = edge_mat
        bm.faces.new(list(reversed(rings[-1]))).material_index = edge_mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def bar(s, p0, p1, width, z0, z1, mat):
    """A straight bar (box) from pixel point p0 to p1, `width` px across, z0 to z1."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy)
    ox, oy = -dy / ln * width / 2, dx / ln * width / 2
    quad = [(x0 + ox, y0 + oy), (x1 + ox, y1 + oy), (x1 - ox, y1 - oy), (x0 - ox, y0 - oy)]
    bm = bmesh.new()
    lo = [bm.verts.new((s.x(x), s.y(y), z0)) for x, y in quad]
    hi = [bm.verts.new((s.x(x), s.y(y), z1)) for x, y in quad]
    bm.faces.new(lo)
    bm.faces.new(hi)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    for f in bm.faces:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def build():
    s = tb.Structure("bunker-ring")
    hull = s.m(1, metallic=0.4, roughness=0.6)  # the hull's near-black (12 12 12)
    hull_edge = s.m(3, metallic=0.4, roughness=0.6)
    pit = s.m("dark")
    grey = s.m(5, metallic=0.6, roughness=0.4)
    grey_light = s.m(7, metallic=0.6, roughness=0.35)
    brass = s.m(24, metallic=0.7, roughness=0.35)
    brass_dark = s.m(21, metallic=0.6, roughness=0.45)
    brass_light = s.m(26, metallic=0.7, roughness=0.3)

    # The hull: a smooth outline with a bevelled armour band; the deck inside it (pixel-terraced)
    # starts under the band's top, so no pixel step shows at the edge.
    poly = smooth_outline()
    s.set_footprint(poly_mask(s, offset(poly, 1.6)))
    fp = s.footprint
    s.set_region(fp, HULL, hull)
    hull_band(s, poly, hull_edge, hull_edge)
    s.raise_box(12, 23, 28, 38, HULL + 0.02, hull)
    # The pit inside the ring.
    c = RING
    inner = s.ellipse_mask(c["cx"], c["cy"], c["rx"] - c["band"] + 0.3, c["ry"] - c["band"] + 0.3)
    s.set_region(inner, PIT, pit)
    # The socket under the crescent, sunk below the deck.
    k = CRESCENT
    s.set_region(s.ellipse_mask(k["cx"], k["cy"], k["rx"] - 0.8, k["ry"] - 0.8), HULL - 0.03, pit)

    # The ring: a riveted brass band (plates and rivets come from the concept's bake). Its loop
    # closes at the far (top) side, out of the game camera's view.
    band(s, c["cx"], c["cy"], c["rx"], c["ry"], c["band"], HULL - 0.04, TOP, brass, edge_mat=brass_dark,
         segments=96, start=-90.0)
    # The grille in the pit: vertical bars, a cross bar and the L-bracket with its diagonal brace.
    irx, iry = c["rx"] - c["band"], c["ry"] - c["band"]
    for bx in (13.0, 15.5, 18.0, 20.5, 23.0, 25.5):
        t = (bx - c["cx"]) / irx
        h = iry * math.sqrt(max(0.0, 1 - t * t))
        bar(s, (bx, c["cy"] - h - 0.5), (bx, c["cy"] + h + 0.5), 0.9, PIT - 0.02, 0.27, grey)
    bar(s, (c["cx"] - irx - 0.5, 9.5), (c["cx"] + irx + 0.5, 9.5), 1.0, PIT - 0.02, 0.285, grey_light)
    bar(s, (12.5, 10.0), (12.5, 16.0), 1.4, PIT - 0.02, 0.29, grey_light)
    bar(s, (12.5, 10.0), (21.0, 17.5), 1.1, PIT - 0.02, 0.28, grey_light)
    # Pipes deep in the pit (dark, under the bars).
    bar(s, (16.0, 15.5), (27.0, 15.5), 1.6, PIT - 0.02, 0.14, brass_dark)

    # The shoulders: brass half-domes (equator at the ground, so their round sides stand clear of
    # the low deck) in a grey collar, a lighter seam strap over each, and a grey muzzle coming out
    # of the lower front of each dome.
    R = DOME_R
    H = TOP - DOME_Z - 0.005
    for (dx, dy), (x0, y0, x1, y1) in zip(DOMES, NOZZLES):
        s.lathe([(0.0, R + 0.7), ((HULL + 0.035) / lt.PX, R + 0.7), ((HULL + 0.035) / lt.PX, R - 0.2)], dx, dy,
                axis="z", z=-0.01, mat=grey, sides=32, smooth=False)
        s.dome(dx, dy, R, R, DOME_Z, H, brass, sides=32, rings=12)
        # The seam strap over the crown (front to back), hugging the curve.
        prof = []
        for i in range(13):
            t = -0.97 + i / 12 * 1.94
            prof.append((dy + t * R, min(TOP, DOME_Z + H * math.sqrt(max(0.0, 1 - t * t)) + 0.012)))
        under = [(py, max(DOME_Z, z - 0.06)) for py, z in reversed(prof)]
        s.prism(prof + under, dx - 0.55, dx + 0.55, mat=brass_light)
        # The muzzle: a grey block out of the dome's front, with a dark bore on its face.
        s.wall_block(x0, y0, x1, y1, HULL - 0.02, 0.27, grey_light, bevel=0.25)
        s.wall_block(x0 + 1.2, y1 - 0.4, x1 - 1.2, y1 + 0.25, HULL + 0.05, 0.22, pit, bevel=0.0)

    # The crescent low in the middle.
    band(s, k["cx"], k["cy"], k["rx"], k["ry"], k["band"], HULL - 0.05, TOP - 0.03, brass, gap=k["gap"],
         edge_mat=brass_dark, segments=48)

    # Grey machinery: the spine between the domes, its struts, the flanks' blocks, the boxes by the
    # crescent and the truss at the foot.
    s.wall_block(18.6, 22.0, 21.6, 34.0, HULL, 0.29, grey, bevel=0.3)
    bar(s, (14.0, 34.5), (19.0, 27.0), 1.2, HULL, 0.26, grey)
    bar(s, (26.5, 34.5), (21.5, 27.0), 1.2, HULL, 0.26, grey)
    bar(s, (12.5, 24.0), (27.5, 24.0), 1.3, HULL, 0.275, grey_light)
    for x0, y0, x1, y1 in ((3.2, 14.5, 6.6, 19.5), (3.0, 20.5, 6.4, 25.5), (34.0, 14.5, 37.8, 19.5), (34.2, 20.5, 38.0, 25.5)):
        s.wall_block(x0, y0, x1, y1, HULL, 0.27, grey_light, bevel=0.3)
    for x0, y0, x1, y1 in ((7.5, 39.0, 12.0, 44.0), (28.5, 38.5, 33.0, 43.5)):
        s.wall_block(x0, y0, x1, y1, HULL, 0.27, grey, bevel=0.3)
    for x in (16.0, 25.0):
        bar(s, (x, 45.5), (x, 50.3), 1.3, HULL, 0.24, grey)
    for y, xa, xb in ((46.8, 13.0, 28.0), (49.6, 15.5, 25.5)):
        bar(s, (xa, y), (xb, y), 1.1, HULL, 0.23, grey_light)
    # Cables on the right flank (the concept's hoses), a pipe along the left.
    s.lathe([(0.0, 0.9), (20.0, 0.9)], 37.6, 16.0, axis="y", z=HULL + 0.03, mat=hull_edge, sides=10)
    s.lathe([(0.0, 0.8), (11.0, 0.8)], 3.8, 27.5, axis="y", z=HULL + 0.03, mat=grey, sides=10)

    objects = s.objects()
    s.check(objects)
    s.export(objects)


build()
