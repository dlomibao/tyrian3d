"""MicroSol FrontBlaster (sidekicks 20, 22 and 26, tyrian.shp#9 frame 83): a 3D version of its sprite.

A 24x28 sidekick, one frame (no animation), symmetric about column edge 13. Read as a small
twin-gun drone shaped like a horseshoe, nose up the screen (it fires forward):

- Twin gun pods (columns 7-12 and 14-19, rows 3-14): two long round barrels' housings, shaded
  round in the sprite (a highlight band on each, darker sides), flat-fronted with a dark muzzle
  bore. They are the tallest parts.
- The centre slot between them (columns 11-15, rows 3-9): dark, cut in, holding a short centre
  barrel and its breech block (the 4 10 10 4 pixels at row 8).
- The deck (columns 3-23, rows 6-15): a flat armour plate with chamfered edges under everything,
  a belly plate under it so the drone has a bottom from the side.
- Shoulder lamps (columns 4-8 and 18-22, rows 6-10): raised housings at the deck's front corners,
  each with a big red lens (the saturated 113-119 pixels with their bright core): emissive glass.
- The bronze cone (columns 9-17, rows 9-18): the sprite's tan diamond, its bright centre column a
  ridge, its lower rows in shadow: a faceted bronze bicone (an engine/reactor housing) lying along
  the drone's axis, its back half poking out between the prongs.
- The two prongs (columns 3-8 and 18-23, rows 10-22): chamfered blades sweeping back to points,
  lower toward the tips, split by a seam at row 15 (the dark 5 3 102 pixels) and carrying a red
  tail lamp at rows 16-18.

Metal parts take their sprite mid-tones; the sprite's bright streaks are sheen and its dark right
sides shadow, left to the game's lighting.

Run: blender --background --python assets/blender/sidekicks/microsol-frontblaster.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "sidekick-microsol-frontblaster"
MODEL = "sidekicks/microsol-frontblaster"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel
AXIS = 13.0  # the sprite's mirror (column edge)


def wx(c):
    """Sprite column edge to X (the 24 px block is centred on the origin)."""
    return (c - 12) / 12


def wy(r):
    """Sprite row edge to Y."""
    return (14 - r) / 12


def mirror_poly(poly):
    return [(2 * AXIS - c, r) for c, r in reversed(poly)]


def _ccw(pts):
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return pts if area > 0 else list(reversed(pts))


def _inset(pts, d):
    """Offset a CCW polygon inward by d (mitred, clamped)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e0 = (p1[0] - p0[0], p1[1] - p0[1])
        e1 = (p2[0] - p1[0], p2[1] - p1[1])
        l0 = math.hypot(*e0) or 1
        l1 = math.hypot(*e1) or 1
        n0 = (-e0[1] / l0, e0[0] / l0)  # inward normal of a CCW edge
        n1 = (-e1[1] / l1, e1[0] / l1)
        m = (n0[0] + n1[0], n0[1] + n1[1])
        ml = math.hypot(*m) or 1
        m = (m[0] / ml, m[1] / ml)
        cos = max(0.35, m[0] * n0[0] + m[1] * n0[1])
        k = d / cos
        out.append((p1[0] + m[0] * k, p1[1] + m[1] * k))
    return out


def plate(bm, poly, z0, z1, mat, flat, chamfer=0.6, bottom_chamfer=0.0, ztop=None):
    """A chamfered plate: outline `poly` in sprite (col, row), from z0 to z1 px, the top edge
    bevelled by `chamfer` px (and the bottom by `bottom_chamfer`). `ztop(c, r)` (px) overrides z1
    per vertex, for plates that slope."""
    pts = _ccw([(wx(c), wy(r)) for c, r in poly])
    src = [(c, r) for c, r in poly]

    def top_z(x, y):
        if ztop is None:
            return z1
        return ztop(x / P + 12, 14 - y / P)

    ch = chamfer * P
    rings = []
    if bottom_chamfer:
        bc = bottom_chamfer * P
        rings.append([(x, y, z0 * P) for x, y in _inset(pts, bc)])
        rings.append([(x, y, z0 * P + bc) for x, y in pts])
    else:
        rings.append([(x, y, z0 * P) for x, y in pts])
    if chamfer:
        rings.append([(x, y, top_z(x, y) * P - ch) for x, y in pts])
        rings.append([(x, y, top_z(x, y) * P) for x, y in _inset(pts, ch)])
    else:
        rings.append([(x, y, top_z(x, y) * P) for x, y in pts])
    del src
    vr = [[bm.verts.new(co) for co in ring] for ring in rings]
    faces = [bm.faces.new(list(reversed(vr[0]))), bm.faces.new(vr[-1])]
    n = len(pts)
    for a, b in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    for f in faces:
        f.material_index = mat
        f[flat] = 1
    return faces


