"""Panel satellite (newshl.shp 7, 9, 45 and 47, a 2x2 block): a 3D version of its sprites.

Seen in episode 4, level 40. Four 2x2 sprites make one 48 x 55 px station, mirror symmetric across
its middle row (the lower half is drawn in shadow): a grey core running left to right with a flange
at its left end, a thin glowing blue shaft, a lit sleeve, a wide collar and a red emitter whose rod
reaches a ribbed panel on the right. Five boxy panels, each a frame around two inset cells, stand
around it on arms: above and below (on the bars that run along the core and loop round its left
end), up-right and down-right on diagonal arms from the collar, and on the right on the rod.

Built whole in assembly coordinates, then cut into the four pieces (newshl-7 top left, newshl-9 top
right, newshl-45 bottom left, newshl-47 bottom right). The lower half mirrors the upper half's
shapes but keeps the darker palette indices its sprites use.

Run: blender --background --python assets/blender/enemies/assembly-newshl-45.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b006 as lib  # noqa: E402

NAME = "assembly-newshl-45"
PIECES = ["newshl-7", "newshl-9", "newshl-45", "newshl-47"]
ROOT = common.repo_root(__file__)
U = lib.U
CENTRE = (286, -3)  # the assembly's centre in screen px (its 48 x 56 block)
AXIS = 27.5  # the row edge the station mirrors across (the core's axis)


def P(ex, ey):
    """Pixel edge coordinates in the 48 x 56 assembly block (x right, y down) to Blender X, Y."""
    return ((ex - 24) * U, (28 - ey) * U)


def M(ey):
    """Mirror a row edge coordinate across the core's axis."""
    return 2 * AXIS - ey


def panel(bm, centre, direction, mats, frame, field, cell, length=11.5, width=10.0, cross=False):
    """A boxy panel: a raised frame around a dark field with two lighter inset cells either side of
    a divider running along `direction` (the arm's direction; cross=True also splits the cells
    across). centre is in pixel edge coordinates; direction a Blender-space (dx, dy)."""
    cx, cy = P(*centre)
    d = math.hypot(*direction)
    vx, vy = direction[0] / d, direction[1] / d  # along the panel
    ux, uy = vy, -vx  # across it

    def rect(u0, u1, v0, v1, z0, z1, mat):
        pts = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        outline = [(cx + (u * ux + v * vx) * U, cy + (u * uy + v * vy) * U) for u, v in pts]
        common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)

    hl, hw = length / 2, width / 2
    rect(-hw + 0.9, hw - 0.9, -hl + 0.9, hl - 0.9, -0.05, 0.025, mats(field))
    # Frame bars, bevel-free but proud of the field.
    rect(-hw, hw, hl - 1.0, hl, -0.06, 0.06, mats(frame))
    rect(-hw, hw, -hl, -hl + 1.0, -0.06, 0.06, mats(frame))
    rect(-hw, -hw + 1.0, -hl + 1.0, hl - 1.0, -0.06, 0.06, mats(frame))
    rect(hw - 1.0, hw, -hl + 1.0, hl - 1.0, -0.06, 0.06, mats(frame))
    # The two cells.
    spans = [(-hl + 2.2, -0.45), (0.45, hl - 2.4)] if cross else [(-hl + 2.2, hl - 2.4)]
    for u0, u1 in ((-hw + 1.7, -0.5), (0.5, hw - 1.7)):
        for v0, v1 in spans:
            rect(u0, u1, v0, v1, -0.05, 0.045, mats(cell))


