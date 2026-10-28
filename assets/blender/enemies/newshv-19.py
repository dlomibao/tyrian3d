"""Small blue gem (newshv.shp frame 19, a 12x14 sprite): a 3D version of its sprite.

Seen in episode 2 (level 2.15). A shiny bulb with a diamond outline: a dark 1 px rim (56), mid
blues (58-60) brightening to a pale (61-62) and white (63) cross just right of centre, and a short
stalk trailing below it: a dark neck row (55) and a mid-blue knob (58). newshv-57 is the same gem
in red.

The bulb is a faceted crystal, flat shaded: 5 px above the midplane (half its 10 px width) and
3.5 px below it, widest at the rim. Its rings go from the diamond at the rim to a rounder shape
towards the crown and close on a crest ridge 4 px long running down the sprite's bright column
(half a pixel right of centre), so the top is a roof whose lit flanks give the white stripe. Each top
face takes the palette index that best fits the sprite pixels it covers from above, so from above
the bulb shows the sprite's own shading; the facets add the sparkle. The stalk is a 2 px rod with
its axis 1 px above the midplane: a narrower dark collar at the neck, then a mid-blue knob with a
rounded end.

Run: blender --background --python assets/blender/enemies/newshv-19.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b003 as lib  # noqa: E402

NAME = "newshv-19"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

W, H = 12, 14
U = 1 / 12
SIDE = 3  # sectors per side of the diamond
TOP = 5.0 * U  # dome height above the midplane: half the bulb's 10 px width
BOTTOM = 3.5 * U  # depth of the rounded underside
TOP_RINGS = (1.0, 0.82, 0.6, 0.34)  # ring scales from the rim in; the crest ridge follows
RIDGE = 2.0 * U  # half the length of the crest ridge, which runs down the sprite (rows 5-9)
BOTTOM_RINGS = (1.0,)  # the underside is one fan: nobody sees it from the game camera
HIGHLIGHT_DX = 0.5 * U  # the bright cross is centred on column 6, half a pixel right of centre
UNDERSIDE = 56
NECK, KNOB = 55, 58  # the stalk's dark neck row (12) and its mid-blue end (row 13)
STALK_Z = 1.0 * U  # the stalk's axis, 1 px above the midplane


def unit_dirs():
    """Points around the unit diamond |x| + |y| = 1, evenly spaced along each side, corners
    included, counter-clockwise from +X."""
    corners = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    out = []
    for k in range(4):
        (x0, y0), (x1, y1) = corners[k], corners[(k + 1) % 4]
        for i in range(SIDE):
            t = i / SIDE
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out


def ring_point(d, s, rx, ry):
    """The point in direction `d` (a point on the unit diamond) on the ring of scale `s`: the ring
    is a superellipse whose exponent goes from 1 (the diamond) at the rim towards 2 (round) at the
    crown."""
    p = 1.0 + (1.0 - s) ** 1.5  # stays a diamond near the rim, so the dark rim band keeps its width
    ang = math.atan2(d[1], d[0])
    c, sn = math.cos(ang), math.sin(ang)
    r = (abs(c) ** p + abs(sn) ** p) ** (-1 / p)
    return (s * r * c * rx + (1 - s) * HIGHLIGHT_DX, s * r * sn * ry + (1 - s) * d[1] * RIDGE)


def sprite_index(pixels, x, y):
    """The palette index of the sprite pixel under Blender (x, y); the nearest opaque pixel when
    (x, y) falls on a transparent one."""
    c, r = math.floor(x * 12 + W / 2), math.floor(H / 2 - y * 12)
    if 0 <= r < H and 0 <= c < W and pixels[r][c] >= 0:
        return pixels[r][c]
    best = min(((rr - r) ** 2 + (cc - c) ** 2, pixels[rr][cc])
               for rr in range(H) for cc in range(W) if pixels[rr][cc] >= 0)
    return best[1]


def inside(poly, x, y):
    """Whether (x, y) lies inside the XY polygon `poly` (even-odd rule)."""
    hit = False
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def bulb(pixels, dist, mats, slot, cx, cy, rx, ry, coll):
    import bmesh
    bm = bmesh.new()
    dirs = unit_dirs()
    n = len(dirs)

    def ring(s, z):
        return [bm.verts.new((cx + x, cy + y, z)) for x, y in (ring_point(d, s, rx, ry) for d in dirs)]

    rim = ring(1.0, 0.0)
    top = [rim] + [ring(s, TOP * (1 - s ** 1.6) ** 0.8) for s in TOP_RINGS[1:]]
    # The crest: a ridge down the sprite's bright column, so its lit right flank is the white
    # stripe. Directions that land on the same ridge point share one vertex.
    crest = {}
    for d in dirs:
        key = round(d[1], 6)
        if key not in crest:
            crest[key] = bm.verts.new((cx + HIGHLIGHT_DX, cy + d[1] * RIDGE, TOP))
    top.append([crest[round(d[1], 6)] for d in dirs])
    top_apex = None
    bot = [rim] + [ring(s, -BOTTOM * math.sqrt(1 - s * s)) for s in BOTTOM_RINGS[1:]]
    bot_apex = bm.verts.new((cx, cy, -BOTTOM))

    def bands(rings, apex, colour):
        for k in range(len(rings)):
            a = rings[k]
            b = rings[k + 1] if k + 1 < len(rings) else None
            if b is None and apex is None:
                break
            for i in range(n):
                j = (i + 1) % n
                f = (a[i], a[j], b[j], b[i]) if b else (a[i], a[j], apex)
                f = tuple(v for k, v in enumerate(f) if v is not f[k - 1])
                face = bm.faces.new(f)
                face.material_index = slot[colour(f)]

    def seen(f):
        """The palette index that best fits the sprite pixels whose centres the face covers from
        above (least total colour distance); the pixel under its centre if it covers none."""
        poly = [(v.co.x, v.co.y) for v in f]
        under = [pixels[r][c] for r in range(H) for c in range(W)
                 if pixels[r][c] >= 0 and inside(poly, (c + 0.5 - W / 2) / 12, (H / 2 - r - 0.5) / 12)]
        if not under:
            return sprite_index(pixels, sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))
        return min(set(under), key=lambda i: sum(dist(i, j) for j in under))

    bands(top, top_apex, seen)
    bands(bot, bot_apex, lambda f: UNDERSIDE)
    return common.mesh_object(NAME, bm, mats, coll, smooth=False)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    pixels = sprite["frames"][0]["pixels"]
    coll = common.reset_collection(NAME)
    used = sorted({v for row in pixels for v in row if v >= 0} | {UNDERSIDE, NECK, KNOB})
    mats, slot = [], {}
    for i in used:
        slot[i] = len(mats)
        glow = {63: 0.9, 62: 0.3}.get(i, 0.0)  # the white core glows a little, as the sprite's does
        mats.append(common.palette_material(sprite, i, NAME, metallic=0.3, roughness=0.3,
                                            emission_strength=glow))

    cy = lib.ey(7.5, H)
    colours = {int(k): v for k, v in sprite["colors"].items()}

    def dist(a, b):
        return sum((p - q) ** 2 for p, q in zip(colours[a], colours[b])) ** 0.5

    gem = bulb(pixels, dist, mats, slot, 0.0, cy, 5.0 * U, 4.5 * U, coll)

    # The stalk below it (rows 12-13, columns 5-6): a round 2 px rod, its axis 1 px above the
    # midplane. It starts inside the bulb in mid blue, narrows to a dark collar at the neck (row 12)
    # and ends in a mid-blue knob (row 13) with a rounded end.
    import bmesh
    bm = bmesh.new()
    z = STALK_Z
    common.loft(bm, [(lib.ey(11.0, H), 1.0 * U, 1.0 * U, z), (lib.ey(12.0, H), 1.0 * U, 1.0 * U, z),
                     (lib.ey(12.0, H), 0.75 * U, 0.75 * U, z), (lib.ey(13.0, H), 0.75 * U, 0.75 * U, z),
                     (lib.ey(13.0, H), 1.0 * U, 1.0 * U, z), (lib.ey(13.65, H), 1.0 * U, 1.0 * U, z),
                     (lib.ey(14.0, H), 0.0, 0.0, z)], sides=6, mat_index=slot[KNOB])
    # Where it leaves the bulb (row 11) it keeps the bulb's dark rim; the collar between the two
    # steps (row 12) is the dark neck row.
    for f in bm.faces:
        ys = [v.co.y for v in f.verts]
        if max(ys) - min(ys) < 1e-6:
            continue
        if min(ys) >= lib.ey(13.0, H) - 1e-6 and max(ys) <= lib.ey(12.0, H) + 1e-6:
            f.material_index = slot[NECK]
        elif min(ys) >= lib.ey(12.0, H) - 1e-6:
            f.material_index = slot[UNDERSIDE]
    stalk = common.mesh_object(f"{NAME}_stalk", bm, mats, coll, smooth=True)

    objects = [gem, stalk]
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    lib.preview(objects, ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
