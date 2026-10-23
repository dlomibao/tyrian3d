"""Grey ribbed dome (newshi.shp frames 154, 156 and 158, one assembly): a 3D version of its sprites.

Seen in episode 1 (level sections 10, 29 and 38) and level 3.21, on the ground. Three 2x2
enemies side by side (sprite.json `assemblyLayout`) make the lower part of one big dark grey
dome, 72 px across at its top edge and narrowing to a rounded point at the bottom. Light ribs
run over its surface and meet at a small blue-grey hub in front of its crown (newshi-156, column
13, row 16); a second blue-grey rivet sits on the rib to its upper right (newshi-158). The dome
is lit from the top and falls into deep shadow along its lower rim.

The whole dome is built once in assembly coordinates and cut into the three pieces with
common.split_assembly. The sprites stop at their top edge, so the dome is cut flat there.

Run: blender --background --python assets/blender/enemies/assembly-newshi-154.py [-- --preview out.png]
(the preview is the whole dome; each piece also gets <piece>.png next to it).
"""

import math
import statistics
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b069 as lib  # noqa: E402

NAME = "assembly-newshi-154"
ROOT = common.repo_root(__file__)
PIECES = ["newshi-154", "newshi-156", "newshi-158"]
# Assembly pixel (0, 0) is the top-left corner of newshi-154 (screen 114, -31); the three pieces
# make a 72 x 28 px strip whose centre (screen 150, -17, the centre of newshi-156) is the origin.
CX0, CY0 = 150, -17
PX = 1 / 12
H = 1.05  # the dome's height at its crown
APEX = (36.5, -1.0)  # the crown, just inside the top edge (assembly px)
HUB = (37.5, 16.5)  # where the ribs meet


def X(c):
    """Assembly pixel x (edge coordinates: 0 = left edge of column 0) to Blender X."""
    return (c - 36) / 12


def Y(r):
    """Assembly pixel y (edge coordinates) to Blender Y: sprite up is +Y."""
    return (14 - r) / 12


def grid():
    """The three pieces' pixels side by side: 28 rows of 72 palette indices (-1 transparent)."""
    g = [[-1] * 72 for _ in range(28)]
    for i, name in enumerate(PIECES):
        for r, line in enumerate(common.load_sprite(ROOT, name)["frames"][0]["pixels"]):
            for c, v in enumerate(line):
                g[r][i * 24 + c] = v
    return g


def outline(g):
    """The dome's footprint (counter-clockwise, assembly px): the sprites' filled extent row by
    row (smoothed), a rounded bottom, and an arc over the top beyond the cut."""
    left, right = [], []
    for r in range(28):
        xs = [c for c in range(72) if g[r][c] >= 0]
        left.append(min(xs))
        right.append(max(xs) + 1)

    def smooth(v):
        return [sum(v[max(i - 1, 0):i + 2]) / len(v[max(i - 1, 0):i + 2]) for i in range(len(v))]

    left, right = smooth(left), smooth(right)
    pts = []
    # Over the top (beyond the cut), right to left.
    top = [(68.0, -4.0), (62.0, -10.0), (50.0, -13.5), (36.5, -14.5), (23.0, -13.5), (11.0, -10.0), (5.0, -4.0)]
    pts += top
    pts += [(left[r], r + 0.5) for r in range(0, 27, 2)]
    pts += [(left[27] + 0.5, 27.6), (34.0, 28.0), (39.0, 28.0), (right[27] - 0.5, 27.6)]
    pts += [(right[r], r + 0.5) for r in range(26, -1, -2)]
    # Our list runs clockwise in screen space (y down), which is counter-clockwise in Blender.
    return pts


def rim_distance(pts, a, d):
    """Distance from `a` along unit direction `d` to the outline (all in assembly px)."""
    best = None
    n = len(pts)
    for i in range(n):
        p, q = Vector(pts[i]), Vector(pts[(i + 1) % n])
        e = q - p
        den = d.x * e.y - d.y * e.x
        if abs(den) < 1e-9:
            continue
        w = p - a
        t = (w.x * e.y - w.y * e.x) / den
        u = (w.x * d.y - w.y * d.x) / den
        if t > 0 and -1e-6 <= u <= 1 + 1e-6:
            best = t if best is None else min(best, t)
    return best


def height(s):
    """The dome's profile: height at fraction s of the way from the crown to the rim."""
    return H * max(1 - s * s, 0.0) ** 0.55


def surface_z(pts, c, r):
    a = Vector(APEX)
    p = Vector((c, r))
    v = p - a
    if v.length < 1e-6:
        return H
    return height(v.length / rim_distance(pts, a, v.normalized()))


