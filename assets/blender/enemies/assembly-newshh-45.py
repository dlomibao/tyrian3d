"""Blue cyclops beast in the rock (newshh.shp, assembly of newshh-5, -7, -43, -45): a 3D version of
its sprites.

Seen in episode 2 (level 2.4). Four 2x2 enemies make one 48x56 px block that fills its tiles: a
slab of grey rock with pale veins running down it (the same 24x28 tile of veins repeated), and a
dark blue beast crouched on it. The beast has a round head with one glowing red eye (newshh-5,
whose three frames only brighten the head and the eye, so one model covers them and its head
and torso colours step up each frame), a hunched torso
and a big rounded back to its right, a thick left foreleg ending in a hooked claw, a thin
right leg reaching down to the bottom right, and thin dark legs in the black shadow under it.

Built once in assembly coordinates (48x56 px, centre at the origin) and cut into the four pieces
with common.split_assembly. The rock is a plate at the bottom with raised veins; the shadow is a
dark plate just above the veins; the beast stands above both.

Run: blender --background --python assets/blender/enemies/assembly-newshh-45.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b057 as lib  # noqa: E402

NAME = "assembly-newshh-45"
ROOT = common.repo_root(__file__)
PIECES = ["newshh-5", "newshh-7", "newshh-43", "newshh-45"]
CX0, CY0 = 209, -3  # screen centre of the 48x56 block (newshh-5 top left ... newshh-45 bottom right)
G = lib.Grid(48, 56)

ROCK_Z0, ROCK_Z1 = -0.17, -0.12  # the rock plate
VEIN_H = 0.024

# Veins of one 24x28 rock tile: paths of (col, row, half width px). The tile repeats 2x2.
VEINS = [
    [(1.0, -0.5, 1.0), (1.0, 9.0, 1.1), (0.6, 11.0, 0.9), (1.0, 14.0, 0.9), (1.0, 27.5, 1.0)],
    [(5.5, -0.5, 1.0), (6.0, 4.0, 1.0), (7.6, 6.5, 1.1), (9.5, 8.0, 1.1), (10.2, 10.5, 1.0),
     (10.5, 16.0, 1.0), (10.5, 23.0, 1.0), (10.0, 25.0, 0.0)],
    [(6.0, 13.0, 0.0), (6.0, 14.5, 0.9), (6.4, 18.0, 1.0), (6.0, 22.0, 1.0), (5.5, 27.5, 1.0)],
    [(11.6, -0.5, 1.0), (10.6, 2.5, 0.9), (10.0, 4.5, 0.0)],
    [(15.5, -0.5, 1.0), (17.0, 3.0, 1.1), (19.5, 5.5, 1.1), (20.5, 8.0, 1.1), (20.5, 12.0, 1.0),
     (21.0, 16.0, 1.0), (20.6, 22.0, 1.0), (21.0, 25.0, 0.0)],
    [(15.0, 4.5, 0.0), (15.0, 6.0, 0.9), (15.0, 13.0, 1.0), (15.5, 20.0, 1.0), (15.5, 27.5, 1.0)],
    [(2.5, 25.5, 0.0), (2.5, 26.5, 0.8), (2.5, 27.5, 0.9)],
    [(2.5, -0.5, 0.9), (2.0, 1.5, 0.0)],
]


def rock(bm, ROCK, VEIN):
    lib.plate(bm, G, [(0, 0), (48, 0), (48, 56), (0, 56)], ROCK_Z0, ROCK_Z1, mat=ROCK)
    for tx, ty in ((0, 0), (24, 0), (0, 28), (24, 28)):
        for path in VEINS:
            pts = [(c + tx, r + ty, ROCK_Z1, w, VEIN_H if w else 0.0) for c, r, w in path]
            # Clamp the ends that run off the block, so nothing sticks out of the rock plate.
            pts = [(c, min(max(r, -0.45), 55.45), z, w, h) for c, r, z, w, h in pts]
            lib.sweep(bm, G, pts, sides=6, mat=VEIN, smooth=True, cap_start=pts[0][3] > 0,
                      cap_end=pts[-1][3] > 0)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshh45", **kw)  # noqa: E731
    mats = [
        pal(99, metallic=0.1, roughness=0.85),  # 0 rock
        pal(105, metallic=0.1, roughness=0.7),  # 1 pale veins
        pal(96, metallic=0.0, roughness=0.95),  # 2 shadow
        pal(53, metallic=0.35, roughness=0.4),  # 3 blue hide
        pal(55, metallic=0.35, roughness=0.35),  # 4 lighter blue (head, back)
        pal(51, metallic=0.3, roughness=0.5),  # 5 dark blue (legs, underside)
        pal(58, metallic=0.4, roughness=0.3),  # 6 pale blue highlights
        pal(48, metallic=0.2, roughness=0.6),  # 7 eye socket
        pal(116, emission_strength=3.0),  # 8 red eye
        pal(119, emission_strength=5.0),  # 9 eye core
    ]
    ROCK, VEIN, SHADOW, HIDE, LIGHT, DARK, PALE, SOCKET, EYE, CORE = range(10)
    # The head and torso brighten on newshh-5's frames 9 and 13 (the hide steps up three to five
    # palette shades each frame, and the eye goes from red to yellow-white): the same colours as
    # above, but with frames, so only newshh-5 animates (main() puts the static ones back on the
    # other pieces).
    anim = lambda i, f9, f13, tag, **kw: common.palette_material(  # noqa: E731
        sprite, i, f"nshh5{tag}", frames={9: f9, 13: f13}, **kw)
    mats += [
        anim(53, 56, 58, "hide", metallic=0.35, roughness=0.4),  # 10 torso
        anim(55, 58, 60, "head", metallic=0.35, roughness=0.35),  # 11 head
        anim(58, 61, 62, "pale", metallic=0.4, roughness=0.3),  # 12 head and chest highlights
        anim(48, 52, 55, "socket", metallic=0.2, roughness=0.6),  # 13 eye socket
        anim(116, 120, 123, "eye", emission_strength=3.0),  # 14 red eye, then orange, then yellow
        anim(119, 126, 127, "core", emission_strength=5.0),  # 15 eye core
    ]
    HIDE_A, LIGHT_A, PALE_A, SOCKET_A, EYE_A, CORE_A = range(10, 16)
    bm = bmesh.new()

    rock(bm, ROCK, VEIN)

    # Black shadow pooled under the beast (rows 38-43), above the veins.
    lib.plate(bm, G, [(14.5, 39), (19, 38), (37, 37.5), (40, 39), (39.5, 43), (34, 43.5), (30, 43),
                      (26, 43.5), (21, 43), (17, 42.5), (14.5, 41)], ROCK_Z1, ROCK_Z1 + VEIN_H + 0.012,
              mat=SHADOW)
    # Thin dark legs reaching down into the shadow (the black streaks under the body).
    zl = ROCK_Z1 + 0.04
    for path in ([(23.0, 39.0, 1.0), (23.0, 45.0, 0.9), (23.0, 50.3, 0.6), (23.0, 51.0, 0.0)],
                 [(27.5, 39.5, 1.1), (27.6, 45.0, 0.9), (28.0, 49.4, 0.6), (28.0, 50.0, 0.0)],
                 [(32.5, 39.5, 1.1), (32.8, 46.0, 1.0), (32.5, 50.3, 0.6), (32.5, 51.0, 0.0)],
                 [(37.5, 39.0, 1.1), (37.0, 43.0, 0.9), (36.6, 45.6, 0.6), (36.5, 46.2, 0.0)],
                 [(40.5, 39.5, 1.0), (42.5, 43.0, 1.0), (41.6, 46.5, 0.9), (40.5, 48.6, 0.9),
                  (38.0, 50.5, 0.8), (36.0, 52.6, 0.6), (35.0, 53.5, 0.0)],
                 [(19.5, 40.0, 1.0), (18.0, 45.0, 0.9), (17.5, 48.6, 0.8), (15.0, 49.2, 0.6), (14.2, 49.4, 0.0)]):
        lib.sweep(bm, G, [(c, r, zl, w, 0.025 if w else 0.0) for c, r, w in path], sides=6, mat=DARK)

    # Torso under the head, hunched down to row 40.
    lib.sweep(bm, G, [(18.5, 19.0, 0.0, 6.0, 0.17), (18.5, 23.0, 0.0, 5.6, 0.17), (18.6, 28.0, 0.0, 4.9, 0.15),
                      (19.0, 32.0, 0.0, 5.0, 0.14), (19.6, 35.5, -0.01, 5.4, 0.13), (20.5, 38.4, -0.02, 4.6, 0.1),
                      (21.6, 39.8, -0.03, 2.5, 0.06), (22.0, 40.3, -0.03, 0.0, 0.0)], sides=12, mat=HIDE_A)
    # Pale ridge down the front of the torso (the light streak at columns 15-17, rows 26-31).
    lib.sweep(bm, G, [(16.4, 25.0, 0.1, 0.0, 0.0), (16.0, 26.2, 0.1, 1.0, 0.05), (15.8, 30.5, 0.09, 1.0, 0.05),
                      (16.0, 31.8, 0.09, 0.0, 0.0)], sides=8, mat=PALE_A)

    # Big rounded back to the right (columns 22-41, rows 22-40), lit from the upper left.
    lib.ellipsoid(bm, G, 31.3, 31.2, 0.0, 10.0, 7.6, 0.24, mat=LIGHT, segments=20, rings=10,
                  angle=math.radians(-28), bottom=0.5)
    # Hump on its top edge (columns 30-36, rows 22-25) and the thin spine behind it (column 37).
    lib.ellipsoid(bm, G, 33.0, 23.6, 0.06, 3.6, 2.2, 0.09, mat=LIGHT, segments=12, rings=6)
    lib.sweep(bm, G, [(37.2, 22.4, 0.02, 0.0, 0.0), (37.2, 23.0, 0.02, 0.7, 0.04), (37.4, 25.8, 0.02, 0.7, 0.04),
                      (37.4, 26.5, 0.02, 0.0, 0.0)], sides=6, mat=HIDE)

    # Thin right leg from the back down to the bottom right (columns 38-45, rows 29-41).
    lib.sweep(bm, G, [(37.6, 28.5, 0.04, 1.8, 0.09), (39.4, 32.0, 0.03, 2.0, 0.09), (39.8, 35.0, 0.02, 1.8, 0.08),
                      (41.2, 36.8, 0.0, 1.5, 0.07), (42.6, 38.3, -0.02, 1.4, 0.06), (44.0, 40.0, -0.04, 1.3, 0.05),
                      (44.8, 41.0, -0.05, 0.0, 0.0)], sides=8, mat=LIGHT)

    # Thick left foreleg (columns 7-13, rows 26-40) ...
    lib.sweep(bm, G, [(9.6, 25.4, 0.04, 0.0, 0.0), (9.6, 26.2, 0.04, 2.6, 0.1), (9.8, 28.5, 0.04, 3.1, 0.13),
                      (10.0, 31.0, 0.03, 3.4, 0.14), (10.3, 34.0, 0.02, 3.8, 0.13), (9.9, 36.5, 0.0, 3.3, 0.11),
                      (8.6, 38.6, -0.02, 1.9, 0.07), (7.6, 39.9, -0.03, 0.0, 0.0)], sides=10, mat=HIDE)
    lib.ellipsoid(bm, G, 10.8, 31.0, 0.1, 1.6, 2.6, 0.06, mat=PALE, segments=10, rings=5)  # its lit front
    # ... joined to the torso by a shoulder (row 27) and ending in a hooked claw on the left.
    lib.sweep(bm, G, [(14.5, 26.5, 0.05, 1.8, 0.09), (11.0, 26.8, 0.06, 1.6, 0.09), (7.5, 27.2, 0.04, 1.3, 0.07),
                      (5.0, 27.8, 0.02, 1.1, 0.06), (3.6, 29.3, 0.0, 0.9, 0.05), (3.1, 31.2, -0.02, 0.8, 0.04),
                      (3.1, 32.8, -0.03, 0.5, 0.03), (3.2, 33.4, -0.03, 0.0, 0.0)], sides=8, mat=LIGHT)

    # Leg from under the torso down to the left (columns 13-17, rows 35-45).
    lib.sweep(bm, G, [(17.6, 35.0, 0.0, 1.8, 0.07), (15.6, 37.4, -0.02, 1.6, 0.06), (13.6, 39.4, -0.04, 1.2, 0.05),
                      (13.0, 42.0, -0.05, 0.8, 0.04), (13.0, 45.4, -0.06, 0.6, 0.03), (13.0, 46.0, -0.06, 0.0, 0.0)],
              sides=8, mat=LIGHT)

    # Round head (columns 12-28, rows 10-25), lit from the upper left, with one red eye.
    lib.ellipsoid(bm, G, 20.4, 17.6, 0.02, 8.4, 7.8, 0.28, mat=LIGHT_A, segments=20, rings=10, bottom=0.4)
    lib.ellipsoid(bm, G, 17.4, 13.2, 0.205, 2.6, 1.8, 0.05, mat=PALE_A, segments=12, rings=6,
                  angle=math.radians(30))
    lib.ellipsoid(bm, G, 22.2, 15.4, 0.25, 3.3, 2.9, 0.055, mat=SOCKET_A, segments=14, rings=7)
    lib.ellipsoid(bm, G, 22.2, 15.4, 0.268, 2.5, 2.1, 0.05, mat=EYE_A, segments=14, rings=7)
    lib.ellipsoid(bm, G, 22.5, 15.3, 0.3, 1.1, 1.0, 0.03, mat=CORE_A, segments=10, rings=5)

    return lib.to_object(NAME, bm, mats, coll)


ANIMATED = "newshh-5"  # the only piece with more than one frame
STATIC_OF = {10: 3, 11: 4, 12: 6, 13: 7, 14: 8, 15: 9}  # animated material slot -> its static twin


def static_materials(piece):
    """Put the static colours back on a piece that doesn't animate, so it's as it was."""
    mesh = piece.data
    for poly in mesh.polygons:
        poly.material_index = STATIC_OF.get(poly.material_index, poly.material_index)
    while len(mesh.materials) > 10:
        mesh.materials.pop()


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name, piece in pieces.items():
        if name != ANIMATED:
            static_materials(piece)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        lib.assembly_previews(ROOT, obj, pieces, layout, 4, out)
    if "--frames" in sys.argv:
        common.render_frame_previews([pieces[ANIMATED]], sys.argv[sys.argv.index("--frames") + 1],
                                     common.load_sprite(ROOT, ANIMATED), ROOT)


if __name__ == "__main__":
    main()
