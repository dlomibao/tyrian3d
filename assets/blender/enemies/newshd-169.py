"""Wooden silo with an iris hatch (newshd.shp frames 169, 193-207): a 3D version of its sprites.

Seen in levels 1.5, 2.8 and 3.15. A round wooden tub of vertical planks with a light rim and a
band round it, standing on a cobbled stone slab that fills the tile. Its top is a pit closed by
four grey quarter-dome shutters that slide apart diagonally into the rim, uncovering a glowing
red-orange core; a little door low on its front wall slides up to show a red-lit window.

The frames are one open-and-shut cycle. The shutters and the door change shape, so each stage
gets its own model (the core's glow only changes brightness, so the glowing frames share one):
  newshd-169     169, 205, 207  open, door up, core and window glowing
  newshd-169-f2  193            shutters closed, door down
  newshd-169-f3  195            shutters a little apart
  newshd-169-f4  197            shutters half open
  newshd-169-f5  199            open, dark core, door down
  newshd-169-f6  201, 203       open, dark core, door half up

Run: blender --background --python assets/blender/enemies/newshd-169.py [-- --preview out.png]
(writes <out>.png for the first model and <name>-fN.png beside it for the others).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b075 as L  # noqa: E402

NAME = "newshd-169"
ROOT = common.repo_root(__file__)
P = L.PX

# (suffix, frames, shutter opening 0-1, door: "down" / "half" / "up", glowing)
STAGES = [
    ("", [169, 205, 207], 1.0, "up", True),
    ("-f2", [193], 0.0, "down", False),
    ("-f3", [195], 0.3, "down", False),
    ("-f4", [197], 0.6, "down", False),
    ("-f5", [199], 1.0, "down", False),
    ("-f6", [201, 203], 1.0, "half", False),
]

CX, CY = L.XE(11.5), L.YE(11.5)  # the tub's axis (pixel edges)
R_OUT, R_PIT = 9.5 * P, 6.6 * P  # outer wall and pit radius
Z_BASE, Z_TOP, Z_PIT = 0.08, 0.7, 0.34  # top of the stone slab, rim top, pit floor
SIDES = 28


def ring_solid(bm, r_in, r_out, z0, z1, mat, sides=SIDES):
    """A closed thick ring (a tube wall) round the tub's axis: smooth walls, flat top and bottom."""
    def ring(r, z):
        return [bm.verts.new((CX + r * math.cos(2 * math.pi * i / sides), CY + r * math.sin(2 * math.pi * i / sides), z))
                for i in range(sides)]
    ob, ot, ib, it = ring(r_out, z0), ring(r_out, z1), ring(r_in, z0), ring(r_in, z1)
    for i in range(sides):
        j = (i + 1) % sides
        for quad, smooth in (((ob[i], ob[j], ot[j], ot[i]), True), ((it[i], it[j], ib[j], ib[i]), True),
                             ((ot[i], ot[j], it[j], it[i]), False), ((ib[i], ib[j], ob[j], ob[i]), False)):
            f = bm.faces.new(quad)
            f.material_index = mat
            f.smooth = smooth


def shutter(bm, sx, sy, d, mat, R=6.2 * P, zb=0.56, hd=0.09, gap=0.35 * P, nr=4, na=6):
    """One quarter-dome shutter in quadrant (sx, sy), slid out along its diagonal by d."""
    before = set(bm.faces)
    off = gap + d / math.sqrt(2)
    def at(rho, th, z):
        return bm.verts.new((CX + sx * (rho * math.cos(th) + off), CY + sy * (rho * math.sin(th) + off), z))
    centre = at(0, 0, zb + hd)
    grid = [[at(R * i / nr, math.pi / 2 * j / na, zb + hd * (1 - (i / nr) ** 2)) for j in range(na + 1)]
            for i in range(1, nr + 1)]
    for j in range(na):
        bm.faces.new((centre, grid[0][j], grid[0][j + 1]))
    for i in range(nr - 1):
        for j in range(na):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    loop = [centre] + [grid[i][0] for i in range(nr)] + [grid[nr - 1][j] for j in range(1, na + 1)] \
        + [grid[i][na] for i in range(nr - 2, -1, -1)]
    low = [bm.verts.new((v.co.x, v.co.y, zb - 0.04)) for v in loop]
    n = len(loop)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((loop[i], low[i], low[j], loop[j]))
    bm.faces.new(list(reversed(low)))
    for f in set(bm.faces) - before:
        f.material_index = mat
        f.smooth = True


