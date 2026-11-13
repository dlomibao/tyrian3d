"""Eye hatch (newsh5.shp frames 160, 162, 164): a 3D version of its sprites.

Seen in episode 4 (4.15 BRAINIAC) set into the ground, terrain-fixed. It fills its whole tile: a purple stone
block, octagonal with arms running out to the tile's edges (seams down their middles), on a dark
teal floor. In its middle is a round pit, and in the pit a glowing red eye that two shutters slide
over: a narrow one down from the top and a wider one up from the bottom. The frames close the
shutters (open, half shut, shut), so each frame gets its own model: newsh5-160, newsh5-160-f2,
newsh5-160-f3.

Run: blender --background --python assets/blender/enemies/newsh5-160.py -- [--review DIR] [--no-export]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b068 as L  # noqa: E402

common = L.common
NAME = "newsh5-160"
ROOT = common.repo_root(__file__)

# The block's outline in pixel edges (column, row): an octagon whose four arms reach the tile edges.
BLOCK = [(7, 0), (17, 0), (17, 1.5), (22.5, 7), (24, 7), (24, 21), (22.5, 21), (17, 26.5), (17, 28),
         (7, 28), (7, 26.5), (1.5, 21), (0, 21), (0, 7), (1.5, 7), (7, 1.5)]
PIT = (12.0, 13.5, 9.0, 9.5)  # pit centre (pixel edges) and radii (px)
# Per frame: the row of the top shutter's lit lip and of the bottom shutter's lit lip.
SHUTTERS = {160: (7, 18), 162: (9, 16), 164: (11, 14)}

TOP_Z = 0.2  # top of the block
FLOOR_Z = 0.07  # floor of the pit


def build(sprite, frame, tag):
    coll = common.reset_collection(tag)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(102, metallic=0.1, roughness=0.8),  # 0 teal floor
        pal(86, metallic=0.15, roughness=0.6),  # 1 purple stone
        pal(88, metallic=0.15, roughness=0.55),  # 2 lit bevel
        pal(83, metallic=0.1, roughness=0.7),  # 3 dark pit wall
        pal(81, metallic=0.1, roughness=0.8),  # 4 pit floor
        pal(82, metallic=0.45, roughness=0.42),  # 5 seams, bottom shutter (machined)
        pal(84, metallic=0.5, roughness=0.4),  # 6 top shutter (machined)
        pal(87, metallic=0.55, roughness=0.35),  # 7 shutter lips
        pal(119, metallic=1.0, roughness=0.55, emission_strength=3.0),  # 8 lens, open (median 119)
        pal(116, metallic=1.0, roughness=0.6, emission_strength=2.0),  # 9 lens, half shut (median 116)
        pal(114, metallic=1.0, roughness=0.65, emission_strength=1.0),  # 10 lens, shut (dull)
        pal(113, metallic=0.6, roughness=0.45),  # 11 bezel ring (the eye's dark rim)
    ]
    FLOOR, STONE, BEVEL, WALL, PITF, SEAM, TOPSH, LIP, OPEN, HALF, SHUT, RIM = range(12)
    EYES = {160: OPEN, 162: HALF, 164: SHUT}
    top_lip, bottom_lip = SHUTTERS[frame["index"]]
    ex, ey = L.EX, L.EY
    bm = bmesh.new()

    # Floor: the whole tile.
    L.box(bm, ex(0), ey(28), ex(24), ey(0), 0.0, 0.03, mat=FLOOR)

    # The block with a bevelled top edge and the pit sunk into it.
    cx, cy, rx, ry = ex(PIT[0]), ey(PIT[1]), PIT[2] * L.PX, PIT[3] * L.PX
    outer = L.resample([(ex(c), ey(r)) for c, r in BLOCK], 1.6 * L.PX)
    loops = [
        L.at_z(outer, 0.03),
        L.at_z(outer, TOP_Z - 0.03),
        L.at_z(L.pull(outer, cx, cy, 0.7 * L.PX), TOP_Z),
        L.at_z(L.toward_ellipse(outer, cx, cy, rx, ry), TOP_Z),
        L.at_z(L.toward_ellipse(outer, cx, cy, rx, ry, 0.9), TOP_Z - 0.04),
        L.at_z(L.toward_ellipse(outer, cx, cy, rx, ry, 0.62), FLOOR_Z),
    ]
    L.terraces(bm, loops, [STONE, BEVEL, STONE, WALL, WALL], cap_bottom=STONE, cap_top=PITF)

    # Seams down the middle of each arm.
    s = 0.004
    L.box(bm, ex(11.2), ey(4.6), ex(12.0), ey(0), TOP_Z - s, TOP_Z + s, mat=SEAM)
    L.box(bm, ex(11.2), ey(28), ex(12.0), ey(22.8), TOP_Z - s, TOP_Z + s, mat=SEAM)
    L.box(bm, ex(0), ey(14), ex(3.4), ey(13.2), TOP_Z - s, TOP_Z + s, mat=SEAM)
    L.box(bm, ex(20.7), ey(14), ex(24), ey(13.2), TOP_Z - s, TOP_Z + s, mat=SEAM)

    # The eye: ONE glowing lens dome (D126/D173: metallic 1, rough), seated in a machined bezel ring.
    # The sprite's yellow core and orange rim are the glow's gradient (lighting), not separate parts;
    # it dims as the shutters close (frame 162 dull red, frame 164 a faint glow).
    ecx, ecy = ex(12.0), ey(13.0)
    P = L.PX

    def ring(rx, ry, z, n=32):
        return [(ecx + rx * P * math.cos(2 * math.pi * (k + 0.5) / n), ecy + ry * P * math.sin(2 * math.pi * (k + 0.5) / n), z)
                for k in range(n)]

    L.terraces(bm, [ring(5.3, 4.0, FLOOR_Z - 0.01), ring(5.15, 3.85, FLOOR_Z + 0.03), ring(4.85, 3.55, FLOOR_Z + 0.042),
                    ring(4.45, 3.15, FLOOR_Z + 0.03), ring(4.3, 3.0, FLOOR_Z - 0.01)],
               [RIM, RIM, RIM, RIM], cap_bottom=None, cap_top=None)
    L.ellipsoid(bm, (ecx, ecy, FLOOR_Z - 0.005), (4.4 * P, 3.1 * P, 0.07), mat=EYES[frame["index"]],
                segments=32, rings=12)

    # Shutters: machined slide plates, chamfered all round, a raised leading lip, panel lines; each
    # runs in a pair of guide rails along the pit wall.
    def strip(x0, x1, y0, y1, z, mat):
        L.box(bm, ex(x0), ey(y1), ex(x1), ey(y0), z - 0.006, z + 0.0035, mat=mat)

    ch = 0.35 * P
    # Top shutter: slides down from the pit's top edge; lit lip on row `top_lip`.
    z0, z1 = FLOOR_Z + 0.075, 0.172
    L.chamfer_box(bm, ex(10.0), ex(14.0), ey(top_lip + 0.2), ey(3.6), z0, z1, ch, TOPSH)
    L.chamfer_box(bm, ex(9.85), ex(14.15), ey(top_lip + 1.0), ey(top_lip), z0, z1 + 0.012, ch, LIP)
    strip(11.8, 12.2, 3.9, top_lip - 0.15, z1, SEAM)  # centre panel line
    if top_lip - 3.6 > 2.5:
        strip(10.35, 13.65, (3.6 + top_lip) / 2 - 0.2, (3.6 + top_lip) / 2 + 0.2, z1, SEAM)
    for x0 in (9.25, 14.15):  # guide rails
        L.chamfer_box(bm, ex(x0), ex(x0 + 0.6), ey(8.6), ey(3.8), FLOOR_Z + 0.03, z0 + 0.03, 0.15 * P, WALL)
    # Bottom shutter: a wider plate sliding up; lit lip on row `bottom_lip`.
    z0, z1 = FLOOR_Z + 0.07, 0.16
    L.chamfer_box(bm, ex(9.0), ex(15.0), ey(23.4), ey(bottom_lip + 0.8), z0, z1, ch, SEAM)
    L.chamfer_box(bm, ex(8.85), ex(15.15), ey(bottom_lip + 1.0), ey(bottom_lip), z0, z1 + 0.012, ch, LIP)
    strip(11.8, 12.2, bottom_lip + 1.2, 23.1, z1, PITF)
    r = bottom_lip + 2.6
    while r < 22.8:  # cross panel lines every 2.4 rows
        strip(9.35, 14.65, r - 0.2, r + 0.2, z1, PITF)
        r += 2.4
    for x0 in (8.25, 15.15):
        L.chamfer_box(bm, ex(x0), ex(x0 + 0.6), ey(23.2), ey(18.6), FLOOR_Z + 0.03, z0 + 0.03, 0.15 * P, WALL)

    return L.to_object(tag, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    models = []
    for i, frame in enumerate(sprite["frames"]):
        tag = NAME if i == 0 else f"{NAME}-f{i + 1}"
        models.append((build(sprite, frame, tag), [frame["index"]]))
    # The hatch fills its whole tile and its sprite draws no ink ring, so no outline shell (D8, D86).
    L.export_frames(ROOT, NAME, sprite, models, outline=False)


if __name__ == "__main__":
    main()
