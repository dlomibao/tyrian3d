"""Panel satellite facing left (newshl.shp 11, 13, 49 and 51, a 2x2 block): a 3D version of its sprites.

Seen in episode 4, level 40. Four 2x2 sprites make one 48 x 56 px station. Its pixels are exactly
the mirror image (left to right) of the station built in assembly-newshl-45.py (newshl 7, 9, 45,
47), so this builds the same shapes in that station's pixel coordinates and mirrors the result:
a grey core running left to right with a flange at its right end, a thin glowing blue shaft, a lit
sleeve, a wide collar and a red emitter whose rod reaches a ribbed panel on the left. Five boxy
panels, each a frame around two inset cells, stand around it on arms: above and below (on bars
that run along the core and loop round its flange), up-left and down-left on diagonal arms from
the collar, and on the left on the rod. The station is mirror symmetric across its middle row
but the lower half is drawn in shadow, so it keeps the darker palette indices its sprites use.

Built whole in assembly coordinates, then cut into the four pieces (newshl-11 top left, newshl-13
top right, newshl-49 bottom left, newshl-51 bottom right).

Run: blender --background --python assets/blender/enemies/assembly-newshl-49.py [-- --preview out.png]
(the preview is the whole station; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b020 as lib  # noqa: E402

NAME = "assembly-newshl-49"
PIECES = ["newshl-11", "newshl-13", "newshl-49", "newshl-51"]
ROOT = common.repo_root(__file__)
U = lib.U
CENTRE = (36, -3)  # the assembly's centre in screen px (its 48 x 56 block)
AXIS = 27.5  # the row edge the station mirrors across (the core's axis)
ZC = 5.0  # the core's axis height above the panels, px
ZB = 2.5  # how much the bars, pipes, shoulders and brackets are raised with it, px
LIFT = 1  # shade steps the core is painted brighter than the sprite


def P(ex, ey):
    """Pixel edge coordinates in the mirrored (b006) 48 x 56 block (x right, y down) to Blender X, Y,
    before the final mirror: column ex here is column 48 - ex of these sprites."""
    return ((ex - 24) * U, (28 - ey) * U)


def M(ey):
    """Mirror a row edge coordinate across the core's axis."""
    return 2 * AXIS - ey


def panel(bm, centre, direction, mats, frame, base, top, length=11.5, width=10.0, grid=(2, 2),
          recessed=False, fw=2.0, div=1.0):
    """A boxy panel: a raised frame around a grid of cells, grid = (cells across, cells along
    `direction`, the arm's direction). recessed=False: lighter cells (`top`) stand proud of a dark
    base (`base`), so the dividers between them read as grooves. recessed=True: the cells are dark
    pits (`base`) cut about 0.5 px into the panel between light dividers (`top`). centre is in pixel
    edge coordinates; direction a Blender-space (dx, dy)."""
    cx, cy = P(*centre)
    d = math.hypot(*direction)
    vx, vy = direction[0] / d, direction[1] / d  # along the panel
    ux, uy = vy, -vx  # across it

    def rect(u0, u1, v0, v1, z0, z1, mat):
        pts = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        outline = [(cx + (u * ux + v * vx) * U, cy + (u * uy + v * vy) * U) for u, v in pts]
        common.slab(bm, outline, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)

    hl, hw = length / 2, width / 2
    zt = 0.06  # frame and raised parts' top (about 0.7 px)
    zb = zt - 0.045  # the grooves' / pits' floor, about 0.55 px down
    rect(-hw + fw - 0.1, hw - fw + 0.1, -hl + fw - 0.1, hl - fw + 0.1, -0.05, zb, mats(base))
    # Frame bars: the sprite's dark outline pixel (which the game's outline redraws) plus the lit
    # rim inside it.
    rect(-hw, hw, hl - fw, hl, -0.06, zt, mats(frame))
    rect(-hw, hw, -hl, -hl + fw, -0.06, zt, mats(frame))
    rect(-hw, -hw + fw, -hl + fw, hl - fw, -0.06, zt, mats(frame))
    rect(hw - fw, hw, -hl + fw, hl - fw, -0.06, zt, mats(frame))
    nu, nv = grid
    iu0, iu1, iv0, iv1 = -hw + fw, hw - fw, -hl + fw, hl - fw
    cu = (iu1 - iu0 - div * (nu - 1)) / nu
    cv = (iv1 - iv0 - div * (nv - 1)) / nv
    if recessed:
        # Light dividers standing up between the pits.
        for i in range(1, nu):
            u = iu0 + i * cu + (i - 1) * div
            rect(u, u + div, iv0, iv1, zb - 0.01, zt, mats(top))
        for j in range(1, nv):
            v = iv0 + j * cv + (j - 1) * div
            rect(iu0, iu1, v, v + div, zb - 0.01, zt, mats(top))
    else:
        for i in range(nu):
            for j in range(nv):
                u = iu0 + i * (cu + div)
                v = iv0 + j * (cv + div)
                rect(u, u + cu, v, v + cv, zb - 0.01, zt - 0.005, mats(top))


