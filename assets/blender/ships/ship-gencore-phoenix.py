"""Gencore Phoenix (player ship, tyrian.shp#8 sprite 157 and its banking frames 153-161).

A grey fighter: a long fuselage with a pointed nose, a dark cockpit slot behind the nose, a
polished metal hull, and two blade-like side pods (taller than they are wide, as the banking
frames show) joined to the fuselage by struts near the tail.

Run: blender --background --python assets/blender/ships/ship-gencore-phoenix.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import common  # noqa: E402
from lib_b001 import box, px, row  # noqa: E402

NAME = "ship-gencore-phoenix"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel


def tube(bm, sections, sides, paint, cap_start=True, cap_end=True):
    """A loft along the sprite's rows, each face coloured by paint(row, col, up).

    Sections are (row, centre column, half width px, top px, bottom px); a zero half width is a
    point. paint gets the face's sprite row and column (pixel centres) and how much it faces up
    (-1..1) and returns a material index, so the top view can follow the sprite's pixels."""
    k = 1 / math.cos(math.pi / sides)  # the polygon's flat sides reach the given half width
    rings = []
    for r, c, w, top, bot in sections:
        y, x, zc, h = row(r), px(c), (top + bot) / 2 * P, (top - bot) / 2 * P
        if w == 0:
            rings.append([bm.verts.new((x, y, zc))])
            continue
        rings.append([bm.verts.new((x + w * k * P * math.cos(a), y, zc + h * k * math.sin(a)))
                      for a in (2 * math.pi * (i + 0.5) / sides for i in range(sides))])

    def face(vs):
        f = bm.faces.new(vs)
        cx = sum(v.co.x for v in vs) / len(vs)
        cy = sum(v.co.y for v in vs) / len(vs)
        f.material_index = paint(14 - 0.5 - cy * 12, cx * 12 + 11.5, face.up)
        return f

    for (s0, r0), (s1, r1) in zip(zip(sections, rings), zip(sections[1:], rings[1:])):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for i in range(sides):
            j = (i + 1) % sides
            face.up = math.sin(2 * math.pi * (i + 1) / sides)
            if len(r0) == 1:
                face((r0[0], r1[j], r1[i]))
            elif len(r1) == 1:
                face((r0[i], r0[j], r1[0]))
            else:
                face((r0[i], r0[j], r1[j], r1[i]))
    face.up = 0.0
    if cap_start and len(rings[0]) > 1:
        face(list(reversed(rings[0])))
    if cap_end and len(rings[-1]) > 1:
        face(rings[-1])


def xtube(bm, x0, x1, r, top, bot, half_rows, sides, paint):
    """A tube across the ship (along X) from column x0 to x1, centred on row r."""
    zc, h, w = (top + bot) / 2 * P, (top - bot) / 2 * P, half_rows * P
    k = 1 / math.cos(math.pi / sides)
    rings = [[bm.verts.new((px(x), row(r) + w * k * math.cos(a), zc + h * k * math.sin(a)))
              for a in (2 * math.pi * (i + 0.5) / sides for i in range(sides))] for x in (x0, x1)]
    for i in range(sides):
        j = (i + 1) % sides
        a = 2 * math.pi * (i + 1) / sides
        f = bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
        f.material_index = paint(math.cos(a), math.sin(a))
    for ring in (rings[0], list(reversed(rings[1]))):
        bm.faces.new(ring).material_index = paint(0.0, 0.0)


