"""Glass orb (newshu.shp, four 2x2 pieces: newshu-91, -93 top, newshu-129, -131 bottom): a 3D
version of its sprites, built whole and cut into the four pieces.

Seen in episode 1 (level section 19), episode 3 and episode 4. A big glass ball with green
organic machinery inside: a large lumpy mass on the left with a glowing core, a small glowing bud
at the top, a lobe on the right, a lamp at the lower right fed by a vein, ribs curving round the
bottom (its dark rim and the bright crescent on its lower-right edge are the glass catching light,
not shapes). The animation changes its whole colour,
not its shape, so each piece gets three models that share the geometry:

- <piece>: dim grey glass (the first frame and the last frame of the fade),
- <piece>-f2: glowing green (lit up, and the first fade steps, which are still mostly green),
- <piece>-f3: a closed, smooth purple shell (one frame).

Within the grey and green states the orb fades: lit up it goes from bright green through duller
greens to grey-green, its core turning pale blue, and the grey state's last frame keeps a green
tinge. Each part's material follows that fade frame by frame (common.palette_material frames=),
taking on every frame the colour that the sprite shows where that part's colour was on the state's
first frame (see frame_colours).

Run: blender --background --python assets/blender/enemies/assembly-newshu-129.py [-- --preview out.png]
(the preview shows the whole orb; out-f2.png and out-f3.png show the green and purple states)
[--frames <dir>] (renders every frame of each grey and green piece beside its sprite, one PNG each).
"""

import math
import sys
from collections import Counter
from pathlib import Path

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b005 as lib  # noqa: E402

NAME = "assembly-newshu-129"
ROOT = common.repo_root(__file__)
W, H = 48, 56  # the four pieces' 2x2 block, in sprite px
# Each piece's centre relative to the block's centre, in screen px (sprite.json assemblyLayout:
# newshu-91 at (225, 75), -93 at (249, 75), -129 at (225, 103), -131 at (249, 103)).
PIECES = [("newshu-91", -12, -14), ("newshu-93", 12, -14), ("newshu-129", -12, 14), ("newshu-131", 12, 14)]

NPARTS = 10
SHELL, ORGAN, LOBE, CORE, RIB, LAMP, RIM, DARK, MID, GLOW = range(NPARTS)
# Palette index per part and state (grey/green indices correspond pixel for pixel in the sprites).
STATES = {
    # Grey: the pale-blue spot and its halo (CORE, RIM) are the glass's specular highlight, so they
    # take the lumpy mass's mid-tone and the glossy glass makes the shine.
    "grey": {"suffix": "", "mats": {SHELL: (4, {}), ORGAN: (102, {}), LOBE: (104, {}),
                                    CORE: (104, {}), RIB: (101, {}),
                                    LAMP: (55, {"emission_strength": 2.0}), RIM: (104, {}),
                                    DARK: (82, {}), MID: (103, {}),
                                    GLOW: (38, {"emission_strength": 1.5})}},
    "green": {"suffix": "-f2", "mats": {SHELL: (38, {}), ORGAN: (195, {}), LOBE: (198, {"emission_strength": 1.0}),
                                        CORE: (206, {"emission_strength": 4.0}),
                                        RIB: (201, {"emission_strength": 2.5}),
                                        LAMP: (207, {"emission_strength": 4.0}),
                                        RIM: (200, {"emission_strength": 1.5}),
                                        DARK: (34, {}), MID: (196, {}),
                                        GLOW: (203, {"emission_strength": 3.0})}},
    "purple": {"suffix": "-f3", "mats": {SHELL: (86, {})}},
}
# The glass ball is painted by the grey sprite's colours (classes of palette indices -> part): the
# machinery seen through the glass and its lights. The sprite's drawn lighting is not painted (the
# game lights the glass and draws the outline): the dark violet outline ring, the dark lower-right
# side and the bright rim crescent round the lower-right edge take the glass's own colour
# (see shading()).
PAINT = {}
for _part, _indices in ((SHELL, (2, 3, 4, 5, 6)), (DARK, (1, 33, 34, 48, 80, 81, 82, 83, 84, 85, 86, 98, 100)),
                        (ORGAN, (101, 102)), (MID, (103,)), (LOBE, (7, 104, 105)), (RIM, (8, 107)),
                        (CORE, (11, 12, 139, 141)), (GLOW, (36, 37, 38, 55))):
    for _i in _indices:
        PAINT[_i] = _part
