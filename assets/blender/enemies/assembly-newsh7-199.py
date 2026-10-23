"""Grey sphere on a purple lander base (newsh7.shp, assembly of newsh7-161, -163, -199 and -201):
a 3D version of its sprites.

Seen in episode 3 (level section 10). Four pieces in a 2x2 block make a 48x56 px structure on
the ice (the level puts two of them side by side; sprite.json `assemblyLayout`): newsh7-161 and
newsh7-163 hold a big panelled grey sphere, and newsh7-199 and newsh7-201 the purple cradle
under it: an arm curving up each side of the sphere, two ribbed blocks under it split by a dark
slot, and two legs pointing down the screen, each with a toe turned in. Each piece has one frame.

The structure is built once in assembly coordinates (the 48x56 px block, origin at its centre)
and cut into the four pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh7-199.py [-- --preview out.png]
(the preview is the whole structure; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b108 as lib  # noqa: E402
from lib_b108 import common  # noqa: E402

NAME = "assembly-newsh7-199"
ROOT = common.repo_root(__file__)
PIECES = ["newsh7-161", "newsh7-163", "newsh7-199", "newsh7-201"]
CX0, CY0 = 236, -4  # screen centre of the left structure's 48x56 block
P = 1 / 12
BASE = 0.04  # top of the ice

# The sphere: centre column / row, radii in px, centre height and vertical radius in units.
SC, SR, SRX, SRY, SZ, SRZ = 17.6, 14.2, 14.3, 12.4, 0.12, 0.82


def X(c):
    """Assembly column (centre; fractions allowed) to Blender X."""
    return (c + 0.5 - 24) / 12


def Y(r):
    """Assembly row (centre) to Blender Y: sprite up is +Y."""
    return (28 - (r + 0.5)) / 12


def on_sphere(c, r, lift=0.004):
    """A point on the sphere's surface above pixel (c, r)."""
    dx, dy = (c - SC) / SRX, (r - SR) / SRY
    k = max(0.0, 1 - dx * dx - dy * dy)
    return (X(c), Y(r), SZ + SRZ * math.sqrt(k) + lift)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "n7_199"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(58, metallic=0.1, roughness=0.35),  # 0 ice
        pal(11, metallic=0.6, roughness=0.28),  # 1 grey sphere
        pal(7, metallic=0.6, roughness=0.4),  # 2 panel seams
        pal(86, metallic=0.35, roughness=0.45),  # 3 purple cradle
        pal(88, metallic=0.35, roughness=0.4),  # 4 lighter purple
        pal(91, metallic=0.4, roughness=0.3),  # 5 bright purple ribs
        pal(82, metallic=0.3, roughness=0.6),  # 6 dark purple grooves
    ]
    ICE, SPHERE, SEAM, PURPLE, LIGHT, RIB, DARK = range(7)
    bm = bmesh.new()

    # Ice under the whole block (edges kept just inside the cut lines).
    e = 0.005
    lib.plate(bm, [(X(-0.5) + e, Y(55.5) + e), (X(47.5) - e, Y(55.5) + e), (X(47.5) - e, Y(-0.5) - e),
                   (X(-0.5) + e, Y(-0.5) - e)], 0.0, BASE, mat=ICE)

    # ---- the purple cradle ----

    # The base of the cradle, each side one piece: an arm up beside the sphere (columns 2-5 from
    # row 15) widening into a block under it (columns 5-16 and 20-30, rows 24-35). The middle of
    # it is hidden under the sphere.
    for outline in ([(1.6, 14.8), (5.5, 14.8), (10.0, 23.6), (16.6, 23.6), (16.6, 35.6), (5.6, 35.6),
                     (4.6, 34.6), (4.6, 28.4), (1.6, 27.6)],
                    [(35.4, 15.8), (31.5, 15.8), (27.0, 23.6), (19.6, 23.6), (19.6, 35.6), (30.6, 35.6),
                     (30.6, 30.0), (35.4, 27.6)]):
        lib.plate(bm, [(X(c - 0.5), Y(r - 0.5)) for c, r in outline], BASE - 0.01, BASE + 0.26, mat=PURPLE)
    # Bevelled tops on the blocks.
    for c0, c1 in ((5.0, 16.2), (20.0, 30.2)):
        bottom = [(X(c0), Y(35.0)), (X(c1), Y(35.0)), (X(c1), Y(25.6)), (X(c0), Y(25.6))]
        upper = [(X(c0 + 0.8), Y(34.4)), (X(c1 - 0.8), Y(34.4)), (X(c1 - 0.8), Y(26.2)), (X(c0 + 0.8), Y(26.2))]
        lib.frustum(bm, bottom, upper, BASE + 0.25, BASE + 0.32, mat=LIGHT)
    lib.plate(bm, [(X(16.4), Y(35.4)), (X(19.8), Y(35.4)), (X(19.8), Y(24)), (X(16.4), Y(24))],
              BASE - 0.01, BASE + 0.1, mat=DARK)
    # Ribs along the blocks (the light columns 6, 12, 23 and 28).
    for c in (6.0, 12.3, 23.0, 28.0):
        lib.tube(bm, (X(c), Y(25.8), BASE + 0.32), (X(c), Y(34.6), BASE + 0.32), 0.7 * P, sides=6,
                 mat_index=RIB if c in (6.0, 23.0) else PURPLE)
    # A dark groove across them (row 34).
    for c0, c1 in ((5.6, 15.8), (20.4, 29.8)):
        lib.tube(bm, (X(c0), Y(33.6), BASE + 0.31), (X(c1), Y(33.6), BASE + 0.31), 0.55 * P, sides=4, mat_index=DARK)

    # Rounded arm crests up each side of the sphere.
    left = [(3.0, 14.8), (3.0, 18.0), (3.4, 22.0), (4.6, 25.4), (6.0, 27.6)]
    right = [(34.0, 15.8), (33.9, 19.0), (33.2, 22.5), (31.8, 25.6), (30.0, 27.6)]
    for path, lit in ((left, RIB), (right, LIGHT)):
        lib.polyline_tube(bm, [(X(c), Y(r), BASE + 0.26) for c, r in path], 1.6 * P, sides=8,
                          mat_index=lit, squash=0.6)

    # Legs pointing down the screen (columns 9-13 and 23-27, rows 35-47), toes turned in at row 41.
    for c, toe, rib in ((11.0, 16.4, 11.2), (25.0, 20.0, 23.6)):
        leg = [(34.5, 3.1, 0.26), (37.0, 3.0, 0.24), (41.0, 3.0, 0.22), (44.0, 2.8, 0.17), (46.0, 2.0, 0.1),
               (47.3, 0.0, 0.0)]
        lib.arch_loft(bm, [(X(c), Y(r), w * P, h, BASE) if w else (X(c), Y(r), 0, 0, BASE + 0.03)
                           for r, w, h in leg], sides=8, mat=PURPLE)
        lib.polyline_tube(bm, [(X(c), Y(41.6), BASE + 0.08), (X(toe), Y(41.8), BASE + 0.06)],
                          [1.6 * P, 1.0 * P], sides=6, mat_index=PURPLE)
        lib.polyline_tube(bm, [(X(rib), Y(35.5), BASE + 0.22), (X(rib), Y(41.0), BASE + 0.19),
                               (X(rib), Y(45.2), BASE + 0.13)], 0.6 * P, sides=4, mat_index=RIB, squash=0.6)

    # ---- the sphere ----
    lib.ellipsoid(bm, X(SC), Y(SR), SZ, SRX * P, SRY * P, SRZ, mat=SPHERE, segments=24, rings=12, z_min=BASE)
    # Panel seams over its surface.
    def seam(points, n=6):
        pts = []
        for (c0, r0), (c1, r1) in zip(points, points[1:]):
            for i in range(n):
                t = i / n
                pts.append(on_sphere(c0 + (c1 - c0) * t, r0 + (r1 - r0) * t))
        pts.append(on_sphere(*points[-1]))
        lib.polyline_tube(bm, pts, 0.5 * P, sides=4, mat_index=SEAM, caps=False, squash=0.5)

    seam([(21.0, 3.2), (21.4, 9.0), (21.0, 15.0)])  # down from the top, right of centre
    seam([(21.0, 15.0), (25.0, 17.5), (28.5, 21.0)])  # off to the lower right
    seam([(8.4, 13.0), (8.6, 17.0), (10.0, 20.0)])  # left
    seam([(10.0, 20.0), (15.0, 19.6), (19.5, 19.8)])  # across the lower half
    seam([(11.0, 6.6), (16.0, 6.4), (21.0, 6.8)])  # across the top

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES[0], PIECES[1:])
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["cx"] in (CX0 - 12, CX0 + 12)]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56)
        common.render_preview([obj], str(out), ref, size=4)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