def build(sprites):
    coll = common.reset_collection(NAME)
    m = lib.Mats(NAME, lib.merged_colors(sprites))
    metal = lambda i: m(i, metallic=0.55, roughness=0.4)  # noqa: E731
    bm = bmesh.new()
    ay = P(0, AXIS)[1]

    # --- Core, left to right: (column edge, radius in px, index). Every section is round: as tall
    # as it is wide across, the way the sprite draws it (a lit band along the axis, dark edges).
    def core_run(secs, mat, sides=16):
        start = len(bm.verts)
        common.loft(bm, [(P(e, 0)[0], r * U, r * U, 0.0) for e, r in secs], sides=sides, mat_index=mat)
        lib.rotate_new_to_x(bm, start, ay, 0.0)
        # rotate_new_to_x maps the loft's along-axis to X; our sections are already X positions.

    # Left end cap: a wheel spanning rows 19.5-35.5 at columns 0-4, where the bars loop in.
    core_run([(0.2, 6.8), (0.6, 7.7), (3.8, 7.7), (4.4, 6.6)], metal(9))
    core_run([(4.2, 4.8), (5.2, 4.8)], m(3, metallic=0.4, roughness=0.6))  # groove
    core_run([(5.2, 5.4), (5.8, 5.8), (8.4, 5.8), (9.2, 5.2)], metal(7))
    # Blue shaft: navy, a faint glow only.
    core_run([(9.0, 3.6), (13.2, 3.6)], m(54, metallic=0.4, roughness=0.3, emission_strength=0.6))
    core_run([(12.8, 4.0), (13.4, 4.5), (18.8, 4.5), (19.4, 4.2)], metal(9))  # lit sleeve
    core_run([(18.8, 6.6), (19.4, 7.5), (25.2, 7.5), (25.9, 6.6)], metal(10))  # collar
    core_run([(25.8, 4.6), (28.2, 4.6)], metal(5))  # neck
    # Red emitter: dark crimson, glossy, a low glow.
    core_run([(28.0, 3.4), (29.6, 3.4), (31.0, 1.6), (31.4, 0.0)],
             m(116, metallic=0.2, roughness=0.25, emission_strength=0.8))
    core_run([(31.0, 0.55), (36.2, 0.55)], m(115, metallic=0.0, roughness=0.4, emission_strength=1.0),
             sides=8)  # rod to the right panel
    # Dark band round the collar's middle (rows 25-29 in the sprite are shaded darker).
    core_run([(20.6, 7.6), (24.6, 7.6)], m(4, metallic=0.5, roughness=0.5))
    # Dark housing the rod runs through, between the emitter and the right panel (columns 31-35).
    x0, y0 = P(30.8, 30.6)
    x1, y1 = P(34.6, 24.4)
    lib.box(bm, x0, y0, x1, y1, -2.2 * U, 2.2 * U, mat_index=m(2, metallic=0.4, roughness=0.5))

    # --- Upper and lower halves: same shapes mirrored, each in its own sprite's palette indices.
    halves = [
        # (row mapping, top/bottom panel (frame, field, cell), diagonal panel, bar, arm, pipe, shoulder)
        (lambda e: e, (9, 4, 7), (6, 3, 5), 10, 6, 5, 5),
        (M, (6, 2, 4), (5, 2, 3), 7, 4, 4, 3),
    ]
    for row, top, diag, bar, arm, pipe, shoulder in halves:
        sign = 1 if row(0) == 0 else -1
        # Panel above the core (rows 0.5-11.5, columns 10.5-20.5) on its arm (column 15).
        panel(bm, (15.5, row(6.0)), (0, sign), lambda i: metal(i), *top)
        lib.tube(bm, [((P(15.5, row(10.8))[0], P(0, row(10.8))[1], 0.0), 1.1 * U),
                      ((P(15.5, row(16))[0], P(0, row(16))[1], 0.0), 1.1 * U)], sides=8, mat_index=metal(arm))
        # The bar along the core (rows 15-17, columns 8-22), looping round the flange at column 3.
        y16 = P(0, row(16.2))[1]
        lib.tube(bm, [((P(7.4, 0)[0], y16, 0.04), 1.4 * U), ((P(22.4, 0)[0], y16, 0.04), 1.4 * U)], sides=10,
                 mat_index=metal(bar))
        lib.tube(bm, [((P(7.8, 0)[0], y16, 0.04), 1.0 * U), ((P(4.6, 0)[0], y16, 0.04), 1.0 * U),
                      ((P(3.4, 0)[0], P(0, row(17.6))[1], 0.03), 1.0 * U),
                      ((P(3.0, 0)[0], P(0, row(21.5))[1], 0.02), 1.0 * U)], sides=8, mat_index=metal(pipe))
        # Diagonal arm from the collar (column 25, row 19.5) up to its panel's corner.
        lib.tube(bm, [((P(23.0, 0)[0], P(0, row(19.8))[1], 0.0), 1.9 * U),
                      ((P(26.0, 0)[0], P(0, row(17.4))[1], 0.0), 1.9 * U),
                      ((P(29.6, 0)[0], P(0, row(13.6))[1], 0.0), 1.7 * U)], sides=8, mat_index=metal(arm))
        # Shoulder on the collar (rows 18-20, columns 17-27) that the diagonal arm grows from.
        sx0, sy0 = P(16.8, row(17.8))
        sx1, sy1 = P(27.2, row(21.5))
        lib.box(bm, sx0, sy0, sx1, sy1, -2.6 * U, 2.6 * U, mat_index=metal(shoulder))
        # Diagonal panel: corners about (35.5, 3), (41.5, 9.5), (33.5, 17), (27.5, 11.5).
        panel(bm, (34.5, row(10.25)), (0.69, 0.73 * sign), lambda i: metal(i), *diag, length=11.6, width=9.6)

    # Ribbed panel on the right, across the axis (rows 22.5-32.5, columns 35.5-47.5), cells split both ways.
    panel(bm, (41.6, AXIS), (1, 0), lambda i: metal(i), 6, 3, 4, length=12.0, width=10.0, cross=True)
    # Brackets above and below the emitter (rows 22-23 and 31-32, columns 28-31).
    for r0, r1, idx in ((22.2, 24.0, 7), (31.0, 32.8, 5)):
        x0, y0 = P(28.0, r1)
        x1, y1 = P(31.4, r0)
        lib.box(bm, x0, y0, x1, y1, -0.08, 0.08, mat_index=metal(idx))

    return common.mesh_object(NAME, bm, m.list, coll, smooth=True)


def main():
    sprites = [common.load_sprite(ROOT, n) for n in PIECES]
    obj = build(sprites)
    layout = [(p["model"], p["cx"] - CENTRE[0], p["cy"] - CENTRE[1]) for p in sprites[0]["assemblyLayout"]]
    pieces = common.split_assembly(obj, layout)
    for piece in [obj, *pieces.values()]:
        # Smooth the round parts, keep the boxes' edges crisp.
        split = piece.modifiers.new("edges", "EDGE_SPLIT")
        split.split_angle = math.radians(40)
    for s in sprites:
        common.export_sprite_model(ROOT, [pieces[s["name"]]], f"enemies/{s['name']}", s["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        common.render_preview([obj], str(out), None, size=4)
        for s in sprites:
            f = s["frames"][0]
            common.render_preview([pieces[s["name"]]], str(out.with_name(f"{s['name']}.png")),
                                  ROOT / "reference" / "models" / s["name"] / f["image"], size=2)


if __name__ == "__main__":
    main()
