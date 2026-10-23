"""Jungle rocket launcher (newshj.shp, pieces newshj-17, -55, -127, -129): a 3D version of its sprites.

Seen in levels 2.2, 2.21 and 2.24. Four 2x2 ground enemies make one 72x56 px launcher (sprite.json
`assemblyLayout`; newshj-1 and newshj-131 beside it in assembly.png are separate enemies, and the
level places a second launcher without the flame piece): a fat grey launch tube aimed up and to
the left on a grey pedestal, with a narrower breech behind it, a strut down to the ground on its
right and a vent between them glowing red to white (newshj-129, whose three frames only change the
glow, so one model covers them). The two lower pieces (newshj-127, newshj-129) are squares of
jungle, built as a dark ground plate covered in leafy mounds.

newshj-55 is the tube's muzzle: frame 55 fires a long flame (whose tip is newshj-17 frame 17),
frame 89 shows only the red rocket nose in the muzzle, and frame 93 a short flame (tip newshj-17
frame 91). The flames change the shape, so newshj-55 gets three models (newshj-55, -f2, -f3) and
newshj-17 two (newshj-17, -f2); the small lights on the tube take each frame's brightness.

The launcher is built once in composite pixel coordinates (72x56, the layout's first launcher),
then cut into the pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshj-127.py [-- --preview out.png]
(the preview is the whole launcher; each model also gets <model>.png next to it).
"""

import math
import random
import sys
import tempfile
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b118 as lib  # noqa: E402

NAME = "assembly-newshj-127"
ROOT = common.repo_root(__file__)
PIECES = ["newshj-17", "newshj-55", "newshj-127", "newshj-129"]
# The first launcher in the layout: (model, frame shown there, screen cx, cy).
LAUNCHER = [("newshj-17", 17, 200, 93), ("newshj-55", 55, 224, 93), ("newshj-127", 127, 224, 121),
            ("newshj-129", 281, 248, 121)]
# Composite pixel (0, 0) is screen (188, 79); its centre (screen 224, 107) is the Blender origin.
CX0, CY0 = 224, 107
G = lib.Grid(72, 56)
PX = lib.PX

# The launch tube's axis, in pixel-edge coordinates and heights: rear end and muzzle.
REAR = (46.0, 35.0, 0.48)
MUZZLE = (30.5, 19.5, 0.60)
TUBE_R = 5.5  # px
TUBE_FLAT = 0.72


def P(c, r, z):
    return Vector((G.xe(c), G.ye(r), z))


def along(t, extra=0.0):
    """A point on the tube's axis: t = 0 at the rear, 1 at the muzzle; `extra` px beyond."""
    a, b = P(*REAR), P(*MUZZLE)
    d = (b - a)
    return a + d * t + d.normalized() * (extra * PX)


def tube_top(c, r):
    """Height of the tube's upper surface over pixel-edge point (c, r)."""
    a, b = Vector(REAR[:2]), Vector(MUZZLE[:2])
    d = (b - a).normalized()
    p = Vector((c, r)) - a
    t = p.dot(d) / (b - a).length
    off = abs(p.x * d.y - p.y * d.x)  # px from the axis, in the top view
    z = REAR[2] + (MUZZLE[2] - REAR[2]) * t
    return z + TUBE_R * PX * TUBE_FLAT * math.sqrt(max(0.0, 1 - (off / TUBE_R) ** 2))


def materials(sprite):
    tag = "nshj127"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    return [
        pal(7, metallic=0.55, roughness=0.35),  # 0 tube grey
        pal(9, metallic=0.55, roughness=0.3),  # 1 light grey collars and strut
        pal(3, metallic=0.4, roughness=0.6),  # 2 dark seams and the bore
        pal(6, metallic=0.5, roughness=0.45),  # 3 darker grey pedestal and vent housing
        pal(8, metallic=0.55, roughness=0.4),  # 4 mid grey breech, pedestal top
        pal(117, emission_strength=2.0),  # 5 red rocket nose
        pal(122, emission_strength=4.0),  # 6 vent glow, upper
        pal(127, emission_strength=5.0),  # 7 vent glow, hottest
        pal(117, emission_strength=2.5),  # 8 vent glow, lower (shares the red)
        pal(192, metallic=0.0, roughness=0.9),  # 9 dark jungle floor
        pal(194, metallic=0.0, roughness=0.8),  # 10 leaves dark
        pal(196, metallic=0.0, roughness=0.8),  # 11 leaves mid
        pal(198, metallic=0.0, roughness=0.75),  # 12 leaves light
        pal(118, emission_strength=3.0),  # 13 flame outer red
        pal(122, emission_strength=4.0),  # 14 flame orange
        pal(125, emission_strength=5.0),  # 15 flame yellow core
        pal(127, emission_strength=6.0),  # 16 flame white heart
        pal(124, emission_strength=4.0),  # 17 tube lights bright (frame 55)
        pal(116, emission_strength=2.0),  # 18 tube lights dim (frame 89)
        pal(120, emission_strength=3.0),  # 19 tube lights mid (frame 93)
        pal(12, metallic=0.6, roughness=0.25),  # 20 bright grey muzzle rim
    ]


