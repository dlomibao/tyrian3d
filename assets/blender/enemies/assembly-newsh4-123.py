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


def plate(bm, outline, z0, z1, mat, ch_px=0.7, ch_z=0.04):
    """A hard plate (lib.prism) whose top edge is chamfered: the top face is inset by `ch_px`
    sprite px and raised `ch_z` units, so the plate reads crisp with a lit bevel."""
    lower = (lambda c, r: z1(c, r) - ch_z) if callable(z1) else z1 - ch_z
    n = len(bm.faces)
    lib.prism(bm, outline, z0, lower, mat=mat)
    bm.faces.ensure_lookup_table()
    top = bm.faces[n]
    res = bmesh.ops.inset_region(bm, faces=[top], thickness=ch_px * lib.PX, depth=ch_z,
                                 use_even_offset=True)
    for f in res["faces"] + [top]:
        f.material_index = mat
        f.smooth = False


def pod(bm, c0, c1, row, nozzle_c, GREY, DKBR, DARK):
    """A grey engine pod lying across the sprite (columns c0-c1 edges, centred on `row`) with a
    nozzle pointing down at column edge `nozzle_c` and a dark bronze band along its top. The pod
    is a faceted (octagonal) drum about as tall as it is wide, with flanged end plates."""
    d = 1 if c1 > c0 else -1
    z = 0.1
    lib.sweep(bm, [(c0 - 0.2 * d, row, z, 0.0, 0.0), (c0, row, z, 2.6, 0.22),
                   (c0 + 0.9 * d, row, z, 3.1, 0.26), (c0 + 1.3 * d, row, z, 2.8, 0.235),
                   (c1 - 1.3 * d, row, z, 2.8, 0.235), (c1 - 0.9 * d, row, z, 3.1, 0.26),
                   (c1, row, z, 2.6, 0.22), (c1 + 0.2 * d, row, z, 0.0, 0.0)],
              sides=8, mat=GREY, smooth=False)
    lo, hi = sorted((c0 + 4.5 * d, c1 - 1.5 * d))
    lib.box(bm, lo, row - 2.0, hi, row - 0.9, z + 0.12, z + 0.25, mat=DKBR)
    lib.loft_y(bm, nozzle_c, [(row + 1.0, 2.2, 0.17, 0.02), (row + 4.0, 2.0, 0.16, 0.02),
                              (row + 5.6, 1.6, 0.12, 0.02), (row + 5.9, 0.0, 0.0, 0.02)],
               sides=10, mat=GREY)
    lib.ellipsoid(bm, nozzle_c, row + 5.5, 0.02, 1.2, 0.5, 0.09, mat=DARK, segments=10, rings=5)


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

    def wing_z(top):
        def z(c, r):
            t = max(0.0, min(1.0, (c - 4) / 19))  # 0 at the tip, 1 at the root
            return 0.1 + 0.12 * t if top else -0.04 - 0.04 * t
        return z

    wing = [(15, 25.8), (18.5, 25.8), (18.5, 31.8), (23.8, 31.8), (23.8, 34.2), (17, 34.4), (14.5, 36),
            (11, 37.6), (8.5, 38.8), (6.5, 39.7), (4.3, 39.6), (4.2, 33.4), (6.5, 32.4), (9, 31.8),
            (11, 29.8), (13, 27.8)]
    plate(bm, wing, wing_z(False), wing_z(True), WING, ch_px=1.0, ch_z=0.05)
    # Light spar down the wing root and along its middle.
    lib.sweep(bm, [(16.5, 26.4, 0.2, 0.0, 0.0), (16.5, 26.8, 0.2, 0.7, 0.05), (16.5, 33.0, 0.19, 0.75, 0.05),
                   (17.6, 33.5, 0.19, 0.7, 0.05), (22.8, 33.5, 0.2, 0.7, 0.05), (23.3, 33.5, 0.2, 0.0, 0.0)],
              sides=6, mat=RIDGE)
    # Red cap at the wing tip with a grey block inboard, and a pale point under it.
    lib.loft_y(bm, 5.4, [(32.4, 0.0, 0.0, 0.1), (32.8, 1.0, 0.09, 0.1), (33.6, 1.5, 0.13, 0.1),
                         (37.6, 1.5, 0.13, 0.1), (38.4, 1.0, 0.09, 0.1)], sides=10, mat=RED)
    lib.loft_y(bm, 5.2, [(38.3, 1.0, 0.08, 0.08), (39.6, 0.9, 0.06, 0.08), (40.3, 0.0, 0.0, 0.08)], sides=8, mat=PALE)
    plate(bm, [(6.6, 32.8), (9.2, 32.8), (9.2, 36.2), (6.6, 36.2)], 0.0, 0.2, GREY, ch_px=0.4, ch_z=0.03)
    # Thin arc from the wing tip round under the wing to the engine pod: a rail of constant
    # thickness.
    lib.sweep(bm, [(4.9, 39.4, 0.06, 0.75, 0.065), (4.6, 41.0, 0.06, 0.75, 0.065), (4.9, 42.6, 0.06, 0.75, 0.065),
                   (5.7, 44.0, 0.06, 0.75, 0.065), (6.8, 45.3, 0.06, 0.75, 0.065), (8.3, 46.4, 0.06, 0.75, 0.065),
                   (10.2, 46.7, 0.06, 0.75, 0.065), (12.0, 46.4, 0.06, 0.75, 0.065)], sides=8, mat=RIDGE)
    # Dark joint where the wing meets the shoulder.
    lib.loft_y(bm, 19.8, [(24.2, 0.0, 0.0, 0.12), (24.7, 1.6, 0.13, 0.12), (30.6, 1.6, 0.13, 0.12),
                          (31.2, 0.0, 0.0, 0.12)], sides=10, mat=GREY)
    lib.mirror_since(bm, start, WING_AXIS)

    # ---- per-side parts ----
    # Red shoulder armour: two plates on the left, one on the right, standing on the wing root.
    plate(bm, [(19.8, 28.8), (23.0, 28.6), (23.0, 31.2), (20.2, 31.2)], 0.1, 0.32, RED, ch_px=0.5, ch_z=0.04)
    plate(bm, [(23.8, 28.6), (27.2, 28.6), (27.2, 31.2), (23.8, 31.2)], 0.1, 0.36, RED, ch_px=0.5, ch_z=0.04)
    plate(bm, [(36.8, 27.8), (41.2, 28.6), (41.0, 31.2), (37.0, 31.2)], 0.1, 0.34, RED, ch_px=0.5, ch_z=0.04)
    # Struts from the shoulders down to the pods: grey on the left, a bronze rod on the right.
    lib.sweep(bm, [(21.8, 33.6, 0.12, 0.0, 0.0), (21.8, 34.0, 0.12, 1.7, 0.14), (21.8, 39.6, 0.12, 1.7, 0.14),
                   (21.8, 40.2, 0.12, 0.0, 0.0)], sides=10, mat=RIB)
    lib.sweep(bm, [(40.4, 32.6, 0.14, 0.0, 0.0), (40.4, 33.0, 0.14, 0.8, 0.07), (40.4, 39.0, 0.14, 0.8, 0.07),
                   (40.4, 39.5, 0.14, 0.0, 0.0)], sides=8, mat=HULL)
    # Engine pods under the wings.
    pod(bm, 23.6, 11.2, 43.0, 13.2, GREY, DKBR, DARK)
    pod(bm, 38.8, 49.6, 43.0, 47.9, GREY, DKBR, DARK)

    # ---- torso, down the middle ----
    # A hard octagonal shell (flat-shaded), low at the front where the head's pincers hang over
    # it (rows 24-28) and full height from the shoulders down.
    lib.loft_y(bm, 30.5, [(24.0, 0.0, 0.0, 0.0), (24.3, 4.5, 0.14, 0.0), (26.0, 5.8, 0.17, 0.0),
                          (28.6, 6.6, 0.24, 0.06), (31.0, 7.0, 0.36, 0.06), (40.0, 7.0, 0.36, 0.06),
                          (43.5, 6.6, 0.34, 0.06), (45.2, 5.2, 0.28, 0.05), (47.0, 3.4, 0.18, 0.03),
                          (48.2, 0.0, 0.0, 0.0)], sides=8, mat=HULL, smooth=False)
    # Grey chest top (rows 28-31) and the glowing red light under it.
    plate(bm, [(27.4, 28.0), (33.4, 28.0), (33.4, 31.8), (27.4, 31.8)], 0.2, 0.44, GREY, ch_px=0.5, ch_z=0.04)
    lib.ellipsoid(bm, 29.9, 33.1, 0.41, 2.0, 1.4, 0.07, mat=LIGHT, segments=12, rings=6)
    lib.ellipsoid(bm, 29.7, 33.3, 0.44, 0.9, 0.6, 0.05, mat=HOT, segments=10, rings=5)
    # Ribbed grey chest (rows 34-39): a plate with two raised light ribs.
    plate(bm, [(26.9, 33.9), (33.6, 33.9), (33.6, 40.4), (26.9, 40.4)], 0.25, 0.45, GREY, ch_px=0.5, ch_z=0.04)
    for r0, r1 in ((34.2, 35.9), (37.0, 37.9)):
        plate(bm, [(28.2, r0), (32.0, r0), (32.0, r1), (28.2, r1)], 0.4, 0.5, RIB, ch_px=0.3, ch_z=0.03)
    # Bright rail down the left of the chest and a dark strut down its right.
    lib.loft_y(bm, 26.5, [(32.6, 0.0, 0.0, 0.38), (33.0, 0.6, 0.05, 0.38), (39.5, 0.6, 0.05, 0.38),
                          (39.9, 0.0, 0.0, 0.38)], sides=6, mat=RAIL)
    lib.loft_y(bm, 36.0, [(31.0, 0.0, 0.0, 0.34), (31.5, 1.4, 0.08, 0.34), (38.5, 1.4, 0.08, 0.34),
                          (39.0, 0.0, 0.0, 0.34)], sides=8, mat=STRUT)
    # Dark band across the belly and the pale dome below it.
    plate(bm, [(24.6, 40.6), (36.4, 40.6), (36.4, 41.8), (24.6, 41.8)], 0.2, 0.42, DKBR, ch_px=0.3, ch_z=0.03)
    lib.ellipsoid(bm, 29.8, 43.4, 0.3, 2.8, 1.8, 0.15, mat=PALE, segments=12, rings=6)
    # Grey tail nozzle.
    lib.loft_y(bm, 29.6, [(44.6, 3.8, 0.16, 0.02), (47.0, 3.4, 0.15, 0.02), (48.2, 2.6, 0.11, 0.02),
                          (48.8, 0.0, 0.0, 0.02)], sides=10, mat=GREY)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    lib.export_assembly(ROOT, obj, PIECES, sys.argv)


if __name__ == "__main__":
    main()
