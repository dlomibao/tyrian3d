"""Blue-armed gun walker (newsh2.shp frames 85 and 87, an assembly of 2 pieces): a 3D version of
its sprites.

Seen in episodes 1 and 3 (levels 1.25, 1.28, 1.3, 1.36, 3.17). Two 2x2 enemies side by side
(newsh2-85 on the left, newsh2-87 on the right, sprite.json `assemblyLayout`) make one 48x28 px
machine, mirror symmetric about the edge between pixel columns 22 and 23:

- a grey armoured hull at the top: a glowing exhaust vent with a grille across its back end,
  armoured housings either side and a dark blue glass screen in a frame in the middle;
- red thruster blocks with dark caps and glowing slits beside the hull, and chunky bright blue
  T-shaped arm plates on top of them that drop into blades with darker tips;
- blue-steel legs down the outer edges: an inner rail and a segmented outer claw that arch down
  from the shoulders to a foot;
- under the hull a dark block with red-lit vent blocks, a grille box and an indicator light either
  side, and a pipe with two cables down to a round housing with a glowing red lens.

Remodelled on the concept (assets/blender/features/concepts/): each part sits where the concept,
registered to the sprite (assets/blender/textures/<name>/concept.png), draws it, kept inside the
sprite's outline, so the concept detail texture_bake.py projects onto it lands on the right part.
Hard surface throughout (bevelled plates and blocks, box-section rails); round only for the
housings' tops, the pipe, the eye housing and its lens.

It stands on the ground. The whole machine is built once in assembly coordinates and cut into
the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-87.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b083 as lib  # noqa: E402

NAME = "assembly-newsh2-87"
ROOT = common.repo_root(__file__)
PIECES = ["newsh2-85", "newsh2-87"]
# Screen pixel at the Blender origin: between the pieces' centres (cx 194 and 218, cy 43).
CX0, CY0 = 206, 43
G = lib.Grid(48, 28)  # both pieces, newsh2-85's left edge at u = 0
AXIS = 23.0  # mirror plane: the edge between columns 22 and 23
R2 = 1.4142  # lib.sweep with 4 sides puts its corners at 45 degrees: scale to get a box section


def prism(bm, outline, z0, z1, mat, chamfer=0.0, slope=None):
    """A hard-edged block over an outline of (u, v) pixel edges, from z0 up to z1 (or to
    z1 + slope * (v - v_first) for a top sloping down the sprite), its top edges chamfered by
    `chamfer` units (the top face inset by it)."""
    start = len(bm.faces)
    pts = [(G.x(u), G.y(v)) for u, v in outline]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts, outline = pts[::-1], outline[::-1]
    v0 = outline[0][1] if slope is None else min(v for _, v in outline)

    def top(v):
        return z1 if slope is None else z1 + slope * (v - v0)

    n = len(pts)
    inset = []
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1 = ((bx - ax), (by - ay))
        e2 = ((cx - bx), (cy - by))
        l1, l2 = (e1[0] ** 2 + e1[1] ** 2) ** 0.5, (e2[0] ** 2 + e2[1] ** 2) ** 0.5
        n1 = (-e1[1] / l1, e1[0] / l1)
        n2 = (-e2[1] / l2, e2[0] / l2)
        d = 1 + n1[0] * n2[0] + n1[1] * n2[1]
        inset.append((bx + chamfer * (n1[0] + n2[0]) / d, by + chamfer * (n1[1] + n2[1]) / d))
    bottom = [bm.verts.new((x, y, z0)) for x, y in pts]
    rings = [bottom]
    if chamfer > 0:
        rings.append([bm.verts.new((x, y, top(v) - chamfer)) for (x, y), (_, v) in zip(pts, outline)])
        rings.append([bm.verts.new((x, y, top(v))) for (x, y), (_, v) in zip(inset, outline)])
    else:
        rings.append([bm.verts.new((x, y, top(v))) for (x, y), (_, v) in zip(pts, outline)])
    bm.faces.new(list(reversed(bottom)))
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(rings[-1])
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start:]:
        f.material_index = mat
        f.smooth = False


def rect(u0, v0, u1, v1, cut=0.0):
    """A rectangle's outline, its corners cut by `cut` px."""
    if cut <= 0:
        return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    return [(u0 + cut, v0), (u1 - cut, v0), (u1, v0 + cut), (u1, v1 - cut), (u1 - cut, v1),
            (u0 + cut, v1), (u0, v1 - cut), (u0, v0 + cut)]