# The ball: the sprite's outline is 45 px wide and 47 px tall, centred on column 23, row 27; it
# stands 23 px tall (a full ball with its equator on the ground plane).
CC, CR = 23, 27
RX, RY, HZ = 22.6 / 12, 23.4 / 12, 23 / 12


def P(c, r):
    """Block column/row (pixel centre) to Blender XY."""
    return lib.grid_x(c, W), lib.grid_y(r, H)


def px(n):
    return n / 12


def classify(frame):
    """grey, green or purple by the colour families of a frame's pixels."""
    green = grey = purple = 0
    for row in frame["pixels"]:
        for v in row:
            if v < 0 or v == 1:
                continue
            if 192 <= v <= 207 or 32 <= v <= 43 or v == 55:
                green += 1
            elif 80 <= v <= 95:
                purple += 1
            else:
                grey += 1
    total = green + grey + purple
    if purple > 0.8 * total:
        return "purple"
    return "green" if green > 0.35 * total else "grey"


def fade_steps(sprite):
    """A piece's grey and green frames in animation order (every piece has the same nine steps:
    grey, seven green fading back to grey, grey; its purple frame is left out)."""
    return [f for f in sorted(sprite["frames"], key=lambda f: f["index"]) if classify(f) != "purple"]


def frame_colours(sprites, state, part):
    """{sprite frame: palette index} for a part's material on the state's other frames, wherever it
    differs from the part's index: on each frame, the commonest colour of the pixels that had the
    part's colour on the state's first frame (the grey frame's for a colour that isn't there)."""
    first = 0 if state == "grey" else 1
    index = STATES[state]["mats"][part][0]
    steps = {name: fade_steps(sprite) for name, sprite in sprites.items()}
    ref_step, ref = first, index
    if not any(v == index for st in steps.values() for row in st[first]["pixels"] for v in row):
        ref_step, ref = 0, STATES["grey"]["mats"][part][0]
    masks = {name: [(r, c) for r, row in enumerate(st[ref_step]["pixels"]) for c, v in enumerate(row) if v == ref]
             for name, st in steps.items()}
    frames = {}
    for name, st in steps.items():
        for k, f in enumerate(st):
            if k == first or classify(f) != state:
                continue
            count = Counter(v for r, c in masks[name] if (v := f["pixels"][r][c]) >= 0)
            if not count:  # this piece doesn't show the part's colour: use the whole orb's
                count = Counter(v for n, other in steps.items() for r, c in masks[n]
                                if (v := other[k]["pixels"][r][c]) >= 0)
            new = count.most_common(1)[0][0]
            if new != index:
                frames[f["index"]] = new
    return frames


def Q(c, r):
    """Block column/row to the XY the ball is built at before it is stretched to RY in Y."""
    x, y = P(c, r)
    cy = P(CC, CR)[1]
    return x, cy + (y - cy) * RX / RY


def grey_pixels(sprites):
    """The whole orb's first grey frame, as rows of palette indices (-1 = transparent)."""
    grid = [[-1] * W for _ in range(H)]
    for name, dx, dy in PIECES:
        frame = fade_steps(sprites[name])[0]
        ox, oy = W // 2 + dx - 12, H // 2 + dy - 14
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[oy + r][ox + c] = v
    return grid


def paint_part(grid, x, y):
    """The part whose colour the sprite shows at final (stretched) XY, looking inward from the
    outline for points outside it."""
    cx, cy = P(CC, CR)
    for k in range(40):
        t = 1 - k * 0.012
        px_x, px_y = cx + (x - cx) * t, cy + (y - cy) * t
        c = round(px_x * 12 + W / 2 - 0.5)
        r = round(H / 2 - px_y * 12 - 0.5)
        if 0 <= r < H and 0 <= c < W and grid[r][c] >= 0:
            return PAINT.get(grid[r][c], SHELL)
    return DARK


def shading(part, x, y):
    """SHELL where a painted part only stands for the sprite's drawn lighting: anything in the outer
    ring (the outline, the dark rim and the bright rim crescent) and the dark lower-right side;
    `part` elsewhere (real markings: the machinery, its gaps and lights). x, y are final XY."""
    cx, cy = P(CC, CR)
    u, v = (x - cx) / RX, (cy - y) / RY  # screen right, screen down
    if math.hypot(u, v) > 0.84:
        return SHELL
    if part == DARK and (u + v) / math.sqrt(2) > 0.45:
        return SHELL
    return part


