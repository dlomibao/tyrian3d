"""Red curled pod (newsh5.shp frames 121, 123, 125): a 3D version of its sprites.

Seen in episode 4 (levels 4.22 and 4.25), lying on the ground. A glossy red pod, a full dome about half
as tall as it is wide, with a dark crease cut into it near its top, and two low, broad folds
curling round it like a shell. The three frames show it turning (the egg goes from a wide, tilted
oval to a tall narrow one), so each frame gets its own model: newsh5-121, newsh5-121-f2, newsh5-121-f3.
The shell's rim follows that frame's silhouette (its distance from a centre at 44 angles); the
details are placed by hand from the frame's pixels. The sprite's drawn light is left to the game:
its dark rim is the outline, its lit left side and the orange/yellow hot spot at the top left (the
top of the red ramp) are the light on a glossy shell, so the shell is one mid red with a glossy
(non-metal) material.

Run: blender --background --python assets/blender/enemies/newsh5-121.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b068 as L  # noqa: E402

common = L.common
NAME = "newsh5-121"
ROOT = common.repo_root(__file__)

# Per frame (sprite pixel coordinates, column/row of pixel centres): the dark crease and the two
# folds (the lighter bands of indices 116/117).
DETAILS = {
    121: dict(crease=[(11.0, 6.7), (12.3, 7.6), (12.9, 9.2), (12.4, 11.0), (11.0, 12.2), (8.4, 12.4), (7.2, 12.3)],
              fold=[(14.2, 6.6), (14.9, 9.0), (14.7, 11.5), (13.6, 13.5), (11.6, 15.3), (9.0, 16.6)],
              rim=[(19.3, 9.6), (19.1, 12.5), (18.1, 14.8), (16.6, 16.8), (14.6, 18.4)]),
    123: dict(crease=[(11.0, 5.8), (12.0, 7.0), (12.3, 9.5), (12.0, 11.2), (10.9, 12.5), (8.4, 13.0), (7.3, 12.9)],
              fold=[(13.6, 5.7), (14.3, 8.5), (14.3, 11.0), (13.5, 13.3), (12.0, 15.0), (10.0, 16.4)],
              rim=[(18.2, 9.0), (18.3, 12.0), (17.8, 14.6), (16.5, 16.5), (14.8, 18.1)]),
    125: dict(crease=[(11.0, 4.8), (11.4, 7.0), (11.5, 9.5), (11.2, 11.8), (9.8, 12.8), (8.0, 12.6)],
              fold=[(13.1, 4.6), (13.3, 8.0), (13.6, 11.5), (13.1, 14.0), (12.0, 16.0), (10.0, 17.3)],
              rim=[(17.3, 8.5), (17.3, 12.0), (17.0, 14.8), (16.0, 16.8), (14.5, 18.4)]),
}


HEIGHT = 9.5 * L.PX  # apex: a full dome, about half as tall as it is wide (~20 px)
POWER = 0.6  # profile (1 - rho^2)^POWER: a round dome that still slopes all the way to the ground
SEGMENTS = 44  # around the rim
RINGS = 13  # from the rim to the apex, denser near the rim
APEX_SHIFT = (-1.4, -2.0)  # px from the centroid


def outline(frame):
    """The frame's silhouette as a centre (sprite px, pixel-edge coordinates) and the distance from
    it to the edge at SEGMENTS even angles (px), measured by stepping out over the pixels and
    lightly smoothed, so the rim follows the sprite's lumpy outline rather than an ellipse."""
    px = frame["pixels"]
    pts = [(c + 0.5, r + 0.5) for r, row in enumerate(px) for c, v in enumerate(row) if v >= 0]
    # The apex (and the centre the rim is measured from) sits up and left of the silhouette's
    # centroid, under the sprite's highlight and inside the crease's hook.
    mx = sum(p[0] for p in pts) / len(pts) + APEX_SHIFT[0]
    my = sum(p[1] for p in pts) / len(pts) + APEX_SHIFT[1]

    def inside(x, y):
        c, r = math.floor(x), math.floor(y)
        return 0 <= r < len(px) and 0 <= c < len(px[0]) and px[r][c] >= 0

    raw = []
    for k in range(SEGMENTS):
        a = 2 * math.pi * k / SEGMENTS
        dx, dy = math.cos(a), -math.sin(a)  # angle measured in Blender's frame (sprite up = +Y)
        d, last = 0.0, 0.0
        while d < 20:
            if inside(mx + dx * d, my + dy * d):
                last = d
            d += 0.05
        raw.append(last - 0.1)  # the staircase's corners stick out; aim between them
    n = len(raw)
    rad = [(raw[k - 1] + 2 * raw[k] + raw[(k + 1) % n]) / 4 for k in range(n)]
    return (mx, my), rad