def rail(bm, path, mat):
    """A box-section rail along (u, v, top z, half width px) points, standing on the ground."""
    lib.sweep(bm, G, [(u, v, z / 2, w * R2, z / 2 * R2) for u, v, z, w in path], sides=4, mat=mat,
              smooth=False)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh2_87", **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.55, roughness=0.4),  # 0 grey hull
        pal(6, metallic=0.5, roughness=0.45),  # 1 darker grey screen frame
        pal(10, metallic=0.6, roughness=0.35),  # 2 light grey housings
        pal(129, metallic=0.3, roughness=0.08),  # 3 dark blue glass screen
        pal(132, metallic=0.5, roughness=0.25),  # 4 light blue screen rim
        pal(121, emission_strength=3.5),  # 5 vent glow
        pal(123, emission_strength=5.0),  # 6 vent hot core
        pal(2, metallic=0.2, roughness=0.7),  # 7 dark grilles and sockets
        pal(119, metallic=0.35, roughness=0.45),  # 8 red thruster blocks
        pal(155, metallic=0.35, roughness=0.35),  # 9 bright blue arm plates
        pal(154, metallic=0.35, roughness=0.35),  # 10 darker blue blade tips
        pal(56, metallic=0.3, roughness=0.55),  # 11 outer claw plates
        pal(57, metallic=0.3, roughness=0.5),  # 12 blue-steel inner rails, feet
        pal(116, metallic=0.3, roughness=0.5),  # 13 dark red vent blocks
        pal(118, emission_strength=3.0),  # 14 red lens
        pal(122, emission_strength=5.0),  # 15 lens core
        pal(6, metallic=0.55, roughness=0.35),  # 16 eye housing
        pal(120, emission_strength=3.0),  # 17 indicator lights, thruster slits
        pal(4, metallic=0.45, roughness=0.5),  # 18 dark grey caps, lower block, grille boxes
        pal(9, metallic=0.6, roughness=0.3),  # 19 pipe, bezel, knobs
        pal(117, emission_strength=1.0),  # 20 red vent glow
    ]
    (HULL, FRAME, POD, GLASS, RIM, VENT, VENTHOT, SLOT, REDBLOCK, ARM, TIP, CLAW, LEG, REDVENT, EYE,
     EYEHOT, HOUSING, LAMP, DARK, PIPE, REDGLOW) = range(21)
    bm = bmesh.new()

    # ---- left half (mirrored) ----
    start = len(bm.faces)
    # Armoured housing beside the screen (concept cols 14.6-19.1, rows 0-10): a rounded-top block,
    # the tallest part of the hull bar the arms.
    lib.dloft(bm, G, 16.9, [(0.0, 1.6, 0.48), (0.9, 2.2, 0.56), (9.0, 2.2, 0.56), (10.2, 1.7, 0.46)],
              sides=8, mat=POD, power=4.5)
    # Red thruster block (cols 10.3-14.2, rows 1.4-8.6) with a dark cap at its back end and glowing
    # slits down its outer side.
    lib.dloft(bm, G, 12.25, [(1.4, 1.6, 0.40), (2.2, 1.95, 0.46), (8.6, 1.95, 0.46)], sides=8,
              mat=REDBLOCK, power=4)
    prism(bm, rect(10.6, 1.0, 13.9, 2.7, 0.4), 0.0, 0.5, DARK, chamfer=0.04)
    prism(bm, rect(10.15, 3.8, 10.9, 6.6), 0.1, 0.36, LAMP)
    # Blue T-shaped arm plate: a tab out of the housing (rows 5-7.3) over a wide bar (cols 9.6-17.8,
    # rows 7.3-10), standing well above the thruster and housing ...
    prism(bm, [(13.2, 5.0), (17.8, 5.0), (17.8, 10.0), (10.2, 10.0), (9.6, 9.4), (9.6, 7.3),
               (12.6, 7.3), (12.6, 5.6)], 0.3, 0.62, ARM, chamfer=0.05)
    # ... and the blade dropping from it (cols 12.6-15), lowering to a darker chamfered tip.
    prism(bm, [(12.6, 9.9), (15.0, 9.9), (15.0, 15.0), (12.6, 15.0)], 0.1, 0.6, ARM, chamfer=0.04,
          slope=-0.024)
    prism(bm, [(12.6, 15.0), (15.0, 15.0), (15.0, 16.0), (14.1, 17.0), (13.4, 17.0), (12.6, 16.2)],
          0.08, 0.475, TIP, chamfer=0.035, slope=-0.024)
    # Leg: an inner rail from the shoulder (col 9, row 3.8) down to the foot, and a two-segment
    # outer claw (cols 5.3-7.1) branching off it at row 8, joined at a foot (rows 19.5-25).
    rail(bm, [(9.0, 3.8, 0.40, 0.95), (9.0, 9.0, 0.42, 1.0), (9.0, 17.0, 0.34, 1.0), (8.5, 20.5, 0.26, 0.9)], LEG)
    rail(bm, [(8.4, 7.9, 0.36, 0.9), (6.6, 9.3, 0.36, 0.9), (6.2, 10.6, 0.35, 0.9), (6.2, 14.1, 0.33, 0.9)], CLAW)
    rail(bm, [(6.2, 14.5, 0.32, 0.9), (6.2, 18.0, 0.30, 0.9), (6.6, 20.4, 0.26, 0.8)], CLAW)
    lib.dloft(bm, G, 7.6, [(19.6, 1.9, 0.27), (23.0, 1.7, 0.23), (24.9, 0.9, 0.12)], sides=6, mat=LEG, power=3)
    # Under the arm: an indicator light in a dark socket (col 11, row 11), a grille box with a knob
    # (cols 15.2-17.6) and a small blue-steel plate (col 18).
    prism(bm, rect(10.2, 10.0, 12.6, 12.5, 0.3), 0.0, 0.17, SLOT, chamfer=0.02)
    lib.dome(bm, G, 11.4, 11.3, 0.17, 0.7, 0.7, 0.06, mat=LAMP, segments=8, rings=2)
    prism(bm, rect(15.2, 10.0, 17.6, 12.8), 0.0, 0.26, DARK, chamfer=0.03)
    lib.dome(bm, G, 16.4, 11.4, 0.26, 0.8, 0.8, 0.07, mat=PIPE, segments=8, rings=2)
    prism(bm, rect(17.6, 10.0, 19.0, 13.4), 0.0, 0.28, LEG, chamfer=0.025)
    # Dark red vent block beside the stem (cols 19-21.4, rows 10.4-14.8), its grille glowing red.
    prism(bm, rect(19.0, 10.4, 21.4, 14.8, 0.3), 0.0, 0.34, REDVENT, chamfer=0.03)
    prism(bm, rect(19.5, 12.4, 20.9, 14.2), 0.2, 0.35, REDGLOW)
    # A cable beside the pipe, bending in to the eye housing.
    lib.sweep(bm, G, [(21.6, 13.5, 0.13, 0.45, 0.04), (21.5, 16.5, 0.13, 0.45, 0.04),
                      (22.0, 18.8, 0.16, 0.45, 0.04)], sides=6, mat=DARK)
    lib.mirror_from(bm, start, G.x(AXIS))

    # ---- centre parts ----
    # Hull deck (cols 14.6-31.4, rows 0-10.4).
    prism(bm, rect(14.6, 0.0, 31.4, 10.4, 0.8), 0.0, 0.40, HULL, chamfer=0.04)
    # Exhaust vent across the back: a housing with a glowing strip (row 0, hottest in the middle)
    # and a dark grille below it (rows 1.2-2.4).
    prism(bm, rect(18.9, 0.0, 27.1, 2.6), 0.0, 0.44, HULL, chamfer=0.03)
    lib.box(bm, G, 19.4, -0.1, 26.6, 1.15, 0.2, 0.46, mat=VENT, chamfer=0.02)
    lib.box(bm, G, 21.0, -0.15, 25.0, 0.9, 0.2, 0.47, mat=VENTHOT)
    lib.box(bm, G, 19.5, 1.15, 26.5, 2.3, 0.2, 0.455, mat=SLOT)
    # Screen frame (cols 18.9-27.1, rows 2.6-10.2) and the dark glass in it, raised above the deck,
    # with a light rim across its lower part.
    prism(bm, rect(18.9, 2.6, 27.1, 10.2, 0.9), 0.0, 0.48, FRAME, chamfer=0.04)
    prism(bm, rect(19.7, 3.2, 26.3, 9.5, 0.9), 0.3, 0.53, GLASS, chamfer=0.06)
    lib.sweep(bm, G, [(20.2, 7.8, 0.515, 0.0, 0.0), (20.6, 7.8, 0.515, 0.4, 0.03),
                      (25.4, 7.8, 0.515, 0.4, 0.03), (25.8, 7.8, 0.515, 0.0, 0.0)], sides=4, mat=RIM,
              smooth=False)
    # Dark block under the hull (cols 19-27, rows 10-14.6) and the pipe down to the eye (col 23),
    # with a clamp on it.
    prism(bm, rect(19.0, 10.0, 27.0, 14.6, 0.4), 0.0, 0.29, DARK, chamfer=0.03)
    lib.sweep(bm, G, [(AXIS, 13.0, 0.17, 0.9, 0.075), (AXIS, 19.6, 0.17, 0.9, 0.075)], sides=8, mat=PIPE)
    lib.sweep(bm, G, [(AXIS, 16.5, 0.17, 1.25, 0.1), (AXIS, 17.4, 0.17, 1.25, 0.1)], sides=8, mat=DARK)
    # Round housing (cols 19.3-26.7, rows 18.1-26.3) with a bezel ring and the red lens.
    lib.dome(bm, G, AXIS, 22.2, 0.0, 3.7, 4.1, 0.42, mat=HOUSING, segments=14, rings=4)
    lib.cylinder(bm, G, AXIS, 21.5, 0.2, 0.43, 2.5, 2.5, mat=PIPE, sides=14)
    lib.dome(bm, G, AXIS, 21.5, 0.40, 1.9, 1.9, 0.12, mat=EYE, segments=12, rings=3)
    lib.dome(bm, G, 22.7, 21.1, 0.46, 0.75, 0.75, 0.06, mat=EYEHOT, segments=8, rings=2)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.assembly_main(ROOT, NAME, build, PIECES, CX0, CY0, preview_tiles=2)


if __name__ == "__main__":
    main()
