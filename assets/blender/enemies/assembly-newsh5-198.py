"""The brain's upper half (newsh5.shp 196, 198, 200, an assembly of three pieces): a 3D version of
its sprites.

Seen in episode 4 (level 4.22). Three 2x2 enemies side by side (sprite.json `assemblyLayout`)
make the top of a giant brain, 72 x 24 px: two dark red hemispheres, split by a deep fissure down
the middle, covered in rounded folds (gyri) with dark grooves between them. A long light fold
sweeps from the lower left up towards the fissure; the brightest lumps are along the bottom edge,
where the brain carries on (below the red star, newsh5-278, which other batches model).

Built whole in assembly coordinates: a domed core lofted column by column to the sprite's outline
(lower along the fissure), with the folds laid on it as rounded tubes, then cut into the three
pieces with common.split_assembly. Each piece has one frame.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-198.py [-- --preview out.png]
(the preview is the whole brain top; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b030 as lib  # noqa: E402

NAME = "assembly-newsh5-198"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-196", "newsh5-198", "newsh5-200"]  # left to right
# Origin: the centre of newsh5-198 (screen cx 162, cy -18). Assembly column a = 0..71 runs across
# the three pieces (newsh5-196 is columns 0-23), rows 0-27 are the pieces' rows.
CX0, CY0 = 162, -18
PX = 1 / 12


def X(a):
    """Assembly column (pixel centre; fractions allowed) to Blender X."""
    return (a - 35.5) / 12


def Y(r):
    """Row (pixel centre) to Blender Y."""
    return (13.5 - r) / 12


def column_tops(sprites):
    """The first coloured row (not transparent, not the black outline) of each assembly column."""
    tops = []
    for data in sprites:
        pix = data["frames"][0]["pixels"]
        for c in range(24):
            r = next((r for r in range(28) if pix[r][c] not in (-1, 1)), 28)
            tops.append(r)
    # smooth the staircase a little, but keep the notch at the fissure (columns 34-38)
    out = list(tops)
    for a in range(1, 71):
        if not 33 <= a <= 39:
            out[a] = 0.25 * tops[a - 1] + 0.5 * tops[a] + 0.25 * tops[a + 1]
    return out


class Brain:
    """The domed core: a loft of rings standing in the YZ plane, one per column, each spanning
    from the sprite's top edge down past the bottom of the pieces (row 31, cut away later)."""

    BOTTOM_ROW = 31.0
    EXP = 0.75  # superellipse exponent: < 1 fills the rings out

    def __init__(self, tops):
        self.tops = tops

    def top_edge(self, a):
        a = min(max(a, 0.0), 71.0)
        i = min(int(a), 70)
        f = a - i
        t = self.tops[i] * (1 - f) + self.tops[i + 1] * f
        return t - 0.5 + 0.3  # pixel top edge, a little inside

    def heights(self, a):
        d = (a - 35.8) / 37.0
        prof = math.sqrt(max(0.0, 1 - d * d))
        fiss = 1 - 0.45 * math.exp(-((a - 36.4) / 1.3) ** 2)
        return (0.07 + 0.25 * prof) * fiss, 0.05 + 0.11 * prof

    def span(self, a):
        top = self.top_edge(a)
        y_top, y_bot = Y(top - 0.5), Y(self.BOTTOM_ROW)
        return (y_top + y_bot) / 2, (y_top - y_bot) / 2

    def ring(self, a, sides=18, scale=1.0):
        yc, ry = self.span(a)
        hz_top, hz_bot = self.heights(a)
        pts = []
        for k in range(sides):
            t = 2 * math.pi * (k + 0.5) / sides
            c, s = math.cos(t), math.sin(t)
            y = yc + ry * math.copysign(abs(c) ** self.EXP, c) * scale
            z = (hz_top if s > 0 else hz_bot) * math.copysign(abs(s) ** self.EXP, s) * scale
            pts.append((X(a), y, z))
        return pts

    def z(self, x, y):
        """Height of the core's top surface at (x, y) in units."""
        a = x * 12 + 35.5
        yc, ry = self.span(a)
        hz_top, _ = self.heights(a)
        u = min(abs(y - yc) / ry, 1.0) if ry > 0 else 1.0
        c = u ** (1 / self.EXP)
        s = math.sqrt(max(0.0, 1 - c * c))
        return hz_top * s ** self.EXP


