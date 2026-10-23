"""Rock fortress (newsh8.shp, assembly of 21 pieces, 12 distinct): a 3D version of its sprites.

Seen in episode 3 (levels 3.4 and 3.19). Seven columns by three rows of 2x2 enemies make one
168x70 px floating mass of brown boulders with stalactites hanging from its lower edge, and two
red machine pillars set into it, each with a glowing lamp window near the top, a ridged cap, a
slotted lower column with a pipe, a stack of cooling fins and a foot block. The three middle
columns repeat the same three pieces (newsh8-167 / 205 / 243) and the two pillars are the same
three pieces (newsh8-165 / 203 / 241); newsh8-165's four frames only pulse the lamp, so one model
covers them.

The boulders come from the sprite itself: a watershed over the shading splits the rock into
its stones (bright tops, flooding down to the dark cracks), and each stone becomes a rounded pod
lofted down the screen over exactly the pixels of that stone, so neighbouring pods meet in
V-shaped cracks. Every face is then painted with the palette index of the sprite pixel under it,
which keeps the highlights and shadows where the sprite has them. The pillars are modelled by
hand. The whole object is built in assembly coordinates and cut into pieces with
common.split_assembly; repeated pieces are taken from an instance whose neighbours are the same
pieces as in game (the middle column, the left pillar).

Run: blender --background --python assets/blender/enemies/assembly-newsh8-243.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b041 as lib  # noqa: E402

NAME = "assembly-newsh8-243"
ROOT = common.repo_root(__file__)
# Grid cell (0, 0) is screen pixel (-20, -31); the grid is 168 x 84 px and screen (64, 11), the
# centre of the middle piece, is the Blender origin.
ORIGIN = (-20, -31)
GRID = (168, 84)
CX0, CY0 = 64, 11
# The instance of each piece that is exported.
EXPORT = {
    "newsh8-169": (-8, -17), "newsh8-165": (16, -17), "newsh8-167": (64, -17), "newsh8-161": (136, -17),
    "newsh8-207": (-8, 11), "newsh8-203": (16, 11), "newsh8-205": (64, 11), "newsh8-199": (136, 11),
    "newsh8-245": (-8, 39), "newsh8-241": (16, 39), "newsh8-243": (64, 39), "newsh8-237": (136, 39),
}
PILLARS = (24, 120)  # grid column of the pillar pieces' left edges
GLOW = 126  # the lamp window: its frames pulse between indices 117 and 127


def Xe(c):
    """Grid column edge (fractions allowed) to Blender X."""
    return (c - 84) / 12


def Ye(r):
    """Grid row edge to Blender Y: sprite up is +Y."""
    return (42 - r) / 12


def merged_sprite():
    data = common.load_sprite(ROOT, "newsh8-243")
    for name in EXPORT:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


class Mats:
    """Material slots by palette index, created as they're needed."""

    def __init__(self, sprite):
        self.sprite = sprite
        self.mats = []
        self.slots = {}

    def slot(self, index, glow=0.0):
        key = (index, glow)
        if key not in self.slots:
            if index >= 112 or index == 64:
                kw = dict(metallic=0.35, roughness=0.4)
            else:
                kw = dict(metallic=0.0, roughness=0.85)
            tag = NAME + ("_glow" if glow else "")
            self.slots[key] = len(self.mats)
            self.mats.append(common.palette_material(self.sprite, index, tag, emission_strength=glow, **kw))
        return self.slots[key]


def sample(grid, x, y):
    c, r = int(x * 12 + 84), int(42 - y * 12)
    if 0 <= r < len(grid) and 0 <= c < len(grid[0]):
        return grid[r][c]
    return -1


def paint(faces, grid, mats, ok, fallback, under):
    """Give each face the material of the sprite pixel under its centre if ok(index), else
    `fallback`; faces looking down get `under`."""
    for f in faces:
        f.normal_update()
        if f.normal.z < -0.35:
            f.material_index = mats.slot(under)
            continue
        cen = f.calc_center_median()
        best = None
        for dx, dy in ((0, 0), (0.3, 0), (-0.3, 0), (0, 0.3), (0, -0.3)):
            v = sample(grid, cen.x + dx / 12, cen.y + dy / 12)
            if ok(v):
                best = v
                break
        f.material_index = mats.slot(best if best is not None else fallback)