def build(sprite):
    coll = common.reset_collection(NAME)
    used = {}
    mats = []

    def m(i, metallic=0.3, roughness=0.45):
        """Material slot for palette index i (one slot per index)."""
        if i not in used:
            used[i] = len(mats)
            mats.append(common.palette_material(sprite, i, NAME, metallic=metallic, roughness=roughness))
        return used[i]

    # Polished grey metal throughout: the sprite's near-white spots and streaks (the nose tip, the
    # bright patch mid-fuselage, the spine streak, the pods' inner edges) are specular highlights,
    # not bumps or paint, so the hull carries its mid-tone colour on a shiny metallic material and
    # the game's lights make the shine. The dark cockpit slot and the nozzle are glossy and dark.
    METAL = dict(metallic=0.8, roughness=0.28)
    SLOT, DARK, HULL, POD, STRUT = (m(2, 0.05, 0.12), m(4, **METAL), m(6, **METAL), m(6, **METAL),
                                    m(7, **METAL))
    bm = bmesh.new()

    # Lower hull: a low, wider flange under every part, out to the sprite's silhouette. The game
    # draws the dark outline, so it carries the hull colour. (row, column, half width, top, bottom).
    skirt = [(0.55, 11.5, 0, 0.3, -0.3), (1.0, 11.5, 0.75, 0.6, -0.5), (2.0, 11.5, 1.7, 0.8, -0.8),
             (3.0, 11.5, 1.75, 0.9, -0.9), (4.0, 11.5, 2.7, 1.0, -1.1), (5.0, 11.5, 2.75, 1.0, -1.2),
             (6.0, 11.5, 3.7, 1.1, -1.3), (8.4, 11.5, 3.7, 1.1, -1.4), (8.6, 11.5, 4.7, 1.2, -1.5),
             (16.4, 11.5, 4.7, 1.2, -1.5), (16.6, 11.5, 3.7, 1.1, -1.4), (23.0, 11.5, 3.7, 1.0, -1.3),
             (24.0, 11.5, 2.7, 0.9, -1.1), (25.0, 11.5, 1.7, 0.8, -0.9), (25.45, 11.5, 1.7, 0.5, -0.6)]
    tube(bm, skirt, 12, lambda r, c, up: HULL)

    # Fuselage: one smooth, tapered polished-metal body (8-10 px wide, about 6 px tall above the
    # plane), the nose tapering in width and height to the tip. The sprite shows only two dark seam
    # rows across it (rows 6 and 13): each is a shallow groove, about 0.5 px deep and 1 px wide.
    # The cockpit slot (row 9), the rear port (rows 18-19) and the tail are painted, not cut, and
    # the bright spot mid-fuselage is the metal's sheen, so the top stays smooth under it.
    hull = [(1.4, 0, 1.0, -0.2), (2.0, 0.85, 1.8, -0.6), (3.0, 1.2, 2.6, -0.9), (4.0, 1.85, 3.4, -1.2),
            (5.0, 2.25, 4.0, -1.5), (5.5, 2.6, 4.35, -1.6),
            (5.75, 2.4, 3.85, -1.6), (6.25, 2.5, 4.0, -1.7),  # seam groove, row 6
            (6.5, 2.8, 4.6, -1.8), (7.5, 3.05, 5.05, -1.9), (8.45, 3.4, 5.45, -2.0), (9.2, 3.7, 5.75, -2.0),
            (9.9, 3.85, 5.95, -2.0), (11.0, 3.85, 6.1, -2.0), (12.5, 3.85, 6.1, -2.0),
            (12.75, 3.6, 5.6, -2.0), (13.25, 3.6, 5.6, -2.0),  # seam groove, row 13
            (13.5, 3.85, 6.1, -2.0), (15.0, 3.85, 6.0, -2.0), (16.0, 3.75, 5.85, -2.0), (16.8, 3.2, 5.55, -2.0),
            (17.45, 2.9, 5.3, -2.0), (19.55, 2.85, 4.95, -1.9), (22.4, 2.85, 4.4, -1.8),
            (23.0, 1.8, 2.8, -1.5), (23.3, 0, 1.5, -1.0)]

    def hull_paint(r, c, up):
        x = abs(c - 11.5)
        if 5.55 < r < 6.45:
            return DARK if x < 2.2 else HULL  # dark band across the nose
        if 8.45 < r < 9.55:
            return SLOT if x < 2.2 else HULL  # cockpit slot
        if 12.45 < r < 13.55:
            return DARK  # band under the cockpit
        if 17.45 < r < 19.55:
            return SLOT if x < 1.0 and up > 0.5 else HULL  # rear port between two lips
        if r > 19.55:
            return DARK  # the darker tail end
        return HULL

    tube(bm, [(r, 11.5, w, t, b) for r, w, t, b in hull], 14, hull_paint)

    # Tail engine (rows 23-25, columns 10-13): a blunt, chamfered block, darker than the hull, with
    # a nozzle cut into its end.
    block = [(22.3, 11.5, 1.95, 3.3, -1.5), (24.6, 11.5, 1.95, 3.3, -1.5), (25.4, 11.5, 1.95, 2.3, -1.2),
             (25.4, 11.5, 1.0, 1.4, -0.4), (24.7, 11.5, 0.8, 1.2, -0.2), (24.7, 11.5, 0, 0.5, 0.5)]

    def block_paint(r, c, up):
        if r > 24.55:
            return SLOT if abs(c - 11.5) < 1.1 else DARK  # nozzle in the dark back face
        return DARK

    tube(bm, block, 8, block_paint, cap_end=False)

    # Side pods: round nacelles, inner edge straight (column 5), outer edge flaring out to
    # column 1 at rows 14-22, on a lower, wider flange out to the silhouette. The bright line along
    # each pod's inner edge in the sprite is the metal's sheen.
    pod_edge = [(8.55, 4.6, 0, 0.4, -0.5), (9.0, 4.5, 0.75, 0.8, -0.9), (10.0, 4.0, 1.25, 1.0, -1.1),
                (11.0, 4.0, 1.25, 1.0, -1.2), (12.0, 3.5, 1.75, 1.1, -1.3), (13.0, 3.5, 1.75, 1.1, -1.3),
                (14.0, 3.0, 2.25, 1.1, -1.4), (22.0, 3.0, 2.25, 1.1, -1.4), (23.0, 4.0, 1.25, 1.0, -1.2),
                (24.0, 3.5, 0.75, 0.8, -0.9), (24.45, 3.5, 0, 0.4, -0.5)]
    pod = [(9.6, 4.2, 0, 1.4, 0.2), (10.0, 4.0, 0.45, 2.0, -0.6), (11.0, 3.55, 0.95, 2.9, -1.3),
           (13.0, 3.5, 0.95, 3.4, -1.6), (14.0, 3.0, 1.45, 3.7, -1.8), (21.0, 3.0, 1.45, 3.7, -1.8),
           (22.0, 3.55, 0.95, 3.2, -1.6), (23.0, 4.0, 0.45, 2.3, -1.2), (23.55, 4.0, 0, 1.4, -0.4)]
    for flip in (False, True):
        mir = (lambda secs: [(r, 23 - c, w, t, b) for r, c, w, t, b in secs]) if flip else (lambda secs: secs)
        tube(bm, mir(pod_edge), 10, lambda r, c, up: POD)
        tube(bm, mir(pod), 10, lambda r, c, up: POD)

    # Struts (rows 20-21, columns 5-8): round bars from the pods into the hull, on a low bar out to
    # the silhouette (rows 19 and 22).
    for a, b in ((4.6, 9.0), (23 - 9.0, 23 - 4.6)):
        box(bm, px(a) - 0.5 * P, px(b) + 0.5 * P, row(22.25), row(18.75), -1.0 * P, 0.6 * P, mat_index=STRUT)
        xtube(bm, a, b, 20.5, 2.6, -0.4, 0.95, 8, lambda dy, up: STRUT)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


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
