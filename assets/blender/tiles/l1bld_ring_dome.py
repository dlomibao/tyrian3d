"""The ring platform of map 1-3's ground (shapesz.dat; 7 x 10 tiles, map rows 154-160, cols 2-11),
after the concept assets/blender/features/concepts/l1-bld-ring-dome.jpg: a paved U of asteroid rock,
its top bar a band of lights (two framed red panels 347, two triple red tubes 339, two brass gun
turrets 358 between them), each arm carrying two round orb sockets (357), and inside the U a separate
paved pad with a metal dome (415 417 / 409 383). The game draws ground enemies (newshs 195/235 on the
lights, newshd 275 on the gun mounts, newshd 127 on the orbs) at 0.45 exactly over these cells, so
the building's own lights, turrets and sockets stay under ENEMY_MAX and show once they're destroyed.

The rim is a band of rounded, faceted boulders (this script's own boulder(): a jittered, flat-shaded
icosphere), not the library's rim_rocks() prisms: an outer row that forms the platform's edge (the
deck is cut from a smoothed, slightly shrunk footprint, so the rocks overhang its pixel-stepped wall)
and a sparse inner row near the edge only. The paving's plates are inlaid (bricks; a basket weave on the pad).

Only ring-dome is built here (ring-dome-b, the second ring, is its own script). Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/l1bld_ring_dome.py
    python tools/concept_maps.py tile:shapesz-l1bld-ring-dome --concept l1-bld-ring-dome
    blender --background --factory-startup --python assets/blender/tiles/l1bld_ring_dome.py   # again, see below
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-l1bld-ring-dome

The concept paves the pad and paints the sprite's highlight where the dome stands; the build
neutralises the concept detail and relief under the dome (assets/blender/textures/shapesz-l1bld-ring-dome/
detail.png, height.png) so the bake doesn't paint bricks and a fake highlight on it. Re-running
concept_maps.py undoes that, so run this script once more after it (as above).
"""

import math
import random
import struct
import sys
import zlib
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_l1bld as lb  # noqa: E402
import lib_tiles as lt  # noqa: E402

DECK = 0.30  # the U's paving
PAD_DECK = 0.27  # the inner pad, a step lower (it reads as a separate island in the concept)
PAD_TOP = (72, 84, 168, 196)  # the inner pad's cells (rows 3-6, cols 3-6) in px
GROOVE = 0.025  # the paving's inlaid plate seams

# The light band (row 1, py 28-56); pixel boxes from the tiles (mirror-symmetric about px 120).
RED_PANELS = [(51, 32, 68, 54), (172, 32, 189, 54)]  # 347: framed red panels
TUBES_X = [(78.0, 84.0, 90.0), (150.0, 156.0, 162.0)]  # 339: three vertical red tubes per cell
TUBE_FRAME = [(73, 34, 95, 56), (145, 34, 167, 56)]
MOUNTS = [(108.0, 44.0), (132.0, 44.0)]  # 358: gun turrets (cell centres)
ORBS = [(36.0, 70.0), (36.0, 98.0), (204.0, 98.0), (204.0, 126.0)]  # 357: orb sockets (cell centres)
DOME = (120.0, 140.0)  # centre of the 415 417 / 409 383 square
DOME_R = 16.5  # px
DOME_PLATE = (99, 115, 141, 165)
# Vents: small grilles cut into the paving just inside the rim (the concept's slots above the lights
# and at the arms' top).
VENTS = [(60, 22), (83, 22), (107, 22), (133, 22), (157, 22), (180, 22), (36, 49), (204, 49)]
LIGHT_TOP = lb.ENEMY_MAX - 0.01
ROCK_TOP = lb.RIM_MAX


def disc(b, px, py, r_px, z0, z1, mat, sides=20, bevel=0.25, ry_px=None):
    """A round bevelled plate (lib_tiles.block with many sides) from z0 to z1."""
    bm = bmesh.new()
    lt.block(bm, b.x(px), b.y(py), r_px * lt.PX, (ry_px or r_px) * lt.PX, 0.0, z0, z1 - z0, mat, sides=sides, bevel=bevel)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)