(TUBE, COLLAR, SEAM, BASE, BREECH, NOSE, VENT, VENTHOT, VENTLOW, FLOOR, LEAF0, LEAF1, LEAF2,
 FLAME0, FLAME1, FLAME2, FLAME3, LIGHT_HI, LIGHT_LO, LIGHT_MID, RIM) = range(21)


def composite_pixels():
    """The first launcher's pixels as {(col, row): palette index}."""
    px = {}
    for name, fidx, cx, cy in LAUNCHER:
        data = common.load_sprite(ROOT, name)
        frame = next(f for f in data["frames"] if f["index"] == fidx)
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    px[(cx - 12 - 188 + c, cy - 14 - 79 + r)] = v
    return px


GREEN = {32: 8, 33: 20, 34: 28, 35: 40, 192: 48, 193: 65, 194: 81, 195: 93, 196: 109, 197: 125,
         198: 142, 200: 166, 201: 182, 203: 207}


def jungle(bm, pixels):
    """The jungle squares under the launcher (columns 24-71, rows 28-55): a dark plate with leafy
    mounds wherever the sprite's leaves are lit, sized and coloured from the pixels around them."""
    lib.prism(bm, [(G.xe(24), G.ye(56)), (G.xe(72), G.ye(56)), (G.xe(72), G.ye(28)), (G.xe(24), G.ye(28))],
              0.0, 0.02, mat=FLOOR)
    rng = random.Random(127)
    step = 4
    for r0 in range(28, 56, step):
        for c0 in range(24, 72, step):
            cells = [(c, r) for r in range(r0, r0 + step) for c in range(c0, c0 + step)]
            vals = [pixels.get(p, -1) for p in cells]
            if sum(1 for v in vals if v not in GREEN) > 4:
                continue  # mostly launcher
            g = [GREEN[v] for v in vals if v in GREEN]
            mean = sum(g) / len(g)
            if mean < 30:
                continue  # dark floor
            # Centre on the lit leaves in the cell.
            wsum = sum(max(0, GREEN.get(v, 0) - 30) for v in vals) or 1
            cx = sum((c + 0.5) * max(0, GREEN.get(v, 0) - 30) for (c, r), v in zip(cells, vals)) / wsum
            cy = sum((r + 0.5) * max(0, GREEN.get(v, 0) - 30) for (c, r), v in zip(cells, vals)) / wsum
            cx += rng.uniform(-0.4, 0.4)
            cy += rng.uniform(-0.4, 0.4)
            mat = LEAF2 if mean > 105 else LEAF1 if mean > 78 else LEAF0
            rad = 2.5 + min(0.9, (mean - 30) / 70)
            # Keep the mounds inside the jungle squares (none spill into the pieces above).
            cx = min(max(cx, 24 + rad * 1.2), 72 - rad * 1.2)
            cy = min(max(cy, 28 + rad * 1.2), 56 - rad * 1.2)
            lib.dome(bm, G.xe(cx), G.ye(cy), 0.0, rad * PX * rng.uniform(0.95, 1.15), rad * PX * rng.uniform(0.9, 1.1),
                     0.04 + 0.07 * min(1.0, mean / 130), mat=mat, segments=6, rings=2)


