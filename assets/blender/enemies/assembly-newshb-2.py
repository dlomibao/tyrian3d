"""Twin pod housings (newshb.shp 2, 4, 6, 8), the top of the CAMANIS boss, D65 hard surface.

Seen in level 3.10. Four 2x2 pieces side by side make one 96 x 28 px row (sprite.json
`assemblyLayout`), directly above assembly-newshb-115 (column 0 here = column 12 there): the
housings that take the two big blue pipes. Each pod, mirror images about column edge 47.5:
  * a grey housing lofted down the sprite (stations per row, chamfered sections) on a trapezoid
    footprint that follows the sprite's outline, its sides sloping to the ground; on its flat top
    three red vents with louvres between bright dividers, and a grille of chamfered slats over a dark
    floor; the front drops in a step to
  * a purple cowl arched over the pipe's end, with skirts either side of the pipe running down to
    newshb-115's purple corner plates (purple outside, dark grey on the inner side);
  * the big blue pipe (newshb-115's, same axis height and radius) coming out from under the cowl in
    a flanged collar and ending in a domed cap: the sprite's glossy "sphere" (its bright spot is
    sheen, art rule 2);
  * a grey block with a knob on the left pod's cowl, a knob in the purple on the right one.
Built whole in pixel-edge coordinates, cut into the four pieces by lib_b119.export_assembly (cull,
weighted normals, AO/roughness bake, outline shell from a sealed pre-cull copy; D50/D51/D65/D90/D118).

Run: blender --background --python assets/blender/enemies/assembly-newshb-2.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b119 as lib  # noqa: E402
from lib_b119 import PX, XE, YE  # noqa: E402

NAME = "assembly-newshb-2"
ROOT = common.repo_root(__file__)
PIECES = ["newshb-2", "newshb-4", "newshb-6", "newshb-8"]
AXIS = 47.5        # column edge the two pods mirror about
HT = 2.15          # housing top
ZC = 1.95          # cowl crown
PIPE_C = 31.0      # pipe axis column (newshb-115's column 43)
PIPE_R = 10.0      # px
PIPE_Z = 0.893     # newshb-115's pipe axis height
COWL_END = 19.8    # the cowl's front edge (row)

# The left pod's footprint: left / right edge of the sprite's inner mask per row (pixel edges).
LEFT = [(2.0, 22.2), (2.5, 22.2), (3.5, 21.3), (5.5, 20.3), (7.5, 19.3), (9.5, 18.3), (11.5, 17.3), (13.5, 16.3),
        (15.5, 15.3), (17.5, 14.3), (19.5, 13.3), (21.5, 12.3), (23.5, 11.0), (25.5, 10.2), (28.0, 10.2)]
RIGHT = [(2.0, 35.9), (2.5, 36.4), (4.5, 38.2), (6.5, 40.1), (8.0, 41.8), (28.0, 41.8)]

GREY, SIDE, DIV, VENT, LOUVRE, SLAT, FLOOR, PURPLE, LILAC, PIPE, COLLAR, KNOB, BLOCK = range(13)


def materials(sprite):
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshb2", **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.55, roughness=0.45),   # GREY housing top (6)
        pal(4, metallic=0.5, roughness=0.5),     # SIDE housing sides, inner skirts (4)
        pal(9, metallic=0.6, roughness=0.36),    # DIV bright vent dividers, grille slats (9)
        pal(113, metallic=0.4, roughness=0.6),   # VENT dark red vent wells (113)
        pal(114, metallic=1.0, roughness=0.9, emission_strength=0.45),  # LOUVRE vent louvres, a low ember (D126)
        pal(7, metallic=0.55, roughness=0.42),   # SLAT grille slats (7)
        pal(3, metallic=0.45, roughness=0.6),    # FLOOR grille floor, step (3)
        pal(85, metallic=0.4, roughness=0.48),   # PURPLE cowl and outer skirts (84-86)
        pal(89, metallic=0.45, roughness=0.42),  # LILAC rolled rib along the cowl (89)
        pal(54, metallic=0.3, roughness=0.42),  # PIPE the blue pipe and its domed cap (54), satin
        pal(5, metallic=0.6, roughness=0.4),     # COLLAR the pipe's flanged collar (5)
        pal(10, metallic=0.65, roughness=0.3),   # KNOB (10)
        pal(5, metallic=0.6, roughness=0.4),     # BLOCK grey block on the left cowl (5; same material as COLLAR)
    ]
    for i in (PIPE, KNOB):
        b = next(n for n in mats[i].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if "Specular IOR Level" in b.inputs:
            b.inputs["Specular IOR Level"].default_value = 0.6
    return mats


def edge(table, r):
    rs = [a for a, _ in table]
    cs = [b for _, b in table]
    return lib.pchip(rs, cs, r)


def loft(m, rows, section, mats):
    """A solid lofted down the sprite: section(r) -> [(col, z)] (same count every row, from the
    ground on the left over the top to the ground on the right); mats[k] for strip k; both ends capped."""
    rings = [[m.nv((XE(c), YE(r), z)) for c, z in section(r)] for r in rows]
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            m.face((a[k], b[k], b[j], a[j]), mats[k])
    m.face(rings[0], mats[-1])
    m.face(list(reversed(rings[-1])), mats[-1])


def housing_section(r):
    L, R = edge(LEFT, r), edge(RIGHT, r)
    c = 0.06 / PX  # chamfer in px
    return [(L, 0.0), (22.0 - 0.15, HT - 0.32), (22.0, HT - 0.06), (22.0 + c, HT), (36.0 - c, HT), (36.0, HT - 0.06),
            (36.0 + 0.15, HT - 0.32), (R, 0.0)]


def cowl_section(r):
    L, R = edge(LEFT, r), edge(RIGHT, r)
    pts = [(L, 0.0), (L + 0.6, 0.35)]
    for k in range(9):  # an arch over the pipe from column 21.4 to 36.4
        a = math.pi * k / 8
        pts.append((28.9 - 7.5 * math.cos(a), 1.45 + (ZC - 1.45) * math.sin(a) ** 0.7))
    pts += [(R - 0.6, 0.35), (R, 0.0)]
    return pts


def build_pod(m):
    """The left pod (mirrored for the right one)."""
    # Housing, rows 1.5-13.4.
    rows = [2.0, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.0, 9.5, 11.5, 13.4]
    lib_side = [SIDE, SIDE, GREY, GREY, GREY, SIDE, SIDE, SIDE]
    loft(m, rows, housing_section, lib_side + [SIDE])
    # Cowl, rows 13.2-COWL_END: purple on the outer side and arch, dark grey on the inner side.
    rows = [13.2, 14.5, 16.0, 17.5, 19.0, COWL_END]
    mats = [PURPLE] * 10 + [SIDE, SIDE, SIDE]
    loft(m, rows, cowl_section, mats + [PURPLE])
    # Step under the housing's front edge, a rolled lilac rib along the cowl's top.
    lib.chbox(m, 22.2, 13.0, 35.8, 13.9, HT - 0.42, HT - 0.06, FLOOR, ch=0.2, chz=0.02)
    rib = []
    for c in (21.6, 22.0, 35.6, 36.0):
        rad = 0.75 if 22.0 <= c <= 35.6 else 0.45
        rib.append([m.nv((XE(c), YE(14.4) + math.cos(2 * math.pi * (k + 0.5) / 10) * rad * PX,
                          ZC - 0.12 + math.sin(2 * math.pi * (k + 0.5) / 10) * rad * PX)) for k in range(10)])
    lib.rings_faces(m, rib, LILAC)
    # Skirts beside the pipe, falling to newshb-115's corner plates at the row's lower edge.
    def skirt_l(r):
        L = edge(LEFT, r)
        zt = lib.pchip([COWL_END - 0.4, 23.0, 28.0], [1.5, 1.05, 0.45], r)
        return [(L, 0.0), (L + 0.8, zt - 0.06), (L + 1.4, zt), (21.6, zt), (22.2, zt - 0.08), (22.2, 0.0)]

    def skirt_r(r):
        R = edge(RIGHT, r)
        zt = lib.pchip([COWL_END - 0.4, 23.0, 28.0], [1.5, 1.05, 0.45], r)
        return [(39.6, 0.0), (39.6, zt - 0.08), (40.2, zt), (R - 1.0, zt), (R - 0.4, zt - 0.06), (R, 0.0)]
    srows = [COWL_END - 0.4, 21.0, 22.5, 24.0, 25.5, 27.0, 27.98]
    loft(m, srows, skirt_l, [PURPLE] * 6)
    loft(m, srows, skirt_r, [SIDE] * 6)
    # Vents: three dark red wells with louvres between bright dividers (rows 1.5-5.6).
    lib.chbox(m, 22.4, 2.1, 35.6, 5.7, HT - 0.03, HT + 0.012, VENT, ch=0.2, chz=0.01)
    for c0 in (23.0, 27.0, 31.0):
        for k in range(3):
            r = 2.45 + 1.1 * k
            lib.chbox(m, c0 + 0.15, r, c0 + 2.85, r + 0.55, HT, HT + 0.03, LOUVRE, ch=0.1, chz=0.008)
    for c0 in (22.2, 26.2, 30.2, 34.2):
        lib.chbox(m, c0, 2.05, c0 + 0.8, 5.9, HT, HT + 0.05, DIV, ch=0.2, chz=0.015)
    # Grille: chamfered slats over a dark floor (rows 6-11), two cross seams.
    lib.chbox(m, 22.4, 6.2, 35.6, 11.6, HT - 0.03, HT + 0.008, FLOOR, ch=0.2, chz=0.006)
    for r0, mat in ((6.3, DIV), (8.3, SLAT), (10.3, SLAT)):
        lib.chbox(m, 22.6, r0, 35.4, r0 + 1.1, HT, HT + 0.04, mat, ch=0.3, chz=0.012)
    # The pipe: a flanged collar out of the cowl, a short straight run, a domed cap.
    z = PIPE_Z
    # the lower end (newshb-115's pipe takes it there; seen alone in the viewer): a hub, a recessed cap,
    # a bolt face and a flange lip, inside row 28
    R = PIPE_R
    end = [(27.75, 0.0, z), (27.75, 2.3, z), (27.6, 2.8, z), (27.15, 3.1, z), (27.15, R - 1.8, z), (27.7, R - 1.45, z),
           (27.7, R - 0.5, z), (27.94, R - 0.25, z), (27.94, R + 0.1, z), (27.75, R + 0.3, z), (26.8, R + 0.3, z),
           (26.4, R, z)]
    prof = end + [(24.5, PIPE_R, z)]
    # dome stations, one ring exactly at the cowl's front so no face straddles it (cull_hidden)
    a_cowl = math.asin((24.5 - COWL_END) / 6.4)
    angs = sorted({math.pi / 2 * k / 9 for k in range(1, 10)} | {a_cowl})
    angs = [a for a in angs if abs(a - a_cowl) > 0.05 or a == a_cowl]
    for a in angs:
        prof.append((24.5 - 6.4 * math.sin(a), PIPE_R * math.cos(a) if a < math.pi / 2 - 1e-6 else 0.0, z))
    mats = [COLLAR, COLLAR, FLOOR, COLLAR, COLLAR, COLLAR] + [PIPE] * (len(prof) - 7)
    lib.lathe_y(m, PIPE_C, prof, PIPE, sides=32, cap0=False, cap1=False, mats=mats)
    lib.lathe_y(m, PIPE_C, [(COWL_END - 0.6, PIPE_R + 0.2, z), (COWL_END - 0.2, PIPE_R + 0.75, z),
                            (COWL_END + 0.7, PIPE_R + 0.75, z), (COWL_END + 1.0, PIPE_R + 0.3, z),
                            (COWL_END + 1.0, PIPE_R - 0.4, z)], COLLAR, sides=28, cap0=False, cap1=False)
    for k in range(7):  # bolt heads round the collar's upper half
        a = math.pi * (0.12 + 0.76 * k / 6)
        cc, zz = PIPE_C + math.cos(a) * (PIPE_R + 0.45), z + math.sin(a) * (PIPE_R + 0.45) * PX
        lib.lathe_y(m, cc, [(COWL_END + 0.7, 0.32, zz), (COWL_END + 1.05, 0.32, zz), (COWL_END + 1.15, 0.0, zz)],
                    KNOB, sides=6, cap0=True, cap1=False)


def mirror_c(c):
    return 2 * AXIS - c


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    m = lib.M()
    n = m.mark()
    build_pod(m)
    m.mirror_since(n, AXIS)
    # Left pod: a grey block on the cowl with a knob; right pod: a knob in the purple.
    lib.chbox(m, 30.0, 14.6, 35.8, 18.6, ZC - 0.35, ZC + 0.08, BLOCK, ch=0.5, chz=0.03)
    lib.lathe_z(m, 31.6, 17.0, [(ZC + 0.07, 1.1), (ZC + 0.12, 1.1), (ZC + 0.16, 0.75), (ZC + 0.17, 0.0)], KNOB, sides=12)
    lib.lathe_z(m, mirror_c(30.6), 17.0, [(ZC - 0.1, 1.1), (ZC + 0.06, 1.1), (ZC + 0.1, 0.75), (ZC + 0.11, 0.0)],
                KNOB, sides=12)
    return m.to_object(NAME, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    lib.export_assembly(ROOT, obj, sprite, PIECES,
                        textured=[GREY, SIDE, DIV, VENT, SLAT, FLOOR, PURPLE, LILAC, PIPE, COLLAR, KNOB, BLOCK], tag="nshb2",
                        shell_groups=[(-99.0, XE(AXIS)), (XE(AXIS), 99.0)])  # one outline shell per pod


if __name__ == "__main__":
    main()