def ball(bm, grid, paint, n=20):
    """A cube-sphere (even top-view cells for painting): RX wide, HZ tall, faces painted from the
    grey sprite (or all shell when `paint` is False)."""
    cx, cy = P(CC, CR)
    verts = {}

    def vert(cube):
        key = tuple(round(v, 6) for v in cube)
        if key not in verts:
            d = Vector(cube).normalized()
            verts[key] = bm.verts.new((cx + RX * d.x, cy + RX * d.y, HZ * d.z))
        return verts[key]

    ts = [math.tan((i / n * 2 - 1) * math.pi / 4) for i in range(n + 1)]
    ts[0], ts[-1] = -1.0, 1.0
    for axis in range(3):
        a1, a2 = (axis + 1) % 3, (axis + 2) % 3
        for sign in (-1.0, 1.0):
            for i in range(n):
                for j in range(n):
                    quad = []
                    for di, dj in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        p = [0.0, 0.0, 0.0]
                        p[axis], p[a1], p[a2] = sign, ts[i + di], ts[j + dj]
                        quad.append(vert(p))
                    f = bm.faces.new(quad if sign > 0 else quad[::-1])
                    if not paint:
                        f.material_index = SHELL
                        continue
                    centre = sum((v.co for v in quad), Vector()) / 4
                    votes = Counter()
                    for q in [centre] + [centre.lerp(v.co, 0.6) for v in quad]:
                        votes[paint_part(grid, q.x, cy + (q.y - cy) * RY / RX)] += 1
                    ranked = votes.most_common()
                    part = ranked[0][0]
                    # The dark gaps between the machinery are 1 px lines: a cell takes them only
                    # where they fill most of it, not as stray dark squares.
                    if part == DARK and ranked[0][1] < 3 and len(ranked) > 1:
                        part = ranked[1][0]
                    # The sides and underside are glass too: the game draws the outline.
                    if centre.z < 0.2 * HZ:
                        part = SHELL
                    f.material_index = shading(part, centre.x, cy + (centre.y - cy) * RY / RX)


def build(state, palette, sprites):
    coll = common.reset_collection(f"{NAME}-{state}")
    spec = STATES[state]["mats"]
    tag = f"{NAME}-{state}"
    # Unused parts take the shell's material so slot indices stay fixed.
    mats = []
    for part in range(NPARTS):
        index, kw = spec.get(part, spec[SHELL])
        kw = dict(kw)
        if state != "purple":
            kw["frames"] = frame_colours(sprites, state, part)
        # All of it is the glass surface (the machinery is seen through it): glossy, not metal.
        if part == SHELL:
            kw.update(metallic=0.05, roughness=0.1)
        else:
            kw.setdefault("metallic", 0.05)
            kw.setdefault("roughness", 0.12)
        part_tag = f"{tag}-{part}" if kw.get("frames") else tag
        mats.append(common.palette_material(palette, index, part_tag, **kw))

    bm = bmesh.new()
    cx, cy = P(CC, CR)
    dome = lib.Dome(RX, HZ, cx, cy)
    ball(bm, grey_pixels(sprites), state != "purple")
    # (The bright crescent round the lower-right edge is the glass catching light: no stroke for it.)

    if state != "purple":
        organs(bm, dome)
    # Stretch to the sprite's slightly taller-than-wide outline.
    stretch = Matrix.Translation((0, cy, 0)) @ Matrix.Diagonal((1, RY / RX, 1, 1)) @ Matrix.Translation((0, -cy, 0))
    bmesh.ops.transform(bm, matrix=stretch, verts=bm.verts)
    return common.mesh_object(f"{NAME}-{state}", bm, mats, coll, smooth=True)


def organs(bm, dome):
    """The machinery seen through the glass: painted on the ball, so only the brightest bits are
    thin decals (well under a pixel proud) and the ribs are flat strokes."""
    def lump(c, r, rx, ry, h, mat, angle=0.0, sides=12, rings=3):
        x, y = Q(c, r)
        lib.patch(bm, dome, x, y, px(rx), px(ry), h, angle=angle, mat_index=mat, sides=sides, rings=rings)

    def vein(points, radius, mat, samples=12):
        lib.surface_tube(bm, dome, [Q(c, r) for c, r in points], px(radius), lift=0.0, mat_index=mat,
                         sides=6, samples=samples, flat=0.2)

    # The bud at the top with its tip.
    lump(23.4, 12, 1.5, 1.4, 0.02, LOBE, sides=8, rings=2)
    # The lamp at the lower right: a green light with a small blue-green centre.
    lump(36, 36, 2.6, 2.6, 0.02, GLOW, sides=12)
    lump(35.6, 35.6, 1.0, 1.0, 0.03, LAMP, sides=8, rings=2)
    # The vein down from the right lobe.
    vein([(30.3, 27.5), (30.6, 31), (30.6, 35), (31, 38.5), (31, 41.5)], 0.9, RIB)
    # Ribs curving round the bottom; the lowest ones are the green light strip.
    vein([(3.2, 29), (5.5, 32), (8.5, 35), (11.5, 37.3), (15.5, 38.4), (19.5, 37.4), (22.5, 35.6), (26, 35)], 1.1,
         RIB, samples=16)
    vein([(11.5, 42.2), (14.5, 43.3), (17.5, 43.6), (20.5, 43.0)], 1.0, GLOW, samples=10)
    vein([(22.2, 43.6), (24.5, 44.0), (26.8, 43.5)], 0.9, GLOW, samples=8)