def launcher(bm):
    # The launch tube: rear seam band, body, collar and muzzle rim, the bore and the rocket's nose.
    d = (P(*MUZZLE) - P(*REAR)).normalized()
    lib.tube3(bm, along(0.0), along(0.07), TUBE_R * PX, sides=16, mat=TUBE, flat=TUBE_FLAT, caps=True)
    lib.tube3(bm, along(0.07), along(0.12), (TUBE_R + 0.3) * PX, sides=16, mat=SEAM, flat=TUBE_FLAT, caps=False)
    lib.tube3(bm, along(0.12), along(0.92), TUBE_R * PX, sides=16, mat=TUBE, flat=TUBE_FLAT, caps=False)
    lib.tube3(bm, along(0.92), along(1.0), (TUBE_R + 0.35) * PX, sides=16, mat=RIM, flat=TUBE_FLAT, caps=True)
    lib.tube3(bm, along(1.0, -0.4), along(1.0, 0.25), (TUBE_R - 1.4) * PX, sides=12, mat=SEAM, flat=TUBE_FLAT)
    lib.tube3(bm, along(1.0, 0.0), along(1.0, 3.2), 2.4 * PX, sides=10, mat=NOSE, r1=0.0, caps=True)
    # Light streaks along the tube's upper side (the sprite's highlight, 4 px in from its edge).
    side = Vector((d.y, -d.x, 0)).normalized()
    for off, t0, t1 in ((-0.5, 0.15, 0.88),):
        a = along(t0) + side * (off * PX) + Vector((0, 0, TUBE_R * PX * TUBE_FLAT))
        b = along(t1) + side * (off * PX) + Vector((0, 0, TUBE_R * PX * TUBE_FLAT))
        lib.tube3(bm, a, b, 0.7 * PX, sides=6, mat=COLLAR, flat=0.5)

    # The breech behind it (columns 44-55, rows 34-42), resting on the pedestal.
    lib.tube3(bm, P(46.5, 34.0, 0.47), P(55.0, 42.5, 0.4), 3.6 * PX, sides=12, mat=BREECH, flat=0.85)
    lib.tube3(bm, P(54.6, 42.1, 0.4), P(55.4, 42.9, 0.4), 2.6 * PX, sides=12, mat=SEAM, flat=0.85)

    # Pedestal (columns 39-50, rows 39-51) with chamfered corners.
    ped = [(39.0, 47.0), (41.5, 49.5), (45.0, 52.0), (49.5, 51.6), (50.5, 49.0), (50.5, 41.5),
           (47.0, 39.0), (42.0, 39.3), (39.0, 42.0)]
    lib.prism(bm, [(G.xe(c), G.ye(r)) for c, r in ped], 0.0, 0.36, mat=BASE, top_mat=BREECH)
    lib.prism(bm, [(G.xe(c), G.ye(r)) for c, r in ((47.2, 40.2), (48.2, 40.2), (48.2, 47.6), (47.2, 47.6))],
              0.3, 0.375, mat=SEAM)

    # Vent housing (columns 51-56, rows 41-50) with the glow in its top, hottest at the top.
    lib.prism(bm, [(G.xe(c), G.ye(r)) for c, r in ((50.6, 41.4), (56.3, 41.4), (56.3, 50.6), (50.6, 50.6))],
              0.0, 0.3, mat=BASE)
    for r0, r1, m in ((41.8, 45.6, VENTHOT), (45.6, 47.6, VENT), (47.6, 50.2, VENTLOW)):
        lib.prism(bm, [(G.xe(c), G.ye(r)) for c, r in ((52.8, r0), (55.2, r0), (55.2, r1), (52.8, r1))],
                  0.28, 0.33, mat=m)

    # Strut from the breech down to the ground on the right (columns 54-61, rows 36-45) and its foot.
    lib.tube3(bm, P(54.0, 36.0, 0.44), P(60.0, 44.2, 0.06), 1.7 * PX, sides=8, mat=COLLAR, flat=1.0)
    lib.prism(bm, [(G.xe(c), G.ye(r)) for c, r in ((57.8, 43.0), (61.6, 43.0), (61.6, 46.0), (57.8, 46.0))],
              0.0, 0.08, mat=BASE)


def flame(bm, path, core):
    """A flame shooting out of the muzzle: `path` is (col, row, half width px) from the base to the
    tip; `core` the same for the bright core inside it."""
    a, b = P(*MUZZLE), along(1.0, 20.0)
    rise = (b.z - a.z) / 20.0

    def z_at(c, r):
        return MUZZLE[2] + rise * math.hypot(c - MUZZLE[0], r - MUZZLE[1])

    for pts, mat, hz, grow in ((path, FLAME0, 0.3, 1.0), (path, FLAME1, 0.55, 0.75), (core, FLAME2, 1.1, 1.0),
                               (core, FLAME3, 1.6, 0.6)):
        lib.sweep(bm, [(G.xe(c), G.ye(r), z_at(c, r), w * grow * PX, w * grow * PX * hz) for c, r, w in pts],
                  sides=10, mat=mat)


BIG_FLAME = [(28.6, 18.2, 0.0), (28.0, 17.4, 2.0), (25.0, 14.0, 3.1), (21.8, 10.6, 3.0), (18.8, 7.2, 2.3),
             (16.4, 4.6, 1.3), (14.6, 2.4, 0.0)]
