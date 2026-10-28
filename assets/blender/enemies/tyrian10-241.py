"""Beer mug (tyrian.shp#10 frame 241): a 3D version of its sprite.

Seen in episode 1 (level section 41). The sprite draws a fluted glass tankard from the side,
mouth up the screen: grey glass at the top, brown beer below a pale foam line, a dark base row,
and a grey strap handle on the right. In 3D it lies on its side in the screen plane: a round body
along Y, 13 px across and as deep (the sprite's highlight and shadow columns say a round glass),
with raised ridges for the bright columns, a dark rim at the mouth and a dark foot at the base.
The handle is a round glass loop round a hole, centred on the body's midplane. The near-black
pixels to the right of and below the mug (indices 160 and 161) are its drop shadow: a thin dark
plate under the mug, its outline the sprite's staircase smoothed, carries them, so they also show
through the handle's hole. Each sprite row is a band of the body's facets, so from above every
facet takes the colour of the pixels it covers.

Run: blender --background --python assets/blender/enemies/tyrian10-241.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b021 as lib  # noqa: E402
from lib_b021 import common, ex, ey  # noqa: E402

NAME = "tyrian10-241"
U = 1 / 12  # one sprite px
CX = ex(11)  # the body's centre line: columns 5-16 (13 px with the outline)
R = 6.6 * U  # body radius: round, as deep as it is wide


def _angles():
    """The ring's vertex angles (0 = the right side, pi/2 = on top). On top, a vertex on every
    sprite column edge, so each column from above is one facet and takes its own colour (the
    sprite's pale stripes and dark grooves); underneath, where nothing sees it, fewer."""
    xs = [17.6, 17.3] + list(range(17, 4, -1)) + [4.7, 4.4]
    top = [math.acos(max(-1.0, min(1.0, (x - 11) * U / R))) for x in xs]
    bottom = [math.pi + math.pi * k / 8 for k in range(1, 8)]
    return top + bottom


ANGLES = _angles()
SIDES = len(ANGLES)
Z0 = R + 0.5 * U  # the axis's height: the mug lies on its drop-shadow plate on the ground


def ring(y, s=1.0):
    """A ring round the body at height y, scaled by s."""
    return [(CX + s * R * math.cos(a), y, s * R * math.sin(a)) for a in ANGLES]


# The drop shadow's outline (sprite column, row of pixel edges): the sprite's own staircase smoothed
# into straight runs that still take in exactly its shadow pixels (and never an empty one). Its top
# and left run under the mug and the handle.
PLATE = [(6, 8), (17, 8), (19.6, 11), (23, 11), (23, 19.6), (22.1, 20.5), (20.1, 21.5), (18.1, 23.6),
         (17.8, 24), (7.4, 24), (5.4, 22)]


def shadow_plate(bm, z0, z1, mat_index):
    """A thin plate under the mug with the smoothed outline PLATE: it shows only where the sprite
    has its drop shadow (and through the handle's hole)."""
    top = [bm.verts.new((ex(c), ey(r), z1)) for c, r in PLATE]
    bot = [bm.verts.new((ex(c), ey(r), z0)) for c, r in PLATE]
    f = bm.faces.new(top)
    f.normal_update()
    if f.normal.z < 0:
        f.normal_flip()
    f.material_index = mat_index
    n = len(PLATE)
    for i in range(n):
        j = (i + 1) % n
        w = bm.faces.new((top[i], bot[i], bot[j], top[j]))
        w.material_index = mat_index
        w.normal_update()
        mid = (top[i].co + top[j].co) / 2
        cen = sum((v.co for v in top), top[0].co * 0) / n
        if w.normal.dot(mid - cen) < 0:
            w.normal_flip()


def sprite_pixels(sprite):
    return [[int(v) for v in (line.split() if isinstance(line, str) else line)]
            for line in sprite["frames"][0]["pixels"]]


def _lab(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(c)) for c in rgb)
    xyz = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.9505, 0.2126 * r + 0.7152 * g + 0.0722 * b, \
        (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.089
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in xyz]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


