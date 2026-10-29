"""Bronze winged boss body (newsh4.shp 119, 121, 123): a 3D version of its three-piece sprite.

Seen in one level of episode 4. Three 2x2 enemies side by side make the lower half of a boss
(the head, horns and shoulder pods above it are assembly-newsh4-81): a bronze torso with a grey
ribbed chest and a red light, swept bronze wings with red caps at their tips whose outer edge
loops down and back in under the wing, two grey gun pods slung under the wings on dark arms,
and a bronze collar over a round grey tail dome.

Remodelled on the concept (assets/blender/features/concepts/, registered to the sprite in
assets/blender/textures/assembly-newsh4-123/concept.png): every part sits where the concept
draws it, within the sprite's outline, so the concept detail texture_bake.py projects onto it
lands on the matching part. The shape language is the concept's: hard, chamfered armour plates
and boxy machinery. Each wing is one bronze plate that runs from the shoulder out to the red tip
cap and loops down and back in round an open slot (the sprite's hole) to the gun pod; under the
shoulder a grey armour block carries a red band. The torso is a machinery bay between bronze
side columns: the head's grey hood comes down to the red chest light, two steel tanks flank a
grey chest stack with two light ribs and a small red lamp, and a bronze collar with a pale centre
plate closes it over the tail dome. The gun pods are grey blocks with a recessed grille and a
tall bracket at their outer end, joined to the wing root by a dark tube.

The body is built once in the frame shared with assembly-newsh4-81 (lib_b065) and cut into the
three pieces with common.split_assembly. The sprite is not quite symmetric (its right side is
drawn up to 2 px further out, and its right pod sits further in), so the wings are mirrored about
column edge 30.75, the torso about 30.4, and the parts that differ more are placed per side.
Each piece has a single frame.

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
WING_AXIS = 30.75  # the wings' mirror axis (column edge)
TORSO_AXIS = 30.4  # the torso's
POD_AXIS = 29.9  # the gun pods': the sprite's right pod sits further in than the left one


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


def rect(c0, r0, c1, r1):
    return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh4b"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(23, metallic=0.45, roughness=0.5),  # 0 bronze wings
        pal(24, metallic=0.45, roughness=0.45),  # 1 bronze torso columns and collar
        pal(25, metallic=0.5, roughness=0.4),  # 2 light bronze panels
        pal(27, metallic=0.45, roughness=0.4),  # 3 pale collar plate and tip points
        pal(163, metallic=0.3, roughness=0.6),  # 4 dark bronze bay floor
        pal(6, metallic=0.6, roughness=0.4),  # 5 grey armour, hood, pods
        pal(9, metallic=0.6, roughness=0.35),  # 6 light grey ribs, brackets, grille bars
        pal(3, metallic=0.4, roughness=0.6),  # 7 dark tubes and grille recess
        pal(70, metallic=0.3, roughness=0.5),  # 8 red armour
        pal(74, emission_strength=3.0),  # 9 red lights
        pal(77, emission_strength=5.0),  # 10 chest light core
        pal(10, metallic=0.6, roughness=0.3),  # 11 bright steel tank
        pal(5, metallic=0.6, roughness=0.35),  # 12 darker steel tank
    ]
    WING, HULL, RIDGE, PALE, DKBR, GREY, RIB, DARK, RED, LIGHT, HOT, STEEL, STEEL2 = range(13)
    bm = bmesh.new()

    # ---- left wing, mirrored for the right ----
    start = len(bm.verts)

    def wing_top(c, r):
        t = max(0.0, min(1.0, (c - 4) / 17))  # 0 at the tip, 1 at the root
        return 0.13 + 0.09 * t

    # One plate: shoulder, leading edge, tip, the outer loop down and back in along the bottom to
    # the pod's bracket, then back up the slot's inner edge to the wing root bar.
    wing = [(15.0, 24.3), (18.0, 24.3), (18.0, 32.0), (22.2, 32.0), (22.2, 40.6), (19.2, 40.6),
            (19.2, 35.0), (16.8, 35.0), (6.6, 40.4), (5.9, 41.3), (5.9, 44.9), (8.2, 45.0),
            (10.9, 44.4), (10.9, 48.2), (8.0, 48.2), (6.2, 47.6), (4.6, 46.4), (3.6, 44.8),
            (3.0, 43.0), (3.0, 34.2), (3.6, 33.0), (4.6, 32.4), (8.2, 31.9), (11.0, 29.6),
            (13.4, 27.6), (15.0, 26.2)]
    plate(bm, wing, -0.05, wing_top, WING, ch_px=0.8, ch_z=0.05)
    # Raised inner panel on the wing (the concept's panel between its panel lines), and a light
    # bronze lip along the slot's top edge.
    plate(bm, [(10.6, 31.4), (15.6, 27.2), (17.4, 27.2), (17.4, 31.4)], 0.1,
          lambda c, r: wing_top(c, r) + 0.05, WING, ch_px=0.5, ch_z=0.03)
    plate(bm, [(8.4, 38.0), (16.6, 33.6), (19.0, 33.6), (19.0, 34.9), (16.8, 34.9), (8.4, 39.3)],
          0.1, lambda c, r: wing_top(c, r) + 0.035, RIDGE, ch_px=0.35, ch_z=0.025)
    # Red cap at the wing tip, a grey block inboard of it and a pale point under it.
    plate(bm, [(3.0, 34.0), (3.7, 33.0), (5.8, 32.9), (5.8, 35.4), (6.0, 38.4), (3.0, 38.6)],
          0.0, 0.3, RED, ch_px=0.45, ch_z=0.04)
    plate(bm, rect(5.8, 32.4, 8.4, 35.3), 0.0, 0.26, GREY, ch_px=0.4, ch_z=0.03)
    plate(bm, rect(3.2, 38.6, 5.6, 40.2), 0.0, 0.2, PALE, ch_px=0.35, ch_z=0.03)
    # Grey armour block on the shoulder.
    plate(bm, [(17.8, 24.3), (22.8, 24.3), (22.8, 31.8), (18.3, 31.8), (17.8, 31.2)],
          0.0, 0.38, GREY, ch_px=0.6, ch_z=0.05)
    # Wing root bar: a raised bronze frame running down to the pod.
    plate(bm, rect(19.3, 31.6, 22.4, 40.6), 0.05, 0.27, HULL, ch_px=0.5, ch_z=0.04)
    lib.mirror_since(bm, start, WING_AXIS)

    # ---- per-side wing parts (the sprite differs side to side here) ----
    # Red band across the shoulder: two plates on the left, one on the right.
    plate(bm, rect(19.4, 29.1, 23.3, 30.8), 0.2, 0.44, RED, ch_px=0.4, ch_z=0.04)
    plate(bm, rect(23.6, 29.1, 26.7, 30.6), 0.2, 0.48, RED, ch_px=0.4, ch_z=0.04)
    plate(bm, [(37.8, 28.6), (41.8, 28.8), (41.8, 31.0), (37.8, 31.0)], 0.2, 0.44, RED, ch_px=0.4, ch_z=0.04)
    # The right pod sits further in than the mirrored loop ends: carry the loop's bottom on to it.
    plate(bm, [(48.8, 44.5), (51.0, 44.4), (51.0, 48.2), (48.8, 48.2)], -0.05, 0.14, WING, ch_px=0.5, ch_z=0.04)
    # Light grey rail on the inboard edge of the left root bar (the sprite's grey strut).
    plate(bm, rect(21.3, 32.4, 22.4, 40.2), 0.1, 0.31, RIB, ch_px=0.25, ch_z=0.02)

    # ---- gun pods, left mirrored for the right about POD_AXIS ----
    start = len(bm.verts)
    # Dark tube from the wing root down to the pod (constant diameter).
    lib.sweep(bm, [(19.9, 37.6, 0.12, 0.0, 0.0), (19.7, 37.8, 0.12, 1.1, 0.1), (13.6, 42.5, 0.12, 1.1, 0.1),
                   (13.3, 42.8, 0.12, 0.0, 0.0)], sides=8, mat=DARK, smooth=True)
    # Body with a recessed grille: grey block, dark recess floor, raised frame and bars.
    plate(bm, [(13.8, 42.6), (21.0, 42.6), (23.4, 41.4), (23.4, 44.6), (21.0, 46.9), (13.8, 46.9)],
          -0.05, 0.22, GREY, ch_px=0.4, ch_z=0.03)
    lib.box(bm, 14.5, 43.2, 20.6, 46.4, 0.18, 0.23, mat=DARK)
    plate(bm, rect(13.8, 42.5, 21.0, 43.2), 0.15, 0.33, GREY, ch_px=0.25, ch_z=0.02)
    plate(bm, rect(13.8, 46.4, 21.0, 46.95), 0.15, 0.3, GREY, ch_px=0.2, ch_z=0.02)
    plate(bm, [(20.6, 42.6), (23.4, 41.4), (23.4, 44.6), (20.6, 46.9)], 0.15, 0.37, GREY, ch_px=0.4, ch_z=0.03)
    for c in (14.9, 15.85, 16.8, 17.75, 18.7, 19.65):
        lib.box(bm, c, 43.2, c + 0.42, 46.4, 0.18, 0.3, mat=RIB)
    # Tall bracket at the pod's outer end.
    plate(bm, [(11.6, 42.2), (14.0, 42.2), (14.0, 49.6), (11.6, 49.6), (11.6, 48.2), (10.7, 48.2),
               (10.7, 44.0), (11.6, 44.0)], -0.05, 0.44, RIB, ch_px=0.45, ch_z=0.04)
    lib.box(bm, 12.2, 45.0, 13.5, 47.6, 0.36, 0.47, mat=GREY)
    lib.mirror_since(bm, start, POD_AXIS)

    # ---- torso, mirrored about TORSO_AXIS where it is symmetric ----
    # Bay floor under everything.
    plate(bm, [(23.0, 24.2), (37.8, 24.2), (37.8, 41.4), (23.0, 41.4)], 0.0, 0.24, DKBR, ch_px=0.4, ch_z=0.03)
    start = len(bm.verts)
    # Bronze side columns: upper (the shoulder of the torso) and lower (beside the tanks).
    plate(bm, rect(23.0, 24.2, 26.6, 29.1), 0.1, 0.46, HULL, ch_px=0.5, ch_z=0.04)
    plate(bm, [(23.0, 31.2), (25.4, 31.2), (25.4, 39.4), (24.4, 40.6), (23.0, 40.6)], 0.1, 0.42, HULL,
          ch_px=0.45, ch_z=0.04)
    lib.mirror_since(bm, start, TORSO_AXIS)
    # Steel tanks either side of the chest: upright cylinders with domed tops.
    for col, mat in ((26.6, STEEL), (34.2, STEEL2)):
        lib.loft_y(bm, col, [(31.6, 0.0, 0.0, 0.3), (31.8, 0.8, 0.08, 0.3), (32.4, 1.2, 0.13, 0.3),
                             (40.2, 1.2, 0.13, 0.3), (40.8, 0.0, 0.0, 0.3)], sides=8, mat=mat)
    # The head's grey hood coming down to the red chest light.
    plate(bm, [(26.6, 24.2), (34.2, 24.2), (34.2, 30.8), (32.8, 32.5), (31.5, 33.4), (28.6, 33.4),
               (27.2, 32.5), (26.6, 31.0)], 0.1, 0.52, GREY, ch_px=0.6, ch_z=0.05)
    lib.ellipsoid(bm, 29.9, 33.1, 0.44, 1.5, 1.1, 0.1, mat=LIGHT, segments=10, rings=5)
    lib.ellipsoid(bm, 29.8, 33.0, 0.5, 0.7, 0.55, 0.06, mat=HOT, segments=8, rings=4)
    # Grey chest stack with two raised light ribs and a small red lamp.
    plate(bm, rect(27.6, 34.0, 33.2, 41.0), 0.15, 0.42, GREY, ch_px=0.5, ch_z=0.04)
    for r0, r1 in ((35.4, 36.9), (37.9, 39.2)):
        plate(bm, rect(27.9, r0, 32.9, r1), 0.3, 0.49, RIB, ch_px=0.3, ch_z=0.03)
    plate(bm, rect(29.7, 39.6, 31.0, 40.9), 0.3, 0.47, LIGHT, ch_px=0.2, ch_z=0.02)
    # Bronze collar closing the bay, a pale plate in its middle, and the round light grey tail dome.
    plate(bm, [(23.6, 41.0), (37.2, 41.0), (37.2, 44.4), (35.6, 45.9), (25.2, 45.9), (23.6, 44.4)],
          0.0, 0.38, HULL, ch_px=0.6, ch_z=0.05)
    plate(bm, rect(24.2, 40.8, 36.6, 41.9), 0.3, 0.42, DKBR, ch_px=0.3, ch_z=0.02)
    plate(bm, [(27.4, 42.2), (33.2, 42.2), (33.2, 44.6), (32.2, 45.3), (28.4, 45.3), (27.4, 44.6)],
          0.3, 0.47, PALE, ch_px=0.4, ch_z=0.04)
    lib.ellipsoid(bm, 30.2, 46.6, 0.1, 2.9, 2.0, 0.27, mat=RIB, segments=12, rings=6)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    lib.export_assembly(ROOT, obj, PIECES, sys.argv)


if __name__ == "__main__":
    main()
