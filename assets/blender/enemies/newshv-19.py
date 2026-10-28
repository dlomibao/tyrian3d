"""Small blue gem (newshv.shp frame 19, a 12x14 sprite): a 3D version of its sprite.

Seen in episode 2 (level 2.15). A shiny bulb with a diamond outline: a dark 1 px rim (56), mid
blues (58-60) brightening to a pale (61-62) and white (63) cross just right of centre, and a short
stalk trailing below it: a dark neck row (55) and a mid-blue knob (58). newshv-57 is the same gem
in red.

The bulb is a cut crystal, flat shaded: 5 px above the midplane (half its 10 px width) and
3.5 px below it, widest at the rim. Its rings go from the diamond at the rim to a rounder shape
towards the crown: a steep girdle, crown facets and a small flat table on top, centred on the bulb.
The sprite's dark rim and its darker lower-right are drawn light, not paint (the game draws the
outline and lights the facets), so every facet is the crystal's mid blue (59) with a glass-like
material (barely metallic, smooth) whose glint the game's sun makes. The white core the sprite
shows through the top is the table, white (63) and glowing softly. The stalk is a 2 px
rod with its axis 1 px above the midplane: a narrower dark collar at the neck (55), then a mid-blue
knob (58) with a rounded end.

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
BOTTOM = 3.5 * U  # depth of the rounded underside
# The crown's rings from the rim in, (scale, height in px): a steep girdle, then crown facets that
# flatten towards the top (about 45 then 30 degrees), closed by a flat table. The ~30 degree
# facets are the ones that throw the game's sun back at its camera, the gem's glint.
CROWN = ((1.0, 0.0), (0.85, 3.0), (0.55, 4.4), (0.32, 5.0))
BOTTOM_RINGS = (1.0,)  # the underside is one fan: nobody sees it from the game camera
BODY = 59  # the crystal's mid blue, on every facet but the table
CORE = 63  # the white core that glows through the table (the sprite's bright centre)
CORE_GLOW = 0.4
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
    p = 1.0 + (1.0 - s) ** 1.5  # stays a diamond near the rim, rounder towards the crown
    ang = math.atan2(d[1], d[0])
    c, sn = math.cos(ang), math.sin(ang)
    r = (abs(c) ** p + abs(sn) ** p) ** (-1 / p)
    return (s * r * c * rx, s * r * sn * ry)


def bulb(mats, slot, cx, cy, rx, ry, coll):
    import bmesh
    bm = bmesh.new()
    dirs = unit_dirs()
    n = len(dirs)

    def ring(s, z):
        return [bm.verts.new((cx + x, cy + y, z)) for x, y in (ring_point(d, s, rx, ry) for d in dirs)]

    rim = ring(1.0, 0.0)
    top = [rim] + [ring(s, z * U) for s, z in CROWN[1:]]
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
                face = bm.faces.new(f)
                face.material_index = slot[colour(f)]

    bands(top, None, lambda f: BODY)
    face = bm.faces.new(top[-1])  # the table
    face.material_index = slot[CORE]
    bands(bot, bot_apex, lambda f: BODY)
    return common.mesh_object(NAME, bm, mats, coll, smooth=False)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    mats, slot = [], {}
    for i in (BODY, CORE, NECK, KNOB):
        slot[i] = len(mats)
        # A crystal: glossy, barely metallic, so the game's sun and environment make its glint.
        mats.append(common.palette_material(sprite, i, NAME, metallic=0.1, roughness=0.15,
                                            emission_strength=CORE_GLOW if i == CORE else 0.0))

    cy = lib.ey(7.5, H)
    gem = bulb(mats, slot, 0.0, cy, 5.0 * U, 4.5 * U, coll)

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
    # The collar between the two steps (row 12) is the dark neck row; the rest is the knob's blue
    # (the bulb's dark rim at row 11 is the sprite's outline, which the game draws).
    for f in bm.faces:
        ys = [v.co.y for v in f.verts]
        if max(ys) - min(ys) < 1e-6:
            continue
        if min(ys) >= lib.ey(13.0, H) - 1e-6 and max(ys) <= lib.ey(12.0, H) + 1e-6:
            f.material_index = slot[NECK]
    stalk = common.mesh_object(f"{NAME}_stalk", bm, mats, coll, smooth=True)

    objects = [gem, stalk]
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    lib.preview(objects, ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
