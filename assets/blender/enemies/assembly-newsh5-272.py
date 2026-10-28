"""Brain creature's underside (newsh5.shp frames 272, 274, 276: an assembly of three pieces): a 3D
version of its sprites.

Seen in episode 4 (level 22), under a brain made of other pieces. Three 2x2 enemies side by side
make one 72x28 px object: a dark, lumpy red mass across the top that narrows downwards, two
glossy blue eye lobes in the middle of its lower edge, and dark red tendrils hanging below: a
strut and a strand down each side into two loops whose inner sides converge under the eyes.

The mass is a heightfield over its pixels, 5-9 px thick: rounded, elongated lobe domes placed on
the sprite's lobes and leaning in towards the eyes like a fan (a back and a front row, the
brightest pair either side of the centre and the centre itself highest), with valleys between them, rounding off towards the outline with no deck or wall.
The eyes are glossy blue balls about 9 px tall, turned to follow the sprite's leaning eyes; the
tendrils are round tubes about 2-3 px thick, the loops traced along the sprite's own tubes, the struts from the
eyes' sides (about 5 px up) down to the loops, and a low dark web between the loops' inner sides.
The lower parts are mirror symmetric about pixel column 36. Built whole in assembly coordinates and
cut into the three pieces with common.split_assembly. One frame each.

Each part is one mid-tone colour (the sprite's bright crests, pale eye spots, dark creases and dark
rims are its drawn light and outline, which the game's lights and outline make): the mass moist
flesh with a soft sheen that shows its lobes (metallic 0, roughness 0.6), the tendrils matte flesh
(0, 0.9), the eyes wet and glossy (0.05, 0.1).

Run: blender --background --python assets/blender/enemies/assembly-newsh5-272.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b029 as lib  # noqa: E402

NAME = "assembly-newsh5-272"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-272", "newsh5-274", "newsh5-276"]
AXIS = 36  # the lower parts are mirror symmetric about the centre of this column
PX = lib.PX


def build(colors, pixels, grid):
    coll = common.reset_collection(NAME)
    sprite = {"name": NAME, "colors": colors}
    h, w = len(pixels), len(pixels[0])
    X, Y = grid.X, grid.Y

    # One palette material per sprite index used; each part takes its mid-tone, which the game's
    # lights shade.
    MASS_RED = 67  # mid-tone of the mass (sprite 64-72; its lobes 67-70)
    TUBE_RED = 69  # mid-tone of the tendrils (bright crest 70-72, dark flanks 65-67)
    EYE_BLUE = 54  # mid-tone of the eyes (48-59)
    mats, slot = [], {}

    def mat(i):
        if i not in slot:
            # Materials (the game keeps them, the palette gives the colour): the eyes are wet,
            # glossy lobes (their pale spot is shine, made by the light); the mass and tendrils
            # are flesh, matte, their bright pixels lit faces of the modelled lobes and tubes.
            if 48 <= i <= 63:
                kw = dict(metallic=0.05, roughness=0.1)
            elif i == MASS_RED:  # moist flesh: a soft sheen on the lobe tops shows their shape
                kw = dict(metallic=0.0, roughness=0.6)
            else:
                kw = dict(metallic=0.0, roughness=0.9)
            slot[i] = len(mats)
            mats.append(common.palette_material(sprite, i, "ns5b272", **kw))
        return slot[i]

    def is_blue(i):
        return 48 <= i <= 63

    def red_slot(i):
        return mat(i) if i == 1 or 64 <= i <= 79 else None

    bm = bmesh.new()
    part = bm.faces.layers.int.new("part")  # 1 = tendril tube (for colouring after the mirror)

    # ---- the mass across the top (rows 0-12): a heightfield of packed lobes ----
    # Each pixel is split into SUB x SUB quads; the height follows the sprite's shading (its
    # lobes are bright, the creases between them dark), rounded off towards the outline so the
    # mass has no wall or deck, and the underside is one flat face at Z0.
    SUB = 1
    Z0 = -0.05
    MASS_ROWS = 13
    inside = [[r < MASS_ROWS and pixels[r][c] >= 0 for c in range(w)] for r in range(h)]

    def level(v):
        if 64 <= v <= 79:
            return v - 64
        if v == 1:
            return -1.0
        if is_blue(v):
            return 1.5
        return 0.0

    # Gaussian-smoothed shading level over the mass.
    sig = 2.0
    ker = [(dr, dc, math.exp(-(dr * dr + dc * dc) / (2 * sig * sig))) for dr in range(-3, 4) for dc in range(-3, 4)]

    def smooth_level(fr, fc):
        """Shading level at fractional pixel position (row, col) (pixel centres at .5)."""
        tot = wt = 0.0
        r0, c0 = int(math.floor(fr)), int(math.floor(fc))
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                r, c = r0 + dr, c0 + dc
                if 0 <= r < h and 0 <= c < w and inside[r][c]:
                    d2 = (r + 0.5 - fr) ** 2 + (c + 0.5 - fc) ** 2
                    k = math.exp(-d2 / (2 * sig * sig))
                    tot += k * level(pixels[r][c])
                    wt += k
        return tot / wt if wt else 0.0

    # Lattice vertices at pixel-edge coordinates (col, row) in steps of 1/SUB.
    cells = [(r * SUB + i, c * SUB + j) for r in range(h) for c in range(w) if inside[r][c]
             for i in range(SUB) for j in range(SUB)]
    cellset = set(cells)
    corners = set()
    for (a, b) in cells:
        corners |= {(a, b), (a + 1, b), (a, b + 1), (a + 1, b + 1)}

    def on_boundary(a, b):
        return not all(n in cellset for n in ((a - 1, b - 1), (a - 1, b), (a, b - 1), (a, b)))

    boundary = [k for k in corners if on_boundary(*k)]
    # (col, row) in px of the outline, less the straight top edge (row 0), which rounds off
    # over a longer run so the back of the mass slopes away instead of standing as a wall.
    bpts = [(b / SUB, a / SUB) for a, b in boundary if a > 0]
    EDGE_TOP = 3.0
    EDGE = 4.0  # px over which the mass rounds off at its outline
    BASE = 4.5  # px: the mass's body under the lobes (the creases between them)
    # The lobes: rounded, elongated domes laid out on the sprite's own lobes, which lean in towards
    # the eyes like a fan: a back row along the top edge, a lower front row, and one on the centre
    # line behind the eyes, the highest. (pixel col, pixel row, radius along, radius across, height
    # above BASE in px, angle of the long axis in degrees from +col towards +row); the right side
    # is the mirror image about column AXIS. The brightest pair, either side of the centre, stands
    # highest of the back row.
    LOBES_L = [
        # back row: the sprite's lobes lean in towards the eyes, fanning out from the centre
        (3.0, 1.0, 4.4, 3.2, 2.8, 30), (11.0, 2.3, 5.8, 3.4, 3.8, 40), (17.2, 1.4, 4.4, 3.1, 3.4, 55),
        (22.0, 2.6, 5.0, 3.2, 3.9, 80), (26.8, 1.6, 4.6, 3.0, 3.7, 35),
        (31.0, 3.4, 4.8, 3.4, 4.6, 70),  # the brightest pair, either side of the centre
        # front row, lower and smaller
        (15.5, 7.6, 5.0, 3.2, 3.3, 25), (22.0, 7.0, 4.8, 3.2, 3.5, 50), (28.2, 6.6, 4.2, 3.2, 3.4, 60),
    ]
    LOBES = [(36.0, 6.0, 4.8, 3.6, 5.0, 90)]  # the centre, behind the eyes, highest
    for c, r, ra, rb, amp, ang in LOBES_L:
        LOBES += [(c, r, ra, rb, amp, ang), (2 * AXIS - c, r, ra, rb, amp, 180 - ang)]
    LOBES = [(c + 0.5, r + 0.5, ra, rb, amp, math.cos(math.radians(a)), math.sin(math.radians(a)))
             for c, r, ra, rb, amp, a in LOBES]  # pixel centres

    def lobes(col, row):
        """Height (px) of the lobes over BASE: a soft elongated dome per lobe (long axis ra along
        its angle, rb across), joined by a soft maximum so the creases between them are rounded
        valleys rather than cracks."""
        tot = 0.0
        for c, r, ra, rb, amp, ca, sa in LOBES:
            dx, dy = col - c, row - r
            u, v = dx * ca + dy * sa, -dx * sa + dy * ca
            d2 = (u / ra) ** 2 + (v / rb) ** 2
            if d2 < 1.0:
                tot += (amp * (1.0 - d2) ** 0.9) ** 5
        return tot ** (1 / 5)

    top_v, bot_v = {}, {}
    for (a, b) in corners:
        col, row = b / SUB, a / SUB
        x, y = (col - w / 2) / 12, (h / 2 - row) / 12
        if on_boundary(a, b):
            v = bm.verts.new((x, y, Z0))
            top_v[(a, b)] = bot_v[(a, b)] = v
            continue
        d = min(math.hypot(col - pc, row - pr) for pc, pr in bpts)
        e = min(d / EDGE, 1.0)
        edge = math.sqrt(max(1 - (1 - e) ** 2, 0.0))
        edge *= math.sin(min(row / EDGE_TOP, 1.0) * math.pi / 2)
        # A little of the sprite's shading on top (bright pixels slightly higher), smoothed wide
        # so it only tilts the lobes, never crinkles them.
        s = smooth_level(row, col)
        shade = min(max((s - 1.0) / 4.0, 0.0), 1.0)
        z = Z0 + edge * (BASE + lobes(col, row) + 0.6 * shade) * PX
        top_v[(a, b)] = bm.verts.new((x, y, z))
        bot_v[(a, b)] = bm.verts.new((x, y, Z0))
    nt = len(bm.faces)
    for (a, b) in cells:
        q = [(a, b), (a + 1, b), (a + 1, b + 1), (a, b + 1)]  # row down, col right
        f = bm.faces.new([top_v[k] for k in reversed(q)])
        f.smooth = True
        # One mid-tone red over the whole mass: the sprite's bright lobes and dark creases are
        # its drawn light on the lobes modelled here, and its dark rim the outline the game draws.
        f.material_index = mat(MASS_RED)
    # Round off the pixel staircase of the outline (two passes along the boundary loop).
    bm.faces.ensure_lookup_table()
    tf = set(bm.faces[nt:])
    nbr = {}
    for f in tf:
        for e in f.edges:
            if sum(1 for g in e.link_faces if g in tf) == 1:
                a_, b_ = e.verts
                nbr.setdefault(a_, []).append(b_)
                nbr.setdefault(b_, []).append(a_)
    for _ in range(2 * SUB):
        new = {}
        for v, ns in nbr.items():
            if len(ns) == 2:
                m = (ns[0].co + ns[1].co) / 2
                new[v] = v.co.lerp(m, 0.5)
        for v, co in new.items():
            v.co.x, v.co.y = co.x, co.y
    nb = len(bm.faces)
    bottom = []
    for (a, b) in cells:
        q = [(a, b), (a + 1, b), (a + 1, b + 1), (a, b + 1)]
        f = bm.faces.new([bot_v[k] for k in q])
        f.material_index = mat(64)
        f.smooth = False
        bottom.append(f)
    bmesh.ops.dissolve_faces(bm, faces=bottom, use_verts=True)

    # ---- the lower parts: left half, mirrored below ----
    start = len(bm.verts)

    def tube(points, half_w, mat_i, n=10, closed=False, half_h=None):
        curve = lib.catmull([(X(c), Y(r), z) for c, r, z in points], n, closed=closed)
        hh = (half_h if half_h is not None else half_w) * PX
        sec = [(p.x, p.y, p.z, half_w * PX, hh) for p in curve]
        if not closed:
            sec[0] = (*sec[0][:3], half_w * PX * 0.8, hh * 0.8)
        n0 = len(bm.faces)
        lib.sweep(bm, sec, sides=8, mat=mat_i, closed=closed)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n0:]:
            f[part] = 1

    TUBE = mat(TUBE_RED)
    # Strut from the mass down to the loop (columns 11-23, rows 11-21).
    tube([(12.6, 10.0, -0.02), (13.4, 14.0, -0.03), (15.4, 17.0, -0.03), (18.0, 18.9, -0.03),
          (21.5, 19.6, -0.03), (24.6, 21.0, -0.03)], 1.6, TUBE, n=12)
    # Thin strand hanging straight down from the mass (column 20, rows 11-19).
    tube([(20.0, 9.5, -0.02), (20.0, 14.0, -0.03), (20.3, 17.0, -0.03), (21.5, 19.3, -0.03)], 1.45,
         TUBE, n=8)
    # The loop (columns 24-35, rows 15-26), traced along the sprite's own tube: narrow at its top
    # under the eye, wider at its bottom, its inner side running down beside the centre line
    # (column 35 at rows 20-22, where it and its mirror twin make the two converging lines of the
    # stem) and round into the bottom at row 25. Its top rises to meet the strut under the eye.
    RING = [(28.6, 13.9), (30.6, 14.4), (32.1, 16.1), (32.9, 17.8), (33.5, 19.3), (34.0, 20.7),
            (34.1, 22.0), (33.5, 23.4), (32.2, 24.5), (30.2, 25.0), (28.2, 24.6), (26.4, 23.6),
            (25.0, 22.2), (24.5, 20.6), (24.8, 18.8), (25.4, 17.0), (26.5, 15.1)]
    ring = [(c, r, -0.04 + 0.05 * max(0.0, (19.0 - r) / 4.0)) for c, r in RING]
    tube(ring, 1.65, TUBE, n=28, closed=True)
    # Strut from the eye's side down to the loop's top-left (the dark pieces beside the eye): a
    # 2 px round tube that leaves the ball about 5 px up and slopes down onto the loop.
    tube([(29.8, 13.4, 0.48), (27.6, 14.6, 0.42), (26.2, 15.8, 0.32), (25.2, 17.4, 0.06)], 1.15, TUBE, n=8)

    # Eye lobe (columns 28-35, rows 8-17): a glossy ball sitting on the mass.
    # The sprite's eye leans: wide at its top-left, running down to a point at the lower right, so
    # the ball is turned 35 degrees to follow it.
    lib.ellipsoid(bm, (X(31.9), Y(12.6), Z0 + 4.8 * PX), (4.6 * PX, 5.4 * PX, 4.9 * PX), mat=mat(EYE_BLUE),
                  segments=24, rings=12, angle=math.radians(35))

    lib.mirror_since(bm, start, X(AXIS))

    # Between the two converging lines of the stem the sprite is dark (column 36, rows 15-24): a
    # low, thin dark web on the axis, which reads as the shadow between them rather than a strand.
    n0 = len(bm.faces)
    tube([(AXIS, 15.0, -0.01), (AXIS, 19.5, -0.03), (AXIS, 24.4, -0.045)], 0.95, mat(65), n=5, half_h=0.6)
    # where the lines leave the eyes (rows 16-20) the dark between them is wider
    tube([(AXIS, 15.5, -0.01), (AXIS, 18.0, -0.02), (AXIS, 20.4, -0.03)], 1.7, mat(65), n=4, half_h=0.6)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f[part] = 2

    # Eyes and tendrils in their mid-tones: the sprite's crests, pale spots and dark flanks are
    # its drawn light and outline, which the game's lights and outline make on the model.
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    for f in bm.faces:
        if f[part] == 1:
            f.material_index = mat(TUBE_RED)
    return lib.to_object(NAME, bm, mats, coll)


def flat_cut_faces(obj):
    """The faces split_assembly fills the cuts with stand on the piece's box sides; shade them flat
    so they don't bend the smooth normals of the surface along the cut (a dark seam from above)."""
    hw = 1.0
    for poly in obj.data.polygons:
        xs = [obj.data.vertices[i].co.x for i in poly.vertices]
        if abs(poly.normal.x) > 0.9 and all(abs(abs(x) - hw) < 1e-4 for x in xs):
            poly.use_smooth = False
    

def main():
    pixels, colors, w, h, (sx0, sy0), layout = lib.assembly_pixels(ROOT, PIECES)
    grid = lib.Grid(w, h)
    obj = build(colors, pixels, grid)
    cx0, cy0 = sx0 + w / 2, sy0 + h / 2
    pieces = common.split_assembly(obj, [(n, layout[n][0] - cx0, layout[n][1] - cy0) for n in PIECES])
    for name in PIECES:
        flat_cut_faces(pieces[name])
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.write_png(Path(tempfile.mkdtemp()) / "assembly.png", pixels, colors)
        common.render_preview([obj], str(out), str(ref), size=(w, h), view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
