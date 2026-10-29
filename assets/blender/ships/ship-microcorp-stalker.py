"""Microcorp Stalker (player ship, tyrian.shp#8 sprite 195 and its banking frames 191-199).

Traced from its concept (assets/blender/features/concepts/ship-microcorp-stalker.jpg, registered
onto the sprite as assets/blender/textures/ship-microcorp-stalker/concept.png): a grey metal
fighter with a round fuselage running the whole length, an ogive nose cone with a seam behind it,
a framed hexagonal dark canopy on the forebody, two short ogive side pods flanking the cockpit whose
open rear intakes glow red (the sprite's two red "neck lights"), a narrower neck with vents behind
the pods, a mid-body band and a rear body ending in a dark nozzle with an orange-red exhaust glow.
Two forward-swept wings: a dark base plate carrying raised panels (a bright leading-edge strip, an
outer rail along the tip, a fore panel with a cut-in vent slot, an aft panel), split by recessed
seams. Box-shaped wing roots with a bright chamfer strip and a dark vent bay sit beside the body,
and two short engine pods hang under the wings' trailing edges. The outline stays inside the
sprite's. The sprite is centred on column 11, half a pixel left of the 24 px block's centre.

Run: blender --background --python assets/blender/ships/ship-microcorp-stalker.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import common  # noqa: E402
from lib_b001 import loft_path  # noqa: E402

NAME = "ship-microcorp-stalker"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel
AXIS = 11  # the sprite's mirror column; the model is built about X = 0 and shifted to it at the end


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


def clips(poly, *planes):
    for a, b, c in planes:
        poly = clip(poly, a, b, c)
    return poly


def plate(bm, poly, z0, z1, mat_index, flat, mirror=False):
    """A flat plate from z0 to z1 (px) with the outline `poly` in sprite (col, row) coordinates."""
    pts = [(sx(c), ey(r)) for c, r in poly]
    if mirror:
        pts = [(-x, y) for x, y in pts]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()
    top = [bm.verts.new((x, y, z1 * P)) for x, y in pts]
    bot = [bm.verts.new((x, y, z0 * P)) for x, y in pts]
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        faces.append(bm.faces.new((bot[i], bot[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat_index
        f[flat] = 1
    return top + bot


def tube(bm, sections, mat_index, sides=12, x=0.0, mirror=False, **kw):
    """A round loft along the sprite: sections are (row, half width, half height, z centre) in px,
    centred on sprite column `x` offset (px from the axis)."""
    for s in ((1, -1) if mirror else (1,)):
        loft_path(bm, [(ey(r), s * x * P, w * P, h * P, z * P) for r, w, h, z in sections],
                  sides=sides, mat_index=mat_index, **kw)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    # Grey metal throughout, each part at its sprite mid-tone; the sprite's bright streaks and
    # dark right sides are its drawn light and shine, left to the game's lighting.
    mats = [
        pal(10, metallic=0.5, roughness=0.4),  # 0 fuselage
        pal(8, metallic=0.45, roughness=0.42),  # 1 wing panels
        pal(11, metallic=0.5, roughness=0.36),  # 2 bright chamfers and leading edges
        pal(10, metallic=0.6, roughness=0.32),  # 3 nose cone
        pal(9, metallic=0.5, roughness=0.38),  # 4 side pods
        pal(2, metallic=0.1, roughness=0.04),  # 5 dark cockpit glass, glossy
        pal(117, emission_strength=3.0),  # 6 red pod intakes
        pal(120, emission_strength=5.0),  # 7 engine glow core
        pal(7, metallic=0.5, roughness=0.42),  # 8 neck, a darker grey
        pal(9, metallic=0.5, roughness=0.38),  # 9 canopy frame
        pal(7, metallic=0.45, roughness=0.42),  # 10 wing roots and engine pods
        pal(3, metallic=0.4, roughness=0.55),  # 11 dark base plate, seams, vents, nozzle
        pal(116, emission_strength=3.0),  # 12 engine glow rim
    ]
    HULL, WING, BRIGHT, NOSE, POD, GLASS, RED, GLOW, NECK, FRAME, ROOT_, DARK, GLOW2 = range(13)
    bm = bmesh.new()
    flat = bm.faces.layers.int.new("flat")  # faces to flat-shade (hard edges)
    ZC = 0.4  # fuselage axis height, px

    # Nose cone (rows 0-3): an ogive, round, ending at a seam ring where the forebody starts.
    tube(bm, [(0.15, 0, 0, ZC - 0.6), (0.5, 0.7, 0.65, ZC - 0.35), (1.0, 1.2, 1.15, ZC - 0.15),
              (1.6, 1.55, 1.55, ZC), (2.2, 1.8, 1.8, ZC), (2.85, 2.15, 2.15, ZC)], NOSE, sides=16)
    # Forebody (rows 3-11.4): a round tube, a touch wider than the nose's end (the seam).
    tube(bm, [(2.85, 2.35, 2.35, ZC), (4.0, 2.5, 2.5, ZC), (11.0, 2.55, 2.5, ZC), (11.4, 2.3, 2.25, ZC)],
         HULL, sides=16)
    # Canopy (rows 5.6-11): a faceted hexagonal dark glass bubble raised in a grey frame.
    tube(bm, [(5.35, 0.45, 0.25, 2.45), (5.9, 1.25, 0.8, 2.45), (7.0, 1.75, 0.95, 2.5), (10.3, 1.75, 0.95, 2.5),
              (11.1, 1.2, 0.7, 2.5), (11.35, 0.5, 0.3, 2.5)], FRAME, sides=10)
    tube(bm, [(5.55, 0, 0, 2.8), (5.9, 0.75, 0.6, 2.7), (7.1, 1.4, 1.15, 2.6), (10.1, 1.4, 1.15, 2.6),
              (10.9, 0.85, 0.75, 2.6), (11.05, 0, 0, 2.7)], GLASS, sides=8)
    # Canopy crossbar at the front pane's joint (row 7.2).
    start = len(bm.faces)
    tube(bm, [(7.05, 1.35, 1.2, 2.6), (7.35, 1.35, 1.2, 2.6)], FRAME, sides=8)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start:]:
        f[flat] = 1

    # Side pods (rows 5.4-13.3) flanking the cockpit, centred on columns 8 and 14: ogive fronts,
    # and open rear intakes glowing red (the sprite's red pixels at rows 12-13).
    tube(bm, [(5.4, 0, 0, 0.9), (6.0, 0.7, 0.6, 0.9), (7.0, 1.1, 1.0, 0.9), (8.5, 1.3, 1.15, 0.9),
              (11.2, 1.35, 1.2, 0.9), (11.7, 1.35, 1.2, 0.9)], POD, x=3.0, mirror=True)
    tube(bm, [(11.7, 1.4, 1.25, 0.9), (12.1, 1.4, 1.25, 0.9)], DARK, x=3.0, mirror=True)
    tube(bm, [(12.1, 1.1, 1.0, 0.9), (13.4, 1.1, 0.95, 0.9), (13.95, 0.9, 0.8, 0.9)], RED, x=3.0, mirror=True, sides=10)

    # Neck (rows 11.4-13.4): narrower, darker and lower, between the pods.
    tube(bm, [(11.3, 1.6, 2.1, ZC), (13.5, 1.6, 2.1, ZC)], NECK, sides=12)
    # Its vents: dark slots either side of the top.
    for s in (-1, 1):
        plate(bm, [(9.85 if s < 0 else 12.45, 11.7), (10.55 if s < 0 else 13.15, 11.7),
                   (10.55 if s < 0 else 13.15, 12.9), (9.85 if s < 0 else 12.45, 12.9)], 0.5, 2.2, DARK, flat)
    # Mid band (rows 13.4-16.6) and rear body (16.6-25), a seam step between them. The band is a
    # little wider than the concept's so it covers the sprite's outline ring at rows 14-16.
    tube(bm, [(13.3, 2.3, 2.3, ZC), (13.6, 3.1, 2.6, ZC), (16.6, 3.1, 2.6, ZC)], HULL, sides=16)
    tube(bm, [(16.55, 2.35, 2.35, ZC), (24.0, 2.35, 2.35, ZC), (24.6, 2.1, 2.05, ZC), (25.0, 1.5, 1.4, ZC)],
         HULL, sides=16)
    # Engine: a dark nozzle (rows 24.2-25.4) and the orange-red exhaust dome in its mouth.
    tube(bm, [(24.2, 2.2, 1.75, ZC - 0.2), (25.6, 2.15, 1.7, ZC - 0.2)], DARK, sides=14)
    tube(bm, [(25.0, 1.55, 1.25, ZC - 0.2), (26.0, 1.5, 1.2, ZC - 0.2), (26.6, 1.1, 0.85, ZC - 0.2),
              (26.9, 0, 0, ZC - 0.2)], GLOW2, sides=14)
    tube(bm, [(25.2, 0.9, 1.45, ZC - 0.2), (26.4, 0.9, 1.3, ZC - 0.2), (26.85, 0, 0, ZC - 0.2)], GLOW, sides=10)

    # Wings (left; the right is its mirror): sprite (col, row) outline, forward-swept to a tip at
    # columns 1-2 row 11, trailing edge following the sprite's staircase.
    outer = [(1.05, 11.1), (2.6, 11.1), (7.5, 16.0), (9.3, 16.0), (9.3, 22.5), (7.0, 24.8), (5.3, 24.8),
             (2.0, 18.0), (1.05, 18.0)]
    # d = row - col runs across the leading edge (the outline at d = 8.5).
    lead = clips(outer, (-1, 1, 9.9), (-1, 0, -2.35), (0, 1, 16.0), (1, 0, 7.2))
    rail = clips(outer, (1, 0, 2.1))
    fore = clips(outer, (1, -1, -10.15), (-1, 0, -2.35), (0, 1, 17.0), (1, 0, 7.0))
    fore_a = clips(fore, (-1, 1, 11.0))
    fore_b = clips(fore, (1, -1, -11.6))
    fore_c = clips(fore, (1, -1, -11.0), (-1, 1, 11.6), (1, 0, 3.1))
    fore_d = clips(fore, (1, -1, -11.0), (-1, 1, 11.6), (-1, 0, -5.2))
    aft = clips(outer, (0, -1, -17.25), (-1, 0, -2.35), (1, 0, 6.8))
    wing_verts = []
    for mirror in (False, True):
        wing_verts += plate(bm, outer, 0.0, 0.9, DARK, flat, mirror)
        wing_verts += plate(bm, rail, 0.6, 1.7, WING, flat, mirror)
        wing_verts += plate(bm, lead, 0.6, 1.5, BRIGHT, flat, mirror)
        for poly in (fore_a, fore_b, fore_c, fore_d, aft):
            wing_verts += plate(bm, poly, 0.6, 1.35, WING, flat, mirror)
    # Tilted up toward the tips.
    for v in wing_verts:
        v.co.z += max(0.0, abs(v.co.x) - 4.0 * P) * 0.16

    # Wing roots (rows 16-21.6, columns 6.9-9.3): boxes beside the body, a bright chamfer strip on
    # the outer edge (the sprite's bright column 7) and a dark vent bay cut into the top.
    for mirror in (False, True):
        plate(bm, [(6.9, 16.7), (7.5, 16.1), (7.6, 16.1), (7.6, 21.6), (6.9, 21.6)], 0.0, 2.0, BRIGHT, flat, mirror)
        plate(bm, [(7.6, 16.1), (8.3, 16.1), (8.3, 21.6), (7.6, 21.6)], 0.0, 2.4, ROOT_, flat, mirror)
        plate(bm, [(8.3, 16.1), (9.4, 16.1), (9.4, 17.0), (8.3, 17.0)], 0.0, 2.4, ROOT_, flat, mirror)
        plate(bm, [(8.3, 19.8), (9.4, 19.8), (9.4, 21.6), (8.3, 21.6)], 0.0, 2.4, ROOT_, flat, mirror)
        plate(bm, [(8.3, 17.0), (9.4, 17.0), (9.4, 19.8), (8.3, 19.8)], 0.0, 1.5, DARK, flat, mirror)

    # Engine pods under the wings' trailing edges (rows 21-26, centred on columns 7.6 and 15.4),
    # each with a dark intake at its front.
    tube(bm, [(20.8, 1.1, 0.9, 0.5), (21.4, 1.2, 1.0, 0.5)], DARK, x=3.9, mirror=True)
    tube(bm, [(21.2, 1.45, 1.2, 0.5), (21.6, 1.6, 1.35, 0.5), (25.0, 1.65, 1.4, 0.5), (25.6, 1.5, 1.25, 0.5),
              (25.95, 1.2, 0.95, 0.5)], ROOT_, x=3.9, mirror=True)

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
