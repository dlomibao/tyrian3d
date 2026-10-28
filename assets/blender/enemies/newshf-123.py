"""Grey straight-winged fighter (newshf.shp frames 123, 125, 127): a 3D version of its sprite.

Seen in episodes 1, 3 and 4. It flies nose down the screen: a round fuselage with a needle nose
(5 px across with its outline), a straight wing across rows 11-16 with a stepped leading edge that
deepens to row 17 beside the fuselage, a blocky tailplane (rows 2-5), an upright fin poking out
behind it (rows 0-1) and a dark glass canopy dome where the wing meets the fuselage (rows 13-16).

The frames rock it: 125 is level with a 21 px span, 123 and 127 narrow the span to 19 px and shift
the fin and canopy a pixel left (123) or right (127). Each frame gets its own model built to its
own outline (newshf-123, -f2, -f3), barely banked (a few degrees) so the wings stay level, with the
canopy and fin leaned toward the raised side.

The wing and tailplane are bevelled plates. The craft is painted grey metal: each part takes one
mid-tone palette index all over (the sprite's light spine, tip highlights and lighter wing band
are sheen, and its dark outline ring is drawn by the game's outline), with a painted-metal
material so the game's lights make the shine. The canopy is dark glass, glossy.

Run: blender --background --python assets/blender/enemies/newshf-123.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b023 as lib  # noqa: E402
import common  # noqa: E402  (lib_b023 puts assets/blender on the path)

NAME = "newshf-123"
P = 1 / 12
X0 = lib.px(12)  # the fuselage's centre line (column 12)
ROLL = math.radians(3)  # a slight bank on the rocked frames; the sprite keeps the craft level

# Per frame: wing and tailplane outlines as (column edge, row edge), the bank (positive lifts the
# left side) and the lean of the canopy and fin in px.
FRAMES = {
    123: dict(
        wing=[(3, 11), (22, 11), (22, 16), (21, 16), (21, 17), (18, 17), (18, 18), (7, 18), (7, 17),
              (4, 17), (4, 16), (3, 16)],
        tail=[(7, 2), (18, 2), (18, 5), (16, 5), (16, 6), (9, 6), (9, 5), (7, 5)],
        roll=-ROLL, lean=-1.0),
    125: dict(
        wing=[(2, 11), (23, 11), (23, 16), (22, 16), (22, 17), (19, 17), (19, 18), (6, 18), (6, 17),
              (3, 17), (3, 16), (2, 16)],
        tail=[(6, 2), (19, 2), (19, 5), (17, 5), (17, 6), (8, 6), (8, 5), (6, 5)],
        roll=0.0, lean=0.0),
    127: dict(
        wing=[(3, 11), (22, 11), (22, 16), (21, 16), (21, 17), (18, 17), (18, 18), (7, 18), (7, 17),
              (4, 17), (4, 16), (3, 16)],
        tail=[(7, 2), (18, 2), (18, 5), (16, 5), (16, 6), (9, 6), (9, 5), (7, 5)],
        roll=ROLL, lean=1.0),
}

# Parts and their mid-tone palette indices (sprite colours: 5 = 69, 6 = 81, 7 = 93, 3 = 40 grey).
FUSELAGE, WING, TAIL, FIN, CANOPY = 0, 1, 2, 3, 4
PART_INDEX = {FUSELAGE: 7, WING: 6, TAIL: 5, FIN: 7, CANOPY: 3}


def _signed_area(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) / 2


def _inset(pts, d):
    """Offset a counter-clockwise polygon inward by d (mitred corners)."""
    out = []
    n = len(pts)
    for i in range(n):
        (xa, ya), (xb, yb), (xc, yc) = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1 = (xb - xa, yb - ya)
        e2 = (xc - xb, yc - yb)
        l1 = math.hypot(*e1)
        l2 = math.hypot(*e2)
        n1 = (-e1[1] / l1, e1[0] / l1)  # inward normal of a CCW edge
        n2 = (-e2[1] / l2, e2[0] / l2)
        m = (n1[0] + n2[0], n1[1] + n2[1])
        dot = m[0] * n1[0] + m[1] * n1[1]
        out.append((xb + m[0] * d / dot, yb + m[1] * d / dot))
    return out


def bevel_plate(bm, outline_cr, z_top, z_edge, z_bot, inset, part_layer, part, flat_layer):
    """A plate with the sprite outline (column/row edges) at z_edge..z_bot and its top inset by
    `inset` (units) at z_top: the sloped band between is a bevel."""
    pts = [(lib.ex(c), lib.ey(r)) for c, r in outline_cr]
    if _signed_area(pts) < 0:
        pts.reverse()
    inner = _inset(pts, inset)
    top = [bm.verts.new((x, y, z_top)) for x, y in inner]
    edge = [bm.verts.new((x, y, z_edge)) for x, y in pts]
    bot = [bm.verts.new((x, y, z_bot)) for x, y in pts]
    n = len(pts)
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((edge[i], edge[j], top[j], top[i])))
        faces.append(bm.faces.new((bot[i], bot[j], edge[j], edge[i])))
    for f in faces:
        f[flat_layer] = 1
        f[part_layer] = part


def wedge_fin(bm, xc, outline_yz, t_bot, t_top, part_layer, flat_layer):
    """An upright fin at X = xc, `outline_yz` its side outline; half-thickness t_bot at its lowest
    point tapering to t_top at its highest."""
    zs = [z for _, z in outline_yz]
    z0, z1 = min(zs), max(zs)

    def t(z):
        return t_bot + (t_top - t_bot) * (z - z0) / (z1 - z0)
    left = [bm.verts.new((xc - t(z), y, z)) for y, z in outline_yz]
    right = [bm.verts.new((xc + t(z), y, z)) for y, z in outline_yz]
    faces = [bm.faces.new(left), bm.faces.new(list(reversed(right)))]
    n = len(outline_yz)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((left[i], left[j], right[j], right[i])))
    for f in faces:
        f[flat_layer] = 1
        f[part_layer] = FIN


def build_frame(sprite, model, frame):
    spec = FRAMES[frame["index"]]
    coll = common.reset_collection(model)
    bm = bmesh.new()
    part_layer = bm.faces.layers.int.new("part")  # 0 (FUSELAGE) unless tagged
    flat_layer = bm.faces.layers.int.new("flat")
    lean = spec["lean"] * P

    # Fuselage, round: (row edge, half width px, half height px). 5 px across (with the outline)
    # behind the wing and along the nose, 7 px at the wing-root fairing (rows 17-19).
    body = [(1.6, 0.0, 0.0), (2.2, 1.1, 1.0), (3.0, 1.6, 1.4), (5.6, 1.9, 1.7), (6.1, 2.6, 2.3),
            (8.5, 2.6, 2.4), (11.0, 2.6, 2.4), (12.5, 2.8, 2.5), (16.8, 2.9, 2.5), (17.2, 3.6, 2.4),
            (19.8, 3.6, 2.2), (20.2, 2.6, 2.1), (21.5, 2.6, 2.0), (23.9, 2.5, 1.8), (24.2, 1.6, 1.4),
            (25.5, 1.6, 1.25), (26.9, 1.5, 1.1), (27.2, 0.8, 0.6), (28.0, 0.0, 0.0)]
    lib.ellipse_loft(bm, X0, [(lib.ey(r), w * P, h * P, 0.0) for r, w, h in body], sides=12, mats=0)

    # Wing: a ~1 px plate a little above the fuselage's midline, its top inset by the bevel.
    bevel_plate(bm, spec["wing"], 0.85 * P, 0.0, -0.25 * P, 0.45 * P, part_layer, WING, flat_layer)
    # Tailplane: a blocky ~1 px plate.
    bevel_plate(bm, spec["tail"], 1.0 * P, 0.1 * P, -0.2 * P, 0.45 * P, part_layer, TAIL, flat_layer)

    # Upright fin over the tail, out past it to row 0, leaning with the bank.
    wedge_fin(bm, X0 + lean * 0.85, [(lib.ey(0.05), 1.0 * P), (lib.ey(6.5), 0.6 * P), (lib.ey(5.0), 1.8 * P),
                                      (lib.ey(2.4), 3.3 * P), (lib.ey(0.05), 3.3 * P)],
              1.25 * P, 0.5 * P, part_layer, flat_layer)

    # Glass canopy dome where the wing meets the fuselage (rows 13-16, 3 px wide), rising ~2 px
    # above the fuselage's top.
    start = len(bm.faces)
    lib.dome(bm, X0 + lean, lib.ey(15.0), 1.8 * P, 1.6 * P, 2.0 * P, 2.7 * P, mat_index=0, segs=12, rings=5)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start:]:
        f[part_layer] = CANOPY

    # Bank about the long axis.
    if spec["roll"]:
        m = Matrix.Translation((X0, 0, 0)) @ Matrix.Rotation(spec["roll"], 4, "Y") @ Matrix.Translation((-X0, 0, 0))
        bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()

    # Paint: each part one mid-tone index all over; painted grey metal, the canopy glossy glass.
    slots = {}
    mats = []
    for f in bm.faces:
        part = f[part_layer]
        index = PART_INDEX[part]
        glass = part == CANOPY
        key = (index, glass)
        if key not in slots:
            if glass:
                mat = common.palette_material(sprite, index, f"{NAME}-glass", metallic=0.05, roughness=0.08)
            else:
                mat = common.palette_material(sprite, index, NAME, metallic=0.45, roughness=0.4)
            slots[key] = len(mats)
            mats.append(mat)
        f.material_index = slots[key]

    flags = [bool(f[flat_layer]) for f in bm.faces]
    obj = common.mesh_object(model, bm, mats, coll, smooth=True)
    for poly, flat in zip(obj.data.polygons, flags):
        poly.use_smooth = not flat
    return [obj]


def build(sprite):
    models = []
    for k, frame in enumerate(sprite["frames"]):
        model = NAME if k == 0 else f"{NAME}-f{k + 1}"
        models.append((model, build_frame(sprite, model, frame), lib.frame_sprites(sprite, [frame["index"]])))
    return models


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
