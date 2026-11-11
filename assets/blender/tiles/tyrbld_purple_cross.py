"""The purple carved cross on TYRIAN's islands (map 1-9, layer 2; a 4x4 pattern with its corners cut,
centre tiles 158/159/168/169), hard-surface (D65, D141). Every part is a stack of chamfered sections
(Stack): a plinth over the art's purple outline, a raised cross deck, octagonal discs (pedestal, seat,
cap, bolts), ringed medallions, plates flanking the arms, split plates either side of the hub over
slot floors, slotted north/south plates and the centre hub (highest point 0.368). Eight broken cap
sockets stay on the rim (D115). The only texture is the model's own AO/roughness bake ("bake": "model").
The island's rock is plain (unbaked). No D51 outline shell: tile models draw no ink outline (structureInstances.ts turns it off, tiles join
edge to edge, D8), so a shell would only add an instanced draw and a shadow caster (D141).

Rings (disc seat, medal groove, hub collar) use palette 88 like the parts they sit between: their
darkness is the AO bake's lighting, not paint.

    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/tyrbld_purple_cross.py
    (or: blender --background --factory-startup --python assets/blender/tiles/tyrbld_purple_cross.py
         -- [--no-bake] [--preview <dir>/x.png])
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402


# --- Layout (pattern px), read off the tiles -------------------------------------------------------
CX, CY = 48.0, 54.5
# The raised cross: the vertical arm and the horizontal one (its ends stop between the sockets).
V_ARM = (36.5, 18.5, 59.5, 91.5)
H_ARM = (17.5, 39.5, 78.5, 68.5)
# Inner-corner octagonal discs (centre cells 158/159/168/169).
DISCS = [(36.0, 40.5), (60.0, 40.5), (36.0, 68.0), (60.0, 68.0)]
DISC_R = 7.8
# Ringed medallions on the arms, and their flanking plates (the art's lighter blocks).
MEDALS = [(CX, 29.0), (CX, 82.0), (24.0, CY), (72.0, CY)]
MEDAL_R = 4.6
ARM_PLATES = [(37.5, 23.0, 43.0, 33.5), (53.0, 23.0, 58.5, 33.5), (37.5, 76.0, 43.0, 86.5), (53.0, 76.0, 58.5, 86.5),
              (19.5, 40.5, 27.5, 47.5), (19.5, 61.5, 27.5, 68.0), (68.5, 40.5, 76.5, 47.5), (68.5, 61.5, 76.5, 68.0)]
# Split plates either side of the hub, and the slotted plates above / below it.
SPLIT = [(29.0, 48.0, 43.0, 60.5), (53.0, 48.0, 67.0, 60.5)]
NS = [(43.5, 32.5, 52.5, 47.0), (43.5, 62.0, 52.5, 76.5)]

# --- Heights (units; layer 2: z = 0 the islands' rock top) -------------------------------------------
BASE_BOT = -0.04
BASE_Z = 0.115
ARM_Z = 0.195
ENEMY_TOP = 0.315  # anything reaching into an enemy cell

# --- Palette indices (the art's per-region medians; see measure_colours()) --------------------------
P_BASE, P_ARM, P_PLATE_HI, P_PLATE, P_SLOT, P_BOLT = 87, 88, 90, 89, 86, 85
P_SPLIT_GAP = 89  # the split plates' 1 px gap floor: near the plates' own 89/90 so they read as one bright block
# Grooves and recesses take the art's index of the part round them: the AO bake darkens them.
P_GROOVE = 88
PLINTH_TOL = 1.0  # above a 1-px staircase's 0.707 deviation: straight diagonals; the lobe notches survive
ROUGH = 0.45
METAL = 0.2


class Stack:
    """A feature as a stack of chamfered sections (its cross-section, bottom to top): each section is
    (shape inset px, z0, z1, palette index, chamfer px, chamfer drop). `shape(inset)` returns the
    outline (pattern px) shrunk by `inset`."""

    def __init__(self, s, shape, regions, name):
        self.s, self.shape, self.regions, self.name = s, shape, regions, name

    def build(self, sections, rough=ROUGH, metal=METAL):
        for k, (inset, z0, z1, pal, ch, drop) in enumerate(sections):
            poly = self.shape(inset)
            self.s.slab(poly, z0, z1, self.s.m(pal, roughness=rough, metallic=metal), chamfer_px=ch, drop=drop)
            self.regions.append((f"{self.name}/{k}", poly, pal, z1))


def box(x0, y0, x1, y1, corner=1.2, seg=2):
    return lambda d: lb.Building.rounded_box(None, x0 + d, y0 + d, x1 - d, y1 - d, corner_px=max(0.3, corner - d * 0.5), segments=seg)


def ngon(px, py, r, sides, angle=None):
    return lambda d: lb.Building.ngon(None, px, py, r - d, sides, angle)


def cross_poly(v, h, notch=1.5):
    """The raised cross's outline (pattern px): the union of the two arm boxes, its four inner
    corners cut by a 45-degree chamfer `notch` px (stone isn't cut to a sharp inner corner)."""
    vx0, vy0, vx1, vy1 = v
    hx0, hy0, hx1, hy1 = h
    c = 1.0  # outer corner chamfer
    pts = [(vx0 + c, vy0), (vx1 - c, vy0), (vx1, vy0 + c),
           (vx1, hy0 - notch), (vx1 + notch, hy0),
           (hx1 - c, hy0), (hx1, hy0 + c), (hx1, hy1 - c), (hx1 - c, hy1),
           (vx1 + notch, hy1), (vx1, hy1 + notch),
           (vx1, vy1 - c), (vx1 - c, vy1), (vx0 + c, vy1), (vx0, vy1 - c),
           (vx0, hy1 + notch), (vx0 - notch, hy1),
           (hx0 + c, hy1), (hx0, hy1 - c), (hx0, hy0 + c), (hx0 + c, hy0),
           (vx0 - notch, hy0), (vx0, hy0 - notch),
           (vx0, vy0 + c)]
    return pts


def clear_scene():
    """Delete whatever the scene starts with (--factory-startup's default 2x2x2 cube at the origin):
    left in, it occludes the AO bake and paints a dark 24x24 px square round the pattern's centre."""
    import bpy
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()


def build(bake=True, preview=None):
    clear_scene()
    s = tb.Structure("purple-cross", tag="tyrbldpurplecrossA")
    stone = s.purple_mask()
    regions = []  # (name, poly, pal, top z): the top view's paint, for the colour check

    # 1. Plinth: the art's purple outline (smoothed), a vertical skirt and a 45-degree chamfer.
    for poly in s.outlines(stone, tol=PLINTH_TOL):
        s.slab(poly, BASE_BOT, BASE_Z, s.m(P_BASE, roughness=ROUGH + 0.06, metallic=METAL), chamfer_px=1.4, drop=0.035)
        regions.append(("plinth", poly, P_BASE, BASE_Z))

    # 2. The raised cross deck: wall, chamfer; a narrow kerb step (0.5 px) along its foot so the
    #    deck reads as a separate machined plate seated on the plinth.
    cp = cross_poly(V_ARM, H_ARM)
    s.slab(ls.inset(cp, -0.5), BASE_Z - 0.02, BASE_Z + 0.012, s.m(P_SLOT, roughness=0.7), chamfer_px=0)
    s.slab(cp, BASE_Z - 0.03, ARM_Z, s.m(P_ARM, roughness=ROUGH, metallic=METAL), chamfer_px=1.3, drop=0.03)
    regions.append(("arms", cp, P_ARM, ARM_Z))

    # 3. Broken cap sockets round the rim (D115), under the enemy ceiling.
    s.broken_sockets(BASE_Z - 0.05)

    # 4. Inner-corner discs (centre cells, always visible). Section: pedestal (chamfered octagon),
    #    a dark groove step, the cap ring, a recessed face, the centre boss; eight bolts round it.
    for px, py in DISCS:
        Stack(s, ngon(px, py, DISC_R, 8), regions, "disc").build([
            (0.0, ARM_Z - 0.03, 0.27, P_ARM, 1.6, 0.05),      # pedestal
            (1.2, 0.26, 0.282, P_GROOVE, 0.0, 0.0),            # seat step (a lower ring round the cap)
            (1.5, 0.27, 0.345, P_ARM, 1.3, 0.04),              # cap: a broad flat octagon
        ])
        r = DISC_R - 0.8
        s.bolts([(px + r * math.cos(math.radians(a)), py + r * math.sin(math.radians(a))) for a in (45, 135, 225, 315)],
                0.265, r_px=0.55, height=0.014, mat=s.m(P_BOLT, roughness=0.4, metallic=0.4))

    # 5. Arm medallions (they reach into enemy cells: kept under ENEMY_TOP). Section: a 12-sided
    #    collar, a groove, a domed cap.
    for px, py in MEDALS:
        Stack(s, ngon(px, py, MEDAL_R, 12), regions, "medal").build([
            (0.0, ARM_Z - 0.02, 0.245, P_ARM, 0.9, 0.025),
            (1.1, 0.235, 0.255, P_GROOVE, 0.0, 0.0),
        ])
        s.dome(px, py, MEDAL_R - 1.5, MEDAL_R - 1.5, 0.245, 0.06, s.m(P_ARM, roughness=0.45, metallic=METAL), sides=20, rings=5)
        regions.append(("medal/dome", lb.Building.ngon(None, px, py, MEDAL_R - 1.5, 20), P_ARM, 0.305))

    # 6. Flanking plates on the arms: a slim inset plate with a bevel, corner bolts.
    for i, (x0, y0, x1, y1) in enumerate(ARM_PLATES):
        hi = P_PLATE_HI if i in (1, 3, 5, 7) else P_PLATE
        Stack(s, box(x0, y0, x1, y1, 1.0), regions, "arm_plate").build([
            (0.0, ARM_Z - 0.02, 0.215, hi, 0.6, 0.015),
        ])
        s.bolts([(x0 + 1.2, y0 + 1.2), (x1 - 1.2, y0 + 1.2), (x0 + 1.2, y1 - 1.2), (x1 - 1.2, y1 - 1.2)], 0.215,
                r_px=0.45, height=0.01, mat=s.m(P_BOLT, roughness=0.4, metallic=0.4))

    # 7. Split plates either side of the hub: a slot floor, two halves with a 1 px panel gap, bolts.
    for x0, y0, x1, y1 in SPLIT:
        Stack(s, box(x0, y0, x1, y1, 1.4), regions, "split_slot").build([(0.0, ARM_Z - 0.02, 0.205, P_SPLIT_GAP, 0.0, 0.0)])
        mid = (x0 + x1) / 2
        left_hi = x0 < CX  # the art's brighter half is the outer one
        for hx0, hx1, outer in ((x0 + 0.3, mid - 0.5, left_hi), (mid + 0.5, x1 - 0.3, not left_hi)):
            Stack(s, box(hx0, y0 + 0.3, hx1, y1 - 0.3, 1.1), regions, "split_plate").build([
                (0.0, 0.195, 0.24, P_PLATE_HI if outer else P_PLATE, 0.7, 0.018),
            ])
            s.bolts([(hx0 + 1.3, y0 + 1.6), (hx1 - 1.3, y0 + 1.6), (hx0 + 1.3, y1 - 1.6), (hx1 - 1.3, y1 - 1.6)], 0.24,
                    r_px=0.45, height=0.01, mat=s.m(P_BOLT, roughness=0.4, metallic=0.4))

    # 8. North / south plates between the discs: a plate with a recessed slot (a lower floor inside a
    #    rim) and a sliding cover's bar across it.
    for x0, y0, x1, y1 in NS:
        Stack(s, box(x0, y0, x1, y1, 1.4), regions, "ns_plate").build([(0.0, ARM_Z - 0.02, 0.245, P_PLATE, 0.8, 0.02)])
        s.slab(s.rounded_box(x0 + 2.0, y0 + 2.2, x1 - 2.0, y1 - 2.2, 0.8), 0.215, 0.232, s.m(P_PLATE, roughness=0.7), chamfer_px=0)
        s.rim(s.rounded_box(x0 + 2.0, y0 + 2.2, x1 - 2.0, y1 - 2.2, 0.8), 0.6, 0.225, 0.25, s.m(P_PLATE, roughness=ROUGH, metallic=METAL))
        my = (y0 + y1) / 2
        s.slab(s.rounded_box(x0 + 2.6, my - 0.8, x1 - 2.6, my + 0.8, 0.4), 0.22, 0.242, s.m(P_PLATE, roughness=0.45, metallic=0.3), chamfer_px=0.3, drop=0.006)
        regions.append(("ns_slot", s.rounded_box(x0 + 2.6, y0 + 2.8, x1 - 2.6, y1 - 2.8, 0.5), P_PLATE, 0.246))

    # 9. The centre hub, the highest point: a stepped 12-sided ring, collar, dome.
    Stack(s, ngon(CX, CY, 6.4, 12), regions, "hub").build([
        (0.0, ARM_Z - 0.02, 0.30, P_PLATE, 1.0, 0.025),
        (1.4, 0.29, 0.31, P_GROOVE, 0.0, 0.0),
        (1.9, 0.30, 0.335, P_ARM, 0.6, 0.012),
    ])
    s.dome(CX, CY, 3.4, 3.4, 0.33, 0.038, s.m(P_ARM, roughness=0.42, metallic=METAL), sides=24, rings=6)
    regions.append(("hub/dome", lb.Building.ngon(None, CX, CY, 3.4, 24), P_ARM, 0.368))

    # 10. The island's rock round it (plain, unbaked, as the per-tile islands).
    s.rock(exclude=lb.erode(stone, 3))

    objects = s.objects()
    s.check(objects)
    iou = s.top_iou(objects, stone)
    colours = measure_colours(s, regions)
    if bake:
        objects = s.bake_model(objects, ao=(0.03, 0.22))
    hard = objects[0]
    tris = sum(len(p.vertices) - 2 for p in hard.data.polygons)
    print(f"purple-cross: {tris} triangles (hard), IoU {iou:.4f}")
    if preview:
        lt.preview(s.ts, objects, s.pattern, Path(preview) / f"{tb.SHAPES}-tyrbld-purple-cross.png", view_px=480)
    s.export(objects, baked=bake)


def _poly_mask(poly, W, H):
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    inside = np.zeros((H, W), bool)
    pts = list(poly)
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cond = (y0 > yy) != (y1 > yy)
        xint = (x1 - x0) * (yy - y0) / ((y1 - y0) if y1 != y0 else 1e-9) + x0
        inside ^= cond & (xx < xint)
    return inside


def measure_colours(s, regions):
    """Per region of the top view: the art's median palette index (purple ramp, the darkest and
    brightest 15% dropped as lighting) against the region's material index."""
    W, H = s.W, s.H
    label = np.full((H, W), -1)
    order = sorted(range(len(regions)), key=lambda i: regions[i][3])
    for i in order:
        label[_poly_mask(regions[i][1], W, H)] = i
    g = s.grid
    acc = {}
    for i, (name, poly, pal, z) in enumerate(regions):
        key = name.split("/")[0] + ("" if "/" not in name else "/" + name.split("/")[1])
        sel = (label == i) & (g >= 80) & (g < 96)
        acc.setdefault(key, [[], pal])[0].extend(g[sel].tolist())
    out = []
    for key, (vals, pal) in acc.items():
        if len(vals) < 8:
            continue
        v = np.sort(np.array(vals))
        k = int(len(v) * 0.15)
        core = v[k:len(v) - k] if len(v) - 2 * k > 4 else v
        med = int(np.median(core))
        out.append(dict(region=key, pal=pal, art_median=med, px=len(vals), delta=pal - med))
        print(f"colour {key:16s} pal {pal}  art {med}  ({len(vals)} px)")
    return out


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, preview=lt.preview_arg())
