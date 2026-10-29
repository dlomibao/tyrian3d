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
# The horn, knuckle and segment are round tubes and a ball (the sprite lights their tops and
# shades their lower halves): each is about as tall as it is wide.
ROUND = 0.95
SEAMS = (64.0, 80.0)  # dark seam lines across the horn's plating (sprite columns)


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
        h = ROUND * w + 0.004
        path.append((X(c + 0.5), Y(m), 0.0, w, h))
        c += 1.5 if c > 6 else 1.0
    return path


def surface_z(prof, c, r):
    """Height of the horn's top surface over pixel (c, r) (edge coordinates), 0 off the horn."""
    m, vh = prof[int(c)]
    w = vh * U
    h = ROUND * w + 0.004
    t = (r - m) / vh
    return h * math.sqrt(max(0.0, 1 - t * t))


def box(bm, x0, x1, y0, y1, z0, z1, mat_index, bevel=0.0):
    """An axis-aligned box between Blender coordinates, its edges chamfered by `bevel`."""
    bm.faces.ensure_lookup_table()
    first = len(bm.faces)
    res = bmesh.ops.create_cube(bm, size=1.0)
    for v in res["verts"]:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1
    if bevel > 0:
        vs = set(res["verts"])
        edges = [e for e in bm.edges if e.verts[0] in vs and e.verts[1] in vs]
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=1, affect="EDGES", profile=0.5)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first:]:
        f.material_index = mat_index
    return first


def build(grid, colors):
    coll = common.reset_collection(NAME)
    mats = lib.Mats("nsh4_231", colors)
    gold = lambda i: mats(i, metallic=0.5, roughness=0.35)  # noqa: E731
    metal = lambda i: mats(i, metallic=0.7, roughness=0.3)  # noqa: E731
    body = gold(22)  # one mid tone: the game's light draws the sprite's lit tops and shaded undersides
    bm = bmesh.new()

    # The horn, from its tip at the bottom left up and along to inside the knuckle: a round tube.
    prof = horn_profile(grid)
    first = lib.sweep(bm, horn_path(prof), sides=16, mat_index=body)
    horn_end = len(bm.faces)
    # The knuckle (columns 114-134, rows 1-19, its lower lobe hanging to a point at column 126): a
    # ball, and the thick segment beyond it (columns 134-167, rows 1-21; it runs on past the arm's
    # right edge, where the cut leaves it open): a round cylinder with a rounded shoulder.
    lib.cube_blob(bm, (X(124.5), Y(8.0), 0.0), (9.5 * U, 7.5 * U, 7.6 * U), n=8, mat_index=body)
    lib.cube_blob(bm, (X(125.6), Y(13.2), -0.05), (5.4 * U, 6.2 * U, 4.6 * U), n=6, mat_index=body)  # lobe under it
    seg = [(133.3, 10.6, 2.5), (133.8, 10.6, 6.0), (134.8, 10.8, 8.0),
           (136.2, 11.0, 9.3), (137.8, 11.3, 10.1), (139.5, 11.5, 10.5)]
    seg += [(x, 11.5, 10.5) for x in (141.5, 143.5, 145.5, 147.5, 149.5, 151.5, 153.5, 155.5, 157.5, 159.5, 161.5,
                                      163.5, 165.5, 167.5, 168.6)]
    lib.sweep(bm, [(X(x), Y(m), 0.0, w * U, ROUND * w * U) for x, m, w in seg], sides=24, mat_index=body)

    # Dark seams across the horn's plating.
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first:horn_end]:
        col = f.calc_center_median().x / U + W / 2
        if any(abs(col - s) < 0.8 for s in SEAMS):
            f.material_index = gold(17)

    # Raised bands round the horn near its root (the bright columns 90, 94 and 104).
    for c in (90, 94, 104):
        m, vh = prof[c]
        w = vh * U
        h = ROUND * w + 0.004
        lib.sweep(bm, [(X(c + 0.05), Y(m), 0.0, w * 1.06, h * 1.06), (X(c + 0.95), Y(m), 0.0, w * 1.06, h * 1.06)],
                  sides=16, mat_index=gold(27 if c == 104 else 25))

    # A thin rod along the lower flank of the horn's root (the lit line on row 12, columns 68-117).
    rail = []
    for c in range(68, 118, 3):
        z = surface_z(prof, c + 0.5, 12.0)
        rail.append((X(c + 0.5), Y(12.25), z * 0.9, 0.75 * U, 0.75 * U))
    lib.sweep(bm, rail, sides=8, mat_index=gold(24))

    # Grey clamps on the horn: (col0, col1, row0, row1) in pixel edges. Each is a hard box from the
    # horn's centre line to a little above its surface, so it wraps the upper half of the tube.
    bm.faces.ensure_lookup_table()
    flat_from = len(bm.faces)
    clamps = [(39.0, 45.5, 7.0, 12.5, 5), (58.0, 63.5, 4.8, 9.5, 5), (80.8, 85.5, 2.0, 7.5, 6),
              (108.0, 112.5, 0.8, 4.6, 106)]
    for c0, c1, r0, r1, idx in clamps:
        top = max(surface_z(prof, c, r) for c in (c0, (c0 + c1) / 2, c1 - 0.1) for r in (r0, (r0 + r1) / 2, r1))
        box(bm, X(c0), X(c1), Y(r1), Y(r0), -0.02, top + 1.3 * U, metal(idx), bevel=0.35 * U)
    # The dark port on the root's lower flank (columns 96-99, rows 8-12): a grey frame, dark inside.
    pz = max(surface_z(prof, c, r) for c in (95.5, 97.5, 99.5) for r in (7.8, 10.0, 12.2))
    for c0, c1, r0, r1 in ((95.5, 100.0, 7.6, 8.4), (95.5, 100.0, 11.8, 12.6), (95.5, 96.3, 7.6, 12.6),
                           (99.2, 100.0, 7.6, 12.6)):
        box(bm, X(c0), X(c1), Y(r1), Y(r0), 0.0, pz + 1.0 * U, metal(5))
    box(bm, X(96.3), X(99.2), Y(11.8), Y(8.4), 0.0, pz + 0.15 * U, metal(1))

    obj = common.mesh_object(NAME, bm, mats.list, coll, smooth=True)
    for poly in obj.data.polygons[flat_from:]:
        poly.use_smooth = False  # the clamps and port are hard, flat-faced metal
    return obj


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