def cylinder(b, p0, p1, r, mat, sides=10):
    """A closed cylinder between two points (units)."""
    p0, p1 = Vector(p0), Vector(p1)
    axis = p1 - p0
    rot = axis.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r, radius2=r, depth=axis.length,
                          matrix=Matrix.Translation((p0 + p1) / 2) @ rot)
    for f in bm.faces:
        f.material_index = mat
    b._merge(bm)


def blur(a, r):
    """Box blur (twice, about a Gaussian) of a float array, radius r px."""
    out = a.astype(np.float32)
    for _ in range(2):
        for axis in (0, 1):
            pad = [(0, 0), (0, 0)]
            pad[axis] = (r + 1, r)
            c = np.cumsum(np.pad(out, pad), axis=axis)
            hi = np.take(c, range(2 * r + 1, c.shape[axis]), axis=axis)
            lo = np.take(c, range(0, c.shape[axis] - 2 * r - 1), axis=axis)
            out = (hi - lo) / (2 * r + 1)
    return out


def boulder(b, rng, px, py, r_px, top, z_base, mat):
    """A rounded, faceted boulder: an icosphere squashed to the rock's height, jittered, turned at
    random and cut flat at z_base (it stands on / in the deck). r_px: its radius across (px)."""
    rx = r_px * lt.PX * (0.85 + 0.3 * rng.random())
    ry = r_px * lt.PX * (0.85 + 0.3 * rng.random())
    zc = top - (top - z_base) * 0.55  # the widest girth sits a little below mid height
    rz = top - zc
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    ang = rng.random() * math.tau
    ca, sa = math.cos(ang), math.sin(ang)
    for v in bm.verts:
        x, y, z = v.co
        j = 0.82 + 0.3 * rng.random()  # chunky facets
        x, y, z = x * j, y * j, z * (0.9 + 0.2 * rng.random())
        z = max(z, -0.15)  # a broad base
        lx, ly = x * rx, y * ry
        v.co = Vector((b.x(px) + lx * ca - ly * sa, b.y(py) + lx * sa + ly * ca, zc + z * rz))
    # Flatten the bottom onto z_base (below the deck) and the top to its cap.
    for v in bm.verts:
        if v.co.z < z_base:
            v.co.z = z_base
        v.co.z = min(v.co.z, top)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for f in bm.faces:
        f.material_index = mat
        f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)


def place_rocks(b, rng, d, mask, r_rng, top_rng, gap, taken, mats, dz_base):
    """Boulders on candidate pixels `mask` (shuffled), each kept apart from the others by `gap` x the
    sum of radii. Returns the number placed; appends (px, py, r) to `taken`."""
    ys, xs = np.nonzero(mask)
    order = list(range(len(ys)))
    rng.shuffle(order)
    n = 0
    for i in order:
        px, py = xs[i] + 0.5, ys[i] + 0.5
        r = r_rng[0] + (r_rng[1] - r_rng[0]) * rng.random()
        if any((qx - px) ** 2 + (qy - py) ** 2 < ((qr + r) * gap) ** 2 for qx, qy, qr in taken):
            continue
        taken.append((px, py, r))
        top = top_rng[0] + (top_rng[1] - top_rng[0]) * rng.random()
        y0, y1 = int(max(0, py - r - 1)), int(min(b.H, py + r + 2))
        x0, x1 = int(max(0, px - r - 1)), int(min(b.W, px + r + 2))
        if b.enemy_mask[y0:y1, x0:x1].any():
            top = min(top, lb.ENEMY_MAX)
        here = b.height[min(b.H - 1, int(py)), min(b.W - 1, int(px))]
        base = lb.SLAB_BOTTOM if (np.isnan(here) or d[int(py), int(px)] <= 4) else float(here) - dz_base
        boulder(b, rng, px, py, r, top, base, mats[rng.randrange(len(mats))])
        n += 1
    return n