def sprite_grid(sprites):
    """The station's pixels as palette indices, grid[row][col] in these sprites' 48 x 56 block (-1 = empty)."""
    grid = [[-1] * 48 for _ in range(56)]
    for s in sprites:
        lay = next(p for p in s["assemblyLayout"] if p["model"] == s["name"])
        x0, y0 = lay["cx"] - CENTRE[0] + 12, lay["cy"] - CENTRE[1] + 14
        for r, row in enumerate(s["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0 and 0 <= y0 + r < 56 and 0 <= x0 + c < 48:
                    grid[y0 + r][x0 + c] = v
    return grid


# The palette indices the core is painted with (each sprite colour snaps to the nearest of these).
GREYS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
BLUES = [50, 52, 55, 59]
REDS = [113, 114, 115, 116, 117, 118]


def round_run(bm, grid, secs, finish, centre=AXIS, z0=0.0, cap=None, lift=0, power=2.0):
    """A round (circular section) length of the core along X, painted in bands along its length
    like the sprite: each band of faces takes the palette index the sprite shows on that pixel row
    over the run's columns. secs are (column edge in the mirrored b006 block, radius in px); centre is
    the row edge of its axis, z0 its height in units. lift raises every shade that many steps of its
    ramp (the sprite's metal is brighter than the same indices come out under the game's light);
    power > 2 squares the section off (a superellipse) into a flat-topped plate."""
    ay = P(0, centre)[1]
    R = max(r for _, r in secs)
    e0, e1 = min(e for e, _ in secs), max(e for e, _ in secs)
    cols = [c for c in range(48) if e0 < 48 - c - 0.5 < e1]  # these sprites' columns it covers

    def snap(v):
        pool = REDS if v >= 112 else BLUES if v >= 48 else GREYS
        if pool is GREYS and v < 10:
            # The sprite's shades include its drawn shadows, which the game's lighting adds again:
            # lift the darker greys part of the way towards the metal's base shade.
            v = v + (10 - v) * 0.25
        return up(min(pool, key=lambda q: abs(q - v)))

    def up(v):
        pool = REDS if v >= 112 else BLUES if v >= 48 else GREYS
        if v not in pool or pool is BLUES:  # the glowing blue is bright enough
            return v
        return pool[min(pool.index(v) + lift, len(pool) - 1)]

    rows = {}

    def colour(t):
        """The index at across offset t (px, + = down the screen) from the axis."""
        row = int(math.floor(centre + t))
        if row not in rows:
            vals = [grid[row][c] for c in cols if 0 <= row < 56 and grid[row][c] >= 0]
            vals = [v for v in vals if v != 1] or vals
            if not vals:
                rows[row] = None
            else:
                rows[row] = snap(sorted(vals)[len(vals) // 2])  # the (upper) median shade
        if rows[row] is None:  # an outline-only row: use the next row in
            return colour(t - math.copysign(1, t)) if abs(t) >= 1 else up(cap or GREYS[3])
        return rows[row]

    # Across positions of the ring's vertices: where the sprite's colour changes between rows, plus
    # enough angles to keep it round (no face wider than about 22 degrees).
    ts = []
    for k in range(int(math.ceil(centre - R)), int(math.floor(centre + R)) + 1):
        t = k - centre
        if abs(t) < R - 0.3 and colour(t - 0.5) != colour(t + 0.5):
            ts.append(t)
    n = max(8, int(math.ceil(180 / 22)))
    for i in range(n + 1):
        t = -R * math.cos(math.pi * i / n)
        if all(abs(t - q) > 0.35 for q in ts) or i in (0, n):
            ts.append(t)
    ts = sorted(set(round(t, 4) for t in ts))
    ring = [(t, R * max(1.0 - (abs(t) / R) ** power, 0.0) ** (1.0 / power)) for t in ts]
    ring += [(t, -z) for t, z in reversed(ring[1:-1])]
    mats = [finish(colour((a[0] + b[0]) / 2)) for a, b in zip(ring, ring[1:] + ring[:1])]

    rings = []
    for e, r in secs:
        k = r / R
        x = P(e, 0)[0]
        rings.append([bm.verts.new((x, ay - t * k * U, z0 + z * k * U)) for t, z in ring])
    for ra, rb in zip(rings, rings[1:]):
        for i in range(len(ring)):
            j = (i + 1) % len(ring)
            bm.faces.new((ra[i], ra[j], rb[j], rb[i])).material_index = mats[i]
    end = finish(up(cap) if cap is not None else colour(-R * 0.4))
    bm.faces.new(list(reversed(rings[0]))).material_index = end
    bm.faces.new(rings[-1]).material_index = end


def build(sprites):
    coll = common.reset_collection(NAME)
    m = lib.Mats("nshl49", lib.merged_colors(sprites))
    metal = lambda i: m(i, metallic=0.3, roughness=0.45)  # noqa: E731
    core = lambda i: m(i, metallic=0.15, roughness=0.45)  # noqa: E731
    bm = bmesh.new()
    ay = P(0, AXIS)[1]
    grid = sprite_grid(sprites)

    # --- Core, left to right in b006 columns (the sprites' right to left): round in section,
    # painted like the sprite (column edge, radius in px), one step brighter than the sprite's shades
    # (its silver drum otherwise comes out mid grey under the game's light). Its axis stands ZC above
    # the panels' plane so the drum sits on the station rather than hanging through it.
    zc = ZC * U
    round_run(bm, grid, [(0.0, 7.4), (0.5, 8.0), (3.6, 8.0), (4.2, 7.0)], core, cap=10, z0=zc, lift=LIFT)  # end flange
    round_run(bm, grid, [(4.2, 5.8), (5.2, 5.8)], core, z0=zc, lift=LIFT)  # groove
    round_run(bm, grid, [(5.2, 5.8), (6.0, 6.2), (8.8, 6.2), (9.6, 5.6)], core, z0=zc, lift=LIFT)  # end cap
    round_run(bm, grid, [(9.0, 3.6), (13.2, 3.6)],
              lambda i: m(i, metallic=0.1, roughness=0.2, emission_strength=2.5), z0=zc, lift=LIFT)  # glowing shaft
    round_run(bm, grid, [(12.6, 4.6), (13.2, 4.9), (18.8, 4.9), (19.4, 4.6)], core, z0=zc, lift=LIFT)  # lit sleeve
    # The raised plate round the drum's left end (sprite columns 22-29): a flat-topped, round-cornered
    # block rather than a ring, its lit top face flat like the sprite's.
    round_run(bm, grid, [(18.8, 6.4), (19.3, 7.5), (25.4, 7.5), (25.9, 6.4)], core, cap=7, z0=zc, lift=LIFT,
              power=3.2)
    round_run(bm, grid, [(25.8, 4.6), (27.9, 4.6)], core, z0=zc, lift=LIFT)  # neck
    # Red emitter: a stubby cone, 6 px across where it meets the neck and still about 5 px across at
    # its left end (the sprite's 3 x 5 px red block), closing onto the rod. A step brighter than the
    # sprite's indices so its lit side reads as the sprite's crimson.
    round_run(bm, grid, [(27.8, 3.2), (28.4, 3.0), (30.7, 2.4), (31.2, 1.3), (31.5, 0.7)],
              lambda i: m(i, metallic=0.0, roughness=0.4, emission_strength=3.0), cap=117, z0=zc, lift=1)
    # Rod from the emitter down to the panel on the right.
    core_rod = len(bm.verts)
    common.loft(bm, [(P(31.0, 0)[0], 0.6 * U, 0.6 * U, zc), (P(32.6, 0)[0], 0.6 * U, 0.6 * U, zc * 0.55),
                     (P(36.2, 0)[0], 0.6 * U, 0.6 * U, 0.04)], sides=8,
                mat_index=m(116, metallic=0.0, roughness=0.4, emission_strength=2.5))
    lib.rotate_new_to_x(bm, core_rod, ay, 0.0)

    # --- Upper and lower halves: same shapes mirrored, each in its own sprite's palette indices.
    # Panels are sized to take in the sprite's dark outline pixels. Panel colours are (frame, base,
    # top) with the grid and whether the cells are pits (see panel()).
    zb = ZB * U  # the bars, pipes and shoulders ride this much higher than before, with the drum
    halves = [
        # (row mapping, top/bottom panel, diagonal panel, bar, arm, pipe, strut, shoulder)
        # Above: the top panel's lighter cells in 2 columns x 3 rows; the up-left panel the lightest,
        # silver framed, with a 3 x 3 grid of dark pits between light dividers.
        (lambda e: e, ((9, 5, 8), (2, 3), False, 2.0), ((9, 3, 6), (3, 3), True, 1.6), 10, 6, 5, 6, 5),
        # Below, in shadow: the bottom panel 2 x 2; the down-left panel dark, 2 x 3 black pits.
        (M, ((6, 2, 4), (2, 2), False, 2.0), ((3, 1, 2), (2, 3), True, 1.6), 7, 4, 4, 2, 2),
    ]
    for row, top, diag, bar, arm, pipe, strut, shoulder in halves:
        sign = 1 if row(0) == 0 else -1
        # Panel above the core (rows 0-12.5, columns 10-21) on its arm (column 15).
        (cols, cgrid, pits, fw) = top
        panel(bm, (15.5, row(6.25)), (0, sign), lambda i: metal(i), *cols, length=12.5, width=11.0, grid=cgrid,
              recessed=pits, fw=fw)
        lib.tube(bm, [((P(15.5, row(10.8))[0], P(0, row(10.8))[1], 0.0), 1.4 * U),
                      ((P(15.5, row(16))[0], P(0, row(16))[1], zb), 1.4 * U)], sides=8, mat_index=metal(arm))
        # The bar along the core (rows 14.5-18, columns 7-23), looping round the flange at column 3.
        round_run(bm, grid, [(6.8, 1.8), (7.3, 2.2), (22.5, 2.2), (23.0, 1.8)], core, centre=row(16.5),
                  z0=0.04 + zb, cap=bar, lift=LIFT)
        lib.tube(bm, [((P(7.8, 0)[0], P(0, row(16.4))[1], 0.04 + zb), 1.3 * U),
                      ((P(5.4, 0)[0], P(0, row(16.6))[1], 0.04 + zb), 1.3 * U),
                      ((P(4.2, 0)[0], P(0, row(17.8))[1], 0.03 + zb), 1.3 * U),
                      ((P(3.5, 0)[0], P(0, row(19.5))[1], 0.02 + zb), 1.3 * U),
                      ((P(3.5, 0)[0], P(0, row(21.5))[1], 0.02 + zb), 1.3 * U)], sides=8,
                 mat_index=metal(min(pipe + 1, 13)))
        # Shoulder joining the bar and the diagonal strut to the collar (rows 17.4-21.2, columns 18-31.5).
        x0, y0 = P(16.5, row(21.2) if sign > 0 else row(17.4))
        x1, y1 = P(30.0, row(17.4) if sign > 0 else row(21.2))
        lib.box(bm, x0, y0, x1, y1, -0.15, 0.15 + zb, mat_index=metal(shoulder))
        # Dark plate in the gap between the shoulder and the lit sleeve (rows 21.7-22.9, columns 28-35.5).
        x0, y0 = P(12.5, row(22.9) if sign > 0 else row(21.7))
        x1, y1 = P(20.0, row(21.7) if sign > 0 else row(22.9))
        lib.box(bm, x0, y0, x1, y1, -0.06, 0.06 + zb, mat_index=metal(2))
        # Diagonal strut from the collar (column 25, row 19.5) up to its panel's corner: a thick bar.
        lib.tube(bm, [((P(25.6, 0)[0], P(0, row(19.4))[1], 0.05 + zb * 0.6), 1.8 * U),
                      ((P(28.5, 0)[0], P(0, row(16.4))[1], 0.03 + zb * 0.2), 1.8 * U),
                      ((P(32.4, 0)[0], P(0, row(14.8))[1], 0.0), 1.7 * U)], sides=8, mat_index=metal(strut))
        # Diagonal panel: corners about (35.5, 3), (41.5, 9.5), (33.5, 17), (27.5, 11.5).
        (cols, cgrid, pits, fw) = diag
        panel(bm, (34.6, row(10.4)), (0.69, 0.73 * sign), lambda i: metal(i), *cols, length=12.8, width=10.3,
              grid=cgrid, recessed=pits, fw=fw)

    # Ribbed panel on the right, across the axis (rows 22-33, columns 35-48), cells split both ways.
    panel(bm, (41.5, AXIS), (1, 0), lambda i: metal(i), 5, 2, 4, length=13.0, width=11.0, grid=(2, 2))
    # The collar's brackets above and below the emitter (rows 21-24 and 31-34, columns 26-33), up
    # against the raised neck.
    for r0, r1, idx in ((21.0, 24.2, 5), (30.8, 34.0, 3)):
        x0, y0 = P(26.0, r1)
        x1, y1 = P(33.0, r0)
        lib.box(bm, x0, y0, x1, y1, -0.1, 0.1 + zb, mat_index=metal(idx))
    # Square tabs either side of the rod where it leaves the emitter (rows 24-27 and 28-31, columns
    # 13-17), standing a pixel proud of the brackets.
    for r0, r1, idx in ((24.0, 26.9, 6), (28.1, 31.0, 4)):
        x0, y0 = P(30.6, r1)
        x1, y1 = P(35.0, r0)
        lib.box(bm, x0, y0, x1, y1, -0.07, 0.1 + zb + U, mat_index=metal(idx))

    # The sprites are the b006 station (assembly-newshl-45) drawn facing left: mirror it.
    lib.mirror_x(bm)
    return common.mesh_object(NAME, bm, m.list, coll, smooth=True)


def main():
    import tempfile
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
        ref = lib.composite_png(ROOT, layout, 48, 56, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=4)
        for s in sprites:
            f = s["frames"][0]
            common.render_preview([pieces[s["name"]]], str(out.with_name(f"{s['name']}.png")),
                                  ROOT / "reference" / "models" / s["name"] / f["image"], size=2)


if __name__ == "__main__":
    main()
