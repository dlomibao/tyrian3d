"""Spiked mine (newsha.shp, assembly of 6 pieces): a 3D version of its sprites.

Seen in episode 3 (levels 3.2 and 3.25). Six 2x2 ground enemies side by side (newsha-77, 79, 81
on top, 115, 117, 119 below; sprite.json `assemblyLayout`) make one 72x56 px object: a big
polished steel ball with long chrome spikes pointing up, down, left and right out of brass
collars, four thin spikes on the diagonals, and a fifth spike pointing straight up out of an
octagonal brass collar on its crown. The ring above it (newsha-125) is a separate enemy.

The ball sits on the ground (base at z = 0), squashed a little so it stays low; the spikes stick
out of its equator. The whole mine is built once in assembly coordinates and cut into the six
pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsha-115.py [-- --preview out.png]
(the preview is the whole mine; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b113 as lib  # noqa: E402

NAME = "assembly-newsha-115"
ROOT = common.repo_root(__file__)
PIECES = ["newsha-77", "newsha-79", "newsha-81", "newsha-115", "newsha-117", "newsha-119"]
# Assembly grid: 72 x 56 px, its top-left corner at screen (210, 29) (newsha-77's corner); its
# centre, screen (246, 57), is the Blender origin.
CX0, CY0 = 246, 57
PX = lib.PX


def X(c):
    """Assembly grid x (continuous: pixel column c spans c..c+1) to Blender X."""
    return (c - 36) / 12


def Y(r):
    """Assembly grid y (continuous) to Blender Y: sprite up is +Y."""
    return (28 - r) / 12


# The ball: centre at grid (36.5, 28.5), 15.5 px radius.
BX, BY = X(36.5), Y(28.5)
R = 15.5 * PX
RZ = 0.72  # half its height: squashed a little so the mine stays low
ZC = RZ  # its equator, where the spikes come out


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsha115"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(11, metallic=0.75, roughness=0.25),  # 0 steel ball
        pal(12, metallic=0.85, roughness=0.15),  # 1 chrome spikes
        pal(170, metallic=0.6, roughness=0.35),  # 2 brass collars
        pal(9, metallic=0.75, roughness=0.3),  # 3 thin diagonal spikes
        pal(13, metallic=0.85, roughness=0.15),  # 4 bright tip of the top spike
    ]
    BALL, SPIKE, BRASS, THIN, TIP = range(5)
    bm = bmesh.new()

    lib.ellipsoid(bm, (BX, BY, ZC), R, R, RZ, mat=BALL, segments=32, rings=16)

    origin = (BX, BY, ZC)
    # Big spikes up, down, left and right (27 px from the centre to the tip) in brass collars.
    for dx, dy in ((0, 1), (0, -1), (-1, 0), (1, 0)):
        d = (dx, dy, 0)
        lib.tube(bm, origin, d, [(s * PX, w * PX, w * PX) for s, w in
                                 ((13.0, 2.6), (17.0, 2.6), (20.5, 2.2), (23.0, 1.4), (25.5, 0.6), (27.0, 0.0))],
                 sides=10, mat=SPIKE)
        lib.tube(bm, origin, d, [(13.0 * PX, 4.0 * PX, 4.0 * PX), (14.6 * PX, 4.2 * PX, 4.2 * PX),
                                 (16.4 * PX, 4.2 * PX, 4.2 * PX), (16.9 * PX, 3.6 * PX, 3.6 * PX)],
                 sides=12, mat=BRASS)
    # Thin spikes on the diagonals (22 px to the tip).
    for dx, dy in ((-1, 1), (1, 1), (-1, -1), (1, -1)):
        d = (dx, dy, 0)
        lib.tube(bm, origin, d, [(s * PX, w * PX, w * PX) for s, w in
                                 ((13.0, 1.4), (16.0, 1.3), (19.5, 0.7), (22.0, 0.0))],
                 sides=8, mat=THIN)

    # The spike on top: an octagonal brass collar (grid 32-42 x 24-34) with a chrome cone in it.
    tx, ty = X(37.0), Y(29.0)
    top = ZC + RZ * math.sqrt(max(0.0, 1 - ((tx - BX) ** 2 + (ty - BY) ** 2) / R ** 2))
    lib.tube(bm, (tx, ty, top - 0.14), (0, 0, 1),
             [(0.0, 5.0 * PX, 5.0 * PX), (0.2, 5.0 * PX, 5.0 * PX), (0.23, 4.3 * PX, 4.3 * PX)],
             sides=8, mat=BRASS, smooth=False)
    lib.tube(bm, (tx, ty, top + 0.05), (0, 0, 1),
             [(0.0, 3.3 * PX, 3.3 * PX), (0.1, 2.8 * PX, 2.8 * PX), (0.2, 1.6 * PX, 1.6 * PX)],
             sides=10, mat=SPIKE)
    lib.tube(bm, (tx, ty, top + 0.25), (0, 0, 1),
             [(0.0, 1.6 * PX, 1.6 * PX), (0.08, 0.8 * PX, 0.8 * PX), (0.14, 0.0, 0.0)],
             sides=10, mat=TIP, cap_start=False)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, "newsha-115", PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = lib.composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 6)
        common.render_preview([obj], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