def rocks(bm, grid, mats):
    mask = [[16 <= v <= 31 for v in line] for line in grid]
    vals = [[(v - 16 if 16 <= v <= 31 else 0) for v in line] for line in grid]
    labels, n = lib.watershed(vals, mask, radius=2, min_size=8)
    for reg in lib.regions(labels, n):
        rows = sorted(reg["rows"])
        idx = sorted(grid[r][c] for r, c in reg["px"])
        median = idx[len(idx) // 2]
        wmax = max(hi - lo + 1 for lo, hi in reg["rows"].values())
        height = min(0.27, 0.03 * min(wmax, len(rows)) + 0.04)
        r0, r1 = rows[0], rows[-1]
        span = (r1 + 1 - r0) / 2
        mid = (r0 + r1 + 1) / 2
        # Sections every other row (the union of the pair's extents), plus the end edges.
        secs = []
        groups = [rows[i:i + 2] for i in range(0, len(rows), 2)]
        for gi, g in enumerate(groups):
            lo = min(reg["rows"][r][0] for r in g)
            hi = max(reg["rows"][r][1] for r in g) + 1
            yc = sum(g) / len(g) + 0.5
            t = (yc - mid) / (span + 0.6)
            prof = max(0.25, (1 - t * t)) ** 0.5
            wf = ((hi - lo) / wmax) ** 0.5
            up = height * prof * wf
            secs.append((Ye(yc), Xe(lo), Xe(hi), up, up * 0.6 + 0.03))
        first, last = secs[0], secs[-1]

        def shrink(s, y):
            _, xl, xr, up, down = s
            c, hw = (xl + xr) / 2, (xr - xl) / 2 * 0.6
            return (y, c - hw, c + hw, up * 0.45, down * 0.5)

        secs = [shrink(first, Ye(r0))] + secs + [shrink(last, Ye(r1 + 1))]
        start = len(bm.faces)
        lib.pod(bm, secs, sides=8)
        bm.faces.ensure_lookup_table()
        paint(bm.faces[start:], grid, mats, lambda v: 16 <= v <= 31, median, 18)


def pillar(bm, grid, mats, c0):
    """A red machine pillar; c0 is the grid column of its piece's left edge."""
    x = lambda c: Xe(c0 + c)  # noqa: E731  (local column edge)
    faces_from = len(bm.faces)

    def body(secs, sides=8):
        lib.pod(bm, [(Ye(r), x(a), x(b), up, down) for r, a, b, up, down in secs], sides=sides)

    # Upper housing (rows 5-32): a rounded box with a ridge round its cap at row 7.
    body([(5.0, 6.6, 16.4, 0.14, 0.1), (5.5, 6.0, 17.0, 0.24, 0.17), (6.8, 6.0, 17.0, 0.26, 0.18),
          (7.2, 5.6, 17.4, 0.3, 0.2), (7.8, 5.6, 17.4, 0.3, 0.2), (8.2, 6.0, 17.0, 0.26, 0.18),
          (15.8, 6.0, 17.0, 0.26, 0.18), (16.2, 5.0, 17.0, 0.27, 0.18), (32.6, 5.0, 17.0, 0.27, 0.18),
          (33.0, 5.6, 16.6, 0.2, 0.14)], sides=8)
    # Lower column (rows 33-45), narrower and set back, with a pipe down its left side.
    body([(32.8, 7.6, 16.8, 0.19, 0.14), (45.2, 7.6, 16.8, 0.19, 0.14)], sides=8)
    start = len(bm.verts)
    common.loft(bm, [(Ye(32.8), 0.05, 0.05, 0.2), (Ye(45.0), 0.05, 0.05, 0.2)], sides=6)
    common.shift_x(bm, start, x(10.5))
    # Cooling fins (rows 45-55) round a dark core.
    body([(44.8, 9.0, 15.0, 0.12, 0.1), (56.0, 9.0, 15.0, 0.12, 0.1)], sides=6)
    for r, a, b in ((45, 6.0, 15.0), (47, 6.0, 16.0), (49, 6.6, 16.0), (51, 7.0, 15.0), (53, 9.0, 16.0),
                    (55, 8.0, 16.0)):
        body([(r + 0.05, a + 0.3, b - 0.3, 0.17, 0.13), (r + 0.3, a, b, 0.22, 0.16), (r + 0.7, a, b, 0.22, 0.16),
              (r + 0.95, a + 0.3, b - 0.3, 0.17, 0.13)], sides=8)
    # Foot block (rows 56-60).
    body([(55.9, 6.4, 15.6, 0.17, 0.13), (56.5, 6.0, 16.0, 0.22, 0.16), (59.6, 6.0, 16.0, 0.22, 0.16),
          (60.6, 6.8, 15.4, 0.14, 0.1)], sides=8)
    bm.faces.ensure_lookup_table()
    paint(bm.faces[faces_from:], grid, mats, lambda v: v == 64 or 112 <= v <= 127, 64, 112)

    # The lamp window (rows 14-24, columns 9-13), glowing.
    glow = mats.slot(GLOW, glow=4.0)
    win = [(9.6, 14.0), (13.4, 14.0), (14.0, 14.6), (14.0, 24.4), (13.4, 25.0), (9.6, 25.0), (9.0, 24.4), (9.0, 14.6)]
    common.slab(bm, [(x(c), Ye(r)) for c, r in reversed(win)], 0.08, z=0.25, mat_index=glow)


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    mats = Mats(sprite)
    bm = bmesh.new()
    rocks(bm, grid, mats)
    for c0 in PILLARS:
        pillar(bm, grid, mats, c0)
    return common.mesh_object(NAME, bm, mats.mats, coll, smooth=True)


def composite_png(grid, colors, out):
    """The whole object's sprite padded to the 12:14 shape render_preview expects (168 x 196)."""
    pad = (196 - 84) // 2
    rows = [[(0, 0, 0, 0)] * 168 for _ in range(pad)]
    for line in grid:
        rows.append([(*colors[str(v)], 255) if v >= 0 else (0, 0, 0, 0) for v in line])
    rows += [[(0, 0, 0, 0)] * 168 for _ in range(196 - len(rows))]
    lib.write_png(out, rows)
    return out


def main():
    sprite = merged_sprite()
    grid = lib.assembled_grid(ROOT, sprite["assemblyLayout"], ORIGIN, GRID)
    obj = build(sprite, grid)
    layout = [(name, cx - CX0, cy - CY0) for name, (cx, cy) in EXPORT.items()]
    pieces = common.split_assembly(obj, layout)
    for name in EXPORT:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(grid, sprite["colors"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=14, view_px=640)
        for name in EXPORT:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
