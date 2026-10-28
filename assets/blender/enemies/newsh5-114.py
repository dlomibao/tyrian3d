"""Green energy arrow (newsh5.shp frames 114, 228, 266): a 3D version of its sprite.

Seen in episode 4 (levels 4.18 and 4.20). A glowing green arrow flying right: a round shaft with a
white-hot core and a faceted blade head (a light-green inner facet with the core running over it
as a white cross). The three frames only fade it (the same pixels in dimmer greens), so one model
covers them all, its materials stepping down to the dimmer greens on frames 228 and 266
(common.palette_material frames=).

Run: blender --background --python assets/blender/enemies/newsh5-114.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b013 as lib  # noqa: E402

NAME = "newsh5-114"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U


def build(sprite):
    coll = common.reset_collection(NAME)

    def anim(i, part, frames, **kw):
        return common.palette_material(sprite, i, f"{NAME}-{part}", frames=frames, **kw)

    mats = [
        anim(199, "shell", {228: 196, 266: 192}, metallic=0.1, roughness=0.4, emission_strength=2.5),  # 0 green shell
        anim(207, "head", {228: 204, 266: 200}, metallic=0.1, roughness=0.3, emission_strength=3.5),  # 1 bright green head
        anim(47, "core", {228: 204, 266: 200}, roughness=0.3, emission_strength=5.0),  # 2 white-hot core
    ]
    SHELL, BRIGHT, CORE = range(3)
    g = lib.Grid(12, 14)
    yc = g.y(6)
    bm = bmesh.new()

    # Shaft (rows 5-7, columns 0-7): a round rod 3 px across, as tall as it is wide, with a
    # chamfered tail, running into the back of the head.
    x0 = g.x(-0.5)
    lib.loft_x(bm, [(x0, 1.15 * U, 1.15 * U, 0.0), (x0 + 0.4 * U, 1.5 * U, 1.5 * U, 0.0),
                    (g.x(7.0), 1.5 * U, 1.5 * U, 0.0)], y=yc, sides=10, mat_index=SHELL)
    # Core along row 6, bulging out of the shaft's top: a light-green cap (column 1), then white
    # (columns 2-6) into the head's back wall.
    zc = 1.2 * U
    lib.loft_x(bm, [(g.x(0.4), 0.0, 0.0, 0.0), (g.x(1.0), 0.6 * U, 0.55 * U, 0.0),
                    (g.x(1.5), 0.6 * U, 0.55 * U, 0.0)], y=yc, z=zc, sides=8, mat_index=BRIGHT, cap_end=False)
    lib.loft_x(bm, [(g.x(1.5), 0.6 * U, 0.55 * U, 0.0), (g.x(7.0), 0.6 * U, 0.55 * U, 0.0)],
               y=yc, z=zc, sides=8, mat_index=CORE, cap_start=False)

    lib.set_smooth(bm, 0)

    def hull(points, mat):
        """A flat-shaded convex solid from (column, px off row 6, z px) points."""
        before = set(bm.faces)
        verts = [bm.verts.new((g.x(c), yc + dy * U, z * U)) for c, dy, z in points]
        res = bmesh.ops.convex_hull(bm, input=verts)
        unused = list({v for v in res["geom_unused"] + res["geom_interior"] if isinstance(v, bmesh.types.BMVert)})
        if unused:
            bmesh.ops.delete(bm, geom=unused, context="VERTS")
        for f in bm.faces:
            if f not in before:
                f.material_index = mat
                f.smooth = False

    # Head: a faceted blade, 7 px wide and full height over columns 7-8 (back at 6.5, shoulder at
    # column 8's centre), tapering 5/3/1 px to the tip at 11.5. A ridge HEAD_H px above the
    # midplane (mirrored below) falls to the tip with the width; a thin vertical rim at the edges.
    BACK, SHOULDER, TIP, HW, HEAD_H, RIM = 6.5, 8.0, 11.5, 3.5, 2.9, 0.35

    def roof(c, dy):
        return HEAD_H + (RIM - HEAD_H) * abs(dy) / HW - HEAD_H * max(0.0, c - SHOULDER) / (TIP - SHOULDER)

    shell = [(TIP, 0.0, 0.0)]
    for c in (BACK, SHOULDER):
        shell += [(c, 0.0, HEAD_H), (c, 0.0, -HEAD_H)]
        shell += [(c, s * HW, z) for s in (-1, 1) for z in (RIM, -RIM)]
    hull(shell, SHELL)

    def plate(top, lift, mat):
        """A solid whose top lies `lift` px above the head's roof over the outline `top`."""
        hull([(c, dy, roof(c, dy) + lift) for c, dy in top] + [(c, dy, 0.0) for c, dy in top], mat)

    # Light-green inner triangle (column 8 rows 4-8, column 9 rows 5-7, column 10 row 6), a raised
    # facet plate on the shell's faces.
    INNER = 0.3
    plate([(7.5, -2.5), (7.5, 0.0), (7.5, 2.5), (8.0, -2.5), (8.0, 0.0), (8.0, 2.5), (10.8, 0.0)], INNER, BRIGHT)
    # The white core runs on over the head as the sprite's cross: a 1 px ridge strip along row 6
    # (columns 7-9) and a 3 px bar across column 8, standing proud of the inner plate.
    CROSS = INNER + 0.35
    plate([(c, dy) for c in (6.55, 8.0, 9.5) for dy in (-0.5, 0.0, 0.5)], CROSS, CORE)
    plate([(c, dy) for c in (7.5, 8.0, 8.5) for dy in (-1.5, 0.0, 1.5)], CROSS, CORE)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, [obj], sprite)


if __name__ == "__main__":
    main()
