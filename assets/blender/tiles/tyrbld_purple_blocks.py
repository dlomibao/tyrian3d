"""TYRIAN's purple blocks (map 1-9, layer 2), hard-surface (D65 / D141 standard).

Three structures of the same stone: the 2x2 (155 157 / 175 177), the 2x3 (155 156 157 / 175 176 177)
and the 2x5 (155 156 156 156 157 / 175 176 176 176 177). Read off the tiles (and their render in the
game at t3300 / t5000 / t5230, where the art's shapes read clearly):

- every cell carries an octagonal boss: the broken socket the tiles paint (lib_sockets, D115), in an
  octagonal stepped collar on a chamfered plinth traced from the purple the tiles paint;
- between the two rows a raised chamfered deck carries the slab's face: under every 156 boss an
  upright plate pair in its own recess (the art's light 'A' plate and mid '9' plate, split by a
  panel gap), on every cell seam a ringed disc (x = 24k - 2.5, y 26), and on the 155 end a single
  plate left of the first disc;
- chamfered bridges fill the gaps between neighbouring bosses, above (y 12.6-19.6) and below
  (y 32.4-38.4) the face;
- on the 157 end the art's small light element (index 90, x 5-8, rows 25-31, ringed by 84-86):
  two small stacked plates in one recess;
- the island rock round it (Structure.rock, plain, never baked).

The scene is emptied before each block (clear_scene): the bake's AO saw every object in the file.

Every cell carries a top enemy, so the whole block stays under 0.32 (L2_ENEMY_MAX 0.33): the bosses'
chunks top out at SOCKET_TOP 0.30, the face at 0.22.

Colours: the art's own index per region (median of the region's purple pixels by brightness, darkest
and brightest fifth dropped: lighting), printed at build time.

Tile models draw no ink outline (structureInstances.ts turns it off: tiles join edge to edge, D8),
so no outline shell (it would draw nothing, only add an instanced draw and a shadow caster, D141).

Run from the worktree root (tools/build-models.sh bakes nothing over it: maps.json says "bake": "model"):

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_purple_blocks.py -- [--no-bake] [--preview dir]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402

TW, TH = lt.TILE_W, lt.TILE_H

# Heights (layer 2: z = 0 the island's rock top).
FOOT = -0.04  # bottoms of the stone
PLINTH_Z = 0.11  # the plinth under the bosses and the body
DECK_Z = 0.165  # the body's deck (the slab face)
BAY_Z = 0.15  # floor of a plate recess
PLATE_Z = 0.205  # face plates
DISC_Z = 0.20  # the seam discs' ring top
CONN_Z = 0.195  # bridges between bosses
COLLAR_Z = 0.205  # the octagonal collar round each socket
SOCKET_Z0 = 0.065  # broken sockets stand from here (floor at z0 + 0.3 * (0.30 - z0))

BAKE_SIZE = 2048  # px: 1024 (the default here) left the many small chamfer islands a texel or two, and the
# mipmaps bled neighbouring islands into each other (ghost shapes on the plates in game)
COLLAR_R = 8.6  # px, the collar's outer vertex radius (9.0 left the bosses' diagonal corners ~1 px fuller than the art)
BOSS_MASK_R = 9.0  # px, the boss regions for the colour sampling (kept as measured: plinth 87 on every block)
BAY_INDEX = 85  # recess floors (the art's seams between the plates: 84-86)
BODY_Y = (12.0, 37.6)  # the deck between the rows (px)
BODY_X0, BODY_X1 = 14.0, 13.0  # its ends: x0, and W - x1 (the art's body runs x 13 .. W-12)
FACE_Y = (20.6, 31.4)  # the face plates' rows
END_Y = (24.9, 31.2)  # the 157 end's light element
DISC_DX, DISC_Y, DISC_R = -2.5, 26.0, 3.7  # seam discs: x = 24k + DISC_DX


def region_index(s, mask, lo=0.2, hi=0.8):
    """The art's palette index for a region: the median of its purple pixels by brightness, the
    darkest and brightest fifth dropped (shading and highlights are lighting)."""
    vals = s.grid[mask & (s.grid >= 0) & s.ramp_mask(5)]
    if len(vals) == 0:
        return None
    lum = s.ts.lum
    vals = sorted((int(v) for v in vals), key=lambda v: lum[v])
    n = len(vals)
    core = vals[int(n * lo):max(int(n * lo) + 1, int(n * hi))]
    return core[len(core) // 2]


def layout(s):
    """Boss centres, plate pairs, single plates, seams and discs (pattern px) for this block."""
    n = s.cols
    bosses = []
    for r in range(2):
        for c in range(n):
            bx, by = ls.BOSS_AT[s.pattern[r][c]]
            bosses.append((c * TW + bx, r * TH + by))
    seams = [k * TW for k in range(1, n)]
    discs = [(sx + DISC_DX, DISC_Y) for sx in seams]
    pairs, singles, ends = [], [], []
    for c in range(n):
        t, ox = s.pattern[0][c], c * TW
        if t == 156:
            pairs.append(((ox + 5.0, ox + 11.55), (ox + 12.45, ox + 19.0)))
        elif t == 155:
            singles.append((ox + 13.0, ox + 17.4))
        elif t == 157:  # the art's small light element: index 90 at x 5-7 rows 25-30, ringed by 84-86
            ends.append((ox + 4.9, ox + 8.1))
    return bosses, pairs, singles, ends, seams, discs


def clear_scene():
    """Delete every object in the file before a block is built. The bake's AO rays hit everything
    in the scene: --factory-startup's default Cube (2 units round the origin) and the blocks built
    earlier in this run (they share the origin) were baked in as ghost lines, plate-sized blots and
    boss outlines on the bridges, plates and boss tops (fix round 1). Shared fix to report:
    Building.bake_model should occlude only with its own objects."""
    for o in list(bpy.data.objects):
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)
    bpy.context.view_layer.update()  # or view_layer.objects still lists the removed ones (as None)


def build(name, bake=True, preview=None):
    clear_scene()
    s = tb.Structure(name)
    W, H = s.W, s.H
    stone = s.purple_mask()
    bosses, pairs, singles, ends, seams, discs = layout(s)

    # Region masks (art px) for the colours.
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    boss_m = np.zeros((H, W), bool)
    for bx, by in bosses:
        boss_m |= ls.octagon_mask(xx, yy, bx, by, BOSS_MASK_R)
    body_m = s.box_mask(BODY_X0, BODY_Y[0], W - BODY_X1, BODY_Y[1]) & ~boss_m
    face_l, face_r, single_m = (np.zeros((H, W), bool) for _ in range(3))
    for (a0, a1), (b0, b1) in pairs:
        face_l |= s.box_mask(a0, FACE_Y[0], a1, FACE_Y[1])
        face_r |= s.box_mask(b0, FACE_Y[0], b1, FACE_Y[1])
    for x0, x1 in singles:
        single_m |= s.box_mask(x0, FACE_Y[0], x1, FACE_Y[1])
    end_m = np.zeros((H, W), bool)
    for x0, x1 in ends:
        end_m |= s.box_mask(x0, END_Y[0], x1, END_Y[1])
    disc_ring, disc_cap = np.zeros((H, W), bool), np.zeros((H, W), bool)
    for dx, dy in discs:
        d = np.hypot(xx - dx, yy - dy)
        disc_ring |= (d <= DISC_R) & (d > DISC_R * 0.62)
        disc_cap |= d <= DISC_R * 0.62
    conn_top, conn_bot = np.zeros((H, W), bool), np.zeros((H, W), bool)
    for sx in seams:
        conn_top |= s.box_mask(sx - 2.5, 13.0, sx + 3.5, 19.5)
        conn_bot |= s.box_mask(sx - 2.0, 32.5, sx + 4.0, 38.5)
    ring = boss_m & ~lb.erode(boss_m, 2)
    deck_m = body_m & ~face_l & ~face_r & ~single_m & ~end_m & ~disc_ring & ~disc_cap & ~conn_top & ~conn_bot

    idx = dict(
        plinth=region_index(s, ring & stone) or 87,
        deck=region_index(s, deck_m & stone) or 88,
        plate_l=region_index(s, face_l) or 90,
        plate_r=region_index(s, face_r) or 89,
        single=region_index(s, single_m) or 89,
        end=region_index(s, end_m) or 90,
        disc_ring=region_index(s, disc_ring) or 88,
        disc_cap=region_index(s, disc_cap) or 89,
        conn_top=region_index(s, conn_top) or 89,
        conn_bot=region_index(s, conn_bot) or 89,
    )
    print(f"{name}: region indices {idx}")
    M = {k: s.m(v, roughness=0.62 if k == "plinth" else 0.56) for k, v in idx.items()}
    bay = s.m(BAY_INDEX, roughness=0.75)

    # The plinth: one chamfered slab over the purple the tiles paint (its outline traced and
    # simplified: the bosses' octagons and the body between them, no pixel steps).
    s.slab_mask(stone, FOOT, PLINTH_Z, M["plinth"], tol=0.9, chamfer_px=1.2, drop=0.03)
    # The deck: a raised tier inset from the plinth between the rows (a machined step).
    x0, x1 = BODY_X0, W - BODY_X1
    y0, y1 = BODY_Y
    # Kept out of the sockets (their floor, 0.13, shows in the cracks: anything higher there would
    # show through them): cut round each boss under its collar.
    excl = np.zeros((H, W), bool)
    for bx, by in bosses:
        excl |= ls.octagon_mask(xx, yy, bx, by, COLLAR_R - 0.6)
    s.slab_mask(s.box_mask(x0, y0, x1, y1) & ~excl, PLINTH_Z - 0.02, DECK_Z, M["deck"], tol=0.6, chamfer_px=1.0, drop=0.025)

    # Upright plate pairs under the 156 bosses, each in its own recess: a dark floor sunk into the
    # deck shows round the pair and in the panel gap between its halves.
    for (a0, a1), (b0, b1) in pairs:
        s.slab(s.rounded_box(a0 - 0.7, FACE_Y[0] - 0.7, b1 + 0.7, FACE_Y[1] + 0.7, 1.0, 1), BAY_Z - 0.03, DECK_Z + 0.004,
               bay, chamfer_px=0)
        s.slab(s.rounded_box(a0, FACE_Y[0], a1, FACE_Y[1], 0.8, 1), BAY_Z - 0.01, PLATE_Z, M["plate_l"],
               chamfer_px=0.7, drop=0.02)
        s.slab(s.rounded_box(b0, FACE_Y[0], b1, FACE_Y[1], 0.8, 1), BAY_Z - 0.01, PLATE_Z - 0.006, M["plate_r"],
               chamfer_px=0.7, drop=0.02)
        # rivets at the pair's outer corners
        s.bolts([(a0 + 1.4, FACE_Y[0] + 1.3), (a0 + 1.4, FACE_Y[1] - 1.3), (b1 - 1.4, FACE_Y[0] + 1.3), (b1 - 1.4, FACE_Y[1] - 1.3)],
                PLATE_Z - 0.006, r_px=0.45, height=0.01, mat=M["plinth"])
    for a0, a1 in singles:
        s.slab(s.rounded_box(a0 - 0.6, FACE_Y[0] - 0.6, a1 + 0.6, FACE_Y[1] + 0.6, 1.0, 1), BAY_Z - 0.03, DECK_Z + 0.004,
               bay, chamfer_px=0)
        s.slab(s.rounded_box(a0, FACE_Y[0], a1, FACE_Y[1], 0.8, 1), BAY_Z - 0.01, PLATE_Z - 0.01, M["single"],
               chamfer_px=0.7, drop=0.02)
    # The 157 end's light element: two small stacked plates (the art's row-28 split) in one recess.
    for a0, a1 in ends:
        s.slab(s.rounded_box(a0 - 0.6, END_Y[0] - 0.6, a1 + 0.6, END_Y[1] + 0.6, 0.9, 1), BAY_Z - 0.03, DECK_Z + 0.004,
               bay, chamfer_px=0)
        ym = (END_Y[0] + END_Y[1]) / 2
        for b0, b1 in ((END_Y[0], ym - 0.35), (ym + 0.35, END_Y[1])):
            s.slab(s.rounded_box(a0, b0, a1, b1, 0.6, 1), BAY_Z - 0.01, PLATE_Z - 0.012, M["end"], chamfer_px=0.5, drop=0.015)
    # Seam discs: a stepped ring round a low domed cap.
    for dx, dy in discs:
        # a dark groove round it, sunk into the deck (the art's dark ring round each disc)
        s.slab(s.ngon(dx, dy, DISC_R + 0.75, 16), BAY_Z - 0.03, DECK_Z + 0.004, bay, chamfer_px=0)
        s.slab(s.ngon(dx, dy, DISC_R, 16), BAY_Z - 0.02, DISC_Z, M["disc_ring"], chamfer_px=0.6, drop=0.018)
        s.slab(s.ngon(dx, dy, DISC_R * 0.66, 16), DISC_Z - 0.03, DISC_Z - 0.012, bay, chamfer_px=0)
        s.dome(dx, dy, DISC_R * 0.52, DISC_R * 0.52, DISC_Z - 0.02, 0.035, M["disc_cap"], sides=16, rings=4)

    # Bridges between neighbouring bosses, above and below the face: chamfered blocks whose ends
    # run in under the bosses' collars.
    for sx in seams:
        s.slab_mask(s.box_mask(sx - 4.0, 12.6, sx + 4.8, 19.6) & ~excl, PLINTH_Z, CONN_Z, M["conn_top"], tol=0.6,
                    chamfer_px=0.9, drop=0.02)
        s.slab_mask(s.box_mask(sx - 4.0, 32.4, sx + 5.2, 38.4) & ~excl, PLINTH_Z, CONN_Z, M["conn_bot"], tol=0.6,
                    chamfer_px=0.9, drop=0.02)
    # Each boss's collar: an octagonal stepped ring round the socket (the art's darker ring round
    # every boss), over the plinth.
    for bx, by in bosses:
        s.rim(ls.octagon(bx, by, COLLAR_R), 1.1, PLINTH_Z - 0.01, COLLAR_Z, M["plinth"], chamfer_px=0.45, drop=0.015)

    # The broken sockets on every cell (D115): the bosses the tiles paint, shattered.
    s.broken_sockets(SOCKET_Z0)

    # The island's rock round it, boulders kept off the stone (plain: the bake leaves it alone).
    s.rock(exclude=lb.erode(stone, 3))

    objects = s.objects()
    s.check(objects)
    s.top_iou(objects, stone)
    if bake:
        objects = s.bake_model(objects, size=BAKE_SIZE)
    if preview:
        lt.preview(s.ts, objects, s.pattern, Path(preview) / f"{tb.SHAPES}-tyrbld-{name}.png", view_px=480)
    s.export(objects, baked=bake)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for nm in ("purple-2x2", "purple-2x3", "purple-2x5"):
    build(nm, bake="--no-bake" not in argv, preview=lt.preview_arg())