GLASS_SET = (4, 7, 10, 12, 14, 15)  # the glass ramp's steps the body's facets take (few materials)
BEER_SET = (18, 20, 23, 25, 28, 30)
LIFT = 8
EDGE = 2  # near black: the sprite's outline columns at the silhouette's edge


def column_colours(sprite, rows, allowed):
    """For each of the body's segments, the palette index (of `allowed`) closest on average to the
    sprite pixels the segment covers from above: the sprite's light and dark columns become the
    colours of the round body's facets."""
    pixels = sprite_pixels(sprite)
    lab = {int(k): _lab(v) for k, v in sprite["colors"].items()}
    out = []
    for i in range(SIDES):
        a0, a1 = ANGLES[i], ANGLES[(i + 1) % SIDES] + (2 * math.pi if i + 1 == SIDES else 0)
        under = math.sin((a0 + a1) / 2) < 0
        if under:  # underneath: mirror the segment above, in the body's colours (not outline)
            a0, a1 = -a1, -a0
        x0, x1 = sorted(11 + R / U * math.cos(a) for a in (a0, a1))
        if under:
            x0, x1 = min(max(x0, 5.0), 16.0), max(min(x1, 17.0), 6.0)
        cands = set(allowed)
        if x0 >= 16.9 or x1 <= 5.1:  # the silhouette's edge: the sprite's outline column
            cols = [4 if x1 <= 5.1 else 17]
            cands = {EDGE}
        else:
            cols = [c for c in range(5, 17) if c + 1 > x0 + 0.01 and c < x1 - 0.01]
        seen = [pixels[r][c] for r in rows for c in cols if pixels[r][c] >= 0]
        # Aim a little lighter than the pixels (LIFT in L*): the lit body reads darker than its
        # flat colour, and the sprite's glass and beer read bright.
        aim = [(lab[v][0] + LIFT, lab[v][1], lab[v][2]) for v in seen]
        out.append(min(sorted(cands), key=lambda k: sum(math.dist(lab[k], t) for t in aim)))
    return out


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats, slot = [], {}

    def m(i, **kw):
        if i not in slot:
            slot[i] = len(mats)
            mats.append(pal(i, **kw))
        return slot[i]
    DARK = m(EDGE, metallic=0.1, roughness=0.5)  # dark base foot, rim and inside
    INSIDE = DARK
    FOOT = m(19, metallic=0.1, roughness=0.3)  # the base seen end on: dark beer through the glass
    # One band of facets per sprite row (rows with the same colours merged): from above each facet
    # takes the colours of the sprite pixels it covers, beer (rows 12-20) and glass (rows 6-11).
    bands = []  # (row the band starts at, going up the screen, its facets' materials)
    for r in range(20, 5, -1):
        cols = [m(i, metallic=0.1, roughness=0.25)
                for i in column_colours(sprite, [r], BEER_SET if r >= 12 else GLASS_SET)]
        if bands and bands[-1][1] == cols:
            continue
        bands.append((r, cols))

    # Body from the base foot (row 21) to the mouth (rows 5-6), then in and down into the mug.
    bm = bmesh.new()
    rings = [ring(ey(22.0), 0.86), ring(ey(21.6), 0.96), ring(ey(21.0), 0.99), ring(ey(20.9))]
    rings += [ring(ey(r + 1)) for r, _ in bands[1:]] + [ring(ey(6.0))]  # each band's bottom edge
    rings += [ring(ey(5.0), 0.95), ring(ey(5.0), 0.84), ring(ey(7.0), 0.8)]
    lib.ring_loft(bm, rings, [DARK, DARK, DARK] + [cols for _, cols in bands] + [DARK, DARK, INSIDE],
                  cap_mats=(FOOT, INSIDE))
    body = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    lib._sharpen(body, 35)

    # The bright columns as raised ridges about 1.5 px wide, standing 0.3 px proud: glass and
    # beer highlights at columns 8, 11 and 14. Each ridge takes its column's colours, in runs of
    # rows of the same colour (the beer's column 8 brightens to cream at the bottom).
    smats, sslot = [], {}

    def sm(i):
        if i not in sslot:
            sslot[i] = len(smats)
            smats.append(pal(i, metallic=0.1, roughness=0.2))
        return sslot[i]
    pixels = sprite_pixels(sprite)
    lab = {int(k): _lab(v) for k, v in sprite["colors"].items()}

    def closest(v, allowed):
        t = (lab[v][0] + LIFT, lab[v][1], lab[v][2])
        return min(allowed, key=lambda k: math.dist(lab[k], t))
    bm = bmesh.new()
    rr = 0.75 * U

    def ridge(col, r0, r1, allowed, end0, end1, whole=False):
        a = math.acos((ex(col + 0.5) - CX) / R)
        rc = R + 0.3 * U - rr
        x, z = CX + rc * math.cos(a), rc * math.sin(a)
        runs = []
        one = min(allowed, key=lambda k: sum(math.dist(lab[k], (lab[pixels[r][col]][0] + LIFT,) + lab[pixels[r][col]][1:])
                                             for r in range(r0, r1 + 1)))
        for r in range(r0, r1 + 1):
            k = one if whole else closest(pixels[r][col], allowed)
            if runs and runs[-1][0] == k:
                runs[-1][2] = r
            else:
                runs.append([k, r, r])
        for n, (k, a0, a1) in enumerate(runs):
            y0 = ey(a1 + 1) if a1 < r1 else ey(end1)
            y1 = ey(a0) if a0 > r0 else ey(end0)
            lib.tube(bm, (x, y0, z), (x, y1, z), rr, sides=6, mat_index=sm(k),
                     caps=n in (0, len(runs) - 1))  # the ridge's own ends only
    for col in (8, 11):  # the glass is bright at columns 7-9 and 11 only: one colour each
        ridge(col, 7, 11, (12, 14, 15), 6.5, 11.8, whole=True)
    for col in (8, 11, 14):
        ridge(col, 13, 20, (25, 26, 27, 28, 29, 30), 12.4, 20.6)
    ridges = common.mesh_object(f"{NAME}_ridges", bm, smats, coll, smooth=True)

    # The handle: a round glass loop about 2.2 px thick round a hole (columns 17-21, rows 8-19),
    # its centre line along the strap's middle (rows 9 and 18, column 20) at the body's axis
    # height, its ends buried in the body; and the drop-shadow plate under everything.
    hmats = [
        pal(10, metallic=0.1, roughness=0.25),  # 0 handle top (the strap's grey middle)
        pal(5, metallic=0.1, roughness=0.25),  # 1 handle flanks (the sprite's dark edges)
        pal(4, metallic=0.1, roughness=0.25),  # 2 handle underside
        pal(160, metallic=0.0, roughness=0.15),  # 3 drop shadow
    ]
    bm = bmesh.new()
    path = [(15.5, 9.5), (19.5, 9.5), (20.5, 10.5), (20.5, 17.5), (19.5, 18.5), (15.5, 18.5)]
    # 1.1 px round, widened at the four 45-degree bends so the mitred joints don't pinch
    radii = [1.1 * U] + [1.1 * U / math.cos(math.pi / 8)] * 4 + [1.1 * U]
    lib.polyline_tube(bm, [(ex(c), ey(r), 0.0) for c, r in path], radii, sides=8)
    for f in bm.faces:
        f.normal_update()
        f.material_index = 0 if f.normal.z > 0.9 else 1 if f.normal.z > -0.3 else 2
    shadow_plate(bm, -Z0, -R, 3)
    for node in hmats[3].node_tree.nodes:  # a matte shadow: no sheen from the sky
        if node.type == "BSDF_PRINCIPLED":
            for key in ("Specular IOR Level", "Specular"):
                if key in node.inputs:
                    node.inputs[key].default_value = 0.0
    handle = common.mesh_object(f"{NAME}_handle", bm, hmats, coll, smooth=True)
    lib._sharpen(handle, 50)  # a smooth loop; the plate's edges stay crisp

    from mathutils import Matrix
    for obj in (body, ridges, handle):  # lift the mug onto the ground
        obj.data.transform(Matrix.Translation((0, 0, Z0)))
    return [(NAME, [body, ridges, handle], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
