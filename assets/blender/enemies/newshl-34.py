"""Twin-plate spindle facing left (newshl.shp 34): a 3D version of its sprite.

Seen in episode 4, level 40. A grey shaft runs across the sprite: a collar where the sprite is
cut off on the left, a shaft with red L-brackets above and below it, two round plates (a thick
one, then a thin one) standing on edge with a red stud bolted between them above and below the
shaft, a wide drum and a short nozzle on the right. newshl 34 is newshl 24 mirrored left to
right; newshl 24 is still built by lib_b020.build_spindle, while this script builds its own,
rounder version (fix round 1, D39): the plates are 21 px discs seen edge-on (circles in the side
elevation, flat faces), the drum and nozzle are round, and every part covers the sprite's 1 px
black outline. The gap between the plates is open down to a dark web at the midplane with the red
studs on it, the brackets are raised blocks in each pixel's red, and the round parts' upper faces
take the sprite's greys under them (its highlights and outline; not its baked dark lower half).
One frame, one model.

Run: blender --background --python assets/blender/enemies/newshl-34.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b020 as lib  # noqa: E402

NAME = "newshl-34"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U


def X(e):
    """Sprite column edge e (newshl 34's own columns) to x."""
    return (e - 12) * U


def Y(r):
    """Sprite row edge r to y."""
    return (14 - r) * U


AY = Y(13.5)  # the shaft's axis: the plates (rows 3-23), shaft and nozzle are centred on edge 13.5


GREYS = (1, 3, 5, 7, 9, 11, 13)  # the grey ramp indices the metal is painted with (few materials)


def build(name, sprite):
    coll = common.reset_collection(name)
    m = lib.Mats(name, sprite["colors"])
    metal = lambda i: m(i, metallic=0.3, roughness=0.35)  # noqa: E731
    bm = bmesh.new()
    pixels = [[int(v) for v in (row.split() if isinstance(row, str) else row)] for row in sprite["frames"][0]["pixels"]]

    def sprite_index(x, y):
        """The sprite pixel under (x, y) seen from above, or -1."""
        c, r = math.floor(x / U + 12), math.floor(14 - y / U)
        if 0 <= r < len(pixels) and 0 <= c < len(pixels[0]):
            return pixels[r][c]
        return -1

    dark = m(2, metallic=0.2, roughness=0.6)
    painted = []  # face ranges whose upper faces take the sprite's grey under them (fix round 1)

    def run(secs, mat, sides=16, caps=True, paint=True):
        """A round part along the shaft: sections are (column edge, radius px), as tall as wide."""
        start = len(bm.faces)
        lib.loft_x(bm, [(X(e), r * U, r * U, 0.0) for e, r in secs], AY, 0.0, sides=sides, mat_index=mat,
                   cap_start=caps, cap_end=caps)
        if paint:
            painted.append((start, len(bm.faces)))

    # Shaft from the cut-off collar at the left edge to the drum, crossing the gap between plates.
    run([(0.0, 4.6), (1.0, 4.6), (1.0, 4.4), (8.0, 4.4)], metal(8), sides=20)  # collar + left shaft
    run([(7.5, 4.3), (9.6, 4.3)], metal(7), sides=20)  # through the gap

    # The two plates: discs 21 px across standing on edge (rows 3-23), flat faces, bevelled rims.
    # The thick one covers columns 4-7, the thin one 9-11; the gap between them (column 8) is open.
    def disc(e0, e1, c0, c1, r=10.5, bevel=0.5):
        """Flat grey faces, a grey rim between column edges c0 and c1, and dark bevels and rim
        bands on both edges out to them (the sprite's outline columns)."""
        run([(e0, r - bevel), (e1, r - bevel)], metal(8), sides=28, paint=False)
        run([(e0, r - bevel), (e0 + bevel, r), (c0, r)], dark, sides=28, caps=False, paint=False)
        run([(c0, r), (c1, r)], metal(8), sides=28, caps=False)
        run([(c1, r), (e1 - bevel, r), (e1, r - bevel)], dark, sides=28, caps=False, paint=False)

    disc(4.0, 7.7, 5.0, 7.0)
    disc(9.3, 12.0, 10.0, 11.0)

    # The drum (columns 12-16, rows 8-18 with its outline) and the nozzle (columns 17-19, rows 10-16).
    run([(11.8, 4.9), (12.3, 5.5), (16.2, 5.5), (16.7, 5.1)], metal(9), sides=20)
    run([(16.5, 3.6), (19.6, 3.5), (20.0, 3.0)], metal(8), sides=16)

    # The gap between the plates is open down to the midplane: a thin dark web there (rows 4-23,
    # seen from above as the sprite's dark column 8), with a red stud standing on it above and
    # below the shaft (rows 5 and 21), deep between the plates.
    for r0, r1 in ((4.0, 9.6), (17.4, 23.0)):
        lib.box(bm, X(7.7), Y(r1), X(9.3), Y(r0), -0.6 * U, 0.4 * U, mat_index=m(1, metallic=0.2, roughness=0.7))
    stud = lambda i: m(i, metallic=0.0, roughness=0.45, emission_strength=3.0)  # noqa: E731
    for r, idx in ((5, 116), (21, 114)):
        lib.box(bm, X(7.75), Y(r + 1.0), X(9.25), Y(r), 0.4 * U, 3.4 * U, mat_index=stud(idx))

    # Red L-brackets on the thick plate's face, above (rows 7-8) and below (rows 18-19) the shaft:
    # a dark base covering the sprite's outline round them, and the red bar standing proud of it,
    # one block per sprite pixel in that pixel's red so the bright and dark reds match the sprite.

    def outline(pts):
        return [(X(c), Y(r)) for c, r in pts]

    def solid(pts, z0, z1, mat):
        common.slab(bm, outline(pts), (z1 - z0) * U, z=(z0 + z1) / 2 * U, mat_index=mat)

    top_dark = [(0.0, 8.6), (1.6, 8.6), (1.6, 9.3), (4.2, 9.3), (4.2, 6.4), (0.0, 6.4)]
    bot_dark = [(0.0, 20.6), (4.2, 20.6), (4.2, 17.7), (0.0, 17.7)]
    solid(top_dark, -1.6, 1.4, dark)
    solid(bot_dark, -1.6, 1.4, dark)
    for c in range(0, 4):
        for r in (7, 8, 18, 19):
            idx = pixels[r][c]
            if idx < 100:
                continue
            x1 = 4.1 if c == 3 else c + 1  # the bars run into the thick plate's face
            glow = idx >= 115
            mat = m(idx, metallic=0.0, roughness=0.6, emission_strength=2.0 if glow else 0.0)
            lib.box(bm, X(c), Y(r + 1), X(x1), Y(r), -1.2 * U, 3.0 * U, mat_index=mat)

    # Paint the upper faces of the grey parts with the sprite's grey under them (rounded to the
    # ramp in GREYS), so the top view carries the sprite's highlight bands and dark lower edges.
    bm.faces.ensure_lookup_table()
    for f0, f1 in painted:
        for f in bm.faces[f0:f1]:
            f.normal_update()
            n, c = f.normal, f.calc_center_median()
            rad = math.hypot(c.y - AY, c.z)  # the loft's winding is mirrored, so use the centre's
            if abs(n.x) >= 0.7 or rad == 0 or c.z / rad < -0.2:  # direction from the axis, not n.z
                continue  # an end face, or underneath
            idx = sprite_index(c.x, c.y)
            if not 0 <= idx <= 13:
                idx = sprite_index(c.x, c.y + (0.4 * U if c.y < AY else -0.4 * U))  # just inside the edge
            if not 0 <= idx <= 13:
                idx = 1
            # The sprite's dark lower half is its baked shading, which the lighting already gives,
            # so only its highlights and its outline (on the sides, seen edge-on) are kept.
            if abs(c.z) / rad > 0.2:
                idx = max(idx, 6)
            else:
                idx = 1 if idx <= 2 else max(idx, 6)
            f.material_index = metal(min(GREYS, key=lambda g: abs(g - idx)))

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