BIG_CORE = [(28.4, 17.8, 0.0), (27.6, 16.8, 1.6), (25.4, 14.0, 2.0), (22.6, 10.6, 1.4), (20.4, 8.0, 0.0)]
SMALL_FLAME = [(28.9, 18.4, 0.0), (28.3, 17.6, 2.0), (26.2, 14.8, 2.8), (23.6, 11.8, 2.2), (21.4, 9.8, 1.0),
               (20.2, 9.0, 0.0)]
SMALL_CORE = [(28.4, 17.6, 0.0), (27.6, 16.6, 1.2), (25.8, 14.2, 1.3), (24.4, 12.4, 0.0)]


def tube_lights(bm, mat):
    """The two small lights on the tube (columns 39-41 row 23, columns 34-35 rows 24-26)."""
    for c, r, rx, ry in ((40.6, 23.5, 1.6, 1.0), (35.0, 25.5, 1.1, 1.6)):
        lib.ellipsoid(bm, G.xe(c), G.ye(r), tube_top(c, r) - 0.015, rx * PX, ry * PX, 0.04, mat=mat,
                      segments=8, rings=3)


def build_object(name, fill, mats, coll):
    bm = bmesh.new()
    fill(bm)
    return lib.to_object(name, bm, mats, coll)


def subset(data, frames):
    return [{**s, "frames": [f for f in s["frames"] if f in frames]} for s in data["sprites"]]


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    pixels = composite_pixels()

    def base_fill(bm):
        jungle(bm, pixels)
        launcher(bm)

    base = build_object(NAME, base_fill, mats, coll)
    big = build_object(NAME + "-flame", lambda bm: flame(bm, BIG_FLAME, BIG_CORE), mats, coll)
    small = build_object(NAME + "-flame-short", lambda bm: flame(bm, SMALL_FLAME, SMALL_CORE), mats, coll)
    lights = {m: build_object(f"{NAME}-lights-{m}", lambda bm, m=m: tube_lights(bm, m), mats, coll)
              for m in (LIGHT_HI, LIGHT_LO, LIGHT_MID)}

    layout = [(n, cx - CX0, cy - CY0) for n, _, cx, cy in LAUNCHER]

    def split(obj, names, suffix):
        parts = common.split_assembly(obj, [e for e in layout if e[0] in names])
        for n, o in parts.items():
            o.name = o.data.name = f"{n}{suffix}"
        return parts

    base_p = split(base, PIECES, "")
    big_p = split(big, ["newshj-17", "newshj-55"], "-flame")
    small_p = split(small, ["newshj-17", "newshj-55"], "-flame-short")
    light_p = {m: split(o, ["newshj-55"], f"-lights-{m}")["newshj-55"] for m, o in lights.items()}

    data = {n: common.load_sprite(ROOT, n) for n in PIECES}
    models = [
        ("newshj-17", [big_p["newshj-17"]], 17),
        ("newshj-17-f2", [small_p["newshj-17"]], 91),
        ("newshj-55", [base_p["newshj-55"], big_p["newshj-55"], light_p[LIGHT_HI]], 55),
        ("newshj-55-f2", [base_p["newshj-55"], light_p[LIGHT_LO]], 89),
        ("newshj-55-f3", [base_p["newshj-55"], small_p["newshj-55"], light_p[LIGHT_MID]], 93),
        ("newshj-127", [base_p["newshj-127"]], None),
        ("newshj-129", [base_p["newshj-129"]], None),
    ]
    for model, objs, frame in models:
        piece = model.split("-f")[0] if "-f" in model else model
        sprites = data[piece]["sprites"] if frame is None else subset(data[piece], [frame])
        common.export_sprite_model(ROOT, objs, f"enemies/{model}", sprites)

    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        # The launcher (72x56) in the middle of a 72x84 image, the 24:28 shape of a size-6 preview.
        entries = [(n, f, cx - 188 - 12, cy - 79 - 14) for n, f, cx, cy in LAUNCHER]
        ref = lib.composite_png(ROOT, entries, Path(tempfile.mkdtemp()) / "assembly.png", 72, 84, y0=14)
        common.render_preview([base, big, lights[LIGHT_HI]], str(out), ref, size=6, view_px=640)
        for model, objs, frame in models:
            piece = model.split("-f")[0] if "-f" in model else model
            fr = data[piece]["frames"][0] if frame is None else next(
                f for f in data[piece]["frames"] if f["index"] == frame)
            img = ROOT / "reference" / "models" / piece / fr["image"]
            common.render_preview(objs, str(out.parent / f"{model}.png"), img, size=2)


if __name__ == "__main__":
    main()
