"""Golden horned arm (newsh4.shp, assembly of 7 pieces): a 3D version of its sprites.

Seen in episode 1 (level 1.3) and episode 3 (level 3.17). Seven 2x2 enemies in a row make one
168x28 px object (sprite.json `assemblyLayout`): a long brown-gold horn that tapers and curves
down to a point at the far left, with grey metal studs along its top and a few raised bands near
its root, a round knuckle, and the start of a thick ribbed segment cut off at the right edge.
Each piece is a single frame.

The whole arm is built once in assembly coordinates, painted from the sprite's own shading (each
face takes the palette index of the pixels under it, grouped into a few shades), then cut into
the seven pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh4-231.py [-- --preview out.png]
(the preview is the whole arm; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b061 as lib  # noqa: E402

NAME = "assembly-newsh4-231"
ROOT = common.repo_root(__file__)
PIECES = ["newsh4-231", "newsh4-233", "newsh4-235", "newsh4-267", "newsh4-269", "newsh4-271", "newsh4-273"]
W, H = 168, 28  # assembly size in px; piece i covers columns 24 i .. 24 i + 23
# Assembly pixel edge (0, 0) is the top-left corner of newsh4-231 (screen 98 - 12, 15 - 14). The
# Blender origin is the assembly's centre, which is the centre of newsh4-267 (screen 170, 15).
CX0, CY0 = 170, 15
U = 1 / 12


def X(e):
    """Assembly pixel edge coordinate (column c's centre is c + 0.5) to Blender X."""
    return (e - W / 2) * U


def Y(e):
    """Assembly pixel edge coordinate (row r's centre is r + 0.5) to Blender Y (sprite up is +Y)."""
    return (H / 2 - e) * U


def load():
    """The pieces' sprites, their merged colours and the whole arm's pixels as one grid."""
    grid = [[-1] * W for _ in range(H)]
    colors, sprites = {}, {}
    for i, name in enumerate(PIECES):
        data = common.load_sprite(ROOT, name)
        sprites[name] = data
        colors.update(data["colors"])
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                grid[r][24 * i + c] = v
    return grid, colors, sprites


def sampler(grid, skip=(-1, 1), reach=2):
    """sample(x, y) -> the palette index of the arm pixel under Blender (x, y); transparent and
    outline pixels are skipped for the nearest other pixel within `reach`."""
    def sample(x, y):
        c, r = int(math.floor(x / U + W / 2)), int(math.floor(H / 2 - y / U))
        for d in range(reach + 1):
            best = None
            for dr in range(-d, d + 1):
                for dc in range(-d, d + 1):
                    if max(abs(dr), abs(dc)) != d:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and grid[rr][cc] not in skip:
                        dist = dr * dr + dc * dc
                        if best is None or dist < best[0]:
                            best = (dist, grid[rr][cc])
            if best:
                return best[1]
        return None
    return sample


def horn_profile(grid):
    """For each column of the horn (2..122): (centre row, vertical half width) in pixel edges,
    from the sprite's filled rows, smoothed. Past column 112 the knuckle hangs below the horn, so
    the horn keeps the rows 1-12 it has there."""
    raw = {}
    for c in range(2, 123):
        if c <= 112:
            rows = [r for r in range(H) if grid[r][c] != -1]
            top, bottom = min(rows), max(rows) + 1
        else:
            top, bottom = 1, 13
        raw[c] = (top, bottom)
    prof = {}
    for c in raw:
        near = [raw[k] for k in range(c - 2, c + 3) if k in raw]
        top = sum(t for t, _ in near) / len(near)
        bottom = sum(b for _, b in near) / len(near)
        prof[c] = ((top + bottom) / 2, (bottom - top) / 2)
    return prof


def horn_path(prof):
    """Sections (x, y, z, half_width, half_height) down the horn from its tip to inside the knuckle."""
    path = [(X(2.0), Y(25.9), 0.0, 0.0, 0.0)]
    c = 2.6
    while c < 122:
        k = int(c)
        m, vh = prof[k]
        m1, _ = prof[min(k + 2, 122)]
        m0, _ = prof[max(k - 2, 2)]
        slope = (m1 - m0) / (min(k + 2, 122) - max(k - 2, 2))
        w = vh * math.cos(math.atan(slope)) * U
        h = min(0.25, 0.55 * w + 0.005)
        path.append((X(c + 0.5), Y(m), 0.0, w, h))
        c += 1.5 if c > 6 else 1.0
    return path


def surface_z(prof, c, r):
    """Height of the horn's top surface over pixel (c, r) (edge coordinates), 0 off the horn."""
    m, vh = prof[int(c)]
    w = vh * U
    h = min(0.25, 0.55 * w + 0.005)
    t = (r - m) / vh
    return h * math.sqrt(max(0.0, 1 - t * t))


def build(grid, colors):
    coll = common.reset_collection(NAME)
    mats = lib.Mats("nsh4_231", colors)
    # The sprite's shading, two or three steps lighter: the model's own lighting darkens it again.
    ramp = {16: 19, 17: 19, 18: 20, 19: 21, 20: 22, 21: 23, 22: 24, 23: 25, 24: 26, 25: 27, 26: 28,
            27: 29, 28: 29, 29: 29, 30: 29, 31: 29}
    grey = {1: 2, 2: 3, 3: 5, 4: 6, 5: 7, 6: 7, 7: 8, 8: 8, 10: 10, 106: 106, 109: 109, 169: 169}
    gold = lambda i: mats(i, metallic=0.1, roughness=0.55)  # noqa: E731
    metal = lambda i: mats(i, metallic=0.7, roughness=0.3)  # noqa: E731

    def horn_slot(idx):
        if idx in ramp:
            return gold(ramp[idx])
        if idx in grey:
            return gold(18)  # a stud's pixels just off the stud: plain shadowed horn
        return None

    def stud_slot(idx):
        if idx in grey:
            return metal(grey[idx])
        return metal(4)

    sample = sampler(grid)
    under = gold(18)
    bm = bmesh.new()

    # The horn, from its tip at the bottom left up and along to inside the knuckle.
    prof = horn_profile(grid)
    first = lib.sweep(bm, horn_path(prof), sides=14, mat_index=gold(20))
    # The knuckle (columns 114-134, rows 1-19, its lower lobe hanging to a point at column 126) and the thick segment beyond it (columns 134-167,
    # rows 1-21; it runs on past the arm's right edge, where the cut leaves it open).
    lib.cube_blob(bm, (X(124.5), Y(8.0), 0.0), (9.5 * U, 7.5 * U, 0.27), n=7, mat_index=gold(20))
    lib.cube_blob(bm, (X(126.5), Y(13.5), -0.02), (5.0 * U, 6.0 * U, 0.2), n=5, mat_index=gold(20))  # lobe under it
    seg = [(133.3, 10.6, 2.5, 0.08), (133.8, 10.6, 6.0, 0.18), (134.8, 10.8, 8.0, 0.23),
           (136.2, 11.0, 9.3, 0.26), (137.8, 11.3, 10.1, 0.275), (139.5, 11.5, 10.5, 0.28)]
    seg += [(x, 11.5, 10.5, 0.28) for x in (141.5, 143.5, 145.5, 147.5, 149.5, 151.5, 153.5, 155.5, 157.5, 159.5, 161.5, 163.5,
                                       165.5, 167.5, 168.6)]
    lib.sweep(bm, [(X(x), Y(m), 0.0, w * U, h) for x, m, w, h in seg], sides=26, mat_index=gold(20))
    lib.paint(bm, first, sample, horn_slot, under_slot=under)

    # Raised bands round the horn near its root (the bright columns 90, 94 and 104).
    for c in (90, 94, 104):
        m, vh = prof[c]
        w = vh * U
        h = min(0.25, 0.55 * w + 0.005)
        lib.sweep(bm, [(X(c + 0.1), Y(m), 0.0, w * 1.035, h * 1.05), (X(c + 0.9), Y(m), 0.0, w * 1.035, h * 1.05)],
                  sides=14, mat_index=gold(24 if c == 104 else 22))

    # Grey studs along the horn: (column, row) of their centres (pixel edges) and half sizes in px.
    studs = [(42.3, 9.4, 3.2, 2.2), (60.8, 6.4, 2.9, 1.9), (83.2, 4.3, 2.3, 2.3), (98.0, 10.9, 2.2, 2.0),
             (110.4, 2.8, 2.3, 2.0)]
    start = len(bm.faces)
    for c, r, rx, ry in studs:
        z = surface_z(prof, c, r)
        lib.ellipsoid(bm, (X(c), Y(r), z * 0.85), (rx * U, ry * U, 0.08), segments=10, rings=6,
                      mat_index=metal(5))
    lib.paint(bm, start, sampler(grid, skip=(-1,), reach=2), stud_slot, under_slot=metal(4))

    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def main():
    grid, colors, sprites = load()
    obj = build(grid, colors)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprites[PIECES[0]]["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", sprites[name]["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = lib.write_png(grid, colors, Path(tempfile.mkdtemp()) / "arm.png", pad_to=(W, W * 14 // 12))
        common.render_preview([obj], str(out), ref, size=W // 12, view_px=840)
        for name in PIECES:
            data = sprites[name]
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
