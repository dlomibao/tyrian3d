"""Horned head (newshh.shp frames 197, 199, 201, an assembly of 3 pieces): a 3D version of its
sprites.

Seen in episode 2 (level 2.2), above the green gunship (newshj-245 and newshj-283, which are
their own models). Three 2x2 enemies side by side make one 72x28 px object (sprite.json
`assemblyLayout`): in the middle (newshh-199) a grey head with a broad brow, two glowing red
eyes, a green skull emblem and a long grey beak pointing down, flanked by small green fangs; on
each side (newshh-197 left, newshh-201 right) a green prong and a long grey horn sweeping down
and inward from above.

The object is mirror symmetric about the centre of the middle piece's pixel column 12. It is
built once in assembly coordinates (the middle piece's centre is the origin; assembly column A
is the middle piece's column, so the left piece's columns are A + 24 and the right piece's A - 24),
then cut into the three pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshh-197.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b018 as lib  # noqa: E402
from lib_b018 import px, row  # noqa: E402

NAME = "assembly-newshh-197"
ROOT = common.repo_root(__file__)
PIECES = ["newshh-197", "newshh-199", "newshh-201"]
CX0, CY0 = 234, 68  # the middle piece's centre in screen pixels
AXIS = px(12)  # the mirror axis, assembly column 12


def merged_sprite():
    """newshh-197's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshh-197")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshh197"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(103, metallic=0.55, roughness=0.4),  # 0 grey head
        pal(99, metallic=0.5, roughness=0.55),  # 1 dark underside and vents
        pal(108, metallic=0.6, roughness=0.3),  # 2 pale beak ridge
        pal(106, metallic=0.6, roughness=0.3),  # 3 grey horns
        pal(40, metallic=0.3, roughness=0.45),  # 4 green prongs and fangs
        pal(44, metallic=0.3, roughness=0.35),  # 5 green skull
        pal(46, metallic=0.3, roughness=0.3),  # 6 pale skull highlights
        pal(115, metallic=0.3, roughness=0.4),  # 7 dark red eye sockets
        pal(120, metallic=0.1, roughness=0.3, emission_strength=4.0),  # 8 glowing red eyes
    ]
    HEAD, DARK, RIDGE, HORN, PRONG, SKULL, PALE, SOCKET, EYE = range(9)
    head_px = common.load_sprite(ROOT, "newshh-199")["frames"][0]["pixels"]
    horn_px = common.load_sprite(ROOT, "newshh-197")["frames"][0]["pixels"]
    bm = bmesh.new()

    # The head (middle piece): its brow fills the full width at rows 0-4 (and a column more on
    # each side), then the body narrows to the beak's point at row 26. Leaves out the fangs.
    keep = lambda r, c, v: v not in (-1, 1, 96, 97) and (r <= 4 or 3 <= c <= 20)  # noqa: E731
    raw = lib.row_spans(head_px, keep, range(0, 27), inset=-0.3)
    # Smooth the stair-stepped widths (the sprite's sides are curves), keeping the beak's point.
    spans = {r: (AXIS, (raw.get(r - 1, raw[r])[1] + 2 * raw[r][1] + raw.get(r + 1, raw[r])[1]) / 4)
             for r in raw}
    spans[0] = spans[1] = (AXIS, 13.3 / 12)
    spans[2] = (AXIS, 13.0 / 12)
    spans[3] = (AXIS, 12.6 / 12)
    spans[4] = (AXIS, 12.0 / 12)
    H = 0.26

    def height(r):
        return H * min(1.0, (spans[r][1] / (8 / 12))) ** 0.6

    rings = [lib.section_ring(AXIS, row(-0.8), 13.3 / 12, -0.02, H * 0.95, 0.16, sides=16, keel=2.0)]
    for r in sorted(spans):
        hw = spans[r][1]
        rings.append(lib.section_ring(AXIS, row(r), hw, -0.02, height(r), 0.16 * min(1.0, hw / (8 / 12)),
                                      sides=16, keel=1.4 if r > 10 else 2.2))
    rings.append([(AXIS, row(26.6), -0.03)])
    lib.ring_loft(bm, rings, mat=HEAD)

    # The pale ridge down the beak (columns 10-12, rows 12-25), a little left of the axis like
    # the sprite's lit side.
    ridge = [(px(11.3), row(r), -0.02 + height(r) - 0.01) for r in (12, 14, 16, 18, 20, 22, 24)]
    ridge.append((px(11.8), row(25.6), -0.02))
    lib.tube(bm, ridge, [0.1, 0.13, 0.13, 0.12, 0.1, 0.08, 0.05, 0.0], sides=8, mat=RIDGE, flat=0.35)

    # The green skull emblem (columns 9-13, rows 3-8) and its jaw (rows 10-12).
    lib.dome(bm, (px(11), row(5.6), height(5) - 0.06), (2.7 / 12, 3.2 / 12, 0.12), mat=SKULL, segments=14,
             rings=4)
    lib.ellipsoid(bm, (px(10.5), row(6.3), height(6) + 0.04), (0.035, 0.035, 0.02), mat=PALE, segments=8, rings=4)
    lib.ellipsoid(bm, (px(11.5), row(5.2), height(5) + 0.05), (0.035, 0.035, 0.02), mat=PALE, segments=8, rings=4)
    lib.ellipsoid(bm, (px(11.3), row(10.5), height(10) - 0.01), (2.0 / 12, 0.9 / 12, 0.04), mat=SKULL,
                  segments=10, rings=4)

    # Mirrored parts (built on the left, mirrored about the axis).
    v0, f0 = len(bm.verts), len(bm.faces)
    # A red eye at the top of the brow (columns 4-6, rows 0-1) in a dark red socket.
    lib.ellipsoid(bm, (px(5), row(0.6), height(1) - 0.04), (1.8 / 12, 1.3 / 12, 0.07), mat=SOCKET, segments=10,
                  rings=5)
    lib.ellipsoid(bm, (px(5.3), row(0.9), height(1) + 0.0), (1.1 / 12, 0.8 / 12, 0.05), mat=EYE, segments=10,
                  rings=5)
    # A vent on the cheek (column 6-7, rows 13-14).
    lib.ellipsoid(bm, (px(6.6), row(13.6), height(13) * 0.55), (0.06, 0.08, 0.04), mat=DARK, segments=8, rings=4)
    # The fang beside the head (columns 1-2, rows 5-10).
    lib.tube(bm, [(px(2.0), row(4.0), 0.06), (px(1.8), row(6.0), 0.05), (px(1.6), row(8.5), 0.03),
                  (px(1.5), row(10.8), 0.0)], [0.1, 0.1, 0.075, 0.0], sides=8, mat=PRONG, flat=0.8)
    # The outer green prong (left piece's columns 19-22, rows 0-9): from above the top edge down
    # and outward.
    lib.tube(bm, [(px(-1.4), row(-1.5), 0.05), (px(-2.3), row(1.5), 0.05), (px(-3.3), row(4.0), 0.04),
                  (px(-4.6), row(6.5), 0.02), (px(-5.0), row(9.4), 0.0)], [0.09, 0.09, 0.08, 0.06, 0.0],
             sides=8, mat=PRONG, flat=0.8)
    # The long horn (left piece's columns 3-15, rows 0-18), sweeping down and inward from above.
    horn = []
    for r in range(0, 18):
        cols = [c - 24 for c, v in enumerate(horn_px[r][:16]) if 100 <= v <= 110]
        horn.append((r, (min(cols) + max(cols)) / 2, (max(cols) - min(cols) + 1) / 2 + 0.3))
    # Its width tapers evenly from 2.8 px at the top to the point (the sprite's rows step).
    path = [(px(horn[0][1]), row(-1.5), 0.08)] + [(px(c), row(r), 0.08 - 0.004 * r) for r, c, _ in horn[::2]]
    path.append((px(-10.4), row(18.3), 0.0))
    radii = [2.9 / 12] + [(2.8 - 1.7 * r / 16) / 12 for r, _, _ in horn[::2]] + [0.0]
    lib.tube(bm, path, radii, sides=10, mat=HORN, flat=0.85)
    lib.mirror_new(bm, v0, f0, axis_x=AXIS)

    return lib.to_object(NAME, bm, mats, coll)


def composite_png(out):
    """The three pieces' sprites side by side as one 72x28 image."""
    import numpy as np
    img = np.zeros((28, 72, 4), dtype=np.float32)
    for i, name in enumerate(PIECES):
        data = common.load_sprite(ROOT, name)
        for r, line in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(line):
                if v >= 0:
                    img[r, 24 * i + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 72, 28, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
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
        ref = composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=(72, 28), view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
