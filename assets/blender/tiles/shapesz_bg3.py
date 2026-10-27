"""The floating islands and fortresses of shapesz.dat in background 3 (Episode 1's TYRIAN): 3D
versions of the tiles, one model per tile (DECISIONS.md D34).

In the art an island is a pile of round boulders, grey with some tan ones, outlined in near-black:
tiles 120-122 / 130-132 / 140-142 are a whole island (the bottom row is its hanging underside
with roots), and 123, 124, 133, 134 and 150-152 are boulder fill that joins islands into bigger
masses. Fortresses are built on them: purple carved blocks on paving (155-177), metal floor with a
maze pattern (180-201) and a rounded hatch (183/184/193/194), a lava pit (143), a crater with gold
rings (153), white stone blocks in brass frames (185-188, 195-198), a machine of red panels and
dark metal (160/161/170/171), two drums with pointed ends (189, 199) and a blue orb set in purple
stone (149).

Each tile becomes a rock slab with its outline (MMPX 2x pixels, so diagonals are smooth) and:
- a rounded boulder for each stone in the art (lib_tiles.boulders: position, size, angle and
  colour from the stone's pixels, built whole across tile edges and cut at the edge);
- coloured relief for everything that isn't boulders (purple blocks, metal, rings): each 2x pixel
  in its own colour (snapped to a few), raised by its brightness; the lava pit is sunk and glows;
- on the underside tiles, a face that hangs down toward the camera with the painted roots on it;
- the drums as cylinders with a cone and bands, and the orb as a glowing sphere with crystals.

Run: blender --background --python assets/blender/tiles/shapesz_bg3.py [-- --preview out_dir]
"""

import sys
from pathlib import Path

import bmesh
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_tiles as lt  # noqa: E402

ROOT = common.repo_root(__file__)
SHAPES = "shapesz"
LAYER = 2

SLAB_TOP = 0.0
SLAB_BOTTOM = -0.3
#: Brightness (0..1) below which a pixel is a dark gap between stones.
GAP = 0.22
#: Palette ramps (index >> 4) of the boulders: grey and tan.
STONE_RAMPS = {0x0, 0xA}

#: tile: (recipe, options)
TILES = {}
for n in (120, 121, 122, 123, 124, 130, 131, 132, 133, 134, 150, 151, 152):
    TILES[n] = ("boulders", {})
for n in (140, 141, 142):
    TILES[n] = ("underside", {"drop": 0.55})
for n in (155, 156, 157, 158, 159, 165, 167, 168, 169, 175, 176, 177):
    TILES[n] = ("boulders", {"relief": 0.17, "base": 0.03, "sigma": 1.4, "colours": 3})  # purple blocks
for n in (185, 186, 187, 188, 195, 196, 197, 198):
    TILES[n] = ("boulders", {"relief": 0.1, "base": 0.03, "colours": 3})  # stone blocks, brass frames
for n in (160, 161, 170, 171):
    TILES[n] = ("inlay", {"relief": 0.24, "base": 0.02, "sigma": 0.9, "colours": 5})  # machine
# Drums: body centre (px), half length along x, radius, which way the cone points.
TILES[189] = ("boulders", {"drum": (10.0, 13.0, 5.5, 8.0, +1)})
TILES[199] = ("boulders", {"drum": (15.0, 13.0, 5.5, 8.0, -1)})
TILES[149] = ("inlay", {"relief": 0.1, "base": 0.0, "sigma": 1.0, "colours": 4, "orb": (13.0, 11.5, 6.5)})
TILES[143] = ("pit", {"relief": 0.16, "base": -0.1, "sigma": 0.9, "glow": 1.8, "colours": 5})  # lava pit
TILES[153] = ("pit", {"relief": 0.16, "base": -0.08, "sigma": 0.9, "glow": 1.8, "colours": 5})  # crater, gold rings
for n in (180, 181, 191, 192, 200, 201, 183, 184, 193, 194):
    TILES[n] = ("metal", {"relief": 0.035, "base": 0.06})


def is_red(ts, index):
    r, g, b = ts.rgb(index)
    return r > 60 and r > 1.7 * g and r > 1.7 * b


