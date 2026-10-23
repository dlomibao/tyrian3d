"""Helpers shared by batch b014's model scripts (the newshd.shp asteroids and the golden shield).

Coordinates: sprite column c / row r. px/row give a pixel's centre, ex/ey a pixel edge (the left or
top edge of column c / row r), for a 24x28 block by default (pass size=1 for 12x14 sprites).

The asteroids are all built by `rock`: an icosphere pushed out to the sprite's silhouette (traced
as a radius per direction from the rock's centre), its top raised where the sprite is lit and sunk
in its dark cracks, and each face painted with the palette colour of the sprite pixels under it
(grouped into a few shades of the sprite's own ramp).

build-models.sh skips lib_ files; the model scripts import this next to them.
"""

import math
import random
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

OUTLINE = (-1, 1, 32)  # transparent and the dark outline the game draws itself


def dims(size):
    return (12, 14) if size == 1 else (24, 28)


def px(c, size=2):
    """Sprite column (pixel centre, or any fractional column) to Blender X."""
    return (c + 0.5 - dims(size)[0] / 2) / 12


def row(r, size=2):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (dims(size)[1] / 2 - (r + 0.5)) / 12


def ex(c, size=2):
    return (c - dims(size)[0] / 2) / 12


def ey(r, size=2):
    return (dims(size)[1] / 2 - r) / 12


def to_edge(x, y, size=2):
    """Blender (x, y) to sprite edge coordinates (u, v): pixel (c, r) covers [c, c+1) x [r, r+1)."""
    w, h = dims(size)
    return x * 12 + w / 2, h / 2 - y * 12


def luminance(rgb):
    r, g, b = rgb
    return 0.3 * r + 0.55 * g + 0.15 * b


class Shade:
    """The sprite's colours as a smooth luminance field, for relief and painting."""

    def __init__(self, sprite, pixels, size, skip=()):
        self.pixels = pixels
        self.size = size
        self.h, self.w = len(pixels), len(pixels[0])
        colors = sprite["colors"]
        self.lum = [[luminance(colors[str(v)]) if v not in OUTLINE and v not in skip else None for v in r]
                    for r in pixels]
        vals = [v for r in self.lum for v in r if v is not None]
        self.mean = sum(vals) / len(vals)

    def inside(self, c, r):
        return 0 <= r < self.h and 0 <= c < self.w and self.pixels[r][c] not in OUTLINE

    def at(self, x, y, blur=0.6):
        """Mean luminance of the sprite round Blender (x, y) (a few samples `blur` px apart)."""
        u, v = to_edge(x, y, self.size)
        acc, n = 0.0, 0
        for du, dv in ((0, 0), (blur, 0), (-blur, 0), (0, blur), (0, -blur)):
            c, r = int(math.floor(u + du)), int(math.floor(v + dv))
            if 0 <= r < self.h and 0 <= c < self.w and self.lum[r][c] is not None:
                acc += self.lum[r][c]
                n += 1
        return acc / n if n else None

    def index(self, x, y):
        u, v = to_edge(x, y, self.size)
        c, r = int(math.floor(u)), int(math.floor(v))
        if 0 <= r < self.h and 0 <= c < self.w:
            return self.pixels[r][c]
        return -1


def silhouette(pixels, size, steps=96, grow=0.25, smooth=1):
    """The sprite's body (pixels that aren't transparent or outline) as a radius per direction from
    its centre: returns (cx, cy, radii) in Blender units, radii[k] for angle 2*pi*k/steps."""
    h, w = len(pixels), len(pixels[0])
    cells = [(c + 0.5, r + 0.5) for r in range(h) for c in range(w) if pixels[r][c] not in OUTLINE]
    cu = sum(c for c, _ in cells) / len(cells)
    cv = sum(r for _, r in cells) / len(cells)
    inside = lambda u, v: (0 <= int(v) < h and 0 <= int(u) < w and u >= 0 and v >= 0  # noqa: E731
                           and pixels[int(v)][int(u)] not in OUTLINE)
    radii = []
    for k in range(steps):
        a = 2 * math.pi * k / steps
        du, dv = math.cos(a), -math.sin(a)  # Blender +Y is up the sprite (-v)
        t = 0.0
        while inside(cu + du * (t + 0.05), cv + dv * (t + 0.05)) and t < 40:
            t += 0.05
        radii.append(t + grow)
    for _ in range(smooth):
        radii = [(radii[k - 1] + 2 * radii[k] + radii[(k + 1) % steps]) / 4 for k in range(steps)]
    W, H = dims(size)
    return (cu - W / 2) / 12, (H / 2 - cv) / 12, [r / 12 for r in radii]


def radius_at(radii, angle):
    steps = len(radii)
    t = (angle % (2 * math.pi)) / (2 * math.pi) * steps
    k = int(t)
    f = t - k
    return radii[k % steps] * (1 - f) + radii[(k + 1) % steps] * f


