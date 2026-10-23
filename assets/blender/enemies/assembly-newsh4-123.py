"""Bronze winged boss body (newsh4.shp 119, 121, 123): a 3D version of its three-piece sprite.

Seen in one level of episode 4. Three 2x2 enemies side by side make the lower half of a boss
(the head, horns and shoulder pods above it are assembly-newsh4-81): a bronze torso with a grey
ribbed chest and a red light, swept bronze wings with red pods at their tips, thin arcs curving
from the wing tips round to two grey engine pods under the wings, and a grey nozzle at the tail.
Each piece has a single frame.

The body is built once in the frame shared with assembly-newsh4-81 (lib_b065) and cut into the
three pieces with common.split_assembly. The sprite is not quite symmetric (its right side is
drawn up to 2 px further out), so the wings are mirrored about column edge 30.75 and the parts
that differ more are placed per side.

Run: blender --background --python assets/blender/enemies/assembly-newsh4-123.py [-- --preview out.png]
(the preview is the whole body; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b065 as lib  # noqa: E402

NAME = "assembly-newsh4-123"
ROOT = common.repo_root(__file__)
PIECES = ["newsh4-119", "newsh4-121", "newsh4-123"]
WING_AXIS = 30.75


def pod(bm, c0, c1, row, nozzle_c, GREY, DKBR, DARK):
    """A grey engine pod lying across the sprite (columns c0-c1 edges, centred on `row`) with a
    nozzle pointing down at column edge `nozzle_c` and a dark bronze band along its top."""
    d = 1 if c1 > c0 else -1
    lib.sweep(bm, [(c0 - 0.2 * d, row, 0.0, 0.0, 0.0), (c0, row, 0.0, 2.2, 0.08),
                   (c0 + 0.6 * d, row, 0.0, 3.0, 0.12), (c1 - 0.8 * d, row, 0.0, 3.0, 0.12),
                   (c1, row, 0.0, 2.3, 0.09), (c1 + 0.2 * d, row, 0.0, 0.0, 0.0)], sides=12, mat=GREY)
    lo, hi = sorted((c0 + 4.5 * d, c1 - 1.5 * d))
    lib.box(bm, lo, row - 2.3, hi, row - 1.3, 0.02, 0.105, mat=DKBR)
    lib.loft_y(bm, nozzle_c, [(row + 1.0, 2.2, 0.09, -0.01), (row + 4.0, 2.0, 0.08, -0.01),
                              (row + 5.6, 1.6, 0.06, -0.01), (row + 5.9, 0.0, 0.0, -0.01)],
               sides=10, mat=GREY)
    lib.ellipsoid(bm, nozzle_c, row + 5.5, -0.01, 1.2, 0.5, 0.045, mat=DARK, segments=10, rings=5)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh4b"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(23, metallic=0.45, roughness=0.45),  # 0 bronze wings
        pal(24, metallic=0.45, roughness=0.4),  # 1 bronze torso
        pal(25, metallic=0.5, roughness=0.35),  # 2 light bronze ridges and arcs
        pal(27, metallic=0.5, roughness=0.3),  # 3 pale bulge
        pal(163, metallic=0.3, roughness=0.55),  # 4 dark bronze bands
        pal(6, metallic=0.65, roughness=0.35),  # 5 grey pods and chest
        pal(9, metallic=0.7, roughness=0.3),  # 6 light grey ribs
        pal(3, metallic=0.4, roughness=0.6),  # 7 dark joints and nozzles
        pal(70, metallic=0.35, roughness=0.4),  # 8 red armour and wing-tip pods
        pal(74, emission_strength=3.0),  # 9 red chest light
        pal(77, emission_strength=5.0),  # 10 chest light core
        pal(10, metallic=0.75, roughness=0.25),  # 11 bright rail
        pal(20, metallic=0.35, roughness=0.5),  # 12 brown strut
    ]
    WING, HULL, RIDGE, PALE, DKBR, GREY, RIB, DARK, RED, LIGHT, HOT, RAIL, STRUT = range(13)
    bm = bmesh.new()

    # ---- left wing, mirrored for the right ----
    start = len(bm.verts)

    def taper(top):
        def z(c, r):
            t = max(0.0, min(1.0, (c - 4) / 19))
            return 0.015 + 0.06 * t if top else -0.03 - 0.03 * t
        return z

    wing = [(15, 25.8), (18.5, 25.8), (18.5, 31.8), (23.8, 31.8), (23.8, 34.2), (17, 34.4), (14.5, 36),
            (11, 37.6), (8.5, 38.8), (6.5, 39.7), (4.3, 39.6), (4.2, 33.4), (6.5, 32.4), (9, 31.8),
            (11, 29.8), (13, 27.8)]
    lib.prism(bm, wing, taper(False), taper(True), mat=WING)
    # Light spar down the wing root and along its middle.
    lib.sweep(bm, [(16.5, 26.4, 0.075, 0.0, 0.0), (16.5, 26.8, 0.075, 0.7, 0.025), (16.5, 33.0, 0.07, 0.75, 0.025),
                   (17.6, 33.5, 0.07, 0.7, 0.025), (22.8, 33.5, 0.075, 0.7, 0.025), (23.3, 33.5, 0.075, 0.0, 0.0)],
              sides=6, mat=RIDGE)
    # Red pod at the wing tip with a grey sleeve, and a pale point under it.
    lib.loft_y(bm, 5.4, [(32.4, 0.0, 0.0, 0.0), (32.8, 1.0, 0.06, 0.0), (33.6, 1.5, 0.09, 0.0),
                         (37.6, 1.5, 0.09, 0.0), (38.4, 1.0, 0.06, 0.0)], sides=10, mat=RED)
    lib.loft_y(bm, 5.2, [(38.3, 1.0, 0.06, 0.0), (39.6, 0.9, 0.045, 0.0), (40.3, 0.0, 0.0, 0.0)], sides=8, mat=PALE)
    lib.box(bm, 6.6, 32.8, 9.2, 36.2, -0.04, 0.07, mat=GREY)
    # Thin arc from the wing tip round under the wing to the engine pod.
    lib.sweep(bm, [(4.9, 39.4, 0.0, 0.6, 0.03), (4.6, 41.0, 0.0, 0.6, 0.03), (4.9, 42.6, 0.0, 0.6, 0.03),
                   (5.7, 44.0, 0.0, 0.6, 0.03), (6.8, 45.3, 0.0, 0.6, 0.03), (8.3, 46.4, 0.0, 0.6, 0.03),
                   (10.2, 46.7, 0.0, 0.6, 0.03), (12.0, 46.4, 0.0, 0.6, 0.03)], sides=6, mat=RIDGE)
    # Dark joint where the wing meets the shoulder.
    lib.loft_y(bm, 19.8, [(24.2, 0.0, 0.0, 0.0), (24.7, 1.6, 0.08, 0.0), (30.6, 1.6, 0.08, 0.0),
                          (31.2, 0.0, 0.0, 0.0)], sides=10, mat=GREY)
    lib.mirror_since(bm, start, WING_AXIS)

    # ---- per-side parts ----
    # Red shoulder armour: two plates on the left, one on the right.
    lib.prism(bm, [(19.8, 28.8), (23.0, 28.6), (23.0, 31.2), (20.2, 31.2)], 0.0, 0.13, mat=RED)
    lib.prism(bm, [(23.8, 28.6), (27.2, 28.6), (27.2, 31.2), (23.8, 31.2)], 0.0, 0.16, mat=RED)
    lib.prism(bm, [(36.8, 27.8), (41.2, 28.6), (41.0, 31.2), (37.0, 31.2)], 0.0, 0.15, mat=RED)
    # Struts from the shoulders down to the pods: grey on the left, a bronze rod on the right.
    lib.sweep(bm, [(21.8, 33.6, 0.0, 0.0, 0.0), (21.8, 34.0, 0.0, 1.7, 0.1), (21.8, 39.6, 0.0, 1.7, 0.1),
                   (21.8, 40.2, 0.0, 0.0, 0.0)], sides=10, mat=RIB)
    lib.sweep(bm, [(40.4, 32.6, 0.02, 0.0, 0.0), (40.4, 33.0, 0.02, 0.8, 0.06), (40.4, 39.0, 0.02, 0.8, 0.06),
                   (40.4, 39.5, 0.02, 0.0, 0.0)], sides=8, mat=HULL)
    # Engine pods under the wings.
    pod(bm, 23.6, 11.2, 43.0, 13.2, GREY, DKBR, DARK)
    pod(bm, 38.8, 49.6, 43.0, 47.9, GREY, DKBR, DARK)

    # ---- torso, down the middle ----
    lib.loft_y(bm, 30.5, [(24.0, 0.0, 0.0, 0.0), (24.3, 4.5, 0.1, 0.0), (26.0, 5.8, 0.13, 0.0),
                          (29.0, 6.6, 0.16, 0.0), (33.0, 7.0, 0.17, 0.0), (40.0, 7.0, 0.17, 0.0),
                          (43.5, 6.6, 0.17, 0.0), (45.2, 5.2, 0.14, 0.0), (47.0, 3.4, 0.09, 0.0),
                          (48.2, 0.0, 0.0, 0.0)], sides=14, mat=HULL)
    # Grey chest top (rows 28-31) and the glowing red light under it.
    lib.prism(bm, [(27.4, 27.2), (33.4, 27.2), (33.4, 31.8), (27.4, 31.8)], 0.08, 0.2, mat=GREY)
    lib.ellipsoid(bm, 29.9, 33.1, 0.18, 2.0, 1.4, 0.05, mat=LIGHT, segments=12, rings=6)
    lib.ellipsoid(bm, 29.7, 33.3, 0.2, 0.9, 0.6, 0.04, mat=HOT, segments=10, rings=5)
    # Ribbed grey chest (rows 34-39): a plate with two raised light ribs.
    lib.box(bm, 26.9, 33.9, 33.6, 40.4, 0.1, 0.19, mat=GREY)
    for r0, r1 in ((34.2, 35.9), (37.0, 37.9)):
        lib.box(bm, 28.2, r0, 32.0, r1, 0.12, 0.215, mat=RIB)
    # Bright rail down the left of the chest and a dark strut down its right.
    lib.loft_y(bm, 26.5, [(32.6, 0.0, 0.0, 0.16), (33.0, 0.6, 0.04, 0.16), (39.5, 0.6, 0.04, 0.16),
                          (39.9, 0.0, 0.0, 0.16)], sides=6, mat=RAIL)
    lib.loft_y(bm, 36.0, [(31.0, 0.0, 0.0, 0.12), (31.5, 1.4, 0.05, 0.12), (38.5, 1.4, 0.05, 0.12),
                          (39.0, 0.0, 0.0, 0.12)], sides=8, mat=STRUT)
    # Dark band across the belly and the pale bulge below it.
    lib.box(bm, 24.6, 40.6, 36.4, 41.8, 0.05, 0.178, mat=DKBR)
    lib.ellipsoid(bm, 29.8, 43.4, 0.12, 2.8, 1.8, 0.07, mat=PALE, segments=12, rings=6)
    # Grey tail nozzle.
    lib.loft_y(bm, 29.6, [(44.6, 3.8, 0.1, -0.02), (47.0, 3.4, 0.1, -0.02), (48.4, 2.4, 0.07, -0.02),
                          (48.8, 0.0, 0.0, -0.02)], sides=10, mat=GREY)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    lib.export_assembly(ROOT, obj, PIECES, sys.argv)


if __name__ == "__main__":
    main()