def build(sprite, name, opening, door, glow):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.0, roughness=0.9),  # 0 stone slab
        pal(8, metallic=0.0, roughness=0.85),  # 1 light cobbles
        pal(7, metallic=0.0, roughness=0.9),  # 2 mid cobbles
        pal(21, metallic=0.0, roughness=0.7),  # 3 wooden wall
        pal(22, metallic=0.0, roughness=0.6),  # 4 rim
        pal(18, metallic=0.0, roughness=0.8),  # 5 dark plank seams
        pal(26, metallic=0.1, roughness=0.5),  # 6 pale band
        pal(2, metallic=0.0, roughness=0.9),  # 7 dark pit, rails, window frame
        pal(9, metallic=0.6, roughness=0.35),  # 8 grey shutters
        pal(11, metallic=0.6, roughness=0.3),  # 9 bright guide blocks
        pal(121, emission_strength=5.0),  # 10 glowing core
        pal(127, emission_strength=6.0),  # 11 white-hot centre
        pal(118, emission_strength=3.5),  # 12 red window
        pal(113, metallic=0.0, roughness=0.8),  # 13 dark red unlit core
    ]
    SLAB, COB, DCOB, WOOD, RIM, SEAM, BAND, PIT, SHUT, GUIDE, CORE, WHITE, WINDOW, DULL = range(14)
    bm = bmesh.new()

    # Stone slab filling the tile, with a few cobbles raised round the tub.
    L.box(bm, 0, 0, 24, 28, 0.0, Z_BASE, mat=SLAB)
    cobbles = [(0, 0, 3, 3, COB), (19, 0, 24, 2, COB), (21, 2, 24, 7, DCOB), (21, 9, 24, 14, COB),
               (0, 4, 2, 9, DCOB), (0, 12, 2, 17, COB), (21, 16, 24, 21, DCOB), (0, 19, 3, 24, DCOB),
               (0, 24, 5, 28, COB), (6, 25, 12, 28, DCOB), (13, 25, 19, 28, DCOB), (19, 22, 24, 28, COB)]
    for c0, r0, c1, r1, m in cobbles:
        L.bevel_box(bm, L.XE(c0) + 0.2 * P, L.YE(r1) + 0.2 * P, L.XE(c1) - 0.2 * P, L.YE(r0) - 0.2 * P,
                    0.0, Z_BASE + 0.04, 0.02, mat=m)

    # The tub: wooden wall, a light rim round the top and a pale band low down.
    ring_solid(bm, R_PIT, R_OUT, Z_BASE, Z_TOP, WOOD)
    ring_solid(bm, R_PIT - 0.2 * P, R_OUT + 0.4 * P, Z_TOP - 0.04, Z_TOP + 0.03, RIM)
    ring_solid(bm, R_OUT - 0.2 * P, R_OUT + 0.35 * P, 0.2, 0.26, BAND)
    # Plank seams down the wall.
    for k in range(16):
        a = 2 * math.pi * (k + 0.5) / 16
        x, y = CX + (R_OUT + 0.1 * P) * math.cos(a), CY + (R_OUT + 0.1 * P) * math.sin(a)
        tx, ty = -math.sin(a) * 0.3 * P, math.cos(a) * 0.3 * P
        nx, ny = math.cos(a) * 0.3 * P, math.sin(a) * 0.3 * P
        L.prism(bm, [(x - tx - nx, y - ty - ny), (x + tx - nx, y + ty - ny), (x + tx + nx, y + ty + ny),
                     (x - tx + nx, y - ty + ny)], Z_BASE, Z_TOP - 0.04, mat=SEAM)
    # Pit floor and the X of rails across it.
    L.cylinder(bm, CX, CY, Z_BASE, Z_PIT, R_PIT + 0.1 * P, sides=SIDES, mat=PIT, smooth=False)
    for a in (math.pi / 4, 3 * math.pi / 4):
        dx, dy = math.cos(a) * R_PIT, math.sin(a) * R_PIT
        L.sweep(bm, [(CX - dx, CY - dy, Z_PIT + 0.03, 0.5 * P, 0.03), (CX + dx, CY + dy, Z_PIT + 0.03, 0.5 * P, 0.03)],
                sides=4, mat=PIT, smooth=False)
    # Bright guide blocks on the rim's inner edge at the four diagonals, where the shutters slide.
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        x, y = CX + (R_PIT + 0.6 * P) * math.cos(a), CY + (R_PIT + 0.6 * P) * math.sin(a)
        L.bevel_box(bm, x - 1.1 * P, y - 1.1 * P, x + 1.1 * P, y + 1.1 * P, Z_TOP - 0.1, Z_TOP + 0.06, 0.02, mat=GUIDE)

    # The core in the pit: glowing, or dark red when the light is off.
    if glow:
        L.ellipsoid(bm, CX, CY, Z_PIT, 3.6 * P, 3.6 * P, 0.14, mat=CORE, segments=14, rings=7, zmin=Z_PIT)
        L.ellipsoid(bm, CX, CY, Z_PIT + 0.08, 1.5 * P, 1.5 * P, 0.09, mat=WHITE, segments=10, rings=5)
    else:
        L.ellipsoid(bm, CX, CY, Z_PIT, 3.0 * P, 3.0 * P, 0.08, mat=DULL, segments=14, rings=7, zmin=Z_PIT)

    # The iris shutters (gone into the rim when fully open).
    if opening < 1.0:
        d = opening * 5.0 * P
        for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            shutter(bm, sx, sy, d, SHUT)

    # The window low on the front wall (sprite columns 8-13) and its sliding door.
    yf = CY - R_OUT
    x0, x1 = L.XE(8.0), L.XE(14.0)
    L.bevel_box(bm, x0 - 0.6 * P, yf - 0.5 * P, x1 + 0.6 * P, yf + 1.0 * P, Z_BASE, 0.4, 0.0, mat=PIT)
    L.prism(bm, [(x0, yf - 0.6 * P), (x1, yf - 0.6 * P), (x1, yf), (x0, yf)], 0.12, 0.34,
            mat=WINDOW if glow else PIT)
    door_bottom = {"down": 0.11, "half": 0.2, "up": None}[door]
    if door_bottom is not None:
        L.prism(bm, [(x0 + 0.2 * P, yf - 1.0 * P), (x1 - 0.2 * P, yf - 1.0 * P), (x1 - 0.2 * P, yf - 0.2 * P),
                     (x0 + 0.2 * P, yf - 0.2 * P)], door_bottom, 0.36, mat=WOOD)
        L.prism(bm, [(x0 + 1.0 * P, yf - 1.2 * P), (x0 + 1.6 * P, yf - 1.2 * P), (x0 + 1.6 * P, yf - 0.9 * P),
                     (x0 + 1.0 * P, yf - 0.9 * P)], door_bottom + 0.02, 0.34, mat=BAND)
    return L.to_object(name, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    out = L.preview_arg()
    for suffix, frames, opening, door, glow in STAGES:
        name = NAME + suffix
        obj = build(sprite, name, opening, door, glow)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", L.frames_subset(sprite, frames))
        if out:
            png = out if not suffix else out.parent / f"{name}.png"
            common.render_preview([obj], str(png), L.frame_image(ROOT, sprite, frames[0]), size=2)
            obj.hide_render = True


if __name__ == "__main__":
    main()