def shade_slots(sprite, pixels, n, skip=()):
    """Group the palette indices of the sprite's body into `n` shades by luminance. Returns
    (indices, edges): the index standing for each shade (the most used index in its band) and the
    luminance where each band starts, darkest first."""
    colors = sprite["colors"]
    count = {}
    for r in pixels:
        for v in r:
            if v not in OUTLINE and v not in skip:
                count[v] = count.get(v, 0) + 1
    lums = sorted(luminance(colors[str(i)]) for i in count)
    lo, hi = lums[0], lums[-1]
    edges = [lo + (hi - lo) * k / n for k in range(n)]
    reps = []
    for k in range(n):
        top = edges[k + 1] if k + 1 < n else hi + 1
        band = [i for i in count if edges[k] <= luminance(colors[str(i)]) < top]
        if band:
            reps.append(max(band, key=lambda i: count[i]))
        elif reps:
            reps.append(reps[-1])
        else:
            reps.append(None)
    # Bands left empty at the dark end take the next one up.
    for k in range(n - 1, -1, -1):
        if reps[k] is None:
            reps[k] = reps[k + 1]
    return reps, edges


def band_of(edges, lum):
    k = 0
    for i, e in enumerate(edges):
        if lum >= e:
            k = i
    return k


def rock(sprite, name, pixels, size=2, half_height=0.24, relief=0.05, lumps=0.06, seed=1, shades=6,
         subdiv=2, extra=None, skip=(), grow=0.25, flat_bottom=0.75):
    """An asteroid built to a frame of its sprite (see the module docstring). Returns (bm, mats,
    shade) so a script can add to it; `extra(bm, mats, shade)` may append materials and parts.

    half_height: the rock's half thickness at its widest (units); relief: how far the lit and dark
    areas of the sprite raise or sink its top; lumps: random lumpiness (a fraction of the radius,
    mostly in Z so the silhouette stays the sprite's). skip: palette indices that aren't rock (e.g.
    a glowing vent) and are left out of the shading."""
    shade = Shade(sprite, pixels, size, skip)
    reps, edges = shade_slots(sprite, pixels, shades, skip)
    mats = []
    for k, idx in enumerate(reps):
        mats.append(common.palette_material(sprite, idx, name, metallic=0.15, roughness=0.85 - 0.04 * k))
    cx, cy, radii = silhouette(pixels, size, grow=grow)
    rmax = max(radii)

    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    bm.normal_update()
    top = {e for f in bm.faces if f.normal.z > -0.25 for e in f.edges}
    bmesh.ops.subdivide_edges(bm, edges=list(top), cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])

    rng = random.Random(seed)
    blobs = [(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized(),
              rng.uniform(0.4, 1.0)) for _ in range(10)]

    def lump(n):
        s = 0.0
        for d, a in blobs:
            s += a * max(0.0, n.dot(d) - 0.55)
        return s

    for v in bm.verts:
        n = v.co.normalized()
        ang = math.atan2(n.y, n.x)
        r = radius_at(radii, ang)
        b = lump(n)
        x = cx + n.x * r * (1 + lumps * 0.25 * b)
        y = cy + n.y * r * (1 + lumps * 0.25 * b)
        hz = half_height * (0.55 + 0.45 * r / rmax)
        z = n.z * hz * (1 + lumps * b * 2.5)
        if n.z < 0:
            z *= flat_bottom
        v.co = Vector((x, y, z))
    # Lit areas of the sprite stand proud, dark cracks sink (on the top only, fading to the rim).
    for v in bm.verts:
        if v.co.z <= 0:
            continue
        lum = shade.at(v.co.x, v.co.y)
        if lum is None:
            continue
        fade = min(1.0, v.co.z / (half_height * 0.5))
        v.co.z += (lum - shade.mean) / 100.0 * relief * fade

    bm.normal_update()
    for f in bm.faces:
        cen = f.calc_center_median()
        if f.normal.z < -0.3:
            f.material_index = 0
            continue
        pts = [cen] + [cen.lerp(v.co, 0.6) for v in f.verts]
        vals = [shade.at(p.x, p.y, blur=0.3) for p in pts]
        vals = [x for x in vals if x is not None]
        if not vals:
            f.material_index = 1 if f.normal.z > 0.3 else 0
            continue
        lum = sum(vals) / len(vals)
        k = band_of(edges, lum)
        if f.normal.z < 0.2:  # the steep rim reads darker
            k = max(0, k - 1)
        f.material_index = k
    if extra:
        extra(bm, mats, shade)
    return bm, mats, shade


def run(name, build, file):
    """The usual main: build, export every model and, with -- --preview <png>, preview the first.

    `build(sprite)` returns a list of (model_name, objects, sprites) to export."""
    root = common.repo_root(file)
    sprite = common.load_sprite(root, name)
    models = build(sprite)
    for model, objects, sprites in models:
        common.export_sprite_model(root, objects, f"enemies/{model}", sprites)
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = root / "reference" / "models" / name / frame["image"]
        common.render_preview(models[0][1], out, ref, size=frame["size"])
    return sprite


def rock_script(name, file, **kw):
    """A whole asteroid script: one model from the first frame covering all the sprite's frames."""
    def build(sprite):
        coll = common.reset_collection(name)
        size = sprite["frames"][0]["size"]
        bm, mats, _ = rock(sprite, name, sprite["frames"][0]["pixels"], size=size, **kw)
        obj = common.mesh_object(name, bm, mats, coll, smooth=False)
        return [(name, [obj], sprite["sprites"])]
    return run(name, build, file)