def shade_map(g):
    """Each pixel's shade with the ribs smoothed out: the median index of its 7x7 neighbourhood
    (outline pixels count as the darkest grey)."""
    out = [[2] * 72 for _ in range(28)]
    for r in range(28):
        for c in range(72):
            vals = [max(g[rr][cc], 2) for rr in range(max(r - 3, 0), min(r + 4, 28))
                    for cc in range(max(c - 3, 0), min(c + 4, 72)) if 0 <= g[rr][cc] < 100]
            if vals:
                out[r][c] = int(round(statistics.median(vals)))
    return out


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshi154"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    shades = [2, 3, 4, 5, 6, 7, 8]
    mats = [pal(i, metallic=0.2, roughness=0.5) for i in shades]  # 0-6 dome greys
    mats += [
        pal(8, metallic=0.3, roughness=0.35),  # 7 bright ribs
        pal(7, metallic=0.3, roughness=0.35),  # 8 ribs
        pal(6, metallic=0.3, roughness=0.4),  # 9 ribs in half shadow
        pal(5, metallic=0.3, roughness=0.4),  # 10 ribs in shadow
        pal(4, metallic=0.3, roughness=0.45),  # 11 ribs in deep shadow
        pal(102, metallic=0.5, roughness=0.3, emission_strength=2.0),  # 12 blue-grey hub and rivet
    ]
    RIB8, RIB7, RIB6, RIB5, RIB4, HUBM = range(7, 13)
    g = grid()
    shade = shade_map(g)
    pts = outline(g)
    bm = bmesh.new()

    # The dome: copies of the footprint shrunk towards the crown, rising as they go.
    a = Vector(APEX)
    steps = [1.0, 0.975, 0.94, 0.89, 0.82, 0.73, 0.62, 0.49, 0.34, 0.18]
    rings = []
    for s in steps:
        z = height(s)
        rings.append([bm.verts.new((X(a.x + (x - a.x) * s), Y(a.y + (y - a.y) * s), z)) for x, y in pts])
    crown = bm.verts.new((X(a.x), Y(a.y), H))
    n = len(pts)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    for i in range(n):
        faces.append(bm.faces.new((rings[-1][i], rings[-1][(i + 1) % n], crown)))
    bottom = bm.faces.new(list(reversed(rings[0])))
    bottom.material_index = 0
    for f in faces:
        f.smooth = True
        cen = f.calc_center_median()
        c = int(min(max(cen.x * 12 + 36, 0), 71))
        r = int(min(max(14 - cen.y * 12, 0), 27))
        f.material_index = shades.index(min(max(shade[r][c], 2), 8))

    # The ribs: polylines over the dome from the hub out to the rim (assembly px, pixel centres).
    ribs = [
        (RIB8, [HUB, (37.5, -1.0)]),  # straight up
        (RIB8, [HUB, (36.5, 14.0), (34.5, 11.0), (33.5, 8.5), (32.5, 6.0), (31.5, 4.0), (30.5, 1.0), (30.2, -1.0)]),
        (RIB7, [HUB, (34.0, 14.5), (31.5, 12.5), (24.5, 5.5), (22.5, 2.5), (21.5, 0.5), (21.0, -1.0)]),
        (RIB7, [HUB, (31.0, 15.5), (27.0, 14.3), (24.5, 13.3), (22.0, 12.0), (19.5, 9.5), (16.5, 6.5),
                (14.5, 4.0), (12.5, 1.0), (11.8, -1.0)]),
        (RIB6, [HUB, (41.5, 12.5), (43.5, 10.5), (44.5, 8.5), (45.5, 7.0), (46.5, 5.5), (47.5, 3.5),
                (48.5, 1.0), (49.0, -1.0)]),
        (RIB5, [HUB, (44.0, 14.0), (48.5, 12.5), (51.5, 10.5), (54.5, 7.5), (56.5, 4.5), (58.5, 1.5),
                (59.3, -1.0)]),
        (RIB5, [HUB, (37.5, 27.2)]),  # straight down
        (RIB5, [HUB, (34.5, 17.5), (32.5, 18.5), (31.5, 19.5), (28.5, 20.5), (24.5, 21.2), (21.6, 21.7)]),
        (RIB4, [HUB, (39.5, 19.5), (41.5, 20.5), (43.5, 21.5), (45.5, 22.5), (48.5, 24.0)]),
    ]
    for mat, poly in ribs:
        path = []
        for (c0, r0), (c1, r1) in zip(poly, poly[1:]):
            seg = math.hypot(c1 - c0, r1 - r0)
            k = max(1, int(math.ceil(seg / 2.5)))
            for t in range(k):
                f = t / k
                path.append((c0 + (c1 - c0) * f, r0 + (r1 - r0) * f))
        path.append(poly[-1])
        tube = []
        for c, r in path:
            z = surface_z(pts, c, r)
            tube.append((X(c), Y(r), z + 0.01, 0.75 * PX, 0.035))
        lib.sweep(bm, tube, sides=6, mat=mat)

    # The hub where the ribs meet and the rivet on the rib to its upper right.
    for (c, r), size in ((HUB, 1.3), ((49.5, 1.5), 1.0)):
        z = surface_z(pts, c, r)
        lib.ellipsoid(bm, X(c), Y(r), z + 0.02, size * PX, size * PX, 0.06, mat=HUBM, segments=10, rings=5)

    return lib.to_object(NAME, bm, mats, coll)


def merged_sprite():
    """newshi-154's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, PIECES[0])
    for name in PIECES[1:]:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = lib.composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 72, 84)
        common.render_preview([obj], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
