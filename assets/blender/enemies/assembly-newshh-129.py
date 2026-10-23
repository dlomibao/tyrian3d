"""Waterfall (newshh.shp, a 5 x 2 block of 2x2 pieces): a 3D version of its sprites.

Seen in episode 2 (levels 2.2 and 2.24). Ten 2x2 ground enemies side by side make one 120 x 56 px
scene, flanked in game by two rock pillars (newshg-153 and newshg-191, modelled elsewhere):

- top row: newshh-117 (grey cliff on the left, water on the right), three newshh-129 (falling
  water) and newshh-153 (water, a dark shadowed cliff face and a lit one),
- bottom row: newshh-157 (cliff foot, green bushes and a rock rim on the left), three newshh-205
  (the foot of the fall: dark gaps between the last sheets of water, a band of foam, the pool)
  and newshh-207 (pool, rock rim, cliff foot and bushes on the right).

In 3D the water runs down a slope from the cliff top (z 0.52 at the back) to the pool (z 0.07):
strands of water 2 px wide (with the dark gaps of the sprite between them), bright streaks, a
ridge of foam with sparkles where it lands and a flat pool. The cliffs either side step down from
a lit top with a highlighted edge; bushes and rounded rocks frame the pool.

Every piece animates only the water (the streaks and sparkles move), so one model covers all of
its frames. newshh-129 and newshh-205 each appear three times side by side; the strands and foam
are laid out from the sprite pixels, which are the same for each copy, so one cut of each tiles.

Built whole in assembly coordinates, then cut into the pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshh-129.py [-- --preview out.png]
(the preview is the whole waterfall; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b112 as lib  # noqa: E402

NAME = "assembly-newshh-129"
ROOT = common.repo_root(__file__)
PIECES = ["newshh-117", "newshh-129", "newshh-153", "newshh-157", "newshh-205", "newshh-207"]
# The block is 120 x 56 px: screen x 68..187, y -3..52. Its centre (screen 128, 25) is the origin.
CX0, CY0 = 128, 25
W, H = 120, 56
G = lib.Grid(W, H)
X, Y = G.X, G.Y

# Heights (row edge -> z): the water slope, the cliffs and the pool.
FALL = [(0, 0.52), (2, 0.515), (4, 0.49), (8, 0.43), (14, 0.36), (22, 0.28), (30, 0.2),
        (38, 0.13), (42, 0.1), (45, 0.09)]
CLIFF = [(0, 0.56), (7, 0.56), (8.5, 0.5), (16, 0.44), (28, 0.35), (36, 0.27), (41, 0.21)]
POOL_Z = 0.07
FOAM_ROW, FOAM_W, FOAM_Z, FOAM_H = 43.5, 3.2, 0.085, 0.04
STRAND_END = 41  # strands of falling water run over rows 0..40


def composite():
    """Assembly pixels {(col, row): index} from each piece's frame used in the layout, the
    layout itself (one entry per model) and every piece's colours."""
    base = common.load_sprite(ROOT, PIECES[0])
    colors, pixels, layout = {}, {}, {}
    for entry in base["assemblyLayout"]:
        name = entry["model"]
        if name not in PIECES:
            continue
        data = common.load_sprite(ROOT, name)
        colors.update(data["colors"])
        index = int(entry["frame"].split("|")[-1])
        frame = next((f for f in data["frames"] if f["index"] == index), data["frames"][0])
        c0, r0 = entry["cx"] - 12 - (CX0 - W // 2), entry["cy"] - 14 - (CY0 - H // 2)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                pixels[(c0 + c, r0 + r)] = v
        layout.setdefault(name, (entry["cx"] - CX0, entry["cy"] - CY0))
    base["colors"] = colors
    return base, pixels, [(n, *layout[n]) for n in PIECES]


def fall_z(r):
    return lib.interp(FALL, r)


def surface_z(r):
    """Top of the water at row centre r: the slope, the foam ridge or the pool."""
    z = max(fall_z(r) if r < 44 else 0.0, POOL_Z)
    d = abs(r - FOAM_ROW) / FOAM_W
    if d < 1:
        z = max(z, FOAM_Z + FOAM_H * (1 - d * d) ** 0.5)
    return z


def quant(a):
    return min(max(int(round(a)), 50), 59)


def strands(bm, pixels, M):
    """Falling water as 2 px strands down the slope, broken where the sprite shows dark gaps,
    coloured by the sprite's brightness along them, with bright streaks on top."""
    for c in range(12, 106, 2):
        rows = []
        for r in range(STRAND_END):
            vals = [v for v in (pixels.get((c, r), -1), pixels.get((c + 1, r), -1)) if v >= 49]
            rows.append(sum(vals) / len(vals) if vals else None)
        for r in range(1, STRAND_END - 1):  # one-row gaps are noise
            if rows[r] is None and rows[r - 1] is not None and rows[r + 1] is not None:
                rows[r] = (rows[r - 1] + rows[r + 1]) / 2
        r = 0
        while r < STRAND_END:
            if rows[r] is None:
                r += 1
                continue
            s = r
            while r < STRAND_END and rows[r] is not None:
                r += 1
            if r - s < 2:
                continue
            seg = rows[s:r]
            # Colour runs, from a 3-row average; runs under 3 rows join the one before.
            cols = []
            for i in range(len(seg)):
                win = seg[max(i - 1, 0):i + 2]
                cols.append(quant(sum(win) / len(win)))
            runs = []
            for i, q in enumerate(cols):
                if runs and (runs[-1][2] == q or i - runs[-1][0] < 3):
                    runs[-1][1] = i + 1
                else:
                    runs.append([i, i + 1, q])
            if len(runs) > 1 and runs[-1][1] - runs[-1][0] < 3:
                runs[-2][1] = runs[-1][1]
                runs.pop()
            # One continuous strand, its bands coloured by the runs.
            secs = []
            for a, b, q in runs:
                for e in list(range(s + a, s + b, 3)):
                    secs.append((Y(e - 0.5), 1.15 * lib.PX, 0.03, fall_z(e), M.slot(q)))
            last = secs[-1][4]
            if r < STRAND_END:  # a rounded lower end where it breaks off
                secs.append((Y(r - 0.5), 1.15 * lib.PX, 0.03, fall_z(r), last))
                secs.append((Y(r + 0.3), 0.0, 0.0, fall_z(r + 0.8), last))
            else:
                secs.append((Y(r - 0.5), 1.15 * lib.PX, 0.03, fall_z(r), last))
            lib.loft_bands(bm, X(c + 0.5), secs, sides=6)

    # Bright streaks: runs of index >= 59 down a single column.
    for c in range(12, 106):
        r = 0
        while r < STRAND_END:
            if pixels.get((c, r), -1) < 59:
                r += 1
                continue
            s = r
            while r < STRAND_END and pixels.get((c, r), -1) >= 59:
                r += 1
            if r - s < 2:
                continue
            top = max(pixels[(c, k)] for k in range(s, r))
            idx = 62 if top >= 62 else 61 if top == 61 else 60
            edges = [s] + ([s + (r - s) // 2] if r - s > 3 else []) + [r]
            secs = [(Y(edges[0] - 0.4), 0.0, 0.0, fall_z(edges[0]) + 0.03)]
            secs += [(Y(e - 0.5), 0.5 * lib.PX, 0.02, fall_z(e) + 0.03) for e in edges]
            secs.append((Y(edges[-1] - 0.6), 0.0, 0.0, fall_z(edges[-1]) + 0.03))
            start, fstart = len(bm.verts), len(bm.faces)
            common.loft(bm, secs, sides=4, mat_index=M.slot(idx))
            common.shift_x(bm, start, X(c))
            bm.faces.ensure_lookup_table()
            for f in bm.faces[fstart:]:
                f.smooth = True


def foam(bm, pixels, M):
    """A ridge of foam where the water lands, sparkles on it in the pool."""
    path = [(4.5, FOAM_ROW + 1.0), (10, FOAM_ROW - 1.5), (20, FOAM_ROW - 1.0)]
    path += [(c, FOAM_ROW + (0.5 if (c // 12) % 2 else -0.3)) for c in range(32, 100, 12)]
    path += [(104, FOAM_ROW - 1.0), (111.5, FOAM_ROW - 2.5)]
    lib.sweep(bm, G, [(c, r, FOAM_Z, FOAM_W, FOAM_H) for c, r in path], sides=8, mat=M.slot(58))
    # Sparkles: the brightest pixels of the foam and the pool.
    for (c, r), v in pixels.items():
        if v >= 59 and 34 <= r < H and 5 <= c <= 112 and (r >= 38 or c < 12):
            idx = 62 if v >= 62 else 61 if v == 61 else 60
            lib.ellipsoid(bm, G, c, r, surface_z(r), 0.75, 0.75, 0.025, mat=M.slot(idx), segments=6, rings=3)


def cliffs(bm, M):
    """The grey cliffs either side of the fall and the rocks round the pool."""
    # Left cliff (newshh-117 and the top of newshh-157): a dark face under a lit top.
    lib.ramp(bm, G, 0, 12, CLIFF, M.slot(3), r_to=41, step=4)
    lib.plate(bm, G, [(0, 0), (12, 0), (12, 5.5), (9, 7.5), (0, 7.5)], 0.5, CLIFF[0][1] + 0.025, M.slot(6))
    lib.sweep(bm, G, [(-0.2, 6.6, CLIFF[0][1] + 0.01, 1.0, 0.03), (4, 6.0, CLIFF[0][1] + 0.015, 1.1, 0.035),
                      (8, 6.0, CLIFF[0][1] + 0.01, 1.0, 0.03), (11.2, 4.8, CLIFF[0][1] + 0.005, 0.0, 0.0)],
              sides=6, mat=M.slot(10))
    lib.sweep(bm, G, [(3, 0, CLIFF[0][1] + 0.025, 0.6, 0.01), (3, 7.0, CLIFF[0][1] + 0.025, 0.6, 0.01)],
              sides=4, mat=M.slot(3), smooth=False)  # crack across the top
    # The lit rib down the face (columns 6-8) and a darker groove beside it (columns 3-5).
    lib.sweep(bm, G, [(7.2, 6.5, lib.interp(CLIFF, 6.5) - 0.01, 0.0, 0.0)]
              + [(7.2 - (r > 30) * 0.6, r, lib.interp(CLIFF, r), 1.6, 0.05) for r in (8, 14, 20, 26, 32)]
              + [(6.4, 37.5, lib.interp(CLIFF, 37.5), 1.4, 0.045), (6.0, 40.8, lib.interp(CLIFF, 40.8), 0.0, 0.0)],
              sides=6, mat=M.slot(5))
    lib.ramp(bm, G, 3, 6, CLIFF, M.slot(2), r_from=15, r_to=36, step=4, lift=0.008)
    # A rock lump at the foot (newshh-157 rows 4-8, columns 3-7).
    lib.ellipsoid(bm, G, 4.8, 34.5, lib.interp(CLIFF, 34.5), 2.4, 2.4, 0.06, mat=M.slot(5), segments=8, rings=4)

    # Right cliff (newshh-153 and the top of newshh-207): a shadowed face by the water and a lit one.
    shade = [(0, 0.56), (3.5, 0.56), (5, 0.42), (16, 0.34), (28, 0.26), (36, 0.2), (41, 0.17)]
    lib.ramp(bm, G, 105, 113, shade, M.slot(2), r_to=34, step=4)
    lib.ramp(bm, G, 109, 113, shade, M.slot(2), r_from=34, r_to=41, step=4)
    for c, r, rad, idx in ((108.6, 9.6, 1.6, 4), (108.0, 13.2, 1.2, 3), (110.0, 19.8, 1.8, 4), (109.2, 25.5, 1.4, 4),
                           (113.2, 23.6, 1.5, 5), (110.5, 31.0, 1.4, 3)):
        lib.ellipsoid(bm, G, c, r, lib.interp(shade, r), rad, rad * 1.2, 0.04, mat=M.slot(idx), segments=6, rings=3)
    lib.ramp(bm, G, 113, 120, CLIFF, M.slot(4), r_to=41, step=4)
    lib.plate(bm, G, [(107, 0), (120, 0), (120, 8.5), (117, 8.5), (110, 3.8), (107, 3.8)], 0.5,
              CLIFF[0][1] + 0.025, M.slot(5))
    lib.sweep(bm, G, [(108.5, 2.0, CLIFF[0][1] + 0.005, 0.0, 0.0), (110.0, 2.8, CLIFF[0][1] + 0.015, 1.0, 0.035),
                      (114.0, 5.0, CLIFF[0][1] + 0.015, 1.1, 0.035), (116.6, 7.6, CLIFF[0][1] + 0.01, 1.0, 0.03),
                      (117.6, 8.6, CLIFF[0][1] + 0.005, 0.0, 0.0)], sides=6, mat=M.slot(11))
    lib.sweep(bm, G, [(115.6, 8.0, lib.interp(CLIFF, 8.0) - 0.01, 0.0, 0.0)]
              + [(115.6 - max(r - 26, 0) * 0.13, r, lib.interp(CLIFF, r), 1.3, 0.045) for r in (9.5, 16, 22, 28, 34)]
              + [(113.8, 39.5, lib.interp(CLIFF, 39.5), 0.0, 0.0)], sides=6, mat=M.slot(5))
    # A green vine down the lit face (newshh-207 column 19).
    lib.sweep(bm, G, [(115.2, 32.5, lib.interp(CLIFF, 32.5) + 0.01, 0.0, 0.0),
                      (115.2, 34, lib.interp(CLIFF, 34) + 0.01, 0.9, 0.03),
                      (115.4, 40, lib.interp(CLIFF, 40) + 0.01, 0.9, 0.03),
                      (115.4, 41.5, lib.interp(CLIFF, 41.5) + 0.01, 0.0, 0.0)], sides=5, mat=M.slot(34))

    # Rocks round the pool: a dark lump at each cliff foot and a rounded rim curving down.
    lib.sweep(bm, G, [(5.6, 39.5, 0.1, 0.0, 0.0), (5.6, 41, 0.1, 2.0, 0.09), (5.8, 46, 0.09, 2.0, 0.08),
                      (7.0, 49, 0.08, 1.8, 0.07)], sides=8, mat=M.slot(2))
    lib.sweep(bm, G, [(6.4, 48.2, 0.07, 0.0, 0.0), (7.0, 49.0, 0.07, 1.6, 0.08), (9.5, 51.8, 0.07, 2.0, 0.09),
                      (12.0, 54.4, 0.07, 2.0, 0.09), (13.6, 56.0, 0.07, 1.8, 0.08)], sides=8, mat=M.slot(4))
    lib.sweep(bm, G, [(112.0, 37.5, 0.11, 0.0, 0.0), (112.4, 39, 0.11, 1.4, 0.08), (112.6, 45.5, 0.09, 1.6, 0.08),
                      (111.2, 48.5, 0.08, 1.8, 0.08)], sides=8, mat=M.slot(2))
    lib.sweep(bm, G, [(112.0, 47.2, 0.07, 0.0, 0.0), (111.2, 48.4, 0.07, 1.6, 0.08), (108.6, 50.6, 0.07, 2.0, 0.09),
                      (106.0, 53.6, 0.07, 2.0, 0.09), (104.6, 56.0, 0.07, 1.8, 0.08)], sides=8, mat=M.slot(4))
    lib.ellipsoid(bm, G, 108.8, 50.2, 0.13, 1.3, 1.1, 0.04, mat=M.slot(7), segments=6, rings=3)
    lib.ellipsoid(bm, G, 10.6, 52.4, 0.13, 1.2, 1.0, 0.035, mat=M.slot(4), segments=6, rings=3)


def bushes(bm, M):
    """Green bushes at the foot of each cliff, below the rock rims."""
    # Dark ground under them so nothing shows through between the clumps.
    lib.plate(bm, G, [(0, 36), (4, 36), (4.5, 48), (12, 56), (0, 56)], 0.0, 0.05, M.slot(32))
    lib.plate(bm, G, [(112.5, 40), (120, 40), (120, 56), (104, 56), (112.5, 48)], 0.0, 0.05, M.slot(32))
    clumps = [
        # left: (col, row, radius px, height, index)
        (1.8, 38.0, 1.8, 0.12, 35), (1.6, 41.8, 2.0, 0.15, 34), (2.0, 45.5, 2.2, 0.16, 192),
        (2.2, 49.5, 2.4, 0.18, 35), (1.8, 53.6, 2.4, 0.17, 193), (5.4, 52.6, 2.0, 0.14, 33),
        (7.4, 55.0, 1.8, 0.12, 34), (4.5, 55.8, 1.6, 0.11, 194),
        # right
        (116.6, 42.5, 2.0, 0.13, 33), (119.2, 44.6, 1.8, 0.14, 35), (115.4, 46.6, 2.0, 0.15, 192),
        (118.4, 48.8, 2.2, 0.17, 34), (114.6, 51.0, 2.0, 0.15, 193), (118.6, 53.4, 2.2, 0.18, 35),
        (111.8, 54.4, 2.0, 0.14, 194), (115.4, 55.4, 2.0, 0.15, 197),
    ]
    bright = {32: 193, 33: 194, 34: 194, 35: 195, 192: 195, 193: 195, 194: 197, 197: 195}
    for k, (c, r, rad, h, idx) in enumerate(clumps):
        lib.ellipsoid(bm, G, c, r, 0.03, rad * 1.2, rad * 1.1, h * 0.65, mat=M.slot(idx), segments=8, rings=4)
        if k % 2 == 0:  # a lit tuft of leaves on top
            lib.ellipsoid(bm, G, c - rad * 0.25, r - rad * 0.25, 0.03 + h * 0.52, rad * 0.55, rad * 0.5, h * 0.2,
                          mat=M.slot(bright[idx]), segments=6, rings=3)


def build(sprite, pixels):
    coll = common.reset_collection(NAME)
    water = {i: {"metallic": 0.2, "roughness": 0.15} for i in range(48, 63)}
    rock = {i: {"metallic": 0.05, "roughness": 0.8} for i in range(1, 13)}
    leaf = {i: {"metallic": 0.0, "roughness": 0.75} for i in (32, 33, 34, 35, 36, 192, 193, 194, 195, 197)}
    M = lib.Mats(sprite, "nshh129", {**water, **rock, **leaf})
    bm = bmesh.new()

    # The water: a dark slope (seen through the gaps) and the pool, then strands, streaks, foam.
    lib.ramp(bm, G, 12, 105, FALL, M.slot(49), r_to=45, step=2)
    lib.plate(bm, G, [(4, 38), (104, 38), (104, 33), (112.5, 33), (112.5, 48), (104.5, 56), (12.5, 56), (4.5, 48)], 0.0, POOL_Z, M.slot(54))
    strands(bm, pixels, M)
    foam(bm, pixels, M)
    cliffs(bm, M)
    bushes(bm, M)
    return lib.to_object(NAME, bm, M.list, coll)


def main():
    sprite, pixels, layout = composite()
    obj = build(sprite, pixels)
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        # The whole sprite, padded to the 24:28 shape render_preview expects for size 10.
        padded = {(c, r + (140 - H) // 2): v for (c, r), v in pixels.items()}
        ref = lib.composite_png(padded, sprite["colors"], 120, 140, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=10, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
