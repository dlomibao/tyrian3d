"""Glass-domed city (newshr.shp, four 2x2 pieces: newshr-1, -3 top, newshr-39, -41 bottom): a 3D
version of its sprites, built whole and cut into the four pieces.

Seen in episode 3 (levels 3.4 and 3.19), always as a pair side by side. A dark blue glass dome
sits in a shallow crater in brown dirt; through the glass the blue-grey blocks of a city show,
lit from the upper left, with a white glint at the top left of the dome, a pale reflection along
its lower-right rim and one red light. The city blocks are plates that follow the dome's curve,
stepped up from the glass so they read as buildings under it. Each piece has one frame.

Run: blender --background --python assets/blender/enemies/assembly-newshr-39.py [-- --preview out.png]
(the preview is the whole dome; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b105 as lib  # noqa: E402

NAME = "assembly-newshr-39"
ROOT = common.repo_root(__file__)
W, H = 48, 56
G = lib.Grid(W, H)
# Piece centres relative to the block's centre, in screen px (sprite.json assemblyLayout:
# newshr-1 at (176, 66), -3 at (200, 66), -39 at (176, 94), -41 at (200, 94)).
PIECES = [("newshr-1", -12, -14), ("newshr-3", 12, -14), ("newshr-39", -12, 14), ("newshr-41", 12, 14)]

# The dome in pixel-edge coordinates: centre (25, 27.5), radii 19 x 18.5 px.
DOME_C, DOME_R = (25.0, 27.5), (19.0, 18.5)
DOME_H = 0.72
DIRT_TOP = 0.04


def whole_grid(sprites):
    return lib.compose_grid([(sprites[n]["frames"][0]["pixels"], W // 2 + dx - 12, H // 2 + dy - 14)
                             for n, dx, dy in PIECES], W, H)


def build(palette, grid):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(palette, i, "nshr39", **kw)  # noqa: E731
    mats = [
        pal(17, metallic=0.0, roughness=0.95),  # 0 dirt
        pal(19, metallic=0.0, roughness=0.9),  # 1 lighter clods
        pal(20, metallic=0.0, roughness=0.9),  # 2 lightest clod tops
        pal(161, metallic=0.0, roughness=0.95),  # 3 dark crater rim
        pal(100, metallic=0.35, roughness=0.15),  # 4 dark blue glass
        pal(101, metallic=0.5, roughness=0.35),  # 5 city block
        pal(102, metallic=0.5, roughness=0.35),  # 6 lighter block
        pal(103, metallic=0.5, roughness=0.3),  # 7 lit block
        pal(105, metallic=0.5, roughness=0.3),  # 8 brightest block faces
        pal(58, metallic=0.5, roughness=0.3),  # 9 blue-lit facades
        pal(129, metallic=0.5, roughness=0.3),  # 10 blue trim
        pal(95, metallic=0.2, roughness=0.1, emission_strength=1.5),  # 11 white glint
        pal(109, metallic=0.3, roughness=0.1, emission_strength=1.0),  # 12 rim reflection
        pal(67, emission_strength=4.0),  # 13 red light
        pal(100, metallic=0.5, roughness=0.3),  # 14 low dark structures
        pal(18, metallic=0.0, roughness=0.95),  # 15 mid dirt clods
    ]
    DIRT, CLOD, CLOD2, RIM, GLASS, B1, B2, B3, B5, BLUE, TRIM, GLINT, REFL, RED, LOW, MID = range(16)
    bm = bmesh.new()

    # Dirt: a dark slab under the whole block, cobbled with lumps: every patch of the lighter dirt
    # colours (bounded by the darkest ones) outside the crater is one lump, coloured by its mean.
    lib.box(bm, G.x(0), G.y(0), G.x(W), G.y(H), 0.0, DIRT_TOP, mat=DIRT)

    cx, cy = G.xy(*DOME_C)
    rx, ry = DOME_R[0] / 12, DOME_R[1] / 12

    def outside(c, r, k):
        u = ((c + 0.5 - DOME_C[0]) / (DOME_R[0] + 2.5)) ** 2 + ((r + 0.5 - DOME_C[1]) / (DOME_R[1] + 2.5)) ** 2
        return u > 1.0

    for comp in lib.components(grid, lambda c, r, k: k in (18, 19, 20) and outside(c, r, k)):
        if len(comp) < 2:
            continue
        cs = [c for c, _ in comp]
        rs = [r for _, r in comp]
        mc, mr = sum(cs) / len(cs) + 0.5, sum(rs) / len(rs) + 0.5
        ex = (max(cs) - min(cs) + 1) / 2 + 0.4
        ey = (max(rs) - min(rs) + 1) / 2 + 0.4
        mean = sum(grid[r][c] for c, r in comp) / len(comp)
        mat = CLOD2 if mean >= 18.7 else CLOD if mean >= 18.0 else MID
        hz = 0.015 + 0.004 * min(len(comp), 10)
        lib.ellipsoid(bm, (G.x(mc), G.y(mr), DIRT_TOP - 0.01), (ex / 12, ey / 12, hz),
                      mat=mat, segments=7, rings=4, half=True)

    # Crater: a low dark berm round the dome.
    lib.ellipsoid(bm, (cx + 0.02, cy - 0.02, 0.0), (rx + 2.6 / 12, ry + 2.6 / 12, 0.1), mat=RIM,
                  segments=32, rings=6, half=True)

    # The glass dome.
    dome = lib.Dome(cx, cy, rx, ry, DOME_H, z0=0.0)
    dome.build(bm, mat=GLASS, segments=32, rings=16)

    # City blocks under the glass (pixel-edge rectangles: col0, row0, col1, row1, lift, top, side).
    blocks = [
        (12, 11, 23, 21, 0.04, B2, B1),  # big block at the upper left
        (14, 13, 22, 20, 0.1, B3, BLUE),  # its lit upper storey (the glint sits on it)
        (16, 15, 21, 19, 0.13, B5, B3),
        (22, 14, 26, 18, 0.09, BLUE, TRIM),  # blue-lit tower
        (22, 18, 26, 21, 0.06, B2, B1),
        (27, 21, 32, 27, 0.06, B2, BLUE),  # block right of the centre
        (28, 21, 32, 22, 0.09, TRIM, TRIM),  # its blue cornice
        (31, 22, 32, 26, 0.09, BLUE, BLUE),
        (12, 25, 14, 31, 0.06, B3, BLUE),  # narrow block at the left
        (15, 21, 18, 27, 0.1, B3, BLUE),  # tall block in the middle
        (18, 22, 22, 25, 0.08, B5, B3),
        (19, 26, 23, 30, 0.06, B2, BLUE),
        (25, 30, 36, 34, 0.03, LOW, B1),  # low works below the centre
        (32, 33, 35, 34, 0.05, B2, B1),
        (17, 36, 24, 40, 0.03, B1, LOW),  # low block at the bottom
        (8, 14, 12, 20, 0.02, LOW, LOW),
    ]
    for c0, r0, c1, r1, lift, top, side in blocks:
        lib.drape(bm, dome, G.x(c0), G.y(r1), G.x(c1), G.y(r0), lift, mat=top, n=3, side_mat=side)

    # White glint at the upper left of the dome.
    gx, gy = G.xy(19.0, 17.5)
    lib.ellipsoid(bm, (gx, gy, dome.z(gx, gy) + 0.14), (3.0 / 12, 2.8 / 12, 0.025), mat=GLINT,
                  segments=12, rings=6)
    # Pale reflection along the lower-right rim.
    path = [(42.6, 27.5), (42.2, 31.5), (41.2, 35.0), (39.3, 37.8), (36.8, 40.2), (34.3, 42.0), (32.5, 43.0)]
    pts = []
    for c, r in path:
        x, y = G.xy(c, r)
        # Pull the path slightly inside the outline so it rides on the glass.
        dx, dy = x - cx, y - cy
        x, y = cx + dx * 0.93, cy + dy * 0.93
        pts.append((x, y, dome.z(x, y) + 0.01))
    lib.tube(bm, pts, [0.03, 0.05, 0.06, 0.06, 0.055, 0.045, 0.025], mat=REFL, sides=6)
    # Red light on the low works.
    lx, ly = G.xy(29.5, 32.5)
    lib.ellipsoid(bm, (lx, ly, dome.z(lx, ly) + 0.03), (0.6 / 12, 0.6 / 12, 0.03), mat=RED, segments=8, rings=4)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprites = {name: common.load_sprite(ROOT, name) for name, _, _ in PIECES}
    palette = {"name": NAME, "colors": {}}
    for s in sprites.values():
        palette["colors"].update(s["colors"])
    grid = whole_grid(sprites)
    whole = build(palette, grid)
    pieces = common.split_assembly(whole, PIECES)
    for name, _, _ in PIECES:
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", sprites[name]["sprites"])

    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        placed = [(sprites[n]["frames"][0]["pixels"], sprites[n]["colors"], W // 2 + dx - 12, H // 2 + dy - 14)
                  for n, dx, dy in PIECES]
        ref = out.with_name(f"{out.stem}-sprite.png")
        lib.write_png(ref, lib.compose_pixels(placed, W, H, scale=6))
        common.render_preview([whole], str(out), ref, size=4, view_px=480)
        for name, _, _ in PIECES:
            img = ROOT / "reference" / "models" / name / sprites[name]["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.with_name(f"{name}.png")), img, size=2)


if __name__ == "__main__":
    main()
