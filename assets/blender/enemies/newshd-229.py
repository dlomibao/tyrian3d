"""Asteroid with a blue light (newshd.shp frames 229, 231, 233 and 235): a 3D version of its sprites.

Seen in episode 1 (level 1.5). The same grey boulder as newshd-229, 23 x 23 px, made of
a few lumps: a big pale one on the left, one on top right, a bright knob in the middle and two
smaller ones below, split by dark cracks), with a blue light in the crack below the middle knob
that the frames switch on and grow into a glowing diamond. The frames only change the light, so
one model covers them all: the rock as in newshd-229, with a glowing blue crystal set in the
crack for each look of the light (none, a small cross, a deep-blue diamond, a pale-blue one).
Its faces take the grey of the first frame's pixels.

Run: blender --background --python assets/blender/enemies/newshd-229.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b036 as lib  # noqa: E402
from lib_b036 import common  # noqa: E402

NAME = "newshd-229"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    grid = lib.Grid(24, 28, frame["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    under = mats(4, metallic=0.1, roughness=0.9)
    bm = bmesh.new()
    lumps = [
        (7.5, 10.5, 6.5, 0.07),  # big pale lump, left
        (17.0, 6.5, 5.5, 0.06),  # top right
        (14.5, 12.5, 3.5, 0.05),  # bright knob in the middle
        (7.0, 18.0, 5.0, 0.05),  # lower left
        (17.5, 16.5, 4.5, 0.04),  # lower right
    ]
    first = lib.rock(bm, grid, (12.0, 13.0), top=0.22, bottom=0.16, lumps=lumps, shade=0.03,
                     colors=sprite["colors"], n=12, mat_index=under)
    lib.paint(bm, first, grid, lambda i: mats(i, metallic=0.1, roughness=0.85), min_nz=-0.3)
    rock = common.mesh_object(NAME, bm, mats.list, coll, smooth=True)

    # The blue light, set in the crack below the middle knob (centre row 14, column 12): off on
    # frame 229, a small dark-blue cross on 231 (rows 13-15), a diamond on 233 and 235 (rows 12-16,
    # columns 10-14) that brightens from deep blue to pale blue with a white-hot heart on 235. Each
    # look is a glowing crystal, a flattened octahedron with its tips along the arms, shown on its
    # frames (common.frame_part); the diamond's colours change between 233 and 235.
    gc, gr = 12, 14
    gx, gy = grid.x(gc), grid.y(gr)
    near = [v.co.z for v in rock.data.vertices if (v.co.x - gx) ** 2 + (v.co.y - gy) ** 2 < (2.0 / 12) ** 2
            and v.co.z > 0]
    z0 = sum(near) / len(near)

    def crystal(name, r, heart_r, gmats, frames):
        bm = bmesh.new()
        ring = [bm.verts.new((gx + r * dx, gy + r * dy, z0)) for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1))]
        top = bm.verts.new((gx, gy, z0 + 0.06 * r / (2.6 / 12)))
        bottom = bm.verts.new((gx, gy, z0 - 0.08))
        for k in range(4):
            j = (k + 1) % 4
            bm.faces.new((ring[k], ring[j], top)).material_index = 0
            bm.faces.new((ring[j], ring[k], bottom)).material_index = 0
        # Its brighter heart (the middle pixel), just proud of the crystal's tip.
        hz = z0 + 0.05 * r / (2.6 / 12)
        common.loft(bm, [(gy - 0.6 / 12, 0.0, 0.0, hz), (gy, heart_r, 0.03, hz),
                         (gy + 0.6 / 12, 0.0, 0.0, hz)], sides=8, mat_index=1)
        bm.verts.ensure_lookup_table()
        for v in bm.verts[6:]:
            v.co.x += gx
        return common.frame_part(common.mesh_object(f"{NAME}_light_{name}", bm, gmats, coll, smooth=False), frames)

    small = crystal("small", 1.6 / 12, 0.5 / 12, [
        common.palette_material(sprite, 151, NAME, metallic=0.2, roughness=0.2, emission_strength=3.0),
        common.palette_material(sprite, 154, NAME, metallic=0.2, roughness=0.2, emission_strength=4.0)], [231])
    big = crystal("big", 2.6 / 12, 0.55 / 12, [
        common.palette_material(sprite, 152, f"{NAME}_light", metallic=0.2, roughness=0.2, emission_strength=4.0,
                                frames={235: 156}),
        common.palette_material(sprite, 157, f"{NAME}_heart", metallic=0.1, roughness=0.15, emission_strength=6.0,
                                frames={235: 141})], [233, 235])
    return [rock, small, big]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objs = build(sprite)
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, objs, sprite)


if __name__ == "__main__":
    main()