class Dome:
    """The pod's shell: a dome whose rim follows the sprite's outline, height H*(1-rho^2)^POWER."""

    def __init__(self, frame):
        (mx, my), self.rad = outline(frame)
        self.cx, self.cy = L.EX(mx), L.EY(my)

    def rim(self, a):
        """Rim distance (units) at Blender angle a, interpolated between the measured angles."""
        n = len(self.rad)
        t = (a / (2 * math.pi) % 1.0) * n
        k = int(t) % n
        f = t - int(t)
        return (self.rad[k] * (1 - f) + self.rad[(k + 1) % n] * f) * L.PX

    def rho(self, x, y):
        """0 at the centre, 1 on the rim."""
        dx, dy = x - self.cx, y - self.cy
        return math.hypot(dx, dy) / self.rim(math.atan2(dy, dx))

    def z(self, x, y):
        rho = self.rho(x, y)
        return HEIGHT * max(0.0, 1 - rho * rho) ** POWER if rho < 1 else 0.0

    def build(self, bm, mat):
        f0 = len(bm.faces)
        loops = []
        for i in range(RINGS):
            rho = math.cos(0.5 * math.pi * i / RINGS)  # 1 at the rim, dense there
            h = HEIGHT * (1 - rho * rho) ** POWER
            loop = []
            for k in range(SEGMENTS):
                a = 2 * math.pi * k / SEGMENTS
                r = self.rad[k] * L.PX * rho
                loop.append(bm.verts.new((self.cx + r * math.cos(a), self.cy + r * math.sin(a), h)))
            loops.append(loop)
        apex = bm.verts.new((self.cx, self.cy, HEIGHT))
        for a, b in zip(loops, loops[1:]):
            for k in range(SEGMENTS):
                j = (k + 1) % SEGMENTS
                bm.faces.new((a[k], a[j], b[j], b[k]))
        top = loops[-1]
        for k in range(SEGMENTS):
            bm.faces.new((top[k], top[(k + 1) % SEGMENTS], apex))
        bm.faces.new(list(reversed(loops[0])))  # the floor
        L.set_faces(bm, f0, mat, True)
        bm.faces.ensure_lookup_table()
        bm.faces[-1].smooth = False


def seg_dist(x, y, path):
    """Distance (units) from (x, y) to a polyline of (x, y) points."""
    best = 1e9
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        ex, ey = x1 - x0, y1 - y0
        t = max(0.0, min(1.0, ((x - x0) * ex + (y - y0) * ey) / (ex * ex + ey * ey)))
        best = min(best, math.hypot(x - x0 - t * ex, y - y0 - t * ey))
    return best


def relief(bm, path, depth, half_width, lift):
    """Raise (depth > 0) or sink (< 0) the shell along a path of sprite (column, row) points: a
    smooth band `half_width` px either side, at most `depth` px (cos^2 fall-off). `lift` collects
    each vertex's total change (px)."""
    pts = [(L.X(c), L.Y(r)) for c, r in path]
    w = half_width * L.PX
    for v in bm.verts:
        if v.co.z <= 1e-6:
            continue  # the floor and the rim stay put
        d = seg_dist(v.co.x, v.co.y, pts)
        if d < w:
            dz = depth * math.cos(0.5 * math.pi * d / w) ** 2
            v.co.z += dz * L.PX
            lift[v.index] = lift.get(v.index, 0.0) + dz


# The shell's mid red, folds included: their lighter bands in the sprite are their lit crests,
# which the relief and the game's light make (painting them gave blocky, jagged patches).
SHELL_PAL = (116,)
BODY = FOLD = 116


def build(sprite, frame, tag):
    coll = common.reset_collection(tag)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    # A glossy shell (not metal): the sprite's orange/yellow spot near the top left is the top of
    # the red ramp (120-124), the sheen of that gloss under an upper-left light, so it is the
    # material's job, not a knob. The shell is one mid-tone; the game's lights shade it.
    mats = [pal(i, metallic=0.0, roughness=0.3) for i in SHELL_PAL] + [
        common.palette_material(sprite, 114, NAME + "-crease", metallic=0.0, roughness=0.8),
    ]
    CREASE = len(SHELL_PAL)
    d = DETAILS[frame["index"]]
    dome = Dome(frame)
    bm = bmesh.new()
    dome.build(bm, 0)
    bm.verts.index_update()

    # The two folds: broad, low bands (~3 px wide, ~0.45 px proud) curling round the crease.
    lift = {}
    relief(bm, d["fold"], 0.45, 1.6, lift)
    relief(bm, d["rim"], 0.45, 1.6, lift)

    # The shell is the sprite's mid red all over (its dark rim is the sprite's outline and its
    # lit/dark sides are its drawn light: the game draws both).
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        if len(f.verts) > 4:
            continue  # the floor
        dz = sum(lift.get(v.index, 0.0) for v in f.verts) / len(f.verts)
        f.material_index = SHELL_PAL.index(BODY if dz <= 0.2 else FOLD)

    shell = L.to_object(tag, bm, mats, coll)

    # The dark crease: a groove ~1 px deep and ~2 px wide cut into the shell (a boolean with a
    # tube draped on the surface), its walls and floor dark red.
    bm = bmesh.new()
    L.sweep(bm, [(L.X(c), L.Y(r), 0.0, 0.95 * L.PX, 1.0 * L.PX) for c, r in d["crease"]], sides=8)
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        v.co.z += dome.z(v.co.x, v.co.y)
    cutter = L.to_object(tag + "-cutter", bm, [mats[CREASE]], coll)
    mod = shell.modifiers.new("crease", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    mod.material_mode = "TRANSFER"
    with bpy.context.temp_override(object=shell, active_object=shell):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    # The boolean may add the crease material as another slot: map faces back onto `mats`, and
    # shade the groove flat with a hard edge where it meets the shell.
    slot = [mats.index(m) for m in shell.data.materials]
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    for f in bm.faces:
        f.material_index = slot[f.material_index]
        if f.material_index == CREASE:
            f.smooth = False
    for e in bm.edges:
        if len({f.material_index == CREASE for f in e.link_faces}) > 1:
            e.smooth = False
    shell.data.materials.clear()
    for m in mats:
        shell.data.materials.append(m)
    bm.to_mesh(shell.data)
    bm.free()
    return shell


def main():
    sprite = common.load_sprite(ROOT, NAME)
    models = []
    for i, frame in enumerate(sprite["frames"]):
        tag = NAME if i == 0 else f"{NAME}-f{i + 1}"
        models.append((build(sprite, frame, tag), [frame["index"]]))
    L.export_frames(ROOT, NAME, sprite, models)


if __name__ == "__main__":
    main()