def build(sprite, tops):
    coll = common.reset_collection(NAME)
    tag = "nsh5brain"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(67, metallic=0.1, roughness=0.55),  # 0 dark red core, showing in the grooves
        pal(71, metallic=0.1, roughness=0.45),  # 1 folds
        pal(74, metallic=0.15, roughness=0.35),  # 2 light folds
        pal(69, metallic=0.1, roughness=0.5),  # 3 shaded folds (right side, edges)
        pal(64, metallic=0.0, roughness=0.8),  # 4 the fissure's dark depths
    ]
    CORE, FOLD, LIGHT, SHADE, DEEP = range(5)
    brain = Brain(tops)
    bm = bmesh.new()

    # Core: rings every column from 1.6 to 70.4, closing to a point at each end.
    cols = [1.6] + [a + 0.5 for a in range(2, 70)] + [70.4]
    rings = []
    yc, _ = brain.span(1.0)
    rings.append([(X(1.0), yc, 0.0)])
    for a in cols:
        rings.append(brain.ring(a))
    yc, _ = brain.span(71.0)
    rings.append([(X(71.0), yc, 0.0)])
    lib.ring_loft(bm, rings, mat=CORE, smooth=True)

    def fold(points, w, mat=FOLD, h=0.07, sides=8):
        n = len(points)  # fuller in the middle, like a fold swelling out of the grooves
        ws = [w * 1.45 * PX * (0.85 + 0.25 * math.sin(math.pi * i / max(n - 1, 1))) for i in range(n)]
        lib.sausage(bm, [(X(a), Y(r)) for a, r in points], ws, h, sides=sides, mat=mat,
                    z_of=brain.z, lift=-0.02)

    # The fissure: a dark strip in the dip down the middle.
    lib.sausage(bm, [(X(36.4), Y(9.0)), (X(36.4), Y(28.5))], 0.9 * PX, 0.02, sides=6, mat=DEEP,
                z_of=brain.z, lift=0.0)

    # Left hemisphere.
    fold([(4.2, 24.4), (8.0, 24.9)], 2.6)  # round lobe at the lower left
    fold([(6.2, 17.6), (10.5, 18.7), (13.5, 21.6), (16.5, 24.0), (21.0, 24.6), (24.6, 22.2),
          (28.0, 19.0), (31.6, 18.4)], 1.6, LIGHT)  # the long light fold
    fold([(13.4, 13.4), (17.0, 15.6)], 1.8, LIGHT)
    fold([(18.4, 10.8), (21.0, 9.6), (24.0, 6.6), (27.4, 5.6)], 2.1)  # along the top edge
    fold([(11.6, 11.6), (15.8, 10.8)], 1.6, SHADE)
    fold([(17.2, 18.6), (22.4, 18.6), (26.0, 15.6), (30.0, 15.2)], 1.5)
    fold([(29.6, 26.6), (32.8, 26.0)], 2.2, LIGHT)  # bright lump at the bottom
    fold([(30.4, 9.8), (33.2, 11.4), (34.0, 13.4)], 1.9, LIGHT)  # cap beside the fissure
    fold([(24.4, 11.0), (27.6, 12.6)], 1.7)
    fold([(24.2, 25.6), (27.2, 26.4)], 1.7)
    fold([(34.6, 16.6), (34.4, 23.6)], 1.1, SHADE)
    fold([(5.0, 20.4), (8.6, 21.4)], 1.3, SHADE)
    fold([(8.6, 14.4), (11.6, 13.8)], 1.3, SHADE)
    fold([(17.0, 26.6), (21.6, 26.8)], 1.4)
    fold([(19.6, 13.6), (23.6, 13.0)], 1.4)
    fold([(3.2, 21.6), (4.4, 19.4)], 1.1, SHADE)

    # Right hemisphere.
    fold([(38.0, 10.0), (39.0, 12.6)], 2.0, LIGHT)  # cap beside the fissure
    fold([(39.4, 22.0), (40.9, 19.0), (42.0, 16.4)], 1.8, LIGHT)
    fold([(38.8, 26.5), (42.2, 25.6)], 2.2, LIGHT)  # bright lump at the bottom
    fold([(44.4, 5.4), (48.0, 6.6), (51.0, 9.6)], 2.4)  # top right lobe
    fold([(44.4, 19.6), (46.0, 21.6), (49.0, 24.0), (51.6, 24.6)], 1.7, LIGHT)
    fold([(55.0, 12.8), (57.6, 15.6)], 1.6)
    fold([(56.6, 11.0), (61.4, 12.4)], 1.4, SHADE)
    fold([(56.0, 23.6), (59.6, 21.0), (62.6, 18.0)], 1.5)
    fold([(63.4, 16.6), (67.2, 18.2)], 1.4, SHADE)
    fold([(63.4, 23.4), (68.4, 23.6)], 2.0)
    fold([(46.0, 17.4), (53.6, 18.4)], 1.4, SHADE)
    fold([(43.0, 14.4), (47.6, 14.8)], 1.4)
    fold([(52.4, 26.6), (57.6, 26.8)], 1.3, SHADE)
    fold([(53.0, 13.4), (51.0, 15.6)], 1.2, SHADE)
    fold([(59.6, 25.6), (62.0, 26.6)], 1.2, SHADE)
    fold([(66.6, 20.4), (68.8, 21.0)], 1.0, SHADE)

    return lib.to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newsh5-198's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh5-198")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(out):
    """The three pieces' sprites as one 72 x 84 image centred on newsh5-198's centre (the shape
    render_preview expects for size 6)."""
    import numpy as np
    img = np.zeros((84, 72, 4), dtype=np.float32)
    for i, name in enumerate(PIECES):
        data = common.load_sprite(ROOT, name)
        for r, rw in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(rw):
                if v >= 0:
                    img[28 + r, 24 * i + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 72, 84, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    tops = column_tops([common.load_sprite(ROOT, n) for n in PIECES])
    obj = build(sprite, tops)
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
        # the whole top as cut: the pieces put back in place
        for name, cx, cy in layout:
            pieces[name].location = (cx / 12, -cy / 12, 0)
        common.render_preview([pieces[n] for n in PIECES], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            pieces[name].location = (0, 0, 0)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
