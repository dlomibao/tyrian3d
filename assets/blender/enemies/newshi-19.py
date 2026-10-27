"""Ring with a blade (newshi.shp frames 19, 38, 57, 76, 95): a 3D version of its sprite.

Seen in episode 1 (level sections 10, 29 and 38) and level 3.21, on the ground. A round
rust-red ring, lit from the upper right, with a hole through its middle (the ground shows
through) and a curved crescent blade hugging the inside of the ring at the upper right. The
five frames are the same shape getting brighter (dark brown to pale pink), so one model covers
them all; it takes its palette indices from the middle frame (newshi-57) and each material steps
through the other frames' shades (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshi-19.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b069 as lib  # noqa: E402

NAME = "newshi-19"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12

# The ring's centre is the middle of the 12x14 tile (between columns 5 and 6, rows 6 and 7).
R_TUBE = 4.55 * PX  # radius of the ring's tube centre line
W_TUBE = 1.55 * PX  # tube half width (outer edge at 6.1 px, hole edge at 3.0 px)
H_TUBE = 0.11  # tube half height
Z_TUBE = H_TUBE  # sits on the ground


def build(sprite):
    coll = common.reset_collection(NAME)
    # Each part takes its colour from the middle frame (57) and steps through the others' shades:
    # {sprite frame: palette index}, read off the same pixels of every frame.
    pal = lambda i, part, frames, **kw: common.palette_material(  # noqa: E731
        sprite, i, f"{NAME}-{part}", frames=frames, **kw)
    lit = {19: 69, 38: 72, 76: 77, 95: 31}
    mats = [
        pal(72, "ring", {19: 67, 38: 69, 76: 74, 95: 77}, metallic=0.35, roughness=0.4),  # 0 ring
        pal(74, "lit", lit, metallic=0.35, roughness=0.35),  # 1 lit upper-right of the ring
        pal(69, "shade", {19: 66, 38: 67, 76: 72, 95: 74}, metallic=0.3, roughness=0.5),  # 2 shaded lower-left
        pal(2, "inner", {19: 32, 38: 1, 76: 3, 95: 3}, metallic=0.2, roughness=0.7),  # 3 dark inner wall of the hole
        pal(74, "lit", lit, metallic=0.4, roughness=0.3),  # 4 blade (the same material as 1)
        pal(76, "edge", {19: 70, 38: 74, 76: 78, 95: 31}, metallic=0.4, roughness=0.25),  # 5 blade's bright edge
    ]
    RING, LIT, SHADE, INNER, BLADE, EDGE = range(6)
    bm = bmesh.new()

    # The ring: a torus whose faces take the sprite's shading (lit towards the upper right).
    segs, sides = 28, 10
    rings = []
    for i in range(segs):
        th = 2 * math.pi * i / segs
        ring = []
        for k in range(sides):
            ph = 2 * math.pi * k / sides
            r = R_TUBE + W_TUBE * math.cos(ph)
            ring.append(bm.verts.new((r * math.cos(th), r * math.sin(th), Z_TUBE + H_TUBE * math.sin(ph))))
        rings.append(ring)
    for i in range(segs):
        i2 = (i + 1) % segs
        th = 2 * math.pi * (i + 0.5) / segs
        light = math.cos(th - math.radians(55))
        for k in range(sides):
            k2 = (k + 1) % sides
            ph = 2 * math.pi * (k + 0.5) / sides
            f = bm.faces.new((rings[i][k], rings[i2][k], rings[i2][k2], rings[i][k2]))
            f.smooth = True
            if math.cos(ph) < -0.35:
                f.material_index = INNER
            elif math.sin(ph) > 0.75:
                f.material_index = LIT if light > 0.55 else RING
            elif light > 0.3:
                f.material_index = LIT
            elif light < -0.45:
                f.material_index = SHADE
            else:
                f.material_index = RING

    # The crescent blade inside the ring's upper right, from its tip at the upper left of the
    # hole (column 4, row 4) round to its tail at the lower right (column 7, row 9).
    # (angle deg about the centre, radius px of its centre line, half width px, top z)
    blade = [(134, 3.0, 0.0, 0.12), (118, 2.8, 0.6, 0.18), (94, 2.5, 1.0, 0.23),
             (68, 2.3, 1.3, 0.26), (42, 2.3, 1.35, 0.26), (18, 2.55, 1.05, 0.22),
             (-8, 2.8, 0.75, 0.18), (-34, 3.0, 0.5, 0.14), (-60, 3.15, 0.0, 0.11)]
    path = []
    for a, r, w, z in blade:
        a = math.radians(a)
        h = z / 2
        path.append((r * PX * math.cos(a), r * PX * math.sin(a), h, w * PX, h))
    lib.sweep(bm, path, sides=8, mat=BLADE)
    # Its bright edge along the top.
    ridge = []
    for a, r, w, z in blade[1:-1]:
        a = math.radians(a)
        ridge.append((r * PX * math.cos(a), r * PX * math.sin(a), z - 0.005, max(w - 0.6, 0.25) * PX, 0.012))
    lib.sweep(bm, ridge, sides=6, mat=EDGE)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][2]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])
    if "--frames" in sys.argv:
        common.render_frame_previews([obj], sys.argv[sys.argv.index("--frames") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