def build(ts, n, recipe, opts):
    name = f"t{n}"
    coll = common.reset_collection(f"{SHAPES}-{name}")
    pal = lt.Palette(ts, f"{SHAPES}{name}", roughness=0.85, metallic=0.0)
    frame = lt.Frame([[n]], scale=2)
    own = ts.grid([[n]], 2)
    h, w = own.shape
    opaque = own >= 0
    lum = lt.lum_of(ts, own)
    ramp = np.where(opaque, np.maximum(own, 0) >> 4, -1)

    dark = lt.dominant(own[opaque & (lum <= GAP)], prefer="mode")
    DARK = pal(3 if dark is None else dark)

    # What isn't boulder or gap is relief ("special"): purple, metal, rings, lava.
    if recipe == "metal":
        special = opaque.copy()
    elif recipe in ("pit", "inlay"):
        # Everything but the grey stones: the hole (dark, with glowing lava) and its gold rim, as
        # relief: bright parts up, the dark hole down.
        red = opaque & np.vectorize(lambda v: v >= 0 and is_red(ts, v))(own)
        near = lt.blur(red.astype(float), 3.0) > 0.04 if recipe == "pit" else np.zeros_like(opaque)
        special = opaque & ((ramp != 0) | near)
    else:
        special = opaque & (lum > GAP) & ~np.isin(ramp, list(STONE_RAMPS))
    heights = np.zeros_like(lum)
    cell_mat = {}
    if special.any():
        snap = lt.Snapper(ts, own[special], limit=opts.get("colours", 4))
        amp = opts.get("relief", 0.04)
        rel = lt.relief_heights(ts, np.where(special, own, -1), abs(amp), sigma=opts.get("sigma", 1.2))
        heights = np.where(special, opts.get("base", 0.0) + np.sign(amp) * rel, 0.0)
        for y, x in zip(*np.nonzero(special)):
            idx = snap(own[y, x])
            glow = opts.get("glow", 0) if is_red(ts, idx) else 0
            cell_mat[(x, y)] = pal(idx, emission_strength=glow) if glow else pal(idx)

    drop = np.zeros_like(lum)
    if recipe == "underside":
        # The face hangs from the row where the island's stones end down to -drop at the bottom.
        start = np.full(w, h * 0.3)
        for x in range(w):
            col = np.nonzero(opaque[:, x] & (lum[:, x] > GAP))[0]
            col = col[col < h * 0.55]
            if len(col):
                start[x] = col.max() + 1
        for y in range(h):
            drop[y, :] = -opts["drop"] * np.clip((y - start) / max(1.0, h - start.min()), 0, 1) ** 0.8
        snap = lt.Snapper(ts, own[opaque & (drop < -0.01)], limit=5)
        for y, x in zip(*np.nonzero(opaque & (drop < -0.01))):
            cell_mat[(x, y)] = pal(snap(own[y, x]))

    bm = bmesh.new()
    bottom = SLAB_BOTTOM + min(0.0, drop.min(), heights.min())
    lt.mask_slab(bm, opaque, frame, bottom, SLAB_TOP, lambda x, y: cell_mat.get((x, y), DARK), DARK,
                 top_height=heights + drop)
    lt.dissolve_coplanar(bm)

    covered = np.zeros_like(opaque)  # where a hand-built part stands
    if "drum" in opts:
        covered |= drum(bm, pal, frame, own, *opts["drum"])
    if "orb" in opts:
        covered |= orb(bm, pal, frame, own, *opts["orb"])

    if recipe != "metal":
        def keep(ys, xs):
            # A stone stays if most of its pixels in this tile are stone (not relief, not hanging).
            inside = (ys >= 0) & (ys < h) & (xs >= 0) & (xs < w)
            yi, xi = ys[inside], xs[inside]
            if len(yi) == 0:
                return True
            stone = ~special[yi, xi] & (drop[yi, xi] > -0.05) & ~covered[yi, xi]
            return stone.mean() > 0.6
        lt.boulders(ts, n, pal, bm, keep=keep, gap=GAP, quantile=0.3)

    return [lt.mesh(f"{SHAPES}-{name}", bm, pal, coll, smooth=False)]


