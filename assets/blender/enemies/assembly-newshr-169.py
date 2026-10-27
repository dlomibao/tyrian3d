"""Furnace column (newshr.shp, two 2x2 pieces: newshr-167 on top of newshr-169): a 3D version of
its sprites, built whole and cut into the two pieces.

Seen in episode 3 (level 3.4). A grey housing holds a big glowing ball of fire in a bronze-rimmed
socket; below it three grey blocks, separated by narrow gaps, each carry a glowing oval lens in
a grey bezel (the lower two with ribbed panels at the left), and a brown pipe runs down the
right of the lowest two. The four frames of each piece only change colours, so one model per piece
covers them, its materials taking each frame's palette colour (palette_material frames=): on
newshr-167 (frames 167, 205, 243, 281) the fire dims two palette steps a frame from yellow-orange
towards red and the bronze rim round it turns red-brown; on newshr-169 (169, 207, 245, 283) the
top and bottom lenses brighten while the middle one dims.

Run: blender --background --python assets/blender/enemies/assembly-newshr-169.py [-- --preview out.png]
(the preview is the whole column; each piece also gets <piece>.png next to it; -- --frames <dir>
renders every frame of each piece to <dir>/<piece>.png).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b105 as lib  # noqa: E402

NAME = "assembly-newshr-169"
ROOT = common.repo_root(__file__)
W, H = 24, 56
G = lib.Grid(W, H)
# Piece centres relative to the column's centre, in screen px (sprite.json assemblyLayout:
# newshr-167 at (148, -14), newshr-169 at (148, 14)).
PIECES = [("newshr-167", 0, -14), ("newshr-169", 0, 14)]
PX = 1 / 12


def build(palette):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(palette, i, "nshr169", **kw)  # noqa: E731

    def anim(i, part, frames, **kw):
        """A palette material that changes colour by frame: {sprite frame: palette index}."""
        return common.palette_material(palette, i, f"nshr169_{part}", frames=frames, **kw)

    mats = [
        pal(5, metallic=0.6, roughness=0.4),  # 0 grey housing
        pal(3, metallic=0.6, roughness=0.45),  # 1 dark grey blocks
        pal(2, metallic=0.4, roughness=0.6),  # 2 recesses
        pal(10, metallic=0.75, roughness=0.25),  # 3 bright bezels
        pal(7, metallic=0.65, roughness=0.35),  # 4 mid grey ribs and rails
        anim(24, "rim", {205: 71, 243: 69, 281: 68}, metallic=0.7, roughness=0.3),  # 5 bronze socket rim
        anim(121, "fire", {205: 119, 243: 117, 281: 115}, emission_strength=3.0),  # 6 orange fire
        anim(124, "fire_core", {205: 122, 243: 120, 281: 118}, emission_strength=4.0),  # 7 yellow fire
        pal(127, emission_strength=6.0),  # 8 white-hot
        # The lenses of newshr-169 (body, then core): the top one brightens, the middle one dims,
        # the bottom one brightens.
        anim(117, "lens1", {207: 119, 245: 122, 283: 124}, emission_strength=2.5),  # 9 red lens
        anim(120, "lens1_core", {207: 122, 245: 125, 283: 127}, emission_strength=3.5),  # 10 its core
        anim(123, "lens2", {207: 122, 245: 120, 283: 118}, emission_strength=3.5),  # 11 yellow lens
        pal(165, metallic=0.3, roughness=0.5),  # 12 brown pipe
        pal(12, metallic=0.8, roughness=0.2),  # 13 brightest grey edge
        anim(124, "lens2_core", {207: 123, 245: 121, 283: 119}, emission_strength=4.0),  # 14 its core
        anim(117, "lens3", {207: 119, 245: 120, 283: 123}, emission_strength=2.5),  # 15 bottom lens
        anim(120, "lens3_core", {207: 122, 245: 123, 283: 126}, emission_strength=3.5),  # 16 its core
    ]
    (GREY, DGREY, RECESS, BEZEL, RIB, BRONZE, FIRE, YELLOW, HOT, LENS1, LENS1_CORE, LENS2, PIPE, EDGE,
     LENS2_CORE, LENS3, LENS3_CORE) = range(17)
    bm = bmesh.new()

    # ---- the furnace housing (rows 10-28) and the first lens block (rows 28-37), one piece ----
    lib.box(bm, G.x(0), G.y(10), G.x(24), G.y(28), 0.0, 0.2, mat=GREY)
    # Rounded rails down its sides (lighter on the lit left).
    for c, mat in ((1.6, EDGE), (22.4, BEZEL)):
        lib.tube(bm, [(G.x(c), G.y(10.3), 0.2), (G.x(c), G.y(27.7), 0.2)], 1.5 * PX, mat=mat, sides=8)
    # Socket: a bronze rim round the ball, on a grey collar.
    bx, by = G.xy(11.5, 19.5)
    brx, bry = 10.3 * PX, 8.4 * PX
    lib.ellipsoid(bm, (bx, by, 0.2), (brx + 0.6 * PX, bry + 0.6 * PX, 0.07), mat=BRONZE, segments=24, rings=6,
                  half=True)
    # The ball of fire: orange skin, a yellow core swelling out of it and white-hot swirls on top.
    ball_h = 0.3
    lib.ellipsoid(bm, (bx, by, 0.2), (brx, bry, ball_h), mat=FIRE, segments=24, rings=10, half=True)
    ball = lib.Dome(bx, by, brx, bry, ball_h, z0=0.2)
    yx, yy = G.xy(11.0, 19.0)
    lib.ellipsoid(bm, (yx, yy, 0.2), (9.0 * PX, 7.4 * PX, ball_h + 0.03), mat=YELLOW, segments=20, rings=8,
                  half=True)
    ball = lib.Dome(yx, yy, 9.0 * PX, 7.4 * PX, ball_h + 0.03, z0=0.2)
    for c, r, rx, ry in ((9.3, 17.0, 4.9, 3.0), (13.2, 15.3, 2.2, 2.4), (17.3, 20.6, 1.8, 3.2)):
        x, y = G.xy(c, r)
        lib.ellipsoid(bm, (x, y, ball.z(x, y) + 0.02), (rx * PX, ry * PX, 0.03), mat=HOT, segments=10, rings=4)
    # The swirl's lower arm (rows 22-24).
    pts = []
    for c, r in ((11.5, 24.4), (13.5, 24.0), (15.5, 23.2), (17.0, 22.0)):
        x, y = G.xy(c, r)
        pts.append((x, y, ball.z(x, y) + 0.012))
    lib.tube(bm, pts, [0.04, 0.075, 0.085, 0.06], mat=HOT, sides=6)

    # First lens block (rows 28-37).
    lib.box(bm, G.x(0), G.y(28), G.x(24), G.y(37), 0.0, 0.17, mat=GREY)
    lib.box(bm, G.x(0), G.y(36), G.x(3), G.y(37), 0.17, 0.19, mat=RIB)  # light lip at its lower left
    lib.box(bm, G.x(19.6), G.y(30.6), G.x(22), G.y(35.6), 0.12, 0.172, mat=RECESS)
    lens = (12.0, 32.4, 6.2, 3.7)

    def lens_at(c, r, rx, ry, z, body, core, hot, hot_at, bezel_mat):
        x, y = G.xy(c, r)
        # Bezel: a ring round the lens, then the lens bulging out of it.
        ring = []
        import math
        for k in range(17):
            a = 2 * math.pi * k / 16
            ring.append((x + (rx + 0.7) * PX * math.cos(a), y + (ry + 0.7) * PX * math.sin(a), z + 0.01))
        lib.tube(bm, ring, 0.75 * PX, mat=bezel_mat, sides=6, caps=False)
        lib.ellipsoid(bm, (x, y, z), (rx * PX, ry * PX, 0.075), mat=body, segments=16, rings=6, half=True)
        lib.ellipsoid(bm, (x - 0.6 * PX, y + 0.3 * PX, z), (rx * 0.62 * PX, ry * 0.6 * PX, 0.085), mat=core,
                      segments=12, rings=6, half=True)
        hx, hy = G.xy(*hot_at)
        lib.ellipsoid(bm, (hx, hy, z + 0.065), (1.6 * PX, 1.0 * PX, 0.025), mat=hot, segments=8, rings=4)

    lens_at(*lens, 0.17, LENS1, LENS1_CORE, HOT, (9.5, 31.8), BEZEL)

    # ---- second block (rows 39-46) ----
    lib.box(bm, G.x(0), G.y(39), G.x(18), G.y(46), 0.0, 0.15, mat=DGREY)
    lib.box(bm, G.x(18), G.y(39), G.x(24), G.y(46), 0.0, 0.09, mat=RECESS)
    lib.box(bm, G.x(20.6), G.y(39), G.x(22.6), G.y(43.5), 0.09, 0.13, mat=DGREY)
    for r in (41.5, 44.5):  # ribs across its left end
        lib.tube(bm, [(G.x(0.1), G.y(r), 0.15), (G.x(3.0), G.y(r), 0.15)], 0.55 * PX, mat=RIB, sides=6)
    lens_at(12.3, 42.5, 4.2, 2.6, 0.15, LENS2, LENS2_CORE, HOT, (10.8, 41.8), BEZEL)
    # Brown pipe: a thin feed down the right edge into the top of the big pipe.
    lib.tube(bm, [(G.x(23.4), G.y(40.6), 0.1), (G.x(23.2), G.y(43.8), 0.1)], 0.6 * PX, mat=PIPE, sides=6)
    lib.tube(bm, [(G.x(22.0), G.y(43.8), 0.1), (G.x(22.0), G.y(46.0), 0.1)], 2.0 * PX, mat=PIPE, sides=10,
             caps=True)

    # ---- third block (rows 48-56) ----
    lib.box(bm, G.x(0), G.y(48), G.x(20), G.y(56), 0.0, 0.08, mat=RECESS)
    lib.box(bm, G.x(0), G.y(48), G.x(16), G.y(52.5), 0.0, 0.15, mat=DGREY)
    lib.box(bm, G.x(0), G.y(52.5), G.x(9.5), G.y(56), 0.0, 0.15, mat=DGREY)
    for c in (1.5, 3.5):  # ribs down its left end
        lib.tube(bm, [(G.x(c), G.y(49.6), 0.15), (G.x(c), G.y(56.0), 0.15)], 0.55 * PX, mat=RIB, sides=6)
    lib.box(bm, G.x(17.8), G.y(48), G.x(18.8), G.y(56), 0.08, 0.11, mat=DGREY)
    lens_at(11.8, 50.2, 3.0, 1.7, 0.15, LENS3, LENS3_CORE, HOT, (11.0, 49.8), RIB)
    lib.tube(bm, [(G.x(22.0), G.y(48.0), 0.1), (G.x(22.0), G.y(56.0), 0.1)], 2.0 * PX, mat=PIPE, sides=10)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprites = {name: common.load_sprite(ROOT, name) for name, _, _ in PIECES}
    palette = {"name": NAME, "colors": {}}
    for s in sprites.values():
        palette["colors"].update(s["colors"])
    whole = build(palette)
    pieces = common.split_assembly(whole, PIECES)
    for name, _, _ in PIECES:
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", sprites[name]["sprites"])

    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        # The column in the middle of a 48 x 56 block (render_preview's size 4).
        placed = [(sprites[n]["frames"][0]["pixels"], sprites[n]["colors"], 24 + dx - 12, 28 + dy - 14)
                  for n, dx, dy in PIECES]
        ref = out.with_name(f"{out.stem}-sprite.png")
        lib.write_png(ref, lib.compose_pixels(placed, 48, 56, scale=6))
        common.render_preview([whole], str(out), ref, size=4, view_px=480)
        for name, _, _ in PIECES:
            img = ROOT / "reference" / "models" / name / sprites[name]["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.with_name(f"{name}.png")), img, size=2)
    if "--frames" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--frames") + 1])
        for name, _, _ in PIECES:
            common.render_frame_previews([pieces[name]], str(out / f"{name}.png"), sprites[name], ROOT)


if __name__ == "__main__":
    main()
