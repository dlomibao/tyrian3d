"""Twin-disc spindle (newshl.shp 24): a 3D version of its sprite.

Seen in episode 4, level 40. A turned grey shaft runs across the sprite on an axle at z = 0: a
short nose, a wide body, two full-height discs standing on edge (the sprite's 21 px tall bars,
lit on the left, dark on the right) with a deep dark gap between them down to the shaft and a red
stud above and below the shaft in it, then a narrower shaft with dark clamp blocks above and
below it carrying red strips, and a flange where the sprite is cut off. Every round part is round
(as tall as it is wide). newshl 34 (its mirror image) is still built by lib_b020.build_spindle;
this script builds its own, rounder version. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshl-24.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b020 as lib  # noqa: E402

NAME = "newshl-24"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U
GREYS = [2, 4, 6, 9, 10, 12, 13]  # the shades metal faces take from the sprite
OUTLINE_SHADE = 2  # what the sprite's black outline pixels become on the model


def build(name, sprite):
    """Built in the sprite's pixel edge coordinates (column edge e -> X(e), row edge e -> Y(e)),
    the axle along X through row edge 13.5 at z = 0."""
    coll = common.reset_collection(name)
    m = lib.Mats(name, sprite["colors"])
    metal = lambda i: m(i, metallic=0.25, roughness=0.45)  # noqa: E731
    bm = bmesh.new()

    def X(e):
        return (e - 12) * U

    def Y(e):
        return (14 - e) * U

    ay = Y(13.5)

    painted = []  # face ranges of the metal parts, coloured from the sprite below

    def run(secs, mat, sides=16):
        """Round sections (column edge, radius px) or (column edge, radius across, radius up):
        as tall as they are wide. Extra sections at every column edge in between let the faces
        take the sprite's colour column by column."""
        secs = [s if len(s) == 3 else (s[0], s[1], s[1]) for s in secs]
        full = [secs[0]]
        for (e0, a0, b0), (e1, a1, b1) in zip(secs, secs[1:]):
            for c in range(math.floor(e0) + 1, math.ceil(e1)):
                if c - e0 > 0.2 and e1 - c > 0.2:
                    t = (c - e0) / (e1 - e0)
                    full.append((c, a0 + (a1 - a0) * t, b0 + (b1 - b0) * t))
            full.append((e1, a1, b1))
        start = len(bm.faces)
        lib.loft_x(bm, [(X(e), a * U, b * U, 0.0) for e, a, b in full], ay, 0.0, sides=sides, mat_index=mat)
        painted.append((start, len(bm.faces)))

    # Nose (columns 4-7, rows 10-16) and body (columns 7-11, rows 8-18), outline included.
    run([(4.0, 2.4), (4.4, 3.3), (5.0, 3.6), (7.6, 3.6)], metal(10))
    # The body's darker band at column 9 is a shallow turned groove (kept full width from above).
    run([(7.0, 4.6), (7.4, 5.6), (8.85, 5.6), (9.1, 5.6, 5.0), (9.9, 5.6, 5.0), (10.15, 5.6),
         (11.6, 5.6), (12.2, 5.0)], metal(10))
    # Shaft through the discs and between them (seen lit at column 15, rows 9-17).
    run([(11.8, 4.6), (19.6, 4.6)], metal(10))
    # The two discs (rows 3-23 with the outline: 21 px across), on edge, rims rounded.
    run([(12.0, 9.8), (12.35, 10.6), (14.65, 10.6), (15.0, 9.8)], metal(10), sides=28)
    run([(17.0, 9.8), (17.35, 10.6), (19.65, 10.6), (20.0, 9.8)], metal(10), sides=28)
    # Right shaft (columns 19-22, rows 9-17) and the flange at the sprite's edge (column 23).
    run([(19.4, 4.4), (22.8, 4.4)], metal(10))
    run([(22.4, 4.4), (22.8, 5.0), (24.0, 5.0)], metal(10))

    # Dark web low between the discs (columns 15-16): from above the gap is a deep dark slot
    # down past the shaft, with a red stud on the web above and below the shaft (rows 5 and 21).
    lib.box(bm, X(14.9), Y(23.4), X(17.1), Y(3.6), -0.6 * U, 0.6 * U, mat_index=m(1, metallic=0.2, roughness=0.7))
    lib.box(bm, X(16.0), Y(4.0), X(17.1), Y(3.0), -0.6 * U, 0.6 * U, mat_index=m(1, metallic=0.2, roughness=0.7))
    lib.box(bm, X(16.0), Y(24.0), X(17.1), Y(23.0), -0.6 * U, 0.6 * U, mat_index=m(1, metallic=0.2, roughness=0.7))
    for r, idx in ((5, 116), (21, 114)):
        lib.box(bm, X(15.0), Y(r + 1.0), X(16.0), Y(r), 0.0, 1.6 * U,
                mat_index=m(idx, metallic=0.0, roughness=0.4, emission_strength=3.0))

    # Clamp blocks above (rows 6-9) and below (rows 17-21) the right shaft: dark boxes with the
    # sprite's saturated red L strips 1 px proud on top.
    dark = m(1, metallic=0.3, roughness=0.6)  # black like the sprite's pixels round the red
    lib.box(bm, X(19.0), Y(9.6), X(24.0), Y(6.0), -3.0 * U, 2.6 * U, mat_index=dark)
    lib.box(bm, X(19.0), Y(21.0), X(24.0), Y(17.2), -3.0 * U, 2.6 * U, mat_index=dark)
    # Matte and faintly self-lit so they stay saturated red under the lights, not brown-pink.
    red_top, red_bottom = (m(i, metallic=0.0, roughness=0.7, emission_strength=0.8) for i in (114, 113))
    common.slab(bm, [(X(20), Y(7)), (X(24), Y(7)), (X(24), Y(8)), (X(22), Y(8)), (X(22), Y(9)), (X(20), Y(9))][::-1],
                1.2 * U, z=3.0 * U, mat_index=red_top)
    common.slab(bm, [(X(20), Y(18)), (X(22), Y(18)), (X(22), Y(19)), (X(23), Y(19)), (X(23), Y(20)), (X(20), Y(20))],
                1.2 * U, z=3.0 * U, mat_index=red_bottom)

    # Colour each metal face with the sprite's grey at the pixel it covers seen from above (a few
    # shades of the sprite's ramp), so the top view carries the sprite's lit and shadowed bands.
    pix = sprite["frames"][0]["pixels"]
    rgb = sprite["colors"]
    shades = [i for i in GREYS if str(i) in rgb]
    bm.faces.ensure_lookup_table()
    for a, b in painted:
        for f in bm.faces[a:b]:
            if len(f.verts) > 4:
                continue  # end caps keep the part's own shade too
            c = f.calc_center_median()
            if c.z < 0.15 * math.hypot(c.y - ay, c.z):
                continue  # sides and underside keep the part's own shade
            col, row = int(math.floor(c.x / U + 12)), int(math.floor(14 - c.y / U))
            idx = pix[row][col] if 0 <= row < len(pix) and 0 <= col < len(pix[0]) else -1
            if not 1 <= idx <= 13:
                continue
            if idx == 1:
                idx = OUTLINE_SHADE
            q = min(shades, key=lambda i: abs(rgb[str(i)][0] - rgb[str(idx)][0]))
            if idx >= 6 and q != shades[-1]:
                q = shades[shades.index(q) + 1]  # highlights a shade up: the lit render dims them
            f.material_index = metal(q)

    obj = common.mesh_object(name, bm, m.list, coll, smooth=True)
    split = obj.modifiers.new("edges", "EDGE_SPLIT")
    split.split_angle = math.radians(40)
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(NAME, sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
