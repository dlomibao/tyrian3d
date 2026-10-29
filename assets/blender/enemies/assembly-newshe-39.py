"""Rock outcrop (newshe.shp frames 1, 3, 5, 39, 41, 43; an assembly of 6 pieces): a 3D version of
its sprites.

Seen in episode 1 (levels 1.28 and 1.3) and episode 3 (3.17). Six 2x2 ground enemies side by side
(three across, two down; sprite.json `assemblyLayout`) make one 72 x 56 px heap of grey boulders on
brown dirt, lit from the top left: a big flat-topped block at the back (upper right) with a bright
edge down its left side, smaller boulders to its left, splintered shards below it, and a dark
shadow on the ground in front of them all.

The heap is built once in assembly coordinates, remodelled on the concept
(assets/blender/features/concepts/assembly-newshe-39.jpg, registered to the sprite by
tools/concept_maps.py) as hard columnar basalt: the big block is two large flat-topped slabs split by
the fissure, its lower-left edge one straight chamfer catching the light (the lit ridge); smaller
blocks with chamfered rims step down to the left, and in front the block's steep dark front faces,
the front boulder and two pointed splinters are low with tops tilting down the screen (SLABS,
COLUMNS). The blocks set only the geometry: every face is cut on a 2 px grid and takes the sprite's
shade under it, so texture_bake.py's concept detail (cracks, weathering) lands on the matching
block; low dark rubble fills the crevices. It is
cut into the six pieces with common.split_assembly, and each piece gets a flat patch of dirt and
shadow under it, painted from its sprite in 2 x 2 px cells.

Run: blender --background --python assets/blender/enemies/assembly-newshe-39.py [-- --preview out.png]
(the preview is the whole heap; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b134 as lib  # noqa: E402

NAME = "assembly-newshe-39"
ROOT = common.repo_root(__file__)
PIECES = ["newshe-1", "newshe-3", "newshe-5", "newshe-39", "newshe-41", "newshe-43"]
# Assembly pixel (0, 0) is the top-left pixel of newshe-1 (screen 224 - 12, -18 - 14); the heap is
# 72 x 56 px and its centre (screen 248, -4) is the Blender origin.
SX0, SY0 = 212, -32
CX0, CY0 = 248, -4

ROCK = set(range(4, 12))  # the grey ramp of the boulders
CREVICE = {2, 3}


# Remodelled on the concept (assets/blender/textures/assembly-newshe-39/concept.png, the concept
# registered to the sprite) as hard columnar basalt: flat-topped prisms with a chamfered rim and steep
# sides. The big block at the back is two large slabs split by the fissure (col ~45.5), the only deep
# seam: a V groove about 4-5 px deep. The left slab's lower-left edge is one straight chamfer along the
# sprite's lit ridge (col 29, row 5 to col 41, row 14), with the dark left face falling away below it.
# In front of it the concept draws the block's steep dark front faces in perspective: the front
# boulder, the slab and the two splinters are low (2-7 px) and their tops tilt down towards the screen
# bottom; the splinters are narrow wedges with pointed lower ends. The row of blocks on the left steps
# down to the left (9 to 7 px). Every face is then cut on a 2 px grid and painted with the sprite's
# shade under it (geometry from the blocks, light and dark from the sprite).
#
# Main slabs: top face [(col, row)] at z px, and the footprint on the ground [(col, row)].
SLABS = {
    "block-left": ([(29, 5), (33, 2.4), (38, 1), (44.5, 0.4), (44.5, 14.6), (41, 14.2)], 14.0,
                   [(27.4, 4.6), (32, 1.8), (38, 0.3), (46.6, 0), (46.6, 20.2), (43, 20.6), (36, 18.8),
                    (30, 16.2), (27.4, 12)]),
    "block-right": ([(47, 0.6), (50, 0.8), (56, 3), (59, 6.4), (59.6, 11.5), (57, 14), (52, 14.6),
                     (47, 14.6)], 12.5,
                    [(44.4, 0), (50, 0), (56, 2), (62, 5), (65.6, 9), (65.6, 16), (62, 20), (52, 21.2),
                     (44.4, 20.6)]),
}
LIT_RIDGE = ((29, 5), (41, 14.2))  # the left slab's lit edge (sprite's bright diagonal)
LIT = 11  # its shade: the sprite's lightest rock grey
# Smaller blocks: top face [(col, row)], height at the top face's back (upper) edge and at its front
# (lower) edge in px (a tilted top when they differ), lean (px the foot reaches further down).
COLUMNS = {
    # Front boulder: part of the big block's front face, tilting down to the screen bottom.
    "front-boulder": ([(46, 16.6), (52, 15.6), (58, 16.4), (60.6, 19.6), (58.4, 24.5), (53.5, 28.4),
                       (48.5, 29.2), (45.4, 24.5)], 6.5, 3.0, 1.5),
    "splinter-r": ([(52.5, 27.5), (57, 23.5), (60.4, 20.4), (61, 23), (57.6, 30), (53.6, 33.8),
                    (50.8, 33)], 3.0, 1.2, 0.5),
    "chip": ([(45.6, 31), (48, 29.8), (51, 30.4), (50.6, 33.6), (47.2, 35.6)], 2.0, 1.0, 0.3),
    # Shards below the block: a low tilted slab and two narrow splinters tapering to a point.
    "slab": ([(29.6, 20.8), (36, 19.6), (38, 21.5), (37.6, 28.5), (31, 29.6), (29.4, 26)], 5.0, 2.5,
             1.0),
    "shard-lit": ([(38, 20.6), (44.4, 20.2), (45, 23.5), (42.5, 30), (40.2, 37.8), (38.4, 31)], 6.0,
                  1.2, 0.6),
    "splinter": ([(30, 29.8), (36.6, 29), (39, 31.5), (38, 36.5), (35.4, 41.8), (31, 35.5)], 4.5, 1.0,
                 0.5),
    # The row of blocks left of the big one, stepping down to the left.
    "between": ([(23.6, 14), (29, 13.2), (31.4, 16), (30.6, 21), (26, 21.4), (24.2, 18)], 9.0, 9.0, 2.0),
    "bright": ([(15.6, 19.4), (21, 17.6), (26.4, 18.6), (27.4, 22), (25, 25.4), (17, 25.6)], 8.5, 8.5,
               2.5),
    "upper-left": ([(7.5, 15.4), (13, 12.2), (21.5, 11.2), (23, 13.2), (21, 16.6), (10, 17.8)], 8.0,
                   8.0, 1.5),
    "left": ([(1.2, 20), (5, 17.6), (14, 17.6), (15, 21), (13.5, 25), (3, 25)], 7.0, 7.0, 2.5),
}
CHAMFER = 0.8  # px: the crisp bevel round each block's top (the concept's lit rims)
RIDGE_CHAMFER = 1.3  # px: the wider bevel along the lit ridge
FLARE = 1.0  # px the foot spreads beyond the rim
STEP = 2  # px between the cuts that let the faces take the sprite's shading


def offset(poly, d, d_edge=None):
    """The convex polygon `poly` [(col, row)] with every edge moved d px outwards (edge i, from
    vertex i to i + 1, by d_edge[i] when given): the parallel rim of a chamfer."""
    import math
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    lines = []
    for i in range(n):
        (c1, r1), (c2, r2) = poly[i], poly[(i + 1) % n]
        L = math.hypot(c2 - c1, r2 - r1)
        nc, nr = sgn * (r2 - r1) / L, -sgn * (c2 - c1) / L  # outward normal
        k = d_edge[i] if d_edge else d
        lines.append(((c1 + nc * k, r1 + nr * k), (c2 - c1, r2 - r1)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    return out


def tilt(poly, zb, zf):
    """Heights for a top face that falls from zb px at its back (upper) edge to zf at its front."""
    r0, r1 = min(r for _, r in poly), max(r for _, r in poly)
    return [zb - (zb - zf) * (r - r0) / ((r1 - r0) or 1) for _, r in poly]


def slab(bm, grid, top, zpx, foot):
    """One of the big block's two halves: flat top, chamfered rim (wider along the lit ridge), and
    steep faces down to its footprint."""
    widths = []
    for i in range(len(top)):
        edge = (top[i], top[(i + 1) % len(top)])
        widths.append(RIDGE_CHAMFER if set(edge) == set(LIT_RIDGE) else CHAMFER)
    rim = offset(top, 0, widths)
    pts = [(c, r, zpx * lib.U) for c, r in top]
    pts += [(c, r, (zpx - w) * lib.U) for (c, r), w in zip(rim, [max(a, b) for a, b in
                                                                   zip(widths, widths[-1:] + widths[:-1])])]
    return lib.rock(bm, grid, foot, pts)


def column(bm, grid, top, zb, zf, lean):
    """A smaller block: a (possibly tilted) top, a chamfered rim, steep sides down to a foot that
    reaches `lean` px further down the screen."""
    zs = tilt(top, zb, zf)
    ch = min(CHAMFER, 0.35 * zf)
    pts = [(c, r, z * lib.U) for (c, r), z in zip(top, zs)]
    pts += [(c, r, (z - ch) * lib.U) for (c, r), z in zip(offset(top, ch), zs)]
    foot = offset(top, ch + FLARE) + [(c, r + lean) for c, r in offset(top, ch + FLARE * 0.5)]
    return lib.rock(bm, grid, foot, pts)


def near_ridge(c, r, tol):
    """Whether (col, row) lies within tol px of the lit ridge segment."""
    (c1, r1), (c2, r2) = LIT_RIDGE
    dc, dr = c2 - c1, r2 - r1
    t = max(0.0, min(1.0, ((c - c1) * dc + (r - r1) * dr) / (dc * dc + dr * dr)))
    return ((c - c1 - t * dc) ** 2 + (r - r1 - t * dr) ** 2) ** 0.5 <= tol


def boulders(bm, grid):
    # Low rubble under the heap, filling the gaps between the blocks (the dark crevices).
    lib.block_rock(bm, grid, [(0.5, 23), (5, 16), (14, 11.5), (26, 11.5), (31, 14), (31, 32), (20, 33),
                              (8, 31), (1, 29.5)], 0.2, inset=5.0)
    lib.block_rock(bm, grid, [(28, 16), (64, 16), (64.5, 22), (60, 30), (50, 35), (40, 41.5), (33, 42),
                              (28, 33)], 0.24, inset=6.0)
    for top, z, foot in SLABS.values():
        slab(bm, grid, top, z, foot)
    for top, zb, zf, lean in COLUMNS.values():
        column(bm, grid, top, zb, zf, lean)


def build(colors, grid):
    coll = common.reset_collection(NAME)
    mats = lib.Mats("nshe39", colors)
    rock = lambda i: mats(i, metallic=0.15, roughness=0.75)  # noqa: E731
    (rc1, rr1), (rc2, rr2) = LIT_RIDGE
    ridge_dir = ((rr2 - rr1), (rc2 - rc1))  # outward normal of the ridge in Blender X/Y: (-, -)
    import math
    k = math.hypot(*ridge_dir)
    ridge_n = (-ridge_dir[0] / k, -ridge_dir[1] / k)

    def rock_slot(idx, face):
        n = face.normal
        if n.z < -0.3:
            return mats(3)
        cen = face.calc_center_median()
        c, r = cen.x / lib.U + grid.w / 2 - 0.5, grid.h / 2 - cen.y / lib.U - 0.5
        # The lit ridge: the chamfer along the left slab's lower-left edge, one crisp light line.
        if 0.45 < n.z < 0.95 and cen.z > 11 * lib.U and near_ridge(c, r, 1.6):
            h = math.hypot(n.x, n.y) or 1
            if (n.x * ridge_n[0] + n.y * ridge_n[1]) / h > 0.8:
                return rock(LIT)
        if idx in ROCK:
            return rock(idx)
        if idx in CREVICE:
            return mats(idx, metallic=0.1, roughness=0.9)
        return rock(4)  # side faces over the ground and shadow

    bm = bmesh.new()
    boulders(bm, grid)
    lib.slice_grid(bm, grid, step=STEP)
    bm.normal_update()
    lib.paint(bm.faces[:], grid, rock_slot)
    for f in bm.faces:
        f.smooth = False
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats.list:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj, mats


def add_ground(piece, grid, mats, ox, oy):
    """Lay the patch of ground under piece (top-left assembly pixel ox, oy) into its mesh."""
    def slot(idx):
        if idx == -2:
            return mats(17, roughness=0.95, metallic=0.0)
        if idx in ROCK or idx in CREVICE:
            return mats(idx if idx in CREVICE else 3, metallic=0.1, roughness=0.9)
        return mats(idx, metallic=0.0, roughness=0.95)

    bm = bmesh.new()
    bm.from_mesh(piece.data)
    lib.ground_tile(bm, grid, ox, oy, slot)
    piece.data.materials.clear()
    for m in mats.list:
        piece.data.materials.append(m)
    bm.to_mesh(piece.data)
    bm.free()


def main():
    first = common.load_sprite(ROOT, PIECES[0])
    layout = [(e["model"], e["cx"], e["cy"]) for e in first["assemblyLayout"]]
    corners = [(n, cx - 12 - SX0, cy - 14 - SY0) for n, cx, cy in layout]
    pixels, w, h, colors = lib.assembly_pixels(ROOT, corners)
    grid = lib.Grid(w, h, pixels)
    obj, mats = build(colors, grid)
    pieces = common.split_assembly(obj, [(n, cx - CX0, cy - CY0) for n, cx, cy in layout])
    for name, ox, oy in corners:
        add_ground(pieces[name], grid, mats, ox, oy)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        piece = pieces[name]
        print(f"{name}: {len(piece.data.polygons)} faces")
        common.export_sprite_model(ROOT, [piece], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.pixels_png(pixels, colors, Path(tempfile.mkdtemp()) / "assembly.png", pad_to=(72, 84))
        # The whole heap, its pieces laid out in place, beside the composite sprite.
        whole = []
        for name, ox, oy in corners:
            p = pieces[name]
            p.location = ((ox + 12 - w / 2) / 12, (h / 2 - oy - 14) / 12, 0)
            whole.append(p)
        bpy.context.view_layer.update()
        common.render_preview(whole, str(out), ref, size=6, view_px=640)
        for p in whole:
            p.location = (0, 0, 0)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