def unseam(obj, x0, y0):
    """Shade a piece as part of one smooth ball: the cut caps (faces on the piece's box) are split
    off and flat, and every other face corner takes the ellipsoid's own normal, so the pieces meet
    without a groove and the thin decals and strokes on the glass shade flush with it.
    (x0, y0) is the piece's centre in block coordinates."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    hw, hh, eps = 1.0, 14 / 12, 1e-4

    def on_cut(f):
        for axis, lim in ((0, hw), (1, hh)):
            for sgn in (-1, 1):
                if all(abs(v.co[axis] - sgn * lim) < eps for v in f.verts):
                    return True
        return False

    caps = {f for f in bm.faces if on_cut(f)}
    for f in caps:
        f.smooth = False
    edges = [e for e in bm.edges if len(e.link_faces) == 2
             and (e.link_faces[0] in caps) != (e.link_faces[1] in caps)]
    if edges:
        bmesh.ops.split_edges(bm, edges=edges)
    bm.faces.index_update()
    cap_ids = {f.index for f in caps}
    bm.to_mesh(obj.data)
    bm.free()
    mesh = obj.data
    bx, by = P(CC, CR)
    centre = Vector((bx - x0, by - y0, 0.0))
    normals = []
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            if poly.index in cap_ids:
                normals.append(tuple(poly.normal))
                continue
            d = mesh.vertices[mesh.loops[li].vertex_index].co - centre
            normals.append(tuple(Vector((d.x / RX ** 2, d.y / RY ** 2, d.z / HZ ** 2)).normalized()))
    mesh.normals_split_custom_set(normals)
    mesh.update()


def main():
    sprites = {name: common.load_sprite(ROOT, name) for name, _, _ in PIECES}
    palette = {"name": NAME, "colors": {}}
    for s in sprites.values():
        palette["colors"].update(s["colors"])

    wholes = {}
    exported = []
    for state, info in STATES.items():
        whole = build(state, palette, sprites)
        wholes[state] = whole
        layout = [(name + info["suffix"], dx, dy) for name, dx, dy in PIECES]
        pieces = common.split_assembly(whole, layout)
        for name, dx, dy in layout:
            unseam(pieces[name], dx / 12, -dy / 12)
        for name, _, _ in PIECES:
            sprite = sprites[name]
            frames = [f["index"] for f in sprite["frames"] if classify(f) == state]
            assert frames, f"{name} has no {state} frames"
            ref = sprite["sprites"][0]
            subset = [{"sheet": ref["sheet"], "size": ref["size"], "frames": frames}]
            common.export_sprite_model(ROOT, [pieces[name + info["suffix"]]], f"enemies/{name}{info['suffix']}",
                                       subset)
            if state != "purple":
                exported.append((name + info["suffix"], pieces[name + info["suffix"]],
                                 dict(sprite, frames=[f for f in sprite["frames"] if f["index"] in frames])))

    if "--frames" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--frames") + 1])
        for model, obj, sprite in exported:
            common.render_frame_previews([obj], out / f"{model}.png", sprite, ROOT)

    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        for state, info in STATES.items():
            placed = []
            for name, dx, dy in PIECES:
                sprite = sprites[name]
                frame = next(f for f in sprite["frames"] if classify(f) == state)
                placed.append((frame["pixels"], sprite["colors"], W // 2 + dx - 12, H // 2 + dy - 14))
            ref = out.with_name(f"{out.stem}{info['suffix']}-sprite.png")
            lib.write_png(ref, lib.compose_pixels(placed, W, H, scale=6))
            common.render_preview([wholes[state]], str(out.with_name(f"{out.stem}{info['suffix']}.png")), ref, size=4)


if __name__ == "__main__":
    main()