def tube(bm, sections, mat, sides=12, c=AXIS, phase=0.5, flat=None, faceted=False):
    """A loft along Y: sections (row, half width, half height, z centre) in px about column c.
    The end caps are flat shaded (with `flat`), and every face with `faceted`."""
    x = wx(c)
    rings = []
    for r, w, h, z in sections:
        if w == 0 and h == 0:
            rings.append([bm.verts.new((x, wy(r), z * P))])
            continue
        rings.append([bm.verts.new((x + w * P * math.cos(a), wy(r), z * P + h * P * math.sin(a)))
                      for a in (2 * math.pi * (i + phase) / sides for i in range(sides))])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            faces.append(bm.faces.new(face))
    if len(rings[0]) > 1:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
        if flat is not None:
            faces[-1][flat] = 1
    if len(rings[-1]) > 1:
        faces.append(bm.faces.new(rings[-1]))
        if flat is not None:
            faces[-1][flat] = 1
    for f in faces:
        f.material_index = mat
        if faceted:
            f[flat] = 1
    return faces


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.55, roughness=0.38),  # 0 deck
        pal(11, metallic=0.6, roughness=0.32),  # 1 gun pods
        pal(9, metallic=0.55, roughness=0.4),  # 2 shoulder lamp housings
        pal(2, metallic=0.3, roughness=0.55),  # 3 dark: slot, seams, bores, belly
        pal(115, metallic=0.0, roughness=0.15, emission_strength=2.5),  # 4 red lenses
        pal(119, metallic=0.0, roughness=0.1, emission_strength=4.0),  # 5 lens hot cores
        pal(26, metallic=0.75, roughness=0.3),  # 6 bronze cone
        pal(8, metallic=0.55, roughness=0.4),  # 7 prongs
        pal(13, metallic=0.6, roughness=0.3),  # 8 bright trim: lamp bezels, muzzle rings
        pal(118, metallic=0.0, roughness=0.15, emission_strength=2.5),  # 9 tail lamps
        pal(5, metallic=0.45, roughness=0.5),  # 10 dark grey: belly, barrel
    ]
    DECK, POD, HOUSING, DARK, RED, CORE, BRONZE, PRONG, TRIM, TAIL, GREY = range(len(mats))
    bm = bmesh.new()
    flat = bm.faces.layers.int.new("flat")

    def both(poly):
        return (poly, mirror_poly(poly))

    # Belly: a smaller plate under the deck, so the drone has a bottom and isn't a flat tile.
    plate(bm, [(5.5, 8.0), (20.5, 8.0), (20.5, 14.2), (5.5, 14.2)], -2.2, -0.4, GREY, flat,
          chamfer=0.6, bottom_chamfer=0.6)

    # Deck: one chamfered plate across the drone, front corners cut back diagonally, the rear edge
    # straight between the prongs (the bronze cone pokes out over it).
    deck = [(8.0, 5.6), (18.0, 5.6), (22.8, 8.0), (23.0, 14.6), (3.0, 14.6), (3.2, 8.0)]
    plate(bm, deck, -0.6, 2.4, DECK, flat, chamfer=0.7, bottom_chamfer=0.5)

    # Centre slot: a dark recessed channel between the pods holding the centre barrel.
    plate(bm, [(11.4, 3.6), (14.6, 3.6), (14.6, 9.4), (11.4, 9.4)], 0.0, 2.8, DARK, flat, chamfer=0.2)
    # Breech block at row 8 and the centre barrel running forward from it.
    plate(bm, [(11.6, 7.6), (14.4, 7.6), (14.4, 9.6), (11.6, 9.6)], 0.5, 4.3, DECK, flat, chamfer=0.5)
    tube(bm, [(4.3, 0.95, 0.95, 3.4), (7.8, 0.95, 0.95, 3.4)], GREY, sides=10, flat=flat)
    tube(bm, [(4.1, 1.15, 1.15, 3.4), (4.6, 1.15, 1.15, 3.4)], TRIM, sides=10, flat=flat)
    tube(bm, [(4.0, 0.55, 0.55, 3.4), (4.35, 0.55, 0.55, 3.4)], DARK, sides=8)

    # Twin gun pods: round housings along Y, flat fronts with a bright muzzle ring and a dark bore.
    for c in (9.5, 2 * AXIS - 9.5):
        # The housing narrows behind row 9 and tucks down into the deck by row 13, so the bronze
        # cone between the pods shows as wide as the sprite draws it.
        d = -1 if c < AXIS else 1
        tube(bm, [(3.5, 1.9, 2.1, 3.9), (3.9, 2.3, 2.5, 3.9), (5.0, 2.4, 2.65, 3.9),
                  (9.0, 2.4, 2.65, 3.9), (11.0, 2.0, 2.3, 3.6), (12.6, 1.5, 1.6, 3.1),
                  (13.4, 0.8, 0.8, 2.7)],
             POD, sides=14, c=c, flat=flat)
        # The gun barrel, a short muzzle standing out of the housing's front.
        tube(bm, [(2.9, 0.7, 0.7, 3.9), (3.6, 0.7, 0.7, 3.9)], GREY, sides=10, c=c, flat=flat)
        del d
        tube(bm, [(3.2, 1.45, 1.6, 3.9), (3.6, 1.45, 1.6, 3.9)], TRIM, sides=14, c=c, flat=flat)
        tube(bm, [(2.8, 0.42, 0.42, 3.9), (3.05, 0.42, 0.42, 3.9)], DARK, sides=8, c=c)
        # A seam ring around each pod where the barrel housing meets the body (row 9).
        tube(bm, [(8.4, 2.5, 2.75, 3.9), (8.85, 2.5, 2.75, 3.9)], GREY, sides=14, c=c, flat=flat)

    # Shoulder lamps: raised housings at the deck's front corners carrying the red lenses.
    for poly, lens, core in (
        ([(3.3, 7.6), (5.6, 5.9), (8.0, 6.3), (8.0, 10.2), (3.3, 10.2)],
         [(3.8, 7.7), (5.7, 6.4), (7.6, 6.8), (7.6, 9.6), (3.8, 9.6)],
         [(4.9, 7.7), (6.0, 7.3), (6.2, 8.8), (4.9, 8.9)]),
    ):
        for p, l, k in zip(both(poly), both(lens), both(core)):
            plate(bm, p, 1.0, 4.4, HOUSING, flat, chamfer=0.6)
            plate(bm, l, 3.6, 4.7, RED, flat, chamfer=0.35)
            plate(bm, k, 4.2, 4.95, CORE, flat, chamfer=0.25)

    # Bronze cone: a faceted bicone along the axis, a ridge on top (the bright centre column).
    # Two clean pyramids joined by a short band: crisp triangular facets like the sprite's diamond.
    tube(bm, [(8.8, 0, 0, 3.3), (13.2, 3.9, 3.6, 2.9), (14.3, 3.9, 3.6, 2.8), (17.9, 0, 0, 2.4)],
         BRONZE, sides=8, phase=0.0, flat=flat, faceted=True)

    # Prongs: chamfered blades sweeping back to points, lower toward the tips, split by a seam at
    # row 15, with a red tail lamp at rows 16-18.
    def prong_top(c, r):
        return 3.6 - max(0.0, r - 12.0) * 0.17

    fore = [(3.0, 10.0), (8.3, 10.0), (8.3, 15.0), (3.0, 15.0)]
    aft = [(3.1, 15.6), (8.2, 15.6), (8.1, 21.0), (7.3, 22.0), (6.6, 22.0), (3.7, 19.0), (3.1, 18.2)]
    seam = [(3.4, 14.8), (7.9, 14.8), (7.9, 15.8), (3.4, 15.8)]
    lamp = [(3.9, 16.4), (7.4, 16.4), (7.4, 18.1), (3.9, 18.1)]
    lens = [(4.25, 16.7), (7.05, 16.7), (7.05, 17.9), (4.25, 17.9)]
    for f, a, s, lp, ln in zip(both(fore), both(aft), both(seam), both(lamp), both(lens)):
        plate(bm, f, -0.8, None, PRONG, flat, chamfer=0.6, bottom_chamfer=0.5, ztop=prong_top)
        plate(bm, a, -0.6, None, PRONG, flat, chamfer=0.55, bottom_chamfer=0.4, ztop=prong_top)
        plate(bm, s, -0.4, 1.6, DARK, flat, chamfer=0.0)
        plate(bm, lp, 1.0, 3.25, TRIM, flat, chamfer=0.35)
        plate(bm, ln, 2.0, 3.4, TAIL, flat, chamfer=0.25)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    attr = obj.data.attributes["flat"]
    for poly, a in zip(obj.data.polygons, attr.data):
        if a.value:
            poly.use_smooth = False
    obj.data.attributes.remove(attr)
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = ROOT / "reference" / "models" / NAME / frame["image"]
        common.render_preview([obj], out, ref, size=frame["size"])


if __name__ == "__main__":
    main()
