"""Brown machine body (newshf.shp, the six middle pieces of assembly-newshf-270): a 3D version
of their sprites.

Seen in episodes 1-4 (levels 1.10, 1.29, 1.38, 2.2, 3.21, 4.16). Fourteen 2x2 ground enemies
make one big machine: two clawed side units with glowing red fingers (newshf-153, -155, -161,
-163, -191, -193, -199, -201, built elsewhere) on either side of this body, a 72 x 56 px block
of six pieces:

    newshf-165  newshf-234  newshf-167     grey band: four hooded lamps (165, 167) and a dark
    newshf-270  newshf-272  newshf-274     recess with two grey pistons (234); brown armour below

The brown armour has rounded outer panels with a dark slot, two raised panels each carrying a
long glowing pink tube that ends in a rounded pod, and between them a ridged plate over a dark
doorway with two arches. Pieces 165 and 167 have five frames that only light up the red lamps
under their hoods, so one model covers each.

The body is built once in assembly coordinates (left half, mirrored about pixel column 36, the
sprite's axis) and cut into the six pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshf-270.py [-- --preview out.png]
(the preview is the whole body; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b095 as lib  # noqa: E402
import common  # noqa: E402

NAME = "assembly-newshf-270"
ROOT = common.repo_root(__file__)
PIECES = ["newshf-165", "newshf-234", "newshf-167", "newshf-270", "newshf-272", "newshf-274"]
# Body pixel (0, 0) is the top-left corner of newshf-165 (screen 130 - 12, 39 - 14); the body is
# 72 x 56 px and its centre (screen 154, 53) is the Blender origin.
CX0, CY0 = 154, 53
G = lib.Grid(72, 56)
AX = G.xe(36.5)  # mirror axis: the centre of pixel column 36

BASE = 0.16  # top of the brown base slab
PANEL = 0.29  # top of the raised armour panels


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshf270", **kw)  # noqa: E731
    mats = [
        pal(65, metallic=0.1, roughness=0.8),  # 0 dark brown base, slots and recesses
        pal(69, metallic=0.15, roughness=0.6),  # 1 brown armour panels
        pal(72, metallic=0.2, roughness=0.45),  # 2 light rims, tube casing, arches
        pal(68, metallic=0.2, roughness=0.5),  # 3 darker brown (pods, jambs)
        pal(79, emission_strength=2.5),  # 4 glowing tube core
        pal(3, metallic=0.5, roughness=0.5),  # 5 dark grey band base
        pal(2, metallic=0.2, roughness=0.8),  # 6 near-black recesses
        pal(7, metallic=0.7, roughness=0.3),  # 7 light grey hoods
        pal(5, metallic=0.65, roughness=0.35),  # 8 grey walls, pistons
        pal(8, metallic=0.7, roughness=0.3),  # 9 bright grey edges, collars
        pal(116, emission_strength=3.0),  # 10 red lamps
        pal(70, metallic=0.15, roughness=0.5),  # 11 ridge on the centre plate
        pal(4, metallic=0.5, roughness=0.5),  # 12 dark grey pipes
    ]
    (DARK, ARMOUR, RIM, BROWN, GLOW, BAND, BLACK, HOOD, GREY, EDGE, LAMP, RIDGE, PIPE) = range(13)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----

    # Brown base slab under the armour, following the rounded outline down to the pods.
    lib.plate(bm, G, [(1, 13), (24, 13), (24, 17), (36.5, 17), (36.5, 48), (14, 48), (14, 41),
                      (12.5, 40.2), (10, 38.8), (8, 37.2), (6.4, 35.2), (6, 33), (5.2, 31), (3.6, 29),
                      (2.2, 27), (1, 25.5)], 0.0, BASE, mat=DARK)

    # Grey band (rows 1-13) under the two hooded lamps, and the dark recess in the middle.
    lib.box(bm, G, 1, 1, 24, 13, 0.0, 0.18, mat=BAND)
    lib.box(bm, G, 24, 0.3, 36.5, 17, 0.0, 0.10, mat=BLACK)

    # Two hooded lamps per side (columns 1-11 and 13-23).
    for x0 in (1, 13):
        x1 = x0 + 11
        lib.box(bm, G, x0, 1.2, x0 + 1, 10, 0.18, 0.36, mat=EDGE)  # lit left wall
        lib.box(bm, G, x1 - 1, 1.2, x1, 10, 0.18, 0.36, mat=GREY)  # right wall
        lib.half_sweep(bm, G, [(x0 + 0.1, 3.0, 0.18, 2.3, 0.2), (x1 - 1.1, 3.0, 0.18, 2.3, 0.2)],
                       sides=8, mat=HOOD)  # the rounded hood over the opening
        lib.box(bm, G, x0 + 1, 5, x1 - 1, 10, 0.18, 0.2, mat=BLACK)  # dark pit
        lib.ellipsoid(bm, G, x0 + 5, 7.6, 0.2, 3.0, 1.8, 0.075, mat=LAMP, segments=14, rings=6, z_min=0.2)
        lib.box(bm, G, x0, 10, x1, 11.3, 0.18, 0.33, mat=GREY)  # lip in front
        lib.box(bm, G, x0, 11.3, x1, 13, 0.18, 0.27, mat=PIPE)

    # Grey piston down the middle recess (columns 32-35) with a bright collar at its foot, and
    # two thin dark pipes beside it.
    lib.sweep(bm, G, [(33.5, -0.2, 0.12, 2.0, 0.2), (33.5, 14.6, 0.12, 2.0, 0.2)], sides=12, mat=GREY)
    lib.sweep(bm, G, [(33.5, 12.3, 0.12, 2.25, 0.22), (33.5, 14.2, 0.12, 2.25, 0.22)], sides=12, mat=EDGE)
    for c in (28, 30):
        lib.sweep(bm, G, [(c, 1.5, 0.1, 0.55, 0.05), (c, 15.8, 0.1, 0.55, 0.05)], sides=6, mat=PIPE)

    # Outer panel (columns 1-11): a strip outside the dark slot that rolls down toward the
    # rounded lower edge, and a taller strip inside it; a light rim along their top.
    lib.wedge_plate(bm, G, [(1.6, 13.3, PANEL - 0.01), (5, 13.3, PANEL - 0.01), (5, 17, PANEL - 0.02),
                            (5, 27, BASE + 0.02), (2.0, 25.4, BASE + 0.01), (1.6, 17, PANEL - 0.04)],
                    BASE - 0.01, mat=ARMOUR)
    lib.wedge_plate(bm, G, [(9, 13.3, PANEL), (11.7, 13.3, PANEL), (11.7, 39.6, PANEL - 0.07),
                            (10.6, 39.0, PANEL - 0.08), (9, 37.9, PANEL - 0.09)], BASE - 0.01, mat=ARMOUR)
    lib.box(bm, G, 1.6, 13.2, 11.7, 14.2, BASE, PANEL + 0.015, mat=RIM)

    # Tube panel (columns 13-23): two raised strips either side of the tube's channel, a cross
    # piece above it and a light rim.
    lib.plate(bm, G, [(13.2, 13.2), (17, 13.2), (17, 47.6), (14.2, 47.6), (14.2, 40.4), (13.2, 40.4)],
              BASE - 0.01, PANEL, mat=ARMOUR)
    lib.box(bm, G, 22, 13.2, 23.8, 47.6, BASE - 0.01, PANEL, mat=ARMOUR)
    lib.box(bm, G, 17, 13.2, 22, 16.8, BASE - 0.01, PANEL, mat=ARMOUR)
    lib.box(bm, G, 13.2, 13.2, 23.8, 14.2, BASE, PANEL + 0.015, mat=RIM)
    # The tube: a pink casing with a glowing core, rounded at both ends.
    lib.sweep(bm, G, [(19, 17.0, BASE + 0.02, 0.0, 0.0), (19, 17.8, BASE + 0.02, 1.4, 0.08),
                      (19, 19.0, BASE + 0.02, 1.8, 0.11), (19, 45.6, BASE + 0.02, 1.8, 0.11),
                      (19, 46.6, BASE + 0.02, 1.2, 0.07), (19, 47.0, BASE + 0.02, 0.0, 0.0)], sides=10, mat=RIM)
    lib.sweep(bm, G, [(19, 20.2, BASE + 0.05, 0.0, 0.0), (19, 22.0, BASE + 0.05, 0.75, 0.085),
                      (19, 45.0, BASE + 0.05, 0.8, 0.09), (19, 46.2, BASE + 0.05, 0.0, 0.0)], sides=8, mat=GLOW)
    # Rounded pod below the tube panel, its tip leaning in toward the middle.
    lib.sweep(bm, G, [(18.6, 45.0, 0.14, 4.6, 0.14), (18.7, 48.4, 0.13, 4.3, 0.13), (19.4, 50.8, 0.12, 3.5, 0.12),
                      (20.4, 52.4, 0.1, 2.4, 0.1), (21.2, 53.5, 0.08, 1.1, 0.07), (21.5, 54.0, 0.07, 0.0, 0.0)],
              sides=12, mat=BROWN)

    # Centre: a brown plate (rows 17-29) with a light ridge, then the doorway's jamb and arch.
    lib.box(bm, G, 25, 17.2, 36, 19, BASE - 0.01, BASE + 0.06, mat=BROWN)  # dark step at its top
    lib.box(bm, G, 25, 19, 36, 21, BASE - 0.01, PANEL, mat=RIDGE)
    lib.box(bm, G, 25, 21.7, 36, 29, BASE - 0.01, PANEL - 0.02, mat=ARMOUR)
    # Key-pattern ribs on it (the darker lines at rows 21-25).
    lib.box(bm, G, 29, 22.5, 30, 25.5, PANEL - 0.02, PANEL, mat=BROWN)
    lib.box(bm, G, 26, 25, 30, 26, PANEL - 0.02, PANEL, mat=BROWN)
    lib.box(bm, G, 33, 22.5, 34, 26, PANEL - 0.02, PANEL, mat=BROWN)
    lib.plate(bm, G, [(25, 29), (28, 29), (28, 44), (26, 44), (25, 43)], BASE - 0.01, PANEL - 0.02, mat=BROWN)
    arch = [(32, 43.6), (32, 34.4), (32.4, 33.5), (33.5, 33.0), (34.6, 33.5), (35, 34.4), (35, 43.6)]
    lib.half_sweep(bm, G, [(c, r, BASE, 0.8, 0.09) for c, r in arch], sides=6, mat=RIM)

    lib.mirror_since(bm, 0, AX)
    return lib.to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newshf-270's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshf-270")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        import tempfile
        tiles = [(name, cx + 36 - 12, cy + 28 - 14) for name, cx, cy in layout]
        ref = lib.composite_png(ROOT, tiles, 72, 84, 0, 14, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            lib.preview(ROOT, name, [pieces[name]], data, out=str(Path(out).with_name(f"{name}.png")))


if __name__ == "__main__":
    main()