def drum(bm, pal, frame, own, cx, cy, half, radius, point):
    """A drum lying along x with its axis at pixel (cx, cy): wooden body, darker bands at its ends
    and middle, and a cone pointing `point` (+1 right, -1 left). Squashed in height to stay
    within the layer. Returns the 2x pixels it covers."""
    import math
    body = [v for v in own[int((cy - radius) * 2):int((cy + radius) * 2), int((cx - half) * 2):int((cx + half) * 2)].ravel() if v >= 16 and v < 32]
    wood = lt.dominant(body, None, prefer="mode") or 20
    band = min(body) if body else 16
    WOOD, BAND = pal(wood, roughness=0.7), pal(band, roughness=0.6, metallic=0.3)
    r = radius * lt.PX
    zr = 0.32  # vertical radius (the layer's room above its base)
    x0, x1 = frame.x((cx - half) * 2), frame.x((cx + half) * 2)
    y = frame.y(cy * 2)
    sides = 16

    def ring(x, scale):
        return [bm.verts.new((x, y + r * scale * math.cos(2 * math.pi * i / sides), zr * scale * math.sin(2 * math.pi * i / sides) - 0.02))
                for i in range(sides)]

    def join(a, b, mat):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat

    # Body with bands: (x fraction along the body, radius scale, material of the segment after it).
    stations = [(0.0, 0.92, BAND), (0.1, 1.0, WOOD), (0.42, 1.0, BAND), (0.58, 1.0, WOOD), (0.9, 1.0, BAND), (1.0, 0.92, None)]
    rings = [(ring(x0 + (x1 - x0) * f, k), m) for f, k, m in stations]
    for (a, m), (b, _) in zip(rings, rings[1:]):
        join(a, b, m)
    back = rings[0][0] if point > 0 else rings[-1][0]
    front = rings[-1][0] if point > 0 else rings[0][0]
    bm.faces.new(list(reversed(back)) if point > 0 else back).material_index = BAND
    tip = bm.verts.new((frame.x((cx + point * (half + 4.5)) * 2), y, -0.02))
    for i in range(sides):
        j = (i + 1) % sides
        f = (front[i], front[j], tip) if point > 0 else (front[j], front[i], tip)
        bm.faces.new(f).material_index = BAND
    covered = np.zeros(own.shape, dtype=bool)
    lo, hi = (cx - half) if point > 0 else (cx - half - 4.5), (cx + half + 4.5) if point > 0 else (cx + half)
    covered[int((cy - radius) * 2):int((cy + radius) * 2), int(lo * 2):int(hi * 2)] = True
    return covered


def orb(bm, pal, frame, own, cx, cy, radius):
    """The blue orb: a glowing sphere sunk in its purple setting, and the crystals below it."""
    blue = [v for v in own.ravel() if v >> 4 == 3]
    BLUE = pal(lt.dominant(blue, None, prefer="mode") or 52, emission_strength=0.8, roughness=0.2, metallic=0.1)
    r = radius * lt.PX
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=r)
    for v in bm.verts[-(20 * 11 + 2):]:
        v.co.x += frame.x(cx * 2)
        v.co.y += frame.y(cy * 2)
        v.co.z = v.co.z * 0.6 + 0.02
    start = len(bm.faces) - 20 * 12
    bm.faces.ensure_lookup_table()
    for f in bm.faces[start:]:
        f.material_index = BLUE
        f.smooth = True
    # Crystal shards bottom left and right, where the art has blue pixels below the orb.
    for px, py in ((4.0, 19.0), (20.0, 19.5)):
        lt.dome(bm, frame.x(px * 2), frame.y(py * 2), 0.17, 0.12, 0.6 if px < 12 else -0.6, 0.0, 0.16, BLUE, sides=5, rings=1)
    covered = np.zeros(own.shape, dtype=bool)
    yy, xx = np.mgrid[0:own.shape[0], 0:own.shape[1]]
    covered |= (xx / 2 - cx) ** 2 + (yy / 2 - cy) ** 2 < (radius + 1) ** 2
    return covered


def main():
    ts = lt.Tileset(ROOT, SHAPES, layer=LAYER)
    preview = lt.preview_arg()
    only = {int(a) for a in sys.argv[sys.argv.index("--") + 1:] if a.isdigit()} if "--" in sys.argv else set()
    for n, (recipe, opts) in TILES.items():
        if only and n not in only:
            continue
        objects = build(ts, n, recipe, opts)
        lt.export_tile_model(ts, objects, f"t{n}", LAYER, [[n]])
        if preview:
            lt.preview(ts, objects, [[n]], Path(preview) / f"{SHAPES}-t{n}.png", view_px=240)


main()