def write_png_grey(path, a):
    """An 8-bit greyscale PNG from a uint8 array (no PIL in Blender)."""
    h, w = a.shape
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def neutralise_dome(b):
    """Concept detail -> neutral and relief -> flat under the dome (and its drum), if the concept maps
    exist: the concept paves this spot and paints the sprite's highlight on it."""
    tex = lb.ROOT / "assets/blender/textures" / f"{lb.SHAPES}-l1bld-{b.name}"
    meta_path = tex / "maps.json"
    if not meta_path.exists():
        return
    import json
    meta = json.loads(meta_path.read_text())
    k = meta["texels_per_px"]
    for name, value in (("detail.png", meta["neutral"]), ("height.png", None)):
        path = tex / name
        img = bpy.data.images.load(str(path))
        w, h = img.size
        px = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(px)
        a = px.reshape(h, w, 4)[::-1, :, 0].copy()  # top row first
        bpy.data.images.remove(img)
        yy, xx = np.mgrid[0:h, 0:w]
        rr = np.hypot((xx + 0.5) / k - DOME[0], (yy + 0.5) / k - DOME[1])
        r0 = DOME_R + 2.0
        f = np.clip((rr - r0) / 1.5, 0.0, 1.0)  # 0 inside, 1 outside
        if value is None:
            value = float(np.median(a))  # the relief's flat level
        a = a * f + value * (1 - f)
        write_png_grey(path, np.clip(np.round(a * 255), 0, 255).astype(np.uint8))
    print(f"neutralised the dome in {tex.relative_to(lb.ROOT)}/detail.png, height.png")


def plate_seams(b, pad):
    """The paving's plate seams (1 px): running-bond bricks (12 x 7 px) on the U, as on its tiles and
    in the concept, and a basket weave of planks (12 x 14 px blocks, two planks each, alternating
    across and along) on the inner pad."""
    yy, xx = np.mgrid[0:b.H, 0:b.W]
    row = yy // 7
    bricks = (yy % 7 == 0) | ((xx + np.where(row % 2 == 1, 6, 0)) % 12 == 0)
    px0, py0 = PAD_TOP[0], PAD_TOP[1]
    lx, ly = (xx - px0) % 12, (yy - py0) % 14
    across = (((xx - px0) // 12 + (yy - py0) // 14) % 2) == 0
    weave = (lx == 0) | (ly == 0) | np.where(across, ly == 7, lx == 6)
    return np.where(pad, weave, bricks)


def main():
    rng = random.Random("ring-dome-v2")
    b = lb.Building("ring-dome")
    b.surface(deck=DECK, channel=False, pits=False, red=False)
    pave, metal, dark = b.m("pave"), b.m("metal"), b.m("dark")
    fp = b.footprint
    d_fp = lb.depth(fp)

    # The deck: a smoothed outline, pulled 2 px inside the painted one (the boulders form the edge).
    smooth = (blur(fp.astype(np.float32), 3) > 0.5) & b.cover
    deck_mask = lb.erode(smooth, 2) & fp
    b.height[~deck_mask] = np.nan
    b.mat[~deck_mask] = -1

    # The inner pad, a step lower than the U, with its own chamfered square plate under the dome.
    pad = b.box_mask(*PAD_TOP) & ~b.box_mask(0, 0, 240, 92)
    b.set_region(pad & deck_mask, PAD_DECK)
    # Inlaid seams of the plates (U arms and pad; not in the band, the rim or under the dome plate).
    g = plate_seams(b, pad) & deck_mask & (d_fp > 8)
    g &= ~b.box_mask(44, 26, 196, 60)
    for ox, oy in ORBS:
        g &= ~b.box_mask(ox - 11, oy - 11, ox + 11, oy + 11)
    for vx, vy in VENTS:
        g &= ~b.box_mask(vx - 5, vy - 6, vx + 5, vy + 6)
    base_h = np.where(pad, PAD_DECK, DECK)
    b.height[g] = base_h[g] - GROOVE
    b.mat[g] = b.m(4)
    x0, y0, x1, y1 = DOME_PLATE
    b.set_region(b.box_mask(x0, y0, x1, y1) & deck_mask, PAD_DECK + 0.03, pave)
    b.set_region(b.box_mask(x0 + 2, y0 + 2, x1 - 2, y1 - 2) & deck_mask, PAD_DECK + 0.06, b.m(7))

    # The light band: a sunk dark trough the lights stand in.
    b.raise_box(48, 31, 192, 57, DECK - 0.02, b.m(3))
    # Vents: shallow dark slots.
    for vx, vy in VENTS:
        b.raise_box(vx - 3.5, vy - 5, vx + 3.5, vy + 5, DECK - 0.03, b.m(2))
    deck = b.terrace()

    # Vent slats (thin bars across each slot).
    for vx, vy in VENTS:
        for sx in (-1.75, 0, 1.75):
            b.wall_block(vx + sx - 0.5, vy - 4, vx + sx + 0.5, vy + 4, DECK - 0.04, DECK - 0.005, b.m(5), bevel=0.0)

    # Red panels (347): metal frame round a glowing red panel crossed by dark slats.
    red_glow = b.m("red", emission_strength=4.0)
    for (px0, py0, px1, py1) in RED_PANELS:
        b.hatch(px0, py0, px1, py1, z=LIGHT_TOP, frame_px=2, depth_=0.05, mat_frame=metal, mat_inside=red_glow)
        for sy in range(py0 + 5, py1 - 3, 4):
            b.wall_block(px0 + 3, sy - 0.6, px1 - 3, sy + 0.6, DECK - 0.05, LIGHT_TOP - 0.02, b.m(2), bevel=0.0)

    # Triple tubes (339): a framed trough, its floor dimly lit red (the tubes' glow), with three round
    # glowing capsules lying in it, half of each showing.
    tube_r = 2.3  # px
    trough = LIGHT_TOP - 2 * tube_r * lt.PX * 0.55
    for (fx0, fy0, fx1, fy1), xs in zip(TUBE_FRAME, TUBES_X):
        b.hatch(fx0, fy0, fx1, fy1, z=LIGHT_TOP, frame_px=1.5, depth_=LIGHT_TOP - trough,
                mat_frame=b.m("red_dark"), mat_inside=b.m(114, emission_strength=1.2, roughness=0.6))
        for tx in xs:
            b.capsule(tx, (fy0 + fy1) / 2, fy1 - fy0 - 5, tube_r, axis="y", z=LIGHT_TOP - 0.005,
                      mat=b.m("red", emission_strength=5.0, roughness=0.15), housing=False, sides=12)

    # Gun turrets (358): a dark base ring, a brass turret body with a domed top and a short barrel
    # pointing down the screen (towards the player), all under the enemy drawn on top.
    brass = b.m(24, metallic=0.75, roughness=0.35)
    brass_dk = b.m(21, metallic=0.6, roughness=0.45)
    for mx, my in MOUNTS:
        disc(b, mx, my, 10.5, DECK - 0.05, DECK + 0.02, b.m(3, metallic=0.4, roughness=0.5), sides=16)
        disc(b, mx, my, 8.0, DECK - 0.05, DECK + 0.045, brass_dk, sides=16, bevel=0.3)
        disc(b, mx, my - 1.0, 6.0, DECK - 0.05, DECK + 0.055, brass, sides=14, bevel=0.2)
        b.dome(mx, my - 1.0, 5.5, 5.5, DECK + 0.05, lb.ENEMY_MAX - 0.005 - (DECK + 0.05), brass, sides=14, rings=4)
        # Side brackets (the concept's yoke).
        for sx in (-6.5, 6.5):
            b.wall_block(mx + sx - 1.2, my - 5, mx + sx + 1.2, my + 3, DECK - 0.05, DECK + 0.07, brass_dk, bevel=0.3)
        # Barrel: from the body's front down-screen, slightly sloped.
        br = 0.9 * lt.PX
        zb = lb.ENEMY_MAX - 0.005 - br
        cylinder(b, (b.x(mx), b.y(my + 2.0), zb), (b.x(mx), b.y(my + 11.0), zb), br, metal, sides=10)
        disc(b, mx, my + 10.0, 1.4, DECK - 0.02, zb + br * 0.9, metal, sides=10, bevel=0.0, ry_px=1.2)

    # Orb sockets (357): dark round bezel, metal ring, a glowing red lens.
    for ox, oy in ORBS:
        disc(b, ox, oy, 10.0, DECK - 0.05, DECK + 0.035, b.m(2, metallic=0.4, roughness=0.5), sides=16)
        disc(b, ox, oy, 7.0, DECK - 0.05, DECK + 0.045, metal, sides=14)
        b.dome(ox, oy, 4.5, 4.5, DECK + 0.04, 0.04, b.m("red", emission_strength=3.0), sides=12, rings=2)

    # The dome on the inner pad: a short drum, then a bright, smooth metal cupola as tall as the
    # height limit allows (a finial ring on top).
    dz0 = PAD_DECK + 0.06
    dome_mat = b.m(12, metallic=0.85, roughness=0.18)
    disc(b, *DOME, DOME_R + 1.5, dz0 - 0.03, dz0 + 0.06, b.m(7, metallic=0.5, roughness=0.4), sides=32, bevel=0.3)
    disc(b, *DOME, DOME_R, dz0, dz0 + 0.12, dome_mat, sides=32, bevel=0.0)
    b.dome(*DOME, DOME_R, DOME_R, dz0 + 0.12, lb.TALL_MAX - 0.03 - (dz0 + 0.12), dome_mat, sides=32, rings=10)
    b.dome(*DOME, 2.2, 2.2, lb.TALL_MAX - 0.06, 0.055, b.m(11, metallic=0.85, roughness=0.25), sides=12, rings=3)
    # Bolts on the plate's corners.
    for px, py in ((x0 + 3.5, y0 + 3.5), (x1 - 3.5, y0 + 3.5), (x0 + 3.5, y1 - 3.5), (x1 - 3.5, y1 - 3.5)):
        b.dome(px, py, 1.8, 1.8, PAD_DECK + 0.055, 0.04, metal, sides=10, rings=3)

    # The rocky rim: boulders, an outer row forming the edge and a sparse inner row close behind it.
    def clear(px, py, pad=0.0):
        if 44 - pad <= px <= 196 + pad and 26 - pad <= py <= 60 + pad:  # the light band
            return False
        if any((px - ox) ** 2 + (py - oy) ** 2 < (12 + pad) ** 2 for ox, oy in ORBS):
            return False
        if any(abs(px - vx) < 5 + pad and abs(py - vy) < 6 + pad for vx, vy in VENTS):
            return False
        x0_, y0_, x1_, y1_ = DOME_PLATE
        return not (x0_ - 3 - pad <= px <= x1_ + 3 + pad and y0_ - 3 - pad <= py <= y1_ + 3 + pad)

    keep = np.zeros_like(fp)
    for yy, xx in zip(*np.nonzero(fp)):
        keep[yy, xx] = clear(xx + 0.5, yy + 0.5, 0.0)
    rock_mats = [b.m(6, roughness=0.9), b.m(5, roughness=0.9)]
    taken = []
    # Outer row: rocks centred 3-4 px inside the painted outline; the bigger ones first.
    outer = keep & (d_fp >= 3) & (d_fp <= 4)
    n_out = place_rocks(b, rng, d_fp, outer, (6.0, 7.5), (0.45, ROCK_TOP), 0.74, taken, rock_mats, 0.12)
    # Fill gaps the first pass left (smaller rocks), so the edge stays closed.
    n_out += place_rocks(b, rng, d_fp, outer | (keep & (d_fp == 2)), (4.0, 5.0), (0.41, 0.47), 0.78, taken, rock_mats, 0.12)
    # Inner row: sparser and lower, staggered just behind the outer one.
    inner = keep & (d_fp >= 8) & (d_fp <= 9)
    n_in = place_rocks(b, rng, d_fp, inner, (3.5, 4.8), (0.39, 0.45), 1.0, taken, rock_mats, 0.10)
    print(f"rocks: {n_out} outer, {n_in} inner")

    objects = b.objects(deck)
    b.check(objects)
    tris = sum(len(o.data.polygons) and sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects)
    print(f"triangles: {tris}")
    b.export(objects)
    neutralise_dome(b)


main()
